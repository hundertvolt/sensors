# R2 falsification brief (lead, 2026-11-04)

Your job: try to REFUTE the claims below about `433d53b2` (ten commits on base `8a32d826`, f6593d6a through 433d53b2;
pre-audit `25caf528`). You get the claims, not the reasoning behind them. A claim stands only if you could not break
it; say how hard you tried. Also look for a lost feature, a weakened product check or a reintroduced real defect in
the changed files (`git diff --stat 8a32d826 433d53b2 -- ':!arduino'`: tests, tooling, CI, the register, the boot
entry). Chip and port facts: the pinned MicroPython and pico-sdk under `/root/pico-toolchain` (say file:line); say
where you took any other fact from.

- Read-only worktree `S/wt-r2f` (detached at `433d53b2`, `node_modules` linked); S =
  `/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad`.
  You may plant a temporary break there to test a claim, then restore it (`git -C S/wt-r2f checkout -- <path>`).
  Never commit, never push, never touch any other worktree.
- `S/u35r/r1/common_r1.md` gives the environment, the run wrapper (`S/u35/lead/run.sh`, labels `r2f_`), the one-file
  test commands and `S/u23/rebuild.sh <worktree>` (run it once before any test file; it counts as a run). Its binding
  rules apply. No whole gate: single test files only (one tests_scripts or tests_js file counts as one), at most ten
  runs in all, one after another, never two at once. Never open anything under `/root/.claude/`. Never read
  `arduino/` (`':!arduino'` in every git grep and git log). `tests_hardware` only with `--collect-only` or `--twin`.
  Keep any source copy or extract out of `S/u35r/` except under `S/u35r/r2/f/ftmp/` (never published), and delete
  that folder before you hand back. The legacy tree (`python/`, `modules/`, `legacy/`) is reference-only.

## Claims
1. **Loop end.** Each of the six generated boot entries calls `reset()` right after `record_loop_end()` in the arm for
   any other exception, and nowhere else; the Ctrl-C arm and the no-autostart entry are as at `8a32d826`. On rp2,
   `machine.reset()` leaves the reset record intact, so the next boot's `ResetReason` reads 22 (check the port's
   `machine.reset()`, the SDK's `watchdog_reboot()` and which watchdog scratch registers `src/`'s reset record uses).
   Nothing prints after a loop end at any DebugLevel. `tests/test_reset_call_site_invariant.py` still fails on any
   other reset site (plant one). No hardware-tier test, device script or doc still expects a REPL or a soft reset
   after a loop end.
2. **Removals.** A1-A3 (`tests_scripts/test_hardware_clones.py`, `test_host_annotations.py`,
   `test_host_text_encoding.py`), the 48 self-bite functions, the twin and fake knobs (`_bmp3xx_chip.py`'s
   `fatal_err`, `_scd30_chip.py`'s `rdy_stuck_high`, the twin pixel's `power_dip()`/`displayed()`,
   `_fram_chip_fake.py`'s `silent`), the shared twin's 89 s retirement and the launcher stop file: nothing left reads
   any of them (code, tests, docs, CI, npm and lint configs); every product test is kept; each check that lost its
   self-bite test still runs its real case. The idle check's `_own_backup` excuses only the boot's own untimestamped
   SGP40 backup, never a movement a scenario causes or states (try to construct one it wrongly excuses).
3. **The seven sleeps.** Each formerly fixed sleep now waits for its stated condition with a bound; none can pass
   without that condition (plant one that never comes true: the test must fail within its bound). The one-turn waits
   (`sleep_ms(0)`, then assert) are decided by the asyncio run queue's order, not by timing. `_PROBE_LEAD_MS = 5` is
   the one fixed lead left.
4. **CI.** `ci.yml`'s twin job is 6 devices x 2 GC stages = 12 jobs, 46 jobs in all before and 34 after. Every twin
   scenario that ran at `8a32d826` for a device and stage still runs for it, exactly once across `unit-tests`,
   `unit-tests-gc-threshold` and the twin job (the shared-port ones in `scripts/test.sh`, the exclusive-port-53 ones
   in the twin job). No `timeout-minutes` changed; the twin job's 20 minutes covers its merged leg with the margin its
   row states. Both `uv sync` retries, `needs:` with `!cancelled()`, the per-file timeout and retry and `stdbuf` are
   intact; actionlint and zizmor stay clean.
5. **Part N.** 192 rows remain (188 ID rows, 4 rule rows), every row for a `src/` or `buildgen/` value present at
   `8a32d826` among them; each removed row was a single test's own wait, poll, timeout or count, or one of the five
   rule rows whose content stays in J.6 and F.3 (the owner's narrow reading, 2026-11-04 11:23, rulings file). Every
   literal is unchanged except `mem.max_await_depth` 28 to 25. `tests_scripts/test_tunables_register.py` still fails
   on a register/tag mismatch (plant one). The seven `# source:` comments use the product-copy check's existing
   exemption, and a real copy of a product value cannot now pass that check by carrying such a comment where it could
   not before.
6. **Await depth.** 25 is the measured maximum, the measure is a static walk (not timing), and the check fails at 26.
7. **Carries.** `HardConsumer.what`/`.relief` had no reader; `SETTINGS_GROUPS` and `_owns_config_store()` have
   readers; the settings test checks every emitted page; the UART buffer citations match the pinned
   `ports/rp2/machine_uart.c`.
8. **Nothing else changed.** `src/` changes are comment lines only (the UART wire format is untouched); every test
   change is the mechanical consequence of the items above; text outside `audit/` cites no audit IDs or lane and unit
   names; no comment block exceeds 3 lines; only `BACKLOG.md` and `README.md` grew, by one line each.
9. **Numbers.** 332 lines added and 3,745 removed against `8a32d826` (arduino excluded); `SPECIFICATION.md`
   1,589,923 B / 13,230 lines to 1,128,895 B / 12,143 lines.

## Hand-back
Write `S/u35r/r2/FALSIFY.md`, first line "R2 falsification, written by the agent (<date -u>)": per claim STANDS or
REFUTED, with file:line evidence (and the planted break or run label where you used one). Then any defect you found
outside the claims. Your final message: the path, one line per REFUTED claim, last "nothing of mine is running".
