"""scripts/_unix_port.sh, the one Unix-port probe: each binary is named by the build flavour it reports, `check` fails on
a mismatch and builds nothing, `ensure` runs one setup on a missing or wrong binary, a missing record or a record built
from other inputs, the shared toolchain lock refuses a run while a setup holds it, and the two layouts come from one file."""

import ast
import json
import os
import shlex
import shutil
import subprocess
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from types import ModuleType

import pytest
import tomllib
from _script_loader import load_script_module

REPO_ROOT = Path(__file__).resolve().parent.parent
_LIB = REPO_ROOT / "scripts" / "_unix_port.sh"
_FLAVOURS = ("standard", "settrace", "lwip")
_TIMEOUT_S = 60
_FAST_S = 10  # a held lock fails at once: well inside this, never after a wait
_SETUP_ARGV = ["run", "toolchain/setup_toolchain.py", "setup", "--toolchain-dir"]
# A Unix-port binary of one build flavour: the probe it is handed runs under this suite's interpreter, with sys.settrace,
# lwip and asyncio present or absent as that flavour's build has them; any other invocation fails.
_STUB_BINARY = """#!{python} -I
import sys
FLAVOUR = {flavour!r}
if FLAVOUR != "settrace":
    del sys.settrace
if FLAVOUR == "lwip":
    sys.modules["lwip"] = type(sys)("lwip")
if FLAVOUR == "unusable":
    sys.modules["asyncio"] = None
if sys.argv[1:2] == ["-c"] and len(sys.argv) > 2:
    exec(compile(sys.argv[2], "<probe>", "exec"), {{"__name__": "__main__"}})
    sys.exit(0)
sys.exit(97)
"""
# uv as setup_toolchain.py's `setup` meets it: records its call, whether it could take the toolchain lock exclusively as
# setup does, then lays an after-state tree over the toolchain (STUB_UV_AFTER) and exits with STUB_UV_EXIT.
_STUB_UV = """#!{python} -I
import fcntl, json, os, shutil, sys
from pathlib import Path
args = sys.argv[1:]
toolchain = Path(args[args.index("--toolchain-dir") + 1]) if "--toolchain-dir" in args else None
lock = "no toolchain directory"
if toolchain is not None and toolchain.is_dir():
    with open(toolchain / {lock_name!r}, "a+") as f:
        try:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
            lock = "exclusive"
        except BlockingIOError:
            lock = "refused"
with open({calls!r}, "a", encoding="utf-8") as calls:
    calls.write(json.dumps({{"argv": args, "cwd": os.getcwd(), "lock": lock}}) + "\\n")
after = os.environ.get("STUB_UV_AFTER")
if after and toolchain is not None:
    shutil.copytree(after, toolchain, dirs_exist_ok=True)
sys.exit(int(os.environ.get("STUB_UV_EXIT", "0")))
"""
_HOLDER = """import sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import setup_toolchain
with setup_toolchain.toolchain_lock(Path(sys.argv[2])):
    print("held", flush=True)
    sys.stdin.read()
"""
# Every condition under which ensure runs setup: the binary, its flavour, the record and each input the record hashes.
_REASONS = ["missing binary", "wrong flavour", "no record", "stale versions.toml", "stale setup_toolchain.py", "stale micropython_overrides.py"]


def _binary(toolchain: Path, flavour: str) -> Path:
    return toolchain / "micropython" / "ports" / "unix" / f"build-{flavour}" / "micropython"


def _broken(setup_toolchain: ModuleType, toolchain: Path, why: str) -> None:
    if why == "missing binary":
        _binary(toolchain, "standard").unlink()
    elif why == "wrong flavour":
        _plant_binary(toolchain, "standard", acts_as="settrace")
    elif why == "no record":
        (toolchain / setup_toolchain.TOOLCHAIN_RECORD).unlink()
    else:
        _plant_record(setup_toolchain, toolchain, stale=why.removeprefix("stale "))


def _calls(tmp_path: Path) -> list[dict[str, object]]:
    path = tmp_path / "uv.calls"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()] if path.exists() else []


def _env(tmp_path: Path, toolchain: Path, **extra: str) -> dict[str, str]:
    stub_bin = tmp_path / "stub_bin"
    if not stub_bin.is_dir():
        stub_bin.mkdir()
        (stub_bin / "uv").write_text(_STUB_UV.format(python=sys.executable, calls=str(tmp_path / "uv.calls"), lock_name=".toolchain.lock"), encoding="utf-8")
        (stub_bin / "uv").chmod(0o755)
    env = {name: value for name, value in os.environ.items() if name not in ("SKIP_APT", "STUB_UV_AFTER", "STUB_UV_EXIT")}
    return {**env, "PATH": f"{stub_bin}:{os.environ['PATH']}", "HOME": str(tmp_path / "home"), "PICO_TOOLCHAIN_DIR": str(toolchain), **extra}


@contextmanager
def _exclusive_holder(toolchain: Path) -> Iterator[subprocess.Popen[str]]:
    # setup_toolchain.py's own toolchain_lock(), held in another process until its stdin closes.
    holder = subprocess.Popen([sys.executable, "-I", "-c", _HOLDER, str(REPO_ROOT / "toolchain"), str(toolchain)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        assert holder.stdout is not None
        assert holder.stdout.readline().strip() == "held", holder.stderr.read() if holder.stderr else ""
        yield holder
    finally:
        if holder.stdin is not None:
            holder.stdin.close()
        holder.wait(timeout=_TIMEOUT_S)


def _input_names() -> list[str]:
    # The record's input_sha256 keys, in the order setup_toolchain.py's _toolchain_record() writes them.
    tree = ast.parse((REPO_ROOT / "toolchain" / "setup_toolchain.py").read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            for key, value in zip(node.keys, node.values, strict=True):
                if isinstance(key, ast.Constant) and key.value == "input_sha256" and isinstance(value, ast.Dict):
                    return [k.value for k in value.keys if isinstance(k, ast.Constant) and isinstance(k.value, str)]
    raise AssertionError("no input_sha256 dict in setup_toolchain.py")


def _plant_binary(toolchain: Path, flavour: str, *, acts_as: str | None = None) -> Path:
    path = _binary(toolchain, flavour)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_STUB_BINARY.format(python=sys.executable, flavour=acts_as or flavour), encoding="utf-8")
    path.chmod(0o755)
    return path


def _plant_record(setup_toolchain: ModuleType, toolchain: Path, *, stale: str | None = None) -> dict[str, str]:
    # The record as setup writes it (its own writer), with this tree's input hashes, one of them replaced if stale.
    hashes = {name: setup_toolchain._sha256(REPO_ROOT / "toolchain" / name) for name in _input_names()}
    if stale is not None:
        hashes[stale] = "0" * 64
    record = {"pinned_ref": "v0.0.0", "built_ref": "v0.0.0", "input_sha256": hashes, "unix_binaries": [f"build-{f}" for f in _FLAVOURS]}
    toolchain.mkdir(parents=True, exist_ok=True)
    setup_toolchain._write_json(toolchain / setup_toolchain.TOOLCHAIN_RECORD, record)
    return hashes


def _reasons() -> list[str]:
    return ["missing binary", "wrong flavour", "no record", *(f"stale {name}" for name in _input_names())]


def _run(env: dict[str, str], *args: str, cwd: Path = REPO_ROOT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["/bin/bash", str(_LIB), *args], cwd=cwd, env=env, capture_output=True, text=True, check=False, timeout=_TIMEOUT_S)


def _sourced(env: dict[str, str], *lines: str) -> subprocess.CompletedProcess[str]:
    script = "\n".join(["set -euo pipefail", f"source {shlex.quote(str(_LIB))}", *lines])
    return subprocess.run(["/bin/bash", "-c", script], cwd=REPO_ROOT, env=env, capture_output=True, text=True, check=False, timeout=_TIMEOUT_S)


def _toolchain(setup_toolchain: ModuleType, root: Path) -> Path:
    # A complete toolchain: each flavour's binary acting as itself and a current record.
    for flavour in _FLAVOURS:
        _plant_binary(root, flavour)
    _plant_record(setup_toolchain, root)
    return root


@pytest.fixture(scope="module")
def setup_toolchain() -> ModuleType:
    return load_script_module(REPO_ROOT / "toolchain" / "setup_toolchain.py", "setup_toolchain")


@pytest.mark.parametrize("flavour", _FLAVOURS)
def test_unix_port_bin_names_each_flavours_build_directory(tmp_path: Path, flavour: str) -> None:
    done = _run(_env(tmp_path, tmp_path / "toolchain"), "unix_port_bin", flavour)
    assert (done.returncode, done.stdout, done.stderr) == (0, f"{_binary(tmp_path / 'toolchain', flavour)}\n", "")


def test_the_toolchain_defaults_to_home_and_a_relative_one_is_made_absolute(tmp_path: Path) -> None:
    env = _env(tmp_path, tmp_path / "unused")
    del env["PICO_TOOLCHAIN_DIR"]
    assert _run(env, "unix_port_bin", "standard").stdout == f"{_binary(tmp_path / 'home' / 'pico-toolchain', 'standard')}\n"
    (tmp_path / "work").mkdir()
    done = _run({**env, "PICO_TOOLCHAIN_DIR": "rel/toolchain"}, "unix_port_bin", "lwip", cwd=tmp_path / "work")
    assert done.stdout == f"{_binary(tmp_path / 'work' / 'rel' / 'toolchain', 'lwip')}\n", done


@pytest.mark.parametrize("acts_as", [*_FLAVOURS, "unusable"])
def test_the_flavour_is_what_the_binary_reports_not_its_path(tmp_path: Path, acts_as: str) -> None:
    binary = _plant_binary(tmp_path / "toolchain", "standard", acts_as=acts_as)
    done = _sourced(_env(tmp_path, tmp_path / "toolchain"), f"unix_port_flavour {shlex.quote(str(binary))}")
    assert (done.returncode, done.stdout) == (0, f"{acts_as}\n"), done


def test_a_missing_or_non_executable_binary_reports_unusable(tmp_path: Path) -> None:
    plain = tmp_path / "not_executable"
    plain.write_text("#!/bin/sh\necho standard\n", encoding="utf-8")
    done = _sourced(_env(tmp_path, tmp_path / "toolchain"), f"unix_port_flavour {shlex.quote(str(tmp_path / 'missing'))}", f"unix_port_flavour {shlex.quote(str(plain))}")
    assert (done.returncode, done.stdout) == (0, "unusable\nunusable\n"), done


@pytest.mark.parametrize("flavour", _FLAVOURS)
def test_check_prints_the_path_of_a_matching_binary(setup_toolchain: ModuleType, tmp_path: Path, flavour: str) -> None:
    toolchain = _toolchain(setup_toolchain, tmp_path / "toolchain")
    done = _run(_env(tmp_path, toolchain), "check", flavour)
    assert (done.returncode, done.stdout, done.stderr) == (0, f"{_binary(toolchain, flavour)}\n", "")
    assert _calls(tmp_path) == []


@pytest.mark.parametrize(("found", "wanted"), [("settrace", "standard"), ("standard", "settrace"), ("standard", "lwip"), ("unusable", "standard")])
def test_check_fails_naming_the_found_flavour_and_builds_nothing(setup_toolchain: ModuleType, tmp_path: Path, found: str, wanted: str) -> None:
    toolchain = _toolchain(setup_toolchain, tmp_path / "toolchain")
    _plant_binary(toolchain, wanted, acts_as=found)
    done = _run(_env(tmp_path, toolchain), "check", wanted)
    assert (done.returncode, done.stdout) == (1, ""), done
    # An unusable binary's verdict carries the probe's own last line, the cause a rebuild has to address.
    said = " (the probe said: ModuleNotFoundError: import of asyncio halted; None in sys.modules)" if found == "unusable" else ""
    assert done.stderr.strip() == f"error: {_binary(toolchain, wanted)} reports itself as the '{found}' build flavour, not '{wanted}'{said} - rebuild with: uv run toolchain/setup_toolchain.py setup --clean"
    assert _calls(tmp_path) == []


def test_check_fails_on_a_missing_binary_naming_the_build(setup_toolchain: ModuleType, tmp_path: Path) -> None:
    toolchain = _toolchain(setup_toolchain, tmp_path / "toolchain")
    _binary(toolchain, "settrace").unlink()
    done = _run(_env(tmp_path, toolchain), "check", "settrace")
    assert (done.returncode, done.stdout) == (1, ""), done
    assert done.stderr.strip() == f"error: no MicroPython Unix port at {_binary(toolchain, 'settrace')} - build it with: uv run toolchain/setup_toolchain.py setup"
    assert _calls(tmp_path) == []


def test_a_record_check_without_sha256sum_fails_naming_it(setup_toolchain: ModuleType, tmp_path: Path) -> None:
    # A missing hash tool must not read as a toolchain built from other inputs, which would rebuild it on every run.
    toolchain = _toolchain(setup_toolchain, tmp_path / "toolchain")
    env = _env(tmp_path, toolchain)
    bare = tmp_path / "bare_bin"
    bare.mkdir()
    for name in ("bash", "flock", "dirname"):
        target = shutil.which(name)
        assert target is not None, name
        (bare / name).symlink_to(target)
    (bare / "uv").symlink_to(tmp_path / "stub_bin" / "uv")
    done = _run({**env, "PATH": str(bare)}, "ensure", "standard")
    assert (done.returncode, done.stdout) == (1, ""), done
    assert done.stderr.strip() == "error: sha256sum (coreutils) is not on PATH - scripts/_unix_port.sh compares the toolchain record's input hashes with it"
    assert _calls(tmp_path) == []


def test_ensure_on_a_current_toolchain_runs_no_setup(setup_toolchain: ModuleType, tmp_path: Path) -> None:
    toolchain = _toolchain(setup_toolchain, tmp_path / "toolchain")
    done = _run(_env(tmp_path, toolchain), "ensure", "standard")
    assert (done.returncode, done.stdout, done.stderr) == (0, f"{_binary(toolchain, 'standard')}\n", "")
    assert _calls(tmp_path) == []


def test_the_stale_cases_cover_every_recorded_input() -> None:
    assert _reasons() == _REASONS, "setup_toolchain.py records other inputs - extend _REASONS and scripts/_unix_port.sh"


@pytest.mark.parametrize("why", _REASONS)
def test_ensure_runs_setup_once_and_succeeds_once_the_rebuild_fixed_it(setup_toolchain: ModuleType, tmp_path: Path, why: str) -> None:
    toolchain = _toolchain(setup_toolchain, tmp_path / "toolchain")
    after = _toolchain(setup_toolchain, tmp_path / "after")
    _broken(setup_toolchain, toolchain, why)
    done = _run(_env(tmp_path, toolchain, STUB_UV_AFTER=str(after)), "ensure", "standard")
    assert (done.returncode, done.stdout) == (0, f"{_binary(toolchain, 'standard')}\n"), done
    assert _calls(tmp_path) == [{"argv": [*_SETUP_ARGV, str(toolchain)], "cwd": str(REPO_ROOT), "lock": "exclusive"}], "ensure held its shared lock across setup, or ran it more than once"
    assert "rebuilding the Unix ports" in done.stderr, done.stderr


@pytest.mark.parametrize("why", _REASONS)
def test_ensure_fails_naming_what_is_still_wrong_after_its_one_setup(setup_toolchain: ModuleType, tmp_path: Path, why: str) -> None:
    toolchain = _toolchain(setup_toolchain, tmp_path / "toolchain")
    _broken(setup_toolchain, toolchain, why)
    done = _run(_env(tmp_path, toolchain), "ensure", "standard")
    assert (done.returncode, done.stdout) == (1, ""), done
    assert len(_calls(tmp_path)) == 1
    last = done.stderr.strip().splitlines()[-1]
    expected = {
        "missing binary": f"error: {_binary(toolchain, 'standard')} is still missing after setup - rebuild with: uv run toolchain/setup_toolchain.py setup --clean",
        "wrong flavour": f"error: {_binary(toolchain, 'standard')} reports itself as the 'settrace' build flavour after setup, not 'standard' - rebuild with: uv run toolchain/setup_toolchain.py setup --clean",
        "no record": f"error: setup left no toolchain record at {toolchain / setup_toolchain.TOOLCHAIN_RECORD} - rebuild with: uv run toolchain/setup_toolchain.py setup --clean",
    }.get(why, f"error: the toolchain record at {toolchain / setup_toolchain.TOOLCHAIN_RECORD} still names other inputs than this tree's toolchain/{why.removeprefix('stale ')} after setup - rebuild with: uv run toolchain/setup_toolchain.py setup --clean")
    assert last == expected


def test_ensure_of_several_flavours_runs_one_setup_and_checks_each_after_it(setup_toolchain: ModuleType, tmp_path: Path) -> None:
    # A run needing two builds asks once: one setup covers every binary, and each is probed again after it.
    toolchain = _toolchain(setup_toolchain, tmp_path / "toolchain")
    after = _toolchain(setup_toolchain, tmp_path / "after")
    _binary(toolchain, "standard").unlink()
    _binary(toolchain, "lwip").unlink()
    done = _sourced(_env(tmp_path, toolchain, STUB_UV_AFTER=str(after)), "unix_port_ensure standard lwip", "echo ensured")
    assert (done.returncode, done.stdout) == (0, "ensured\n"), done
    assert len(_calls(tmp_path)) == 1
    _binary(after, "lwip").unlink()
    _binary(toolchain, "lwip").unlink()
    (tmp_path / "uv.calls").unlink()
    done = _sourced(_env(tmp_path, toolchain, STUB_UV_AFTER=str(after)), "unix_port_ensure standard lwip", "echo ensured")
    assert (done.returncode, done.stdout) == (1, ""), done
    assert len(_calls(tmp_path)) == 1
    assert done.stderr.strip().splitlines()[-1] == f"error: {_binary(toolchain, 'lwip')} is still missing after setup - rebuild with: uv run toolchain/setup_toolchain.py setup --clean"


def test_ensure_builds_a_toolchain_that_does_not_exist_yet(setup_toolchain: ModuleType, tmp_path: Path) -> None:
    after = _toolchain(setup_toolchain, tmp_path / "after")
    toolchain = tmp_path / "fresh"
    done = _run(_env(tmp_path, toolchain, STUB_UV_AFTER=str(after)), "ensure", "lwip")
    assert (done.returncode, done.stdout) == (0, f"{_binary(toolchain, 'lwip')}\n"), done
    assert _calls(tmp_path) == [{"argv": [*_SETUP_ARGV, str(toolchain)], "cwd": str(REPO_ROOT), "lock": "no toolchain directory"}]


def test_ensure_passes_skip_apt_through(setup_toolchain: ModuleType, tmp_path: Path) -> None:
    toolchain = _toolchain(setup_toolchain, tmp_path / "toolchain")
    _broken(setup_toolchain, toolchain, "no record")
    _run(_env(tmp_path, toolchain, SKIP_APT="1"), "ensure", "standard")
    assert [call["argv"] for call in _calls(tmp_path)] == [[*_SETUP_ARGV, str(toolchain), "--skip-apt"]]


def test_a_failing_setup_ends_ensure_once_naming_it(setup_toolchain: ModuleType, tmp_path: Path) -> None:
    toolchain = _toolchain(setup_toolchain, tmp_path / "toolchain")
    _broken(setup_toolchain, toolchain, "missing binary")
    done = _run(_env(tmp_path, toolchain, STUB_UV_EXIT="3"), "ensure", "standard")
    assert (done.returncode, done.stdout) == (1, ""), done
    assert done.stderr.strip().splitlines()[-1] == f"error: uv run toolchain/setup_toolchain.py setup --toolchain-dir {toolchain} failed (exit 3) - its output above names the cause"
    assert len(_calls(tmp_path)) == 1


@pytest.mark.parametrize("command", ["check", "ensure"])
def test_a_setup_holding_the_toolchain_lock_fails_a_run_at_once_naming_it(setup_toolchain: ModuleType, tmp_path: Path, command: str) -> None:
    toolchain = _toolchain(setup_toolchain, tmp_path / "toolchain")
    with _exclusive_holder(toolchain) as holder:
        started = time.monotonic()
        done = _run(_env(tmp_path, toolchain), command, "standard")
        elapsed = time.monotonic() - started
    assert (done.returncode, done.stdout) == (1, ""), done
    assert done.stderr.strip() == f"error: the toolchain at {toolchain} is in use by a setup or firmware build (pid {holder.pid}, holding {toolchain / setup_toolchain.TOOLCHAIN_LOCK}) - wait for it to finish, or use another PICO_TOOLCHAIN_DIR"
    assert elapsed < _FAST_S, f"the refusal took {elapsed:.1f}s: a run waited for the lock"
    assert _calls(tmp_path) == []


def test_a_run_holds_the_lock_shared_for_its_life_and_releases_it_on_exit(setup_toolchain: ModuleType, tmp_path: Path) -> None:
    toolchain = _toolchain(setup_toolchain, tmp_path / "toolchain")
    env = _env(tmp_path, toolchain)
    script = "\n".join(["set -euo pipefail", f"source {shlex.quote(str(_LIB))}", "unix_port_ensure standard", "unix_port_check lwip", 'echo "ready"', "read -r _ || true"])
    run = subprocess.Popen(["/bin/bash", "-c", script], cwd=REPO_ROOT, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        assert run.stdout is not None
        assert run.stdout.readline().strip() == "ready", run.stderr.read() if run.stderr else ""
        assert _run(env, "check", "settrace").returncode == 0, "a second run sharing the lock was refused"
        with pytest.raises(setup_toolchain.SetupError, match=r"^a test run is using the Unix ports of .* \(it holds the toolchain lock shared\)"), setup_toolchain.toolchain_lock(toolchain):
            pass
    finally:
        if run.stdin is not None:
            run.stdin.close()
        assert run.wait(timeout=_TIMEOUT_S) == 0
    with setup_toolchain.toolchain_lock(toolchain):
        pass


@pytest.mark.parametrize("layout", ["unit", "twin"])
def test_micropypath_prints_the_layout_files_value(layout: str) -> None:
    expected = tomllib.loads((REPO_ROOT / "scripts" / "micropypath.toml").read_text(encoding="utf-8"))[layout]
    done = _run(dict(os.environ), "micropypath", layout)
    assert (done.returncode, done.stdout, done.stderr) == (0, f"{expected}\n", "")


def test_a_layout_file_without_the_line_fails_naming_it(tmp_path: Path) -> None:
    (tmp_path / "scripts").mkdir()
    shutil.copy2(_LIB, tmp_path / "scripts" / "_unix_port.sh")
    (tmp_path / "scripts" / "micropypath.toml").write_text('unit = "src:.frozen"\n', encoding="utf-8")
    done = subprocess.run(["/bin/bash", str(tmp_path / "scripts" / "_unix_port.sh"), "micropypath", "twin"], capture_output=True, text=True, check=False, timeout=_TIMEOUT_S)
    assert (done.returncode, done.stdout) == (1, ""), done
    assert done.stderr.strip() == f'error: {tmp_path / "scripts" / "micropypath.toml"} has no single twin = "…" line'


@pytest.mark.parametrize(
    ("args", "message"),
    [
        ((), "error: no command given"),
        (("frobnicate", "standard"), "error: unknown command 'frobnicate'"),
        (("check",), "error: check needs one build flavour"),
        (("ensure", "standard", "extra"), "error: ensure needs one build flavour"),
        (("check", "plain"), "error: unknown build flavour 'plain' - one of: standard settrace lwip"),
        (("unix_port_bin", "unusable"), "error: unknown build flavour 'unusable' - one of: standard settrace lwip"),
        (("micropypath", "frozen"), "error: unknown MICROPYPATH layout 'frozen' - one of: unit twin"),
    ],
    ids=["none", "unknown-command", "no-flavour", "extra-argument", "unknown-flavour", "probe-word-is-no-flavour", "unknown-layout"],
)
def test_a_malformed_command_is_a_usage_error(tmp_path: Path, args: tuple[str, ...], message: str) -> None:
    done = _run(_env(tmp_path, tmp_path / "toolchain"), *args)
    assert (done.returncode, done.stdout) == (2, ""), done
    assert done.stderr.splitlines()[0] == message
    assert done.stderr.splitlines()[1].startswith("Usage: scripts/_unix_port.sh ")
    assert _calls(tmp_path) == []


@pytest.mark.parametrize("flag", ["-h", "--help"])
def test_help_answers_with_the_usage(flag: str) -> None:
    done = _run(dict(os.environ), flag)
    assert (done.returncode, done.stderr) == (0, ""), done
    assert done.stdout.startswith("Usage: scripts/_unix_port.sh ")


def test_sourcing_it_changes_none_of_the_callers_shell_options(tmp_path: Path) -> None:
    # Read in the calling shell itself: a $(...) would not show errexit, which bash clears in command substitutions.
    before, after = tmp_path / "before", tmp_path / "after"
    probe = f'opts() {{ printf "%s\\n" "$-"; set +o; shopt -p; }}; opts >{before}; source {shlex.quote(str(_LIB))}; opts >{after}'
    done = subprocess.run(["/bin/bash", "-c", probe], capture_output=True, text=True, check=False, timeout=_TIMEOUT_S)
    assert (done.returncode, done.stderr) == (0, ""), done
    assert after.read_text(encoding="utf-8") == before.read_text(encoding="utf-8")
