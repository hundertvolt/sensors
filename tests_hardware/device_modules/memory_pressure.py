"""Allocator-pressure instrument, frozen into --memory-pressure builds only (buildgen/gc_policy.py).
Makes the heap genuinely scarce and fragmented while real code runs; its own allocation failures are
counted apart from the system's, so the two can never be confused. See SPECIFICATION.md Part I.6."""

import asyncio
import gc
import time

# Mixed sizes, not one uniform block: same-sized holes are trivially reusable, so a fixed-size
# churn measures occupancy rather than fragmentation. These span the shapes real code actually
# asks for - a small header, a response fragment, a bus buffer.
_BLOCK_SIZES = (64, 256, 512, 1024)

# Fragment mode aims to leave this much free rather than to exhaust the heap. Without a floor the
# instrument starves whatever it is co-resident with, and every result says "out of memory" no
# matter how sound the design under test is. Sized for the largest single allocation the system
# legitimately makes (asy_webserver_service.py's _MAX_STATUS_PIECE_BYTES fragments plus a socket
# buffer), with room to spare.
_DEFAULT_HEADROOM = 24576
_DEFAULT_HOLD_BLOCKS = 48
_DEFAULT_INTERVAL_MS = 5
_REPORT_INTERVAL_MS = 10000

MODE_FRAGMENT = "fragment"  # keep a headroom floor; a MemoryError here means miscalibration
MODE_EXHAUST = "exhaust"  # drive to the ceiling on purpose; its own MemoryError is the point


class Pressure:
    def __init__(self, mode: str = MODE_FRAGMENT, headroom: int = _DEFAULT_HEADROOM, hold_blocks: int = _DEFAULT_HOLD_BLOCKS, interval_ms: int = _DEFAULT_INTERVAL_MS) -> None:
        self.mode = mode
        self.headroom = headroom
        self.hold_blocks = hold_blocks
        self.interval_ms = interval_ms
        self.blocks = 0  # allocations made
        self.drops = 0  # release events
        self.alloc_failures = 0  # the INSTRUMENT's own MemoryErrors, never the system's
        self.stop = False
        self._held: list[bytearray] = []
        self._size_index = 0
        self._task: asyncio.Task[None] | None = None

    def _next_size(self) -> int:
        size = _BLOCK_SIZES[self._size_index % len(_BLOCK_SIZES)]
        self._size_index += 1
        return size

    def _release(self) -> None:
        # Half, not all: the heap must keep moving rather than emptying back to a clean slate,
        # which is what makes this fragmentation pressure instead of a sawtooth.
        if self._held:
            self._held = self._held[len(self._held) // 2 :]
            self.drops += 1

    def _step(self) -> None:
        size = self._next_size()
        if self.mode == MODE_FRAGMENT and gc.mem_free() < self.headroom + size:
            self._release()
            return
        try:
            self._held.append(bytearray(size))
            self.blocks += 1
        except MemoryError:
            # Counted, never raised. In exhaust mode this is the instrument doing its job; in
            # fragment mode it means the headroom was set too low for this workload - either way
            # it is the instrument's own event, distinct from any MemoryError the system raises.
            self.alloc_failures += 1
            self._held = []
        if len(self._held) > self.hold_blocks:
            self._release()

    def report(self) -> str:
        return f"MEMPRESSURE mode={self.mode} blocks={self.blocks} drops={self.drops} allocfail={self.alloc_failures} free={gc.mem_free()}"

    def stats(self) -> "dict[str, object]":
        return {"mode": self.mode, "blocks": self.blocks, "drops": self.drops, "alloc_failures": self.alloc_failures}

    async def run(self) -> None:
        print(f"MEMPRESSURE ACTIVE mode={self.mode} headroom={self.headroom} hold_blocks={self.hold_blocks} threshold={gc.threshold()}")
        next_report = time.ticks_add(time.ticks_ms(), _REPORT_INTERVAL_MS)
        while not self.stop:
            self._step()
            if time.ticks_diff(next_report, time.ticks_ms()) <= 0:
                # Printed, not returned: the host reads pressure progress off the serial log without
                # interrupting the live system (SPECIFICATION.md Part E.9).
                print(self.report())
                next_report = time.ticks_add(time.ticks_ms(), _REPORT_INTERVAL_MS)
            await asyncio.sleep_ms(self.interval_ms)
        self._held = []

    def start_task(self) -> "asyncio.Task[None]":
        self._task = asyncio.create_task(self.run())
        return self._task

    async def stop_and_join(self) -> None:
        self.stop = True
        await asyncio.sleep_ms(self.interval_ms * 4)
        if self._task is not None:
            self._task.cancel()
        self._held = []
        gc.collect()  # instrument teardown, after the measured window - never during one


_ACTIVE: "Pressure | None" = None


def start(mode: str = MODE_FRAGMENT, **kwargs: int) -> Pressure:
    """Module-level entry point used by a --memory-pressure boot entry and by device scripts."""
    global _ACTIVE
    _ACTIVE = Pressure(mode, **kwargs)
    _ACTIVE.start_task()
    return _ACTIVE


def active() -> "Pressure | None":
    return _ACTIVE
