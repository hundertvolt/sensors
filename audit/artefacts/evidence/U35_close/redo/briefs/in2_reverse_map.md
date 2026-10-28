# IN2: every test function reaches an intent row (the reverse map), and the lwip_host tests get review rows (lead, 2026-10-28)
Read `S/u35r/briefs/redo_common.md` (all of it; "Quality comes first" and "Efficiency" are binding, and it says how
you hand back). Then:
- `S/u35r/handbacks_redo/INLV.md` in full, above all "The reverse map (OR25.a (2)): held for the lead" and its proposed
  method;
- `S/u35r/briefs/inlv_intent_levels.md` item 6 (the rule: tied or classed; never removed in-lane);
- on your worktree: `audit/b3/levels_walk.py` (how a cell reaches a test function, the superset proof, `--dump`),
  `audit/b3/intent.md`, `audit/b3/levels.md`, `audit/b3/levels_data.json`, `audit/sweeps/redflags.py`,
  `audit/sweeps/review_rows.py` and `audit/sweeps/review_verdicts.json`.

Worktree and base: in your launch message. Logs go in `S/u35/laneB/in2/`.

## The state
On the integration head the walk reports 0 gaps and every intent, schema and integration row biting. However, 1204
test functions are reached by no row: host (pytest) 723, unit 270, flash 59, web 58, bench 47, manual 21, device
scripts 20, twin 6. Separately, `redflags.py` skips `tests/lwip_host/` (13 test functions in two files), so
`review.md` has no row for them.

## The lead's decision on the method (agent, 2026-10-28)
IN+LV's four steps are taken, in order, with these conditions:
1. **Follow helpers across files.** A test reaches a subject through a helper (`tests/_*.py`, `tests_scripts/_*.py`,
   `conftest.py` fixtures, `tests_js/_*.js`) only when that helper's own code drives the subject: an import alone
   reaches nothing.
   - The walk's superset proof is restated for the widened cells and checked both ways: every old cell lies inside its
     new cell, and every widening names the helper that carries it.
   - Bite: a planted helper that imports the subject but never calls it widens nothing.
2. **Rows for the test infrastructure the tiers test:** the fakes and helpers in `tests/`, the `tests_hardware/*.py`
   harness, the `tests_scripts/_*.py` and `tests_js/_*.js` helpers, `html/`, `devices/*.toml`,
   `buildgen/error_catalog.json`, and the CI suite's runs.
   - These go in their own section of levels.md (and intent.md if they get intent rows), so the product rows' counts
     stay as they are and are reported apart.
3. **Cross-file invariant rows for the repo-wide L0 scans:** the comment cap, citations, decision vocabulary,
   suppression form, conventions, tokens and their kind.
   - Recognise them mechanically: a scan globs a scope root and names no single subject. List what the rule caught.
   - Bite: a scan that names one subject file is not counted as cross-file.
4. **Tie what remains by hand,** each with its row. Or class it with a reason (for example, a test of the test
   runner's own contract).
   - A test you judge redundant is listed with the test that makes the same assertion on the same path, for the lead.
     Never remove a test in-lane.
   - The target is zero unreached. Report each tier's count after every step.
5. **The lwip_host rows:** `redflags.py` covers `tests/lwip_host/`, and each of its 13 test functions gets a verdict.
   Read each test with its subject, as the review's other rows were read, and add a bite where one is owed. Re-render
   with `review_rows.py`; `--check` must be 0.

## Checks
- `levels_walk.py` on your head, with its superset proof and the new step-1 and step-3 bites;
- the readers of the changed records;
- review_rows `--check`, walk and e51;
- lint_direct and the six mypy passes if any Python changed;
- any test file you change, at both stages, with zero memory markers.

## Notes
- No src/ change. A product finding goes to the lead with its evidence.
- Other lanes add tests while you work. The lead re-runs the walk at the merge, so keep the walk mechanical and keep
  hand-ties in data (`levels_data.json`), not in prose.
- Run to the end; hand back early only as redo_common says.

## Hand-back (the file, per redo_common)
- Commits; each step's per-tier counts before and after; the helpers each widening names; step 3's list.
- The hand-tied and classed tests; any redundant pair; the lwip_host verdicts; the checks.
- Last line: "nothing of mine is running".
