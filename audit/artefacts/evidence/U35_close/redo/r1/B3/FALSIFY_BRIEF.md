# B3 falsification brief (lead, 2026-11-03)

Your job: try to REFUTE the claims below about commit `cc5daeb7` (base `90691b6d`, pre-audit `25caf528`). You get the
claims, not the reasoning behind them. A claim stands only if you could not break it; say how hard you tried. Also look
for a lost feature or a reintroduced real defect in these files against the pre-audit code: `asy_fram_driver.py`,
`asy_fram_manager.py`, `asy_crc_checks.py` (pre-audit `crc_checks.py`), `asy_spi_driver.py`'s bus half, the erase
preflight and the auto-unpause in `asy_system_service.py`, and `buildgen/error_catalog.json`. Datasheets for the FRAM
chips are in `datasheets/` when the submodule is present; say so if one you need is missing.

- Read-only worktree `S/wt-b3f` (detached at `cc5daeb7`); S =
  `/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad`.
  You may plant a temporary break there to test a claim, then restore it (`git -C S/wt-b3f checkout -- <path>`).
  Never commit, never push, never touch any other worktree.
- `S/u35r/r1/common_r1.md` gives the environment, the run wrapper (`S/u35/lead/run.sh`, labels `b3f_`), the one-file
  test commands and `S/u23/rebuild.sh <worktree>` (run it once before any test file; it counts as a run). Its binding
  rules apply. No whole gate: single test files only, at most ten runs in all, one at a time; if the lead says another
  unit holds the host, every run waits for the lead's message (it does now: hold every run until it comes).
  Never open anything under `/root/.claude/`. Never read
  `arduino/` (`':!arduino'` in every git grep and git log). `tests_hardware` only with `--collect-only` or `--twin`.
- The legacy tree (`python/`, `modules/`, `legacy/`) is reference-only: read it, never run or change it.

## Claims
1. Nothing detects an FRAM chip lost after boot (no status-register fixed-zero check, no ID probe, no `lost` event, no
   `is_ready()`, no E54); a lost chip's writes fail with the latch warnings and the chunk entries and resume once it
   answers, with no task ending. `verify_present()` stays a library entry in its pre-audit form (bounded lock wait, E19,
   `initialized = False` on a mismatch) and no product path calls it.
2. A chunk read that finds the region blank answers "blank" (or "not read" on a fault) without probing the chip; a
   blank read beside a bus session held past 1,000 ms stays blank, sends no RDID and logs nothing. The chip watch keeps
   its escalation and otherwise waits.
3. `erase_ready()` is true exactly when the manager is initialized and the chip is not write-protected; the erase
   preflight in `asy_system_service.py` has no exception catch and no re-check, and the erase gate still refuses an
   uninitialized or write-protected FRAM.
4. With the SPI bus dropped, an FRAM operation raises `configure()`'s `RuntimeError`, the chunk layer logs E23 and
   `FRAMManager.setup()` E10, as at `25caf528`; `SPI.available` and E52 are gone.
5. The FRAM bus runs at 8 MHz, inside both chips' datasheet clock limits; the wire trace's init event and every text
   naming the FRAM clock or the erase unit's duration agree with it.
6. A chunk read copies its data with one `bytearray(...)`; a missing buffer logs no ALLOC entry (the method still
   answers "not read"); a missing check buffer reads as an invalid block 1, which logs W63 and is rewritten, with no
   ALLOC entry.
7. The write-protect state is "all protect bits set", as at `25caf528`, with no E53; `setup()` and
   `set_write_protected()` take the bus lock only, and no other FRAM operation can interleave with either.
8. `FRAM_SPI.setup()` and `FRAMManager.setup()` answer `None`, and no product caller reads either.
9. CRC: the width fields (`length()` included) behave as at `25caf528`; `add_into()` and `check_from()` keep
   `90691b6d`'s pass-mode bounds (a zero, negative or overrunning size is refused in pass mode too); every CRC vector
   the tests carry gives the same result; no width and polynomial the product constructs answers differently.
10. A failed allocation of the erase unit's buffer still ends in the orderly code-9 reboot.
11. Nothing emits, decodes or expects E52, E53 or E54; E19, E20, W29, E49 and W63 stay in the catalog.
12. The auto-unpause order and the boot signature's flag order in `asy_system_service.py` are those before `a4f0ccea`
    and `8cf55c6b`, and nothing there can raise at the points those commits guarded.
13. FRAM-backed error histories still survive a reboot (twin Run 13's superset check); the four-tier bus-hazard
    coverage (mock, twin, flash and bench files named in CLAUDE.md) still covers the FRAM, and the mock and twin tiers
    pass.
14. No product check got weaker: every test change is the mechanical consequence of an item above. Look hardest at the
    wire-trace golden, the twin FRAM tests changed to the pre-audit outcome, `tests/test_readiness_gates.py`, the
    removed hardware-tier fault-injection scenario, every removed test, and the twin CI suite's Run 3 (it skips a link
    responder's wait for an E entry, and allows one write attempt per "PrintLog: FRAM setup failed!" line).
15. Numbers: `src/` bytecode 196,591 B at `cc5daeb7` (-1,652 B against `90691b6d`'s 198,243 B), no module grew; dev's
    `imageFreeBytes` 56,684 B. Also: the CRC16-derived Run 3 boots with its console off, so its setup-write allowance
    counts 0 lines and it passes on its window alone (24 allowed, 20 seen, at 7.7 s); say whether that can fail.

## Hand-back
Write `S/u35r/r1/B3/FALSIFY.md`, first line "B3 falsification, written by the agent (<date -u>)": per claim STANDS or
REFUTED, with file:line evidence (and the planted break or run label where you used one). Then any defect you found
outside the claims. Your final message: the path, one line per REFUTED claim, last "nothing of mine is running".
