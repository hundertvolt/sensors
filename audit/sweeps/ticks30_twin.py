"""M.PROC.024 (2): the twin suite per derived device on the 2**30 build, the counter's wrap inside Run 11's cycle window.
Usage: ticks30_twin.py <out dir> <toolchain copy whose build-standard is build-ticks30> <ticks30 binary> [device ...]; resumable.
Per device: place (Run 11 alone, the counter 10**8 ms from its wrap), once a prove (Run 11 alone, wrapping), then both stages; a run whose wrap falls outside the window (a placement miss, kept, never counted) gets a fresh place run at its stage and runs again, the wrap mid-way through the span every window observed at that stage shares."""

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
OWN_GATE = re.compile(r"^OK: .*carries none of \('MemoryError', 'memory allocation failed'\)$")  # the suite's own passing marker check names both
SAMPLE = re.compile(r"^MEM_SAMPLE (\d+) (\d+)$", re.MULTILINE)
WINDOW = re.compile(r"Run 11 memory trend: .* samples=(\d+)")
STAGE_DIRS = {"-1": "gc_threshold_neg1", "32768": "gc_threshold_32768"}
CRC16_PART = "== Running Run 3 on the CRC16-derived "  # scripts/run_digital_twin_ci.sh's line before a uart_link device's second part
STEP_MAX_MS = 1000  # the suite samples every 100 ms: a step across the wrap this close reads the 2**30 period from inside the run
HEAVY = frozenset({"micropython", "node"})
MAX_HEAVY = 4  # CHECKLIST 12: a twin suite starts only while at most 4 heavy processes run on the host
MAX_REPLACE = 3  # re-placement rounds per stage after a miss: each adds a place run, so the shared span only narrows
GATE_MAX_S = 7200  # the gate never starts a suite under load: past this it stops the sweep instead, resumable


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


def _heavy_count() -> int:
    count = 0
    for comm in Path("/proc").glob("[0-9]*/comm"):
        try:
            count += comm.read_text(encoding="utf-8").strip() in HEAVY
        except OSError:
            continue
    return count


def _gate() -> float:
    waited = 0.0
    while _heavy_count() > MAX_HEAVY:
        if waited >= GATE_MAX_S:
            msg = f"load gate: more than {MAX_HEAVY} heavy processes for {GATE_MAX_S} s, nothing started"
            raise SystemExit(msg)
        time.sleep(10)
        waited += 10
    return waited


def _suite(device: str, stage: str, wrap_ms: int, toolchain: Path, log: Path, only: list[str]) -> tuple[int, float, float]:
    waited = _gate()
    env = dict(os.environ, PICO_TOOLCHAIN_DIR=str(toolchain), TICKS30_WRAP_IN_MS=str(wrap_ms))
    cmd = ["scripts/run_digital_twin_ci.sh", device, "--gc-threshold", stage, "--part", "suite", *only]
    t0 = time.monotonic()
    with log.open("w", encoding="utf-8") as f:
        rc = subprocess.run(cmd, cwd=REPO, env=env, stdout=f, stderr=subprocess.STDOUT, check=False).returncode  # noqa: S603  # our own argv, no shell
    return rc, round(time.monotonic() - t0, 1), waited


def _soak(stage_dir: Path, suite_log: str) -> dict[str, object]:
    # Run 11's samples, its window (the suite's own sample count: the window is the log's tail, then the shutdown's few),
    # and where the counter wrapped among them; the ticks either side of it read the period from inside the run.
    text = (stage_dir / "run11_soak.log").read_text(encoding="utf-8", errors="replace")
    ticks = [int(m.group(1)) for m in SAMPLE.finditer(text)]
    found = WINDOW.findall(suite_log)
    n = int(found[-1]) if found else 0
    wraps = [i for i in range(1, len(ticks)) if ticks[i] < ticks[i - 1]]
    rec: dict[str, object] = {"samples": len(ticks), "window": n, "wraps": len(wraps), "step_ok": False, "in_window": False}
    if wraps:
        i = wraps[0]
        step = ticks[i] + PERIOD - ticks[i - 1]
        pos = round((i - (len(ticks) - n)) / n, 3) if n else None
        rec.update({"wrap_index": i, "before": ticks[i - 1], "after": ticks[i], "step_ms": step, "pos_in_window": pos, "step_ok": 0 < step <= STEP_MAX_MS, "in_window": pos is not None and 0 < pos < 1})
    rec["first"], rec["last"] = (ticks[0], ticks[-1]) if ticks else (None, None)
    return rec


def _evidence(binary: Path, ticks30: Path, sha_before: str, suite_log: str, logs: list[Path]) -> dict[str, object]:
    # That the suite ran the toolchain copy's binary, which is build-ticks30 before and after, unrebuilt; and every marker hit.
    hits = sorted(str(p) for p in logs if p.is_file() and MARKERS.search(p.read_text(encoding="utf-8", errors="replace")))
    return {
        "rebuilt": "rebuilding the Unix ports" in suite_log, "binary_is_ticks30": sha_before == _sha(binary) == _sha(ticks30), "launches_copy": str(binary) in suite_log,
        "markers_in": hits + [f"suite log: {line}" for line in suite_log.splitlines() if MARKERS.search(line) and not OWN_GATE.match(line)],
    }


def _clean(rec: dict[str, object]) -> bool:
    return rec["rc"] == 0 and not rec["rebuilt"] and bool(rec["binary_is_ticks30"]) and bool(rec["launches_copy"]) and not rec["markers_in"] and not rec.get("unscanned")


def _proven(rec: dict[str, object]) -> bool:
    return _clean(rec) and rec["wraps"] == 1 and bool(rec["step_ok"]) and bool(rec["in_window"])


def _passed(rec: dict[str, object]) -> bool:
    return rec["result"] == ["Result: PASS"] * int(str(rec.get("parts", 1))) and rec["fails"] == 0


def _green(rec: dict[str, object]) -> bool:
    return _proven(rec) and _passed(rec)


def _miss(rec: dict[str, object]) -> bool:
    # Clean and passing, but Run 11 crossed no wrap inside its window: the placement missed, so the run proves nothing either way.
    return _clean(rec) and _passed(rec) and not (rec["wraps"] == 1 and bool(rec["in_window"]))


def _binary(toolchain: Path) -> Path:
    return toolchain / "micropython/ports/unix/build-standard/micropython"


def place(device: str, out: Path, toolchain: Path, ticks30: Path, stage: str = "-1", phase: str = "place") -> int:
    tag = ("" if stage == "-1" else f"_{STAGE_DIRS[stage]}") + ("" if phase == "place" else "_re")
    log = out / "logs" / f"place_{device}{tag}.log"
    sha_before = _sha(_binary(toolchain))
    rc, wall, waited = _suite(device, stage, FAR_MS, toolchain, log, ["--only", "11"])
    stage_dir = REPO / "digital_twin_ci_logs" / device / STAGE_DIRS[stage]
    kept = out / "logs" / f"place_{device}{tag}_run11_soak.log"
    shutil.copy2(stage_dir / "run11_soak.log", kept)
    suite_log = log.read_text(encoding="utf-8", errors="replace")
    soak = _soak(stage_dir, suite_log)
    text = kept.read_text(encoding="utf-8", errors="replace")
    offsets = [int(m.group(1)) - (PERIOD - FAR_MS) for m in SAMPLE.finditer(text)]
    n = int(str(soak["window"]))
    base = {"device": device, "stage": stage, "rc": rc, "wall_s": wall, "load_wait_s": waited, **_evidence(_binary(toolchain), ticks30, sha_before, suite_log, [kept])}
    if rc or not n or n > len(offsets):
        _append(out, {"phase": "place-failed", **base, **soak})
        msg = f"place {device}: no Run 11 window in {log}"
        raise SystemExit(msg)
    start, end = offsets[len(offsets) - n], offsets[-1]
    wrap_ms = (start + end) // 2
    _append(out, {"phase": phase, **base, "window_start_ms": start, "window_end_ms": end, "wrap_ms": wrap_ms, **soak})
    return wrap_ms


def _window_ms(soak_log: Path, first: int, n: int) -> tuple[int, int] | None:
    # Run 11's window (its last n samples) in ms since the process's first counter read, which the build set to first.
    offs = [(int(m.group(1)) - first) % PERIOD for m in SAMPLE.finditer(soak_log.read_text(encoding="utf-8", errors="replace"))]
    return (offs[-n], offs[-1]) if 0 < n <= len(offs) else None


def observed(device: str, stage: str, out: Path) -> list[tuple[int, int]]:
    # Every Run 11 window seen at this stage: each place run's, and each suite run's own, read back from its kept soak log.
    wins: list[tuple[int, int]] = []
    for r in _records(out):
        if r["device"] != device or r.get("stage", "-1") != stage:
            continue
        if r["phase"] in {"place", "re-place"}:
            wins.append((int(str(r["window_start_ms"])), int(str(r["window_end_ms"]))))
        elif r["phase"] == "suite":
            w = _window_ms(out / "logs" / f"{device}_{STAGE_DIRS[stage]}{_tag(_attempt(r))}" / "run11_soak.log", PERIOD - int(str(r["wrap_ms"])), int(str(r["window"])))
            if w is not None:
                wins.append(w)
    return wins


def replace(device: str, stage: str, out: Path, toolchain: Path, ticks30: Path) -> int:
    # Run 11's warm-up ends adaptively (no new MEM_SAMPLE floor for 20 cycles, at most 100), so its window moves from run to
    # run: after a miss, a fresh place run at this stage, then the wrap mid-way through the span every observed window shares.
    place(device, out, toolchain, ticks30, stage, phase="re-place")
    wins = observed(device, stage, out)
    lo, hi = max(a for a, _ in wins), min(b for _, b in wins)
    if lo >= hi:
        _append(out, {"phase": "common-window-none", "device": device, "stage": stage, "windows": wins})
        msg = f"{device} {stage}: the observed Run 11 windows share no span, nothing re-run: {wins}"
        raise SystemExit(msg)
    _append(out, {"phase": "common-window", "device": device, "stage": stage, "windows": wins, "lo": lo, "hi": hi, "wrap_ms": (lo + hi) // 2})
    return (lo + hi) // 2


def prove(device: str, wrap_ms: int, out: Path, toolchain: Path, ticks30: Path) -> None:
    # Before the long runs: Run 11 alone with the wrap placed, read back for the period, the binary and the window.
    log = out / "logs" / f"prove_{device}.log"
    sha_before = _sha(_binary(toolchain))
    rc, wall, waited = _suite(device, "-1", wrap_ms, toolchain, log, ["--only", "11"])
    stage_dir = REPO / "digital_twin_ci_logs" / device / STAGE_DIRS["-1"]
    kept = out / "logs" / f"prove_{device}_run11_soak.log"
    shutil.copy2(stage_dir / "run11_soak.log", kept)
    suite_log = log.read_text(encoding="utf-8", errors="replace")
    rec: dict[str, object] = {"phase": "prove", "device": device, "stage": "-1", "wrap_ms": wrap_ms, "rc": rc, "wall_s": wall, "load_wait_s": waited}
    rec.update(_evidence(_binary(toolchain), ticks30, sha_before, suite_log, [kept]))
    rec.update(_soak(stage_dir, suite_log))
    _append(out, rec)
    if not _proven(rec):
        msg = f"prove {device}: not proven, nothing long started: {rec}"
        raise SystemExit(msg)


def _attempt(rec: dict[str, object]) -> int:
    return int(str(rec.get("attempt", 1 if rec.get("replaced") else 0)))


def _tag(attempt: int) -> str:
    return "" if attempt == 0 else "_placed" if attempt == 1 else f"_placed{attempt}"  # each re-placed run keeps its logs beside the misses'


def run(device: str, stage: str, wrap_ms: int, out: Path, toolchain: Path, ticks30: Path, *, attempt: int) -> dict[str, object]:
    binary = _binary(toolchain)
    sha_before = _sha(binary)
    tag = _tag(attempt)
    log = out / "logs" / f"suite_{device}_{STAGE_DIRS[stage]}{tag}.log"
    rc, wall, waited = _suite(device, stage, wrap_ms, toolchain, log, [])
    suite_log = log.read_text(encoding="utf-8", errors="replace")
    stage_dir = REPO / "digital_twin_ci_logs" / device / STAGE_DIRS[stage]
    kept = out / "logs" / f"{device}_{STAGE_DIRS[stage]}{tag}"
    shutil.rmtree(kept, ignore_errors=True)
    shutil.copytree(stage_dir, kept, ignore=shutil.ignore_patterns("state*"))
    # A uart_link device runs Run 3 again on CRC16: its own Result line, its logs beside the stage's, kept and scanned with them.
    crc16 = CRC16_PART in suite_log
    crc_dir = REPO / "digital_twin_ci_logs" / device / "crc16" / STAGE_DIRS[stage]
    if crc16 and crc_dir.is_dir():
        shutil.copytree(crc_dir, kept / "crc16", ignore=shutil.ignore_patterns("state*"))
    rec: dict[str, object] = {
        "phase": "suite", "device": device, "stage": stage, "wrap_ms": wrap_ms, "replaced": attempt > 0, "attempt": attempt, "rc": rc, "wall_s": wall, "load_wait_s": waited, "parts": 1 + crc16, "unscanned": [str(crc_dir)] if crc16 and not crc_dir.is_dir() else [], "result": re.findall(r"^Result: \w+", suite_log, re.MULTILINE),
        "fails": len(re.findall(r"^FAIL", suite_log, re.MULTILINE)), "oks": len(re.findall(r"^OK:", suite_log, re.MULTILINE)),
    }
    rec.update(_evidence(binary, ticks30, sha_before, suite_log, sorted(kept.rglob("*.log"))))
    rec.update(_soak(stage_dir, suite_log))
    _append(out, rec)
    return rec


def stage_run(device: str, stage: str, wrap_ms: int, out: Path, toolchain: Path, ticks30: Path) -> None:
    done = [r for r in _records(out) if r["phase"] == "suite" and r["device"] == device and r["stage"] == stage]
    rec = done[-1] if done else run(device, stage, wrap_ms, out, toolchain, ticks30, attempt=0)
    while _miss(rec) and _attempt(rec) < MAX_REPLACE:
        common = [r for r in _records(out) if r["phase"] == "common-window" and r["device"] == device and r["stage"] == stage]
        again = int(str(common[-1]["wrap_ms"])) if len(common) > _attempt(rec) else replace(device, stage, out, toolchain, ticks30)
        rec = run(device, stage, again, out, toolchain, ticks30, attempt=_attempt(rec) + 1)
    if not _green(rec):
        msg = f"{device} {stage}: not green, the sweep stops here for its root cause: {rec}"
        raise SystemExit(msg)


def main() -> int:
    out, toolchain, ticks30 = (Path(a).resolve() for a in sys.argv[1:4])
    (out / "logs").mkdir(parents=True, exist_ok=True)
    devices = sys.argv[4:] or subprocess.run(["/bin/bash", "-c", "source scripts/_devices.sh; derived_devices"], cwd=REPO, check=True, capture_output=True, text=True).stdout.split()
    for device in devices:
        recs = _records(out)
        placed = [r for r in recs if r["phase"] == "place" and r["device"] == device and r.get("stage", "-1") == "-1"]
        wrap_ms = int(str(placed[-1]["wrap_ms"])) if placed else place(device, out, toolchain, ticks30)  # each stage's first run; a miss re-places that stage
        if not any(r["phase"] == "prove" and _proven(r) for r in recs):
            prove(device, wrap_ms, out, toolchain, ticks30)
        for stage in STAGE_DIRS:
            stage_run(device, stage, wrap_ms, out, toolchain, ticks30)
    return 0


if __name__ == "__main__":
    sys.exit(main())
