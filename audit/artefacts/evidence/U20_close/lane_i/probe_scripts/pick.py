# Scratch: runs named scenarios of tests/_sensortask_scenarios.py for one device: pick.py <device> <name substring>...
import sys
from _sensortask_scenarios import register_for_device
import microtest
args = sys.argv[1:]
if args and args[0].endswith(".py"):
    args = args[2:]
device = args[0]
wanted = args[1:]
tests = register_for_device(device)
picked = {n: f for n, f in tests.items() if any(w in n for w in wanted)}
print("picked", sorted(picked))
microtest.run(picked)
