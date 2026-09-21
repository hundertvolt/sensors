"""The regression guard for SPECIFICATION.md Part I.4(f.1)'s boot-confined placement reset: boots
every real generated device under the Unix port and asserts the two one-time boot lists still place
their survivors low, measured through tests_hardware/heap_map.py - the board tier's own parser."""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING, NamedTuple

import pytest
from _devices import DEVICE_NAMES

# Same import route tests_scripts/test_heap_map_parser.py uses for the same file: the repo has no
# packages by design, so importing it as `tests_hardware.heap_map` would make mypy see one source
# file under two module names (confirmed - host_typecheck.ini's pass fails on exactly that).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tests_hardware"))

# No E402 suppression: ruff exempts a sys.path insert outright, and RUF100 fails an unused one.
from heap_map import HeapMap, delta, parse_labelled

if TYPE_CHECKING:
    from collections.abc import Callable

# scripts/test.sh's own MICROPYPATH and heap size, so this measures what the suite measures. The
# heap size is deliberately NOT calibrated to a fill fraction: every bound below is an absolute
# offset above the seam, and those were measured byte-identical at 8M and 16M.
_MICROPYPATH = "build/generated_src:src:tests:frozen_modules:.frozen"
_HEAPSIZE = "16M"
_PROBE = "tests/_boot_contiguity_probe.py"
_PROBE_TIMEOUT_S = 120

_ARM_LIVE = "collects"
_ARM_SUPPRESSED = "suppressed"

# Which devices get the suppressed control arm too: wozi is the exemplary variant the whole
# promotion is validated against, dev is the only board ever flashed. Running it for all six would
# double the subprocess count to prove the same thing six times.
_CONTROL_DEVICES = ("wozi", "dev")

_REQUIRED_MAPS = ("baseline", "batch_00", "after_batch", "after_starter_loop_end")

# Every bound is the worst reading measured across all six devices with the collects live, times a
# margin, and each sits at least 2.6x below the best reading the suppressed arm produced. Twin units
# (32 B blocks, x86-64) and twin-only - the board's own tripwire stays the hardware test.
_BATCH_REACH_MAX = 640 * 1024  # worst live 278,688 (2.35x); best suppressed 2,103,008 (3.21x above)
_BATCH_MEDIAN_MAX = 192 * 1024  # worst live 45,056 (4.36x); best suppressed 1,174,880 (5.98x above)
_BOOT_REACH_MAX = 1280 * 1024  # worst live 633,344 (2.07x); best suppressed 3,530,208 (2.69x above)
_BOOT_MEDIAN_MAX = 192 * 1024  # worst live -55,744, below the seam entirely; suppressed 1,213,632

# How many newly allocated blocks may sit more than this far above the seam. Measured zero on every
# device with the collects live and 1,110+ without, so the slack is for one future large allocation
# that genuinely cannot fit a low hole, not for a drift in placement.
_HIGH_BAND = 512 * 1024
_HIGH_BAND_BLOCKS_MAX = 256

# Retention must be arm-independent: the collects change WHERE the next survivor is born, never how
# much survives (MEASUREMENTS 7A.1's finding, which reproduces here at 0.05%). 1% is 19x that.
_RETENTION_TOLERANCE = 0.01

_COUNTER_LINE = re.compile(r"^(?:LISTS|COUNTS) (.*)$", re.MULTILINE)


class _ProbeRun(NamedTuple):
    """One boot of one device on one arm: the maps it dumped and the counters it printed."""

    maps: dict[str, HeapMap]
    counters: dict[str, int]


def _parse_counters(stdout: str) -> dict[str, int]:
    found: dict[str, int] = {}
    for match in _COUNTER_LINE.finditer(stdout):
        for field in match.group(1).split():
            name, _, value = field.partition("=")
            found[name] = int(value)
    return found


@pytest.fixture(scope="session")
def generated_src(repo_root: Path) -> Path:
    # The probe imports `sensortask_<device>` and reads its wiring plan from here; scripts/test.sh
    # generates both before any tier runs. Skipped rather than failed when absent, the same way
    # conftest.py's own micropython_bin fixture treats an unbuilt interpreter.
    path = repo_root / "build" / "generated_src"
    if not path.is_dir():
        pytest.skip(f"no generated device modules at {path} - scripts/test.sh generates them before the suites run")
    return path


@pytest.fixture(scope="session")
def boot_probe(
    repo_root: Path,
    micropython_bin: Path,
    generated_src: Path,
    tmp_path_factory: pytest.TempPathFactory,
) -> Callable[[str, str], _ProbeRun]:
    """Runs tests/_boot_contiguity_probe.py once per (device, arm) and caches the result: several
    assertions over one boot rather than one boot each."""
    assert generated_src.is_dir()  # the skip above already ran; this keeps the dependency explicit
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
        tail = f"{completed.stdout[-3000:]}\n{completed.stderr[-3000:]}"
        assert completed.returncode == 0, f"the probe failed for {device}/{arm} (exit {completed.returncode}):\n{tail}"
        assert "RESULT: PASS" in completed.stdout, f"the probe never reached its own PASS line for {device}/{arm}:\n{tail}"
        maps = parse_labelled(completed.stdout)
        missing = [label for label in _REQUIRED_MAPS if label not in maps]
        assert not missing, f"no usable map captured for {missing} on {device}/{arm} - the measurement would be vacuous:\n{tail}"
        cache[key] = _ProbeRun(maps, _parse_counters(completed.stdout))
        return cache[key]

    return run


def _offsets_above_seam(before: HeapMap, after: HeapMap) -> list[int]:
    """Every block newly allocated between the two maps, as a signed byte offset from the top of
    what `before` already had allocated. Negative means it went into a hole further down."""
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
    reach, median = _reach(seam, after), _median(seam, after)
    high = _blocks_above(seam, after, _HIGH_BAND)
    assert reach <= _BATCH_REACH_MAX, f"{device}: the setup batch's highest new block sits {reach} B above the seam, over the {_BATCH_REACH_MAX} B bound - a collect is missing, or no longer resets placement"
    assert median <= _BATCH_MEDIAN_MAX, f"{device}: the median new block sits {median} B above the seam, over the {_BATCH_MEDIAN_MAX} B bound"
    assert high <= _HIGH_BAND_BLOCKS_MAX, f"{device}: {high} new blocks sit more than {_HIGH_BAND} B above the seam, over the {_HIGH_BAND_BLOCKS_MAX} allowed"


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_the_whole_boot_sequence_places_its_survivors_low(boot_probe: Callable[[str, str], _ProbeRun], device: str) -> None:
    # Both lists together - the batch plus start_and_check_tasks()'s starter loop, which 7A.3
    # measured as mattering as much as the batch. Read at the loop's own end, never after a settle:
    # the run phase undoes most of the gain within ~2 s and the position stops discriminating (7F.9).
    maps = boot_probe(device, _ARM_LIVE).maps
    seam, after = maps["batch_00"], maps["after_starter_loop_end"]
    reach, median = _reach(seam, after), _median(seam, after)
    assert reach <= _BOOT_REACH_MAX, f"{device}: the whole boot sequence's highest new block sits {reach} B above the seam, over the {_BOOT_REACH_MAX} B bound"
    assert median <= _BOOT_MEDIAN_MAX, f"{device}: the median new block sits {median} B above the seam, over the {_BOOT_MEDIAN_MAX} B bound"


@pytest.mark.parametrize("device", _CONTROL_DEVICES)
def test_suppressing_the_emitted_collects_breaks_both_bounds(boot_probe: Callable[[str, str], _ProbeRun], device: str) -> None:
    # The control arm, and the reason the bounds above mean anything: the probe's own `gc` stand-in
    # stops forwarding to the real collect, which is what deleting the emitted lines would do.
    # A bound the broken configuration also satisfies is not a guard.
    maps = boot_probe(device, _ARM_SUPPRESSED).maps
    seam = maps["batch_00"]
    batch_reach = _reach(seam, maps["after_batch"])
    boot_reach = _reach(seam, maps["after_starter_loop_end"])
    assert batch_reach > _BATCH_REACH_MAX, f"{device}: with every emitted collect suppressed the batch still stayed inside the {_BATCH_REACH_MAX} B bound (reach {batch_reach} B) - the bound no longer detects the defect it exists for"
    assert boot_reach > _BOOT_REACH_MAX, f"{device}: with every collect suppressed the whole boot sequence still stayed inside the {_BOOT_REACH_MAX} B bound (reach {boot_reach} B)"


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
