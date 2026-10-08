# Runs the named test functions of one tests/ file under microtest (scratch helper, not committed).
import sys
sys.path.insert(0, "tests")
mod_name = sys.argv[1]
names = sys.argv[2:]
mod = __import__(mod_name)
failed = 0
for n in names:
    try:
        getattr(mod, n)()
        print("PASS", n)
    except Exception as e:
        failed += 1
        print("FAIL", n, repr(e))
print("failed:", failed)
