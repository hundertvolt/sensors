# R2 fix round (lead, 2026-11-04 14:16 UTC)

The falsification is `S/u35r/r2/FALSIFY.md`; the lead's verdicts are `S/u35r/r2/ACTION_LIST.md` item 4. This is R2's
one fix round after it. Same worktree `S/wt-r2`, branch `audit/r2`, on top of `433d53b2`; the same rules (common_r1.md,
labels `r2x_`); nothing grows beyond what each fix needs; a fix that needs a new mechanism stops and goes to the lead.

## Fixes
- **F1, the loop end's soft-reset path.** SPEC F.5.4 (about 7006-7010): a Ctrl-D at the REPL now follows only the
  Ctrl-C arm and reports its 21; a loop end resets the chip itself, so its 22, or the 10 + p of a loop that ended
  during boot, is read after that forced reset (check A.7 says the same). `tests/test_asy_system_service.py`: the
  first soft-reset test (about 3666) keeps only the 21 case; the boot-phase one (about 3700) goes if another test
  already reads 10 + p after a forced or watchdog reset, else it becomes that case. Say which.
- **F2, the idle check.** `_own_backup` excuses an SGP40 move only when the count moved by exactly one (a missing
  count before reads 0). Show the falsifier's planted case (FALSIFY.md, `r2f_ownbackup`) caught after the fix.
- **F3, captive DNS.** The waits in `tests/test_asy_captive_dns.py` wait on `server._udps.connected`, not
  `_sock is not None`. Show the held-port plant (`r2f_dns_bind`) failing within the bound after the fix.
- **F4, the BMP3xx twin's EVENT register.** Restore it as at `8a32d826` (por_detected after power-up and soft reset,
  clear-on-read), without the `fatal_err` knob. Show the twin side of the conformance comparison reading
  `C03_por_after_softreset` 1 again (the falsifier's `r2f_bmp_twin_head`/`_old` runs show how).
- **F5, the bench loop-end test** (`tests_hardware/bench/test_reset_reasons.py`, about 222-240). Make it independent of
  the old watchdog delay: read `run_isolated_expect_reset()` first; drop the `raised_in_phase` assertion if the 22
  already proves the loop ended after BOOT_DONE (cite why), and drop or fix the drop-off wait so an immediate reset
  cannot slip past it. `--collect-only` only; it is owed to round 1's first bench run, say so in the hand-back.
- **F6, stale text.** `src/asy_system_service.py:94`; `tests_scripts/test_device_script_watchdog.py:20`; codes 11-15's
  text (SPEC about 1036-1040 and `buildgen/error_catalog.json`) where the entry's own reset now applies; the
  docstrings announcing removed bite tests (`test_timing_budget.py:3`, `test_error_catalog.py:3, :760, :798`,
  `test_fram_chunk_owner_sites.py:181`); the await-depth row's Basis cites the 2026-11-04 measurement on this tree,
  not `fde57f45`.

## Gate, once, on the finished fix
Lint and the six mypy passes; both `scripts/test.sh` stages; dev's twin suite and harness at both stages. npm only if
a JS file changed. Append to `S/u35r/r2/HANDBACK.md` a section "## Fix round" (first line with `date -u`): per fix what
changed and its evidence, the commits, the gate's lines, net lines per directory against `8a32d826`. Final message:
the commits, one line per fix, last "nothing of mine is running".
