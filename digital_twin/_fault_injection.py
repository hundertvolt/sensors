"""Shared fault-injection primitive for every chip fake in this package — an op-name-keyed FIFO of exceptions, mirroring (independently of) `tests/machine.py`'s own `inject_fault()`/`_maybe_raise()` convention.
For chip-protocol-level faults (corrupted CRC, mid-transaction timeout) a bus fake can't express on its own; address-level NAK is handled generically by `machine.py`'s own `I2C` class instead."""

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    pass


class FaultInjector:
    def __init__(self) -> None:
        self._queues: dict[str, list[BaseException]] = {}

    def inject_fault(self, op: str, exc: BaseException, times: int = 1) -> None:
        # Queues `exc` to be raised on the next `times` calls to the named op - lets a test fail
        # one specific step of a multi-step transaction without affecting the others.
        self._queues.setdefault(op, []).extend([exc] * times)

    def maybe_raise(self, op: str) -> None:
        queue = self._queues.get(op)
        if queue:
            raise queue.pop(0)

    def clear(self, op: "str | None" = None) -> None:
        if op is None:
            self._queues.clear()
        else:
            self._queues.pop(op, None)
