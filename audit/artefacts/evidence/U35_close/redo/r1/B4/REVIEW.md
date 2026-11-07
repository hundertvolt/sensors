# B4 review (lead, 2026-11-03)

Every hunk of `src/` and `buildgen/` in `3129bf21..963d0de1` read against `ACTION_LIST.md` (`review_hunks.py`: 64
hunks, none proven mechanically, all read; `review_hunks.out`). Every hunk maps to an item: 1 (no-bus contract), 2 (one
bus clear: the boot path drives the async routine with one `send(None)`, which never suspends there), 3 (short-ACK
path), 4 (allocation reductions), 5-7 (BMP3XX), 8 (SCD30), 9, 10, 19 (ISL29125), 11-14 (SGP40), 15, 16 (VOC), 17
(settled), 18 (timer trio), 21 (setup and `deinit()` to None, typing-side forms, `_comp_unreadable`, `_frc_cfg_ok`'s
guard, the 2 ms settle, the heater-off wait), 22 (catalog). Only `asy_spi_driver.py` grows (+53 B, the pre-audit
`configure()` text: admitted). The FRAM driver reads no SPI return value (it checks `spi.available`), so item 1 leaves
it working until B3.

Decisions on the points the hand-back named (agent, 2026-11-03):
- **The W65 harness changes stay:** they follow item 13 (a fresh FRAM's blank chunk logs W65, as at `25caf528`); Run
  1 had passed only by a race before them.
- **SGP-14's pending restore stays:** row 4 keeps it if its test reproduces a lost backup on the pre-audit code, and the
  probe does (`b4_probe_sgp14`: without it the restore reads "no backup" and the next backup overwrites the state).
- **No separate GC -1 rerun:** the merge gate runs every tier at both stages on the merged head.
- **ISL-8's tick clamp goes as listed:** the stale dwell tick needs 6.2 days on the high range with no switch
  (C.md), which a night ends.
- **R2 carries** the twin chip knobs with no driver reader (`fatal_err`, the EVENT model, `rdy_stuck_high`) and the
  bench tests that may meet the restored W65; **B3 carries** the FRAM E19 (`LOCK_TIMEOUT`) seen twice in the first
  scenario run beside the then-unwaited boot W65 write: lock contention under host load, gone once the harness waited;
  B3 checks the lock timeout covers a boot W65 beside a burst.
