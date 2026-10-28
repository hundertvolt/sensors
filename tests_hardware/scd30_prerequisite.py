"""The flash tier's SCD30 prerequisite: read the measurement interval, wait up to three intervals for a measurement,
and send the NVM-persisted start command only when none arrives - at most once per pytest session and never retried
(owner, 2026-09-29), so a default run normally writes the SCD30's NVM zero times."""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from harness import DEVICE_SCRIPTS_DIR, HardwareTestFailureError, parse_facts

if TYPE_CHECKING:
    from pathlib import Path

INTERVAL_SCRIPT = DEVICE_SCRIPTS_DIR / "scd30_measurement_interval_read.py"
WAIT_SCRIPT = DEVICE_SCRIPTS_DIR / "scd30_data_ready_wait.py"
START_SCRIPT = DEVICE_SCRIPTS_DIR / "scd30_start_continuous_measurement.py"

# One setup and a register read bound both the interval read and the start script (one read-back, one send).
# @tunable l3.scd30_prerequisite_interval_read_timeout_s = 30.0
_INTERVAL_READ_TIMEOUT_S = 30.0
# @tunable l3.scd30_prerequisite_wait_margin_s = 60
_WAIT_MARGIN_S = 60


class _Runner(Protocol):
    def run_isolated(self, script_path: "str | Path", *, soft_reset_after: bool = True, timeout_s: "float | None" = None, allow_recovery: bool = True, **extras: object) -> str: ...


@dataclass
class Session:
    # Set before the one send and never reset: a second start in the same pytest session is refused.
    start_sent: bool = False


def new_session() -> Session:
    return Session()


def interval_facts(board: _Runner) -> "dict[str, object]":
    # The read-only interval script's facts as it yields them (an interval or an error); the session snapshot reads this.
    return parse_facts(board.run_isolated(INTERVAL_SCRIPT, timeout_s=_INTERVAL_READ_TIMEOUT_S))


def _interval(board: _Runner) -> int:
    facts = interval_facts(board)
    interval = facts.get("interval")
    if not isinstance(interval, int) or isinstance(interval, bool) or interval <= 0:
        raise HardwareTestFailureError(f"the SCD30 measurement interval read gave no interval, so nothing is sent: {facts}")
    return interval


def _measuring(board: _Runner, interval: int) -> bool:
    facts = parse_facts(board.run_isolated(WAIT_SCRIPT, timeout_s=3 * interval + _WAIT_MARGIN_S))
    measuring = facts.get("measuring")
    if not isinstance(measuring, bool):
        raise HardwareTestFailureError(f"the SCD30 data-ready wait reported no measuring fact: {facts}")
    return measuring


def ensure_scd30_measuring(board: _Runner, state: Session) -> str:
    # Returns what it did, for the session note; every failure raises, and none after the guard is set retries.
    interval = _interval(board)
    if _measuring(board, interval):
        return "already measuring (no write)"
    if state.start_sent:
        raise HardwareTestFailureError("the SCD30 start command was already sent this session; not resending")
    state.start_sent = True
    facts = parse_facts(board.run_isolated(START_SCRIPT, timeout_s=_INTERVAL_READ_TIMEOUT_S))
    if "invalid_readback" in facts:
        raise HardwareTestFailureError(f"invalid ambient read-back {facts['invalid_readback']}: the SCD30 start command was not sent")
    if facts.get("sent") is not True:
        raise HardwareTestFailureError(f"the SCD30 start script reported no send: {facts}")
    if not _measuring(board, interval):
        raise HardwareTestFailureError("started but no measurement within 3 intervals")
    return "started (one NVM write)"
