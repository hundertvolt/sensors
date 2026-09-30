# A-C merge SRC_NET (HEAD ff2e004)

Scope: the network, web and UART modules of `src/` (CLUSTERS.md "## SRC_NET"). Inputs: `site_index.json` `by_file`
for the eleven paths, plus a slot-by-slot grep of `audit/actions/*.md` for each path and each class name (Site, Change,
Blast); an action whose Site/Change names a path only as a cross-reference (a test or doc site elsewhere) is not merged
here but its blast into these files is checked. Names: the module and class renames of A.U10.37/A.U10.38 land in U10,
before every later unit, so every merged change of U11+ is written against the renamed file and class (`asy_captive_dns`
/ `CaptiveDNS`, `UDPSocket`, `NTPClient`, `WifiService`, `UARTComm`, `UARTLinkDriver`, `asy_print_log`,
`asy_base_classes`, `asy_config_manager`, `asy_system_service`, `asy_crc_checks`, `asy_framing_codecs`,
`asy_api_response`); line numbers are HEAD's. "Tests cluster", "docs cluster" etc. name the cluster that merges an
A-ID's test/doc site; the carrying A-ID is named each time.

Repo-wide mechanical actions whose per-file effect is written into each file's merged changes below (their other
files are other clusters'): A.U10.31 (unquote non-`TYPE_CHECKING` annotations), A.U10.33 (D.15 reorder, last in U10),
A.U10.35 (test-only public attributes private), A.U10.37/A.U10.38 (renames), A.U10.45 (raise-message form, except-tuple
order), A.U10.29 (`const()`/privatise), A.U5.02 (constructor `log` tail), A.U11.31 (`reset_error_counter() -> bool`),
A.U2.04 (named `_ERR_`/`_WRN_` constants), A.U8.x (`# @tunable` tags), A.U24.01/A.U27.30 and similar test/tooling
actions only where they name a product line.

## src/captive_dns.py (→ src/asy_captive_dns.py) and src/LICENSE-captive_dns

### M.SRC_NET.001 Rename the module and its server class
- **From**: A.U10.37 (module `captive_dns` → `asy_captive_dns`, `git mv`), A.U10.38 (`DNSServer` → `CaptiveDNS`)
- **Site**: `src/captive_dns.py` (whole file, `:56` class); text mentions `src/asy_dns_client.py:7`,
  `src/asy_uart_comm.py:97`, `src/asy_wifi_service.py:17, 107, 168, 170, 389`, `src/asy_webserver_service.py:36`,
  `src/LICENSE-captive_dns:1`
- **Change**: `git mv src/captive_dns.py src/asy_captive_dns.py`; class `DNSServer` → `CaptiveDNS`; `DNSQuery` keeps
  its name (upstream's, Apache-2.0 portion). Every in-cluster mention follows: `asy_wifi_service.py:17` `from
  asy_captive_dns import CaptiveDNS`; `:107, :168, :389` comments name `CaptiveDNS`; `asy_webserver_service.py:36`
  comment `DNSServer` → `CaptiveDNS`; `asy_dns_client.py:7` "matching captive_dns.py's precedent" → "matching
  asy_captive_dns.py's precedent" (rewritten again by M.SRC_NET.020); `asy_uart_comm.py:97` "matching captive_dns.py's
  own 0.5s -> 5s shape" → "matching asy_captive_dns.py's own 500 ms -> 5 s shape" (the unit follows M.SRC_NET.004);
  `LICENSE-captive_dns:1` "src/captive_dns.py's" → "src/asy_captive_dns.py's". The module docstring's "DNSServer.run()"
  follows in M.SRC_NET.003. The legacy file `legacy/firmware/python/CommonDrivers/captive_dns.py` is a different file,
  untouched.
- **Resolved**: —
- **Unit**: U10
- **Depends**: A.U1.01 (legacy move, so the legacy name is unambiguous)
- **Blast carried by**: importers outside the cluster (`buildgen/` `CORE_MODULES`, generated modules, tests
  `tests/test_captive_dns.py` → `tests/test_asy_captive_dns.py`, twin, `pyproject.toml` per-file rows, SPEC/CLAUDE.md/
  README/`tests_hardware/README.md`/`digital_twin/README.md`, `THIRD_PARTY_LICENSES.md`) → A.U10.37 / A.U10.38
  (other clusters); UART changelog Class B "names only" → A.U10.38 (docs cluster)
- **Kind**: code

### M.SRC_NET.002 SPDX header scopes Apache-2.0 to DNSQuery
- **From**: A.U34.05 (2)
- **Site**: `src/asy_captive_dns.py:1-3`
- **Change**: → `# SPDX-FileCopyrightText: Copyright <year> p-doyle (Micropython-DNSServer-Captive-Portal)` /
  `# SPDX-License-Identifier: Apache-2.0 AND MIT` / `# Apache-2.0 covers DNSQuery (from its main.py, changes per
  SS4(b)), MIT the rest - THIRD_PARTY_LICENSES.md.`; `<year>` is sourced at execution by A.U34.05 (1) (upstream's first
  commit of `main.py`), or the year is dropped from all three places if upstream cannot be reached.
- **Resolved**: —
- **Unit**: U34
- **Depends**: M.SRC_NET.001; M.SRC_NET.005 (same year, same holder string)
- **Blast carried by**: `THIRD_PARTY_LICENSES.md:128-137` scope sentence → A.U34.05 (4) (LIC cluster); header check
  accepting `Apache-2.0 AND MIT` → A.U34.07 (L0, LIC/tests cluster); `pyproject.toml` CPY001 reason → A.U28.32 /
  A.U34.07 (tooling cluster)
- **Kind**: doc

### M.SRC_NET.003 Module docstring states the QTYPE rule
- **From**: A.U18.01 (header text), A.U10.38 (class name in the docstring)
- **Site**: `src/asy_captive_dns.py:5-8` module docstring
- **Change**: → `"""Captive-portal DNS spoofer for hotspot/AP mode. CaptiveDNS.run() runs while the device broadcasts`
  / `its fallback hotspot; every on-subnet A/ANY query gets a canned A record pointing back at the AP's own IP, any other type an empty NOERROR reply.`
  / `Malformed/off-subnet/truncated input is dropped, never raised.` / `"""` (three prose lines, CLAUDE.md cap).
- **Resolved**: —
- **Unit**: U18
- **Depends**: M.SRC_NET.001
- **Blast carried by**: SPEC A.5 `:331` sentence and new SPEC C.7.5 → A.U18.01 (docs cluster); `THIRD_PARTY_LICENSES.md:145-148`
  change list → A.U18.01/A.U18.02 (LIC cluster)
- **Kind**: code

### M.SRC_NET.004 Imports, error codes and tuned constants
- **From**: A.U10.37 (import names), A.U10.38 (`UDPSocket`), A.U18.01 (`DNS_QTYPE_A` import, `_QTYPE_ANY`), A.U18.02
  (`DNS_LABEL_MAX`, `DNS_NAME_MAX` import), A.U18.03 (`DNS_UDP_MAX` import), A.U18.08 (`ipv4_to_int` import; local
  parser, `_IPV4_OCTETS`, `_IPV4_OCTET_MAX` go), A.U18.09 (`DNS_NAME_MAX` defined in the resolver), A.U18.44 (`Any`
  import goes), A.U5.02 (`LogConfig`/`DEFAULT_LOG`; `AsyFramManager` import goes), A.U2.04 + A.U2.16 + A.U18.06 +
  A.U18.15 (named code constants), A.U31.16 (ms backoff), A.U8.11 (tags; error-retry constant), A.U10.46/A.U11.S02
  (`ErrorSource` alias import)
- **Site**: `src/asy_captive_dns.py:10-54` (imports, `TYPE_CHECKING` block, constants, `_ipv4_to_int()`)
- **Change**: end state, in order:
  - imports: `import asyncio` / `from micropython import const` / `from asy_dns_client import DNS_LABEL_MAX,
    DNS_NAME_MAX, DNS_QTYPE_A, DNS_UDP_MAX, ipv4_to_int` / `from asy_print_log import DEFAULT_LOG, PrintLogHistory,
    make_logger` / `from asy_udp_socket import UDPSocket`; the `TYPE_CHECKING` block imports `from asy_base_classes
    import ErrorSource` and `from asy_print_log import ErrorLog, LogConfig` (no `Any`, no FRAM-manager import).
  - `_NAME = const("DNSSRV")` unchanged (logger names do not change, A.U10.37).
  - one code block after the imports (A.U2.04 idiom): `_ERR_INIT = const(10)` (bind failure, shared, A.U18.06),
    `_ERR_BAD_ARG = const(21)` (invalid server_ip/netmask, was e1), `_ERR_UNEXPECTED = const(23)` (loop top and
    disconnect raise, were e2/e3), `_WRN_SOCKET_TEARDOWN = const(11)` (shared, A.U18.15; was w3 → 43, now 11),
    `_WRN_DNS_REPLY_DROPPED = const(41)` (was w1), `_WRN_DNS_RECV_FAILED = const(42)` (was w2 `DNS_BAD_REQUEST`,
    renamed and reworded by A.U18.06).
  - backoff constants: the `:30-32` comment keeps its three lines; `_RECV_FAIL_BACKOFF_INITIAL_MS = const(500)  #
    @tunable dns_server.recv_backoff_initial_ms = 500`, `_RECV_FAIL_BACKOFF_MAX_MS = const(5000)  # @tunable
    dns_server.recv_backoff_max_ms = 5000`, `_RECV_FAIL_BACKOFF_MULTIPLIER = const(2)  # @tunable
    dns_server.recv_backoff_mult = 2`, new `_ERROR_RETRY_WAIT_S = const(3)  # @tunable dns_server.error_retry_wait_s =
    3` (an int second count, allowed by G10/R23). (Tag placement per A.U8.02's grammar.)
  - `_QTYPE_ANY = const(b"\x00\xff")  # RFC 1035 SS3.2.3 QTYPE * (ANY)`.
  - `_IPV4_OCTETS`, `_IPV4_OCTET_MAX` and `_ipv4_to_int()` (`:37-54`) are deleted (moved to `asy_dns_client`,
    M.SRC_NET.021).
- **Resolved**: A.U8.11's tag names `…_s` vs A.U31.16's `…_ms` — A.U31.16 depends on A.U8.11 and converts the unit
  (G10/R23), so the `_ms` IDs stand and A.U8.11's `dns_server.recv_backoff_initial_s`/`…_max_s` rows are renamed, not
  added twice. DNSSRV w3 → 43 (A.U2.16) vs → shared 11 (A.U18.15) — U18 register fix 9 settles 11, 43 unassigned. w2
  name `DNS_BAD_REQUEST` (A.U2.01) vs `DNS_RECV_FAILED` (A.U18.06) — U18 register fix 9 settles `DNS_RECV_FAILED`.
- **Unit**: U18 (the import/constant rewrite lands with its users; U10's renames of the same lines land in U10 via
  M.SRC_NET.001 and the import renames of A.U10.37, U2's code names are written here because U2.16's numbers are
  replaced in U18 anyway — see Staging below)
- **Depends**: M.SRC_NET.001, M.SRC_NET.020, M.SRC_NET.021, M.SRC_NET.022 (the constants imported); A.U2.01 catalog
  (with the U18 register-fix-9 edits), A.U5.01 (`LogConfig`), A.U10.46 (`ErrorSource`), A.U8.02 (tag grammar)
- **Blast carried by**: catalog rows (w42 text, w43 unassigned, shared w11, DNSSRV uses e10) → A.U2.01 with U18 register
  fix 9 (catalog cluster); Part N rows → A.U8.11/A.U31.16 (docs cluster); tests `tests/test_captive_dns.py` timing
  literals tagged against these IDs → A.U8C.23, A.U8C2.07, A.U8C.120 (tests cluster); `tests_hardware/README.md:879`
  "`wrnno=2`" → A.U2.16/A.U18.06/A.U26 wording (docs cluster)
- **Kind**: code
- **Staging**: U2 (A.U2.16) writes `_ERR_BAD_ARG`/`_ERR_UNEXPECTED`/`_WRN_DNS_REPLY_DROPPED`/`_WRN_DNS_BAD_REQUEST` (41-43
  as A.U2.16) at `:91, 119, 123, 135, 147, 153` because U2's L0 catalog check (A.U2.02) must pass from U2 on; U18 then
  renames 42 and moves 43 → 11 as above. State after U2: every DNSSRV call site passes a named constant; after U18: the
  end state above.

### M.SRC_NET.005 LICENSE-captive_dns paths, holder and year
- **From**: A.U1.20 (`:2` repath), A.U10.37 (`:1` file name), A.U34.05 (1), (3) (`:201` holder/year; NOTICE check)
- **Site**: `src/LICENSE-captive_dns:1-2, 201`, and its end (NOTICE text, if any)
- **Change**: `:1` "src/captive_dns.py's" → "src/asy_captive_dns.py's"; `:2` "python/CommonDrivers/captive_dns.py" →
  "legacy/firmware/python/CommonDrivers/captive_dns.py"; `:201` "Copyright 2019 p-doyle (Micropython-DNSServer-Captive-Portal
  contributors)" → "Copyright <year> p-doyle (Micropython-DNSServer-Captive-Portal)" (same holder string as the SPDX
  header, year sourced as in M.SRC_NET.002, or dropped with it); if upstream ships a `NOTICE` file its text is appended
  at the end of the file (Apache-2.0 §4(d)), else nothing is appended here and THIRD_PARTY_LICENSES.md says "upstream
  ships no NOTICE file" (A.U34.05 (1)).
- **Resolved**: —
- **Unit**: staged — U1: `:2` (A.U1.09's old-path check fails on the stale path from U1 on); U10: `:1` (A.U10.37 moves
  every text mention in its one change); U34: `:201` and the NOTICE append. State after each: correct legacy path / correct
  module name / sourced holder line.
- **Depends**: A.U1.01 (the move), M.SRC_NET.001
- **Blast carried by**: THIRD_PARTY_LICENSES.md entries → A.U1.20, A.U34.05 (4) (LIC cluster); README map entry →
  A.U36.547; image-notice list naming this file → A.U34.09 (LIC cluster)
- **Kind**: doc

### M.SRC_NET.006 CaptiveDNS constructor, accessors and attribute privacy
- **From**: A.U5.02 (`CaptiveDNS(log)`), A.U10.35 (`udps` → `_udps`), A.U18.13 (no `conn_tries`), A.U18.44
  (`get_error_sources()` type), A.U11.S02 (names this site as U18's annotation), A.U10.31 (unquote), A.U11.31
  (`reset_error_counter() -> bool`), A.U10.38/A.U10.37 (names in comments)
- **Site**: `src/asy_captive_dns.py:56-83` `__init__`, `get_error_sources()`, `get_loggers()`, `get_error_counter()`,
  `reset_error_counter()`
- **Change**: `def __init__(self, log: "LogConfig" = DEFAULT_LOG) -> None:` → `self.pr: PrintLogHistory =
  make_logger(log, _NAME)`; `self.name = _NAME` and its comment unchanged except `asy_webserver_service.py`'s wording;
  `self._udps = UDPSocket(("0.0.0.0", 53), mode="server")` (comment `:66-67` "asy_udp_socket.py places source-address
  trust on the caller" unchanged). `get_error_sources(self) -> "list[ErrorSource]"`, comment `:71-73` names
  `asy_base_classes.py`'s `SensorReader.get_error_sources()` and "owned by WifiService". `get_loggers(self) ->
  list[PrintLogHistory]` (unquoted). `async def reset_error_counter(self) -> bool: return await self.pr.reset()`.
  Every other use of `self.udps` in the class → `self._udps`.
- **Resolved**: —
- **Unit**: U18 (the latest constituent; U5.02/U10.x signature/name parts of the same lines are written once here and
  land with U5 and U10 respectively per the staging note)
- **Depends**: A.U5.01, M.SRC_NET.001, M.SRC_NET.004, M.SRC_NET.026 (UDPSocket without `conn_tries`)
- **Blast carried by**: construction `WifiService` → M.SRC_NET.0xx (wifi constructor, below: `CaptiveDNS(log=log)`);
  tests `tests/test_captive_dns.py` (10 constructor calls, `udps` reads, `reset_error_counter` return) → A.U5.02,
  A.U10.35, A.U11.31 (tests cluster); `_collect_error_sources()` generated → A.U10.46 (GEN cluster); `/status`
  `ResetErrors` → M.SRC_NET (webserver `_put_status`, below)
- **Kind**: code
- **Staging**: U5: constructor signature `log` (A.U5.02; all constructors move together, generated code A.U5.03
  in the same unit); U10: `_udps`, unquote, names (A.U10.31/35/37/38); U11: `-> bool` (A.U11.31 co-lands across all
  error sources); U18: `-> "list[ErrorSource]"`. Each stage is a prerequisite of the cross-module change of its own
  unit (constructor sweep, attribute sweep, `ResetErrors` sweep).

### M.SRC_NET.007 CaptiveDNS.run(): bound receive, typed logging, local-failure branch, re-raised cancel
- **From**: A.U18.03 (512 B), A.U18.04 (fixed message + args), A.U18.06 (bind failure vs receive failure), A.U18.07
  (`try`/`finally`, cancel re-raised), A.U18.08 (`ipv4_to_int`), A.U18.15 (teardown wrnno 11), A.U2.16 (numbers),
  A.U31.16 (ms backoff, `sleep_ms`), A.U8.11 (`_ERROR_RETRY_WAIT_S`), A.U10.35 (`_udps`), A.U10.38 (`UDPSocket` in
  comments), A.U10.20 (read-only: the top exists)
- **Site**: `src/asy_captive_dns.py:85-154` `CaptiveDNS.run()`
- **Change**: end state:
  - `:86-92`: `ipv4_to_int(netmask)`/`ipv4_to_int(server_ip)`; the invalid pair logs `await self.pr.err_s("Invalid
    server_ip/netmask, not starting:", server_ip, netmask, errno=_ERR_BAD_ARG)` and returns (before the `try`).
  - `recv_fail_backoff_ms = _RECV_FAIL_BACKOFF_INITIAL_MS`, then `try:` / `while True:` / inner `try:`:
    `data, addr = await self._udps.recvfrom(DNS_UDP_MAX)`; the success branch resets `recv_fail_backoff_ms`;
    `addr_int = ipv4_to_int(addr[0])` inside its existing `try/except Exception` (comment `:102-103` kept);
    off-subnet: `self.pr.evt("Ignoring DNS request from off-subnet or malformed address", addr[0])`; then
    `self.pr.evt("Incoming DNS request from", addr[0], addr[1])`; `packet is None` branch unchanged; `sent is None`:
    `await self.pr.wrn_s("Reply dropped by sendto() to", addr[0], addr[1], wrnno=_WRN_DNS_REPLY_DROPPED)`; else
    `self.pr.evt("Replying to", addr[0], addr[1], dns.domain, "->", server_ip)`.
  - the `else:` (data or addr `None`) branch: one comment line "# (None, None) is local: the socket never bound, or the
    receive raised - never a client's datagram."; `if not self._udps.connected: await self.pr.err_s("Captive DNS
    socket could not bind port 53.", errno=_ERR_INIT)` `else: await self.pr.wrn_s("Receiving a DNS request failed.",
    wrnno=_WRN_DNS_RECV_FAILED)`; then `await asyncio.sleep_ms(recv_fail_backoff_ms)` and `recv_fail_backoff_ms =
    min(recv_fail_backoff_ms * _RECV_FAIL_BACKOFF_MULTIPLIER, _RECV_FAIL_BACKOFF_MAX_MS)` (all small ints).
  - the `except asyncio.CancelledError: … break` arm goes; `except Exception as e:` keeps its comment `:134` and becomes
    `await self.pr.err_s("DNS Server error:", e, errno=_ERR_UNEXPECTED)` / `await asyncio.sleep(_ERROR_RETRY_WAIT_S)`.
  - `finally:` `self.pr.evt("DNS Server shutdown")`; `try: disconnect_ok = await self._udps.disconnect()`; `except
    Exception as e:` (comment `:145-146` kept) `await self.pr.err_s("DNS Server error during disconnect:", e,
    errno=_ERR_UNEXPECTED)`; `disconnect_ok = True`; the inner `except asyncio.CancelledError` arm (`:140-143`) goes
    (a second cancel propagates); `if not disconnect_ok:` comment `:150-152` names `UDPSocket` (≤ 3 lines) and `await
    self.pr.wrn_s("DNS Server socket teardown did not complete cleanly.", wrnno=_WRN_SOCKET_TEARDOWN)`;
    `self.pr.evt("DNS Server disconnected.")`. `CancelledError` then propagates out of `run()`.
- **Resolved**: A.U18.06 reads `self._udps.connected` from another module while A.U10.35 privatises
  `AsyUDPSocket.connected` — settled by G10/R07's own exception ("public only where another module needs it", the
  A.U10.35 C.2 text) and A.U18.06's Depends ("keeps `connected` public and meaningful"): `UDPSocket.connected` stays
  public (M.SRC_NET.026 drops it from A.U10.35's list). A.U8.11 "`:136` becomes `_ERROR_RETRY_WAIT_S`" vs A.U31.16
  "`:136` (`sleep(3)`) stays" — no conflict: A.U31.16 keeps the int-second sleep, A.U8.11 names it; both hold.
- **Unit**: U31 (A.U31.16 is the latest constituent; everything else is U18 — staged)
- **Depends**: M.SRC_NET.004, M.SRC_NET.006, M.SRC_NET.027 (one connect attempt; `connected` semantics), A.U10.46
- **Blast carried by**: `WifiService` fire-and-forget `cancel()` (`asy_wifi_service.py:299-301, 329-331`) unchanged
  (A.U18.07); tests `tests/test_captive_dns.py` (`_FakeUDPS.connected`, wrnno 42 text, bind-failure test,
  cancellation tests, `recvfrom(512)` record, the four log sites) → A.U18.03/04/06/07/15, A.U24.41 (persisted entry),
  A.U35.14 (driven wait), A.U35.48 (cancel sweep) (tests cluster); `tests_hardware/README.md:879, 893` → A.U18.06 /
  U26 wording (docs cluster); SPEC C.7.1 DNSSRV row → A.U2.22 (docs); SPEC C.8 cancellation line → A.U18.07;
  js mock DNSSRV rows → A.U2.21 (WEB cluster)
- **Kind**: code
- **Staging**: U18: every line above except the backoff unit (writes `recv_fail_backoff_s`/`asyncio.sleep(...)` with
  the `_S` float constants as at HEAD); U31: the ms conversion (A.U31.16) of `:94, :100, :124-127` and the constants of
  M.SRC_NET.004. No earlier-unit work needs the U18 stage beyond its own tests, so U18 → U31 is the only split. (The
  U2 stage of M.SRC_NET.004 writes the code names used here from U2 on.)

### M.SRC_NET.008 DNSQuery parses one plain question of at most 255 octets
- **From**: A.U18.02
- **Site**: `src/asy_captive_dns.py:157-192` `DNSQuery.__init__()`
- **Change**: inside the existing `try:`, before `tipo = …` (`:170`): `if data[2] & 0x80 or data[4:6] != b"\x00\x01":
  raise ValueError("not a query with exactly one question")`; inside the label loop before the decode: `if lon >
  DNS_LABEL_MAX: raise ValueError("label type or length not supported")`; after the loop, before `question_end`: `if
  ini - 11 > DNS_NAME_MAX: raise ValueError("name longer than 255 octets")`. Everything else unchanged; the
  `except Exception` sentinel (`:187-191`) maps each to "don't respond". Messages are lower-case (A.U10.45 form).
- **Resolved**: —
- **Unit**: U18
- **Depends**: M.SRC_NET.004 (imports), M.SRC_NET.020/022 (constants in `asy_dns_client`)
- **Blast carried by**: tests `tests/test_captive_dns.py:205-220` flip, `malformed_query_cases()` shapes, boundary
  pair → A.U18.02 (tests cluster); SPEC C.7.5 drop rule and SPEC I.4 `:4871` → A.U18.02 (docs cluster);
  `THIRD_PARTY_LICENSES.md:145-148` → A.U18.02 (LIC cluster)
- **Kind**: code

### M.SRC_NET.009 DNSQuery.response() answers A/ANY, NODATA otherwise
- **From**: A.U18.01, A.U18.08 (`ipv4_to_int`)
- **Site**: `src/asy_captive_dns.py:194-212` `DNSQuery.response()`
- **Change**: `:201` `ipv4_to_int(ip) is None`; then `qtype = self.data[self._question_end - 4 :
  self._question_end - 2]` and `answer = qtype in (DNS_QTYPE_A, _QTYPE_ANY)`; one-line comment above the check "# RFC
  1035 / RFC 2308 2.2: an A or ANY query gets the A record, any other type NOERROR with no answer (NODATA) (owner,
  2026-09-29)."; the `:204-205` comment → "# QDCOUNT=1 (the one parsed question); ANCOUNT=1 only for an A/ANY query";
  the count bytes → `b"\x00\x01\x00\x01\x00\x00\x00\x00" if answer else b"\x00\x01\x00\x00\x00\x00\x00\x00"`; the three
  answer lines `:208-210` run only `if answer:`; flags stay `0x8180`; `:197` `evt` unchanged; the `:195-196` comment
  "with one compressed-pointer A-record answer" → "with one compressed-pointer A-record answer for A/ANY".
- **Resolved**: —
- **Unit**: U18
- **Depends**: M.SRC_NET.004, M.SRC_NET.008, M.SRC_NET.020 (`DNS_QTYPE_A`)
- **Blast carried by**: tests (QTYPE 1/255/28/65/15/2 cases; `tests/test_asy_wifi_service.py:2315` comment; L4 AAAA
  query and `dns_probe.build_query(qtype=)`) → A.U18.01 (tests/HW clusters); SPEC A.5 `:331`, C.7.5 → A.U18.01 (docs);
  `THIRD_PARTY_LICENSES.md:145-148` → A.U18.01 (LIC)
- **Kind**: code

### M.SRC_NET.010 Class and function order per D.15 (captive DNS)
- **From**: A.U10.33
- **Site**: `src/asy_captive_dns.py` classes `CaptiveDNS`, `DNSQuery` and module-level functions
- **Change**: script-driven pure reorder under D.15's key (A.U10.32), AST-verified (identical name/body pairs, comment
  multiset unchanged); `_ipv4_to_int` is still present at U10 time and is reordered with the rest (deleted later by
  M.SRC_NET.004). `DNSQuery` (upstream-derived) is reordered too: D.15 applies to every `src/` class and no literal-port
  exception covers it (only the VOC port has one, G3/R10).
- **Resolved**: —
- **Unit**: U10 (last U10 edit to the file)
- **Depends**: M.SRC_NET.001, every U10 edit of this file
- **Blast carried by**: — (order only; D.15's own bar: tests unchanged, lint/typecheck counts equal)
- **Kind**: code

## src/asy_dns_client.py

### M.SRC_NET.020 Resolver constants: public DNS bounds, tags, no built-in servers
- **From**: A.U18.01 (`_QTYPE_A` → `DNS_QTYPE_A`), A.U18.02 (`_LABEL_MAX_OCTETS` → `DNS_LABEL_MAX`), A.U18.03
  (`_DNS_RECV_BUF` → `DNS_UDP_MAX`), A.U18.09 (new `DNS_NAME_MAX`), A.U18.10 (`_FALLBACK_DNS_SERVERS` goes), A.U10.29
  (drops `_FALLBACK_DNS_SERVERS` from its `const()` list — superseded by the removal), A.U8.09 (tags), A.U10.38
  (`UDPSocket` import), A.U18.15 (`PrintLogHistory` import under `TYPE_CHECKING`)
- **Site**: `src/asy_dns_client.py:9-30` (imports and constants)
- **Change**: imports: `import os` / `from micropython import const` / `from asy_udp_socket import UDPSocket` / the
  `try: from typing import TYPE_CHECKING` / `except ImportError: TYPE_CHECKING = False` idiom (as in the other NET
  modules) / `if TYPE_CHECKING: from asy_print_log import PrintLogHistory`. Constants: `_DNS_PORT = const(53)`;
  `_DNS_TIMEOUT_MS = const(500)` with its two-line comment and `# @tunable dns.timeout_ms = 500`; `_DNS_TRIES =
  const(1)` with `# @tunable dns.tries = 1`; `DNS_UDP_MAX = const(512)  # RFC 1035 SS4.2.1: a DNS message over UDP is at
  most 512 octets.`; `_FALLBACK_DNS_SERVERS` and its comment `:20-21` deleted; `DNS_QTYPE_A = const(b"\x00\x01")`;
  `_QCLASS_IN` unchanged; `_IPV4_OCTETS`, `_IPV4_OCTET_MAX` unchanged; `DNS_LABEL_MAX = const(63)  # RFC 1035 SS3.1's
  single-length-byte ceiling`; new `DNS_NAME_MAX = const(255)  # RFC 1035 SS3.1: a name is at most 255 octets on the
  wire`; `_HEADER_LEN`, `_PTR_MASK` unchanged. The four public constants are imported by `asy_captive_dns` (G4/R27: a
  public `const()` exists only for names other modules import).
- **Resolved**: A.U10.29 lists `_FALLBACK_DNS_SERVERS` for `const()` wrapping — its own text drops it ("U18 config
  value"); A.U18.10 removes it. Dropped from A.U10.29 here.
- **Unit**: U18
- **Depends**: M.SRC_NET.001 (names), A.U8.02 (tag grammar)
- **Blast carried by**: `asy_captive_dns` import → M.SRC_NET.004; Part N rows `dns.timeout_ms`/`dns.tries` with their
  `asy_ntp_client`/`codegen.py` sites → A.U8.09 and M.SRC_NET (NTP constants, below); tests
  `tests/test_asy_dns_client.py:67-77` fallback swap removal → A.U18.10 (tests cluster); SPEC I.2/I.4 buffer sentence →
  A.U18.03 (docs)
- **Kind**: code

### M.SRC_NET.021 One dotted-quad parser, `ipv4_to_int()`, lives here
- **From**: A.U18.08
- **Site**: `src/asy_dns_client.py:33-38` `_is_ipv4_literal()`; callers `:104, :111`
- **Change**: `_is_ipv4_literal()` is replaced by public `ipv4_to_int(ip: str) -> int | None` — the body of HEAD's
  `captive_dns._ipv4_to_int()` (`captive_dns.py:44-53`, uses `_IPV4_OCTETS`/`_IPV4_OCTET_MAX`), comment "# RFC 791
  section 3.2 dotted-quad -> 32-bit big-endian form; never raises for a malformed str"; placed by D.15's key (public
  after the private helpers, A.U10.32/A.U10.33). The two callers read `ipv4_to_int(host) is not None` /
  `ipv4_to_int(server) is None` (M.SRC_NET.023).
- **Resolved**: —
- **Unit**: U18
- **Depends**: M.SRC_NET.019 (U10 reorder done first)
- **Blast carried by**: captive DNS callers → M.SRC_NET.004/007/009; `asy_ntp_client` `DNSFallback` check uses it →
  M.SRC_NET (NTP `_set_mgr_cfg`, below); tests moved to `tests/test_asy_dns_client.py`, comment rewrites in
  `tests/test_captive_dns.py`, `tests/test_ntp_wifi_dns_integration.py:429` → A.U18.08 (tests cluster); SPEC G.1/G.2
  entry → A.U18.08 (docs)
- **Kind**: code

### M.SRC_NET.022 `_build_query()` refuses every name RFC 1035 cannot encode
- **From**: A.U18.09, A.U18.02 (`DNS_LABEL_MAX` at `:48-49`)
- **Site**: `src/asy_dns_client.py:41-66` `_build_query()`
- **Change**: after `labels = host.split(b".")`: `if len(host) + 2 > DNS_NAME_MAX or b"" in labels: raise
  ValueError("not an encodable DNS name")`; the comment `:45-47` → "# resolve_ipv4() is public: a name RFC 1035 SS3.1
  cannot encode (a label over 63 octets, an empty label, over 255" / "# octets on the wire) is refused here whatever its
  caller checked; resolve_ipv4() maps it to None."; the 63-octet check uses `DNS_LABEL_MAX` in its test and message
  (`f"DNS label too long (… > {DNS_LABEL_MAX} octets)"`, capital kept: an acronym, A.U10.45).
- **Resolved**: —
- **Unit**: U18
- **Depends**: M.SRC_NET.020
- **Blast carried by**: `resolve_ipv4()`'s `except (MemoryError, ValueError)` maps it (M.SRC_NET.023, unchanged arm);
  tests (`_build_query` refusals, boundary pair, zero-construction proof) → A.U18.09 (tests cluster); SPEC C.7 resolver
  bounds → A.U18.09 (docs); the `NTPHost` PUT shape check → A.U10.41 (other cluster, in `asy_ntp_client`, merged below)
- **Kind**: code

### M.SRC_NET.023 `resolve_ipv4()`: caller's servers only, fixed port, teardown logged
- **From**: A.U18.10 (no fallback), A.U18.45 (`port` goes), A.U18.15 (`pr` keyword, teardown bool logged), A.U18.08
  (`ipv4_to_int`), A.U10.38 (`UDPSocket`), A.U10.45 (except-tuple order), A.U2.04 (named code); adherence addition
  (construction guard, G5/R54)
- **Site**: `src/asy_dns_client.py:97-129` `resolve_ipv4()`
- **Change**: signature `async def resolve_ipv4(host: str, dns_servers: tuple[str, ...] = (), timeout_ms: int =
  _DNS_TIMEOUT_MS, tries: int = _DNS_TRIES, *, pr: "PrintLogHistory") -> str | None:`. Body: `if ipv4_to_int(host) is
  not None: return host`; the query build and its `except (MemoryError, ValueError)` arm unchanged except the trailing
  comment → "# ValueError: a name RFC 1035 cannot encode - nothing to resolve"; `for server in dns_servers:`; `if server
  == "0.0.0.0" or ipv4_to_int(server) is None: continue` (comment kept); `cli = UDPSocket((server, _DNS_PORT),
  mode="client")` with no surrounding `try` (see Resolved); `try: rsp, _addr = await cli.write_and_recvfrom(query,
  DNS_UDP_MAX, timeout_ms=timeout_ms, tries=tries)` `finally: if not await cli.disconnect(): await pr.wrn_s("DNS socket
  teardown did not complete cleanly.", wrnno=_WRN_SOCKET_TEARDOWN)` (the "never raises" comment goes); the parse and its
  `except (IndexError, ValueError)` arm unchanged. A module-level `_WRN_SOCKET_TEARDOWN = const(11)` joins the constants
  (A.U2.04 idiom; shared code, U18 register fix 9).
- **Resolved**: HEAD's `try: cli = AsyUDPSocket((server, port), …) except (ValueError, TypeError): continue  # malformed
  port` guards only a caller-supplied `port`; after A.U18.45 the port is the constant 53, `server` is a validated `str`
  and `mode` a literal, so no input reaches the arm (A.U18.12's constructor raises only for a non-`(str, int)` tuple or
  a bad mode). G5/R54 ("A branch that no input can reach is removed", owner, OR46.a (2)) settles its removal; its comment
  would otherwise state a false cause (docs hold current state). Agent decision under that rule, listed for OR2.c.
- **Unit**: U18
- **Depends**: M.SRC_NET.020, M.SRC_NET.021, M.SRC_NET.022, M.SRC_NET.026 (constructor), M.SRC_NET.029
  (`write_and_recvfrom()` with required `tries`); A.U2.01 + U18 register fix 9 (shared wrnno 11)
- **Blast carried by**: caller `asy_ntp_client` `_resolve_ntp_server()` passes `pr=self.pr` and the configured
  fallback → M.SRC_NET (NTP, below); tests (`pr=make_pr()` on every call, `port=` calls through
  `tests/_udp_port_redirect.py`, `_ResolvingAsyUDPSocket` removal, multi-server rewrites, teardown-failure test) →
  A.U18.10/A.U18.15/A.U18.45/A.U18.12 (tests cluster); `tests_hardware/bench/test_network_resilience.py:351-355`
  comment holds (A.U18.10); SPEC C.7 → A.U18.15 (docs)
- **Kind**: code

### M.SRC_NET.024 Module header and docstring state the resolver's contract
- **From**: A.U18.10 (":5-7 tries the caller's servers in order; it has no built-in server"), A.U18.09 ("a name RFC
  1035 cannot encode resolves to None"), A.U10.38 (`UDPSocket`), A.U10.37 (`asy_captive_dns.py` — the text mention of
  M.SRC_NET.001, written here in its final form)
- **Site**: `src/asy_dns_client.py:5-7`
- **Change**: docstring → `"""Async, non-blocking IPv4 DNS resolver (A records only) built on asy_udp_socket.py's
  UDPSocket."""`; the comment block `:6-7` → "# resolve_ipv4() never raises: it tries the caller's servers in order (no
  built-in server) and returns" / "# the dotted-quad str or None; a name RFC 1035 cannot encode resolves to None. Only
  bare compression-pointer" / "# answer names (RFC 1035 SS4.1.4) are followed, matching asy_captive_dns.py's
  precedent." (three prose lines). Header `:1-3` (SPDX, inspiration line) unchanged (A.U34.07: already in order).
- **Resolved**: —
- **Unit**: U18 (the U10 rename stage writes only the file name in `:7`, M.SRC_NET.001)
- **Depends**: M.SRC_NET.001
- **Blast carried by**: `THIRD_PARTY_LICENSES.md:76-79` "its header states" → A.U34.03 (LIC cluster)
- **Kind**: code

### M.SRC_NET.019 Module-level function order per D.15 (resolver)
- **From**: A.U10.33 (module-level functions of `src/` reordered in the same pass, OR96.a (2))
- **Site**: `src/asy_dns_client.py:33-129` (`_is_ipv4_literal`, `_build_query`, `_parse_response`, `resolve_ipv4`)
- **Change**: pure reorder by D.15's key (A.U10.32), AST-verified as A.U10.33 states; `ipv4_to_int()` (U18,
  M.SRC_NET.021) is inserted at its key position when written.
- **Resolved**: —
- **Unit**: U10
- **Depends**: M.SRC_NET.001
- **Blast carried by**: —
- **Kind**: code

## src/asy_udp_socket.py

### M.SRC_NET.025 Header carries the discussion link; docstring loses the context-manager clause
- **From**: A.U34.06 (1) (header), A.U18.46 (docstring clause), A.U10.38 (class name)
- **Site**: `src/asy_udp_socket.py:1-7`
- **Change**: `:1-3` → "# No formal license: the class's shape is close to karfas's AsyUDPClient
  (github.com/karfas/upy-simple-app)," / "# which its author posted as 'a starting point' in
  github.com/orgs/micropython/discussions/12967." / "# THIRD_PARTY_LICENSES.md carries the full account and what was
  changed or added here."; docstring `:5-7` → `"""Async, non-blocking UDP wrapper around one socket.socket, driven by a
  hand-rolled select.poll` / `loop. Two modes: mode="client" for a one-shot outbound request/response exchange,
  mode="server" for a bound socket answering inbound datagrams.` / `"""`; the `:8-10` comment block unchanged.
- **Resolved**: —
- **Unit**: U34 (the docstring clause lands in U18 with A.U18.46: staged — U18 removes "; also usable as `async with
  AsyUDPSocket(...) as sock:`", U34 rewrites `:1-3`)
- **Depends**: M.SRC_NET.031
- **Blast carried by**: `THIRD_PARTY_LICENSES.md:185-205` (comparison "retries"/"context-manager support" drops, class
  name, carrier sentence) → A.U18.13, A.U18.46, A.U10.38, A.U34.06 (2) (LIC cluster); the no-license header form check →
  A.U34.07 (tests cluster)
- **Kind**: doc

### M.SRC_NET.026 UDPSocket constants and constructor: tuple only, one attempt, private socket
- **From**: A.U10.38 (`AsyUDPSocket` → `UDPSocket`), A.U18.12 (tuple only), A.U18.13 (`conn_tries` goes), A.U18.05
  (`_POLL_WAIT_MS`/`_POLL_IDLE_MS`), A.U31.16 (`_RETRY_BACKOFF_MS`), A.U8.11 (tags), A.U10.35 (`sock` → `_sock`),
  A.U10.17 (lock reason), A.U10.45 (message form)
- **Site**: `src/asy_udp_socket.py:29-59` (constants, `__init__`)
- **Change**: constants: `_ADDR_TUPLE_LEN = const(2)` unchanged; `_RETRY_BACKOFF_MS = const(500)  # pause after a
  failed socket setup, connect() or bind()` with `# @tunable udp.retry_backoff_ms = 500`; `_POLL_WAIT_MS = const(20)`
  with `# @tunable udp.poll_wait_ms = 20` (a wait with a deadline, inside an exchange; owner-confirmed 2026-07-19);
  `_POLL_IDLE_MS = const(100)` with `# @tunable udp.poll_idle_ms = 100` (a wait with no deadline: the captive DNS
  listen; tuned agent choice 2026-09-30, measurement owed). `class UDPSocket:`; `__init__(self, addr: tuple[str, int],
  mode: 'Literal["client", "server"]' = "client") -> None:` — the mode check unchanged; `:43-49` → `if not
  (isinstance(addr, tuple) and len(addr) == _ADDR_TUPLE_LEN and isinstance(addr[0], str) and isinstance(addr[1],
  int)): raise TypeError(f"addr must be a (host: str, port: int) tuple, got {addr!r}")` (the bytes branch, its comment
  and the `type: ignore[unreachable]` go); `:50-51` and `self._conn_tries` go; `self._addr = addr`; `self._sock:
  socket.socket | None = None`; `self.poller: select.poll | None = None` (public: the sanctioned poller swap, S09);
  `self._mode = mode`; `self.connected = False` (public, see Resolved); `self._connect_lock = asyncio.Lock()  # serialises
  setup and teardown of the one socket object`.
- **Resolved**: (1) A.U8.11 tags `udp.conn_tries_default = 1` and `udp.round_trip_tries_default = 1`; A.U18.13 and
  A.U18.14 remove the parameter/default they sit on — verifier rulings V.U18.D and V.U18.14 (OR36.a (1), REF/R02) settle
  both rows dropped. (2) A.U8.11's `udp.ready_poll_ms = 20` splits into `udp.poll_wait_ms`/`udp.poll_idle_ms` (A.U18.05's
  own Depends, A.U8.11's "the tags follow its two named values"). (3) A.U8.11's `udp.retry_backoff_s = 0.5` → A.U31.16's
  `udp.retry_backoff_ms = 500` (the unit change is the later action and depends on A.U8.11). (4) A.U10.35 privatises
  `AsyUDPSocket.connected` (S09: read outside only by tests at HEAD) while A.U18.06 makes `asy_captive_dns` read it —
  G10/R07's exception ("public where another module needs it", A.U10.35's own C.2 text) keeps it public; A.U10.35's list
  loses `connected` for this class, keeps `sock`.
- **Unit**: U31 (the ms constant is the latest; staged: U10 — class rename, `_sock`, lock reason; U18 — tuple check,
  `conn_tries` removal, the two poll constants and tags, `udp.retry_backoff_s` row renamed by U31; U31 — `_RETRY_BACKOFF_MS`)
- **Depends**: A.U8.02 (tag grammar)
- **Blast carried by**: product constructions `asy_dns_client` (M.SRC_NET.023), `asy_ntp_client` (NTP fetch, below),
  `asy_captive_dns` (M.SRC_NET.006) — all tuples, no `conn_tries`; tests (address shim at import, `make_addr()`
  tuples, `conn_tries` tests removed/renamed, `sock` → `_sock` readers, doubles dropping the parameter) → A.U18.12,
  A.U18.13, A.U10.35 (tests cluster); twin shim move to a hardware-fake-free directory + `mypy_path`/runner
  `sys.path` → A.U18.12 / A.U25 (TWIN cluster), `pyproject.toml:365` (tooling); Part N rows → A.U8.11/A.U18.05/A.U31.16
  (docs); SPEC G.2 `UDPSocket` entry → A.U18.13 (docs); SPEC F.5.9 paragraph → A.U18.05 (docs)
- **Kind**: code

### M.SRC_NET.027 `_connect()`: one attempt, millisecond backoff
- **From**: A.U18.13 (one attempt), A.U31.16 (`sleep_ms`), A.U10.45 (except order), A.U10.35 (`_sock`)
- **Site**: `src/asy_udp_socket.py:73-102` `_connect()`, `:104-124` `_disconnect_locked()`
- **Change**: inside `async with self._connect_lock:` / `if self._sock is None:` / `try:` socket, `setsockopt`,
  `setblocking(False)`, `select.poll()`, `register(...)` as today, then `if self._mode == "client":
  self._sock.connect(self._addr)` `else: self._sock.bind(self._addr)`; `self.connected = True`; `except (MemoryError,
  OSError, TypeError):` comment "# setup, connect or bind failed" and `await asyncio.sleep_ms(_RETRY_BACKOFF_MS)`; `if
  not self.connected: await self._disconnect_locked()` unchanged. Header comment `:74-75` unchanged.
  `_disconnect_locked()`: `self.sock` → `self._sock` throughout, both excepts `(MemoryError, OSError)`, comments
  unchanged.
- **Resolved**: —
- **Unit**: U31 (staged: U18 writes the one-attempt shape with `asyncio.sleep(_RETRY_BACKOFF_S)`; U31 converts)
- **Depends**: M.SRC_NET.026
- **Blast carried by**: tests (lock-wait bound one backoff, self-heal renamed, `DrivenTime` 500 ms advance) →
  A.U18.13, A.U35.14, A.U31.16 (tests cluster); twin shim wraps `_connect` unchanged (A.U18.13)
- **Kind**: code

### M.SRC_NET.028 `ready()`: one poll coroutine, deadline through `wait_for_ms`, idle rate without one
- **From**: A.U10.26 (`_poll()` + `wait_for_ms`), A.U18.05 (`wait_time_ms` goes; two rates), A.U18.17 (POLLERR arm
  kept, verdict), A.U8.11 (tags on the two constants, M.SRC_NET.026), A.U10.45 (except order), A.U18.34 (read-only: the
  lock-hold analysis cites this loop)
- **Site**: `src/asy_udp_socket.py:126-148` `ready()`
- **Change**: new private `async def _poll(self, mask: int, wait_ms: int) -> bool:` — `while True:` the `poller is
  None` check with its two comments kept; `for _, event in self.poller.ipoll(0): if event & (mask | select.POLLERR |
  select.POLLHUP): return True`; `await asyncio.sleep_ms(wait_ms)` (no ticks deadline). `async def ready(self, mask:
  int, timeout_ms: int = -1) -> bool:` — comment (3 lines): "# Polls ipoll(0), sleeping _POLL_WAIT_MS inside an
  exchange (a deadline is set) and _POLL_IDLE_MS while listening with none (SPECIFICATION.md F.5.9's shape)." / "# A
  real POLLERR/POLLHUP is always reported; returning True lets the caller's socket call surface it." / "# A malformed
  mask or timeout_ms returns False: callers' excepts wrap only their own socket call."; body: `await self._connect()`;
  `if not self.connected or self.poller is None: return False`; `try: if timeout_ms <= 0: return await self._poll(mask,
  _POLL_IDLE_MS)` / `return await asyncio.wait_for_ms(self._poll(mask, _POLL_WAIT_MS), timeout_ms)` / `except
  asyncio.TimeoutError: return False` / `except (MemoryError, OSError, TypeError): return False`. `import time` goes if
  nothing else uses it (grep at execution: `ready()` was its only user).
- **Resolved**: A.U10.26 "`ready()` keeps its signature" vs A.U18.05 removing `wait_time_ms` — V.U18.05/V.U18.D rule for
  A.U18.05 (recorded in A.U18.05's Depends). A.U10.26 passes one `wait_time_ms` to `_poll()`; A.U18.05's Depends settles
  `_POLL_WAIT_MS` in the deadline branch and `_POLL_IDLE_MS` in the no-deadline branch. Soundness (agent, OR111.a (2)):
  A.U10.26's shape puts the `timeout_ms <= 0` test outside the loop's `try`, so a non-int `timeout_ms` would raise out of
  `ready()`, breaking G6/R34 "`AsyUDPSocket` I/O … never raise" (HEAD maps it to `False`, `:145-148`); the merged body
  keeps the branch and the `wait_for_ms` call inside one `try` that maps `TypeError` to `False` — settled by G6/R34.
- **Unit**: U18 (A.U10.26's structure lands in U10 with the 20 ms `wait_time_ms` passed through — staged: U10 writes
  `_poll()`/`wait_for_ms` with `wait_time_ms` kept, U18 removes the parameter and splits the rate)
- **Depends**: M.SRC_NET.026, M.SRC_NET.027
- **Blast carried by**: callers `sendto()`/`write()`/`recvfrom()` pass no rate (M.SRC_NET.030); `asy_captive_dns`
  listens with no deadline (M.SRC_NET.007); tests (renamed deadline-rate test, dropped `wait_time_ms` arguments,
  recorder 20/100 assertions, `ready(timeout_ms=50)` no-runner-left test, real-socket 100 ms wake margins,
  `tests/test_asy_wifi_service.py:2320-2345`) → A.U18.05, A.U10.26, A.U35.14 (tests cluster); the ticks-wrap crossing
  tests of A.U14.34 no longer have a `ticks_*` site in this file after A.U10.26 (tests cluster, A.U14.34's own list);
  SPEC F.2 mechanism, F.5.9 paragraph, Part C/G "one poller pattern", SPEC F POLLERR paragraph → A.U10.26, A.U18.05,
  A.U18.17 (docs); BACKLOG prioritised item removed → A.U10.26 (docs)
- **Kind**: code

### M.SRC_NET.029 `write_and_recvfrom()`: a failed send is not waited out; `tries` required
- **From**: A.U18.14 (1), and its ruling on A.U8.11's `udp.round_trip_tries_default` (V.U18.14, V.U18.D)
- **Site**: `src/asy_udp_socket.py:182-201` `write_and_recvfrom()`
- **Change**: signature `(self, msg: bytes | bytearray, buf: int, timeout_ms: int = -1, *, tries: int)` (`tries`
  required and keyword-only; the one product caller, `asy_dns_client`, already passes it by keyword, M.SRC_NET.023);
  comment `:189-191` → "# Retries the full write+response round
  trip up to `tries` times, returning as soon as a response arrives;" / "# a try whose write() failed does not wait for
  a reply. range(tries) is guarded: a malformed tries raises TypeError" / "# from range() itself, before
  write()/recvfrom() ever see it."; the loop: `if await self.write(msg, timeout_ms=timeout_ms) is None: continue`, then
  `data, addr = await self.recvfrom(buf, timeout_ms=timeout_ms)` as today.
- **Resolved**: A.U8.11 tags the `tries: int = 1` default; A.U18.14 removes the default — ruling for A.U18.14 (its own
  Depends). The parameter order: `timeout_ms` keeps its `-1` default, so `tries` without a default must come first or be
  keyword-only; keyword-only (`*, tries: int`) keeps every positional call shape and is the smaller change — agent choice.
- **Unit**: U18
- **Depends**: M.SRC_NET.028
- **Blast carried by**: `asy_dns_client` passes `tries=tries` (M.SRC_NET.023); NTP stops using it (NTP fetch, below);
  tests omitting `tries` pass `tries=1`, new failed-send test → A.U18.14 (tests cluster)
- **Kind**: code

### M.SRC_NET.030 I/O methods: except order, truncation and stub comment
- **From**: A.U18.17 (`recvfrom()` comment), A.U18.43 (2) (names A.U18.17's text as the workaround comment), A.U28.30
  (4) (removal trigger for the `:177` suppression), A.U10.45 (except order), A.U10.35 (`_sock`), A.SDEP.08 (the version
  stamp in the comment)
- **Site**: `src/asy_udp_socket.py:150-180` `sendto()`, `write()`, `recvfrom()`
- **Change**: `self.sock` → `self._sock`; the three excepts `(MemoryError, OSError, TypeError)` with their trailing
  reasons unchanged; `recvfrom()`'s comment `:174-176` → "# A datagram longer than buf arrives cut to buf bytes, the
  rest dropped (extmod/modlwip.c:719-721, v1.29.0)." / "# The 1.29 stub types the address as socket's full _Address
  union; this AF_INET socket (_connect()) only returns a 2-tuple." / "# Remove the ignore once the stub narrows it
  (warn_unused_ignores then flags it)."; `# type: ignore[return-value]` on `:177` stays. The version text is the pin
  current at execution (if B0's refresh moved it, A.SDEP.08's re-stamp applies to these lines).
- **Resolved**: —
- **Unit**: U28 (A.U28.30 is the latest constituent; U18 writes the first two lines, U28 adds the trigger line)
- **Depends**: M.SRC_NET.026
- **Blast carried by**: SPEC F.5.5 suppression rule → A.U14.36 (docs); the suppression-form check → A.U28.30 (tests
  cluster); SPEC F POLLERR/truncation paragraph → A.U18.17 (docs)
- **Kind**: code

### M.SRC_NET.031 Remove the unused async context manager
- **From**: A.U18.46
- **Site**: `src/asy_udp_socket.py:24-27, 61-71`
- **Change**: `__aenter__()`/`__aexit__()` go; the `TYPE_CHECKING` import of `Self` (and `typing_extensions`) goes;
  `Literal` stays (the `mode` annotation).
- **Resolved**: —
- **Unit**: U18
- **Depends**: M.SRC_NET.026
- **Blast carried by**: tests `tests/test_asy_udp_socket.py:998-1030` → A.U18.46 (tests cluster); THIRD_PARTY_LICENSES
  "context-manager support" → A.U18.46 (LIC)
- **Kind**: code

### M.SRC_NET.032 Class member order per D.15 (UDP socket)
- **From**: A.U10.33
- **Site**: `src/asy_udp_socket.py` class `UDPSocket`
- **Change**: pure reorder by D.15's key (A.U10.32), AST-verified; the private `_poll()` added in U10 by M.SRC_NET.028's
  first stage is placed by the same key.
- **Resolved**: —
- **Unit**: U10 (last U10 edit)
- **Depends**: every U10 edit of the file
- **Blast carried by**: —
- **Kind**: code

### M.SRC_NET.018 One host-label check, `host_label_ok()`, lives beside `ipv4_to_int()`
- **From**: A.U6.29 (`_host_label_ok()`, written in `asy_wifi_service.py`), A.U10.41 (the NTP host shape applies "the
  product's `_host_label_ok()` of A.U6.29 per label"), REF/R05 (a helper is written once and imported), G10/R07 (a name
  another module imports is public)
- **Site**: `src/asy_dns_client.py` (new public function next to `ipv4_to_int()`); removed from
  `src/asy_wifi_service.py`
- **Change**: `def host_label_ok(label: str) -> bool:` — `False` for an empty string; otherwise every character an
  ASCII letter, digit or `-`, first and last not `-` (RFC 1123 §2.1), a plain loop over `ord()` (no `re`); comment
  "# RFC 1123 SS2.1 host label (letters, digits, '-'; not at either end); the caller bounds the length." Placed by
  D.15's key. `asy_wifi_service` (Hostname, M.SRC_NET.083) and `asy_ntp_client` (`NTPHost` per label, M.SRC_NET.045)
  import it; no copy remains in either.
- **Resolved**: A.U6.29 writes the helper privately in the WiFi module; A.U10.41 needs it from the NTP module. Importing
  a `_`-private name across modules breaks G10/R07; REF/R05 forbids a second copy. The resolver module already holds the
  one dotted-quad parser both DNS users share (A.U18.08), so the DNS-name helper joins it (agent choice of home, OR2.c).
- **Unit**: staged — U6: A.U6.29 writes `_host_label_ok()` in `asy_wifi_service.py` (its only user then); U18: it moves
  here as `host_label_ok()` with the NTP host check (M.SRC_NET.045), the WiFi import following in the same change.
- **Depends**: M.SRC_NET.021
- **Blast carried by**: the three-implementation corpus `tests/_radio_shape_cases.json` (`hostLabel`, `hostName`) and
  its L1 reader import the product helper from `asy_dns_client` → A.U6.29/A.U10.41 (tests cluster); SPEC C.7.4 host-label
  rule and G.2 "reuse before writing" entry → A.U6.29/A.U18.08 (docs)
- **Kind**: code

## src/asy_ntp_client.py

### M.SRC_NET.040 Module docstring and header comment state current facts
- **From**: A.U10.37 (`asy_base_classes.py` in the text); adherence finding (the `:8-10` comment goes stale)
- **Site**: `src/asy_ntp_client.py:5-10`
- **Change**: docstring `:6` "extends base_classes.py's SensorReaderConfig" → "extends asy_base_classes.py's
  SensorReaderConfig"; comment `:8-10` → "# Two fields check their shape before storing (_set_mgr_cfg(): NTPHost,
  DNSFallback); the rest persist through" / "# asy_base_classes.py's generic _set_dict_cfg(), with no _push_callbacks
  entries. Error numbers come from the one" / "# catalog (SPECIFICATION.md Part C.7.1)." SPDX header `:1-3` unchanged
  (A.U34.07: already in order).
- **Resolved**: HEAD's "errno/wrnno numbering starts at 11, clear of base_classes.py's own reservation" is false after
  A.U2.15 (NTP codes 67-72, 40 and shared ones) and "gives full setter support with no _push_callbacks" is incomplete
  after A.U18.10's `_set_mgr_cfg()` override; no action carries the comment. CLAUDE.md working agreement (docs hold
  current state) settles the rewrite.
- **Unit**: U18 (A.U10.37's file-name text stage lands in U10)
- **Depends**: M.SRC_NET.045
- **Blast carried by**: —
- **Kind**: code

### M.SRC_NET.041 Imports follow the renames and the new primitives
- **From**: A.U10.37, A.U10.38, A.U10.03 (`arm_tick_timer`, `TickSeconds`), A.U10.06 (`utc_now`, `set_utc_valid`),
  A.U5.02/A.U5.10 (`LogConfig`, `DEFAULT_LOG`), A.U18.10/A.U10.41 (`ipv4_to_int`, `host_label_ok`, `DNS_LABEL_MAX`),
  A.U18.44 (`Any` goes), A.U10.46 (`TaskStarter`)
- **Site**: `src/asy_ntp_client.py:12-35`
- **Change**: runtime imports: `asyncio`, `struct`, `time`, `namedtuple`; `from machine import RTC, Timer`; `const`;
  `from asy_base_classes import SensorReaderConfig, TickSeconds, arm_tick_timer, set_utc_valid, utc_now`;
  `from asy_config_manager import make_dict`; `from asy_dns_client import DNS_LABEL_MAX, host_label_ok, ipv4_to_int,
  resolve_ipv4`; `from asy_print_log import DEFAULT_LOG, LogConfig`; `from asy_udp_socket import UDPSocket`.
  `TYPE_CHECKING` block: `Callable`; `from asy_base_classes import TaskStarter`; `from asy_config_manager import
  ConfigSchema, WriteValidity` (the new override's annotations); `from asy_print_log import ErrorLog`; no `Any`, no
  FRAM-manager import.
- **Resolved**: —
- **Unit**: U18 (each rename stage in its own unit: U10 names, U5 `LogConfig`)
- **Depends**: A.U10.02 (`TickSeconds`), A.U10.03, A.U10.06, A.U5.01, M.SRC_NET.018, M.SRC_NET.021
- **Blast carried by**: —
- **Kind**: code

### M.SRC_NET.042 Timing, protocol and plausibility constants
- **From**: A.U8.09 (tags), A.U10.29 + A.U18.11 (`_NTP_UDP_PORT` `const()`), A.U18.16 (`_NTP_PACKET_LEN`), A.U5.10
  (`NtpTiming` and its defaults), A.U10.43 (no identifier here carries `_sec`)
- **Site**: `src/asy_ntp_client.py:37-61`, the constructor defaults `:101-107`
- **Change**: `_NTP_ASYNC_INTERV = const(3)` (`# @tunable ntp.async_intervals = 3`), `_NTP_CHECK_INTERV = const(10)`
  (`ntp.check_interval_s = 10`; buildgen AST-reads it, A.U20.27), `_NTP_SYNC_RETRIES = const(3)` (`ntp.sync_retries`),
  `_NTP_RETRY_INTERV = const(15)` (`ntp.retry_interval_s`), `_NTP_BACKOFF_MULT = const(2)` (`ntp.backoff_mult`), each
  keeping its comment; `_DEFAULT_RETRY_S = const(10)` (`ntp.retry_s_default = 10`) and `_DEFAULT_RETRY_MAX_S =
  const(600)` (`ntp.retry_max_s_default = 600`), comment "# unsynced retry: first interval and its cap; both round up to
  the 10 s check tick (Part C.7.2)"; `NtpTiming = namedtuple("NtpTiming", ("dns_timeout_ms", "dns_tries",
  "fetch_timeout_ms", "retry_s", "retry_max_s"))`; `_NTP_CONN_TIMEOUT` (`:39`) is deleted (see Resolved);
  `_NTP_UDP_PORT = const(123)  # RFC 5905 SS7.2` (the two-line "not const()-wrapped so tests can redirect it" comment
  goes); `_NTP_PACKET_LEN = const(48)  # RFC 5905 SS7.3: the NTP header; the reply fields read end at byte 48`
  (untagged: a protocol constant); `_NTP_EPOCH_DELTA`, `_NTP_ERA_SECONDS` unchanged; the plausibility pair tagged
  `ntp.plausible_min_unix = 1735689600` / `ntp.plausible_max_unix = 4102444800` (re-check trigger in Part N, A.U8.09);
  `_NTP_LI_UNSYNCHRONIZED`, `_NTP_STRATUM_INVALID`, `_TIME_OFFSET_COUNT`, `_GMTIME_FIELDS` unchanged.
- **Resolved**: A.U8.09 lists `asy_ntp_client.py:101, 103` (the `__init__` defaults `dns_timeout_ms=500`, `dns_tries=1`)
  and `:39` as tagged sites "at A.U5.10's `NtpTiming` constants"; A.U5.10 makes `timing` a required argument, so no
  `src/` code reads a DNS or fetch default here any more — the generated module passes codegen's `_DNS_TIMEOUT_MS`,
  `_DNS_TRIES`, `_NTP_FETCH_TIMEOUT_MS` (A.U5.10), and the resolver keeps its own standalone defaults
  (`asy_dns_client._DNS_TIMEOUT_MS`/`_DNS_TRIES`, M.SRC_NET.020). A third copy of those values, and `_NTP_CONN_TIMEOUT`
  with no reader, would be exactly what REF/R05 ("written once") and G5/R54 (no unreachable code) forbid; the
  constants buildgen actually reads (`_DEFAULT_RETRY_S`, `_DEFAULT_RETRY_MAX_S`, U5.10) stay. Part N's `dns.timeout_ms`,
  `dns.tries`, `ntp.fetch_timeout_ms` rows therefore list `asy_dns_client.py` and `codegen.py` sites only. Agent reading
  of A.U5.10's "…", for OR2.c.
- **Unit**: U18 (tags U8 and constants U5 are staged in their units: U5 writes `NtpTiming` and the two retry
  defaults, U8 tags them; U10.29's `const()` of the port is written by U18 together with its seam removal, as A.U10.29
  itself defers it)
- **Depends**: A.U8.02 (grammar); A.U20.27 (AST read of `_NTP_CHECK_INTERV`, name unchanged)
- **Blast carried by**: codegen `NtpTiming(...)` emission and `validate.py` default reads → A.U5.10 (GEN cluster);
  Part N rows → A.U8.09 (docs; the three rows' site lists per Resolved); tests reassigning `_NTP_UDP_PORT` →
  `tests/_udp_port_redirect.py` → A.U18.11 (tests cluster); mirror sites in `tests/test_asy_ntp_client.py` → A.U8.09
  (tests cluster)
- **Kind**: code

### M.SRC_NET.043 Schema tuples, key names and web tags
- **From**: A.U10.39 (`_VAL_` names), A.U10.40 (keys `NTPHost`, `NTPOffset`, `NTPInterval`), A.U10.41 (bound 3-253,
  `shape=hostName`, comment), A.U18.10 (`_VAL_DNS_FALLBACK`), A.U6.26 (dns group tags), A.U23.17 (`clearable=true`,
  description), A.U6.18 (`submitLabel`), A.U5.03 + A.U10.38 (`@wiring` tag), A.U10.38 (class name in the comment)
- **Site**: `src/asy_ntp_client.py:63-85`
- **Change**: comment `:63-64` → "# Schema tuples for ConfigManager.get_*_values(). NTPHost is bounded by RFC 1035 (253
  characters); the other" / "# bounds mirror the pre-refactor handler; defaults are the only source of truth for a
  fresh config_NTP.cfg."; tuples `_VAL_NTP_HOST = const((("NTPHost", "str", "pool.ntp.org", 3, 253, None),))`,
  `_VAL_NTP_OFFSET = const((("NTPOffset", "int", 0, -43200, 43200, None),))`, `_VAL_NTP_INTERVAL =
  const((("NTPInterval", "int", 12, 1, 24, None),))`, `_VAL_GMT_OFFSET` (`GMTOffset`), `_VAL_DST_OFFSET`
  (`DSTOffset`) unchanged values; new `_VAL_DNS_FALLBACK = const((("DNSFallback", "str", "8.8.8.8,1.1.1.1", 0, 47,
  None),))` with its two-line comment "# DNS servers tried after the DHCP-provided one, in order; empty = none. Default:
  today's public pair" / "# (owner, 2026-09-26). At most three (agent, 2026-09-30), which bounds the NTP attempt's lock
  hold (SPECIFICATION.md C.8)." Tags: `# @web-group section=networking submitGroup=ntp label="NTP Time Sync" submit=true
  submitLabel="Apply & Resync"`; `# @web NTPHost … label="NTP Server Address" shape=hostName`; `# @web NTPOffset …
  unit="s" description=…` (text unchanged); `# @web NTPInterval … unit="h"`; new `# @web-group section=networking
  submitGroup=dns label="DNS Fallback Servers" submit=true` and `# @web DNSFallback section=networking submitGroup=dns
  label="Fallback DNS Servers" shape=ipv4List clearable=true description="Asked after the DHCP-provided server fails, in
  order. Empty = none; the Clear button empties it."`; the GMT/DST contribution block `:76-80` unchanged; `:82-84`
  comment "because AsyNtpClient is mandatory infra" → "because NTPClient is mandatory infra"; `:85` → `# @wiring
  fram_target FRAMManager log optional kwarg`.
- **Resolved**: A.U6.26's description vs A.U23.17's — A.U23.17 replaces it ("co-lands with A.U6.26 — A-C merges"); the
  later text stands. A.U6.26 left the file open; A.U18.10 chose `asy_ntp_client.py` (A.U6.26/A.U23.17 follow).
- **Unit**: U23 (A.U23.17 is the latest; staged: U6 writes the `submitLabel`; U10 the key/name renames and the 253 bound;
  U18 the `DNSFallback` tuple and the dns group with A.U6.26's description; U23 `clearable=true` and the final
  description)
- **Depends**: A.U6.29 (the `shape=` key), A.U23.40 (index-based ids for the Clear button), M.SRC_NET.045
- **Blast carried by**: generated definitions (networking `ntp`/`dns` groups, `maxLength` 253, `shape`, `clearable`) →
  A.U6.26/A.U10.41/A.U23.17 (GEN/WEB clusters); `buildgen/definitions.py` `_networking_section()` loads the file's tags
  → A.U6.26; `codegen.py:607-609` networking `SettingsGroup(ntp, ("DNSFallback",))` → A.U18.10 (GEN); js mock shapes
  `hostName`/`ipv4List`, Clear button → A.U10.41/A.U18.10/A.U23.17 (WEB); `mockdata/samples.json` `networkingConfig` →
  A.U18.10/A.U6.26 (WEB); `tests/test_asy_ntp_client.py:53` schema mirror, request-body headroom test → A.U18.10,
  A.U10.41 (tests); SPEC I.3/I.6, BACKLOG `:484-513`, DEVICE_REFERENCE networking settings → A.U10.41/A.U18.10 (docs)
- **Kind**: code

### M.SRC_NET.044 NTPClient constructor: timing object, log object, private state
- **From**: A.U10.38 (`AsyNtpClient` → `NTPClient`), A.U5.02 (`log`, `max_module_error` by keyword), A.U5.10
  (`timing: NtpTiming`), A.U10.18 (`network_available` → `network_available_locked`), A.U10.35 (eight attributes
  private), A.U10.03 (`_sync_age`), A.U18.23 (`_check_armed`, `_tick_armed`), A.U3.02 (episode masks go), A.U18.10
  (schema gains `DNSFallback`), A.U0.37 (owner tag at `:115`), A.U10.39 (names)
- **Site**: `src/asy_ntp_client.py:95-142`
- **Change**: `class NTPClient(SensorReaderConfig):` / `def __init__(self, wifi_mode_lock: asyncio.Lock,
  network_available_locked: "Callable[[], bool]", get_dns_server: "Callable[[], str | None]", timing: NtpTiming,
  cfg_path: str = "", log: LogConfig = DEFAULT_LOG) -> None:`; `super().__init__(NTP(Synced=False, LastSyncAge=None,
  TS=None), _NAME, _VAL_NTP_HOST + _VAL_NTP_OFFSET + _VAL_NTP_INTERVAL + _VAL_GMT_OFFSET + _VAL_DST_OFFSET +
  _VAL_DNS_FALLBACK, max_module_error=0, cfg_path=cfg_path, log=log)` with the trailing comment "# no failure streak: an
  unreachable server is routine here, never a restart (owner, 2026-09-24; Part C.7.2)". Attributes: `wifi_mode_lock`
  (comment names `WifiService`); `network_available_locked` (comment "WifiService.network_available_locked - caller must
  hold wifi_mode_lock"); `get_dns_server` (comment names `WifiService.get_dns_server_ip`); `dns_timeout_ms`,
  `dns_tries`, `ntp_fetch_timeout_ms` from `timing`; `retry_s = max(timing.retry_s, _NTP_CHECK_INTERV)`, `retry_max_s =
  max(timing.retry_max_s, self.retry_s)`; `_retry_wait_s`, `_unsynced_wait_s` as today; `_episode_errs`/`_episode_wrns`
  deleted; `self._sync_age = TickSeconds()`; `self._check_armed: bool | None = None`, `self._tick_armed: bool | None =
  None`; `_ntp_sec_count`, `_ntp_retries`, `_ntp_sync_trigger_event`, `_ntp_timer_trigger_event`,
  `_time_counter_trigger_event`, `_ntp_timer`, `_ntp_retry_timer`, `_counter_timer` (underscore added; every use in the
  file follows).
- **Resolved**: —
- **Unit**: U18 (staged: U5 signature and `log`; U10 class name, `network_available_locked`, private names,
  `_sync_age`; U3 episode masks; U18 schema and `_check_armed`/`_tick_armed`)
- **Depends**: M.SRC_NET.042, M.SRC_NET.043, A.U5.01, A.U10.02
- **Blast carried by**: generated `ntp = NTPClient(conn.get_wifi_mode_lock(), conn.network_available_locked, …,
  NtpTiming(…), log=…)` → A.U5.03, A.U5.10, A.U10.18 (GEN cluster); `WifiService.network_available_locked()` →
  M.SRC_NET.0W4 (WiFi getters, below); tests (`make_client()` taking `NtpTiming`, 129 calls; private-attribute readers;
  `network_available` stubs) → A.U5.10, A.U10.35, A.U10.18 (tests cluster); `tests_scripts/test_counter_steps.py`
  exemption table names `_ntp_sec_count`/`_unsynced_wait_s` by their private names → A.U10.05 (tests cluster, name
  follows A.U10.35); SPEC C.7.2 (`retry_s` wording), A.7 `:406` → A.U5.10, A.U10.18 (docs)
- **Kind**: code

### M.SRC_NET.045 A `_set_mgr_cfg()` override refuses a malformed `NTPHost` or `DNSFallback`
- **From**: A.U18.10 (the override; `DNSFallback` check, errno 21), A.U10.41 (`NTPHost` shape at PUT; "joins the same
  override — A-C merges"), M.SRC_NET.018 (`host_label_ok()`)
- **Site**: `src/asy_ntp_client.py`, new private helpers after the constants and a new `_set_mgr_cfg()` method (the
  WiFi shape, `asy_wifi_service.py:690-702`)
- **Change**: module-level `def _ntp_host_ok(value: object) -> bool:` — `type(value) is str and (ipv4_to_int(value)
  is not None or all(len(label) <= DNS_LABEL_MAX and host_label_ok(label) for label in value.split(".")))`, comment "#
  hostName shape: an IPv4 literal, or dot-separated RFC 1123 labels of at most 63 characters."; `def
  _dns_fallback_ok(value: object) -> bool:` — `""`, or at most three comma-separated items each `ipv4_to_int()`-valid
  (so `"8.8.8.8,"`, `"8.8.8.8 ,1.1.1.1"` and four items fail), comment "# ipv4List shape: empty, or up to three
  comma-separated IPv4 literals." `async def _set_mgr_cfg(self, data: "dict[str, CfgValue]", cfg_vals: "ConfigSchema")
  -> "tuple[bool, WriteValidity]":` — builds `refused` from `NTPHost` values failing `_ntp_host_ok()` and
  `DNSFallback` values failing `_dns_fallback_ok()`; logs each `await self.pr.err_s("Refusing", key, "- not a host name
  or IPv4 address" | "- not a list of up to three IPv4 addresses", errno=_ERR_BAD_ARG)`; calls
  `super()._set_mgr_cfg()` with the rest; sets `results[key] = "Invalid"` for each refused key; comment (≤ 2 lines)
  "# NTPHost and DNSFallback are shape-checked before they are stored; the rest of the request goes through /
  # ConfigManager as usual (SPECIFICATION.md C.7.2)." The value type annotation follows A.U11.S01 (`CfgValue`).
- **Resolved**: A.U10.41 lands in U10 but its PUT check needs this override, which A.U18.10 creates in U18: the shape
  check lands with the override in U18 (A.U18.10's Depends: "A-C merges"); U10 carries the 253 bound only.
- **Unit**: U18
- **Depends**: M.SRC_NET.018, M.SRC_NET.021, M.SRC_NET.043, A.U11.S01 (`CfgValue`)
- **Blast carried by**: the `ipv4List`/`hostName` corpus in `tests/_radio_shape_cases.json` and its L1/L0/vitest
  readers → A.U18.10/A.U10.41 (tests/WEB); the L1 PUT-refusal tests → A.U18.10 (tests); catalog: NTP owner uses shared
  errno 21 → A.U2.01 (catalog cluster; shared codes are open to every owner)
- **Kind**: code

### M.SRC_NET.046 Config read, server resolution and the DNS-server callback
- **From**: A.U18.10 (`_get_ntp_config()` reads `DNSFallback`; `_resolve_ntp_server()` takes the list), A.U10.41 (use
  path of the `NTPHost` shape), A.U18.15 (`pr=` to the resolver), A.U2.15 (codes), A.U3.02 (`_episode_log()` goes),
  A.U10.18 (`async with`; the comment's `acquire()` wording), A.U10.39 (names)
- **Site**: `src/asy_ntp_client.py:150-173` `_safe_get_dns_server()`, `_get_ntp_config()`, `_resolve_ntp_server()`
- **Change**: `_safe_get_dns_server()`: comment `:151-153` → "# Must run before taking wifi_mode_lock, never inside
  it: get_dns_server() gates on wifi_mode_lock.locked()" / "# itself, which this client holds during the sync attempt,
  so from inside it always returned None."; the callback failure → `await self.pr.err_s("get_dns_server() callback
  failed:", e, errno=_ERR_CALLBACK)`. `_get_ntp_config() -> "tuple[str, str, int] | None"`: `values = await
  self.cfgmgr.get_str_values(_VAL_NTP_HOST + _VAL_DNS_FALLBACK)`, `offs = await
  self.cfgmgr.get_int_values(_VAL_NTP_OFFSET)`; `None` unless `len(values) == 2 and len(offs) == 1`; a stored host
  failing `_ntp_host_ok()` logs `await self.pr.wrn_s("Stored NTPHost is not a host name, using its default",
  wrnno=_WRN_STORED_DEFAULT)` and uses `_VAL_NTP_HOST[0][2]` (A.U6.29's use-path shape, applied to NTP); returns
  `(host, fallback, offset)`. `_resolve_ntp_server(self, ntp_host: str, dns_server: str | None, fallback: str)`: `servers
  = (() if dns_server is None else (dns_server,)) + tuple(s for s in fallback.split(",") if s)`; `ip = await
  resolve_ipv4(ntp_host, servers, timeout_ms=self.dns_timeout_ms, tries=self.dns_tries, pr=self.pr)`; `None` → `await
  self.pr.err_s("No valid NTP server:", ntp_host, errno=_ERR_NTP_DNS)`; returns `(ip, _NTP_UDP_PORT)`.
- **Resolved**: —
- **Unit**: U18
- **Depends**: M.SRC_NET.023, M.SRC_NET.045, M.SRC_NET.047 (code constants)
- **Blast carried by**: tests (`_RecordingResolver` accepting `pr=`, recorder call tuples with the configured fallback,
  third `_resolve_ntp_server()` argument, stored-host use-path test) → A.U18.10, A.U18.15, A.U10.41 (tests cluster);
  catalog NTP owner uses shared wrnno 10 → A.U2.01 (catalog)
- **Kind**: code

### M.SRC_NET.047 Named error-code block for NTP
- **From**: A.U2.04, A.U2.15 (renumbering, W→E for callbacks), A.U3.02, A.U3.05 (e11/e18 become console lines),
  A.U18.14 (72), A.U18.15 (shared w11), A.U10.41/A.U18.10 (21 for the PUT refusal; shared w10 for the stored-host
  default); register fix 10 (no `CLOCK` code left here)
- **Site**: `src/asy_ntp_client.py`, one block after the imports
- **Change**: `_ERR_CALLBACK = const(14)`, `_ERR_TIMER = const(17)`, `_ERR_BAD_ARG = const(21)`, `_ERR_NTP_DNS =
  const(67)`, `_ERR_NTP_IMPLAUSIBLE = const(68)`, `_ERR_NTP_MALFORMED = const(69)`, `_ERR_NTP_RETRIES = const(70)`,
  `_ERR_NTP_NO_REPLY = const(71)`, `_ERR_NTP_NOT_SENT = const(72)`, `_WRN_STORED_DEFAULT = const(10)`,
  `_WRN_SOCKET_TEARDOWN = const(11)`, `_WRN_NTP_UNSYNC_REPLY = const(40)`. No `_ERR_CLOCK`: `cettime()`'s handler goes
  (M.SRC_NET.053). HEAD's e13 "Invalid NTP server address" site goes (M.SRC_NET.048), so 21 is the PUT refusal only.
- **Resolved**: A.U2.15 maps e19 → 16 CLOCK for `cettime()`; U18 register fix 10 (lead, ruling V.U18.R10) removes that
  handler ("`cettime()`'s handler takes the same rule": no catch), so NTP logs no 16 — with A.U10.06 retiring SYSTEM e2
  and FRAM e86/e88, catalog row 16 has no site left (gap for the catalog cluster, below).
- **Unit**: U18 (staged: U2 writes the renumbered constants for the HEAD sites, U3 removes e11/e18's persistence, U18
  the end state)
- **Depends**: A.U2.01 with U18 register fix 9 (72, w11, w42 text)
- **Blast carried by**: NTP catalog rows and js mock rows → A.U2.01/A.U2.21 (catalog/WEB); tests (22 NTP code
  assertions, `scripts/_digital_twin_ci_suite.py:62, 1026-1027`, bench `test_network_resilience.py` code sets) →
  A.U2.15, A.U18.14 (tests/HW/TWIN clusters)
- **Kind**: code

### M.SRC_NET.048 `_fetch_ntp_reply()`: own write/receive, 48 B, teardown in `finally`
- **From**: A.U18.14 (2) (own `write()`/`recvfrom()`, errno 72), A.U18.15 (1) (`finally` disconnect, w11), A.U18.16
  (48 B), A.U18.19 (source-trust comment), A.U10.38 (`UDPSocket`), A.U2.15/A.U3.02 (codes, direct calls); adherence
  addition (construction guard, G5/R54)
- **Site**: `src/asy_ntp_client.py:175-191`
- **Change**: `cli = UDPSocket(addr, mode="client")` with no surrounding `try`; comment block (2 lines) "# Only the
  connected server's replies reach this socket (lwIP udp_input()); no origin check (SPECIFICATION.md C.7.2)." / "#
  write()/recvfrom()/disconnect() never raise: each returns its None-shaped sentinel (asy_udp_socket.py)."; `try:` `if
  await cli.write(b"\x1b" + bytes(_NTP_PACKET_LEN - 1), timeout_ms=self.ntp_fetch_timeout_ms) is None: await
  self.pr.err_s("NTP request not sent to", addr[0], errno=_ERR_NTP_NOT_SENT); return None` / `msg, _ = await
  cli.recvfrom(_NTP_PACKET_LEN, timeout_ms=self.ntp_fetch_timeout_ms)` / `finally: if not await cli.disconnect(): await
  self.pr.wrn_s("NTP socket teardown did not complete cleanly.", wrnno=_WRN_SOCKET_TEARDOWN)`; then `if msg is None:
  await self.pr.err_s("No reply from NTP server:", addr[0], errno=_ERR_NTP_NO_REPLY)`; `return msg`.
- **Resolved**: HEAD's `try: cli = AsyUDPSocket(addr, …) except (ValueError, TypeError) as e: … errno 13` guarded a
  malformed `addr`; after A.U18.12/A.U18.45 the only caller passes `(ip, _NTP_UDP_PORT)` with `ip` a dotted-quad `str`
  from `resolve_ipv4()`, so no input reaches it: G5/R54 removes it (agent verdict under that rule, OR2.c list). A.U8.11's
  `udp.round_trip_tries_default` rested on this call: dropped with A.U18.14 (M.SRC_NET.029).
- **Unit**: U18
- **Depends**: M.SRC_NET.026, M.SRC_NET.029, M.SRC_NET.042, M.SRC_NET.047
- **Blast carried by**: caller `_run_ntp_sync_attempt()` (M.SRC_NET.050); tests (fake socket exposing
  `write()`/`recvfrom()`/`disconnect()`, never-connected socket → 72, cancelled-fetch teardown, 90 B reply cut to 48,
  `recvfrom(48)` record, construction-failure tests removed) → A.U18.14/A.U18.15/A.U18.16 (tests cluster); L4 garbage
  payload test holds on the console line → A.U18.16 (HW); SPEC C.7.2 source-trust paragraph and both local codes →
  A.U18.19/A.U18.14 (docs); G5/R57 threat model lists NTP source trust → A.U29.01 (docs)
- **Kind**: code

### M.SRC_NET.049 `_parse_ntp_reply()`: direct codes, reachable failures only
- **From**: A.U14.26 (3) (drop `OverflowError`, add `MemoryError`, comment), A.U2.15/A.U3.02 (codes, direct calls),
  A.U10.43 (`raw_seconds` → `raw_s`), A.U10.45 (except order)
- **Site**: `src/asy_ntp_client.py:243-270`
- **Change**: unsynced/KoD branch → `await self.pr.wrn_s("NTP reply unsynchronized or Kiss-of-Death, rejecting:",
  leap_indicator, stratum, wrnno=_WRN_NTP_UNSYNC_REPLY)`; `raw_s = struct.unpack("!I", msg[40:44])[0]`; implausible →
  `errno=_ERR_NTP_IMPLAUSIBLE`; `except (IndexError, MemoryError, OSError, ValueError) as e:` with the comment "#
  malformed/truncated reply (MicroPython's struct raises plain ValueError, not struct.error) or an" / "# allocation
  failure (Part F.1) - treat like no response."; message → `await self.pr.err_s("Unusable NTP response, treating as no
  response:", e, errno=_ERR_NTP_MALFORMED)`.
- **Resolved**: A.U14.26 asks A-C to check errno 69's text ("the reply is malformed", A.U2.01) now that an allocation
  failure lands there too: the site message and the catalog text must both say what is logged — site "Unusable NTP
  response", catalog 69 text "the reply is malformed or could not be parsed" (name `NTP_MALFORMED` kept); agent reading,
  OR2.c list; the catalog half is a gap for the catalog cluster. U18 register fix 10 (no catch for the `_now()` shapes
  and `cettime()`) does not name this site; A.U14.26 (3) stands here (the gmtime of a reply value is not one of those
  shapes).
- **Unit**: U18 (A.U14.26 is U14: staged — U14 writes the except tuple and comment; U18 the code names and message)
- **Depends**: M.SRC_NET.047
- **Blast carried by**: tests (`gmtime` overflow test removed, `_NTP_MAX_PLAUSIBLE_UNIX_TIME < 2**32` structural test,
  `MemoryError("simulated allocation failure")` injection returning `None`, the `:1073-1074` comment) → A.U14.26
  (tests cluster); catalog 69 text → gap (catalog cluster, A.U2.01)
- **Kind**: code

### M.SRC_NET.050 `_run_ntp_sync_attempt()`: renamed callback, console config line, three-value config
- **From**: A.U10.18 (`network_available_locked`, message text), A.U2.15 (callback W→E 14), A.U3.05 (missing config →
  console), A.U18.10 (config tuple, third argument), A.U10.31 (unquote the return annotation if its names are runtime)
- **Site**: `src/asy_ntp_client.py:213-241`
- **Change**: `network_ok = self.network_available_locked()`; except → `await self.pr.err_s("network_available_locked()
  callback failed:", e, errno=_ERR_CALLBACK)`; missing config → `await self._set_synced(value=False)` then
  `self.pr.err("Missing NTP configuration!")` (console, no number); `ntp_host, fallback, ntp_offs = ntp_config`;
  `addr = await self._resolve_ntp_server(ntp_host, dns_server, fallback)`; `tm = await self._parse_ntp_reply(msg,
  ntp_offs)`; the rest unchanged. Return annotation `-> tuple[tuple[int, ...] | None, bool]` unquoted (no
  `TYPE_CHECKING` name).
- **Resolved**: —
- **Unit**: U18
- **Depends**: M.SRC_NET.046, M.SRC_NET.048
- **Blast carried by**: tests (callback-failure code class E, missing-config test now one `CFGMGR_NTP` entry and none in
  NTP's log) → A.U2.15, A.U3.05 (tests cluster)
- **Kind**: code

### M.SRC_NET.051 `_handle_ntp_sync_failure()`: codes, ONE_SHOT backstop comment, private names
- **From**: A.U2.15 (e16 → 17, e17 → 70), A.U18.22 (comment), A.U10.35 (names), A.U10.45 (except order), A.U10.40
  (the key named in the comment), A.U10.44 (the coroutine name in the comments)
- **Site**: `src/asy_ntp_client.py:272-293`
- **Change**: `self._ntp_retry_timer`, `self._ntp_retries`, `self._ntp_sync_trigger_event` throughout; one comment line
  above the `init(` call: "# ONE_SHOT: a dropped fire loses only this retry; _refresh_loop()'s due check starts the
  next sync once NTPInterval (default 12 h) has passed."; the `:278` trailing comment and the `:287-288` comment name
  `_refresh_loop()` instead of `ntp_time_hours_counter()` (A.U10.44); `except (MemoryError, OSError) as e:` otherwise
  unchanged; `errno=_ERR_TIMER`; max retries → `errno=_ERR_NTP_RETRIES`.
- **Resolved**: A.U18.22's text names `NTP_Interv_H`, which A.U10.40 renames to `NTPInterval` in U10 (before U18): the
  comment uses the new key.
- **Unit**: U18
- **Depends**: M.SRC_NET.044, M.SRC_NET.047
- **Blast carried by**: SPEC C.9 ONE_SHOT list with this backstop → A.U18.22/A.U10.14 (docs)
- **Kind**: code

### M.SRC_NET.052 Sync success publishes on the tick age; three helpers go
- **From**: A.U10.06 (`_now()` goes; `set_utc_valid()` first; `TS=utc_now()`), A.U10.03 (`_sync_age.restart(0)`;
  `_increment_last_sync_age()` goes), A.U3.02 (`_episode_log()` and the episode reset go), A.U14.26 (1) (the `_now()`
  handler — dropped, see Resolved), A.U14.15 (`_set_synced()` comment)
- **Site**: `src/asy_ntp_client.py:144-148` `_now()`, `:193-211` `_set_synced()`/`_set_last_sync_age()`/
  `_increment_last_sync_age()`, `:295-316` `_episode_log()`, `_reset_backoff()`, `_handle_ntp_sync_success()`
- **Change**: `_now()`, `_increment_last_sync_age()` and `_episode_log()` are deleted. `_set_synced()`'s comment → "#
  Nothing runs between this get and the set below: an uncontended lock never yields (Part F.1)." / "# get_data() keeps
  the NTP fields typed, not the base class's generic NamedTuple." `_handle_ntp_sync_success()`: first statement
  `set_utc_valid(…)` (A.U10.06's call form), then `self._ntp_retry_timer.deinit()`, `self._ntp_retries = 0`,
  `self._reset_backoff()`, `self._sync_age.restart(0)`, `await self._set_meas_data(NTP(Synced=True, LastSyncAge=0,
  TS=utc_now()))`, `self.pr.one("RTC set to:", tm)`.
- **Resolved**: A.U14.26 (1) turns the `_now()` handler into `except MemoryError`; A.U10.06 deletes `_now()` for a
  `try`-less `utc_now()` — U18 register fix 10 (ruling V.U18.R10) settles it for A.U10.06: A.U14.26 (1) is dropped for
  this site. HEAD's `LastSyncAge` cap `min(current + 1, 0xFFFFFFFF)` (OR105.a (3) breach) goes with
  `_increment_last_sync_age()` (A.U10.03; LEAD/R24 U18 clause superseded, U18 register fix 11).
- **Unit**: U18 (U10 stage: A.U10.03/A.U10.06 edits of these lines land in U10 — `_now()` → `utc_now()`, the tick
  age; U14's comment; U3's `_episode_log()` removal in U3)
- **Depends**: A.U10.02, A.U10.03, A.U10.06, M.SRC_NET.044
- **Blast carried by**: tests (`_increment_last_sync_age()` tests removed, `_now()` overflow tests removed, success
  calls `set_utc_valid`, driven tick source) → A.U10.03, A.U10.06, A.U14.26 (tests cluster); SPEC G.2 "Current UTC
  timestamp", C.9 tick-timer sentence → A.U10.06/A.U10.03 (docs); SPEC F.1 asyncio list → A.U14.15 (docs)
- **Kind**: code

### M.SRC_NET.053 `cettime()` runs without a catch
- **From**: A.U14.26 (2) (`except MemoryError`), U18 register fix 10 ("`cettime()`'s handler takes the same rule": no
  catch), A.U2.15 (e19 → 16 — superseded), A.U18.25/A.U18.26 (tests only)
- **Site**: `src/asy_ntp_client.py:384-414`
- **Change**: the `try:`/`except (OverflowError, ValueError, OSError) as e:` and its `err_s(…, errno=19)` go; the body
  (year, the two switch instants, `now`, the three branches) runs unguarded; `if len(cet) == _GMTIME_FIELDS: return
  GMTimeStruct(*cet)` / `return None` unchanged; no comment about a 2037 limit remains (G4/R15).
- **Resolved**: A.U14.26 (2) vs register fix 10 — the register fix (lead, later, ruling V.U18.R10, U18 ledger "G4/R15 …
  `cettime()`'s handler takes A.U10.06's rule, no catch") settles it; A.U2.15's 16 mapping for this site is superseded.
- **Unit**: U18
- **Depends**: M.SRC_NET.047
- **Blast carried by**: tests `tests/test_asy_ntp_client.py:1535-1541` (`…failure_returns_none_not_raise`) retired, not
  converted → A.U14.26 as corrected by register fix 10 (tests cluster); the switch-date and RTC-step tests → A.U18.25,
  A.U18.26 (tests); callers (generated `LocalTime`, notification window) now see a propagating allocation failure, as
  the register fix intends → no product change; catalog row 16 → gap (catalog)
- **Kind**: code

### M.SRC_NET.054 Timer starters record their outcome; a failed arm is retried from the task
- **From**: A.U18.23 (`_check_armed`, `_tick_armed`, `_rearm_failed_timers()`, comments), A.U10.03 (tick starter via
  `arm_tick_timer()`), A.U14.10 (`Part F.1` pointer), A.U18.44 (`TaskStarter`), A.U10.35 (names), A.U10.45 (except
  order), A.U10.44 (starter names)
- **Site**: `src/asy_ntp_client.py:318-361` starters, `get_task_starters()`, `get_timer_starters()`, stops; new
  `_rearm_failed_timers()`
- **Change**: names (A.U10.44): task starters `start_asy_sync()` (over `_sync_loop()`, was `start_asy_ntp_client()`/
  `asy_ntp_time()`), `start_asy_refresh()` (over `_refresh_loop()`, was `start_asy_ntp_refresh()`/
  `ntp_time_hours_counter()`), `start_asy_sync_age()` (over `_sync_age_loop()`, was `start_asy_sync_age_counter()`/
  `time_counter()`); timer starters `start_check_timer()` (was `start_ntp_timer()`) and `start_sync_age_timer()` (was
  `start_counter_timer()`), stops `stop_check_timer()`/`stop_sync_age_timer()`. `start_check_timer()`: `try: self._ntp_timer.init(period=_NTP_CHECK_INTERV * 1000, mode=Timer.PERIODIC,
  callback=lambda _b: self._ntp_timer_trigger_event.set())` / `self._check_armed = True` / `except (MemoryError, OSError)
  as e:  # alarm-pool exhaustion (ENOMEM, Part F.1): retried at the next sync trigger;` / `# a second failure ends the
  task for the supervisor (_rearm_failed_timers()).` / `self.pr.err("Could not start NTP timer:", e)` / `self._check_armed
  = False`. `start_sync_age_timer()`: `self._tick_armed = arm_tick_timer(self._counter_timer,
  self._time_counter_trigger_event, self.pr, "NTP sync age")`. New `async def _rearm_failed_timers(self) -> bool`: for
  each of the two flags that is `False`, re-arm (the check timer through the same `init`, the tick timer through
  `arm_tick_timer()`); success sets `True`; a second failure persists `await self.pr.err_s("NTP", "check" | "sync-age",
  "timer not armed", errno=_ERR_TIMER)` and returns `False`; returns `True` otherwise. `get_task_starters(self) ->
  "list[TaskStarter]"`; `get_task_starters()` returns the three renamed starters; `get_timer_starters()` the two renamed timer starters.
- **Resolved**: A.U14.10 and A.U18.23 both rewrite the `:337-338` comment (A.U18.23's Depends: "A-C merges the two
  edits of that line") — merged text above keeps A.U14.10's `Part F.1` pointer and A.U18.23's consequence.
- **Unit**: U18 (U10 stage: `arm_tick_timer()`, names; U14 stage: the pointer)
- **Depends**: A.U10.03, M.SRC_NET.044, M.SRC_NET.047
- **Blast carried by**: tests (arm/degrade tests gain `_check_armed`/`_tick_armed`, second failure ends the task with
  one 17, restarted task re-arms; every starter/coroutine called by name) → A.U18.23, A.U10.44 (tests); device scripts
  starting tasks by name → A.U10.44 (HW); twin 16-alarm pool L2 case → U25 (TWIN cluster, A.U18.23's twin
  clause); SPEC C.9 retry point → A.U18.23/A.U10.14 (docs)
- **Kind**: code

### M.SRC_NET.055 `ntp_force_sync()` clears `Synced` with the age
- **From**: A.U18.21, A.U10.35 (names)
- **Site**: `src/asy_ntp_client.py:416-422`
- **Change**: first statement → one publish: `data = await self.get_data()` / `await
  self._set_meas_data(NTP(Synced=False, LastSyncAge=None, TS=data.TS))` with the one-line comment "# A settings change
  clears Synced, as legacy did: nothing runs on a sync taken under the old settings (owner, 2026-09-29)."; then
  `self._ntp_retry_timer.deinit()`, `self._ntp_retries = 0`, `self._reset_backoff()` (its comment kept),
  `self._ntp_sync_trigger_event.set()`, `self.pr.evt("Force resync triggered.")`.
- **Resolved**: —
- **Unit**: U18
- **Depends**: M.SRC_NET.044, M.SRC_NET.052
- **Blast carried by**: generated `SettingsGroup(ntp, …, post_asy_fct=ntp.ntp_force_sync)` and the boot's last step
  unchanged (A.U18.21); tests (synced start then force-sync → unsynced; per-device `PUT /networking {"NTPHost": …}`
  scenario; the stale "Setters are explicitly out of scope" comment) → A.U18.21 (tests); SPEC C.7.2/DEVICE_REFERENCE →
  A.U18.21 (docs)
- **Kind**: code

### M.SRC_NET.056 `_sync_loop()`: no lazy logger setup, `async with`, timer re-arm
- **From**: A.U10.44 (`asy_ntp_time()` → `_sync_loop()`), A.U10.10 (`pr.setup()` `:425-426` goes), A.U10.06
  (`TS=utc_now()` `:427`), A.U10.18 (`async with`), A.U18.23 (`_rearm_failed_timers()` before the first wait and after
  each wake), A.U10.35 (names)
- **Site**: `src/asy_ntp_client.py:424-444` `asy_ntp_time()`
- **Change**: `async def _sync_loop(self) -> None:` — `await self._set_meas_data(NTP(Synced=False, LastSyncAge=None, TS=utc_now()))`; `if not await
  self._rearm_failed_timers(): return`; loop: `await self._ntp_sync_trigger_event.wait()`, `if not await
  self._rearm_failed_timers(): return`, `self.pr.evt("NTP sync starting.")`, `dns_server = await
  self._safe_get_dns_server()  # read before taking wifi_mode_lock - see _safe_get_dns_server()`, `async with
  self.wifi_mode_lock: tm, network_ok = await self._run_ntp_sync_attempt(dns_server)`, then the unchanged backoff
  lines with their two-line comment.
- **Resolved**: —
- **Unit**: U18 (U10 stage: setup removal, `utc_now()`, `async with`)
- **Depends**: M.SRC_NET.050, M.SRC_NET.054, A.U10.10 (`SensorReaderConfig.setup()` sets up the logger in the batch)
- **Blast carried by**: tests pinning lazy setup (`tests/test_asy_ntp_client.py:1880-1895`) → A.U10.10 (tests);
  L1 lock-hold tests (`tests/test_ntp_wifi_dns_integration.py`) → A.U18.34 (tests); SPEC C.8 lock table → A.U18.34 (docs)
- **Kind**: code

### M.SRC_NET.057 `_refresh_loop()`: staleness on the tick age, console config line
- **From**: A.U10.44 (`ntp_time_hours_counter()` → `_refresh_loop()`), A.U18.20 (stale test on `_sync_age`, comment),
  A.U3.05 (errno 18 → console), A.U10.39 (name), A.U10.35 (names)
- **Site**: `src/asy_ntp_client.py:446-474` `ntp_time_hours_counter()`
- **Change**: `async def _refresh_loop(self) -> None:`; `ntp_interv = await self.cfgmgr.get_int_values(_VAL_NTP_INTERVAL)`; missing → `ntp_interv = [12]` and
  `self.pr.err("Missing NTP configuration, defaulting interval to 12h!")` (console); synced branch → the two-line comment
  "# Stale once the last success is _NTP_ASYNC_INTERV intervals old; a failed due resync resets only the due cadence,
  never this age" / "# (agent, 2026-09-27; legacy's intent, legacy/firmware/python/CommonDrivers/async_connect.py:450-461)."
  then `if self._sync_age.read() >= _NTP_ASYNC_INTERV * ntp_interv[0] * 3600: await self._set_synced(value=False)`
  `else: self._ntp_sec_count += _NTP_CHECK_INTERV`; the due logic and resets unchanged with private names.
- **Resolved**: —
- **Unit**: U18
- **Depends**: M.SRC_NET.044, M.SRC_NET.052, A.U1.01 (the cited legacy path)
- **Blast carried by**: `NTPSynced` consumers already handle `False` (A.U18.20); tests (the legacy-pin test inverted,
  driven tick source past 3 h, 5-day bound on `_ntp_sec_count`) → A.U18.20 (tests); SPEC C.7.2/DEVICE_REFERENCE →
  A.U18.20 (docs)
- **Kind**: code

### M.SRC_NET.058 `_sync_age_loop()` publishes the tick age
- **From**: A.U10.03, A.U10.44 (`time_counter()` → `_sync_age_loop()`), A.U10.35 (names)
- **Site**: `src/asy_ntp_client.py:476-483` `time_counter()`
- **Change**: `async def _sync_age_loop(self) -> None:` — `await self._set_last_sync_age(value=None)`; loop: `await self._time_counter_trigger_event.wait()`; synced
  → `await self._set_last_sync_age(value=self._sync_age.read())`, else `value=None`.
- **Resolved**: —
- **Unit**: U10
- **Depends**: A.U10.02
- **Blast carried by**: generated `NTPLastSyncAge` key (A.U10.40) unchanged value semantics; tests (driven ticks, 2.5 s
  wake → age +2) → A.U10.03 (tests)
- **Kind**: code

### M.SRC_NET.059 Member order per D.15 (NTP client)
- **From**: A.U10.33
- **Site**: `src/asy_ntp_client.py` class `NTPClient`
- **Change**: pure reorder by D.15's key (A.U10.32), AST-verified; members added later (`_set_mgr_cfg()`,
  `_rearm_failed_timers()`, the module helpers `_ntp_host_ok()`/`_dns_fallback_ok()`) are placed by the same key when
  written in U18.
- **Resolved**: —
- **Unit**: U10 (last U10 edit)
- **Depends**: every U10 edit of the file
- **Blast carried by**: —
- **Kind**: code
