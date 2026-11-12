# CFr: the planted-fault record in the owner's scope, and the tests its survivors owe (lead, 2026-10-26)
Read `S/u35r/briefs/redo_common.md` first. Base, worktree and branch named at launch; logs in `S/u35/laneC/cfr/`.
This redoes lane C's CF1, CF1b and the never-launched CF1c (328c80d, 99fc7d3: lost). The map, not proof:
`S/u35r/recovered/handbacks/CF1b_final.md` (its scope, counts, 12 fixes, open items and the lead's note under it),
`S/u35r/recovered/lead_notes_119_148.md` (the CF1 line), `S/u35r/verify/V2.md` :81, V4.md row 138, V5.md N9/N11/N12.
Specification: audit/actions/U35.md A.U35.04 and A.U35.05 (Change lines), A.U35.35's K rows, audit/b3/faults.md's
header (its completion rule), and the owner's ruling, binding over every older scope (verbatim,
`S/u35r/recovered/owner_rulings_after_LN118.md`): "Question 2: I never required to plant faults for every test.
Planting faults is a good measure for complex measurement tests (e.g. memory exhaustion, leaks, long running
accumulating processes, multi layered or external dependencies, and similar), but not required for the straightforward
tests (which I would assume to be the majority by far). Planting errors for those straightforward tests would be
complete overkill."

## Items
1. `audit/sweeps/plant.py` (rewritten): one fault applied to a throwaway copy (under /dev/shm or S, never your
   worktree's tree, nothing kept, removed after each plant and checked removed), the named test file run on it at
   both GC stages with build-standard directly (or the named level's runner for a JS or host plant), red/green and the
   catching test recorded; a resume file so a stop loses nothing; a restore check that the source copy is unchanged.
2. The planted set, in the owner's scope: A.U35.04's named planting requests (its Change line's list); the generated
   boot entry's decisions (buildgen/codegen.py's template: each recorded reset path, the report, the loop end, the
   finally); every K row of A.U35.35 (two plants each: the cap's comparison flipped, the check dropped); A.U35.05's
   two plants per memory gate; and the seeded picks that are complex measurement tests by the owner's words, each
   named in faults.md with its reason. Every other module decision gets the row "not planted: straightforward logic"
   with the owner's ruling cited once in the method line. No widening beyond that scope (agent decision logged if any
   boundary case is unclear: the conservative reading is the owner's words).
3. `audit/b3/faults.md`: one row per fault (module, fault, site, catching tests, survivor -> action), terminal.
4. Survivors: a new or strengthened test in the permanent tree, goal kept, red on its re-plant, green unplanted, zero
   memory markers at both stages. CF1b's 12 fixes are a checklist to re-find (their test names are in its hand-back);
   a fix already in your base is "found landed" with its line, not redone.
5. CF1c's items: (1) the exact-bound survivors src/asy_isl29125_driver.py near :569 and src/asy_neopixel_driver.py near
   :184 (the notification one is in the tree since F2r: confirm), each with a driven or frozen-clock test; (2) the tests
   caught only by the file timeout because their wait has no bound (CF1b names three: give each a run bound so the
   plant fails the test, not the file); (3) `named.pair_scan` retargeted to the renamed check
   tests_scripts/test_fault_or_warning_never_both.py (audit/consolidation/M_TSC.md M.TSC.111) and re-planted;
   (4) `named.fram_two_entries`: its requirement is dropped by OR140.a (7) (audit/actions/FOLD_BRIEF.md F11): the row
   says so; (5) A.U21.13's one-time unpatched modlwip control: in a private toolchain copy (`cp -a S/tc-int
   S/tc-cfr`, disk check first, deleted after), after a `make -n` check that nothing outside your BUILD and overrides
   directory is written, then tests/lwip_host/test_modlwip_eagain.py on it, red as the control must be; never the
   shared toolchain; (6) `src/asy_system_service.py`'s cancel-reachable line near :441 (F1r's finding): its direct test
   if the tree lacks one; (7) the uart driver test near tests/test_asy_uart_driver.py:2319 renamed for what it asserts.
6. K.10's planting rule (SPECIFICATION.md K.10) restated with the owner's scope: hand the sentence back for D3.

## Proof and checks
Each changed test file at both stages with build-standard directly, zero memory markers, times against the base table
(CHECKLIST 14: growth over 10 % and 0.5 s is made efficient, never by cutting strictness). ruff, the mypy passes
(stubs at `S/shared/typings`), the comment cap, test_citations, test_decision_vocabulary, test_tunables_register, every
tests_scripts reader of a changed file. No scripts/test.sh or twin CI against the shared toolchain. Other lanes run:
nice 19, keep CPU modest (one plant run at a time). Past 80 tool calls, commit what is green at a seam (plant.py and
the record first, then the fixes) and hand back the rest.

## Not yours
src/ (plants only in throwaway copies), toolchain/, digital_twin/, every allow-list (hand back the row you need),
audit/ records other than faults.md and your plant scripts. A product defect a plant shows goes to the lead with its
evidence (OR12.a), not into a test. Commit subject `U35 lane CFr: <summary>`, the two trailers; do not push.
Hand-back: commits; counts (rows, planted, biting, fixed, equivalent, open, not planted); each fix with its re-plant
red and log path; the modlwip control's result; the D3 sentence; last line "nothing of mine is running".
