# tests_hardware/ - real-hardware test tier

Implements SPECIFICATION.md Part E.6's flash/bench/manual backends: automated tests driven from the
host over `mpremote`/`nmcli`/`iptables` (never the MicroPython Unix port `tests/` uses - see
SPECIFICATION.md Part E.1), plus a structurally separate manual runner for tests that need a human's
hands. **Real-hardware execution is standing practice on the bench Pi4** - both the flash and bench
tiers run clean end to end as of 2026-09-04 (77 automated tests: 68 passed, 6 opt-in-skipped, 0
failed/errored); this file is the durable reference for prerequisites, environment variables, how to
run it, and the facts/assumptions worth knowing before trusting a run's results.

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
# default - this genuinely re-flashes the board, see SPECIFICATION.md Part E.6.3):
scripts/run_flash_hardware_suite.sh --allow-flash-cycle

# Manual tests (interactive, prints instructions, waits for confirmation):
scripts/run_manual_hardware_tests.sh --list          # see what's registered, run nothing
scripts/run_manual_hardware_tests.sh --only <name>   # run just one
scripts/run_manual_hardware_tests.sh                 # run all of them, in sequence
```

Both automated scripts are plain `uv run pytest` wrappers - any pytest flag works (`-k <substring>`,
`-m role_reversal`, `-v`, `--tb=short`, ...). `--collect-only` works with nothing attached at all
(every fixture skips cleanly, never errors, when the hardware it needs isn't reachable).

## Known assumptions and open findings

Flagged while writing this tier against real source/datasheets, or found once real-hardware runs
started. Read them before trusting a run's results blindly - a failure in one of these areas may
point at a flagged assumption being wrong, not at a real product bug. Resolved items are struck
through, kept (not deleted) so a reader mid-investigation doesn't wonder whether something was ever
a live question:

- ~~Does `mpremote`'s implicit soft-reset re-execute `modules/_boot.py`/`boot.py`/`main.py`?~~ —
  **resolved: no.** Confirmed against the pinned MicroPython C source and empirically on real
  hardware: only a genuine `hard_reset()` resumes the live system; `exec()`/`run_isolated()` never
  do, regardless of `soft_reset_after`. See `harness.Board.run_isolated()`'s own docstring for the
  full finding. Tests that need to observe the *real* boot sequence correctly use `hard_reset()` +
  `tail_log()` instead, for exactly this reason.
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
  serialize valid JSON), a real 413 over `max_content_length=4096`, and syntactically valid but
  nonsensical field values (wrong type, out-of-range, an entirely unknown sensor key) - each
  confirmed against `_body_as_dict()`/`base_classes.py`'s `_set_dict_cfg()` to land exactly where the
  real source says it should, including confirming none of these paths ever reach
  `ConfigManager.write_config()` (so nothing needed restoring afterward, unlike the third pass's
  BMP3xx config-push test).
- **Slowloris-style partial requests and abrupt mid-response disconnects**: grounded against
  `_serve()`'s own outer `asyncio.wait_for(..., outer_cap_s)` (production default 15.0s, confirmed
  not overridden anywhere in `sensortask_wozi.py`) - the exact mechanism the code's own comment says
  bounds "a Slowloris-paced client no single per-call timeout alone would catch".

**Deliberately not covered, and why** (see `test_network_resilience.py`'s own module docstring for
the full account): DHCP flakiness/slowness/rubbish responses. The DUT's DHCP *client* behavior lives
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
this pass (the hotspot role-reversal scenario's own dozen-plus fault tests, the flash-tier timer-
exhaustion/scheduler-saturation scripts, etc.) - a real, larger remaining gap, flagged here rather
than silently left looking finished.
