"""M.PROC.024 (1): every L1 file whose import closure reads ticks, on the 2**30 build, the wrap at 1/4, 1/2, 3/4 of its wall clock.
Usage: ticks30_batch.py derive|measure|wrap|rewrap|table <out dir> [<ticks30 binary>]; one record per run in <out>/results.jsonl, resumable.
measure runs each job once on build-standard at -1 (the wall clock); wrap runs both GC stages on the scratch build; rewrap re-places a job
whose run ended before its wrap on its in-run span (first read to exit) instead. Audit only."""

import ast
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
STANDARD = Path(os.environ.get("PICO_TOOLCHAIN_DIR", "/root/pico-toolchain")) / "micropython/ports/unix/build-standard/micropython"
UNIT_PATH = "build/generated_src:src:tests:frozen_modules:.frozen"  # scripts/micropypath.toml's unit layout
SEARCH = ("build/generated_src", "src", "tests", "digital_twin", "frozen_modules")
TICK = re.compile(r"\bticks_(ms|us|diff|add)\b")
MARKERS = ("MemoryError", "memory allocation failed")
FRACTIONS = ((1, 4), (1, 2), (3, 4))
STAGES = ("-1", "32768")
HEAVY = frozenset({"micropython", "node"})
MAX_HEAVY = 4  # CHECKLIST 12: a wall-time-bound file starts only while at most 4 heavy processes run on the host
WALL_NAME = re.compile(r"concurrency|integration|uart_link|webserver|live")  # CHECKLIST 12's wall-time-bound kinds, by name
WALL_TEXT = re.compile(r"elapsed|ticks_diff\(|time\.time\(\)|monotonic")  # and any file timing itself
# The first ticks read fixes the scratch build's offset, so the launcher reads first: the wrap lands TICKS30_WRAP_IN_MS
# after start. It then runs the target as tests/_threshold_runner.py runs a file, and prints what the run's counter did.
LAUNCHER = """import sys
import time
_t0 = time.ticks_ms()
_period = time.ticks_add(0, -1) + 1
_target = sys.argv[1]
sys.argv[:] = sys.argv[1:]
sys.path[0] = _target.rsplit("/", 1)[0] if "/" in _target else ""
_code = 0
try:
    with open(_target) as _f:
        _source = _f.read()
    exec(compile(_source, _target, "exec"), {"__name__": "__main__", "__file__": _target})
except SystemExit as _exc:
    _code = _exc.args[0] if _exc.args else 0
finally:
    _t1 = time.ticks_ms()
    print("TICKS30 period=%d start=%d end=%d crossed=%s" % (_period, _t0, _t1, _t1 < _t0))
sys.exit(_code)
"""


def _module(name: str) -> Path | None:
    for directory in SEARCH:
        path = REPO / directory / (name.split(".", 1)[0] + ".py")
        if path.is_file():
            return path
    return None


def _direct(path: Path, cache: dict[Path, tuple[set[Path], bool]]) -> tuple[set[Path], bool]:
    # One module's own imports (static, plus the generated device modules a __import__ by device name reaches) and
    # whether its non-comment code names a ticks call.
    if path not in cache:
        text = path.read_text(encoding="utf-8")
        deps: set[Path] = set()
        for node in ast.walk(ast.parse(text)):
            names = [alias.name for alias in node.names] if isinstance(node, ast.Import) else [node.module] if isinstance(node, ast.ImportFrom) and node.module and not node.level else []
            deps.update(dep for dep in map(_module, names) if dep is not None and dep != path)
        if "sensortask_{device}" in text or "__import__(name)" in text:
            deps.update(p for p in (REPO / "build/generated_src").glob("sensortask_*.py") if re.fullmatch(r"sensortask_[a-z]+\.py", p.name))
        code = "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("#"))
        cache[path] = (deps, bool(TICK.search(code)))
    return cache[path]


def derive() -> list[dict[str, object]]:
    cache: dict[Path, tuple[set[Path], bool]] = {}
    devices = subprocess.run(["/bin/bash", "-c", "source scripts/_devices.sh; derived_devices"], cwd=REPO, check=True, capture_output=True, text=True).stdout.split()
    jobs: list[dict[str, object]] = []
    for test in sorted((REPO / "tests").glob("test_*.py")):
        seen: set[Path] = set()
        todo = [test]
        while todo:
            path = todo.pop()
            if path not in seen:
                seen.add(path)
                todo.extend(_direct(path, cache)[0])
        readers = sorted(str(p.relative_to(REPO)) for p in seen if _direct(p, cache)[1])
        if not readers:
            continue
        text = test.read_text(encoding="utf-8")
        per_device = re.search(r"^PER_DEVICE = True$", text, re.MULTILINE) is not None
        for device in devices if per_device else [""]:
            rel = str(test.relative_to(REPO))
            jobs.append({"job": f"{rel}[{device}]" if device else rel, "file": rel, "device": device, "readers": readers, "driven": "DrivenTime" in text})
    return jobs


def _heavy_count() -> int:
    count = 0
    for comm in Path("/proc").glob("[0-9]*/comm"):
        try:
            count += comm.read_text(encoding="utf-8").strip() in HEAVY
        except OSError:
            continue
    return count


def _run(job: dict[str, object], binary: Path, stage: str, wrap_ms: int | None, log: Path, timeout_s: float, launcher: Path) -> dict[str, object]:
    waited = 0.0
    bound = bool(WALL_NAME.search(str(job["file"])) or WALL_TEXT.search((REPO / str(job["file"])).read_text(encoding="utf-8")))
    while bound and _heavy_count() > MAX_HEAVY and waited < 1200:  # noqa: PLR2004  # the gate's bound: 20 min, then the run starts and says so
        time.sleep(10)
        waited += 10
    env = {k: v for k, v in os.environ.items() if k not in {"TEST_DEVICE", "TICKS30_WRAP_IN_MS"}}
    env.update({"TZ": "UTC", "MICROPYPATH": UNIT_PATH})
    if job["device"]:
        env["TEST_DEVICE"] = str(job["device"])
    if wrap_ms is not None:
        env["TICKS30_WRAP_IN_MS"] = str(wrap_ms)
    target = [str(job["file"])] if stage == "-1" else ["tests/_threshold_runner.py", str(job["file"]), stage]
    cmd = [str(binary), "-X", "heapsize=16M", *([str(launcher), *target] if wrap_ms is not None else target)]
    log.parent.mkdir(parents=True, exist_ok=True)
    t0 = time.monotonic()
    with log.open("w", encoding="utf-8") as out:
        try:
            rc = subprocess.run(cmd, cwd=REPO, env=env, stdout=out, stderr=subprocess.STDOUT, timeout=timeout_s, check=False).returncode  # noqa: S603  # our own argv, no shell
        except subprocess.TimeoutExpired:
            rc = -9
    wall = time.monotonic() - t0
    text = log.read_text(encoding="utf-8", errors="replace")
    summary = re.findall(r"\d+/\d+ passed, \d+ failed, \d+ skipped", text)
    tick = re.search(r"TICKS30 period=(\d+) start=(\d+) end=(\d+) crossed=(\w+)", text)
    return {
        "job": job["job"], "stage": stage, "wrap_ms": wrap_ms, "rc": rc, "wall_s": round(wall, 2), "summary": summary[-1] if summary else None,
        "markers": sum(text.count(m) for m in MARKERS), "period": int(tick.group(1)) if tick else None, "start": int(tick.group(2)) if tick else None,
        "end": int(tick.group(3)) if tick else None, "crossed": tick.group(4) == "True" if tick else None, "wall_bound": bound, "load_wait_s": waited, "log": str(log),
    }


def _records(out: Path) -> list[dict[str, object]]:
    path = out / "results.jsonl"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()] if path.is_file() else []


def _key(rec: dict[str, object]) -> tuple[str, str, str, str]:
    return (str(rec["phase"]), str(rec["job"]), str(rec["stage"]), str(rec["wrap_ms"]))


def _append(out: Path, rec: dict[str, object]) -> None:
    with (out / "results.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec) + "\n")
    sys.stdout.write(f"{rec['phase']} {rec['job']} stage={rec['stage']} wrap={rec['wrap_ms']} rc={rec['rc']} wall={rec['wall_s']}s {rec['summary']} markers={rec['markers']} crossed={rec['crossed']}\n")
    sys.stdout.flush()


def _tag(job: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]", "_", job)


def batch(phase: str, out: Path, binary: Path) -> int:
    jobs = json.loads((out / "jobs.json").read_text(encoding="utf-8"))
    done = {_key(r) for r in _records(out)}
    launcher = out / "launch" / "ticks_first.py"  # alone in its directory: the interpreter puts that directory first on the path
    launcher.parent.mkdir(parents=True, exist_ok=True)
    launcher.write_text(LAUNCHER, encoding="utf-8")
    walls = {str(r["job"]): float(str(r["wall_s"])) for r in _records(out) if r["phase"] == "measure"}
    spans: dict[str, int] = {}
    for r in _records(out):
        if r["phase"] == "wrap" and not r["crossed"]:
            job_runs = [x for x in _records(out) if x["phase"] == "wrap" and x["job"] == r["job"] and x["start"] is not None]
            spans[str(r["job"])] = min((int(str(x["end"])) - int(str(x["start"]))) % (1 << 30) for x in job_runs)
    for job in jobs:
        if phase == "rewrap" and job["job"] not in spans:
            continue
        ms = spans.get(job["job"]) if phase == "rewrap" else walls[job["job"]] * 1000
        plan = [("-1", None)] if phase == "measure" else [(s, round(float(str(ms)) * n / d)) for s in STAGES for n, d in FRACTIONS]
        for stage, wrap_ms in plan:
            rec = {"phase": phase, "job": job["job"], "stage": stage, "wrap_ms": wrap_ms}
            if _key(rec) in done:
                continue
            log = out / "logs" / phase / f"{_tag(job['job'])}__{stage}__{wrap_ms}.log"
            timeout_s = 900.0 if wrap_ms is None else max(300.0, 6 * walls[job["job"]])
            rec.update(_run(job, STANDARD if phase == "measure" else binary, stage, wrap_ms, log, timeout_s, launcher))
            _append(out, rec)
    return 0


def table(out: Path) -> int:
    recs = _records(out)
    walls = {r["job"]: r for r in recs if r["phase"] == "measure"}
    sys.stdout.write("| file | build-standard -1 | wrap points (ms) | -1 on build-ticks30 | 32768 on build-ticks30 | time on build-ticks30 |\n|---|---|---|---|---|---|\n")
    for job in json.loads((out / "jobs.json").read_text(encoding="utf-8")):
        runs = [r for r in recs if r["phase"] == "rewrap" and r["job"] == job["job"]] or [r for r in recs if r["phase"] == "wrap" and r["job"] == job["job"]]
        cells = []
        for stage in STAGES:
            mine = [r for r in runs if r["stage"] == stage]
            green = [r for r in mine if r["rc"] == 0 and not r["markers"] and r["period"] == 1 << 30]
            crossed = [r for r in green if r["crossed"]]
            if not mine:
                cells.append("not run yet")
            elif len(green) < len(mine):
                cells.append(f"FAIL {[(r['wrap_ms'], r['rc'], r['markers'], r['crossed']) for r in mine]}")
            else:
                pending = "" if len(crossed) == len(mine) else f", {len(crossed)} crossed (re-place pending)"
                cells.append(f"{len(green)}/{len(mine)} PASS {mine[0]['summary'] or ''}{pending}")
        points: list[object] = [*sorted({int(str(r["wrap_ms"])) for r in runs})]
        if runs and runs[0]["phase"] == "rewrap":
            missed = sorted({(r["stage"], r["wrap_ms"]) for r in recs if r["phase"] == "wrap" and r["job"] == job["job"] and not r["crossed"]})
            points.append(f"(re-placed on the in-run span; on the wall clock {missed} ended before the wrap, passing)")
        times = [float(str(r["wall_s"])) for r in runs]
        base = walls.get(job["job"])
        span = f"{min(times):.2f}-{max(times):.2f} s" if times else "-"
        sys.stdout.write(f"| `{job['job']}` | {base['wall_s'] if base else '-'} s, {base['summary'] if base else '-'} | {', '.join(map(str, points))} | {cells[0]} | {cells[1]} | {span} |\n")
    return 0


def main() -> int:
    phase, out = sys.argv[1], Path(sys.argv[2]).resolve()
    out.mkdir(parents=True, exist_ok=True)
    if phase == "derive":
        jobs = derive()
        (out / "jobs.json").write_text(json.dumps(jobs, indent=1) + "\n", encoding="utf-8")
        sys.stdout.write(f"{len(jobs)} jobs from {len({j['file'] for j in jobs})} files; DrivenTime in {len({j['file'] for j in jobs if j['driven']})} files\n")
        return 0
    if phase == "table":
        return table(out)
    return batch(phase, out, Path(sys.argv[3]) if len(sys.argv) > 3 else STANDARD)  # noqa: PLR2004  # argv: phase, out, binary


if __name__ == "__main__":
    sys.exit(main())
