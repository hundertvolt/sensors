import sys
from pathlib import Path
root = Path.cwd()
sys.path[:0] = [str(root / "tests_scripts"), str(root)]
import test_ticks_wrap_scan as s
from _devices import DEVICE_NAMES
from buildgen.generate import generate_device
gen = {}
for d in DEVICE_NAMES:
    r = generate_device(root / "devices" / f"{d}.toml", root / "src", root / "ext")
    gen[f"generated:sensortask_{d}.py"] = r.module_source
    gen[f"generated:{d}/main.py"] = r.boot_entry_source
base = s._read_scopes(root) | gen
known = s._known_users()
m = base["digital_twin/machine.py"]
old_ordered = "        return self._items[self._head :] + self._items[: self._head]\n"
new_ordered = "        ordered = self._items[self._head :]\n        ordered.extend(self._items[: self._head])\n        return ordered\n"
assert m.count(old_ordered) == 1
feed = "        self.feed_times.append(time.ticks_ms())\n"
assert m.count(feed) == 1
print("as is:          ", s._findings(base, known))
print("no feed line:   ", s._findings(base | {"digital_twin/machine.py": m.replace(feed, "")}, known))
print("_ordered extend:", s._findings(base | {"digital_twin/machine.py": m.replace(old_ordered, new_ordered)}, known))
