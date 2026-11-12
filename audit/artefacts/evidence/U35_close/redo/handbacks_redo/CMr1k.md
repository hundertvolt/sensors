CMr1k hand-back, written by the lane (2026-10-27 18:32 UTC)

Worktree S/wt-u35cm2, branch audit/u35-cm2, base 111129f4. Logs, probes, bite copies and scripts are in S/u35/laneC/cmr1k/
(times.txt, load.txt, final.out, bites/, hp/, tun/, py/). Every run went through my one.sh / pair.sh / pyt.sh /
pyt_root.sh / checks.sh / final.sh wrappers (namespace, nice 19, RUNS.md lines: 113 started, 113 done). No src/,
digital_twin/, ext/ or tests_hardware/ file is edited. The scratch roots used for the bites are deleted. Not pushed.

## Commits
- `3658034b` item 1: the clock-jump and NTP booted tests run on a driven clock, once per distinct device wiring.
- `d87bd0d8` item 2: the SCD30 and SGP40 twin-bus driver tests run once per distinct wiring of their bus.
- `eb6c4cb9` item 3: the launcher's main() runs and the runner's real boot run once per distinct wiring they reach.
- `b6f461fc` item 4b: the NTP and clock-jump boots hold the previous webserver by id().
- `34380155` item 5: matrices.md's device-pick rows, no open row.
- `deb50e1c` item 6: the two files' remaining real waits tagged and measured in Part N.

Final head deb50e1c: lint_direct rc=0; mypy main / twin / host clean (274 / 57 / 312 files); the whole tests_scripts tier
7047 passed, 6 skipped, 2 failed: test_twin_record.py's two tests (instruments with no twin run recorded, and runner/
instrument hashes changed). Both name only tests_hardware files and runner hashes I did not touch; the expected red
(common_u35), as at the lead's gate before this lane. Every changed test file is green at both stages with zero memory markers.

## Item 1: clock_jump and ntp (3658034b)
Reach probe on the driven version, per device, after the last boot (counts of transfers):

| site (line at 5a8c6e35 -> b6f461fc) | after the boot it touches | class, set |
|---|---|---|
| clock_jump :328 -> :397 year forward, two back | FRAM 5 r/5 w, SGP40 6, general call 1, SCD30 12, LED 5; dev adds BMP3XX 30, ISL29125 23, UART 24; wozi BMP3XX 30 | W, `distinct_wirings()` = arzi, dev, grkizi, wozi |
| clock_jump :350 -> :406 first sync | FRAM 26 r/66 w (1 NTP store write), SGP40 11, SCD30 16, LED 6, plus the same extras | W, same set |
| clock_jump :372 -> :415 offset change | SGP40 4, SCD30 4, LED 5, plus the extras; no FRAM transfer | W (lead's ruling), same set: grkizi is a measured over-cover of one boot (it differs from arzi only in the FRAM); kept because the booted graph wires the FRAM its loggers write, the structural key there is |
| ntp :442 -> :535 clean first sync | SGP40 4, SCD30 4, LED 5, plus the extras; no FRAM transfer, but it asserts the NTP log the boot restored from the FRAM | W, same set |
| ntp :456 -> :542 outage back-off | FRAM 26/66 (1 NTP store write), SGP40 11, SCD30 16, LED 6, extras | W, same set |
| ntp :506 site -> :565 each failing reply | FRAM 63/183 (3 NTP store writes), SGP40, SCD30, LED, extras | W, same set |
| ntp :549 a socket failing its setup or connect (CO5's, new since the brief; 2 boots per device) | FRAM 21/61 (1 NTP store write), SGP40, SCD30, LED, extras | W, same set (decided by the same ruling; named here as an addition) |

Efficiency: clock_jump's `_booted()` now runs main() on one DrivenWall over every module holding asyncio and the responder,
as ntp's does, with the UART crossover wired after construction (dev). Per device on the driven clock (load ~4): offset
change 0.8-1.3 s, year steps 1.7-2.6 s, first sync 2.8-4.3 s.
Bites (clock_jump, -1): c1 `_driven_until` never elapses: 3/3 fail ("no first sync within 20.0 driven s"); c2
`_ticks_to_attempt` never elapses: the first-sync test fails ("no attempt within 4 check ticks"); c3/c4/c5 the responder,
network or machine off the clock: 3/3 pass (not load-bearing for the result; kept on the one clock as ntp's, since a real-
time responder makes the tick counts timing-dependent). Wiring bites in a scratch generated tree: wozi's I2C pins swapped
fails all 7 widened tests on wozi ("bad SCL pin"); wozi's BMP3XX at 0x76 (its setup fails, its task ends) and grkizi's FRAM
`max_size=0x40` (stores without a chunk) pass all 7: the assertions read the NTP state's RAM copies (finding 1). A FRAM CS
mismatch is no bite on the twin: its SPI routes no transfer by CS.

Formal pair, base = 111129f4's file then head (wall s; load 1-min avg, other heavy processes):
| file | -1 | 32768 |
|---|---|---|
| clock_jump | 17.54 -> 30.72 (+75 %), load 0.4, 0-2 others | 18.70 -> 38.41, load 0.4-0.6, 2-5 others |
| ntp | 36.86 -> 60.65 (+65 %), load 0.6-1.5 | 41.44 -> 74.29, load 1.5-9.2, up to 6 others |
Final head (after 4b and 6, load ~2): clock_jump 30.95 / 34.64 s, ntp 55.73 / 61.77 s.
**Residual** against base: clock_jump +13.4 / +15.9 s, ntp +18.9 / +20.3 s. Cause, measured: 9 added driven boots in
clock_jump and 15 in ntp, each paying the twin graph's CPU per virtual second. Of a boot through a silent fetch (the outage
and first-sync tests) 85 % of the real time is the IO queue's waits: 2.1-2.5 s of 2.6-2.9 s per arzi boot, 1,820 zero-
timeout rounds with a ThreadSafeFlag registered beside another stream, each paying the Unix port's 1 ms ioctl period. The
responder's 10 ms poll loop on the driven clock adds rounds too (the three tests took 18.7 s off the clock against 25.8 s
on it). Levers outside my files: finding 3.

## Item 2: scd30 and sgp40 (d87bd0d8)
- scd30's six `_reader_on_the_twin_bus()` callers: W, set arzi, dev. sgp40's three `_sgp40_bus()` callers: W, arzi, dev, wozi.
  Each caller loops over its set with the file's per-test reset (`machine.reset_test_state()`, which includes
  `reset_peripherals()` and also clears the Pin registry, so no irq handler of the previous device survives).
- Seen failing first: all 9 widened tests failed "left a task parked on the scheduler" (the SCD30 and ISL29125 fakes'
  measurement Timers on dev's shared i2c1). The helpers now stop every neighbour's own Timer; every occupant stays wired.
- Bite: a scratch twin `machine.py` garbling the first read byte on any bus with two or more chips: head 5/6 scd30 and 3/3
  sgp40 fail (on dev; CRC errors, setups false), the pre-widening files pass (arzi's buses hold one chip each).
- Pair (load 0.6-1.5): scd30 0.56 -> 1.22 / 1.00 -> 1.78 s; sgp40 0.37 -> 1.09 / 0.42 -> 1.12 s. Residual +0.7-0.8 s,
  the added device runs.

## Item 3: launch and the runner sites (eb6c4cb9)
- launch :51 `device_with("bmp3xx")`: reach probe on its main() runs: SCD30, SGP40 and BMP3XX on each device's buses
  (dev 2/2/3 to 10/6/9 transfers a run, wozi the same counts), no FRAM, LED or UART: W, set
  `distinct_wirings("bmp3xx", "scd30", "sgp40")` = dev, wozi. Efficiency: main() on one DrivenTime over launch, machine and
  network; summaries equal the real-clock ones (readings 2/8/2/3, the same wifi_status). Pair: 8.13 -> 0.28 / 8.17 -> 0.32 s.
  Bites: drive removed -> 4/4 time out; network off the clock -> the faults test fails (wifi_status 1); launch off the clock
  -> 4/4 fail at run_until; machine off the clock -> 4/4 pass (finding 4); wozi's plan with i2c1 pins swapped -> 4/4 fail
  on wozi (the base ran dev only).
- The brief names digital_twin/run_generic_integration.py, but CMr1c's :933/:1031/:1072 are in
  tests/test_digital_twin_run_generic_integration.py (resolved against 4cf293d0); no digital_twin/ file is edited.
  - :933 -> :1041 the real boot at a stored error level: W. The run ends inside WIFI's setup: 393 FRAM chip writes from the
    stores' entries on every device, and the armed SGP40 fault resolves its chip through the device's buses. Set
    `distinct_wirings("fram", "sgp40")` = arzi, dev, grkizi, wozi. Bite: grkizi's generated FRAM `max_size=0x40` fails
    it on grkizi ("FRAM allocation failed!" among CFGMGR_WIFI's lines).
  - :1031 -> :1096 and :1072 -> :1137 (`_IdleBoot` stand-ins): I. 0 transfers on arzi, dev, grkizi, wozi; on dev the
    runner's crossover wiring fails on the stand-in (no `uart_link_init`).
  - The section heading said "Exactly one" boot because the supervisor leaves tasks running; four boots in one test left
    no task parked, so the heading now states the per-wiring boot and the drain. Pair: 1.83 -> 2.53 / 1.82 -> 2.77 s.

## Item 4: the four bites (nothing planted is committed)
Each in a scratch root; the one-device version is the same test cut to its first device.
- network_neopixel (arzi, dev, grkizi): grkizi's generated FRAM `max_size=0x40` fails it on grkizi ("AssertionError:
  None": SYSTEM persisted nothing); the first device alone passes.
- neopixel_wifi timer list (arzi, dev, grkizi, wozi): wozi's generated `_collect_timer_starters()` given a None fails
  "wozi"; the first device alone passes.
- fram_less_boot (all six): a generator planted to hand the ISL29125 the FRAM logger fails only [dev] (`NameError:
  log_fram`), 11 others pass, [arzi] among them.
- `_lag_run` (all six): the loop-lag scenario planted to read the first device's bound fails 3 window cases on [dev] only.
- TOML-level bites were tried first and buildgen refused each: FRAM `max_size` 64 (legal 8192, 262144); `poll_idle_ms` 760
  (against the i2c1 timeout); i2c1 `timeout` 100000 (the SCD30's `@requires bus.timeout>=200000`).

## Item 4b: the boot link (b6f461fc)
- `earlier` holds the previous webserver's id(), with the same comparison.
- An AST scan of the twin tests and digital_twin/ found only these two boot-to-boot links: a device-module attribute
  captured before the same function's first boot call.
- Live heap after a collect, six re-boots of one case on arzi:
  - ntp base: 829,984 -> 977,024 -> ... 1,566,720, so +147,040, then +147,424 per re-boot. Head: 829,952 -> 829,792, then flat.
  - clock_jump base: +146,912, then +147,424 per re-boot. Head: +672 once, then 0.
  - At 32768 the step is the same in both files, and 0 after the cut.
- Pair (load 4-5): clock_jump 30.88 -> 30.52 / 36.13 -> 33.84 s; ntp 58.65 -> 55.31 / 73.09 -> 62.28 s.

## Item 5: matrices.md (34380155)
- One row per site, lines at b6f461fc, written in place.
- Merged in: CMr1i's ready rows, CMr1j's rows (integration :783/:916/:963/:981/:845, wifi_modes :323, loop_end :254/:274)
  and this lane's rows, with the bite results.
- 28 more tests_scripts `DEVICE_NAMES[0]` functions are classed I. CMr1i's 42 covered only 6 files; the rest are in
  scenarios, frozen_inputs_reproducible, generate_sensortask_modules, generated_tree, live_command_device_args,
  run_digital_twin_ci_sh, stage_website and ticks_wrap_scan.
- No "open" row is left. Nothing is left to paste.

## Item 6 (lines at deb50e1c; measured 2 runs per stage, load 9.3-9.5 with six other test processes)
| site | class | commit, row or reason |
|---|---|---|
| ntp :74 `_POLL_MS = 5` | R | deb50e1c, `l2.ntp_reply_poll_ms`: sleeps at most 9.78 ms (once 44.85) / 10.78 ms; answered request at most 10.76 / 10.99 ms, dropped 1103.84 / 1066.37 ms; the second responder within 40 looks |
| ntp :279 `200` | R | deb50e1c, `l2.ntp_starve_window_ms`: 175/173 ticks at -1, 171/172 at 32768, against the 50 needed |
| ntp :281 `sleep_ms(1)` | R | deb50e1c, `l2.ntp_starve_tick_ms`: each step at most 2.69 / 1.76 ms |
| ntp :412 `timeout_ms=100` (sendto) | test input, untagged | to a refused address the call returns in 0.14-0.19 ms: it fails before any wait |
| ntp :529 `timeout_ms=100` (`_write_to`) | test input, untagged | returns after 501.7-510.9 ms: the socket's own `udp.retry_backoff_ms` (500) after the refused connect. The bound is never reached |
| ntp :427 `_SYNC_POLL_MS = 50` | V | on the driven clock since a425deec (CMr1f), before this lane |
| clock_jump :63 `_POLL_MS = 50` | R | deb50e1c, `l2.clock_jump_poll_ms`: the stamps case's real `_until()`, 14 sleeps per run, each at most 51.84 / 53.25 ms. It also steps my item-1 driven waits; the stamps case was not moved in any commit |
Register reader: 19 passed. Bite 1, a tag removed: red, "l2.ntp_starve_tick_ms is a tuned row, but no file carries its
@tunable tag". Bite 2, a row removed: red, "l2.clock_jump_poll_ms is tagged but has no SPECIFICATION.md Part N row". No
value changed.

## Findings for the lead
1. The widened booted clock-jump and NTP tests catch a boot-breaking wiring fault, but not a fault confined to a reached
   part (wozi's BMP3XX address, grkizi's FRAM size): they assert NTP state only. This extends CMr1j's finding 3.
2. The grouping key cannot name the NTP client, which is no wiring instance. Its construction is identical on all six
   (checked), so no run is missed today; a device with its own NTP settings would share another device's run.
3. Efficiency levers outside my files, measured:
   - clock_jump could call `skip_idle_flag_polls()` as ntp does: 473 -> 113 ms of IO waits per comparable boot. The
     README names its callers, and suite-wide use is CMr1e's open decision.
   - The 1 ms ioctl period on zero-timeout rounds with a flag beside a socket is not covered by that skip (digital_twin/
     unix_port_idle_poll.py or the C override); it is 85 % of the outage-type boots.
   - The responder's 10 ms driven poll (digital_twin/unixport/_ntp_responder.py).
4. launch's long test (`l2.launch_long_min_readings` = 5) is met by the SGP40 and BMP3XX alone: 6 readings with machine
   off the clock. The SCD30 Timer reading its name claims is not pinned, at base too. It is a bound, so it is yours.
5. The scd30 and sgp40 per-device helpers keep their bodies verbatim, so a failure there does not name its device.
6. SPECIFICATION.md E.2.1 names neither these files nor their per-wiring runs. A possible D3 sentence: "The clock-jump,
   NTP, SCD30 and SGP40 twin-bus, launcher and runner twin files run each case that reaches a wired part once per
   distinct wiring of what it reaches, the booted and launched ones on one driven clock."

## Process notes
- Item 1's ntp edit was made with a scripted Python rewrite, not Edit/Write as the launch message asks. The diff was
  reviewed and the result is the same.
- The 32768 legs of the item-1 pair ran under rising load (up to 9.2). The item-6 measurements ran at load 9.3-9.5.
- The harness restart at about 18:11 cut none of my runs: every RUNS.md line had its done line and every log was
  complete. No line was written by hand and nothing was re-run for it.

nothing of mine is running
