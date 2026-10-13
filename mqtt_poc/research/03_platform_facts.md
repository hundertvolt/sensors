> **Raw research report** (agent, 2026-10-07): written by a read-only research agent of the MQTT PoC research session, kept verbatim as the evidence base for `mqtt_poc/RESEARCH.md`. Tags such as [V]/[SRC] mean verified in source by that agent; [I]/[INFERENCE] are not verified; nothing here was run on hardware. Clone paths (`<research-session scratchpad>/ext/...`) refer to that session's temporary scratchpad, not to this repo. Line anchors into this repo are as of `1cff5a2`.

# 03 — MicroPython v1.29.0 platform facts for a long-lived MQTT TCP client on Pico W

Date: 2026-10-07. Everything below was read out of the pinned source tree, which was cloned read-only:
`git clone --depth 1 --branch v1.29.0` (HEAD `0fd6c57 all: Bump version to 1.29.0.`) into
`scratchpad/ext/micropython-v1.29.0/`, with only these submodules fetched:

| Submodule | Pinned commit | Version read from the tree |
|---|---|---|
| `lib/lwip` | `77dcd25` | lwIP **2.2.1** release (`src/include/lwip/init.h:53-61`) |
| `lib/cyw43-driver` | `055d642` | (the v1.1.0+ line, see §6.4) |
| `lib/mbedtls` | `0bebf8b` | mbedTLS **3.6.6** (`include/mbedtls/build_info.h:37`) |

Paths below are relative to that tree unless they start with `src/`, `toolchain/`, `buildgen/` or
`SPECIFICATION.md` (this repo). **Nothing was built or run.** The labels mean:
- **[source]**: read directly at the cited lines.
- **[inference]**: my own derivation from source, not measured on silicon.
- **[issue]**: taken from an upstream GitHub issue or PR. Each one is linked with its status.

The upstream documentation site (docs.micropython.org) is blocked by this session's egress proxy,
so the in-tree `docs/` at the tag was read instead.

---

## 0. What the project already established (built on, not re-researched)

- **F.1.** A soft-callback drop can happen. The watchdog cap is 8,388 ms, and the boot code arms
  it at 8,000 ms. The asyncio facts: a stream takes one waiter per direction (`core.py:82-83`), and
  `asyncio.TimeoutError` is not an `OSError`. Each `wait_for()` has a real per-piece cost. The
  CYW43 driver's warnings go to the console only.
- **F.2.** `socket.getaddrinfo()` is never called from `src/` on a name. `asy_dns_client.py`
  resolves over its own non-blocking UDP. The CYW43 `isconnected()` false positive is backstopped
  by a power cycle, which the owner accepted.
- **F.5.6.** `extmod/asyncio/` is byte-identical between v1.28.0 and v1.29.0. `SOCK_RAW` is on.
- **F.7.** Rows 1-3 cover the Unix sockaddr and tuple differences, and row 12 covers
  `select.poll` over non-fd objects.
- **F.9.** Two rows matter here: "No `setsockopt(TCP_NODELAY)`" and "`peer_gone` write suppression
  after a connection reset".
- **B.14.2.** The lwIP options are an ensemble. `PCB = N+3`, `SEG = 8N` and `MEM_SIZE = 2000·N`.
  One connection costs 2,324 B of GC heap. `modlwip`'s `ERR_MEM` retry loop runs up to 10 s.
- **H.7 / H.7.1.** `tcp_alloc()` reclaim order, the 10 s close abort, the `backlog` coupling, and
  writes going through a NULL pcb after `ECONNRESET`.
- **`src/asy_wifi_service.py`.**
  - `pm=0xA11140` is set after every `active(True)` (`:326`, `:689`).
  - A plain reconnect calls `disconnect()` only (`:373-388`, `:728-733`).
  - A mode switch and permanent deactivation call `active(False)` + `deinit()` (`:361-371`,
    `:667-682`).
  - `network_available_locked()` returns `phase != HOTSPOT and status == STAT_GOT_IP` (`:858-859`).
- **`src/asy_dns_client.py`.** `resolve_ipv4()` never raises. It tries the caller's servers, then
  8.8.8.8 and 1.1.1.1, each `timeout_ms` (default 500) × `tries` (default 1), through a transient
  `UDPSocket`.
- **`src/asy_udp_socket.py`.** Polls with `ipoll(0)` plus `sleep_ms(20)`, bounded by
  `asyncio.wait_for_ms()` (F.2's one timeout mechanism).

---

## 1. TCP sockets via `extmod/modlwip.c`

### 1.1 Execution model: lwIP runs in the background, not in Python

- **lwIP runs at PendSV level, driven by a 64 ms soft timer.** The timer is
  `LWIP_TICK_RATE_MS 64` (`ports/rp2/mpnetworkport.c:39`). Its callback calls `sys_check_timeouts()`
  and keeps itself periodic only while `tcp_active_pcbs != NULL` or some netif has link up
  (`:144-166`). [source]
- **Python-side lwIP calls take the "lock" by suspending PendSV.** `MICROPY_PY_LWIP_ENTER/EXIT` are
  `lwip_lock_acquire/release()` (`ports/rp2/mphalport.h:51-54`), which call
  `pendsv_suspend()/pendsv_resume()` (`ports/rp2/mpnetworkport.c:127-135`). [source]
- **Since bfc69dbe8 (#18805, v1.28.0), every blocking-wait helper restarts that timer.** The helper
  is `poll_sockets()` (`extmod/modlwip.c:367-370`), which calls `MICROPY_PY_LWIP_POLL_HOOK` →
  `lwip_poll_hook()` and then `mp_event_wait_ms(1)` (`ports/rp2/mpnetworkport.c:137-143`). [source]
  [issue: #18805, merged 2026-03-04]

**Consequence [inference].** TCP retransmissions, ACKs, FIN/TIME_WAIT aging and DNS retries all
happen without any Python involvement. Python only moves data between lwIP pbufs and its own
buffers.

### 1.2 Socket object and state machine

```c
// extmod/modlwip.c:352-359
#define STATE_NEW 0
#define STATE_LISTENING 1
#define STATE_CONNECTING 2
#define STATE_CONNECTED 3
#define STATE_ACTIVE_UDP 4
#define STATE_PEER_CLOSED 5 // Values higher than this must also be closed by peer
#define STATE_PEER_RST_HANDLED 6
// Negative value is lwIP error
```

- **`socket.socket()` allocates the lwIP PCB immediately.** `tcp_new()` is called at `:971` and is
  `tcp_alloc(TCP_PRIO_NORMAL)` (`lib/lwip/src/core/tcp.c:1953-1956`). If the pool is empty it
  raises `OSError(ENOMEM)` (`modlwip.c:995-997`).
  - A created-but-unconnected socket holds a PCB that `tcp_alloc()` cannot reclaim, because it is
    on no list. It is freed only by `close()` or by the GC finaliser
    (`mp_obj_malloc_with_finaliser`, `:946`). [source]
  - "Errno 12 on the 6th socket" is this limit. [issue:
    [discussion #13022](https://github.com/orgs/micropython/discussions/13022), answered]
- **The default timeout is -1 (blocking)** (`:949`). [source]
- **The lwIP error callback hands the error to Python and drops the pcb.** `_lwip_tcp_error()`
  stores the lwIP error in `state` (negative) and sets `pcb.tcp = NULL`. It keeps any queued
  receive data so it can still be read later (`:498-508`). [source]
- **Incoming data stays in lwIP pbufs until Python reads it.** `_lwip_tcp_recv()` appends each
  incoming pbuf to the socket's chain with `pbuf_cat()` and returns `ERR_OK` (`:602-627`). The
  pbufs (PBUF_POOL buffers, §4) stay there until Python reads them. The receive window reopens
  only when Python reads, via `tcp_recved(pcb, len)` at `:909`. [source]

### 1.3 `connect()`: blocking, non-blocking, failure modes and timings

```c
// extmod/modlwip.c:1219-1246 (abridged)
tcp_recv(socket->pcb.tcp, _lwip_tcp_recv);
socket->state = STATE_CONNECTING;
err = tcp_connect(socket->pcb.tcp, &dest, port, _lwip_tcp_connected);
if (err != ERR_OK) { ... socket->state = STATE_NEW; mp_raise_OSError(error_lookup_table[-err]); }
...
for (;;) {
    poll_sockets();
    if (socket->state != STATE_CONNECTING) break;
    if (socket_is_timedout(socket, ticks_start)) {
        if (socket->timeout == 0) mp_raise_OSError(MP_EINPROGRESS);
        else mp_raise_OSError(MP_ETIMEDOUT);
    }
}
```

- **Non-blocking (`setblocking(False)`, timeout 0).** `tcp_connect()` emits the SYN, then one
  `poll_sockets()` runs (≤ 1 ms WFE). The call then raises `OSError(EINPROGRESS)` (115).
  - It does **not** wait for the SYN-ACK.
  - Completion is signalled by `POLLOUT` (§1.6), and failure by `POLLERR`/`POLLHUP`.
  - [source]
- **Timeout > 0.** The call spins in `poll_sockets()`, which handles scheduled callbacks but never
  runs asyncio, until it connects or times out.
  - On timeout it raises `ETIMEDOUT`. The PCB stays in SYN_SENT and lwIP keeps retrying. A second
  `connect()` then raises `EALREADY` (`:1211-1217`).
  - [source]
- **Blocking (the default -1).** The call spins until lwIP itself gives up. That takes about
  18.5 s for an unanswered SYN (next bullet), which is far past the 8,388 ms watchdog. [inference]
- **Unanswered SYN (host or port silent).**
  - In SYN_SENT the RTO stays at its initial value and is not backed off (`tcp.c:1288-1293`):
    `LWIP_TCP_RTO_TIME` 3000 ms (`opt.h:1375`, set in `tcp_alloc()` at `tcp.c:1906-1907`).
  - After `TCP_SYNMAXRTX` = 6 retransmissions (`opt.h:1313`, checked at `tcp.c:1232`), the slow
    timer (500 ms) removes the PCB and calls the error callback with **`ERR_ABRT`**
    (`tcp.c:1413`).
  - Python therefore sees **`ECONNABORTED` (103), not `ETIMEDOUT`**.
  - Timeline: retransmits at about 3, 6, 9, 12, 15 and 18 s, abort at about **18.5 s** (±0.5 s
    timer phase). [source + inference for the arithmetic]
- **ICMP destination-unreachable is ignored by TCP.** lwIP only counts it
  (`core/ipv4/icmp.c:258-260`), so an unreachable remote is also detected only after about 18.5 s.
  [source]
- **No route (WLAN link down, no IPv4 address, interface removed).** `tcp_connect()` returns
  `ERR_RTE` immediately (`tcp.c:1090-1099`; `ip4_route()` requires up, link up and a non-zero
  address, `core/ipv4/ip4.c:172, 216-224`). `connect()` raises **`EHOSTUNREACH` (113)
  synchronously**, even on a non-blocking socket. [source]
- **Port closed (RST answers the SYN).** `tcp_in.c:442-447` delivers `ERR_RST`, so Python sees
  **`ECONNRESET` (104)**. lwIP has no `ECONNREFUSED`; the lwIP 2.x error table maps no code to it
  (`modlwip.c:262-288`). [source]
- **Pool or memory failure inside `tcp_connect()` (SYN segment).** Raises `ENOMEM`. [source
  (`error_lookup_table[1]`)]

### 1.4 `settimeout()` / `setblocking()`

- **`settimeout(None)` is -1 (block forever), `settimeout(0)` is non-blocking, and `settimeout(x)`
  is `x*1000` ms** (`:1442-1456`). `setblocking(True/False)` sets -1 or 0 (`:1459-1468`). [source]
- **Every timed wait inside modlwip blocks the VM.** Each one (`connect` `:1236-1246`, `send` loop
  `:778-788`, `recv` loop `:861-867`, `accept` `:1136-1150`) is a `poll_sockets()` busy-wait. It
  services scheduled callbacks but never yields to asyncio. Inside the asyncio firmware **only
  timeout 0 is acceptable**: the WDT is fed from the `_supervise()` task every 2 s
  (`src/asy_system_service.py:356-394`). [source + inference]

### 1.5 Reads and writes on non-blocking sockets

**`read`/`readinto`/`recv`** (`lwip_tcp_receive`, `:832-916`):

| Condition | Result |
|---|---|
| no data, `state < 0` | the lwIP error (mapped) is raised once. `ECONNRESET` then sets `STATE_PEER_RST_HANDLED`; any other error sets `_ERR_BADF` (-17), so later calls raise `EBADF` (`:838-849`) |
| no data, connected, non-blocking | `EAGAIN` (`:852-858`), which the stream layer returns as `None` |
| no data, peer FIN (`STATE_PEER_CLOSED`) or `STATE_PEER_RST_HANDLED` | returns 0, i.e. EOF / `b""` (`:853-855`) |
| data queued | copies from the **first pbuf only**: `len = min(len, p->len - recv_offset)` (`:887-893`), frees the pbuf when consumed, calls `tcp_recved(len)` (`:895-910`) |

- **Each low-level read returns at most one pbuf's payload.** That is ≤ 800 B with `TCP_MSS = 800`
  and one pool pbuf per segment (§4.3). `stream.readinto(buf)` without `ONCE` loops until the
  buffer is full or the next read hits `EAGAIN` (`py/stream.c:45-79`, `:310-313`), so one
  `readinto` drains several pbufs. [source]
- **`recv(n)`/`read(n)` allocate the full `n` bytes up front** (`vstr_init_len(&vstr, len)`,
  `modlwip.c:1324`; `py/stream.c:122-160`). **`readinto()` into a preallocated buffer is the
  allocation-free path.** [source]

**`write`/`send`** (`lwip_tcp_send`, `:750-826`):

- **The error check only looks at `state < 0`.** `STREAM_ERROR_CHECK` (`:732-737`) checks the state
  and then only `assert`s the pcb. **After a read has turned `ERR_RST` into
  `STATE_PEER_RST_HANDLED` (6, pcb NULL), a write passes the check and calls
  `tcp_sndbuf(NULL)`** (`:760`). This is the H.7.1 / F.9 `peer_gone` finding, and it is unchanged
  at v1.29.0. [source]
- **Write size and `EAGAIN`.** The write is `available = tcp_sndbuf(pcb)` (≤ `TCP_SND_BUF` 6400),
  and `write_len = min(available, len)`. A non-blocking socket with `available == 0` raises `EAGAIN`
  (`:763-768`). [source]
- **The `ERR_MEM` loop blocks the VM even on a non-blocking socket.**

  ```c
  // :801-813
  for (int i = 0; i < 200; ++i) {
      err = tcp_write(socket->pcb.tcp, buf, write_len, TCP_WRITE_FLAG_COPY);
      if (err != ERR_MEM) break;
      err = tcp_output(socket->pcb.tcp);
      if (err != ERR_OK) break;
      MICROPY_PY_LWIP_EXIT
      mp_hal_delay_ms(50);
      MICROPY_PY_LWIP_REENTER
  }
  ```

  - It blocks for up to 10 s (B.14.2 documents this). **10 s exceeds the 8,388 ms watchdog cap, so
    on this firmware the block would end in a WDT reset, not a stall.** [inference]
  - It is reached when the `MEM_SIZE` arena or the `TCP_SEG` pool is full. For a connection whose
    link is dead, unacked data is never freed.
- **Nagle then decides whether to send now** (`tcp_output_nagle`, `:817-819`;
  `include/lwip/priv/tcp_priv.h:100-106`). `TCP_NODELAY` stays off by project rule (F.9). [source]
- **While the link is down, a write can raise even though its data was queued.** `tcp_output()`
  returns **`ERR_RTE` → `EHOSTUNREACH`** when there is no route (`lib/lwip/src/core/tcp_out.c:1294-1296`),
  so the write raises **after `tcp_write()` already queued the data**. If Nagle defers, the same
  write returns success. **A write exception therefore does not mean "nothing was sent".** Never
  retry the same bytes on the same connection; reconnect instead. [source + inference]
- **`sendall()` on a non-blocking socket** raises `EAGAIN` up front if `len > tcp_sndbuf`
  (`:1411-1420`). [source]

### 1.6 `select.poll` / `ipoll` readiness for lwIP sockets

- **rp2 has no POSIX poll path** (`MICROPY_PY_SELECT_POSIX_OPTIMISATIONS` 0, F.7 row 12). `poll`
  calls each registered object's `ioctl(MP_STREAM_POLL)` in a loop, then waits in
  `mp_event_wait_ms(remaining)` (`extmod/modselect.c:293-339, 397-411`). Readiness is
  level-triggered and re-evaluated after every wake. [source]

`lwip_socket_ioctl(MP_STREAM_POLL)`, `modlwip.c:1604-1666`:

| Socket state | Reported |
|---|---|
| `STATE_NEW` | `HUP` (`:1646-1648`), so never register a fresh unconnected socket |
| `STATE_CONNECTING` | nothing; `WR` requires `state != CONNECTING && pcb && tcp_sndbuf > 0` (`:1639-1642`) |
| `STATE_CONNECTED` | `RD` if a pbuf is queued; `WR` if `tcp_sndbuf > 0` |
| `STATE_PEER_CLOSED` (FIN) | whatever `RD`/`WR` was asked for (`:1649-1653`); a read gives EOF |
| `ERR_RST` (-14) | `RD` + `WR` + `ERR` + `HUP` (`:1615-1621`, `:1654-1657`) |
| `STATE_PEER_RST_HANDLED` | `RD` + `HUP` (`:1658-1659`) |
| `_ERR_BADF` (closed) | `NVAL` (`:1660-1661`) |
| any other `< 0` (e.g. `ERR_ABRT` -13) | `ERR` only (`:1662-1665`) |

**Effect on asyncio [source + inference].** `IOQueue.wait_io_event()` wakes the reader on
`ev & ~POLLOUT` and the writer on `ev & ~POLLIN` (`extmod/asyncio/core.py:113-131`). An error
state therefore wakes both waiters, and the next I/O call raises.

### 1.7 `close()`: FIN vs RST, and how long the PCB lingers

`MP_STREAM_CLOSE` (`modlwip.c:1668-1711`):

1. **Queued receive pbufs are freed without `tcp_recved()`** (`lwip_socket_free_incoming(socket,
   true)`, `:1670`, `:380-386`).
2. **The callbacks are deregistered.** For a non-listening socket a poll callback,
   `_lwip_tcp_close_poll`, is armed at `MICROPY_PY_LWIP_TCP_CLOSE_TIMEOUT_MS / 500` (= 20 coarse
   ticks = **10 s**). It `tcp_abort()`s the PCB if it has not closed by then (`:1683-1690`,
   `:1586-1591`). `MICROPY_PY_LWIP_TCP_CLOSE_TIMEOUT_MS` is an **unguarded `#define`** (`:64`), so
   only a B.14.1-style override could change it.
3. **`tcp_close()`** (`:1691-1694`), whose behaviour depends on what is left unread:
   - **Unread data** (`rcv_wnd != TCP_WND_MAX`, which is always true after step 1 dropped unread
     pbufs): **RST**, and the PCB is freed at once (`lib/lwip/src/core/tcp.c:352-374`).
   - **Everything read:** **FIN**. ESTABLISHED goes to FIN_WAIT_1, CLOSE_WAIT goes to LAST_ACK
     (`tcp.c:409-437`).
4. **The socket is set to `_ERR_BADF`**, so every later call raises `EBADF` (`:1709-1710`).
   - A close after lwIP already aborted the PCB (pcb NULL) only sets `_ERR_BADF` (`:1672-1675`).
   - **Closing on the first error is therefore the one safe reaction.** It also closes off the
     write-through-NULL-pcb path in §1.5. [source]

How long the PCB outlives `close()`, by case:

| Case | What lwIP does | PCB held |
|---|---|---|
| Unread data at close | RST, freed | 0 |
| Peer closed first (we are in CLOSE_WAIT) | FIN, then LAST_ACK | until the ACK, ≤ 10 s (modlwip abort); reclaimable by `tcp_alloc()` (`tcp_kill_state(LAST_ACK)`, `tcp.c:1756-1784`) |
| We close first, link healthy | FIN_WAIT_1/2, then **TIME_WAIT for 2·TCP_MSL = 120 s** (`priv/tcp_priv.h:134`, `tcp.c:1449`) | 120 s, but TIME_WAIT is reclaimed first when the pool is empty (`tcp_kill_timewait`, `tcp.c:1788-1806`) |
| We close first, **link dead** (typical after an MQTT keepalive timeout) | FIN never ACKed, stuck in FIN_WAIT_1 | **≤ 10 s, then modlwip aborts.** FIN_WAIT is **not** reclaimable at equal priority (`tcp_kill_prio`, `tcp.c:1710-1750`, strictly lower prio only), so for those 10 s it uses a pool slot that nothing else can take |
| Socket dropped without `close()` | nothing until the GC finaliser runs | indefinitely, if ESTABLISHED |

- **The `close()` path never sends a TLS close_notify** (§3).
- **Not covered by the 10 s abort:** a TIME_WAIT PCB sits on `tcp_tw_pcbs`, which is never polled
  (`tcp.c:1440-1467`). It ages 120 s (reclaimable).

### 1.8 Error codes that reach Python (lwIP 2.2.1 table, `modlwip.c:262-288`)

| errno | Where it arises for a TCP client |
|---|---|
| `EINPROGRESS` 115 | non-blocking `connect()` (normal) |
| `EAGAIN`/`EWOULDBLOCK` 11 | non-blocking read/write with nothing to do; the stream layer turns it into `None` (`py/stream.c:225-231, 258-262`) |
| `ECONNRESET` 104 | RST from the peer: refused connect, or reset mid-stream. Raised once on read; later reads return EOF |
| `ECONNABORTED` 103 | `ERR_ABRT`: SYN retries exhausted (about 18.5 s); data retries exhausted (§1.9); the netif removed or the IP changed (§5.1); keepalive (unreachable, §1.10) |
| `EHOSTUNREACH` 113 | no route (link down / no IP), synchronous from `connect()`, or from a write whose `tcp_output()` failed (§1.5) |
| `ENOTCONN` 107 | `ERR_CONN`/`ERR_CLSD` (e.g. `tcp_write` on a closing PCB); recv on a listening socket |
| `ENOMEM` 12 | no free PCB at `socket()`; `ERR_MEM` from `tcp_connect`; TLS buffer allocation (§3) |
| `EBADF` 9 | any call after `close()` or after an error was consumed (`_ERR_BADF`) |
| `ETIMEDOUT` 110 | **only** from a modlwip socket timeout > 0 (`:784-786`, `:863-866`, `:1244`), never from lwIP itself |
| `EALREADY` / `EISCONN` | second `connect()` (`:1211-1217`) |

**No v1.29.0 TCP or TLS path raises a negative errno like `OSError(-110)`.**
- TLS turns pass-through socket errors back to positive with a -256 cutoff
  (`extmod/modtls_mbedtls.c:180-185`).
- `network_cyw43` negates cyw43 errors to positive (`extmod/network_cyw43.c:111, 233, 311`).
- Negative codes still come from `getaddrinfo()`: `-2` (DNS failure, `modlwip.c:1815`) and raw
  lwIP codes such as `-6` `ERR_VAL` when no DNS server is set (`:1882-1889`).
- Peter Hinch's `mqtt_as` lists `-110` as a "busy" error on RP2 (`mqtt_as/__init__.py:46-47` in
  the clone at `scratchpad/ext/micropython-mqtt`). That entry is presumably historical. [source +
  inference]

### 1.9 How long lwIP alone takes to notice a dead peer with data in flight [source + inference]

- **The mechanism.** The RTO is backed off by `tcp_backoff[] = {1,2,3,4,5,6,7,7,…}` (`tcp.c:163-164`,
  used at `:1290-1293`). The PCB is aborted after `TCP_MAXRTX` = 12 (`opt.h:1306`, `tcp.c:1235`),
  which gives **`ECONNABORTED`**. The total wait is about **767 × base RTO**.
- **The base RTO** comes from `sa`/`sv` in 500 ms ticks:
  - It starts at `sv = 6` ticks (3 s) (`tcp.c:1906-1907`).
  - On a LAN with sub-tick RTTs it decays toward `sv ≈ 3` ticks (1.5 s) (`tcp_in.c:1353-1366`).
- **The resulting detection times:**
  - **≈ 19 min** at base 1.5 s.
  - **≈ 38 min** if no RTT sample was ever taken (base 3 s).
  - **Never**, if nothing is unacked (idle connection, no keepalive; §1.10).

**Consequence:** the MQTT client's own PINGRESP deadline is the only practical dead-link detector.

### 1.10 TCP keepalive: not available

- **The keepalive machinery exists in lwIP but cannot be reached from Python.** lwIP's slow timer
  does run keepalive probes when `SOF_KEEPALIVE` is set (`tcp.c:1333-1352`), with idle
  `TCP_KEEPIDLE_DEFAULT` 7,200,000 ms (`priv/tcp_priv.h:139`).
  - `LWIP_TCP_KEEPALIVE` (per-PCB idle/interval/count) is left at its default **0** (`opt.h:2078`).
    Neither `lwipopts_common.h` nor rp2's `lwipopts.h` sets it, and the project's `[lwip]` table
    doesn't either.
  - **modlwip's `setsockopt` has no `SOF_KEEPALIVE` case.** It handles only `SO_REUSEADDR`,
    `SO_BROADCAST`, `IP_ADD/DROP_MEMBERSHIP`, `TCP_NODELAY` and the private option 20 (callback)
    (`modlwip.c:1477-1545`).
  - **The `level` argument is ignored.** An unknown option **prints `Warning: lwip.setsockopt() not
    implemented` to the console and returns `None` without raising** (`:1538-1540`). That console
    write can stall on a held USB port (F.1).
  - **The `socket` module exports no `SO_KEEPALIVE` constant** (`:1932-1943`). [source]
- **Other gaps relevant to a client:** no `shutdown()`, `getsockopt()`, `getsockname()`,
  `getpeername()`, `fileno()` or `SO_LINGER` (locals table, `:1718-1739`). [source]

---

## 2. `asyncio` streams (`extmod/asyncio/stream.py`, unchanged since v1.28.0)

### 2.1 `open_connection()`

```python
# stream.py:99-123
def open_connection(host, port, ssl=None, server_hostname=None):
    ai = socket.getaddrinfo(host, port, 0, socket.SOCK_STREAM)[0]  # TODO this is blocking!
    s = socket.socket(ai[0], ai[1], ai[2])
    s.setblocking(False)
    try:
        s.connect(ai[-1])
    except OSError as er:
        if er.errno != EINPROGRESS:
            raise er
    if ssl: ... s = ssl.wrap_socket(s, server_hostname=server_hostname, do_handshake_on_connect=False); s.setblocking(False)
    ss = Stream(s)
    yield core._io_queue.queue_write(s)
    return ss, ss
```

- **`getaddrinfo` is synchronous** (§6). With an **IPv4 literal** it returns without any network
  I/O: `ipaddr_aton` short-circuits at `lib/lwip/src/core/dns.c:1606-1614`. Because it goes through
  `getaddrinfo()[0][-1]`, the same call is portable to the Unix port, whose `connect()` needs a
  packed sockaddr (F.7 row 1). [source]
- **The connect itself is non-blocking.** Synchronous failures raise out of `open_connection`:
  `EHOSTUNREACH` (no route) and `ENOMEM` (no PCB).
- **Asynchronous failures do not raise out of `open_connection()`.** A refused or aborted connect
  wakes the `queue_write` wait through `POLLERR`/`HUP` (§1.6), and `open_connection()` **returns a
  Stream anyway**. The error appears at the first read or write.
  - The docs claim it "Will raise a socket-specific `OSError` ... if the connection could not be
    made" (`docs/library/asyncio.rst:203-214`). That is true only for the synchronous cases.
    [source]
- **There is no timeout.** A silent host leaves `open_connection` waiting about 18.5 s until
  lwIP's `ERR_ABRT`.
- **Wrapping it in `wait_for()` leaks the socket on timeout.** Cancellation hits the `yield`
  (`:122`). The local socket `s` is then unreferenced, and **only the GC finaliser closes it**.
  - If the SYN-ACK arrives after the cancel, an ESTABLISHED PCB is held until the next GC pass.
  - **Better:** a project-owned connect helper that keeps the socket and `close()`s it in
    `finally`. [source + inference]
- **`ssl=` is supported.** It wraps with `do_handshake_on_connect=False` (`:112-120`); see §3.

### 2.2 The Stream methods (`stream.py:7-88`)

- **`read(n)` / `readinto(buf)`.** Each does one `queue_read` wait, then a non-blocking stream
  call (`:24-39`). `read(n)` allocates `n` bytes per call (§1.5), and `read(-1)` concatenates
  (`r += r2`).
- **`readexactly(n)`** loops with `r += r2` concatenation (`:42-52`). It allocates repeatedly, and
  partial data is lost on cancellation. The project already avoids it in the twin
  (F.9, `digital_twin/_http_client.py`).
- **`readline()`** uses the unbuffered `mp_stream_unbuffered_readline` (`:55-64`).
- **`write(buf)`** first writes straight to the socket when `out_buf` is empty. Any remainder is
  appended to `out_buf`, which allocates (`:66-74`).
- **`drain()`** always yields at least once (`sleep_ms(0)`), then loops on `queue_write` +
  `s.write(mv[off:])` (`:77-88`).
- **`Stream.close()` is a no-op (`:16-17`). Only `await wait_closed()` closes the socket
  (`:19-21`).** The docs present `close()` as "Close the stream" (`asyncio.rst`), so a client that
  only calls `close()` leaks the socket and its PCB until GC. [source]
- **Each `await` of a Stream method allocates.** It creates a generator object. A first-direction
  wait also allocates the `IOQueue` entry list and the `select.poll` registration
  (`core.py:75-89`). This is small, steady churn (F.1 already notes the `wait_for` cost). [source]

### 2.3 Waiting, cancellation and `wait_for`

- **IOQueue mechanics.** `IOQueue._enqueue()` records the task per stream in an entry
  `[reader, writer, s]`. A second waiter in the **same** direction fails
  `assert sm[idx] is None` (`core.py:75-89`), as F.1 says. Two concurrent `drain()`s on one stream
  would hit that assert. Upstream [#6621](https://github.com/micropython/micropython/issues/6621)
  (duplicate frames from concurrent drains, closed without a recorded fix) is the older form of the
  same hazard. **Use one writer task, or a `Lock` around write+drain.**
- **Cancelling one waiter strands the other direction's waiter (new; not in SPECIFICATION).**
  - Cancelling a task that waits on a stream calls `IOQueue.remove(task)` (`modasyncio.c:217-224`
    → `core.py:100-111`).
  - `remove()` calls `_dequeue(s)` (`core.py:90-92`), which **deletes the whole entry and
    unregisters the stream.** So if a reader task and a writer task both wait on the same socket
    and one is cancelled (for example by a `wait_for` timeout on the read), **the other task is
    left with `data = IOQueue` but is no longer registered anywhere, and never wakes on I/O.** It
    hangs until it is itself cancelled.
  - I found no upstream issue for this. [source; the symptom is inference]
  - Design rule: **never cancel one direction of a shared stream while the other direction may be
    waiting.** Either keep a single I/O task, or put a timeout on both waits and treat any timeout
    as "connection dead, close it".
- **What `wait_for(aw, t)` does on timeout.** It cancels the runner and raises `TimeoutError`
  (`funcs.py:24-51`). The cancelled read gets `CancelledError` at its `yield`. The socket stays open
  and its unread lwIP data stays queued. **Bytes already pulled by `readexactly`'s loop are lost,
  so a timeout mid-MQTT-packet desynchronises the framing. Close the connection after any timeout
  inside a packet.** [source + inference]
- **Not exposed:** `start_tls`, `local_addr`, and a connect timeout.

---

## 3. TLS on rp2 (`extmod/modtls_mbedtls.c`, mbedTLS 3.6.6)

### 3.1 Configuration and handshake

- **Configuration.** `ports/rp2/mbedtls/mbedtls_config_port.h:30-42` includes the common config
  with `MICROPY_MBEDTLS_CONFIG_BARE_METAL` set (`extmod/mbedtls/mbedtls_config_common.h`).
  - **TLS 1.0-1.2 only.** `MBEDTLS_SSL_PROTO_TLS1_3` is not defined (`:57-59`).
  - SNI is on (`:60`). Curves P-192 to P-521 plus K-curves; RSA and ECDHE key exchange; PSK. CBC is
    enabled, which raises the padding overhead (`:36-56`).
  - **No max-fragment-length extension.**
  - **`MBEDTLS_SSL_KEEP_PEER_CERTIFICATE` is not defined**, so `getpeercert()` is not built
    (`modtls_mbedtls.c` `#if` around `:850-862`).
  - DTLS is compiled in (`MICROPY_PY_SSL_DTLS`, `py/mpconfig.h:2176-2177`).
  - [source]
- **The handshake is non-blocking only with `do_handshake_on_connect=False`.**
  - `wrap_socket()` defaults to `True` (`:630`). That path spins `mbedtls_ssl_handshake()` +
    `mp_event_wait_ms(1)` until done (`:818-825`), **blocking the VM for the whole handshake** even
    on a non-blocking socket.
  - With `False`, the handshake is driven lazily by `mbedtls_ssl_read/write`. `WANT_READ/WANT_WRITE`
    become `EAGAIN`, and `poll_mask` records which direction mbedTLS actually needs
    (`:876-950`).
  - `open_connection(ssl=…)` uses `False` (`stream.py:119`). [source]
- **`MP_STREAM_POLL` is handled correctly for asyncio** (`:962-1027`):
  - Data already buffered in mbedTLS short-circuits to `RD` (`mbedtls_ssl_check_pending`,
    `:993-1001`).
  - A pending handshake direction is substituted for the asked one, and a fake ready is returned so
    the stream re-enters read/write (`:986-990`, `:1019-1024`).
  - An error or a closed socket reports `NVAL` (`:979-982`). The error is sticky: `last_error`
    makes every later op raise the same error (`:880-883`).
  - [source]
- **Each crypto step runs synchronously inside one read/write call.** That covers ECDHE keygen,
  signature verify and RSA, so a TLS handshake produces **multi-hundred-ms (possibly longer)
  event-loop stalls on the M0+**. This is unmeasured here.
  - A third-party estimate of "300–400 ms TLS handshakes" (Gadgetoid, board unspecified) is in
    [discussion #13022](https://github.com/orgs/micropython/discussions/13022). [inference / issue]
- **Errors.** Socket errors pass through as `-errno` and come back positive (`:174-185`, `:678-711`).
  `MBEDTLS_ERR_SSL_ALLOC_FAILED` becomes **`OSError(ENOMEM)`** (`:166-167`). Other mbedTLS codes
  are large negatives with a message (`:187-210`). [source]
- **`close()`** frees the mbedTLS context and then closes the underlying lwIP socket (`:970-976`,
  falling through to `:1016-1017`). **It sends no `close_notify`.** [source]

### 3.2 Heap cost per TLS connection

| Item | Bytes | Where |
|---|---|---|
| `in_buf` = header 13 + IV 16 + MAC 48 (SHA-384) + CBC padding 256 + `IN_CONTENT_LEN` 16,384 | **16,717** | `library/ssl_misc.h:296-330, 392-409`; `mbedtls_config_common.h:63-65`; allocated at `ssl_tls.c:1390-1410` |
| `out_buf` = 13 + 320 + `OUT_CONTENT_LEN` 4,096 | **4,429** | same, `ssl_tls.c:1418-1420` |
| allocator | GC heap via `m_tracked_calloc` (8 B node header, rounded to 16 B blocks, so about **16,736 + 4,448**) | `py/malloc.c:277-300`; `MICROPY_TRACKED_ALLOC` on rp2 (`ports/rp2/mpconfigport.h:122`) |
| handshake state, ECDH/bignum temporaries, peer chain parse, the context's CA chain | not measured | — |

**What this means for this project [inference].**
- **Both buffers are single contiguous GC blocks.** They are allocated at every `ssl_setup`, i.e.
  every reconnect, and freed at close.
- **Measured headroom (H.7, I.5, F.5.3).** About 115 KB is the largest free block after
  `build_system()`. At peak HTTP load the largest free block was **~1.5 KB**.
- **A TLS reconnect under HTTP load is therefore likely to fail with `ENOMEM`.** Under the I.4 rule
  ("design for zero `MemoryError`s first"), TLS would need a dedicated solution, which upstream does
  not offer.
- **The finaliser.** `MICROPY_PY_SSL_FINALISER` follows `MICROPY_ENABLE_FINALISER`, which is on at
  rp2's ROM level (`py/mpconfig.h:2166-2167`). An abandoned `SSLSocket` is therefore eventually
  freed, but only at GC. Tracked allocations stay rooted (`m_tracked_head`) until then.
- **Certificate validity uses the RTC.** The relevant settings are `MBEDTLS_HAVE_TIME_DATE`
  (`mbedtls_config_common.h:36-37`) and `MBEDTLS_PLATFORM_TIME_MACRO rp2_rtctime_seconds`
  (`mbedtls_config_port.h:33-36`). The boot clock reads 2021-01-01 until NTP sync (F.1), so with
  `CERT_REQUIRED` **verification fails ("not yet valid") before the first NTP sync**. Upstream
  tests time-based failure in `tests/multi_net/sslcontext_verify_time_error.py`. [inference from
  config + F.1]

---

## 4. Memory per TCP connection, and the lwIP budget for one extra connection

### 4.1 Where the bytes live

**lwIP side (static `.bss`, which shrinks the GC heap 1:1 on rp2):**

- **A `tcp_pcb`** from `memp_memory_TCP_PCB` (`include/lwip/priv/memp_std.h:50`). The project
  measured **196 B per slot** (B.14.2).
- **A `tcp_seg` per queued outbound segment, and per out-of-order inbound segment.** These come
  from `TCP_SEG` (`memp_std.h:52`), measured at **16 B each**.
- **Outbound payload goes through the `MEM_SIZE` arena.** `tcp_write(..., TCP_WRITE_FLAG_COPY)`
  (`modlwip.c:802`) calls `tcp_pbuf_prealloc()`, which calls `pbuf_alloc(PBUF_TRANSPORT, ..., PBUF_RAM)`
  (`tcp_out.c:228-273`), which calls `mem_malloc()` (`core/pbuf.c:275-287`).
  - **Per allocation:** `struct mem` 8 + `struct pbuf` 16 + transport headroom 74 (IPv6-enabled,
    aligned 76) + payload.
  - **Allocation size depends on Nagle.** When Nagle would defer (unacked or unsent data exists,
    no `TF_NODELAY`), lwIP allocates an **oversized MSS pbuf (~900 B)** that later writes fill
    (`tcp_out.c:245-264`). Otherwise it allocates the exact size: a 2-byte PINGREQ costs about
    104 B and a 300-byte PUBLISH about 400 B. [source + inference for the sums]
  - **It is held until the peer ACKs it.** At most `TCP_SND_BUF` = 6,400 B of payload per
    connection, and `TCP_SND_QUEUELEN` = 32 segments (derived, B.14.2).
- **Inbound frames come from `PBUF_POOL`.** The driver allocates
  `pbuf_alloc(PBUF_RAW, len, PBUF_POOL)` per received frame
  (`lib/cyw43-driver/src/cyw43_lwip.c:279-288`). **If the pool is empty the frame is silently
  dropped.** Each pool pbuf is **892 B** (16 + 876), `PBUF_POOL_BUFSIZE` 876 (`memp_std.h:134`;
  B.14.2). A full-MSS IPv4 segment (14 + 20 + 20 + 800 = 854 B) fits one pbuf. The pbufs stay
  chained on the socket until Python reads them (§1.2).

**MicroPython side (GC heap):**

- **`lwip_socket_obj_t`**, about 60 B, i.e. **~64 B (4 blocks) with a finaliser**: base,
  pcb pointer, incoming union, callback, `ip_addr_t` (24 B with IPv4+IPv6), port, timeout,
  `recv_offset`, domain/type/state (`modlwip.c:307-361`). [inference from the struct layout]
- **The `Stream` instance, the per-wait IOQueue entry, and the `select.poll` registration** — small.
- **Application buffers:** whatever the client preallocates. **No receive data lives on the GC
  heap until it is read.**
- **TLS adds §3.2.**

### 4.2 Budget arithmetic: shipped values plus one permanent MQTT connection

The shipped table (`toolchain/versions.toml:41-62`) is sized for `max_connections = 6`:
`MEMP_NUM_TCP_PCB` 9, `MEMP_NUM_TCP_SEG` 48, `MEM_SIZE` 12,000, `PBUF_POOL_SIZE` 16, `TCP_MSS` 800,
`TCP_WND` 6,400, `TCP_SND_BUF` 6,400.

The project's own per-connection rules are in `toolchain/micropython_overrides.py:259-285` and
B.14.2. Counting the MQTT link as one more connection (N = 6 + 1 = 7):

| Option | Rule | Shipped | Needed | Δ | GC-heap cost (B.14.2 unit costs) |
|---|---|---|---|---|---|
| `MEMP_NUM_TCP_PCB` | N + 3 spares | 9 | **10** | +1 | 196 B |
| *(optional)* one more PCB for a dead-link FIN_WAIT left by the previous MQTT socket (§1.7: ≤ 10 s, not reclaimable) | — | — | 11 | +1 | 196 B |
| `MEMP_NUM_TCP_SEG` | N × `TCP_SND_BUF`/`TCP_MSS` = 7 × 8 | 48 | **56** | +8 | 128 B |
| `MEM_SIZE` | N × 2,000 floor | 12,000 | **14,000** | +2,000 | 2,000 B |
| `PBUF_POOL_SIZE` | no project rule; lwIP's init.c check `TCP_WND ≤ pool × (876-74)`: 6,400 ≤ 12,832 still holds | 16 | 16 | 0 | (892 B each if raised) |
| **Total** | | | | | **2,324 B** (2,520 B with the optional PCB) |

- **The total checks out.** 196 + 128 + 2,000 = 2,324 B, exactly the project's measured
  coherent-ensemble step. The B.14.2 table's `max_connections = 7` row (PCB 10 / SEG 56 /
  MEM 14,000) shows −7,364 B against the pinned baseline, i.e. −2,324 B against the shipped image.
  [source: SPECIFICATION]
- **The optional PCB.** It is needed only if a reconnect can start within 10 s of closing a socket
  whose link is dead. A reconnect backoff of ≥ 10 s makes it unnecessary, because modlwip's abort
  has fired by then. [inference]
- **The alternative** is no image change, with `max_connections = 5` freeing one PCB, 8 segments
  and a 2,000 B share for MQTT. That is an owner trade-off (H.7 chose 6 for heap stability).
- **The gap in the checks.** Neither `check_lwip_ensemble()` nor `buildgen/validate.py`
  (`:219-250`) can express an outbound connection today; both take only `max_connections`.

### 4.3 Inbound bursts (e.g. a retained-message flood after SUBSCRIBE) vs `TCP_WND` and `PBUF_POOL_SIZE` [source + inference]

- **The window caps unread bytes per connection at 6,400**, regardless of segment count. lwIP
  trims out-of-window data, and `tcp_recved()` reopens the window only as Python reads.
- **The pool caps how many frames the whole device can hold.** It is a single **16-pbuf** pool
  shared by every inbound frame: HTTP requests, ARP, DHCP, DNS/NTP replies, mDNS multicast
  (`LWIP_MDNS_RESPONDER 1`) and LAN broadcast. **There is no per-PCB quota.** A full-MSS MQTT
  window holds **8 pbufs**. A flood of **small** segments can hold **all 16**, because each
  segment occupies a whole 892 B pool pbuf.
  - When the pool is empty, `cyw43_cb_process_ethernet()` drops every frame. HTTP SYNs and ARP
    replies are dropped too, until Python drains the MQTT socket and TCP retransmits recover.
  - Whether the broker sends small segments depends on its Nagle setting (unverified).
- **This changes an assumption in B.14.2 / H.7.** They keep `PBUF_POOL_SIZE` at 16 because
  "inbound demand is one small request per connection". A subscribing MQTT connection breaks that
  assumption.
- **Mitigations without changing the image:**
  - A dedicated reader task that always drains the socket completely, using `readinto` into a
    preallocated buffer, on every wake.
  - Bounded subscriptions and retained sets.
  - A hard maximum MQTT packet size, with disconnect on oversize (an MQTT 3.1.1 client cannot
    advertise one).
- **Outbound backpressure.** Keep the client's own unacked bytes well under the 2,000 B MEM_SIZE
  share (e.g. one QoS-0 burst at a time, nothing new while the link is suspect). Then the 10 s
  `ERR_MEM` VM block in §1.5, which is a WDT reset here, cannot be reached by MQTT alone.

---

## 5. CYW43 link loss, status values, power save, and the upstream record

### 5.1 How a WiFi drop reaches lwIP and Python [source]

- **Link-down events.** A `DISASSOC` event calls `cyw43_cb_tcpip_set_link_down()` and zeroes
  `wifi_join_state` (`lib/cyw43-driver/src/cyw43_ctrl.c:353-355`). A `LINK` event with the "down"
  flag does the same (`:404-414`). Both call **`netif_set_link_down()`**
  (`cyw43_lwip.c:296-298`).
- **`netif_set_link_down()` does not touch TCP PCBs or the IP address** (`lwip/src/core/netif.c:1056-1080`).
  An ESTABLISHED connection **stays ESTABLISHED with no error**:
  - reads return `EAGAIN`;
  - writes either queue silently or raise `EHOSTUNREACH` (§1.5);
  - the connection is aborted only by retransmission exhaustion (§1.9).
- **When the link comes back,** `netif_set_link_up()` → `dhcp_network_changed_link_up()` →
  `dhcp_reboot()` re-requests the **same** address (`netif.c:1018-1028`,
  `core/ipv4/dhcp.c:938-966`).
  - **Same lease:** the old PCB silently resumes. The broker may already have dropped the session
    (1.5 × keepalive), in which case the next segment gets an RST, i.e. `ECONNRESET`.
  - **NAK:** the address is cleared (`dhcp.c:~334`), `netif_do_ip_addr_changed()` runs,
    `tcp_netif_ip_addr_changed()` calls `tcp_abort()` on each PCB, and Python sees
    **`ECONNABORTED`** (`netif.c:459-469`, `tcp.c:2309-2341`).
- **`WLAN.active(False)` / `WLAN.deinit()` / a mode switch** call `cyw43_cb_tcpip_deinit()` →
  `netif_remove()`. That **aborts every TCP PCB bound to the old address**, so Python sees
  `ECONNABORTED` (`network_cyw43.c:140-150`, `cyw43_ctrl.c:576-581`, `cyw43_lwip.c:246-266`,
  `netif.c:764-781`).
  - In this project that is `_switch_wlan_mode()` and `_deactivate_wlan_permanently()`
    (hotspot fallback).
  - **`WLAN.disconnect()`**, the project's plain reconnect, only sends `SET_DISASSOC`
    (`cyw43_ctrl.c:666-669`): link down, no abort.
- **`status()`** is `cyw43_tcpip_link_status()` (`cyw43_lwip.c:300-326`). With netif up and link up
  it returns 3 `STAT_GOT_IP` (address ≠ 0) or 2 (NOIP). Otherwise it returns the join state: 0 IDLE
  (after DISASSOC), 1 JOIN, −1 FAIL, −2 NONET, −3 BADAUTH (`cyw43.h:98-104`,
  `extmod/modnetwork.c:197-202`). `isconnected()` is `status == LINK_UP` (`network_cyw43.c:324-337`).
  - **Python's view therefore only changes when the radio firmware delivers a DISASSOC/LINK-down
    event.** The F.2 false positive is the case where no event arrives.
  - The netif IP address survives link-down, which matches
    [#9505](https://github.com/micropython/micropython/issues/9505).
- **The CYW43 firmware handles some failures itself.** `pend_rejoin` on PSK timeouts and
  `ICV_ERROR` makes it rejoin by itself (`cyw43_ctrl.c:415-432`).

### 5.2 Power management [source]

- **`pm` value layout:** `li_assoc<<20 | li_dtim<<16 | li_bcn<<12 | (pm2_sleep_ret_ms/10)<<4 | mode`
  (`network_cyw43.c:41-52`). `PM_NONE` = 0x10, `PM_PERFORMANCE` = 0xA11142 (PM2, 200 ms),
  `PM_POWERSAVE` = 0x11 (PM1).
- **The driver default is `CYW43_DEFAULT_PM` = `CYW43_PERFORMANCE_PM` (PM2)**, applied on the first
  interface up (`cyw43.h:637, 652`; `cyw43_ctrl.c:561`).
- **The project's `0xA11140` is PM_PERFORMANCE's listen-interval fields with mode 0.** It sets
  `WLC_SET_PM 0`, i.e. **no power save** (`cyw43_ll.c:1979-2019`). This is the Raspberry Pi guide
  value.
- **The project re-applies it after every `active(True)`** (`src/asy_wifi_service.py:326, 689`),
  which correctly overrides the driver default re-applied after `deinit()`.
- **What this means for MQTT [inference]:**
  - With PM2/PM1 the radio sleeps between DTIM beacons, adding beacon-interval latency to
    unsolicited inbound PUBLISHes.
  - Upstream reports tie power save to idle-connection failures (below).
  - Keeping power save off is right for a long-lived connection.
  - The MQTT PINGREQ is also the "periodic traffic" that upstream reports say keeps a Pico W
    reachable.

### 5.3 Upstream issues and discussions (status as fetched 2026-10-07)

| Link | Content | Status |
|---|---|---|
| [#9505](https://github.com/micropython/micropython/issues/9505) | IPv4 address persists after AP loss; `status()` can stay 3 (v1.19.1) | **open**, no maintainer reply |
| [#9455](https://github.com/micropython/micropython/issues/9455) | Pico W network inaccessible after idle (≈5 min with PS, ≥10 min without), `OSError: -2`; regular pings keep it alive | **open** |
| [#16482](https://github.com/micropython/micropython/issues/16482) | v1.24.1: 8/20 runs lost the network; `isconnected()` True / `status()` 3 while offline; mostly under `PM_POWERSAVE`; `PM_NONE` more reliable | **closed**, fixed by [#16914](https://github.com/micropython/micropython/pull/16914) (cyw43-driver v1.1.0, merged 2025-03-13, release 1.25.0: "attempt to reconnect to AP in response to validation error") |
| [#18797](https://github.com/micropython/micropython/issues/18797) | `getaddrinfo()` blocks indefinitely when WiFi active but not connected (Pico 2 W, v1.26.1) | **closed**, fixed by [#18805](https://github.com/micropython/micropython/pull/18805) / bfc69dbe8 (merged 2026-03-04, release 1.28.0); the alternative [#18801](https://github.com/micropython/micropython/pull/18801) (20 s cap + netif check) was not merged |
| [discussion #13022](https://github.com/orgs/micropython/discussions/13022) | 6th `socket()` raises `ENOMEM`: `MEMP_NUM_TCP_PCB` 5 (jimmo); 2026 follow-up: ~196 B per socket, ESP32 port runs `gc_collect()` to reclaim abandoned sockets, bare-metal lwIP ports do not | answered |
| [#10812](https://github.com/micropython/micropython/issues/10812) | Pico W sockets not released between runs | closed, no recorded fix |
| [micropython-lib#741](https://github.com/micropython/micropython-lib/issues/741) | Pico W HTTPS POST loses ~32-38 KB per call until `ENOMEM` (v1.20) | closed, cause not recorded |
| [discussion #12608](https://github.com/orgs/micropython/discussions/12608) | Pico W `ECONNRESET`/`ECONNABORTED`/"EOF" during long runs | discussion |
| [RPi forum t=347986](https://forums.raspberrypi.com/viewtopic.php?t=347986) | umqtt on Pico W: intermittent `ECONNABORTED` in `connect()` after days; replies recommend `mqtt_as` | forum |
| [#6621](https://github.com/micropython/micropython/issues/6621) | concurrent `drain()` duplicates frames | closed, no recorded fix |
| [#10482](https://github.com/micropython/micropython/issues/10482) | requests from an IRQ handler → `ECONNABORTED` | closed |

**No upstream issue found** for:
- lwIP PCB exhaustion caused by TIME_WAIT/FIN_WAIT after many reconnects (the mechanism is in
  §1.7);
- the IOQueue cancel-strands-the-other-direction behaviour (§2.3);
- the write-after-`ECONNRESET` NULL-pcb path (H.7.1).

---

## 6. DNS

- **F.2 is confirmed, with one refinement.** `lwip_getaddrinfo()` (`modlwip.c:1820-1900`) calls
  `dns_gethostbyname_addrtype()` under the lwIP lock (`:1864-1870`; the lwIP 2.x call is at
  **`:1868`**, while F.2 cites `:1866`, the lwIP-1.x branch). On `ERR_INPROGRESS` it runs
  **`while (state.status == 0) poll_sockets();`** (`:1877-1880`). There is no MicroPython-level
  timeout and no yield to asyncio. [source]
- **The block is bounded only by lwIP's DNS retry schedule** (`core/dns.c:1066-1112`;
  `DNS_TMR_INTERVAL` 1000 ms, `include/lwip/dns.h:54`; `DNS_MAX_RETRIES` 4, `opt.h:1176`;
  `DNS_MAX_SERVERS` 2, `opt.h:1171`). Queries go out at t = 0, 1, 2 and 4 s, and the server fails
  at about **7 s**. Then the backup server repeats the schedule.
  - **Worst case for an unreachable DNS: about 7 s with one configured server, about 14 s with
    two.** Both exceed or approach the 8,388 ms watchdog, given the 2 s feed cadence.
  - Before bfc69dbe8 the lwIP timer could stop, and the wait was unbounded (#18797).
  - A `.local` name takes lwIP's mDNS query path (`LWIP_DNS_SUPPORT_MDNS_QUERIES 1`,
    `lwipopts_common.h:59`; `dns.c:1636-1650`) on the same schedule.
  - [source + inference for the arithmetic]
- **Fast failures.** No DNS server set gives `ERR_VAL`, i.e. `OSError(-6)`, immediately
  (`dns.c:1647-1650`). A failure reported through the callback gives `OSError(-2)`
  (`modlwip.c:1815`, `:1889`). [source]
- **A numeric host never touches the network** (`dns.c:1606-1614`). That is why
  `start_server('0.0.0.0', …)` and `open_connection('<ip>', …)` are safe. [source]
- **What the MQTT client has to do:**
  1. Resolve the broker name with
     `asy_dns_client.resolve_ipv4(host, (wifi.get_dns_server_ip(),), timeout_ms=…, tries=…)`.
     It is non-blocking, never raises, and returns the literal directly for an IPv4 host.
  2. Pass the dotted quad to `asyncio.open_connection(ip, port)` or to its own connect helper.
     `getaddrinfo` on a literal is then a pure parse on both ports.
  3. Do **not** pass `server_hostname`-only names to `open_connection`. For TLS, pass the IP as
     `host` and the name as `server_hostname` (`stream.py:117-118`).
  - Constraints:
    - The project resolver is unicast-A-only, so a broker addressed by `*.local` (mDNS) is not
      supported without new code.
    - Each lookup takes a transient UDP PCB from `MEMP_NUM_UDP_PCB` 5, the same pattern as NTP.
    - Worst-case resolve time is (servers + 2 fallbacks) × `timeout_ms` × `tries`, all
      cooperative.

---

## 7. The Unix port: what an MQTT client cannot be tested against faithfully

The Unix `socket` is `ports/unix/modsocket.c`, i.e. host BSD sockets. F.7 rows 1-3 and 12 already
cover addresses and poll. The MQTT-relevant additions:

| Behaviour | Unix port (host kernel) | rp2 (lwIP) | Source |
|---|---|---|---|
| connect failure, closed port | `ECONNREFUSED` (111) | `ECONNRESET` (104) | `modsocket.c:198-226` vs §1.3 |
| SYN timeout | kernel's (Linux default about 127 s, `ETIMEDOUT` 110) [inference] | ≈ 18.5 s, **`ECONNABORTED` 103** | §1.3 |
| data-retransmit death | `ETIMEDOUT` after `tcp_retries2` (Linux ~15 min) [inference] | `ECONNABORTED` after ~19-38 min | §1.9 |
| no route | `ENETUNREACH`/`EHOSTUNREACH` from the kernel, often asynchronous | `EHOSTUNREACH` synchronous; also raised by a write while the link is down | §1.3, §1.5 |
| write after peer reset | `EPIPE` (32) / `ECONNRESET`; `SIGPIPE` is ignored (`ports/unix/main.c:456-467`) | `ECONNRESET`, or after a read consumed it, the **NULL-pcb write** (H.7.1), which cannot be reproduced on Unix | — |
| read granularity | whatever the kernel buffer holds | one pbuf (≤ 800 B) per low-level read | §1.5 |
| `setsockopt` | passed straight to the kernel (`modsocket.c:384-409`): `SO_KEEPALIVE`, `SO_LINGER` and `SO_ERROR` exist (`:710-731`); **no `IPPROTO_TCP`/`TCP_NODELAY` constants** | unknown options print a warning and are ignored; `TCP_NODELAY` exists but is unsafe (F.9) | §1.10 |
| `settimeout` | `SO_RCVTIMEO`/`SO_SNDTIMEO` (`:433-476`) | busy-wait inside modlwip | §1.4 |
| link loss / netif removal / DHCP change | **not reproducible** (no netif; loopback never goes down; the peer kernel keeps ACKing even if the app stops reading) | §5.1 | — |
| PCB ceiling, TIME_WAIT/FIN_WAIT holding pool slots, `MEM_SIZE`/`TCP_SEG`/`PBUF_POOL` exhaustion, the 10 s `ERR_MEM` VM block, frame drops on pool exhaustion | none | all real | §1.7, §4 |
| `getaddrinfo` | host libc (blocking, `/etc/hosts`), returns packed sockaddr | lwIP DNS, bounded only by its retry schedule | §6 |
| TLS buffers | mbedTLS uses **libc calloc** (bare-metal mode only in the `coverage` variant, `ports/unix/mbedtls/mbedtls_config_port.h`), so the ~21 KB per connection is **invisible to GC-heap tests** | 16,736 + 4,448 B contiguous GC blocks per connection | §3.2 |
| `select.poll` | real fds (POSIX path) | ioctl loop | F.7 row 12 |

**What carries over identically [source]:**
- the asyncio `Stream`/`IOQueue` Python code, including the §2.3 stranding hazard and the no-op
  `close()`;
- `open_connection`'s "returns a stream even on asynchronous failure";
- EOF handling (`b""` / `EOFError`).

Upstream's own cross-port expectations are pinned in `tests/multi_net/asyncio_tcp_client_rst.py(.exp)`
(server read after client RST, `OSError 104`) and `asyncio_tcp_close_write.py(.exp)` (write after own
close → `OSError`).

**Consequence [inference].** Link-loss, dead-peer and pool-exhaustion behaviour of an MQTT client
can only be pinned:
- with a bounded fake socket at L1/L2 that scripts the rp2 states of §1.6/§1.8 (the established
  `_StepPoller` pattern), or
- on the dev bench, which needs a go-ahead for each real-hardware session.

---

## 8. SPECIFICATION items that look stale or that an MQTT client touches

1. **F.2's "`extmod/modlwip.c:1866`"** cites the lwIP-1.x `#if` branch. The compiled lwIP 2.2.1
   call is `:1868`. Trivial.
2. **F.2 says #18797 is "fixed since v1.28.0".** That is correct, but the fix only bounds the block
   by lwIP's DNS schedule: ≈7 s per configured server, ≈14 s with two (§6). That is past the WDT
   cap, so "`getaddrinfo()` only on a numeric host" stays a hard rule. The bound is worth stating.
3. **F.2 / CLAUDE.md say the `isconnected()` false positive has "no upstream fix" and has been "open
   since v1.19.1/2022".**
   - #9505 (and #9455) are still open.
   - But #16482, the same symptom (`isconnected()` True / `status()` 3 while offline), was closed as
     fixed by #16914 (cyw43-driver v1.1.0, MicroPython 1.25.0). That fix is the `ICV_ERROR` →
     rejoin at `cyw43_ctrl.c:429-432` at the pin.
   - The project's observation on later firmware means a residual case remains, so the wording
     should name the partial upstream fix rather than "none".
4. **B.14.2 / H.7 / `check_lwip_ensemble()` / `buildgen/validate.py` cover only `max_connections`.**
   A permanent outbound connection is unrepresented. It needs a term such as
   `max_connections + outbound_connections` in all three per-connection rules (§4.2).
5. **B.14.2's `PBUF_POOL_SIZE` rationale** ("inbound demand is one small request per connection")
   no longer holds for a subscribing MQTT connection (§4.3).
6. **B.14.2's 10 s `ERR_MEM` block** is described as "never observed (lwIP is never the
   constraint)". For a long-lived connection on a dead link, unacked data persists for minutes
   rather than ≤ 15 s, so the scenario becomes reachable. **10 s also exceeds the 8,388 ms WDT
   cap**, which turns it into a reset, not a stall. Worth adding.
7. **F.9 `TCP_NODELAY` row: still accurate at v1.29.0.** `modlwip.c:1528-1536` has no NULL check
   and no `MICROPY_PY_LWIP_ENTER`. MQTT consequence: assemble each control packet into one buffer
   and write it with a single call, so Nagle never splits header from payload.
   - Setting `TCP_NODELAY` on a fresh, not-yet-connected pcb would avoid both hazards by
     construction [inference], but the row records the owner's decision.
8. **F.9 `peer_gone` row: still accurate** (`modlwip.c:732-737`, `:844`, `:507`, `:760`). An MQTT
   client with separate reader and writer tasks has the same exposure, so it needs the same "first
   `OSError` in either direction marks the connection dead; close immediately" rule.
9. **F.1's "one waiter per direction" should gain a sentence.** Cancelling either waiter dequeues
   the whole stream and strands the other (§2.3).
10. **Docs vs source.** The asyncio docs say `open_connection` raises when "the connection could not
    be made", and that `Stream.close()` closes. In source, asynchronous connect failures surface at
    first I/O, and `close()` is a no-op that only `wait_closed()` backs (§2.1, §2.2). This
    discrepancy is exactly the kind CLAUDE.md's "check current docs" rule exists for.
11. **F.7 could gain the MQTT-relevant Unix rows** of §7: error-code divergence, SYN timeout,
    `setsockopt` pass-through, missing `TCP_NODELAY` constant, and TLS buffers off-heap.

---

## 9. Constraints for an MQTT client design (condensed)

- **Connecting.**
  - Resolve with `asy_dns_client`, then connect to an IPv4 literal. Never call `getaddrinfo` on a
    name.
  - Socket always non-blocking. Never use `settimeout(>0)` or the default blocking mode.
  - Never use `wrap_socket()` with `do_handshake_on_connect=True`.
  - Own connect helper (or `open_connection`), bounded by `wait_for_ms`, keeping the socket so it
    can be `close()`d in `finally`.
  - Treat CONNACK, not `open_connection()` returning, as "connected".
- **I/O tasks.**
  - Use **one** writer path (a lock or a single task).
  - Use **one** reader task that drains with `readinto` into a preallocated buffer.
  - Do not cancel one direction while the other waits (§2.3).
  - On any `OSError` or `EOF` from either direction, or any timeout inside a packet:
    `await wait_closed()` (not `close()`) and reconnect.
- **Liveness.**
  - The client must run its own PINGREQ/PINGRESP deadline. lwIP gives no keepalive and takes about
    19-38 min to abort a dead link with data in flight, or never if idle.
  - Gate the client on `network_available_locked()`.
  - Expect `ECONNABORTED` on hotspot fallback or `deinit()`.
  - Expect a silently surviving PCB after a plain `disconnect()`/`connect()` reconnect; reconnect
    proactively after WiFi reconnects.
- **Memory and pools.**
  - +1 PCB, +8 SEG, +2,000 B `MEM_SIZE` (2,324 B GC heap); optionally one more PCB, or a reconnect
    backoff ≥ 10 s.
  - Cap in-flight unacked bytes and the maximum inbound packet size.
  - Keep power save off.
  - TLS costs about 21 KB of contiguous GC heap per reconnect and needs NTP sync first. It is
    likely incompatible with the project's peak-load heap figures, so plain TCP on the trusted home
    LAN matches the existing threat model (CLAUDE.md credentials rule).
