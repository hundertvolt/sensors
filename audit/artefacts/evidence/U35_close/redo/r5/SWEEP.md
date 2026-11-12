Sweep hand-back, written by the agent (Fri Nov  6 06:28 UTC 2026). Read-only at the integration head f509c906.
Domain: the generated main() and boot entry with src/asy_system_service.py (setups, task start, timers, stagger, supervisor, feeds, shutdown, reset records, error counts), each chain traced from src/ through every tier's script.

## Parity (L1 mock, L2 twin, L3 flash, L4 bench)
- Holds at every tier that applies, each silicon script driving real product objects from a real trigger: the boot phases and begin_boot()'s
  decode (L4: codes 0, 2, 3, 5-9, 11-15, 20, 21, 22; code 1 is the manual power cut), both boot-entry handlers, task start and the unretrieved
  report (L3), the supervisor's restart (L3), both escalations (L4), the shutdown's steps, feed gaps and attribution (L3, L4 races), the failed reset arm.
- Already recorded as "a gap until written": a command in the boot window (`system-commands-instrumented`; smallest fix one bench test: PUT reboot
  at the first /status 200, read ResetReason 3), failed arms beside the graph (`timer-pool-under-graph`), main() ending or raising inside the running
  system (`watchdog-fault-planted`), the unfed boot stretches' silicon figures (BACKLOG.md:151).

## Findings
1. Wrongly trusted (containment claim). flash/test_task_supervisor.py:13 claims `ci_suite._run_5_recovery_after_bounded_fault`. Run 5
   (scripts/_digital_twin_ci_suite.py:1280-1316) is an injected SGP40 read fault handled in place, with no task end and no restart; the flash test
   restarts a synthetic task (device_scripts/system_service_restarts_a_real_dead_task.py:36-42), so Run 5 counts as covered on silicon and is not.
   Fix, one commit: COVERS `("sensortask_integration",)` (tests/test_digital_twin_sensortask_integration.py:658), Run 5 into row `bus-fault-injection` (SPECIFICATION.md:5812).
2. Wrongly trusted (fake feed). hold_console claims a non-reading USB host still lets the budget reboot (bench/test_reset_reasons.py:104). The script
   feeds the WDT itself every 0.9 s in every mode (system_service_restarts_a_real_dead_task.py:58-60). A console stall (A.5, SPECIFICATION.md:677-683)
   can only show as a TIMER-bit starvation, which that feed hides, and the test asserts the FORCED bit (:118), so it cannot fail on the hazard it names.
   Fix: one line, no script feed after HOLD_FROM_HERE, as system_command_hang.py:74 does. Needs hardware to see it green.
3. Gap. A ResetErrors refused after a reset decision (src :673-678; asy_webserver_service.py:429, 800-812) is pinned at L1/L2 only
   (scripts/_digital_twin_scenarios.py:1647 command, :1660 escalation, :1685 mempause), and no row names it. Over REST, with no instrumentation: one
   assertion in bench/test_rest_endpoints_over_sta.py:55 (after mempause, ResetErrors answers Failed), and one bench test (PUT reboot, then ResetErrors in
   the park window, errcount saved first). For the escalation, reset_code_stack_exhausted.py reports reset_error_counter() once is_reset_decided(). Needs hardware.
4. Gap. An escalation entry that never finishes leaves code 20 to the watchdog (_digital_twin_scenarios.py:818; src :545-556, "Awaited plainly").
   It runs at L1/L2 only, and no row names it. Silicon can reach it with no src/ change: the stack script holds SYSTEM's chunk lock, and the test
   expects 20 with the TIMER bit, against the FORCED bit of bench/test_reset_reasons.py:192-205. Fix: one parametrisation. Needs hardware.
5. Gap in the record. A dropped one-shot fire leaves the reset to the watchdog, for the reset fire (_digital_twin_scenarios.py:1699,
   tests/test_asy_system_service.py:715) and for the boot stagger fire (:1831). Both run only at L1/L2 (digital_twin/machine.py:1372-1375), and no row
   names them; they pass under rows SPECIFICATION.md:5815 and :5817, whose reasons cover other cases. Silicon proves each half on its own: the drop
   (scheduler_saturation_drop.py), the starve-to-watchdog (reboot_fallback_starves_the_watchdog.py), a phase-4 stall (bench phase hang). Fix: one line
   in each row stating that split, or a script saturating the queue across the 4 s reset fire (needs hardware).
6. Gap. ConfigFaults (run_setups(), src :691) is pinned at L1 (tests/_sensortask_scenarios.py:3405) and L2 (Run 13's damaged cell,
   _digital_twin_ci_suite.py:977-1000), never on silicon: the flash script damages a file only after the setups ran (system_command_config_reset.py:56-61),
   and the bench reads only `[]` after a reset (test_system_commands_over_rest.py:150). It stays hidden because flash/test_system_commands.py:20 claims all
   of Run 13. Fix: one flash test, damage a scratch file, build and set up over it, read get_config_faults() (one repair write, persistence_write). Needs hardware.
7. Gap. `system.scan_budget` (SPECIFICATION.md:12147, `feed.supervisor` :6715) reads "measurement owed ... L3", with no script and no BACKLOG entry. No
   silicon escalation reaches it: escalate logs to RAM with one task dying (script :52), and the stack path writes one entry and skips the scan; L1
   counts writes, not time (_sensortask_scenarios.py:1833). Fix: one BACKLOG line, then a timed full-graph pass with several tasks ending at once and SYSTEM on FRAM.
8. Gap. The boot signature's random fallback (src :502-505) claims "unique per boot" from ring-oscillator entropy, which only silicon can prove; it is
   pinned at L1 only (test_asy_system_service.py:403). The NTP-blocked bench boot holds the block 90 s (bench/test_wifi_networking.py:27, :93-101), under
   the 120 s _NTP_WAIT_TIME. Fix: one assertion, hold past 120 s and assert BootSignature is set; two such boots that differ prove the entropy. Needs hardware.
9. Needs an owner decision. The read-trigger spacing (C.9.1, `rate.trigger_spacing`) is observed on silicon only under --soak-duration
   (bench/test_boot_order_and_triggers.py:78-83), which the standard bench floor deselects; E.6.1 limits soak runs to proving liveness. Options: a short
   fixed window in the default run, or one E.6.6 line accepting soak-only.
10. Needs an owner decision; this is why 1 and 3-6 were invisible. tests_scripts/test_level_containment.py:44-55 and :108-112 match per harness family
   and per ci_suite run, so a row naming `system_commands` or `timer_pool` excuses every later member, and one COVERS id covers all of a run's cells.
   Options: per-scenario ids, or a row review whenever its family grows.
BACKLOG item (BACKLOG.md:29-44): it can come out once this account lands in tests_hardware/README.md's tier-parity section and findings 1-10 are fixed or carried as their own items. It names no other unswept domain.
nothing of mine is running
