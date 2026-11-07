"""Lane D's MicroPython batch: each (label, tree, file, mode) run alone, nice 19, its own netns; a TSV line per run."""
import os
import subprocess
import sys
import time
from pathlib import Path

SCRATCH = Path("/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad")
NS = str(SCRATCH / "u22/api5/ns.sh")
STD = "/root/pico-toolchain/micropython/ports/unix/build-standard/micropython"
COV = "/root/pico-toolchain/micropython/ports/unix/build-settrace/micropython"
OUT = SCRATCH / "u23/laneD/batch"
TREES = {"after": SCRATCH / "wt-u23d", "before": SCRATCH / "u23/laneD/head_tree"}


def command(mode: str, label: str, name: str) -> "list[str]":
    if mode == "e":
        return [STD, "-X", "heapsize=16M", f"tests/{name}.py"]
    if mode == "f":
        return [STD, "-X", "heapsize=16M", "tests/_threshold_runner.py", f"tests/{name}.py", "32768"]
    return [COV, "-X", "heapsize=16M", "tests/_coverage_runner.py", f"tests/{name}.py", str(SCRATCH / f"u23/laneD/cov/{label}_{name}.json")]


def main() -> int:
    plan = [line.split() for line in Path(sys.argv[1]).read_text().splitlines() if line.strip()]
    env = {**os.environ, "TZ": "UTC", "MICROPYPATH": "build/generated_src:src:tests:frozen_modules:.frozen"}
    with (OUT / "results.tsv").open("a") as tsv:
        for label, name, mode in plan:
            out = OUT / f"{label}_{mode}_{name}.txt"
            start = time.monotonic()
            with out.open("w") as f:
                rc = subprocess.run(["nice", "-n", "19", "timeout", "300", "unshare", "-n", NS, *command(mode, label, name)], cwd=TREES[label], env=env, stdout=f, stderr=subprocess.STDOUT, check=False).returncode
            wall = time.monotonic() - start
            text = out.read_text(errors="replace")
            summary = next((line for line in reversed(text.splitlines()) if "passed," in line), "no summary")
            mem = text.count("MemoryError") + text.count("memory allocation failed")
            tsv.write(f"{label}\t{name}\t{mode}\trc={rc}\t{wall:.1f}s\tmem={mem}\t{summary}\n")
            tsv.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
