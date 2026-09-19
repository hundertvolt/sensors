"""Workaround for a MicroPython Unix-port race that leaves the GC heap permanently locked when a real SIGINT lands during a `gc_collect()` — every later allocation then fails with `MemoryError: memory allocation failed, heap is locked`, including the shutdown flush.
Call `unwedge_heap_after_interrupt()` first in any `except KeyboardInterrupt:` handler that still needs to allocate. Full mechanism: SPECIFICATION.md Part F.6, whose amendment notes toolchain/micropython_overrides.py's unix_kbd_intr override (Part B.14.1) has since closed the root cause - this module stays wired in as defense in depth only."""

import gc


def unwedge_heap_after_interrupt() -> None:
    """Clear a `GC_COLLECT_FLAG` left stuck in `gc_lock_depth` by an interrupted collection."""
    # gc.collect() is the recovery and the only one that works: gc_collect_start_common() re-sets
    # the flag and gc_collect_end() clears it properly. heap_unlock() is not a substitute - it
    # subtracts a shift from a value holding only the 1-bit flag, leaving the depth negative.

    # Unconditional and cheap: a collection at shutdown costs nothing and allocates nothing, so
    # running it on every interrupt rather than only the wedged ones is safe.
    gc.collect()
