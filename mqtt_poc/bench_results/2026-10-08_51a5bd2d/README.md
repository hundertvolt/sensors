# MQTT PoC bench results, 2026-10-08 on `51a5bd2d`

Run by the bench Pi4 session (`session_01HaBZru65HAV9qRRZWCG2ZY`) following `mqtt_poc/BENCH_HANDOVER.md`,
with the owner's go-ahead given in that session's conversation (owner, 2026-10-08: "read the bench handover
and start the MQTT bench run").

## Setup

| | |
|---|---|
| Commit | `51a5bd2d` (branch `claude/whole-project-audit-plan-followup`) |
| Image | `dev`, `BuildDate` 2026-10-08T09:47:36Z, firmware/website `2.0b0` (`system_after_flash.json`) |
| Image replaced | `dev`, `buildDate` 2026-09-25T12:54:13Z (`system_before_flash.json`) |
| Host | `Linux raspberrypi 6.18.50+rpt-rpi-v8 #1 SMP PREEMPT Debian 1:6.18.50-1+rpt1 (2026-09-11) aarch64`, Debian GNU/Linux 13 (trixie), 4 cores, 7.6 GiB |
| Broker | mosquitto 2.0.21-1 (Debian package), avahi-daemon 0.8-16 active |
| Session path | SSH from 192.168.85.42 over `eth0` (bridge FDB), default route via `br0`; the AP never carried it |

## Preparation

- `env --tier bench`: exit 0; bridge reused, `br0` presents `eth0`'s MAC `D8:3A:DD:28:EA:5A`.
- `fram_before_flash.json`: the old image's FRAM logs held WIFI W5 ×3 (counter 13), SGP40 W13/W11
  (counter 16) and NTP E21 (counter 3); every other module was empty.
- Flash: `machine.bootloader()` over mpremote, then `sudo picotool load -x -v build/firmware-dev.uf2`, loaded
  and verified on the first attempt. The session's one flash.
- **First boot fell back to hotspot.** After the flash the board did not join the bench AP within ~4 min;
  its console showed `WIFI Hotspot mode is active` with every task running. One station kick plus one hard
  reset (`dut_ip`'s own documented first recovery step, the bench's CYW43 reconnect behaviour) and it joined
  at 192.168.85.57 within ~25 s, NTP synced. No credential push was needed.
- `fram_after_flash.json` (taken after that reset) holds only first-boot-of-a-new-image entries: `CFGMGR_*`
  W10 `STORED_DEFAULT` / W23 `CFG_KEYS_REMOVED` (config migration), WIFI W38 `WLAN_CONNECT_FAILED` (the
  hotspot fallback above), SGP40 W33/W35 (baseline restored/written before NTP gave it a timestamp).
  `MQTTState` `disabled`; all 24 FRAM modules present, `MQTT` and `CFGMGR_MQTT` included.

## The run

```bash
scripts/run_bench_hardware_suite.sh --scope mqtt \
    --allow-persistence-writes-to=networking/identity,networking/mqtt,networking/ntp,notification/autoConfig \
    2>&1 | tee "$HOME/mqtt_bench_console.log"; echo "runner exit ${PIPESTATUS[0]}"
```

### Attempt 1: stopped at L0, no board touched

Started 2026-10-08 10:01 UTC, exit 1 at 10:21 UTC. `scripts/test.sh` (GC stage -1): every MicroPython
file passed (92 files, 4,586 tests), but the backgrounded `tests_scripts/` tier hit its 1200 s bound at 73%
(`== tests_scripts/ exceeded 1200s`), and the runner stopped before L3. Root cause, two host facts, no code
defect:

1. **The `tests_scripts/` tier is slower on the Pi4 than its bound assumes.** Run alone afterwards
   (`uv run pytest tests_scripts -q --durations=30`, nothing else running) it took **1848 s** (3195 passed,
   11 skipped). The bound is Part N `runner.tests_scripts_timeout_s` = 1200 s, set at ~5× a ~248 s
   measurement on a faster host; its row owes exactly this figure ("the pytest tier's wall clock on the
   bench Pi4").
2. **Node was not on `PATH`.** `env --tier bench` installs the `.nvmrc`-pinned Node 24.21.0 into
   `~/pico-toolchain/node/` but puts it on `PATH` only for its own subprocesses, and no shell profile on the
   Pi4 adds it. That standalone run therefore also showed 41 failures, all "node is not on PATH" (five
   files); with Node on `PATH` those five files pass, 112 of 112 in 30 s. `npm test` would have failed the
   same way.

The owner chose how to continue (owner, 2026-10-08, asked "How do I continue?": "Rerun, env overrides
(Recommended)"): rerun the whole scope with Node on `PATH` for the run and `TESTS_SCRIPTS_TIMEOUT_S=3600`
(the runner's own override), no code change.

### Attempt 2

```bash
export PATH="$HOME/pico-toolchain/node/node-v24.21.0-linux-arm64/bin:$PATH" TESTS_SCRIPTS_TIMEOUT_S=3600
scripts/run_bench_hardware_suite.sh --scope mqtt \
    --allow-persistence-writes-to=networking/identity,networking/mqtt,networking/ntp,notification/autoConfig
```

Started 2026-10-08 11:09 UTC. GC stage -1 passed in full (summary below: 92 files, 4,586 tests; the
`tests_scripts/` tier 3,236 passed, 11 skipped, now inside its raised bound). At stage 32768 one test outside
this branch failed: `tests/test_asy_uart_driver.py::test_thousands_of_back_to_back_frames_at_line_rate_lose_nothing`,
a `TimeoutError` at its 60 s wall-clock bound (Part N `l1.asy_uart_driver_hammer_bound_s`) while three other
files were overrunning their 240 s per-file bound on the loaded Pi4. Before the stage was stopped, every file
covering this branch had passed at both stages: `test_asy_mqtt_client` 43/43, `test_mqtt_codec` 22/22,
`test_asy_dns_client` 39/39, `test_asy_ntp_client` 151/151, `test_asy_captive_dns` 60/60,
`test_ntp_wifi_dns_integration` 9/9, `test_ntp_fram_system_integration` 12/12, `test_sensortask_dev` 70/70,
`test_digital_twin_webserver_concurrency_dev` 20/20. The owner directed (owner, 2026-10-08): "It is not your
task to test the UART. Your only task is to test everything around MQTT and ignore anything else so far which
does not come from your changes." The run was stopped (host processes only, no board touched) and the scope
continued with `--skip-lower-levels`.

```
== Summary: scripts/test.sh ==
Commit: 51a5bd2d (uncommitted changes)
Levels: L0 PASS · L1 PASS · L2 PASS (tests/test_digital_twin_*.py only; run_digital_twin_ci.sh not run)
GC stage: -1 (reactive default)
Counts (files): passed 92 · failed 0 · skipped 0 · deselected 0 · retried 0 · recovered 0 · vacuous 0
Counts (tests_scripts tests): passed 3236 · failed 0 · skipped 11 · deselected 0 · retried 0 · recovered 0 · vacuous 0
Counts (tests): passed 4586 · failed 0 · skipped 0 · deselected 0 · retried 0 · recovered 0 · vacuous 0
Result: PASS
Exit code: 0
```

("uncommitted changes": this results directory, untracked at the time.)

### Attempt 3: the flash step (`--skip-lower-levels`), 2 of 3 failed

Started 2026-10-08 12:00 UTC; evidence in `flash_step/`. `test_env_tier_flash_recurring_run_is_idempotent`
passed. Two failed:

1. **`test_real_gc_heap_headroom_survives_a_full_system_build`: this branch's finding.** "the built object
   graph holds more than it should: 113280 > 100000 B allocated". The bound
   (`l3.heap_headroom_after_full_system_build_max_used`) is ~14% over every pre-MQTT reading,
   87,760–87,968 B. An ad-hoc read-only board script (run from RAM via `run_isolated`, no flash write, no
   `setup()`) attributed the client's share:

   | On the board, `gc.mem_alloc()` deltas after a collect | Bytes |
   |---|---|
   | `mqtt_codec` import | 640 |
   | `asy_mqtt_client` import | 2,288 |
   | one `MQTTClient` construction | 8,432 |
   | **MQTT total** | **11,360** |

   DESIGN.md §5 estimated "about 5 KB plus the object"; the buffers are that, the rest is the client's
   `SensorReaderConfig` base, config manager and module objects. 87,968 + 11,360 = 99,328 B: MQTT alone
   takes the bound to its edge. The other ~14 KB of the +25.3 KB is not the client's and is unattributed
   (the audit base since the 2026-09-19 readings, or this branch's wiring); a second image to compare against
   would need a second flash. The bound changes only by a new derivation, never to fit a reading (audit G4),
   so it was left untouched.
2. **`test_every_fram_wired_module_gets_a_real_chunk_after_a_full_system_build`: not this branch's.** The
   device script aborts with "scd30.cfgmgr.pr is not a PrintLogHistoryStore at all (expected FRAM-backed -
   dev.toml wires fram_target everywhere)", but `CFGMGR_SCD30` is RAM-only by the owner's decision (owner,
   2026-09-29, on the FRC settings: 'no extra FRAM chunk'; CLAUDE.md). The script stops there, before the
   MQTT chunks; `fram_after_flash.json` shows `MQTT` and `CFGMGR_MQTT` served from FRAM on the running image.

The owner chose (owner, 2026-10-08, asked "How do I go on?": "Run bench step now (Recommended)"): run the
66 scoped bench tests on their own, both flash findings recorded for a later decision.

### Attempt 4: the bench step on its own

The runner's bench-step line with the scope's 66 selections (`tests_hardware/run_scopes.py mqtt bench`),
`--allow-persistence-writes-to=networking/identity,networking/mqtt,networking/ntp,notification/autoConfig`,
and a not-clean reason naming everything above. Started 2026-10-08 12:12 UTC.
Ended 12:55 UTC, runner exit 1: **62 passed, 2 failed, 1 skipped** (the permanent
`test_spoofed_off_subnet_source_address_is_ignored`), **1 recovery pass**. Evidence in `bench_step/`; the
measured values in `measurements.md`.

- **The MQTT client, 18 of 18**, one of them a recovery pass (the AP outage, reconnected 15.4 s after the
  bench's documented recovery hard reset).
- **The connection ceiling and body cap, 7 of 7**; **heap with the client resident, 5 of 5** (no figures
  kept, see `measurements.md`); **cold boot, REST reboot, the website, 3 of 3**.
- **The hotspot role reversal, 24 of 24 run** (plus the permanent skip), stage 6's credential handoff and
  the flip back included.
- **NTP and the resolver, 7 of 9.** Both failures are a precondition, not the behaviour under test:
  - `test_ntp_recovers_via_its_own_retry_timer_after_a_transient_outage_with_no_reboot`: "timed out after
    30.0s waiting for: test precondition: DUT to report NTP-synced before this test's own transient-outage
    fault starts";
  - `test_ntp_connected_socket_rejects_a_reply_from_an_unexpected_source`: "GET /status's UTCTime is null:
    the DUT has not synced NTP yet, so its clock is no signal for this test".

  **Cause: the scope's order** (`tests_hardware/run_scopes.py`, this branch's file).
  `test_real_ntp_handles_a_genuinely_unreachable_server_without_crashing` hard-resets the board with UDP 123
  blocked and unblocks it without waiting for a resync, so the board boots unsynced and NTP's unsynced
  backoff (10 s doubling to 600 s, `src/asy_ntp_client.py`) puts its next attempt minutes away. The scope
  ran that test *before* the two that need a synced board; the full tier collects
  `test_network_resilience.py` before `test_wifi_networking.py`, so there they run first. Consistent with
  it: the board stayed unsynced from then on, and a passive 40 s capture at 12:40 UTC saw no UDP 53/123
  from it at all, while the Pi4 itself reached `pool.ntp.org` and no `iptables` rule was left. The NTP
  client and the resolver's unicast path are unchanged by this branch.

```
== Summary: run_bench_hardware_suite_scope_mqtt ==
Commit: 51a5bd2d (uncommitted changes)
Levels: L4, scope mqtt
Counts (tests): passed 62 · failed 2 · skipped 1 · deselected 0 · retried 0 · recovered 1 · vacuous 0
Failed:
  - tests_hardware/bench/test_network_resilience.py::test_ntp_recovers_via_its_own_retry_timer_after_a_transient_outage_with_no_reboot: failed in call: TimeoutError: timed out after 30.0s waiting for: test precondition: DUT to report NTP-synced before this test's own transient-outage fault starts
  - tests_hardware/bench/test_network_resilience.py::test_ntp_connected_socket_rejects_a_reply_from_an_unexpected_source: failed in call: AssertionError: GET /status's UTCTime is null: the DUT has not synced NTP yet, so its clock is no signal for this test
Skipped:
  - tests_hardware/bench/test_hotspot_role_reversal.py::test_spoofed_off_subnet_source_address_is_ignored: Raw-socket feasibility on the bench Rpi4 not yet checked - spoofing an off-subnet UDP source address needs either a raw socket (CAP_NET_RAW) or a second network namespace with a routable off-subnet address, neither confirmed practical here yet. Flagged rather than guessed at - implement once a concrete spoofing mechanism is confirmed to work.
Deselected: none
Passed only on retry: none
Recovery passes:
  - tests_hardware/bench/test_mqtt_broker_faults.py::test_an_ap_outage_pauses_the_client_and_it_returns_with_the_link: reconnected 15.4s after a recovery hard reset; 0 failed attempt(s) logged
Notes:
  - tests_hardware/bench/test_mqtt_broker_faults.py::test_the_client_connects_and_announces_itself_online: connected within 1.3s of the first poll; MQTTState 'connected'
  - tests_hardware/bench/test_mqtt_broker_faults.py::test_every_sensor_publishes_strict_json_on_its_own_topic: largest measurement payload 245 B of the 384 B slot
  - tests_hardware/bench/test_mqtt_broker_faults.py::test_a_killed_broker_is_reconnected_after_its_restart: reconnected 4.2s after the restart (outage 5s)
  - tests_hardware/bench/test_mqtt_broker_faults.py::test_a_stalled_broker_is_detected_by_the_pingresp_deadline: stall detected in 21.0s; reconnected 8.7s after the resume
  - tests_hardware/bench/test_mqtt_broker_faults.py::test_a_silent_path_loss_is_detected_and_recovered: path loss detected in 21.5s ('no pingresp'); reconnected 13.8s after the restore
  - tests_hardware/bench/test_mqtt_broker_faults.py::test_a_reset_path_ends_the_connection_and_attempts_stay_bounded: reset path ended the connection in 6.7s; reconnected 11.4s after the restore
  - tests_hardware/bench/test_mqtt_broker_faults.py::test_a_duplicate_client_id_is_bounded_by_the_backoff: 0 retakes in 20s against 1 by the duplicate; reconnected 39.8s after it left
  - tests_hardware/bench/test_mqtt_broker_faults.py::test_an_inbound_flood_leaves_rest_serving_and_the_session_up: 3001 of 3001 messages taken; GET /status under the flood: max 1.93s, median 1.84s
  - tests_hardware/bench/test_mqtt_broker_faults.py::test_an_inbound_qos1_burst_is_acknowledged_in_full: 500 QoS 1 messages acknowledged in 7.1s
  - tests_hardware/bench/test_mqtt_broker_faults.py::test_the_broker_is_found_by_the_bench_hosts_local_name: raspberrypi.local resolved to 192.168.85.75 and connected within 1.6s
  - tests_hardware/bench/test_mqtt_broker_faults.py::test_a_reboot_reconnects_from_the_stored_settings: connected 15.8s after the reset; the broker published the will on the takeover
  - tests_hardware/bench/test_mqtt_broker_faults.py::test_the_broker_faults_run_clean_at_micropythons_default_gc: timeline ['connected', 'reconnected after kill', 'stall detected', 'reconnected after stall', 'connected after floods', 'reconnected after takeover', 'done']; free heap min 2192 B over 42 samples
  - tests_hardware/bench/test_network_resilience.py::test_concurrent_mixed_body_sizes_are_never_answered_with_the_wrong_status: 19 answered, 21 refused at the connection ceiling, 0 answered wrongly
Checked nothing: none
Result: FAIL (pytest exited 1)
Exit code: 1
```

("uncommitted changes": this results directory.)

**The fix** (the commit after these results): `tests_hardware/run_scopes.py` now lists the scope's NTP/DNS
tests in the full tier's relative order, and `tests_scripts/test_run_scopes.py` pins that order for every
scope (it fails on the order this run used). Not yet re-verified on the board. In the full tier's own order,
`test_ntp_server_sends_garbage_instead_of_a_valid_response` also hard-resets the board against a rogue NTP
answer shortly before `test_ntp_connected_socket_rejects_a_reply_from_an_unexpected_source`, which asserts a
synced clock at once, so the same precondition could still bite there; only a rerun of the block shows it.

### Attempt 5: the NTP/DNS block rerun in the fixed order (`0bf85a47`)

The owner asked for it (owner, 2026-10-08: "Yes run it"); `--allow-persistence-writes-to=networking/ntp` only.
**8 passed, 1 failed**; evidence in `ntp_rerun_step/`. `test_ntp_recovers_via_its_own_retry_timer_after_a_transient_outage_with_no_reboot`
now passes, so the reorder fixed that one. `test_ntp_connected_socket_rejects_a_reply_from_an_unexpected_source`
still fails its precondition ("GET /status's UTCTime is null"), now in the full tier's own order: the two
tests before it (`test_ntp_server_sends_garbage_instead_of_a_valid_response`,
`test_dns_server_sends_garbage_instead_of_a_valid_response`) each hard-reset the board against bad answers
and end without waiting for a resync, and this test asserts a synced clock at once, with no wait. So the full
tier would hit the same, independent of this branch: a precondition gap in the test, which reads its clock
once rather than waiting for the sync the earlier tests took away (status at the failure:
`fram_after_failure_rerun_test_ntp_connected_socket_rejects_a_reply_from_an_unexpected_source.json`).
