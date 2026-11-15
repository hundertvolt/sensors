> **Raw research report** (agent, 2026-10-07): written by a read-only research agent of the MQTT PoC research session, kept verbatim as the evidence base for `mqtt_poc/RESEARCH.md`. Tags such as [V]/[SRC] mean verified in source by that agent; [I]/[INFERENCE] are not verified; nothing here was run on hardware. Clone paths (`<research-session scratchpad>/ext/...`) refer to that session's temporary scratchpad, not to this repo. Line anchors into this repo are as of `1cff5a2`.

# 05 — MQTT client PoC: socket/port, memory/heap and testing requirements

Read-only analysis of `/home/user/sensors` (2026-10-07). Scope: what a new asyncio MQTT client
service (publish + subscribe, proof of concept, not consumed by other modules) must satisfy on
sockets/PCBs, heap, and the four test tiers, and what the existing infrastructure offers or lacks.

## 0. Provenance tags used below

- **[OWNER]** — a hard rule carrying an owner actor/date (CLAUDE.md or SPECIFICATION.md).
- **[RULE]** — a standing rule in CLAUDE.md/SPECIFICATION.md recorded by the agent or without an
  owner actor; still binding as written project policy, but not an owner quote.
- **[PRECEDENT]** — how existing code/tests do it; the natural model, not mandated.
- **[SRC]** — verified this session against upstream source at the pinned refs: MicroPython
  `v1.29.0`, its lwIP submodule `77dcd25a72509eb83f72b033d219b1d40cd8eb95`, cyw43-driver
  `055d64274b014dd7b1c2fc94d26e8a18face7124`, micropython-lib `ee4bb8ff`. (No local checkout exists
  in this sandbox; files were fetched read-only into the scratchpad.)
- **[INFERENCE]** — my derivation from the above; needs a measurement or a decision before it is
  relied on.

---

## 1. The binding rules an MQTT service lands under (digest)

| # | Rule | Where | Kind |
|---|---|---|---|
| R1 | Memory ladder: design for zero `MemoryError` first; catch→degrade→restart→watchdog only as backstop; a caught-and-logged `MemoryError` is a design defect, never a pass | CLAUDE.md:342-404; SPEC I.4(a)-(d),(g) | [OWNER] (2026-09-26) |
| R2 | Two GC stages: whole suite at `gc.threshold(-1)` with zero `MemoryError` markers, then again at `32768`; threshold/`gc.collect()` never the fix | CLAUDE.md:351-404; SPEC I.4(e),(f) | [OWNER] (2026-09-26) |
| R3 | No `gc.collect()` anywhere except the two boot lists (generated setup batch, `start_and_check_tasks()`), mechanically enforced | SPEC I.4(f.1); `scripts/lint.sh`; `tests_scripts/test_gc_collect_sites.py` | [OWNER] (2026-09-18, boot exception) |
| R4 | Every memory gate matches `MemoryError` **or** `memory allocation failed`; injected test failures must avoid both wordings | CLAUDE.md:366-377; SPEC I.4(e); `tests_hardware/harness.py:37`, `tests_js/_memory_markers.js:5`, `scripts/test.sh:389-405`, `scripts/_digital_twin_ci_suite.py:248`; `tests_scripts/test_memory_error_gate_agreement.py` | [RULE] |
| R5 | Four-tier hazard coverage for every shared resource — explicitly incl. **sockets and the heap**, locks, FRAM, config file | CLAUDE.md:265-278; SPEC C.8 (lines 2313-2440) | [OWNER] (2026-09-03; extended 2026-09-26) |
| R6 | Every L1/L2 test exercising real-hardware-facing behaviour needs an L3/L4 counterpart or an E.6.6 exception row | SPEC E.6.6; `tests_scripts/test_level_containment.py` | [OWNER] (2026-09-26) |
| R7 | No avoidable wear (target flash/NVM and host SSD); config-persisting PUTs behind `persistence_write`; FRAM writes are not wear | CLAUDE.md:279-317 | [OWNER] (2026-09-17, 2026-09-26) |
| R8 | Real hardware only with the owner's go-ahead in the running conversation | CLAUDE.md:318-328 | [OWNER] (2026-09-25) |
| R9 | Read FRAM-persisted error logs before any `ResetErrors` | CLAUDE.md:405-431 | [OWNER] (2026-09-25/26) |
| R10 | Never block the loop (D.5, F.3); long-blocking work must not stall timing-sensitive work | CLAUDE.md:236-238; SPEC D.5, F.3 | [RULE] |
| R11 | A routine, repeatable failure is handled in place, never by ending the task (restart budget ≈ 3 restarts before reboot) | SPEC C.7.2 (2132-2170), C.4.1 (1790-1795) | [OWNER] (2026-09-24) |
| R12 | Sentinel-returning retry loops need their own capped exponential backoff | SPEC C.9 (2560-2568) | [RULE] |
| R13 | Hangs never allowed: per-file timeout+retry, `stdbuf`, `needs:` sequencing kept | CLAUDE.md:658-670; SPEC E.3.1 | [OWNER] (2026-09-26) |
| R14 | No real `select.poll()` behind a fake stream (hangs on GitHub runners); bounded fakes only | CLAUDE.md:671-682; SPEC F.7 row 12, F.9 | [RULE] |
| R15 | Never nest `asyncio.run()` (segfaults the Unix port) | CLAUDE.md:708-722; SPEC F.1 | [RULE] |
| R16 | Two suites binding real ports never at the same time; each test file claims its own port base below 32768 | CLAUDE.md:778-791; SPEC E.1 | [RULE] |
| R17 | A third party's outage must never read as a red test | CLAUDE.md:645-657 | [OWNER] (2026-09-26, "don't simplify the retry away") |
| R18 | Driver/DUT process separation: anything that can run outside the twin process must | SPEC E.9 | [OWNER] (2026-09-25) |
| R19 | Any new module joins the digital twin once it can form a complete chain | SPEC A.10 | [OWNER] (2026-08-20) |
| R20 | Tuned values carry `@tunable` + Part N row in the same change | CLAUDE.md:792-793 | [OWNER] (2026-09-25) |
| R21 | Every external dependency refreshed as one step; pins stay pinned | CLAUDE.md:52-61 | [OWNER] (2026-09-30) |
| R22 | `socket.getaddrinfo()` only ever on a numeric host (cannot be timeout-wrapped) | SPEC F.2, F.9 row "getaddrinfo() only on a numeric host" | [RULE] |
| R23 | No `setsockopt(TCP_NODELAY)`; lifting it is the owner's call | SPEC F.9 | [OWNER] (2026-09-30) |
| R24 | Boot latency is not a metric; boot setup must not starve the WDT | CLAUDE.md:239-246; SPEC A.7 (unfed stretches) | [OWNER] (2026-09-16) |

---

## 2. Sockets, ports and the lwIP PCB budget

### 2.1 The lwIP ensemble as built

`toolchain/versions.toml:41-59` (`[lwip]`), injected through a generated `lwipopts.h`
(SPEC B.14.2, `toolchain/micropython_overrides.py`):

| option | value | role |
|---|---|---|
| `MEMP_NUM_TCP_PCB` | **9** | every non-listening TCP pcb (active, connecting, closing, TIME_WAIT) |
| `MEMP_NUM_TCP_PCB_LISTEN` | 8 | listening pcbs |
| `MEMP_NUM_UDP_PCB` | **5** | = MicroPython's own default `4 + LWIP_MDNS_RESPONDER` (`extmod/lwip-include/lwipopts_common.h:60,70`) [SRC] |
| `MEMP_NUM_TCP_SEG` | 48 | global segment pool |
| `MEM_SIZE` | 12,000 | the arena every outbound TCP byte is copied into (`modlwip.c:802` `TCP_WRITE_FLAG_COPY`) |
| `TCP_MSS`/`TCP_WND`/`TCP_SND_BUF` | 800 / 6,400 / 6,400 | per connection |
| `PBUF_POOL_SIZE` | 16 (~892 B GC-heap-equivalent each) | inbound pbufs, shared by all sockets |

**The sizing rule is the ensemble for N admitted connections** (`micropython_overrides.py:176-185,
259-280`; `buildgen/validate.py:219-265`), [RULE] with owner-decided `max_connections = 6`
(SPEC H.7, owner 2026-09-24, `db3bf52`):

- `MEMP_NUM_TCP_PCB >= max_connections + SPARE_TCP_PCBS(3)` — the 3 spares exist because "a closed
  connection's FIN_WAIT pcb outlives its slot (`tcp_alloc()` never reclaims one at equal priority;
  modlwip aborts it after 10 s), as do arrivals not yet accepted or refused. **The pattern every
  limit ever measured on silicon ran at**" (`micropython_overrides.py:180-185`; H.7: "nothing
  leaner has been measured").
- `MEMP_NUM_TCP_SEG >= max_connections × (TCP_SND_BUF / TCP_MSS)` = 6 × 8 = 48.
- `MEM_SIZE / max_connections >= 2,000 B` (`MEM_SIZE_BYTES_PER_CONNECTION_FLOOR`, Part N
  `lwip.mem_size_per_connection_floor`).
- Measured cost: **2,324 B of GC heap per connection** in the coherent ensemble (B.14.2 table:
  6 → GC heap 192,488 B; 7 → 190,164 B).

All six devices (`devices/{wozi,dev,arzi,klkizi,grkizi,schlafzi}.toml:12-15`) set
`max_connections = 6`, `backlog` omitted → derived 7 (`asy_webserver_service.py:380`).

### 2.2 Current socket inventory (identical on all six devices)

The networking core (WiFi, NTP, DNS client, captive DNS, webserver) is fixed infrastructure built
once per device by the generated module (SPEC C.14, A.7 steps 6-7, 14), so the inventory does not
vary per device; `dev`'s two UART links use no sockets.

**TCP listen pool (8):**
| consumer | count | source |
|---|---|---|
| webserver port 80 | 1, permanent | `asy_webserver_service.py:702-706` → `stream.py:181-189` (`socket()` takes a TCP pcb at `modlwip.c:971`, `listen()` converts it) [SRC] |
| anything else in `src/` | 0 | — |

**TCP active pool (9):**
| consumer | count | source |
|---|---|---|
| admitted HTTP connections | ≤ 6 (`_DEFAULT_MAX_CONNECTIONS`, `asy_webserver_service.py:129`; reject-when-full `:664-670`) | H.7 |
| queued over-ceiling arrival | ≤ 1 (backlog = 7) | H.7 |
| closing connections (FIN_WAIT_1/2 not reclaimable; TIME_WAIT/LAST_ACK/CLOSING reclaimable) | the rest | H.7; lwIP `tcp.c:1837-1880` [SRC] |
| any outbound/client TCP | **0 — there is no TCP client anywhere in `src/` today** | grep of `src/` |

Designed occupancy at a full ceiling: **9 of 9**. At rest: 0 of 9.

**UDP pool (5):**
| consumer | count / lifetime | source |
|---|---|---|
| mDNS responder | 1, permanent from boot | `ports/rp2/main.c:175` → lwIP `mdns.c:2820` [SRC] |
| DHCP client | 1 while the STA netif is up | `cyw43_lwip.c:226` → `dhcp.c:279`; freed at `cyw43_lwip.c:253` [SRC] |
| DHCP server | 1 while the AP netif is up | `cyw43_lwip.c:238` → `shared/netutils/dhcpserver.c:94`; freed `cyw43_lwip.c:257` [SRC] |
| lwIP's own DNS | 0 — allocated per lookup only for `getaddrinfo(<hostname>)`, freed after (`dns.c:332-334, 1008-1012`; `opt.h:1189`) [SRC]; `src/` never does this (F.2) | |
| captive DNS listener (`UDPSocket` bound `0.0.0.0:53`) | 1, hotspot mode only | `asy_captive_dns.py:73`; task row in SPEC C.9 |
| NTP fetch (`UDPSocket` client) | 1 transient | `asy_ntp_client.py:187-202` |
| DNS client (`UDPSocket` per server attempt) | 1 transient, sequential | `asy_dns_client.py:115-122` |

NTP's DNS lookup and fetch run sequentially inside one `_sync_loop()` turn holding
`wifi_mode_lock` (`asy_ntp_client.py:360-366`), so they never overlap each other.

- **STA peak: 3 of 5** (mDNS + DHCP client + one NTP/DNS transient).
- **AP peak: 3 of 5** (mDNS + DHCP server + captive DNS). [INFERENCE] whether the STA netif's DHCP
  client pcb is released during hotspot mode was not traced through `asy_wifi_service.py`'s mode
  switch; it does not change the conclusion (≤ 4 of 5).

### 2.3 What one permanent outbound TCP connection requires

**Headroom today: zero under the documented rule.** The 3 spare PCBs are not free capacity — they
are the documented reserve for closing and queued HTTP connections, and the only configuration ever
measured on silicon ([RULE] H.7; `micropython_overrides.py:180-185`). A permanent MQTT pcb leaves
the webserver with 2 spares at a full ceiling.

[INFERENCE] The conservative, rule-preserving change is to count the outbound connection inside the
ensemble — **N = max_connections + outbound = 7**:

| option | now | with one outbound connection |
|---|---|---|
| `MEMP_NUM_TCP_PCB` | 9 | **10** (N + 3) |
| `MEMP_NUM_TCP_SEG` | 48 | **56** (N × 8) |
| `MEM_SIZE` | 12,000 | **14,000** (N × 2,000) |
| GC heap (B.14.2 measured row) | 192,488 B | 190,164 B (**−2,324 B**) |

This needs code, not only numbers: `check_lwip_ensemble(macros, max_connections)` and
`buildgen/validate.py:_lwip_ensemble_problems()` know only *admitted inbound* connections. An
outbound count has to become an input (e.g. derived from whether a device wires the MQTT service),
with `tests_scripts/test_micropython_overrides.py`'s `TestLwipEnsemble` and
`test_buildgen_validate.py` extended; `toolchain/versions.toml` change ⇒ BACKLOG build-environment
entry and the owner's chroot run (CLAUDE.md:1102-1106, "Build-environment verification"); the
`[lwip]` rows are Part N tunables (R20). The alternative — run MQTT inside the existing spares —
is a departure from the measured configuration and is a decision for the owner, not a default.

Note: raising the PCB count alone is "not a supported configuration" (B.14.2): `MEM_SIZE` must
move with it because **every outbound byte, MQTT publishes included, is copied into `MEM_SIZE`**,
and when that arena is empty `lwip_tcp_send()` retries `tcp_write()` 200 × 50 ms — **blocking the
whole VM for up to 10 s even on a non-blocking socket** (`modlwip.c:795-812`) [SRC]. 10 s exceeds
the RP2040 watchdog's 8,388 ms hard cap (SPEC F.1, `wdt.timeout_ms` 8000) — i.e. an exhausted arena
during a publish is a watchdog reset, not a slow write. B.14.2 records it as "never observed on
silicon", but it was never observed with an MQTT publisher competing either.

### 2.4 Reconnect churn — PCB lifetimes on lwIP [SRC]

| state of the *previous* connection | how long it holds a pcb | reclaimable by `tcp_alloc()`? |
|---|---|---|
| `SYN_SENT` (connect in progress, broker black-holed) | RTO stays at 3 s in SYN_SENT (`tcp.c:1288-1294`, `LWIP_TCP_RTO_TIME` 3000 `opt.h:1375`); aborted after `TCP_SYNMAXRTX` = 6 (`tcp.c:1232-1234`, `opt.h:1313`) → **≈ 18-21 s**; an explicit `close()` frees it **immediately** (`tcp.c:397-401`) | no (equal priority) |
| `ESTABLISHED`, half-open (peer gone, unacked data) | until `TCP_MAXRTX` = 12 retransmissions with backoff (`opt.h:1306`) — minutes | no |
| `FIN_WAIT_1/2` after the device closes | bounded by modlwip's close-poll abort: **10 s** (`modlwip.c:62-64, 1586-1590, 1684-1694`), FIN_WAIT_2 also by `TCP_FIN_WAIT_TIMEOUT` 20 s (`tcp_priv.h:128`) | **no** |
| `TIME_WAIT` | 2 × `TCP_MSL` = **120 s** (`tcp_priv.h:134`) | **yes, oldest first** (`tcp.c:1849-1851`) |
| `LAST_ACK` / `CLOSING` (broker closed first) | short | yes (`tcp.c:1855-1865`) |

Consequences [INFERENCE, each grounded above]:

1. **The client must own its socket and close it on every exit path** (D.3 "no resource acquisition
   without a guaranteed release on every exit path"). `asyncio.open_connection()` creates the socket
   as a generator local (`stream.py:99-121`); cancelling it under `wait_for` (the only way to bound
   it) abandons the socket, which is then closed only by its GC finaliser (`modlwip.c:946, 1719`) —
   at `gc.threshold(-1)` that is "whenever an allocation next fails". On rp2 lwIP still frees a
   leaked `SYN_SENT` pcb after ~18-21 s, so a reconnect cadence faster than that can stack
   `SYN_SENT` pcbs in the pool the webserver depends on. Precedent for "own the socket, close in
   finally": `asy_udp_socket.py:74-125` (`_connect()`/`_disconnect_locked()`), webserver
   `_serve()`'s `finally` (`asy_webserver_service.py:696-700`).
2. **Reconnect backoff floor ≥ 10 s** (`MICROPY_PY_LWIP_TCP_CLOSE_TIMEOUT_MS`) keeps the closing
   pcb of the previous connection (non-reclaimable FIN_WAIT) from overlapping the next one → steady
   requirement stays **1 pcb**, worst case 2 for ≤ 10 s. Capped exponential backoff is mandatory
   anyway (R12), and the backoff state must never end the task (R11; NTP precedent
   `asy_ntp_client.py:360-371`, `_reset_backoff()` `:300-302`).
3. **Prefer the TIME_WAIT side** (device sends DISCONNECT and closes → TIME_WAIT, which lwIP
   reclaims under pressure) over leaving pcbs in FIN_WAIT; both are bounded.
4. **Connect timeout must be explicit**: on rp2 a black-holed broker fails in ~18-21 s at lwIP level;
   on the Unix port (host kernel) the same black hole takes ~2 min. Tests must never depend on the
   transport's own connect timeout — bound it with `asyncio.wait_for_ms()` (F.2 "one timeout
   mechanism", agent 2026-09-29).
5. Ephemeral local ports: `TCP_LOCAL_PORT_RANGE_START/END` 0xc000-0xffff (`tcp.c:124-125`) — not a
   constraint at a ≥10 s reconnect cadence.

### 2.5 Other socket-path hazards specific to an outbound client [SRC unless noted]

- **`getaddrinfo()` blocks** and cannot be timeout-wrapped (R22). `asyncio.open_connection()` calls
  it unconditionally ("TODO this is blocking!", `stream.py:103`); umqtt.simple calls it in
  `connect()` (`umqtt/simple.py:80`). The broker hostname must be resolved through
  `asy_dns_client.resolve_ipv4()` (non-blocking, returns a literal unchanged,
  `asy_dns_client.py:99-131`) and only the numeric IP handed to the socket layer — the NTP client is
  the exact precedent (`asy_ntp_client.py:304-310`).
- **No TCP keepalive exists**: `LWIP_TCP_KEEPALIVE` 0 (`opt.h:2078`), and modlwip exposes only
  `SO_REUSEADDR` and `TCP_NODELAY` (`modlwip.c:1933, 1941`). MQTT's own PINGREQ/PINGRESP with a
  response deadline is the **only** liveness detector for a half-open broker connection — critical
  because the CYW43 `isconnected()` false positive is an accepted, unfixed condition (CLAUDE.md:220;
  SPEC F.2).
- **netif events**: an IP change or netif removal aborts every pcb bound to the old address
  (`tcp.c:2309-2330`, `netif.c:462`); a mere link-down does not. So a WiFi drop may or may not kill
  the MQTT socket on silicon — the client must handle both (immediate `OSError`, or silent
  half-open detected by the ping deadline).
- **Never write after a read has raised** (`OSError`): after `ECONNRESET`, modlwip has freed the
  pcb but the socket state still passes the write path's check; a write then goes through a NULL
  pcb — unmuted `OSError(EIO)` or a spin until timeout (SPEC H.7.1; agent 2026-09-29). The webserver
  carries the guard (`_TimeoutStreamProxy._peer_gone`, `asy_webserver_service.py:256, 274-278,
  286-288`); it is a F.9 standing workaround. An MQTT client needs the same "peer gone ⇒ no DISCONNECT,
  no PINGREQ, just close" rule.
- **No `TCP_NODELAY`** (R23). Nagle is on (`modlwip.c:814-818`); small MQTT packets may coalesce —
  latency, not correctness.
- **Non-blocking send semantics**: with `timeout == 0`, `tcp_sndbuf() == 0` returns `EAGAIN`
  (`modlwip.c:763-767`); asyncio's `Stream.write()` then appends to `out_buf` (`stream.py:66-74`, an
  allocation) and `drain()` waits on `queue_write`.
- **Idle listener cost**: a subscriber waits for traffic that may not arrive for hours. A poll loop
  in the `UDPSocket.ready()` style (`ipoll(0)` + `sleep_ms(20)`, `asy_udp_socket.py:127-136, 145`)
  would be a permanent CPU cost (SPEC F.5.9, measured on the UART: 20.6× fewer rounds at an idle
  rate). Waiting through asyncio's own IO queue (`Stream.readinto()` → `queue_read`) costs nothing
  while idle. [PRECEDENT/RULE]
- **Stack depth**: rp2's C stack is 8 KB less a 256 B margin vs 80,000 B on the Unix rig
  (F.7 row 21) — keep the await nesting of the read path shallow; a depth that passes L1/L2 can raise
  `RuntimeError` on the board.
- **wifi_mode_lock coordination**: NTP holds `WifiService.wifi_mode_lock` across its whole network
  attempt and checks `network_available_locked()` first (`asy_ntp_client.py:312-320, 364-365`); the
  lock table (SPEC C.8, `<!-- locks:begin -->`) lists exactly what it may be held while taking. An MQTT
  connect that takes this lock becomes a lock-table row (checked by `tests_scripts/test_lock_order.py`),
  and inherits the known priority inversion with the 60 s STA-retry branch (C.8 "Known inconsistency").
  Holding it for a connect is a design choice; holding it across the whole session would block WiFi
  mode switches and must not happen [INFERENCE].
- **TLS is not compatible with the current memory model** [SRC + INFERENCE]: rp2's mbedtls takes
  `MBEDTLS_SSL_IN_CONTENT_LEN` 16,384 B + `OUT` 4,096 B per connection from the **GC heap**
  (`extmod/mbedtls/mbedtls_config_common.h:63-65, 121-124`, `m_tracked_calloc`), allocated at each
  handshake — a ≥16 KB contiguous run at every (re)connect, against a largest free run of ~1.5 KB at
  serving peak (H.7). A PoC on plain TCP 1883 is the only option that fits; TLS would be its own design
  question.

### 2.6 Inbound buffering — the shared pbuf pool

Received TCP data sits in lwIP pbufs from `PBUF_POOL` (16 × ~876-892 B, not the GC heap at
runtime, but sized by the GC-heap budget) until the application reads it. The pool was sized for
"one small request per connection" inbound (B.14.2: `PBUF_POOL_SIZE` stays at default, agent
2026-09-22, `31da2b3`), and each connection advertises `TCP_WND` 6,400 B. [INFERENCE] A broker burst
(retained messages on subscribe, a large payload) that the client does not drain promptly can hold
up to ~8 of the 16 pool pbufs that HTTP requests also need. Requirements: drain the socket
continuously, cap the accepted packet size, and discard oversize packets in chunks (§3.4).

### 2.7 Ports

- Device side: outbound only; ephemeral local ports. No new listening port, so the
  `MEMP_NUM_TCP_PCB_LISTEN` pool and the webserver's port are untouched.
- Test side (R16, SPEC E.1): every file that binds claims a module-level `PORT`/`_PORT*` base below
  32768 and outside every neighbour's band. Claimed today: TCP 17400 (+64 scan,
  `digital_twin/unix_port_poll_prewarm.py:24-25`), 18080 (twin CI), 18099-18103, 19100, 19300,
  19400, 19420/19421 (cross-browser), 19481/19482 (JS live twins), 19500-19559 (construction),
  19700-20899 (webserver concurrency, `19700 + 200·i`); UDP 21000-27000 (seven files). **28000-31999
  is unclaimed** (grep, this session). The Unix port has no `getsockname()`, so a MicroPython-side
  fake broker cannot bind port 0 and read it back — it needs a claimed base plus a scan window
  (`unix_port_poll_prewarm._bind_free_listener()` precedent). Host-side (CPython) brokers can use
  `_free_port()`-style ephemeral binding (`tests_scripts`).
- Bench: broker port 1883 on the bench host; the DUT reaches the host over `br0`.

---

## 3. Memory / heap requirements

### 3.1 The numbers the service has to live inside

| figure | value | source |
|---|---|---|
| GC heap, shipped 6-connection ensemble | 192,488 B (linker heap of the shipped image 192,360 B) | B.14.2 table; archive §7R.1 |
| `mem_info` total | ≈ 2.3 % below the linker heap (GC tables) | HEAP_FRAGMENTATION_MEASUREMENTS.md §M6.2 |
| after a real `build_system()` at rest (1.29, 2026-09-11) | 130,224 B free, 115,536 B largest block | SPEC F.5.3 — **predates the 6-connection ensemble** (−5,040 B), so today's figure is lower [INFERENCE] |
| flash-tier assertions after `build_system()` | ≤ 100,000 B allocated; nothing newly placed in, and ≥ 16,384 B free above, the top survivor; a ≥ 32,768 B run | `tests_hardware/flash/test_memory_stress.py:46`; §M2.5 |
| serving peak at `max_connections = 6`, `gc.threshold(-1)` | **~21 % free, largest free block ~1.5 KB (five 256 B pieces)**, 0 true failures of 2,255 | H.7 table |
| at 7 HTTP connections | ~14 % free, largest 528 B | H.7 table |
| per open HTTP connection at peak | ~7.5-8 KB live heap | H.7 (archive §7R.4) |
| reliably placeable piece under load | 256 B (`chunk_bytes`); 1,024 B pieces failed at ~870 B | I.3 "Why 256" |
| loaded floor (1.28, limit 4) | `mem_free` 91,312 B at 32768 vs 128 B at -1 | I.5 |
| worst reachable single allocation the gates are derived from | 2,048 B (request body cap) | §M2.5 step 1; I.6 |

"No free-heap target is published"; the 20-30 % free at peak H.7 relies on is general embedded
practice (I.1). [INFERENCE] MQTT costs 2,324 B static (§2.3) plus its own buffers plus connection
objects; against ~39-40 KB free at the measured peak (21 % of ~188 KB) it plausibly moves the peak
below 20 % — **this must be re-measured on silicon at the full ceiling with MQTT active**, using the
existing instruments (`bench/test_heap_under_connection_ceiling.py`,
`bench/test_serving_heap_at_default_gc.py`, `device_scripts/heap_under_connection_ceiling.py`).

### 3.2 The ladder applied to an MQTT client (R1-R3)

- (a) **Zero `MemoryError` by construction** under worst-case load (webserver at its full ceiling,
  NTP syncing, FRAM writes, broker bursts). A caught one is a defect.
- (b) **Degrade**: every API returns a documented sentinel; a failed buffer allocation leaves a
  `None` buffer and the service reports "unavailable" (G.2 `LockableBuffer` rule: "a failed
  allocation degrades to a `None` buffer, never an exception").
- (c)/(d) Supervisor restart then watchdog — but by R11 an unreachable/misbehaving broker is a
  *routine* failure: handled in place with backoff, **never** a task end (a restart costs 100 of the
  300 budget, ≈ 3 restarts before a self-reboot; C.4.1). An MQTT task ending on every broker outage
  would reboot the device every few minutes — exactly the NTP failure mode C.7.2 records (owner,
  2026-09-24).
- (e)/(f) Both GC stages, automatically: `scripts/test.sh` (-1) and `GC_THRESHOLD=32768
  scripts/test.sh` (`tests/_threshold_runner.py`), CI jobs `unit-tests` and
  `unit-tests-gc-threshold` (`ci.yml:440-497`); the twin suite runs its whole sequence at both
  (`scripts/_digital_twin_ci_suite.py`, `digital_twin/README.md:430-441`); L3/L4 via the two-image
  release proof (SPEC E.6.1, owner 2026-09-26).
- (g) Fix pressure by design (chunk, preallocate/reuse, stream), never with `gc.collect()` /
  `gc.threshold()` — `gc.collect()` outside the two boot lists fails `scripts/lint.sh` and
  `tests_scripts/test_gc_collect_sites.py`.
- **Don't blanket-wrap asyncio primitives in `try/except MemoryError`** — only where a real
  graceful-degradation alternative exists (CLAUDE.md:227-235; SPEC F.2; owner 2026-09-25).

### 3.3 Where the long-lived buffers must be allocated

The placement law (§M1): a long-lived multi-block object lands inside the heap's large free run iff
no lower hole fits at that instant, splitting it; one-block objects always find a hole. Allowed
birthplaces, in order of precedent:

1. **`__init__` (construction phase)** — SPEC C.13: "`__init__` only stashes args and sets a readiness
   gate"; I.1: "long-lived state in `__init__`, churn-prone I/O in `setup()`" and the official
   "instantiate large permanent buffers early" (`docs/reference/constrained.rst:359-361`). Construction
   runs before the setup batch and allocates only (A.7 step list; unfed stretch 1). [PRECEDENT:
   `asy_fram_driver.py` scratch buffers, `asy_sgp40_driver.py`'s `_measure_command`, `LockableBuffer`]
2. **`setup()`** — a unit of the one-time setup list, between the boot-confined `gc.collect()`
   placement resets (`buildgen/codegen.py:466-478`). [PRECEDENT: the UART RX DMA ring "allocated once
   in the link's `setup()` (a unit of the one-time setup list, I.4(f.1))", SPEC J.8.] A FRAM-backed
   logger's store setup goes **first** in `setup()` (I.2 owner decision 2026-09-21).
3. **Never in the run phase** for anything multi-block: connect, reconnect, per-message. Connection
   objects are unavoidably created at (re)connect — the `lwip_socket_obj_t` (with finaliser), asyncio
   `Stream` (3 attrs), the IO-queue entry — keep them few and small, and count them per reconnect.

Not a free lunch: survivors added at boot consume the holes the rest of the boot needs (§M7:
"hoisting … consumes the holes the rest need at the real dose"), so the boot gates must still pass —
`tests_scripts/test_digital_twin_boot_contiguity.py` (twin, all six devices, suppressed control
arm) and `tests_hardware/flash/test_memory_stress.py::test_real_gc_heap_headroom_survives_a_full_system_build`
(silicon thresholds above). If the service is wired on `wozi`/`dev` only, only those devices' figures move.

Shape: G.2's buffer-ownership primitive — **one contiguous allocation per logical record, sized once
from configuration, `memoryview` regions handed out, paired `write()/write_into()` and
`read()/read_into()` APIs, failed allocation → `None`**. J.8 is the closest existing analogue of a
byte-stream protocol client and states the rule outright: "Preallocate …, never grow"; "A failed
allocation degrades to the module's normal failure sentinel … never an exception".

### 3.4 Buffer sizing and the read/write path [SRC for the API facts]

- **Read only with `readinto()` into the preallocated buffer.** `stream.readinto()` allocates nothing
  (`py/stream.c:310`; asyncio `Stream.readinto()` is one `queue_read` + one `readinto`,
  `stream.py:37-39`).
  - Never `read(n)` — allocates `n` up front (`py/stream.c:220`, `vstr_init_len`).
  - Never `recv(n)`/`recvfrom(n)` — allocates `n` up front (`modlwip.c:1316-1349`, `:1324`).
  - Never `Stream.readexactly()`/`read(-1)`/`readline()` — `r += r2` re-concatenation per partial
    read (`stream.py:34, 50`); F.9 lists the twin client's avoidance of exactly this as a standing
    workaround, and its unbounded growth was a real CI `MemoryError` (digital_twin/README.md:736-771).
  - Note the existing precedent **not** to copy for a large *n*: the captive DNS reads with
    `recvfrom(4096)` (`asy_captive_dns.py:103`), which on rp2 allocates 4,096 B per datagram before
    shrinking; NTP uses 1,024 (`asy_ntp_client.py:198`), DNS 512 (`asy_dns_client.py:21`).
- **Remaining-length decode**: MQTT's varint (≤ 4 bytes, max 268,435,455) must be decoded from the
  fixed buffer and checked against the buffer before reading; an over-length packet is consumed in
  chunk-size `readinto()` passes and discarded (or the connection dropped) — **never allocate
  `remaining_length`**. MQTT 3.1.1 has no maximum-packet-size negotiation, so this is the only defence.
- **RX/TX buffer size** is a configuration constant with a Part N row (R20). The ~1.5 KB largest run at
  peak only matters for *run-phase* allocations; buffers born at boot can be larger, but their size
  enters the boot survivor budget above. [INFERENCE] A few hundred bytes each keeps the PoC well inside
  every gate; anything near or above the 2,048 B worst-reachable allocation changes §M2.5's derivation.
- **Outbound size bound**: a publish must stay well under the per-connection `MEM_SIZE` share
  (2,000 B) so the 10 s blocking `tcp_write` loop (§2.3) is unreachable; `TCP_SND_BUF` 6,400 caps
  in-flight bytes per connection.
- **Writes**: `Stream.write()` appends to `out_buf` when the immediate write is partial
  (`stream.py:66-74`) and `drain()` builds `memoryview` slices (`:77-90`); a direct non-blocking
  `sock.write(memoryview(buf)[off:])` loop with `queue_write` waits is the non-allocating shape
  [INFERENCE]. Either way, assert a **per-message allocation rate** (E.8), not an absolute delta.
- **Timeout wrappers allocate**: each `asyncio.wait_for()` creates a wrapper; F.1 measured +53 %
  overhead from wrapping many small writes. Bound the waits that can genuinely hang (connect,
  CONNACK, PINGRESP deadline, a write blocked on `queue_write`) rather than every byte.
- **Topic handling**: match incoming topics as bytes in the RX buffer against preallocated
  subscription bytes; decoding to `str` per message is a per-message allocation. [INFERENCE] —
  `memoryview`-vs-`bytes` equality semantics must be verified on the pinned interpreter first
  (CLAUDE.md:29 "always check current MicroPython docs").
- **Config strings** (if REST-configurable: broker host, client id, topic, credentials): bound each at
  ≤ 253 characters. I.3: "the ceiling is the longest string any schema permits, … `NTPHost`'s 253
  characters … giving a ~255 B piece on `/networking`, inside the cap" — a longer string becomes one
  over-cap `_PieceWriter` fragment on a GET route. And `tests_scripts/test_request_body_cap_headroom.py`
  pins every device's maximum PUT body per route (I.6: `/networking` 536 B today), so new fields fail it
  deliberately until the pins are re-derived; the 2,048 B cap itself has ample room.
- **Ints**: rp2 small ints are 31-bit (F.7 row 7); packet ids 1..65535 and remaining lengths stay
  small ints; tick arithmetic only via `ticks_diff()/ticks_add()` (`tests_scripts/test_ticks_wrap_scan.py`;
  `tests/_ticks30.py` 2**30-period fake for keepalive deadlines).
- **Counters** (publish/receive/failure counts) via `LockedCounter`, saturating at `COUNTER_CAP`
  (G.2; `tests_scripts/test_counter_steps.py`).

### 3.5 What counts as a hotspot (I.2/I.4)

"Any new function/module that holds, builds, or grows an allocation whose size isn't a small,
provably-fixed constant" (CLAUDE.md:342-346; I.4 "Applying this scheme to new code": run it through
(a)-(d) at design time and give it its own (e)/(f)-shaped test pair). For MQTT that is: the RX path
(remaining length is attacker/broker-controlled), any per-message object (topic `str`, payload
`bytes`, callback argument), the reconnect path (socket/Stream/IO-queue entry per reconnect), any
list of subscriptions or queued publishes (must be fixed-capacity), and any status/diagnostic dict
the service exposes over REST (stream it if it can grow, I.3/G.2 `_stream_dict_response()`).

### 3.6 The gates that will judge it

- Unit tier: `scripts/test.sh:389-405` greps each file's log for `MemoryError|memory allocation
  failed`, on passing files too; an unreadable log is "no verdict" = fail.
- Twin: `scripts/_digital_twin_ci_suite.py` `_close_log_and_check_memory_safety()` on every
  subprocess, both thresholds; Run 11 memory-trend soak with noise-derived tolerance (E.9).
- `tests_scripts` twin boots: `test_digital_twin_generated_boot.py`,
  `test_digital_twin_boot_contiguity.py`.
- Hardware: `tests_hardware/flash/test_memory_stress.py`, `bench/test_memory_stress_bench.py`
  (via `harness.MEMORY_ERROR_MARKERS`), plus SYSTEM's persisted `TASK_RAISED` read around each window
  because at DebugLevel 0 the console shows nothing (I.4(e)).
- JS live twins/cross-browser smoke: `tests_js/_memory_markers.js` (if the website ever shows MQTT state).
- Agreement guard: `tests_scripts/test_memory_error_gate_agreement.py` (also walks `tests/` and
  `digital_twin/` with `ast` for injected messages borrowing the interpreter's wording — use
  "simulated allocation failure").
- PC tiers print every unretrieved task exception at every level
  (`digital_twin/unix_port_unretrieved_report.py`, installed by `tests/microtest.py:24`).

### 3.7 Measurement discipline if MQTT memory is measured (HEAP_FRAGMENTATION_MEASUREMENTS.md)

Price bytes on the flag-free `build-standard` binary, never under `--coverage`'s `build-settrace`
(4-5× inflation, §M3.7, E.5.2); 64-bit Unix-port byte figures do not transfer to the board (§M4.1,
F.7 row 7) — counts and same-binary ratios do; every heap-measuring device script sets and prints its
own `GC_THRESHOLD=` (§M3.8, `tests_scripts/test_device_script_gc_threshold.py`); measure at a proven
peak with `mem_info(1)` parsed by `tests_hardware/heap_map.py` (E.8); one process per scenario
(§M3.6); a leak is a rate (E.8: `tests/test_uart_comm_hazard.py`'s `< 6.0 B/transaction` is the
precedent); throttle any twin used for serving limits (E.8). The 32-bit frozen twin is an ad-hoc
instrument, never committed (owner, 2026-09-23/29).

---

## 4. Test plan skeleton per tier

### 4.0 What every new `src/` module must pass before any MQTT behaviour is tested (L0 gates)

From `tests_scripts/` (all run in the backgrounded pytest tier of `scripts/test.sh`):

| gate | what it demands of the MQTT service |
|---|---|
| `test_task_inventory.py` | every `create_task(`/`start_server(` is in a starter (`get_task_starters()`) or a row of SPEC C.9's task table |
| `test_lock_order.py` | every lock (e.g. a connect lock, `wifi_mode_lock` use) is a row of C.8's lock table, taken in level order |
| `test_readiness_gates.py` | `self.initialized` False in `__init__`, True in `setup()`; teardown returns `bool` |
| `test_error_catalog.py`, `test_fault_or_warning_never_both.py` | errno/wrnno from `buildgen/error_catalog.json`, passed by keyword through named constants |
| `test_code_conventions.py`, `test_comment_block_cap.py`, `test_import_graph.py`, `test_import_placement.py` | `asy_` naming, `_NAME`, D.15 member order, 3-line comment cap, acyclic imports |
| `test_tunables_register.py` | every tuned value (keepalive, backoff, timeouts, buffer sizes, port) tagged `@tunable` with a Part N row |
| `test_counter_steps.py`, `test_ticks_wrap_scan.py` | bounded counters; tick math via `ticks_diff/ticks_add` |
| `test_exception_handler_contract.py`, `test_watchdog_feed_sites.py`, `test_gc_collect_sites.py` | no new handler install, no new feed site, no `gc.collect()` |
| `test_level_containment.py` | every new `tests/test_digital_twin_*` scenario named in an L3/L4 module's `COVERS_TWIN_SCENARIOS` or an E.6.6 row |
| `test_micropython_overrides.py` (`TestLwipEnsemble`), `test_buildgen_validate.py` | only if the lwIP ensemble/validator learns an outbound count (§2.3) |
| `test_buildgen_driver_registry.py`, `test_buildgen_generate.py`, `test_device_tomls.py`, `buildgen_fixtures/novel_combo.toml` | if wired through buildgen as an `[[instance]]` (K.6; `_OVERRIDES` precedent `buildgen/driver_registry.py:16-21`) — `test_device_tomls.py` pins which devices carry it |
| `test_request_body_cap_headroom.py`, `test_config_schemas.py`, `test_stored_config_golden.py` | only if it has a REST-configurable schema |
| `test_persistence_write_marker_completeness.py` | any hardware test that PUTs its config |

### 4.1 L1 — unit, MicroPython Unix port (`tests/test_asy_mqtt_*.py`)

Runner facts: one Unix-port process per file, `-X heapsize=16M` (never raised as a fix, E.3.1),
`TZ=UTC`, `MICROPYPATH=build/generated_src:src:tests:frozen_modules:.frozen`, 240 s per file × 3
attempts (a retried pass is a root-cause item), `TEST_PARALLELISM` concurrent files
(`scripts/test.sh:94, 375-450`); `microtest.run(globals())` ends with `sys.exit()` so parked tasks
cannot hang the process (`tests/microtest.py:15-58`).

**Fakes — what exists and what does not:**
- `tests/network.py` fakes `network.WLAN` state only (`raise_on` fault injection); there is **no
  socket fake** anywhere in `tests/`. Network-service tests use **real host loopback sockets**
  (UDP: `test_asy_udp_socket.py:85-115`, `test_asy_dns_client.py`, `test_asy_ntp_client.py`,
  `test_asy_captive_dns.py`; TCP: `_webserver_concurrency_scenarios.py` with
  `asyncio.open_connection()` and raw non-blocking `socket.socket()` clients, `:166, 233, 736-745`).
- The webserver's route/streaming tests drive `_serve()` through **pure-Python stream doubles**
  implementing the `_StreamLike` coroutine surface (`asy_webserver_service.py:53-67`;
  `tests/test_asy_webserver_service.py:246`) — these never touch asyncio's IO queue.
- `_StepPoller` (`tests/test_asy_uart_driver.py:130-143`) — the mandatory bounded double for any
  code that polls a stream itself.

**Rules imposed on MQTT tests by the known hang/segfault causes:**
1. **No fake socket may reach asyncio's IO queue.** asyncio's `Stream.read/readinto/readexactly/
   drain` and `open_connection` all `yield core._io_queue.queue_read/queue_write(self.s)`
   (`stream.py:28-90, 120`); with a non-fd Python object the Unix port's real poll watches fd 0 and
   never turns ready on GitHub runners (CLAUDE.md:671-682; F.7 row 12). Two acceptable shapes:
   (a) real loopback sockets (real fds), or (b) a transport seam *above* the IO queue — the client
   takes a factory returning a Stream-like object, and the L1 double implements `readinto/write/
   drain/wait_closed` as plain coroutines (the webserver's `_StreamLike` precedent). If the client
   polls itself, the double is a `_StepPoller`.
2. **No nested `asyncio.run()`** (CLAUDE.md:708-722): build the fake broker/client fixtures in the
   synchronous test body, then pass them into the one coroutine `run()` drives; never call a helper
   that does its own `asyncio.run()` from inside a coroutine. A segfault mid-file with no closing
   `P/T passed` line is this, not a memory bug.
3. **Cancel and await every server/client task in the test's own `finally`** — tasks share one
   process-wide queue and parked listeners keep allocating into the next test's measurement (E.8
   "cross-test contamination"); `globals()` order is not file order (F.1).
4. **Port base**: claim an unused base below 32768 (28000-31999 is free) as a module-level constant
   (E.1). Raw `bind()/connect()` need `socket.getaddrinfo(host, port)[0][-1]` on the Unix port
   (F.7 row 1); `open_connection()` does that internally.
5. **Poll-set prewarm**: any file that boots a `sensortask_<device>` module with real sockets calls
   `prewarm_poll_set()` at import, before anything registers a poll object
   (`digital_twin/unix_port_poll_prewarm.py`; the Unix-only `modselect.c` pollfds-growth segfault,
   digital_twin/README.md:899-944).
6. **Allocation failure**: only where a real `MemoryError` is unreachable, use the `_StarvedAlloc`
   shape — armed, one-shot, restoring the shadowed module global in `__exit__` (E.4,
   `tests/test_asy_uart_comm.py`); message wording clear of the gate words (R4).
7. **Short timings**: keepalive/backoff/connect timeouts are constructor/config parameters so L1 can
   use milliseconds; a real 60 s keepalive in L1 would blow the per-file budget. Use
   `tests/_ticks30.py` for deadline wrap. Every await in a test is bounded (`run_timed()` pattern,
   `_webserver_concurrency_scenarios.py:55-56`).

**L1 content (skeleton):**
- Codec (pure functions, D.12 bar): remaining-length varint at 0, 127, 128, 16,383, 16,384,
  2,097,151, 2,097,152, 268,435,455 and a malformed 5th continuation byte; UTF-8 length-prefixed
  strings at 0 and the configured maximum; every fixed-header flag combination; packet-id wrap
  (1..65535, never 0); CONNECT/CONNACK/SUBSCRIBE/SUBACK/PUBLISH(QoS 0/1)/PUBACK/PINGREQ/PINGRESP/
  DISCONNECT round trips against independently known byte strings (the spec's own examples), not
  self-referential encode→decode.
- Session state machine against a fake broker (in-process `asyncio.start_server` on loopback, or the
  stream double): CONNACK refusal codes; broker never answers CONNACK; broker closes mid-packet;
  broker dribbles one byte per write; oversize PUBLISH discarded without allocation; PINGRESP
  deadline expiry ⇒ close and reconnect; read raises `OSError` ⇒ **no further write** (H.7.1
  analogue); connect refused ⇒ backoff grows to its cap and resets on success; network-unavailable
  gate skips attempts without growing the backoff (NTP precedent `asy_ntp_client.py:366-370`);
  task never ends on any of these (C.7.2).
- Resource release: socket closed on every exit path incl. cancellation (count opens/closes through
  the factory seam); `disconnect()` idempotent and never raises (UDPSocket contract precedent).
- Memory: per-message and per-reconnect allocation **rates** (E.8) measured with
  `gc.mem_alloc()` deltas in collection-free windows (§M2.3), asserting against an injected-leak
  control so the bound bites; a revert-the-fix mutation must fail it (E.8 "guard is blind" trap).
- Readiness gates (`tests/test_readiness_gates.py` MicroPython half).
- **Hazards (R5), L1 shares:** (a) **sockets** — MQTT connected and publishing while
  `_webserver_concurrency_scenarios.py`-style full-ceiling bursts run: admission stays exactly
  `max_connections`, every admitted response complete, MQTT session uninterrupted (on the Unix port
  this proves asyncio-level coexistence only; PCB exhaustion is L4); (b) **heap** — GET-route hammer
  plus MQTT traffic, zero gate markers at both stages; (c) **locks** — connect vs
  `reconnect_wifi()`/hotspot switch if `wifi_mode_lock` is taken; (d) **UDP/DNS** — MQTT broker
  resolve concurrent with NTP's resolve; (e) **config file** — PUT vs read of the MQTT schema if any;
  (f) **FRAM** — its logger under `ResetErrors` (`tests/test_fram_integration.py` precedent).
  The bus-centric generated hazard machinery (`tests/test_bus_hazard_generated.py`,
  `_bus_hazard_catalog.py`) does not apply to sockets; socket/heap hazards have only the webserver's
  scenarios as precedent.

### 4.2 L2 — digital twin (`tests/test_digital_twin_*` + `scripts/run_digital_twin_ci.sh <device>`)

**What exists:** `digital_twin/network.py` fakes WLAN *state only*; "real traffic (NTP/DNS/HTTP)
goes through the real `socket` module straight to the host's actual network" (its docstring).
`_fault_injection.FaultInjector` is a bus/chip-level op queue (raise or blocking hang) — **there is
no TCP-client fault model and no network fault flag** in `run_generic_integration.py` other than
`--wifi-outcome` (`:131-160`). The CI suite (`scripts/_digital_twin_ci_suite.py`, stdlib-only `uv run`
CPython) spawns only the twin subprocess and drives it from threads; it runs no external server
process. Today the twin already reaches the real internet for NTP/DNS (`NTPHost` default
`pool.ntp.org`, fallback DNS `8.8.8.8`/`1.1.1.1`, `asy_dns_client.py:22`) — tolerated because an NTP
failure is harmless and asserted nowhere except Run 9's deliberately unreachable host.

**Chain completeness (R19)** therefore needs a broker in the twin's environment before the module
can join. Options [INFERENCE, each with its consequence]:
- **Host-side stdlib fake broker** inside the CI suite process (thread, like the suite's own
  `threading.Barrier` load at `scripts/_digital_twin_ci_suite.py:282-291`): no new dependency (R21),
  fully scriptable faults (RST, stall, half-open, garbage, oversize, slow drip, refused CONNACK),
  E.9-compliant (all driving and observing host-side). Risk: self-consistency — it shares the
  client author's reading of the spec (C.11.1's "fake drifts silently" problem).
- **Real mosquitto** for conformance: not installed anywhere (`which mosquitto` empty; not in
  `toolchain/versions.toml` `apt_packages`; `ci.yml` has no `services:`). Via apt it is unpinned
  (contrary to R21's "pins stay pinned", like the documented conda-forge Firefox exception, H.7) and
  touches `versions.toml` ⇒ chroot-verification BACKLOG entry; via a service container it must be
  digest-pinned and passes zizmor's default audits (`.github/zizmor.yml` configures only
  `unpinned-uses`).
- **Public broker**: violates R17 — a third party's outage would turn a test red.

**L2 runs to add (skeleton, both thresholds automatically):** broker reachable — connect, subscribe,
publish, receive round trip with the twin's webserver serving; broker black-holed (TEST-NET-1
`192.0.2.1` as Run 9 does for NTP) — webserver fully healthy past the connect timeout, MQTT backing
off, no task end; broker RST / stall / oversize / malformed — degrade and recover; reconnect storm
bounded by the backoff; Run 11-style soak with MQTT traffic and the memory-trend check; Run 11b full
ceiling with MQTT connected. Per-device construction/wiring scenarios
(`tests/_digital_twin_construction_scenarios.py`) and the boot-contiguity guard pick the module up
automatically once it is generated into a device module.

**What the twin cannot say (fidelity gaps):** no lwIP at all — PCB pool, `MEM_SIZE` arena,
`PBUF_POOL`, TIME_WAIT reclamation, modlwip's 10 s close abort, the 10 s `tcp_write` block and the
NULL-pcb write are all invisible (H.7 "cannot validate a PCB ceiling"); WLAN fake state changes do
not touch host sockets, so "WiFi drop kills the broker connection" needs an explicit twin-side
coupling or L4; host kernel connect timeout (~2 min) ≠ rp2 (~18-21 s); host socket buffers rarely
produce partial writes; 64-bit object sizes (F.7 row 7); the AP-mode `ifconfig()` fidelity gap
(digital_twin/README.md:123-125); an unthrottled twin is 50-100× faster than the board (E.8).

### 4.3 L3 — flash tier (`tests_hardware/flash/` + `device_scripts/`)

Real `dev` board over USB/`mpremote`, no WiFi bridge (E.6.1); requires the owner's go-ahead (R8);
`dev` is the only board (`dev-only-bench` row, E.6.6); FRAM error logs read before any reset (R9);
isolated-driver scripts overwrite production's first FRAM chunk (CLAUDE.md:405-431 caveat).
What L3 can own for MQTT:
- codec on silicon (31-bit small ints, `struct` native sizes, single-precision floats if any);
- the service constructed inside a real `build_system()` — extend
  `device_scripts/heap_headroom_after_full_system_build.py` / `test_memory_stress.py` thresholds
  (§3.1) and `device_scripts/allocation_need_per_source.py` (the need sieve, §M6.1) for the publish
  and receive paths;
- C-stack depth of the read path (F.7 row 21);
- every heap script sets/prints `GC_THRESHOLD=`; config writes `await flush_pending()`
  (`tests_hardware/README.md:408-430`).
Everything transport-related has no L3 home → an E.6.6 row (precedent rows `flash-only-bus-checks`,
`fram-write-protect-no-rest`).

### 4.4 L4 — bench tier (`tests_hardware/bench/`)

Real `dev` board on the bench Pi4's `br0` bridge (tests_hardware/README.md:115-178). Existing
primitives (`tests_hardware/bench_control.py`): `ap_down/ap_up` (:88-99), `kick_client`/
`kick_all_stations` (:101-116), `block_udp_ports`/`unblock_udp_ports` (:118-129),
`redirect_udp_port_to_local` + `RogueUdpResponder` (:131-140; `rogue_udp_responder.py`),
`inject_network_degradation` via `tc netem` (loss/delay/corrupt/duplicate/reorder, :169-207).
**All port-level faults are UDP-only**; a TCP equivalent (iptables `DROP` and
`REJECT --reject-with tcp-reset` on 1883, a DNAT redirect to a rogue TCP broker) does not exist.
Broker: none on the bench host today; options are a stdlib fake broker run host-side by the test
(no install) and/or mosquitto installed on the Pi4 (a bench-host setup change through
`setup_toolchain.py env --tier bench`; not a `br0` change, so the dead-man's-switch rule only applies
if bridge/network config is touched, CLAUDE.md:329-341).

L4 is the **only** tier that can prove the lwIP-level claims of §2:
- PCB pressure: hold the full webserver ceiling (`harness.discover_max_connections()`,
  `bench/test_heap_under_connection_ceiling.py`'s sustained-ceiling method, README "Holding a ceiling
  open") while MQTT reconnects repeatedly — no `OSError(ENOMEM)` from `socket()` (`modlwip.c:994-996`),
  exact admission still `max_connections`, every body complete (H.7 "service, not just survival").
- Heap at peak with MQTT active — the 20-30 % band and ≥ 256 B placeability (§3.1).
- Network resilience mirroring `bench/test_network_resilience.py`: AP down/up, station kick, netem
  loss/latency, broker kill/restart, TCP RST/blackhole on 1883, garbage broker — no task end
  (`assert_no_task_ended`), no new module error beyond the expected MQTT entries, MQTT recovers.
- Half-open detection: drop broker traffic silently (iptables DROP) and assert the ping deadline,
  not a TCP keepalive, closes and reconnects.
- Soak tiers (`long_soak`, `--soak-tier`), and `bench/test_memory_stress_bench.py` hammer with MQTT.
- A conformance probe in C.11.1's spirit: the same scripted exchange against the fake broker and
  against real mosquitto, diffed, so the fake cannot drift silently.
- Wear: any test that PUTs MQTT config spends a flash write → `persistence_write` unless it is a
  shared prerequisite (CLAUDE.md:279-317 "the write a test OWNS").
- Each L4 module lists the twin scenarios it covers in `COVERS_TWIN_SCENARIOS` (R6).

### 4.5 CI

Jobs that would run MQTT code (`.github/workflows/ci.yml`): `lint-and-typecheck` (ruff over
`src tests digital_twin tests_hardware buildgen scripts toolchain tests_scripts`, mypy three passes),
`unit-tests` (45 min, :440-475), `unit-tests-gc-threshold` (45 min, :480-497), `unit-tests-coverage`
(45 min; its test result gates, report advisory, :499-...), `digital-twin-e2e` (20 min **per
device**, matrix of six, success-gated on `unit-tests`), `firmware-build-verify` (15 min per device;
a real `firmware.uf2` link — and the lwIP readback `verify_lwip_macros_in_build()` if the ensemble
changes). No job has a broker or any `services:` container. The hang backstops (per-file timeout,
`stdbuf`, `needs:` with `if: ${{ !cancelled() }}` on `unit-tests`/`firmware-build-verify`) stay
(R13). `scripts/test.sh`'s MicroPython tier and `npm test`'s mock server bind real ports and must not
run concurrently locally (R16); a host-side broker in `tests_scripts/` must bind ephemeral ports
because that tier runs concurrently with the MicroPython tier (CLAUDE.md:787-791).

---

## 5. Gaps an MQTT PoC would have to fill

1. **No outbound TCP client exists in `src/`** — no precedent for connect/reconnect/backoff/keepalive
   over TCP; the nearest shapes are `asy_udp_socket.py` (own-the-socket, never-raise, lock-serialised
   connect/teardown), `asy_ntp_client.py` (network gating, DNS via `resolve_ipv4`, backoff that never
   ends the task) and `asy_uart_comm.py`/J.8 (preallocated byte-stream buffers).
2. **No MQTT code is available to freeze**: the Pico W manifest pulls `bundle-networking`
   (`mip, ntptime, ssl, requests, webrepl, urequests`) and `aioble` — no `umqtt`. micropython-lib's
   `umqtt.simple` is blocking (`wait_msg()` sets `setblocking(True)`, `umqtt/simple.py:193-195`;
   blocking `getaddrinfo` `:80`) and allocates per message (`read(sz)` `:216`) — incompatible with
   D.5/F.3 and §3. Vendoring policy covers only `ext/` (unmodified upstream, never edited) and
   Adafruit/Sensirion code (F.4); an adapted third-party client has no policy home. A project-native
   client is the path that fits every rule [INFERENCE].
3. **lwIP ensemble and its validators know only inbound connections** (§2.3) — an outbound count
   must become an input, with the GC-heap cost (2,324 B) accepted and the shipped image's heap
   re-read (`verify_lwip_macros_in_build()`, §M6.2 formula).
4. **No TCP fault model at L1/L2** (no socket fake, no fake broker, twin WLAN fake decoupled from
   sockets, `FaultInjector` bus-only) and **no TCP port faults at L4** (bench primitives UDP-only).
5. **No broker anywhere** — CI, twin, bench host — and every option has a cost (§4.2).
6. **No socket/heap hazard catalog** — the generated hazard machinery is I2C-bus-centric; the
   webserver's concurrency scenarios are the only socket-pool/heap precedent to extend.
7. **No allocation-rate harness for a TCP stream client** (the UART hazard file is the precedent to
   copy).
8. **Peak heap headroom must be re-measured on silicon** with MQTT active (H.7's 20-30 % band was
   measured without it).
9. **Bookkeeping that has to land with the code**: C.9 task table row or starter; C.8 lock-table row;
   `buildgen/error_catalog.json` band and C.7.1 rows; Part N rows for every tunable; E.6.6 rows for
   L3 (and any L4) gaps; a claimed test port base (28000-31999 free); `devices/*.toml` placement and
   `test_device_tomls.py` allow-list; FRAM chunk (the 8 KB `wozi` FRAM capacity check if wired there,
   `device_scripts/fram_capacity_after_full_system_build.py`); request-body pins and ≤ 253-char
   string bounds if REST-configurable; BACKLOG build-environment entry if `versions.toml`/`apt_packages`
   change.
10. **Decisions the PoC forces** (to be put to the owner through the project's own process, not
    pre-decided here): count MQTT in the lwIP ensemble (+2,324 B) vs run inside the 3 measured spares;
    which devices carry it (a `dev`-only PoC is the only one testable at L3/L4 — `wozi` is never
    flashed, CLAUDE.md:174-190); broker for twin/CI (stdlib fake vs pinned container vs apt mosquitto);
    whether MQTT takes `wifi_mode_lock` for its connect; TLS explicitly out of scope for the PoC.
