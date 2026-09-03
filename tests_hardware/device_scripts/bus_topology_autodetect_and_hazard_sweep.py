"""Isolated-driver device script, flash-tier: live-detects this real board's actual I2C topology
(never assumes it - a real bench's wiring can drift from any declared registry) and, driven purely
by what it actually finds, runs the "closest possible simulation" hazard checks the project owner
asked for when a real second device isn't physically present to prove interference against:

1. **Address/command sweep** - every known device address (KNOWN_ADDRESSES below, mirroring
   tests_hardware/bus_topology.py's own KNOWN_ADDRESSES - keep the two in sync) is probed directly
   on every bus, whether or not it was actually discovered there by scan() - proving the real bus
   master (asy_i2c_driver.I2C/the RP2040 hardware I2C peripheral) handles an address for a
   *declared-but-physically-absent* device with a clean NAK/OSError, never a hang. This is exactly
   "the bus master starting a transaction with a device using its address although the device is
   not present" the project owner asked for.
2. **Reserved-range sweep** - every I2C-spec-reserved address (0x00-0x07, 0x78-0x7F) is probed on
   every bus too, confirming the bus master survives addressing them cleanly (general call 0x00
   included - already covered in depth by sgp40_general_call_reset_hazard.py; this sweep's own job
   is the *other* seven reserved addresses, which nothing else in this tier ever touches).
3. **Self-hazard, single-device-bus case** - for any bus where scan() finds exactly one KNOWN
   device (this bench's real i2c0/BMP3xx-alone case today), that device's own real reads run
   concurrently with a rogue general-call broadcast loop issued directly by this script (not by any
   real SGP40 - there may be none on this bus) - "issuing rogue broadcasts mid-transaction" even
   with no second real device to observe corruption in: the device under test observing its *own*
   read survive is the proof. Real-hardware counterpart of tests/test_bus_hazard_multi_device.py's
   own test_general_call_absent_sibling_bmp3xx_alone_on_the_bus_survives_a_broadcast_too.

**Auto-detection, not hardcoded assumptions**: this script never assumes which bus has which
device - it scans first, classifies what it finds, and adapts. Add a new device to
KNOWN_ADDRESSES/_read_once_handlers below when a new bus-facing driver is promoted to src/ (see
tests_hardware/bus_topology.py's own "Standing rule") - everything else here already generalizes.

SCD30 NVM-write budget: this script only ever *reads* SCD30 (never a setter) - see
scd30_same_device_rw_concurrency.py's own docstring for the one write this whole test group makes.

Run via `mpremote run <this> soft-reset`."""

import asyncio

import machine

import asy_i2c_driver
from asy_bmp3xx_driver import BMP3XX_I2C
from asy_scd30_driver import SCD30_I2C
from asy_sgp40_driver import SGP40_I2C

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
        return None  # ACKed - either a real device answered, or (0x00 only) the general call always "succeeds"
    except OSError:
        return None  # clean NAK/timeout - exactly what an absent device should produce
    except Exception as e:  # noqa: BLE001 - anything else is the real finding this probe exists to catch
        return f"{type(e).__name__}: {e}"


async def _read_scd30_once(scd: "SCD30_I2C") -> "str | None":
    # No setup()/continuous-measurement dependency - read_measurement() degrades cleanly (cached
    # fields stay None, no exception) if continuous measurement was never triggered on this
    # particular device, which the lone-device self-hazard branch below never assumes either way.
    try:
        await scd.read_measurement()
        return None
    except Exception as e:  # noqa: BLE001
        return f"{type(e).__name__}: {e}"


async def _read_bmp3xx_once(bmp: "BMP3XX_I2C") -> "str | None":
    try:
        pressure, temperature = await bmp.get_pressure_and_temperature()
        if not (300.0 <= pressure <= 1250.0 and -40.0 <= temperature <= 85.0):
            return f"reading outside plausible bounds: Pres={pressure} Temp={temperature}"
        return None
    except Exception as e:  # noqa: BLE001
        return f"{type(e).__name__}: {e}"


async def _read_sgp40_once(sgp: "SGP40_I2C") -> "str | None":
    try:
        raw = await sgp.measure_raw(temperature=25, relative_humidity=50)
        if raw is None:
            return "measure_raw() returned None"
        return None
    except Exception as e:  # noqa: BLE001
        return f"{type(e).__name__}: {e}"


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
        for addr in KNOWN_ADDRESSES:
            err = await _probe(i2c, addr)
            if err is not None:
                findings.append(f"bus {port_id}: probing known address {hex(addr)} ({KNOWN_ADDRESSES[addr]}) misbehaved: {err}")
        wdt.feed()

        # 2. Reserved-range sweep (excluding the general call, covered elsewhere in depth).
        for addr in _OTHER_RESERVED:
            err = await _probe(i2c, addr)
            if err is not None:
                findings.append(f"bus {port_id}: probing reserved address {hex(addr)} misbehaved: {err}")
        wdt.feed()

        # 3. Self-hazard for a lone known device. Each protocol object is constructed and set up
        # exactly once, outside the read loop - unlike BMP3xx/SGP40, a freshly-constructed object
        # per call would never have run setup() and would crash on its own cached calibration/CRC
        # state (BMP3xx's _temp_calib/_pressure_calib in particular, only populated by setup()).
        known_here = [addr for addr in scan if addr in KNOWN_ADDRESSES]
        if len(known_here) == 1:
            addr = known_here[0]
            name = KNOWN_ADDRESSES[addr]
            read_once = None
            try:
                if addr == 0x61:
                    scd = SCD30_I2C(i2c, address=addr)
                    read_once = lambda: _read_scd30_once(scd)  # noqa: E731
                elif addr == 0x77:
                    bmp = BMP3XX_I2C(i2c, address=addr)
                    await bmp.setup()
                    read_once = lambda: _read_bmp3xx_once(bmp)  # noqa: E731
                elif addr == 0x59:
                    sgp = SGP40_I2C(i2c, address=addr)
                    await sgp.setup()
                    read_once = lambda: _read_sgp40_once(sgp)  # noqa: E731
            except Exception as e:  # noqa: BLE001 - setup() failing here is itself worth surfacing, not silently skipping the self-hazard check
                findings.append(f"bus {port_id}: {name} setup() before self-hazard check failed: {type(e).__name__}: {e}")

            if read_once is not None:
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
                findings.extend(self_errors)
        wdt.feed()

    summary = ", ".join(f"bus {b}: {sorted(d.values())}" for b, d in all_discovered.items())
    if findings:
        print(f"RESULT: FAIL {len(findings)} issue(s) (discovered: {summary}): {'; '.join(findings[:10])}")
    else:
        print(f"RESULT: PASS discovered: {summary} - address/reserved-range sweep and self-hazard checks clean")


asyncio.run(_main())
