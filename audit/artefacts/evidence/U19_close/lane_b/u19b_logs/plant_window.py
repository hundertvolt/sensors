import sys
src, dst, which = sys.argv[1], sys.argv[2], sys.argv[3]
s = open(src).read()
plants = {
    "nocap_total": ("            if b >= COUNTER_CAP - s:  # checked before the step: no intermediate leaves the small-int range\n                return COUNTER_CAP\n", ""),
    "noshift": ("            for h in range(self._hour + 1, hour + 1):\n                self._bins[h % _WINDOW_HOURS] = 0\n", "            pass\n"),
    "nogapclear": ("            for i in range(_WINDOW_HOURS):\n                self._bins[i] = 0\n        else:", "            pass\n        else:"),
    "noreset": ("    def reset(self) -> None:\n        for i in range(_WINDOW_HOURS):\n            self._bins[i] = 0\n", "    def reset(self) -> None:\n        pass\n"),
    "nocap_add": ("        if self._bins[i] < COUNTER_CAP:\n            self._bins[i] += 1\n", "        self._bins[i] += 1\n"),
    "newbins_reset": ("    def reset(self) -> None:\n        for i in range(_WINDOW_HOURS):\n            self._bins[i] = 0\n", "    def reset(self) -> None:\n        self._bins = [0] * _WINDOW_HOURS\n"),
}
old, new = plants[which]
assert s.count(old) == 1, which
open(dst, "w").write(s.replace(old, new))
