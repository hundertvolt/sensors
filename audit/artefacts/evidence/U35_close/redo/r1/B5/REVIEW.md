# B5 review (lead, 2026-11-03)

Every hunk of `src/` and `buildgen/` in `3129bf21..21e12c76` read against `ACTION_LIST.md` (`review_hunks.py`: 58
hunks, none proven mechanically, all read; `review_hunks.out`). Every hunk maps to an item: 1 (start), 2 (head check,
hook), 3 (W16), 4 (captive re-raise), 5 (NTP parse), 6 (cadence), 7 (resolver), 8 (stored re-checks, CD-2, DNS-1),
9 (NTP timers), 10 (W49/W50), 12 (static hold), 13 (body heap), 15 (UDP poll), 16 (setup, `_cfg_values()`), 18
(CD-4, UDP-5, NTP-7, WS-15, WS-19, WS-20), 19 (NTP retry); codegen, validator and catalog follow items 1, 2, 3, 7,
10 and 19. No module grows.

Decisions on the points the hand-back named (agent, 2026-11-03):
- **WS-20 is not restored.** The serving-demand rule (SPECIFICATION.md I.3, H.7: the largest GET body "held once as
  its encoded pieces") and its scenario's identity check ("so an encode-copy fails here") exist to catch exactly the
  copy the str writer makes at `_pieces_response()`; the hand-back weakened that check to fit. dev's margin is about
  3.4 KB against an estimated budget. The bytes writer is no more complex, so it stays with the identity check and
  `test_h2_piece_writer_counts_bytes_not_characters`; the unit agent reverts the WS-20 hunks.
- **CD-5 stays as landed:** the task-top rule (`tests_scripts/test_task_tops.py`) is a standing check, and keeping the
  landed form changes nothing.
- **WS-22 stays:** the kept W48 trace and the task top need `counted`.
- **`test_fatal_report_sites.py`:** not a weakening. B1's logger records a C-stack overflow at its entry, so a
  rebound printer that logs through `err()` records; the check gained a case that fails a hook returning before its
  log.
- **UDP-5:** the cancel invariant moved from the socket to its callers ("every caller tears its socket down in its own
  finally"); the falsification checks that every product user does (claim 11).
- **NTP-7:** the 1 KB receive per attempt is legacy's and the pre-audit form; the scan judged a failure implausible.
  Kept restored.
- **WS-19:** in the action list by name; every float source checked gates its own values (SCD30 `isfinite`, the math
  helpers, ISL29125's range checks); the falsification checks every GET route (claim 13).
