"""Run each full-suite command once, recording exit code, wall clock, host peak RAM and SSD writes (M.PROC.002/.007).
Output: <outdir>/<label>.log per command and one JSON line per command appended to <outdir>/results.jsonl.
Usage: [MEASURE_ROOT=<tree>] b0_measure.py <outdir> [label ...]   (no labels: every command, in order)"""
import json
import os
import resource
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT = Path(os.environ.get("MEASURE_ROOT") or Path(__file__).resolve().parents[2])
DEVICES = sorted(p.stem for p in (ROOT / "devices").glob("*.toml"))
FW = "RUN_SLOW_FIRMWARE_BUILD=1 uv run pytest tests_scripts/test_build_firmware.py -k test_real_firmware_build_produces_a_valid_uf2"
COMMANDS = [
    ("L0_pytest_tests_scripts", "uv run pytest tests_scripts -q"),
    ("L0_npm_lint", "npm run lint"),
    ("L0_npm_typecheck", "npm run typecheck"),
    ("L0_npm_lint_html", "npm run lint:html"),
    ("L0_npm_lint_css", "npm run lint:css"),
    ("L0_npm_test", "npm test"),
    ("L1_test_sh_gc_default", "scripts/test.sh"),
    ("L1_test_sh_gc_32768", "GC_THRESHOLD=32768 scripts/test.sh"),
    ("L1_test_sh_coverage", "scripts/test.sh --coverage"),
    *[(f"L2_twin_{d}", f"scripts/run_digital_twin_ci.sh {d}") for d in DEVICES],
    ("L34_hw_collect_only", "uv run pytest tests_hardware --collect-only -q"),
    ("lint_sh", "scripts/lint.sh"),
    ("typecheck_sh", "scripts/typecheck.sh"),
    ("firmware_build_verify", FW),
    ("toolchain_test", "uv run toolchain/setup_toolchain.py test"),
]


def sectors_written(dev="vda"):
    for line in Path("/proc/diskstats").read_text().splitlines():
        f = line.split()
        if f[2] == dev:
            return int(f[9])
    return 0


def mem_available_kb():
    for line in Path("/proc/meminfo").read_text().splitlines():
        if line.startswith("MemAvailable:"):
            return int(line.split()[1])
    return 0


def run(label, cmd, outdir):
    low = [mem_available_kb()]
    stop = threading.Event()

    def sample():
        while not stop.wait(1.0):
            low[0] = min(low[0], mem_available_kb())

    base_avail, w0, t0 = low[0], sectors_written(), time.monotonic()
    rss0 = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
    th = threading.Thread(target=sample, daemon=True)
    th.start()
    with (outdir / f"{label}.log").open("w") as log:
        rc = subprocess.call(["bash", "-c", f"source .venv/bin/activate && {cmd}"], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, env=os.environ | {"PYTHONUNBUFFERED": "1"})
    stop.set()
    th.join()
    rss1 = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
    rec = {
        "label": label, "cmd": cmd, "rc": rc, "wall_s": round(time.monotonic() - t0, 1),
        "host_peak_ram_mb": round((base_avail - low[0]) / 1024, 1), "max_child_rss_mb": round(max(rss1, rss0) / 1024, 1),
        "ssd_writes_mb": round((sectors_written() - w0) * 512 / 1e6, 1), "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    with (outdir / "results.jsonl").open("a") as f:
        f.write(json.dumps(rec) + "\n")
    print(json.dumps(rec), flush=True)


def main():
    outdir = Path(sys.argv[1])
    outdir.mkdir(parents=True, exist_ok=True)
    wanted = sys.argv[2:]
    for label, cmd in COMMANDS:
        if not wanted or label in wanted:
            run(label, cmd, outdir)


if __name__ == "__main__":
    main()
