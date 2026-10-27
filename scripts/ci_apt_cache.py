#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""CI's apt download guard (SPECIFICATION.md B.10.1): a mirror check that drops a slow runner mirror before apt
fetches, and the package cache's key and copy-in and copy-out lists. Every path is a parameter; the CI steps run apt,
the privileged copies and the mirror-list write themselves, so this script never needs root."""

# Usage: ci_apt_cache.py {plan|dry-run-packages|copy-in|check|copy-out} ... (--help on each); a usage error exits 2.

import argparse
import hashlib
import http.client
import json
import re
import shutil
import ssl
import sys
import time
import urllib.parse
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import socket
    from collections.abc import Iterable
    from typing import Protocol

    class Fetcher(Protocol):
        def __call__(self, url: str, *, cap_s: float, budget: int) -> "Probe": ...

# One mirror probe's cap and the rate it must reach: healthy nodes serve 30 MB/s or more, slow ones 45-130 kB/s
# (actions/runner-images#14823). The probe reads at most cap x rate bytes: "healthy" is "that much inside the cap".
# @tunable ci.apt_mirror_probe_cap_s = 10
PROBE_CAP_S = 10
# @tunable ci.apt_mirror_min_bytes_per_s = 1000000
MIN_BYTES_PER_S = 1000000

_LINE = re.compile(r"^'(?P<uri>[^'\s]+)' (?P<file>\S+) (?P<size>\d+) ?(?P<hash>\S*)$")
_SHA256 = re.compile(r"^sha256:([0-9a-f]{64})$", re.IGNORECASE)
# A Debian archive's file name (name_version_arch.deb, an epoch's colon written %3a): never a path, never hidden.
_FILE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.+~%_-]*$")
_MIRROR = re.compile(r"^https?://\S+$")
_PRIORITY = re.compile(r"^priority:(\d+)$")
# apt's mirror method sorts a line without a priority tag after every tagged one (methods/mirror.cc, MirrorInfo).
_NO_PRIORITY = 2**64 - 1
_DRY_RUN_MISSING = re.compile(r"^Missing system dependencies \((\d+)\):$")
_DRY_RUN_NONE = "All system dependencies are installed."
_CHUNK = 64 * 1024
_MAX_REDIRECTS = 3
_HTTP_OK = 200
_REDIRECTS = frozenset({301, 302, 303, 307, 308})


@dataclass(frozen=True)
class Planned:
    # One archive apt is about to fetch, as `apt-get --print-uris` names it; sha256 is "" where the index gave none.
    uri: str
    file: str
    size: int
    sha256: str


@dataclass(frozen=True)
class Mirror:
    line: int
    uri: str
    priority: int


@dataclass(frozen=True)
class Probe:
    url: str
    received: int
    seconds: float
    error: str = ""

    @property
    def rate(self) -> float:
        return self.received / self.seconds if self.seconds > 0 else float("inf")


def warn(message: str) -> None:
    print(f"::warning::{message}", flush=True)


def emit(path: "Path | None", **values: object) -> None:
    # Step outputs: appended to $GITHUB_OUTPUT when given, else printed.
    lines = "".join(f"{name.replace('_', '-')}={value}\n" for name, value in values.items())
    if path is None:
        print(lines, end="", flush=True)
    else:
        with path.open("a", encoding="utf-8") as out:
            out.write(lines)


def parse_print_uris(text: str) -> "tuple[list[Planned], list[str]]":
    # apt-get --print-uris prints `'URI' FILE SIZE HASH` per archive (apt-private/private-install.cc); other lines are
    # apt's own chatter. A quoted line that does not parse is returned, so the caller can name it.
    planned, unparsed = [], []
    for line in text.splitlines():
        if not line.startswith("'"):
            continue
        found = _LINE.match(line)
        if found is None or not _FILE.match(found["file"]):
            unparsed.append(line)
            continue
        digest = _SHA256.match(found["hash"])
        planned.append(Planned(found["uri"], found["file"], int(found["size"]), digest[1].lower() if digest else ""))
    return sorted(planned, key=lambda item: item.file), unparsed


def cache_key(prefix: str, planned: "Iterable[Planned]") -> str:
    # The exact archives, in a fixed order: a changed version changes the key, a reordered set does not.
    lines = sorted(f"{item.file} {item.size} {item.sha256}\n" for item in planned if item.sha256)
    return prefix + hashlib.sha256("".join(lines).encode()).hexdigest()


def write_manifest(path: Path, planned: "list[Planned]") -> None:
    path.write_text(json.dumps([asdict(item) for item in planned], indent=1) + "\n", encoding="utf-8")


def read_manifest(path: Path) -> "list[Planned]":
    return [Planned(str(item["uri"]), str(item["file"]), int(item["size"]), str(item["sha256"])) for item in json.loads(path.read_text(encoding="utf-8"))]


def verified(path: Path, item: Planned) -> bool:
    # True only for a regular file of the index's size and SHA-256: apt itself checks a pre-placed archive's size alone.
    if not item.sha256 or not path.is_file() or path.stat().st_size != item.size:
        return False
    digest = hashlib.sha256()
    with path.open("rb") as data:
        while chunk := data.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest() == item.sha256


def dry_run_packages(text: str) -> "list[str] | None":
    # The packages `npx playwright install-deps --dry-run` reports missing (its `apt-get install -s` Inst lines), [] when
    # it reports none; None for output in a form this reader does not know.
    lines = [line.rstrip() for line in text.splitlines()]
    if _DRY_RUN_NONE in lines:
        return []
    for index, line in enumerate(lines):
        found = _DRY_RUN_MISSING.match(line)
        if found is None:
            continue
        names = [entry.strip() for entry in lines[index + 1 : index + 1 + int(found[1])] if re.fullmatch(r"  [a-z0-9][a-z0-9.+:-]*", entry)]
        return names if len(names) == int(found[1]) else None
    return None


def copy_in(planned: "list[Planned]", cache_dir: Path) -> "list[Path]":
    # The cached archives safe to place in apt's archive folder: each checked against the fresh index's SHA-256.
    keep = []
    for item in planned:
        path = cache_dir / item.file
        if verified(path, item):
            keep.append(path)
        elif path.exists():
            warn(f"cached {item.file} does not match the index's size and SHA-256: left out, apt fetches it")
    return keep


def copy_out(planned: "list[Planned]", archives: Path, cache_dir: Path) -> "tuple[int, int]":
    # Copies each archive apt fetched into the cache folder, drops what the set no longer holds; (copied, missing).
    cache_dir.mkdir(parents=True, exist_ok=True)
    wanted = {item.file for item in planned if item.sha256}
    for stale in sorted(p for p in cache_dir.iterdir() if p.name not in wanted):
        if stale.is_file():
            stale.unlink()
    copied = missing = 0
    for item in planned:
        if not item.sha256 or verified(cache_dir / item.file, item):
            continue
        source = archives / item.file
        if verified(source, item):
            partial = cache_dir / f".{item.file}.partial"
            shutil.copyfile(source, partial)
            partial.replace(cache_dir / item.file)
            copied += 1
        else:
            missing += 1
    return copied, missing


def parse_mirror_list(text: str) -> "list[Mirror] | None":
    # The runner's apt-mirrors.txt: one URI per line, tab, optional `priority:N` tags; '#' and empty lines skipped
    # (apt's methods/mirror.cc). Any other tag or form returns None, so the list is never edited on a guess.
    mirrors = []
    for number, line in enumerate(text.split("\n")):
        if not line or line.startswith("#"):
            continue
        uri, _, tags = line.partition("\t")
        if not _MIRROR.match(uri):
            return None
        priority = _NO_PRIORITY
        for tag in tags.split():
            found = _PRIORITY.match(tag)
            if found is None:
                return None
            priority = int(found[1])
        mirrors.append(Mirror(number, uri, priority))
    return mirrors or None


def apt_order(mirrors: "list[Mirror]") -> "list[Mirror]":
    # apt tries the lowest priority first; equal priorities it shuffles, which file order stands in for here.
    return sorted(mirrors, key=lambda mirror: mirror.priority)


def without(text: str, dropped: "list[Mirror]") -> str:
    lines = {mirror.line for mirror in dropped}
    return "\n".join(line for number, line in enumerate(text.split("\n")) if number not in lines)


class _ProbeHTTP(http.client.HTTPConnection):
    # Keeps its socket after a `Connection: close` response detaches it, so each read gets the time left to the cap.
    probe_sock: "socket.socket | None" = None

    def connect(self) -> None:
        super().connect()
        self.probe_sock = self.sock


class _ProbeHTTPS(http.client.HTTPSConnection):
    probe_sock: "socket.socket | None" = None

    def connect(self) -> None:
        super().connect()
        self.probe_sock = self.sock


def fetch(url: str, *, cap_s: float, budget: int) -> Probe:
    # Reads up to budget bytes of url, never past cap_s: each read waits only the time left. A stall is the cap
    # running out (an empty error); a refused connection, an HTTP error or a broken transfer names itself.
    start = time.monotonic()
    received = 0
    try:
        for _ in range(_MAX_REDIRECTS + 1):
            parts = urllib.parse.urlsplit(url)
            left = cap_s - (time.monotonic() - start)
            if left <= 0:
                return Probe(url, received, time.monotonic() - start)
            host = parts.hostname or ""
            conn: _ProbeHTTP | _ProbeHTTPS = _ProbeHTTPS(host, parts.port, timeout=left, context=ssl.create_default_context()) if parts.scheme == "https" else _ProbeHTTP(host, parts.port, timeout=left)
            try:
                conn.request("GET", urllib.parse.urlunsplit(("", "", parts.path or "/", parts.query, "")), headers={"User-Agent": "ci_apt_cache mirror probe"})
                response = conn.getresponse()
                location = response.getheader("Location")
                if response.status in _REDIRECTS and location:
                    url = urllib.parse.urljoin(url, location)
                    continue
                if response.status != _HTTP_OK:
                    return Probe(url, 0, time.monotonic() - start, f"HTTP {response.status}")
                while received < budget:
                    left = cap_s - (time.monotonic() - start)
                    if left <= 0 or conn.probe_sock is None:
                        break
                    conn.probe_sock.settimeout(left)
                    try:
                        chunk = response.read1(min(_CHUNK, budget - received))
                    except TimeoutError:
                        break
                    if not chunk:
                        break
                    received += len(chunk)
                return Probe(url, received, time.monotonic() - start)
            finally:
                conn.close()
        return Probe(url, received, time.monotonic() - start, f"more than {_MAX_REDIRECTS} redirects")
    except TimeoutError:
        return Probe(url, received, time.monotonic() - start)
    except (OSError, http.client.HTTPException) as exc:
        return Probe(url, received, time.monotonic() - start, str(exc) or type(exc).__name__)


def _relative(uri: str, list_path: Path, mirrors: "list[Mirror]") -> "str | None":
    # The archive's path under a mirror: apt prints a mirror-list source as mirror+file:<list>/<path>.
    for base in (f"mirror+file:{list_path}/", *(mirror.uri.rstrip("/") + "/" for mirror in mirrors)):
        if uri.startswith(base):
            return uri[len(base) :]
    return None


def _kb(rate: float) -> str:
    return "inf" if rate == float("inf") else f"{rate / 1000:.0f} kB/s"


def check(planned: "list[Planned]", have: "set[str]", list_path: Path, *, cap_s: float, min_rate: float, force: bool = False, fetcher: "Fetcher" = fetch) -> "str | None":
    # The mirror list with the slow mirrors ahead of the first healthy one dropped, or None to leave it as it is.
    # With no healthy mirror the fastest measured stays first; the list keeps that one and all after it, never empty.
    remaining = [item for item in planned if item.file not in have]
    if not remaining and not force:
        print("== every planned archive came from the cache: no mirror check", flush=True)
        return None
    if not list_path.is_file():
        warn(f"{list_path} does not exist: no mirror check")
        return None
    text = list_path.read_text(encoding="utf-8")
    print(f"== {list_path}:\n{text.rstrip()}", flush=True)
    mirrors = parse_mirror_list(text)
    if mirrors is None:
        warn(f"{list_path} is in a form this check does not recognise: left unchanged")
        return None
    candidates = [(item, rel) for item in remaining if (rel := _relative(item.uri, list_path, mirrors))]
    if not candidates and force:
        candidates = [(item, rel) for item in planned if (rel := _relative(item.uri, list_path, mirrors))]
    if not candidates:
        print(f"== no planned archive comes from {list_path}: no mirror check", flush=True)
        return None
    budget = int(cap_s * min_rate)
    large = [pair for pair in candidates if pair[0].size >= budget]
    item, rel = min(large, key=lambda pair: pair[0].size) if large else max(candidates, key=lambda pair: pair[0].size)
    want = min(budget, item.size)
    ordered = apt_order(mirrors)
    measured: list[tuple[Mirror, Probe]] = []
    chosen = None
    for mirror in ordered:
        probe = fetcher(mirror.uri.rstrip("/") + "/" + rel, cap_s=cap_s, budget=want)
        healthy = not probe.error and probe.received >= want and probe.rate >= min_rate
        verdict = "healthy" if healthy else f"slow (healthy is {_kb(min_rate)} or more)"
        reason = f" - {probe.error}" if probe.error else ""
        print(f"== probe {probe.url}: {probe.received} of {want} bytes in {probe.seconds:.2f} s = {_kb(probe.rate)}, {verdict}{reason}", flush=True)
        measured.append((mirror, probe))
        if healthy:
            chosen = mirror
            break
    if chosen is None:
        answered = [(mirror, probe) for mirror, probe in measured if probe.received > 0]
        if not answered:
            warn(f"no mirror in {list_path} answered the probe: left unchanged")
            return None
        chosen = max(answered, key=lambda pair: pair[1].rate)[0]
        warn(f"no mirror in {list_path} reached {_kb(min_rate)}: the fastest measured, {chosen.uri}, goes first")
    dropped = ordered[: ordered.index(chosen)]
    if not dropped:
        return None
    warn(f"dropped {', '.join(mirror.uri for mirror in dropped)} from {list_path} for the rest of this job: apt fetches from {chosen.uri}")
    return without(text, dropped)


def _cli_plan(args: argparse.Namespace) -> int:
    planned, unparsed = parse_print_uris(args.uris.read_text(encoding="utf-8"))
    for line in unparsed:
        warn(f"an apt-get --print-uris line this reader does not know, left out of the plan: {line}")
    write_manifest(args.manifest, planned)
    uncached = [item.file for item in planned if not item.sha256]
    if uncached:
        warn(f"no SHA-256 in the index for {', '.join(uncached)}: never cached")
    size = sum(item.size for item in planned)
    print(f"== {len(planned)} archives to fetch, {size} bytes", flush=True)
    emit(args.github_output, key=cache_key(args.key_prefix, planned) if planned else "", restore_prefix=args.key_prefix, planned=len(planned))
    return 0


def _cli_dry_run_packages(args: argparse.Namespace) -> int:
    names = dry_run_packages(args.dry_run.read_text(encoding="utf-8"))
    if names is None:
        # stdout carries only the names, so the caller's $(...) never takes a message for one.
        print(f"{args.dry_run}: Playwright's dry-run output is in a form this reader does not know", file=sys.stderr)
        return 1
    print(" ".join(names), flush=True)
    return 0


def _cli_copy_in(args: argparse.Namespace) -> int:
    planned = read_manifest(args.manifest)
    keep = copy_in(planned, args.cache_dir)
    args.list.write_bytes(b"".join(str(path).encode() + b"\0" for path in keep))
    print(f"== {len(keep)} of {len(planned)} archives from the cache", flush=True)
    emit(args.github_output, restored=len(keep), remaining=len(planned) - len(keep))
    return 0


def _cli_check(args: argparse.Namespace) -> int:
    planned = read_manifest(args.manifest)
    have = {Path(entry.decode()).name for entry in args.have.read_bytes().split(b"\0") if entry} if args.have.is_file() else set()
    new_text = check(planned, have, args.mirror_list, cap_s=args.cap_s, min_rate=args.min_bytes_per_s, force=args.force)
    if new_text is not None:
        args.out.write_text(new_text, encoding="utf-8")
        print(f"== {args.mirror_list} from here on:\n{new_text.rstrip()}", flush=True)
    return 0


def _cli_copy_out(args: argparse.Namespace) -> int:
    planned = read_manifest(args.manifest)
    copied, missing = copy_out(planned, args.archives, args.cache_dir)
    cacheable = sum(1 for item in planned if item.sha256)
    print(f"== {copied} archives copied to {args.cache_dir}, {missing} of {cacheable} missing", flush=True)
    emit(args.github_output, complete=str(bool(cacheable) and missing == 0).lower(), copied=copied)
    return 0


def main(argv: "list[str] | None" = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    plan = commands.add_parser("plan", help="the manifest and cache key of an apt-get --print-uris listing")
    plan.add_argument("--uris", type=Path, required=True)
    plan.add_argument("--manifest", type=Path, required=True)
    plan.add_argument("--key-prefix", required=True)
    dry = commands.add_parser("dry-run-packages", help="the package names of npx playwright install-deps --dry-run")
    dry.add_argument("--dry-run", type=Path, required=True)
    copy = commands.add_parser("copy-in", help="the NUL-separated list of cached archives that match the index")
    copy.add_argument("--manifest", type=Path, required=True)
    copy.add_argument("--cache-dir", type=Path, required=True)
    copy.add_argument("--list", type=Path, required=True)
    probe = commands.add_parser("check", help="probe the mirror list's mirrors and write the list apt should use")
    probe.add_argument("--manifest", type=Path, required=True)
    probe.add_argument("--have", type=Path, required=True)
    probe.add_argument("--mirror-list", type=Path, required=True)
    probe.add_argument("--out", type=Path, required=True)
    probe.add_argument("--cap-s", type=float, default=PROBE_CAP_S)
    probe.add_argument("--min-bytes-per-s", type=float, default=MIN_BYTES_PER_S)
    probe.add_argument("--force", action="store_true", help="probe even when the cache holds every planned archive")
    out = commands.add_parser("copy-out", help="copy what apt fetched into the cache folder")
    out.add_argument("--manifest", type=Path, required=True)
    out.add_argument("--archives", type=Path, required=True)
    out.add_argument("--cache-dir", type=Path, required=True)
    for sub in (plan, copy, out):
        sub.add_argument("--github-output", type=Path)
    args = parser.parse_args(argv)
    handlers = {"plan": _cli_plan, "dry-run-packages": _cli_dry_run_packages, "copy-in": _cli_copy_in, "check": _cli_check, "copy-out": _cli_copy_out}
    return handlers[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
