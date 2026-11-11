TW hand-back, written by the agent (Wed Nov 11 11:33 UTC 2026)

Commit e6dd5b3c on audit/tw (from 015dda9f), local only. Items 1, 3 and 4 are done. Item 2 stopped on its ripple; options below.

1. SCD30 C03 (chip dddddd, twin 000000). Cause: handle_writeto() stores 0xD304 as _last_cmd, and _power_up() never cleared
   it, so the probe's read after its soft reset hit the unknown-command branch (zeros). Edit: _power_up() sets _last_cmd
   = None (1 line); a power cycle is covered too. Proof: D scd30::a_read_with_no_command_pending_returns_0xdd_bytes now
   reads after a soft reset and after a power cycle: red before the fix, then 57/57 at -1 and 32768 and under settrace.
   run_probe_on_twin(): C03=dddddd at both stages.
3. FRAM C02 (chip 1, twin 0). Datasheet: MB85RS2MTA DS501-00032-3v0-E p.6 resets WEL only "After power ON" and "After
   WRDI command recognition", and is in continual programming mode "After WRSR command. After WRITE command." So the chip
   is right; no conflict to hand back. The MB85RS64V (DS501-00015-4v0-E p.6) clears WEL at CS after WRITE and WRSR.
   Edit: _status_after_write mask, set from the table's key (size > 64 KB = the MB85RS2MTA, as for address width); the
   stick_next_wrdi comment corrected. Proof: new D fram::the_mb85rs2mta_keeps_wel_through_a_write_and_a_wrsr_until_a_wrdi,
   red before, then 57/57 at both stages and under settrace; the MB85RS64V tests unchanged. Probe C02=1 at both stages.
4. test_reset_reasons _attributed(): wait_until(board.is_device_present, ...) before board.exec(). This is the
   harness's own passive presence check, the tier's idiom. Its bound reuses the file's _SERVING_TIMEOUT_S (90 s), the
   wait for that same reboot, so no new number. Proof here: --collect-only, ruff, mypy. The behaviour proof is the
   next bench round (the bench tier skips under --twin).
2. BMP3XX B03 (chip 13, twin 03): STOPPED, no change committed. I built the full model (DS001 3.9.2 time at the set
   OSR, the reading and the return to sleep landing at the first access after it, a soft reset ending it; the fake's
   tests on a driven Ticks30Time). It made all three probe keys equal and passed its own 29 tests. It rippled:
   D hot_replug::a_power_cycled_bmp3xx_reads_on_at_the_chip_defaults_without_a_ladder_step failed (E11+E1 x2).
   Cause, confirmed by experiment: that test runs the driver on DrivenTime(driven_modules()), which covers modules
   holding asyncio plus machine/network, while the fake read host ticks. The driver's 7 ms wait passed in virtual time
   and it read STATUS before the conversion ended. Everything else passed with the model at -1: the 20 other twin files,
   and the 5 PER_DEVICE files on arzi/dev/grkizi/wozi. Not run: the scenario harness jobs, the twin CI suite, 32768.
   Options: (A) the full model, with machine.py handing the fake its clock (clock=lambda: time, the timer_factory
   pattern): hot_replug 2/2 and own tests pass; patch at ftmp_tw/bmp3xx_full_model_with_machine_clock.patch (it needs
   typing and a 3-line comment pass, plus the README rows 233/235). (B) PWR_CTRL alone reads 0x13 for DS001's time and
   the reading lands at the trigger as today. No ripple, since src/ only writes PWR_CTRL, but "data ready at once" stays
   a divergence needing an actor. Weakening B03 to a physical key is not an option (never weaken a check).
Checks on the final tree: rebuild; lint_direct clean (ruff 0.17.4); mypy main/host/twin clean; the scd30/fram/bmp3xx
and hot_replug files 0 failures at -1 and 32768; tests_scripts readers plus the comment cap 750 passed; tests_hardware
collect 23/24 (1 deselected). No gate was run (not asked; host not released).
Sizes and cost: no product file touched, so bytecode and imageFreeBytes are unchanged. Host-only twin cost is one store
per SCD30 power-up and one attribute AND per FRAM WRITE/WRSR. The presence wait is one 0.2 s port probe, 90 s at most.
Decisions (agent, 2026-11-11): FRAM part by size; the bound reuses _SERVING_TIMEOUT_S; item 2 reverted per the stop rule.
Findings (c): src/asy_bmp3xx_driver.py's _conversion_wait_ms() comment credits DS001/DS002/DS003 with DS002's
2020/163 us formula. DS001/DS003 say 2000/313. Its 6/5 margin still covers both (DS001 at most 2.3 % above).
Addendum (agent, 2026-11-11 12:08 UTC): item 2 done as option A on the lead's decision; commit 8eef7b95, second on audit/tw.
- Fake: DS001 3.9.2 time (2000/313 us) at the set OSR; reading, data ready and sleep land at the first access after; 0xB6 ends it.
  clock: "Callable[[], _Clock] | None", where _Clock is a read-only-property Protocol the `time` module meets (MicroPython refuses
  PEP 570 `/`, ruff PYI063 the `__x` form); one fallback `lambda: time`; machine.py `clock=lambda: time`; a planted errno fails mypy.
- Proof: own test red, then 29/29 at -1/32768/settrace; probe B03=13, B05=03 at both stages (all three keys equal); 26 twin files
  and 6 PER_DEVICE files on arzi/dev/grkizi/wozi at -1 and 32768: 100/100 passed, 0 memory errors; ruff, mypy x3, tests_scripts 750.
  One rerun: my driver edit landed mid-run and staled build/generated_src (b, my process; rebuilt, then all green).
- Driver comment cites DS002 3.9.2 and every Table 22/23 Typ column, naming DS001/DS003 3.9.2's 2000/313: 617 lines before and
  after, mpy-cross plain and -march=armv6m cmp-identical. Note: all three tables' Typ follow 2020/163 (x8/x1's 18.69 fits neither);
  the fake keeps DS001 3.9.2 per the brief, at most 2.3 % longer, inside the driver's 6/5 wait. README rows 233/235 updated.
