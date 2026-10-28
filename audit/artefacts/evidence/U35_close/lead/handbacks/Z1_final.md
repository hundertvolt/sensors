Lane Z (U35, block Z) hand-back. Commit 447ae0b on audit/u35-z (worktree S/wt-u35z, based on 6dabd9b). Nothing is left uncommitted and nothing of mine is still running.

**Steps**
- **Step 1 applied.** Both write sites now open the config file "w", write the text, close it and set `unpersisted = False`. Error handling is the same as at f3fff0e.
  - Removed: `_write_text`, `_finish_write`, `_remove_sibling`, `_TMP_SUFFIX`, `_FLUSH_SLICE_BYTES` with its @tunable tag, the sibling cleanup in delete_file, and the `BinaryIO` import.
  - Kept: the boot write under `_config_lock`. Its comment is reworded because the write no longer yields. K1's docstring refit is kept.
  - **Deviation (agent, 2026-10-22):** the two sites share one sync helper, `_write_file()` (asy_config_manager.py:429-434), holding exactly those lines. Written inline under the lock, setup() has 75 statements against ruff's ceiling of 73, which must not be raised. The helper adds no await.
  - AST compare against f3fff0e: only `_flush_staged`, `setup` and the new `_write_file` differ (u35/laneZ/mpy_ast_compare.log; mpy-cross sizes are in the same log).
- **Step 2 applied.** The tests return to f3fff0e's shape.
  - The structural test pins one open "w" and two `_write_file` calls.
  - `_FailingOs.rename` and `_RemoveFailingOs`'s `.tmp` branch are gone; their method reorders are kept.
  - `_littlefs_fake.py` is cut down to its commit-at-close model (the close after a failed write commits nothing, lfs2.c:3250-3253), for the one kept test.
  - In `_sensortask_scenarios.py`, `_DirWrites` is back to counting direct opens and `_RenameReporting` is gone.
- **Step 3 applied.** Six new tests, five using an open/os call recorder that asserts exact call lists, plus the kept write-error test:
  - PUT that changes a value: [open w, write, close]
  - unchanged PUT: []
  - boot over a valid file: [stat, open r]
  - boot over an absent file: [stat, open w, write, close]
  - reset of two stores: one remove each and nothing else
  - write error: not retried, old document kept, unpersisted, CFG_FILE_WRITE logged
  - Existing tests that already counted some of this (write-mode opens only): 842/864 (absent file written once), 932 (valid file: 0 writes), 2761-2773 (changed PUT writes 1, unchanged writes 0), 2738 (once per change).
- **Step 4:** all checks below are green apart from the one expected red.

**Seen failing first, against 6dabd9b's src:** the PUT, boot-absent, reset and structural pins all failed, each naming the old mechanism (`.tmp` "wb", the rename, the sibling removes).

**Bites (one scratch copy each), each failing its pin with the planted call shown:**
- b1: a second open in `_flush_staged`
- b2: a write on the unchanged path
- b3: a forced rewrite at boot
- b4: an extra stat after the boot write
- b5: an extra remove in delete_file
- b6: a write retry, caught at (writes, write_calls) == (1, 1)

**Checks**
- test_asy_config_manager: 240/240 at -1 and at 32768 (0.14/0.17 s; f3fff0e base 0.54/0.15 s).
- tests/test_sensortask.py, all 6 devices, at both stages, paired with 6dabd9b: 105/105 everywhere, times within ±3% (u35/laneZ/st_pairs.out).
- No MemoryError or "memory allocation failed" in any log.
- mypy main passes (no args, and `src tests tests_hardware/device_scripts`) clean; ruff clean.
- One pytest process with the 17 scans, the 12 pre-commit checks and the readers (incl. buildgen_error_contract, generate_sensortask_modules): 1463 passed, 1 failed.
- build_firmware 53 passed (6 skipped), digital_twin_ci_suite_errcount 134 passed, microtest 24 passed.
- **Red, expected:** tests_scripts/test_tunables_register.py:253 — "SPECIFICATION.md:11743: config.flush_slice_bytes is a tuned row, but no file carries its @tunable tag". It waits on the doc block.
- error_catalog.json needed no change: lane P's log sites had no errno.

**Hunk table (lead addendum; a = write mechanism, reverted; b = other, kept unless it only serves a)**
| Commit | Hunk | Class | Function / outcome |
|---|---|---|---|
| 934539c | `_FLUSH_SLICE_CHARS` + tag; `_flush_staged` comment and call; `_write_text` | a | reverted |
| 934539c | boot write under `_config_lock` | b | a reset's delete_file() and a flush share the lock with the boot write (owner "1. is good."); kept |
| 934539c | boot write sets `unpersisted = False` (through the shared helper) | b | a successful boot write marks the store persisted, as a flush does; kept |
| 934539c | structural test; slice and boot-slice tests; cancel-between-slices test | a | reverted / removed |
| 934539c | PUT+read during a yielded flush | serves a only | its premise is a yield inside the write; the torn-read property stays pinned by tests/test_bus_hazard_multi_device.py's concurrent-reader test; removed |
| 934539c | write error between slices | b | the error is not retried and leaves the old document; kept, rewritten for the single write |
| b52f3b6 | `_finish_write` (its log and unpersisted handling); sibling + rename; `TextIO` | a | reverted |
| b52f3b6 | `_FailingOs.rename`; interrupt/cancel/failing-close tests and helpers; asyncio.core import | a | removed |
| b52f3b6 | `_LittlefsOs`/`_FailingOs` member reorder | b | D.15 order; kept |
| b52f3b6 | model moved into tests/_littlefs_fake.py | a | cut down to commit-at-close for the kept test |
| 8f2f15f | memoryview, "wb", byte slices, tag rename, UTF-8 test | a | reverted |
| 65f7454 | `_TMP_SUFFIX`, `_remove_sibling`, delete_file calls; sibling-reset test; `.tmp` stand-in branch | a | removed |
| 65f7454 | `_RemoveFailingOs` reorder | b | D.15 order; kept |
| 480d4cf | `run_to_interrupt` moved into tests/_async_harness.py | b | harness runner with its own test (test_async_harness.py:376); kept there, no longer used by my file |
| 480d4cf | `_decoded()` | serves a only | 8 of its 9 sites were slice tests; back to `json.loads(before)`; the file still has 2 `json.loads` calls |
| 8edb5aa (lane V) | `_DirWrites` rename translation, `_RenameReporting` | a | reverted |

No hunk had an unclear purpose. A repo-wide git grep (excluding arduino and audit) finds no remaining caller of a removed name, only the SPECIFICATION lines below. `run_to_interrupt` stays in the harness.

**Leftovers in files outside my set (a-serving), for the lead**
- digital_twin/_flash_stall.py:74-75: comment says the store writes "wb", and `len(data)` now counts the characters of a str. f3fff0e had `len(data.encode())` and `IO[str]`; non-ASCII text is under-counted.
- tests/test_bus_hazard_multi_device.py:1049: comment names the sibling and rename.
- tests/test_asy_system_service.py:1569 (lane M's file): the `os.stat(path)` line is no longer needed but harmless.

**Stale SPECIFICATION.md sentences, for the doc block**
- A.4 :170-173
- C.7.3 :3756-3768, including :3766: a power cut in the first boot's defaults write now leaves an empty file, because littlefs commits a new file at open (lfs2.c:3125-3128). The next boot repairs it with the same defaults and records a ConfigFaults entry. This matches f3fff0e and differs from 6dabd9b.
- F.3 :6531 (`stall.flash_program`)
- J.6 :9602-9612: `_FLASH_HOLD_MAX_MS` 2129 is again the actual one-stretch bound.
- N.3 :11721 and :11743

**Resilience and effects**
- A cancel cannot interrupt the write (no await). A power cut leaves the old document (commit at close).
- A Ctrl-C cannot tear it: the VM raises a pending KeyboardInterrupt only at jump opcodes (py/vm.c:575-818, :1341), and there is none between the open and the with's close.
- Effect is the same in every mode (STA/AP/Silent/Off/USB) and on all six devices: one littlefs file write per accepted change or boot write, and one remove per store on reset. On dev, a flush holds the loop for one stretch again, inside the kept J.6 bound.

**Silent-failure scan of my files**
- Class 5 (flush window), flash-writes/UART mode, asy_config_manager.py:429-434: covered by `_FLASH_HOLD_MAX_MS`.
- Class 6/7 (power cut in first-boot write, empty file and fault entry), power-loss mode, same lines: self-heals; new relative to 6dabd9b, same as f3fff0e.
- No swallowed failures.

**Facts owed**
- To X: the @tunable tag `config.flush_slice_bytes` (256) is withdrawn.
- To the lead: the three outside-file leftovers above.

**Runs and exits**
- st_pairs.sh (pid 6443), rc=0.
- pytest group A, rc=1 (the expected red only).
- build_firmware, digital_twin_ci_suite_errcount and microtest, rc=0 each.
- MicroPython file runs, rc=0; seen-failing-first and bite runs, rc=1 as intended.
- All logged in RUNS.md; logs are in S/u35/laneZ/.
