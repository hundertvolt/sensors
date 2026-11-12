H4 hand-back (lane H, block H4), on c398332, branch audit/u35-h4, worktree S/wt-u35h4. Nothing is uncommitted and nothing was pushed.

Commits:
- 6162d1d: `tests_hardware/conftest.py:110-112`. `pytest_configure` adds the ini line `error::pytest.PytestUnhandledThreadExceptionWarning`, so a thread that dies now fails the test it ran under. The comment is 2 lines and tagged (agent, 2026-10-22). A `-W` option or a filterwarnings mark still overrides it; the hardware suite has neither.
- bc8d615: `tests_hardware/twin_record.json`, re-recorded at both GC stages.

Item 1, the bites. All ran in a throwaway copy of the tree with `--twin`, never on hardware; the copy is now deleted and nothing planted was committed.
- B1, on the base: a scratch test whose thread target raises RuntimeError passed, and so did a planted death in the real bench `sensors_reader` (driven through `_load.readers()` with a fetch that raises KeyError, a type the reader does not catch). Result: 2 passed, 2 warnings, rc 0.
- B2, with the change: both tests FAILED ("Exception in thread scratch-dier" and "Exception in thread reader-0"), rc 1.
- Logs: S/u35/laneH/h4/B1_base.log and S/u35/laneH/h4/B2_change.log.
- No bench test can run in the twin (`dut_ip` needs the bridge), so "its test" is the scratch test that drives the real reader.

Item 2, the re-record. I used S/u35/laneH/h4/record.sh, the lead's script pointed at wt-u35h4 and laneH/h4, with H3's reasons.json unchanged. The disk had 8.2 GB free and no other heavy process was running.
- Wall time 2109 s, rc 0, 122 instruments recorded.
- Flash tier: 25 failed / 72 passed / 7 skipped at gc -1, and 24 / 73 / 7 at gc 32768.
- Against the base record (cb89c3d): no entry's result, stage outcome or reason changed. Both before and after hold 67 pass and 55 exception at each stage.
- Only 24 `api_sha256` hashes moved. They are exactly the 24 entries whose imports (by ast, includes too) name one of the 3 changed src/ modules (S/u35/laneH/h4/apicheck.py). The brief's 27 came from a text match. No `sha256` or `runner_sha256` moved.
- The conftest change uncovered no hidden thread death: 0 PytestUnhandledThreadExceptionWarning at either stage, so nothing needed a root cause.
- One test case differs between the stages without changing its entry: `test_a_reset_mid_erase_leaves_every_chunk_old_or_blank[1000]` failed at -1 and passed at 32768.
  - Cause: the twin's erase took 1033 to 1349 ms in these runs, so a reset at 1.0 s can land either side of the erase's end depending on host speed.
  - The [2000] case fails at both stages, so both entries stay exception.
  - For the lead: the reason text in reasons.json and the record (`system_command_fram_erase.py`, `test_system_commands.py`) says the resets "land after it". For the 1.0 s case that is a race, not a certainty.
- To capture the flash runs' output, a uv shim on PATH (S/u35/laneH/h4/shim/uv) teed it per stage. It does not change output or exit code. Logs: S/u35/laneH/h4/flash_-1.out and S/u35/laneH/h4/flash_32768.out.

Unraisable count: 0 PytestUnraisableExceptionWarning in record.log and in both stages' flash output, so no test is named. There were also 0 "Exception ignored" lines, 0 MemoryError and 0 "memory allocation failed".

Item 3, the checks:
- ruff is clean on conftest.py.
- The host mypy pass (host_typecheck.ini, cold cache) is clean on conftest.py.
- 27 tests_scripts files ran one per process (S/u35/laneH/h4/checks.sum), all rc 0: twin_record 10 passed, the runner and verdict tests, the run-record tests, the marker and persistence-gating tests, the conftest readers (constants, collect matrix, board image, scd30 prerequisite, bench restores serving, request timeout ceiling, fram regions) and the 12 doc and convention checks.
  - test_citations keeps its existing warning: the datasheets/ submodule is not initialised.
- `pytest tests_hardware --collect-only`: rc 0, 198 of 229 collected (31 deselected).

Silent-failure scan of conftest.py:
- This change closes the swallowed-thread-death class (class 4) for the whole hardware suite.
- Remaining limits, all inherently safe or already covered:
  - threading itself drops a SystemExit raised in a thread, and no target raises one;
  - pytest charges a thread that outlives its test to a later phase, but every test joins its threads with a bound and fails on survivors (`_load.join`, observe_during's is_alive check).

For D3: no sentence goes stale. Optional: tests_hardware/README.md could state that a thread that dies fails its test (conftest.py:110-112).

Effect: host tooling only. No firmware change; every mode (STA, AP, Silent, Off, USB) and every device is unaffected.

Runs, all lined in RUNS.md: the record, pid 32396, rc 0; readers plus the 12 checks, pid 6286, rc 0. Under a minute each: B1 rc 0, B2 rc 1 (the intended bite), collect rc 0.

About 38 tool calls.
nothing of mine is running