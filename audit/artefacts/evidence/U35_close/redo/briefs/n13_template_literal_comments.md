# N13: comments inside a template literal's `${...}` hidden from the repo scans (lead, 2026-10-27)
Read `S/u35r/briefs/redo_common.md` first, then N12's hand-back `S/u35r/handbacks_redo/N12.md` (ITEM 2 and its NEW
finding). Base, worktree and branch named at launch; logs in `S/u35/laneN/n13/`. Test and tool code only: no src/ or
js/ change, no wear.

## The find
tests_scripts/_repo_scan.py `_slash_blocks()` treats a template literal (backtick) as one string from its opening to its
closing backtick, so the code inside a substitution `${...}` is never read: a `//` or `/* */` comment there is invisible
to every scan built on `prose_blocks()`. Three are hidden today, all `/** @type */` casts:
scripts/cross_browser_smoke.mjs:390, tests_js/_live_matrix_command.js:164, tests_js/_live_twin_command.js:173 (N12's
lines on its base; re-locate them). The same blind spot also hides a regex literal or a string inside the substitution
from the quote and regex logic.

## Items
1. Prove it first: tests in tests_scripts/test_repo_scan_regex_literals.py (or a sibling file, your call) where a
   comment inside `${...}` is found (red on today's code), with nesting (a template inside a substitution inside a
   template; a `}` inside a string or a regex inside the substitution; an object literal's braces inside it) and the
   negatives (`${` inside a plain string, an escaped `\${` in a template, a `$` not followed by `{`).
2. The fix: the reader keeps a stack of open templates and, inside a substitution, reads code exactly as at top level
   (comments, strings, regexes, nested templates) until the `}` that closes it at depth zero. Planted bites, each
   failing its guard (the stack dropped, a `}` in a string closing the substitution, the escape ignored).
3. Compare against espree's real parse as N12 did (its tools in `S/u35/laneN/n12/`: espree_comments.mjs,
   compare_ground_truth.py; read them before reusing them): the missed count before and after (N12 ended at 3).
4. Run every repo scan that uses prose_blocks over the tree and report each comment seen for the first time and what
   the scans say about it (a new finding goes to the lead, never allow-listed).

## Proof and checks
Lint with `S/u35/lead/lint_direct.sh`; the host mypy pass; test_comment_block_cap, test_citations,
test_decision_vocabulary, test_code_conventions and every tests_scripts reader of _repo_scan.py, in the namespace. No
scripts/test.sh run needed. Shell rules (binding): scripts as files you wrote, never `bash -c` holding rm, never nohup
chains, never a `tail --pid` wait, rm only as its own command with a literal path or "${var:?}", a timed-out run's
children killed; a refused command stops you. Commit subject `U35 lane N13: <summary>`, the two trailers; do not push.
Hand-back: the commit; each red and green with log paths; the bites; the espree counts; new sightings; last line
"nothing of mine is running".
