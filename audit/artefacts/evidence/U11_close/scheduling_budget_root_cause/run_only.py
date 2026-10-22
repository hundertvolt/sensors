# Runs only the test_* functions of one tests/ file whose name contains <substr>, via microtest.
# Usage (cwd = worktree): micropython -X heapsize=16M run_only.py <test_file> <substr|@names_file> [gc_threshold]
import gc
import sys

import microtest

if len(sys.argv) > 3:
    gc.threshold(int(sys.argv[3]))
ns = {"__name__": "run_only", "__file__": sys.argv[1]}
with open(sys.argv[1]) as f:
    exec(compile(f.read(), sys.argv[1], "exec"), ns)  # noqa: S102
if sys.argv[2].startswith("@"):  # @names_file: exactly the listed test names
    with open(sys.argv[2][1:]) as f:
        wanted = {line.strip() for line in f if line.strip()}
    microtest.run({n: v for n, v in ns.items() if n in wanted})
else:
    microtest.run({n: v for n, v in ns.items() if n.startswith("test_") and sys.argv[2] in n})
