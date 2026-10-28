CMr1i hand-back, written by the lane (2026-10-27)

Worktree S/wt-u35cm2, branch audit/u35-cm2, base 5a8c6e35. Logs, probes and scripts are in S/u35/laneC/cmr1i/:
times.txt, load.txt, item1.out, item2.out, after1.out, pair1.out, probe_extra.txt, reach_extra.txt, reach2_extra.txt,
item2_widening.patch and item3_sites.txt. Every run went through my one.sh or pyt.sh, with RUNS.md lines named U35 lane
CMr1i. I changed no wait's value. Not pushed. I stopped at the seam, at about 125 tool calls.

## Commits
- `84a9f1e4` U35 lane CMr1i: bus_hazard's SCD30 command and erase-race tests drive their boot, released before the
  supervisor (tests/_fake_time.py, tests/test_driven_time.py, tests/test_digital_twin_bus_hazard_concurrency.py).

Checks on the committed tree:
- lint_direct rc=0, with ruff over the eight scopes and build/generated_src.
- The three mypy passes are clean. The main and twin passes were re-run after the last edit.
- The tests_scripts readers (CMr1g's list of 32 files, the comment cap, citations, decision vocabulary, tunables and
  port bands among them): 1312 passed.

## Item 1: the release growth's cause, found and fixed in the harness
**Probe.** I rebuilt CMr1h's release() in a scratch copy of the two tests and ran it in three modes: base, drive and
count (item1.out). Sub-phases per boot, in ms (arzi / dev):

| phase | base | driven |
|---|---|---|
| `_boot` | 205-293 / 314-373 | 203-384 / 310-415 |
| graph (stagger + sequencer) | 1040-1058 / 1572-1600 | 190-239 / 496-564 |
| healthy window (first word) | 2731 / 2437 | 2732 / 2440 |
| command -> armed reset, words 2-4 | 101-102 / 101 | 2155-2160 / 2164-2168 |
| erase -> armed reset (arzi, grkizi / dev) | 233-287 / 1483-1550 | 2160-2235 / 3472-3579 |
| first word's command -> armed reset | 1436 / 1730 | 1436 / 1628 |

**Candidate A is refuted** (DrivenTime's Python time reads).
- Calls after release, counted per boot: ticks_ms 85-2,574; ticks_diff 43-1,162; ticks_us 0-521; forwarded names 10-11,192.
- Measured cost per call, DrivenTime against the real `time`:

  | call | DrivenTime | real |
  |---|---|---|
  | ticks_ms | 1.00 us | 0.36 us |
  | ticks_diff | 3.60 us | 0.40 us |
  | ticks_add | 2.79 us | 0.32 us |
  | a forwarded name | 1.34 us | 0.20 us |

- The worst boot (dev's erase) costs about 16 ms extra. All 11 boots together cost well under 0.1 s, against an 18 s growth.

**Candidate B is refuted** (the chips running on real time).
- The twin chips' only clock is the twin `machine.Timer`. Its `_run()` sleeps through `machine`'s own `asyncio`, and
  `machine` is one of `_driven_modules()`. The probe read machine_driven True on every boot.
- So the chips were on the driven clock. The healthy window is unchanged: 2732 vs 2731 ms, and 2440 vs 2437 ms.

**The cause, measured.** Every command after the first gains about 2.05 s, which is exactly one `_TASK_CHECK_TIME`
(2 s, src/asy_system_service.py:71).
- The shutdown sequence waits for the supervisor to park, and `_supervise()` parks only at the start of a pass.
- In the attempt, `_driven()`'s last `elapse()` settled the run queue after `_supervised_graph()` had created the
  supervisor task. The supervisor's first pass therefore ran inside the drive, and its 2 s check sleep was parked.
- release() then re-armed that sleep on the real clock, so the command waited out the rest of it.
- On the real clock the command is accepted before the supervisor's first pass, and the supervisor parks at once
  (101 ms).
- 9 such commands (the SCD30 test's words 2-4 on two devices, and 3 erases) x about 2.05 s = the 18 s.
- This is a harness artefact, not a product property: main() starts the supervisor after the stagger, as the base
  harness does.

**The fix** is in the harness only.
- `_supervised_graph(module, clock)` drives only `_start_graph()` (start_tasks()'s stagger and the timer sequencer),
  calls `clock.release()`, and only then creates the supervisor task, on the real clock as main() does.
- `DrivenTime.release()` (tests/_fake_time.py):
  - `now` runs on at the real rate from the instant reached;
  - each module's asyncio is the real one again;
  - each parked sleep and each wait_for() bound ends on the real clock after the time it had left, and a bound still
    awaits its own task;
  - a released clock refuses to move.
- Two self-tests in tests/test_driven_time.py pin it: 21/21 at both stages, 0.42 / 0.47 s.
- Every boot, wiring and assertion is kept.
- Bite: the drive's `clock.elapse(_POLL_MS)` replaced by a bare yield, so the boot wait never elapses. Both tests fail
  with "a driven step never ended" (bite_boot_m1.log).

**Formal pair.** The whole bus_hazard file, with 5a8c6e35's file as base, then the head. The load before each run is
in load.txt.

| stage | base | head | the two tests, base -> head | load (1-min avg, base / head) |
|---|---|---|---|---|
| -1 | 122.10 s | 112.91 s (-9.2 s, -7.5 %) | 23.69 + 6.71 = 30.40 s -> 16.89 + 3.99 = 20.88 s | 2.52 / 1.50, 3 runs on the host |
| 32768 | 133.55 s | 121.78 s (-11.8 s, -8.8 %) | 26.37 + 7.90 = 34.27 s -> 18.44 + 4.92 = 23.36 s | 1.79 / 3.35, 5 runs during head |

- 22/22 passed in all four runs, with zero memory markers. No other test moved by more than 1 s.
- Against base52 (CMr1g: 96.0 / 97.6 s) the file is still +17.6 % / +24.8 %. That remainder is CMr1h's measured
  residual, the real boots of the added wirings in the file's other tests. A boot costs arzi 1.26 s and dev 1.91 s on
  the real clock; driven, the two tests' boots now cost 0.43 / 0.87 s.

## Item 2: the 20 one-device skips against the wiring read, and the DHCP-trace test
**Measured; the widening is not committed** (CHECKLIST 14, below).

The reach probe (reach_extra.txt and reach2_extra.txt) counts the twin parts each scenario touches after its boot. It
ran on arzi, dev and grkizi, with the skip helpers bypassed in the probe copy (item2.out, after1.out).

| test (line at 5a8c6e35) | after its boot it touches | class |
|---|---|---|
| :756 DHCP trace | FRAM: 6 WIFI store writes, 366 chip writes, 126 reads. Its `get_error_counter()` read: 0 transfers (RAM) | W: `_driver_specific("fram")` -> arzi, dev, grkizi |
| :816 factory-state hotspot windows | nothing: no FRAM write, no LED frame, no bus transfer | I: stays `_first_device_only()` |
| :886 radio re-select | FRAM: 5 WIFI store writes, 305 chip writes | W: `_driver_specific("fram")` |
| :949 DNS idle rate (`_first_device_wiring("neopixel")`) | FRAM: 6 WIFI store writes. NeoPixel: 37-38 frames | W: `_driver_specific("neopixel", "fram")` -> arzi, dev, grkizi |
| :931 hotspot fallback (`_driver_specific("neopixel")`, a D skip, same `_hotspot_boot()`) | FRAM: 6 WIFI store writes. NeoPixel: 35 frames | W: `("neopixel", "fram")`, so grkizi is added |

- The DHCP test's read does not reach the FRAM wiring (0 transfers). Its own writes do, which fails the brief's wider
  condition ("reaches no part whose wiring differs").
- **The widening fails CHECKLIST 14, so I reverted it.** It is saved as cmr1i/item2_widening.patch (85 lines). The
  patch also removes `_first_device_wiring()`, which has no user left, puts the measured reason into each comment and
  keeps the `(agent, 2026-10-27)` tag.

The integration file on the two devices that gain runs, base (5a8c6e35) then head:

| device | -1: base -> head | 32768: base -> head | passed / skipped |
|---|---|---|---|
| dev | 32.53 -> 49.32 s (+52 %) | 35.31 -> 52.19 s (+48 %) | 14/4 -> 17/1 |
| grkizi | 25.22 -> 42.95 s (+70 %) | 26.90 -> 44.29 s (+65 %) | 8/10 -> 12/6 |

- Every run passed, with zero memory markers.
- The added scenarios cost, at -1 on dev / grkizi:

  | scenario | dev | grkizi |
  |---|---|---|
  | DHCP trace | 5.97 s | 5.87 s |
  | radio re-select | 6.67 s | 6.62 s |
  | DNS idle rate | 4.13 s | 4.00 s |
  | hotspot fallback | 1.07 s | 0.94 s |

- Their cost is real-clock Wi-Fi waits. The DNS window and the join/hotspot streaks run under `_SteppedAsyncio` and
  `_IDLE_WINDOW_S`.
- **For the next block:** the efficiency work these four need first is a driven clock for asy_wifi_service and
  asy_captive_dns in these scenarios (the bus_hazard technique). After that, apply the patch.
- The skip counts the patch gives: arzi 1, dev 1, grkizi 6, klkizi 14, schlafzi 14, wozi 7.

## Item 3: cmr1d item 3's sites (lines at 5a8c6e35), classed where measured; the widenings are left at the seam
**Clock_jump and ntp (reach2 probe, arzi), after the last boot:**

| test | reaches | class |
|---|---|---|
| clock_jump :304 cettime March switch | nothing | I: stays |
| clock_jump :328 year forward, two back | FRAM (5 writes), SGP40 0x59, SCD30 0x61, the general call 0x00, 5 LED frames | W |
| clock_jump :350 first sync | FRAM (66 writes, one an NTP store write), SGP40, SCD30, LED | W |
| clock_jump :372 NTP offset change | SGP40, SCD30, LED | W (task-graph traffic only, see the question) |
| ntp :442 first sync, clean log | SGP40, SCD30, LED | W (task-graph traffic only) |
| ntp :456 outage, back-off | FRAM (66 writes, one an NTP store write), SGP40, SCD30, LED | W |
| ntp :506 site (the failing-reply codes test) | FRAM (183 writes, 3 NTP store writes), SGP40, SCD30, LED | W |

**Question for the lead (CHECKLIST 1c).** In five of these tests the bus and LED traffic comes from the booted task
graph running beside the subject, not from the subject; in :372 and :442 it is the only reach. Under the literal
criterion every test with a running task graph is W. Does background task-graph traffic count as reach, or only what
the scenario's own subject drives (here, the NTP store's FRAM writes in :350, :456 and the :506 test)? The answer
decides :372 and :442. The other W rows stand either way.

**The other sites:**

| site | what it reads (measured) | class |
|---|---|---|
| tests/test_digital_twin_scd30.py:54 `_reader_on_the_twin_bus()` (5 callers: :553, :566, :586, :615 and one more) | the SCD30's bus, SCL/SDA, irq pin and every chip on that bus, from the plan. distinct_wirings("scd30") = arzi, dev | W, widening pending: each caller loops over the set with a per-iteration `machine.reset_peripherals()`. These are driver-only tests with no boot, so the cost is small |
| tests/test_digital_twin_sgp40.py:239 `_sgp40_bus()` (3 callers) | the SGP40's bus, pins and neighbours. Set = arzi, dev, wozi | W, widening pending, as above |
| tests/test_digital_twin_wifi_modes.py:160 `_scenario_plan()` | its own comment and item 2's measurement: the Wi-Fi LED's NeoPixel and WIFI's FRAM chunk. Set = arzi, dev, grkizi | W, widening pending. It is one test at the product's real waits, so the efficiency work comes first (CHECKLIST 14) |
| loop_end :236 `_first_device_only()` (8 tests) | after the last boot only task-graph traffic (SGP40, SCD30, 3 LED frames), with no FRAM transfer. The record crosses a reboot and is read during the next boot, which the probe's after-boot boundary cannot see | open: the next block measures where the loop-end record lives (FRAM is W, else I) |
| tests/test_digital_twin_launch.py:51 `device_with("bmp3xx")` | not measured | open: needs the reach probe on its main() runs. The bmp3xx set is dev, wozi |
| digital_twin/run_generic_integration.py (CMr1c's :933/:1031/:1072) | not re-located | open, class only (digital_twin/ is not this lane's to edit) |
| tests_scripts `DEVICE_NAMES[0]` sites: 42 tests in 6 files, listed in item3_sites.txt | each asserts a host build-chain behaviour that no device TOML reaches: CLI exit codes and one-line errors, a refused or patched source, staging/flag/record handling, a traced line set. Each file's per-device outputs are covered by its own DEVICE_NAMES-parametrized tests (api_reference 13, build_firmware 5, build_website_sh 3, buildgen_definitions 33, buildgen_generate 50) | I: stays; the device is a vehicle |
| tests_scripts/test_fram_less_boot.py :99, test_digital_twin_scenarios.py `_lag_run` (:285, :295) | the whole generated device without its FRAM, and its bound, link roles and timer list | W on all six, kept. Deduplicating needs a host-side read key (`distinct_wirings()` is MicroPython-side), which would be new tooling. Running all six over-covers and never under-covers |

## Item 4: the four bites
Not reached (seam): network_neopixel, neopixel_wifi, fram_less_boot and `_lag_run`.

## Item 5: matrices.md and E.2.1
**matrices.md is not edited.** Its "open" row cannot be closed this block: launch, loop_end and
run_generic_integration are unmeasured, and the item 2 and item 3 widenings are not applied. Rows ready to paste
(lines at 5a8c6e35):

| site | class | measured reason | device set |
|---|---|---|---|
| tests/test_digital_twin_sensortask_integration.py:756 DHCP trace, :886 radio re-select (now `_first_device_only()`) | W, widening pending efficiency work | after the boot, 6 / 5 WIFI store writes to the FRAM chip (366 / 305 chip writes). The slot read itself is RAM (0 transfers) | arzi, dev, grkizi |
| tests/test_digital_twin_sensortask_integration.py:949 DNS idle rate (`_first_device_wiring("neopixel")`), :931 hotspot fallback (`_driver_specific("neopixel")`) | W, widening pending efficiency work | the hotspot boot: 35-38 LED frames and 6 WIFI store writes to the FRAM chip | arzi, dev, grkizi |
| tests/test_digital_twin_sensortask_integration.py:816 factory-state hotspot windows `_first_device_only()` | I | after the boot it touches no wired part: 0 FRAM writes, 0 LED frames, 0 bus transfers | arzi |
| tests/test_digital_twin_bus_hazard_concurrency.py SCD30 system commands, erase race | W | sets unchanged. The boot is now driven and released before the supervisor (84a9f1e4) | arzi, dev / arzi, dev, grkizi |
| clock_jump :304 | I | after the boot it touches no wired part | arzi |
| clock_jump :328/:350, ntp :456 and the :506 test | W, widening pending | FRAM writes (the NTP store among them) plus SGP40/SCD30/LED | per the wired parts |
| clock_jump :372, ntp :442 | pending the lead's ruling | task-graph traffic only (SGP40, SCD30, LED) | - |
| scd30 :54, sgp40 :239, wifi_modes `_scenario_plan()` | W, widening pending | see item 3 | scd30: arzi, dev. sgp40: arzi, dev, wozi. wifi_modes: arzi, dev, grkizi |
| the tests_scripts `DEVICE_NAMES[0]` sites (42 tests, cmr1i/item3_sites.txt) | I | host build-chain mechanism. Per-device outputs are covered by each file's parametrized tests | the first device |
| tests_scripts/test_fram_less_boot.py :99, test_digital_twin_scenarios.py `_lag_run` :285/:295 | W, all six kept | deduplicating would need a host-side read key, which does not exist | all six |
| loop_end :236, launch :51, run_generic_integration (CMr1c's :933/:1031/:1072) | open | not measured this block | - |

**E.2.1.** CMr1h's text (its hand-back) matches the committed tree, where the Wi-Fi join, hotspot and radio
re-selection paths still run on the first device. Once item2_widening.patch lands, the text becomes:

"`tests/test_digital_twin_sensortask_integration.py` runs each driver-specific scenario once per distinct wiring of
the parts it reaches. Devices are grouped at run time by what the scenario reads of their generated plan and module:
each driver's construction statement and every module constant it names, and the pins and every occupant of each I2C
bus, SPI bus or UART pair one sits on. Each group runs on its first device, and a device not wiring the parts skips.
The Wi-Fi scenarios count among them the status LED and the FRAM their log entries are written to. A scenario that
reaches no wired part after its boot (the factory-state hotspot windows) runs only on the first generated device.
Every skip names the device that runs it instead."

nothing of mine is running
