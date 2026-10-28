# CRr2b2: finish the bench log check; the overlap gap in its two siblings (lead, 2026-10-27)
Read `S/u35r/briefs/redo_common.md` first, then `S/u35r/briefs/crr2_hardware_rows.md` (the task: CRr2b's block, its
proof, checks, "Not yours" and shell discipline all apply) and CRr2b's hand-back `S/u35r/handbacks_redo/CRr2b.md`.
Worktree `S/wt-u35crr2b`, branch `audit/u35-crr2b` at 59021b11 (clean). Logs in `S/u35/laneC/crr2b2/`; CRr2b's in
`S/u35/laneC/crr2b/` (bench_map.txt, mark_bench.py, plants.py: read before reusing).

## Items, in order
1. Undo one part of 59021b11: it re-sorted bench/conftest.py's existing functions into D.15 order. The D.15 question
   over the unchecked scopes is with the owner, and until it is answered nothing there is reordered. Restore the
   existing functions' base order (0dcc13d2), with the two new fixtures after them. Prove that only order changed: an
   AST comparison of each function's body against 59021b11.
2. CRr2b's "Left for the next agent" 1-4. For item 1, class every remaining bench test by reading src: provokes_log
   with its reason, or unmarked with the reason it leaves no E or W entry, in the map. CR4's count (21 bench of CR3's
   40, plus 10 bench outside the 99) is a checklist to re-find, not proof. A test that reboots the board or leaves it
   unreachable at its end: say what the after-read meets there. Make the fixture fail bounded and clearly in that case
   (logger read impossible, with the test named), never hang or raise a bare teardown traceback; a test of that,
   red first. Item 2 is the flash tests' markers only: the flash fixture is CRr2c's.
3. The overlap gap CRr2b found untouched, the lead's call (test code, no added write): the same fix as b63be1b6 in
   `bus_concurrency_scd30_write_vs_siblings.py` (its NVM writes unchanged in number and placement; say so with the
   script's write sites) and in the HTTP bench counterpart of the ISL test (re-locate it). Read
   `_shared/bus_reader_loops.py`'s window helpers first: if two or more scripts use `_overlapped()`, it moves there
   beside them (Part G reuse) and b63be1b6's copy goes. Bites as b63be1b6's (synthetic no-overlap output passes the old
   test and fails the new one; an overlap passes both) and through TwinBoard where the twin runs the script.

## Notes
Commit each item green on its own, subject `U35 lane CRr2b2: <summary>`, the two trailers; do not push. CRr2b's one
deviation (a `find -exec rm` in its plant setup) is the kind the shell rules forbid: deletions are their own command
with a literal path or "${var:?}". Past 80 tool calls, commit what is green and hand back at a seam. Hand-back: commits;
per item the evidence with log paths; the map's final counts (marked, unmarked with reason); the review_rows.py
counts; the scripts whose twin record changes; last line "nothing of mine is running".
