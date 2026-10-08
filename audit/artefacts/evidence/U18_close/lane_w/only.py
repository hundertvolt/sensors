# Scratch: run only the tests of one test module whose names contain any of the comma-separated
# substrings in argv[2] (argv[1] = module name). Lane W iteration aid; never committed.
import sys

import microtest

mod = __import__(sys.argv[1])
keys = sys.argv[2].split(",")
ns = {}
for k in dir(mod):
    v = getattr(mod, k)
    if k.startswith("test_") and not any(s in k for s in keys):
        continue
    ns[k] = v
microtest.run(ns)
