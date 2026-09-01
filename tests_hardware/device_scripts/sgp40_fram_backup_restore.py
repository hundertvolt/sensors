"""Isolated-driver device script, flash-tier gap fix: the real SGP40 VOC-state FRAM backup/restore
pathway (asy_sgp40_driver.py's SGP40_Reader.ts_storage, an AsyFramTimestampedChunk from
asy_fram_manager.py) against the real MB85RS2MTA FRAM chip this bench unit carries (CS=GPIO5, not
the deployed wozi unit's MB85RS64V at CS=GPIO1) and the real SGP40 on I2C1 GPIO15/14 (not GPIO19/18
- dev_legacy/README.md's own wiring table, confirmed directly against this bench's live main.py and
real i2c.scan()/RDID probes) - the "FRAM backup working" gap.

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

REAL FINDING, fixed: an earlier draft never initialized reader1.cfgmgr/reader2.cfgmgr at all - no
setup() call, no primed cache. _check_storage()'s very first step is `await self.cfgmgr.
get_int_values(...)`, which returns None whenever `cfgmgr.valid` is False (confirmed directly:
real hardware printed "SGP40 Error reading config data!" every single cycle and the backup counter
never even started incrementing, since that early-return happens before the counter logic runs) -
so a backup could never fire regardless of how long the script waited; the original ~90s timeout
guess was never actually the problem. Fixed per dev_legacy/README.md's own documented pattern for
diagnostic scripts that must not write to the RP2040's own real flash: prime `cfgmgr.valid = True`
and `cfgmgr._cache = {...}` directly with the schema's own defaults, instead of calling
`cfgmgr.setup()` (which would do a real littlefs file write/read).

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
    except (asyncio.CancelledError, Exception):  # noqa: BLE001 - CancelledError (real hardware confirmed: MicroPython's, like CPython's, subclasses BaseException, not Exception - SPECIFICATION.md Part F.2) or whatever the loop itself raised
        pass


async def _main() -> None:
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
    await _run_until_cancelled(reader1, BACKUP_WAIT_S)
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
    await _run_until_cancelled(reader2, RESTORE_WAIT_S)
    reader2.stop_timer()

    _, restored_from = await reader2.get_mem_status()
    if restored_from is None:
        print(f"RESULT: FAIL reader2 (simulated fresh boot) never reported a restored backup - real FRAM restore did not succeed (reader1's last_backup={last_backup})")
        return

    print(f"RESULT: PASS reader1 last_backup={last_backup} reader2 restored_from={restored_from}")


asyncio.run(_main())
