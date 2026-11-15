# HTTPS for the web server — research (2026-11-15)

**Status: RESEARCH ONLY, 2026-11-15.** No firmware code has been written and nothing ran on hardware. This file
condenses one research round and ends with the questions it leaves for the owner (section 9). **Temporary**: like
`mqtt_poc/` on its branch, it is deleted once its lasting outcomes (settled decisions, facts, code) have moved into
`SPECIFICATION.md`, `CLAUDE.md` or `BACKLOG.md`.

**Branch.** `ccr-fe3da2dd-jjyfvw`, branched from `claude/whole-project-audit-plan` at `a6f28126` (the head of
pull request #107, release 2.0) and independent of it.

**The owner's request (2026-11-15, quoted):** "Investigate about how to add https connectivity to it. The existing
functionality stays as it is, also Http. The https is on top. Same access as plain HTTP. Microdot already has addons
for this. A method for the self signed cert must be found - either generate on device or upload over the API / Web
interface. See what fits, research the web,"

**Evidence.** Two research reports in `research/`, plus one browser probe run by this session:

| Report | Scope |
|---|---|
| `research/01_upstream.md` | MicroPython v1.29.0, its mbedTLS 3.6.6 and Microdot v2.7.0 read at their tags with file:line references; heap and minimum-heap measurements of a TLS server on the stock v1.29.0 Unix port |
| `research/02_web.md` | Field reports, RP2040 crypto benchmarks, browser rules, how comparable devices handle certificates, on-device certificate generation, MicroPython after v1.29.0 |
| section 6.1 below | Headless Chromium 153 against the stock v1.29.0 TLS server (2026-11-15) |

Marks: **[source]** read in the pinned source by this session or a report and re-checked here; **[measured]** with
its condition named; **[derived]** computed from measured figures, not itself measured; **[reported]** from an
outside source, not reproduced.

---

## 1. Bottom line

1. **HTTPS is feasible in principle with the pinned stack, but not "on top" for free.** MicroPython v1.29.0 runs a
   TLS 1.2 server through `asyncio.start_server(..., ssl=ctx)`, and Chromium 153 completes a handshake with it
   [measured, section 6.1]. Microdot has no TLS add-on: its `ssl=` argument only passes the context to
   `asyncio.start_server()` (`ext/microdot.py:1307-1316`) [source], and this firmware already calls
   `asyncio.start_server()` itself (`src/asy_webserver_service.py:900`). A second listener on port 443 sharing
   `_serve()` gives exactly "same access as plain HTTP": the same routes, the same connection count and timeouts.
2. **Memory is the deciding constraint.** Every HTTPS connection costs about 23-25 KB of GC heap, of which 16,736 B
   is one contiguous block, allocated when the connection is accepted [source + measured, section 4.1]. `dev` has
   about 82 KB free in operation against a serving demand of 68,790 B at its six HTTP connections, about 13 KB of
   margin (SPECIFICATION.md H.7). One HTTPS connection does not fit beside a full HTTP ceiling on any device, and
   under peak HTTP load the largest free block is about 1.5 KB. So HTTPS cannot be added without taking memory
   from HTTP (fewer HTTP connections) or from somewhere else. That is in tension with "the existing functionality
   stays as it is", which makes it the first question for the owner (section 9). The owner has since ruled that
   HTTP and HTTPS share one connection count; with a 4 KB receive buffer and at most one HTTPS slot, about 4 slots
   fit on `dev` and 5 on the other devices, against 6 today (section 4.4).
3. **Every HTTPS request pays a full handshake.** The pinned mbedTLS configuration has no session cache and no
   session tickets, and Microdot closes every connection after one response [source]. The open web page polls
   every 3 s (`buildgen/definitions.py:31-32`), so an open page over HTTPS means one full handshake every 3 s.
4. **Each handshake holds the event loop twice.** The server's ECDHE key generation and ECDSA signature run in
   one uninterrupted C call, its ECDH secret in a second one; mbedTLS 3.6.6 cannot split either on the server side
   [source]. From published RP2040 benchmarks these are about 0.18 s and 0.23 s with a P-256 certificate, and about
   3.4 s for one call with an RSA-2048 certificate [derived]. Both P-256 figures cross the 21 ms routine-stall
   budget and the 50 ms LED frame (SPECIFICATION.md F.3); RSA-2048 also crosses `dev`'s 925 ms UART reply bound.
   **Only an ECDSA P-256 certificate is workable.** Only new C code running the handshake on core 1 removes the
   freeze; session tickets make it rare instead (section 4.5).
5. **v1.29.0 leaks a TCP connection on every refused handshake** until the next garbage collection: a browser
   meeting the self-signed certificate for the first time sends alert 46, which takes exactly that path
   [source + measured, section 6]. Fixed upstream in `9ee1531` (2026-10-02), which is in no release yet.
6. **The certificate cannot be generated on the device with the stock firmware.** No API exists and the needed
   mbedTLS parts are not compiled in [source]. On-device generation needs a C module or our own pure-Python P-256
   and X.509 code. Comparable products either serve no HTTPS (ESPHome, Tasmota, WLED) or take a certificate the
   user uploads (Shelly, Home Assistant) [reported].
7. **Recommended certificate path (agent, 2026-11-15, for discussion):** a per-device ECDSA P-256 certificate made
   on the build host and signed by a small home CA kept on that host, frozen into the device image (section 5.4).
   It writes nothing on the device, survives "Reset to defaults" and reflashes with the same fingerprint, and once
   the CA is installed in browsers and openHAB nothing warns at all. Upload over the API stays possible later.
8. **What only the bench can settle:** the real stall durations, the heap a session needs on the 32-bit target,
   whether the 16.7 KB block can be placed in operation, the C-stack peak of a handshake, and Firefox's and
   Safari's behaviour (section 8). That needs a dev-only proof-of-concept image and the owner's go-ahead for the
   bench.

---

## 2. What the pinned stack provides

MicroPython v1.29.0 (`0fd6c573`), its `lib/mbedtls` at `0bebf8b8` = Mbed TLS 3.6.6, Microdot v2.7.0 (`7742db9f`,
byte-identical to `ext/microdot.py`). Details and line references: `research/01_upstream.md` items 2-8.

- **Server TLS is compiled into the Pico W image.** `MICROPY_SSL_MBEDTLS (1)` and `MICROPY_PY_SSL (1)` on rp2,
  `MBEDTLS_SSL_SRV_C` on; `ssl.py` comes from micropython-lib through the `RPI_PICO_W` board manifest, which this
  project's build relays unchanged (`toolchain/micropython_overrides.py:738`) [source]. No extra flash is needed to
  serve TLS with the stock options.
- **TLS 1.2 only.** TLS 1.3 is off. Key exchanges ECDHE-ECDSA, ECDHE-RSA, static RSA, PSK; AES-GCM and AES-CBC
  (no ChaCha20); curves secp256r1/384r1/521r1 and others, **no X25519** [source]. A TLS 1.2 browser negotiates
  secp256r1 [measured].
- **Certificates and keys** are accepted as PEM or DER bytes, RSA or EC, without a password; the input bytes are
  copied and can be dropped after `load_cert_chain()` [source + measured]. Microdot's docs still say MicroPython
  needs DER; that note predates 1.29.0 [source].
- **Handshake.** `asyncio.start_server(ssl=)` wraps each accepted socket with `do_handshake_on_connect=False`
  (`extmod/asyncio/stream.py:165-167`), so the handshake runs inside the connection task's first read, in two
  no-yield C calls (section 4.3) [source].
- **Missing on the server side** [source]: session cache and tickets, ALPN (so no HTTP/2), a server SNI callback,
  `close_notify` on close, extended master secret, restartable ECC for servers.
- **Allocation.** mbedTLS allocates through `m_tracked_calloc` on the MicroPython GC heap; a failed allocation is
  `OSError(ENOMEM)` [source].
- **Entropy.** `os.urandom` and mbedTLS both draw from pico-sdk's `pico_rand`, a PRNG mixed from ROSC, timer and
  bus-counter entropy; the SDK makes no cryptographic-strength claim [source]. This matters for any key made on the
  device (section 5.3), not for the handshake's ephemeral keys alone.

## 3. How HTTPS would sit in this firmware

- **Listener.** A second listener on TCP 443 next to the existing one on 80, both driving `WebserverService._serve()`,
  so the routes, the reject-when-full count (`_open_conns`), the per-call and outer timeouts and the error handling
  are one code path. `ext/microdot.py` stays untouched (CLAUDE.md). `Request.scheme` reads `http` over TLS too
  (`ext/microdot.py:1418-1419`); nothing here builds an absolute URL (the captive fallback redirects to the relative
  `/`), so that is harmless [source].
- **HTTP stays as it is**: port 80 keeps its listener, its routes and its behaviour. The website uses relative URLs
  only (`js/poll-manager.js`, `js/shell.js`), so the same page works over either scheme.
- **Own accept loop for TLS.** `extmod/asyncio/stream.py` allocates the 21 KB of record buffers in `wrap_socket()`
  before the connection callback runs, prints and drops a connection whose allocation fails (`:168-171`), and lets a
  `MemoryError` from the `SSLSocket` object end the accept task (code reading) [source]. Under this project's rules
  (admission before allocation, SPECIFICATION.md I.4's zero-`MemoryError` design, every refusal counted in
  `HTTPDropped`), the TLS listener would accept the plain socket itself, decide admission first, and only then wrap
  it — our code, no upstream file edited.
- **A separate supervised task** for the TLS listener, so a TLS fault never restarts the HTTP listener.
- **Error classes.** A refused handshake reaches `_serve()` as `OSError` with a negative mbedTLS code (for example
  `-30592` `MBEDTLS_ERR_SSL_FATAL_ALERT_MESSAGE` when a browser rejects the certificate), which today's `except
  OSError` arm would log as W51 on every first browser visit [source + measured]. It needs its own warning code,
  counted like the other drops.
- **Threat model.** SPECIFICATION.md A.11 row 1 records "no authentication, no TLS" as accepted, and a new service
  joins that table in the same change. HTTPS with the same access adds confidentiality and integrity on the wire for
  clients that choose it; access control is unchanged, and port 80 still serves everything in clear.
- **Hotspot mode.** Captive-portal checks use HTTP; HTTPS adds nothing to the setup flow. Whether the TLS listener
  also runs on the hotspot is a detail for the design.
- **MQTT branch.** The MQTT proof of concept on `claude/whole-project-audit-plan-followup` takes one web connection
  (owner, 2026-10-07: "Web connections 6->5") and heap of its own; if both land, their budgets add up.

## 4. What it costs

### 4.1 Heap

| Item | Size | Mark |
|---|---|---|
| receive record buffer per connection, one contiguous block | 16,717 B → 16,736 B on rp2 (1,046 GC blocks) | [source] `ssl_misc.h:395-409`, `MBEDTLS_SSL_IN_CONTENT_LEN` 16384 |
| send record buffer per connection | 4,429 B → 4,448 B | [source] `MBEDTLS_SSL_OUT_CONTENT_LEN` 4096 |
| one established session, everything included | 24,896 B (EC) / 25,408 B (RSA) on the 64-bit Unix port | [measured] `research/01_upstream.md` Part 2 |
| `SSLContext` plus a parsed P-256 certificate and key, kept for the server's life | about 4.9 KB on 64-bit, less on rp2 | [measured] |
| smallest heap above a plain server that passed 6 of 6 runs | one P-256 session +32 KB, two +54 KB (RSA-2048 +34 / +58 KB), 64-bit; a 6-8 KB band below passes only sometimes | [measured] |

Against this firmware's budget (SPECIFICATION.md H.7, Part N):

- **In operation.** One collect leaves 81,984-82,400 B free on `dev`; the serving demand at its six connections is
  68,790 B against the `web.serving_demand_budget_b` of 72,232 B. The other devices' demand is 57,888-61,422 B. A
  TLS connection carries the same request and response as an HTTP one plus its ~24 KB, so **one HTTPS connection
  roughly costs what three of `dev`'s HTTP connections cost** [derived].
- **Placeability.** The budget's derivation rests on "many small pieces, never one block". The receive buffer is
  one 16,736 B block. On the final release image the largest free block after one collect in operation read
  16,192-53,040 B (bench relay 41, 2026-11-13, `claude/u35-bench-campaign`), and about 1.5 KB at peak HTTP load
  (H.7). So even an idle device places it only some of the time [derived].
- **Boot survivors.** The context and certificate live for the server's life: about 4-5 KB against `dev`'s 36,368 B
  of build survivors and the owner's bound of 41,000 B (`l3.heap_headroom_after_full_system_build_max_added`), a
  4,632 B margin [derived; needs the 32-bit figure].
- **Ways out, none chosen:** (a) at most one HTTPS connection at a time with the HTTP ceiling lowered to pay for it;
  (b) a static mbedTLS arena outside the GC heap (`MBEDTLS_MEMORY_BUFFER_ALLOC_C`, off at the pin,
  `lib/mbedtls/include/mbedtls/mbedtls_config.h:3076`, `library/memory_buffer_alloc.c:562`; a C-level override): no
  fragmentation risk for the 16.7 KB block, but the arena is taken from the GC heap permanently, so HTTP capacity
  drops anyway; (c) a smaller receive buffer: **not possible for browsers**. Chrome implements neither max fragment
  length nor record size limit, and mbedTLS supports record size limit only for TLS 1.3 [reported, source]. A
  client may send a full 16 KB record, so a smaller buffer breaks the spec, even though this server's own limits
  (2,048 B head, 2,048 B body) mean its legitimate requests never need one.

### 4.2 CPU per request

No resumption and no keep-alive (section 2): **every request is a full handshake**. With a P-256 certificate that
is about 0.4 s of server CPU [derived: ECDHE key generation 83.6 ms, ECDSA sign 92.6 ms, one ECDH secret about
225 ms, from rojinc/pqc-cortex-m0-benchmark, RP2040 at 125 MHz, `-O3`, pico-sdk mbedTLS with `MBEDTLS_ECP_NIST_OPTIM`].
An open page polls every 3 s: one handshake per poll is about 13 % of the CPU per open tab. A page load opens two
connections, and Chromium-family browsers may open one or two spare ones (H.7), each a full handshake. A browser's
first visit costs one more, refused handshake (section 6.1).

Server-side session tickets would cut every later handshake to symmetric crypto only, but need a C-level override
(enable `MBEDTLS_SSL_SESSION_TICKETS` and `MBEDTLS_SSL_TICKET_C`, and patch `modtls_mbedtls.c` to set up a ticket
key) — the same kind of patch as the `modlwip` overrides (SPECIFICATION.md B.14.4).

### 4.3 Event-loop stalls

Two non-yielding C calls per handshake [source; structure measured on the Unix port]:

| Stretch | Work | P-256 cert | RSA-2048 cert |
|---|---|---|---|
| 1, after the ClientHello | ServerHello, Certificate, ServerKeyExchange (ECDHE key generation + signature), ServerHelloDone | about 176 ms | about 3.39 s plus key generation |
| 2, after the client's key exchange | ECDH secret, key derivation, both Finished | about 225 ms | about 225 ms |

All [derived] from the benchmark above; MicroPython's own rp2 compiler flags may make them slower. Against the F.3
consumers: `con.routine_stall` 21 ms crossed about tenfold; `con.led_frame` 50 ms crossed (a visible LED stutter,
cosmetic); `con.uart_reply` 925 ms on `dev` held by P-256 but crossed by RSA (hard: a failed transfer and a resync);
`con.watchdog` 6,000 ms held. A new F.3 row would have to state the LED degradation it accepts, a decision for the
owner once the bench has measured it (section 8). mbedTLS's restartable ECC would split the work but applies only to TLS 1.2 clients
(`lib/mbedtls/include/mbedtls/mbedtls_config.h:811-819`) [source].

### 4.4 Memory per connection, HTTP against HTTPS

Worst case on `dev` (a `/status` response); the HTTP figure is H.7's serving demand per connection, 68,790 B / 6:

| | HTTP | HTTPS, stock receive buffer | HTTPS, 4 KB receive buffer |
|---|---|---|---|
| request and response, both kinds | about 11.5 KB | about 11.5 KB | about 11.5 KB |
| TLS receive buffer | — | 16,736 B, one block | about 4.4 KB |
| TLS send buffer | — | 4,448 B | 4,448 B |
| session, transform, socket object | — | about 2 KB | about 2 KB |
| **per connection** | **about 11.5 KB** | **about 35 KB, 3x** | **about 22 KB, 2x** |

[source for the buffers, measured on the 64-bit Unix port for the session (+24.9 KB), derived for the rest]. The
other devices' HTTP figure is about 9.6-10.2 KB. On top: the listener's context and certificate once, about 4-5 KB,
and a few KB per handshake while it runs. Silicon measured about 7.5-8 KB of live heap per open HTTP connection at
peak (H.7).

**The smaller receive buffer.** The server's own limits cap every request at a 2,048 B head and a 2,048 B body,
so a 4-6 KB `MBEDTLS_SSL_IN_CONTENT_LEN` holds every record a request this server answers can need; a client
sending a larger record has that connection refused (`lib/mbedtls/library/ssl_msg.c:4303`). It departs from the TLS
rule that a peer may send 16 KB records unless one is negotiated, which no browser offers (4.1). The value is set
unconditionally in `extmod/mbedtls/mbedtls_config_common.h:63-65`, so it needs a config override, and Chrome, Firefox
and Safari need checking against it on the bench.

**One shared connection count** (owner, 2026-11-15: "Generally, the connection count always is for Http and https
together, so not for each."). The serving budget then has to hold the worst mix of that count. With the listener's
context taken from the heap free after boot as well, the total that fits [derived; the bench sets the figures]:

| Shared total | any slot may be HTTPS | at most one slot HTTPS |
|---|---|---|
| stock receive buffer | `dev` 1, others 2 | `dev` 3, others 4 |
| 4 KB receive buffer | `dev` 3, others 3 | `dev` 4, others 5 |

### 4.5 Mitigations

**The freeze.** No stock-mbedTLS setting removes it; the work can only be made shorter, rarer or moved off the
event loop.

| Measure | Effect | Cost |
|---|---|---|
| ECDSA P-256 only, ECDHE-ECDSA suites | stalls about 0.18 s and 0.23 s instead of 3.4 s | a cipher-list setting |
| **Session tickets** (`MBEDTLS_SSL_SESSION_TICKETS`, `MBEDTLS_SSL_TICKET_C`; prerequisites cipher and GCM, both on, `check_config.h:974-982`) | a returning browser's connections resume with symmetric crypto only, so full handshakes happen on first contact, after a reboot and at ticket expiry | a config override plus a patch to `modtls_mbedtls.c` setting up a ticket context (two keys, about 1-2 KB once, nothing per session) |
| `MBEDTLS_HAVE_ASM` (a Thumb-1 bignum path exists, `library/bn_mul.h:663`; upstream master enables it for bare-metal ports, `9e348d293`) | shorter stalls, gain on the M0+ unmeasured | a config override |
| 200 MHz system clock (certified for the RP2040 from pico-sdk 2.1.1, at a regulator voltage of at least 1.15 V) | stalls about 40 % shorter | every timing of the firmware was measured at 125 MHz, so all of it is re-measured |
| `MBEDTLS_SSL_ASYNC_PRIVATE` (`mbedtls_config.h:1628-1637`; the server's hook at `ssl_tls12_server.c:3063-3076`) with the signature on core 1 | removes the signature, about 0.09 s of 0.4 s | a C module and core-1 code; key generation and the ECDH secret stay in the loop |
| the whole handshake on core 1, socket I/O kept on core 0 | removes the freeze | a new C subsystem: rp2's lwIP lock only suspends PendSV on its own core (`ports/rp2/mpnetworkport.c:127-135`), `_thread` runs without a GIL (`ports/rp2/mpconfigport.h:140-142`), so core 1 may not touch the network stack; high effort and risk |
| defer a full handshake while an LED animation runs | hides the stutter | a short wait for the client; Python only |

Recommended for discussion (agent, 2026-11-15): P-256 only and session tickets, with `MBEDTLS_HAVE_ASM` once its
gain is measured. The hard bounds (watchdog, `dev`'s UART reply) then hold, and a first connection still costs an LED
stutter.

**The other findings.**
- The connection leak: backport `9ee1531` as an override (B.14.4), removed when a release carries it.
- Allocation before admission, a silent `ENOMEM` and a `MemoryError` ending the accept task: an own TLS accept loop
  that admits first, counts every refusal and runs as its own supervised task (section 3).
- A refused certificate logged as W51: its own warning code (section 3).
- The static-RSA path's 1 KB stack frame: gone with the ECDHE-ECDSA cipher list; the handshake's stack peak still
  needs the bench (4.6).

### 4.6 Flash and C stack

- **Flash.** TLS serving needs nothing new compiled in. The release image on `dev` is 1,158,444 B of 1,228,800 B
  before the filesystem (bench relay 41, 2026-11-13), about 70 KB free. On-device certificate generation in C would
  add mbedTLS's write modules and a C module; that size is not measured.
- **C stack.** `dev`'s main stack is 7,936 B with a measured peak of 6,060 B (about 1.9 KB left, the owner's
  reserve 1,024 B). The handshake's deepest chain was not measurable here (no ARM toolchain in this sandbox). The
  static-RSA key exchange alone puts a 1,024 B buffer in one frame (`lib/mbedtls/library/rsa.c:2097-2107`), another
  reason to restrict the cipher list to ECDHE-ECDSA [source]. Needs an on-device stack-paint measurement.

## 5. The certificate

### 5.1 What the certificate must be

- **ECDSA P-256** (sections 4.2-4.3); restrict the server's cipher list to the ECDHE-ECDSA AES-GCM suites.
- **subjectAltName** with the names clients use: the hostname, `<hostname>.local` (the mDNS responder answers for
  it, SPECIFICATION.md A.11 row 4) and, where the device has a fixed address, an `IP:` entry. Chrome ignores the
  Common Name [reported].
- **Validity**: browsers impose no maximum on a self-signed or privately trusted leaf that this research could
  find; Apple caps certificates from user-added roots at 825 days [reported].
- **Browser exceptions are tied to the certificate's fingerprint**: Chrome remembers "proceed anyway" for one week
  per host and certificate chain, Firefox permanently per host and port; any new certificate warns again
  [source, `research/02_web.md` section 3].
- **openHAB's HTTP binding** either validates against the Java trust store or ignores every error
  (`ignoreSSLErrors`); it has no per-device pinning [source].
- **Clock.** The device clock reads 2021-01-01 until NTP sync (SPECIFICATION.md F.1); that matters only for
  verifying peers, which the server does not do.

### 5.2 Options

| | (a) Build-time, frozen into the image | (b) Upload over the API / website | (c) Generated on the device |
|---|---|---|---|
| Who makes it | a host script in the build chain, per device | the user, on a PC (openssl, or a repo script) | the device |
| Device writes | **none** (frozen like the website) | one write per upload: a config file on flash, or FRAM | one write per generation: FRAM, or flash |
| Write rules (CLAUDE.md) | untouched | a flash write follows a user action, but a new write site is the owner's decision | flash: firmware-initiated, so only FRAM fits the rule without a user action |
| New device code | listener and context only | plus a PUT field, validation, storage, website file picker, key masking on GET | plus a C module (e.g. `dmazzella/ucryptography`) or our own P-256, SHA-256-signing and DER/X.509 code |
| Survives "Reset to defaults" / reflash | yes / yes with the same key if the host keeps it | flash file: no / yes; FRAM: yes, not "Erase FRAM" | as (b) |
| Trust | home CA possible: **no warnings** once the CA is installed | home CA possible | self-signed per device only: every browser warns per device, Chrome weekly |
| Private key exposure | in the build artifacts on the build host | crosses the LAN once in clear over port 80 (inside A.11's model) | never leaves the device |
| Body cap | — | a P-256 PEM certificate and key, about 870 B, fit the 2,048 B cap; RSA would not | — |
| Prior art | — | Shelly 2.x, Home Assistant | none among the products surveyed |

### 5.3 On-device generation in detail

Stock v1.29.0 has no key-generation or certificate-writing API, and `MBEDTLS_PK_WRITE_C`, `MBEDTLS_X509_CRT_WRITE_C`,
`MBEDTLS_X509_CREATE_C`, `MBEDTLS_PEM_WRITE_C` and `MBEDTLS_GENPRIME` are all off [source]. Two routes:

- **A C user module over the port's mbedTLS**: `dmazzella/ucryptography` (lists rp2; `CertificateBuilder` with IP and
  DNS SANs) [reported]. The project's build has no user C modules today: a new build surface to re-check at every
  MicroPython pin move, plus enabling the write modules in the mbedTLS config. P-256 key plus signature is about
  0.2 s of CPU in one call [derived].
- **Pure Python** on MicroPython's arbitrary-precision integers and the mbedTLS-backed `hashlib.sha256`: no build
  change, and the work can yield between steps so it never stalls the loop. But it is cryptographic code of our own,
  its speed is unmeasured, and its key's quality rests on `pico_rand` (section 2).

Either way the certificate is self-signed per device (no home CA unless the CA key is also on the device), and its
IP entry goes stale on an address change.

### 5.4 Recommendation (agent, 2026-11-15, for discussion; nothing is decided)

**(a), build-time, with a home CA on the build host.** A host-side step creates, once, a home CA (P-256) in a
directory outside the repository, then per device a P-256 key and a certificate whose subjectAltName carries the
TOML's hostname, `<hostname>.local` and an optional fixed IP; buildgen freezes certificate and key into the image
like the website. Why it fits the project's rules best:

- zero writes on the device, so the central least-wear rule is untouched and no new write site exists;
- no new API field, website control or validation path, and no cryptographic code of our own on the device;
- reflashes keep the same key and fingerprint while the host keeps it; "Reset to defaults" and "Erase FRAM" leave
  it alone;
- installing one CA certificate in each browser and once in openHAB's trust store removes every warning for every
  unit, and openHAB can validate instead of `ignoreSSLErrors`.

Costs: changing a certificate needs a rebuild and reflash; the build host's CA key becomes something to keep safe;
the private key sits in the build artifacts (never committed: CLAUDE.md's credentials rule, `.gitignore`); an IP
entry needs the address in the TOML. Upload (b) can be added later on top for anyone who wants their own
certificate, without changing (a).

## 6. Upstream defects and gaps that matter here

- **Socket leak on a refused handshake** [source + measured]: `ssl_check_async_handshake_failure()`
  (`extmod/modtls_mbedtls.c:220-258`, v1.29.0) drops its reference to the TCP socket and frees the TLS state
  without closing the socket, so the later `close()` does nothing (`:972-975`). On rp2 the lwIP socket's finaliser
  (`extmod/modlwip.c:1166-1168`, `__del__` at `:1719`) frees it only at the next garbage collection. Every browser
  that rejects the certificate takes this path (section 6.1), and the lwIP pool has three spare connections above
  the HTTP ceiling (H.7), shared with port 80. Upstream fix: `9ee1531` "extmod/modtls_mbedtls: Close transport on
  handshake failure" (committed 2026-10-02, on master, in no release; v1.29.0 is the newest stable release). A
  backport fits the project's override mechanism (SPECIFICATION.md B.14.4), removed again when a pinned release
  carries it.
- **No resumption, no close_notify, no ALPN, no extended master secret** (section 2). Chromium accepts the last one
  missing (section 6.1); Firefox and Safari were not tested.
- **Microdot's TLS docs** recommend RSA-4096 without an IP SAN and DER files; both are wrong for this target.

### 6.1 Browser probe (2026-11-15)

Headless Chromium 153.0.8010.12 (Playwright's) against the stock v1.29.0 Unix port (standard variant) running an
asyncio TLS server with a P-256 certificate (`CN=sensor.local`, SAN `DNS:sensor.local`, `IP:127.0.0.1`) on
127.0.0.1, read from Chromium's net log:

- **Certificate not trusted**: Chromium received ServerHello and Certificate, sent alert 46 (`certificate_unknown`)
  and failed with `ERR_CERT_AUTHORITY_INVALID`; the server saw `OSError(-30592, 'MBEDTLS_ERR_SSL_FATAL_ALERT_MESSAGE')`,
  the leaking path above.
- **Certificate errors ignored** (Playwright's `ignoreHTTPSErrors`): the first connection aborted the same way, the
  retry completed: TLS 1.2, cipher suite `0xC02C` (ECDHE-ECDSA-AES256-GCM-SHA384), group 23 (secp256r1), signature
  `0x0403` (ECDSA-SHA256), not resumed; `200`, body `ok`.

The probe's server was `research/01_upstream.md`'s `tls_srv_fast.py` (a minimal `asyncio.start_server(ssl=ctx)` server
answering `200 ok`), allowed three connections so Chromium's retry could land; the probe script was a few lines of
Playwright (`chromium.launch()` with `--log-net-log`, `page.goto()`, `response.securityDetails()`). Neither is kept.

## 7. A possible path, if the owner goes on (nothing here is decided)

1. Owner decisions on section 9.
2. A dev-only proof-of-concept image: the TLS listener with its own admission, a P-256 certificate made by the host
   step of 5.4, the leak fix as an override, and a TLS ceiling of one.
3. Bench measurements (section 8), with the owner's go-ahead in that session.
4. Only then the design for all devices: the budget split, the F.3 row, the error code, the A.11 row, tests per
   tier (twin TLS, Chromium in the web tier, the crossover rule's software-resource cases).

## 8. What only the bench can settle

- the two stall durations per handshake on the RP2040 under this firmware's build flags, against F.3;
- the heap one session needs on the 32-bit target, the context's boot-survivor cost, and whether the 16,736 B block
  places in operation and under HTTP load;
- the C-stack peak of a handshake against the 7,936 B stack;
- a page left open over HTTPS for an hour: CPU share, LED stutter, `HTTPDropped`, leaked connections;
- Firefox and Safari against the pinned configuration (TLS 1.2 without extended master secret).

## 9. Questions for the owner (asked in session, 2026-11-15)

Asked one at a time; each answer is recorded here with the owner's words once given.

**Answered.** On question 1 (owner, 2026-11-15): "Generally, the connection count always is for Http and https
together, so not for each." The same message asked whether the freeze can be prevented and what an HTTPS connection
costs against an HTTP one, answered in 4.4 and 4.5. That leaves the split inside the shared count open, asked as
question 1a.

1a. **Within the shared count: at most one HTTPS slot, or any slot?** (section 4.4)
   - (a) At most one of the shared slots is HTTPS at a time, with the 4 KB receive buffer and session tickets
     (recommended): about 4 slots in all on `dev` and 5 on the other devices; a second HTTPS client waits or is
     refused while one is served.
   - (b) Any slot may be HTTPS: about 3 slots in all on every device with the 4 KB buffer, 1-2 with the stock one;
     every client may use either scheme.

1. **HTTPS memory: take it from HTTP connections, or stop?** (section 4.1)
   - (a) HTTPS gets one connection at a time and the HTTP ceiling drops to pay for it, about 6 → 3 on `dev` and
     6 → 4 on the others [derived from section 4.1's per-connection figures; set from bench figures]: every device
     serves fewer concurrent HTTP clients, with more refusals under load, and the 16.7 KB block still has to find a
     hole in a fragmented heap; no change to the buses.
   - (b) As (a), but the TLS memory comes from a static mbedTLS arena carved out of the GC heap: the same loss of
     HTTP connections on every device, a C-level override to maintain at each MicroPython pin move, and no
     fragmentation risk for the 16.7 KB block.
   - (c) Stop here: no HTTPS; the research stays on record and nothing changes on any device.
2. **Which certificate source: build-time CA, upload, or on-device generation?** (section 5)
   - (a) Build-time with a home CA (recommended, 5.4): no device writes on any device, no new API field, no browser
     warning once the CA is installed; a certificate change needs a reflash.
   - (b) Upload over the API and website: one write per upload on the unit concerned (flash or FRAM), a new PUT
     field and website control; works with a home CA too.
   - (c) Generated on the device: a C module or our own crypto code on every device, one FRAM write per
     generation, self-signed only, so every browser warns per unit.
3. **Build a dev-only proof-of-concept image for bench measurements?** (sections 7-8)
   - (a) Yes: one reflash of `dev` and a short bench round with the owner's go-ahead in that session; no other
     device changes.
   - (b) Not now: the stall, heap and stack figures stay estimates.

## 10. Sources

Upstream sources are cited by file:line at the pinned tags in `research/01_upstream.md`; web sources with their URLs
in `research/02_web.md`. The ones this file leans on most:

- MicroPython v1.29.0: `extmod/modtls_mbedtls.c`, `extmod/asyncio/stream.py`, `extmod/mbedtls/mbedtls_config_common.h`,
  `ports/rp2/mbedtls/mbedtls_config_port.h`; mbedTLS 3.6.6 `library/ssl_tls12_server.c`, `library/ssl_misc.h`,
  `include/mbedtls/mbedtls_config.h`.
- Upstream fix `9ee1531b509e13dfeb7f0f1da0764cda8d289fab`: https://github.com/micropython/micropython/commit/9ee1531b5
- RP2040 mbedTLS benchmarks: https://github.com/rojinc/pqc-cortex-m0-benchmark
- Chromium certificate-error bypass: `components/security_interstitials/content/stateful_ssl_host_state_delegate.cc`;
  BoringSSL extensions: `ssl/extensions.cc`; Firefox: `security/manager/ssl/nsCertOverrideService.cpp`.
- RFC 8449 (record size limit): https://www.rfc-editor.org/rfc/rfc8449.html
- Shelly custom HTTPS certificates: https://shelly-api-docs.shelly.cloud/gen2/General/CustomHTTPSCertificates/
- `dmazzella/ucryptography`: https://github.com/dmazzella/ucryptography
- openHAB HTTP binding: `openhab-addons/bundles/org.openhab.binding.http`
- This repository: SPECIFICATION.md A.11, F.3, H.7, I.4, I.6, B.14.4; `src/asy_webserver_service.py`;
  `ext/microdot.py`; `buildgen/definitions.py`.
