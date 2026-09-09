"""Flash-tier automated tests: real-hardware confirmation of SPECIFICATION.md Part C.8's I2C
concurrency/locking model, a regression test for the SGP40 general-call reset hazard, same-device
read/write concurrency per sensor, and a live-topology address/reserved-range/self-hazard sweep."""

from __future__ import annotations

import re
from pathlib import Path

from harness import Board, wait_until

DEVICE_SCRIPTS = Path(__file__).resolve().parent.parent / "device_scripts"
RESULT_RE = re.compile(r"^RESULT: (PASS|FAIL)(.*)$", re.MULTILINE)


def _assert_pass(output: str, what: str) -> None:
    match = RESULT_RE.search(output)
    assert match is not None, f"device script printed no RESULT line - full output:\n{output}"
    assert match.group(1) == "PASS", f"{what} failed: {match.group(2).strip()}\nfull output:\n{output}"


def test_scd30_same_device_read_write_concurrency_and_continuous_measurement_trigger(scd30_continuous_measurement_triggered: None) -> None:
    # Declaring the fixture as a parameter is what actually runs it (pytest fixture semantics) -
    # this test exists to give that one real NVM write its own clearly-named, first-to-run pass/
    # fail surface, even though every other SCD30-dependent test below also (harmlessly, thanks to
    # session-scoped caching) depends on the same fixture.
    pass


def test_same_device_concurrent_sessions_never_corrupt_each_other(board: Board, scd30_continuous_measurement_triggered: None) -> None:
    # Generous relative to the device script's own ~90s internal asyncio.wait_for budget.
    output = board.run_isolated(DEVICE_SCRIPTS / "bus_concurrency_same_device_scd30.py", timeout_s=120.0)
    _assert_pass(output, "same-device concurrency check")


def test_cross_device_concurrent_sessions_genuinely_interleave(board: Board, scd30_continuous_measurement_triggered: None) -> None:
    output = board.run_isolated(DEVICE_SCRIPTS / "bus_concurrency_cross_device_scd30_sgp40.py", timeout_s=90.0)
    _assert_pass(output, "cross-device interleaving check")


def test_sgp40_general_call_reset_does_not_corrupt_a_concurrent_scd30_transaction(board: Board, scd30_continuous_measurement_triggered: None) -> None:
    output = board.run_isolated(DEVICE_SCRIPTS / "sgp40_general_call_reset_hazard.py", timeout_s=120.0)
    _assert_pass(output, "SGP40 general-call hazard regression check")


def test_bmp3xx_same_device_read_write_concurrency(board: Board) -> None:
    # No NVM-write-budget dependency - BMP3xx's own config registers are volatile (see the device
    # script's own docstring), so this needs no session fixture.
    output = board.run_isolated(DEVICE_SCRIPTS / "bmp3xx_same_device_rw_concurrency.py", timeout_s=90.0)
    _assert_pass(output, "BMP3xx same-device read/write concurrency check")


def test_bus_topology_autodetect_address_and_reserved_range_sweep(board: Board) -> None:
    # Deliberately does NOT depend on scd30_continuous_measurement_triggered - this sweep only ever
    # *reads* SCD30 (see the device script's own docstring), and its self-hazard branch doesn't
    # need continuous measurement to be active to prove a lone device survives a rogue broadcast.
    output = board.run_isolated(DEVICE_SCRIPTS / "bus_topology_autodetect_and_hazard_sweep.py", timeout_s=90.0)
    _assert_pass(output, "bus-topology autodetect/address/reserved-range/self-hazard sweep")


def test_fram_same_device_read_write_concurrency(board: Board) -> None:
    # No NVM-write-budget dependency, like BMP3xx above - FRAM's real datasheet endurance is
    # 10^13 read/write operations per byte (see the device script's own docstring), not wear-limited
    # for any realistic test usage.
    output = board.run_isolated(DEVICE_SCRIPTS / "fram_same_device_rw_concurrency.py", timeout_s=90.0)
    _assert_pass(output, "FRAM same-device read/write concurrency check")


def test_fram_cs_pin_hijack_fault_injection_and_recovery(board: Board) -> None:
    # Real-hardware GPIO-level fault injection against FRAM's own CS pin - see the device script's
    # own docstring for the full mechanism and why it needed no separate fault-injection hardware
    # (BACKLOG.md open question 8's "not currently provisioned" GPIO harness doesn't apply here).
    output = board.run_isolated(DEVICE_SCRIPTS / "fram_cs_hijack_fault_injection_and_recovery.py", timeout_s=60.0)
    _assert_pass(output, "FRAM CS-pin hijack fault-injection/recovery check")


def test_fram_hard_reset_race_during_write_and_recovery(board: Board) -> None:
    # Real hardware-reset race against an in-flight FRAM write - a genuinely different fault than
    # the CS-hijack race above (a real RP2040-side machine.reset(), not a controlled SPI-protocol-
    # level CS deselect) - see fram_reset_race_during_write_seed_and_race.py's own docstring for the
    # full mechanism and its honest, deliberately-scoped-safe design.
    board.run_isolated_expect_reset(DEVICE_SCRIPTS / "fram_reset_race_during_write_seed_and_race.py", timeout_s=30.0)
    # is_reachable() (not the presence-only is_device_present()), same established pattern
    # test_reboot_persistence.py's own test_config_value_survives_a_genuine_hard_reset uses - the
    # real, freshly-rebooted production firmware is about to be interrupted for the verify phase
    # below anyway, so there's no live system here to avoid disturbing.
    wait_until(board.is_reachable, timeout_s=30.0, poll_interval_s=1.0, description="board reachable again after the real reset-raced write")
    output = board.run_isolated(DEVICE_SCRIPTS / "fram_reset_race_during_write_verify_recovery.py", timeout_s=60.0)
    _assert_pass(output, "FRAM hard-reset race during write recovery check")
