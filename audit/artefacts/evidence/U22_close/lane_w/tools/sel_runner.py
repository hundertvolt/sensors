# Runs the named test_* functions of one test module (imported, so microtest.run() never fires); PASS/FAIL per name.
import sys

module = __import__(sys.argv[1])
failed = 0
for name in sys.argv[2:]:
    try:
        getattr(module, name)()
    except Exception as exc:
        failed += 1
        print("FAIL", name)
        sys.print_exception(exc)
    else:
        print("PASS", name)
print("selected:", len(sys.argv) - 2, "failed:", failed)
sys.exit(1 if failed else 0)
