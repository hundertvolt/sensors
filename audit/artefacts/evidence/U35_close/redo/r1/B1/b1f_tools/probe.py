# B1 falsifier probe, run under the pinned Unix port against head src/ or a base copy of asy_print_log.py.
import asyncio
import collections
import micropython

import asy_print_log as L

TAG = "HEAD" if hasattr(L.PrintLog, "err_nomem") else "BASE"
print("== probe", TAG, L.__file__)


def overflow():
    def dive(d):
        return dive(d + 1)

    try:
        dive(0)
    except RuntimeError as e:
        return e
    return None


# ---- P1: a C-stack overflow handed to each entry with the heap exhausted (locked): recorded or not
ov = overflow()
print("P1 overflow args:", ov.args)
res = [None] * 24
pr = L.PrintLogHistory(2, 0, name="P")
entries = ("report_if_fatal", "err", "wrn", "one", "evt", "all", "err_s", "wrn_s", "err_nomem")
for i in range(len(entries)):
    name = entries[i]
    if name == "err_nomem" and TAG == "BASE":
        continue
    L._fatal = False
    raised = None
    micropython.heap_lock()
    try:
        if i == 0:
            L.report_if_fatal(ov)
        elif i == 1:
            pr.err("caught:", ov)
        elif i == 2:
            pr.wrn("caught:", ov)
        elif i == 3:
            pr.one("caught:", ov)
        elif i == 4:
            pr.evt("caught:", ov)
        elif i == 5:
            pr.all("caught:", ov)
        elif i == 6:
            c = pr.err_s("caught:", ov, errno=0)
            c.send(None)
        elif i == 7:
            c = pr.wrn_s("caught:", ov, wrnno=0)
            c.send(None)
        elif i == 8:
            pr.err_nomem("caught:", ov)
    except StopIteration:
        pass
    except MemoryError as m:
        raised = m
    micropython.heap_unlock()
    print("P1", name, "raised MemoryError" if raised is not None else "no raise", "recorded" if L.fatal_reported() else "NOT recorded")
L._fatal = False

# ---- P2: a caught MemoryError logged below err level, at DebugLevel 1 (the stored level a device can run at)
pr = L.PrintLogHistory(2, 1, name="H")
asyncio.run(pr.setup())
print("P2 begin (level 1)")
pr.wrn("Web server start failed, retrying:", MemoryError("probe text W"))
asyncio.run(pr.wrn_s("Config file x could not be read:", MemoryError("probe text WS"), wrnno=0))
print("P2 end")

# ---- P3: product construction at debug=None, the stored DebugLevel applied afterwards (as sysfunct.setup() does)
real = collections.deque


def refusing(it, n):
    if n:
        raise MemoryError("probe text C")
    return real(it, n)


L.deque = refusing
print("P3 begin (construct at debug None)")
pr = L.make_logger(L.LogConfig(None, 10, None), "C")
pr.set_level(5)
L.deque = real
print("P3 end, level now", pr.level)

# ---- P4: err_nomem on an exhausted heap: a MemoryError born under the lock, levels 0 and 1, and a really full heap
if TAG == "HEAD":
    out = [None, None, None]
    for level in (0, 1):
        p = L.PrintLog(level, name="N")
        born = None
        micropython.heap_lock()
        try:
            bytearray(64)
        except MemoryError as m:
            born = m
        try:
            p.err_nomem("arm:", born)
        except Exception as x:
            out[level] = x
        micropython.heap_unlock()
    hog = []
    size = 1 << 20
    while size >= 16:
        try:
            hog.append(bytearray(size))
        except MemoryError:
            size //= 2
    p = L.PrintLog(1, name="F")
    try:
        bytearray(1 << 16)
    except MemoryError as m:
        born = m
    try:
        p.err_nomem("full heap arm:", born)
    except Exception as x:
        out[2] = x
    hog = None
    print("P4 raised:", out)
print("== probe end", TAG)
