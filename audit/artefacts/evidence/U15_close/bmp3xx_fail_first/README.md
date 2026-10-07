# BMP3XX onto the shared base (U15, lane A)

What failed: `tests/test_asy_bmp3xx_driver.py` on the previous driver, `bmp_before.txt`: 90/134, the 44 failing tests
listed in `bmp_before_fails.txt` (among them the chip-reset re-apply, the failed re-apply failing the cycle, the
ERR_REG `fatal_err` read, the range code, the domain warning and the failed timer arm).

Why: the driver never read EVENT or ERR_REG, so a chip self-reset silently reverted its settings, and a failed
trigger arm was a console line only.

Fix: commit `2d67e51` (with the base API of `2abd7e9`/`1507a10`): EVENT read every cycle, W71 and the stored
configuration re-applied under the setter lock, the 8-byte burst from ERR_REG, E27 and W11.

What proves it: `bmp_after.txt`, 134/134 on lane A's tree; the merged lane tree's runs are in `../lane_a_runs/`
(134/134 at both GC stages, zero memory-error lines).
