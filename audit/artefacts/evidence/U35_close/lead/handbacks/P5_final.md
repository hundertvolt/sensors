U35 P5 hand-back, lane P, S/wt-u35p. Head 596e7ff, on 65f7454. Nothing is uncommitted and nothing of mine is running. I used about 70 tool calls, so two reds in a P file are left open (see "Left open").

Listing check (sites that list, glob or count a config directory, checked for `<file>.tmp`). No P file misreads the sibling, so nothing needed a fix.
- src/, buildgen/, digital_twin/: none list a config directory.
- tests/_sensortask_scenarios.py:2305 and :2308 (lane V): read right. A leftover sibling would count as a defect, which matches delete_file removing it, and every write renames, so none is left.
- tests/_sensortask_scenarios.py:954 `_DirWrites` (lane V): misreads (it records `.tmp` names). P4 already reported it. It is still red on all six devices at both stages, at :939.
- scripts/_digital_twin_ci_suite.py:452: reads right. The glob `config_*.cfg` excludes `x.cfg.tmp`, and Run 13 abandons no write. :339 lists the state directory only.
- tests_hardware device-script cleanup loops (about 25 sites, e.g. allocation_need_per_source.py:137) remove every name, the sibling too. system_command_config_reset.py:57 reads right: setup leaves no sibling, and sorting puts `.cfg` first. config_files_dump.py:27 reads right: its prefix and suffix filter skips the sibling. conftest.py:75/:280 reads right: a production sibling is not scratch. flash/test_system_commands.py:132 reads right: an empty dir after a reset matches delete_file.
- Not a listing, lane V: digital_twin/_flash_stall.py stalls at the sibling's close but not at the rename's directory commit, so the twin does not model the rename's stretch.

R-10: the row is right, and it is fixed. All three new tests failed on 65f7454:
- the later reset refused by a pause: got (1, [0,0,0,0]), expected (1, [0,0,0,4]);
- the same with a new code logged between the starts: got (2, [0,0,0,5]), expected (2, [0,0,4,5]);
- both resets land: the final state is right, but the repeat's own write packed (1,0,0,0,0,0).
- Fix in src/asy_print_log.py: each store reset() takes the lowest free bit of `_RESETS_ALL` (29 bits, so every step stays a small int). A repeat of the newest code marks every reset begun with nothing kept since. An append ends that. A `finally` frees the bit on every exit, a cancel included. `_since_kept`, `_clear`, `_pack_reset` and `_write` now take the bit.
- New behaviour: a reset beyond 29 in flight on one store is refused at once and clears nothing. It failed first at the missing bound.
- Bites, all biting: no fresh reset on append fails the new-code guard with (2, [0,0,4,5]); dropping the `finally` fails the cancel test; disabling the refusal fails the bound test with (None, …).
- Allocation, Unix port, collection suspended, the same at -1 and 32768: construction unchanged (2176 B at 10 slots, 2272 B at 64). One reset goes from 1344 to 1440 B, transient, from a larger frame. Attributes go from 19 to 20 with no map growth. Zero MemoryError in every run.
- Effect: every FRAM device, in STA and AP, through ResetErrors over REST. Silent, Off and USB have no REST, so nothing changes there. RAM-only histories reset atomically and are untouched.

Changelog: B89, Class B. It covers 1856280's six narrowing comments in asy_uart_comm.py, lane P's only change to that file since f3fff0e. The mpy file is byte-identical. The exerciser gets no row.

P's checks:
- mpy compare, f3fff0e against the head, in p5/mpy/compare.txt. uart_comm is identical. crc_checks, fram_manager and config_manager match P1-P4's commits. print_log's code changes only in the functions edited plus the two class bodies.
- Silent-failure scan of the print_log change: class 2 (the bound) refuses visibly, and ResetErrors answers "Failed". Class 6: a bit could leak on a cancel; the `finally` closes it, shown by a bite. Classes 4 and 7: a refusal shows as "Failed". Class 5: the old mark could alias after a `_kept` wrap; the new bits cannot. Nothing new beyond these. P1-P4 scanned their own files.
- The 17 scans: 1 red, tunables_register, on config.flush_slice_bytes. It is expected and waits on D's Part N row.
- Readers (39 files in one process): 1987 passed, 2 red, both in test_microtest.py, both on P4's tests/test_asy_config_manager.py:
  - :3325 `asyncio.run(coro)` in `_run_to_interrupt`. The harness's `run()` tracks and cleans up tasks, which may change the abandoned-task scenario, so it needs checking before a swap.
  - json.loads: 10 sites where the allowlist counts 2 ("config files and a decoder stand-in"). Fix without touching the allowlist: route :2461 and the 8 `json.loads(files.docs[path])` sites through one module helper, which leaves 2 sites.
- twin_record: red, expected.

Runs (all in S/u21/RUNS.md; batch pid 4130 exited; mem=0 in every row):
- Rebuild ok.
- print_log, base f3fff0e against the head, in seconds: at -1, 0.36/0.37 against 0.39/0.38; at 32768, 0.41/0.40 against 0.44/0.43. The head has 6 more tests and stays under 10 % slower.
- 14 reset importers at both stages: all green.
- test_sensortask: 90/91 on all six devices at both stages. The one red is V's :939.
- One bite loop hung on a self-held lock in my own first draft of the bound test. I killed it by pid and fixed the test.

Decisions (agent, 2026-10-21): per-reset bits rather than one shared pair; refusal beyond 29 in flight; I left P4's interrupt helper alone in this block.

Left open: the two test_microtest reds above, in tests/test_asy_config_manager.py.

Logs: S/u35/laneP/p5/ (batch.tsv, logs/, readers.log, scans17.log, seen/, bites/, mpy/, alloc/alloc.txt).