"""Isolated-driver device script: the real SGP40 VOC-state FRAM backup/restore pathway on the real parts. reader1 runs
until its backup schedule fires; a second reader simulates a fresh boot at the same FRAM address and restores it
(tests_hardware/README.md's cfgmgr-priming note). The VOC-state chunk is cleared first and on the way out."""

import asyncio

import asy_i2c_driver
import asy_spi_driver
from asy_base_classes import ValueRef, set_utc_valid
from asy_fram_manager import FRAMManager
from asy_print_log import DEFAULT_LOG, LogConfig
from asy_sgp40_driver import SGP40_Reader, SgpBackup

# @include _shared/facts.py
# @include _shared/fixed_source.py
# @include _shared/watchdog.py

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython
    TYPE_CHECKING = False

if TYPE_CHECKING:
    import machine
    from _shared.facts import done, fact
    from _shared.fixed_source import FixedSource
    from _shared.watchdog import arm, fed_sleep_ms
    from bench_facts import BenchFacts

    from asy_spi_driver import SPI

BENCH: "BenchFacts" = {}  # rendered by tests_hardware/harness.py

# @tunable l3.sgp40_fram_backup_restore_backup_wait_s = 75.0
_BACKUP_WAIT_S = 75.0  # 60 s to the first natural BackupPeriod=1min trigger, plus margin
# @tunable l3.sgp40_fram_backup_restore_restore_wait_s = 10.0
_RESTORE_WAIT_S = 10.0
_POLL_MS = 1000  # one read cycle of the reader's own 1 s trigger


async def _always_synced() -> bool:
    return True  # stands in for the real ntp.ntp_issynced - no NTP subsystem in this isolated script


async def _main() -> None:
    wdt = arm()
    # The NTP client's other half: the clock it sets is marked valid, so a dated backup is written (utc_now() stays None
    # until then, and a backup waiting for NTP never lands); the RTC keeps whatever time it holds.
    set_utc_valid()
    sensor = next(instance for instance in BENCH["instances"].values() if instance["driver"] == "sgp40")
    i2c_bus = BENCH["bus"][sensor["bus"]]
    i2c = asy_i2c_driver.I2C(i2c_bus["id"], i2c_bus["scl_pin"], i2c_bus["sda_pin"], frequency=i2c_bus["frequency"], timeout=i2c_bus.get("timeout"))
    chip = next(instance for instance in BENCH["instances"].values() if instance["driver"] == "fram")
    spi_bus = BENCH["bus"][chip["bus"]]
    spi: SPI = asy_spi_driver.SPI(spi_bus["id"], sck_pin=spi_bus["sck_pin"], mosi_pin=spi_bus["mosi_pin"], miso_pin=spi_bus["miso_pin"])
    fram_a = FRAMManager(spi, chip["cs_pin"], BENCH["fram_max_size"])
    fact("setup", await fram_a.setup())
    reader1 = _reader(i2c, fram_a)
    fact("allocated", reader1._ts_storage is not None)
    if reader1._ts_storage is None:
        done()
        return
    fact("cleared_first", await reader1._ts_storage.clear())
    # A fresh boot: a new FRAMManager over the same part allocates its chunks at the addresses reader1's took. Its
    # loggers are never set up, so they write nothing; the VOC-state chunk is the one this run writes.
    fram_b = FRAMManager(spi, chip["cs_pin"], BENCH["fram_max_size"])
    fact("rebooted_setup", await fram_b.setup())
    reader2 = _reader(i2c, fram_b)
    try:
        last_backup = await _run_until(reader1, wdt, _BACKUP_WAIT_S, 0)
        fact("backup_written", last_backup is not None)
        if last_backup is not None:
            restored_from = await _run_until(reader2, wdt, _RESTORE_WAIT_S, 1)
            fact("restored_from", restored_from)
            fact("restored_state_matches", restored_from == last_backup)
    finally:
        fact("cleared_last", reader2._ts_storage is not None and await reader2._ts_storage.clear())
    done()


def _reader(i2c: "asy_i2c_driver.I2C", fram: FRAMManager) -> SGP40_Reader:
    reader = SGP40_Reader(
        i2c,
        ValueRef(FixedSource(25.0), "value"),
        ValueRef(FixedSource(50.0), "value"),
        backup=SgpBackup(fram, _always_synced),
        max_module_error=999,
        log=LogConfig(fram, DEFAULT_LOG.history_length, None),
    )
    # Primed in RAM from the driver's own schema rather than cfgmgr.setup(): no flash file I/O. Its BackupPeriod default
    # of 1 min is what _BACKUP_WAIT_S is sized around, and _init_sgp() reads it to start a restore.
    reader.cfgmgr.valid = True
    reader.cfgmgr._cache = {field[0]: field[2] for field in reader.get_cfg_schema() if field[2] is not None}
    return reader


async def _run_until(reader: SGP40_Reader, wdt: "machine.WDT", deadline_s: float, slot: int) -> "int | None":
    # Runs the read task until get_mem_status()[slot] is set or the deadline passes, fed in steps; the task is cancelled.
    task = reader.start_asy_read()
    reader.start_timer()
    waited_ms = 0
    try:
        while (await reader.get_mem_status())[slot] is None and waited_ms < deadline_s * 1000:
            await fed_sleep_ms(wdt, _POLL_MS)
            waited_ms += _POLL_MS
    finally:
        reader.stop_timer()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass  # the cancel above; a read task that died on its own re-raises here and fails the run
    return (await reader.get_mem_status())[slot]


asyncio.run(_main())
