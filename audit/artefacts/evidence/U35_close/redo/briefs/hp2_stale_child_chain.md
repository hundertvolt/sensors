# HP2: does the stale `child_last` pin a growing chain on the product's own task patterns? (lead, 2026-10-27)
Read `S/u35r/briefs/redo_common.md` (all of it; its "Efficiency" section is binding and says how you hand back),
then HP1's hand-back `S/u35r/handbacks_redo/HP1.md` (the mechanism, the probes in `S/u35/laneB/hp1/`, the uctypes
read of a Task's words). Worktree `S/wt-u35hp1`, branch `audit/u35-hp1` at 5a8c6e35 (clean). Logs in
`S/u35/laneB/hp2/`. Probes stay scratch copies outside the worktree, as HP1's did.

## The lead's review of HP1 (binding)
- Kept: restarts do not leak; the ntp test's 147 KB step is the test linking its boots (fixed test-side elsewhere).
- The lead re-read the pinned v1.29.0 source: `child_last` is written only in meld and delete (py/pairheap.c:52, :59,
  :144) and never cleared where `child` is set to NULL (pairheap.h init_node and pop, pairheap.c delete). So every
  node popped with children keeps a pointer to a node popped later, and a finished task pins its last child.
- What HP1 did not measure: those pointers can chain forward in time (X pins Y, popped after X; Y pins Z, popped
  after Y), so a live task that waits outside the queue for long (an accept loop, an Event wait) may pin a chain
  that grows with uptime under connection churn. Restarts and an idle device do not exercise that. This is a
  silicon question (the C is the same on rp2), so it is settled here, not left to a later unit.

## Items, in order
1. Existing evidence first (targeted reads): any twin soak or heap record under HTTP load whose heap trend already
   bounds this (HEAP_FRAGMENTATION_MEASUREMENTS.md, the twin CI soak's checks). Name what it covers and what not.
2. Measure directly, arzi and dev, both stages: after a gc.collect(), walk from every live Task and the queue along
   `child_last` and count the finished Tasks reachable only through it, with their bytes, at intervals under
   (a) HTTP connection churn, serial and overlapping bursts, thousands of connections; (b) dev's UART exerciser;
   (c) NTP/DNS socket churn. Report the chain's maximum and its trend against uptime and connection count.
3. Verdict with numbers. If the pinned set grows with uptime or connections: it is a firmware defect. Build the
   minimal upstream-style patch (clear `child_last` wherever `child` is set to NULL) in a private toolchain copy
   (PICO_TOOLCHAIN_DIR), show the growth gone, and hand back the choice for the owner in prose (a
   toolchain/micropython_overrides.py override, an upstream report, or both, with consequences and a
   recommendation). Do not add the override yourself. If bounded, state the bound and the measured worst case.
4. rp2's `poll.unregister()` keeps the stream in its deleted map slot (extmod/modselect.c:505-520 does not NULL the
   value that py/map.c:202 says the caller must; the lead confirmed it). Bound it: the poll map's allocation after
   the product's peak concurrent registrations in the twin under load, so the hardware round knows what to read.
- Seams: at about 80 tool calls, commit nothing that is not green, and hand back with what is left.

## Hand-back (the file, per redo_common)
The evidence read; the walk's numbers per scenario and stage; the verdict; the patch result if built; the poll
bound; any owner question in prose with a recommendation; last line "nothing of mine is running".
