"""Flash-tier automated tests: real-hardware confirmation of SPECIFICATION.md Part C.8's I2C
concurrency/locking model (device-session lock serializes same-device multi-transaction sequences;
the bus lock is fine-grained enough to let different devices on a shared bus genuinely interleave),
plus a regression test for the SGP40 general-call reset broadcast hazard found while auditing that
model. Closes a real gap: nothing in this tier previously spun up concurrent coroutines against real
hardware to prove the locking model holds under real contention (only mock-level tests exist for the
raw bus-lock mechanism - tests/test_asy_i2c_driver.py's "asyncio interlock" section - none of which
touch a real device's own CRC-8-protected wire protocol or a second real device sharing the bus).

Uses this dev bench's own real wiring (sensortask_dev.py): SCD30 + SGP40 share I2C1 (scl=15,
sda=14); BMP3xx sits alone on I2C0. Production wozi wiring pairs SGP40 with BMP3xx instead (SCD30
alone) - see this session's own Part 1 bus-hazard report for why both pairings independently check
out against their respective datasheets, and why the dev-bench pairing tested here is still valid
evidence for wozi too (CLAUDE.md's own "a passing dev-bench result is treated as valid for wozi too,
provided the code under test is genuinely dev-native" rule - these device scripts use dev's own
correct pins via sensortask_dev.py's own wiring comments, never wozi's hardcoded build)."""

from __future__ import annotations

import re
from pathlib import Path

from harness import Board

DEVICE_SCRIPTS = Path(__file__).resolve().parent.parent / "device_scripts"
RESULT_RE = re.compile(r"^RESULT: (PASS|FAIL)(.*)$", re.MULTILINE)


def test_same_device_concurrent_sessions_never_corrupt_each_other(board: Board) -> None:
    # Generous relative to the device script's own ~90s internal asyncio.wait_for budget.
    output = board.run_isolated(DEVICE_SCRIPTS / "bus_concurrency_same_device_scd30.py", timeout_s=120.0)
    match = RESULT_RE.search(output)
    assert match is not None, f"device script printed no RESULT line - full output:\n{output}"
    assert match.group(1) == "PASS", f"same-device concurrency check failed: {match.group(2).strip()}\nfull output:\n{output}"


def test_cross_device_concurrent_sessions_genuinely_interleave(board: Board) -> None:
    output = board.run_isolated(DEVICE_SCRIPTS / "bus_concurrency_cross_device_scd30_sgp40.py", timeout_s=90.0)
    match = RESULT_RE.search(output)
    assert match is not None, f"device script printed no RESULT line - full output:\n{output}"
    assert match.group(1) == "PASS", f"cross-device interleaving check failed: {match.group(2).strip()}\nfull output:\n{output}"


def test_sgp40_general_call_reset_does_not_corrupt_a_concurrent_scd30_transaction(board: Board) -> None:
    output = board.run_isolated(DEVICE_SCRIPTS / "sgp40_general_call_reset_hazard.py", timeout_s=120.0)
    match = RESULT_RE.search(output)
    assert match is not None, f"device script printed no RESULT line - full output:\n{output}"
    assert match.group(1) == "PASS", f"SGP40 general-call hazard regression check failed: {match.group(2).strip()}\nfull output:\n{output}"
