# Runs only the named scenarios of tests/_sensortask_scenarios.py for one device.
import sys

from _sensortask_scenarios import register_for_device

device = sys.argv[1]
names = sys.argv[2:]
tests = register_for_device(device)
fails = 0
for n in names:
    try:
        tests["test_" + n]()
        print("PASS", n)
    except Exception as e:
        fails += 1
        print("FAIL", n, repr(e))
        sys.print_exception(e)
print(f"{len(names) - fails}/{len(names)} passed")
