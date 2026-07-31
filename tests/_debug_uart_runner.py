# TEMPORARY debug-only runner - not part of the real test suite, lives only on the
# debug/uart-ci-hang-investigation branch. Unlike tests/microtest.py, prints START before
# calling each test (not just PASS/FAIL after), so a hang shows exactly which test began but
# never returned instead of just "no output at all".
import sys

import test_asy_uart_driver as mod

names = [name for name in vars(mod) if name.startswith("test_")]
print(f"collected {len(names)} tests")

total = 0
failed = 0
for name in names:
    fn = vars(mod)[name]
    if not callable(fn):
        continue
    total += 1
    print(f"START {name}")
    try:
        fn()
    except Exception as exc:
        failed += 1
        print(f"FAIL {name}:")
        sys.print_exception(exc)
    else:
        print(f"PASS {name}")

print(f"{total - failed}/{total} passed")
if failed:
    sys.exit(1)
