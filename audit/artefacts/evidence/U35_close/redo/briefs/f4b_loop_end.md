# F4b: no exception leaves the boot entry unrecorded (lead, 2026-10-26)
Read `S/u35r/briefs/redo_common.md` first. Worktree `S/wt-u35f4b`, branch `audit/u35-f4b` at `656fc82`; logs in
`S/u35/laneR/f4b/`. The lead's facts: `S/u35/lane_plan.md` LEAD NOTES 156-157 (re-check each yourself).

## The owner's words (2026-10-26, verbatim)
"There should be no uncaught exceptions. That's a hard pillar. Are there such possibilities or is it for fallback
reasons like interpreter errors?" Then, to the lead's recommendation below and its question "How do you want this one
handled?": "And for sure test and verify it in both twin and real hardware".
The recommendation: the generated boot entry catches every exception that leaves `asyncio.run()`, prints it, writes a
reset record and lets the watchdog reset, as Ctrl-C is handled today; after boot a new ResetReason value ("the event
loop ended with an exception"), during boot today's 10 + phase code; identical on every device; RAM record, no wear.

## The facts (LEAD NOTES 156)
The entry: `buildgen/codegen.py` :852-866 catches KeyboardInterrupt only (RR_INTERRUPTED 21). After BOOT_DONE region 1
holds BOOT_DONE, so `begin_boot()` (src/asy_system_service.py :147-165) reads any later watchdog reset as 2. The paths
left: a non-Exception BaseException raised in a task (SystemExit, GeneratorExit), the asyncio loop core failing outside
any task (extmod/asyncio/core.py run_until_complete catches only CancelledError and Exception), and before BOOT_DONE an
exception escaping a boot phase (attributed 10 + phase, the exception console-only).

## What to build
1. The entry catches every BaseException leaving `asyncio.run()`; KeyboardInterrupt keeps its own clause and code.
   For the others it prints the exception with no heap use (fixed-argument print, `sys.print_exception`), records, then
   ends so the armed watchdog resets the unit. The record rule lives in `asy_system_service` (one small function the
   entry calls, unit-testable): after BOOT_DONE and with no valid record in region 0, the new code (the next free value,
   22; a name in the RR_ style); during boot nothing is written, so the next boot reads 10 + phase; a record already
   written (a system command's, an escalation's) is kept, since it names the reset already underway (conservative,
   logged as "(agent, <date -u>)").
2. Every class must reach the next boot as that code. Check against the pinned source what rp2 does when each class
   leaves a frozen main.py (ports/rp2/main.c, shared/runtime/pyexec.c: a SystemExit is a soft-reset request there) and
   what `begin_boot()` then reads (its PWRON_RESET check runs first); where a re-raise would lose the record, end that
   path so it does not, citing the source lines.
3. The new code wherever ResetReason values are listed or described: SPECIFICATION.md (A.7, A.8's table and the boot
   entry's text, F.5.4), the website (the js mirror of the descriptions and its tests_js), tests_scripts that pin the
   list, DEVICE_REFERENCE.md/README.md where they list codes (grep RR_INTERRUPTED, "ResetReason" and the code 21).

## Proof, each seen red first, both GC stages where it runs on MicroPython
- Unit: the record rule (after boot, during boot, a record kept) and `begin_boot()` decoding the new code.
- tests_scripts: every device's generated entry carries the clause and imports what it calls; it compiles.
- Twin: a new `tests/test_digital_twin_*.py` file (the twin CI suite is lane T's): a device booted to BOOT_DONE in the
  twin, an Exception and a non-Exception BaseException made to leave the loop, the twin's watchdog/reset model run
  (digital_twin/machine.py: mem_backup, WDT, SimulatedRebootError), the next boot's `/status` ResetReason read: the new
  code; an escape during boot reads 10 + phase; Ctrl-C still 21. Every device, by hardware configuration only, the
  matrix deduplicated as the suite already does (owner's device ruling). Zero memory markers.
- Real hardware, prepared, never run (no hardware in this session): a bench test beside
  `tests_hardware/bench/test_reset_reasons.py::test_a_console_interrupt_is_attributed`, with no flash write and no extra
  flash cycle (the least-wear rule). Candidate: Ctrl-C into the REPL, then inside the armed watchdog's window exec a
  script that makes the next run's loop end with an exception after BOOT_DONE (patch, then import the frozen main), the
  watchdog resets, ResetReason reads the new code, and its bits are checked like the Ctrl-C test's. Verify each step
  against the pinned source (frozen main importable by name, WDT re-init on rp2, the 8388 ms window, what the first
  Ctrl-C's record does to the second run). Follow tests_hardware/README.md's FRAM-log rule. Run it `--collect-only`,
  and through the twin where the harness allows. If no wear-free trigger works, stop and hand back the options with
  their wear: that is the owner's question.
Checks: scripts/lint.sh, scripts/typecheck.sh's five mypy passes (it refuses the shared venv: run them directly, with
the stubs at `S/shared/typings`), the comment-cap test, test_citations, the buildgen tests,
tests/test_asy_system_service.py and every file you changed at both stages, the dev and wozi twin CI once each at -1
at the end (`scripts/run_digital_twin_ci.sh <device>` inside the namespace, a disk check first).

## Not yours
toolchain/ (F4a), src/asy_webserver_service.py, asy_base_classes.py, asy_sgp40_driver.py (F1r), the F2r files,
scripts/_digital_twin_ci_suite.py and digital_twin/_fram_chip.py (T4r1), audit/ records. If you need a change there,
hand it back. Commit subject `U35 lane F4b: <summary>`, the two trailers; do not push. Hand-back: files and commits,
each proof's red and green with log paths, the hardware test's steps and what each was verified against, anything that
surprised you; last line "nothing of mine is running".
