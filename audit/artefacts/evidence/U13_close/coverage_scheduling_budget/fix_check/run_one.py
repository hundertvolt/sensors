# Runs one test function of a test file (argv: file, test name); prints PASS/FAIL like microtest.
import sys
f, name = sys.argv[1], sys.argv[2]
sys.path.insert(0, f.rsplit("/", 1)[0])  # the file's own dir first, as a direct run would have it
ns = {"__name__": "not_main", "__file__": f}
exec(compile(open(f).read(), f, "exec"), ns)
try:
    ns[name]()
    print("PASS", name)
except AssertionError as e:
    print("FAIL", name, e)
