> **Raw research report** (agent, 2026-10-07): written by a read-only research agent of the MQTT PoC research session, kept verbatim as the evidence base for `mqtt_poc/RESEARCH.md`. Tags such as [V]/[SRC] mean verified in source by that agent; [I]/[INFERENCE] are not verified; nothing here was run on hardware. Clone paths (`<research-session scratchpad>/ext/...`) refer to that session's temporary scratchpad, not to this repo. Line anchors into this repo are as of `1cff5a2`.

# asyncio MQTT clients for MicroPython: landscape survey

Survey date: 2026-10-07. Target: Raspberry Pi Pico W (RP2040 + CYW43), MicroPython v1.29.0, everything on
`asyncio`, the project's own WiFi service (`src/asy_wifi_service.py`), a hardware watchdog capped at 8388 ms,
and the project's memory and blocking rules (CLAUDE.md / SPECIFICATION.md Parts F and I).

Scope: the whole landscape. `peterhinch/micropython-mqtt` (`mqtt_as`) is covered at landscape depth only,
because another agent is reviewing it line by line.

---

## 0. Method, evidence levels, and what could not be reached

- Every candidate repo was shallow-cloned, each into its own directory under
  `<research-session scratchpad>/ext/<name>/`, and read
  without running anything. File:line references are to the commit SHA given in each section.
- The MicroPython facts come from my own sparse checkout of tag `v1.29.0` (commit `0fd6c57`), at
  `ext/mp-v1.29.0-landscape/`. Where a file was not checked out, it was read with `git show HEAD:<path>`.
- Repo metadata (stars, forks, open counts, dates) comes from the GitHub search API, read on 2026-10-07.
  PyPI metadata comes from `pypi.org/pypi/<name>/json`.
- **Evidence labels used throughout:**
  - **[verified]**: I read the source or document myself.
  - **[inference]**: my conclusion from the code; not run on hardware.
  - **[snippet]**: seen only in a search-engine summary; not verified at the source.
- **Sources this session could not reach:**
  - `forum.micropython.org`, `notes.alelec.net` and `web.archive.org` are blocked by the egress policy.
  - GitHub issue comment threads do not render through WebFetch (only the opening post comes through), and
    per-repo GitHub API reads are restricted to the session's own repo.
  - For issues, I therefore had the **opening post plus the comment count** (via the GitHub search API).
  - GitHub *Discussions* render fully, so the Discussion field reports are complete.
  - Forum-archive statements below are marked [snippet].

---

## 1. Bottom line

1. **The only actively maintained, field-proven asyncio client is Peter Hinch's `mqtt_as`.**
   - Last commit `dd03ab3`, 2026-10-07 (today). 688 stars, 153 forks.
   - Supports Pico W; MQTT 3.1.1 plus partial MQTT v5; QoS 0/1.
2. **Biggest surprise: a brand-new `mqtt_as_eth` variant, 10 days old, removes all WiFi management.**
   - Committed `ac0492d`, 2026-09-27, as "Add Unix build/wired Ethernet capability". It has the same API and
     runs on the Unix port and CPython.
   - This is structurally what this project needs. The classic `mqtt_as` owns the WLAN and calls
     `wlan.connect()`/`disconnect()` itself, which cannot coexist with `asy_wifi_service.py`.
   - Caveat: it is days old and still changing (commits on 10-06 and 10-07). At HEAD its mip `package.json` is
     not valid JSON, and it has a dead method calling a function that does not exist.
3. **Every other asyncio client found is abandoned, broken, or a thin naive port.** Specifically:
   - `tve/mqtt_async`: keepalive silently disabled by a missing `return`. Unmaintained since 2021–22.
   - `aiomqttc`: GitHub HEAD does not even parse. The PyPI release uses non-builtin exception names.
   - `zcattacz/mqtt_as`: a stripped 2022 `mqtt_as`. Usable, but single-maintainer and behind upstream.
   - Naive `umqtt.simple` ports: `asyncmd`, micropython-lib PRs #722 and #1086, `umqtt_async`.
4. **The official `umqtt.simple`/`umqtt.robust` are blocking.** They are actively maintained in 2026, but:
   - Two asyncio ports to micropython-lib are open and unmerged. #1086 has protocol bugs I verified.
   - On 2026-07-01, Damien George asked for codec logic to be factored out and shared between them.
   - An official async umqtt may arrive later, but it is not there now.
5. **Nothing in the MicroPython ecosystem supports QoS 2 on the client side.**
6. **Two platform facts dominate the risk, whichever library is chosen** (§2):
   - `socket.getaddrinfo()` blocks the event loop (bounded by lwIP's DNS timeout since 1.28; IP literals return
     immediately).
   - A TLS handshake on RP2040 can block the event loop for about 7–8 s or more, i.e. at the watchdog cap.

---

## 2. Platform facts that decide the comparison (MicroPython v1.29.0, verified)

| # | Fact | Source |
|---|------|--------|
| P1 | `asyncio.open_connection()` calls `socket.getaddrinfo()` synchronously; upstream marks it `# TODO this is blocking!`. The TCP connect is non-blocking, and the socket is wrapped with `do_handshake_on_connect=False` when `ssl` is given. | `extmod/asyncio/stream.py:99-123` |
| P2 | `Stream.read(n)` with `n >= 0` returns whatever the first successful non-blocking read gives, so it can return **short reads**. Only `readexactly(n)` loops until `n` bytes. Any client that reads fixed-size MQTT fields with `read(n)` can desynchronise on fragmented or TLS-chunked data. | `stream.py:24-52` |
| P3 | Legacy `Stream.awrite(buf, off=0, sz=-1)` treats its 2nd positional arg as an **offset**. | `stream.py:209-222` |
| P4 | `wrap_socket(..., do_handshake_on_connect=True)` (the default) loops `mbedtls_ssl_handshake()` with `mp_event_wait_ms(1)`. That waits for low-level events only and never yields to the asyncio scheduler, so **the whole handshake blocks the loop**. With `False`, the handshake advances inside `read`/`write`, which return `EWOULDBLOCK`. **[inference]:** each individual crypto step still runs synchronously. | `extmod/modtls_mbedtls.c:818-825, 896-905, 936-944` |
| P5 | The C `tls.SSLContext` client defaults to `VERIFY_REQUIRED`. The frozen Python wrapper `ssl.SSLContext` (micropython-lib) forces `verify_mode = CERT_NONE`, so `open_connection(..., ssl=True)` gives an encrypted but **unauthenticated** link. | `modtls_mbedtls.c:330-335`; micropython-lib `python-stdlib/ssl/ssl.py:5-8, 44-65` |
| P6 | The Pico W build freezes `bundle-networking`, which includes `ssl`, `requests` and `ntptime` but **not `umqtt`**. Any MQTT client must therefore be vendored. | `ports/rp2/boards/RPI_PICO_W/manifest.py`; micropython-lib `micropython/bundles/bundle-networking/manifest.py` |
| P7 | `getaddrinfo()`: an IP literal or a cached name takes lwIP's `ERR_OK` path and returns immediately. Otherwise it loops `poll_sockets()` until the lwIP DNS callback fires. | `extmod/modlwip.c:1862-1890` |
| P8 | Hang bug micropython#18797 (`getaddrinfo` never returning after the interface went down; Pico 2 W, v1.26.1) was fixed by **PR #18805**: merged 2026-03-04, milestone 1.28.0, so **present in v1.29.0**. The PR author's own description: "Hangs indefinitely without this fix. Fails after the DNS timeout with this fix." So it is now bounded, but **still blocks the event loop** for the lwIP DNS timeout. | `ports/rp2/mpnetworkport.c:137-144` (`lwip_poll_hook`); [PR #18805](https://github.com/micropython/micropython/pull/18805) |
| P9 | `socket.setblocking(True)` sets the timeout to `-1` (infinite), so it erases any earlier `settimeout()`. | `modlwip.c:1459-1466` |
| P10 | `TimeoutError` and `ConnectionError` are **not MicroPython builtins**: they sit in a commented-out block and are absent from the builtins table. `asyncio.TimeoutError` is a separate class. | `py/objexcept.c:331-349`; `py/modbuiltins.c:740-772`; `extmod/asyncio/core.py:22` |
| P11 | `WLAN.connect()` on CYW43 requires an `ssid` buffer (`MP_ARG_REQUIRED` plus `mp_get_buffer_raise`), so `connect(None, None)` raises `TypeError`. | `extmod/network_cyw43.c`, `network_cyw43_connect` |
| P12 | CYW43 power-management constants: `PM_NONE` = `CYW43_PM_VALUE(NO_POWERSAVE,10,0,0,0)` (the `0xA11140` used by mqtt_as and by this project), plus `PM_PERFORMANCE` and `PM_POWERSAVE`. | `network_cyw43.c:50-52`; project `src/asy_wifi_service.py:326, 689` |
| P13 | errno values on rp2/lwIP: EAGAIN 11, ECONNABORTED 103, ECONNRESET 104, ENOTCONN 107, ETIMEDOUT 110, EHOSTUNREACH 113, EINPROGRESS 115. A failed `getaddrinfo` raises lwIP's **negative** native code, e.g. `OSError(-2)`. | `py/mperrno.h:46-83`; `modlwip.c:1886-1889` |

**[inference]** Consequences for this project:

- Resolve the broker name with the project's own non-blocking `src/asy_dns_client.py` and hand the client an
  **IP literal**. lwIP then takes the immediate path (P7), and no candidate's internal `getaddrinfo` can stall
  the loop.
- On a trusted LAN, plain MQTT avoids P4 entirely. That is consistent with the project's accepted
  trusted-home-LAN threat model.

---

## 3. Candidates found

**Real candidates** (asyncio, MicroPython, MQTT client):

1. `peterhinch/micropython-mqtt`, two variants: `mqtt_as` (WiFi) and `mqtt_as_eth` (no network management, new).
2. `zcattacz/mqtt_as`: a fork with no network management.
3. `tve/mqboard` → `mqtt_async`, published on PyPI as `micropython-mqtt` / `micropython-mqtt-async` 0.7b4.
4. `kevinkk525/micropython-mqtt` (fork, including the `hardware_independent` branch). Embedded copies in
   `kevinkk525/pysmartnode` and `microhomie/microhomie`.
5. `Tangerino/aiomqttc` (GitHub plus PyPI 1.0.7).
6. `Carglglz/asyncmd` → `async_modules/async_mqtt`. The same code is open as micropython-lib PR #722.
7. micropython-lib PR #1086, `umqtt.async`.
8. `a-smiggle/umqtt_async`.
9. `nznobody/micropython-umqtt.uasyncio2` (WIP).

**Synchronous references:** micropython-lib `umqtt.simple` and `umqtt.robust`; fizista `umqtt.simple2` and
`umqtt.robust2`.

**Surprises and non-candidates:**

- `gregyedlik/micropython-holdfast` (2026, MIT): a Pico W resilience framework built on blocking `umqtt.simple`.
- `belyalov/tinymqtt`: uses the pre-2020 uasyncio v2 API.
- `chrismoorhouse/micropython-mqtt`: uses `_thread`, not asyncio.
- `Joel-Edem/async-mqtt-client`: blocking calls dressed as coroutines.
- `andreicsp/upymqtt`: an empty repo.
- `ehong-tl/mqttsn-python3-micropython`: an MQTT-SN client, synchronous and `_thread`-based.
- `mateuszsury/beehiveMQTT`: a MicroPython MQTT **broker** with QoS 0–2.
- CPython design references: `aiomqtt`, `mqtt5`, `paho-mqtt`, `gmqtt`, `amqtt`.

No MicroPython MQTT v5 client exists other than `mqtt_as`'s partial v5 mode. A GitHub search for
`mqtt5 micropython` returned 0 repos.

---

## 4. Comparison table

Legend:
- **Y** = yes, **N** = no, **P** = partial, **?** = not verified.
- **Non-blocking** refers to steady-state I/O.
- **DNS** means `getaddrinfo` and **TLS** means the handshake behaviour (§2 P1/P4).

| | mqtt_as (WiFi) | mqtt_as_eth | zcattacz/mqtt_as | tve mqtt_async | aiomqttc 1.0.7 | asyncmd async_mqtt / PR#722 | PR#1086 umqtt.async | umqtt_async (a-smiggle) | umqtt.simple / robust |
|---|---|---|---|---|---|---|---|---|---|
| Last commit | 2026-10-07 | 2026-10-07 (new 09-27) | 2025-11-25 | 2022-05-08 (file 2021-01-17) | 2025-05-21 (HEAD broken) | 2024-03-20 / 2023-09-01 | 2026-02-19 | 2020-12-29 | 2026-09-11 / 2026-07-01 |
| Stars / open issues | 688 / 18 (+6 PR) | (same repo) | 9 / 0 issues (1 open item, likely a PR) | 128 / 19 | 21 / 1 | 13 / 0 | n/a | 2 / 1 | n/a (≥12 umqtt issues open) |
| License | MIT | MIT | MIT (Hinch header) | MIT | Unlicense | MIT | MIT (mplib) | MIT | MIT (mplib) |
| MQTT 3.1.1 / v5 | Y / P (opt-in) | Y / P | Y / N | Y / N | Y / N | Y / N | Y / N | Y / N | Y / N |
| QoS pub / sub | 0,1 / 0,1 | 0,1 / 0,1 | 0,1 / 0,1 | 0,1 / 0,1 | 0,1 (no retry) / 0,1 | 0,1 / 0,1 | 0,1 (QoS1 pub broken) / 0,1 | 0,1 / 0,1 | 0,1 / 0,1 (2 = assert) |
| Retain flag delivered on receive | Y | Y | Y | Y | Y | N | N | N | N |
| Last will | Y | Y | Y | Y | Y | Y | Y | Y | Y |
| Clean / persistent session | Y (`clean_init`/`clean`) | Y | Y | forced persistent after 1st connect | Y | Y | Y | Y | Y |
| Keepalive ping + dead-link detect | Y | Y | Y | **N (bug)** | P (flags only) | N | N | P (no PINGRESP timeout) | N (manual `ping()`) |
| Non-blocking I/O | Y (raw sock, polled) | Y | Y (5 ms polling) | Y (streams) | Y (streams) | Y (streams) | Y (streams) | Y (streams) | **N** |
| DNS blocking? | once, 1st connect | once, 1st connect | once (≤5 retries) | once, 1st connect | every connect | every connect | every connect | every connect | every connect |
| TLS handshake | blocking (`wrap_socket`) unless `do_handshake=False` | same (MicroPython only) | blocking (`ussl.wrap_socket`) | `ssl=` dict → likely error on 1.29 [inference] | non-blocking, CERT_NONE | non-blocking via SSLContext | ignored | none | blocking |
| Read timeouts | Y (`response_time`) | Y | Y | N | N on MicroPython | N | N | N | via `connect(timeout)` until `wait_msg` resets it |
| Auto reconnect | Y | Y (1 s fixed) | **N** (app's job) | Y (1 s fixed) | off by default | N | N | Y | robust: Y (blocking `time.sleep`) |
| Resubscribe after reconnect | N (persistent session + app `up` handler) | same | N | N (persistent session) | N | N | N | N | N |
| In-flight QoS1 on reconnect | `publish()` waits, then re-sends | same | raises after `max_repubs` | 1 outstanding re-sent `dup=1` | dropped after 5 s | n/a | n/a | P | robust re-calls publish |
| Owns the WLAN? | **Y** (`connect`/`disconnect`/`pm`) | **N** | N | Y (injectable `interface`) | N | N | N | N (`network_status` flag) | N |
| Incoming API | callback or Event + ring-queue `async for` | same | ring-queue `async for` (+ callback adaptor) | callback (coro awaited inline) | callbacks / coro inline | callback inline | callback inline | callback inline | callback inline |
| `gc.collect()` in run phase | Y (1 Hz) | Y (1 Hz) | Y (connect) | N | N | N | N | N | N |
| Unix port / CPython | N | **Y / Y** (TLS: MicroPython only) | Y / Y | Y / Y (shims) | Y / Y | Y (`develop/unix/`) / ? | ? | ? (CPython import fallbacks present, untested) | N |
| Verdict | mature; WiFi ownership conflicts | **best structural fit; immature** | fallback / reference | design reference only | do not use | minimal base, needs fixes | not usable as is | do not use | not usable in asyncio |

---

## 5. Per-candidate details

### 5.1 peterhinch/micropython-mqtt: `mqtt_as` and `mqtt_as_eth` (landscape view)

Repo: https://github.com/peterhinch/micropython-mqtt. HEAD `dd03ab3` (2026-10-07). Clone:
`ext/peterhinch-mqtt_as/`.

**Status [verified]**
- 688 stars and 153 forks; 18 open issues plus PRs (24 total).
- MIT licence.
- **No git tags or GitHub releases**: versions live in the files (`mqtt_as/__init__.py:31` `VERSION = (0, 8, 5)`;
  `mqtt_as_eth/__init__.py:42` `VERSION = (0, 1, 0)`). Install is via `mip` `package.json`.
- Release notes are in `README.md:179-190`:
  - "1 Oct 2026 Add support for non-wifi hardware."
  - V0.8.3 (7 Mar 2025): unsubscribe and VBI decode fixes.
  - V0.8.2 (24 Oct 2024): pre-allocated socket read buffer.
  - V0.8.0 (9 Aug 2024): "Partial MQTTv5 support contributed by Bob Veringa".
  - V0.6.5 (11 Jul 2022): "Support RP2 Pico W".
- Vendoring into `ext/` would therefore pin a **commit SHA**, not a tag.

**Recent activity (git log)**
- `ac0492d` 2026-09-27: "Add Unix build/wired Ethernet capability". New `mqtt_as_eth/`, 849 lines.
- `1700feb` 2026-10-04: README now says `.publish()` during an outage "will pause until the WiFi/broker are
  accessible when the message will be published. If late publication is undesirable, status may be tested with
  `.isconnected()` immediately prior to issuing `.publish()`." This followed issue #185 (below).
- `6a40818` 2026-10-06: "First pass at CPython support".
- `dd03ab3` 2026-10-07: "Further work on CPython compatibility".
- Earlier: static-IP PR #182 (2026-09-02/03); Arduino Nano RP2040 Connect (2026-03-14); `do_handshake` TLS docs
  (`7b1a63e`, 2025-05-07).
- `FUTURE_DEVELOPMENT.md` (verified): Hinch argues "a rewrite is called for". He wants a transport-agnostic
  client with separate "socket layer" and "transport layer", says "Support for `qos == 2` is reasonably
  straightforward", and cites `umqtt.robust2` as a reference. He also notes "Kevin Köck planned to extend it to
  handle wired networks but is unable to continue this work."

**Protocol [verified]**
- MQTT 3.1.1, plus MQTT v5 opt-in (`config["mqttv5"]`, `__init__.py:111, 210-214`; the CONNECT protocol level
  is set at L317).
- QoS 0/1 only: `qos_check` raises "Only qos 0 and 1 are supported." (L127-128).
- Optional event interface: `up`/`down` Events plus `MsgQueue`, a fixed-size ring that **overwrites the oldest**
  entry and counts `discards` (L60-85). Enabled by `queue_len > 0` (L109, L151, L177-178).
- Pre-allocated 50-byte input buffer that grows on demand (`IBUFSIZE` L34; `_as_read` L234-242).

**WLAN ownership: the decisive point for this project [verified]**

The WiFi variant takes the radio over:
- `self._sta_if = network.WLAN(network.STA_IF); self._sta_if.active(True)` runs in the constructor (L191-192).
- `wifi_connect()` on RP2 calls `s.config(pm=0xA11140)` and then **`s.connect(self._ssid, self._wifi_pw)`
  unconditionally** (L743-747). With no SSID this raises `TypeError` (P11). That matches issue #121
  (Pico W, 2023-08-22: `wifi_connect` → "TypeError: object with buffer protocol required").
- On every outage, `_keep_connected()` calls `self._sta_if.disconnect()` and re-runs `wifi_connect()`
  (L903-917). `connect()` runs `wifi_connect()` on first call (L785-788).

**[inference]** This fights `asy_wifi_service.py`: both would drive the same CYW43 interface.

**`mqtt_as_eth` (new) [verified]**
- It deletes all `network`/WLAN code (`diff mqtt_as/__init__.py mqtt_as_eth/__init__.py`). Same API.
- README §10, "Non-wifi platforms" (README:1432-1520): "Potentially any device providing a `socket` interface
  may be employed. The API is identical to the WiFi library (irrelevant configuration args such as WiFi
  credentials will be ignored.)"
- It also says: "If attempting to use a platform that requires programmatic intervention to re-establish lost
  connectivity, it is the responsibility of the application to supply it. The library provides notification of
  outages … but does not distinguish between broker outages and more general network outages."
- **[inference]** That division of labour is exactly what this project wants: its WiFi service owns the link,
  and the MQTT client only owns the broker session.
- It runs on the Unix port and CPython. CPython uses `loop.sock_recv`/`sock_sendall` with `wait_for(...,
  response_time)` (L285-340), and TLS raises "SSL/TLS requires MicroPython." (L204-210). **[inference]** This
  fits the project's Unix-port unit tier and digital twin directly.

`mqtt_as_eth` defects and caveats at `dd03ab3` [verified]:
- `mqtt_as_eth/package.json` is **invalid JSON** (trailing comma at line 6). It also still lists `unix_test.py`,
  which was renamed to `pc_test.py` in `dd03ab3`. **[inference]** `mip install github:…/mqtt_as_eth` probably
  fails until fixed; MicroPython's own JSON parser was not tested.
- `_lan_connect()` (L451-456) calls `self.wan_ok()`, which only exists in the WiFi variant. It is unused dead
  code, but shows the variant is not yet settled.
- `BUSY_ERRORS = [EINPROGRESS, ETIMEDOUT]` (L49). The RP2-specific `-110` that the WiFi variant treats as
  "busy" (`mqtt_as/__init__.py:46-47`) is gone. **[inference]** If `-110` still occurs on Pico W, it would now
  count as a link failure; whether it still occurs on v1.29 is unverified.
- `getaddrinfo` runs only on the first `connect()` and the address is **cached for the lifetime of the
  client** (L743-745). A broker whose IP changes needs a client restart.
- Reconnect loop: a fixed 1 s pause, then `connect()`; no backoff (L851-872).
- `gc.collect()` runs **every second while connected** in `_keep_connected` (L855; WiFi variant L907), and in
  the debug `_memory` task (L833).
  - **[inference]** This conflicts with SPECIFICATION I.4 ("no `gc.collect()` calls … anywhere in the business
    logic"). `tests_scripts/test_gc_collect_sites.py` only scans `src/` and `buildgen/`, so a vendored `ext/`
    copy would not trip the guard.
  - Because `ext/` code must stay unmodified, this needs an owner decision. A wrapper cannot remove it.

**Blocking points [verified + inference]:**
- `getaddrinfo` on first connect. The source comment: "Note this blocks if DNS lookup occurs. Do it once to
  prevent blocking during later internet outage" (WiFi L789-790).
- `ssl.wrap_socket(self._sock, **self._ssl_params)` (WiFi L314, eth L369) runs the full handshake
  synchronously unless `ssl_params["do_handshake"] = False`.
  - Issue #171 (2025-04-30, open): "`ssl.wrap_socket()` hangs on reconnecting … this triggers WatchDog Timer to
    restart the MCU."
  - README §9 now points to #171 for the `do_handshake` key (README:1395-1403).

**Open issues relevant here** (opening posts read; comment threads not readable):
- [#183](https://github.com/peterhinch/micropython-mqtt/issues/183) "starting without mqtt" (2026-09-20, ESP32):
  the first `connect()` raises if the broker is down, so the app must loop.
- [#171](https://github.com/peterhinch/micropython-mqtt/issues/171): TLS blocking → watchdog reset (14 comments).
- [#161](https://github.com/peterhinch/micropython-mqtt/issues/161) "OSError: Connection Unstable"
  (2025-01-08, **Pico W**), raised by `wifi_connect`'s 5 s integrity check.
- [#122](https://github.com/peterhinch/micropython-mqtt/issues/122) "wifi is treated as internal details only"
  (2023-10-06): "mqtt_as assumes control of the wifi interface".
- [#118](https://github.com/peterhinch/micropython-mqtt/issues/118) "Sporadic resets" (2023-07-25, **Pico W**,
  14 comments).

**Forks:** 153 GitHub forks; recent ones (`growmatic`, `marcosdiez`, `digital-codes`, …) are plain copies. The
notable derivatives are §5.2 (zcattacz), §5.4 (kevinkk525, microhomie, pysmartnode), and Bob Veringa's fork,
which was the origin of v5 (merged via #139/#148).

### 5.2 zcattacz/mqtt_as: mqtt_as "without network management"

Repo: https://github.com/zcattacz/mqtt_as. HEAD `3ab976a` (2025-11-25). Clone: `ext/zcattacz-mqtt_as/`.

**Status:** 9 stars, 4 forks, 0 open issues. MIT via Hinch's header (`mqtt_as.py:1-3`, "(C) Copyright Peter
Hinch 2017-2022"). There is no LICENSE file. One maintainer; commits in 2023-11, 2024-12/2025-01 and 2025-11.

**Purpose (README):** "Drops wifi and connectivity management… whenever the network device can't or shouldn't
be directly manipulated by a mqtt client lib." "This version reports down on network read/write error and stops
working. User needs to recover link and try `connect()`."

**Details:**
- Based on a 2022 mqtt_as, so it lacks v5 and the 0.8.x fixes (VBI decode, pre-allocated read buffer).
- QoS 0/1 (`qos_check` L138-140); last will; `connect(clean)`.
- Keepalive pings at `keepalive/4`; after 4 intervals without rx it reports "broker timeout" → down
  (L454-468).
- Non-blocking raw socket, **polled every 5 ms** (`_SOCKET_POLL_DELAY` L54, used at L259 and L292).
  **[inference]** This costs CPU continuously while a read waits.
- `_as_read` allocates a fresh `bytearray(n)` for every read (L231). Read timeout is `response_time` (L238-240).
- DNS: blocking `getaddrinfo`, up to 5 attempts, a random pick among A records, then cached (L315-336,
  L349-350).
- TLS: `import ussl; ussl.wrap_socket(...)` (L390-393), so the handshake is blocking. Whether `import ussl`
  still resolves on 1.29 is **?**.
- QoS1: re-publishes up to `max_repubs`, then `raise OSError(-1)` (L541-555). There is no auto-reconnect and
  no resubscribe.
- Incoming messages go to `MsgQueue`, the same overwrite-oldest ring as upstream (L79-105), default
  `queue_len` 2 (L123). Callbacks come via `mqtt_as_cb.py`.
- Unix port and CPython supported (`micropython.py` shim; `patch_poll_socket.py` adds a 5 s poll-based connect
  timeout for old firmware).
- An experimental stream-based `mqtt_sr.py` exists: `asyncio.open_connection` + `readexactly` (L224, L300).
  It was first removed ("Remove stream version, it failed echo test.", `4226654`, 2023-11-26) and reintroduced
  `807e0e3` (2025-11-25).
- **[inference]** `_handle_msg` catches every `Exception`; any error whose `args[0]` is not a "link down" errno
  is swallowed silently (L470-479).

**Verdict:** a proof that the "no network management" split works, with a usable async-iterator API. Upstream's
own `mqtt_as_eth` now supersedes it.

### 5.3 tve/mqboard → `mqtt_async` (Thorsten von Eicken)

Repo: https://github.com/tve/mqboard. HEAD `98bcdd0` (2022-05-08); `mqtt_async/mqtt_async.py` last changed
`e8f4076` (2021-01-17). Clone: `ext/tve-mqboard/`. Also on PyPI as `micropython-mqtt` and
`micropython-mqtt-async`, both 0.7b4, 2020-03-26, pointing to `tve/micropython-mqtt`.

**Status:** 128 stars, 19 open issues, all unanswered. Examples: #22 TLS example, #28/#29 "Hello World example
not working with Mosquitto", #32 "unexpected keyword argument 'ssl'", #34 LAN usage. MIT.

**Good design ideas [verified]:**
- A protocol object per connection (`MQTTProto`, L149-153) is kept apart from the resilient client
  (`MQTTClient`, L496).
- Uses `asyncio.open_connection` streams (L27-28, L189).
- Publish allows a single outstanding async QoS1 message, retransmitted with `dup=1` after reconnect
  (L623-628, L814-853).
- Connects with a clean session first, then reconnects unclean so the broker keeps subscriptions across outages
  (L612-619).
- Subscription callbacks may be coroutines, awaited inline (L469-474).

**Critical bug [verified]:** `MQTTProto.isconnected()` has no `return` (L355-356:
`def isconnected(self): self._sock is not None`).
- So `_keep_alive`'s `while proto.isconnected():` (L727) never runs, and **no PINGREQ is ever sent**.
- MQTT keepalive is also forced to 0 unless a will is configured (L503-504).
- Present since at least `76cea86` (2020-05-24). The unit test mocks `isconnected()` correctly
  (`test_client.py:165`), which is why the tests never caught it.
- **[inference]** A half-open TCP connection is never detected while idle.

**Other issues:**
- Reads and writes have no timeout, by design: "relies on the socket being closed by a watchdog" (L259-263,
  L290-292).
- Owns WiFi: `interface` defaults to `STA_IF` (L103). `wifi_connect` is at L531-578, and **`interface.disconnect()`
  is called when a broker reconnect fails** (L780). The interface object is injectable, so a shim is possible.
- **[inference]** `ssl_params` is passed as `open_connection(..., ssl=...)` (L607, L27-28). On 1.29 that must be
  `True` or an `SSLContext` (P1), and the hostname for SNI would be the resolved IP.
- QoS2 inbound raises (L482-483). `unsubscribe` is commented out (L408-416).
- Reads concatenate `self._read_buf += got`, reading at least 128 bytes each time (L264-288): an allocation per
  read.

**Verdict:** unmaintained, with a silent keepalive defect. Valuable as a design reference only.

### 5.4 kevinkk525 fork, pysmartnode, microhomie

**kevinkk525/micropython-mqtt** (https://github.com/kevinkk525/micropython-mqtt, MIT). Clone:
`ext/kevinkk525-micropython-mqtt/`.
- `master` is at `6e25ac7` (2020-04-07, "new implementation for concurrent timeout operations").
- Branch `hardware_independent` is at `2067e57` (2021-08-02). It adds a `BaseInterface` abstraction in
  `mqtt_as/interfaces/__init__.py`: `connect`/`disconnect`/`reconnect`/`isconnected` plus state-change
  callbacks, with WLAN implementations for ESP32/ESP8266/Pyboard and a Linux interface. There is **no rp2**
  implementation, and the branch is abandoned (see Hinch's note in §5.1).
- **[inference]** This is the right integration shape for this project: the WiFi service would implement the
  interface.

**pysmartnode** (`a0998ad`, 2020-09-01) uses the fork's `mqtt_as_timeout_concurrent`. **microhomie** (`67324a9`,
2021-01-07) bundles mqtt_as `VERSION = (0, 6, 0)` (`lib/mqtt_as.py:27`). Both are ESP-focused and dormant.

### 5.5 Tangerino/aiomqttc

Repo: https://github.com/Tangerino/aiomqttc. HEAD `b4cf7e8` (2025-05-21). Clones: `ext/tangerino-aiomqttc/`,
and the PyPI sdist at `ext/aiomqttc-pypi-1.0.7/`.

**Status:** 21 stars, 1 fork. Unlicense (public domain). README: "Tested on: ESP32-PICO, MicroPython v1.23.0".

- **GitHub HEAD does not parse [verified]:** `ast.parse` reports *SyntaxError at line 1152, "unindent does not
  match any outer indentation level"*. A duplicated, half-merged `_read_packet` sits at L1146-1219.
  - Issue [#8](https://github.com/Tangerino/aiomqttc/issues/8) (2025-11-23, no reply) says the same: "a stray
    duplicate `_read_packet` method … which seems to contain part of the `handle_packet` code", and reports
    malformed-SUBACK failures even after a patch.
- **PyPI 1.0.7 (2025-05-21) parses.** Reviewed below (line numbers are in the sdist file).

**Design:**
- `asyncio.open_connection` wrapped in `wait_for` (L209-224).
- Protocol/client split, stats counters, callbacks (`on_connect`/`on_disconnect`/`on_message`/`on_ping`).
- Exponential reconnect backoff, but `reconnect_interval = max_reconnect_interval = 0` by default
  (L915-917, L1150-1152), so **auto-reconnect is off unless configured**. `publish()` lazily reconnects
  (L1008-1011).

**Problems [verified unless marked]:**
- Exception names that are not MicroPython builtins (P10): `except TimeoutError:` at L598, L713, L985 and
  L1097. GitHub HEAD also has `raise ConnectionError(...)` at L1275.
  - **[inference]** In MicroPython, reaching one of these clauses raises `NameError`. For example, an `OSError`
    propagating into `handle_packet` hits the `except TimeoutError` clause first (L713), so the error paths
    themselves crash.
- No read timeout (L255-262), and on MicroPython the write path `writer.awrite(data)` has no timeout (L239-240).
- When the keepalive declares the server dead, it only sets `connected = False` (L1077-1080, L1085-1086). The
  socket is not closed and the receive task is not cancelled. **[inference]** This leaks resources.
- **[inference]** After EOF, `read()` returns `b""`. `handle_packet` then sleeps 50 ms and returns `True`, so
  the receive loop spins (L647-652).
- `MQTTClient.subscribe` does not wait for SUBACK (L1032-1041). Meanwhile `MQTTProtocol.subscribe` reads
  packets itself while the receive loop also reads (L587-597). **[inference]** That is a reader race.
- Per-topic callbacks use exact-string lookup (L678), so wildcard subscriptions only reach `on_message`.
- No resubscribe.
- QoS1: polls every 100 ms for up to 5 s, never retransmits (the retry loop is commented out, L463), and
  drops the message.
- QoS2 inbound is not acknowledged.
- `publish()` defaults to `qos=1` (L1007).
- `ssl=True` gives a CERT_NONE context (P5); `ssl_params` is stored but ignored (L906, L954).

**Upside:** no WiFi management.

**Verdict:** not usable.

### 5.6 Carglglz/asyncmd `async_mqtt`, and micropython-lib PR #722

**`async_modules/async_mqtt/async_mqtt.py`** (238 lines, `3f5c067`, 2024-03-20, MIT). Clone:
`ext/carglglz-asyncmd/`. The author also wrote MicroPython's asyncio SSL support (micropython#11897, which PR
#722 references).

- An `umqtt.simple` port onto asyncio streams.
- `open_connection(server, port, ssl=SSLContext, server_hostname=...)` (L74-77). This is the **only
  candidate built around the non-blocking-handshake TLS path** (P4).
- **[inference]** It reads fixed-size fields and the payload with `read(n)` (L121, L187, L199-222), so short
  reads can desync framing (P2).
- No keepalive task, no reconnect, no timeouts. `assert`-based protocol checks. Callback runs inline. QoS2 hits
  an `assert 0`.

**PR #722** ([link](https://github.com/micropython/micropython-lib/pull/722), Carglglz, 2023-09-01, open, no
reviews) adds the same file as `umqtt.simple/umqtt/async_simple.py`. `diff` shows only comments and an
`is_connected()` helper differ.

### 5.7 micropython-lib PR #1086 `umqtt.async`

[PR #1086](https://github.com/micropython/micropython-lib/pull/1086) (dketov, 2026-02-19, open). Fetched as
`pr1086`; the file is copied to `ext/mplib-pr1086/async.py`.

Damien George, 2026-07-01: "This reimplements all the MQTT logic from scratch. Is there a way to factor out the
logic (eg for creating packets) so it can be shared by `umqtt.simple` and `umqtt.async`?" He also pointed to
#722 as "a very similar thing". The author agreed on 2026-07-03. No change since.

Verified defects:
- `sz = await self.r.read(1)[0]` (L194) subscripts the generator before awaiting it, so a **`TypeError` on every
  PINGRESP**.
- `await self.w.awrite(pkt, 2)` (L136) means `off=2` (P3). It sends `pkt[2:4]` instead of the 2-byte packet ID,
  so **QoS1 PUBLISH packets are malformed**.
- `ssl` and `ssl_params` are ignored (`open_connection(self.server, self.port)`, L67).
- Fixed-size fields are read with `read(n)` (P2).

### 5.8 a-smiggle/umqtt_async; nznobody umqtt.uasyncio2

**a-smiggle/umqtt_async** (`18004ae`, 2020-12-29, v0.1.0, 2 stars, MIT). Clone: `ext/asmiggle-umqtt_async/`.
- The right idea: the network is managed outside, signalled through a `network_status` flag
  (`umqtt_async.py:89-90`).
- But `read(n)` is not looped, so short reads break framing (L117-129).
- The condition `e.args[0] != EINPROGRESS or e.args[0] != ETIMEDOUT` is always true (L123).
- The keepalive sends pings but never times out a missing PINGRESP (L338-346).
- No SSL (L107-110). Abandoned.

**nznobody/micropython-umqtt.uasyncio2** (`d99b9be`, 2022-02-03, 0 stars, MIT).
- An asyncio port of `umqtt.simple2`. README: "a work-in-progress (WIP)… still outstanding known and unknown
  bugs".
- Blocking `getaddrinfo` and `ssl.wrap_socket` (`uasyncio2.py:219-226`).

### 5.9 Official micropython-lib `umqtt.simple` / `umqtt.robust`, synchronous

Clone: `ext/micropython-lib/`, HEAD `4fa59bd` (2026-09-23).

**Status:** `umqtt.simple` v1.8.1 (bumped `2693181` 2026-09-11); `umqtt.robust` v1.0.3. Active in 2026:
CONNACK length check, VBI for subscribe (fixes #969), and shared encoders (2026-07-28). Unsubscribe was added in
2025 (#1042).

**Blocking by design [verified]:**
- `connect()` runs `getaddrinfo`, a blocking TCP connect, an optional blocking `wrap_socket`, and a blocking
  CONNACK read (`simple.py:75-124`).
- QoS1 `publish()` waits for PUBACK with blocking reads (L150-159).
- `check_msg()` is non-blocking for the first byte only (L231-233). `wait_msg()` then calls
  `setblocking(True)` (L197), which erases the `connect(timeout=…)` timeout (P9).
  **[inference]** After the first `check_msg()`, a partially received packet can block forever. This is a
  plausible mechanism for the Pico W freeze in micropython-lib #951.
- QoS2 hits `assert 0` (L160-161, L224-225).
- No automatic ping (issue #909). The callback gets `(topic, msg)` with no retain flag (L219).

**`umqtt.robust`** blocks harder: `delay()` is `time.sleep(2)` and retries are unbounded (`robust.py:9-10,
19-45`).

**Not frozen into Pico W firmware** (P6). In Discussion #9530 Hinch called the official clients "best viewed as
demos" (quoted in §6).

### 5.10 fizista umqtt.simple2 / umqtt.robust2 (synchronous references)

- `simple2`: `1794e20`, 2022-12-23, PyPI 2.2.0; 79 stars.
- `robust2`: `c12c064`, 2024-09-02, PyPI 2.2.0 (2023-04-27); 53 stars. MIT.
- Synchronous, but every socket wait goes through `uselect.poll` with `socket_timeout` (default 5 s) and
  `message_timeout` (`simple2.py:18-19, 174-187`).
- `robust2` adds a bounded outgoing queue (`MSG_QUEUE_MAX = 5`), automatic resubscribe and `is_conn_issue()`
  (`robust2.py:13, 26-28, 131-138, 158-190, 325`). This is the design Hinch cites in `FUTURE_DEVELOPMENT.md`.
- TLS goes through blocking `ussl.wrap_socket` (`simple2.py:266-268`).
- Not usable under asyncio. Useful as a reference for queue semantics.

### 5.11 gregyedlik/micropython-holdfast (surprise, 2026)

Repo: https://github.com/gregyedlik/micropython-holdfast. HEAD `3cd3885` (2026-08-22, "Keep OTA sockets within
RP2 watchdog window"). MIT. Clone: `ext/gregyedlik-holdfast/`.

- "Resilient WiFi + MQTT + OTA scaffolding for unattended MicroPython devices (Raspberry Pi Pico W / Pico 2 W,
  ESP32…)."
- Deliberately built on `umqtt.simple`: "`umqtt.robust`'s auto-reconnect blocks the event loop in an unbounded
  retry and fights any external connection manager" (README; `holdfast/mqtt.py:13-15`).
- **But** it calls blocking `umqtt.simple` from asyncio tasks (`connect()` L58-73, `check_msg()` in
  `pump_task` L232-243), so `connect()` and QoS1 publish still block the loop.
- Operational patterns worth borrowing:
  - Application-level **ACK heartbeat**: publish a sequence number and require the server to echo it.
    "Detects failures that transport keepalive cannot: a half-open subscribe socket, or a broker that is up
    while the server behind it is down" (L259-358).
  - **WiFi radio power-cycling** after N consecutive MQTT reconnect failures. The source says this "can happen
    after upstream router/modem outages: cycling the CYW43 radio is cheaper than rebooting" (L81-90,
    L203-230).
  - Exponential backoff from 2 s to 60 s (L96-112).
  - Retained "latest value" publishing.
  - A supervisor that reboots when any task ends.

### 5.12 Excluded

- **belyalov/tinymqtt** (`aad84c8`, 2018-08-24, MIT):
  - Written for uasyncio v2: `yield uasyncio.IOWrite(sock)`, `IORead`, `loop.call_soon(generator)`
    (`client.py:198, 241, 216-217`). It cannot run on asyncio v3 (MicroPython ≥ 1.13).
  - Speaks MQTT 3.1 (`MQIsdp`, L119). Stores user/password but never sends them (L114-130, L322-326).
  - Good ideas: a single writer task draining a queue (L254-276) and resubscribe on reconnect (L220-223).
- **chrismoorhouse/micropython-mqtt** (`df542c8`, 2018-04-01, BSD-3): "async" means `_thread`
  (`src/mqtt.py:104, 190`), with `getaddrinfo` in the constructor (L52).
- **Joel-Edem/async-mqtt-client** (`4a5a8e1`, 2025-01-04, MIT):
  - Coroutine wrappers around blocking socket calls (`async_mqtt_client.py:49-50, 78-79`, plus
    `setblocking(True)` at L263).
  - A single-byte remaining-length field (L215) breaks any publish over 127 bytes.
  - Its own README: "You should probably not use this library unless you know what you are doing."
  - Idea worth noting: zero-allocation receive into a caller-supplied buffer (L282, L290).
- **andreicsp/upymqtt** (`9f790a2`, 2025-02-04): only a LICENSE file, despite "A fully async MQTT client".
- **ehong-tl/mqttsn-python3-micropython** (`0a6c920`, 2018-12-04, EPL/EDL, Paho-derived): MQTT-SN over UDP,
  using `_thread` and `time.sleep` (`umqttsn/MQTTSNclient.py:22, 275`). Needs an MQTT-SN gateway.
- **mateuszsury/beehiveMQTT** (2026): a MicroPython broker with QoS 0–2. Not a client; possibly useful as an
  on-bench reference.

### 5.13 CPython clients, as design references only

- **aiomqtt**: 2.5.1 (paho-based), and **3.0.0a1** (2026-04-02), which depends only on **`mqtt5`** 0.8.0. That
  is "A sans-I/O implementation of the MQTTv5 protocol for Python, written in Rust".
  - API (verified from the PyPI README): `async with aiomqtt.Client(...)`, `async for message in
    client.messages()`.
  - Advertised features: "No callbacks", "Complete MQTTv5 support (flow control, user properties, ...)",
    "Automatic reconnection", "Fine-grained control over acknowledgments".
  - **Takeaway:** a pure packet codec (bytes ↔ packet objects), separate from the transport and session state
    machine, can be unit-tested without sockets. That matches the project's Unix-port test tiers.
- `paho-mqtt` 2.1.0 ("MQTT version 5.0/3.1.1 client class"), `gmqtt` 0.7.0 (2024-11-22) and `amqtt` 0.12.1
  (2026-09-16, "asyncio-native MQTT broker and client"): metadata only, not inspected further.

---

## 6. Field reports (Pico W focus)

| # | Report | Date / board / firmware | What it says |
|---|--------|------------------------|--------------|
| F1 | [mqtt_as #88](https://github.com/peterhinch/micropython-mqtt/issues/88) "Horrible performance and frequency disconnections with Pico W? Disable power management" | 2022-07-30, Pico W | Calling `config(pm=0xa11140)` "radically improved the performance of MQTT communication. removing a 5 to 8 delay when MQTT subscriptions accepted by Pico W"; keepalive "DID NOT address the 5 to 8 second lag". mqtt_as now sets pm in `wifi_connect` (L743-746). Issue #109 refers to "before you disabled the power management on the Pico W by default". **This project already sets it** (`src/asy_wifi_service.py:326, 689`). |
| F2 | [mqtt_as #171](https://github.com/peterhinch/micropython-mqtt/issues/171) | 2025-04-30 (board not stated) | "sometimes during reconnection, `ssl.wrap_socket()` blocks … causes other coroutines to stop responding. In my case, this triggers WatchDog Timer to restart the MCU." Workaround: `do_handshake=False`. Still open. |
| F3 | [Discussion #10559](https://github.com/orgs/micropython/discussions/10559) TLS with umqtt on Pico W | 2023-01/02, Pico W | Measured handshakes on Pico W: **P-256 7.232 s, RSA-2048 8.016 s, P-384 11.288 s, RSA-4096 26.646 s** (JustinS-B, 2023-02-14). An ESP32 managed P-256 in about 1.9 s; Carglglz: "the hardware accelerator makes a big difference here". **[inference]** On RP2040, a blocking handshake meets or exceeds the 8388 ms watchdog cap. |
| F4 | [micropython#16290](https://github.com/micropython/micropython/issues/16290) + [Discussion #16288](https://github.com/orgs/micropython/discussions/16288) | 2024-11, Pico W, v1.24.0 | "error no 103 connection aborted" on outbound requests while `isconnected()` returned True, within 0–6 h. Only fix found: reverting to the 2024-06 (v1.23.0) build. This mirrors the CYW43 `isconnected()` false positive this project already backstops with a reset. |
| F5 | [micropython#18797](https://github.com/micropython/micropython/issues/18797), fixed by [#18805](https://github.com/micropython/micropython/pull/18805) | 2026-02, Pico 2 W, v1.26.1 | `getaddrinfo()` never returned with WiFi active but not connected; only a hard reset recovered. Fixed for 1.28.0, present in v1.29.0 (P8). |
| F6 | [micropython-lib #994](https://github.com/micropython/micropython-lib/issues/994) | 2025-04-02, Pico 1 W | "umqtt.simple cannot transmit longer messages than 125 ascii characters". The **same behaviour with peterhinch mqtt_as and bobveringa's fork**, with Wireshark retransmits; a raw TCP transfer of 20000 bytes was fine. [snippet] Per a mirror summary, the reporter tied it to v1.23.0 and a maintainer could not reproduce it. Still open. **[inference]** Add a payload-size sweep (≤ and > 125 bytes) to the bench tests. |
| F7 | [micropython-lib #951](https://github.com/micropython/micropython-lib/issues/951) | 2024-12-23, Pico W, v1.24.1 | umqtt "stops receiving broker responses after a subscribed message arrives" while ICMP ping still works; only tearing down and reconnecting recovers. Open, 9 comments. Possible mechanism: P9 [inference]. |
| F8 | [micropython-lib #909](https://github.com/micropython/micropython-lib/issues/909) | 2024-08-15 | umqtt keepalive "does not automatically send pings", so the broker disconnects at 1.5× keepalive. |
| F9 | [mqtt_as #161](https://github.com/peterhinch/micropython-mqtt/issues/161) | 2025-01-08, Pico W | `OSError: Connection Unstable`, raised from `wifi_connect`; "`mqtt.simple` worked" on the same setup. Open. |
| F10 | [mqtt_as #134](https://github.com/peterhinch/micropython-mqtt/issues/134) | 2024-02-18, Pico W | With weak WiFi at power-up the first connect "just quitted without re-trying" (`status=-1`/`-2`). Same class as [#183](https://github.com/peterhinch/micropython-mqtt/issues/183) (2026-09-20, ESP32: broker down at boot → `connect()` raises). |
| F11 | [mqtt_as #118](https://github.com/peterhinch/micropython-mqtt/issues/118) | 2023-07-25, Pico W | Sporadic resets reported as `PWRON_RESET`, "only seen this behaviour since using mqtt_as". Open, 14 comments (not readable here). |
| F12 | [mqtt_as #185](https://github.com/peterhinch/micropython-mqtt/issues/185) | 2026-10-02, Teensy 4.1 + Ethernet, **mqtt_as_eth** | A qos=0 publish issued just after the outage was detected was held and published late on reconnect. Closed 2026-10-04 with the README clarification (§5.1). |
| F13 | [Discussion #9530](https://github.com/orgs/micropython/discussions/9530) | 2022-10-06/07 | Peter Hinch: "WiFi suffers from outages which cause the official clients to fail. In my testing they only held up for about 30 minutes." "In my opinion they are best viewed as demos." karfas: "global state like the connection to an AP needs to be handled by the application, not some communication/protocol library." jimmo asked whether to "focus on an asyncio version instead and deprecate the one in micropython-lib". |
| F14 | [Discussion #10306](https://github.com/orgs/micropython/discussions/10306) | 2022-12-22, Pico W | umqtt kept failing with `OSError(113,)` (EHOSTUNREACH) against local Mosquitto; after switching to mqtt_as "now everything works just fine (both for ESP32 & RPi PICO W)". |
| F15 | [Discussion #13602](https://github.com/orgs/micropython/discussions/13602) | 2024-02-06, Pico W (Inky Frame), v1.21.0 | `MemoryError` after subscribing to a busy parent topic. glenn20: "the other incoming messages would cause increased memory fragmentation, even though you ignore them". He suggests `readinto()` into a reused buffer. **[inference]** Supports subscribing narrowly and preferring clients with pre-allocated receive buffers (mqtt_as) over per-read allocation (zcattacz, tve, aiomqttc). |
| F16 | [Discussion #10795](https://github.com/orgs/micropython/discussions/10795) | 2023-02, Pico W | umqtt messages stopped after about 25 s. peterhinch: "The `umqtt.simple` driver has a number of limitations, notably it doesn't keep the link open with MQTT ping requests." (The root cause turned out to be the campus network.) |
| F17 | forum.micropython.org | 2022 | [snippet] An mqtt_as user on an RP2040 board saw "the nonblocking socket produces OSError -110 on occasion" (viewtopic p=66435). Peter Hinch said the library assumes the device "would power up and initialise the MQTT connection", so "the 'already connected' state could never arise". Not verifiable from this session (domain blocked). |

**Error-code cheat sheet** for these reports (P13):
- 103 ECONNABORTED: the #16290 class.
- 113 EHOSTUNREACH: #10306.
- 110 / −110 ETIMEDOUT: `mqtt_as` treats −110 as "busy" on RP2 only (`mqtt_as/__init__.py:46-47`).
- −2: lwIP DNS failure from `getaddrinfo`.

---

## 7. Ranked recommendation

These are agent recommendations for the owner's PoC decision, not decisions.

**1. `mqtt_as_eth` from peterhinch/micropython-mqtt, pinned to a commit SHA and used from project code (as with
Microdot).**
- Why:
  - It is the only maintained lineage. The maintainer is active this very week, and it has years of Pico W
    field use (F1, F14).
  - It is the only candidate with the right division of labour: no WLAN control, while the API, resilience
    logic, ring-queue `async for` interface, response-time timeouts and keepalive match `mqtt_as` (§5.1).
  - It runs on the Unix port and CPython, which fits the project's test tiers.
- Preconditions and risks to resolve first:
  - **(a)** Its immaturity (10 days old; broken `package.json`; dead `_lan_connect`; the dropped RP2 `-110`
    busy code). Prefer pinning a later SHA once it settles, or vendoring the two files directly instead of
    using `mip`.
  - **(b)** `gc.collect()` at 1 Hz (L855) against SPECIFICATION I.4. This needs an owner decision, because
    `ext/` stays unmodified.
  - **(c)** Pass an **IP literal** from `asy_dns_client.py` so the first-connect `getaddrinfo` is instantaneous
    (P7). The address is cached forever, so re-resolution means rebuilding the client.
  - **(d)** No TLS on the LAN (P4/F2/F3). If TLS is ever needed, use `ssl_params={"do_handshake": False}` with
    ECDSA certificates, and measure per-step stalls against the 8388 ms watchdog.
  - **(e)** The deep-dive agent should confirm its behaviour on a WiFi drop that the project's WiFi service
    handles. It no longer touches WLAN, so it will only see socket errors and keepalive timeouts.

**2. Classic `mqtt_as` (WiFi variant): mature, but only if the project hands the WLAN to it, which contradicts
the existing WiFi service.**
- Its WLAN calls (L191-192, L743-747, L909) cannot be disabled by configuration. With no SSID, `connect()`
  raises `TypeError` on CYW43 (P11, #121).
- **Not recommended** for this architecture, despite being the more battle-tested file.

**3. A project-owned `src/asy_mqtt_client.py`, written to the project's Part C/D rules and modelled on
`mqtt_as_eth`'s session logic, with a sans-I/O codec in the `mqtt5`/aiomqtt style.**
- Transport: asyncio streams with `readexactly` (avoids P2), or the project's existing socket primitives.
- **[inference]** It removes the I.4 conflict, lets errors log through the project's FRAM-backed module logs,
  lets tasks register with `asy_system_service`'s supervisor, and allows bounded queues with explicit
  back-pressure.
- It is more work than vendoring, so it is a candidate for after the PoC rather than for the PoC itself.
- The owner's call: vendor-and-wrap versus own-and-test.

**4. `zcattacz/mqtt_as`: a fallback or reference only.**
- It has the same "no network management" model, plus a CPython shim, and is fully application-driven: no
  auto-reconnect, which actually suits an external supervisor.
- But it is single-maintainer, a 2022 base without the 0.8.x fixes or v5, polls every 5 ms, allocates on every
  read, and has a blocking TLS handshake.

**Not recommended:**
- `tve/mqtt_async`: keepalive is silently dead; unmaintained.
- `aiomqttc`: HEAD does not parse; non-builtin exception names; no retransmit or resubscribe.
- `asyncmd` / PR #722: short-read framing risk; no session management. A good *TLS-path* reference, though.
- PR #1086: malformed QoS1 publish; TypeError on PINGRESP.
- `umqtt_async`, `uasyncio2`, `tinymqtt`, `chrismoorhouse`, `Joel-Edem`, `upymqtt`, MQTT-SN.
- `umqtt.simple`/`robust` and `simple2`/`robust2`: blocking.
- `holdfast`: blocking underneath, but its heartbeat, radio-cycling and backoff patterns are worth adopting
  at the service level.

---

## 8. What would still be missing, whichever library is chosen

1. **Link-state coupling with `asy_wifi_service.py`.** The client should be *told* the link is down or up
   (pause, fail fast, resume) rather than discover it through socket errors or keepalive timeouts. That
   detection can take up to 4 × ping interval in mqtt_as. The CYW43 `isconnected()` false positive (F4) means
   the MQTT keepalive, or a holdfast-style end-to-end ACK heartbeat, is also the project's best detector of a
   silently dead uplink. It could feed the existing reset backstop.
2. **Non-blocking name resolution.** Resolve with `asy_dns_client.py`, connect by IP, and re-resolve on
   reconnect. mqtt_as caches the address forever.
3. **TLS.** None of the candidates offers a handshake that is safe against the watchdog on RP2040 (P4,
   F2, F3). Plain MQTT on the trusted LAN is the low-risk PoC path.
4. **Outbound back-pressure policy.**
   - mqtt_as `publish()` pauses for the whole outage and publishes late (F12, README `1700feb`).
   - Nothing offers a bounded, droppable outbound queue for sensor readings (robust2's `MSG_QUEUE_MAX` is the
     closest model).
   - Inbound: mqtt_as's overwrite-oldest ring (`MsgQueue`) with a `discards` counter is the only explicit
     back-pressure in the field.
5. **Task supervision and observability.** Every candidate spawns fire-and-forget `create_task`s
   (`mqtt_as` L819-832). None registers with a supervisor or logs to persistent error counters; the project
   would need wrapper-level restart and error accounting.
6. **Memory discipline.**
   - mqtt_as's 1 Hz `gc.collect()` (§5.1) conflicts with SPECIFICATION I.4.
   - Per-message allocations need measuring at both GC stages (`-1` and `32768`), with zero `MemoryError`s.
   - Subscribe narrowly (F15).
7. **QoS 2 and full MQTT v5:** not available client-side in the ecosystem. mqtt_as's v5 is a subset.
8. **Payload-size behaviour on Pico W** (F6, ~125 bytes): an open report that hits every client, including
   mqtt_as. It needs a bench check.
9. **Test coverage per the project's rules:**
   - A mock broker for the unit and digital-twin tiers. mqtt_as_eth's CPython and Unix support helps.
   - Hazard tests for shared resources: sockets, the heap, and the asyncio loop under webserver load.
   - Fault injection for broker-down-at-boot (F10, #183), half-open TCP, and DNS failure.
10. **Packaging under the `ext/` policy.** No tags exist, so pin a commit SHA. Vendor only `mqtt_as_eth/__init__.py`
    (plus `mqtt_v5_properties.py` if v5 is wanted), byte-identical, and add a refresh entry to the
    every-external-dependency update practice.

---

## 9. Source index

Clones (all under `…/scratchpad/ext/`, read-only):

| Directory | Repo | Commit |
|-----------|------|--------|
| `peterhinch-mqtt_as/` | peterhinch/micropython-mqtt | `dd03ab3` 2026-10-07 |
| `zcattacz-mqtt_as/` | zcattacz/mqtt_as | `3ab976a` 2025-11-25 |
| `tve-mqboard/` | tve/mqboard | `98bcdd0` 2022-05-08 |
| `kevinkk525-micropython-mqtt/` | kevinkk525/micropython-mqtt | `6e25ac7` (master); `2067e57` (hardware_independent) |
| `kevinkk525-pysmartnode/` | kevinkk525/pysmartnode | `a0998ad` 2020-09-01 |
| `microhomie/` | microhomie/microhomie | `67324a9` 2021-01-07 |
| `tangerino-aiomqttc/` | Tangerino/aiomqttc | `b4cf7e8` 2025-05-21 (does not parse) |
| `aiomqttc-pypi-1.0.7/` | PyPI sdist aiomqttc 1.0.7 | — |
| `carglglz-asyncmd/` | Carglglz/asyncmd | `3f5c067` 2024-03-20 |
| `micropython-lib/` | micropython/micropython-lib | `4fa59bd` 2026-09-23; branches `pr722`, `pr1086` |
| `mplib-pr1086/` | extracted PR #1086 file | — |
| `asmiggle-umqtt_async/` | a-smiggle/umqtt_async | `18004ae` 2020-12-29 |
| `nznobody-uasyncio2/` | nznobody/micropython-umqtt.uasyncio2 | `d99b9be` 2022-02-03 |
| `umqtt_simple2/` | fizista/micropython-umqtt.simple2 | `1794e20` 2022-12-23 |
| `fizista-robust2/` | fizista/micropython-umqtt.robust2 | `c12c064` 2024-09-02 |
| `gregyedlik-holdfast/` | gregyedlik/micropython-holdfast | `3cd3885` 2026-08-22 |
| `belyalov-tinymqtt/` | belyalov/tinymqtt | `aad84c8` 2018-08-24 |
| `chrismoorhouse-mqtt/` | chrismoorhouse/micropython-mqtt | `df542c8` 2018-04-01 |
| `joeledem-async-mqtt-client/` | Joel-Edem/async-mqtt-client | `4a5a8e1` 2025-01-04 |
| `andreicsp-upymqtt/` | andreicsp/upymqtt | `9f790a2` (empty) |
| `ehongtl-mqttsn/` | ehong-tl/mqttsn-python3-micropython | `0a6c920` 2018-12-04 |
| `mp-v1.29.0-landscape/` | micropython/micropython | tag `v1.29.0` = `0fd6c57` (sparse) |

Web sources:
- Issues, PRs and Discussions are linked inline in §5–§6.
- PyPI JSON for `aiomqttc`, `micropython-mqtt`, `micropython-mqtt-async`, `micropython-umqtt.simple2`,
  `micropython-umqtt.robust2`, `micropython-umqtt.simple`, `aiomqtt`, `mqtt5`, `paho-mqtt`, `gmqtt` and
  `amqtt` (2026-10-07).
