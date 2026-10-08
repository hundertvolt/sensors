# Scratch (not repo): prints each test name before running it, to find a test that kills the process.
import sys
test_file = sys.argv[1]
with open(test_file) as f:
    source = f.read()
ns = {"__name__": "not_main", "__file__": test_file}
exec(compile(source, test_file, "exec"), ns)
for name, value in list(ns.items()):
    if name.startswith("test_") and callable(value):
        print("RUN", name)
        try:
            value()
        except Exception as e:
            print("FAIL", name, repr(e))
print("done")
