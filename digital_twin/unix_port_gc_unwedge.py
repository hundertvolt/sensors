"""Workaround for a MicroPython Unix-port race that leaves the GC heap permanently locked when a real SIGINT lands during a `gc_collect()` — every later allocation then fails with `MemoryError: memory allocation failed, heap is locked`, including the shutdown flush.
Call `unwedge_heap_after_interrupt()` first in any `except KeyboardInterrupt:` handler that still needs to allocate. Full mechanism: SPECIFICATION.md Part F.6."""

import gc


def unwedge_heap_after_interrupt() -> None:
    """Clear a `GC_COLLECT_FLAG` left stuck in `gc_lock_depth` by an interrupted collection."""
    # gc.collect() is the recovery, and the only one that works: py/gc.c's gc_collect_start_common()
    # re-sets the flag and gc_collect_end() clears it properly on the way out. micropython.
    # heap_unlock() is NOT a substitute - it subtracts (1 << GC_LOCK_DEPTH_SHIFT) from a value
    # holding only the 1-bit collect flag, leaving gc_lock_depth negative and still "locked".
    # Unconditional and cheap: a collection at shutdown costs nothing and needs no allocation of
    # its own, so this is safe to run on every interrupt rather than only the wedged ones.
    gc.collect()
