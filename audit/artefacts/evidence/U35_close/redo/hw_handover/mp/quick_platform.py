"""Bare-image platform facts (REPORT 7 items 5 and 7): config-like floats through json on rp2's single-precision build,
and the text a heap exhaustion raises, plain, in a soft callback and in a hard IRQ without and with the emergency
exception buffer (the memory gates match "memory allocation failed"). Prints facts, judges nothing."""

import gc
import json
import time

import machine
import micropython

VALUES = (0.1, 0.2, 0.5, 1.5, 2.5, 3.3, 9.81, 21.37, 25.0, -40.0, 85.0, 1e-3, 0.333, 1013.25, 101325.0, 12345.678, 3.14159, 6.022e23)
bad = []
for v in VALUES:
    s = json.dumps(v)
    back = json.loads(s)
    if back != v or json.dumps(back) != s:
        bad.append("%r->%s->%r" % (v, s, back))
print("SUM json_floats n=%d not_round_tripping=%d examples=%s" % (len(VALUES), len(bad), bad[:4]))
print("SUM float_repr 0.1=%r 1013.25=%r 21.37=%r 12345.678=%r" % (0.1, 1013.25, 21.37, 12345.678))

gc.collect()
print("SUM heap free=%d alloc=%d" % (gc.mem_free(), gc.mem_alloc()))
try:
    bytearray(10_000_000)
except MemoryError as e:
    print("SUM memoryerror big_alloc=%r" % (e,))
hog = []
try:
    while True:
        hog.append(bytearray(1024))
except MemoryError as e:
    print("SUM memoryerror exhaust=%r after_kib=%d" % (e, len(hog)))
hog = None
gc.collect()


def _alloc(_t: object) -> None:
    bytearray(10_000_000)


for hard in (False, True):
    t = machine.Timer(mode=machine.Timer.ONE_SHOT, period=10, callback=_alloc, hard=hard)
    time.sleep_ms(200)
    t.deinit()
    print("SUM irq_alloc_above hard=%d emergency_buf=0 (the traceback is the console text above)" % hard)
micropython.alloc_emergency_exception_buf(256)
t = machine.Timer(mode=machine.Timer.ONE_SHOT, period=10, callback=_alloc, hard=True)
time.sleep_ms(200)
t.deinit()
print("SUM irq_alloc_above hard=1 emergency_buf=256 (the traceback is the console text above)")
print("DONE=1")
