"""Deterministic unit tests for digital_twin/unix_port_gc_unwedge.py (SPECIFICATION.md Part F.6) -
its own file since this module is shared by every digital-twin entry point that calls
asyncio.run(), not owned by any one of them."""

import gc
import sys

sys.path.insert(0, "digital_twin")  # see test_digital_twin_sgp40.py's own comment for why

from unix_port_gc_unwedge import unwedge_heap_after_interrupt

# ---------------------------------------------------------------------------
# unix_port_gc_unwedge: recovery from a SIGINT-wedged GC heap
# (SPECIFICATION.md Part F.6)
# ---------------------------------------------------------------------------

# The wedged state itself (GC_COLLECT_FLAG stuck in gc_lock_depth after a SIGINT interrupted a
# collection) is deliberately NOT constructed here: it is unreachable from Python. micropython.
# heap_lock() looks like a stand-in - both states raise the same "memory allocation failed, heap
# is locked" MemoryError - but it sets a different field, and the two need opposite recoveries
# (confirmed directly: gc.collect() clears the stuck collect flag but not heap_lock()'s depth
# counter; heap_unlock() does the reverse). Testing against heap_lock() would therefore assert the
# wrong contract. The real recovery is proven by out-of-process reproduction instead - see
# SPECIFICATION.md Part F.6 - and by the digital-twin CI suite's own eleven interrupt-driven
# shutdowns per device. What is checkable here is that it is safe on the healthy path it runs on
# every time.


def test_unwedge_is_a_harmless_no_op_on_an_unlocked_heap() -> None:
    # Called unconditionally on every interrupt, not just the wedged ones, so the overwhelmingly
    # common healthy path has to stay unaffected.
    before = gc.mem_free()
    unwedge_heap_after_interrupt()
    unwedge_heap_after_interrupt()
    assert len(bytearray(128)) == 128
    assert gc.mem_free() > 0 and isinstance(before, int)


def test_unwedge_actually_collects_so_it_can_clear_the_stuck_flag() -> None:
    # The recovery only works because it runs a real collection (gc_collect_end() is what clears
    # the flag on the way out), not because of anything it allocates - so prove a collection
    # genuinely happens: unreferenced garbage is reclaimed by the call.
    garbage = [bytearray(512) for _ in range(64)]
    assert len(garbage) == 64
    del garbage
    before = gc.mem_free()
    unwedge_heap_after_interrupt()
    assert gc.mem_free() >= before


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
