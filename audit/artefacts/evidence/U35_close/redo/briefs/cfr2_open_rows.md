# CFr2: the planted-fault record's open rows (lead, 2026-10-27)
Read `S/u35r/briefs/redo_common.md` first, then `S/u35r/briefs/cfr_planted_faults.md` (the specification, the owner's
Question 2 ruling quoted there) and CFr's hand-back `S/u35r/handbacks_redo/CFr.md`. Base, worktree and branch named at
launch; logs in `S/u35/laneC/cfr2/`. Your base holds CFr's plant driver (audit/sweeps/plant.py, now starting each run
in its own session and killing the group on timeout; `plant.py selftest`) and audit/b3/faults.md. Update the rows there.

## Items, most important first
1. `src/asy_system_service.py` near :453-454, the line a cancel reaches (F1r's finding; CF1c item 6): CFr's draft test
   ("a cancel of the shutdown task before the supervisor stops ends the sequence there") HUNG inside its own run bound
   (its probe log is named in CFr's hand-back). Root-cause that hang before anything else: read the shutdown sequence
   and the cancel path in the pinned source and in src/, and decide with evidence whether the test was wrong or the
   product does not end its sequence on that cancel. A product defect goes to the lead at once with its evidence and a
   proposed red-first test, never into the test as an accommodation. Never call it a flake.
2. CF1b's three survivor fixes, lost and not redone by CFr (its "Open" list): the FRAM erase loop's yield
   (`test_erase_chip_lets_another_task_run_between_every_two_units`), the COBS decode loop's yield
   (`test_cobs_decode_lets_another_task_run_after_every_code_block`), the UART link's recovery window
   (`test_each_recovery_try_first_waits_one_window`), and the exact-bound survivor src/asy_isl29125_driver.py near
   :569 (a driven or frozen-clock test). Each red on its re-plant, green unplanted, zero markers, both stages.
3. K.25-mask-drop: a sequence row crosses its mask and asserts the wrap-safe comparison (audit/actions/U35.md
   A.U35.35's sequence-row shape), red on the plant.
4. `named.fram_alloc`: red at -1 but green at 32768, so the allocation-budget test misses a 16-byte per-call allocation
   at the threshold stage. Root-cause why (what the test measures, how a collection inside the window hides the bytes),
   then propose the fix to the lead before changing the measurement: CLAUDE.md forbids nonstandard gc settings in a
   test's setup that prop a result up, so a change to how the test counts allocations is the lead's to rule on.
5. A.U21.13's one-time unpatched modlwip control: CFr's `S/u35/laneC/cfr/modlwip_control.sh prep|build|test|clean`
   (read it before running it): the `make -n` check, one private compile in a tc-int copy, the test red as the control
   must be, the copy removed. Never the shared toolchain.

## Proof and checks
As the parent brief. Lint with `S/u35/lead/lint_direct.sh`. Shell rules (binding): every script you run is a file you
wrote first; never `bash -c` holding rm, never a nohup chain; rm only as its own command with a literal path or
`"${var:?}"` (CFr once used an unguarded `"$S"` glob: never); a refused command stops you. Commit subject
`U35 lane CFr2: <summary>`, the two trailers; do not push. Past 80 tool calls, commit what is green and hand back at a
seam. Hand-back: commits; per item its result with logs; item 1's root cause with source lines; item 4's proposal; the
updated counts; last line "nothing of mine is running".
