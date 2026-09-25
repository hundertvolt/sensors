# Harvest — HW: Real-hardware tier

What the project's own comments, docs and history already record for this area (snapshot `2a88cc8`).
Recorded, not verified or triaged; `audit/HARVEST.md` explains the kinds, tags and method.

Kinds: SETTLED 63, INVAR 113, MIRROR 60, LIMIT 115, RISK 67, ASSUME 189, PLATFORM 27, WORKAROUND 9, SUPPRESS 65, TODO 25, OPENQ 11, DRIFT 72, NOTE 6 — 822 items.


## tests_hardware/conftest.py

- **HW.N001** SETTLED · `tests_hardware/conftest.py:1-3` — "fixtures skip (not error) when the hardware
  they need isn't reachable, so `uv run pytest tests_hardware --collect-only` always succeeds" — Tier is
  designed to stay collectible and skip (not error) with nothing attached. · related: HW.T14 · [H07]
- **HW.N002** SUPPRESS · `tests_hardware/conftest.py:139-144` — "no real board reachable at {b.device}
  ... Not a failure" — Session `board` fixture skips the whole dependent tier when `is_reachable()`
  fails — and `is_reachable()` itself raw-REPL-interrupts the live system (harness.py:409-411). ·
  related: HW.T13 · [H07]
- **HW.N003** SUPPRESS · `tests_hardware/conftest.py:153-157` — "no bench WiFi bridge configured
  (br0-wifi-ap missing)" — `bench` fixture skips every bench test when the NM profile is absent. ·
  related: HW.T13 · [H07]
- **HW.N004** SUPPRESS · `tests_hardware/conftest.py:27-37, 106` — "Not set by default, so long_soak
  tests always skip in a general suite run" — `long_soak` gate (tiers short/mid/long) is an in-test
  `pytest.skip`, not a deselect (implemented per test: flash/test_memory_stress.py:88-90,
  flash/test_bus_electrical_timing.py:84-86, bench/test_memory_stress_bench.py:116-118, 137-139). ·
  covered-by: HW.T13 · [H07] ⟨quote not matched at the anchor⟩
- **HW.N005** SUPPRESS · `tests_hardware/conftest.py:44-53, 107` — "a real, fixed ~12.4-day wait
  (time.ticks_ms()'s own 2**30 rollover) ... never bundled with --soak-tier" — `multi_day_rollover`
  gate, in-test skip (flash/test_bus_electrical_timing.py:115-116). · covered-by: HW.T13 · [H07] ⟨quote
  not matched at the anchor⟩
- **HW.N006** SUPPRESS · `tests_hardware/conftest.py:38-43, 108` — "a deliberate re-provisioning flash -
  counts against the 'no extra flash cycles' constraint" — `flash_cycle` gate, in-test skip
  (flash/test_toolchain_flash_boot.py:54-55). · covered-by: HW.T13 · [H07]
- **HW.N007** DRIFT · `tests_hardware/conftest.py:65, 111` — "Spends no write of any kind, so it is its
  own flag rather than a persistence one" — `neopixel_sweep` help claims no writes, while the plan's
  HW.S05 records ~5 flash writes in isl29125_mechanism_envelope.py under this flag only (see that file
  below). · covered-by: HW.S05 · [H07]
- **HW.N008** SETTLED · `tests_hardware/conftest.py:69-88, 109` — "FRAM is deliberately NOT in scope -
  its endurance is effectively unbounded" — `persistence_write` covers SCD30 NVM + RP2040 flash FS only;
  FRAM writes are outside the wear gate by decision. · covered-by: HW.T01 · [H07]
- **HW.N009** SETTLED · `tests_hardware/conftest.py:80-83` — "a persisting write that is a shared
  PREREQUISITE (joined_hotspot clearing the SSID, _recover_stale_dut_credentials()) stays unmarked and
  still runs" — Named unmarked prerequisite writes; "not zero writes overall" without the flag. ·
  covered-by: HW.T01 · [H07] ⟨quote not matched at the anchor⟩
- **HW.N010** SUPPRESS · `tests_hardware/conftest.py:116-133` — "Central deselection point for every
  real limited-endurance persistence write" — Only `persistence_write`/`scd30_extra_write` DESELECT
  (invisible to a skip check); all other gates skip in-test. · covered-by: HW.T13 · [H07]
- **HW.N011** INVAR · `tests_hardware/conftest.py:89-102, 110, 126` — "passing this alone, without
  --allow-persistence-writes, still deselects the test" — `scd30_extra_write` is AND-gated and "always
  carried alongside @pytest.mark.persistence_write" — the carrying rule is convention only. ·
  covered-by: HW.T13 · [H07] ⟨quote not matched at the anchor⟩
- **HW.N012** SUPPRESS · `tests_hardware/conftest.py:112` — "informational marker, not skip-gated, so it
  reports the board's own wall whenever it is run" — `over_provisioned_image` runs on every pass
  regardless of image. · covered-by: HW.S25 · [H07]
- **HW.N013** SUPPRESS · `tests_hardware/conftest.py:113` — "bench radio temporarily stops hosting
  br0-wifi-ap ... informational marker, not skip-gated" — `role_reversal` is not a gate; the scenario
  runs in routine bench passes. · covered-by: HW.S25 · [H07]
- **HW.N014** INVAR · `tests_hardware/conftest.py:105-113` — markers registered via `addinivalue_line` —
  No `--strict-markers`: a misspelled gate marker would silently run ungated. · covered-by: CI.S13 ·
  [H07] ⟨quote not matched at the anchor⟩
- **HW.N015** ASSUME · `tests_hardware/conftest.py:161-164` — "a board with an older config file still
  answers to the persisted \"SensorNode\". Both are live" — Hardcoded DUT hostname candidates
  ("SensorStationDev", "SensorNode") mirror devices/dev.toml's injected default + legacy default. ·
  related: PAR.S11 · [H07]
- **HW.N016** MIRROR · `tests_hardware/conftest.py:165` — "_DUT_HOTSPOT_PASSWORD = \"12345678\" #
  src/asy_wifi_service.py's _VAL_HOTSPOT_PW default, which every devices/*.toml also declares" —
  Committed hotspot credential copy #1 (also bench/test_hotspot_role_reversal.py `_HOTSPOT_PASSWORD`,
  manual/manual_wifi.py) — consistency item, not alarm. · covered-by: HW.T11 · [H07]
- **HW.N017** ASSUME · `tests_hardware/conftest.py:168-200` — "stale stored WiFi credentials are the
  likely cause" — Last-resort recovery PUTs `/networking` SSID/PW = an unmarked RP2040 flash write
  (prerequisite class), and takes the bench AP down (join_dut_hotspot). · related: HW.T01 · [H07]
- **HW.N018** DRIFT · `tests_hardware/conftest.py:181-187` — "wait_until(_any_candidate_visible, ...)"
  before "bench.join_dut_hotspot(...)" — Scans via `is_ssid_visible()` while the AP is still up, though
  bench_control.py:195-196 says it "Requires ap_down() already called - this single-radio bench can't
  scan while still hosting an AP". (low) · related: HW.T12 · [H07] ⟨quote not matched at the anchor⟩
- **HW.N019** RISK · `tests_hardware/conftest.py:187-200` — "bench.join_dut_hotspot(found[0], ...)" is
  outside the `try:`/`finally: leave_dut_hotspot_and_restore_bridge()` — A failure inside join (after
  its own `ap_down()`) leaves the bench AP down with no `ap_up()`. (low) · related: HW.T12 · [H07]
- **HW.N020** ASSUME · `tests_hardware/conftest.py:211-212, 255` — "Strands main.py (soft reset via
  exec() stops it re-running) - always followed by a real hard_reset()"; "only a real hard_reset()
  reliably resumes normal auto-boot" — Harness-level fact about raw-REPL/soft-reset side effects. ·
  covered-by: HW.T06 · [H07]
- **HW.N021** ASSUME · `tests_hardware/conftest.py:233-234` — "Purely passive (tail_log only, no
  exec()/run()) - the board must already be mid-boot from a prior hard_reset()" — Caller-discipline
  precondition of `_wait_for_sta_ip`. · [H07]
- **HW.N022** ASSUME · `tests_hardware/conftest.py:250, 257, 262, 269` — "webserver task starts only
  after ntp_force_sync(), up to ~20s after STA connects" — Timing basis for 60 s STA wait + 30 s HTTP
  wait, three attempts (≈4.5 min worst case). · related: HW.S19 · [H07]
- **HW.N023** ASSUME · `tests_hardware/conftest.py:205-207` — "Retries hard_reset()+kick_all_stations()
  through known reconnect flakiness" — Known reconnect flakiness is worked around, not fixed; assumes
  stable DUT DHCP address after resets. · covered-by: HW.S19 · [H07]
- **HW.N024** MIRROR · `tests_hardware/conftest.py:196-198` — "accepted = {\"Valid\", \"Unchanged\"}" —
  Hardcoded copy of the REST setter result vocabulary. (low) · [H07]

## tests_hardware/flash/conftest.py

- **HW.N025** INVAR · `tests_hardware/flash/conftest.py:1-3, 18-22` — "this test group writes it at most
  once per pytest session" — SCD30 NVM write budget upheld by a session-scoped fixture that every
  dependent reuses. · covered-by: HW.T01 · [H07]
- **HW.N026** INVAR · `tests_hardware/flash/conftest.py:23-31` — "reaching here means a test forgot the
  marker: fail loudly rather than spend the write" — Runtime backstop for a missing `persistence_write`
  marker on this fixture's dependents (mechanical enforcement). · related: CI.S13 · [H07]
- **HW.N027** ASSUME · `tests_hardware/flash/conftest.py:20-21, 32` — "the one real NVM-persisted SCD30
  write (set_ambient_pressure(), doubling as \"trigger continuous measurement\")" — Wear-relevant write
  lives in device script scd30_same_device_rw_concurrency.py; 90 s timeout under run_isolated's 8 s WDT.
  · covered-by: HW.T01 · [H07]

## tests_hardware/soak_tiers.py

- **HW.N028** ASSUME · `tests_hardware/soak_tiers.py:1-3` — "a subdirectory's own conftest.py (e.g.
  flash/) shadows a bare `from conftest import ...` - confirmed directly via a real ImportError" —
  Reason the tiers live outside conftest.py; docs pointing at conftest.py for them are stale. · related:
  HW.S17 · [H07]
- **HW.N029** ASSUME · `tests_hardware/soak_tiers.py:7` — "SOAK_TIER_SECONDS = {\"short\": 60.0,
  \"mid\": 600.0, \"long\": 6 * 3600.0}" — Soak duration thresholds; no basis stated here (mid = 600 s
  matches "the original WDT-reset investigation", bench/test_memory_stress_bench.py:118). · [H07]

## tests_hardware/harness.py

- **HW.N030** MIRROR · `tests_hardware/harness.py:34-37` — "BOTH spellings: src/'s degrade handlers log
  str(e), so a real caught allocation failure reads \"memory allocation failed, ...\"" — Shared hardware
  MemoryError markers; kept in agreement with the unit/twin gates by
  tests_scripts/test_memory_error_gate_agreement.py (CLAUDE.md); only three bench/flash importers use
  it. · related: TEST.T18 · [H07]
- **HW.N031** LIMIT · `tests_hardware/harness.py:39-41` — "It describes the TREE, not necessarily the
  image on the board" — `configured_max_connections()` can disagree with the flashed image. ·
  covered-by: HW.T19 · [H07]
- **HW.N032** PLATFORM · `tests_hardware/harness.py:49-53` — "Not an RST - a read of it leaves modlwip
  writing the 400 to a NULL pcb (SPECIFICATION.md Part H.7.1)" — Probe shape chosen around a modlwip
  behaviour; FIN close relies on microdot answering 405 for an unrouted method. · related: REST.T06 ·
  [H07]
- **HW.N033** INVAR · `tests_hardware/harness.py:77-80` — "only the outer cap bounds it, which is why
  probe_limit * dwell_s stays under it" — 40 × 0.3 s = 12 s must stay under the server's 15 s outer cap
  — kept by default values only. · related: REST.T06 · [H07]
- **HW.N034** ASSUME · `tests_hardware/harness.py:56-59` — "The only figure that is silicon's own rather
  than the tree's, and the one a raised lwIP PCB count has to be confirmed against (SPECIFICATION.md
  Part B.14.2)" — Ceiling discovery is the claimed oracle for the lwIP PCB override. · related: HW.T19 ·
  [H07]
- **HW.N035** ASSUME · `tests_hardware/harness.py:60, 138-141` — "a slot outlives its client's close by
  0.71-0.84 s (SPECIFICATION.md Part H.7.1)" — Single dated measurement drives settle/release sleeps
  (settle_s/release_s 1.0 s, hold_s 0.3 s). · related: REST.T06 · [H07]
- **HW.N036** SUPPRESS · `tests_hardware/harness.py:64-70` — "best effort, one slot: the next test
  starts cleaner, and the walk's error stays the headline" — Drain failure after a failed walk is folded
  into the walk error. (low) · [H07]
- **HW.N037** LIMIT · `tests_hardware/harness.py:155-157` — "retrying sooner can alternate forever
  between two half-drained sets" — Known drain-livelock mode, mitigated by sleep only. (low) · [H07]
- **HW.N038** DRIFT · `tests_hardware/harness.py:175-177` — "its skip gate deselects rather than fails,
  which is exactly the way that goes unnoticed" — Bench gate is a `pytest.skip` (conftest.py:154), not a
  deselect; the MIRROR (connection names imported from setup_toolchain) is enforced by import. (low) ·
  related: HW.T13 · [H07]
- **HW.N039** WORKAROUND · `tests_hardware/harness.py:183-207` — "same effect as a physical
  unplug/replug, recovering a wedged raw-REPL-entry state" — USB unbind/rebind via `sudo tee /sys/bus/usb/...`
  for a bench USB wedge; removal trigger: none stated; needs passwordless sudo. · related: HW.S19 ·
  [H07]
- **HW.N040** DRIFT · `tests_hardware/harness.py:210-213` — "conftest.py turns it into a skip" —
  conftest.py has no HardwareNotAvailableError handler; only `is_reachable()` swallows it, while
  `tail_log()`/`_nmcli()` raise it mid-test as an error. (low) · related: HW.T12 · [H07]
- **HW.N041** SUPPRESS · `tests_hardware/harness.py:227-245` — "treating a raising check as
  not-yet-ready" — `wait_until` swallows every `Exception` from the check (including
  HardwareTestFailureError, an AssertionError) until timeout. · related: HW.T12 · [H07]
- **HW.N042** INVAR · `tests_hardware/harness.py:248-251` — "A bench test that runs a device script
  calls this in a finally or a fixture's teardown ... (tests_scripts/test_bench_restores_serving.py pins
  it)" — restore-after-device-script obligation, mechanically pinned by a tests_scripts meta-test. ·
  [H07]
- **HW.N043** ASSUME · `tests_hardware/harness.py:264-267` — "main.py's server may still be answering
  when this starts, so it first waits (up to `handover_s`) for that one to go quiet" — 20 s handover /
  120 s timeout basis unstated. (low) · [H07]
- **HW.N044** SETTLED · `tests_hardware/harness.py:296-300` — "a path that cannot exist, so the `board`
  fixture's own is_reachable() probe fails and SKIPS ... without mpremote ever opening some other
  device's port" — No-board sentinel design. · [H07]
- **HW.N045** INVAR · `tests_hardware/harness.py:318-337` — "never a bare ttyACM scan, which could pick
  the bench's Arduino ... Two matches is a hard error, not sorted()[0]" — Board selection by vendor ID;
  the Arduino C peer is on the same host. · related: HW.S19 · [H07]
- **HW.N046** ASSUME · `tests_hardware/harness.py:350-353` — "observed ttyACM0 -> ttyACM1 mid-suite" —
  Re-enumeration after hard reset has no index guarantee; pinned device is never re-resolved. · [H07]
- **HW.N047** WORKAROUND · `tests_hardware/harness.py:362-406` — "this bench's USB device can wedge into
  indefinite raw-REPL-entry failure until unbound/rebound" — 10 s transient-marker grace + ≤2 rebinds +
  one USB reset per call; removal trigger: none stated. · related: HW.T06 · [H07]
- **HW.N048** RISK · `tests_hardware/harness.py:408-416` — "Raw-REPL entry always Ctrl-C's the device,
  so never poll this against a live system" — `is_reachable()` is what the session `board` fixture calls
  first, so every run starts by stopping main.py (WDT reset ~8 s later). · covered-by: HW.T06 · [H07]
- **HW.N049** INVAR · `tests_hardware/harness.py:429-432` — "this always interrupts whatever's running
  first ... Never use for passive live-system observation" — exec()/run_isolated() usage rule,
  convention only. · covered-by: HW.T06 · [H07]
- **HW.N050** PLATFORM · `tests_hardware/harness.py:440-447` — "machine.WDT(timeout=8000)" armed before
  every `mpremote run`; "against the real frozen src/ drivers" — Every device script runs under an 8 s
  watchdog it must feed, against the image not the tree. · covered-by: HW.T19 · [H07]
- **HW.N051** SUPPRESS · `tests_hardware/harness.py:454-459` — "Deliberately ignore the return
  code/output" — `run_isolated_expect_reset` cannot tell a script that failed before reaching its reset
  from one that reset. · related: HW.T05 · [H07]
- **HW.N052** DRIFT · `tests_hardware/harness.py:466-469` — "The `reset` shortcut (DTR-line hardware
  reset, never a flash)" — mpremote `reset` is described as DTR; plan notes it is `machine.reset()`. ·
  covered-by: HW.S17 · [H07]
- **HW.N053** ASSUME · `tests_hardware/harness.py:474-480` — "Counts as a flash cycle if followed by a
  picotool write ... a non-zero/timeout exit here is expected, not a failure" — enter_bootloader()
  result is unchecked by design. · related: HW.T13 · [H07]
- **HW.N054** ASSUME · `tests_hardware/harness.py:482-501` — "Retries a transient post-hard_reset()
  USB-settle failure before raising HardwareNotAvailableError" — 10 s grace; raises (error, not skip)
  mid-test. (low) · [H07]

## tests_hardware/bench_control.py

- **HW.N055** MIRROR · `tests_hardware/bench_control.py:1-3` — "Shares connection names with
  toolchain/setup_toolchain.py's ensure_bench_bridge()" — Enforced by import (harness.py:178-180);
  role-reversal profile name is local. · [H07]
- **HW.N056** ASSUME · `tests_hardware/bench_control.py:18-21` — "always torn down ... so a crashed test
  run never leaves a stray profile behind" — A killed pytest cannot tear down; only join_dut_hotspot's
  delete-first (:207-210) recovers a leftover. · related: HW.T12 · [H07]
- **HW.N057** ASSUME · `tests_hardware/bench_control.py:24-33, 90, 201-203, 249, 255` — `["sudo", "nmcli", ...]`,
  `sudo iw`, `sudo iptables`, `sudo tc`, `sudo timeout ... tcpdump` — Bench host must grant passwordless
  sudo for nmcli/iw/iptables/tc/tcpdump/tee. · covered-by: HW.S19 · [H07] ⟨quote not matched at the
  anchor⟩
- **HW.N058** WORKAROUND · `tests_hardware/bench_control.py:59-62` — "`nmcli -g` escapes ':' as '\\:',
  so an SSID/PSK containing one reaches the DUT with stray backslashes" — `--escape no` for nmcli output
  quirk; removal: none stated. (low) · [H07]
- **HW.N059** ASSUME · `tests_hardware/bench_control.py:64-68` — "The real, current WPA2 PSK for this
  bridge's AP - needs `--show-secrets`" — Run-time credential read (the HW.T11 convention);
  `$BENCH_AP_PASSWORD` override mentioned at :61. · related: HW.T11 · [H07]
- **HW.N060** WORKAROUND · `tests_hardware/bench_control.py:72-80` — "if \"is not an active connection\"
  not in str(e): raise" — Idempotency depends on nmcli's English error text. (low) · [H07]
- **HW.N061** WORKAROUND · `tests_hardware/bench_control.py:85-100` — "Fixes the dominant cause of WiFi
  reconnection flakiness - a stale AP-side entry surviving a hard_reset() power-cycle" — `iw station del`
  per MAC before each hard_reset; removal: none stated. · [H07]
- **HW.N062** DRIFT · `tests_hardware/bench_control.py:102-107` — "iptables DROP rules on the bridge's
  OUTPUT/FORWARD chains" — Code appends to FORWARD only. · covered-by: HW.S17 · [H07]
- **HW.N063** RISK · `tests_hardware/bench_control.py:102-124` — "Always paired with unblock_udp_ports()
  in a test's own teardown" — Host iptables FORWARD DROP and nat PREROUTING DNAT survive a killed
  pytest; nothing restores at session start. · covered-by: HW.T12 · [H07]
- **HW.N064** LIMIT · `tests_hardware/bench_control.py:115-119, 126-129` — "works around a
  local-delivery gap in redirect_udp_port_to_local()" — DNAT-to-loopback does not deliver locally;
  tcpdump source-port capture is the workaround. · covered-by: HW.S13 · [H07]
- **HW.N065** ASSUME · `tests_hardware/bench_control.py:146-147` — "e.g. \"14:35:23.753510 IP
  192.168.85.57.55718 > 162.159.200.123.123: NTPv3, ...\"" — Parser relies on tcpdump -nn line format;
  example records bench DUT IP 192.168.85.57. (low) · related: HW.S19 · [H07]
- **HW.N066** RISK · `tests_hardware/bench_control.py:153-188` — "Real packet loss/latency/... via `tc netem`
  on `wifi_iface()` only (doesn't affect eth0/br0)" — Host qdisc left in place if pytest is killed;
  cleared only by test teardown. · covered-by: HW.T12 · [H07]
- **HW.N067** PLATFORM · `tests_hardware/bench_control.py:190-196` — "the bench Pi4 has a single WiFi
  radio"; "can't scan while still hosting an AP" — Bench-rig fact driving sequential role-reversal. ·
  related: HW.T07 · [H07]
- **HW.N068** SUPPRESS · `tests_hardware/bench_control.py:209-210, 243-244` — "except
  HardwareTestFailureError: pass # no leftover profile" — Swallows any nmcli failure of the delete, not
  just "not found". (low) · [H07]
- **HW.N069** ASSUME · `tests_hardware/bench_control.py:267-274` — `["iw", "dev", iface, "station", "dump"]`
  — Station dump runs without sudo while `station del` uses sudo. (low) · [H07]
- **HW.N070** WORKAROUND · `tests_hardware/bench_control.py:277-281` — "Best-effort settle delay ... the
  immediately-following wifi-connect call was found racy without this" — Fixed ≤2 s sleep for NM/kernel
  teardown race; removal: none stated. · covered-by: HW.S19 · [H07]

## tests_hardware/http_client.py

- **HW.N071** MIRROR · `tests_hardware/http_client.py:1-3` — "mirrors digital_twin/_http_client.py's
  `HttpResponse`/`fetch()` shape closely enough" — Oracle mirror between hardware and twin HTTP clients
  (sync vs async). · related: TEST.T17 · [H07]
- **HW.N072** ASSUME · `tests_hardware/http_client.py:22-24` — "every endpoint this tier talks to
  answers with a JSON object, never a bare array/scalar" — json() narrowing assumption. (low) · related:
  TEST.T17 · [H07]
- **HW.N073** ASSUME · `tests_hardware/http_client.py:46-49` — "the client sees FIN or RST depending on
  kernel TCP state (queue F10/F11 measured both)" — Ceiling-close shape is not chosen by src/; cites
  deleted queue rows from permanent code. · covered-by: DOC.S06 · [H07]
- **HW.N074** INVAR · `tests_hardware/http_client.py:52-54` — "An HTTPException, not an OSError, so a
  caller catching transport failures has to name it too" — Caller discipline. (low) · [H07]

## tests_hardware/error_log_helpers.py

- **HW.N075** ASSUME · `tests_hardware/error_log_helpers.py:11-74 (agent cited tests_hardware/error_log_helpers.py:71-74)`
  — "Above the server's own 15.0s outer_cap_s ... Measurements: BACKLOG item 24" —
  `_RESET_ERRORS_TIMEOUT_S = 30.0` basis: ResetErrors sweep cost over real WiFi. · related: PERF.T03 ·
  [H07] ⟨re-anchored: quote found at line 11⟩
- **HW.N076** RISK · `tests_hardware/error_log_helpers.py:1-63, 77-79 (agent cited tests_hardware/error_log_helpers.py:61-63, 77-79)`
  — "reset before a test, confirm a provoked fault produced the expected error/warning entry, then reset
  again" — `reset_all_error_logs()` clears FRAM-backed evidence with no snapshot first. · covered-by:
  HW.S06 · [H07] ⟨re-anchored: quote found at line 1⟩
- **HW.N077** ASSUME · `tests_hardware/error_log_helpers.py:32-94 (agent cited tests_hardware/error_log_helpers.py:89-94)`
  — "A routine fault is handled in place (SPECIFICATION.md C.7.2), so this stays empty" — SYSTEM log
  persists across hard_reset via FRAM; oracle assumes routine faults never end a task. · related: HW.T05
  · [H07] ⟨re-anchored: quote found at line 32⟩
- **HW.N078** DRIFT · `tests_hardware/error_log_helpers.py:78-140 (agent cited tests_hardware/error_log_helpers.py:137-140)`
  — "Every FRAM-backed module's counter, not one named module's" — Code compares every module present in
  errcount (RAM-only ones included). (low) · [H07] ⟨re-anchored: quote found at line 78⟩
- **HW.N079** MIRROR · `tests_hardware/error_log_helpers.py:128-129` — "Kind is \"E\" (err_s()) or \"W\"
  (wrn_s())" — History `type` vocabulary mirrors src/print_log. (low) · [H07] ⟨anchor out of bounds⟩

## tests_hardware/heap_map.py

- **HW.N080** PLATFORM · `tests_hardware/heap_map.py:1-3` — "The device cannot read it back - it goes to
  the platform print, not `sys.stdout`" — `mem_info(1)` output routing is a MicroPython fact the whole
  heap-map tier depends on. · [H07]
- **HW.N081** PLATFORM · `tests_hardware/heap_map.py:10-13` — "`gc_dump_alloc_table()` emits 64 blocks
  per line [SRC, py/gc.c] ... abbreviates two or more consecutive all-free lines. The block size is
  never printed" — Parser is bound to py/gc.c's dump format; re-check on a MicroPython bump. · [H07]
- **HW.N082** PLATFORM · `tests_hardware/heap_map.py:91-92` — "these metrics assume the single area the
  rp2 port builds" — Single-heap-area assumption, enforced by a raise. · [H07]
- **HW.N083** PLATFORM · `tests_hardware/heap_map.py:195-213` — "` No. of 1-blocks`" ... "max free sz" —
  `parse_allocation_need` depends on `mem_info()` summary wording. (low) · [H07]
- **HW.N084** INVAR · `tests_hardware/heap_map.py:59-62` — "a truncated capture ... would otherwise read
  as a heap with a huge free run at the end, which is exactly the direction that turns a real regression
  into a pass" — Fail-loud parsing, enforced (total-vs-map check :99-100). · [H07]
- **HW.N085** LIMIT · `tests_hardware/heap_map.py:137-140` — "a LOWER bound - a block occupied in both
  maps is not attributed, even if the first occupant was freed in between (MEASUREMENTS M2.1)" —
  HeapDelta under-counts placement. · [H07]
- **HW.N086** LIMIT · `tests_hardware/heap_map.py:162-170` — "Both must come from the same interpreter
  session ... which is why a mismatch raises" — Only heap geometry is checked; two same-sized maps from
  different sessions compare silently. (low) · [H07]
- **HW.N087** ASSUME · `tests_hardware/heap_map.py:41-44` — "it is the capacity that has to cover a
  simultaneous demand (HEAP_FRAGMENTATION_MEASUREMENTS.md archive §7R.2)" — Metric choice rests on an
  archived measurement section. (low) · [H07]
- **HW.N088** MIRROR · `tests_hardware/heap_map.py:192` — "_ALLOCATION_FAILED =
  re.compile(r\"MemoryError|memory allocation failed\")" — Separate copy of
  harness.MEMORY_ERROR_MARKERS, not reached by tests_scripts/test_memory_error_gate_agreement.py. ·
  related: TEST.T18 · [H07]

## tests_hardware/ntp_probe.py

- **HW.N089** MIRROR · `tests_hardware/ntp_probe.py:9` — "matches src/asy_ntp_client.py's own const of
  the same name" — Copied constant `_NTP_EPOCH_DELTA`. · [H07]
- **HW.N090** ASSUME · `tests_hardware/ntp_probe.py:12-14` — "the only fields src/asy_ntp_client.py's
  _parse_ntp_reply() actually reads" — Crafted reply (origin timestamp zero) is shaped to today's
  parser, so it cannot detect a parser that starts validating more. (low) · related: NET.T03 · [H07]

## tests_hardware/rogue_udp_responder.py

- **HW.N091** SUPPRESS · `tests_hardware/rogue_udp_responder.py:31-54 (agent cited tests_hardware/rogue_udp_responder.py:53-54)`
  — "pass # best-effort - a send failure here is not this responder's own test to report" — Swallowed
  send error. (low) · [H07] ⟨re-anchored: quote found at line 31⟩
- **HW.N092** LIMIT · `tests_hardware/rogue_udp_responder.py:2-26, 39 (agent cited tests_hardware/rogue_udp_responder.py:24-26, 39)`
  — "used by the NTP/DNS garbage-response tests via bench_control.BenchBridge's UDP-port-redirect
  helpers" — Binds 0.0.0.0 on the bench host; its DNAT-to-loopback delivery path is the documented gap.
  · covered-by: HW.S13 · [H07] ⟨re-anchored: quote found at line 2⟩

## tests_hardware/website_identity.py

- **HW.N093** DRIFT · `tests_hardware/website_identity.py:1-2` — "not merely non-empty (queue row G9)" —
  Cites a deleted queue row from permanent code. · covered-by: DOC.S06 · [H07]
- **HW.N094** SUPPRESS · `tests_hardware/website_identity.py:15-85 (agent cited tests_hardware/website_identity.py:84-85)`
  — "# noqa: E402 (the sys.path line above is what makes this importable)" — Two E402 suppressions (a
  `REPO_ROOT =` statement precedes the imports). (low) · [H07] ⟨re-anchored: quote found at line 15⟩
- **HW.N095** ASSUME · `tests_hardware/website_identity.py:26-96 (agent cited tests_hardware/website_identity.py:95-96)`
  — "The firmware serves index.html.gz, so the body is gzip whenever the server says so" —
  Content-Encoding keyed. (low) · [H07] ⟨re-anchored: quote found at line 26⟩
- **HW.N096** ASSUME · `tests_hardware/website_identity.py:57-127 (agent cited tests_hardware/website_identity.py:126-127)`
  — "dev is a superset of every other variant today, so no foreign errcount key exists to look for" —
  Discrimination relies on the device id alone while that superset holds. · [H07] ⟨re-anchored: quote
  found at line 57⟩
- **HW.N097** LIMIT · `tests_hardware/website_identity.py:2-72, 102-109 (agent cited tests_hardware/website_identity.py:70-72, 102-109)`
  — "Every expected name is derived from `devices/<device>.toml` through buildgen itself" — Oracle is
  computed from the TREE while the page comes from the IMAGE. · related: HW.T19 · [H07] ⟨re-anchored:
  quote found at line 2⟩

## tests_hardware/isl29125_conformance.py

- **HW.N098** LIMIT · `tests_hardware/isl29125_conformance.py:15-157 (agent cited tests_hardware/isl29125_conformance.py:144-157)`
  — "Keys whose value is a function of the actual light falling on the part ... only checked in a
  light-independent form" — Nine PHYSICAL_KEYS excluded from real-vs-mock diff. · related: TWIN.T01 ·
  [H07] ⟨re-anchored: quote found at line 15⟩
- **HW.N099** MIRROR · `tests_hardware/isl29125_conformance.py:40-171 (agent cited tests_hardware/isl29125_conformance.py:168-171)`
  — "Same location scripts/test.sh uses, and the same PICO_TOOLCHAIN_DIR override" — Hardcoded copy of
  the Unix-port path (`build-standard`). · [H07] ⟨re-anchored: quote found at line 40⟩
- **HW.N100** ASSUME · `tests_hardware/isl29125_conformance.py:193-195` — "-X\", \"heapsize=8M\"" with
  `TZ=UTC` and a local MICROPYPATH — Twin run uses its own heap size (test.sh uses 16M) and no
  GC-threshold stage. (low) · related: TEST.T18 · [H07] ⟨anchor out of bounds⟩
- **HW.N101** SUPPRESS · `tests_hardware/isl29125_conformance.py:65 (agent cited tests_hardware/isl29125_conformance.py:194)`
  — "# noqa: S603 - every argument is a repo-controlled path, no shell" — Subprocess lint suppression.
  (low) · [H07] ⟨re-anchored: quote found at line 65⟩

## tests_hardware/bench/dns_probe.py

- **HW.N102** SETTLED · `tests_hardware/bench/dns_probe.py:1-3` — "hand-rolled rather than pulling in
  dnspython, matching this project's preference for small hand-rolled protocol code" — Dependency
  policy. (low) · [H07]
- **HW.N103** ASSUME · `tests_hardware/bench/dns_probe.py:27-30` — "never raises, since \"no response\"
  is itself a real, assertable outcome (a malformed/off-subnet query should be silently dropped)" — Only
  a timeout maps to None; silence is treated as the expected captive-DNS behaviour. · related: HW.S13 ·
  [H07]
- **HW.N104** LIMIT · `tests_hardware/bench/dns_probe.py:42-45` — "src/captive_dns.py always answers
  with exactly one A record, so this doesn't handle the general multi-answer/multi-type case" — Oracle
  parser tied to one answer shape. · [H07]

## tests_hardware/bench/test_network_resilience.py

- **HW.N105** SETTLED · `tests_hardware/bench/test_network_resilience.py:1-3` — "DHCP-client flakiness
  is deliberately out of scope (see BACKLOG.md)" — Stated coverage exclusion. · [H07]
- **HW.N106** ASSUME · `tests_hardware/bench/test_network_resilience.py:30-34` — "that case takes the
  safe \"retry in 60s\" branch and never increments connection_failures or reaches hotspot fallback -
  read out of the source, not assumed" — Source-derived claim the outage tests are built on; pins
  current `_on_sta_disconnected()` behaviour. · related: NET.S01 · [H07]
- **HW.N107** SETTLED · `tests_hardware/bench/test_network_resilience.py:49-51, 62-68, 88-89` — "A
  fallback hard_reset() is a genuine pass per CLAUDE.md; the notes below record which ran" — CYW43
  associated-but-dead false positive: the outage/flap tests pass via hard reset, and then skip the
  WIFI-log check (:72-73, 110-111). · related: HW.T05 · [H07]
- **HW.N108** ASSUME · `tests_hardware/bench/test_network_resilience.py:41-44` — "a brief outage is a
  fully realistic, low-risk window to inject" — 15 s outage; 3×(3 s down/3 s up) flaps (:80); 150 s
  recovery wait. · [H07]
- **HW.N109** ASSUME · `tests_hardware/bench/test_network_resilience.py:114-117` — "wrnno=4 (cyw43's
  BADAUTH, also raised when the AP drops mid-handshake - BACKLOG item 29) ... the password never changes
  here, so 4 cannot be real" — Tolerated warnings 4/5 in the WIFI log. · related: DOC.S13 · [H07]
- **HW.N110** MIRROR · `tests_hardware/bench/test_network_resilience.py:120-122` — "\"N\" entries are
  print_log.py's own \"nothing recorded\" padding (get_log()'s own encoding)" — Oracle mirrors
  print_log's ring encoding. (low) · [H07]
- **HW.N111** ASSUME · `tests_hardware/bench/test_network_resilience.py:134-136, 144-146, 173-175` —
  "The parameter ranges come from researched real-world WiFi figures (tests_hardware/README.md)" — netem
  figures (30 %/150±50 ms, 2 %/30±20 ms, corrupt 5 %, dup 10 %/reorder 25 %) and "90s is generous"
  basis. · [H07]
- **HW.N112** LIMIT · `tests_hardware/bench/test_network_resilience.py:156-158, 205-207, 235-237` — "a
  brief passive window, purely for the crash check below" — Crash check greps only "Traceback" in a 5 s
  tail taken AFTER the fault cleared; nothing logged during the fault is seen; no MEMORY_ERROR_MARKERS.
  · related: TEST.T18 · [H07]
- **HW.N113** RISK · `tests_hardware/bench/test_network_resilience.py:169, 216, 246, 283, 325, 358, 415, 464, 592, 938, 975, 994`
  — "never leave a deliberately-provoked fault in the live error history" — Nearly every test resets
  errcount at start and end — deliberate, routine FRAM-evidence clearing with no snapshot. · covered-by:
  HW.S06 · [H07]
- **HW.N114** ASSUME · `tests_hardware/bench/test_network_resilience.py:220-222` — "checks whether a
  duplicate or late reply ever gets mismatched against a different, later pending request" — The test
  only asserts REST reachability, no Traceback and no task ended — narrower than the stated purpose. ·
  related: HW.T05 · [H07]
- **HW.N115** ASSUME · `tests_hardware/bench/test_network_resilience.py:251-253, 275, 279-281` — "the
  outage outlasts _NTP_CONN_TIMEOUT (5s) but clears inside the 15s retry" — Hardcoded 8 s block / 20 s
  wait mirror src NTP constants 5 s and 15 s. · related: NET.T03 · [H07]
- **HW.N116** ASSUME · `tests_hardware/bench/test_network_resilience.py:262-264` — "confirmed directly
  (NtpLastSyncAge showed sync completing only ~12s after dut_ip returned)" — Single observation behind
  the 30 s precondition wait. · [H07]
- **HW.N117** DRIFT · `tests_hardware/bench/test_network_resilience.py:270-272 vs 434-436, 514-516` —
  "PUT-ing NTP_Host back to its current value still fires post_asy_fct" vs "The PUT below is then
  reported \"Unchanged\" and fires no post_asy_fct" — Same file makes opposite claims about whether a
  same-value (Unchanged) PUT fires the post hook. · related: XCUT.T11 · [H07]
- **HW.N118** SUPPRESS · `tests_hardware/bench/test_network_resilience.py:249, 429, 508` —
  "@pytest.mark.persistence_write" — Three owned flash writes: NTP_Host re-PUT; garbage NTP_Host +
  restore; garbage SSID + restore. · covered-by: HW.T01 · [H07]
- **HW.N119** DRIFT · `tests_hardware/bench/test_network_resilience.py:287-289` —
  "redirect_udp_port_to_local(), which its own docstring marks unverified" — bench_control.py:116-119's
  docstring does not mark it unverified. (low) · related: HW.S13 · [H07]
- **HW.N120** ASSUME · `tests_hardware/bench/test_network_resilience.py:304, 324` — "generous relative
  to asy_ntp_client.py's own retry/backoff budget"; "past the ~60s the old NTP give-up needed" — 90 s
  tail basis refers to an older give-up behaviour. (low) · [H07]
- **HW.N121** INVAR · `tests_hardware/bench/test_network_resilience.py:311, 342` — "assert \"CFGMGR_\"
  in joined or \"FRAM\" in joined" — Loose "boot finished" oracle. · covered-by: HW.S15 · [H07]
- **HW.N122** ASSUME · `tests_hardware/bench/test_network_resilience.py:312-315` — "whose fixed 10-entry
  window a full 90s of garbage evicts ... \"Invalid NTP time received!\" ... (errno 14 or 15)" — Oracle
  bound to a src log string and a 10-entry history window. · [H07]
- **HW.N123** LIMIT · `tests_hardware/bench/test_network_resilience.py:351-355` — "a garbage reply fails
  the same sanity checks as no reply at all, so resolve_ipv4() exhausts every server and lands on
  \"NTP\" module's own errno=12" — DNS-garbage test cannot tell garbage from silence; no DNS-client log
  exists. · covered-by: HW.S13 · [H07]
- **HW.N124** LIMIT · `tests_hardware/bench/test_network_resilience.py:361-364` — "the garbage-response
  tests cannot reach: DNAT+conntrack rewrites the reply's source back first" — Garbage-response tests
  never exercise source filtering. · related: NET.S19 · [H07]
- **HW.N125** MIRROR · `tests_hardware/bench/test_network_resilience.py:367` — "safely inside
  _parse_ntp_reply()'s own 2025-2100 plausibility window" — Spoof date tied to src plausibility window;
  precondition 2020 < year < 2049 (:377). · related: NET.S19 · [H07]
- **HW.N126** RISK · `tests_hardware/bench/test_network_resilience.py:381-383` — "this bench's known
  ~1-in-3 reachability hiccup (BACKLOG.md open question 9) can land a hard_reset() in hotspot fallback
  instead" — Known bench flakiness retried 3×. · [H07]
- **HW.N127** ASSUME · `tests_hardware/bench/test_network_resilience.py:396-404` — "time.sleep(3.0) #
  generous relative to _parse_ntp_reply()'s own synchronous RTC().datetime() write" — Spoof pass
  condition (year != 2050) is also met if the DUT's socket already closed after the real reply — no
  evidence the spoof arrived while the socket was open. (low) · related: HW.T05 · [H07]
- **HW.N128** RISK · `tests_hardware/bench/test_network_resilience.py:434-437` — "An earlier run aborted
  before its own restore leaves the board already on the garbage value" — Persisted garbage NTP_Host can
  outlive an aborted run on the shared board. · related: HW.T03 · [H07]
- **HW.N129** ASSUME · `tests_hardware/bench/test_network_resilience.py:443-446` — "_VAL_NH bounds
  string length (3-1024) and nothing else" — Pins a validation gap (garbage host accepted "Valid"); same
  for `_VAL_SSID` (:499, 522-525). · related: NET.S17 · [H07]
- **HW.N130** LIMIT · `tests_hardware/bench/test_network_resilience.py:479-487` — "needing this fallback
  at all is worth a second look, not an expected outcome" — The hard_reset fallback path prints nothing,
  so its use is invisible in a passing run. · related: HW.T05 · [H07]
- **HW.N131** ASSUME · `tests_hardware/bench/test_network_resilience.py:498-501` — "It aims to finish
  inside the ~50s before hotspot fallback takes dut_ip away ... a recovery path is a pass" — Timing
  budget basis for the garbage-SSID test. · [H07]
- **HW.N132** MIRROR · `tests_hardware/bench/test_network_resilience.py:505` — "_HOTSPOT_PASSWORD =
  \"12345678\" # hardcoded in src/asy_wifi_service.py's _configure_hotspot_ap()" — Committed hotspot
  credential copy #2; its comment calls it hardcoded in `_configure_hotspot_ap()` while conftest.py:165
  calls it a `_VAL_HOTSPOT_PW` default declared by every devices/*.toml. · covered-by: HW.T11 · [H07]
- **HW.N133** RISK · `tests_hardware/bench/test_network_resilience.py:520-533` — "put_res = ...
  {\"SSID\": _GARBAGE_SSID}" followed by bare asserts on the tail log — The garbage-SSID PUT is
  persisted and the two tail-log asserts run before any restore, outside try/finally — a failure there
  strands the board off the bench network. · related: HW.T03 · [H07]
- **HW.N134** INVAR · `tests_hardware/bench/test_network_resilience.py:527-529` — "Passive observation
  only - no exec()/is_reachable(), which disturb a live system" — Caller discipline. · covered-by:
  HW.T06 · [H07]
- **HW.N135** ASSUME · `tests_hardware/bench/test_network_resilience.py:535-540` — "a reconnect is
  impossible by construction ... Not actually expected to trigger ..., kept only as a defensive
  fallback" — Happy-path branch is declared dead. (low) · [H07]
- **HW.N136** ASSUME · `tests_hardware/bench/test_network_resilience.py:585-588` — "matching this tier's
  established \"a recovery path counts as a pass\" convention" — Convention that recovery-by-reset
  passes. · related: HW.T05 · [H07]
- **HW.N137** MIRROR · `tests_hardware/bench/test_network_resilience.py:611-617` — "max_connections,
  three below lwIP's own MEMP_NUM_TCP_PCB"; "the build's own ceiling, never a restated literal" —
  Ceiling read from the TREE at import; stated relationship to versions.toml PCB count. · related:
  HW.T19 · [H07]
- **HW.N138** ASSUME · `tests_hardware/bench/test_network_resilience.py:630-633, 846-849, 1049, 1064, 1079`
  — "shifting every slot by one (confirmed directly)"; "a slot is released after _serve() awaits the
  close" — 1.0 s settle sleeps rest on the measured slot-release lag. · related: REST.T06 · [H07]
- **HW.N139** INVAR · `tests_hardware/bench/test_network_resilience.py:697-700, 773-776` — "a
  schema-rejected field is \"Invalid\" and never reaches write_config()"; "Unknown keys are ignored
  silently, so nothing validates, persists or logs" — Why these PUT tests carry no `persistence_write` —
  rests on src behaviour. · related: HW.T01 · [H07]
- **HW.N140** MIRROR · `tests_hardware/bench/test_network_resilience.py:813-752, 768-770 (agent cited tests_hardware/bench/test_network_resilience.py:750-752, 768-770)`
  — "_BODY_CAP = 2048"; "_OLD_CONTENT_CAP = 4096"; "_SCHEMA_MAX_BODY = 1312 ... derived in
  tests_scripts/ and asserted here" — Hardcoded copies of src/webserver caps and a derived schema
  maximum. · related: REST.T01 · [H07] ⟨re-anchored: quote found at line 813⟩
- **HW.N141** ASSUME · `tests_hardware/bench/test_network_resilience.py:789` — "microdot's
  Request.create() compares with <=, so the cap itself must still be served" — Relies on vendored
  microdot comparison. (low) · related: REST.T09 · [H07]
- **HW.N142** ASSUME · `tests_hardware/bench/test_network_resilience.py:800-807` — "The one check that
  can tell this firmware from the previous one" — A behaviour probe used as an image-identity proxy. ·
  related: HW.T19 · [H07]
- **HW.N143** INVAR · `tests_hardware/bench/test_network_resilience.py:819-824` — "ONE character over
  _VAL_NH's own 3..1024 bound ... an accepted NTP_Host is a flash write this test must not own" — Wear
  avoided by construction, depends on src's bound staying 1024. · related: HW.T01 · [H07]
- **HW.N144** DRIFT · `tests_hardware/bench/test_network_resilience.py:848, 890-891` — "Without it the
  workers start against 3 free slots, not 4"; "The 24 workers' slots" — Counts from an older ceiling;
  the worker list is 8 × max(3, _MAX_CONNECTIONS) and max_connections is 6 now. (low) · [H07]
- **HW.N145** DRIFT · `tests_hardware/bench/test_network_resilience.py:876-877` — "queue F10 measured
  ~25%" — Deleted queue row cited. · covered-by: DOC.S06 · [H07]
- **HW.N146** SUPPRESS · `tests_hardware/bench/test_network_resilience.py:861` — "except Exception as
  exc: # the worker's job is to report, never to raise into the harness" — Broad catch in worker threads
  (reported, not dropped). (low) · [H07]
- **HW.N147** MIRROR · `tests_hardware/bench/test_network_resilience.py:906-907` — "_VAL_POV only
  accepts _OSR_SETTINGS=(1,2,4,8,16,32)" — Oracle mirrors BMP3xx driver constant. (low) · [H07]
- **HW.N148** DRIFT · `tests_hardware/bench/test_network_resilience.py:929-930` — "A rejected key logs
  errno=12 on its own separate \"CFGMGR_<NAME>\" logger ... in-RAM only" — CLAUDE.md says every
  `CFGMGR_<name>` logger joined the FRAM-backed set under WP2. · related: HW.S23 · [H07]
- **HW.N149** MIRROR · `tests_hardware/bench/test_network_resilience.py:941-955` — "outer_cap_s=15.0";
  "per_call_timeout_s=5.0. One header line every 3s" — Slowloris pacing hardcodes src timeouts. ·
  related: REST.T06 · [H07]
- **HW.N150** SUPPRESS · `tests_hardware/bench/test_network_resilience.py:960-961` — "except OSError:
  pass # the server may have already closed the connection" — Swallowed with comment. (low) · [H07]
- **HW.N151** LIMIT · `tests_hardware/bench/test_network_resilience.py:987-993` — "would otherwise only
  surface as a slow, cumulative degradation over many such events"; "No hard assertion on WEBSERVER's
  error log ... a genuine timing race" — One abrupt disconnect cannot show a cumulative leak; wrnno=3
  left unasserted. · related: HW.T05 · [H07]
- **HW.N152** LIMIT · `tests_hardware/bench/test_network_resilience.py:997-1000` — "The only check in
  the repo that can confirm a raised lwIP MEMP_NUM_TCP_PCB really took effect on silicon - nothing in
  the twin can, it has no lwIP at all" — Twin fidelity gap; silicon-only evidence. · related: HW.T19 ·
  [H07]
- **HW.N153** ASSUME · `tests_hardware/bench/test_network_resilience.py:1008-1016` — "holding more means
  the image on the board is not the one this tree describes" — Tree-vs-image equality oracle. · related:
  HW.T19 · [H07]
- **HW.N154** ASSUME · `tests_hardware/bench/test_network_resilience.py:1060-1063` — "Complete and
  correct, not merely non-empty" — Checks status 200, a parseable dict with > 0 keys and < 30 s — not
  content correctness. (low) · related: HW.T05 · [H07]
- **HW.N155** ASSUME · `tests_hardware/bench/test_network_resilience.py:1081` — "2 connections per real
  page load, post-inlining" — Website request count assumption. (low) · related: PERF.T02 · [H07]

## tests_hardware/bench/test_hotspot_role_reversal.py

- **HW.N156** INVAR · `tests_hardware/bench/test_hotspot_role_reversal.py:1-3, 373-377` — "Definition
  order matters"; "MUST run after every read-only check above (pytest's default, non-randomized
  definition order)" — Stage-6 mutation safety depends on unrandomized test order — nothing enforces it.
  · related: HW.S10 · [H07]
- **HW.N157** SUPPRESS · `tests_hardware/bench/test_hotspot_role_reversal.py:24` — "pytestmark =
  pytest.mark.role_reversal" — Whole module is informational-marked, not gated: it runs in routine bench
  passes. · covered-by: HW.S25 · [H07]
- **HW.N158** WORKAROUND · `tests_hardware/bench/test_hotspot_role_reversal.py:27-41` —
  "`is_ssid_visible()`==True doesn't guarantee nmcli's own internal rescan still sees it a moment later,
  and this can persist across several attempts" — Up to 5 join retries; `except TimeoutError: pass`
  falls through; removal trigger: none stated. · [H07]
- **HW.N159** MIRROR · `tests_hardware/bench/test_hotspot_role_reversal.py:43` — "_HOTSPOT_PASSWORD =
  \"12345678\" # hardcoded in src/asy_wifi_service.py's _configure_hotspot_ap()" — Committed hotspot
  credential copy #3. · covered-by: HW.T11 · [H07]
- **HW.N160** SETTLED · `tests_hardware/bench/test_hotspot_role_reversal.py:59-61` — "Its own persisting
  writes stay UNMARKED per CLAUDE.md's owns-vs-reached-through rule: mark a test that spends a write,
  never this fixture" — SSID="" at stage 0 plus the stage-7 restore = two unmarked flash writes per
  module run. · covered-by: HW.T01 · [H07]
- **HW.N161** RISK · `tests_hardware/bench/test_hotspot_role_reversal.py:62-67, 73-89` — "the cleared
  SSID is persisted to flash, so no reset clears it. It happened on the bench (2026-09-17) and needed a
  manual serial-side repair" — Restore lives only in post-yield teardown; a failure in stages 1-2
  (before `yield`) leaves SSID="" persisted and the bench AP down. · covered-by: HW.S10 · [H07]
- **HW.N162** ASSUME · `tests_hardware/bench/test_hotspot_role_reversal.py:59-60` — "each join/leave
  costs a real ~15-30s association" — Timing basis for module scope. (low) · [H07]
- **HW.N163** SUPPRESS · `tests_hardware/bench/test_hotspot_role_reversal.py:91-102` — "Best-effort and
  never raising, so it cannot mask the failure unwinding this fixture" — A rejected/failed stage-7 SSID
  restore is only printed as "RESULT NOTE"; stage 8 reachability is the only loud check. · related:
  HW.S10 · [H07]
- **HW.N164** ASSUME · `tests_hardware/bench/test_hotspot_role_reversal.py:105-107, 113-116` — "A failed
  stage-6 STA reconnect ends in _PHASE_DEACTIVATED, which only a power cycle clears (Part A.4), so
  recover with hard_reset()" — Treats mpremote `reset` as equivalent to the power cycle Part A.4
  requires. · related: HW.T06 · [H07]
- **HW.N165** LIMIT · `tests_hardware/bench/test_hotspot_role_reversal.py:132-133, 136-140, 143-147, 155-156, 366-370, 417-421, 424-428`
  — "pass # the joined_hotspot fixture itself only succeeds if stage 0-2 all completed" — Seven tests
  assert nothing of their own (pass, constant==constant, non-empty) and count as passes. · covered-by:
  HW.S11 · [H07]
- **HW.N166** ASSUME · `tests_hardware/bench/test_hotspot_role_reversal.py:173-174` — "A /24 assumption
  (the common CYW43 AP DHCP range) ... tighten if this proves too loose" — Plausibility-only subnet
  check; stated follow-up. · [H07]
- **HW.N167** ASSUME · `tests_hardware/bench/test_hotspot_role_reversal.py:179-181` — "Fault injection
  against the CYW43 firmware's own DHCP server - there is no Python DHCP code here to test" — DHCP lives
  in CYW43 firmware. (low) · [H07]
- **HW.N168** ASSUME · `tests_hardware/bench/test_hotspot_role_reversal.py:202-203, 210-211, 221-222` —
  "src/captive_dns.py's response() returns None for this (confirmed by reading the module)" — Tests pin
  captive_dns behaviour read from source. · [H07]
- **HW.N169** SUPPRESS · `tests_hardware/bench/test_hotspot_role_reversal.py:232-241` — "Raw-socket
  feasibility on the bench Rpi4 not yet checked ... implement once a concrete spoofing mechanism is
  confirmed to work" — Unconditional `@pytest.mark.skip`: off-subnet DNS source spoofing is untested; a
  permanent skip in a routine bench run (skip whitelist, `_require_clean_hardware_run.sh`). · related:
  SCR.T05 · [H07]
- **HW.N170** LIMIT · `tests_hardware/bench/test_hotspot_role_reversal.py:244-247, 256-257` — "What it
  proves is robustness under flood and recovery after, not the backoff curve"; "the backoff cap is 5s" —
  Test name (`..._backoff_curve_recovers...`) claims more than it checks; 5 s cap mirrors captive_dns. ·
  related: HW.T05 · [H07]
- **HW.N171** RISK · `tests_hardware/bench/test_hotspot_role_reversal.py:274-281` — "PUT\",
  \"/notification\", {\"WarnCO2\": 1700}" — Owned flash write (marked) that is never restored: the board
  keeps WarnCO2=1700 afterwards. · related: HW.T03 · [H07]
- **HW.N172** ASSUME · `tests_hardware/bench/test_hotspot_role_reversal.py:320-322` — "A non-GET to an
  unmatched path resolves to 405 inside Microdot's routing, before _serve_static() is reached" — Relies
  on vendored microdot routing; hotspot↔STA toggle deliberately not repeated. (low) · related: REST.T07
  · [H07]
- **HW.N173** LIMIT · `tests_hardware/bench/test_hotspot_role_reversal.py:346-347` — "The exact response
  shape isn't asserted (mock/twin cover that)" — Stated coverage split. (low) · [H07]
- **HW.N174** LIMIT · `tests_hardware/bench/test_hotspot_role_reversal.py:366-370` — "a genuine
  concurrent multi-client burst ... isn't reproducible in hotspot mode with only one bench radio
  available" — Stated gap: no multi-client load test in AP mode. · [H07]
- **HW.N175** ASSUME · `tests_hardware/bench/test_hotspot_role_reversal.py:382-384` — "post_fct (the
  /networking group's reconnect_wifi() hook) fires if ANY field validates, so sending PW alone keeps
  `results` to one entry" — Pins post-hook semantics; the test is `persistence_write`-marked though its
  all-invalid PUT persists nothing. (low) · related: XCUT.T11 · [H07]
- **HW.N176** DRIFT · `tests_hardware/bench/test_hotspot_role_reversal.py:396-398` — "see
  tests_hardware/README.md for why this PUT is required (stage 7's flip-back depends on it)" — Stage 6
  is `persistence_write`-deselected by default, and the fixture now restores the SSID itself (:62-67,
  94-97). (low) · related: HW.S10 · [H07]
- **HW.N177** ASSUME · `tests_hardware/bench/test_hotspot_role_reversal.py:399` —
  "os.environ.get(\"BENCH_AP_PASSWORD\") or bench.ap_password()" — Run-time bench credential read (the
  HW.T11 convention); the bench PSK is then persisted in the DUT's flash config. · related: HW.T11 ·
  [H07]
- **HW.N178** OPENQ · `tests_hardware/bench/test_hotspot_role_reversal.py:425-427` — "adding one would
  be a src/ change to put to the owner rather than make unasked. The proxy: dut_ip being reachable at
  all means STA mode" — No `_conn_phase` field on GET; STA state only inferred. (low) · [H07]

## tests_hardware/bench/test_bus_concurrency_under_api_load.py

- **HW.N179** MIRROR · `tests_hardware/bench/test_bus_concurrency_under_api_load.py:19-21` — "VOC_MIN,
  VOC_MAX = 0, 500 # same bounds as device_scripts/sgp40_voc_algorithm_quality.py" — Plausibility bounds
  (CO2 200-10000 ppm, Pres 300-1250 hPa, VOC 0-500) copied across files. · [H07]
- **HW.N180** INVAR · `tests_hardware/bench/test_bus_concurrency_under_api_load.py:23-26` — "two slots
  under the build's own max_connections: at it, real wireless timing overlaps into an undesired
  reject-when-full" — Worker count derived from the TREE's ceiling (minus 3), not the image's. ·
  related: HW.T19 · [H07]
- **HW.N181** INVAR · `tests_hardware/bench/test_bus_concurrency_under_api_load.py:42-45` — "Same name
  and positional signature on purpose: tests_scripts/test_persistence_write_marker_completeness.py reads
  PUT bodies by AST and would silently lose a persisting write behind another shape (F15)" — The
  wear-marker guard only sees PUTs of a specific call shape; cites "F15". · related: HW.S05 · [H07]
- **HW.N182** SUPPRESS · `tests_hardware/bench/test_bus_concurrency_under_api_load.py:29-30, 46-55` —
  "retrying only a connection-ceiling refusal, never a transport failure"; "BACKLOG 30's resets share
  their signature" — Ceiling refusals are retried up to 3× and only printed (CEILING_RETRIES); an
  ISL29125 mechanism reset looks the same. · [H07]
- **HW.N183** LIMIT · `tests_hardware/bench/test_bus_concurrency_under_api_load.py:58-61` — "A value
  outside it is not a driver bug but a torn/corrupted read" — Torn-read oracle only catches
  out-of-schema values (MeasInt 2..1800, PressOvers set, Resolution 12/16, VOC 0..500 — hardcoded schema
  copies); an in-range torn read is invisible. · related: HW.T05 · [H07]
- **HW.N184** ASSUME · `tests_hardware/bench/test_bus_concurrency_under_api_load.py:104-112` —
  "{\"SGP40\": {\"SGPResetVOC\": True}}" — SGPResetVOC PUTs in unmarked tests (:81, :162, :311) are
  treated as dispatch-only (no persisting write). (low) · related: HW.T01 · [H07]
- **HW.N185** RISK · `tests_hardware/bench/test_bus_concurrency_under_api_load.py:124-126` — "A real
  WiFi reconnect blip (BACKLOG.md open question 6 ...) can land right after this heavy load ... a
  transient GET /status 500 that self-heals" — A transient 500 on /status after load is tolerated by a
  30 s wait. · related: REST.T06 · [H07]
- **HW.N186** LIMIT · `tests_hardware/bench/test_bus_concurrency_under_api_load.py:134-138` — "must all
  report nothing wrong" — Checked loggers are SCD30/BMP3XX/SGP40/ISL29125/FRAM only; the first test has
  no `assert_no_task_ended` and no WEBSERVER check. (low) · related: HW.T05 · [H07]
- **HW.N187** SUPPRESS · `tests_hardware/bench/test_bus_concurrency_under_api_load.py:172-181, 183-192, 252-272, 321-341`
  — "except Exception: continue" / "if res.status_code != 200: continue" — Compound-fault variants drop
  every failed request with no engagement floor — a run where no request succeeded still passes. ·
  related: HW.T05 · [H07]
- **HW.N188** SETTLED · `tests_hardware/bench/test_bus_concurrency_under_api_load.py:222-225, 304-307` —
  "Recombination test (owner's request)" — Owner-requested compound tests. · [H07]
- **HW.N189** SUPPRESS · `tests_hardware/bench/test_bus_concurrency_under_api_load.py:229, 398, 488` —
  "@pytest.mark.persistence_write" — Owned flash writes: NTP_Host re-PUT; 4 ISL29125 Resolution writes +
  restore; 4 BMP3XX PressOvers writes + restore. · covered-by: HW.T01 · [H07]
- **HW.N190** ASSUME · `tests_hardware/bench/test_bus_concurrency_under_api_load.py:276-277, 286-288, 295`
  — "post_asy_fct fires on ANY validated field, even one PUT back to its own current value"; "This join
  alone virtually guarantees it outlasts the 5s _NTP_CONN_TIMEOUT"; "15s _NTP_RETRY_INTERV" —
  Unchanged-PUT hook claim (see the DRIFT in test_network_resilience.py) and hardcoded NTP constants;
  outage length is not guaranteed. · related: XCUT.T11 · [H07]
- **HW.N191** SETTLED · `tests_hardware/bench/test_bus_concurrency_under_api_load.py:373-384` — "Same
  accepted real-pass pattern ... a hard_reset() fallback is a genuine recovery, not a failure" —
  Module-log checks skipped on the hard-reset path. · related: HW.T05 · [H07]
- **HW.N192** INVAR · `tests_hardware/bench/test_bus_concurrency_under_api_load.py:388-392, 480-482` —
  "per Part C.8's standing rule: every flash-tier bus hazard gets a bench-tier counterpart"; "flash-tier
  bus-hazard coverage is always a subset of bench-tier coverage" — Tier-parity rule, review-enforced. ·
  related: HW.T09 · [H07]
- **HW.N193** MIRROR · `tests_hardware/bench/test_bus_concurrency_under_api_load.py:394-395, 485, 521-523`
  — "(asy_isl29125_driver.py's own _RESOLUTIONS)"; "(asy_bmp3xx_driver.py's own _OSR_SETTINGS)";
  "PressOvers' driver default IS _BMP3XX_OVERSAMPLING_SETTINGS[0]" — Driver constants copied; 4 cycles
  vs flash tier's 8. (low) · [H07]
- **HW.N194** ASSUME · `tests_hardware/bench/test_bus_concurrency_under_api_load.py:431-432` — "an equal
  PUT reports \"Unchanged\" and _set_dict_cfg() pushes only \"Valid\" fields live, so it would reach no
  hardware" — Pins setter semantics. · related: XCUT.T11 · [H07]
- **HW.N195** DRIFT · `tests_hardware/bench/test_bus_concurrency_under_api_load.py:474-476` — "the
  driver registers no push callback at all - so no PUT can reach its NVM write" — Additional site of the
  structural-exception-1 claim the plan says is contradicted (SCD30 NVM reachable over REST). ·
  covered-by: HW.S02 · [H07]
- **HW.N196** SETTLED · `tests_hardware/bench/test_bus_concurrency_under_api_load.py:561-563` — "that is
  Part C.8's structural exception 2: the broadcast fires only from _reset() at setup. SGPResetVOC ...
  reaches a software-only reset instead" — Structural exception for the SGP40 general-call hazard. ·
  covered-by: HW.T09 · [H07]

## tests_hardware/bench/test_end_to_end_timing.py

- **HW.N197** LIMIT · `tests_hardware/bench/test_end_to_end_timing.py:19-22, 40-41` —
  "storage_pause()-then-wait genuinely completes before the real reset fires, WDT isn't starved
  mid-sequence" — The oracle is only "USB went away, then came back": a WDT reset and the intended
  `machine.reset()` look the same (no `reset_cause()` read). · related: HW.T05 · [H07]
- **HW.N198** RISK · `tests_hardware/bench/test_end_to_end_timing.py:26-28, 41` — "is_reachable()
  soft-resets the board's heap on every poll (raw-REPL entry Ctrl-D's first), wiping the very Timer this
  test waits on" — The post-reboot wait still polls `board.is_reachable`, which stops the freshly booted
  main.py; webserver recovery then depends on the WDT reset or the hard_reset fallback (:48-53). ·
  related: HW.T06 · [H07]
- **HW.N199** ASSUME · `tests_hardware/bench/test_end_to_end_timing.py:32-34, 37-39, 42-44` — "this is a
  genuine machine.reset() under the hood"; "not this test's to assume a specific value for"; "it starts
  only after ntp_force_sync() (up to ~20s)" — Reboot-path timing assumptions; 30 s waits. · [H07]
- **HW.N200** PLATFORM · `tests_hardware/bench/test_end_to_end_timing.py:57-58` — "the segfault this
  originally chased is confirmed compiled out of real rp2 firmware" — Claimed platform fact behind
  keeping the burst test as robustness-only. · related: PLAT.T06 · [H07]
- **HW.N201** DRIFT · `tests_hardware/bench/test_end_to_end_timing.py:85-88` — "The webserver must still
  answer afterwards" vs "assert board.is_device_present() or http_client.fetch(...) == 200" — The `or`
  short-circuits on USB presence, so the post-burst HTTP check never runs while the board is attached. ·
  related: HW.T05 · [H07]
- **HW.N202** ASSUME · `tests_hardware/bench/test_end_to_end_timing.py:63-66, 84` — "keeps serving at
  least the ceiling's own worth of requests" — Burst oracle ≥ tree ceiling successes out of 2× ceiling.
  · related: HW.T19 · [H07]
- **HW.N203** TODO · `tests_hardware/bench/test_end_to_end_timing.py:92-93, 105, 110` —
  "Reported/sanity-bounded, not asserted against a tight SLA - no measured baseline exists yet" —
  Cold-boot latency has no asserted threshold (120 s ceiling, printed only). · related: PERF.T01 · [H07]
- **HW.N204** SETTLED · `tests_hardware/bench/test_end_to_end_timing.py:120-123` — "Recombination test
  (owner's explicit request) ... The flash tier's reset race can only land as a write session begins" —
  Owner-requested; states the flash-tier race's reach limit. · [H07]
- **HW.N205** SUPPRESS · `tests_hardware/bench/test_end_to_end_timing.py:127, 134-139, 181-205` —
  "@pytest.mark.persistence_write"; "BackupPeriod=1 (minute) is the schema's fastest active cadence" —
  Owned flash writes: BackupPeriod=1 + restore; ≥3 hard resets land during production FRAM backups;
  restore checks only HTTP 200, not the result. · covered-by: HW.T01 · [H07]
- **HW.N206** LIMIT · `tests_hardware/bench/test_end_to_end_timing.py:143-145` — "can't be synchronized
  to the real SPI write itself from the host side" — No evidence any reset actually landed mid-write;
  checks SGP40/FRAM logs only (:168-169), not SYSTEM. · related: HW.T05 · [H07]
- **HW.N207** RISK · `tests_hardware/bench/test_end_to_end_timing.py:148-149` — "(see BACKLOG.md open
  question 9)" — Known intermittent unreachability after a hard reset, retried once. · [H07]

## tests_hardware/bench/test_heap_under_connection_ceiling.py

- **HW.N208** MIRROR · `tests_hardware/bench/test_heap_under_connection_ceiling.py:22-25` — "microdot
  reads one only when Content-Length > 0, up to max_content_length (2048), contiguously" —
  Per-connection demand hardcoded to src's body cap. · related: MEM.T03 · [H07]
- **HW.N209** MIRROR · `tests_hardware/bench/test_heap_under_connection_ceiling.py:26-27` — "The
  script's own window is 90s and it prints READY about 20s in" — Timing coupled to
  device_scripts/heap_under_connection_ceiling.py. (low) · [H07]
- **HW.N210** ASSUME · `tests_hardware/bench/test_heap_under_connection_ceiling.py:28-30` — "measured on
  silicon at 5.12-5.16s plain, 15.1s dripping (SPECIFICATION.md Part H.7.1)" — Single measurement behind
  drip 2 s / recycle 10 s constants. · related: REST.T06 · [H07]
- **HW.N211** ASSUME · `tests_hardware/bench/test_heap_under_connection_ceiling.py:35-40` —
  "_MIN_FRACTION_AT_CEILING = 0.55"; "A refusal is a FIN ~6 ms after connect" — Peak-reading threshold
  and 0.3 s admission wait, from measurement. · [H07]
- **HW.N212** INVAR · `tests_hardware/bench/test_heap_under_connection_ceiling.py:105-106, 122-127` — "a
  worker that outlives its test hammers the board for the rest of the pytest session, which took down 37
  unrelated tests once" — Holder-thread teardown obligation, asserted in-test. · [H07]
- **HW.N213** LIMIT · `tests_hardware/bench/test_heap_under_connection_ceiling.py:88-91, 121` — "the
  script's own boot, not main.py's" — Heap is measured with `sensortask_dev.main()` started by a device
  script under run_isolated (production boot plus a sampler in the same process), not a natural power-on
  boot. · related: HW.T05 · [H07]
- **HW.N214** LIMIT · `tests_hardware/bench/test_heap_under_connection_ceiling.py:151-156` — "A floor on
  the absolute bytes would be a guess; this is the actual requirement" — Only placeability of `ceiling`
  × 2048 B is asserted. · [H07]
- **HW.N215** SUPPRESS · `tests_hardware/bench/test_heap_under_connection_ceiling.py:159-172` —
  "@pytest.mark.over_provisioned_image" — Informational marker; runs on every image and `pytest.fail`s
  only when fewer than configured are admitted. · covered-by: HW.S25 · [H07]
- **HW.N216** DRIFT · `tests_hardware/bench/test_heap_under_connection_ceiling.py:161-163, 171` — "Row 5
  of the decision table, and the reason §5 needs only two images"; "use §6's LWIP_STATS image" — Named
  citations into HEAP_FRAGMENTATION_MEASUREMENTS.md sections without a file name. · covered-by: DOC.S05
  · [H07]

## tests_hardware/bench/test_memory_stress_bench.py

- **HW.N217** DRIFT · `tests_hardware/bench/test_memory_stress_bench.py:19-22` — "WIFI/NTP/every
  CFGMGR_* logger are RAM-only" — `_FRAM_BACKED_MODULES` omits WIFI, NTP, WEBSERVER, DNSSRV, CFGMGR_*,
  UART_* against CLAUDE.md's list. · covered-by: HW.S23 · [H07]
- **HW.N218** DRIFT · `tests_hardware/bench/test_memory_stress_bench.py:24-30` — "4 GET threads at true
  max speed" — Thread count is now `configured_max_connections()` (6). (low) · [H07]
- **HW.N219** ASSUME · `tests_hardware/bench/test_memory_stress_bench.py:24-27` — "reproduces the
  request density that originally found real MemoryErrors within 45s. Not soak-tier gated - 120s needs
  no --soak-tier flag to run" — A 120 s max-speed hammer runs in every routine bench pass; basis is one
  historical finding. · [H07]
- **HW.N220** LIMIT · `tests_hardware/bench/test_memory_stress_bench.py:53-55` — "ConnectionResetError
  is the server's intended reject-when-full behavior, not a fault - not asserted against" — All non-200
  outcomes are collected but never asserted. · [H07]
- **HW.N221** ASSUME · `tests_hardware/bench/test_memory_stress_bench.py:107, 127, 174` — "assert
  success_count > 100"; "assert len(request_errors) < 5" — Liveness/error thresholds with no stated
  basis (the < 5 applies to runs up to 6 h). · related: HW.S14 · [H07]
- **HW.N222** MIRROR · `tests_hardware/bench/test_memory_stress_bench.py:91-95, 168-171` — "\"config is
  ready\"/\"FRAM SPI FRAM Driver Setup complete\" are the genuinely one-time-per-setup() completion
  lines" — Reboot detection depends on src log strings (and their DebugLevel). · covered-by: HW.S14 ·
  [H07]
- **HW.N223** RISK · `tests_hardware/bench/test_memory_stress_bench.py:101, 108, 120, 132` —
  "reset_all_error_logs(dut_ip)" — Resets at start of both hammer tests, before any snapshot. ·
  covered-by: HW.S06 · [H07]
- **HW.N224** ASSUME · `tests_hardware/bench/test_memory_stress_bench.py:113-115, 118` — "--soak-tier
  mid = 600s, matching the one real WDT_RESET this project has observed" — Soak duration chosen from a
  single event. · [H07]
- **HW.N225** SETTLED · `tests_hardware/bench/test_memory_stress_bench.py:129-131` — "Deliberately only
  cleared AFTER the assertions above have already captured/reported whatever FRAM-backed history existed
  ... per this file's own new standing rule" — Evidence-before-clear rule applied only at the end of
  this one test. · related: HW.T02 · [H07]
- **HW.N226** LIMIT · `tests_hardware/bench/test_memory_stress_bench.py:135-174` —
  "test_real_hardware_memory_does_not_leak_under_real_http_soak_traffic" — "Does not leak" is asserted
  only as no crash/reboot marker and < 5 errors — no heap trend. · covered-by: HW.S14 · [H07]
- **HW.N227** DRIFT · `tests_hardware/bench/test_memory_stress_bench.py:156` — "a modest, sustained
  request rate - not a flood (that's item 17's job)" — Dangling "item 17" reference. (low) · [H07]
- **HW.N228** SUPPRESS · `tests_hardware/bench/test_memory_stress_bench.py:111, 116-118, 135, 137-139` —
  "pytest.skip(\"real extended max-speed hammer load - run via scripts/run_bench_soak_tests.sh --tier
  mid ...\")" — Two `long_soak` in-test skips. · covered-by: HW.T13 · [H07]

## tests_hardware/bench/test_rest_endpoints_over_sta.py

- **HW.N229** DRIFT · `tests_hardware/bench/test_rest_endpoints_over_sta.py:34-35` — "(queue row G9)" —
  Deleted queue row cited. · covered-by: DOC.S06 · [H07]
- **HW.N230** MIRROR · `tests_hardware/bench/test_rest_endpoints_over_sta.py:1-3, 18-24` — "Bounds
  mirror the flash-tier isolated-driver plausibility scripts' own datasheet-sourced bounds" — Copied
  bounds; CO2 floor here is 400 ppm vs 200 ppm in test_bus_concurrency_under_api_load.py:19. (low) ·
  [H07]
- **HW.N231** LIMIT · `tests_hardware/bench/test_rest_endpoints_over_sta.py:50-51` — "for name in
  (\"SCD30\", \"BMP3XX\", \"SGP40\")" — ISL29125 (dev-only) values are not checked over REST. (low) ·
  [H07]
- **HW.N232** SETTLED · `tests_hardware/bench/test_rest_endpoints_over_sta.py:102-104` — "the window is
  a fixed 300s and the duration is never client-suppliable, so no REST unpause exists ... the pause is
  RAM-only" — Pins mempause semantics; recovery by hard reset. · related: STOR.T05 · [H07]
- **HW.N233** RISK · `tests_hardware/bench/test_rest_endpoints_over_sta.py:93` — "a previous test left
  the bench in a paused state" — Cross-test state leakage precondition. (low) · [H07]
- **HW.N234** SUPPRESS · `tests_hardware/bench/test_rest_endpoints_over_sta.py:124-128` — "this test
  OWNS its persisting writes (the probe PUT and the restore PUT), unlike the dispatch-only ISLCalibrate
  push, which stores nothing" — Two owned flash writes; ISLCalibrate asserted dispatch-only. ·
  covered-by: HW.T01 · [H07]
- **HW.N235** MIRROR · `tests_hardware/bench/test_rest_endpoints_over_sta.py:118-120, 134-136` —
  "GainRatio is ordinary user-PUT config now, not a self-learned runtime value"; "Inside the driver's
  own [20, 34] band" — Classification decision and driver band copied. (low) · [H07]

## tests_hardware/bench/test_sensor_config_push_over_real_hardware.py

- **HW.N236** MIRROR · `tests_hardware/bench/test_sensor_config_push_over_real_hardware.py:17-20, 25-27`
  — "Different from every driver default (PressOvers=1, TempOvers=1, FiltCoeff=0)"; "Of its ten config
  fields only these four are hardware-backed with a real get-back path" — Driver defaults, discrete
  settings and ISL29125 field classification copied into the test. · [H07]
- **HW.N237** DRIFT · `tests_hardware/bench/test_sensor_config_push_over_real_hardware.py:22-23` —
  "SCD30 has no live-push config fields at all (asy_scd30_driver.py registers no _push_callbacks)" —
  Contradicted by the SCD30 REST dispatch path per the plan. · covered-by: HW.S02 · [H07]
- **HW.N238** ASSUME · `tests_hardware/bench/test_sensor_config_push_over_real_hardware.py:29-31` —
  "under auto-range the chip's range bit is the state machine's pick, not the user's, so
  _read_sensor_dict() omits Range from a live snapshot entirely" — Pins ISL29125 read-back behaviour;
  test forces RangeAuto False. (low) · [H07]
- **HW.N239** RISK · `tests_hardware/bench/test_sensor_config_push_over_real_hardware.py:41-45, 81-85` —
  "An earlier run aborted before its own restore leaves the board already holding a test value" —
  Persisted test values can outlive an aborted run; the test refuses to run rather than repairing. ·
  related: HW.T03 · [H07]
- **HW.N240** SUPPRESS · `tests_hardware/bench/test_sensor_config_push_over_real_hardware.py:35, 75` —
  "@pytest.mark.persistence_write" — Owned flash writes: BMP3XX 3-field push + restore; ISL29125 5-field
  push + restore (plus live register writes). · covered-by: HW.T01 · [H07]
- **HW.N241** ASSUME · `tests_hardware/bench/test_sensor_config_push_over_real_hardware.py:69-70` —
  "config_manager.py's errno=12 only fires on a rejected key" — Oracle for an empty CFGMGR log. (low) ·
  [H07]
- **HW.N242** ASSUME · `tests_hardware/bench/test_sensor_config_push_over_real_hardware.py:116-118, 131, 146-147`
  — "PauseTime is dispatch-only"; "real ~1s-per-tick auto_led_override() cadence"; "SGPResetVOC is
  command-only (never persisted - see asy_sgp40_driver.py's _VAL_RESET comment)" — Why these PUTs carry
  no `persistence_write` marker. · related: HW.T01 · [H07]
- **HW.N243** LIMIT · `tests_hardware/bench/test_sensor_config_push_over_real_hardware.py:153-157` —
  "The sensor must still be alive and producing real readings afterward" — Only a 200 on /measurements
  and an empty SGP40 log are checked, no reading values. (low) · related: HW.T05 · [H07]
- **HW.N244** LIMIT · `tests_hardware/bench/test_sensor_config_push_over_real_hardware.py:175-187` —
  "Its PRESENCE is the contract, not its value - a run that finds no usable scene legitimately leaves it
  null, and the bench light is not arranged" — ISL29125 calibration is not validated on silicon; only
  "applied ratio unchanged" and "GainMeas key present". · [H07]

## tests_hardware/bench/test_serving_heap_at_default_gc.py

- **HW.N245** MIRROR · `tests_hardware/bench/test_serving_heap_at_default_gc.py:25-31` — "under the
  device script's own 10 s quiet-to-leave"; "the device starts dumping 20 s into its own boot" — Host
  timings coupled to device_scripts/serving_at_default_gc.py. (low) · [H07]
- **HW.N246** ASSUME · `tests_hardware/bench/test_serving_heap_at_default_gc.py:32-35` — "Fixed, the
  worst route needs 320-336 B (board and 32-bit twin); pre-fix needs were 512-1,536 B ... the measured
  rung cannot flip the verdict" — `_MAX_ROUTE_NEED = 480` rests on one measurement set (SPECIFICATION
  Part I.3). · related: MEM.T06 · [H07]
- **HW.N247** INVAR · `tests_hardware/bench/test_serving_heap_at_default_gc.py:39-40` — "body DRAINED
  rather than materialised - the drain rule, so the host measures the board and never its own buffering"
  — Measurement discipline shared with the twin HTTP client test. (low) · [H07]
- **HW.N248** INVAR · `tests_hardware/bench/test_serving_heap_at_default_gc.py:84-85, 131-134` — "`stop`
  guarantees it cannot outlive its test - a driver that did took 37 tests down once" — Load-driver
  teardown obligation, asserted in-test. · [H07]
- **HW.N249** LIMIT · `tests_hardware/bench/test_serving_heap_at_default_gc.py:1-3, 101-110, 130` —
  "Serving at MicroPython's own gc default"; "Both tests stop main.py" — Numbers come from device-script
  builds under run_isolated (not the production boot) at the reactive gc default, not the firmware's
  32768 threshold. · related: HW.T05 · [H07]
- **HW.N250** ASSUME · `tests_hardware/bench/test_serving_heap_at_default_gc.py:146-150` — "expected
  {admitted} served, the rest refused cleanly" — Exact `served == min(n, ceiling) × rounds` oracle uses
  the TREE's ceiling. (low) · related: HW.T19 · [H07]

## tests_hardware/bench/test_uart_link_under_api_load.py

- **HW.N251** MIRROR · `tests_hardware/bench/test_uart_link_under_api_load.py:20-21` —
  "asy_uart_link_driver.UartLinkExerciser's own name_ext=\"init\"/\"resp\" -> instance_name()
  resolution" — Hardcoded logger names mirror devices/dev.toml + buildgen catalog. · [H07]
- **HW.N252** INVAR · `tests_hardware/bench/test_uart_link_under_api_load.py:22-23` — "A PUT belongs in
  this tier only where it is documented command-only and never persisted" — Wear rule for this file, by
  convention. (low) · related: HW.T01 · [H07]
- **HW.N253** SUPPRESS · `tests_hardware/bench/test_uart_link_under_api_load.py:39-43, 51-57` — "Absent
  entries are therefore a build to check, not a protocol failure" — A firmware that drops UARTLINK or
  the UART loggers turns into skips, not failures. · related: HW.T13 · [H07]
- **HW.N254** LIMIT · `tests_hardware/bench/test_uart_link_under_api_load.py:31-34, 111-114` — "an idle
  link and a healthy one both leave that at zero"; "Its two neighbours assert the link logged no errors,
  which an idle link satisfies too" — Tests 1 and 3 pass on an idle link; only test 2 checks transfers.
  · related: HW.T05 · [H07]
- **HW.N255** DRIFT · `tests_hardware/bench/test_uart_link_under_api_load.py:143-150` — "The link must
  have progressed *during* the hammering" — The transfer check polls up to 30 s AFTER the load window,
  so a post-load transfer also passes. (low) · related: HW.T05 · [H07]
- **HW.N256** MIRROR · `tests_hardware/bench/test_uart_link_under_api_load.py:143-144` — "One exerciser
  period is 1s" — Exerciser period copied from src. (low) · [H07]
- **HW.N257** DRIFT · `tests_hardware/bench/test_uart_link_under_api_load.py:160-162, 177` — "a burst
  past the server's comfortable concurrency" vs "range(6)" — Hardcoded 6 now equals max_connections (6),
  so the burst no longer exceeds the ceiling. (low) · [H07]
- **HW.N258** SUPPRESS · `tests_hardware/bench/test_uart_link_under_api_load.py:172-173` — "except
  Exception: # a rejected connection under a deliberate overload is an accepted outcome" — Every
  exception accepted; floor is "at least one 200". (low) · [H07]

## tests_hardware/bench/test_wifi_networking.py

- **HW.N259** RISK · `tests_hardware/bench/test_wifi_networking.py:30-32` — "measured 2026-09-19: 1 miss
  in 3 full suite runs, 12/12 clean in isolation, CYW43 reporting status -1 after the firmware's own two
  retries ... queue F13" — Known STA association flakiness tolerated by a second cold boot; cites a
  deleted queue row. · covered-by: DOC.S06 · [H07]
- **HW.N260** LIMIT · `tests_hardware/bench/test_wifi_networking.py:54-59` — "assert \"NTP\" in joined"
  — "Real NTP round-trip" is inferred from any NTP log line plus absence of fail/error/timeout words in
  an arbitrary 60 s window; no sync is provoked. · related: HW.T05 · [H07]
- **HW.N261** LIMIT · `tests_hardware/bench/test_wifi_networking.py:67-70` — "observed DNS failure/error
  log lines during a window with no fault injected" — DNS test only asserts absence of failure lines —
  passes when no DNS activity is logged at all. · related: HW.T05 · [H07]
- **HW.N262** INVAR · `tests_hardware/bench/test_wifi_networking.py:97` — "assert \"CFGMGR_\" in joined
  or \"FRAM\" in joined" — Loose boot-finished oracle (additional site). · covered-by: HW.S15 · [H07]
- **HW.N263** ASSUME · `tests_hardware/bench/test_wifi_networking.py:108-112` — "errno 21 (no reply) is
  logged and the task backs off in place"; "Task ended - attempting restart" — Pins NTP errno and a
  supervisor log string. · related: XCUT.T07 · [H07]
- **HW.N264** DRIFT · `tests_hardware/bench/test_wifi_networking.py:16-18, 80` — "Item 7 - real STA
  connect/disconnect"; "BACKLOG open question 6" — Unanchored "Item 7" numbering. (low) · [H07]

## tests_hardware/flash/test_bus_concurrency.py

- **HW.N265** SUPPRESS · `tests_hardware/flash/test_bus_concurrency.py:23, 31, 38, 44, 68, 76, 85-86` —
  "@pytest.mark.persistence_write" / "@pytest.mark.scd30_extra_write" — Seven SCD30-fixture dependents
  gated (one NVM write per session), plus the AND-gated second SCD30 NVM write at :85-92. · covered-by:
  HW.T13 · [H07]
- **HW.N266** LIMIT · `tests_hardware/flash/test_bus_concurrency.py:23-28` — "This test exists only to
  give that one real NVM write its own named, first-to-run pass/fail surface" — Body is `pass`;
  first-to-run relies on definition order. (low) · related: HW.T05 · [H07]
- **HW.N267** ASSUME · `tests_hardware/flash/test_bus_concurrency.py:33-34` — "Generous relative to the
  device script's own ~90s internal asyncio.wait_for budget" — Script runs ~90 s under run_isolated's 8
  s WDT, so it must feed the WDT itself. · related: HW.S09 · [H07]
- **HW.N268** PLATFORM · `tests_hardware/flash/test_bus_concurrency.py:53-55, 61-63, 80` — "BMP3xx's own
  config registers are volatile"; "FN8424 p7 calls the ISL29125's config registers volatile outright";
  "the DESTRUCTIVE 0x08 status read" — Datasheet facts behind leaving these write tests unmarked. ·
  related: HW.T01 · [H07]
- **HW.N269** ASSUME · `tests_hardware/flash/test_bus_concurrency.py:104-106` — "this sweep only ever
  *reads* SCD30 ... its self-hazard branch doesn't need continuous measurement" — Sweep's claims rest on
  the device script (whose probes the plan says cannot fail). · covered-by: HW.S12 · [H07]
- **HW.N270** PLATFORM · `tests_hardware/flash/test_bus_concurrency.py:111-114` — "FRAM's real datasheet
  endurance is 10^13 read/write operations per byte" — Endurance figure for MB85RS2MTA; the plan notes
  10^12 for MB85RS64V — which part dev has is open. · related: HW.T07 · [H07]
- **HW.N271** DRIFT · `tests_hardware/flash/test_bus_concurrency.py:120-122` — "(BACKLOG.md open
  question 8's \"not currently provisioned\" GPIO harness doesn't apply here)" — Quotes a BACKLOG item
  as unsettled. · covered-by: DOC.S05 · [H07]
- **HW.N272** RISK · `tests_hardware/flash/test_bus_concurrency.py:127-137` — "Real hardware-reset race
  against an in-flight FRAM write"; "there is no live system to protect here" — Reset-raced write
  against production's own FRAM chunks; the seed script's outcome is ignored
  (run_isolated_expect_reset). · covered-by: HW.T17 · [H07]

## tests_hardware/flash/test_bus_electrical_timing.py

- **HW.N273** LIMIT · `tests_hardware/flash/test_bus_electrical_timing.py:52-54` — "can't fully
  disambiguate a genuine hardware edge from the fallback purely in software (a scope on the pin would be
  the only certain check)" — SCD30 IRQ-edge test cannot prove the edge path. · related: HW.T05 · [H07]
- **HW.N274** PLATFORM · `tests_hardware/flash/test_bus_electrical_timing.py:76-79` — "the ~150ms
  stretch happens roughly once a day for internal calibration (Interface Description p.2, cited in
  tests/_sensortask_scenarios.py too)" — Datasheet fact mirrored in the unit tier. · [H07]
- **HW.N275** LIMIT · `tests_hardware/flash/test_bus_electrical_timing.py:87-93` — "a \"never observed
  to fail\" soak, not \"confirmed exercised\" (only the \"long\" tier runs long enough to likely observe
  the ~once/day event)" — A 6 h "long" tier for a ~once/day event; string-match oracle. · covered-by:
  HW.S14 · [H07]
- **HW.N276** SUPPRESS · `tests_hardware/flash/test_bus_electrical_timing.py:82-86, 110-116` —
  "pytest.skip(\"real SCD30 clock-stretch events are opportunistic ...\")"; "pytest.skip(\"real
  ~12.4-day wait ...\")" — `long_soak` and `multi_day_rollover` in-test skips. · covered-by: HW.T13 ·
  [H07]
- **HW.N277** TODO · `tests_hardware/flash/test_bus_electrical_timing.py:96-101, 131-138` — "Expect this
  to be the outcome as long as this test polls with board.exec() ... that redesign is tracked in
  REAL_HARDWARE_TEST_QUEUE.md, not worked around here" — The gated ticks_ms rollover test is known to
  fail by construction (each `exec` starves the WDT and zeroes the counter). · related: HW.T13 · [H07]
- **HW.N278** ASSUME · `tests_hardware/flash/test_bus_electrical_timing.py:104-107, 122` — "Two hours of
  headroom, wider than the poll interval below" — `_WRAP_FLOOR_MS` and 3600 s polling. (low) · [H07]
- **HW.N279** DRIFT · `tests_hardware/flash/test_bus_electrical_timing.py:30, 41, 52, 65, 76, 97` —
  "Item 2 - soft Timer callback drop ..." — Unanchored "Item N" numbering. (low) · [H07]

## tests_hardware/flash/test_fram_storage.py

- **HW.N280** DRIFT · `tests_hardware/flash/test_fram_storage.py:1` — "real MB85RS64V SPI FRAM chip
  coverage" — Device scripts and dev_legacy name MB85RS2MTA. · covered-by: HW.S17 · [H07]
- **HW.N281** ASSUME · `tests_hardware/flash/test_fram_storage.py:42-43` — "~90s real runtime (60s to
  the first natural BackupPeriod trigger, plus restore-cycle margin)" — 150 s timeout basis. (low) ·
  [H07]
- **HW.N282** LIMIT · `tests_hardware/flash/test_fram_storage.py:57-58` — "simulates a fresh boot in the
  SAME process and so only ever shows the happy path" — fram_error_log_roundtrip.py's reboot is
  simulated, not real. · [H07]
- **HW.N283** SETTLED · `tests_hardware/flash/test_fram_storage.py:77-82` — "Reads being gated too is
  intended (Part A.4's FRAM entry)"; "Flash-only, no bench counterpart, structurally (E.6.6 exception
  2): get_write_protected()/set_write_protected() have no REST route at all" — Structural-exception
  claim for FRAM write-protect. · covered-by: HW.T09 · [H07]
- **HW.N284** PLATFORM · `tests_hardware/flash/test_fram_storage.py:91-93, 98-100` — "the ONE_SHOT
  auto-unpause really fires on an rp2 alarm pool"; "the 2s/2s/6s auto-unpause windows plus margins, and
  the exhausted-alarm-pool step's own window" — Hardware-only timer claims. (low) · related: PLAT.T03 ·
  [H07]
- **HW.N285** LIMIT · `tests_hardware/flash/test_fram_storage.py:105-108` — "The overrun is a DMA timing
  condition no Python knob can induce on target, so this tests its consequence" — SPI RX-overrun itself
  is untested on silicon. · related: PLAT.T03 · [H07]
- **HW.N286** SETTLED · `tests_hardware/flash/test_fram_storage.py:116-118` — "mpremote-only by design
  (owner's own decision) - no new /status field, this is a one-time build-validity fact" — FRAM capacity
  check is not surfaced at runtime. · [H07]

## tests_hardware/flash/test_memory_stress.py

- **HW.N287** SETTLED · `tests_hardware/flash/test_memory_stress.py:22-28` — "That worst case fell to
  2,048 B once both caps were bound ... Not re-derived on purpose: these are a regression tripwire with
  margin" — `WORST_CASE_ALLOCATION = 16_384` deliberately kept above the current 2048 B worst case
  (MEASUREMENTS M2.5). · related: MEM.T06 · [H07]
- **HW.N288** PLATFORM · `tests_hardware/flash/test_memory_stress.py:32-34` — "real 264KB SRAM minus the
  firmware's own static footprint" — Heap figure is silicon- and image-specific; measured inside a
  device-script build (run_isolated), not the production boot. · related: HW.T16 · [H07]
- **HW.N289** ASSUME · `tests_hardware/flash/test_memory_stress.py:49-57` — "the probe's own pinning
  artefact looks exactly like this (MEASUREMENTS M2.2), and it always understates"; "a power-of-two
  fraction of 192 KB is the known artefact" — ±2-block tolerance between probe and map rests on a
  recorded artefact. · [H07]
- **HW.N290** ASSUME · `tests_hardware/flash/test_memory_stress.py:64-66` — "Zero, not a budget - 17
  twin runs across 41-58% fill, perturbed, never placed one (MEASUREMENTS M2.1)" — Silicon threshold
  justified by twin runs. · related: HW.T16 · [H07]
- **HW.N291** SUPPRESS · `tests_hardware/flash/test_memory_stress.py:86-90` — "pytest.skip(\"passive
  soak, one of three named duration tiers ...\")" — `long_soak` in-test skip. · covered-by: HW.T13 ·
  [H07]
- **HW.N292** LIMIT · `tests_hardware/flash/test_memory_stress.py:86-105` —
  "test_single_core_timing_headroom_holds_under_normal_full_task_load"; "use the two genuinely
  one-time-per-setup() ConfigManager/FRAM messages instead" — "Timing headroom" is asserted only as no
  reboot/traceback markers (DebugLevel-dependent strings); no timing is measured. · covered-by: HW.S14 ·
  [H07]

## tests_hardware/flash/test_reboot_persistence.py

- **HW.N293** DRIFT · `tests_hardware/flash/test_reboot_persistence.py:1-3` — "mpremote's DTR-based
  reset, the closest real equivalent to a power-cycle without pulling power" — hard_reset described as
  DTR. · covered-by: HW.S17 · [H07]
- **HW.N294** DRIFT · `tests_hardware/flash/test_reboot_persistence.py:25` — "Item 13 - config.json (a
  real ConfigManager-backed file) survives a genuine reboot" — The refactor persists
  `config_<NAME>.cfg`, not config.json. (low) · related: HW.S21 · [H07]
- **HW.N295** SUPPRESS · `tests_hardware/flash/test_reboot_persistence.py:29, 50` —
  "@pytest.mark.persistence_write" — Owned flash writes: reboot_persist_write config; DebugLevel raise +
  restore (plus 2 hard resets). · covered-by: HW.T01 · [H07]
- **HW.N296** LIMIT · `tests_hardware/flash/test_reboot_persistence.py:44-47` — "This bench only flashes
  the refactored `src/` build ..., never the legacy `modules/_boot.py` mechanism of BACKLOG open
  question 1" — The legacy `import sensortask.py` boot path is never exercised on silicon (consistent
  with CLAUDE.md). · [H07]
- **HW.N297** DRIFT · `tests_hardware/flash/test_reboot_persistence.py:52-54, 68, 73, 77, 79` — "This
  bench's board is left at production-quiet DebugLevel=0 between sessions" — Stale DebugLevel comments.
  · covered-by: HW.S17 · [H07]
- **HW.N298** INVAR · `tests_hardware/flash/test_reboot_persistence.py:66` — "assert \"CFGMGR_\" in
  joined or \"FRAM\" in joined" — Loose boot oracle. · covered-by: HW.S15 · [H07]
- **HW.N299** ASSUME · `tests_hardware/flash/test_reboot_persistence.py:73-74` — "write_config() only
  persists to disk, not the live debug-level registry - one more real hard_reset() makes the restored 0
  genuinely live" — Pins config-vs-live semantics for DebugLevel. · [H07]
- **HW.N300** RISK · `tests_hardware/flash/test_reboot_persistence.py:77` — "failed to restore
  DebugLevel to 0 after the boot check - board may be left non-default" — Board-state hazard on restore
  failure. (low) · related: HW.T03 · [H07]

## tests_hardware/flash/test_sensor_accuracy.py

- **HW.N301** ASSUME · `tests_hardware/flash/test_sensor_accuracy.py:22-23, 38-39, 47` — "~60s real
  runtime (45s post-reset settle + up to 15s final poll ...)"; "45s documented algorithm blackout" —
  Timeout bases; each script runs well past run_isolated's 8 s WDT, so must feed it. (low) · related:
  HW.S09 · [H07]
- **HW.N302** SUPPRESS · `tests_hardware/flash/test_sensor_accuracy.py:54-57, 67-70` —
  "pytest.skip(\"needs the NeoPixel-aimed-at-the-ISL29125 rig physically set up ...\")" —
  `neopixel_sweep` in-test skips; the gated mechanism-envelope script also makes flash writes. ·
  covered-by: HW.S05 · [H07]
- **HW.N303** ASSUME · `tests_hardware/flash/test_sensor_accuracy.py:58-60, 71-73` — "22 holds x
  SETTLE_S=4.5s is ~99s of guaranteed settle alone"; "sums to ~8.5 minutes of real segment time" —
  Durations mirror constants inside the device scripts. (low) · [H07]
- **HW.N304** LIMIT · `tests_hardware/flash/test_sensor_accuracy.py:80-89` — "run_probe_against_twin(),
  which needs that port built" — A hardware test that also needs the host Unix port; a missing build
  raises FileNotFoundError (error, not skip). (low) · [H07]

## tests_hardware/flash/test_task_supervisor.py

- **HW.N305** ASSUME · `tests_hardware/flash/test_task_supervisor.py:1-3` — "the recovery rung
  CLAUDE.md's own memory-safety-discipline rule leans on between a caught local degrade and the hardware
  watchdog" — The supervisor-restart rung is proved on silicon only by this isolated script (15 s
  timeout). · related: XCUT.T02 · [H07]

## tests_hardware/flash/test_toolchain_flash_boot.py

- **HW.N306** RISK · `tests_hardware/flash/test_toolchain_flash_boot.py:19-22` — "Cheap, run first:
  every other test in this tier assumes basic mpremote connectivity already works" — Five
  `is_reachable()` calls, each stopping main.py; order-dependent baseline. (low) · related: HW.T06 ·
  [H07]
- **HW.N307** RISK · `tests_hardware/flash/test_toolchain_flash_boot.py:30-42` — "fresh git fetch, full
  picotool rebuild, full mpy-cross/Unix-port/firmware pass), which takes ~481s wall clock on this
  bench's Pi4" — Unmarked, runs in every flash pass: host SSD wear and third-party network dependency
  inside a hardware run. · covered-by: HW.S01 · [H07]
- **HW.N308** DRIFT · `tests_hardware/flash/test_toolchain_flash_boot.py:14, 25, 46-47` — "Item 23";
  "Item 19"; "Item 20 ... Part 2 item 8" — Dangling named citations. · covered-by: DOC.S05 · [H07]
- **HW.N309** SUPPRESS · `tests_hardware/flash/test_toolchain_flash_boot.py:52-55` — "pytest.skip(\"this
  IS a real flash cycle - pass --allow-flash-cycle to deliberately run it\")" — `flash_cycle` in-test
  skip. · covered-by: HW.T13 · [H07]
- **HW.N310** SETTLED · `tests_hardware/flash/test_toolchain_flash_boot.py:57-59` — "dev, never wozi -
  wozi is never physically flashed (CLAUDE.md's hard rule), and its hardcoded pins don't match this
  bench's real wiring" — Restated hard rule. · [H07]
- **HW.N311** WORKAROUND · `tests_hardware/flash/test_toolchain_flash_boot.py:72-75` — "picotool has no
  internal retry for USB BOOTSEL re-enumeration (calling it immediately after enter_bootloader() can
  race it, failing with exit 249)" — 5× retry with 2 s sleeps; removal trigger: none stated. · [H07]
- **HW.N312** ASSUME · `tests_hardware/flash/test_toolchain_flash_boot.py:78` — "[\"sudo\",
  \"picotool\", \"load\", \"-x\", \"-v\", str(uf2_path)]" — Passwordless sudo for picotool. ·
  covered-by: HW.S19 · [H07]

## tests_hardware/flash/test_uart_crossover.py

- **HW.N313** SUPPRESS · `tests_hardware/flash/test_uart_crossover.py:19-34` — "The guard below is not
  an expected skip - it only names the cause if some future build genuinely lacks the module" — A
  firmware missing asy_uart_comm becomes a skip; broad `except Exception` re-raised otherwise. ·
  related: HW.T13 · [H07]
- **HW.N314** SETTLED · `tests_hardware/flash/test_uart_crossover.py:67-68` — "Counted, never timed: a
  poll-round count is a property of the code, while throughput on this board moves with heap state (Part
  E.7)" — Test design choice. (low) · [H07]

## tests_hardware/flash/test_watchdog_starvation.py

- **HW.N315** ASSUME · `tests_hardware/flash/test_watchdog_starvation.py:20-22` — "its 10s grace window
  put this measurement at a reproducible ~13.2s against the 10.0s bound" — Historical measurement behind
  `allow_recovery=False`. (low) · [H07]
- **HW.N316** LIMIT · `tests_hardware/flash/test_watchdog_starvation.py:29-36, 38-41` — "assert elapsed
  < 10.0"; "Checked via is_device_present()/is_reachable() rather than tail_log() content" — Reset
  proved by banner + USB drop + timing; `machine.reset_cause()` is never read. · covered-by: HW.S15 ·
  [H07]
- **HW.N317** MIRROR · `tests_hardware/flash/test_watchdog_starvation.py:13` — "_ARMED_BANNER = \"WDT
  armed, starving now\" # printed by device_scripts/watchdog_starvation_reset.py" — String coupled to
  the device script. (low) · [H07]

## tests_hardware/manual/__main__.py

- **HW.N318** INVAR · `tests_hardware/manual/__main__.py:1-3` — "run this file, never runner.py
  directly. Running runner.py directly creates a second `runner` module instance with its own empty
  `_REGISTRY`, silently no-op'ing every registered test" — Entry-point discipline; mitigated only by
  runner.py having no `__main__` block (runner.py:113-114). · related: HW.T15 · [H07]

## tests_hardware/manual/runner.py

- **HW.N319** SETTLED · `tests_hardware/manual/runner.py:1-3` — "kept structurally separate from the
  automated flash/bench runner so an unattended pass never stalls on a human" — Manual tier separation.
  (low) · [H07]
- **HW.N320** LIMIT · `tests_hardware/manual/runner.py:27-28, 94-98` — "input(f\" {prompt}... \")" then
  "PASS (human-confirmed)" — A test that uses only `confirm()` cannot record a FAIL: every
  manual_persistence and manual_sensor_accuracy test, manual_toolchain's human steps and the
  captive-portal test print PASS whenever the operator presses Enter; the only way out is Ctrl-C
  aborting the whole run (manual_sensor_accuracy.py:31). · related: HW.T15 · [H07]
- **HW.N321** SUPPRESS · `tests_hardware/manual/runner.py:72-76` — "import manual_bus_electrical # noqa:
  F401" — Five F401 suppressions for registration-by-import. (low) · [H07]
- **HW.N322** DRIFT · `tests_hardware/manual/runner.py:53` — "tier: str # \"[USB]\" or \"[USB+WiFi]\"" —
  Registered tiers are "[USB][MANUAL]"/"[USB+WiFi][MANUAL]". (low) · [H07]

## tests_hardware/manual/manual_bus_electrical.py

- **HW.N323** ASSUME · `tests_hardware/manual/manual_bus_electrical.py:11, 29` — "confirm the two-tier
  recovery (task respawn re-probe + reset/soft-reset) actually works"; "assert \"SCD30\" in joined or
  \"CO2\" in joined" — Recovery oracle is any log line naming SCD30/CO2 within 30 s —
  DebugLevel-dependent and does not show a fresh successful read. · related: HW.T15 · [H07]
- **HW.N324** PLATFORM · `tests_hardware/manual/manual_bus_electrical.py:34, 40, 43` — "within the
  8388ms cap"; "digital twin CI Run 10 only proves this in simulation" — WDT cap fact; wedged-bus
  backstop proven on silicon only here. · related: PLAT.T03 · [H07]
- **HW.N325** DRIFT · `tests_hardware/manual/manual_bus_electrical.py:46` — "rebooted = \"CFGMGR_\" in
  joined or \"FRAM SPI FRAM Driver Setup complete\" in joined" — Uses the bare "CFGMGR_" reboot marker
  the automated tier calls false-positive-prone (bench/test_memory_stress_bench.py:91-93,
  flash/test_memory_stress.py:97-98). · related: HW.S15 · [H07]
- **HW.N326** LIMIT · `tests_hardware/manual/manual_bus_electrical.py:54, 60` — "WS2812 timing values
  are NOT sourced from a datasheet in this repo's datasheets/ folder (no WS2812/Neopixel datasheet
  present) - flagged per CLAUDE.md" — Missing datasheet; only a human visual check. · [H07]
- **HW.N327** ASSUME · `tests_hardware/manual/manual_bus_electrical.py:59, 61` — "via the real
  /notification lightCmdLED endpoint" — Instruction assumes the dev LED route is live on today's
  firmware. (low) · related: HW.T15 · [H07]

## tests_hardware/manual/manual_persistence.py

- **HW.N328** DRIFT · `tests_hardware/manual/manual_persistence.py:1-3, 14, 18-19` — "real MB85RS64V";
  "PUT /notification WarnCO2={marker}" with marker "424242" — Wrong chip name, out-of-range marker, and
  the value lives in flash config, not FRAM. · covered-by: HW.S04 · [H07]
- **HW.N329** RISK · `tests_hardware/manual/manual_persistence.py:32-47` — "PUT /sensors {\"SCD30\":
  {\"MeasInt\": 7}}" — SCD30 NVM write with no restore; later SCD30 tests assume ~2 s. · covered-by:
  HW.S03 · [H07]
- **HW.N330** PLATFORM · `tests_hardware/manual/manual_persistence.py:14, 34` — "data retention >=10
  years at +85 degC"; "the sensor's own onboard NVM (measurement interval, ambient pressure, altitude,
  temp offset, self-cal)" — Datasheet claims (FRAM retention; SCD30 NVM-held settings). · related:
  SENS.T01 · [H07]
- **HW.N331** DRIFT · `tests_hardware/manual/manual_persistence.py:52, 56-59` — "an active
  config.json/FRAM write"; "cut power to the board as close to immediately afterward as you physically
  can" — config.json naming, and since WP5 the flash write is deferred past the response. · covered-by:
  HW.S21 · [H07]
- **HW.N332** LIMIT · `tests_hardware/manual/manual_persistence.py:12-71` — "Trigger a real SCD30 NVM
  write now" — Manual tier sits outside the `persistence_write` wear gate: every run spends flash and
  SCD30 NVM writes by instruction. · related: HW.T01 · [H07]

## tests_hardware/manual/manual_sensor_accuracy.py

- **HW.N333** PLATFORM · `tests_hardware/manual/manual_sensor_accuracy.py:11-15` — "BMP388/BMP384
  typical accuracy, read from datasheets/bmp3xx/bst-bmp388-ds001.pdf" — Tolerances taken from the BMP388
  sheet only, although the heading names both parts. (low) · [H07]
- **HW.N334** DRIFT · `tests_hardware/manual/manual_sensor_accuracy.py:24, 27, 30` — "note the
  Press/Temp fields"; "Enter the reference pressure in Pa" — Driver publishes `Pres` in hPa (with
  PressOffset). · covered-by: HW.S22 · [H07]
- **HW.N335** PLATFORM · `tests_hardware/manual/manual_sensor_accuracy.py:34-38` — "Table 1 (not assumed
  from memory): VOC Index range 1-500, response time <10s (63%) to <30s (90%)" — SGP40 datasheet
  figures. (low) · [H07]
- **HW.N336** DRIFT · `tests_hardware/manual/manual_sensor_accuracy.py:47` — "note the SGP40 VocIndex
  field" — The REST field is `VOC` (bench/test_rest_endpoints_over_sta.py:74). · related: HW.T15 · [H07]
- **HW.N337** ASSUME · `tests_hardware/manual/manual_sensor_accuracy.py:56-58` — "The ISL29125 datasheet
  states no lux accuracy figure" — Datasheet claim behind relative-only assertions. (low) · [H07]
- **HW.N338** ASSUME · `tests_hardware/manual/manual_sensor_accuracy.py:76, 79` — "RangeAct changes to
  375"; "the on-board WS2812 (GP18 on the dev bench)" — Hardcoded range value and pin vs
  devices/dev.toml. (low) · related: HW.T08 · [H07]

## tests_hardware/manual/manual_toolchain.py

- **HW.N339** SETTLED · `tests_hardware/manual/manual_toolchain.py:19-20` — "dev, never wozi - wozi is
  never physically flashed (CLAUDE.md's hard rule)" — Restated rule. (low) · [H07]
- **HW.N340** ASSUME · `tests_hardware/manual/manual_toolchain.py:42` — "[\"sudo\", \"picotool\",
  \"load\", \"-x\", \"-v\", str(uf2_path)]" — Passwordless sudo on the host. (low) · covered-by: HW.S19
  · [H07]

## tests_hardware/manual/manual_wifi.py

- **HW.N341** MIRROR · `tests_hardware/manual/manual_wifi.py:19, 30` — "password: 12345678" — Committed
  hotspot credential copy #4 (instruction text). · covered-by: HW.S24 · [H07]
- **HW.N342** RISK · `tests_hardware/manual/manual_wifi.py:16` — "e.g. after PUT /networking {\"SSID\":
  \"\"}" — Instructs a persisting SSID clear with no restore step. (low) · related: HW.T15 · [H07]
- **HW.N343** ASSUME · `tests_hardware/manual/manual_wifi.py:32` — "http://<gateway IP, usually
  192.168.4.1>/" — Assumed CYW43 AP gateway address. (low) · [H07]

## tests_hardware/device_scripts/allocation_need_per_source.py

- **HW.N344** RISK · `tests_hardware/device_scripts/allocation_need_per_source.py:10, 112` — "await
  sensortask_dev.build_system(web_host=\"127.0.0.1\", web_port=8080)" — Builds the full production
  object graph in isolation, including its own FRAM manager/loggers over the real chip (production's
  first chunks) and ConfigManager setup. · covered-by: HW.T17 · [H07]
- **HW.N345** ASSUME · `tests_hardware/device_scripts/allocation_need_per_source.py:43-45` — "A 1-block
  allocation advances the allocator's scan hint, so they land in address order" — Sieve construction
  relies on py/gc.c allocator behaviour. · [H07]
- **HW.N346** SUPPRESS · `tests_hardware/device_scripts/allocation_need_per_source.py:48, 56-57, 60, 65, 119`
  — "except MemoryError: pass"; "gc.collect()" — Deliberate MemoryError fill and gc.collect() calls in a
  measurement instrument (outside src/'s confined sites). · related: MEM.T05 · [H07]
- **HW.N347** LIMIT · `tests_hardware/device_scripts/allocation_need_per_source.py:98-99, 126-128` —
  "everything but the socket write and microdot's own request parsing"; "a probe that degrades
  internally (a caught MemoryError, logged) still returns normally, and only the host can see that in
  the log" — Measured need excludes socket write and request parsing; relies on private
  `ws._status_sources` etc. · related: MEM.T03 · [H07]
- **HW.N348** SUPPRESS · `tests_hardware/device_scripts/allocation_need_per_source.py:152-153` — "except
  Exception as e: # a failure here is a result, reported rather than raised into the harness" — Broad
  catch → RESULT: FAIL. (low) · [H07]

## tests_hardware/device_scripts/bmp3xx_plausibility_read.py

- **HW.N349** INVAR · `tests_hardware/device_scripts/bmp3xx_plausibility_read.py:2-3, 20-23` — "Primes
  reader.cfgmgr directly (no real flash I/O)" — Pokes private `cfgmgr.valid`/`_cache` to avoid a flash
  write; coupled to ConfigManager internals. · related: HW.T01 · [H07]
- **HW.N350** DRIFT · `tests_hardware/device_scripts/bmp3xx_plausibility_read.py:17 (also scd30_plausibility_read.py:19, sgp40_voc_algorithm_quality.py:45, sgp40_fram_backup_restore.py:53, isl29125_plausibility_read.py:22, bus_concurrency_same_device_scd30.py:25)`
  — "matches src/system_service.py's own production value" — Production `WDT(timeout=8000)` is emitted
  by buildgen/codegen.py:381, not system_service.py. (low) · related: XCUT.S13 · [H07]
- **HW.N351** ASSUME · `tests_hardware/device_scripts/bmp3xx_plausibility_read.py:18` —
  "asy_i2c_driver.I2C(0, 13, 12, frequency=50000)" — Hardcoded dev pins/frequency (one of ~20 scripts).
  · covered-by: HW.S18 · [H07]
- **HW.N352** SUPPRESS · `tests_hardware/device_scripts/bmp3xx_plausibility_read.py:42-43` — "except
  (asyncio.CancelledError, Exception): pass" — Task-teardown swallow (same pattern in many scripts).
  (low) · [H07]

## tests_hardware/device_scripts/bmp3xx_same_device_rw_concurrency.py

- **HW.N353** PLATFORM · `tests_hardware/device_scripts/bmp3xx_same_device_rw_concurrency.py:2-3` —
  "BMP3xx's OSR/CONFIG registers are volatile (no NVM), so unlike SCD30 this writes freely" — Datasheet
  fact justifying unmarked writes. · [H07]
- **HW.N354** MIRROR · `tests_hardware/device_scripts/bmp3xx_same_device_rw_concurrency.py:14` —
  "_OSR_SETTINGS = (1, 2, 4, 8, 16, 32)" — Driver constant copied. (low) · [H07]
- **HW.N355** SUPPRESS · `tests_hardware/device_scripts/bmp3xx_same_device_rw_concurrency.py:62-68` —
  "Restore the datasheet/production default (x1 ...)" + "except Exception: pass" — Restores the default,
  not the board's configured value; failure swallowed. (low) · [H07]

## tests_hardware/device_scripts/bus_concurrency_cross_device_scd30_sgp40.py

- **HW.N356** INVAR · `tests_hardware/device_scripts/bus_concurrency_cross_device_scd30_sgp40.py:23-25`
  — "this group's one NVM-persisted write happens once per session in flash/conftest.py's
  scd30_continuous_measurement_triggered fixture" — Script correctness depends on a host fixture having
  run first. · related: HW.T01 · [H07]
- **HW.N357** ASSUME · `tests_hardware/device_scripts/bus_concurrency_cross_device_scd30_sgp40.py:19, 26`
  — "I2C(1, 15, 14, frequency=50000, timeout=200000)"; "await sgp.setup() # includes one initialize()
  call already" — Hardcoded pins; SGP40 setup (whose `_reset()` is the general-call path per C.8) runs
  next to SCD30. · covered-by: HW.S18 · [H07]
- **HW.N358** ASSUME · `tests_hardware/device_scripts/bus_concurrency_cross_device_scd30_sgp40.py:89-93`
  — "less interleaving than expected, worth a closer look even though not zero" — Heuristic floor (≥1
  interleaved read per SGP40 window) fails the run. (low) · related: HW.T05 · [H07]

## tests_hardware/device_scripts/bus_concurrency_isl29125_write_vs_siblings.py

- **HW.N359** ASSUME · `tests_hardware/device_scripts/bus_concurrency_isl29125_write_vs_siblings.py:1-3, 15-19`
  — "Why delays, not yields: SPECIFICATION.md Part C.8"; "_WRITE_DELAYS_MS = (5, 15, 40, 80, 120)" —
  Host-chosen offsets stand in for the mock tier's systematic sweep; coverage of the relevant phase is
  not proven. · related: HW.T05 · [H07]
- **HW.N360** LIMIT ·
  `tests_hardware/device_scripts/bus_concurrency_isl29125_write_vs_siblings.py:61-63` — "outside the
  16-bit range - a torn word" — Torn-read oracle can only catch impossible values (and CRC/NAK
  exceptions). · related: HW.T05 · [H07]

## tests_hardware/device_scripts/bus_concurrency_same_device_scd30.py

- **HW.N361** ASSUME · `tests_hardware/device_scripts/bus_concurrency_same_device_scd30.py:18-21, 33-35`
  — "setup()'s soft reset leaves the NVM-persisted measurement interval running ...
  scd30_same_device_rw_concurrency.py carries the same constant" — `_SETTLE_S = 12.0` duplicated across
  two scripts; assumes the NVM MeasInt is ~2 s (manual tier may leave 7). · related: HW.S03 · [H07]
- **HW.N362** ASSUME · `tests_hardware/device_scripts/bus_concurrency_same_device_scd30.py:2-3` — "Both
  paths are CRC-8 protected, so interleaving corruption would trip a CRC/NAK, not silently succeed" —
  Oracle rests on CRC detection. (low) · [H07]
- **HW.N363** MIRROR · `tests_hardware/device_scripts/bus_concurrency_same_device_scd30.py:12-14, 71-74`
  — "2 <= meas_int <= 1800"; "400 <= frc <= 2000" — Schema bounds copied from the driver. (low) · [H07]

## tests_hardware/device_scripts/bus_concurrency_scd30_write_vs_siblings.py

- **HW.N364** INVAR · `tests_hardware/device_scripts/bus_concurrency_scd30_write_vs_siblings.py:1-3, 73-75`
  — "THE one extra real NVM write this script makes ... this script must never be called more than once
  per opt-in run" — SCD30 NVM write (`set_temperature_offset(4.0)`), gated host-side by
  scd30_extra_write; once-per-run by convention. · covered-by: HW.T01 · [H07]
- **HW.N365** RISK · `tests_hardware/device_scripts/bus_concurrency_scd30_write_vs_siblings.py:75` —
  "await scd.set_temperature_offset(4.0)" — Leaves a non-default temperature offset in SCD30 NVM; no
  restore. · related: HW.T03 · [H07]

## tests_hardware/device_scripts/bus_deinit_is_a_noop_on_real_hardware.py

- **HW.N366** RISK · `tests_hardware/device_scripts/bus_deinit_is_a_noop_on_real_hardware.py:44-53` —
  "fram = AsyFramManager(spi_wrapper, SPI_CS, max_size=0x40000, debug=None)"; "chunk.write(PATTERN)" —
  Own FRAM manager over the real chip overwrites production's first chunk with a test pattern. ·
  covered-by: HW.T17 · [H07]
- **HW.N367** ASSUME · `tests_hardware/device_scripts/bus_deinit_is_a_noop_on_real_hardware.py:13-14, 45`
  — "I2C_PORT, I2C_SCL, I2C_SDA = 0, 13, 12 # dev bench wiring"; "max_size=0x40000" — Hardcoded pins;
  256 KB size assumes the MB85RS2MTA part. · related: HW.T07 · [H07]
- **HW.N368** LIMIT · `tests_hardware/device_scripts/bus_deinit_is_a_noop_on_real_hardware.py:55` —
  "raw_spi = spi_wrapper._spi" — Reaches into the wrapper's private attribute. (low) · [H07]

## tests_hardware/device_scripts/bus_topology_autodetect_and_hazard_sweep.py

- **HW.N369** MIRROR · `tests_hardware/device_scripts/bus_topology_autodetect_and_hazard_sweep.py:21-23`
  — "The on-target copy of the address table ... Adding a driver means adding it here too (Part K.7)" —
  Hand-kept address table mirrors the host device model. · related: HW.T08 · [H07]
- **HW.N370** ASSUME · `tests_hardware/device_scripts/bus_topology_autodetect_and_hazard_sweep.py:28-30`
  — "This bench's own real pin assignments (sensortask_dev.py's own construction comments)" — Hardcoded
  bus pins/timeouts, cited from a generated file's comments. · covered-by: HW.S18 · [H07]
- **HW.N371** LIMIT · `tests_hardware/device_scripts/bus_topology_autodetect_and_hazard_sweep.py:33-44`
  — "return None # clean NAK/timeout"; "return None # ACKed" — Probe returns None for both NAK and ACK,
  so the address/reserved sweeps can only fail on a non-OSError exception. · covered-by: HW.S12 · [H07]
- **HW.N372** LIMIT · `tests_hardware/device_scripts/bus_topology_autodetect_and_hazard_sweep.py:47-50, 170-172`
  — "read_measurement() degrades cleanly (cached fields stay None, no exception)"; "if len(known_here)
  == 1" — Self-hazard runs only for a lone device, and an SCD30 read "passes" with no data. ·
  covered-by: HW.S12 · [H07]
- **HW.N373** SUPPRESS ·
  `tests_hardware/device_scripts/bus_topology_autodetect_and_hazard_sweep.py:104-116, 133-136` — "#
  noqa: E731"; "except OSError: pass" — Four lambda suppressions; general-call broadcast errors
  swallowed. (low) · [H07]
- **HW.N374** RISK · `tests_hardware/device_scripts/bus_topology_autodetect_and_hazard_sweep.py:131-137`
  — "i2c.writeto(GENERAL_CALL_ADDRESS, b\"\\x06\")" — Issues real general-call resets on the bus the
  SCD30 sits on. (low) · related: HW.T03 · [H07]

## tests_hardware/device_scripts/float_boundary_2pow24.py

- **HW.N375** DRIFT · `tests_hardware/device_scripts/float_boundary_2pow24.py:7-8` — "kept only for
  parity with how isolated-driver scripts are documented to work" — Vestigial `sys.path.insert(0, "/")`,
  not used by other scripts. (low) · [H07]
- **HW.N376** ASSUME · `tests_hardware/device_scripts/float_boundary_2pow24.py:20-35` —
  "coerce_numeric() always accepts this by design; the real assertion is whether the stored value
  silently lost precision" — Pins that precision loss is accepted silently (expects 2**24,
  round-to-even). · related: MEM.T07 · [H07]

## tests_hardware/device_scripts/fram_busy_status_lockout.py

- **HW.N377** LIMIT · `tests_hardware/device_scripts/fram_busy_status_lockout.py:1-3` — "The overrun is
  a DMA timing condition Python cannot induce; its consequence is" — Only the consequence of an RX
  overrun is tested. · related: PLAT.T03 · [H07]
- **HW.N378** MIRROR · `tests_hardware/device_scripts/fram_busy_status_lockout.py:14-17` — "Wire-level
  values, hardcoded rather than imported: asy_fram_manager.py's own _STATUS_*/_ADDR_* are
  micropython.const() and compiled away" — Copied wire constants. · [H07]
- **HW.N379** RISK · `tests_hardware/device_scripts/fram_busy_status_lockout.py:39-65` —
  "AsyFramManager(spi0, 5, max_size=0x40000, debug=None)"; "_force_both_blocks_busy" — Overwrites
  production's first FRAM chunk and deliberately leaves it BUSY before rewriting. · covered-by: HW.T17 ·
  [H07]

## tests_hardware/device_scripts/fram_capacity_after_full_system_build.py

- **HW.N380** RISK · `tests_hardware/device_scripts/fram_capacity_after_full_system_build.py:30` —
  "await sensortask_dev.build_system(cfg_path=\"\", web_host=\"127.0.0.1\", web_port=8080)" — Full
  build_system over the real FRAM re-runs production's deterministic allocation (same chunks). ·
  covered-by: HW.T17 · [H07]
- **HW.N381** MIRROR · `tests_hardware/device_scripts/fram_capacity_after_full_system_build.py:11-17` —
  "Every name dev's build_system() constructs that could hold a FRAM-backed logger. Probed via
  getattr()" — Hand-kept attribute-name list; a new FRAM-wired module name is silently skipped
  (`continue` on None). · related: HW.T02 · [H07]
- **HW.N382** SETTLED · `tests_hardware/device_scripts/fram_capacity_after_full_system_build.py:3` —
  "mpremote-only by design; tests_hardware/README.md has both reasons" — No runtime surface for FRAM
  capacity. (low) · [H07]

## tests_hardware/device_scripts/fram_cs_hijack_fault_injection_and_recovery.py

- **HW.N383** INVAR ·
  `tests_hardware/device_scripts/fram_cs_hijack_fault_injection_and_recovery.py:13-16` — "scratch
  addresses, disjoint from every other device script's own regions" — Raw FRAM addresses 0x9000-0x93FF
  kept disjoint by convention only; beyond an 8 KB MB85RS64V's range, and not checked against
  production's allocated chunks. · related: HW.T07 · [H07]
- **HW.N384** ASSUME ·
  `tests_hardware/device_scripts/fram_cs_hijack_fault_injection_and_recovery.py:25-27` — "measure A made
  that window non-yielding, so the race could no longer land (HEAP_FRAGMENTATION_MEASUREMENTS archive
  §7D.5)" — Injection moved to the synchronous seam after a measurement-driven src change. (low) · [H07]
- **HW.N385** SUPPRESS ·
  `tests_hardware/device_scripts/fram_cs_hijack_fault_injection_and_recovery.py:49, 57, 60-61` — "#
  type: ignore[method-assign]" — Four method-assign suppressions in device-script code (checked in the
  main mypy pass). · [H07]
- **HW.N386** ASSUME ·
  `tests_hardware/device_scripts/fram_cs_hijack_fault_injection_and_recovery.py:161-163` — "Not asserted
  against a specific wrong value (a different unit could float differently on a deselected MISO)" —
  Read-hijack oracle is "not the seeded data". (low) · [H07]

## tests_hardware/device_scripts/fram_error_log_reset_during_boot_window.py

- **HW.N387** RISK · `tests_hardware/device_scripts/fram_error_log_reset_during_boot_window.py:17-33` —
  "AsyFramManager(spi0, 5, max_size=0x40000 ...)"; "await store.err_s(\"seeded\", errno=SEEDED_ERRNO)"
  with SEEDED_ERRNO = 5 — Seeds errno=5 into production's first FRAM chunk — the exact pattern CLAUDE.md
  records as later read back as SYSTEM's "Task N ended"; this script resets it again before exiting only
  on the success path. · covered-by: HW.T17 · [H07]
- **HW.N388** SETTLED · `tests_hardware/device_scripts/fram_error_log_reset_during_boot_window.py:28-29`
  — "Clear at the START, never at the end (tests_hardware/README.md's own rule)" — Stated device-script
  FRAM rule (contrasts with early-return paths that leave seeded history). · related: HW.T02 · [H07]

## tests_hardware/device_scripts/fram_error_log_reset_race_seed_and_race.py

- **HW.N389** RISK · `tests_hardware/device_scripts/fram_error_log_reset_race_seed_and_race.py:14-15, 28-31, 46-47, 58`
  — "First chunk allocated off a freshly-constructed manager, so it lands at allocation offset 0";
  "SEEDED_ERRNO = 5"; "RACED_ERRNO = 6" — Writes errno 5/6 entries into production's chunk 0 and then
  resets mid-write; the verify phase never clears them — the board is left with plausible-looking
  fabricated history (CLAUDE.md's errno=5 incident). · covered-by: HW.T17 · [H07]
- **HW.N390** ASSUME · `tests_hardware/device_scripts/fram_error_log_reset_race_seed_and_race.py:60-64`
  — "One await asyncio.sleep(0) before acting - next-in-line the instant victim_writer yields, same
  scheduling-order dependency" — Race landing depends on asyncio scheduling order; no evidence the reset
  hit mid-write. · related: HW.T05 · [H07]
- **HW.N391** SUPPRESS · `tests_hardware/device_scripts/fram_error_log_reset_race_seed_and_race.py:49` —
  "# noqa: B905 - MicroPython zip() rejects strict=" — Platform-driven suppression (also in
  fram_error_log_reset_race_verify.py:41, 57 and fram_error_log_roundtrip.py:63). · [H07]

## tests_hardware/device_scripts/fram_error_log_reset_race_verify.py

- **HW.N392** SETTLED · `tests_hardware/device_scripts/fram_error_log_reset_race_verify.py:31-32` —
  "Deliberately NOT cleared first, against tests_hardware/README.md's clear-at-the-start rule" —
  Deliberate exception; the chunk is left holding errno 5/6/7 entries afterwards. · covered-by: HW.T17 ·
  [H07]

## tests_hardware/device_scripts/fram_error_log_roundtrip.py

- **HW.N393** LIMIT · `tests_hardware/device_scripts/fram_error_log_roundtrip.py:2-3, 33-35` —
  "simulates a fresh boot (a new AsyFramManager)" — Not a real reboot; also names the chip MB85RS2MTA
  (the flash test says MB85RS64V). · related: HW.S17 · [H07]
- **HW.N394** RISK · `tests_hardware/device_scripts/fram_error_log_roundtrip.py:19-31` — "await
  pr1.err_s(\"test error for fram_error_log_roundtrip.py\", errno=TEST_ERRNO)" — Leaves an errno=42
  entry in production's chunk 0. · covered-by: HW.T17 · [H07]

## tests_hardware/device_scripts/fram_manager_roundtrip.py

- **HW.N395** RISK · `tests_hardware/device_scripts/fram_manager_roundtrip.py:16-27` — "chunk =
  fram.get_chunk(CHUNK_SIZE, crc=CRC8())"; "chunk.write(PATTERN)" — Overwrites production's first FRAM
  chunk with a test pattern. · covered-by: HW.T17 · [H07]

## tests_hardware/device_scripts/fram_pause_unpause_and_gating.py

- **HW.N396** ASSUME · `tests_hardware/device_scripts/fram_pause_unpause_and_gating.py:103-105` —
  "Whether the re-arm aborts on ENOMEM or finds the slot its own deinit() just freed is an rp2 detail;
  both are fine" — Invariant asserted either way; which path ran is not recorded. · related: PLAT.T03 ·
  [H07]
- **HW.N397** SUPPRESS · `tests_hardware/device_scripts/fram_pause_unpause_and_gating.py:112-113, 126-129`
  — "except OSError: pass # the pool is now exhausted"; "except Exception: pass" — Deliberate alarm-pool
  exhaustion (64 Timers) and swallowed deinit errors. (low) · [H07]
- **HW.N398** RISK · `tests_hardware/device_scripts/fram_pause_unpause_and_gating.py:171-182` —
  "AsyFramManager(spi0, 5, max_size=0x40000 ...)"; "SystemService(_ntp_never_synced, fram=fram,
  debug=None)" — Overwrites production's first chunks (plain + timestamped) with test patterns. ·
  covered-by: HW.T17 · [H07]

## tests_hardware/device_scripts/fram_reset_race_during_write_seed_and_race.py

- **HW.N399** INVAR ·
  `tests_hardware/device_scripts/fram_reset_race_during_write_seed_and_race.py:13-17` — "Scratch
  addresses, disjoint from every other device script's own regions (CS-hijack uses 0x9000-0x93ff)" — Raw
  0xA000-0xA03F region kept disjoint by convention; beyond an 8 KB part. · related: HW.T07 · [H07]
- **HW.N400** ASSUME ·
  `tests_hardware/device_scripts/fram_reset_race_during_write_seed_and_race.py:55-65` — "machine.reset()
  # never returns - real RP2040 hardware reset, immediate, CS still asserted" — Reset fires before the
  payload bytes are sent, so the test proves an unsent-payload command does not commit, not a
  mid-payload tear. (low) · related: HW.T05 · [H07]
- **HW.N401** SUPPRESS ·
  `tests_hardware/device_scripts/fram_reset_race_during_write_seed_and_race.py:67, 69` — "# type:
  ignore[method-assign]" — Two more method-assign suppressions. · [H07]

## tests_hardware/device_scripts/fram_reset_race_during_write_verify_recovery.py

- **HW.N402** DRIFT ·
  `tests_hardware/device_scripts/fram_reset_race_during_write_verify_recovery.py:1-3` — "the real
  hardware reset seed_and_race.py's reset_yanker() triggered mid-write" — The phase-1 script resets from
  `resetting_write_sync`; `reset_yanker()` lives in fram_error_log_reset_race_seed_and_race.py. (low) ·
  [H07]

## tests_hardware/device_scripts/fram_same_device_rw_concurrency.py

- **HW.N403** RISK · `tests_hardware/device_scripts/fram_same_device_rw_concurrency.py:13-14, 30-31` —
  "READ_REGION = (0x0000, 32) # never touched by the writer below"; "WRITE_REGION = (0x8000, 32) #
  disjoint scratch region, well within the real 256KB chip's range" — Raw write of a seed pattern at
  FRAM address 0 — production's first chunk — plus a scratch region that assumes the 256 KB part. ·
  covered-by: HW.T17 · [H07]
- **HW.N404** PLATFORM · `tests_hardware/device_scripts/fram_same_device_rw_concurrency.py:2-3` — "FRAM
  has no NVM write-wear concern (10^13 ops/byte, datasheets/fram/)" — Endurance figure of the MB85RS2MTA
  sheet (MB85RS64V is 10^12 per the plan). · related: HW.T07 · [H07]

## tests_hardware/device_scripts/fram_write_protect_roundtrip.py

- **HW.N405** RISK · `tests_hardware/device_scripts/fram_write_protect_roundtrip.py:93-107` — "Always
  leave the real chip unprotected on exit, regardless of where a failure occurs - a stuck-protected chip
  would silently break every other FRAM-owning module's writes" — Non-volatile WPEN|BP0|BP1 restored
  only in `finally`; a WDT reset/killed mpremote leaves production FRAM protected. · covered-by: HW.S07
  · [H07]
- **HW.N406** LIMIT · `tests_hardware/device_scripts/fram_write_protect_roundtrip.py:48-59` — "Lying to
  the driver (_wp is only a cached status-register copy)"; "No verdict of its own" — Chip-level refusal
  tested by desyncing a private cache field. (low) · [H07]
- **HW.N407** RISK · `tests_hardware/device_scripts/fram_write_protect_roundtrip.py:82-99` —
  "AsyFramManager(spi0, 5, max_size=0x40000 ...)"; "chunk.write(PATTERN_A)" — Also overwrites
  production's first chunk. · covered-by: HW.T17 · [H07]

## tests_hardware/device_scripts/heap_headroom_after_full_system_build.py

- **HW.N408** PLATFORM · `tests_hardware/device_scripts/heap_headroom_after_full_system_build.py:11-14`
  — "mpremote's raw-REPL soft reset keeps whatever threshold was in force ... until 2026-09-24, setting
  none of its own, this script read one or the other by timing (MEASUREMENTS M3.8)" — Earlier readings
  of this script are threshold-ambiguous. · related: HW.T16 · [H07]
- **HW.N409** ASSUME · `tests_hardware/device_scripts/heap_headroom_after_full_system_build.py:36-39` —
  "Every [HW] reading of a fully built dev graph is 87,760-87,968 B, so this is ~14% over" — `_MAX_USED = 100_000`
  fitted to measurements of an unnamed image. · related: HW.T16 · [H07]
- **HW.N410** ASSUME · `tests_hardware/device_scripts/heap_headroom_after_full_system_build.py:83-93` —
  "A probe run can pin its own buffer through a stale root ... always _PROBE_MAX >> k, e.g. 49,152
  (MEASUREMENTS M2.2)" — Known probe artefact handled by rereads; a persisting one only prints WARNING
  and the result still gates. · [H07]
- **HW.N411** MIRROR · `tests_hardware/device_scripts/heap_headroom_after_full_system_build.py:117` —
  "gc.threshold(32768) # what buildgen.codegen.generate_boot_entry_source() sets in the real firmware" —
  Copied production GC threshold. · [H07]
- **HW.N412** RISK · `tests_hardware/device_scripts/heap_headroom_after_full_system_build.py:105` —
  "await sensortask_dev.build_system(cfg_path=\"\", ...)" — Full build_system over the real FRAM
  (production allocation). · covered-by: HW.T17 · [H07]
- **HW.N413** SUPPRESS · `tests_hardware/device_scripts/heap_headroom_after_full_system_build.py:46, 59, 64, 67, 77`
  — "gc.collect()" — Measurement-instrument gc.collect() calls. (low) · related: MEM.T05 · [H07]

## tests_hardware/device_scripts/heap_layout_after_full_boot_sequence.py

- **HW.N414** LIMIT · `tests_hardware/device_scripts/heap_layout_after_full_boot_sequence.py:3, 219-222`
  — "Report only, no floors"; "No reading for this position exists yet on silicon, so a threshold here
  would be invented" — Always PASSes; no host wrapper runs it (orphan). · covered-by: HW.S16 · [H07]
- **HW.N415** LIMIT · `tests_hardware/device_scripts/heap_layout_after_full_boot_sequence.py:161-163` —
  "main()'s own order, minus ntp_force_sync() ... It allocates during the gap between the two lists
  either way - stated, not measured here" — Boot sequence reproduced without its NTP step. · [H07]
- **HW.N416** ASSUME · `tests_hardware/device_scripts/heap_layout_after_full_boot_sequence.py:25-35` —
  "the twin says B's gain decays there within ~2 s (MEASUREMENTS M3.9)"; "~41 ms on the RP2040
  (MEASUREMENTS archive 7F.7)" — Settle/grace constants from twin and single silicon measurements. ·
  related: HW.T16 · [H07]
- **HW.N417** PLATFORM · `tests_hardware/device_scripts/heap_layout_after_full_boot_sequence.py:44-47` —
  "mpremote run takes no argv but does share globals with an `exec` earlier in the same raw-REPL session
  ... Verified on this board, 2026-09-22; assigning sys.argv raises there" — Arm selection relies on
  raw-REPL global sharing. · [H07]
- **HW.N418** MIRROR · `tests_hardware/device_scripts/heap_layout_after_full_boot_sequence.py:17-18, 55-58, 213`
  — "Same doubling/halving bounds as heap_headroom_after_full_system_build.py, deliberately"; "Ported
  from tests/_boot_contiguity_probe.py"; "gc.threshold(32768)" — Probe duplicated across two scripts and
  a unit-tier probe. · related: TEST.T08 · [H07]
- **HW.N419** SUPPRESS · `tests_hardware/device_scripts/heap_layout_after_full_boot_sequence.py:138-139, 177-184`
  — "sensortask_dev.gc = batch_gc # type: ignore[assignment]"; "sysfunct._start_task =
  _counting_start_task" — Module/private-method patching of generated and src code. (low) · [H07]

## tests_hardware/device_scripts/heap_under_connection_ceiling.py

- **HW.N420** RISK · `tests_hardware/device_scripts/heap_under_connection_ceiling.py:40` —
  "create_task(sensortask_dev.main())" — Runs the full production main (WiFi, FRAM, config) from a
  device script for 90 s + 20 s. · covered-by: HW.T17 · [H07]
- **HW.N421** INVAR · `tests_hardware/device_scripts/heap_under_connection_ceiling.py:41-43` — "a
  request driven from this process would share the heap under measurement, which is the whole thing Part
  E.9 forbids" — Measurement discipline: load is host-driven only. · [H07]
- **HW.N422** ASSUME · `tests_hardware/device_scripts/heap_under_connection_ceiling.py:12-15, 44` — "The
  threshold is the boot entry's own ... what MEASUREMENTS archive 7R.2 was taken at"; "await
  asyncio.sleep(20)" — Fixed 20 s boot wait before READY; threshold copied from the boot entry. (low) ·
  [H07]

## tests_hardware/device_scripts/isl29125_cross_device_concurrency.py

- **HW.N423** ASSUME · `tests_hardware/device_scripts/isl29125_cross_device_concurrency.py:32, 50` — "or
  continuous measurement was never triggered"; "no set_ambient_pressure() - that is the one NVM write
  this group makes, via the session fixture" — Depends on the host session fixture's SCD30 NVM write
  having run. · related: HW.T01 · [H07]
- **HW.N424** ASSUME · `tests_hardware/device_scripts/isl29125_cross_device_concurrency.py:33-38, 105-110`
  — "zero ISL29125 reads completed inside any SGP40 initialize() window" — Interleaving floor is ≥1 in
  total (weaker than the SCD30/SGP40 script's per-window heuristic). (low) · related: HW.T05 · [H07]

## tests_hardware/device_scripts/isl29125_plausibility_read.py

- **HW.N425** RISK · `tests_hardware/device_scripts/isl29125_plausibility_read.py:23-28, 84-85` —
  "depending on ambient made this result depend on test ORDER - it passed with the pixel latched white,
  then failed once a preceding test parked it dark" — Known order dependence between device scripts via
  the latched NeoPixel; the script now self-lights and parks it dark afterwards (the early no-reading
  return skips the park). · [H07]
- **HW.N426** ASSUME · `tests_hardware/device_scripts/isl29125_plausibility_read.py:14-17` —
  "_SELF_LIGHT_LEVEL = 20 # ~750 lx at this geometry"; "ROOM_LIGHT_MIN_LUX = 5.0" —
  Bench-geometry-dependent calibration of the self-lit scene. · [H07]
- **HW.N427** PLATFORM · `tests_hardware/device_scripts/isl29125_plausibility_read.py:1-2, 14-15` —
  "FN8424 p1's own 0.0057-10000 lx span ... McCamy's 2000-12500 K" — Datasheet/literature bounds. (low)
  · [H07]
- **HW.N428** ASSUME · `tests_hardware/device_scripts/isl29125_plausibility_read.py:26, 30-31` —
  "NeoPixel(Pin(18, Pin.OUT), 1)"; "ISL29125_Reader(i2c1, 6, ...)" — Hardcoded GP18/GP6/i2c1 pins vs
  dev.toml. · covered-by: HW.S18 · [H07]
- **HW.N429** INVAR · `tests_hardware/device_scripts/isl29125_plausibility_read.py:32-37` — "Seeded from
  the driver's own schema, never a hand-copied list - a key added there (GainRatio, f05f82d) otherwise
  leaves this one short of _N_FLOAT_CFG" — Private cfgmgr priming (no flash write) must track the
  schema; same in isl29125_real_irq_edge.py:89-95. · [H07]

## tests_hardware/device_scripts/isl29125_real_irq_edge.py

- **HW.N430** ASSUME · `tests_hardware/device_scripts/isl29125_real_irq_edge.py:15-20` — "~3030ms worst
  case, so the old 3.0s no longer clears it. 6.0s is still 5x under the periodic fallback"; "tINT =
  101ms typ (p3)" — Deadline derived from datasheet typicals. · [H07]
- **HW.N431** DRIFT · `tests_hardware/device_scripts/isl29125_real_irq_edge.py:86-87` — "A 30s periodic
  interval means a reading inside 3s can only have come from the interrupt" — Deadline is 6.0 s (:18).
  (low) · [H07]
- **HW.N432** RISK · `tests_hardware/device_scripts/isl29125_real_irq_edge.py:70-72` — "`mpremote run`
  leaves it wherever the WiFi signalling service last wrote it - often full white, ~2000 lx here" —
  Interrupted main.py leaves the NeoPixel state behind for the next script. (low) · [H07]

## tests_hardware/device_scripts/isl29125_same_device_rw_concurrency.py

- **HW.N433** INVAR · `tests_hardware/device_scripts/isl29125_same_device_rw_concurrency.py:20-22` —
  "Constructs the PROTOCOL layer directly, never ISL29125_Reader: Part C.8's standing rule for a
  concurrency script exercising persisted config, so nothing here touches the RP2040's flash" — Wear
  rule for device scripts, by convention. · related: HW.T01 · [H07]
- **HW.N434** PLATFORM · `tests_hardware/device_scripts/isl29125_same_device_rw_concurrency.py:14-15, 57-58`
  — "_STATUS_RESERVED_MASK = 0xC8 # B7:B6 and B3 read zero on a working part (p12, Table 15)"; "a 2-byte
  burst at 0x02, which deliberately does NOT restart the conversion" — Datasheet facts behind the
  oracle. · [H07]
- **HW.N435** LIMIT · `tests_hardware/device_scripts/isl29125_same_device_rw_concurrency.py:71` — "await
  asyncio.gather(reader(), writer())" — No `wait_for` bound, unlike sibling scripts (host timeout still
  applies). (low) · [H07]

## tests_hardware/device_scripts/isl29125_lighting_scenarios.py

- **HW.N436** ASSUME · `tests_hardware/device_scripts/isl29125_lighting_scenarios.py:27-31, 233-235` —
  "Measured on the covered rig: rising, the low range holds to level 6 (~197 lx) and the high takes over
  at level 8 (~300 lx)" — Scenario levels depend on one measured hysteresis band of one rig geometry. ·
  related: HW.T16 · [H07]
- **HW.N437** ASSUME · `tests_hardware/device_scripts/isl29125_lighting_scenarios.py:32-40` —
  "_BASELINE_TOL = 0.35"; "_MAX_SAMPLE_GAP_S = 8.0"; "_SWITCH_HOLD_S = 8.0 # the derived 2 cycles +
  settle + a 1s sample interval, with margin" — Tolerances and timing thresholds, basis partly stated.
  (low) · [H07]
- **HW.N438** SETTLED · `tests_hardware/device_scripts/isl29125_lighting_scenarios.py:23-25` — "The
  NeoPixel is driven RAW on purpose ... Nothing else contends for the pixel in an isolated run, so no
  arbitration is bypassed" — Deliberate bypass of NeopixelDriver. (low) · [H07]
- **HW.N439** ASSUME · `tests_hardware/device_scripts/isl29125_lighting_scenarios.py:239-241` — "an
  inherited range is how the first version of this file passed while proving nothing" — Engagement
  floors (min_switches, both ranges, ≥5 total switches) added after a vacuous pass. · related: HW.T05 ·
  [H07]
- **HW.N440** INVAR · `tests_hardware/device_scripts/isl29125_lighting_scenarios.py:309-315` —
  "reader.cfgmgr._cache[\"AutoRangeDwell\"] = 0.0" — Primed config (no flash write), but scenario
  behaviour differs from the shipped AutoRangeDwell default. (low) · [H07]

## tests_hardware/device_scripts/isl29125_mechanism_envelope.py

- **HW.N441** RISK · `tests_hardware/device_scripts/isl29125_mechanism_envelope.py:100-105, 150-196` —
  "this script calls _set_dict_cfg, whose persist leg is a real write_config() ... Scratch filename";
  nine `_set_dict_cfg` calls — ~9 real RP2040 flash writes under `neopixel_sweep` only (no
  persistence_write gate), to a scratch `config_HWTEST_ISL29125.cfg` left on the board. · covered-by:
  HW.S05 · [H07]
- **HW.N442** ASSUME · `tests_hardware/device_scripts/isl29125_mechanism_envelope.py:22-31` —
  "OVERLAP_LEVEL = 4 # ~150 lx on this rig"; "MAX_RANGE_STEP = 0.25 ... the applied ratio's band is
  20-34 around a nominal 26.67"; "The accuracy question itself lives in Part M.1.6" — Rig-dependent
  levels and a relative gain bound derived from the driver's band. · related: HW.T16 · [H07]
- **HW.N443** ASSUME · `tests_hardware/device_scripts/isl29125_mechanism_envelope.py:170-172, 215-217` —
  "The retired ramp sweep tried it on a moving ramp, where the light's own ~22%/s rise swamps the step";
  "this rig really does exceed 10000 lx at ~20mm"; "one leg cannot reach it: a guard, not a proof" — W13
  check on one leg is a guard only; rig geometry assumption. · related: HW.T05 · [H07]

## tests_hardware/device_scripts/isl29125_mock_conformance_probe.py

- **HW.N444** MIRROR · `tests_hardware/device_scripts/isl29125_mock_conformance_probe.py:1-3` — "run
  IDENTICALLY against the real chip and the twin's fake - it talks only raw machine.I2C, the one layer
  both implement" — Real-vs-twin conformance oracle; diffed by isl29125_conformance.py (PHYSICAL_KEYS
  excluded). · related: TWIN.T01 · [H07]
- **HW.N445** SUPPRESS · `tests_hardware/device_scripts/isl29125_mock_conformance_probe.py:11-14` —
  "except (AttributeError, ValueError, OSError): _WDT = None # the twin's machine.py has no real
  watchdog to feed" — Twin fidelity gap (no WDT) papered by a swallow. (low) · related: TWIN.T02 · [H07]
- **HW.N446** ASSUME · `tests_hardware/device_scripts/isl29125_mock_conformance_probe.py:54-56` — "the
  twin's Timer is a real asyncio task, so one modelled conversion cycle costs the same wall-clock as a
  real one" — Timing parity assumption between twin and silicon. (low) · [H07]
- **HW.N447** RISK · `tests_hardware/device_scripts/isl29125_mock_conformance_probe.py:114-129` —
  "p.wr(REG_C1, [0xFF])"; "p.wr(0x0F, [0x5A])" — Writes all-ones and an undefined register on the live
  part; relies on the teardown reset (:245-251). (low) · [H07]

## tests_hardware/device_scripts/reboot_persist_read.py

- **HW.N448** ASSUME · `tests_hardware/device_scripts/reboot_persist_read.py:1-3, 10-11` — "Runs after a
  genuine machine.reset()"; "_PATH = \"config_HWTEST_REBOOT.cfg\"" — Scratch config file persists on the
  board after the test. (low) · related: HW.T03 · [H07]

## tests_hardware/device_scripts/reboot_persist_write.py

- **HW.N449** INVAR · `tests_hardware/device_scripts/reboot_persist_write.py:3, 21-24` — "write_config()
  stages and spawns the flash write as its own task (Part F.2) ... asyncio.run() would tear the loop
  down with the flush still queued" — Deferred-write contract: any script that writes config must
  `flush_pending()`. · related: XCUT.T10 · [H07]
- **HW.N450** SUPPRESS · `tests_hardware/device_scripts/reboot_persist_write.py:17` — "await
  mgr.write_config({\"Marker\": _MARKER_VALUE}, _SCHEMA)" — One owned RP2040 flash write, gated
  host-side by `persistence_write` (flash/test_reboot_persistence.py:29). · covered-by: HW.T01 · [H07]

## tests_hardware/device_scripts/scd30_plausibility_read.py

- **HW.N451** ASSUME · `tests_hardware/device_scripts/scd30_plausibility_read.py:1-3, 12` — "CO2
  200-10000 ppm, below the datasheet's 400 floor since sub-400 readings are real and unremarkable" —
  Stated rationale for 200; the bench REST test uses 400 (bench/test_rest_endpoints_over_sta.py:18). ·
  [H07]
- **HW.N452** ASSUME · `tests_hardware/device_scripts/scd30_plausibility_read.py:21-23` —
  "SCD30_Reader(i2c1, 11, trigger_sec=3, max_module_error=999, fram=None, debug=None)"; "read_loop()" —
  Full reader started without the cfgmgr priming other plausibility scripts use; whether its init
  touches the production config file or pushes defaults to SCD30 NVM is not stated. (low) · related:
  HW.S02 · [H07]
- **HW.N453** ASSUME · `tests_hardware/device_scripts/scd30_plausibility_read.py:15, 36` — "_SETTLE_S =
  45.0 # datasheet-bound response-time window"; "the sensor's own ~2s default interval" — Assumes the
  NVM MeasInt is 2 s (manual tier can leave 7). · covered-by: HW.S03 · [H07]

## tests_hardware/device_scripts/scd30_real_irq_edge.py

- **HW.N454** LIMIT · `tests_hardware/device_scripts/scd30_real_irq_edge.py:2-3, 11-13` — "Can't fully
  disambiguate a real IRQ from the software fallback purely from software"; "comfortably above the
  SCD30's own ~2s natural interval" — Pass does not prove the IRQ path; assumes MeasInt ≈ 2 s. ·
  covered-by: HW.S03 · [H07]
- **HW.N455** ASSUME · `tests_hardware/device_scripts/scd30_real_irq_edge.py:16-31` — (no `wdt.feed()`
  in the script) — Relies on finishing inside run_isolated's 8 s WDT (5 s deadline + teardown). (low) ·
  related: HW.S09 · [H07] ⟨quote not matched at the anchor⟩

## tests_hardware/device_scripts/scd30_same_device_rw_concurrency.py

- **HW.N456** DRIFT · `tests_hardware/device_scripts/scd30_same_device_rw_concurrency.py:1-2` — "the ONE
  script allowed to issue a real NVM-persisted write to the SCD30" —
  bus_concurrency_scd30_write_vs_siblings.py:75 also writes SCD30 NVM (the gated extra write). (low) ·
  related: HW.T01 · [H07]
- **HW.N457** RISK · `tests_hardware/device_scripts/scd30_same_device_rw_concurrency.py:66-67` — "await
  scd.set_ambient_pressure(1013)" — Persists 1013 hPa ambient-pressure compensation in SCD30 NVM
  regardless of the board's configured AmbPres; no restore. · related: HW.T03 · [H07]
- **HW.N458** ASSUME · `tests_hardware/device_scripts/scd30_same_device_rw_concurrency.py:17-20` —
  "which read back as a stuck CO2=141.99 on every iteration. A few intervals are enough to clear it" —
  Settle constant from one observation (duplicated in bus_concurrency_same_device_scd30.py). · [H07]
- **HW.N459** ASSUME · `tests_hardware/device_scripts/scd30_same_device_rw_concurrency.py:27` — "a real
  soft reset - RAM/operating-state only, not an NVM write, safe every run" — Datasheet claim behind
  unmarked setup(). (low) · [H07]

## tests_hardware/device_scripts/scheduler_saturation_drop.py

- **HW.N460** LIMIT · `tests_hardware/device_scripts/scheduler_saturation_drop.py:3, 43, 54-55` — "Widen
  BUSY_WAIT_MS if `dropped` comes back 0"; "if all_self_healed: print(\"RESULT: PASS dropped=...\")" —
  Passes even when no callback was dropped, so self-healing may never have been exercised. · related:
  HW.T05 · [H07]

## tests_hardware/device_scripts/serving_at_default_gc.py

- **HW.N461** RISK · `tests_hardware/device_scripts/serving_at_default_gc.py:93` —
  "create_task(sensortask_dev.main())" — Full production main (WiFi, FRAM, config) for up to 600 s from
  a device script. · covered-by: HW.T17 · [H07]
- **HW.N462** LIMIT · `tests_hardware/device_scripts/serving_at_default_gc.py:24-26` —
  "gc.threshold(-1)" — Measures at the reactive default, not the firmware's 32768 (by design, the (e)
  stage). (low) · [H07]
- **HW.N463** SUPPRESS · `tests_hardware/device_scripts/serving_at_default_gc.py:46-63` — "Re-raises
  unchanged, so the served outcome is exactly production's"; "setattr(WebserverService, _name,
  _dumping_on_failure(...))" — Class-level route patching; only uncaught MemoryErrors get a map
  (caught-and-degraded ones are found by the host grep). · related: TEST.T18 · [H07]
- **HW.N464** ASSUME · `tests_hardware/device_scripts/serving_at_default_gc.py:27-33, 72` —
  "_QUIET_TO_LEAVE = 10 # consecutive idle polls; the host's own gaps between levels stay below this";
  "webserver._open_conns.value" — Phase detection coupled to host pacing and a private counter. (low) ·
  [H07]

## tests_hardware/device_scripts/sgp40_fram_backup_restore.py

- **HW.N465** RISK · `tests_hardware/device_scripts/sgp40_fram_backup_restore.py:57-81, 89-92` —
  "allocating its own chunk 0 at the same physical address reader1's did" — Writes an SGP40 VOC-state
  backup into production's chunk 0 (whatever module owns it in production). · covered-by: HW.T17 · [H07]
- **HW.N466** ASSUME · `tests_hardware/device_scripts/sgp40_fram_backup_restore.py:54` —
  "asy_i2c_driver.I2C(1, 15, 14, frequency=50000)" — Omits `timeout=200000` on the shared i2c1
  singleton. · covered-by: HW.S18 · [H07]
- **HW.N467** LIMIT · `tests_hardware/device_scripts/sgp40_fram_backup_restore.py:2-3, 34-35, 89-91` —
  "a second reader simulates a fresh boot"; "stands in for the real ntp.ntp_issynced" — Reboot and NTP
  sync are simulated; `_FixedSource` compensation defaults (Table 10). · [H07]
- **HW.N468** ASSUME · `tests_hardware/device_scripts/sgp40_fram_backup_restore.py:15, 76-77` — "60s to
  the first natural BackupPeriod=1min trigger"; "its BackupPeriod default of 1 min is what BACKUP_WAIT_S
  is sized around" — Timing coupled to the driver's schema default. (low) · [H07]

## tests_hardware/device_scripts/sgp40_general_call_reset_hazard.py

- **HW.N469** ASSUME · `tests_hardware/device_scripts/sgp40_general_call_reset_hazard.py:31-38` —
  "advancing measurement means >= 2 distinct CO2 values; one unchanging value means it silently stopped
  (an undocumented general-call reset). A CRC failure cannot catch this" — Silent-stop oracle is ≥2
  distinct CO2 values over the run. · related: HW.T05 · [H07]
- **HW.N470** INVAR · `tests_hardware/device_scripts/sgp40_general_call_reset_hazard.py:49-51, 110` —
  "this group's one NVM-persisted write happens once per session in flash/conftest.py's ... fixture";
  "real production path: ends with _reset()'s general-call broadcast" — Depends on the host fixture;
  issues 8 real general-call resets on i2c1. · related: HW.T01 · [H07]

## tests_hardware/device_scripts/sgp40_voc_algorithm_quality.py

- **HW.N471** ASSUME · `tests_hardware/device_scripts/sgp40_voc_algorithm_quality.py:15-18, 58` — "45s
  documented blackout + margin"; "MAX_SINGLE_STEP_JUMP = 300 # generous relative to the algorithm's own
  adaptive-lowpass smoothing"; "1s fixed period - the algorithm's own sampling interval assumption" —
  Sanity thresholds; "not an accuracy claim". (low) · [H07]
- **HW.N472** ASSUME · `tests_hardware/device_scripts/sgp40_voc_algorithm_quality.py:46` —
  "asy_i2c_driver.I2C(1, 15, 14, frequency=50000)" — Omits `timeout=200000` on the shared i2c1
  singleton. · covered-by: HW.S18 · [H07]
- **HW.N473** SUPPRESS · `tests_hardware/device_scripts/sgp40_voc_algorithm_quality.py:91` — "# noqa:
  B905 - MicroPython zip() rejects strict=" — Platform-driven suppression. (low) · [H07]

## tests_hardware/device_scripts/system_debug_level_raise_for_boot_log_check.py

- **HW.N474** RISK · `tests_hardware/device_scripts/system_debug_level_raise_for_boot_log_check.py:9-10, 17-18, 43-44`
  — "_SYS_SCHEMA ... ((\"DebugLevel\", \"int\", 0, 0, 5, None),)"; "_SYS_PATH = \"config_SYSTEM.cfg\"" —
  Writes the PRODUCTION SYSTEM config file through a one-field schema; effect on the file's other keys
  is not stated. (low) · related: HW.T03 · [H07]
- **HW.N475** ASSUME ·
  `tests_hardware/device_scripts/system_debug_level_raise_for_boot_log_check.py:34-36` — "the restore
  phase then drives DebugLevel to 0, which is the state that silently breaks the rest of the bench tier"
  — Bench-tier log-string oracles depend on DebugLevel ≥ 3. · covered-by: HW.S14 · [H07]
- **HW.N476** ASSUME ·
  `tests_hardware/device_scripts/system_debug_level_raise_for_boot_log_check.py:12-13` — "_BACKUP_PATH =
  \"config_HWTEST_DEBUGLEVEL_BACKUP.cfg\""; "_VERBOSE_LEVEL = 3 # print_log.py's _LOG_ONCE" — Backup
  file left on board; level constant mirrors print_log. (low) · [H07]

## tests_hardware/device_scripts/system_debug_level_restore_after_boot_log_check.py

- **HW.N477** INVAR ·
  `tests_hardware/device_scripts/system_debug_level_restore_after_boot_log_check.py:1-3, 30-31` — "Run
  from a `finally` block in the driving test"; "unflushed, the restore reports success while the on-disk
  DebugLevel keeps whatever the raise phase left there" — Restore correctness depends on flush + caller
  discipline. (low) · [H07]

## tests_hardware/device_scripts/system_service_restarts_a_real_dead_task.py

- **HW.N478** MIRROR · `tests_hardware/device_scripts/system_service_restarts_a_real_dead_task.py:34-36`
  — "task_errors capped at 200 ... (_TASK_FAIL_MAX=300, _TASK_FAIL_INCREMENT=100 per cycle)" —
  Supervisor constants copied into a timing window (~3.5 s). · related: XCUT.T02 · [H07]

## tests_hardware/device_scripts/timer_alarm_pool_exhaustion.py

- **HW.N479** SUPPRESS · `tests_hardware/device_scripts/timer_alarm_pool_exhaustion.py:12, 25-28` — "#
  noqa: B007"; "except Exception: pass" — Lint suppression and swallowed deinit errors. (low) · [H07]

## tests_hardware/device_scripts/uart_crossover_exchange.py

- **HW.N480** INVAR · `tests_hardware/device_scripts/uart_crossover_exchange.py:4-6` — "per C.8's
  standing constraint that a hazard-tier test must not touch the RP2040's own flash filesystem. Both
  loggers are RAM-only" — Wear rule for UART scripts, by convention. (low) · related: HW.T01 · [H07]
- **HW.N481** MIRROR · `tests_hardware/device_scripts/uart_crossover_exchange.py:1-2, 26-33` —
  "GP0<->GP9, GP1<->GP8"; "Mirrors sensortask_dev.py's own pair: 2ms while a transaction is in flight,
  50ms while the line is idle" — Pins, payload 48, timeout 1000 ms, 115200 baud, poll rates hand-copied
  from the generated dev module / dev.toml (same in uart_crossover_recovery.py:26-33). · related: HW.T08
  · [H07]
- **HW.N482** ASSUME · `tests_hardware/device_scripts/uart_crossover_exchange.py:43-45` — "Three data
  chunks: enough to exercise a real multi-frame train's chunk indexing ... without spending a minute of
  wire time on the maximum 254" — Docstring says "maximum-length train" (:1) but only 3 chunks are sent.
  (low) · [H07]

## tests_hardware/device_scripts/uart_crossover_recovery.py

- **HW.N483** LIMIT · `tests_hardware/device_scripts/uart_crossover_recovery.py:4-6, 57-64, 126-133` —
  "a future external injector implements the same three methods"; "desync() re-inits it at a baud rate
  the other end does not share" — `desync()` is defined but never called — the baud-mismatch fault is
  not exercised; "within the specified window" is not timed. · related: HW.T05 · [H07]

## tests_hardware/device_scripts/uart_idle_poll_rate.py

- **HW.N484** ASSUME · `tests_hardware/device_scripts/uart_idle_poll_rate.py:17-20` — "_MIN_RATIO = 5 #
  measured 20.6x"; "the bound is deliberately loose on absolute counts" — Threshold from one
  measurement; absolute count bounded to ±2× of 60. · related: UART.T10 · [H07]
- **HW.N485** SUPPRESS · `tests_hardware/device_scripts/uart_idle_poll_rate.py:32, 35, 38, 57` — "#
  type: ignore[attr-defined]"; "uart.poller = counter # type: ignore[assignment]" — Four type
  suppressions for the counting poller wrapper. (low) · [H07]

## tests_hardware/device_scripts/uart_read_never_blocks_the_loop.py

- **HW.N486** ASSUME · `tests_hardware/device_scripts/uart_read_never_blocks_the_loop.py:15-19` —
  "~4.4ms measured"; "~280us measured worst case" — `_CLAMPED_MAX_US = wire/3` sits between two single
  measurements. · related: UART.T10 · [H07]
- **HW.N487** RISK · `tests_hardware/device_scripts/uart_read_never_blocks_the_loop.py:42-43, 53-58` —
  "while not any(ev & select.POLLIN for _, ev in poller.ipoll(0)): pass" — Unbounded busy-waits with no
  WDT feed: a missing jumper ends in a WDT reset, not a FAIL line. (low) · [H07]

## tests_hardware/device_scripts/uart_link_under_concurrent_system_load.py

- **HW.N488** DRIFT · `tests_hardware/device_scripts/uart_link_under_concurrent_system_load.py:144-2 vs 146-148 (agent cited tests_hardware/device_scripts/uart_link_under_concurrent_system_load.py:1-2 vs 146-148)`
  — "both I2C buses" vs "SCD30 and SGP40 both sit on i2c1 on this bench ... the loop labelled i2c0 is
  really \"the other device on the shared bus\"" — i2c0 is never loaded; counters are mislabelled. (low)
  · [H07] ⟨re-anchored: quote found at line 144⟩
- **HW.N489** ASSUME · `tests_hardware/device_scripts/uart_link_under_concurrent_system_load.py:30-36` —
  "_MIN_TRANSFERS = 20 # measured 58 unloaded-by-comparison"; "Measured worst case under this load is
  ~114ms" — Floors from single measurements. · related: UART.T10 · [H07]
- **HW.N490** DRIFT · `tests_hardware/device_scripts/uart_link_under_concurrent_system_load.py:107-110`
  — "a 6144 B swing that swamped the 2048 B bound (queue F7)" — Deleted queue row cited. · covered-by:
  DOC.S06 · [H07]
- **HW.N491** LIMIT · `tests_hardware/device_scripts/uart_link_under_concurrent_system_load.py:95-101, 228`
  — "except MemoryError: load.alloc_failures += 1 ... gc.collect()" — Allocation failures in the churn
  load are caught, counted and only printed, never asserted. (low) · related: TEST.T18 · [H07]
- **HW.N492** ASSUME · `tests_hardware/device_scripts/uart_link_under_concurrent_system_load.py:124-128, 141`
  — "prove it under MicroPython's own real default (no proactive collection)"; "dev_legacy/README.md's
  wiring: i2c0 (13, 12), i2c1 (15, 14), SPI0 (2, 3, 4) with FRAM CS=5" — Pins cited from the legacy
  bench doc rather than dev.toml. · related: HW.T08 · [H07]
- **HW.N493** LIMIT · `tests_hardware/device_scripts/uart_link_under_concurrent_system_load.py:216-220`
  — "real per-transaction retention would be thousands of bytes, far above this bound" — Heap-growth
  check skipped if the one-third sample was never taken; 2048 B bound. (low) · [H07]

## tests_hardware/device_scripts/watchdog_starvation_reset.py

- **HW.N494** MIRROR · `tests_hardware/device_scripts/watchdog_starvation_reset.py:10` — "print(\"WDT
  armed, starving now\")" — Banner string matched by flash/test_watchdog_starvation.py:13. (low) · [H07]

## tests_hardware/device_scripts/wifi_country_hostname_edge_values.py

- **HW.N495** LIMIT · `tests_hardware/device_scripts/wifi_country_hostname_edge_values.py:14-16, 31-35, 40`
  — "PASS accepted"; "PASS raised"; "RESULT: interpreter survived both edge-value calls" — Every branch
  prints PASS and no host wrapper runs it (orphan). · covered-by: HW.S16 · [H07]

## tests_hardware/device_scripts/wifi_reconnect_after_failed_attempts_repro.py

- **HW.N496** MIRROR ·
  `tests_hardware/device_scripts/wifi_reconnect_after_failed_attempts_repro.py:9-10, 109` — "REAL_SSID =
  \"sensors-bench-ap\""; "REAL_PW = \"<redacted: bench PSK, HW.T11>\""; "password=\"12345678\"" —
  Committed bench SSID/PSK and hotspot password (copy #5) — consistency item vs the run-time
  `bench.ap_password()` convention. · covered-by: HW.S08 · [H07] ⟨quote not matched at the anchor⟩
- **HW.N497** LIMIT · `tests_hardware/device_scripts/wifi_reconnect_after_failed_attempts_repro.py:1-3`
  — "one-off repro ... (NOT part of the routine test suite)"; "recover afterward via hard_reset()" —
  Orphan diagnostic; leaves the board on an ad-hoc WLAN object. · covered-by: HW.S16 · [H07]
- **HW.N498** RISK · `tests_hardware/device_scripts/wifi_reconnect_after_failed_attempts_repro.py:76, 134`
  — "max_polls=240 ... up to 120s"; "max_polls=1200 ... up to 600s" — No WDT feed anywhere; if main.py
  had armed the 8 s watchdog before the attach, the board resets mid-diagnostic (same shape as the other
  repro). · related: HW.S09 · [H07]
- **HW.N499** MIRROR · `tests_hardware/device_scripts/wifi_reconnect_after_failed_attempts_repro.py:13, 15, 67, 87-88, 96`
  — "HOTSPOT_HOSTNAME = \"sensornode-dev\""; "_STAT_OBTAINING_IP = 2 # matches asy_wifi_service.py's own
  module-level constant"; "pm=0xA11140"; "wifi_refresh_sec=5s cadence" — src constants copied into a
  diagnostic (hostname differs from both DUT candidates in conftest.py). (low) · [H07]

## tests_hardware/device_scripts/wifi_service_reconnect_repro.py

- **HW.N500** RISK · `tests_hardware/device_scripts/wifi_service_reconnect_repro.py:12-15, 70-78, 89, 119`
  — "writing it is what stranded the bench (QUEUE F1)"; "The scratch file holds a full WIFI config, real
  password included"; "up to 3 minutes"; "up to 10 minutes" — Up to ~13 min with no WDT feed; a watchdog
  reset skips `_drop_scratch()`, leaving `config_HWTEST_WIFI.cfg` with the real password on the board. ·
  covered-by: HW.S09 · [H07]
- **HW.N501** LIMIT · `tests_hardware/device_scripts/wifi_service_reconnect_repro.py:1-3` — "diagnostic
  script #2 (NOT part of the routine test suite)" — Orphan diagnostic, run by hand. · covered-by: HW.S16
  · [H07]
- **HW.N502** MIRROR · `tests_hardware/device_scripts/wifi_service_reconnect_repro.py:24, 101, 133` —
  "_PHASE_NAMES = {0: \"STA_SEEKING\", 1: \"STA_ESTABLISHED\", 2: \"HOTSPOT\", 3: \"DEACTIVATED\"}";
  "`data` is the terminating exception, set by asyncio/core.py's run_until_complete()" — Copies src
  phase values and relies on a MicroPython asyncio internal. (low) · [H07]
- **HW.N503** RISK · `tests_hardware/device_scripts/wifi_service_reconnect_repro.py:82-99` —
  "overwriting SSID with a garbage value"; "if phase == 2: reached_hotspot = True" — Drives the live
  board into hotspot mode (bench link lost) until the restore path runs. (low) · related: HW.T03 · [H07]

## tests_hardware/README.md

- **HW.N504** SETTLED · `tests_hardware/README.md:11-16` — "needs the project owner's go-ahead first,
  given directly in that session's own conversation" — Restates CLAUDE.md's per-conversation hardware
  gate as the precondition of this whole tier. · related: HW.T14 · [H08]
- **HW.N505** INVAR · `tests_hardware/README.md:27-29` — "Never `scripts/build_firmware.py wozi` against
  this bench" — Only a `dev` build may be flashed; wozi's hardcoded pins don't match the bench
  (CLAUDE.md WoZi rule; queue D3). · related: PAR.S13 · [H08]
- **HW.N506** LIMIT · `tests_hardware/README.md:40-50` — "not provisioned by any `setup_toolchain.py`
  tier because it is physical, not software" — The NeoPixel→ISL29125 sweep rig is a physical
  precondition; without it the two gated light tests fail outright (~10 min when run). · related: HW.T13
  · [H08]
- **HW.N507** TODO · `tests_hardware/README.md:47-49` — "run that once, record the distance here, and
  the automated pair becomes meaningful" — The rig geometry/distance is not yet recorded in this file
  (queue M1 still OPEN). · [H08]
- **HW.N508** RISK · `tests_hardware/README.md:62-63` — "`scripts/mpremote_connect.sh` still defaults to
  `/dev/ttyACM0`, making it the one entry point a re-enumeration can still strand" — Only entry point
  not using by-id resolution; may hit another device's port. · covered-by: HW.S19 · [H08]
- **HW.N509** SETTLED · `tests_hardware/README.md:64-74` — "it no longer skips on its own; a real bench
  ... always has a readable password" — Stage 6 of role reversal now always runs (password read live via
  `nmcli --show-secrets`); env var only overrides. · related: HW.S25, HW.T11 · [H08]
- **HW.N510** INVAR · `tests_hardware/README.md:85-95` — "Soak tests (long_soak marker) are NEVER
  bundled into either suite runner above" — Soak tiers and the ~12.4-day rollover wait run only by
  deliberate separate invocation. · related: HW.T13 · [H08]
- **HW.N511** DRIFT · `tests_hardware/README.md:86-87` — "see tests_hardware/conftest.py's own
  SOAK_TIER_SECONDS" — Points at conftest.py; the constant lives in `soak_tiers.py`. · covered-by:
  HW.S17 · [H08]
- **HW.N512** LIMIT · `tests_hardware/README.md:162-165` — "a notification signal landing mid-scenario
  is indistinguishable from a bad reading" — Rig faults (ambient above low range, a notification on the
  pixel) masquerade as driver failures. · [H08]
- **HW.N513** ASSUME · `tests_hardware/README.md:177-184` — "a register probe read 65444/65272/65323 and
  was briefly taken for real saturation" — Dated bench readings: latched WS2812 ~2000 lx, parked dark
  ~40 lx (10.7% of low range), irq_edge passes in 0.60 s parked dark. · [H08]
- **HW.N514** LIMIT · `tests_hardware/README.md:185-190` — "The breakout carries its own red LEDs, so
  red reads systematically high" — Cover state and on-breakout LEDs bias readings; nothing asserts
  channel equality or hue. · [H08]
- **HW.N515** ASSUME · `tests_hardware/README.md:226-227` — "this rig really does exceed 10000 lx at ~20
  mm" — Envelope test asserts `Overrange` true at full white based on an unrecorded (~20 mm) geometry. ·
  - (low) · [H08]
- **HW.N516** INVAR · `tests_hardware/README.md:240-242` — "its result depended on test ORDER, with the
  script itself unchanged" — Device scripts must provide their own light; ordering dependence was found
  once. · related: HW.T05 · [H08]
- **HW.N517** INVAR · `tests_hardware/README.md:243-245` — "wrote that cache over the board's real
  `config_ISL29125.cfg`: six silent flash writes per run" — Scripts must restore/side-step shared state
  (light, config files, FRAM chunks); precedent of silent flash wear. · related: HW.S05 · [H08]
- **HW.N518** INVAR · `tests_hardware/README.md:246-251` — "Assert a minimum engagement beside every
  ceiling" — `min_switches`/must-use-both-ranges guards against vacuous passes. · covered-by: HW.T05 ·
  [H08]
- **HW.N519** INVAR · `tests_hardware/README.md:252-256` — "`write_config()` only *stages* ... a script
  that returns before the flush loses the write" — `await flush_pending()` after any config write;
  enforced per manager by `tests_scripts/test_device_script_config_flush.py`. · related: CORE.T02 ·
  [H08]
- **HW.N520** INVAR · `tests_hardware/README.md:262-270` — "every serial check you make to diagnose it
  re-causes the symptom" — `exec`/`run` stop `main.py`; armed WDT resets ~8 s later; diagnose passively
  via `hard_reset()`+`tail_log()`, `SysUptime`. · covered-by: HW.T06 · [H08]
- **HW.N521** INVAR · `tests_hardware/README.md:279-283` — "assert the property your feature owns, not
  that every client is served" — Ceiling-reaching tests assert per-answer correctness plus a floor on
  answered count. · related: HW.T05 · [H08]
- **HW.N522** INVAR · `tests_hardware/README.md:330-335` — "Verify the image before its figures count."
  — lwIP macros, `check_lwip_ensemble()`, `/system` buildDate; local-only images reverted at once. ·
  related: HW.T19, HW.T16 · [H08]
- **HW.N523** LIMIT · `tests_hardware/README.md:337-340` — "assertion messages carry only
  `output[-2000:]` of device output" — Probabilistic failures near the wall; a one-boot sweep loses
  which level broke. · [H08]
- **HW.N524** INVAR · `tests_hardware/README.md:342-353` — "since `run_isolated()` leaves `main.py`
  stopped, the test restores the board" — Ceiling-holding needs five layered measures and
  `restore_board_to_serving()` in `finally`. · related: HW.T12 · [H08]
- **HW.N525** LIMIT · `tests_hardware/README.md:363-364` — "after a failed walk it drains one slot
  best-effort" — Ceiling probe's failure path drain is best effort. · related: HW.T12 (low) · [H08]
- **HW.N526** INVAR · `tests_hardware/README.md:365-378` — "Pinned by the pytest tier." — Probe/holder
  timing contracts enforced by `test_request_timeout_ceiling.py`, `test_ceiling_probe.py`,
  `test_bench_harness_helpers.py`. · related: HW.T12 · [H08]
- **HW.N527** ASSUME · `tests_hardware/README.md:383-384` — "a watchdog reset ~9 s after an early attach
  is the likely, unconfirmed cause of one dead run" — Stated as unconfirmed; BACKLOG.md:400-403 (item
  44) says the mechanism is already measured (item 12). · covered-by: HW.S19 · [H08]
- **HW.N528** INVAR · `tests_hardware/README.md:387-391` — "read `machine.reset_cause()` over `mpremote exec`
  before anything flashes or reboots the board" — Bench traps: reset_cause first; `pkill -f` self-match;
  don't edit tools/scripts between chained runs. · related: HW.T05 · [H08]
- **HW.N529** ASSUME · `tests_hardware/README.md:443-445` — "the board may need reflashing before any of
  this runs" — Skip guards name a firmware predating a `src/` change; no image identity check. ·
  related: HW.T19 · [H08]
- **HW.N530** INVAR · `tests_hardware/README.md:446-456` — "A device script's every wait must stay
  inside its own watchdog window" — Crossover scripts poll `task.done()` in bounded steps and use
  `UART_Comm.clear()`; else a link fault reports as a reset. · [H08]
- **HW.N531** SETTLED · `tests_hardware/README.md:472-478` — "clears its chunk at the START, never at
  the end ... Residue is the accepted outcome" — Error-log device scripts wipe their chunk first;
  `fram_error_log_reset_race_verify.py` is the one exception. · related: HW.T02 · [H08]
- **HW.N532** INVAR · `tests_hardware/README.md:491-500` — "use the genuinely passive
  `Board.is_device_present()` ... for any liveness poll" — `exec`/`is_reachable()` self-reset the heap;
  `is_reachable()` stays mpremote-based deliberately. · related: HW.S14 · [H08]
- **HW.N533** DRIFT · `tests_hardware/README.md:501-504` — "Does `machine.soft_reset()` reset the
  hardware counter `time.ticks_ms()` reads from?" — Still listed as open and "deliberately uses
  `board.exec()`"; BACKLOG.md:237-249 (item 12) answered it 2026-09-11 (no; the WDT reset ~8 s after
  each exec zeroes the counter) and queue G6 says the exec-poll design cannot measure. · covered-by:
  HW.S17 · [H08]
- **HW.N534** ASSUME · `tests_hardware/README.md:505-506` — "`BUSY_WAIT_MS`/`TIMER_PERIOD_MS` are a
  starting guess, not measured on real hardware" — Scheduler-saturation script constants unmeasured. ·
  [H08]
- **HW.N535** SUPPRESS · `tests_hardware/README.md:507-510` — "is `@pytest.mark.skip` pending this;
  implement once a concrete mechanism ... is confirmed" — Spoofed off-subnet DNS test skipped "pending",
  yet it is the one entry in `KNOWN_PERMANENT_SKIPS` (`scripts/_require_clean_hardware_run.sh:10`). ·
  related: HW.T13 · [H08]
- **HW.N536** ASSUME · `tests_hardware/README.md:514-519` — "the authoring sandbox had no systemd/D-Bus
  to actually run NetworkManager against and confirm live" — `nmcli -g IP4.ADDRESS/GATEWAY` output shape
  unverified live. · related: HW.T12 · [H08]
- **HW.N537** ASSUME · `tests_hardware/README.md:565-586` — "that's an implicit precondition of the
  whole tier, not stated anywhere until this entry" — Bench tier requires live `DebugLevel` ≥3 (NTP test
  5); at 0 `dut_ip` times out (2026-09-04: 2 failures + 48 errors). · covered-by: HW.S14 · [H08]
- **HW.N538** INVAR · `tests_hardware/README.md:610-615` — "`kick_all_stations()` before the post-flash
  reconnect attempt, every time" — Same stale-station hazard after every `picotool load` reflash. ·
  [H08] ⟨quote not matched at the anchor⟩
- **HW.N539** INVAR · `tests_hardware/README.md:640-643` — "first re-verify the test's own check is
  asking the right question of the right endpoint/field" — Lesson from a `"Mode"` field read from the
  wrong endpoint. · related: HW.T05 · [H08]
- **HW.N540** INVAR · `tests_hardware/README.md:650-654` — "each calling `input()` and hanging forever"
  — `manual/` files named away from `test_*.py`; naming is the structural backstop. · [H08]
- **HW.N541** DRIFT · `tests_hardware/README.md:672-680` — "The existing `RogueUdpResponder`-based
  garbage-response tests are unaffected" — Same bullet says DNAT-to-loopback does not deliver locally,
  yet the rogue tests rely on that redirect (also :792-799 "not ... verified live"). · covered-by:
  HW.S13 · [H08]
- **HW.N542** OPENQ · `tests_hardware/README.md:679-681` — "the redirect didn't intercept traffic at all
  for one `hard_reset()` cycle, root cause not chased" — Unexplained DNAT quirk. · related: HW.S13 ·
  [H08]
- **HW.N543** DRIFT · `tests_hardware/README.md:708-711` — "against the physical MB85RS64V chip" — dev's
  FRAM is recorded as MB85RS2MTA (dev_legacy/README.md:44, devices/dev.toml). · covered-by: HW.S17 ·
  [H08]
- **HW.N544** DRIFT · `tests_hardware/README.md:748-750` — "**SCD30 has no live-push config fields at
  all** ... not a gap" — Repeated at :1129-1136, :1172-1174, :1239-1240; HW.S02 says SCD30 NVM is
  reachable over REST. · covered-by: HW.S02 · [H08]
- **HW.N545** LIMIT · `tests_hardware/README.md:752-759` — "**Still not automated even after this
  pass**" — No calibrated-accuracy test, no WS2812 validation, no genuine power-loss test of FRAM chunk
  logic. · [H08]
- **HW.N546** DRIFT · `tests_hardware/README.md:815-816` — "confirmed not overridden anywhere in
  `sensortask_wozi.py`" — `sensortask_<device>.py` is now generated; also :949
  "`sensortask_wozi.main()`". · related: DOC.T16 (low) · [H08]
- **HW.N547** INVAR · `tests_hardware/README.md:830-834` — "Every bench test that injects a network
  fault also calls `assert_no_task_ended()`" — Enforced by
  `tests_scripts/test_bench_no_task_ended_completeness.py`. · [H08]
- **HW.N548** RISK · `tests_hardware/README.md:836-848` — "reset the real, REST-exposed error/warning
  history (`PUT /status {\"ResetErrors\": true}`) before a fault-injecting test" — Standing policy of
  clearing live error history before and after tests, with no automatic prior snapshot. · covered-by:
  HW.S06 · [H08] ⟨quote not matched at the anchor⟩
- **HW.N549** LIMIT · `tests_hardware/README.md:857-864` — "documented as a deliberate non-assertion
  rather than a flaky one" — Some faults have no groundable log entry; retrofit "not extended to the
  rest of the tier". · related: HW.T05 · [H08]
- **HW.N550** INVAR · `tests_hardware/README.md:931-938` — "Never call `cfgmgr.setup()` in such scripts
  - that performs a real littlefs file write/read." — Isolated-driver priming pattern (valid/_cache);
  handover 5.3 says two scripts moved to a schema-derived cache. · [H08]
- **HW.N551** ASSUME · `tests_hardware/README.md:949-952` — "up to ~20s can pass with a connected IP but
  nothing on port 80" — Webserver starts only after `ntp_force_sync()` (20 s bound). · [H08]
- **HW.N552** INVAR · `tests_hardware/README.md:987-990` — "reading the actual IP still needs one
  `board.exec()` call (unavoidable), always immediately followed by `board.hard_reset()`" — `dut_ip`
  fixture's one unavoidable raw-REPL entry. · [H08]
- **HW.N553** INVAR · `tests_hardware/README.md:1018-1028` — "run `uv run python tests_hardware/manual/__main__.py`,
  never `runner.py` directly" — Running runner.py directly is a silent no-op (duplicate module
  instance). · [H08]
- **HW.N554** ASSUME · `tests_hardware/README.md:1065-1072` — "**Honesty note - neither test has been
  run against real hardware yet.**" — Seventh-pass tests flagged unverified; same notes at :1138-1140,
  :1176-1177, :1295-1296 — possibly stale since later runs (queue: gated run 2026-09-23; W4 2026-09-24).
  · related: HW.T16 (low) · [H08]
- **HW.N555** LIMIT · `tests_hardware/README.md:1088-1094` — "fires at exactly ONE fixed offset (0.3s
  in) - the one-write budget makes a real multi-offset sweep structurally impossible" — SCD30
  write-vs-siblings has no timing sweep. · [H08]
- **HW.N556** DRIFT · `tests_hardware/README.md:1096-1098` — "(i2c0: BMP3xx alone; i2c1:
  SCD30+SGP40+ISL29125)" — dev_legacy/README.md:48 lists an MPRLS on I2C0. · covered-by: HW.S12 · [H08]
- **HW.N557** MIRROR · `tests_hardware/README.md:1107-1111` — "that file's module docstring stated the
  invariant; nothing enforced it, which is why it drifted" — On-target `KNOWN_ADDRESSES` table is a
  hand-kept mirror of device addresses (SPECIFICATION.md:5970 checklist), unenforced. · related: HW.S12,
  HW.T08 · [H08]
- **HW.N558** SETTLED · `tests_hardware/README.md:1230-1240` — "Confirmed structural exceptions (no fix
  possible" — `lightCmdLED`, WS2812 timing, SCD30 IRQ/same-device write have no bench equivalent. ·
  related: HW.T09 · [H08]
- **HW.N559** LIMIT · `tests_hardware/README.md:1291-1293` — "SGP40's `SGPResetVOC` push is a thin test
  (it never asserts the reset's own effect)" — Known thin test. · related: HW.T05 · [H08]
- **HW.N560** SETTLED · `tests_hardware/README.md:1298-1312` — "**Standing design, project owner's own
  choice** (broadened from SCD30-only to all persistence, 2026-09-17)" — Two-flag persistence gate,
  AND-gated in code. · covered-by: HW.T13 · [H08]
- **HW.N561** SETTLED · `tests_hardware/README.md:1314-1323` — "the write a test OWNS, not one it is
  reached through" — Prerequisite writes stay unmarked; pinned by
  `tests_scripts/test_persistence_write_marker_completeness.py`. · covered-by: HW.T01 · [H08]
- **HW.N562** MIRROR · `tests_hardware/README.md:1328-1331` — "(`SGPResetVOC`, `ISLCalibrate` today —
  derive that set from the tags, never from this list going stale)" — Dispatch-only field list in prose
  mirrors `@web dispatch=true` tags; FRAM declared out of wear scope ("effectively unbounded"). ·
  related: HW.T01 · [H08]
- **HW.N563** RISK · `tests_hardware/README.md:1342-1349` — "A plain
  `scripts/run_bench_hardware_suite.sh` spends the prerequisite ones" — Default bench run spends flash
  writes (`joined_hotspot` stage-0/7, `_recover_stale_dut_credentials()`). · related: HW.T01 · [H08]
- **HW.N564** DRIFT · `tests_hardware/README.md:1354` — "(13 of the bench tier's 73 tests, 9 of the
  flash tier's 51, as of this writing" — Queue :73 says 85 bench tests. · covered-by: HW.S17 · [H08]
- **HW.N565** INVAR · `tests_hardware/README.md:1360-1378` — "`pytest_collection_modifyitems()` is the
  single deselection point ... No test checks either flag inline." — Marker placement derived from
  fixture dependents; `scd30_continuous_measurement_triggered` raises without the flag as backstop. ·
  covered-by: HW.T13 · [H08]
- **HW.N566** DRIFT · `tests_hardware/README.md:560-562` — "the same SSID (`\"SensorNode\"`, the config
  default)" — Hostname/hotspot SSID default is now `SensorStation<Name>` (devices/dev.toml:6). ·
  related: PAR.S11 (low) · [H08]

## REAL_HARDWARE_TEST_QUEUE.md (snapshot only; being updated by another session)

- **HW.N567** TODO · `REAL_HARDWARE_TEST_QUEUE.md:3-6` — "each row is deleted once its result is
  migrated ... and the file goes when the last row does" — Temporary doc; deletion trigger = last row
  migrated. · related: HW.T10 · [H08]
- **HW.N568** SETTLED · `REAL_HARDWARE_TEST_QUEUE.md:8-11` — "**Nothing here authorizes anything.**" —
  Queue is not a go-ahead; README is the technical reference. · [H08]
- **HW.N569** ASSUME · `REAL_HARDWARE_TEST_QUEUE.md:21` — "**30 rows owed.**" — Dated count (matches the
  30 IDs listed at the snapshot: D3 S3b T1 T2 T4 G8 N2 N3 R1 R2 R4-R7 R9 R13 G1 G3 G4 G6 G12 H1 S4 M1 F1
  F17 F18 W3 W4 W5). · related: DOC.T08 (low) · [H08]
- **HW.N570** ASSUME · `REAL_HARDWARE_TEST_QUEUE.md:46-48` — "`dev` image of tree `3062cc7`, `buildDate 2026-09-25T07:31:00Z`
  ... A sitting is in progress" — Board state duplicated in the handover (:17-18); "Check `buildDate`
  against the tree every time." · covered-by: DOC.S15 · [H08]
- **HW.N571** TODO · `REAL_HARDWARE_TEST_QUEUE.md:54-55` — "this is the script that stranded the bench,
  and the fix is structural but still unverified on silicon" — F1 in the one-sitting shortlist. ·
  related: HW.S09 · [H08]
- **HW.N572** SETTLED · `REAL_HARDWARE_TEST_QUEUE.md:66-74` — "**ANSWERED 2026-09-22: yes, after a clean
  default run.**" — D1 (spend flash/NVM writes only after a green default run) and D2 (rig in place) are
  standing owner answers, not re-asked. · related: HW.T13 · [H08]
- **HW.N573** DRIFT · `REAL_HARDWARE_TEST_QUEUE.md:73` — "A default run deselects 13 of the bench tier's
  85 tests and 9 of the flash tier's 51" — tests_hardware/README.md:1354 says 73 bench tests. ·
  covered-by: HW.S17 · [H08]
- **HW.N574** OPENQ · `REAL_HARDWARE_TEST_QUEUE.md:75` — "| D3 — **Which firmware image.**" | D3 status
  OPEN: confirmed every sitting; always a `dev` build of the tree under test. · related: HW.T19 · [H08]
- **HW.N575** INVAR · `REAL_HARDWARE_TEST_QUEUE.md:87-93` — "An unexplained entry is evidence only if
  the board's recent history allows it to be." — Run sheet Step 1: save `errcount` verbatim before
  anything writes; ask what last ran against the board. · covered-by: HW.T17 · [H08]
- **HW.N576** ASSUME · `REAL_HARDWARE_TEST_QUEUE.md:104-106` — "Both device-script fixes and the
  watchdog-starvation banner passed here on 2026-09-19" — Dated baseline for Step 4. · - (low) · [H08]
- **HW.N577** ASSUME · `REAL_HARDWARE_TEST_QUEUE.md:115-116` — "The last gated run (2026-09-23, clean,
  archive §7R.2) was image A, not the current tree." — Wear-gated run owed on the current tree. ·
  related: HW.T16 · [H08]
- **HW.N578** TODO · `REAL_HARDWARE_TEST_QUEUE.md:141` — "| S3b — ... | OPEN — D2 answered yes,
  2026-09-22: the rig is in place |" | S3b OPEN: `--allow-neopixel-sweep` light programs (~10 min),
  after M1. · [H08]
- **HW.N579** TODO · `REAL_HARDWARE_TEST_QUEUE.md:142` — "setting up and writing down the rig geometry
  S3b depends on" — M1 OPEN: interactive manual rig/geometry run. · [H08]
- **HW.N580** TODO · `REAL_HARDWARE_TEST_QUEUE.md:143` — "A real long-duration memory-soak run has still
  never been executed" — S4 OPEN; cites README.md's "Further reading", which (README.md:780-783) says it
  is tracked in BACKLOG.md. · related: HW.S14 · [H08]
- **HW.N581** RISK · `REAL_HARDWARE_TEST_QUEUE.md:151` — "**A6's timing script is not committed and this
  is the only copy.**" — The T4 instrument exists only in this temporary file (lost if the file is
  deleted before T4 decides). · [H08]
- **HW.N582** TODO · `REAL_HARDWARE_TEST_QUEUE.md:228` —
  "`tests_hardware/bench/test_bus_concurrency_under_api_load.py`'s six were last run on the **A-only**
  arm" — T2 PARTIAL: bus-hazard tier 4 on A+B code; three tests need `--allow-persistence-writes`. ·
  [H08]
- **HW.N583** TODO · `REAL_HARDWARE_TEST_QUEUE.md:244` — "a silently skipped chunk is invisible today
  because the call still answers `200`" — R4 OPEN: `ResetErrors` completeness under contention never
  checked; needs a gated run. · related: HW.T02 · [H08]
- **HW.N584** RISK · `REAL_HARDWARE_TEST_QUEUE.md:260` — "Residual, the owner's to weigh: the scratch
  write still spends one flash cycle, gated only by CLAUDE.md's go-ahead rule" — F1 FIXED 2026-09-18,
  unverified on silicon; the script once stranded the bench. · related: HW.S09 · [H08]
- **HW.N585** OPENQ · `REAL_HARDWARE_TEST_QUEUE.md:261` — "later resets overwrote `reset_cause()`, so it
  is recorded, not explained" — F17 OPEN: USB serial drop mid-upload unexplained; hotspot fallbacks
  explained as stale-AP-station after un-kicked WDT resets; PERIODIC hotspot timer returned to STA after
  8 min. · [H08]
- **HW.N586** SETTLED · `REAL_HARDWARE_TEST_QUEUE.md:275` — "**DECIDED 2026-09-22: adapt the method,
  defer the measurement.**" — G6: rollover test's `board.exec()` poll cannot measure (every exec → WDT
  reset); a non-exec method is owed, the ~12.4-day run deliberately unscheduled. · related: XCUT.T25 ·
  [H08]
- **HW.N587** DRIFT · `REAL_HARDWARE_TEST_QUEUE.md:291-293` — "these two get no dedicated sitting" —
  Says "these two" but the table lists three rows (W3, W4, W5). · - (low) · [H08]
- **HW.N588** TODO · `REAL_HARDWARE_TEST_QUEUE.md:296` — "**RAN 2026-09-24, not clean; re-run owed on
  the current tree.**" — W4: 103 passed/2 failed (one test bug fixed, one USB drop); `c20f80b` NTP fix
  and `assert_no_task_ended` checks unverified on silicon then. · [H08]
- **HW.N589** SETTLED · `REAL_HARDWARE_TEST_QUEUE.md:309-312` — "**The PR itself was closed unmerged on
  2026-09-18 by owner decision**" — PR #84's `--gc-policy`/`--memory-pressure` tooling is not coming. ·
  [H08]
- **HW.N590** SETTLED · `REAL_HARDWARE_TEST_QUEUE.md:313-318` — "**Owner, 2026-09-22: no hardware will
  be bought for this, so the rig stays as it is**" — GPIO fault-injection harness and second WiFi client
  permanently manual (BACKLOG 8). · related: HW.T09 · [H08]
- **HW.N591** SETTLED · `REAL_HARDWARE_TEST_QUEUE.md:319-321` — "Answered and migrated (SPECIFICATION.md
  Part A.7, BACKLOG 24). Do not re-measure." — Round 1's three requests. · [H08]
- **HW.N592** INVAR · `REAL_HARDWARE_TEST_QUEUE.md:333-334` — "a persistence check built on it passes
  vacuously `0 → 0`" — `kick_all_stations()` deauth logs nothing; use a real `ap_down()` outage. ·
  related: HW.T05 · [H08]
- **HW.N593** SETTLED · `REAL_HARDWARE_TEST_QUEUE.md:335-338` — "keeps a recovery dead-man's-switch
  armed for the whole risk window" — Host network safety rule (cost the Pi4 its SSH once). · covered-by:
  HW.T04 · [H08]
- **HW.N594** RISK · `REAL_HARDWARE_TEST_QUEUE.md:339-341` — "a failure between them used to leave the
  board permanently in hotspot mode ... It has happened." — Role-reversal stage 0 clears the persisted
  SSID. · covered-by: HW.S10 · [H08]
- **HW.N595** INVAR · `REAL_HARDWARE_TEST_QUEUE.md:366-375` — "a post-burst health check written as a
  bare `assert fetch(...) == 200` is the bug, not the server" — Post-burst slot drain:
  `ConnectionResetError` 2 runs in 3, same request OK 75 ms later; use `wait_until()`. · related:
  PERF.T02 · [H08]

## HARDWARE_TEST_HANDOVER.md (snapshot only; sitting IN PROGRESS in another session)

- **HW.N596** TODO · `HARDWARE_TEST_HANDOVER.md:3-7` — "A per-effort throwaway: delete it once the
  sitting's results are migrated." — Temporary doc; queue stays the single owed list, yet board state
  and running order are duplicated here. · covered-by: DOC.S15 · [H08]
- **HW.N597** ASSUME · `HARDWARE_TEST_HANDOVER.md:17-20` — "**This sitting (2026-09-24/25) is still in
  progress**" — Board on image of tree `3062cc7` (`buildDate 2026-09-25T07:31:00Z`), `DebugLevel` 5;
  results are not final. · related: HW.T18 · [H08]
- **HW.N598** TODO · `HARDWARE_TEST_HANDOVER.md:35, 43` — "a red here is a new finding, not a flaky
  test: read the SYSTEM log before anything else" — Webserver header/reset-guard/`MemoryError`
  slot-release changes and `assert_no_task_ended` still owe their first full bench run (W4 re-run). ·
  [H08]
- **HW.N599** INVAR · `HARDWARE_TEST_HANDOVER.md:49-50` — "Stop and report if a step goes red in a way
  its row does not anticipate; do not work around it." — Sitting discipline. · [H08]
- **HW.N600** DRIFT · `HARDWARE_TEST_HANDOVER.md:57-59` — "**G11, code at the sitting** ... (the queue
  row has the two lines)" — No G11 row exists in REAL_HARDWARE_TEST_QUEUE.md at the snapshot (dangling
  row ID). · related: HW.T10, DOC.S06 · [H08]
- **HW.N601** DRIFT · `HARDWARE_TEST_HANDOVER.md:65-66` — "Then **W3**:
  `tests_hardware/bench/test_end_to_end_timing.py`." — Queue W3 (:295) says that test "times no
  `/status`" and W3 was measured directly instead. · related: HW.T10 · [H08]
- **HW.N602** INVAR · `HARDWARE_TEST_HANDOVER.md:114-115` — "**Before any `ResetErrors`**, save
  `errcount` again — it is the only record of what the sitting itself logged." — FRAM-evidence
  discipline inside a sitting. · related: HW.S06 · [H08]
- **HW.N603** RISK · `HARDWARE_TEST_HANDOVER.md:121-122` — "Raw logs sit in the session's scratchpad
  only; what matters is here." — Raw evidence of the sitting is not preserved in the repo. · related:
  HW.T16 · [H08]
- **HW.N604** ASSUME · `HARDWARE_TEST_HANDOVER.md:126-130` — "`3062cc7` (functionally the tree as of
  this commit)" — Three images used (`bf62580`, `dd80eef`, `3062cc7`); figures tied to different trees.
  · related: HW.T19 · [H08]
- **HW.N605** ASSUME · `HARDWARE_TEST_HANDOVER.md:132-133` — "NTP `E21` (the NTP check, 5.3), WIFI `W6`
  ×5 and SGP40 `W13` ×9" — Board `errcount` as of last read (sitting-induced entries). · related: HW.T17
  · [H08]
- **HW.N606** TODO · `HARDWARE_TEST_HANDOVER.md:139` — "**Re-run the whole bench tier on the current
  image**" — W4 re-run is the gate for the wear-gated step. · [H08]
- **HW.N607** TODO · `HARDWARE_TEST_HANDOVER.md:143` — "The board prints `GC_THRESHOLD=` but the test
  does not echo it" — T1: echo `GC_THRESHOLD=` in the test; owner to close T1 or name the comparison
  position. · related: HW.T16 · [H08]
- **HW.N608** ASSUME · `HARDWARE_TEST_HANDOVER.md:152-155` — "**PASS**: after a real fallback the board
  returned to STA by itself after the 8 min window" — First silicon runs: NTP never-ends (`c20f80b`),
  radio byte bounds (`b5450aa`), PERIODIC hotspot timer, G11 flash tier 36 passed/3 skipped/12
  deselected. · [H08]
- **HW.N609** TODO · `HARDWARE_TEST_HANDOVER.md:167-171` — "Kicking 50 s early does not help — the board
  re-associates in between." — Kick must immediately precede a reset; suggested README note and ad-hoc
  helper not yet done (README :385-386 lacks it). · [H08]
- **HW.N610** RISK · `HARDWARE_TEST_HANDOVER.md:176-178` — "An `mpremote` attach within ~1 s of boot
  parks the board at the REPL with no watchdog armed" — Board never recovers on its own; suggested
  addition to traps/README not yet made. · related: HW.T06, XCUT.T20 · [H08]
- **HW.N611** OPENQ · `HARDWARE_TEST_HANDOVER.md:179` — "**F17, USB drop mid-upload during W4**: still
  unexplained, not reproduced." — Open anomaly. · [H08]
- **HW.N612** INVAR · `HARDWARE_TEST_HANDOVER.md:180-181` — "Ad-hoc scripts now cap retries and run
  under `timeout`." — After R2's unbounded retry ran 1 h 40 min. · [H08]
- **HW.N613** TODO · `HARDWARE_TEST_HANDOVER.md:183-190` — "### 5.5 Still owed this sitting, shortest
  first" — W4 re-run (~50 min), gated step 6 (~55 min, wear), F1/N2 (one write each), M1+S3b (owner
  present), R13+N3, step-9 scripts, owner decisions. · related: HW.T18 · [H08]

## dev_legacy/README.md

- **HW.N614** DRIFT · `dev_legacy/README.md:19-28` — "As of 2026-08-28 this unit runs a **custom-built
  firmware** based on **MicroPython 1.28.0**" — Stale: pin is 1.29.0; board now runs
  `scripts/build_firmware.py dev` images with persisted config files (queue N2); "VFS is still empty" no
  longer true. · covered-by: HW.S20 · [H08]
- **HW.N615** MIRROR · `dev_legacy/README.md:30-52` — "this table is the authoritative source for wiring
  this specific unit, not any code that references it" — Wiring table vs `devices/dev.toml` (buildgen's
  source of truth) vs ~20 device scripts' hardcoded pins — three copies, no guard. · related: HW.T08,
  HW.S18 · [H08]
- **HW.N616** DRIFT · `dev_legacy/README.md:45` — "address 0x77 (driver default); physically a
  **BMP384**" — Same file :629 says "BMP390 chip_id=0x50" for the same part. · related: HW.T07, SENS.S20
  · [H08]
- **HW.N617** DRIFT · `dev_legacy/README.md:48` — "| MPRLS — I2C0 | reset_pin=GPIO10, eoc_pin=GPIO7 |" |
  tests_hardware/README.md:1098 says i2c0 holds BMP3xx alone. · covered-by: HW.S12 · [H08]
- **HW.N618** SETTLED · `dev_legacy/README.md:49` — "**externally pulled up on this board** — confirmed
  by the project owner directly, which is why `devices/dev.toml` sets `irq_pull_up = false`" —
  Owner-confirmed rig fact mirrored in `devices/dev.toml`. · - (low) · [H08]
- **HW.N619** OPENQ · `dev_legacy/README.md:50` — "| BME688 (BSEC) — UART0 | tx=GPIO16, rx=GPIO17,
  115200 baud" | Whether the BME688 is still attached is unstated; `devices/dev.toml` puts UART0 on
  GP0/GP1 for the crossover jumper (same peripheral). · related: HW.T07 (low) · [H08]
- **HW.N620** INVAR · `dev_legacy/README.md:54-62` — "a deliberate bench-only loopback jumper, kept in
  place for further tests" — UART0↔UART1 crossover GP0↔GP9, GP1↔GP8; `devices/dev.toml:38` depends on
  it. · [H08]
- **HW.N621** RISK · `dev_legacy/README.md:92-96` — "breakout had a broken 3.3V trace, running
  parasitically off the I2C pull-ups until repaired 2026-08-28" — Bench history: an `EIO` pattern once
  came from hardware, not code. · - (low) · [H08]
- **HW.N622** SETTLED · `dev_legacy/README.md:103` — "(watchdog deliberately spared as a debugging aid,
  not a standing bench convention)" — 2026-08-28 full-system bring-up ran without a WDT (also the
  embedded entry script :237). · - (low) · [H08]
- **HW.N623** INVAR · `dev_legacy/README.md:112-113` — "`exec`/`run`/`mount` stay RAM-only,
  `cp`/`rm`/`mkdir`/`rmdir` write flash" — Wear boundary of mpremote subcommands. · related: HW.T01 ·
  [H08]
- **HW.N624** DRIFT · `dev_legacy/README.md:117-119` — "Since this bench unit's flash is empty, a `src/`
  module needs `mpremote mount src <exec|run>`" — Premise stale (see :19-28). · covered-by: HW.S20 ·
  [H08]
- **HW.N625** INVAR · `dev_legacy/README.md:133-141` — "prime `reader.cfgmgr.valid = True` and
  `reader.cfgmgr._cache = {...}` directly instead of calling `cfgmgr.setup()`" — No-flash-write
  diagnostic pattern; fresh `AsyFramManager` per simulated restart (bump allocator). · [H08]
- **HW.N626** DRIFT · `dev_legacy/README.md:143-175` — "with none of `scripts/build_firmware.py`'s
  wozi-specific `boot_entry`/website coupling" — Bench-only frozen-firmware recipe superseded by
  `build_firmware.py dev`; references retired boot_entry. · covered-by: HW.S20 · [H08]
- **HW.N627** RISK · `dev_legacy/README.md:177-179` — "the one accepted exception to the usual \"no
  RP2040 flash writes for bench testing\" default" — Firmware flash declared an accepted wear exception.
  · related: HW.T01 · [H08]
- **HW.N628** DRIFT · `dev_legacy/README.md:186-523` — "(this exact content lived on the device's own
  flash filesystem as `/main.py` for a long stretch" — Embedded pre-buildgen entry script: setup order
  `sysfunct → fram` (:475-476) and `watchdog = None` (:237); historical copy, not the generated wiring.
  · related: DOC.S09 (low) · [H08]
- **HW.N629** DRIFT · `dev_legacy/README.md:537-543` — "clear it first (`PUT /status {\"ResetErrors\": true}`
  once the system is up" — Instructs clearing FRAM logs before a run with no read-first step; CLAUDE.md
  requires reading `errcount` before any `ResetErrors`. · related: HW.S06, HW.T02 · [H08]
- **HW.N630** INVAR · `dev_legacy/README.md:549-552` — "This is real, persistent host infrastructure
  (survives a host reboot" — Bench bridge persists across host reboots. · related: HW.T04 · [H08]
- **HW.N631** RISK · `dev_legacy/README.md:563-572` — "nmcli connection up br0-eth0; nmcli connection up
  br0-wifi-ap" — Manual recipe enslaves eth0 with no dead-man's-switch step in the recipe itself
  (pointer to B.13 only). · related: TOOL.S03, HW.T04 · [H08]
- **HW.N632** INVAR · `dev_legacy/README.md:574-579` — "**Pin `bridge.mac-address` to `eth0`'s own real
  hardware MAC before ever bringing the bridge up — load-bearing, not optional.**" — Unpinned bridge MAC
  orphans the router's DHCP reservation. · covered-by: TOOL.T03 · [H08]
- **HW.N633** INVAR · `dev_legacy/README.md:588-593` — "Generate a fresh test-only SSID/password per
  session ... never commit real credentials" — Also: mount-proxied `config_WIFI.cfg` is "the accepted
  default for bench testing". · related: HW.T11 · [H08]
- **HW.N634** DRIFT · `dev_legacy/README.md:595-600` — "## Current bench state (as of 2026-09-02 —
  supersedes 2026-08-28 where they conflict)" — Stale snapshot of board state; the queue/handover now
  carry current state. · covered-by: HW.S20 · [H08]
- **HW.N635** DRIFT · `dev_legacy/README.md:615-621` — "no watchdog is armed ... and WiFi has no saved
  credentials (falls back to hotspot mode, SSID `SensorNode`)" — Stale bench state (hostname now
  `SensorStationDev`). · covered-by: HW.S20 · [H08]
- **HW.N636** DRIFT · `dev_legacy/README.md:622-641` — "the mounted-entry-script recipe above is the
  only currently-valid way ... until the per-variant generator exists" — The generator now exists; the
  wozi-on-dev `errno=11` finding reclassified as noise (rule itself still valid). · covered-by: HW.S20 ·
  [H08]
- **HW.N637** TODO · `dev_legacy/README.md:659-663` — "**Still open, needs the router's own admin UI
  (not automatable from here, the project owner's own follow-up)**" — Router DHCP reservation still
  keyed to a stale MAC; the file records the Pi's `eth0` MAC. · covered-by: HW.S08 · [H08]

## dev_legacy/*.py (reference-only 2026-08-27 on-device snapshot, MicroPython 1.24.1 — plan §2.2; field/bench behaviour only)

- **HW.N638** ASSUME · `dev_legacy/sensortask_test.py:29` — "i2c1 = asy_i2c_driver.I2C(1, 15, 14,
  frequency=50000)" — Legacy dev wiring put SCD30 on i2c1 without the 200 ms `timeout` the README entry
  script and `devices/dev.toml` use. · related: HW.S18 (low) · [H08]

## scripts/_require_clean_hardware_run.sh

- **HW.N639** SETTLED · `scripts/_require_clean_hardware_run.sh:7-10` — "The one permanent skip:
  off-subnet source-address spoofing on the bench host is unconfirmed" —
  `test_spoofed_off_subnet_source_address_is_ignored` is permanently whitelisted as a skip; the
  underlying capability is unconfirmed. · related: SCR.T05 · [H09]
- **HW.N640** INVAR · `scripts/_require_clean_hardware_run.sh:8-9` — "Add a name here only for an
  equally deliberate, documented, permanent skip - never to silence a real one." — Whitelist growth is
  policed by review only. · related: SCR.T05 · [H09]
- **HW.N641** MIRROR · `scripts/_require_clean_hardware_run.sh:12-47` — "The opt-in gates
  (tests_hardware/conftest.py's pytest_addoption()) are an EXPECTED skip only while their own flag is
  absent" — Hard-coded flag names and 9 test names mirror `tests_hardware/conftest.py` options and real
  test function names; a rename silently changes what is whitelisted. · related: SCR.T05 · [H09]
- **HW.N642** LIMIT · `scripts/_require_clean_hardware_run.sh:99-106` — "Deselected tests are invisible
  to every check above" — "Clean" means everything that ran passed, not everything ran (CLAUDE.md
  wear-gate rule). · related: SCR.S01 · [H09]

## scripts/mpremote_connect.sh

- **HW.N643** INVAR · `scripts/mpremote_connect.sh:2-4` — "`cp`/`rm`/`mkdir`/`rmdir` do write flash - be
  deliberate before passing those" — Flash wear/real-hardware discipline left to the caller; any use
  needs the owner's in-session go-ahead (CLAUDE.md). · [H09]
- **HW.N644** ASSUME · `scripts/mpremote_connect.sh:8` — "device=\"${MPREMOTE_DEVICE:-/dev/ttyACM0}\"" —
  Fixed default serial path. (low) · [H09]

## scripts/run_bench_hardware_suite.sh

- **HW.N645** SETTLED · `scripts/run_bench_hardware_suite.sh:2-3` — "bench is a strict superset of flash
  (SPECIFICATION.md Part E.6)" — Tier-structure claim. · [H09]

## scripts/run_bench_soak_tests.sh

- **HW.N646** SETTLED · `scripts/run_bench_soak_tests.sh:2-4` — "a deliberate, dedicated invocation
  (owner's direction, 2026-09-04) that the two general suite runners never bundle" — Soak tests only run
  through this runner. · [H09]
- **HW.N647** SETTLED · `scripts/run_bench_soak_tests.sh:8-10` — "The ~12.4-day ticks_ms() rollover wait
  is NOT a long_soak test and no tier here runs it" — The 2^30 ms rollover test runs only via its own
  flag. · [H09]

## scripts/run_manual_hardware_tests.sh

- **HW.N648** SETTLED · `scripts/run_manual_hardware_tests.sh:2-3` — "interactive, never invoked by
  pytest, structurally separate from the automated suites" — Manual tier has no automated gate. · [H09]

## toolchain/setup_toolchain.py

- **HW.N649** ASSUME · `toolchain/setup_toolchain.py:629-632` — "matching on vendor ID alone is enough
  to find \"some Pico-family board\"" — Any Raspberry Pi vendor-ID device (e.g. a debug probe) counts as
  a Pico. (low) · [H09]
- **HW.N650** ASSUME · `toolchain/setup_toolchain.py:734-736` — "Raspberry Pi OS does not install by
  default - confirmed on the real bench Pi4" — Bench-host package fact. · [H09]
- **HW.N651** PLATFORM · `toolchain/setup_toolchain.py:906-908` — "NetworkManager picked channel 13,
  which the Pico W's cyw43439 did not associate with reliably" — AP pinned to channel 6 / band bg based
  on a bench finding. · [H09]

## pyproject.toml

- **HW.N652** SUPPRESS · `pyproject.toml:324-330` — "S603/S607: shelling out to
  mpremote/picotool/nmcli/iw/iptables/tc IS this tier's job ... tools resolve from PATH" — Four
  tests_hardware files: S603, S607. · [H09]
- **HW.N653** SUPPRESS · `pyproject.toml:331-337` — "S310: a fixed `http://` URL this module builds
  itself" / "S112: injected packet loss makes individual request failures the fault itself" —
  tests_hardware/http_client.py: S310; test_bus_concurrency_under_api_load.py: S112. · [H09]

## tests_scripts/test_bench_harness_helpers.py

- **HW.N654** LIMIT · `tests_scripts/test_bench_harness_helpers.py:98-112,123-125` — "Thread-target
  functions whose try around http_client.fetch() names OSError but not HTTP_ERROR" — Structural guard
  over `tests_hardware/bench/test_*.py` only; flags a `try` that catches OSError but not
  HTTP_ERROR/Exception/BaseException. Does NOT flag a worker with no `try` at all around `fetch()`, a
  fetch reached via a helper, a Thread target passed positionally or defined in another module, or
  anything in flash/ or device_scripts/ · related: HW.T12 · [H10]
- **HW.N655** ASSUME · `tests_scripts/test_bench_harness_helpers.py:99-100` — "a cut-off answer is an
  HTTPException, which then kills the thread and silently stops its load" — Load-generator threads that
  die silently make a bench load test under-load without failing; the guard is the only protection ·
  related: HW.T05 · [H10]
- **HW.N656** MIRROR · `tests_scripts/test_bench_harness_helpers.py:138-143` —
  "configured_max_connections_is_the_builds_own_ceiling" — Pins
  `tests_hardware/harness.configured_max_connections()` == `buildgen.validate.device_max_connections()`
  for every device (host harness ↔ build) · [H10]

## tests_scripts/test_bench_no_task_ended_completeness.py

- **HW.N657** INVAR · `tests_scripts/test_bench_no_task_ended_completeness.py:1-3` — "\"no Traceback\"
  alone passed the NTP give-up that restarted a task a minute and rebooted every four" — Standing rule:
  every fault-injecting bench test must assert no task ended (SPEC C.7.2); enforced by this AST guard ·
  related: HW.T05 · [H10]
- **HW.N658** LIMIT · `tests_scripts/test_bench_no_task_ended_completeness.py:15-19,27-38` —
  "_FAULT_INJECTORS = frozenset({\"ap_down\", \"inject_network_degradation\", \"block_udp_ports\"," —
  Pinned sets: 5 fault injectors, checkers `assert_no_task_ended`/`_restore_ssid_over`. Scans only
  module-level `def test_*` in `tests_hardware/bench/`; does NOT see class methods, fixtures, faults
  injected through helper functions, a new BenchBridge fault method not in the set, call ORDER (checker
  before fault passes), or flash/ tier · related: HW.T05 · [H10]
- **HW.N659** SETTLED · `tests_scripts/test_bench_no_task_ended_completeness.py:15-16` —
  "kick_all_stations() is absent on purpose: it is the reconnect nudge every hard_reset() test uses, not
  a fault" — Deliberate exclusion from the fault set · [H10]
- **HW.N660** SUPPRESS · `tests_scripts/test_bench_no_task_ended_completeness.py:20-24` — "\"ap_down()
  is join mechanics, not a fault\"" — Two named exemptions (DHCP churn and station-management churn
  tests); staleness is checked (:54-56) but not whether the exemption reason still holds · [H10]
- **HW.N661** LIMIT · `tests_scripts/test_bench_no_task_ended_completeness.py:41-46` — "assert
  len(names) >= 15" — Vacuity floor: two named tests plus a count floor of 15 fault tests · [H10]
- **HW.N662** MIRROR · `tests_scripts/test_bench_no_task_ended_completeness.py:62-66` — "{\"num\": 1,
  \"type\": \"W\"}]}, False), # \"Task ended - attempting restart\"" — Pins SYSTEM log codes W1 (task
  ended/restart), E5 (task ended with exception), E4 (budget reboot) as the task-ended signal — must
  match `src/system_service.py`'s errno/wrnno assignment and C.7.1 · related: XCUT.T07 · [H10]
- **HW.N663** ASSUME · `tests_scripts/test_bench_no_task_ended_completeness.py:63` — "a board whose
  SYSTEM never logged anything reports no entry at all" — Helper treats a missing SYSTEM key in
  `/status` errcount as a pass; a /status that omits SYSTEM for another reason (degraded source) also
  passes · related: WEB.S09 (low) · [H10]

## tests_scripts/test_bench_restores_serving.py

- **HW.N664** INVAR · `tests_scripts/test_bench_restores_serving.py:1-3` — "run_isolated() leaves
  main.py stopped, and the one bench test that did not restore it failed every network test after it" —
  Rule: every bench test calling `run_isolated()` must reach `restore_board_to_serving()` in a `finally`
  or a same-module fixture teardown · related: HW.T05 · [H10]
- **HW.N665** LIMIT · `tests_scripts/test_bench_restores_serving.py:34-65` — "sorted(p for p in
  BENCH.glob(\"test_*.py\") if f\".{_RUNS}(\" in p.read_text())" — Scans only `tests_hardware/bench/`;
  flash-tier tests that run device scripts are NOT checked; only attribute calls `.run_isolated(` count;
  fixtures from conftest.py are not recognised as restoring (false positive, not false negative) · [H10]
- **HW.N666** LIMIT · `tests_scripts/test_bench_restores_serving.py:68-70` — "Guards the detector: an
  empty set would pass the test below vacuously." — Vacuity floor pins two named files
  (`test_heap_under_connection_ceiling.py`, `test_serving_heap_at_default_gc.py`) · [H10]

## tests_scripts/test_buildgen_validate.py

- **HW.N667** MIRROR · `tests_scripts/test_buildgen_validate.py:1718` — "The one reader every host-side
  instrument sizes its load with, so it must agree with the build." — `device_max_connections()` is the
  shared source for host load tools · [H10]

## tests_scripts/test_ceiling_probe.py

- **HW.N668** LIMIT · `tests_scripts/test_ceiling_probe.py:1-3,21-24` — "against a loopback server
  shaped like _serve(): reject-when-full, an idle-read timeout, a whole-request cap" — The ceiling probe
  is validated only against a threaded Linux-TCP loopback model of `_serve()` (options mimic
  serve-after-EOF, answer, RST refusal); lwIP accept/backlog/PCB behaviour is not modelled · related:
  TEST.T17 · [H10]
- **HW.N669** ASSUME · `tests_scripts/test_ceiling_probe.py:106-107` — "Nothing listening: the stack
  refuses the connect itself, as a PCB-exhausted board does." — Board behaviour at PCB exhaustion
  assumed equal to a closed-port connect refusal · related: PLAT.T04 · [H10]
- **HW.N670** ASSUME · `tests_scripts/test_ceiling_probe.py:204` — "The board refuses with an RST once a
  refused client's request bytes have arrived." — Observed board refusal mode encoded as a fake option;
  provenance not cited · related: HW.T16 · [H10]

## tests_scripts/test_device_script_config_flush.py

- **HW.N671** INVAR · `tests_scripts/test_device_script_config_flush.py:1-3` — "write_config() only
  stages - an unflushed manager lets asyncio.run() discard the flash write" — Device scripts must
  `flush_pending()` every manager they stage on; enforced here for `tests_hardware/device_scripts/*.py`
  only (MEASUREMENTS archive 7O) · related: HW.T01 · [H10]
- **HW.N672** LIMIT · `tests_scripts/test_device_script_config_flush.py:20-22,48-65` —
  "_DELEGATES_TO_CFGMGR = \"_set_dict_cfg\"" — Only `write_config()` and `_set_dict_cfg()` calls count
  as writes; other staging paths (driver setters, `_set_mgr_cfg` direct, REST) are not seen; matching is
  by source spelling, so aliases give false positives and a flush on an unreached path is a false
  negative · [H10]
- **HW.N673** SETTLED · `tests_scripts/test_device_script_config_flush.py:69-71` — "So no call ORDER is
  asserted: across two functions there is no order to read." — Deliberate: flush-after-write order is
  not checked · [H10]
- **HW.N674** SUPPRESS · `tests_scripts/test_device_script_config_flush.py:26-28` —
  "\"isl29125_mechanism_envelope.py\": \"awaits between pushes, so its flushes are scheduled, and
  nothing it writes has to survive a reset\"" — One allowlisted unflushed script; the re-derivation
  (:81-87) only checks that ANY `.sleep*()` call exists anywhere in the file, not "between writes" as
  the helper's name says · related: HW.S05 · [H10]

## tests_scripts/test_device_script_gc_threshold.py

- **HW.N675** LIMIT · `tests_scripts/test_device_script_gc_threshold.py:14-25,68-69` — "_MEASURES =
  {(\"gc\", \"mem_free\"), (\"gc\", \"mem_alloc\"), (\"micropython\", \"mem_info\")}" — A script is
  "measuring" only via plain `gc.mem_free/mem_alloc` or `micropython.mem_info` calls; `from gc import ...`,
  aliases, or heap reads through helper modules are not detected; "set before report" uses first line
  numbers, not control flow · [H10]
- **HW.N676** LIMIT · `tests_scripts/test_device_script_gc_threshold.py:72-75` — "Guards the detector
  itself: an empty or shrunken set would pass everything below vacuously." — Floor of five named
  heap-measuring scripts · [H10]

## tests_scripts/test_device_tomls.py

- **HW.N677** MIRROR · `tests_scripts/test_device_tomls.py:808-813` — "The on-target sweep keeps its own
  copy deliberately, being MicroPython on the board and unable to import host test code." — I2C reserved
  ranges 0x00-0x07/0x78-0x7F duplicated here and in the on-target bus sweep script · related: TEST.S05 ·
  [H10]

## tests_scripts/test_digital_twin_boot_contiguity.py

- **HW.N678** MIRROR · `tests_scripts/test_digital_twin_boot_contiguity.py:260-297` — "The probe's
  header claims it mirrors the board script's bounds ... Nothing pinned that claim." —
  `_STARTER_LOOP_TIMEOUT_MS`, `_STARTER_LOOP_GRACE_MS`, `_TIMERS_TIMEOUT_S` must match between
  tests/_boot_contiguity_probe.py and
  tests_hardware/device_scripts/heap_layout_after_full_boot_sequence.py (now enforced) · [H10]

## tests_scripts/test_heap_map_parser.py

- **HW.N679** INVAR · `tests_scripts/test_heap_map_parser.py:1-3` — "its dangerous failure mode is
  silent: a truncated capture reads as a heap with an enormous free run at the end, turning a regression
  into a pass" — heap_map.py gates real-hardware assertions; must fail closed on damaged captures
  (pinned here) · related: TEST.T17 · [H10]
- **HW.N680** MIRROR · `tests_scripts/test_heap_map_parser.py:194-222` — "=== MAP {label} ===" —
  MAP/ENDMAP envelope contract between heap_map.parse_labelled() and five emitters (now enforced);
  allocation_need_per_source.py's SIEVE/TRY/RES/BLOCK= line shapes are mirrored by a hand-built fixture
  only · [H10]

## tests_scripts/test_http_client_ceiling_close.py

- **HW.N681** ASSUME · `tests_scripts/test_http_client_ceiling_close.py:18-27` — "F10/F11 measured the
  reset and the empty-read forms on real silicon." — Only ECONNRESET and empty-read were observed on
  silicon; ECONNABORTED/EPIPE are accepted as ceiling closes by reasoning; cites queue row IDs F10/F11 ·
  related: DOC.T03 · [H10]
- **HW.N682** ASSUME · `tests_scripts/test_http_client_ceiling_close.py:31-36` —
  "ConnectionRefusedError(errno.ECONNREFUSED, \"Connection refused\")," — `is_ceiling_close()` classes a
  refused connect as a real failure, while test_ceiling_probe.py:106-107 treats a refused connect as how
  "a PCB-exhausted board" refuses — the two host oracles read the same symptom differently
  (context-dependent) (low) · related: TEST.T17 · [H10]
- **HW.N683** LIMIT · `tests_scripts/test_http_client_ceiling_close.py:59-63` — "RemoteDisconnected
  subclasses ConnectionResetError and BadStatusLine ... but only while that holds" — Depends on
  CPython's http.client class hierarchy (host-Python-version dependent) · [H10]

## tests_scripts/test_memory_error_gate_agreement.py

- **HW.N684** LIMIT · `tests_scripts/test_memory_error_gate_agreement.py:17-20,42-49` —
  "_HARDWARE_TIER_FILES = (\"tests_hardware/flash/test_memory_stress.py\",
  \"tests_hardware/bench/test_memory_stress_bench.py\"," — Only two hardware files are checked for
  routing through the shared constant; other hardware tests carry no MemoryError gate at all ·
  covered-by: TEST.T18 · [H10]

## tests_scripts/test_persistence_write_marker_completeness.py

- **HW.N685** SETTLED · `tests_scripts/test_persistence_write_marker_completeness.py:5-7` — "The gate
  covers the write a test OWNS, not one it is merely reached through ... Owner's rule, 2026-09-18" —
  Prerequisite writes stay unmarked; "not spend zero" · related: HW.T01 · [H10]
- **HW.N686** INVAR · `tests_scripts/test_persistence_write_marker_completeness.py:1-3,171-183` — "a
  test that PUTs a config-persisting field but forgets @pytest.mark.persistence_write spends real RP2040
  flash wear on every routine run, silently" — Enforced wear guard over tests_hardware/ (excluding
  device_scripts/) · related: HW.T01 · [H10]
- **HW.N687** LIMIT · `tests_scripts/test_persistence_write_marker_completeness.py:50-53` —
  "device_scripts/ is real MicroPython pushed to the board - it has no http_client and no markers." —
  Board-side scripts that write config (`_set_dict_cfg`/`write_config`) are outside this guard ·
  covered-by: HW.S05 · [H10]
- **HW.N688** LIMIT · `tests_scripts/test_persistence_write_marker_completeness.py:99-106,116-121` —
  "(enclosing function name, call) for every call named `fetch` in the module." — Detector sees only
  calls named `fetch` with a literal "PUT" method and a literal dict body; non-PUT writes,
  mpremote/`run_isolated` config writes, raw sockets ("deliberately out of scope", :272-274) and FRAM
  writes are not seen · related: HW.T01 · [H10]
- **HW.N689** LIMIT · `tests_scripts/test_persistence_write_marker_completeness.py:285-304` — "Checked
  per entry and per FIELD rather than against a fixed count" — Exemption re-derivation searches only
  tests_hardware/bench/test_network_resilience.py and counts `== "Invalid"` / `not in body["result"]`
  substrings in the function text, not which field each assertion is about · [H10]
- **HW.N690** INVAR · `tests_scripts/test_persistence_write_marker_completeness.py:32-47` — "Pinned by
  name so a NEW one has to be triaged deliberately" — `_KNOWN_PERSISTING_HELPERS` =
  {isl29125_write_worker, bmp3xx_write_worker, joined_hotspot, _restore_ssid_over,
  _recover_stale_dut_credentials}; whether each helper's callers carry the marker is NOT verified ("this
  file cannot verify by name resolution", :307) · related: HW.T01 · [H10]
- **HW.N691** SUPPRESS · `tests_scripts/test_persistence_write_marker_completeness.py:202-206` — "a
  ceiling-close retry wrapper that forwards every argument unchanged" — One allowlisted forwarding
  wrapper (`bench/test_bus_concurrency_under_api_load.py::fetch`); its signature parity with
  http_client.fetch is re-derived · [H10]
- **HW.N692** LIMIT · `tests_scripts/test_persistence_write_marker_completeness.py:161-168` — "if
  \"persistence_write\" in ast.dump(dec)" — "Marked" = any decorator whose AST dump contains the string;
  class-level/module `pytestmark` markers are not recognised · [H10]
- **HW.N693** INVAR · `tests_scripts/test_persistence_write_marker_completeness.py:367-376` —
  "--strict-markers is off, so an unregistered marker - a typo, or one left by a rename - is silently
  inert" — Mitigation for CI.S13; built-in allowlist includes "timeout" (a plugin marker, inert unless
  pytest-timeout is installed) · covered-by: CI.S13 · [H10]
- **HW.N694** INVAR · `tests_scripts/test_persistence_write_marker_completeness.py:379-384` —
  "scd30_extra_write only NARROWS, and nothing makes it imply the global gate" — Enforced:
  `scd30_extra_write` never carried without `persistence_write` · related: HW.T13 · [H10]

## tests_scripts/test_request_timeout_ceiling.py

- **HW.N695** MIRROR · `tests_scripts/test_request_timeout_ceiling.py:100-133` — "Both failed silently
  on silicon when they outlived the firmware's own timeouts (SPECIFICATION.md H.7.1)" — harness `dwell_s < per_call_timeout_s`,
  `probe_limit*dwell_s < outer_cap_s`, `probe_limit >` largest shipped ceiling; holder `_DRIP_INTERVAL_S < per_call_timeout_s`,
  `_RECYCLE_S < outer_cap_s` · [H10]
- **HW.N696** ASSUME · `tests_scripts/test_request_timeout_ceiling.py:262-263` — "The board refuses by
  closing ~6 ms after connect, after the request is already sent." — Measured board refusal timing
  encoded in a test rationale · related: HW.T16 · [H10]

## tests_scripts/test_require_clean_hardware_run_sh.py

- **HW.N697** LIMIT · `tests_scripts/test_require_clean_hardware_run_sh.py:136-155` — "if
  _SKIP_GATES[target.attr] not in body:" — "Really checks its own flag" = the flag string appears
  anywhere in the function's source text (a comment or docstring mention satisfies it); only function
  decorators are scanned (class/module markers not) · related: HW.T13 · [H10]
- **HW.N698** LIMIT · `tests_scripts/test_require_clean_hardware_run_sh.py:78-81,161` —
  "test_spoofed_off_subnet_source_address_is_ignored SKIPPED (unconfirmed)" — One bench test is a known
  permanent, unconditional skip accepted by the verdict script · [H10]

## tests_scripts/test_resolve_board_device.py

- **HW.N699** PLATFORM · `tests_scripts/test_resolve_board_device.py:14-15,45-46` — "_PICO_VENDOR =
  \"2e8a\"" / "usb-MicroPython_Board_in_FS_mode_{serial_no}-if00" — Board identification depends on the
  RP2040/MicroPython USB vendor ID and by-id naming; Arduino peer vendor 2341 · related: HW.T06 · [H10]
- **HW.N700** INVAR · `tests_scripts/test_resolve_board_device.py:83-88` — "The `board` fixture skips on
  an unreachable device, so this tier stays collectible with nothing attached" — `_NO_BOARD_DEVICE` must
  be a path that cannot exist; two boards is a hard error naming MPREMOTE_DEVICE · related: HW.T14 ·
  [H10]

## tests_scripts/test_setup_toolchain_env.py

- **HW.N701** MIRROR · `tests_scripts/test_setup_toolchain_env.py:433-445` — "must READ them from here
  rather than carry its own literals ... its skip gate deselects rather than fails" —
  harness.BENCH_BRIDGE_CONN/ETH_CONN/AP_CONN must be read from setup_toolchain (enforced by source
  substring) · [H10]

## tests_scripts/test_tests_hardware_conftest_constants.py

- **HW.N702** MIRROR · `tests_scripts/test_tests_hardware_conftest_constants.py:1-3,50-81` — "Drift here
  is silent and only shows up as a bench recovery that scans for an SSID no board is broadcasting" —
  tests_hardware/conftest.py `_DUT_HOSTNAME_CANDIDATES` (first = dev.toml hostname, last = `_VAL_HOST`
  default, each 1..32) and `_DUT_HOTSPOT_PASSWORD` must equal both dev.toml's `hotspot_password` and
  `_VAL_HOTSPOT_PW`'s default (enforced) · related: HW.T11 · [H10]
- **HW.N703** ASSUME · `tests_scripts/test_tests_hardware_conftest_constants.py:13` — "_BENCH_DEVICE =
  \"dev\" # the only unit ever bench-flashed (CLAUDE.md's hard rule)" — Hardcoded bench device · [H10]

## tests_scripts/test_tests_hardware_persistence_write_gating.py

- **HW.N704** INVAR · `tests_scripts/test_tests_hardware_persistence_write_gating.py:1-3,27-54` —
  "--allow-persistence-writes is the single global permission ... --allow-scd30-extra-write only narrows
  further" — Verified by real `pytest --collect-only` runs of tests_hardware/ (no hardware); board-free
  check executed in the host tier · related: HW.T14 · [H10]
- **HW.N705** LIMIT · `tests_scripts/test_tests_hardware_persistence_write_gating.py:32,39,47` — "assert
  \"7 deselected\" in output" — Exact deselect counts pinned for one file
  (flash/test_bus_concurrency.py); bench tier only checks "some" deselected; flash tier checks two named
  tests · [H10]
- **HW.N706** ASSUME · `tests_scripts/test_tests_hardware_persistence_write_gating.py:74-78` —
  "SGPResetVOC/ISLCalibrate carry `dispatch=true` ... never in ConfigManager's cache" — The bench
  memory-stress hammer stays ungated because its only PUT is dispatch-only · related: HW.S23 · [H10]

## SPECIFICATION.md Part A.1 (Repository layout, 29-92)

- **HW.N707** LIMIT · `SPECIFICATION.md:40-41` — "a 2026-08-27 snapshot of its on-device filesystem
  (reference only, in no lint/type/test scope)" — Dated bench-filesystem snapshot used as reference;
  ages silently. · related: HW.S20 · [H12]

## SPECIFICATION.md Part B.11 (Building this project's firmware, 931-984)

- **HW.N708** LIMIT · `SPECIFICATION.md:958-959` — "Confirmed working on real hardware for `dev`; not
  yet re-confirmed for `wozi` (never physically flashed)." — wozi boot entry never proven on silicon. ·
  related: PAR.S13 · [H12]
- **HW.N709** SUPPRESS · `SPECIFICATION.md:981` — "`tests_hardware/flash/test_toolchain_flash_boot.py`
  (`--allow-flash-cycle`-gated)" — Opt-in gate on the only on-silicon boot check. · related: HW.S01 ·
  [H12]

## SPECIFICATION.md Part B.13 (Bench network safety, 1016-1061)

- **HW.N710** INVAR · `SPECIFICATION.md:1018-1021` — "must keep a recovery dead-man's-switch
  continuously armed for the entire risk window — never touch live network state with none armed" —
  Operator rule; `ensure_bench_bridge()` itself arms none. · covered-by: TOOL.S03 · [H12]
- **HW.N711** ASSUME · `SPECIFICATION.md:1021-1023` — "One arm covering a whole atomic sequence is
  equivalent protection to per-command re-arming, provided the sequence's real timing is measured, not
  guessed." — Conditional equivalence claim. · related: TOOL.T03 · [H12]
- **HW.N712** MIRROR · `SPECIFICATION.md:1033-1034` — "`dev_legacy/README.md`'s manual recipe carries
  the identical fix." — MAC-pinning in code ↔ manual recipe doc. · [H12]
- **HW.N713** SETTLED · `SPECIFICATION.md:1036-1038` — "Recreate this script fresh in a session's own
  scratchpad each time (deliberately not a committed file)" — Recovery script intentionally uncommitted.
  · [H12]
- **HW.N714** ASSUME · `SPECIFICATION.md:1045-1048` — "nmcli connection modify \"Wired connection 1\"
  autoconnect yes" — Hardcoded NM profile name assumed present on the Pi. · covered-by: TOOL.S03 · [H12]
- **HW.N715** ASSUME · `SPECIFICATION.md:1055-1059` — "a real run showed success in ~1s but no DHCP
  lease/default route until ~30s later, STP delay" — Single observed timing informing the arm window. ·
  [H12]

## SPECIFICATION.md Part C.7 (Error handling & logging contract, 1807-1891)

- **HW.N716** INVAR · `SPECIFICATION.md:1810-1813` — "Known pitfall: a FRAM-backed history survives
  everything except an explicit reset, including a reflash — before treating a persisted
  `errcount`/history entry as evidence from *this* run, clear it first" — Tension with CLAUDE.md's
  read-FRAM-logs-BEFORE-clearing rule; order of operations is caller discipline. · related: HW.T02 ·
  [H12]
- **HW.N717** ASSUME · `SPECIFICATION.md:1845-1849` — "WIFI's FRAM-backed log read `counter=3`, history
  `W5, W4, W4` before an abrupt `hard_reset()` and byte-identical values after it" — Single dated
  (2026-09-17) silicon observation. · related: HW.T16 · [H12]

## SPECIFICATION.md Part C.8 (Concurrency & locking model, 2016-2188)

- **HW.N718** INVAR · `SPECIFICATION.md:2093-2098` — "ideally at most one real write per bus-hazard test
  group ... must construct the real protocol-layer driver directly (the DUT), never the `*_Reader`
  layer" — Owner-mandated write-safety constraints. · related: HW.T01 · [H12]
- **HW.N719** INVAR · `SPECIFICATION.md:2099-2101` — "Extend the worker set only with requests safe
  under both constraints above (`GET` always safe; `PUT` only if documented
  command-only/never-persisted)" — "GET always safe" vs ISL GET writing chip/FRAM (SENS.S24). · related:
  SENS.S24 · [H12]
- **HW.N720** SUPPRESS · `SPECIFICATION.md:2128-2138` — "SCD30's own on-chip NVM write is opt-in, off by
  default ... `--allow-persistence-writes`/`@pytest.mark.persistence_write` ...
  `--allow-scd30-extra-write`/`@pytest.mark.scd30_extra_write`, that is AND-gated" — Wear gates
  (deselect, not skip). · covered-by: HW.T13 · [H12]
- **HW.N721** LIMIT · `SPECIFICATION.md:2139-2144` — "Real hardware has no literal equivalent of the
  mock tier's `asyncio.sleep(0)`-count offset sweep ... fires at one deliberately chosen representative
  offset instead" — Real-hardware timing sweep weaker than mock/twin. · [H12]
- **HW.N722** MIRROR · `SPECIFICATION.md:2147-2152` — "whatever gets added to
  `tests_hardware/flash/test_bus_concurrency.py` gets a bench-tier counterpart ... never left as a
  silent asymmetry" — flash ↔ bench tier mirror obligation. · related: HW.T09 · [H12]
- **HW.N723** DRIFT · `SPECIFICATION.md:2153-2155` — "No REST-layer path exists to the write at all —
  e.g. SCD30 registers zero `_push_callbacks`" — Seed says SCD30 NVM is reachable over REST via its own
  setter dispatch. · covered-by: HW.S02 · [H12]
- **HW.N724** ASSUME · `SPECIFICATION.md:2156-2162` — "SGP40's real general-call broadcast only fires
  from `SGP40_I2C._reset()`, itself only called from `initialize()` at setup time ... confirmed by
  reading the real call chain" — Structural-exception claim. · related: HW.T09 · [H12]

## SPECIFICATION.md Part C.11 / C.11.1 (Design decisions; conformance probe, 2310-2353)

- **HW.N725** SUPPRESS · `SPECIFICATION.md:2346-2348` — "gated by
  `tests_hardware/flash/test_sensor_accuracy.py::test_isl29125_register_probe_matches_the_digital_twins_fake_chip`"
  — The only conformance check runs only on the gated flash tier. · [H12]

## SPECIFICATION.md Part E.6 / E.6.1-E.6.6 (Shared behaviours, real-hardware tier, 3090-3225)

- **HW.N726** ASSUME · `SPECIFICATION.md:3104-3107` — "Both tiers run clean end to end on real hardware;
  the earlier WiFi-reconnection flakiness ... is root-caused and mitigated" — Undated status claim. ·
  related: HW.T16 · [H12]
- **HW.N727** SETTLED · `SPECIFICATION.md:3123-3130` — "Credential rotation is deliberately not a bench
  capability (owner decision, 2026-09-22)" — Removed `rotate_ap_password()`. · [H12]
- **HW.N728** LIMIT · `SPECIFICATION.md:3154-3157` — "a trailing soft reset only restores the
  *appearance* of normal operation ... only a genuine `hard_reset()` reliably resumes the live system" —
  Isolated-driver mode caveat. · related: HW.T06 · [H12]
- **HW.N729** RISK · `SPECIFICATION.md:3165-3169` — "a failed real-credential PUT lands in
  `_PHASE_DEACTIVATED` (a terminal state, A.4) ... hence the fixture's real `hard_reset()` fallback" —
  Role-reversal can strand WLAN deactivated. · covered-by: HW.S25 · [H12]
- **HW.N730** ASSUME · `SPECIFICATION.md:3164-3165` — "a real, source-traced ~15-20s timing budget from
  a credential PUT to the DUT's first STA attempt" — Timing premise. · [H12]
- **HW.N731** INVAR · `SPECIFICATION.md:3184-3191` — "every mock/digital-twin test that exercises
  real-hardware-facing behavior needs a real-hardware equivalent, wherever technically possible" —
  Standing owner rule; review-only. · related: TEST.T06 · [H12]
- **HW.N732** SETTLED · `SPECIFICATION.md:3196-3201` — "Only `dev` is ever physically bench-tested ...
  real-hardware parity for anything specific to one of them is structurally impossible" — Exception 1. ·
  [H12]
- **HW.N733** DRIFT · `SPECIFICATION.md:3202-3207` — "SCD30 has zero REST-pushable fields
  (`asy_scd30_driver.py` registers no `_push_callbacks`), so no bench-tier `PUT` can ever reach its own
  NVM write" — Disputed: SCD30 dispatches PUTs via its own setters. · covered-by: HW.S02 · [H12]
- **HW.N734** TODO · `SPECIFICATION.md:3218-3219` — "Revisit when that hardware exists." — Deferred
  real-hardware UART fault injection. · [H12]

## SPECIFICATION.md Part F.5 — MicroPython 1.29 delta (intro)

- **HW.N735** LIMIT · `SPECIFICATION.md:3673-3676` — "inducing a genuine RX overrun is not reachable
  from Python, so its *consequence* is pinned instead (`device_scripts/fram_busy_status_lockout.py`)" —
  F.5.2's EIO path is never exercised on silicon, only its downstream consequence. · related: PLAT.T03 ·
  [H13]

## SPECIFICATION.md Part F.5.3 — Free wins in the 1.29 build

- **HW.N736** SETTLED · `SPECIFICATION.md:3768-3774` — "**That test's thresholds changed on
  2026-09-19**: the owner retired its 100,000 B free / 80,000 B contiguous floors" — Owner decision; now
  survivor volume ≤ 100,000 B, contiguity ≥ 32,768 B, nothing placed/sitting in top 16,384 B
  (`tests_hardware/flash/test_memory_stress.py`). · related: HW.T16 · [H13]

## SPECIFICATION.md Part H.5.1 — Definitions-file autogeneration

- **HW.N737** INVAR · `SPECIFICATION.md:4435-4444` — "`tests_hardware/website_identity.py` runs
  `build_model()` + `generate_definitions()` ... Nothing is hardcoded: a new `[[instance]]` is covered
  the day it is declared" — Hardware-tier check that the served page matches the generator. · related:
  HW.T05 · [H13]

## SPECIFICATION.md Part H.7.1 — Connection lifetime and instruments

- **HW.N738** INVAR · `SPECIFICATION.md:4653-4659` — "**A walk's per-connection dwell stays under
  `per_call_timeout_s`, and the whole walk under `outer_cap_s`**, or no ceiling is ever reached" —
  Instrument constraint; a violating instrument "fails silently, not loudly" (4634-4635). · related:
  HW.T12 · [H13]

## SPECIFICATION.md Part I.5 — Real-hardware confirmation

- **HW.N739** ASSUME · `SPECIFICATION.md:5138-5141` — "a 120s always-run hammer test plus a
  `long_soak`-gated 600s variant) — nothing from this audit remains open pending hardware" — Closure
  claim for the 2026-09-07 audit. · related: HW.S14 · [H13]

## SPECIFICATION.md Part I.6 — Request-body cap (sits inside Part J)

- **HW.N740** LIMIT · `SPECIFICATION.md:5220-5225` — "a socket cannot distinguish \"buffered then
  rejected\" from \"rejected unread\" ... The binding itself stays a mock-tier and source-level claim,
  never a hardware-confirmed one" — Hardware tier cannot prove the no-allocation property. · [H13]
- **HW.N741** ASSUME · `SPECIFICATION.md:5227-5234` — "**Run on silicon, 2026-09-19** [HW]. W1-W4 pass
  ... (2047 -> 200, 2048 -> 200, 2049 -> 413 ...)" — Dated bench result; cites queue rows W1-W5. ·
  related: HW.T16, DOC.T03 · [H13]
- **HW.N742** ASSUME · `SPECIFICATION.md:5257-5273` — "Across the 96 concurrent requests ... **not one
  was answered with the wrong status** ... 20 of 24 requests answered against a floor of 4" — Dated
  replay and silicon results. · related: HW.T16 · [H13]

## SPECIFICATION.md Part K.7 — devices/*.toml

- **HW.N743** MIRROR · `SPECIFICATION.md:5892-5895, 5970-5971` — "The on-target sweep
  (`device_scripts/bus_topology_autodetect_and_hazard_sweep.py`) keeps its own address table ... needs
  the new address added by hand" — `KNOWN_ADDRESSES` ↔ `devices/*.toml`, hand-kept, no cross-check. ·
  related: HW.T08 · [H13]

## CLAUDE.md

- **HW.N744** SETTLED · `CLAUDE.md:159-162` — "it is never physically flashed or bench-tested; only the
  dev board is, and only ever will be" — WoZi's correctness rests entirely on the mock, twin and unit
  tiers. · related: PAR.S13 · [H14]
- **HW.N745** INVAR · `CLAUDE.md:163-169` — "a passing dev-bench result is treated as valid for wozi
  too, provided the code actually under test is genuinely dev-native" — Nothing stops a wozi image being
  built and flashed onto dev (`build_firmware.py wozi` is accepted). The "false bugs" trap is guarded by
  convention only. · related: PAR.S13 · [H14]
- **HW.N746** ASSUME · `CLAUDE.md:164-165` — "a passing dev-bench result is treated as valid for wozi
  too" — An inferred transfer: wozi's own bus pairing and instance set are never exercised on silicon. ·
  related: TEST.T15 · [H14]
- **HW.N747** INVAR · `CLAUDE.md:246-248` — "the two real-hardware write-safety constraints any new
  device's own on-chip NVM or the RP2040's own flash filesystem must respect" — Delegated to Part C.8.
  Convention only. · related: HW.T01 · [H14]
- **HW.N748** INVAR · `CLAUDE.md:249-260` — "every operation that spends a limited-endurance write cycle
  is a default-off, explicitly-opted-into marker with a tracked budget" — Enforced by the
  tests_hardware/conftest.py markers (deselect at :117-133) and
  tests_scripts/test_persistence_write_marker_completeness.py, which excludes device_scripts/. Owner,
  2026-09-17. · covered-by: HW.T01 (related HW.S05, HW.T13) · [H14]
- **HW.N749** LIMIT · `CLAUDE.md:256-257` — "a *dispatch-only* PUT persists nothing and is deliberately
  outside the gate, and FRAM is out of scope (effectively unbounded endurance here)" — FRAM writes are
  ungated, including those that overwrite production error logs. · covered-by: HW.T01 (related STOR.T10,
  HW.T02) · [H14]
- **HW.N750** LIMIT · `CLAUDE.md:260-263` — "Because that gate DESELECTS rather than skips, a gated run
  is invisible to `scripts/_require_clean_hardware_run.sh`'s own skip check" — "Clean" means everything
  that ran passed. `flash_cycle`/`long_soak`/`multi_day_rollover`/`neopixel_sweep` skip in-test instead
  (conftest.py:106-111, 140-154). · covered-by: HW.T13 · [H14]
- **HW.N751** SETTLED · `CLAUDE.md:263-271` — "The gate covers the write a test OWNS, not one it is
  merely reached through (owner's clarification, 2026-09-18)" — Prerequisite writes stay unmarked;
  test_persistence_write_marker_completeness.py pins that set by name. · covered-by: HW.T01 · [H14]
- **HW.N752** INVAR · `CLAUDE.md:284-290` — "A session needs the project owner's go-ahead, given
  directly in that session's own conversation, before running anything against real hardware" —
  Convention only; the runners have no technical interlock. · related: HW.T14 · [H14]
- **HW.N753** INVAR · `CLAUDE.md:367-379` — "read the FRAM-persisted per-module error logs ... BEFORE
  issuing any `PUT /status {\"ResetErrors\": true}` call" — Convention only: the harness takes no
  automatic `errcount` snapshot. · covered-by: HW.T02 (HW.S06) · [H14]
- **HW.N754** DRIFT · `CLAUDE.md:370-373` — "WIFI/NTP/WEBSERVER joined this list ... every
  `CFGMGR_<name>` logger joined it too" — tests_hardware/bench/test_memory_stress_bench.py:18-19 still
  calls them RAM-only. · covered-by: HW.S23 · [H14]
- **HW.N755** ASSUME · `CLAUDE.md:379-385` — "a single real `WDT_RESET` was investigated down to \"GC
  ruled out, cause otherwise undetermined\"" — Unresolved 2026-09-08 reset; its evidence was lost. ·
  related: XCUT.S10 · [H14]
- **HW.N756** LIMIT · `CLAUDE.md:387-394` — "this rule assumes a board that has been running normally" —
  Device scripts build their own AsyFramManager over production's first chunk and can fabricate
  plausible entries. No record of what ran against the board. · covered-by: HW.T17 · [H14]

## README.md

- **HW.N757** INVAR · `README.md:299-301` — "Always flash `dev`, never `wozi` — `wozi` is never
  physically flashed; its hardcoded pins don't match any real bench wiring" — Convention only
  (`build_firmware.py wozi` succeeds). "Hardcoded pins" predates buildgen; the pins come from
  devices/wozi.toml (low). · related: PAR.S13 · [H14]
- **HW.N758** RISK · `README.md:311, 319-320` — "sudo picotool load -x -v build/firmware-dev.uf2" /
  "machine.bootloader()" — Root flashing plus remote bootloader entry, gated only by the go-ahead
  convention. · related: TOOL.T09 · [H14]
- **HW.N759** ASSUME · `README.md:323-327` — "Both recipes are exercised as real, automated/manual
  tests, not just prose here" — The automated one (tests_hardware/flash/test_toolchain_flash_boot.py:53)
  is `--allow-flash-cycle`-gated. Its file also runs `env --tier flash` unmarked. · related: HW.S01 ·
  [H14]
- **HW.N760** ASSUME · `README.md:331-333` — "`exec`/`run`/`ls`/`cat` execute or read against the device
  without writing flash" — Raw-REPL entry stops `main.py` (WDT reset ~8 s later), and a `run` script can
  itself write. "RAM-only" understates the side effects. · related: HW.T06, HW.S14 · [H14]
- **HW.N761** LIMIT · `README.md:334-335, 346-347` — "a default device path of `/dev/ttyACM0` ... (still
  pass it as `MPREMOTE_DEVICE` yourself" — The default may be the Arduino peer; auto-detection doesn't
  feed mpremote_connect.sh. · covered-by: HW.S19 · [H14]
- **HW.N762** INVAR · `README.md:363-367` — "A session needs the project owner's explicit go-ahead,
  given in that session's own conversation, before running any of these" — Convention only. · related:
  HW.T14 · [H14]
- **HW.N763** LIMIT · `README.md:390-392` — "Add --allow-flash-cycle to also run the one deliberate
  re-provisioning-flash test (skipped by default" — `flash_cycle` skips in-test while
  `persistence_write` deselects; each interacts with the clean-run wrapper differently. · covered-by:
  HW.T13 · [H14]
- **HW.N764** DRIFT · `README.md:398-400` — "(see tests_hardware/conftest.py's own SOAK_TIER_SECONDS)" —
  It is in tests_hardware/soak_tiers.py:7. · covered-by: HW.S17 · [H14]
- **HW.N765** ASSUME · `README.md:401-403` — "`--tier long # ~6h - the real production soak duration`" —
  Matches soak_tiers.py:7. Units run for months; soak tests assert less than their names. · related:
  HW.S14 · [H14]
- **HW.N766** SETTLED · `README.md:398-399` — "Soak tests (@pytest.mark.long_soak) are NEVER bundled
  into either suite above" — The role-reversal scenario, however, runs in every routine bench pass. ·
  related: HW.S25 · [H14]
- **HW.N767** ASSUME · `README.md:410-411` — "Collection-only sanity check - works with nothing attached
  at all, every fixture skips cleanly" — Presented as safe; the plan wants board-free checks confirmed
  with the owner at go-ahead. · related: HW.T14 · [H14]
- **HW.N768** INVAR · `README.md:700-706` — "Each row is deleted once its result is migrated into the
  permanent docs ... It authorizes nothing" — Rows get deleted, but permanent code still cites row IDs.
  · related: HW.T10, DOC.S06 · [H14]

## BACKLOG.md

- **HW.N769** INVAR · `BACKLOG.md:53-55` — "the write path is now gated behind
  @pytest.mark.persistence_write, so a default bench run deselects both arms" — Re-confirmation silently
  does not happen without `--allow-persistence-writes` (deselect, not skip). · related: HW.T13 · [H15]
- **HW.N770** SETTLED · `BACKLOG.md:111-114` — "answered 2026-09-22: a structural exception until
  injection hardware exists" — The mock tier's ~20-scenario UART fault catalog stays a structural
  exception (SPEC E.6.6 fourth item). · related: HW.T09 · [H15]
- **HW.N771** SETTLED · `BACKLOG.md:215-226` — "no hardware will be bought for this, so the rig stays as
  it is and both candidates are permanently [MANUAL]" — #8 GPIO fault harness / second WiFi client never
  built; re-open only as a new entry if fault hardware arrives; no software stand-in may claim the same
  coverage. · related: DOC.S05, DOC.S08 · [H15]
- **HW.N772** ASSUME · `BACKLOG.md:234-236` — "independently verified rock-solid (28/28 trials, ~9.1s
  each, zero variance)" — #9 closed stub; single-campaign figure for `kick_all_stations()` +
  `hard_reset()`. · [H15]
- **HW.N773** LIMIT · `BACKLOG.md:358-362` — "Since 2026-09-19 the test retries a ceiling refusal, so a
  clean run no longer answers this item" — The test's retry masks the symptom; only per-arm
  `CEILING_RETRIES` answers it. · [H15]
- **HW.N774** TODO · `BACKLOG.md:364-388` — "Setting the bench budget waits on item 24's design fix
  (batched or concurrent reset) — the owner's decision." — #32: bench `ResetErrors` timeout raised 10→30
  s (`tests_hardware/error_log_helpers.py:14`) with no elapsed-time budget; a 25 s sweep would pass
  silently. · covered-by: PERF.T03 · [H15]
- **HW.N775** OPENQ · `BACKLOG.md:390-403` — "recorded, not chased; each needs silicon" — #44: one
  silent reset in 1/9 peak-load boots (watchdog starvation first candidate); hotspot fallbacks (one
  explained as stale-AP-station); queue F17. · related: XCUT.T03, XCUT.S01 · [H15]
- **HW.N776** TODO · `BACKLOG.md:654-677` — "the script still does not complete ... so it likely needs
  run_isolated_expect_reset()" — `wifi_service_reconnect_repro.py` half-closed; queue §2A F1 (also its
  garbage-SSID incident). · related: HW.S09 · [H15]
- **HW.N777** TODO · `BACKLOG.md:727-761` — "Still open: the real --tier long (6h) production-duration
  run itself" — Long real-HW memory soak never run (queue S4); 10-min `mid` passed 2026-09-08. ·
  related: HW.S14 · [H15]
- **HW.N778** LIMIT · `BACKLOG.md:743-749` — "a real but coarser signal than an actual trend
  measurement" — Real-HW soak detects only a `MemoryError` traceback or a reboot. · related: HW.S14 ·
  [H15]
- **HW.N779** LIMIT · `BACKLOG.md:866-868` — "CYW43-firmware-level faults such as wlan.connect() itself
  raising are not network-path faults tc/iptables can express" — Covered only by the twin's `--fault wlan:`.
  · [H15]

## HEAP_FRAGMENTATION_MEASUREMENTS.md (current, 393 lines; owning area HW)

- **HW.N780** INVAR · `HEAP_FRAGMENTATION_MEASUREMENTS.md:14-15` — "Read the archive's §9 before reusing
  any old number — it lists the figures a defective instrument produced." — Quarantined figures must not
  be reused. · related: HW.T16 · [H15]
- **HW.N781** INVAR · `HEAP_FRAGMENTATION_MEASUREMENTS.md:43-52` — "Every figure must name the threshold
  it was taken at" — Report consumption and layout together; ensemble; compare like positions. ·
  related: HW.T16 · [H15]
- **HW.N782** INVAR · `HEAP_FRAGMENTATION_MEASUREMENTS.md:71-72` — "A truncated capture reads as a heap
  with an enormous free run at the end" — Enforced by `tests_scripts/test_heap_map_parser.py`. · [H15]
- **HW.N783** LIMIT · `HEAP_FRAGMENTATION_MEASUREMENTS.md:73-75` — "HeapDelta ... is independent of what
  the heap held before, and a lower bound" — Re-occupied blocks are never attributed. · [H15]
- **HW.N784** LIMIT · `HEAP_FRAGMENTATION_MEASUREMENTS.md:79-85` — "It can pin its own buffer." —
  Bisecting probe returns `_PROBE_MAX >> k`; `retained=` printed and `_report_checked()` re-reads
  (device scripts). · [H15]
- **HW.N785** INVAR · `HEAP_FRAGMENTATION_MEASUREMENTS.md:86-92` — "it runs after the last map dump,
  never before one" — Probe ordering / collect-before-measuring / read `mem_free()` before probe. ·
  [H15]
- **HW.N786** SETTLED · `HEAP_FRAGMENTATION_MEASUREMENTS.md:141-144` — "deliberately not lowered to the
  new 2,048 B worst case" — `tests_hardware/flash/test_memory_stress.py` keeps ≤100,000 B used, ≥16,384
  B above top survivor, ≥32,768 B run (`WORST_CASE_ALLOCATION = 16_384` at :25). · [H15]
- **HW.N787** INVAR · `HEAP_FRAGMENTATION_MEASUREMENTS.md:138-139` — "A derived threshold's first
  silicon run can fail; that is a finding, not automatically a regression" — · [H15]
- **HW.N788** INVAR · `HEAP_FRAGMENTATION_MEASUREMENTS.md:158-160` — "A substitution that changes
  control flow is not an isolation." — Stub arms need a byte-identical bus-work audit. · [H15]
- **HW.N789** INVAR · `HEAP_FRAGMENTATION_MEASUREMENTS.md:161-163` — "Allocating instrumentation
  perturbs the layout." — No headline from an audit run; no `gc.collect()` in the measured phase. ·
  [H15]
- **HW.N790** INVAR · `HEAP_FRAGMENTATION_MEASUREMENTS.md:171-178` — "a result that does not name its
  threshold is void" — Heap device scripts set their own threshold and print `GC_THRESHOLD=` (enforced
  by `tests_scripts/test_device_script_gc_threshold.py`); twin harnesses importing `sensortask_<dev>`
  directly sit at `-1` unless they set it. · related: TEST.T18 · [H15]
- **HW.N791** LIMIT · `HEAP_FRAGMENTATION_MEASUREMENTS.md:179-185` — "Board.run_isolated() interrupts
  the running firmware and never resets" — Device scripts build inside whatever heap `main.py` left;
  standalone reading ≠ layout reading. · related: HW.T06 · [H15]
- **HW.N792** PLATFORM · `HEAP_FRAGMENTATION_MEASUREMENTS.md:200-204` — "under mpremote run, sys.argv
  reads [] and cannot be assigned" — Also: wrappers must pass Microdot's `filename` kw; an await-less
  `get_value()` is a truthy coroutine. · [H15]
- **HW.N793** INVAR · `HEAP_FRAGMENTATION_MEASUREMENTS.md:205-206` — "a device script building its own
  AsyFramManager writes production's first chunk" — Read `errcount` before anything clears it. ·
  related: HW.T02, HW.T17 · [H15]
- **HW.N794** INVAR · `HEAP_FRAGMENTATION_MEASUREMENTS.md:310` — "Always do this before silicon" — Run
  device scripts in the twin first (found three instrument defects). · [H15]
- **HW.N795** LIMIT · `HEAP_FRAGMENTATION_MEASUREMENTS.md:312-322` — "last present at commit 4914a25,
  removed once the connection limit was settled" — Silicon combined-load sweep tool exists only in
  history (`tests_hardware/combined_load_sweep.py` absent). · [H15]
- **HW.N796** LIMIT · `HEAP_FRAGMENTATION_MEASUREMENTS.md:340-341` — "Exact from ~6 blocks up; below
  that the sieve's own residue floors the reading." — Need-sieve precision. · [H15]
- **HW.N797** INVAR · `HEAP_FRAGMENTATION_MEASUREMENTS.md:351-355` — "A serving figure holds only within
  its scope; write it down every time" — · related: HW.T16 · [H15]

## Archive `12640c2:HEAP_FRAGMENTATION_MEASUREMENTS.md` (5,553 lines) — only items still open/undecided/deferred/next-step there, with carry status in current docs

- **HW.N798** TODO · `ARCH:559` — "Optional silicon confirmation of the race is queue row T1's." —
  Threshold-inheritance race; queue T1 (REAL_HARDWARE_TEST_QUEUE.md:227) records that the script now
  sets its own threshold but has no explicit race-confirmation step. Partially carried. · [H15]
- **HW.N799** OPENQ · `ARCH:3633-3638, :3978` — "it is a real defect in whatever wrote it. Not chased;
  queued." — Malformed `config_HWTEST_ISL29125.cfgconfig_ISL29125.cfg` on board flash: queued as F8,
  file deleted 2026-09-19 (§7J.6); the writer's concatenation defect is never recorded as found or
  fixed; F8 and any mention are gone from current docs. Only device script naming that scratch file:
  `tests_hardware/device_scripts/isl29125_mechanism_envelope.py:105` (not investigated). · related:
  HW.T03 · [H15]
- **HW.N800** OPENQ · `ARCH:5124-5127` — "A self-reset under heap exhaustion on pre-fix image G ...
  Cause not captured." — Not carried in BACKLOG #44 / queue F17 (they carry only the silent reset and
  hotspot fallbacks). Pre-fix image. (low) · [H15]
- **HW.N801** OPENQ · `ARCH:5118-5123` — "One silent reset ... watchdog or hard fault, cause lost." —
  Carried with the "hotspot fallback, three times" bullet as BACKLOG #44 / queue F17. · [H15]

## Commit messages (chronological)

- **HW.N802** TODO · `commit 3cb3e5b` — "once real rp2040 hardware testing is available, repeat both the
  segfault-stress and memory-leak soak tests there" — Real-hardware soak retest. · tracked: BACKLOG
  "Real-hardware re-test of the segfault fix and the memory-leak soak test" (6h tier still open; queue
  S4) | related: HW.T* · [H17]
- **HW.N803** SETTLED · `commit 7416dbc` — "Documented as the one accepted exception to \"no RP2040
  flash writes for bench testing\"" — Frozen-firmware reflash accepted for bench bring-up because
  imports of the full dependency closure exceed heap (~140-180KB needed vs ~196KB free; single dated
  measurement). · tracked: dev_legacy/README.md (per commit) | related: HW.T*, MEM.T* · [H17]
- **HW.N804** WORKAROUND · `commit e249999 / 48ea9c8` — "this bench's USB connection to the board can
  wedge into a state where raw-REPL entry fails indefinitely ... only clearing via an actual USB
  unbind/rebind" — Harness auto-unbinds/rebinds USB; is_reachable() opts out so real reboots stay
  visible. · tracked: tests_hardware/harness.py (per commit) | related: HW.T* · [H17]
- **HW.N805** PLATFORM · `commit b802d7b` — "a trailing soft-reset does NOT \"hand the board back to its
  normal auto-booted state\" ... only hard_reset() resumes main.py" — mpremote/raw-REPL behaviour the
  whole HW tier depends on. · tracked: SPECIFICATION Part E.6, tests_hardware/harness.py | related:
  HW.T* · [H17]
- **HW.N806** SETTLED · `commit 5bdac21` — "a fallback hard_reset() recovery ... now counts as a genuine
  pass, not a failure - the same \"hardware watchdog is the accepted backstop\" principle" — Owner
  direction: WiFi-link-wedge tests pass via hard reset. · tracked: CLAUDE.md hard rule (CYW43
  isconnected false positive) | - · [H17]
- **HW.N807** SETTLED · `commit 5730e72 / a19691c` — "testing scripts/build_firmware.py wozi ... against
  the dev bench's physically different wiring can never produce a meaningful result - it's not a real
  target, it's a mistake" — Items 7/8 (captive 404, I2C errno=11 boot loop) dropped as
  invalid-by-construction; standing rule. · tracked: CLAUDE.md hard rule (WoZi never flashed) | - ·
  [H17]
- **HW.N808** INVAR · `commit dc3ee33` — "run_isolated()'s implicit soft reset stops the live system's
  own WDT-feed loop ... does not reset the RP2040's hardware watchdog peripheral ... chunk them into
  <=2s sleeps with a wdt.feed() between each" — Every device script with a wait beyond ~8.4 s must feed
  the re-armed WDT; enforced only by review. · tracked: tests_hardware/README.md:1069 (mentions
  `wdt.feed()` cadence as review item) | related: HW.T* · [H17]
- **HW.N809** SETTLED · `commit dc3ee33` — "loosens scd30_plausibility_read.py's CO2 floor from the
  datasheet's 400ppm \"measurement range\" to 200ppm, per project owner input" — Plausibility bound
  below datasheet range by owner decision. · tracked:
  tests_hardware/device_scripts/scd30_plausibility_read.py:2,12 | - · [H17]
- **HW.N810** TODO · `commit 0f6208d` — "Still open: tests_hardware/'s flash+bench pytest tiers haven't
  been re-run against this corrected build, and hotspot role-reversal + a bounded soak window remain
  outstanding" — Post-flash re-runs. · status: done (later bench passes, f57eccf/9bcfe20, BACKLOG soak
  `mid` pass 2026-09-08) | - · [H17]
- **HW.N811** RISK · `commit 33b38e5` —
  "test_real_ntp_handles_a_genuinely_unreachable_server_without_crashing (block_udp_ports) has likely
  been passing for the wrong reason all along ... zero fault actually injected" — Bench fault injection
  was a silent no-op until br_netfilter; a class of bench tests could pass vacuously. · status: done-in
  21106f2 (ensure_br_netfilter persisted) — but no bench guard asserts the fault actually took effect
  beyond per-test log checks (low) | related: HW.T* · [H17]
- **HW.N812** INVAR · `commit 5205785 / 70195d4` — "DebugLevel=0 silently blinds every log-based bench
  check" — Bench tier relies on DebugLevel=5 on the DUT; log-line waits cannot fire otherwise. ·
  tracked: tests_hardware/README.md (standing gotcha) | related: HW.T* · [H17]
- **HW.N813** SETTLED · `commit 1096b31 / a10c578` — "the router's own reservation re-keying is the
  project owner's own follow-up, not something to track here" — Out-of-repo bench follow-up deliberately
  untracked. · status: UNTRACKED by owner decision (low) | - · [H17]
- **HW.N814** LIMIT · `commit f862b1e` — "test_dns_flood_backoff_curve_recovers_once_flood_stops's own
  docstring claims its flood \"triggers the backoff path\" - checked directly and this doesn't hold" —
  DNS backoff path not actually exercised by the flood test. · tracked: tests_hardware/README.md:874-882
  (comment corrected; backoff path still not exercised by that test) | related: NET.T* · [H17]
- **HW.N815** OPENQ · `commit e246825` — "one separate, flagged-not-chased finding (a device-side
  AttributeError traceback whose line numbers don't match the current src/ checkout, suggesting stale
  firmware rather than a current bug)" — Unexplained device-side AttributeError. · status: no closure
  found; later explained generally by d967013 (build_firmware's ast.unparse drops comments so line
  numbers never match) — cause of the AttributeError itself UNTRACKED (low) | - · [H17]
- **HW.N816** RISK · `commit 3cace28 / 6b58828` — "a separate, not-yet-root-caused real hardware
  watchdog reset observed after the same run" — Single WDT_RESET closed as singular, evidence lost to
  ResetErrors. · tracked: CLAUDE.md FRAM-evidence hard rule | - · [H17]
- **HW.N817** NOTE(CONVENTION) · `commit f887c2d` — device scripts clear their FRAM chunk at start —
  Mitigation for FRAM residue fabricating logs. · tracked: tests_hardware/README.md | related: HW.T* ·
  [H17]
- **HW.N818** NOTE(TRAP) · `commit 47af5bb` — device script silently overwrote production
  config_ISL29125.cfg (six flash writes/run) — Fixed; caveat recorded. · tracked:
  tests_hardware/README.md | related: HW.T* · [H17]
- **HW.N819** NOTE(PATTERN) · `commit b18618f` — "BACKLOG 23 records it as a pattern ... provide your
  own light, restore the state you changed, and assert a minimum engagement"; "BACKLOG 24 records the
  two live-backend browser tests failing on a stub frozen website" — Rig-dependence pattern; web tier
  failure. · tracked: tests_hardware/README.md:237-283 (pattern); live-backend-on-stub item: likely
  done-in 12640c2 ("Retire html_stub/"); branch-local BACKLOG numbering differed from today's | - ·
  [H17]
- **HW.N820** NOTE(FLAG) · `commit a379128` — "BACKLOG 26 now holds only the FRAM hard-reset test ...
  asks a contract question"; "BACKLOG 27 ... an interrupted setup_toolchain.py env --tier flash leaves a
  Unix port with no frozen asyncio ... fix is a capability check ... left undone because scripts/ is
  inside the two-chroot pre-push gate" — Two deferred items. · status: FRAM hard-reset done-in 699836e
  (owner: expect E31/W71/W72); frozen-asyncio probe done-in 12640c2 (scripts/test.sh:92) | - · [H17]
- **HW.N821** NOTE(UNPROVEN) · `commit 62f1ab9 / f05f82d` — "what is still NOT proven: a ratio learned
  from a real overlap-band measurement surviving a reboot" -> "22 restates what the redesign leaves
  unproven on hardware" — Hardware proof gap for ISL calibration. · status: partly moot (ratio now user
  config, persisted via ConfigManager); SPEC:6767 records a hardware measurement; not re-verified
  whether "calibrate then reboot" is covered | related: HW.T* · [H17]
- **HW.N822** NOTE(DEFERRED) · `commit 5615efc` — "bmp3xx_plausibility_read.py (8 keys) and
  sgp40_fram_backup_restore.py ... still hand-list theirs ... left for whenever their driver's schema
  next changes" — Device script cache drift. · status: done (both now derive from cfg_schema:
  bmp3xx_plausibility_read.py:23, sgp40_fram_backup_restore.py:79,114) | - · [H17]
