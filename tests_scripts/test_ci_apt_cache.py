"""Tests scripts/ci_apt_cache.py against loopback mirrors, one throttled and one fast: the slow mirror is dropped and
the fast one kept, an unknown list form is never edited, the list is never emptied, the key follows the exact
archives, a full cache hit skips the probe, and a cached file reaches apt only when the index's SHA-256 matches."""

import contextlib
import hashlib
import os
import subprocess
import sys
import threading
import time
from collections.abc import Callable, Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import ModuleType

import pytest
from _script_loader import load_script_module

_SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "ci_apt_cache.py"
# The probe's cap in these tests: each slow mirror is waited out to it.
# @tunable l0.apt_mirror_probe_test_cap_s = 0.5
_CAP_S = 0.5
_MIN_RATE = 400_000.0  # the healthy rate the tests ask for: 5x the throttled mirror's 80 kB/s
_BODY = bytes(range(256)) * 1200  # 300 kB, more than the probe's 200 kB budget (cap x rate)
_POOL = "pool/main/p/probe/probe_1.0-1_amd64.deb"
_FILE = "probe_1.0-1_amd64.deb"

Serve = Callable[[BaseHTTPRequestHandler, "Mirror"], None]


class Mirror:
    # A loopback mirror on 127.0.0.1: `serve` answers each GET, `paths` records them; close() ends any stall.
    def __init__(self, serve: Serve) -> None:
        self.paths: list[str] = []
        self.stop = threading.Event()
        mirror = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                mirror.paths.append(self.path)
                with contextlib.suppress(BrokenPipeError, ConnectionResetError):
                    serve(self, mirror)

            def log_message(self, *args: object) -> None:
                del args

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.server.daemon_threads = True
        self.thread = threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
        self.thread.start()

    @property
    def uri(self) -> str:
        return f"http://127.0.0.1:{self.server.server_address[1]}/ubuntu/"

    def close(self) -> None:
        self.stop.set()
        self.server.shutdown()
        self.server.server_close()


def _headers(handler: BaseHTTPRequestHandler, status: int = 200, **extra: str) -> None:
    handler.send_response(status)
    handler.send_header("Content-Length", str(len(_BODY) if status == 200 else 0))
    for name, value in extra.items():
        handler.send_header(name, value)
    handler.end_headers()


def fast(handler: BaseHTTPRequestHandler, mirror: Mirror) -> None:
    del mirror
    _headers(handler)
    handler.wfile.write(_BODY)


def throttled(chunk: int) -> Serve:
    # chunk bytes every 50 ms: 4096 is 80 kB/s, 1024 is 20 kB/s.
    def serve(handler: BaseHTTPRequestHandler, mirror: Mirror) -> None:
        _headers(handler)
        for start in range(0, len(_BODY), chunk):
            handler.wfile.write(_BODY[start : start + chunk])
            handler.wfile.flush()
            if mirror.stop.wait(0.05):
                return

    return serve


def status(code: int, location: str = "") -> Serve:
    def serve(handler: BaseHTTPRequestHandler, mirror: Mirror) -> None:
        del mirror
        if location:
            _headers(handler, code, Location=location)
        else:
            _headers(handler, code)

    return serve


@pytest.fixture(scope="module")
def apt_cache() -> ModuleType:
    return load_script_module(_SCRIPT, "ci_apt_cache")


@pytest.fixture
def mirrors() -> Iterator[Callable[[Serve], Mirror]]:
    started: list[Mirror] = []

    def start(serve: Serve) -> Mirror:
        started.append(Mirror(serve))
        return started[-1]

    yield start
    for mirror in started:
        mirror.close()


def _list(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "apt-mirrors.txt"
    path.write_text(text, encoding="utf-8")
    return path


def _planned(apt_cache: ModuleType, list_path: Path, body: bytes = _BODY, file: str = _FILE) -> object:
    return apt_cache.Planned(f"mirror+file:{list_path}/{_POOL}", file, len(body), hashlib.sha256(body).hexdigest())


def _check(apt_cache: ModuleType, list_path: Path, **kwargs: object) -> "str | None":
    planned = kwargs.pop("planned", None) or [_planned(apt_cache, list_path)]
    result: str | None = apt_cache.check(planned, kwargs.pop("have", set()), list_path, cap_s=_CAP_S, min_rate=_MIN_RATE, **kwargs)
    return result


def test_a_slow_mirror_apt_tries_first_is_dropped_and_the_fast_one_kept(apt_cache: ModuleType, mirrors: Callable[[Serve], Mirror], tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    slow, quick = mirrors(throttled(4096)), mirrors(fast)
    # The fast mirror's line comes first, but priority:1 makes apt try the slow one first (methods/mirror.cc).
    list_path = _list(tmp_path, f"{quick.uri}\tpriority:2\n{slow.uri}\tpriority:1\nhttps://security.example/ubuntu/\tpriority:3\n")
    assert _check(apt_cache, list_path) == f"{quick.uri}\tpriority:2\nhttps://security.example/ubuntu/\tpriority:3\n"
    assert slow.paths == quick.paths == [f"/ubuntu/{_POOL}"], "each mirror probed once, at the archive's own pool path"
    out = capsys.readouterr().out
    assert f"== probe {slow.uri}{_POOL}: " in out and f"== probe {quick.uri}{_POOL}: 200000 of 200000 bytes" in out, out
    assert f"::warning::dropped {slow.uri} from {list_path}" in out, out


def test_a_healthy_first_mirror_leaves_the_list_as_it_is(apt_cache: ModuleType, mirrors: Callable[[Serve], Mirror], tmp_path: Path) -> None:
    quick, slow = mirrors(fast), mirrors(throttled(4096))
    list_path = _list(tmp_path, f"{quick.uri}\tpriority:1\n{slow.uri}\tpriority:2\n")
    assert _check(apt_cache, list_path) is None
    assert slow.paths == [], "the probe stops at the first healthy mirror"


def test_a_redirect_is_followed_and_an_http_error_is_not_healthy(apt_cache: ModuleType, mirrors: Callable[[Serve], Mirror], tmp_path: Path) -> None:
    quick = mirrors(fast)
    moved = mirrors(status(302, f"{quick.uri}{_POOL}"))
    missing = mirrors(status(404))
    assert _check(apt_cache, _list(tmp_path, f"{moved.uri}\tpriority:1\n{quick.uri}\tpriority:2\n")) is None, "a mirror that redirects to a healthy one is healthy"
    assert _check(apt_cache, _list(tmp_path, f"{missing.uri}\tpriority:1\n{quick.uri}\tpriority:2\n")) == f"{quick.uri}\tpriority:2\n"


@pytest.mark.parametrize(
    "first_line",
    [
        "deb {uri} noble main",  # a sources.list line, not a mirror list
        "{uri}\tarch:amd64",  # a tag apt matches per item, which a probe of one archive cannot honour
        " {uri}\tpriority:1",  # leading blank: apt would read it as another URI
        "{uri}\tpriority:first",
    ],
)
def test_a_list_in_an_unknown_form_is_left_unchanged_with_a_warning(apt_cache: ModuleType, mirrors: Callable[[Serve], Mirror], tmp_path: Path, capsys: pytest.CaptureFixture[str], first_line: str) -> None:
    slow, quick = mirrors(throttled(4096)), mirrors(fast)
    list_path = _list(tmp_path, first_line.format(uri=slow.uri) + f"\n{quick.uri}\tpriority:2\n")
    assert _check(apt_cache, list_path) is None
    assert slow.paths == quick.paths == [], "nothing is probed on a list the check cannot read"
    assert f"::warning::{list_path} is in a form this check does not recognise: left unchanged" in capsys.readouterr().out


def test_the_list_is_never_emptied(apt_cache: ModuleType, mirrors: Callable[[Serve], Mirror], tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    slower, slow = mirrors(throttled(1024)), mirrors(throttled(4096))
    # No mirror healthy: the fastest measured goes first, everything ahead of it is dropped, it and the rest stay.
    assert _check(apt_cache, _list(tmp_path, f"{slower.uri}\tpriority:1\n{slow.uri}\tpriority:2\n")) == f"{slow.uri}\tpriority:2\n"
    assert f"the fastest measured, {slow.uri}, goes first" in capsys.readouterr().out
    # A lone slow mirror, and mirrors that never answer, leave the list as it is.
    assert _check(apt_cache, _list(tmp_path, f"{slow.uri}\tpriority:1\n")) is None
    refused = socketless_uri()
    assert _check(apt_cache, _list(tmp_path, f"{refused}\tpriority:1\n{refused}x/\tpriority:2\n")) is None
    assert "answered the probe: left unchanged" in capsys.readouterr().out


def socketless_uri() -> str:
    # A loopback port nothing listens on: the probe's connection is refused.
    server = ThreadingHTTPServer(("127.0.0.1", 0), BaseHTTPRequestHandler)
    port = server.server_address[1]
    server.server_close()
    return f"http://127.0.0.1:{port}/ubuntu/"


def test_a_full_cache_hit_skips_the_check_unless_forced(apt_cache: ModuleType, mirrors: Callable[[Serve], Mirror], tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    slow, quick = mirrors(throttled(4096)), mirrors(fast)
    list_path = _list(tmp_path, f"{slow.uri}\tpriority:1\n{quick.uri}\tpriority:2\n")
    assert _check(apt_cache, list_path, have={_FILE}) is None
    assert slow.paths == quick.paths == []
    assert "every planned archive came from the cache: no mirror check" in capsys.readouterr().out
    # A later step fetching more from the same list (the cross-browser job) forces it.
    assert _check(apt_cache, list_path, have={_FILE}, force=True) == f"{quick.uri}\tpriority:2\n"


# The stall test's cap: one byte at half the cap, then nothing. A read that waits only the time left ends at the cap,
# one that waits a whole cap ends at 1.5 caps; the bound sits midway.
# @tunable l0.apt_mirror_probe_stall_test_cap_s = 2.0
_STALL_CAP_S = 2.0


def test_a_probe_never_outlasts_its_cap(apt_cache: ModuleType, mirrors: Callable[[Serve], Mirror]) -> None:
    def late_stall(handler: BaseHTTPRequestHandler, mirror: Mirror) -> None:
        _headers(handler)
        handler.wfile.flush()
        if not mirror.stop.wait(_STALL_CAP_S / 2):
            handler.wfile.write(b"x")
            handler.wfile.flush()
            mirror.stop.wait(_STALL_CAP_S * 5)

    stalled = mirrors(late_stall)
    start = time.monotonic()
    probe = apt_cache.fetch(f"{stalled.uri}{_POOL}", cap_s=_STALL_CAP_S, budget=len(_BODY))
    elapsed = time.monotonic() - start
    assert probe.received == 1 and not probe.error, probe
    assert elapsed < _STALL_CAP_S * 1.25, f"the probe took {elapsed:.2f} s against its {_STALL_CAP_S} s cap"


_URIS = """Reading package lists...
'mirror+file:/etc/apt/apt-mirrors.txt/pool/main/c/cmake/cmake_3.28.3-1build7_amd64.deb' cmake_3.28.3-1build7_amd64.deb 11190006 SHA256:{cmake}
'mirror+file:/etc/apt/apt-mirrors.txt/pool/universe/g/gcc-arm-none-eabi/gcc-arm-none-eabi_15%3a13.2.rel1-2_amd64.deb' gcc-arm-none-eabi_15%3a13.2.rel1-2_amd64.deb 57521126 SHA256:{gcc}
"""


def _uris(cmake: str = "a" * 64, gcc: str = "b" * 64) -> str:
    return _URIS.format(cmake=cmake, gcc=gcc)


def test_the_key_follows_the_exact_archives_and_not_their_order(apt_cache: ModuleType) -> None:
    planned, unparsed = apt_cache.parse_print_uris(_uris())
    assert unparsed == [] and [item.file for item in planned] == ["cmake_3.28.3-1build7_amd64.deb", "gcc-arm-none-eabi_15%3a13.2.rel1-2_amd64.deb"]
    key = apt_cache.cache_key("apt-firmware-Linux-", planned)
    assert key.startswith("apt-firmware-Linux-") and len(key) == len("apt-firmware-Linux-") + 64
    assert apt_cache.cache_key("apt-firmware-Linux-", list(reversed(planned))) == key, "a reordered set keeps its key"
    reordered = "".join(reversed(_uris().splitlines(keepends=True)))
    assert apt_cache.cache_key("apt-firmware-Linux-", apt_cache.parse_print_uris(reordered)[0]) == key
    bumped = _uris().replace("3.28.3-1build7", "3.28.3-1ubuntu0.1")
    assert apt_cache.cache_key("apt-firmware-Linux-", apt_cache.parse_print_uris(bumped)[0]) != key, "a changed version changes the key"
    rebuilt = apt_cache.parse_print_uris(_uris(cmake="c" * 64))[0]
    assert apt_cache.cache_key("apt-firmware-Linux-", rebuilt) != key, "a changed archive changes the key"


def test_a_line_without_sha256_is_never_cached_and_a_foreign_line_is_named(apt_cache: ModuleType) -> None:
    text = _uris() + (
        "'http://x/pool/m/md5_1_all.deb' md5_1_all.deb 10 MD5Sum:0123456789abcdef0123456789abcdef\n"
        "'http://x/pool/n/nohash_1_all.deb' nohash_1_all.deb 10 \n"
        "'http://x/pool/../escape.deb' ../escape.deb 10 SHA256:" + "d" * 64 + "\n"
        "'http://x/pool/h/hidden_1_all.deb' .hidden_1_all.deb 10 SHA256:" + "e" * 64 + "\n"
        "'not a print-uris line\n"
    )
    planned, unparsed = apt_cache.parse_print_uris(text)
    assert {item.file: item.sha256 for item in planned if not item.sha256} == {"md5_1_all.deb": "", "nohash_1_all.deb": ""}
    assert len(unparsed) == 3, unparsed
    base = apt_cache.cache_key("p-", apt_cache.parse_print_uris(_uris())[0])
    assert apt_cache.cache_key("p-", planned) == base, "an archive with no SHA-256 is no part of the cache, so not of its key"


def test_a_cached_archive_reaches_apt_only_with_the_index_size_and_sha256(apt_cache: ModuleType, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    # apt trusts a pre-placed archive of the right size (apt-pkg/acquire-item.cc); this check is what verifies its content.
    cache = tmp_path / "cache"
    cache.mkdir()
    good, altered, short = b"good archive", b"evil archive", b"short"
    planned = [_planned(apt_cache, tmp_path, good, "good_1_all.deb"), _planned(apt_cache, tmp_path, good, "altered_1_all.deb"), _planned(apt_cache, tmp_path, good, "short_1_all.deb"), _planned(apt_cache, tmp_path, good, "absent_1_all.deb")]
    (cache / "good_1_all.deb").write_bytes(good)
    (cache / "altered_1_all.deb").write_bytes(altered)
    (cache / "short_1_all.deb").write_bytes(short)
    assert apt_cache.copy_in(planned, cache) == [cache / "good_1_all.deb"]
    out = capsys.readouterr().out
    assert "cached altered_1_all.deb does not match" in out and "cached short_1_all.deb does not match" in out and "absent" not in out, out


def test_copy_out_takes_what_apt_fetched_and_drops_what_the_set_no_longer_holds(apt_cache: ModuleType, tmp_path: Path) -> None:
    archives, cache = tmp_path / "archives", tmp_path / "cache"
    archives.mkdir()
    cache.mkdir()
    one, two = b"first archive", b"second archive"
    planned = [_planned(apt_cache, tmp_path, one, "one_1_all.deb"), _planned(apt_cache, tmp_path, two, "two_1_all.deb")]
    (archives / "one_1_all.deb").write_bytes(one)
    (archives / "two_1_all.deb").write_bytes(b"second archivX")  # torn or altered: never cached
    (cache / "old_0_all.deb").write_bytes(b"a version the set has moved past")
    assert apt_cache.copy_out(planned, archives, cache) == (1, 1)
    assert sorted(p.name for p in cache.iterdir()) == ["one_1_all.deb"]
    (archives / "two_1_all.deb").write_bytes(two)
    assert apt_cache.copy_out(planned, archives, cache) == (1, 0)
    assert sorted(p.name for p in cache.iterdir()) == ["one_1_all.deb", "two_1_all.deb"]


def test_playwrights_dry_run_names_its_packages(apt_cache: ModuleType) -> None:
    missing = "Missing system dependencies (3):\n  fonts-freefont-ttf\n  libglib2.0-0t64\n  xvfb\n"
    assert apt_cache.dry_run_packages("npm notice\n" + missing) == ["fonts-freefont-ttf", "libglib2.0-0t64", "xvfb"]
    assert apt_cache.dry_run_packages("All system dependencies are installed.\n") == []
    assert apt_cache.dry_run_packages(missing.replace("(3)", "(4)")) is None, "a count the list does not match"
    assert apt_cache.dry_run_packages("Installing dependencies...\n") is None


def _run(*args: str, **paths: Path) -> "subprocess.CompletedProcess[str]":
    argv = [sys.executable, "-I", str(_SCRIPT), *args]
    for name, path in paths.items():
        argv += [f"--{name.replace('_', '-')}", str(path)]
    return subprocess.run(argv, capture_output=True, text=True, check=False, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})


def _outputs(path: Path) -> "dict[str, str]":
    return dict(line.split("=", 1) for line in path.read_text(encoding="utf-8").splitlines())


def test_the_commands_chain_as_the_ci_steps_run_them(mirrors: Callable[[Serve], Mirror], tmp_path: Path) -> None:
    slow, quick = mirrors(throttled(4096)), mirrors(fast)
    list_path = _list(tmp_path, f"{slow.uri}\tpriority:1\n{quick.uri}\tpriority:2\n")
    sha = hashlib.sha256(_BODY).hexdigest()
    (tmp_path / "uris.txt").write_text(f"'mirror+file:{list_path}/{_POOL}' {_FILE} {len(_BODY)} SHA256:{sha}\n", encoding="utf-8")
    manifest, cache, archives = tmp_path / "manifest.json", tmp_path / "cache", tmp_path / "archives"
    plan_out, copy_out, save_out = tmp_path / "plan.out", tmp_path / "copy.out", tmp_path / "save.out"
    done = _run("plan", "--key-prefix", "apt-test-Linux-", uris=tmp_path / "uris.txt", manifest=manifest, github_output=plan_out)
    assert done.returncode == 0, done.stdout + done.stderr
    assert _outputs(plan_out) == {"key": "apt-test-Linux-" + hashlib.sha256(f"{_FILE} {len(_BODY)} {sha}\n".encode()).hexdigest(), "restore-prefix": "apt-test-Linux-", "planned": "1"}
    cache.mkdir()
    done = _run("copy-in", manifest=manifest, cache_dir=cache, list=tmp_path / "copy-in", github_output=copy_out)
    assert done.returncode == 0 and _outputs(copy_out) == {"restored": "0", "remaining": "1"}, done.stdout + done.stderr
    done = _run("check", "--cap-s", str(_CAP_S), "--min-bytes-per-s", str(_MIN_RATE), manifest=manifest, have=tmp_path / "copy-in", mirror_list=list_path, out=tmp_path / "new.txt")
    assert done.returncode == 0, done.stdout + done.stderr
    assert (tmp_path / "new.txt").read_text(encoding="utf-8") == f"{quick.uri}\tpriority:2\n"
    assert list_path.read_text(encoding="utf-8").startswith(slow.uri), "the script never writes the live list: the CI step copies --out over it"
    archives.mkdir()
    (archives / _FILE).write_bytes(_BODY)
    done = _run("copy-out", manifest=manifest, archives=archives, cache_dir=cache, github_output=save_out)
    assert done.returncode == 0 and _outputs(save_out) == {"complete": "true", "copied": "1"}, done.stdout + done.stderr
    done = _run("copy-in", manifest=manifest, cache_dir=cache, list=tmp_path / "copy-in", github_output=copy_out)
    assert (tmp_path / "copy-in").read_bytes() == str(cache / _FILE).encode() + b"\0"
    done = _run("check", manifest=manifest, have=tmp_path / "copy-in", mirror_list=list_path, out=tmp_path / "hit.txt")
    assert done.returncode == 0 and "no mirror check" in done.stdout and not (tmp_path / "hit.txt").exists(), done.stdout + done.stderr
    (tmp_path / "dry-run.txt").write_text("Missing system dependencies (2):\n  libnss3\n  xvfb\n", encoding="utf-8")
    done = _run("dry-run-packages", dry_run=tmp_path / "dry-run.txt")
    assert (done.returncode, done.stdout) == (0, "libnss3 xvfb\n"), done.stderr
    (tmp_path / "dry-run.txt").write_text("Installing dependencies...\n", encoding="utf-8")
    done = _run("dry-run-packages", dry_run=tmp_path / "dry-run.txt")
    assert (done.returncode, done.stdout) == (1, "") and "does not know" in done.stderr, "an unread form exits 1 and leaves stdout, which the step captures, empty"
