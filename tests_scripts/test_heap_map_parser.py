"""Pins tests_hardware/heap_map.py against real `micropython.mem_info(1)` output. It gates a real
hardware assertion, and its dangerous failure mode is silent: a truncated capture reads as a heap
with an enormous free run at the end, turning a regression into a pass."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tests_hardware"))

import heap_map  # noqa: E402  (the sys.path line above is what makes this importable)

# A real dump, trimmed to four map lines: 64 blocks per line, 0x800 per line = 32 B per block (the
# Unix port's size; the rp2 port's is 16, and the parser derives it rather than assuming either).
_REAL = """GC: total: 8192, used: 2048, free: 6144
 No. of 1-blocks: 39, 2-blocks: 23, max blk sz: 128, max free sz: 128
GC memory layout; from 5593dbb45640:
00000000: hh=hhLhhSh===h========hhhBA.hBhLAAh=hh=Ah=Ah=Ah=Ah=====hhh=AAh=h
00000800: ================================================================
00001000: ................................................................
00001800: ................................................................
"""


def _parsed() -> heap_map.HeapMap:
    return heap_map.parse(_REAL)


def test_block_size_is_derived_from_the_offset_step_not_assumed() -> None:
    assert _parsed().block_bytes == 32
    assert _parsed().heap_blocks == 256


def test_the_two_independent_largest_free_run_figures_agree() -> None:
    # gc_dump_info's `max free sz` is counted by the VM; largest_free_run_from_map is reconstructed
    # from the map. They come from different code paths, so agreement is a real cross-check.
    parsed = _parsed()
    assert parsed.largest_free_run == 128 * 32
    assert parsed.largest_free_run_from_map == parsed.largest_free_run


def test_free_above_top_survivor_measures_the_run_after_the_last_allocated_block() -> None:
    assert _parsed().free_above_top_survivor == 128 * 32


def test_a_survivor_at_the_very_top_collapses_free_above_top_survivor() -> None:
    # The pathology the hardware assertion exists to catch: one long-lived object at the top of the
    # heap, with everything else unchanged.
    colonised = _REAL[:-2] + "h\n"
    assert heap_map.parse(colonised).free_above_top_survivor == 0
    assert heap_map.parse(colonised).largest_free_run_from_map == 127 * 32


def test_abbreviated_all_free_runs_are_expanded_back_to_blocks() -> None:
    abbreviated = """GC: total: 8192, used: 2048, free: 6144
 No. of 1-blocks: 1, 2-blocks: 1, max blk sz: 8, max free sz: 128
GC memory layout; from 0x1:
00000000: hh=hhLhhSh===h========hhhBA.hBhLAAh=hh=Ah=Ah=Ah=Ah=====hhh=AAh=h
00000800: ================================================================
       (2 lines all free)
"""
    parsed = heap_map.parse(abbreviated)
    assert parsed.heap_blocks == 256
    assert parsed.free_above_top_survivor == 128 * 32


def test_deciles_place_every_allocated_block_and_add_up() -> None:
    parsed = _parsed()
    assert sum(parsed.deciles) == parsed.heap_blocks - sum(run // parsed.block_bytes for run in parsed.free_runs)
    assert parsed.deciles[5:] == [0, 0, 0, 0, 0]


def test_gaps_at_least_counts_independent_runs() -> None:
    parsed = _parsed()
    assert parsed.gaps_at_least(4096) == 1
    assert parsed.gaps_at_least(8192) == 0


@pytest.mark.parametrize(
    ("text", "because"),
    [
        ("nothing here at all", "no totals line"),
        (_REAL.replace("GC: total: 8192, used: 2048, free: 6144\n", ""), "totals line missing"),
        (_REAL.replace("00001800: " + "." * 64 + "\n", ""), "a map line dropped mid-capture"),
        ("\n".join(_REAL.splitlines()[:4]) + "\n", "only one map line, so no offset step"),
    ],
)
def test_a_damaged_capture_raises_rather_than_reporting_a_healthy_heap(text: str, because: str) -> None:
    # Each of these would otherwise produce a plausible-looking result, and every one of them errs
    # toward "more free space than there is" - the direction that hides a regression.
    with pytest.raises(heap_map.HeapMapError):
        heap_map.parse(text)
    assert because  # names the case in the parametrize id


def test_two_heap_areas_are_refused_rather_than_silently_measured_as_one() -> None:
    with pytest.raises(heap_map.HeapMapError):
        heap_map.parse(_REAL + _REAL)


def test_parse_labelled_picks_out_each_marked_block() -> None:
    doubled = f"=== MAP first ===\n{_REAL}=== ENDMAP first ===\nnoise\n=== MAP second ===\n{_REAL}=== ENDMAP second ===\n"
    found = heap_map.parse_labelled(doubled)
    assert sorted(found) == ["first", "second"]
    assert found["first"].heap_blocks == 256


def _with_top_block_allocated() -> heap_map.HeapMap:
    return heap_map.parse(_REAL[:-2] + "h\n")


def test_delta_reports_only_what_the_second_map_added() -> None:
    # The whole point: a block already allocated in `before` is not the boot's doing, however high
    # it sits, so it must not show up here. This synthetic heap is 256 blocks of 32 B, so the top
    # 2,048 B is its last 64 - the added run sits at 128-191, just below it.
    before = _with_top_block_allocated()
    after = heap_map.parse(_REAL.replace("00001000: " + "." * 64, "00001000: " + "h" * 64)[:-2] + "h\n")
    placed = heap_map.delta(before, after)
    assert len(placed.new_offsets) == 64
    assert placed.new_above(2048) == 0
    assert placed.highest_new_pct() == 74


def test_delta_catches_a_survivor_placed_in_the_long_heap() -> None:
    before = _parsed()
    after = _with_top_block_allocated()
    placed = heap_map.delta(before, after)
    assert placed.new_offsets == [255]
    assert placed.new_above(2048) == 1
    assert placed.highest_new_pct() == 99


def test_delta_of_a_map_against_itself_is_empty() -> None:
    placed = heap_map.delta(_parsed(), _parsed())
    assert placed.new_offsets == []
    assert placed.highest_new_pct() == -1
    assert placed.new_above(2048) == 0


def test_delta_refuses_two_maps_from_different_heaps() -> None:
    # Offsets only name the same addresses within one interpreter session; comparing across two
    # would silently report garbage rather than fail.
    bigger = heap_map.parse(_REAL.replace("total: 8192", "total: 10240") + "00002000: " + "." * 64 + "\n")
    assert bigger.heap_blocks == 320
    with pytest.raises(heap_map.HeapMapError):
        heap_map.delta(_parsed(), bigger)


def test_new_above_a_region_larger_than_the_heap_counts_everything() -> None:
    # Asking for the top 16 KB of an 8 KB heap is the whole heap, not an error - the real device
    # heap is far larger than any region these tests ask about, so this only guards the arithmetic.
    placed = heap_map.delta(_parsed(), _with_top_block_allocated())
    assert placed.new_above(16384) == len(placed.new_offsets) == 1
