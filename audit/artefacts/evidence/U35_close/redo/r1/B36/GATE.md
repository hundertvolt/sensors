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
