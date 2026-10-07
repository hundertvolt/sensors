"""The regression guard for SPECIFICATION.md Part I.4(f.1)'s boot-confined placement reset: boots
every real generated device under the Unix port and asserts the two one-time boot lists still place
their survivors low, measured through tests_hardware/heap_map.py - the board tier's own parser."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING, NamedTuple

import pytest
from _devices import DEVICE_NAMES
from _script_loader import load_script_module

# Same import route tests_scripts/test_heap_map_parser.py uses for the same file: the repo has no
# packages by design, so importing it as `tests_hardware.heap_map` would make mypy see one source
# file under two module names (confirmed - host_typecheck.ini's pass fails on exactly that).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tests_hardware"))

# No E402 suppression: ruff exempts a sys.path insert outright, and RUF100 fails an unused one.
from heap_map import HeapMap, delta, parse_labelled

if TYPE_CHECKING:
    from collections.abc import Callable

# scripts/test.sh's own MICROPYPATH, heap size and interpreter, so this measures what the suite
# measures. The heap size is deliberately NOT calibrated to a fill fraction: every bound below is
# an absolute offset from the seam, and those proved heap-size independent at 8M and 16M.
_MICROPYPATH = "build/generated_src:src:tests:frozen_modules:.frozen"
# @tunable l1.unix_heapsize = 16M
_HEAPSIZE = "16M"
_PROBE = "tests/_boot_contiguity_probe.py"
_GENERATED = Path(__file__).resolve().parent.parent / "build" / "generated_src"
# @tunable l0.boot_contiguity_probe_timeout_s = 120
_PROBE_TIMEOUT_S = 120

_ARM_LIVE = "collects"
_ARM_SUPPRESSED = "suppressed"

# Which devices get the suppressed control arm too: wozi is the exemplary variant the whole
# promotion is validated against, dev is the only board ever flashed. Running it for all six would
# double the subprocess count to prove the same thing six times.
_CONTROL_DEVICES = ("wozi", "dev")

_REQUIRED_MAPS = ("baseline", "batch_00", "after_batch", "after_starter_loop_end")

# Every bound is the worst reading measured across all six devices with the collects live, times a
# margin, with the best suppressed reading on the other side of it. Twin units (32 B blocks,
# x86-64) and twin-only - the board's own tripwire stays the hardware test.
#
# Re-derived on the settrace-FREE interpreter (SPECIFICATION.md Part E.5.2), which cost the batch's
# own reach its discrimination and left depth below the seam plus the whole sequence's reach as
# what carries it. Full re-derivation, and what the old bounds were: MEASUREMENTS archive §7L.7 and §7L.3.

# The batch's median new block must sit at least this far BELOW the seam's top survivor. The two
# margins are thin because the ARMS are only 2.07x apart here, not because the bound is sloppy -
# no split of that gap gives more than ~1.44x each way. _ARM_DEPTH_RATIO_MIN below is the strict half.
_BATCH_MEDIAN_DEPTH_MIN = 300 * 1024  # worst live 452,832 (1.47x); best suppressed 218,528 (1.41x under)

# The batch's own reach and band count no longer separate the arms (8,160 B and 0 in BOTH), so they
# are kept as plain regression tripwires rather than as proof the collects work: they catch a future
# module allocating high during the batch, which is a different defect and otherwise unguarded.

# Both lists together: the highest new block, and the median's depth.
_BOOT_REACH_MAX = 64 * 1024  # live 16,352 on every device (4.0x); best suppressed 141,632 (2.16x over)
_BOOT_MEDIAN_DEPTH_MIN = 256 * 1024  # worst live 356,576 (1.36x); best suppressed 108,352 (2.42x under)

# How many new blocks may sit more than this far above the seam: twice the live reach, zero live on every
# device, 703 (wozi) and 1,510 (dev) suppressed. A band near the suppressed reach counts only its edge; the
# slack is for one future large allocation that genuinely cannot fit a low hole, not for a drift in placement.
_HIGH_BAND = 32 * 1024
# @tunable l0.boot_contiguity_high_band_blocks_max = 32
_HIGH_BAND_BLOCKS_MAX = 32

# How much deeper the live arm must place than the suppressed one. A ratio between the two arms of
# the same run, so it needs no absolute bound and no unit - the strictest thing this file asserts.
# Measured: batch depth 2.36x (wozi) and 4.64x (dev); cumulative reach 12.96x and 13.93x.
# @tunable l0.boot_contiguity_arm_depth_ratio_min = 1.5
_ARM_DEPTH_RATIO_MIN = 1.5
# @tunable l0.boot_contiguity_arm_reach_ratio_min = 4.0
_ARM_REACH_RATIO_MIN = 4.0

# Retention must be arm-independent: the collects change WHERE the next survivor is born, never how
# much survives (MEASUREMENTS archive 7A.1's finding, which reproduces here at 0.05%). 1% is 19x that.
# @tunable l0.boot_contiguity_retention_tolerance = 0.01
_RETENTION_TOLERANCE = 0.01

# The allocation-failure markers every gate shares, from the hardware tier's harness
# (tests_scripts/test_memory_error_gate_agreement.py keeps the gates agreeing).
_MEMORY_ERROR_MARKERS: tuple[str, ...] = tuple(load_script_module(Path(__file__).resolve().parent.parent / "tests_hardware" / "harness.py", "harness").MEMORY_ERROR_MARKERS)

_COUNTER_LINE = re.compile(r"^(?:LISTS|COUNTS) (.*)$", re.MULTILINE)
_RING_LINE = re.compile(r"^RING (\S+) (\S+) (none|0x[0-9a-f]+) (\d+)$", re.MULTILINE)
_POOL_START = re.compile(r"^GC memory layout; from ([0-9a-fA-F]+):", re.MULTILINE)


class _ProbeRun(NamedTuple):
    # One boot of one device on one arm: the maps it dumped, the counters it printed, each UART bus's
    # receive ring (position -> bus -> (address, length), address None for no ring) and the heap's start.

    maps: dict[str, HeapMap]
    counters: dict[str, int]
    rings: dict[str, dict[str, tuple[int | None, int]]]
    pool_start: int | None


def _parse_rings(stdout: str) -> dict[str, dict[str, tuple[int | None, int]]]:
    found: dict[str, dict[str, tuple[int | None, int]]] = {}
    for label, bus, address, length in _RING_LINE.findall(stdout):
        found.setdefault(label, {})[bus] = (None if address == "none" else int(address, 16), int(length))
    return found


def _parse_counters(stdout: str) -> dict[str, int]:
    found: dict[str, int] = {}
    for match in _COUNTER_LINE.finditer(stdout):
        for field in match.group(1).split():
            name, _, value = field.partition("=")
            found[name] = int(value)
    return found


def _checked_probe_run(device: str, arm: str, completed: subprocess.CompletedProcess[str]) -> _ProbeRun:
    # One finished probe, judged: exit status, its own PASS line, no allocation-failure marker
    # (SPECIFICATION.md Part I.4(e)), and every map the bounds read.
    tail = f"{completed.stdout[-3000:]}\n{completed.stderr[-3000:]}"
    assert completed.returncode == 0, f"the probe failed for {device}/{arm} (exit {completed.returncode}):\n{tail}"
    assert "RESULT: PASS" in completed.stdout, f"the probe never reached its own PASS line for {device}/{arm}:\n{tail}"
    marked = [line for line in f"{completed.stdout}\n{completed.stderr}".splitlines() if any(marker in line for marker in _MEMORY_ERROR_MARKERS)]
    assert not marked, f"the probe for {device}/{arm} logged an allocation failure:\n" + "\n".join(marked)
    maps = parse_labelled(completed.stdout)
    missing = [label for label in _REQUIRED_MAPS if label not in maps]
    assert not missing, f"no usable map captured for {missing} on {device}/{arm} - the measurement would be vacuous:\n{tail}"
    pool = _POOL_START.search(completed.stdout)
    return _ProbeRun(maps, _parse_counters(completed.stdout), _parse_rings(completed.stdout), int(pool.group(1), 16) if pool else None)


@pytest.fixture(scope="session")
def generated_src(repo_root: Path) -> Path:
    # The probe imports `sensortask_<device>` and reads its wiring plan from here; scripts/test.sh
    # generates both before any tier runs. Failed, never skipped, when absent: a skip reads as a pass.
    path = repo_root / "build" / "generated_src"
    if not path.is_dir():
        pytest.fail(f"no generated device modules at {path} - scripts/test.sh generates them before the suites run")
    return path


@pytest.fixture(scope="session")
def boot_probe(
    repo_root: Path,
    micropython_bin: Path,
    generated_src: Path,
    tmp_path_factory: pytest.TempPathFactory,
) -> Callable[[str, str], _ProbeRun]:
    # Runs tests/_boot_contiguity_probe.py once per (device, arm) and caches the result: several
    # assertions over one boot rather than one boot each.
    assert generated_src.is_dir()  # the fixture above already failed if not; this keeps the dependency explicit
    cache: dict[tuple[str, str], _ProbeRun] = {}

    def run(device: str, arm: str) -> _ProbeRun:
        key = (device, arm)
        if key in cache:
            return cache[key]
        cfg_dir = tmp_path_factory.mktemp(f"cfg_{device}_{arm}")
        completed = subprocess.run(
            [str(micropython_bin), "-X", f"heapsize={_HEAPSIZE}", _PROBE, device, arm, f"{cfg_dir}/", "0"],
            cwd=repo_root,
            env=dict(os.environ, MICROPYPATH=_MICROPYPATH, TZ="UTC"),
            capture_output=True,
            text=True,
            timeout=_PROBE_TIMEOUT_S,
            check=False,
        )
        cache[key] = _checked_probe_run(device, arm, completed)
        return cache[key]

    return run


def _offsets_above_seam(before: HeapMap, after: HeapMap) -> list[int]:
    # Every block newly allocated between the two maps, as a signed byte offset from the top of
    # what `before` already had allocated. Negative means it went into a hole further down.
    change = delta(before, after)
    assert change.new_offsets, "no block was newly allocated between the two maps, so there is nothing to measure"
    seam_top = before.total_bytes - before.free_above_top_survivor
    return sorted(offset * change.block_bytes - seam_top for offset in change.new_offsets)


def _reach(before: HeapMap, after: HeapMap) -> int:
    return _offsets_above_seam(before, after)[-1]


def _median(before: HeapMap, after: HeapMap) -> int:
    offsets = _offsets_above_seam(before, after)
    return offsets[len(offsets) // 2]


def _blocks_above(before: HeapMap, after: HeapMap, band: int) -> int:
    return sum(1 for offset in _offsets_above_seam(before, after) if offset > band)


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_the_setup_batch_places_its_survivors_low(boot_probe: Callable[[str, str], _ProbeRun], device: str) -> None:
    # The emitted collects' own job (buildgen/codegen.py's batch): each one resets the allocator's
    # free-scan index, so the next module's permanent objects take the lowest fitting holes instead
    # of landing above the churn's high-water mark. Suppressing them moves this by 7.5x or more.
    maps = boot_probe(device, _ARM_LIVE).maps
    seam, after = maps["batch_00"], maps["after_batch"]
    depth, reach = -_median(seam, after), _reach(seam, after)
    high = _blocks_above(seam, after, _HIGH_BAND)
    assert depth >= _BATCH_MEDIAN_DEPTH_MIN, f"{device}: the setup batch's median new block sits only {depth} B below the seam, under the {_BATCH_MEDIAN_DEPTH_MIN} B bound - a collect is missing, or no longer resets placement"
    assert reach <= _BOOT_REACH_MAX, f"{device}: the setup batch's highest new block sits {reach} B above the seam, over the {_BOOT_REACH_MAX} B tripwire - something in the batch now allocates high"
    assert high <= _HIGH_BAND_BLOCKS_MAX, f"{device}: {high} of the batch's new blocks sit more than {_HIGH_BAND} B above the seam, over the {_HIGH_BAND_BLOCKS_MAX} allowed"


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_the_whole_boot_sequence_places_its_survivors_low(boot_probe: Callable[[str, str], _ProbeRun], device: str) -> None:
    # Both lists together - the batch plus start_and_check_tasks()'s starter loop, which archive 7A.3
    # measured as mattering as much as the batch. Read at the loop's own end, never after a settle:
    # the run phase undoes most of the gain within ~2 s and the position stops discriminating (MEASUREMENTS M3.9).
    maps = boot_probe(device, _ARM_LIVE).maps
    seam, after = maps["batch_00"], maps["after_starter_loop_end"]
    reach, depth = _reach(seam, after), -_median(seam, after)
    high = _blocks_above(seam, after, _HIGH_BAND)
    assert reach <= _BOOT_REACH_MAX, f"{device}: the whole boot sequence's highest new block sits {reach} B above the seam, over the {_BOOT_REACH_MAX} B bound"
    assert depth >= _BOOT_MEDIAN_DEPTH_MIN, f"{device}: the median new block sits only {depth} B below the seam, under the {_BOOT_MEDIAN_DEPTH_MIN} B bound"
    assert high <= _HIGH_BAND_BLOCKS_MAX, f"{device}: {high} new blocks sit more than {_HIGH_BAND} B above the seam, over the {_HIGH_BAND_BLOCKS_MAX} allowed"


@pytest.mark.parametrize("device", _CONTROL_DEVICES)
def test_suppressing_the_emitted_collects_breaks_both_bounds(boot_probe: Callable[[str, str], _ProbeRun], device: str) -> None:
    # The control arm, and the reason the bounds above mean anything: a bound the broken
    # configuration also satisfies is not a guard. The arm keeps only the seam's own anchor collect
    # (both arms need it to be comparable) and drops the per-module ones, so this UNDERSTATES.
    maps = boot_probe(device, _ARM_SUPPRESSED).maps
    seam, after = maps["batch_00"], maps["after_starter_loop_end"]
    batch_depth = -_median(seam, maps["after_batch"])
    boot_reach, boot_high = _reach(seam, after), _blocks_above(seam, after, _HIGH_BAND)
    assert batch_depth < _BATCH_MEDIAN_DEPTH_MIN, f"{device}: with every emitted collect suppressed the batch's median still sat {batch_depth} B below the seam, past the {_BATCH_MEDIAN_DEPTH_MIN} B bound - the bound no longer detects the defect it exists for"
    assert boot_reach > _BOOT_REACH_MAX, f"{device}: with every collect suppressed the whole boot sequence still stayed inside the {_BOOT_REACH_MAX} B bound (reach {boot_reach} B)"
    assert boot_high > _HIGH_BAND_BLOCKS_MAX, f"{device}: with every collect suppressed only {boot_high} new blocks sat more than {_HIGH_BAND} B above the seam, still inside the {_HIGH_BAND_BLOCKS_MAX} allowed"


@pytest.mark.parametrize("device", _CONTROL_DEVICES)
def test_the_live_arm_places_strictly_deeper_than_the_suppressed_one(boot_probe: Callable[[str, str], _ProbeRun], device: str) -> None:
    # The mechanism as a RATIO between the two arms of the same run, which is what the absolute
    # bounds above only approximate: no unit, no heap-size term, and no margin spent on the gap
    # between devices. A change that moved both arms together would pass every bound and fail here.
    live, suppressed = boot_probe(device, _ARM_LIVE).maps, boot_probe(device, _ARM_SUPPRESSED).maps
    live_depth, suppressed_depth = -_median(live["batch_00"], live["after_batch"]), -_median(suppressed["batch_00"], suppressed["after_batch"])
    live_reach, suppressed_reach = _reach(live["batch_00"], live["after_starter_loop_end"]), _reach(suppressed["batch_00"], suppressed["after_starter_loop_end"])
    # Multiplied rather than divided, so the bound holds over the whole domain: either side of
    # either quotient can legitimately go negative (a median or a reach BELOW the seam), which
    # flips a ratio's sense and would fail this for a mechanism working better than measured.
    assert live_depth >= _ARM_DEPTH_RATIO_MIN * suppressed_depth, f"{device}: the batch's median sits {live_depth} B below the seam with the collects live against {suppressed_depth} B without - under the {_ARM_DEPTH_RATIO_MIN}x separation this asserts"
    assert suppressed_reach >= _ARM_REACH_RATIO_MIN * live_reach, f"{device}: the whole sequence reaches {suppressed_reach} B above the seam with the collects suppressed against {live_reach} B with them live - under the {_ARM_REACH_RATIO_MIN}x separation this asserts"


@pytest.mark.parametrize("device", _CONTROL_DEVICES)
def test_the_collects_move_placement_and_not_retention(boot_probe: Callable[[str, str], _ProbeRun], device: str) -> None:
    # I.4(f.1)'s central claim as an assertion rather than a doc sentence: a placement reset, not
    # hygiene. If the arms ever diverge on how much SURVIVES, the collects have started compensating
    # for a leak, and the exception's whole justification has changed.
    live = boot_probe(device, _ARM_LIVE).maps["after_batch"].used_bytes
    suppressed = boot_probe(device, _ARM_SUPPRESSED).maps["after_batch"].used_bytes
    drift = abs(live - suppressed) / max(live, 1)
    assert drift <= _RETENTION_TOLERANCE, f"{device}: {live} B survives the batch with the collects live against {suppressed} B without them ({drift:.2%}) - that is a consumption difference, and these collects only move placement"


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_a_real_boot_fires_exactly_the_collects_the_static_guards_count(
    boot_probe: Callable[[str, str], _ProbeRun],
    repo_root: Path,
    device: str,
) -> None:
    # Derived from each list's own length, never from the emitted line count: the effect measured
    # above anchors its seam at the FIRST collect, so a dropped leading collect would re-anchor it
    # silently - this is the assertion that keeps that anchor honest, and it is what then fails.
    counters = boot_probe(device, _ARM_LIVE).counters
    source = (repo_root / "build" / "generated_src" / f"sensortask_{device}.py").read_text()
    setup_calls = len(re.findall(r"^\s*await \w+\.setup\(\)\s*$", source, re.MULTILINE))
    assert setup_calls > 0, f"{device}: the generated build_system() has no setup() calls at all, so this count would be vacuous"
    assert counters["batch_collects"] == setup_calls + 1, f"{device}: the generated build_system() awaits {setup_calls} setup() calls, so it must collect {setup_calls + 1} times (one before the batch, one after each module) - a real boot fired {counters['batch_collects']}"
    assert counters["starter_collects"] == counters["starters"] + 1, f"{device}: {counters['starters']} task starters ran but the loop collected {counters['starter_collects']} times, not {counters['starters'] + 1}"
    assert source.count("gc.collect()") == setup_calls + 1, f"{device}: the generated module carries {source.count('gc.collect()')} gc.collect() lines against {setup_calls} setup() calls - one before the batch and one after each module is {setup_calls + 1}"


def _uart_link_devices() -> list[str]:
    # Every device whose wiring builds a UART link: the ones whose setup allocates receive rings.
    return [device for device in DEVICE_NAMES if "uart_link" in json.loads((_GENERATED / f"sensortask_{device}_wiring_plan.json").read_text())["instances"]]


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_the_uart_receive_rings_land_with_the_boot_survivors(boot_probe: Callable[[str, str], _ProbeRun], device: str) -> None:
    # Each link allocates its DMA ring in its own setup(), a unit of the one-time batch, so the placement
    # reset puts it low with the other survivors (SPECIFICATION.md I.4(f.1)), and its address never moves:
    # the same ring after the starter loop, nothing reallocated once the batch ended.
    if device not in _uart_link_devices():
        pytest.skip(f"{device} builds no UART link, so it has no receive ring")
    run = boot_probe(device, _ARM_LIVE)
    after_batch, after_loop = run.rings.get("after_batch", {}), run.rings.get("after_starter_loop_end", {})
    plan = json.loads((_GENERATED / f"sensortask_{device}_wiring_plan.json").read_text())
    assert len(after_batch) == len(plan["uart"]), f"{device}: the probe reported rings for {sorted(after_batch)}, not one per bus of the {len(plan['uart'])}-bus link"
    assert after_loop == after_batch, f"{device}: a receive ring moved or appeared after the setup batch: {after_batch} then {after_loop}"
    assert run.pool_start is not None, f"{device}: the probe's maps carry no heap start, so no ring can be placed"
    seam = run.maps["batch_00"]
    seam_top = seam.total_bytes - seam.free_above_top_survivor
    for bus, (address, length) in sorted(after_batch.items()):
        assert address is not None, f"{device}: {bus} came out of the setup batch with no receive ring"
        above = address + length - run.pool_start - seam_top
        assert above <= _HIGH_BAND, f"{device}: {bus}'s receive ring ends {above} B above the seam, past the {_HIGH_BAND} B high band - it is not placed with the boot's survivors"
    batch, before = run.maps["after_batch"], seam
    windows = sum(length for _address, length in after_batch.values())
    print(f"{device}: {len(after_batch)} receive rings, {windows} B of windows; largest free run {before.largest_free_run} B before the batch, {batch.largest_free_run} B after")


_BOARD_SCRIPT = "tests_hardware/device_scripts/heap_layout_after_full_boot_sequence.py"
# The probe's header claims it mirrors the board script's bounds, so that a twin reading and a
# board reading are taken at the same positions of the same sequence. Nothing pinned that claim.
_MIRRORED_BOUNDS = ("_STARTER_LOOP_TIMEOUT_MS", "_STARTER_LOOP_GRACE_MS", "_TIMERS_TIMEOUT_S")


def _int_constants(source: str, names: tuple[str, ...]) -> dict[str, int]:
    found: dict[str, int] = {}
    for name in names:
        match = re.search(rf"^{name} = (-?\d+)$", source, re.MULTILINE)
        if match:
            found[name] = int(match.group(1))
    return found


def test_the_control_arm_devices_are_real_devices() -> None:
    # A name that stopped being a device would still parametrize, and the probe would then fail on
    # a missing generated module - a confusing import error in place of "this list is stale".
    assert set(_CONTROL_DEVICES) <= set(DEVICE_NAMES), f"{sorted(set(_CONTROL_DEVICES) - set(DEVICE_NAMES))} is no longer a real device - update the control arm with it"


def test_a_missing_generated_tree_fails_rather_than_skipping(repo_root: Path, tmp_path: Path) -> None:
    # A skip reads as a pass: every placement bound above would report green while measuring nothing.
    this_file = load_script_module(repo_root / "tests_scripts" / "test_digital_twin_boot_contiguity.py", "_boot_contiguity_tests_under_test")
    with pytest.raises(BaseException) as caught:  # BaseException: an escaping skip would skip this test too
        this_file.generated_src.__wrapped__(tmp_path)
    assert isinstance(caught.value, pytest.fail.Exception), f"a missing generated tree must fail, not {type(caught.value).__name__}: {caught.value}"
    assert "scripts/test.sh" in str(caught.value)


def test_a_probe_that_logged_an_allocation_failure_fails_even_when_it_passed() -> None:
    # The degrade-and-pass case the memory gates exist for: src/ logs str(e), so a caught failure
    # reads "memory allocation failed" on a run that still exits 0 and prints its own PASS line.
    planted = "boot ok\n[E] SYSTEM: memory allocation failed, allocating 512 bytes\nRESULT: PASS\n"
    completed = subprocess.CompletedProcess(["probe"], 0, stdout=planted, stderr="")
    with pytest.raises(AssertionError, match="memory allocation failed, allocating 512 bytes"):
        _checked_probe_run("wozi", _ARM_LIVE, completed)


def test_the_probe_runs_under_the_same_interpreter_settings_as_the_suite(repo_root: Path) -> None:
    # This file's header claims it measures what scripts/test.sh measures. A MICROPYPATH that
    # drifted would resolve `import sensortask_<device>` somewhere else, or not at all, and the
    # measurement would silently describe a different build than the one the suite runs.
    text = (repo_root / "scripts" / "test.sh").read_text()
    assert f'MICROPYPATH="{_MICROPYPATH}"' in text, f"scripts/test.sh no longer runs the suite on MICROPYPATH={_MICROPYPATH!r} - re-derive this probe's own bounds against whatever replaced it"
    assert f"-X heapsize={_HEAPSIZE}" in text, f"scripts/test.sh no longer runs the suite at heapsize={_HEAPSIZE} - the bounds proved heap-size independent at 8M and 16M, so confirm that still holds before changing this"


def test_the_twin_probe_and_the_board_script_read_at_the_same_positions(repo_root: Path) -> None:
    # Drift here is silent and invalidates the handover: the board reading is only comparable to the
    # twin's if both wait out the same starter loop by the same margin. Two files by necessity - a
    # device script is pushed to the board standalone and can import nothing from tests_scripts/.
    twin = _int_constants((repo_root / _PROBE).read_text(), _MIRRORED_BOUNDS)
    board = _int_constants((repo_root / _BOARD_SCRIPT).read_text(), _MIRRORED_BOUNDS)
    assert set(twin) == set(_MIRRORED_BOUNDS), f"{_PROBE} no longer declares {sorted(set(_MIRRORED_BOUNDS) - set(twin))} - update this guard with it"
    assert set(board) == set(_MIRRORED_BOUNDS), f"{_BOARD_SCRIPT} no longer declares {sorted(set(_MIRRORED_BOUNDS) - set(board))} - update this guard with it"
    assert twin == board, f"the twin probe and the board script disagree on {[name for name in _MIRRORED_BOUNDS if twin[name] != board[name]]}: {twin} against {board}"
