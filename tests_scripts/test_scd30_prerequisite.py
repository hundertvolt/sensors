"""tests_hardware/scd30_prerequisite.py on a scripted fake board: the NVM-persisted start command is sent only when no
measurement arrives within three intervals, at most once per session and never retried, and every failure mode
raises naming itself after at most that one send - a failed read never writes blind."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests_hardware"))
import scd30_prerequisite
from harness import HardwareTestFailureError

_INTERVAL = 2


def _facts(**facts: object) -> str:
    return "".join(f"FACT {key}={json.dumps(value)}\n" for key, value in facts.items()) + "DONE\n"


class _FakeBoard:
    # Answers each prerequisite script from a queue per script name; logs every run with its timeout.
    def __init__(self, **answers: "list[str | Exception]") -> None:
        self.answers = {name: list(queue) for name, queue in answers.items()}
        self.runs: list[tuple[str, float | None]] = []

    def run_isolated(self, script_path: "str | Path", *, soft_reset_after: bool = True, timeout_s: "float | None" = None, allow_recovery: bool = True, **extras: object) -> str:
        del soft_reset_after, allow_recovery, extras
        name = Path(script_path).stem
        self.runs.append((name, timeout_s))
        answer = self.answers[name].pop(0)
        if isinstance(answer, Exception):
            raise answer
        return answer

    def count(self, script: Path) -> int:
        return sum(1 for name, _ in self.runs if name == script.stem)


_INTERVAL_OK = _facts(interval=_INTERVAL)
_MEASURING = _facts(measuring=True, co2=612.0)
_NOT_MEASURING = _facts(measuring=False, waited_s=3 * _INTERVAL + 2)
_SENT = _facts(ambient=0, sent=True)


def _board(*, interval: "list[str | Exception] | None" = None, wait: "list[str | Exception] | None" = None, start: "list[str | Exception] | None" = None) -> _FakeBoard:
    return _FakeBoard(
        scd30_measurement_interval_read=interval or [_INTERVAL_OK] * 4,
        scd30_data_ready_wait=wait or [],
        scd30_start_continuous_measurement=start or [],
    )


def test_a_measuring_chip_spends_no_write() -> None:
    board, session = _board(wait=[_MEASURING]), scd30_prerequisite.new_session()
    assert scd30_prerequisite.ensure_scd30_measuring(board, session) == "already measuring (no write)"
    assert board.count(scd30_prerequisite.START_SCRIPT) == 0
    assert session.start_sent is False


def test_a_stopped_chip_is_started_once_and_confirmed() -> None:
    board, session = _board(wait=[_NOT_MEASURING, _MEASURING], start=[_SENT]), scd30_prerequisite.new_session()
    assert scd30_prerequisite.ensure_scd30_measuring(board, session) == "started (one NVM write)"
    assert board.count(scd30_prerequisite.START_SCRIPT) == 1
    assert [name for name, _ in board.runs] == ["scd30_measurement_interval_read", "scd30_data_ready_wait", "scd30_start_continuous_measurement", "scd30_data_ready_wait"]


def test_the_wait_scales_with_the_interval() -> None:
    board = _board(wait=[_MEASURING], interval=[_facts(interval=30)])
    scd30_prerequisite.ensure_scd30_measuring(board, scd30_prerequisite.new_session())
    waits = [timeout for name, timeout in board.runs if name == scd30_prerequisite.WAIT_SCRIPT.stem]
    assert waits == [3 * 30 + scd30_prerequisite._WAIT_MARGIN_S], waits


@pytest.mark.parametrize("interval", [[RuntimeError("mpremote failed")], [_facts(error="OSError(5)")], ["no facts at all\n"]], ids=["raises", "no-interval", "no-done"])
def test_a_failed_interval_read_raises_with_no_send(interval: "list[str | Exception]") -> None:
    board, session = _board(interval=interval), scd30_prerequisite.new_session()
    with pytest.raises((HardwareTestFailureError, RuntimeError), match=r"interval|mpremote|DONE"):
        scd30_prerequisite.ensure_scd30_measuring(board, session)
    assert board.count(scd30_prerequisite.START_SCRIPT) == 0
    assert session.start_sent is False


def test_a_wait_that_times_out_raises_with_no_send() -> None:
    board, session = _board(wait=[HardwareTestFailureError("mpremote timed out")]), scd30_prerequisite.new_session()
    with pytest.raises(HardwareTestFailureError, match="timed out"):
        scd30_prerequisite.ensure_scd30_measuring(board, session)
    assert board.count(scd30_prerequisite.START_SCRIPT) == 0


def test_a_start_that_raises_fails_after_one_send_and_is_never_retried() -> None:
    board, session = _board(wait=[_NOT_MEASURING], start=[HardwareTestFailureError("I2C NACK")]), scd30_prerequisite.new_session()
    with pytest.raises(HardwareTestFailureError, match="I2C NACK"):
        scd30_prerequisite.ensure_scd30_measuring(board, session)
    assert board.count(scd30_prerequisite.START_SCRIPT) == 1
    assert session.start_sent is True


def test_an_invalid_read_back_sets_the_guard_sends_nothing_and_fails() -> None:
    board, session = _board(wait=[_NOT_MEASURING], start=[_facts(ambient=65535, sent=False, invalid_readback=65535)]), scd30_prerequisite.new_session()
    with pytest.raises(HardwareTestFailureError, match="invalid ambient read-back 65535"):
        scd30_prerequisite.ensure_scd30_measuring(board, session)
    assert board.count(scd30_prerequisite.START_SCRIPT) == 1
    assert session.start_sent is True


def test_a_start_without_a_measurement_after_it_fails_without_a_resend() -> None:
    board, session = _board(wait=[_NOT_MEASURING, _NOT_MEASURING], start=[_SENT]), scd30_prerequisite.new_session()
    with pytest.raises(HardwareTestFailureError, match="started but no measurement within 3 intervals"):
        scd30_prerequisite.ensure_scd30_measuring(board, session)
    assert board.count(scd30_prerequisite.START_SCRIPT) == 1


def test_a_second_call_after_a_send_never_sends_again() -> None:
    session = scd30_prerequisite.new_session()
    first = _board(wait=[_NOT_MEASURING, _NOT_MEASURING], start=[_SENT])
    with pytest.raises(HardwareTestFailureError):
        scd30_prerequisite.ensure_scd30_measuring(first, session)
    second = _board(wait=[_NOT_MEASURING], start=[_SENT])
    with pytest.raises(HardwareTestFailureError, match="already sent this session"):
        scd30_prerequisite.ensure_scd30_measuring(second, session)
    assert second.count(scd30_prerequisite.START_SCRIPT) == 0


def test_the_flash_fixture_keeps_one_session_for_the_whole_run(repo_root: Path) -> None:
    # The guard lives at module level in flash/conftest.py and nothing resets it: one start per pytest session.
    source = (repo_root / "tests_hardware" / "flash" / "conftest.py").read_text(encoding="utf-8")
    assert "_SESSION = scd30_prerequisite.new_session()" in source
    assert "start_sent" not in source, "the flash conftest must never touch the guard itself"
