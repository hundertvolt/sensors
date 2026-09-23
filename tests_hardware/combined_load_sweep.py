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
PEAK_LOAD_S = 60.0
PUT_INTERVAL_S = 3.0  # the hammer test's own cadence (bench/test_memory_stress_bench.py)
_THRESHOLD_LINE = "gc.threshold(-1)\n"
_MARGIN_LINE = "_COLLECT_BEFORE_SAMPLE = False"
_PEAK_LINE = "_PEAK_SAMPLE_MS = 0"


def _reference_lengths(ip: str) -> dict[str, int]:
    # Idle fetches, retried until a 200 whose body matches its Content-Length: every boot of the device
    # script drops and rejoins WLAN at uptime ~6 s, and a fetch caught by it once came back 0 B (§10.10).
    lengths: dict[str, int] = {}
    for path in STATIC:
        for _ in range(10):
            try:
                response = http_client.fetch(ip, 80, "GET", path, timeout_s=30.0)
            except Exception as e:
                print(f"   reference fetch {path} retry: {e!r}")
                time.sleep(2.0)
                continue
            framed = response.headers.get("Content-Length") == str(len(response.body))
            if response.status_code == 200 and response.body and framed:
                lengths[path] = len(response.body)
                break
            print(f"   reference fetch {path} retry: status {response.status_code}, {len(response.body)} B, Content-Length {response.headers.get('Content-Length')}")
            time.sleep(2.0)
    return lengths


def _one(ip: str, path: str, reference: dict[str, int]) -> str:
    """'ok', or why not. A static body must match its idle length: pre-fix, a truncated page was a 200."""
    try:
        response = http_client.fetch(ip, 80, "GET", path, timeout_s=30.0)
    except Exception as e:
        return "refused" if http_client.is_ceiling_close(e) else f"{type(e).__name__}:{getattr(e, 'reason', e)!r}"[:80]
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
    reference = _wait_until_serving(ip)
    served = refused = 0
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
            elif outcome == "refused":
                refused += 1
            else:
                key = f"{PATHS[i % len(PATHS)]} {outcome or 'hang'} (round {round_index})"
                failures[key] = failures.get(key, 0) + 1
        time.sleep(0.5)
    result.update(reference=reference, served=served, refused=refused, failures=failures)


def _wait_until_serving(ip: str) -> dict[str, int]:
    for _ in range(600):  # the device script's own boot has to start serving first
        try:
            if http_client.fetch(ip, 80, "GET", "/status", timeout_s=3.0).status_code == 200:
                break
        except Exception:
            time.sleep(1.0)
    time.sleep(2.0)
    return _reference_lengths(ip)


def _drive_peak(ip: str, n: int, result: dict[str, object]) -> None:
    """--peak: N threads back to back for PEAK_LOAD_S, the full path mix, and thread 0 swaps one GET for
    the hammer test's dispatch-only SGP40 reset every 3 s - saturated admission plus forced sensor work."""
    reference = _wait_until_serving(ip)
    stop = threading.Event()
    lock = threading.Lock()
    outcomes: dict[str, int] = {}

    def worker(index: int) -> None:
        position, next_put = index, time.monotonic() + PUT_INTERVAL_S
        while not stop.is_set():
            if index == 0 and time.monotonic() >= next_put:
                next_put += PUT_INTERVAL_S
                key = "PUT /sensors " + _put_reset(ip)
            else:
                path = PATHS[position % len(PATHS)]
                position += 1
                key = f"{path} {_one(ip, path, reference)}"
            with lock:
                outcomes[key] = outcomes.get(key, 0) + 1

    threads = [threading.Thread(target=worker, args=(i,), daemon=True) for i in range(n)]
    for thread in threads:
        thread.start()
    time.sleep(PEAK_LOAD_S)
    stop.set()
    for thread in threads:
        thread.join(timeout=40.0)
    total = sum(outcomes.values())
    refused = sum(v for k, v in outcomes.items() if k.endswith(" refused"))
    failed = {k: v for k, v in outcomes.items() if not k.endswith((" ok", " refused"))}
    result.update(reference=reference, served=total - refused - sum(failed.values()), total=total, refused=refused, failures=failed)


def _put_reset(ip: str) -> str:
    try:
        response = http_client.fetch(ip, 80, "PUT", "/sensors", {"SGP40": {"SGPResetVOC": True}}, timeout_s=30.0)
    except Exception as e:
        return "refused" if http_client.is_ceiling_close(e) else f"{type(e).__name__}:{getattr(e, 'reason', e)!r}"[:80]
    return "ok" if response.status_code == 200 else f"status{response.status_code}"


def _peak_lines(output: str) -> list[str]:
    """The device's post-GC low-water figures (serving_stability_under_combined_load.py's _peak_sampler)."""
    lines = [line.strip() for line in output.splitlines() if line.startswith(("PEAK_SUMMARY", "PEAK_AT"))]
    new_min = [line for line in output.splitlines() if line.startswith("PEAK_NEW_MIN")]
    if new_min:  # the largest free block at the overall minimum: mem_info() follows that line, in blocks
        tail = output.split(new_min[-1], 1)[1]
        block = next((line for line in tail.splitlines() if "max free sz" in line), "")
        lines.insert(0, f"at the minimum ({new_min[-1].split(' ', 1)[1]}): {block.strip()}")
    return lines or ["peak: no PEAK_SUMMARY in the device output"]


def _margin_line(output: str) -> str:
    """Post-collect free heap from a --margin run: settled idle (the window's last third, after the load)
    against the load window, i.e. every sample up to the last one below 95 % of that idle."""
    samples = [m for label, m in sorted(heap_map.parse_labelled(output).items()) if label.startswith("t")]
    if len(samples) < 6:
        return "margin: too few post-collect samples captured"
    idle = sorted(m.free_bytes for m in samples[-len(samples) // 3 :])[len(samples) // 6]
    last_loaded = max((i for i, m in enumerate(samples) if m.free_bytes < 0.95 * idle), default=-1)
    if last_loaded < 0:
        return f"margin: no sample below 95 % of the settled idle {idle} B - no load window found"
    load = samples[: last_loaded + 1]
    frees = sorted(m.free_bytes for m in load)
    runs = sorted(m.largest_free_run for m in load)
    total = samples[0].total_bytes

    def pct(value: int) -> str:
        return f"{value} B ({100 * value / total:.1f} %)"

    return (
        f"margin (post-collect, heap {total} B): settled idle {pct(idle)} | under load min {pct(frees[0])}, "
        f"median {pct(frees[len(frees) // 2])} | largest free run min {runs[0]} B, median {runs[len(runs) // 2]} B | load samples {len(load)} of {len(samples)}"
    )


def run_level(board: Board, bench: BenchBridge, ip: str, script: Path, n: int, raw_dir: Path | None, *, margin: bool = False, peak: bool = False) -> bool:
    result: dict[str, object] = {}
    driver = threading.Thread(target=_drive_peak if peak else _drive, args=(ip, n, result), daemon=True)
    driver.start()
    output = board.run_isolated(script, timeout_s=260.0)
    driver.join(timeout=120.0)
    if raw_dir is not None:
        (raw_dir / f"combined_load_N{n}_{int(time.time())}.txt").write_text(output)
    threshold = next((line for line in output.splitlines() if line.startswith("GC_THRESHOLD=")), "GC_THRESHOLD=?")
    allocation_lines = [line.strip() for line in output.splitlines() if any(marker in line for marker in MEMORY_ERROR_MARKERS)]
    try:  # one torn heap-map capture once cost a whole level's host tally (§10.10): report it, don't crash
        samples = [m for label, m in sorted(heap_map.parse_labelled(output).items()) if label.startswith("t")]
        worst_run = min((m.largest_free_run for m in samples), default=-1)
    except heap_map.HeapMapError as e:
        print(f"     heap map unreadable, worst free run not measured: {e}")
        worst_run = -1
    served, total = int(str(result.get("served", 0))), int(str(result.get("total", n * ROUNDS)))
    refused = int(str(result.get("refused", 0)))  # a reject-when-full close at the ceiling: expected under saturation, never a failure
    failures = result.get("failures", {})
    failed = total - served - refused
    rate = f"{100 * failed / total:.2f} %" if total else "n/a"
    stable = failed == 0 and not allocation_lines and not driver.is_alive()
    print(
        f"N={n:2d} {threshold} | {'STABLE' if stable else 'UNSTABLE'} | complete {served}/{total} | refused {refused} (expected) | failed {failed} ({rate}) | "
        f"device allocation-failure lines {len(allocation_lines)} | worst largest free run {worst_run} B | reference {result.get('reference')}",
    )
    if peak:
        for line in _peak_lines(output):
            print(f"     {line}")
        device_rejected = next((part.split("=", 1)[1] for line in output.splitlines() if line.startswith("PEAK_SUMMARY") for part in line.split() if part.startswith("rejected=")), "?")
        print(f"     refusals cross-check: host counted {refused}, device rejected {device_rejected} (a gap means a reset the ceiling did not cause)")
    if margin and not peak:  # --peak --margin reports through _peak_lines(); the maps it summarises are not taken
        try:
            print(f"     {_margin_line(output)}")
        except heap_map.HeapMapError as e:
            print(f"     margin not measured, a heap map was unreadable: {e}")
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
    parser.add_argument("--peak", action="store_true", help="saturated load (N threads back to back for 60 s, the SGP40 reset PUT every 3 s) and the device's non-collecting post-GC low-water sampler; its verdict IS evidence")
    parser.add_argument("--margin", action="store_true", help="gc.collect() before each heap sample and report the post-collect free heap; instrumentation - its STABLE/UNSTABLE is not evidence")
    args = parser.parse_args()
    if not args.ip:
        parser.error("the DUT's IP is needed: --ip or $DUT_IP")
    source = DEVICE_SCRIPT.read_text()
    if _THRESHOLD_LINE not in source:
        parser.error(f"{DEVICE_SCRIPT.name} no longer carries the line this driver substitutes")
    variant = Path(os.environ.get("TMPDIR", "/tmp")) / f"combined_load_threshold_{args.threshold}.py"  # noqa: S108 - a scratch copy of a device script
    if _MARGIN_LINE not in source:
        parser.error(f"{DEVICE_SCRIPT.name} no longer carries the line --margin substitutes")
    source = source.replace(_THRESHOLD_LINE, f"gc.threshold({args.threshold})\n", 1)
    if args.margin:
        source = source.replace(_MARGIN_LINE, "_COLLECT_BEFORE_SAMPLE = True", 1)
    if args.peak:
        if _PEAK_LINE not in source:
            parser.error(f"{DEVICE_SCRIPT.name} no longer carries the line --peak substitutes")
        source = source.replace(_PEAK_LINE, f"_PEAK_SAMPLE_MS = {100 if args.margin else 20}", 1)
    variant.write_text(source)
    board, bench = Board(), BenchBridge()
    verdicts = [run_level(board, bench, args.ip, variant, n, args.raw_dir, margin=args.margin, peak=args.peak) for n in args.levels]
    return 0 if all(verdicts) else 1


if __name__ == "__main__":
    sys.exit(main())
