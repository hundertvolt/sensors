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

### Observation: NTP's own recovery after the block (`observations/ntp_recovery.json`)

A read-only probe started right after attempt 5 ended (the last test, the unreachable server, leaves NTP
unsynced): `GET /status` every 5 s plus the board's console, read passively with host timestamps. The board
resynced by itself **29.8 s after the probe started** (`/status` showed it at the next poll, 34.7 s); the probe
started after the test's teardown, so this is not a time from the unblock. From the timestamped console, for
the twin: NTP's check tick fires every 10.0 s (9.79 → 19.79 → 29.79 s), the resync is triggered on a tick
(`NTP resync triggered.` → `NTP sync starting.` 10 ms later), and the NTP exchange takes **105 ms**
(`sync starting` → `Received NTP time`); the WiFi service logs its established link every 5.0 s.

### Observation: the client's steady state (`observations/mqtt_steady_state/`)

A 1,060 s run with only `networking/mqtt` written: MQTT off for 120 s, on at the 60 s interval for 600 s, at
the 10 s minimum for 300 s, then off; `GET /status` every 5 s throughout, the console read passively with host
timestamps (`console.txt.gz`), mosquitto 2.0.21 on the bench Pi4 (`broker/`), and an observer subscribed to
`sensors/SensorStationDev/#`. For the twin:

- **Enable**: from the PUT's `Writing config via cfgmgr.` line, `Connected` on the console in 108 ms and
  `online` at the observer in 220 ms; the first round 1.05 s after `online` (the publisher's 1 s step);
  `MQTTConnected` seen by REST 1.72 s after the PUT returned (0.5 s polling).
- **A round**: SCD30, SGP40, BMP3XX, ISL29125 in that order, all four within 46 ms (max 52 ms). Payloads:
  SCD30 143–151 B, SGP40 58–59 B, BMP3XX 77–79 B, ISL29125 239–247 B (largest of the 384 B slot); status 6/7 B.
- **Interval**: measured between rounds at the observer, **60.49 s mean (60.00–61.08) at 60 s** and **10.56 s
  mean (10.05–11.00) at 10 s**. A round fires at the first 1 s publisher step at or after the interval, measured
  from the last round's start, so the expected overshoot is about half a step.
- **Interval change**: reconnects, as designed (`MQTTLastReason` `reconfigured`, one teardown): `offline`
  published, `Reconnecting with new settings.` → `Connected` in 150 ms, `online` at the observer 1.03 s after
  `offline`, the first 10 s round 0.16 s after that.
- **Disable**: `offline` published and a clean DISCONNECT (broker: `disconnected`, no will); the retained
  `offline` is what a later subscriber gets.
- **While disabled**: the keeper rereads its three settings groups every 60.0 s (`mqtt.idle_recheck_ms`;
  console 11.4 → 71.4 s, then 1089.8 → 1149.8 s).
- **Counters**: 158 messages sent over 2 connects (1 status + 10 rounds × 4 in the 60 s phase; 1 status +
  29 rounds × 4 in the 10 s phase), 0 ping timeouts, 0 short sessions, 0 dropped either way; the broker kept
  the board's 60 s keepalive session for its whole 605 s and 301 s.
- **REST cost**: none measurable. `GET /status` median/p90/max: off 1.561/1.606/1.652 s, on at 60 s
  1.561/1.637/1.730 s, on at 10 s 1.526/1.608/1.664 s, off again 1.537/1.575/1.658 s; 0 failures in 210.
- **Console and logs**: no error, warning or memory line in 1,170 s. The FRAM logs show nonzero counters only
  for NTP (3, last entry `E` 71) and SGP40 (2, `W` 33 and `W` 35). The run did not snapshot them beforehand,
  so this sets no baseline; the attempt 4/5 NTP tests are where NTP's come from. MQTT and CFGMGR_MQTT: 0.

**A bench-helper defect this run found, not a board one.** The observer was dropped by mosquitto 16 times
("exceeded timeout", every 30–60 s), and each reconnect replayed the retained `online`. Two rounds of three
sensors were lost to it (SCD30's message of each arrived before the drop). The board's own counters show every
round was sent. Cause: `Probe._read_exact()` kept waiting through the 1 s read timeout, so `_run()` sent its
PINGREQ only after some packet arrived, and a probe idle for 1.5 × its 20 s keepalive was dropped. Fixed with
`tests_scripts/test_mqtt_probe.py`, whose idle-ping test failed before the fix. The bench tests passed
regardless, and their observers are mostly busy, but a quiet wait longer than 30 s could have lost messages.

### Attempt 6: the five heap tests rerun with `-s` (`heap_rerun_step/`)

Run to keep the figures attempt 4 discarded (owner, 2026-10-08: "measure and push"); no write group, MQTT
resident but disabled, as in attempt 4. The FRAM logs were read first (`status_before.json`: NTP 3, SGP40 2),
since the hammer test resets them. **4 passed, 1 failed, and the failure is a checkout/image skew, not the
board's.** `test_serving_sweep_at_the_reactive_default` stopped at `ImportError: can't import name
_StaticRoutes`: this checkout carries U19 (`f5c82557`), whose `serving_at_default_gc.py` imports a class the
`51a5bd2d` image does not have. `allocation_need_per_source.py` changed in U19 too, so both serving-heap tests
were rerun from a `51a5bd2d` worktree with `-s`: **2 passed** (`worktree_51a5bd2d/console.log.gz`). The
lesson for every later bench step: device scripts must come from the image's own commit.

Figures, the first kept with the client resident (no earlier run kept any, so no pre-MQTT baseline exists):

- **Full ceiling held** (`test_heap_at_peak_while_a_full_ceiling_is_held`): ceiling 5, held 1–5, at the ceiling
  in 115 of 142 samples. After boot free 36,960 B, largest free run 33,472 B, 16 placeable 2,048 B blocks; at
  peak (worst of 69 samples) largest free run 21,440 B, 12 slots against the 5 needed.
- **Connection wall**: the board admitted 5 simultaneous connections against its configured 5.
- **Serving sweep at `gc.threshold(-1)`** (from the worktree): 0 allocation failures; N=4: 48 of 48 answered;
  N=6 over the ceiling of 5: 60 answered, 12 refused. Free before load 55,248–63,104 B (largest run
  5,696–13,488 B); **under load down to free 1,152 B with a largest run of 912 B** (`load13`), the tightest heap
  figure this session produced; after load 61,776–61,840 B (largest run 4,288–5,776 B).
- **Allocation need per source** (51 probes, both runs): the largest need is 320 B (`route:/status`,
  `route:/`), then 256 B (`/measurements`, `/sensors`, `status:networking`); `/status` churns 51,984–53,984 B per
  call, `/` 22,352 B, `/sensors` 22,304 B. The errcount probes' need moved by one 16 B rung (80/128 B vs 112 B)
  between the two runs with the same probe code, so a single reading of that size is ±16 B.
- **Hammer** (`test_real_hardware_survives_max_speed_hammer_load_without_memoryerror_or_reboot`): passed; it
  prints only the error logs it read before reset, so it keeps no load figure even with `-s`.

### The twin beside the board (`observations/twin_dev_mqtt_timing/`)

The dev twin (HEAD's src, Unix port, `gc.threshold(32768)` as the firmware boots), a real mosquitto on
loopback, the same probe, polled at 0.25 s; driven by `observations/method/twin_mqtt_timing.py` (372 s, zero
memory markers, clean exit). The MQTT src between `51a5bd2d` and HEAD changed only its host-name check, a
warning code and a logging argument (U18/U19 merges), so the timing paths compared are the same code. The
board's bench figures were polled at 1 s, with each `GET /status` taking about 1.5 s on the board, so their
resolution is about 2.5 s.

| Quantity | Board | Twin | Reproduced? |
|---|---|---|---|
| Round order and spread | SCD30, SGP40, BMP3XX, ISL29125; 46 ms | same order; 41–44 ms | yes |
| Interval at 10 s | 10.56 s mean (10.05–11.00) | 10.01 s mean (9.89–10.09) | **no**: the board overshoots by up to one 1 s publisher step, the twin not at all |
| Interval at 20 s / 60 s | 60.49 s mean (60.00–61.08) | 20.02 s mean (19.97–20.05) | the same gap: no overshoot in the twin |
| Interval change | reconnect 150 ms (console), `online` 1.03 s after `offline` | `online` 120 ms after `offline` | the reconnect yes; the board's late `online` at the observer no |
| Broker kill, 5 s outage | reconnected 4.2 s after the restart | 2.3 s, 4.2 s | yes, within the backoff's range |
| Stall detection | 21.0 s (path loss 21.5 s) | 20.7, 21.4, 21.5 s | yes; both sample one phase of the ping schedule, see below |
| Reconnect after a stall | 8.7 s after the resume | 16.2, 32.0, 60.3 s (backoff grown over three stalls) | not comparable: the twin repeated the fault, the board did not |
| Connect after enable | 1.72 s (WiFi already up) | 17.2 s (the same PUT set the SSID, so WiFi joined first) | not comparable as run |
| Payload sizes | SCD30 143–151, SGP40 58–59, BMP3XX 77–79, ISL29125 239–247 B | 177–195, 51–59, 95–104, 274–285 B | no: the twin's fake readings carry more digits, so its payloads are the larger, conservative for the 384 B slot |

What this tells the twin's further development:

- **The twin runs at host speed, so it does not show the board's event-loop latency.** The board's rounds land
  up to 1 s late. The likeliest cause is the 1 s publisher step waking late while the loop is busy (here a
  `GET /status` every 5 s, about 1.5 s of board time each); the twin, its loop never busy that long, fires on
  the step. That cause is an agent hypothesis, unverified: a board run without the REST sampler would settle
  it. A twin that is to reproduce the board's timing needs a model of loop latency under load.
- **Stall detection is about 21 s in both, because both start the stall a few seconds after a connect.** The
  next PINGREQ then falls about 11–12 s later (15 s ping interval) and its 10 s response deadline ends the
  session. The bound is 10–25 s by phase; neither tier has measured the other phases yet.
- **Fake sensor payloads are larger than the real ones**, so a payload-size check in the twin over-estimates;
  the real figures above are the ones for `mqtt.out_payload_max`.
- **The fixed probe held its session for the whole twin run** (3 connects: the start and the two kills),
  where before the fix a quiet observer was dropped every 30–60 s.
