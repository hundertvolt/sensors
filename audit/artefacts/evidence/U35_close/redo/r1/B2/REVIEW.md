# B2 review (lead, 2026-11-03)

Every hunk of `src/` and `buildgen/` in `93224dab..8019a9ef` read against `ACTION_LIST.md` (`review_hunks.py`: 41
hunks, all read). No hunk without an item; no module grows. One correction: the hand-back twice says the bootloader
arms "code 3"; the code, the commit message and SPECIFICATION.md say 9 (`_RR_COMMAND_INCOMPLETE`), which is right.

Decisions on the items the hand-back named (agent, 2026-11-03):
- A raising post-write hook: pre-audit answered ERR code 100, legacy an unguarded raise (Microdot's 500); since U11 it
  answers OK with the group's fields "Failed". Kept: it follows the pre-audit rule "a per-field failure never demotes
  the overall response below OK/0", and only a caller-supplied hook raising reaches it. Codes 2-5 had no product
  producer at `25caf528` (`parse_cmd_request()` had no caller), so their catalog rows going changes no reply. The
  hook's FRAM error code moved from 99 to the shared E14.
  A `_set_dict_cfg()` that raises (a defect: it catches its own failures) now reaches Microdot's 500, where
  pre-audit answered ERR 100; kept on the same reasoning (falsification claim 11).
- The typed getters stay: a stored value's type follows its key, which the type check cannot see, so the first half of
  the owner's test (2026-10-27) does not hold.
- The stagger timer's failed-arm catch in `start_timers()` stays: it is the scan's keep for that family (one
  catch-and-log per arm), and its sleep starts every trigger where the pre-audit code stopped sequencing early.
- A refused uptime arm also leaves the mempause auto-unpause unrun (the status loop never wakes); the arm's trigger is
  refuted (V6), and a manual unpause still works. Stated in the report.
- Item 8 removed the setup-failure rung rather than reordering it: the restart, then the budget's reboot, is the ladder
  above a failed chip setup, as before the audit; the read ladder is unchanged.

Carried to later units: `S/u35r/r1/CARRY_LATER.md`.
