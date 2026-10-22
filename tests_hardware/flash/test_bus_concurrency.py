"""Flash-tier tests: real-hardware confirmation of SPECIFICATION.md Part C.8's I2C concurrency and locking model, the
SGP40 general-call regression, same-device read/write concurrency per chip, the participant and bus recovery rungs,
the live-topology sweep and the FRAM fault scripts. Each script reports facts; each test here gives the verdict."""

import errno
from typing import Protocol

import plausibility_bounds
import pytest
from error_log_helpers import code, read_live_system_log
from harness import DEVICE_SCRIPTS_DIR, SRC_DIR, Board, parse_facts, save_fram_raw, wait_for_boot, wait_until

from buildgen.validate import module_int_const


class _ResultNote(Protocol):
    # The root conftest's result_note fixture.
    def __call__(self, text: str, *, recovery: bool = False) -> None: ...


COVERS_TWIN_SCENARIOS: tuple[str, ...] = ("bus_hazard_concurrency", "bmp3xx", "fram")

# @tunable l3.bus_concurrency_long_script_timeout_s = 120.0
_LONG_SCRIPT_TIMEOUT_S = 120.0
# @tunable l3.bus_concurrency_script_timeout_s = 90.0
_SCRIPT_TIMEOUT_S = 90.0
# @tunable l3.bus_concurrency_short_script_timeout_s = 60.0
_SHORT_SCRIPT_TIMEOUT_S = 60.0
# @tunable l3.bus_concurrency_reset_script_timeout_s = 30.0
_RESET_SCRIPT_TIMEOUT_S = 30.0
# @tunable l3.bus_concurrency_reachable_timeout_s = 30.0
_REACHABLE_TIMEOUT_S = 30.0
# @tunable l3.bus_concurrency_reachable_poll_s = 1.0
_REACHABLE_POLL_S = 1.0
# The production boot after a system command's reset, before the raw dump reads the FRAM it left.
# @tunable l3.bus_concurrency_command_boot_timeout_s = 60.0
_COMMAND_BOOT_TIMEOUT_S = 60.0

_REC_SDA_LOW = module_int_const(SRC_DIR, "asy_i2c_driver.py", "_REC_SDA_LOW")
_REC_SDA_STUCK = module_int_const(SRC_DIR, "asy_i2c_driver.py", "_REC_SDA_STUCK")
_ERR_FRAM_CHIP_LOST = module_int_const(SRC_DIR, "asy_fram_driver.py", "_ERR_FRAM_CHIP_LOST")
_RR_REBOOT = module_int_const(SRC_DIR, "asy_system_service.py", "_RR_REBOOT")
_RR_FRAM_ERASED = module_int_const(SRC_DIR, "asy_system_service.py", "_RR_FRAM_ERASED")
_TEST_BAND = frozenset(code("E", name) for name in ("TEST_SEED_A", "TEST_SEED_B", "TEST_SEED_C"))  # the command scripts' writes
# The command scripts' scratch config directory: their reset ends them before their own cleanup.
_REMOVE_COMMAND_SCRATCH = "import os\nif 'hwtest-scratch' in os.listdir():\n    for n in os.listdir('hwtest-scratch/'):\n        os.remove('hwtest-scratch/' + n)\n    os.rmdir('hwtest-scratch/')\nprint('SCRATCH_REMOVED')\n"


def _after_boot_band(board: Board, request: pytest.FixtureRequest, result_note: _ResultNote, reason: str) -> "list[int] | None":
    # After the production boot: the test-band codes in SYSTEM's restored ring, oldest first, then the raw dump read
    # clean. None on the twin, which boots no production image after a reset.
    if request.config.getoption("--twin"):
        result_note("twin run: no production boot follows the reset - the after-boot half is silicon's")
        return None
    wait_for_boot(board, _COMMAND_BOOT_TIMEOUT_S)
    history = read_live_system_log(board)["SYSTEM"]["history"]
    band = [int(str(h["num"])) for h in history if h.get("type") == "E" and h.get("num") in _TEST_BAND]
    after = save_fram_raw(board, f"{reason}-after")
    assert after.facts["read_failed_at"] is None, f"the raw dump after the boot failed at {after.facts['read_failed_at']}"
    return band


def _count(facts: "dict[str, object]", key: str) -> int:
    value = facts.get(key)
    assert isinstance(value, int), f"fact {key} is no count: {value!r} in {facts}"
    return value


def _no_errors(facts: "dict[str, object]", what: str) -> None:
    record = facts.get("errors")
    assert isinstance(record, dict), f"{what}: no errors fact: {facts}"
    assert record["total"] == 0, f"{what}: {record['total']} failure(s), first: {record['first']}"


def _remove_command_scratch(board: Board) -> None:
    # The scratch directory a command script's reset left, then the firmware restarted from the parked REPL.
    output = board.exec(_REMOVE_COMMAND_SCRATCH)
    assert "SCRATCH_REMOVED" in output, f"removing the command scripts' scratch directory failed:\n{output}"
    board.hard_reset()
    wait_until(board.is_device_present, timeout_s=_REACHABLE_TIMEOUT_S, poll_interval_s=_REACHABLE_POLL_S, description="board back on USB after the scratch cleanup")


def _run(board: Board, script: str, timeout_s: float, *, bounds: bool = False) -> "dict[str, object]":
    # The script's facts; with bounds=True it receives the plausibility bounds (plausibility_bounds.BOUNDS) as BENCH["bounds"].
    path = DEVICE_SCRIPTS_DIR / script
    if bounds:
        return parse_facts(board.run_isolated(path, timeout_s=timeout_s, bounds=plausibility_bounds.BOUNDS))
    return parse_facts(board.run_isolated(path, timeout_s=timeout_s))


def _table(facts: "dict[str, object]", key: str) -> "dict[str, object]":
    value = facts.get(key)
    assert isinstance(value, dict), f"fact {key} is no table: {value!r} in {facts}"
    return value


# Bench counterpart: bench/test_bus_concurrency_under_api_load.py::test_concurrent_get_sensors_under_real_multi_client_load_never_corrupts_or_crashes
@pytest.mark.persistence_write
def test_scd30_same_device_read_write_concurrency(board: Board, scd30_measuring: str) -> None:
    # Owns one SCD30 NVM write: the ambient pressure the chip already holds, re-sent among a reader's reads.
    facts = _run(board, "scd30_same_device_rw_concurrency.py", _SCRIPT_TIMEOUT_S, bounds=True)
    assert "write_skipped" not in facts, f"the ambient-pressure write was skipped: {facts['write_skipped']}"
    assert "write_error" not in facts, f"the concurrent ambient-pressure write failed: {facts['write_error']}"
    assert facts.get("write_done") is True, f"the concurrent write never completed: {facts}"
    assert facts["read_completed"] == facts["reads_planned"], f"the reader completed {facts['read_completed']} of {facts['reads_planned']} reads"
    _no_errors(facts, "SCD30 read-vs-write")


# Bench counterpart: bench/test_bus_concurrency_under_api_load.py::test_concurrent_get_sensors_under_real_multi_client_load_never_corrupts_or_crashes
def test_same_device_concurrent_sessions_never_corrupt_each_other(board: Board, scd30_measuring: str) -> None:
    # Needs the SCD30 measuring (the session's prerequisite); reads and snapshots only, no write.
    facts = _run(board, "bus_concurrency_same_device_scd30.py", _LONG_SCRIPT_TIMEOUT_S, bounds=True)
    assert facts["reader_completed"] == facts["reader_planned"], f"reader: {facts['reader_completed']} of {facts['reader_planned']}"
    assert facts["snapshot_completed"] == facts["snapshot_planned"], f"snapshotter: {facts['snapshot_completed']} of {facts['snapshot_planned']}"
    _no_errors(facts, "SCD30 reader vs snapshotter")


# Bench counterpart: bench/test_bus_concurrency_under_api_load.py::test_concurrent_get_sensors_under_real_multi_client_load_never_corrupts_or_crashes
def test_cross_device_concurrent_sessions_genuinely_interleave(board: Board, scd30_measuring: str) -> None:
    # Needs the SCD30 measuring; the two rungs are a soft reset (no NVM) and the SGP40 heater-off.
    facts = _run(board, "bus_concurrency_cross_device_scd30_sgp40.py", _SCRIPT_TIMEOUT_S)
    assert facts["sgp_cycles"] == facts["sgp_cycles_planned"], f"SGP40 completed {facts['sgp_cycles']} of {facts['sgp_cycles_planned']} cycles"
    assert _count(facts, "scd_reads") > 0, "the SCD30 completed no read - its loop never progressed"
    assert _count(facts, "interleaved_total") >= _count(facts, "sgp_cycles"), f"only {facts['interleaved_total']} SCD30 reads inside {facts['sgp_cycles']} SGP40 windows - the bus lock is held too broadly"
    assert facts["reset_sibling_errors"] == 0, f"{facts['reset_sibling_errors']} sibling read failure(s) around the SCD30 soft reset"
    resumed = facts["scd30_resumed"]
    assert isinstance(resumed, int), f"the SCD30 reported no measurement after its soft reset: {facts}"
    assert resumed <= _count(facts, "scd30_resume_bound_ms"), f"the SCD30 measured again {resumed} ms after its reset, bound {facts['scd30_resume_bound_ms']} ms"
    assert facts["heater_off_sibling_errors"] == 0, f"{facts['heater_off_sibling_errors']} sibling read failure(s) around the SGP40 heater-off"
    assert facts["sgp_after_heater_off"] is not None, "the SGP40 gave no reading after its heater-off"
    _no_errors(facts, "SCD30 x SGP40 interleave")


# Bench counterpart: none, E.6.6 row `sgp40-general-call`
def test_sgp40_general_call_reset_does_not_corrupt_concurrent_scd30_and_isl29125_transactions(board: Board, scd30_measuring: str) -> None:
    # Both i2c1 siblings read through every general call; advancing CO2 (two or more values) proves measuring went on.
    facts = _run(board, "sgp40_general_call_reset_hazard.py", _LONG_SCRIPT_TIMEOUT_S, bounds=True)
    assert facts["sgp_completed"] == facts["sgp_cycles_planned"], f"SGP40 completed {facts['sgp_completed']} of {facts['sgp_cycles_planned']} reset cycles"
    assert _count(facts, "scd_completed") > 0, "the SCD30 completed no read"
    assert _count(facts, "isl_completed") > 0, "the ISL29125 completed no read"
    assert _count(facts, "distinct_co2_count") >= 2, f"only {facts['distinct_co2_count']} distinct CO2 value(s) - continuous measurement may have stopped"
    _no_errors(facts, "SGP40 general-call regression")


# Bench counterpart: bench/test_bus_concurrency_under_api_load.py::test_bmp3xx_config_write_does_not_disturb_its_own_concurrent_reads_under_api_load
def test_bmp3xx_same_device_read_write_concurrency(board: Board) -> None:
    # Volatile registers only, so no wear: the OSR writes, then the reset rung (soft reset and the OSR re-applied).
    facts = _run(board, "bmp3xx_same_device_rw_concurrency.py", _SCRIPT_TIMEOUT_S, bounds=True)
    assert facts["reads"] == facts["reads_planned"], f"reader: {facts['reads']} of {facts['reads_planned']}"
    assert facts["writes_ok"] == facts["writes_planned"], f"writer: {facts['writes_ok']} of {facts['writes_planned']}"
    assert facts["post_reset_valid"] is True, "no valid reading after the reset rung"
    assert facts["osr_after"] == facts["osr_configured"], f"OSR after the reset rung x{facts['osr_after']}, configured x{facts['osr_configured']}"
    _no_errors(facts, "BMP3xx read-vs-write and reset rung")


# Bench counterpart: bench/test_bus_concurrency_under_api_load.py::test_isl29125_config_write_does_not_disturb_concurrent_sibling_reads_under_api_load
def test_isl29125_same_device_read_write_concurrency(board: Board) -> None:
    # FN8424 p.7: the configuration registers are volatile, so this writes freely; the hazard is the destructive status read.
    facts = _run(board, "isl29125_same_device_rw_concurrency.py", _SCRIPT_TIMEOUT_S)
    assert facts["reads"] == facts["reads_planned"], f"reader: {facts['reads']} of {facts['reads_planned']}"
    assert facts["torn_reads"] == 0, f"{facts['torn_reads']} torn read(s)"
    assert facts["writes_ok"] == facts["writes_planned"], f"writer: {facts['writes_ok']} of {facts['writes_planned']}"
    _no_errors(facts, "ISL29125 read-vs-write")


# Bench counterpart: bench/test_bus_concurrency_under_api_load.py::test_concurrent_get_sensors_under_real_multi_client_load_never_corrupts_or_crashes
def test_sgp40_concurrent_sessions_each_get_a_tick(board: Board) -> None:
    # Silicon proves the three sessions are serialised; the payload each sends is pinned by the mock and twin tiers.
    facts = _run(board, "sgp40_same_device_concurrent_sessions.py", _SHORT_SCRIPT_TIMEOUT_S)
    low, high, source = plausibility_bounds.BOUNDS["voc_raw_ticks"]
    ticks = facts["ticks"]
    assert isinstance(ticks, list) and len(ticks) == 3, f"three sessions, answers {ticks}"
    assert all(isinstance(t, int) and low <= t <= high for t in ticks), f"ticks {ticks} not all in [{low}, {high}] ({source})"
    _no_errors(facts, "SGP40 concurrent sessions")


# Bench counterpart: bench/test_bus_concurrency_under_api_load.py::test_concurrent_get_sensors_under_real_multi_client_load_never_corrupts_or_crashes
def test_isl29125_cross_device_concurrency_with_its_i2c1_neighbours(board: Board, scd30_measuring: str) -> None:
    # The SCD30 leg reads real measurements, so it needs the session's measuring prerequisite.
    facts = _run(board, "isl29125_cross_device_concurrency.py", _SCRIPT_TIMEOUT_S)
    assert facts["sgp_cycles"] == facts["sgp_cycles_planned"], f"SGP40 completed {facts['sgp_cycles']} of {facts['sgp_cycles_planned']} cycles"
    assert _count(facts, "isl_reads") > 0, "the ISL29125 completed no read"
    assert _count(facts, "scd_reads") > 0, "the SCD30 completed no read - the third device never got the bus"
    assert _count(facts, "interleaved") > 0, "no ISL29125 read completed inside an SGP40 window - it serialises behind its neighbour"
    _no_errors(facts, "ISL29125 cross-device interleave")


# Bench counterpart: bench/test_bus_concurrency_under_api_load.py::test_isl29125_config_write_does_not_disturb_concurrent_sibling_reads_under_api_load
def test_isl29125_config_write_does_not_disturb_concurrent_sibling_reads(board: Board, scd30_measuring: str) -> None:
    # Real-hardware counterpart to the mock tier's scenario_a: an i2c1 occupant's write among its siblings' reads; the
    # ISL29125 writes because its registers are volatile. Needs the SCD30 measuring for the sibling reads.
    facts = _run(board, "bus_concurrency_isl29125_write_vs_siblings.py", _SCRIPT_TIMEOUT_S)
    assert facts["write_count"] == facts["write_cycles_planned"], f"ISL29125 completed {facts['write_count']} of {facts['write_cycles_planned']} writes"
    assert _count(facts, "scd_reads") > 0, "the SCD30 completed no read"
    assert _count(facts, "sgp_reads") > 0, "the SGP40 completed no read"
    _no_errors(facts, "ISL29125 write among sibling reads")


# Bench counterpart: bench/test_bus_concurrency_under_api_load.py::test_scd30_config_write_does_not_disturb_concurrent_sibling_reads_under_api_load
@pytest.mark.persistence_write
@pytest.mark.scd30_extra_write
def test_scd30_config_write_does_not_disturb_concurrent_sibling_reads(board: Board, scd30_measuring: str) -> None:
    # Owns two SCD30 NVM writes (the offset and its restore), so it runs only with --allow-persistence-write and
    # --allow-scd30-extra-write.
    facts = _run(board, "bus_concurrency_scd30_write_vs_siblings.py", _SCRIPT_TIMEOUT_S)
    assert "write_skipped" not in facts and facts["prior_offset"] is not None, f"the prior offset could not be read, nothing was written: {facts}"
    assert "write_error" not in facts, f"the SCD30 offset write failed: {facts['write_error']}"
    assert isinstance(facts.get("write_done"), int), f"the SCD30 offset write never completed: {facts}"
    assert "restore_error" not in facts, f"the offset restore failed: {facts['restore_error']}"
    assert facts["restored"] == facts["prior_offset"], f"offset after the restore {facts['restored']}, before the run {facts['prior_offset']}"
    assert _count(facts, "isl_windows") > 0, "the ISL29125 completed no read"
    assert _count(facts, "sgp_reads") > 0, "the SGP40 completed no read"
    _no_errors(facts, "SCD30 write among sibling reads")


# Bench counterpart: none, E.6.6 row `flash-only-bus-checks`
def test_isl29125_real_irq_edge_beats_the_periodic_fallback(board: Board, result_note: _ResultNote) -> None:
    # The script fails unless PRST counts whole RGB cycles, the unit persist_for_interval() assumes;
    # whether a CONFIG1 write restarts a conversion is reported only.
    facts = _run(board, "isl29125_real_irq_edge.py", _SCRIPT_TIMEOUT_S)
    result_note(f"config1_restart={facts['config1_restart']}")
    persist = facts["persist_unit"]
    assert isinstance(persist, dict), f"no PRST measurement: {facts}"
    assert persist["unit"] == "rgb_cycles", f"PRST={persist}: persist_for_interval() assumes whole RGB cycles"
    assert facts["died"] == [], f"a reader task died: {facts['died']}"
    fast = facts["fast_path_ms"]
    assert isinstance(fast, int), f"no reading within {facts['deadline_ms']} ms (periodic fallback {facts['trigger_s']} s) - the INT line does not reach its pin"
    assert fast <= _count(facts, "deadline_ms"), f"the interrupt-driven reading took {fast} ms, deadline {facts['deadline_ms']} ms"


# Bench counterpart: none, E.6.6 row `flash-only-bus-checks`
def test_bus_topology_autodetect_address_and_reserved_range_sweep(board: Board, result_note: _ResultNote) -> None:
    # Reads only: no SCD30 measuring needed, and a lone device survives a rogue broadcast without it.
    facts = _run(board, "bus_topology_autodetect_and_hazard_sweep.py", _SCRIPT_TIMEOUT_S, bounds=True)
    result_note(f"addresses={facts['addresses']} unknown_addresses={facts['unknown_addresses']}")
    assert not any(_table(facts, "reserved_hits").values()), f"reserved addresses acknowledged: {facts['reserved_hits']}"
    for bus_id, hazard in _table(facts, "self_hazard").items():
        assert isinstance(hazard, dict), facts
        assert hazard["broadcasts"] >= 1, f"{bus_id}: no general call reached the bus ({hazard['broadcasts']} of {hazard['broadcasts_planned']} sent, {hazard['naks']} NAKed), so the lone {hazard['device']}'s reads raced nothing"
        assert hazard["clean_reads"] == hazard["planned"], f"{bus_id}: the lone {hazard['device']} read clean {hazard['clean_reads']} of {hazard['planned']} times through general calls"
    assert all(status == 0 for status in _table(facts, "recover_status").values()), f"recover() on a healthy bus: {facts['recover_status']}"
    assert not any(_table(facts, "recover_sibling_errors").values()), f"reads failed beside recover(): {facts['recover_sibling_errors']}"
    assert all(_table(facts, "heater_off_ok").values()), f"a sibling read failed after the SGP40 heater-off: {facts['heater_off_ok']}"
    assert facts["write_eio"] == 0, f"write_eio={facts['write_eio']}: the drivers' register transfers raised EIO on a healthy bus"
    assert not any(_table(facts, "por_after_setup").values()), f"por_after_setup={facts['por_after_setup']}: reset() did not consume the flag its own soft reset raised"
    assert facts["isl_divergences"] == 0, f"isl_divergences={facts['isl_divergences']}: an ISL29125 snapshot diverged from the driver's shadow"
    _no_errors(facts, "bus sweep")


# Bench counterpart: none, E.6.6 row `flash-only-bus-checks`
def test_a_held_sda_line_is_cleared_and_every_device_answers(board: Board, result_note: _ResultNote) -> None:
    # A real held SDA, cleared by the runtime rung and by the boot-time clear; no device register is written.
    facts = _run(board, "i2c_held_sda_recovery.py", _SHORT_SCRIPT_TIMEOUT_S, bounds=True)
    assert facts["held_device"] is not None, "no discovered device answers a pointer read with a 0 first bit - nothing to hold"
    runtime, boot = facts["runtime_clear"], facts["boot_clear"]
    assert isinstance(runtime, dict) and isinstance(boot, dict), facts
    result_note(f"held {facts['held_device']}, runtime clear {runtime['clear_ms']} ms")
    assert runtime["held"] is True, f"the bit-banged read left SDA high - no held line was made: {runtime}"
    assert runtime["stuck_errno"] in (errno.ETIMEDOUT, errno.EIO), f"a transfer on the held bus gave {runtime['stuck_errno']}, not ETIMEDOUT or EIO"
    assert runtime["status"] == _REC_SDA_LOW, f"clear() returned {runtime['status']}, expected SDA-low ({_REC_SDA_LOW}) without stuck ({_REC_SDA_STUCK})"
    assert all(answer is None for answer in runtime["answered"].values()), f"after the runtime clear: {runtime['answered']}"
    assert boot["held"] is True and boot["sda_high"] is True, f"the boot-time clear did not release SDA: {boot}"
    assert boot["status"] == _REC_SDA_LOW, f"the boot-time clear returned {boot['status']}, expected {_REC_SDA_LOW}"
    assert all(answer is None for answer in boot["answered"].values()), f"after the boot-time clear: {boot['answered']}"


# Bench counterpart: none, E.6.6 row `flash-only-bus-checks`
def test_bmp3xx_alone_survives_a_general_call(board: Board, result_note: _ResultNote) -> None:
    # A lone BMP3xx through general-call resets: volatile registers only, restored by a soft reset at the end.
    facts = _run(board, "bmp3xx_alone_survives_a_general_call.py", _SHORT_SCRIPT_TIMEOUT_S, bounds=True)
    result_note(f"naks={facts['naks']} devices_on_bus={facts['devices_on_bus']}")
    assert _count(facts, "broadcasts") >= _count(facts, "broadcasts_planned"), f"{facts['broadcasts']} of {facts['broadcasts_planned']} broadcasts sent"
    assert _count(facts, "reads") > 0, "the reader completed no read"
    assert facts["before"] == facts["after"], f"the BMP3xx state changed through the general calls: before {facts['before']}, after {facts['after']}"
    assert _table(facts, "before")["snapshot"] == facts["distinct"], f"the distinctive settings never applied: {facts['before']}"
    assert facts["por_after"] is False, "the BMP3xx flagged a power-on reset: a general call reset it"
    _no_errors(facts, "lone BMP3xx through general calls")


# Bench counterpart: none, E.6.6 row `flash-only-bus-checks`
def test_fram_same_device_read_write_concurrency(board: Board) -> None:
    # FRAM has no write wear (10^13 operations per byte); the reads are of production bytes, after the evidence save.
    facts = _run(board, "fram_same_device_rw_concurrency.py", _SCRIPT_TIMEOUT_S)
    assert facts["initialized"] is True, "the FRAM did not set up"
    assert facts["reads_ok"] == facts["reads_planned"], f"{facts['reads_ok']} of {facts['reads_planned']} reads matched the baseline"
    assert facts["write_ok"] is True and facts["write_readback_ok"] is True, f"the scratch write did not land intact: {facts}"
    _no_errors(facts, "FRAM read-vs-write")


# Bench counterpart: none, E.6.6 row `flash-only-bus-checks`
def test_fram_cs_pin_hijack_fault_injection_and_recovery(board: Board) -> None:
    # Needs no separate fault-injection hardware: the RP2040 owns CS as a GPIO.
    facts = _run(board, "fram_cs_hijack_fault_injection_and_recovery.py", _SHORT_SCRIPT_TIMEOUT_S)
    assert facts["initialized"] is True, "the FRAM did not set up"
    write, read, wren, lost = (facts[key] for key in ("write_hijack", "read_hijack", "wren_dropped", "chip_lost"))
    assert isinstance(write, dict) and isinstance(read, dict) and isinstance(wren, dict) and isinstance(lost, dict), facts
    assert write["injected"] and read["injected"] and wren["injected"], f"an injection never landed with CS asserted: {write}, {read}, {wren}"
    # Hard requirement (owner, 2026-09-04): a hijacked write never reaches the chip, a hijacked read never returns real data.
    assert write["readback_ok"] is True, f"the hijacked write reached the chip although CS was deasserted first: {write}"
    assert read["real_data_returned"] is False, f"the hijacked read returned the real data: {read}"
    assert write["recovered"] and read["recovered"], f"the driver did not recover: {write}, {read}"
    assert wren["readback_ok"] is True, f"the write after a dropped WREN did not land (the driver's one WREN retry): {wren}"
    assert lost["initialized_after"] is False, f"CS held inactive across two writes: the chip was never declared lost: {lost}"
    assert _ERR_FRAM_CHIP_LOST in lost["errnos"], f"no chip-lost entry (errno {_ERR_FRAM_CHIP_LOST}) in the driver's log: {lost['errnos']}"
    assert lost["setup_after_release"] is True and lost["recovered"] is True, f"CS released, setup() did not bring the chip back: {lost}"
    assert facts["system_task_exceptions"] == [], f"a task ended with an exception under the fault: {facts['system_task_exceptions']}"


# Bench counterpart: none, E.6.6 row `flash-only-bus-checks`
def test_fram_hard_reset_race_during_write_and_recovery(board: Board) -> None:
    # A real machine.reset() inside a FRAM write's payload transfer, then the verify after the board is back.
    out = board.run_isolated_expect_reset(DEVICE_SCRIPTS_DIR / "fram_reset_race_during_write_seed_and_race.py", timeout_s=_RESET_SCRIPT_TIMEOUT_S)
    seed = parse_facts(out, allow_missing_done=True)
    assert seed.get("seeded") == [True, True, True], f"the race region was not seeded: {seed}"
    assert seed.get("system_task_exceptions") == [], f"a task ended with an exception while seeding: {seed}"
    assert "RESET_RACE_ARMED" in out and "reset_fired" not in seed, f"the reset never fired inside the write - nothing was tested:\n{out}"
    wait_until(board.is_reachable, timeout_s=_REACHABLE_TIMEOUT_S, poll_interval_s=_REACHABLE_POLL_S, description="board reachable again after the real reset-raced write")
    facts = _run(board, "fram_reset_race_during_write_verify_recovery.py", _SHORT_SCRIPT_TIMEOUT_S)
    assert facts["guard_before_ok"] is True and facts["guard_after_ok"] is True, f"a guard region around the target changed: {facts}"
    state = facts["target_state"]
    assert state == "original" or (isinstance(state, str) and state.startswith("prefix:")), f"the target holds {state}: neither its original bytes nor a prefix of the new ones"
    assert facts["recovered"] is True, "the driver did not recover after the reset"
    assert facts["seed_restored"] is True, "the race region was not restored to its seed state"


# Bench counterpart: none, E.6.6 row `flash-only-bus-checks`
def test_i2c_and_spi_deinit_are_silent_noops_and_each_bus_id_is_a_singleton(board: Board) -> None:
    # SPECIFICATION.md Part F.5.1 on a live bus: read from the port's protocol tables and modelled in the fakes.
    facts = _run(board, "bus_deinit_is_a_noop_on_real_hardware.py", _SHORT_SCRIPT_TIMEOUT_S)
    assert facts["i2c_has_deinit"] is True, "machine.I2C has no deinit() - this build predates 1.29"
    assert facts["scan_before"], "no I2C device found before deinit() - a wiring problem, not a deinit finding"
    assert facts["scan_after"] == facts["scan_before"], f"I2C.deinit() stopped the bus: scan {facts['scan_before']} -> {facts['scan_after']}"
    assert facts["i2c_singleton"] is True, "machine.I2C(id) built a new object on re-construction"
    assert facts["spi_singleton"] is True, "machine.SPI(id) built a new object on re-construction"
    assert facts["spi_read_after_deinit"] is True, "a FRAM read failed after machine.SPI.deinit()"
    assert facts["chunk_cleared"] is True, "the scratch chunk was not cleared on the way out"


# Bench counterpart: none, E.6.6 row `flash-only-bus-checks`
def test_fram_erase_racing_a_chunk_write_leaves_no_torn_chunk(board: Board, request: pytest.FixtureRequest, result_note: _ResultNote) -> None:
    # The erase blanks the FRAM logs: the raw dump is saved first, then again after the production boot.
    save_fram_raw(board, "erase-racing-a-chunk-write")
    try:
        out = board.run_isolated_expect_reset(DEVICE_SCRIPTS_DIR / "system_command_fram_erase.py", timeout_s=_LONG_SCRIPT_TIMEOUT_S, STATE="loads")
        facts = parse_facts(out, allow_missing_done=True)
        assert "ERASE START" in out.splitlines() and "failure" not in facts, f"the erase never started under the logger writes:\n{out}"
        erase, reset = facts.get("erase"), facts.get("reset")
        assert isinstance(erase, dict) and erase.get("ok") is True, f"the erase did not complete before the reset: {erase}"
        assert isinstance(reset, dict) and reset.get("code") == _RR_FRAM_ERASED, f"the erase armed {reset}, not reset code {_RR_FRAM_ERASED}"
        result_note(f"erase {erase.get('ms')} ms under {reset.get('loads')} (load writes, bus reads, bus faults)")
        late = _after_boot_band(board, request, result_note, "erase-racing-a-chunk-write")
        if late is not None:
            assert not late, f"test-band SYSTEM entries outlived the erase (a racing chunk write landed after it, or a ring was kept): {late}"
    finally:
        _remove_command_scratch(board)


# Bench counterpart: none, E.6.6 row `flash-only-bus-checks`
def test_reboot_command_shuts_down_then_resets(board: Board, request: pytest.FixtureRequest, result_note: _ResultNote) -> None:
    # The reboot command with a logger write and an I2C read in flight; the evidence is saved before it runs.
    save_fram_raw(board, "reboot-command")
    try:
        out = board.run_isolated_expect_reset(DEVICE_SCRIPTS_DIR / "system_command_reboot.py", timeout_s=_LONG_SCRIPT_TIMEOUT_S, COMMAND="reboot")
        facts = parse_facts(out, allow_missing_done=True)
        reset, written = facts.get("reset"), facts.get("written")
        assert "failure" not in facts and facts.get("answer") == "Valid", f"the reboot command was not accepted: {facts}"
        assert isinstance(reset, dict) and reset.get("code") == _RR_REBOOT, f"the reboot armed {reset}, not reset code {_RR_REBOOT}"
        codes = written.get("SYSTEM") if isinstance(written, dict) else None
        assert isinstance(codes, list) and codes, f"the script reported no log entry written before the reset: {facts}"
        kept = _after_boot_band(board, request, result_note, "reboot-command")
        if kept is not None:
            # Newest last on both sides: the ring's newest test-band entry is the last write reported, or the one in flight.
            assert kept, f"the SYSTEM ring lost every entry written before the reset (a torn or dropped chunk): wrote {codes[-3:]}"
            assert kept[-1] in codes[-2:], f"the ring's newest test-band entry {kept[-1]} is not among the last writes reported {codes[-2:]}"
    finally:
        _remove_command_scratch(board)
