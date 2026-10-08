# MQTT client — detailed design (2026-10-08)

**Temporary doc** of the MQTT PoC branch, like `RESEARCH.md` beside it. It turns the owner's answers
(`RESEARCH.md` §8.0) and the twin torture findings (`prototype/RESULTS.md`) into the shape the `src/`
client, its `dev` wiring and its tests take. Once the PoC lands, every rule here moves to its permanent
home (SPECIFICATION.md rows named in §12) and this file is deleted with the rest of `mqtt_poc/`.

**Go-ahead** (owner, 2026-10-08): "go ahead with the design, and prepare it for a real hardware session
on the bench tier, install mosquitto on the Pi4 and run all (or more) of your tests in real there". This
also settles the reading flagged in `RESEARCH.md` §8.0 row 8.10: development continues now, the merge
still waits for the audit to close.

**Where the bench run happens.** This session runs in a cloud container with no route to the bench Pi4
or the board (agent, 2026-10-08). Everything up to the bench run is done here; the run itself is a
session on the Pi4 with the owner's go-ahead given in that session (CLAUDE.md), following §11's runbook.

---

## 1. Shape at a glance

| Piece | File | Role |
|---|---|---|
| Codec | `src/mqtt_codec.py` | Pure MQTT 3.1.1 packet encode/decode into caller buffers, topic matching, the string-shape checks. No async, no logging, never raises on wire input. |
| Client | `src/asy_mqtt_client.py` → `MQTTClient(SensorReaderConfig)` | Config, the connection keeper, the per-connection reader, the outbound ring, inbound dispatch, the measurement publisher, status, logging. |
| Wiring | `buildgen/*`, `devices/dev.toml` | An optional singleton `[[instance]] driver = "mqtt"`, on `dev` only (owner, 8.2). |
| L1 | `tests/test_mqtt_codec.py`, `tests/test_asy_mqtt_client.py` | Codec against the specification's bytes; the client against an in-process scripted broker over real loopback sockets. |
| L2 | `scripts/_digital_twin_ci_suite.py` Run 12 | The generated `dev` twin against a real mosquitto, both GC stages, host-side driver (E.9). |
| L4 | `tests_hardware/bench/test_mqtt_broker_faults.py` + device script | The real board against a mosquitto on the bench Pi4, both GC stages, every fault the twin ran plus the ones only silicon has. |

The prototype in `prototype/` stays as the evidence for `RESULTS.md` and is not promoted; the `src/`
client is written fresh to the Part C/D bar, keeping the prototype's architecture (it passed the torture
run) and closing every finding in `RESULTS.md`.

## 2. Task and socket model

**Two tasks per connection, one owner per direction; neither waiter is ever cancelled alone** (RESEARCH.md
§4 fact 5: cancelling one waiter on a socket drops the socket's whole poll entry and strands the other).

- **Keeper** — `_connection_loop()`, started by `start_asy_connection()` and supervised. Never ends on
  a remote fault (C.7.2). Each round: wait until enabled and the link is up → resolve → connect →
  CONNECT/CONNACK → start the reader → serve → teardown → backoff. While serving it ticks every
  `mqtt.tick_ms` on `asyncio.sleep_ms()` (allocation-free) and owns every write, the ping schedule,
  QoS 1 retransmission, the link check and every deadline.
- **Reader** — `_reader_loop()`, created by the keeper after CONNACK, one per connection (a C.9 task-table
  row). It blocks on `Stream.readinto()` with no timeout, parses into the preallocated receive buffer,
  queues the PUBACK for inbound QoS 1 and dispatches. It never logs and never raises: its top records the
  reason in a field the keeper reads on its next tick, and the keeper persists it.
- **The cancellation rule.** Exactly two things cancel a socket waiter: the keeper's teardown (which
  cancels the reader, then closes the socket) and a `wait_for_ms()` timeout on a drain, which is itself
  a teardown reason handled in the same tick. Nothing cancels the reader on a live connection. A unit
  test pins it: a drain timeout always ends the connection. The teardown never awaits the cancelled
  reader: MicroPython cannot tell the reader's cancellation from the keeper's own, so an `except
  CancelledError` around that await swallowed a supervisor's cancel and left the keeper running (found
  by the unit tier, 2026-10-08). `cancel()` takes the reader out of the poll set at once, and a
  cancelled task's end is never reported, so nothing needs the await.
- **PUBACKs are queued, not written by the reader**: the keeper writes them on its next tick, so every
  write has one author and no PUBACK can land inside a running drain (which resets the stream's
  pending output when it finishes).
- **Measurement publisher** — `_publish_loop()`, started by `start_asy_publish()` and supervised. Right
  after each CONNACK and then every `MQTTPubInterval` seconds (read at connect, checked every
  `mqtt.pub_step_ms`) it reads each source's `get_dict_data()` and enqueues one QoS 0 message per
  module; it never touches the socket.
- **Socket ownership.** The keeper creates the socket itself (`socket.socket()`, `setblocking(False)`,
  `connect()` to the resolved IPv4 literal, EINPROGRESS accepted), wraps it in an asyncio `Stream`, and
  closes it with `wait_closed()` in a `finally` on every exit path (`Stream.close()` is a no-op).
  `asyncio.open_connection()` is never used: its `getaddrinfo()` and its untimed connect wait both
  leave a socket to the GC finaliser on a timeout (RESEARCH.md §4 fact 4). The CONNECT packet is
  written at once; a connecting socket refuses it with EAGAIN (`modlwip.c` `lwip_tcp_send()`, and
  the Unix port alike), so it waits in the stream's buffer and the drain that follows is the connect
  wait, bounded by `mqtt.connect_timeout_ms`.
- **Writes** are `Stream.write()` calls from the keeper's tick alone, synchronous, so packets never
  interleave; a partial socket write leaves the rest in the stream's `out_buf`, which the keeper
  drains under `mqtt.drain_timeout_ms`.
- **No lock of its own.** Every shared field is touched only between awaits. `wifi_mode_lock` is taken
  only around the `network_available_locked()` call and never across broker I/O; the DNS server is read
  before it (the NTP ordering).

## 3. Connection behaviour

### 3.1 Gating and link

- Disabled (`MQTTEnable` false, or an empty `MQTTHost`): the keeper waits on an event that `reconnect()`
  sets, re-checking the config every `mqtt.idle_recheck_ms`. No socket, no DNS, no log.
- Link: `network_available_locked()` false (link down, no IP, or hotspot mode) → wait, polling every
  `mqtt.link_poll_ms`; backoff does not grow. While serving, the link is re-checked once per
  `mqtt.link_poll_ms` when the lock is free; a link loss ends the connection without a log entry
  (WIFI logs its own) and without backoff.
- **MQTT never drives WiFi** (owner, 8.9): no call into `reconnect_wifi()`, the radio or a reset. A
  PINGRESP deadline missed while the link reports up is counted as `PingTimeouts` ("link up, transport
  dead") and nothing more.

### 3.2 Connect

- Resolve with `resolve_ipv4(host, (dns_server,), timeout_ms, tries)`; an IPv4 literal returns at once.
  Re-resolved on every attempt (the address may move).
- CONNECT: protocol level 4, clean session, keepalive `mqtt.keepalive_s`, client id `MQTTClientId`,
  will `<base>/status` = `offline`, QoS 1, retained; user name and password flags only when set.
- CONNACK within `mqtt.response_timeout_ms` of the connect completing; any return code other than 0 is
  a refusal (E `MQTT_REFUSED`, the code logged). The session-present flag is read and ignored (clean
  session), never treated as an error — the `mqtt_as` A4 defect.
- After CONNACK: SUBSCRIBE every filter at QoS 1, re-queue unacknowledged QoS 1 messages as new, drop
  queued QoS 0, then enqueue `online` (QoS 1, retained) on `<base>/status`.

### 3.3 Serving

- **Ping**: PINGREQ every `mqtt.ping_interval_ms` regardless of traffic; no PINGRESP within
  `mqtt.response_timeout_ms` → teardown (E `MQTT_NO_PINGRESP`). Worst-case dead-transport detection is
  their sum. lwIP has no TCP keepalive here, so this is the only detector (RESEARCH.md §4 fact 1).
- **QoS 1 out**: retransmitted with DUP after `mqtt.qos1_retry_ms`, given up after
  `mqtt.qos1_max_tries` (counted, never a teardown — the `mqtt_as` A9 self-inflicted reconnect).
- **Stalled broker**: the stream's pending output past `mqtt.max_out_backlog` bytes, or a drain not done
  within `mqtt.drain_timeout_ms` → teardown (E `MQTT_STALLED`). Small packets keep each `tcp_write()`
  small; the `ERR_MEM` 10 s stall (RESEARCH.md §4 fact 6) is closed only by the audit's U21 override.
- **Unconfirmed bytes** (§14 item 2): at most `mqtt.unconfirmed_max_bytes` written that no PINGRESP has
  confirmed, the connection's 2,000 B share of lwIP's `MEM_SIZE`. A PINGRESP confirms everything up to
  its PINGREQ (TCP is in order). A PUBLISH that would pass the cap waits in the ring and the next tick
  pings early; PUBACKs and PINGREQs are never held. MQTT then cannot be what exhausts `MEM_SIZE` and
  trips the `ERR_MEM` loop.
- **Inbound**: packets up to `mqtt.rx_buf_bytes` are parsed in place; a larger one is read and discarded
  in buffer-sized chunks (counted `RxDropped`, never allocated). A remaining length past four bytes, an
  unexpected packet type, a QoS 2 PUBLISH or a PUBLISH whose topic overruns it → teardown
  (E `MQTT_PROTOCOL`). SUBACK `0x80` → E `MQTT_SUB_REFUSED`, the connection stays.

### 3.4 Teardown and backoff

- Teardown order: record the reason → on a deliberate reconnect only, publish a retained `offline` on the
  old `<base>/status` and send DISCONNECT (so the broker drops the will, and the status still ends
  `offline`, a disabled client included) → cancel the reader, never awaited (§2) → `wait_closed()` →
  clear per-connection state.
- Backoff after a failed attempt or a lost connection: `mqtt.backoff_min_ms` doubling to
  `mqtt.backoff_max_ms`. **Reset only after a connection stayed up `mqtt.stable_after_ms`** (RESULTS.md
  finding 2: a reset on CONNACK lets a duplicate client id or a session-dropping broker loop at the
  minimum), or by `reconnect()`.
- **Short sessions** (finding 5): a connection the broker ends inside `mqtt.stable_after_ms` counts as
  short; `mqtt.short_session_warn` in a row log one W `MQTT_SHORT_SESSIONS` per episode ("possible
  duplicate client id"); a stable session ends the episode.

### 3.5 Reconfiguration

`reconnect()` is the settings group's `post_fct` (sync, like WiFi's): it sets a flag the keeper reads on
its next tick (retained `offline`, graceful DISCONNECT, teardown, config re-read, backoff reset) and wakes a
disabled keeper.

## 4. Public API

| Member | Shape |
|---|---|
| `publish(topic, payload, *, qos=0, retain=False) -> bool` | Never blocks, never raises on load. Copies the payload into a free ring slot; `False` (counted `TxDropped`) when disabled, disconnected for QoS 0, the payload too long, or the ring full. The topic object is referenced, not copied — callers pass long-lived strings or bytes. |
| `reconnect() -> None` | §3.5. |
| `get_link_status() -> dict` | The `MQTT*` status fields (§6.3), built with no await. |
| `get_data()` / `get_dict_data()` / `get_dict_cfg()` | C.4.2's contract; `MQTT(Connected, TS)`; `MQTTPW` masked. |
| `get_task_starters()` / `get_timer_starters()` | `[start_asy_connection, start_asy_publish]` / `[]`. |
| `get_error_counter()` / `reset_error_counter()` / `get_error_sources()` / `get_loggers()` | From `SensorReaderConfig`. |

**Consumers** (owner, 8.6) are constructor arguments, since nothing completes a module after
construction (A.7): `consumers=(MqttConsumer(topic_filter, callback), ...)`. Each filter is subscribed
besides the device's own `<base>/cmd/#`. The callback is synchronous —
`callback(topic: memoryview, payload: memoryview, retained: bool) -> None` — runs on the reader task, must
copy what it keeps (both views point into the receive buffer), must validate every value before use, must
be idempotent (a retained message is delivered again after each reconnect) and **must not write to
flash** (owner, 8.6 follow-up: "No flash writes (Recommended)"), so "every flash write comes through REST
PUT" stays true. A raising callback is caught, logged (shared `CALLBACK` errno 14) and counted; the
message is still acknowledged. `dev` wires no consumer; the unit tier proves the mechanism with a test
consumer. The device's own `cmd/#` messages are counted and their last topic shown in status (8.7 (a)).

## 5. Memory

All long-lived buffers are allocated once in `__init__` (construction runs once per boot, A.7), in one
pass, each a single `bytearray` with `memoryview` regions; an allocation failure there is the shared
`ALLOC` errno and leaves the client permanently disabled (status `State: "no memory"`), never a crash.

| Buffer | Bytes | Tunable |
|---|---|---|
| receive | 1,024 | `mqtt.rx_buf_bytes` |
| transmit | 640 | `mqtt.tx_buf_bytes` |
| outbound ring | 8 × 384 | `mqtt.out_slots`, `mqtt.out_payload_max` |
| last inbound topic | 64 | `mqtt.last_topic_bytes` |

About 5 KB plus the object, against the ~7.5–8 KB one HTTP connection holds at peak, which the
`max_connections` 6 → 5 step frees (owner, 8.4). Steady-state per-message allocation: the `readinto`
generator per inbound read, one `memoryview` slice per write, the measurement JSON text per module per
interval. Counters saturate at `COUNTER_CAP`. Nothing grows with uptime or traffic; the twin and bench
tiers check it at `gc.threshold(-1)` and `32768` with zero memory markers.

## 6. Configuration, REST and website

### 6.1 Schema (`config_MQTT.cfg`, persist-only, all in `/networking`)

| Key | Type | Default | Bounds | Rule at PUT and at use |
|---|---|---|---|---|
| `MQTTEnable` | bool | `false` | — | off by default (owner, 8.2) |
| `MQTTHost` | str | `""` | 0–253 | bytes ≤ 253 at PUT; at use, an IPv4 literal (no lookup), a DNS name, or a `.local` name asked by one mDNS query (§14 item 1), as `NTPHost` |
| `MQTTPort` | int | 1883 | 1–65535 | plain TCP only (owner, 8.3) |
| `MQTTUser` | str | `""` | 0–64 | bytes ≤ 64, no NUL |
| `MQTTPW` | str | `""` | 0–64 | bytes ≤ 64; masked on every GET (owner, 8.5) |
| `MQTTClientId` | str | `[device].hostname` | 1–23 | 1–23 bytes of letters, digits, `-` |
| `MQTTPrefix` | str | `"sensors"` | 1–64 | bytes ≤ 64; no `+`, `#`, NUL; no leading or trailing `/` |
| `MQTTPubInterval` | int | 60 | 10–3600 | seconds between measurement rounds |

A refused value answers `"Invalid"` with the shared `BAD_ARG` errno 21, as WiFi's radio fields do
(C.7.4). `MQTTHost`'s shape is checked at use only, as `NTPHost`'s is: the website has no host-name
shape to mirror a PUT check, and the live PUT matrix sends any in-range string to a shapeless field
(§13 item 8). A stored value that fails its shape at use keeps the client disabled with the shared
`STORED_DEFAULT` warning, never a failure streak. `MQTTEnable` exists because the web UI cannot set an
empty string (owner, 2026-08-22), so an empty host could never switch the client off again from the UI.
The client id default is `[device].hostname`, substituted the way WiFi substitutes its hostname default.

### 6.2 Settings group

`SettingsGroup(mqtt, (all eight keys), post_fct=mqtt.reconnect)` under `"networking"`, rendered as the
"MQTT Broker" group after NTP. The `/networking` body grows by the eight keys; the body-cap headroom pin
is updated and its margin read (I.6).

### 6.3 Status (`GET /status` → `networking`)

`MQTTState` (`disabled`, `waiting`, `connecting`, `connected`, `backoff`, `no memory`), `MQTTConnected`,
`MQTTBroker` (the resolved IP or `null`), `MQTTUptime` (s), `MQTTConnects`, `MQTTTeardowns`,
`MQTTLastReason`, `MQTTTxMsgs`, `MQTTTxDropped`, `MQTTRxMsgs`, `MQTTRxDropped`, `MQTTPingTimeouts`,
`MQTTShortSessions`, `MQTTLastRxTopic`. Added to the generated `_networking_status()` and the Networking
Status group only when the device carries the driver. The errcount group gains `MQTT` and
`CFGMGR_MQTT`.

## 7. Topic and payload contract

`<base>` = `<MQTTPrefix>/<MQTTClientId>`, e.g. `sensors/SensorStationDev`. Frozen at the release like the
REST API (owner, 8.7: one key scheme with `/measurements`).

| Topic | Direction | QoS | Retain | Payload |
|---|---|---|---|---|
| `<base>/status` | out | 1 | yes | `online` after each CONNACK; `offline` is the will, and is published before a reconfiguring DISCONNECT |
| `<base>/measurements/<NAME>` | out | 0 | no | the module's `/measurements` object as JSON, non-finite as `null` |
| `<base>/cmd/#` | in | 1 | — | counted and shown in status; no behaviour in the PoC |
| each consumer filter | in | 1 | — | the consumer's own contract |

`<NAME>` is the module's REST key (`SCD30`, `SGP40`, `BMP3XX`, `ISL29125` on `dev`). One message per module
keeps each packet small (RESEARCH.md §4 fact 6). Consumers read the retained `status`, so a burst of
`offline` wills after a stall (finding 4) is harmless.

## 8. Errors and warnings

New catalog owner `mqtt`, logger `MQTT`, bands E 115–124 and W 77–80:

| Code | Name | When |
|---|---|---|
| E 115 | `MQTT_DNS` | the broker name did not resolve |
| E 116 | `MQTT_CONNECT` | the TCP connect or CONNACK failed or timed out |
| E 117 | `MQTT_REFUSED` | CONNACK carried a refusal code |
| E 118 | `MQTT_PROTOCOL` | a malformed or unexpected packet from the broker |
| E 119 | `MQTT_NO_PINGRESP` | no PINGRESP within its deadline |
| E 120 | `MQTT_LOST` | the broker closed the connection, or a socket error ended it |
| E 121 | `MQTT_STALLED` | the broker stopped reading (backlog or drain timeout) |
| E 122 | `MQTT_SUB_REFUSED` | the broker refused a subscription |
| W 77 | `MQTT_SHORT_SESSIONS` | sessions keep ending right after they start |

Shared codes: `CALLBACK` 14 (a WiFi callback or a consumer raised), `ALLOC` 20, `BAD_ARG` 21, `CFG_READ`
26, W `STORED_DEFAULT` 10. A link-loss teardown and a deliberate reconnect log nothing. Each failure is
logged once per attempt, so the backoff bounds the FRAM writes; the newest-entry rule keeps a long outage
to one history slot. `MQTT` and `CFGMGR_MQTT` are FRAM-backed on `dev` (`fram_target = "fram"`).

## 9. Tunables

Generated constants in the `dev` module (the per-service timeouts rule, N.1), passed whole as
`MqttConfig`: `mqtt.keepalive_s` 60, `mqtt.ping_interval_ms` 15,000, `mqtt.response_timeout_ms` 10,000,
`mqtt.connect_timeout_ms` 10,000, `mqtt.backoff_min_ms` 2,000, `mqtt.backoff_max_ms` 60,000,
`mqtt.stable_after_ms` 30,000, plus the shared `dns.timeout_ms`/`dns.tries` and the client id default.
In `src/`: `mqtt.tick_ms` 100, `mqtt.link_poll_ms` 1,000, `mqtt.idle_recheck_ms` 60,000,
`mqtt.drain_timeout_ms` 5,000, `mqtt.max_out_backlog` 2,048, `mqtt.qos1_retry_ms` 10,000,
`mqtt.qos1_max_tries` 3, `mqtt.short_session_warn` 3, `mqtt.pub_step_ms` 1,000, `mqtt.unconfirmed_max_bytes`
2,000 (an owner decision, §14) and the buffer sizes in §5. Every one is an
estimate until the bench run (Basis "estimated (agent, …) — measurement owed: … L4").

## 10. Build wiring

- `driver_registry._OVERRIDES["mqtt"]`, a singleton service; `buildspec` rows with no TOML fields.
- `codegen._build_args_mqtt`: the WiFi bound methods, `MqttConfig(...)`, `sources=` the sensor
  instances, `cfg_path`, `_fram_kw`; the settings group, the status merge and the import, each only
  when `"mqtt" in have`.
- `graph.py`: `mqtt` depends on `conn` and on every sensor it publishes.
- `definitions.py`: the MQTT Broker group (from the `@web` tags), the status fields, the errcount rows.
- `validate.py`: a device carrying `mqtt` must keep `max_connections` at least one below the shared lwIP
  ensemble's ceiling, so the owner's 8.4 trade is checked at build time rather than remembered.
- `devices/dev.toml`: `max_connections = 5` and the `[[instance]] driver = "mqtt"` block with
  `fram_target = "fram"`.
- `js/mock-server.js` masks `MQTTPW` like `PW`; `mockdata/samples.json` gains the MQTT config, status
  and errcount samples.
- `toolchain/versions.toml` `apt_packages` gains `mosquitto` and `mosquitto-clients` (owner, 8.8: "apt
  package (Recommended)"); the digital-twin CI job installs the list; BACKLOG.md's chroot list gets the
  entry.

## 11. Tests by tier, and the bench runbook

- **L0**: every existing gate (task inventory row for the reader, error catalog, tunables register,
  comment cap, conventions, readiness, setter contract, golden stored-config map, body cap, device TOML
  allow-list `mqtt` on `dev` only, novel-combo fixture, registry, codegen present/absent, definitions,
  validate refusal with its malformed fixture, level containment).
- **L1** (`tests/`, Unix port, claimed port base 28000): codec against the specification's examples and
  every remaining-length boundary; the client against an in-process scripted broker — connect, refusal,
  timeouts, subscribe, QoS 0/1 both ways, DUP retransmission and give-up, ping deadline, malformed and
  oversize input, broker EOF, stall, short-session warning, link gating, hotspot, disabled, reconnect,
  backoff growth and stable reset, consumer dispatch and a raising consumer, the drain-timeout-ends-the-
  connection rule, the config shape refusals, and an allocation-flat run.
- **L2** (Run 12 of the twin CI suite, devices carrying `mqtt`): a real mosquitto on a free port; enable over
  REST; `online` retained and every module's measurements arrive; inbound `cmd` messages counted; broker
  SIGKILL and restart, SIGSTOP stall, client-id takeover and an inbound flood, each recovered by the rules
  above; REST serving throughout; no task restarted; the expected codes and nothing else in `MQTT`'s log;
  zero memory markers at both GC stages (the suite runs twice).
- **L4** (bench, Pi4, `tests_hardware/bench/test_mqtt_broker_faults.py`): §11.1.

### 11.1 Bench runbook (a session on the Pi4, owner's go-ahead in that session)

1. `git fetch` and check out `claude/whole-project-audit-plan-followup`; `uv run
   toolchain/setup_toolchain.py env --tier bench` (installs `mosquitto` with the rest of `apt_packages`).
2. Build and flash the `dev` image from this branch — the session's one allowed flash (E.6.3): `uv run
   scripts/build_firmware.py dev`, then `picotool load -x -v` with a USB-capable picotool.
3. Read the board's FRAM error logs (`GET /status` errcount) before anything clears them (CLAUDE.md); the
   module's fixture also prints every non-empty log before its own `ResetErrors`.
4. Run the `mqtt` scope, never the whole bench yet (owner, 2026-10-08: "you shall not run the whole bench at
   this time (will happen lateron when mqtt as such is running)"):
   `scripts/run_bench_hardware_suite.sh --scope mqtt --allow-persistence-writes-to=networking/mqtt`. It runs
   L0-L2 first, then only the flash and bench tests `tests_hardware/run_scopes.py` lists: this module plus
   the tests the branch reaches beside it (the resolver, the connection ceiling and body cap, the heap with
   the client resident, boot and reboot, the website, the FRAM chunk layout and the `env --tier flash`
   rerun), with the reason for each. The write permission is scoped to `networking/mqtt`, so no other
   group, the SCD30's NVM least of all, can be written; the runner refuses the global
   `--allow-persistence-writes` with a scope, and reports a passing scoped run NOT CLEAN, since the rest of
   both tiers waits for the full run. The module starts its own mosquitto on the Pi4's `br0` address and
   port 18883 and enables the client over REST once (a shared prerequisite write). In order it covers:
   - connect, `online`, and strict-JSON measurements per sensor;
   - an inbound command;
   - broker SIGKILL and restart;
   - SIGSTOP stall and silent path loss (`iptables` DROP), both detected within 35 s;
   - a reset path (REJECT);
   - a client-id takeover bounded by the backoff;
   - the broker found by the Pi4's own `.local` name through its Avahi (this one writes `MQTTHost` twice, so
     it runs only with `--allow-persistence-writes-to=networking/mqtt`);
   - a 3000-message QoS 0 flood with REST timed under it, a 500-message QoS 1 burst and an oversized message;
   - a checkpoint (no task ended, only the expected `MQTT` codes);
   - an AP outage through `BenchBridge`;
   - a hard reset;
   - the faults again under `device_scripts/mqtt_at_default_gc.py` at `gc.threshold(-1)`;
   - switching the client off, which must publish a retained `offline`.

   Every `iptables` rule matches only the DUT's address and port 18883 and is removed in a `finally`; none
   touches `br0` or the session's own path (`tests_hardware/README.md` has the account).
5. Report: the run record's `result_note`s (detection and reconnect times, the flood's REST latency, the
   largest payload, the default-gc heap minimum), which are the measurements Part N's `mqtt.*` and
   `l4.mqtt_*` rows owe, and the module's verdict. The client ends switched off, so later bench tests see the
   old baseline.

## 12. Where the rules land when the PoC merges

SPECIFICATION.md: C.7.1 band row; C.9 task-table row (the reader); A.7 construction/FRAM chunk order for
`dev`; A.8 `/networking` and `/status` fields; F.2 (the client connects to IPv4 literals only, after
`resolve_ipv4()`); H.7 (the `dev` connection budget with MQTT); I.6 body figure; Part N rows; a new Part M
section for the MQTT client's settled rules (this file's §2–§8). CLAUDE.md's FRAM-logger list gains
`MQTT`/`CFGMGR_MQTT` (dev only). `DEVICE_REFERENCE.md` gains the user-facing MQTT settings.

## 13. Decided on the owner's behalf during design (agent, 2026-10-08)

Each the more conservative, more easily reversible choice, for review:

1. An explicit `MQTTEnable` switch besides the host (the UI cannot clear a string).
2. Measurements are QoS 0 and not retained; only `status` is retained.
3. The PoC's own `cmd/#` messages trigger nothing; behaviour comes only through constructor-wired
   consumers, synchronous and RAM-only.
4. Connection failures are errors (the NTP precedent: `NTP_NO_REPLY`, `NTP_DNS`); only the short-session
   pattern is a warning.
5. Client id limited to the 1–23 letters, digits and `-` every MQTT 3.1.1 broker must accept.
6. Ping every 15 s with a 10 s deadline regardless of traffic: dead-transport detection within 25 s.
7. No MQTT DISCONNECT before a commanded reboot (no new shutdown hook); the broker publishes the will.
8. `MQTTHost` is length-checked at PUT and shape-checked at use, exactly as `NTPHost` is, until the
   project's host-name shape exists on both sides of the website; every other MQTT string keeps its
   PUT check.
9. A reconfiguring DISCONNECT (a settings change, or switching the client off) is preceded by a
   retained `offline` on the old status topic, since the DISCONNECT makes the broker drop the will.
10. The first measurement round follows each CONNACK, and the interval is read at connect: a consumer
    gets values at once, and a changed interval applies at once instead of after the old one ran out.
11. A passing scoped bench run (`--scope mqtt`) is reported NOT CLEAN, the precedent `--skip-lower-levels`
    set: everything that ran passed, but it never stands in for an L3/L4 pass. Its scope also carries the
    tests the branch reaches outside the client (§11.1), and two candidates were left to the full run: the
    NTP tests that write `NTPHost` (`networking/ntp`), and the hotspot role reversal, which never enables
    the client.

## 14. Owner decisions after the design (owner, 2026-10-08)

- No TLS: 'TLS is not needed as it all runs in a local network.' A plain IP address is always accepted
  and nothing may block: 'It should accept plain IP addresses anyway. But it must not block, ever.'
1. Asked "Should the resolver learn .local names (one-shot mDNS), for MQTTHost and NTPHost alike?":
   'Add it, bench-tested (Recommended)'. `asy_dns_client.py` sends the ordinary query, RD clear, from an
   ephemeral port to 224.0.0.251:5353 (RFC 6762 §5.1); the responder answers by unicast with the ID and
   question repeated (§6.7). The same bounded, cooperative wait as a DNS lookup, never lwIP's own mDNS
   path, which only the blocking `getaddrinfo()` reaches.
2. Asked "Should the MQTT client cap the bytes the broker has not yet confirmed at its 2,000 B share of
   lwIP memory?": 'Cap at 2,000 B (Recommended)'. §3.3 has the mechanism.
- The bench runs the client's scope, not the whole tier: 'set up the tests in such way that you only test
  MQTT (and whatever is affected by your changes) on the bench. you shall not run the whole bench at this
  time (will happen lateron when mqtt as such is running)'. And its writes are scoped per group: 'it makes
  absolutely no sense globally enable persistence writes, as writing the scd30 for mqtt tests is nonsense,
  so scope it correctly'. §11.1 step 4 has the command.
