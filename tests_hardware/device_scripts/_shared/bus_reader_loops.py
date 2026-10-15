"""Included into device scripts at render: the one reader loop every bus-hazard script runs beside its writer - it
feeds the watchdog and yields on every path of every round, the failing one included, and keeps a bounded failure
record (a total and the first few messages) that report_errors() turns into one `errors` fact."""

import asyncio
import time

import machine

# @include _shared/facts.py

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from _mpy_shed.time_mp import _TicksMs
    from bench_facts import BenchFacts

    import asy_i2c_driver
    from _shared.facts import _ERRORS_KEPT, errors
    from asy_bmp3xx_driver import BMP3XX_I2C
    from asy_isl29125_driver import ISL29125_I2C
    from asy_scd30_driver import SCD30_I2C
    from asy_sgp40_driver import SGP40_I2C


class Drivers:
    # The driver classes device_reader() sets up, imported at the top of the script that reads through it: a script
    # including this file without reading through device_reader() imports none of them.
    def __init__(self, scd30: "type[SCD30_I2C]", bmp3xx: "type[BMP3XX_I2C]", sgp40: "type[SGP40_I2C]", isl29125: "type[ISL29125_I2C]") -> None:
        self.scd30 = scd30
        self.bmp3xx = bmp3xx
        self.sgp40 = sgp40
        self.isl29125 = isl29125


class Record:
    # One loop's completed rounds, its failures (counted, the first few kept) and, when asked, each completed round's
    # (start, end) ticks_ms() window for an interleave check.
    def __init__(self, name: str, *, windows: bool = False) -> None:
        self.name = name
        self.reads = 0
        self.total = 0
        self.first: list[str] = []
        self.windows: list[tuple[_TicksMs, _TicksMs]] | None = [] if windows else None

    def fail(self, message: str) -> None:
        self.total += 1
        if len(self.first) < _ERRORS_KEPT:
            self.first.append(f"{self.name}: {message}")


class Seen:
    # What device reads noticed beside their own result: each BMP3XX's power-on flag right after its setup(), and the
    # ISL29125 configuration snapshots that diverged from the driver's shadow.
    def __init__(self) -> None:
        self.por_after_setup: dict[str, bool] = {}
        self.isl_divergences = 0


class Stop:
    # Set by the loop that drives a phase when its own rounds are done; every other loop ends at its next round.
    def __init__(self) -> None:
        self.is_set = False


async def device_reader(bench: "BenchFacts", label: str, i2c: "asy_i2c_driver.I2C", seen: Seen, drivers: Drivers) -> "Callable[[], Awaitable[str | None]] | None":
    # The instance set up through its own driver (setup() checks its identification) and one read of it for read_loop();
    # None for an instance with no reader here.
    driver = bench["instances"][label]["driver"]
    if driver == "scd30":
        scd = drivers.scd30(i2c)
        await scd.setup()

        async def read_scd30() -> "str | None":
            await scd.read_measurement()  # without new data the cache stays as it was: no measurement prerequisite
            return None

        return read_scd30
    if driver == "bmp3xx":
        bmp = drivers.bmp3xx(i2c, bench["addresses"][label])
        await bmp.setup()
        seen.por_after_setup[label] = await bmp.take_por_detected()

        async def read_bmp3xx() -> "str | None":
            await bmp.take_por_detected()
            pressure, temperature = await bmp.get_pressure_and_temperature()
            return outside(bench["bounds"], "pressure_hpa", pressure) or outside(bench["bounds"], "bmp3xx_temp_c", temperature)

        return read_bmp3xx
    if driver == "sgp40":
        sgp = drivers.sgp40(i2c)
        await sgp.setup()

        async def read_sgp40() -> "str | None":
            return None if await sgp.measure_raw(temperature=25, relative_humidity=50) is not None else "measure_raw() returned None"

        return read_sgp40
    if driver == "isl29125":
        isl = drivers.isl29125(i2c)
        await isl.setup()

        async def read_isl29125() -> "str | None":
            problem = await isl29125_counts_problem(isl)
            if not isl.matches_shadow(await isl.get_config_snapshot()):
                seen.isl_divergences += 1
            return problem

        return read_isl29125
    return None


def interleaved(inner: Record, outer: Record) -> "tuple[int, int]":
    # (inner rounds that started and ended inside an outer round's window, outer windows holding at least one); ticks
    # wrap, so every comparison goes through ticks_diff().
    total = 0
    holding = 0
    for outer_start, outer_end in outer.windows or []:
        count = sum(1 for start, end in inner.windows or [] if time.ticks_diff(start, outer_start) >= 0 and time.ticks_diff(outer_end, end) >= 0)
        total += count
        holding += 1 if count else 0
    return total, holding


async def isl29125_counts_problem(isl: "ISL29125_I2C") -> "str | None":
    # One read_counts(): every channel inside 16 bits, else a torn burst.
    counts = await isl.read_counts()
    return None if all(0 <= c <= 0xFFFF for c in counts) else f"counts={counts} outside the 16-bit range - a torn burst"


def outside(bounds: "dict[str, tuple[float, float, str]]", name: str, value: "float | None") -> "str | None":
    # None for a value inside its plausibility bound (BENCH["bounds"], tests_hardware/plausibility_bounds.py) or no value.
    low, high, _source = bounds[name]
    return None if value is None or low <= value <= high else f"{name}={value} outside [{low}, {high}]"


async def read_loop(read: "Callable[[], Awaitable[str | None]]", iterations: "int | None", step_ms: int, wdt: machine.WDT, record: Record, stop: Stop) -> None:
    # Up to `iterations` rounds (None: until `stop`); `read` returns None for a good round or names what was wrong.
    i = 0
    while not stop.is_set and (iterations is None or i < iterations):
        start = time.ticks_ms()
        try:
            problem = await read()
        except Exception as e:  # every failure is recorded and the loop goes on; the host gives the verdict
            problem = f"{type(e).__name__}: {e}"
        if problem is None:
            record.reads += 1
            if record.windows is not None:
                record.windows.append((start, time.ticks_ms()))
        else:
            record.fail(f"round {i}: {problem}")
        i += 1
        wdt.feed()
        await asyncio.sleep_ms(step_ms)


def report_errors(records: "list[Record]") -> None:
    # The run's failures as one `errors` fact: every loop's total, the first few messages across the loops.
    errors("errors", sum(r.total for r in records), [message for r in records for message in r.first])


async def scd30_reading_problem(scd: "SCD30_I2C", bounds: "dict[str, tuple[float, float, str]]") -> "str | None":
    # One read_measurement() and the three cached values against their bounds; a round with no new data checks the last.
    await scd.read_measurement()
    return outside(bounds, "co2_ppm", await scd.get_CO2()) or outside(bounds, "humidity_rh", await scd.get_relative_humidity()) or outside(bounds, "scd30_temp_c", await scd.get_temperature())
