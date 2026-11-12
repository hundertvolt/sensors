CMr1j hand-back, written by the lane (2026-10-27 15:23 UTC)

Worktree S/wt-u35cm2, branch audit/u35-cm2, base 9ce2e376 (its three test files equal 5a8c6e35's, so one base serves the
formal pairs and the residuals). Logs, scratch copies and bites in S/u35/laneC/cmr1j/ (times.txt, load.txt, final.out,
bites/). Every run went through my one.sh / many.sh / pair.sh / readers.sh / pyt.sh wrappers (namespace, nice 19,
RUNS.md lines), with one exception, below. No wait's value changed, no src/, digital_twin/ or SPEC edit. Not pushed.

## Commits
- `621350ed` the four Wi-Fi integration scenarios run on one driven clock.
- `e761bc2a` the integration file's Wi-Fi scenarios run per distinct wiring of what they reach (CMr1i's patch, applied by hand
  on top of item 1, with its DNS comment rewrapped: the patch's third line was 128 characters, a 4-line block for the cap).
- `c4189736` the Wi-Fi modes scenario runs on a driven clock, once per distinct LED and FRAM wiring.
- `562cf582` the loop-end record classes run on a driven clock, once per distinct device wiring.

Final head 562cf582: lint_direct rc=0; mypy main / twin / host clean (272 / 57 / 312 files); every changed file green at
both stages with zero memory markers (integration and loop_end on all six devices, wifi_modes once); the whole
tests_scripts tier: 7040 passed, 6 skipped, 6 failed, the same six as the lead's gate9ce at base (member_order in
src/asy_fram_manager.py, host_text_encoding, level_containment held_i2c_line/setup_resets, suppression_form in
test_digital_twin_sgp40.py:314, twin_record x2); none names a file of mine.

## Item 1: the four integration scenarios on one driven clock (621350ed)
Technique: `_on_driven_clock()` runs the scenario inside one DrivenTime(sleeps=True) over every module holding asyncio
(`_driven_modules()`, the sibling twin files' own); `_driven()` drives the boot; `_wait_until(..., clock=)` elapses the
clock per poll; `_SteppedAsyncio(clock=)` and `_ListenerSleeps` park their sleeps on it (same steps as before, so every
bound and the virtual timeline equal the base's real one); the DNS window and the burst's wait elapse it. Every assertion
and wiring kept; one added: the idle window asserts it lasted its length on the listener's clock (a vacuous window would
otherwise pass the rate check at 0 = 0).
Measured: `_boot()` (build_system + setups) takes 0 virtual ms on five devices and 20 ms on dev, 180-300 ms real CPU.

Bites (selection of the four, arzi at -1 unless named; control 4/4 green):
| bite | result |
|---|---|
| b1 the boot's drive never elapses | arzi 4/4 pass (vacuous: 0 virtual ms); dev: hotspot fallback fails "the boot - run_until: the condition still fails at virtual t=0 ms" |
| b2 a driven poll never elapses | 0/4: "the no-verdict streak never opened the hotspot", "real hotspot activation never started the real DNSServer task" (x2), "the station never linked before the fault" |
| b3 the DNS window never elapses | "the idle window lasted 0 ms of the listener's clock, not 3000" |
| b4 the burst's wait never elapses | "0 of 6 queries sent together were answered" |
| b5 the stepped Wi-Fi waits off the clock | DHCP "the no-verdict streak never opened the hotspot", radio "the station never linked before the fault"; the two hotspot-boot tests pass (their 10 ms real steps finish in the real time the 10 ms polls take; b2 shows those waits are driven) |
| b6 the listener's idle sleeps off the clock | "1 listener wake-ups in 3000 ms, not 30 +-1 at 100 ms" |
| b7 network (the twin's join) off the clock | DHCP "only 0 polls read joined without an IP over 5 attempts", radio "2 failed joins re-selected the radio 0 times, not once" |
| b8 machine (the twin's timers) off the clock | radio "the station never linked before the fault" |

Formal pair p1 (base file then head, per stage and device; load 1-min 1.9-3.9, beside it lane CO5's MicroPython run and
lane UM3's twin pytest probe):
| device | -1 | 32768 |
|---|---|---|
| arzi | 45.94 -> 31.43 s (-31.6 %) | 47.07 -> 33.38 s (-29.1 %) |
| dev | 32.46 -> 32.95 s | 35.55 -> 35.69 s |
| grkizi | 25.61 -> 26.71 s (none of the four runs there yet: load) | 26.62 -> 26.85 s |
Per scenario on arzi, -1 / 32768: DHCP 5.74 -> 0.27 / 5.83 -> 0.34; radio 6.49 -> 0.63 / 6.52 -> 0.76; DNS idle 3.94 -> 1.06
/ 3.98 -> 1.15; hotspot fallback 1.00 -> 0.91 / 1.00 -> 1.04 (dev 1.04 -> 0.99 / 1.20 -> 1.24). After a lean-up (the
listener's clock made required) the committed head re-ran on arzi: 31.55 / 33.25 s.

## Item 2: the widening (e761bc2a)
Skip counts as the patch says: arzi 1, dev 1, grkizi 6, klkizi 14, schlafzi 14, wozi 7.
Formal pair p2, all six devices (load rose 0.6 -> 4.8 during it, 4-7 other heavy processes of other lanes):
| device | -1 | 32768 |
|---|---|---|
| arzi | 45.80 -> 31.65 s (-30.9 %) | 47.13 -> 33.10 s (-29.8 %) |
| dev | 32.67 -> 34.79 s (+6.5 %) | 34.71 -> 37.76 s (+8.8 %) |
| grkizi | 25.60 -> 28.53 s (+11.4 %) | 26.66 -> 29.82 s (+11.9 %) |
| klkizi | 22.29 -> 22.40 s | 22.57 -> 23.32 s |
| schlafzi | 22.42 -> 22.84 s | 22.73 -> 23.29 s |
| wozi | 28.08 -> 28.18 s | 29.41 -> 31.15 s |
| sum | 176.86 -> 168.39 s (-4.8 %) | 183.21 -> 178.44 s (-2.6 %) |
Final head (fin_int): sum 169.71 / 177.92 s; grkizi 28.87 / 30.43 s, dev 35.06 / 37.61 s.
**Residual against 5a8c6e35's file**: dev +2.1 / +3.1 s, grkizi +2.9 / +3.2 s (+11.4 / +11.9 %). Cause: the added runs' CPU,
no wait time left. grkizi's four cost 3.21 / 3.57 s (DHCP 0.35, hotspot 0.96, DNS 1.19, radio 0.71 at -1), dev's three
2.54 / 3.08 s. Of that, each boot is 0.2-0.3 s of build_system + setups, and each hotspot boot ~0.65 s for its streak's six
persisted W entries: ~70 ms each while the LED overlay waits on its ThreadSafeFlag (10-13 ms each with the overlay not
started, measured on the same streak; every scheduler round of the write then polls the IO queue the flag sits in). The
unchanged klkizi/schlafzi/wozi files grew +0.1-1.7 s in the same pair: load drift. Merging the hotspot fallback into the
DNS test would save one hotspot boot (~0.9 s) per device but couples two tests; not done.
No wiring bite for the widening (the brief names none); see finding 3.

## Item 3: test_digital_twin_wifi_modes.py (c4189736)
The waits allow it: the boot is driven (`_driven`), both poll helpers elapse the clock, `_ScaledAsyncio` keeps its /5
scale with its sleeps on the clock; then one run per `distinct_wirings("neopixel", "fram")` = arzi, dev, grkizi, each after
the file's per-test reset, the device's module loaded before the clock is entered. Found while doing it: dev's boot,
awaited directly in the driven block, hung (its 20 ms boot wait): the reason the boot is driven, pinned by bite w4.
Bites (-1): w1 poll never elapses "(c) the boot streak never opened the hotspot's window"; w2 async poll never elapses
"('(c) a further check', [...])"; w3 scaled Wi-Fi sleeps off the clock "(c) the boot streak never opened the hotspot's
window"; w4 boot drive never elapses "the boot - run_until: ... virtual t=0 ms" (on dev; arzi boots in 0 virtual ms); w5
network off the clock "(b) the silent mode's attempt never linked once the access point was back"; w6 machine off the
clock: passes (the scenario fires its timers by hand, so no wait of machine's is load-bearing; machine stays on the clock
so every module shares one).
Formal pair p3 (load 5.2): 26.01 -> 8.04 s at -1, 26.28 -> 8.93 s at 32768 (base one device, head three). Final 7.97 / 8.40 s.

## Item 4: test_digital_twin_loop_end.py (562cf582)
`distinct_wirings()` (every instance) = arzi, dev, grkizi, wozi (klkizi and schlafzi read as one of them). The seven
first-device classes take `_per_distinct_wiring()`; the loop-core class keeps all six (never narrowed). Efficiency: both
boots of each class on one DrivenTime; the watcher elapses it until the entry's boot reaches the planted phase; the next
boot is driven to its last phase, then `release()`d, so the GET /status request, its server and the teardown run on the
real clock. Two variants compared on dev back to back twice: this one 16.8 / 16.8 s, the request polled on the driven
clock 20.8 / 20.9 s; the latter without a release also left run()'s reap unable to end a sensor `_read_loop` parked on
the clock ("the reap could not end a task the run created").
Observation point (for the lead): the next boot's /status is now read once that boot reached BOOT_DONE (the base read it as
soon as it served, mid-stagger), so each class also requires the next boot to finish within 20 s of virtual time; the
values read are fixed at boot and all eight classes read what they read before. Test-only, stricter.
Bites (arzi, -1): l1 the entry boot's drive never elapses: the 6 BOOT_DONE classes fail "the boot never reached phase 6"
(the watcher's _BootTimeoutError), the 2 BOOT_SETUP classes pass (setup is reached at 0 virtual ms); l2 the next boot's
drive never elapses: 8/8 fail "the next boot never reached its last phase - run_until: ...".
Formal pair p4b (committed version; load 5.4-5.6 throughout):
| device | -1 | 32768 |
|---|---|---|
| arzi | 19.07 -> 9.98 s | 19.67 -> 11.08 s |
| dev | 4.05 -> 19.51 s (1 -> 8 classes) | 4.36 -> 20.03 s |
| grkizi | 3.19 -> 9.91 s (1 -> 8) | 3.19 -> 11.00 s |
| klkizi | 3.04 -> 2.61 s | 3.15 -> 2.87 s |
| schlafzi | 3.28 -> 2.69 s | 3.21 -> 2.72 s |
| wozi | 3.60 -> 12.44 s (1 -> 8) | 3.96 -> 13.12 s |
| sum | 36.23 -> 57.14 s (+57.7 %) | 37.54 -> 60.82 s (+62.0 %) |
(p4, the version before the teardown release moved into a finally: sum 36.01 -> 55.83 / 37.49 -> 61.49 s; dev varies
17.0-19.9 s run to run at this load.) Final: sum 56.75 / 59.94 s.
**Residual**: +20.9 / +23.3 s. Cause: 21 added runs (7 classes x dev, grkizi, wozi), each two booted graphs' CPU on the
twin, no wait time left: the entry's boot to its phase (arzi 0.6 s real for 995 virtual ms, dev 1.1 s for 1510) and the
next boot to its last phase (arzi 0.4 s, dev 0.78 s), plus one GET /status (0.2-0.3 s). Per class the time fell 40-50 %
(arzi's 8 classes 19.1 -> 10.0 s; dev's single class 3.73 -> 2.27 s).
Across the three files together: 239.10 -> 234.43 s at -1, 247.03 -> 246.26 s at 32768, with 30 more device runs.

## Findings for the lead
1. Base flake, seen once: on the base file, arzi at 32768 (p2_base_arzi_t), `test_a_supervised_task_death_reaches_the_console_
   through_the_pc_report_at_level_0` failed "32 B retained per supervised death: [946816, 945600, 945280, 945280, 945280,
   945280, 945696, 945280, 945472, 945472]": the median pairwise slope of the seven settled readings is exactly 32 (one +416
   B transient at death 6, +192 B at deaths 8 and 9) against `slope < 32`; `_DRIFT_SLOPE_BYTES`'s own comment names this
   mode ("two transients at the last two deaths read 38 B"). It passed in the other base arzi runs (p1 both stages, p2 -1) and
   in all eight head arzi runs (p1, c1, p2, final, both stages each); I did not touch it (a bound is the lead's).
2. Persisted entries cost ~70 ms of CPU each on the twin while the NeoPixel overlay waits in `wait_for_ms(ThreadSafeFlag.wait(),
   ...)`, 10-13 ms without it (finding of the probe above; not checked against rp2 or the asyncio source; product and twin
   files are not mine).
3. The widened integration Wi-Fi scenarios reach each device's FRAM through their writes, but their assertions read the error
   log's RAM copy: a FRAM-only wiring fault that leaves the write path non-raising would pass on every device.
4. SPECIFICATION.md is stale on these files: E.2.1's two paragraphs (:5160-5170 at 9ce2e376) and the tunables row for
   `l2.wifi_modes_sleep_scale` (:12571, "here about 26 s against 101 s unscaled"): on the driven clock the scale saves no wall
   time; it is kept so the virtual timeline and the 25 s poll bounds stay the base's. Text below.

## Process notes
- One short pytest run (cap2: comment cap, citations, decision vocabulary, 671 passed, 30 s) ran niced with RUNS.md lines but
  without `unshare -n`; every other run used the namespace wrapper.
- A `sleep 60` was blocked by the harness's own rule against chained sleeps (not a permission refusal); I waited with
  `tail --pid` from then on. No command was refused.

## Matrices rows (lines at 562cf582)
| site | class | measured reason | device set |
|---|---|---|---|
| tests/test_digital_twin_sensortask_integration.py:778 DHCP trace, :911 radio re-select (`_driver_specific("fram")`) | W, widened, on a driven clock | after the boot, 6 / 5 WIFI store writes to the FRAM chip (366 / 305 chip writes); the slot read is RAM | arzi, dev, grkizi |
| tests/test_digital_twin_sensortask_integration.py:958 hotspot fallback, :976 DNS idle rate (`_driver_specific("neopixel", "fram")`) | W, widened, on a driven clock | the hotspot boot: 35-38 LED frames and 6 WIFI store writes to the FRAM chip | arzi, dev, grkizi |
| tests/test_digital_twin_sensortask_integration.py:840 factory-state hotspot windows (`_first_device_only()`) | I | after the boot no wired part: 0 FRAM writes, 0 LED frames, 0 bus transfers | arzi |
| tests/test_digital_twin_wifi_modes.py:230 the modes scenario (`distinct_wirings("neopixel", "fram")`, :323) | W, widened, on a driven clock | the Wi-Fi LED's NeoPixel and WIFI's FRAM chunk, as for the hotspot rows | arzi, dev, grkizi |
| tests/test_digital_twin_loop_end.py:281-333, its seven classes (`_per_distinct_wiring()`, :254) | W, widened, on a driven clock (lead's ruling: the booted graph's traffic counts) | the record is written and read beside the whole booted graph (SGP40, SCD30 and LED traffic after the last boot, CMr1i) | arzi, dev, grkizi, wozi |
| tests/test_digital_twin_loop_end.py:274 the loop-core class | W, all six kept | as above | all six |

## E.2.1 text (SPECIFICATION.md :5160-5170 at 9ce2e376 replaced; for D3)
"`tests/test_digital_twin_sensortask_integration.py` runs each driver-specific scenario once per distinct wiring of the
parts it reaches. Devices are grouped at run time by what the scenario reads of their generated plan and module: each
driver's construction statement and every module constant it names, and the pins and every occupant of each I2C bus, SPI
bus or UART pair one sits on. Each group runs on its first device, and a device not wiring the parts skips. The Wi-Fi
scenarios count among them the status LED and the FRAM their log entries are written to, and run on one driven clock
(`tests/_fake_time.py`'s DrivenTime over every module holding asyncio), so their seconds of waits take no wall clock. A
scenario that reaches no wired part after its boot (the factory-state hotspot windows) runs only on the first generated
device. Every skip names the device that runs it instead.
`tests/test_digital_twin_wifi_modes.py` walks the Wi-Fi modes after a hotspot ran (the stations rule, a reconnecting
settings change landing in the fresh-boot state, the silent mode) in one boot per distinct wiring of the NeoPixel and the
FRAM the scenario reads, each on a fresh board, with the WiFi service's own sleeps `l2.wifi_modes_sleep_scale` times shorter
on one driven clock — its transitions are under test, not its periods — about 8 s for its three devices.
`tests/test_digital_twin_loop_end.py` runs each loop-end class once per distinct wiring of every instance a device wires,
since the record is written and read beside the whole booted graph, both boots of each on a driven clock; its loop-core
class runs on every device (agent, 2026-10-27)."
Tunables row :12571, reason column: "the WiFi service's own sleeps run this many times faster on the driven clock, which
keeps the scenario's virtual timeline and its 25 s poll bounds; it saves no wall time there (about 8 s for three devices)".

nothing of mine is running
