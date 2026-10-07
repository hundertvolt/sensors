> **Raw research report** (agent, 2026-10-07): written by a read-only research agent of the MQTT PoC research session, kept verbatim as the evidence base for `mqtt_poc/RESEARCH.md`. Tags such as [V]/[SRC] mean verified in source by that agent; [I]/[INFERENCE] are not verified; nothing here was run on hardware. Clone paths (`<research-session scratchpad>/ext/...`) refer to that session's temporary scratchpad, not to this repo. Line anchors into this repo are as of `1cff5a2`.

# 04 — Integration requirements for an MQTT client service (publish + subscribe, PoC)

Read-only analysis of `/home/user/sensors` at HEAD (2026-10-07). Every requirement is cited. Legend:

- **HARD** — an owner decision, a CLAUDE.md hard rule, or a machine-enforced gate (a test/lint that
  fails the build). Not negotiable without an owner decision.
- **CONV** — established convention/precedent (Part C/D/G shape); deviating needs a stated reason and
  is "changed, not flagged" under D.10 (CLAUDE.md:90-101).
- **REC** — agent recommendation derived from the above (not yet anyone's decision).

Citations: `SPEC` = `SPECIFICATION.md` (line numbers as of this read), `CLAUDE` = `CLAUDE.md`.

---

## 0. The five things most likely to be gotten wrong

1. **There is no "link up/down" event, callback or flag API from WiFi.** Dependants *poll*
   `WifiService` through bound methods (`network_available_locked`, `get_dns_server_ip`,
   `get_wifi_mode_lock`, `wlan_isconnected`, `is_hotspot_active`), exactly as `NTPClient` does
   (`src/asy_ntp_client.py:134-153`, generated wiring `buildgen/codegen.py:418-424`). `WifiService`
   owns the one `network.WLAN` and **re-creates it on every mode switch** (`src/asy_wifi_service.py:667-682`),
   so any library that constructs/activates/disconnects its own `network.WLAN` (e.g. `mqtt_as`) is
   incompatible by construction (§3).
2. **A broker that is unreachable is routine, never a task end.** A supervised task that ends is
   restarted at a cost of 100 against a 300 budget decaying 1 per 2 s pass → ~3 restarts then a
   **device reboot** (SPEC:1790-1796, `src/asy_system_service.py:63-66, 357-394`). The NTP client
   used to end after failures and rebooted the device every ~4 minutes (SPEC:2134-2142, owner
   2026-09-24). MQTT must retry in place with its own capped exponential backoff (SPEC:2562-2570).
3. **`socket.getaddrinfo()` is not called from `src/`** (SPEC:4188-4193) and
   `asyncio.open_connection()` calls it unconditionally (`extmod/asyncio/stream.py:103`, "TODO this is
   blocking!" at v1.29.0). Resolve with `asy_dns_client.resolve_ipv4()` first and hand
   `open_connection()` a dotted-quad (lwIP resolves numeric hosts without a DNS query, SPEC:4189-4193);
   wrap the connect/CONNACK/PINGRESP waits in `asyncio.wait_for_ms()` (SPEC:4194-4201).
4. **The firmware's lwIP pools and the GC heap are sized for exactly 6 inbound HTTP connections.**
   `MEMP_NUM_TCP_PCB = 9 = max_connections(6) + 3 spares` (`toolchain/versions.toml:41-59`,
   SPEC:1362-1366) and `check_lwip_ensemble()` counts no outbound client
   (`toolchain/micropython_overrides.py:185, 208-277`). `max_connections = 6` was an owner decision
   backed by heap measurements at peak (~21 % free, SPEC:5532-5546, owner 2026-09-24). A permanently
   held MQTT TCP connection is not in any of these budgets → owner question (§11).
5. **The REST surface is fixed at six endpoints and the website/codegen are hand-assembled per
   section.** A new service does *not* get REST/website exposure "for free": `buildgen/codegen.py`
   hardcodes the `settings`/`status_sources` dicts (`codegen.py:643-697`), `WebserverService`
   hardcodes the three `/status` sections it streams (`src/asy_webserver_service.py:503-532`), and
   `buildgen/definitions.py` hand-builds the Networking/Status sections and the errcount catalog
   (`definitions.py:105-138, 407-421, 497-557`). Plan edits in codegen, definitions, `js/mock-server.js`
   (cross-language mirror, SPEC G.2 / H.4) and `mockdata/samples.json`.

---

## 1. Module shape & naming

| # | Requirement | Class | Source |
|---|---|---|---|
| 1.1 | One file in `src/`; a module with an `async def` in its public API **must** carry the `asy_` prefix (and only such a module). | HARD (gate) | `tests_scripts/test_code_conventions.py:52-68` (`asy_marker`) |
| 1.2 | Primary class name derives from the file name: `asy_<x>_service.py` → `<X>Service`, `asy_<x>_driver.py` → `<X>Driver`; acronyms upper-case (`NTPClient`, `UARTComm`, `FRAMManager`); no `Asy` prefix. So `asy_mqtt_client.py`→`MQTTClient` (mirrors `asy_ntp_client.py`→`NTPClient`) or `asy_mqtt_service.py`→`MQTTService`. | CONV | SPEC:1562-1570 (C.2) |
| 1.3 | Flat frozen namespace: `src/` and `ext/` are copied flat and frozen together; a module name colliding with any other frozen module (e.g. an `ext/` copy of `umqtt`/`mqtt_as`) silently resolves to whichever defines it. Pick a unique module name. | HARD (mechanism) | CLAUDE:114-127 (last sentence); SPEC A.4:158-161 |
| 1.4 | `_NAME = const("MQTT")` (or chosen base name) is the logger name, the REST/errcount key, the config file stem and the `CFGMGR_<name>` logger; if the class publishes a measurement namedtuple, **its type-name string must equal `_NAME`** (machine-checked). Field tuple `_FIELDS` kept beside the namedtuple literal (mypy needs the literal). | HARD (gate) / CONV | SPEC:1572-1582; `test_code_conventions.py:78-97` (`measurement_name`); precedent `src/asy_ntp_client.py:125-129` |
| 1.5 | Attributes/methods private by default; public only when another module needs it. No name-mangled `__` methods. | CONV | SPEC:1570-1573 |
| 1.6 | Constructor: own parameters first (here: the WiFi bound methods/lock, a timing namedtuple, maybe a config namedtuple), then the fixed tail `max_module_error=5`, `name_ext=""`, `cfg_path=""` (those it has) and exactly one `log: LogConfig = DEFAULT_LOG`. "checked by a test". | HARD (gate) | SPEC:1599-1605 (agent, 2026-08-07) |
| 1.7 | Parameters that travel together are **one config namedtuple built by generated code** (`NtpTiming`, `WifiConfig`, `ServingLimits` precedents): runtime `collections.namedtuple`, typed via a same-named `typing.NamedTuple` under `TYPE_CHECKING`, defaults as module `const()`s, **every field passed** (MicroPython namedtuple has no defaults). ruff `max-args = 8` only goes down. | CONV + HARD (ceiling) | SPEC G.2:5196-5200; SPEC D.10:2987-2992; `pyproject.toml:206`; `tests_scripts/test_lint_ceilings.py`; precedent `src/asy_ntp_client.py:67-78` |
| 1.8 | A `bool` constructor parameter must be keyword-only (`*,`) — ruff `FBT001/FBT002` under `select=["ALL"]`. | HARD (lint) | SPEC K.2:6784-6790 |
| 1.9 | Member order (D.15): dunders (`__init__` first), then private, then public; within each: Starters, Getters (`get_*`,`is_*`), Setters (`set_*`), Others (`setup`, `reset*` are Others); alphabetical within a role. "Starter" is a role: a method handed to the supervisor (`get_*_starters`, `start_*`, its paired `stop_*`). Machine-checked over `src/`. | HARD (gate) | SPEC:3032-3068; `test_code_conventions.py` (`member_order`) |
| 1.10 | Naming of starters/coroutines (machine-checked): task starters `start_asy_*`, timer starters `start_timer`/`start_*_timer`, coroutine handed to `create_task()` named `_*_loop`. | HARD (gate) | `tests_scripts/test_code_conventions.py:18-24, 109-...` (`starter_names`) |
| 1.11 | Comment discipline: exactly one header block per module (≤3 prose lines); **function/class explanations are `#` comments under the `def`, never docstrings** (agent, 2026-09-29); every inline comment block ≤3 lines; load-bearing detail moves to SPEC with a pointer. Gate at zero over-cap blocks. | HARD (gate) | CLAUDE:465-499; SPEC D.11:2995-3008; `tests_scripts/test_comment_block_cap.py` |
| 1.12 | Typing: full annotations; `TYPE_CHECKING` via `try: from typing import TYPE_CHECKING / except ImportError: TYPE_CHECKING = False`; PEP 604 `X | None` only; structural `Protocol`s inside `if TYPE_CHECKING:`; quote an annotation only if it names a `TYPE_CHECKING` import or a later class (owner 2026-09-24). Reuse shared aliases from `asy_base_classes.py` (`TaskStarter`, `TimerStarter`, `ErrorSource`, `JsonMapping`, `NtpSyncFct`, `AsyncCallback`, `SetupFct`, `PushFct`) and `"ErrorLog"` from `asy_print_log.py`. mypy `--strict`; `src/` must never suppress `method-assign`. | HARD | SPEC C.10:2570-2591; SPEC D.6:2941-2955; CLAUDE:805-842; `src/asy_base_classes.py:21-67` |
| 1.13 | Every import is a static top-level `import`/`from … import` (no import inside a function, no `__import__`/`importlib`) — enforced for `src/`, `ext/` and generated modules. | HARD (gate) | SPEC F.1:3894-3925; `tests_scripts/test_import_placement.py`, `test_import_graph.py` |
| 1.14 | No `print()` (use the logger), no `assert` in `src/` (machine-checked). | HARD (gate) | `test_code_conventions.py` rules `no_print`, `no_assert` |
| 1.15 | Raise message form: a fixed string naming the condition, values as separate args; `except` tuples alphabetical `(MemoryError, OSError)`; logging calls `err_s("Fixed text:", e, errno=_ERR_X)` — never f-strings/pre-built strings (so a suppressed level allocates nothing); codes passed **by keyword** `errno=`/`wrnno=` (machine-checked). | HARD/CONV | SPEC:1655-1656, 1749-1752; `test_code_conventions.py` (`log_keywords`) |
| 1.16 | Layering: Part C's layer 2/3 split is for bus chips. For a network client the closest precedent is the `NTPClient` split: transport helpers that **never log and never raise** (`asy_udp_socket.py`, `asy_dns_client.py`, SPEC C.7.1 "No logging in these layers", owner 2026-08-20) under one service class that owns the logger and persists failures. A TCP/MQTT-packet helper layer, if split out, takes the same "return sentinel, owner logs" contract (`UDPSocket.disconnect()` returns bool, C.7). | HARD (for named layers) / REC (for a new one) | SPEC:2127-2131; SPEC:2075-2078; `src/asy_udp_socket.py:8-10, 138-143` |

## 2. Lifecycle

### 2.1 Construction (sync `__init__`)

- **HARD** `__init__` only stashes args and sets the readiness gate "not ready"; no awaitable work, no
  I/O, no network. `async def setup(self) -> bool` (no parameters) does the deferred work; `True` =
  ready, `False` = degraded and already logged by the object. Gate attribute is `self.initialized`
  (False→True) unless the meaning genuinely differs. Pre-`setup()` calls answer per the class's own
  never-raise contract. Checked by `tests_scripts/test_readiness_gates.py` and
  `tests/test_readiness_gates.py`. (SPEC C.13:2646-2668)
- **HARD** The logger is created in `__init__` via `make_logger(log, name)` (or by the
  `SensorReader` base). With a FRAM `LogConfig` this **draws a FRAM chunk at construction**
  (`src/asy_print_log.py:225-239`). FRAM chunk determinism rule: the construction must be
  unconditional, fixed-position, never inside a branch/loop a task restart could re-enter; "prove
  single, deterministic construction before adding any new FRAM-backed class" (SPEC:226-234). So:
  never build a logger, `ConfigManager` or any FRAM-backed object on (re)connect.
- **HARD** "Nothing completes a module after construction" — no `register()/finalize()`; everything a
  module needs (WiFi bound methods, topics, schema) is a constructor argument (SPEC:1824-1826, A.7
  step 13 at SPEC:459-460).
- **CONV** Every `machine.Timer` (if any) is allocated in `__init__` and kept referenced on the object
  (an unreferenced armed Timer is disarmed by the GC finaliser; SPEC F.1:3966-3975).

### 2.2 `setup()` (the one-time boot batch)

- **HARD** `setup()` is awaited once in the generated boot batch, in construction order, each call
  followed by `sysfunct.feed_watchdog()` and a `gc.collect()` placement reset
  (`buildgen/codegen.py:450-482`; SPEC A.7 step 15:477-490). It must be **bounded and short**: the
  batch runs unfed between feeds against an 8000 ms watchdog (SPEC:492-500, Part N
  `boot.unfed_stretch_*`). → **No broker connect, no DNS, no socket in `setup()`**; WiFi is not even
  up at that point (the WiFi task starts later in `start_and_check_tasks()`).
- **HARD** "Every logger store is set up here, first in its module's `setup()`, so no task sets a
  logger up lazily" (SPEC:483-485; `src/asy_base_classes.py:4-5`). A `SensorReaderConfig` subclass
  gets this from `super().setup()` (logger, then `cfgmgr`, returns `cfgmgr.valid`,
  `asy_base_classes.py:622-626`); a non-`SensorReader` class must call `await self.pr.setup()` (and
  its own `cfgmgr.setup()`) itself (`asy_system_service.py:482-499`, `asy_webserver_service.py:788-790`).
- **HARD (buildgen mechanics)** buildgen only emits `await x.setup()` if `DriverInfo.needs_setup`:
  true for any `SensorReader/SensorReaderConfig` subclass; for an `_OVERRIDES` service whose base is
  something else, only if the class body itself defines `async def setup` (inherited doesn't count)
  (`buildgen/driver_registry.py:61-70`).
- **HARD** Boot latency is not a metric; the only bar is "does not starve the watchdog" (CLAUDE:239-246).

### 2.3 Tasks: how a long-running task must be registered

- **HARD** Expose `get_task_starters()` (list of bound `start_asy_*` methods, each returning
  `asyncio.get_event_loop().create_task(self._<x>_loop())`) and `get_timer_starters()` (list, may be
  empty — "kept empty rather than omitted so callers can treat every driver/service uniformly",
  `asy_webserver_service.py:760-763`). `get_trigger_starters()` only for sensor read triggers
  (stagger), not for a service (SPEC C.9:2445-2450; C.9.1:2501-2525). The generated
  `_collect_task_starters()`/`_collect_timer_starters()` call these uniformly on **every** module
  (except `fram`) — a missing method is an `AttributeError` at boot (`codegen.py:699-757`).
- **HARD** Supervision is generic: `SystemService.start_and_check_tasks()` starts each starter
  (spread `1/N` s apart), then `_supervise()` every 2 s restarts any task that is `done()` by
  **re-invoking the same starter on the existing object** (never `__init__`), logs one SYSTEM entry per
  end (`TASK_RAISED`/`TASK_CANCELLED`/`TASK_RETURNED`, errnos 42-44) and charges 100 to a 300 budget;
  past it → `TASK_BUDGET_REBOOT` and `_reboot()` (`src/asy_system_service.py:248-258, 357-394, 501-523`).
- **HARD** Which failures may end a task: **only when the restart re-initialises something real**;
  a failure the task meets again unchanged after a restart is handled in place, logged under the
  repeat rule, retried, recovered on next success (SPEC C.7.2:2132-2142; owner 2026-09-24). For MQTT
  a restart re-initialises nothing but a socket → the loop should never end. **REC**: one supervised
  `_connection_loop()` that resets its state at the top (as `WifiService._connect_loop()` does,
  `asy_wifi_service.py:336-339`), closes any socket left by a previous incarnation, and loops forever
  with backoff.
- **HARD** "A retry loop never ends its task to 'retry by restart' — that spends the reboot budget"
  and a sentinel-returning retry loop needs its own capped exponential backoff (precedents:
  `CaptiveDNS.run()` 0.5→5 s, `NTPClient` 10→600 s, `ntp.backoff_mult=2`) (SPEC:2562-2570;
  `src/asy_captive_dns.py:35-45, 99-141`; `src/asy_ntp_client.py:59-65, 360-371`).
- **HARD** Every task created **outside** the starters (e.g. a separate reader/pinger task spawned per
  connection) must be a row of SPEC C.9's task table with reason, lifetime, cancel path and "top that
  persists its failure"; every `create_task(`/`start_server(` in `src/` is a starter or a row —
  `tests_scripts/test_task_inventory.py` fails otherwise (SPEC:2451-2468). A task nobody awaits must
  catch everything at its top and persist it (precedent `CaptiveDNS.run()` and `_flash_led_off()`,
  table rows at SPEC:2462-2463).
- **HARD** A task that ends raising with nobody awaiting it reaches SYSTEM's `report_unretrieved()`;
  a finished C `Task` has no `.exception()/.result()`; await an ended task at most once (second await
  segfaults the Unix port); a task cannot cancel itself (SPEC F.1:4072-4090, 4115-4140).
- **CONV/HARD** Timers: prefer `asyncio.sleep_ms`/`wait_for_ms` in the task for keepalive scheduling.
  If a `machine.Timer` is used: soft only, callback only `.set()`s a `ThreadSafeFlag` (one waiter per
  flag), a fire that must not be lost is `PERIODIC`, every `Timer.init()` catches
  `(MemoryError, OSError)` (ENOMEM from the 16-alarm pool shared image-wide), keep it referenced
  (SPEC C.9:2470-2499; F.1:3926-3975; owner 2026-08-07 `a015e66`). 1 s tick timers go through
  `arm_tick_timer()` (`asy_base_classes.py:262-270`).
- **HARD** Nothing but `asy_system_service.py` may call `machine.reset()/bootloader()`
  (`tests/test_reset_call_site_invariant.py`, SPEC:255-261); only the boot batch and the supervisor
  feed the watchdog (`SystemService.feed_watchdog()`, feed sites pinned by
  `tests_scripts/test_watchdog_feed_sites.py`, SPEC G.2:5180-5189). An MQTT task never feeds and never
  resets.
- **HARD** `gc.collect()` is confined to the two boot lists; none in business logic (CLAUDE:342-404;
  `scripts/lint.sh:72-87`; `tests_scripts/test_gc_collect_sites.py:8-12`). (`mqtt_as` calls
  `gc.collect()` in `_keep_connected` — disqualifying if placed in `src/`.)

### 2.4 Shutdown / teardown

- **HARD** No resource acquisition without a guaranteed release on every exit path, exceptions and
  cancellation included (SPEC D.3:2923-2928). For TCP via asyncio streams: MicroPython's
  `Stream.close()` is a no-op and **`wait_closed()` is what actually closes the socket**
  (`extmod/asyncio/stream.py:16-21` at v1.29.0); the webserver's precedent is `close()` then
  `asyncio.wait_for(writer.wait_closed(), timeout)` with each failure persisted as a warning
  (`asy_webserver_service.py:534-544`, wrnno 52/53).
- **HARD** A teardown method on a class with no logger returns `bool` so the owner logs; a class with a
  logger persists its own teardown failure (SPEC:2075-2078; `CaptiveDNS` precedent
  `asy_captive_dns.py:143-159`).
- **CONV** Commanded reboots: `_reboot()` flushes config stores, pauses FRAM, arms a one-shot; the
  generated `_flush_pending_configs()` flushes any module with a `cfgmgr` attribute
  (`codegen.py:535-547`). No MQTT-specific shutdown hook exists or is needed; an orderly MQTT
  DISCONNECT before reset would need new plumbing (owner question if wanted).

## 3. WiFi interplay

### 3.1 What `WifiService` offers dependants (complete list)

All pull-based; **no events, callbacks or observers** (`src/asy_wifi_service.py`):

| API | Semantics | Line |
|---|---|---|
| `get_wifi_mode_lock() -> asyncio.Lock` / `wifi_mode_lock` | serialises every use of the CYW43 radio; NTP holds it for its whole sync attempt | 244, 808-809 |
| `network_available_locked() -> bool` | `True` iff not hotspot and `wlan.status() == STAT_GOT_IP`; **caller must already hold `wifi_mode_lock`** | 858-859 |
| `wlan_isconnected() -> bool` | returns `False` if the lock is held (degrades), else `isconnected()` | 874-877 |
| `get_wlan_ifconfig()` / `get_dns_server_ip()` / `get_wlan_rssi()` | answer `None` while the lock is held | 790-794, 817-839 |
| `is_hotspot_active() -> bool` | lock-free int compare | 841-845 |
| `get_data()` → `WIFI(Mode, Connected, IP, TS)` | 1 Hz cached snapshot from `_uptime_loop()` | 86, 709-726, 775-779 |
| `get_wifi_uptime()` | measured seconds connected | 811-812 |
| `reconnect_wifi()` | sets a flag the WiFi task acts on (used as `post_fct` of the identity settings group) | 861-867 |

- **HARD** Locking convention: "a function that needs its caller to hold a lock ends in `_locked`,
  and the getters that check `.locked()` themselves and answer `None` keep plain names. ... A new getter
  picks one shape deliberately, never by copying its nearest neighbour" (SPEC C.8:2321-2326;
  `asy_wifi_service.py:814-816`). Already caused a real bug (`get_dns_server_ip()` always `None` from
  inside the lock) → read the DNS server **before** taking the lock (`asy_ntp_client.py:342-349`).
- **HARD** `wifi_mode_lock` is a row of the lock table; it may be held while taking
  `UDPSocket._connect_lock` and a FRAM log write. Any new lock (e.g. an MQTT socket-write lock) must be
  added to SPEC C.8's table in the same change; `tests_scripts/test_lock_order.py` resolves every
  `async with`/`.acquire()` in `src/` against it (SPEC:2254-2276).
- **Fact** The WiFi task holds `wifi_mode_lock` across its 60 s STA retry wait after a loss
  ("accepted priority-inversion cost", SPEC:2327-2328; `asy_wifi_service.py:523-531, 643-647`) and
  across mode switches (2+1+1 s settles, `:667-682`).

### 3.2 How existing dependants wait for / react to link state

- `NTPClient` (the only network client today): wiring generated as
  `NTPClient(conn.get_wifi_mode_lock(), conn.network_available_locked, conn.get_dns_server_ip, NtpTiming(...), ...)`
  (`codegen.py:418-424`). Per attempt: read DNS server outside the lock → `async with wifi_mode_lock:`
  → guarded `network_available_locked()` call (`except Exception` → `CALLBACK` errno 14) → skip
  silently if not available (a skipped attempt does not lengthen the backoff) → resolve via
  `resolve_ipv4()` → UDP exchange (`asy_ntp_client.py:312-371`).
- Caller-supplied callbacks are guarded individually (`try/except Exception` → `err_s(..., errno=_ERR_CALLBACK)`),
  since "caller-supplied callback - could legitimately misbehave" (`asy_ntp_client.py:313-317, 345-349`;
  SPEC G.2 dispatch guarding).
- The webserver depends on WiFi only via `StaticSite.is_hotspot_active` (captive redirect).

### 3.3 Constraints this places on an MQTT client

- **HARD (ownership)** `WifiService` is the radio owner: it calls `network.country()/hostname()`,
  `WLAN.active()/connect()/disconnect()/deinit()` and **replaces `self._wlan` with a new
  `network.WLAN(mode)`** on every STA↔AP switch (`asy_wifi_service.py:231, 317-327, 667-696`). An
  MQTT library that creates its own `network.WLAN(STA_IF)`, calls `.active(True)`, `.connect(ssid, pw)`
  or `.disconnect()` (e.g. `mqtt_as`: `self._sta_if = network.WLAN(network.STA_IF); self._sta_if.active(True)`
  in `__init__`, `wifi_connect()`, `_keep_connected()` disconnecting WiFi, plus `time.sleep(0.1)` and
  `socket.getaddrinfo()`) would fight the WiFi state machine, its hotspot fallback and its permanent
  deactivation rules (A.4 "functional behaviours confirmed intentional", SPEC:283-294). It must be used
  — if at all — with all WiFi management disabled, which `ext/`'s no-edit policy may make impossible
  (§9.10).
- **HARD (no reachability-driven WiFi recovery)** A stuck CYW43 `isconnected()` false positive is
  recovered by power cycle; "the owner judged an independent reachability probe not worth its
  complexity" (CLAUDE:220-226; SPEC F.2:4220-4232, owner 2026-09-04 `655e4f9`, confirmed
  2026-09-26). MQTT's keepalive is effectively such a probe; it **must not** trigger
  `reconnect_wifi()` or any WiFi/device reset — doing so would be a feature change needing an owner
  decision.
- **HARD** In hotspot mode `network_available_locked()` is False → MQTT stays idle (no broker
  attempts, no error spam). After a mode switch every socket is dead (new WLAN object): detect via
  `OSError`/EOF/timeout, close, back off, reconnect.
- **REC** Do not hold `wifi_mode_lock` across broker I/O (a persistent session would starve WiFi's own
  task); check availability under the lock briefly like NTP, then release before the TCP connect.
  Decide deliberately whether `wlan_isconnected()` (lock-free degrade-to-False) or
  `network_available_locked()` (excludes hotspot, needs the lock) is the gate.

## 4. Config

### 4.1 Declaring and validating

- **HARD** Each field is a 6-tuple `(name, type, default, min, max, special)`, `type` ∈
  `"int"|"float"|"str"|"bool"` only (no lists — several topics = several `str` fields or one bounded
  string); `special` is a single bypass sentinel or a discrete allowed-value set; a `const()` schema
  referenced inside another `const()` tuple must itself be `const()` (SPEC C.5:1836-1846). Schema
  tuples named `_VAL_<KEY_UPPER_SNAKE>` (SPEC:1583-1585).
- **HARD** One file per module `config_<self.name>.cfg`, built only through `config_filename()`;
  `CFGMGR_<name>` logger built only by `ConfigManager`; a hand-built `"config_"` string fails
  `test_code_conventions.py` (SPEC C.14.1:2685-2700). `SensorReaderConfig.__init__` does this for you
  (`asy_base_classes.py:577-594`); `SystemService` shows the embedded-`ConfigManager` form for a
  non-`SensorReaderConfig` class (`asy_system_service.py:183-187`).
- **HARD** Numeric coercion policy: int OK for float; float for int only if integral; `bool` never for
  numbers (`type(x) is int`, bool is not an int subclass on MicroPython); NaN/±inf refused; float bounds
  checked against 2**24 statically (SPEC A.8:648-656; F.1:3949-3960; `tests_scripts/test_config_schemas.py`).
  Use `type_or_range_error()`/`checked_int()`/`checked_float()`/`checked_numeric()`; never hand-roll a
  cast or range check (SPEC G.2:5044-5048).
- **HARD (by analogy, agent precedent)** Schema string bounds count **characters**; protocol limits are
  often **bytes** (C.7.4: SSID/PW/Country/Hostname bounded in bytes at PUT and at use, refused as
  `"Invalid"` with `BAD_ARG` errno 21; a stored out-of-shape value runs on its default with
  `STORED_DEFAULT` wrnno 10) (SPEC:2213-2234; `asy_wifi_service.py:90-135, 274-284, 581-593`). MQTT
  3.1.1 strings are UTF-8 with 2-byte length prefixes, client IDs are guaranteed only for 1-23 bytes
  `[0-9a-zA-Z]`, publish topics must not contain `+`/`#`: apply the same byte/shape checks at PUT and use.
- **HARD** A config value is never a hardware/network failure: a value the broker/protocol would refuse
  must not feed a failure streak or end a task (C.7.4 rationale, SPEC:2224-2230).
- **CONV** Wire names: every bool is native JSON `true/false`; drop a redundant per-driver prefix only
  where the body is nested per module (`/sensors`); on the flat `/networking`/`/system` bodies keys must be
  unique across groups (NTP keeps `NTPHost`, `NTPOffset`) → e.g. `MQTTHost`, `MQTTPort` (SPEC C.5.3:1950-1960).
- **CONV** Command-only trigger fields (e.g. a "reconnect now"): special-alone `"bool"` field
  `(("X", "bool", None, None, None, True),)`, excluded from `get_dict_cfg()`'s explicit list; push
  callback reports success unconditionally once typed (SPEC C.5.2.1:1912-1922); website tag `dispatch=true`.
- **HARD** Push-callback/setter return contract is uniformly `bool`; a push callback receives the
  coerced persisted value; narrow ints with `type(v) is not int` (`tests_scripts/test_setter_contract.py`;
  SPEC:1898-1911).

### 4.2 Persistence

- **HARD** `setup()` writes the defaults once when the file is absent, repairs a damaged readable file at
  most once per boot, never overwrites an unreadable one; a failed write costs persistence, never the
  config; no write is ever retried (SPEC C.7.3:2170-2211). PUT writes are staged and flushed by a
  deferred task (WP5) because a flash write disables interrupts port-wide (SPEC F.2:4237-4250).
- **HARD** Never construct a `ConfigManager` over a production file with a narrower schema (drops sibling
  keys) (SPEC:1856-1866). Stored-config map (file names + key→type) is derived two ways and, from the
  release on, pinned as a golden fixture: a change ships with a migration (owner, 2026-09-26)
  (`tests_scripts/test_stored_config_golden.py`; SPEC:1862-1866).
- **HARD (tests)** Any hardware test PUT that persists is a `persistence_write` (flash wear gate);
  dispatch-only PUTs are outside it (CLAUDE:279-317; SPEC H.4 dispatch row at SPEC:5324).

### 4.3 Exposure via REST and website

- **HARD/mechanism** A setting reaches REST only through a `SettingsGroup(module, (field, …),
  post_fct=…, post_asy_fct=…)` registered under one of the fixed route keys
  `"networking"|"system"|"notification"` in the generated `RouteSources.settings`
  (`asy_webserver_service.py:233-245, 455-501`; `codegen.py:648-662`). A group receives only the request
  keys in its tuple while the store validates against the whole schema; a hook fires once per call only
  if a field changed; a raising hook marks the group's fields `"Failed"` (SPEC C.5.3:1935-1960; H.6).
  Precedents: `post_fct=conn.reconnect_wifi`, `post_asy_fct=ntp.ntp_force_sync`. The module must
  satisfy `_ModuleLike`: `name`, `pr`, `_set_dict_cfg`, `get_cfg_schema`, `get_dict_cfg`,
  `get_dict_data`, `get_error_counter`, `reset_error_counter` (`asy_webserver_service.py:39-51`).
- **HARD** Request body cap: `max_content_length = 2048` B (owner-sized, Part N `web.max_content_length`)
  must exceed the largest schema-permitted PUT body **per route**; `tests_scripts/test_request_body_cap_headroom.py`
  derives it from the generated definitions (string fields count `maxLength + 2`) and pins each
  device's maximum (`_EXPECTED_LARGEST`, dev 972 B). Adding MQTT host (≤253) + user + password + client
  id + topics to the flat `/networking` body grows it substantially; "a new driver or a widened string
  bound SHOULD fail this - update it and read the margin" (`test_request_body_cap_headroom.py:31-40, 103-130`;
  SPEC I.6; Part N row at SPEC ~7991).
- **HARD** Website definitions are generated from `# @web`/`# @web-group` tags, never hand-edited JSON
  (SPEC H.5:5339-5345, K.4). Tag grammar keys: `section, submitGroup, label, unit, description, kind,
  onLabel, offLabel, mask, dispatch, defaultValue, path, decimals, alwaysExecuted, format, codes, bytes,
  shape` (shapes `hostLabel|countryCode|hostName`) (`buildgen/web_tag.py:23-35`). A singleton service uses a
  literal `submitGroup` (not the `self` sentinel) (SPEC H.5.1:5384-5390). Every tag family is strictly
  parsed; a near-miss fails the build (SPEC L.5:7436-7445).
- **HARD/mechanism** The Networking section is assembled by hand in `buildgen/definitions.py:_networking_section()`
  (`:407-421`, explicit `_mandatory_group(...)` per group) — a new group needs an explicit (conditional)
  entry there; it is not discovered from tags alone (K.3 item 4's `_SENSOR_DRIVERS` is for sensors only,
  `definitions.py:49`).
- **HARD (G.2 mirror)** A `src/` policy and its `js/` mirror are one change: `js/mock-server.js` mirrors
  every backend quirk field for field, bound for bound — including the password mask, which today is
  hardcoded for `PW` only (`js/mock-server.js:619-622`); `mockdata/samples.json` needs a sample (K.8).
  Cross-language bounds pinned by `tests_scripts/test_definitions_js_mirrors.py` (SPEC G.2:5165-5173, H.4).
- **Known UI gap** "An empty string can't be set via this UI for any field" (owner, 2026-08-22,
  `cc999c1`, accepted) — so "no username/password" cannot be restored from the web UI once set (SPEC
  H.4:5330). Owner question if credentials are optional.

### 4.4 Credentials

- **HARD** "Don't touch `sensors/config.json`-equivalent files or commit any real credentials." The only
  accepted real credential in the repo is the hotspot fallback password, accepted permanently under the
  trusted-home-LAN threat model (CLAUDE:207-216; SPEC L.2:7117-7128). → Broker user/password schema
  defaults must be empty/non-secret; no credential in `devices/*.toml`, tests, fixtures or docs; set only
  via REST, persisted in the device's own `config_<name>.cfg` (gitignored per-device artifact).
- **CONV (C.4.4 "second legitimate reason")** Mask secrets on every GET through `_get_dict_cfg(..., callback=self._mask_pw)`
  that overwrites the value with `"********"` (`asy_wifi_service.py:510-514, 781-784`); `@web … mask=true`;
  mock mirrors the mask (§4.3).
- **Fact** WiFi credentials are stored in plaintext on littlefs; MQTT without TLS also sends the password
  in clear over the LAN → threat-model question for the owner (§11).

### 4.5 "Enable" flag

- **REC** Default the service to disabled (empty host = off, or an explicit `bool` enable defaulting
  `false`). Rationale grounded in gates: the twin CI and bench tiers assert healthy baselines — "no module
  logging a new error", `assert_no_task_ended` (SPEC H.7:5590-5600; C.7.2:2150-2153) — and the twin's real
  host sockets would otherwise hit a real or absent broker on every boot (`digital_twin/README.md:114-125`).
  A disabled instance must log nothing and spin no network I/O, but must still draw its FRAM chunks
  (determinism rule) and expose errcount/status.

## 5. Error handling & logging

- **HARD** Logger: `self.pr = make_logger(log, _NAME)` (or via `SensorReader`), `PrintLogHistory` (RAM) or
  `PrintLogHistoryStore` (FRAM), chosen by `LogConfig.fram`; `name` attribute equals `pr.name` (the
  `_ModuleLike`/`ErrorSource` registration shape) (SPEC C.7:1972-1981; `asy_print_log.py:296-322`;
  `asy_captive_dns.py:66-73`).
- **HARD (FRAM wiring rule)** "The ONLY module which NEVER has own FRAM logging is the FRAM module itself …
  Every other module shall have FRAM logging optional" (owner, 2026-09-16; SPEC A.7 step 4:418-426).
  Implemented as a comment tag `# @wiring fram_target FRAMManager log optional kwarg` at module level
  (every FRAM-wirable module carries it; `asy_ntp_client.py:120-123`; SPEC C.14.2:2741-2756). Every real
  device wires `fram_target = "fram"` on every wirable instance — enforced by
  `tests_scripts/test_device_tomls.py:374-381` (`_FRAM_WIRABLE_INSTANCE_DRIVERS` at :38 must gain the
  driver). A `SensorReaderConfig`'s own `cfgmgr` inherits the same `log=` as its own separate
  `CFGMGR_<name>` logger (WP2, SPEC A.7 step 6:432-437) → **2 FRAM chunks** (own + cfgmgr).
- **HARD** FRAM capacity is checked once per build per generated device (a `None` from `get_chunk()` at the
  mock level and on the board by the capacity device script; wozi ~17 chunks on 8 KB MB85RS64V); no runtime
  errno reports it (owner, 2026-09-16) (SPEC A.4:296-300).
- **HARD** Two log tiers: `pr.one/evt/all` print-only info; `pr.err_s/wrn_s` (async) persist to history/FRAM
  and count; `pr.err/wrn` sync, non-persisting for a genuinely sync site or a routine observation that must
  not count (SPEC:2018-2029). WiFi's split: "attempt" operations persist; routine state observations
  degrade silently with `pr.err()` (`asy_wifi_service.py:4-6, 742-749`).
- **HARD** Codes: integers 1-127 from **one global catalog** `buildgen/error_catalog.json`; base 1-9/1-2
  reusable only for the identical condition; shared band 10-29/10-19 (one number per condition — reuse
  `CALLBACK` 14, `TIMER` 17, `ALLOC` 20, `BAD_ARG` 21, `TIMEOUT` 22, `UNEXPECTED` 23, `CFG_READ` 26/W13,
  `STORED_DEFAULT` W10); module-specific codes in **a new, non-overlapping owner band** (free today: errno
  115-124, wrnno 71+; retired numbers never reused); declared as `_ERR_<NAME>`/`_WRN_<NAME>` `const()`s;
  `tests_scripts/test_error_catalog.py` checks every logging call (SPEC C.7:2031-2038; C.7.1:2080-2105;
  `buildgen/error_catalog.json:3-21`). The catalog also feeds the website's code descriptions (SPEC L.4:7348-7351).
- **HARD** "Every layer that meets a fault keeps its own persisted entry" (owner, 2026-10-02) **but** "in one
  log, one occurrence is never persisted as both an error and a warning" (owner, 2026-09-26), L0 scan
  `tests_scripts/test_fault_or_warning_never_both.py` (SPEC:2040-2049). Decide per condition: e.g. broker
  unreachable/refused as a warning (cf. `WLAN_NO_AP` wrnno 37) or an error (cf. `NTP_NO_REPLY` errno 71).
- **HARD** History ring: 10 slots, a code identical to the newest entry is counted and written through but
  spends no slot ('just don't repeat the same error in the slots', owner 2026-09-26) (SPEC:2093-2099). Each
  `err_s` on a FRAM logger is a FRAM write (not wear, owner 2026-09-26) — bounded by the backoff.
- **HARD (D.2)** Never raise out of any public method/task top; catch specific types; never bare `except:`
  (E722 enabled); allowed raises only the two controlled kinds (D.2:2901-2921). `MemoryError` is not an
  `OSError` subclass; `asyncio.TimeoutError` is a plain `Exception` — catch separately (SPEC F.1:3976-3978, 4095-4096).
- **HARD (MemoryError policy)** Design for zero `MemoryError`s; catching `(MemoryError, OSError)` and
  degrading is a backstop for genuinely uncontrollable conditions, and **a caught `MemoryError` is still a
  design defect**; every test must pass at `gc.threshold(-1)` *and* `32768` with zero caught-or-uncaught
  allocation failures (gates match `MemoryError` **or** `memory allocation failed`) (CLAUDE:342-404; SPEC
  I.4:5976-6050). Don't blanket-wrap asyncio primitives (owner, 2026-09-25; CLAUDE:227-231). Never let a
  `MemoryError` bubble into an unguarded crash of an otherwise-healthy task; the supervisor and watchdog are
  the last rungs (I.4(b)-(d)).
- **HARD** Inbound bytes are untrusted: clamp any size taken from the wire (MQTT remaining-length up to
  268 MB) **before** allocating (`[x] * n` can segfault for huge n; `LockableBuffer`/`PrintLogHistory`
  clamp-first pattern) (SPEC F.1:3941-3946). Relieve pressure by design — pre-allocated/reused buffers,
  chunking, streaming — never by a `gc` threshold or `gc.collect()` (CLAUDE:381-397).
- **HARD** `json.loads()` is not a validator and `json.dumps()` never raises and emits `nan`/`inf`; gate
  values before publishing; check emitted JSON strictly in tests (`tests/_strict_json.py`) (SPEC F.1:4142-4169).
- **Diagnostics rule** Investigating any real-hardware error: read FRAM-persisted errcount before any
  `ResetErrors` (CLAUDE:405-431). An MQTT logger joins that FRAM-backed list.

## 6. Status / REST exposure

- **Fixed surface** Six endpoints, no new routes: `/measurements`, `/sensors`, `/networking`, `/system`,
  `/status`, `/notification` (SPEC A.8:611-620; H.4 "Mirrors the 6 REST endpoints 1:1").
- **errcount (automatic once wired)** `/status.errcount` lists every registered error source by `name`;
  the generated `_collect_error_sources()` calls `get_error_sources()` uniformly on every module
  (`codegen.py:699-711`). A `SensorReaderConfig` returns `[self, self.cfgmgr]`; a non-reader implements
  `get_error_sources()`, `get_loggers()`, `get_error_counter()` (returns `await self.pr.get_log()`),
  `reset_error_counter() -> bool` (`await self.pr.reset()`) directly (SPEC C.14.3:2830-2846;
  `asy_captive_dns.py:75-88`). `PUT /status {"ResetErrors": true}` resets every source concurrently
  (`asy_webserver_service.py:633-648`).
- **errcount website rows are NOT automatic** — `buildgen/definitions.py`'s `_ERRCOUNT_CATALOG`,
  `_ERRCOUNT_NAME` and `_CFGMGR_LABEL` must gain the driver (`:105-132`); "a published source with no row is
  never rendered at all, and a row with no published source renders a permanent, reassuring 0" (SPEC
  H.6:5461-5469). Real-hardware `tests_hardware/website_identity.py` checks the served page names every
  errcount key (SPEC H.5.1:5412-5422).
- **Live state (connected, counters)** — three precedents, each needing codegen + definitions + JS mock work:
  1. **`maintenance_sensors`** (variable-length by design): `UARTLinkDriver.get_link_status()` registered
     under `MAINTENANCE_NAMES = {"uart_link": "UARTLINK"}` (`buildgen/model.py:24-26`;
     `codegen.py:442-451`), flattened on the page as `<NAME>_<field>`; "Registered as a maintenance sensor,
     not a new /status key ... without touching the shared webserver" (`src/asy_uart_link_driver.py:137-141`;
     definitions `:531-548`). Least invasive.
  2. Extend the generated `_networking_status()` dict (`codegen.py:612-622`) + `_status_section()`'s
     `networking_fields` (`definitions.py:499-512`).
  3. A new top-level `/status` section → requires editing `WebserverService._build_status_pieces()`, which
     hardcodes `networking/system/notification` (`asy_webserver_service.py:503-532`), the JS mock's status
     keys (`js/mock-server.js:416-417, 469`) and the definitions skeleton.
- **`/measurements` / `/sensors`** are fed only by `kind == "sensor"` instances (auto-resolved
  `SensorReader[Config]` subclasses in `asy_<x>_driver.py`) (`codegen.py:519-521, 646`). A service resolved
  through `_OVERRIDES` is `kind == "service"` and stays out of them — which is what a non-sensor service
  wants.
- **Response shapes** Every dict-shaped GET that scales with configuration is streamed
  (`_stream_dict_response`, `_PieceWriter`, ≤256 B pieces, non-finite → `null`); envelope only via
  `make_response()`; `res != "OK"` only for a broken request, never for invalid content (owner,
  2026-09-26) (SPEC C.5.3:1935-1949; G.2:5155-5160; I.3). GET copy-safety: build each snapshot with no
  `await` mid-construction (SPEC A.8:658-663).
- **Timestamps** `utc_now()` (None until first NTP sync) for any `TS`; elapsed times via `TickSeconds`,
  never counted wake-ups (owner, 2026-09-29) (SPEC G.2:5054-5065).

## 7. Build wiring (buildgen) and generated artifacts

### 7.1 Placement decision: optional `[[instance]]` vs mandatory infra

- **HARD** WiFi, NTP, SystemService and the webserver are mandatory infrastructure: never `[[instance]]`
  entries, constructed unconditionally by hardcoded codegen branches, in `CORE_MODULES`
  (SPEC L.3:7165-7178; `buildgen/frozen_modules.py:13-30`; `test_no_mandatory_infra_modeled_as_instance`).
  Optional/varying modules (FRAM, Neopixel, Notification, sensors, uart_link) are `[[instance]]` entries
  (SPEC L.3:7165-7168).
- **REC** A PoC "wired like any other service but not yet used" fits the **optional singleton service**
  path (Notification precedent): `[[instance]] driver = "mqtt"` on the chosen device(s), resolved through
  `_OVERRIDES`, member of `SINGLETON_SERVICE_DRIVERS` (name_ext refused, `validate.py:396-397`).

### 7.2 Files to touch (per K.3 and the service precedents)

| File | Change | Source |
|---|---|---|
| `buildgen/driver_registry.py` | `_OVERRIDES["mqtt"] = ("asy_mqtt_client", "MQTTClient")`; `SERVICE_DRIVERS`/`SINGLETON_SERVICE_DRIVERS` derive from it (uart_link is the only non-singleton exception). Needed even for a `SensorReaderConfig` subclass, both to keep it out of `sensors=` and because auto-resolution only scans `asy_<name>_driver.py`. | `driver_registry.py:13-31, 83-111`; SPEC L.4:7319-7323 |
| `buildgen/buildspec.py` | Rows in `REQUIRED_TOML_FIELDS`/`OPTIONAL_TOML_FIELDS` (the one hand-maintained table; owner 2026-09-18 `b0f755c`); not bus-attached → exclude from `BUS_ATTACHED_DRIVERS` like `neopixel`/`notification` (`:47`). A resolvable driver with no buildspec row fails with a dedicated error. | `buildspec.py:12-68`; SPEC L.1:7067-7072; L.6.6:7620-7628 |
| `buildgen/codegen.py` | A `_build_args_mqtt()` registered in `_BUILD_ARGS_HANDLERS` (`:248-257`); optional TOML fields emitted only `if "<f>" in f:`; WiFi bound methods hardcoded in the handler like `ntp`'s (`:418-424`), `cfg_path=cfg_path`, `_fram_kw(spec, ctx)`; timeout constants as generated `const()`s with `@tunable` (like `_DNS_TIMEOUT_MS`, `:20-27, 346-352`); the `SettingsGroup` line(s) in `_emit_webserver()` conditional on `"mqtt" in have` (`:643-662`); status exposure (§6). Import line is automatic per module. | SPEC K.3:6799-6843; N.1:7918-7923 |
| `buildgen/graph.py` | Construction-order edge(s) to mandatory infra are hardcoded by driver name (`if spec.driver in ("sgp40", "notification"): deps[spec.key].add("ntp")`, `:60-62`) — add `deps[mqtt].add("conn")` (and `"ntp"` if it takes `ntp.ntp_issynced`). `@wiring` cannot reference `conn`/`ntp` (they are not instances). | `graph.py:39-111`; SPEC C.14.2:2805-2812 |
| `buildgen/definitions.py` | Networking group (explicit `_mandatory_group(...)` in `_networking_section`, conditional), errcount catalog rows, status fields; the mock and samples follow. | `definitions.py:105-138, 407-421, 497-557` |
| `buildgen/error_catalog.json` | New owner band + every code with name/text. | SPEC C.7.1 |
| `buildgen/validate.py` | Any new build-time refusal (e.g. lwIP budget incl. the outbound connection, a TOML-provided port range) — build tooling must "abort immediately with a clear, human-readable message" (owner, 2026-09-09) and every abort gets its own test with a malformed fixture. | SPEC L.5:7379-7470 |
| `buildgen/twin_wiring.py`, `pico_gpio.py` | No change expected (no pin, no bus). | SPEC K.3 items 5-6 |
| `devices/<chosen>.toml` | `[[instance]] driver = "mqtt"` + `[instance.wiring] fram_target = "fram"`; wiring facts cited to a real source; "only to the real devices that actually carry this" (K.7); no credentials (§4.4). | SPEC K.7:6938-6956 |
| `tests_scripts/test_device_tomls.py` | `_ALWAYS_PRESENT_DRIVERS`/`_DEVICES_WITH_*` allow-list, `_SINGLETON_DRIVERS`, `_FRAM_WIRABLE_INSTANCE_DRIVERS`; a `test_mqtt_only_present_on_<x>` in the `test_isl29125_only_present_on_dev` shape ("never let a new instance land on a device by omission of a check"). | `test_device_tomls.py:20-40, 306-325, 417-428`; SPEC K.6:6904-6906 |
| `tests_scripts/buildgen_fixtures/novel_combo.toml` | Exercise the driver in the synthetic fixture too. | SPEC K.6:6907-6908; L.1:7076-7084 |
| `tests_scripts/test_buildgen_driver_registry.py` | It pins `SINGLETON_SERVICE_DRIVERS == {"fram","neopixel","notification"}` (`:94`) → update deliberately. | |

### 7.3 Generated outputs affected

- `build/generated_src/sensortask_<device>.py`: globals, construction line, `setup()` batch entry,
  collectors, `_flush_pending_configs()` (picks up `cfgmgr` via `getattr`), webserver `RouteSources`
  (`codegen.py:285-532`). Frozen-module set: the instance's module joins by seed + import closure
  (`frozen_modules.py:64-77`); a mandatory module would need `CORE_MODULES`.
- `build/generated_src/definitions/<device>.json` and the staged website (K.8 says read them for every
  device carrying the driver).
- Wiring plan JSON for the twin (unchanged shape).
- Generation is build-time only, never committed; CI regenerates all six devices (SPEC L.2:7096-7101).
- `@requires` is bus-only (`bus.<field><op><value>`, L.6.4) — not applicable to a network service.
  `@limits` only for documented value domains (L.6.4:7579-7583).

## 8. Shared primitives (Part G) — reuse, never re-implement

Must reuse (SPEC G.1:5029-5040 "If a match exists, use it directly, never reimplement even a version
that looks locally simpler"):

| Need | Primitive | Source |
|---|---|---|
| Base class + config + error streak + fan-in | `SensorReaderConfig` (as `WifiService`/`NTPClient`/`NotificationService` do) or the `SystemService`/`CaptiveDNS` duck-typed shape | `asy_base_classes.py:273-626` |
| Logger / history / FRAM | `make_logger()`, `LogConfig`, `DEFAULT_LOG`, `PrintLogHistory(Store)`; `ErrorLog` type | `asy_print_log.py:296-322`; SPEC G.2:5066-5079 |
| Config store, coercion, naming | `ConfigManager`, `type_or_range_error`, `checked_int/float/numeric`, `compare_before_write`, `instance_name`, `config_filename`, `name_cfg`, `schema_names`, `schema_dict`, `make_dict(..., name=self.name)` | `asy_config_manager.py`; SPEC G.2:5044-5048, 5190-5195 |
| Setter orchestration / REST envelope | `_set_dict_cfg`/`_set_mgr_cfg`/`_push_callbacks`, `SettingsGroup`, `handle_set_cmd`, `make_response` | SPEC C.5.2-C.5.3; G.2:5049-5053 |
| Callback guarding | the `_dispatch_*` shape: validate, `try/await`, `except Exception` → `err_s(..., errno=_ERR_CALLBACK)` → `"Failed"` | SPEC G.2:5049-5051; `asy_webserver_service.py:546-594` |
| Shared mutable state | `LockedCounter` (saturating at `COUNTER_CAP`, allocation-free, `tests_scripts/test_counter_steps.py`), `LockedFlag`, `LockedValue`, `Lockable` | SPEC G.2:5055-5060 |
| Elapsed time / UTC | `TickSeconds`, `utc_now()`, `arm_tick_timer()` | SPEC G.2:5061-5069 |
| Buffers | `LockableBuffer` (one allocation per logical record, `memoryview` regions, paired `write/write_into`, `read/read_into`; failed allocation → `None` buffer, consumer checks first) | SPEC G.2:5096-5134 |
| DNS | `asy_dns_client.resolve_ipv4(host, servers, timeout_ms=, tries=)` (never raises; DHCP server first, then 8.8.8.8/1.1.1.1) | `src/asy_dns_client.py:99-131` |
| Timeouts | `asyncio.wait_for_ms(<single awaitable>, <timeout_ms>)`, timeout a caller parameter, mapped to the documented sentinel | SPEC F.2:4194-4201 |
| Config namedtuples | `NtpTiming`/`WifiConfig` shape | SPEC G.2:5196-5200 |
| Fan-in | `get_error_sources()`/`get_loggers()` | SPEC C.14.3; G.2:5178-5181 |
| Watchdog | never touched by the service (`feed_watchdog()` is boot/supervisor-only) | SPEC G.2:5182-5189 |
| Streaming responses | `_stream_dict_response`, `_PieceWriter` (if a route grows) | SPEC G.2:5155-5160 |

Duplication risks an MQTT library would introduce (each a G.3 "candidate migration" / D.10 issue):
- its own DNS resolution via blocking `socket.getaddrinfo()` (duplicates `resolve_ipv4`, violates F.2);
- its own WiFi connect/reconnect (duplicates `WifiService`, §3.3);
- its own logging/`print`/debug flags (duplicates `PrintLog`, violates `no_print` and the error catalog);
- its own retry/backoff timers or `time.sleep` (violates never-block; duplicates the C.9 backoff shape);
- its own `gc.collect()` calls (forbidden);
- its own "status" dict building / JSON (duplicates `make_dict`/streaming);
- an `asyncio.Lock` + bare variable state (G.2 says use the `Locked*` primitives);
- ad-hoc timeouts with `asyncio.wait_for` in seconds (project form is `wait_for_ms`, ms parameter).
No existing primitive covers TCP client streams; the closest precedents are the webserver's
`_TimeoutStreamProxy` (per-call bounded reads/writes, peer-gone handling after an `OSError` read,
`asy_webserver_service.py:247-309`) and `UDPSocket` (never-raise transport). A reusable TCP-client helper,
if built, must be added to G.2 in the same change (G.1:5037-5040).

## 9. Other binding requirements

### 9.1 Never block

- **HARD** No blocking I/O, `time.sleep`, or unbounded loops; I/O must be async and yield (SPEC D.5:2936-2939;
  F.3:4261-4271; CLAUDE:236-238). Synchronous waits are a Part N rule row (`loop.sync_wait_max_us`:
  sub-millisecond, SPEC:~8858).
- **Fact** `open_connection()` → blocking `getaddrinfo` (use a numeric IP); its connect wait has no timeout
  (wrap); TLS handshake is deferred to the first I/O (`do_handshake_on_connect=False`) and `server_hostname`
  defaults to the host argument (pass it explicitly if TLS) (`extmod/asyncio/stream.py:99-123`).
- **Fact** `Stream.readexactly()` allocates and concatenates per call; `Stream.readinto(buf)` is the
  non-allocating form; `write()` concatenates `out_buf` on partial writes; `drain()` yields
  (`stream.py:24-96`).
- **Fact (lwIP)** When `MEM_SIZE` is exhausted `modlwip.c`'s write retries `tcp_write()` up to 200 × 50 ms,
  **blocking the whole VM up to 10 s even on a non-blocking socket**, past the 8 s watchdog; "never observed
  on silicon" with HTTP alone (SPEC B.14.2:1371-1378). A persistent publisher adds outbound arena demand.
- **HARD (analogy)** The UART modules' sharper "never block, not even in a wait state" rule
  (CLAUDE:247-264) is scoped to UART; its F.5.9 lesson (an idle poll loop is a permanent CPU cost) applies
  to any hand-rolled `ipoll`+`sleep` reader — prefer asyncio stream waits (event-driven) over the
  `UDPSocket._poll` style (`asy_udp_socket.py:127-136`, 20 ms rounds).

### 9.2 Timeouts and tunables (Part N)

- **HARD** "Define the timeouts per service … Only the individual timeouts need to be set as parameter"
  (owner, 2026-07-28, `5ddbcd3`): the generated module's constants are the parameters the firmware runs
  (`dns.timeout_ms`, `dns.tries`, `ntp.fetch_timeout_ms`); a `src/` default of the same value is a further
  site of the same row; summed/dependent timings are computed in the generated module, never inside a
  service (SPEC N.1:7918-7923).
- **HARD** Every tuned value carries `# @tunable <area>.<name> = <literal>` directly above it **and** a Part N
  row (ID, Value, Sites, Dependants, Basis, Margin, Re-check trigger) in the same change; an unmeasured
  value's Basis is `estimated (agent, <commit>) — measurement owed: <how, level>` (owner, 2026-09-25)
  (CLAUDE:792-793; SPEC N.1-N.2:7894-7975; `tests_scripts/test_tunables_register.py`). Config values set by
  TOML/REST are class *config* and are not tagged; protocol constants are *fact* (SPEC N.1:7909-7913).
- **HARD** Relations checked by the register test (e.g. `system.task_check_s` vs watchdog); new timeouts must
  respect the watchdog and the webserver's `outer_cap_s` where they interact (SPEC N.2:7955-7959).

### 9.3 Network resource budgets

- **HARD** lwIP ensemble: `MEMP_NUM_TCP_PCB >= max_connections + 3` (closing pcbs hold slots; FIN_WAIT not
  reclaimed), `MEMP_NUM_TCP_SEG >= max_connections × TCP_SND_BUF/TCP_MSS`, `MEM_SIZE/max_connections >= 2000 B`;
  `buildgen/validate.py` refuses a device the pools cannot serve; values in `toolchain/versions.toml [lwip]`
  (each a Part N `lwip.*` row) (SPEC B.14.2:1274-1440; H.7:5498-5520). The checks have **no term for an
  outbound client**. A connection costs **2,324 B of GC heap** in pool terms; an open HTTP connection ~7.5-8 KB
  of live heap at peak (SPEC:1418-1423, 5550-5553).
- **HARD** Changing `toolchain/versions.toml` needs the chroot verification note in BACKLOG.md **and** the
  separate toolchain-installer verification (CLAUDE:922-1098, 1100-1106).
- **Fact** `MEMP_NUM_UDP_PCB = 5` shared by NTP, the DNS resolver and the captive DNS server; an MQTT DNS
  lookup takes one transiently.
- **Fact** The digital twin has **no lwIP** (real host sockets): it cannot validate a PCB ceiling (SPEC
  H.7:5574-5584).

### 9.4 Test obligations (every tier)

- **HARD** Unit tests under the real MicroPython Unix port (`tests/test_asy_<name>.py`, `tests/microtest.py`),
  D.12's per-parameter/combination/boundary/NaN±inf coverage; integration through the real chain to the real
  consumer (SPEC D.12:3010-3020; E.1-E.3; CLAUDE:589-614).
- **HARD** Any fake for a poller/stream must be a **bounded fake** (`_StepPoller` shape), never backed by a real
  `select.poll()` on a non-fd object (hangs on GitHub runners) (CLAUDE:671-679). Never call `asyncio.run()`
  from inside a coroutine in tests (segfault) (CLAUDE:708-723).
- **HARD** "A new device on a shared resource — … every other shared resource (locks, FRAM, the config file,
  sockets, the heap) — gets hazard test coverage across all four test tiers … never forget this" (owner,
  2026-09-03 `da3a5b5`; extended 2026-09-26) (CLAUDE:265-278; SPEC C.8:2347-2440). For MQTT: concurrency
  with the webserver at its connection ceiling (sockets/pcbs/heap), with NTP (`wifi_mode_lock`, UDP pcbs),
  FRAM log writes, the config file (PUT vs flush).
- **HARD** Digital twin: per-device L2 boot of the real graph, both GC stages, zero memory markers
  (`scripts/run_digital_twin_ci.sh <device>`); Driver/DUT process separation — a test broker and request
  drivers live host-side (CPython), never inside the twin's heap (owner, 2026-09-25) (SPEC E.9:3752-3806;
  K.10:6985-7000).
- **HARD** Real hardware (L3/L4) only with the owner's go-ahead given in that session (CLAUDE:318-328); no
  avoidable wear (CLAUDE:279-317); bench network changes need the dead-man's switch (CLAUDE:329-341).
  A bench broker would be new bench infrastructure.
- **HARD** Containment: L3 ∪ L4 ⊇ L2 scenarios, each L3/L4 module names the twin scenarios it covers
  (`COVERS_TWIN_SCENARIOS`, `tests_scripts/test_level_containment.py`), exceptions are rows of E.6.6 (SPEC
  E.6.1-E.6.2:3493-3536).
- **HARD** `tests_scripts` gates that will fire on this change: `test_code_conventions`, `test_comment_block_cap`,
  `test_import_placement`/`test_import_graph`, `test_task_inventory`, `test_lock_order`, `test_error_catalog`,
  `test_fault_or_warning_never_both`, `test_tunables_register`, `test_readiness_gates`, `test_setter_contract`,
  `test_counter_steps`, `test_gc_collect_sites`, `test_watchdog_feed_sites`, `test_config_schemas`,
  `test_stored_config_golden`, `test_request_body_cap_headroom`, `test_device_tomls`,
  `test_buildgen_driver_registry`/`_generate`/`_definitions`/`_web_tag`, `test_definitions_js_mirrors`,
  `test_no_variant_literals`, `test_decision_vocabulary`, `test_citations`, `test_exception_handler_contract`,
  `test_ticks_wrap_scan` (any `ticks_*` use), `test_memory_error_gate_agreement` (injected exception wording).

### 9.5 Bird's-eye scan and D-checklist

- **HARD** Adding a file to `src/` triggers a whole-`src/` consistency scan (D.10, D.9) and Part G.3's
  grep-for-the-shape; a consistency discrepancy is fixed directly and logged ('Change, don't flag, if not
  according', owner 2026-09-25); a formula/behaviour discrepancy is flagged first (CLAUDE:90-101).
- **HARD** Part D in full (D.0-D.16) before landing in `src/`; D.9: check against current MicroPython (v1.29.0)
  and current Microdot docs, never memory (CLAUDE:29-31).

### 9.6 Documentation and decision records

- **HARD** Every decision statement names actor and date; owner decisions quote the owner (or are marked
  "paraphrase"); agent recommendations stay the agent's; owner questions go only into BACKLOG.md's one
  numbered "Owner questions" list (decision ≤10 words, options with per-device consequences); "flagged for the
  owner"/"owner's call"/"revisit" appear nowhere else; `test_decision_vocabulary.py`/`test_citations.py` gate it
  (CLAUDE:450-464; BACKLOG.md:885-888).
- **HARD** Docs hold current state, targets and rules — not history; BACKLOG is working memory, pruned on
  resolution (CLAUDE:442-449).
- **CONV (K.9)** Docs to update: SPEC C.7.1 band row, C.8 lock table (if a lock), C.9 task table (if an
  unsupervised task), A.7 construction/FRAM chunk order, A.8 REST reference (new `/networking`/`/status`
  fields), F.2 (a second `getaddrinfo` call site, numeric-only), H.6/H.7, I.6 quoted body figure, N rows,
  `DEVICE_REFERENCE.md` (user-configurable behaviour), `THIRD_PARTY_LICENSES.md` (any derived code),
  `digital_twin/README.md` (fake broker).

### 9.7 Workflow (how the work must be run)

- **HARD** Research and cross-check first; owner questions only at requirement recording or a consolidation
  run, never during execution; tests first, then implementation, then coverage tests; a "pause" = commit,
  push, full local suite at both GC stages, CI green via hooks only; an unforeseen decision during execution
  takes the more conservative, more reversible option and is logged as decided on the owner's behalf; CI
  failures are never ignored (CLAUDE:500-517).
- **HARD** PRs may be opened proactively; always with a meaningful description; subscribe to PR activity
  (CLAUDE:1107-1115).

### 9.8 Device policy

- **HARD** WoZi is the exemplary/base variant, never flashed; correctness via mock/twin/unit tests only; dev is
  the only flashed board, and a dev-bench result counts for wozi only if the code is dev-native (CLAUDE:174-186).
  `dev` meets every device's bar (CLAUDE:172-173). Feature parity goal: same top-level features as the legacy
  units, "not a feature change" (CLAUDE:434-441) — MQTT is a **new** feature, so its scope is the owner's.

### 9.9 Legacy

- **HARD** `legacy/` is reference-only forever; no work of any kind; no MQTT exists there (CLAUDE:187-206).

### 9.10 Third-party code policy (if a library is used)

- **Fact** `umqtt` is **not** frozen into the pinned image: `RPI_PICO_W/manifest.py` requires
  `bundle-networking`, which at the pinned micropython-lib commit `ee4bb8f` contains only `mip, ntptime, ssl,
  requests, webrepl, urequests` (verified against upstream source). So any MQTT code must be in `src/` or
  vendored in `ext/`.
- **HARD** `ext/` = plain, unmodified upstream at a pinned tag/commit, "no edits, no restyling, ever" (owner,
  2026-09-25), behaviour changes only by wrapping; refreshed in the all-dependencies step; licence text kept
  (CLAUDE:114-127, 52-61). A vendored client that blocks, calls `getaddrinfo`, manages WiFi, prints or
  `gc.collect()`s cannot be fixed in place.
- **HARD** Vendor-derived code has a **per-vendor policy** (Adafruit: rewrite allowed with attribution;
  Sensirion: literal port; Microdot: hands-off) (SPEC F.4:4273-4300; CLAUDE:232-235). A new vendor's policy is
  undecided. Precedents for "inspired by / derived, rewritten in `src/` with attribution + SPDX header +
  THIRD_PARTY_LICENSES entry": `asy_dns_client.py:1-3` (aiodns), `asy_udp_socket.py:1-3` (karfas),
  `asy_captive_dns.py:1-3` (Apache-2.0, changes listed), `asy_ntp_client.py:1-3` (micropython-lib ntptime).

## 10. Best template(s) to copy the shape from

1. **`src/asy_ntp_client.py` → `NTPClient`** — the closest overall: a `SensorReaderConfig` network client
   that is not a sensor; owns a persist-only schema (`config_NTP.cfg`) exposed through a `/networking`
   `SettingsGroup` with a `post_asy_fct`; takes `WifiService`'s lock and bound methods at construction; reads
   the DNS server outside the lock; resolves via `resolve_ipv4()`; never gives up (`max_module_error=0`,
   backoff, C.7.2); timing via a generated namedtuple (`NtpTiming`) whose values are generated `const()`s with
   Part N rows; status via a `get_data()` namedtuple (`NTP(Synced, LastSyncAge, TS)`).
2. **`src/asy_notification_service.py` + its buildgen plumbing** — the template for being an **optional
   singleton `[[instance]]`** resolved through `_OVERRIDES`, with conditional codegen
   (`if "notification" in have`), its own definitions section/group, errcount rows, and a hardcoded
   construction-order edge to `ntp` in `graph.py`.
3. **`src/asy_uart_link_driver.py` → `UARTLinkDriver`** — template for a non-reader service that reports live
   counters through `maintenance_sensors` without touching the webserver, and delegates fan-in.
4. **`src/asy_captive_dns.py` → `CaptiveDNS.run()`** — template for a never-dying network loop: catch-all top,
   `CancelledError` handling, backoff on sentinel failures, clean teardown with a persisted warning.
5. **`src/asy_webserver_service.py`** — the only TCP user: per-call bounded stream I/O, peer-gone handling,
   close/`wait_closed` discipline, never raising out of a connection task.

## 11. Open questions the owner should decide (before execution, per CLAUDE:500-517)

1. **Placement and devices**: optional `[[instance]]` singleton (REC) vs mandatory infra; which devices —
   dev only (bench-testable), dev + wozi (wozi is the validated base but "never gets a … not-yet-deployed-
   everywhere [module] just because dev does", K.7), or all six?
2. **Implementation source**: own minimal MQTT 3.1.1 client in `src/` (meets every rule; precedent for
   "inspired by" rewrites) vs an `ext/` vendored library (cannot be edited; known candidates block, call
   `getaddrinfo`, manage `network.WLAN`, print and `gc.collect()`); and the vendor policy for any derived code.
3. **Transport security**: plain TCP 1883 vs TLS 8883 (`ssl` is frozen; mbedtls heap cost unmeasured here;
   certificate validation needs NTP time and a CA/cert stored somewhere — never committed).
4. **Credentials/threat model**: plaintext broker password on flash and (without TLS) on the LAN; acceptable
   under the trusted-home-LAN model (as accepted for WiFi/hotspot)? Optional credentials vs the UI's "empty
   string can't be set" gap.
5. **Connection budget**: count the persistent outbound connection in the lwIP ensemble (raise
   `MEMP_NUM_TCP_PCB`/`MEM_SIZE`, `versions.toml` change + re-verification) or lower `max_connections` to 5;
   re-measure H.7's peak-heap evidence with a live MQTT session either way.
6. **Status exposure**: `maintenance_sensors` entry (least invasive) vs extra `networking` status fields vs a
   new `/status` section (webserver + JS change).
7. **Enabled by default?** (REC: off/empty host, so twin and bench baselines stay clean.)
8. **PoC behaviour**: what to publish (heartbeat? measurements?) and at what period; which topics to subscribe;
   what happens to received messages (counted/logged only?); QoS 0 only?; retain/LWT/clean-session; client-id
   derivation (hostname?).
9. **Failure semantics**: never end the task (REC, C.7.2) vs a streak; broker-unreachable as warning or error;
   catalog band numbers.
10. **Reconnect trigger**: should a `/networking` PUT of MQTT fields force a reconnect (`post_fct`, like
    WiFi/NTP)? Should an orderly MQTT DISCONNECT precede commanded reboots (new hook)?
11. **Bench infrastructure**: a broker on the bench Pi4 for L3/L4 (new host package/service; owner go-ahead,
    dead-man's-switch rules if network config is touched).
12. **Keepalive vs WiFi recovery**: confirm MQTT link loss must never drive WiFi recovery (status quo,
    owner 2026-09-04) — it only reconnects its own socket.

## Appendix A — Minimal contract of the service class (derived checklist)

```
class MQTTClient(SensorReaderConfig):            # or duck-typed like SystemService
    __init__(wifi_mode_lock, network_available_locked, get_dns_server, timing: MqttTiming,
             cfg_path="", log=DEFAULT_LOG)        # no I/O; logger+cfgmgr drawn here (2 FRAM chunks)
    _connection_loop()                           # one supervised task; never ends; backoff; closes socket in finally
    get_task_starters() -> [self.start_asy_connection]
    get_timer_starters() -> []                    # or arm_tick_timer-based starters
    start_asy_connection() -> create_task(self._connection_loop())
    get_data() -> MQTT(Connected, ..., TS)        # namedtuple type name == _NAME
    get_dict_cfg() -> _get_dict_cfg(self.name, schema, callback=self._mask_pw)
    get_dict_data() -> make_dict(data, _FIELDS, name=self.name)
    get_error_counter() -> await self.pr.get_log()
    get_error_sources() -> [self, self.cfgmgr];  get_loggers() -> [self.pr, self.cfgmgr.pr]
    reset_error_counter() -> bool
    setup() -> bool                              # logger then cfgmgr; no network
    reconnect()                                   # post_fct for the settings group (sync, sets a flag)
```
Plus: `# @wiring fram_target FRAMManager log optional kwarg`, `# @web-group`/`# @web` tags, `_VAL_*` schema,
`_ERR_*/_WRN_*` consts in a new catalog band, `@tunable` lines with Part N rows.
