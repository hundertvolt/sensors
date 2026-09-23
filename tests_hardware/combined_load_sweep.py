"""Per-boot combined-load sweep (BENCH_SITTING_2026-09-23_HANDOVER.md §10.6): for each level N, a fresh
boot of the real task graph at a chosen gc.threshold, 12 rounds of N concurrent GETs from the host, and
a verdict of stable = every body complete AND zero allocation-failure lines on the device."""

from __future__ import annotations

import argparse
import os
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import heap_map
import http_client
from bench_control import BenchBridge
from harness import MEMORY_ERROR_MARKERS, Board

DEVICE_SCRIPT = Path(__file__).resolve().parent / "device_scripts" / "serving_stability_under_combined_load.py"
# The heavy end of the real surface plus the cheap routes: both streaming endpoints twice, the static
# page and the script every page load fetches, so the mix is realistic rather than worst-case only.
PATHS = ("/status", "/sensors", "/", "/measurements", "/status", "/networking", "/sensors", "/system", "/js/app.js")
STATIC = ("/", "/js/app.js")
ROUNDS = 12
_THRESHOLD_LINE = "gc.threshold(-1)\n"


def _reference_lengths(ip: str) -> dict[str, int]:
    # Idle fetches, retried: the first request after boot can land on a board still settling.
    lengths: dict[str, int] = {}
    for path in STATIC:
        for _ in range(10):
            try:
                lengths[path] = len(http_client.fetch(ip, 80, "GET", path, timeout_s=30.0).body)
                break
            except Exception as e:
                print(f"   reference fetch {path} retry: {e!r}")
                time.sleep(2.0)
    return lengths


def _one(ip: str, path: str, reference: dict[str, int]) -> str:
    """'ok', or why not. A static body must match its idle length: pre-fix, a truncated page was a 200."""
    try:
        response = http_client.fetch(ip, 80, "GET", path, timeout_s=30.0)
    except Exception as e:
        return f"{type(e).__name__}:{getattr(e, 'reason', e)!r}"[:80]
    if response.status_code != 200:
        return f"status{response.status_code}"
    if path in STATIC:
        return "ok" if len(response.body) == reference.get(path, -1) else f"truncated{len(response.body)}"
    try:
        response.json()
    except ValueError:
        return "badjson"
    return "ok"


def _drive(ip: str, n: int, result: dict[str, object]) -> None:
    for _ in range(600):  # the device script's own boot has to start serving first
        try:
            if http_client.fetch(ip, 80, "GET", "/status", timeout_s=3.0).status_code == 200:
                break
        except Exception:
            time.sleep(1.0)
    time.sleep(2.0)
    reference = _reference_lengths(ip)
    served = 0
    failures: dict[str, int] = {}
    for round_index in range(ROUNDS):
        outcomes = [""] * n

        def request(i: int, outcomes: list[str] = outcomes) -> None:
            outcomes[i] = _one(ip, PATHS[i % len(PATHS)], reference)

        threads = [threading.Thread(target=request, args=(i,)) for i in range(n)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=40.0)
        for i, outcome in enumerate(outcomes):
            if outcome == "ok":
                served += 1
            else:
                key = f"{PATHS[i % len(PATHS)]} {outcome or 'hang'} (round {round_index})"
                failures[key] = failures.get(key, 0) + 1
        time.sleep(0.5)
    result.update(reference=reference, served=served, failures=failures)


def run_level(board: Board, bench: BenchBridge, ip: str, script: Path, n: int, raw_dir: Path | None) -> bool:
    result: dict[str, object] = {}
    driver = threading.Thread(target=_drive, args=(ip, n, result), daemon=True)
    driver.start()
    output = board.run_isolated(script, timeout_s=260.0)
    driver.join(timeout=120.0)
    if raw_dir is not None:
        (raw_dir / f"combined_load_N{n}_{int(time.time())}.txt").write_text(output)
    threshold = next((line for line in output.splitlines() if line.startswith("GC_THRESHOLD=")), "GC_THRESHOLD=?")
    allocation_lines = [line.strip() for line in output.splitlines() if any(marker in line for marker in MEMORY_ERROR_MARKERS)]
    samples = [m for label, m in sorted(heap_map.parse_labelled(output).items()) if label.startswith("t")]
    worst_run = min((m.largest_free_run for m in samples), default=-1)
    served = result.get("served", 0)
    failures = result.get("failures", {})
    stable = served == n * ROUNDS and not allocation_lines and not driver.is_alive()
    print(
        f"N={n:2d} {threshold} | {'STABLE' if stable else 'UNSTABLE'} | complete {served}/{n * ROUNDS} | "
        f"device allocation-failure lines {len(allocation_lines)} | worst largest free run {worst_run} B | reference {result.get('reference')}",
    )
    for key, count in sorted(failures.items()) if isinstance(failures, dict) else ():
        print(f"     {count} x {key}")
    for line in allocation_lines[:6]:
        print(f"     device: {line}")
    bench.kick_all_stations()  # run_isolated() leaves main.py stopped; put the board back each level
    board.hard_reset()
    time.sleep(45.0)
    return stable


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("levels", type=int, nargs="+", help="concurrency levels, one fresh boot each; repeat a level to repeat its run")
    parser.add_argument("--threshold", type=int, default=-1, help="gc.threshold for the run (default -1, MicroPython's own reactive default)")
    parser.add_argument("--ip", default=os.environ.get("DUT_IP"), help="the DUT's address (default $DUT_IP)")
    parser.add_argument("--raw-dir", type=Path, default=None, help="save each level's full device output here")
    args = parser.parse_args()
    if not args.ip:
        parser.error("the DUT's IP is needed: --ip or $DUT_IP")
    source = DEVICE_SCRIPT.read_text()
    if _THRESHOLD_LINE not in source:
        parser.error(f"{DEVICE_SCRIPT.name} no longer carries the line this driver substitutes")
    variant = Path(os.environ.get("TMPDIR", "/tmp")) / f"combined_load_threshold_{args.threshold}.py"  # noqa: S108 - a scratch copy of a device script
    variant.write_text(source.replace(_THRESHOLD_LINE, f"gc.threshold({args.threshold})\n", 1))
    board, bench = Board(), BenchBridge()
    verdicts = [run_level(board, bench, args.ip, variant, n, args.raw_dir) for n in args.levels]
    return 0 if all(verdicts) else 1


if __name__ == "__main__":
    sys.exit(main())
