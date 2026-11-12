# R2 brief, phase B: the changes (lead, 2026-11-04, after 11:27 UTC; time not taken)

The owner has seen the list (`S/u35r/r2/LIST.md`) and answered its questions; their words are in the rulings file
(2026-11-04 11:23 and 11:27). Phase A's rules stay (common_r1.md, labels `r2_`), except that you now edit, commit and
run. Worktree `S/wt-r2`, branch `audit/r2`, from 8a32d826. A few commits are fine (PLAN 2 step 6), each with its tests.
Hand-back: a new file, `S/u35r/r2/HANDBACK.md`, first line "R2 hand-back, written by the agent (<date -u>)".

## The work (the list's rows, as decided)
1. **Removals**: A1-A3 (A2 after confirming ruff TC004 fires on a planted runtime-evaluated TYPE_CHECKING name); the
   48 self-bite functions of appendix S (OR21.a (2)); one port lock instead of three, O-lock-1..5; W1-W5 (the 89 s
   retirement gives way to the idle event, the launcher stop file goes); N-knob-1..5 (twin knobs read only by their
   own tests; `silent` re-read first). The rig override is records only: nothing in code.
2. **The seven fixed sleeps** (section 3.1) wait for their condition (OR37.a (3)).
3. **CI**: C1 option (b) (the harness part runs only the exclusive-port-53 scenarios, inside the suite job; 6 x 2 = 12
   twin jobs; both stages and the per-device rule kept). Timeouts from measured need with the stated margin where a CI
   record gives the need (R0's run and the snapshot runs since); a value whose need rests on an unmeasured host (the
   bench Pi4's scenario time) keeps its value and says "measure on the bench" in its Part N row. Both retries stay; the
   hang backstop as CLAUDE.md states it.
4. **Part N** (owner, 2026-11-04 11:23: "the tunables' main target is firmware. Buildgen may also be included. But
   generally, it's option a with it"): the narrow reading of section 5.1: about 197 rows stay (firmware, build, the 12
   hardware-tier budgets and soak durations, the in-scope L0-L2 rows, CI, runners, the 4 rule rows); the 1,081 others
   and their 1,127 `@tunable` lines go (the literal stays); `test_tunables_register.py` follows. The heap-floor row and
   `mem.max_await_depth` as section 5.3 says (one host run for the await depth). A throwaway edit script under
   `S/u35r/r2/ftmp/` is fine; it is never committed and is deleted before the hand-back.
5. **The loop end** (owner, 2026-11-04 11:27: "option c"): the generated boot entry calls `machine.reset()` right after
   `record_loop_end()`, so rp2's REPL never starts. Test first: `tests/test_generated_boot_entry.py`'s stub records the
   reset call (seen red, then green). Facts to cite: `ports/rp2/modmachine.c:74-79` (`watchdog_reboot(0, SRAM_END, 0)`),
   the pico-sdk's `watchdog_reboot()` touching only `scratch[4]` for pc 0, SPEC F.5.4 (mem_backup survives
   `machine.reset()`), so the next boot reads 22; the firmware's `_reboot()` already resets through `system_reset`.
   SPEC A.7 and F.5.4's loop-end sentences follow. The Ctrl-C arm and the no-autostart entry stay as they are.
6. **Carries** (section 6): `_UART_BUFFER_MAX`'s line numbers corrected; `SETTINGS_GROUPS`/`_owns_config_store()` with
   no reader go, unless a reader exists; `HardConsumer.what`/`.relief` as section 6 says. P-sleep: no change (lead,
   2026-11-04: its subject already holds; narrowing it would add code).

## Bounds
- Complexity (owner, 2026-11-04 06:11): nothing grows; a change that would add a mechanism goes to the lead first.
  Report net lines per directory against 8a32d826.
- Budget: R2's share is 5 % of the week for both phases; this is the larger half: one gate, at most one fix round.
- The host is yours; one run at a time. Gate once on the finished change: the two `scripts/test.sh` stages, dev's
  twin suite and harness at both stages (the harness part as C1 leaves it), npm lint, typecheck and test:unit.
- Report: test and tool lines removed per directory, CI's jobs before and after, SPECIFICATION.md's size before and
  after, the gate's lines. Final message: the path, your commits, one line per headline result, last "nothing of mine
  is running".
