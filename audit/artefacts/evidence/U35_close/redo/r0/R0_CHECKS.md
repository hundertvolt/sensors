# R0: DECREV 9's three checks (2026-11-02, the lead)

Each decides an item of the unit that owns its code (PLAN.md, R0). Sources: the pinned MicroPython v1.29.0, the
repository's history, `scan/decrev/DECREV.md` 9 and `DRX.md` V9.

## Item 3: the logger-side C-stack check at a nearly exhausted C stack (decides B1's form)

- Run: `r0/cstack/cstack_check.py` on the pinned Unix port (`ports/unix/build-standard`), through the lead's run
  wrapper (2026-11-02 19:31 UTC). A recursion runs until the interpreter's "maximum recursion depth exceeded"; every
  level's handler only logs through a logger whose entry checks its arguments for that error first, as B1 plans.
- Result, sync and inside an asyncio task alike: the record is set (`fatal=True`). The two or three deepest handlers'
  logging call overflowed again and raised out of its handler; the overflow then propagated to the next outer
  handler, whose logging call fitted and recorded it (sync at depth 222, async at depth 253: the deepest handler
  whose logging fitted).
- Verdict: B1's logger-side form holds. A handler too deep to log passes the overflow outward, and the first handler
  that can log records it; the supervisor's own logging is the last such handler. A handler that logs nothing needs
  its explicit call (B1's five and the Microdot hook). The board half stays round 1's item 1 on the final image.

## Item 5: the three fixes of `ad1fae73`, `a4f0ccea` and `8cf55c6b` (decides three B2 items)

The rule (DECREV 9; F.2 before the audit: "only worth closing for a concrete, non-hypothetical threat"): name the
raising call at each site at the parent of `7008730e` and read it in v1.29.0; only a MemoryError at call entry means
revert, anything else keep.
- `ad1fae73`, the shutdown gate around `await self._storage.erase_ready()`: `erase_ready()` reads two flags, an
  `asyncio.Event` and `get_write_protected()`, whose not-initialized branch cannot run there (`erase_ready()` checks the
  driver's readiness first) and which otherwise returns a flag or `Pin.value()`. Nothing raises but the two coroutine
  objects' allocation at call entry. Revert.
- `a4f0ccea`, the auto-unpause order: the call is `FRAMManager.set_pause()`, whose only statement besides an
  assignment is `self.pr.evt(...)` on a RAM-only logger, a `print()` of a string and a bool; the raise is the
  argument tuple's allocation at call entry. Revert.
- `8cf55c6b`, the boot signature's flag order: the call is `self.pr.one(...)`, the same `print()` path. Revert.
- Verdict: all three revert in B2 (the commits' forced-raise tests go with them, listed in B2's action list).

## Item 6: the exception-handler guard (decides one B1 item)

- Asked: the 2026-10-07 proposal the owner answered "Yes, build it that way." Guard in it: keep; not in it: DIFF
  (OR36), one line.
- Found: the proposal text is not in the repository; only the answer is (REGISTER.md:285, SPECIFICATION.md:6549), and
  the 2026-10-07 session's own transcript is outside this session's reach. The register row written the same day
  records what was built under that answer: "installed by `start_and_check_tasks()` only when no handler is set".
- Decision taken on the owner's behalf (agent, 2026-11-02), shown in R0's report: keep the guard. It is the smaller
  change (none), the same-day record pairs it with the owner's answer, and leaving a handler someone installed in
  place is a library's ordinary manners ("Always regard the modules as libraries"). The owner can reverse it.
