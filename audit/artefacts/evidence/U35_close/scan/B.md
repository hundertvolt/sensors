B scan, written by the lane (Wed Oct 28 07:58:46 UTC 2026)

Group B (network, web and UART): `src/asy_webserver_service.py`, `src/asy_wifi_service.py`, `src/asy_ntp_client.py`,
`src/asy_dns_client.py`, `src/asy_captive_dns.py` (was `src/captive_dns.py`), `src/asy_udp_socket.py`,
`src/asy_uart_comm.py`, `src/asy_uart_driver.py`, `src/asy_uart_link_driver.py`. Range `25caf528..497b3eda`, read in
`S/wt-u35int` (nothing written there). Brief: `S/u35r/briefs/scan_firmware.md` with its scheme addendum (it replaced
`inv_firmware_additions.md` mid-lane; the inventory part done before carried over). Nothing changed in the repo.
Buildgen and the generated modules are not in group B; where a row's behaviour lives partly there (the /status flag of
NTP-16, the system commands of WS-12, the HotspotPW tag), the row says so. The NeoPixel overlay row the brief names is
group A's file, not recorded here.

## How the rows were found and judged
- Each file's diff was read on an AST-normalised form of both ends (comments, docstrings and annotations stripped;
  the scripts in `S/u35r/scan/work_B/tools/`), function by function where D.15
  reordered the file, with `git blame 25caf528..497b3eda` for the commits and each U35 lane commit's own message.
- Origins come from `audit/consolidation/M_SRC_NET.md` (M items, their "From" A-IDs), the A-IDs' "Why" in
  `audit/actions/U*.md`, `audit/sweeps/open_findings.md`, `audit/REGISTER.md`, the U35 lane commits and briefs.
- Evidence O: the owner's own words decide the behaviour, either naming it or ordering it for a class whose members are
  objectively identifiable ("No unbounded counters anywhere", "a parameter ... that exists only so a test ... can reach
  inside ... is removed", the review page's per-item "ok", the never-block rule CLAUDE.md:276-277 names these files).
  A general principle an agent applied to a fault found by reading (OR113's recovery ladder, the memory-gate rule) is
  H, its rule named in the origin. F: a test or bench run that failed on the pre-audit code. A test written to pin new
  behaviour that "failed first" only because the behaviour was absent is not F.
- Classes: R (O or F), K (a real finding - a deterministic fact by reading - whose code is beyond need, mostly
  diagnostics), H (hypothetical), X (right intent, more code than needed), C (exists because of another addition; the
  root is named). Every H carries a triage; the suspicious ones got one minimal check (V1-V6 below).
- Legacy citations are `legacy/firmware/python/...` paths (CommonDrivers/ unless IndividualDrivers/ is named) and
  `legacy/firmware/modules/sensortask-wozi.py`.

## Rows

### src/asy_dns_client.py

**DNS-1** - class **H** - evidence **H** - 2 code lines
- where: src/asy_dns_client.py:60-61
- what: a name over 255 octets on the wire or with an empty label is refused before any query is sent
- commits: f1f800e7
- origin: A.U18.09 / M.SRC_NET.022; seed NET.S14; G6/R33
- evidence: H: seed NET.S14: "trailing dot/empty label -> malformed query; no 255-octet QNAME check" (audit/actions/U18.md A.U18.09); no failure recorded
- legacy: no: legacy resolves through socket.getaddrinfo (legacy/firmware/python/CommonDrivers/async_connect.py:384)
- form: design: input validation at a public entry
- depends on: none
- device cost: 2 code lines; per lookup one empty-label scan and a length test
- triage: implausible: the only product caller, NTP, refuses such a host at PUT and swaps a stored one for the default (NTP-1, src/asy_ntp_client.py:162-166, 218-220), so no product input reaches the check
- simplest alternative: the pre-audit 63-octet label check alone
- scheme: HYP (built on a hypothetical, u35r/briefs/scan_firmware.md:6); MIN (minimal change, u35r/briefs/scan_firmware.md:3-5)

**DNS-2** - class **R** - evidence **O** - 0 code lines
- where: src/asy_dns_client.py:159-161
- what: the resolver asks only the servers its caller passes; the built-in 8.8.8.8/1.1.1.1 pair is gone (it moved into NTP's DNSFallback, NTP-2)
- commits: f1f800e7
- origin: A.U18.10 / M.SRC_NET.020, .023; OR56 (2)
- evidence: O: OR56 (2026-09-26, PROJECT_AUDIT_PLAN.md:382): "Public DNS fallback: If that was just an added default value for the config it's okay"; review item dns-fallback-setting "ok" 2026-10-02 (audit/review/answers.json)
- legacy: no: legacy has no resolver of its own (async_connect.py:384)
- form: design
- depends on: NTP-2
- device cost: 0 code lines; removal: -2 lines (the constant and its concatenation)
- minimal change: pre-audit `dns_servers + _FALLBACK_DNS_SERVERS` -> `dns_servers` and the constant deleted (2 lines), with NTP-2 passing the list; pinned by tests/test_asy_ntp_client.py test_resolve_ntp_server_asks_dhcp_first_then_the_fallback_list_in_order
- scheme: none

**DNS-3** - class **K** - evidence **H** - 16 code lines
- where: src/asy_dns_client.py:45-51, 107-113, 158, 169-170, 185-186
- what: resolve_ipv4() returns (address, cause): resolved, not sent, NXDOMAIN, failed; NTP logs the cause (NTP-5)
- commits: 06a8ae5d
- origin: OF-78, OF-80 (U18 lanes U and R scans), closed at U30 lane C c78c936 (R-19)
- evidence: H: OF-80: "NXDOMAIN, SERVFAIL and 'no answer' all return None and the caller logs one E67, so a mistyped NTPHost and a broken resolver look the same in /status" (audit/sweeps/open_findings.md:88)
- legacy: no
- form: design: a return shape
- depends on: none (NTP-5 consumes it)
- device cost: 16 code lines; one 2-tuple per lookup
- triage: implausible as a failure: the pre-audit ambiguity is real by reading (asy_dns_client.py@25caf528 resolve_ipv4 returns None for every case), its effect is one error code for four causes
- simplest alternative: the pre-audit `str | None`
- scheme: MIN (minimal change, u35r/briefs/scan_firmware.md:3-5); FEAT (same top-level features, CLAUDE.md:508-511)

**DNS-4** - class **H** - evidence **H** - 8 code lines
- where: src/asy_dns_client.py:165-173
- what: each try checks its own send; a try whose send failed waits for no reply (the retry loop moved here from UDPSocket.write_and_recvfrom)
- commits: 06a8ae5d (f1f800e7 for the UDP half)
- origin: OF-78; A.U18.14 RF160 (agent, 2026-09-28)
- evidence: H: RF160: "write_and_recvfrom() discards write()'s result ..., so a failed send ... is waited out and logged as NTP errno 21" (A.U18.14 Why); no failure recorded
- legacy: no: legacy ignores the send's result too (legacy/firmware/python/CommonDrivers/asy_udp_socket.py:73-76)
- form: design
- depends on: DNS-3
- device cost: 8 code lines; none extra
- triage: implausible: a send fails only with no link or socket; the pre-audit cost was one wasted 500 ms reply wait per server
- simplest alternative: pre-audit write_and_recvfrom()
- scheme: HYP (built on a hypothetical, u35r/briefs/scan_firmware.md:6); MIN (minimal change, u35r/briefs/scan_firmware.md:3-5)

**DNS-5** - class **H** - evidence **H** - 4 code lines
- where: src/asy_dns_client.py:147-150
- what: a `tries` past a machine word answers (None, not sent) instead of raising
- commits: 06a8ae5d, f0b2f2fb
- origin: REGISTER.md:738, U30 fix F1c (agent, 2026-10-20)
- evidence: H: REGISTER.md:738: "Modes: the resolver unchanged for a generated int"
- legacy: no
- form: patch: guards a value no caller produces (tries comes from the generated NtpTiming, Part N dns.tries = 1)
- depends on: none
- device cost: 4 code lines; one range() per lookup (already there)
- triage: implausible: no product or generated caller can pass an overflowing tries
- simplest alternative: none (pre-audit had a TypeError guard only)
- scheme: HYP (built on a hypothetical, u35r/briefs/scan_firmware.md:6); PATCH (patch, not design, u35r/briefs/inv_firmware_additions.md:2-4); TYPEG (unreachable guard, u35r/recovered/owner_rulings_after_LN118.md (2026-10-27))

**DNS-6** - class **K** - evidence **H** - 3 code lines
- where: src/asy_dns_client.py:153-155
- what: a heap failure while building the query prints its text through console() at every DebugLevel
- commits: 06a8ae5d
- origin: OF-77 (U18 lane R scan), closed at U30
- evidence: H: OF-77: "a caught MemoryError returns the sentinel with no text, so the memory gates never see it" (open_findings.md:85)
- legacy: no
- form: design: memory-gate visibility (CLAUDE.md:395-403)
- depends on: none
- device cost: 3 code lines; only on a failed allocation
- triage: implausible as a device failure; it serves the test gates' MemoryError rule
- simplest alternative: pre-audit silent None
- scheme: none

**DNS-7** - class **H** - evidence **H** - 2 code lines
- where: src/asy_dns_client.py:175-176
- what: a socket teardown that did not complete persists W12
- commits: f1f800e7
- origin: A.U18.15; G6/R34 "every caller checks disconnect()'s bool and logs"
- evidence: H: no failure recorded (A.U18.15 Why cites requirements only)
- legacy: no
- form: design
- depends on: none
- device cost: 2 code lines; a FRAM entry only on failure
- triage: implausible: disconnect() fails only if poller.unregister()/close() raise, never observed
- simplest alternative: pre-audit unchecked disconnect()
- scheme: HYP (built on a hypothetical, u35r/briefs/scan_firmware.md:6)

**DNS-8** - class **H** - evidence **H** - 4 code lines
- where: src/asy_dns_client.py:171, 177-180
- what: a reply filling 513 bytes is taken as cut by lwIP: W16, next server
- commits: f1f800e7
- origin: M.SRC_NET.023 (1), silent-failure scan SF-B15 (2026-10-06)
- evidence: H: M.SRC_NET.023 (1): "A cut reply is detected instead of parsed as 'no usable answer'"; no failure recorded
- legacy: no
- form: design
- depends on: none
- device cost: 4 code lines; one byte more per receive allocation
- triage: implausible: no EDNS is sent, so a server truncates at 512 B itself (RFC 1035 4.2.1); an A answer to one question fits
- simplest alternative: pre-audit 512 B receive
- scheme: HYP (built on a hypothetical, u35r/briefs/scan_firmware.md:6); MIN (minimal change, u35r/briefs/scan_firmware.md:3-5)

**DNS-9** - class **R** - evidence **O** - 4 code lines
- where: src/asy_dns_client.py:116-120
- what: host_label_ok(): the RFC 1123 host-label test, shared by NTPHost (NTP-1) and Hostname (WF-1)
- commits: f1f800e7
- origin: M.SRC_NET.018; A.U6.29, A.U10.41
- evidence: O: via NTP-1 (OR70 "4. b", PROJECT_AUDIT_PLAN.md:410)
- legacy: no
- form: design: one shared helper (Part G)
- depends on: NTP-1, WF-1
- device cost: 4 code lines; per PUT of NTPHost/Hostname
- minimal change: needed by NTP-1's minimal form; 4 lines; pinned by tests/test_asy_dns_client.py host-label cases (tests/_radio_shape_cases.json hostLabel)
- scheme: none

Checked for non-behavioural changes (src/asy_dns_client.py): the full diff 25caf528..497b3eda was read on an AST-normalised form (comments, docstrings and annotations stripped). Not counted: `_is_ipv4_literal()` -> `ipv4_to_int()` (the same accept rule: four decimal parts 0-255), the constant renames (`DNS_QTYPE_A`, `DNS_LABEL_MAX`, `DNS_UDP_MAX`), the removed test-only `port` parameter (A.U18.45, OR36.a (1)), the removed UDPSocket construction guard (unreachable once the port is a constant, G5/R54), the `pr` keyword, the header text.

### src/asy_udp_socket.py

**UDP-1** - class **R** - evidence **O** - 0 code lines
- where: src/asy_udp_socket.py:42-43
- what: the address must be a (host, port) tuple; the pre-resolved bytes sockaddr path is gone
- commits: f1f800e7
- origin: A.U18.12; G7/R01
- evidence: O: OR36.a (1) (2026-09-26, PROJECT_AUDIT_PLAN.md:341): "A parameter, non-const() value, public attribute or function that exists only so a test, the twin or a hardware script can reach inside is a test artifact and is removed"
- legacy: partly: legacy passes any addr through (legacy asy_udp_socket.py:13-14)
- form: design: removal
- depends on: none
- device cost: 0 code lines; removal: about -4 lines; no product caller affected (every one passes a tuple)
- minimal change: the removal itself; pinned by a test that UDPSocket(b'...') raises TypeError
- scheme: none

**UDP-2** - class **X** - evidence **H** - 14 code lines
- where: src/asy_udp_socket.py:69-70, 92-93, 98-99, 135-136, 147-148, 161-162, 170-171
- what: every one of the seven handlers prints a caught MemoryError's text through console()
- commits: f1f800e7
- origin: M.SRC_NET.027 (1)/.028 (1), silent-failure scan SF-A12 (2026-10-06)
- evidence: H: SF-A12 (A-C fold): the class has no logger; the memory gates read printed text (CLAUDE.md:395-424)
- legacy: no
- form: design intent, repeated by hand seven times
- depends on: none
- device cost: 14 code lines; only on a failed allocation
- triage: implausible as a device failure; serves the test gates
- simplest alternative: one small helper, or the logger rule F3r gave PrintLog (68224efb) reused
- scheme: MIN (minimal change, u35r/briefs/scan_firmware.md:3-5); P4 (P4 one material, audit/CONSOLIDATION.md:28)

**UDP-3** - class **R** - evidence **O** - 3 code lines
- where: src/asy_udp_socket.py:33-36, 133
- what: a wait with no deadline (the captive DNS listen) polls every 100 ms instead of 20 ms; exchanges keep 20 ms
- commits: f1f800e7
- origin: A.U18.05; G4/R56
- evidence: O: OR141 (2026-10-05, PROJECT_AUDIT_PLAN.md:552): "Concerning the answers to my questions: do all as you suggested", after the review note on idle-poll-rate: "What is the general background of this, and how and where is the rate specified and validated?" (audit/review/answers.json); M.SRC_NET.007 (1): "100 ms, kept: owner, 2026-10-05, OR141.a (5)"
- legacy: no: legacy sleeps 0 between polls (legacy asy_udp_socket.py:44, 56)
- form: design
- depends on: none
- device cost: 3 code lines; the captive DNS listener wakes 10/s instead of 50/s (a saving)
- minimal change: pre-audit ready(): pass 100 instead of 20 when timeout_ms <= 0 (1 line); pinned by tests/test_asy_udp_socket.py test_ready_without_a_deadline_polls_at_the_idle_rate
- scheme: none

**UDP-4** - class **C** - evidence **H** - 12 code lines
- where: src/asy_udp_socket.py:103-116
- what: the poll loop checks its own deadline before each poll and cuts the last sleep to end at it
- commits: 21ec0979 (LC1); 41b47f1d, f1f800e7 (the wait_for_ms() form it replaced)
- origin: LC1 commit; root A.U10.26 "one timeout mechanism" (owner-prioritised, 2026-09-11, 6cf82a1: "PRIORITIZED ... to be done soon")
- evidence: H: against 25caf528 the change is the deadline's precision only; the F belongs to the audit's own intermediate form: "a cancel in each round after the deadline raises out of ready() and ends NTP's sync task (both red on the wait_for_ms() form at round 1)" (21ec0979)
- legacy: partly: legacy's loop has the same ticks deadline (legacy asy_udp_socket.py:44-56)
- form: design restored
- depends on: the A.U10.26 wait_for_ms() form (gone)
- device cost: 12 code lines; none extra
- triage: implausible: the pre-audit loop overshot its deadline by at most one 20 ms poll and never lost a cancel
- simplest alternative: the pre-audit loop as it was, plus UDP-3's idle rate
- scheme: CASC (cascade, u35r/briefs/scan_firmware.md:7); DELAY (hardcoded delay/timing check, u35r/briefs/scan_firmware.md:106-107); MIN (minimal change, u35r/briefs/scan_firmware.md:3-5)

**UDP-5** - class **H** - evidence **H** - 3 code lines
- where: src/asy_udp_socket.py:73-75
- what: a cancel landing in the connect backoff still tears the half-built socket down (disconnect in finally)
- commits: 656fc82f
- origin: OF-240 (U35 C2b reading, LEAD NOTES 19), lane Q e50f813
- evidence: H: OF-240: "latent, each caller disconnects in its own finally" (open_findings.md:248)
- legacy: no: legacy never tears a failed connect down (legacy asy_udp_socket.py:21-42)
- form: design
- depends on: none
- device cost: 3 code lines; none
- triage: implausible: OF-240 itself records it as latent - every caller disconnects in its own finally
- simplest alternative: pre-audit order
- scheme: HYP (built on a hypothetical, u35r/briefs/scan_firmware.md:6)

Checked for non-behavioural changes (src/asy_udp_socket.py): AST-normalised diff read in full. Not counted: the class and attribute renames (`AsyUDPSocket` -> `UDPSocket`, `sock` -> `_sock`), the backoff in ms (same 500 ms), the removed `conn_tries` (every product caller used 1; OR36.a (1)), the removed async context manager (no user; OR46.a (2)), the removed `write_and_recvfrom()` (U34, its two callers loop themselves: DNS-4, NTP-4), the removed mode check and the TypeError catches of ready()/recvfrom()/write() (D2S, owner 2026-10-27 typing rule), the except-tuple order, the attribution header.

### src/asy_captive_dns.py

**CD-1** - class **R** - evidence **O** - 8 code lines
- where: src/asy_captive_dns.py:49, 204-206, 209, 211-214
- what: an A or ANY query gets the A record; every other type gets NOERROR with no answer (NODATA)
- commits: f1f800e7
- origin: A.U18.01 / M.SRC_NET.009; seed NET.S12
- evidence: O: OR102 (2026-09-29, PROJECT_AUDIT_PLAN.md:474): "7. adopt correct behavior adhering to the standards without raising complexity"; code tag :205 (owner, 2026-09-29)
- legacy: no: legacy answers every QTYPE with an A record (legacy/firmware/python/CommonDrivers/captive_dns.py:57-66)
- form: design
- depends on: none
- device cost: 8 code lines; per query one 2-byte slice
- minimal change: pre-audit response(): one QTYPE test, the ANCOUNT byte and `if answer:` around the three answer lines (~6 lines); pinned by tests/test_asy_captive_dns.py test_other_query_types_get_an_empty_noerror_reply, test_an_a_or_any_query_gets_the_a_record
- scheme: none

**CD-2** - class **H** - evidence **H** - 6 code lines
- where: src/asy_captive_dns.py:162-163, 169-170, 174-175
- what: a query with QR set or QDCOUNT != 1, a label byte over 63 or a name over 255 octets is dropped
- commits: f1f800e7
- origin: A.U18.02 RF214 (agent, 2026-09-28); seed NET.S12
- evidence: H: RF214: "a query declaring 0 or several questions is answered as one ... answered with a malformed echoed question instead of being dropped" (A.U18.02 Why); no failure recorded
- legacy: no (legacy captive_dns.py:47-55 checks the opcode only)
- form: design: validation
- depends on: none
- device cost: 6 code lines; per query three comparisons
- triage: implausible: a malformed query gets a malformed echo; the pre-audit parse already drops a truncated question and catches every parse error
- simplest alternative: pre-audit parse
- scheme: HYP (built on a hypothetical, u35r/briefs/scan_firmware.md:6); MIN (minimal change, u35r/briefs/scan_firmware.md:3-5)

**CD-3** - class **H** - evidence **H** - 1 code lines
- where: src/asy_captive_dns.py:92
- what: each datagram is received into 512 B (the DNS bound) instead of 4096 B
- commits: f1f800e7
- origin: A.U18.03; G4/R39; seed NET.S10
- evidence: H: A.U18.03 Fact: "modlwip allocates the full requested length for every receive (vstr_init_len(&vstr, len), extmod/modlwip.c:1324)"
- legacy: no: legacy receives 4096 B (legacy captive_dns.py:20)
- form: design
- depends on: none
- device cost: 1 code lines; 3.5 KB less heap per query in hotspot mode
- triage: suspicious: every hotspot query allocated 4 KB while the setup page is served; SPEC I.3 records ~870 B pieces failing with ~100 KB free under load
- verification: V3, mechanism confirmed; consequence unverified
- minimal change: recvfrom(4096) -> recvfrom(512) (1 line); pinned by tests/test_asy_captive_dns.py's recvfrom(512) record (M.SRC_NET.007 blast)
- scheme: none

**CD-4** - class **K** - evidence **H** - 3 code lines
- where: src/asy_captive_dns.py:115-119
- what: a socket that never bound logs E10 INIT; a failed receive logs W42 (was W2 'Invalid DNS request data or address')
- commits: f1f800e7
- origin: A.U18.06 RF179 (agent, 2026-09-28)
- evidence: H: RF179: "a local bind failure logged as client garbage" (A.U18.06 Why)
- legacy: no (legacy logs nothing persisted)
- form: design: diagnostic
- depends on: none
- device cost: 3 code lines; none
- triage: implausible as a failure: a wrong log text by reading, nothing else
- simplest alternative: pre-audit W2
- scheme: MIN (minimal change, u35r/briefs/scan_firmware.md:3-5)

**CD-5** - class **H** - evidence **H** - 12 code lines
- where: src/asy_captive_dns.py:86-87, 131-146
- what: a cancellation propagates out of run() after the cleanup instead of ending it normally
- commits: f1f800e7
- origin: A.U18.07 RF205 (agent)
- evidence: H: RF205: "captive DNS turns a cancellation into a normal return" (A.U18.07 Why)
- legacy: no: legacy catches CancelledError and breaks (legacy captive_dns.py:31-33)
- form: design
- depends on: none
- device cost: 12 code lines; none
- triage: implausible: no code awaits the captive DNS task (grep `await .*dns_server_task` over src/ and build/generated_src/: none); WifiService cancels it fire-and-forget
- simplest alternative: pre-audit except CancelledError: break
- scheme: HYP (built on a hypothetical, u35r/briefs/scan_firmware.md:6)

**CD-6** - class **H** - evidence **H** - 1 code lines
- where: src/asy_captive_dns.py:97
- what: the listen loop yields once per received datagram
- commits: f1f800e7
- origin: REGISTER.md:520 (U18 lane C scan)
- evidence: H: REGISTER.md:520: "a flood kept the socket ready and starved every other task until the watchdog; ... found by lane C's scan, tests fail first"
- legacy: no: legacy has the same gap (legacy asy_udp_socket.py:49-53 returns without yielding while ready)
- form: design
- depends on: none
- device cost: 1 code lines; one scheduler pass per datagram
- triage: suspicious: rare trigger (a hotspot client flooding DNS), severe consequence (watchdog reset)
- verification: V2, confirmed (mechanism); the watchdog consequence unverified
- minimal change: `await asyncio.sleep(0)` after each received datagram (1 line); pinned by tests/test_asy_captive_dns.py test_run_yields_once_per_datagram_while_the_socket_stays_ready
- scheme: none

**CD-7** - class **K** - evidence **H** - 2 code lines
- where: src/asy_captive_dns.py:185-186
- what: a heap failure while parsing a query re-raises: run() persists E23 and pauses 3 s, instead of dropping the query as malformed
- commits: f1f800e7
- origin: REGISTER.md:520 (U18 lane C scan)
- evidence: H: REGISTER.md:520: "the parse catches swallowed MemoryError"
- legacy: no
- form: design: diagnostic
- depends on: none
- device cost: 2 code lines; a 3 s pause on each heap failure (new)
- triage: implausible as a failure; it adds a persisted entry and a pause where a drop was
- simplest alternative: pre-audit drop
- scheme: MIN (minimal change, u35r/briefs/scan_firmware.md:3-5)

**CD-8** - class **R** - evidence **O** - 3 code lines
- where: src/asy_captive_dns.py:127, 138, 190
- what: every broad handler records a caught C-stack overflow first (the supervisor then reboots with its own reason)
- commits: 06a8ae5d
- origin: A.U30.19 / M.SRC_NET.011
- evidence: O: review item c-stack-reboot "ok" 2026-10-01, decision "Running out of C stack reboots the unit with its own reset reason" (audit/review/answers.json)
- legacy: no
- form: design
- depends on: the supervisor's reboot path (group A)
- device cost: 3 code lines; one flag test per caught exception
- minimal change: one report_if_fatal(e) per broad handler (3 lines); pinned by tests_scripts/test_fatal_report_sites.py
- scheme: none

**CD-9** - class **R** - evidence **O** - 6 code lines
- where: src/asy_captive_dns.py:30-35
- what: error/warning numbers come from the global catalog (E10/21/23, W12/41/42; were E1-3, W1-3)
- commits: 43aced07, f1f800e7
- origin: A.U2.16
- evidence: O: OR28 (2026-09-25, PROJECT_AUDIT_PLAN.md:324): "Globally harmonize errno and wrnno numbers."
- legacy: no (legacy logs nothing persisted)
- form: design
- depends on: none
- device cost: 6 code lines; none
- minimal change: renumbering only (6 constants); pinned by tests_scripts catalog check (buildgen/error_catalog.json)
- scheme: none

Checked for non-behavioural changes (src/asy_captive_dns.py): diffed against src/captive_dns.py at 25caf528 (git mv in U10). Not counted: the module/class rename (`DNSServer` -> `CaptiveDNS`), `ipv4_to_int()` imported from the resolver (the same rule as the removed local `_ipv4_to_int()`), the log calls passing a fixed message and arguments instead of f-strings (A.U18.04: same text, no allocation when the level is off), the backoff constants in ms (same 0.5-5 s), the constructor's log config object (U5), `reset_error_counter()` returning the write's bool (A.U11.31), the removed address-parse try/except (rp2's recvfrom always gives a str, 656fc82f), the SPDX header.

### src/asy_ntp_client.py

**NTP-1** - class **R** - evidence **O** - 7 code lines
- where: src/asy_ntp_client.py:111, 162-166, 234-235
- what: NTPHost is 3-253 characters and must be an IPv4 literal or dot-separated host labels of at most 63; a PUT outside that answers Invalid (E21)
- commits: 41b47f1d, f1f800e7
- origin: A.U10.41 / M.SRC_NET.043, .045
- evidence: O: OR70 (2026-09-26, PROJECT_AUDIT_PLAN.md:410): "4. b", integrated as OR70.a (4): NTPHost "grounded in RFC 1035 (a name <= 253 octets, labels <= 63) or an IPv4 literal" (A.U10.41 Why)
- legacy: partly: legacy bounds the length only (the pre-audit bounds 'mirror the pre-refactor handler', :109-110)
- form: design
- depends on: DNS-9
- device cost: 7 code lines; per PUT
- minimal change: bound 1024 -> 253 (1 constant) and a PUT-side shape check in the existing override path (~5 lines); pinned by a PUT of NTPHost 'bad host!' answers Invalid and stores nothing (tests/test_asy_ntp_client.py PUT-refusal tests)
- scheme: none

**NTP-2** - class **R** - evidence **O** - 22 code lines
- where: src/asy_ntp_client.py:116-119, 147-154, 213, 217, 230-233, 236-243, 414
- what: new setting DNSFallback (default "8.8.8.8,1.1.1.1", up to three IPv4 addresses, empty = none), asked after the DHCP server; a PUT outside the form answers Invalid
- commits: f1f800e7
- origin: A.U18.10 / M.SRC_NET.020, .045
- evidence: O: OR56 (2) (PROJECT_AUDIT_PLAN.md:382): "Public DNS fallback: If that was just an added default value for the config it's okay"; review dns-fallback-setting "ok" 2026-10-02 (audit/review/answers.json); the three-server cap: code tag :117 (agent, 2026-09-30; owner-reviewed, 2026-10-02)
- legacy: no
- form: design
- depends on: DNS-2
- device cost: 22 code lines; per sync the list is split once
- minimal change: one config field + its ipv4-list check + passing it to resolve_ipv4() (~12 lines); pinned by tests/test_asy_ntp_client.py test_resolve_ntp_server_asks_dhcp_first_then_the_fallback_list_in_order, test_a_stored_fallback_that_is_not_an_ipv4_list_uses_its_default
- scheme: none

**NTP-3** - class **H** - evidence **H** - 6 code lines
- where: src/asy_ntp_client.py:218-223
- what: a stored NTPHost or DNSFallback outside its form runs on its default with W10
- commits: f1f800e7
- origin: M.SRC_NET.046
- evidence: H: code comment :221: "a file written outside the PUT path; four servers would break the C.8 bound"
- legacy: no
- form: patch: re-checks at every read what the PUT path already refuses
- depends on: NTP-1, NTP-2
- device cost: 6 code lines; two shape checks per sync
- triage: implausible: only a config file written outside the API reaches it
- simplest alternative: the PUT-side check alone
- scheme: HYP (built on a hypothetical, u35r/briefs/scan_firmware.md:6); MIN (minimal change, u35r/briefs/scan_firmware.md:3-5)

**NTP-4** - class **K** - evidence **H** - 3 code lines
- where: src/asy_ntp_client.py:269-271
- what: a request that could not be sent logs E72 'request not sent' and waits for no reply (was: waited and logged 'No reply')
- commits: f1f800e7
- origin: A.U18.14 RF160 (agent, 2026-09-28); review new-dns-ntp-errnos (routine, unanswered)
- evidence: H: RF160 (A.U18.14 Why): "a local failure recorded as the peer's silence"
- legacy: no: legacy ignores the send's result (async_connect.py:399)
- form: design: diagnostic
- depends on: none
- device cost: 3 code lines; none
- triage: implausible as a failure: a wrong log code by reading, plus one 5 s wait saved
- simplest alternative: pre-audit write_and_recvfrom()
- scheme: MIN (minimal change, u35r/briefs/scan_firmware.md:3-5); FEAT (same top-level features, CLAUDE.md:508-511)

**NTP-5** - class **K** - evidence **H** - 6 code lines
- where: src/asy_ntp_client.py:418-424
- what: a failed name lookup persists E73 (query not sent), E74 (NXDOMAIN) or E67 (no answer)
- commits: 06a8ae5d
- origin: OF-78, OF-80
- evidence: H: see DNS-3
- legacy: no
- form: design: diagnostic
- depends on: DNS-3
- device cost: 6 code lines; none
- triage: implausible as a failure (see DNS-3)
- simplest alternative: pre-audit one E12/E67
- scheme: MIN (minimal change, u35r/briefs/scan_firmware.md:3-5); FEAT (same top-level features, CLAUDE.md:508-511)

**NTP-6** - class **H** - evidence **H** - 3 code lines
- where: src/asy_ntp_client.py:268, 273-275
- what: the fetch disconnects in finally; a failed teardown persists W12
- commits: f1f800e7
- origin: A.U18.15; seed NET.S13
- evidence: H: NET.S13: "a cancel mid-fetch leaks a UDP PCB until GC" (A.U18.15 Why)
- legacy: no
- form: design
- depends on: none
- device cost: 3 code lines; none
- triage: implausible: a cancel lands mid-fetch only at shutdown or a task restart, and the socket's finaliser frees the pcb at the next collection
- simplest alternative: pre-audit disconnect after the exchange
- scheme: HYP (built on a hypothetical, u35r/briefs/scan_firmware.md:6)

**NTP-7** - class **H** - evidence **H** - 3 code lines
- where: src/asy_ntp_client.py:87-88, 272
- what: the reply is received into 48 B (was 1024 B); the request is built once
- commits: f1f800e7
- origin: A.U18.16; seed NET.S10
- evidence: H: seed NET.S10: "NTP allocates 1024 B for a 48 B reply"
- legacy: no: legacy 1024 B (async_connect.py:399)
- form: design
- depends on: none
- device cost: 3 code lines; ~1 KB less per sync (every 12 h)
- triage: implausible: one 1 KB allocation per sync
- simplest alternative: pre-audit 1024
- scheme: none

**NTP-8** - class **H** - evidence **H** - 3 code lines
- where: src/asy_ntp_client.py:327-329
- what: a reply whose transmit timestamp is zero is rejected (E69) instead of being read as 2036
- commits: f1f800e7
- origin: M.SRC_NET.049 (2): dependency refresh, micropython-lib 5139530
- evidence: H: M.SRC_NET.049 (2): "A zero transmit timestamp is refused before the era step can carry it into the plausibility window (raw 0 maps to 2036-02-07)"
- legacy: no: legacy sets any received time (async_connect.py:426-429), the same gap
- form: design: one guard
- depends on: none
- device cost: 3 code lines; one comparison per reply
- triage: suspicious: rare trigger (a non-KoD server reply with an unset timestamp), wrong consequence (the RTC jumps to 2036 until the next sync, every timestamp wrong)
- verification: V1, confirmed
- minimal change: `if raw_s == 0: log E69; return None` before the era step (3 lines); pinned by tests/test_asy_ntp_client.py test_a_zero_transmit_timestamp_is_rejected
- scheme: none

**NTP-9** - class **H** - evidence **H** - 3 code lines
- where: src/asy_ntp_client.py:316-318
- what: a reply shorter than 48 B is rejected (E69) before it is read
- commits: f1f800e7
- origin: M.SRC_NET.049 (1): dependency refresh, micropython-lib 9ec1830
- evidence: H: M.SRC_NET.049 (1): "receiver-side tightening; HEAD accepts 44-47 bytes"
- legacy: no
- form: design
- depends on: none
- device cost: 3 code lines; one comparison per reply
- triage: implausible: the parser reads bytes 0, 1 and 40-43 only, so a 44-47 B reply parses correctly, and a shorter one raised IndexError/ValueError, caught as malformed pre-audit (asy_ntp_client.py@25caf528 _parse_ntp_reply)
- simplest alternative: pre-audit except (IndexError, ValueError)
- scheme: HYP (built on a hypothetical, u35r/briefs/scan_firmware.md:6); MIN (minimal change, u35r/briefs/scan_firmware.md:3-5)

**NTP-10** - class **K** - evidence **H** - 3 code lines
- where: src/asy_ntp_client.py:341-343
- what: a heap failure while parsing logs E20 ALLOC, apart from E69 malformed
- commits: 1cff5a26
- origin: A.U14.26 (3); routine settlement ntp-malformed-text
- evidence: H: no failure recorded
- legacy: no
- form: design: diagnostic
- depends on: none
- device cost: 3 code lines; none
- triage: implausible as a failure: a code split
- simplest alternative: pre-audit one arm
- scheme: MIN (minimal change, u35r/briefs/scan_firmware.md:3-5)

**NTP-11** - class **R** - evidence **O** - 4 code lines
- where: src/asy_ntp_client.py:201, 310, 384-385
- what: Synced turns false three intervals after the last success, measured on ticks; a failed due resync no longer resets that age
- commits: 41b47f1d, f1f800e7, 656fc82f
- origin: A.U18.20 (agent, 2026-09-27; S03); G6/R30
- evidence: O: review ntp-synced-goes-stale "ok" 2026-10-02, decision "NTPSynced is true only while the last successful sync is recent: a failed resync no longer resets the staleness count" (audit/review/answers.json); owner, 2026-10-27, Q10: "Option a, the 10s don't matter at all relative to the interval" (S/u35r/recovered/owner_rulings_after_LN118.md)
- legacy: partly: legacy's intent (async_connect.py:450-461), defeated by its counter reset at every due resync
- form: design
- depends on: NTP-14 (the tick-age primitive)
- device cost: 4 code lines; one TickSeconds read per 10 s tick
- minimal change: pre-audit loop: count the stale age in its own seconds counter that only a success resets (~3 lines); pinned by tests/test_asy_ntp_client.py test_a_failed_resync_never_resets_the_staleness_count
- scheme: none

**NTP-12** - class **H** - evidence **H** - 5 code lines
- where: src/asy_ntp_client.py:199, 369, 387, 395, 404
- what: the synced resync cadence reads elapsed time (TickSeconds) instead of counting delivered 10 s ticks
- commits: c56b366b (F2r)
- origin: OF-247 (U35 V6 reading, LEAD NOTES 69): "a behaviour discrepancy, SPECIFICATION.md D.1's flag-first path"
- evidence: H: OF-247: "the resync cadence counts delivered 10 s ticks, so a dropped tick delays the resync" (open_findings.md:255); no owner ruling found (searched S/u35r/recovered/owner_rulings_after_LN118.md and REGISTER.md for OF-247)
- legacy: no: legacy counts delivered ticks (async_connect.py:451-452)
- form: design
- depends on: none
- device cost: 5 code lines; one TickSeconds per tick
- triage: implausible: a dropped soft-timer callback delays one 12 h resync by 10 s; the owner on the sibling rule: "the 10s don't matter at all relative to the interval" (Q10)
- simplest alternative: pre-audit `+= _NTP_CHECK_INTERV`
- scheme: HYP (built on a hypothetical, u35r/briefs/scan_firmware.md:6); D1 (flag, don't silently change, SPECIFICATION.md:4765-4766); MIN (minimal change, u35r/briefs/scan_firmware.md:3-5)

**NTP-13** - class **C** - evidence **H** - 3 code lines
- where: src/asy_ntp_client.py:157-159, 391-393
- what: the resync is due on the 10 s tick nearest its interval (the elapsed seconds rounded to the tick grid)
- commits: a66213b6 (F5)
- origin: F5 brief (lead, 2026-10-26); code tag :392 (agent, 2026-10-26)
- evidence: H: a66213b6: "the boundary tick then read just under one NTPInterval and the resync ran one tick (10 s) late, cycle after cycle" - a defect of NTP-12's form; the pre-audit tick count was due at exactly N ticks
- legacy: no
- form: patch: rounds around the restart jitter NTP-12 introduced
- depends on: NTP-12
- device cost: 3 code lines; one integer rounding per tick
- triage: implausible on its own: it only repairs NTP-12
- simplest alternative: none needed without NTP-12
- scheme: CASC (cascade, u35r/briefs/scan_firmware.md:7); DELAY (hardcoded delay/timing check, u35r/briefs/scan_firmware.md:106-107); PATCH (patch, not design, u35r/briefs/inv_firmware_additions.md:2-4)

**NTP-14** - class **R** - evidence **O** - 1 code lines
- where: src/asy_ntp_client.py:473
- what: LastSyncAge is read from a tick-measured age (TickSeconds) instead of +1 per 1 s tick
- commits: 41b47f1d
- origin: A.U10.03; REF/R03
- evidence: O: OR104 (2026-09-29, PROJECT_AUDIT_PLAN.md:478): "the \"never UTC\" goes for the others as well and might be a good candidate for a function which lives in the system service or the base classes, whichever fits best"
- legacy: no: legacy increments per tick (async_connect.py:498-499)
- form: design: the shared primitive (Part G)
- depends on: TickSeconds (group A)
- device cost: 1 code lines; one read per second
- minimal change: read a TickSeconds restarted at each success instead of incrementing (2 lines here); pinned by a driven-clock test: a dropped 1 s tick leaves LastSyncAge exact
- scheme: none

**NTP-15** - class **H** - evidence **H** - 6 code lines
- where: src/asy_ntp_client.py:196-197, 370, 373-374, 396-397
- what: the unsynced retry wait credits the check intervals since the last tick, rounded, at least one
- commits: 68224efb (F3r)
- origin: F3r brief (agent): "unsynced retry is one check interval late per dropped tick"
- evidence: H: no failure recorded; tests written red-first (68224efb)
- legacy: no: legacy retried at every 10 s tick (async_connect.py:457)
- form: patch: compensates dropped soft-timer ticks
- depends on: shares NTP-13's helper
- device cost: 6 code lines; one TickSeconds read per tick
- triage: implausible: a dropped tick delays one unsynced retry by 10 s inside a 10-600 s backoff
- simplest alternative: pre-audit `+= _NTP_CHECK_INTERV`
- scheme: HYP (built on a hypothetical, u35r/briefs/scan_firmware.md:6); DELAY (hardcoded delay/timing check, u35r/briefs/scan_firmware.md:106-107); CASC (cascade, u35r/briefs/scan_firmware.md:7)

**NTP-16** - class **R** - evidence **O** - 5 code lines
- where: src/asy_ntp_client.py:202, 306, 570-573, 579
- what: a clock-valid flag: UTCTime and the VOC backups keep using the clock through a stale sync, until a settings change (/status TimeStale)
- commits: 656fc82f
- origin: OF-79; BACKLOG owner question 7
- evidence: O: owner, 2026-10-21: "Clock time: Option b, but with a flag in /status showing it might be stale. Should be visible on the website as well" (656fc82f message; S/u35r/recovered/owner_rulings_after_LN118.md:11)
- legacy: no: legacy gates everything on Synced
- form: design
- depends on: NTP-11 (staleness became reachable)
- device cost: 5 code lines; none
- minimal change: as is (~5 lines; the /status flag is buildgen's); pinned by tests/test_asy_ntp_client.py test_a_settings_change_unsets_the_clock_until_the_next_sync
- scheme: none

**NTP-17** - class **R** - evidence **O** - 2 code lines
- where: src/asy_ntp_client.py:311, 478
- what: TS is null until the first sync this boot (utc_now())
- commits: 41b47f1d
- origin: A.U10.06
- evidence: O: review timestamps-before-ntp "ok" 2026-10-01, decision "Until NTP first sets the clock after a boot, readings are published with TS null, and UTCTime/LocalTime read null." (audit/review/answers.json)
- legacy: no
- form: design: the shared primitive
- depends on: utc_now() (group A)
- device cost: 2 code lines; none
- minimal change: two call sites of the primitive; pinned by twin Run 1 asserts UTCTime/LocalTime null before sync (review run1-null-time)
- scheme: none

**NTP-18** - class **C** - evidence **H** - 1 code lines
- where: src/asy_ntp_client.py:547-548
- what: cettime() answers once the clock was set this boot, not only while Synced
- commits: f1f800e7
- origin: M.SRC_NET.053 (1), SF-M2-02 (agent, 2026-10-06); REGISTER owner-review row 'LED alerts gated on clock set rather than synced'
- evidence: H: M.SRC_NET.053 (1): "it keeps HEAD's observable alert behaviour, where staleness is unreachable"
- legacy: no: legacy gates on Synced (async_connect.py:465-466)
- form: design
- depends on: NTP-11
- device cost: 1 code lines; none
- triage: needed only because NTP-11 made staleness reachable; without it the notification window would stop 36 h after the last sync (consistent with the owner's 2026-10-21 option b)
- simplest alternative: keep it with NTP-11
- scheme: CASC (cascade, u35r/briefs/scan_firmware.md:7)

**NTP-19** - class **R** - evidence **O** - 2 code lines
- where: src/asy_ntp_client.py:577-578
- what: an NTP settings change clears Synced and LastSyncAge, as legacy did
- commits: f1f800e7
- origin: A.U18.21
- evidence: O: OR102 (PROJECT_AUDIT_PLAN.md:474): "3. a", integrated as OR102.a (3): "an NTP settings change clears `Synced`, as legacy"; code tag :576 (owner, 2026-09-29)
- legacy: yes (async_connect.py:129-131)
- form: design: legacy parity
- depends on: none
- device cost: 2 code lines; none
- minimal change: add the Synced clear to the pre-audit ntp_force_sync() (1 line); pinned by tests/test_asy_ntp_client.py test_ntp_force_sync_resets_last_sync_retries_and_fires_the_sync_trigger
- scheme: none

**NTP-20** - class **H** - evidence **H** - 31 code lines
- where: src/asy_ntp_client.py:209-210, 251-262, 352-365, 479-480, 483-484, 513, 516
- what: a timer that failed to arm is re-armed from the sync task; a second failure persists E17 and ends the task
- commits: f1f800e7
- origin: A.U18.23 / M.SRC_NET.054; G5/R09
- evidence: H: rule only: OR31.a "either really work or return / end" and OR113.a (2) (A.U18.23 Why); no failure recorded
- legacy: no: legacy arms unguarded (async_connect.py:67-68)
- form: design
- depends on: none
- device cost: 31 code lines; two flag tests per sync trigger
- triage: implausible: needs the 16-alarm default pool exhausted (SPECIFICATION.md:6332-6338); no device census reaching 16 armed alarms found (searched SPEC F.1 and the twin timer-pool test's row, SPEC:5878, which empties the pool artificially)
- simplest alternative: pre-audit: log the failed arm, as it did
- scheme: HYP (built on a hypothetical, u35r/briefs/scan_firmware.md:6); MIN (minimal change, u35r/briefs/scan_firmware.md:3-5)

**NTP-21** - class **R** - evidence **O** - 0 code lines
- where: src/asy_ntp_client.py (removal)
- what: the per-module episode flags are gone: every failure persists through the logger's one newest-entry rule
- commits: 65a0df3b
- origin: A.U3.02
- evidence: O: OR35.a (PROJECT_AUDIT_PLAN.md:338): "It should be a feature of the print log module itself and apply to all its layers of error storage - RAM or FRAM."; OR35.b: "just don't repeat the same error in the slots. Pure and simple."
- legacy: no (legacy NTP logs nothing persisted)
- form: design: removal (-17 lines)
- depends on: the logger rule (group A)
- device cost: 0 code lines; none
- minimal change: the removal itself; pinned by tests/test_asy_print_log.py newest-entry rule tests (group A)
- scheme: none

**NTP-22** - class **R** - evidence **O** - 2 code lines
- where: src/asy_ntp_client.py:431, 464
- what: the two broad handlers record a caught C-stack overflow
- commits: 06a8ae5d
- origin: A.U30.19
- evidence: O: review c-stack-reboot "ok" (see CD-8)
- legacy: no
- form: design
- depends on: see CD-8
- device cost: 2 code lines; one flag test per caught exception
- minimal change: 2 lines; pinned by tests_scripts/test_fatal_report_sites.py
- scheme: none

**NTP-23** - class **R** - evidence **O** - 16 code lines
- where: src/asy_ntp_client.py:40-55
- what: error/warning numbers from the global catalog; a failed WiFi callback is now error E14 (was warnings W1/W3)
- commits: 65a0df3b, f1f800e7, 06a8ae5d
- origin: A.U2.15
- evidence: O: OR28 (see CD-9)
- legacy: no
- form: design
- depends on: none
- device cost: 16 code lines; none
- minimal change: renumbering; pinned by tests_scripts catalog check
- scheme: none

**NTP-24** - class **R** - evidence **O** - 0 code lines
- where: src/asy_ntp_client.py (removal)
- what: the logger's FRAM store is set up in the boot setup() batch, no longer lazily in the sync task
- commits: 8d44fd14
- origin: A.U10.10
- evidence: O: OR47.a (2026-09-26, PROJECT_AUDIT_PLAN.md:366) as A.U10.10 quotes it: "every chunk setup (`pr.setup()`) moves into the one-time boot `setup()` batch"
- legacy: no
- form: design: removal of the lazy call
- depends on: the base class setup() (group A)
- device cost: 0 code lines; none
- minimal change: the removal itself; pinned by the twin's boot-order record (OR47.a (1))
- scheme: none

Checked for non-behavioural changes (src/asy_ntp_client.py): AST-normalised diff read in full plus every U35 lane commit's own diff (c56b366b, 68224efb, a66213b6). Not counted: the class/key renames (`AsyNtpClient` -> `NTPClient`, `NTP_Host` -> `NTPHost`, `NTP_Offset_S` -> `NTPOffset`, `NTP_Interv_H` -> `NTPInterval`: REST key spelling, review rest-key-scheme "ok"), the timing object (U5), `async with` for the lock (the old acquire/finally/RuntimeError-swallow did the same), the starter renames, the removed `_now()` (its handler unreachable on target, G4/R15; replaced by `utc_now()`, NTP-17), `cettime()` without its catch (U18 register fix 10: unreachable on target), `max_module_error=0` as a keyword (same value), the RFC comments.

### src/asy_wifi_service.py

**WF-1** - class **H** - evidence **H** - 10 code lines
- where: src/asy_wifi_service.py:70-71, 101-103, 115-118, 130, 665
- what: Hostname must be an RFC 1123 host label and Country two uppercase letters: refused at PUT (E21), a stored outlier runs on its default (W10), a bad per-device default is ignored
- commits: 1b59a05d, f1f800e7
- origin: A.U6.29 RF212, A.U6.30 RF213 (agent, 2026-09-28)
- evidence: H: RF212/RF213 (A.U6.29/A.U6.30 Why): network.hostname()/country() copy the bytes unchecked (extmod/modnetwork.c:134-161); no failure recorded
- legacy: no: legacy checks lengths only
- form: design: validation
- depends on: DNS-9
- device cost: 10 code lines; per PUT and per connect
- triage: Hostname implausible (only DHCP/mDNS naming suffers); Country suspicious: a lowercase or non-ISO code reaches the CYW43, whose firmware CLM decides the channel set, so a home AP on channel 12/13 might never be found
- verification: V5, unverified (hardware round)
- simplest alternative: pre-audit byte bound only
- scheme: HYP (built on a hypothetical, u35r/briefs/scan_firmware.md:6); MIN (minimal change, u35r/briefs/scan_firmware.md:3-5)

**WF-2** - class **H** - evidence **H** - 13 code lines
- where: src/asy_wifi_service.py:368-380, 877-878
- what: GET /networking shows the radio value in use where a stored value outside the form runs on its default
- commits: f1f800e7
- origin: A.U18.37 RF164 (agent, 2026-09-28)
- evidence: H: RF164: "the API shows a setting that is not the one in use"
- legacy: no
- form: design
- depends on: WF-1 (the substitution it shows)
- device cost: 13 code lines; per GET /networking three shape checks
- triage: implausible: WF-1's PUT refusal keeps such values out; only a file written outside the API reaches it
- simplest alternative: pre-audit _mask_pw()
- scheme: HYP (built on a hypothetical, u35r/briefs/scan_firmware.md:6); MIN (minimal change, u35r/briefs/scan_firmware.md:3-5); CASC (cascade, u35r/briefs/scan_firmware.md:7)

**WF-3** - class **R** - evidence **O** - 44 code lines
- where: src/asy_wifi_service.py:196, 269, 420-424, 514-520, 541, 551, 596, 686-697, 711, 740-741, 749-766
- what: after a hotspot phase a second failed STA streak enters a silent mode (LED dark, no hotspot, one connect attempt per hotspot period) instead of switching Wi-Fi off for good
- commits: 01032838 (U22)
- origin: OR151 (U22 start fold) / M.SRC_NET.223
- evidence: O: owner, 2026-10-08 (REGISTER.md:889): "Don't permanently switch WiFi off, only stop retrying to connect." ... "The WiFi LED stays dark, even if it is activated, being completely silent in that mode. It should look like turned off."
- legacy: no: legacy deactivates Wi-Fi permanently (async_connect.py:353-361)
- form: design
- depends on: WF-7 (the period's timer)
- device cost: 44 code lines; one hotspot-period timer armed while silent; one connect attempt per hotspot_time_min
- minimal change: replace the pre-audit _deactivate_wlan_permanently() by a silent phase marked due by the hotspot window's watcher (~25 lines); pinned by tests/test_asy_wifi_service.py test_the_silent_mode_keeps_the_led_dark_until_a_link
- scheme: none

**WF-4** - class **R** - evidence **O** - 9 code lines
- where: src/asy_wifi_service.py:268, 474-478, 480, 988-992
- what: any credentials change lands in the fresh-boot state: a fresh failure streak and the hotspot available once more
- commits: 01032838
- origin: OR152 / M.SRC_NET.223 (5)
- evidence: O: owner, 2026-10-08 (M.SRC_NET.223 (5)): "Any change of credentials, no matter from which side, lands in the same mode as \"initial connection attempt after a fresh boot\". All further steps follow normally."
- legacy: no: legacy keeps the task-local streak and hotspot-used state across a reconnect (async_connect.py:168-200)
- form: design
- depends on: WF-3
- device cost: 9 code lines; none
- minimal change: a fresh-boot flag set by reconnect_wifi() and taken by the reconnect handler (~6 lines); pinned by tests/test_asy_wifi_service.py test_the_identity_hook_lands_in_the_fresh_boot_state
- scheme: none

**WF-5** - class **K** - evidence **H** - 4 code lines
- where: src/asy_wifi_service.py:348-351
- what: an empty SSID goes straight back to the hotspot without a failure streak (was: a forced streak, so after the first hotspot window: Wi-Fi off)
- commits: f1f800e7
- origin: SF-M2-01 (agent; REGISTER.md:107 owner-review list, not yet reviewed)
- evidence: H: REGISTER.md:107: "keeps the unit reachable; the owner rule's 'second STA failure streak' presupposes real STA attempts; reversible"
- legacy: partly: legacy forces the streak too and deactivates once the hotspot ran (async_connect.py:296-298, 353-361)
- form: design
- depends on: WF-3
- device cost: 4 code lines; none
- triage: suspicious: a fresh unit nobody configures within its first hotspot window (normal) goes dark until a power cycle
- verification: V6, confirmed by reading; whether it is a gap is the owner's call
- minimal change: only if the owner rejects OR151's "only through a reboot, as is" for an unconfigured unit: an empty SSID sets the hotspot phase directly (3 lines); pinned by tests/test_asy_wifi_service.py empty-SSID test: after a hotspot window with no client and no SSID the unit is back on the hotspot, not off
- scheme: D1 (flag, don't silently change, SPECIFICATION.md:4765-4766); FEAT (same top-level features, CLAUDE.md:508-511)

**WF-6** - class **H** - evidence **H** - 19 code lines
- where: src/asy_wifi_service.py:249, 731-735, 788, 799, 356-366
- what: in hotspot mode the radio mode switch is never repeated: an AP selected but not up gets its configuration re-applied
- commits: f1f800e7
- origin: A.U18.28; seed NET.S08; G4/R18
- evidence: H: NET.S08: "_run_hotspot_mode repeats the full mode switch ... on any tick where AP status != STAT_GOT_IP"; fact cited from cyw43 source only (A.U18.28 Why)
- legacy: no: legacy repeats the mode switch the same way (async_connect.py:225-229)
- form: design
- depends on: none
- device cost: 19 code lines; none
- triage: implausible: needs a link-down event on an active AP, not observed (driver source only); legacy field behaviour
- simplest alternative: pre-audit status != GOT_IP -> _start_hotspot()
- scheme: HYP (built on a hypothetical, u35r/briefs/scan_firmware.md:6); MIN (minimal change, u35r/briefs/scan_firmware.md:3-5)

**WF-7** - class **R** - evidence **O** - 16 code lines
- where: src/asy_wifi_service.py:323-337, 500-505
- what: a hotspot-window timer that fails to arm persists E17 and counts as the iteration's hardware failure (streak, task restart, reboot)
- commits: f1f800e7, 9bf22747
- origin: A.U18.24 (2); OF-129
- evidence: O: owner, 2026-10-13: "Take option b for 2" to "(b) Count it like silent mode does: it feeds the failure streak, then the task restart, then the budget's reboot." (REGISTER.md:624)
- legacy: no: legacy arms unguarded (async_connect.py:268)
- form: design
- depends on: WF-3
- device cost: 16 code lines; none unless the arm fails
- triage: trigger itself hypothetical (alarm pool exhaustion, see NTP-20); the owner chose the handling
- minimal change: catch the arm's OSError, persist E17, set the hardware-failure flag (~6 lines); pinned by tests/test_asy_wifi_service.py hotspot timer arm-failure tests
- scheme: HYP (built on a hypothetical, u35r/briefs/scan_firmware.md:6)

**WF-8** - class **H** - evidence **H** - 7 code lines
- where: src/asy_wifi_service.py:412-417, 923-925
- what: an uptime timer that failed to arm is retried every loop pass, persisted E17 (console line once per episode) and fed into the hardware streak
- commits: f1f800e7, 72b12815
- origin: A.U18.24 (1); OF-29
- evidence: H: rule only (G5/R09, OR113.a (2)); OF-29: the console flood while the pool stays exhausted
- legacy: no
- form: design
- depends on: none
- device cost: 7 code lines; one flag test per 5 s pass
- triage: implausible: alarm pool exhaustion (see NTP-20)
- simplest alternative: pre-audit: log the failed arm
- scheme: HYP (built on a hypothetical, u35r/briefs/scan_firmware.md:6); MIN (minimal change, u35r/briefs/scan_firmware.md:3-5)

**WF-9** - class **R** - evidence **O** - 4 code lines
- where: src/asy_wifi_service.py:174-176, 317, 407-409
- what: no readable Wi-Fi configuration: the LED blinks 100 ms on / 2900 ms off, obeying LEDWifiOn (the LED setting falls back to its default for it)
- commits: f1f800e7, 72b12815
- origin: A.U18.30 / M.SRC_NET.077, .084, .100
- evidence: O: OR97 (2026-09-29, PROJECT_AUDIT_PLAN.md:464): "19 b"; review wifi-off-led-pattern note: "Generally fine, and as discussed already, this shall respect the general WiFi LED setting (stay silent if turned off, apply whatever current pattern when turned on)" (audit/review/answers.json)
- legacy: no: legacy's LED stays off (async_connect.py:186-189)
- form: design
- depends on: WF-11 (the one flash task)
- device cost: 4 code lines; one flash task while in that state
- minimal change: start the flash task with the inverted pattern in the deactivated branch (~3 lines plus the pattern parameters); pinned by tests/test_asy_wifi_service.py deactivated-pattern tests
- scheme: none

**WF-10** - class **H** - evidence **H** - 3 code lines
- where: src/asy_wifi_service.py:170-172, 511
- what: with a client on the hotspot the LED blinks 1500/1500 ms (was steady on)
- commits: f1f800e7, 72b12815
- origin: SF-M2-04 (agent; REGISTER.md:109 owner-review list)
- evidence: H: REGISTER.md:109: "visibility only, no behaviour change; reversible"
- legacy: no: legacy holds the LED on with a client (async_connect.py:271-276)
- form: design
- depends on: WF-11
- device cost: 3 code lines; one flash task while a client is on
- triage: implausible: no failure behind it, a new visible behaviour
- simplest alternative: pre-audit steady on
- scheme: FEAT (same top-level features, CLAUDE.md:508-511); D1 (flag, don't silently change, SPECIFICATION.md:4765-4766); MIN (minimal change, u35r/briefs/scan_firmware.md:3-5)

**WF-11** - class **H** - evidence **H** - 17 code lines
- where: src/asy_wifi_service.py:455-465, 737-747
- what: one LED flash task, restarted only when the pattern changes; a cancel no longer turns the LED on; a failure persists E23
- commits: f1f800e7, 72b12815
- origin: A.U18.31 RF204; M.SRC_NET.092
- evidence: H: RF204: the cancel handler turns the LED on after the canceller continued (A.U18.31 Why); no failure recorded beyond the LED state
- legacy: no: legacy turns the LED on at cancel (async_connect.py:146-148)
- form: design
- depends on: none (WF-9, WF-10, WF-3 use it)
- device cost: 17 code lines; one task per pattern
- triage: implausible: cosmetic (the LED state after a task restart)
- simplest alternative: pre-audit _flash_led_off()
- scheme: HYP (built on a hypothetical, u35r/briefs/scan_firmware.md:6); MIN (minimal change, u35r/briefs/scan_firmware.md:3-5)

**WF-12** - class **H** - evidence **H** - 8 code lines
- where: src/asy_wifi_service.py:593-594, 600, 772-777
- what: after a lost link the 60 s retry wait sleeps outside wifi_mode_lock
- commits: f1f800e7
- origin: A.U18.32 (1); seed NET.S01
- evidence: H: NET.S01: "wifi_mode_lock is held across asyncio.sleep(60) ... stalling NTP, uptime updates and PUT-triggered reconnects for 60 s"
- legacy: no: legacy sleeps holding the lock (async_connect.py:341-343)
- form: design
- depends on: none
- device cost: 8 code lines; none
- triage: implausible: legacy field behaviour; nothing waiting on the lock needs the link that is down
- simplest alternative: pre-audit
- scheme: HYP (built on a hypothetical, u35r/briefs/scan_firmware.md:6)

**WF-13** - class **H** - evidence **H** - 1 code lines
- where: src/asy_wifi_service.py:631, 636
- what: the connect poll stops at STAT_GOT_IP; ten polls with no verdict persist W81
- commits: f1f800e7
- origin: A.U18.32 (2); SF-M2-03
- evidence: H: no failure recorded
- legacy: no: legacy keeps polling after a join (async_connect.py:311-336)
- form: design
- depends on: none
- device cost: 1 code lines; saves up to 4.5 s of lock hold per join
- triage: implausible: legacy field behaviour
- simplest alternative: pre-audit
- scheme: HYP (built on a hypothetical, u35r/briefs/scan_firmware.md:6); MIN (minimal change, u35r/briefs/scan_firmware.md:3-5)

**WF-14** - class **K** - evidence **H** - 1 code lines
- where: src/asy_wifi_service.py:700
- what: the switch to the hotspot persists W79 (was a console line)
- commits: f1f800e7
- origin: SF-M2-03 (silent-failure scan, 2026-10-06)
- evidence: H: M.SRC_NET.077 (1)
- legacy: no
- form: design: diagnostic
- depends on: none
- device cost: 1 code lines; one FRAM entry per switch
- triage: implausible as a failure; evidence for P7
- simplest alternative: pre-audit pr.one()
- scheme: MIN (minimal change, u35r/briefs/scan_firmware.md:3-5)

**WF-15** - class **H** - evidence **H** - 17 code lines
- where: src/asy_wifi_service.py:248, 826-828, 833-837, 843-850, 949
- what: one networking snapshot per second carries IP, Subnet, Gateway, DNS and RSSI; getters read it; RSSI only on STA with a link; the deactivated state reads nulls without the radio
- commits: f1f800e7
- origin: A.U18.33 RF206; seeds NET.S05, NET.S15
- evidence: H: RF206: "the generated /status networking block mixes the 1 Hz cached WiFi snapshot ... with live lock-gated reads"; review deactivated-snapshot "ok" 2026-10-02 for the deactivated part (audit/review/answers.json)
- legacy: partly: legacy getters read the radio live (async_connect.py:87-104)
- form: design
- depends on: WF-6's _ap_selected
- device cost: 17 code lines; one ifconfig() and one status('rssi') per second under the lock
- triage: implausible: pre-audit lock-skipped getters return null during a connect poll, and NTP could miss the DHCP server once and use the public pair; no failure
- simplest alternative: pre-audit live getters
- scheme: HYP (built on a hypothetical, u35r/briefs/scan_firmware.md:6); P6 (P6 efficient and compact, audit/CONSOLIDATION.md:30)

**WF-16** - class **R** - evidence **O** - 7 code lines
- where: src/asy_wifi_service.py:202, 290-292, 565-569
- what: a stations check that fails (or returns the radio's unfilled 32-entry answer) counts as no client and persists W77
- commits: 01032838
- origin: OR152 / M.SRC_NET.224
- evidence: O: owner, 2026-10-08, to the agent's proposal "the stations check returns to the legacy rule": "yes, record it that way" (M.SRC_NET.224 From); code tag :565
- legacy: partly: legacy counts a failed check as no client, silently (async_connect.py:256-262)
- form: design
- depends on: none
- device cost: 7 code lines; none
- minimal change: keep the pre-audit 'failure = no client' and add the W77 entry (2 lines); pinned by tests/test_asy_wifi_service.py test_get_hotspot_stations_answers_none_for_a_failed_query_and_an_empty_list_for_no_client
- scheme: none

**WF-17** - class **H** - evidence **H** - 7 code lines
- where: src/asy_wifi_service.py:860-864, 874-875
- what: an unreadable WLAN status keeps the link state and uptime and persists W78 each tick (was: counted as down)
- commits: f1f800e7
- origin: SF-B7 (silent-failure scan, 2026-10-06); OF-160
- evidence: H: M.SRC_NET.101 (1): "An unreadable status is unknown, not disconnected"
- legacy: no: legacy resets the uptime on any non-GOT_IP read (async_connect.py:489-494)
- form: design
- depends on: none
- device cost: 7 code lines; none
- triage: implausible: wlan.status() raising was never observed; the pre-audit effect was a one-tick uptime reset
- simplest alternative: pre-audit
- scheme: HYP (built on a hypothetical, u35r/briefs/scan_firmware.md:6); MIN (minimal change, u35r/briefs/scan_firmware.md:3-5)

**WF-18** - class **R** - evidence **O** - 7 code lines
- where: src/asy_wifi_service.py:246-247, 866-869, 966-967
- what: WiFi uptime is measured on ticks (TickSeconds) instead of +1 per 1 s tick
- commits: 41b47f1d
- origin: A.U10.03
- evidence: O: OR104 (2026-09-29, PROJECT_AUDIT_PLAN.md:478): "the \"never UTC\" goes for the others as well and might be a good candidate for a function which lives in the system service or the base classes, whichever fits best"
- legacy: no: legacy increments per tick (async_connect.py:491-494)
- form: design: the shared primitive
- depends on: TickSeconds (group A)
- device cost: 7 code lines; one read per second
- minimal change: read a TickSeconds instead of incrementing (~3 lines); pinned by a driven-clock test: a dropped 1 s tick leaves WifiUptime exact
- scheme: none

**WF-19** - class **H** - evidence **H** - 9 code lines
- where: src/asy_wifi_service.py:675-680, 787-788, 799, 806-807
- what: the hardware streak's participant rung re-selects the current mode, which power-cycles the CYW43, before the task restart
- commits: f1f800e7
- origin: A.U18.R01 (audit/actions/SUPP_recovery.md:732)
- evidence: H: rule only: OR113.a (2) "recover the one participant ... restart the task; reboot" (SUPP_recovery.md:733-736)
- legacy: no
- form: design
- depends on: WF-6's _ap_selected
- device cost: 9 code lines; none unless the streak escalates
- triage: implausible as a gap: the pre-audit ladder already ends in a task restart, then the budget's reboot, which OR18.a accepts for a stalled chip
- simplest alternative: pre-audit ladder
- scheme: HYP (built on a hypothetical, u35r/briefs/scan_firmware.md:6); MIN (minimal change, u35r/briefs/scan_firmware.md:3-5)

**WF-20** - class **R** - evidence **O** - 16 code lines
- where: src/asy_wifi_service.py:287, 310, 451, 464, 536, 547, 555, 608, 646, 721, 803, 817, 839, 848, 891, 901
- what: every broad handler records a caught C-stack overflow
- commits: 06a8ae5d
- origin: A.U30.19 / M.SRC_NET.104
- evidence: O: review c-stack-reboot "ok" (see CD-8)
- legacy: no
- form: design
- depends on: see CD-8
- device cost: 16 code lines; one flag test per caught exception
- minimal change: one call per handler (16 lines); pinned by tests_scripts/test_fatal_report_sites.py
- scheme: none

**WF-21** - class **R** - evidence **O** - 17 code lines
- where: src/asy_wifi_service.py:45-61
- what: error/warning numbers from the global catalog (E60-66, W36-39, W77-81; the missing-config warnings W13)
- commits: 65a0df3b, f1f800e7, 01032838
- origin: A.U2.14
- evidence: O: OR28 (see CD-9)
- legacy: no
- form: design
- depends on: none
- device cost: 17 code lines; none
- minimal change: renumbering; pinned by tests_scripts catalog check
- scheme: none

**WF-22** - class **R** - evidence **O** - 4 code lines
- where: src/asy_wifi_service.py:994-998
- what: setup() sets up the WIFI and DNSSRV loggers in the boot batch (were set up lazily in the connect task)
- commits: 8d44fd14
- origin: A.U10.10 / M.SRC_NET.079
- evidence: O: OR47.a (see NTP-24)
- legacy: no
- form: design
- depends on: none
- device cost: 4 code lines; none
- minimal change: 5 lines; pinned by the twin's boot-order record
- scheme: none

**WF-23** - class **R** - evidence **O** - 0 code lines
- where: src/asy_wifi_service.py (removal)
- what: the connect-verdict episode flag is gone: each verdict warning persists through the logger's newest-entry rule
- commits: 65a0df3b
- origin: A.U3.02
- evidence: O: OR35.a/OR35.b (see NTP-21)
- legacy: no
- form: design: removal (-6 lines)
- depends on: the logger rule (group A)
- device cost: 0 code lines; none
- minimal change: the removal itself; pinned by see NTP-21
- scheme: none

Checked for non-behavioural changes (src/asy_wifi_service.py): compared function by function on the AST-normalised form (the file was reordered by D.15). Not counted: the class rename (`AsyConnTime` -> `WifiService`), the constructor's config object and required hostname/hotspot password (U5, A.U18.40), the removed GPIO-LED `led_pin` path and `set_ext_led()` (no TOML or generated caller, OR36.a (1)), `wlan_isconnected()` removed (tests only, OR46.a (2)), `get_wlan_ifconfig()`/`get_wlan_rssi()` folded into WF-15, `async with` replacing `_release_wifi_lock()`, the named settle constants (same 2 s/1 s/1 s/100 ms/500 ms values), `_PM_NO_POWERSAVE` (same 0xA11140), `_STAT_JOINED_NO_IP` (same 2), the W36 wording, `LedWifiOn` -> `LEDWifiOn`, the `@web` tag lines (HotspotPW published: buildgen's behaviour, not this file's).

### src/asy_webserver_service.py

**WS-1** - class **R** - evidence **O** - 35 code lines
- where: src/asy_webserver_service.py:166-170, 299-303, 358-371, 394-397, 443-460
- what: the request head is bounded before Microdot parses it: at most 32 header lines and 2,048 B, each line within max_readline, read in chunk_bytes pieces; over a bound the connection closes quietly and counts a drop (W61)
- commits: f5c82557
- origin: A.U19.07 / M.SRC_NET.118
- evidence: O: review http-head-limits "ok" 2026-10-01, decision "The web server refuses, quietly, a request with more than 32 header lines or a request line and headers over 2,048 bytes in total, before the memory is allocated." (audit/review/answers.json)
- legacy: no: legacy's Microdot reads lines unbounded and checks max_readline after the read (ext/microdot.py:535)
- form: design: the proxy reads the lines itself so the bound holds before allocation
- depends on: WS-3 (the W61 trace)
- device cost: 35 code lines; per request one bounded buffered read per line
- minimal change: the line and head-byte counters in the proxy's readline() plus the own buffered read (~25 lines); pinned by tests/test_asy_webserver_service.py test_the_header_count_is_bounded, test_a_head_past_its_byte_cap_is_refused_though_each_line_fits
- scheme: none

**WS-2** - class **H** - evidence **H** - 32 code lines
- where: src/asy_webserver_service.py:372-393, 430-442
- what: further head refusals: undecodable bytes, a malformed request line or version, a header without ':', any Transfer-Encoding, a repeated or non-numeric Content-Length, a body cut short
- commits: f5c82557
- origin: A.U19.07; G6/R52
- evidence: H: G6/R52 (A.U19.07 Why): "a negative, huge, non-numeric or duplicate Content-Length is refused outside ext/ ... chunked bodies and Expect: 100-continue are answered cleanly"; no failure recorded
- legacy: no
- form: design: validation
- depends on: WS-1
- device cost: 32 code lines; per header line a few string tests
- triage: implausible: on the trusted LAN (OR52.a (3)) a non-numeric length raises inside Microdot's own catch, a negative one loops in readexactly() (extmod/asyncio/stream.py:42-52, v1.29.0) until the pre-audit proxy's per-call timeout reclaims it, and a chunked body reaches the handler empty and answers ERR
- simplest alternative: WS-1's bounds alone
- scheme: HYP (built on a hypothetical, u35r/briefs/scan_firmware.md:6); MIN (minimal change, u35r/briefs/scan_firmware.md:3-5)

**WS-3** - class **R** - evidence **O** - 14 code lines
- where: src/asy_webserver_service.py:108, 114-115, 919-926, 949-953
- what: every connection dropped before a response leaves a trace: refused at the ceiling (W60), head refused (W61), reset by the peer (W48)
- commits: f5c82557
- origin: A.U19.08 / M.SRC_NET.127
- evidence: O: OR102 (PROJECT_AUDIT_PLAN.md:474): "9. c", integrated as OR102.a (9): "dropped connections get detection logging so a repeat leaves evidence (H2.99)"
- legacy: no
- form: design
- depends on: none
- device cost: 14 code lines; one FRAM entry per drop (the newest-entry rule folds a run)
- minimal change: one wrn_s per drop path (~6 lines); pinned by tests/test_asy_webserver_service.py test_a_client_gone_mid_response_counts_one_drop
- scheme: none

**WS-4** - class **R** - evidence **O** - 6 code lines
- where: src/asy_webserver_service.py:592, 799-801, 1044-1046, 1068
- what: HTTPDropped: the drops of the last 24 hours in hourly bins, cleared by ResetErrors
- commits: f5c82557
- origin: OR137 / M.SRC_NET.119, .129
- evidence: O: OR137 (2026-10-01, PROJECT_AUDIT_PLAN.md:544): "ResetErrors shall clear it, but more important: I would like the idea of showing the last 24h sliding through ... Maybe something like using 24 hourly counter bins, shifting through, with 1h resolution (that would be enough)?"
- legacy: no
- form: design
- depends on: WS-3; HourlyWindowCounter and the uptime reader (group A)
- device cost: 6 code lines; one 24-int array at construction; per drop or read a lazy bin shift
- minimal change: as is (~6 lines here); pinned by tests/test_asy_webserver_service.py test_dropped_connections_leave_the_count_after_a_day, test_reset_errors_clears_the_dropped_count
- scheme: none

**WS-5** - class **K** - evidence **H** - 6 code lines
- where: src/asy_webserver_service.py:335-340, 942
- what: a per-call timeout (W49) is told apart from the 15 s request cap (W50)
- commits: 43aced07, f5c82557
- origin: A.U2.19 (catalog)
- evidence: H: no failure recorded
- legacy: no
- form: design: diagnostic
- depends on: none
- device cost: 6 code lines; one flag per connection
- triage: implausible as a failure: a code split
- simplest alternative: pre-audit one W2
- scheme: MIN (minimal change, u35r/briefs/scan_firmware.md:3-5)

**WS-6** - class **C** - evidence **O** - 5 code lines
- where: src/asy_webserver_service.py:994-1000
- what: each trace a connection awaits before its close is held at most one per-call timeout (an entry cut short stays in RAM)
- commits: 656fc82f
- origin: OF-254 (U35 gate 1, G1b; LEAD NOTES 105-106)
- evidence: O: OF-254: "a refused connection's close waits on its FRAM trace with no bound, past a client's 10 s timeout under FRAM-log writes and flash holds" (open_findings.md:262); owner, 2026-10-22: "Solutions you proposed agreed." (656fc82f message)
- legacy: no
- form: patch: a timed wait around a log write, around the FRAM latency WS-3's traces meet
- depends on: WS-3
- device cost: 5 code lines; one wait_for_ms task per trace before a close
- triage: owner-agreed; it exists because WS-3's traces sit on the close path
- simplest alternative: trace after the close, or no trace on the refusal path
- scheme: CASC (cascade, u35r/briefs/scan_firmware.md:7); PATCH (patch, not design, u35r/briefs/inv_firmware_additions.md:2-4); DELAY (hardcoded delay/timing check, u35r/briefs/scan_firmware.md:106-107)

**WS-7** - class **H** - evidence **H** - 8 code lines
- where: src/asy_webserver_service.py:424-428, 461-465, 536, 955
- what: a static file the route opened is held by the connection and closed at its end, HEAD and aborted responses included
- commits: f5c82557
- origin: A.U19.06; seeds REST.S07, REST.S08
- evidence: H: G6/R42: "HEAD and aborted static responses close their stream"; no failure recorded
- legacy: no
- form: design
- depends on: none
- device cost: 8 code lines; none
- triage: implausible: an unclosed file object is closed by its finaliser at the next collection (SPECIFICATION.md:6338-6341: finalisers are on at rp2's ROM level) and static files are read-only
- simplest alternative: pre-audit Microdot send_file close
- scheme: HYP (built on a hypothetical, u35r/briefs/scan_firmware.md:6); MIN (minimal change, u35r/briefs/scan_firmware.md:3-5)

**WS-8** - class **R** - evidence **O** - 1 code lines
- where: src/asy_webserver_service.py:541
- what: static files carry Cache-Control: no-cache (revalidated on every visit)
- commits: f5c82557
- origin: A.U19.06
- evidence: O: review static-no-cache "ok" 2026-10-01, decision "Static pages are revalidated on every visit" (audit/review/answers.json); code tag :541
- legacy: no
- form: design
- depends on: none
- device cost: 1 code lines; one header per static response
- minimal change: 1 line; pinned by tests/test_asy_webserver_service.py test_a_static_get_answers_cache_control_no_cache
- scheme: none

**WS-9** - class **H** - evidence **H** - 11 code lines
- where: src/asy_webserver_service.py:564, 804-814, 349
- what: Microdot's exception prints are rebound: a C-stack check, a timeout the proxy already traced skipped, a MemoryError to console(), the rest through the level-gated logger
- commits: f5c82557, 06a8ae5d
- origin: SF-M4-01 (b) (agent; REGISTER.md:110 owner-review list); OF-97
- evidence: H: REGISTER.md:110: "DebugLevel 0 then keeps the console quiet"; A.U19.23: client-triggered output can stall on a non-reading USB host
- legacy: no: legacy's Microdot prints every exception
- form: design
- depends on: none
- device cost: 11 code lines; none
- triage: implausible on these devices: the console stall needs an attached, non-reading USB CDC host, which field units (USB power only) do not have
- simplest alternative: Microdot's own print
- scheme: HYP (built on a hypothetical, u35r/briefs/scan_firmware.md:6); MIN (minimal change, u35r/briefs/scan_firmware.md:3-5)

**WS-10** - class **K** - evidence **H** - 2 code lines
- where: src/asy_webserver_service.py:200-201
- what: a heap failure while decoding the JSON body reaches the catch-all (500, E23 persisted) instead of 'Invalid JSON'
- commits: 06a8ae5d
- origin: OF-98 (U19 lane WS scan)
- evidence: H: OF-98: "_body_as_dict()'s MemoryError ('Invalid JSON') are printed only"
- legacy: no
- form: design: diagnostic
- depends on: none
- device cost: 2 code lines; none
- triage: implausible as a failure
- simplest alternative: pre-audit ERR answer
- scheme: MIN (minimal change, u35r/briefs/scan_firmware.md:3-5)

**WS-11** - class **H** - evidence **H** - 18 code lines
- where: src/asy_webserver_service.py:171-175, 970-992
- what: a failed server start is retried three times, 5 s apart; the first and the last failure persist W62
- commits: f5c82557, 06a8ae5d
- origin: A.U19.09; OF-98
- evidence: H: rule only: OR113 (PROJECT_AUDIT_PLAN.md:496) "Apply this idea throughout!" (A.U19.09 Why); no start failure recorded (searched open_findings.md and REGISTER.md for start_server)
- legacy: no: legacy starts once (legacy/firmware/modules/sensortask-wozi.py:98)
- form: design
- depends on: none
- device cost: 18 code lines; up to 10 s of retries at boot when it fails
- triage: implausible: start_server() fails only on a socket/bind failure at boot; pre-audit the task then ends and the supervisor restarts it (OR18.a's ladder)
- simplest alternative: pre-audit single start
- scheme: HYP (built on a hypothetical, u35r/briefs/scan_firmware.md:6); DELAY (hardcoded delay/timing check, u35r/briefs/scan_firmware.md:106-107); MIN (minimal change, u35r/briefs/scan_firmware.md:3-5)

**WS-12** - class **R** - evidence **O** - 1 code lines
- where: src/asy_webserver_service.py:126
- what: SystemCmd accepts two new words: resetconfig and erasefram
- commits: f76385a6
- origin: A.S0930.09 / M.SRC_NET.121
- evidence: O: OR138 (2026-10-01, PROJECT_AUDIT_PLAN.md:546): "... must be deletable by the user when triggering the newly added \"delete config\" command."; review system-command-words "ok" (audit/review/answers.json)
- legacy: no: legacy knows reboot, bootloader, mempause (legacy/firmware/modules/sensortask-wozi.py:519)
- form: design: a feature
- depends on: the shutdown sequence (buildgen/system service)
- device cost: 1 code lines; none
- minimal change: two words in the tuple (1 line); the commands themselves are group A's; pinned by tests/test_asy_webserver_service.py test_each_system_command_over_put_system_reaches_its_reset_arm_without_a_lock_held
- scheme: none

**WS-13** - class **R** - evidence **O** - 5 code lines
- where: src/asy_webserver_service.py:478, 571, 862-867
- what: ResetErrors clears nothing and answers Failed while a refusal holds (the FRAM manager's memory pause, the system's reset decision)
- commits: 06a8ae5d
- origin: U30 / M.SRC_NET.123
- evidence: O: owner, 2026-10-13: "1 b, 2 b", to "Clear nothing when ResetErrors answers Failed in mempause?" and "Refuse ResetErrors from the supervisor's own reboot decision too?" (06a8ae5d message; code tag :863-865)
- legacy: no
- form: design
- depends on: the refusal callables (group A)
- device cost: 5 code lines; one callable per ResetErrors
- minimal change: one `if any(refused()...)` before the resets (~3 lines) and the callables passed in; pinned by tests/test_asy_webserver_service.py ResetErrors refusal tests
- scheme: none

**WS-14** - class **R** - evidence **O** - 1 code lines
- where: src/asy_webserver_service.py:871
- what: ResetErrors resets every log concurrently (was one after another)
- commits: 9bf22747
- origin: A.U11.31 / M.SRC_NET.123
- evidence: O: code tag :868-869 quoting the owner, 2026-09-26: "`ResetErrors` resets the FRAM-backed logs concurrently rather than one after another" (OR72.a (1))
- legacy: no
- form: design
- depends on: none
- device cost: 1 code lines; one gather of N coroutines
- minimal change: the pre-audit loop -> one asyncio.gather() (2 lines); pinned by tests/test_asy_webserver_service.py concurrent ResetErrors test
- scheme: none

**WS-15** - class **K** - evidence **H** - 9 code lines
- where: src/asy_webserver_service.py:872-880
- what: each reset that raised persists E14 after the others ran, and the key answers Failed
- commits: 9bf22747
- origin: OF-99 (U19 lane E scan)
- evidence: H: OF-99: "a raise ... answers 500 with E23 and leaves the other resets running unawaited, so the operator cannot tell which logs were cleared"
- legacy: no
- form: design
- depends on: WS-14
- device cost: 9 code lines; none
- triage: implausible: a reset raises only with the heap near full; the finding is real by reading
- simplest alternative: gather without return_exceptions
- scheme: MIN (minimal change, u35r/briefs/scan_firmware.md:3-5)

**WS-16** - class **R** - evidence **O** - 9 code lines
- where: src/asy_webserver_service.py:692-697, 841-843, 859-861
- what: every PUT key gets an answer: an unknown key or sensor reads Invalid (was omitted)
- commits: f5c82557
- origin: A.U19.01 / M.SRC_NET.120
- evidence: O: review api-unknown-key-invalid "ok" 2026-10-01, decision "Every PUT key gets an answer; unknown keys read Invalid" (audit/review/answers.json)
- legacy: partly: legacy answers an unknown command 'Invalid command' (legacy/firmware/python/CommonDrivers/api_helpers.py:133)
- form: design
- depends on: none
- device cost: 9 code lines; per PUT one membership test per key
- minimal change: one loop marking keys no group lists (~5 lines); pinned by tests/test_asy_webserver_service.py test_sensors_put_unknown_sensor_key_answers_invalid
- scheme: none

**WS-17** - class **R** - evidence **O** - 34 code lines
- where: src/asy_webserver_service.py:140-146, 744-765, 822-832
- what: LightCmdLED is validated here (exactly R, G, B 0-255 and T 0.5-60 s); a running signal refuses it with Failed and the descr 'LED busy - retry later'
- commits: f5c82557
- origin: A.U19.02 / M.SRC_NET.122
- evidence: O: OR102 (PROJECT_AUDIT_PLAN.md:474): "5. a", integrated as OR102.a (5): "an LED command while a signal runs is refused at once with \"Failed\" (legacy's \"LED is busy\" in the new envelope)"; code tag :763 (owner, 2026-10-02)
- legacy: yes: legacy validates r/g/b 0-255, t 0.5-60 and answers 'LED is busy' (legacy/firmware/modules/sensortask-wozi.py:402-418)
- form: design: legacy parity
- depends on: none
- device cost: 34 code lines; per LED command four checks
- minimal change: as is, the legacy bounds in the dispatcher (~15 lines); pinned by tests/test_asy_webserver_service.py LightCmdLED validation and busy tests
- scheme: none

**WS-18** - class **K** - evidence **H** - 2 code lines
- where: src/asy_webserver_service.py:658-659
- what: a flat settings GET sends the unavailable marker for each field of a module whose config cannot be read
- commits: f5c82557, 18b9ff67 (F1r)
- origin: SF-B8 (agent; REGISTER.md:832)
- evidence: H: REGISTER.md:832: "a config GET after a chip-read failure returns null fields indistinguishable from 'not set'"
- legacy: no
- form: design
- depends on: the marker producers (group A)
- device cost: 2 code lines; none
- triage: implausible as a failure: a display ambiguity; F1r later tightened its own key test (a cascade inside the row)
- simplest alternative: pre-audit null fields
- scheme: MIN (minimal change, u35r/briefs/scan_firmware.md:3-5); CASC (cascade, u35r/briefs/scan_firmware.md:7)

**WS-19** - class **H** - evidence **H** - 2 code lines
- where: src/asy_webserver_service.py:252-253
- what: a non-finite float is written as null
- commits: f5c82557
- origin: A.U10.27 (rule agent, 2026-09-24)
- evidence: H: A.U10.27: "json.dumps() ... writes bare nan/inf that browsers and MicroPython's own json.load() reject"
- legacy: no: legacy json.dumps writes bare nan
- form: design
- depends on: the drivers' own gates (group A)
- device cost: 2 code lines; one isinstance per value
- triage: implausible here: the float sources are gated upstream by A.U10.27's per-route check (group A's rows); this is a second gate
- simplest alternative: none
- scheme: HYP (built on a hypothetical, u35r/briefs/scan_firmware.md:6); MIN (minimal change, u35r/briefs/scan_firmware.md:3-5)

**WS-20** - class **H** - evidence **H** - 14 code lines
- where: src/asy_webserver_service.py:224-233, 257-260, 1076-1086
- what: streamed GET pieces are encoded once, as bytes; Microdot gets that one copy
- commits: f5c82557
- origin: A.U19.11; G4/R43; seed REST.S06
- evidence: H: A.U19.11: "_PieceWriter counts characters today"; M.SRC_NET.115: one encoded copy; no failure recorded
- legacy: no: legacy returns the dict for one json.dumps()
- form: design: allocation
- depends on: none
- device cost: 14 code lines; halves a streamed response's held bytes
- triage: suspicious as recorded ('a full encoded copy' per streamed GET, M.SRC_NET.115); checked in V4: refuted as a held copy - the str list is garbage once the pre-audit _pieces_response() returns, so only a transient 2x peak during the encode remains
- verification: V4, refuted as stated
- simplest alternative: pre-audit encode in _pieces_response()
- scheme: HYP (built on a hypothetical, u35r/briefs/scan_firmware.md:6); MIN (minimal change, u35r/briefs/scan_firmware.md:3-5)

**WS-21** - class **R** - evidence **O** - 3 code lines
- where: src/asy_webserver_service.py:916-917, 956-962
- what: the connection task has a top: what escapes the request persists 'Connection task failed' (E23)
- commits: 970b63ba
- origin: U32 / M.SRC_NET.127
- evidence: O: owner, 2026-10-21: "The task logs shall then be handled by their creators in general and the caveats are okay as they are inevitable." (970b63ba message)
- legacy: no
- form: design
- depends on: none
- device cost: 3 code lines; none
- minimal change: one outer try/except (~5 lines); pinned by tests_scripts/test_task_tops.py
- scheme: none

**WS-22** - class **H** - evidence **H** - 5 code lines
- where: src/asy_webserver_service.py:915, 919, 924, 967-968
- what: the open-connection count is released only if it was taken
- commits: f5c82557
- origin: M.SRC_NET.127
- evidence: H: no failure recorded
- legacy: no
- form: design
- depends on: WS-21
- device cost: 5 code lines; none
- triage: implausible: the increment cannot raise but on an exhausted heap
- simplest alternative: pre-audit order
- scheme: HYP (built on a hypothetical, u35r/briefs/scan_firmware.md:6)

**WS-23** - class **R** - evidence **O** - 7 code lines
- where: src/asy_webserver_service.py:203, 809, 877, 896, 909, 947, 961
- what: every broad handler records a caught C-stack overflow
- commits: 06a8ae5d
- origin: A.U30.19
- evidence: O: review c-stack-reboot "ok" (see CD-8)
- legacy: no
- form: design
- depends on: see CD-8
- device cost: 7 code lines; one flag test per caught exception
- minimal change: one call per handler; pinned by tests_scripts/test_fatal_report_sites.py
- scheme: none

**WS-24** - class **R** - evidence **O** - 15 code lines
- where: src/asy_webserver_service.py:106-116, 177, 1101-1105
- what: catalog numbers (E14/23, W48-53, W60-62); a shaped HTTP error carries its status as envelope code, without descr
- commits: 43aced07, f5c82557
- origin: A.U2.19, A.U19.15
- evidence: O: OR28 (see CD-9); review envelope-codes-equal-http "ok" 2026-10-02 (audit/review/answers.json)
- legacy: no
- form: design
- depends on: none
- device cost: 15 code lines; none
- minimal change: renumbering; pinned by tests_scripts catalog check
- scheme: none

**WS-25** - class **R** - evidence **O** - 3 code lines
- where: src/asy_webserver_service.py:1071-1074
- what: setup() sets up the logger in the boot batch (was lazily in the serve task)
- commits: 8d44fd14, f76385a6
- origin: A.U10.10
- evidence: O: OR47.a (see NTP-24)
- legacy: no
- form: design
- depends on: none
- device cost: 3 code lines; none
- minimal change: 3 lines; pinned by the twin's boot-order record
- scheme: none

**WS-26** - class **R** - evidence **O** - 15 code lines
- where: src/asy_webserver_service.py:572, 855-858, 892-899, 1062-1065
- what: PUT /status runs registered dispatch-only commands (dev's UART hazard trigger)
- commits: 656fc82f
- origin: the UART hazard mode (UL-1)
- evidence: O: see UL-1
- legacy: no
- form: design: plumbing of UL-1
- depends on: UL-1
- device cost: 15 code lines; none
- minimal change: as is with UL-1; pinned by tests/test_asy_webserver_service.py status-command tests
- scheme: none

Checked for non-behavioural changes (src/asy_webserver_service.py): compared function by function on the AST-normalised form. Not counted: the three config objects (U5), the one ROUTES table (same eleven routes), `_StaticRoutes` (the same serve logic moved into a class; its stream hold is WS-7, its header WS-8), ms timeouts (same 5 s/15 s), `SystemCmd` matched by loop (the same whole-string equality as `in`), PauseTime through `checked_int()` (the shared validator for the same 0-3600 int range), the typing protocols and aliases, `_cfg_values()` (the one nested shape the flatten handled), the result-word constants (U19).

### src/asy_uart_comm.py

**UC-1** - class **R** - evidence **O** - 11 code lines
- where: src/asy_uart_comm.py:116, 266-268, 295-297, 472-475, 635-639
- what: a received train (SET, or a GET's answer) declaring more than max_transfer_bytes (default 12,192) is refused before anything is allocated (E93, ACK withheld)
- commits: c11ca0aa
- origin: M.SRC_NET.220; OR143.a (2)
- evidence: O: OR143 (2026-10-05, PROJECT_AUDIT_PLAN.md:556): "I want one parked item to be fixed: the UART chunking for large allocations. ... A general maximum buffer size, catching uncapped heap flooding in general if too large incoming transmissions occur, is also to be implemented"
- legacy: no: legacy grows one bytearray per chunk, uncapped (legacy/firmware/python/IndividualDrivers/asy_uart_comm.py:117-140)
- form: design (changelog Class A, receiver side)
- depends on: none
- device cost: 11 code lines; one comparison per received train header
- minimal change: one constructor value and one check before the ACK in _accept_set()/_get_unlocked() (~6 lines); pinned by tests/test_asy_uart_comm.py receive-cap refusal tests
- scheme: none

**UC-2** - class **X** - evidence **H** - 8 code lines
- where: src/asy_uart_comm.py:435-442, 848, 1188, 1208
- what: this end's own initiator also refuses to send or request a train over the cap
- commits: c11ca0aa, 970b63ba
- origin: M.SRC_NET.220; U32 ("a size over the sender's cap is the cap's refusal at every cap the build allows")
- evidence: H: no failure recorded; OR143 names incoming transmissions only
- legacy: no
- form: design
- depends on: UC-1
- device cost: 8 code lines; one comparison per call
- triage: implausible: the peer refuses an oversize train itself (UC-1); the sender check only names the cause earlier
- simplest alternative: UC-1 alone
- scheme: MIN (minimal change, u35r/briefs/scan_firmware.md:3-5); HYP (built on a hypothetical, u35r/briefs/scan_firmware.md:6)

**UC-3** - class **R** - evidence **O** - 18 code lines
- where: src/asy_uart_comm.py:114, 277-279, 318, 323, 776-783, 1108-1119
- what: a train with no caller buffer arrives in PieceBuffer pieces of at most chunk_bytes (256); uart_get() returns that PieceBuffer
- commits: c11ca0aa
- origin: M.SRC_NET.220; OR143.a (1)
- evidence: O: OR143 (2026-10-05, PROJECT_AUDIT_PLAN.md:556): "I want one parked item to be fixed: the UART chunking for large allocations. ... A general maximum buffer size, catching uncapped heap flooding in general if too large incoming transmissions occur, is also to be implemented"
- legacy: no
- form: design
- depends on: PieceBuffer (group A)
- device cost: 18 code lines; pieces of 256 B instead of one peer-sized block
- minimal change: as is (~15 lines here); pinned by tests/test_asy_uart_comm.py largest-receive-allocation test
- scheme: none

**UC-4** - class **R** - evidence **O** - 6 code lines
- where: src/asy_uart_comm.py:280-282, 319-321
- what: a PieceBuffer that cannot be built is a UART fault (E20 ALLOC, resync), not a raise
- commits: 1d2b3cca
- origin: UM2; OR143 follow-up
- evidence: O: owner, 2026-10-27: "Do option (c) as you recommended" (S/u35r/recovered/owner_rulings_after_LN118.md, PieceBuffer's UART callers and a MemoryError)
- legacy: no
- form: design
- depends on: UC-3
- device cost: 6 code lines; none
- minimal change: 2 x 3 lines; pinned by tests/test_asy_uart_comm.py the three fault-flow tests of 1d2b3cca
- scheme: none

**UC-5** - class **C** - evidence **F** - 9 code lines
- where: src/asy_uart_comm.py:372, 892-899
- what: a responder may answer a GET with a PieceBuffer; its chunks are copied by index into the TX frame
- commits: 3a24c773, d57ad57b
- origin: UM2
- evidence: F: 3a24c773: "measured at the receive cap, one 12,192-byte allocation per GET served" (test red: [12192]); the pre-audit echo made the same peer-sized copy (`bytes(self.last_echo or b'')`, src/asy_uart_link_driver.py@25caf528)
- legacy: no
- form: design
- depends on: UC-3 (the pieces it sends from)
- device cost: 9 code lines; no peer-sized copy per GET
- triage: completes OR143's bound on the send side; dev-only (the link exerciser's echo is its one user)
- simplest alternative: the echo bounded by a smaller cap
- scheme: CASC (cascade, u35r/briefs/scan_firmware.md:7)

**UC-6** - class **H** - evidence **H** - 2 code lines
- where: src/asy_uart_comm.py:997-998
- what: a GET frame declaring CHUNKS other than 1 is refused (changelog Class A, receiver side)
- commits: c11ca0aa
- origin: A.U17.16 (UART.S02)
- evidence: H: J.4 (owner-confirmed Part J, 2026-09-11): "the initiator sends a one-chunk GET train"; no failure recorded
- legacy: no
- form: design: validation
- depends on: none
- device cost: 2 code lines; one comparison per GET
- triage: implausible: no initiator, this one or the C peer's, sends another form
- simplest alternative: pre-audit
- scheme: HYP (built on a hypothetical, u35r/briefs/scan_firmware.md:6)

**UC-7** - class **H** - evidence **H** - 1 code lines
- where: src/asy_uart_comm.py:393
- what: a write hold-off older than the resync window expires (stays inside ticks_diff()'s horizon)
- commits: c11ca0aa
- origin: A.U17.06 (G5/R10)
- evidence: H: A.U17.06: "_holdoff_active stale after >6.2 days idle is a defect"; no failure recorded
- legacy: no
- form: design
- depends on: none
- device cost: 1 code lines; one comparison per gated write
- triage: implausible on these devices: dev's exerciser transacts every second, so no hold-off ages 6.2 days
- simplest alternative: pre-audit
- scheme: HYP (built on a hypothetical, u35r/briefs/scan_firmware.md:6)

**UC-8** - class **X** - evidence **H** - 22 code lines
- where: src/asy_uart_comm.py:592-594, 959-976, 981-984
- what: construction refuses a delimited codec too small for a frame (E92), a timeout past the ticks horizon, a poll interval outside 1-9 ms (E91), a bad chunk_bytes or max_transfer_bytes
- commits: c11ca0aa
- origin: A.U17.20, A.U17.22 (UART.S08, RF215)
- evidence: H: RF215: "latent while production selects Framing_Pass" (A.U17.22 Why)
- legacy: no
- form: design
- depends on: buildgen refuses the same bounds at build (A.U17.21)
- device cost: 22 code lines; at construction
- triage: implausible: buildgen refuses the same values first, and dev's TOML fixes them
- simplest alternative: the build check alone
- scheme: MIN (minimal change, u35r/briefs/scan_firmware.md:3-5); P8 (P8 one source of truth, audit/CONSOLIDATION.md:32); HYP (built on a hypothetical, u35r/briefs/scan_firmware.md:6)

**UC-9** - class **R** - evidence **O** - 12 code lines
- where: src/asy_uart_comm.py:235, 657-660, 813, 904-912, 1098
- what: bytes a failed frame read dropped count toward the resync's drained total, so the 'bytes but no valid frame' diagnostic (E89) also fires for a speak-when-spoken-to peer
- commits: c11ca0aa
- origin: A.U17.13; OR70.a (5) B07
- evidence: O: OR70 (2026-09-26, PROJECT_AUDIT_PLAN.md:410): "5. b", integrated as OR70.a (5): "B07: the UART error-32 blind spot is fixed"
- legacy: no
- form: design
- depends on: UD-3 (the driver's count)
- device cost: 12 code lines; none
- minimal change: read the driver's discard count into the resync total (~5 lines); pinned by tests/test_asy_uart_comm.py E89 for a speak-when-spoken-to peer
- scheme: none

**UC-10** - class **K** - evidence **H** - 16 code lines
- where: src/asy_uart_comm.py:569-573, 706-709, 752-755, 1020-1023
- what: a read that dropped a corrupted or incomplete frame says so in its fault text, apart from a silence
- commits: 970b63ba
- origin: OF-210 (U32)
- evidence: H: no failure recorded
- legacy: no
- form: design: diagnostic
- depends on: UC-9
- device cost: 16 code lines; two counter reads per frame read
- triage: implausible as a failure: a log text
- simplest alternative: pre-audit texts
- scheme: MIN (minimal change, u35r/briefs/scan_firmware.md:3-5)

**UC-11** - class **K** - evidence **H** - 4 code lines
- where: src/asy_uart_comm.py:149, 727, 735-736
- what: a frame read during which the receive ring overran persists W57
- commits: c11ca0aa
- origin: OF-37 (U13 lane U scan)
- evidence: H: OF-37: "neither the log nor a REST client can tell an overrun from a silent peer"
- legacy: no
- form: design: diagnostic
- depends on: UD-1
- device cost: 4 code lines; one counter read per frame read
- triage: implausible as a failure
- simplest alternative: none
- scheme: MIN (minimal change, u35r/briefs/scan_firmware.md:3-5); CASC (cascade, u35r/briefs/scan_firmware.md:7)

**UC-12** - class **R** - evidence **O** - 12 code lines
- where: src/asy_uart_comm.py:99, 596-608, 986
- what: the receive ring must hold what the peer can send during the longest flash hold (2,129 ms traced) - else construction refuses (E78)
- commits: c11ca0aa
- origin: M.SRC_NET.222; OR141.a (4) (e)
- evidence: O: OR141 (2026-10-05, PROJECT_AUDIT_PLAN.md:552): "do all as you suggested ... and UART in the DMA ring buffer"; OR141.a (4) (e): "Size: the larger of today's floors ... and what the peer can send during the longest synchronous flash write"
- legacy: no
- form: design
- depends on: UD-1
- device cost: 12 code lines; at construction
- minimal change: as is (~8 lines); pinned by tests/test_asy_uart_comm.py test_the_ring_floor_covers_a_config_flush
- scheme: none

**UC-13** - class **R** - evidence **O** - 7 code lines
- where: src/asy_uart_comm.py:507-511, 1090-1092
- what: setup() allocates the DMA ring (in the boot batch) and names a refusal's cause; the drain continues past an overrun
- commits: c11ca0aa
- origin: OR143.a (5); OF-38
- evidence: O: OR143: "Special care must be taken for the ring buffer allocation, this should probably happen during the init phase where the long term survivor allocations are done"
- legacy: no
- form: design
- depends on: UD-1
- device cost: 7 code lines; once at boot
- minimal change: as is; pinned by tests/test_asy_uart_comm.py test_a_ring_refused_at_setup_names_its_cause
- scheme: none

**UC-14** - class **R** - evidence **O** - 9 code lines
- where: src/asy_uart_comm.py:517-519, 802-806, 817-820
- what: the episode budget and the repeat-errno dedupe are gone: every fault persists its errno, a resync only prints, each declined command persists W56
- commits: 65a0df3b, 43aced07
- origin: A.U3.02, A.U3.08
- evidence: O: OR56 (1) (PROJECT_AUDIT_PLAN.md:382): "'each UART fault writes an error entry and a warning entry into one shared log' - that's already conceptually wrong. Either it's a fault or a warning, but never both at a time."; OR35.b (see NTP-21)
- legacy: no
- form: design: removal (-40 lines)
- depends on: the logger rule (group A)
- device cost: 9 code lines; none
- minimal change: the removal itself; pinned by tests_scripts/test_fault_or_warning_never_both.py
- scheme: none

**UC-15** - class **H** - evidence **H** - 2 code lines
- where: src/asy_uart_comm.py:548, 560
- what: a declined (validated) command resets the listen backoff instead of backing off
- commits: c11ca0aa
- origin: A.U17.17 (UART.S05)
- evidence: H: UART.S05: "sending _listen_loop into backoff up to 5x timeout while the initiator may already be retrying"
- legacy: no
- form: design
- depends on: none
- device cost: 2 code lines; none
- triage: implausible: dev declines only during the hazard sweep, and J.5's retry recovers
- simplest alternative: pre-audit
- scheme: HYP (built on a hypothetical, u35r/briefs/scan_firmware.md:6)

**UC-16** - class **H** - evidence **H** - 2 code lines
- where: src/asy_uart_comm.py:867, 1017
- what: frame and ACK writes are bounded by the link timeout
- commits: c11ca0aa
- origin: OF-39
- evidence: H: OF-39: "waits poll_wait_ms per round while txdone() is false, with no deadline of its own"
- legacy: no
- form: design
- depends on: UD-4
- device cost: 2 code lines; none
- triage: implausible: with no flow control the TX ring always drains at the baud rate
- simplest alternative: pre-audit
- scheme: HYP (built on a hypothetical, u35r/briefs/scan_firmware.md:6)

**UC-17** - class **R** - evidence **O** - 4 code lines
- where: src/asy_uart_comm.py:631-632, 827-828
- what: valid_frames and blind_resyncs stop at their caps
- commits: c11ca0aa, 41b47f1d
- origin: A.U10.04, A.U17.14
- evidence: O: OR103 (2026-09-29, PROJECT_AUDIT_PLAN.md:476): "No unbounded counters anywhere."; OR105: "all candidates for such counters must be found"
- legacy: no
- form: design
- depends on: none
- device cost: 4 code lines; one comparison per step
- minimal change: check-before-step (2 x 1 line); pinned by counter-cap tests (tests_scripts/test_counter_steps.py)
- scheme: none

**UC-18** - class **H** - evidence **H** - 4 code lines
- where: src/asy_uart_comm.py:630-633
- what: per-frame bookkeeping is a plain function (no coroutine per received frame)
- commits: 41b47f1d
- origin: M.SRC_NET.164
- evidence: H: review uart-valid-frame-sync (routine, unanswered)
- legacy: no
- form: design: allocation
- depends on: none
- device cost: 4 code lines; one coroutine less per frame
- triage: implausible as a failure; a small allocation saving (P6)
- simplest alternative: pre-audit
- scheme: none

**UC-19** - class **R** - evidence **O** - 11 code lines
- where: src/asy_uart_comm.py:1108-1110, 1121-1123, 1134-1136, 1197-1207
- what: the six initiator entry points check role first, then arguments
- commits: c11ca0aa
- origin: A.U17.01
- evidence: O: OR24.a (1) (PROJECT_AUDIT_PLAN.md:317): "Within the audit, OR24 is the owner's advance authorisation for consistency changes (naming, ordering, signatures, uniform behaviour of equivalent methods)"
- legacy: no
- form: design: consistency
- depends on: none
- device cost: 11 code lines; none
- minimal change: reorder; pinned by tests/test_asy_uart_comm.py entry-point order tests
- scheme: none

**UC-20** - class **R** - evidence **O** - 3 code lines
- where: src/asy_uart_comm.py:1075-1079
- what: ResetErrors clears the log only (no longer the frame count and the declined-id map)
- commits: 43aced07, 8d44fd14
- origin: A.U3.02, A.U11.31
- evidence: O: OR35.a/OR35.b (see NTP-21)
- legacy: no
- form: design: removal
- depends on: UC-14
- device cost: 3 code lines; none
- minimal change: the removal itself; pinned by see UC-14
- scheme: none

**UC-21** - class **R** - evidence **O** - 3 code lines
- where: src/asy_uart_comm.py:348, 422, 563
- what: a scratch-buffer allocation failure prints its text; the two broad handlers record a C-stack overflow
- commits: 06a8ae5d
- origin: A.U30.19; OF-77 family
- evidence: O: review c-stack-reboot "ok" (see CD-8) for the handlers
- legacy: no
- form: design
- depends on: see CD-8
- device cost: 3 code lines; none
- minimal change: 3 lines; pinned by tests_scripts/test_fatal_report_sites.py
- scheme: none

**UC-22** - class **R** - evidence **O** - 29 code lines
- where: src/asy_uart_comm.py:120-149
- what: error/warning numbers from the global catalog (E75-93, W54-57; were 10-34, W10-14)
- commits: 43aced07, c11ca0aa
- origin: A.U2.20
- evidence: O: OR28 (see CD-9)
- legacy: no
- form: design
- depends on: none
- device cost: 29 code lines; none
- minimal change: renumbering (no wire byte changes); pinned by tests_scripts catalog check
- scheme: none

Checked for non-behavioural changes (src/asy_uart_comm.py): AST-normalised diff read in full plus the UM2/UM4/D2S lane diffs. Not counted: `UART_Comm` -> `UARTComm`, the callbacks and limits objects (U5), `CMD_ACK`/`CMD_GET` made private, `LockableBuffer` -> `RegionBuffer` (group A), the starter rename, `_check_buffer()` narrowed (D2S, typing only), `_call()` passing **kwargs, the comments and Part J pointers. No wire byte changed in the range (every UM2 and U17 commit states it; UART_C_PORT_CHANGELOG.md carries the rows).

### src/asy_uart_driver.py

**UD-1** - class **R** - evidence **O** - 214 code lines
- where: src/asy_uart_driver.py:59-85, 106, 140-147, 177-215, 285-371, 420-425, 444-452, 459-460, 476-507, 515-524, 584-590, 636-650, 706-712, 747-780
- what: each UART receives through a DMA ring (two chained channels, 512 B, the RX interrupt off), so no byte is lost while a flash write holds interrupts off; a lap or a receive error is counted as an overrun and resynced
- commits: cbb65df2 (U13), c11ca0aa (U17)
- origin: M.SRC_NET.221, .222; OR141.a (4)
- evidence: O: review uart-flash-erase-overrun, owner note: "Either don't lose a frame in general (preferred, if achievable with adequate effort), or halt the UART in some way for the time it takes (feels like a workaround only, though)." (audit/review/answers.json); OR141 (PROJECT_AUDIT_PLAN.md:552): "UART in the DMA ring buffer, but keep a strict eye on how that integrates with the heap allocation and fragmentation"
- legacy: no: legacy reads machine.UART directly (legacy/firmware/python/IndividualDrivers/asy_uart.py:74-150)
- form: design
- depends on: none
- device cost: 214 code lines; 2 DMA channels; one 1 KB allocation at setup (the ring plus its alignment padding); a Python byte-copy loop per read
- minimal change: as designed - the owner's preferred option (about 200 added or changed lines, the count above); pinned by tests/test_asy_uart_comm.py test_a_flood_that_laps_the_ring_drains_to_its_bound_not_as_quiet; flash tier crossover tests
- scheme: none

**UD-2** - class **R** - evidence **O** - 8 code lines
- where: src/asy_uart_driver.py:131, 217-226
- what: the driver counts the bytes its failed reads consumed (discarded_bytes, wrapping at the shared cap)
- commits: c11ca0aa
- origin: A.U17.13
- evidence: O: OR70.a (5) (see UC-9)
- legacy: no
- form: design
- depends on: UC-9
- device cost: 8 code lines; one add per failed read
- minimal change: one counter and its increments (~6 lines); pinned by see UC-9
- scheme: none

**UD-3** - class **R** - evidence **O** - 17 code lines
- where: src/asy_uart_driver.py:380-396
- what: a write goes only into an empty TX ring, at most txbuf bytes, under a deadline
- commits: cbb65df2, c11ca0aa
- origin: A.U13.13; OF-39
- evidence: O: CLAUDE.md:276-277: "`asy_uart_driver.py` and `asy_uart_comm.py` may never block the asyncio loop - not even in a wait state." (project owner, 2026-09-11)
- legacy: no
- form: design
- depends on: none
- device cost: 17 code lines; one txdone() poll per round
- triage: latent while a frame fits the free ring (A.U13.13 Why); the owner's rule for these files is categorical
- minimal change: wait for txdone() and cap each write at txbuf (~5 lines; the deadline is UC-16's H); pinned by tests/test_asy_uart_driver.py write-ring tests
- scheme: none

**UD-4** - class **R** - evidence **O** - 38 code lines
- where: src/asy_uart_driver.py:652-695
- what: readline_until_complete() collects at most max_bytes in PieceBuffer pieces; an over-cap line is discarded (E93); a failed allocation answers None
- commits: c11ca0aa, 1d2b3cca
- origin: OR143.a (2); owner option (c)
- evidence: O: OR143 (2026-10-05, PROJECT_AUDIT_PLAN.md:556): "I want one parked item to be fixed: the UART chunking for large allocations. ... A general maximum buffer size, catching uncapped heap flooding in general if too large incoming transmissions occur, is also to be implemented"; OR143.a (2): "readline_until_complete() gets the same cap: it no longer grows by concatenation"; owner, 2026-10-27: "Do option (c) as you recommended"
- legacy: no: legacy concatenates without a cap (asy_uart.py:138-155)
- form: design
- depends on: PieceBuffer (group A)
- device cost: 38 code lines; pieces of chunk_bytes
- triage: no product caller (library API)
- minimal change: as is; pinned by tests/test_asy_uart_driver.py readline cap tests
- scheme: none

**UD-5** - class **R** - evidence **O** - 2 code lines
- where: src/asy_uart_driver.py:636-640
- what: readline() reads only the bytes already received (up to rxbuf), never waiting per byte
- commits: cbb65df2
- origin: A.U13.12
- evidence: O: CLAUDE.md:276-277 (see UD-3)
- legacy: no: legacy calls uart.readline() unclamped (asy_uart.py:131-135)
- form: design
- depends on: UD-1
- device cost: 2 code lines; none
- triage: no product caller (library API)
- minimal change: clamp to what is there (~3 lines); pinned by tests/test_asy_uart_driver.py readline clamp test
- scheme: none

**UD-6** - class **R** - evidence **O** - 15 code lines
- where: src/asy_uart_driver.py:49, 398-416
- what: the cancel request/acknowledge sequences and the unacknowledged count wrap at the shared cap and compare wrap-safe
- commits: c11ca0aa
- origin: A.U17.28
- evidence: O: OR103/OR105 (see UC-17)
- legacy: no
- form: design
- depends on: none
- device cost: 15 code lines; none
- minimal change: mask and compare (~4 lines); pinned by counter-step tests
- scheme: none

**UD-7** - class **H** - evidence **H** - 8 code lines
- where: src/asy_uart_driver.py:535-536, 600-601, 787-788, 809-810
- what: a zero-length read answers empty and a zero-length write sends nothing
- commits: 2949ed97
- origin: A.U12.03
- evidence: H: HARVEST decision "callers never pass a zero-length payload" (A.U12.03 Why)
- legacy: no
- form: design: guard
- depends on: none
- device cost: 8 code lines; none
- triage: implausible: no caller passes zero, by the recorded decision
- simplest alternative: pre-audit
- scheme: HYP (built on a hypothetical, u35r/briefs/scan_firmware.md:6); MIN (minimal change, u35r/briefs/scan_firmware.md:3-5)

**UD-8** - class **H** - evidence **H** - 2 code lines
- where: src/asy_uart_driver.py:729, 739
- what: ready() re-checks the bus after its closing yield; an out-of-range wait answers False
- commits: cbb65df2
- origin: A.U13.18, A.U13.19
- evidence: H: A.U13.18: a deinit'd rp2 UART's RX ring is unrooted (SPEC F.5.7)
- legacy: no
- form: design
- depends on: none
- device cost: 2 code lines; none
- triage: implausible: no product path deinits a UART mid-session
- simplest alternative: pre-audit
- scheme: HYP (built on a hypothetical, u35r/briefs/scan_firmware.md:6)

**UD-9** - class **K** - evidence **H** - 11 code lines
- where: src/asy_uart_driver.py:436, 468, 524, 541, 550, 574, 649, 663, 732, 772, 792
- what: every allocation-failure catch prints its text through console()
- commits: 06a8ae5d
- origin: U30 ("9 of 47 handlers were silent")
- evidence: H: 06a8ae5d: "Allocation failures: every caught one reaches the four memory gates with its text, the UART link and driver included"
- legacy: no
- form: design intent repeated per site
- depends on: none
- device cost: 11 code lines; only on failure
- triage: implausible as a device failure; serves the test gates
- simplest alternative: pre-audit silent
- scheme: MIN (minimal change, u35r/briefs/scan_firmware.md:3-5)

Checked for non-behavioural changes (src/asy_uart_driver.py): AST-normalised diff read in full. Not counted: the session-lock rename, the codec class renames, sorted except tuples, the header pointers, the changed `poll_wait_ms`/`poll_idle_ms` defaults 20/None -> 2/50 (dev's TOML passed 2 and 50 at 25caf528 and at the head, devices/dev.toml, so no device sees it).

### src/asy_uart_link_driver.py

**UL-1** - class **R** - evidence **O** - 95 code lines
- where: src/asy_uart_link_driver.py:45-66, 120-127, 144-151, 160-236, 264-266, 279-286
- what: dev's UART hazard mode: on request (PUT /status) two initiations at once, a crossed initiation and a field sweep, then recovery; the facts are reported in /status
- commits: 656fc82f, c56b366b
- origin: U35 C-block; owner rulings 2026-10-21/22
- evidence: O: owner, 2026-10-21: "b - system shall be proven stable unter max load allover"; owner, 2026-10-22: "the link module is a necessity for testing, and it's testing code inside a module, but for a good reason, and the guard from being included in real deployed firmware is the fact that the module is never included in the config files for deployment boards." (656fc82f message)
- legacy: no
- form: design: bench-only test mode
- depends on: WS-26
- device cost: 95 code lines; nothing until requested; one run per request
- minimal change: as is (dev only); pinned by tests/test_asy_uart_link_driver.py hazard-run tests; twin UART hazard files
- scheme: none

**UL-2** - class **R** - evidence **O** - 6 code lines
- where: src/asy_uart_link_driver.py:98, 133, 290-293
- what: the exercise loop runs only while the link came up; a failed setup ends it, so the supervisor escalates on both roles
- commits: c11ca0aa
- origin: A.U17.07 (RF154)
- evidence: O: OR18.a (2026-09-25, PROJECT_AUDIT_PLAN.md:305): "b, because a stalled chip may recover by a reboot, keeping it contained going so far may miss that opportunity"
- legacy: no
- form: design
- depends on: none
- device cost: 6 code lines; none
- minimal change: a readiness flag (3 lines); pinned by tests/test_asy_uart_link_driver.py failed-setup test
- scheme: none

**UL-3** - class **R** - evidence **O** - 7 code lines
- where: src/asy_uart_link_driver.py:137-141, 191-192
- what: transfer, failure and hazard-run counts stop at the shared cap
- commits: c11ca0aa, 656fc82f
- origin: A.U17.29
- evidence: O: OR103/OR105 (see UC-17)
- legacy: no
- form: design
- depends on: none
- device cost: 7 code lines; none
- minimal change: check-before-step; pinned by counter-step tests
- scheme: none

**UL-4** - class **R** - evidence **O** - 2 code lines
- where: src/asy_uart_link_driver.py:287-288
- what: ResetErrors leaves the transfer counts (clears the log only)
- commits: 8d44fd14
- origin: A.U17.19
- evidence: O: OR36.a (2) (PROJECT_AUDIT_PLAN.md:341): "The UART link exerciser ... is a regular driver ... like every driver it is held to the same bar"; OR24.a (1) consistency
- legacy: no
- form: design: consistency
- depends on: none
- device cost: 2 code lines; none
- minimal change: the removal of two lines; pinned by tests/test_asy_uart_link_driver.py reset test
- scheme: none

**UL-5** - class **C** - evidence **F** - 7 code lines
- where: src/asy_uart_link_driver.py:97, 137, 102-113
- what: the banner check copies into a scratch buffer allocated once; the echo answers GET from its stored pieces
- commits: c11ca0aa, 3a24c773
- origin: UC-3, UC-5
- evidence: F: see UC-5 (the measured 12,192-byte copy per GET)
- legacy: no
- form: design
- depends on: UC-3
- device cost: 7 code lines; no allocation per check or per GET
- triage: exists because uart_get() returns a PieceBuffer (UC-3)
- simplest alternative: with UC-3 as is, needed
- scheme: CASC (cascade, u35r/briefs/scan_firmware.md:7)

Checked for non-behavioural changes (src/asy_uart_link_driver.py): AST-normalised diff read in full. Not counted: `UartLinkExerciser` -> `UARTLinkDriver`, the limits/callbacks objects, the banner text 'dev-uart-crossover' -> 'uart-crossover' (review uart-banner-rename: the no-variant rule; a Python-internal changelog line), the starter rename, the removed public `uart` seam (A.U17.18, OR36.a (1)).

## Per-file totals

| file | rows | R rows / lines | K rows / lines | H rows / lines | X rows / lines | C rows / lines | O / F / H rows |
|---|---|---|---|---|---|---|---|
| src/asy_dns_client.py | 9 | 2 / 4 | 2 / 19 | 5 / 20 | 0 / 0 | 0 / 0 | 2 / 0 / 7 |
| src/asy_udp_socket.py | 5 | 2 / 3 | 0 / 0 | 1 / 3 | 1 / 14 | 1 / 12 | 2 / 0 / 3 |
| src/asy_captive_dns.py | 9 | 3 / 17 | 2 / 5 | 4 / 20 | 0 / 0 | 0 / 0 | 3 / 0 / 6 |
| src/asy_ntp_client.py | 24 | 11 / 61 | 3 / 12 | 8 / 60 | 0 / 0 | 2 / 4 | 11 / 0 / 13 |
| src/asy_wifi_service.py | 23 | 10 / 124 | 2 / 5 | 11 / 111 | 0 / 0 | 0 / 0 | 10 / 0 / 13 |
| src/asy_webserver_service.py | 26 | 14 / 149 | 4 / 19 | 7 / 90 | 0 / 0 | 1 / 5 | 15 / 0 / 11 |
| src/asy_uart_comm.py | 22 | 12 / 125 | 2 / 20 | 5 / 11 | 2 / 30 | 1 / 9 | 12 / 1 / 9 |
| src/asy_uart_driver.py | 9 | 6 / 294 | 1 / 11 | 2 / 10 | 0 / 0 | 0 / 0 | 6 / 0 / 3 |
| src/asy_uart_link_driver.py | 5 | 4 / 110 | 0 / 0 | 0 / 0 | 0 / 0 | 1 / 7 | 4 / 1 / 0 |
| all | 132 | 64 / 887 | 16 / 91 | 43 / 325 | 3 / 44 | 6 / 37 | 65 / 2 / 65 |

Code lines: the lines inside each row's ranges at 497b3eda that `git blame 25caf528..497b3eda` attributes to a commit of the range (so added or changed, not pre-audit lines), comment and blank lines excluded. A removal row counts 0; its removed lines are stated in the row. A renamed line counts as changed, so small rows can include a renamed neighbour.

## Scheme violations

| file | MIN | HYP | CASC | DELAY | PATCH | FEAT | D1 | P6 | P8 | P4 | TYPEG | rows with none |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| src/asy_dns_client.py | 4 | 5 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 1 | 3 |
| src/asy_udp_socket.py | 2 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 2 |
| src/asy_captive_dns.py | 3 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 5 |
| src/asy_ntp_client.py | 7 | 6 | 3 | 2 | 1 | 2 | 1 | 0 | 0 | 0 | 0 | 13 |
| src/asy_wifi_service.py | 10 | 11 | 1 | 0 | 0 | 2 | 2 | 1 | 0 | 0 | 0 | 9 |
| src/asy_webserver_service.py | 10 | 7 | 2 | 2 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 14 |
| src/asy_uart_comm.py | 4 | 6 | 2 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 13 |
| src/asy_uart_driver.py | 2 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 6 |
| src/asy_uart_link_driver.py | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 |
| all | 42 | 40 | 10 | 5 | 3 | 5 | 3 | 1 | 1 | 1 | 1 | 69 |

Rule keys:
- MIN: minimal change - u35r/briefs/scan_firmware.md:3-5: owner, 2026-10-28: "the way it flows into the firmware and buildgen is *really* minimal change"
- HYP: built on a hypothetical - u35r/briefs/scan_firmware.md:6: owner, 2026-10-28: "Speculative and hypothetical effects maybe, maybe not."
- CASC: cascade - u35r/briefs/scan_firmware.md:7: owner, 2026-10-28: "Resulting cascades are a red flag at least."
- DELAY: hardcoded delay/timing check - u35r/briefs/scan_firmware.md:106-107: owner: "hardcoded delay checks like this are a very bad, very awkward pattern"
- PATCH: patch, not design - u35r/briefs/inv_firmware_additions.md:2-4: the owner's standing target as the lead states it: "clean and minimal firmware code; nothing built on hypothetical findings; no patches"
- FEAT: same top-level features - CLAUDE.md:508-511: The refactor should end up with the *same top-level features* ... just more consistent/stable - not a feature change.
- D1: flag, don't silently change - SPECIFICATION.md:4765-4766: If verification surfaces a discrepancy, do not silently change it - flag and ask before altering real output.
- P6: P6 efficient and compact - audit/CONSOLIDATION.md:30: P6 Efficient and compact on low-end hardware
- P8: P8 one source of truth - audit/CONSOLIDATION.md:32: P8 One source of truth, generated not copied
- P4: P4 one material - audit/CONSOLIDATION.md:28: P4 Premium code, one material, nothing in the product for tests
- TYPEG: unreachable guard - u35r/recovered/owner_rulings_after_LN118.md (2026-10-27): owner, 2026-10-27: "A strong hint for an unnecessary check is that it is proven to be fully covered by typing adherence alone, and that it is unreachable with today's code"

Most violated, in order: MIN (42), HYP (40), CASC (10), FEAT (5), DELAY (5), PATCH (3), D1 (3), TYPEG (1), P4 (1), P6 (1), P8 (1).

## Minimal-change list (R and confirmed items)

| row | class | change against 25caf528 | pinning test |
|---|---|---|---|
| DNS-2 | R | pre-audit `dns_servers + _FALLBACK_DNS_SERVERS` -> `dns_servers` and the constant deleted (2 lines), with NTP-2 passing the list | tests/test_asy_ntp_client.py test_resolve_ntp_server_asks_dhcp_first_then_the_fallback_list_in_order |
| DNS-9 | R | needed by NTP-1's minimal form; 4 lines | tests/test_asy_dns_client.py host-label cases (tests/_radio_shape_cases.json hostLabel) |
| UDP-1 | R | the removal itself | a test that UDPSocket(b'...') raises TypeError |
| UDP-3 | R | pre-audit ready(): pass 100 instead of 20 when timeout_ms <= 0 (1 line) | tests/test_asy_udp_socket.py test_ready_without_a_deadline_polls_at_the_idle_rate |
| CD-1 | R | pre-audit response(): one QTYPE test, the ANCOUNT byte and `if answer:` around the three answer lines (~6 lines) | tests/test_asy_captive_dns.py test_other_query_types_get_an_empty_noerror_reply, test_an_a_or_any_query_gets_the_a_record |
| CD-3 | H (V3) | recvfrom(4096) -> recvfrom(512) (1 line) | tests/test_asy_captive_dns.py's recvfrom(512) record (M.SRC_NET.007 blast) |
| CD-6 | H (V2) | `await asyncio.sleep(0)` after each received datagram (1 line) | tests/test_asy_captive_dns.py test_run_yields_once_per_datagram_while_the_socket_stays_ready |
| CD-8 | R | one report_if_fatal(e) per broad handler (3 lines) | tests_scripts/test_fatal_report_sites.py |
| CD-9 | R | renumbering only (6 constants) | tests_scripts catalog check (buildgen/error_catalog.json) |
| NTP-1 | R | bound 1024 -> 253 (1 constant) and a PUT-side shape check in the existing override path (~5 lines) | a PUT of NTPHost 'bad host!' answers Invalid and stores nothing (tests/test_asy_ntp_client.py PUT-refusal tests) |
| NTP-2 | R | one config field + its ipv4-list check + passing it to resolve_ipv4() (~12 lines) | tests/test_asy_ntp_client.py test_resolve_ntp_server_asks_dhcp_first_then_the_fallback_list_in_order, test_a_stored_fallback_that_is_not_an_ipv4_list_uses_its_default |
| NTP-8 | H (V1) | `if raw_s == 0: log E69; return None` before the era step (3 lines) | tests/test_asy_ntp_client.py test_a_zero_transmit_timestamp_is_rejected |
| NTP-11 | R | pre-audit loop: count the stale age in its own seconds counter that only a success resets (~3 lines) | tests/test_asy_ntp_client.py test_a_failed_resync_never_resets_the_staleness_count |
| NTP-14 | R | read a TickSeconds restarted at each success instead of incrementing (2 lines here) | a driven-clock test: a dropped 1 s tick leaves LastSyncAge exact |
| NTP-16 | R | as is (~5 lines; the /status flag is buildgen's) | tests/test_asy_ntp_client.py test_a_settings_change_unsets_the_clock_until_the_next_sync |
| NTP-17 | R | two call sites of the primitive | twin Run 1 asserts UTCTime/LocalTime null before sync (review run1-null-time) |
| NTP-19 | R | add the Synced clear to the pre-audit ntp_force_sync() (1 line) | tests/test_asy_ntp_client.py test_ntp_force_sync_resets_last_sync_retries_and_fires_the_sync_trigger |
| NTP-21 | R | the removal itself | tests/test_asy_print_log.py newest-entry rule tests (group A) |
| NTP-22 | R | 2 lines | tests_scripts/test_fatal_report_sites.py |
| NTP-23 | R | renumbering | tests_scripts catalog check |
| NTP-24 | R | the removal itself | the twin's boot-order record (OR47.a (1)) |
| WF-3 | R | replace the pre-audit _deactivate_wlan_permanently() by a silent phase marked due by the hotspot window's watcher (~25 lines) | tests/test_asy_wifi_service.py test_the_silent_mode_keeps_the_led_dark_until_a_link |
| WF-4 | R | a fresh-boot flag set by reconnect_wifi() and taken by the reconnect handler (~6 lines) | tests/test_asy_wifi_service.py test_the_identity_hook_lands_in_the_fresh_boot_state |
| WF-5 | K (V6) | only if the owner rejects OR151's "only through a reboot, as is" for an unconfigured unit: an empty SSID sets the hotspot phase directly (3 lines) | tests/test_asy_wifi_service.py empty-SSID test: after a hotspot window with no client and no SSID the unit is back on the hotspot, not off |
| WF-7 | R | catch the arm's OSError, persist E17, set the hardware-failure flag (~6 lines) | tests/test_asy_wifi_service.py hotspot timer arm-failure tests |
| WF-9 | R | start the flash task with the inverted pattern in the deactivated branch (~3 lines plus the pattern parameters) | tests/test_asy_wifi_service.py deactivated-pattern tests |
| WF-16 | R | keep the pre-audit 'failure = no client' and add the W77 entry (2 lines) | tests/test_asy_wifi_service.py test_get_hotspot_stations_answers_none_for_a_failed_query_and_an_empty_list_for_no_client |
| WF-18 | R | read a TickSeconds instead of incrementing (~3 lines) | a driven-clock test: a dropped 1 s tick leaves WifiUptime exact |
| WF-20 | R | one call per handler (16 lines) | tests_scripts/test_fatal_report_sites.py |
| WF-21 | R | renumbering | tests_scripts catalog check |
| WF-22 | R | 5 lines | the twin's boot-order record |
| WF-23 | R | the removal itself | see NTP-21 |
| WS-1 | R | the line and head-byte counters in the proxy's readline() plus the own buffered read (~25 lines) | tests/test_asy_webserver_service.py test_the_header_count_is_bounded, test_a_head_past_its_byte_cap_is_refused_though_each_line_fits |
| WS-3 | R | one wrn_s per drop path (~6 lines) | tests/test_asy_webserver_service.py test_a_client_gone_mid_response_counts_one_drop |
| WS-4 | R | as is (~6 lines here) | tests/test_asy_webserver_service.py test_dropped_connections_leave_the_count_after_a_day, test_reset_errors_clears_the_dropped_count |
| WS-8 | R | 1 line | tests/test_asy_webserver_service.py test_a_static_get_answers_cache_control_no_cache |
| WS-12 | R | two words in the tuple (1 line); the commands themselves are group A's | tests/test_asy_webserver_service.py test_each_system_command_over_put_system_reaches_its_reset_arm_without_a_lock_held |
| WS-13 | R | one `if any(refused()...)` before the resets (~3 lines) and the callables passed in | tests/test_asy_webserver_service.py ResetErrors refusal tests |
| WS-14 | R | the pre-audit loop -> one asyncio.gather() (2 lines) | tests/test_asy_webserver_service.py concurrent ResetErrors test |
| WS-16 | R | one loop marking keys no group lists (~5 lines) | tests/test_asy_webserver_service.py test_sensors_put_unknown_sensor_key_answers_invalid |
| WS-17 | R | as is, the legacy bounds in the dispatcher (~15 lines) | tests/test_asy_webserver_service.py LightCmdLED validation and busy tests |
| WS-21 | R | one outer try/except (~5 lines) | tests_scripts/test_task_tops.py |
| WS-23 | R | one call per handler | tests_scripts/test_fatal_report_sites.py |
| WS-24 | R | renumbering | tests_scripts catalog check |
| WS-25 | R | 3 lines | the twin's boot-order record |
| WS-26 | R | as is with UL-1 | tests/test_asy_webserver_service.py status-command tests |
| UC-1 | R | one constructor value and one check before the ACK in _accept_set()/_get_unlocked() (~6 lines) | tests/test_asy_uart_comm.py receive-cap refusal tests |
| UC-3 | R | as is (~15 lines here) | tests/test_asy_uart_comm.py largest-receive-allocation test |
| UC-4 | R | 2 x 3 lines | tests/test_asy_uart_comm.py the three fault-flow tests of 1d2b3cca |
| UC-9 | R | read the driver's discard count into the resync total (~5 lines) | tests/test_asy_uart_comm.py E89 for a speak-when-spoken-to peer |
| UC-12 | R | as is (~8 lines) | tests/test_asy_uart_comm.py test_the_ring_floor_covers_a_config_flush |
| UC-13 | R | as is | tests/test_asy_uart_comm.py test_a_ring_refused_at_setup_names_its_cause |
| UC-14 | R | the removal itself | tests_scripts/test_fault_or_warning_never_both.py |
| UC-17 | R | check-before-step (2 x 1 line) | counter-cap tests (tests_scripts/test_counter_steps.py) |
| UC-19 | R | reorder | tests/test_asy_uart_comm.py entry-point order tests |
| UC-20 | R | the removal itself | see UC-14 |
| UC-21 | R | 3 lines | tests_scripts/test_fatal_report_sites.py |
| UC-22 | R | renumbering (no wire byte changes) | tests_scripts catalog check |
| UD-1 | R | as designed - the owner's preferred option (about 200 added or changed lines, the count above) | tests/test_asy_uart_comm.py test_a_flood_that_laps_the_ring_drains_to_its_bound_not_as_quiet; flash tier crossover tests |
| UD-2 | R | one counter and its increments (~6 lines) | see UC-9 |
| UD-3 | R | wait for txdone() and cap each write at txbuf (~5 lines; the deadline is UC-16's H) | tests/test_asy_uart_driver.py write-ring tests |
| UD-4 | R | as is | tests/test_asy_uart_driver.py readline cap tests |
| UD-5 | R | clamp to what is there (~3 lines) | tests/test_asy_uart_driver.py readline clamp test |
| UD-6 | R | mask and compare (~4 lines) | counter-step tests |
| UL-1 | R | as is (dev only) | tests/test_asy_uart_link_driver.py hazard-run tests; twin UART hazard files |
| UL-2 | R | a readiness flag (3 lines) | tests/test_asy_uart_link_driver.py failed-setup test |
| UL-3 | R | check-before-step | counter-step tests |
| UL-4 | R | the removal of two lines | tests/test_asy_uart_link_driver.py reset test |

## Cascades

1. **UDP deadline** (root A.U10.26, the owner-prioritised "one timeout mechanism", 2026-09-11): `ready()` moved onto
   `asyncio.wait_for_ms()` (41b47f1d/f1f800e7), which lost a cancel landing after its timeout (both LC1 tests red on
   that form) -> LC1 (21ec0979) took the deadline back into `_poll()` = UDP-4. Net against 25caf528: the pre-audit
   loop with a cut last sleep. The owner-decided part that remains is UDP-3's idle rate.
2. **NTP cadence** (root NTP-12, F2r c56b366b, OF-247 read at U35 V6 as a D.1 flag-first item, no owner ruling
   found): the elapsed-time cadence restarted a few ms after a fire, so the boundary tick read just under the interval
   -> F5 (a66213b6) rounds to the nearest 10 s tick = NTP-13; F3r (68224efb) applied the same idea to the unsynced
   wait = NTP-15, sharing NTP-13's helper. Three commits, ~14 lines, for a 10 s slack the owner called irrelevant
   (Q10, 2026-10-27, about the sibling stale rule).
3. **Staleness reachable** (root NTP-11, O): once Synced can go stale, local time had to keep running = NTP-18
   (`cettime()` on clock-set), and UTCTime/the VOC backups needed the clock-valid flag = NTP-16 (O, 2026-10-21).
   Chain O -> C -> O; the C link is the conservative form.
4. **UART pieces** (root UC-3, OR143, O): `uart_get()` returns a PieceBuffer -> the link driver's banner check copies
   into a scratch buffer and its echo answers from stored pieces (UL-5), which needs a send-side PieceBuffer path in
   the comm (UC-5, F: the measured 12,192-byte copy per GET) -> the owner's option (c) catch at the PieceBuffer sites
   (UC-4, O). OR143.a (2) had said the caught-MemoryError sites at these allocations "go"; UC-4 put two back, by the
   owner's later choice.
5. **UART DMA ring** (root UD-1, OR141, O): the lap/receive-error count (UD-1) -> the drain continuing past an
   overrun (UC-13), the ring floor from the traced flash hold (UC-12, O), the overrun warning per failed frame read
   (UC-11, K, OF-37). Within O except UC-11.
6. **UART discards** (root UC-9/UD-2, OR70.a (5), O): the discard count -> the fault texts naming a dropped frame
   (UC-10, K, OF-210).
7. **Webserver drops** (root WS-3, O): each drop's trace sits on the connection's close path -> under FRAM-log load
   the close waited past a client's timeout (OF-254, found in the U35 gate) -> WS-6 bounds each trace by one per-call
   timeout (owner-agreed 2026-10-22, but a patch around FRAM latency).
8. **Head guard** (root WS-1, O): the bound before allocation needs the proxy's own buffered readline/readexactly,
   which the further shape refusals of WS-2 (H) ride on.
9. **Wi-Fi silent mode** (root WF-3, O): it reuses the hotspot window's timer -> a failed arm of it must count (WF-7,
   O 2026-10-13) -> the connect loop's "evidence" flag so an idle silent pass neither counts nor heals the streak
   (inside WF-3's ranges). WF-5 (empty SSID straight to the hotspot, K) predates it and conflicts with OR151's "Entering
   the hotspot mode only through a reboot, as is" (V6).
10. **Wi-Fi snapshot** (root WF-15, H) -> `_dhcp_dns` cached for NTP and the deactivated nulls (review "ok"); WF-6's
    `_ap_selected` feeds WF-15's RSSI gate and WF-19's rung.
11. **Radio shapes** (root WF-1, H) -> the GET overlay showing the value in use (WF-2, H).
12. **Flat GET marker** (root SF-B8, WS-18, K) -> F1r (18b9ff67) tightening its own key test inside the same row.

## Verifications
Runs: one, logged in `S/u21/RUNS.md` ("U35 scan B v1_ntp_zero_ts"), under `unshare -n S/u24/ns_xdg.sh nice -n 19`,
the pinned Unix port, the pre-audit tree exported to `S/u35r/scan/work_B/pre/` (git archive 25caf528 src tests).

- **V1 (NTP-8), confirmed.** `S/u35r/scan/work_B/run/v1_ntp_zero_ts.py` feeds the pre-audit
  `AsyNtpClient._parse_ntp_reply()` one 48-byte reply: LI 0, VN 4, mode 4, stratum 2, transmit timestamp 0. Three runs,
  identical (`run/v1_run1.log`..`v1_run3.log`): "Received NTP time: 2085978496", returned `(2036, 2, 7, 6, 28, 16, 3,
  38, 0)`, RTC set to `(2036, 2, 7, 4, 6, 28, 16, 0)`. The era step carries an unset timestamp into the plausibility
  window; the KoD check does not catch it because the stratum is not 0. Legacy has the same gap (it sets any time).
- **V2 (CD-6), confirmed (mechanism).** The lane C test `test_run_yields_once_per_datagram_while_the_socket_stays_ready`
  FAILED on the pre-audit loop (`audit/artefacts/evidence/U18_close/lane_c/u18c_logs/fix2_testsfirst_std.log`). By
  reading: pre-audit `recvfrom()` -> `ready()` returns True without an await while `ipoll(0)` reports POLLIN, and
  `sendto()` the same, so a socket kept ready never yields. The watchdog consequence needs a sustained flood faster
  than the loop answers for 8.4 s; not reproduced (hardware-round item 2).
- **V3 (CD-3), mechanism confirmed, consequence unverified.** `extmod/modlwip.c` (v1.29.0, the recvfrom path at
  :1318-1324) runs `vstr_init_len(&vstr, len)` before reading, so `recvfrom(4096)` allocates 4 KB per query. Whether
  that fails in hotspot mode needs a heap run with the setup page served and phones probing: hardware-round item 3 (or
  a twin hotspot scenario).
- **V4 (WS-20), refuted as stated.** In the pre-audit tree `_stream_dict_response()`/`_build_status_pieces()` hand
  their str list to `_pieces_response()`, which builds `encoded` and returns; the str list is unreferenced from then on
  (`S/u35r/scan/work_B/pre/src/asy_webserver_service.py:181-202, 569-577`). So no copy is held for the response's
  life; a transient 2x peak during the encode remains.
- **V5 (WF-1, Country), unverified.** `network.country()` copies the two bytes unchecked (`extmod/modnetwork.c:134-146`,
  cited by A.U6.30); what the CYW43 firmware's CLM does with "de" or "zz" is inside the firmware blob. Hardware-round
  item 1.
- **V6 (WF-5), confirmed by reading.** Pre-audit `_attempt_sta_connect()` sets the streak to its limit for an empty SSID
  (`S/u35r/scan/work_B/pre/src/asy_wifi_service.py:441-442`) and `_register_sta_connection_failure()` then calls
  `_deactivate_wlan_permanently()` once the hotspot ran (`:479-486`): a unit nobody configures within its first hotspot
  window switches Wi-Fi off until a power cycle. Legacy does exactly this (`async_connect.py:296-298, 353-361`), so it
  is field behaviour; the owner's OR151 wording "Entering the hotspot mode only through a reboot, as is." reads as
  accepting it, while SF-M2-01 (agent, on the owner-review list) changed it. An owner decision, not a verified gap.

## Hardware-round list
1. Country: on dev, set the country to "de" with the pre-audit image (the head build refuses it at PUT), or call
   `network.country("de")` from a device script, and connect to an AP on channel 13; does the CYW43 find it? Settles V5 and whether WF-1's
   Country half is a real gap.
2. Optional: a DNS query flood at dev's hotspot from the bench host, pre-audit image, watching for a watchdog reset
   (V2's consequence). Not needed to keep the one-line fix.
3. Optional: free heap and largest block on dev in hotspot mode with a phone probing and the setup page loading,
   pre-audit image (V3's consequence).
4. Already owed by OR141.a (4) (d): the DMA ring "proven on the bench" (soft reset, no frame lost during a config
   flush) - UD-1, UC-12, UC-13.

## Notes for the lead
- The scheme field names the owner's 2026-10-28 rules as written in the brief. MIN and HYP are given wherever a row is
  H/K/X/C; they are the rules such a row conflicts with by definition, so their counts mirror the H/K/X/C counts.
- WF-7 is O on its handling (2026-10-13) though its trigger (alarm-pool exhaustion) is as hypothetical as NTP-20's and
  WF-8's; the three are the same mechanism handled three ways.
- UD-3 and UD-5 are O by the never-block rule but have no product caller that can trigger them today (frames fit the
  ring; nothing calls readline). UD-4 likewise has no product caller.
- OF-247 (NTP-12) is still "open, U37" in `open_findings.md:255` though F2r implemented it; the D.1 flag-first path it
  names was not found walked.
