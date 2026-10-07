# Applies one named plant to the scratch tree (argv: tree, name); "none" restores nothing.
import sys
tree, name = sys.argv[1], sys.argv[2]
P = {
    "P1_no_heater_off": ("src/asy_sgp40_driver.py",
        "        try:\n            await self._sgp.turn_heater_off()\n        except Exception as e:\n            await self.pr.err_s(\"Heater-off failed:\", e, errno=_ERR_CHIP_SET)\n            return False\n        return True\n",
        "        return None\n"),
    "P2_rung_per_reader": ("src/asy_base_classes.py",
        "        if bus.recoveries != self._bus_mark:\n            return\n        if rung == _RUNG_BUS:",
        "        if rung == _RUNG_BUS:"),
    "P3_no_bus_clear": ("src/asy_base_classes.py",
        "        elif n >= _RECOVER_BUS_AT and not self._rungs & _RUNG_BUS:\n            await self._recover_bus(_RUNG_BUS)\n",
        ""),
}
f, a, b = P[name]
p = f"{tree}/{f}"
s = open(p).read()
assert s.count(a) == 1, name
open(p, "w").write(s.replace(a, b))
print("planted", name)
