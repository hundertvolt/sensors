"""Isolated-driver device script: three concurrent SGP40_I2C.measure_raw() calls on one instance, each with its own
temperature/humidity, all return an in-range tick (SPECIFICATION.md Part C.8). Silicon proves the serialisation only:
the chip CRC-checks what an overwriting caller also wrote, so the payload each session sends is the mock and twin tiers'."""

import asyncio

import machine

import asy_i2c_driver
from asy_sgp40_driver import SGP40_I2C

# SRAW_VOC's output range, SGP40 datasheet Table 1.
_SRAW_MIN, _SRAW_MAX = 0, 65535
# Three distinct (degC, %RH) inputs inside Table 10's range, the same three the mock and twin tiers send.
_SESSIONS = ((25, 50), (10, 30), (35, 80))
# @tunable l3.sgp40_same_device_concurrent_sessions_run_bound_s = 5.0
_RUN_BOUND_S = 5.0


async def _main() -> None:
    # @tunable wdt.timeout_ms = 8000
    wdt = machine.WDT(timeout=8000)  # matches src/asy_system_service.py's own production value
    i2c1 = asy_i2c_driver.I2C(1, 15, 14, frequency=50000, timeout=200000)
    sgp = SGP40_I2C(i2c1)
    await sgp.setup()
    wdt.feed()

    ticks: list[int | None] = []
    errors: list[str] = []

    async def session(temperature: int, relative_humidity: int) -> None:
        try:
            raw = await sgp.measure_raw(temperature=temperature, relative_humidity=relative_humidity)
        except Exception as e:
            errors.append(f"{temperature} C/{relative_humidity} %: {type(e).__name__}: {e}")
            return
        ticks.append(raw)
        if raw is None or not (_SRAW_MIN <= raw <= _SRAW_MAX):
            errors.append(f"{temperature} C/{relative_humidity} %: tick {raw!r} is not a value in {_SRAW_MIN}..{_SRAW_MAX}")

    async def sessions() -> None:
        await asyncio.gather(*(session(t, rh) for t, rh in _SESSIONS))

    await asyncio.wait_for(sessions(), _RUN_BOUND_S)
    wdt.feed()

    if len(ticks) + len(errors) < len(_SESSIONS):
        errors.append(f"only {len(ticks)} of {len(_SESSIONS)} sessions returned")
    if errors:
        print(f"RESULT: FAIL {len(errors)} issue(s): {'; '.join(errors)}")
    else:
        print(f"RESULT: PASS ticks={ticks} - every concurrent session got its own in-range tick")


asyncio.run(_main())
