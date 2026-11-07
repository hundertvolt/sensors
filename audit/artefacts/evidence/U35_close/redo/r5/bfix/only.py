# only.py MODULE TEST...: runs the named test functions of one tests/ module through microtest.
import sys

mod = __import__(sys.argv[1])
import microtest  # noqa: E402

microtest.run({name: getattr(mod, name) for name in sys.argv[2:]})
