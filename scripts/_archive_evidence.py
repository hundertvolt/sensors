#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Moves a runner's evidence into build/archive/<runner>/<UTC timestamp>/ and keeps the newest three
runs per runner (SSD wear; owner, 2026-09-26)."""

# Usage: _archive_evidence.py --runner NAME [--keep N] [--new-dir] [PATH ...]
# --new-dir creates and prints an empty run directory; otherwise the existing PATHs are moved into
# one new run directory, which is printed (nothing is printed when no PATH exists). Usage errors exit 2.

import argparse
import re
import shutil
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
_RUNNER = re.compile(r"^[a-z0-9_]+$")
_RUN_DIR = re.compile(r"^(\d{8}T\d{6}Z)(?:-(\d+))?$")


def _timestamp() -> str:
    return time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())


def _check(runner: str, keep: int) -> None:
    if not _RUNNER.match(runner):
        raise ValueError(f"runner name {runner!r} must match {_RUNNER.pattern}")
    if keep < 1:
        raise ValueError(f"keep must be at least 1, not {keep}")


def _runs(runner_dir: Path) -> list[tuple[tuple[str, int], Path]]:
    # The run directories, oldest first; anything not named like a run is never one.
    runs = []
    for entry in runner_dir.iterdir():
        match = _RUN_DIR.match(entry.name)
        if match and entry.is_dir() and not entry.is_symlink():
            runs.append(((match.group(1), int(match.group(2) or 0)), entry))
    return sorted(runs)


def _prune(runner_dir: Path, keep: int, new: Path) -> None:
    # The new run is always kept, so a host clock stepped backwards cannot prune it on arrival.
    older = [entry for _, entry in _runs(runner_dir) if entry != new]
    for entry in older[: max(0, len(older) - (keep - 1))]:
        shutil.rmtree(entry)


def new_run_dir(runner: str, *, keep: int = 3, root: Path = REPO_ROOT / "build" / "archive") -> Path:
    # Creates <root>/<runner>/<UTC timestamp>[-n]/ and prunes that runner's runs to the newest `keep`.
    _check(runner, keep)
    runner_dir = root / runner
    runner_dir.mkdir(parents=True, exist_ok=True)
    stamp = _timestamp()
    # A second run in the same second takes the next suffix after every existing one, never a pruned gap.
    same = [n for (ts, n), _ in _runs(runner_dir) if ts == stamp]
    n = max(same) + 1 if same else 0
    while True:
        run_dir = runner_dir / (f"{stamp}-{n}" if n else stamp)
        try:
            run_dir.mkdir()
            break
        except FileExistsError:
            n += 1
    _prune(runner_dir, keep, run_dir)
    return run_dir


def archive(runner: str, paths: list[Path], *, keep: int = 3, root: Path = REPO_ROOT / "build" / "archive") -> Path | None:
    # Moves every existing path into one new run directory and returns it; None when none exists.
    _check(runner, keep)
    existing = [path for path in paths if path.exists() or path.is_symlink()]
    if not existing:
        return None
    run_dir = new_run_dir(runner, keep=keep, root=root)
    for path in existing:
        target = run_dir / path.name
        n = 0
        while target.exists():
            n += 1
            target = run_dir / f"{path.name}-{n}"
        shutil.move(str(path), target)
    return run_dir


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--runner", required=True, help="archive name, matching [a-z0-9_]+ (one keep-3 history per name)")
    parser.add_argument("--keep", type=int, default=3, help="runs kept per runner (default 3)")
    parser.add_argument("--new-dir", action="store_true", help="create and print an empty run directory instead of moving PATHs")
    parser.add_argument("paths", nargs="*", type=Path, metavar="PATH", help="evidence to move; a missing PATH is skipped")
    args = parser.parse_args(argv)
    try:
        _check(args.runner, args.keep)
    except ValueError as exc:
        parser.error(str(exc))  # exits 2
    if args.new_dir:
        if args.paths:
            parser.error("--new-dir takes no PATH")
        print(new_run_dir(args.runner, keep=args.keep))
        return 0
    run_dir = archive(args.runner, args.paths, keep=args.keep)
    if run_dir is not None:
        print(run_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
