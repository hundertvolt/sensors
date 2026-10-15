"""Flash-tier heap layout after the whole boot sequence, one test per arm: the twin's high-band bound
(tests_scripts/test_digital_twin_boot_contiguity.py) holds on the live arm and is broken on the suppressed one
(SPECIFICATION.md Part I.4(f.1)); every figure is noted with the image it was taken on."""

import ast
import json
from typing import TYPE_CHECKING

import heap_map
from error_log_helpers import code
from harness import DEVICE_SCRIPTS_DIR, REPO_ROOT, bench_device, crash_lines, parse_facts

if TYPE_CHECKING:
    from collections.abc import Callable

    from harness import Board

COVERS_TWIN_SCENARIOS: tuple[str, ...] = ("construction",)

_TWIN_BOUNDS = REPO_ROOT / "tests_scripts" / "test_digital_twin_boot_contiguity.py"
# @tunable l3.heap_layout_script_timeout_s = 120.0
_LAYOUT_SCRIPT_TIMEOUT_S = 120.0
_UNRETRIEVED = "UNRETRIEVED"  # the script's always-printing report of a task that died unawaited
_CONFIG_LOST = code("W", "CONFIG_LOST")


def _high_band_blocks(arm: str, board: "Board", result_note: "Callable[[str], None]") -> "tuple[int, int]":
    # Runs one arm and counts the new blocks between the seam map and the starter loop's end that sit more than the
    # twin's high band above the seam, as the twin's own check counts them; returns (count, the bound).
    output = board.run_isolated(DEVICE_SCRIPTS_DIR / "heap_layout_after_full_boot_sequence.py", timeout_s=_LAYOUT_SCRIPT_TIMEOUT_S, ARM=arm)
    facts = parse_facts(output)
    assert facts.get("arm") == arm, f"the script ran another arm: {facts}"
    assert facts.get("starter_loop_done") is True and facts.get("timers_done") is True, f"{arm}: a boot list did not complete within its bound: {facts}"
    # A scratch build over a SYSTEM chunk holding history logs CONFIG_LOST, its config file being absent in the scratch
    # directory; any other entry is a degraded stagger or a starter that raised.
    system = facts.get("system")
    assert isinstance(system, dict), f"{arm}: no SYSTEM log fact: {facts}"
    logged = [(t, n) for t, n in zip(system.get("ErrType", []), system.get("ErrNum", []), strict=True) if t != "N"]
    assert all(entry == ("W", _CONFIG_LOST) for entry in logged), f"{arm}: SYSTEM logged during the boot lists: {system}"
    died = crash_lines(output.splitlines()) + [line for line in output.splitlines() if line.startswith(_UNRETRIEVED)]
    assert not died, f"{arm}: a traceback, an allocation failure or a task death in the measured boot:\n" + "\n".join(died)
    maps = heap_map.parse_labelled(output)
    assert "batch_00" in maps and "after_starter_loop_end" in maps, f"{arm}: the seam or the starter-loop map is missing:\n{output}"
    seam, after = maps["batch_00"], maps["after_starter_loop_end"]
    change = heap_map.delta(seam, after)
    seam_top = seam.total_bytes - seam.free_above_top_survivor
    band, bound = _twin_bound("_HIGH_BAND"), _twin_bound("_HIGH_BAND_BLOCKS_MAX")
    high = sum(1 for offset in change.new_offsets if offset * change.block_bytes - seam_top > band)
    result_note(f"{arm} arm on {_image()}: {high} new blocks above the {band} B high band (bound {bound}); counts {facts.get('counts')}, boot {facts.get('boot_ms')}, gc.threshold {facts.get('gc_threshold')}")
    return high, bound


def _image() -> str:
    # The image the figures belong to: the bench build's record beside its .uf2 when one exists (build_firmware.py).
    record = REPO_ROOT / "build" / f"firmware-{bench_device()}.json"
    if not record.is_file():
        return f"{bench_device()} image with no record at {record.relative_to(REPO_ROOT)}"
    data = json.loads(record.read_text(encoding="utf-8"))
    return f"{bench_device()} image {data.get('BuildDate')} commit {data.get('commit')} dirty {data.get('dirty')}"


def _integer(node: ast.expr) -> int:
    # An integer constant or a product of them (`32 * 1024`), evaluated from its AST.
    if isinstance(node, ast.Constant) and isinstance(node.value, int):
        return node.value
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mult):
        return _integer(node.left) * _integer(node.right)
    raise AssertionError(f"{_TWIN_BOUNDS.name}: not an integer constant expression: {ast.unparse(node)}")


def _twin_bound(name: str) -> int:
    # One module-level integer constant of the twin's bound file, read by AST (never imported).
    for node in ast.parse(_TWIN_BOUNDS.read_text(encoding="utf-8")).body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) and node.targets[0].id == name:
            return _integer(node.value)
    raise AssertionError(f"{_TWIN_BOUNDS.name} no longer declares {name}")


def test_the_live_arm_keeps_the_boot_survivors_under_the_high_band(board: "Board", result_note: "Callable[[str], None]") -> None:
    high, bound = _high_band_blocks("collects", board, result_note)
    assert high <= bound, f"with the boot's placement collects live, {high} new blocks sit above the high band, over the twin's {bound}"


def test_the_suppressed_arm_breaks_the_high_band(board: "Board", result_note: "Callable[[str], None]") -> None:
    # The control: a bound the broken configuration also satisfies is no guard.
    high, bound = _high_band_blocks("suppressed", board, result_note)
    assert high > bound, f"with the per-unit collects suppressed only {high} new blocks sat above the high band, inside the twin's {bound} - the bound no longer detects the defect it exists for"
