"""Included into device scripts at render: the largest contiguous block (a doubling search on bytearray(n), the
allocation shape a real buffer needs), its HEAP report line, retried while the probe pins its own buffer, and the
collected block map (SPECIFICATION.md Part I). Includes map_dump.py for the map itself."""

import gc

# @include _shared/map_dump.py

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from _shared.map_dump import dump

# Search bounds: 64 B is below anything worth reporting; 192 KiB is above the RP2040's free heap, so the search
# always converges on a real failure rather than running off the top.
# @tunable l3.heap_probe_min = 64
_PROBE_MIN = 64
# @tunable l3.heap_probe_max_kib = 192
_PROBE_MAX = 192 * 1024
# Rereads while the probe still holds its own buffer through a stale root (one has always been enough).
# @tunable l3.heap_probe_retries = 3
_PROBE_RETRIES = 3


def _report(label: str) -> "tuple[int, int, int]":
    gc.collect()
    free, base = gc.mem_free(), gc.mem_alloc()
    largest = largest_block()
    gc.collect()
    retained = gc.mem_alloc() - base
    print(f"HEAP {label}: free={free} alloc={gc.mem_alloc()} largest_block={largest} retained={retained} pct={largest * 100 // max(free, 1)}")
    return free, largest, retained


def dump_map(label: str) -> None:
    gc.collect()
    dump(label)


def largest_block() -> int:
    gc.collect()
    low, high = 0, _PROBE_MAX
    while low < high:
        mid = (low + high + 1) // 2
        if mid < _PROBE_MIN:
            break
        try:
            probe = bytearray(mid)
        except MemoryError:
            high = mid - 1
        else:
            del probe
            low = mid
        gc.collect()
    return low


def report_checked(label: str) -> "tuple[int, int]":
    # A probe can pin its own buffer; every later attempt then converges on the pinned size, always _PROBE_MAX >> k
    # (HEAP_FRAGMENTATION_MEASUREMENTS.md M2.2). retained > 0 is that state, and a rerun from a fresh frame clears it.
    free, largest, retained = _report(label)
    attempt = 0
    while retained >= _PROBE_MIN and attempt < _PROBE_RETRIES:
        attempt += 1
        free, largest, retained = _report(f"{label}_retry{attempt}")
    if retained >= _PROBE_MIN:
        print(f"WARNING {label}: probe still holding {retained} B after {_PROBE_RETRIES} rereads - largest_block is a floor, not a figure")
    return free, largest
