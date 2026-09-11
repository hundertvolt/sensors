"""Isolated-driver device script: live-detects this board's actual I2C topology and runs an
address/command sweep, a reserved-address-range sweep, and (for a lone known device on a bus) a
self-hazard broadcast-vs-read check. Keep KNOWN_ADDRESSES in sync with tests_hardware/bus_topology.py."""

import asyncio

import machine

import asy_i2c_driver
from asy_bmp3xx_driver import BMP3XX_I2C
from asy_scd30_driver import SCD30_I2C
from asy_sgp40_driver import SGP40_I2C

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False


KNOWN_ADDRESSES = {0x61: "SCD30", 0x59: "SGP40", 0x77: "BMP3xx"}
GENERAL_CALL_ADDRESS = 0x00
RESERVED_RANGES = ((0x00, 0x07), (0x78, 0x7F))
_OTHER_RESERVED = [a for lo, hi in RESERVED_RANGES for a in range(lo, hi + 1) if a != GENERAL_CALL_ADDRESS]

# This bench's own real pin assignments (sensortask_dev.py's own construction comments) - scanned,
# never assumed populated.
_BUSES = ((0, 13, 12, 50000, None), (1, 15, 14, 50000, 200000))


async def _probe(i2c: "asy_i2c_driver.I2C", address: int) -> "str | None":
    # Mirrors I2CDevice._probe_for_device()'s own zero-length-write probe convention. Returns None
    # on a clean NAK/timeout (the expected, healthy outcome for an absent/reserved address other
    # than the general call), or a description of anything else that happened.
    try:
        i2c.writeto(address, b"")
    except OSError:
        return None  # clean NAK/timeout - exactly what an absent device should produce
    except Exception as e:
        return f"{type(e).__name__}: {e}"
    else:
        return None  # ACKed - either a real device answered, or (0x00 only) the general call always "succeeds"


async def _read_scd30_once(scd: "SCD30_I2C") -> "str | None":
    # No setup()/continuous-measurement dependency - read_measurement() degrades cleanly (cached
    # fields stay None, no exception) if continuous measurement was never triggered on this
    # particular device, which the lone-device self-hazard branch below never assumes either way.
    try:
        await scd.read_measurement()
    except Exception as e:
        return f"{type(e).__name__}: {e}"
    else:
        return None


async def _read_bmp3xx_once(bmp: "BMP3XX_I2C") -> "str | None":
    try:
        pressure, temperature = await bmp.get_pressure_and_temperature()
        if not (300.0 <= pressure <= 1250.0 and -40.0 <= temperature <= 85.0):
            return f"reading outside plausible bounds: Pres={pressure} Temp={temperature}"
    except Exception as e:
        return f"{type(e).__name__}: {e}"
    else:
        return None


async def _read_sgp40_once(sgp: "SGP40_I2C") -> "str | None":
    try:
        raw = await sgp.measure_raw(temperature=25, relative_humidity=50)
        if raw is None:
            return "measure_raw() returned None"
    except Exception as e:
        return f"{type(e).__name__}: {e}"
    else:
        return None


async def _self_hazard_check(i2c: "asy_i2c_driver.I2C", port_id: int, address: int) -> "list[str]":
    """A lone known device on a bus, read repeatedly while general-call broadcasts race those
    reads. A module-level function rather than an inline block so no closure here captures the
    caller's bus-loop variables (ruff B023) - everything it needs is a parameter."""
    name = KNOWN_ADDRESSES[address]
    # Each protocol object is constructed and set up exactly once, outside the read loop - unlike
    # BMP3xx/SGP40, a freshly-constructed object per call would never have run setup() and would
    # crash on its own cached calibration/CRC state (BMP3xx's _temp_calib/_pressure_calib in
    # particular, only populated by setup()).
    read_once = None
    try:
        if address == 0x61:
            scd = SCD30_I2C(i2c, address=address)
            read_once = lambda: _read_scd30_once(scd)  # noqa: E731
        elif address == 0x77:
            bmp = BMP3XX_I2C(i2c, address=address)
            await bmp.setup()
            read_once = lambda: _read_bmp3xx_once(bmp)  # noqa: E731
        elif address == 0x59:
            sgp = SGP40_I2C(i2c, address=address)
            await sgp.setup()
            read_once = lambda: _read_sgp40_once(sgp)  # noqa: E731
    except Exception as e:
        return [f"bus {port_id}: {name} setup() before self-hazard check failed: {type(e).__name__}: {e}"]

    if read_once is None:
        return []
    self_errors: list[str] = []

    async def reads() -> None:
        for i in range(8):
            err = await read_once()
            if err is not None:
                self_errors.append(f"bus {port_id} {name} self-hazard read {i}: {err}")
            await asyncio.sleep(0)

    async def broadcasts() -> None:
        for _ in range(3):
            try:
                i2c.writeto(GENERAL_CALL_ADDRESS, b"\x06")
            except OSError:
                pass
            await asyncio.sleep(0.2)

    await asyncio.wait_for(asyncio.gather(reads(), broadcasts()), 30.0)
    return self_errors


async def _main() -> None:
    wdt = machine.WDT(timeout=8000)
    findings: list[str] = []
    all_discovered: dict[int, dict[int, str]] = {}

    for port_id, scl, sda, freq, timeout in _BUSES:
        i2c = asy_i2c_driver.I2C(port_id, scl, sda, frequency=freq, timeout=timeout)
        scan = i2c.scan() or []
        discovered = {addr: KNOWN_ADDRESSES.get(addr, f"unknown@{hex(addr)}") for addr in scan}
        all_discovered[port_id] = discovered
        wdt.feed()

        # 1. Address sweep: every known address, present or not.
        for addr, known_name in KNOWN_ADDRESSES.items():
            err = await _probe(i2c, addr)
            if err is not None:
                findings.append(f"bus {port_id}: probing known address {hex(addr)} ({known_name}) misbehaved: {err}")
        wdt.feed()

        # 2. Reserved-range sweep (excluding the general call, covered elsewhere in depth).
        for addr in _OTHER_RESERVED:
            err = await _probe(i2c, addr)
            if err is not None:
                findings.append(f"bus {port_id}: probing reserved address {hex(addr)} misbehaved: {err}")
        wdt.feed()

        # 3. Self-hazard for a lone known device.
        known_here = [addr for addr in scan if addr in KNOWN_ADDRESSES]
        if len(known_here) == 1:
            findings.extend(await _self_hazard_check(i2c, port_id, known_here[0]))
        wdt.feed()

    summary = ", ".join(f"bus {b}: {sorted(d.values())}" for b, d in all_discovered.items())
    if findings:
        print(f"RESULT: FAIL {len(findings)} issue(s) (discovered: {summary}): {'; '.join(findings[:10])}")
    else:
        print(f"RESULT: PASS discovered: {summary} - address/reserved-range sweep and self-hazard checks clean")


asyncio.run(_main())
