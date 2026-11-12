# LC1: no product task swallows a cancel through wait_for's lost-cancel window (lead, 2026-10-28)
Read `S/u35r/briefs/redo_common.md` (all of it; "Quality comes first" and "Efficiency" are binding, and it says how
you hand back). Then:
- `S/u35r/handbacks_redo/UM4.md`, "A Part F fact" and "Lost cancel in product code";
- the pinned MicroPython source at v1.29.0: `extmod/asyncio/funcs.py` (`wait_for`, `wait_for_ms`, `gather`) and
  `extmod/modasyncio.c`'s `task_cancel` (the forward to an awaited task). Read the source in the toolchain checkout
  (`$PICO_TOOLCHAIN_DIR/micropython`); never from memory;
- on your worktree: `tests/test_digital_twin_driven_clock.py`'s cancel-window test (UM4's red-first form);
  SPECIFICATION.md Part F.2 (what can be timeout-wrapped) and F.3; CLAUDE.md's rule against blanket asyncio try/except;
- `src/asy_system_service.py`'s task supervisor and shutdown sequence (who cancels which task, and what waits on it).

Worktree and base: in your launch message. Logs go in `S/u35/laneC/lc1/`.

## The fault
UM4 found that `asyncio.wait_for()`/`wait_for_ms()` turn a cancel landing after the timeout fired, and before the
runner task ended, into `TimeoutError` (v1.29.0). A product loop that catches `TimeoutError` from one and goes on
therefore swallows a supervisor's or the shutdown's cancel: the task never ends, and whatever awaits it hangs. UM4 names
`src/asy_neopixel_driver.py:82` (the overlay loop). The owner's rules here: "root-cause faults", "no uncaught
exceptions", "Firmware really complete, don't push fixes to future units".

Lane CMr1m is root-causing a hung cleanup cancel of a sensor `_read_loop`. If that turns out to be this mechanism, its
site is CMr1m's; the lead tells you which, and you leave it. Every other site is yours.

## Items, in order (each committed green on its own)
1. **Confirm the mechanism** on the pinned Unix port with a minimal reproducer in `S/u35/laneC/lc1/` (no src/ copy
   needed): a task in `while True: try: await wait_for_ms(...) except TimeoutError: pass`, cancelled inside the window,
   never ends; the same task with the cancel outside the window ends. Cite the source lines. Also state whether rp2's
   build runs the same funcs.py (frozen asyncio): the firmware's own behaviour is the question.
2. **The inventory.** Every `wait_for`/`wait_for_ms`/`gather` site in `src/`, and every helper of ours that wraps one,
   with each caller up to the task boundary. For each: can a cancel reach it in the window (who cancels this task, when);
   what the code does with a `TimeoutError` there (re-raise, return, log and loop); and so whether a cancel can be lost.
   A site that converts the lost cancel into a finished task (it returns, it raises) is safe, with the reason.
3. **Each unsafe site, red first:** a test that cancels the task inside the window and asserts it ends (fails today),
   then the fix, small and local, at that site or in one shared helper used by every unsafe site. UM4's driver form (an
   alarm task setting an event, awaiting only the event) is one candidate, not a requirement: choose by what keeps each
   site's timing and its error-log behaviour identical, and say why.
   - If a fix is not small and local, or changes behaviour beyond "a cancel now cancels", stop and hand the facts to the
     lead for an owner question in prose.
   - Each fix's bite: the old form fails its test, the new passes; every importer of each changed module at both stages
     (PER_DEVICE files on all six devices), zero memory markers.
   - No blanket try/except, no added gc.collect(); `MemoryError` handling stays as it is.
4. **The fact recorded:** SPECIFICATION.md Part F gets the fact with its source lines and the rule that follows from it
   (no product loop may swallow a `TimeoutError` from `wait_for`/`wait_for_ms` without checking for a cancel, or the
   form you chose). Write the text into your hand-back if it is longer than a row; the lead's D3r places it.
5. **Checks:** lint_direct, the six mypy passes, the three audit checks, every changed file's importers at both stages,
   the whole twin tier if a module every twin boots changed (asy_system_service, the base classes), the whole
   tests_scripts tier on your final head, and review rows re-rendered if a test's text changed.

## Notes
- No real hardware. Port-binding runs in `unshare -n S/u24/ns_xdg.sh`, nice 19. One test run at a time in your worktree.
- src/ is yours for the unsafe sites only. Lane CMr1m is changing `digital_twin/machine.py` (the watchdog) and
  `tests/test_digital_twin_sensortask_integration.py`; leave both, or name the need.
- Run to the end; hand back early only as redo_common says.

## Hand-back (the file, per redo_common)
- Commits; item 1's reproducer and source lines, and the rp2 answer.
- Item 2's inventory table (site, who cancels, what TimeoutError does, safe or not, reason).
- Each fix with its red-first test and bite; the importers' runs at both stages with wall times.
- The Part F text; the checks. Last line: "nothing of mine is running".
