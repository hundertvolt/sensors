# MQTT PoC: bench handover

Written by session `session_01EkZFpqSuwHuhRKfojd3CiE` for the bench session; a per-effort file, deleted once
its results are migrated (README.md's handover rule).

The real-hardware run of the MQTT client proof of concept, for the session on the bench Pi4: what to test,
in which order, what to record, and where the results go. Nothing in it has run on hardware yet. Branch:
`claude/whole-project-audit-plan-followup` (draft PR hundertvolt/sensors#110). The design is
`mqtt_poc/DESIGN.md`; the bench tier's general reference is `tests_hardware/README.md`.

## 1. Before anything touches the board

- **The owner's go-ahead in this session's own conversation.** CLAUDE.md's hard rule: one given to another
  session does not carry over. Without it, stop here and ask.
- **This is a scoped run, not the whole bench** (owner, 2026-10-08: "you shall not run the whole bench at
  this time (will happen lateron when mqtt as such is running)"). The one command in section 3 is the run.
- **Writes are scoped to two groups** (owner, 2026-10-08: "it makes absolutely no sense globally enable
  persistence writes, as writing the scd30 for mqtt tests is nonsense, so scope it correctly"; "include the
  ntp tests too, allow networking/ntp"). Pass `--allow-persistence-writes-to=networking/mqtt,networking/ntp`.
  Leave out the global `--allow-persistence-writes` (the runner refuses it with a scope) and
  `--allow-scd30-extra-write`. Shared prerequisite writes stay unmarked and still happen (owner's rule,
  `tests_hardware/README.md`): the MQTT module enables the client once and switches it off at the end
  (`networking/mqtt`), and if the board cannot rejoin the bench AP, `dut_ip` pushes the bench SSID and
  password to it (`networking/identity`).
- **Only `dev` is flashed.** `wozi` and every other image stay off this bench (CLAUDE.md).
- **The session's own path to the Pi4 has to be the wired `br0`/`eth0`, not WiFi.** The MQTT AP-outage
  test takes the bench WiFi AP down and up (`BenchBridge.ap_down()`/`ap_up()`, the AP slave `br0-wifi-ap`
  only). Check with `ip route get 1.1.1.1` that the uplink is not the WiFi interface before starting.
  Nothing in the scope touches `br0` itself or `eth0`, so CLAUDE.md's dead-man's switch is not in play. The
  `iptables` rules are temporary and each is removed in a `finally`: the MQTT tests match the DUT's address
  and port 18883; the NTP and DNS tests drop UDP 123 (the Pi4's own NTP included, for the outage) or
  redirect forwarded UDP 53/123 to a local responder. None touches TCP, so the session's connection stays.
- **Not in this run, left for the full bench later:** the hotspot role reversal, the bus-hazard and sensor
  push tests, the SCD30 writes, every soak.

## 2. Preparation, in this order

1. Update the checkout: `git fetch origin claude/whole-project-audit-plan-followup`, check the branch out,
   and create the results directory, named by today's date and the commit (`git rev-parse --short HEAD`):
   `mqtt_poc/bench_results/<YYYY-MM-DD>_<commit>/` (section 4).
2. Provision the host: `uv run toolchain/setup_toolchain.py env --tier bench`. It installs `mosquitto` with
   the rest of `apt_packages` and `avahi-daemon` when missing. Check `avahi-daemon` is running
   (`systemctl is-active avahi-daemon`): the `.local` test needs the Pi4 answering for its own host name.
3. **Save the FRAM-backed error logs from the image now running, before the flash.** This branch adds the
   `MQTT` and `CFGMGR_MQTT` chunks ahead of `WEBSERVER`'s, so the new image no longer finds `WEBSERVER`'s
   old chunk, and the flash step's FRAM tests build their own graph over the chip (CLAUDE.md's FRAM rule).
   Find the board's address (`ip neigh show dev br0`, or the router's lease for `SensorStationDev`), then
   save `GET /status` and `GET /system` (its `build` group names the running image) into the results
   directory as `fram_before_flash.json` and `system_before_flash.json`. Before reading the logs as
   evidence, check what ran against this board last (`tests_hardware/README.md`).
4. Build and flash the branch's `dev` image, the session's one allowed flash (SPECIFICATION.md E.6.3):
   `uv run scripts/build_firmware.py dev` writes `build/firmware-dev.uf2`; load it with `sudo picotool load
   -x -v build/firmware-dev.uf2` from a USB-capable picotool (`tests_hardware/README.md`, Prerequisites
   item 3).
5. Once it serves again, save `GET /status` and `GET /system` of the first boot as `fram_after_flash.json`
   and `system_after_flash.json`. The client is off by default, so `MQTTState` reads `disabled`.

## 3. The run

```bash
scripts/run_bench_hardware_suite.sh --scope mqtt --allow-persistence-writes-to=networking/mqtt,networking/ntp \
    2>&1 | tee "$HOME/mqtt_bench_console.log"; echo "runner exit ${PIPESTATUS[0]}"
```

It runs every lower level first (`scripts/test.sh` at both GC stages, `npm test`, the twin CI for every
device), which is the longest part on the Pi4 and touches no board. A lower-level failure stops the run
before the board: that is a finding to report, never a reason to skip the levels. Then the flash step, then
the bench step, each on only what `tests_hardware/run_scopes.py` lists for `mqtt`:

**Flash step (3 tests)**: the FRAM chunk layout after a full system build, the full-build heap headroom, and
the `env --tier flash` rerun (`mosquitto` joined `apt_packages`).

**Bench step (41 tests)**:

- **The client** (`tests_hardware/bench/test_mqtt_broker_faults.py`, about 20 minutes, in this order):
  - connect, `online` and strict-JSON measurements per sensor, then an inbound command;
  - broker SIGKILL and restart, SIGSTOP stall, silent path loss, a reset path;
  - a client-id takeover;
  - a 3000-message QoS 0 flood, a 500-message QoS 1 burst;
  - the broker found by the Pi4's own `.local` name (one of the two `MQTTHost` writes);
  - an oversized message;
  - a no-task-ended checkpoint;
  - an AP outage, a hard reset;
  - the faults again at `gc.threshold(-1)`;
  - switching the client off, which must publish a retained `offline`.
- **NTP and the resolver**: NTP sync and DNS resolution over real UDP, a garbage DNS answer, an unreachable
  NTP server, a garbage NTP answer, a reply from an unexpected source, the NTP retry after a transient outage
  (with and without API load), and an unresolvable `NTPHost` set over REST. Three carry the
  `networking/ntp` permission: one sets an unresolvable `NTPHost` and restores it, two send the current one
  back to force a resync.
- **The connection ceiling and body cap** (dev's ceiling went 6 to 5, and `PUT /networking` is now the largest
  body at 1,176 B): the ceiling held exactly, at and above it, a full ceiling served complete bodies, a page
  load under contention, mixed body sizes under concurrency, the largest body, and the concurrent burst.
- **Heap with the client resident**: at a full ceiling, at the reactive gc default, under the hammer load.
- **Boot and website**: cold boot to the first response, reboot over REST, the website being dev's own.

A passing scoped run ends `Result: NOT CLEAN (scope mqtt: ...)` with exit code 4: everything that ran passed,
but the rest of both tiers did not run (agent, 2026-10-08, `mqtt_poc/DESIGN.md` §13). Exit 1 is a failure.
A failure is root-caused, never written off as a flake (CLAUDE.md); one rerun with `--skip-lower-levels` on
the same commit is the way to repeat the hardware steps once the lower levels have passed.

## 4. Where the results go

One directory per run, committed on this branch: `mqtt_poc/bench_results/<YYYY-MM-DD>_<commit>/`.

| File | What |
|---|---|
| `README.md` | date, commit, image (`system_after_flash.json`'s build), the exact command, both summary blocks pasted, every rerun, anything abnormal |
| `fram_before_flash.json`, `system_before_flash.json` | the old image's logs and identity (section 2, item 3) |
| `fram_after_flash.json`, `system_after_flash.json` | the new image's first boot (section 2, item 5) |
| `flash_step/` | `pytest.log` and `run_record.json` from `build/archive/run_bench_hardware_suite_scope_mqtt_flash_step/<timestamp>/` |
| `bench_step/` | the same from `build/archive/run_bench_hardware_suite_scope_mqtt/<timestamp>/` |
| `lower_levels.txt` | every `== Summary:` block of the console log: `awk '/^== Summary: /,/^Exit code:/' "$HOME/mqtt_bench_console.log"` |
| `console.log.gz` | the whole console log, compressed after the scrub below |
| `mosquitto/` | the broker logs the module names (`[HW] mosquitto log: ...`), only when a test failed |
| `measurements.md` | the table in section 5, filled in |

**Scrub before committing.** No credential goes into the repository (CLAUDE.md). With the bench AP's
pre-shared key in a variable (`psk="$(sudo nmcli --show-secrets --escape no -g 802-11-wireless-security.psk
connection show br0-wifi-ap)"`), `grep -rlF -- "$psk" <the results directory> "$HOME/mqtt_bench_console.log"`
prints nothing; redact any hit as `<redacted>` and rerun the check. Then compress the console log into the
directory, commit (`MQTT PoC: bench results <date> on <commit>`), push, and post the two summary blocks as a
comment on the PR.

## 5. What to measure

The tests write each value into the run record as a `result_note` (the `bench_step/run_record.json` notes,
also printed in the summary block). Each settles a Part N row that still reads "measurement owed":

| Test (in `test_mqtt_broker_faults.py`) | Note | Part N rows |
|---|---|---|
| `test_the_client_connects_and_announces_itself_online` | time to connected | `mqtt.connect_timeout_ms`, `mqtt.response_timeout_ms` |
| `test_every_sensor_publishes_strict_json_on_its_own_topic` | largest payload | `mqtt.out_payload_max` |
| `test_a_killed_broker_is_reconnected_after_its_restart` | reconnect after the restart | `mqtt.backoff_min_ms`, `l4.mqtt_connect_wait_s` |
| `test_a_stalled_broker_is_detected_by_the_pingresp_deadline` | detection, reconnect | `mqtt.ping_interval_ms`, `l4.mqtt_detect_bound_s` |
| `test_a_silent_path_loss_is_detected_and_recovered` | detection, reconnect | `mqtt.ping_interval_ms`, `l4.mqtt_detect_bound_s` |
| `test_a_duplicate_client_id_is_bounded_by_the_backoff` | retakes against the duplicate | `mqtt.stable_after_ms`, `mqtt.short_session_warn`, `l4.mqtt_takeover_max_connects` |
| `test_an_inbound_flood_leaves_rest_serving_and_the_session_up` | messages taken, `GET /status` latency | `l4.mqtt_flood_messages`, `l4.mqtt_rest_budget_s` |
| `test_an_inbound_qos1_burst_is_acknowledged_in_full` | burst time | `mqtt.qos1_retry_ms`, `l4.mqtt_detect_wait_s` |
| `test_the_broker_is_found_by_the_bench_hosts_local_name` | resolved address, connect time | none: the `.local` path itself |
| `test_an_ap_outage_pauses_the_client_and_it_returns_with_the_link` | reconnect, failed attempts | `l4.mqtt_ap_reconnect_timeout_s`, `l4.mqtt_ap_max_failed_attempts` |
| `test_a_reboot_reconnects_from_the_stored_settings` | connected after the reset | `l4.mqtt_reboot_wait_s` |
| `test_the_broker_faults_run_clean_at_micropythons_default_gc` | timeline, free heap minimum | `l4.mqtt_at_default_gc_window_s`, `l4.mqtt_default_gc_script_timeout_s` |

Record the heap tests' notes (connection wall, serving sweep, hammer) beside them: they are the first
figures with the client resident. Changing a tunable from these figures is follow-up work on this branch,
each value with its `@tunable` tag and Part N row in the same change (CLAUDE.md), from the stored evidence;
the bench session only records.
