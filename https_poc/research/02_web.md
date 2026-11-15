# HTTPS server on Pico W / MicroPython v1.29.0 / Microdot v2.7.0: web research

**Raw report (2026-11-15)**, written by a research subagent and condensed into `../RESEARCH.md`, which re-checked the
claims its conclusions rest on. `<scratch>` paths name the research session's temporary space; the scripts and
clones there were not kept.

Research date: 2026-11-15. Every claim has a URL or names a source tree at a stated commit. Labels:
**[measured]** means the source reports a measurement, and the label says who measured it and on what.
**[claimed]** means stated without a measurement. **[derived]** means my own arithmetic from measured
figures, not a measurement. **[source]** means read directly in source code or docs at a stated version.

Some hosts could not be fetched from this session: forums.raspberrypi.com, support.apple.com,
chromestatus.com, shelly-api-docs.shelly.cloud, blog.crawlex.net and www.ietf.org. Anything about
those pages comes from the search engine's summaries of them and is marked **(search summary only)**.
The GitHub pages, raw.githubusercontent.com and git clones did work.

Source trees read:
- MicroPython, tag `v1.29.0` (commit 0fd6c573e, 2026-08-24) and `master` at d2d095d0f (2026-11-07).
  Partial clone: https://github.com/micropython/micropython
- Microdot, tag `v2.7.0` (7742db9, 2026-09-18): https://github.com/miguelgrinberg/microdot
- pico-examples, 0d62f75 (2026-09-03), ams1/pico_https, rojinc/pqc-cortex-m0-benchmark, dmazzella/ucryptography,
  Carglglz/mpy-mbedtls, tasmota/docs, esphome/esphome.io, openhab/openhab-addons, plus Chromium, Firefox and
  BoringSSL files fetched raw from GitHub (main branches, 2026-11-15).

---

## 0. What MicroPython v1.29.0 itself does: the baseline every other finding is measured against

All of the following is **[source]**, read in MicroPython at `v1.29.0`.

- **The rp2 port uses mbedTLS, and its config is MicroPython's own, not mbedTLS's default.** It is set by
  `ports/rp2/mbedtls/mbedtls_config_port.h` and `extmod/mbedtls/mbedtls_config_common.h`. The mbedTLS submodule is
  v3.6.6, per commit 19e685eca: https://github.com/micropython/micropython/commit/19e685eca
- **TLS 1.2 only.** `MBEDTLS_SSL_PROTO_TLS1_2` is set, along with TLS1 and TLS1_1. `MBEDTLS_SSL_PROTO_TLS1_3` is absent.
- **Buffers.** `MBEDTLS_SSL_IN_CONTENT_LEN` is 16384 and `MBEDTLS_SSL_OUT_CONTENT_LEN` is 4096, under the comment
  "Use a smaller output buffer to reduce size of SSL context".
- **No buffer-shrinking extension is compiled in.** Neither `MBEDTLS_SSL_MAX_FRAGMENT_LENGTH` nor
  `MBEDTLS_SSL_RECORD_SIZE_LIMIT` is defined, and neither is `MBEDTLS_SSL_VARIABLE_BUFFER_LENGTH`.
- **No server-side session resumption.** `MBEDTLS_SSL_SESSION_TICKETS`, `MBEDTLS_SSL_TICKET_C` and
  `MBEDTLS_SSL_CACHE_C` are all absent, so every TLS connection to the device is a full handshake.
- **Key exchanges and ciphers.** `MBEDTLS_KEY_EXCHANGE_ECDHE_ECDSA_ENABLED`, `..._ECDHE_RSA_ENABLED`,
  `..._RSA_ENABLED` and `..._PSK_ENABLED` are set, as are `MBEDTLS_GCM_C` and `MBEDTLS_AES_ROM_TABLES`.
  ChaCha20-Poly1305 is not enabled.
- **Curves.** secp192/224/256/384/521 r1 and secp192/224/256 k1. X25519 is **not** enabled in v1.29.0.
- **`MBEDTLS_ECP_NIST_OPTIM` is on for rp2**, set in the port header. `MBEDTLS_HAVE_ASM` is off in v1.29.0.
- **No key or certificate writing.** `MBEDTLS_PK_WRITE_C`, `MBEDTLS_X509_CRT_WRITE_C`, `MBEDTLS_X509_CREATE_C` and
  `MBEDTLS_GENPRIME` are absent. `MBEDTLS_PK_PARSE_C`, `MBEDTLS_X509_CRT_PARSE_C`, `MBEDTLS_PEM_PARSE_C` and
  `MBEDTLS_ASN1_WRITE_C` are present.
- **mbedTLS allocates from the MicroPython GC heap.** rp2 sets `MICROPY_MBEDTLS_CONFIG_BARE_METAL`. That maps
  `MBEDTLS_PLATFORM_STD_CALLOC` to `m_tracked_calloc`, which calls `m_malloc_maybe()` in `py/malloc.c`
  (`ports/rp2/mpconfigport.h:122`: `MICROPY_TRACKED_ALLOC (MICROPY_SSL_MBEDTLS || ...)`). So each connection's ~16 KB
  input record buffer is one contiguous GC-heap block.
  - The bare-metal build does **not** retry `mbedtls_ssl_setup()` after a `gc_collect()`; only non-bare-metal ports
    do (`modtls_mbedtls.c`, `ssl_socket_make_new`).
  - `MBEDTLS_ERR_SSL_ALLOC_FAILED` is raised as `OSError(ENOMEM)` (`mbedtls_raise_error`).
- **PEM is accepted in v1.29.0.** Commit 8356e6732 (Damien George, 2026-07-31; in `v1.29.0`) "Enable PEM parsing
  in common mbedTLS config": https://github.com/micropython/micropython/commit/8356e6732
  - `asn1_get_data()` adds the terminating NUL for PEM.
  - `SSLContext.load_cert_chain(certfile, keyfile)` takes paths or, as a MicroPython extension, bytes
    (`docs/library/ssl.rst` at v1.29.0).
- **asyncio server path.** `asyncio.start_server(..., ssl=ctx)` wraps each accepted socket with
  `ctx.wrap_socket(s2, server_side=True, do_handshake_on_connect=False)` (`extmod/asyncio/stream.py`, `Server._serve`).
  - An `OSError` there, such as ENOMEM, is printed, and that client socket is closed and skipped. The server keeps running.
  - The handshake then runs inside the first non-blocking `read`/`write` calls. Each mbedTLS step that does public-key
    math runs to completion inside that call, so the asyncio loop is held for the length of each crypto step.
    This is an inference from the code structure and was not measured here.
- **TLS-PSK server support exists** (`SSLContext.server_psk_keys`, commit aa25a4ec2, 2026-05-28, in v1.29.0).
  Browsers do not use PSK, so this only helps machine-to-machine clients.
- **No keep-alive in Microdot v2.7.0.** `Microdot.handle_request()` reads one request, writes one response and calls
  `writer.aclose()` (`src/microdot/microdot.py`, around line 1415). So **one HTTP request means one TCP connection
  means one full TLS handshake** on this stack. A page that loads HTML, JS, CSS and API calls pays one handshake per
  resource.
- **Handshake-failure socket leak in v1.29.0, fixed only on master.** Commit 9ee1531b5 (committed 2026-10-02, in no
  tag yet): https://github.com/micropython/micropython/commit/9ee1531b5. Its message: "Fatal TLS handshake errors
  during read or write cleared SSLSocket.sock without closing the underlying transport. Later close() calls therefore
  became no-ops, which could leave native sockets allocated until their TCP timeout expired."
  - With a self-signed certificate, browsers abort the first handshake when they show their warning.
  - So on v1.29.0, every rejected handshake can strand a native (lwIP) socket. This is an inference from the commit
    text plus the deferred-handshake server path; it was not measured.

---

## 1. Real-world reports of a TLS server (or TLS in general) on Pico W / RP2040

**Handshake duration**
- **CircuitPython HTTPS server on Pico W.** adafruit/circuitpython#7657, opened 2023-02-28, CircuitPython version
  not stated: https://github.com/adafruit/circuitpython/issues/7657
  - **[measured, by the reporter]** "taking 6 seconds to respond with a HTML file that's around 100 bytes and a
    1024-bit RSA certificate", against "75 to 350 milliseconds" over plain HTTP.
  - **[claimed]** 2048-bit certificates were "about 1.5x slower".
  - A comment notes that CircuitPython's RP2040 mbedTLS config lacks `MBEDTLS_SSL_CACHE_C` (session caching).
  - Still open, milestone "Long term".
- **Raspberry Pi Forums, "Slow TLS (server) handshake (~3 seconds) normal?"** C SDK + mbedTLS on Pico W, about
  2023: https://forums.raspberrypi.com/viewtopic.php?t=362979 **(search summary only)**
  - **[measured, by the forum users]** about 3 s server handshake with RSA-2048, and about 1 s with RSA-1024.
  - An EC prime256v1 key was reported *slower*: "about 9 seconds from client hello to server hello", and a capture
    suggested about 18 s in total.
  - The cause of the slow EC case is not explained in the summary. Compare the RP2040 ECC figures in section 2,
    which predict about 0.4 s of crypto.
- **Raspberry Pi Forums, "TLS Handshake very slow, LwIP, FreeRTOS, MbedTLS"** (Pico W):
  https://forums.raspberrypi.com/viewtopic.php?t=353547. Title only; the content could not be fetched.
- **MicroPython on Pico W, client side.** Discussion #10559, posted 2023-02-14, MicroPython v1.19.1-837:
  https://github.com/orgs/micropython/discussions/10559
  - **[measured, by JustinS-B]** TLS connect time to an MQTT broker: EC P-256 7.232 s, RSA-2048 8.016 s,
    P-384 11.288 s, P-521 16.425 s, RSA-4096 26.646 s.
  - **[measured, Carglglz]** ESP32 P-256: 1.9 s.
  - These are old firmware and client-side, so they are not a server figure.
- **MicroPython HTTPS server on Pico W / Pico 2 W.** Raspberry Pi Forums t=388660, about 2025:
  https://forums.raspberrypi.com/viewtopic.php?t=388660 **(search summary only)**
  - Uses `ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)` with the cert and key in the root filesystem.
  - One reply: "Seemed to work fine on a Pico 2 W with MicroPython 1.25.0 but did give an error message when I
    connected from Firefox on Win11".
  - The author mentions "dropping packets and exhibiting huge latency issues which no one has so far got to the
    bottom of". No figures.
- **MicroPython ESP8266 server, axTLS, v1.27.0.** Discussion #18794, 2026-02-08:
  https://github.com/orgs/micropython/discussions/18794
  - **[measured, by stonehippo]** RSA-512 about 1 s, RSA-1024 about 8 s, RSA-2048 "about 50 seconds (!)".
  - PKCS#1 DER keys were needed. A different chip and stack; included only as an order-of-magnitude reference.

**RAM per connection and MemoryError reports**
- **CircuitPython (Zephyr port) on Pico W.** PR #11802, merged 2026-11-09:
  https://github.com/adafruit/circuitpython/pull/11802
  - **[measured with gdb, by the PR author]** "Whole TLS connection, peak 32,640" bytes; key buffers peak 270 bytes.
  - Before the fix, "Only 38.5 KB was left for Python and TLS, so HTTPS failed with MemoryError".
  - The mbedTLS config differs from MicroPython's, so this is not directly transferable.
- **CircuitPython #9003.** MemoryError at `SSLSocket.accept()` for an HTTPS server, opened 2024-03-04:
  https://github.com/adafruit/circuitpython/issues/9003
  - **[measured, by the reporter]** on Pico W, about 40 KB+ free after the caught MemoryError, about 80 KB+ before
    accept, about 50 KB+ before close.
  - Closed 2025-05-09 via PR #10328. In January 2025 it was reported working on Pico and Pico 2.
- **RPi forum t=382328**: https://forums.raspberrypi.com/viewtopic.php?t=382328 **(search summary only)**
  - **[claimed]** "ussl.wrap_socket() requires 16kb of continuous memory to be available otherwise it throws the
    ENOMEM error regardless of how much actual free memory there is".
  - This matches the v1.29.0 config: a 16384-byte input content buffer allocated on the GC heap (section 0).
- **MicroPython #9071** (Pico W, 2022, around v1.19.1): TLS failed on its own; the workaround then was to shrink the
  GC heap so mbedTLS could use the C heap: https://github.com/micropython/micropython/issues/9071
  - Today's rp2 instead puts mbedTLS on the GC heap through `m_tracked_calloc` (section 0).
- **Microdot #160** (ESP32, MicroPython v1.20 to v1.22 preview, 2023-07 to 2024-01):
  https://github.com/miguelgrinberg/microdot/issues/160
  - Errors seen: `OSError: [Errno 12] ENOMEM` after the handshake, and
    `OSError: (-30464, 'SSL - An unexpected message was received from our peer')`.
  - **[claimed, by Carglglz]** only one active SSL connection at a time was practical on ESP32.
  - Freezing Microdot into the firmware freed enough RAM.
  - Closed after the maintainer verified TLS on 1.22.
- **Generic ESP32 HTTPS server library.** fhessel esp32_https_server README:
  https://awesome.ecosyste.ms/api/v1/projects/github.com%2Ffhessel%2Fesp32_https_server **(search summary only)**
  - **[claimed]** "each opened connection of the TLS-enabled HTTPSServer requires additional 40 to 50 kB of heap memory".

**Concurrency**
- No source was found that measures how many concurrent TLS server connections a Pico W running MicroPython sustains.
- The only concurrency statement is the ESP32 claim above, "only one active SSL connection at a time" (Microdot #160).
- **[derived]** Per connection, the GC heap must hold a contiguous ~16.4 KB input buffer, a ~4.1 KB output buffer, the
  ssl context and transient handshake state. The CircuitPython gdb figure of 32.6 KB per connection is the closest
  measurement on the same chip.

**Examples**
- **pico-examples** (0d62f75, 2026-09-03) has **no TLS server example**, only `pico_w/wifi/tls_client`.
  Verified by listing `pico_w/wifi`: https://github.com/raspberrypi/pico-examples/tree/master/pico_w/wifi
- **ams1/pico_https** is a C (pico-sdk + mbedTLS) HTTPS/WebSocket TLS server for the Pico, last commit 2024-02-28.
  It ships RSA or EC cert scripts. Its README has no timing or memory figures:
  https://github.com/ams1/pico_https

---

## 2. mbedTLS speed on Cortex-M0+

**Measured on the RP2040.** rojinc/pqc-cortex-m0-benchmark, repo last commit 2026-10-13. Companion paper:
arXiv 2603.19340 (https://arxiv.org/html/2603.19340v4). Repo: https://github.com/rojinc/pqc-cortex-m0-benchmark

Conditions: RP2040 at 125 MHz (the README corrects an earlier 133 MHz label), `-O3`, pico-sdk 2.2.0's
`pico_mbedtls`, custom `mbedtls_config.h` with `MBEDTLS_ECP_NIST_OPTIM`, and no `MBEDTLS_HAVE_ASM`. The
fixed-point/window options are left at mbedTLS defaults; their values were not checked in this research.
- **[measured]** Mean timings:

  | Operation | Mean time |
  |---|---|
  | ECDSA P-256 keygen | 83.6 ms |
  | ECDSA P-256 sign | 92.6 ms |
  | ECDSA P-256 verify | 321.4 ms |
  | ECDH P-256 "key agreement" (see below) | 617.0 ms |
  | RSA-2048 public ("encrypt") | 139.7 ms |
  | RSA-2048 private ("decrypt", PKCS#1 v1.5) | 3.39 s |
  | RSA-2048 keygen | about 216 s (215,611,503 µs) |

  - The ECDH figure is **both** sides of an exchange: two key generations plus two shared-secret computations
    (`src/bench_classical.c`, `do_ecdh_key_agreement`).
  - The README says absolute latencies are 4–16 % higher at `-Os`.
- **[derived]** Server-side public-key work per full TLS 1.2 handshake on the RP2040:
  - **ECDHE-ECDSA (P-256 cert):** ephemeral keygen ≈ 84 ms + ECDSA sign ≈ 93 ms + one ECDH shared secret
    ≈ (617 − 2×84)/2 ≈ 225 ms, so **≈ 0.4 s of CPU**.
  - **ECDHE-RSA (RSA-2048 cert):** ≈ 3.39 s + ≈ 0.31 s, so **≈ 3.7 s of CPU**.
  - Not a measurement. It excludes SHA, AES-GCM, network RTTs and MicroPython overhead, and MicroPython's own build
    flags may differ from `-O3`. The RSA estimate agrees with the forum's "~3 s with RSA-2048" (section 1).

**Other Cortex-M0 data**
- **p256-m** (mbedTLS maintainer's minimal P-256): https://github.com/mpg/p256-m
  - **[measured, by the author]** on a Cortex-M0 at 48 MHz (STM32F091, GCC with inline asm): keygen 921 ms,
    ECDH 922 ms, ECDSA sign 990 ms, verify 1976 ms. On a Cortex-M4 at 100 MHz: sign 155 ms.
  - Stack is about 600–750 bytes and code under 3 KiB. A different library from mbedTLS ECP.
- **An mbedTLS-optimisation measurement in MicroPython itself, not on M0+.** Commits 5e2b2ee24 and 9e348d293 (master,
  2026-10-13): https://github.com/micropython/micropython/commit/9e348d293
  - **[measured, by Kwabena Agyeman]** on an Alif AE3 Cortex-M55 at 400 MHz, a client handshake with cert
    verification: P-256 only 2278 ms; X25519 1690 ms; + `MBEDTLS_ECP_NIST_OPTIM` 454 ms; + `MBEDTLS_HAVE_ASM` 419 ms.
  - Shows NIST_OPTIM is the big lever. rp2 already had it in v1.29.0; HAVE_ASM is new on master.
- **An often-cited comparison that is NOT RP2040.** arduino-pico's BearSSL server doc:
  https://raw.githubusercontent.com/earlephilhower/arduino-pico/master/docs/bearssl-server-secure-class.rst
  - **[measured]** "EC key of 256 bits, a request taking ~360ms without caching takes ~60ms with caching". RSA-2048:
    "~1850ms … ~70ms with caching".
  - The doc states these were "with an ESP8266 with it's clock set at 160MHz". Some search summaries wrongly attribute
    them to the RP2040.
- I did not find a published `mbedtls/programs/test/benchmark` run on an RP2040 or other M0+, nor a measured full
  server-side ECDHE-ECDSA handshake time under MicroPython on a Pico W.

---

## 3. Browser requirements (2026) for a self-signed LAN certificate

**subjectAltName / IP SAN**
- Chrome stopped matching the Common Name in Chrome 58 (2017). A certificate reached by IP needs an `IP:` SAN entry,
  or Chrome reports `NET::ERR_CERT_COMMON_NAME_INVALID`. These are secondary sources **(search summary only)**:
  https://www.ssdnodes.com/learn/lang/it/self-signed-certificate-ubuntu and
  https://community.fortinet.com/fortimanager-27/technical-tip-common-name-invalid-error-for-self-signed-certificate-used-for-device-access-226087
  - The Chromium primary source (chromestatus) could not be fetched.
- Apple "Requirements for trusted certificates in iOS 13 and macOS 10.15" (HT210176): https://support.apple.com/103769
  **(search summary only)**
  - SAN required (the CN is no longer trusted), RSA ≥ 2048, SHA-2 signatures.
  - **825-day maximum validity** for TLS server certs issued after 2019-07-01, and EKU id-kp-serverAuth. The EKU
    point was not confirmed by the summaries; secondary source: https://redmine.pfsense.org/issues/9825
- Apple's 398-day limit "affects only TLS server certificates issued from the Root CAs preinstalled", not user- or
  admin-added roots: https://support.apple.com/en-qa/102028 **(search summary only)**
  - An Apple engineer on the developer forum says private roots "do have to be under 825 days":
    https://developer.apple.com/forums/thread/130039
- I found no source saying Chrome or Firefox enforce a maximum validity on self-signed or locally trusted leaf
  certificates. The 398-day and shrinking CA/B Forum limits concern publicly trusted CAs; that was not separately
  verified here.

**Key types and TLS 1.2 suites**
- **Chrome** (`net/socket/ssl_client_socket_impl.cc`, Chromium main, read 2026-11-15):
  https://raw.githubusercontent.com/chromium/chromium/main/net/socket/ssl_client_socket_impl.cc
  - The cipher string is `"ALL:!aPSK:!ECDSA+SHA1:!3DES"`, plus `!kRSA` when `require_ecdhe`, with the comment
    "TLS versions before TLS 1.2 are no longer supported".
  - So TLS 1.2 `ECDHE-ECDSA-AES128-GCM-SHA256` is offered.
  - The verify prefs include `SSL_SIGN_ECDSA_SECP256R1_SHA256` and `SSL_SIGN_RSA_PKCS1_SHA256`, and SHA-1 server
    signatures are disabled.
- **All browsers.** No browser plans to drop TLS 1.2 were found; TLS 1.0/1.1 were removed in 2020:
  https://bugzilla.mozilla.org/show_bug.cgi?id=1880709 and
  https://groups.google.com/a/chromium.org/g/blink-dev/c/EHSnAn2rucg/m/L7C_KaQ8BAAJ **(search summary only)**
  - The Firefox and Safari cipher lists were not verified from source in this research.
- **Shelly's KB** recommends P-256 for its device web UI: "smaller keys and faster handshakes on constrained devices".
  https://kb.shelly.cloud/knowledge-base/kbsa-shelly-tls-supported-certs-config **(search summary only)**

**"Proceed anyway" exception behaviour**
- **Chrome** (`components/security_interstitials/content/stateful_ssl_host_state_delegate.cc`, main, 2026-11-15):
  https://raw.githubusercontent.com/chromium/chromium/main/components/security_interstitials/content/stateful_ssl_host_state_delegate.cc
  **[source]**
  - `kCertErrorBypassExpirationInSeconds = UINT64_C(604800)`: the decision is "remembered for one week".
  - It is keyed per host, with the key `error + base64(SHA-256 chain fingerprint)`. **A changed certificate on the same
    host shows the interstitial again.**
  - Decisions for non-default storage partitions are held in memory only.
- **Firefox** (`security/manager/ssl/nsCertOverrideService.cpp`, main, 2026-11-15):
  https://raw.githubusercontent.com/mozilla-firefox/firefox/main/security/manager/ssl/nsCertOverrideService.cpp
  **[source]**
  - A permanent exception is stored in `cert_override.txt`, keyed by host:port and origin attributes, holding the
    certificate's SHA-256 fingerprint (temporary ones are never written).
  - The lookup returns true only if `settings->mFingerprint.Equals(fpStr)`. **A changed certificate warns again.**
- **Safari:** no primary source on exception persistence was found.
- **Consequence:** any scheme that changes the certificate, such as regeneration on IP change or a reflash with a new
  build-time cert, makes every browser warn again. Chrome also re-asks weekly even with an unchanged certificate.

**Max Fragment Length (RFC 6066) / Record Size Limit (RFC 8449)**
- **Chrome/BoringSSL implements neither.** BoringSSL `ssl/extensions.cc`'s `kExtensions` table (main, 2026-11-15)
  contains no max_fragment_length or record_size_limit entry. Its 31 entries run from server_name through
  server_padding. https://raw.githubusercontent.com/google/boringssl/main/ssl/extensions.cc **[source]**
- **Firefox:** third-party ClientHello-mimicry projects report that Firefox sends `record_size_limit` = 16385
  (0x4001): https://github.com/apify/impit/pull/578 and https://github.com/bywayhq/btls/pull/3 **[claimed]**
  - 16385 is the TLS 1.3 maximum, so it would not shrink anything.
  - Firefox's `nsNSSIOLayer.cpp` does not set it (source checked); where NSS enables it was not traced.
  - No source was found showing any browser sends max_fragment_length.
- **The servers can't shrink it themselves.**
  - RFC 8449 says MFL was designed for constrained *clients* and that constrained servers cannot limit record sizes
    when clients don't deploy it: https://www.rfc-editor.org/rfc/rfc8449.html
  - The arduino-pico doc: "servers cannot request a buffer size from the client".
  - mbedTLS's `MBEDTLS_SSL_RECORD_SIZE_LIMIT` is documented as TLS 1.3 only:
    https://pigweed.googlesource.com/third_party/github/ARMmbed/mbedtls/+/a9bdc8fbb8b26112115b9fd735bd2c1226d52db5/ChangeLog.d/add-record-size-limit-extension-support.txt
    **(search summary only)**
  - MicroPython v1.29.0 has TLS 1.3 off and neither option enabled (section 0).
- **Conclusion: a device serving browsers must keep a 16 KB receive buffer.** Only the 4 KB *send* buffer is already
  reduced, which needs no peer cooperation.

**Related browser change**
- Chrome 154 (October 2026) turns on "Always Use Secure Connections" by default for *public* sites. Private
  addresses, meaning local IPs and single-label hostnames, are excluded **(search summary only)**:
  https://ppc.land/chrome-enforces-secure-connections-by-default-in-october-2026/ and
  https://chromium.googlesource.com/chromium/src/+show/main/docs/security/ask-before-http/ask-before-http-adoption-guide.md
  - Plain HTTP to a LAN IP therefore does not get the new interstitial.

---

## 4. How comparable devices handle HTTPS

- **Shelly Gen2/Gen3/Gen4**: the user uploads the certificate.
  - HTTPS for the local web UI exists from firmware 1.8.0 on Gen3+, per Shelly's KB, or 2.0.0, per its API docs and
    the HA guide.
  - The certificate and **unencrypted** key are uploaded via RPC `Shelly.PutHTTPServerCert` / `Shelly.PutHTTPServerKey`,
    plus `PutHTTPServerCABundle`.
  - Accepted keys: RSA-2048 and ECDSA P-256/384/521. Ed25519 and encrypted keys are not. TLS 1.2, with conflicting
    statements on 1.3.
  - Firmware 2.0+ devices ship **no factory certificate** and serve plain HTTP until the user uploads one.
  - Sources **(search summary only)**:
    https://shelly-api-docs.shelly.cloud/gen2/General/CustomHTTPSCertificates/,
    https://kb.shelly.cloud/knowledge-base/kbsa-shelly-tls-supported-certs-config and
    https://shelly.guide/en/home-assistant/integration/
  - Their docs note that other Shelly devices calling a self-signed device over HTTPS "will be rejected with a TLS
    verification error".
  - Third-party tool: caddy issues and renews the cert, then uploads it over RPC: https://github.com/BdN3504/shelly-caddy-tls
- **ESPHome**: no TLS on the device web server.
  - The docs (esphome.io at 6615ae7, 2026-11-13) describe the `web_server` as plain HTTP with optional basic/digest
    `auth:`: https://esphome.io/components/web_server/
  - Its threat model: "exposes a plain HTTP interface" and recommends "keeping devices on a trusted, segmented network":
    https://github.com/esphome/esphome/blob/dev/THREAT_MODEL.md
  - The native API uses Noise `NNpsk0` with a 32-byte pre-shared key instead of TLS and certificates:
    https://esphome.io/components/api/ (docs source `src/content/docs/components/api.mdx`)
- **Tasmota**: the docs (tasmota/docs at 75341eb, 2026-11-14) cover TLS only for client roles. MQTT uses BearSSL
  with fingerprint or CA validation (https://tasmota.github.io/docs/TLS), and the Berry `webclient` runs in "insecure"
  mode. No on-device HTTPS web server is documented; none was found.
- **WLED**: no HTTPS. Its docs recommend a VPN or a reverse proxy terminating HTTPS: https://kno.wled.ge/advanced/access-over-internet/
  - **[claimed, community]** ESP32 "not fast enough" and short of space: https://wled.discourse.group/t/making-wled-addressable-via-https/5948
- **Home Assistant**: certificates are provided by the user.
  - `http:` takes `ssl_certificate` / `ssl_key` file paths, from Let's Encrypt or a self-signed cert per the cookbook:
    https://www.home-assistant.io/cookbook/tls_self_signed_certificate/
  - A restart is required to load a new certificate.
- **openHAB HTTP binding** (openhab-addons at 1593348, 2026-11-15, `bundles/org.openhab.binding.http`) **[source]**:
  - The thing option `ignoreSSLErrors` (default false) is documented as "ignores invalid SSL certificate errors.
    This is potentially dangerous."
  - In code, `HttpThingHandler` switches between `httpClientProvider.getSecureClient()` and `getInsecureClient()`.
  - There is **no per-device certificate pinning**. openHAB either validates against the JVM trust store, which
    means importing the device's cert or CA, or accepts any certificate.
  - Community: https://community.openhab.org/t/disable-ssl-certificate-checking-on-http-binding/101887
  - **[claimed, community]** JS-rule `actions.HTTP` has no equivalent switch:
    https://community.openhab.org/t/after-upgrading-from-openhab-5-1-3-to-5-2-0-a-js-rule-that-talks-directly-to-my-philips-hue-bridge-over-its-local-https-api-not-via-the-official-hue-binding-started-failing-with/169868
- **ESP32 community library precedent for on-device generation**: fhessel/esp32_https_server has an example that
  generates a self-signed certificate on the ESP at sketch start:
  https://awesome.ecosyste.ms/api/v1/projects/github.com%2Ffhessel%2Fesp32_https_server **(search summary only)**

Pattern across the established devices: either no HTTPS at all (ESPHome, Tasmota, WLED), or a certificate uploaded by
the user with no factory certificate (Shelly 2.x, Home Assistant). None of the products surveyed was found to generate
a certificate on the device at first boot.

---

## 5. Generating a key and a self-signed X.509 certificate on a MicroPython device

- **Stock MicroPython v1.29.0 cannot do it.**
  - The `tls`/`ssl` module has no key-generation or certificate-writing API (`modtls_mbedtls.c` locals table:
    `load_cert_chain`, `load_verify_locations`, `get_ciphers`, `set_ciphers`, `wrap_socket`).
  - The required mbedTLS modules (`PK_WRITE_C`, `X509_CRT_WRITE_C`, `X509_CREATE_C`) are not compiled in (section 0).
  - `cryptolib` offers only AES.
  - **[source]**
- **dmazzella/ucryptography**, a user C module over the port's mbedTLS, last commit 2026-08-14:
  https://github.com/dmazzella/ucryptography
  - The README lists rp2 among supported ports. It implements `ec.generate_private_key` (SECP256R1/384R1/521R1),
    `rsa.generate_private_key` and `x509.CertificateBuilder`.
  - CertificateBuilder supports SubjectAlternativeName with `IPAddress`/`DNSName`, ExtendedKeyUsage, BasicConstraints
    and KeyUsage, using `mbedtls_x509write_crt_*`.
  - Feature toggles `X509_CREATE=0` drop `MBEDTLS_X509_CREATE_C` + `MBEDTLS_X509_CRT_WRITE_C`. The README earlier
    said it needs a patch to `extmod/mbedtls/mbedtls_config_common.h` (search summary); the current README documents
    compile-time toggles.
  - Build instructions are shown for unix, ESP32 and STM32, not rp2. No timing figures are published.
- **Carglglz/mpy-mbedtls**, last commit 2024-04-02: https://github.com/Carglglz/mpy-mbedtls
  - Implements EC key generation (`mbedtls_ecp_gen_key`), PEM/DER key export (`mbedtls_pk_write_*`), ECDH and a
    **CSR** writer (`mbedtls_x509write_csr`). It has **no self-signed certificate writer**.
  - Ships a `ports/rp2/mbedtls_config.h`.
- **No pure-Python X.509/ASN.1 builder for MicroPython** was found.
- **Expected speed on the RP2040**, from the benchmarks in section 2 rather than any on-device certificate-generation
  report:
  - **[measured, mbedTLS, pico-sdk, -O3]** EC P-256 keygen ≈ 84 ms and the certificate signature ≈ 93 ms, so a P-256
    self-signed certificate is roughly 0.2 s of CPU **[derived]**.
  - **[measured]** RSA-2048 keygen averages about 216 s, which is impractical, and longer than the RP2040's 8.39 s
    watchdog maximum if run unbroken.
- **Entropy on the device:** rp2 builds with `MBEDTLS_ENTROPY_HARDWARE_ALT`. The rp2 `mbedtls_hardware_poll`
  implementation was not located or verified in this research, so the source of key-generation entropy is an open point.
- **No open or merged PR adds key or certificate generation to MicroPython's ssl/tls/cryptolib** up to 2026-11-15.
  - GitHub search of micropython/micropython PRs for x509 and certificate generation found none, only old
    cert-loading fixes such as #14385 and #15657.
  - Closed WIP PR #19449 (2026-07-09), "Add machine.RTC.set_build_date() function for TLS cert checks", concerns
    validity checking, not creation.

---

## 6. Microdot TLS support (v2.7.0)

- **There is no TLS "addon".** TLS is a built-in `ssl=` argument to `Microdot.run()` and `start_server()`, which takes
  an `SSLContext` (`src/microdot/microdot.py`: `start_server(..., ssl=None, ...)` around line 1237, and
  `run(..., ssl=None)` around line 1334).
- The old `microdot_ssl.py` extension "was only used with the synchronous web server … and has been removed"
  (`docs/implementation/migrating.rst`).
- Docs (`docs/users-guide/intro.rst` at v2.7.0): "``ssl``: an ``SSLContext`` instance that configures the server to use
  TLS encryption", with the example `sslctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);
  sslctx.load_cert_chain('cert.pem', 'key.pem'); app.run(port=4443, debug=True, ssl=sslctx)`.
  - It adds the note "When using MicroPython, these files must be given in DER format."
  - That note predates MicroPython 1.29.0's PEM support (section 0). DER remains valid and avoids base64 decoding.
- **`examples/tls/`** holds `hello.py` and `README.md`:
  https://github.com/miguelgrinberg/microdot/tree/main/examples/tls
  - It picks `cert.der`/`key.der` on MicroPython and `.pem` on CPython.
  - It suggests `openssl req -x509 -newkey rsa:4096 -nodes -out cert.pem -keyout key.pem -days 365`, then
    `openssl x509 … -outform DER` / `openssl rsa … -outform DER`.
  - RSA-4096 has no IP SAN and is very slow on an RP2040 (section 2).
  - Discussion #13534 (2024-01, v1.22) reports `ValueError: invalid key` with a converted RSA key and success with
    an EC prime256v1 key: https://github.com/orgs/micropython/discussions/13534
- **No keep-alive.** One request per connection (section 0), so each HTTPS request is a full handshake on MicroPython.
- **Microdot issues about TLS:**
  - #160, "Microdot + ssl socket connection" (2023-07 to 2024-01; ESP32; ENOMEM; closed after 1.22 verification):
    https://github.com/miguelgrinberg/microdot/issues/160
  - #34, secure WebSocket (2022).
  - No Microdot issue about TLS on Pico W was found:
    https://github.com/miguelgrinberg/microdot/issues?q=is%3Aissue+ssl

---

## 7. MicroPython after v1.29.0 (as of 2026-11-15)

- **No newer stable release.** `git ls-remote --tags` (2026-11-15) shows `v1.29.0` (commit dated 2026-08-24) as the
  newest release tag. `v1.30.0-preview` (2026-08-25) only marks the start of the next development cycle, and there is
  no v1.29.1.
- **TLS-relevant commits on master since v1.29.0** (none of them in a tag yet):
  - 9ee1531b5 (2026-10-02): close the transport on a fatal handshake failure (the socket leak in section 0):
    https://github.com/micropython/micropython/commit/9ee1531b5
  - 5e2b2ee24 (2026-10-13): enable X25519 in the common mbedTLS config:
    https://github.com/micropython/micropython/commit/5e2b2ee24
  - 9e348d293 (2026-10-13): enable `MBEDTLS_HAVE_ASM` and `MBEDTLS_ECP_NIST_OPTIM` for all bare-metal ports, rp2
    included (rp2's own NIST_OPTIM line removed). Measured on an M55 only, figures in section 2:
    https://github.com/micropython/micropython/commit/9e348d293
  - 19e685eca: remove support for mbedTLS < 3.0; the submodule is v3.6.6.
  - modlwip, relevant to listener/socket behaviour:
    - 6e79dcf9c "Poll the stack while waiting for TCP send memory".
    - 6cd9f5c2c (2026-10-27) "Don't clear err and recv callbacks of a listening pcb".
- **Open PRs**
  - #19797 (projectgus, draft, 2026-10-22): mbedTLS 3.6.6 → 4.2, tested on rp2, stm32 and unix. It does not mention
    TLS 1.3, RAM or speed. The author notes "all support may stop in April 2027" for mbedTLS:
    https://github.com/micropython/micropython/pull/19797
  - #12780 (open since 2023, milestone release-1.30): SSLSession, i.e. **client-side** session resumption. Server-side
    tickets only appear in the Unix-port test.
    **[measured, by the author]** 1829 ms → 919 ms on resumption; board not named:
    https://github.com/micropython/micropython/pull/12780
- **Not found:** no enabling of TLS 1.3 on rp2, no server-side session cache or tickets, no new non-blocking handshake
  mechanism (the deferred handshake already exists), and no TLS memory reduction.

---

## Gaps (not found or not verifiable here)
- A measured MicroPython-on-Pico-W TLS *server* handshake time with ECDSA P-256, measured RAM per connection under
  MicroPython 1.2x, and the number of concurrent TLS connections that work.
- An mbedTLS `benchmark` program run on an RP2040 or other M0+, and MicroPython rp2's mbedTLS compiler flags.
- Safari's exception persistence, the Firefox/Safari cipher lists from source, and whether Safari enforces the
  825-day rule on a self-signed leaf the user clicked through.
- Where NSS/Firefox enables `record_size_limit` (third-party claim only).
- The rp2 entropy source behind `MBEDTLS_ENTROPY_HARDWARE_ALT` at v1.29.0.
- Primary pages that could not be fetched: the Raspberry Pi forum threads, Apple support pages, chromestatus, Shelly
  API docs and the IETF slides.
