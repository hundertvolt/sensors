"""Isolated-driver device script, flash-tier gap fix: the real SGP40 VOC-state FRAM backup/restore
pathway (asy_sgp40_driver.py's SGP40_Reader.ts_storage, an AsyFramTimestampedChunk from
asy_fram_manager.py) against the real MB85RS64V FRAM chip - the "FRAM backup working" gap.

Drives the real production read_loop() end to end, not synthetic internal calls: reader1 runs
until its own natural backup schedule fires (BackupPeriod defaults to 1 minute -> 60 real read
cycles at SGP40's fixed 1s trigger period - see asy_sgp40_driver.py's _check_storage()/_run_backup()),
writing real algorithm state to the real chip. A second AsyFramManager/SGP40_Reader pair (fram_b/
reader2) then simulates a fresh boot: allocated_size starts at 0 again for a *new* AsyFramManager
Python object (exactly what a real reboot's own fresh build_system() call does - CLAUDE.md's own
FRAM-chunk-instantiation-order contract), so reader2's ts_storage chunk lands at the identical real
FRAM byte address reader1's did, without needing an actual board reboot (the real chip's bytes are
untouched by a plain object-level "restart" either way). reader2's own SGPWaitTimeNTP-driven
voc_init (default 30, set in _init_sgp()) triggers a real deserialize attempt on its very first
read cycle, matching real first-boot behavior.

fram_ntp_callback is a fixed stub always reporting synced=True (this script has no real NTP
subsystem running) - exercises the real timestamped-backup path deterministically rather than
depending on this script's own wall-clock coincidentally landing after some real NTP sync.

Run via `mpremote run <this> soft-reset`. Takes ~90s (60s to the first natural backup trigger, plus
restore-cycle margin)."""

import asyncio

import asy_i2c_driver
import asy_spi_driver
from asy_fram_manager import AsyFramManager
from asy_sgp40_driver import SGP40_Reader

BACKUP_WAIT_S = 75.0  # 60s to the first natural BackupPeriod=1min trigger, plus margin
RESTORE_WAIT_S = 10.0


async def _fixed_comp() -> list[float | None]:
    return [25.0, 50.0]  # datasheet Table 10 compensation defaults


async def _always_synced() -> bool:
    return True  # stands in for the real ntp.ntp_issynced - no NTP subsystem in this isolated script


async def _run_until_cancelled(reader: SGP40_Reader, duration_s: float) -> None:
    task = reader.start_asy_read()
    await asyncio.sleep(duration_s)
    task.cancel()
    try:
        await task
    except Exception:  # noqa: BLE001 - CancelledError or whatever the loop itself raised
        pass


async def _main() -> None:
    i2c1 = asy_i2c_driver.I2C(1, 19, 18, frequency=50000)
    spi0 = asy_spi_driver.SPI(0, 2, 3, 4)

    fram_a = AsyFramManager(spi0, 1, max_size=0x2000, debug=None)
    if not await fram_a.setup():
        print("RESULT: FAIL fram_a.setup() failed - real FRAM chip not responding on spi0/cs1")
        return

    reader1 = SGP40_Reader(i2c1, _fixed_comp, max_module_error=999, fram_storage=fram_a, fram_ntp_callback=_always_synced, debug=None)
    if reader1.ts_storage is None:
        print("RESULT: FAIL reader1.ts_storage allocation failed - no FRAM chunk to back up into")
        return
    reader1.start_timer()
    await _run_until_cancelled(reader1, BACKUP_WAIT_S)
    reader1.stop_timer()

    last_backup, _ = await reader1.get_mem_status()
    if last_backup is None:
        print("RESULT: FAIL reader1 never completed a backup within the wait window - no real write to FRAM observed")
        return

    # Simulate a fresh boot: a brand new AsyFramManager Python object against the same real spi0
    # bus/chip, allocating its own chunk 0 at the same physical address reader1's did - see this
    # script's own module docstring for why this is a faithful reboot simulation.
    fram_b = AsyFramManager(spi0, 1, max_size=0x2000, debug=None)
    if not await fram_b.setup():
        print("RESULT: FAIL fram_b.setup() failed - real FRAM chip not responding on second probe")
        return

    reader2 = SGP40_Reader(i2c1, _fixed_comp, max_module_error=999, fram_storage=fram_b, fram_ntp_callback=_always_synced, debug=None)
    if reader2.ts_storage is None:
        print("RESULT: FAIL reader2.ts_storage allocation failed - no FRAM chunk to restore from")
        return
    reader2.start_timer()
    await _run_until_cancelled(reader2, RESTORE_WAIT_S)
    reader2.stop_timer()

    _, restored_from = await reader2.get_mem_status()
    if restored_from is None:
        print(f"RESULT: FAIL reader2 (simulated fresh boot) never reported a restored backup - real FRAM restore did not succeed (reader1's last_backup={last_backup})")
        return

    print(f"RESULT: PASS reader1 last_backup={last_backup} reader2 restored_from={restored_from}")


asyncio.run(_main())
