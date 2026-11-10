W1b hand-back, written by the agent (Tue Nov 10 19:26:32 UTC 2026)
Worktree S/wt-w1b, branch audit/w1b, one commit 3e35f5c9 on 886f8af0 (not pushed): 71 files, +2942/-2946.

1. Reorder by hand (Edit moves): 69 of 586 Python files. buildgen 13, digital_twin 2, fakes 0, scripts 13, toolchain 2,
   tests 18 (9 helper modules, classes in 9 test files), tests_hardware 11, tests_scripts 10 (_devices.py, classes in 9
   test files); js/ 0 of 11 (already in order). One non-Edit move: tests_hardware/conftest.py's two credential-filtered
   functions moved as one line-range move, never printed; the 16 credential-word lines are moves (+16/-16, same set).
   Removed heading: buildgen/driver_registry.py's 2 lines over its four lru_cache'd helpers ("cached by the file's text,
   not by its path ... each returns an immutable value"), split by the order; the facts stay in their signatures; code
   in 886f8af0. Decisions (agent, 2026-11-10): micropython_overrides.py's 42 functions all follow its last constant, so
   the section banners label constants only; scripts/_digital_twin_scenarios.py's registry follows the file order, so
   two own-boot scenarios swap run order (_reset_errors_under_mempause before _reset_errors_under_the_escalation).
2. AST comparison (scratch ftmp_w1b/astcmp.py vs 886f8af0, seen catching a planted body and comment change): 69/69 same
   definitions, each ast.dump identical, statements in order (classes, if-blocks recursed); 68 with identical comments,
   driver_registry less its heading. Generator outputs (module, 2 boot entries, definitions, API reference, twin wiring,
   expected facts) byte-identical on all 6 devices. src/ untouched: sizes, bytecode, image unchanged.
3. Check: member_order() also runs over the 8 scopes (test_every_python_scope_follows_d15, _repo_scan.python_files, no
   new fixture; 2.9 s for 586 files). The test-file rule is one condition (_TESTS_THEMSELVES); classes there stay
   checked (test_a_test_files_function_list_is_left_out_of_the_order_but_not_its_classes). Module.generated now reads
   "under build/" (was "not under src/"; equal on the old inputs). Red first (planted test; scan named 69 files), then
   green. SPEC D.15 scope + last sentence and Part 0.4's row: nine Python scopes machine-checked, js/ by review.
4. _PENDING_ASSERTS (allow-list of src asserts a later change would remove), _asserts_by_function, no_assert()'s pending
   branch and its pinning test test_every_pending_assert_is_still_there: removed, the list being empty; no_assert()
   keeps its planted-break case; code in 886f8af0.
Held back (a reorder changes behaviour or the tests themselves): module function lists of tests_hardware/manual/manual_
{bus_electrical,persistence,sensor_accuracy,wifi}.py (@register order = run order) and tests/_sensortask_scenarios.py
(86 _scenario_* = test_<name>). Check and SPEC D.15 exempt both (agent, 2026-11-10); back to the lead if wrong.
Gate: rebuild.sh OK; lint_direct rc=0; mypy x3 clean; conventions + comment cap 685 passed; 74 port-free tests_scripts
readers 2093; SPEC readers 110; 7 MicroPython files with touched classes at -1/32768/coverage, 0 memory markers; npm
lint + typecheck clean, test:unit 1192 passed; scripts/test.sh -1: PASS, files 120 passed / 29 skipped / 4 deselected,
tests 5252, tests_scripts 6560, scenarios 4/4 devices, 0 memory markers. Not on tc-c as written, see below.
Toolchain (needs the lead): reordering setup_toolchain.py + micropython_overrides.py changes the input hashes every
toolchain record pins, so after this commit tc-c, tc-gate, tc-int and tc-mcov read stale and test.sh runs setup, which
fetches (no network in run.sh). Fix per dir, offline, ~76 s: uv run toolchain/setup_toolchain.py test --toolchain-dir
<dir> (it keeps the pico-sdk/picotool fields). My first test.sh on tc-c hit this: setup dropped tc-c's record, then its
fetch failed; binaries untouched. Restored 19:08 by 886f8af0's own _toolchain_record() + probes (equal to tc-int's but
for input_sha256, 886f8af0's, and recorded_utc); test.sh's stale probe passes it for 886f8af0. The gate ran instead on a
private copy (offline `test` rebuilt all 3 flavours + firmware from my toolchain files, zero warnings), now deleted.
Findings (c): common_r1's MICROPYPATH lacks fakes; one early unfiltered grep printed a fake test SSID literal from
tests/_sensortask_scenarios.py (no real secret). No operation's cost changed (pure moves).
