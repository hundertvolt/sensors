# MQTT PoC: bench handover

Written by session `session_01EkZFpqSuwHuhRKfojd3CiE` (a cloud session with no route to the bench) for the
session that runs on the bench Pi4 after the owner clones this branch there. A per-effort file, deleted once
its results are migrated (README.md's handover rule).

**Read this whole file before doing anything.** It assumes nothing from the conversation that produced the
branch: sections 1 and 2 are the context, sections 3 to 8 the run, section 9 what follows it. CLAUDE.md
loads on its own and stays the authority; where this file restates a rule, CLAUDE.md wins.

---

## 1. Context

### 1.1 The project, as far as this run needs it

- Networked sensor stations on a Raspberry Pi Pico W (RP2040 + CYW43 WiFi), MicroPython v1.29.0. The
  firmware is `src/` (asyncio services and drivers) plus the vendored `ext/microdot.py` web framework,
  frozen into the image. Each device's top-level module (`sensortask_<device>.py`) is generated at build
  time by `buildgen/` from `devices/<device>.toml`; it is never committed.
- **`dev` is the one board on this bench** and the only image ever flashed here. `wozi` and the other
  devices are tested only through the host tiers (CLAUDE.md).
- Every module logs errors into a FRAM-backed history, read over `GET /status` (`errcount`). It survives a
  reboot and is the one diagnostic a reset does not erase; clearing it (`PUT /status {"ResetErrors": true}`)
  is irreversible.
- **Test levels** (SPECIFICATION.md E.6.1):
  - L0, host checks (`tests_scripts/`, pytest; `tests_js/`, vitest);
  - L1, unit tests under the real MicroPython Unix port (`tests/`);
  - L2, the digital twin: the generated system on the Unix port with fake chips (`scripts/run_digital_twin_ci.sh <device>`);
  - L3, flash: the real board over USB (`tests_hardware/flash/`);
  - L4, bench: the board plus this Pi4's WiFi (`tests_hardware/bench/`).
  
  Each hardware runner runs every lower level first. Two GC stages: MicroPython's reactive default
  `gc.threshold(-1)` and the firmware's shipped `32768`; zero memory errors at both.
- **The bench Pi4**: `br0` bridges the wired `eth0` (the uplink) and a WiFi access point (`br0-wifi-ap`)
  the board joins as a station. `tests_hardware/bench_control.py` drives it: AP down/up, station kicks,
  scoped `iptables` faults, the role reversal where the Pi4's radio joins the board's own hotspot.

### 1.2 What this branch is

The MQTT client proof of concept. The owner's request (2026-10-07): "Adding MQTT capabilities to the
system, just as a driver / available service, not used at any place at that point, only a proof of
concept." "publishing and subscribing should both work, and it must be fully compatible to our framework."

The owner's answers that shape it (`mqtt_poc/RESEARCH.md` §8.0, 2026-10-07):

| Question | Answer |
|---|---|
| Which code? | "Own client (Recommended)" |
| Which devices, on by default? | "dev only, off (Recommended)" |
| TLS? | "Plain TCP (Recommended)" |
| Who pays the permanent TCP connection? | "Web connections 6->5" |
| Broker credentials? | "Optional, masked (Recommended)" |
| What may received messages do? | "They may trigger behaviours or contain values (e.g. external measurements)"; no flash writes from them |
| What does it publish? | "Also measurements JSON" |
| Which broker for tests? | "mosquitto in CI", installed as an "apt package (Recommended)" |
| May an MQTT loss trigger WiFi recovery? | "Never (Recommended)" |
| When does it merge? | "After audit closes" |

And on 2026-10-08:
- 'TLS is not needed as it all runs in a local network.'
- 'It should accept plain IP addresses anyway. But it must not block, ever.'
- `.local` broker names: 'Add it, bench-tested (Recommended)'.
- The unconfirmed-bytes cap: 'Cap at 2,000 B (Recommended)'.
- The bench run's scope and writes: section 1.5.

### 1.3 Where it stands

- **Branch** `claude/whole-project-audit-plan-followup`, draft PR hundertvolt/sensors#110. It is stacked on the
  whole-project audit branch `claude/whole-project-audit-plan` (PR hundertvolt/sensors#107) at its head
  `f5c8255` (U19, the REST layer). It merges only after the audit closes (owner, 2026-10-07: "After audit closes"), then retargets to
  `main`. Never merge it, rebase it, force-push it or push to another branch.
- **Verified on the host, not on hardware**:
  - lint and all three typecheck passes;
  - `scripts/test.sh` at both GC stages: 93 files, about 4,590 MicroPython tests, zero memory errors;
  - the full `tests_scripts/` tier: about 3,240 tests;
  - the `dev` twin suite at both stages, Run 12 included (the client against a real mosquitto: kill, stall,
    takeover, flood), 346 of 346 checks;
  - the website's settings matrix.
- **CI**: the last fully finished run before the U18 merge (on `51a5bd2`) was green on all 27 checks; the
  PR's checks show the current head.
- **Nothing has run on the board.** This session is the first.

### 1.4 The client in brief

`mqtt_poc/DESIGN.md` is the full design; SPECIFICATION.md Part A.11 its permanent form.

- **Files**:
  - `src/mqtt_codec.py`: MQTT 3.1.1 packets.
  - `src/asy_mqtt_client.py`: `MQTTClient`. A keeper task is the only writer; a reader task per connection;
    a publisher. QoS 0 and 1, clean session, every buffer allocated once.
  - `src/asy_dns_client.py` learned one-shot mDNS for `.local` names, for `NTPHost` too.
- **Never blocking**:
  - an IPv4 broker address is used as it is;
  - a name goes through the project's bounded, cooperative resolver, asking the DHCP-provided DNS server
    only (`DNSFallback` is NTP's own list);
  - the client never has more than 2,000 B written that no PINGRESP confirmed, its share of lwIP's TCP
    memory, so lwIP's 10 s write retry can never be what it hits.
- **Hotspot mode**: the client is off there (owner, 2026-10-08: 'Generally, when the device is in hotspot
  mode, the MQTT client is off.'): no socket, no DNS query, no log.
- **Recovery**: a dead transport is found by the PINGRESP deadline (15 s ping, 10 s deadline); reconnects
  back off 2 s doubling to 60 s and reset after a 30 s stable session. MQTT never touches WiFi.
- **Settings**, `PUT /networking`: `MQTTEnable` (default off), `MQTTHost`, `MQTTPort` (1883), `MQTTUser`,
  `MQTTPW` (masked), `MQTTClientId` (default the hostname, `SensorStationDev`), `MQTTPrefix` (`sensors`),
  `MQTTPubInterval` (60 s, 10 to 3600).
- **Status**, `GET /status` → `networking`: `MQTTState`, `MQTTConnected`, `MQTTBroker`, counters,
  `MQTTLastReason`, `MQTTLastRxTopic`.
- **Topics**, `<base>` = `<MQTTPrefix>/<MQTTClientId>`:
  - `<base>/status`: retained `online`, and `offline` as the will and before a reconfiguring DISCONNECT;
  - `<base>/measurements/<NAME>`: one JSON object per sensor;
  - `<base>/cmd/#`: inbound, counted.
- **Error log `MQTT`** (FRAM-backed, like `CFGMGR_MQTT`): E 115 `MQTT_DNS`, 116 `MQTT_CONNECT`, 117
  `MQTT_REFUSED`, 118 `MQTT_PROTOCOL`, 119 `MQTT_NO_PINGRESP`, 120 `MQTT_LOST`, 121 `MQTT_STALLED`,
  122 `MQTT_SUB_REFUSED`; W 82 `MQTT_SHORT_SESSIONS`.
- **What else changed on `dev`**:
  - `max_connections` 6 → 5;
  - FRAM chunks `MQTT` and `CFGMGR_MQTT` ahead of `WEBSERVER`'s;
  - `PUT /networking` is now the largest request body, 1,318 B;
  - `mosquitto` joined the toolchain's apt packages, and `env --tier bench` installs `avahi-daemon`.

### 1.5 Why the run is scoped, and what it covers

The owner, 2026-10-08:
- "set up the tests in such way that you only test MQTT (and whatever is affected by your changes) on the
  bench. you shall not run the whole bench at this time (will happen lateron when mqtt as such is running)"
- "it makes absolutely no sense globally enable persistence writes, as writing the scd30 for mqtt tests is
  nonsense, so scope it correctly"
- "include the ntp tests too, allow networking/ntp"
- "include the hotspot role reversal too"

What that became on this branch:
- **Write permission per settings group.** Each `@pytest.mark.persistence_write(...)` names the groups its
  write lands in (`networking/mqtt`, `sensors/SCD30`, ...). `--allow-persistence-writes-to GROUP` runs only
  the writers whose every group is given. The global `--allow-persistence-writes` stays for the later full
  run, and the runner refuses it alongside a scope.
- **A run scope.** `scripts/run_bench_hardware_suite.sh --scope mqtt` runs the lower levels, then only what
  `tests_hardware/run_scopes.py` lists, each entry with the reason the branch reaches it. That is 3 flash
  tests and 66 bench tests (section 5). Its owned writes are `networking/identity`, `networking/mqtt`,
  `networking/ntp` and `notification/autoConfig`; nothing in it writes the SCD30.
- **Not in this run**, left for the full bench later: the bus-hazard and sensor push tests, every SCD30
  write, every soak.

### 1.6 Decided on the owner's behalf, for review (agent, 2026-10-08)

`mqtt_poc/DESIGN.md` §13 holds all twelve. The ones this run touches:
- The first measurement round follows each CONNACK.
- A settings change or switching the client off publishes a retained `offline` first.
- `MQTTHost` takes `NTPHost`'s host-name shape at PUT and at use; empty is the special "no broker, the
  client off".
- A passing scoped run is reported `NOT CLEAN` (exit 4), as `--skip-lower-levels` is, so it never stands in
  for a full L3/L4 pass.
- The broker name is asked of the DHCP-provided DNS server only, never NTP's `DNSFallback` list.

### 1.7 Known failures that are not this branch's

**In the lower levels and CI.** All three are in code this branch does not touch (the UART protocol and
the CI toolchain step, from the audit's U17 and U16), and each is commented on PR hundertvolt/sensors#110:

1. `tests/test_uart_comm_hazard.py::test_cancelling_a_set_at_every_await_leaves_both_ends_consistent_crc16`
   failed once in CI's coverage job ("no recovery within two transactions after step 2"). The audit's U18
   fix (`cfd92e4`, merged here) root-caused it (the sweep's CRC16 pair ran on a 30 ms budget instead of
   SPECIFICATION.md J.7's 240 ms) and moved the sweeps to `tests/test_uart_comm_cancel_sweep.py`.
2. `tests/test_asy_uart_driver.py::test_two_concurrent_cancellers_both_return` failed once locally at
   `gc.threshold(32768)` on a loaded machine: the second canceller returned `False`. It is a race in the
   test.
3. CI's `firmware-build-verify (wozi)` hit its job limit while `apt-get install` hung.

The Pi4 is slower than the machines these ran on, so 1 or 2 may fail in the lower levels here. Section 6
says what to do.

**On the bench, from the audit's U19 (`f5c8255`, merged here).** U19's web server writes two new warnings
to the persisted WEBSERVER log: W60 `HTTP_REFUSED` for a connection refused at the ceiling, and W61
`HTTP_BAD_HEAD` for a refused request head. Each also counts in `/status`'s `HTTPDropped`. Four scoped
bench tests were written before that, and each still ends by asserting an empty WEBSERVER log:

4. `test_network_resilience.py::test_connections_at_and_above_the_real_socket_limit_degrade_cleanly`: it
   opens one connection past the ceiling on purpose (W60).
5. `test_network_resilience.py::test_the_board_holds_exactly_the_connection_ceiling_this_tree_configures`:
   `discover_max_connections()` holds connections until one is refused (W60).
6. `test_network_resilience.py::test_concurrent_mixed_body_sizes_are_never_answered_with_the_wrong_status`:
   its storm is meant to go past the ceiling (W60).
7. `test_hotspot_role_reversal.py`, lines 394-396: "NOT A REAL HTTP REQUEST" is now refused (W61). This
   one is the audit's open finding OF-101, which its U26 fixes before any L4 run; the audit's scan does not
   name 4 to 6.

These tests are the audit's, so this branch leaves them as they are. A failure is one of these known items
only if all of the following hold:
- it fails at that WEBSERVER-log check;
- every earlier assertion in the test passed;
- the log holds only W60 (4 to 6) or W61 (7) entries, and `HTTPDropped` is at least 1.

Record such a failure as known, quoting the log. Edit nothing in those tests, and report the run NOT CLEAN
naming them. Any other WEBSERVER code, or an earlier assertion failing, is a real failure (section 6).

---

## 2. Rules for this session

CLAUDE.md is the authority; these are the rules this run meets.

- **The owner's go-ahead, given in this session's own conversation**, before any `mpremote`, `picotool`,
  `nmcli`, `iw`, `iptables` or `tests_hardware/` runner. A go-ahead to an earlier session does not carry over.
- **FRAM logs before anything clears them**, and know what ran against the board before reading them as
  evidence: a flash-tier script builds its own FRAM manager over the chip.
- **Only `dev` is flashed**, once per session.
- **Only the scoped writes**: `--allow-persistence-writes-to=networking/identity,networking/mqtt,networking/ntp,notification/autoConfig`.
  Leave out `--allow-persistence-writes`, `--allow-scd30-extra-write` and `--allow-flash-cycle`.
- **No credential in the repository**: the scrub in section 7.
- **A failure is root-caused, never written off as a flake**; no test is skipped, disabled or edited to pass.
- **Decision records**: a decision written down names its actor and date, and an owner decision quotes the
  owner. An unforeseen decision during the run goes to the owner in this session, who is at the bench.
- **Git**: commit and push to `claude/whole-project-audit-plan-followup` only. Never merge, rebase or
  force-push, and never mark the PR ready.
- **Never touch** the legacy tree (`legacy/`) or the vendored `ext/`.

---

## 3. Before anything touches the board

- **The session's own path to the Pi4 has to be the wired uplink, not the bench WiFi.** Two parts of the
  run take the bench AP (`br0-wifi-ap`, a `br0` slave) down: the MQTT AP-outage test, and the hotspot role
  reversal, where the Pi4's radio leaves its AP role to join the board's own hotspot and comes back.
  `br0` and `br0-eth0` stay up throughout. Check with `ip route get 1.1.1.1` that the route leaves through
  `br0` over `eth0`. If this session reaches the Pi4 any other way, stop: CLAUDE.md's dead-man's-switch
  rule (SPECIFICATION.md B.13) then applies, and the owner decides.
- **What the `iptables` rules match.** Every rule is temporary and removed in a `finally`. None touches
  TCP beyond the broker port, so this session's connection stays up.
  - The MQTT tests match the board's address and port 18883.
  - The NTP and DNS tests drop UDP 123 (the Pi4's own NTP included, for the outage) or redirect forwarded
    UDP 53/123 to a local responder.
- **Shared prerequisite writes still happen**, unmarked (owner's rule, `tests_hardware/README.md`):
  - the MQTT module enables the client once and switches it off at the end;
  - the hotspot module clears the board's SSID to force hotspot mode and restores it when it ends;
  - if the board cannot rejoin the bench AP, `dut_ip` pushes the bench SSID and password to it.
- **The hotspot module's stage 6 can deactivate the board's WLAN until a power cycle.** By then the board
  has run its hotspot since stage 0, so a failed credential handoff ends in a terminal state, not a
  fallback. The module's fixture recovers with a hard reset; `tests_hardware/README.md` ("A
  permanent-WLAN-deactivation risk") has the account. Do not interrupt the run inside that module. If it
  was interrupted anyway, the next run's `dut_ip` recovery joins the board's hotspot and pushes the bench
  credentials back.
- **Read first in `tests_hardware/README.md`**: Prerequisites, Running, "The MQTT client on the bench",
  "Persistence-write gating", and the stage-6 finding.

## 4. Preparation, in this order

1. **Check out the branch** (the owner's clone): `git fetch origin claude/whole-project-audit-plan-followup`
   and check it out. Create the results directory, named by today's date and the commit
   (`git rev-parse --short HEAD`): `mqtt_poc/bench_results/<YYYY-MM-DD>_<commit>/` (section 7).
2. **Provision the host**: `uv run toolchain/setup_toolchain.py env --tier bench`. It installs `mosquitto`
   and `avahi-daemon` when missing. Check `systemctl is-active avahi-daemon`: the `.local` test needs the
   Pi4 to answer for its own host name. The Debian package also starts a system mosquitto on port 1883,
   which no test uses (they start their own on 18883).
3. **Save the FRAM-backed logs from the image running now, before the flash.**
   - Why before: the new image puts the `MQTT` chunks ahead of `WEBSERVER`'s, so `WEBSERVER`'s old chunk
     is no longer found after the flash.
   - Find the board's address with `ip neigh show dev br0`, or the router's lease for `SensorStationDev`.
   - Save `GET /status` and `GET /system` (its `build` group names the running image) as
     `fram_before_flash.json` and `system_before_flash.json` in the results directory.
4. **Build and flash** the branch's `dev` image, the session's one flash (SPECIFICATION.md E.6.3).
   - `uv run scripts/build_firmware.py dev` writes `build/firmware-dev.uf2`.
   - Load it with `sudo picotool load -x -v build/firmware-dev.uf2` from a USB-capable picotool
     (`tests_hardware/README.md`, Prerequisites item 3).
5. **Save the first boot**: once the board serves again, save `GET /status` and `GET /system` as
   `fram_after_flash.json` and `system_after_flash.json`. The client is off, so `MQTTState` reads
   `disabled`, and `build.BuildDate` is today's.

## 5. The run

```bash
scripts/run_bench_hardware_suite.sh --scope mqtt \
    --allow-persistence-writes-to=networking/identity,networking/mqtt,networking/ntp,notification/autoConfig \
    2>&1 | tee "$HOME/mqtt_bench_console.log"; echo "runner exit ${PIPESTATUS[0]}"
```

**The lower levels run first** and touch no board: `scripts/test.sh` at both GC stages, `npm test`, and the
twin suite for every device. On the Pi4 this likely takes hours (an estimate). A failure there stops the run
before the board (section 6).

**The flash step: 3 tests.**
- The FRAM chunk layout after a full system build, which now holds the two MQTT chunks.
- The full-build heap headroom, with the client's buffers resident.
- The `env --tier flash` rerun, about 8 minutes, since `mosquitto` joined the apt packages.

**The bench step: 66 tests**, in the order `tests_hardware/run_scopes.py` lists them. The durations below are
estimates.

- **The client** (`tests_hardware/bench/test_mqtt_broker_faults.py`, roughly 20 to 30 minutes). It starts
  its own mosquitto on the Pi4's `br0` address, port 18883, and enables the client over REST. In order:
  - connect and `online`;
  - strict-JSON measurements per sensor, then an inbound command;
  - broker SIGKILL and restart, a SIGSTOP stall, silent path loss, a reset path;
  - a client-id takeover;
  - a 3000-message QoS 0 flood, with REST timed under it, and a 500-message QoS 1 burst;
  - the broker found by the Pi4's own `.local` name (it writes `MQTTHost` twice);
  - an oversized message;
  - a no-task-ended checkpoint;
  - an AP outage, then a hard reset;
  - the faults again under `device_scripts/mqtt_at_default_gc.py` at `gc.threshold(-1)`, a 7-minute window;
  - switching the client off, which has to publish a retained `offline`.
- **NTP and the resolver**:
  - NTP sync and DNS resolution over real UDP;
  - garbage DNS and NTP answers, an unreachable NTP server, a reply from an unexpected source;
  - the NTP retry after a transient outage, with and without API load;
  - an unresolvable `NTPHost` set over REST.
  
  Three of these write `NTPHost`: one sets an unresolvable name and restores it, two send the current one back.
- **The connection ceiling and body cap**:
  - the ceiling held exactly, and degrading cleanly at and above it;
  - a full ceiling served complete bodies;
  - a page load under contention;
  - mixed body sizes under concurrency;
  - the largest body;
  - the concurrent burst.
- **Heap with the client resident**: at a full ceiling, at the reactive gc default, under the hammer load.
- **Boot and website**: cold boot to the first response, reboot over REST, the website being dev's own.
- **The hotspot role reversal** (last, roughly 10 to 15 minutes): the board's hotspot, DHCP, captive DNS,
  every GET endpoint's shape over it (`/networking` and `/status` now carry the MQTT fields), a
  representative settings round trip, invalid and then the real credentials (stage 6), and the flip back.

**The result.** A passing scoped run ends `Result: NOT CLEAN (scope mqtt: ...)` with exit code 4: everything
that ran passed, but the rest of both tiers did not run. Exit 1 is a failure. One test is an expected skip:
`test_spoofed_off_subnet_source_address_is_ignored` needs an off-subnet host the bench lacks (owner,
2026-09-26).

## 6. When something fails

- **A lower level fails.** No board was touched. Rerun only the failing file once, exactly as
  `scripts/test.sh` runs it:

  ```bash
  MP="${PICO_TOOLCHAIN_DIR:-$HOME/pico-toolchain}/micropython/ports/unix/build-standard/micropython"
  export TZ=UTC MICROPYPATH="build/generated_src:src:tests:frozen_modules:.frozen"
  "$MP" -X heapsize=16M tests/<file>.py                                    # gc.threshold(-1)
  "$MP" -X heapsize=16M tests/_threshold_runner.py tests/<file>.py 32768   # the shipped threshold
  ```

  Record the output in the results either way. If it is one of section 1.7's known items, or elsewhere in
  code this branch does not touch, ask the owner whether to go on with `--skip-lower-levels`. That run is
  reported NOT CLEAN with both reasons named. Never go on without asking.
- **A hardware test fails.**
  0. If it is one of section 1.7's bench items (4 to 7), check that item's signature. If it matches, save
     the FRAM logs (step 2) and record it as known. Otherwise go on with step 1.
  1. Keep the evidence: the run's archive under `build/archive/` and the console log.
  2. Read the FRAM logs (`GET /status` `errcount`) before anything resets them; the next test's setup
     usually does. Save them into the results as `fram_after_failure_<test>.json`.
  3. Root-cause it against the code and the log. A fix goes on this branch through the same gates as any
     change:
     - lint and typecheck;
     - `scripts/test.sh` at both GC stages;
     - `scripts/run_digital_twin_ci.sh dev`;
     - a test that fails without the fix.
  4. Then rerun that part of the scope: `uv run pytest <node id>` with the same
     `--allow-persistence-writes-to=...`, then the whole scope again before reporting.
  5. If the cause is unclear or the fix is a design change, stop and bring it to the owner with the
     evidence.
- **The board stops answering after a reset.** The tests already recover from this once themselves (a
  station kick, then one hard reset: the bench's documented CYW43 behaviour) and note it in the run record
  as a pass with recovery. A second time in a row is a finding.

## 7. Where the results go

One directory per run, committed on this branch: `mqtt_poc/bench_results/<YYYY-MM-DD>_<commit>/`.

| File | What |
|---|---|
| `README.md` | date, commit, image (`system_after_flash.json`'s `build`), host (`uname -a`, OS), the exact command and its exit code, both summary blocks pasted, every rerun with its reason, anything abnormal |
| `fram_before_flash.json`, `system_before_flash.json` | the old image's logs and identity (section 4, item 3) |
| `fram_after_flash.json`, `system_after_flash.json` | the new image's first boot (section 4, item 5) |
| `fram_after_failure_<test>.json` | only when a test failed (section 6) |
| `flash_step/` | `pytest.log` and `run_record.json` from `build/archive/run_bench_hardware_suite_scope_mqtt_flash_step/<timestamp>/` |
| `bench_step/` | the same from `build/archive/run_bench_hardware_suite_scope_mqtt/<timestamp>/` |
| `lower_levels.txt` | every summary block of the console log: `awk '/^== Summary: /,/^Exit code:/' "$HOME/mqtt_bench_console.log"` |
| `console.log.gz` | the whole console log, compressed after the scrub |
| `mosquitto/` | the broker logs the module names (`[HW] mosquitto log: ...`), only when a test failed |
| `measurements.md` | section 8's table, filled in |

**Scrub before committing.** No credential goes into the repository.
1. Put the bench AP's key in a variable: `psk="$(sudo nmcli --show-secrets --escape no -g
   802-11-wireless-security.psk connection show br0-wifi-ap)"`.
2. `grep -rlF -- "$psk" <the results directory> "$HOME/mqtt_bench_console.log"` must print nothing.
3. Redact any hit as `<redacted>` and check again. The board's own hotspot password in `src/` is a known
   one CLAUDE.md records, and needs no scrub.
4. Then compress the console log into the directory.

**Commit and report.**
- Commit as `MQTT PoC: bench results <date> on <commit>`, then push.
- Comment on PR hundertvolt/sensors#110 with the two summary blocks and a link to the directory.
- If this session has no GitHub access, leave the comment text in the results `README.md` for the owner.

## 8. What to measure

The tests write each value into the run record as a `result_note`: in `bench_step/run_record.json`, and in
the summary block's notes. Each settles a SPECIFICATION.md Part N row that still reads "measurement owed".

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

Record the heap tests' notes beside them (the connection wall, the serving sweep, the hammer load): they are
the first figures with the client resident. The bench session records; it does not retune.

## 9. After the run

- **Part N rows**: each value from section 8 moves its row from "estimated" to the measured figure, naming
  the results commit so the evidence stays reachable once `mqtt_poc/` is deleted. A changed value changes
  its `@tunable` tag and its row in the same commit (CLAUDE.md). A session without hardware can do this from
  the committed results.
- **Statuses**: DESIGN.md §11.1 and BACKLOG.md's "Real-hardware work still owed" entry state the run's
  outcome.
- **This file and `mqtt_poc/`** are deleted once their outcomes have migrated, when the PoC merges after the
  audit.

## 10. File map

| What | Where |
|---|---|
| The design, the research, the prototype evidence | `mqtt_poc/DESIGN.md`, `mqtt_poc/RESEARCH.md`, `mqtt_poc/prototype/RESULTS.md` |
| The client, codec, resolver | `src/asy_mqtt_client.py`, `src/mqtt_codec.py`, `src/asy_dns_client.py` |
| The bench device | `devices/dev.toml` (the `mqtt` instance, `max_connections`) |
| The MQTT bench module, its device script, the host broker helper | `tests_hardware/bench/test_mqtt_broker_faults.py`, `tests_hardware/device_scripts/mqtt_at_default_gc.py`, `tests_hardware/mqtt_probe.py` |
| The scope and the write groups | `tests_hardware/run_scopes.py`, `tests_hardware/persistence_groups.py`, `tests_hardware/conftest.py` |
| The runner | `scripts/run_bench_hardware_suite.sh` (`--scope`) |
| The twin's MQTT run | `scripts/_digital_twin_ci_suite.py` (Run 12) |
| The bench tier's reference | `tests_hardware/README.md` |
| The rules | `CLAUDE.md`; SPECIFICATION.md Parts A.11, E.6, N |
