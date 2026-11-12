# B4 falsification brief (lead, 2026-11-03)

Your job: try to REFUTE the claims below about commit `963d0de1` (base `3129bf21`, pre-audit `25caf528`). You get the
claims, not the reasoning behind them. A claim stands only if you could not break it; say how hard you tried. Also look
for a lost feature or a reintroduced real defect in these files against the pre-audit code: `asy_i2c_driver.py`,
`asy_spi_driver.py`, `asy_bmp3xx_driver.py`, `asy_scd30_driver.py`, `asy_sgp40_driver.py`, `voc_algorithm.py`,
`asy_isl29125_driver.py`, the reader parts of `asy_base_classes.py`, and `buildgen/error_catalog.json`. Datasheets for
these chips are in `datasheets/` when the submodule is present; say so if one you need is missing.

- Read-only worktree `S/wt-b4f` (detached at `963d0de1`); S = `/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad`.
  You may plant a temporary break there to test a claim, then restore it (`git -C S/wt-b4f checkout -- <path>`).
  Never commit, never push, never touch any other worktree.
- `S/u35r/r1/common_r1.md` gives the environment, the run wrapper (`S/u35/lead/run.sh`, labels `b4f_`), the one-file
  test commands and `S/u23/rebuild.sh <worktree>` (run it once before any test file). Its binding rules apply. No whole
  gate: single test files only, at most ten runs in all. Never open anything under `/root/.claude/`. Never read
  `arduino/` (`':!arduino'` in every git grep and git log). `tests_hardware` only with `--collect-only` or `--twin`.
- The legacy tree (`python/`, `modules/`) is reference-only: read it, never run or change it.

## Claims
1. With no bus, every I2C and SPI getter answers `None` and every other call answers nothing, `configure()` raises its
   `RuntimeError`, and `recover()` is a bus clear plus `init()`, exactly as at `25caf528`; no driver raises of its own
   for a missing bus remain, and every driver still survives a missing bus as it did at `25caf528`.
2. The I2C bus clear is one routine (9 clock pulses, then STOP), used by the boot clear, `clear()` and `recover()`; a
   slave holding SDA low is still freed (the twin's held-line tests).
3. An I2C write sends address and payload in one `writeto()`; a short ACK count raises `OSError(EIO)`; a short write
   without stop still sends its STOP; `_point_at()` stays.
4. BMP3XX reads as at `25caf528`: forced mode, the STATUS poll, the 6-byte burst from 0x04. Nothing detects a chip
   power-on or emits W71; a range rejection logs E11 "Read failed:" (no E27 at the BMP3XX); E27 stays at the SCD30.
5. SCD30 emits no W73; its read path otherwise matches the base.
6. ISL29125 compares its config shadow only after a counted failed write (`_verify_after_failed_write()`), and that
   re-read stays silent; the calibration end prints its console line (no W75); the ISL-2, ISL-8 and ISL-12 mechanisms
   are gone while W32 and the `_int_held` reset stay.
7. SGP40: a task restart restores the backup (VOCState then reads 3 for 24 h); every chunk read that is not valid,
   blank included, logs one W65; no sample-age check remains; while waiting for NTP the chunk is read each cycle, then
   restored silently; a failed restore buffer keeps its pending restore.
8. `voc_algorithm.py` gives the same outputs as `25caf528`'s port for the same input sequence, and its stored state
   packs and unpacks byte-identically; VOCState 2 reads "settled" on the website and in the catalog.
9. A refused reader timer arm in any of the four drivers logs one line, and nothing else breaks.
10. BMP3XX and ISL29125 GETs still send the chip-config unavailable marker.
11. Nothing emits, decodes or expects W71, W73 or W75; E27 stays in the catalog.
12. `setup()` and `deinit()` of these classes answer `None` and no product caller reads them; the readiness check's
    new exemption covers only the I2C and SPI `deinit()` no-ops.
13. The four-tier bus-hazard coverage (mock, twin, flash and bench files named in CLAUDE.md) still covers every
    bus-facing device, and the mock and twin tiers pass.
14. No product check got weaker: every test change is the mechanical consequence of an item above. Look hardest at the
    scenario harness and CI-suite changes that expect a fresh FRAM's first-boot SGP40 W65 (Run 1), the readiness
    check's exemption, and every removed test (tests lost about 2,000 lines).
15. Numbers: `src/` bytecode about 201,265 B at `963d0de1` (-4,416 B against `3129bf21`); only
    `asy_spi_driver.py` grows (+53 B); dev's `imageFreeBytes` 51,356 B.

## Hand-back
Write `S/u35r/r1/B4/FALSIFY.md`, first line "B4 falsification, written by the agent (<date -u>)": per claim STANDS or
REFUTED, with file:line evidence (and the planted break or run label where you used one). Then any defect you found
outside the claims. Your final message: the path, one line per REFUTED claim, last "nothing of mine is running".
