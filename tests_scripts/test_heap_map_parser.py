"""Pins tests_hardware/heap_map.py against real `micropython.mem_info(1)` output. It gates a real
hardware assertion, and its dangerous failure mode is silent: a truncated capture reads as a heap
with an enormous free run at the end, turning a regression into a pass."""

from __future__ import annotations

import re
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


def test_a_map_with_nothing_allocated_at_all_is_refused() -> None:
    # The interpreter is running the dump, so its own frame is allocated somewhere in it. An
    # all-free map means the capture lost the kinds and kept the geometry - the deciles below
    # would then read as a perfectly empty heap rather than as a broken read.
    all_free = _REAL.replace("00000000: " + _REAL.splitlines()[3].split(": ")[1], "00000000: " + "." * 64).replace("00000800: " + "=" * 64, "00000800: " + "." * 64)
    # Matched on the message: a mis-built fixture here would raise one of the other four and
    # pass this test while proving nothing.
    with pytest.raises(heap_map.HeapMapError, match="no allocated block at all"):
        heap_map.parse(all_free)


def test_the_map_summary_renders_every_figure_a_failing_assertion_quotes() -> None:
    # summary() is only ever called from a real-hardware failure message, so a defect in it would
    # surface as an error inside the diagnostic of a run that already cost bench time.
    text = _parsed().summary()
    for field in ("used=2048", "free=6144", "largest_free_run=4096", "free_above_top_survivor=4096", "gaps>=4K=1", "gaps>=16K=0"):
        assert field in text, f"{field!r} missing from the map summary: {text!r}"
    assert f"deciles={_parsed().deciles}" in text


def test_the_delta_summary_renders_every_figure_too() -> None:
    placed = heap_map.delta(_parsed(), _with_top_block_allocated())
    text = placed.summary()
    for field in ("new_blocks=1", "highest_new_pct=99", "new_in_top16K=1", "new_in_top32K=1"):
        assert field in text, f"{field!r} missing from the delta summary: {text!r}"


def test_an_empty_delta_summary_still_renders_rather_than_dividing_by_zero() -> None:
    # The case a passing run produces: nothing placed high, so highest_new_pct() takes its -1
    # branch. A guard that fails on the very next device would print this one first.
    assert "highest_new_pct=-1" in heap_map.delta(_parsed(), _parsed()).summary()


# The MAP/ENDMAP envelope is a contract between ONE parser regex and THREE independent emitters -
# two device scripts and the twin probe. A drift on either side makes parse_labelled() find
# nothing, and on the flash tier that only surfaces in a bench session.
_EMITTERS = (
    "tests_hardware/device_scripts/heap_layout_after_full_boot_sequence.py",
    "tests_hardware/device_scripts/heap_headroom_after_full_system_build.py",
    "tests/_boot_contiguity_probe.py",
)


def _emitted_envelope(source: str, label: str) -> tuple[str, str]:
    """The open/close lines one emitter would actually print for `label`, from its own f-strings."""
    opens = re.findall(r'print\(f"(=== MAP \{label\} ===)"\)', source)
    closes = re.findall(r'print\(f"(=== ENDMAP \{label\} ===)"\)', source)
    assert len(opens) == 1 and len(closes) == 1, f"expected one MAP and one ENDMAP print, found {len(opens)}/{len(closes)}"
    return opens[0].replace("{label}", label), closes[0].replace("{label}", label)


@pytest.mark.parametrize("emitter", _EMITTERS)
def test_every_emitters_own_envelope_round_trips_through_the_parser(emitter: str) -> None:
    # Built from the emitter's real format string rather than from a copy of it here, so a changed
    # marker on either side fails this instead of silently yielding an empty result on the bench.
    opened, closed = _emitted_envelope((REPO_ROOT / emitter).read_text(), "after_build_system")
    found = heap_map.parse_labelled(f"noise before\n{opened}\n{_REAL}{closed}\ntrailing noise\n")
    assert sorted(found) == ["after_build_system"], f"{emitter}'s MAP envelope is not what parse_labelled() looks for"
    assert found["after_build_system"].heap_blocks == 256


def test_an_unterminated_block_is_skipped_rather_than_swallowing_the_rest_of_the_log() -> None:
    # A capture cut off mid-dump: the label must not come back with a half map, and a later
    # complete block in the same log must still be found.
    found = heap_map.parse_labelled(f"=== MAP lost ===\n{_REAL}=== MAP kept ===\n{_REAL}=== ENDMAP kept ===\n")
    assert sorted(found) == ["kept"]


def test_a_labels_own_endmap_is_what_closes_it() -> None:
    # The backreference in the parser's regex: two interleaved blocks must not pair up across
    # labels, which is what a plain `.*?ENDMAP` would do.
    found = heap_map.parse_labelled(f"=== MAP first ===\n{_REAL}=== ENDMAP second ===\n")
    assert found == {}


def test_placeable_counts_capacity_not_runs() -> None:
    # The distinction that made a real bench row fail: one big run is a single gap but holds many
    # blocks, and a simultaneous demand is a question about capacity, not about how many gaps exist.
    parsed = _parsed()
    assert parsed.gaps_at_least(4096) == 1
    assert parsed.placeable(4096) >= parsed.gaps_at_least(4096)
    assert parsed.placeable(1) == sum(parsed.free_runs)


def _need_output(*rungs: tuple[int, list[tuple[str, str, str]]]) -> str:
    # allocation_need_per_source.py's own line shapes: SIEVE, a mem_info() summary, then TRY/RES.
    lines = ["CHURN route:/status 1000", "BLOCK=16 PROBES=2"]
    for max_free_blocks, probes in rungs:
        lines += ["SIEVE 1", "GC: total: 1000, used: 10, free: 990", f" No. of 1-blocks: 1, 2-blocks: 0, max blk sz: 4, max free sz: {max_free_blocks}"]
        for label, logged, result in probes:
            lines.append(f"TRY {label}")
            if logged:
                lines.append(logged)
            lines.append(f"RES {label} {result}")
    lines.append("RESULT: PASS")
    return "\n".join(lines)


def test_allocation_need_is_the_first_rung_from_which_every_larger_one_is_clean() -> None:
    text = _need_output(
        (8, [("a", "", "fail"), ("b", "", "ok")]),
        (16, [("a", "", "ok"), ("b", "", "fail")]),  # b fails again higher up: its earlier ok was luck
        (32, [("a", "", "ok"), ("b", "", "ok")]),
    )
    assert heap_map.parse_allocation_need(text) == {"a": 16 * 16, "b": 32 * 16}


def test_a_caught_and_logged_allocation_failure_counts_as_a_failure() -> None:
    # I.4(e): a probe that degrades internally still returns normally, so RES says ok - only the log
    # between its TRY and RES shows it. That must not read as a clean pass.
    text = _need_output(
        (8, [("a", "Status stream source failed: SYSTEM memory allocation failed, allocating 300 bytes", "ok")]),
        (16, [("a", "", "ok")]),
    )
    assert heap_map.parse_allocation_need(text) == {"a": 16 * 16}


def test_a_probe_that_never_succeeds_reads_as_none() -> None:
    text = _need_output((8, [("a", "", "fail")]), (16, [("a", "", "fail")]))
    assert heap_map.parse_allocation_need(text) == {"a": None}
