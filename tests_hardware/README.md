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

## Environment variables

- `MPREMOTE_DEVICE` (or `--device` on any `pytest tests_hardware` invocation) - serial device path
  for the flash-tier board. Defaults to `/dev/ttyACM0`, same convention as
  `scripts/mpremote_connect.sh`.
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
  task added to `boot_entry/<device>_boot.py` (never committed - `git diff` confirmed clean after
  reverting, real production firmware rebuilt+reflashed before finishing), printing a fixed-format
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
`HardwareTestFailure`. A repro with both fixes in place still occasionally exhausted 3 attempts once;
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
