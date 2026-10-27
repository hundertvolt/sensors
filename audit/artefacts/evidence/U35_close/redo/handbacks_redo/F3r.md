F3r hand-back, saved by the lead from the message it sent (2026-10-26). Commit 68224efb on audit/u35-f3r (base bc3bed11).

F3r hand-back. Commit 68224efb on audit/u35-f3r (base bc3bed11). Not pushed, nothing uncommitted. Stopped at the seam: item 3 (whole tier, twin CI) has not run and waits for your go. Logs: S/u35/laneR/f3r/.

**Items 1-2, applied (src/asy_print_log.py).** Every level-gated line method (err, wrn, one, evt, all, err_s, wrn_s) now prints through one shared `PrintLog._line()`. Below its level, `_line()` prints the first MemoryError among its arguments, as its own text, once, through `console()`. Anything else stays gated. Entries, counts and write-through are unchanged. The arm allocates nothing: a tuple iterates on the VM stack (py/compile.c:1575, objtuple.c:282-290), and console() has a fixed arity.
- Call sites covered: 140 src/ calls hand a caught error to a logger, always bare (AST scan): err_s 112, err 18, wrn_s 9, wrn 1. evt, one and all are covered through the same `_line()`.
- Seen failing first, both stages (red_print_log.*.log): the below-level test failed with `('err', 0, [])`; the err_s/wrn_s test failed with `[]`. The at-level guard and the heap-locked test passed once the fix was in. Each was bitten: a second console line at the level (fails), and a star-call in the arm (fails with `[True, True, False]`) (bite_*.log).
- One test changed: test_asy_webserver_connections.py:1157-1160. At level 0, a handler MemoryError now leaves two console lines (Microdot's print and the catch-all's own), as the same event already does at level 1. It pins the new behaviour, so it cannot pass on the old source.

**NTP unsynced wait, applied (src/asy_ntp_client.py).** Each check tick now adds the intervals since the last tick, rounded to the nearest, at least one: `max(10, round10(gap))`, where `gap` is a TickSeconds read at each tick.
- Red on the old source, both stages (red2_ntp_oldsrc.*.log): due at 50 s instead of 40 s, in both new tests (one dropped tick; and a dropped tick between wakes 1 ms early). Bites: flooring the gap fails the early-wake test; dropping the at-least-one floor fails three existing tests.
- No existing test changed.
- Deviation from "pure elapsed, like F2r": I tried pure elapsed time first. It broke 3 unit tests and 3 twin tests (test_digital_twin_ntp, test_digital_twin_clock_jump), which fire the tick by hand to stand in for the 10 s timer. On silicon it would also put a 10 s retry at 20 s whenever a wake lands earlier than the last one. The per-tick credit keeps every pinned behaviour.
- **Lead:** test_counter_steps.py:27, the `_EXEMPT` row `NTPClient._unsynced_wait_s`, is now orphaned (red). Please delete the row. test_twin_record is red as expected, since src/ changed.

**Handed back, owner question: report_unretrieved().** It is left silent at level 0. That silence is the owner's ruling (2026-10-07, SPECIFICATION.md:6392-6396), and test_asy_system_service.py's `test_the_report_prints_nothing_at_level_0...` pins it. So a MemoryError ending an unawaited task stays invisible on silicon at level 0. Options:
- (a) Keep it as it is.
- (b) Print one console() line for a MemoryError only. This adds a single branch, changes no entry, and affects every device on silicon.

**Item 4, effect.**
- MemoryError console line: every device, in all five modes (STA, AP, Silent, Off, USB). At DebugLevel 0, each logger call handed a caught MemoryError now prints one console line. While a USB host holds the port open without reading, that line can wait up to 500 ms (SPECIFICATION.md:620), as console() already can.
- NTP: all six devices, STA mode. A dropped tick no longer delays the unsynced retry.
- Stale sentences, for D3:
  - SPECIFICATION.md:617-618: a task ending with an exception "prints nothing at DebugLevel 0".
  - :3446-3448 and :3668-3670: console() is for "a layer with no logger".
  - :563-569: the webserver's bypass is now the general rule.
  - :7487-7493: G.2's console row.
  - :9068-9070 and :9077-9078: I.4(e) says err()/err_s() "prints only at a DebugLevel of at least 1".
  - CLAUDE.md is not incomplete.

**Findings (none changed):**
- Silent-failure class 5, new, in F2r's cadence (asy_ntp_client.py:382): `>=` on a rounded-down TickSeconds read puts the resync one tick late whenever a wake lands earlier than the restart. That is likely about half the cycles on silicon, 10 s per hour or more. The same rounding would fix it.
- Four console() bypasses are now redundant but harmless: webserver_service.py:811-812, base_classes.py:388-389, dns_client.py:153-154, system_service.py:581-582.

**Checks.**
- Importer files of both modules: 46 files (timer_pool on all six devices), 102 runs at -1 and 32768, plus re-runs on the final NTP code. All green, zero memory markers (batch_summary.txt, re*_*.log).
- ruff clean. mypy main pass (265 files) and twin pass (52) clean, cold, using f2r/typings.
- tests_scripts readers: 3036 passed. Red: counter_steps and twin_record only. A comment-cap red (a line over 120 characters) was fixed before the commit.
- mpy-cross compiles both files.
- Times are within 1% of F2r's: print_log 0.39/0.41 s, ntp_client 23.69/24.10 s.

**Deviations:**
- The twin ntp, clock_jump and generic-integration re-runs started at a ps heavy count of 6, because other agents had two twin CI runs going. All of them were green.
- The decision tag uses the decision's date, 2026-10-23 (LEAD NOTES 146).

All five of my RUNS.md runs are closed.
nothing of mine is running
