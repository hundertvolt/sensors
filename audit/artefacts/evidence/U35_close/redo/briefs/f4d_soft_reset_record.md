# F4d: a console soft reset keeps the reset record (lead, 2026-10-26)
Read `S/u35r/briefs/redo_common.md` first. Worktree `S/wt-u35f4d`, branch `audit/u35-f4d` at `2a46984a` (the
integration head: F4b's loop-end record and F4a's toolchain change are in it); logs in `S/u35/laneR/f4d/`. The lead's
facts: `S/u35/lane_plan.md` LEAD NOTES 174 and 177; F4b's hand-back `S/u35r/handbacks_redo/F4b.md` (its scan, class 7).
Re-check each fact yourself.

## The owner's words (2026-10-26, verbatim)
The lead's question, "Which one: (a), (b) or (c)?", (b) being: "Read the record first. Two checks in the boot's reset
decoding swap order, so a valid record wins over the power-on check. ... A real power-on still reads 1, because the RAM
is empty then. A console soft reset now reports the 21 or 22 that was recorded. ... Testing: done like the event-loop
record: unit tests, the twin, and a bench test in the hardware round. On a board that last booted from power-on, the
bench test presses Ctrl-C, then Ctrl-D inside the window, and the next boot must read 21."
The owner: "B is fine, very rare edge case".

## The facts
- `begin_boot()` (src/asy_system_service.py:147-167 at 2a46984a) decides in this order: `reset_cause() == PWRON_RESET`
  (1), a valid region-0 record (its code), a torn record (0), a region-1 boot phase (10 + p), else 2. A friendly-REPL
  Ctrl-D after the entry ended (Ctrl-C: 21; another exception after boot: 22) soft-resets and re-runs main.py; rp2's
  `reset_cause()` still reads the last hard reset (ports/rp2/modmachine.c at v1.29.0), so after a power-on the boot
  reads 1 and clears the record unreported.
- A power-off and a poweron-style reset clear rp2's mem_backup: the pinned MicroPython docs
  (`/root/pico-toolchain/micropython/docs/library/machine.rst`, the rp2/esp32 note under the port table) and SPEC F.5.4
  (RP2040 datasheet 4.7.4, read by an earlier session). The RP2040 silicon datasheet is not in this container (the
  datasheets submodule is not fetched): cite the docs and the spec, never web or memory. So a valid record seen under a
  power-on cause means a soft reset.
- `tests/test_asy_system_service.py:3843` `test_power_on_reads_1_even_with_a_stale_valid_record` pins the old order.
- The twin: `digital_twin/machine.py` `power_on()` clears both regions; the mem_backup state file carries the cause
  (`configure_mem_backup_state_path`), so a soft reset is a relaunch whose cause stays PWRON_RESET with the regions kept.
- SPEC:6933-6935 gives the old order as the reason the entry never re-raises a SystemExit.

## What to build
1. The swap, nothing more: a valid region-0 record is decoded before the power-on check; the torn-record, phase and
   watchdog branches keep their order after it (a torn record under a power-on cause still reads 1). Same on every
   device, RAM only. The comment says why in at most 3 lines.
2. Sweep every consumer of the old order and fix what it breaks: `tests_hardware/` (each place expecting ResetReason 1
   or `_RR_POWER_ON` after a flow that soft-resets: mpremote's raw-REPL soft reset, device scripts that call
   `begin_boot()` or `import main`, F4b's `reset_code_loop_end.py`), the twin and its README fidelity rows, the website
   and tests_js if they describe code 1, `src/` for any `machine.soft_reset()`/`sys.exit()` (none expected; say so).
3. Docs: SPECIFICATION.md F.5.4 (the order, why a record under a power-on cause means a soft reset, the decision tag
   below), A.7/A.8 where they state what code 1 means, SPEC:6933-6935 restated to what still holds about not
   re-raising (check rp2's soft-reset path in the pinned source: ports/rp2/main.c soft_reset_exit). The entry's
   behaviour is the owner's earlier decision and does not change; if no true reason is left for that sentence, state
   the facts and hand it back, do not change the entry. tests_hardware/README.md where it describes reading code 1.
   Decision tag: (owner, 2026-10-26: "B is fine, very rare edge case"; the question, paraphrase: whether the boot should
   read a valid reset record before its power-on check, so a console soft reset inside the watchdog window keeps a
   recorded 21 or 22).

## Proof, each seen red first, both GC stages where it runs on MicroPython
- Unit: a valid record under a power-on cause reads its code (replaces the test above); `power_on()` then a boot reads
  1; a torn record under a power-on cause reads 1; the existing order tests stay green.
- Twin, in F4b's tests/test_digital_twin_loop_end.py (deduplicated as its first-device cases are, identical code on
  every device): after a power-on launch, Ctrl-C (21) then a relaunch modelling the soft reset (cause kept PWRON, the
  regions carried) reads 21 on `/status`; the same for 22; a real power cycle (regions cleared) reads 1. Zero markers.
  Bite: the old order planted in a scratch copy turns the soft-reset cases red.
- Real hardware, prepared, never run, no flash write and no flash cycle (check that each step writes nothing to flash).
  It needs a power-on cause, so it is a manual-tier step beside `tests_hardware/manual/manual_persistence.py`'s
  power-cycle steps (read how they prompt the operator):
  (1) the silicon fact: with a valid record in region 0 (for example the 21 that mpremote's Ctrl-C leaves, a device
  script then feeding the static WDT so no watchdog reset clears it), the operator power-cycles; the next boot must read
  1 (this proves a power-off clears the scratch registers, which the order now relies on);
  (2) the change: on that power-on boot, Ctrl-C at the friendly REPL, then Ctrl-D inside the 8 s window; the boot that
  follows must read 21, and its ResetBits are checked like the Ctrl-C test's.
  Verify each step against the pinned source (friendly-REPL Ctrl-D re-runs main.py on rp2; raw REPL's soft reset does
  not; WDT objects are static and feedable from a script, machine_wdt.c). Follow tests_hardware/README.md's FRAM-log
  rule. Run it `--collect-only`. If a step cannot be done without wear or without hardware the bench lacks, stop and
  hand back the options: that is the owner's question.
Checks: ruff, the mypy passes (stubs at `S/shared/typings`), the comment-cap test, test_citations, test_error_catalog,
tests/test_asy_system_service.py and every changed file at both stages, the tests_scripts files that read the changed
files. The toolchain hazard in redo_common.md applies: your base has F4a's `toolchain/`, so `scripts/test.sh`, the twin
CI and any tests_scripts file that starts a twin runner run only against a private toolchain copy; test files run with
the binary directly are fine. No twin CI run is required of you.

## Not yours
toolchain/, the F2r files (asy_fram_manager.py, asy_fram_driver.py, asy_notification_service.py, asy_ntp_client.py,
asy_uart_link_driver.py, asy_uart_driver.py, html/style.css), src/asy_print_log.py (F3r), scripts/_digital_twin_ci_suite.py
and digital_twin/_fram_chip.py, audit/ records, allow-lists in tests_scripts (hand back the row you need). Commit subject
`U35 lane F4d: <summary>`, the two trailers; do not push. Hand-back: files and commits, each proof's red and green with
log paths, the sweep's sites and verdicts, the hardware steps and what each was verified against, the SPEC:6933 facts,
anything that surprised you; last line "nothing of mine is running".
