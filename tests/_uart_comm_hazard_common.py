"""The comm-hazard tier's shared pieces: its pair, reply budgets, CRC modes and the registration running every check
in both, imported by test_uart_comm_hazard.py and test_uart_comm_cancel_sweep.py (SPECIFICATION.md Part J.7)."""

from _uart_comm_harness import Pair, PollRoundClock, accept_set, echo_get, run

from asy_crc_checks import CRC16

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable

    from asy_crc_checks import CRCBase

    # None means "no CRC on the bus"; otherwise a zero-argument factory, called once per end. A factory, not
    # an instance, CRCBase carrying state the two ends must not share. Not type[CRCBase], which would
    # demand a three-argument constructor the concrete widths do not take.
    CrcMaker = Callable[[], CRCBase] | None

# A short timeout keeps each recovery cycle cheap: this tier is about which frames pass validation and what is
# emitted, not about real-world durations, and every value still clears the module's own floor of 2 x
# poll_wait_ms + poll_idle_ms plus the worst-case GC pause - 24ms here, the harness setting poll_idle_ms equal to poll_wait_ms.
# @tunable l1.uart_comm_hazard_timeout_ms = 30
_TIMEOUT_MS = 30
_PAYLOAD = 8

# @tunable l1.uart_comm_hazard_exchange_limit_s = 20
_EXCHANGE_LIMIT_S = 20
# @tunable l1.uart_comm_hazard_step_bound_s = 5
_STEP_BOUND_S = 5
# @tunable l1.uart_comm_hazard_crc_timeout_factor = 8
_CRC_TIMEOUT_FACTOR = 8


# Every check runs both with and without a CRC (agent, 2026-09-12) - the dev wiring selects
# CRCPass, but a CRC changes which corruptions are detectable at all
# (SPECIFICATION.md Part E.8). `crc()` builds a fresh instance per pair: CRCBase carries state.
CRC_MODES = (("nocrc", None), ("crc16", CRC16))


def timeout_for(crc: "CrcMaker") -> int:
    # A CRC yields once per byte, and the peer keeps polling through those yields, so the same budget covers
    # far fewer bytes - measured as transactions timing out at this tier's short 30ms. The real
    # link's 1000ms has ample headroom; this keeps the mock's speed at the same relative margin.
    return _TIMEOUT_MS if crc is None else _TIMEOUT_MS * _CRC_TIMEOUT_FACTOR


def hazard_pair(crc: "CrcMaker" = None, timeout_ms: int | None = None, answer: bytes = b"v") -> Pair:
    maker = (lambda: None) if crc is None else crc
    pair = Pair(
        payload_size=_PAYLOAD, timeout=timeout_for(crc) if timeout_ms is None else timeout_ms,
        get_callback=echo_get(answer), set_callback=accept_set(), crc_a=maker(), crc_b=maker(),
    )
    assert run(pair.setup()) is True
    return pair


def register_both_crc_modes(namespace: "dict[str, object]", mode_specific: "dict[str, str]", own_clock: "tuple[str, ...]") -> None:
    # Registered once per mode, so a failure names the configuration that broke; mode_specific names a check's one
    # mode, own_clock the checks entering the poll-round clock themselves.
    for label, crc in CRC_MODES:
        for name, check in list(namespace.items()):
            if not name.startswith("_check_") or not callable(check):
                continue
            stem = name[len("_check_") :]
            if mode_specific.get(stem, label) != label:
                continue
            namespace[f"test_{stem}_{label}"] = _bind(check, crc, own_clock=stem in own_clock)


def _bind(check: "Callable[[CrcMaker], object]", crc: "CrcMaker", *, own_clock: bool) -> "Callable[[], None]":
    # Every other check runs on the poll-round clock too: on the wall clock one host stall past a reply budget
    # fails a live exchange, so the verdict would depend on host load (SPECIFICATION.md Part J.7).
    def run_one() -> None:
        if own_clock:
            check(crc)
            return
        with PollRoundClock():
            check(crc)

    return run_one
