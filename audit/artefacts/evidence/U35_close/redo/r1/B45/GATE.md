# B4 + B5 gate on the merged integration head (lead, 2026-11-03)

The integration head 90691b6d carries B4 with its fix round (b8ed30e5, merge 450a52da) and B5 with its fix round
(60a88be1, merge 90691b6d; the one conflict, SPECIFICATION.md's teardown sentence, resolved per
`MERGE_B4B5_NOTES.md`), on top of 942ca477 (the wording fix), 1daa0fae (the Stull paper out) and a6047339 (the
datasheets pointer). One gate ran on 90691b6d (`gate_unit.sh`, 11:46-13:06 UTC):

| step | result |
|---|---|
| `scripts/test.sh`, GC -1 | MicroPython 137 files, 5,907 tests passed, 0 failed; `tests_scripts/` 7,111 passed, 0 failed |
| `scripts/test.sh`, GC 32768 | the same counts |
| twin suite and harness, GC -1 and 32768 | all four PASS (332 + 16 checks, 65 scenarios, 2 skipped as before) |
| `npm run lint`, `typecheck`, `test:unit` | PASS |
| lint (`lint_direct.sh`) and the three mypy passes | clean; no issues in 276, 314 and 59 files |
| memory markers | none in any output (the twin suite's 40 hits are its own "carries none of" lines) |

Against B2's gate: 120 MicroPython tests and 13 `tests_scripts` tests fewer, the pins of the removed mechanisms.

Sizes on 90691b6d (`sizes_90691b6d.tsv`): 28 modules, 15,819 lines, 198,243 B of bytecode. Against 942ca477
(205,681 B): -7,438 B (B4 -4,416, B5 -3,022 with its fix round's +16); only `asy_spi_driver.py` grows (+53 B, the
pre-audit `configure()` text). Against R0 (208,708 B): -10,465 B. dev's `imageFreeBytes`: 54,724 B on
90691b6d (`build/firmware-dev.json`; B2's 8019a9ef: 46,468 B, +8,256 B).

CI on snapshot 27 (41da2a61, run 41642287378): every non-dev twin suite job failed one check, Run 5c's "restored
history was actually cleared by ResetErrors" (`scripts/_digital_twin_ci_suite.py`): after the reset each SGP40 on FRAM
held its blank chunk's W SGP_NO_BACKUP (counter 1), its first restore after the commanded reboot landing after the
reset; on dev it lands before, so the local gate (dev only) passed. B4 restored that warning (item 13) and updated
Run 1 and the scenario harness, not Run 5c. Fixed in 6dc76d02: the check admits exactly that one warning for an SGP40,
counted once; checked against the CI entry (the old predicate fails it, the new one passes it for an SGP40 and fails it
for any other source), lint, the host mypy pass and the CI-suite rule tests (789 passed).
