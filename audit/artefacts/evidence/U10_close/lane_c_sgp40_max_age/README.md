# Lane C's SGP40 backup max-age test failure

Before the session limit of 2026-10-07 (03:31 UTC) lane C's run of `tests/test_asy_sgp40_driver.py`
failed one test, 118/119: `test_fram_restore_rejects_backup_older_than_backup_max_age`.

Root cause: U10 moves the FRAM backup timestamp from `asy_fram_manager`'s own `mktime()` to
`asy_base_classes.utc_now()`, which answers `None` until the clock is valid. The test's `_OldTime`
patch replaced `asy_fram_manager.time`, which the timestamp no longer reads, and the clock flag was
unset, so the backup carried no age to reject. Firmware behaviour is as specified; the test now patches
`asy_base_classes.time` under a valid clock (lane C, U10), 120/120 since. The failing output itself was
not kept by the lane; this record is its account, from the lane's report and transcript.
