"""The regression guard for SPECIFICATION.md Part I.4(f.1)'s boot placement: boots every real generated device
under the Unix port and asserts the two one-time boot lists place their survivors low with no collect between
their units, measured through tests_hardware/heap_map.py - the board tier's own parser."""

import ast
import json
import os
import re
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import NamedTuple

import pytest
import tomllib
from _devices import DEVICE_NAMES, devices_with
from _script_loader import load_script_module

# Same import route tests_scripts/test_heap_map_parser.py uses for the same file: the repo has no
# packages by design, so importing it as `tests_hardware.heap_map` would make mypy see one source
# file under two module names (confirmed - host_typecheck.ini's pass fails on exactly that).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tests_hardware"))

# No E402 suppression: ruff exempts a sys.path insert outright, and RUF100 fails an unused one.
from heap_map import HeapMap, delta, parse_labelled

# scripts/test.sh's own MICROPYPATH (the unit layout, scripts/micropypath.toml), heap size and interpreter, so this
# measures what the suite measures. The heap size is deliberately NOT calibrated to a fill fraction: every bound below
# is an absolute offset from the seam, and those proved heap-size independent at 8M and 16M.
_MICROPYPATH = tomllib.loads((Path(__file__).resolve().parent.parent / "scripts" / "micropypath.toml").read_text(encoding="utf-8"))["unit"]
# @tunable l1.unix_heapsize = 16M
_HEAPSIZE = "16M"
_PROBE = "tests/_boot_contiguity_probe.py"
_GENERATED = Path(__file__).resolve().parent.parent / "build" / "generated_src"
_PROBE_TIMEOUT_S = 120

_REQUIRED_MAPS = ("baseline", "batch_00", "after_batch", "after_starter_loop_end")

# Every bound clears the worst reading across every device, with margin, taken with no collect between the units
# (2026-11-10) on the firmware's own blocks (the probe keeps the fakes' call logs empty) on the settrace-free binary.
# Twin units (32 B blocks, x86-64) and twin-only - the board's own tripwire stays the hardware test.

# The batch's median new block must sit at least this far BELOW the seam's top survivor.
_BATCH_MEDIAN_DEPTH_MIN = 300 * 1024  # worst 645,408 (2.10x)

# The batch's own reach and band count: -425 KB or lower and 0 on every device, asserted as tripwires for a module
# allocating high during the batch.

# Both lists together: the highest new block, and the median's depth.
_BOOT_REACH_MAX = 64 * 1024  # worst -235,200 (below the seam)
_BOOT_MEDIAN_DEPTH_MIN = 256 * 1024  # worst 830,304 (3.17x), a tripwire

# How many new blocks may sit more than this far above the seam: zero on every device. The slack is for one future
# large allocation that genuinely cannot fit a low hole, not for a drift in placement.
_HIGH_BAND = 32 * 1024
_HIGH_BAND_BLOCKS_MAX = 32

# The allocation-failure markers every gate shares, from the hardware tier's harness
# (tests_scripts/test_memory_error_gate_agreement.py keeps the gates agreeing).
_MEMORY_ERROR_MARKERS: tuple[str, ...] = tuple(load_script_module(Path(__file__).resolve().parent.parent / "tests_hardware" / "harness.py", "harness_for_contiguity").MEMORY_ERROR_MARKERS)
# The line the probe's always-printing asyncio report opens with for a task that died unawaited.
_TASK_DEATH_MARKER = str(load_script_module(Path(__file__).resolve().parent.parent / "digital_twin" / "unix_port_unretrieved_report.py", "unix_port_unretrieved_report").MARKER)

_RING_LINE = re.compile(r"^RING (\S+) (\S+) (none|0x[0-9a-f]+) (\d+)$", re.MULTILINE)
_POOL_START = re.compile(r"^GC memory layout; from ([0-9a-fA-F]+):", re.MULTILINE)


class _ProbeRun(NamedTuple):
    # One boot of one device: the maps it dumped, each UART bus's receive ring (position -> bus -> (address,
    # length), address None for no ring) and the heap's start.

    maps: dict[str, HeapMap]
    rings: dict[str, dict[str, tuple[int | None, int]]]
    pool_start: int | None


def _parse_rings(stdout: str) -> dict[str, dict[str, tuple[int | None, int]]]:
    found: dict[str, dict[str, tuple[int | None, int]]] = {}
    for label, bus, address, length in _RING_LINE.findall(stdout):
        found.setdefault(label, {})[bus] = (None if address == "none" else int(address, 16), int(length))
    return found


def _checked_probe_run(device: str, completed: subprocess.CompletedProcess[str]) -> _ProbeRun:
    # One finished probe, judged: exit status, its own PASS line, no allocation-failure marker
    # (SPECIFICATION.md Part I.4(e)), no task that died, and every map the bounds read.
    tail = f"{completed.stdout[-3000:]}\n{completed.stderr[-3000:]}"
    assert completed.returncode == 0, f"the probe failed for {device} (exit {completed.returncode}):\n{tail}"
    assert "RESULT: PASS" in completed.stdout, f"the probe never reached its own PASS line for {device}:\n{tail}"
    marked = [line for line in f"{completed.stdout}\n{completed.stderr}".splitlines() if any(marker in line for marker in _MEMORY_ERROR_MARKERS)]
    assert not marked, f"the probe for {device} logged an allocation failure:\n" + "\n".join(marked)
    died = [line for line in f"{completed.stdout}\n{completed.stderr}".splitlines() if _TASK_DEATH_MARKER in line]
    assert not died, f"the probe for {device} reports that a task died during the boot it measured:\n" + "\n".join(died)
    maps = parse_labelled(completed.stdout)
    missing = [label for label in _REQUIRED_MAPS if label not in maps]
    assert not missing, f"no usable map captured for {missing} on {device} - the measurement would be vacuous:\n{tail}"
    pool = _POOL_START.search(completed.stdout)
    return _ProbeRun(maps, _parse_rings(completed.stdout), int(pool.group(1), 16) if pool else None)


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
) -> Callable[[str], _ProbeRun]:
    # Runs tests/_boot_contiguity_probe.py once per device and caches the result: several assertions over one boot
    # rather than one boot each.
    assert generated_src.is_dir()  # the fixture above already failed if not; this keeps the dependency explicit
    cache: dict[str, _ProbeRun] = {}

    def run(device: str) -> _ProbeRun:
        if device in cache:
            return cache[device]
        cfg_dir = tmp_path_factory.mktemp(f"cfg_{device}")
        completed = subprocess.run(
            [str(micropython_bin), "-X", f"heapsize={_HEAPSIZE}", _PROBE, device, f"{cfg_dir}/", "0"],
            cwd=repo_root,
            env=dict(os.environ, MICROPYPATH=_MICROPYPATH, TZ="UTC"),
            capture_output=True,
            text=True,
            timeout=_PROBE_TIMEOUT_S,
            check=False,
        )
        cache[device] = _checked_probe_run(device, completed)
        return cache[device]

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
def test_the_setup_batch_places_its_survivors_low(boot_probe: Callable[[str], _ProbeRun], device: str) -> None:
    # The setup list (SystemService.run_setups()), no collect between its units: since FRAM became synchronous the batch
    # makes too little churn to push the next module's permanent objects above the lowest fitting holes.
    maps = boot_probe(device).maps
    seam, after = maps["batch_00"], maps["after_batch"]
    depth, reach = -_median(seam, after), _reach(seam, after)
    high = _blocks_above(seam, after, _HIGH_BAND)
    assert depth >= _BATCH_MEDIAN_DEPTH_MIN, f"{device}: the setup batch's median new block sits only {depth} B below the seam, under the {_BATCH_MEDIAN_DEPTH_MIN} B bound - something in the batch now churns before its survivors land"
    assert reach <= _BOOT_REACH_MAX, f"{device}: the setup batch's highest new block sits {reach} B above the seam, over the {_BOOT_REACH_MAX} B tripwire - something in the batch now allocates high"
    assert high <= _HIGH_BAND_BLOCKS_MAX, f"{device}: {high} of the batch's new blocks sit more than {_HIGH_BAND} B above the seam, over the {_HIGH_BAND_BLOCKS_MAX} allowed"


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_the_whole_boot_sequence_places_its_survivors_low(boot_probe: Callable[[str], _ProbeRun], device: str) -> None:
    # Both lists together - the batch plus start_tasks()'s starter loop, which archive 7A.3
    # measured as mattering as much as the batch. Read at the loop's own end, never after a settle:
    # the run phase undoes most of the gain within ~2 s and the position stops discriminating (MEASUREMENTS M3.9).
    maps = boot_probe(device).maps
    seam, after = maps["batch_00"], maps["after_starter_loop_end"]
    reach, depth = _reach(seam, after), -_median(seam, after)
    high = _blocks_above(seam, after, _HIGH_BAND)
    assert reach <= _BOOT_REACH_MAX, f"{device}: the whole boot sequence's highest new block sits {reach} B above the seam, over the {_BOOT_REACH_MAX} B bound"
    assert depth >= _BOOT_MEDIAN_DEPTH_MIN, f"{device}: the median new block sits only {depth} B below the seam, under the {_BOOT_MEDIAN_DEPTH_MIN} B bound"
    assert high <= _HIGH_BAND_BLOCKS_MAX, f"{device}: {high} new blocks sit more than {_HIGH_BAND} B above the seam, over the {_HIGH_BAND_BLOCKS_MAX} allowed"


# Every device whose TOML declares a UART link: the ones whose setup allocates receive rings.
_UART_LINK_DEVICES = devices_with("uart_link")


def test_a_real_device_builds_a_uart_link() -> None:
    # The floor of the ring check below, which runs on each of these devices and on no other.
    assert _UART_LINK_DEVICES, "no device declares a uart_link, so no receive ring below is ever placed"


@pytest.mark.parametrize("device", _UART_LINK_DEVICES)
def test_the_uart_receive_rings_land_with_the_boot_survivors(boot_probe: Callable[[str], _ProbeRun], device: str) -> None:
    # Each link allocates its DMA ring in its own setup(), a unit of the one-time batch, so it lands low with the
    # other survivors (SPECIFICATION.md I.4(f.1)), and its address never moves: the same ring after the starter loop,
    # nothing reallocated once the batch ended.
    run = boot_probe(device)
    after_batch, after_loop = run.rings.get("after_batch", {}), run.rings.get("after_starter_loop_end", {})
    plan = json.loads((_GENERATED / f"sensortask_{device}_wiring_plan.json").read_text(encoding="utf-8"))
    assert "uart_link" in plan["instances"] and plan["uart"], f"{device} declares a uart_link, yet its generated wiring plan builds no UART bus"
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
_MIRRORED_BOUNDS = ("_STARTER_LOOP_TIMEOUT_MS", "_TIMERS_TIMEOUT_S")


def _int_constants(source: str, names: tuple[str, ...]) -> dict[str, int]:
    # Each named module-level constant's value, an integer constant expression (`192 * 1024`) evaluated from its AST.
    found: dict[str, int] = {}
    for node in ast.parse(source).body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) and node.targets[0].id in names:
            found[node.targets[0].id] = _arithmetic(node.value)
    return found


def test_a_missing_generated_tree_fails_rather_than_skipping(repo_root: Path, tmp_path: Path) -> None:
    # A skip reads as a pass: every placement bound above would report green while measuring nothing.
    this_file = load_script_module(repo_root / "tests_scripts" / "test_digital_twin_boot_contiguity.py", "_boot_contiguity_tests_under_test")
    try:
        this_file.generated_src.__wrapped__(tmp_path)
    except BaseException as exc:  # BaseException: an escaping skip would skip this test too
        caught = exc
    else:
        pytest.fail("a missing generated tree raised nothing")
    assert isinstance(caught, pytest.fail.Exception), f"a missing generated tree must fail, not {type(caught).__name__}: {caught}"
    assert "scripts/test.sh" in str(caught)


def test_a_probe_that_logged_an_allocation_failure_fails_even_when_it_passed() -> None:
    # The degrade-and-pass case the memory gates exist for: src/ logs str(e), so a caught failure
    # reads "memory allocation failed" on a run that still exits 0 and prints its own PASS line.
    planted = "boot ok\n[E] SYSTEM: memory allocation failed, allocating 512 bytes\nRESULT: PASS\n"
    completed = subprocess.CompletedProcess(["probe"], 0, stdout=planted, stderr="")
    with pytest.raises(AssertionError, match="memory allocation failed, allocating 512 bytes"):
        _checked_probe_run("fixture_device", completed)


def test_a_probe_in_which_a_task_died_fails_even_when_it_passed() -> None:
    # No supervisor runs in the probe, so nothing restarts or records a dead task: the PC report's line is the
    # only trace, and a boot that lost a task places a different set of survivors than the one measured.
    planted = "boot ok\nUNRETRIEVED TASK EXCEPTION: Task exception wasn't retrieved\nValueError: planted\nRESULT: PASS\n"
    completed = subprocess.CompletedProcess(["probe"], 0, stdout=planted, stderr="")
    with pytest.raises(AssertionError, match="a task died during the boot it measured"):
        _checked_probe_run("fixture_device", completed)


def test_the_probe_runs_under_the_same_interpreter_settings_as_the_suite(repo_root: Path) -> None:
    # This file's header claims it measures what scripts/test.sh measures. A MICROPYPATH that
    # drifted would resolve `import sensortask_<device>` somewhere else, or not at all, and the
    # measurement would silently describe a different build than the one the suite runs.
    text = (repo_root / "scripts" / "test.sh").read_text(encoding="utf-8")
    assert 'unit_micropypath="$(micropypath unit)"' in text and '"MICROPYPATH=$unit_micropypath"' in text, "scripts/test.sh no longer runs the suite on the unit layout of scripts/micropypath.toml - re-derive this probe's own bounds against whatever replaced it"
    assert f"-X heapsize={_HEAPSIZE}" in text, f"scripts/test.sh no longer runs the suite at heapsize={_HEAPSIZE} - the bounds proved heap-size independent at 8M and 16M, so confirm that still holds before changing this"


def test_the_twin_probe_and_the_board_script_read_at_the_same_positions(repo_root: Path) -> None:
    # Drift here is silent and invalidates the handover: the board reading is only comparable to the
    # twin's if both bound the same starter loop and timer start alike. Two files by necessity - a
    # device script is pushed to the board standalone and can import nothing from tests_scripts/.
    twin = _int_constants((repo_root / _PROBE).read_text(encoding="utf-8"), _MIRRORED_BOUNDS)
    board = _int_constants((repo_root / _BOARD_SCRIPT).read_text(encoding="utf-8"), _MIRRORED_BOUNDS)
    assert set(twin) == set(_MIRRORED_BOUNDS), f"{_PROBE} no longer declares {sorted(set(_MIRRORED_BOUNDS) - set(twin))} - update this guard with it"
    assert set(board) == set(_MIRRORED_BOUNDS), f"{_BOARD_SCRIPT} no longer declares {sorted(set(_MIRRORED_BOUNDS) - set(board))} - update this guard with it"
    assert twin == board, f"the twin probe and the board script disagree on {[name for name in _MIRRORED_BOUNDS if twin[name] != board[name]]}: {twin} against {board}"


_PROBE_CONSTANTS = ("_PROBE_MIN", "_PROBE_MAX", "_PROBE_RETRIES")
_SHARED_PROBE = "_shared/heap_probe.py"


def _arithmetic(node: ast.expr) -> int:
    # An integer constant expression evaluated from its AST; any other expression fails the read.
    if isinstance(node, ast.Constant) and isinstance(node.value, int):
        return node.value
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return -_arithmetic(node.operand)
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Mult, ast.Add, ast.Sub, ast.LShift)):
        left, right = _arithmetic(node.left), _arithmetic(node.right)
        return {ast.Mult: left * right, ast.Add: left + right, ast.Sub: left - right, ast.LShift: left << right}[type(node.op)]
    raise AssertionError(f"not an integer constant expression: {ast.unparse(node)}")


def _probe_constant_findings(scripts: Path, twin_probe: Path) -> "list[str]":
    # The heap probe's search constants live once, in the shared include; no script keeps a copy, and a twin probe
    # stating one states the same value (today it reads mem_info maps and searches nothing).
    shared = _int_constants((scripts / _SHARED_PROBE).read_text(encoding="utf-8"), _PROBE_CONSTANTS)
    found = [] if set(shared) == set(_PROBE_CONSTANTS) else [f"{_SHARED_PROBE} states {sorted(shared)}, not all of {_PROBE_CONSTANTS}"]
    found += [f"{path.name} keeps its own {sorted(kept)}" for path in sorted(scripts.glob("*.py")) if (kept := _int_constants(path.read_text(encoding="utf-8"), _PROBE_CONSTANTS))]
    twin = _int_constants(twin_probe.read_text(encoding="utf-8"), _PROBE_CONSTANTS)
    found += [f"the twin probe's {name} = {value}, the shared include's {shared.get(name)}" for name, value in twin.items() if shared.get(name) != value]
    return found


def test_the_heap_probe_constants_live_once_in_the_shared_include(repo_root: Path) -> None:
    assert _probe_constant_findings(repo_root / "tests_hardware" / "device_scripts", repo_root / _PROBE) == []


def test_no_device_script_keeps_a_copy_of_this_files_high_band(repo_root: Path) -> None:
    # Reported, not failed: the high band is a twin-only bound, and a board script stating one would drift unseen.
    names = ("_HIGH_BAND", "_HIGH_BAND_BLOCKS_MAX")
    copies = {p.name: kept for p in sorted((repo_root / "tests_hardware" / "device_scripts").glob("*.py")) if (kept := _int_constants(p.read_text(encoding="utf-8"), names))}
    print(f"device-script copies of {names}: {copies or 'none'}")


def test_the_probe_constant_check_bites(tmp_path: Path) -> None:
    scripts = tmp_path / "device_scripts"
    (scripts / "_shared").mkdir(parents=True)
    (scripts / _SHARED_PROBE).write_text("_PROBE_MIN = 64\n_PROBE_MAX = 192 * 1024\n_PROBE_RETRIES = 3\n", encoding="utf-8")
    (scripts / "copy.py").write_text("_PROBE_MIN = 64\n", encoding="utf-8")
    twin = tmp_path / "twin_probe.py"
    twin.write_text("_PROBE_RETRIES = 4\n", encoding="utf-8")
    assert _probe_constant_findings(scripts, twin) == ["copy.py keeps its own ['_PROBE_MIN']", "the twin probe's _PROBE_RETRIES = 4, the shared include's 3"]
