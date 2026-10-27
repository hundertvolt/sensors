# N11: the real-time waits in tests/ that carry no tunable tag; one vacuous budget check (lead, 2026-10-27)
Read `S/u35r/briefs/redo_common.md` first. Base, worktree and branch named at launch; logs in `S/u35/laneN/n11/`.
Sources: N10's hand-back `S/u35r/handbacks_redo/N10.md` (item 2: 176 untagged sites in 31 tests/ files, 96 in five
false-positive classes, about 80 possible real waits in 23 files, about half real by its spot check) and its scan
tools and outputs in `S/u35/laneN/n10/` (tools/untagged_waits.py, classify_waits.py, item2_scan.txt,
item2_classes.txt); CFr2's hand-back `S/u35r/handbacks_redo/CFr2.md` item 4; SPECIFICATION.md N.1 (the classes) and
N.2 (row form, per-file counts). The lead decided (CHECKLIST 1d: test-only, no wear) that every real-time wait gets
its tag in U35 (N.1: a value waited out in real time is tuned). Test and register text only: no src/, no wear.

## Items
1. Re-run N10's scan on your base (read its tools first). Every one of the ~80 candidates read and classed by N.1:
   tuned (waited out in real time: a per-call timeout or cap a case can wait out, a hang bound, a real sleep or
   wait, a cycle count that sets real run time) -> a module constant per value and role in its file's constant block
   with its `# @tunable l1.<file-stem>_<role>` tag (or l2 for twin files) and its Part N row, Basis measured (an
   instrumented scratch copy, both stages, build-standard, slowest observed against the bound) or estimated with the
   measurement owed; an equal-valued existing tagged constant of the same role reused instead of a new one; test input
   (fed only to a fake, a constructor or validator, never waited out) -> no tag, its class named in your hand-back.
2. Per changed file: the AST identical once each new constant is substituted back (N8's and N10's comparison tool);
   the file green at both stages, zero markers, base and head timed back to back; test_tunables_register green and red on
   a scratch copy with one new tag deleted.
3. tests/test_asy_fram_allocation_budget.py's `allocated == consumed` check (CFr2 item 4): CFr2 measured
   `gc.mem_alloc() + gc.mem_free()` constant in every window, so the check is an identity that can never fail. Show
   that yourself (a probe), then remove it, and state in one comment line beside the budget that its bite is the
   -1 stage's (at 32768 a collection inside the window frees its garbage). No gc call is added anywhere (the
   gc-threshold-window option is the owner's question, not yours).
Order: item 3 first (small), then the files by candidate count; commit per file group green; past 80 tool calls hand
back the rest at a seam with the remaining list.

## Proof and checks
Lint with `S/u35/lead/lint_direct.sh`; the mypy passes (stubs at `S/shared/typings`); the comment cap, test_citations,
test_decision_vocabulary, test_tunables_register, test_code_conventions, every tests_scripts reader of a changed file.
Shell rules (binding): scripts as files you wrote, never `bash -c` holding rm, never nohup chains; rm only as its own
command with a literal path or "${var:?}"; a refused command stops you. nice 19, one test run at a time.

## Not yours
src/, toolchain/, digital_twin/, audit/ records, every allow-list (hand back the row you need). Commit subject
`U35 lane N11: <summary>`, the two trailers; do not push. Hand-back: commits; per candidate its class and tag or
reason; the AST comparisons; the measured Basis values; times; last line "nothing of mine is running".
