# B2 core: action list (lead, 2026-11-02 21:25 UTC)

Base: the integration head after B1's merge. Files: `asy_base_classes.py`, `asy_system_service.py`,
`asy_config_manager.py`, `math_helpers.py`, `asy_api_response.py`; the `/status` emitter lines of their keys
(`buildgen/codegen.py`) and website rows (`buildgen/definitions.py`). Pre-audit counterparts at `25caf528` (`src/`
`base_classes.py`, `system_service.py`, `config_manager.py`, `math_helpers.py`, `api_response.py`). Full wording and
silicon facts: `PLAN_before_rewrite.md` 2.3, row B2. Every hunk of these files is judged.

| # | what | decision | basis | test that shows it |
|---|---|---|---|---|
| 1 | `/status` keys `ResetBits` and `ConfigUnpersisted` | remove: emitter lines, website rows, getters, their tests; `ResetReason` and the internal unpersisted flag (the shutdown flush) stay. `tests_hardware` readers of `ResetBits` (24 references) stop reading the key: a raw-bit check moves into the test's own device-side read where a few lines do it, else it is listed for R2 with its basis; nothing skipped or disabled | owner, 2026-11-02 21:11: "(a), remove both" | the status key-set tests change first (red), web tier green |
| 2 | Reset code 4 (bootloader) | remove: the bootloader command writes no reset record; catalog row 4 goes (no placeholder); the bench test `test_reset_reasons.py` expects what silicon reads (2); smallest form, no new branch where avoidable | owner, 21:22: "That actually never happened and is overkill code bloating the firmware. Remove code 4." | the bootloader command's test changes first |
| 3 | The wet bulb's cold-dry corner | remove: `_WB_CORNER_*` and the corner check; the pre-audit range check stays | owner, 21:25: "(a), remove the corner" | the corner tests go first; a corner point then returns a value |
| 4 | `rel_humidity()` | change back: clamps to 0-100 % again, as legacy and the pre-audit code did | the no-clamp rule is agent text; the owner kept the helpers and asked the tests to be aligned | a value just over 100 % reads 100 (red today) |
| 5 | W69 CONFIG_LOST, `absent_at_boot`, the logger's `restored` flag | remove: a missing config file returns to the pre-audit persisted warning, once per boot, where the defaults are then written; a command-only schema keeps its printed note; OR136.a's write-once kept | S2-G4-21 (an addition with its own false positive); OR136.a (3) | the W69 tests go first; the missing-file test reads the pre-audit warning |
| 6 | The uptime timer's re-arm (`_status_loop`, the one-second sleep and re-arm, its `reported` flag) | remove: back to the pre-audit loop | S2-G4-7 (the timer-arm family: a refuted trigger), S2-G4-8 | its tests go first |
| 7 | The 1,200 ms escalation entry bound (`_ESCALATION_ENTRY_WAIT_MS`) | remove: the entry write is awaited plainly; a hung write (an overflow inside `release()` leaving a lock held) ends in the watchdog reset, and the reset record, written before it, still reads the right reason | rule 6 (no hardcoded timed check); `plancheck/R1.md` B2.6 (checked against the closure's keep in `scan2/G4.md`:526) | its test goes first; the escalation test stays green |
| 8 | A chip-setup failure | change: follows OR113's order, mild rung first (no ladder existed before the audit) | OR113 (`PROJECT_AUDIT_PLAN.md`:496): "always try to solve / recover from issues with the smallest possible blast radius" | a test of the order, red first |
| 9 | Per-unit cleanups in these files | remove: test-only product code (the `setup()` bools, `set_utc_valid(valid=)`, `_shutdown_task`); per-episode flags (`_read_failing`, `_timer_reported`, `quiet=`) for the newest-entry rule; a narrowing branch that can never run becomes a typing-side form; the whole-millisecond rule only for waits in loops | PLAN.md R1; S2-G4-8; S2-G4-22; OR35.b "Pure and simple." | each change's tests first |
| 10 | Kept | E115 (a supervisor crash's one persisted trace); the mempause deadline (decision 3), its two cascade parts judged here; the recovery ladder in a smaller form; the reset path; the system commands; the staged write; the newest-entry rule; the counter caps (OR103); the measured uptime (OR101) | the owner's decisions | existing tests |
| 11 | Every other hunk against the pre-audit text | restore it, or name it to the lead with its basis | PLAN section 2, step 4 | the review script marks it |

No user-visible removal beyond item 1 (agreed). Docs in the same commit: the SPECIFICATION.md lines of each item, the
catalog texts. Each removed item: one knowledge line.
