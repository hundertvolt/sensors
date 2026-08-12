"""Shared fault-injection primitive for every chip fake in this package (_sgp40_chip.py/
_scd30_chip.py/_bmp3xx_chip.py/_fram_chip.py) - an op-name-keyed FIFO of exceptions, mirroring
tests/machine.py's own I2C.inject_fault()/_maybe_raise() convention exactly (same shape, kept as an
independent reimplementation like every other file in this package - see FINAL_WIRING_PLAN.md's
Step 3 section for why the whole package avoids importing tests/machine.py).

Address-level NAK (an unknown/unwired I2C address) is handled once, generically, by
digital_twin/machine.py's own I2C class - this class is for the *chip-protocol-level* faults a bus
fake can't express on its own (a corrupted CRC byte, a timeout mid-transaction, an occasional NAK
from an otherwise-present device), matching tests/_fram_chip_fake.py's own chip-level knobs.
"""

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
