# LEAD NOTES 119-148 (recovered by the lead, 2026-10-26)
LEAD NOTES 1-118 are in S/u35/lane_plan.md (restored from the 656fc82 snapshot; 118 is gate 2 at 7851668, "W7 B2
starts on 7851668"). 119-143 are lost as text; what survives is the lead's compaction summary of 2026-10-23 (facts
below, marked "summary"). 144-148 are verbatim (written in the lead's context after the summary).

## Integration history after 7851668 (summary; all of it lost)
7851668 (= 656fc82's tree) -> 09b15a7 (B2, fast-forward) -> 33d9ad8 (N4) -> 024390d (N5) -> 0f9f07d (CE through
8f504a4); audit/u35-t4 took int as c3d1ce6; then 0a0476a (CE3), c674288 (CF1b), 58a2b3c (T4: T4a + T4a2), d7e51cc (F1),
b2f72dd (T4b2); the CR merge (CR..CR4) was tested green and not yet committed when the session stopped.
Branches not merged: audit/u35-rec at befa1aa (REC1's records), audit/u35-cm at d24e225 (CM), audit/u35-cr (pending
commit), and the stopped F2, F3, CM2.

## 119-132 (summary only)
- 122-123: N4's root cause: on arzi the string case leaves NTPHost at a name nothing in the twin's namespace resolves,
  so the unsynced client retries and logs E73 by itself; the ResetErrors probe turned the backups off but not this.
- 127: a "Findings routed (a)" paragraph followed it (N4's hotspot-exit guess, routed; F1 later disproved it).
- 130: the owner's device-selection decision (recovered/owner_rulings_after_LN118.md) and its facts: N5's brief.
- 133-141 were written without reading the clock and corrected afterwards to 05:34, 05:38, 05:49, 06:06, 06:16, 06:42,
  06:44, 06:47, 06:57 UTC (2026-10-23). Among them: 138, the lead's ruling on tests/_sensortask_scenarios.py:861 (the
  first boot after a reflash is the owner's own case, "handled gracefully (CRC mismatch → treated as empty and
  re-initialised, no crash, no error flood — OR35)" (owner, 2026-09-26, OR47.a (2)); the row is "justified (owner
  decision)", no product route), later confirmed by the owner's FRAM-reflash words of 2026-10-23.
- 142 (07:10): the owner's answers of 2026-10-23, verbatim with the questions (recovered/owner_rulings_after_LN118.md).
- 143 (07:08): "the open firmware-affecting rows routed past U35 land in U35 (agent, 2026-10-23), in two blocks" F1 and
  F2 (recovered/briefs/blocks_f.md); "F1 and F2 start at the next free slots, before CR4, T4b and D3." Stay with
  hardware evidence: OF-40, 60, 70, 90, 119, 184; decided earlier: OF-145, OF-146; doc or typing only: OF-44, OF-237.

## 144 (2026-10-23 07:25 UTC)
CE3 done (d255632, hand-back S/u35/handbacks/CE3_final.md): of e51.md's 35 owed rows, 30 got a direct test, each red
on a plant of its lines first (64 plants); 5 re-classed unreachable with proofs (uart_driver :564-565, :620-621,
:672-673; scd30:735; system_service:441), their removal moved into F1 item 3 under the owner's library rule. No product
file changed. Merged into int as 0a0476a. F1 started on 0a0476a (wt-u35f1). Left for CR4: CHECKLIST 16's silent-failure
scan over CE3's 9 test files (CE3's valve). Left for W10: test_asy_uart_link_driver's time (3.6 s against a base row of
1.72 s taken before CE2's tests), measured like for like.

## 145 (2026-10-23 07:42 UTC)
CF1b done (99fc7d3, hand-back S/u35/handbacks/CF1b_final.md): the owner-scoped plant pass (owner, 2026-10-23, LEAD
NOTES 142, Question 2). 226 rows: 118 planted (96 biting, 12 fixed with a direct test, 5 equivalent, 5 open), 108 not
planted as straightforward logic, 0 routed product findings. Merged into int as c674288; the 7 merged test files pass
at -1 and 32768 with 0 memory markers, ruff clean. Two of CF1b's open rows rest on a misreading, settled by the lead
from the records: named.pair_scan's scan is not absent but renamed and narrowed (M.TSC.111,
test_fault_or_warning_never_both.py), and named.fram_two_entries' requirement A.U3.04 is dropped by OR140.a (7)
(FOLD_BRIEF F11). F2 started on c674288 (wt-u35f2), with CF1b's notification:230 survivor added to its item 2. CF1c
written (blocks_c.md) for the rest. Queue: CR4, CF1c, T4b (after T4a2), then D3.

## 146 (2026-10-23 07:50 UTC)
T4a2 done (e1f6c5f, 2d0d34b; hand-back S/u35/handbacks/T4a2_final.md). The Run 13 red is root-caused in the twin, not
the product: the twin FRAM chip's writes_at dict rehashed (19,568 contiguous bytes, py/map.c:131-148) inside the
product's erase on a -1 heap whose largest free block was 8.4 KB; the shutdown catch-all ended the sequence, nothing
fed, and the twin's watchdog only records, so the process hung to wait_exit's SIGKILL and the next boot read a power-on
(ResetReason 1). Reproduced 9 in 50 on c3d1ce6, 0 in 30 after the fix (the table sized for its 2048-key cap at
construction, its test red first at both stages). T4b item 4 (:507 through untraced()) landed; item 3 left with its
plan. T4 merged into int as 58a2b3c (the twin files at both stages and 853 tests_scripts readers green).
The finding T4a2 raised is the gates' own: a caught MemoryError logged through a level-gated PrintLog method at the
default DebugLevel 0 prints nothing, so it reaches none of the four memory gates (CLAUDE.md's memory rule: "caught-and-
logged included"). Decision (agent, 2026-10-23): extend the existing console() rule (G.2, C.7, I.4(e); the webserver's
MemoryError bypass of 2026-10-08) to every logger, so a MemoryError argument prints its text once ungated, whatever the
level; no entry, code, count, REST field or wire byte changes, an OSError stays gated. Conservative and reversible (one
place in asy_print_log.py), and it closes the gap on silicon too. Block F3 (blocks_f.md) lands it test first, then runs
both GC stages and the dev and wozi twin CI to surface whatever it had hidden, each root-caused.

## 147 (2026-10-23 07:55 UTC)
F1 done (9cc8c96; S/u35/handbacks/F1_final.md), merged into int as d7e51cc (the 6 touched test files green at -1 and
32768, 0 markers). Landed: the flat GET's unavailable marker read by its whole shape (OF-142); SensorReader's logger=
restored with its test under the owner's library rule (it was removed in 8d44fd1); sgp40 _exchange()'s reply bound
removed as dead (private, callers pass 1 and 3, 9-byte buffer); 7 narrowing comments (bytecode unchanged). The
hotspot-exit window cannot occur (proof in the commit, guard test bitten by a planted yield). Kept as features: CE's
direct-test-only isl29125 lines, webserver :425 and :903; kept as guards: uart's three `if not want:` branches (the
never-block rule) and scd30:735. system:441 is reachable by a cancel, against CE3: its test goes to CF1c. First boot:
nothing is keyed on being the first boot; each one-time behaviour has its evidence. F1's one hand-back, the boot after
a commanded config reset logging no W CONFIG_LOST: decided (a) keep it (agent, 2026-10-23, the conservative option,
logged): the suppression is keyed on the reset record, which is evidence, as the owner's rule asks (owner, 2026-10-23:
"If things happen at first boot, they must be triggered by evidence"), and option (b) would add one W69 per commanded
reset whose text ("reformatted or wiped") misdescribes it. Not an owner question: no behaviour changes.
CM done (d24e225; S/u35/handbacks/CM_final.md): the owner's all-devices rule applied to the integration file's
driver-specific scenarios, network_neopixel, neopixel_wifi, fram_less_boot and the scenarios' lag run, green on all 6
devices at both stages; the rest rewritten, run, reverted on three per-device defects in the tests, now CM2's. The
integration file's sum grew 165 → 303 s per stage (a boot per scenario): CM2 shares the boot. A red in int found by CM:
test_twin_wiring_contract's scanner reads N5's _board_plan comprehension as an I2C key (a false positive); CM2 item 1.
The pairs (211 pairs, 145 gaps, a 12-fixture cover) and items 2-3 of A.U35.08/09 are not started beyond pairs.py:
"about six" was the lead's valve, not an owner bound (OR41.a asks all-pairs); they go to a CM3 block after CM2, with the
boots made cheap, not dropped. T4b2 and CM2 launched on d7e51cc.

## 148 (2026-10-23, about 08:10 UTC)
T4b2 done (0d466b6; S/u35/handbacks/T4b2_final.md), merged into int as b2f72dd (the integration test file 44/44 at both
stages). The smoke boot's presence-only check is now exact: the run ends at WifiService.setup()'s return, the WIFI
store's layer holds one E CFG_PATH_IS_DIR and one printed line, a planted second err_s turns it red (decision: end at
setup's return, not BOOT_TASKS; agent, 2026-10-23, T4b2's: +55 % file time otherwise, same entry, and CFG_NOT_VALID's
timing after BOOT_TASKS is not deterministic). The runner's `boot phase:` line named the first boot's device in a
multi-boot process: fixed, test first. Fold (1) meets its case only by luck on a host whose send buffer grows to 4 MiB:
decided (agent, 2026-10-23) a scenario-scoped SO_SNDBUF floor knob, off by default, the twin-wide question left to the
records. T4b item 2's twin CI for dev and arzi moves to W10's full twin CI (run once on the merged head, not twice).
T4b3 written (blocks_t4.md). CR4 launched on b2f72dd.

## After 148 (the lead's context, not written as a note before the stop)
CR4 done (CR4_final.md); the CR merge into int ran its 9 MicroPython test files green at both stages, uncommitted.
F2, F3 and CM2 stopped at the usage limit (2026-10-23). The container was reclaimed during the pause; on 2026-10-26 the
session resumed in a fresh container with only the 656fc82 push and this context.

## Facts from the summary about the lost blocks (for the redo)
- B2c: Run 11's calibration `_SOAK_CYCLES = 80`, `_MEM_TREND_TOLERANCE_SD_MULTIPLIER = 4.0`, `_MEM_SAMPLE_INTERVAL_MS =
  100`, gc.collect() kept; the old setting (20 at 3.0) caught 0 of 12 planted leak boots. B2c also re-measured the
  FRAM both-copies-marked loss rate (SPECIFICATION.md's 1-in-8 sentence) [value lost] and found Run 5b's "nothing"
  branch never taken (0 of 80). B2a: one full scripts/test.sh at -1 took 1350.2 s; 25 tests fail and 1 errors in
  tests_scripts without frozen_modules. B2b2: the twin's FRAM image save writes the whole 66.1 MB per dev run (fixed in
  T4a to the used span, 274 KB); the 2**30-period ticks build and ticks30_batch.py. B2b: step 136 (twin_record
  reasons), the walks, step 102's columns [details lost].
- CE (e592fff, 0f9dbed): audit/sweeps/e51_sweep.py, audit/b3/e51.md, e51_verdicts.json: every gate-2-uncovered src
  line classed; the four files whose C-stack test ended tracing re-measured.
- CE2 (8f504a4): the coverage tracer's death: a raise in the trace callback leaves `mp_prof_is_executing` set
  (py/profile.c:168-173, py/vm.c:161-185, v1.29.0) so tracing ends silently for the rest of the file (CPython documents
  the same unset-on-error rule). tests/_coverage_runner.py: `_PROBE = compile("_ = 1\n", "src/<tracer probe>",
  "exec")`, `_LAST` holds the last traced file and line, `_note_ended()` writes `<out>.json.incomplete`;
  scripts/test.sh lists the notes and exits 3 (E.5.3's code 3; E.10 prints "PASS (coverage report not rendered)").
  tests/_untraced.py: a module global `tracer`; `untraced(call)` calls `sys.settrace(None)` and restores the tracer in
  `finally`; 5 of 6 C-stack test files run through it (the sixth, the twin integration file's :507, was T4a2's). Plus
  11 owed tests.
- CF1 (328c80d): audit/sweeps/plant.py (plants in /dev/shm copies), audit/b3/faults.md, the check_inc test, 11 of 217
  plants run, asy_crc_checks.4 fixed.
- CR (c564719): audit/sweeps/redflags.py, review_rows.py, audit/b3/review.md (8,514 rows). CR2 (146df65): 14 fixes in
  test files. CR3, CR4: recovered hand-backs.
- T4a (95e3b95): Run 11 values; TimeStale checks (null in Run 1, false after Run 8's first sync); README steps 167 and
  169-171; the twin FRAM save limited to its used span; Run 5b requires the exact ring and count.
- The twin record (tests_hardware/twin_record.json) must be re-recorded on the final head with the final reasons.json;
  test_twin_record is expected red until then.
- The decision-vocabulary allow-list row for the README's old `--mem-sample-interval-ms` line goes (the lead's, at
  W10) once that line changes.
