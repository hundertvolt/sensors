"""Parses `micropython.mem_info(1)`'s block map into the layout metrics the heap tests assert on.
The device cannot read it back - it goes to the platform print, not `sys.stdout` - so the map is
captured host-side out of `Board.run_isolated()`'s output and measured here."""

from __future__ import annotations

import re
from typing import NamedTuple

# `gc_dump_alloc_table()` emits 64 blocks per line [SRC, py/gc.c], prefixed by the byte offset, and
# abbreviates two or more consecutive all-free lines. The block size is never printed; it is derived
# from the offset step, which is the only place it appears.
_BLOCKS_PER_LINE = 64
_MAP_LINE = re.compile(r"^([0-9a-f]{8}): (\S.*)$")
_ABBREVIATED = re.compile(r"^\s*\((\d+) lines all free\)\s*$")
_TOTALS = re.compile(r"^GC: total: (\d+), used: (\d+), free: (\d+)")
_SIZES = re.compile(r"max blk sz: (\d+), max free sz: (\d+)")
_AREA = re.compile(r"^GC memory layout; from ")
_FREE = "."


class HeapMap(NamedTuple):
    """One parsed `mem_info(1)` dump. Byte figures throughout; `deciles` counts allocated blocks."""

    kinds: str
    block_bytes: int
    heap_blocks: int
    total_bytes: int
    used_bytes: int
    free_bytes: int
    largest_free_run: int
    largest_free_run_from_map: int
    free_above_top_survivor: int
    lowest_survivor_offset: int
    free_runs: list[int]
    deciles: list[int]

    def gaps_at_least(self, size: int) -> int:
        return sum(1 for run in self.free_runs if run >= size)

    def placeable(self, size: int) -> int:
        """How many `size`-byte blocks the heap could still place. Not gaps_at_least(): one 40 KB
        run is ONE gap but holds nineteen 2 KB buffers, and it is the capacity that has to cover a
        simultaneous demand (REAL_HARDWARE_HANDOVER_CONNECTION_SCALING.md 5B rule 10)."""
        return sum(run // size for run in self.free_runs)

    def summary(self) -> str:
        return (
            f"used={self.used_bytes} free={self.free_bytes} largest_free_run={self.largest_free_run} "
            f"free_above_top_survivor={self.free_above_top_survivor} gaps>=4K={self.gaps_at_least(4096)} "
            f"gaps>=16K={self.gaps_at_least(16384)} deciles={self.deciles}"
        )


class HeapMapError(ValueError):
    """The captured text is not a usable `mem_info(1)` dump - malformed, truncated, or absent."""


def parse(text: str) -> HeapMap:
    """Parse one `mem_info(1)` dump. Raises HeapMapError rather than returning something plausible:
    a truncated capture (a dropped USB CDC chunk, say) would otherwise read as a heap with a huge
    free run at the end, which is exactly the direction that turns a real regression into a pass."""
    totals: tuple[int, int, int] | None = None
    reported_max_free: int | None = None
    offsets: list[int] = []
    kinds: list[str] = []
    areas = 0
    for raw in text.splitlines():
        if _AREA.match(raw):
            areas += 1
            continue
        totals_match = _TOTALS.match(raw)
        if totals_match:
            totals = (int(totals_match.group(1)), int(totals_match.group(2)), int(totals_match.group(3)))
            continue
        sizes_match = _SIZES.search(raw)
        if sizes_match:
            reported_max_free = int(sizes_match.group(2))
            continue
        abbreviated = _ABBREVIATED.match(raw)
        if abbreviated:
            kinds.append(_FREE * (int(abbreviated.group(1)) * _BLOCKS_PER_LINE))
            continue
        line_match = _MAP_LINE.match(raw)
        if line_match:
            offsets.append(int(line_match.group(1), 16))
            kinds.append(line_match.group(2).strip())

    if totals is None or reported_max_free is None:
        raise HeapMapError("no `GC: total:`/`max free sz:` line in the captured output - mem_info(1) did not run, or its output was lost")
    if areas > 1:
        raise HeapMapError(f"{areas} heap areas in the dump; these metrics assume the single area the rp2 port builds - read the raw map instead")
    if len(offsets) < 2:
        raise HeapMapError(f"only {len(offsets)} map lines captured - the block size is derived from the offset step, so two are the minimum")

    block_bytes = (offsets[1] - offsets[0]) // _BLOCKS_PER_LINE
    blocks = "".join(kinds)
    total_bytes, used_bytes, free_bytes = totals
    if block_bytes <= 0 or len(blocks) * block_bytes != total_bytes:
        raise HeapMapError(f"map covers {len(blocks)} blocks of {block_bytes} B against a reported total of {total_bytes} B - the capture is incomplete")

    free_runs: list[int] = []
    run = 0
    for kind in blocks:
        if kind == _FREE:
            run += 1
        elif run:
            free_runs.append(run * block_bytes)
            run = 0
    trailing_free = run * block_bytes
    if run:
        free_runs.append(trailing_free)

    allocated = [i for i, kind in enumerate(blocks) if kind != _FREE]
    if not allocated:
        raise HeapMapError("the map shows no allocated block at all, which cannot happen while the interpreter is running it")
    deciles = [0] * 10
    for index in allocated:
        deciles[min(9, index * 10 // len(blocks))] += 1

    return HeapMap(
        kinds=blocks,
        block_bytes=block_bytes,
        heap_blocks=len(blocks),
        total_bytes=total_bytes,
        used_bytes=used_bytes,
        free_bytes=free_bytes,
        largest_free_run=reported_max_free * block_bytes,
        largest_free_run_from_map=max(free_runs, default=0),
        free_above_top_survivor=trailing_free,
        lowest_survivor_offset=allocated[0] * block_bytes,
        free_runs=free_runs,
        deciles=deciles,
    )


class HeapDelta(NamedTuple):
    """What one stretch of code ADDED to the heap: blocks free in `before` and allocated in `after`.
    Position-independent by construction, and a LOWER bound - a block occupied in both maps is not
    attributed, even if the first occupant was freed in between (MEASUREMENTS 7G.5)."""

    block_bytes: int
    heap_blocks: int
    new_offsets: list[int]

    def new_above(self, top_bytes: int) -> int:
        """Newly allocated blocks within the topmost `top_bytes` of the heap."""
        first = self.heap_blocks - top_bytes // self.block_bytes
        return sum(1 for offset in self.new_offsets if offset >= first)

    def highest_new_pct(self) -> int:
        """How far up the heap the highest newly allocated block sits, 0-100; -1 if none."""
        return max(self.new_offsets) * 100 // self.heap_blocks if self.new_offsets else -1

    def summary(self) -> str:
        return (
            f"new_blocks={len(self.new_offsets)} highest_new_pct={self.highest_new_pct()} "
            f"new_in_top16K={self.new_above(16384)} new_in_top32K={self.new_above(32768)}"
        )


def delta(before: HeapMap, after: HeapMap) -> HeapDelta:
    """What `after` holds that `before` did not, block position by block position. Both must come
    from the same interpreter session, or the offsets name different addresses and the answer is
    meaningless - which is why a mismatch raises rather than comparing what it can."""
    if before.block_bytes != after.block_bytes or before.heap_blocks != after.heap_blocks:
        raise HeapMapError(
            f"the two maps describe different heaps ({before.heap_blocks}x{before.block_bytes} B against "
            f"{after.heap_blocks}x{after.block_bytes} B) - they must come from one session to be comparable",
        )
    return HeapDelta(
        block_bytes=after.block_bytes,
        heap_blocks=after.heap_blocks,
        new_offsets=[i for i, kind in enumerate(after.kinds) if kind != _FREE and before.kinds[i] == _FREE],
    )


def parse_labelled(text: str) -> dict[str, HeapMap]:
    """Every `MAP <label>` ... `ENDMAP <label>` block a device script emitted, keyed by label."""
    found: dict[str, HeapMap] = {}
    for match in re.finditer(r"^=== MAP (\S+) ===$(.*?)^=== ENDMAP \1 ===$", text, re.MULTILINE | re.DOTALL):
        found[match.group(1)] = parse(match.group(2))
    return found
