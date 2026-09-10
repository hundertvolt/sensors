"""Isolated-driver device script: the real SGP40 VOC-state FRAM backup/restore pathway against the
real chip. reader1 runs until its backup schedule fires; a second reader simulates a fresh boot at
the same FRAM address and must restore it. See tests_hardware/README.md's cfgmgr-priming note."""

import asyncio

import machine

import asy_i2c_driver
import asy_spi_driver
from asy_fram_manager import AsyFramManager
from asy_sgp40_driver import SGP40_Reader

BACKUP_WAIT_S = 75.0  # 60s to the first natural BackupPeriod=1min trigger, plus margin
RESTORE_WAIT_S = 10.0
_WDT_FEED_INTERVAL_S = 2.0  # comfortably under the 8.388s hardware ceiling


async def _fixed_comp() -> list[float | None]:
    return [25.0, 50.0]  # datasheet Table 10 compensation defaults


async def _always_synced() -> bool:
    return True  # stands in for the real ntp.ntp_issynced - no NTP subsystem in this isolated script


async def _run_until_cancelled(reader: SGP40_Reader, duration_s: float, wdt: machine.WDT) -> None:
    task = reader.start_asy_read()
    remaining = duration_s
    while remaining > 0:
        await asyncio.sleep(min(_WDT_FEED_INTERVAL_S, remaining))
        wdt.feed()
        remaining -= _WDT_FEED_INTERVAL_S
    task.cancel()
    try:
        await task
    except (asyncio.CancelledError, Exception):
        pass


async def _main() -> None:
    wdt = machine.WDT(timeout=8000)  # matches src/system_service.py's own production value
    i2c1 = asy_i2c_driver.I2C(1, 15, 14, frequency=50000)
    spi0 = asy_spi_driver.SPI(0, 2, 3, 4)

    fram_a = AsyFramManager(spi0, 5, max_size=0x40000, debug=None)
    if not await fram_a.setup():
        print("RESULT: FAIL fram_a.setup() failed - real FRAM chip not responding on spi0/cs5")
        return

    reader1 = SGP40_Reader(i2c1, _fixed_comp, max_module_error=999, fram_storage=fram_a, fram_ntp_callback=_always_synced, debug=None)
    if reader1.ts_storage is None:
        print("RESULT: FAIL reader1.ts_storage allocation failed - no FRAM chunk to back up into")
        return
    # Prime config directly rather than reader1.cfgmgr.setup() - no real flash file I/O, matching
    # dev_legacy/README.md's documented pattern. Defaults straight from asy_sgp40_driver.py's own
    # _VAL_BP/_VAL_BMAX/_VAL_WT (BackupPeriod=1 min is exactly what BACKUP_WAIT_S is sized around).
    reader1.cfgmgr.valid = True
    reader1.cfgmgr._cache = {"BackupPeriod": 1, "BackupMaxAge": 7200, "WaitTimeNTP": 30}
    reader1.start_timer()
    await _run_until_cancelled(reader1, BACKUP_WAIT_S, wdt)
    reader1.stop_timer()

    last_backup, _ = await reader1.get_mem_status()
    if last_backup is None:
        print("RESULT: FAIL reader1 never completed a backup within the wait window - no real write to FRAM observed")
        return

    # Simulate a fresh boot: a brand new AsyFramManager Python object against the same real spi0
    # bus/chip, allocating its own chunk 0 at the same physical address reader1's did - see this
    # script's own module docstring for why this is a faithful reboot simulation.
    fram_b = AsyFramManager(spi0, 5, max_size=0x40000, debug=None)
    if not await fram_b.setup():
        print("RESULT: FAIL fram_b.setup() failed - real FRAM chip not responding on second probe")
        return

    reader2 = SGP40_Reader(i2c1, _fixed_comp, max_module_error=999, fram_storage=fram_b, fram_ntp_callback=_always_synced, debug=None)
    if reader2.ts_storage is None:
        print("RESULT: FAIL reader2.ts_storage allocation failed - no FRAM chunk to restore from")
        return
    # Same priming as reader1 above - _init_sgp() (which sets voc_init, the real restore trigger)
    # reads this same config too, so without it reader2 would never even attempt a restore.
    reader2.cfgmgr.valid = True
    reader2.cfgmgr._cache = {"BackupPeriod": 1, "BackupMaxAge": 7200, "WaitTimeNTP": 30}
    reader2.start_timer()
    await _run_until_cancelled(reader2, RESTORE_WAIT_S, wdt)
    reader2.stop_timer()

    _, restored_from = await reader2.get_mem_status()
    if restored_from is None:
        print(f"RESULT: FAIL reader2 (simulated fresh boot) never reported a restored backup - real FRAM restore did not succeed (reader1's last_backup={last_backup})")
        return

    print(f"RESULT: PASS reader1 last_backup={last_backup} reader2 restored_from={restored_from}")


asyncio.run(_main())
