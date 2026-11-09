"""held_logger(): a set-up FRAM-backed logger whose chunk writes wait until the test sets its gate; until(): whether a
condition holds within a bound in rounds, so an entry awaited under a lock shows as the lock still held, never as a
wall-clock wait; written(): until the loggers' written-behind entries are on the chip."""

import asyncio

from asy_base_classes import RegionBuffer
from asy_print_log import PrintLogHistory, PrintLogHistoryStore

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable

ROUNDS = 64  # far above any path's own awaits, and a held entry never ends without its gate


class _HeldChunk:
    def __init__(self, size: int) -> None:
        self.size = size
        self.gate = asyncio.Event()
        self.writes = 0

    def get_buffer(self) -> RegionBuffer:
        return RegionBuffer(self.size, data_start=0, data_length=self.size)

    async def read_into(self, buf: RegionBuffer) -> bool | None:
        return False

    async def write_into(self, buf: RegionBuffer) -> bool:
        await self.gate.wait()
        self.writes += 1
        return True


class _HeldManager:
    def __init__(self) -> None:
        self.chunk: _HeldChunk | None = None

    # Parameter names kept exact for the structural _FramManager/_FramChunk Protocol match (asy_print_log.py).
    def get_chunk(self, size: int, crc: object = None, verify: int = 0, *, owner: str) -> _HeldChunk:
        self.chunk = _HeldChunk(size)
        return self.chunk

    def get_pause(self) -> bool:
        return False


def held_logger(name: str) -> "tuple[PrintLogHistoryStore, asyncio.Event]":
    manager = _HeldManager()
    store = PrintLogHistoryStore(manager, 10, None, name=name)
    store.initialized = True  # as after setup(): every entry is due for a chunk write
    assert manager.chunk is not None
    return store, manager.chunk.gate


async def until(condition: "Callable[[], bool]", rounds: int = ROUNDS) -> bool:
    for _ in range(rounds):
        if condition():
            return True
        await asyncio.sleep(0)
    return condition()


async def written(*loggers: PrintLogHistory) -> bool:
    return await until(lambda: not any(isinstance(lg, PrintLogHistoryStore) and lg._writer is not None for lg in loggers))
