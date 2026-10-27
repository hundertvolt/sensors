"""Flash-tier automated tests: real GC-heap headroom once the whole object graph exists, the routine no-yield stretches,
one flash write's span, the loop lag and the C-stack peak on the real 133 MHz core, and single-core timing headroom
under normal full task load (SPECIFICATION.md Parts I and F.3). The real-HTTP-soak variants live in bench/."""

import threading
import time
from typing import TYPE_CHECKING, ParamSpec

import heap_map
import http_client
import pytest
from error_log_helpers import assert_no_new_task_raised, read_live_system_log
from harness import DEVICE_SCRIPTS_DIR, MEMORY_ERROR_MARKERS, SRC_DIR, boot_lines, configured_max_connections, crash_lines, device_toml, get_routes, parse_facts, wait_for_boot, wait_until
from heap_bounds import WORST_CASE_ALLOCATION
from soak_durations import SOAK_DURATION_SECONDS

from buildgen.model import load_device
from buildgen.validate import smallest_hard_consumer

if TYPE_CHECKING:
    from collections.abc import Callable

    from harness import Board

COVERS_TWIN_SCENARIOS: tuple[str, ...] = ("construction", "loop_lag")
_P = ParamSpec("_P")

# @tunable l3.memory_stress_headroom_script_timeout_s = 120.0
_HEADROOM_SCRIPT_TIMEOUT_S = 120.0
# @tunable l3.memory_stress_probe_map_tolerance_blocks = 2
_PROBE_MAP_TOLERANCE_BLOCKS = 2
# @tunable l3.memory_stress_presence_timeout_s = 30.0
_PRESENCE_TIMEOUT_S = 30.0
# @tunable l3.memory_stress_boot_timeout_s = 30.0
_BOOT_TIMEOUT_S = 30.0  # the boot line after the soak's first hard reset
# Past the boot's one-time setup lines, so a DebugLevel at or above 3 cannot print them into the window as a reboot.
# @tunable l3.memory_stress_boot_settle_s = 30.0
_BOOT_SETTLE_S = 30.0
# @tunable l3.memory_stress_stretch_script_timeout_s = 60.0
_STRETCH_SCRIPT_TIMEOUT_S = 60.0
# @tunable l3.memory_stress_flash_gap_script_timeout_s = 30.0
_FLASH_GAP_SCRIPT_TIMEOUT_S = 30.0
# The lag script's own 30 s window plus the shipped boot and the scratch cleanup.
# @tunable l3.memory_stress_loop_lag_script_timeout_s = 90.0
_LOOP_LAG_SCRIPT_TIMEOUT_S = 90.0
# The C-stack script's own 10 s window plus the build, its setup batch and the timer stagger.
# @tunable l3.memory_stress_c_stack_script_timeout_s = 60.0
_C_STACK_SCRIPT_TIMEOUT_S = 60.0
# The twin run's server: the script's scratch-config main() binds it inside the run's own network namespace.
_TWIN_SERVER = ("127.0.0.1", 8080)


def _lag_load(stop: threading.Event, served: "dict[str, int]", failures: "list[str]") -> None:
    # Once the twin script's server answers, a ceiling of readers cycles every JSON GET route from its own offset until
    # `stop`, each 200 counted per route: the twin scenario's load (scripts/_digital_twin_scenarios.py, _lag_load()).
    host, port = _TWIN_SERVER
    routes = list(served)
    lock = threading.Lock()

    def status(path: str) -> int:
        try:
            return http_client.fetch(host, port, "GET", path).status_code
        except (OSError, http_client.HTTP_ERROR):  # a refusal at the ceiling is no answer, as the twin scenario counts it
            return 0

    def reader(index: int) -> None:
        while not stop.is_set():
            route = routes[index % len(routes)]
            index += 1
            if status(route) == 200:
                with lock:
                    served[route] += 1

    try:
        wait_until(lambda: stop.is_set() or status("/status") == 200, _LOOP_LAG_SCRIPT_TIMEOUT_S, description="the loop-lag script's own server answering")
    except TimeoutError as e:  # recorded for the test's verdict, never a dead thread's warning
        failures.append(str(e))
        return
    threads = [threading.Thread(target=_recording(failures, reader), args=(i,), name=f"lag-reader-{i}") for i in range(configured_max_connections())]
    try:
        for thread in threads:
            thread.start()
    finally:  # the readers end at `stop`, which the test sets once the script has ended
        for thread in threads:
            if thread.ident is not None:  # started
                thread.join(_LOOP_LAG_SCRIPT_TIMEOUT_S)
    failures.extend(f"{thread.name} still running after the load" for thread in threads if thread.is_alive())


def _recording(failures: "list[str]", target: "Callable[_P, None]") -> "Callable[_P, None]":
    # The thread target with its death recorded for the test's verdict, naming the exception: never only pytest's warning.
    def run(*args: _P.args, **kwargs: _P.kwargs) -> None:
        try:
            target(*args, **kwargs)
        except Exception as e:  # any death is recorded: the test fails on it
            failures.append(f"{threading.current_thread().name} died: {type(e).__name__}: {e}")

    return run


def _run(board: "Board", script: str, timeout_s: float) -> "tuple[str, dict[str, object]]":
    # A measurement over a heap that failed an allocation and carried on is no figure: every marker spelling fails it.
    output = board.run_isolated(DEVICE_SCRIPTS_DIR / script, timeout_s=timeout_s)
    failed = [line for line in output.splitlines() if any(marker in line for marker in MEMORY_ERROR_MARKERS)]
    assert not failed, f"{script} reported an allocation failure:\n" + "\n".join(failed)
    return output, parse_facts(output)


def test_real_gc_heap_headroom_survives_a_full_system_build(board: "Board", result_note: "Callable[[str], None]") -> None:
    # The one memory figure no fake can produce: real 264 KB SRAM minus the firmware's own static footprint, after the
    # bench build's object graph exists. Survivor volume and contiguity are judged on the facts, placement on the map.
    output = board.run_isolated(DEVICE_SCRIPTS_DIR / "heap_headroom_after_full_system_build.py", timeout_s=_HEADROOM_SCRIPT_TIMEOUT_S, worst_case_allocation=WORST_CASE_ALLOCATION)
    facts = parse_facts(output)
    assert not crash_lines(output.splitlines()), "the headroom build crashed or failed an allocation:\n" + "\n".join(crash_lines(output.splitlines()))
    stages, used, max_used = facts.get("gc_threshold"), facts.get("used"), facts.get("max_used")
    largest, min_largest = facts.get("largest_block"), facts.get("min_largest_block")
    heaps = {key: value for key, value in facts.items() if key.startswith("heap_")}
    result_note(f"heap headroom at gc.threshold {stages}: used {used} B (max {max_used}), largest block {largest} B (min {min_largest}); {heaps}")
    assert isinstance(used, int) and isinstance(max_used, int) and used <= max_used, f"at gc.threshold {stages}: the built object graph holds {used} B, over {max_used} B; facts {facts}"
    assert isinstance(largest, int) and isinstance(min_largest, int) and largest >= min_largest, f"at gc.threshold {stages}: {largest} B contiguous, under {min_largest} B (the worst allocation twice); facts {facts}"
    maps = heap_map.parse_labelled(output)
    assert "after_build_system" in maps, f"no mem_info(1) block map in the device output - the layout cannot be checked:\n{output}"
    layout = maps["after_build_system"]
    result_note(f"MAP after_build_system: {layout.summary()}")
    # The probe allocates and the map does not, so they fail in different ways: a disagreement means one is wrong, and
    # the probe understating by a power-of-two fraction of 192 KB is the known pinning artefact.
    assert abs(layout.largest_free_run - largest) <= layout.block_bytes * _PROBE_MAP_TOLERANCE_BLOCKS, f"the allocating probe says {largest} B and the block map says {layout.largest_free_run} B for one run:\n{output}"
    # Long-lived objects must not colonise the top of the heap (owner, 2026-09-19): asserted twice, because the two fail
    # for different reasons - the boot's own placement, and whatever already sat up there.
    assert "baseline" in maps, f"no baseline block map in the device output - the placement delta cannot be computed:\n{output}"
    placed = heap_map.delta(maps["baseline"], layout)
    result_note(f"DELTA boot placement: {placed.summary()}")
    assert placed.new_above(WORST_CASE_ALLOCATION) == 0, f"the boot placed {placed.new_above(WORST_CASE_ALLOCATION)} long-lived object(s) inside the top {WORST_CASE_ALLOCATION} B of the heap: {placed.summary()}"
    assert layout.free_above_top_survivor >= WORST_CASE_ALLOCATION, f"only {layout.free_above_top_survivor} B free above the highest allocated block, against the {WORST_CASE_ALLOCATION} B worst reachable allocation; layout {layout.summary()}"


def test_routine_no_yield_stretches_stay_under_the_gc_term(board: "Board", result_note: "Callable[[str], None]") -> None:
    _output, facts = _run(board, "loop_stretch_timing.py", _STRETCH_SCRIPT_TIMEOUT_S)
    bound = facts.get("routine_stall_us")
    stretches = {key: facts.get(key) for key in ("gc_max_us", "voc_max_us", "crc_gap_max_us")}
    result_note(f"no-yield stretches at gc.threshold {facts.get('gc_threshold')}: {stretches}, CRC total {facts.get('crc_total_us')} us (bound {bound} us)")
    assert isinstance(bound, int), f"no routine_stall_us fact: {facts}"
    over = {key: value for key, value in stretches.items() if not isinstance(value, int) or value > bound}
    assert not over, f"routine no-yield stretches over the {bound} us GC term, or missing: {over}; facts {facts}"


@pytest.mark.persistence_write
def test_flash_write_loop_gap_is_recorded(board: "Board", result_note: "Callable[[str], None]") -> None:
    # The test owns one scratch flash write (CLAUDE.md wear rule); the figure feeds F.3's flash stall row, so it is
    # recorded here and judged against its consumers there.
    _output, facts = _run(board, "flash_write_loop_gap.py", _FLASH_GAP_SCRIPT_TIMEOUT_S)
    longest, total = facts.get("flash_call_max_us"), facts.get("flash_total_us")
    result_note(f"one 1 KiB scratch flash write: longest call {longest} us, all four {total} us ({facts.get('flash_calls_us')})")
    assert isinstance(longest, int) and isinstance(total, int), f"the flash write's spans were not reported: {facts}"


def test_loop_lag_under_combined_load_stays_under_the_uart_reply_budget(board: "Board", request: pytest.FixtureRequest, result_note: "Callable[[str], None]") -> None:
    # The twin's run, under a ceiling of GETs on every route as the twin scenario loads it. Silicon's is the bench tier's
    # test: only the bench network reaches the script's server on the board, and its main() writes production FRAM chunks.
    if not request.config.getoption("--twin"):
        pytest.skip("silicon runs this instrument in bench/test_memory_stress_bench.py: only the bench network reaches the script's server on the board")
    served = dict.fromkeys(get_routes(), 0)
    failures: list[str] = []
    stop = threading.Event()
    load = threading.Thread(target=_recording(failures, _lag_load), args=(stop, served, failures), name="lag-load")
    try:
        load.start()
        _output, facts = _run(board, "loop_lag_under_combined_load.py", _LOOP_LAG_SCRIPT_TIMEOUT_S)
    finally:
        stop.set()
        load.join(2 * _LOOP_LAG_SCRIPT_TIMEOUT_S)
    bound_us = smallest_hard_consumer(load_device(device_toml()), SRC_DIR).ms * 1000  # the build rule's and the twin scenario's one source
    lag_max, lag_p99, samples = facts.get("lag_max_us"), facts.get("lag_p99_us"), facts.get("samples")
    result_note(f"loop lag under combined load: max {lag_max} us, p99 {lag_p99} us over {facts.get('samples')} samples (bound {bound_us} us); answers per route {served}")
    assert not load.is_alive() and not failures, f"the HTTP load did not end cleanly: {failures}"
    assert served and all(served.values()), f"GET routes never served under the load: {sorted(route for route, count in served.items() if not count)} of {len(served)} routes"
    assert facts.get("main_running") is True, f"the shipped main() ended inside the window: {facts}"
    writes = facts.get("fram_writes")
    assert facts.get("fram_write_failures") == 0 and isinstance(writes, int) and writes > 0, f"the FRAM load did not run cleanly: {facts}"
    assert isinstance(samples, int) and samples > 0, f"the lag probe recorded no sample, so the {bound_us} us bound was checked against nothing: {facts}"
    assert isinstance(lag_max, int) and lag_max <= bound_us, f"the loop lagged {lag_max} us, past the {bound_us} us smallest hard consumer: {facts}"


def test_c_stack_peak_is_within_half_the_limit(board: "Board", result_note: "Callable[[str], None]") -> None:
    _output, facts = _run(board, "c_stack_budget.py", _C_STACK_SCRIPT_TIMEOUT_S)
    limit = facts.get("c_stack_limit")
    result_note(f"C stack: chain {facts.get('chain')}, peak {facts.get('c_stack_peak', facts.get('twin_c_stack_peak'))} B of {limit} B; leaves {facts.get('leaf_peaks')}")
    assert isinstance(limit, int) and facts.get("chain") is not None, f"no leaf of the running system recorded a stack reading: {facts}"
    if "twin_c_stack_peak" in facts:
        return  # the Unix port's 64-bit frames are not the board's: reported, never compared
    peak = facts.get("c_stack_peak")
    assert isinstance(peak, int) and peak <= limit // 2, f"the C-stack peak {peak} B is over half the {limit} B limit (chain {facts.get('chain')}): {facts}"


@pytest.mark.soak_duration
def test_single_core_timing_headroom_holds_under_normal_full_task_load(board: "Board", request: pytest.FixtureRequest) -> None:
    duration = request.config.getoption("--soak-duration")
    if duration is None:
        pytest.skip("passive soak over one named duration - run via scripts/run_bench_soak_tests.sh --duration {short,mid,long}")
    duration_s = SOAK_DURATION_SECONDS[duration]
    # SYSTEM's task-end log is read before and after the window, each read interrupting the firmware, so each is
    # followed by a hard reset: at DebugLevel 0 a task that died raising prints nothing (SPECIFICATION.md I.4(e)).
    # The first read waits for a fresh boot's line, so it never lands mid-boot after the session's own reset.
    board.hard_reset()
    wait_until(board.is_device_present, timeout_s=_PRESENCE_TIMEOUT_S, description="board present again after hard_reset()")
    wait_for_boot(board, _BOOT_TIMEOUT_S)
    before = read_live_system_log(board)
    board.hard_reset()
    wait_until(board.is_device_present, timeout_s=_PRESENCE_TIMEOUT_S, description="board present again after hard_reset()")
    time.sleep(_BOOT_SETTLE_S)
    # Passive observation only (tail_log(), never exec()/run_isolated(): those stop main.py).
    lines = board.tail_log(duration_s=duration_s)
    after = read_live_system_log(board)
    board.hard_reset()
    wait_until(board.is_device_present, timeout_s=_PRESENCE_TIMEOUT_S, description="board present again after hard_reset()")
    # A boot line mid-window is an unexpected reboot; a crash line is a raised exception or an allocation failure that
    # was caught and logged - the case the memory rule is named for (the board never prints the class name for it).
    assert not boot_lines(lines), f"observed what looks like an unexpected mid-soak reboot (watchdog starvation?): {boot_lines(lines)}\nfull log:\n" + "\n".join(lines)
    assert not crash_lines(lines), "observed an unexpected traceback or allocation failure during the soak window:\n" + "\n".join(crash_lines(lines))
    assert_no_new_task_raised(before, after, "the soak window")
