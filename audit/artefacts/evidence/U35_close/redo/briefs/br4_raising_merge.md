# BR4: the raising lanes merged, rendered and checked (lead, 2026-10-27)
Read `S/u35r/briefs/redo_common.md` (all of it; its "Efficiency" section is binding and says how you hand back),
then `S/u35r/briefs/br1_raising_calls.md` (the walk's rules), then the hand-backs `S/u35r/handbacks_redo/BR1.md`,
`BR1b.md`, `BR2.md`, `BR3.md` (only their commits, checks, reds and notes for the lead). Worktree `S/wt-u35braise4`,
branch `audit/u35-braise4` at the integration head 5a8c6e35 (clean, rebuilt). Logs in `S/u35/laneB/br4/`.

## The lead's review (binding)
- All four lanes' commits are kept: BR1 651d3e79, 5023bcf7, 32a62f28 and BR1b b8c28a07..c942fef2 on audit/u35-braise;
  BR2 ad1fae73..1f5c555b on audit/u35-braise2 (three asy_system_service.py fixes); BR3 7ceb50b2, 396ab96d, acebee6d
  on audit/u35-braise3 (the FRAM chunk-read copy fix).
- The lead's decisions (agent, 2026-10-27): the walk renders each verdict file's "conventions" key into raising.md; a
  lambda is its own scope in the walk (it runs outside the enclosing try, BR1b point 4, BR2's note); the coverage
  hits of the moved src lines come from a fresh build-settrace run on the merged tree, not a remap.

## Items, in order (each committed green on its own)
1. Merge the three branches onto 5a8c6e35 (`git merge --no-ff`, one per branch). Generated files (raising.md, the
   e51 block, review.md) are never hand-resolved: take either side and re-render with the tools.
2. The walk: give a lambda its own scope; render the "conventions" key. Re-walk over the merged JSON; every group
   is terminal, the transitive groups BR2 and BR3 left resolve against BR1/BR1b's verdicts, or name each that does not.
3. The e51 hits for asy_system_service.py and asy_fram_manager.py: a fresh coverage run of their test files on the
   merged tree (`scripts/test.sh --coverage` mechanics, private toolchain copy per redo_common), the hits re-dumped.
   Compare with BR3's remap and say whether it matched. `e51_sweep.py --check` green.
4. `review_rows.py --check`'s flag on BR2's test_a_raising_preflight_leaves_the_gate_as_a_refusal_does: establish
   the scanner's real cause (the test does not call `_retire()`), then the verdict row with its reason. Also the six
   flagged rows with no verdict that came in with the CMr1 merge (clock_jump x2, hot_replug, ntp x2,
   tests_scripts/test_twin_wiring_contract.py; lane CO2 found them): each its verdict with its reason, read from
   the test, under review.md's flag definitions. Then the render is refreshed and `--check` is green.
5. Design-first check on BR3's fix (CLAUDE.md memory rule): list every production caller of FRAMChunk.read() and
   FRAMTimestampedChunk.read() with its chunk size. A caller that allocates on a repeated path where read_into()
   would serve is a finding (hand it back with numbers, do not change it); a one-time or small fixed copy is fine.
6. Checks on the final head: the walk, e51 and review_rows `--check`; the readers; lint_direct; the six mypy passes;
   every test file importing asy_system_service, asy_fram_manager or asy_fram_driver at both stages (PER_DEVICE
   files on all six devices), zero memory markers.

## Hand-back (the file, per redo_common)
Commits; rows by verdict per module after the merge; the transitive groups' fate; the coverage comparison; the
review_rows cause and verdict; item 5's callers; the checks; last line "nothing of mine is running".
