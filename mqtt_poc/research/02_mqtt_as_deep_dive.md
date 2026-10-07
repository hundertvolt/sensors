> **Raw research report** (agent, 2026-10-07): written by a read-only research agent of the MQTT PoC research session, kept verbatim as the evidence base for `mqtt_poc/RESEARCH.md`. Tags such as [V]/[SRC] mean verified in source by that agent; [I]/[INFERENCE] are not verified; nothing here was run on hardware. Clone paths (`<research-session scratchpad>/ext/...`) refer to that session's temporary scratchpad, not to this repo. Line anchors into this repo are as of `1cff5a2`.

# mqtt_as deep dive: Peter Hinch's asyncio MQTT client, evaluated for an RP2040/CYW43 device on MicroPython v1.29.0

Research date: 2026-10-07. Nothing from the cloned repositories was executed; everything below was found by reading the source.

## 0. Sources, method and how to read the tags

| Source | Pin | Local path |
|---|---|---|
| `peterhinch/micropython-mqtt` | `dd03ab3bb8067658d1103292c36797bc5f259f83`, 2026-10-07 18:45:47 +0100, "Further work on CPython compatibility." (full history fetched: 298 commits) | `scratchpad/ext/micropython-mqtt/` |
| MicroPython | tag `v1.29.0` = `0fd6c573ea81`, 2026-08-24 (sparse: `extmod/`, `py/`, `ports/rp2/`, `ports/unix/`) | `scratchpad/ext/micropython/` |
| micropython-lib `ssl.py` | `ee4bb8ff139e`, the submodule commit that v1.29.0 pins | `scratchpad/ext/mplib/ssl.py` |
| mosquitto `src/handle_connect.c` | `master` as fetched 2026-10-07 (exact commit not recorded) | `scratchpad/ext/mosquitto/` |

`scratchpad` = `/tmp/claude-0/-home-user-sensors/096ae655-ad17-556e-88d8-dfa45babcdb6/scratchpad`. Unless a section says otherwise, line references are into `mqtt_as/__init__.py` at the pinned commit.

**Tags used throughout:**
- **[V]** verified by reading the cited source.
- **[I]** inference from code reading, not run or measured.
- **[R]** reported in an issue or PR body and not independently verified.

**Access limits.**
- GitHub issue pages render their comment threads client-side, and the session policy blocked the REST API, GraphQL and `gh`. Issue summaries therefore come from the issue body plus the repo's own commits that reference them.
- PR pages do render their conversations, so PR comments are quoted.
- `forum.micropython.org`, `docs.oasis-open.org` and `docs.solace.com` were blocked by the egress proxy. For the MQTT "Session Present" behaviour I checked mosquitto's source instead of the spec text.
- The repo has GitHub Discussions disabled (the tab returns 404).

## 1. Variants in the repository

| Path | What it is | Version | WiFi coupling |
|---|---|---|---|
| `mqtt_as/__init__.py` (960 lines) | The main library ("wireless"). | `VERSION = (0, 8, 5)` (line 31) | Hard: `import network` (line 26). Owns `network.WLAN(STA_IF)`. |
| `mqtt_as/mqtt_v5_properties.py` (239 lines) | MQTTv5 property encode/decode. It is imported lazily by a *relative* import (line 216) only when `mqttv5` is set. | — | none |
| `mqtt_as_eth/__init__.py` (906 lines) | **New since 2026-09-27** (`ac0492d`). A copy of the main library with all WiFi code removed, for wired Ethernet, the Unix port and (since 2026-10-06/07) CPython. | `VERSION = (0, 1, 0)` (eth:42) | **None**: no `network` import. |
| `mqtt_as/mqtt_as_timeout.py` | Kevin Köck's 2019 subclass that adds a publish timeout. It still uses `uasyncio`. | — | via the parent class |
| `mqtt_as/{range,range_ex,clean,unclean,tls,tls32,tls8266,lptest_min,async_message,main}.py`, `mqtt_as/v5/{basic,cbtest}.py` | Demos | — | — |
| `mqtt_as/tests/{v3,v5}/{test,target}.py` | Manual two-device protocol tests that print PASS/FAIL. They need a live broker at `192.168.0.10`, `mqtt_local.py` and `primitives.RingbufQueue` from micropython-async. | — | — |
| `mqtt_local_example.py` | Config template plus LED helpers | — | — |
| `gateway/` | ESP-NOW gateway (ESP32 only). Not relevant here. | — | — |
| `FUTURE_DEVELOPMENT.md` | The author's case for a rewrite, quoted in section 9. | — | — |

Repo housekeeping, all [V]:
- **No tags and no releases.** `git ls-remote --tags` returns 0, so vendoring has to pin a commit.
- **No CI.** There is no `.github/` directory.
- Side branches `pid-fix`, `publish-timeout`, `read_allocate` and `protocol_tests` are stale (2019–2025) and carry nothing that master lacks, apart from one 2019 demo.
- `mqtt_as_eth/package.json` is **invalid JSON**. CPython's `json` rejects it with "Illegal trailing comma before end of array: line 6 column 96". It also lists `mqtt_as_eth/unix_test.py`, which does not exist (renamed to `pc_test.py`), and leaves out `pc_test.py`, `pc_tls.py` and `v5_test.py`.
- `mqtt_as_eth/__init__.py:451-456` `_lan_connect()` calls `self.wan_ok()`, which the eth variant deleted. It is dead code that would raise `AttributeError`, but nothing calls it.

Activity, [V] from the log:
- 2026-03-14 `980a3fe`: Nano RP2040 Connect support (0.8.5).
- 2026-09-02 PR #182: static IP.
- 2026-09-27: `mqtt_as_eth`.
- 2026-10-04: README clarification on `publish()` during an outage.
- 2026-10-06 and 2026-10-07: CPython support in `mqtt_as_eth`.

The project is maintained and actively changing right now. The eth variant in particular is about 10 days old.

## 2. Architecture (Q1)

### 2.1 Classes and config

- `config` (lines 89-113) is a **module-global dict** that holds the defaults. You mutate it and pass it to `MQTTClient(config)`.
  - Keys: `client_id` (default `hexlify(unique_id())`), `server`, `port` (0 means 1883, or 8883 with ssl), `user`, `password`, `keepalive=60`, `ping_interval=0`, `ssl=False`, `ssl_params={}`, `response_time=10`, `clean_init=True`, `clean=True`, `max_repubs=4`, `will=None`, `subs_cb`, `wifi_coro=eliza`, `connect_coro=eliza`, `ssid=None`, `wifi_pw=None`, `queue_len=0`, `gateway=False`, `mqttv5=False`, `mqttv5_con_props=None`.
  - `ifconfig` is optional and absent from the defaults. It is read from the **module-global** `config`, not from the dict passed to the constructor (lines 721, 735, 748: `if 'ifconfig' in config:`). [V] That is a bug from PR #182: a client built from a different dict silently ignores its `ifconfig`.
- `MsgQueue` (lines 60-86): a ring buffer plus an `asyncio.Event`, exposed as `client.queue`, an async iterator. Details in section 6.
- `MQTT_base` (lines 146-691): the protocol layer "on the basis of a good connection". Methods: `_as_read`, `_as_write`, `_connect`, `_ping`, `publish`, `_publish`, `subscribe`, `unsubscribe`, `_usub`, `wait_msg`, `kill_pid`, `wan_ok`, `broker_up`, `disconnect`, `close`.
- `MQTTClient(MQTT_base)` (lines 697-960): adds connectivity handling: `wifi_connect`, `connect`, `_handle_msg`, `_keep_alive`, `_kill_tasks`, `_memory`, `isconnected`, `_reconnect`, `_connection`, `_keep_connected`, plus the retrying `subscribe`/`unsubscribe`/`publish` wrappers.
- Class variables: `DEBUG = False` and `REPUB_COUNT = 0`. `dprint()` (lines 227-229) is `print(msg % args)`, and the README (3.2.10) says it may be overridden in a subclass. That is the logging hook.

### 2.2 Every background task: who starts it, who stops it

All [V].

| Task | Created at | Tracked in `self._tasks`? | Ends when | Cancelled by |
|---|---|---|---|---|
| `_keep_connected()` | `connect()` line 822, **once**, on the first successful connect | **no** | `_has_connected` becomes False (only via `disconnect()`) and the loop re-checks it | nothing; never cancelled |
| `_handle_msg()` | `connect()` line 825, **on every successful (re)connect** | **no** | `isconnected()` turns False, or an `OSError` is caught. **Any other exception ends it without calling `_reconnect()`** (lines 836-847). | not cancelled; `_kill_tasks` closes the socket under it |
| `_keep_alive()` | line 826, every connect | yes | ping failure, or `pings_due >= 4` | `_kill_tasks()` |
| `_memory()` | line 828, only if `DEBUG` | yes | never (`while True`) | `_kill_tasks()` |
| user `wifi_coro(True/False)` | lines 819 and 894 (callback mode only) | no | user code | never |
| user `connect_coro(client)` | line 832 (callback mode only) | no | user code | never. Issue #147: an outage during the handler leaves it running, so a reconnect starts a second copy |
| `_kill_tasks(True)` | `_reconnect()` line 890, fire-and-forget | no | runs once | — |

```python
# mqtt_as/__init__.py:818-832
        if not self._events:
            asyncio.create_task(self._wifi_handler(True))  # User handler.
        if not self._has_connected:
            self._has_connected = True  # Use normal clean flag on reconnect.
            asyncio.create_task(self._keep_connected())
            # Runs forever unless user issues .disconnect()

        asyncio.create_task(self._handle_msg())  # Task quits on connection fail.
        self._tasks.append(asyncio.create_task(self._keep_alive()))
        if self.DEBUG:
            self._tasks.append(asyncio.create_task(self._memory()))
        if self._events:
            self.up.set()  # Connectivity is up
        else:
            asyncio.create_task(self._connect_handler(self))  # User handler.
```

`_kill_tasks()` (lines 864-870) cancels only `_keep_alive` and `_memory`. It then `await asyncio.sleep_ms(0)` and closes the socket. `_handle_msg` exits on its own when its next socket call fails or `isconnected()` is False.

`isconnected()` has side effects [V] (lines 879-885). If the library believes it is connected but `self._sta_if.isconnected()` is False, it calls `_reconnect()`, which spawns tasks. Any user call to `isconnected()` can therefore start the teardown.

### 2.3 `disconnect()` and `close()`

All [V] unless tagged.

```python
# mqtt_as/__init__.py:438-460
    async def disconnect(self):
        if self._sock is not None:
            await self._kill_tasks(False)  # Keep socket open
            try:
                async with self.lock:
                    self._sock.write(b"\xe0\0")  # Close broker connection
                    await asyncio.sleep_ms(100)
            except OSError:
                pass
            self._close()
        self._has_connected = False
...
    def close(self):  # API. See https://github.com/peterhinch/micropython-mqtt/issues/60
        self._close()
        try:
            self._sta_if.disconnect()  # Disconnect Wi-Fi to avoid errors
        except OSError:
            self.dprint("Wi-Fi not started, unable to disconnect interface")
        self._sta_if.active(False)
```

What `disconnect()` does:
- It does **not** set `_isconnected = False`.
- `_handle_msg` keeps running until its next `sock.read(1)` on the closed socket raises EBADF. It then calls `_reconnect()`, which **fires a spurious "down" event / `wifi_coro(False)`**.
- `_keep_connected` then sees `_has_connected == False` and exits.
- A `publish()` issued after `disconnect()` waits in `_connection()` forever, because nobody reconnects any more. [I]
- The README admits this (5.2): "the library has no mechanism to ensure all tasks are shut down cleanly after issuing `.disconnect`."

What `close()` does:
- It **deactivates the WLAN interface**: `active(False)`.
- It cancels nothing. If the event loop keeps running after `close()`, `_handle_msg` hits EBADF, `_reconnect()` runs, and `_keep_connected` calls `wifi_connect()`, which calls `active(True)` and rejoins. [I] `close()` is meant to be called only after `asyncio.run()` has returned, in a `finally:` block, as every demo does.

### 2.4 Connection state machine

All [V] from lines 785-931 and 438-460.

```
                 MQTTClient(config)
   __init__: WLAN(STA_IF).active(True)   (sync, line 191-192)
                       |
                       v
  +---------------- INIT ------------------------------------------------------+
  | _has_connected=F, _isconnected=F, _in_connect=F                             |
  +-------------------+---------------------------------------------------------+
                      | user: await connect(quick)
                      v
  FIRST-CONNECT: wifi_connect(quick) [<=60 s join + 5 s stability unless quick]
                 _addr = socket.getaddrinfo(server, port)   (SYNC, once only)
                 _in_connect=T ; [_connect(True); write DISCONNECT; sleep 2]  (clean_init && !clean, v3 only)
                 _connect(clean)  : socket(), setblocking(False), connect()->EINPROGRESS,
                                    [ssl.wrap_socket()  SYNC handshake], CONNECT, await CONNACK
        | any exception: _close(), _in_connect=F, re-raise to the caller (app must retry)
        v success
  UP: _isconnected=T, _in_connect=F, rcv_pids.clear()
      tasks: _handle_msg (5 ms poll), _keep_alive, [_memory], _keep_connected (1 s loop, gc.collect())
      notify: up.set() | wifi_coro(True) + connect_coro(client)
        |
        | trigger: STA link down (seen in isconnected()), OSError in a read/write/handler,
        |          "Empty response" (EOF), 4 ping intervals with no rx, PUBACK/SUBACK timeout,
        |          QoS1 max_repubs exhausted, reason code >= 0x80, unknown PID ...
        v  _reconnect(): _isconnected=F; spawn _kill_tasks(True); down.set() | wifi_coro(False)
  DOWN (socket closed, keepalive cancelled)
        |  _keep_connected loop (every pass):
        |    _sta_if.disconnect()          <-- WiFi torn down even for a pure broker outage
        |    sleep 1 s
        |    wifi_connect()                <-- active(True), config(pm=0xA11140), connect(ssid,pw),
        |                                      <=60 s, then 5 s "integrity" check (quick=False)
        |      OSError -> continue (back to the top of DOWN)
        |    connect()  (no DNS; same cached _addr)
        |      OSError -> _close(); _in_connect=F; _isconnected=F; loop
        |      non-OSError -> escapes and _keep_connected DIES -> client stuck DOWN forever
        v success -> UP (new _handle_msg/_keep_alive; up/connect_coro again)

  user: await disconnect()  -> kill keepalive, write DISCONNECT, close socket,
                               _has_connected=F  -> _keep_connected exits at its next check
                               (spurious "down" fired via _handle_msg EBADF; see 2.3)
  user: close()             -> close socket, STA disconnect, STA active(False)
```

There is no retry limit, no backoff and no jitter anywhere in the cycle. [V]

## 3. WiFi coupling (Q2), the critical point for this project

### 3.1 Every `network.WLAN` call in `mqtt_as/__init__.py`

All [V].

| Where | Call | When |
|---|---|---|
| line 191-192 | `self._sta_if = network.WLAN(network.STA_IF)`; `self._sta_if.active(True)` | **in the constructor**, synchronously |
| lines 196-199 | `sta.active()` polled with `time.sleep(0.1)`; `sta.config(pm=sta.PM_NONE)` | only with `gateway=True` (ESP32) |
| line 742 | `s.active(True)` | every `wifi_connect()` |
| lines 743-746 | `s.config(pm=0xA11140)` | every `wifi_connect()` on RP2, except NINA |
| line 747 | `s.connect(self._ssid, self._wifi_pw)` | every `wifi_connect()`, even if already connected |
| lines 748-749 | `s.ifconfig(config['ifconfig'])` (module-global `config`, see 2.1) | optional |
| lines 750-769 | `s.isconnected()` / `s.status()` polled once per second, up to 60 times. RP2: break unless `1 <= status() <= 2` | `wifi_connect()` |
| lines 770-772 | `s.disconnect()` on a 60 s timeout | `wifi_connect()` |
| lines 779-781 | `s.isconnected()` five times, 1 s apart, ending in `OSError("Connection Unstable")` | `wifi_connect(quick=False)`, i.e. every reconnect |
| line 883 | `self._sta_if.isconnected()` | **every `isconnected()` call**, which means on every `_handle_msg` iteration (about 200/s) and every `_as_read`/`_as_write` loop pass |
| line 910 | `self._sta_if.disconnect()` | **every pass of the `_keep_connected` DOWN branch** |
| lines 457 and 460 | `self._sta_if.disconnect()`; `self._sta_if.active(False)` | `close()` |

```python
# mqtt_as/__init__.py:903-917
    async def _keep_connected(self):
        while self._has_connected:
            if self.isconnected():  # Pause for 1 second
                await asyncio.sleep(1)
                gc.collect()
            else:  # Link is down, socket is closed, tasks are killed
                try:
                    self._sta_if.disconnect()
                except OSError:
                    self.dprint("Wi-Fi not started, unable to disconnect interface")
                await asyncio.sleep(1)
                try:
                    await self.wifi_connect()
                except OSError:
                    continue
```

### 3.2 What happens on rp2 specifically

All [V] against `extmod/network_cyw43.c` at v1.29.0.

- **`config(pm=0xA11140)`.** `CYW43_PM_VALUE()` (network_cyw43.c:43-48) decodes it as `li_assoc=10`, `li_dtim=1`, `li_beacon=1`, `pm2_sleep_ret=200 ms`, **`pm_mode=0` (no power save)**. So this is "power saving off", with the PERFORMANCE mode's timing fields.
  - The project's own `src/asy_wifi_service.py:326,689` writes the identical value, so the two would not fight over the value itself.
  - The source is the Pico W "connecting to the internet" PDF §3.6.3, cited in the code. The motivation is issue #88 [R]: 5–8 s MQTT lag with power management on.
- **`connect()`** (network_cyw43.c:251-315) starts a background `cyw43_wifi_join` and returns. **`ssid` is a required buffer argument**: `mp_get_buffer_raise(args[ARG_ssid].u_obj, ...)`. So with `config['ssid'] = None` on rp2, `wifi_connect()` raises **`TypeError`**, not `OSError`.
  - On the first connect, that `TypeError` reaches the application.
  - Inside `_keep_connected` (which catches only `OSError`, lines 916 and 925) it **kills the reconnect task for good**. [V] code; [I] consequence.
  - Conclusion: you cannot switch off WiFi management by leaving `ssid` unset.
- **`isconnected()`** (network_cyw43.c:324-337) is `cyw43_tcpip_link_status(...) == CYW43_LINK_UP`, i.e. joined and holding an IP. It is cheap C with no blocking.
- **`status()`** returns the CYW43 link status: 0 down, 1 join, 2 no IP, 3 up, -1 fail, -2 no network, -3 bad auth. The RP2 loop keeps waiting while the status is 1 or 2.
- **`active(False)`** on STA calls `cyw43_wifi_leave()` and then `cyw43_wifi_set_up(..., false)` (network_cyw43.c:140-152). `close()` therefore takes down the whole STA interface.
- **`BUSY_ERRORS = [EINPROGRESS, ETIMEDOUT, -110]` on rp2** (lines 46-47).
  - Added 2022-04-22 (`03b22aa`) for the Nano RP2040 Connect, and narrowed to Pico W ("RP2 and not NINA") in `980a3fe`, 2026-03-14.
  - Where -110 comes from [I]: the TLS layer returns `-err` for underlying socket errors (`_mbedtls_ssl_recv/_send`, modtls_mbedtls.c:678-708), so -110 is a sign-inverted `ETIMEDOUT` reaching the TLS socket. mqtt_as treats it as "busy" until `response_time` runs out.

### 3.3 Can it be told not to manage WiFi?

**Not in `mqtt_as/__init__.py`.** [V]
- The constructor activates STA.
- `wifi_connect()` always joins with its own credentials.
- Every outage, broker-only outages included, runs `_sta_if.disconnect()` and then rejoins with a 5 s stability wait.
- `close()` deactivates STA.

Consequences for this project's `asy_wifi_service.py`, which owns `network.WLAN` (sets pm, runs a hotspot phase, calls `disconnect()`/`active(False)` itself at lines 365-366, 375 and 669-670). All [I] from the code:
1. **A broker outage becomes a device-wide WiFi outage.** On every pass of the DOWN branch, mqtt_as drops the STA link, rejoins, waits 5 s, tries the broker, fails, and drops the link again. That cycle repeats roughly every 7–10 s for as long as the broker is down. The webserver, NTP and DNS lose connectivity with it.
2. **Two state machines drive one radio.** For example, mqtt_as would `active(True)` and `connect(ssid)` while the project's service is deliberately in its hotspot phase or in its own reconnect sequence. Issues #59 and #61 [R] report the ESP32 version of this collision ("sta is connecting, return error", "Wifi Internal Error"). The maintainer's position, quoted in a 2021 forum post that surfaced only as a search snippet [R, unverified]: the library "assumed the device would connect once at power-up", and as a stopgap one should "disconnect from WiFi before initialising mqtt_as".
3. The maintainer has repeatedly declined to make WiFi external in the core library:
   - Issue #122 (open, unanswered): "wifi is treated as internal details only".
   - PR #57 (2021, open and stale; it added a `BaseInterface`).
   - PR #167 (2025, open). Maintainer, 2025-03-06: "wary of adding complexity to the core `mqtt_as`… a stripped-down version for wired interfaces … may be the best way forward."

    That stripped-down version is `mqtt_as_eth`.

**`mqtt_as_eth/__init__.py` has no WLAN coupling at all.** [V]
- `isconnected()` is pure MQTT state (eth:836-839).
- `_keep_connected` just sleeps 1 s and calls `connect()` again (eth:851-873).
- `close()` only closes the socket (eth:487-489).
- On rp2 it gets `machine.unique_id` through `get_unique_id()` (eth:57-82).
- README §10: "Potentially any device providing a `socket` interface may be employed … If attempting to use a platform that requires programmatic intervention to re-establish lost connectivity, it is the responsibility of the application to supply it."

Caveats for using it on rp2 over the project's WLAN:
- [V] It is v0.1.0 and 10 days old. Its CPython adaptations landed on 2026-10-06 and 2026-10-07.
- [V] TLS is described as "not yet tested on these platforms", meaning the Unix build and CPython.
- [V] Its MicroPython `wait_msg` drops the RP2 `BUSY_ERRORS` handling (eth:594-603). Any `OSError` there, including a TLS -110, reconnects instead of retrying [I].
- [V] It has no link-state fast path, so a WiFi drop is noticed only by socket errors or the keepalive timeout (section 5). Feeding the project's WiFi-service state into it would take a subclass `isconnected()` override [I].

There are two integration options, both [I] and neither decided here:
- **(a)** Vendor `mqtt_as_eth` and subclass it to add link awareness.
- **(b)** Vendor `mqtt_as` and, right after construction, replace `client._sta_if` with a shim. The shim's `active`, `config`, `connect`, `disconnect` and `ifconfig` are no-ops; `isconnected()` and `status()` delegate to the project's WiFi service. The constructor's `active(True)` (line 192) would still hit the real interface once. The 5 s "integrity" loop and the 1 s sleep would still run on every reconnect.

## 4. Blocking calls and polling cost (Q3)

### 4.1 Calls that can hold the asyncio loop

| # | Call | Where | Blocks? | For how long |
|---|---|---|---|---|
| B1 | `network.WLAN(STA_IF).active(True)` | constructor, lines 191-192 | sync C | [I] on a cold radio, CYW43 firmware load, typically hundreds of ms; otherwise short |
| B2 | `socket.getaddrinfo(self.server, self.port)` | line 790, **first `connect()` only** (and again after `disconnect()`) | **yes** [V]: `lwip_getaddrinfo` spins `poll_sockets()` until the DNS callback fires (modlwip.c:1872-1881) | numeric IP: no DNS query, immediate [V, project SPECIFICATION F.2 cites lwIP `dns.c:1605-1606`]. Hostname: until lwIP's DNS gives up, several seconds [I]. The code's own comment says: "Note this blocks if DNS lookup occurs. Do it once…" |
| B3 | `sock.connect(addr)` on a non-blocking socket | line 302 | **no** [V]: one `poll_sockets()`, then `OSError(EINPROGRESS)` (modlwip.c:1234-1243). In `BUSY_ERRORS`. | µs |
| B4 | `ssl.wrap_socket(sock, **ssl_params)` | line 314 | **yes, by default** [V]. micropython-lib `ssl.wrap_socket(..., do_handshake=True)` (ssl.py:44-65) leads to the C loop `while ((ret = mbedtls_ssl_handshake(...)) != 0) { … mp_event_wait_ms(1); }` (modtls_mbedtls.c:818-824). There is **no timeout**, and no Python task runs. On the non-blocking socket it spins through the TCP connect and the whole handshake. | handshake RTTs plus RP2040 public-key crypto: **seconds** [I]. With an unresponsive peer, until lwIP aborts the TCP connection (tens of seconds to minutes [I]). **Issue #171 (open, unanswered):** "ssl.wrap_socket() hangs on reconnecting … this triggers WatchDog Timer to restart the MCU". Workaround: `ssl_params={'do_handshake': False}` (README §9). The handshake then advances inside the non-blocking `_as_write` loop; each mbedtls step is still a synchronous CPU burst [I]. |
| B5 | `sock.write(buf)` | `_as_write` line 277, plus raw writes at lines 443 and 803 | **mostly no** [V]: returns `None` on EAGAIN (py/stream.c:255-263) and while the socket is still connecting (modlwip.c:757-769). **But** on lwIP `ERR_MEM`, `lwip_tcp_send` retries `tcp_write` up to 200 × `mp_hal_delay_ms(50)`. The source comment: "if the socket is non-blocking then this code will actually block until there's enough memory" (modlwip.c:797-812). | **up to 10 s** in the lwIP-out-of-pbufs case [V code; I how often it happens] |
| B6 | `sock.readinto(mv, n)`, `sock.read(1)` | lines 250 and 568 | no [V]: EAGAIN gives `None` (py/stream.c:222-232; modlwip.c:852-858) | memcpy |
| B7 | `time.sleep(0.1)` loop | lines 196-197 | yes | `gateway=True` only (ESP32). Not reached on rp2. |
| B8 | `gc.collect()` | lines 15, 19, 23, 28 (import); **907 (every 1 s while connected)**; 876 (every 20 s with DEBUG) | yes, a full mark-sweep | [I] a few ms per collection on a ~200 KB RP2040 heap, once per second for the life of the device |
| B9 | user `subs_cb` | called at line 684 **while `_handle_msg` holds `self.lock`** | as long as the callback runs | user-defined; it blocks every publish and ping |

### 4.2 How the non-blocking sockets are read

All [V].
- **Polling only.** There is no `select.poll`, no `ipoll`, and no `asyncio` stream/`_io_queue` integration anywhere. Grep finds no `select`, `poll` or `StreamReader`.
- **Idle reader.** `_handle_msg` (lines 836-847) loops `isconnected()`, then `async with self.lock`, then `wait_msg()` (one `sock.read(1)`), then `await asyncio.sleep_ms(5)`.
  - That is a **~200 Hz poll for the entire life of the connection.**
  - The 5 ms value (it used to be 20, then 0) is the workaround for issue #166 (`63f734e`, 2025-02-20): with 0, Ctrl-C and STDIN over WebREPL stopped working.
- **Mid-packet reads and all writes** (`_as_read`/`_as_write`) spin with `await asyncio.sleep_ms(0)` between attempts until data arrives or `response_time` (10 s) runs out. While waiting for the CONNACK, the TCP connect, or the rest of a packet, that coroutine is runnable on every scheduler pass, so the loop never idles [I from `extmod/asyncio/core.py` semantics]. It yields, so other tasks run, but CPU use sits near 100% for the wait.
- **QoS1 and SUBACK waits** poll `rcv_pids` every 100 ms (`_await_pid`, lines 462-470). Each QoS1 `publish()` therefore returns up to 100 ms after its PUBACK arrives, so one publishing task manages roughly 10 QoS1 messages/s at most [I].
- **Waiting for a reconnect.** `_connection()` polls every 1 s (lines 897-899).

**Heap churn of the idle poll.** Sources [V], sizes [I]. Each idle `_handle_msg` iteration allocates:
1. the `__aenter__` coroutine;
2. the `Lock.acquire` generator (`extmod/asyncio/lock.py:33-55`);
3. the `wait_msg()` coroutine (`py/objgenerator.c:61-64`: every generator call is `mp_obj_malloc_var`);
4. the `__aexit__` coroutine;
5. a 2-byte vstr inside `sock.read(1)`, freed again on EAGAIN (py/stream.c:219-231).

`asyncio.sleep_ms` itself allocates nothing (a singleton generator, `core.py:54-58`).

Estimated cost: about 4 garbage objects of roughly 20–25 GC blocks (300–400 B) per iteration, at up to 200 iterations/s. That is **tens of KB/s of garbage at idle** [I, must be measured]. Every one of those allocations counts toward `gc.threshold` (`py/gc.c:1011`, `gc_alloc_amount += n_blocks`; `gc_free` never decrements it). Under this project's `gc.threshold(32768)`, MQTT idle polling alone would plausibly trigger a collection every second or so, on top of the library's own explicit `gc.collect()` every second (B8).

## 5. Link-failure detection and recovery (Q4)

### 5.1 Keepalive

All [V], lines 698-705 and 851-862.
- `ping_interval = keepalive/4` (15 s at the default 60 s); 20 s if `keepalive == 0`. `config["ping_interval"]` can only make it shorter.
- `_keep_alive` sends `PINGREQ` once per ping interval **unconditionally**, even when other traffic is flowing.
- It declares the broker dead when `(now - last_rx) // ping_interval >= 4`, i.e. after a full keepalive period of silence. Since that is checked only once per interval, detection takes **60–75 s** with the defaults [I].
- `last_rx` is refreshed only by `_as_read` receiving bytes (line 260). A `PINGRESP` counts because `wait_msg` reads its length byte with `_as_read(1)` (lines 580-582).
- Issue #41 (closed) [R] discusses the race between this client-side timeout and the broker's 1.5× keepalive.

### 5.2 Failure modes

| Failure | Detected by | Latency |
|---|---|---|
| STA link down (CYW43 reports it) | `isconnected()` → `_sta_if.isconnected()` False (line 883), polled about every 5 ms | about 5 ms [V/I] |
| Broker process restart (RST/FIN) | `read(1)` returns `b""`: `OSError("Empty response")` (line 578). Or a mid-packet `msg_size == 0`: "Connection closed by host" (line 256). Or a socket error. | about 5 ms [V/I] |
| Half-open TCP; WiFi "connected" but carrying no traffic (the CYW43 false positive this project already knows); broker host powered off | Writes still "succeed" into lwIP's send buffer. Only the missing `PINGRESP` (5.1), or a QoS1 PUBACK timing out `max_repubs + 1` times, raises `OSError(-1)` (line 489). | idle: 60–75 s. With a QoS1 publish in flight: about 5 × 10 s = 50 s [I] |
| DNS failure | only on the first `connect()`, as an `OSError` (negative lwIP code) to the caller | — |
| Broker IP changes later | never noticed: `_addr` is cached for the client's lifetime (line 790) | [V] needs `disconnect()` + `connect()` or a reboot |

The recovery path is the DOWN branch of the state machine in 2.4. Each pass is: WiFi disconnect, 1 s, rejoin (≤60 s), 5 s stability, broker connect. There is no retry limit, no backoff and no jitter [V].

On the eth variant a pass is just 1 s plus a connect. With the WLAN down, `tcp_connect` fails at once (no route, [I]), so the client retries at about 1 Hz and allocates a new socket each time.

### 5.3 Callbacks and events, resubscription, clean session, publishing while down

- **Callbacks or events.** Callback mode (`queue_len == 0`) uses `wifi_coro(state)` and `connect_coro(client)`. Event mode (`queue_len > 0`) sets `client.up`/`client.down` (`asyncio.Event`s the user must `clear()`). The two are mutually exclusive (lines 174-182).
- **Subscriptions are not remembered.** [V] No subscription list exists anywhere. The README (3.2.3): "Subscriptions should be created in the connect coroutine to ensure they are re-established after an outage." The application re-subscribes on `up` or in `connect_coro`. With `clean=False` the broker keeps them, but see the next point.
- **`clean=False` cannot reconnect, on v3.1.1 and v5 alike, since v0.8.0 (August 2024).** [V] by code plus mosquitto source; not reproduced by running anything.

  ```python
  # mqtt_as/__init__.py:367-372
          connack_resp = await self._as_read(2)
          # Connect ack flags
          if connack_resp[0] != 0:
              raise OSError(-1, "CONNACK flags not 0")
  ```

  - Bit 0 of that byte is **Session Present**. mosquitto sets it whenever a client reconnects with clean-start 0 and a stored session exists (`handle_connect.c:115-118`: `if(context->clean_start == false && found_context->session_expiry_interval != MQTT_SESSION_EXPIRY_IMMEDIATE){ … connect_ack |= 0x01;`). For v3.1.1 with clean 0, the session never expires (`set_session_expiry_interval`, lines 596-605).
  - So with `clean=False`, **every reconnect after the first outage fails** with "CONNACK flags not 0", and `_keep_connected` loops forever, cycling WiFi on the wireless variant.
  - `lptest_min.py` (`clean=False`, `clean_init=False`) would fail on its very first connect once a session exists.
  - The check came in with the MQTTv5 contribution (`e925c04`, 2024-04-12). The earlier code checked only the return code (`resp[3]`).
  - The default `clean=True` is unaffected.
- **Publishing while down.** All [V] lines 952-960.
  - `publish()` (also `subscribe()`/`unsubscribe()`) loops `await self._connection()` (1 s polls), then the protocol call; on `OSError` it calls `_reconnect()` and loops.
  - It **blocks until reconnected, with no timeout, no drop and no exception.** README 3.2.2 (clarified 2026-10-04): "it will pause until the WiFi/broker are accessible when the message will be published."
  - If `_keep_connected` has died (section 8) or `disconnect()` was called, that wait is **forever**.
  - QoS0 publishes issued during the 5.2 detection window go into a dead socket and are **lost silently**. Issue #185 [R] (eth, 2026-10-02, closed without visible comment): a QoS0 publish issued just after "down" is held and sent late, while ones issued before detection are lost.
  - There is no offline queue. Each publishing coroutine holds its own message while it waits.

## 6. QoS (Q5)

All [V] unless tagged.
- **Supported levels.** `qos_check` (lines 127-129) allows QoS 0 and 1 for publish, subscribe and the will. QoS2 is not supported. An incoming QoS2 PUBLISH is **handed to the callback first** (line 684) and only then raises `OSError("QoS 2 not supported")` (lines 690-691), which forces a reconnect. A broker never sends QoS2 when every subscription is at QoS ≤ 1, though.
- **PIDs.** `pid_gen` (lines 120-124) produces 1..65535 and wraps; one generator is shared by PUBLISH and SUBSCRIBE/UNSUBSCRIBE. Pending PIDs live in the set `rcv_pids`. `kill_pid` (lines 554-558) removes a PID on its ack and **raises `OSError("Invalid pid in … packet")` for an unknown PID**, which forces a reconnect.
- **QoS1 publish flow** (lines 474-494):
  1. Add the PID.
  2. Send under the lock.
  3. Release the lock and wait for the PUBACK (`_await_pid`, 100 ms polls, `response_time`).
  4. On timeout, **re-send with DUP=1 and the same PID**, up to `max_repubs` (4) times.
  5. If still unacknowledged, or the link is down: `OSError(-1)`. The wrapper then reconnects and **publishes again as a new message with a new PID**. README 4.2: "The new PID proved necessary for Mosquitto to recognise the message."
- **Mid-flight link drop.** `publish()` blocks through the outage, then re-sends with a new PID. The broker may receive the message twice; QoS1 semantics allow that. The README calls the result "effectively guarantee[d]" reception "with the proviso that the publishing coroutine will block until reception has been acknowledged."
- **Self-inflicted reconnect on a slow link** [I from lines 485-494 and 554-558]. If the PUBACK takes longer than `response_time`, the DUP re-send also gets a PUBACK (the broker must ack every QoS1 PUBLISH). The first PUBACK removes the PID. The second hits `kill_pid` with an unknown PID, so `OSError`, a reconnect and (on the wireless variant) a WiFi cycle follow.
- **Rejection reason codes.** A SUBACK return code ≥ 0x80 (lines 625-629), or a v5 PUBACK reason ≥ 0x80 (lines 592-596), raises in `_handle_msg` and forces a reconnect. A broker that rejects a subscription or publish (ACL, quota) therefore produces an **endless reconnect loop**, because `connect_coro`/`up` re-subscribes and the publisher re-publishes [I].
- **PID race during reconnect** [I, low probability]. `publish()` adds its PID **before** taking the lock (lines 476-478). `connect()` clears `rcv_pids` (line 814). A publisher still queued on the lock across a whole reconnect would see `pid not in rcv_pids` and return "success" without a PUBACK.
- **Incoming QoS1.** The PUBACK is sent **after** the callback or `queue.put` (lines 684-689), while still holding the lock.
- **Duplicates.** There is no de-duplication; the DUP flag is ignored. README §0: "Duplicates can readily be handled at the application level."
- **Ordering.** Concurrent publishers go out in lock order. A QoS1 message re-published after a reconnect overtakes nothing, but messages published after it may arrive first [I]. Issue #95 [R]: "messages arrive in a different order than they are sent" (ESP32, closed).
- **Cancelling a publish** (README 4.4.1): "Simple cancellation of a publication task is not recommended because it can disrupt the MQTT protocol." [I] from code:
  - Cancelling while parked in `_connection()` is harmless.
  - Cancelling during `_as_write` (between `sleep_ms(0)` yields) releases the lock with a **partial packet on the wire**. The next packet's bytes are then parsed as the remainder, the broker sees a malformed stream and disconnects.
  - `asyncio.wait_for(client.publish(...))` carries exactly this risk. `mqtt_as_timeout.py` avoids it by taking `self.lock` before cancelling.

## 7. Incoming message API (Q6)

All [V].
- **Callback mode.** `subs_cb(topic, msg, retained[, properties])`, called synchronously **inside the lock**. README 4.4: "The subscription callback will block publications and the reception of further subscribed messages and should therefore be designed for a fast return." Only one callback exists for all topics.
- **Event mode** (`queue_len = N > 0`). `async for topic, msg, retained[, properties] in client.queue`, with the `MsgQueue` at lines 60-86.

  ```python
  # mqtt_as/__init__.py:69-75
      def put(self, *v):
          self._q[self._wi] = v
          self._evt.set()
          self._wi = (self._wi + 1) % self._size
          if self._wi == self._ri:  # Would indicate empty
              self._ri = (self._ri + 1) % self._size  # Discard a message
              self.discards += 1
  ```

  - **Overflow drops the oldest message silently.** The PUBACK has already gone out, so QoS1 is not end to end. README 3.5: "This policy prioritises resilience over the `qos==1` guarantee."
  - **Usable capacity is N−1.** One slot distinguishes full from empty, and the list is allocated with `max(size, 4)` slots, of which only `size` are used.
  - **`queue_len = 1`, the README's "minimal queue" and the default in the demos, is a one-slot mailbox.** Every `put` makes `_wi == _ri`, so **every message increments `discards`**, and a consumer that awaits anything between reads loses messages [I].
- **Types.**
  - `topic` is always a fresh `bytes` copy (line 656).
  - `msg` is a `bytes` copy in event mode, or when `MSG_BYTES` is True (the default). Otherwise it is a `memoryview` into the shared read buffer, valid only during the synchronous callback (README 4.4.3; lines 674-679).
  - `retained` is `bool`.
  - v5 `properties` is a dict keyed by property id, or None.
- **Size limits.**
  - There is no maximum-size guard. `_recv_len` (lines 292-295) decodes any variable-byte integer recursively, with no 4-byte cap, so a corrupt stream can make it recurse deep enough to raise `RuntimeError` [I].
  - `_as_read` then grows `self._ibuf` to `n + 50` (lines 238-242) **and never shrinks it again** [V].
  - README 1.9: "it is wise to design on the basis of a maximum of around 1KiB."
  - Issues #83 and #160 [R]: `MemoryError` on large messages (33 KB, 50 KB). Issue #151 [R]: that `MemoryError` "causes this whole task to crash" (see section 8).
- **Ordering** is TCP receive order, one packet per `wait_msg()` call.
- **Outgoing topic and message types.** README 3.2: "Messages and topics may be strings provided that all characters have ordinal values <= 127 … Otherwise the string `encode` method should be used." The code counts `len(str)` in characters (lines 288 and 499). A non-ASCII `str` therefore produces a **malformed packet**: issue #178 [R] (FlashMQ "DISCONNECT 0x81 Malformed Packet"). PR #179 offered a fix; the maintainer closed it as "by design: pass bytes."

## 8. Error handling (Q8)

All [V] unless tagged.

**What reaches application code:**
- `connect()`, first call:
  - `OSError("Wi-Fi connect timed out")` and `OSError("Connection Unstable")`;
  - lwIP `OSError`s from `getaddrinfo` and `connect`;
  - TLS errors from mbedtls (`OSError` with a negative code; issue #125: "BIGNUM - Memory allocation failed");
  - `OSError(-1, "CONNACK …")`;
  - `TypeError` (rp2 with `ssid=None`, section 3.2);
  - `MemoryError`.

  The socket is closed before the re-raise (lines 810-813, the issue #25 fix). The app must retry; there is no built-in first-connect retry. Issue #183 (open): "the app cannot start at all" if the broker is down at boot. The maintainer advised a retry or `machine.reset()` in a forum thread [R, unverified snippet].
- `publish()`/`subscribe()`/`unsubscribe()`:
  - `ValueError` (QoS);
  - `TypeError` (unsupported msg/topic type, issue #135). The header can already be written by then, which corrupts the stream [I];
  - `MemoryError`;
  - v5 property encoding errors.

  **`OSError` never escapes; it means retry forever.**

**Swallowed or turned into a reconnect:** any `OSError` in `_handle_msg`, `_keep_alive`, `publish`, `subscribe` or `unsubscribe`, and any `OSError` raised by `wifi_connect`/`connect` inside `_keep_connected`.

**Not handled, and the consequences:**
- **Inside `_keep_connected`, any non-`OSError`** kills the only reconnect task permanently. Examples: `TypeError` from `connect(None, None)`; `MemoryError` from `ssl.wrap_socket` or buffer growth; a v5 `ValueError`. After that, `isconnected()` stays False, `down` has fired, and every `publish()` waits forever [I]. There is no supervisor and no exception escalation; MicroPython's default handler just prints "Task exception wasn't retrieved" (`extmod/asyncio/core.py:294-297`).
- **Inside `_handle_msg`, any non-`OSError`** ends the reader without calling `_reconnect()`. Examples: an exception raised by the user callback; `MemoryError` (#151); `ValueError("Unknown property identifier")` from v5 `decode_properties` (mqtt_v5_properties.py:236-237); `RuntimeError` from recursion; `IndexError`.
  - Nothing reads the socket any more, so `last_rx` stops, and `_keep_alive` declares the broker dead 60–75 s later and reconnects [I].
  - If the trigger was a retained or QoS1-redelivered message, it comes back after the re-subscribe, so the cycle can repeat indefinitely [I].
- Issue #172 (closed by `c6b8127`) was an `AssertionError` in this path; the fix turned the asserts into `OSError`s.

**Unknown packet types.** `wait_msg` returns without consuming the remaining length or body for any type it does not parse (line 649). The stream then desynchronises. That covers v5 `AUTH`, a v3 `DISCONNECT`, and `PUBREL`, none of which a compliant v3.1.1 server sends to a QoS ≤ 1 client [I].

**Logging.** Only `dprint` (print), gated by `DEBUG`. There are no counters apart from `REPUB_COUNT` and `queue.discards`. `OSError` codes are not logged unless `DEBUG` is on (line 926).

**`OSError` codes the code checks for:** `EINPROGRESS`, `ETIMEDOUT`, rp2 `-110`, ESP32 `118`/`119`. Anything else counts as fatal for the connection.

## 9. Memory (Q7)

**Allocations on the hot paths.** Sources [V]; whether each allocation is *needed* is [I].

| Path | Allocations |
|---|---|
| Idle poll (×~200/s) | `__aenter__`, `acquire`, `wait_msg` and `__aexit__` generator objects, plus a 2-byte vstr (allocated, then freed). See 4.2. |
| Receive PUBLISH | `read(1)` → 1-byte `bytes`. `_recv_len` recursion → 2 coroutines per length byte. Every `_as_read` → a coroutine, `buffer[size:]` (new memoryview per `readinto` attempt) and `buffer[:n]` (memoryview). `bytes(topic)`, `bytes(msg)`, the `args` list, the event-mode tuple. The PUBACK `bytearray(4)` plus its `_as_write` coroutine and memoryview. v5: `bytes(props)` copy and a dict. |
| Send PUBLISH | `bytearray(4)` header. About 5 `_as_write` coroutines and memoryviews. `struct.pack("!H")` `bytes` in `_send_str`. A slice per partial write. Lock generators. QoS1: the `_await_pid` coroutine. v5: `encode_properties` builds a dict, intermediate `bytes`/`bytearray` (and `list(value.items())` for user properties). |
| PINGREQ | lock generators, an `_as_write` coroutine, a memoryview |
| Each (re)connect | new socket; `bytearray` CONNECT pieces; with TLS, **a new `SSLContext` and mbedtls session: 16 KiB IN + 4 KiB OUT record buffers** (`extmod/mbedtls/mbedtls_config_common.h:63-65`) taken from the **GC heap** via `MBEDTLS_PLATFORM_STD_CALLOC m_tracked_calloc` (line 123; `py/malloc.c:277-278` allocates it with `m_malloc_maybe`) [V]. That is a ≥ 20 KiB allocation burst on every reconnect: a fragmentation risk for a long-running device [I]. Issue #125 [R]: BIGNUM allocation failure in `wrap_socket`. |

**Pre-allocation.** Only `_ibuf` (`IBUFSIZE = 50`, settable before construction: README 4.4.3, "IBUFSIZE") and its memoryview are pre-allocated. `_ibuf` grows to the largest packet and stays that size permanently.

**`gc.collect()` inside the library, in both variants:** [V]
- `mqtt_as/__init__.py:15, 19, 23, 28` at import;
- **`:907`, once per second while connected, forever**;
- `:876`, every 20 s with `DEBUG`;
- eth: `:855` and `:833`.

This **contradicts the project's rule against `gc.collect()` in business logic**, and its GC-stage (e) test ("no `gc.collect()` calls … anywhere in the business logic"). Under the project's no-edit vendoring policy, neutralising it would need a subclass that overrides `_keep_connected` (copying its roughly 30 lines) or rebinding the module's `gc` name [I]. Both would be departures that need a decision.

**Fragmentation over months** [I]:
- steady garbage from polling;
- a permanent `_ibuf` high-water mark;
- 20 KiB TLS bursts on every reconnect;
- one new socket object per reconnect attempt (lwIP sockets carry a finaliser, `modlwip.c:946`, so orphans are eventually closed by the GC).

One orphaned socket path exists [V]: the `clean_init && !clean` first connect (lines 800-809) creates a second socket without closing the first. It happens once, at boot.

## 10. MQTT v5 (Q9)

All [V] unless tagged. Contributed by Bob Veringa (PR #139, August 2024; fixes in 0.8.1 and 0.8.3).
- **Supported:**
  - Properties on CONNECT (`mqttv5_con_props`), PUBLISH (outgoing and incoming) and SUBSCRIBE/UNSUBSCRIBE (outgoing).
  - Reason codes on CONNACK, PUBACK, SUBACK, UNSUBACK and DISCONNECT. Any code ≥ 0x80 raises `OSError` and forces a reconnect.
  - Session Expiry (0x11) and Message Expiry (0x02).
  - `topic_alias_maximum` is read from CONNACK (line 390) and exposed but not enforced.
  - Request/response properties (0x08, 0x09).
- **Not supported** (README 3.6.3):
  - AUTH / enhanced authentication;
  - will properties (always sends 0);
  - more than one user property: only the first is sent and the last received is kept;
  - subscription options (NL, RAP, retain handling);
  - most CONNACK properties are not exposed;
  - properties on ACK packets reach the user only via `DEBUG` prints;
  - incoming topic aliases are not stored;
  - Receive Maximum is not enforced on outgoing QoS1.
- **Defects** [V code]:
  - the Session Present bug (5.3) applies to v5 `clean=False` as well;
  - an unknown property id raises `ValueError` and kills `_handle_msg` (section 8);
  - the relative import `from .mqtt_v5_properties import …` only works inside a package directory [V]. A flat copy as `mqtt_as.py` would fail with `ImportError` once v5 is enabled [I], which matters for this project's flat `src/`+`ext/` freeze layout.
- **Maturity** [I]: about 2 years old with modest use. Testing is manual (tests/v5, cbtest).

## 11. TLS (Q10)

- **How it works.** `ssl.wrap_socket(self._sock, **self._ssl_params)` (lines 308-314) wraps the non-blocking socket *before* its TCP connect has finished. Valid keys (README §9): `key`, `cert`, `server_side`, `server_hostname`, `do_handshake`, `cert_reqs`, `cadata`.
- **Blocking handshake by default.** See B4. Issue #171 is open, with no maintainer reply.
- **No certificate verification by default.** micropython-lib `ssl.wrap_socket(..., cert_reqs=CERT_NONE)` (ssl.py:44-59) [V]. Verifying the server requires `cert_reqs=ssl.CERT_REQUIRED` plus `cadata`, and a correct clock (README §9) before connect.
- **Memory.** ≥ 20 KiB from the GC heap per connection, re-allocated on every reconnect (section 9).
- **rp2-specific notes:**
  - -110 is treated as busy (section 3.2).
  - Issue #161 (open) [R]: Pico W plus HiveMQ TLS fails with "Connection Unstable". That message is the WiFi stability check, not TLS.
  - Issue #153 [R]: `MBEDTLS_ERR_SSL_BAD_INPUT_DATA` on disconnect.
  - Issue #125 [R]: BIGNUM allocation failure in `wrap_socket`.

## 12. Concurrency (Q11)

All [V] unless tagged.
- A single `asyncio.Lock` (`self.lock`, line 206) protects **each packet's write** (`_publish`, `_usub`, `_ping`, `disconnect`) and **each packet's read, callback and PUBACK** (`_handle_msg`).
- The lock is **not** held while waiting for a PUBACK or SUBACK. Several coroutines can publish QoS1 concurrently, and `subscribe()` can run while a `publish()` waits for its PUBACK. README 4.4: "The module allows concurrent publications and registration of subscriptions."
- There is no limit on the number of in-flight QoS1 messages; each waiting coroutine holds its own message and generator frames. README 4.4 warns about resource use on small devices.
- Lock fairness: MicroPython's Lock is FIFO. `_handle_msg` sleeps 5 ms outside the lock so writers can get in.
- A slow incoming packet holds the lock for up to `response_time` (10 s) per `_as_read` stall, which delays every writer and ping [I].

## 13. Known issues and PRs (Q12)

The tracker holds 143 issues (18 open) and 42 PRs (6 open). Issue comment threads could not be fetched (see section 0). Status is as shown on 2026-10-07. Items touching reconnects, hangs, memory, Pico W/rp2/CYW43, blocking publishes, lost messages or WiFi ownership:

| # | State | Title / gist | Relevance |
|---|---|---|---|
| [#171](https://github.com/peterhinch/micropython-mqtt/issues/171) | **open** (2025-04-30, no reply) | `ssl.wrap_socket()` hangs on reconnecting; triggers the WDT. Workaround `do_handshake=False`. | B4; loop blocking |
| [#183](https://github.com/peterhinch/micropython-mqtt/issues/183) | **open** (2026-09-20) | Starting while the broker is down: the first `connect()` raises and the app cannot start | 2.4 / 8 |
| [#185](https://github.com/peterhinch/micropython-mqtt/issues/185) | closed (2026-10, no visible comment) | eth: QoS0 publish at the start of an outage is held and sent late; earlier ones are lost | 5.3 |
| [#178](https://github.com/peterhinch/micropython-mqtt/issues/178) / [PR #179](https://github.com/peterhinch/micropython-mqtt/pull/179) | closed | Non-ASCII `str` gives a wrong Remaining Length and DISCONNECT 0x81. Maintainer: by design, pass bytes. | 7 |
| [#177](https://github.com/peterhinch/micropython-mqtt/issues/177) | closed | `isconnected()` always False (user confusion around connect timing) | — |
| [#172](https://github.com/peterhinch/micropython-mqtt/issues/172) | closed (`c6b8127`) | Broker reboot gave an `AssertionError` in `_handle_msg`; asserts became exceptions | 8 |
| [#166](https://github.com/peterhinch/micropython-mqtt/issues/166) | closed (`63f734e`) | `sleep_ms(0)` in `_handle_msg` starved STDIN/Ctrl-C, hence the 5 ms poll | 4.2 |
| [#165](https://github.com/peterhinch/micropython-mqtt/issues/165) | open | Request to make PINGRESP handling overridable (latency measurement) | extensibility |
| [#163](https://github.com/peterhinch/micropython-mqtt/issues/163) | open (code fixed in 0.8.3, `bc7d4c2`) | `unsubscribe` `pack_into` bug | — |
| [#161](https://github.com/peterhinch/micropython-mqtt/issues/161) | **open** | Pico W: "OSError: Connection Unstable" on HiveMQ TLS | rp2 WiFi stability check |
| [#160](https://github.com/peterhinch/micropython-mqtt/issues/160) | closed | 50 KB messages: the second allocation fails (fragmentation); proposes chunked reads | 7, 9 |
| [#158](https://github.com/peterhinch/micropython-mqtt/issues/158) | closed | "The Rewrite" (FUTURE_DEVELOPMENT.md): the author's own case that mqtt_as is socket- and WiFi-bound and needs a rewrite | design |
| [#153](https://github.com/peterhinch/micropython-mqtt/issues/153) | closed | `MBEDTLS_ERR_SSL_BAD_INPUT_DATA` on disconnect | TLS |
| [#151](https://github.com/peterhinch/micropython-mqtt/issues/151) | closed (code unchanged: still catches only `OSError`, line 845) | `MemoryError` in `_as_read` crashes `_handle_msg`; recovery only via keepalive | 8 |
| [#147](https://github.com/peterhinch/micropython-mqtt/issues/147) | closed | `connect_coro` not cancelled on outage, giving duplicate handlers and double subscriptions | 2.2 |
| [#144](https://github.com/peterhinch/micropython-mqtt/issues/144) | closed | ESP32-S2 1.23: "stuck and never recovered" after an AP power-cycle or broker restart | reconnect |
| [#140](https://github.com/peterhinch/micropython-mqtt/issues/140) | closed | No reconnect after the broker restarts (ESP, SSL) | reconnect |
| [#135](https://github.com/peterhinch/micropython-mqtt/issues/135) | **open** | `TypeError: object with buffer protocol required` in `_as_write` | 8 |
| [#132](https://github.com/peterhinch/micropython-mqtt/issues/132) / [PR #154](https://github.com/peterhinch/micropython-mqtt/pull/154) | closed | ESP32 never reconnects after a WiFi outage; fixed with a 1 s sleep (ESP32 only) | reconnect |
| [#125](https://github.com/peterhinch/micropython-mqtt/issues/125) | closed | TLS: BIGNUM memory allocation failed after MP 1.21 | TLS memory |
| [#122](https://github.com/peterhinch/micropython-mqtt/issues/122) | **open**, unanswered | "wifi is treated as internal details only" | **3.3** |
| [#119](https://github.com/peterhinch/micropython-mqtt/issues/119) | closed | Unix port compatibility (no `unique_id`, no `network`); partly answered by `mqtt_as_eth` | 14 |
| [#118](https://github.com/peterhinch/micropython-mqtt/issues/118) | **open** | Pico W: sporadic resets (`reset_cause` = power-on) "only since using mqtt_as". No root cause. | rp2 stability |
| [#110](https://github.com/peterhinch/micropython-mqtt/issues/110) | closed | ESP32-S2 lockup under stress; `gc.collect()` prolonged the run | memory |
| [#109](https://github.com/peterhinch/micropython-mqtt/issues/109) | open | Slow first subscribe (power-management suspicion) | — |
| [#96](https://github.com/peterhinch/micropython-mqtt/issues/96) | closed | Use with an external WiFi manager: the constructor wants credentials | **3.3** |
| [#95](https://github.com/peterhinch/micropython-mqtt/issues/95) | closed | Messages arrive out of order (ESP32) | 6 |
| [#88](https://github.com/peterhinch/micropython-mqtt/issues/88) | closed | Pico W 5–8 s lag; disabling PM fixed it, so `pm=0xA11140` became default | 3.2 |
| [#83](https://github.com/peterhinch/micropython-mqtt/issues/83) | closed | Pico: `MemoryError` allocating 33 KB in `_as_read` | 7 |
| [#82](https://github.com/peterhinch/micropython-mqtt/issues/82) | closed | Pico W `wifi_connect` broke out on status 2 (led to the `1 <= status <= 2` check) | 3.2 |
| [#74](https://github.com/peterhinch/micropython-mqtt/issues/74) | closed (fixed: lines 810-813) | `_in_connect` stuck True after a failed `connect()` | — |
| [#61](https://github.com/peterhinch/micropython-mqtt/issues/61), [#59](https://github.com/peterhinch/micropython-mqtt/issues/59) | closed | Starting with WiFi already connected leads to "Wifi Internal Error" (ESP32) | **3.3** |
| [#54](https://github.com/peterhinch/micropython-mqtt/issues/54) | closed | ESP32 1.14: PUBACKs late, repubs, then `MemoryError`/`task_queue_push_sorted` assertion | 6, 9 |
| [#46](https://github.com/peterhinch/micropython-mqtt/issues/46) | closed | Subscriptions lost after reconnect (answer per README: re-subscribe in `connect_coro`) | 5.3 |
| [#41](https://github.com/peterhinch/micropython-mqtt/issues/41) | closed | Keepalive race between the client timeout and the broker's 1.5× | 5.1 |
| [#40](https://github.com/peterhinch/micropython-mqtt/issues/40) | closed | `clean_init` vs `clean` | 5.3 |
| [#36](https://github.com/peterhinch/micropython-mqtt/issues/36) | closed | Request for a StreamReader/Writer-based client without WiFi logic | 4.2 |
| [#25](https://github.com/peterhinch/micropython-mqtt/issues/25) | closed (fixed) | Socket left open after a failed first connect | — |
| [#16](https://github.com/peterhinch/micropython-mqtt/issues/16) | closed | How to combine with a WDT | — |
| [PR #57](https://github.com/peterhinch/micropython-mqtt/pull/57) | open (stale since 2021) | `BaseInterface` abstraction; maintainer 2022: "I have no plans to work on this" | 3.3 |
| [PR #167](https://github.com/peterhinch/micropython-mqtt/pull/167) | open | Non-WiFi interfaces. Maintainer favours a stripped-down separate variant, now `mqtt_as_eth`. | 3.3 |
| [PR #180](https://github.com/peterhinch/micropython-mqtt/pull/180) | open | AI-generated no-hardware test harness. Maintainer: "leave this open in case it is useful to others"; his testing relies on "physical WiFi". | 14 |
| [PR #184](https://github.com/peterhinch/micropython-mqtt/pull/184) | open | Unix support. The maintainer answered with `mqtt_as_eth` (2026-09-27). | 14 |

Outside the repo, a third-party mirror (unverified, search snippet only, [R]) described a Pico W running ≥ 1.23 where publishes stalled at payloads above about 125 bytes. The reporter said "peterhinch's micropython-mqtt" behaved the same. Maintainers could not reproduce it. Issue #170 (closed, Pico W, longer payloads stall) may be the same symptom. Neither has been verified.

## 14. Testability (Q13)

- **The repo's own tests** [V] are manual and hardware-in-the-loop:
  - `tests/v3|v5/test.py` drives a second device running `target.py` through a live broker.
  - They print coloured PASS/FAIL, need `mqtt_local.py`, LEDs and `primitives.RingbufQueue`, and have no automated runner and no CI.
  - The demos are interactive.
  - PR #180's harness is unmerged.
- **Imports that break on the Unix port** [V]:
  - `mqtt_as/__init__.py` imports `machine.unique_id` (the Unix port has `machine`, `mpconfigvariant_common.h:117`, but no `unique_id`) and `network` (the Unix port has no `network` module).
  - `sys.implementation._machine` exists.
  - The project's fakes cover part of this: `digital_twin/network.py` has `WLAN.active/connect/disconnect/isconnected/status/config`. Neither `tests/machine.py` nor `digital_twin/machine.py` defines `unique_id`.
  - `mqtt_as_eth` imports neither and is documented as running on the Unix build. The maintainer tested it on the Unix build and a W5500-EVB-Pico (PR #184 comment, 2026-09-27).
- **Feasible test tiers** [I]:
  1. **Against a real mosquitto on the Unix port.** apt-installable, runs on a loopback port. Covers protocol conformance (CONNACK, SUBACK, PUBACK, retained, clean/unclean; this would reproduce the Session Present bug immediately), broker restart (kill/restart mosquitto), and keepalive.
  2. **Against a scripted fake broker** (a small asyncio TCP server in MicroPython or CPython) for fault injection:
     - drop, delay or duplicate PUBACK (the "Invalid pid" reconnect);
     - SUBACK 0x80;
     - Session Present = 1;
     - malformed or oversized lengths;
     - mid-packet stalls;
     - half-open (stop reading, keep the socket);
     - RST.
  3. **Heap and allocation measurements** on the Unix port, using `micropython.mem_info()` / `gc.mem_alloc()` deltas per idle second, to confirm or refute 4.2's churn estimate. The project already runs such GC-stage checks.
- **What the Unix port cannot show** [I]:
  - rp2 lwIP specifics: `ERR_MEM` blocking, -110, CYW43 link-state transitions, TLS handshake CPU time on the RP2040.
  - The wireless variant's WiFi branches (`RP2` is False on Unix) run only against a WLAN fake.
  - The Unix `modsocket` (POSIX) is not modlwip.

## 15. License and vendoring (Q14)

- **LICENSE (MIT)** [V]: "MIT License / Copyright (c) 2017 Peter Hinch / Permission is hereby granted, free of charge, …" (standard MIT text, 21 lines).
- **File headers:**
  - `mqtt_as/__init__.py:1-8`: "(C) Copyright Peter Hinch 2017-2025. Released under the MIT licence." It credits Kevin Köck and Bob Veringa (v5).
  - `mqtt_v5_properties.py`: "(C) Copyright Bob Veringa 2024-2025. Released under the MIT licence."
  - `mqtt_as_eth/__init__.py`: "(C) Copyright Peter Hinch 2017-2026."
  - `mqtt_as_timeout.py`: "(C) Copyright 2019 Kevin Köck."
- **Self-contained?**
  - Yes for v3.1.1: one file, `mqtt_as/__init__.py`, using only built-ins: `gc`, `socket`, `struct`, `time`, `binascii`, `asyncio`, `errno`, `micropython`, `machine`, `network`, `sys`, plus `ssl` from the firmware-frozen micropython-lib when `ssl` is set.
  - v5 adds `mqtt_v5_properties.py` via a **relative** import, which needs the package layout (section 10).
  - The eth variant's v5 file is only mapped from `mqtt_as/` by its package.json; it is not in `mqtt_as_eth/`.
- There are no upstream tags, so the project's "unmodified upstream tag or commit" rule means pinning a commit such as `dd03ab3`.

## 16. Gaps and risks for a 24/7, months-without-reboot, never-block, never-leak device (Q15)

Ordered by impact on this project. All [I] unless a code reference marks the fact itself as [V].

1. **WiFi ownership conflict (wireless variant).** The library owns `network.WLAN`. Every outage, including a pure broker outage, runs `_sta_if.disconnect()` and a rejoin with a 5 s wait, with no backoff [V, 3.1]. `ssid=None` breaks it with a `TypeError` [V, 3.2], and `close()` deactivates WLAN [V]. That is incompatible with `asy_wifi_service.py` and its hotspot phase without a shim or subclass, or a switch to `mqtt_as_eth` (v0.1.0, 10 days old, TLS untested off-WiFi).
2. **`gc.collect()` every second, hard-coded, in both variants** [V, 9]. It violates the project's GC discipline and cannot be removed without editing vendored code or overriding `_keep_connected`.
3. **Polling architecture.** A 200 Hz idle poll with several heap allocations per pass, CPU spinning with `sleep_ms(0)` during mid-packet and connect waits, and 100 ms and 1 s polls elsewhere [V code, I cost]. Continuous garbage, GC pressure under `gc.threshold(32768)`, wake-ups and CPU use for the life of the device. No `select.poll`/IO-queue integration.
4. **Loop-blocking calls.**
   - the TLS handshake by default, unbounded (#171 open) [V];
   - `getaddrinfo` with a hostname (first connect) [V];
   - lwIP `ERR_MEM` up to 10 s inside `write` [V];
   - `gc.collect()` every second [V];
   - the user callback runs under the lock [V].
5. **`clean=False` is broken.** The "CONNACK flags not 0" check rejects Session Present, so persistent sessions can never reconnect [V code + mosquitto source; not run].
6. **Silent permanent failure modes.**
   - A non-`OSError` exception in `_keep_connected` ends reconnection forever. The client then sits "down" with every `publish()` blocked forever, and there is no watchdog hook or failure callback [V code].
   - A non-`OSError` in `_handle_msg` (callback exception, `MemoryError`, v5 `ValueError`) silently stops reception for 60–75 s per occurrence, possibly repeating [V code, I recurrence].
7. **Self-inflicted reconnect storms.**
   - A duplicate or late PUBACK raises "Invalid pid" and forces a reconnect [V code].
   - A SUBACK or v5 PUBACK failure code (ACL or quota) forces a reconnect, then the app re-subscribes or re-publishes and the loop repeats [V code].
   - On the wireless variant each of these also cycles WiFi.
8. **Unbounded waits and no back-pressure.**
   - `publish()`/`subscribe()` block indefinitely while down. There is no timeout parameter, and cancellation is unsafe mid-write [V].
   - No offline queue or bound on concurrent in-flight QoS1 [V].
   - QoS0 is lost silently during the 5–75 s detection window [I].
9. **Message-queue semantics.**
   - The oldest message is dropped after its PUBACK has gone out, so QoS1 is not end to end [V].
   - `queue_len=1` counts every message as a discard [V].
   - Capacity is N−1 [V].
10. **Memory over months.**
    - The receive buffer grows to the largest packet ever and never shrinks [V].
    - There is no maximum-packet-size guard, and the VBI decode recurses without bound [V].
    - Every TLS reconnect bursts ≥ 20 KiB from the GC heap [V config, I fragmentation].
    - No certificate verification by default [V].
11. **Detection latency.**
    - Half-open links and the CYW43 "connected but dead" state are found only after about 60–75 s idle, or about 50 s with QoS1 in flight [I].
    - Pings are sent even when traffic is flowing [V].
    - The broker address is cached forever [V].
12. **Lifecycle hygiene.**
    - `disconnect()` fires a spurious "down", and a later `publish()` hangs [V/I].
    - Internal and user tasks (`_handle_msg`, `_keep_connected`, `connect_coro`, `wifi_coro`) are untracked and uncancellable [V].
    - `isconnected()` has side effects [V].
    - The tasks bypass the project's `asy_system_service.py` supervisor entirely [I].
13. **API footguns.**
    - A `str` topic or message with non-ASCII characters produces malformed packets (maintainer: by design) [V].
    - `ifconfig` is read from the module-global `config` [V].
    - The config is a mutable module-global dict [V].
14. **Project health and vendoring.**
    - No tags and no CI [V].
    - Tests are manual two-device hardware scripts [V].
    - The eth variant has an invalid `package.json` and a dead `_lan_connect` [V].
    - Active churn (CPython support landed today) [V].
    - The maintainer states the design is "strictly socket-based" and WiFi-centric and that "a rewrite is called for" (FUTURE_DEVELOPMENT.md) [V].

### What it does well

All [V].
- The socket I/O really is non-blocking (B3, B5 and B6 in the normal case), and the handling of the platform-specific "busy" errnos is well thought out.
- QoS1 retransmission with DUP, plus re-publication after a reconnect, gives "effectively guaranteed" QoS1 delivery for blocking publishers.
- Keepalive pings feed the broker's last will.
- `broker_up()` gives an on-demand liveness probe.
- Both callback and event/queue interfaces exist.
- Basic v5 support.
- `dprint` is an overridable logging hook.
- The pre-allocated read buffer and `MSG_BYTES=False` give a zero-copy path for synchronous callbacks.
- MIT licence; small (one file); widely used, with maintainer response within days on PRs.
