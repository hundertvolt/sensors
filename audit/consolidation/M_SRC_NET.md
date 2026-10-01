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
    disconnect raise, were e2/e3), `_WRN_SOCKET_TEARDOWN = const(12)` (shared, A.U18.15; was w3 → 43, now 12),
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
  added twice. DNSSRV w3 → 43 (A.U2.16) vs → shared 11 (A.U18.15) — U18 register fix 9 settles the shared code, 43 unassigned; its
  number is W12 after gap pass G2: M.SRC_SENS.043, the later merge, gives W11 to `DERIVED_DOMAIN` (SUPP_recovery conflicts row 7); the catalog takes W12 (M.GEN.034; G1 hand-off H1; M_SRC_SENS GAP-7, M_TEST_UNIT GAP-U5). w2
  name `DNS_BAD_REQUEST` (A.U2.01) vs `DNS_RECV_FAILED` (A.U18.06) — U18 register fix 9 settles `DNS_RECV_FAILED`.
- **Unit**: U31 (A.U31.16, the latest constituent: the backoff constants in milliseconds; see Staging for the earlier
  stages)
- **Depends**: M.SRC_NET.001, M.SRC_NET.020, M.SRC_NET.021, M.SRC_NET.022 (the constants imported); A.U2.01 catalog
  (with the U18 register-fix-9 edits), A.U5.01 (`LogConfig`), A.U10.46 (`ErrorSource`), A.U8.02 (tag grammar)
- **Blast carried by**: catalog rows (w42 text, w43 unassigned, shared w11, DNSSRV uses e10) → A.U2.01 with U18 register
  fix 9 (catalog cluster); Part N rows → A.U8.11/A.U31.16 (docs cluster); tests `tests/test_captive_dns.py` timing
  literals tagged against these IDs → A.U8C.23, A.U8C2.07, A.U8C.120 (tests cluster); `tests_hardware/README.md:879`
  "`wrnno=2`" → A.U2.16/A.U18.06/A.U26 wording (docs cluster)
- **Kind**: code
- **Staging**: U2 (A.U2.16) writes `_ERR_BAD_ARG`/`_ERR_UNEXPECTED`/`_WRN_DNS_REPLY_DROPPED`/`_WRN_DNS_BAD_REQUEST` (41-43
  as A.U2.16) at `:91, 119, 123, 135, 147, 153`, because U2's L0 catalog check (A.U2.02) must pass from U2 on; U8
  (A.U8.11) tags the HEAD seconds constants and adds `_ERROR_RETRY_WAIT_S`; U10 renames the imports (A.U10.37/38); U18
  writes the imports, `_QTYPE_ANY`, the deletions and the code block above (42 renamed, 43 → shared 12); U31 (A.U31.16)
  turns the two backoff constants into the `_MS` pair with their `_ms` tag IDs. State after each stage: every DNSSRV call
  site passes a named constant (U2); tagged (U8); renamed names (U10); the end state except the backoff unit (U18); the
  end state (U31).

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
- **Blast carried by**: construction `WifiService` → M.SRC_NET.078 (`CaptiveDNS(log=log)`);
  tests `tests/test_captive_dns.py` (10 constructor calls, `udps` reads, `reset_error_counter` return) → A.U5.02,
  A.U10.35, A.U11.31 (tests cluster); `_collect_error_sources()` generated → A.U10.46 (GEN cluster); `/status`
  `ResetErrors` → M.SRC_NET.123
- **Kind**: code
- **Staging**: U5: constructor signature `log` (A.U5.02; all constructors move together, generated code A.U5.03
  in the same unit); U10: `_udps`, unquote, names (A.U10.31/35/37/38); U11: `-> bool` (A.U11.31 co-lands across all
  error sources); U18: `-> "list[ErrorSource]"`. Each stage is a prerequisite of the cross-module change of its own
  unit (constructor sweep, attribute sweep, `ResetErrors` sweep).

### M.SRC_NET.007 CaptiveDNS.run(): bound receive, typed logging, local-failure branch, re-raised cancel
- **From**: A.U18.03 (512 B), A.U18.04 (fixed message + args), A.U18.06 (bind failure vs receive failure), A.U18.07
  (`try`/`finally`, cancel re-raised), A.U18.08 (`ipv4_to_int`), A.U18.15 (teardown wrnno 12), A.U2.16 (numbers),
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
  ini - 11 > DNS_NAME_MAX: raise ValueError("name longer than 255 octets")`. `self.data` → `self._data` (no reader outside the class; G10/R07,
  gap pass G2 for M_SRC_CORE GAP-G12; every use follows, M.SRC_NET.009). Everything else unchanged; the
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
- **Change**: `:201` `ipv4_to_int(ip) is None`; then `qtype = self._data[self._question_end - 4 :
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

### M.SRC_NET.011 Every broad handler records a C-stack overflow (captive DNS)
- **From**: A.U30.19 (2) (first statement `report_if_fatal(<name>)`, an `as e` binding added where absent)
- **Site**: `src/asy_captive_dns.py` HEAD `:105` (address-parse `except Exception:`), `:133` (loop top), `:144`
  (disconnect), `:187` (`DNSQuery` parse `except Exception:`)
- **Change**: each handler's first statement is `report_if_fatal(e)`: `:105` → `except Exception as e:` /
  `report_if_fatal(e)` / `addr_int = None`; `:133` and `:144` gain it above their `err_s(...)` (the texts M.SRC_NET.007
  writes); `:187` → `except Exception as e:` / `report_if_fatal(e)` / the two sentinel assignments. Import `from
  asy_print_log import report_if_fatal` beside the other runtime imports (M.SRC_NET.004; its home is `asy_print_log`,
  M.SRC_CORE.034 — M_SRC_CORE GAP-G8, M_TEST_UNIT GAP-U6, gap pass G2). A handler that M.SRC_NET.007
  or .008 rewrites keeps the call as its first statement; no handler of the file ends in a bare `raise`.
- **Resolved**: —
- **Unit**: U30 (M.SRC_NET.007's U31 stage writes those two handlers with the call already in place)
- **Depends**: A.U30.19 (`report_if_fatal()` in `asy_print_log`, M.SRC_CORE.034), M.SRC_NET.007, M.SRC_NET.008
- **Blast carried by**: `tests_scripts/test_fatal_report_sites.py` (L0 site check) → A.U30.19 (tests); UART-free, no
  changelog entry
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
  `asy_ntp_client`/`codegen.py` sites → A.U8.09 and M.SRC_NET.042; tests
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
  M.SRC_NET.045; tests moved to `tests/test_asy_dns_client.py`, comment rewrites in
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
  bounds → A.U18.09 (docs); the `NTPHost` PUT shape check → M.SRC_NET.045
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
  `except (IndexError, ValueError)` arm unchanged. A module-level `_WRN_SOCKET_TEARDOWN = const(12)` joins the constants
  (A.U2.04 idiom; shared code, U18 register fix 9).
- **Resolved**: HEAD's `try: cli = AsyUDPSocket((server, port), …) except (ValueError, TypeError): continue  # malformed
  port` guards only a caller-supplied `port`; after A.U18.45 the port is the constant 53, `server` is a validated `str`
  and `mode` a literal, so no input reaches the arm (A.U18.12's constructor raises only for a non-`(str, int)` tuple or
  a bad mode). G5/R54 ("A branch that no input can reach is removed", owner, OR46.a (2)) settles its removal; its comment
  would otherwise state a false cause (docs hold current state). Agent decision under that rule, listed for OR2.c.
- **Unit**: U18
- **Depends**: M.SRC_NET.020, M.SRC_NET.021, M.SRC_NET.022, M.SRC_NET.026 (constructor), M.SRC_NET.029
  (`write_and_recvfrom()` with required `tries`); A.U2.01 + U18 register fix 9 (shared wrnno 12, W12 after gap pass G2: M.SRC_SENS.043, the later merge, gives W11 to `DERIVED_DOMAIN` (SUPP_recovery conflicts row 7); the catalog takes W12 (M.GEN.034; G1 hand-off H1; M_SRC_SENS GAP-7, M_TEST_UNIT GAP-U5))
- **Blast carried by**: caller `asy_ntp_client` `_resolve_ntp_server()` passes `pr=self.pr` and the configured
  fallback → M.SRC_NET.046; tests (`pr=make_pr()` on every call, `port=` calls through
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

### M.SRC_NET.018 One host-label check, `host_label_ok()`, lives beside `ipv4_to_int()`
- **From**: A.U6.29 (`_host_label_ok()`, written in `asy_wifi_service.py`), A.U10.41 (the NTP host shape applies "the
  product's `_host_label_ok()` of A.U6.29 per label"), REF/R05 (a helper is written once and imported), G10/R07 (a name
  another module imports is public)
- **Site**: `src/asy_dns_client.py` (new public function next to `ipv4_to_int()`); removed from
  `src/asy_wifi_service.py`
- **Change**: `def host_label_ok(label: str) -> bool:` — `False` for an empty string; otherwise every character an
  ASCII letter, digit or `-`, first and last not `-` (RFC 1123 §2.1), a plain loop over `ord()` (no `re`); comment
  "# RFC 1123 SS2.1 host label (letters, digits, '-'; not at either end); the caller bounds the length." Placed by
  D.15's key. `asy_wifi_service` (Hostname, M.SRC_NET.075) and `asy_ntp_client` (`NTPHost` per label, M.SRC_NET.045)
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
- **Blast carried by**: product constructions `asy_dns_client` (M.SRC_NET.023), `asy_ntp_client` (M.SRC_NET.048),
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
- **Blast carried by**: `asy_dns_client` passes `tries=tries` (M.SRC_NET.023); NTP stops using it (M.SRC_NET.048);
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
  `TYPE_CHECKING` block: `Callable`; `from asy_base_classes import JsonMapping, TaskStarter` (`JsonMapping`: gap pass G2,
  the override's raw-body parameter, M.SRC_NET.045); `from asy_config_manager import
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
  (comment names `WifiService`; a lock, R17's name kept); `_network_available_locked` (comment
  "WifiService.network_available_locked - caller must hold wifi_mode_lock"); `_get_dns_server` (comment names
  `WifiService.get_dns_server_ip`); `_dns_timeout_ms`, `_dns_tries`, `_ntp_fetch_timeout_ms` from `timing`; `_retry_s =
  max(timing.retry_s, _NTP_CHECK_INTERV)`, `_retry_max_s = max(timing.retry_max_s, self._retry_s)` (gap pass G2: none has
  a reader outside the class in `src/` or the generated code — G10/R07 "private by default", M_SRC_CORE GAP-G12; every
  use follows, M.SRC_NET.046/.048/.050/.056); `_retry_wait_s`, `_unsynced_wait_s` as today; `_episode_errs`/`_episode_wrns`
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
  M.SRC_NET.098; tests (`make_client()` taking `NtpTiming`, 129 calls; private-attribute readers;
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
  comma-separated IPv4 literals." `async def _set_mgr_cfg(self, data: "JsonMapping", cfg_vals: "ConfigSchema")
  -> "tuple[bool, WriteValidity]":` — builds `refused` from `NTPHost` values failing `_ntp_host_ok()` and
  `DNSFallback` values failing `_dns_fallback_ok()`; logs each `await self.pr.err_s("Refusing", key, "- not a host name
  or IPv4 address" | "- not a list of up to three IPv4 addresses", errno=_ERR_BAD_ARG)`; calls
  `super()._set_mgr_cfg()` with the rest; sets `results[key] = "Invalid"` for each refused key; comment (≤ 2 lines)
  "# NTPHost and DNSFallback are shape-checked before they are stored; the rest of the request goes through /
  # ConfigManager as usual (SPECIFICATION.md C.7.2)." `data` is the raw body (`JsonMapping`, the base's parameter after U19 A-C note 2 — M.SRC_CORE.038; gap pass G2), whose
  values the two shape checks already take as `object`.
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
  resolve_ipv4(ntp_host, servers, timeout_ms=self._dns_timeout_ms, tries=self._dns_tries, pr=self.pr)`; `None` → `await
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
  A.U18.14 (72), A.U18.15 (shared w12; W12 after gap pass G2: M.SRC_SENS.043, the later merge, gives W11 to `DERIVED_DOMAIN` (SUPP_recovery conflicts row 7); the catalog takes W12 (M.GEN.034; G1 hand-off H1; M_SRC_SENS GAP-7, M_TEST_UNIT GAP-U5)), A.U10.41/A.U18.10 (21 for the PUT refusal; shared w10 for the stored-host
  default); register fix 10 (no `CLOCK` code left here)
- **Site**: `src/asy_ntp_client.py`, one block after the imports
- **Change**: `_ERR_CALLBACK = const(14)`, `_ERR_TIMER = const(17)`, `_ERR_BAD_ARG = const(21)`, `_ERR_NTP_DNS =
  const(67)`, `_ERR_NTP_IMPLAUSIBLE = const(68)`, `_ERR_NTP_MALFORMED = const(69)`, `_ERR_NTP_RETRIES = const(70)`,
  `_ERR_NTP_NO_REPLY = const(71)`, `_ERR_NTP_NOT_SENT = const(72)`, `_WRN_STORED_DEFAULT = const(10)`,
  `_WRN_SOCKET_TEARDOWN = const(12)`, `_WRN_NTP_UNSYNC_REPLY = const(40)`. No `_ERR_CLOCK`: `cettime()`'s handler goes
  (M.SRC_NET.053). HEAD's e13 "Invalid NTP server address" site goes (M.SRC_NET.048), so 21 is the PUT refusal only.
- **Resolved**: A.U2.15 maps e19 → 16 CLOCK for `cettime()`; U18 register fix 10 (lead, ruling V.U18.R10) removes that
  handler ("`cettime()`'s handler takes the same rule": no catch), so NTP logs no 16 — with A.U10.06 retiring SYSTEM e2
  and FRAM e86/e88, catalog row 16 has no site left (gap for the catalog cluster, below).
- **Unit**: U18 (staged: U2 writes the renumbered constants for the HEAD sites, U3 removes e11/e18's persistence, U18
  the end state)
- **Depends**: A.U2.01 with U18 register fix 9 (72, w12, w42 text)
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
  await cli.write(b"\x1b" + bytes(_NTP_PACKET_LEN - 1), timeout_ms=self._ntp_fetch_timeout_ms) is None: await
  self.pr.err_s("NTP request not sent to", addr[0], errno=_ERR_NTP_NOT_SENT); return None` / `msg, _ = await
  cli.recvfrom(_NTP_PACKET_LEN, timeout_ms=self._ntp_fetch_timeout_ms)` / `finally: if not await cli.disconnect(): await
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
- **Change**: `network_ok = self._network_available_locked()`; except → `await self.pr.err_s("network_available_locked()
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

### M.SRC_NET.060 Every broad handler records a C-stack overflow (NTP)
- **From**: A.U30.19 (2)
- **Site**: `src/asy_ntp_client.py` HEAD `:156` (`get_dns_server` callback guard), `:216`
  (`network_available_locked()` callback guard)
- **Change**: each `except Exception as e:` gains `report_if_fatal(e)` as its first statement, above the logging line
  M.SRC_NET.046/.050 write; `from asy_print_log import report_if_fatal` joins the runtime imports (M.SRC_NET.041; GAP-G8, gap pass G2). Every
  other handler of the end state names its exception types (M.SRC_NET.048/.049/.054), so none else needs it.
- **Resolved**: —
- **Unit**: U30
- **Depends**: A.U30.19, M.SRC_NET.041, M.SRC_NET.046, M.SRC_NET.050
- **Blast carried by**: `tests_scripts/test_fatal_report_sites.py` → A.U30.19 (tests)
- **Kind**: code

## src/asy_wifi_service.py

### M.SRC_NET.070 Module docstring and header comment state current facts
- **From**: A.U10.37 (file names in text), A.U18.36 (C.7 per-site pointer), A.U10.44 (loop name); adherence finding
  (`:6` "errno numbering starts at 11, same convention as asy_ntp_client.py" is false after A.U2.14)
- **Site**: `src/asy_wifi_service.py:1-6`
- **Change**: docstring `:2` "extends base_classes.py's SensorReaderConfig" → "extends asy_base_classes.py's
  SensorReaderConfig"; comment `:4-6` → "# "Attempt" operations persist a real errno via self.pr.err_s() and set
  self._hw_op_failed, feeding" / "# _connect_loop()'s _error_check() streak; routine state observations stay
  print-only via self.pr.err()" / "# (SPECIFICATION.md C.7 lists every site; error numbers come from the one catalog,
  C.7.1)."
- **Resolved**: the stale numbering sentence has no carrying action; CLAUDE.md "docs hold current state" settles the
  rewrite (as M.SRC_NET.040 for NTP).
- **Unit**: U18
- **Depends**: M.SRC_NET.100
- **Blast carried by**: SPEC C.7 WIFI paragraph with the per-site review → A.U18.36 (docs)
- **Kind**: code

### M.SRC_NET.071 Imports follow the renames, the primitives and the removals
- **From**: A.U10.37, A.U10.38, A.U10.03 (`TickSeconds`, `arm_tick_timer`; `LockedCounter` goes), A.U10.06
  (`utc_now`), A.U5.01/A.U5.02 (`LogConfig`, `DEFAULT_LOG`), A.U18.40 (`Pin` goes), A.U18.44 (`Any` goes), A.U10.46
  (`TaskStarter`, `ErrorSource`), A.U10.39 (`name_cfg`, `schema_names`), A.U19.16 (`INVALID`), M.SRC_NET.018
  (`host_label_ok`), A.U11.S01 (`CfgValue`)
- **Site**: `src/asy_wifi_service.py:8-37`
- **Change**: runtime: `asyncio`, `namedtuple`, `network`, `from machine import Timer`, `const`; `from asy_base_classes
  import SensorReaderConfig, TickSeconds, arm_tick_timer, utc_now`; `from asy_captive_dns import CaptiveDNS`; `from
  asy_config_manager import INVALID, make_dict, name_cfg, schema_dict, schema_names`; `from asy_dns_client import
  host_label_ok`; `from asy_print_log import DEFAULT_LOG, LogConfig`; `import time` goes (its one user `_now()` goes).
  `TYPE_CHECKING`: `Protocol`; `from asy_base_classes import ErrorSource, JsonMapping, TaskStarter` (`JsonMapping`: gap pass
  G2, M.SRC_NET.096); `from asy_config_manager import
  CfgValue, ConfigSchema, FieldSchema, WriteValidity`; `from asy_print_log import ErrorLog, PrintLogHistory`; the
  `LEDControl` Protocol unchanged; no `Any`, no `Callable` (its users are the starters, now `TaskStarter`), no
  FRAM-manager import.
- **Resolved**: —
- **Unit**: U19 (A.U19.16's `INVALID` is the latest; each other import lands with its user's unit)
- **Depends**: A.U10.02, A.U10.03, A.U10.06, A.U5.01, A.U19.16, M.SRC_NET.018
- **Blast carried by**: —
- **Kind**: code

### M.SRC_NET.072 Schema tuples: names follow the keys, each bound states its reason
- **From**: A.U10.39 (`_VAL_` names), A.U10.40 (`LedWifiOn` → `LEDWifiOn`), A.U10.41 (each string bound's reason at its
  `_VAL_`), A.U0.35 + A.U29.03 (the `HotspotPW` comment), A.U6.30 (Country shape)
- **Site**: `src/asy_wifi_service.py:40-53`
- **Change**: `_VAL_SSID` (comment `:41-42` kept: 0-32 octets, 0 = "not configured" sentinel), `_VAL_PW` (comment
  `:44-45` kept), `_VAL_COUNTRY = const((("Country", "str", "DE", 2, 2, None),))  # ISO 3166-1 alpha-2, checked by
  _country_ok()`, `_VAL_HOSTNAME = const((("Hostname", "str", "SensorNode", 1, 32, None),))  # 32 =
  MICROPY_PY_NETWORK_HOSTNAME_MAX_LEN (extmod/modnetwork.h:58-60, v1.29.0)`, `_VAL_LED_WIFI_ON =
  const((("LEDWifiOn", "bool", True, None, None, None),))`; the `HotspotPW` comment `:50-52` → "# Hotspot AP password -
  real WPA2-PSK length (8-63), defaulting to the hardcoded "12345678": accepted" / "# permanently as a known limitation
  (owner, 2026-09-26; SPECIFICATION.md A.11), made per-device configurable." / "# Masked like _VAL_PW."; `_VAL_HOTSPOT_PW`
  value unchanged (the default stays "12345678": CLAUDE.md's accepted credential, no change without the owner).
- **Resolved**: A.U10.41 writes "`SSID` 1-32 bytes" among the bounds that "are re-checked and stay"; HEAD's `SSID`
  minimum is 0, the "not configured" sentinel that routes to the hotspot (`:41-42`, `:441-443`). "Stay" is the operative
  word (a 1-byte minimum would make an unconfigured unit's default invalid): the bound stays 0-32; A.U10.41's "1-32" is
  read as a slip. Settled by A.U10.41's own "stay".
- **Unit**: U29 (A.U29.03 is the latest; staged: U0 comment wording (A.U0.35), U10 names/keys/reasons, U29 the A.11
  pointer)
- **Depends**: A.U29.01 (A.11 exists)
- **Blast carried by**: every key rename consumer (definitions, js, mockdata, tests, docs) → A.U10.40 (other clusters);
  `tests_scripts/test_tests_hardware_conftest_constants.py:62, 79` (`_VAL_HOST` → `_VAL_HOSTNAME`) → A.U10.39 (tests);
  `buildgen/validate.py` AST reads of `_VAL_HOST`/`_VAL_HOTSPOT_PW` bounds → A.U20.27 (GEN; names follow);
  CLAUDE.md credential bullet → A.U29.03 (docs)
- **Kind**: code

### M.SRC_NET.073 Web tags: identity group label, byte and shape keys, HotspotPW published
- **From**: A.U6.18 (`submitLabel`), A.U6.28 (`bytes=true`), A.U6.29 (`shape=hostLabel`), A.U6.30 (`shape=countryCode`,
  description), A.U18.38 (`HotspotPW` tag), A.U10.40 (`LEDWifiOn`), M_WEB gap 3 (`PW`'s `special:`; gap pass G2)
- **Site**: `src/asy_wifi_service.py:55-62`
- **Change**: `# @web-group section=networking submitGroup=identity label="Wi-Fi & Identity" submit=true
  submitLabel="Apply & Reconnect"`; `# @web SSID … label="Wi-Fi SSID" bytes=true`; `# @web PW … label="Wi-Fi Password"
  mask=true bytes=true special:""="Open network"` (the schema special `""` reaches the definitions with its label: gap
  pass G2 — M_WEB gap 3, G1 hand-off H2, M.GEN.017/.046 emit it; OR43.a (2) "field for field"); `# @web Country … label="Country" bytes=true shape=countryCode description="Two uppercase letters
  (ISO 3166-1 alpha-2), e.g. DE."`; `# @web Hostname … label="Hostname" bytes=true shape=hostLabel`; `# @web HotspotPW
  section=networking submitGroup=identity label="Hotspot Password" mask=true bytes=true description="Password of the
  fallback hotspot (8-63 characters)."`; the `wifiLed` group unchanged; `# @web LEDWifiOn section=networking
  submitGroup=wifiLed label="Wi-Fi Status LED"`.
- **Resolved**: —
- **Unit**: U18 (A.U18.38 and the `PW` `special:` with M.GEN.017's U18 stage, string specials; staged: U6
  `submitLabel`/`bytes`/`shape`, U10 key rename)
- **Depends**: A.U6.02, A.U6.04 (definitions from tags), A.U6.28/A.U6.29 (tag keys)
- **Blast carried by**: `codegen.py:607` identity `SettingsGroup` gains `"HotspotPW"` → A.U18.38 (GEN); js mock masks
  `HotspotPW`, shape and byte mirrors, hint → A.U18.38/A.U6.28/A.U6.29/A.U6.30 (WEB); `mockdata/samples.json` →
  A.U18.38 (WEB); `tests_scripts/test_buildgen_web_tag.py:492`, A.U6.28's byte-field check (drops its `HotspotPW`
  exception) → A.U18.38 (tests); hardware PUT matrices walking the identity group now write `HotspotPW` behind
  `persistence_write` → A.U18.38/U26 (HW); SPEC H placement → A.U18.38 (docs)
- **Kind**: code

### M.SRC_NET.074 The snapshot tuple carries every networking field
- **From**: A.U18.33, A.U10.40 (`Rssi` → `RSSI`)
- **Site**: `src/asy_wifi_service.py:64-68`
- **Change**: `WIFI = namedtuple("WIFI", ("Mode", "Connected", "IP", "Subnet", "Gateway", "DNS", "RSSI", "TS"))` and
  `_FIELDS = const(("Mode", "Connected", "IP", "Subnet", "Gateway", "DNS", "RSSI", "TS"))`; comments unchanged.
- **Resolved**: A.U18.33 names the new field `Rssi` and leaves `IP` vs `IPv4` to "A.U10.40's key-scheme call (A-C)";
  A.U10.40 (U10, earlier) renames the REST key `Rssi` → `RSSI`, so U18 writes `RSSI`. `IP`/`IPv4` is a generated-block
  key question (the site is `buildgen/codegen.py`), listed as a gap for the GEN cluster.
- **Unit**: U18
- **Depends**: —
- **Blast carried by**: generated `_networking_status()` reads the snapshot once → A.U18.33 (GEN); snapshot tests →
  A.U18.33 (tests); mockdata keys → A.U18.33/A.U10.40 (WEB)
- **Kind**: code

### M.SRC_NET.075 Radio value checks: bytes, host label, country; the per-device default
- **From**: A.U6.29 (`_radio_value_ok()`, host label at PUT/use/`_with_default()`), A.U6.30 (`_country_ok()`),
  A.U10.39 (keys through `name_cfg()`/`schema_names()`), A.U18.40 (`_with_default()`'s `None` branch goes), A.U10.31
  (unquote), M.SRC_NET.018 (`host_label_ok()` imported, no local copy)
- **Site**: `src/asy_wifi_service.py:71-97` (`_RADIO_FIELDS`, `_radio_bytes_ok()`, `_with_default()`)
- **Change**: comment `:71-72` kept; `_RADIO_FIELDS = schema_names(_VAL_SSID + _VAL_PW + _VAL_COUNTRY + _VAL_HOSTNAME
  + _VAL_HOTSPOT_PW)` (a runtime tuple of the five keys; no key literal). `def _country_ok(value: str) -> bool:` — exactly
  two characters, each `A`-`Z` (comment "# ISO 3166-1 alpha-2 in the cyw43 table's uppercase (cyw43_country.h:49)").
  `_radio_bytes_ok()` → `def _radio_value_ok(field: "FieldSchema", value: object) -> bool:` — HEAD's early `return True`
  for a non-`str`, the special value, or a value outside the character bounds (left to the schema check); then `False`
  if `len(value.encode()) > high`; then `host_label_ok(value)` when `field[0] == name_cfg(_VAL_HOSTNAME)`,
  `_country_ok(value)` when `field[0] == name_cfg(_VAL_COUNTRY)`, else `True`; its comment (≤ 3 lines) states the three
  checks. `_with_default(schema: tuple[tuple[str, str, str, int, int, str | None], ...], value: str) -> …` (unquoted):
  the `if value is None: return schema` lines go; the bound check becomes `if kind != "str" or not (low <= len(value) <=
  high) or not _radio_value_ok(schema[0], value): return schema`; its second comment block says "outside the field's
  bounds or shape".
- **Resolved**: A.U6.28's L0 check AST-reads `_RADIO_FIELDS` as a `const()` tuple of key literals; A.U10.39 (G10/R11:
  "Code names a key only through `name_cfg(_VAL_X)`, never a repeated literal", listing `:73`) removes those literals.
  G10/R11 governs the product; A.U6.28's check reads the `_VAL_` names inside the `schema_names()` call and resolves
  their keys with `extract_field_schemas()` instead (gap for the tests cluster, below). A.U6.29's `field[0] ==
  "Hostname"` is written with `name_cfg()` for the same rule.
- **Unit**: U18 (the helper import from M.SRC_NET.018; staged: U6 writes `_radio_value_ok()`/`_country_ok()` with a
  private host-label helper, U10 the `name_cfg()`/`schema_names()` form, U18 the import and the `_with_default()` edit)
- **Depends**: M.SRC_NET.018, M.SRC_NET.072
- **Blast carried by**: callers `_set_mgr_cfg()` (M.SRC_NET.096), `_radio_values()`/`_value_in_use()`
  (M.SRC_NET.096), `__init__` (M.SRC_NET.078); corpus `tests/_radio_shape_cases.json` and the L1/L0/vitest readers →
  A.U6.29/A.U6.30 (tests/WEB); byte-bound tests calling `_radio_bytes_ok` by name → A.U6.29 (tests); build-side
  hostname rule → A.U6.29 (GEN)
- **Kind**: code

### M.SRC_NET.076 Wiring tags pass the LED and the log config at construction
- **From**: A.U5.07 (`led_target` → `ext_led` kwarg; setter mode goes), A.U5.03 + A.U10.38 (`fram_target FRAMManager
  log`), A.U10.38/A.U10.37 (names in the comments)
- **Site**: `src/asy_wifi_service.py:100-108`
- **Change**: `:100-102` → "# This service's one optional live cross-instance dependency (Parts C.14 and L.4): the status
  LED it" / "# drives, resolved from [device.wiring].led_target to an already-constructed NeopixelDriver and passed" /
  "# as ext_led at construction (the NeoPixel is built first)."; `:103` → `# @wiring led_target NeopixelDriver ext_led
  optional kwarg`; `:105-107` → "# Its other optional dependency: the FRAM error-log target, resolved from
  [device.wiring].fram_target" / "# implicitly because WifiService is mandatory infra, exactly as asy_system_service.py's
  own tag is." / "# __init__ passes the log config to super().__init__() and to this service's CaptiveDNS."; `:108` → `#
  @wiring fram_target FRAMManager log optional kwarg`.
- **Resolved**: —
- **Unit**: U10 (staged: U5 `ext_led`/`log` targets; U10 class names)
- **Depends**: —
- **Blast carried by**: `buildgen/graph.py`/`wiring.py` setter-mode removal, codegen `ext_led=` → A.U5.07 (GEN); SPEC
  C.14.2/L.6.4 → A.U5.07/A.U5.03 (docs)
- **Kind**: code

### M.SRC_NET.077 Named timing and CYW43 constants; the code block
- **From**: A.U8.10 (names, tags), A.U31.15 (milliseconds), A.U18.30 (LED pattern names, deactivated pair), A.U18.40
  (`_WIFI_REFRESH_S`), A.U18.27 (`_STAT_JOINED_NO_IP`, `_PM_NO_POWERSAVE`), A.U2.04 + A.U2.14 + A.U18.24 + A.U10.20 +
  A.U6.29 (codes), A.U10.39 (names in comments)
- **Site**: `src/asy_wifi_service.py:110-129` and a new code block after the imports
- **Change**: `_STA_DISCONNECT_WAIT_ITERS = const(20)` with comment "# 20 × 500 ms = 10 s max wait for isconnected() to
  clear -" (second line unchanged); new, each with its `# @tunable wifi.<id> = <v>` tag: `_STA_DISCONNECT_POLL_MS =
  const(500)` (`wifi.sta_disconnect_poll_ms`), `_STA_CONNECT_POLL_MS = const(500)` (`wifi.sta_connect_poll_ms`),
  `_STA_CONNECT_POLL_ITERS = const(10)` (`wifi.sta_connect_poll_iters`), `_HOTSPOT_STATIONS_SETTLE_MS = const(100)`
  (`wifi.hotspot_stations_settle_ms`), `_WLAN_DOWN_SETTLE_S = const(2)` (`wifi.wlan_down_settle_s`),
  `_WLAN_DEINIT_SETTLE_S = const(1)`, `_WLAN_MODE_SETTLE_S = const(1)`, `_STA_RETRY_AFTER_LOSS_S = const(60)`,
  `_RECONNECT_CALLER_GRACE_S = const(5)`, `_RECONNECT_SETTLE_S = const(3)`, `_LED_HOTSPOT_ON_MS = const(2900)`,
  `_LED_HOTSPOT_OFF_MS = const(100)`, `_LED_DEACTIVATED_ON_MS = const(100)`, `_LED_DEACTIVATED_OFF_MS = const(2900)`
  (basis "the hotspot pattern inverted (agent, 2026-09-30)"), `_WIFI_REFRESH_S = const(5)` (`wifi.refresh_s = 5`); the
  field-count constants' comments name `_VAL_COUNTRY + _VAL_HOSTNAME + _VAL_HOTSPOT_PW` / `_VAL_SSID + _VAL_PW +
  _VAL_COUNTRY + _VAL_HOSTNAME`; phase constants unchanged; `:128-129` → `_STAT_JOINED_NO_IP = const(2)  # cyw43
  CYW43_LINK_NOIP (cyw43.h:100): joined, no IP yet; network exports no name for it (extmod/modnetwork.c:197-202,
  v1.29.0)`; new `_PM_NO_POWERSAVE = const(0xA11140)` with "# CYW43_PM_VALUE(NO_POWERSAVE, 200, 1, 1, 10): power save
  off, PM_PERFORMANCE's listen fields" / "# (network_cyw43.c:43-51); legacy's word.". Code block: `_ERR_TIMER =
  const(17)`, `_ERR_BAD_ARG = const(21)`, `_ERR_TIMEOUT = const(22)`, `_ERR_UNEXPECTED = const(23)`,
  `_ERR_WLAN_MODE_SWITCH = const(60)`, `_ERR_WLAN_AP_START = const(61)`, `_ERR_WLAN_STA_START = const(62)`,
  `_ERR_WLAN_STA_POLL = const(63)`, `_ERR_WLAN_STA_DISCONNECT = const(64)`, `_ERR_WLAN_OFF = const(65)`,
  `_WRN_STORED_DEFAULT = const(10)`, `_WRN_WLAN_AUTH_FAILED = const(36)`, `_WRN_WLAN_NO_AP = const(37)`,
  `_WRN_WLAN_CONNECT_FAILED = const(38)`, `_WRN_WLAN_STATUS_UNKNOWN = const(39)`.
- **Resolved**: (1) A.U8.10's `_LED_FLASH_ON_S`/`_OFF_S` (2.9/0.1) → A.U18.30's `_LED_HOTSPOT_*` → A.U31.15's `_MS`: each
  later action names the earlier as its Depends; the last stands, Part N rows renamed once. (2) `wifi_refresh_sec`: A.U8.10
  tags it at A.U5.09's `WifiConfig` constant, A.U5.09 groups it, A.U31.15 turns the loop sleep into
  `sleep_ms(self._refresh_ms)` from an attribute, A.U10.43 renames it `wifi_refresh_s`; A.U18.40 (ruling V.U18.D, OR36.a
  (1)) removes the parameter and sleeps a module constant. With a `const(5)` int, `asyncio.sleep(_WIFI_REFRESH_S)`
  meets G10/R23 ("or an int number of seconds") and A.U31.19's check (a module name bound to `const(<int>)`), so
  A.U31.15's `_refresh_ms` attribute has no reason left and is not added; A.U10.43's rename is superseded (the name
  goes). (3) A.U8.10 sets `wifi.sta_disconnect_poll_s`/`wifi.sta_connect_poll_s` and `wifi.hotspot_stations_settle_s`;
  A.U31.15 renames them `_ms` (the later action).
- **Unit**: U31 (A.U31.15 latest; staged: U2 codes, U8 names/tags in seconds, U18 new LED pair/refresh constant/CYW43
  names/timer and unexpected codes, U31 milliseconds)
- **Depends**: A.U8.02 (grammar), A.U2.01 (+ U18 register fix 9: WIFI uses shared 17)
- **Blast carried by**: Part N rows (renames and new rows) → A.U8.10/A.U18.30/A.U31.15 (docs); tests' comments quoting
  values and the `_FastAsyncSleep` `sleep_ms` patch → A.U8.10/A.U31.15 (tests); mirrored phase/status constants in
  `tests/test_asy_wifi_service.py`, `tests/network.py:5` → A.U18.27 (tests); `pm=0xA11140` literals in tests/twin →
  A.U18.27 (tests/TWIN); SPEC F "CYW43 values this code names" list → A.U18.27 (docs); twin `_CONNECT_DELAY_S` Dependant
  row → A.U8.10 (TWIN/docs); catalog rows for WIFI (17 owner note, 36 text) → A.U2.01 + U18 register fix 9 (catalog)
- **Kind**: code

### M.SRC_NET.078 WifiService constructor: one config object, construction-time LED, private state
- **From**: A.U10.38 (`AsyConnTime` → `WifiService`), A.U5.02 (`log`), A.U5.09 + A.U18.40 ruling (`WifiConfig`
  members), A.U5.07 (`ext_led` at construction), A.U10.35 (private attributes), A.U10.03 (`_wifi_uptime` on
  `TickSeconds`, `_wifi_connected`), A.U18.33 (`_dhcp_dns`), A.U18.28 (`_ap_selected`), A.U18.24 (`_tick_armed`),
  A.U3.02 (`_episode_wrns` goes), A.U0.35 (D05 comment), A.U10.17 (lock reason), A.U10.39 (push key via `name_cfg()`),
  A.U8.12 (`module.max_error` tag on the `:140` default), A.U6.25 (G6/R39 doc clause: the `:168-169` comment)
- **Site**: `src/asy_wifi_service.py:132-189`
- **Change**: new module-level `WifiConfig = namedtuple("WifiConfig", ("hostname", "hotspot_password",
  "conn_fail_to_hotspot", "hotspot_time_min"))` (no default constants: all four are required `[device]` fields,
  `buildgen/validate.py:63`). `class WifiService(SensorReaderConfig):` / `def __init__(self, wifi: WifiConfig, ext_led:
  "LEDControl | None" = None, max_module_error: int = 5, cfg_path: str = "", log: LogConfig = DEFAULT_LOG) -> None:`
  (the `max_module_error` comment `:140-142` kept, and the parameter's line carries `# @tunable module.max_error = 5`,
  A.U8.12's standalone-default site of that ID); `super().__init__(WIFI(None, None, None, None, None, None, None,
  None), _NAME, _VAL_SSID + _VAL_PW + _VAL_COUNTRY + _with_default(_VAL_HOSTNAME, wifi.hostname) + _VAL_LED_WIFI_ON +
  _with_default(_VAL_HOTSPOT_PW, wifi.hotspot_password), max_module_error=max_module_error, cfg_path=cfg_path,
  log=log)`. Attributes: `self._wlan = network.WLAN(network.STA_IF)`; `self._ext_led = ext_led`; `self._led:
  LEDControl | None = None`; `self._hotspot_time = 60000 * wifi.hotspot_time_min  # convert to ms`;
  `self._conn_fail_to_hotspot = wifi.conn_fail_to_hotspot` (gap pass G2: both private, no reader outside the class,
  G10/R07, M_SRC_CORE GAP-G12; every use follows); `self._wifi_uptime = TickSeconds()`; `self._wifi_connected
  = False`; `self._dhcp_dns: str | None = None`; `self._ap_selected = False`; the comment `:168-169` → "# CaptiveDNS gets
  its own independent "DNSSRV"-named logger, not this class's own self.pr (owner, 2026-08-07) -" / "# its history is
  shown with the networking data (owner, 2026-09-26)."; `self._dns_server = CaptiveDNS(log=log)`;
  `self._dns_server_task: asyncio.Task[None] | None = None`; `self._reconn_wifi = False`;
  `self._time_counter_trigger_event = asyncio.ThreadSafeFlag()`; `self.wifi_mode_lock = asyncio.Lock()  # serialises
  every use of the CYW43 radio`; `self._counter_timer = Timer()`, `self._hotspot_timer = Timer()`,
  `self._hotspot_timer_running = False`, `self._hotspot_timeout_trigger_event = asyncio.ThreadSafeFlag()`,
  `self._ledflash: asyncio.Task[None] | None = None`; `self._conn_phase` with its comment; `self._connection_failures = 0`;
  `self._hotspot_started_once = False`; `self._hw_op_failed = False` with its comment; `self._tick_armed: bool | None =
  None`; `self._push_callbacks[name_cfg(_VAL_LED_WIFI_ON)] = self._push_wifi_led` with its comment (`LEDWifiOn`).
  `led_pin`, `self.led_pin`, `wifi_refresh_sec`, `hostname`/`hotspot_password` parameters and their "every test wants"
  comment are gone.
- **Resolved**: A.U5.09 (`WifiConfig` with `wifi_refresh_sec`, `led_pin=None` kept) vs A.U18.40 — ruling V.U18.D (OR36.a
  (1) decides the members): `WifiConfig(hostname, hotspot_password, conn_fail_to_hotspot, hotspot_time_min)`, no
  `led_pin`, no refresh plumbing (A.U5.04's `_DEFAULT_WIFI_REFRESH_SEC` read goes). A.U18.42 keeps "the raw
  `WLAN.isconnected()` reachable through `conn.wlan`", while A.U10.35 makes it `_wlan` — the end state has `_wlan` (a
  tool reaches `conn._wlan`); no product reader changes.
- **Unit**: U18 (staged: U5 signature/`log`/`ext_led`; U10 class name, private names, `TickSeconds`; U18 the rest)
- **Depends**: M.SRC_NET.075, M.SRC_NET.006 (`CaptiveDNS(log)`), A.U10.02
- **Blast carried by**: generated `conn = WifiService(WifiConfig(…), ext_led=<neopixel>, max_module_error=…, cfg_path=…,
  log=…)` → A.U5.03/A.U5.07/A.U5.09 as ruled (GEN); tests (`make_client()` helpers, 14 `wifi_refresh_sec=0` calls, direct
  constructions, `tests/test_neopixel_wifi_integration.py`, `tests/test_setter_microdot_integration.py:64`,
  `tests/test_ntp_*`, private-attribute readers) →
  A.U18.40, A.U5.09, A.U10.35 (tests/HW); the led_pin tests of A.U24.45 (2) are void (see Ledger); `tests_hardware/device_scripts/wifi_service_reconnect_repro.py:41`
  gets no edit — the file is deleted in U26 (M.HW_DEV.112; M_HW_DEV GAP-D9, gap pass G2); `tests_hardware/README.md`
  `wifi_refresh_sec` mention → A.U18.40 (docs); SPEC C.2/G.2 constructor text → A.U5.09 as ruled (docs)
- **Kind**: code

### M.SRC_NET.079 `setup()` sets up both loggers in the boot batch
- **From**: A.U10.10 (new override; the lazy calls `:815-818` go), A.U36.544 (the `:818` pointer's replacement text),
  A.U10.21 (`-> bool`), A.U10.22 (readiness inherited)
- **Site**: `src/asy_wifi_service.py` new `setup()`; `:815-818` in `wlan_connect()`
- **Change**: `async def setup(self) -> bool:` / `ok = await super().setup()` / `await self._dns_server.pr.setup()  # the
  DNS server's own logger is set up separately` / `return ok` (A.U10.21's one contract; `initialized` comes from
  `SensorReader.setup()` through `super()`, M.SRC_CORE.039 — gap pass G2, M_SRC_NET gap 3: HEAD's draft returned `None`,
  which overrides a `bool` `setup()` incompatibly). The two lazy `setup()` calls and their comments leave the connect loop.
- **Resolved**: A.U36.544 rewrites the `:818` comment ("see SPECIFICATION.md Part C.7 for the real bug this fixed" →
  "(the DNS server's logger is set up separately)"); A.U10.10 moves the call — the rewritten text goes with the call.
- **Unit**: U10 (A.U36.544's text lands with it; U36 finds nothing left at `:818`)
- **Depends**: A.U10.10's `SensorReaderConfig.setup()`
- **Blast carried by**: the generated boot batch already calls `conn.setup()` (A.U10.10, GEN); tests pinning lazy setup
  (`tests/test_asy_wifi_service.py:2060-2095`) → A.U10.10 (tests)
- **Kind**: code

### M.SRC_NET.080 `_now()` goes; the GET overlay shows the value in use
- **From**: A.U10.06 (`_now()` → `utc_now()`), A.U14.26 (1) (dropped, register fix 10), A.U18.37 (`_value_in_use()`,
  `_mask_pw()` → `_cfg_overlay()`), A.U10.39 (keys via `name_cfg()`), A.U11.S01 (`CfgValue`)
- **Site**: `src/asy_wifi_service.py:191-201`
- **Change**: `_now()` deleted (its one caller uses `utc_now()`, M.SRC_NET.091). New `def _value_in_use(self, field:
  "FieldSchema", value: str) -> str: return value if _radio_value_ok(field, value) else str(field[2])`. `_mask_pw()` →
  `async def _cfg_overlay(self) -> "dict[str, CfgValue]":` with the comment "# GET shows what the radio uses: passwords
  masked, and a stored value the radio would refuse as the default it runs" / "# on (SPECIFICATION.md C.7.4)."; body:
  `overlay = {name_cfg(_VAL_PW): "********", name_cfg(_VAL_HOTSPOT_PW): "********"}`; `schema = _VAL_SSID +
  _VAL_COUNTRY + _VAL_HOSTNAME`; `values = await self.cfgmgr.get_str_values(schema)`; when not `None`, for each field
  whose `_value_in_use(live_field, value)` differs from the stored value, `overlay[field[0]] = <value in use>` (live field
  from `schema_dict(self._cfg_schema)`); no log on a GET; `return overlay`. The mask stays the display value (OR104.a
  (1): kept for page parity, never read back).
- **Resolved**: A.U14.26 (1)'s `except MemoryError` for `_now()` vs A.U10.06 — U18 register fix 10 settles for A.U10.06.
- **Unit**: U18 (U10 stage: `_now()` removal)
- **Depends**: M.SRC_NET.075, A.U10.39 (`_cfg_schema`)
- **Blast carried by**: tests (masks hold; stored over-bound values read back as the default; the `_now()` overflow tests
  `tests/test_asy_wifi_service.py:2545-2580` retire with the method) → A.U18.37, A.U10.06 (tests); SPEC C.7.4 sentence
  → A.U18.37 (docs)
- **Kind**: code

### M.SRC_NET.081 Locked status read and the stations query use `async with`
- **From**: A.U10.18 (`async with`; `_release_wifi_lock()` goes), A.U18.43 (1) (settle comment, suppression reason),
  A.U28.30 (4) (removal trigger), A.SDEP.15 (W11, conditional), A.U18.44 (return type), A.U31.15 (`sleep_ms`), A.U8.10
  (constant), A.U1.01 (legacy path in the comment)
- **Site**: `src/asy_wifi_service.py:225-246` `_locked_wlan_status()`, `_get_hotspot_stations()`
- **Change**: `_locked_wlan_status()`: `async with self.wifi_mode_lock: return self._wlan_status_or_none()`.
  `_get_hotspot_stations(self) -> "list[tuple[bytes]]"`: `async with self.wifi_mode_lock:` then the comment "# Legacy's
  settle before the stations query (legacy/firmware/python/CommonDrivers/async_connect.py:258); cyw43 055d642 states no
  such need." / "# Removal: a hardware round showing the count stays right without it (BACKLOG real-hardware list)." and
  `await asyncio.sleep_ms(_HOTSPOT_STATIONS_SETTLE_MS)`; `try: stations = self._wlan.status("stations");
  self.pr.all(...)`; the `except Exception` observation arm unchanged; `else:` preceded by "# The 1.29 stub types
  status(str) as int; "stations" returns a list of 1-tuples (network_cyw43.c:371-388)." / "# Remove the ignore when the
  stub types it (warn_unused_ignores then flags it)." and `return stations  # type: ignore[return-value]`. If
  A.SDEP.15 (U0) finds the refreshed stub already types `status("stations")`, the ignore and those two lines are not
  written (W11). Version stamps follow the pin current at execution (A.SDEP.08).
- **Resolved**: A.U18.43 (1) and A.U28.30 (4) both edit the `:244` suppression reason (A.U28.30: "A-C merges") — merged
  above (reason on the line above the suppression, the form A.U28.30's check accepts).
- **Unit**: U31 (the `sleep_ms` form; staged: U10 `async with`, U18 comments, U28 the trigger line)
- **Depends**: M.SRC_NET.077
- **Blast carried by**: BACKLOG real-hardware row "stations query without the 100 ms settle" → A.U18.43 (docs); tests
  (`tests/test_asy_wifi_service.py:1833-1848` stations tests unchanged) → A.U18.43
- **Kind**: code

### M.SRC_NET.082 Mode switch: bool result, selected-interface record, named settles
- **From**: A.U18.R01 (1) (bool), A.U18.28 (`_ap_selected`), A.U10.18 (`async with`), A.U10.03 (`restart(0)`), A.U8.10
  (settle constants), A.U2.14 (60), A.U10.35 (`_wlan`, `_hw_op_failed`)
- **Site**: `src/asy_wifi_service.py:271-293` `_select_wifi_mode()`, `_switch_wlan_mode()`
- **Change**: `async def _select_wifi_mode(self, mode: int) -> bool: async with self.wifi_mode_lock: return await
  self._switch_wlan_mode(mode)`. `async def _switch_wlan_mode(self, mode: int) -> bool:` — first statement
  `self._ap_selected = False`; `try:` disconnect, `active(False)`, print, `await asyncio.sleep(_WLAN_DOWN_SETTLE_S)`,
  `deinit()`, print, `await asyncio.sleep(_WLAN_DEINIT_SETTLE_S)`, `self._wifi_uptime.restart(0)`, `self._wlan =
  network.WLAN(mode)`, `self._ap_selected = mode == network.AP_IF`, print, `await asyncio.sleep(_WLAN_MODE_SETTLE_S)`;
  `except Exception as e:` → `self._hw_op_failed = True`, `await self.pr.err_s("Error switching WLAN mode:", e,
  errno=_ERR_WLAN_MODE_SWITCH)`, `return False`; after the `try`, `return True`.
- **Resolved**: —
- **Unit**: U18
- **Depends**: M.SRC_NET.077, M.SRC_NET.078
- **Blast carried by**: callers `_start_hotspot()`, `_leave_hotspot_mode()` ignore the bool (M.SRC_NET.086/085);
  `_recover_device()` returns it (M.SRC_NET.102); tests (mode-switch tests hold; `_ap_selected` cases) → A.U18.28,
  A.U18.R01 (tests); `A.U30.03`'s run-phase allowance for `_switch_wlan_mode`/`_wlan` re-derived against the renamed
  class → A.U30.03 (tests)
- **Kind**: code

### M.SRC_NET.083 Task-restart state reset states the hotspot behaviour
- **From**: A.U18.29 (comment), A.U10.35 (names), A.U1.01 (legacy path)
- **Site**: `src/asy_wifi_service.py:295-316` `_reset_wlan_connect_state()`
- **Change**: private names throughout (`_ledflash`, `_dns_server_task`, `_connection_failures`,
  `_hotspot_started_once`, `_hotspot_timer`, `_hotspot_timer_running`, `_reconn_wifi`, `_wlan`); the `:305-306`
  comment → "# DEACTIVATED survives a restart (A.4); HOTSPOT is kept only so reconn_wifi below leaves it through
  _leave_hotspot_mode()," / "# after which STA starts a fresh streak with hotspot_started_once cleared, as legacy's
  restart did (legacy/firmware/python/CommonDrivers/async_connect.py:176-181)." Behaviour unchanged.
- **Resolved**: —
- **Unit**: U18
- **Depends**: M.SRC_NET.078
- **Blast carried by**: SPEC A.4 `:271-273` → A.U18.29 (docs); the end-to-end restart test → A.U18.29 (tests)
- **Kind**: code

### M.SRC_NET.084 Missing LED configuration deactivates with the LED on its default
- **From**: A.U18.30 (LED default so the pattern shows), A.U3.05 (wrnno 1 → console), A.U10.39 (name)
- **Site**: `src/asy_wifi_service.py:318-325` `_apply_initial_led_config()`; `:219-223` `_read_wifi_led_cfg()`
- **Change**: `_read_wifi_led_cfg()` reads `_VAL_LED_WIFI_ON`; `_apply_initial_led_config()`: `led_cfg is None` →
  `await self.set_wifi_led(status=_VAL_LED_WIFI_ON[0][2])` (the schema default, `True`), `self._conn_phase =
  _PHASE_DEACTIVATED`, `self.pr.err("Missing WLAN configuration!")` (console, no number); else unchanged.
- **Resolved**: —
- **Unit**: U18
- **Depends**: M.SRC_NET.072
- **Blast carried by**: tests (`…missing_config_persists_wrnno_1_and_deactivates` → one `CFGMGR_WIFI` entry, none in
  WIFI's own log, `client._led is not None`) → A.U3.05, A.U18.30 (tests); the deactivated pattern starts in the loop
  (M.SRC_NET.100)
- **Kind**: code

### M.SRC_NET.085 Leaving the hotspot and waiting for an STA disconnect
- **From**: A.U10.18 (`async with`), A.U2.14 (22, 64), A.U8.10 + A.U31.15 (`_STA_DISCONNECT_POLL_MS`), A.U10.35 (names)
- **Site**: `src/asy_wifi_service.py:327-351` `_leave_hotspot_mode()`, `_disconnect_sta_and_wait()`; `:558-566`
  `_wait_for_sta_disconnect()`
- **Change**: `_leave_hotspot_mode()`: private names, `await self._select_wifi_mode(network.STA_IF)` (bool ignored).
  `_disconnect_sta_and_wait()`: `await asyncio.sleep_ms(_STA_DISCONNECT_POLL_MS)`; timeout → `errno=_ERR_TIMEOUT`;
  raise → `errno=_ERR_WLAN_STA_DISCONNECT`; `self._hw_op_failed`. `_wait_for_sta_disconnect()`: `async with
  self.wifi_mode_lock: await self._disconnect_sta_and_wait()`, then the LED off and the event line.
- **Resolved**: —
- **Unit**: U31 (staged: U2, U10, U18 names; U31 `sleep_ms`)
- **Depends**: M.SRC_NET.077, M.SRC_NET.082
- **Blast carried by**: tests (codes 22/64; `:1564` comment naming the constants) → A.U2.14, A.U8.10 (tests)
- **Kind**: code

### M.SRC_NET.086 Hotspot bring-up split; the running AP is never reconfigured
- **From**: A.U18.28 (split, comment), A.U10.18 (`async with`), A.U3.05 (wrnno 2 → console), A.U2.14 (61), A.U18.27
  (`_PM_NO_POWERSAVE`), A.U10.39 (names), A.U10.38 (`CaptiveDNS.run()` in the comment), A.U10.35 (names)
- **Site**: `src/asy_wifi_service.py:353-394` `_start_hotspot()`, `_activate_hotspot_ap()`, `_configure_hotspot_ap()`
- **Change**: `_start_hotspot()`: `await self._select_wifi_mode(network.AP_IF)`, `await self._bring_up_hotspot_ap()`,
  `self._hotspot_started_once = True`. New `_bring_up_hotspot_ap()`: `async with self.wifi_mode_lock:` LED config and
  `get_str_values(_VAL_COUNTRY + _VAL_HOSTNAME + _VAL_HOTSPOT_PW)`; missing → `self.pr.err("Missing WLAN
  configuration!")` and `await self.set_wifi_led(status=False)`; else `set_wifi_led(status=led_cfg)`, `_radio_values(…)`,
  `await self._activate_hotspot_ap(country, hostname, password)`. `_activate_hotspot_ap()`: `errno=_ERR_WLAN_AP_START`.
  `_configure_hotspot_ap()`: comment `:378-380` → "# Configures only an inactive AP: re-applying essid/password to a
  running one can drop its beacon (cyw43)." / "# Reached on a hotspot phase's first tick and when the selected AP reports
  no link (_run_hotspot_mode())."; `self._wlan.config(pm=_PM_NO_POWERSAVE)` (trailing comment goes); the DNS-task guard
  comment names `CaptiveDNS.run()`; `self._dns_server_task = evtloop.create_task(self._dns_server.run(own_ip,
  own_netmask))`.
- **Resolved**: —
- **Unit**: U18
- **Depends**: M.SRC_NET.077, M.SRC_NET.082, M.SRC_NET.096 (`_radio_values()`)
- **Blast carried by**: tests (the twice-leak test's header reworded; the DNS-task guard holds for
  `_bring_up_hotspot_ap()`; `…re_activates_without_a_mode_switch…` sibling) → A.U18.28 (tests); twin AP reports
  `STAT_GOT_IP` and `192.168.4.1`, so L2 reaches the stations path and the captive DNS subnet check sees a real AP subnet
  → A.U25.72 (TWIN); SPEC F.2 `:3635-3636`, A.4 phase table → A.U18.28 (docs)
- **Kind**: code

### M.SRC_NET.087 Hotspot client paths persist a timer failure; the watcher loop is renamed
- **From**: A.U18.31 (`_hotspot_client_connected()` sets the LED itself), A.U18.24 (2) (hotspot-timer failure
  persisted, errno 17), A.U18.30 (flash call), A.U31.15 (ms constants), A.U10.44 (`_watch_hotspot_timeout()` →
  `_hotspot_timeout_loop()`), A.U10.45 (except order), A.U10.35 (names), A.U18.40 (`wifi_refresh_sec` gone from the
  comment)
- **Site**: `src/asy_wifi_service.py:396-430`
- **Change**: `_hotspot_client_connected()`: deinit and flag as today; `if self._ledflash is not None:
  self._ledflash.cancel(); self._ledflash = None`; then `self._led_on()` unconditionally; the event line.
  `_hotspot_client_absent()`: the timer arm as today (comment `:410-412` kept) with `except (MemoryError, OSError) as e:`
  and the trailing comment "# alarm-pool exhaustion (ENOMEM) -" / "# _hotspot_timer_running stays False so the next
  refresh cycle retries arming it." and `await self.pr.err_s("Could not start hotspot timer:", e, errno=_ERR_TIMER)`;
  then `if self._ledflash is None: self._ledflash = evtloop.create_task(self._flash_led(_LED_HOTSPOT_ON_MS,
  _LED_HOTSPOT_OFF_MS))`. `async def _hotspot_timeout_loop(self) -> None:` (was `_watch_hotspot_timeout()`), body with
  private names.
- **Resolved**: —
- **Unit**: U31 (staged: U10 name, U18 behaviour, U31 constants)
- **Depends**: M.SRC_NET.077, M.SRC_NET.092
- **Blast carried by**: tests (`:1363-1378` gain one errno-17 entry; flash-cancel test inverted) → A.U18.24, A.U18.31
  (tests)
- **Kind**: code

### M.SRC_NET.088 STA connect path: console config line, named codes, retry wait outside the lock
- **From**: A.U3.05 (wrnno 3 → console), A.U2.14 (62, 65), A.U18.27 (`_PM_NO_POWERSAVE`), A.U3.02 (episode reset
  goes), A.U18.32 (1) (retry wait unlocked), A.U10.18 (`async with`), A.U8.10 (`_STA_RETRY_AFTER_LOSS_S`,
  `_WLAN_DOWN_SETTLE_S`), A.U10.39 (names), A.U10.35 (names)
- **Site**: `src/asy_wifi_service.py:432-501` (`_attempt_sta_connect()` … `_deactivate_wlan_permanently()`),
  `:583-590` `_run_sta_mode()`, `:632-636` `_handle_sta_connection_result()`
- **Change**: `_attempt_sta_connect()`: reads `_VAL_SSID + _VAL_PW + _VAL_COUNTRY + _VAL_HOSTNAME`; missing →
  `self.pr.err("Missing WLAN configuration!")` and return; `_connection_failures` on an empty SSID. `_trigger_sta_connect()`:
  `pm=_PM_NO_POWERSAVE`, `errno=_ERR_WLAN_STA_START`. `_on_sta_connected()`: the `_episode_wrns = 0` line goes.
  `_on_sta_disconnected(self) -> bool`: event line; `retry_due = self._conn_phase == _PHASE_STA_ESTABLISHED`; if due the
  "retrying in 1 minute" event line, else `await self._register_sta_connection_failure()`; `self._led_off()`; the status
  print; `return retry_due`. `_handle_sta_connection_result(self) -> bool`: connected → `self._on_sta_connected()`,
  `return False`; else `return await self._on_sta_disconnected()`. `_run_sta_mode()`: `async with self.wifi_mode_lock:`
  the attempt and `retry_due = await self._handle_sta_connection_result()`; after the block, `if retry_due: await
  asyncio.sleep(_STA_RETRY_AFTER_LOSS_S)`. `_deactivate_wlan_permanently()`: `await asyncio.sleep(_WLAN_DOWN_SETTLE_S)`,
  `errno=_ERR_WLAN_OFF`.
- **Resolved**: —
- **Unit**: U18
- **Depends**: M.SRC_NET.077, M.SRC_NET.096
- **Blast carried by**: tests (retry test asserts the lock is released during the wait; getters return real values
  during it; codes) → A.U18.32, A.U2.14 (tests); SPEC C.8 priority-inversion sentence goes, lock-hold table → A.U18.32,
  A.U18.34 (docs)
- **Kind**: code

### M.SRC_NET.089 Connect-status poll: stops at `STAT_GOT_IP`, direct warnings, BADAUTH wording
- **From**: A.U18.32 (2) (return at `STAT_GOT_IP`), A.U18.27 (`_STAT_JOINED_NO_IP`), A.U18.36 (message and comment),
  A.U2.14 (63, 36-39), A.U3.02 (`_episode_wrn()` goes), A.U8.10 + A.U31.15 (`_STA_CONNECT_POLL_ITERS`,
  `_STA_CONNECT_POLL_MS`)
- **Site**: `src/asy_wifi_service.py:592-630` `_poll_sta_connect_status()`, `_episode_wrn()`
- **Change**: `for _i in range(_STA_CONNECT_POLL_ITERS):`; status raise → `errno=_ERR_WLAN_STA_POLL`;
  `elif status == _STAT_JOINED_NO_IP: self.pr.all("WLAN obtaining IP")`; `STAT_WRONG_PASSWORD` → comment "# cyw43 reports
  any failed AUTH event or key exchange as BADAUTH (cyw43_ctrl.c:383-395, 415-427): not proof of a wrong password." and
  `await self.pr.wrn_s("WLAN authentication or handshake failed", wrnno=_WRN_WLAN_AUTH_FAILED)`; `NO_AP_FOUND` →
  `wrnno=_WRN_WLAN_NO_AP`; `CONNECT_FAIL` → `wrnno=_WRN_WLAN_CONNECT_FAILED`; `STAT_GOT_IP` → `self.pr.all("WLAN connection
  successful")` then `return`; else `wrnno=_WRN_WLAN_STATUS_UNKNOWN`; each warning branch returns as today; `await
  asyncio.sleep_ms(_STA_CONNECT_POLL_MS)`. `_episode_wrn()` deleted.
- **Resolved**: —
- **Unit**: U31 (staged: U3 direct calls, U8 names, U18 behaviour/texts, U31 ms)
- **Depends**: M.SRC_NET.077
- **Blast carried by**: tests (one status call on success; renamed authentication test; episode tests rewritten to the
  central rule; the printed state line tests) → A.U18.32, A.U18.36, A.U3.02, A.U24.32 (tests); catalog 36 text → A.U2.01
  + U18 register fix 9 (catalog); twin/bench wrong-password assertions read the number → A.U18.36 (HW)
- **Kind**: code

### M.SRC_NET.091 One networking snapshot per second
- **From**: A.U18.33 (snapshot fields, `_dhcp_dns`, rssi only in STA), A.U10.06 (`utc_now()`), A.U10.35 (`_wlan`)
- **Site**: `src/asy_wifi_service.py:503-512` `_update_wifi_snapshot()`
- **Change**: `mode = "AP" if self._conn_phase == _PHASE_HOTSPOT else "STA"`; in `_PHASE_DEACTIVATED` no radio call:
  publish `WIFI("STA", connected, None, None, None, None, None, utc_now())` and `self._dhcp_dns = None`; otherwise
  `ifconfig()` once (print-only on failure, as today) giving IP/Subnet/Gateway/DNS when it has four fields; `rssi = None`,
  and only when `not self._ap_selected and connected`: `try: rssi = int(self._wlan.status("rssi"))` with the HEAD
  comment's substance ("outside STA mode it raises ValueError") and a print-only `except`; `self._dhcp_dns = dns if
  connected else None` with no await between the read and the publish; `await self._set_meas_data(WIFI(mode, connected,
  ip, subnet, gateway, dns, rssi, utc_now()))`.
- **Resolved**: A.U18.33's "in `_PHASE_DEACTIVATED` … all fields `None`, Mode 'STA'" — `Connected` keeps the value the
  caller passes (`False`, HEAD `:849`), `TS` the timestamp primitive's value; the address fields and `RSSI` are `None`
  (reading of "all fields", keeping HEAD's published `Connected: false`).
- **Unit**: U18
- **Depends**: M.SRC_NET.074, M.SRC_NET.082
- **Blast carried by**: generated `_networking_status()` reads one `conn.get_data()` → A.U18.33 (GEN); per-device
  `/status` tests with the lock held → A.U18.33 (tests); twin `status("rssi")` raises outside STA → A.U18.33/U25 (TWIN);
  SPEC A.8/C.8 → A.U18.33 (docs)
- **Kind**: code

### M.SRC_NET.092 Push narrowing stated; lock helper goes; one flash task for both patterns
- **From**: A.U18.41 (comment), A.U10.18 (`_release_wifi_lock()` goes), A.U18.30 (`_flash_led(on, off)`), A.U18.31
  (cancel arm goes), A.U10.20 (task top; its cancel clause dropped by the V.U18.31/V.U18.D ruling), A.U31.15 (ms)
- **Site**: `src/asy_wifi_service.py:514-536` `_push_wifi_led()`, `_release_wifi_lock()`, `_flash_led_off()`
- **Change**: `_push_wifi_led()` comment `:515-516` → "# Narrows the config-value union to bool for set_wifi_led(); the
  schema already guarantees a bool, so the False arm is unreachable - kept for the type."; body unchanged (value type
  `CfgValue`, A.U11.S01). `_release_wifi_lock()` deleted. `_flash_led_off()` → `async def _flash_led(self, on_ms: int,
  off_ms: int) -> None:` — `while True:` `self._led_on()`, `await asyncio.sleep_ms(on_ms)`, `self._led_off()`, `await
  asyncio.sleep_ms(off_ms)`; wrapped once in `try:` … `except Exception as e: await self.pr.err_s("LED flash task
  failed:", e, errno=_ERR_UNEXPECTED)` (the unsupervised task's top, G5/R16); no `CancelledError` arm: a cancel ends the
  task at its sleep, touching no LED.
- **Resolved**: A.U10.20 keeps the `CancelledError` arm and says "the LED left on, as on cancel"; A.U18.31 removes it —
  ruling V.U18.31/V.U18.D (G6/R54, RF204) for A.U18.31; A.U10.20's `except Exception` top stays. Soundness (agent,
  OR111.a (2)): A.U10.20's L1 WiFi test ("an LED whose `on()` raises ends the flash task with one 23 entry") cannot pass
  as written, because `_led_on()`/`_led_off()` absorb every exception of the LED object (`:248-262`, print-only); the top
  is still reachable (a `MemoryError` in those helpers' own logging), so it stays under G5/R16 and its test drives it
  through a double (a replaced `_led_on` raising), as G5/R54 allows — gap for the tests cluster (below).
- **Unit**: U31 (staged: U10 top and lock helper removal, U18 signature/cancel semantics, U31 `sleep_ms`)
- **Depends**: M.SRC_NET.077
- **Blast carried by**: the four cancellers (M.SRC_NET.083, .087, .093, .098); tests (flash cancel inverted, pattern
  durations 100/2900, the flash top test via a double) → A.U18.30, A.U18.31, A.U10.20 as corrected (tests); SPEC E.5.1
  narrowing entry → A.U18.41/A.U35.41 (docs); SPEC C.8 cancellation line → A.U18.31 (docs)
- **Kind**: code

### M.SRC_NET.093 Reconnect trigger, hotspot tick and stations management
- **From**: A.U18.28 (`_run_hotspot_mode()`), A.U8.10 (`_RECONNECT_CALLER_GRACE_S`, `_RECONNECT_SETTLE_S`), A.U10.35
  (names)
- **Site**: `src/asy_wifi_service.py:538-581` `_handle_reconnect_trigger()`, `_run_hotspot_mode()`,
  `_manage_hotspot_stations()`
- **Change**: `_handle_reconnect_trigger()`: private names; `await asyncio.sleep(_RECONNECT_CALLER_GRACE_S)` (comment
  kept) and `await asyncio.sleep(_RECONNECT_SETTLE_S)`. `_run_hotspot_mode()`: `status = await
  self._locked_wlan_status()`; `if status == network.STAT_GOT_IP: await self._manage_hotspot_stations()` / `elif not
  self._ap_selected: await self._start_hotspot()` / `else: await self._bring_up_hotspot_ap(); await
  self._hotspot_client_absent()`. `_manage_hotspot_stations()` unchanged.
- **Resolved**: —
- **Unit**: U18
- **Depends**: M.SRC_NET.086, M.SRC_NET.087
- **Blast carried by**: tests (the new sibling case) → A.U18.28 (tests)
- **Kind**: code

### M.SRC_NET.094 Starters and starter lists follow one naming scheme
- **From**: A.U10.44 (names), A.U10.03 (tick starter), A.U18.24 (1) (`_tick_armed`), A.U18.44 (`TaskStarter`),
  A.U10.46
- **Site**: `src/asy_wifi_service.py:648-678`
- **Change**: `start_asy_connect()` over `_connect_loop()`, `start_asy_uptime()` over `_uptime_loop()`,
  `start_asy_hotspot_timeout()` over `_hotspot_timeout_loop()`; `start_uptime_timer()` (was `start_counter_timer()`):
  `self._tick_armed = arm_tick_timer(self._counter_timer, self._time_counter_trigger_event, self.pr, "WiFi uptime")`
  with the one-line comment "# a failed arm is retried by _connect_loop(), which persists a second failure";
  `stop_uptime_timer()` (was `stop_counter_timer()`); `get_task_starters(self) -> "list[TaskStarter]"` returning the
  three renamed starters; `get_timer_starters()` returning `[self.start_uptime_timer]`.
- **Resolved**: —
- **Unit**: U18 (U10 names and `arm_tick_timer()`)
- **Depends**: A.U10.03
- **Blast carried by**: tests and device scripts calling starters/coroutines by name → A.U10.44 (tests/HW); SPEC C.9
  tick-timer sentence → A.U10.03 (docs)
- **Kind**: code

### M.SRC_NET.096 PUT refusal and use path share one radio check
- **From**: A.U6.29 (message, `_radio_value_ok()`), A.U2.14 (21, 10), A.U19.16 (`INVALID`), A.U3.02 (direct `wrn_s`),
  A.U18.37 (`_value_in_use()`), A.U28.28 (B905 inline `noqa` goes), A.U10.39 (`_cfg_schema`), A.U11.S01 (`CfgValue`)
- **Site**: `src/asy_wifi_service.py:690-716` `_set_mgr_cfg()`, `_radio_values()`
- **Change**: `_set_mgr_cfg(self, data: "JsonMapping", cfg_vals: "ConfigSchema") -> "tuple[bool,
  WriteValidity]"` (the base's raw-body parameter, M.SRC_CORE.038; gap pass G2, U19 A-C note 2): comment "# Refuses a radio value outside its byte bound or shape before it is stored (C.7.4); the
  rest of the" / "# request goes through ConfigManager as usual."; `refused` built with `_radio_value_ok()`; each `await
  self.pr.err_s("Refusing", key, "- outside the radio's accepted form", errno=_ERR_BAD_ARG)`; `results[key] = INVALID`.
  `_radio_values()`: `fields = schema_dict(self._cfg_schema)`; `for field, value in zip(schema, values):` (no inline
  `noqa`: B905 is exempted centrally for MicroPython-run code, A.U28.27/A.U28.28); `live = fields.get(field[0], field)`;
  `used = self._value_in_use(live, value)`; `if used != value: await self.pr.wrn_s("Stored", field[0], "is outside the
  radio's accepted form, using its default", wrnno=_WRN_STORED_DEFAULT)`; `safe.append(used)`; comment `:705-706` kept.
- **Resolved**: —
- **Unit**: U28 (A.U28.28's noqa removal is the latest; staged: U2 codes, U3 direct call, U6 check/message, U10 name,
  U18 helper, U19 `INVALID`)
- **Depends**: M.SRC_NET.075, M.SRC_NET.080, A.U28.27 (the central B905 entry exists before the inline noqa goes)
- **Blast carried by**: tests (refusal text, byte-bound tests, corpus cases, B905 removal keeps ruff clean) → A.U6.29,
  A.U28.28 (tests/tooling); SPEC C.7.4 → A.U6.29 (docs)
- **Kind**: code

### M.SRC_NET.097 Config getter, error sources and loggers
- **From**: A.U18.37 (`callback=self._cfg_overlay`), A.U10.39/A.U10.40 (names), A.U18.44 + A.U11.S02
  (`list[ErrorSource]`), A.U10.35 (`_dns_server`)
- **Site**: `src/asy_wifi_service.py:718-733`
- **Change**: `get_dict_cfg()` → `self._get_dict_cfg(self.name, _VAL_SSID + _VAL_PW + _VAL_COUNTRY + _VAL_HOSTNAME +
  _VAL_LED_WIFI_ON + _VAL_HOTSPOT_PW, callback=self._cfg_overlay)`; `get_error_sources(self) -> "list[ErrorSource]":`
  comment names `self._dns_server`, `return super().get_error_sources() + [self._dns_server]`; `get_loggers()` →
  `super().get_loggers() + [self._dns_server.pr]`; `get_error_counter()` unchanged.
- **Resolved**: —
- **Unit**: U18
- **Depends**: M.SRC_NET.080
- **Blast carried by**: generated `_collect_error_sources()` → A.U10.46 (GEN); `test_captive_dns.py:283`-style equality
  tests hold → A.U11.S02 (tests)
- **Kind**: code

### M.SRC_NET.098 Getters read held state; the lock-requiring read says so; LED setter simplified
- **From**: A.U18.33 (comment; `get_wlan_ifconfig()`/`get_wlan_rssi()` go; `get_dns_server_ip()` from the snapshot),
  A.U18.42 (`wlan_isconnected()` goes), A.U10.18 (`network_available()` → `network_available_locked()`), A.U10.03
  (`get_wifi_uptime()`), A.U5.07 (`set_ext_led()` goes), A.U18.40 (`set_wifi_led()`), A.U0.35 (`:793` tag), A.U10.35
  (names)
- **Site**: `src/asy_wifi_service.py:735-812`
- **Change**: comment `:735-737` → "# Every public getter reads state this service holds (the 1 Hz snapshot, the phase);
  none touches the radio. The one" / "# radio read callers may make, network_available_locked(), requires wifi_mode_lock
  (SPECIFICATION.md C.8)."; `get_wlan_ifconfig()` and `get_wlan_rssi()` deleted; `get_dns_server_ip()` → `return
  self._dhcp_dns` with the comment "# The DHCP-assigned DNS server to try first, from the last snapshot."; `get_wifi_mode_lock()`
  unchanged; `async def get_wifi_uptime(self) -> int: return self._wifi_uptime.read() if self._wifi_connected else 0`;
  `wlan_isconnected()` deleted; `def network_available_locked(self) -> bool:  # caller must already hold wifi_mode_lock`
  with HEAD's body; `is_hotspot_active()` comment → "# A plain self._conn_phase compare touches no hardware, unlike
  network_available_locked()'s radio read -" / "# no lock needed, the callable-from-anywhere getter shape.";
  `set_ext_led()` deleted; `set_wifi_led()`: comment "# Uniform setter return contract (owner, 2026-09-26): always True
  here - pure attribute" / "# assignment plus _led_off()'s own already-defensive degrade-on-raise, nothing to reject.";
  `if status: if self._led is None: self._led = self._ext_led  # if None, the LED stays off` / `else: self._led_off();
  self._led = None`; `return True`. `reconnect_wifi()` unchanged apart from private names.
- **Resolved**: —
- **Unit**: U18 (U5 `set_ext_led()` removal; U10 names, `get_wifi_uptime()`)
- **Depends**: M.SRC_NET.091
- **Blast carried by**: generated `ntp = NTPClient(…, conn.network_available_locked, conn.get_dns_server_ip, …)` →
  A.U10.18 (GEN); generated `_networking_status()` stops calling the two removed getters → A.U18.33 (GEN); tests
  (`get_wlan_ifconfig` tests go, `get_dns_server_ip` inverts to "last snapshot while locked", rssi tests become snapshot
  tests, `wlan_isconnected` tests go, `…selects_the_ext_led`) → A.U18.33, A.U18.42, A.U18.40 (tests); SPEC C.8 "Known
  inconsistency" → the one contract → A.U18.33/A.U10.18 (docs)
- **Kind**: code

### M.SRC_NET.100 `_connect_loop()`: timer re-arm, deactivated pattern, console give-up, constant refresh
- **From**: A.U10.44 (`wlan_connect()` → `_connect_loop()`), A.U10.10 (lazy setups go), A.U18.24 (1) (tick re-arm),
  A.U18.30 (deactivated pattern), A.U3.07 (give-up → console), A.U18.40 (`_WIFI_REFRESH_S`), A.U10.R01 (the streak it
  zeroes; the ladder in `_error_check()`), A.U10.35 (names)
- **Site**: `src/asy_wifi_service.py:814-841` `wlan_connect()`
- **Change**: `async def _connect_loop(self) -> None:` — `self._err_cnt_internal = 0` (comment kept), `_reset_wlan_connect_state()`,
  `await self._apply_initial_led_config()`; loop: `if self._conn_phase == _PHASE_DEACTIVATED:` the `all()` line, then
  "# Deactivated: a distinct pattern (owner, 2026-09-29), a short blink every 3 s (agent, 2026-09-30)." and `if
  self._ledflash is None: self._ledflash = asyncio.get_event_loop().create_task(self._flash_led(_LED_DEACTIVATED_ON_MS,
  _LED_DEACTIVATED_OFF_MS))`; else `self._hw_op_failed = False`; `if self._tick_armed is False: self._tick_armed =
  arm_tick_timer(self._counter_timer, self._time_counter_trigger_event, self.pr, "WiFi uptime")` and, still `False`,
  `await self.pr.err_s("WiFi uptime timer not armed", errno=_ERR_TIMER)` and `self._hw_op_failed = True`; reconnect
  trigger, hotspot/STA branch as today; the streak comment's "matching a Reader's read_loop() returning False" →
  "_read_loop()"; give-up → `self.pr.err("Giving up after repeated WLAN hardware failures, restarting task.")` (console:
  `_error_check()`'s errno 2 is the persisted entry) and `return`; after the branch `await
  asyncio.sleep(_WIFI_REFRESH_S)`.
- **Resolved**: —
- **Unit**: U18 (staged: U3 console give-up, U10 name/setup removal)
- **Depends**: M.SRC_NET.077, M.SRC_NET.079, M.SRC_NET.092, M.SRC_NET.102, A.U10.R01
- **Blast carried by**: tests (tick re-arm cases, `max_module_error` failed re-arms end the loop, deactivated pattern,
  give-up expects errno 2 once, streak tests re-derived for the recovery rung) → A.U18.24, A.U18.30, A.U3.07, A.U18.R01
  (tests); `_RUN_PHASE_ALLOWED` gains `WifiService._connect_loop`/`_ledflash` "the deactivated-state LED pattern" →
  A.U30.03 (tests, its "earlier units' new sites join" clause); SPEC C.9 / A.4 → A.U18.24, A.U18.30 (docs)
- **Kind**: code

### M.SRC_NET.101 `_uptime_loop()` counts measured link time under the lock
- **From**: A.U10.44 (`time_counter()` → `_uptime_loop()`), A.U10.03 (`TickSeconds`, `_wifi_connected`), A.U10.18
  (`async with`), A.U18.35 (comment), A.U18.33 (the snapshot it publishes)
- **Site**: `src/asy_wifi_service.py:843-860` `time_counter()`
- **Change**: `async def _uptime_loop(self) -> None:` — `self._wifi_uptime.restart(0)`, `self._wifi_connected = False`;
  loop: `await self._time_counter_trigger_event.wait()`; deactivated → `restart(0)`, `self._wifi_connected = False`,
  `await self._update_wifi_snapshot(connected=False)`, `continue`; `async with self.wifi_mode_lock:` comment "# Link up,
  hotspot included: an active AP reports STAT_GOT_IP too (owner, 2026-09-29)." / `connected =
  self._wlan_status_or_none() == network.STAT_GOT_IP` / `self._wifi_connected = connected` / `if not connected:
  self._wifi_uptime.restart(0)` / `await self._update_wifi_snapshot(connected=connected)`. `get_data()`'s comment
  `:682-683` names `_uptime_loop()`.
- **Resolved**: —
- **Unit**: U18 (U10 stage: name, `TickSeconds`, `async with`)
- **Depends**: M.SRC_NET.091, A.U10.02
- **Blast carried by**: status catalog descriptions and DEVICE_REFERENCE "link up, hotspot included" → A.U18.35
  (GEN/docs); tests (driven ticks; `get_wifi_uptime()`) → A.U10.03 (tests); lock-hold tests → A.U18.34 (tests)
- **Kind**: code

### M.SRC_NET.102 The radio re-initialisation is WiFi's participant rung
- **From**: A.U18.R01 (2)
- **Site**: `src/asy_wifi_service.py`, new `_recover_device()` override
- **Change**: `async def _recover_device(self) -> bool | None:` with the comment (≤ 3 lines) "# Participant rung
  (SPECIFICATION.md C.7/F.2): re-select the current mode; deinit() powers the CYW43 off" / "# and the next active(True)
  reloads its firmware (cyw43_ctrl.c:118-175, cyw43-driver 055d642). None while deactivated: no radio in use."; `if
  self._conn_phase == _PHASE_DEACTIVATED: return None`; `return await self._select_wifi_mode(network.AP_IF if
  self._conn_phase == _PHASE_HOTSPOT else network.STA_IF)`.
- **Resolved**: A.U18.R01 notes that in hotspot phase "the AP's own mode select repeats the re-initialisation once";
  with A.U18.28 merged (`_ap_selected` set by the re-select, M.SRC_NET.082/093), the next hotspot tick takes the
  `_bring_up_hotspot_ap()` branch instead, so no second re-initialisation happens — the bound improves, nothing else
  changes. A.U18.R01's "re-checks these line numbers against its applied changes" is done here.
- **Unit**: U18
- **Depends**: A.U10.R01 (the hook and ladder), M.SRC_NET.082
- **Blast carried by**: tests (two failed iterations → one `deinit()` and one `WLAN(STA_IF)` construction, one wrnno
  14; hotspot re-selects AP; deactivated no call; a raising `deinit()` → one errno 60 only; episode re-arm) → A.U18.R01
  (tests); L2 twin WLAN counts constructions per interface → A.U18.R01/U25 (TWIN); L3 device-script step →
  A.U18.R01 (HW); SPEC A.4 WiFi bullet, F.2 → A.U18.R01/A.U14.R01 (docs); lock-hold table gains this holder → A.U18.34
  (docs)
- **Kind**: code

### M.SRC_NET.103 Member order per D.15 (WiFi service)
- **From**: A.U10.33
- **Site**: `src/asy_wifi_service.py` class `WifiService` and the module-level helpers
- **Change**: pure reorder by D.15's key (A.U10.32), AST-verified; methods added after U10 (`_bring_up_hotspot_ap()`,
  `_value_in_use()`, `_cfg_overlay()`, `_recover_device()`, `_country_ok()`) are placed by the same key when written.
- **Resolved**: —
- **Unit**: U10 (last U10 edit)
- **Depends**: every U10 edit of the file
- **Blast carried by**: —
- **Kind**: code

### M.SRC_NET.104 Every broad handler records a C-stack overflow (WiFi)
- **From**: A.U30.19 (2)
- **Site**: `src/asy_wifi_service.py` HEAD `:208, 215, 239, 254, 261, 268, 291, 312, 349, 373, 454, 499, 510, 597, 645,
  743, 761` (seventeen `except Exception as e:`), plus the LED-flash task's top handler M.SRC_NET.092 adds
- **Change**: every broad handler present in the file's end state starts with `report_if_fatal(e)`, above its logging or
  fallback line (the observation-tier `_wlan_status_or_none()`-style arms included: a swallowed stack overflow there is
  still a design defect, A.U30.19 (1)); where M.SRC_NET.078-.102 merge or split a handler, the resulting handler carries
  it once. `from asy_print_log import report_if_fatal` joins the runtime imports (M.SRC_NET.071; GAP-G8, gap pass G2).
- **Resolved**: —
- **Unit**: U30
- **Depends**: A.U30.19, M.SRC_NET.071, M.SRC_NET.078-.102 (the handlers as they end up)
- **Blast carried by**: `tests_scripts/test_fatal_report_sites.py` → A.U30.19 (tests); A.U30.03's run-phase allow-list is
  unaffected (the call allocates nothing)
- **Kind**: code

## src/asy_webserver_service.py

Every `ext/microdot.py:<line>` and `extmod/…` cite below is v2.6.2's / v1.29.0's; B0's dependency refresh (A.SDEP.06,
A.SDEP.08, OR129.a (5)) may move either, and each cite is re-checked against the refreshed pin before the change that
carries it is executed (AC_NOTES item 34 (second)). `ext/` itself is never edited (only `ext/typings/microdot/` is
added, unmodified upstream stubs, A.U8.23).

### M.SRC_NET.110 Imports: renamed modules, typed Microdot, the new primitives
- **From**: A.U10.37 (`asy_api_response`, `asy_base_classes`, `asy_config_manager`, `asy_print_log`), A.U8.23 (vendored
  stub; the import's ignore and the `:7-9` comment), A.U20.14 (2) (same ignore), A.U10.27 (`import math`), A.U19.07
  (`import errno`), A.U19.16 (`VALID`, `INVALID`, `FAILED`), A.U5.02 (`DEFAULT_LOG`, `LogConfig`), A.U19.17/A.U11.S02/
  A.U10.46 (aliases; `Any` goes), A.U10.38 (FRAM-manager import goes with `fram`)
- **Site**: `src/asy_webserver_service.py:4-31`
- **Change**: `import asyncio`, `import errno`, `import json`, `import math`; the comment `:7-9` → "# Typed via the
  vendored upstream stub (ext/typings/microdot/); firmware freezes ext/ and src/ flat together."; `from microdot import
  Request, Response, abort, redirect, send_file` (no `type: ignore`); `const`; `import asy_api_response as ar`; `from
  asy_base_classes import LockedCounter`; `from asy_config_manager import FAILED, INVALID, VALID, checked_float,
  checked_int`; `from asy_print_log import DEFAULT_LOG, LogConfig, make_logger, report_if_fatal`. `TYPE_CHECKING`: `Awaitable, Callable, Iterable,
  Sequence` (no `Coroutine` unless a remaining annotation needs it), `Protocol, TypeVar`; `import asy_config_manager as
  cm`; `from asy_api_response import ResponseEnvelope, _RequestLike`; `from asy_base_classes import AsyncCallback, ErrorSource,
  JsonDict, JsonMapping, JsonValue, TaskStarter` (the aliases' one home, M.SRC_CORE.030, per A.U11.S02); `from asy_print_log import
  ErrorLog, PrintLogHistory`; no `Any`, no FRAM-manager import.
- **Resolved**: A.U8.23 and A.U20.14 (2) both remove the `microdot` import's ignore — one removal (A.U20.14 defers to
  A.U8.23). Gap pass G2: the per-kind validators replace `type_or_range_error` (M_SRC_CORE GAP-G13, M.SRC_NET.122);
  `report_if_fatal` is imported from its home `asy_print_log` (M.SRC_CORE.034; GAP-G8 — no import line carried it);
  `JsonMapping` from where M.SRC_CORE.030 declares it, not re-exported through `asy_api_response`.
- **Unit**: U19 (A.U19.16/A.U19.17 latest; staged: U8 stub/ignore, U10 names/`math`, U5 log imports)
- **Depends**: A.U8.23 (the stub on `mypy_path`), A.U10.46, A.U11.S02, A.U19.16
- **Blast carried by**: `pyproject.toml` `mypy_path`, the override comment → A.U8.23 (tooling); CLAUDE.md vendoring rule
  gains the stub sentence → A.U8.23 (docs); `tests_scripts/test_mypy_any_baseline.py` drops this module → A.U19.17/A.U8.24
  (tests)
- **Kind**: code

### M.SRC_NET.111 The `TYPE_CHECKING` protocols and callback aliases
- **From**: A.U19.17 (aliases, `_ModuleLike.pr` goes, `RouteHandler -> object`), A.U8.23 (`_MicrodotApp` comment),
  A.U10.38 (`CaptiveDNS` in the `_ModuleLike` comment), A.U11.31 (`reset_error_counter() -> bool`), A.U19.02
  (`NotificationLedFct`), A.U19.07 (the reader half's `read()`), A.U10.31 (quotes only on `TYPE_CHECKING` names)
- **Site**: `src/asy_webserver_service.py:32-86`
- **Change**: `_ModuleLike`: comment names "every SensorReaderConfig subclass, NeopixelDriver, CaptiveDNS and
  ConfigManager"; `name: str`; the `pr` member goes; `get_dict_data()`/`get_dict_cfg() -> "JsonDict"`;
  `_set_dict_cfg(self, data: "JsonMapping", cfg_vals: "cm.ConfigSchema") -> "dict[str, str]"`;
  `get_error_counter() -> "ErrorLog"`; `reset_error_counter() -> bool`. `_ClosableStream` unchanged. `_StreamLike` gains
  `async def read(self, n: int) -> bytes: ...` (A.U19.07's reader proxy fills from it). `RouteHandler =
  Callable[..., object]` with its comment. `_MicrodotApp` comment → "# The subset of the Microdot instance routes are
  registered onto; the vendored stub (ext/typings/microdot/) leaves get/put/route unannotated (v2.6.2)." (≤ 3 lines);
  members unchanged. Aliases: `StatusSourceFct = MaintenanceFct = Callable[[], Awaitable[JsonDict]]`, `SystemCmdFct =
  Callable[[str], Awaitable[bool]]`, `NotificationLedFct = Callable[[int, int, int, float], Awaitable[bool]]`,
  `NotificationPauseFct = Callable[[int], Awaitable[bool]]`, `HotspotActiveFct = Callable[[], bool]` (each on its own
  line; `StatusSourceFct`/`MaintenanceFct` may be one alias, A.U10.46's "one named alias each" rule: one alias,
  `StatusSourceFct`, used for both).
- **Resolved**: U19 A-C note 2 — `_set_dict_cfg()`'s `data` is typed `dict[str, CfgValue]` in `asy_base_classes.py` while
  every route passes the raw JSON body; A.U19.17 types the Protocol `JsonMapping`, which "needs the implementers … to
  accept it — merge with A.U11.S02". The implementers are another cluster's (SRC_CORE); the merged end state here is the
  Protocol as A.U19.17 writes it, and the implementer's parameter type is a gap for that cluster (below) — carried in the
  gap pass G2 by M.SRC_CORE.017/.038/.040/.044 and the overrides M.SRC_NET.045/.096, M.SRC_SENS.053.
- **Unit**: U19
- **Depends**: A.U10.46, A.U11.S02, A.U19.02
- **Blast carried by**: implementers' `_set_dict_cfg(data: JsonMapping)` → gap (SRC_CORE cluster, A.U11.S01/A.U11.S02);
  test fakes typed against the Protocols hold → A.U19.17 (tests)
- **Kind**: code

### M.SRC_NET.112 Module constants: commands, dispatch schemas, defaults, limits, routes, codes
- **From**: A.U5.03 + A.U10.38 (`@wiring fram_target FRAMManager log`), A.U10.29 + A.S0930.09 (`_SYSTEM_CMDS`), A.U19.02
  (`_LIGHT_CMD_FIELDS`), A.U10.40 (`LightCmdLED` members `R/G/B/T`), A.U5.04 + A.U5.05 + A.U8.04 (`_DEFAULT_*` and tags),
  A.U19.11 (the `:107` comment unit), A.U19.15 + A.U0.29 (`_ERROR_STATUSES`, comment), A.U10.29 (`const()`), A.U19.07
  (`_MAX_HEADER_LINES`, `_MAX_HEAD_BYTES`), A.U19.09 (`_START_RETRIES`, `_START_RETRY_S`), A.U19.20 (`ROUTES`), A.U2.04 +
  A.U2.19 + A.U19.08/A.U19.09 + U19 A-C note 3 (code block), A.U19.02/A.U19.03 (the shared dispatch comment)
- **Site**: `src/asy_webserver_service.py:88-119`
- **Change**: `_NAME = const("WEBSERVER")`; `:90-93` comment names "wifi/ntp" unchanged and the tag → `# @wiring
  fram_target FRAMManager log optional kwarg`. `_SYSTEM_CMDS = const(("reboot", "bootloader", "mempause",
  "resetconfig", "erasefram"))` with the comment "# The only values ever forwarded to system_cmd(), matched as whole
  strings: the exact action word is what" / "# runs a command, so no alias, prefix or case variant does (owner,
  2026-09-30). mempause's fixed 300 s lives in" / "# the callback (Part A.8)." `_PAUSE_TIME_MAX` and its comment
  unchanged (`LockedCounter(max_val=…)` wording follows A.U9.09's notification rewrite if that site changes);
  `_PAUSE_TIME_FIELD: "cm.FieldSchema" = ("PauseTime", "int", 0, 0, _PAUSE_TIME_MAX, None)` and new `_LIGHT_CMD_FIELDS:
  "tuple[cm.FieldSchema, ...]" = (("R", "int", None, 0, 255, None), ("G", "int", None, 0, 255, None), ("B", "int", None,
  0, 255, None), ("T", "float", None, 0.5, 60.0, None))`, both preceded by one shared comment "# Dispatch-only fields
  validate through the per-kind validators against synthetic schemas, as schema-backed fields do" / "#
  (SPECIFICATION.md A.8); LightCmdLED's are legacy's own led_cmd() bounds, never schema-backed." (gap pass G2: the
  validators of M.SRC_CORE.047) (the `:103-105` block
  goes into it). `_MAX_PENDING_FRAGMENTS = const(16)  # @tunable web.max_pending_fragments = 16` with "_PieceWriter's
  list never outgrows 16 slots". Defaults (A.U5.04/A.U5.05) each tagged (A.U8.04): `_DEFAULT_MAX_CONTENT_LENGTH =
  const(2048)` (`web.max_content_length = 2048`; the "1.56x … (I.6)" reason moves here), `_DEFAULT_CHUNK_BYTES =
  const(256)` (`web.chunk_bytes = 256`; its `:108-110` comment kept), `_DEFAULT_MAX_CONNECTIONS = const(6)` (its
  `:315-317` reason), `_DEFAULT_PER_CALL_TIMEOUT_S = const(5.0)` (`web.per_call_timeout_s = 5.0`),
  `_DEFAULT_OUTER_CAP_S = const(15.0)` (`web.outer_cap_s = 15.0`), `_DEFAULT_STATIC_INDEX = const("index.html")`.
  `_ERROR_STATUSES = const((400, 404, 405, 413, 500))  # the five shaped statuses SPECIFICATION.md A.5 names; each is its
  own envelope code (C.5.3)`. `_MAX_HEADER_LINES = const(32)` (`web.max_header_lines = 32`), `_MAX_HEAD_BYTES =
  const(2048)` (`web.max_head_bytes = 2048`), `_START_RETRIES = const(3)` (`web.start_retries = 3`), `_START_RETRY_S =
  const(5)` (`web.start_retry_s = 5`, "derived from the 10 s close linger"). `ROUTES = (("GET", "/measurements",
  "_get_measurements"), ("GET", "/sensors", "_get_sensors"), ("PUT", "/sensors", "_put_sensors"), ("GET", "/networking",
  "_get_networking"), ("PUT", "/networking", "_put_networking"), ("GET", "/system", "_get_system"), ("PUT", "/system",
  "_put_system"), ("GET", "/status", "_get_status"), ("PUT", "/status", "_put_status"), ("GET", "/notification",
  "_get_notification"), ("PUT", "/notification", "_put_notification"))` with one comment line "# The one route table:
  registered in this order; buildgen reads it for the REST reference (SPECIFICATION.md A.8)." Code block:
  `_ERR_CALLBACK = const(14)`, `_ERR_UNEXPECTED = const(23)`, `_WRN_HTTP_PEER_RESET = const(48)`,
  `_WRN_HTTP_CALL_TIMEOUT = const(49)`, `_WRN_HTTP_REQUEST_CAP = const(50)`, `_WRN_HTTP_SOCKET_ERROR = const(51)`,
  `_WRN_HTTP_CLOSE_RAISED = const(52)`, `_WRN_HTTP_WAIT_CLOSED = const(53)`, `_WRN_HTTP_REFUSED = const(60)`,
  `_WRN_HTTP_BAD_HEAD = const(61)`, `_WRN_HTTP_START_FAILED = const(62)`.
- **Resolved**: (1) A.U10.29 wraps `_ERROR_SHAPES` in `const()`; A.U19.15 replaces it with `_ERROR_STATUSES` — the new
  tuple is wrapped instead. (2) A.U8.04 tags the `__init__` defaults; A.U5.05 moves them into constants ("A.U8.04's tag
  sites move … to the new constants (A-C merge)") — tags sit on the constants. (3) U19 A-C note 3: the webserver's three
  new warnings take wrnno 60-62 (checked: no other action allocates 60-62; A.U2.01 leaves 60-127 free) and W48
  `HTTP_PEER_CLOSED` is re-homed to the peer-reset trace (its old `EOFError` site goes): name `HTTP_PEER_RESET` here,
  the catalog row's name and text follow (gap for the catalog cluster). (4) `_LIGHT_CMD_FIELDS` members: A.U19.02 writes
  `r/g/b/t`, A.U10.40 (U10, earlier) renames the members `R/G/B/T` and its site list gains this constant (U19 A-C note
  5) — the upper-case names stand.
- **Unit**: U19 (staged: U5 constants and `log` tag, U8 tags, U10 `const()`/names, U19 the rest; A.S0930.09's two words
  land with SUPP_owner_0930's unit order — the latest of U19 and that supplement's placement)
- **Depends**: A.U5.04, A.U8.02, A.U2.01 (+ U19 A-C note 3)
- **Blast carried by**: `tests_scripts/test_request_timeout_ceiling.py`/`test_request_body_cap_headroom.py` read the
  `_DEFAULT_*` constants → A.U5.05 (tests); `js/poll-manager.js:8` tag → A.U8.04 (WEB); the `SystemCmd` dropdown and mock
  `SYSTEM_CMDS` derived from `_SYSTEM_CMDS` → A.S0930.10/A.U23.27 (GEN/WEB); `_PERSISTING_COMMAND_WORDS` read by `ast` →
  A.S0930.19 (tests); the REST reference and every route-set reader (15 sites) → A.U19.20/A.U26.80/A.U24.36 (GEN/tests/HW);
  catalog rows 48 (renamed/re-homed), 60-62 → A.U2.01 via U19 A-C note 3 (catalog); Part N rows → A.U8.04/A.U19.07/
  A.U19.09 (docs)
- **Kind**: code

### M.SRC_NET.113 Registration helpers state their owner-tagged reasons
- **From**: A.U0.29 (`:123-124`), A.U19.17 (types)
- **Site**: `src/asy_webserver_service.py:122-132` `_index_by_name()`, `_index_pairs()`
- **Change**: `_index_by_name(items: "Iterable[_ModuleLike]") -> "dict[str, _ModuleLike]"` with the comment "#
  Last-registration-wins, by construction (owner, 2026-08-12; SPEC A.8): the" / "# simplest per-item loop already
  behaves this way; no dedup/guard code on top (agent, 2026-08-12)."; `_index_pairs(items:
  "Iterable[tuple[str, StatusSourceFct]]") -> "dict[str, StatusSourceFct]"`.
- **Resolved**: —
- **Unit**: U19 (A.U0.29's text in U0)
- **Depends**: M.SRC_NET.111
- **Blast carried by**: A.U0.08 allow-list loses the "decision N" entries → A.U0.29 (tests)
- **Kind**: code

### M.SRC_NET.114 `_PieceWriter` groups bytes and writes a non-finite float as `null`
- **From**: A.U19.11 (bytes), A.U10.27 (`null` for NaN/±inf), A.U19.17 (types)
- **Site**: `src/asy_webserver_service.py:135-178`
- **Change**: `__init__(self, pieces: "list[bytes]", max_bytes: int)`; `self._group: list[bytes]`; `add(self, fragment:
  str) -> None`: `data = fragment.encode()`; `if self._group and self._size + len(data) > self._max_bytes: self.flush()`;
  append `data`, `self._size += len(data)`; the 16-slot collapse joins with `b"".join(self._group)`; `flush()` appends
  `b"".join(self._group)`; comment `:136-137` → "# Concatenates adjacent JSON text fragments into pieces of at most
  max_bytes bytes, never splitting" / "# one - so the largest allocation is bounded by the largest fragment, not by the
  response." `add_value(self, value: object) -> None`: dict/list/tuple branches unchanged; scalar branch: `if
  isinstance(value, float) and not math.isfinite(value): self.add("null")` `else: self.add(json.dumps(value))` with one
  comment line "# json.dumps() writes bare nan/inf, which JSON rejects: a non-finite float is written as null (Part G)."
- **Resolved**: —
- **Unit**: U19 (U10 stage: the `null` branch)
- **Depends**: —
- **Blast carried by**: every GET route (M.SRC_NET.115, .123); tests (`_written()` → bytes, byte-equality tests,
  `[len(p)…]` lists, the `"é"` case, the NaN case, per-device non-finite scenario) → A.U19.11, A.U10.27 (tests); SPEC
  I.3/G.2 "bytes" and the non-finite rule → A.U19.11, A.U10.27 (docs); js mock `JSON.stringify` already writes `null`
  (A.U10.27)
- **Kind**: code

### M.SRC_NET.115 Streamed responses hand Microdot one encoded copy
- **From**: A.U19.11, A.U19.17
- **Site**: `src/asy_webserver_service.py:181-204` `_stream_dict_response()`, `_pieces_response()`
- **Change**: `_stream_dict_response(result: "JsonMapping", chunk_bytes: int) -> Response`: `pieces: list[bytes] = []`,
  body unchanged otherwise (its comment kept: the growable-GET rule, CLAUDE.md memory bullet); `_pieces_response(pieces:
  "list[bytes]") -> Response`: `Response(iter(pieces), headers={"Content-Type": "application/json; charset=UTF-8",
  "Content-Length": str(sum(len(p) for p in pieces))})`; its comment keeps its two reasons. Return annotations
  unquoted (`Response` is a runtime import).
- **Resolved**: —
- **Unit**: U19
- **Depends**: M.SRC_NET.114
- **Blast carried by**: tests draining an iterator of bytes hold → A.U19.11 (tests)
- **Kind**: code

### M.SRC_NET.116 One nested config shape; the flatten helper narrows to it
- **From**: A.U10.36, A.U19.17
- **Site**: `src/asy_webserver_service.py:207-217` `_flatten_cfg_values()`; `:439`
- **Change**: `_flatten_cfg_values()` → `def _cfg_values(values: "JsonMapping") -> "JsonDict":` returning the single
  nested entry's inner dict (`make_dict()`'s `{name: {field: value}}` shape, which every module now returns, SYSTEM
  included); the flat branch and the `digital_twin/README.md` production-bug pointer go; one comment line "# Every
  module's get_dict_cfg() returns make_dict()'s {name: {field: value}}; this takes the one inner dict." `:439` calls it.
- **Resolved**: —
- **Unit**: U19 (U10 stage: the shape; U19: the types)
- **Depends**: A.U10.36's `SystemService.get_dict_cfg()` change (SRC_CORE cluster)
- **Blast carried by**: `_FakeModule.get_dict_cfg()` → nested → A.U10.36 (tests); `digital_twin/README.md:227-229`,
  `tests/test_digital_twin_sensortask_integration.py:211` → A.U10.36 (TWIN/docs); SPEC C.6 → A.U10.36 (docs)
- **Kind**: code

### M.SRC_NET.117 `SettingsGroup` typed with the shared callback alias
- **From**: A.U19.17, A.U11.S02 (`AsyncCallback`)
- **Site**: `src/asy_webserver_service.py:220-231`
- **Change**: `post_fct: "Callable[[], None] | None" = None`, `post_asy_fct: "AsyncCallback | None" = None`; body
  unchanged.
- **Resolved**: —
- **Unit**: U19
- **Depends**: A.U11.S02
- **Blast carried by**: generated `SettingsGroup(…, post_asy_fct=ntp.ntp_force_sync)` → holds (GEN)
- **Kind**: code

### M.SRC_NET.118 `_TimeoutStreamProxy`: millisecond bound, shared flags, bounded request head, held stream
- **From**: A.U31.18 (`wait_for_ms`, `timeout_ms`), A.U2.19 (`timed_out` flag; 49 on the read path), A.U19.07 (the
  bounded head parser, `_HeadRefused`, `head_refused` flag, `chunk` size), A.U19.06 (`hold()`/`release()`), A.U14.03 +
  A.U18.43 (4) (the reset comment), A.SDEP.18 (W29/W30, conditional), A.U19.17 (types), A.U10.22 (read-only: `close()`
  is named a stream-interface mirror in its check)
- **Site**: `src/asy_webserver_service.py:234-291`
- **Change**: new private `class _HeadRefused(OSError):` (constructed as `_HeadRefused(errno.EPIPE)`), comment "# A
  refused request head: errno 32 is in Microdot's muted list (ext/microdot.py:56-61), so it answers 400 with no
  traceback." Class comment → "# Forwards every stream method ext/microdot.py calls, each bounded by timeout_ms (a plain
  asyncio.TimeoutError," / "# not an OSError subclass - Part F.1), and bounds the request head before Microdot parses
  it (SPECIFICATION.md A.5)." / "# Microdot's read-phase catch swallows a read timeout (Part A.5), so this proxy is the
  only place it is observable." `__init__(self, stream: "_StreamLike", timeout_ms: int, pr: "PrintLogHistory",
  peer_gone: "list[bool]", timed_out: "list[bool]", head_refused: "list[bool] | None" = None, chunk: int =
  _DEFAULT_CHUNK_BYTES) -> None:` — stores them; `self._head: list[bytes] | None = []` (header coalescing, unchanged);
  `self._rbuf = b""`, the head-line counters of A.U19.07 (2), `self._held: object | None = None`. `_bounded(coro)`:
  `try: return await asyncio.wait_for_ms(coro, self._timeout_ms)` `except asyncio.TimeoutError: self._timed_out[0] =
  True; raise`. `_bounded_read(coro)`: `TimeoutError` → `await self._pr.wrn_s("Connection reclaimed (per-call
  timeout):", e, wrnno=_WRN_HTTP_CALL_TIMEOUT)` then re-raise; `OSError` → comment "# A read that saw a reset leaves the
  socket in STATE_PEER_RST_HANDLED with its pcb freed (extmod/modlwip.c:507, 843-844); a" / "# later write still goes
  through that NULL pcb (:751-760, Part H.7.1), so writes stop here." / "# Re-check at every pin move; remove once
  modlwip refuses them." then `self._peer_gone[0] = True` and re-raise. `readline()` and `readexactly(n)`: A.U19.07 (1)-(3)
  as written — `readline()` fills `self._rbuf` through `self._stream.read(k)` with `k = min(limit + 1 - len(self._rbuf),
  self._chunk)`, `limit = Request.max_readline` read at call time, each read through `_bounded_read()`; returns through the
  first `\n` or the partial buffer at EOF; counts head lines and refuses (raises `_HeadRefused` outside
  `_bounded_read()`, after `self._head_refused[0] = True`) on: a line over `limit`, more than `_MAX_HEADER_LINES`
  headers, a head over `_MAX_HEAD_BYTES`, a line that does not decode as UTF-8, a request line not of three tokens, a
  header without `:`, a `Content-Length` that is empty or not all ASCII digits or repeated, any `Transfer-Encoding`;
  `readexactly(n)` takes from `self._rbuf` first, then the stream, and turns the stream's `EOFError` into the same
  refusal; one comment line per rule at its site. `awrite()`, `aclose()`, `close()`, `wait_closed()`, `get_extra_info()`
  unchanged apart from `_bounded()`. New `hold(self, closable: object) -> None` (stores one object) and `release(self) ->
  None` (sets the slot to `None` first, then calls the object's `close()` once), each with one comment line. SDEP.18,
  after B0's Microdot re-vendor: if the vendored tag writes the header block in one call, the `_head` coalescing and its
  branch in `awrite()` go (W29); if read-phase exceptions stop being swallowed, the read-timeout log moves per A.SDEP.18
  (W30) — otherwise both stay as above.
- **Resolved**: A.U14.03 and A.U18.43 (4) both rewrite the `:256-258` comment (each: "A-C merges"): A.U18.43's text
  (defect, scope, removal trigger, as G6/R55 requires) with A.U14.03's wording "goes through a NULL pcb" and its
  "Part H.7.1" pointer, three lines. A.U2.19 adds a `timed_out` list and A.U19.07 a `head_refused` list, both "shared like
  `peer_gone`": one keyword each, `head_refused` only on the reader proxy (the writer never parses a head).
- **Unit**: U31 (A.U31.18 latest; staged: U2 flag and codes, U14 comment, U18 comment, U19 parser/hold, U31 ms)
- **Depends**: M.SRC_NET.112 (constants), A.U19.08 (the trace `_serve()` makes from `head_refused`)
- **Blast carried by**: `_serve()` builds the pair (M.SRC_NET.127); `_StaticRoutes.serve()` calls `hold()`
  (M.SRC_NET.124); every reader fake gains `read(n)`, the adversarial-client matrix, the `_TimeoutStreamProxy(writer,
  1.0, …)` → `1000` test, W49 tests → A.U19.07, A.U31.18, A.U2.19 (tests); L2 raw-socket `Content-Length: -1` case →
  A.U19.07 (TWIN); L4 negative/non-numeric `Content-Length` row → A.U19.07/U26 (HW); SPEC A.5 head bullet, I.6 sentence,
  F.1 `readexactly(-1)` fact → A.U19.07 (docs); `_RequestLike.sock` member (`asy_api_response.py`) → A.U19.06 (SRC_CORE)
- **Kind**: code

### M.SRC_NET.119 `WebserverService.__init__`: three config objects, one route loop, drop counter, readiness flag
- **From**: A.U5.04 (`ServingLimits`, `StaticSite`, `RouteSources`; `__init__(app, routes, serving, static=None,
  log=DEFAULT_LOG)`), A.U5.02 (`log`), A.U5.05 (defaults from constants; the `max(chunk_bytes, 1)` clamp stays),
  A.U19.20 (route loop), A.U19.05 (static routes object), A.U19.08 (`_dropped`), A.U10.01 (`_open_conns` on the shared
  cap), A.U31.18 (ms attributes), A.U19.15 (error statuses), A.U0.29 (`:387` comment), A.U10.10/A.U10.22 (`setup()` and
  its readiness flag), A.U19.17 (types)
- **Site**: `src/asy_webserver_service.py:294-400`
- **Change**: module-level namedtuples (A.U5.04): `ServingLimits = namedtuple("ServingLimits", ("max_content_length",
  "chunk_bytes", "max_connections", "backlog", "per_call_timeout_s", "outer_cap_s", "host", "port"))`, `StaticSite =
  namedtuple("StaticSite", ("mount", "index", "is_hotspot_active"))`, `RouteSources = namedtuple("RouteSources",
  ("sensors", "settings", "build_info", "system_cmd", "notification_led", "notification_pause", "status_sources",
  "maintenance_sensors", "error_sources"))` (`from collections import namedtuple` joins the imports), each with a one-line
  comment carrying the reasons HEAD's parameter comments give (`max_content_length` I.6, `chunk_bytes` I.3 and the
  `>= 1` clamp, `max_connections`/`backlog` H.7 relationship, `build_info` L.7 verbatim sub-entry, `is_hotspot_active`
  A.5 captive fallback). `def __init__(self, app: "_MicrodotApp", routes: RouteSources, serving: ServingLimits,
  static: StaticSite | None = None, log: LogConfig = DEFAULT_LOG) -> None:` — `self.pr: PrintLogHistory =
  make_logger(log, _NAME)`; `self.initialized = False`; the `routes` fields indexed as today (`_index_by_name`,
  `_index_pairs`, `dict(… or {})`); `self._max_connections`, `self._chunk_bytes = max(serving.chunk_bytes, 1)`, the
  backlog clamp and its comment; `self._per_call_timeout_ms = round(serving.per_call_timeout_s * 1000)`,
  `self._outer_cap_ms = round(serving.outer_cap_s * 1000)`; `self._host`, `self._port`; `self._open_conns =
  LockedCounter(init_value=0)`; `self._dropped = LockedCounter(init_value=0)`; `Request.max_content_length`/`max_body_length`
  lines and their comments unchanged; routes: `for method, path, handler in ROUTES: (app.get if method == "GET" else
  app.put)(path)(getattr(self, handler))`; `after_request`/`after_error_request` with the comment "(SPECIFICATION.md Part
  A.8)" (no "decision 7"); `for status_code in _ERROR_STATUSES: app.errorhandler(status_code)(_shaped_error_handler(status_code))`;
  the catch-all comment and `app.errorhandler(Exception)(self._handle_unhandled_exception)`; `if static is not None:`
  the `:396-398` comment, `site_routes = _StaticRoutes(static, self._chunk_bytes, self.pr)`,
  `app.get("/")(site_routes.get_index)`, `app.get("/<path:filename>")(site_routes.get)`. New `async def setup(self) ->
  bool: await self.pr.setup(); self.initialized = True; return True` (A.U10.21's one contract; gap pass G2).
- **Resolved**: A.U10.22's readiness check requires `self.initialized` in every class that defines `async def setup`
  (G5/R14); A.U10.10 gives this class one and no action writes the flag — added here (the flag gates nothing else: routes
  are registered at construction and the server starts only after the boot batch, A.U10.10's order). A.U19.08 writes
  `LockedCounter(init_value=0)` "with A.U10.01's cap" — the default `max_val` is `COUNTER_CAP` after A.U10.01, so no
  argument is passed.
- **Unit**: U19 (staged: U5 objects/`log`, U10 cap/setup/flag, U31 ms attributes)
- **Depends**: M.SRC_NET.112, M.SRC_NET.124, A.U10.01
- **Blast carried by**: generated `_emit_webserver()` builds the three objects from TOML values and `src/` constants →
  A.U5.04/A.U5.05 (GEN); `_make_service()` test helper builds the objects (153 call sites unchanged) → A.U5.04 (tests);
  route-table equality test → A.U19.20 (tests); tests reading `_per_call_timeout_s`/`_outer_cap_s` → `_ms` → A.U31.18
  (tests); SPEC A.5/A.8/H.7/I.3 constructor mentions, A.7 step 14, G.2 config-object entry → A.U5.04 (docs)
- **Kind**: code

### M.SRC_NET.120 Sensor and flat settings routes answer every key
- **From**: A.U19.01 (1)-(3), (5) (unknown sensor or key → `INVALID`; `dispatch_keys`; ERR branch goes), A.U19.16
  (constants), A.U19.17 (types), A.U10.36 (`_cfg_values()`), A.U10.40 (dispatch key names), A.U36.512 (`:477` "device
  variant" → "device"), A.U19.12 (read-only: the lock is taken inside `_get_dict_cfg()`, SRC_CORE's site)
- **Site**: `src/asy_webserver_service.py:402-486, 519-520`
- **Change**: `_get_measurements()`/`_get_sensors()` unchanged in body (typed `result: dict[str, JsonValue]`, return
  `Response`); `_put_sensors()`: unknown `name` or non-dict `fields` → `results[name] = INVALID`, comment "# An unknown
  sensor, or a sensor entry that is not an object, answers "Invalid" in place of its field map." `_get_settings_flat()
  -> "JsonDict"` using `_cfg_values()`. `_apply_settings_groups(self, endpoint: str, body: "JsonMapping", dispatch_keys:
  tuple[str, ...] = ()) -> "dict[str, str]"`: the `:446-448` comment stays; per group as today but the `res == "ERR"`
  branch `:463-469` and its comment go; `results.update(await ar.handle_set_cmd(group.module, subset,
  group.module.get_cfg_schema(), group.post_fct, group.post_asy_fct))` — `handle_set_cmd()` returns the per-field
  `WriteValidity` (M.SRC_CORE.072), so no envelope is unwrapped and no `isinstance()` narrowing is written; after the loop every body key no group
  lists and not in `dispatch_keys` → `INVALID`. `_put_networking()` passes `()`, `_put_system()` `("SystemCmd",)`,
  `_put_notification()` `("LightCmdLED", "PauseTime")`. `_get_networking()` comment → "# Streamed via
  _stream_dict_response(): this scales with however many SettingsGroup entries this device's own build wires up" / "#
  (CLAUDE.md's memory-safety hard rule)."; `_get_system()`/`_get_notification()` unchanged apart from types.
- **Resolved**: U19 A-C note 1 (return `WriteValidity` from `handle_set_cmd()` instead of an envelope, to drop the
  `isinstance` narrowing). Gap pass G2 (2026-10-01): settled by the lead's L1 ruling (SUPP_coverage, 2026-09-30;
  AC_NOTES 38: "a narrowing check that can never fire is runtime code and dead code … the fix is at the type level (an
  honest return type …)") — `handle_set_cmd()` returns `WriteValidity` (M.SRC_CORE.072, the api_response site, now
  merged the same way), the endpoint's own `make_response(0, result=results)` is the one envelope (no wire change);
  the earlier "narrowing kept" agent decision is withdrawn.
- **Unit**: U19 (U10 stage: `_cfg_values()`, key names; U36 stage: the `:477` wording lands with U19's rewrite of the
  same comment)
- **Depends**: M.SRC_NET.116, A.U11.26, M.SRC_CORE.072 (the return type; its U11 stage of this caller lands in the same
  commit)
- **Blast carried by**: js mock `applySparsePut()` and unknown-sensor mirror → A.U19.01/U23 (WEB); tests (unknown
  sensor → `{"BOGUS": "Invalid"}`, unknown top-level key → "Invalid" on every settings endpoint, dispatch key never
  double-reported, per-device `PUT /networking {"NoSuchKey": 1}`) → A.U19.01 (tests); SPEC A.8 `:607-608` → A.U19.01
  (docs); no E.5.1 narrowing entry (no narrowing left; hand-off SPEC/TSC for A.U35.41's row, `GAPS_G2.md`)
- **Kind**: code

### M.SRC_NET.121 `SystemCmd`: five exact words, whole-string match, one guarded run
- **From**: A.U19.04 (loop form, `_run_system_cmd()`), A.S0930.09 (two words, comment), A.U2.19 (e2 → 14), A.U19.16
  (constants), A.U30.19 (`report_if_fatal`)
- **Site**: `src/asy_webserver_service.py:494-517` `_put_system()`, `_dispatch_system_cmd()`
- **Change**: `_put_system()`: `results = dict(await self._apply_settings_groups("system", body, ("SystemCmd",)))`; `if
  "SystemCmd" in body: results["SystemCmd"] = await self._dispatch_system_cmd(body["SystemCmd"])`. `async def
  _dispatch_system_cmd(self, cmd: object) -> str:` comment "# object: whatever JSON value the client sent; membership in
  the enum is the whole check" / "# (whole-string equality: no alias, prefix, case folding or number runs a command)."; `if
  self._system_cmd is None: return INVALID`; `for name in _SYSTEM_CMDS: if cmd == name: return await
  self._run_system_cmd(name)`; `return INVALID`. New `async def _run_system_cmd(self, name: str) -> str:` with HEAD's
  guarded `try` and its comment (≤ 3 lines): `ok = await self._system_cmd(name)` / `except Exception as e:
  report_if_fatal(e); await self.pr.err_s("system_cmd callback failed:", e, errno=_ERR_CALLBACK); return FAILED` /
  `return VALID if ok else FAILED`.
- **Resolved**: OR122.a (2) requires "the dispatch compares the whole string against `_SYSTEM_CMDS` … no alias, prefix,
  case folding or number"; A.U19.04's loop compares `cmd == name` for each of the five `str` words — equality on the whole
  value, so a non-`str` JSON value, a prefix, a case variant or a number never equals a word (settled by OR122.a (2);
  the property is pinned by A.S0930.21 (g)'s near-miss test and A.S0930.20's L0 mirror). OR126.a (3) (reboot and
  bootloader on the controlled sequence) changes only what the callback does (`SystemService`, A.S0930.31); this
  dispatcher answers the callback's bool as today.
- **Unit**: U30 (A.U30.19 latest; staged: U2 code, U19 loop/constants, the supplement's two words)
- **Depends**: M.SRC_NET.112, A.U30.19 (`report_if_fatal()` in `asy_print_log`, M.SRC_CORE.034)
- **Blast carried by**: generated `_system_cmd_callback` answers all five words → A.S0930.11 (GEN); the dropdown's two
  options → A.S0930.10 (GEN/WEB); tests (non-string values → Invalid; near misses; exact words; raise → Failed + one 14)
  → A.U19.04, A.S0930.21 (tests); SPEC A.8 `:612` and A.11 threat model rows → A.S0930.30, A.U29.01 (docs)
- **Kind**: code

### M.SRC_NET.122 Notification dispatch validates the LED command and the pause through synthetic schemas
- **From**: A.U19.02 (LED validation; callback `(r, g, b, t)`; busy → `FAILED`), A.U19.03 (pause pre-check goes), A.U10.40
  (`LightCmdLED`, members `R/G/B/T`), A.U2.19 (e3/e5 → 14), A.U19.16, A.U30.19, A.U9.09 (comment wording referenced by
  A.U19.03), M_SRC_CORE GAP-G13 (per-kind validators; gap pass G2)
- **Site**: `src/asy_webserver_service.py:522-565`
- **Change**: `_put_notification()`: `("LightCmdLED", "PauseTime")` dispatch keys; `if "LightCmdLED" in body:
  results["LightCmdLED"] = await self._dispatch_notification_led(body["LightCmdLED"])`; `PauseTime` as today.
  `_dispatch_notification_led(payload: object) -> str`: `INVALID` when the callback is `None`, `payload` is not a dict,
  a key is outside `R`/`G`/`B`/`T` or one is missing; `r`, `g`, `b` through `checked_int(value, field)` and `t` through
  `checked_float(value, field)` against `_LIGHT_CMD_FIELDS` (any `None` → `INVALID`; the returned values kept, already
  `int`/`float`); then the guarded call `ok = await
  self._notification_led(r, g, b, t)` with `except Exception as e: report_if_fatal(e); await self.pr.err_s("notification_led
  callback failed:", e, errno=_ERR_CALLBACK); return FAILED`; `return VALID if ok else FAILED` (a busy LED answers
  "Failed", owner, 2026-09-29). `_dispatch_notification_pause(payload: object) -> str`: comment "# Out of range is
  Invalid, never clamped (legacy rejected it)." (with the shared constant comment of M.SRC_NET.112); `if
  self._notification_pause is None: return INVALID`; `pause = checked_int(payload,
  _PAUSE_TIME_FIELD)`; `if pause is None: return INVALID`; the guarded call as above (`errno=_ERR_CALLBACK`,
  `report_if_fatal(e)` first).
- **Resolved**: gap pass G2 — M_SRC_CORE GAP-G13 (the lead's L1/GAP-14 ruling, AC_NOTES 38): the callbacks take `int`/
  `float` (`NotificationLedFct`, `NotificationPauseFct`, M.SRC_NET.111), so the values come from the per-kind
  validators, never from a `type()` test that cannot fire (A.U11.S01 (5)'s webserver check is not written).
- **Unit**: U30 (A.U30.19; staged: U2 codes, U10 key names, U19 validation)
- **Depends**: M.SRC_NET.112, M.SRC_CORE.047 (the validators, U11), A.U9.03 (its generated callback body is superseded
  by A.U19.02's)
- **Blast carried by**: generated `_notification_led_callback(r, g, b, t)` and the removal of `_FIELD_LED_*` → A.U19.02
  (GEN); js mock `dispatchLightCmdLed()` "Failed" → "Invalid", members → A.U19.02/A.U10.40/U23 (WEB); tests (seven
  scenarios "Failed" → "Invalid", fake callback signatures, new malformed cases, pause list/dict cases) → A.U19.02,
  A.U19.03 (tests); `src/config_manager.py:124-127` comment names this dispatcher → M.SRC_CORE.047 (its two-line comment above
  `checked_int()`; M_GEN gap 4, U19 A-C note 5); SPEC H.6/A.8 → A.U19.02 (docs)
- **Kind**: code

### M.SRC_NET.123 `/status`: guarded sources, concurrent `ResetErrors`, unknown keys answered
- **From**: A.U11.31 (`ResetErrors` per result, concurrent `gather`), A.U19.01 (4) (other keys → `INVALID`), A.U2.19
  (e6 → 14), A.U19.16 (constants), A.U19.17 (types), A.U30.19, A.U23.11 (read-only: the `{"error":"unavailable"}` shape
  the page renders)
- **Site**: `src/asy_webserver_service.py:569-639`
- **Change**: `_get_status()`/`_build_status_pieces()` unchanged in logic (pieces are `bytes` through M.SRC_NET.114; the
  `_NAME` entry and its comment kept); `_write_guarded(self, writer: "_PieceWriter", fct: "StatusSourceFct", name: str)`
  and `_write_errcount_entry(self, writer, get_log_fct: "Callable[[], Awaitable[ErrorLog]]", name: str)`: each `except
  Exception as e: report_if_fatal(e); await self.pr.err_s("Status stream source failed:", name, e,
  errno=_ERR_CALLBACK)` then `writer.add('{"error":"unavailable"}')`. `_put_status()`: `body is None` → `make_response(1)`;
  `result: dict[str, str] = {}`; `if "ResetErrors" in body:` `if body["ResetErrors"] is True:` `ok = await
  asyncio.gather(*(m.reset_error_counter() for m in self._error_sources.values()), self.reset_error_counter())`,
  `result["ResetErrors"] = VALID if all(ok) else FAILED` / `else: result["ResetErrors"] = INVALID`; every other body key →
  `result[key] = INVALID`; `return ar.make_response(0, result=result)`.
- **Resolved**: A.U11.31 writes `body.get("ResetErrors") is True → … ; any other ResetErrors value → "Invalid"`;
  A.U19.01 (4) adds "every body key other than `ResetErrors` → Invalid in the result A.U11.31 builds" — combined above.
- **Unit**: U30 (A.U30.19; staged: U2, U11 reset, U19 keys/constants)
- **Depends**: M.SRC_NET.114, M.SRC_NET.129 (`reset_error_counter() -> bool`), A.U11.31's `-> bool` at every error source
- **Blast carried by**: error sources' `reset_error_counter() -> bool` in every module (this cluster: M.SRC_NET.006,
  UART merges below; other clusters' modules → A.U11.31); js mock `ResetErrors` result and `render.js` → A.U11.31/U23
  (WEB); tests (result words, concurrency proof, `{"ResetErrors": true, "X": 1}`) → A.U11.31, A.U19.01 (tests);
  SPEC A.8 `/status` PUT line, the sequential-reset sentence → A.U11.31 (docs); BACKLOG item 24 → A.U19.14 per U19 A-C
  note 4 (docs)
- **Kind**: code

### M.SRC_NET.124 Static routes on a typed object: closed stream, revalidation, one write bound
- **From**: A.U19.05 (`_StaticRoutes`; the `assert` and `S101` go), A.U19.06 (`hold()`, `Cache-Control: no-cache`),
  A.U18.43 (5) (send_file comment), A.SDEP.18 (W43: the comment names the vendored default), A.U19.17 (types)
- **Site**: `src/asy_webserver_service.py:641-667`
- **Change**: new private `class _StaticRoutes:` — `__init__(self, site: StaticSite, chunk_bytes: int, pr:
  "PrintLogHistory")`; `async def get_index(self, request: "_RequestLike") -> Response: return self.serve(request,
  self._site.index)`; `async def get(self, request: "_RequestLike", filename: str) -> Response: return self.serve(request,
  filename)`; `def serve(self, request: "_RequestLike", filename: str) -> Response:` — HEAD's `_serve_static()` body with
  `self._site.mount`/`.index`/`.is_hotspot_active`, the `..` guard and its comment, no `assert`; right after `open()`:
  `request.sock[1].hold(stream)` with "# closed when the connection ends, a HEAD or aborted response included"; the
  `:662-663` comment pair; `response.headers["Content-Length"] = str(size)`; `response.headers["Cache-Control"] =
  "no-cache"  # revalidate before reuse: a reflashed page is never served stale (agent, 2026-09-30)`;
  `response.send_file_buffer_size = self._chunk_bytes` with the comment "# Microdot v2.6.2 reads 1,024 B per send_file
  chunk (ext/microdot.py:567, 746); ours is the one write bound." / "# Re-check at a Microdot bump." (version and lines of
  the tag B0 vendors, A.SDEP.06/A.SDEP.18). The three HEAD methods on `WebserverService` go.
- **Resolved**: —
- **Unit**: U19
- **Depends**: M.SRC_NET.118 (`hold()`), M.SRC_NET.119 (registration), A.U11.S02/A.U19.06 (`_RequestLike.sock`,
  SRC_CORE's file)
- **Blast carried by**: `pyproject.toml:309` loses `S101` (and `ANN401`, M.SRC_NET.110), comment `:306-308` → A.U19.05,
  A.U19.17 (tooling; BACKLOG chroot list line); request builders gain `sock=(_NoopHolder(), _NoopHolder())`, static and
  frozen-mount tests, HEAD-close and `Cache-Control` tests → A.U19.06 (tests); comments naming `_serve_static()` in tests
  and SPEC A.5/A.9/I.3, `tests_hardware/README.md:549` → A.U19.05 (tests/docs)
- **Kind**: code

### M.SRC_NET.125 The catch-all error handler records a stack overflow and answers from the catalog
- **From**: A.U19.15 (`make_response(500)`), A.U2.19 (e4 → 23), A.U30.19 (`report_if_fatal(exc)` first), A.U19.17
  (return type)
- **Site**: `src/asy_webserver_service.py:671-676`
- **Change**: `async def _handle_unhandled_exception(self, _request: "_RequestLike", exc: Exception) ->
  "tuple[ResponseEnvelope, int]":` — `report_if_fatal(exc)` first; comment kept (≤ 3 lines); `await self.pr.err_s("Unhandled
  exception in route handler:", exc, errno=_ERR_UNEXPECTED)`; `return ar.make_response(500), 500`.
- **Resolved**: —
- **Unit**: U30
- **Depends**: A.U30.19
- **Blast carried by**: webserver handler raising the stack-exhausted error answers 500 and sets the flag → A.U30.19
  (tests); the L0 fatal-report check names this handler → A.U30.19 (tests)
- **Kind**: code

### M.SRC_NET.126 `_close_writer()`: one entry per close, millisecond bound
- **From**: A.U2.19 (w4 → 52, w5 → 53), A.U3.11 (W53 prints when W52 fired in the same call), A.U31.18
  (`wait_for_ms`), A.U30.19
- **Site**: `src/asy_webserver_service.py:680-690`
- **Change**: `close_failed = False`; `try: writer.close()` / `except Exception as e:` `report_if_fatal(e)`, comment kept
  (≤ 3 lines), `await self.pr.wrn_s("Error closing connection writer:", e, wrnno=_WRN_HTTP_CLOSE_RAISED)`,
  `close_failed = True`; `try: await asyncio.wait_for_ms(writer.wait_closed(), self._per_call_timeout_ms)` / `except
  Exception as e:` `report_if_fatal(e)`; comment "# bounds a hanging wait_closed() (F.6); after a failed close() it only
  prints: one close, one entry"; `if close_failed: self.pr.wrn("Error waiting for writer to close:", e)` `else: await
  self.pr.wrn_s("Error waiting for writer to close:", e, wrnno=_WRN_HTTP_WAIT_CLOSED)`.
- **Resolved**: —
- **Unit**: U31 (A.U31.18 latest; U3 one-entry rule, U2 codes, U30 fatal report — staged)
- **Depends**: M.SRC_NET.112
- **Blast carried by**: the one-entry-per-event L0 scan (no allow-list entry for this pair) and the L1 "close that raises
  and whose wait then fails adds exactly one W52" test → A.U3.11 (tests); persisted-warning tests read the entry →
  A.U24.41 (tests)
- **Kind**: code

### M.SRC_NET.127 `_serve()`: traced drops, split timeouts, released stream, no unreachable arm
- **From**: A.U19.08 ((1)-(3), (4), (6), (7): `_note_drop()`, refusal/peer-reset/bad-head traces, `EOFError` arm goes,
  comment), A.U2.19 (49 vs 50 by `timed_out`, w3 → 51, e1 → 23), A.U19.07 (`head_refused` flag read after
  `handle_request()`), A.U19.06 (`release()` in `finally`), A.U31.18 (`wait_for_ms`, `_ms` bounds), A.U19.17
  (`_StreamLike` annotations), A.U0.29 (`:698` comment), A.U30.19, A.U10.01 (the gauge's cap)
- **Site**: `src/asy_webserver_service.py:692-731`
- **Change**: new `async def _note_drop(self, wrnno: int, what: str) -> None: await self._dropped.increment(); await
  self.pr.wrn_s(what, "- dropped so far:", await self._dropped.get_value(), wrnno=wrnno)` (one comment line: "# One entry
  per event; a run of identical codes spends one history slot (print_log's newest-entry rule)."). `async def
  _serve(self, reader: "_StreamLike", writer: "_StreamLike") -> None:` (the `Any` comment `:693-695` goes: the one
  mismatch moves to `start_server()`, M.SRC_NET.128); `current = await self._open_conns.increment()`; over the ceiling:
  comment "# Reject-when-full (owner, 2026-08-12; SPEC A.8): accepted by asyncio, then closed with no response ever" / "#
  written - cheapest, doesn't risk the rejection path itself becoming a resource consumer."; `await
  self._open_conns.decrement()`; `await self._note_drop(_WRN_HTTP_REFUSED, "Connection refused at the ceiling")`; `await
  self._close_writer(writer)`; `return`. Then `peer_gone = [False]`, `timed_out = [False]`, `head_refused = [False]`;
  `proxy_reader = _TimeoutStreamProxy(reader, self._per_call_timeout_ms, self.pr, peer_gone, timed_out, head_refused,
  self._chunk_bytes)`, `proxy_writer = _TimeoutStreamProxy(writer, self._per_call_timeout_ms, self.pr, peer_gone,
  timed_out)`; `try:` `try: await asyncio.wait_for_ms(self._app.handle_request(proxy_reader, proxy_writer),
  self._outer_cap_ms)` / `except asyncio.CancelledError: raise` (comment kept) / `except asyncio.TimeoutError as e:`
  comment `:717-719` kept, `await self.pr.wrn_s("Connection reclaimed (timed out):", e, wrnno=_WRN_HTTP_CALL_TIMEOUT if
  timed_out[0] else _WRN_HTTP_REQUEST_CAP)` / `except OSError as e:` comment kept, `wrnno=_WRN_HTTP_SOCKET_ERROR` /
  `except Exception as e:  # never raises out of this task (SPECIFICATION.md A.5)` then `report_if_fatal(e)` and `await
  self.pr.err_s("Unexpected error serving connection:", e, errno=_ERR_UNEXPECTED)`; after the inner `try`: `if
  peer_gone[0]: await self._note_drop(_WRN_HTTP_PEER_RESET, "Connection reset by the peer before its response")` and `if
  head_refused[0]: await self._note_drop(_WRN_HTTP_BAD_HEAD, "Request head refused")`; `finally:` `proxy_writer.release()`,
  then HEAD's nested `try: await self._close_writer(writer)` / `finally: await self._open_conns.decrement()` with its two
  comments. The `except EOFError` arm and its comment are gone.
- **Resolved**: HEAD's `except asyncio.TimeoutError` logs one code for two conditions — A.U2.19 splits it by the
  `timed_out` flag (49 write-phase per-call, 50 outer cap); A.U19.08 does not touch that arm; both hold. The EOFError arm's
  W48 is re-homed to the peer-reset trace (U19 A-C note 3), so W48's meaning changes with its only site.
- **Unit**: U31 (A.U31.18 latest; staged: U0 comment, U2 codes, U10 cap, U19 drops/flags/release, U30 fatal report,
  U31 ms)
- **Depends**: M.SRC_NET.112, M.SRC_NET.118, M.SRC_NET.119, M.SRC_NET.126
- **Blast carried by**: `HTTPDropped` in the generated `/status` networking block (`get_dropped_count()`, M.SRC_NET.129)
  → A.U19.10 (GEN); tests (ceiling refusals now logged — tests asserting no log invert; peer-reset entries; W49/W50;
  seven-refusals counter case; preconnect EOF no entry) → A.U19.08, A.U2.19 (tests); `tests_hardware` benign-code lists gain
  60/48 → A.U19.08 (HW); twin concurrency scenario `HTTPDropped` rises → A.U19.08/A.U19.10 (TWIN); SPEC H.7 drop/accept
  sentences with register fix 2's heap clause, A.5 ladder sentence → A.U19.08 (docs); catalog rows → U19 A-C note 3
  (catalog)
- **Kind**: code

### M.SRC_NET.128 `_serve_loop()`: setup in the batch, a bounded start retry, the typed start call
- **From**: A.U10.44 (`_run()` → `_serve_loop()`), A.U10.10 (`pr.setup()` leaves the task), A.U19.09 (start retry),
  A.U19.17 (`# type: ignore[arg-type]` with reason at `start_server()`), A.S0930.18 (read-only: `wait_closed()` forwards a
  cancel and closes the listening socket — pinned by its test)
- **Site**: `src/asy_webserver_service.py:733-739`
- **Change**: `async def _serve_loop(self) -> None:` — the backlog comment `:736-737` kept; `attempt = 0`; `while
  True:` `try: server = await asyncio.start_server(self._serve, self._host, self._port, backlog=self._backlog)  #
  type: ignore[arg-type]` preceded by the comment "# The stub splits MicroPython's one Stream into StreamReader/StreamWriter
  (extmod/asyncio/stream.py:92-93" / "# aliases both to Stream); remove the ignore once the stub models the one class."
  then `break` / `except (MemoryError, OSError) as e:` `attempt += 1`; `if attempt >= _START_RETRIES: await
  self.pr.wrn_s("Web server start failed:", e, wrnno=_WRN_HTTP_START_FAILED); raise`; `self.pr.wrn("Web server start
  failed, retrying:", e)`; `await asyncio.sleep(_START_RETRY_S)`; comment (≤ 3 lines) "# Retries span one lwIP close
  linger (10 s): a socket() failure holds nothing; a failed bind()/listen() holds its pcb until a" / "# collection, up to
  two across the retries. The last failure ends the task for the supervisor (SPECIFICATION.md A.5)."; after the loop
  `await server.wait_closed()`.
- **Resolved**: A.S0930.18 ("DONE-AT-HEAD, pinned") and A.U19.09 both name this function; the retry wraps only
  `start_server()`, `wait_closed()` stays — the cancel property A.S0930.18 pins is unchanged (A.S0930.18's Depends:
  "A-C merges").
- **Unit**: U19 (U10 stage: name, setup removal)
- **Depends**: M.SRC_NET.112, M.SRC_NET.119 (`setup()`), A.U10.10
- **Blast carried by**: tests (fake `start_server` failing twice then serving; failing three times → one persisted
  entry and re-raise; the cancel-closes-the-port test on a file-owned port block) → A.U19.09, A.S0930.18 (tests); SPEC
  A.5 ladder sentence, F.5 forwarded-cancel fact → A.U19.09, A.S0930.18 (docs); catalog 62 → U19 A-C note 3 (catalog)
- **Kind**: code

### M.SRC_NET.129 Starters, error sources, drop count and a comment without history
- **From**: A.U10.44 (`_start_serving()` → `start_asy_serve()`), A.U19.17 (`TaskStarter`, `ErrorSource`), A.U19.10
  (`get_dropped_count()`), A.U11.31 (`reset_error_counter() -> bool`); adherence finding (`:749-752` cites a temporary
  plan step, G9/R12, and is history)
- **Site**: `src/asy_webserver_service.py:741-767`
- **Change**: `def start_asy_serve(self) -> "asyncio.Task[None]": return asyncio.get_event_loop().create_task(self._serve_loop())`;
  `get_task_starters(self) -> "list[TaskStarter]": return [self.start_asy_serve]`; `get_timer_starters(self) ->
  "list[Callable[[], None]]": return []` with the comment "# No machine.Timer in this module: kept empty, not omitted, so
  callers treat every module alike (SPECIFICATION.md C.9)."; `get_error_sources(self) -> "list[ErrorSource]"` (comment
  kept); `get_loggers()` unchanged; new `async def get_dropped_count(self) -> int: return await
  self._dropped.get_value()`; `async def reset_error_counter(self) -> bool: return await self.pr.reset()`.
- **Resolved**: HEAD's "found missing entirely during the Step 7 audit, unlike those two" names a temporary plan step
  (G9/R12: permanent text cites no temporary plan by section or number) and is history (CLAUDE.md working agreement);
  no action carries it — rewritten here.
- **Unit**: U19 (U10 stage: starter name; U11 stage: `-> bool`)
- **Depends**: M.SRC_NET.127
- **Blast carried by**: generated collectors call `get_task_starters()`; generated `_networking_status()` reads
  `webserver.get_dropped_count()` → A.U19.10 (GEN); tests calling `_start_serving()`/`_run()` by name → A.U10.44 (tests)
- **Kind**: code

### M.SRC_NET.130 Module helpers: typed, central B905, fatal report
- **From**: A.U19.17 (types), A.U28.28 (the B905 inline `noqa` goes), A.U19.15 (`_shaped_error_handler(status_code)`),
  A.U30.19 (`_body_as_dict()`'s broad handler)
- **Site**: `src/asy_webserver_service.py:770-807`
- **Change**: `_shape_errcount_entry(raw: "ErrorLog", name: str) -> "JsonDict"`: the history comprehension without the
  inline `noqa` (B905 exempt centrally for MicroPython-run code, A.U28.27/A.U28.28), its two-line reason comment kept as
  one line "# No strict= (ruff B905): MicroPython's zip() rejects it; ErrEntry keeps both lists in step."; `_body_as_dict(request)
  -> "dict[str, JsonValue] | None"`: `except Exception as e: report_if_fatal(e); return None`; `_mark_connection_close()`
  unchanged; `_shaped_error_handler(status_code: int) -> "Callable[[_RequestLike], tuple[ResponseEnvelope, int]]"`,
  whose inner handler returns `ar.make_response(status_code), status_code`.
- **Resolved**: —
- **Unit**: U30 (U19/U28 stages first)
- **Depends**: A.U28.27, M.SRC_NET.112
- **Blast carried by**: `asy_api_response` catalog gains 400/404/405/413/500 → A.U19.15 (SRC_CORE); shaped-error tests hold
  (texts unchanged) → A.U19.15 (tests); ruff clean over the scope → A.U28.28 (tooling)
- **Kind**: code

### M.SRC_NET.131 Member order per D.15 (webserver)
- **From**: A.U10.33
- **Site**: `src/asy_webserver_service.py` classes `_PieceWriter`, `SettingsGroup`, `_TimeoutStreamProxy`,
  `WebserverService`, module functions
- **Change**: pure reorder by D.15's key (A.U10.32), AST-verified; members added after U10 (`_StaticRoutes`, `_HeadRefused`,
  `_note_drop()`, `_run_system_cmd()`, `get_dropped_count()`, `hold()`/`release()`, `setup()`) placed by the same key when
  written.
- **Resolved**: —
- **Unit**: U10 (last U10 edit)
- **Depends**: every U10 edit of the file
- **Blast carried by**: —
- **Kind**: code

### M.SRC_NET.132 The `peer_gone` suppression's reason follows the pinned modlwip
- **From**: A.SDEP.13 (the write-after-reset re-read), A.U19.22 (read: withdrawn, no `TCP_NODELAY` call)
- **Site**: `src/asy_webserver_service.py:255-259, :269-270` (the `peer_gone` suppression in `_TimeoutStreamProxy`)
- **Change**: conditional, at the MicroPython bump: if the new tag's `lwip_tcp_send()` refuses a write on a closed/freed
  pcb with an error, the suppression's comment states that reason ("it still saves a pointless write") and its
  retirement is recorded as a U19 delta; otherwise nothing changes. No `setsockopt(TCP_NODELAY)` is added whatever the
  re-read finds (OR114.a (2), owner's decision).
- **Resolved**: —
- **Unit**: the SDEP bump (A.SDEP.13), after U19's M.SRC_NET.118
- **Depends**: M.SRC_NET.118, A.SDEP.08 (the pin)
- **Blast carried by**: the override decision (A.U21.09-.14) → A.SDEP.13 (TOOL); SPEC B.14.2.1 → A.U14.30 (SPEC)
- **Kind**: code

## src/asy_uart_comm.py

The protocol module of the two-implementation contract: every merged change below names the `UART_C_PORT_CHANGELOG.md`
entry its constituents carry (DOCS cluster writes the file; numbering in landing order, A.U17.30); a comment-only or
annotation-only change carries none, per its constituent. No merged change here blocks the loop: every new wait is an
`await asyncio.sleep_ms()` or goes through the driver's `ready()` (CLAUDE.md UART rule, F.5.8/F.5.9).

### M.SRC_NET.150 Imports and the `TYPE_CHECKING` block
- **From**: A.U10.37 (`asy_base_classes`, `asy_print_log`), A.U16.05 (`LockableBuffer` → `RegionBuffer`), A.U10.04 +
  A.U10.01 (`COUNTER_CAP`), A.U17.13 (`COUNTER_CAP` for `_take_discarded()`), A.U5.02/A.U5.12 (`DEFAULT_LOG`,
  `LogConfig`; the FRAM-manager import goes), A.U17.26 (`Any`/`_asyncio` go; `TaskStarter`/`TimerStarter`), A.U10.46
  (alias home), A.U30.19 (`report_if_fatal`), A.U10.31 (unquote)
- **Site**: `src/asy_uart_comm.py:8-58`
- **Change**: runtime imports: `import asyncio` / `import time` / `from collections import namedtuple` / `from micropython
  import const` / `from asy_base_classes import COUNTER_CAP, RegionBuffer` / `from asy_print_log import
  DEFAULT_LOG, PrintLogHistory, make_logger, report_if_fatal` (the fatal report's home, M.SRC_CORE.034; GAP-G8). `TYPE_CHECKING` block: `from collections.abc import Callable` (kept: `_call()`),
  `from typing import Protocol`, `from asy_base_classes import TaskStarter, TimerStarter`, `from asy_print_log import
  ErrorLog, LogConfig`, `from asy_uart_driver import UART`; `import asyncio as _asyncio`, `Any` and the
  `asy_fram_manager` import go. The five callback `Protocol` classes and `Readable`/`Writable` unchanged (their comments
  kept).
- **Resolved**: —
- **Unit**: U30 (A.U30.19's import is the last to land). Staged: U5 (`DEFAULT_LOG`/`LogConfig`, FRAM import out), U10
  (module renames, `COUNTER_CAP`, unquoting), U16 (`RegionBuffer`), U17 (`TaskStarter`/`TimerStarter`, `Any` out), U30
  (`report_if_fatal`). Each stage leaves the file importing exactly the names it uses (ruff F401).
- **Depends**: A.U10.01/A.U10.46/A.U16.05 in `asy_base_classes` and A.U30.19 in `asy_print_log` (M.SRC_CORE.031/.030/.027/.034),
  A.U5.01 (`LogConfig`)
- **Blast carried by**: UART changelog Class B entries for the renames → A.U10.37, A.U16.05 (DOCS); ANN401 baseline list
  loses the file → A.U17.26/A.U8.24 (TOOL)
- **Kind**: code

### M.SRC_NET.151 Command-byte names: only `CMD_SET` stays public
- **From**: A.U10.29 (`CMD_ACK`/`CMD_GET` → `_CMD_ACK`/`_CMD_GET`, comment)
- **Site**: `src/asy_uart_comm.py:66-71`; every use (`:285`, `:417`, `:445`, `:1003`, `:1012`, `:1026-1037`, `_get_unlocked()`
  `:922`, `_write_frame_with_ack()` `:637`)
- **Change**: `:66-68` → "# CMD_SET is public: asy_uart_link_driver.py imports it; ACK and GET are module-private.";
  `_CMD_ACK = const(0x01)`, `_CMD_GET = const(0x02)`, `CMD_SET = const(0x04)`; every use follows. `ROLE_INITIATOR`/
  `ROLE_RESPONDER` stay public (imported by `asy_uart_link_driver.py` and `buildgen/validate.py`, A.U20.27). Values
  unchanged.
- **Resolved**: —
- **Unit**: U10
- **Depends**: —
- **Blast carried by**: UART changelog Class B "`CMD_ACK`/`CMD_GET` become module-private names; values and wire unchanged"
  → A.U10.29 (DOCS); tests keep their J.3 wire copies (`tests/test_asy_uart_comm.py:33-42`) → A.U24.01/A.U24.02 (TEST_UNIT);
  the L0 constants table lists `_CMD_ACK`/`_CMD_GET` → A.U17.11 (SCR/DOCS)
- **Kind**: code

### M.SRC_NET.152 Recovery and timing constants: tags, Part J pointers, the two ceilings
- **From**: A.U8.06 (tags `:93-95, :98`), A.U36.544 (3) (`:87` "changelog A4", `:90` "changelog A5" → Part J), A.U17.20
  (`_TICKS_HORIZON_MS`, `_POLL_WAIT_MAX_MS`), A.U3.02 (`_REJECT_MAP_LEN` goes), A.U10.37 (the `captive_dns.py` mention),
  A.U17.14 (read: `_DIAG_RESYNC_STREAK` is the cap)
- **Site**: `src/asy_uart_comm.py:81-102`
- **Change**: `:87` "Both are 1.5 x timeout and both are part of the wire contract (changelog A4)." → "… part of the wire
  contract (Part J)."; `:90` "The drain's own hard bound (changelog A5)." → "The drain's own hard bound (Part J.5)."; tags
  (A.U8.02 grammar, beside the existing trailing comments or on the line above where the line would pass the cap):
  `_GATE_STEP_MS` `# @tunable uart.gate_step_ms = 20`, `_GC_PAUSE_WORST_MS` `# @tunable uart.gc_pause_worst_ms = 21`,
  `_POLL_JITTER_MS` `# @tunable uart.poll_jitter_ms = 5`, `_DIAG_RESYNC_STREAK` `# @tunable uart.diag_resync_streak = 2`;
  the contract constants (`_UID_MAX`, `_CHUNKS_MAX`, `_PAYLOAD_MIN/MAX`, `_RESYNC_NUM/DEN`, `_DRAIN_BOUND_MULT`,
  `_BACKOFF_MULT`, `_BACKOFF_MAX_MULT`, `_MIN_CHUNKS`) stay untagged. `_BACKOFF_MAX_MULT`'s comment → "cap = 5 x timeout,
  matching asy_captive_dns.py's own 500 ms -> 5 s shape". New, after `_CMD_ID_MAX`: `_TICKS_HORIZON_MS =
  const(0x1FFFFFFF)  # 2**29 - 1: the longest delay ticks_add() and sleep_ms() take and the widest span ticks_diff()
  compares (F.1)` and `_POLL_WAIT_MAX_MS = const(9)  # J.6: a transaction polls at single-digit milliseconds` (contract
  bounds, untagged, A.U17.20). `_REJECT_MAP_LEN` and its comment go.
- **Resolved**: A.U8.06 "Depends: U17's upper bounds … may change the literals — the tags move with them": no tagged
  literal changes value here (the two new constants are bounds, not tunables, per A.U17.20).
- **Unit**: U36 (A.U36.544's label removal). Staged: U3 (`_REJECT_MAP_LEN` out, with its users, M.SRC_NET.157/.163),
  U8 (tags), U10 (the module name in the comment), U17 (two new constants).
- **Depends**: A.U8.01/A.U8.02 (tag grammar, Part N rows)
- **Blast carried by**: Part N rows `uart.*` (Basis, "Re-check trigger: any value change is logged in
  UART_C_PORT_CHANGELOG.md") and actor-tag normalisation (AC_NOTES 6) → A.U8.06 (DOCS); `buildgen/validate.py:246-273`
  reads `_GC_PAUSE_WORST_MS` from source (comments do not change the AST) → A.U8.06 (GEN); UART changelog Class B for the
  two ceilings → A.U17.20, for the map's removal → A.U3.13 (DOCS); L0 constants table rows (`_TICKS_HORIZON_MS`,
  `_POLL_WAIT_MAX_MS` Class B; no `_REJECT_MAP_LEN`) → A.U17.11 (SCR/DOCS); the changelog keeps its A4/A5 entries → A.U36.544
- **Kind**: code

### M.SRC_NET.153 Error codes: catalog names and numbers, two new UART codes
- **From**: A.U2.20 (renames/values, band comment, `_ERRNO_MIN/_MAX`/`_WRNNO_MIN/_MAX` go), A.U2.04 (named-constant
  idiom), A.U3.08 (`_WRN_RESYNC` goes), A.U3.02 (`_WRN_FAULT_CLEARED` goes), A.U17.20 (`_ERR_UART_POLL_RATE`), A.U17.22
  (`_ERR_UART_CODEC_SIZE`), A.U2.01 (the band and rows)
- **Site**: `src/asy_uart_comm.py:104-141` (block and comment) and every `_err`/`_fault`/`err_s`/`wrn_s` use in the file
- **Change**: comment `:104-106` → "# Codes from the global catalog (buildgen/error_catalog.json): the UART band 75-99
  for this module's own conditions, the shared codes for the rest. Mirrored in SPECIFICATION.md Part C.7.1." Block:
  shared `_ERR_CALLBACK = const(14)`, `_ERR_NOT_INIT = const(18)`, `_ERR_ALLOC = const(20)`, `_ERR_BAD_ARG = const(21)`,
  `_ERR_TIMEOUT = const(22)`, `_ERR_UNEXPECTED = const(23)`; band `_ERR_UART_PAYLOAD_SIZE` 75, `_ERR_UART_TIMEOUT_PARAM`
  76, `_ERR_UART_NO_BUS` 77, `_ERR_UART_RXBUF` 78, `_ERR_UART_ROLE_REFUSED` 79, `_ERR_UART_FRAME_INVALID` 80,
  `_ERR_UART_NO_ACK` 81, `_ERR_UART_WRITE_FAILED` 82, `_ERR_UART_PAYLOAD_TOO_LARGE` 83, `_ERR_UART_SIZE_MISMATCH` 84,
  `_ERR_UART_REENTRANT` 85, `_ERR_UART_WRONG_KIND` 86, `_ERR_UART_GET_ID_MISMATCH` 87, `_ERR_UART_PEER_INITIATED` 88,
  `_ERR_UART_LINK_UNINTELLIGIBLE` 89, `_ERR_UART_STREAM_SHORT` 90, `_ERR_UART_POLL_RATE` 91, `_ERR_UART_CODEC_SIZE` 92;
  `_WRN_UART_DRAIN_BOUND` 54, `_WRN_UART_CANCEL_UNACKED` 55, `_WRN_UART_CMD_DECLINED` 56. HEAD → end: e14/e24 →
  `_ERR_ALLOC`; e17 → `_ERR_NOT_INIT`; e22 → `_ERR_TIMEOUT`; e26 → `_ERR_CALLBACK`; e30 → `_ERR_UNEXPECTED`; e12/e16/e34 →
  `_ERR_BAD_ARG`; w11/w13/w14 → 54/55/56; w10 and w12 have no constant. Every use site passes the new name.
- **Resolved**: A.U3.08 writes "errno 32→91 (`LINK_UNINTELLIGIBLE`)"; A.U2.01's catalog row lists the sixteen band codes
  75-90 in HEAD order, which puts e32 at 89 — the catalog is the numbering source (A.U2.20 "the catalog names and values
  of A.U2.01"), so 89 stands and A.U3.08's "91" is read as a slip. The two new codes are numbered after the band's last
  used code in landing order (A.U17.20 before A.U17.22 within U17): 91, 92 — agent decision, OR2.c list.
- **Unit**: U17 (the two new codes). Staged: U2 (renames and values, the catalog check A.U2.02 passes from U2 on), U3 (w10,
  w12 constants out with their users), U17 (91, 92).
- **Depends**: A.U2.01 catalog file (GEN, M.GEN.034)
- **Blast carried by**: catalog rows 91 `UART_POLL_RATE`, 92 `UART_CODEC_SIZE` → M.GEN.034 (A.U17.20/.22); UART changelog
  Class B renumbering entry → A.U2.26 (DOCS); tests (54 lines in `test_asy_uart_comm.py`, `test_uart_comm_hazard.py`
  RF135 copies, `persisted()` "W14" → 56) → A.U2.20/A.U2.03 (TEST_UNIT); device-script prints → A.U2.20 (HW_DEV); SPEC
  C.7.1/C.7.2/J.1/J.5/J.6/J.9/E.8 numbers, `tests_hardware/README.md:464, :1418`, BACKLOG `:374-376, 385` → A.U2.20
  (SPEC, DOCS); js mock `UART_init`/`UART_resp` rows → A.U2.20 (WEB)
- **Kind**: code

### M.SRC_NET.154 `ResponderCallbacks`: one object for the responder's three callbacks
- **From**: A.U5.12
- **Site**: `src/asy_uart_comm.py:143-147` (beside `ListenResult`)
- **Change**: `ResponderCallbacks = namedtuple("ResponderCallbacks", ("get", "set", "message"))` directly above
  `ListenResult`, with one comment line "# A responder's get/set callbacks (both required) and its optional message
  callback, passed as one object." Public: `asy_uart_link_driver.py` builds it.
- **Resolved**: —
- **Unit**: U5
- **Depends**: —
- **Blast carried by**: see M.SRC_NET.155
- **Kind**: code

### M.SRC_NET.155 `UARTComm.__init__`: callbacks and log objects, private attributes, no episode state
- **From**: A.U10.38 (`UART_Comm` → `UARTComm`), A.U5.12 (signature, unpacking), A.U5.02 (`log`, `make_logger(log,
  name)`), A.U10.35 (`get_callback`/`message_callback`/`frame_size` private), A.U3.02 (`_last_errno`, `_fault_streak`,
  `_episode_events`, `_rejected` go), A.U17.13 (`_discarded_seen`), A.U17.06 (read: `:202-203` init unchanged), A.U10.31;
  adherence addition (G10/R07, D.10): `set_callback` private with its two siblings
- **Site**: `src/asy_uart_comm.py:166-222`
- **Change**: `class UARTComm:` / `def __init__(self, uart: "UART | None", role: str, payload_size: int = 48, timeout: int
  = 1000, callbacks: ResponderCallbacks | None = None, name: str = _NAME, log: "LogConfig" = DEFAULT_LOG, logger:
  PrintLogHistory | None = None) -> None:`; logger resolution: `self.pr = logger if logger is not None else
  make_logger(log, name)` (comment `:182` kept); `self._get_callback`, `self._set_callback`, `self._message_callback` =
  `callbacks.get`/`.set`/`.message`, or `None` each when `callbacks is None` (the optional-message comment `:194-195` kept
  above the unpack); `self._frame_size = _HEADER_LEN + payload` and every reader (`_allocate()`, `_buffers_ready()`,
  `_validate()`, `_read_frame()`, `_send_ack()`, `_write_frame_with_ack()`) follows; `self._last_errno`,
  `self._fault_streak`, `self._episode_events` and their comments go; `self._discarded_seen = 0` after
  `_cancel_unacked_seen` (comment: M.SRC_NET.162); `self._tx, self._rx, self._ack, self._zero, self._cmd_buf =
  self._allocate()`; `self._uart`, `self._role`, `self._payload_size`, `self._timeout`, `self._uid` (gap pass G2: no reader outside the class in `src/` or the generated code — G10/R07 "private by default", M_SRC_CORE GAP-G12; every use in the file follows,
  M.SRC_NET.156 and the transfer paths); the rest (`initialized`, `_busy`, `_in_resync`, `_holdoff_*`, `_valid_frames`,
  `_blind_resyncs`, `_drain_bound_hit`, `_cancel_unacked_seen`, `_init_errno`, the re-check comment, backoff fields,
  construction print) unchanged. 8 parameters (A.U5.17 `max-args = 8`), ending `…, log, logger` (A.U5.18's tail probe;
  `logger` recorded by A.U5.12).
- **Resolved**: A.U5.12 unpacks into "the existing attributes `get_callback`/`set_callback`/`message_callback`" (U5);
  A.U10.35 (U10) privatises two of them from S09's list, which omits `set_callback` only because no test reads it (grep:
  no reader outside the module) — G10/R07 "private by default" and D.10 (one shape within a class) make all three
  private (agent, adherence finding; OR2.c list).
- **Unit**: U17 (A.U17.13's `_discarded_seen`). Staged: U3 (episode state out), U5 (signature, unpack), U10 (class name,
  private names, unquoting), U17 (`_discarded_seen`).
- **Depends**: M.SRC_NET.154, A.U5.01 (`LogConfig`), A.U3.01 (the central newest-entry rule that replaces the episode
  state)
- **Blast carried by**: `UARTLinkDriver` construction → M.SRC_NET.213; tests (`tests/_uart_comm_harness.py:71-80`, 12
  `UART_Comm(` calls, 88 callback keywords, `make_comm()`, `test_uart_comm_hazard.py:789, 808, 1115, 1171`, readers of
  `get_callback`/`message_callback`/`frame_size`/`set_callback`) → A.U5.12, A.U10.35 (TEST_UNIT, TEST_HELP); UART device
  scripts → A.U5.12 (HW_DEV); SPEC J.9 constructor contract → A.U5.12 (SPEC); UART changelog Class B (constructor
  objects; names; private attributes incl. `set_callback` — see Gaps) → A.U5.12, A.U10.38, A.U10.35 (DOCS)
- **Kind**: code

### M.SRC_NET.156 Construction checks: codec size, timeout ceiling, poll range
- **From**: A.U17.20 (`_max_timeout()`, timeout ceiling, poll range), A.U17.22 (delimited codec sized to a frame),
  A.U2.20 (`_ERR_ROLE_PARAM`/`_ERR_NO_CALLBACK` → `_ERR_BAD_ARG`, band names), A.U5.12 (callback refusal unchanged),
  A.U10.38 (codec class names in comments)
- **Site**: `src/asy_uart_comm.py:230-271` (`_validate_config()`, `_min_timeout()`, `_min_rxbuf()`), new `_max_timeout()`
- **Change**: `_validate_config()` order: `uart is None` → `_ERR_UART_NO_BUS`; framing not ready → `_ERR_ALLOC`;
  `payload_size` type/range → `_ERR_UART_PAYLOAD_SIZE`; then `if self._uart.framing.is_delimited() and
  self._uart.framing.max_frame < _HEADER_LEN + self._payload_size + self._uart.crc.length(): return _ERR_UART_CODEC_SIZE  # a
  delimited codec must carry one whole frame`; role → `_ERR_BAD_ARG`; `timeout` not a positive int →
  `_ERR_UART_TIMEOUT_PARAM`; `if self._timeout > self._max_timeout(): return _ERR_UART_TIMEOUT_PARAM`; `if not
  isinstance(self._uart.poll_wait_ms, int) or not 1 <= self._uart.poll_wait_ms <= _POLL_WAIT_MAX_MS: return
  _ERR_UART_POLL_RATE  # J.6`; the floor `timeout < _min_timeout()` → `_ERR_UART_TIMEOUT_PARAM` (comment kept); responder
  without `_get_callback`/`_set_callback` → `_ERR_BAD_ARG` (comment kept); rxbuf floor → `_ERR_UART_RXBUF`. New
  `def _max_timeout(self) -> int: return (_TICKS_HORIZON_MS * _RESYNC_DEN) // (_RESYNC_NUM * _DRAIN_BOUND_MULT)` with
  "# The drain bound, 6 x timeout, is the largest deadline derived from timeout; it must stay a valid ticks delay."
  (= 89,478,485 ms). `_min_timeout()`/`_min_rxbuf()` unchanged. Nothing is clamped.
- **Resolved**: —
- **Unit**: U17
- **Depends**: M.SRC_NET.152, M.SRC_NET.153, A.U17.21 (the same arithmetic at build, GEN), A.U12.16 (codec `__init__`),
  A.U10.37 (`asy_framing_codecs`)
- **Blast carried by**: `FramingCOBS._checked_encoded()`/`decode_from()` → A.U17.22 (SRC_CORE); tests (`:105-111`
  poll 9/9, `:165-170` rxbuf assertion names the code, new ceiling/poll/codec cases, backoff-under-ceiling case) →
  A.U17.20, A.U17.22 (TEST_UNIT); SPEC J.6 ceilings sentence, J.3/G.2 codec sentence, C.7.2 → A.U17.20/.21/.22 (SPEC);
  UART changelog Class B (two refusals; codec bound) → A.U17.20, A.U17.22 (DOCS); catalog 91/92 → M.GEN.034
- **Kind**: code

### M.SRC_NET.157 `_allocate()`/`_buffers_ready()`: five buffers, region buffers
- **From**: A.U3.02 (the declined-id bitmap and its readiness term go), A.U16.05 (`RegionBuffer`), A.U10.29 (`_CMD_ACK`),
  A.U10.35 (`_frame_size`), A.U10.31 (return annotation unquoted)
- **Site**: `src/asy_uart_comm.py:273-310`
- **Change**: `def _allocate(self) -> tuple[RegionBuffer, RegionBuffer, bytearray, bytearray, bytearray]:`; comment
  `:274-276` "…the zero padding and the command-id scratch." (the bitmap words go, rest kept); `tx`/`rx` are
  `RegionBuffer(room, data_start=_HEADER_LEN, data_length=…)`; the `try` builds `ack`, `zero`, `cmd_buf`; its `except
  (MemoryError, OverflowError)` returns `tx, rx, bytearray(0), bytearray(0), bytearray(0)`; `ack[_MSG_CMD] = _CMD_ACK`;
  `return tx, rx, ack, zero, cmd_buf`. `_buffers_ready()`: comment "…guards its three scratch buffers as one group…";
  the `len(self._rejected)` term goes.
- **Resolved**: —
- **Unit**: U16 (A.U16.05). Staged: U3 (bitmap out), U10 (names).
- **Depends**: M.SRC_NET.151, M.SRC_NET.155, A.U16.05's `RegionBuffer` (SRC_CORE)
- **Blast carried by**: `tests/test_asy_uart_comm.py:347-365` five-tuple → A.U3.02; `:19, 337, 1256, 2182`
  `LockableBuffer` mentions → A.U16.05 (TEST_UNIT); allocation budget pinned by `test_uart_comm_hazard.py` holds
  (one buffer fewer); UART changelog Class B (`RegionBuffer`; bitmap removed) → A.U16.05, A.U3.13 (DOCS)
- **Kind**: code

### M.SRC_NET.158 Logging helper: one plain `_err()`, no episode mechanism
- **From**: A.U3.02 (`_err()` dedupe, `_fault_cleared()`, `_episode_wrn()`, `_clear_fault_state()` go), A.U3.08 (resync
  prints), A.U2.20 (names)
- **Site**: `src/asy_uart_comm.py:314-347`
- **Change**: section heading kept; `async def _err(self, errno: int, *args: object) -> None: await
  self.pr.err_s("UART error:", *args, errno=errno)` with one comment line "# Every fault persists its errno; a repeat of
  the newest code is collapsed by the central rule (C.7.1)." `_fault_cleared()`, `_episode_wrn()`,
  `_clear_fault_state()` and their comments go (callers: M.SRC_NET.162, .163, .165, .171, .173).
- **Resolved**: —
- **Unit**: U3
- **Depends**: A.U3.01 (`print_log`'s newest-entry rule, SRC_CORE), M.SRC_NET.153
- **Blast carried by**: tests `test_asy_uart_comm.py:221-231` (`_last_errno` assert goes), `:234-273` (repeat tests
  rewritten to the central rule), `:801-835`, `:1458-1493`, `:1729-1746`, `:1763-2033` (`[errno, "W10"]` → `[errno]`) →
  A.U3.02, A.U3.08 (TEST_UNIT); SPEC J.5 `:5491-5497`, J.6 `:5514-5516`, E.8 → A.U3.08 (SPEC); UART changelog Class B,
  B20/B28/B32 superseded → A.U3.13 (DOCS)
- **Kind**: code

### M.SRC_NET.159 Frame validation refuses a GET that is not one chunk
- **From**: A.U17.16, A.U36.544 (3) (`:483` "changelog A12" → Part J), A.U10.29 (`_CMD_ACK`/`_CMD_GET` in
  `_prepare_tx()`/`_validate()`), A.U2.20 (`_ERR_UART_FRAME_INVALID`, `_ERR_UART_WRONG_KIND`, `_ERR_UART_NO_ACK`)
- **Site**: `src/asy_uart_comm.py:406-494` (`_prepare_tx()`, `_validate*()`)
- **Change**: `_prepare_tx()`'s kind check `cmd not in (_CMD_ACK, _CMD_GET, CMD_SET)`; `_validate()` likewise;
  `_validate_size_for_position()`: comment `:482-483` → "…each rule here closes a silent-corruption path (Part J.4).";
  in the `cur == 1` branch after the SET test: `if cmd == _CMD_GET and chunks != 1: return _ERR_UART_FRAME_INVALID  # a
  GET is a one-chunk train (J.4)`. Every other return passes the band name.
- **Resolved**: —
- **Unit**: U36 (A.U36.544's label). Staged: U2 (names), U10 (`_CMD_*`), U17 (the new refusal).
- **Depends**: M.SRC_NET.151, M.SRC_NET.153
- **Blast carried by**: tests (CHUNKS 0-255 sweep both CRC modes; no-ACK list gains "GET with CHUNKS 2") → A.U17.16
  (TEST_UNIT); L2 sweep → A.U17.25 (TWIN); SPEC J.4 GET paragraph → A.U17.16 (SPEC); UART changelog **Class A** A13
  "Reject a GET frame whose CHUNKS is not 1" (receiver-only tightening) → A.U17.16 (DOCS); traceability row → A.U17.12
- **Kind**: code

### M.SRC_NET.160 A stale write hold-off expires
- **From**: A.U17.06
- **Site**: `src/asy_uart_comm.py:516-525` `_await_write_gate()`
- **Change**: `if remaining <= 0 or remaining > self._resync_window_ms():` with "# The deadline is set one window ahead,
  so more than a window remaining means the stored tick aged past ticks_diff()'s 2**29 ms horizon (idle > 6.2 days):
  expired. The one aliased band left costs at most one window, a normal hold-off." (3 lines). `_hold_off_writes()`,
  `_resync_window_ms()` and `uart_listen()`'s early reset unchanged.
- **Resolved**: —
- **Unit**: U17
- **Depends**: M.SRC_NET.156 (the timeout ceiling keeps the window below 2**29), A.U14.34 (`tests/_ticks30.py`)
- **Blast carried by**: tests (aged, aliased-band and un-aged cases on `Ticks30Time`) → A.U17.06/A.U14.34 (TEST_UNIT);
  SPEC J.5 hold-off sentence → A.U17.06 (SPEC); UART changelog Class B (tick-horizon expiry; note for the C side's
  32-bit tick) → A.U17.06 (DOCS)
- **Kind**: code

### M.SRC_NET.161 `_drain()`'s comment says who persists the drain bound
- **From**: A.U3.08/A.U3.02 (the episode wording loses its referent); adherence finding (CLAUDE.md "documentation
  contains current state")
- **Site**: `src/asy_uart_comm.py:548-550`
- **Change**: "# Visible only, and flagged rather than persisted here: the caller owns the episode's one slot, and setup()'s
  boot drain owns no episode at all (SPECIFICATION.md C.7.1)." → "# Visible only, and flagged rather than persisted here:
  the resync that called it persists W54, and setup()'s boot drain persists nothing (C.7.1)." Code unchanged.
- **Resolved**: —
- **Unit**: U3
- **Depends**: M.SRC_NET.162
- **Blast carried by**: — (comment only, no changelog entry)
- **Kind**: code

### M.SRC_NET.162 `_resync()`: prints, persists W54 only on the bound, counts swallowed bytes, stops the streak at its cap
- **From**: A.U3.08 (print; W54 persisted only when the bound was hit; W11 precedence), A.U3.02 (`_episode_wrn()` calls
  go), A.U17.13 (`_take_discarded()`), A.U17.14 (streak saturates), A.U2.20 (names)
- **Site**: `src/asy_uart_comm.py:562-590` `_resync()`; new `_take_discarded()` beside it
- **Change**: `drained = await self._drain(device) + self._take_discarded()`; the logging block → `if
  self._drain_bound_hit: await self.pr.wrn_s("Resynced the link - drain bound reached, the peer never stopped sending",
  wrnno=_WRN_UART_DRAIN_BOUND)` / `else: self.pr.wrn("Resyncing the link")`, its comment → "# A resync is routine and
  prints; only a drain that hit its bound (a babbling or misconfigured peer) persists W54. Logged after the drain, which
  decides which one this is." Then `_hold_off_writes()` and `resync_framing()` as today; the blind-resync block: `if
  self._blind_resyncs < _DIAG_RESYNC_STREAK: self._blind_resyncs += 1` then the unchanged `>=` test calling
  `self._err(_ERR_UART_LINK_UNINTELLIGIBLE, …)` (message kept). New `def _take_discarded(self) -> int:` — `0` for a
  `None` bus; else `n = (bus.discarded_bytes - self._discarded_seen) & COUNTER_CAP`, `self._discarded_seen =
  bus.discarded_bytes`, `return n`; comment "# Bytes a failed frame read swallowed since the last resync: without them a
  peer that only speaks when spoken to never shows the mismatch signature (J.6)." `_valid_frames == 0` gate and
  `_DIAG_RESYNC_STREAK` unchanged.
- **Resolved**: A.U3.08 "prints 'Resyncing the link' and persists W54 only when `_drain_bound_hit`" with "W11's precedence
  kept" — written as one or the other (the persisted W54 text says it resynced), matching HEAD's one-slot precedence.
- **Unit**: U17. Staged: U3 (logging), U17 (count, cap).
- **Depends**: M.SRC_NET.153, M.SRC_NET.158, M.SRC_NET.196/.200/.201 (the driver's `discarded_bytes`), A.U10.01
- **Blast carried by**: tests (fault with quiet line adds one entry; bound adds errno + 54; streak saturates at 2; the
  inverted blind-spot check; CRC16 frame-corrupt diagnostic; L2 mismatched-payload pair) → A.U3.08, A.U17.13, A.U17.14
  (TEST_UNIT, TWIN); SPEC J.6 and changelog B26 → A.U17.15 (SPEC, DOCS); A.U10.05's counter check lists `_blind_resyncs`
  capped and `discarded_bytes` masked → A.U10.05 (SCR); UART changelog Class B (resync logging A.U3.13; B26; streak cap
  A.U17.14) (DOCS)
- **Kind**: code

### M.SRC_NET.163 `_fault()`/`_reject_wrn()`: a declined command persists W56 each time
- **From**: A.U3.02 (bitmap and repeat branch go), A.U2.20 (`_WRN_UART_CMD_DECLINED`), A.U17.17 (read: the declined path
  returns `ListenResult.cmd` set)
- **Site**: `src/asy_uart_comm.py:592-610`
- **Change**: `_fault()` unchanged (comment's "twenty-eight call sites" → "every call site"). `_reject_wrn(self, device,
  cmd_id)`: comment → "# A declined command persists W56 every time (a run of identical codes spends one slot under the
  central rule) and, like every refusal, resyncs."; body `await self.pr.wrn_s("callback rejected command", cmd_id,
  wrnno=_WRN_UART_CMD_DECLINED)` then `await self._resync(device)`.
- **Resolved**: —
- **Unit**: U3
- **Depends**: M.SRC_NET.158, M.SRC_NET.162
- **Blast carried by**: tests `:1983-2000` (one W56 slot, count per refusal), `:234-273` → A.U3.02 (TEST_UNIT); UART
  changelog Class B → A.U3.13 (DOCS)
- **Kind**: code

### M.SRC_NET.164 `_write_frame_with_ack()` and `_note_valid_frame()`: owner tag, narrowing stated, saturating count, no per-frame coroutine
- **From**: A.U0.28 (`:649-650` owner tag), A.U35.47 (`:636-639`), A.U10.04 (`_valid_frames` saturates), A.U3.02
  (`_fault_cleared()` call goes), A.U10.29/A.U2.20 (names), A.U10.35 (`_frame_size`); adherence addition (G4/R42 no
  same-shaped churn on a hot path): `_note_valid_frame()` becomes synchronous
- **Site**: `src/asy_uart_comm.py:629-661`; callers `:651`, `:777`, `:973`, `:1011`
- **Change**: `_write_frame_with_ack()`: the `buf is None` branch after `_prepare_tx()` gains "# Unreachable:
  _prepare_tx() returned False if the TX buffer were missing - kept to narrow the Optional for the type checker." and
  logs `_ERR_ALLOC`; faults pass `_ERR_UART_WRITE_FAILED`/`_ERR_UART_NO_ACK`/`_ERR_UART_PEER_INITIATED`; `:649` "Out of
  contract - there is no arbitration" → "Out of contract (owner, 2026-09-11) - there is no arbitration"; validation expects
  `_CMD_ACK`; `self._note_valid_frame()` (no `await`). `def _note_valid_frame(self) -> None:` / `if self._valid_frames <
  COUNTER_CAP: self._valid_frames += 1` / `self._blind_resyncs = 0`; the four call sites drop `await`.
- **Resolved**: A.U3.02 removes the only `await` in `_note_valid_frame()`; left `async`, every validated frame would
  allocate a coroutine object for nothing (a per-frame same-shaped allocation, G4/R42; J.9 "never per frame") — made
  synchronous (agent, adherence finding; OR2.c list). No wire effect.
- **Unit**: U35 (A.U35.47's comment). Staged: U0 (tag), U2 (names), U3 (call out, sync), U10 (saturation, `_CMD_ACK`).
- **Depends**: M.SRC_NET.150 (`COUNTER_CAP`), M.SRC_NET.151, M.SRC_NET.153, M.SRC_NET.158
- **Blast carried by**: tests (`_valid_frames` at `COUNTER_CAP` stays) → A.U10.04 (TEST_UNIT); SPEC E.5.1 names the kept
  narrowings once → A.U35.41 (SPEC); UART changelog Class B `_valid_frames` saturation → A.U10.04; the synchronous
  `_note_valid_frame()` has no constituent entry → Gaps (DOCS)
- **Kind**: code

### M.SRC_NET.165 Callback dispatch: coded suppressions, fatal report, sorted excepts
- **From**: A.U28.30 (3) (`:675` reason, `:687-690` reason line above `:686`), A.U30.19 (`report_if_fatal(e)`), A.U2.20
  (`_ERR_CALLBACK`), A.U10.45 (`(IndexError, TypeError)`)
- **Site**: `src/asy_uart_comm.py:665-693` (`_call()`, `_pair()`)
- **Change**: `_call()`: `result = await result  # type: ignore[misc]  # awaitable: `send` checked above`; `except
  Exception as e:  # caller-supplied code; its runtime behaviour is not statically known` → first statement
  `report_if_fatal(e)`, then `await self._err(_ERR_CALLBACK, "callback raised:", e)`. `_pair()`: one comment line above
  the `try:` "# An arbitrary callback's result: `len()`/indexing are tried, and TypeError/IndexError below is the real
  check." ; the three ignores keep their codes; `except (IndexError, TypeError):`.
- **Resolved**: —
- **Unit**: U30. Staged: U2, U10 (except order), U28 (reasons).
- **Depends**: M.SRC_NET.150, A.U30.19 (SRC_CORE)
- **Blast carried by**: `tests_scripts/test_suppression_form.py` → A.U28.30 (SCR); `test_fatal_report_sites.py` → A.U30.19
  (SCR); UART changelog Class B "every broad handler records a C-stack overflow" → A.U30.19, "except-tuple order" →
  A.U10.45 (DOCS)
- **Kind**: code

### M.SRC_NET.166 Train send/receive: names and stated narrowings
- **From**: A.U35.47 (`:757-761`, `:774-776`), A.U2.20 (`_ERR_UART_PAYLOAD_TOO_LARGE`, `_ERR_ALLOC`, `_ERR_CALLBACK`,
  `_ERR_UART_STREAM_SHORT`, `_ERR_TIMEOUT`, `_ERR_UART_SIZE_MISMATCH`, `_ERR_UART_WRITE_FAILED`), A.U10.31 (unquote where
  no `TYPE_CHECKING` name)
- **Site**: `src/asy_uart_comm.py:699-804` (`_send_train()`, `_pull_chunk()`, `_recv_train()`, `_dest_size()`)
- **Change**: codes renamed at every `_err`/`_fault`; `_recv_train()`'s `if err or rx is None:` gains "# Unreachable:
  `_read_frame()` already failed on a missing RX buffer - kept to narrow the Optional for the type checker."; the
  destination bound `:774-776` gains "# Unreachable: `_dest_size()` sized the destination to the train's bound before the
  first ACK - kept to narrow the type for the type checker." (≤ 1 line each, replacing no existing comment); `_note_valid_frame()`
  called without `await` (M.SRC_NET.164). `_dest_size()` unchanged (its `(chunks - 1) × payload_size` bound is what
  J.8's corrected text states, A.U17.03).
- **Resolved**: —
- **Unit**: U35. Staged: U2 (names), U3 (sync call).
- **Depends**: M.SRC_NET.153, M.SRC_NET.164
- **Blast carried by**: SPEC E.5.1 → A.U35.41; SPEC J.8 → A.U17.03 (SPEC); BACKLOG owner question 1 names
  `_get_unlocked()` and `_accept_set()` → A.U0.12/A.U17.03 (DOCS)
- **Kind**: code

### M.SRC_NET.167 Initiator entry points: gate first, then argument checks
- **From**: A.U17.01, A.U0.49 (`:836-837`), A.U35.47 (`:865-866`), A.U16.05 (`:878` comment), A.U2.20 (`_ERR_DEST_ALLOC` →
  `_ERR_ALLOC`, `_ERR_UART_SIZE_MISMATCH`), A.U10.29 (`_CMD_GET` in `_get_unlocked()`), A.U10.31
- **Site**: `src/asy_uart_comm.py:808-975` (`uart_set()`, `uart_set_into()`, `uart_set_stream()`, `uart_get()`,
  `uart_get_into()`, `uart_get_stream()`, `_run_get()`, `_get_unlocked()`, `_read_answer_header()`)
- **Change**: order for every public initiator form: `_gate(ROLE_INITIATOR)` → `_check_cmd_id` → buffer/callback →
  size → `bus is None` → `_busy`/lock. `uart_set_stream()`: comment → "# A declared total is required up front: every frame
  carries the train's CHUNKS, chunk 1 included (Part J.3), so a genuinely unknown length cannot be sent."; the `pull is
  None` refusal (`_ERR_BAD_ARG`, comment kept) moves above `_check_size(total_size, allow_none=False)`, the `bus is None`
  check below both. `uart_get()`: `if not await self._gate(ROLE_INITIATOR): return None` / `if not await
  self._check_cmd_id(get_id): return None` / `result = await self._run_get(get_id, exp_size)`; its `own is None` branch
  gains "# Unreachable: …" per A.U35.47 wording for this site ("`_run_get()` returns a buffer whenever neither dest nor push
  was given") - kept to narrow the Optional for the type checker; right-size failure → `_ERR_ALLOC`. `uart_get_into()`:
  gate, id, then `buf is None` (`_ERR_ALLOC`, comment `:878` "A failed RegionBuffer hands its owner None, …"), then
  `_check_buffer(buf, writable=True)`, then `_run_get(...)`. `uart_get_stream()`: gate, id, `push is None`
  (`_ERR_BAD_ARG`, comment kept), `_run_get(...)`. `_run_get()`: one comment line above it "# Shared tail of the three GET
  forms: each gates, then checks its own arguments, first."; its body keeps only `_check_size(exp_size, allow_none=True)`,
  bus, busy, lock. `_get_unlocked()`: `_CMD_GET`, allocation failure → `_ERR_ALLOC`; `_read_answer_header()`: codes
  renamed, `self._note_valid_frame()` without `await`. No awaited call that can suspend on a success path sits between
  `_gate()`'s `_busy` test and `self._busy = True` (kept).
- **Resolved**: A.U35.47's sixth site (`:865-866`) is the `own is None` narrowing in `uart_get()`; its wording follows
  A.U35.47's form.
- **Unit**: U35. Staged: U0 (comment), U2 (names), U10 (`_CMD_GET`), U16 (comment), U17 (order).
- **Depends**: M.SRC_NET.153, M.SRC_NET.164
- **Blast carried by**: `UARTLinkDriver._exercise_loop()` (valid arguments, unchanged); tests (gate-first before setup,
  role refusal first on a responder, command-id first on an initiator) → A.U17.01 (TEST_UNIT); SPEC J.9 order sentence →
  A.U17.01 (SPEC); UART changelog Class B (check order) → A.U17.01 (DOCS)
- **Kind**: code

### M.SRC_NET.168 Responder path: private callbacks, codes, stated narrowing
- **From**: A.U35.47 (`:999-1001`), A.U10.35 (+ adherence `_set_callback`), A.U2.20 (`_ERR_NO_CALLBACK` → `_ERR_BAD_ARG`;
  band names; `_ERR_DEST_ALLOC` → `_ERR_ALLOC`), A.U10.29 (`_CMD_GET`), A.U3.02 (declines via `_reject_wrn()`)
- **Site**: `src/asy_uart_comm.py:979-1080` (`uart_listen()`, `_listen_unlocked()`, `_answer_get()`, `_accept_set()`)
- **Change**: `uart_listen()`: `get_cb = self._get_callback if get_callback is None else get_callback`, `set_cb =
  self._set_callback if …`; missing → `_ERR_BAD_ARG`. `_listen_unlocked()`: `_ERR_TIMEOUT` for the listen read; the `rx is
  None` branch gains "# Unreachable: `_read_frame()` already failed on a missing RX buffer - kept to narrow the Optional
  for the type checker."; `exp = _CMD_GET if cmd == _CMD_GET else CMD_SET`; `self._note_valid_frame()` without `await`;
  `if cmd == _CMD_GET:`. `_answer_get()`/`_accept_set()`: `ListenResult(…, _CMD_GET, …)`, codes renamed, right-size and
  destination allocation failures → `_ERR_ALLOC`; everything else unchanged (the peer-sized allocation stays as J.8 and
  BACKLOG's owner question 1 state, A.U17.03/A.U0.12).
- **Resolved**: —
- **Unit**: U35. Staged: U2, U3, U10.
- **Depends**: M.SRC_NET.151, M.SRC_NET.153, M.SRC_NET.155, M.SRC_NET.163, M.SRC_NET.164
- **Blast carried by**: SPEC E.5.1 → A.U35.41; BACKLOG owner question 1 (both allocation sites) → A.U0.12 (DOCS)
- **Kind**: code

### M.SRC_NET.169 `setup()`: the discard baseline, no episode reset
- **From**: A.U17.13 (`_discarded_seen` after the boot drain), A.U3.02 (`_clear_fault_state()` goes), A.U2.20
  (`_ERR_UART_NO_BUS`), A.U10.21 (read: already `-> bool`, `pr.setup()` first, refusal persisted), A.U10.22 (read:
  `initialized` False → True present)
- **Site**: `src/asy_uart_comm.py:1084-1106`
- **Change**: after the boot drain block: `self._discarded_seen = bus.discarded_bytes  # a pre-setup discard is not this
  link's evidence`; the `self._clear_fault_state()` line and its comment go; the rest unchanged.
- **Resolved**: —
- **Unit**: U17. Staged: U2, U3.
- **Depends**: M.SRC_NET.162, M.SRC_NET.192 (`discarded_bytes`)
- **Blast carried by**: A.U10.22's readiness check passes for `UARTComm` (TSC); tests → A.U17.13 (TEST_UNIT)
- **Kind**: code

### M.SRC_NET.170 Listen loop: a validated command resets the backoff; named starter; fatal report; typed lists
- **From**: A.U17.17 (`result.cmd`), A.U30.19, A.U2.20 (`_ERR_UNEXPECTED`), A.U10.44 (`start_asy_listen()` over
  `_listen_loop`), A.U32.06 (3) (named starter method), A.U17.26 (`list[TaskStarter]`, `list[TimerStarter]`), A.U10.35
  (`_message_callback`)
- **Site**: `src/asy_uart_comm.py:1108-1136`
- **Change**: `_listen_loop()`: `if result.cmd is not None:` / `if result.cmd_id is not None and self._message_callback is
  not None:` the guarded `_call(...)` (comment kept) / `backoff = self._backoff_initial_ms` / `continue`; comment above the
  test (≤ 3 lines): "# After any transaction whose command frame validated and was then answered, declined or aborted
  mid-train (ListenResult.cmd set), re-listen at once, so the backoff never outlasts the initiator's retry (J.5); a listen
  that returns no command kind backs off. No spin: the next listen parks on its read." `except Exception as e:` (trailing
  comment kept) → `report_if_fatal(e)` then `await self._err(_ERR_UNEXPECTED, "listen loop caught:", e)`. New `def
  start_asy_listen(self) -> "asyncio.Task[None]": return asyncio.get_event_loop().create_task(self._listen_loop())`;
  `get_task_starters(self) -> "list[TaskStarter]"`: `return []` for an initiator (comment kept), else
  `[self.start_asy_listen]`; `get_timer_starters(self) -> "list[TimerStarter]"`.
- **Resolved**: A.U32.06 names the starter `start_listen`; A.U10.44's scheme (U10, the naming rule G10/R16) names it
  `start_asy_listen` and lands first — A.U32.06's need (a named method, so no task name reads `<lambda>`) is met by it,
  and `LastTaskEnd` shows `UART_resp.start_asy_listen` (agent decision, OR2.c list).
- **Unit**: U30 (A.U30.19). Staged: U2, U10 (starter, names), U17 (backoff rule, types); A.U32.06 adds nothing further
  here.
- **Depends**: M.SRC_NET.150, M.SRC_NET.155, A.U10.46 (aliases)
- **Blast carried by**: `UARTLinkDriver.get_task_starters()` → M.SRC_NET.215; generated `_collect_task_names()` reads
  `__name__` → A.U32.06 (GEN); tests (declined-then-answered GET without backoff; dead link still doubles; starters called
  by name) → A.U17.17, A.U10.44 (TEST_UNIT); SPEC J.5 sentence → A.U17.17 (SPEC); UART changelog **Class A** A14 (responder
  re-listens at once after a validated command) → A.U17.17, Class B (named starter; one entry for A.U10.44 and A.U32.06;
  fatal report) → A.U10.44, A.U30.19 (DOCS)
- **Kind**: code

### M.SRC_NET.171 Error counter reset returns the write's result and clears only what exists
- **From**: A.U11.31 (`-> bool`), A.U3.02 (`_clear_fault_state()` and the bitmap loop go)
- **Site**: `src/asy_uart_comm.py:1138-1149`
- **Change**: `async def reset_error_counter(self) -> bool:` comment → "# Clears the history and the link diagnostic's
  state behind it (valid-frame count, blind-resync streak)."; body `self._valid_frames = 0` / `self._blind_resyncs = 0` /
  `return await self.pr.reset()`. `get_error_counter()` unchanged.
- **Resolved**: —
- **Unit**: U11. Staged: U3.
- **Depends**: A.U11.31's `PrintLogHistory.reset() -> bool` (SRC_CORE)
- **Blast carried by**: `UARTLinkDriver.reset_error_counter()` → M.SRC_NET.216; `/status` `ResetErrors` → M.SRC_NET.123;
  UART changelog Class B (return type) → A.U11.31 (DOCS)
- **Kind**: code

### M.SRC_NET.172 Unquoted annotations (UART comm)
- **From**: A.U10.31
- **Site**: `src/asy_uart_comm.py` — the eight fully-quoted annotations naming no `TYPE_CHECKING` symbol (AST count, A.U10.31)
- **Change**: each unquoted (e.g. `_allocate()`'s tuple, `_pair()` `-> tuple[bool, object] | None`, `_run_get()`/
  `_get_unlocked()` returns, `_read_answer_header()`, `uart_get()` `-> bytearray | None`); annotations naming `UART`,
  `ErrorLog`, `LogConfig`, `Readable`, `Writable`, the callback Protocols or the aliases stay quoted.
- **Resolved**: —
- **Unit**: U10
- **Depends**: M.SRC_NET.150
- **Blast carried by**: A.U10.47's check (SCR)
- **Kind**: code

### M.SRC_NET.173 Member order per D.15 (UART comm)
- **From**: A.U10.33
- **Site**: `src/asy_uart_comm.py` class `UARTComm`, module functions, the `TYPE_CHECKING` Protocol classes
- **Change**: pure reorder by D.15's key (A.U10.32), AST-verified; members added later (`_max_timeout()`,
  `_take_discarded()`, `start_asy_listen()`) placed by the same key when written.
- **Resolved**: —
- **Unit**: U10 (last U10 edit)
- **Depends**: every U10 edit of the file
- **Blast carried by**: — (no changelog entry: the changelog does not record member order, A.U10.33)
- **Kind**: code

## src/asy_uart_driver.py

Below the protocol module: its changes reach the wire only where a constituent says so (none here does; each carries a
Class B line). Every new wait yields (`ready()`, `asyncio.sleep_ms()`), and every read stays clamped to `any()` (CLAUDE.md
UART rule; F.5.8 — F.8.2 after U36).

### M.SRC_NET.190 Module header and section pointers
- **From**: A.U10.37 (module names in the docstring), A.U36.532 (4) (F.5.7/F.5.8/F.5.9 → F.8.1/F.8.2/F.8.3 at `:121, :200,
  :266, :293` and in every comment the U13/U17 merges below write), A.SDEP.17 (W24/W25: the comments at `:198-200` and
  the F.5.8 mechanism sentences follow the source at the new MicroPython tag), A.U14.06 (read: the never-raise surface is
  already stated, DONE-AT-HEAD)
- **Site**: `src/asy_uart_driver.py:1-6`; `:119-121`, `:198-200`, `:264-266`, `:291-293` and the new comments of
  M.SRC_NET.195/.199/.203
- **Change**: docstring "lock-scoped via base_classes.Lockable" → "lock-scoped via asy_base_classes.Lockable"; "(crc_checks.py)"
  → "(asy_crc_checks.py)", "(framing_codecs.py)" → "(asy_framing_codecs.py)"; the pin comment `:4-5` unchanged (it agrees
  with RP2040 Table 279, A.U20.09). At U36 every "F.5.7" → "F.8.1", "F.5.8" → "F.8.2", "F.5.9" → "F.8.3" in the file. At
  the MicroPython bump (A.SDEP.17): if `machine.UART.deinit()` no longer leaves the ring unrooted (W24), the `init()`
  comment `:198-200` says the fresh construction is kept but no longer load-bearing; if `read()` no longer waits per
  missing byte (W25), the `_buffered()`/`ready()` mechanism sentences follow the source — the clamp and the yield stay
  either way (owner's no-block rule).
- **Resolved**: —
- **Unit**: U36 (A.U36.532). Staged: U10 (module names), the SDEP bump (conditional comment rewrite, only if the
  re-read source changed).
- **Depends**: A.U14.28 (F.7 exists), the SPEC move (A.U36.532, SPEC)
- **Blast carried by**: every other F.5.7-F.5.9 citer → A.U36.532 (SPEC, TEST_UNIT, TWIN, HW_*); changelog `:95` pointer →
  A.U36.532 (DOCS)
- **Kind**: code

### M.SRC_NET.191 Imports and module constants
- **From**: A.U10.37/A.U10.38 (`asy_base_classes`, `asy_crc_checks.CRCBase/CRCPass`, `asy_framing_codecs.FramingBase/
  FramingPass`), A.U10.01 + A.U17.13 + A.U17.28 (`COUNTER_CAP` import), A.U17.28 (`_SEQ_HALF`), A.U8.06 (tags
  `:33`, `:38`)
- **Site**: `src/asy_uart_driver.py:8-38`
- **Change**: `from asy_base_classes import COUNTER_CAP, Lockable` / `from asy_crc_checks import CRCBase, CRCPass` / `from
  asy_framing_codecs import FramingBase, FramingPass`; `_CANCEL_ACK_TIMEOUT_MS = const(1000)  # @tunable
  uart.cancel_ack_timeout_ms = 1000` and `_DELIMITED_YIELD_BYTES = const(16)  # @tunable uart.delimited_yield_bytes = 16`
  (their comments kept); new `_SEQ_HALF = const(0x20000000)  # half the 2**30 sequence space: a distance below it is "behind"`.
- **Resolved**: —
- **Unit**: U17. Staged: U8 (tags), U10 (names, `COUNTER_CAP`), U17 (`_SEQ_HALF`).
- **Depends**: A.U10.01 (SRC_CORE), A.U10.37/38
- **Blast carried by**: Part N rows → A.U8.06 (DOCS); UART changelog Class B for the renames → A.U10.37 (DOCS)
- **Kind**: code

### M.SRC_NET.192 `UART.__init__`/`init()`: measured poll defaults, tagged buffer sizes, kept `txbuf`, a discard count
- **From**: A.U13.17 (`poll_wait_ms = 2`, `poll_idle_ms: int = 50`), A.U8.06 (tags: rxbuf/txbuf ×2 sites, poll default;
  `uart.poll_idle_ms_default` row per A.U13.17), A.U13.13 (`self.txbuf`), A.U17.13 (`discarded_bytes`), A.U17.28 (the
  counter comment), A.U36.544 (3) (`:79` "changelog A11"), A.U10.38 (codec class names), A.U10.31, A.U5.17 (read: the
  12 + 4 parameters keep a per-file PLR0913 exemption)
- **Site**: `src/asy_uart_driver.py:41-82`, `:183-222`
- **Change**: `poll_wait_ms: int = 2,  # @tunable uart.poll_wait_ms_default = 2`, `poll_idle_ms: int = 50,  # @tunable
  uart.poll_idle_ms_default = 50`, `rxbuf: int = 256,  # @tunable uart.rxbuf_default = 256`, `txbuf: int = 256,  #
  @tunable uart.txbuf_default = 256` (the two buffer tags at both `__init__` and `init()`); `crc: CRCBase | None`,
  `framing: FramingBase | None`; `self.poll_idle_ms = poll_idle_ms`, its comment `:65-67` keeping its first two sentences
  (the "None keeps the single rate" sentence goes); the cancel comment `:69-71` → "# A cancel request is latched and
  acknowledged by publishing the request number it served: two sequences rather than an Event, masked to COUNTER_CAP and
  compared by distance, so one acknowledgement stays visible to every waiting canceller."; `self.discarded_bytes = 0  #
  Bytes a failed *_until_complete() read consumed and dropped: a wrap-by-design count (masked to COUNTER_CAP) a caller
  compares, never a total` (comment on the line above if the line would exceed the cap); `CRCPass()`/`FramingPass()`
  defaults; `:79` "…selecting a delimited one is a wire change (changelog A11)." → "…is a coordinated flag day with the C
  peer (Part J)."; `init()` keeps `self._txbuf = txbuf` beside `rxbuf`/`baudrate` (comment `:202-204` names all three); `self.cancel` →
  `self._cancel` (`:72`, `:99-100`, `:249`, `:275`). Both private (gap pass G2: no reader outside the class in `src/` or the generated code — G10/R07 "private by default", M_SRC_CORE GAP-G12; every use in the file follows); `rxbuf`, `baudrate`, `poll_*_ms`,
  `crc`, `framing`, `poller`, `cancel_unacknowledged` and `discarded_bytes` stay public (`UARTComm` and the poller swap
  read them).
- **Resolved**: A.U8.06 tags `poll_wait_ms_default = 20` at HEAD's literal; A.U13.17 changes the literal to 2 and adds the
  idle row — the tag moves with the value (A.U8.06's own Depends).
- **Unit**: U36 (the label). Staged: U8 (tags at HEAD values), U10 (names), U13 (defaults, `txbuf`), U17 (count, comment).
- **Depends**: M.SRC_NET.191
- **Blast carried by**: `buildgen/validate.py:246-251` `poll_idle_ms` special case goes → A.U13.17 (GEN); tests built by
  `make_uart()` re-checked for timing, harness `poll_idle_ms=POLL_WAIT_MS`, `test_buildgen_validate.py:1290-1310` →
  A.U13.17 (TEST_UNIT, TEST_HELP, SCR); fakes gain `txdone()` → A.U13.13 (TEST_HELP, TWIN); SPEC J.6/F.5.9/C.3.2,
  `devices/dev.toml:39-40` comment → A.U13.17, A.U17.13 (SPEC, GEN); `pyproject.toml` PLR0913 per-file entry and the
  ceiling probe's exempt set → A.U5.17/A.U5.18 (TOOL); UART changelog Class B (defaults; discard count) → A.U13.17,
  A.U17.13 (DOCS)
- **Kind**: code

### M.SRC_NET.193 Session lock name
- **From**: A.U10.18 (`Lockable.asy_lock` → `session_lock`)
- **Site**: `src/asy_uart_driver.py:109-115` `_active_uart()`, `:245` `cancel_read_timeout()`
- **Change**: `self.asy_lock.locked()` → `self.session_lock.locked()` at both sites; the `:111-112` comment names
  `session_lock`.
- **Resolved**: —
- **Unit**: U10
- **Depends**: A.U10.18 in `asy_base_classes` (SRC_CORE)
- **Blast carried by**: `tests/test_asy_uart_driver.py` (9 sites) → A.U10.18 (TEST_UNIT); UART changelog Class B →
  A.U10.18 (DOCS)
- **Kind**: code

### M.SRC_NET.194 Sorted except tuples (driver)
- **From**: A.U10.45
- **Site**: `src/asy_uart_driver.py:124` (`_buffered()`), `:234` (`deinit()`)
- **Change**: `except (OSError, MemoryError):` → `except (MemoryError, OSError):` at both (the trailing comment at
  `:124` kept); `ready()`'s tuple is written sorted by M.SRC_NET.199.
- **Resolved**: —
- **Unit**: U10
- **Depends**: —
- **Blast carried by**: UART changelog Class B → A.U10.45 (DOCS)
- **Kind**: code

### M.SRC_NET.195 `_write_all()` writes only into an empty TX ring, at most `txbuf` bytes
- **From**: A.U13.13
- **Site**: `src/asy_uart_driver.py:127-141`
- **Change**: comment → "# Write only into an empty TX ring, at most txbuf bytes: POLLOUT means one free byte, and a
  longer write waits per byte inside machine.UART.write() (F.8.2)." plus HEAD's short-write sentence; per round: `if not
  await self.ready(select.POLLOUT): return False` / `if not uart.txdone(): await asyncio.sleep_ms(self.poll_wait_ms);
  continue` / `chunk = min(total - sent, self._txbuf)` / `n = uart.write(view if sent == 0 and chunk == total else
  view[sent : sent + chunk])` / `None` → `False` / `sent += n`.
- **Resolved**: —
- **Unit**: U13 (F.5.8 written until U36's repoint, M.SRC_NET.190)
- **Depends**: M.SRC_NET.192 (`self._txbuf`)
- **Blast carried by**: fakes' `txdone()`/`tx_pending_rounds` → A.U13.13 (TEST_HELP, TWIN); tests (3 × txbuf in three
  writes, no write while not done, cancel mid-wait) → A.U13.13 (TEST_UNIT); SPEC F.5.8 write half → A.U14 (RF192, SPEC);
  UART changelog Class B → A.U13.13 (DOCS)
- **Kind**: code

### M.SRC_NET.196 `_read_delimited()`: every consumed byte counts toward the yield and toward the discard count
- **From**: A.U13.14 (`consumed`), A.U13.18 (poller re-check after the yield), A.U17.13 (`_count_discarded()` on every
  `None` after consumed bytes), A.U17.22 (read: `decode_from()`'s bound is the codec's)
- **Site**: `src/asy_uart_driver.py:143-181`; new `_count_discarded()`
- **Change**: `consumed = 0` beside `size`; after a byte is obtained (`timeout = timeout_ms`): `consumed += 1` / `if not
  consumed % _DELIMITED_YIELD_BYTES:` `await asyncio.sleep_ms(0)` / `if self.poller is None: self._count_discarded(consumed);
  return None`; the data branch's own yield (`:168-169`) and its comment go. Every `None` return after bytes were consumed
  calls `self._count_discarded(consumed)` first: the bound, the mid-frame `ready()` failure, the decode `None` and the
  CRC `None` (the result of `check_from()` is held, counted on `None`, then returned). New `def _count_discarded(self, n:
  int) -> None:` — `if n > 0: d = self.discarded_bytes; self.discarded_bytes = d + n if d <= COUNTER_CAP - n else d -
  (COUNTER_CAP - n) - 1` with "# masked to COUNTER_CAP by a conditional wrap, never add-then-mask".
- **Resolved**: A.U17.13's helper uses the conditional wrap AC_NOTES 17 requires (no add-then-mask).
- **Unit**: U17. Staged: U13 (yield, re-check).
- **Depends**: M.SRC_NET.191, M.SRC_NET.192
- **Blast carried by**: tests (64 delimiters let a counter task run; deinit during the yield; discard counts on decode/CRC
  failure) → A.U13.14, A.U13.18, A.U17.13 (TEST_UNIT); UART changelog Class B → A.U13.14, A.U13.18, A.U17.13 (DOCS)
- **Kind**: code

### M.SRC_NET.197 Cancel sequences wrap without allocating
- **From**: A.U17.28, A.U10.18 (lock name, M.SRC_NET.193)
- **Site**: `src/asy_uart_driver.py:241-256` `cancel_read_timeout()`
- **Change**: `self._cancel_req = self._cancel_req + 1 if self._cancel_req < COUNTER_CAP else 0`; `while 0 < ((my_req -
  self._cancel_ack) & COUNTER_CAP) < _SEQ_HALF:`; `self.cancel_unacknowledged = self.cancel_unacknowledged + 1 if
  self.cancel_unacknowledged < COUNTER_CAP else 0  # a wedged holder; the request stays latched`; comment (≤ 3 lines)
  "# Wrap-by-design sequences stepped by a conditional wrap, never `+ 1` then masked, so no intermediate leaves the
  small-int range; compared by distance or equality only."
- **Resolved**: —
- **Unit**: U17
- **Depends**: M.SRC_NET.191, M.SRC_NET.193
- **Blast carried by**: `UARTComm.clear()`'s `!=` report holds (M.SRC_NET.153 names); tests at `COUNTER_CAP` →
  A.U17.28 (TEST_UNIT); SPEC C.3.2 handshake wording → A.U17.28 (SPEC); A.U10.05's table → (SCR); UART changelog Class B
  → A.U17.28 (DOCS)
- **Kind**: code

### M.SRC_NET.199 `ready()`: re-check after the closing yield; an out-of-range wait degrades to `False`
- **From**: A.U13.18, A.U13.19, A.U10.45
- **Site**: `src/asy_uart_driver.py:258-295`
- **Change**: `except (MemoryError, OSError, OverflowError, TypeError):` with the comment's two HEAD lines plus "#
  OverflowError: a wait beyond the ticks range - asyncio.sleep_ms() raises it for a delta >= 2**29 ms." (the block stays
  ≤ 3 lines: the HEAD pair is folded to one line "# TypeError: a malformed mask/timeout_ms; callers' excepts wrap only the
  UART call."); the closing lines → `await asyncio.sleep_ms(0)` / `return self.poller is not None` with "# A deinit()
  during the yield must not hand the caller a dead UART (its RX ring is unrooted, F.8.1)." (the yield comment `:291-293`
  kept above).
- **Resolved**: —
- **Unit**: U13 (F.5.7 written until U36, M.SRC_NET.190). Staged: U10 (order).
- **Depends**: —
- **Blast carried by**: tests (deinit during the yield → `None`/`False`; `poll_idle_ms = 2**29` with a bounded
  `_StepPoller` → `False`) → A.U13.18, A.U13.19 (TEST_UNIT); SPEC C.3.2, F.5.9 → (SPEC); UART changelog Class B →
  A.U13.18 (DOCS)
- **Kind**: code

### M.SRC_NET.200 `read_until_complete()`: nothing to read for no bytes; discarded bytes counted
- **From**: A.U12.03, A.U17.13, A.U35.41 (read: the `msg += add` `MemoryError` arm is kept and registered untestable in
  E.5.1; the `check()` arm stays, exercised through a double)
- **Site**: `src/asy_uart_driver.py:306-345`
- **Change**: after `if uart is None: return None`: `if nbytes <= 0: return bytearray()`, before `nbytes +=
  self.crc.length()`. Delimited branch: `_read_delimited()` counts its own discards. Counted branch: every `None` return
  after bytes arrived calls `self._count_discarded(len(msg))` first — `add is None`, the `MemoryError` arm, the mid-frame
  `ready()` failure (`len(msg)` is 0 on a start timeout, adding nothing) and a `crc.check()` result of `None` or its
  `MemoryError` arm (the whole frame).
- **Resolved**: —
- **Unit**: U17. Staged: U12 (zero-length).
- **Depends**: M.SRC_NET.196 (`_count_discarded()`)
- **Blast carried by**: tests (`crc=CRC16()` zero-length; discard counts) → A.U12.03, A.U17.13 (TEST_UNIT); SPEC E.5.1
  line → A.U35.41 (SPEC); UART changelog Class B → A.U12.03, A.U17.13 (DOCS)
- **Kind**: code

### M.SRC_NET.201 `readinto_until_complete()`: same two rules
- **From**: A.U12.03, A.U17.13
- **Site**: `src/asy_uart_driver.py:356-387`
- **Change**: `if nbytes <= 0: return 0` after the bus guard, before `nbytes += self.crc.length()`; counted branch: `nb is
  None` and the mid-frame `ready()` failure call `self._count_discarded(size)` before `return None`; the final
  `checked = await self.crc.check_from(buf, size=size)` / `if checked is None: self._count_discarded(size)` / `return
  checked`.
- **Resolved**: —
- **Unit**: U17. Staged: U12.
- **Depends**: M.SRC_NET.196
- **Blast carried by**: as M.SRC_NET.200; `UARTComm._read_frame()` reads through it (M.SRC_NET.162 takes the count)
- **Kind**: code

### M.SRC_NET.202 Readline paths clamped to `any()`; the growth comment names the owner question
- **From**: A.U13.12, A.U17.31
- **Site**: `src/asy_uart_driver.py:389-424`
- **Change**: `readline()`: comment "# Clamped like every counted read: readline() reads byte by byte, each missing byte a
  blocking wait (F.8.2)."; `want = self._buffered(uart, self.rxbuf)` / `return uart.readline(want) if want else None`.
  `readline_until_complete()`: `want = self._buffered(uart, self.rxbuf)` / `if not want: await
  asyncio.sleep_ms(self.poll_wait_ms); continue` / `add = uart.readline(want)`; `except MemoryError:  # grows across rounds
  without a bound; whether to cap or chunk it is an open owner question (BACKLOG.md)`.
- **Resolved**: —
- **Unit**: U17 (F.5.8 written until U36). Staged: U13.
- **Depends**: A.U0.12 (BACKLOG owner question 1)
- **Blast carried by**: fakes `readline(self, size=-1)` → A.U13.12 (TEST_HELP, TWIN); contract check → A.U13.12
  (TEST_HELP); L3 readline leg → A.U13.12/U26 (HW_DEV); UART changelog Class B (corrects B25) → A.U13.12 (DOCS)
- **Kind**: code

### M.SRC_NET.203 Writes send nothing for a zero-length payload
- **From**: A.U12.03
- **Site**: `src/asy_uart_driver.py:426-455`
- **Change**: `write()`: after the bus guard `if not msg: return True` with "# A zero-length payload is sent as nothing: a
  CRC-only frame could never be verified."; `writefrom()`: `if size < 0 or …` kept, then `if size == 0: return True`
  before `add_into()`.
- **Resolved**: —
- **Unit**: U12
- **Depends**: — (A.U12.02 in `asy_crc_checks` lands with or after it)
- **Blast carried by**: tests (`:1866-1870` flips; CRC16/CRC_Pass zero-length cases) → A.U12.03 (TEST_UNIT); SPEC C.3.2 →
  A.U12.03; UART changelog Class B → A.U12.03 (DOCS)
- **Kind**: code

### M.SRC_NET.204 Unquoted annotations (UART driver)
- **From**: A.U10.31
- **Site**: `src/asy_uart_driver.py` — the four fully-quoted annotations naming no `TYPE_CHECKING` name (`"_UART | None"`
  `:109`, `uart: "_UART"` `:118`, `:127`, `:144`)
- **Change**: unquoted (`_UART` is a runtime import); `"Literal[False]"` stays quoted.
- **Resolved**: —
- **Unit**: U10
- **Depends**: —
- **Blast carried by**: A.U10.47 check (SCR)
- **Kind**: code

### M.SRC_NET.205 Member order per D.15 (UART driver)
- **From**: A.U10.33
- **Site**: `src/asy_uart_driver.py` class `UART`
- **Change**: pure reorder by D.15's key, AST-verified; `_count_discarded()` placed by the key when written (U17).
- **Resolved**: —
- **Unit**: U10 (last U10 edit)
- **Depends**: every U10 edit of the file
- **Blast carried by**: —
- **Kind**: code

## src/asy_uart_link_driver.py

Bench application logic over one role's `UARTComm`; not the protocol module (its constituents log no changelog entry
except A.U24.67's banner and the renames).

### M.SRC_NET.210 Header and module comments
- **From**: A.U0.48 (`:4-5`), A.U10.38 (`UART_Comm` → `UARTComm` in docstring/comments)
- **Site**: `src/asy_uart_link_driver.py:1-5`, comment mentions `:62`, `:79`, `:134-136`, `:146-148`
- **Change**: docstring "wraps one role's `UARTComm`"; `:4-5` → "# Not a SensorReader/SensorReaderConfig subclass, like
  UARTComm (agent, 2026-09-11; Part J.9) -\n# resolved via buildgen.driver_registry._OVERRIDES."; every other comment names
  `UARTComm`.
- **Resolved**: —
- **Unit**: U10. Staged: U0 (`:4-5` with the HEAD class name).
- **Depends**: —
- **Blast carried by**: SPEC J.9 → A.U0.44 (SPEC)
- **Kind**: code

### M.SRC_NET.211 Imports, wiring tag and typing
- **From**: A.U10.37/A.U10.38, A.U5.12 (`ResponderCallbacks`), A.U5.02 (`DEFAULT_LOG`, `LogConfig`; FRAM-manager import
  goes), A.U5.03 (wiring tag), A.U17.26 (`Any`, `Callable`, `_asyncio` go; aliases), A.U17.29 (`COUNTER_CAP`)
- **Site**: `src/asy_uart_link_driver.py:7-29`
- **Change**: runtime: `import asyncio` / `from micropython import const` / `from asy_base_classes import COUNTER_CAP` /
  `from asy_config_manager import instance_name` / `from asy_print_log import DEFAULT_LOG` / `from asy_uart_comm import
  CMD_SET, ROLE_INITIATOR, ROLE_RESPONDER, ResponderCallbacks, UARTComm`. `TYPE_CHECKING`: `from asy_base_classes import
  ErrorSource, JsonDict, TaskStarter, TimerStarter`, `from asy_print_log import ErrorLog, LogConfig, PrintLogHistory`,
  `from asy_uart_driver import UART`. `:29` → `# @wiring fram_target FRAMManager log optional kwarg`.
- **Resolved**: —
- **Unit**: U17. Staged: U5 (log, tag), U10 (names), U17 (aliases, `COUNTER_CAP`).
- **Depends**: A.U10.46 (aliases), A.U5.01
- **Blast carried by**: generated construction → A.U5.03 (GEN); A.U8.24 baseline loses the file → A.U17.26 (TOOL)
- **Kind**: code

### M.SRC_NET.212 The bench banner names its mechanism and is folded
- **From**: A.U24.67 (1) (value), A.U10.29 (`const()`), A.U8.06 (`_EXERCISE_PERIOD_MS` tag)
- **Site**: `src/asy_uart_link_driver.py:34-40`
- **Change**: `_BANNER = const(b"uart-crossover")`; `_EXERCISE_PERIOD_MS = const(1000)  # @tunable uart.exercise_period_ms
  = 1000` (comment kept).
- **Resolved**: A.U24.67 (U24) wants the test to import `asy_uart_link_driver._BANNER` as "a plain global, not a
  `const()`"; A.U10.29 (U10, G4/R27 "every constant `const()` can fold is `_`-prefixed and `const()`-wrapped") folds it
  first, after which it cannot be imported (SPEC E.5.1) — the rule wins and the test reads it with `src_const(
  "src/asy_uart_link_driver.py", "_BANNER")` (A.U24.01's helper, which V.U24.45 noted needs exactly a `const()`). Agent
  decision, OR2.c list.
- **Unit**: U24. Staged: U8 (tag), U10 (`const()`).
- **Depends**: —
- **Blast carried by**: `tests/test_asy_uart_link_driver.py:189-195` reads `src_const(...)` → A.U24.67/A.U24.01
  (TEST_UNIT, see Gaps); twin test → U25; UART changelog Class B (banner renamed) → A.U24.67 (DOCS); Part N row →
  A.U8.06 (DOCS)
- **Kind**: code

### M.SRC_NET.213 `UARTLinkDriver.__init__`: log object, callbacks object, no test seam, private counters, readiness flag
- **From**: A.U10.38 (`UARTLinkDriver`), A.U5.02 (`(uart, role, payload_size, timeout, name_ext, log, logger)`), A.U5.12
  (one `ResponderCallbacks`), A.U17.18 (1) (`self.uart` and its comment go), A.U10.35 (`failures` → `_failures`);
  adherence additions: `transfers` → `_transfers` (G10/R07, read outside only by tests; D.10 with its pair) and
  `self.initialized` (A.U10.22's readiness rule)
- **Site**: `src/asy_uart_link_driver.py:43-83`
- **Change**: `class UARTLinkDriver:` / `def __init__(self, uart: "UART | None", role: str, payload_size: int = 48, timeout:
  int = 1000, name_ext: str = "", log: "LogConfig" = DEFAULT_LOG, logger: "PrintLogHistory | None" = None) -> None:`;
  `self._role = role` (gap pass G2: no reader outside the class in `src/` or the generated code — G10/R07 "private by default", M_SRC_CORE GAP-G12; every use in the file follows, M.SRC_NET.215); the `self.uart` line and `:58-60` go; `resolved_name = instance_name(_NAME, name_ext)`; comment
  `:62-64` → "# log=/logger= forwarded into UARTComm. The protocol carries no application semantics (Part J.1), but its
  history is real diagnostic state, so it gets the same optional-FRAM treatment as every module's logger."; `callbacks =
  ResponderCallbacks(self._get_callback, self._set_callback, self._message_callback) if role == ROLE_RESPONDER else None`;
  `self._comm = UARTComm(uart, role, payload_size=payload_size, timeout=timeout, callbacks=callbacks, name=resolved_name,
  log=log, logger=logger)`; `name`/`pr` as today; `self._last_echo` as today; `self._transfers = 0`, `self._failures = 0`;
  `self.initialized = False`.
- **Resolved**: A.U10.35's S09 list privatises `failures` but not `transfers`, though both are read outside the module
  only by `tests/test_asy_uart_link_driver.py` (grep at HEAD) — made private together (agent, adherence; OR2.c list). A.U10.22's
  L0 check requires every class with `async def setup` to set `initialized`; the wrapper had none (agent; OR2.c list).
- **Unit**: U17 (A.U17.18). Staged: U5 (signature, callbacks), U10 (class name, private names, flag).
- **Depends**: M.SRC_NET.154, M.SRC_NET.155, M.SRC_NET.211
- **Blast carried by**: twin `_wire_uart_crossover()` reads the generated buses, `buildgen/twin_wiring.py` plan shape →
  A.U17.18 (TWIN, GEN); generated construction `(…, log=…)` → A.U5.03 (GEN); tests (`transfers`/`failures` readers,
  constructor calls) → A.U5.02, A.U10.35 (TEST_UNIT, see Gaps for `_transfers`); `digital_twin/README.md:288-297`,
  `validate.py:542-544` comment → A.U17.18 (TWIN, GEN); UART changelog Class B names → A.U10.38 (DOCS)
- **Kind**: code

### M.SRC_NET.214 The exercise loop ends with its link and caps its counts
- **From**: A.U17.07, A.U17.29, A.U10.35 (names), A.U10.44 (read: `_exercise_loop` already fits the scheme)
- **Site**: `src/asy_uart_link_driver.py:110-120`
- **Change**: `while self.initialized:` (comment's second sentence gains "Ends, like the responder's listen loop, when
  setup() failed: the supervisor's restart escalation is the path to a reboot for a link that cannot come up (C.7.2)."
  — block ≤ 3 lines); success `if self._transfers < COUNTER_CAP: self._transfers += 1`; else `if self._failures <
  COUNTER_CAP: self._failures += 1`; the sleep unchanged.
- **Resolved**: A.U17.07 tests `self._comm.initialized`; with the wrapper's own flag set from its comm's `setup()`
  (M.SRC_NET.215) the two are equal — the loop reads the wrapper's (agent; OR2.c list).
- **Unit**: U17
- **Depends**: M.SRC_NET.213, M.SRC_NET.215
- **Blast carried by**: tests (refused construction ends every task within 200 ms; counts stop at the cap) → A.U17.07,
  A.U17.29 (TEST_UNIT); SPEC C.7.2 → A.U17.07 (SPEC)
- **Kind**: code

### M.SRC_NET.215 Status, setup and starters
- **From**: A.U17.26 (`-> JsonDict`, `list[TaskStarter]`, `list[TimerStarter]`), A.U10.44 (`start_asy_exercise()`),
  A.U32.06 (3) (named method), A.U0.28 (`:134-135` owner tag), A.U10.21 (read: already `-> bool`), A.U10.22 (flag)
- **Site**: `src/asy_uart_link_driver.py:122-143`
- **Change**: `async def get_link_status(self) -> "JsonDict": return {"Transfers": self._transfers, "Failures":
  self._failures}` (comment kept). `async def setup(self) -> bool:` / `if await self._comm.setup(): self.initialized =
  True` / `return self.initialized`. New `def start_asy_exercise(self) -> "asyncio.Task[None]": return
  asyncio.get_event_loop().create_task(self._exercise_loop())`; `get_task_starters(self) -> "list[TaskStarter]"`: comment
  `:134` "… has no arbitration in this protocol (Part J.2; owner, 2026-09-11)."; `starters = self._comm.get_task_starters()`
  / `if self._role == ROLE_INITIATOR: starters = starters + [self.start_asy_exercise]`. `get_timer_starters(self) ->
  "list[TimerStarter]"`.
- **Resolved**: A.U32.06's `start_exercise` vs A.U10.44's `start_asy_exercise` — as M.SRC_NET.170.
- **Unit**: U17. Staged: U0 (tag), U10 (starter, flag).
- **Depends**: M.SRC_NET.170, M.SRC_NET.213
- **Blast carried by**: generated maintenance callback `UARTLINK` (`codegen.py:630-634`) unchanged; `LastTaskEnd` names
  `UART_init.start_asy_exercise` → A.U32.06 (GEN); tests calling starters → A.U10.44 (TEST_UNIT)
- **Kind**: code

### M.SRC_NET.216 Error sources and a reset that leaves the transfer counts
- **From**: A.U17.19, A.U11.31 (`-> bool`), A.U17.26 (`list[ErrorSource]`)
- **Site**: `src/asy_uart_link_driver.py:145-160`
- **Change**: `get_error_sources(self) -> "list[ErrorSource]"` (comment names `UARTComm`); `get_loggers()` and
  `get_error_counter()` unchanged; `async def reset_error_counter(self) -> bool: return await
  self._comm.reset_error_counter()` (the two counter resets go).
- **Resolved**: —
- **Unit**: U17. Staged: U11 (return).
- **Depends**: M.SRC_NET.171
- **Blast carried by**: `/status` `ResetErrors` → M.SRC_NET.123; test `:133-140` inverts → A.U17.19 (TEST_UNIT); js mock
  check → A.U17.19 (WEB)
- **Kind**: code

### M.SRC_NET.219 Member order per D.15 (link driver)
- **From**: A.U10.33
- **Site**: `src/asy_uart_link_driver.py` class `UARTLinkDriver`
- **Change**: pure reorder by D.15's key, AST-verified; `start_asy_exercise()` placed by the key.
- **Resolved**: —
- **Unit**: U10 (last U10 edit)
- **Depends**: every U10 edit of the file
- **Blast carried by**: —
- **Kind**: code

## Gaps for other clusters

1. **Catalog (GEN, M.GEN.034)**: row 16 `CLOCK` loses its last site once `cettime()` stops catching (U18 register fix 10,
   M.SRC_NET.053) — retire it or name a site; row 69's text becomes "the reply was malformed or could not be parsed"
   (M.SRC_NET.049); WEBSERVER 48 renamed `HTTP_PEER_RESET` and rows 60-62 added (U19 A-C note 3, M.SRC_NET.112, checked
   collision-free); DNSSRV 42 → `DNS_RECV_FAILED`, 43 unassigned, the shared wrnno 11 `SOCKET_TEARDOWN` used by DNSSRV,
   the resolver and NTP (U18 register fix 9); WIFI uses shared 17 `TIMER`, NTP shared 10 and 21 (owner lists); UART
   `UART_POLL_RATE` = 91 and `UART_CODEC_SIZE` = 92 (M.SRC_NET.153 — the catalog entry says only "after the band's last
   used code").
2. **GEN**: the `IP`/`IPv4` generated status key that A.U18.33 deferred to A-C must match the snapshot field M.SRC_NET.074/
   .091 publish; `_collect_task_names()` (A.U32.06) reads `start_asy_listen`/`start_asy_exercise`; the twin wiring plan and
   generated `UARTLinkDriver(..., log=...)` follow M.SRC_NET.213.
3. **SCR**: A.U6.28's L0 check must resolve WiFi's `_RADIO_FIELDS = schema_names(...)` (M.SRC_NET.075); A.U10.05's counter
   exemption table must use the post-U10 private names and list `discarded_bytes` (masked) and `_blind_resyncs` (capped);
   A.U30.03's `_RUN_PHASE_ALLOWED` takes the renamed WiFi sites (`WifiService._connect_loop`, the LED-flash task,
   M.SRC_NET.092); A.U10.22's readiness check meets `WifiService`'s `setup()` override and `SensorReaderConfig`'s missing
   `initialized` (SRC_CORE) — `UARTLinkDriver` gains the flag here (M.SRC_NET.213/.215).
4. **SRC_CORE**: `_set_dict_cfg(data: JsonMapping)` implementers (U19 A-C note 2); `asy_api_response.handle_set_cmd()`'s
   envelope as M.SRC_NET.120 uses it; `report_if_fatal`, `COUNTER_CAP`, `RegionBuffer`, `TaskStarter`/`TimerStarter`/
   `ErrorSource`/`JsonDict`, `LogConfig`/`DEFAULT_LOG`, `session_lock` must exist before the stages that import them.
5. **TEST_UNIT / TEST_HELP**: A.U10.20's WiFi flash-top test premise is wrong — `_led_on()`/`_led_off()` absorb the LED's
   exceptions, so the test needs a raising `_led_on` double (M.SRC_NET.092); A.U24.45 (2) `led_pin` tests are void
   (A.U18.40); A.U14.34's UDP crossing tests lose their site after A.U10.26 (`wait_for_ms`, M.SRC_NET.028);
   `tests/test_asy_uart_link_driver.py:136-242` read `transfers` → `_transfers` (agent addition, M.SRC_NET.213, beyond
   A.U10.35's list); the banner test reads `src_const("src/asy_uart_link_driver.py", "_BANNER")` (M.SRC_NET.212);
   readers of `UARTComm.set_callback` (none at HEAD) follow `_set_callback`.
6. **DOCS (`UART_C_PORT_CHANGELOG.md`)**: no constituent carries a Class B line for `_note_valid_frame()` becoming
   synchronous (M.SRC_NET.164: "no wire effect; one coroutine allocation per validated frame removed"); A.U10.35's Class
   B entry must name `set_callback` with its two siblings (M.SRC_NET.155); A.U32.06's entry text names `start_listen`/
   `start_exercise` — one entry with A.U10.44's `start_asy_*` names.

## Adherence findings

- `src/asy_captive_dns.py`: SPDX header and licence file carry both licences (M.SRC_NET.002/.005); no breach left.
- `src/asy_dns_client.py`, `src/asy_udp_socket.py`: none beyond the merged changes (every wait yields; `getaddrinfo()`
  only on a numeric host, F.2 unchanged).
- `src/asy_ntp_client.py`: a stale "numbering starts at 11" comment survives the catalog (fixed in M.SRC_NET.040).
- `src/asy_wifi_service.py`: the same stale numbering comment (M.SRC_NET.070); the hotspot fallback password default is
  unchanged (accepted known credential, CLAUDE.md; only its comment points at A.11); the CYW43 power-cycle recovery is
  untouched (CLAUDE.md hard rule).
- `src/asy_webserver_service.py`: a "Step 7 audit" history comment (M.SRC_NET.129, G9/R12); every growable GET still
  streams through `_stream_dict_response()`; Microdot is only wrapped (`ext/` read, never edited); `SystemCmd` compares the
  whole string against the five words (OR117/OR121/OR122) and reboot/bootloader go through the callback's controlled
  sequence (OR126.a (3)); no `TCP_NODELAY` (OR114.a (2)).
- `src/asy_uart_comm.py`: `_drain()`'s comment still described the removed episode slot (M.SRC_NET.161);
  `_note_valid_frame()` left `async` with no `await` would allocate a coroutine per validated frame (M.SRC_NET.164);
  `set_callback` would stay the one public member of a private triple (M.SRC_NET.155). Contract checks: every change has
  its changelog line (gap 6 for the two agent additions); no loop-blocking wait added; CRC mode stays a TOML/constructor
  fact, no runtime switch and no negotiation (OR116/OR123, owner 2026-09-11); strictly initiator/responder.
- `src/asy_uart_driver.py`: the never-raise header holds for every poll value after M.SRC_NET.199; every read stays
  clamped to `any()` and every wait yields (readline included, M.SRC_NET.202).
- `src/asy_uart_link_driver.py`: `transfers` public beside a private `_failures` (M.SRC_NET.213); no readiness flag on a
  class with `async def setup` (M.SRC_NET.213/.215).

## Owner questions

None raised: every conflict in this cluster was settled by an owner row, the register, AC_NOTES or a verifier ruling,
or is an agent decision listed below.

## Agent decisions for the OR2.c review

1. Construction guards removed as unreachable (G5/R54) in `resolve_ipv4()` and `_fetch_ntp_reply()` (M.SRC_NET.023/.048).
2. `NtpTiming` defaults and the deleted `_NTP_CONN_TIMEOUT` (M.SRC_NET.042).
3. `host_label_ok()` lives in `asy_dns_client` beside `ipv4_to_int()` (M.SRC_NET.018).
4. Catalog row 69's text (M.SRC_NET.049).
5. The webserver gains `self.initialized` (M.SRC_NET.119); the `isinstance` narrowing it kept (U19 A-C note 1) is withdrawn
   in the gap pass — settled by the lead's L1 ruling, `handle_set_cmd()` returns `WriteValidity` (M.SRC_NET.120,
   M.SRC_CORE.072).
6. The captive-DNS backoff tag IDs are the `_ms` ones (M.SRC_NET.004).
7. A deactivated radio's snapshot reports not connected (M.SRC_NET.091).
8. UART codes numbered 91 `UART_POLL_RATE`, 92 `UART_CODEC_SIZE`; A.U3.08's "91" for e32 read as a slip (89) (M.SRC_NET.153).
9. `UARTComm.set_callback` and `UARTLinkDriver.transfers` made private with their siblings (M.SRC_NET.155/.213).
10. `_note_valid_frame()` made synchronous (M.SRC_NET.164).
11. Starter names `start_asy_listen`/`start_asy_exercise` (A.U10.44) satisfy A.U32.06 (M.SRC_NET.170/.215).
12. `_BANNER` stays `const()`; the test reads it with `src_const()` (M.SRC_NET.212).
13. `UARTLinkDriver` keeps its own `initialized`, which its exercise loop reads (M.SRC_NET.213-.215).
14. `_resync()` either persists W54 or prints the routine line, never both (M.SRC_NET.162).

Added by gap pass G2 (2026-10-01):

15. G10/R07 "private by default" across this cluster's classes (M_SRC_CORE GAP-G12): `DNSQuery._data`; NTP
    `_network_available_locked`, `_get_dns_server`, `_dns_timeout_ms`, `_dns_tries`, `_ntp_fetch_timeout_ms`, `_retry_s`,
    `_retry_max_s`; WiFi `_hotspot_time`, `_conn_fail_to_hotspot`; `UARTComm` `_uart`, `_role`, `_payload_size`,
    `_timeout`, `_uid`; `UART` `_cancel`, `_txbuf`; `UARTLinkDriver._role` (HEAD AST scan of public attributes, readers
    searched in `src/` and `buildgen/`; locks (R17), `initialized`, `name`/`pr` and setter/getter/starter methods left as
    they are).
16. `WifiService.setup()` and `WebserverService.setup()` return `bool` (A.U10.21's contract; M.SRC_NET.079/.119).

## Ledger

| action ID | merged into M-ID / dropped (reason) |
|---|---|
| A.C.13 | dropped (no site here: bench test (HW_BENCH); the body cap it proves is M.SRC_NET.118's) |
| A.S0930.01 | dropped (no site here: buildgen TOML key and checks (GEN); UARTComm stays CRC-agnostic, no runtime switch (OR116/OR123)) |
| A.S0930.07 | dropped (no site here: changelog Class B row (DOCS)) |
| A.S0930.08 | dropped (no site here: SPECIFICATION.md text (SPEC)) |
| A.S0930.09 | merged into M.SRC_NET.112, M.SRC_NET.121 |
| A.S0930.18 | merged into M.SRC_NET.128 |
| A.S0930.19 | dropped (no site here: wear-gate detector and README (SCR, HW_BENCH); `resetconfig` dispatch is M.SRC_NET.121) |
| A.S0930.20 | merged into M.SRC_NET.121 |
| A.S0930.21 | merged into M.SRC_NET.121 |
| A.S0930.31 | merged into M.SRC_NET.121 |
| A.S0930.33 | dropped (no site here: `SystemService` reset path (SRC_CORE)) |
| A.SDEP.06 | dropped (no site here: `ext/microdot.py` re-vendor (ext/ untouched by this cluster); webserver cites re-checked at execution, noted in the section intro) |
| A.SDEP.07 | dropped (no site here: `ext/freezefs` (TOOL)) |
| A.SDEP.08 | merged into M.SRC_NET.030 |
| A.SDEP.13 | merged into M.SRC_NET.132 |
| A.SDEP.15 | merged into M.SRC_NET.081 |
| A.SDEP.17 | merged into M.SRC_NET.190 |
| A.SDEP.18 | merged into M.SRC_NET.118, M.SRC_NET.124 |
| A.U0.12 | dropped (no site here: BACKLOG owner question 1 and SPEC:4870 (DOCS, SPEC); code comment is A.U17.31 → M.SRC_NET.202) |
| A.U0.19 | dropped (no site here: SPECIFICATION.md text (SPEC)) |
| A.U0.22 | dropped (no site here: repo docs (DOCS)) |
| A.U0.25 | dropped (no site here: SPECIFICATION.md text (SPEC)) |
| A.U0.28 | merged into M.SRC_NET.164, M.SRC_NET.215 |
| A.U0.29 | merged into M.SRC_NET.112, M.SRC_NET.113, M.SRC_NET.119, M.SRC_NET.127 |
| A.U0.30 | dropped (no site here: repo docs (DOCS)) |
| A.U0.35 | merged into M.SRC_NET.072, M.SRC_NET.078, M.SRC_NET.098 |
| A.U0.37 | merged into M.SRC_NET.044 |
| A.U0.48 | merged into M.SRC_NET.210 |
| A.U0.49 | merged into M.SRC_NET.167 |
| A.U1.01 | merged into M.SRC_NET.081, M.SRC_NET.083 |
| A.U1.03 | dropped (no site here: repo docs (DOCS)) |
| A.U1.18 | dropped (no site here: SPECIFICATION.md text (SPEC)) |
| A.U1.20 | merged into M.SRC_NET.005 |
| A.U10.01 | merged into M.SRC_NET.119, M.SRC_NET.127, M.SRC_NET.150, M.SRC_NET.191 |
| A.U10.R01 | merged into M.SRC_NET.100 |
| A.U10.03 | merged into M.SRC_NET.041, M.SRC_NET.044, M.SRC_NET.052, M.SRC_NET.054, M.SRC_NET.058, M.SRC_NET.071, M.SRC_NET.078, M.SRC_NET.082, M.SRC_NET.094, M.SRC_NET.098, M.SRC_NET.101 |
| A.U10.04 | merged into M.SRC_NET.150, M.SRC_NET.164 |
| A.U10.05 | dropped (no site here: L0 counter check (SCR); its exemption table must use the renamed private names (see Gaps)) |
| A.U10.06 | merged into M.SRC_NET.041, M.SRC_NET.047, M.SRC_NET.052, M.SRC_NET.053, M.SRC_NET.056, M.SRC_NET.071, M.SRC_NET.080, M.SRC_NET.091 |
| A.U10.10 | merged into M.SRC_NET.056, M.SRC_NET.079, M.SRC_NET.100, M.SRC_NET.119, M.SRC_NET.128 |
| A.U10.17 | merged into M.SRC_NET.026, M.SRC_NET.078 |
| A.U10.18 | merged into M.SRC_NET.044, M.SRC_NET.046, M.SRC_NET.050, M.SRC_NET.056, M.SRC_NET.081, M.SRC_NET.082, M.SRC_NET.085, M.SRC_NET.086, M.SRC_NET.088, M.SRC_NET.092, M.SRC_NET.098, M.SRC_NET.101, M.SRC_NET.193, M.SRC_NET.197 |
| A.U10.19 | dropped (no site here: L0/L1 checks (SCR, TEST_HELP); the src sites they read keep the shape these merges give them) |
| A.U10.20 | merged into M.SRC_NET.007, M.SRC_NET.077, M.SRC_NET.092 |
| A.U10.21 | merged into M.SRC_NET.169, M.SRC_NET.215 |
| A.U10.22 | merged into M.SRC_NET.118, M.SRC_NET.119, M.SRC_NET.169, M.SRC_NET.213, M.SRC_NET.215 |
| A.U10.25 | dropped (no site here: L0/L1 checks (SCR, TEST_HELP); the src sites they read keep the shape these merges give them) |
| A.U10.26 | merged into M.SRC_NET.028 |
| A.U10.27 | merged into M.SRC_NET.110, M.SRC_NET.114 |
| A.U10.29 | merged into M.SRC_NET.020, M.SRC_NET.042, M.SRC_NET.112, M.SRC_NET.151, M.SRC_NET.157, M.SRC_NET.159, M.SRC_NET.164, M.SRC_NET.167, M.SRC_NET.168, M.SRC_NET.212 |
| A.U10.31 | merged into M.SRC_NET.006, M.SRC_NET.050, M.SRC_NET.075, M.SRC_NET.111, M.SRC_NET.150, M.SRC_NET.155, M.SRC_NET.157, M.SRC_NET.166, M.SRC_NET.167, M.SRC_NET.172, M.SRC_NET.192, M.SRC_NET.204 |
| A.U10.33 | merged into M.SRC_NET.010, M.SRC_NET.019, M.SRC_NET.032, M.SRC_NET.059, M.SRC_NET.103, M.SRC_NET.131, M.SRC_NET.173, M.SRC_NET.205, M.SRC_NET.219 |
| A.U10.35 | merged into M.SRC_NET.006, M.SRC_NET.007, M.SRC_NET.026, M.SRC_NET.027, M.SRC_NET.030, M.SRC_NET.044, M.SRC_NET.051, M.SRC_NET.054, M.SRC_NET.055, M.SRC_NET.056, M.SRC_NET.057, M.SRC_NET.058, M.SRC_NET.078, M.SRC_NET.082, M.SRC_NET.083, M.SRC_NET.085, M.SRC_NET.086, M.SRC_NET.087, M.SRC_NET.088, M.SRC_NET.091, M.SRC_NET.093, M.SRC_NET.097, M.SRC_NET.098, M.SRC_NET.100, M.SRC_NET.155, M.SRC_NET.157, M.SRC_NET.164, M.SRC_NET.168, M.SRC_NET.170, M.SRC_NET.213, M.SRC_NET.214 |
| A.U10.36 | merged into M.SRC_NET.116, M.SRC_NET.120 |
| A.U10.37 | merged into M.SRC_NET.001, M.SRC_NET.004, M.SRC_NET.005, M.SRC_NET.006, M.SRC_NET.024, M.SRC_NET.040, M.SRC_NET.041, M.SRC_NET.070, M.SRC_NET.071, M.SRC_NET.076, M.SRC_NET.110, M.SRC_NET.150, M.SRC_NET.152, M.SRC_NET.190, M.SRC_NET.191, M.SRC_NET.211 |
| A.U10.38 | merged into M.SRC_NET.001, M.SRC_NET.003, M.SRC_NET.004, M.SRC_NET.006, M.SRC_NET.007, M.SRC_NET.020, M.SRC_NET.023, M.SRC_NET.024, M.SRC_NET.025, M.SRC_NET.026, M.SRC_NET.041, M.SRC_NET.043, M.SRC_NET.044, M.SRC_NET.048, M.SRC_NET.071, M.SRC_NET.076, M.SRC_NET.078, M.SRC_NET.086, M.SRC_NET.110, M.SRC_NET.111, M.SRC_NET.112, M.SRC_NET.155, M.SRC_NET.156, M.SRC_NET.191, M.SRC_NET.192, M.SRC_NET.210, M.SRC_NET.211, M.SRC_NET.213 |
| A.U10.39 | merged into M.SRC_NET.043, M.SRC_NET.044, M.SRC_NET.046, M.SRC_NET.057, M.SRC_NET.071, M.SRC_NET.072, M.SRC_NET.075, M.SRC_NET.077, M.SRC_NET.078, M.SRC_NET.080, M.SRC_NET.084, M.SRC_NET.086, M.SRC_NET.088, M.SRC_NET.096, M.SRC_NET.097 |
| A.U10.40 | merged into M.SRC_NET.043, M.SRC_NET.051, M.SRC_NET.072, M.SRC_NET.073, M.SRC_NET.074, M.SRC_NET.097, M.SRC_NET.112, M.SRC_NET.120, M.SRC_NET.122 |
| A.U10.41 | merged into M.SRC_NET.018, M.SRC_NET.041, M.SRC_NET.043, M.SRC_NET.045, M.SRC_NET.046, M.SRC_NET.047, M.SRC_NET.072 |
| A.U10.43 | merged into M.SRC_NET.042, M.SRC_NET.049, M.SRC_NET.077 |
| A.U10.44 | merged into M.SRC_NET.051, M.SRC_NET.054, M.SRC_NET.056, M.SRC_NET.057, M.SRC_NET.058, M.SRC_NET.070, M.SRC_NET.087, M.SRC_NET.094, M.SRC_NET.100, M.SRC_NET.101, M.SRC_NET.128, M.SRC_NET.129, M.SRC_NET.170, M.SRC_NET.214, M.SRC_NET.215 |
| A.U10.45 | merged into M.SRC_NET.023, M.SRC_NET.026, M.SRC_NET.027, M.SRC_NET.028, M.SRC_NET.030, M.SRC_NET.049, M.SRC_NET.051, M.SRC_NET.054, M.SRC_NET.087, M.SRC_NET.165, M.SRC_NET.194, M.SRC_NET.199 |
| A.U10.46 | merged into M.SRC_NET.004, M.SRC_NET.041, M.SRC_NET.071, M.SRC_NET.094, M.SRC_NET.110, M.SRC_NET.150 |
| A.U11.S01 | merged into M.SRC_NET.071, M.SRC_NET.080, M.SRC_NET.096, M.SRC_NET.120 |
| A.U11.S02 | merged into M.SRC_NET.004, M.SRC_NET.006, M.SRC_NET.097, M.SRC_NET.110, M.SRC_NET.111, M.SRC_NET.117 |
| A.U11.04 | dropped (mentioned in this cluster's files only in its Why/Blast slot; no site here — carried by its own cluster) |
| A.U11.08 | dropped (no site here: buildgen/generated code (GEN); names it reads follow this cluster's renames) |
| A.U11.12 | dropped (no site here: `SystemService` level handling (SRC_CORE)) |
| A.U11.24 | dropped (mentioned in this cluster's files only in its Why/Blast slot; no site here — carried by its own cluster) |
| A.U11.26 | merged into M.SRC_NET.120 |
| A.U11.31 | merged into M.SRC_NET.006, M.SRC_NET.111, M.SRC_NET.123, M.SRC_NET.129, M.SRC_NET.171, M.SRC_NET.216 |
| A.U11.34 | dropped (no site here: tests (TEST_UNIT, TEST_HELP); src paths named only as the code under test, unchanged by the action) |
| A.U12.02 | dropped (mentioned in this cluster's files only in its Why/Blast slot; no site here — carried by its own cluster) |
| A.U12.03 | merged into M.SRC_NET.200, M.SRC_NET.201, M.SRC_NET.203 |
| A.U13.12 | merged into M.SRC_NET.202 |
| A.U13.13 | merged into M.SRC_NET.192, M.SRC_NET.195 |
| A.U13.14 | merged into M.SRC_NET.196 |
| A.U13.17 | merged into M.SRC_NET.192 |
| A.U13.18 | merged into M.SRC_NET.196, M.SRC_NET.199 |
| A.U13.19 | merged into M.SRC_NET.199 |
| A.U14.03 | merged into M.SRC_NET.118 |
| A.U14.06 | merged into M.SRC_NET.190 |
| A.U14.10 | merged into M.SRC_NET.054 |
| A.U14.15 | merged into M.SRC_NET.052 |
| A.U14.16 | dropped (no site here: SPEC F.2 / BACKLOG text (SPEC, DOCS)) |
| A.U14.26 | merged into M.SRC_NET.049, M.SRC_NET.052, M.SRC_NET.053, M.SRC_NET.080; parts (1)/(2) on `_now()`/`cettime()` dropped per U18 register fix 10 |
| A.U14.28 | dropped (no site here: SPECIFICATION.md text (SPEC)) |
| A.U14.34 | dropped (no site here: tests (TEST_UNIT, TEST_HELP); src paths named only as the code under test, unchanged by the action) |
| A.U14.36 | dropped (no site here: SPECIFICATION.md text (SPEC)) |
| A.U14.37 | dropped (mentioned in this cluster's files only in its Why/Blast slot; no site here — carried by its own cluster) |
| A.U15.09 | dropped (no site here: sensor drivers (SRC_SENS)) |
| A.U16.02 | dropped (no site here: L0/L1 checks (SCR, TEST_HELP); the src sites they read keep the shape these merges give them) |
| A.U16.05 | merged into M.SRC_NET.150, M.SRC_NET.157, M.SRC_NET.167 |
| A.U17.01 | merged into M.SRC_NET.167 |
| A.U17.02 | dropped (mentioned in this cluster's files only in its Why/Blast slot; no site here — carried by its own cluster) |
| A.U17.03 | dropped (no site here: SPECIFICATION.md text (SPEC)) |
| A.U17.04 | dropped (no site here: twin test (TWIN); reads `_GC_PAUSE_WORST_MS`'s value only) |
| A.U17.06 | merged into M.SRC_NET.155, M.SRC_NET.160 |
| A.U17.07 | merged into M.SRC_NET.214 |
| A.U17.08 | dropped (no site here: repo docs (DOCS)) |
| A.U17.10 | dropped (mentioned in this cluster's files only in its Why/Blast slot; no site here — carried by its own cluster) |
| A.U17.11 | dropped (no site here: L0 changelog check and the changelog table (SCR, DOCS); written from the final module (M.SRC_NET.151-.153)) |
| A.U17.12 | dropped (no site here: audit working file `audit/trace/UART_PART_J.md`) |
| A.U17.13 | merged into M.SRC_NET.150, M.SRC_NET.155, M.SRC_NET.162, M.SRC_NET.169, M.SRC_NET.191, M.SRC_NET.192, M.SRC_NET.196, M.SRC_NET.200, M.SRC_NET.201 |
| A.U17.14 | merged into M.SRC_NET.152, M.SRC_NET.162 |
| A.U17.16 | merged into M.SRC_NET.159 |
| A.U17.17 | merged into M.SRC_NET.163, M.SRC_NET.170 |
| A.U17.18 | merged into M.SRC_NET.213 |
| A.U17.19 | merged into M.SRC_NET.216 |
| A.U17.20 | merged into M.SRC_NET.152, M.SRC_NET.153, M.SRC_NET.156 |
| A.U17.22 | merged into M.SRC_NET.153, M.SRC_NET.156, M.SRC_NET.196 |
| A.U17.26 | merged into M.SRC_NET.150, M.SRC_NET.170, M.SRC_NET.211, M.SRC_NET.215, M.SRC_NET.216 |
| A.U17.28 | merged into M.SRC_NET.191, M.SRC_NET.192, M.SRC_NET.197 |
| A.U17.29 | merged into M.SRC_NET.211, M.SRC_NET.214 |
| A.U17.31 | merged into M.SRC_NET.202 |
| A.U18.01 | merged into M.SRC_NET.003, M.SRC_NET.004, M.SRC_NET.009, M.SRC_NET.020 |
| A.U18.R01 | merged into M.SRC_NET.082, M.SRC_NET.102 |
| A.U18.02 | merged into M.SRC_NET.004, M.SRC_NET.008, M.SRC_NET.020, M.SRC_NET.022 |
| A.U18.03 | merged into M.SRC_NET.004, M.SRC_NET.007, M.SRC_NET.020 |
| A.U18.04 | merged into M.SRC_NET.007 |
| A.U18.05 | merged into M.SRC_NET.026, M.SRC_NET.028 |
| A.U18.06 | merged into M.SRC_NET.004, M.SRC_NET.007, M.SRC_NET.026 |
| A.U18.07 | merged into M.SRC_NET.007 |
| A.U18.08 | merged into M.SRC_NET.004, M.SRC_NET.007, M.SRC_NET.009, M.SRC_NET.018, M.SRC_NET.021, M.SRC_NET.023 |
| A.U18.09 | merged into M.SRC_NET.004, M.SRC_NET.020, M.SRC_NET.022, M.SRC_NET.024 |
| A.U18.10 | merged into M.SRC_NET.020, M.SRC_NET.023, M.SRC_NET.024, M.SRC_NET.040, M.SRC_NET.041, M.SRC_NET.043, M.SRC_NET.044, M.SRC_NET.045, M.SRC_NET.046, M.SRC_NET.047, M.SRC_NET.050 |
| A.U18.11 | merged into M.SRC_NET.042 |
| A.U18.12 | merged into M.SRC_NET.023, M.SRC_NET.026, M.SRC_NET.048 |
| A.U18.13 | merged into M.SRC_NET.006, M.SRC_NET.026, M.SRC_NET.027 |
| A.U18.14 | merged into M.SRC_NET.026, M.SRC_NET.029, M.SRC_NET.047, M.SRC_NET.048 |
| A.U18.15 | merged into M.SRC_NET.004, M.SRC_NET.007, M.SRC_NET.020, M.SRC_NET.023, M.SRC_NET.046, M.SRC_NET.047, M.SRC_NET.048 |
| A.U18.16 | merged into M.SRC_NET.042, M.SRC_NET.048 |
| A.U18.17 | merged into M.SRC_NET.028, M.SRC_NET.030 |
| A.U18.19 | merged into M.SRC_NET.048 |
| A.U18.20 | merged into M.SRC_NET.057 |
| A.U18.21 | merged into M.SRC_NET.055 |
| A.U18.22 | merged into M.SRC_NET.051 |
| A.U18.23 | merged into M.SRC_NET.044, M.SRC_NET.054, M.SRC_NET.056 |
| A.U18.24 | merged into M.SRC_NET.077, M.SRC_NET.078, M.SRC_NET.087, M.SRC_NET.094, M.SRC_NET.100 |
| A.U18.25 | merged into M.SRC_NET.053 |
| A.U18.26 | merged into M.SRC_NET.053 |
| A.U18.27 | merged into M.SRC_NET.077, M.SRC_NET.086, M.SRC_NET.088, M.SRC_NET.089 |
| A.U18.28 | merged into M.SRC_NET.078, M.SRC_NET.082, M.SRC_NET.086, M.SRC_NET.093, M.SRC_NET.102 |
| A.U18.29 | merged into M.SRC_NET.083 |
| A.U18.30 | merged into M.SRC_NET.077, M.SRC_NET.084, M.SRC_NET.087, M.SRC_NET.092, M.SRC_NET.100 |
| A.U18.31 | merged into M.SRC_NET.087, M.SRC_NET.092 |
| A.U18.32 | merged into M.SRC_NET.088, M.SRC_NET.089 |
| A.U18.33 | merged into M.SRC_NET.074, M.SRC_NET.078, M.SRC_NET.091, M.SRC_NET.098, M.SRC_NET.101 |
| A.U18.34 | merged into M.SRC_NET.028 |
| A.U18.35 | merged into M.SRC_NET.101 |
| A.U18.36 | merged into M.SRC_NET.070, M.SRC_NET.089 |
| A.U18.37 | merged into M.SRC_NET.080, M.SRC_NET.096, M.SRC_NET.097 |
| A.U18.38 | merged into M.SRC_NET.073 |
| A.U18.40 | merged into M.SRC_NET.071, M.SRC_NET.075, M.SRC_NET.077, M.SRC_NET.078, M.SRC_NET.087, M.SRC_NET.098, M.SRC_NET.100 |
| A.U18.41 | merged into M.SRC_NET.092, M.SRC_NET.120 |
| A.U18.42 | merged into M.SRC_NET.078, M.SRC_NET.098 |
| A.U18.43 | merged into M.SRC_NET.030, M.SRC_NET.081, M.SRC_NET.118, M.SRC_NET.124 |
| A.U18.44 | merged into M.SRC_NET.004, M.SRC_NET.006, M.SRC_NET.041, M.SRC_NET.054, M.SRC_NET.071, M.SRC_NET.081, M.SRC_NET.094, M.SRC_NET.097 |
| A.U18.45 | merged into M.SRC_NET.023, M.SRC_NET.048 |
| A.U18.46 | merged into M.SRC_NET.025, M.SRC_NET.031 |
| A.U19.01 | merged into M.SRC_NET.120, M.SRC_NET.123 |
| A.U19.02 | merged into M.SRC_NET.111, M.SRC_NET.112, M.SRC_NET.122 |
| A.U19.03 | merged into M.SRC_NET.112, M.SRC_NET.122 |
| A.U19.04 | merged into M.SRC_NET.121 |
| A.U19.05 | merged into M.SRC_NET.119, M.SRC_NET.124 |
| A.U19.06 | merged into M.SRC_NET.118, M.SRC_NET.124, M.SRC_NET.127 |
| A.U19.07 | merged into M.SRC_NET.110, M.SRC_NET.111, M.SRC_NET.112, M.SRC_NET.118, M.SRC_NET.127 |
| A.U19.08 | merged into M.SRC_NET.112, M.SRC_NET.119, M.SRC_NET.127 |
| A.U19.09 | merged into M.SRC_NET.112, M.SRC_NET.128 |
| A.U19.10 | merged into M.SRC_NET.129 |
| A.U19.11 | merged into M.SRC_NET.112, M.SRC_NET.114, M.SRC_NET.115 |
| A.U19.12 | merged into M.SRC_NET.120 |
| A.U19.13 | dropped (mentioned in this cluster's files only in its Why/Blast slot; no site here — carried by its own cluster) |
| A.U19.15 | merged into M.SRC_NET.112, M.SRC_NET.119, M.SRC_NET.125, M.SRC_NET.130 |
| A.U19.16 | merged into M.SRC_NET.071, M.SRC_NET.096, M.SRC_NET.110, M.SRC_NET.120, M.SRC_NET.121, M.SRC_NET.122, M.SRC_NET.123 |
| A.U19.17 | merged into M.SRC_NET.110, M.SRC_NET.111, M.SRC_NET.113, M.SRC_NET.114, M.SRC_NET.115, M.SRC_NET.116, M.SRC_NET.117, M.SRC_NET.118, M.SRC_NET.119, M.SRC_NET.120, M.SRC_NET.123, M.SRC_NET.124, M.SRC_NET.125, M.SRC_NET.127, M.SRC_NET.128, M.SRC_NET.129, M.SRC_NET.130 |
| A.U19.19 | dropped (no site here: SPECIFICATION.md text (SPEC)) |
| A.U19.20 | merged into M.SRC_NET.112, M.SRC_NET.119 |
| A.U19.22 | dropped (withdrawn by the owner (OR114.a (2), no TCP_NODELAY); read only, in M.SRC_NET.132) |
| A.U19.23 | dropped (no site here: tests (TEST_UNIT, TEST_HELP); src paths named only as the code under test, unchanged by the action) |
| A.U19.24 | dropped (no site here: tests (TEST_UNIT, TEST_HELP); src paths named only as the code under test, unchanged by the action) |
| A.U2.01 | merged into M.SRC_NET.004, M.SRC_NET.049, M.SRC_NET.112, M.SRC_NET.153 |
| A.U2.04 | merged into M.SRC_NET.004, M.SRC_NET.023, M.SRC_NET.047, M.SRC_NET.077, M.SRC_NET.112, M.SRC_NET.153 |
| A.U2.05 | dropped (mentioned in this cluster's files only in its Why/Blast slot; no site here — carried by its own cluster) |
| A.U2.14 | merged into M.SRC_NET.070, M.SRC_NET.077, M.SRC_NET.082, M.SRC_NET.085, M.SRC_NET.086, M.SRC_NET.088, M.SRC_NET.089, M.SRC_NET.096 |
| A.U2.15 | merged into M.SRC_NET.040, M.SRC_NET.046, M.SRC_NET.047, M.SRC_NET.048, M.SRC_NET.049, M.SRC_NET.050, M.SRC_NET.051, M.SRC_NET.053 |
| A.U2.16 | merged into M.SRC_NET.004, M.SRC_NET.007 |
| A.U2.18 | dropped (mentioned in this cluster's files only in its Why/Blast slot; no site here — carried by its own cluster) |
| A.U2.19 | merged into M.SRC_NET.112, M.SRC_NET.118, M.SRC_NET.121, M.SRC_NET.122, M.SRC_NET.123, M.SRC_NET.125, M.SRC_NET.126, M.SRC_NET.127 |
| A.U2.20 | merged into M.SRC_NET.153, M.SRC_NET.156, M.SRC_NET.158, M.SRC_NET.159, M.SRC_NET.162, M.SRC_NET.163, M.SRC_NET.164, M.SRC_NET.165, M.SRC_NET.166, M.SRC_NET.167, M.SRC_NET.168, M.SRC_NET.169, M.SRC_NET.170 |
| A.U20.06 | dropped (no site here: buildgen/generated code (GEN); names it reads follow this cluster's renames) |
| A.U20.09 | dropped (no site here: buildgen/generated code (GEN); names it reads follow this cluster's renames) |
| A.U20.14 | merged into M.SRC_NET.110 |
| A.U20.16 | dropped (mentioned in this cluster's files only in its Why/Blast slot; no site here — carried by its own cluster) |
| A.U20.20 | dropped (no site here: buildgen/generated code (GEN); names it reads follow this cluster's renames) |
| A.U20.25 | dropped (no site here: buildgen/generated code (GEN); names it reads follow this cluster's renames) |
| A.U20.26 | dropped (no site here: buildgen/generated code (GEN); names it reads follow this cluster's renames) |
| A.U20.27 | dropped (no site here: buildgen/generated code (GEN); names it reads follow this cluster's renames) |
| A.U20.34 | dropped (no site here: buildgen/generated code (GEN); names it reads follow this cluster's renames) |
| A.U20.38 | dropped (no site here: buildgen/generated code (GEN); names it reads follow this cluster's renames) |
| A.U23.11 | merged into M.SRC_NET.123 |
| A.U23.17 | merged into M.SRC_NET.043 |
| A.U23.25 | dropped (no site here: js/ (WEB)) |
| A.U23.27 | dropped (no site here: js/ (WEB)) |
| A.U24.01 | merged into M.SRC_NET.212 |
| A.U24.09 | dropped (mentioned in this cluster's files only in its Why/Blast slot; no site here — carried by its own cluster) |
| A.U24.15 | dropped (mentioned in this cluster's files only in its Why/Blast slot; no site here — carried by its own cluster) |
| A.U24.16 | dropped (mentioned in this cluster's files only in its Why/Blast slot; no site here — carried by its own cluster) |
| A.U24.17 | dropped (mentioned in this cluster's files only in its Why/Blast slot; no site here — carried by its own cluster) |
| A.U24.19 | dropped (mentioned in this cluster's files only in its Why/Blast slot; no site here — carried by its own cluster) |
| A.U24.24 | dropped (mentioned in this cluster's files only in its Why/Blast slot; no site here — carried by its own cluster) |
| A.U24.32 | dropped (no site here: tests (TEST_UNIT, TEST_HELP); src paths named only as the code under test, unchanged by the action) |
| A.U24.33 | dropped (no site here: tests (TEST_UNIT, TEST_HELP); src paths named only as the code under test, unchanged by the action) |
| A.U24.34 | dropped (no site here: tests (TEST_UNIT, TEST_HELP); src paths named only as the code under test, unchanged by the action) |
| A.U24.36 | dropped (no site here: tests (TEST_UNIT, TEST_HELP); src paths named only as the code under test, unchanged by the action) |
| A.U24.37 | dropped (no site here: tests (TEST_UNIT, TEST_HELP); src paths named only as the code under test, unchanged by the action) |
| A.U24.41 | dropped (no site here: tests (TEST_UNIT, TEST_HELP); src paths named only as the code under test, unchanged by the action) |
| A.U24.45 | dropped (no site here for (1) (UART FRAM-logging tests, TEST_UNIT); (2) dropped: the `led_pin` path it tests is removed by A.U18.40 (M.SRC_NET.098)) |
| A.U24.67 | merged into M.SRC_NET.212; test-side `src_const()` read is TEST_UNIT's; `_BANNER` stays `const()` (A.U10.29) |
| A.U24.81 | dropped (mentioned in this cluster's files only in its Why/Blast slot; no site here — carried by its own cluster) |
| A.U25.20 | dropped (mentioned in this cluster's files only in its Why/Blast slot; no site here — carried by its own cluster) |
| A.U25.26 | dropped (mentioned in this cluster's files only in its Why/Blast slot; no site here — carried by its own cluster) |
| A.U25.27 | dropped (mentioned in this cluster's files only in its Why/Blast slot; no site here — carried by its own cluster) |
| A.U25.31 | dropped (no site here: twin (TWIN)) |
| A.U25.33 | dropped (mentioned in this cluster's files only in its Why/Blast slot; no site here — carried by its own cluster) |
| A.U25.45 | dropped (no site here: twin (TWIN)) |
| A.U25.46 | dropped (no site here: twin (TWIN)) |
| A.U25.71 | dropped (mentioned in this cluster's files only in its Why/Blast slot; no site here — carried by its own cluster) |
| A.U25.72 | dropped (mentioned in this cluster's files only in its Why/Blast slot; no site here — carried by its own cluster) |
| A.U26.15 | dropped (no site here: hardware tiers (HW_BENCH, HW_DEV)) |
| A.U26.20 | dropped (no site here: hardware tiers (HW_BENCH, HW_DEV)) |
| A.U26.27 | dropped (mentioned in this cluster's files only in its Why/Blast slot; no site here — carried by its own cluster) |
| A.U26.32 | dropped (mentioned in this cluster's files only in its Why/Blast slot; no site here — carried by its own cluster) |
| A.U26.33 | dropped (no site here: hardware tiers (HW_BENCH, HW_DEV)) |
| A.U26.45 | dropped (no site here: hardware tiers (HW_BENCH, HW_DEV)) |
| A.U26.49 | dropped (no site here: hardware tiers (HW_BENCH, HW_DEV)) |
| A.U26.55 | dropped (no site here: hardware tiers (HW_BENCH, HW_DEV)) |
| A.U26.56 | dropped (no site here: hardware tiers (HW_BENCH, HW_DEV)) |
| A.U26.67 | dropped (mentioned in this cluster's files only in its Why/Blast slot; no site here — carried by its own cluster) |
| A.U26.80 | dropped (no site here: hardware tiers (HW_BENCH, HW_DEV)) |
| A.U26.87 | dropped (mentioned in this cluster's files only in its Why/Blast slot; no site here — carried by its own cluster) |
| A.U27.07 | dropped (no site here: tests (TEST_UNIT, TEST_HELP); src paths named only as the code under test, unchanged by the action) |
| A.U27.32 | dropped (mentioned in this cluster's files only in its Why/Blast slot; no site here — carried by its own cluster) |
| A.U27.39 | dropped (mentioned in this cluster's files only in its Why/Blast slot; no site here — carried by its own cluster) |
| A.U28.27 | dropped (no site here: `pyproject.toml` (TOOL); the hotspot password stays as is (accepted credential)) |
| A.U28.28 | merged into M.SRC_NET.096, M.SRC_NET.130 |
| A.U28.29 | dropped (no site here: `pyproject.toml` (TOOL); the hotspot password stays as is (accepted credential)) |
| A.U28.30 | merged into M.SRC_NET.030, M.SRC_NET.081, M.SRC_NET.165 |
| A.U28.31 | dropped (no site here: `pyproject.toml` (TOOL); the hotspot password stays as is (accepted credential)) |
| A.U29.01 | dropped (no site here: SPECIFICATION.md text (SPEC)) |
| A.U29.02 | dropped (no site here: L0/L1 checks (SCR, TEST_HELP); the src sites they read keep the shape these merges give them) |
| A.U29.03 | merged into M.SRC_NET.072 |
| A.U3.01 | dropped (mentioned in this cluster's files only in its Why/Blast slot; no site here — carried by its own cluster) |
| A.U3.02 | merged into M.SRC_NET.044, M.SRC_NET.046, M.SRC_NET.047, M.SRC_NET.048, M.SRC_NET.049, M.SRC_NET.052, M.SRC_NET.078, M.SRC_NET.088, M.SRC_NET.089, M.SRC_NET.096, M.SRC_NET.152, M.SRC_NET.153, M.SRC_NET.155, M.SRC_NET.157, M.SRC_NET.158, M.SRC_NET.161, M.SRC_NET.162, M.SRC_NET.163, M.SRC_NET.164, M.SRC_NET.168, M.SRC_NET.169, M.SRC_NET.171 |
| A.U3.05 | merged into M.SRC_NET.047, M.SRC_NET.050, M.SRC_NET.057, M.SRC_NET.084, M.SRC_NET.086, M.SRC_NET.088 |
| A.U3.07 | merged into M.SRC_NET.100 |
| A.U3.08 | merged into M.SRC_NET.153, M.SRC_NET.158, M.SRC_NET.161, M.SRC_NET.162; its "32→91" read as a slip: catalog row 89 (A.U2.01) |
| A.U3.11 | merged into M.SRC_NET.126 |
| A.U30.02 | dropped (no site here: SPECIFICATION.md text (SPEC)) |
| A.U30.03 | dropped (no site here: L0/L1 checks (SCR, TEST_HELP); the src sites they read keep the shape these merges give them) |
| A.U30.19 | merged into M.SRC_NET.011, M.SRC_NET.060, M.SRC_NET.104, M.SRC_NET.121, M.SRC_NET.122, M.SRC_NET.123, M.SRC_NET.125, M.SRC_NET.126, M.SRC_NET.127, M.SRC_NET.130, M.SRC_NET.150, M.SRC_NET.165, M.SRC_NET.170 |
| A.U30.21 | dropped (mentioned in this cluster's files only in its Why/Blast slot; no site here — carried by its own cluster) |
| A.U31.01 | dropped (no site here: SPECIFICATION.md text (SPEC)) |
| A.U31.15 | merged into M.SRC_NET.077, M.SRC_NET.081, M.SRC_NET.085, M.SRC_NET.087, M.SRC_NET.089, M.SRC_NET.092 |
| A.U31.16 | merged into M.SRC_NET.004, M.SRC_NET.007, M.SRC_NET.026, M.SRC_NET.027 |
| A.U31.18 | merged into M.SRC_NET.118, M.SRC_NET.119, M.SRC_NET.126, M.SRC_NET.127 |
| A.U31.19 | merged into M.SRC_NET.077 |
| A.U32.01 | dropped (no site here: repo docs (DOCS)) |
| A.U32.04 | dropped (no site here: audit working record/inventory) |
| A.U32.05 | dropped (no site here: audit working record/inventory) |
| A.U32.06 | merged into M.SRC_NET.170, M.SRC_NET.215; starter names `start_listen`/`start_exercise` superseded by A.U10.44's `start_asy_*` (need met) |
| A.U34.01 | dropped (no site here: THIRD_PARTY_LICENSES.md / L0 attribution check (LIC)) |
| A.U34.03 | dropped (no site here: THIRD_PARTY_LICENSES.md / L0 attribution check (LIC)) |
| A.U34.05 | merged into M.SRC_NET.002, M.SRC_NET.005 |
| A.U34.06 | merged into M.SRC_NET.025 |
| A.U34.07 | dropped (no site here: THIRD_PARTY_LICENSES.md / L0 attribution check (LIC)) |
| A.U34.09 | dropped (no site here: THIRD_PARTY_LICENSES.md / L0 attribution check (LIC)) |
| A.U34.10 | dropped (no site here: THIRD_PARTY_LICENSES.md / L0 attribution check (LIC)) |
| A.U35.14 | dropped (no site here: tests (TEST_UNIT, TEST_HELP); src paths named only as the code under test, unchanged by the action) |
| A.U35.27 | dropped (no site here: twin CI suite (SCR)) |
| A.U35.35 | dropped (no site here: tests (TEST_UNIT, TEST_HELP); src paths named only as the code under test, unchanged by the action) |
| A.U35.38 | dropped (no site here: twin CI suite (SCR)) |
| A.U35.41 | merged into M.SRC_NET.200 |
| A.U35.43 | dropped (mentioned in this cluster's files only in its Why/Blast slot; no site here — carried by its own cluster) |
| A.U35.44 | dropped (mentioned in this cluster's files only in its Why/Blast slot; no site here — carried by its own cluster) |
| A.U35.45 | dropped (mentioned in this cluster's files only in its Why/Blast slot; no site here — carried by its own cluster) |
| A.U35.47 | merged into M.SRC_NET.164, M.SRC_NET.166, M.SRC_NET.167, M.SRC_NET.168 |
| A.U35.48 | dropped (no site here: tests (TEST_UNIT, TEST_HELP); src paths named only as the code under test, unchanged by the action) |
| A.U36.026 | dropped (mentioned in this cluster's files only in its Why/Blast slot; no site here — carried by its own cluster) |
| A.U36.029 | dropped (no site here: repo docs (DOCS)) |
| A.U36.044 | dropped (no site here: SPECIFICATION.md text (SPEC)) |
| A.U36.503 | dropped (no site here: SPECIFICATION.md text (SPEC)) |
| A.U36.507 | dropped (mentioned in this cluster's files only in its Why/Blast slot; no site here — carried by its own cluster) |
| A.U36.512 | merged into M.SRC_NET.120 |
| A.U36.531 | dropped (mentioned in this cluster's files only in its Why/Blast slot; no site here — carried by its own cluster) |
| A.U36.532 | merged into M.SRC_NET.190 |
| A.U36.536 | dropped (no site here: repo docs (DOCS)) |
| A.U36.544 | merged into M.SRC_NET.079, M.SRC_NET.152, M.SRC_NET.159, M.SRC_NET.192 |
| A.U36.547 | dropped (no site here: repo docs (DOCS)) |
| A.U36.548 | dropped (no site here: repo docs (DOCS)) |
| A.U37.04 | dropped (no site here: closing procedure (PROC)) |
| A.U37.07 | dropped (mentioned in this cluster's files only in its Why/Blast slot; no site here — carried by its own cluster) |
| A.U4.02 | dropped (mentioned in this cluster's files only in its Why/Blast slot; no site here — carried by its own cluster) |
| A.U4.07 | dropped (mentioned in this cluster's files only in its Why/Blast slot; no site here — carried by its own cluster) |
| A.U5.01 | merged into M.SRC_NET.071 |
| A.U5.02 | merged into M.SRC_NET.004, M.SRC_NET.006, M.SRC_NET.041, M.SRC_NET.044, M.SRC_NET.071, M.SRC_NET.078, M.SRC_NET.110, M.SRC_NET.119, M.SRC_NET.150, M.SRC_NET.155, M.SRC_NET.211, M.SRC_NET.213 |
| A.U5.03 | merged into M.SRC_NET.043, M.SRC_NET.076, M.SRC_NET.112, M.SRC_NET.211 |
| A.U5.04 | merged into M.SRC_NET.078, M.SRC_NET.112, M.SRC_NET.119 |
| A.U5.05 | merged into M.SRC_NET.112, M.SRC_NET.119 |
| A.U5.07 | merged into M.SRC_NET.076, M.SRC_NET.078, M.SRC_NET.098 |
| A.U5.09 | merged into M.SRC_NET.077, M.SRC_NET.078 |
| A.U5.10 | merged into M.SRC_NET.041, M.SRC_NET.042, M.SRC_NET.044 |
| A.U5.12 | merged into M.SRC_NET.150, M.SRC_NET.154, M.SRC_NET.155, M.SRC_NET.156, M.SRC_NET.211, M.SRC_NET.213 |
| A.U5.17 | merged into M.SRC_NET.192 |
| A.U5.18 | dropped (no site here: L0/L1 checks (SCR, TEST_HELP); the src sites they read keep the shape these merges give them) |
| A.U6.04 | dropped (no site here: buildgen/generated code (GEN); names it reads follow this cluster's renames) |
| A.U6.18 | merged into M.SRC_NET.043, M.SRC_NET.073 |
| A.U6.21 | dropped (no site here: buildgen/generated code (GEN); names it reads follow this cluster's renames) |
| A.U6.24 | dropped (no site here: buildgen/generated code (GEN); names it reads follow this cluster's renames) |
| A.U6.25 | merged into M.SRC_NET.078 |
| A.U6.26 | merged into M.SRC_NET.043 |
| A.U6.28 | merged into M.SRC_NET.073, M.SRC_NET.075 |
| A.U6.29 | merged into M.SRC_NET.018, M.SRC_NET.073, M.SRC_NET.075, M.SRC_NET.077, M.SRC_NET.096 |
| A.U6.30 | merged into M.SRC_NET.072, M.SRC_NET.073, M.SRC_NET.075 |
| A.U7.25 | dropped (no site here: SPECIFICATION.md text (SPEC)) |
| A.U8.01 | dropped (no site here: SPECIFICATION.md text (SPEC)) |
| A.U8.04 | merged into M.SRC_NET.112 |
| A.U8.06 | merged into M.SRC_NET.152, M.SRC_NET.191, M.SRC_NET.192, M.SRC_NET.212 |
| A.U8.07 | dropped (no site here: sensor drivers (SRC_SENS)) |
| A.U8.09 | merged into M.SRC_NET.020, M.SRC_NET.042 |
| A.U8.10 | merged into M.SRC_NET.077, M.SRC_NET.081, M.SRC_NET.082, M.SRC_NET.085, M.SRC_NET.088, M.SRC_NET.089, M.SRC_NET.093 |
| A.U8.11 | merged into M.SRC_NET.004, M.SRC_NET.007, M.SRC_NET.026, M.SRC_NET.028, M.SRC_NET.029, M.SRC_NET.048; `conn_tries`/round-trip tags dropped (V.U18.D); `_s` rows renamed `_ms` (A.U31.16) |
| A.U8.12 | merged into M.SRC_NET.078 |
| A.U8.23 | merged into M.SRC_NET.110, M.SRC_NET.111 |
| A.U8C2.04 | dropped (mentioned in this cluster's files only in its Why/Blast slot; no site here — carried by its own cluster) |
| A.U9.03 | dropped (no site here: buildgen/generated code (GEN); names it reads follow this cluster's renames) |
| A.U9.09 | merged into M.SRC_NET.122 |


Gap pass G2 rows (2026-10-01; `GAPS_G2.md` lists each item and its source):

| action ID / gap item | merged into M-ID / dropped (reason) |
|---|---|
| G1 hand-off H1 / M_SRC_SENS GAP-7 / M_TEST_UNIT GAP-U5 (`SOCKET_TEARDOWN` = W12) | M.SRC_NET.004, .007, .023, .047 (amended) |
| G1 hand-off H2 / M_WEB gap 3 (`PW` tag `special:""="Open network"`) | M.SRC_NET.073 (amended) |
| M_SRC_CORE GAP-G8 / M_TEST_UNIT GAP-U6 (`report_if_fatal` from `asy_print_log`) | M.SRC_NET.011, .060, .104, .110, .121, .150 (amended) |
| M_SRC_CORE GAP-G13 / M_SRC_SENS GAP-14 (webserver half) | M.SRC_NET.110, .112, .122 (amended: `checked_int()`/`checked_float()`) |
| M_SRC_CORE GAP-G12 (private by default across SRC_NET) | M.SRC_NET.008, .009 (`DNSQuery._data`), .044, .046, .048, .050 (NTP: `_network_available_locked`, `_get_dns_server`, `_dns_timeout_ms`, `_dns_tries`, `_ntp_fetch_timeout_ms`, `_retry_s`, `_retry_max_s`), .078 (`_hotspot_time`, `_conn_fail_to_hotspot`), .155, .156 (`UARTComm` `_uart`, `_role`, `_payload_size`, `_timeout`, `_uid`), .192, .195 (`UART` `_cancel`, `_txbuf`), .213, .215 (`UARTLinkDriver._role`) (amended) |
| M_SRC_NET gap 3 (readiness meets `WifiService`'s override) + A.U10.21 | M.SRC_NET.079 (`-> bool`, flag inherited), .119 (`-> bool`) (amended) |
| M_SRC_NET gap 4 / U19 A-C note 1 (envelope narrowing) | M.SRC_NET.120 (amended: no narrowing; agent decision 5 withdrawn) |
| M_GEN gap 6 (webserver/WiFi/NTP APIs the template calls) | carried as found: M.SRC_NET.044, .074, .078, .098, .112, .119, .129 (the snapshot field is `RSSI`, hand-off H-G1 to GEN) |
| M_HW_DEV GAP-D9 (WiFi repro scripts) | M.SRC_NET.078 (amended: the repro edit is skipped, the file goes in U26) |
| A.U10.21 | also M.SRC_NET.079, .119 (this pass) |
