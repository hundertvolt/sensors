# Merged head's gate: B3 (storage) + B6 (UART)

Run by the lead, alone on the host, through `S/u35/lead/run.sh`, in two parts (each under the 2 h background bound).
Script: `tools/gate.sh` (not in the snapshot). Toolchain `tc-int`.

## Part a: aa6119c1 (17:46-19:03 UTC)

| Step | rc | Result |
| --- | --- | --- |
| lint (`lint_direct.sh`) | 0 | clean |
| mypy main / twin | 2 | not run: the script had no typings link ("not a valid typeshed"); re-run below |
| mypy host | 0 | no issues |
| `scripts/test.sh` (gc -1) | 1 | 5,862 MicroPython green (L1, L2 PASS); tests_scripts 7,106 passed, 5 failed |
| `GC_THRESHOLD=32768 scripts/test.sh` | 1 | the same five failed; everything else green |
| dev twin suite, gc -1 / 32768 | 0 / 0 | PASS |
| dev twin harness, gc -1 / 32768 | 0 / 0 | PASS (65 scenarios, 2 skipped, each stage) |

The five: every case of `test_run_3_bounds_every_fram_write_the_product_issues_landed_or_silent`, on a refused
connection. B3's fix 0f5cbaf7 made Run 3 read `/status`; the test stubbed spawn and serve, not that read. Memory
markers: the log's 80 hits are all the twin's own "log carries none of" OK lines. `ss: command not found` after the
twins is the namespace lacking `ss` (a diagnostic print; rc 0).

Fix b5cd0252 on audit/r1-b3 (stub plus two cases: a FRAM-backed logger adds one setup attempt, FRAM's in-memory log
none), merged as **d6bc7617**. On d6bc7617 (19:07-19:08, `checks.sh`, typings linked): lint 0; mypy main, host and
twin no issues; `tests_scripts/test_digital_twin_ci_suite_errcount.py` 134 passed. The rest of part a stands for
d6bc7617: the merge changes that one test file only.

## Part b: d6bc7617 (19:08-19:32 UTC)

| Step | rc | Result |
| --- | --- | --- |
| wozi twin suite, gc -1 / 32768 | 0 / 0 | PASS, 308 checks each |
| `pytest --collect-only tests_hardware` | 0 | 203 of 234 collected (31 deselected by the opt-in gates) |
| npm lint / typecheck | 0 / 0 | clean |
| npm unit | 0 | 26 files, 1,340 tests passed |
| sizes (`module_sizes.sh`, `sizes/head.tsv`) | 0 | below |
| `scripts/build_firmware.py dev` | 0 | 1,170,932 B of 1,228,800 B, **57,868 B free** |

Memory markers: the log's 74 hits are all "log carries none of" OK lines.

## Sizes

`src/` bytecode **195,511 B** at d6bc7617, 15,600 lines, against 198,243 B and 15,819 lines at 90691b6d: -2,732 B, the
sum of B3's -1,652 and B6's -1,080 measured alone; against R0's 208,708 B, -13,197 B. Per module: FRAM driver 5,554 to
4,669 (-885), FRAM manager 11,638 to 10,950 (-688), CRC 1,879 to 1,876 (-3), SPI driver 2,073 to 2,028 (-45), system
service 10,513 to 10,482 (-31), UART comm 14,843 to 14,053 (-790), UART driver 7,727 to 7,546 (-181), UART link 3,666
to 3,648 (-18), base classes 10,310 to 10,219 (-91). No module grew. The dev image's free space 57,868 B, +3,144 B
against the previous snapshot's 54,724 B.

## CI on snapshot 29 (10af8c6c, run 41705178692) and the fix

29 of 30 jobs green. `unit-tests-coverage` failed one test: `tests/test_asy_system_service.py`
`test_erase_fram_zeroes_every_byte_and_reboots_with_code_8`, "MemoryError: memory allocation failed, allocating 262144
bytes" (the 2 Mbit fake chip's memory). Locally the file passed under build-settrace at 16 MB; at 12 MB it failed 15
tests on 8 KB chips, at 10 MB 24, and the pre-B3 file (B6's tree) failed 5 at 12 MB and 15 at 10 MB: the file sat near
the heap's limit before this merge, and the merge spent the last margin.

Root cause, measured with a scratch probe (microtest's own run, the live heap after each test's after-each reset and a
collection): the live heap grew from 423,744 B to 4,878,624 B over the 187 tests; the erase test alone kept 643,008 B.
`_SEQUENCES` (`tests/test_asy_system_service.py:104`, from B2's 8019a9ef) holds each service's shutdown-sequence
tracker keyed by `id(svc)`, and nothing cleared it, so every service, rig and fake chip outlived its test (and a
reused `id()` could hand a later service a stale list). No other module-level container in `tests/test_*.py` grows
per test (the twin link lists are reset per build or filled once).

Fix **d922323b** on int: `microtest.after_each(_SEQUENCES.clear)`, as `test_asy_webserver_service.py:114` does for its
parse cache. After it: the live heap 423,648 B at the first test, 500,672 B at most, 498,112 B at the end; the file
187/187 under build-settrace at 16, 10 and 4 MB, and under build-standard at -1 and 32768; lint, the three mypy passes
and `test_comment_block_cap.py` (657) green.

## CI on snapshot 30 (23297252, run 41712336673) and its fix

`unit-tests` and `Unit tests (shipped gc.threshold)` failed (the twin jobs, which wait on them, were skipped): every
MicroPython test passed (5,868), and one tests_scripts test failed in each. d922323b had moved `import microtest` to
the top and dropped it from the `__main__` block, and `tests_scripts/test_microtest.py`
(`test_every_test_file_ends_with_the_canonical_trailer_and_binds_only_functions`) pins that block in every test file:
checked by parsing the snapshot-30 file (not canonical) and the fixed one (canonical). The lead had run only
`test_comment_block_cap.py` from tests_scripts for d922323b; the whole tier is the check for a test-file change.
Fix **a97ec884**: the trailer back as it was, the top-level import kept (as `test_asy_webserver_service.py` has both).
On it: lint, the three mypy passes and the whole tests_scripts tier (7,113 passed, 6 skipped) green.
Snapshot 31 (f625b077): CI green, run 41716670309 (pull_request, 20:53-21:28 UTC), the twin and coverage jobs included;
the push run 41716654193 was cancelled by the newer run of the same sha. B3+B6 are closed.
