# UM2: the UART catches (owner's option C), and the dev echo's allocation (lead, 2026-10-27)
Read `S/u35r/briefs/redo_common.md` (all of it; its "Efficiency" section is binding and says how you hand back),
then `S/u35r/handbacks_redo/UM1.md` (the facts, the sites, option B/C's list of what changes). CLAUDE.md's UART
hard rules apply: the two-implementation contract, UART_C_PORT_CHANGELOG.md's classes, the never-block rule. Never
read `arduino/`. Worktree `S/wt-u35um1`, branch `audit/u35-um1` at ad624cca (UM1's three tests on 5a8c6e35; clean,
rebuilt). Logs in `S/u35/laneB/um2/`.

## The owner's decision
"Do option (c) as you recommended" (owner, 2026-10-27). Option C, from UM1.md: catch PieceBuffer's MemoryError at
asy_uart_comm.py's GET (initiator, :278) and SET (responder, :313) sites with the protocol's own fault flow
(`_fault(_ERR_ALLOC)` as before the 2026-10-05 change, None or `ListenResult(None, CMD_SET, None)`, the resync and
re-listen rules), the caught text printed so the memory gates see it (the B80/B81 precedent); and at
asy_uart_driver.py's `readline_until_complete` (:660) with a None return, as that file's other read paths do.

## Items, in order (each committed green on its own)
1. The fix, red first: UM1's three tests flip into the fix's red-first tests (each red on ad624cca, green after).
   UART_C_PORT_CHANGELOG.md: one Class A entry (receiver side, no byte emitted differently, the recovery timing
   restored) for the two protocol sites and one Class B entry for readline. The docs: SPECIFICATION.md G.2, J.8,
   I.2, asy_base_classes.py's PieceBuffer comments (:7-8, :180 per UM1), a note at B64; asy_uart_link_driver.py:133's
   "never raises out" made true or corrected. Decision tags "(owner, 2026-10-27)" where the owner decided.
2. The dev echo's single allocation of up to 12,192 B (asy_uart_link_driver.py:112), under CLAUDE.md's memory rule
   (design first: chunking, reuse, streaming; a threshold or a catch is never the fix). Measure first: what it
   allocates, when, how often, the largest free block at that moment in the twin (both stages). Then either show
   it is a bounded, placeable one-off with numbers, or build the design-level fix with its test. It is bench-only
   application logic, but it is src/ code under the same rule. An owner question, if one arises, in prose.
3. Checks on the head: every test file importing asy_uart_comm, asy_uart_driver or asy_uart_link_driver at both
   stages (PER_DEVICE files on all six devices), zero memory markers; lint_direct, the six mypy passes, the
   readers, the three audit checks (walk, e51, review_rows; the six BR4 rows may still be red, name them only).
4. Seams: at about 80 tool calls, commit what is green and hand back with what is left.

## Hand-back (the file, per redo_common)
Commits; per site the red and green; the changelog entries; the docs changed; the echo's measurement and verdict;
the checks; last line "nothing of mine is running".
