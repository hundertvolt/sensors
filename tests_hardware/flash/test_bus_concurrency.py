"""Flash-tier automated tests: real-hardware confirmation of SPECIFICATION.md Part C.8's I2C
concurrency/locking model, a regression test for the SGP40 general-call reset hazard, same-device
read/write concurrency per sensor, and a live-topology address/reserved-range/self-hazard sweep."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from harness import Board, wait_until

DEVICE_SCRIPTS = Path(__file__).resolve().parent.parent / "device_scripts"
RESULT_RE = re.compile(r"^RESULT: (PASS|FAIL)(.*)$", re.MULTILINE)


def _assert_pass(output: str, what: str) -> None:
    match = RESULT_RE.search(output)
    assert match is not None, f"device script printed no RESULT line - full output:\n{output}"
    assert match.group(1) == "PASS", f"{what} failed: {match.group(2).strip()}\nfull output:\n{output}"


@pytest.mark.persistence_write
def test_scd30_same_device_read_write_concurrency_and_continuous_measurement_trigger(scd30_continuous_measurement_triggered: None) -> None:
    # Declaring the fixture as a parameter is what runs it. This test exists only to give that
    # one real NVM write its own named, first-to-run pass/fail surface; the SCD30 tests below
    # depend on the same session-scoped fixture and so pay nothing extra.
    pass


@pytest.mark.persistence_write
def test_same_device_concurrent_sessions_never_corrupt_each_other(board: Board, scd30_continuous_measurement_triggered: None) -> None:
    # Generous relative to the device script's own ~90s internal asyncio.wait_for budget.
    output = board.run_isolated(DEVICE_SCRIPTS / "bus_concurrency_same_device_scd30.py", timeout_s=120.0)
    _assert_pass(output, "same-device concurrency check")


@pytest.mark.persistence_write
def test_cross_device_concurrent_sessions_genuinely_interleave(board: Board, scd30_continuous_measurement_triggered: None) -> None:
    output = board.run_isolated(DEVICE_SCRIPTS / "bus_concurrency_cross_device_scd30_sgp40.py", timeout_s=90.0)
    _assert_pass(output, "cross-device interleaving check")


@pytest.mark.persistence_write
def test_sgp40_general_call_reset_does_not_corrupt_concurrent_scd30_and_isl29125_transactions(board: Board, scd30_continuous_measurement_triggered: None) -> None:
    # Both real i2c1 siblings, not just SCD30 - closes a gap tests/_bus_hazard_catalog.py's own
    # generic scenario_general_call_does_not_disturb_concurrent_siblings surfaced (it runs against
    # every non-broadcasting occupant of the bus, which real hardware used to only partially mirror).
    output = board.run_isolated(DEVICE_SCRIPTS / "sgp40_general_call_reset_hazard.py", timeout_s=120.0)
    _assert_pass(output, "SGP40 general-call hazard regression check")


def test_bmp3xx_same_device_read_write_concurrency(board: Board) -> None:
    # No NVM-write-budget dependency - BMP3xx's own config registers are volatile (see the device
    # script's own docstring), so this needs no session fixture.
    output = board.run_isolated(DEVICE_SCRIPTS / "bmp3xx_same_device_rw_concurrency.py", timeout_s=90.0)
    _assert_pass(output, "BMP3xx same-device read/write concurrency check")


def test_isl29125_same_device_read_write_concurrency(board: Board) -> None:
    # No NVM-write budget at all here, unlike BMP3xx: FN8424 p7 calls the ISL29125's config
    # registers volatile outright, so rewriting them costs nothing. The real hazard is the
    # DESTRUCTIVE 0x08 status read, which a config write landing mid-cycle must not tear.
    output = board.run_isolated(DEVICE_SCRIPTS / "isl29125_same_device_rw_concurrency.py", timeout_s=90.0)
    _assert_pass(output, "ISL29125 same-device read/write concurrency check")


@pytest.mark.persistence_write
def test_isl29125_cross_device_concurrency_with_its_i2c1_neighbours(board: Board, scd30_continuous_measurement_triggered: None) -> None:
    # The SCD30 leg reads real measurements, so it needs the same session fixture the other
    # SCD30-touching tests take; the ISL and SGP40 legs would run fine without it.
    output = board.run_isolated(DEVICE_SCRIPTS / "isl29125_cross_device_concurrency.py", timeout_s=90.0)
    _assert_pass(output, "ISL29125 cross-device interleaving check")


@pytest.mark.persistence_write
def test_isl29125_config_write_does_not_disturb_concurrent_sibling_reads(board: Board, scd30_continuous_measurement_triggered: None) -> None:
    # Real-hardware counterpart to _bus_hazard_catalog.py's scenario_a (Part C.8), closing a gap
    # that catalog surfaced: nothing here had proved one dev/i2c1 occupant's WRITE landing among
    # its siblings' reads. ISL29125 writes because its registers are volatile; SCD30's is opt-in.
    output = board.run_isolated(DEVICE_SCRIPTS / "bus_concurrency_isl29125_write_vs_siblings.py", timeout_s=90.0)
    _assert_pass(output, "ISL29125 config-write-vs-concurrent-sibling-reads check")


@pytest.mark.persistence_write
@pytest.mark.scd30_extra_write
def test_scd30_config_write_does_not_disturb_concurrent_sibling_reads(board: Board, scd30_continuous_measurement_triggered: None) -> None:
    # The SCD30-as-writer half of the same gap, deliberately outside the routine group: it spends
    # one NVM write beyond the fixture's, so conftest.py's pytest_collection_modifyitems()
    # deselects it unless BOTH --allow-persistence-writes and --allow-scd30-extra-write are given.
    output = board.run_isolated(DEVICE_SCRIPTS / "bus_concurrency_scd30_write_vs_siblings.py", timeout_s=90.0)
    _assert_pass(output, "SCD30 config-write-vs-concurrent-sibling-reads check")


def test_isl29125_real_irq_edge_beats_the_periodic_fallback(board: Board) -> None:
    # Also measures the two datasheet questions no document answers - whether a CONFIG1 write
    # restarts the conversion, and whether PRST counts RGB cycles or single-channel integrations.
    # Both are reported on the RESULT line whatever the verdict; neither gates the pass.
    output = board.run_isolated(DEVICE_SCRIPTS / "isl29125_real_irq_edge.py", timeout_s=90.0)
    _assert_pass(output, "ISL29125 real INT-pin falling-edge fast-path check")


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
    # Real hardware-reset race against an in-flight FRAM write: a different fault from the
    # CS-hijack above, since this is a real machine.reset() rather than a protocol-level deselect.
    # fram_reset_race_during_write_seed_and_race.py's docstring has the mechanism.
    board.run_isolated_expect_reset(DEVICE_SCRIPTS / "fram_reset_race_during_write_seed_and_race.py", timeout_s=30.0)
    # is_reachable(), not the presence-only is_device_present() - the same pattern
    # test_config_value_survives_a_genuine_hard_reset uses. The freshly-rebooted firmware is
    # interrupted by the verify phase below anyway, so there is no live system to protect here.
    wait_until(board.is_reachable, timeout_s=30.0, poll_interval_s=1.0, description="board reachable again after the real reset-raced write")
    output = board.run_isolated(DEVICE_SCRIPTS / "fram_reset_race_during_write_verify_recovery.py", timeout_s=60.0)
    _assert_pass(output, "FRAM hard-reset race during write recovery check")


# ---------------------------------------------------------------------------
# SPECIFICATION.md Part F.5.1, on a live bus. Both claims were read out of the rp2 port's own
# protocol tables and modelled in tests/machine.py and digital_twin/machine.py - but a fake
# agreeing with a fake proves nothing about silicon.
# ---------------------------------------------------------------------------


def test_i2c_and_spi_deinit_are_silent_noops_and_each_bus_id_is_a_singleton(board: Board) -> None:
    output = board.run_isolated(DEVICE_SCRIPTS / "bus_deinit_is_a_noop_on_real_hardware.py", timeout_s=60.0)
    _assert_pass(output, "I2C/SPI deinit() no-op and bus-singleton check")
