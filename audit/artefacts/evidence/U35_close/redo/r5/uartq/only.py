# only.py MODULE NAME...: runs the named test_* functions of one tests/ module through microtest.
import sys

import microtest

mod = __import__(sys.argv[1])
want = sys.argv[2:]
ns = {k: getattr(mod, k) for k in dir(mod) if k in want}
assert len(ns) == len(want), (sorted(ns), want)
microtest.run(ns)
