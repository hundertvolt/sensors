# T4r2d: fold (1) with its send-buffer knob, then the UART load plant (lead, 2026-10-26)
Read `S/u35r/briefs/redo_common.md` first. Base, worktree and branch named at launch; logs in `S/u35/laneT/t4r2d/`.
The fourth block of T4r2: read `S/u35r/briefs/t4r2_twin_scenarios.md` in full; its item 3's fold (1), its item 5 and
its "Proof and checks" and "Not yours" sections are your brief, unchanged. Folds (2) and (3) and item 4 are done (the
hand-backs `S/u35r/handbacks_redo/T4r2b.md` and `T4r2c.md`; T4r2c's runner flag `--test-defer-faults` is the pattern
for a new twin knob: a TestFlags field, the usage text, the README row, tests_scripts/test_twin_runner_test_flags.py's
flag table row, knob tests red first).

## Fold (1) facts (T4r2c's; re-check each)
No SO_SNDBUF knob exists. Accepted sockets come from `asyncio.start_server(self._serve, ...)` (src/asy_webserver_
service.py near :978), so a scenario-scoped knob (off by default, set only by this scenario) wraps the accept or the
stream inside a runner `_test_` function, never in src/. Check first whether the Unix port's `socket` module defines
`SO_SNDBUF` (`/root/pico-toolchain/micropython`, read-only) and what Linux's floor for SO_SNDBUF is (`man 7 socket`;
the kernel doubles the value and clamps to its minimum): the knob's effect on the accepted socket must be read back and
asserted in its own test. The scenario asserts the largest GET body exceeds the pinned buffer before it relies on a
mid-write reset; it skips (UnmetPremiseError, T4r2b's) only if no body does. `HTTPDropped` comes from
buildgen/codegen.py near :284 and src/asy_webserver_service.py near :592/:1045; `_WRN_HTTP_PEER_RESET` = 48.

## Item 5
`_UART_LOAD_REQUEST_S`: scripts/_digital_twin_scenarios.py near :156, used near :2045, :2052, :2068.

## Notes
The scenario runs need a private toolchain copy (`cp -a S/tc-int S/tc-t4r2d`, disk check first, keep 3 GB free,
deleted after). Lint with `S/u35/lead/lint_direct.sh`. Commit each item green on its own; past 80 tool calls hand back
the rest at a seam with its facts. Other lanes share the 4-core host: nice 19, one run at a time.
