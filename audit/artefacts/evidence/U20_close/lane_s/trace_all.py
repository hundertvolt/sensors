# Scratch tracer: every test_* function of one module in turn, each name printed before it starts, failures kept going.
import sys

import microtest  # noqa: F401

module = __import__(sys.argv[1])
names = sys.argv[2:] or sorted(n for n in dir(module) if n.startswith("test_"))
for n in names:
    print("START", n)
    try:
        getattr(module, n)()
        print("OK", n)
    except Exception as e:  # keep going: the point is which one hangs
        print("FAIL", n, repr(e))
        sys.print_exception(e)
