"""M.PROC.024 (2): the twin suite per derived device on the 2**30 build, the counter's wrap inside Run 11's cycle window.
Usage: ticks30_twin.py <out dir> <toolchain copy whose build-standard is build-ticks30> <ticks30 binary> [device ...]; resumable.
Per device: place (Run 11 alone, the counter 10**8 ms from its wrap, so each MEM_SAMPLE tick reads ms since the first read), then both stages."""

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PERIOD = 1 << 30
FAR_MS = 10**8  # the place run's counter starts this far from its wrap: no wrap inside it, every tick an offset from the first read
MARKERS = re.compile(r"MemoryError|memory allocation failed")
SAMPLE = re.compile(r"^MEM_SAMPLE (\d+) (\d+)$", re.MULTILINE)
WINDOW = re.compile(r"Run 11 memory trend: .* samples=(\d+)")
STAGE_DIRS = {"-1": "gc_threshold_neg1", "32768": "gc_threshold_32768"}


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _records(out: Path) -> list[dict[str, object]]:
    path = out / "results.jsonl"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()] if path.is_file() else []


def _append(out: Path, rec: dict[str, object]) -> None:
    with (out / "results.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec) + "\n")
    sys.stdout.write(json.dumps(rec) + "\n")
    sys.stdout.flush()


def _suite(device: str, stage: str, wrap_ms: int, toolchain: Path, log: Path, only: list[str]) -> tuple[int, float]:
    env = dict(os.environ, PICO_TOOLCHAIN_DIR=str(toolchain), TICKS30_WRAP_IN_MS=str(wrap_ms))
    cmd = ["scripts/run_digital_twin_ci.sh", device, "--gc-threshold", stage, "--part", "suite", *only]
    t0 = time.monotonic()
    with log.open("w", encoding="utf-8") as f:
        rc = subprocess.run(cmd, cwd=REPO, env=env, stdout=f, stderr=subprocess.STDOUT, check=False).returncode  # noqa: S603  # our own argv, no shell
    return rc, round(time.monotonic() - t0, 1)


def _soak(stage_dir: Path, suite_log: str) -> dict[str, object]:
    # Run 11's samples, its window (the suite's own sample count: the window is the log's tail, then the shutdown's few),
    # and where the counter wrapped among them; the ticks either side of it read the period from inside the run.
    text = (stage_dir / "run11_soak.log").read_text(encoding="utf-8", errors="replace")
    ticks = [int(m.group(1)) for m in SAMPLE.finditer(text)]
    found = WINDOW.findall(suite_log)
    n = int(found[-1]) if found else 0
    wraps = [i for i in range(1, len(ticks)) if ticks[i] < ticks[i - 1]]
    rec: dict[str, object] = {"samples": len(ticks), "window": n, "wraps": len(wraps)}
    if wraps:
        i = wraps[0]
        rec.update({"wrap_index": i, "before": ticks[i - 1], "after": ticks[i], "step_ms": ticks[i] + PERIOD - ticks[i - 1], "pos_in_window": round((i - (len(ticks) - n)) / n, 3) if n else None})
    rec["first"], rec["last"] = (ticks[0], ticks[-1]) if ticks else (None, None)
    return rec


def place(device: str, out: Path, toolchain: Path) -> int:
    log = out / "logs" / f"place_{device}.log"
    rc, wall = _suite(device, "-1", FAR_MS, toolchain, log, ["--only", "11"])
    stage_dir = REPO / "digital_twin_ci_logs" / device / STAGE_DIRS["-1"]
    shutil.copy2(stage_dir / "run11_soak.log", out / "logs" / f"place_{device}_run11_soak.log")
    soak = _soak(stage_dir, log.read_text(encoding="utf-8", errors="replace"))
    text = (stage_dir / "run11_soak.log").read_text(encoding="utf-8", errors="replace")
    offsets = [int(m.group(1)) - (PERIOD - FAR_MS) for m in SAMPLE.finditer(text)]
    n = int(str(soak["window"]))
    if not n or n > len(offsets):
        _append(out, {"phase": "place-failed", "device": device, "rc": rc, "wall_s": wall, **soak})
        msg = f"place {device}: no Run 11 window in {log}"
        raise SystemExit(msg)
    start, end = offsets[len(offsets) - n], offsets[-1]
    wrap_ms = (start + end) // 2
    _append(out, {"phase": "place", "device": device, "rc": rc, "wall_s": wall, "window_start_ms": start, "window_end_ms": end, "wrap_ms": wrap_ms, **soak})
    return wrap_ms


def run(device: str, stage: str, wrap_ms: int, out: Path, toolchain: Path, ticks30: Path) -> None:
    binary = toolchain / "micropython/ports/unix/build-standard/micropython"
    sha_before = _sha(binary)
    log = out / "logs" / f"suite_{device}_{STAGE_DIRS[stage]}.log"
    rc, wall = _suite(device, stage, wrap_ms, toolchain, log, [])
    suite_log = log.read_text(encoding="utf-8", errors="replace")
    stage_dir = REPO / "digital_twin_ci_logs" / device / STAGE_DIRS[stage]
    kept = out / "logs" / f"{device}_{STAGE_DIRS[stage]}"
    shutil.rmtree(kept, ignore_errors=True)
    shutil.copytree(stage_dir, kept, ignore=shutil.ignore_patterns("state*"))
    marker_hits = sorted(str(p.relative_to(kept)) for p in kept.rglob("*.log") if MARKERS.search(p.read_text(encoding="utf-8", errors="replace")))
    rec: dict[str, object] = {
        "phase": "suite", "device": device, "stage": stage, "wrap_ms": wrap_ms, "rc": rc, "wall_s": wall, "result": re.findall(r"^Result: \w+", suite_log, re.MULTILINE),
        "fails": len(re.findall(r"^FAIL", suite_log, re.MULTILINE)), "oks": len(re.findall(r"^OK:", suite_log, re.MULTILINE)), "markers_in": marker_hits + (["suite log"] if MARKERS.search(suite_log) else []),
        "rebuilt": "rebuilding the Unix ports" in suite_log, "binary_is_ticks30": sha_before == _sha(binary) == _sha(ticks30), "launches_copy": str(binary) in suite_log,
    }
    rec.update(_soak(stage_dir, suite_log))
    _append(out, rec)


def main() -> int:
    out, toolchain, ticks30 = (Path(a).resolve() for a in sys.argv[1:4])
    (out / "logs").mkdir(parents=True, exist_ok=True)
    devices = sys.argv[4:] or subprocess.run(["/bin/bash", "-c", "source scripts/_devices.sh; derived_devices"], cwd=REPO, check=True, capture_output=True, text=True).stdout.split()
    for device in devices:
        recs = _records(out)
        placed = [r for r in recs if r["phase"] == "place" and r["device"] == device]
        wrap_ms = int(str(placed[-1]["wrap_ms"])) if placed else place(device, out, toolchain)
        for stage in STAGE_DIRS:
            if not any(r["phase"] == "suite" and r["device"] == device and r["stage"] == stage for r in recs):
                run(device, stage, wrap_ms, out, toolchain, ticks30)
    return 0


if __name__ == "__main__":
    sys.exit(main())
