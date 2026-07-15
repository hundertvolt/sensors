"""Test-only stand-in for improved-quality/base_classes.py's Lockable. asy_i2c_driver.py depends
on it, but base_classes.py itself hasn't cleared the src/ promotion checklist yet (see
CLAUDE.md) - improved-quality/ isn't on the test MICROPYPATH, so this tracks Lockable's current
real behavior just closely enough to exercise I2CDevice's locking. Must be reconciled or removed
once base_classes.py is itself promoted to src/ (see BACKLOG.md).
"""

import asyncio


class Lockable:
    def __init__(self, asy_lock: asyncio.Lock | None = None) -> None:
        self.asy_lock = asyncio.Lock() if asy_lock is None else asy_lock

    async def __aenter__(self) -> "Lockable":
        await self.asy_lock.acquire()
        return self

    async def __aexit__(self, exc_type: object, exc_val: object, exc_tb: object) -> bool:
        try:
            self.asy_lock.release()
        except RuntimeError:  # in case it's already released somehow
            pass
        return False
