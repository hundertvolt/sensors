# CEr1: one coverage run on the merged head, every uncovered src line classed (lead, 2026-10-27)
Read `S/u35r/briefs/redo_common.md` first. Base, worktree and branch named at launch; logs in `S/u35/laneE/cer1/`.
This redoes lane E's CE and CE3 (e592fff, 0f9dbed, d255632; lost). The map, not proof: `S/u35r/recovered/handbacks/
CE3_final.md` (its 35 rows: 30 tested, 5 re-classed unreachable, its plants), `S/u35r/recovered/lead_notes_119_148.md`
(the CE line: audit/sweeps/e51_sweep.py, audit/b3/e51.md, e51_verdicts.json), and F1r's library-rule reading in
`S/u35r/handbacks_redo/F1r.md`. Specification: audit/actions/U35.md A.U35.41 (the verdict table and the convention:
"A branch no input can reach is removed. It stays only as a guard of an overridable extension point or of a documented
runtime failure ... exercised through a double ... or, when no test can provoke it, listed in E.5.1 with its reason")
and A.U35.04's coverage rule; audit/b3/e51.md's header (its completion rule). The owner's rule on dead code is binding
over every older verdict (verbatim, `S/u35r/recovered/owner_rulings_after_LN118.md`): "Dead code: Double check it's
really dead code. I don't want real features or sensible functionalities removed which could be worthwhile in future
use. Always regard the modules as libraries, not every feature must be immediately used, as long as it is a real
feature."

## Items
1. One `scripts/test.sh --coverage` run on your base, through a private toolchain copy (`cp -a S/tc-int S/tc-cer1`,
   `PICO_TOOLCHAIN_DIR=S/tc-cer1`, disk check first; never the shared toolchain), inside `unshare -n S/u24/ns_xdg.sh`,
   nice 19, RUNS.md lines, run in the background with its own time bound (it takes about 25-40 min; the tool's own
   background limit is 30 min unless you set a longer one). Since CE2r, a tracer that ends early leaves a note and the
   run exits 3: any note is a finding to report, never ignored. Its JSON/XML outputs are your input.
2. `audit/sweeps/e51_sweep.py` (rewritten; `python3 -I`): every src/ line the run did not execute, grouped by site, each
   with its enclosing function and the condition that reaches it.
3. `audit/b3/e51.md` and `audit/sweeps/e51_verdicts.json`: one terminal row per uncovered site, classed:
   (a) reachable and untested -> a direct test owed (the next block writes it; name the input that reaches it);
   (b) a guard of an overridable extension point or a documented runtime failure -> kept, exercised through a double
   (owed test) or registered untestable with its reason;
   (c) a type-narrowing re-check -> kept, stated in place;
   (d) a real feature not yet used by the product (the owner's library rule) -> kept, its feature named, tested by a
   direct test if it has none;
   (e) truly unreachable and not a feature or guard -> a removal proposal to the lead with its proof (never removed by
   you; the owner's rule says double check).
   CE3's 35 rows are a checklist to re-find (their sites re-located), with its three unreachable proofs re-checked and
   F1r's and the lead's later readings applied: uart_driver's three `if not want:` kept as the never-block guard,
   scd30's session-shared line kept, system_service's `return` near :453-454 kept as a safety guard (CFr2's proof that
   no cancel reaches it, `S/u35r/handbacks_redo/CFr2.md` item 1), the ISL lines kept as features, webserver's two kept.
4. The E.5.1 register text (SPECIFICATION.md E.5.1, only what stays, one line each with its reason) handed back as a
   proposed text for D3r, plus the Part E convention paragraph if E does not already hold it.
5. CRr2a's find (S/u35r/handbacks_redo/CRr2a.md item 3): CE3's lost bmp3xx test ("the bus goes down between reset()'s
   two sessions") and its run bound belong to the owed-test list.

## Proof and checks
The sweep's own tests (a scratch coverage JSON with known lines) red first; lint with `S/u35/lead/lint_direct.sh`;
test_citations, test_decision_vocabulary. Shell rules (binding): scripts as files you wrote; never `bash -c` holding
rm, never nohup chains, never a `tail --pid` wait chained with other commands; rm only as its own command with a
literal path or "${var:?}"; a timed-out run's children killed; a refused command stops you. Delete S/tc-cer1 when done.

## Not yours
src/ (no removal, no test in this block), toolchain/, digital_twin/, every allow-list. Commit subject `U35 lane
CEr1: <summary>`, the two trailers; do not push. Hand-back: commits; the run's result and any tracer note; per class
the count and the rows; the removal proposals with proofs; the owed-test list (site, input, test file); the E.5.1 text;
last line "nothing of mine is running".
