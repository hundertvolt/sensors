# usage: micropython run_with_catalog.py <test_file> <gc_threshold> [name_substring]
# Puts $CATALOG_DIR (if set) ahead of the runner dir on sys.path, sets gc.threshold, and runs the test
# file's test_* functions (all, or only those containing the substring) through tests/microtest.run().
import gc
import os
import sys
cd = os.getenv("CATALOG_DIR")
if cd:
    sys.path.insert(0, cd)
test_file = sys.argv[1]
gc.threshold(int(sys.argv[2]))
sub = sys.argv[3] if len(sys.argv) > 3 else ""
ns = {"__name__": "not_main", "__file__": test_file}
exec(compile(open(test_file).read(), test_file, "exec"), ns)
import microtest
sel = {k: v for k, v in ns.items() if not (k.startswith("test_") and sub not in k)}
print("catalog:", sys.modules["_bus_hazard_catalog"].__file__ if "_bus_hazard_catalog" in sys.modules else None)
print("selected:", [k for k in sel if k.startswith("test_")])
microtest.run(sel)
