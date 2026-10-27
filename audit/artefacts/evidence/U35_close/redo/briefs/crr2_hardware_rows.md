# CRr2: the review's hardware rows - device-script facts, the bench log check, the flash tier's logs (lead, 2026-10-26)
Read `S/u35r/briefs/redo_common.md` first. Base, worktree and branch named at launch; logs in `S/u35/laneC/crr2/`.
This redoes lane C's CR3 and CR4 (lost; their hand-backs survive: `S/u35r/recovered/handbacks/CR3_final.md`,
`CR4_final.md`, each a map to re-check, never proof) on CRr1's rows: audit/b3/review.md, audit/sweeps/redflags.py,
review_rows.py and review_verdicts.json are in your base; every row CRr1 gave the verdict "CRr2" is yours (update
verdicts through review_verdicts.json and re-render with review_rows.py). Specification: audit/actions/U35.md A.U35.03
and A.U35.37 (Change lines); CRr1's hand-back `S/u35r/handbacks_redo/CRr1.md` ("For CRr2"). Never run a tests_hardware
test except `--collect-only` or `--twin`.

## Blocks, in order (one fresh agent each; commit each block green; past 80 tool calls hand back at a seam)
CRr2a, the device scripts and the named rows:
1. Every device-script fact row (CR3's item 1: a fact a host test asserts by key is biting, named; a fact no host test
   reads gets a host assertion in the test that runs the script, or is a stated diagnostic, justified in place). CR3
   found 42 such rows and fixed 6 with 7 host assertions (its hand-back names them: test_bus_concurrency, test_reset_
   reasons, test_uart_crossover); re-find and re-land each, bitten on synthetic script output (vacuous output passes the
   old test and fails the new one, healthy output passes both) and through TwinBoard where the twin runs the script.
2. CRr1's five named rows (flash test_bus_concurrency's chip-lost errnos exact; bench test_hotspot_role_reversal and
   test_network_resilience's allow-lists as an exact count of the provoked entry; two bench reads of the provoked entry
   before a clear; bench test_uart_link_under_api_load's `intact == total` that also passes on two missing facts).
3. CR4's item 3: tests/test_asy_bmp3xx_driver.py's bus-down-during-the-settle test, whose `run()` has no bound, so a
   reset() that never writes the soft reset hangs the file to its timeout: a bound, so the plant (soft reset written to
   the wrong register, in a scratch src copy) fails the test and the file finishes; 139-ish/139 at both stages.
4. CR3's unread question: does the boot after a commanded config reset log W CONFIG_LOST (flash test_system_commands
   near :117)? Read src/ and the twin; answer with source lines. If it does, it is A.U35.37 (a): a normal situation
   logging a warning, a product question for the lead with its evidence, never a test change.
CRr2b, the bench tier's log check (CR4's item 1, re-landed): an autouse `no_unprovoked_log_entry` fixture in
tests_hardware/bench/conftest.py (a GET /status before and after each test, clearing and writing nothing, failing on a
new E or W entry in any module, naming module, code and catalog name, and test); a `provokes_log("<reason>")` marker in
tests_hardware/markers.py's one table exempting a test, refusing a marker without a reason; the helpers in
error_log_helpers.py; the marker on each provoked test with its reason from the test's own comment or name (CR4: 50
tests, 21 bench and 19 flash of CR3's 40 provoked plus 10 bench outside the 99); CR4's hotspot deviation (per test,
through the gateway) re-checked; tests in tests_scripts, each seen failing first, and CR4's seven plants re-planted.
CRr2c, the flash tier's logs (CR4's item 2 plan): a `logs` fact helper, one call per device script naming its loggers,
`parse_facts()` collecting it, a flash autouse fixture honouring `provokes_log`; bites on synthetic output and through
TwinBoard; then hand the lead the scripts whose twin record changes (the lead re-records).

## Proof and checks
`--collect-only` of the whole tests_hardware tier and `--twin` runs of changed flash files, inside
`unshare -n S/u24/ns_xdg.sh`, nice 19, RUNS.md lines; changed MicroPython files at both stages with build-standard
directly, zero markers; lint with `S/u35/lead/lint_direct.sh`; the mypy passes (main pass covers device_scripts);
tests_scripts readers of changed files; the comment cap, test_citations, test_decision_vocabulary,
test_tunables_register, test_persistence_write_marker_completeness. test_twin_record stays red for changed hardware
files (the lead re-records at the close).

## Not yours
src/, toolchain/, digital_twin/, every allow-list (hand back the row you need), audit/ records other than the review
files. Commit subject `U35 lane CRr2<a|b|c>: <summary>`, the two trailers; do not push. Hand-back: commits; per row its
verdict or fix with its bite and log path; the counts from review_rows.py; the product question if any; last line
"nothing of mine is running".

## Shell discipline (binding, lead, 2026-10-27)
Run scripts you wrote to files (`bash <file>`, `python3 <file>`), never a `bash -c` holding rm or a nohup chain (a
safety check refused that form once); a deletion is its own command with a literal path; a refused command stops you.
A run killed at its timeout must not leave its interpreter running: start it in its own session and kill the group.

## Added for CRr2b (lead, 2026-10-27)
CRr2a2 (S/u35r/handbacks_redo/CRr2a2.md, "Open question") found
`test_isl29125_config_write_does_not_disturb_concurrent_sibling_reads` never proves the sibling reads overlapped an ISL
write: `isl_windows` is raw write timing and the sibling read windows are not recorded, so the "no disturbance" claim
can pass on reads that never overlapped. The lead's decision (test code, no wear): fix it with its goal kept - the
device script records each sibling read's window, and the host test asserts at least one read overlapped a write
window before it credits the "not disturbed" result; bitten on synthetic output (no overlap: old passes, new fails;
an overlap: both pass) and through TwinBoard if the twin runs it. Do this in CRr2b, first.
