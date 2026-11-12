K4 hand-back (tests_scripts/, 47 files, 50 blocks)
Commit 48b634d on branch audit/u35-k4, built on bc0d77b. Worktree: /tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/wt-u35k4. Not pushed. Nothing is left uncommitted. The commit changes exactly the 47 files listed in k4.txt. In test_comment_block_cap.py only the module docstring changed.

Blocks by kind (50 in total):
- Rewrapped, words unchanged (16): 12 module docstrings, plus 4 comment blocks: test_digital_twin_boot_contiguity.py:69, :76 and :209, and test_run_unix_port_integration_sh.py:30.
- Tightened (31): mostly dropped articles or "and", and "through" became "via". Every citation, number, quote and actor stays. The most visible rewordings:
  - test_fatal_report_sites.py: "the one errorhandler(Exception) registers" became "the errorhandler(Exception) one".
  - test_ci_workflow.py: "(pyyaml is no dependency here)" became "(no pyyaml)".
  - test_code_conventions.py: "_NAME equal to" became "_NAME =".
  - test_twin_record.py: "demands a re-run" became "needs a re-run".
  - The full word-level list is in /tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/u35/laneK/k4/changes.txt
- Split (2):
  - test_js_api_mirrors.py: which mirrors are pinned, then how both sides are read and each pin is bitten. Words unchanged.
  - test_ruff_exemptions_live.py: the lifted ruff run must show each exemption, then the policy entries with no site. The first paragraph was also tightened.
- Moved (1): test_task_tops.py. The top's shape left the docstring and now sits as a 2-line comment in `_is_top()` and a 1-line comment in `ends_in_a_top()`. The docstring now points to them.

verify.txt: /tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/u35/laneK/k4/verify.txt. It ends `CODE-CHANGED FILES: 0`, with 33 docstrings changed in wording.
CAPMOVE lines: none. Relay lines written: none.
Runtime docstring readers: none of my files feeds argparse, and I changed no scenario docstring.

Checks (logs in u35/laneK/k4/):
- show.py 120 on my 47 files: `TOTAL 0`, exit 0.
- verify.py: exit 0. measure.py: exit 0, none of my files appears.
- ruff 0.16.10: exit 0. Host mypy pass (host_typecheck.ini, cold cache, 47 files): exit 0.
- The 12 commit checks plus 6 readers (ruff_exemptions_live, host_cli_exit_idiom, host_text_encoding, no_variant_literals, retry_counts, suppression_form): 910 passed, 1 failed, exit 1. The failure is already red on bc0d77b (below).
- The 17 repo-wide scans on 48b634d: 872 passed, 6 failed, exit 1. All six are already red on bc0d77b.
- No shell files in my set, so no shellcheck. No unit, twin or timing files run, as the brief says.

Already red on bc0d77b. My diff touches only tests_scripts/, and every failure names a site in src/, tests/, scripts/, tests_hardware/ or SPECIFICATION.md:
1. test_tunables_register.py::test_the_tags_and_the_part_n_rows_agree: 16 tags have no Part N row, e.g. src/asy_config_manager.py:71 config.flush_slice_bytes, src/asy_uart_link_driver.py:51/53/55, scripts/_digital_twin_scenarios.py:146/148/150/161. Also, SPECIFICATION.md:11787 is a row with no tag. These wait on D2 or you landing the register rows.
2. test_level_containment.py::test_every_twin_scenario_is_covered_or_an_exception_row_with_a_reason: fault_storm, ntp_unreachable_load, reader_saturation and watchdog_fault have neither an L3/L4 counterpart nor an E.6.6 row.
3. test_task_inventory.py (4 tests): src/asy_uart_link_driver.py:221/222, `UARTLinkDriver._two_initiations()` creates tasks outside every starter and has no C.9 row. This comes from bc0d77b's own UART commit.

Decision (agent, 2026-10-22): two rewraps leave a citation split across a line break, test_manual_runner_summary.py:1-2 and test_task_tops.py:2-3. test_citations matches across whitespace and passes, so I left them.
I did not run the silent-failure scan as a separate sweep: verify.py shows no code changed, so there is nothing new for it to find.

Runs, each with start and exit lines in RUNS.md: host mypy (6 s, exit 0), commit checks (1m30, exit 1, the red above), 17 scans (58 s, exit 1, the reds above). I deleted the mypy cache. nothing of mine is running

--- addendum ---
K4 addendum on your note about keeping line counts. I made no new edits: the note says finished blocks stand. Commit 48b634d is unchanged and nothing is uncommitted.

Four files changed line count, so their file:line citations move:
- tests_scripts/test_js_api_mirrors.py, +3: the docstring split at lines 1-3 is now lines 1-6. Everything below shifts by 3.
- tests_scripts/test_ruff_exemptions_live.py, +2: the docstring split at lines 1-3 is now lines 1-5. Everything below shifts by 2.
- tests_scripts/test_task_tops.py, +3: the docstring keeps its 3 lines. The two lines added inside `_is_top()` (now lines 27-28) shift everything after old line 26 by 2. The line added inside `ends_in_a_top()` (now line 166) shifts everything after old line 163 by 3 in total.
- tests_scripts/test_run_unix_port_integration_sh.py, +1: the comment at lines 30-31 is now lines 30-32. Everything after old line 31 shifts by 1.

The other 43 files keep every line where it was.

A search outside audit/ (and excluding arduino/) finds no file:line citation into any of these four files, so only audit/ text could need remapping.

nothing of mine is running
