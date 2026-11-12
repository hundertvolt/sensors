"""heap_probe.py: the real firmware under `mpremote run`, no flash write, a heap map printed at each failed /status piece; keeps serving after DONE."""
import sys
sys.path.insert(0, ".frozen")
from machine import WDT
watchdog = WDT(timeout=8000)
import gc, micropython, asyncio, time
micropython.alloc_emergency_exception_buf(100)
import asy_webserver_service as ws
from sensortask_dev import main
THRESHOLD = None
CHUNK = 0
SHARE_MS = 0
END_S = 240
if THRESHOLD: gc.threshold(THRESHOLD)
counts = [0, 0, 0]  # dumps, status builds in flight, peak in flight
def dump(tag, full):
    print("HEAP", tag, "free", gc.mem_free(), "alloc", gc.mem_alloc(), "inflight", counts[1], "peak", counts[2], "ms", time.ticks_ms())
    micropython.mem_info(1) if full else micropython.mem_info()
    print("HEAP_END", tag)
_flush = ws._PieceWriter.flush
def flush(self):
    try:
        _flush(self)
    except MemoryError:
        counts[0] += 1
        dump("FAIL_FLUSH%d" % counts[0], counts[0] <= 3)
        raise
ws._PieceWriter.flush = flush
if CHUNK:
    _wr_init = ws._PieceWriter.__init__
    def wr_init(self, pieces, max_bytes):
        _wr_init(self, pieces, CHUNK)
    ws._PieceWriter.__init__ = wr_init
shared = [None, 0, 0]  # pieces, when built, builds saved
_build = ws.WebserverService._build_status_pieces
async def build(self):
    if SHARE_MS and shared[0] is not None and time.ticks_diff(time.ticks_ms(), shared[1]) < SHARE_MS:
        shared[2] += 1
        return shared[0]
    counts[1] += 1
    counts[2] = max(counts[2], counts[1])
    try:
        pieces = await _build(self)
        if SHARE_MS:
            shared[0] = pieces
            shared[1] = time.ticks_ms()
        return pieces
    finally:
        counts[1] -= 1
ws.WebserverService._build_status_pieces = build
_handler = ws.WebserverService._handle_unhandled_exception
async def handler(self, request, exc):
    print("HEAP handler", exc, "free", gc.mem_free(), "inflight", counts[1])
    return await _handler(self, request, exc)
ws.WebserverService._handle_unhandled_exception = handler
async def driver():
    await asyncio.sleep(45)
    dump("IDLE_RAW", False)
    gc.collect()
    dump("BASELINE", True)
    print("LOAD_NOW")
    await asyncio.sleep(END_S - 45)
    dump("END", False)
    print("DONE saved", shared[2])
async def top():
    asyncio.create_task(driver())
    await main(watchdog=watchdog)
asyncio.run(top())
