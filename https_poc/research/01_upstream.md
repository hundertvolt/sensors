# HTTPS server on MicroPython v1.29.0 / Pico W: upstream research

**Raw report (2026-11-15)**, written by a research subagent and condensed into `../RESEARCH.md`, which re-checked the
claims its conclusions rest on. `<scratch>` paths name the research session's temporary space; the scripts and
clones there were not kept.

Scope: research only, nothing in /home/user/sensors changed. Clones (data, read only; only MicroPython's
own Unix port was built and run) under
`<scratch>/upstream/`.

Pinned sources:

- MicroPython `v1.29.0`: annotated tag object `23f16c8a0939d43736fa481227dffef984cbec7b`, which
  dereferences to commit `0fd6c573ea815774668bbb16b8e197c8822368b2` ("all: Bump version to 1.29.0",
  2026-08-24). Paths below are relative to the micropython checkout unless prefixed.
- `lib/mbedtls` submodule at `0bebf8b8c7f07abe3571ded48a11aa907a1ffb20` = **Mbed TLS 3.6.6**
  (`lib/mbedtls/include/mbedtls/build_info.h:36-37`, `MBEDTLS_VERSION_NUMBER 0x03060600`; the running
  Unix port reports `tls.MBEDTLS_VERSION == 'Mbed TLS 3.6.6'`).
- `lib/micropython-lib` at `ee4bb8ff139e24c42b739935fbd8ec7c4d061e02`; `lib/pico-sdk` at
  `98a542c1a62fb549ffb5d66a3e5892b06276b670` (fetched only to read `pico_rand`).
- Microdot `v2.7.0` = commit `7742db9ff9f49635de3387145fafe56bf2377a97`; its `src/microdot/microdot.py`
  is byte-identical to the project's `ext/microdot.py` (checked with `diff -q`).

mbedTLS replaces its whole default config when `MBEDTLS_CONFIG_FILE` is set
(`extmod/extmod.cmake:254-259` points it at `ports/<port>/mbedtls/mbedtls_config_port.h`), so **any
option not defined in the three headers below is off**; the only defaults that still apply are the
in-header fallbacks (`MBEDTLS_ECP_WINDOW_SIZE` etc., item 3).

---------------------------------------------------------------------------------------------------

## 1. Checkout and mbedTLS version

`git clone --depth 1 --branch v1.29.0 https://github.com/micropython/micropython`, then
`git submodule update --init --depth 1 lib/mbedtls lib/micropython-lib`; `make -C ports/unix
submodules` added what the Unix build needs. mbedTLS **3.6.6** (above).

## 2. `extmod/modtls_mbedtls.c`

**Objects and where their memory lives.**
- `SSLContext` is one GC object (`mp_obj_malloc[_with_finaliser]`, `:283-287`) that embeds the
  `mbedtls_entropy_context`, `mbedtls_ctr_drbg_context`, `mbedtls_ssl_config`, two `mbedtls_x509_crt`
  and the `mbedtls_pk_context` inline (`:85-108`). Everything mbedTLS allocates behind those
  (parsed cert, key MPIs, record buffers, handshake state) goes through `mbedtls_calloc`, which on rp2
  is the MicroPython GC heap (item 3).
- `SSLSocket` is one GC object embedding the `mbedtls_ssl_context` (`:111-125`, allocated at
  `:755-759`).

**Server side.** `PROTOCOL_TLS_SERVER = MP_ENDPOINT_IS_SERVER` (`:76-82`, exported `:1131-1132`);
`ssl_context_make_new` selects `MBEDTLS_SSL_IS_SERVER` from the protocol (`:279`), seeds CTR-DRBG
from `mbedtls_entropy_func` with the fixed personalisation `"mpy"` (`:318-322`), applies
`MBEDTLS_SSL_PRESET_DEFAULT` (`:324-325`).

**Verify modes.** Server default `MBEDTLS_SSL_VERIFY_NONE`, client default `VERIFY_REQUIRED`
(`:330-335`); `verify_mode` is settable (`:391-394`); constants `CERT_NONE/OPTIONAL/REQUIRED`
(`:1137-1139`). A server can therefore request client certificates (`CERT_REQUIRED` +
`load_verify_locations`, `:517-535`). An optional Python `verify_callback` is called per cert
(`:260-268`). micropython-lib's `ssl.SSLContext` forces `CERT_NONE` on every context it creates
(`lib/micropython-lib/python-stdlib/ssl/ssl.py:8`).

**`load_cert_chain(cert, key)`** (`:509-515` -> `ssl_context_load_key`, `:483-507`):
- Takes the **data** (bytes/str), not a path; the path form is micropython-lib's `ssl.py:18-25`, which
  reads the files into bytes first.
- **PEM and DER are both accepted**: `asn1_get_data()` (`:147-162`) passes DER as-is and adds the
  terminating NUL to the length when it finds `-----BEGIN ` (PEM parsing is compiled in:
  `MBEDTLS_PEM_PARSE_C`, `extmod/mbedtls/mbedtls_config_common.h:84`). Measured: DER and PEM, EC and
  RSA, all four work (item Part 2).
- Key: `mbedtls_pk_parse_key(..., NULL, 0, ctr_drbg)` (`:487-491`), no password; any key type the PK
  layer parses: RSA (`MBEDTLS_RSA_C`, `MBEDTLS_PKCS1_V15`, config `:90`, `:55`) and EC
  (`MBEDTLS_PK_HAVE_ECC_KEYS`, `MBEDTLS_ECP_C`, `:87`, `:77`) on the enabled curves (item 3). Every
  parse error is collapsed to `ValueError("invalid key")` / `ValueError("invalid cert")`
  (`:492-501`, mapping `:168-172`).
- Cert: `mbedtls_x509_crt_parse` (`:498`); for DER it copies the input (`mbedtls_x509_crt_parse_der`
  -> `make_copy = 1`, `lib/mbedtls/library/x509_crt.c:1383-1388`, copy at `:1115`); a PEM input with
  several certificates yields a chain. `mbedtls_ssl_conf_own_cert` (`:503`).
- So the Python bytes are not referenced afterwards and can be dropped; measured retained cost in
  Part 2.

**Handshake and non-blocking operation.**
- `wrap_socket(sock, server_side=, do_handshake_on_connect=True, server_hostname=)` (`:626-652`).
  `ssl_socket_make_new` calls `mbedtls_ssl_setup` (`:770`) - this is where the record buffers are
  allocated (item 3) - and `mbedtls_ssl_set_bio` with MicroPython-stream send/recv callbacks
  (`:816`). On a non-bare-metal port a failed setup is retried after `gc_collect()`; rp2 is bare-metal,
  so there is no retry (`:771-780`, rp2 sets `MICROPY_MBEDTLS_CONFIG_BARE_METAL (1)`,
  `ports/rp2/mbedtls/mbedtls_config_port.h:39`).
- `do_handshake_on_connect=True` loops `mbedtls_ssl_handshake` with `mp_event_wait_ms(1)` until done
  (`:818-825`) - blocking. With `False` (what asyncio uses, item 5) the handshake is driven lazily by
  the first `read`/`write`: `socket_read` -> `mbedtls_ssl_read` (`:888`), `socket_write` ->
  `mbedtls_ssl_write` (`:932`). mbedTLS's `mbedtls_ssl_read` runs `mbedtls_ssl_handshake()` while the
  handshake is not over (`lib/mbedtls/library/ssl_msg.c:6027-6028`), and `mbedtls_ssl_handshake` loops
  `mbedtls_ssl_handshake_step` until HANDSHAKE_OVER or any non-zero return
  (`lib/mbedtls/library/ssl_tls.c:4673-4679`).
- The BIO callbacks map EAGAIN to `MBEDTLS_ERR_SSL_WANT_READ/WRITE` (`:678-711`); `socket_read/write`
  map WANT_READ/WANT_WRITE to `MP_EWOULDBLOCK` and record in `poll_mask` which direction the protocol
  needs next (`:896-903`, `:936-943`); `ioctl(POLL)` substitutes that direction and reports pending
  decrypted data via `mbedtls_ssl_check_pending` (`:978-1025`). TLS 1.3 new-session-ticket handling
  (`:904-911`) is compiled out (no TLS 1.3).
- **Consequence: the expensive crypto runs inside single uninterrupted C calls.** The only points
  where the server handshake returns to Python are socket EAGAINs. Server state machine
  (`lib/mbedtls/library/ssl_tls12_server.c:4190-4275`): after the ClientHello arrives, one
  `mbedtls_ssl_read` call executes ServerHello, Certificate, **ServerKeyExchange** (ECDHE
  `mbedtls_ecdh_setup` + `mbedtls_ecdh_make_params` = ephemeral key generation, `:2950-2962`, then the
  signature `mbedtls_pk_sign`, `:3094-3100`) and ServerHelloDone, then stops at WANT_READ for the
  client's flight. The next call, once ClientKeyExchange/CCS/Finished arrive, executes
  **`mbedtls_ecdh_calc_secret`** (`:3675-3680`) - or for static-RSA suites `mbedtls_pk_decrypt`
  (`:3387-3389`) - key derivation, both Finished messages. Each of the two is one no-yield C call.
  Measured structure (Part 2): exactly two loop-blocking segments per handshake.
- Restartable ECC (coordinator question 1): `MBEDTLS_ECP_RESTARTABLE` is **not defined** in any of
  MicroPython's three config headers, and mbedTLS's own description limits its TLS effect to
  **"TLS 1.2 clients (not servers) when using the ECDHE-ECDSA key exchange"**
  (`lib/mbedtls/include/mbedtls/mbedtls_config.h:787-839`, the client/server sentence at `:811-819`);
  the internal switch `MBEDTLS_SSL_ECP_RESTARTABLE_ENABLED` requires `MBEDTLS_SSL_CLI_C`
  (`lib/mbedtls/library/ssl_misc.h:57-61`); `ssl_tls12_server.c` contains no `rs_ctx`/restart code
  (grep: 0 hits, vs 21 in `ssl_tls12_client.c`), and the server call sites above use the
  non-restartable `mbedtls_ecdh_make_params`/`mbedtls_pk_sign`/`mbedtls_ecdh_calc_secret`.
  `modtls_mbedtls.c` never references `MBEDTLS_ERR_SSL_CRYPTO_IN_PROGRESS` (grep: 0 hits). So even a
  custom build enabling it would not split the server's ECC work in 3.6.6.

**Record buffers** (sizes in item 3): allocated per `SSLSocket` in `mbedtls_ssl_setup`
(`lib/mbedtls/library/ssl_tls.c:1387-1425`: `in_buf = mbedtls_calloc(1, MBEDTLS_SSL_IN_BUFFER_LEN)`,
`out_buf = mbedtls_calloc(1, MBEDTLS_SSL_OUT_BUFFER_LEN)`), i.e. at `wrap_socket` time, before the
first handshake byte. Freed by `mbedtls_ssl_free` on close (`:968-977`) or on handshake failure
(`:254-255`); measured: no growth after closed sessions (Part 2).

**Session cache / tickets** (coordinator question 2): `modtls_mbedtls.c` calls neither
`mbedtls_ssl_conf_session_cache` nor `mbedtls_ssl_conf_session_tickets_cb`/`mbedtls_ssl_ticket_setup`
(grep for `session_cache`, `ticket`, `session_tickets`: the only hit is the TLS 1.3 comment at `:906`),
and `MBEDTLS_SSL_CACHE_C`, `MBEDTLS_SSL_TICKET_C`, `MBEDTLS_SSL_SESSION_TICKETS` are not defined
(item 3). The server's resumption paths are gated on those callbacks: ticket parsing returns early
when `conf->f_ticket_parse == NULL` (`ssl_tls12_server.c:470-503`), cache lookup when
`conf->f_get_cache == NULL` (`:1985-2003`). **Every connection pays a full handshake.**

**ALPN / SNI.** `MBEDTLS_SSL_ALPN` is off (item 3) - no ALPN, so no HTTP/2 negotiation.
`MBEDTLS_SSL_SERVER_NAME_INDICATION` is on (`mbedtls_config_common.h:60`) but `modtls_mbedtls.c`
only uses SNI as a client (`mbedtls_ssl_set_hostname`, `:785-790`) and never installs a server SNI
callback (`mbedtls_ssl_conf_sni` not referenced): one certificate for every host name
(`openssl s_client` reports "Can't use SSL_get_servername").

**Other server-relevant API.** `set_ciphers`/`get_ciphers` (`:441-481`); server PSK via
`server_psk_keys` (`:409-413`, `:596-623`; restricts to PSK suites, `:546-568`); `cipher()` returns
(suite, version) (`:865-874`); `getpeercert` exists only with `MBEDTLS_SSL_KEEP_PEER_CERTIFICATE`
(`:850-863`), which is off. Closing frees the mbedTLS state and closes the TCP socket **without
sending close_notify** (`:968-977` then `:1017`; no `mbedtls_ssl_close_notify` call anywhere) -
`openssl s_client` logs "unexpected eof while reading" after a complete response.

**Error mapping** (`mbedtls_raise_error`, `:164-211`): `MBEDTLS_ERR_SSL_ALLOC_FAILED` ->
`OSError(ENOMEM)` (`:166-167`); key/cert parse -> `ValueError`; codes in (-256, 0) are socket errnos
passed through BIO and re-raised as positive `OSError` (`:174-180`); everything else ->
`OSError(<negative mbedTLS code>, '<name string>')` (`:182-206`; strings come out as e.g.
`'MBEDTLS_ERR_SSL_FATAL_ALERT_MESSAGE'`). Through streams, errors go via
`MICROPY_STREAMS_DELEGATE_ERROR` (`py/mpconfig.h:1110-1111`, on at EXTRA_FEATURES) ->
`py/stream.c:111-120` -> `socket_ioctl(MP_STREAM_RAISE_ERROR)` (`:1004-1008`).

**Handshake-failure cleanup defect (verified by test).** `ssl_check_async_handshake_failure`
(`:220-258`) handles any negative code except `MBEDTLS_ERR_SSL_CONN_EOF` while the handshake is not
over: it sets `sslsock->sock = MP_OBJ_NULL` and frees the TLS state before raising (`:248-256`).
The later `close()` then hits `if (sock == MP_OBJ_NULL) return 0;` (`:972-975`) and **never closes
the underlying TCP socket**. Measured on the Unix port: after a client offered only TLS 1.3 (server
answers alert 40, `OSError(-28160, 'MBEDTLS_ERR_SSL_HANDSHAKE_FAILURE')`), the server-side TCP
connection stayed in CLOSE_WAIT at t+0, +1 s and +4 s (`/proc/net/tcp` state 08). The EOF case is
excluded from that path and does close normally (no lingering socket measured). On rp2 the lwIP socket
object has a finaliser (`extmod/modlwip.c:946`, `:1168`, `__del__ = close` at `:1719`), so the PCB is
released only when a later GC finds the orphaned socket object unreachable; on the Unix port's
`modsocket.c` there is no finaliser at all. Every client that rejects a self-signed certificate with a
fatal alert (rather than a plain close) or fails negotiation therefore leaves one TCP PCB alive until
the next collection on rp2.

## 3. mbedTLS configuration (rp2 vs unix)

`extmod/mbedtls/mbedtls_config_common.h` (shared), `ports/rp2/mbedtls/mbedtls_config_port.h`,
`ports/unix/mbedtls/mbedtls_config_port.h`.

| Item | State | Where |
|---|---|---|
| `MBEDTLS_SSL_SRV_C` | on | common `:97` |
| TLS 1.2 | on (`MBEDTLS_SSL_PROTO_TLS1_2`) | common `:59` |
| TLS 1.0/1.1 defines | present (`:57-58`) but no effect: 3.6.6 has no code for them (no reference in `library/` or `include/`) | |
| TLS 1.3 | **off** (`MBEDTLS_SSL_PROTO_TLS1_3` undefined); measured: TLS1.3-only client gets alert 40 | |
| Key exchanges | RSA, ECDHE-ECDSA, ECDHE-RSA, PSK | common `:49-52` |
| DHE-RSA, ECDH static | off | |
| Ciphers | AES (`:68`, ROM tables `:39`), GCM (`:80`), CBC (`:40`); CCM, ChaCha20/Poly1305 **off** | |
| Hashes | MD5, SHA1, SHA224, SHA256 (`MBEDTLS_SHA256_SMALLER` `:56`), SHA384, SHA512 | `:82-95` |
| Curves | secp192r1, 224r1, **256r1**, 384r1, 521r1, 192k1, 224k1, 256k1 | `:41-48` |
| x25519 / x448 / Brainpool | **off** | |
| ECDSA / ECDH / RSA | on (`:76`, `:75`, `:90`), `MBEDTLS_PK_CAN_ECDSA_SIGN` `:54`, PKCS#1 v1.5 only (`PKCS1_V21` off) | |
| `MBEDTLS_ECDSA_DETERMINISTIC`, `HMAC_DRBG_C` | off (randomised ECDSA with CTR-DRBG) | |
| `MBEDTLS_SSL_MAX_CONTENT_LEN` / `IN_CONTENT_LEN` | 16384 / 16384 | common `:63-64` |
| `MBEDTLS_SSL_OUT_CONTENT_LEN` | 4096 | common `:65` |
| `MBEDTLS_SSL_MAX_FRAGMENT_LENGTH` | off | |
| `MBEDTLS_SSL_VARIABLE_BUFFER_LENGTH` | off (buffers never shrink after handshake) | |
| `MBEDTLS_SSL_DTLS_CONNECTION_ID` | off | |
| DTLS | on, both rp2 and unix: `MICROPY_PY_SSL_DTLS` defaults on at `ROM_LEVEL >= EXTRA_FEATURES` (`py/mpconfig.h:2176-2177`; rp2 level `ports/rp2/mpconfigport.h:80-81`) -> `MBEDTLS_SSL_PROTO_DTLS` etc. (common `:102-107`) | |
| `MBEDTLS_ECP_NIST_OPTIM` | **rp2 only** (`rp2 :30`), not unix | |
| `MBEDTLS_ECP_FIXED_POINT_OPTIM` | 1 (header default, `include/mbedtls/ecp.h:307`) | |
| `MBEDTLS_ECP_WINDOW_SIZE` | 4 (header default, `ecp.h:291`) | |
| `MBEDTLS_MPI_WINDOW_SIZE` / `MPI_MAX_SIZE` | 3 / 1024 (`include/mbedtls/bignum.h:63`, `:74`) | |
| `MBEDTLS_ECP_RESTARTABLE` | off (item 2) | |
| `MBEDTLS_PK_WRITE_C`, `X509_CRT_WRITE_C`, `X509_CREATE_C`, `PEM_WRITE_C`, `GENPRIME` | **all off** | |
| `MBEDTLS_SSL_CACHE_C`, `SSL_TICKET_C`, `SSL_SESSION_TICKETS` | **all off** | |
| `MBEDTLS_SSL_ALPN`, `RENEGOTIATION`, `KEEP_PEER_CERTIFICATE` | off | |
| `MBEDTLS_SSL_EXTENDED_MASTER_SECRET`, `ENCRYPT_THEN_MAC` | off (whether any browser refuses TLS 1.2 without EMS was not verifiable from primary sources here; curl and openssl 3.0.13 connect) | |
| PSA (`PSA_CRYPTO_C`, `USE_PSA_CRYPTO`) | off | |
| `MBEDTLS_ERROR_C` | on (error strings, `:79`) | |
| `MBEDTLS_DEBUG_C` | off (`:31-33`) | |
| Unix-only | `MBEDTLS_CIPHER_MODE_CTR`, `MBEDTLS_TIMING_C` (`unix :30-33`) | |
| rp2-only | time hook `rp2_rtctime_seconds`, `mbedtls_ms_time` = seconds x 1000 (`rp2 :32-36`; `ports/rp2/mbedtls/mbedtls_port.c:38-49`, AON timer) | |

`diff` of the two port headers: rp2 adds `MBEDTLS_ECP_NIST_OPTIM`, the time hooks and
`MICROPY_MBEDTLS_CONFIG_BARE_METAL (1)` unconditionally; unix adds `CIPHER_MODE_CTR`, `TIMING_C`,
and sets BARE_METAL **only under `MICROPY_UNIX_COVERAGE`** (`unix :35-38`), then undoes the
hardware-entropy part (`unix :43-47`).

**Record buffer sizes** (`lib/mbedtls/library/ssl_misc.h`): CBC suites are compiled in, so
`MBEDTLS_SSL_MAC_ADD = 48` (SHA-384 HMAC, `:294-305`), `PADDING_ADD = 256` (`:307-311`),
`MAX_IV_LENGTH = 16` (`include/mbedtls/cipher.h:220`), CID expansion 0 (`:313-317`): payload overhead
320 (`:319-323`); header 13 (`:392`). **`in_buf` = 13 + 320 + 16384 = 16,717 B; `out_buf` = 13 + 320
+ 4096 = 4,429 B** (`:395-409`), each one `mbedtls_calloc` (`ssl_tls.c:1410`, `:1420`). The sibling's
figures are confirmed.

**Memory hooks.** BARE_METAL defines `MBEDTLS_PLATFORM_MEMORY` and maps
`MBEDTLS_PLATFORM_STD_CALLOC/FREE` to `m_tracked_calloc/m_tracked_free` (common `:110-127`). Without
`MBEDTLS_PLATFORM_MEMORY`, `mbedtls_calloc` is libc `calloc` (`include/mbedtls/platform.h:165-168`).
- **rp2: yes, GC heap.** BARE_METAL (rp2 `:39`), `MICROPY_TRACKED_ALLOC` on
  (`ports/rp2/mpconfigport.h:122`). `m_tracked_calloc` (`py/malloc.c:277-302`) calls
  `m_malloc_maybe` (= `gc_alloc(n, 0)`, `py/malloc.c:59`, `:99-100`) for a node of
  `{prev, next}` + data (`:239-246`; the size field exists only when GC is off, `:237`), links it
  into `MP_STATE_VM(m_tracked_head)` (`:287-294`), zeroes it. On rp2 the header is 8 B and GC blocks
  are 16 B (`py/mpconfig.h:251`), so `in_buf` occupies **1,046 contiguous blocks = 16,736 B** and
  `out_buf` **278 blocks = 4,448 B**. `m_tracked_head` sits in the scanned root range of
  `mp_state_vm` (`py/mpstate.h:181`, root range `py/gc.c:472-474`), and there is no "do not scan"
  allocation flag in this tree (no `SELECTIVE_COLLECT`/`DO_NOT_COLLECT` in `py/`), so every
  collection conservatively scans all live record buffers word by word.
  `m_malloc_maybe` returning NULL becomes `MBEDTLS_ERR_SSL_ALLOC_FAILED` -> `OSError(ENOMEM)`.
- **unix standard: no** - libc `calloc` (BARE_METAL undefined). **unix coverage variant: yes**
  (`ports/unix/variants/coverage/mpconfigvariant.mk:8` defines `MICROPY_UNIX_COVERAGE`), which is why
  Part 2 measures on that variant.
- Entropy on rp2: `MBEDTLS_ENTROPY_HARDWARE_ALT` + `MBEDTLS_NO_PLATFORM_ENTROPY` (common `:115-116`)
  -> `mbedtls_hardware_poll` = `mp_hal_get_random` (`extmod/mbedtls/mbedtls_alt.c:95-103`) ->
  `get_rand_64()` from pico-sdk `pico_rand` (`ports/rp2/mphalport.c:281-286`; item 7).

## 4. rp2 port: `ssl` / `tls` for RPI_PICO_W

- `MICROPY_SSL_MBEDTLS (1)` (`ports/rp2/mpconfigport.h:219`; CMake `ports/rp2/CMakeLists.txt:87`,
  mbedtls glue `:188`, `:496`, link `:527`), `MICROPY_PY_SSL (1)` by default (`mpconfigport.h:251-252`).
  The C module is `tls` (`modtls_mbedtls.c:1123-1148`).
- `ssl.py` comes from micropython-lib: `ports/rp2/boards/RPI_PICO_W/manifest.py` includes the port
  manifest and `require("bundle-networking")`, whose manifest has `require("ssl")`
  (`lib/micropython-lib/micropython/bundles/bundle-networking/manifest.py:8`) ->
  `python-stdlib/ssl/manifest.py:1-3` (`ssl.py`, version 0.2.1, frozen at `opt=3`). Whether the
  project's own firmware build keeps that manifest was not checked here (`toolchain/
  micropython_overrides.py:122` re-anchors `MICROPY_FROZEN_MANIFEST`); `tls` is present regardless.
- `ssl.py` (`python-stdlib/ssl/ssl.py`): `from tls import *` (`:1-2`); `SSLContext` wraps a
  `tls.SSLContext` and sets `verify_mode = CERT_NONE` (`:5-8`); `load_cert_chain` accepts a path
  (read into bytes) or bytes (`:18-25`); `load_verify_locations(cafile|cadata)` (`:27-31`);
  `wrap_socket` forwards `server_side`, `do_handshake_on_connect`, `server_hostname` (`:33-41`);
  module-level `wrap_socket` builds a context per call (`:44-65`). It adds one Python object; using
  `tls.SSLContext` directly works the same with `asyncio.start_server(ssl=...)`.
- `MICROPY_PY_SSL_ECDSA_SIGN_ALT` is not set for rp2 (only a make-port flag, `extmod/extmod.mk:252-253`).

## 5. `extmod/asyncio/stream.py`: `start_server(..., ssl=)`

- `start_server(cb, host, port, backlog=5, ssl=None)` (`:179-203`) creates the non-blocking listener
  and runs `Server._serve(s, cb, ssl)` as a task (`:192`).
- Accept loop (`:144-174`): wait readable (`:149`); `s.accept()` errors of any kind are swallowed
  (`:160-164`); with `ssl`, **`ssl.wrap_socket(s2, server_side=True, do_handshake_on_connect=False)`**
  (`:165-167`); `s2.setblocking(False)` (`:172`, delegated to the TCP socket by
  `modtls_mbedtls.c:952-959`); `Stream(s2, {"peername": addr})` and `create_task(cb(...))`
  (`:173-174`).
- **The handshake does not happen in the accept loop.** `wrap_socket` only allocates (the ~21 KB of
  record buffers + the SSLSocket object); the handshake runs inside the connection task's first
  `Stream.read*` (`:24-64`: `queue_read` then `self.s.read/readline`), i.e. in Microdot's first
  `readline`, in the two no-yield C calls described in item 2.
- **Failure handling.**
  - `wrap_socket` raising `OSError` (e.g. `ENOMEM` from `MBEDTLS_ERR_SSL_ALLOC_FAILED`) is printed,
    the TCP socket closed, the loop continues (`:168-171`). Measured at the boundary heap: traceback
    `OSError: [Errno 12] ENOMEM`, that client got no response, the other client was served.
  - A `MemoryError` there (allocating the `SSLSocket` object itself, `modtls_mbedtls.c:755-759` ->
    `m_malloc` -> `m_malloc_fail`, `py/malloc.c:87-88`) is not an `OSError` and is not caught: it
    propagates out of `_serve` and **ends the accept task** (code reading; not exercised).
  - A client that rejects the certificate or drops mid-handshake: the error is raised in the
    connection task's `readline`, never in the accept loop; the loop keeps accepting (measured: the
    next client was served each time). Measured exceptions (Unix port, curl/openssl clients):
    curl without `-k` (rejects the self-signed cert): `OSError(-30592,
    'MBEDTLS_ERR_SSL_FATAL_ALERT_MESSAGE')` in one run and `OSError(32,)` (EPIPE) in another;
    TCP connect + close, or a truncated ClientHello + close: `OSError(-29312,
    'MBEDTLS_ERR_SSL_CONN_EOF')`; TLS1.3-only or X25519-only client: `OSError(-28160,
    'MBEDTLS_ERR_SSL_HANDSHAKE_FAILURE')` (server sends alert 40).
  - Microdot: `handle_request` re-raises any `OSError` whose errno is not in `MUTED_SOCKET_ERRORS`
    (`microdot/src/microdot/microdot.py:56-59` list of 32/54/104/..., `:1415-1424`); the negative
    mbedTLS codes are not in it. The project calls `handle_request` from its own `_serve`
    (`src/asy_webserver_service.py:844-868`), which is where such an exception would land.
  - After a non-EOF handshake failure the raw TCP socket is not closed (item 2 defect).

## 6. `docs/library/ssl.rst` at the tag

- Documents client and server use (`:9-11`), `SSLContext(protocol)` (`:38-41`),
  `load_cert_chain(certfile, keyfile)` as paths with the MicroPython extension of passing bytes as the
  data (`:43-53`), `load_verify_locations`, `get_ciphers`, `set_ciphers` (`:55-68`), PSK attributes
  incl. server `server_psk_keys` (`:70-93`), `wrap_socket(..., server_side, do_handshake_on_connect,
  server_hostname, client_id)` (`:95-119`): "For non-blocking sockets ... the handshake should
  generally be deferred because otherwise wrap_socket blocks until it completes" (`:106-112`); a
  server-side SSL socket is created from an `accept()`ed socket (`:102-104`).
- Limitations: mbedTLS ports validate only with `CERT_REQUIRED` (`:24-26`); the returned object is
  `SSLObject`-like, without `send`/`recv` (`:126-129`); `CERT_REQUIRED` needs a set clock (`:136-140`);
  **no `ssl.SSLError` - `OSError` is used** (`:145-147`); DTLS server notes (`:149-199`).
- Not documented: TLS version support, buffer sizes, memory cost, session resumption, server SNI,
  key generation. No separate tls doc page at the tag (`docs/library/` has `ssl.rst`,
  `hashlib.rst`, `cryptolib.rst`).

## 7. Key/certificate generation and crypto primitives

- **No way to generate a key pair or X.509 certificate on the device in v1.29.0**: no API in
  `modtls_mbedtls.c` (methods `:654-663`, module `:1123-1140`), no keygen/write calls in `extmod/*.c`
  or `ports/rp2/*.c` (grep for `genkey|pk_write|x509write|mbedtls_ecp_gen`: none), and the C
  capability is not even compiled (`PK_WRITE_C`, `X509_CRT_WRITE_C`, `X509_CREATE_C`, `PEM_WRITE_C`,
  `GENPRIME` off, item 3). Key and certificate must be provisioned. A pure-Python P-256 keygen/self-
  signing on device would be possible in principle (rp2 has arbitrary-precision ints,
  `MICROPY_LONGINT_IMPL_MPZ`, `ports/rp2/mpconfigport.h:127`, plus SHA-256) but nothing upstream
  provides it and its cost was not measured.
- `hashlib`: sha256 (on by default, `py/mpconfig.h:2039`) is mbedTLS-backed when
  `MICROPY_SSL_MBEDTLS` (`extmod/modhashlib.c:38-41`, `:73-76`); md5 and sha1 on for rp2
  (`ports/rp2/mpconfigport.h:157-158`). No HMAC primitive in `hashlib`.
- `cryptolib` on for rp2 (`:159`): AES ECB/CBC (`extmod/modcryptolib.c:44-46`); CTR only with
  `MICROPY_PY_CRYPTOLIB_CTR`, default 0 (`py/mpconfig.h:2048`; `modcryptolib.c:94-95`, `:143`) and
  rp2's mbedTLS lacks `CIPHER_MODE_CTR`.
- `os.urandom` (`MICROPY_PY_OS_URANDOM (1)`, `ports/rp2/mpconfigport.h:154`) ->
  `mp_hal_get_random` (`extmod/modos.c:150-157`) -> pico-sdk `get_rand_64()`, the same source as
  mbedTLS's entropy. `pico_rand` (`lib/pico-sdk/src/rp2_common/pico_rand/include/pico/rand.h:15-60`)
  is a 128-bit software PRNG (xoroshiro128**, `rand.c:7`) whose state is mixed with hashed entropy of
  "varying quality": ROSC random bit (default on without a hardware TRNG, `rand.h:69`), the 64-bit
  us timer (`:82`), a bus performance counter, and at seeding the board id and a RAM hash. The SDK
  header makes no cryptographic-strength claim. (The RP2040 datasheet's ROSC section was not
  consulted here; the project's datasheet submodule was not read.)

## 8. Microdot v2.7.0 and TLS

- TLS is only the `ssl=` argument: `Microdot.start_server(host, port, debug, ssl=None, ...)`
  (`microdot.py:1237-1255`) stores `self.ssl = ssl` (`:1282`) and passes it to
  `asyncio.start_server(serve, host, port, ssl=ssl, ...)` (`:1307-1316`); `run(..., ssl=None)`
  likewise (`:1334-1366`). No separate TLS extension: `microdot_ssl.py` belonged to the old
  synchronous server and was removed (`docs/implementation/migrating.rst:62-63`).
- `self.ssl` is written (`:963`, `:1282`) and **never read**. `handle_request` calls
  `Request.create(self, reader, writer, peername)` **without `scheme`** (`:1418-1419`), so
  `Request.scheme` is always `'http'` (`:331-332`, `create(..., scheme=None)` `:386-434`), even over
  TLS. Microdot has no URL builder (`url_for` absent); `Response.redirect(location)` uses the given
  `Location` verbatim (`:762-771`), so relative redirects are unaffected, absolute ones built from
  `request.scheme` would say `http`.
- Docs: `docs/users-guide/intro.rst:145-160` (`ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)`,
  `load_cert_chain('cert.pem','key.pem')`, `app.run(port=4443, ssl=sslctx)`) and the note that "When
  using MicroPython, these files must be given in DER format"; `examples/tls/hello.py:35-38` picks
  `.der` on MicroPython; `examples/tls/README.md` suggests `rsa:4096`. The DER-only note is stale
  for 1.29.0: PEM is parsed (item 2) and measured working. Microdot `handle_request` closes the
  connection after every response (`:1432`), so each HTTP request is a new TCP connection and, with no
  resumption, a new full handshake.

---------------------------------------------------------------------------------------------------

# Part 2 - measurements

## Condition (applies to every number below)

- Binary: upstream `v1.29.0` Unix port, **coverage variant** (`make -C ports/unix VARIANT=coverage`),
  chosen because it is the only Unix build where mbedTLS allocates through `m_tracked_calloc` on the
  GC heap (item 3). It is **64-bit x86-64** (`sys.maxsize = 2^63-1`); a 32-bit build was not possible
  (no `gcc-multilib`: `gcc -m32` fails, `Scrt1.o`/`crti.o` missing). 64-bit inflates object/struct
  sizes (pointers, 64-bit MPI limbs, 32 B GC blocks vs 16 B on rp2) but **not** the byte buffers
  (16,717/4,429 B). Coverage variant = `DEBUG=1` (`-Og`) + gcov instrumentation, so its timings are
  meaningless; timing was taken from the standard variant (`-Os`, mbedTLS on libc malloc).
- mbedTLS config differences vs rp2 that matter: unix lacks `MBEDTLS_ECP_NIST_OPTIM` (speed only);
  unix coverage uses libc entropy instead of the hardware-poll hook; everything else that the server
  path touches (TLS 1.2 only, suites, curves, buffer sizes, DTLS on) is identical (both include the
  same common header). The coverage variant's ROM level is EVERYTHING (more modules, larger
  interpreter baseline) vs rp2's EXTRA_FEATURES.
- `asyncio` from `extmod/asyncio` and `ssl.py` from micropython-lib copied to a lib dir and loaded via
  `MICROPYPATH` (the coverage variant does not freeze them).
- Server: `scratchpad/scripts/tls_srv.py` - `tls.SSLContext(PROTOCOL_TLS_SERVER)`, `load_cert_chain`
  with bytes, `asyncio.start_server(cb, "127.0.0.1", port, backlog=5, ssl=ctx)`; `cb` reads the
  request line and headers with `readline`, samples `gc.collect(); gc.mem_alloc()`, waits until all
  `CONC` sessions are open (so they are concurrent), writes a fixed `HTTP/1.0 200` with body `ok`,
  closes. A 1 ms ticker task records event-loop gaps. Driver `run1.sh`:
  `MICROPYPATH=... micropython -X heapsize=<N>K tls_srv.py <cert> <key> <port> <CONC> tls`, clients
  `curl -sk --noproxy '*' --max-time 15 [opts] https://127.0.0.1:<port>/` launched concurrently;
  pass = every client gets `200 ok` and the server exits 0. `bsearch.sh`: bisection 16-320 KiB at
  1 KiB, the result confirmed 3/3. `grid.sh`: pass counts per heap size.
- Certs (host OpenSSL 3.0.13): `openssl req -x509 -newkey ec -pkeyopt ec_paramgen_curve:prime256v1
  -nodes ...` and `-newkey rsa:2048`, CN/SAN sensor.local + 127.0.0.1; DER via `openssl x509 -outform
  DER` / `openssl pkey -outform DER`. Sizes: EC cert 423 B DER / 627 B PEM, key 121 / 241 B; RSA cert
  818 / 1164 B, key 1190 / 1704 B.
- `micropython.mem_peak()` is unusable with tracked allocations (it went negative), so peaks are
  expressed as minimum heap sizes instead.

## Negotiation (coverage binary, 1 MB heap)

- curl default (offers TLS 1.3 + 1.2): `TLSv1.2`, `TLS-ECDHE-ECDSA-WITH-AES-256-GCM-SHA384` (EC cert),
  `TLS-ECDHE-RSA-WITH-AES-256-GCM-SHA384` (RSA cert) - server-preference order of
  `get_ciphers()` (24 suites, AES-256-GCM first).
- Forced `curl --tls-max 1.2 --ciphers ECDHE-ECDSA-AES128-GCM-SHA256`: works,
  `TLS-ECDHE-ECDSA-WITH-AES-128-GCM-SHA256`, TLSv1.2.
- `openssl s_client -tls1_2` (default groups, X25519 offered first): `Server Temp Key: ECDH,
  prime256v1, 256 bits`; `-groups X25519` only: alert 40 handshake failure; `-tls1_3`: alert 40;
  `-groups P-384` with RSA cert: secp384r1 works; `-cipher AES128-GCM-SHA256` (static RSA key
  exchange): works. So a TLS 1.2 ClientHello negotiates secp256r1 (or 384/521) when the client offers
  it; x25519 cannot be negotiated. (Which groups each browser offers in its TLS 1.2 fallback was not
  verifiable from primary sources here.)

## Memory (coverage, 64-bit; `gc.mem_alloc()` after `gc.collect()`)

| Quantity | EC P-256 | RSA-2048 |
|---|---|---|
| interpreter + asyncio baseline | 18,592 B | 18,592 B |
| `SSLContext(PROTOCOL_TLS_SERVER)` retained | +3,424 B | +3,424 B |
| `load_cert_chain` retained (DER or PEM, same) | +1,536 B | +3,232 B |
| after `start_server`, TLS vs plain | 33,632 vs 28,608 B | 35,296 vs 28,608 B |
| 1 established session open (sampled in handler) | +25,056 B | +26,240 B |
| 2 sessions open | +49,952 B | +51,648 B |
| => per additional session | **24,896 B** | **25,408 B** (+ ~830 B one-time, first RSA operation) |
| after all sessions closed | +1.5-1.8 KB vs listening (sample lists/strings in the test; no buffer retained) | same |

Split, from the standard variant (mbedTLS on libc, so the GC heap shows only MicroPython objects):
`SSLContext` object 3,072 B; one TLS connection costs 1,568 B of GC objects vs 832 B for a plain one
(2 connections: ~1,490 vs ~740 B each), i.e. the `SSLSocket` object is ~750 B on 64-bit. Hence
mbedTLS's own per-session allocations are ~23.4 KB (EC) on 64-bit, of which 21,146 B are the two
fixed record buffers; the remaining ~2.3 KB (transform with two AES-GCM contexts, session, tracked
headers, 32 B block rounding) would be somewhat smaller on 32-bit (not measurable here).

## Minimum heap (`-X heapsize`, coverage, 64-bit)

`bsearch.sh` results (smallest size passing 3/3, then one more run at that size and at 1 K less):

| Case | min heap |
|---|---|
| plain HTTP, 1 or 2 connections | 51-52 K (`50K` fails at startup: `MemoryError ... allocating 1552 bytes`; the plain baseline is set by import/compile, not by serving) |
| EC DER, 1 session, curl default (AES-256-GCM) | 79 K (78 K also passed once) |
| EC DER, 1 session, TLS 1.2 ECDHE-ECDSA-AES128-GCM-SHA256 | 82 K (81 K also passed once) |
| EC PEM, 1 session | 84 K (83 K passed once) |
| EC DER, 2 concurrent sessions, default | 105 K (104 K: one client `ENOMEM` at `wrap_socket`, other served) |
| EC DER, 2 sessions, TLS 1.2 AES128-GCM | 107 K (106 K passed once) |
| RSA DER, 1 session | 83-85 K (84 K failed once with `ENOMEM` after passing 3/3) |
| RSA PEM, 1 session | 85 K (84 K passed once) |
| RSA DER, 2 sessions | 109 K (108 K: one client `ENOMEM` at `wrap_socket`) |

The boundary is noisy by a few KiB (GC timing and fragmentation vary run to run), so the grid below
gives pass rates. Robust reading (grid below): **one TLS session needs ~32-34 KB of heap above the plain server
(context + cert + one session incl. handshake transients), and each further concurrent session
~22-25 KB**, on 64-bit. The failure mode at the boundary was always `OSError(ENOMEM)` from
`wrap_socket` (the 16.7 KB block), caught by the accept loop.

Grid (`grid.sh`, 6 runs per size, 2 KiB steps, coverage, 64-bit, DER, curl default suite):

| Case | 0/6 at or below | partial | 6/6 from |
|---|---|---|---|
| plain HTTP, 2 connections | 50 K | - | **52 K** |
| EC P-256, 1 session | 76 K | 78 K 3/6, 80 K 4/6, 82 K 4/6 | **84 K** |
| EC P-256, 2 concurrent sessions | 98 K (100 K 1/6, 102 K 0/6) | 104 K 2/6 | **106 K** |
| RSA-2048, 1 session | 80 K | 82 K 3/6, 84 K 2/6 | **86 K** |
| RSA-2048, 2 concurrent sessions | 104 K | 106 K 1/6, 108 K 4/6 | **110 K** |

Reliable figures (6/6) above the plain server: **EC +32 K for one session, +54 K for two; RSA +34 K /
+58 K**; the second concurrent session adds 22 K (EC) / 24 K (RSA) to the reliable minimum, the
retained cost of an established session being ~25 K. Between the first failing and the first
reliable size lies a ~6-8 K band where success depends on GC timing and fragmentation, which on the
device would be worse (long-running, fragmented heap).

## Event-loop blocking (standard variant, `-Os`, x86-64, mbedTLS without `MBEDTLS_HAVE_ASM` and without NIST_OPTIM)

`tls_srv_fast.py` (same server without the in-handler `gc.collect()` sampling), 1 MB heap, 1 ms
ticker, 5 runs each: ECDHE-ECDSA P-256: max gap 4-6 ms, **two** gaps per handshake visible when
above 5 ms; ECDHE-RSA-2048: 7-10 ms (gaps `[10, 6]`, `[9]`, ...); static RSA key exchange
(`AES128-GCM-SHA256`): 5-7 ms. These confirm the structure (two no-yield C calls per handshake) but
**say nothing about the RP2040** (Cortex-M0+, no 64-bit multiply result, NIST_OPTIM on): the on-device
duration of each segment is not determinable here and needs a bench measurement against the 21 ms
no-yield budget. (Gaps measured on the coverage binary - 9-42 ms, up to ~290 ms for P-384 - are
dominated by `-Og` + gcov and by the sampling `gc.collect()`; do not use them.)

## Static stack usage

Not available: `arm-none-eabi-gcc` is not installed and installing it was refused by the session's
permission policy. Source reading only, for the 7,936 B main stack with a 6,060 B measured peak
(~1.9 KB margin): the static-RSA key exchange path calls `mbedtls_rsa_rsaes_pkcs1_v15_decrypt`, which
holds `unsigned char buf[MBEDTLS_MPI_MAX_SIZE]` = **1,024 B on the stack** in one frame
(`lib/mbedtls/library/rsa.c:2097-2107`); other larger frames on the server path:
`ssl_tls12_populate_transform` `keyblk[256]` (`ssl_tls.c:8634-8647`), `ssl_prepare_server_key_exchange`
`hash[MBEDTLS_MD_MAX_SIZE]` (`ssl_tls12_server.c:2992`), CTR-DRBG `tmp/key/chain` (`ctr_drbg.c:166-168`),
`modtls_mbedtls.c`'s `xcbuf[256]` on the verify-failure paths (`:242`, `:838`), plus nested
`mbedtls_md_context_t`/SHA contexts. RSA signing allocates its scratch on the heap
(`rsa.c:2515-2520`). The real worst-case chain depth needs `-fstack-usage` with the rp2 toolchain or
an on-device stack-paint measurement.

---------------------------------------------------------------------------------------------------

# Decision-relevant summary

1. Server TLS exists in 1.29.0 and works with `asyncio.start_server(..., ssl=ctx)` (and Microdot's
   `ssl=`): **TLS 1.2 only**, ECDHE-ECDSA / ECDHE-RSA / static RSA with AES-GCM or AES-CBC, curves
   secp256r1/384r1/521r1 (no x25519, no ChaCha20); PEM and DER keys/certs, RSA or EC.
2. **Per session ~21.2 KB in two contiguous GC blocks** (in 16,717 B -> 16,736 B on rp2, out 4,429 B
   -> 4,448 B), allocated at accept time (`wrap_socket`), plus ~1-2.5 KB more; measured
   ~24.9 KB (EC) / ~25.4 KB (RSA) per established session on 64-bit. Against dev's ~13 KB margin, even
   one HTTPS session does not fit without taking memory from the plain-HTTP connection ceiling, and
   the 16.7 KB block needs a large contiguous hole.
3. Once: `SSLContext` ~3.4 KB, cert+key retained 1.5 KB (P-256) / 3.2 KB (RSA-2048) (64-bit); input
   bytes can be dropped after `load_cert_chain`.
4. Minimum heap that passed 6/6 (64-bit): plain 52 K; one EC session 84 K, two 106 K; RSA 86 K / 110 K
   (i.e. +32-34 K for the first session, +22-24 K per further one; a 6-8 K band below that passes only
   sometimes); failure = `OSError(ENOMEM)` at `wrap_socket`, caught by the accept loop.
5. The handshake's ECC/RSA work runs in **two uninterrupted C calls per handshake** inside the
   connection's first `readline`; `MBEDTLS_ECP_RESTARTABLE` is off and in 3.6.6 applies only to TLS 1.2
   clients; `modtls` has no `CRYPTO_IN_PROGRESS` handling. RP2040 duration: not determinable here.
6. **No session resumption** (no cache, no tickets, options compiled out) and Microdot closes every
   connection after one response: every HTTP request = new TCP + full ECDHE handshake + two blocking
   segments.
7. Accept loop survives `OSError` from `wrap_socket` (measured) but a `MemoryError` allocating the
   `SSLSocket` object would end it (code). Handshake errors arrive in the connection task as `OSError`
   with negative mbedTLS codes (-30592, -29312, -28160) or EPIPE, which Microdot does not mute.
8. **Socket leak**: after a non-EOF handshake failure `modtls` drops its socket reference before
   `close()`, so the TCP socket stays open (CLOSE_WAIT measured for >4 s); on rp2 the lwIP PCB is
   freed only by the socket finaliser at a later GC.
9. **No on-device key/cert generation** (no API, write/genprime modules compiled out); cert and key
   must be provisioned. Primitives: hashlib sha256/sha1/md5, cryptolib AES ECB/CBC, `os.urandom` =
   pico_rand PRNG mixed from ROSC/timer/bus-counter entropy (same source as mbedTLS).
10. Microdot 2.7.0 has no TLS extension; `self.ssl` is never read and `Request.scheme` is always
    `'http'`. Also: no close_notify, SNI ignored, no ALPN, no EMS; static stack not measured, but the
    static-RSA suites put a 1 KB buffer on the stack (`rsa.c:2107`) against a ~1.9 KB margin.
