# R3 falsification brief (lead, 2026-11-04)

Your job: try to REFUTE the claims below about `13a833c7` (eight commits on base `17688315`, 26705ef8 through
13a833c7; pre-audit `25caf528`). You get the claims, not the reasoning behind them. A claim stands only if you could
not break it; say how hard you tried. Also look for a lost feature, a weakened product check or a reintroduced real
defect in the changed files (`git diff --stat 17688315 13a833c7 -- ':!arduino'`), and compare each changed test with
its state at `25caf528` where it existed then. Chip and port facts: the pinned MicroPython and pico-sdk under
`/root/pico-toolchain` (say file:line), datasheets at `/home/user/datasheets/` (document, page, table); say where you
took any other fact from.

- Read-only worktree `S/wt-r3f` (detached at `13a833c7`, `node_modules` linked); S =
  `/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad`.
  You may plant a temporary break there to test a claim, then restore it (`git -C S/wt-r3f checkout -- <path>`).
  Never commit, never push, never touch any other worktree.
- `S/u35r/r1/common_r1.md` gives the environment, the run wrapper (`S/u35/lead/run.sh`, labels `r3f_`), the one-file
  test commands and `S/u23/rebuild.sh <worktree>` (run it once before any test file; it counts as a run). Its binding
  rules apply. No whole gate: single test files only (one tests_scripts file counts as one), at most twelve runs in
  all, one after another, never two at once. Never open anything under `/root/.claude/`. Never read `arduino/`
  (`':!arduino'` in every git grep and git log). `tests_hardware` only with `--collect-only` or `--twin`. Keep any
  source copy or extract out of `S/u35r/` except under `S/u35r/r3/f/ftmp/` (never published), and delete that folder
  before you hand back. The legacy tree (`python/`, `modules/`, `legacy/`) is reference-only.

## Claims
1. **Timer pool.** `tests/test_digital_twin_timer_pool.py`'s full soft-callback queue test fails when the product's
   recovery after a lost soft callback is broken (plant one), and it cannot pass on a scheduler queue that never
   fills. The DNS flood runs inside the existing exclusive port-53 hotspot scenario in
   `scripts/_digital_twin_scenarios.py`: no new boot, no timeout changed, and the flood's answers are checked.
2. **Strengthened tests.** Each fails on a planted break of the behaviour it names:
   (a) `test_start_timer_degrades_when_the_alarm_pool_is_exhausted` (ISL29125): the timer armed anyway, a callback
   wired, or an entry logged; (b) the twin's power-cycled BMP3XX test: an entry logged over the power cycle, or the
   chip's OSR/CONFIG left at other than the twin model's reset values; (c) SCD30 ContMeas False with the stop
   command NAKed after the snapshot answers `Failed` with exactly one E CHIP_SET; (d) a runtime I2C `clear()` whose
   SCL reads low lets a sibling task run before it returns its held-SCL status (a synchronous wait fails it).
3. **Restored tests.** `tests_scripts/test_record_twin_instrument_runs.py` reads no committed record and each of its
   five tests fails on a planted break in `scripts/record_twin_instrument_runs.py`'s matching behaviour. The SCD30
   missed-edge twin test fails if the fallback read falls due a tick early or late, or logs an entry.
4. **Removal.** `test_the_lowered_uptime_limit_leaves_the_output_unchanged` pinned only a limit no longer in `src/`;
   no test, doc (outside `audit/`) or config names it, and the two constants removed with it had no other reader.
5. **Hardware tiers.** The new `PERMANENT_SKIPS` entry names an existing test and excuses only that one; the verdict
   still fails on any other skip. `uart_comm_hazards.py` only adds evidence fields: no verdict, recovery or exchange
   changed. `listener_close_leaves_the_pcb_pools.py`: port 30100 is no fixed port elsewhere in the tree and lies
   below the host's ephemeral range; the close-order change alters nothing an rp2 run checks; the port-held check can
   still fail (show a listener close that leaves the port held is caught).
6. **Fidelity rows.** The five new rows in `digital_twin/README.md` match the probe values in `S/u35r/r3/m/probes.md`
   and the twin's actual behaviour (read the twin chip files), and each datasheet citation says what the row says.
7. **src/.** One comment line changed (`src/asy_scd30_driver.py`); every `src/` module's bytecode is identical to
   `17688315`'s (194,883 B in all); the UART wire format is untouched.
8. **Nothing else.** Every change is one of the items above; text outside `audit/` cites no audit IDs or lane and unit
   names; no comment block exceeds 3 lines.
9. **Numbers.** 343 lines added and 53 removed against `17688315`, 14 files (arduino excluded).
10. **R3's records.** `S/u35r/r3/m/twin.md` classes the twin runner's 39 reds as 0 product defects, 31 twin fidelity
    and 8 test; `m/coverage.md` finds no dead line; `m/plants.md` has 2 survivors of 72. Pick the five classings you
    judge most likely wrong and try to show one is a product defect, a dead line or a further survivor.

## Hand-back
Write `S/u35r/r3/FALSIFY.md`, first line "R3 falsification, written by the agent (<date -u>)": per claim STANDS or
REFUTED, with file:line evidence (and the planted break or run label where you used one). Then any defect you found
outside the claims. Your final message: the path, one line per REFUTED claim, last "nothing of mine is running".
