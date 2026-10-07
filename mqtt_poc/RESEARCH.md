# MQTT proof of concept — research and requirements

**Status: RESEARCH, 2026-10-07 (agent).** No code has been written and nothing has been decided. This file
consolidates one research round so the owner can answer the questions in section 8 before any design work
starts. **Temporary**: like `PROJECT_AUDIT_PLAN.md`, it is deleted once the PoC's lasting outcomes
(code, settled decisions, new rules) have migrated into `SPECIFICATION.md`, `CLAUDE.md` or `BACKLOG.md`.

**Branch.** `claude/whole-project-audit-plan-followup`, branched from the audit branch at `1cff5a2` (U14). The
owner (2026-10-07) on why it branches from the audit: "The audit is a very moving target at the moment, and we
don't need to track every move. But it contains valuable details". The work itself is unrelated to the audit.

**The owner's request (2026-10-07, quoted):** "Adding MQTT capabilities to the system, just as a driver /
available service, not used at any place at that point, only a proof of concept." "publishing and
subscribing should both work, and it must be fully compatible to our framework. Maybe nothing fits
perfectly, and we will have to change or extend such modules to fit." The asked-for steps: survey asyncio
MQTT clients; deep-dive how they work; get a detailed view of this project's requirements; find the best fit
("probably the Peter Hinch one … but maybe there are surprises out there?"); state what would still be
missing.

**Evidence.** Six read-only research reports in `mqtt_poc/research/` (`01`–`06`, about 46,000 words with
file:line references) are the evidence base. This file condenses them. The claims this file's conclusions
rest on were re-checked directly in source by the session that wrote it; they are marked **[V]**. **[R]**
means reported in an upstream issue or forum thread and not reproduced; **[I]** means inference. Nothing
was run on hardware.

| Report | Scope |
|---|---|
| `research/01_landscape.md` | Every asyncio-capable MicroPython MQTT client found, field reports (Pico W focus), ranking |
| `research/02_mqtt_as_deep_dive.md` | Line-by-line read of `peterhinch/micropython-mqtt` at `dd03ab3`, including its issue tracker |
| `research/03_platform_facts.md` | MicroPython v1.29.0 / lwIP / CYW43 / mbedTLS facts for a long-lived TCP client |
| `research/04_integration_requirements.md` | What a new service must satisfy to fit the framework (shape, lifecycle, WiFi, config, REST, build) |
| `research/05_sockets_memory_testing.md` | Socket/PCB inventory and budget, heap discipline, the four test tiers and their gaps |
| `research/06_audit_pillars.md` | Audit pillars, owner requirements and policies that bind a new network service |

---

## 1. Bottom line

1. **Nothing existing fits unmodified.** Every asyncio MQTT client for MicroPython either blocks the event
   loop, manages `network.WLAN` itself, runs `gc.collect()` in its own loops, or is broken in a way
   the source shows (sections 2–3).
2. **Peter Hinch's lineage is the best existing code, as expected — and its own author wants it rewritten.**
   `mqtt_as` is the only maintained, field-proven candidate. But the classic variant owns the WiFi radio
   and drops it on every broker outage **[V]**. The new `mqtt_as_eth` variant (added 2026-09-27) leaves WiFi
   alone, but it is three weeks old, still changing daily, untagged, and keeps the internal model (1 Hz
   `gc.collect()`, 5 ms socket polling, fire-and-forget tasks, `OSError`-only recovery) that collides with
   this project's rules **[V]**. Its author wrote in 2024 that "a rewrite is called for", separating the
   transport from the client (`FUTURE_DEVELOPMENT.md`, `837a748`) **[V]**.
3. **Surprise candidates exist, but none beats it.** Nine further asyncio clients were read in source. The
   only notable surprises: tve's `mqtt_async` never sends a keepalive ping (a `return` is missing in
   `isconnected()`, `mqtt_async.py:355-356`) **[V]**; `aiomqttc` does not parse at its GitHub head; the open
   micropython-lib PR #1086 (`umqtt.async`) sends malformed QoS 1 publishes; and `micropython-holdfast` (2026)
   has good resilience patterns on top of a blocking client. No MicroPython client supports QoS 2; only
   `mqtt_as` has (partial) MQTT v5.
4. **Recommendation (agent, 2026-10-07): a project-owned, minimal MQTT 3.1.1 client in `src/`**, QoS 0 and 1
   in both directions, clean session, plain TCP — built from the project's own primitives (DNS, timeouts,
   supervision, logging, config, buffers) and using `mqtt_as` as the reference for its field-proven protocol
   behaviour (ping scheduling, QoS 1 retransmission with DUP), with MIT attribution wherever code is
   derived. Reason: once everything in `mqtt_as` that conflicts with the framework is replaced, what remains
   is the packet codec — the easy part. The connection/session management that would have to be rewritten
   anyway is exactly the part this framework already prescribes. The alternative routes and their costs are
   question 8.1.
5. **Platform facts bind any client, whichever route is chosen** (section 4): lwIP has no TCP keepalive here
   and a WiFi link drop does not abort a TCP connection, so the MQTT ping deadline is the only dead-link
   detector; a send into an exhausted lwIP buffer freezes the whole VM for up to 10 s (past the 8,388 ms
   watchdog); `asyncio.open_connection()` resolves DNS synchronously, has no timeout and leaks the socket on
   cancellation; cancelling one waiter on a stream silently strands the other direction; TLS costs about
   21 KB of contiguous heap per (re)connect and a blocking handshake measured at 7–8 s on Pico W.
6. **The lwIP ensemble has no room for it yet.** It is sized for `max_connections = 6` HTTP connections plus 3
   spares. A permanent MQTT connection needs its own share (+1 PCB, +8 segments, +2,000 B `MEM_SIZE`:
   2,324 B of GC heap, matching the project's measured 7-connection row) or `max_connections` drops to 5
   (question 8.4).

---

## 2. Candidates surveyed

Last-commit dates as of 2026-10-07. "Owns WLAN" = calls `network.WLAN` connect/disconnect/active itself.

| Client | Last commit | MQTT / QoS | Owns WLAN | Dead-link detection | Blocking calls in the loop | Verdict |
|---|---|---|---|---|---|---|
| peterhinch `mqtt_as` (classic) | 2026-10-07 | 3.1.1 + partial v5 / 0,1 | **yes** | ping + 1× keepalive deadline | DNS once; TLS handshake | mature; fights `asy_wifi_service.py` |
| peterhinch `mqtt_as_eth` | added 2026-09-27 | same | no | same | same | best existing; very new, still moving |
| zcattacz/mqtt_as | 2025-11 | 3.1.1 / 0,1 | no | yes | DNS once; TLS | 2022 base, no 0.8.x fixes, allocates per read |
| tve/mqboard `mqtt_async` | 2021–22 | 3.1.1 / 0,1 | yes (injectable) | **none — ping never sent** | DNS once | design reference only |
| kevinkk525 fork / pysmartnode / microhomie | old | 3.1.1 / 0,1 | yes | yes | DNS; TLS | superseded by upstream |
| Tangerino/aiomqttc | 2025-05 | 3.1.1 / 0,1 | no | flag only, no reconnect | DNS every connect | HEAD has a SyntaxError |
| Carglglz/asyncmd `async_mqtt` (= micropython-lib PR #722) | 2024 / 2023 | 3.1.1 / 0,1 | no | none | non-blocking TLS path | minimal base only |
| micropython-lib PR #1086 `umqtt.async` | 2026-02 (open) | 3.1.1 / 0,1 | no | none | — | malformed QoS 1 publish; `TypeError` on PINGRESP |
| a-smiggle `umqtt_async`, nznobody `umqtt.uasyncio2` | old | 3.1.1 / 0,1 | no | none | yes | toy-grade |
| micropython-lib `umqtt.simple`/`robust` | 2026-09 | 3.1.1 / 0,1 | no | none (manual ping) | fully blocking | not usable under asyncio |
| fizista `umqtt.simple2`/`robust2` | old | 3.1.1 / 0,1 | no | manual | blocking | reference: bounded outbound queue |
| gregyedlik `micropython-holdfast` (2026) | 2026-08 | via `umqtt.simple` | yes | app-level ACK heartbeat | blocking | reference: resilience patterns |

Excluded on sight (reasons in `research/01_landscape.md` §5.12): tinymqtt (pre-2020 uasyncio API),
chrismoorhouse (`_thread`), Joel-Edem (blocking, breaks above 127-byte payloads), upymqtt (empty), an MQTT-SN
client (`_thread`), beehiveMQTT (a broker). CPython's aiomqtt 3.0 (built on the sans-I/O `mqtt5` codec) is a
design reference only: a pure packet codec separate from transport and session is what makes a client
testable without sockets.

Neither `umqtt` nor any other MQTT client is in the stock Pico W image: the board manifest freezes
`bundle-networking` (mip, ntptime, ssl, requests, webrepl, urequests) and `aioble` only. Whatever route is
chosen, the code is this project's to carry.

---

## 3. Peter Hinch's `mqtt_as` in detail (`dd03ab3`, 2026-10-07)

**What it gets right** (the parts worth learning from): genuinely non-blocking socket I/O in the normal case;
pings at keepalive/4 with a one-keepalive deadline; QoS 1 retransmission with the DUP flag and the same
packet id (`max_repubs`, default 4); a lock per packet write/read, not held while awaiting PUBACK, so
concurrent publishes and a subscribe during a pending publish work; an overwrite-oldest inbound ring with a
`discards` counter; `broker_up()`; an overridable `dprint`; an active, responsive maintainer; years of Pico W
field use. The CYW43 power-save fix it applies (`pm=0xA11140`, issue #88) is already in
`src/asy_wifi_service.py`.

**What blocks adoption in this framework** (file:line in `mqtt_as/__init__.py` unless noted):

| # | Finding | Evidence | Rule it meets |
|---|---|---|---|
| A1 | Classic variant owns the radio: `WLAN.active(True)` in the constructor (`:191-192`), `wlan.connect(ssid, pw)` on every reconnect (`:747`), `wlan.disconnect()` on every outage (`:910`), even when only the broker is down. With `ssid=None` on rp2, `connect()` raises `TypeError` and kills the reconnect task. | [V] | `WifiService` owns `network.WLAN` (SPEC C.8); MQTT must never drive WiFi recovery (CLAUDE.md, owner 2026-09-04/26) |
| A2 | `gc.collect()` every second while connected (`:907`; eth `:855`), plus four at import in the classic variant (`:15-28`) and every 20 s in debug. | [V] | No `gc.collect()` in business logic (CLAUDE.md memory rule; lint + `test_gc_collect_sites.py`, which does not scan `ext/`) |
| A3 | The reader polls: `_handle_msg` wakes every 5 ms for the whole connection (`:843`, the #166 workaround), allocating coroutine objects each pass; partial-packet, connect and CONNACK waits spin on `sleep_ms(0)`. | [V] code; churn volume [I] | Heap-churn discipline (SPEC I.4); "never block" in spirit (SPEC D.5) |
| A4 | `clean=False` (persistent session) can never reconnect: it rejects any CONNACK whose flags byte is non-zero (`:371-372`), but bit 0 there is Session Present, which a broker sets whenever it kept the session. | [V] code; mosquitto `handle_connect.c:115-118` | Correctness |
| A5 | Recovery catches only `OSError` (`:845`, `:925`): a `MemoryError` (#151), `TypeError` or v5 `ValueError` kills the reader or the reconnect task for good; `publish()` then waits forever (`:948-958`). | [V] | SPEC C.7 / D.2; supervision (C.9) |
| A6 | Tasks are fire-and-forget `asyncio.create_task` (`:819-832`), outside the project's supervisor and task inventory; user handler tasks are never cancelled (#147). | [V] | SPEC C.9; `test_task_inventory.py` |
| A7 | `publish()`/`subscribe()` loop until reconnected, with no timeout (`:943-960`); cancelling one mid-write corrupts the stream. QoS 0 messages in the detection window are lost or sent late (#185). | [V] | Never block a caller indefinitely; bounded queues |
| A8 | DNS: `socket.getaddrinfo(server)` once on first connect (`:790`), cached for the client's lifetime. TLS: `ssl.wrap_socket()` with a blocking handshake by default (#171: watchdog reset). | [V] | SPEC F.2: `getaddrinfo` only on a numeric host; never block |
| A9 | Self-inflicted reconnects: a late PUBACK beyond `response_time` causes a re-send, the second PUBACK raises "Invalid pid" and forces a reconnect; a SUBACK/PUBACK rejection code also forces one. Retries every 1 s with no backoff. | [V] code | Capped exponential backoff (SPEC C.7.2/G); lwIP PCB churn (section 4) |
| A10 | `mqtt_as_eth` specifically: invalid `package.json` that lists a missing file; `_lan_connect()` calls a `wan_ok()` that exists only in the classic variant; the rp2 `-110` "busy" errno handling was dropped; three commits in the last ten days. No tags or releases anywhere in the repo, no CI. | [V] | `ext/` pins an unmodified upstream tag or commit (CLAUDE.md) |

Under the `ext/` policy ("no edits, ever"), A2, A3, A5 and A6 can only be removed by subclassing and
overriding private methods (`_keep_connected`, `_handle_msg`) of a library that is changing weekly — the
override would carry most of the library's logic while still depending on its internals.

---

## 4. Platform facts that bind any MQTT client (MicroPython v1.29.0 on rp2)

From `research/03_platform_facts.md` and `research/05_sockets_memory_testing.md` (source refs there). The
four marked [V] were re-checked directly against the `v1.29.0` tag.

1. **No dead-link detection from the stack.** `LWIP_TCP_KEEPALIVE` is 0 and `modlwip` has no keepalive
   `setsockopt` case. A CYW43 link drop only sets the netif link down: an idle connection stays ESTABLISHED
   forever, one with data in flight aborts only after ~19–38 min. **The MQTT PINGRESP deadline is the only
   practical detector** — which also makes MQTT the first component able to notice the accepted CYW43
   `isconnected()` false positive (question 8.9).
2. **What WiFi events do to a connection.** `active(False)`/`deinit()` (the project's STA↔AP switch, which
   also replaces the `WLAN` object) aborts every TCP connection with `ECONNABORTED`; the plain
   `disconnect()`/`connect()` reconnect does not, and a DHCP renewal to the same IP lets the old connection
   survive silently.
3. **Connect.** A non-blocking `connect()` raises `EINPROGRESS` after ~1 ms. No route → `EHOSTUNREACH`
   immediately; no free PCB → `ENOMEM`; a refused port → `ECONNRESET`; an unanswered SYN aborts after
   ~18.5 s with `ECONNABORTED` (6 retries, 3 s each, ICMP ignored).
4. **`asyncio.open_connection()` is unsuitable as-is [V].** It calls `socket.getaddrinfo()` unconditionally
   (`extmod/asyncio/stream.py:103`, "TODO this is blocking!"), has no timeout, returns a stream even when the
   connect later fails, and leaves the socket to the GC finaliser if cancelled. **`Stream.close()` is a no-op
   [V]** (`stream.py:16-17`); only `wait_closed()` closes.
5. **Cancelling one waiter strands the other [V].** `IOQueue.remove()` drops the socket's whole poll entry
   when *either* waiting task is cancelled (`extmod/asyncio/core.py:100-111`), so a reader and a writer on
   one stream must never be cancelled independently (e.g. a `wait_for` around a drain). Not in
   `SPECIFICATION.md` yet; no upstream issue found.
6. **The `ERR_MEM` stall [V].** When lwIP's send memory is exhausted, `modlwip` retries `tcp_write` 200 × 50 ms
   — a 10 s VM freeze even on a non-blocking socket (`extmod/modlwip.c:795-813`), past the watchdog cap. A
   broker that stops reading is exactly the trigger. The audit plans a build override for this (OR112/114/
   115, unit U21), not at HEAD. Until then: small packets, and `MEM_SIZE` that grows with the connection
   count.
7. **DNS.** `getaddrinfo` on a name blocks for lwIP's DNS schedule (~7 s per server, ~14 s with two). On an
   IPv4 literal it returns at once. The project resolver (`asy_dns_client.resolve_ipv4()`) is unicast
   A-records only, so a `*.local` broker name would need new code.
8. **Receive path.** Unread data sits in the shared 16-pbuf pool (892 B each), not the GC heap; there is no
   per-connection quota, so a burst of small segments (e.g. retained messages after SUBSCRIBE) can hold all
   16 and make the driver drop every inbound frame — HTTP SYNs and ARP included — until Python drains.
   `read(n)`/`recv(n)` allocate n bytes up front; `readinto()` into a preallocated buffer allocates nothing.
9. **TLS.** Works with `do_handshake_on_connect=False` (asyncio then drives it), TLS 1.2 max, but needs a
   16,717 B and a 4,429 B contiguous GC block on every (re)connect — the largest free block at serving
   peak is about 1.5 KB (H.7). Certificate dates are checked against the RTC, which reads 2021 until the
   first NTP sync. Field-measured Pico W handshakes: P-256 7.2 s, RSA-2048 8.0 s (Discussion #10559) [R].
10. **The Unix port cannot model** `ECONNRESET`/`ECONNABORTED` semantics (it reports `ECONNREFUSED` and kernel
    timeouts), link loss, pbuf/PCB pool limits, the NULL-pcb write or the `ERR_MEM` stall. Those need bounded
    fakes that script rp2 states, or the dev bench.

**Field reports worth a bench check** (`research/01_landscape.md` §6): publishes stalling above ~125-byte
payloads on Pico 1 W with umqtt *and* mqtt_as (micropython-lib #994, open) [R]; `ECONNABORTED` while
`isconnected()` is True since v1.24 (micropython #16290) [R]; Peter Hinch on the official clients under WiFi
outages: "only held up for about 30 minutes" (Discussion #9530) [R].

**Spec items that look stale** (found by the research, not changed on this branch since the audit owns them):
SPEC F.2 cites `modlwip.c:1866`, the lwIP-1.x branch (the compiled call is `:1868`), and its "#18797 fixed"
holds but the fix only bounds the block to lwIP's DNS schedule; the `isconnected()` false-positive wording
could name the partial upstream fix (#16482, closed by PR #16914, cyw43-driver v1.1.0) [R, not re-checked
here]; Part F.1 lacks the cancellation fact in item 5; Part B.14.2's reason for keeping `PBUF_POOL_SIZE`
("one small request per connection") does not hold for a subscriber.

---

## 5. What the framework requires of an MQTT service (condensed)

Full catalogue with citations: `research/04_integration_requirements.md` (shape, lifecycle, WiFi, config,
REST, build), `research/05_sockets_memory_testing.md` (sockets, memory, tests), `research/06_audit_pillars.md`
(pillars and owner requirements). The items most likely to be gotten wrong:

**Shape and lifecycle.** `src/asy_mqtt_client.py`, class `MQTTClient` (C.2 naming; D.15 member order; 3-line
comment cap; mypy strict; no explicit `Any`; at most 8 constructor arguments, grouped values in a
namedtuple built by generated code like `NtpTiming`; fixed tail `max_module_error=5, name_ext="",
cfg_path="", log=DEFAULT_LOG`). Sync `__init__` stores arguments and draws its logger and `ConfigManager`
(two FRAM chunks, built once, never again on reconnect); async `setup() -> bool` runs in the one-time boot
batch, so no networking there. One long-running task from `get_task_starters()`; any other `create_task`
must be a row in SPEC C.9's table. No test seams in product code (OR36.a).

**Self-healing ladder** (CONSOLIDATION P1–P3; SPEC C.7.2; OR18.a). A remote fault — broker down, refused,
garbage, DNS failure — is handled in place with a capped exponential backoff (never zero, reset on first
success) and never ends the task: each task end costs 100 of the supervisor's 300 restart budget, so about
three lead to a reboot. NTP is the precedent (10 s doubling to 600 s, never ends). The task ends only for a
local fault, and only when its restart re-initialises something real. Self-probes and periodic restarts are
ruled out (owner, 2026-08-03 and 2026-09-04/26).

**WiFi interplay.** `WifiService` owns the radio under `wifi_mode_lock`; dependants get bound methods, not
events: `get_wifi_mode_lock()`, `network_available_locked()` (caller holds the lock; False in hotspot mode),
`get_dns_server_ip()`, `is_hotspot_active()`, `reconnect_wifi()`. NTP reads the DNS server *before* taking the
lock (that ordering once caused a real bug) and skips an attempt silently when the network is down. The lock
must not be held across broker I/O (the WiFi task holds it through a 60 s retry wait). There is no link-up
or link-down notification today, so a client learns of a dead link only from its own I/O or ping deadline.

**Never block.** Resolve via `resolve_ipv4()`, connect to the IPv4 literal; wrap every connect, CONNACK,
SUBACK and PINGRESP wait in `asyncio.wait_for_ms()` (the project's one timeout mechanism); own the socket
and close it in `finally` on every path; never write after a read raised `OSError` (the webserver's
`_peer_gone` guard is the precedent).

**Memory.** Zero `MemoryError`s — caught-and-logged included — at both GC stages (`-1` and `32768`); no
`gc.collect()` outside the two boot lists; long-lived buffers allocated once at construction/setup in the
`LockableBuffer` shape; reads only via `readinto()`; MQTT's Remaining Length (up to 256 MB) capped before
anything is allocated (MEM.T03); config strings ≤ 253 characters to fit the 256 B response pieces (I.3);
counters capped at 2**30 − 1; nothing permanent may grow.

**Sockets and lwIP.** Section 4 and question 8.4. Changing `toolchain/versions.toml`'s `[lwip]` table also
means teaching `check_lwip_ensemble()` and `buildgen/validate.py` about an outbound connection (both count
only `max_connections`), new Part N rows, a BACKLOG entry for the owner's chroot run, and a bench
re-measurement of H.7's peak heap.

**Config, credentials, exposure.** Config through `ConfigManager` (types int/float/str/bool only), persisted
by REST PUT; every value wired into the API and website (OR43.a: GET returns exactly what PUT accepts);
`@web` tags generate the website. The REST surface is hand-assembled: settings reach it only through a
`SettingsGroup` under `"networking"`/`"system"`/`"notification"` (`buildgen/codegen.py:643-662`), and the
errcount rows in `buildgen/definitions.py` are hand-listed. `js/mock-server.js` must mirror any change
(SPEC G.2). Adding broker fields to `/networking` changes the pinned body sizes in
`tests_scripts/test_request_body_cap_headroom.py` (cap 2,048 B; dev's largest route is 972 B today). No real
credentials in the repo: defaults empty, masked on every GET like the WiFi `PW`; the web UI cannot set an
empty string, so an optional credential cannot be cleared once entered (owner, 2026-08-22).

**Errors and logging.** One FRAM-backed logger plus its `CFGMGR_<name>` companion, wired by
`# @wiring fram_target FRAMManager log optional kwarg`; a new owner band in `buildgen/error_catalog.json`
(free: errno 115–124, wrnno 71+); a repeated error spends no new slot; one occurrence is never both an error
and a warning. The new loggers join CLAUDE.md's FRAM-logger list.

**Build wiring.** An optional singleton service: an `_OVERRIDES` entry in `buildgen/driver_registry.py` (like
`notification`), a build-arguments handler with a conditional `SettingsGroup`, a `conn` dependency edge in
`buildgen/graph.py`, definitions entries, a TOML block on the chosen devices, and the allow-list updates in
`test_device_tomls.py`/`test_buildgen_driver_registry.py`. Status can be exposed most cheaply as a
`maintenance_sensors` entry, as `UARTLinkDriver.get_link_status()` does.

**Testing, every tier** (CLAUDE.md's shared-resource rule covers sockets, the heap, locks, FRAM and the config
file):
- **L0, host gates:** task inventory, lock order, error catalog, tunables register, comment cap, citations.
- **L1, unit tests (MicroPython Unix port):** codec tests against the MQTT specification's example bytes; a
  session state machine against a fake broker over real loopback sockets, or a transport seam above the IO
  queue — never a fake object behind a real `select.poll()` (it hangs on CI runners); fixtures built in
  synchronous scope (a nested `asyncio.run()` segfaults the Unix port); allocation-rate tests; ports below
  32768.
- **L2, digital twin:** has no TCP fault model today, and test logic, broker included, must run host-side
  (E.9). A public broker would turn a third party's outage into a red result.
- **L3, flash tier:** no network; codec and heap placement only.
- **L4, bench tier:** the only tier where PCB, `ERR_MEM`, close-timeout and link-loss behaviour is real.
  Needs a broker on the bench Pi4 and the owner's go-ahead in that session.

**Vendoring and licence.** `ext/` holds only unmodified upstream tags or commits. SPEC F.4's
rewrite-with-attribution policy is per vendor (Adafruit; Sensirion stays literal) and names no MQTT source,
but `THIRD_PARTY_LICENSES.md` already applies restructure-with-attribution to other MIT sources (ISL29125,
NTP from micropython-lib, DNS from aiodns). `mqtt_as` is MIT, "Copyright (c) 2017 Peter Hinch" (the v5
properties file © Bob Veringa 2024–2025) — compatible with this project's MIT licence.

**Audit interplay** (`research/06_audit_pillars.md` §4). The audit is in execution (phase B since 2026-10-06);
units U18 (NET: `asy_wifi_service.py`, DNS/UDP), U19 (REST: `asy_webserver_service.py`), U20 (GEN: buildgen
and TOMLs) and U21 (TOOL: `[lwip]` and overrides) are pending and own every existing file the PoC would
touch. New files plus read-only use of public APIs keep the PoC clear of them; the build wiring is where the
two meet.

---

## 6. What would still be missing, by route

| Need | Vendor `mqtt_as_eth` unmodified + wrap | Own client in `src/` (recommended) |
|---|---|---|
| Leave WiFi to `WifiService` | yes (eth variant) | yes, by construction |
| No `gc.collect()` in loops | **no** — needs overriding `_keep_connected` | yes |
| No 5 ms polling / heap churn | **no** — needs overriding `_handle_msg` | yes: one task waits on the socket with a deadline |
| Non-blocking DNS, re-resolve on reconnect | partly — pass an IP; it never re-resolves | yes, via `resolve_ipv4()` |
| One supervised task, restart via the supervisor | **no** — fire-and-forget tasks | yes |
| Survives non-`OSError` exceptions | **no** (A5) | yes, per SPEC C.7 |
| Capped exponential backoff | **no** — 1 s retry | yes |
| Bounded, non-blocking `publish()` | **no** — waits for the whole outage | yes: bounded outbound ring, returns False when full or down |
| Inbound back-pressure | yes — overwrite-oldest ring, counted | yes, same idea, preallocated |
| Persistent session (`clean=False`) | **broken** (A4) | not in the PoC: clean session, resubscribe on every CONNACK |
| FRAM error log, errcount, catalog band | **no** — wrapper must translate | yes |
| Config/REST/website, `@web`/`@tunable` | wrapper | yes |
| Stays put under upstream churn | **no** — 3 weeks old, untagged | yes |
| Code to write and test | wrapper ≈ most of the session logic | codec + session ≈ 600–900 lines [I], plus tests |
| Field-proven protocol behaviour | inherited | borrowed deliberately from `mqtt_as`, re-proven by tests |

Missing on **both** routes: link-state input from `WifiService` (none exists; the client must be gated by
`network_available_locked()` and its own ping deadline); the lwIP budget; the `ERR_MEM` stall until the U21
override lands; TCP fault models for L1/L2; a test broker; L4 bench scenarios (broker on the Pi4, TCP
`REJECT`/`DROP` faults, holding the full HTTP ceiling while MQTT reconnects, the payload-size sweep above);
the documentation rows (SPEC C.7.1 catalog, C.8 locks, C.9 tasks, Part N, E.6.6 tier exceptions,
`THIRD_PARTY_LICENSES.md` if derived).

---

## 7. Sketch of the recommended client (for discussion; nothing here is decided)

- **One task, one owner of the socket.** A single supervised `_connection_loop()` resets its state at the top
  of every attempt: wait for the STA link → `resolve_ipv4(host)` → non-blocking connect under
  `wait_for_ms` → CONNECT/CONNACK → SUBSCRIBE everything declared → serve. While serving, the same task waits
  for readability with a deadline equal to the next due event (ping, pending publish, retransmission), so no
  two waiters ever share the socket (fact 5) and nothing polls. `finally` closes the socket on every exit.
- **Buffers allocated once.** A receive buffer sized by a tunable maximum inbound packet (larger packets are
  read and discarded in chunks, counted, never allocated); a transmit buffer; a fixed-slot outbound ring.
  All `readinto()`/`memoryview`; a failed allocation degrades to "disabled", per the ladder.
- **Publish API that never blocks.** `publish(topic, payload, qos, retain) -> bool` enqueues into the ring and
  returns False when the ring is full or the client is disabled; the oldest QoS 0 entry may be overwritten,
  QoS 1 entries wait for PUBACK with DUP retransmission (bounded count). Counters for sent, dropped,
  retransmitted.
- **Subscribe.** Topics declared in config; re-subscribed on every CONNACK (clean session). Received messages
  land in a bounded inbound ring that the PoC only counts and exposes (last topic, last payload size) — no
  config writes, no commands (question 8.6).
- **Keepalive.** PINGREQ when nothing has been sent for keepalive/2 (tunable); a missing PINGRESP within a
  deadline closes the connection and enters backoff. Backoff: capped exponential, first retry ≥ 10 s (this
  also keeps reconnect churn from needing an extra PCB, section 4).
- **Codec separate from session.** Pure functions packing/unpacking MQTT 3.1.1 packets into caller buffers,
  testable against the specification's examples without sockets — the aiomqtt-3.0 lesson.
- **Status.** Connected flag, broker IP, reconnect count, last error, counters — exposed via a
  `maintenance_sensors` entry or a status section (question 8.7).
- **Default off.** Empty broker host means disabled, so twin and bench "no new errors" baselines stay clean.

---

## 8. Questions for the owner (2026-10-07)

Each: the decision in at most ten words, then the options, each with its consequence. The agent's
recommendation is marked; none of these has been decided. No option touches any I2C, SPI or UART bus;
the effects are on WiFi/lwIP, the heap, the flash filesystem, REST and the website.

**8.1 Which code: vendor, derive, or write our own?**
- (a) Vendor `mqtt_as_eth` unmodified in `ext/`, wrapped from `src/` — inherits the field-proven session
  logic; the 1 Hz `gc.collect()`, 5 ms polling, fire-and-forget tasks and `OSError`-only recovery stay
  unless private methods are overridden; pinned to an untagged commit of a three-week-old variant.
- (b) Derive from `mqtt_as` into `src/` with MIT attribution (the ISL29125/NTP/DNS precedent) — freely
  restructured to the framework; a `THIRD_PARTY_LICENSES.md` "restructured" entry; upstream fixes are
  ported by hand.
- (c) **Recommended:** write a minimal MQTT 3.1.1 client in `src/` from the specification, with `mqtt_as` as
  the behavioural reference and (b)'s attribution for any part that ends up derived — every rule met by
  construction; most code to write and test.

**8.2 Which devices carry it, and enabled by default?**
- (a) **Recommended:** `dev` only, opt-in through `devices/dev.toml`, disabled until a broker host is set —
  the only device that can be bench-tested; no other device's image, heap or lwIP budget changes.
- (b) `dev` and `wozi` — wozi is the validated base, so its twin and unit tiers cover it too; wozi's image
  and budget change without a hardware test (wozi is never flashed).
- (c) All six, opt-in per TOML — every device's image grows; the per-device budget and twin baselines all
  change.

**8.3 Plain TCP only, or TLS too?**
- (a) **Recommended:** plain TCP 1883 under the trusted-home-LAN model — no mbedTLS heap; consistent with the
  unauthenticated REST API.
- (b) TLS 8883 — about 21 KB of contiguous heap per (re)connect against a ~1.5 KB largest free block at
  serving peak; certificate checks fail before the first NTP sync; likely forces fewer web connections on
  every device that carries it.

**8.4 Who pays MQTT's lwIP and heap share?**
- (a) **Recommended:** add one connection on top of `max_connections` 6 on carrying devices — PCB 9→10,
  SEG 48→56, `MEM_SIZE` 12,000→14,000 (2,324 B GC heap); a `versions.toml` change with validator updates,
  Part N rows, a BACKLOG chroot entry and a bench re-measure of the H.7 peak (~21 % free toward the
  7-connection ~14 %).
- (b) Lower `max_connections` to 5 on carrying devices — no image change to lwIP; one fewer simultaneous web
  client (OpenHAB's two pollers plus one browser tab still fit).
- (c) Run inside the existing 3 spares — no change at all; a burst of closing HTTP connections can exhaust
  the pool and make lwIP reset new web connections.

**8.5 Broker credentials: stored and masked like the WiFi password?**
- (a) **Recommended:** yes — optional user/password in the module's config file, empty by default, never
  returned on GET; same exposure as the WiFi `PW` over USB-REPL; an entered credential cannot be cleared from
  the web UI (known gap).
- (b) Anonymous broker only — no secret on any device; the broker must accept anonymous LAN clients.

**8.6 May received MQTT messages change configuration or run commands?**
- (a) **Recommended for the PoC:** no — received messages are counted and exposed only; "every flash write
  comes through REST PUT" (SPEC F.2, the WiFi power-cycle safety argument) stays true.
- (b) Settings writes via the existing compare-before-write path — a second flash-write trigger; SPEC F.2 and
  CLAUDE.md reworded; retained messages re-delivered on every reconnect must answer "unchanged" (no wear).
- (c) Also system commands (reboot, bootloader, reset, erase FRAM) — any LAN publisher can take a device
  offline.

**8.7 What does the PoC publish and subscribe to?**
- (a) **Recommended:** a periodic status/heartbeat topic `<prefix>/<hostname>/status` (QoS 0, retained) plus
  a last-will "offline", and one subscribed test topic `<prefix>/<hostname>/cmd/#` whose messages are only
  counted and echoed to status — exercises publish, subscribe, QoS 1, retain and will without touching any
  other module (the request says "not used at any place").
- (b) Also publish the existing `/measurements` keys as JSON per module, mirroring the REST key scheme — a
  second data contract (OR58.a's one key scheme) that is then frozen at the release.
- (c) Own flat topic per value — easiest for OpenHAB channels; a separate contract with its own conformance
  test.

**8.8 Which broker do the tests run against?**
- (a) **Recommended:** a minimal in-repo fake broker (host-side, stdlib only) for L1/L2 fault scripting, plus
  `mosquitto` on the bench Pi4 for L4 interoperability — no new CI dependency; real-broker behaviour proven
  on the bench only.
- (b) A pinned Python broker (e.g. `amqtt`) as a `dev` dependency for L2 — a real broker in CI; one more
  pinned dependency in the refresh.
- (c) `mosquitto` in CI too (apt package or digest-pinned container) — closest to deployment; adds to the
  toolchain apt list, the chroot check and the CI job graph.

**8.9 May MQTT link loss ever trigger WiFi recovery?**
- (a) **Recommended:** no — a broker outage is a remote fault, retried on backoff, never escalated; the CYW43
  false positive keeps its power-cycle backstop on every device (owner, 2026-09-04/26).
- (b) Yes — the MQTT ping becomes the reachability probe the owner declined on 2026-09-04 and confirmed on
  2026-09-26, reopening that decision; a broker outage could restart the radio on every carrying device.

**8.10 Where and when does this merge?**
- (a) **Recommended:** keep this branch's PR into the audit branch, with new files only until the audit's
  U18–U21 land, then do the build wiring on their final shapes — no audit unit changes; the PoC rebases over
  them.
- (b) Wire it into buildgen, the webserver and `[lwip]` now — collides with pending U18–U21 steps on the same
  files; the audit's work order would need re-deriving.
- (c) Merge to `main` only after the audit closes — no interaction at all; the PoC waits for the audit.

---

## 9. Sources

- `peterhinch/micropython-mqtt` at `dd03ab3bb8067658d1103292c36797bc5f259f83` (2026-10-07); MIT.
  `FUTURE_DEVELOPMENT.md` (`837a748`, 2024-08-18): "I have become convinced that, rather than extending to
  further network hardware, a rewrite is called for."
- MicroPython `v1.29.0` (`0fd6c57`): `extmod/asyncio/core.py`, `extmod/asyncio/stream.py`, `extmod/modlwip.c`,
  `extmod/modtls_mbedtls.c`, `ports/rp2/`; lwIP `77dcd25`; cyw43-driver `055d642`; micropython-lib
  `ee4bb8f`; mosquitto `src/handle_connect.c` (master).
- Every other repository, issue, discussion and forum thread: the source indexes at the end of
  `research/01_landscape.md` and `research/02_mqtt_as_deep_dive.md`.
- MQTT 3.1.1 (OASIS standard) is the protocol reference; the OASIS site was not reachable from the research
  session, so packet-level claims rest on the client sources and mosquitto, and must be checked against the
  specification text before any codec is written.
