"""tests_hardware/harness.py's transient-failure classifier: which mpremote stderr signatures are
worth a retry plus a USB unbind/rebind rather than being reported as a test failure. Locks in the
two real bench signatures that used to slip past it (SPECIFICATION.md Part I.6's matrix run)."""

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tests_hardware"))

from harness import is_transient_mpremote_failure  # noqa: E402

# The two verbatim tracebacks a USB-wedged bench board really produced, trimmed to their last line.
# Neither contains any of mpremote's own "could not ..." wording, which is exactly why they went
# unrecognised and failed four tests at setup instead of triggering the existing recovery.
_REAL_IN_WAITING_WEDGE = """Traceback (most recent call last):
  File ".../mpremote/transport_serial.py", line 158, in read_until
    if self.is_pty or self.serial.inWaiting() > 0:
  File ".../serial/serialposix.py", line 549, in in_waiting
OSError: [Errno 5] Input/output error
"""
_REAL_RTS_CLOSE_WEDGE = """Traceback (most recent call last):
  File ".../mpremote/transport_serial.py", line 125, in close
    self.serial.rts = False
  File ".../serial/serialposix.py", line 708, in _update_rts_state
    fcntl.ioctl(self.fd, TIOCMBIC, TIOCM_RTS_str)
OSError: [Errno 5] Input/output error
"""


@pytest.mark.parametrize(
    "stderr",
    [
        _REAL_IN_WAITING_WEDGE,
        _REAL_RTS_CLOSE_WEDGE,
        "mpremote: failed to access /dev/ttyACM0 (it may be in use by another program)",
        "could not enter raw repl",
        "could not open /dev/ttyACM0",
    ],
)
def test_known_connection_level_failures_are_classified_transient(stderr: str) -> None:
    assert is_transient_mpremote_failure(stderr)


def test_classification_is_case_insensitive() -> None:
    assert is_transient_mpremote_failure("OSError: [ERRNO 5] INPUT/OUTPUT ERROR")


@pytest.mark.parametrize(
    "stderr",
    [
        "",
        "AssertionError: RESULT: FAIL the link dropped 3 transfers",
        "MemoryError: memory allocation failed, allocating 4096 bytes",
        "OSError: [Errno 2] ENOENT",
        "ImportError: no module named 'asy_uart_comm'",
    ],
)
def test_real_device_side_failures_are_never_masked_as_transient(stderr: str) -> None:
    # The whole point of a marker list rather than a blanket retry: a genuine device-side failure
    # must surface as a failure, not get retried until it looks intermittent.
    assert not is_transient_mpremote_failure(stderr)
