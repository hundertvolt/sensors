"""Twin-only test knob shared by every chip fake: an op-keyed FIFO of bounded faults (fresh exceptions,
optionally aimed at one command key) and of blocking hangs. A hang is a real time.sleep(), not asyncio.sleep(): an rp2
bus call has no await point, so a wedged peripheral freezes the whole interpreter (SPECIFICATION.md F.2)."""

import time


class FaultInjector:
    TEST_API = ("inject_fault", "maybe_raise", "inject_hang", "maybe_hang", "clear", "pending")

    def __init__(self, raisable_ops: "tuple[str, ...] | None" = None) -> None:
        # raisable_ops: the ops the chip's real bus can raise on (None: every op), so a fault rp2 cannot produce is refused.
        self._raisable_ops = raisable_ops
        self._queues: dict[str, list[tuple[type[BaseException], tuple[object, ...], int | None]]] = {}
        self._hangs: dict[str, list[float]] = {}

    def clear(self, op: "str | None" = None) -> None:
        # Empties both queues for one op, or every op.
        if op is None:
            self._queues.clear()
            self._hangs.clear()
        else:
            self._queues.pop(op, None)
            self._hangs.pop(op, None)

    def inject_fault(self, op: str, exc_type: "type[BaseException]", *args: object, times: int = 1, match: "int | None" = None) -> None:
        # The next `times` calls to `op` whose key `match` names (None: any key) raise exc_type(*args), oldest first.
        # The key is the command word of a word protocol, the register of a *_mem transfer, the opcode of an SPI one.
        if times < 1:
            raise ValueError("times must be at least 1")
        if self._raisable_ops is not None and op not in self._raisable_ops:
            raise ValueError(f"{op!r} cannot raise on this bus (rp2) - see digital_twin/README.md's fidelity table")
        self._queues.setdefault(op, []).extend([(exc_type, args, match)] * times)

    def inject_hang(self, op: str, seconds: float, times: int = 1) -> None:
        # A real blocking time.sleep() before the next `times` calls to `op` (the header says why); a delay, not an
        # exception, so it has its own queue and the call still completes.
        if times < 1:
            raise ValueError("times must be at least 1")
        self._hangs.setdefault(op, []).extend([seconds] * times)

    def maybe_hang(self, op: str) -> None:
        queue = self._hangs.get(op)
        if queue:
            time.sleep(queue.pop(0))

    def maybe_raise(self, op: str, key: "int | None" = None) -> None:
        # The oldest queued fault whose match accepts `key` raises, a fresh exception each time; the rest stay queued.
        queue = self._queues.get(op)
        if queue:
            for i, (exc_type, args, match) in enumerate(queue):
                if match is None or match == key:
                    del queue[i]
                    raise exc_type(*args)

    def pending(self, op: str) -> int:
        # The faults still queued for `op` (0 for none): lets a test prove a fault was consumed before it reads on.
        return len(self._queues.get(op, ()))
