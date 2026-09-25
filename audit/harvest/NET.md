# Harvest — NET: Networking

What the project's own comments, docs and history already record for this area (snapshot `2a88cc8`).
Recorded, not verified or triaged; `audit/HARVEST.md` explains the kinds, tags and method.

Kinds: SETTLED 43, INVAR 31, MIRROR 7, LIMIT 50, RISK 18, ASSUME 30, PLATFORM 15, WORKAROUND 2, SUPPRESS 39, TODO 6, OPENQ 3, DRIFT 6, NOTE 7 — 257 items.


## src/asy_dns_client.py

- **NET.N001** LIMIT · `src/asy_dns_client.py:5-7` — "IPv4 DNS resolver (A-records only) ... only bare
  compression-pointer names (RFC 1035 SS4.1.4) are followed, matching captive_dns.py's precedent" —
  Answers whose NAME is not a bare pointer end parsing; A-only. · covered-by: NET.S14 · [H01]
- **NET.N002** INVAR · `src/asy_dns_client.py:6` — "resolve_ipv4() never raises, returns the dotted-quad
  str or None" — Never-raise relies on callee contracts (`AsyUDPSocket` I/O never raises, `__init__`
  excepted); `__init__`'s `asyncio.Lock()` MemoryError is not in the caught set at :115 (low). ·
  related: NET.T04, NET.T05 · [H01]
- **NET.N003** ASSUME · `src/asy_dns_client.py:16-17` — "_DNS_TIMEOUT_MS = const(500) # ... a standalone
  default only; real callers are expected to override it explicitly" — Expectation on callers; NTP's
  per-server budget depends on it. · related: NET.S02 · [H01]
- **NET.N004** PLATFORM · `src/asy_dns_client.py:19` — "_DNS_RECV_BUF = const(512) # RFC 1035 SS4.2.1's
  guaranteed-safe UDP message size." — 512-byte receive; larger replies truncated, TC bit unchecked. ·
  covered-by: NET.S14 · [H01]
- **NET.N005** RISK · `src/asy_dns_client.py:20-21` — "_FALLBACK_DNS_SERVERS ... = (\"8.8.8.8\",
  \"1.1.1.1\") # tried after caller-supplied servers." — Public-resolver fallback (outbound traffic /
  behaviour change vs legacy). · covered-by: NET.S04 · [H01]
- **NET.N006** INVAR · `src/asy_dns_client.py:21` — "Not const()-wrapped so tests can monkeypatch it
  (const() inlines at compile time)." — Shipped constant shaped for a test hook (low). · [H01]
- **NET.N007** LIMIT · `src/asy_dns_client.py:45-49` — "over 63 octets is not a real label and over 255
  cannot be encoded at all. host comes from a REST-settable config field with no per-label check" — Only
  per-label length is checked; no 255-octet QNAME total, empty labels not rejected. · covered-by:
  NET.S14 · [H01]
- **NET.N008** ASSUME · `src/asy_dns_client.py:78-80` — "Response's Question section mirrors the query's
  own (RFC 1035), so len(query) is the exact answer-section offset." — QDCOUNT/question echo not
  verified; answers parsed at a fixed offset. · related: NET.T04 · [H01]
- **NET.N009** SUPPRESS · `src/asy_dns_client.py:108-109` — "except (MemoryError, ValueError): #
  ValueError: a label over 63 octets - not a real DNS name" — Query-build failure swallowed to None, no
  log. · [H01]
- **NET.N010** LIMIT · `src/asy_dns_client.py:111-112` — "continue # an unset/placeholder or malformed
  DNS server value - not worth a network attempt" — "0.0.0.0"/malformed servers silently skipped (falls
  through to public resolvers). · related: NET.S05 · [H01]
- **NET.N011** SUPPRESS · `src/asy_dns_client.py:115-116` — "except (ValueError, TypeError): # malformed
  port - server is already validated above" — Construction failure silently skips the server. · [H01]
- **NET.N012** INVAR · `src/asy_dns_client.py:119-120` — "await cli.disconnect() # never raises - see
  asy_udp_socket.py's own contract" — Cross-module contract (`src/asy_udp_socket.py:8`). · related:
  NET.T05 · [H01]
- **NET.N013** SUPPRESS · `src/asy_dns_client.py:125-126` — "except (IndexError, ValueError): # residual
  bounds-math edge case against untrusted network bytes" — Parse exceptions on hostile input swallowed
  to None, no log. · related: SEC.T05 · [H01]

## src/asy_ntp_client.py

- **NET.N014** DRIFT · `src/asy_ntp_client.py:9-10 vs :157, :217, :250` — "errno/wrnno numbering starts
  at 11, clear of base_classes.py's own reservation" — Code uses wrnno 1, 2, 3 (inside base_classes'
  reserved wrnno 1-2); SPECIFICATION.md:1900-1906 lists NTP as still numbering inside the reserved
  range. · related: XCUT.T07 · [H01]
- **NET.N015** LIMIT · `src/asy_ntp_client.py:5, 384-414` — "Async NTP client + CET/CEST local-time
  helper" / "Time of March change to CEST" — DST switch dates are the EU rule regardless of the
  configured GMT/DST offsets. · covered-by: NET.T03 · [H01]
- **NET.N016** LIMIT · `src/asy_ntp_client.py:37, 455-459` — "_NTP_ASYNC_INTERV = const(3) # 3 times
  interval considered as out of sync" — The stale-after-3×-interval rule can never fire (counter reset
  at every due resync). · covered-by: NET.S03 · [H01]
- **NET.N017** PLATFORM · `src/asy_ntp_client.py:39-42` — "_NTP_CONN_TIMEOUT = const(5000) # 5s ..." /
  "_NTP_SYNC_RETRIES = const(3)" / "_NTP_RETRY_INTERV = const(15)" / "_NTP_BACKOFF_MULT = const(2)" —
  Retry/backoff timing constants (parity vs legacy retry timing). · related: PAR.T04, NET.T03 · [H01]
- **NET.N018** INVAR · `src/asy_ntp_client.py:44-45` — "not const()-wrapped so tests can redirect it to
  a fake server's ephemeral port (binding real port 123 needs root)" — Shipped constant shaped for a
  test hook (low). · [H01]
- **NET.N019** PLATFORM · `src/asy_ntp_client.py:47-48` — "_NTP_ERA_SECONDS = const(4294967296) # 2**32
  - one full NTP era (32-bit seconds field wraps ~2036)" — Era-wrap handling (bigint constant on rp2). ·
  related: NET.T03, MEM.T07 · [H01]
- **NET.N020** TODO · `src/asy_ntp_client.py:49-53` — "Bump both forward occasionally to stay \"recent
  enough\"/\"far enough out\"." — Maintenance obligation on the plausibility window (min 2025-01-01, max
  2100-01-01) with no trigger. · related: NET.T03 · [H01]
- **NET.N021** PLATFORM · `src/asy_ntp_client.py:55-58, 247-251` — "RFC 5905 Leap Indicator top-2-bits:
  3 = server's own clock is unsynchronized" / "stratum 0 = Kiss-o'-Death packet" — Reply validation
  covers LI and stratum only (no mode/version/origin check). · covered-by: NET.T03 · [H01]
- **NET.N022** LIMIT · `src/asy_ntp_client.py:73` — "NTP_Offset_S ... description=\"Added to Unix time;
  affects system time and all timestamps.\"" — The offset shifts the RTC itself and every stored
  timestamp. · covered-by: NET.T11 · [H01]
- **NET.N023** MIRROR · `src/asy_ntp_client.py:76-80` — "That group is declared once, by
  system_service.py's own @web-group tag; this file only adds fields to it." — Cross-file @web group
  contribution by convention. · related: GEN.T03 · [H01]
- **NET.N024** ASSUME · `src/asy_ntp_client.py:101-107` — "whichever module wires this up decides the
  real deployment value at construction time" / "both round up to the 10s check tick (Part C.7.2)" —
  Real timeouts come from codegen wiring; retry granularity is the 10 s tick. · related: NET.S02 · [H01]
- **NET.N025** SETTLED · `src/asy_ntp_client.py:115, 441-442` — "0, # no failure streak: an unreachable
  server is routine here, never a restart (Part C.7.2)" / "Never gives up (Part C.7.2)" — Design: no
  supervisor restart on NTP failure. · [H01]
- **NET.N026** INVAR · `src/asy_ntp_client.py:123-125` — "network_available ... - caller must hold
  wifi_mode_lock" — Lock precondition by caller discipline. · related: NET.T02 · [H01]
- **NET.N027** INVAR · `src/asy_ntp_client.py:151-153, 431-432` — "Must be called before
  wifi_mode_lock.acquire(), never after: get_dns_server() gates on wifi_mode_lock.locked() itself" —
  Ordering invariant; the gate still returns None whenever anyone else holds the lock. · covered-by:
  NET.S05 · [H01]
- **NET.N028** SUPPRESS · `src/asy_ntp_client.py:154-158` — "except Exception as e: # caller-supplied
  callback - could legitimately misbehave" wrn_s "get_dns_server() callback failed:" wrnno=3 — Callback
  failure swallowed. · [H01]
- **NET.N029** SUPPRESS · `src/asy_ntp_client.py:176-180` — "except (ValueError, TypeError) as e: #
  malformed addr" → errno 13 — Construction failure swallowed. · [H01]
- **NET.N030** INVAR · `src/asy_ntp_client.py:181-188` — "write_and_recvfrom()/disconnect() never raise
  ... so no try/except is needed here" — No `finally: disconnect()`; a cancel mid-fetch leaks the PCB. ·
  covered-by: NET.S13 · [H01]
- **NET.N031** LIMIT · `src/asy_ntp_client.py:183-185` — "b\"\\x1b\" + bytearray(47), 1024," — 1024-byte
  receive for a 48-byte reply; transmit timestamp all-zero; source address discarded. · covered-by:
  NET.S10, NET.S19 · [H01]
- **NET.N032** ASSUME · `src/asy_ntp_client.py:205-209` — "None counts as 0 ... matching
  base_classes.py's LockedCounter.increment() this replaces" / "min(current + 1, 0xFFFFFFFF)" —
  Saturation bound is a bigint on rp2 (above 2**30) (low). · related: MEM.T07 · [H01]
- **NET.N033** SUPPRESS · `src/asy_ntp_client.py:214-218` — wrn_s "network_available() callback failed:"
  wrnno=1 — Callback failure swallowed to "network down". · [H01]
- **NET.N034** ASSUME · `src/asy_ntp_client.py:253-257` — "assume the current NTP era first" / "a
  still-wrapped reply from the next NTP era (RFC 5905 7.3) - reinterpret and recheck" — Era handling
  heuristic via the plausibility floor. · related: NET.T03 · [H01]
- **NET.N035** LIMIT · `src/asy_ntp_client.py:275-293` — "if not synced at all,
  self.ntp_time_hours_counter() will permanently try to sync" / err_s "Could not arm NTP retry timer:"
  errno=16 / "Maximum retries reached, cancelling sync!" errno=17 — ONE_SHOT retry timer; 16/17 are not
  episode-limited (persisted per exhaustion). · related: NET.T03, XCUT.S02 · [H01]
- **NET.N036** SETTLED · `src/asy_ntp_client.py:295-304` — "C.7.1's repeat rule, per distinct code: a
  dead server fails every attempt, so a slot per attempt would empty the ring." — Episode rule for
  11-15, 21 and wrnno 2. · related: XCUT.T07 · [H01]
- **NET.N037** LIMIT · `src/asy_ntp_client.py:330-349` — "alarm-pool exhaustion (ENOMEM, see CLAUDE.md)
  - degrades gracefully; NTP refresh scheduling just never starts" — Print-only failure; NTP (and the
  sync-age counter) then never runs, with nothing persisted. · related: XCUT.T04 · [H01]
- **NET.N038** LIMIT · `src/asy_ntp_client.py:357-361` — "def stop_ntp_timer" / "def stop_counter_timer"
  — No production caller. · covered-by: SENS.S26 · [H01]
- **NET.N039** SUPPRESS · `src/asy_ntp_client.py:365` — "# type: ignore[return-value]" — get_data()
  narrowing. · related: SENS.T08 · [H01]
- **NET.N040** LIMIT · `src/asy_ntp_client.py:416-422` — "an operator's resync must not wait out a long
  backoff step" — Force-sync does not clear `Synced` (legacy did). · covered-by: NET.S06 · [H01]
- **NET.N041** DRIFT · `src/asy_ntp_client.py:425-426` — "matches every _init_<sensor>() in the three
  promoted drivers" — Four sensor drivers are promoted (ISL29125 included); same text at
  `src/asy_wifi_service.py:816` (low). · related: DOC.S08 · [H01]
- **NET.N042** LIMIT · `src/asy_ntp_client.py:433-440` — "await self.wifi_mode_lock.acquire()" ...
  "except RuntimeError: # in case it's already released somehow" — Lock held across the whole DNS+fetch
  attempt; double-release swallowed (SUPPRESS). · covered-by: NET.S02 · [H01]
- **NET.N043** LIMIT · `src/asy_ntp_client.py:450-453` — err_s "Missing NTP configuration, defaulting
  interval to 12h!" errno=18 — Degraded 12 h default; persisted on every 10 s tick while the config read
  fails (no repeat rule). · related: SENS.T15, XCUT.T07 · [H01]
- **NET.N044** LIMIT · `src/asy_ntp_client.py:476-483` — "await self._increment_last_sync_age()" per 1 s
  ThreadSafeFlag tick — LastSyncAge counts wake-ups, not elapsed seconds. · related: XCUT.T21 · [H01]

## src/asy_udp_socket.py

- **NET.N045** INVAR · `src/asy_udp_socket.py:8` — "Every I/O method returns its documented None-shaped
  sentinel, never raises (__init__ excepted)." — Never-raise contract upheld by per-method broad catches
  · related: NET.T05 · [H02]
- **NET.N046** SUPPRESS · `src/asy_udp_socket.py:21` — "except ImportError: # typing has no runtime
  presence on MicroPython" — Swallowed ImportError for `typing` · [H02]
- **NET.N047** ASSUME · `src/asy_udp_socket.py:30` — "_RETRY_BACKOFF_S = const(0.5) # pause between a
  failed connect()/bind() (or setup) attempt and the next" — Float `const()` backoff; every failed setup
  costs ≥0.5 s inside the caller's time budget · related: NET.T05 · [H02]
- **NET.N048** SUPPRESS · `src/asy_udp_socket.py:48` — "elif not isinstance(addr, (bytes, bytearray)): #
  type: ignore[unreachable] # real at runtime" — mypy suppression in shipped code · [H02]
- **NET.N049** SUPPRESS · `src/asy_udp_socket.py:93-99` — "except (OSError, MemoryError, TypeError): #
  setup itself failed, or a non-int conn_tries raised from the while condition." — Socket
  creation/connect/bind failures swallowed silently (no log, no errno surfaced); caller only sees
  `connected == False` · related: NET.T05 · [H02]
- **NET.N050** INVAR · `src/asy_udp_socket.py:105-107` — "assuming self._connect_lock is already held -
  split out so _connect()'s self-heal path can call this directly without deadlocking on the same
  non-reentrant lock" — Caller-held-lock precondition by convention · [H02]
- **NET.N051** SUPPRESS · `src/asy_udp_socket.py:118-119, 122-123` — "except (OSError, MemoryError): ok
  = False" — Teardown failures reported only as a bool; this class has no logger (:205-206) · related:
  NET.T05 · [H02]
- **NET.N052** SUPPRESS · `src/asy_udp_socket.py:136` — "return False # type: ignore[unreachable] # mypy
  can't see the mutation" — mypy suppression in shipped code · [H02]
- **NET.N053** SUPPRESS · `src/asy_udp_socket.py:145-148` — "except (OSError, MemoryError, TypeError): #
  TypeError: a malformed mask/timeout_ms/wait_time_ms" — Poll failure collapses to "not ready" · [H02]
- **NET.N054** SUPPRESS · `src/asy_udp_socket.py:159-160` — "except (OSError, MemoryError, TypeError): #
  TypeError: a malformed addr/msg... pass" — Send failure swallowed to `None` · [H02]
- **NET.N055** SUPPRESS · `src/asy_udp_socket.py:167-168` — "except (OSError, MemoryError, TypeError): #
  TypeError: a malformed msg, matching sendto()'s reasoning / pass" — Write failure swallowed to `None`
  · [H02]
- **NET.N056** WORKAROUND · `src/asy_udp_socket.py:174-177` — "The 1.29 stub types recvfrom()'s address
  as socket's full _Address union... return self.sock.recvfrom(buf) # type: ignore[return-value]" — Stub
  over-breadth worked around with a suppression; removal trigger none stated · related: PLAT.T05 · [H02]
- **NET.N057** DRIFT · `src/asy_udp_socket.py:176` — "This socket is always AF_INET/SOCK_DGRAM (see
  _open())." — No `_open()` exists; creation is in `_connect()` (:73-83) · covered-by: NET.S18 · [H02]
- **NET.N058** INVAR · `src/asy_udp_socket.py:204-206` — "this class owns no logger, so the caller logs
  it (Part C.7's bool rule)" — Callers must check and log `disconnect()`'s result · related: NET.S13 ·
  [H02]

## src/asy_webserver_service.py

- **NET.N059** ASSUME · `src/asy_webserver_service.py:658-660` — "Captive-portal redirect fallback...
  see SPECIFICATION.md Part A.5 for the full mechanism and why no try/except is needed." — Hotspot 302
  relies on Microdot `redirect()` · related: NET.T09 · [H02]

## src/asy_wifi_service.py

- **NET.N060** INVAR · `src/asy_wifi_service.py:4-6` — "\"Attempt\" operations persist a real errno via
  self.pr.err_s() and set self.hw_op_failed... routine state observations degrade silently via
  self.pr.err() instead. errno numbering starts at 11, same convention as asy_ntp_client.py." — Two-tier
  error convention (persisted vs print-only) kept by per-site discipline; numbering mirrors NTP ·
  related: XCUT.T07 · [H02]
- **NET.N061** SUPPRESS · `src/asy_wifi_service.py:22` — "except ImportError: # typing has no runtime
  presence on MicroPython" — Swallowed ImportError for `typing` · [H02]
- **NET.N062** SETTLED · `src/asy_wifi_service.py:41-42` — "0 also doubles as this driver's \"not
  configured yet\" sentinel (routes to hotspot fallback" — Empty SSID = unconfigured → immediate hotspot
  (:441-443), relevant to first boot after reflash · covered-by: PAR.S08 · [H02]
- **NET.N063** LIMIT · `src/asy_wifi_service.py:44-46` — "PW: real passphrase length is WPA2-PSK's 8-63
  *when used* - special=\"\" bypasses that for an intentionally open/unsecured network." — `""` = open
  network (legacy meant "unchanged"); raw 64-hex PSK excluded · covered-by: NET.S17 · [H02]
- **NET.N064** PLATFORM · `src/asy_wifi_service.py:48` — "32 = network.hostname()'s real cap" — Platform
  hostname limit behind the 1-32 bound (legacy 1-63) · covered-by: NET.S17 · [H02]
- **NET.N065** MIRROR · `src/asy_wifi_service.py:65-68` — "_FIELDS = const((\"Mode\", \"Connected\",
  \"IP\", \"TS\")) # kept in sync with WIFI's own fields above" — Duplicate field list kept in sync by
  hand (mypy namedtuple limitation) · [H02]
- **NET.N066** PLATFORM · `src/asy_wifi_service.py:71-72` — "country()/hostname() raise outside 2 / 32
  bytes and connect() overflows past a 32-byte SSID (SPECIFICATION.md C.7.4)" — cyw43/network byte-bound
  facts at 1.29 · covered-by: NET.T07 · [H02]
- **NET.N067** MIRROR · `src/asy_wifi_service.py:89-91` — "A value outside the field's bounds is dropped
  rather than installed... buildgen.validate refuses it at build time; this keeps it bootable." —
  Runtime silently falls back to the built-in default; buildgen is the primary check · related: GEN.T01
  · [H02]
- **NET.N068** ASSUME · `src/asy_wifi_service.py:110-111` — "20 * 0.5s = 10s max wait for isconnected()
  to clear... a real disconnect() completes far faster than this." — Unmeasured bound; timeout persists
  errno 18 (:348) · related: NET.T01 · [H02]
- **NET.N069** SETTLED · `src/asy_wifi_service.py:126` — "_PHASE_DEACTIVATED = const(3) # terminal -
  WLAN fully deactivated, needs a task/device restart" — Permanent deactivation is intended (A.4); only
  a restart leaves it · related: SEC.T04 · [H02]
- **NET.N070** TODO · `src/asy_wifi_service.py:168-169` — "its history is expected to fold into a
  separate combined \"Networking\" REST endpoint later" — Future endpoint that no doc tracks ·
  covered-by: NET.S18 · [H02]
- **NET.N071** SUPPRESS · `src/asy_wifi_service.py:204-210` — "Observation-tier: a status query failing
  (WLAN mid-transition/deinitialized) is routine enough to degrade silently" — `except Exception` →
  print-only `pr.err`; same pattern at :215-217, :239-242, :510-511, :645-646, :743-745, :761-765 ·
  related: XCUT.T24 · [H02]
- **NET.N072** SUPPRESS · `src/asy_wifi_service.py:215-217` — "except Exception as e: # observation-tier
  - see _wlan_status_or_none()'s comment" — Broad catch, print-only (isconnected) · [H02]
- **NET.N073** WORKAROUND · `src/asy_wifi_service.py:235-236` — "stations command needs no other status
  commands close before (and does not support \"async with\"!)" — 100 ms sleep under the lock for a
  cyw43 quirk; unverified, removal trigger none stated · related: NET.T08 · [H02]
- **NET.N074** SUPPRESS · `src/asy_wifi_service.py:239-242` — "except Exception as e: # observation-tier
  (polled every wifi_refresh_sec while hotspot is active)" — Broad catch, print-only; failure reads as
  "no clients" and can start the hotspot timer · [H02]
- **NET.N075** SUPPRESS · `src/asy_wifi_service.py:244` — "# type: ignore[return-value] # stub types
  status(str) as int; real AP-mode \"stations\" returns a list per MicroPython docs" — Stub defect
  worked around by suppression in shipped code · related: PLAT.T05 · [H02]
- **NET.N076** SUPPRESS · `src/asy_wifi_service.py:250-255, 259-262, 266-269` — "could misbehave, so
  this degrades silently rather than feeding hw_op_failed/_error_check()" — Three broad catches around
  LED on/off/toggle, print-only · [H02]
- **NET.N077** SUPPRESS · `src/asy_wifi_service.py:291-293` — "except Exception as e: self.hw_op_failed
  = True; await self.pr.err_s(\"Error switching WLAN mode:\", e, errno=11)" — Mode-switch failure
  persisted; the fixed 2+1+1 s sleeps run under `wifi_mode_lock` · related: NET.T02 · [H02]
- **NET.N078** SETTLED · `src/asy_wifi_service.py:304-307` — "Both left as-is on a task restart, not
  reset to _PHASE_STA_SEEKING - see SPECIFICATION.md Part A.4's \"Permanent WiFi deactivation\" bullet."
  — Comment vs :303/:311 (`hotspot_started_once` reset, `reconn_wifi` forced) · covered-by: NET.S09 ·
  [H02]
- **NET.N079** SUPPRESS · `src/asy_wifi_service.py:312-314` — "except Exception as e: # rare (once per
  task (re)start) - safe default forces a clean reconnect" — Broad catch, print-only · [H02]
- **NET.N080** RISK · `src/asy_wifi_service.py:320-323` — "self._conn_phase = _PHASE_DEACTIVATED / await
  self.pr.wrn_s(\"Missing WLAN configuration!\", wrnno=1)" — Any failed `LedWifiOn` config read at task
  start deactivates WLAN until a restart (degraded mode; with `CORE.S02`) · related: NET.T01 · [H02]
  ⟨quote not matched at the anchor⟩
- **NET.N081** LIMIT · `src/asy_wifi_service.py:358-366` — "await self.pr.wrn_s(\"Missing WLAN
  configuration!\", wrnno=2)" — Missing hotspot config: AP never activated but `hotspot_started_once = True`,
  so the next streak deactivates WLAN (low) · related: NET.T01 · [H02]
- **NET.N082** PLATFORM · `src/asy_wifi_service.py:378-380` — "see SPECIFICATION.md Part F.2 for why
  STAT_GOT_IP isn't STA-only. The active() guard below is kept regardless" — AP-mode status semantics
  relied on · related: NET.S08 · [H02]
- **NET.N083** RISK · `src/asy_wifi_service.py:389-394` — "Guard against leaking a duplicate concurrent
  DNSServer.run() task... same \"is None or .done()\" convention system_service.py's own
  start_and_check_tasks() already uses" — Captive DNS runs as an unsupervised task; its exceptions are
  never retrieved · related: XCUT.S12 · [H02]
- **NET.N084** INVAR · `src/asy_wifi_service.py:410-412` — "PERIODIC, per C.9: a dropped soft callback
  is simply re-fired one period later, and the first one delivered ends the repeats" — Relies on
  `reconnect_wifi()` deinit-ing the timer on first delivery · related: XCUT.T04 · [H02]
- **NET.N085** SUPPRESS · `src/asy_wifi_service.py:419-422` — "except (OSError, MemoryError) as e: #
  alarm-pool exhaustion (ENOMEM) - matches asy_ntp_client.py's own Timer.init() guards" — Timer arm
  failure print-only, retried next cycle; mirrors NTP's guard · related: XCUT.T04 · [H02]
- **NET.N086** SUPPRESS · `src/asy_wifi_service.py:454-457` — "except Exception as e: self.hw_op_failed
  = True; await self.pr.err_s(\"Error attempting STA connect:\", e, errno=13)" — Broad catch, persisted
  · [H02]
- **NET.N087** RISK · `src/asy_wifi_service.py:469-473` — "await asyncio.sleep(60) # retry previously
  successful connecion in one minute" — 60 s sleep while `_run_sta_mode` holds `wifi_mode_lock` ·
  covered-by: NET.S01 · [H02]
- **NET.N088** SETTLED · `src/asy_wifi_service.py:485-492` — "Permanently no WLAN connection, no
  connection to hotspot. Deactivating WLAN!" — Second streak after a hotspot → permanent deactivation
  (A.4 intentional) · related: SEC.T04 · [H02]
- **NET.N089** SUPPRESS · `src/asy_wifi_service.py:499-501` — "except Exception as e: ... errno=16" —
  Broad catch, persisted · [H02]
- **NET.N090** SUPPRESS · `src/asy_wifi_service.py:510-511` — "except Exception as e: #
  observation-tier" — ifconfig failure → `IP` None · [H02]
- **NET.N091** INVAR · `src/asy_wifi_service.py:515-516` — "the isinstance check is defense-in-depth,
  not a scenario a real (schema-validated) caller hits" — Relies on schema validation upstream (low) ·
  [H02]
- **NET.N092** SUPPRESS · `src/asy_wifi_service.py:524-525` — "except RuntimeError: # in case it's
  already released somehow / pass" — Double release swallowed silently (same shape as
  `Lockable.__aexit__`) · related: CORE.S13 · [H02]
- **NET.N093** ASSUME · `src/asy_wifi_service.py:551, 556` — "await asyncio.sleep(5) # allow final tasks
  of calling function" / "await asyncio.sleep(3) # wait once for whatever else to settle" — Unexplained
  fixed settle delays (legacy-derived?) · related: PAR.T04 · [H02]
- **NET.N094** RISK · `src/asy_wifi_service.py:570-571` — "if status != network.STAT_GOT_IP: await
  self._start_hotspot()" — Full mode switch repeated on any non-GOT_IP tick · covered-by: NET.S08 ·
  [H02]
- **NET.N095** LIMIT · `src/asy_wifi_service.py:608` — "\"WLAN authentication failed - wrong password,
  or the AP dropped mid-handshake\"" — wrnno 4 cannot distinguish a wrong password from a handshake drop
  · [H02]
- **NET.N096** LIMIT · `src/asy_wifi_service.py:619` — "await self._episode_wrn(7, \"WLAN undefined
  state:\", status)" — Unexpected-status case, persisted once per episode · related: NET.T12 · [H02]
- **NET.N097** INVAR · `src/asy_wifi_service.py:624-630` — "C.7.1's repeat rule, per DISTINCT code...
  Repeats still count" — Episode bitmap `1 << wrnno` assumes small wrnnos; episode ends only on a
  successful connect · related: XCUT.T07 · [H02]
- **NET.N098** SUPPRESS · `src/asy_wifi_service.py:645-646` — "except Exception as e: #
  observation-tier" — Diagnostic print failure swallowed · [H02]
- **NET.N099** SUPPRESS · `src/asy_wifi_service.py:667-669` — "except (OSError, MemoryError) as e: #
  alarm-pool exhaustion (ENOMEM) - degrades gracefully... (uptime counting just never starts this
  cycle)" — Timer failure print-only; `WifiUptime` then never counts, and nothing retries until a
  supervisor restart · related: XCUT.T04 · [H02]
- **NET.N100** SUPPRESS · `src/asy_wifi_service.py:681-684` — "return await self._get_meas_data() #
  type: ignore[return-value]" — mypy suppression in shipped code; data is a 1 Hz cache · [H02]
- **NET.N101** RISK · `src/asy_wifi_service.py:693-698` — "await self.pr.err_s(\"Refusing\", key, \"-
  over the radio's byte bound\", errno=20)" — Client input error persisted into the fault ring per
  refused key · related: CORE.S11 · [H02]
- **NET.N102** SUPPRESS · `src/asy_wifi_service.py:709` — "for field, value in zip(schema, values): #
  noqa: B905 - MicroPython zip() rejects strict=" — ruff suppression in shipped code · [H02]
- **NET.N103** ASSUME · `src/asy_wifi_service.py:705-715` — "safe.append(str(live[2])) # every radio
  field's default is a str" — Over-bound stored value silently replaced by default (wrnno 8) · related:
  NET.T07 · [H02]
- **NET.N104** INVAR · `src/asy_wifi_service.py:735-737, 780` — "network_available() assumes the caller
  holds wifi_mode_lock; every getter below checks .locked() itself and degrades. A new getter picks one
  shape deliberately" — Part C.8's "Known inconsistency": two locking shapes by convention · related:
  NET.T02 · [H02]
- **NET.N105** RISK · `src/asy_wifi_service.py:739-740, 757-758, 776-777` — "if
  self.wifi_mode_lock.locked(): return None" — Getters return None/False whenever the lock is held (60 s
  sleep, NTP attempt) · covered-by: NET.S05 · [H02]
- **NET.N106** PLATFORM · `src/asy_wifi_service.py:760-765` — "Per extmod/network_cyw43.c, querying
  \"rssi\" outside STA mode raises ValueError(\"STA required\"), a routine failure while hotspot_mode is
  active - still logs." — Error print on every /status in AP mode · covered-by: NET.S15 · [H02]
- **NET.N107** SETTLED · `src/asy_wifi_service.py:793-794` — "Uniform setter return contract
  (project-wide decision): always True here" — Setter always reports success · [H02]
- **NET.N108** DRIFT · `src/asy_wifi_service.py:815-818` — "matches every _init_<sensor>() in the three
  promoted drivers" / "see SPECIFICATION.md Part C.7 for the real bug this fixed" — `src/` has four
  sensor drivers (SCD30, SGP40, BMP3xx, ISL29125) (low) · [H02]
- **NET.N109** LIMIT · `src/asy_wifi_service.py:823-824` — "self.pr.all(\"WLAN is deactivated.\")" —
  Deactivated phase loops forever at `wifi_refresh_sec` with no exit short of restart · related: NET.T01
  · [H02]
- **NET.N110** LIMIT · `src/asy_wifi_service.py:837-840` — "\"Giving up after repeated WLAN hardware
  failures, restarting task.\", errno=17" — Degraded path hands off to the supervisor · related:
  XCUT.T02 · [H02]
- **NET.N111** RISK · `src/asy_wifi_service.py:843-858` — "await self.time_counter_trigger_event.wait()"
  — Uptime counts flag wake-ups (lost under lock stalls) and counts in AP mode · covered-by: NET.S02 ·
  [H02]

## src/captive_dns.py

- **NET.N112** INVAR · `src/captive_dns.py:7` — "Malformed/off-subnet/truncated input is dropped, never
  raised." — Never-raise contract backed by broad catches (:105, :133, :187) · related: NET.T06 · [H02]
- **NET.N113** SUPPRESS · `src/captive_dns.py:19` — "except ImportError: # typing has no runtime
  presence on MicroPython" — Swallowed ImportError for `typing` · [H02]
- **NET.N114** MIRROR · `src/captive_dns.py:30-35` — "This path once looped at zero delay, measured at
  ~5 warning lines a second in a real run (Part C.9's cascading-recovery-storm convention)." — 0.5 s → 5
  s backoff shape that `asy_uart_comm.py:97` claims to mirror · related: UART.S05 · [H02]
- **NET.N115** MIRROR · `src/captive_dns.py:42-43` — "Never raises for a malformed-but-str value;
  matches asy_dns_client.py's _is_ipv4_literal()." — Two IPv4 parsers kept consistent by hand (Part G
  duplicate candidate) · related: XCUT.T15 · [H02]
- **NET.N116** DRIFT · `src/captive_dns.py:72-73` — "see this module's own docstring: it's owned by
  AsyConnTime, not itself a SensorReader subclass" — Module docstring (:5-7) says neither (low) · [H02]
- **NET.N117** ASSUME · `src/captive_dns.py:89-91` — "a startup misconfiguration, not expected in normal
  operation, so it's worth a persisted errno" — Task then returns silently for the rest of the hotspot
  session · related: NET.T06 · [H02]
- **NET.N118** RISK · `src/captive_dns.py:119, 123` — "await self.pr.wrn_s(\"Invalid DNS request data or
  address, not sending response.\", wrnno=2)" — Persisted warnings without `repeat=` · covered-by:
  REST.S05 · [H02]
- **NET.N119** SUPPRESS · `src/captive_dns.py:133-136` — "except Exception as e: # nothing supervises
  this task - never let an unexpected exception here kill it." — Broad catch in an unsupervised task,
  errno 2 persisted, 3 s sleep · related: XCUT.T05 · [H02]
- **NET.N120** SUPPRESS · `src/captive_dns.py:140-148` — "disconnect() is documented as never raising,
  but nothing supervises this task - never let cleanup itself become the uncaught exception." — Cleanup
  catches CancelledError and Exception (errno 3) · related: XCUT.S12 · [H02]
- **NET.N121** INVAR · `src/captive_dns.py:150-153` — "logged here so a real socket or poll-slot leak
  over a long uptime leaves a trail" — C.7 bool rule for `disconnect()` (wrnno 3) · related: NET.T05 ·
  [H02]
- **NET.N122** SUPPRESS · `src/captive_dns.py:187-191` — "except Exception: # Truncated/malformed data
  (or non-bytes data, since this class is public)" — Parse failure (incl. MemoryError, decode errors) →
  empty domain · [H02]
- **NET.N123** LIMIT · `src/captive_dns.py:167-177` — "opcode is bits 3-6 of header byte 2; the question
  section... starts at byte 12" — QR bit unchecked; domain built by per-label string concatenation ·
  covered-by: NET.S12 · [H02]
- **NET.N124** LIMIT · `src/captive_dns.py:204-205` — "QDCOUNT=1, ANCOUNT=1... hardcoded, not echoed
  from the original header: this class always parses/echoes exactly one question" — Multi-question
  queries answered for the first question only (low) · related: NET.T06 · [H02]
- **NET.N125** LIMIT · `src/captive_dns.py:208-210` — "packet +=
  b\"\\x00\\x01\\x00\\x01\\x00\\x00\\x00\\x3c\\x00\\x04\" # Response type, ttl and resource data length"
  — Always an A record with TTL 60 s whatever QTYPE was asked · covered-by: NET.S12 · [H02]

## tests/network.py

- **NET.N126** PLATFORM · `tests/network.py:73-76` — "real driver: unchecked copy past a 32-byte field
  ... overflows cyw43's last_ssid_joined on silicon" — on silicon a >32-byte SSID reaching `connect()`
  is memory corruption; src must validate (the fake raises AssertionError to catch it); password >64
  bytes → EINVAL · related: NET.S17 · [H03]

## tests/test_asy_dns_client.py

- **NET.N127** SETTLED · `tests/test_asy_dns_client.py:45-46` — "this project is IPv4-only" — IPv4-only
  scope · [H03]
- **NET.N128** ASSUME · `tests/test_asy_dns_client.py:131-132` — "QNAME wire length is len(host) + 2
  regardless of label count" — size formula assumes no trailing dot/empty label; the tests cover only
  the 63-octet label guard, not a 255-octet QNAME or empty labels · covered-by: NET.S14 · [H03]
- **NET.N129** LIMIT · `tests/test_asy_dns_client.py:173-177,534-536` — "a plausible REST-configured
  NTP_Host paste error, that schema allowing 1024 characters with no per-label check" — the REST schema
  accepts wire-invalid host names; only `_build_query()` guards them · related: NET.S14 (the 1024 bound
  is SETTLED per plan §2.3) · [H03]
- **NET.N130** LIMIT · `tests/test_asy_dns_client.py:274-276` — "Documented limitation (module
  docstring): only a bare 2-byte compression pointer is supported for an answer's own name field" —
  uncompressed answer names stop parsing · covered-by: NET.S14 · [H03]
- **NET.N131** INVAR · `tests/test_asy_dns_client.py:553-558` — "resolve_ipv4()'s docstring promises
  \"never raises\" - previously true only because every real caller's port happened to be well-typed" —
  never-raise contract now guarded at construction · [H03]
- **NET.N132** LIMIT · `tests/test_asy_dns_client.py:569-571` — "no crafted malformed reply has ever
  been found to reach this IndexError/ValueError guard through real bytes" — guard proven only by faking
  `_parse_response` · [H03]

## tests/test_asy_ntp_client.py

- **NET.N133** INVAR · `tests/test_asy_ntp_client.py:393-394` — "Each helper does an unlocked
  get-then-set pair, safe only because nothing in between awaits" —
  `_set_synced()`/`_set_last_sync_age()`/... are race-free only while no `await` sits between read and
  write; not mechanically enforced · [H04]
- **NET.N134** LIMIT · `tests/test_asy_ntp_client.py:896-900` — "a resolver preferring IPv6 hands back a
  4-tuple, not the 2-tuple this file assumes" — an IPv6-preferring getaddrinfo() result makes
  AsyUDPSocket raise TypeError, caught so NTP degrades silently to "no reply"; pinned by this test ·
  [H04]
- **NET.N135** PLATFORM · `tests/test_asy_ntp_client.py:1073-1075` — "NTP's 32-bit \"seconds since
  1900\" field wraps in 2036, distinct from the ~2037 Unix time_t OverflowError" — era-rollover logic
  (RFC 5905 7.3) and a separate ~2037 time_t overflow on the target are relied upon; plausibility window
  hardcoded 2025-01-01..2100-01-01 in the test (:1095, :1104) because the consts are compiled away ·
  related: NET.T03 · [H04]
- **NET.N136** LIMIT · `tests/test_asy_ntp_client.py:1389-1391` — "so the \"distrust a stale sync\" net
  never engages - inherited byte for byte from legacy" — test pins the current behaviour that `Synced`
  never reverts to False under natural ticking (the 3x-interval staleness net is dead code in practice)
  · covered-by: NET.S03 · [H04]
- **NET.N137** LIMIT · `tests/test_asy_ntp_client.py:1414-1416` — "copied verbatim from deployed
  production code. This only proves branch selection and exception safety." — cettime()'s last-Sunday
  DST formula is not independently verified by the tests; only branch choice is · related: NET.T03 ·
  [H04]
- **NET.N138** ASSUME · `tests/test_asy_ntp_client.py:1795-1796` — "That should not happen after the
  exception audit, but the surrounding try/finally must not depend on it." — assumes
  `_run_ntp_sync_attempt` never raises post-audit; lock release still tested for the raise case · -
  (low) · [H04]
- **NET.N139** SUPPRESS · `tests/test_asy_ntp_client.py:1853-1856` — "wifi_mode_lock.release() raises
  RuntimeError - caught and swallowed rather than crashing the task" — src swallows a RuntimeError from
  a redundant lock release in asy_ntp_time()'s finally; pinned here · [H04]
- **NET.N140** SETTLED · `tests/test_asy_ntp_client.py:1917-1918` — "An unreachable server is routine
  for this task (Part C.7.2): a restart re-initialises nothing" — NTP never gives up and keeps no
  failure streak (give-up code 20 retired); pinned by 50-attempt test · related: NET.T03 · [H04]
- **NET.N141** LIMIT · `tests/test_asy_ntp_client.py:2206-2211` — "_handle_ntp_sync_failure()'s one-shot
  retry timer is armed only when ntp_synced is already True" — a never-synced client gets no fast retry,
  relying on the periodic retrigger · related: NET.T03 · [H04]

## tests/test_asy_udp_socket.py

- **NET.N142** LIMIT · `tests/test_asy_udp_socket.py:75-77` — "Some platforms' socket.getaddrinfo()
  returns an opaque sockaddr (bytes/bytearray) rather than a tuple" — AsyUDPSocket must accept a
  non-tuple addr only because of the test host; production callers pass tuples · - (low) · [H04]
- **NET.N143** SETTLED · `tests/test_asy_udp_socket.py:84-86` — "An invalid mode used to busy-loop
  forever inside _connect() with zero await points" — mode validated eagerly at construction;
  `_connect()`'s branch is binary (mutated `_mode` falls through to bind(), :1271-1273) · - (low) ·
  [H04]
- **NET.N144** LIMIT · `tests/test_asy_udp_socket.py:292` — "# AF_INET only, see asy_udp_socket.py" —
  AsyUDPSocket is IPv4-only · related: NET.T05 (low) · [H04]
- **NET.N145** SETTLED · `tests/test_asy_udp_socket.py:309-311` — "a datagram larger than the recv
  buffer is truncated to buf bytes with no error and no signal ... Documented rather than \"fixed\"" —
  silent UDP truncation is a caller-facing contract (MSG_TRUNC not exposed) · related: NET.T05 · [H04]
- **NET.N146** INVAR · `tests/test_asy_udp_socket.py:332-334` — "recvfrom() must return (b\"\", addr) -
  distinguishable from the (None, None) timeout/error sentinel" — zero-length datagram vs sentinel
  distinction; `data is not None` is what write_and_recvfrom() tests · [H04]
- **NET.N147** SETTLED · `tests/test_asy_udp_socket.py:372-374` — "Validating payload structure (NTP
  header, DNS query) is the caller's job, not this module's." — UDP layer is content-agnostic · - (low)
  · [H04]
- **NET.N148** ASSUME · `tests/test_asy_udp_socket.py:395-401` — "real rp2/lwIP is a different socket
  implementation and is covered instead by tests_hardware/bench/test_network_resilience.py, which
  confirmed the same property holds" — connected-socket source filtering is proven on the Unix port here
  and claimed confirmed on hardware (BACKLOG Q5, 2026-09-08) · related: NET.S19 · [H04]
- **NET.N149** SETTLED · `tests/test_asy_udp_socket.py:684-685,715` — "disconnect() now reports a failed
  unregister() via its own return value, since this logger-less class has no other way to signal it" —
  AsyUDPSocket has no logger; failures surface only through return values · - (low) · [H04]
- **NET.N150** ASSUME · `tests/test_asy_udp_socket.py:746-748` — "Neither real caller does this today
  (both use one AsyUDPSocket from a single coroutine at a time), but nothing enforced or documented that
  constraint" — single-coroutine use of an AsyUDPSocket is the real callers' pattern; ready() tolerates
  a concurrent disconnect anyway · - (low) · [H04]
- **NET.N151** ASSUME · `tests/test_asy_udp_socket.py:1180-1182` — "captive_dns.py's guard is `if data is not None and addr is not None:`,
  implicitly assuming the two are always both set or both None" — pairing contract of recvfrom()'s
  return, pinned here · - (low) · [H04]
- **NET.N152** RISK · `tests/test_asy_udp_socket.py:1206-1207` — "captive_dns.py discards sendto()'s
  return value, so a failed reply is silently swallowed one level above this module" — captive DNS reply
  failures are invisible · related: NET.T06 · [H04]
- **NET.N153** SETTLED · `tests/test_asy_udp_socket.py:1236-1238` — "Closed by widening every touching
  except clause to catch TypeError, not by re-validating on each access." — post-construction mutation
  of `_addr`/`_conn_tries` is absorbed by broader excepts · - (low) · [H04]
- **NET.N154** INVAR · `tests/test_asy_udp_socket.py:1323-1325,1330-1332` — "a per-instance asyncio.Lock
  serializes them against each other" — `_connect()`/`disconnect()` serialized; disconnect() can wait up
  to conn_tries × backoff · related: XCUT.T06 · [H04]
- **NET.N155** SETTLED · `tests/test_asy_udp_socket.py:1456-1458` — "calling it on a
  bound-but-unconnected server-mode socket is a caller misuse this file deliberately does not guard
  structurally" — write() on a server socket relies on the OSError path · - (low) · [H04]
- **NET.N156** INVAR · `tests/test_asy_udp_socket.py:1596-1598` — "it must not start swallowing
  asyncio.CancelledError, a BaseException subclass not in that tuple" — ready()'s widened except
  (OSError, MemoryError, TypeError) must never include CancelledError · related: XCUT.T19 · [H04]

## tests/test_asy_wifi_service.py

- **NET.N157** SETTLED · `tests/test_asy_wifi_service.py:252-254,2842-2844,2870-2872` — "a build that
  injected a 3-character hotspot password must not produce a device the CYW43 cannot bring up. It falls
  back to the schema's own default" — buildgen-injected hostname/hotspot password are schema defaults
  validated at runtime too (backstop to buildgen's check); non-str shapes keep the built-in default ·
  related: GEN.T01 · [H04]
- **NET.N158** SETTLED · `tests/test_asy_wifi_service.py:352-353` — "SSID's own schema min is relaxed to
  0 ... so the fresh, unconfigured default (\"\") self-validates" — SSID may be empty (empty → straight
  to hotspot, :2986) · covered-by: NET.S17 · [H04]
- **NET.N159** LIMIT · `tests/test_asy_wifi_service.py:527-528,538-539` — "PW comes back \"********\"
  even though the real cached default is \"\" - _mask_pw()'s callback overlay is unconditional" — GET
  always shows a masked PW, even for an open network or an invalid config manager, so a client cannot
  tell "" from a set password · related: NET.S16 · [H04]
- **NET.N160** SETTLED · `tests/test_asy_wifi_service.py:658-660` — "whichever phase of the
  ~2.9s-on/0.1s-off cycle is interrupted, cancellation must leave the LED lit" — hotspot LED flasher's
  cancel handler restores a steady-on LED · - (low) · [H04]
- **NET.N161** SUPPRESS · `tests/test_asy_wifi_service.py:818` — "_release_wifi_lock() - replaces 7
  duplicated try/except RuntimeError blocks" — src `_release_wifi_lock()` swallows RuntimeError on a
  redundant release (src/asy_wifi_service.py:521-525, "in case it's already released somehow") · [H04]
- **NET.N162** RISK · `tests/test_asy_wifi_service.py:852-853` — "this one awaits a settle sleep while
  holding the lock, so a supervisor-driven cancellation can land inside the critical section" — mode
  switch sleeps under wifi_mode_lock; cancellation mid-switch relies on the finally release · related:
  XCUT.T19 · [H04]
- **NET.N163** SETTLED · `tests/test_asy_wifi_service.py:893-894` — "backed by time_counter()'s 1Hz push
  (_update_wifi_snapshot()), not a live lock-aware query" — WiFi get_data() returns a cached 1 Hz
  snapshot · related: NET.S02 · [H04]
- **NET.N164** SETTLED · `tests/test_asy_wifi_service.py:1004-1005` — "a status/isconnected/ifconfig
  *query* failing degrades silently (returns a safe sentinel) instead of raising or feeding
  get_error_counter()" — observation-tier failures leave no persisted evidence · related: XCUT.T24 ·
  [H04]
- **NET.N165** LIMIT · `tests/test_asy_wifi_service.py:1175-1181` — "every \"returns a locked default\"
  test above proves the getter's defensive check against a synthetically pre-acquired lock" — during the
  60 s ESTABLISHED retry, REST getters return "don't know yet" sentinels (pinned) · covered-by: NET.S01
  · [H04]
- **NET.N166** SETTLED · `tests/test_asy_wifi_service.py:1222-1224` — "the ESTABLISHED branch's whole
  point is a silent, patient retry, not an escalation" — a previously established link never escalates
  to hotspot on outage · related: NET.T01 · [H04]
- **NET.N167** SETTLED · `tests/test_asy_wifi_service.py:1266,1307-1308,1329,1347-1348` — "PERIODIC
  keeps the timer armed, so the next period's fire still reconnects - no backstop needed" / "(errno 19
  is retired, C.7.1)" — hotspot shutoff uses a PERIODIC timer (C.9) so a dropped soft callback only
  delays by one period; the ONE_SHOT tick-count backstop and errno 19 are retired · related: XCUT.S02 ·
  [H04]
- **NET.N168** SETTLED · `tests/test_asy_wifi_service.py:1527-1528` — "Exactly item 29's shape: a W4
  beside a W5 on one outage must survive the dedup" — BACKLOG Q29's spurious-W4 evidence must not be
  deduped away · - (low) · [H04]
- **NET.N169** SETTLED · `tests/test_asy_wifi_service.py:1785-1791` — "the CYW43 firmware can leave
  isconnected() stuck True for well over 150s after a real outage ... CLAUDE.md's \"physical
  intervention as the accepted backstop\" pattern" — stuck-isconnected steady state pinned as benign
  (5/5 bench trials) · related: NET.T13 · [H04]
- **NET.N170** ASSUME · `tests/test_asy_wifi_service.py:1824-1825,2424-2426` —
  "_poll_sta_connect_status() never returns early on STAT_GOT_IP (existing behavior - it polls all 10
  iterations regardless), so this genuinely runs ~5s in real time" — integration tests pay the full 5 s
  poll; pins the no-early-break behaviour · covered-by: NET.S07 · [H04]
- **NET.N171** SETTLED · `tests/test_asy_wifi_service.py:1972-1974` — "_PHASE_DEACTIVATED is a
  deliberate, permanent WLAN-off state (Part A.4: a physical power-cycle is the recovery)" — task
  restarts never leave the deactivated phase · related: NET.T01 · [H04]
- **NET.N172** ASSUME · `tests/test_asy_wifi_service.py:2035-2037` — "A real exception checking
  wlan.isconnected()/active() at task-start time is rare" — frequency assumption; reconnect forced on
  the next iteration · - (low) · [H04]
- **NET.N173** TODO · `tests/test_asy_wifi_service.py:2669` — "not a named network.STAT_* constant yet -
  see this driver's own comment" — status 2 ("obtaining IP") handled as a magic number pending an
  upstream constant · covered-by: NET.T12 · [H04]
- **NET.N174** LIMIT · `tests/test_asy_wifi_service.py:2700-2702` — "HotspotPW is per-device
  configurable (SPECIFICATION.md Part C.14)" — the test writes HotspotPW via cfgmgr, but no
  SettingsGroup exposes it over REST (build-time only) · related: NET.S17 · [H04]
- **NET.N175** SETTLED · `tests/test_asy_wifi_service.py:2851-2853,2991` — "a device renamed through the
  web UI must keep that name across a reflash whose TOML says something else" — TOML hostname is only a
  default; stored config wins across reflash · related: PAR.T01 · [H04]
- **NET.N176** INVAR · `tests/test_asy_wifi_service.py:2878-2880` — "the radio bounds
  SSID/PW/Country/Hostname/HotspotPW in UTF-8 BYTES, where the schema counts characters" — C.7.4 byte
  bounds enforced separately from character bounds at write and at use · covered-by: NET.T07 · [H04]

## tests/test_captive_dns.py

- **NET.N177** LIMIT · `tests/test_captive_dns.py:95-96` — "A previously-silent gap: an out-of-range
  octet used to shift bits past its own byte position" — Regression pin for a fixed false-subnet-match
  bug in `_ipv4_to_int` (low) · [H05]
- **NET.N178** LIMIT · `tests/test_captive_dns.py:104-114, 704-718, 769-780` — "a wrongly-typed value
  must raise one of the exact types every caller in this file already guards against" — `_ipv4_to_int`,
  `DNSServer.run()` and `DNSQuery.response()` RAISE on non-str input rather than degrade; the str-typed
  public signature relies on callers only passing str · [H05]
- **NET.N179** INVAR · `tests/test_captive_dns.py:279-281` — "a wrong list here drops DNSSRV out of
  /status's errcount and out of the level registry, both silently" — The duck-typed fan-in accessor pair
  must list DNSSRV's logger; a wrong list fails silently at runtime, only this test catches it · [H05]
- **NET.N180** INVAR · `tests/test_captive_dns.py:810-812` — "safe only because
  AsyUDPSocket.disconnect() fully resets state for the next _connect()" — Reusing one DNSServer across
  hotspot activations depends on disconnect() fully resetting the socket state · [H05]
- **NET.N181** ASSUME · `tests/test_captive_dns.py:981-983` — "measured at ~5 wrn_s() lines/second
  before the fix" — Single measurement of the pre-fix empty-recvfrom spin rate; now backs off 0.5→1→2 s,
  cap 5 s (C.9) · [H05]
- **NET.N182** INVAR · `tests/test_captive_dns.py:1086-1088` — "AsyUDPSocket.disconnect() never raises,
  but now reports a failed unregister()/close() via its bool return - run() must actually check it and
  log" — Callers of disconnect() must check its bool; enforced here for captive_dns only · [H05]
- **NET.N183** INVAR · `tests/test_captive_dns.py:146-147` — "it must reuse the caller's logger
  identity/history, not get an independent PrintLogHistory of its own" — DNSQuery is built per request
  and must share DNSSRV's logger (low) · [H05] ⟨quote not matched at the anchor⟩

## tests/test_ntp_fram_system_integration.py

- **NET.N184** ASSUME · `tests/test_ntp_fram_system_integration.py:2, 304-309` — "Proves the "no
  cross-lock contention" assumption asy_fram_manager.py's comments rely on" — ntp_issynced() must only
  touch SensorReader's `_datalock`, never `wifi_mode_lock`; tested with a 1.0 s wait_for bound · [H05]

## tests/test_ntp_wifi_dns_integration.py

- **NET.N185** SETTLED · `tests/test_ntp_wifi_dns_integration.py:2` — "AsyNtpClient used to call
  get_dns_server_ip() after acquiring the shared wifi_mode_lock ... Fixed via _safe_get_dns_server(),
  called before acquiring the lock" — Ordering invariant: DNS-server lookup must happen before taking
  wifi_mode_lock · [H05]
- **NET.N186** ASSUME · `tests/test_ntp_wifi_dns_integration.py:365-367` — "a real arping probe got zero
  responses from a DUT `iw station dump` called associated" (BACKLOG open question 6, closed 2026-09-04)
  — Single dated real-hardware finding (CYW43 false-positive link) reproduced at mock tier as "sent,
  nothing back" · [H05]
- **NET.N187** SETTLED · `tests/test_ntp_wifi_dns_integration.py:400-402` — "the silent timeout
  persisted as errno 21 - once for the whole run (C.7.1's repeat rule) while still counted every time" —
  NTP handles its own failures (C.7.2); persistence deduplicates repeats · [H05]
- **NET.N188** LIMIT · `tests/test_ntp_wifi_dns_integration.py:182-184` — "it degrades via
  self.pr.err(), debug-level only and never persisted" — A wlan.ifconfig() exception leaves no FRAM
  evidence (observation-tier query) · [H05]

## tests/test_setter_microdot_integration.py

- **NET.N189** INVAR · `tests/test_setter_microdot_integration.py:253-254` — "toggling the WiFi status
  LED must never reconnect the WiFi connection" — setWiFiLED passes no post_fct · [H05]
- **NET.N190** ASSUME · `tests/test_setter_microdot_integration.py:505-510` — "asy_ntp_client.py's
  module docstring claims base_classes.py's generic _set_dict_cfg() gives full setter support" — The NTP
  setter path is proven only through a test-local route shaped like the real handler · [H05]

## digital_twin/README.md

- **NET.N191** RISK · `digital_twin/README.md:523-527` — "`asy_udp_socket.py`'s own `bind()` retry loop
  swallows the resulting `PermissionError` and gives up silently" — DNS server can silently never
  listen; no crash, no log-gate signal · related: SCR.S06 · [H06]
- **NET.N192** ASSUME · `digital_twin/README.md:532-533` — "stays fully healthy past NTP's own 5s fetch
  timeout" — Copied timing constant from src/ · [H06]

## digital_twin/_unix_port_udp_addr_shim.py

- **NET.N193** LIMIT · `digital_twin/_unix_port_udp_addr_shim.py:25-27, 74-76` —
  "`asy_udp_socket.AsyUDPSocket._connect = _patched_connect`" — Twin tests exercise patched
  `_connect`/`sendto`/`recvfrom`; the production plain-tuple address path is only exercised on hardware
  · [H06]
- **NET.N194** ASSUME · `digital_twin/_unix_port_udp_addr_shim.py:33-35` — "this project is IPv4-only
  (AsyUDPSocket's own addr type)" — IPv6 addresses pass through unnormalised · [H06]
- **NET.N195** ASSUME · `digital_twin/_unix_port_udp_addr_shim.py:41-43` — "Every real call site already
  hands over a numeric (host, port) tuple, so this getaddrinfo() is always local and never a DNS query"
  — A hostname would make the shim do a blocking real DNS lookup · [H06]

## digital_twin/network.py

- **NET.N196** PLATFORM · `digital_twin/network.py:109-112` — "cyw43_ll_wifi_join()'s -CYW43_EINVAL" /
  "real driver: unchecked copy past a 32-byte field" — Silicon-driver limits; an over-long SSID raises
  `AssertionError` only in the twin · [H06]
- **NET.N197** INVAR · `digital_twin/network.py:111-112` — "SSID over 32 bytes reached connect() -
  overflows cyw43's last_ssid_joined on silicon" — src/ must validate SSID length before `connect()`;
  the twin's assertion is the only guard at this tier · [H06]

## tests/test_digital_twin_bus_hazard_concurrency.py

- **NET.N198** LIMIT · `tests/test_digital_twin_bus_hazard_concurrency.py:353-355` — "A single
  disconnect, not repeated flapping: the ESTABLISHED retry branch is a genuine, non-fast-forwardable 60s
  sleep" — Repeated WiFi flapping is not covered at the twin tier (bench only) · [H06]

## tests_hardware/bench/test_hotspot_role_reversal.py

- **NET.N199** LIMIT · `tests_hardware/bench/test_hotspot_role_reversal.py:226-229` — "logs via pr.evt()
  (an ordinary event), not err_s()/wrn_s(), so the module's real errcount log should stay empty" —
  Malformed DNS traffic leaves no errcount trace (pinned). · [H07]

## tests_hardware/manual/manual_wifi.py

- **NET.N200** OPENQ · `tests_hardware/manual/manual_wifi.py:1-3, 38-48` — "genuinely unknown until
  tried"; "this test always reports PASS since either outcome is valid data" — Captive-portal
  auto-detection against the DNS-only spoof is an open question; recorded, never failed. · [H07]

## tests_hardware/device_scripts/wifi_country_hostname_edge_values.py

- **NET.N201** ASSUME · `tests_hardware/device_scripts/wifi_country_hostname_edge_values.py:2-3, 37-39`
  — "whose UTF-8 byte count exceeds the real 32-byte cap"; "asy_wifi_service.py's own try/except around
  both calls means neither should ever be able to crash the process" — Schema counts characters while
  the platform cap is bytes (pinned gap); hardcodes country "DE". · related: NET.S17 · [H07]

## tests_hardware/README.md

- **NET.N202** RISK · `tests_hardware/README.md:385-386` — "`kick_all_stations()` + `hard_reset()`
  recovers it, occasionally only on a second try" — Hotspot fallback after reset/flash is a known bench
  hazard. · [H08]
- **NET.N203** RISK · `tests_hardware/README.md:520-529` — "leads to `_PHASE_DEACTIVATED` - a terminal
  state only a real power-cycle clears" — Stage-6 permanent-WLAN-deactivation risk; `joined_hotspot`
  teardown relies on a `hard_reset()` fallback. · covered-by: HW.S25 · [H08]
- **NET.N204** SETTLED · `tests_hardware/README.md:530-543` — "confirmed working on real hardware
  (2026-09-03)" — Captive-portal 302 fallback verified on the dev build; dev result declared valid for
  wozi. · related: NET.T09 · [H08]
- **NET.N205** LIMIT · `tests_hardware/README.md:548-564` — "this is almost certainly phone-side" — Real
  Android (A54, One UI 8.5) showed no sign-in prompt; blamed on Private DNS / cached verdict,
  unconfirmed; no code changed. · related: NET.T09, WEB.T14 · [H08]
- **NET.N206** RISK · `tests_hardware/README.md:607-609` — "a device WDT-looping against a real router
  would hit the same stale-entry pattern" — Field caveat of the stale-AP-station reconnect mechanism
  (repeated :976-979); bench fix is harness-side only. · [H08]
- **NET.N207** DRIFT · `tests_hardware/README.md:626-632` — "Whether to add an independent reachability
  check is a real architectural question for the project owner, not decided here." — Presented as
  undecided; CLAUDE.md hard rule and BACKLOG.md:207-214 (item 6, closed) say it is settled (no probe,
  hard reset is the backstop). · related: NET.T13 · [H08]
- **NET.N208** SETTLED · `tests_hardware/README.md:787-791` — "\"WiFi available but no internet access\"
  is treated as equivalent to \"NTP/DNS unreachable\" for this device" — Scope decision for
  network-robustness tests. · - (low) · [H08]
- **NET.N209** SETTLED · `tests_hardware/README.md:819-828` — "**Deliberately not covered, and why**:
  DHCP flakiness/slowness/rubbish responses." — DHCP client lives in lwIP; a rogue DHCP responder could
  strand the DUT. · related: NET.T13 · [H08]
- **NET.N210** LIMIT · `tests_hardware/README.md:883-886` — "the backoff-growth branch itself remains
  unexercised by any test in this tier" — captive_dns `recv_fail_backoff_s` growth branch: open coverage
  gap. · [H08]
- **NET.N211** ASSUME · `tests_hardware/README.md:1004-1016` — "a plausible (not confirmed) explanation
  ... could plausibly cause a brief beacon gap" — Hotspot SSID visibility flicker attributed,
  unconfirmed, to `_configure_hotspot_ap()` re-running every 5 s; worked around by widening attempts. ·
  related: NET.S08 · [H08]

## REAL_HARDWARE_TEST_QUEUE.md (snapshot only; being updated by another session)

- **NET.N212** TODO · `REAL_HARDWARE_TEST_QUEUE.md:218` — "the substitution path itself is still
  unproven on silicon" — N2 PARTIAL: `_with_default()` hostname default substitution needs a boot with
  `Hostname` absent from persisted `config_WIFI.cfg` (one write). · [H08]
- **NET.N213** RISK · `REAL_HARDWARE_TEST_QUEUE.md:376-383` — "`PUT /system {\"SystemCmd\": \"reboot\"}`
  on its own leaves a stale station entry on the bench AP" — A hand REST reboot strands the DUT in
  hotspot mode indefinitely; kick first, expect a `hard_reset()` (~40 s). · [H08]

## tests_scripts/test_buildgen_validate.py

- **NET.N214** PLATFORM · `tests_scripts/test_buildgen_validate.py:84` — "8 characters is WPA2-PSK's own
  minimum - below it the CYW43 can't bring the hotspot up at all" — CYW43/WPA2 bound the validator
  relies on · related: NET.S16 · [H10]
- **NET.N215** MIRROR · `tests_scripts/test_buildgen_validate.py:1642-1647` — "assert
  init_int_default(src_dir, \"asy_ntp_client.py\", \"AsyNtpClient\", \"retry_s\") == 10" — Pins NTP
  backoff defaults 10/600 read by AST from src; build-time check ↔ src constants · related: NET.T03 ·
  [H10]
- **NET.N216** ASSUME · `tests_scripts/test_buildgen_validate.py:1682` — "AsyNtpClient would silently
  round it up to its 10s tick" — Runtime rounding behaviour that the build check pre-empts · [H10]

## tests_js/live-backend-put-matrix.test.js

- **NET.N217** LIMIT · `tests_js/live-backend-put-matrix.test.js:134-137` — "PW reads back as the fixed
  \"********\" overlay ... resubmitting it is not a no-op probe but a new password the backend would
  persist" — masked fields are never resubmit-probed; confirms a PUT of the mask would be stored ·
  related: NET.S16 · [H11]

## SPECIFICATION.md Part C.4 (Layer 3 Reader, 1624-1697)

- **NET.N218** INVAR · `SPECIFICATION.md:1695-1697` — "`asy_wifi_service.py`'s `callback=self._mask_pw`
  unconditionally overwrites the persisted `PW` with a fixed mask" — Masking contract (PUT-back of the
  mask seeded). · related: NET.S16 · [H12] ⟨quote not matched at the anchor⟩

## SPECIFICATION.md Part C.7.1 (Running errno/wrnno table, 1893-1941)

- **NET.N219** PLATFORM · `SPECIFICATION.md:1931` — "4 is cyw43-driver's catch-all for any failed auth
  or handshake ... not proof of a wrong password, BACKLOG item 29" — cyw43 status semantics. · [H12]

## SPECIFICATION.md Part C.7.2 (Which failures may end a task, 1943-1973)

- **NET.N220** SETTLED · `SPECIFICATION.md:1949-1952` — "the NTP task used to end after six failed syncs
  ... (owner, 2026-09-24). The legacy client never gave up." — NTP handled in place. · [H12]

## SPECIFICATION.md Part C.7.4 (Radio string bounds are bytes, 2002-2014)

- **NET.N221** PLATFORM · `SPECIFICATION.md:2004-2008` — "`network.country()` raises unless exactly 2
  bytes, `network.hostname()` above 32 bytes, and `WLAN.connect()` raises `EINVAL` on a key over 64
  bytes and copies an SSID over 32 bytes past its 36-byte buffer unchecked" — Pinned modnetwork/cyw43
  limits, incl. an upstream unchecked copy. · covered-by: NET.T07 · [H12]

## SPECIFICATION.md Part C.8 (Concurrency & locking model, 2016-2188)

- **NET.N222** LIMIT · `SPECIFICATION.md:2041-2044` — "`network_available()` requires the *caller* to
  already hold `wifi_mode_lock`, while its sibling getters assume the caller does *not* ... left as-is"
  — Known inconsistent lock contract. · related: NET.S05 · [H12]
- **NET.N223** RISK · `SPECIFICATION.md:2044-2045` — "the 60s STA-retry branch holds `wifi_mode_lock`
  while NTP's sync task waits on it — an accepted priority-inversion cost, not a bug" — Accepted 60 s
  stall. · covered-by: NET.S01 · [H12]

## SPECIFICATION.md Part C.9.1 (Read-trigger timer stagger, 2211-2298)

- **NET.N224** INVAR · `SPECIFICATION.md:2292-2298` — "a retry loop that fails non-raising (returns a
  sentinel) needs its own capped exponential backoff ... A retry loop never ends its task to \"retry by
  restart\"" — Convention; captive DNS 0.5→4 s (cap 5 s). · [H12]

## SPECIFICATION.md Part F.2 — Blocking calls / timeout-wrapping

- **NET.N225** SETTLED · `SPECIFICATION.md:3611-3617` — "**Decided: investigated, no `src/` change** ...
  a physical power cycle/`hard_reset()` is the accepted recovery" — CYW43 `isconnected()` false positive
  accepted; `WifiUptime` inaccuracy called cosmetic. · related: DOC.T14 · [H13]
- **NET.N226** ASSUME · `SPECIFICATION.md:3618-3620` — "a sustained outage essentially never
  self-resolves within 150s (5/5 trials ...); repeated brief flapping self-heals reliably instead (3/3
  trials, ~30s)" — Small-sample bench measurements that the residual-window argument below reuses. ·
  related: HW.T16 · [H13]
- **NET.N227** PLATFORM · `SPECIFICATION.md:3621-3622` — "`network.STAT_GOT_IP` is not STA-only (an AP
  interface reports it too) — `_run_hotspot_mode()`'s `status != STAT_GOT_IP` branch is only true on the
  first tick" — CYW43/port fact that makes a code branch nearly dead. · related: NET.S07 · [H13]

## SPECIFICATION.md Part F.5.5 — Stub defects repaired at install

- **NET.N228** SUPPRESS · `SPECIFICATION.md:3821-3824 (site src/asy_udp_socket.py:177)` — "The one place
  a `type: ignore` *is* right is `asy_udp_socket.py`'s `recvfrom()`" — `# type: ignore[return-value]` at
  src/asy_udp_socket.py:177 for AF_INET-only narrowing; the same file also carries two `type: ignore[unreachable]`
  (:48, :136) the doc does not mention. · [H13]

## SPECIFICATION.md Part I.3 — Bounded response assembly

- **NET.N229** SETTLED · `SPECIFICATION.md:4927, 4931-4932` — "the bound is settled, BACKLOG's deferred
  list ... a shorter `NTP_Host` bound is the lever, and the owner settled it" — Owner decision keeping
  `NTP_Host` at 1,024. · [H13]

## SPECIFICATION.md Part I.6 — Request-body cap (sits inside Part J)

- **NET.N230** SETTLED · `SPECIFICATION.md:5290-5293` — "**Related, deliberately not changed:**
  `NTP_Host`'s 1024-character bound mirrors the deployed pre-refactor handler ... the owner's call" —
  Settled bound (plan §2.3). · [H13]

## CLAUDE.md

- **NET.N231** SETTLED · `CLAUDE.md:197-203` — "a power cycle/`hard_reset()` is a deliberately stable,
  intended recovery feature ... don't propose an independent reachability-probe mechanism" — Applies to
  the CYW43 `isconnected()` false positive; BACKLOG open question 6 is a closed pointer (BACKLOG.md:207,
  213). · related: NET.T13 · [H14]

## BACKLOG.md

- **NET.N232** LIMIT · `BACKLOG.md:201-203` — "POLLERR/POLLHUP delivery (never observed -
  AsyUDPSocket.ready()'s handling is correct but effectively dead code on this platform)" — #5 closed
  stub: a code path unreachable on rp2/lwIP. · related: NET.T05 · [H15]
- **NET.N233** SETTLED · `BACKLOG.md:207-214` — "closed (2026-09-08): investigated, no src/ change." —
  #6 independent WiFi reachability check rejected; stub kept for citations ("don't renumber"). · [H15]
- **NET.N234** SETTLED · `BACKLOG.md:316-323` — "an AP vanishing mid-association reads as a wrong
  password" — #29 spurious `W4` is cyw43 BADAUTH behaviour; the bench outage check accepts `W4` as
  benign beside `W5`. · [H15]
- **NET.N235** SETTLED · `BACKLOG.md:417-422` — "NTP_Host keeps its 1024-character bound — SETTLED,
  owner, 2026-09-21: 'keep it'. Do not re-raise." — 4x over DNS's 253; sole reason the max PUT is 1,312
  B (margin 1.56x). · related: NET.S14 (plan §2.3 settled list) · [H15]
- **NET.N236** MIRROR · `BACKLOG.md:439-444` — "html/definitions/{dev,wozi}.json carry the bound as
  'maxLength': 1024 and are generated and committed" — Bound mirrored in `_VAL_NH`
  (`src/asy_ntp_client.py`), two committed definitions, `tests/test_asy_ntp_client.py:53` (verified
  verbatim) and a webserver test; a change must touch all. · related: GEN.T15 · [H15]
- **NET.N237** TODO · `BACKLOG.md:833-838` — "a rename to make network_available()'s already-held-lock
  contract visible in its own name ... was considered but not done" — Lock contract is convention-only
  (`src/asy_wifi_service.py:780` "caller must already hold wifi_mode_lock"); `buildgen/codegen.py:413`
  passes `conn.network_available`. · related: NET.T02, XCUT.T06 · [H15]

## Archive `12640c2:HEAP_FRAGMENTATION_MEASUREMENTS.md` (5,553 lines) — only items still open/undecided/deferred/next-step there, with carry status in current docs

- **NET.N238** TODO · `ARCH:3639-3643` — "R12 (per-device hostname) cannot be checked on this board as
  it stands." — Carried as queue N2 PARTIAL (REAL_HARDWARE_TEST_QUEUE.md:218). · [H15]

## Commit messages (chronological)

- **NET.N239** LIMIT · `commit 6438bdc` — "this pass's empirical claims are verified against the
  Unix-port's socket implementation only, not the real rp2 target's lwIP stack" — UDP
  truncation/POLLERR/source-filter claims were Unix-port-only at the time. · status: done (BACKLOG #5
  closed 2026-09-08 on real bench) | - · [H17]
- **NET.N240** SETTLED · `commit 639e992` — "captive_dns.py keeps its existing debug: bool + print()
  shape ... Flagged, not silently changed." — Cross-file logging divergence. · status: done
  (src/captive_dns.py:61-63 now `debug: int | None` + make_logger) | - · [H17]
- **NET.N241** LIMIT · `commit d92da47` — "a root-domain query never gets a reply (the same empty-string
  sentinel is used for both \"failed to parse\" and \"the domain actually is empty\"" — Captive DNS
  never answers a bare-root query; accepted. · tracked: src/captive_dns.py:162 | related: NET.T* · [H17]
- **NET.N242** LIMIT · `commit ce6d402` — "ntp_time_hours_counter()'s \"3x interval without success ->
  unsynced\" branch is unreachable under natural ticking ... flagged not changed" — Stale-sync distrust
  never engages (legacy parity). · covered-by: NET.S03 · [H17]
- **NET.N243** ASSUME · `commit c7b9431` — "validates against a floor-and-ceiling plausibility window
  (2025-01-01..2100-01-01)" — Hard-coded NTP plausibility window; floor predates the file, ceiling past
  era wrap; combined with rp2's ~2037 mktime OverflowError guards. · tracked:
  src/asy_ntp_client.py:49-53 | related: NET.T03 · [H17]
- **NET.N244** OPENQ · `commit 54c0d42` — "since `reconnects` is never configured anywhere ...
  wlan.status() may never actually surface STAT_WRONG_PASSWORD/STAT_NO_AP_FOUND/STAT_CONNECT_FAIL on
  stock rp2 - ... left for the project owner to decide" — Flagged owner question. · status: superseded
  by real-hardware evidence (BACKLOG #29: W4/W6 do surface) (low) | - · [H17]
- **NET.N245** SETTLED · `commit 8696c1d / dd22d43` — "the automatic path to permanent WLAN deactivation
  ... is an intentional trade-off ... STA never falling back to hotspot once connected successfully even
  once is likewise intentional" — Owner-confirmed WLAN state-machine behaviors. · tracked:
  SPECIFICATION.md:271 (permanent WiFi deactivation) | related: NET.T* · [H17]
- **NET.N246** SETTLED · `commit 5ddbcd3` — "An earlier wifi_mode_lock_timeout_ms/bounded-acquire
  mechanism added to asy_wifi_service.py during this work was reverted per direction" — Bounded
  wifi_mode_lock acquire rejected (keep timing centralized). · status: owner decision; not restated in
  docs (low) — UNTRACKED | related: NET.T* · [H17]
- **NET.N247** OPENQ · `commit 8784c66` — "a theoretical (verified unreachable in practice, matches
  legacy behavior) task-restart edge case in asy_wifi_service.py's permanent-WLAN-deactivation feature"
  — Flagged for owner input; class-naming half is done (AsyConnTime/AsyNtpClient). · status: no closure
  found by grep (low) — UNTRACKED | related: NET.T* · [H17]
- **NET.N248** LIMIT · `commit 72a241c (PR #41)` — "validates each DNS label's length (<=63 octets ...)
  but not the *total* encoded QNAME length (<=255 octets ...) ... Left as-is given the low severity" —
  DNS QNAME total-length gap. · status: src/asy_dns_client.py:42-51 comment now discusses the 255 bound
  (partially addressed?) | covered-by: NET.S14 · [H17]
- **NET.N249** RISK · `commit 40a405f` — "a device WDT-looping against a real router would hit the same
  stale-entry pattern with no bench harness able to kick_client() on its behalf" — Field risk: stale AP
  station entry after an unclean reset may push a deployed unit into hotspot fallback; bench fix is
  test-only. · tracked: tests_hardware/README.md:607-609; BACKLOG #44 (hotspot fallback after reset,
  stale-AP mechanism) | related: NET.T*, HW.T* · [H17]
- **NET.N250** SETTLED · `commit 655e4f9 / a04b483` — "the project owner judged a new reachability-probe
  mechanism's complexity not worth it" — No independent WiFi reachability probe; power-cycle is the
  recovery (asymmetry measured: 15 s outage needed hard_reset 5/5, flapping recovered 3/3). · tracked:
  CLAUDE.md hard rule, SPECIFICATION Part F.2, BACKLOG #6 stub | - · [H17]
- **NET.N251** NOTE(NEW-ITEM) · `commit b0f755c` — "New item 35: the same warning-flood class ...
  _poll_sta_connect_status() spends a slot per connect attempt ... and _read()'s 71/72/73 log on every
  degraded FRAM read forever" — Warning floods. · status: done (item 35 closed 2026-09-19, owner
  decision, per 86fb067 diff) | - · [H17]
- **NET.N252** NOTE(NOT-VALIDATABLE-IN-TWIN) · `commit 9751814 / 9c6d5c9` — "The lwIP half cannot be
  validated on the Unix port, which has no lwIP at all, and is queued for the bench"; "Run 11b ... says
  nothing about PCB or pbuf exhaustion. That stays the hardware bisection's job" — lwIP limits only
  testable on silicon. · status: bench work done later (queue at 2a88cc8 records max_connections now 6
  and W4 row); not re-verified in detail | related: NET.T*, HW.T* · [H17]
- **NET.N253** NOTE(WITHDRAWN) · `commits dbc7524, c04f106, 0754c92, 9c6d5c9` — "the cliff is withdrawn
  everywhere it was asserted, and 7 now rests on ... a margin decision under uncertainty, not a measured
  cliff"; latency gradient withdrawn; "18-connection bar and the ~12 KB of free heap per connection"
  withdrawn — Measurement claims withdrawn; max_connections choice is a judgement. · tracked:
  CONNECTION_SCALING_PLAN.md §8 (deleted; not re-verified migrated to SPEC I.6) | related: PERF.T* ·
  [H17]
- **NET.N254** NOTE(OWNER-BAR-UNMET) · `commit f92f87e -> db3bf52` — "The owner's bar of 10 is met by no
  image measured; what changes is the owner's call" -> "Owner's decision on the peak-load evidence: 6 is
  the only limit clean" — Connection limit lowered to 6. · tracked: SPEC H.7 | - · [H17]

## GitHub PRs and issues (hundertvolt/sensors)

- **NET.N255** NOTE(KNOWN-GAP) · `https://github.com/hundertvolt/sensors/pull/41` — "validates each DNS
  label's length (≤63 octets ...) but not the *total* encoded QNAME length (≤255 octets" —
  `_build_query()` builds a spec-invalid query for a >255-octet name; degrades to a timeout/`None`.
  Still true at 2a88cc8 (src/asy_dns_client.py:40-51); reachable because NTP_Host keeps its 1024 bound ·
  UNTRACKED | related: BACKLOG NTP_Host SETTLED entry (BACKLOG.md:423-440), commit-side NTP_Host items ·
  [H17]
- **NET.N256** NOTE(DEAD-CODE) · `https://github.com/hundertvolt/sensors/pull/50` —
  "`wlan_isconnected()` still has zero production callers. Whether to remove it or keep it as
  intentional public API surface is a code decision ... left as-is" — Was cited as BACKLOG ~line 379 in
  Sept 8; no BACKLOG/SPEC mention at 2a88cc8, method still at src/asy_wifi_service.py:775 — pruned
  without decision · UNTRACKED | - · [H17 (also H17)]
- **NET.N257** NOTE(DONE) · `https://github.com/hundertvolt/sensors/pull/61` — hostname follow-up —
  Hostname item closed · done-in b0f755c | - · [H17]
