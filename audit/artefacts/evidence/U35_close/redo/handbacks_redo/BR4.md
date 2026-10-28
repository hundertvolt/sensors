BR4 hand-back, written by the lane (2026-10-27)

Lane BR4: the raising lanes merged, rendered and checked, plus the owner's `_checked_write_results` decision (item 7).
Worktree S/wt-u35braise4, branch audit/u35-braise4, on 5a8c6e35. Not pushed. Nothing uncommitted (node_modules was
already untracked). Logs are in S/u35/laneB/br4/. Every run went through its run.sh, with RUNS.md lines naming `U35 lane BR4`.

## Commits (oldest first)
- 3d6e7a0a: merge audit/u35-braise (BR1, BR1b).
- c21df668: merge audit/u35-braise2 (BR2).
- 00c7c69d: merge audit/u35-braise3 (BR3).
  - raising.md and e51.md were never hand-resolved: one side was taken and the walk re-rendered them.
  - The walk's `--check` was green on each merge.
  - e51_sweep `--check` stayed red from c21df668 until b3e9ff3e. That was BR2's known stale hits.
  - review_rows `--check` stayed red until 598e8ef2.
- fad46143: cross-module line citations in the verdict files, re-located.
  - Each lane wrote its files without the other lanes' src edits. So the BR1/BR1b/BR3 files cited pre-BR2 asy_system_service.py lines, and the BR1/BR2 files cited pre-BR3 asy_fram_manager.py lines (for example run_setups :734-740 → :738-744, the shutdown try :441/except :494 → :445/:498, _start_task's except :502 → :506, set_pause :764-767 → :775-778).
  - Every moved line was mapped over equal difflib blocks, and its line text is unchanged.
- 65e31420: item 2 (the walk). See below.
- 598e8ef2: item 4 (the review rows).
- b3e9ff3e: item 3 (the e51 hits).
- 7008730e: item 7 (the owner decision): `_checked_write_results` removed.
- Item 5 needed no commit (no finding).

## Item 2: the walk (65e31420)
- **Lambdas.** A lambda is now its own scope, like a nested def, named `<fn>.<lambda>`.
  - This covers the three Timer callbacks: `arm_tick_timer.<lambda>::flag.set`, `SystemService._reboot.<lambda>::self._reset_due.set` and `SystemService.start_timers.<lambda>::self._sequencer_flag.set`.
  - Their e51 rows now show "none" for the enclosing except.
  - The three keys and proofs were updated. The proofs no longer say "the walk places it inside the try".
- **Conventions.** Every file's `conventions` key is rendered under "## Shared classes (each verdict file's `conventions`)".
- **Transitive groups.** A group with no hand verdict whose callee is in one of the seven modules now resolves to the callee's own rows.
  - A receiver table names what the receiver can be: `self.pr` → PrintLog, PrintLogHistory or PrintLogHistoryStore; `self._uptime` → TickSeconds; `self._boot_signature` → LockedValue; `buf` → RegionBuffer. A bare name resolves to the module function. The receiver table is an agent decision (2026-10-27).
  - The group becomes "handled" once every row of every candidate is terminal. Otherwise it stays "transitive" and names the open callee.
  - A call cycle makes the walk refuse to write.
- **Fate of the transitive groups.** BR2 and BR3 left 46 groups (212 sites). None is left open.
  - 40 resolve against BR1/BR1b's rows. That covers 19 distinct callees: PrintLog all/err/evt/one, PrintLogHistory err_s/wrn_s/setup/reset (+Store), make_logger, report_if_fatal, console, utc_now, arm_tick_timer, TickSeconds.read, LockedValue get/set_value, RegionBuffer get_buf/get_data_buf.
  - I read each callee's handled rows. They let out only small fixed allocations, or, for PrintLogHistoryStore.setup's history list, boot-only ones. Each calling file's conventions place those at its caller.
  - The six `get_log`/`reset` calls (`get_error_counter`/`reset_error_counter` in config_manager, system_service and fram_manager) got hand verdicts instead. Their catch is the webserver's, and their files' conventions do not name it:
    - get_log: `_write_errcount_entry()`'s `except Exception` at asy_webserver_service.py:1005;
    - reset: the ResetErrors `asyncio.gather(..., return_exceptions=True)` at :871 (extmod/asyncio/funcs.py:131-133), whose :876-880 log the error and answer Failed.
- **Other fixes in this commit:**
  - BR2's extmod/asyncio/event.py citations were off against v1.29.0, and are corrected: set 16-22, clear 24-25, ThreadSafeFlag 45-47/set 54-55/wait 60-63, Event.wait 28-35.
  - The walk's debug key now follows the FRAM setup call to :828.

## Rows by verdict per module (raising.md: raise rows plus call groups)
After the merge, at b3e9ff3e:

| module | handled | unreachable | defect |
|---|---|---|---|
| asy_base_classes | 72 | 49 | |
| asy_config_manager | 67 | 36 | |
| asy_fram_driver | 32 | 58 | |
| asy_fram_manager | 81 | 42 | |
| asy_print_log | 50 | 39 | |
| asy_system_service | 63 | 48 | 2 |
| math_helpers | 6 | 5 | |

- Sites outside a broad try: defect 3, handled 592, unreachable 540. Nothing is open or transitive.
- After item 7, asy_base_classes reads handled 71, unreachable 47 (the function's raise row and its isinstance and TypeError groups are gone). Sites: defect 3, handled 592, unreachable 538.
- The two "defect" rows are BR2's fixed mempause groups (:530; :713/:717). I kept the word because A.U35.36 counts a defect as terminal. Whether a fixed defect should now read "handled" is your call.

## Item 3: the coverage comparison (b3e9ff3e)
**The run.**
- Every tests/test_*.py ran under build-settrace with tests/_coverage_runner.py, using the test.sh `--coverage` command line. The PER_DEVICE files ran on all six devices: 116 jobs, all rc 0, no tracer cut short, 680 s.
- The toolchain was a private copy of S/tc-int, whose toolchain record matches this tree's toolchain/ inputs. It is deleted.
- The hits are the union of the dumps.

**asy_system_service.py: matched.**
- Every earlier hit outside BR2's edited regions maps to a fresh hit.
- The 14 edited or inserted lines are all hit: :387-396, :532, :538, :544, :714.
- The E.5.1 fallback row moves from :454 to :458.

**asy_fram_manager.py: BR3's remap matched on every line it moved or measured.** No earlier hit is missing.
- The fresh run also hits :168-170 and :424-425. These are the two `except Exception` guards in `_clear_chunk`/`_write_chunk`, which test_asy_fram_manager.py has reached since CEr2's test (1298e714).
- BR3's own run hit them too, but its remap kept CEr1's status for unchanged lines.
- Their two "covered" e51 verdicts were stale (their sites no longer exist), so they were removed: 61 sites now.

**Item 7's second fresh run.** It reproduced both files' hits exactly. For asy_base_classes.py, every earlier hit maps to a fresh one, and the edited try line :502 is hit.

## Item 4: the review rows (598e8ef2)
- **The `helper_swallows` flag on BR2's test: its real cause.**
  - `test_a_raising_preflight_leaves_the_gate_as_a_refusal_does` never calls `_retire()`.
  - The scan resolves `rig.stop(sup)` by attribute name to `_Rig.stop` (tests/test_asy_system_service.py:1252-1258, via redflags.py's `_near_mods` class-member lookup), which awaits `_retire()` (:1130-1137, its `except (CancelledError, Exception): pass` at :1137).
  - Verdict: justified. It is teardown, and the claim is asserted before it, at :1589-1593.
- **The file's 42 other `_retire()` rows.** Their shared reason cited :1128-1136 / "stated at :1135", which was already stale on the head. It now cites :1130-1137 / :1137.
- **The six CMr1 rows, all biting.** Each is a case helper looped over `distinct_wirings()` whose own assertions carry the claim. The reasons give the lines:
  - clock_jump `_stepped_stamps_on` :264;
  - clock_jump `_backup_after_a_backward_step_on` :137/:139;
  - hot_replug `_power_cycled_bmp3xx_on` :135-138;
  - ntp `_restore_through_the_outage_on` :385-387;
  - ntp `_lost_sync_on` :291-293;
  - test_twin_wiring_contract `same_callee`: two planted devices compared, :413.
- **Result:** 8546 rows (8545 after item 7 removed one test): CRr2 83, fixed 46, justified 129, biting 8288 (8287 after item 7). `--check` is green.

## Item 5: callers of FRAMChunk.read() and FRAMTimestampedChunk.read()
**No production caller of either.** The searches covered src/, build/generated_src/ and digital_twin/, including `await x.read()`, a bound `.read` and getattr. Every `.read()` found there is TickSeconds.read().

**The two production chunk owners use read_into() with their own buffer:**

| owner | chunk size | how it reads | when |
|---|---|---|---|
| PrintLogHistoryStore (asy_print_log.py:293) | 2 + history_length bytes, plus CRC8 1 (history_length defaults to 10, up to 0xFFFF) | one get_buffer() (:317) and read_into() (:321) in `_read()` | `_read()` is called only from setup() (:407), once at boot |
| SGP40Reader's timestamped backup (asy_sgp40_driver.py:243) | 256 bytes (_VOC_PARAMS_MEMSIZE), plus CRC32 | read_into() (:558) into `_backup_buf` | the buffer is allocated once at construction (:253), re-tried once at :297 |

- `_FramChunk`, print_log's Protocol, does not even declare read().
- read() itself allocates a chunk-sized FRAMChunkBuffer and a copy on every call. Only tests and device scripts call it: test_asy_fram_manager.py (69 calls), test_digital_twin_bus_hazard_concurrency.py (13), test_fram_integration.py (2), test_ntp_fram_system_integration.py (1), and the fram_* device scripts.
- **No finding.**

## Item 6: checks on the head after item 5 (b3e9ff3e)
- The walk, e51_sweep and review_rows `--check`: all green.
- Readers (test_citations, test_decision_vocabulary, test_comment_block_cap, test_fatal_report_sites): 687 passed.
- lint_direct rc 0. The six mypy passes: rc 0 (main 272, twin 55, host 311, three single-file checks).
- The 23 test files importing asy_system_service, asy_fram_manager or asy_fram_driver, at both stages, with test_digital_twin_sensortask_integration.py on all six devices: 56 jobs, all rc 0, zero memory markers (i6_both.log, both_imp6.out).
- **A runner artifact, not a product red.** My first pass ran a file's two stages at the same time. That made test_asy_sgp40_driver.py fail at 32768 and test_asy_system_service.py time out at 32768.
  - Cause: both processes share TmpScratch's per-file root, tests/_tmp/<key>. The second process reused the first one's numbered config directory, so BackupPeriod was already 30.
  - Both files pass with the stages run one after the other, as scripts/test.sh runs them (i6_rerun2.log). The runner now does that.
  - scripts/test.sh is not exposed: it never runs one file twice at once, and its PER_DEVICE files key their scratch by device.

## Item 7: `_checked_write_results` removed (7008730e)
**The proof, per override.** I ran mypy's main pass with reveal_type at every return, in a scratch copy (deleted).

| override | the returned WriteValidity | revealed / found |
|---|---|---|
| SensorReader._set_mgr_cfg (asy_base_classes.py:550) | `return False, {}` | a literal dict |
| SensorReaderConfig._set_mgr_cfg (:808) | returns ConfigManager.write_config(), whose results come from compare_before_write() | `results: WriteValidity = {}` at asy_config_manager.py:208, filled only with the Final literals; revealed dict[str, Literal['Invalid','Unchanged','Valid','Failed']] at :232, :648 and :669; every other return is `False, {}` |
| asy_ntp_client.py:230 | super()'s result, then `results[key] = INVALID` | revealed the same dict at the return |
| asy_wifi_service.py:294 | the same | revealed the same dict at the return |
| asy_scd30_driver.py:261 | compare_before_write()'s results, mutated with literals, `.update()` with super()'s frc_results or `dict.fromkeys(frc, FAILED)` | outcome, frc_results and results revealed as typed dicts |

- **Generated modules** define no override (checked across build/generated_src).
- **Any, cast and ignores.** The function bodies and compare_before_write/write_config were scanned for these.
  - None occurs on a returned value's path.
  - asy_scd30_driver.py's override does carry three `type: ignore`s: :278 `[arg-type]` on compare_before_write's `resolution` argument, :297 `[arg-type]` on a setter's argument, :300 `[assignment]` on `_frc_interval_s`.
  - None of them touches `results`. compare_before_write is not generic, so its declared return type stands.
  - I read the condition as "on the returned value's path", so the proof holds. If you read it as the whole function, these three are the path to hand back, and 7008730e reverts alone.
- **Removed:**
  - the function and its two calls (the try comment now says the return shape is mypy's, D.2);
  - test_set_dict_cfg_set_mgr_cfg_override_malformed_result_marks_every_field_failed, and its decision-vocabulary allow-list line;
  - the function's three verdict entries; the raising.md and e51 rows were re-rendered;
  - the review row went with the test.
- **Two proofs were rewritten:** `_set_dict_cfg::results.setdefault` and `_recover_failed_push::res.get`. Both had leaned on the check, and both now cite D.2's static dict.
- **Moved lines** were re-located in asy_base_classes.json (67, by a strict own-module rule, checked by hand where another file's citation came first), config_manager.json and print_log.json.
- **Catalog text.** buildgen/error_catalog.json errno 5's text now reads "the _set_mgr_cfg() extension point raised", without "or returned a malformed result". The constant and code are unchanged. Agent decision (2026-10-27): after the removal, that detection no longer exists.
- **Checks:**
  - fresh coverage: 116 jobs, rc 0; the base_classes hits re-dumped;
  - asy_base_classes.py's 39 importer files at both stages, PER_DEVICE files on all six devices: 98 jobs, all rc 0, zero memory markers;
  - lint_direct rc 0; the six mypy passes rc 0;
  - `npm run test:unit`: PASS;
  - tests_scripts catalog, definitions, generator and readers: 1150 passed;
  - the walk, e51 and review_rows `--check`: green.

## For the lead
1. **Living registers outside the raising files still cite pre-fix lines.** The BR2/BR3 fixes moved these citations, and I did not touch them (other lanes' files; some describe the fixed code itself). Mapping, old → new:
   - faults.md: system_service :569→573, :401→405, :453-454→457-458; fram_manager :697→708, :748→759, :795→806;
   - open_findings.md: system_service :577-580→581-584, :481→485, :406-408→410-412, :737→741, :536-552→540-556, :542-543→546-547; fram_manager :788→799;
   - REGISTER.md: system_service :660-665→664-669, :537→541, :542-543→546-547, :406-408→410-412; fram_manager :645-680→656-691.
   
   Item 7 moved asy_base_classes.py lines past :366 too. My mapping tool for this is S/u35/laneB/br4/tools/cites.py.
2. **e51_hits.json is now mixed.** asy_base_classes.py, asy_system_service.py and asy_fram_manager.py come from this tree's run; every other file still has CEr1's. Lines CEr2's tests cover in other files therefore stay listed as uncovered with "covered" verdicts until those files are re-dumped too.
3. **Tool calls.** About 150, past the 80 goal. Item 7 arrived mid-lane and was finished, committed and green. Both fresh coverage runs and the reruns were needed.

nothing of mine is running
