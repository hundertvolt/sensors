# Harvest H07 — real-hardware test code: `tests_hardware/` except README (snapshot 2a88cc8)

## tests_hardware/conftest.py
- SETTLED | tests_hardware/conftest.py:1-3 | "fixtures skip (not error) when the hardware they need isn't reachable, so `uv run pytest tests_hardware --collect-only` always succeeds" | Tier is designed to stay collectible and skip (not error) with nothing attached. | area: HW | related: HW.T14
- SUPPRESS | tests_hardware/conftest.py:139-144 | "no real board reachable at {b.device} ... Not a failure" | Session `board` fixture skips the whole dependent tier when `is_reachable()` fails — and `is_reachable()` itself raw-REPL-interrupts the live system (harness.py:409-411). | area: HW | related: HW.T13
- SUPPRESS | tests_hardware/conftest.py:153-157 | "no bench WiFi bridge configured (br0-wifi-ap missing)" | `bench` fixture skips every bench test when the NM profile is absent. | area: HW | related: HW.T13
- SUPPRESS | tests_hardware/conftest.py:27-37, 106 | "Not set by default, so long_soak tests always skip in a general suite run" | `long_soak` gate (tiers short/mid/long) is an in-test `pytest.skip`, not a deselect (implemented per test: flash/test_memory_stress.py:88-90, flash/test_bus_electrical_timing.py:84-86, bench/test_memory_stress_bench.py:116-118, 137-139). | area: HW | covered-by: HW.T13
- SUPPRESS | tests_hardware/conftest.py:44-53, 107 | "a real, fixed ~12.4-day wait (time.ticks_ms()'s own 2**30 rollover) ... never bundled with --soak-tier" | `multi_day_rollover` gate, in-test skip (flash/test_bus_electrical_timing.py:115-116). | area: HW | covered-by: HW.T13
- SUPPRESS | tests_hardware/conftest.py:38-43, 108 | "a deliberate re-provisioning flash - counts against the 'no extra flash cycles' constraint" | `flash_cycle` gate, in-test skip (flash/test_toolchain_flash_boot.py:54-55). | area: HW | covered-by: HW.T13
- DRIFT | tests_hardware/conftest.py:65, 111 | "Spends no write of any kind, so it is its own flag rather than a persistence one" | `neopixel_sweep` help claims no writes, while the plan's HW.S05 records ~5 flash writes in isl29125_mechanism_envelope.py under this flag only (see that file below). | area: HW | covered-by: HW.S05
- SETTLED | tests_hardware/conftest.py:69-88, 109 | "FRAM is deliberately NOT in scope - its endurance is effectively unbounded" | `persistence_write` covers SCD30 NVM + RP2040 flash FS only; FRAM writes are outside the wear gate by decision. | area: HW | covered-by: HW.T01
- SETTLED | tests_hardware/conftest.py:80-83 | "a persisting write that is a shared PREREQUISITE (joined_hotspot clearing the SSID, _recover_stale_dut_credentials()) stays unmarked and still runs" | Named unmarked prerequisite writes; "not zero writes overall" without the flag. | area: HW | covered-by: HW.T01
- SUPPRESS | tests_hardware/conftest.py:116-133 | "Central deselection point for every real limited-endurance persistence write" | Only `persistence_write`/`scd30_extra_write` DESELECT (invisible to a skip check); all other gates skip in-test. | area: HW | covered-by: HW.T13
- INVAR | tests_hardware/conftest.py:89-102, 110, 126 | "passing this alone, without --allow-persistence-writes, still deselects the test" | `scd30_extra_write` is AND-gated and "always carried alongside @pytest.mark.persistence_write" — the carrying rule is convention only. | area: HW | covered-by: HW.T13
- SUPPRESS | tests_hardware/conftest.py:112 | "informational marker, not skip-gated, so it reports the board's own wall whenever it is run" | `over_provisioned_image` runs on every pass regardless of image. | area: HW | covered-by: HW.S25
- SUPPRESS | tests_hardware/conftest.py:113 | "bench radio temporarily stops hosting br0-wifi-ap ... informational marker, not skip-gated" | `role_reversal` is not a gate; the scenario runs in routine bench passes. | area: HW | covered-by: HW.S25
- INVAR | tests_hardware/conftest.py:105-113 | markers registered via `addinivalue_line` | No `--strict-markers`: a misspelled gate marker would silently run ungated. | area: HW | covered-by: CI.S13
- ASSUME | tests_hardware/conftest.py:161-164 | "a board with an older config file still answers to the persisted \"SensorNode\". Both are live" | Hardcoded DUT hostname candidates ("SensorStationDev", "SensorNode") mirror devices/dev.toml's injected default + legacy default. | area: HW | related: PAR.S11
- MIRROR | tests_hardware/conftest.py:165 | "_DUT_HOTSPOT_PASSWORD = \"12345678\"  # src/asy_wifi_service.py's _VAL_HOTSPOT_PW default, which every devices/*.toml also declares" | Committed hotspot credential copy #1 (also bench/test_hotspot_role_reversal.py `_HOTSPOT_PASSWORD`, manual/manual_wifi.py) — consistency item, not alarm. | area: HW | covered-by: HW.T11
- ASSUME | tests_hardware/conftest.py:168-200 | "stale stored WiFi credentials are the likely cause" | Last-resort recovery PUTs `/networking` SSID/PW = an unmarked RP2040 flash write (prerequisite class), and takes the bench AP down (join_dut_hotspot). | area: HW | related: HW.T01
- DRIFT | tests_hardware/conftest.py:181-187 | "wait_until(_any_candidate_visible, ...)" before "bench.join_dut_hotspot(...)" | Scans via `is_ssid_visible()` while the AP is still up, though bench_control.py:195-196 says it "Requires ap_down() already called - this single-radio bench can't scan while still hosting an AP". (low) | area: HW | related: HW.T12
- RISK | tests_hardware/conftest.py:187-200 | "bench.join_dut_hotspot(found[0], ...)" is outside the `try:`/`finally: leave_dut_hotspot_and_restore_bridge()` | A failure inside join (after its own `ap_down()`) leaves the bench AP down with no `ap_up()`. (low) | area: HW | related: HW.T12
- ASSUME | tests_hardware/conftest.py:211-212, 255 | "Strands main.py (soft reset via exec() stops it re-running) - always followed by a real hard_reset()"; "only a real hard_reset() reliably resumes normal auto-boot" | Harness-level fact about raw-REPL/soft-reset side effects. | area: HW | covered-by: HW.T06
- ASSUME | tests_hardware/conftest.py:233-234 | "Purely passive (tail_log only, no exec()/run()) - the board must already be mid-boot from a prior hard_reset()" | Caller-discipline precondition of `_wait_for_sta_ip`. | area: HW | -
- ASSUME | tests_hardware/conftest.py:250, 257, 262, 269 | "webserver task starts only after ntp_force_sync(), up to ~20s after STA connects" | Timing basis for 60 s STA wait + 30 s HTTP wait, three attempts (≈4.5 min worst case). | area: HW | related: HW.S19
- ASSUME | tests_hardware/conftest.py:205-207 | "Retries hard_reset()+kick_all_stations() through known reconnect flakiness" | Known reconnect flakiness is worked around, not fixed; assumes stable DUT DHCP address after resets. | area: HW | covered-by: HW.S19
- MIRROR | tests_hardware/conftest.py:196-198 | "accepted = {\"Valid\", \"Unchanged\"}" | Hardcoded copy of the REST setter result vocabulary. (low) | area: HW | -

## tests_hardware/flash/conftest.py
- INVAR | tests_hardware/flash/conftest.py:1-3, 18-22 | "this test group writes it at most once per pytest session" | SCD30 NVM write budget upheld by a session-scoped fixture that every dependent reuses. | area: HW | covered-by: HW.T01
- INVAR | tests_hardware/flash/conftest.py:23-31 | "reaching here means a test forgot the marker: fail loudly rather than spend the write" | Runtime backstop for a missing `persistence_write` marker on this fixture's dependents (mechanical enforcement). | area: HW | related: CI.S13
- ASSUME | tests_hardware/flash/conftest.py:20-21, 32 | "the one real NVM-persisted SCD30 write (set_ambient_pressure(), doubling as \"trigger continuous measurement\")" | Wear-relevant write lives in device script scd30_same_device_rw_concurrency.py; 90 s timeout under run_isolated's 8 s WDT. | area: HW | covered-by: HW.T01

## tests_hardware/soak_tiers.py
- ASSUME | tests_hardware/soak_tiers.py:1-3 | "a subdirectory's own conftest.py (e.g. flash/) shadows a bare `from conftest import ...` - confirmed directly via a real ImportError" | Reason the tiers live outside conftest.py; docs pointing at conftest.py for them are stale. | area: HW | related: HW.S17
- ASSUME | tests_hardware/soak_tiers.py:7 | "SOAK_TIER_SECONDS = {\"short\": 60.0, \"mid\": 600.0, \"long\": 6 * 3600.0}" | Soak duration thresholds; no basis stated here (mid = 600 s matches "the original WDT-reset investigation", bench/test_memory_stress_bench.py:118). | area: HW | -

## tests_hardware/harness.py
- MIRROR | tests_hardware/harness.py:34-37 | "BOTH spellings: src/'s degrade handlers log str(e), so a real caught allocation failure reads \"memory allocation failed, ...\"" | Shared hardware MemoryError markers; kept in agreement with the unit/twin gates by tests_scripts/test_memory_error_gate_agreement.py (CLAUDE.md); only three bench/flash importers use it. | area: HW | related: TEST.T18
- LIMIT | tests_hardware/harness.py:39-41 | "It describes the TREE, not necessarily the image on the board" | `configured_max_connections()` can disagree with the flashed image. | area: HW | covered-by: HW.T19
- PLATFORM | tests_hardware/harness.py:49-53 | "Not an RST - a read of it leaves modlwip writing the 400 to a NULL pcb (SPECIFICATION.md Part H.7.1)" | Probe shape chosen around a modlwip behaviour; FIN close relies on microdot answering 405 for an unrouted method. | area: HW | related: REST.T06
- INVAR | tests_hardware/harness.py:77-80 | "only the outer cap bounds it, which is why probe_limit * dwell_s stays under it" | 40 × 0.3 s = 12 s must stay under the server's 15 s outer cap — kept by default values only. | area: HW | related: REST.T06
- ASSUME | tests_hardware/harness.py:56-59 | "The only figure that is silicon's own rather than the tree's, and the one a raised lwIP PCB count has to be confirmed against (SPECIFICATION.md Part B.14.2)" | Ceiling discovery is the claimed oracle for the lwIP PCB override. | area: HW | related: HW.T19
- ASSUME | tests_hardware/harness.py:60, 138-141 | "a slot outlives its client's close by 0.71-0.84 s (SPECIFICATION.md Part H.7.1)" | Single dated measurement drives settle/release sleeps (settle_s/release_s 1.0 s, hold_s 0.3 s). | area: HW | related: REST.T06
- SUPPRESS | tests_hardware/harness.py:64-70 | "best effort, one slot: the next test starts cleaner, and the walk's error stays the headline" | Drain failure after a failed walk is folded into the walk error. (low) | area: HW | -
- LIMIT | tests_hardware/harness.py:155-157 | "retrying sooner can alternate forever between two half-drained sets" | Known drain-livelock mode, mitigated by sleep only. (low) | area: HW | -
- DRIFT | tests_hardware/harness.py:175-177 | "its skip gate deselects rather than fails, which is exactly the way that goes unnoticed" | Bench gate is a `pytest.skip` (conftest.py:154), not a deselect; the MIRROR (connection names imported from setup_toolchain) is enforced by import. (low) | area: HW | related: HW.T13
- WORKAROUND | tests_hardware/harness.py:183-207 | "same effect as a physical unplug/replug, recovering a wedged raw-REPL-entry state" | USB unbind/rebind via `sudo tee /sys/bus/usb/...` for a bench USB wedge; removal trigger: none stated; needs passwordless sudo. | area: HW | related: HW.S19
- DRIFT | tests_hardware/harness.py:210-213 | "conftest.py turns it into a skip" | conftest.py has no HardwareNotAvailableError handler; only `is_reachable()` swallows it, while `tail_log()`/`_nmcli()` raise it mid-test as an error. (low) | area: HW | related: HW.T12
- SUPPRESS | tests_hardware/harness.py:227-245 | "treating a raising check as not-yet-ready" | `wait_until` swallows every `Exception` from the check (including HardwareTestFailureError, an AssertionError) until timeout. | area: HW | related: HW.T12
- INVAR | tests_hardware/harness.py:248-251 | "A bench test that runs a device script calls this in a finally or a fixture's teardown ... (tests_scripts/test_bench_restores_serving.py pins it)" | restore-after-device-script obligation, mechanically pinned by a tests_scripts meta-test. | area: HW | -
- ASSUME | tests_hardware/harness.py:264-267 | "main.py's server may still be answering when this starts, so it first waits (up to `handover_s`) for that one to go quiet" | 20 s handover / 120 s timeout basis unstated. (low) | area: HW | -
- SETTLED | tests_hardware/harness.py:296-300 | "a path that cannot exist, so the `board` fixture's own is_reachable() probe fails and SKIPS ... without mpremote ever opening some other device's port" | No-board sentinel design. | area: HW | -
- INVAR | tests_hardware/harness.py:318-337 | "never a bare ttyACM scan, which could pick the bench's Arduino ... Two matches is a hard error, not sorted()[0]" | Board selection by vendor ID; the Arduino C peer is on the same host. | area: HW | related: HW.S19
- ASSUME | tests_hardware/harness.py:350-353 | "observed ttyACM0 -> ttyACM1 mid-suite" | Re-enumeration after hard reset has no index guarantee; pinned device is never re-resolved. | area: HW | -
- WORKAROUND | tests_hardware/harness.py:362-406 | "this bench's USB device can wedge into indefinite raw-REPL-entry failure until unbound/rebound" | 10 s transient-marker grace + ≤2 rebinds + one USB reset per call; removal trigger: none stated. | area: HW | related: HW.T06
- RISK | tests_hardware/harness.py:408-416 | "Raw-REPL entry always Ctrl-C's the device, so never poll this against a live system" | `is_reachable()` is what the session `board` fixture calls first, so every run starts by stopping main.py (WDT reset ~8 s later). | area: HW | covered-by: HW.T06
- INVAR | tests_hardware/harness.py:429-432 | "this always interrupts whatever's running first ... Never use for passive live-system observation" | exec()/run_isolated() usage rule, convention only. | area: HW | covered-by: HW.T06
- PLATFORM | tests_hardware/harness.py:440-447 | "machine.WDT(timeout=8000)" armed before every `mpremote run`; "against the real frozen src/ drivers" | Every device script runs under an 8 s watchdog it must feed, against the image not the tree. | area: HW | covered-by: HW.T19
- SUPPRESS | tests_hardware/harness.py:454-459 | "Deliberately ignore the return code/output" | `run_isolated_expect_reset` cannot tell a script that failed before reaching its reset from one that reset. | area: HW | related: HW.T05
- DRIFT | tests_hardware/harness.py:466-469 | "The `reset` shortcut (DTR-line hardware reset, never a flash)" | mpremote `reset` is described as DTR; plan notes it is `machine.reset()`. | area: HW | covered-by: HW.S17
- ASSUME | tests_hardware/harness.py:474-480 | "Counts as a flash cycle if followed by a picotool write ... a non-zero/timeout exit here is expected, not a failure" | enter_bootloader() result is unchecked by design. | area: HW | related: HW.T13
- ASSUME | tests_hardware/harness.py:482-501 | "Retries a transient post-hard_reset() USB-settle failure before raising HardwareNotAvailableError" | 10 s grace; raises (error, not skip) mid-test. (low) | area: HW | -

## tests_hardware/bench_control.py
- MIRROR | tests_hardware/bench_control.py:1-3 | "Shares connection names with toolchain/setup_toolchain.py's ensure_bench_bridge()" | Enforced by import (harness.py:178-180); role-reversal profile name is local. | area: HW | -
- ASSUME | tests_hardware/bench_control.py:18-21 | "always torn down ... so a crashed test run never leaves a stray profile behind" | A killed pytest cannot tear down; only join_dut_hotspot's delete-first (:207-210) recovers a leftover. | area: HW | related: HW.T12
- ASSUME | tests_hardware/bench_control.py:24-33, 90, 201-203, 249, 255 | `["sudo", "nmcli", ...]`, `sudo iw`, `sudo iptables`, `sudo tc`, `sudo timeout ... tcpdump` | Bench host must grant passwordless sudo for nmcli/iw/iptables/tc/tcpdump/tee. | area: HW | covered-by: HW.S19
- WORKAROUND | tests_hardware/bench_control.py:59-62 | "`nmcli -g` escapes ':' as '\\:', so an SSID/PSK containing one reaches the DUT with stray backslashes" | `--escape no` for nmcli output quirk; removal: none stated. (low) | area: HW | -
- ASSUME | tests_hardware/bench_control.py:64-68 | "The real, current WPA2 PSK for this bridge's AP - needs `--show-secrets`" | Run-time credential read (the HW.T11 convention); `$BENCH_AP_PASSWORD` override mentioned at :61. | area: HW | related: HW.T11
- WORKAROUND | tests_hardware/bench_control.py:72-80 | "if \"is not an active connection\" not in str(e): raise" | Idempotency depends on nmcli's English error text. (low) | area: HW | -
- WORKAROUND | tests_hardware/bench_control.py:85-100 | "Fixes the dominant cause of WiFi reconnection flakiness - a stale AP-side entry surviving a hard_reset() power-cycle" | `iw station del` per MAC before each hard_reset; removal: none stated. | area: HW | -
- DRIFT | tests_hardware/bench_control.py:102-107 | "iptables DROP rules on the bridge's OUTPUT/FORWARD chains" | Code appends to FORWARD only. | area: HW | covered-by: HW.S17
- RISK | tests_hardware/bench_control.py:102-124 | "Always paired with unblock_udp_ports() in a test's own teardown" | Host iptables FORWARD DROP and nat PREROUTING DNAT survive a killed pytest; nothing restores at session start. | area: HW | covered-by: HW.T12
- LIMIT | tests_hardware/bench_control.py:115-119, 126-129 | "works around a local-delivery gap in redirect_udp_port_to_local()" | DNAT-to-loopback does not deliver locally; tcpdump source-port capture is the workaround. | area: HW | covered-by: HW.S13
- ASSUME | tests_hardware/bench_control.py:146-147 | "e.g. \"14:35:23.753510 IP 192.168.85.57.55718 > 162.159.200.123.123: NTPv3, ...\"" | Parser relies on tcpdump -nn line format; example records bench DUT IP 192.168.85.57. (low) | area: HW | related: HW.S19
- RISK | tests_hardware/bench_control.py:153-188 | "Real packet loss/latency/... via `tc netem` on `wifi_iface()` only (doesn't affect eth0/br0)" | Host qdisc left in place if pytest is killed; cleared only by test teardown. | area: HW | covered-by: HW.T12
- PLATFORM | tests_hardware/bench_control.py:190-196 | "the bench Pi4 has a single WiFi radio"; "can't scan while still hosting an AP" | Bench-rig fact driving sequential role-reversal. | area: HW | related: HW.T07
- SUPPRESS | tests_hardware/bench_control.py:209-210, 243-244 | "except HardwareTestFailureError: pass  # no leftover profile" | Swallows any nmcli failure of the delete, not just "not found". (low) | area: HW | -
- ASSUME | tests_hardware/bench_control.py:267-274 | `["iw", "dev", iface, "station", "dump"]` | Station dump runs without sudo while `station del` uses sudo. (low) | area: HW | -
- WORKAROUND | tests_hardware/bench_control.py:277-281 | "Best-effort settle delay ... the immediately-following wifi-connect call was found racy without this" | Fixed ≤2 s sleep for NM/kernel teardown race; removal: none stated. | area: HW | covered-by: HW.S19

## tests_hardware/http_client.py
- MIRROR | tests_hardware/http_client.py:1-3 | "mirrors digital_twin/_http_client.py's `HttpResponse`/`fetch()` shape closely enough" | Oracle mirror between hardware and twin HTTP clients (sync vs async). | area: HW | related: TEST.T17
- ASSUME | tests_hardware/http_client.py:22-24 | "every endpoint this tier talks to answers with a JSON object, never a bare array/scalar" | json() narrowing assumption. (low) | area: HW | related: TEST.T17
- ASSUME | tests_hardware/http_client.py:46-49 | "the client sees FIN or RST depending on kernel TCP state (queue F10/F11 measured both)" | Ceiling-close shape is not chosen by src/; cites deleted queue rows from permanent code. | area: HW | covered-by: DOC.S06
- INVAR | tests_hardware/http_client.py:52-54 | "An HTTPException, not an OSError, so a caller catching transport failures has to name it too" | Caller discipline. (low) | area: HW | -

## tests_hardware/error_log_helpers.py
- ASSUME | tests_hardware/error_log_helpers.py:71-74 | "Above the server's own 15.0s outer_cap_s ... Measurements: BACKLOG item 24" | `_RESET_ERRORS_TIMEOUT_S = 30.0` basis: ResetErrors sweep cost over real WiFi. | area: HW | related: PERF.T03
- RISK | tests_hardware/error_log_helpers.py:61-63, 77-79 | "reset before a test, confirm a provoked fault produced the expected error/warning entry, then reset again" | `reset_all_error_logs()` clears FRAM-backed evidence with no snapshot first. | area: HW | covered-by: HW.S06
- ASSUME | tests_hardware/error_log_helpers.py:89-94 | "A routine fault is handled in place (SPECIFICATION.md C.7.2), so this stays empty" | SYSTEM log persists across hard_reset via FRAM; oracle assumes routine faults never end a task. | area: HW | related: HW.T05
- DRIFT | tests_hardware/error_log_helpers.py:137-140 | "Every FRAM-backed module's counter, not one named module's" | Code compares every module present in errcount (RAM-only ones included). (low) | area: HW | -
- MIRROR | tests_hardware/error_log_helpers.py:128-129 | "Kind is \"E\" (err_s()) or \"W\" (wrn_s())" | History `type` vocabulary mirrors src/print_log. (low) | area: HW | -

## tests_hardware/heap_map.py
- PLATFORM | tests_hardware/heap_map.py:1-3 | "The device cannot read it back - it goes to the platform print, not `sys.stdout`" | `mem_info(1)` output routing is a MicroPython fact the whole heap-map tier depends on. | area: HW | -
- PLATFORM | tests_hardware/heap_map.py:10-13 | "`gc_dump_alloc_table()` emits 64 blocks per line [SRC, py/gc.c] ... abbreviates two or more consecutive all-free lines. The block size is never printed" | Parser is bound to py/gc.c's dump format; re-check on a MicroPython bump. | area: HW | -
- PLATFORM | tests_hardware/heap_map.py:91-92 | "these metrics assume the single area the rp2 port builds" | Single-heap-area assumption, enforced by a raise. | area: HW | -
- PLATFORM | tests_hardware/heap_map.py:195-213 | "` No. of 1-blocks`" ... "max free sz" | `parse_allocation_need` depends on `mem_info()` summary wording. (low) | area: HW | -
- INVAR | tests_hardware/heap_map.py:59-62 | "a truncated capture ... would otherwise read as a heap with a huge free run at the end, which is exactly the direction that turns a real regression into a pass" | Fail-loud parsing, enforced (total-vs-map check :99-100). | area: HW | -
- LIMIT | tests_hardware/heap_map.py:137-140 | "a LOWER bound - a block occupied in both maps is not attributed, even if the first occupant was freed in between (MEASUREMENTS M2.1)" | HeapDelta under-counts placement. | area: HW | -
- LIMIT | tests_hardware/heap_map.py:162-170 | "Both must come from the same interpreter session ... which is why a mismatch raises" | Only heap geometry is checked; two same-sized maps from different sessions compare silently. (low) | area: HW | -
- ASSUME | tests_hardware/heap_map.py:41-44 | "it is the capacity that has to cover a simultaneous demand (HEAP_FRAGMENTATION_MEASUREMENTS.md archive §7R.2)" | Metric choice rests on an archived measurement section. (low) | area: HW | -
- MIRROR | tests_hardware/heap_map.py:192 | "_ALLOCATION_FAILED = re.compile(r\"MemoryError|memory allocation failed\")" | Separate copy of harness.MEMORY_ERROR_MARKERS, not reached by tests_scripts/test_memory_error_gate_agreement.py. | area: HW | related: TEST.T18

## tests_hardware/ntp_probe.py
- MIRROR | tests_hardware/ntp_probe.py:9 | "matches src/asy_ntp_client.py's own const of the same name" | Copied constant `_NTP_EPOCH_DELTA`. | area: HW | -
- ASSUME | tests_hardware/ntp_probe.py:12-14 | "the only fields src/asy_ntp_client.py's _parse_ntp_reply() actually reads" | Crafted reply (origin timestamp zero) is shaped to today's parser, so it cannot detect a parser that starts validating more. (low) | area: HW | related: NET.T03

## tests_hardware/rogue_udp_responder.py
- SUPPRESS | tests_hardware/rogue_udp_responder.py:53-54 | "pass  # best-effort - a send failure here is not this responder's own test to report" | Swallowed send error. (low) | area: HW | -
- LIMIT | tests_hardware/rogue_udp_responder.py:24-26, 39 | "used by the NTP/DNS garbage-response tests via bench_control.BenchBridge's UDP-port-redirect helpers" | Binds 0.0.0.0 on the bench host; its DNAT-to-loopback delivery path is the documented gap. | area: HW | covered-by: HW.S13

## tests_hardware/website_identity.py
- DRIFT | tests_hardware/website_identity.py:1-2 | "not merely non-empty (queue row G9)" | Cites a deleted queue row from permanent code. | area: HW | covered-by: DOC.S06
- SUPPRESS | tests_hardware/website_identity.py:84-85 | "# noqa: E402  (the sys.path line above is what makes this importable)" | Two E402 suppressions (a `REPO_ROOT =` statement precedes the imports). (low) | area: HW | -
- ASSUME | tests_hardware/website_identity.py:95-96 | "The firmware serves index.html.gz, so the body is gzip whenever the server says so" | Content-Encoding keyed. (low) | area: HW | -
- ASSUME | tests_hardware/website_identity.py:126-127 | "dev is a superset of every other variant today, so no foreign errcount key exists to look for" | Discrimination relies on the device id alone while that superset holds. | area: HW | -
- LIMIT | tests_hardware/website_identity.py:70-72, 102-109 | "Every expected name is derived from `devices/<device>.toml` through buildgen itself" | Oracle is computed from the TREE while the page comes from the IMAGE. | area: HW | related: HW.T19

## tests_hardware/isl29125_conformance.py
- LIMIT | tests_hardware/isl29125_conformance.py:144-157 | "Keys whose value is a function of the actual light falling on the part ... only checked in a light-independent form" | Nine PHYSICAL_KEYS excluded from real-vs-mock diff. | area: HW | related: TWIN.T01
- MIRROR | tests_hardware/isl29125_conformance.py:168-171 | "Same location scripts/test.sh uses, and the same PICO_TOOLCHAIN_DIR override" | Hardcoded copy of the Unix-port path (`build-standard`). | area: HW | -
- ASSUME | tests_hardware/isl29125_conformance.py:193-195 | "-X\", \"heapsize=8M\"" with `TZ=UTC` and a local MICROPYPATH | Twin run uses its own heap size (test.sh uses 16M) and no GC-threshold stage. (low) | area: HW | related: TEST.T18
- SUPPRESS | tests_hardware/isl29125_conformance.py:194 | "# noqa: S603 - every argument is a repo-controlled path, no shell" | Subprocess lint suppression. (low) | area: HW | -

## tests_hardware/bench/dns_probe.py
- SETTLED | tests_hardware/bench/dns_probe.py:1-3 | "hand-rolled rather than pulling in dnspython, matching this project's preference for small hand-rolled protocol code" | Dependency policy. (low) | area: HW | -
- ASSUME | tests_hardware/bench/dns_probe.py:27-30 | "never raises, since \"no response\" is itself a real, assertable outcome (a malformed/off-subnet query should be silently dropped)" | Only a timeout maps to None; silence is treated as the expected captive-DNS behaviour. | area: HW | related: HW.S13
- LIMIT | tests_hardware/bench/dns_probe.py:42-45 | "src/captive_dns.py always answers with exactly one A record, so this doesn't handle the general multi-answer/multi-type case" | Oracle parser tied to one answer shape. | area: HW | -

## tests_hardware/bench/test_network_resilience.py
- SETTLED | tests_hardware/bench/test_network_resilience.py:1-3 | "DHCP-client flakiness is deliberately out of scope (see BACKLOG.md)" | Stated coverage exclusion. | area: HW | -
- ASSUME | tests_hardware/bench/test_network_resilience.py:30-34 | "that case takes the safe \"retry in 60s\" branch and never increments connection_failures or reaches hotspot fallback - read out of the source, not assumed" | Source-derived claim the outage tests are built on; pins current `_on_sta_disconnected()` behaviour. | area: HW | related: NET.S01
- SETTLED | tests_hardware/bench/test_network_resilience.py:49-51, 62-68, 88-89 | "A fallback hard_reset() is a genuine pass per CLAUDE.md; the notes below record which ran" | CYW43 associated-but-dead false positive: the outage/flap tests pass via hard reset, and then skip the WIFI-log check (:72-73, 110-111). | area: HW | related: HW.T05
- ASSUME | tests_hardware/bench/test_network_resilience.py:41-44 | "a brief outage is a fully realistic, low-risk window to inject" | 15 s outage; 3×(3 s down/3 s up) flaps (:80); 150 s recovery wait. | area: HW | -
- ASSUME | tests_hardware/bench/test_network_resilience.py:114-117 | "wrnno=4 (cyw43's BADAUTH, also raised when the AP drops mid-handshake - BACKLOG item 29) ... the password never changes here, so 4 cannot be real" | Tolerated warnings 4/5 in the WIFI log. | area: HW | related: DOC.S13
- MIRROR | tests_hardware/bench/test_network_resilience.py:120-122 | "\"N\" entries are print_log.py's own \"nothing recorded\" padding (get_log()'s own encoding)" | Oracle mirrors print_log's ring encoding. (low) | area: HW | -
- ASSUME | tests_hardware/bench/test_network_resilience.py:134-136, 144-146, 173-175 | "The parameter ranges come from researched real-world WiFi figures (tests_hardware/README.md)" | netem figures (30 %/150±50 ms, 2 %/30±20 ms, corrupt 5 %, dup 10 %/reorder 25 %) and "90s is generous" basis. | area: HW | -
- LIMIT | tests_hardware/bench/test_network_resilience.py:156-158, 205-207, 235-237 | "a brief passive window, purely for the crash check below" | Crash check greps only "Traceback" in a 5 s tail taken AFTER the fault cleared; nothing logged during the fault is seen; no MEMORY_ERROR_MARKERS. | area: HW | related: TEST.T18
- RISK | tests_hardware/bench/test_network_resilience.py:169, 216, 246, 283, 325, 358, 415, 464, 592, 938, 975, 994 | "never leave a deliberately-provoked fault in the live error history" | Nearly every test resets errcount at start and end — deliberate, routine FRAM-evidence clearing with no snapshot. | area: HW | covered-by: HW.S06
- ASSUME | tests_hardware/bench/test_network_resilience.py:220-222 | "checks whether a duplicate or late reply ever gets mismatched against a different, later pending request" | The test only asserts REST reachability, no Traceback and no task ended — narrower than the stated purpose. | area: HW | related: HW.T05
- ASSUME | tests_hardware/bench/test_network_resilience.py:251-253, 275, 279-281 | "the outage outlasts _NTP_CONN_TIMEOUT (5s) but clears inside the 15s retry" | Hardcoded 8 s block / 20 s wait mirror src NTP constants 5 s and 15 s. | area: HW | related: NET.T03
- ASSUME | tests_hardware/bench/test_network_resilience.py:262-264 | "confirmed directly (NtpLastSyncAge showed sync completing only ~12s after dut_ip returned)" | Single observation behind the 30 s precondition wait. | area: HW | -
- DRIFT | tests_hardware/bench/test_network_resilience.py:270-272 vs 434-436, 514-516 | "PUT-ing NTP_Host back to its current value still fires post_asy_fct" vs "The PUT below is then reported \"Unchanged\" and fires no post_asy_fct" | Same file makes opposite claims about whether a same-value (Unchanged) PUT fires the post hook. | area: HW | related: XCUT.T11
- SUPPRESS | tests_hardware/bench/test_network_resilience.py:249, 429, 508 | "@pytest.mark.persistence_write" | Three owned flash writes: NTP_Host re-PUT; garbage NTP_Host + restore; garbage SSID + restore. | area: HW | covered-by: HW.T01
- DRIFT | tests_hardware/bench/test_network_resilience.py:287-289 | "redirect_udp_port_to_local(), which its own docstring marks unverified" | bench_control.py:116-119's docstring does not mark it unverified. (low) | area: HW | related: HW.S13
- ASSUME | tests_hardware/bench/test_network_resilience.py:304, 324 | "generous relative to asy_ntp_client.py's own retry/backoff budget"; "past the ~60s the old NTP give-up needed" | 90 s tail basis refers to an older give-up behaviour. (low) | area: HW | -
- INVAR | tests_hardware/bench/test_network_resilience.py:311, 342 | "assert \"CFGMGR_\" in joined or \"FRAM\" in joined" | Loose "boot finished" oracle. | area: HW | covered-by: HW.S15
- ASSUME | tests_hardware/bench/test_network_resilience.py:312-315 | "whose fixed 10-entry window a full 90s of garbage evicts ... \"Invalid NTP time received!\" ... (errno 14 or 15)" | Oracle bound to a src log string and a 10-entry history window. | area: HW | -
- LIMIT | tests_hardware/bench/test_network_resilience.py:351-355 | "a garbage reply fails the same sanity checks as no reply at all, so resolve_ipv4() exhausts every server and lands on \"NTP\" module's own errno=12" | DNS-garbage test cannot tell garbage from silence; no DNS-client log exists. | area: HW | covered-by: HW.S13
- LIMIT | tests_hardware/bench/test_network_resilience.py:361-364 | "the garbage-response tests cannot reach: DNAT+conntrack rewrites the reply's source back first" | Garbage-response tests never exercise source filtering. | area: HW | related: NET.S19
- MIRROR | tests_hardware/bench/test_network_resilience.py:367 | "safely inside _parse_ntp_reply()'s own 2025-2100 plausibility window" | Spoof date tied to src plausibility window; precondition 2020 < year < 2049 (:377). | area: HW | related: NET.S19
- RISK | tests_hardware/bench/test_network_resilience.py:381-383 | "this bench's known ~1-in-3 reachability hiccup (BACKLOG.md open question 9) can land a hard_reset() in hotspot fallback instead" | Known bench flakiness retried 3×. | area: HW | -
- ASSUME | tests_hardware/bench/test_network_resilience.py:396-404 | "time.sleep(3.0)  # generous relative to _parse_ntp_reply()'s own synchronous RTC().datetime() write" | Spoof pass condition (year != 2050) is also met if the DUT's socket already closed after the real reply — no evidence the spoof arrived while the socket was open. (low) | area: HW | related: HW.T05
- RISK | tests_hardware/bench/test_network_resilience.py:434-437 | "An earlier run aborted before its own restore leaves the board already on the garbage value" | Persisted garbage NTP_Host can outlive an aborted run on the shared board. | area: HW | related: HW.T03
- ASSUME | tests_hardware/bench/test_network_resilience.py:443-446 | "_VAL_NH bounds string length (3-1024) and nothing else" | Pins a validation gap (garbage host accepted "Valid"); same for `_VAL_SSID` (:499, 522-525). | area: HW | related: NET.S17
- LIMIT | tests_hardware/bench/test_network_resilience.py:479-487 | "needing this fallback at all is worth a second look, not an expected outcome" | The hard_reset fallback path prints nothing, so its use is invisible in a passing run. | area: HW | related: HW.T05
- ASSUME | tests_hardware/bench/test_network_resilience.py:498-501 | "It aims to finish inside the ~50s before hotspot fallback takes dut_ip away ... a recovery path is a pass" | Timing budget basis for the garbage-SSID test. | area: HW | -
- MIRROR | tests_hardware/bench/test_network_resilience.py:505 | "_HOTSPOT_PASSWORD = \"12345678\"  # hardcoded in src/asy_wifi_service.py's _configure_hotspot_ap()" | Committed hotspot credential copy #2; its comment calls it hardcoded in `_configure_hotspot_ap()` while conftest.py:165 calls it a `_VAL_HOTSPOT_PW` default declared by every devices/*.toml. | area: HW | covered-by: HW.T11
- RISK | tests_hardware/bench/test_network_resilience.py:520-533 | "put_res = ... {\"SSID\": _GARBAGE_SSID}" followed by bare asserts on the tail log | The garbage-SSID PUT is persisted and the two tail-log asserts run before any restore, outside try/finally — a failure there strands the board off the bench network. | area: HW | related: HW.T03
- INVAR | tests_hardware/bench/test_network_resilience.py:527-529 | "Passive observation only - no exec()/is_reachable(), which disturb a live system" | Caller discipline. | area: HW | covered-by: HW.T06
- ASSUME | tests_hardware/bench/test_network_resilience.py:535-540 | "a reconnect is impossible by construction ... Not actually expected to trigger ..., kept only as a defensive fallback" | Happy-path branch is declared dead. (low) | area: HW | -
- ASSUME | tests_hardware/bench/test_network_resilience.py:585-588 | "matching this tier's established \"a recovery path counts as a pass\" convention" | Convention that recovery-by-reset passes. | area: HW | related: HW.T05
- MIRROR | tests_hardware/bench/test_network_resilience.py:611-617 | "max_connections, three below lwIP's own MEMP_NUM_TCP_PCB"; "the build's own ceiling, never a restated literal" | Ceiling read from the TREE at import; stated relationship to versions.toml PCB count. | area: HW | related: HW.T19
- RISK | tests_hardware/bench/test_network_resilience.py:646-648 | "under load that lag can admit connection _MAX_CONNECTIONS + 1 into the app layer. A real race" | Known transient over-admission by one above the ceiling; test retries up to 3×. | area: REST | related: REST.T06
- ASSUME | tests_hardware/bench/test_network_resilience.py:630-633, 846-849, 1049, 1064, 1079 | "shifting every slot by one (confirmed directly)"; "a slot is released after _serve() awaits the close" | 1.0 s settle sleeps rest on the measured slot-release lag. | area: HW | related: REST.T06
- LIMIT | tests_hardware/bench/test_network_resilience.py:690-693 | "no pr.err_s()/wrn_s() call anywhere on that path, so a real rejection at the connection ceiling is expected to leave WEBSERVER's own error/warning log untouched" | Pins that ceiling rejections are unlogged (invisible in errcount). | area: REST | related: REST.T08
- INVAR | tests_hardware/bench/test_network_resilience.py:697-700, 773-776 | "a schema-rejected field is \"Invalid\" and never reaches write_config()"; "Unknown keys are ignored silently, so nothing validates, persists or logs" | Why these PUT tests carry no `persistence_write` — rests on src behaviour. | area: HW | related: HW.T01
- SETTLED | tests_hardware/bench/test_network_resilience.py:735-738 | "Malformed JSON is an application-level error ... so the HTTP status is still 200 rather than a transport-level 4xx" | Pinned REST contract; relies on vendored microdot's literal "HTTP/1.0" status line. | area: REST | -
- MIRROR | tests_hardware/bench/test_network_resilience.py:750-752, 768-770 | "_BODY_CAP = 2048"; "_OLD_CONTENT_CAP = 4096"; "_SCHEMA_MAX_BODY = 1312 ... derived in tests_scripts/ and asserted here" | Hardcoded copies of src/webserver caps and a derived schema maximum. | area: HW | related: REST.T01
- ASSUME | tests_hardware/bench/test_network_resilience.py:789 | "microdot's Request.create() compares with <=, so the cap itself must still be served" | Relies on vendored microdot comparison. (low) | area: HW | related: REST.T09
- ASSUME | tests_hardware/bench/test_network_resilience.py:800-807 | "The one check that can tell this firmware from the previous one" | A behaviour probe used as an image-identity proxy. | area: HW | related: HW.T19
- INVAR | tests_hardware/bench/test_network_resilience.py:819-824 | "ONE character over _VAL_NH's own 3..1024 bound ... an accepted NTP_Host is a flash write this test must not own" | Wear avoided by construction, depends on src's bound staying 1024. | area: HW | related: HW.T01
- DRIFT | tests_hardware/bench/test_network_resilience.py:848, 890-891 | "Without it the workers start against 3 free slots, not 4"; "The 24 workers' slots" | Counts from an older ceiling; the worker list is 8 × max(3, _MAX_CONNECTIONS) and max_connections is 6 now. (low) | area: HW | -
- DRIFT | tests_hardware/bench/test_network_resilience.py:876-877 | "queue F10 measured ~25%" | Deleted queue row cited. | area: HW | covered-by: DOC.S06
- SUPPRESS | tests_hardware/bench/test_network_resilience.py:861 | "except Exception as exc:  # the worker's job is to report, never to raise into the harness" | Broad catch in worker threads (reported, not dropped). (low) | area: HW | -
- MIRROR | tests_hardware/bench/test_network_resilience.py:906-907 | "_VAL_POV only accepts _OSR_SETTINGS=(1,2,4,8,16,32)" | Oracle mirrors BMP3xx driver constant. (low) | area: HW | -
- DRIFT | tests_hardware/bench/test_network_resilience.py:929-930 | "A rejected key logs errno=12 on its own separate \"CFGMGR_<NAME>\" logger ... in-RAM only" | CLAUDE.md says every `CFGMGR_<name>` logger joined the FRAM-backed set under WP2. | area: HW | related: HW.S23
- MIRROR | tests_hardware/bench/test_network_resilience.py:941-955 | "outer_cap_s=15.0"; "per_call_timeout_s=5.0. One header line every 3s" | Slowloris pacing hardcodes src timeouts. | area: HW | related: REST.T06
- SUPPRESS | tests_hardware/bench/test_network_resilience.py:960-961 | "except OSError: pass  # the server may have already closed the connection" | Swallowed with comment. (low) | area: HW | -
- LIMIT | tests_hardware/bench/test_network_resilience.py:969-970 | "_serve()'s outer wait_for(outer_cap_s) timeout logs wrnno=2 - ... the (also wrnno=2) per-call timeout path" | Two distinct timeouts share one warning number. | area: REST | related: XCUT.T07
- LIMIT | tests_hardware/bench/test_network_resilience.py:987-993 | "would otherwise only surface as a slow, cumulative degradation over many such events"; "No hard assertion on WEBSERVER's error log ... a genuine timing race" | One abrupt disconnect cannot show a cumulative leak; wrnno=3 left unasserted. | area: HW | related: HW.T05
- LIMIT | tests_hardware/bench/test_network_resilience.py:997-1000 | "The only check in the repo that can confirm a raised lwIP MEMP_NUM_TCP_PCB really took effect on silicon - nothing in the twin can, it has no lwIP at all" | Twin fidelity gap; silicon-only evidence. | area: HW | related: HW.T19
- ASSUME | tests_hardware/bench/test_network_resilience.py:1008-1016 | "holding more means the image on the board is not the one this tree describes" | Tree-vs-image equality oracle. | area: HW | related: HW.T19
- ASSUME | tests_hardware/bench/test_network_resilience.py:1060-1063 | "Complete and correct, not merely non-empty" | Checks status 200, a parseable dict with > 0 keys and < 30 s — not content correctness. (low) | area: HW | related: HW.T05
- ASSUME | tests_hardware/bench/test_network_resilience.py:1081 | "2 connections per real page load, post-inlining" | Website request count assumption. (low) | area: HW | related: PERF.T02

## tests_hardware/bench/test_hotspot_role_reversal.py
- INVAR | tests_hardware/bench/test_hotspot_role_reversal.py:1-3, 373-377 | "Definition order matters"; "MUST run after every read-only check above (pytest's default, non-randomized definition order)" | Stage-6 mutation safety depends on unrandomized test order — nothing enforces it. | area: HW | related: HW.S10
- SUPPRESS | tests_hardware/bench/test_hotspot_role_reversal.py:24 | "pytestmark = pytest.mark.role_reversal" | Whole module is informational-marked, not gated: it runs in routine bench passes. | area: HW | covered-by: HW.S25
- WORKAROUND | tests_hardware/bench/test_hotspot_role_reversal.py:27-41 | "`is_ssid_visible()`==True doesn't guarantee nmcli's own internal rescan still sees it a moment later, and this can persist across several attempts" | Up to 5 join retries; `except TimeoutError: pass` falls through; removal trigger: none stated. | area: HW | -
- MIRROR | tests_hardware/bench/test_hotspot_role_reversal.py:43 | "_HOTSPOT_PASSWORD = \"12345678\"  # hardcoded in src/asy_wifi_service.py's _configure_hotspot_ap()" | Committed hotspot credential copy #3. | area: HW | covered-by: HW.T11
- SETTLED | tests_hardware/bench/test_hotspot_role_reversal.py:59-61 | "Its own persisting writes stay UNMARKED per CLAUDE.md's owns-vs-reached-through rule: mark a test that spends a write, never this fixture" | SSID="" at stage 0 plus the stage-7 restore = two unmarked flash writes per module run. | area: HW | covered-by: HW.T01
- RISK | tests_hardware/bench/test_hotspot_role_reversal.py:62-67, 73-89 | "the cleared SSID is persisted to flash, so no reset clears it. It happened on the bench (2026-09-17) and needed a manual serial-side repair" | Restore lives only in post-yield teardown; a failure in stages 1-2 (before `yield`) leaves SSID="" persisted and the bench AP down. | area: HW | covered-by: HW.S10
- ASSUME | tests_hardware/bench/test_hotspot_role_reversal.py:59-60 | "each join/leave costs a real ~15-30s association" | Timing basis for module scope. (low) | area: HW | -
- SUPPRESS | tests_hardware/bench/test_hotspot_role_reversal.py:91-102 | "Best-effort and never raising, so it cannot mask the failure unwinding this fixture" | A rejected/failed stage-7 SSID restore is only printed as "RESULT NOTE"; stage 8 reachability is the only loud check. | area: HW | related: HW.S10
- ASSUME | tests_hardware/bench/test_hotspot_role_reversal.py:105-107, 113-116 | "A failed stage-6 STA reconnect ends in _PHASE_DEACTIVATED, which only a power cycle clears (Part A.4), so recover with hard_reset()" | Treats mpremote `reset` as equivalent to the power cycle Part A.4 requires. | area: HW | related: HW.T06
- LIMIT | tests_hardware/bench/test_hotspot_role_reversal.py:132-133, 136-140, 143-147, 155-156, 366-370, 417-421, 424-428 | "pass  # the joined_hotspot fixture itself only succeeds if stage 0-2 all completed" | Seven tests assert nothing of their own (pass, constant==constant, non-empty) and count as passes. | area: HW | covered-by: HW.S11
- SETTLED | tests_hardware/bench/test_hotspot_role_reversal.py:144-146 | "Documents the known, hardcoded weak credential - not something to silently \"fix\" here, per CLAUDE.md's credential-handling rule" | Accepted-risk credential, restated in test code. | area: SEC | related: SEC.T07
- ASSUME | tests_hardware/bench/test_hotspot_role_reversal.py:173-174 | "A /24 assumption (the common CYW43 AP DHCP range) ... tighten if this proves too loose" | Plausibility-only subnet check; stated follow-up. | area: HW | -
- ASSUME | tests_hardware/bench/test_hotspot_role_reversal.py:179-181 | "Fault injection against the CYW43 firmware's own DHCP server - there is no Python DHCP code here to test" | DHCP lives in CYW43 firmware. (low) | area: HW | -
- ASSUME | tests_hardware/bench/test_hotspot_role_reversal.py:202-203, 210-211, 221-222 | "src/captive_dns.py's response() returns None for this (confirmed by reading the module)" | Tests pin captive_dns behaviour read from source. | area: HW | -
- LIMIT | tests_hardware/bench/test_hotspot_role_reversal.py:226-229 | "logs via pr.evt() (an ordinary event), not err_s()/wrn_s(), so the module's real errcount log should stay empty" | Malformed DNS traffic leaves no errcount trace (pinned). | area: NET | -
- SUPPRESS | tests_hardware/bench/test_hotspot_role_reversal.py:232-241 | "Raw-socket feasibility on the bench Rpi4 not yet checked ... implement once a concrete spoofing mechanism is confirmed to work" | Unconditional `@pytest.mark.skip`: off-subnet DNS source spoofing is untested; a permanent skip in a routine bench run (skip whitelist, `_require_clean_hardware_run.sh`). | area: HW | related: SCR.T05
- LIMIT | tests_hardware/bench/test_hotspot_role_reversal.py:244-247, 256-257 | "What it proves is robustness under flood and recovery after, not the backoff curve"; "the backoff cap is 5s" | Test name (`..._backoff_curve_recovers...`) claims more than it checks; 5 s cap mirrors captive_dns. | area: HW | related: HW.T05
- RISK | tests_hardware/bench/test_hotspot_role_reversal.py:274-281 | "PUT\", \"/notification\", {\"WarnCO2\": 1700}" | Owned flash write (marked) that is never restored: the board keeps WarnCO2=1700 afterwards. | area: HW | related: HW.T03
- ASSUME | tests_hardware/bench/test_hotspot_role_reversal.py:320-322 | "A non-GET to an unmatched path resolves to 405 inside Microdot's routing, before _serve_static() is reached" | Relies on vendored microdot routing; hotspot↔STA toggle deliberately not repeated. (low) | area: HW | related: REST.T07
- LIMIT | tests_hardware/bench/test_hotspot_role_reversal.py:346-347 | "The exact response shape isn't asserted (mock/twin cover that)" | Stated coverage split. (low) | area: HW | -
- LIMIT | tests_hardware/bench/test_hotspot_role_reversal.py:366-370 | "a genuine concurrent multi-client burst ... isn't reproducible in hotspot mode with only one bench radio available" | Stated gap: no multi-client load test in AP mode. | area: HW | -
- ASSUME | tests_hardware/bench/test_hotspot_role_reversal.py:382-384 | "post_fct (the /networking group's reconnect_wifi() hook) fires if ANY field validates, so sending PW alone keeps `results` to one entry" | Pins post-hook semantics; the test is `persistence_write`-marked though its all-invalid PUT persists nothing. (low) | area: HW | related: XCUT.T11
- DRIFT | tests_hardware/bench/test_hotspot_role_reversal.py:396-398 | "see tests_hardware/README.md for why this PUT is required (stage 7's flip-back depends on it)" | Stage 6 is `persistence_write`-deselected by default, and the fixture now restores the SSID itself (:62-67, 94-97). (low) | area: HW | related: HW.S10
- ASSUME | tests_hardware/bench/test_hotspot_role_reversal.py:399 | "os.environ.get(\"BENCH_AP_PASSWORD\") or bench.ap_password()" | Run-time bench credential read (the HW.T11 convention); the bench PSK is then persisted in the DUT's flash config. | area: HW | related: HW.T11
- OPENQ | tests_hardware/bench/test_hotspot_role_reversal.py:425-427 | "adding one would be a src/ change to put to the owner rather than make unasked. The proxy: dut_ip being reachable at all means STA mode" | No `_conn_phase` field on GET; STA state only inferred. (low) | area: HW | -

## tests_hardware/bench/test_bus_concurrency_under_api_load.py
- MIRROR | tests_hardware/bench/test_bus_concurrency_under_api_load.py:19-21 | "VOC_MIN, VOC_MAX = 0, 500  # same bounds as device_scripts/sgp40_voc_algorithm_quality.py" | Plausibility bounds (CO2 200-10000 ppm, Pres 300-1250 hPa, VOC 0-500) copied across files. | area: HW | -
- INVAR | tests_hardware/bench/test_bus_concurrency_under_api_load.py:23-26 | "two slots under the build's own max_connections: at it, real wireless timing overlaps into an undesired reject-when-full" | Worker count derived from the TREE's ceiling (minus 3), not the image's. | area: HW | related: HW.T19
- INVAR | tests_hardware/bench/test_bus_concurrency_under_api_load.py:42-45 | "Same name and positional signature on purpose: tests_scripts/test_persistence_write_marker_completeness.py reads PUT bodies by AST and would silently lose a persisting write behind another shape (F15)" | The wear-marker guard only sees PUTs of a specific call shape; cites "F15". | area: HW | related: HW.S05
- SUPPRESS | tests_hardware/bench/test_bus_concurrency_under_api_load.py:29-30, 46-55 | "retrying only a connection-ceiling refusal, never a transport failure"; "BACKLOG 30's resets share their signature" | Ceiling refusals are retried up to 3× and only printed (CEILING_RETRIES); an ISL29125 mechanism reset looks the same. | area: HW | -
- LIMIT | tests_hardware/bench/test_bus_concurrency_under_api_load.py:58-61 | "A value outside it is not a driver bug but a torn/corrupted read" | Torn-read oracle only catches out-of-schema values (MeasInt 2..1800, PressOvers set, Resolution 12/16, VOC 0..500 — hardcoded schema copies); an in-range torn read is invisible. | area: HW | related: HW.T05
- ASSUME | tests_hardware/bench/test_bus_concurrency_under_api_load.py:104-112 | "{\"SGP40\": {\"SGPResetVOC\": True}}" | SGPResetVOC PUTs in unmarked tests (:81, :162, :311) are treated as dispatch-only (no persisting write). (low) | area: HW | related: HW.T01
- RISK | tests_hardware/bench/test_bus_concurrency_under_api_load.py:124-126 | "A real WiFi reconnect blip (BACKLOG.md open question 6 ...) can land right after this heavy load ... a transient GET /status 500 that self-heals" | A transient 500 on /status after load is tolerated by a 30 s wait. | area: HW | related: REST.T06
- LIMIT | tests_hardware/bench/test_bus_concurrency_under_api_load.py:134-138 | "must all report nothing wrong" | Checked loggers are SCD30/BMP3XX/SGP40/ISL29125/FRAM only; the first test has no `assert_no_task_ended` and no WEBSERVER check. (low) | area: HW | related: HW.T05
- SUPPRESS | tests_hardware/bench/test_bus_concurrency_under_api_load.py:172-181, 183-192, 252-272, 321-341 | "except Exception: continue" / "if res.status_code != 200: continue" | Compound-fault variants drop every failed request with no engagement floor — a run where no request succeeded still passes. | area: HW | related: HW.T05
- SETTLED | tests_hardware/bench/test_bus_concurrency_under_api_load.py:222-225, 304-307 | "Recombination test (owner's request)" | Owner-requested compound tests. | area: HW | -
- SUPPRESS | tests_hardware/bench/test_bus_concurrency_under_api_load.py:229, 398, 488 | "@pytest.mark.persistence_write" | Owned flash writes: NTP_Host re-PUT; 4 ISL29125 Resolution writes + restore; 4 BMP3XX PressOvers writes + restore. | area: HW | covered-by: HW.T01
- ASSUME | tests_hardware/bench/test_bus_concurrency_under_api_load.py:276-277, 286-288, 295 | "post_asy_fct fires on ANY validated field, even one PUT back to its own current value"; "This join alone virtually guarantees it outlasts the 5s _NTP_CONN_TIMEOUT"; "15s _NTP_RETRY_INTERV" | Unchanged-PUT hook claim (see the DRIFT in test_network_resilience.py) and hardcoded NTP constants; outage length is not guaranteed. | area: HW | related: XCUT.T11
- SETTLED | tests_hardware/bench/test_bus_concurrency_under_api_load.py:373-384 | "Same accepted real-pass pattern ... a hard_reset() fallback is a genuine recovery, not a failure" | Module-log checks skipped on the hard-reset path. | area: HW | related: HW.T05
- INVAR | tests_hardware/bench/test_bus_concurrency_under_api_load.py:388-392, 480-482 | "per Part C.8's standing rule: every flash-tier bus hazard gets a bench-tier counterpart"; "flash-tier bus-hazard coverage is always a subset of bench-tier coverage" | Tier-parity rule, review-enforced. | area: HW | related: HW.T09
- MIRROR | tests_hardware/bench/test_bus_concurrency_under_api_load.py:394-395, 485, 521-523 | "(asy_isl29125_driver.py's own _RESOLUTIONS)"; "(asy_bmp3xx_driver.py's own _OSR_SETTINGS)"; "PressOvers' driver default IS _BMP3XX_OVERSAMPLING_SETTINGS[0]" | Driver constants copied; 4 cycles vs flash tier's 8. (low) | area: HW | -
- ASSUME | tests_hardware/bench/test_bus_concurrency_under_api_load.py:431-432 | "an equal PUT reports \"Unchanged\" and _set_dict_cfg() pushes only \"Valid\" fields live, so it would reach no hardware" | Pins setter semantics. | area: HW | related: XCUT.T11
- DRIFT | tests_hardware/bench/test_bus_concurrency_under_api_load.py:474-476 | "the driver registers no push callback at all - so no PUT can reach its NVM write" | Additional site of the structural-exception-1 claim the plan says is contradicted (SCD30 NVM reachable over REST). | area: HW | covered-by: HW.S02
- SETTLED | tests_hardware/bench/test_bus_concurrency_under_api_load.py:561-563 | "that is Part C.8's structural exception 2: the broadcast fires only from _reset() at setup. SGPResetVOC ... reaches a software-only reset instead" | Structural exception for the SGP40 general-call hazard. | area: HW | covered-by: HW.T09

## tests_hardware/bench/test_end_to_end_timing.py
- LIMIT | tests_hardware/bench/test_end_to_end_timing.py:19-22, 40-41 | "storage_pause()-then-wait genuinely completes before the real reset fires, WDT isn't starved mid-sequence" | The oracle is only "USB went away, then came back": a WDT reset and the intended `machine.reset()` look the same (no `reset_cause()` read). | area: HW | related: HW.T05
- RISK | tests_hardware/bench/test_end_to_end_timing.py:26-28, 41 | "is_reachable() soft-resets the board's heap on every poll (raw-REPL entry Ctrl-D's first), wiping the very Timer this test waits on" | The post-reboot wait still polls `board.is_reachable`, which stops the freshly booted main.py; webserver recovery then depends on the WDT reset or the hard_reset fallback (:48-53). | area: HW | related: HW.T06
- ASSUME | tests_hardware/bench/test_end_to_end_timing.py:32-34, 37-39, 42-44 | "this is a genuine machine.reset() under the hood"; "not this test's to assume a specific value for"; "it starts only after ntp_force_sync() (up to ~20s)" | Reboot-path timing assumptions; 30 s waits. | area: HW | -
- PLATFORM | tests_hardware/bench/test_end_to_end_timing.py:57-58 | "the segfault this originally chased is confirmed compiled out of real rp2 firmware" | Claimed platform fact behind keeping the burst test as robustness-only. | area: HW | related: PLAT.T06
- DRIFT | tests_hardware/bench/test_end_to_end_timing.py:85-88 | "The webserver must still answer afterwards" vs "assert board.is_device_present() or http_client.fetch(...) == 200" | The `or` short-circuits on USB presence, so the post-burst HTTP check never runs while the board is attached. | area: HW | related: HW.T05
- ASSUME | tests_hardware/bench/test_end_to_end_timing.py:63-66, 84 | "keeps serving at least the ceiling's own worth of requests" | Burst oracle ≥ tree ceiling successes out of 2× ceiling. | area: HW | related: HW.T19
- TODO | tests_hardware/bench/test_end_to_end_timing.py:92-93, 105, 110 | "Reported/sanity-bounded, not asserted against a tight SLA - no measured baseline exists yet" | Cold-boot latency has no asserted threshold (120 s ceiling, printed only). | area: HW | related: PERF.T01
- SETTLED | tests_hardware/bench/test_end_to_end_timing.py:120-123 | "Recombination test (owner's explicit request) ... The flash tier's reset race can only land as a write session begins" | Owner-requested; states the flash-tier race's reach limit. | area: HW | -
- SUPPRESS | tests_hardware/bench/test_end_to_end_timing.py:127, 134-139, 181-205 | "@pytest.mark.persistence_write"; "BackupPeriod=1 (minute) is the schema's fastest active cadence" | Owned flash writes: BackupPeriod=1 + restore; ≥3 hard resets land during production FRAM backups; restore checks only HTTP 200, not the result. | area: HW | covered-by: HW.T01
- LIMIT | tests_hardware/bench/test_end_to_end_timing.py:143-145 | "can't be synchronized to the real SPI write itself from the host side" | No evidence any reset actually landed mid-write; checks SGP40/FRAM logs only (:168-169), not SYSTEM. | area: HW | related: HW.T05
- RISK | tests_hardware/bench/test_end_to_end_timing.py:148-149 | "(see BACKLOG.md open question 9)" | Known intermittent unreachability after a hard reset, retried once. | area: HW | -

## tests_hardware/bench/test_heap_under_connection_ceiling.py
- MIRROR | tests_hardware/bench/test_heap_under_connection_ceiling.py:22-25 | "microdot reads one only when Content-Length > 0, up to max_content_length (2048), contiguously" | Per-connection demand hardcoded to src's body cap. | area: HW | related: MEM.T03
- MIRROR | tests_hardware/bench/test_heap_under_connection_ceiling.py:26-27 | "The script's own window is 90s and it prints READY about 20s in" | Timing coupled to device_scripts/heap_under_connection_ceiling.py. (low) | area: HW | -
- ASSUME | tests_hardware/bench/test_heap_under_connection_ceiling.py:28-30 | "measured on silicon at 5.12-5.16s plain, 15.1s dripping (SPECIFICATION.md Part H.7.1)" | Single measurement behind drip 2 s / recycle 10 s constants. | area: HW | related: REST.T06
- ASSUME | tests_hardware/bench/test_heap_under_connection_ceiling.py:35-40 | "_MIN_FRACTION_AT_CEILING = 0.55"; "A refusal is a FIN ~6 ms after connect" | Peak-reading threshold and 0.3 s admission wait, from measurement. | area: HW | -
- INVAR | tests_hardware/bench/test_heap_under_connection_ceiling.py:105-106, 122-127 | "a worker that outlives its test hammers the board for the rest of the pytest session, which took down 37 unrelated tests once" | Holder-thread teardown obligation, asserted in-test. | area: HW | -
- LIMIT | tests_hardware/bench/test_heap_under_connection_ceiling.py:88-91, 121 | "the script's own boot, not main.py's" | Heap is measured with `sensortask_dev.main()` started by a device script under run_isolated (production boot plus a sampler in the same process), not a natural power-on boot. | area: HW | related: HW.T05
- LIMIT | tests_hardware/bench/test_heap_under_connection_ceiling.py:151-156 | "A floor on the absolute bytes would be a guess; this is the actual requirement" | Only placeability of `ceiling` × 2048 B is asserted. | area: HW | -
- SUPPRESS | tests_hardware/bench/test_heap_under_connection_ceiling.py:159-172 | "@pytest.mark.over_provisioned_image" | Informational marker; runs on every image and `pytest.fail`s only when fewer than configured are admitted. | area: HW | covered-by: HW.S25
- DRIFT | tests_hardware/bench/test_heap_under_connection_ceiling.py:161-163, 171 | "Row 5 of the decision table, and the reason §5 needs only two images"; "use §6's LWIP_STATS image" | Named citations into HEAP_FRAGMENTATION_MEASUREMENTS.md sections without a file name. | area: HW | covered-by: DOC.S05

## tests_hardware/bench/test_memory_stress_bench.py
- DRIFT | tests_hardware/bench/test_memory_stress_bench.py:19-22 | "WIFI/NTP/every CFGMGR_* logger are RAM-only" | `_FRAM_BACKED_MODULES` omits WIFI, NTP, WEBSERVER, DNSSRV, CFGMGR_*, UART_* against CLAUDE.md's list. | area: HW | covered-by: HW.S23
- DRIFT | tests_hardware/bench/test_memory_stress_bench.py:24-30 | "4 GET threads at true max speed" | Thread count is now `configured_max_connections()` (6). (low) | area: HW | -
- ASSUME | tests_hardware/bench/test_memory_stress_bench.py:24-27 | "reproduces the request density that originally found real MemoryErrors within 45s. Not soak-tier gated - 120s needs no --soak-tier flag to run" | A 120 s max-speed hammer runs in every routine bench pass; basis is one historical finding. | area: HW | -
- LIMIT | tests_hardware/bench/test_memory_stress_bench.py:53-55 | "ConnectionResetError is the server's intended reject-when-full behavior, not a fault - not asserted against" | All non-200 outcomes are collected but never asserted. | area: HW | -
- ASSUME | tests_hardware/bench/test_memory_stress_bench.py:107, 127, 174 | "assert success_count > 100"; "assert len(request_errors) < 5" | Liveness/error thresholds with no stated basis (the < 5 applies to runs up to 6 h). | area: HW | related: HW.S14
- MIRROR | tests_hardware/bench/test_memory_stress_bench.py:91-95, 168-171 | "\"config is ready\"/\"FRAM SPI FRAM Driver Setup complete\" are the genuinely one-time-per-setup() completion lines" | Reboot detection depends on src log strings (and their DebugLevel). | area: HW | covered-by: HW.S14
- RISK | tests_hardware/bench/test_memory_stress_bench.py:101, 108, 120, 132 | "reset_all_error_logs(dut_ip)" | Resets at start of both hammer tests, before any snapshot. | area: HW | covered-by: HW.S06
- ASSUME | tests_hardware/bench/test_memory_stress_bench.py:113-115, 118 | "--soak-tier mid = 600s, matching the one real WDT_RESET this project has observed" | Soak duration chosen from a single event. | area: HW | -
- SETTLED | tests_hardware/bench/test_memory_stress_bench.py:129-131 | "Deliberately only cleared AFTER the assertions above have already captured/reported whatever FRAM-backed history existed ... per this file's own new standing rule" | Evidence-before-clear rule applied only at the end of this one test. | area: HW | related: HW.T02
- LIMIT | tests_hardware/bench/test_memory_stress_bench.py:135-174 | "test_real_hardware_memory_does_not_leak_under_real_http_soak_traffic" | "Does not leak" is asserted only as no crash/reboot marker and < 5 errors — no heap trend. | area: HW | covered-by: HW.S14
- DRIFT | tests_hardware/bench/test_memory_stress_bench.py:156 | "a modest, sustained request rate - not a flood (that's item 17's job)" | Dangling "item 17" reference. (low) | area: HW | -
- SUPPRESS | tests_hardware/bench/test_memory_stress_bench.py:111, 116-118, 135, 137-139 | "pytest.skip(\"real extended max-speed hammer load - run via scripts/run_bench_soak_tests.sh --tier mid ...\")" | Two `long_soak` in-test skips. | area: HW | covered-by: HW.T13

## tests_hardware/bench/test_rest_endpoints_over_sta.py
- DRIFT | tests_hardware/bench/test_rest_endpoints_over_sta.py:34-35 | "(queue row G9)" | Deleted queue row cited. | area: HW | covered-by: DOC.S06
- MIRROR | tests_hardware/bench/test_rest_endpoints_over_sta.py:1-3, 18-24 | "Bounds mirror the flash-tier isolated-driver plausibility scripts' own datasheet-sourced bounds" | Copied bounds; CO2 floor here is 400 ppm vs 200 ppm in test_bus_concurrency_under_api_load.py:19. (low) | area: HW | -
- LIMIT | tests_hardware/bench/test_rest_endpoints_over_sta.py:50-51 | "for name in (\"SCD30\", \"BMP3XX\", \"SGP40\")" | ISL29125 (dev-only) values are not checked over REST. (low) | area: HW | -
- SETTLED | tests_hardware/bench/test_rest_endpoints_over_sta.py:102-104 | "the window is a fixed 300s and the duration is never client-suppliable, so no REST unpause exists ... the pause is RAM-only" | Pins mempause semantics; recovery by hard reset. | area: HW | related: STOR.T05
- RISK | tests_hardware/bench/test_rest_endpoints_over_sta.py:93 | "a previous test left the bench in a paused state" | Cross-test state leakage precondition. (low) | area: HW | -
- SUPPRESS | tests_hardware/bench/test_rest_endpoints_over_sta.py:124-128 | "this test OWNS its persisting writes (the probe PUT and the restore PUT), unlike the dispatch-only ISLCalibrate push, which stores nothing" | Two owned flash writes; ISLCalibrate asserted dispatch-only. | area: HW | covered-by: HW.T01
- MIRROR | tests_hardware/bench/test_rest_endpoints_over_sta.py:118-120, 134-136 | "GainRatio is ordinary user-PUT config now, not a self-learned runtime value"; "Inside the driver's own [20, 34] band" | Classification decision and driver band copied. (low) | area: HW | -

## tests_hardware/bench/test_sensor_config_push_over_real_hardware.py
- MIRROR | tests_hardware/bench/test_sensor_config_push_over_real_hardware.py:17-20, 25-27 | "Different from every driver default (PressOvers=1, TempOvers=1, FiltCoeff=0)"; "Of its ten config fields only these four are hardware-backed with a real get-back path" | Driver defaults, discrete settings and ISL29125 field classification copied into the test. | area: HW | -
- DRIFT | tests_hardware/bench/test_sensor_config_push_over_real_hardware.py:22-23 | "SCD30 has no live-push config fields at all (asy_scd30_driver.py registers no _push_callbacks)" | Contradicted by the SCD30 REST dispatch path per the plan. | area: HW | covered-by: HW.S02
- ASSUME | tests_hardware/bench/test_sensor_config_push_over_real_hardware.py:29-31 | "under auto-range the chip's range bit is the state machine's pick, not the user's, so _read_sensor_dict() omits Range from a live snapshot entirely" | Pins ISL29125 read-back behaviour; test forces RangeAuto False. (low) | area: HW | -
- RISK | tests_hardware/bench/test_sensor_config_push_over_real_hardware.py:41-45, 81-85 | "An earlier run aborted before its own restore leaves the board already holding a test value" | Persisted test values can outlive an aborted run; the test refuses to run rather than repairing. | area: HW | related: HW.T03
- SUPPRESS | tests_hardware/bench/test_sensor_config_push_over_real_hardware.py:35, 75 | "@pytest.mark.persistence_write" | Owned flash writes: BMP3XX 3-field push + restore; ISL29125 5-field push + restore (plus live register writes). | area: HW | covered-by: HW.T01
- ASSUME | tests_hardware/bench/test_sensor_config_push_over_real_hardware.py:69-70 | "config_manager.py's errno=12 only fires on a rejected key" | Oracle for an empty CFGMGR log. (low) | area: HW | -
- ASSUME | tests_hardware/bench/test_sensor_config_push_over_real_hardware.py:116-118, 131, 146-147 | "PauseTime is dispatch-only"; "real ~1s-per-tick auto_led_override() cadence"; "SGPResetVOC is command-only (never persisted - see asy_sgp40_driver.py's _VAL_RESET comment)" | Why these PUTs carry no `persistence_write` marker. | area: HW | related: HW.T01
- LIMIT | tests_hardware/bench/test_sensor_config_push_over_real_hardware.py:153-157 | "The sensor must still be alive and producing real readings afterward" | Only a 200 on /measurements and an empty SGP40 log are checked, no reading values. (low) | area: HW | related: HW.T05
- LIMIT | tests_hardware/bench/test_sensor_config_push_over_real_hardware.py:175-187 | "Its PRESENCE is the contract, not its value - a run that finds no usable scene legitimately leaves it null, and the bench light is not arranged" | ISL29125 calibration is not validated on silicon; only "applied ratio unchanged" and "GainMeas key present". | area: HW | -

## tests_hardware/bench/test_serving_heap_at_default_gc.py
- MIRROR | tests_hardware/bench/test_serving_heap_at_default_gc.py:25-31 | "under the device script's own 10 s quiet-to-leave"; "the device starts dumping 20 s into its own boot" | Host timings coupled to device_scripts/serving_at_default_gc.py. (low) | area: HW | -
- ASSUME | tests_hardware/bench/test_serving_heap_at_default_gc.py:32-35 | "Fixed, the worst route needs 320-336 B (board and 32-bit twin); pre-fix needs were 512-1,536 B ... the measured rung cannot flip the verdict" | `_MAX_ROUTE_NEED = 480` rests on one measurement set (SPECIFICATION Part I.3). | area: HW | related: MEM.T06
- INVAR | tests_hardware/bench/test_serving_heap_at_default_gc.py:39-40 | "body DRAINED rather than materialised - the drain rule, so the host measures the board and never its own buffering" | Measurement discipline shared with the twin HTTP client test. (low) | area: HW | -
- INVAR | tests_hardware/bench/test_serving_heap_at_default_gc.py:84-85, 131-134 | "`stop` guarantees it cannot outlive its test - a driver that did took 37 tests down once" | Load-driver teardown obligation, asserted in-test. | area: HW | -
- LIMIT | tests_hardware/bench/test_serving_heap_at_default_gc.py:1-3, 101-110, 130 | "Serving at MicroPython's own gc default"; "Both tests stop main.py" | Numbers come from device-script builds under run_isolated (not the production boot) at the reactive gc default, not the firmware's 32768 threshold. | area: HW | related: HW.T05
- ASSUME | tests_hardware/bench/test_serving_heap_at_default_gc.py:146-150 | "expected {admitted} served, the rest refused cleanly" | Exact `served == min(n, ceiling) × rounds` oracle uses the TREE's ceiling. (low) | area: HW | related: HW.T19

## tests_hardware/bench/test_uart_link_under_api_load.py
- MIRROR | tests_hardware/bench/test_uart_link_under_api_load.py:20-21 | "asy_uart_link_driver.UartLinkExerciser's own name_ext=\"init\"/\"resp\" -> instance_name() resolution" | Hardcoded logger names mirror devices/dev.toml + buildgen catalog. | area: HW | -
- INVAR | tests_hardware/bench/test_uart_link_under_api_load.py:22-23 | "A PUT belongs in this tier only where it is documented command-only and never persisted" | Wear rule for this file, by convention. (low) | area: HW | related: HW.T01
- SUPPRESS | tests_hardware/bench/test_uart_link_under_api_load.py:39-43, 51-57 | "Absent entries are therefore a build to check, not a protocol failure" | A firmware that drops UARTLINK or the UART loggers turns into skips, not failures. | area: HW | related: HW.T13
- LIMIT | tests_hardware/bench/test_uart_link_under_api_load.py:31-34, 111-114 | "an idle link and a healthy one both leave that at zero"; "Its two neighbours assert the link logged no errors, which an idle link satisfies too" | Tests 1 and 3 pass on an idle link; only test 2 checks transfers. | area: HW | related: HW.T05
- DRIFT | tests_hardware/bench/test_uart_link_under_api_load.py:143-150 | "The link must have progressed *during* the hammering" | The transfer check polls up to 30 s AFTER the load window, so a post-load transfer also passes. (low) | area: HW | related: HW.T05
- MIRROR | tests_hardware/bench/test_uart_link_under_api_load.py:143-144 | "One exerciser period is 1s" | Exerciser period copied from src. (low) | area: HW | -
- DRIFT | tests_hardware/bench/test_uart_link_under_api_load.py:160-162, 177 | "a burst past the server's comfortable concurrency" vs "range(6)" | Hardcoded 6 now equals max_connections (6), so the burst no longer exceeds the ceiling. (low) | area: HW | -
- SUPPRESS | tests_hardware/bench/test_uart_link_under_api_load.py:172-173 | "except Exception:  # a rejected connection under a deliberate overload is an accepted outcome" | Every exception accepted; floor is "at least one 200". (low) | area: HW | -

## tests_hardware/bench/test_wifi_networking.py
- RISK | tests_hardware/bench/test_wifi_networking.py:30-32 | "measured 2026-09-19: 1 miss in 3 full suite runs, 12/12 clean in isolation, CYW43 reporting status -1 after the firmware's own two retries ... queue F13" | Known STA association flakiness tolerated by a second cold boot; cites a deleted queue row. | area: HW | covered-by: DOC.S06
- LIMIT | tests_hardware/bench/test_wifi_networking.py:54-59 | "assert \"NTP\" in joined" | "Real NTP round-trip" is inferred from any NTP log line plus absence of fail/error/timeout words in an arbitrary 60 s window; no sync is provoked. | area: HW | related: HW.T05
- LIMIT | tests_hardware/bench/test_wifi_networking.py:67-70 | "observed DNS failure/error log lines during a window with no fault injected" | DNS test only asserts absence of failure lines — passes when no DNS activity is logged at all. | area: HW | related: HW.T05
- INVAR | tests_hardware/bench/test_wifi_networking.py:97 | "assert \"CFGMGR_\" in joined or \"FRAM\" in joined" | Loose boot-finished oracle (additional site). | area: HW | covered-by: HW.S15
- ASSUME | tests_hardware/bench/test_wifi_networking.py:108-112 | "errno 21 (no reply) is logged and the task backs off in place"; "Task ended - attempting restart" | Pins NTP errno and a supervisor log string. | area: HW | related: XCUT.T07
- DRIFT | tests_hardware/bench/test_wifi_networking.py:16-18, 80 | "Item 7 - real STA connect/disconnect"; "BACKLOG open question 6" | Unanchored "Item 7" numbering. (low) | area: HW | -

## tests_hardware/flash/test_bus_concurrency.py
- SUPPRESS | tests_hardware/flash/test_bus_concurrency.py:23, 31, 38, 44, 68, 76, 85-86 | "@pytest.mark.persistence_write" / "@pytest.mark.scd30_extra_write" | Seven SCD30-fixture dependents gated (one NVM write per session), plus the AND-gated second SCD30 NVM write at :85-92. | area: HW | covered-by: HW.T13
- LIMIT | tests_hardware/flash/test_bus_concurrency.py:23-28 | "This test exists only to give that one real NVM write its own named, first-to-run pass/fail surface" | Body is `pass`; first-to-run relies on definition order. (low) | area: HW | related: HW.T05
- ASSUME | tests_hardware/flash/test_bus_concurrency.py:33-34 | "Generous relative to the device script's own ~90s internal asyncio.wait_for budget" | Script runs ~90 s under run_isolated's 8 s WDT, so it must feed the WDT itself. | area: HW | related: HW.S09
- PLATFORM | tests_hardware/flash/test_bus_concurrency.py:53-55, 61-63, 80 | "BMP3xx's own config registers are volatile"; "FN8424 p7 calls the ISL29125's config registers volatile outright"; "the DESTRUCTIVE 0x08 status read" | Datasheet facts behind leaving these write tests unmarked. | area: HW | related: HW.T01
- OPENQ | tests_hardware/flash/test_bus_concurrency.py:96-98 | "the two datasheet questions no document answers - whether a CONFIG1 write restarts the conversion, and whether PRST counts RGB cycles or single-channel integrations ... neither gates the pass" | Open ISL29125 datasheet questions, measured and reported only. | area: SENS | -
- ASSUME | tests_hardware/flash/test_bus_concurrency.py:104-106 | "this sweep only ever *reads* SCD30 ... its self-hazard branch doesn't need continuous measurement" | Sweep's claims rest on the device script (whose probes the plan says cannot fail). | area: HW | covered-by: HW.S12
- PLATFORM | tests_hardware/flash/test_bus_concurrency.py:111-114 | "FRAM's real datasheet endurance is 10^13 read/write operations per byte" | Endurance figure for MB85RS2MTA; the plan notes 10^12 for MB85RS64V — which part dev has is open. | area: HW | related: HW.T07
- DRIFT | tests_hardware/flash/test_bus_concurrency.py:120-122 | "(BACKLOG.md open question 8's \"not currently provisioned\" GPIO harness doesn't apply here)" | Quotes a BACKLOG item as unsettled. | area: HW | covered-by: DOC.S05
- RISK | tests_hardware/flash/test_bus_concurrency.py:127-137 | "Real hardware-reset race against an in-flight FRAM write"; "there is no live system to protect here" | Reset-raced write against production's own FRAM chunks; the seed script's outcome is ignored (run_isolated_expect_reset). | area: HW | covered-by: HW.T17
- PLATFORM | tests_hardware/flash/test_bus_concurrency.py:140-143 | "Both claims were read out of the rp2 port's own protocol tables and modelled in tests/machine.py and digital_twin/machine.py - but a fake agreeing with a fake proves nothing about silicon" | F.5.1 deinit/singleton claims need silicon confirmation. | area: PLAT | related: PLAT.T06

## tests_hardware/flash/test_bus_electrical_timing.py
- LIMIT | tests_hardware/flash/test_bus_electrical_timing.py:52-54 | "can't fully disambiguate a genuine hardware edge from the fallback purely in software (a scope on the pin would be the only certain check)" | SCD30 IRQ-edge test cannot prove the edge path. | area: HW | related: HW.T05
- PLATFORM | tests_hardware/flash/test_bus_electrical_timing.py:76-79 | "the ~150ms stretch happens roughly once a day for internal calibration (Interface Description p.2, cited in tests/_sensortask_scenarios.py too)" | Datasheet fact mirrored in the unit tier. | area: HW | -
- LIMIT | tests_hardware/flash/test_bus_electrical_timing.py:87-93 | "a \"never observed to fail\" soak, not \"confirmed exercised\" (only the \"long\" tier runs long enough to likely observe the ~once/day event)" | A 6 h "long" tier for a ~once/day event; string-match oracle. | area: HW | covered-by: HW.S14
- SUPPRESS | tests_hardware/flash/test_bus_electrical_timing.py:82-86, 110-116 | "pytest.skip(\"real SCD30 clock-stretch events are opportunistic ...\")"; "pytest.skip(\"real ~12.4-day wait ...\")" | `long_soak` and `multi_day_rollover` in-test skips. | area: HW | covered-by: HW.T13
- TODO | tests_hardware/flash/test_bus_electrical_timing.py:96-101, 131-138 | "Expect this to be the outcome as long as this test polls with board.exec() ... that redesign is tracked in REAL_HARDWARE_TEST_QUEUE.md, not worked around here" | The gated ticks_ms rollover test is known to fail by construction (each `exec` starves the WDT and zeroes the counter). | area: HW | related: HW.T13
- PLATFORM | tests_hardware/flash/test_bus_electrical_timing.py:99-101 | "BACKLOG item 12 answered the soft_reset() question ... the counter is free-running - but ... every `mpremote exec` starves the watchdog into a hard reset that DOES zero it" | ticks_ms survives soft reset; a WDT reset zeroes it. | area: PLAT | related: HW.T06
- ASSUME | tests_hardware/flash/test_bus_electrical_timing.py:104-107, 122 | "Two hours of headroom, wider than the poll interval below" | `_WRAP_FLOOR_MS` and 3600 s polling. (low) | area: HW | -
- DRIFT | tests_hardware/flash/test_bus_electrical_timing.py:30, 41, 52, 65, 76, 97 | "Item 2 - soft Timer callback drop ..." | Unanchored "Item N" numbering. (low) | area: HW | -

## tests_hardware/flash/test_fram_storage.py
- DRIFT | tests_hardware/flash/test_fram_storage.py:1 | "real MB85RS64V SPI FRAM chip coverage" | Device scripts and dev_legacy name MB85RS2MTA. | area: HW | covered-by: HW.S17
- ASSUME | tests_hardware/flash/test_fram_storage.py:42-43 | "~90s real runtime (60s to the first natural BackupPeriod trigger, plus restore-cycle margin)" | 150 s timeout basis. (low) | area: HW | -
- SETTLED | tests_hardware/flash/test_fram_storage.py:57-59 | "Losing the whole history to a reset landing mid-write is accepted (owner, 2026-09-11; Part C.3.1); a PARTIAL restore never is" | Accepted all-or-nothing loss of error history. | area: STOR | related: STOR.T01
- LIMIT | tests_hardware/flash/test_fram_storage.py:57-58 | "simulates a fresh boot in the SAME process and so only ever shows the happy path" | fram_error_log_roundtrip.py's reboot is simulated, not real. | area: HW | -
- SETTLED | tests_hardware/flash/test_fram_storage.py:77-82 | "Reads being gated too is intended (Part A.4's FRAM entry)"; "Flash-only, no bench counterpart, structurally (E.6.6 exception 2): get_write_protected()/set_write_protected() have no REST route at all" | Structural-exception claim for FRAM write-protect. | area: HW | covered-by: HW.T09
- PLATFORM | tests_hardware/flash/test_fram_storage.py:91-93, 98-100 | "the ONE_SHOT auto-unpause really fires on an rp2 alarm pool"; "the 2s/2s/6s auto-unpause windows plus margins, and the exhausted-alarm-pool step's own window" | Hardware-only timer claims. (low) | area: HW | related: PLAT.T03
- LIMIT | tests_hardware/flash/test_fram_storage.py:105-108 | "The overrun is a DMA timing condition no Python knob can induce on target, so this tests its consequence" | SPI RX-overrun itself is untested on silicon. | area: HW | related: PLAT.T03
- SETTLED | tests_hardware/flash/test_fram_storage.py:116-118 | "mpremote-only by design (owner's own decision) - no new /status field, this is a one-time build-validity fact" | FRAM capacity check is not surfaced at runtime. | area: HW | -

## tests_hardware/flash/test_memory_stress.py
- SETTLED | tests_hardware/flash/test_memory_stress.py:22-28 | "That worst case fell to 2,048 B once both caps were bound ... Not re-derived on purpose: these are a regression tripwire with margin" | `WORST_CASE_ALLOCATION = 16_384` deliberately kept above the current 2048 B worst case (MEASUREMENTS M2.5). | area: HW | related: MEM.T06
- PLATFORM | tests_hardware/flash/test_memory_stress.py:32-34 | "real 264KB SRAM minus the firmware's own static footprint" | Heap figure is silicon- and image-specific; measured inside a device-script build (run_isolated), not the production boot. | area: HW | related: HW.T16
- ASSUME | tests_hardware/flash/test_memory_stress.py:49-57 | "the probe's own pinning artefact looks exactly like this (MEASUREMENTS M2.2), and it always understates"; "a power-of-two fraction of 192 KB is the known artefact" | ±2-block tolerance between probe and map rests on a recorded artefact. | area: HW | -
- SETTLED | tests_hardware/flash/test_memory_stress.py:58-60 | "What the owner asked these tests to express (2026-09-19): long-lived objects must not colonise the top of the heap" | Owner-set placement requirement. | area: MEM | related: MEM.T02
- ASSUME | tests_hardware/flash/test_memory_stress.py:64-66 | "Zero, not a budget - 17 twin runs across 41-58% fill, perturbed, never placed one (MEASUREMENTS M2.1)" | Silicon threshold justified by twin runs. | area: HW | related: HW.T16
- SUPPRESS | tests_hardware/flash/test_memory_stress.py:86-90 | "pytest.skip(\"passive soak, one of three named duration tiers ...\")" | `long_soak` in-test skip. | area: HW | covered-by: HW.T13
- LIMIT | tests_hardware/flash/test_memory_stress.py:86-105 | "test_single_core_timing_headroom_holds_under_normal_full_task_load"; "use the two genuinely one-time-per-setup() ConfigManager/FRAM messages instead" | "Timing headroom" is asserted only as no reboot/traceback markers (DebugLevel-dependent strings); no timing is measured. | area: HW | covered-by: HW.S14

## tests_hardware/flash/test_reboot_persistence.py
- DRIFT | tests_hardware/flash/test_reboot_persistence.py:1-3 | "mpremote's DTR-based reset, the closest real equivalent to a power-cycle without pulling power" | hard_reset described as DTR. | area: HW | covered-by: HW.S17
- DRIFT | tests_hardware/flash/test_reboot_persistence.py:25 | "Item 13 - config.json (a real ConfigManager-backed file) survives a genuine reboot" | The refactor persists `config_<NAME>.cfg`, not config.json. (low) | area: HW | related: HW.S21
- SUPPRESS | tests_hardware/flash/test_reboot_persistence.py:29, 50 | "@pytest.mark.persistence_write" | Owned flash writes: reboot_persist_write config; DebugLevel raise + restore (plus 2 hard resets). | area: HW | covered-by: HW.T01
- LIMIT | tests_hardware/flash/test_reboot_persistence.py:44-47 | "This bench only flashes the refactored `src/` build ..., never the legacy `modules/_boot.py` mechanism of BACKLOG open question 1" | The legacy `import sensortask.py` boot path is never exercised on silicon (consistent with CLAUDE.md). | area: HW | -
- DRIFT | tests_hardware/flash/test_reboot_persistence.py:52-54, 68, 73, 77, 79 | "This bench's board is left at production-quiet DebugLevel=0 between sessions" | Stale DebugLevel comments. | area: HW | covered-by: HW.S17
- INVAR | tests_hardware/flash/test_reboot_persistence.py:66 | "assert \"CFGMGR_\" in joined or \"FRAM\" in joined" | Loose boot oracle. | area: HW | covered-by: HW.S15
- ASSUME | tests_hardware/flash/test_reboot_persistence.py:73-74 | "write_config() only persists to disk, not the live debug-level registry - one more real hard_reset() makes the restored 0 genuinely live" | Pins config-vs-live semantics for DebugLevel. | area: HW | -
- RISK | tests_hardware/flash/test_reboot_persistence.py:77 | "failed to restore DebugLevel to 0 after the boot check - board may be left non-default" | Board-state hazard on restore failure. (low) | area: HW | related: HW.T03

## tests_hardware/flash/test_sensor_accuracy.py
- ASSUME | tests_hardware/flash/test_sensor_accuracy.py:22-23, 38-39, 47 | "~60s real runtime (45s post-reset settle + up to 15s final poll ...)"; "45s documented algorithm blackout" | Timeout bases; each script runs well past run_isolated's 8 s WDT, so must feed it. (low) | area: HW | related: HW.S09
- SUPPRESS | tests_hardware/flash/test_sensor_accuracy.py:54-57, 67-70 | "pytest.skip(\"needs the NeoPixel-aimed-at-the-ISL29125 rig physically set up ...\")" | `neopixel_sweep` in-test skips; the gated mechanism-envelope script also makes flash writes. | area: HW | covered-by: HW.S05
- ASSUME | tests_hardware/flash/test_sensor_accuracy.py:58-60, 71-73 | "22 holds x SETTLE_S=4.5s is ~99s of guaranteed settle alone"; "sums to ~8.5 minutes of real segment time" | Durations mirror constants inside the device scripts. (low) | area: HW | -
- LIMIT | tests_hardware/flash/test_sensor_accuracy.py:80-89 | "run_probe_against_twin(), which needs that port built" | A hardware test that also needs the host Unix port; a missing build raises FileNotFoundError (error, not skip). (low) | area: HW | -

## tests_hardware/flash/test_task_supervisor.py
- ASSUME | tests_hardware/flash/test_task_supervisor.py:1-3 | "the recovery rung CLAUDE.md's own memory-safety-discipline rule leans on between a caught local degrade and the hardware watchdog" | The supervisor-restart rung is proved on silicon only by this isolated script (15 s timeout). | area: HW | related: XCUT.T02

## tests_hardware/flash/test_toolchain_flash_boot.py
- RISK | tests_hardware/flash/test_toolchain_flash_boot.py:19-22 | "Cheap, run first: every other test in this tier assumes basic mpremote connectivity already works" | Five `is_reachable()` calls, each stopping main.py; order-dependent baseline. (low) | area: HW | related: HW.T06
- RISK | tests_hardware/flash/test_toolchain_flash_boot.py:30-42 | "fresh git fetch, full picotool rebuild, full mpy-cross/Unix-port/firmware pass), which takes ~481s wall clock on this bench's Pi4" | Unmarked, runs in every flash pass: host SSD wear and third-party network dependency inside a hardware run. | area: HW | covered-by: HW.S01
- DRIFT | tests_hardware/flash/test_toolchain_flash_boot.py:14, 25, 46-47 | "Item 23"; "Item 19"; "Item 20 ... Part 2 item 8" | Dangling named citations. | area: HW | covered-by: DOC.S05
- SUPPRESS | tests_hardware/flash/test_toolchain_flash_boot.py:52-55 | "pytest.skip(\"this IS a real flash cycle - pass --allow-flash-cycle to deliberately run it\")" | `flash_cycle` in-test skip. | area: HW | covered-by: HW.T13
- SETTLED | tests_hardware/flash/test_toolchain_flash_boot.py:57-59 | "dev, never wozi - wozi is never physically flashed (CLAUDE.md's hard rule), and its hardcoded pins don't match this bench's real wiring" | Restated hard rule. | area: HW | -
- WORKAROUND | tests_hardware/flash/test_toolchain_flash_boot.py:72-75 | "picotool has no internal retry for USB BOOTSEL re-enumeration (calling it immediately after enter_bootloader() can race it, failing with exit 249)" | 5× retry with 2 s sleeps; removal trigger: none stated. | area: HW | -
- ASSUME | tests_hardware/flash/test_toolchain_flash_boot.py:78 | "[\"sudo\", \"picotool\", \"load\", \"-x\", \"-v\", str(uf2_path)]" | Passwordless sudo for picotool. | area: HW | covered-by: HW.S19

## tests_hardware/flash/test_uart_crossover.py
- SUPPRESS | tests_hardware/flash/test_uart_crossover.py:19-34 | "The guard below is not an expected skip - it only names the cause if some future build genuinely lacks the module" | A firmware missing asy_uart_comm becomes a skip; broad `except Exception` re-raised otherwise. | area: HW | related: HW.T13
- LIMIT | tests_hardware/flash/test_uart_crossover.py:44-46 | "One Python instance as initiator and one as responder interoperating perfectly is a required, tested property" | Jumper tests prove Python↔Python only; the C peer (out of scope) is never on the other end here. | area: UART | related: UART.T07
- SETTLED | tests_hardware/flash/test_uart_crossover.py:52-53 | "the one it deliberately cannot - which must therefore be diagnosed rather than absorbed" | Parameter mismatch is diagnosed, never negotiated (owner decision in CLAUDE.md). | area: UART | -
- PLATFORM | tests_hardware/flash/test_uart_crossover.py:59-61 | "POLLIN fires on the first byte, so asking the peripheral for a whole frame blocks the event loop for its remaining wire time" | F.5.8 platform fact, asserted on silicon. | area: UART | related: UART.T10
- SETTLED | tests_hardware/flash/test_uart_crossover.py:67-68 | "Counted, never timed: a poll-round count is a property of the code, while throughput on this board moves with heap state (Part E.7)" | Test design choice. (low) | area: HW | -

## tests_hardware/flash/test_watchdog_starvation.py
- PLATFORM | tests_hardware/flash/test_watchdog_starvation.py:1-3 | "WDT(timeout=...) always re-arms fresh, so the short device-script timeout governs" | Relies on rp2 WDT re-init with a shorter timeout taking effect after run_isolated's 8000 ms arm. | area: PLAT | related: HW.T06
- ASSUME | tests_hardware/flash/test_watchdog_starvation.py:20-22 | "its 10s grace window put this measurement at a reproducible ~13.2s against the 10.0s bound" | Historical measurement behind `allow_recovery=False`. (low) | area: HW | -
- LIMIT | tests_hardware/flash/test_watchdog_starvation.py:29-36, 38-41 | "assert elapsed < 10.0"; "Checked via is_device_present()/is_reachable() rather than tail_log() content" | Reset proved by banner + USB drop + timing; `machine.reset_cause()` is never read. | area: HW | covered-by: HW.S15
- MIRROR | tests_hardware/flash/test_watchdog_starvation.py:13 | "_ARMED_BANNER = \"WDT armed, starving now\"  # printed by device_scripts/watchdog_starvation_reset.py" | String coupled to the device script. (low) | area: HW | -

## tests_hardware/manual/__main__.py
- INVAR | tests_hardware/manual/__main__.py:1-3 | "run this file, never runner.py directly. Running runner.py directly creates a second `runner` module instance with its own empty `_REGISTRY`, silently no-op'ing every registered test" | Entry-point discipline; mitigated only by runner.py having no `__main__` block (runner.py:113-114). | area: HW | related: HW.T15

## tests_hardware/manual/runner.py
- SETTLED | tests_hardware/manual/runner.py:1-3 | "kept structurally separate from the automated flash/bench runner so an unattended pass never stalls on a human" | Manual tier separation. (low) | area: HW | -
- LIMIT | tests_hardware/manual/runner.py:27-28, 94-98 | "input(f\"    {prompt}... \")" then "PASS (human-confirmed)" | A test that uses only `confirm()` cannot record a FAIL: every manual_persistence and manual_sensor_accuracy test, manual_toolchain's human steps and the captive-portal test print PASS whenever the operator presses Enter; the only way out is Ctrl-C aborting the whole run (manual_sensor_accuracy.py:31). | area: HW | related: HW.T15
- SUPPRESS | tests_hardware/manual/runner.py:72-76 | "import manual_bus_electrical  # noqa: F401" | Five F401 suppressions for registration-by-import. (low) | area: HW | -
- DRIFT | tests_hardware/manual/runner.py:53 | "tier: str  # \"[USB]\" or \"[USB+WiFi]\"" | Registered tiers are "[USB][MANUAL]"/"[USB+WiFi][MANUAL]". (low) | area: HW | -

## tests_hardware/manual/manual_bus_electrical.py
- ASSUME | tests_hardware/manual/manual_bus_electrical.py:11, 29 | "confirm the two-tier recovery (task respawn re-probe + reset/soft-reset) actually works"; "assert \"SCD30\" in joined or \"CO2\" in joined" | Recovery oracle is any log line naming SCD30/CO2 within 30 s — DebugLevel-dependent and does not show a fresh successful read. | area: HW | related: HW.T15
- PLATFORM | tests_hardware/manual/manual_bus_electrical.py:34, 40, 43 | "within the 8388ms cap"; "digital twin CI Run 10 only proves this in simulation" | WDT cap fact; wedged-bus backstop proven on silicon only here. | area: HW | related: PLAT.T03
- DRIFT | tests_hardware/manual/manual_bus_electrical.py:46 | "rebooted = \"CFGMGR_\" in joined or \"FRAM SPI FRAM Driver Setup complete\" in joined" | Uses the bare "CFGMGR_" reboot marker the automated tier calls false-positive-prone (bench/test_memory_stress_bench.py:91-93, flash/test_memory_stress.py:97-98). | area: HW | related: HW.S15
- LIMIT | tests_hardware/manual/manual_bus_electrical.py:54, 60 | "WS2812 timing values are NOT sourced from a datasheet in this repo's datasheets/ folder (no WS2812/Neopixel datasheet present) - flagged per CLAUDE.md" | Missing datasheet; only a human visual check. | area: HW | -
- ASSUME | tests_hardware/manual/manual_bus_electrical.py:59, 61 | "via the real /notification lightCmdLED endpoint" | Instruction assumes the dev LED route is live on today's firmware. (low) | area: HW | related: HW.T15

## tests_hardware/manual/manual_persistence.py
- DRIFT | tests_hardware/manual/manual_persistence.py:1-3, 14, 18-19 | "real MB85RS64V"; "PUT /notification WarnCO2={marker}" with marker "424242" | Wrong chip name, out-of-range marker, and the value lives in flash config, not FRAM. | area: HW | covered-by: HW.S04
- RISK | tests_hardware/manual/manual_persistence.py:32-47 | "PUT /sensors {\"SCD30\": {\"MeasInt\": 7}}" | SCD30 NVM write with no restore; later SCD30 tests assume ~2 s. | area: HW | covered-by: HW.S03
- PLATFORM | tests_hardware/manual/manual_persistence.py:14, 34 | "data retention >=10 years at +85 degC"; "the sensor's own onboard NVM (measurement interval, ambient pressure, altitude, temp offset, self-cal)" | Datasheet claims (FRAM retention; SCD30 NVM-held settings). | area: HW | related: SENS.T01
- DRIFT | tests_hardware/manual/manual_persistence.py:52, 56-59 | "an active config.json/FRAM write"; "cut power to the board as close to immediately afterward as you physically can" | config.json naming, and since WP5 the flash write is deferred past the response. | area: HW | covered-by: HW.S21
- LIMIT | tests_hardware/manual/manual_persistence.py:12-71 | "Trigger a real SCD30 NVM write now" | Manual tier sits outside the `persistence_write` wear gate: every run spends flash and SCD30 NVM writes by instruction. | area: HW | related: HW.T01

## tests_hardware/manual/manual_sensor_accuracy.py
- PLATFORM | tests_hardware/manual/manual_sensor_accuracy.py:11-15 | "BMP388/BMP384 typical accuracy, read from datasheets/bmp3xx/bst-bmp388-ds001.pdf" | Tolerances taken from the BMP388 sheet only, although the heading names both parts. (low) | area: HW | -
- DRIFT | tests_hardware/manual/manual_sensor_accuracy.py:24, 27, 30 | "note the Press/Temp fields"; "Enter the reference pressure in Pa" | Driver publishes `Pres` in hPa (with PressOffset). | area: HW | covered-by: HW.S22
- LIMIT | tests_hardware/manual/manual_sensor_accuracy.py:20 | "The digital twin's own README explicitly flags its calibration block as 'not sourced from a real chip'" | Twin fidelity gap: BMP compensation only validated by this manual check. | area: TWIN | related: TWIN.T01
- PLATFORM | tests_hardware/manual/manual_sensor_accuracy.py:34-38 | "Table 1 (not assumed from memory): VOC Index range 1-500, response time <10s (63%) to <30s (90%)" | SGP40 datasheet figures. (low) | area: HW | -
- DRIFT | tests_hardware/manual/manual_sensor_accuracy.py:47 | "note the SGP40 VocIndex field" | The REST field is `VOC` (bench/test_rest_endpoints_over_sta.py:74). | area: HW | related: HW.T15
- ASSUME | tests_hardware/manual/manual_sensor_accuracy.py:56-58 | "The ISL29125 datasheet states no lux accuracy figure" | Datasheet claim behind relative-only assertions. (low) | area: HW | -
- ASSUME | tests_hardware/manual/manual_sensor_accuracy.py:76, 79 | "RangeAct changes to 375"; "the on-board WS2812 (GP18 on the dev bench)" | Hardcoded range value and pin vs devices/dev.toml. (low) | area: HW | related: HW.T08

## tests_hardware/manual/manual_toolchain.py
- SETTLED | tests_hardware/manual/manual_toolchain.py:19-20 | "dev, never wozi - wozi is never physically flashed (CLAUDE.md's hard rule)" | Restated rule. (low) | area: HW | -
- ASSUME | tests_hardware/manual/manual_toolchain.py:42 | "[\"sudo\", \"picotool\", \"load\", \"-x\", \"-v\", str(uf2_path)]" | Passwordless sudo on the host. (low) | area: HW | covered-by: HW.S19

## tests_hardware/manual/manual_wifi.py
- MIRROR | tests_hardware/manual/manual_wifi.py:19, 30 | "password: 12345678" | Committed hotspot credential copy #4 (instruction text). | area: HW | covered-by: HW.S24
- RISK | tests_hardware/manual/manual_wifi.py:16 | "e.g. after PUT /networking {\"SSID\": \"\"}" | Instructs a persisting SSID clear with no restore step. (low) | area: HW | related: HW.T15
- ASSUME | tests_hardware/manual/manual_wifi.py:32 | "http://<gateway IP, usually 192.168.4.1>/" | Assumed CYW43 AP gateway address. (low) | area: HW | -
- OPENQ | tests_hardware/manual/manual_wifi.py:1-3, 38-48 | "genuinely unknown until tried"; "this test always reports PASS since either outcome is valid data" | Captive-portal auto-detection against the DNS-only spoof is an open question; recorded, never failed. | area: NET | -

## tests_hardware/device_scripts/allocation_need_per_source.py
- RISK | tests_hardware/device_scripts/allocation_need_per_source.py:10, 112 | "await sensortask_dev.build_system(web_host=\"127.0.0.1\", web_port=8080)" | Builds the full production object graph in isolation, including its own FRAM manager/loggers over the real chip (production's first chunks) and ConfigManager setup. | area: HW | covered-by: HW.T17
- PLATFORM | tests_hardware/device_scripts/allocation_need_per_source.py:23-25 | "mpremote's raw-REPL soft reset keeps whatever threshold was in force - the boot entry's 32768, or -1 if the attach interrupted main.py first (MEASUREMENTS M3.8)" | GC threshold survives soft reset; script pins -1 explicitly. | area: PLAT | -
- PLATFORM | tests_hardware/device_scripts/allocation_need_per_source.py:26-32 | "GC block: 16 B on the RP2040, 32 B on the 64-bit twin"; "The real WDT.feed() is C and allocates nothing ... the twin's fake allocates" | Block size and feed-allocation facts the instrument depends on. | area: PLAT | -
- ASSUME | tests_hardware/device_scripts/allocation_need_per_source.py:43-45 | "A 1-block allocation advances the allocator's scan hint, so they land in address order" | Sieve construction relies on py/gc.c allocator behaviour. | area: HW | -
- SUPPRESS | tests_hardware/device_scripts/allocation_need_per_source.py:48, 56-57, 60, 65, 119 | "except MemoryError: pass"; "gc.collect()" | Deliberate MemoryError fill and gc.collect() calls in a measurement instrument (outside src/'s confined sites). | area: HW | related: MEM.T05
- LIMIT | tests_hardware/device_scripts/allocation_need_per_source.py:98-99, 126-128 | "everything but the socket write and microdot's own request parsing"; "a probe that degrades internally (a caught MemoryError, logged) still returns normally, and only the host can see that in the log" | Measured need excludes socket write and request parsing; relies on private `ws._status_sources` etc. | area: HW | related: MEM.T03
- SUPPRESS | tests_hardware/device_scripts/allocation_need_per_source.py:152-153 | "except Exception as e:  # a failure here is a result, reported rather than raised into the harness" | Broad catch → RESULT: FAIL. (low) | area: HW | -

## tests_hardware/device_scripts/bmp3xx_plausibility_read.py
- INVAR | tests_hardware/device_scripts/bmp3xx_plausibility_read.py:2-3, 20-23 | "Primes reader.cfgmgr directly (no real flash I/O)" | Pokes private `cfgmgr.valid`/`_cache` to avoid a flash write; coupled to ConfigManager internals. | area: HW | related: HW.T01
- DRIFT | tests_hardware/device_scripts/bmp3xx_plausibility_read.py:17 (also scd30_plausibility_read.py:19, sgp40_voc_algorithm_quality.py:45, sgp40_fram_backup_restore.py:53, isl29125_plausibility_read.py:22, bus_concurrency_same_device_scd30.py:25) | "matches src/system_service.py's own production value" | Production `WDT(timeout=8000)` is emitted by buildgen/codegen.py:381, not system_service.py. (low) | area: HW | related: XCUT.S13
- PLATFORM | tests_hardware/device_scripts/bmp3xx_plausibility_read.py:29-30 | "~15s worst case exceeds the 8.388s hardware WDT ceiling; soft-reset doesn't reset that timer" | WDT persists across soft reset; scripts must feed. | area: PLAT | related: HW.T06
- ASSUME | tests_hardware/device_scripts/bmp3xx_plausibility_read.py:18 | "asy_i2c_driver.I2C(0, 13, 12, frequency=50000)" | Hardcoded dev pins/frequency (one of ~20 scripts). | area: HW | covered-by: HW.S18
- SUPPRESS | tests_hardware/device_scripts/bmp3xx_plausibility_read.py:42-43 | "except (asyncio.CancelledError, Exception): pass" | Task-teardown swallow (same pattern in many scripts). (low) | area: HW | -

## tests_hardware/device_scripts/bmp3xx_same_device_rw_concurrency.py
- PLATFORM | tests_hardware/device_scripts/bmp3xx_same_device_rw_concurrency.py:2-3 | "BMP3xx's OSR/CONFIG registers are volatile (no NVM), so unlike SCD30 this writes freely" | Datasheet fact justifying unmarked writes. | area: HW | -
- MIRROR | tests_hardware/device_scripts/bmp3xx_same_device_rw_concurrency.py:14 | "_OSR_SETTINGS = (1, 2, 4, 8, 16, 32)" | Driver constant copied. (low) | area: HW | -
- SUPPRESS | tests_hardware/device_scripts/bmp3xx_same_device_rw_concurrency.py:62-68 | "Restore the datasheet/production default (x1 ...)" + "except Exception: pass" | Restores the default, not the board's configured value; failure swallowed. (low) | area: HW | -

## tests_hardware/device_scripts/bus_concurrency_cross_device_scd30_sgp40.py
- INVAR | tests_hardware/device_scripts/bus_concurrency_cross_device_scd30_sgp40.py:23-25 | "this group's one NVM-persisted write happens once per session in flash/conftest.py's scd30_continuous_measurement_triggered fixture" | Script correctness depends on a host fixture having run first. | area: HW | related: HW.T01
- ASSUME | tests_hardware/device_scripts/bus_concurrency_cross_device_scd30_sgp40.py:19, 26 | "I2C(1, 15, 14, frequency=50000, timeout=200000)"; "await sgp.setup()  # includes one initialize() call already" | Hardcoded pins; SGP40 setup (whose `_reset()` is the general-call path per C.8) runs next to SCD30. | area: HW | covered-by: HW.S18
- ASSUME | tests_hardware/device_scripts/bus_concurrency_cross_device_scd30_sgp40.py:89-93 | "less interleaving than expected, worth a closer look even though not zero" | Heuristic floor (≥1 interleaved read per SGP40 window) fails the run. (low) | area: HW | related: HW.T05

## tests_hardware/device_scripts/bus_concurrency_isl29125_write_vs_siblings.py
- ASSUME | tests_hardware/device_scripts/bus_concurrency_isl29125_write_vs_siblings.py:1-3, 15-19 | "Why delays, not yields: SPECIFICATION.md Part C.8"; "_WRITE_DELAYS_MS = (5, 15, 40, 80, 120)" | Host-chosen offsets stand in for the mock tier's systematic sweep; coverage of the relevant phase is not proven. | area: HW | related: HW.T05
- LIMIT | tests_hardware/device_scripts/bus_concurrency_isl29125_write_vs_siblings.py:61-63 | "outside the 16-bit range - a torn word" | Torn-read oracle can only catch impossible values (and CRC/NAK exceptions). | area: HW | related: HW.T05

## tests_hardware/device_scripts/bus_concurrency_same_device_scd30.py
- ASSUME | tests_hardware/device_scripts/bus_concurrency_same_device_scd30.py:18-21, 33-35 | "setup()'s soft reset leaves the NVM-persisted measurement interval running ... scd30_same_device_rw_concurrency.py carries the same constant" | `_SETTLE_S = 12.0` duplicated across two scripts; assumes the NVM MeasInt is ~2 s (manual tier may leave 7). | area: HW | related: HW.S03
- ASSUME | tests_hardware/device_scripts/bus_concurrency_same_device_scd30.py:2-3 | "Both paths are CRC-8 protected, so interleaving corruption would trip a CRC/NAK, not silently succeed" | Oracle rests on CRC detection. (low) | area: HW | -
- MIRROR | tests_hardware/device_scripts/bus_concurrency_same_device_scd30.py:12-14, 71-74 | "2 <= meas_int <= 1800"; "400 <= frc <= 2000" | Schema bounds copied from the driver. (low) | area: HW | -

## tests_hardware/device_scripts/bus_concurrency_scd30_write_vs_siblings.py
- INVAR | tests_hardware/device_scripts/bus_concurrency_scd30_write_vs_siblings.py:1-3, 73-75 | "THE one extra real NVM write this script makes ... this script must never be called more than once per opt-in run" | SCD30 NVM write (`set_temperature_offset(4.0)`), gated host-side by scd30_extra_write; once-per-run by convention. | area: HW | covered-by: HW.T01
- RISK | tests_hardware/device_scripts/bus_concurrency_scd30_write_vs_siblings.py:75 | "await scd.set_temperature_offset(4.0)" | Leaves a non-default temperature offset in SCD30 NVM; no restore. | area: HW | related: HW.T03

## tests_hardware/device_scripts/bus_deinit_is_a_noop_on_real_hardware.py
- PLATFORM | tests_hardware/device_scripts/bus_deinit_is_a_noop_on_real_hardware.py:1-3, 26-27 | "machine.I2C/SPI .deinit() are silent no-ops and each bus id is a static singleton ... never observed on real silicon"; "(1.29 floor - it raises AttributeError on 1.28)" | F.5.1 version-specific facts; re-check on a pin move. | area: PLAT | related: PLAT.T06
- RISK | tests_hardware/device_scripts/bus_deinit_is_a_noop_on_real_hardware.py:44-53 | "fram = AsyFramManager(spi_wrapper, SPI_CS, max_size=0x40000, debug=None)"; "chunk.write(PATTERN)" | Own FRAM manager over the real chip overwrites production's first chunk with a test pattern. | area: HW | covered-by: HW.T17
- ASSUME | tests_hardware/device_scripts/bus_deinit_is_a_noop_on_real_hardware.py:13-14, 45 | "I2C_PORT, I2C_SCL, I2C_SDA = 0, 13, 12  # dev bench wiring"; "max_size=0x40000" | Hardcoded pins; 256 KB size assumes the MB85RS2MTA part. | area: HW | related: HW.T07
- LIMIT | tests_hardware/device_scripts/bus_deinit_is_a_noop_on_real_hardware.py:55 | "raw_spi = spi_wrapper._spi" | Reaches into the wrapper's private attribute. (low) | area: HW | -

## tests_hardware/device_scripts/bus_topology_autodetect_and_hazard_sweep.py
- MIRROR | tests_hardware/device_scripts/bus_topology_autodetect_and_hazard_sweep.py:21-23 | "The on-target copy of the address table ... Adding a driver means adding it here too (Part K.7)" | Hand-kept address table mirrors the host device model. | area: HW | related: HW.T08
- ASSUME | tests_hardware/device_scripts/bus_topology_autodetect_and_hazard_sweep.py:28-30 | "This bench's own real pin assignments (sensortask_dev.py's own construction comments)" | Hardcoded bus pins/timeouts, cited from a generated file's comments. | area: HW | covered-by: HW.S18
- LIMIT | tests_hardware/device_scripts/bus_topology_autodetect_and_hazard_sweep.py:33-44 | "return None  # clean NAK/timeout"; "return None  # ACKed" | Probe returns None for both NAK and ACK, so the address/reserved sweeps can only fail on a non-OSError exception. | area: HW | covered-by: HW.S12
- LIMIT | tests_hardware/device_scripts/bus_topology_autodetect_and_hazard_sweep.py:47-50, 170-172 | "read_measurement() degrades cleanly (cached fields stay None, no exception)"; "if len(known_here) == 1" | Self-hazard runs only for a lone device, and an SCD30 read "passes" with no data. | area: HW | covered-by: HW.S12
- SUPPRESS | tests_hardware/device_scripts/bus_topology_autodetect_and_hazard_sweep.py:104-116, 133-136 | "# noqa: E731"; "except OSError: pass" | Four lambda suppressions; general-call broadcast errors swallowed. (low) | area: HW | -
- RISK | tests_hardware/device_scripts/bus_topology_autodetect_and_hazard_sweep.py:131-137 | "i2c.writeto(GENERAL_CALL_ADDRESS, b\"\\x06\")" | Issues real general-call resets on the bus the SCD30 sits on. (low) | area: HW | related: HW.T03

## tests_hardware/device_scripts/float_boundary_2pow24.py
- PLATFORM | tests_hardware/device_scripts/float_boundary_2pow24.py:1-3 | "RP2040's real firmware is MICROPY_FLOAT_IMPL_FLOAT (24-bit mantissa ...) - the Unix-port test rig uses doubles and can't reproduce this" | Float representation gap between target and test rig. | area: PLAT | related: PLAT.T08
- DRIFT | tests_hardware/device_scripts/float_boundary_2pow24.py:7-8 | "kept only for parity with how isolated-driver scripts are documented to work" | Vestigial `sys.path.insert(0, "/")`, not used by other scripts. (low) | area: HW | -
- ASSUME | tests_hardware/device_scripts/float_boundary_2pow24.py:20-35 | "coerce_numeric() always accepts this by design; the real assertion is whether the stored value silently lost precision" | Pins that precision loss is accepted silently (expects 2**24, round-to-even). | area: HW | related: MEM.T07

## tests_hardware/device_scripts/fram_busy_status_lockout.py
- LIMIT | tests_hardware/device_scripts/fram_busy_status_lockout.py:1-3 | "The overrun is a DMA timing condition Python cannot induce; its consequence is" | Only the consequence of an RX overrun is tested. | area: HW | related: PLAT.T03
- MIRROR | tests_hardware/device_scripts/fram_busy_status_lockout.py:14-17 | "Wire-level values, hardcoded rather than imported: asy_fram_manager.py's own _STATUS_*/_ADDR_* are micropython.const() and compiled away" | Copied wire constants. | area: HW | -
- RISK | tests_hardware/device_scripts/fram_busy_status_lockout.py:39-65 | "AsyFramManager(spi0, 5, max_size=0x40000, debug=None)"; "_force_both_blocks_busy" | Overwrites production's first FRAM chunk and deliberately leaves it BUSY before rewriting. | area: HW | covered-by: HW.T17

## tests_hardware/device_scripts/fram_capacity_after_full_system_build.py
- RISK | tests_hardware/device_scripts/fram_capacity_after_full_system_build.py:30 | "await sensortask_dev.build_system(cfg_path=\"\", web_host=\"127.0.0.1\", web_port=8080)" | Full build_system over the real FRAM re-runs production's deterministic allocation (same chunks). | area: HW | covered-by: HW.T17
- MIRROR | tests_hardware/device_scripts/fram_capacity_after_full_system_build.py:11-17 | "Every name dev's build_system() constructs that could hold a FRAM-backed logger. Probed via getattr()" | Hand-kept attribute-name list; a new FRAM-wired module name is silently skipped (`continue` on None). | area: HW | related: HW.T02
- SETTLED | tests_hardware/device_scripts/fram_capacity_after_full_system_build.py:3 | "mpremote-only by design; tests_hardware/README.md has both reasons" | No runtime surface for FRAM capacity. (low) | area: HW | -

## tests_hardware/device_scripts/fram_cs_hijack_fault_injection_and_recovery.py
- INVAR | tests_hardware/device_scripts/fram_cs_hijack_fault_injection_and_recovery.py:13-16 | "scratch addresses, disjoint from every other device script's own regions" | Raw FRAM addresses 0x9000-0x93FF kept disjoint by convention only; beyond an 8 KB MB85RS64V's range, and not checked against production's allocated chunks. | area: HW | related: HW.T07
- ASSUME | tests_hardware/device_scripts/fram_cs_hijack_fault_injection_and_recovery.py:25-27 | "measure A made that window non-yielding, so the race could no longer land (HEAP_FRAGMENTATION_MEASUREMENTS archive §7D.5)" | Injection moved to the synchronous seam after a measurement-driven src change. (low) | area: HW | -
- SUPPRESS | tests_hardware/device_scripts/fram_cs_hijack_fault_injection_and_recovery.py:49, 57, 60-61 | "# type: ignore[method-assign]" | Four method-assign suppressions in device-script code (checked in the main mypy pass). | area: HW | -
- PLATFORM | tests_hardware/device_scripts/fram_cs_hijack_fault_injection_and_recovery.py:38-39 | "Reading an output pin back gives its driven level on rp2" | rp2 Pin readback fact the injection proof rests on. | area: PLAT | -
- ASSUME | tests_hardware/device_scripts/fram_cs_hijack_fault_injection_and_recovery.py:161-163 | "Not asserted against a specific wrong value (a different unit could float differently on a deselected MISO)" | Read-hijack oracle is "not the seeded data". (low) | area: HW | -

## tests_hardware/device_scripts/fram_error_log_reset_during_boot_window.py
- RISK | tests_hardware/device_scripts/fram_error_log_reset_during_boot_window.py:17-33 | "AsyFramManager(spi0, 5, max_size=0x40000 ...)"; "await store.err_s(\"seeded\", errno=SEEDED_ERRNO)" with SEEDED_ERRNO = 5 | Seeds errno=5 into production's first FRAM chunk — the exact pattern CLAUDE.md records as later read back as SYSTEM's "Task N ended"; this script resets it again before exiting only on the success path. | area: HW | covered-by: HW.T17
- SETTLED | tests_hardware/device_scripts/fram_error_log_reset_during_boot_window.py:28-29 | "Clear at the START, never at the end (tests_hardware/README.md's own rule)" | Stated device-script FRAM rule (contrasts with early-return paths that leave seeded history). | area: HW | related: HW.T02

## tests_hardware/device_scripts/fram_error_log_reset_race_seed_and_race.py
- RISK | tests_hardware/device_scripts/fram_error_log_reset_race_seed_and_race.py:14-15, 28-31, 46-47, 58 | "First chunk allocated off a freshly-constructed manager, so it lands at allocation offset 0"; "SEEDED_ERRNO = 5"; "RACED_ERRNO = 6" | Writes errno 5/6 entries into production's chunk 0 and then resets mid-write; the verify phase never clears them — the board is left with plausible-looking fabricated history (CLAUDE.md's errno=5 incident). | area: HW | covered-by: HW.T17
- ASSUME | tests_hardware/device_scripts/fram_error_log_reset_race_seed_and_race.py:60-64 | "One await asyncio.sleep(0) before acting - next-in-line the instant victim_writer yields, same scheduling-order dependency" | Race landing depends on asyncio scheduling order; no evidence the reset hit mid-write. | area: HW | related: HW.T05
- SUPPRESS | tests_hardware/device_scripts/fram_error_log_reset_race_seed_and_race.py:49 | "# noqa: B905 - MicroPython zip() rejects strict=" | Platform-driven suppression (also in fram_error_log_reset_race_verify.py:41, 57 and fram_error_log_roundtrip.py:63). | area: HW | -

## tests_hardware/device_scripts/fram_error_log_reset_race_verify.py
- SETTLED | tests_hardware/device_scripts/fram_error_log_reset_race_verify.py:17-20 | "Losing the whole history is accepted (owner, 2026-09-11) - SPECIFICATION.md Part C.3.1" | Accepted all-or-nothing loss; partial restore never. | area: STOR | related: STOR.T01
- SETTLED | tests_hardware/device_scripts/fram_error_log_reset_race_verify.py:31-32 | "Deliberately NOT cleared first, against tests_hardware/README.md's clear-at-the-start rule" | Deliberate exception; the chunk is left holding errno 5/6/7 entries afterwards. | area: HW | covered-by: HW.T17
- PLATFORM | tests_hardware/device_scripts/fram_error_log_reset_race_verify.py:58-60 | "MicroPython has no iterable unpacking inside a list display ... a runtime SyntaxError on target and neither ruff nor mypy sees it (caught by the real board, 2026-09-11)" | Target-only syntax gap invisible to host tooling. | area: PLAT | related: PLAT.T07

## tests_hardware/device_scripts/fram_error_log_roundtrip.py
- LIMIT | tests_hardware/device_scripts/fram_error_log_roundtrip.py:2-3, 33-35 | "simulates a fresh boot (a new AsyFramManager)" | Not a real reboot; also names the chip MB85RS2MTA (the flash test says MB85RS64V). | area: HW | related: HW.S17
- RISK | tests_hardware/device_scripts/fram_error_log_roundtrip.py:19-31 | "await pr1.err_s(\"test error for fram_error_log_roundtrip.py\", errno=TEST_ERRNO)" | Leaves an errno=42 entry in production's chunk 0. | area: HW | covered-by: HW.T17

## tests_hardware/device_scripts/fram_manager_roundtrip.py
- RISK | tests_hardware/device_scripts/fram_manager_roundtrip.py:16-27 | "chunk = fram.get_chunk(CHUNK_SIZE, crc=CRC8())"; "chunk.write(PATTERN)" | Overwrites production's first FRAM chunk with a test pattern. | area: HW | covered-by: HW.T17

## tests_hardware/device_scripts/fram_pause_unpause_and_gating.py
- PLATFORM | tests_hardware/device_scripts/fram_pause_unpause_and_gating.py:26-28 | "mpremote's soft reset does NOT disarm an armed rp2 watchdog, so a script running past the ~8s timeout resets the board mid-run, presenting as a bare serial EIO" | Load-bearing WDT fact every long device script depends on. | area: PLAT | related: HW.T06
- LIMIT | tests_hardware/device_scripts/fram_pause_unpause_and_gating.py:64-65 | "override_pause ... (zero callers in src/, so this escape hatch has only ever been exercised against mocks)" | Unused src API exercised only here. (low) | area: STOR | related: STOR.T05
- ASSUME | tests_hardware/device_scripts/fram_pause_unpause_and_gating.py:103-105 | "Whether the re-arm aborts on ENOMEM or finds the slot its own deinit() just freed is an rp2 detail; both are fine" | Invariant asserted either way; which path ran is not recorded. | area: HW | related: PLAT.T03
- SUPPRESS | tests_hardware/device_scripts/fram_pause_unpause_and_gating.py:112-113, 126-129 | "except OSError: pass  # the pool is now exhausted"; "except Exception: pass" | Deliberate alarm-pool exhaustion (64 Timers) and swallowed deinit errors. (low) | area: HW | -
- RISK | tests_hardware/device_scripts/fram_pause_unpause_and_gating.py:171-182 | "AsyFramManager(spi0, 5, max_size=0x40000 ...)"; "SystemService(_ntp_never_synced, fram=fram, debug=None)" | Overwrites production's first chunks (plain + timestamped) with test patterns. | area: HW | covered-by: HW.T17

## tests_hardware/device_scripts/fram_reset_race_during_write_seed_and_race.py
- INVAR | tests_hardware/device_scripts/fram_reset_race_during_write_seed_and_race.py:13-17 | "Scratch addresses, disjoint from every other device script's own regions (CS-hijack uses 0x9000-0x93ff)" | Raw 0xA000-0xA03F region kept disjoint by convention; beyond an 8 KB part. | area: HW | related: HW.T07
- ASSUME | tests_hardware/device_scripts/fram_reset_race_during_write_seed_and_race.py:55-65 | "machine.reset()  # never returns - real RP2040 hardware reset, immediate, CS still asserted" | Reset fires before the payload bytes are sent, so the test proves an unsent-payload command does not commit, not a mid-payload tear. (low) | area: HW | related: HW.T05
- SUPPRESS | tests_hardware/device_scripts/fram_reset_race_during_write_seed_and_race.py:67, 69 | "# type: ignore[method-assign]" | Two more method-assign suppressions. | area: HW | -

## tests_hardware/device_scripts/fram_reset_race_during_write_verify_recovery.py
- DRIFT | tests_hardware/device_scripts/fram_reset_race_during_write_verify_recovery.py:1-3 | "the real hardware reset seed_and_race.py's reset_yanker() triggered mid-write" | The phase-1 script resets from `resetting_write_sync`; `reset_yanker()` lives in fram_error_log_reset_race_seed_and_race.py. (low) | area: HW | -

## tests_hardware/device_scripts/fram_same_device_rw_concurrency.py
- RISK | tests_hardware/device_scripts/fram_same_device_rw_concurrency.py:13-14, 30-31 | "READ_REGION = (0x0000, 32)  # never touched by the writer below"; "WRITE_REGION = (0x8000, 32)  # disjoint scratch region, well within the real 256KB chip's range" | Raw write of a seed pattern at FRAM address 0 — production's first chunk — plus a scratch region that assumes the 256 KB part. | area: HW | covered-by: HW.T17
- PLATFORM | tests_hardware/device_scripts/fram_same_device_rw_concurrency.py:2-3 | "FRAM has no NVM write-wear concern (10^13 ops/byte, datasheets/fram/)" | Endurance figure of the MB85RS2MTA sheet (MB85RS64V is 10^12 per the plan). | area: HW | related: HW.T07
- INVAR | tests_hardware/device_scripts/fram_same_device_rw_concurrency.py:3 | "get_values()/set_values() require the caller to already hold the outer Lockable lock" | Driver caller contract, by convention. | area: STOR | related: STOR.T01

## tests_hardware/device_scripts/fram_write_protect_roundtrip.py
- RISK | tests_hardware/device_scripts/fram_write_protect_roundtrip.py:93-107 | "Always leave the real chip unprotected on exit, regardless of where a failure occurs - a stuck-protected chip would silently break every other FRAM-owning module's writes" | Non-volatile WPEN|BP0|BP1 restored only in `finally`; a WDT reset/killed mpremote leaves production FRAM protected. | area: HW | covered-by: HW.S07
- SETTLED | tests_hardware/device_scripts/fram_write_protect_roundtrip.py:2-3, 36-38 | "Reads being gated too is intended, accepted behavior - SPECIFICATION.md Part A.4's FRAM entry" | Accepted behaviour, asserted identically in mock and twin. | area: STOR | -
- LIMIT | tests_hardware/device_scripts/fram_write_protect_roundtrip.py:48-59 | "Lying to the driver (_wp is only a cached status-register copy)"; "No verdict of its own" | Chip-level refusal tested by desyncing a private cache field. (low) | area: HW | -
- RISK | tests_hardware/device_scripts/fram_write_protect_roundtrip.py:82-99 | "AsyFramManager(spi0, 5, max_size=0x40000 ...)"; "chunk.write(PATTERN_A)" | Also overwrites production's first chunk. | area: HW | covered-by: HW.T17

## tests_hardware/device_scripts/heap_headroom_after_full_system_build.py
- PLATFORM | tests_hardware/device_scripts/heap_headroom_after_full_system_build.py:11-14 | "mpremote's raw-REPL soft reset keeps whatever threshold was in force ... until 2026-09-24, setting none of its own, this script read one or the other by timing (MEASUREMENTS M3.8)" | Earlier readings of this script are threshold-ambiguous. | area: HW | related: HW.T16
- SETTLED | tests_hardware/device_scripts/heap_headroom_after_full_system_build.py:24-35 | "Not re-derived on purpose ... the retired 80,000 B floor was 30% - a third of physical memory, which is what the owner retired it for on 2026-09-19. Nothing here may be raised to fit a reading" | `_MIN_LARGEST_BLOCK = 32768` is a requirement, not a fitted floor. | area: MEM | related: MEM.T06
- ASSUME | tests_hardware/device_scripts/heap_headroom_after_full_system_build.py:36-39 | "Every [HW] reading of a fully built dev graph is 87,760-87,968 B, so this is ~14% over" | `_MAX_USED = 100_000` fitted to measurements of an unnamed image. | area: HW | related: HW.T16
- ASSUME | tests_hardware/device_scripts/heap_headroom_after_full_system_build.py:83-93 | "A probe run can pin its own buffer through a stale root ... always _PROBE_MAX >> k, e.g. 49,152 (MEASUREMENTS M2.2)" | Known probe artefact handled by rereads; a persisting one only prints WARNING and the result still gates. | area: HW | -
- MIRROR | tests_hardware/device_scripts/heap_headroom_after_full_system_build.py:117 | "gc.threshold(32768)  # what buildgen.codegen.generate_boot_entry_source() sets in the real firmware" | Copied production GC threshold. | area: HW | -
- RISK | tests_hardware/device_scripts/heap_headroom_after_full_system_build.py:105 | "await sensortask_dev.build_system(cfg_path=\"\", ...)" | Full build_system over the real FRAM (production allocation). | area: HW | covered-by: HW.T17
- SUPPRESS | tests_hardware/device_scripts/heap_headroom_after_full_system_build.py:46, 59, 64, 67, 77 | "gc.collect()" | Measurement-instrument gc.collect() calls. (low) | area: HW | related: MEM.T05

## tests_hardware/device_scripts/heap_layout_after_full_boot_sequence.py
- LIMIT | tests_hardware/device_scripts/heap_layout_after_full_boot_sequence.py:3, 219-222 | "Report only, no floors"; "No reading for this position exists yet on silicon, so a threshold here would be invented" | Always PASSes; no host wrapper runs it (orphan). | area: HW | covered-by: HW.S16
- LIMIT | tests_hardware/device_scripts/heap_layout_after_full_boot_sequence.py:161-163 | "main()'s own order, minus ntp_force_sync() ... It allocates during the gap between the two lists either way - stated, not measured here" | Boot sequence reproduced without its NTP step. | area: HW | -
- ASSUME | tests_hardware/device_scripts/heap_layout_after_full_boot_sequence.py:25-35 | "the twin says B's gain decays there within ~2 s (MEASUREMENTS M3.9)"; "~41 ms on the RP2040 (MEASUREMENTS archive 7F.7)" | Settle/grace constants from twin and single silicon measurements. | area: HW | related: HW.T16
- PLATFORM | tests_hardware/device_scripts/heap_layout_after_full_boot_sequence.py:44-47 | "mpremote run takes no argv but does share globals with an `exec` earlier in the same raw-REPL session ... Verified on this board, 2026-09-22; assigning sys.argv raises there" | Arm selection relies on raw-REPL global sharing. | area: HW | -
- MIRROR | tests_hardware/device_scripts/heap_layout_after_full_boot_sequence.py:17-18, 55-58, 213 | "Same doubling/halving bounds as heap_headroom_after_full_system_build.py, deliberately"; "Ported from tests/_boot_contiguity_probe.py"; "gc.threshold(32768)" | Probe duplicated across two scripts and a unit-tier probe. | area: HW | related: TEST.T08
- SUPPRESS | tests_hardware/device_scripts/heap_layout_after_full_boot_sequence.py:138-139, 177-184 | "sensortask_dev.gc = batch_gc  # type: ignore[assignment]"; "sysfunct._start_task = _counting_start_task" | Module/private-method patching of generated and src code. (low) | area: HW | -

## tests_hardware/device_scripts/heap_under_connection_ceiling.py
- RISK | tests_hardware/device_scripts/heap_under_connection_ceiling.py:40 | "create_task(sensortask_dev.main())" | Runs the full production main (WiFi, FRAM, config) from a device script for 90 s + 20 s. | area: HW | covered-by: HW.T17
- INVAR | tests_hardware/device_scripts/heap_under_connection_ceiling.py:41-43 | "a request driven from this process would share the heap under measurement, which is the whole thing Part E.9 forbids" | Measurement discipline: load is host-driven only. | area: HW | -
- ASSUME | tests_hardware/device_scripts/heap_under_connection_ceiling.py:12-15, 44 | "The threshold is the boot entry's own ... what MEASUREMENTS archive 7R.2 was taken at"; "await asyncio.sleep(20)" | Fixed 20 s boot wait before READY; threshold copied from the boot entry. (low) | area: HW | -

## tests_hardware/device_scripts/isl29125_cross_device_concurrency.py
- ASSUME | tests_hardware/device_scripts/isl29125_cross_device_concurrency.py:32, 50 | "or continuous measurement was never triggered"; "no set_ambient_pressure() - that is the one NVM write this group makes, via the session fixture" | Depends on the host session fixture's SCD30 NVM write having run. | area: HW | related: HW.T01
- ASSUME | tests_hardware/device_scripts/isl29125_cross_device_concurrency.py:33-38, 105-110 | "zero ISL29125 reads completed inside any SGP40 initialize() window" | Interleaving floor is ≥1 in total (weaker than the SCD30/SGP40 script's per-window heuristic). (low) | area: HW | related: HW.T05

## tests_hardware/device_scripts/isl29125_plausibility_read.py
- RISK | tests_hardware/device_scripts/isl29125_plausibility_read.py:23-28, 84-85 | "depending on ambient made this result depend on test ORDER - it passed with the pixel latched white, then failed once a preceding test parked it dark" | Known order dependence between device scripts via the latched NeoPixel; the script now self-lights and parks it dark afterwards (the early no-reading return skips the park). | area: HW | -
- ASSUME | tests_hardware/device_scripts/isl29125_plausibility_read.py:14-17 | "_SELF_LIGHT_LEVEL = 20  # ~750 lx at this geometry"; "ROOM_LIGHT_MIN_LUX = 5.0" | Bench-geometry-dependent calibration of the self-lit scene. | area: HW | -
- PLATFORM | tests_hardware/device_scripts/isl29125_plausibility_read.py:1-2, 14-15 | "FN8424 p1's own 0.0057-10000 lx span ... McCamy's 2000-12500 K" | Datasheet/literature bounds. (low) | area: HW | -
- ASSUME | tests_hardware/device_scripts/isl29125_plausibility_read.py:26, 30-31 | "NeoPixel(Pin(18, Pin.OUT), 1)"; "ISL29125_Reader(i2c1, 6, ...)" | Hardcoded GP18/GP6/i2c1 pins vs dev.toml. | area: HW | covered-by: HW.S18
- INVAR | tests_hardware/device_scripts/isl29125_plausibility_read.py:32-37 | "Seeded from the driver's own schema, never a hand-copied list - a key added there (GainRatio, f05f82d) otherwise leaves this one short of _N_FLOAT_CFG" | Private cfgmgr priming (no flash write) must track the schema; same in isl29125_real_irq_edge.py:89-95. | area: HW | -

## tests_hardware/device_scripts/isl29125_real_irq_edge.py
- ASSUME | tests_hardware/device_scripts/isl29125_real_irq_edge.py:15-20 | "~3030ms worst case, so the old 3.0s no longer clears it. 6.0s is still 5x under the periodic fallback"; "tINT = 101ms typ (p3)" | Deadline derived from datasheet typicals. | area: HW | -
- DRIFT | tests_hardware/device_scripts/isl29125_real_irq_edge.py:86-87 | "A 30s periodic interval means a reading inside 3s can only have come from the interrupt" | Deadline is 6.0 s (:18). (low) | area: HW | -
- OPENQ | tests_hardware/device_scripts/isl29125_real_irq_edge.py:2-3, 24-27, 44-47 | "the two questions no document answers - whether a CONFIG1 write restarts the conversion, and whether PRST counts cycles or integrations" | CONFIG1-restart result is reported only ("inconclusive" allowed); PRST unit is asserted. | area: SENS | -
- INVAR | tests_hardware/device_scripts/isl29125_real_irq_edge.py:117-121 | "persist_for_interval() compares PRST x a whole RGB CYCLE against the sample interval. If the part answered \"channel integrations\" ... nothing else would notice" | Driver derivation depends on a silicon fact only this script checks. | area: SENS | related: SENS.T01
- RISK | tests_hardware/device_scripts/isl29125_real_irq_edge.py:70-72 | "`mpremote run` leaves it wherever the WiFi signalling service last wrote it - often full white, ~2000 lx here" | Interrupted main.py leaves the NeoPixel state behind for the next script. (low) | area: HW | -

## tests_hardware/device_scripts/isl29125_same_device_rw_concurrency.py
- INVAR | tests_hardware/device_scripts/isl29125_same_device_rw_concurrency.py:20-22 | "Constructs the PROTOCOL layer directly, never ISL29125_Reader: Part C.8's standing rule for a concurrency script exercising persisted config, so nothing here touches the RP2040's flash" | Wear rule for device scripts, by convention. | area: HW | related: HW.T01
- PLATFORM | tests_hardware/device_scripts/isl29125_same_device_rw_concurrency.py:14-15, 57-58 | "_STATUS_RESERVED_MASK = 0xC8  # B7:B6 and B3 read zero on a working part (p12, Table 15)"; "a 2-byte burst at 0x02, which deliberately does NOT restart the conversion" | Datasheet facts behind the oracle. | area: HW | -
- LIMIT | tests_hardware/device_scripts/isl29125_same_device_rw_concurrency.py:71 | "await asyncio.gather(reader(), writer())" | No `wait_for` bound, unlike sibling scripts (host timeout still applies). (low) | area: HW | -

## tests_hardware/device_scripts/isl29125_lighting_scenarios.py
- ASSUME | tests_hardware/device_scripts/isl29125_lighting_scenarios.py:27-31, 233-235 | "Measured on the covered rig: rising, the low range holds to level 6 (~197 lx) and the high takes over at level 8 (~300 lx)" | Scenario levels depend on one measured hysteresis band of one rig geometry. | area: HW | related: HW.T16
- ASSUME | tests_hardware/device_scripts/isl29125_lighting_scenarios.py:32-40 | "_BASELINE_TOL = 0.35"; "_MAX_SAMPLE_GAP_S = 8.0"; "_SWITCH_HOLD_S = 8.0  # the derived 2 cycles + settle + a 1s sample interval, with margin" | Tolerances and timing thresholds, basis partly stated. (low) | area: HW | -
- SETTLED | tests_hardware/device_scripts/isl29125_lighting_scenarios.py:23-25 | "The NeoPixel is driven RAW on purpose ... Nothing else contends for the pixel in an isolated run, so no arbitration is bypassed" | Deliberate bypass of NeopixelDriver. (low) | area: HW | -
- LIMIT | tests_hardware/device_scripts/isl29125_lighting_scenarios.py:201-205 | "that run lives in driver state (_periodic_only_switches) which reset_error_counter() does not touch - so it can span scenarios" | W13 dead-interrupt warning state outlives an error-counter reset in src. | area: SENS | related: SENS.T03
- ASSUME | tests_hardware/device_scripts/isl29125_lighting_scenarios.py:239-241 | "an inherited range is how the first version of this file passed while proving nothing" | Engagement floors (min_switches, both ranges, ≥5 total switches) added after a vacuous pass. | area: HW | related: HW.T05
- INVAR | tests_hardware/device_scripts/isl29125_lighting_scenarios.py:309-315 | "reader.cfgmgr._cache[\"AutoRangeDwell\"] = 0.0" | Primed config (no flash write), but scenario behaviour differs from the shipped AutoRangeDwell default. (low) | area: HW | -

## tests_hardware/device_scripts/isl29125_mechanism_envelope.py
- RISK | tests_hardware/device_scripts/isl29125_mechanism_envelope.py:100-105, 150-196 | "this script calls _set_dict_cfg, whose persist leg is a real write_config() ... Scratch filename"; nine `_set_dict_cfg` calls | ~9 real RP2040 flash writes under `neopixel_sweep` only (no persistence_write gate), to a scratch `config_HWTEST_ISL29125.cfg` left on the board. | area: HW | covered-by: HW.S05
- ASSUME | tests_hardware/device_scripts/isl29125_mechanism_envelope.py:22-31 | "OVERLAP_LEVEL = 4  # ~150 lx on this rig"; "MAX_RANGE_STEP = 0.25 ... the applied ratio's band is 20-34 around a nominal 26.67"; "The accuracy question itself lives in Part M.1.6" | Rig-dependent levels and a relative gain bound derived from the driver's band. | area: HW | related: HW.T16
- ASSUME | tests_hardware/device_scripts/isl29125_mechanism_envelope.py:170-172, 215-217 | "The retired ramp sweep tried it on a moving ramp, where the light's own ~22%/s rise swamps the step"; "this rig really does exceed 10000 lx at ~20mm"; "one leg cannot reach it: a guard, not a proof" | W13 check on one leg is a guard only; rig geometry assumption. | area: HW | related: HW.T05
- INVAR | tests_hardware/device_scripts/isl29125_mechanism_envelope.py:190-196 | "The applied ratio is config now and only a user PUT changes it"; "reader._gain_ratio == 10000 / 375" | Calibration must not move the applied ratio; checked via private fields. | area: SENS | -

## tests_hardware/device_scripts/isl29125_mock_conformance_probe.py
- MIRROR | tests_hardware/device_scripts/isl29125_mock_conformance_probe.py:1-3 | "run IDENTICALLY against the real chip and the twin's fake - it talks only raw machine.I2C, the one layer both implement" | Real-vs-twin conformance oracle; diffed by isl29125_conformance.py (PHYSICAL_KEYS excluded). | area: HW | related: TWIN.T01
- SUPPRESS | tests_hardware/device_scripts/isl29125_mock_conformance_probe.py:11-14 | "except (AttributeError, ValueError, OSError): _WDT = None  # the twin's machine.py has no real watchdog to feed" | Twin fidelity gap (no WDT) papered by a swallow. (low) | area: HW | related: TWIN.T02
- PLATFORM | tests_hardware/device_scripts/isl29125_mock_conformance_probe.py:80-81, 98, 130-132 | "p12: BOUTF is cleared by an I2C write, despite Table 15's \"RO\""; "p6's burst text: ... rolls over and goes back to the first Register Address" | Datasheet-ambiguity points the fake must match. | area: SENS | related: SENS.T01
- ASSUME | tests_hardware/device_scripts/isl29125_mock_conformance_probe.py:54-56 | "the twin's Timer is a real asyncio task, so one modelled conversion cycle costs the same wall-clock as a real one" | Timing parity assumption between twin and silicon. (low) | area: HW | -
- RISK | tests_hardware/device_scripts/isl29125_mock_conformance_probe.py:114-129 | "p.wr(REG_C1, [0xFF])"; "p.wr(0x0F, [0x5A])" | Writes all-ones and an undefined register on the live part; relies on the teardown reset (:245-251). (low) | area: HW | -

## tests_hardware/device_scripts/reboot_persist_read.py
- ASSUME | tests_hardware/device_scripts/reboot_persist_read.py:1-3, 10-11 | "Runs after a genuine machine.reset()"; "_PATH = \"config_HWTEST_REBOOT.cfg\"" | Scratch config file persists on the board after the test. (low) | area: HW | related: HW.T03

## tests_hardware/device_scripts/reboot_persist_write.py
- INVAR | tests_hardware/device_scripts/reboot_persist_write.py:3, 21-24 | "write_config() stages and spawns the flash write as its own task (Part F.2) ... asyncio.run() would tear the loop down with the flush still queued" | Deferred-write contract: any script that writes config must `flush_pending()`. | area: HW | related: XCUT.T10
- SUPPRESS | tests_hardware/device_scripts/reboot_persist_write.py:17 | "await mgr.write_config({\"Marker\": _MARKER_VALUE}, _SCHEMA)" | One owned RP2040 flash write, gated host-side by `persistence_write` (flash/test_reboot_persistence.py:29). | area: HW | covered-by: HW.T01

## tests_hardware/device_scripts/scd30_plausibility_read.py
- ASSUME | tests_hardware/device_scripts/scd30_plausibility_read.py:1-3, 12 | "CO2 200-10000 ppm, below the datasheet's 400 floor since sub-400 readings are real and unremarkable" | Stated rationale for 200; the bench REST test uses 400 (bench/test_rest_endpoints_over_sta.py:18). | area: HW | -
- ASSUME | tests_hardware/device_scripts/scd30_plausibility_read.py:21-23 | "SCD30_Reader(i2c1, 11, trigger_sec=3, max_module_error=999, fram=None, debug=None)"; "read_loop()" | Full reader started without the cfgmgr priming other plausibility scripts use; whether its init touches the production config file or pushes defaults to SCD30 NVM is not stated. (low) | area: HW | related: HW.S02
- ASSUME | tests_hardware/device_scripts/scd30_plausibility_read.py:15, 36 | "_SETTLE_S = 45.0  # datasheet-bound response-time window"; "the sensor's own ~2s default interval" | Assumes the NVM MeasInt is 2 s (manual tier can leave 7). | area: HW | covered-by: HW.S03

## tests_hardware/device_scripts/scd30_real_irq_edge.py
- LIMIT | tests_hardware/device_scripts/scd30_real_irq_edge.py:2-3, 11-13 | "Can't fully disambiguate a real IRQ from the software fallback purely from software"; "comfortably above the SCD30's own ~2s natural interval" | Pass does not prove the IRQ path; assumes MeasInt ≈ 2 s. | area: HW | covered-by: HW.S03
- ASSUME | tests_hardware/device_scripts/scd30_real_irq_edge.py:16-31 | (no `wdt.feed()` in the script) | Relies on finishing inside run_isolated's 8 s WDT (5 s deadline + teardown). (low) | area: HW | related: HW.S09

## tests_hardware/device_scripts/scd30_same_device_rw_concurrency.py
- DRIFT | tests_hardware/device_scripts/scd30_same_device_rw_concurrency.py:1-2 | "the ONE script allowed to issue a real NVM-persisted write to the SCD30" | bus_concurrency_scd30_write_vs_siblings.py:75 also writes SCD30 NVM (the gated extra write). (low) | area: HW | related: HW.T01
- RISK | tests_hardware/device_scripts/scd30_same_device_rw_concurrency.py:66-67 | "await scd.set_ambient_pressure(1013)" | Persists 1013 hPa ambient-pressure compensation in SCD30 NVM regardless of the board's configured AmbPres; no restore. | area: HW | related: HW.T03
- ASSUME | tests_hardware/device_scripts/scd30_same_device_rw_concurrency.py:17-20 | "which read back as a stuck CO2=141.99 on every iteration. A few intervals are enough to clear it" | Settle constant from one observation (duplicated in bus_concurrency_same_device_scd30.py). | area: HW | -
- ASSUME | tests_hardware/device_scripts/scd30_same_device_rw_concurrency.py:27 | "a real soft reset - RAM/operating-state only, not an NVM write, safe every run" | Datasheet claim behind unmarked setup(). (low) | area: HW | -

## tests_hardware/device_scripts/scheduler_saturation_drop.py
- PLATFORM | tests_hardware/device_scripts/scheduler_saturation_drop.py:1-3 | "MICROPY_SCHEDULER_DEPTH=8 on rp2, SPECIFICATION.md Part F.1" | Version/port-specific constant. | area: PLAT | related: PLAT.T03
- LIMIT | tests_hardware/device_scripts/scheduler_saturation_drop.py:3, 43, 54-55 | "Widen BUSY_WAIT_MS if `dropped` comes back 0"; "if all_self_healed: print(\"RESULT: PASS dropped=...\")" | Passes even when no callback was dropped, so self-healing may never have been exercised. | area: HW | related: HW.T05

## tests_hardware/device_scripts/serving_at_default_gc.py
- RISK | tests_hardware/device_scripts/serving_at_default_gc.py:93 | "create_task(sensortask_dev.main())" | Full production main (WiFi, FRAM, config) for up to 600 s from a device script. | area: HW | covered-by: HW.T17
- LIMIT | tests_hardware/device_scripts/serving_at_default_gc.py:24-26 | "gc.threshold(-1)" | Measures at the reactive default, not the firmware's 32768 (by design, the (e) stage). (low) | area: HW | -
- SUPPRESS | tests_hardware/device_scripts/serving_at_default_gc.py:46-63 | "Re-raises unchanged, so the served outcome is exactly production's"; "setattr(WebserverService, _name, _dumping_on_failure(...))" | Class-level route patching; only uncaught MemoryErrors get a map (caught-and-degraded ones are found by the host grep). | area: HW | related: TEST.T18
- ASSUME | tests_hardware/device_scripts/serving_at_default_gc.py:27-33, 72 | "_QUIET_TO_LEAVE = 10  # consecutive idle polls; the host's own gaps between levels stay below this"; "webserver._open_conns.value" | Phase detection coupled to host pacing and a private counter. (low) | area: HW | -

## tests_hardware/device_scripts/sgp40_fram_backup_restore.py
- RISK | tests_hardware/device_scripts/sgp40_fram_backup_restore.py:57-81, 89-92 | "allocating its own chunk 0 at the same physical address reader1's did" | Writes an SGP40 VOC-state backup into production's chunk 0 (whatever module owns it in production). | area: HW | covered-by: HW.T17
- ASSUME | tests_hardware/device_scripts/sgp40_fram_backup_restore.py:54 | "asy_i2c_driver.I2C(1, 15, 14, frequency=50000)" | Omits `timeout=200000` on the shared i2c1 singleton. | area: HW | covered-by: HW.S18
- LIMIT | tests_hardware/device_scripts/sgp40_fram_backup_restore.py:2-3, 34-35, 89-91 | "a second reader simulates a fresh boot"; "stands in for the real ntp.ntp_issynced" | Reboot and NTP sync are simulated; `_FixedSource` compensation defaults (Table 10). | area: HW | -
- ASSUME | tests_hardware/device_scripts/sgp40_fram_backup_restore.py:15, 76-77 | "60s to the first natural BackupPeriod=1min trigger"; "its BackupPeriod default of 1 min is what BACKUP_WAIT_S is sized around" | Timing coupled to the driver's schema default. (low) | area: HW | -

## tests_hardware/device_scripts/sgp40_general_call_reset_hazard.py
- ASSUME | tests_hardware/device_scripts/sgp40_general_call_reset_hazard.py:31-38 | "advancing measurement means >= 2 distinct CO2 values; one unchanging value means it silently stopped (an undocumented general-call reset). A CRC failure cannot catch this" | Silent-stop oracle is ≥2 distinct CO2 values over the run. | area: HW | related: HW.T05
- INVAR | tests_hardware/device_scripts/sgp40_general_call_reset_hazard.py:49-51, 110 | "this group's one NVM-persisted write happens once per session in flash/conftest.py's ... fixture"; "real production path: ends with _reset()'s general-call broadcast" | Depends on the host fixture; issues 8 real general-call resets on i2c1. | area: HW | related: HW.T01

## tests_hardware/device_scripts/sgp40_voc_algorithm_quality.py
- ASSUME | tests_hardware/device_scripts/sgp40_voc_algorithm_quality.py:15-18, 58 | "45s documented blackout + margin"; "MAX_SINGLE_STEP_JUMP = 300  # generous relative to the algorithm's own adaptive-lowpass smoothing"; "1s fixed period - the algorithm's own sampling interval assumption" | Sanity thresholds; "not an accuracy claim". (low) | area: HW | -
- ASSUME | tests_hardware/device_scripts/sgp40_voc_algorithm_quality.py:46 | "asy_i2c_driver.I2C(1, 15, 14, frequency=50000)" | Omits `timeout=200000` on the shared i2c1 singleton. | area: HW | covered-by: HW.S18
- SUPPRESS | tests_hardware/device_scripts/sgp40_voc_algorithm_quality.py:91 | "# noqa: B905 - MicroPython zip() rejects strict=" | Platform-driven suppression. (low) | area: HW | -

## tests_hardware/device_scripts/system_debug_level_raise_for_boot_log_check.py
- RISK | tests_hardware/device_scripts/system_debug_level_raise_for_boot_log_check.py:9-10, 17-18, 43-44 | "_SYS_SCHEMA ... ((\"DebugLevel\", \"int\", 0, 0, 5, None),)"; "_SYS_PATH = \"config_SYSTEM.cfg\"" | Writes the PRODUCTION SYSTEM config file through a one-field schema; effect on the file's other keys is not stated. (low) | area: HW | related: HW.T03
- ASSUME | tests_hardware/device_scripts/system_debug_level_raise_for_boot_log_check.py:34-36 | "the restore phase then drives DebugLevel to 0, which is the state that silently breaks the rest of the bench tier" | Bench-tier log-string oracles depend on DebugLevel ≥ 3. | area: HW | covered-by: HW.S14
- ASSUME | tests_hardware/device_scripts/system_debug_level_raise_for_boot_log_check.py:12-13 | "_BACKUP_PATH = \"config_HWTEST_DEBUGLEVEL_BACKUP.cfg\""; "_VERBOSE_LEVEL = 3  # print_log.py's _LOG_ONCE" | Backup file left on board; level constant mirrors print_log. (low) | area: HW | -

## tests_hardware/device_scripts/system_debug_level_restore_after_boot_log_check.py
- INVAR | tests_hardware/device_scripts/system_debug_level_restore_after_boot_log_check.py:1-3, 30-31 | "Run from a `finally` block in the driving test"; "unflushed, the restore reports success while the on-disk DebugLevel keeps whatever the raise phase left there" | Restore correctness depends on flush + caller discipline. (low) | area: HW | -

## tests_hardware/device_scripts/system_service_restarts_a_real_dead_task.py
- MIRROR | tests_hardware/device_scripts/system_service_restarts_a_real_dead_task.py:34-36 | "task_errors capped at 200 ... (_TASK_FAIL_MAX=300, _TASK_FAIL_INCREMENT=100 per cycle)" | Supervisor constants copied into a timing window (~3.5 s). | area: HW | related: XCUT.T02

## tests_hardware/device_scripts/timer_alarm_pool_exhaustion.py
- PLATFORM | tests_hardware/device_scripts/timer_alarm_pool_exhaustion.py:1-3, 12 | "Timer.init() raises OSError(ENOMEM) once the RP2040's real hardware alarm pool is exhausted"; "the real pool is small and fixed" | F.2 platform claim confirmed on silicon (count reported, not pinned). | area: PLAT | related: PLAT.T03
- SUPPRESS | tests_hardware/device_scripts/timer_alarm_pool_exhaustion.py:12, 25-28 | "# noqa: B007"; "except Exception: pass" | Lint suppression and swallowed deinit errors. (low) | area: HW | -

## tests_hardware/device_scripts/uart_crossover_exchange.py
- INVAR | tests_hardware/device_scripts/uart_crossover_exchange.py:4-6 | "per C.8's standing constraint that a hazard-tier test must not touch the RP2040's own flash filesystem. Both loggers are RAM-only" | Wear rule for UART scripts, by convention. (low) | area: HW | related: HW.T01
- MIRROR | tests_hardware/device_scripts/uart_crossover_exchange.py:1-2, 26-33 | "GP0<->GP9, GP1<->GP8"; "Mirrors sensortask_dev.py's own pair: 2ms while a transaction is in flight, 50ms while the line is idle" | Pins, payload 48, timeout 1000 ms, 115200 baud, poll rates hand-copied from the generated dev module / dev.toml (same in uart_crossover_recovery.py:26-33). | area: HW | related: HW.T08
- LIMIT | tests_hardware/device_scripts/uart_crossover_exchange.py:34-36, 72-73 | "a link that never answers parks the listener in uart_listen()'s one unbounded read, and waiting that out outlasts the watchdog"; "clear() is the module's own documented unstick" | src listener has an unbounded read; scripts must poll-and-feed and call clear() (J.5). | area: UART | related: UART.T02
- ASSUME | tests_hardware/device_scripts/uart_crossover_exchange.py:43-45 | "Three data chunks: enough to exercise a real multi-frame train's chunk indexing ... without spending a minute of wire time on the maximum 254" | Docstring says "maximum-length train" (:1) but only 3 chunks are sent. (low) | area: HW | -

## tests_hardware/device_scripts/uart_crossover_recovery.py
- LIMIT | tests_hardware/device_scripts/uart_crossover_recovery.py:4-6, 57-64, 126-133 | "a future external injector implements the same three methods"; "desync() re-inits it at a baud rate the other end does not share" | `desync()` is defined but never called — the baud-mismatch fault is not exercised; "within the specified window" is not timed. | area: HW | related: HW.T05
- SETTLED | tests_hardware/device_scripts/uart_crossover_recovery.py:139-141 | "A mismatched payload_size is agreed out of band and never negotiated, so it cannot be recovered from - only diagnosed" | Owner decision (no negotiation) pinned on silicon. | area: UART | -

## tests_hardware/device_scripts/uart_idle_poll_rate.py
- ASSUME | tests_hardware/device_scripts/uart_idle_poll_rate.py:17-20 | "_MIN_RATIO = 5  # measured 20.6x"; "the bound is deliberately loose on absolute counts" | Threshold from one measurement; absolute count bounded to ±2× of 60. | area: HW | related: UART.T10
- SUPPRESS | tests_hardware/device_scripts/uart_idle_poll_rate.py:32, 35, 38, 57 | "# type: ignore[attr-defined]"; "uart.poller = counter  # type: ignore[assignment]" | Four type suppressions for the counting poller wrapper. (low) | area: HW | -
- LIMIT | tests_hardware/device_scripts/uart_idle_poll_rate.py:49-51 | "UART1 alone: nothing drives UART0 ... the listener parks in the one deadline-less wait this protocol issues" | Only the responder's deadline-less wait is covered. (low) | area: UART | related: UART.T02

## tests_hardware/device_scripts/uart_read_never_blocks_the_loop.py
- LIMIT | tests_hardware/device_scripts/uart_read_never_blocks_the_loop.py:4-5, 46, 60 | "Raw machine.UART on purpose: this pins the behaviour the driver's clamp exists to avoid, so it stays true independently of how asy_uart_driver is arranged internally" | Measures the platform hazard and a hand-written clamp, not asy_uart_driver's own clamp — a driver regression would not fail it. | area: UART | related: UART.T10
- ASSUME | tests_hardware/device_scripts/uart_read_never_blocks_the_loop.py:15-19 | "~4.4ms measured"; "~280us measured worst case" | `_CLAMPED_MAX_US = wire/3` sits between two single measurements. | area: HW | related: UART.T10
- RISK | tests_hardware/device_scripts/uart_read_never_blocks_the_loop.py:42-43, 53-58 | "while not any(ev & select.POLLIN for _, ev in poller.ipoll(0)): pass" | Unbounded busy-waits with no WDT feed: a missing jumper ends in a WDT reset, not a FAIL line. (low) | area: HW | -
- PLATFORM | tests_hardware/device_scripts/uart_read_never_blocks_the_loop.py:68-71 | "POLLIN firing on a nearly empty buffer is the precondition for the whole finding" | rp2 UART readiness semantics (F.5.8), re-check on a version move. | area: PLAT | related: PLAT.T06

## tests_hardware/device_scripts/uart_link_under_concurrent_system_load.py
- DRIFT | tests_hardware/device_scripts/uart_link_under_concurrent_system_load.py:1-2 vs 146-148 | "both I2C buses" vs "SCD30 and SGP40 both sit on i2c1 on this bench ... the loop labelled i2c0 is really \"the other device on the shared bus\"" | i2c0 is never loaded; counters are mislabelled. (low) | area: HW | -
- ASSUME | tests_hardware/device_scripts/uart_link_under_concurrent_system_load.py:30-36 | "_MIN_TRANSFERS = 20  # measured 58 unloaded-by-comparison"; "Measured worst case under this load is ~114ms" | Floors from single measurements. | area: HW | related: UART.T10
- DRIFT | tests_hardware/device_scripts/uart_link_under_concurrent_system_load.py:107-110 | "a 6144 B swing that swamped the 2048 B bound (queue F7)" | Deleted queue row cited. | area: HW | covered-by: DOC.S06
- LIMIT | tests_hardware/device_scripts/uart_link_under_concurrent_system_load.py:95-101, 228 | "except MemoryError: load.alloc_failures += 1 ... gc.collect()" | Allocation failures in the churn load are caught, counted and only printed, never asserted. (low) | area: HW | related: TEST.T18
- ASSUME | tests_hardware/device_scripts/uart_link_under_concurrent_system_load.py:124-128, 141 | "prove it under MicroPython's own real default (no proactive collection)"; "dev_legacy/README.md's wiring: i2c0 (13, 12), i2c1 (15, 14), SPI0 (2, 3, 4) with FRAM CS=5" | Pins cited from the legacy bench doc rather than dev.toml. | area: HW | related: HW.T08
- LIMIT | tests_hardware/device_scripts/uart_link_under_concurrent_system_load.py:216-220 | "real per-transaction retention would be thousands of bytes, far above this bound" | Heap-growth check skipped if the one-third sample was never taken; 2048 B bound. (low) | area: HW | -

## tests_hardware/device_scripts/watchdog_starvation_reset.py
- PLATFORM | tests_hardware/device_scripts/watchdog_starvation_reset.py:2-3, 7-9 | "Arms a short 1500ms window and never feeds it" | Relies on re-arming an already-armed rp2 WDT (8000 ms from run_isolated) with a shorter timeout; result read host-side without `reset_cause()`. | area: PLAT | covered-by: HW.S15
- MIRROR | tests_hardware/device_scripts/watchdog_starvation_reset.py:10 | "print(\"WDT armed, starving now\")" | Banner string matched by flash/test_watchdog_starvation.py:13. (low) | area: HW | -

## tests_hardware/device_scripts/wifi_country_hostname_edge_values.py
- LIMIT | tests_hardware/device_scripts/wifi_country_hostname_edge_values.py:14-16, 31-35, 40 | "PASS accepted"; "PASS raised"; "RESULT: interpreter survived both edge-value calls" | Every branch prints PASS and no host wrapper runs it (orphan). | area: HW | covered-by: HW.S16
- ASSUME | tests_hardware/device_scripts/wifi_country_hostname_edge_values.py:2-3, 37-39 | "whose UTF-8 byte count exceeds the real 32-byte cap"; "asy_wifi_service.py's own try/except around both calls means neither should ever be able to crash the process" | Schema counts characters while the platform cap is bytes (pinned gap); hardcodes country "DE". | area: NET | related: NET.S17

## tests_hardware/device_scripts/wifi_reconnect_after_failed_attempts_repro.py
- MIRROR | tests_hardware/device_scripts/wifi_reconnect_after_failed_attempts_repro.py:9-10, 109 | "REAL_SSID = \"sensors-bench-ap\""; "REAL_PW = \"<redacted: bench PSK, HW.T11>\""; "password=\"12345678\"" | Committed bench SSID/PSK and hotspot password (copy #5) — consistency item vs the run-time `bench.ap_password()` convention. | area: HW | covered-by: HW.S08
- LIMIT | tests_hardware/device_scripts/wifi_reconnect_after_failed_attempts_repro.py:1-3 | "one-off repro ... (NOT part of the routine test suite)"; "recover afterward via hard_reset()" | Orphan diagnostic; leaves the board on an ad-hoc WLAN object. | area: HW | covered-by: HW.S16
- RISK | tests_hardware/device_scripts/wifi_reconnect_after_failed_attempts_repro.py:76, 134 | "max_polls=240 ... up to 120s"; "max_polls=1200 ... up to 600s" | No WDT feed anywhere; if main.py had armed the 8 s watchdog before the attach, the board resets mid-diagnostic (same shape as the other repro). | area: HW | related: HW.S09
- MIRROR | tests_hardware/device_scripts/wifi_reconnect_after_failed_attempts_repro.py:13, 15, 67, 87-88, 96 | "HOTSPOT_HOSTNAME = \"sensornode-dev\""; "_STAT_OBTAINING_IP = 2  # matches asy_wifi_service.py's own module-level constant"; "pm=0xA11140"; "wifi_refresh_sec=5s cadence" | src constants copied into a diagnostic (hostname differs from both DUT candidates in conftest.py). (low) | area: HW | -

## tests_hardware/device_scripts/wifi_service_reconnect_repro.py
- RISK | tests_hardware/device_scripts/wifi_service_reconnect_repro.py:12-15, 70-78, 89, 119 | "writing it is what stranded the bench (QUEUE F1)"; "The scratch file holds a full WIFI config, real password included"; "up to 3 minutes"; "up to 10 minutes" | Up to ~13 min with no WDT feed; a watchdog reset skips `_drop_scratch()`, leaving `config_HWTEST_WIFI.cfg` with the real password on the board. | area: HW | covered-by: HW.S09
- LIMIT | tests_hardware/device_scripts/wifi_service_reconnect_repro.py:1-3 | "diagnostic script #2 (NOT part of the routine test suite)" | Orphan diagnostic, run by hand. | area: HW | covered-by: HW.S16
- MIRROR | tests_hardware/device_scripts/wifi_service_reconnect_repro.py:24, 101, 133 | "_PHASE_NAMES = {0: \"STA_SEEKING\", 1: \"STA_ESTABLISHED\", 2: \"HOTSPOT\", 3: \"DEACTIVATED\"}"; "`data` is the terminating exception, set by asyncio/core.py's run_until_complete()" | Copies src phase values and relies on a MicroPython asyncio internal. (low) | area: HW | -
- RISK | tests_hardware/device_scripts/wifi_service_reconnect_repro.py:82-99 | "overwriting SSID with a garbage value"; "if phase == 2: reached_hotspot = True" | Drives the live board into hotspot mode (bench link lost) until the restore path runs. (low) | area: HW | related: HW.T03

## Coverage
| file | comment/doc lines read | items |
|---|---|---|
| tests_hardware/bench/dns_probe.py | 20 (full file read) | 3 |
| tests_hardware/bench/test_bus_concurrency_under_api_load.py | 96 (full file read) | 18 |
| tests_hardware/bench/test_end_to_end_timing.py | 57 (full file read) | 11 |
| tests_hardware/bench/test_heap_under_connection_ceiling.py | 42 (full file read) | 9 |
| tests_hardware/bench/test_hotspot_role_reversal.py | 135 (full file read) | 25 |
| tests_hardware/bench/test_memory_stress_bench.py | 34 (full file read) | 12 |
| tests_hardware/bench/test_network_resilience.py | 312 (full file read) | 55 |
| tests_hardware/bench/test_rest_endpoints_over_sta.py | 36 (full file read) | 7 |
| tests_hardware/bench/test_sensor_config_push_over_real_hardware.py | 53 (full file read) | 9 |
| tests_hardware/bench/test_serving_heap_at_default_gc.py | 21 (full file read) | 6 |
| tests_hardware/bench/test_uart_link_under_api_load.py | 28 (full file read) | 8 |
| tests_hardware/bench/test_wifi_networking.py | 42 (full file read) | 6 |
| tests_hardware/bench_control.py | 74 (full file read) | 16 |
| tests_hardware/conftest.py | 28 (full file read) | 24 |
| tests_hardware/device_scripts/allocation_need_per_source.py | 28 (full file read) | 7 |
| tests_hardware/device_scripts/bmp3xx_plausibility_read.py | 10 (full file read) | 5 |
| tests_hardware/device_scripts/bmp3xx_same_device_rw_concurrency.py | 7 (full file read) | 3 |
| tests_hardware/device_scripts/bus_concurrency_cross_device_scd30_sgp40.py | 14 (full file read) | 3 |
| tests_hardware/device_scripts/bus_concurrency_isl29125_write_vs_siblings.py | 10 (full file read) | 2 |
| tests_hardware/device_scripts/bus_concurrency_same_device_scd30.py | 13 (full file read) | 3 |
| tests_hardware/device_scripts/bus_concurrency_scd30_write_vs_siblings.py | 9 (full file read) | 2 |
| tests_hardware/device_scripts/bus_deinit_is_a_noop_on_real_hardware.py | 9 (full file read) | 4 |
| tests_hardware/device_scripts/bus_topology_autodetect_and_hazard_sweep.py | 29 (full file read) | 6 |
| tests_hardware/device_scripts/float_boundary_2pow24.py | 11 (full file read) | 3 |
| tests_hardware/device_scripts/fram_busy_status_lockout.py | 9 (full file read) | 3 |
| tests_hardware/device_scripts/fram_capacity_after_full_system_build.py | 6 (full file read) | 3 |
| tests_hardware/device_scripts/fram_cs_hijack_fault_injection_and_recovery.py | 25 (full file read) | 5 |
| tests_hardware/device_scripts/fram_error_log_reset_during_boot_window.py | 12 (full file read) | 2 |
| tests_hardware/device_scripts/fram_error_log_reset_race_seed_and_race.py | 17 (full file read) | 3 |
| tests_hardware/device_scripts/fram_error_log_reset_race_verify.py | 16 (full file read) | 3 |
| tests_hardware/device_scripts/fram_error_log_roundtrip.py | 12 (full file read) | 2 |
| tests_hardware/device_scripts/fram_manager_roundtrip.py | 4 (full file read) | 1 |
| tests_hardware/device_scripts/fram_pause_unpause_and_gating.py | 33 (full file read) | 5 |
| tests_hardware/device_scripts/fram_reset_race_during_write_seed_and_race.py | 16 (full file read) | 3 |
| tests_hardware/device_scripts/fram_reset_race_during_write_verify_recovery.py | 6 (full file read) | 1 |
| tests_hardware/device_scripts/fram_same_device_rw_concurrency.py | 7 (full file read) | 3 |
| tests_hardware/device_scripts/fram_write_protect_roundtrip.py | 23 (full file read) | 4 |
| tests_hardware/device_scripts/heap_headroom_after_full_system_build.py | 45 (full file read) | 7 |
| tests_hardware/device_scripts/heap_layout_after_full_boot_sequence.py | 57 (full file read) | 6 |
| tests_hardware/device_scripts/heap_under_connection_ceiling.py | 13 (full file read) | 3 |
| tests_hardware/device_scripts/isl29125_cross_device_concurrency.py | 8 (full file read) | 2 |
| tests_hardware/device_scripts/isl29125_lighting_scenarios.py | 62 (full file read) | 6 |
| tests_hardware/device_scripts/isl29125_mechanism_envelope.py | 42 (full file read) | 4 |
| tests_hardware/device_scripts/isl29125_mock_conformance_probe.py | 39 (full file read) | 5 |
| tests_hardware/device_scripts/isl29125_plausibility_read.py | 22 (full file read) | 5 |
| tests_hardware/device_scripts/isl29125_real_irq_edge.py | 34 (full file read) | 5 |
| tests_hardware/device_scripts/isl29125_same_device_rw_concurrency.py | 11 (full file read) | 3 |
| tests_hardware/device_scripts/reboot_persist_read.py | 3 (full file read) | 1 |
| tests_hardware/device_scripts/reboot_persist_write.py | 6 (full file read) | 2 |
| tests_hardware/device_scripts/scd30_plausibility_read.py | 12 (full file read) | 3 |
| tests_hardware/device_scripts/scd30_real_irq_edge.py | 6 (full file read) | 2 |
| tests_hardware/device_scripts/scd30_same_device_rw_concurrency.py | 12 (full file read) | 4 |
| tests_hardware/device_scripts/scheduler_saturation_drop.py | 8 (full file read) | 2 |
| tests_hardware/device_scripts/serving_at_default_gc.py | 21 (full file read) | 4 |
| tests_hardware/device_scripts/sgp40_fram_backup_restore.py | 17 (full file read) | 4 |
| tests_hardware/device_scripts/sgp40_general_call_reset_hazard.py | 10 (full file read) | 2 |
| tests_hardware/device_scripts/sgp40_voc_algorithm_quality.py | 13 (full file read) | 3 |
| tests_hardware/device_scripts/system_debug_level_raise_for_boot_log_check.py | 9 (full file read) | 3 |
| tests_hardware/device_scripts/system_debug_level_restore_after_boot_log_check.py | 5 (full file read) | 1 |
| tests_hardware/device_scripts/system_service_restarts_a_real_dead_task.py | 7 (full file read) | 1 |
| tests_hardware/device_scripts/timer_alarm_pool_exhaustion.py | 5 (full file read) | 2 |
| tests_hardware/device_scripts/uart_crossover_exchange.py | 21 (full file read) | 4 |
| tests_hardware/device_scripts/uart_crossover_recovery.py | 23 (full file read) | 2 |
| tests_hardware/device_scripts/uart_idle_poll_rate.py | 19 (full file read) | 3 |
| tests_hardware/device_scripts/uart_link_under_concurrent_system_load.py | 40 (full file read) | 6 |
| tests_hardware/device_scripts/uart_read_never_blocks_the_loop.py | 13 (full file read) | 4 |
| tests_hardware/device_scripts/watchdog_starvation_reset.py | 3 (full file read) | 2 |
| tests_hardware/device_scripts/wifi_country_hostname_edge_values.py | 12 (full file read) | 2 |
| tests_hardware/device_scripts/wifi_reconnect_after_failed_attempts_repro.py | 23 (full file read) | 4 |
| tests_hardware/device_scripts/wifi_service_reconnect_repro.py | 21 (full file read) | 4 |
| tests_hardware/error_log_helpers.py | 16 (full file read) | 5 |
| tests_hardware/flash/conftest.py | 9 (full file read) | 3 |
| tests_hardware/flash/test_bus_concurrency.py | 46 (full file read) | 10 |
| tests_hardware/flash/test_bus_electrical_timing.py | 40 (full file read) | 8 |
| tests_hardware/flash/test_fram_storage.py | 48 (full file read) | 8 |
| tests_hardware/flash/test_memory_stress.py | 34 (full file read) | 7 |
| tests_hardware/flash/test_reboot_persistence.py | 19 (full file read) | 8 |
| tests_hardware/flash/test_sensor_accuracy.py | 17 (full file read) | 4 |
| tests_hardware/flash/test_task_supervisor.py | 3 (full file read) | 1 |
| tests_hardware/flash/test_toolchain_flash_boot.py | 25 (full file read) | 7 |
| tests_hardware/flash/test_uart_crossover.py | 20 (full file read) | 5 |
| tests_hardware/flash/test_watchdog_starvation.py | 13 (full file read) | 4 |
| tests_hardware/harness.py | 126 (full file read) | 25 |
| tests_hardware/heap_map.py | 30 (full file read) | 9 |
| tests_hardware/http_client.py | 14 (full file read) | 4 |
| tests_hardware/isl29125_conformance.py | 10 (full file read) | 4 |
| tests_hardware/manual/__main__.py | 3 (full file read) | 1 |
| tests_hardware/manual/manual_bus_electrical.py | 1 (full file read) | 5 |
| tests_hardware/manual/manual_persistence.py | 3 (full file read) | 5 |
| tests_hardware/manual/manual_sensor_accuracy.py | 12 (full file read) | 7 |
| tests_hardware/manual/manual_toolchain.py | 5 (full file read) | 2 |
| tests_hardware/manual/manual_wifi.py | 3 (full file read) | 4 |
| tests_hardware/manual/runner.py | 20 (full file read) | 4 |
| tests_hardware/ntp_probe.py | 7 (full file read) | 2 |
| tests_hardware/rogue_udp_responder.py | 6 (full file read) | 2 |
| tests_hardware/soak_tiers.py | 3 (full file read) | 2 |
| tests_hardware/website_identity.py | 12 (full file read) | 5 |
| **total (97 files)** | 2491 | 547 |

## Totals per kind
| kind | count |
|---|---|
| ASSUME | 143 |
| LIMIT | 77 |
| SUPPRESS | 56 |
| RISK | 53 |
| DRIFT | 45 |
| MIRROR | 44 |
| INVAR | 41 |
| PLATFORM | 40 |
| SETTLED | 34 |
| WORKAROUND | 8 |
| OPENQ | 4 |
| TODO | 2 |
| **total** | 547 |

Dedup: 125 items covered-by an existing plan ID, 233 related, 189 new (-).

## Top 10
1. FRAM evidence fabrication/overwrite by device scripts: `device_scripts/fram_error_log_reset_race_seed_and_race.py:14-15, 28-31` + `fram_error_log_reset_race_verify.py:31-32` leave errno 5/6/7 entries in production's chunk 0 (the exact CLAUDE.md incident shape); ~12 further scripts overwrite chunk 0 or raw address 0 (`fram_same_device_rw_concurrency.py:13`, `fram_manager_roundtrip.py`, `sgp40_fram_backup_restore.py`, ...) — covered-by HW.T17, but the concrete list is new.
2. Gate mechanics: only `persistence_write`/`scd30_extra_write` deselect (`conftest.py:116-133`); `long_soak`, `flash_cycle`, `multi_day_rollover`, `neopixel_sweep` are in-test skips, plus an unconditional `@pytest.mark.skip` (`bench/test_hotspot_role_reversal.py:232-241`) and firmware-absence skips (`bench/test_uart_link_under_api_load.py:39-57`, `flash/test_uart_crossover.py:19-34`) — HW.T13/SCR.T05.
3. `neopixel_sweep` help says "Spends no write of any kind" (`conftest.py:65`) while `isl29125_mechanism_envelope.py:100-196` makes ~9 flash writes — HW.S05.
4. Unrestored persisted state: garbage-SSID PUT with pre-restore asserts outside try/finally (`bench/test_network_resilience.py:520-533`); WarnCO2=1700 never restored (`test_hotspot_role_reversal.py:274-281`); SCD30 NVM `set_ambient_pressure(1013)` / `set_temperature_offset(4.0)` never restored (`scd30_same_device_rw_concurrency.py:67`, `bus_concurrency_scd30_write_vs_siblings.py:75`) — HW.T03.
5. Vacuous or weakened oracles: `is_device_present() or http…` short-circuit (`bench/test_end_to_end_timing.py:85-88`); DNS/NTP "real UDP" tests assert only absence of failure words (`bench/test_wifi_networking.py:54-70`); manual `confirm()`-only tests can never FAIL (`manual/runner.py:27-28, 94-98`); scheduler test passes with nothing dropped (`scheduler_saturation_drop.py:43, 54`) — HW.T05.
6. Contradictory in-file claims about whether an "Unchanged" PUT fires `post_asy_fct` (`bench/test_network_resilience.py:270-272` vs `434-436, 514-516`) — XCUT.T11.
7. Known transient over-admission by one above `max_connections` under load (`bench/test_network_resilience.py:646-648`) and ceiling rejections leaving no log trace (`:690-693`) — REST.T06/REST.T08.
8. Committed credential copies for the consistency topic: `conftest.py:165`, `test_network_resilience.py:505`, `test_hotspot_role_reversal.py:43`, `manual/manual_wifi.py:19,30`, `wifi_reconnect_after_failed_attempts_repro.py:9-10,109`, with two different stated sources of truth — HW.T11/HW.S08/HW.S24.
9. Host hazards: `conftest.py:187` calls `join_dut_hotspot()` (which does `ap_down()`) outside the try/finally that restores the AP, and scans while the AP is still up against `is_ssid_visible()`'s stated precondition (`bench_control.py:195-196`); iptables/netem left on a killed run — HW.T12.
10. Tree-vs-image and measurement provenance: every ceiling/body-cap oracle reads the TREE (`harness.py:39-41`, `test_network_resilience.py:617, 768-770, 800-807`), and thresholds rest on single dated measurements (`heap_headroom_after_full_system_build.py:36-39`, `uart_idle_poll_rate.py:20`, `uart_read_never_blocks_the_loop.py:15-19`) — HW.T19/HW.T16.
