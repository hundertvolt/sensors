# N8: OF-13 completed (the webserver test file's planned tags) and two D.15 reorders (lead, 2026-10-26)
Read `S/u35r/briefs/redo_common.md` first. Base, worktree and branch named at launch; logs in `S/u35/laneN/n8/`.
Sources: N67's hand-back `S/u35r/handbacks_redo/N67.md` (item 6 and "Not done"), `audit/sweeps/open_findings.md` OF-13,
the planned actions `audit/actions/U8C.md` A.U8C.21 and `audit/actions/U8C2.md` A.U8C2.05 (their Site and Change
lines are the specification), and `audit/actions/U30.md` item 8 under its interactions list (sites A.U30.12/A.U30.13
removed). Every line number in those actions is stale: re-locate each literal on your base by its value and context.
Test, tool and register text only: no `src/`, no generated file, no wear.

## Items
1. OF-13: apply A.U8C.21 and A.U8C2.05 as written in tests/test_asy_webserver_service.py: each module-level constant
   with its `# @tunable` tag, each listed literal replaced by its constant, the mirror tags and further sites the
   actions name. Use the actions' IDs. N67 tagged `_RUN_BOUND_S` as `l1.webserver_run_bound_s`; A.U8C.21 names it
   `l1.asy_webserver_service_run_bound_s`: rename it to the action's ID (tag and Part N row) unless a later action in
   `audit/actions/` or the register already uses N67's; say which. A literal an action lists that is gone or changed
   meaning on your base: list it with the reason, no tag. A tuned literal in the file that neither action lists: list
   it (value, line, what it bounds), no tag; the lead decides on those.
2. Part N rows for every new ID (SPECIFICATION.md Part N, N.1's Basis rule and N.2's form including per-file
   counts): Basis measured from the file's runs at both stages where a run gives it (as N67 measured the run bound:
   bounded calls per run, slowest), else estimated with the measurement owed; Margin against it; Re-check trigger.
3. Proof: the file's AST before and after differs only by the new constants and names replacing equal-valued literals
   (show the comparison); 225/225 (or the file's count) at both GC stages with the shared binary directly, zero memory
   markers; test_tunables_register green, and it fails on a scratch copy with one new tag deleted.
4. D.15, the two pre-existing helper-order findings N67 named: tests/test_ntp_fram_system_integration.py (`_wlan`
   vs `_connect_wlan`) and tests_scripts/test_tunables_register.py (`_comments` before `_is_comment_line`; its "check
   on a tmp tree" heading removed in its own commit first, D.15's rule). Pure reorders, AST-verified as D.15 requires.
   Then measure, without fixing: run tests_scripts/test_code_conventions.py's own ordering logic over the helpers of
   tests/, tests_scripts/, digital_twin/, buildgen/, scripts/, toolchain/ and tests_hardware/ (a scratch driver, not
   a change to the check), and hand back the count per scope and the first few sites. D.15's scope is all eight
   scopes; only src/ is machine-checked.

## Proof and checks
Each changed MicroPython file at both stages with the shared binary directly; ruff, the host and main mypy passes
(stubs at `S/shared/typings`), the comment cap, test_citations, test_decision_vocabulary, test_tunables_register,
test_code_conventions and every tests_scripts reader of a changed file. Your base has a changed `toolchain/`: no
`scripts/test.sh`, no twin CI, nothing pointed at the shared toolchain that could rebuild it. Other lanes run: nice 19.

## Not yours
src/, digital_twin/, toolchain/, scripts/, audit/ records, the NTP rows of Part N (lane F5), every allow-list (hand
back the row you need). Commit subject `U35 lane N8: <summary>`, the two trailers; do not push. Hand-back: commits;
per item what changed, the AST comparison, the red and green with log paths; the untagged and gone literals; the D.15
counts; last line "nothing of mine is running".
