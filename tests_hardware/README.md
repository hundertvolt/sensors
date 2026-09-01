# tests_hardware/ - real-hardware test tier

Implements HARDWARE_TEST_PLAN.md's flash/bench/manual backends: automated tests driven from the
host over `mpremote`/`nmcli`/`iptables` (never the MicroPython Unix port `tests/` uses - see
SPECIFICATION.md Part E.1), plus a structurally separate manual runner for tests that need a human's
hands. **Nothing in this directory has been run against real hardware yet** - it was written and
verified collectible/lint-clean/type-correct in a session with no board or bench rig attached (see
HARDWARE_TEST_PLAN.md's own provenance note). This file is what a dedicated session *with* real
hardware needs to actually start running it.

**If you're the session about to actually run this tier for the first time, read
`REAL_HARDWARE_HANDOFF.md` (repo root) first** - it's a waiting-for-go-ahead handoff doc with a
suggested run order and the critical safety facts, and explicitly must not be acted on without the
project owner's go-ahead given directly in your own conversation.

## Prerequisites

1. `uv run toolchain/setup_toolchain.py env --tier flash` (real USB board attached) or `--tier
   bench` (also needs a WiFi adapter for the bridge) - see README.md's own environment-tiers table
   and `toolchain/setup_toolchain.py`'s own docstring for the full recipe (dialout group, device
   auto-detection, `br0-wifi-ap` bridge creation via `ensure_bench_bridge()`).
2. The board must already be running the real, unmodified production firmware
   (HARDWARE_TEST_PLAN.md §6.1's "one allowed flash" - `uv run scripts/build_firmware.py wozi` +
   `picotool load -x -v`, or the manual BOOTSEL-button first flash for a genuinely blank board, see
   `tests_hardware/manual/manual_toolchain.py`).
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

## Environment variables

- `MPREMOTE_DEVICE` (or `--device` on any `pytest tests_hardware` invocation) - serial device path
  for the flash-tier board. Defaults to `/dev/ttyACM0`, same convention as
  `scripts/mpremote_connect.sh`.
- `BENCH_AP_PASSWORD` - the real bench bridge AP's own password, needed only by
  `tests_hardware/bench/test_hotspot_role_reversal.py::test_real_credentials_put_succeeds_and_confirms_accepted_values`
  (stage 6's real credential handoff). `toolchain/setup_toolchain.py`'s own `ensure_bench_bridge()`
  deliberately never re-prints this on an idempotent re-run ("a later idempotent run will report the
  SSID again, but never re-prints the password") - find it from wherever it was recorded when the
  bridge was first created (or reset the bridge and re-run `env --tier bench` to generate + print a
  fresh one, if that's acceptable for this session). Without it, that one test skips cleanly rather
  than failing or guessing.

## Running

```bash
# Automated, flash tier only (real USB board, no network):
scripts/run_flash_hardware_suite.sh

# Automated, flash + bench tier (real USB board + real WiFi bridge):
scripts/run_bench_hardware_suite.sh

# Add --run-long-soak to also run the multi-hour/multi-day passive soaks (skipped by default):
scripts/run_bench_hardware_suite.sh --run-long-soak --long-soak-seconds 21600

# Add --allow-flash-cycle to also run the one deliberate re-provisioning-flash test (skipped by
# default - this genuinely re-flashes the board, see HARDWARE_TEST_PLAN.md §6.1):
scripts/run_flash_hardware_suite.sh --allow-flash-cycle

# Manual tests (interactive, prints instructions, waits for confirmation):
scripts/run_manual_hardware_tests.sh --list          # see what's registered, run nothing
scripts/run_manual_hardware_tests.sh --only <name>   # run just one
scripts/run_manual_hardware_tests.sh                 # run all of them, in sequence
```

Both automated scripts are plain `uv run pytest` wrappers - any pytest flag works (`-k <substring>`,
`-m role_reversal`, `-v`, `--tb=short`, ...). `--collect-only` works with nothing attached at all
(every fixture skips cleanly, never errors, when the hardware it needs isn't reachable).

## First real run - things flagged as genuinely unverified, not silently assumed

These were found and explicitly flagged while writing this tier against real source/datasheets, but
could not be checked further without hardware. Read them before trusting the first real run's
results blindly - a failure in one of these areas may point at the flagged assumption being wrong,
not at a real product bug:

- **Does `mpremote`'s implicit soft-reset (every `exec()`/`run_isolated()` call, confirmed against
  real mpremote 1.29.0 source - see `harness.Board.run_isolated()`'s own docstring) re-execute
  `modules/_boot.py`/`boot.py`/`main.py`, or does raw-REPL mode suppress that?** Tests that need to
  observe the *real* boot sequence deliberately use `hard_reset()` + `tail_log()` instead of
  `exec()`/`run_isolated()` specifically to sidestep this, but the underlying question itself is
  still open.
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
- **`kick_client()`'s `iw dev <iface> station del <mac>`** - the *syntax* is confirmed correct
  (checked directly against real `iw 6.7`'s own `iw help` output during this session's re-audit:
  `dev <devname> station del <MAC address>` matches exactly), but whether NetworkManager's own
  AP-mode hostapd backend actually *honors* a raw `iw station del` command issued alongside it is
  still unverified and can only be confirmed on real hardware. Not currently called by any test in
  this tier, but flagged in `bench_control.py`'s own docstring for whoever reaches for it next.
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
- **WS2812/Neopixel timing has no datasheet in this repo's `datasheets/` folder at all** (only
  bmp3xx/fram/pico w/scd30/sgp40 - confirmed by listing the directory) - the manual
  `test_real_ws2812_neopixel_signal_timing` test is deliberately qualitative (visual/scope check,
  human judgment) rather than asserting any specific timing value pulled from memory, per CLAUDE.md's
  "say so explicitly if the datasheet isn't there" rule.

## A mistake this session made and then corrected - SCD30 RDY pin

An earlier pass through this file claimed `src/asy_scd30_driver.py` never wires a real GPIO to the
SCD30's own RDY pin, and skipped `test_scd30_rdy_pin_real_irq_edge` on that basis. **That claim was
wrong**, caught by the project owner: the driver's own module docstring says plainly "SCD30_Reader
runs the read loop plus an IRQ-pin self-healing trigger", and the mechanism is fully real -
`SCD30_Reader`'s own `irq_pin: int` constructor parameter (production value GPIO 8, via
`SCD30_Reader(i2c0, 8, ...)` in `sensortask_wozi.py`), a real `irq_pin.irq(trigger=IRQ_RISING,
...)` wired in `start_timer()`, and a genuine staged self-healing fallback in `scd_init_irq()` (a
500ms software poll that manually fires the same trigger event if the real IRQ was somehow missed
and the pin is stuck HIGH). The earlier check grepped for the literal string "rdy" and found
nothing (the code calls it "irq_pin"/"IRQ" throughout, not "rdy"), then stopped there instead of
reading the rest of the file - the module's own header sentence would have caught this immediately.
Fixed: `test_scd30_rdy_pin_real_irq_edge` is now a real, implemented test
(`test_scd30_real_irq_edge_drives_a_real_read`, `tests_hardware/device_scripts/
scd30_real_irq_edge.py`) - see that script's own docstring for the corrected design and its one
genuine, disclosed limit (software alone can't fully distinguish a genuine hardware IRQ firing from
the self-healing fallback firing instead; only a scope on the pin itself could).

## More findings from a second, deeper re-audit (requested directly, after the mistake above)

Re-reading every driver this tier makes claims about in full (not just the narrow greps that caused
the SCD30 mistake) surfaced two more real issues, both fixed:

- **`scd30_plausibility_read.py` polled sensor data without ever starting the read loop that would
  populate it.** `get_data()` only ever returns whatever `_store_scd()` last wrote via
  `_set_meas_data()` (confirmed directly against `base_classes.py`), which only happens from inside
  `read_loop()` - a task that was never started. The script could only ever have printed FAIL.
  Fixed: it now calls `start_timer()` and starts `read_loop()`/`scd_init_irq()` before polling, the
  same three calls `sensortask_wozi.py`'s own real wiring makes.
- **A permanent-WLAN-deactivation risk in the hotspot role-reversal scenario's own stage 6** - see
  this file's own "first real run" list above for the full account (`asy_wifi_service.py`'s
  `_register_sta_connection_failure()`). Fixed with a `hard_reset()` recovery fallback in
  `joined_hotspot`'s own fixture teardown.
- **Bare `uv run pytest tests_hardware` (no path scoping) used to also collect and would have run
  the manual tests as if they were ordinary pytest tests** - each calls `input()`, so running them
  this way would hang forever, directly against this tier's own "manual tests must never be silently
  mixed into an unattended pass" design principle. `scripts/run_flash_hardware_suite.sh`/
  `run_bench_hardware_suite.sh` were always scoped to avoid this, but the underlying structural gap
  was real. Fixed by renaming every file in `tests_hardware/manual/` away from the `test_*.py` glob
  pytest's default collection matches (e.g. `test_wifi_manual.py` -> `manual_wifi.py`) - confirmed
  directly: `uv run pytest tests_hardware --collect-only` at the time showed exactly the 44 automated
  tests this tier held then, zero from `manual/`, where it previously showed 56 (wrongly including
  all 12 manual ones). See the section below for the count as of the third pass (54).

Also positively confirmed (not previously verified live) during this same re-audit, for what it's
worth to a future reader: `nmcli device wifi connect`'s exact syntax and `iw dev <iface> station
del/dump`'s exact syntax, both checked directly against the real tools' own `--help` output
(`network-manager`/`iw` packages installed into this sandbox specifically to check them).

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

- **FRAM write protection actually gates a real write** (`device_scripts/
  fram_write_protect_roundtrip.py`, `flash/test_fram_storage.py`): sets the real WPEN|BP0|BP1
  status-register bits, confirms a real write is genuinely rejected while protected and succeeds
  once cleared again - not just "can a chunk be written at all" (the roundtrip test above already
  covers that).
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
