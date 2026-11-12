# B2 gate on the merged integration head (lead, 2026-11-03)

The integration head carries B2 with its falsification fixes (2970ff9e), plain `err()` (merge fc4335ec) and the dropped
re-check (3129bf21). One gate ran on 3129bf21 (`gate_unit.sh`, 07:07-08:17 UTC):

| step | result |
|---|---|
| `scripts/test.sh`, GC -1 | MicroPython 137 files, 6,027 tests passed, 0 failed; `tests_scripts/` 7,124 passed, 1 failed |
| `scripts/test.sh`, GC 32768 | the same counts, the same one failure |
| twin suite and harness, GC -1 and 32768 | all four PASS |
| `npm run lint`, `typecheck`, `test:unit` | PASS |
| memory markers | none in any output (the twin suite's 40 hits are its own "carries none of" lines) |

The one failure: `tests_scripts/test_decision_vocabulary.py` flagged six sentences from the falsification fixes that said
a reset "is decided" (SPECIFICATION.md twice, one source comment, three test comments). Root cause: the fix commit's runs
took a chosen `tests_scripts` subset (1,836 tests, `HANDBACK.md`) without that test, and this gate is the first whole
run after it. Fixed in 942ca477 by rewording them to "due" and "commits to"; comments and
docs only, no bytecode change. Re-checked on 942ca477: the vocabulary and comment-cap tests (663 passed), lint clean,
`tests/test_asy_system_service.py` 192/192 at both GC stages. B4 and B5 were told the failure is base-known.

Sizes on 942ca477 (`sizes_942ca477.tsv`): 28 modules, 16,400 lines, 205,681 B of bytecode. Against B2's 8019a9ef
(205,832 B): -151 B (plain `err()` -143, the dropped re-check -8). Against R0 (208,708 B): -3,027 B. dev's
`imageFreeBytes`: 46,468 B at 8019a9ef; CI's build log does not print it and the local build waits on the toolchain
lock, so the merged head's figure comes with the next merge's gate.

CI on snapshot 26 (22477130, run 41603196565): all 46 jobs green (the 16 cancelled are the superseded push run).
