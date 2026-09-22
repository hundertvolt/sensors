# tests_hardware/ - real-hardware test tier

Implements SPECIFICATION.md Part E.6's flash/bench/manual backends: automated tests driven from the
host over `mpremote`/`nmcli`/`iptables` (never the MicroPython Unix port `tests/` uses - see
SPECIFICATION.md Part E.1), plus a structurally separate manual runner for tests that need a human's
hands. **Real-hardware execution is standing practice on the bench Pi4** - the flash and bench tiers
have run clean end to end on real hardware, with additional coverage added since; this file is the
durable reference for prerequisites, environment variables, how to run it, and the facts/assumptions
worth knowing before trusting a run's results.

**Any session about to run real-hardware tests against this tier needs the project owner's
go-ahead first, given directly in that session's own conversation** - see CLAUDE.md's own hard rule
on this. Once granted, this file has everything else needed: prerequisites below, environment
variables, the critical safety facts folded into "Known assumptions and open findings" (the
`--allow-flash-cycle`/long-soak opt-in gates in "Running" below, the stage-6 permanent-WLAN-
deactivation risk, `BENCH_AP_PASSWORD` handling in "Environment variables" below).

## Prerequisites

1. `uv run toolchain/setup_toolchain.py env --tier flash` (real USB board attached) or `--tier
   bench` (also needs a WiFi adapter for the bridge) - see README.md's own environment-tiers table
   and `toolchain/setup_toolchain.py`'s own docstring for the full recipe (dialout group, device
   auto-detection, `br0-wifi-ap` bridge creation via `ensure_bench_bridge()`).
2. The board must already be running the real `dev` firmware
   (SPECIFICATION.md Part E.6.3's "one allowed flash" - `uv run scripts/build_firmware.py dev` +
   `picotool load -x -v`, or the manual BOOTSEL-button first flash for a genuinely blank board, see
   `tests_hardware/manual/manual_toolchain.py`). **Never `scripts/build_firmware.py wozi` against
   this bench** - `wozi` is never physically flashed, only `dev` is (CLAUDE.md's hard rule); `wozi`'s
   own hardcoded pins don't match this bench's real wiring.
3. **`picotool` needs real USB support to actually flash anything.** The toolchain build this
   session ran (`uv run toolchain/setup_toolchain.py setup`) produced a `picotool` explicitly
   compiled *without* USB support (confirmed directly: its own `--help` output prints "This version
   of picotool was compiled without USB support. Some commands are not available." - this sandbox
   had no real USB device for the build to detect/link against). Before running anything that calls
   `picotool load` (`tests_hardware/flash/test_toolchain_flash_boot.py`'s
   `test_real_uf2_reflash_and_boot_smoke_test`, `tests_hardware/manual/manual_toolchain.py`),
   rebuild picotool on the real hardware session's own machine (or confirm the apt-packaged
   `picotool` there already has USB support - check for the same warning line) rather than assuming
   this session's cached build works.
4. **The NeoPixel sweep rig** - only for `--allow-neopixel-sweep`, and not provisioned by any
   `setup_toolchain.py` tier because it is physical, not software. The board's own WS2812 (GP18 on
   this bench) has to be aimed at the ISL29125's window at a fixed, recorded distance, with ambient
   light excluded (an enclosure or a darkened room). Two flash-tier tests depend on it -
   `test_isl29125_mechanism_envelope_holds_across_range_resolution_and_calibration` and
   `test_isl29125_survives_recombined_realistic_lighting_scenarios` - and without the rig they fail
   outright rather than mis-measuring, which is why both are opt-in and skip by default. Setting the
   rig up and writing its geometry down is the manual tier's own
   `isl29125_real_lux_vs_reference_meter_and_neopixel_rig_geometry`; run that once, record the
   distance here, and the automated pair becomes meaningful. They are also the suite's longest pair
   at roughly ten minutes combined, so opting in is a deliberate choice about wall clock as well.

## Environment variables

- `MPREMOTE_DEVICE` (or `--device` on any `pytest tests_hardware` invocation) - serial device path
  for the flash-tier board. With neither set, `harness.resolve_board_device()` identifies the board
  by USB vendor ID - `toolchain/setup_toolchain.py`'s own `detect_pico_serial_devices()`, so the two
  cannot disagree - and returns its `/dev/serial/by-id/...` symlink, which is named by USB serial
  number and so survives the re-enumeration a hard reset causes. Two boards attached is a hard error
  naming both rather than a silent pick; none attached returns a path that cannot exist, so the
  `board` fixture skips without mpremote opening some other device's port to find that out. Either
  variable pins the path outright, and a pinned path is never re-resolved.
  `scripts/mpremote_connect.sh` still defaults to `/dev/ttyACM0`, making it the one entry point a
  re-enumeration can still strand - pass `MPREMOTE_DEVICE` there if the node has moved.
- `BENCH_AP_PASSWORD` - **optional, not required for a normal run** (fixed 2026-09-08 - see
  BACKLOG.md open question 9 for the full incident this used to cause).
  `tests_hardware/bench/test_hotspot_role_reversal.py::test_real_credentials_put_succeeds_and_confirms_accepted_values`
  (stage 6's real credential handoff) now defaults to `bench.ap_password()` - the real bench bridge
  AP's own password, read live from `nmcli --show-secrets` under the same sudo access this whole
  tier already has for everything else (the same mechanism `conftest.py`'s own
  `_recover_stale_dut_credentials()` already relied on). This env var only matters if you need to
  override that with a different password (e.g. testing against a non-bench AP `nmcli` can't read
  secrets back from) - set it and it takes priority over the automatic lookup. **Do not rely on this
  test skipping cleanly if you deliberately want to skip stage 6/7** - it no longer skips on its own;
  a real bench (`ensure_bench_bridge()`-created `br0-wifi-ap`) always has a readable password.

## Running

```bash
# Automated, flash tier only (real USB board, no network):
scripts/run_flash_hardware_suite.sh

# Automated, flash + bench tier (real USB board + real WiFi bridge):
scripts/run_bench_hardware_suite.sh

# Soak tests (long_soak marker) are NEVER bundled into either suite runner above - they always
# need their own deliberate, dedicated invocation, one of three named tiers (short=60s/mid=600s/
# long=6h - see tests_hardware/conftest.py's own SOAK_TIER_SECONDS):
scripts/run_bench_soak_tests.sh --tier short   # quick mechanism/assertion check, CI-time
scripts/run_bench_soak_tests.sh --tier mid     # a few minutes
scripts/run_bench_soak_tests.sh --tier long    # the real 6h production duration

# The one real, fixed ~12.4-day wait (time.ticks_ms()'s 2**30 rollover) is its own separate flag,
# never bundled with any soak tier - run directly, on purpose, only when a session genuinely
# intends a multi-day wait:
uv run pytest tests_hardware/flash --allow-multi-day-rollover-wait -k test_ticks_ms_real_2pow30_rollover

# Add --allow-flash-cycle to also run the one deliberate re-provisioning-flash test (skipped by
# default - this genuinely re-flashes the board, see SPECIFICATION.md Part E.6.3):
scripts/run_flash_hardware_suite.sh --allow-flash-cycle

# SCD30 NVM writes are off by default (flash wear on real hardware) - a plain run above spends zero
# real SCD30 writes, and every SCD30-dependent bus-hazard test (routine or additional) deselects
# cleanly. Add --allow-persistence-writes for the global permission (runs the routine group, one real
# write for the whole session); add --allow-scd30-extra-write ON TOP of that (AND-gated, not a
# substitute) to also run the one test that spends a SECOND real write (skipped/deselected by
# default - same precedent as --allow-flash-cycle; see SPECIFICATION.md Part C.8's bus-hazard
# promotion checklist and bus_concurrency_scd30_write_vs_siblings.py's own docstring):
scripts/run_flash_hardware_suite.sh --allow-persistence-writes
scripts/run_flash_hardware_suite.sh --allow-persistence-writes --allow-scd30-extra-write

# The two long ISL29125 light programs need a PHYSICAL rig, not a permission: the on-board WS2812
# aimed at the sensor's window at a fixed distance with ambient light excluded (see "The NeoPixel
# sweep rig" below). Without it they FAIL rather than mis-measure, and they cost ~10 minutes when
# they do run - so they are opt-in, and skip by default:
scripts/run_flash_hardware_suite.sh --allow-neopixel-sweep

# Manual tests (interactive, prints instructions, waits for confirmation):
scripts/run_manual_hardware_tests.sh --list          # see what's registered, run nothing
scripts/run_manual_hardware_tests.sh --only <name>   # run just one
scripts/run_manual_hardware_tests.sh                 # run all of them, in sequence
```

Both automated scripts are plain `uv run pytest` wrappers - any pytest flag works (`-k <substring>`,
`-m role_reversal`, `-v`, `--tb=short`, ...). `--collect-only` works with nothing attached at all
(every fixture skips cleanly, never errors, when the hardware it needs isn't reachable).

**Why both wrappers go through `scripts/_require_clean_hardware_run.sh` rather than trusting
pytest's exit code.** That clean-skip design is what makes a run against genuinely *unreachable*
hardware look identical at the exit-code level to a real clean run: pytest exits 0 for an
all-skipped run exactly as it does for an all-passed one. These wrappers exist to run against real,
attached hardware, so that ambiguity must never pass silently - every expected test has to show
PASSED, not quietly skip. The helper therefore inspects pytest's own output (which is also why it
runs without `set -e`) and fails on any skip beyond three deliberate classes:

- `KNOWN_PERMANENT_SKIPS`, one documented, permanent entry at a time - never a way to silence a
  real skip.
- The opt-in gates that skip per test (`--allow-flash-cycle`, `--soak-tier`,
  `--allow-multi-day-rollover-wait`, `--allow-neopixel-sweep`), each accepted *only* when its own
  flag is absent from that invocation. Pass the flag and still get a skip, and it fails.
- The gates that deselect at collection time instead (`--allow-persistence-writes`,
  `--allow-scd30-extra-write`), which no check in that script can see at all - hence the deselected
  count in its verdict, described under "Read the deselected count in the verdict" below.

The soak markers are a non-case for the whitelist: both general wrappers pass
`-m "not long_soak and not multi_day_rollover"`, so those tests are deselected rather than skipped.
The entry matters only for a direct invocation that omits that exclusion, such as
`scripts/run_bench_soak_tests.sh`'s own `-m long_soak` selection - where `--soak-tier` *is*
expected, making those tests "must pass" rather than "may skip".

## The NeoPixel sweep rig

Two flash-tier tests are gated on physical geometry rather than on wear or wall clock -
`test_isl29125_mechanism_envelope_holds_across_range_resolution_and_calibration` and
`test_isl29125_survives_recombined_realistic_lighting_scenarios`, both behind `--allow-neopixel-sweep`
and both whitelisted in `scripts/_require_clean_hardware_run.sh` so an expected skip does not read as
a failure. What the rig needs:

- The dev board's own WS2812 (GP18) aimed at the ISL29125's window at a fixed, recorded distance -
  close enough that full-brightness white crosses the 375 lx range's top into the 10000 lx range.
  Record the geometry through the manual tier's
  `isl29125_real_lux_vs_reference_meter_and_neopixel_rig_geometry`.
- Ambient excluded (enclosure or darkened room). Ambient above the low range puts the whole run on
  the high range and fails with "only range N was ever used" - a rig fault, not a driver one.
- Nothing else driving the pixel: these scripts go through `request_signal()`'s real arbitration, and
  a notification signal landing mid-scenario is indistinguishable from a bad reading.

Every assertion is **relative** - continuity across the switch, no chatter, hue/saturation invariance
while the level moves, gain-ratio convergence. Absolute lux and CCT against a WS2812's three narrow
emission lines are meaningless and are asserted nowhere; the reference-meter half is the manual
tier's job. CLAUDE.md's FRAM rule applies in its sharpest form to every script here - see "A hardware
run overwrites the production modules' FRAM chunks" below before treating any log as evidence.

## ISL29125 bench-rig facts, before reading any result

Each of these looks like a driver defect and is not:

- **An interrupted `main.py` leaves the WS2812 latched**, often at full white (~2000 lx at this
  geometry), because a WS2812 holds its last value and every `mpremote run` interrupts `main.py`.
  Every ISL29125 script that reads light therefore parks the pixel dark itself and takes an ambient
  baseline first. Found twice: a register probe read 65444/65272/65323 and was briefly taken for real
  saturation (parked dark, the same bench reads ~40 lx, 10.7% of the low range); and
  `isl29125_real_irq_edge.py` failed its first real run because latched white is a **static** scene -
  it crosses no threshold, no interrupt fires, and the first sample waits for the 30 s periodic tick.
  Parked dark it passes in 0.60 s.
- **The sensor can be covered or uncovered between runs** (~40 lx uncovered here, far less covered),
  so nothing compares an absolute reading across a cover change and the return-to-baseline check uses
  an LED-dominated level rather than ambient.
- **The breakout carries its own red LEDs**, so red reads systematically high against green and blue.
  Nothing asserts channel equality or a specific hue, only that HSB stays in domain and coherent with
  RGB.
- **The auto-range hysteresis band**, measured covered at this geometry (2026-09-12), in NeoPixel
  levels:

  | direction | low range (375 lx) holds | high range (10000 lx) takes over |
  |---|---|---|
  | rising | to level 6 (~197 lx) | from level 8 (~300 lx) |
  | falling | from level 2 (~76 lx) | to level 3 (~112 lx) |

  **Levels 2-8 sit inside the band and cannot force a switch either way.** Re-measure if the rig or
  the cover changes.

## Which path decides a range switch

Measured 2026-09-13, six forced crossings per setting. The chip cannot raise `RGBTHF` before `PRST`
whole RGB cycles have passed (303 ms each at 16 bit), while the driver re-checks the same condition
in software every sample with no persistence requirement. **The shorter window decides every switch.**

| `PRST` | window at 16 bit | against `SampleInterv = 1` | measured |
|---|---|---|---|
| 4 | 1212 ms | longer - software wins | 5 of 6 periodic-led, latency ~1000 ms |
| 2 | 606 ms | shorter - interrupt wins | 6 of 6 interrupt-led, 500-800 ms |
| 1 | 303 ms | shorter - interrupt wins | 6 of 6 interrupt-led, 200-613 ms |

That is why the window is derived rather than configured (SPECIFICATION.md Part C.11.1.3), and why
`wrnno=13` - five range decisions in a row taken by the periodic path - means the INT line looks dead
rather than that a setting is wrong.

## What the two gated light tests prove

- **Mechanism envelope** (`isl29125_mechanism_envelope.py`, ~99 s of settles alone): eight steady
  levels up and back down through the overlay path, never a ramp - a ramp confounds the range step
  with the light's own change. One run proves a live read chain at every level, `Bri == max(R, G, B)`
  with every field in domain, monotonic response across the envelope, both ranges used, hysteresis
  with no chatter, the return to the low range, fixed-range pinning at both ends, 12-bit and 16-bit
  agreeing on one static scene (which is what proves the `<< 4` normalisation), `ISLCalibrate`
  starting a run without moving the applied ratio, `Overrange` true at full white (this rig really
  does exceed 10000 lx at ~20 mm), no `W13`, and zero `E` entries.
- **Lighting scenarios** (`isl29125_lighting_scenarios.py`, ~8.5 min of real segments): ten scenarios
  recombining colour, slope shape, direction, start/end level, pauses and threshold proximity, driven
  **raw** because `NeopixelDriver` offers only a steady white and a 0->peak->0 triangle. Two
  cross-scenario invariants: the inter-sample gap stays at the sample interval (a stall means the read
  chain died, not that the light moved slowly), and a return-to-baseline re-read after each scenario
  catches a driver left wedged in a range.

## Writing a new device script: four habits

A test depending on an unstated rig condition is this tier's recurring failure mode - six instances
so far, every one found by running the test rather than reading it, and every one green first:

- **Provide your own light.** `isl29125_plausibility_read.py` passed while a preceding test left the
  pixel latched white, then failed once another parked it dark - its result depended on test ORDER,
  with the script itself unchanged.
- **Restore or side-step every piece of shared state you touch** - light, config files, FRAM chunks.
  The envelope script once seeded `cfgmgr._cache` without calling `setup()`, so its `_set_dict_cfg()`
  calls wrote that cache over the board's real `config_ISL29125.cfg`: six silent flash writes per run.
- **Assert a minimum engagement beside every ceiling**, or a test passes while the mechanism it
  targets never runs. A "no `W13`" check proves nothing in a run making two switches when the warning
  needs five in a row, and an oscillation scenario passed with `switches=0` because both its levels
  sat inside the band. Every scenario now carries `min_switches` and a must-use-both-ranges flag
  beside its ceiling: `threshold_oscillation_crossing` must switch at least 4 times and
  `hysteresis_band_dwell_no_chatter` exactly zero, so an edit making either vacuous fails the other.
- **`await flush_pending()` after any config write.** `write_config()` only *stages*; the flash write
  is its own task (SPECIFICATION.md Part F.2). Production keeps an event loop running, but a device
  script that writes and then returns lets `asyncio.run()` discard the flush, and the file is left
  holding `setup()`'s defaults - while `write_config()` has already reported success. This silently
  broke three scripts: the reboot-persistence marker never persisted, and the DebugLevel pair backed
  up `PrevLevel: 0` instead of the real 5 and then "restored" that, the two omissions cancelling so
  the *test passed*. Fixing only one of that pair drives the bench board to `DebugLevel = 0`.
  `tests_scripts/test_device_script_config_flush.py` now pins this. Full account: MEASUREMENTS 7O.

## Writing a new bench-tier test, and diagnosing a DUT that has gone quiet: two traps

Both cost real bench time more than once, and neither is discoverable by reading the code.

- **A DUT that has gone unreachable is usually your own `mpremote` call, and every serial check you
  make to diagnose it re-causes the symptom.** `exec` and `run` interrupt the running firmware into
  the REPL, so `main.py` stops and the board leaves the network; `run_isolated()`'s armed
  `WDT(timeout=8000)` then resets it ~8 s after the command ends. It cost time on 2026-09-18 and
  again on 2026-09-19, each time as the same loop: curl fails -> `exec` to inspect the config ->
  the inspection strands `main.py` again -> curl still fails. **The config was intact every time.**
  Diagnose *passively*: `hard_reset()`, then `Board.tail_log()` with no `exec`/`run` at all, and
  only then curl. `tail_log()` replays buffered history, so several identical "WLAN connection
  established" blocks are **not** a reboot loop - poll `SysUptime` and watch it advance, which is
  the cheap discriminator.
- **A test that opens more concurrent connections than `max_connections = 4` cannot expect a
  definitive status from all of them**, whatever it is testing. `_serve()`'s reject-when-full branch
  closes without writing a response, and `src/` does not choose whether the client sees FIN or RST -
  `test_connections_at_and_above_the_real_socket_limit_degrade_cleanly` accepts either for exactly
  that reason. Measured 2026-09-19 with tiny bodies, so it is nothing to do with payload size:
  concurrency 2 -> 0% reset, 4 -> 25%, 8 -> 12%, 24 -> 25%. Resets begin **at** the ceiling, not
  beyond it. **Before calling such a reset a defect, run the all-small-bodies control** - two
  minutes, and it separates the feature under test from the connection ceiling. It is what turned a
  suspected request-body-cap defect into a measured property of the server.

Both halves of the second trap generalise into one rule for any test that exceeds the ceiling:
**assert the property your feature owns, not that every client is served.** A body-cap test owns
"every client that IS answered is answered correctly"; being answered at all is the ceiling's
business. Pair that with a floor on how many were answered, or the test passes vacuously on a run
where nearly everything was refused - the same "assert a minimum engagement beside every ceiling"
habit the section above states for device scripts.

## The ISL29125 mock-conformance probe

`test_isl29125_register_probe_matches_the_digital_twins_fake_chip` is the only test in this tier that
checks the **digital twin** rather than the firmware: `device_scripts/isl29125_mock_conformance_probe.py`
runs against the real part and then against `digital_twin/_isl29125_chip.py` under the Unix port, and
every protocol key is diffed (`tests_hardware/isl29125_conformance.py` holds the shared expectation
table). It talks raw `machine.I2C` only, so it needs nothing from `src/` on the board and no
`mpremote mount`, and it needs the Unix port already built - it raises a `FileNotFoundError` naming
the path rather than skipping. A failure means the fake and the part disagree: decide which is wrong
from the datasheet **and** a fresh measurement, never from the fake (SPECIFICATION.md Part C.11.1
lists what the first real run found).

## Known assumptions and open findings

Flagged while writing this tier against real source/datasheets, or found once real-hardware runs
started. Read them before trusting a run's results blindly - a failure in one of these areas may
point at a flagged assumption being wrong, not at a real product bug. Resolved items are struck
through, kept (not deleted) so a reader mid-investigation doesn't wonder whether something was ever
a live question:

- ~~The bench has never run MicroPython 1.29.0.~~ — **resolved (2026-09-11): it has, repeatedly.**
  Real `dev` firmware built from `src/` and flashed, with the flash, bench and mid soak tiers all
  run clean against it. All three items that wanted on-target confirmation are answered: the SPI
  RX-overrun raise site and the `deinit()` no-ops (both in BACKLOG.md's "Deferred" list), and the
  SRAM-placement change, now measured rather than inferred (SPECIFICATION.md Part F.5.3).
- **A hardware run overwrites the production modules' FRAM chunks — never read an error log as
  firmware evidence straight after one.** `AsyFramManager` is a deterministic bump allocator (a
  required property, SPECIFICATION.md Part A.4), so a device script's own first chunk *is*
  production's first chunk. Usually the next boot's `_read()` just fails on the size/CRC mismatch
  and the log honestly reads empty — but a script leaving a well-formed chunk behind fabricates a
  plausible one. `fram_error_log_reset_race_seed_and_race.py` seeds three `errno=5` entries into
  what is physically SystemService's chunk, which reads back as SYSTEM's own
  `"Task N ended with exception"` (chased down as real on 2026-09-11; it was test data). CLAUDE.md's
  "read the FRAM logs before clearing" rule assumes a board that has been running normally — check
  what was last run against this one first.
- **The UART crossover coverage is 5 flash-tier tests and 3 bench-tier tests, all passing as part
  of the full sweep** (2026-09-12: `run_bench_hardware_suite.sh` → 96 passed, 2 known-permanent
  skips, 41 min, with the four SCD30-EEPROM-write tests deselected). Three of the flash tests and
  one of the bench tests were added in that session; the rest date from 2026-09-11.
  Two platform findings are asserted rather than merely documented: F.5.8's clamped-read CPU hold
  (`uart_read_never_blocks_the_loop.py` — measured 4394 us unclamped against 121 us clamped) and
  F.5.9's idle poll rate (`uart_idle_poll_rate.py` — 1336/1266 rounds at 2 ms against 60/60 at
  50 ms over 3 s). A third, `uart_link_under_concurrent_system_load.py`, runs the link against both
  I2C devices, the FRAM's SPI bus and heavy allocation churn at once, and asserts in both
  directions — the link keeps transferring *and* nothing else was starved.
  The bench tier's "a transfer completes while the API is hammered" claim used to be vacuous and no
  longer is: `sensortask_dev.py` runs a link exerciser and publishes a transfer/failure count
  through `/status`'s `sensors.UARTLINK`, which the bench tier asserts advancing during the load
  window. A later session should also know the board may need reflashing before any of this runs —
  a firmware predating a `src/` change simply won't carry it, and the tier's skip guards name that
  rather than failing obscurely.
- **A device script's every wait must stay inside its own watchdog window, or a link fault reports
  as a reset instead of a result.** `tests_hardware/device_scripts/uart_crossover_*.py` arm an 8s
  `machine.WDT` and used to join their responder task with `asyncio.wait_for(listener, 10/12)`.
  That join can never complete on its own when the frame never arrived - `uart_listen()` parks in
  its one legitimate unbounded read - so the watchdog fired first and the run died with an
  `mpremote` I/O error and no `RESULT:` line at all. Found (2026-09-11) by running the exchange
  script with UART1 deliberately moved to unjumpered pins, i.e. by simulating the exact wiring fault
  this tier exists to catch. Both scripts now poll `task.done()` in bounded steps, feeding as they
  go, and use `UART_Comm.clear()` - the module's own documented unstick - to free a parked listener.
  The same run now reports `GET returned None ... errno 20` (initiator, no ACK) and `errno 22`
  (responder, read timeout), which is the diagnosis a bench session actually needs.
- **Both crossover device scripts poll at two rates, matching `sensortask_dev.py`**: `POLL_WAIT_MS`
  (2 ms) for a transaction in flight, `POLL_IDLE_MS` (50 ms) for a listener waiting on a frame that
  may never come (SPECIFICATION.md Part F.5.9). A script that used one rate would not be exercising
  the shipped configuration, which is the whole point of the flash tier. The practical consequence
  for a bench session: a responder notices the first byte of a frame up to 50 ms late by design, so
  a measured first-frame latency on this rig includes that and is not a link fault.
- **`asy_uart_driver.UART.deinit()` does not release the GPIO function select, so a script that
  inits a UART on different pins poisons that peripheral until the next hard reset.** Confirmed the
  hard way (2026-09-11): a throwaway diagnostic that put UART1 on GP4/GP5 left those pins muxed to
  UART1 after `deinit()`. UART1's RX input then kept being taken from the floating GP5 instead of
  the jumpered GP9, so **every subsequent run of the real crossover tests failed** - deterministically,
  and across `mpremote`'s own soft resets, which do not restore pin defaults. A `mpremote reset`
  (real hard reset) cleared it immediately. The shipped scripts always use GP8/GP9 and never hit
  this, but any ad-hoc device script that moves a UART's pins must hard-reset the board afterwards
  before its results - or the next test's - mean anything.
- **A device script that reads error-log content clears its chunk at the START, never at the end.**
  Clearing first is what makes a run deterministic: the chunk is real persistent storage, so
  without it a script inherits the previous run's ring and its assertions drift silently. Clearing
  at the end would destroy the evidence of what the script just did. Residue is the accepted
  outcome; the caveat above is how a reader avoids misreading it.
  `fram_error_log_reset_race_verify.py` is the one deliberate exception — it exists to read what
  the raced reset left behind, so a baseline wipe would erase the thing under test.
- ~~Does `mpremote`'s implicit soft-reset re-execute `modules/_boot.py`/`boot.py`/`main.py`?~~ —
  **resolved: no.** Confirmed against the pinned MicroPython C source and empirically on real
  hardware: only a genuine `hard_reset()` resumes the live system; `exec()`/`run_isolated()` never
  do, regardless of `soft_reset_after`. See `harness.Board.run_isolated()`'s own docstring for the
  full finding. Tests that need to observe the *real* boot sequence correctly use `hard_reset()` +
  `tail_log()` instead, for exactly this reason.
- **A device script's heap reading is taken inside `main.py`'s aged heap, so a standalone figure and
  an in-suite one are not comparable.** Same consequence as the bullet above, and it has produced a
  false conclusion once: freshly flashed, the heap probe read 95,104 B and passed; deep in a suite
  the *same* firmware read 28,864 B and failed, with `free` unchanged to 0.2 % — the defect is
  position-dependent and a cold build cannot see it. **Any heap figure must state its suite
  position, or it is not a comparison** (HEAP_FRAGMENTATION_MEASUREMENTS.md §7D.2).
- ~~Is it safe to poll a live, already-running system with `board.exec()`/`is_reachable()`?~~ —
  **resolved: no, never.** `mpremote`'s `enter_raw_repl()` unconditionally sends Ctrl-C plus, by
  default, a real Ctrl-D `machine.soft_reset()` before running anything — polling either one against
  a live system self-resets its heap on every single poll, wiping the very state being waited on
  (this once made a real reboot's own transient unreachable window look like the reboot silently
  never happened). **Rule**: use the genuinely passive `Board.is_device_present()` (opens/closes the
  serial port, sends nothing) for any liveness poll against a live system. `is_reachable()` stays
  `mpremote`-based deliberately, for the few callers specifically testing that reset mechanism
  itself (e.g. the flash tier's own connection-stability test) — see both methods' own docstrings in
  `harness.py`.
- **Does `machine.soft_reset()` reset the hardware counter `time.ticks_ms()` reads from?** Matters
  for `test_bus_electrical_timing.py::test_ticks_ms_real_2pow30_rollover`'s multi-day polling design
  (deliberately uses `board.exec()`, never `run_isolated()`, for exactly this reason - but confirm
  this before trusting a multi-day run's result).
- **`scheduler_saturation_drop.py`'s `BUSY_WAIT_MS`/`TIMER_PERIOD_MS` are a starting guess**, not
  measured on real hardware - widen `BUSY_WAIT_MS` if `dropped` comes back `False` on a real run.
- **Raw-socket off-subnet DNS spoofing feasibility on the bench Rpi4 is unchecked** -
  `test_hotspot_role_reversal.py::test_spoofed_off_subnet_source_address_is_ignored` is `@pytest.mark.skip`
  pending this; implement once a concrete mechanism (CAP_NET_RAW, a second netns, ...) is confirmed
  to work on the real bench host.
- ~~`kick_client()`'s `iw dev <iface> station del <mac>` — does NetworkManager's own AP-mode backend
  actually honor it?~~ — **resolved: yes.** See the "WiFi reconnection flakiness" finding below —
  `kick_all_stations()` (built on this primitive) is the confirmed fix.
- **`nmcli -g IP4.ADDRESS`/`IP4.GATEWAY device show <iface>`'s exact output shape** (CIDR-suffixed
  address vs. plain gateway) is well-established, long-stable nmcli behavior, but this session's
  sandbox has no systemd/D-Bus to actually run NetworkManager against and confirm live - unlike
  `nmcli device wifi connect`'s own syntax, which *was* confirmed directly against real `nmcli
  --help` output (installed in this sandbox specifically to check it) during this same session. See
  `bench_control.BenchBridge.own_ip_on()`/`gateway_ip()`'s own docstrings.
- **A permanent-WLAN-deactivation risk in the role-reversal scenario's own stage 6, found during a
  second, deeper re-audit of this tier's claims against `src/asy_wifi_service.py`**: by stage 6 the
  DUT has necessarily already been in hotspot mode since stage 0 (`hotspot_started_once == True`),
  so a failed real credential PUT (5 failed STA attempts) leads to `_PHASE_DEACTIVATED` - a terminal
  state only a real power-cycle clears (SPECIFICATION.md Part A.4's own documented, deliberate
  safety feature) - NOT a graceful fall-back to hotspot the way an *earlier* failure in the scenario
  would. `test_hotspot_role_reversal.py`'s `joined_hotspot` fixture already recovers from this via a
  `board.hard_reset()` fallback in its own teardown, but a first real run hitting this path is worth
  recognizing for what it is (an expected, designed-for recovery, not a new bug) rather than being
  surprised by it.
- ~~Captive-portal hotspot-mode redirect fallback (SPECIFICATION.md Part A.5) - real-hardware
  verification status: NEVER ACTUALLY RUN under a valid configuration.~~ — **resolved: confirmed
  working on real hardware (2026-09-03), on the real `src/sensortask_dev.py` build via
  `scripts/build_firmware.py dev`** (the now-deleted `DEV_HARDWARE_BASELINE_PLAN.md` §4b steps 10-12). A real
  `GET /generate_204` over the real hotspot link returned a genuine `302`/`Location: /`, `GET /`
  served the real site (`200`), and all three sensors (BMP3xx/SCD30/SGP40) read plausible real
  values — a 6.5-minute stability window afterward showed zero real errors on any module, watchdog
  armed throughout. The earlier "dropped as noise" finding (a bare 404 on a mismatched
  `scripts/build_firmware.py wozi`-on-dev-bench test) is now doubly moot: not only was that
  configuration invalid, the *real*, valid `dev`-native configuration has since been directly
  confirmed working. `src/`'s own `is_hotspot_active()`/`_serve_static()` logic was already proven
  correct against the real Unix-port interpreter; this closes the one remaining "never run on real
  rp2/lwIP" gap. Per CLAUDE.md's hard rule, `wozi` is never physically flashed — this dev-bench
  result is the real, complete verification, valid for `wozi` too.
  **Pitfall found investigating this, still worth keeping**: don't reach for `mpremote exec()` to
  inspect live state — per the liveness-polling finding above, `exec()` soft-resets the board and
  wipes the very live state you're trying to observe. Use a passive method (a second REST/
  network-level check, or a genuinely code-level trace) instead.
- **A real phone can fail to show the captive-portal "Sign in to network" prompt even though the
  DUT's own server-side behavior is textbook-correct** (real-hardware production-hotspot session,
  2026-09-03, Samsung Galaxy A54 5G / One UI 8.5): connecting showed Android's "No internet" badge
  in the WiFi list, with no sign-in popup, despite a direct check confirming the DUT answered every
  captive-portal probe host with a real `302`/`Location: /` and DNS-spoofed every hostname to its
  own IP exactly as `SPECIFICATION.md` Part A.5/`captive_dns.py` describe. Not a `src/` bug — this
  is almost certainly phone-side: (1) **Private DNS (DNS-over-HTTPS)**, when enabled in Android's
  network settings, bypasses the DUT's local DNS spoofing entirely for the connectivity-check
  request, so on an isolated hotspot with no real internet the check simply times out with no
  signal, instead of getting the redirect that would trigger the popup — turning it off (or setting
  it to "Automatic", which most Android versions correctly skip on a network with no working DNS
  resolution to a public DoH provider) is the fix to try first; (2) Android can cache a "no
  internet" verdict per-SSID, which would also explain the badge appearing before even tapping to
  connect, if the same SSID (`"SensorNode"`, the config default) was already seen failing this
  check on a previous connection (this bench's own repeated automated test runs are a plausible
  source) — forgetting the saved network and rejoining fresh rules this out. No code changed as a
  result of this investigation.
- **`max_connections=4` real client-visible rejection under a realistic multi-client burst** — see
  BACKLOG.md open question 7 for the full finding and the still-open raise-the-cap decision.
- **This whole tier's log-based synchronization depends on the DUT's live `DebugLevel` being high
  enough — confirmed directly, the hard way (2026-09-04): a full 77-test bench run produced 2 real
  failures + 48 errors, none of them a real regression.** `tests_hardware/conftest.py`'s `dut_ip`
  fixture (every bench test depends on it) passively watches serial for `asy_wifi_service.py`'s own
  `self.pr.one("WLAN connection established")`/`self.pr.one("Permanently no WLAN connection -
  activating hotspot!")` lines — both gated on `DebugLevel >= 3` (`print_log.py`'s `_LOG_ONCE`).
  `test_real_ntp_sync_succeeds_over_genuine_udp` needs `asy_ntp_client.py`'s own
  `self.pr.all("Received NTP time:", ...)`, gated at `_LOG_ALL` (5) — the single highest level. At
  `DebugLevel=0` (this project's own production-quiet default — see DEVICE_REFERENCE.md/CLAUDE.md
  for when a board is deliberately left there, e.g. after a "clean production hotspot" request) none
  of these ever print, so `dut_ip` always times out waiting for a signal that can structurally never
  arrive, cascading into every bench test that depends on it — this looks exactly like the WiFi
  reconnection flakiness documented above, but isn't. **Before chasing a fresh "WiFi flakiness" or
  "NTP won't sync" signal from this tier, first confirm the DUT's live `DebugLevel` is 5** (`GET
  /system`, or a passive `tail_log()` for any routine chatter at all) — a real regression stays
  distinguishable by *which* specific check fails once logging itself is confirmed working, not by
  the blanket "log stayed empty" symptom this causes. `test_boot_import_mechanism_actually_boots_
  the_real_system` (`tests_hardware/flash/test_reboot_persistence.py`) now handles this itself
  (temporarily raises/restores `DebugLevel` around its own one hard reset); every other bench test
  still assumes the DUT is already at a workable level going in — this tier was written and
  originally verified against a board logging at `DebugLevel=5`, and that's an implicit
  precondition of the whole tier, not stated anywhere until this entry.
- **WS2812/Neopixel timing has no datasheet in this repo's `datasheets/` folder at all** (only
  bmp3xx/fram/pico w/scd30/sgp40 - confirmed by listing the directory) - the manual
  `test_real_ws2812_neopixel_signal_timing` test is deliberately qualitative (visual/scope check,
  human judgment) rather than asserting any specific timing value pulled from memory, per CLAUDE.md's
  "say so explicitly if the datasheet isn't there" rule.
- **WiFi reconnection flakiness after a hardware reset - root-caused and mitigated.** A hard reset
  followed by a fresh STA connect attempt used to sometimes fall back to hotspot mode instead of
  reconnecting. **Root cause, confirmed decisively via a real-hardware A/B test**:
  NetworkManager's own AP-mode backend for `br0-wifi-ap`
  (confirmed to be its internal `wpa_supplicant`, not a separate `hostapd` process) retains a stale
  station-table entry for the DUT's MAC across a hard reset (a real power-cycle, no clean 802.11
  deauth), and a fresh association racing against that stale entry doesn't reliably get treated as
  a clean new session - 10/10 trials fell back to hotspot with the stale entry left in place, 10/10
  connected cleanly once it was cleared first. Not a `src/` bug - `asy_wifi_service.py`'s own
  retry/hotspot-fallback logic behaves exactly as designed. **Fixed**: `bench_control.BenchBridge.
  kick_all_stations()` (wrapping the `kick_client()`/`bench_associated_station_macs()` primitives)
  is now called before every `hard_reset()` that expects a real reconnect afterward - the `dut_ip`
  fixture, `joined_hotspot`'s recovery fallback, and `test_real_sta_connect_reaches_established_
  after_a_hard_reset` (`bench/test_wifi_networking.py`, now also asserts a real connection, not
  just any WiFi-related log line).
  - One real caveat for the field, not a reason to distrust this fix: a device WDT-looping against
    a real router would hit the same stale-entry pattern with no bench harness able to
    `kick_client()` on its behalf.
  - **Confirmed the same fix is also required after a `picotool load` reflash, not just
    `hard_reset()`** (BACKLOG.md's 2026-09-05/07 real-hardware `MemoryError`-mitigation sessions,
    hit repeatedly, every single reflash): a fresh flash cycle reboots the board the same abrupt,
    no-clean-802.11-deauth way a hard reset does, so it's mechanically the identical hazard - `kick_
    all_stations()` before the post-flash reconnect attempt, every time, not just around
    `hard_reset()` calls already inside the test harness itself.
- **A second, distinct, real WiFi mechanism - a well-documented upstream characteristic, not
  something to fix in `src/` without a project-owner decision.** Found while confirming the fix
  above at scale: `bench/test_network_resilience.py`'s `ap_down()`/`ap_up()`-based outage/flap
  tests can still fail even with a clean AP-side station table, because the CYW43 firmware/lwIP
  stack can silently mask a real link disruption from `wlan.isconnected()`/`wlan.status()`
  entirely - confirmed directly (a real `arping` probe got zero responses from the DUT while
  `iw station dump` showed it continuously "associated: yes" for hundreds of seconds spanning the
  whole outage) and confirmed as a long-standing, still-open upstream MicroPython characteristic,
  not project-specific, via `micropython/micropython#9455`/`#9505`/`#18797` and independent field
  reports. `asy_wifi_service.py`'s own `_wlan_isconnected_or_false()` is a bare pass-through to
  `wlan.isconnected()` with no independent reachability check, so `_on_sta_disconnected()`'s retry
  logic structurally cannot fire if the firmware never reports the disconnect. Whether to add an
  independent reachability check is a real architectural question for the project owner, not
  decided here. Mitigated at the test level only: both tests now recover via a real `hard_reset()`
  if the graceful wait times out (the one thing confirmed to reliably clear this), but still fail
  loudly afterward so the real limitation stays visible rather than being silently papered over -
  confirmed working as designed (a failure recovers the board cleanly for whatever test runs next).
- **Lesson from a since-fixed test bug, worth keeping as standing practice**:
  `test_garbage_ssid_via_rest_config_is_handled_gracefully`'s own final "did the DUT reconnect"
  check spent many hours looking like unexplained hardware flakiness (escalating retry budgets,
  multiple `hard_reset()` retries, even a full physical power-cycle) before the real cause was
  found: the check read a `"Mode"` field from `GET /networking`, which never has that field
  (`"Mode"` exists only under `GET /status`'s nested `"networking"` object) — so it was
  unconditionally `False` regardless of how long the DUT had actually been reconnected. The DUT was
  reconnecting normally the whole time. **Before trusting an "it's flaky" signal from a
  real-hardware test enough to spend serious time chasing a hardware/firmware explanation, first
  re-verify the test's own check is asking the right question of the right endpoint/field** — a
  plain `curl` of both endpoints side by side would have caught this in under a minute.
- **SCD30's RDY pin is real and wired**: `SCD30_Reader`'s `irq_pin` constructor parameter (GPIO 8 in
  production), a real `irq_pin.irq(trigger=IRQ_RISING, ...)` in `start_timer()`, plus a staged
  500ms software self-healing fallback in `scd_init_irq()` if the real IRQ is ever missed.
  `test_scd30_real_irq_edge_drives_a_real_read` (`device_scripts/scd30_real_irq_edge.py`) exercises
  it - its one genuine, disclosed limit: software alone can't fully distinguish a genuine hardware
  IRQ firing from the self-healing fallback firing instead; only a scope on the pin itself could.
- **`tests_hardware/manual/`'s files are deliberately named away from the `test_*.py` glob**
  (`manual_wifi.py`, not `test_wifi_manual.py`) - a bare `uv run pytest tests_hardware` (no path
  scoping) would otherwise collect and run them as ordinary pytest tests, each calling `input()`
  and hanging forever. `scripts/run_flash_hardware_suite.sh`/`run_bench_hardware_suite.sh` are
  scoped to avoid this either way, but the naming is the structural backstop.
- **Reusable real-hardware GC/fragmentation-instrumentation technique**: a temporary async probe
  task added to the boot entry (`boot_entry/<device>_boot.py` at the time this was written; that
  directory is retired now - SPECIFICATION.md Part L.4 - so add it to the staged `main.py`
  a build produces, before flashing, and never commit the edit), printing a fixed-format
  line every N ms/every real event, captured via direct `pyserial` reads (`Board.tail_log()`, never
  `mpremote exec()` against a live system - that soft-resets it, wiping the very state being
  measured). Used for `gc.mem_free()` sampling + collection detection, real per-collection pause
  timing (bracket `gc.collect()` with `time.ticks_us()`), and real contiguous-allocation-frontier
  probing (attempt a real `bytearray()` at each of a descending candidate-size list, record the
  largest that succeeds - `gc.mem_free()` alone can't distinguish contiguous from scattered free
  space). Reuse this pattern for any future real-hardware memory/timing investigation rather than
  re-deriving it; SPECIFICATION.md Part I.1/I.3/I.5 has the results this technique already produced.
  The same technique applied to `AsyUDPSocket.ready()` (a one-line `print()` on a real
  `POLLERR`/`POLLHUP` event) found that real rp2/lwIP does not appear to propagate ICMP errors onto
  a connected UDP socket's poll state at all (BACKLOG.md open question 5) - zero such events
  observed across 6 real retry cycles against a target with no listener (the condition that
  generates a real ICMP Port Unreachable).
- **`bench_control.BenchBridge.redirect_udp_port_to_local()`'s DNAT redirect does not reliably
  deliver to a local *listening socket*** - confirmed via a live `iptables -t nat -L PREROUTING -n
  -v` packet-counter poll showing the rule matching real traffic while a live-bound listening
  socket on the same redirected port received nothing, across several independent `hard_reset()`
  cycles. `net.ipv4.conf.*.route_localnet` reads `0` (disabled) on every interface on this bench,
  the documented Linux condition for "DNAT to 127.0.0.1 from a non-loopback ingress interface" to
  silently fail post-NAT routing. The existing `RogueUdpResponder`-based garbage-response tests are
  unaffected (they exercise the DUT's own *reply* path, which does work), and a separate quirk was
  also seen where the redirect didn't intercept traffic at all for one `hard_reset()` cycle, root
  cause not chased. **If a future test needs to observe the DUT's own outbound *request* (not
  inject a reply), use `bench_control.BenchBridge.start_udp_source_capture()`/
  `read_captured_udp_source_port()` instead** (a real wire-level `tcpdump -c 1` capture on the
  DUT-facing radio) - no local delivery involved, confirmed reliable on its first real run.

## Third pass - closing real coverage gaps (found via a direct project-owner audit question)

Asked directly: "did you also add tests for the sensors and the on-board hardware itself and
standalone, up through the integration, and at the top level checking the API delivering sensible
values, including the VOC algorithm producing good results, FRAM backup working, FRAM error storage
working, website working... (all of which are tests of the twin, partially simulated, but now
running for real)?" Answer at the time, honestly: no - only SCD30 had any automated real-hardware
value check at all, and several real mechanisms (FRAM, the VOC algorithm, website-over-the-normal-
network, multi-sensor REST value sanity) had zero automated coverage. Confirmed by grep before
writing anything (`grep -rln "AsyFramManager\|asy_fram" tests_hardware/` etc. all came back with
nothing but this README/manual-test references). Ten tests closed these gaps (44 -> 54):

- **BMP3xx/SGP40 standalone plausibility** (`flash/test_sensor_accuracy.py`, `device_scripts/
  bmp3xx_plausibility_read.py` / `sgp40_voc_algorithm_quality.py`): same isolated-driver-plus-
  datasheet-bounds shape as the pre-existing SCD30 test, now covering all three real sensors.
- **VOC algorithm quality** (same `sgp40_voc_algorithm_quality.py`): SGP40's raw signal and
  `voc_algorithm.py`'s Sensirion Gas Index Algorithm can't be exercised independently of each other
  (the driver always runs one straight into the other), so one script covers both - waits out the
  algorithm's own documented 45s initial blackout, then samples several real post-blackout readings
  and checks they're in range *and* neither frozen nor erratic. Deliberately a stability/sanity
  check, not a numerical-accuracy claim against a calibrated reference (that needs a human-supplied
  VOC stimulus - `manual/manual_sensor_accuracy.py` item 10).
- **FRAM backup working** (`device_scripts/fram_manager_roundtrip.py`,
  `sgp40_fram_backup_restore.py`, `flash/test_fram_storage.py`): a real chunk write/read/CRC/dual-
  copy round trip against the physical MB85RS64V chip, plus the real SGP40 VOC-state backup/restore
  pathway specifically, driven through `SGP40_Reader`'s own real production `read_loop()` (natural
  ~60s `BackupPeriod` schedule) rather than synthetic internal calls. A "fresh boot" is simulated by
  constructing a brand-new `AsyFramManager` Python object against the same physical chip (allocator
  state is per-object, so this lands on the identical chunk address a real reboot's own fresh
  `build_system()` call would) rather than requiring an actual `hard_reset()` - the real chip's
  bytes are untouched by a plain object-level restart either way.
- **FRAM error storage working** (`device_scripts/fram_error_log_roundtrip.py`):
  `PrintLogHistoryStore` (every FRAM-chunk-owning module's own `err_s()`/`wrn_s()` persistence)
  against the real chip, same fresh-boot-simulation pattern as the backup/restore test above.
- **Website over the normal network** (`bench/test_rest_endpoints_over_sta.py`): the only prior
  `GET "/"` check anywhere in this tier was hotspot-mode-only, inside
  `test_hotspot_role_reversal.py`.
- **Top-level API delivering sensible values, across all three real sensors together, via REST**
  (same file): the pre-existing endpoint check
  (`test_end_to_end_timing.py::test_real_concurrent_client_burst_does_not_crash_the_webserver`) only
  ever checked HTTP status, never values.

A follow-up clarification then widened scope further, on the same audit thread: not just twin-
parity, but (1) bottom-level hardware *function* checks, not just readings, and (2) a real-hardware
counterpart for every mock-driven integration test in `tests/` "wherever possible". Two more
additions from that:

- **FRAM write protection actually gates a real write, a real read, and does so in silicon**
  (`device_scripts/fram_write_protect_roundtrip.py`, `flash/test_fram_storage.py`): sets the real
  WPEN|BP0|BP1 status-register bits, then checks three things - a write is rejected while
  protected and succeeds once cleared again (not just "can a chunk be written at all", which the
  roundtrip test above already covers); a *read* is rejected too, because `_read_chunk()` must
  write a transient busy marker first (intended behavior, SPECIFICATION.md Part A.4's FRAM entry,
  asserted identically at the mock and twin tiers); and - the part no fake can reach - the chip
  itself refuses, not merely the driver's own guard, proven by desyncing the cached `_wp` from the
  still-protected chip and sending a real WREN+WRITE whose bytes never land.
- **Real PUT /sensors config pushes** (`bench/test_sensor_config_push_over_real_hardware.py`): the
  real-hardware counterpart to `tests/test_setter_microdot_integration.py`'s mock-driven coverage.
  BMP3xx's oversampling/filter-coefficient fields are pushed to non-default values over a real REST
  call, confirmed `"Valid"` (proof the real I2C write succeeded), then read back via a second real
  REST call and restored to their original values in a `finally` block (this mutates the bench
  board's real persisted config). SGP40's `SGPResetVOC` command-only field is pushed the same way.
  **SCD30 has no live-push config fields at all** (confirmed directly: zero `_push_callbacks`
  registrations in `asy_scd30_driver.py`) - there is nothing to add real-push-parity coverage for on
  that sensor, not a gap.

**Still not automated even after this pass** (flagged honestly, not silently left implicit):
real-hardware numerical-accuracy validation against a calibrated reference for any sensor (needs a
human-supplied known-good stimulus - `manual/manual_sensor_accuracy.py` items 9/10, inherently
manual); WS2812/Neopixel notification-signal validation beyond the manual qualitative check (no
datasheet in this repo to assert real timing values against, and no scope/logic-analyzer in this
bench rig's own automated toolchain); a genuine power-loss test of the FRAM backup/restore or
error-log mechanisms specifically (only `manual/manual_persistence.py`'s raw-persistence power-loss
tests touch real power loss at all, and those don't drive `AsyFramManager`'s own chunk logic).

## Fourth pass - real networking-robustness gaps against the API/website/internals

Asked directly: real WiFi outage, WiFi flapping, "WiFi available but no internet", NTP unresponsive
or slow, DHCP flaky/slow, connections at/above the real socket limit, nonsense GET/PUT requests,
and stale/broken-mid-transmission connections - "imagine more". A grep-first check
(`grep -rn "ap_down\|ap_up" tests_hardware/`, `grep -rln "malformed\|garbage\|nonsense"
tests_hardware/`, etc.) confirmed real gaps: `ap_down()`/`ap_up()` were only ever used *inside* the
hotspot role-reversal scenario's own internal join/leave mechanics, never as a standalone "the DUT
was already connected and the AP just disappeared" fault; the only "malformed request" test was
GET-only, hotspot-mode-only, and never checked the response was actually shaped correctly; nothing
checked the real `max_connections=4` ceiling under genuine concurrency (the pre-existing 8-client
burst test in `test_end_to_end_timing.py` never holds a connection open long enough to occupy more
than a couple of real slots); and BACKLOG.md's own open question #5 ("real-hardware verification
gap for `asy_udp_socket.py`/`captive_dns.py`") was still open - every existing NTP/DNS fault test
only ever *dropped* traffic (`block_udp_ports()`), never fed the DUT a real garbage response. Eleven
tests closed these (54 -> 65, `bench/test_network_resilience.py` plus two new
`bench_control.BenchBridge` primitives and a shared `rogue_udp_responder.py` helper):

- **WiFi outage / flap while already connected**: grounded directly against
  `src/asy_wifi_service.py`'s `_on_sta_disconnected()` - once `_conn_phase` is
  `_PHASE_STA_ESTABLISHED` (which it necessarily already is, since these tests depend on `dut_ip`),
  a disconnect takes the "retrying previously successful connection in one minute" branch, which
  never increments `connection_failures` and never reaches the hotspot-fallback path at all. This is
  a structurally *different, safer* branch than the one SPECIFICATION.md Part E.6.4's role-reversal
  scenario exercises (a never-yet-connected DUT) - confirmed by reading the real source before
  designing these tests, specifically to rule out accidentally tripping that scenario's own disclosed
  permanent-WLAN-deactivation risk. "WiFi available but no internet access" is treated as equivalent
  to "NTP/DNS unreachable" for this device: it has no other internet-dependent feature (no outbound
  fetch of remote content) to distinguish a general internet outage from an NTP/DNS-specific one -
  the pre-existing `test_real_ntp_handles_a_genuinely_unreachable_server_without_crashing` already
  covers the *unresponsive* case; deliberately not duplicated here.
- **NTP/DNS servers answering with real garbage** (`rogue_udp_responder.py`,
  `bench_control.py`'s new `redirect_udp_port_to_local()`/`clear_udp_port_redirect()`): a real `nat`
  table PREROUTING DNAT-to-loopback redirects the real port to a local rogue UDP responder that
  answers every query with a fixed non-protocol payload, closing BACKLOG.md's open question #5's
  "garbage response" half specifically (the *unresponsive* half was already covered). Flagged the
  same way `own_ip_on()`/`gateway_ip()` already were: this session's sandbox has no systemd/D-Bus to
  confirm the DNAT combination against a real NetworkManager-managed bridge, so it's a standard,
  well-documented iptables pattern, not something verified live here.
- **Real socket-limit degradation** (`test_connections_at_and_above_the_real_socket_limit_degrade_cleanly`):
  grounded against `asy_webserver_service.py`'s own `_serve()` - `_open_conns` increments the instant
  a TCP connection is *accepted*, before any byte is read, which is what lets this test hold exactly
  `max_connections=4` real slots open with bare `connect()` calls and deterministically observe the
  5th being rejected (closed with zero bytes written, matching `_serve()`'s own "silently close, no
  accept, no response ever written" reject-when-full comment).
- **Nonsense GET/PUT over the normal network**: a genuine 404 (shaped per `_ERROR_SHAPES`), a
  genuinely malformed raw JSON body (needs a raw socket - `http_client.fetch()` can only ever
  serialize valid JSON), a real 413 over `max_content_length=2048`, and syntactically valid but
  nonsensical field values (wrong type, out-of-range, an entirely unknown sensor key) - each
  confirmed against `_body_as_dict()`/`base_classes.py`'s `_set_dict_cfg()` to land exactly where the
  real source says it should, including confirming none of these paths ever reach
  `ConfigManager.write_config()` (so nothing needed restoring afterward, unlike the third pass's
  BMP3xx config-push test).
- **Slowloris-style partial requests and abrupt mid-response disconnects**: grounded against
  `_serve()`'s own outer `asyncio.wait_for(..., outer_cap_s)` (production default 15.0s, confirmed
  not overridden anywhere in `sensortask_wozi.py`) - the exact mechanism the code's own comment says
  bounds "a Slowloris-paced client no single per-call timeout alone would catch".

**Deliberately not covered, and why**: DHCP flakiness/slowness/rubbish responses. The DUT's DHCP
*client* behavior lives
entirely inside MicroPython's own lwIP stack, not this project's own code (no DHCP-handling code
anywhere in `src/`) - the same "outside this project's own code, a different backstop applies"
bucket CLAUDE.md already places I2C-bus-wedge recovery in. Unlike `ap_down()`/`ap_up()` (fully
reversible via `nmcli` in seconds) or the UDP-port redirects above (a plain iptables rule, trivially
removed), the bench bridge's own DHCP server is NetworkManager's managed `dnsmasq` instance with no
exposed per-request delay/corruption knob - a custom rogue DHCP responder risks leaving the DUT
without any valid lease at all, in a way nothing in this tier could then recover from short of
physical intervention.

**Standing policy from this pass on, applied everywhere it's practical**: reset the real, REST-
exposed error/warning history (`PUT /status {"ResetErrors": true}`) before a fault-injecting test,
confirm the *specific* expected `err_s()`/`wrn_s()` entry actually landed on the *right* module's
log afterward (not just "the system didn't crash"), then reset again so a real bench rig's live
error history is never left showing a test's own deliberately-provoked faults - `error_log_helpers.py`
(new shared module) is the reusable primitive for this. `/status`'s own `errcount` shape
(`asy_webserver_service.py`'s `_shape_errcount_entry()`: `{"counter": int, "history": [{"num": int,
"type": "E"|"W"}, ...]}`) is *not* the same shape as `print_log.py`'s raw `get_log()` several
`device_scripts/` files already consume directly - confirmed directly before writing the helper,
not assumed from that other shape. Applied to every fault-injecting test in
`test_network_resilience.py`, the two `test_sensor_config_push_over_real_hardware.py` tests (confirming
a fully valid push-and-restore leaves nothing behind), and retrofitted onto the pre-existing
`test_real_ntp_handles_a_genuinely_unreachable_server_without_crashing` (`test_wifi_networking.py`).
One real design bug this same grounding pass caught in itself, fixed before this even shipped: the
first draft of the slowloris test asserted the wrong response shape and attributed it to the wrong
timeout mechanism - a single stall over 5s actually hits `_TimeoutStreamProxy`'s own *per-call*
read timeout, which Microdot itself silently absorbs and recovers from by writing an ordinary
response (confirmed directly against that class's own module comment), not the *outer* 15s
`outer_cap_s` backstop the test meant to exercise. Fixed with a genuine trickle-feed pace (one extra
header line every 3s, 6 of them - each individual gap safely under the 5s per-call timeout, the 18s
cumulative total safely over the 15s outer one) that actually reaches the outer path instead.
Not every fault has a groundable expected log entry: `_serve()`'s own reject-when-full,
`_shaped_error_handler()`, and `_body_as_dict() is None` paths call no `pr.err_s()`/`wrn_s()` at all
(confirmed directly, not assumed) - those tests assert the log stays *empty* instead, which is
itself the real, meaningful check for a benign/expected outcome. One case (`test_abrupt_disconnect_
mid_response_does_not_hang_the_server`) has a real but genuinely timing-dependent expected log entry
(whether the server is still mid-write when the client's RST lands) - documented as a deliberate
non-assertion rather than a flaky one. This retrofit was **not** extended to the rest of the tier in
this pass.

**Partially closed later (2026-09-04, cloud-agent pass)**: `test_hotspot_role_reversal.py`'s
`test_malformed_truncated_packet_is_silently_dropped` and
`test_malformed_http_request_over_real_wireless_degrades_cleanly` now assert the module log stays
empty too (`DNSSRV`/`WEBSERVER` respectively - both grounded directly against source: a
garbage-but-present UDP datagram never reaches `captive_dns.py`'s own `wrnno=2` backoff branch,
which only fires on a genuine `(None, None)` `recvfrom()` failure, and an unparseable HTTP request
line fails entirely inside vendored `ext/microdot.py` before this project's own code is ever
reached). **Real finding while doing this, since corrected (2026-09-08)**:
`test_dns_flood_backoff_curve_recovers_once_flood_stops`'s own comment used to claim its flood
"triggers the backoff path" - checked directly against `captive_dns.py`'s `run()` and that was not
what happens: `AsyUDPSocket.recvfrom()` returns real `(data, addr)` for any received-but-garbage UDP
payload (UDP has no content validation), so the flood actually takes the *same* `pr.evt()`-only path
as the truncated-packet test above, never the `recv_fail_backoff_s`-growing branch the old comment
described. The test's own assertions (a legitimate query still answered promptly once the flood
stops) always held regardless, so this was never a false pass - only the comment's account of
*which* code path it was proving was wrong. **Resolved by correcting the comment in place**
(project-owner direction): it now describes the actual `pr.evt()`-only path the flood exercises and
notes that no fault in this codebase can currently force a real `(None, None)` `recvfrom()` failure
from a bench test, so the backoff-growth branch itself remains unexercised by any test in this
tier - a real, still-open coverage gap (not a bug), left for whenever a way to inject that specific
failure is worth building.

The rest of the tier - `test_hotspot_role_reversal.py`'s remaining fault tests (association/DHCP
churn, which are bench-radio-observable only and have no DUT-side `src/` module to log against, so
this policy doesn't apply to them) - stays outside this policy's scope for the reason already
given, not silently left looking finished. The flash-tier timer-exhaustion/scheduler-saturation
device scripts (`timer_alarm_pool_exhaustion.py`/`scheduler_saturation_drop.py`) were re-checked too
and turned out **not** to need this retrofit at all: flash tier has no REST server reachable at all
(USB/serial only, no network), both scripts already assert the *specific* expected outcome via
their own `RESULT: PASS/FAIL` line (exact `errno`, per-timer self-heal proof) rather than "didn't
crash," and neither invokes any `src/` driver module that could log to `errcount` in the first
place (bare `machine.Timer` only) - so there is no comparable gap there to close. The original note
above overstated this; corrected here rather than left stale.

## Fifth pass - FRAM fault-injection: CS hijack and hard-reset race

Partially closes the "still not automated" gap noted in the Third pass above (a genuine power-loss
test of FRAM backup/restore) - not full power loss, but two real, reachable fault shapes during an
in-flight FRAM write:

- **FRAM CS-pin hijack** (`device_scripts/fram_cs_hijack_fault_injection_and_recovery.py`): races a
  software CS deassertion against an in-flight SPI write/read. `SPIDevice.write()`/`readinto()` have
  no internal yield point (synchronous `machine.SPI` calls), so the only reachable race window is
  `SPIDevice.__aenter__()`'s `await asyncio.sleep(0.001)` - CS already asserted, opcode not yet
  clocked out. Confirmed empirically (2026-09-04, this bench unit): 5/5 trials of both scenarios
  landed identically (a deterministic scheduling-order race, not timing luck). Write hijack: the
  write never reaches the chip (real memory shows the untouched original). Read hijack: the buffer
  comes back all zero bytes (MISO's real electrical state while SO is high-Z during deselect), never
  the real seeded pattern, never an exception. Both scenarios end with `verify_present()` succeeding
  and a fresh write+read round trip working normally - the chip's SPI protocol state machine is
  never left wedged by a CS-based interruption.
- **FRAM hard-reset race during write** (`device_scripts/fram_reset_race_during_write_seed_and_race.py`
  + `..._verify_recovery.py`): races a genuine `machine.reset()` against an in-flight FRAM write, at
  the same yield-point technique as the CS-hijack script above. A real reset is a genuinely different
  fault than a CS deselect: the FRAM chip has no idea the RP2040 rebooted, so the WEL write-enable
  latch (already SET by the prior WREN handshake) is left exactly as it was, not cleanly unwound.
  Because `SPIDevice.write()`/`readinto()` have no internal yield point, this cannot prove a
  genuinely torn (partially-written) transfer - only that a reset landing right as a write session
  begins leaves the target region untouched and the driver/chip fully recoverable, including that the
  stray SET WEL causes no problem for the very next real write. A true mid-byte-transfer power loss
  is architecturally unreachable via any interpreter-level race (same class of limitation as the
  wedged-bus case in SPECIFICATION.md Part F.2) - only a real external power cycle or an
  out-of-process host-triggered interrupt could reach that point; this is the honest, safely-buildable
  scope, not the exhaustive one.

**Isolated-driver device-script cfgmgr priming pattern**: any device script that constructs a
`*_Reader` directly (not via `sensortask_*.build_system()`) must prime `reader.cfgmgr.valid = True`
and `reader.cfgmgr._cache = {...}` with the driver's own schema defaults before starting read/trigger
tasks. Without it, `cfgmgr.valid` stays `False`, the reader's first config read returns `None`, and
the read loop fails silently (visible only at `debug=5`, e.g. "Error reading config data!") without
ever attempting a real sensor read. Found independently in `bmp3xx_plausibility_read.py` and
`sgp40_fram_backup_restore.py`. Never call `cfgmgr.setup()` in such scripts - that performs a real
littlefs file write/read.

## Sixth pass - the `dut_ip()` fixture's retry/recovery methodology, and other bench-harness findings

`conftest.py`'s session-scoped `dut_ip()` fixture gates nearly every bench test, so its retry logic
carries more real-hardware findings than any other piece of harness code in this tier - recorded
here in full since the code comment that used to carry them had to shrink to a pointer:

1. Early WiFi reconnection flakiness on this bench unit was undiagnosed; a single bad boot used to
   fail this session-scoped fixture outright, cascading into every other bench test. Fixed with one
   bounded `hard_reset()` retry.
2. A real STA IP does not mean the webserver is serving: `sensortask_wozi.main()` starts the
   webserver task only after `ntp_force_sync()` (bounded by a 20s `asyncio.wait_for()`), so up to
   ~20s can pass with a connected IP but nothing on port 80. Fixed by waiting for real HTTP
   reachability, not just link connectivity.
3. Polling for an IP via `board.exec()` in a loop is self-defeating: `mpremote`'s raw-REPL entry
   always performs an implicit `machine.soft_reset()` (confirmed against `transport_serial.py`'s
   `enter_raw_repl(soft_reset=True)`), which tears down the whole running Python VM/heap per
   MicroPython's `ports/rp2/main.c`, killing whatever WiFi reconnection attempt was in progress on
   every single poll.
4. A single (not looped) `board.exec()` call is *also* unsafe: entering raw REPL sets
   `pyexec_mode_kind` to `RAW_REPL`; the soft-reset boot path in `ports/rp2/main.c` only re-runs
   `main.py` when that's `FRIENDLY_REPL`. A trailing `soft-reset` command returns to an idle
   friendly-REPL *prompt* only - it does not retroactively make the already-completed soft-reset's
   boot sequence recheck that condition, so `main.py` stays stopped regardless. Confirmed via an A/B
   test: `exec` alone, `exec ... soft-reset`, and `run <script> soft-reset` all left the board
   silent (no `main.py` output) afterward. Only a genuine `hard_reset()` (real `machine.reset()`)
   reliably resumes normal auto-boot, since the RP2040 restarts from its own reset vector where
   `pyexec_mode_kind` starts fresh at its compiled-in `FRIENDLY_REPL` default.
5. **Dominant root cause, found via a real-hardware A/B test**: the WiFi reconnection flakiness is
   overwhelmingly a stale AP-side station-table entry - the bench AP backend (NetworkManager's
   internal `wpa_supplicant`, confirmed not a separate `hostapd` process) still lists the DUT's MAC
   as associated from before a `hard_reset()` (a real power-cycle, no clean 802.11 deauth frame
   sent), and a fresh association attempt racing against that stale entry doesn't reliably get
   treated as a clean new session. **10/10 trials fell back to hotspot mode with the stale entry
   left in place; 10/10 trials connected cleanly once `kick_all_stations()` cleared it immediately
   before each `hard_reset()`.** Not a `src/` bug - `asy_wifi_service.py`'s own retry/hotspot-fallback
   logic is textbook-correct given what the CYW43 firmware reports; the AP's own stale bookkeeping
   is what was wrong, and only this bench-host-side harness can see or fix it. Caveat: a device
   WDT-looping in the field would hit the same stale-entry pattern against a real router with no
   bench harness able to `kick_client()` on its behalf - this fix makes bench testing representative
   of a *clean* reconnect, not proof the field scenario is risk-free.
6. Neither retry above helps if the real cause is stale stored WiFi credentials (e.g. the bridge was
   just recreated with a fresh random SSID/password) - the DUT organically falls back to its own
   hotspot every time. Fixed by `_recover_stale_dut_credentials()`: joins the DUT's own hotspot
   fallback as a client, PUTs the bench AP's real current SSID/password to it (read via
   `BenchBridge.ap_password()`'s `--show-secrets` nmcli query), then restores the bridge - reusing
   the exact mechanism `test_hotspot_role_reversal.py`'s own stage 6 exercises by hand.

The fixture's current implementation: watches passively via `board.tail_log()` for
`asy_wifi_service.py`'s real log lines ("WLAN connection established" / "Permanently no WLAN
connection - activating hotspot!"); reading the actual IP still needs one `board.exec()` call
(unavoidable), always immediately followed by `board.hard_reset()`.

**`bench_control.py`'s `redirect_udp_port_to_local()` - a DNAT-to-loopback local-delivery gap**: the
DNAT-to-127.0.0.1 redirect itself is real (the `nat` table's own per-rule packet counter confirms
every redirected datagram is matched), but delivery to a local listening socket on the resulting
address/port was repeatedly, reproducibly absent on this bench's real environment -
`net.ipv4.conf.*.route_localnet` reads 0 (disabled) on every interface here, the documented Linux
behavior for "DNAT to 127.0.0.1 from a non-loopback ingress interface." Confirmed via a live
comparison: a background `iptables -t nat -L PREROUTING -n -v` poll showed the rule's packet counter
climbing in real time while a live-bound listening socket on the same redirected port received
nothing, across several independent `hard_reset()` cycles. `start_udp_source_capture()`/
`read_captured_udp_source_port()` (real wire-level `tcpdump` capture) exists specifically to work
around this - no local delivery needed at all.

**`bench_control.py`'s `is_ssid_visible()`/`join_dut_hotspot()` real-hardware timing**: `is_ssid_visible()`
being True one moment doesn't guarantee `nmcli device wifi connect`'s own internal (re)scan still
sees it a moment later - an isolated repro (2026-09-08) showed this can persist across several
consecutive attempts, not just one. `_join_dut_hotspot_with_reverify_retry()`'s reverify window is
30s/2s (widened from an original 15s/1s that let a `TimeoutError` escape uncaught, crashing the
retry loop on attempt 1 instead of exhausting all attempts) and catches `TimeoutError` alongside
`HardwareTestFailureError`. A repro with both fixes in place still occasionally exhausted 3 attempts once;
tracing into `src/asy_wifi_service.py` found a plausible (not confirmed) explanation:
`_configure_hotspot_ap()` re-runs `wlan.config()`+`wlan.active(True)` on every `_run_hotspot_mode()`
loop iteration for as long as no client is connected (every `wifi_refresh_sec`, 5s default) - a real,
code-confirmed periodic reconfiguration cadence that could plausibly cause a brief beacon gap
(unconfirmed on real CYW43 firmware, out of scope for a bench-test stability fix). Widening
`attempts` (not touching `src/` on an unconfirmed hypothesis) was the chosen response.

**The manual-test runner's duplicate-module-instance bug**: running `python3
tests_hardware/manual/runner.py` directly makes Python load that file as the `__main__` module,
while every `test_*.py`'s `from runner import register, ...` imports a *separate* module instance
literally named `runner` (found on `sys.path`) - two distinct module objects, each with its own
separate `_REGISTRY` list. Decorators in the test files populate the `runner`-named instance's
registry; `main()` running as `__main__` reads its own, different, permanently-empty one. Result: a
silent no-op - exit 0, zero output, `--list` showing nothing, no exception anywhere to point at the
cause. Confirmed directly by tracing both module instances' `id()`/`_REGISTRY` in a running
interpreter. Fixed by `__main__.py`: always imports `runner.py` as a plain module, never running it
as `__main__` itself - run `uv run python tests_hardware/manual/__main__.py`, never `runner.py`
directly.

**Manual-test conventions** (`tests_hardware/manual/runner.py`'s helper functions):
`print_instruction()` before the window that depends on it, not after. Timing is human-executable on
a breadboard test device (tens of seconds, chosen per what's physically involved), never a value
carried over from an automated/simulated test. `confirm()` waits for explicit human confirmation
wherever the console survives the step; `countdown()` is reserved for genuine power-cycle cases
where it doesn't. `state_expected_outcome()` prints what "passed" should look like before the
script's own verdict, for tests that end in a human visual/instrument check rather than a
script-only assertion.

## Seventh pass - cross-occupant write-vs-siblings real-hardware coverage (mock-tier gap closure)

`tests/_bus_hazard_catalog.py`'s generic mock-tier scenario
(`scenario_a_write_does_not_disturb_concurrent_sibling_reads`) surfaced a real gap once its own
"same test bar as `src/`" audit was extended to the real-hardware tier: no existing flash-tier test
proved a config WRITE from one dev/i2c1 occupant landing concurrently with its SIBLINGS' own reads -
only same-device write-vs-own-read (`bus_concurrency_same_device_scd30.py`,
`isl29125_same_device_rw_concurrency.py`) and the SGP40 general-call broadcast case
(`sgp40_general_call_reset_hazard.py`, SCD30 sibling only, not ISL29125). Two new tests close this:

- **`test_isl29125_config_write_does_not_disturb_concurrent_sibling_reads`**
  (`device_scripts/bus_concurrency_isl29125_write_vs_siblings.py`) - ISL29125's own `configure()` is
  the writer (a volatile config register, no NVM-write-budget concern per FN8424 p7), repeated
  `WRITE_CYCLES=8` times over a real multi-second window with SCD30 and SGP40 both reading
  concurrently. Part of the routine group, no opt-in needed.
- **`test_scd30_config_write_does_not_disturb_concurrent_sibling_reads`**
  (`device_scripts/bus_concurrency_scd30_write_vs_siblings.py`) - the SCD30-as-writer half of the
  same gap. SCD30's own `set_temperature_offset()` is a real NVM write, so this is deliberately
  **not** part of the routine group: gated behind `@pytest.mark.persistence_write` +
  `@pytest.mark.scd30_extra_write` / `--allow-persistence-writes` AND-gated with
  `--allow-scd30-extra-write` (same precedent as `--allow-flash-cycle` - see the Eleventh pass
  below for the full consolidated gating design), fires the one additional real write exactly once
  per invocation, and must never be folded into the one routine write
  `scd30_continuous_measurement_triggered` already spends for the whole flash-tier bus-hazard group
  (SPECIFICATION.md Part C.8's own write-budget rule).

**Honesty note - neither test has been run against real hardware yet.** Both were written and typed
during a session with no real-hardware go-ahead (CLAUDE.md's own standing gate) and no ability to
verify against the real bench Pi4/dev board - they pass `ruff`/`mypy` and follow the same structural
conventions as every proven-on-hardware script in this directory (window-overlap interleaving proof,
`RESULT: PASS/FAIL` line, `wdt.feed()` cadence, plausibility bounds), but that is not the same as a
real run. Treat both as a first cut to be smoke-tested (and fixed if wrong) on the next real-hardware
session, not as already-confirmed coverage - flagged here explicitly rather than left to look
finished.

## Eighth pass - full mock/twin-to-real-hardware scenario parity for dev's own topology, and flash-tier/bench-tier parity

Follow-up direction (project owner): every generic mock/twin bus-hazard scenario type must have a
real-hardware equivalent for whichever bus dev's own real wiring makes it applicable to (SCD30 stays
under its write-budget restriction), and whatever gets added to the flash tier must also get a
bench-tier counterpart - flash-tier bus-hazard coverage is always a subset of bench-tier coverage,
never the other half.

**The mock tier's timing-offset sweep, made explicit on real hardware, not just implicit in natural
jitter**: the Seventh pass's own two new scripts originally relied on a fixed write cadence (ISL29125)
or natural scheduling jitter alone to vary timing. `bus_concurrency_isl29125_write_vs_siblings.py` now
cycles through a deliberately varied, explicit set of pre-write delays
(`_WRITE_DELAYS_MS = (5, 15, 40, 80, 120)`, each exercised twice) instead of one fixed 30ms cadence -
a designed spread of relative timings against the siblings' own read loops, not merely hoping
uncontrolled jitter happens to cover a range. `bus_concurrency_scd30_write_vs_siblings.py` still fires
at exactly ONE fixed offset (0.3s in) - the one-write budget makes a real multi-offset sweep
structurally impossible there, not a design choice to skip it; its own docstring now says so
explicitly rather than silently reading like an oversight. Real hardware still has no literal
equivalent of the mock tier's `asyncio.sleep(0)`-count offset (a yield count means nothing against a
real preemptible interpreter and real bus timing) - a real elapsed-time delay is the honest,
tier-appropriate substitute.

**Two real gaps closed in dev's own general-call/address-sweep coverage**, found by checking every
mock-tier generic scenario type against what real hardware actually covers for dev's real topology
(i2c0: BMP3xx alone; i2c1: SCD30+SGP40+ISL29125):

- `sgp40_general_call_reset_hazard.py` used to run its concurrent-sibling check against SCD30 only,
  even though ISL29125 is also a real, non-broadcasting sibling on the same bus (mirroring
  `tests/_bus_hazard_catalog.py`'s own `scenario_general_call_does_not_disturb_concurrent_siblings`,
  which runs against every non-broadcasting occupant, not just one). Now reads both concurrently
  while SGP40's own `initialize()` fires its real general-call broadcast; the flash-tier test this
  wraps was renamed to `test_sgp40_general_call_reset_does_not_corrupt_concurrent_scd30_and_isl29125_
  transactions` to say so.
- `bus_topology_autodetect_and_hazard_sweep.py`'s own `KNOWN_ADDRESSES` table had drifted out of
  sync with the since-deleted `tests_hardware/bus_topology.py`'s own copy (that file's module
  docstring stated the invariant; nothing enforced it, which is why it drifted) - it was missing ISL29125 (`0x44`) entirely, so the address sweep never probed/labeled
  it and the lone-device self-hazard branch could never apply to it. Fixed: `ISL29125_I2C` support
  added to both the address table and the self-hazard construction/read branch.
  - Everything else in the mock tier's generic scenario set already had a real-hardware equivalent
    for dev's own topology once this pass checked systematically: same-occupant write-vs-own-read
    (per-driver same-device scripts, all three occupants), all-occupants-concurrent-reads
    (`isl29125_cross_device_concurrency.py` already runs all three of i2c1's occupants at once), and
    the "rogue general call against a lone occupant with no real broadcaster" case (i2c0's own
    BMP3xx-alone bus) - the topology script's own self-hazard branch already covered this before this
    pass, for whichever known device turns out to be the bus's sole occupant.

**Flash-tier -> bench-tier parity**: added
`test_isl29125_config_write_does_not_disturb_concurrent_sibling_reads_under_api_load`
(`tests_hardware/bench/test_bus_concurrency_under_api_load.py`) - the same ISL29125-writes-while-
siblings-read hazard as the flash-tier test above, driven through the real HTTP/REST stack instead of
the bare driver (`PUT /sensors {"ISL29125": {"Resolution": ...}}` alternating between both real valid
settings, concurrent with `GET /sensors` hammering, with the board's original `Resolution` restored
in a `finally` block - the same push/restore duty `test_sensor_config_push_over_real_hardware.py`'s
own BMP3xx test already owes for a shared bench rig).

**SCD30 has no bench-tier (or any REST-layer) counterpart, and this is structural, not a scope gap**:
`asy_scd30_driver.py` registers zero `_push_callbacks` (already noted by
`test_sensor_config_push_over_real_hardware.py`'s own comment) - there is no `PUT /sensors` field
that could ever reach SCD30's own NVM write at all. The flash tier's own
`bus_concurrency_scd30_write_vs_siblings.py` (gated behind both `--allow-persistence-writes` and
`--allow-scd30-extra-write` - see the Eleventh pass below) is therefore the only real-hardware
coverage this specific hazard can ever have, by construction of `src/` itself - recorded here
rather than left as a silent asymmetry between the two tiers.

Same honesty note as the Seventh pass: none of this pass's changes have been run against real
hardware either (still no go-ahead this session) - `ruff`/`mypy` clean, structurally consistent with
proven scripts, but unverified on silicon until a real bench session confirms it.

## Ninth pass - auditing the flash-tier/bench-tier bus-hazard pairing itself, and a real miscoverage found

Direct follow-up question: does *every* pre-existing flash-tier bus-hazard test (not just the ones
this session added) actually have a bench-tier counterpart? Checking systematically found one
genuine, surprising miscoverage plus two closeable gaps:

- **SGP40's general-call hazard has ZERO real bench-tier coverage, despite `test_bus_concurrency_
  under_api_load.py` appearing to exercise it.** Every one of that file's four tests already runs a
  `sgp40_reset_trigger_worker()` PUTting `SGPResetVOC` concurrently with GET load - reasonable to
  assume, from the name and the pattern, that this re-triggers the same general-call broadcast the
  flash tier's `sgp40_general_call_reset_hazard.py` proves survives concurrent reads. **It does not.**
  Read the real call chain directly: `reset_voc()` only sets a flag consumed by the next
  `measure_index_and_raw(reset=True)` call, which calls `vocalgorithm_reset()` - a software-only VOC
  algorithm reset. The real broadcast only ever fires from `SGP40_I2C._reset()`, itself only called
  from `initialize()`, itself only ever invoked internally at driver setup/task-supervisor restart -
  never through any `_push_callbacks`/REST field. There is currently no way to force this hazard on a
  live, already-running system via REST at all - a bench test would need a real reboot mid-load,
  which would confound the very load being measured. Documented as a structural exception (module
  docstring, `test_bus_concurrency_under_api_load.py`) rather than left implied by the
  superficially-similar-looking worker.
- **SGP40 was never schema-sanity-checked in any bench GET worker at all** - `_schema_sanity_findings()`
  checked SCD30/BMP3xx/ISL29125's own config fields but no SGP40 field, so a torn/corrupted VOC
  reading under bench load would have gone completely undetected. Closed: checks `SGP40.VOC` against
  the same `[0, 500]` bounds `sgp40_voc_algorithm_quality.py` already uses.
- **BMP3xx's same-device write-vs-own-read had no bench-tier counterpart**, even though (unlike
  SCD30) BMP3xx has real REST-pushable fields already exercised elsewhere
  (`test_sensor_config_push_over_real_hardware.py`). Closed:
  `test_bmp3xx_config_write_does_not_disturb_its_own_concurrent_reads_under_api_load` - alternates
  `PressOvers` between both real valid settings concurrently with this same sensor's own GET reads,
  restoring the original value afterward.
- **SCD30's own same-device write-vs-own-read** has the identical structural absence as its
  write-vs-siblings hazard (zero `_push_callbacks`) - recorded as the same exception, not a second
  one, right next to the existing note.

Same honesty note again: the two new/closed items above are `ruff`/`mypy`-clean but unverified
against real silicon this session.

## Tenth pass - full test-suite sweep for tier/layering completeness and wrongly-trusted tests, beyond bus-hazard (project owner, 2026-09-15, BACKLOG.md HIGH PRIORITY item)

Direct follow-up to the Ninth pass's own SGP40 miscoverage: is that failure mode (a test whose
name/pattern matches a hazard but whose real call chain doesn't reach it) present anywhere else in
the suite, and does E.6.6/E.6.1's tier-parity requirement hold outside the bus-hazard domain? Swept
UART, WiFi/network/NTP/DNS, FRAM/memory/reboot/watchdog, and webserver/notification/config-push -
each domain's own real call chains traced against the test files that claim to exercise them, not
grepped for coverage. No second instance of the exact SGP40 bug (a real hardware trigger silently
substituted with a software-only one) turned up, but several real tier-parity gaps did.

**Fixed this pass:**

- **`isl29125_plausibility_read.py` was a real, working, silicon-ready device script with no pytest
  wrapper at all** - written during the ISL29125 promotion (PR #83) but never wired into
  `test_sensor_accuracy.py`, so it never actually ran as part of this suite. Closed:
  `test_isl29125_real_reading_is_within_datasheet_plausible_bounds`.
- **ISL29125's entire real REST config-push surface had zero bench-tier coverage** - unlike SCD30
  (explicitly excluded, zero `_push_callbacks`), ISL29125 has four hardware-backed, read-back-able
  fields (`Resolution`/`Range`/`IrCompOffset`/`IrCompAdjust`) with no exclusion comment, suggesting
  oversight rather than a decision. Closed:
  `test_isl29125_resolution_range_and_ir_comp_push_over_real_rest_and_readback` in
  `test_sensor_config_push_over_real_hardware.py` - also pushes `RangeAuto: False` alongside `Range`,
  since under real auto-ranging (the driver's own default) the chip's own range bit is the state
  machine's choice, not the user's setting, and `_read_sensor_dict()` omits `Range` from a live
  snapshot entirely rather than misreport it (`asy_isl29125_driver.py`'s own comment) - a real
  readback of a pushed `Range` needs auto-ranging off first.
- **FRAM's write-protect gate (`get_write_protected()`/`set_write_protected()`) had real flash-tier
  coverage with its own bench-vs-flash split never written down anywhere**, unlike storage-pause
  gating's own explicitly-documented split. Confirmed structural (E.6.6 exception 2: neither method
  has a REST route at all, by grep) and now stated as such directly in `test_fram_storage.py`.
- **`SystemService.start_and_check_tasks()`'s own real restart-a-dead-task mechanism had no
  real-hardware test at all** - the exact recovery rung CLAUDE.md's memory-safety-discipline rule
  leans on ("trust `system_service.py`'s task supervisor to restart a task that still dies"), proven
  only at the mock/twin tiers. New: `device_scripts/system_service_restarts_a_real_dead_task.py` +
  `tests_hardware/flash/test_task_supervisor.py`'s
  `test_start_and_check_tasks_restarts_a_real_dead_task` - a starter that dies immediately, checked
  called at least twice within one real `_TASK_CHECK_TIME` (2s) cycle. Deliberately stops at ~3.6s
  real time (task_errors capped at 200): a task that dies immediately adds `_TASK_FAIL_INCREMENT`
  (100) per cycle, and `_TASK_FAIL_MAX` (300) would otherwise trip a real reboot around the 4th
  cycle (~7s) - not what this script is testing.
- **`PUT /notification`'s `PauseTime` field was initially misjudged as an unfixable structural
  exception during this pass (no GET /notification field reads it back) - wrong**: buildgen's own
  generated `_notification_status()` puts a live `PauseTime` (`await notification.get_override_led()`)
  into `GET /status`'s own `"notification"` section on every real device, the same real signal
  `tests/test_digital_twin_sensortask_integration.py`'s own
  `test_put_pause_time_round_trips_and_counts_down_over_real_http` already reads. Closed (once
  found, not left as the wrong "exception"):
  `test_notification_pause_time_push_counts_down_over_real_rest` in
  `test_sensor_config_push_over_real_hardware.py` - proves the real `auto_led_override()` background
  task actually decrements the pushed value to 0 on real hardware, not just that the PUT stuck.

**Confirmed structural exceptions (no fix possible, recorded so the absence reads as a decision, not
a gap):**

- **`PUT /notification`'s `lightCmdLED` field has no bench-tier equivalent, and currently cannot** -
  it drives the Neopixel directly, and WS2812 has no read protocol at all (the same reason its own
  timing check is manual-only - see the Known assumptions entry above). Not fixable without a real
  scope/logic-analyzer in the bench rig's own automated toolchain.
- **Neopixel/WS2812 signal timing** - already a documented structural exception (Known assumptions
  entry above); reconfirmed still accurate, not re-litigated.
- **SCD30's real IRQ-pin edge and same-device write-vs-own-read** - already-documented structural
  exceptions (zero `_push_callbacks`); reconfirmed, not re-litigated.

**Named, not fixed this pass** (real, credible findings from the domain sweeps below, each requiring
either a dedicated real-hardware session to get right or a project-owner decision this pass
shouldn't make unilaterally - disclosed rather than silently dropped, per BACKLOG.md's own
"resolved or migrated, never silently dropped" rule):

- **UART's sharpest invariant (`asy_uart_driver.py`/`asy_uart_comm.py` may never block the loop -
  CLAUDE.md) has its F.5.8 half real-hardware-tested only via a hand-rolled clamp, never the shipped
  driver's own `ready()`/`_buffered()`.** `device_scripts/uart_read_never_blocks_the_loop.py`
  deliberately uses raw `machine.UART` "so it stays true independently of how `asy_uart_driver` is
  arranged internally" (its own docstring) - honest, not a wrongly-trusted test, but it means no
  real-hardware run ever calls the actual shipped clamp. F.5.9 (idle poll rate) already has a
  real-driver-object proof (`uart_idle_poll_rate.py`); F.5.8 needs the analogous script.
- **Bench-tier UART traffic under load never issues a multi-chunk SET** - `UartLinkExerciser.
  _exercise_loop()` only ever calls `uart_get(_CMD_BANNER)`, so "bench ⊇ flash" (E.6.1) doesn't hold
  for the multi-chunk SET train the flash tier proves (`uart_crossover_exchange.py`). The exerciser
  already has `_CMD_ECHO`/`_set_callback` wired for exactly this; wiring a periodic SET into the live
  loop touches the real production exerciser, not just a test, so it's named here rather than done
  blind.
- **The mock-tier UART hazard catalog (~20 fault-injection scenarios: corruption, drop, truncate,
  duplicate, receive-overrun, lost-final-ACK, peer-reset-mid-transaction, and more) has only two
  real-hardware equivalents (silence, baud desync).** Plausibly a genuine E.6.6 structural exception
  (no MITM device sits on the crossover jumper to corrupt/drop/duplicate real bytes) but - unlike the
  SCD30/FRAM-write-protect precedents above - this was never actually written down as one anywhere,
  and a hand-built corrupt frame via a second raw `machine.UART` write (the same technique the mock
  tier's own `raw_frame()` helper uses in-process) is at least plausible. **Answered 2026-09-22
  (owner): it is a structural exception, for now.** Fault-injection hardware will come one day but
  is not available, so the catalog stays mock-only and is recorded as Part E.6.6's fourth
  exception rather than improvised with a second raw UART. Revisit when that hardware exists.
- **`_reboot()`'s own alarm-pool-exhaustion fallback (`_force_watchdog_starve = True`) is mock-only.**
  The technique to exhaust a real alarm pool already exists on real hardware
  (`fram_pause_unpause_and_gating.py`), so a flash-tier script is straightforward in principle - it
  would deliberately trigger a real watchdog-starvation reset (safe, same shape as
  `test_watchdog_starvation.py`), but getting the real timing right without a live board to verify
  against is exactly the kind of thing worth doing in a dedicated real-hardware session rather than
  blind.
- **NOTIFY's own FRAM chunk has no hard-reset-recovery bench test**, unlike SGP40's
  (`test_real_hard_resets_during_natural_fram_backup_activity_recover_cleanly`). Extending that
  ~5-minute, 3-real-hard-reset test to a second FRAM-backed module needs first identifying NOTIFY's
  own equivalent of `BackupTS` (an observable "a fresh write just completed" signal) - not confirmed
  to exist yet, so left named rather than guessed at.

**Confirmed clean, no fixes needed** (traced end-to-end, not just grep-counted): WiFi's real bench
worker call chains (`ap_down`/`ap_up`, UDP block/redirect, `netem` fault injection, hotspot
role-reversal, spoofed-NTP-source) all genuinely reach the real mechanism their names claim; the
wedged-WiFi `isconnected()` backstop has real, automated bench coverage with real timing data
(`test_network_resilience.py`), not just a one-off manual finding; UART's flash-tier fault-injection
and idle-poll-rate scripts, and mock/twin/flash parity for the core happy-path and one-sided-silence
scenarios, are all genuine; BMP3xx/SGP40's REST config-push is proven end-to-end via real
GET-after-PUT readback; the bench mempause test and the flash/bench memory-stress split are both
honestly and correctly scoped, not wrongly-trusted; SGP40's `SGPResetVOC` push is a thin test (it
never asserts the reset's own effect) but says so in its own comment - not a new instance of the
Ninth pass's bug, just worth naming.

Same honesty note as every real-hardware addition in this file: the new/changed files above are
`ruff`/`mypy`-clean but unverified against real silicon this session.

## Persistence-write gating: one global flag plus an AND-gated extra flag

**Standing design, project owner's own choice** (broadened from SCD30-only to all persistence,
2026-09-17): every real write to a **limited-endurance** store is gated by two flags/markers,
deliberately not one, in a strict hierarchy —
- `--allow-persistence-writes`/`@pytest.mark.persistence_write` is the single **global** permission:
  without it, no test spending a real limited-endurance write runs at all. That covers the routine
  per-session SCD30 write `scd30_continuous_measurement_triggered` makes for the flash-tier
  bus-hazard group (7 tests, directly or transitively), the two flash-tier reboot tests that write
  real config through `ConfigManager.write_config()`, and every bench-tier test issuing a
  config-persisting PUT.
- `--allow-scd30-extra-write`/`@pytest.mark.scd30_extra_write` is a **narrower** opt-in, carried
  ALONGSIDE `@pytest.mark.persistence_write` (never in place of it) on the one test that spends a second
  write beyond the routine one. It is AND-gated with the global flag in code, not just by
  convention — passing it alone, without `--allow-persistence-writes`, still deselects that test.

**What the gate is about: the write a test OWNS, not one it is reached through** (project owner's
clarification, 2026-09-18). A persisting write that *is* the thing under test is optional, and
belongs behind the marker. A persisting write that is a **prerequisite** several other tests are
reached through — `test_hotspot_role_reversal.py`'s `joined_hotspot` clearing the SSID to force
hotspot mode (and restoring it in teardown), `conftest.py`'s `_recover_stale_dut_credentials()` —
stays unmarked and allowed: gating it would deselect the tests it exists to enable, and those tests
are not what spends the wear. So the choice the flag offers is "test everything and accept the
higher write wear" versus "test everything that matters and keep wear as low as it can go" — never
"spend zero". `tests_scripts/test_persistence_write_marker_completeness.py` pins the prerequisite
set by name, so a new one has to be triaged against this rule rather than silently joining it.

**What counts as a limited-endurance store**: the SCD30's own on-chip NVM, and the RP2040's flash
filesystem — which every accepted *config-persisting* PUT writes through `config_manager.py`'s own
`json.dump()`, so a REST write is a flash cycle, not just a network round trip. A **dispatch-only**
PUT is deliberately outside the gate, because it is never persisted at all: `SystemCmd`,
`PauseTime`, `lightCmdLED`, `ResetErrors`, plus any schema field carrying `dispatch=true` in its own
`@web` tag (`SGPResetVOC`, `ISLCalibrate` today — derive that set from the tags, never from this
list going stale). FRAM is **not** in scope: its endurance is effectively unbounded at this
project's write rates.

This shape exists because a real, unbypassable rule and a real, opt-in-only rarity are two
different things: both stores have a finite write-wear budget, so it must be possible to run the
full flash- and bench-tier suites (dozens of tests) without spending any write a test *owns* —
that's the global flag's job. Separately, one specific test spends a second write beyond the
routine one and stays behind its own narrower opt-in, since running the routine group should never
implicitly commit to that extra write too. Both flags are skipped/deselected by default, matching
every other opt-in real-hardware gate in this file.

**Be precise about what a plain invocation costs**, since it is not zero and an earlier revision of
this section said it was, two paragraphs after stating the rule that makes it false. A plain
`scripts/run_flash_hardware_suite.sh` spends no real persistence write at all — every prerequisite
writer named above is bench-only. A plain `scripts/run_bench_hardware_suite.sh` spends the
prerequisite ones: `joined_hotspot`'s stage-0 `PUT {"SSID": ""}` and its stage-7 restore on every
run that reaches the hotspot module, plus `_recover_stale_dut_credentials()`'s SSID/PW push on a run
where the DUT cannot rejoin the bench AP. That is the deliberate cost of the owner's rule, not an
oversight — gating them would deselect the dozen-odd tests they exist to enable.

**Read the deselected count in the verdict.** Because the gate deselects at collection time rather
than skipping per test, a gated run is invisible to every check in
`scripts/_require_clean_hardware_run.sh` — so that script now names the count in its own OK line
(13 of the bench tier's 73 tests, 9 of the flash tier's 51, as of this writing - measured by real
`--collect-only` runs, not estimated). "Clean" there means
"everything that ran, passed", not "everything ran".

**Mechanism:**

- `tests_hardware/conftest.py`'s `pytest_collection_modifyitems()` is the single deselection point:
  it deselects every `persistence_write`-marked item when `--allow-persistence-writes` is absent, and every
  additionally `scd30_extra_write`-marked item when `--allow-scd30-extra-write` is absent. No test
  checks either flag inline. This matters beyond style: `scripts/_require_clean_hardware_run.sh`
  fails a run on any *unexpected* `SKIPPED` test, and has no allowance for either SCD30 flag the way
  it does for `--allow-flash-cycle`/`--soak-tier`/`--allow-multi-day-rollover-wait` — a plain
  `scripts/run_flash_hardware_suite.sh` invocation (no extra flags) needs the SCD30 tests to
  disappear from the run cleanly. Collection-time deselection reports as `N deselected` in pytest's
  own summary line, never a per-test `SKIPPED`, so that script's grep never needs an entry for it.
- Every test that depends on `scd30_continuous_measurement_triggered`, directly or transitively,
  carries `@pytest.mark.persistence_write` — the 6 routine-group tests, plus two ISL29125-named tests
  (`test_isl29125_cross_device_concurrency_with_its_i2c1_neighbours`,
  `test_isl29125_config_write_does_not_disturb_concurrent_sibling_reads`) whose SCD30 leg also
  depends on that fixture. Marker placement is derived from the fixture's real dependents, not from
  which tests look SCD30-related by name.
- `scd30_continuous_measurement_triggered` (`tests_hardware/flash/conftest.py`) raises loudly if
  it is ever invoked without `--allow-persistence-writes`, as a backstop: correct marker placement on every
  dependent test makes this unreachable via the collection-time deselection above, but a future test
  that forgets the marker fails hard here instead of silently spending a real write.

## WP4/Topic 6 - FRAM capacity check, real-hardware tier

`test_fram_storage.py::test_every_fram_wired_module_gets_a_real_chunk_after_a_full_system_build`
(device script `fram_capacity_after_full_system_build.py`) closes the real-hardware leg of
CLAUDE.md's implicit-FRAM-wiring rule's own capacity backstop: a shipped firmware asking for more
FRAM than its own chip has must be a hard, automatic, pre-flash test failure, not a silent
boot-time console print nobody's watching. Builds the real `dev` object graph
(`sensortask_dev.build_system()`) on the real board, then checks that every module which should
have inherited a real FRAM chunk (its own `pr`, plus its own `cfgmgr` where one exists) actually
got one rather than silently degrading to RAM-only.

**Deliberately not `fram.allocated_size <= fram.size`** - `AsyFramManager.get_chunk()` checks
capacity *before* incrementing `allocated_size`, never after, so that comparison can never be
false by construction and would be a tautology, not a check. A `None` chunk reference on a module
that should have gotten one is the real, observable signal that capacity ran out; the mock-tier
equivalent (`tests/_sensortask_scenarios.py`'s `fram_chunks_are_all_successfully_allocated_not_out_of_memory`,
run for every real device) uses the same shape, and
`tests/test_base_classes.py`'s `test_sensorreaderconfig_fram_allocation_failure_and_missing_config_file_together`
is the negative case proving it can actually fail.

**mpremote-only by design (owner's own decision)**: no new `/status` field - this is a one-time,
build-deterministic build-validity fact (`AsyFramManager` is a bump-pointer allocator with no
deallocation, so "does everything fit" is fully decided once construction finishes, and stays true
for that build's entire life), not live operational state a client needs to query.

**Extended by WP3**: `_CANDIDATE_MODULE_NAMES` now also checks `uart_link_init`/`uart_link_resp` -
`dev.toml`'s only two `uart_link` instances, both wired with `fram_target = "fram"` - so this same
real-hardware check covers the UART crossover link's own errno/wrnno history getting a real chunk,
not just the sensor/infra modules it already covered. `UartLinkExerciser`'s own `fram=`/`logger=`
forwarding is otherwise covered by `tests/test_asy_uart_link_driver.py` (mock tier: functionality,
the no-`fram=` regression, the allocation-failure fallback, the `logger=` reach-through, and a
simulated-reboot roundtrip) and `tests/test_digital_twin_uart_link.py`'s
`test_both_ends_get_their_own_real_fram_chunk` (twin tier) - real-hardware visibility through
`/status` was already covered pre-WP3 by `tests_hardware/bench/test_uart_link_under_api_load.py`'s
own `get_errcount()` calls, since that was never conditional on RAM-vs-FRAM backing.
