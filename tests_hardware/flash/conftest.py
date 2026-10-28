"""Flash-tier fixtures: the SCD30 continuous-measurement prerequisite. The start command is NVM-persisted, so it is sent
only when no measurement arrives within three intervals, and at most once per pytest session (owner, 2026-09-29; NVM
never written more than once per session, owner, 2026-09-16). Every flash run ends on a serving board."""

from typing import TYPE_CHECKING, Protocol

import pytest
import scd30_prerequisite
from harness import wait_for_boot, wait_until

if TYPE_CHECKING:
    from collections.abc import Iterator

    from harness import Board


class _SessionNote(Protocol):
    # The root conftest's session_note fixture: record_session_note() bound to this session.
    def __call__(self, text: str, *, recovery: bool = False, source: str) -> None: ...


_SESSION = scd30_prerequisite.new_session()

# @tunable l3.flash_leave_serving_present_timeout_s = 15.0
_PRESENT_TIMEOUT_S = 15.0
# @tunable l3.flash_leave_serving_boot_timeout_s = 30.0
_BOOT_TIMEOUT_S = 30.0


@pytest.fixture(scope="session")
def scd30_measuring(board: "Board", session_note: _SessionNote) -> str:
    # Unmarked and ungated: normally it writes nothing, and its one possible write is a pinned prerequisite.
    note = scd30_prerequisite.ensure_scd30_measuring(board, _SESSION)
    session_note(note, source="scd30_measuring")
    return note


@pytest.fixture(scope="session", autouse=True)
def leave_board_serving(board: "Board", request: pytest.FixtureRequest) -> "Iterator[None]":
    # A device script leaves main.py stopped (an exec ends it), so the run ends with one hard reset and a passive
    # wait for the boot line; a board that does not come back fails the teardown, which the verdict counts.
    yield
    if request.config.getoption("--twin"):
        return
    board.hard_reset()
    wait_until(board.is_device_present, timeout_s=_PRESENT_TIMEOUT_S, description="board back on USB after the flash run's final hard reset")
    wait_for_boot(board, _BOOT_TIMEOUT_S)
