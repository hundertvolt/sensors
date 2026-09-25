# Harvest — REST: Web server and HTTP surface

What the project's own comments, docs and history already record for this area (snapshot `2a88cc8`).
Recorded, not verified or triaged; `audit/HARVEST.md` explains the kinds, tags and method.

Kinds: SETTLED 20, INVAR 31, MIRROR 13, LIMIT 30, RISK 16, ASSUME 35, PLATFORM 7, WORKAROUND 5, SUPPRESS 13, TODO 2, OPENQ 4, DRIFT 4, NOTE 5 — 185 items.


## src/asy_webserver_service.py

- **REST.N001** SETTLED · `src/asy_webserver_service.py:2` — "`ext/microdot.py` is never edited; every
  behavior change wraps/calls it instead (CLAUDE.md hard rule)." — Vendoring rule; every Microdot gap
  must be covered in this file · covered-by: REST.T09 · [H02]
- **REST.N002** SUPPRESS · `src/asy_webserver_service.py:7-10` — "from microdot import Request,
  Response, abort, redirect, send_file # type: ignore[import-not-found]" — mypy suppression in shipped
  code: `ext/` is off the mypy path, so every Microdot call here is unchecked · [H02]
- **REST.N003** SUPPRESS · `src/asy_webserver_service.py:20` — "except ImportError: # typing has no
  runtime presence on MicroPython" — Swallowed ImportError for `typing` · [H02]
- **REST.N004** ASSUME · `src/asy_webserver_service.py:35-37` — "every SensorReaderConfig subclass,
  NeopixelDriver, DNSServer and ConfigManager satisfies it (SPECIFICATION.md Part C.10)" — Structural
  protocol conformance checked only statically, and only for callers mypy sees · [H02]
- **REST.N005** WORKAROUND · `src/asy_webserver_service.py:55-57` — "typings/'s CPython-derived
  StreamReader/StreamWriter split models neither half of it completely (no aclose() at all)" — Local
  `_StreamLike` Protocol works around the stub's CPython stream model; removal trigger none stated ·
  related: PLAT.T05 · [H02]
- **REST.N006** ASSUME · `src/asy_webserver_service.py:64-66` — "Microdot's own dispatch_request()
  accepts a Response, a dict, a (body, status) tuple or a bare int" — Relied-upon Microdot
  handler-return semantics · related: REST.T09 · [H02]
- **REST.N007** MIRROR · `src/asy_webserver_service.py:95-97` — "never a client-supplied duration
  (mempause's fixed 300s lives in system_cmd()'s own implementation" — `_SYSTEM_CMDS` enum must match
  the generated `system_cmd()` dispatch; 300 s lives elsewhere · related: REST.T04 · [H02]
- **REST.N008** MIRROR · `src/asy_webserver_service.py:98-101` — "matches legacy's own pauseAutoLED
  command range and asy_notification_service.py's own LockedCounter(max_val=_MAX_OVERRIDE_TIME) clamp
  ceiling, kept here as its own constant (not imported)" — Copied constant 3600 with
  `src/asy_notification_service.py:48`; also a legacy-parity claim · [H02]
- **REST.N009** SETTLED · `src/asy_webserver_service.py:123-124` — "deliberately no dedup/guard code on
  top" — Duplicate names silently shadow each other in the sensor/error-source maps · [H02]
- **REST.N010** LIMIT · `src/asy_webserver_service.py:136-148` — "Concatenates adjacent JSON text
  fragments into pieces of at most max_bytes" — `len(fragment)` counts characters, not bytes ·
  covered-by: REST.S06 · [H02]
- **REST.N011** MIRROR · `src/asy_webserver_service.py:161-162, 183-184` — "Exactly json.dumps(value)'s
  text... with json.dumps()'s own \", \"/\": \"" / "the same bytes the old per-key json.dumps()
  fragments produced" — Streaming writer must reproduce MicroPython `json.dumps()` output byte for byte
  (nested uses ", "/": ", top level ","/":") · related: REST.T05 · [H02]
- **REST.N012** DRIFT · `src/asy_webserver_service.py:208-210` — "See digital_twin/README.md for the
  real production bug this fixed." — Pointer holds (`digital_twin/README.md:226-229`); flattening also
  silently merges same-named fields across type groups (low) · [H02]
- **REST.N013** ASSUME · `src/asy_webserver_service.py:235-237` — "a plain asyncio.TimeoutError, not an
  OSError subclass - Part F.1). Microdot's read-phase catch swallows it (Part A.5), so this proxy is the
  only place a read timeout is observable." — Relied-upon Microdot read-phase exception swallowing ·
  covered-by: REST.T06 · [H02]
- **REST.N014** RISK · `src/asy_webserver_service.py:254` — "await self._pr.wrn_s(\"Connection reclaimed
  (per-call timeout):\", e, wrnno=2)" — Persisted per idle connection, no `repeat=` · covered-by:
  REST.S05 · [H02]
- **REST.N015** WORKAROUND · `src/asy_webserver_service.py:271-278` — "microdot writes the status line
  and each header apart; sent as one, a cut response never ends mid-headers" — Header coalescing assumes
  Microdot ends the header block with a separate `b"\r\n"` write; a change in Microdot's write pattern
  would buffer the whole response head indefinitely · related: REST.T09 · [H02]
- **REST.N016** ASSUME · `src/asy_webserver_service.py:311` — "max_content_length: int = 2048, # 1.56x
  the largest schema-permitted body, ~9x real traffic (I.6)" — Ratio figures depend on current schemas
  and measured traffic · related: REST.T01 · [H02]
- **REST.N017** ASSUME · `src/asy_webserver_service.py:312-314` — "Clamped to >= 1: a read of 0 would
  never end microdot's loop." — Relied-upon Microdot `send_file` read loop behaviour · related: REST.T07
  · [H02]
- **REST.N018** MIRROR · `src/asy_webserver_service.py:315-317` — "three below the firmware's own
  MEMP_NUM_TCP_PCB (toolchain/versions.toml) for connections still closing - Part H.7 holds that as a
  RELATIONSHIP" — 6 vs `MEMP_NUM_TCP_PCB = 9` (`toolchain/versions.toml:42`); buildgen passes the
  per-device value · related: REST.T06 · [H02]
- **REST.N019** MIRROR · `src/asy_webserver_service.py:318-320, 350-353` — "buildgen bounds it to [max,
  max + 1] (H.7)" / "Clamped rather than rejected... buildgen rejects the same mistake in config" —
  Backlog rule enforced in buildgen, clamped here · related: REST.T06 · [H02]
- **REST.N020** LIMIT · `src/asy_webserver_service.py:363-365` — "a Request *class* attribute, not
  per-app-instance" — `max_content_length`/`max_body_length` are process-global Microdot class
  attributes; a second instance silently overrides the first (low) · [H02]
- **REST.N021** ASSUME · `src/asy_webserver_service.py:367-370` — "Request.create() buffers the body
  before dispatch_request() answers 413" — Relied-upon Microdot order of operations (negative
  Content-Length path) · related: REST.S01 · [H02]
- **REST.N022** ASSUME · `src/asy_webserver_service.py:385-387` — "after_request alone misses every
  error-response path... dispatch_request() only runs after_request handlers on its happy path" —
  Relied-upon Microdot hook semantics · related: REST.T09 · [H02]
- **REST.N023** ASSUME · `src/asy_webserver_service.py:390-393` — "Microdot's own error_response()
  fallthrough already gives the correct reply shape via the 500 handler above regardless" — Relied-upon
  Microdot error dispatch · related: REST.T09 · [H02]
- **REST.N024** INVAR · `src/asy_webserver_service.py:396-398` — "Microdot's find_route() returns the
  first matching pattern, so every exact-match API route must already be registered or it would be
  shadowed." — Registration order invariant; relies on Microdot routing · related: REST.T02 · [H02]
- **REST.N025** LIMIT · `src/asy_webserver_service.py:406-410, 414-417` — ".update(), not result[name] =
  ... - see SPECIFICATION.md Part A.8 for the real double-wrap production bug" — Modules' top-level keys
  are merged; a key collision between modules is silently overwritten (low) · [H02]
- **REST.N026** LIMIT · `src/asy_webserver_service.py:427-430` — "silently ignored, matches
  ConfigManager.write_config()'s own per-key \"Invalid\" convention" — Comment cites a per-key Invalid
  convention but nothing is emitted · covered-by: REST.S13 · [H02]
- **REST.N027** RISK · `src/asy_webserver_service.py:431` — "results[name] = await
  module._set_dict_cfg(fields, module.get_cfg_schema())" — Bypasses `ar.handle_set_cmd` (no guard, no
  post hooks) · covered-by: REST.S03 · [H02]
- **REST.N028** SUPPRESS · `src/asy_webserver_service.py:455-457` — "group.module, # type:
  ignore[arg-type] # structurally SensorReaderConfig-shaped" — mypy suppression in shipped code · [H02]
- **REST.N029** LIMIT · `src/asy_webserver_service.py:463-469` — "Nothing the group attempted can be
  trusted as applied, so report it all \"Failed\"." — Post-hook failure marks persisted fields Failed ·
  covered-by: CORE.S06 · [H02]
- **REST.N030** SUPPRESS · `src/asy_webserver_service.py:509-516` — "try: # caller-supplied callback,
  could legitimately misbehave... except Exception as e: ... errno=2" — Broad catch → "Failed" +
  persisted errno 2 · related: REST.T04 · [H02]
- **REST.N031** SUPPRESS · `src/asy_webserver_service.py:536-542` — "except Exception as e: await
  self.pr.err_s(\"notification_led callback failed:\", e, errno=3)" — Broad catch → "Failed" + errno 3 ·
  related: REST.S09 · [H02]
- **REST.N032** SUPPRESS · `src/asy_webserver_service.py:558-564` — "except Exception as e: ... errno=5"
  — Broad catch → "Failed" + errno 5 · [H02]
- **REST.N033** SUPPRESS · `src/asy_webserver_service.py:613-619, 623-628` — "degrades this one key
  instead of letting one failing source discard every other section's already-fetched data...
  '{\"error\":\"unavailable\"}'" — Degraded-mode body per section, errno 6 persisted per failing source
  per request · related: REST.T10 · [H02]
- **REST.N034** RISK · `src/asy_webserver_service.py:635-639` — "if body.get(\"ResetErrors\") is True:
  for module in self._error_sources.values(): await module.reset_error_counter()" — Sequential unguarded
  evidence wipe; unknown keys ignored with code 0 · covered-by: REST.S04 · [H02]
- **REST.N035** ASSUME · `src/asy_webserver_service.py:650-652` — "even though freezefs's own VfsFrozen
  already refuses to escape its mount root" — Relied-upon freezefs path containment · related: REST.T07
  · [H02]
- **REST.N036** INVAR · `src/asy_webserver_service.py:653` — "assert self._static_mount is not None #
  only ever registered as a route when it isn't" — `assert` in shipped code guarding registration order
  (low) · [H02]
- **REST.N037** LIMIT · `src/asy_webserver_service.py:655-656` — "stream = open(self._static_mount +
  \"/\" + filename + \".gz\", \"rb\") / except OSError: # no such file" — Only `.gz` files are served,
  regardless of `Accept-Encoding`; any open error reads as "no such file" · covered-by: REST.T12 · [H02]
- **REST.N038** INVAR · `src/asy_webserver_service.py:662-663` — "without it this HTTP/1.0 body ends
  only at FIN, so a write that fails after the 200 would reach the client as a complete page" —
  Content-Length must be set on every static response · related: REST.T07 · [H02]
- **REST.N039** RISK · `src/asy_webserver_service.py:664-667` — "response.send_file_buffer_size =
  self._chunk_bytes # microdot's own per-response knob" — Opened stream relies on Microdot to close it;
  HEAD/abort paths don't · covered-by: REST.S07 · [H02]
- **REST.N040** SUPPRESS · `src/asy_webserver_service.py:683-686` — "except Exception as e: #
  best-effort cleanup, never load-bearing... a repeatedly-failing close() could leak TCP PCBs under this
  platform's tiny connection ceiling" — Broad catch, wrnno 4 persisted · related: REST.T06 · [H02]
- **REST.N041** WORKAROUND · `src/asy_webserver_service.py:693-695` — "asyncio.start_server() types its
  callback as Callable[[StreamReader, StreamWriter], ...] (typings/'s CPython-shaped alias)" — Stub
  mismatch worked around with `Any`; removal trigger none stated · related: PLAT.T05 · [H02]
- **REST.N042** SETTLED · `src/asy_webserver_service.py:698-699` — "Reject-when-full (decision 3):
  accepted by asyncio, then closed with no response ever written" — Deliberate silent rejection above
  `max_connections` · related: REST.T06 · [H02]
- **REST.N043** ASSUME · `src/asy_webserver_service.py:712-714` — "Structurally unreachable today -
  Microdot's blanket catch around Request.create() absorbs any EOFError" — Dead branch justified by
  Microdot internals · related: REST.T09 · [H02]
- **REST.N044** DRIFT · `src/asy_webserver_service.py:725` — "except Exception as e: # never raises out
  of this task - see module docstring" — Module docstring says nothing about it · covered-by: REST.S11 ·
  [H02]
- **REST.N045** SUPPRESS · `src/asy_webserver_service.py:725-726` — "await self.pr.err_s(\"Unexpected
  error serving connection:\", e, errno=1)" — Broad catch per connection, persisted errno 1 · [H02]
- **REST.N046** INVAR · `src/asy_webserver_service.py:728-731` — "_close_writer()'s own logging can
  raise MemoryError on an exhausted heap, and a slot skipped here would be lost until reboot" — Slot
  accounting relies on the nested `finally` · related: REST.T06 · [H02]
- **REST.N047** MIRROR · `src/asy_webserver_service.py:734-735` — "matches every other module's own
  main-loop convention (see e.g. asy_wifi_service.py's wlan_connect())" — Logger-setup-in-main-loop
  convention; cited precedent holds (`src/asy_wifi_service.py:815`, `wlan_connect()`) (low) · [H02]
- **REST.N048** LIMIT · `src/asy_webserver_service.py:755-757` — "Not consulted by the generated
  _collect_error_sources() - this service's /status entry is added directly" — Kept-for-uniformity API
  with no production consumer · related: CORE.T10 · [H02]
- **REST.N049** SUPPRESS · `src/asy_webserver_service.py:778-780` — "# noqa: B905 - MicroPython zip()
  rejects strict=, ErrEntry keeps both lists in step" — ruff suppression in shipped code; relies on
  ErrNum/ErrType lists staying equal length (mirrors `src/asy_fram_manager.py` precedent) · [H02]
- **REST.N050** SUPPRESS · `src/asy_webserver_service.py:785-791` — "None covers both a request.json
  access raising... except Exception: return None" — Any JSON parse failure (incl. MemoryError) degrades
  to code 1; duplicates `api_response.parse_cmd_request` · covered-by: CORE.S14 · [H02]
- **REST.N051** ASSUME · `src/asy_webserver_service.py:796-798` — "ext/microdot.py speaks HTTP/1.0,
  whose default is already non-persistent" — Relied-upon Microdot protocol version; `Connection: close`
  added via the supported hook · related: REST.T12 · [H02]

## ext/microdot.py

- **REST.N052** SUPPRESS · `ext/microdot.py:14, 34, 49, 1566` — "import orjson as json # type:
  ignore[import-not-found]" / "# type: ignore[misc]" / "# type: ignore[attr-defined]" / "# type:
  ignore[assignment]" — 4 mypy suppressions + ~40 `# pragma: no cover`/`no branch` markers in the
  vendored file (upstream's own per the byte-identical claim; `ext/` is off every mypy/ruff scope) ·
  [H02]
- **REST.N053** LIMIT · `ext/microdot.py:38-42` — "This method runs sync handlers in the asyncio thread,
  which can potentially cause blocking and performance issues." — MicroPython branch of
  `invoke_handler`; project's sync hooks (`_mark_connection_close`, `_shaped_error_handler`) run inline
  · related: REST.T09 · [H02]
- **REST.N054** ASSUME · `ext/microdot.py:56-61, 691-705, 1402-1406, 1415-1419` — "MUTED_SOCKET_ERRORS =
  [32, # Broken pipe / 54, ... 104, ... 128, # Operation on closed socket]" — Only these errnos (and
  "Connection lost") are muted; any other OSError re-raises into the project's `_serve()` (wrnno 3).
  Numbers are platform errno values to check on rp2/lwIP · related: REST.T06 · [H02] ⟨quote not matched
  at the anchor⟩
- **REST.N055** LIMIT · `ext/microdot.py:162-164` — "This matches the method resolution order of
  MicroPython, but not CPython." — Error-handler lookup order differs between runtimes (project
  registers only `Exception` and status codes) (low) · [H02]
- **REST.N056** ASSUME · `ext/microdot.py:290-308` — "Requests with payloads that are larger than this
  size and up to ``max_content_length`` bytes will be accepted, but the application will only be able to
  access the body... from ``stream``" — Semantics the project's `max_body_length = max_content_length`
  choice rests on (`asy_webserver_service.py:367-370`) · related: REST.S01 · [H02]
- **REST.N057** LIMIT · `ext/microdot.py:310-317, 533-537` — "Requests with longer lines will not be
  correctly interpreted." / "if len(line) > Request.max_readline: raise ValueError('line too long')" —
  Default 2 KB line cap (not set by the project) is checked only after the whole line is buffered ·
  covered-by: REST.S02 · [H02]
- **REST.N058** RISK · `ext/microdot.py:403-406, 413-421` — "method, url, http_version = line.split()" /
  "content_length = int(value)" — Unvalidated parsing: malformed request line / negative Content-Length
  · covered-by: REST.S01 · [H02]
- **REST.N059** LIMIT · `ext/microdot.py:424-430, 1443-1445` — "if content_length and content_length <=
  Request.max_body_length: body = await client_reader.readexactly(content_length)" / "if
  req.content_length > req.max_content_length:" — 413 decided only after the body was read; chunked
  bodies arrive as `b''` · covered-by: REST.T12 · [H02]
- **REST.N060** LIMIT · `ext/microdot.py:526-527` — "Note that the function is not called if the request
  handler raises an exception and an error response is returned instead." — Request-level after_request
  skipped on errors; project compensates with `after_error_request` · related: REST.T09 · [H02]
- **REST.N061** ASSUME · `ext/microdot.py:567, 575` — "send_file_buffer_size = 1024" / "A value of
  ``None`` means that no ``Cache-Control`` header is added." — Defaults the project overrides (buffer)
  or inherits (no caching) · covered-by: REST.S08 · [H02] ⟨quote not matched at the anchor⟩
- **REST.N062** ASSUME · `ext/microdot.py:656-663, 672-681` — "await stream.awrite('HTTP/1.0
  {status_code} {reason}\r\n'...)" / "await stream.awrite(b'\r\n')" — HTTP/1.0 status line, one write
  per header then a separate blank line; Content-Length auto-set only for bytes bodies — all relied on
  by the project's header coalescing and explicit Content-Length · related: REST.T05 · [H02]
- **REST.N063** LIMIT · `ext/microdot.py:684, 697-698, 1562` — "if not self.is_head:" / "res.is_head =
  (req and req.method == 'HEAD')" — HEAD skips body iteration, so the file stream is never `aclose()`d ·
  covered-by: REST.S07 · [H02]
- **REST.N064** ASSUME · `ext/microdot.py:746-751` — "buf =
  response.body.read(response.send_file_buffer_size) ... if len(buf) < response.send_file_buffer_size:
  self.i = self.ITER_NO_BODY" — Loop ends only on a short read (the project's clamp to ≥1 at
  `asy_webserver_service.py:312-314`) · related: REST.T07 · [H02]
- **REST.N065** LIMIT · `ext/microdot.py:796-798` — "Note that when using this option the file must have
  been compressed beforehand. This option only sets the header." — `compressed=True` sets
  `Content-Encoding: gzip` unconditionally; no `Accept-Encoding` negotiation · covered-by: REST.T12 ·
  [H02]
- **REST.N066** LIMIT · `ext/microdot.py:555-565, 808-816` — "types_map = { 'css': ..., 'svg':
  'image/svg+xml', }" / "content_type = 'application/octet-stream'" — Any other extension (ico, woff2,
  webmanifest, map) is served as octet-stream (low) · related: REST.T07 · [H02]
- **REST.N067** ASSUME · `ext/microdot.py:844-848, 1374-1385` — "'path': '/(.+)'" / first-match loop
  with `f = 405` — Catch-all path pattern + first-match routing: registration order matters; a
  path-matching route with the wrong method yields 405 · related: REST.T02 · [H02]
- **REST.N068** LIMIT · `ext/microdot.py:1367-1370, 1387-1395` — "if method == 'OPTIONS' and
  self.options_handler: return self.options_handler(req), '', None / if method == 'HEAD': method =
  'GET'" — OPTIONS/HEAD answered implicitly for every route · covered-by: REST.T02 · [H02]
- **REST.N069** RISK · `ext/microdot.py:1407-1408, 1515-1518, 1542-1543` — "except Exception as exc: #
  pragma: no cover / print_exception(exc)" — Client-triggerable console output per bad request/handler
  exception · covered-by: REST.T13 · [H02]
- **REST.N070** ASSUME · `ext/microdot.py:1466-1492, 1549-1561` — "an integer response is taken as a
  status code with an empty body" / "if the request could not be parsed, issue a 400 error" /
  after_error_request when `not after_request_handled` — Dispatch semantics the project's handler shapes
  and hooks rely on · related: REST.T09 · [H02]

## ext/freezefs/ffsmount.py

- **REST.N071** ASSUME · `ext/freezefs/ffsmount.py:39-49` — "# Solve \"..\" ... # Can't access /.." —
  Path containment the webserver's `..` guard cites as a second line of defence
  (`asy_webserver_service.py:650-652`) · related: REST.T07 · [H02]

## tests/_sensortask_scenarios.py

- **REST.N072** INVAR · `tests/_sensortask_scenarios.py:1124-1128` — "two loggers sharing a name would
  collapse into one row" — errcount keys must be unique by name (Part H.6), enforced here · [H03]

## tests/_webserver_concurrency_scenarios.py

- **REST.N073** OPENQ · `tests/_webserver_concurrency_scenarios.py:133-138` — "The server's connection
  accounting is evidently sensitive to a well-formed-but-unread connection landing first, in a way a
  fixed sleep never triggers." — an unexplained server behaviour (a readiness probe's connection not
  released before the next burst) was worked around, not root-caused · related: REST.T06 · [H03]
- **REST.N074** RISK · `tests/_webserver_concurrency_scenarios.py:175-177` — "a real, benign timing
  window, not a wedged server" — slots can look full right after a burst; tolerated as benign · related:
  REST.T06 · [H03]
- **REST.N075** SETTLED · `tests/_webserver_concurrency_scenarios.py:482-484` — "The project owner's own
  stated expectation: exceeding max_connections rejects only the new arrival" — owner-stated contract,
  confirmed by reading `_serve()`/`_open_conns` · related: REST.T06 · [H03]
- **REST.N076** MIRROR · `tests/_webserver_concurrency_scenarios.py:753-755` — "Settled, pinned at each
  device's own ceiling (SPECIFICATION.md H.7) ... Changes with test_asy_webserver_service.py's F1 twin
  of it, never alone." — slot-held-until-close-finishes behaviour is SETTLED and pinned in two files
  that must change together · related: REST.T06 · [H03]

## tests/test_asy_webserver_service.py

- **REST.N077** ASSUME · `tests/test_asy_webserver_service.py:905-911` — "measured false against the
  pinned interpreter, which parses depth 3,000 fine" — json.loads nesting depth up to 1,000 (the 2,048 B
  body cap) is proven only on the Unix port, not on rp2's smaller stack · related: REST.T01 · [H04]
- **REST.N078** INVAR · `tests/test_asy_webserver_service.py:921-923` — "max_content_length is a Request
  *class* attribute in ext/microdot.py ... WebserverService's constructor is expected to set it there" —
  the body cap is process-global class state mutated by the service constructor · related: TEST.T07 ·
  [H04]
- **REST.N079** SETTLED · `tests/test_asy_webserver_service.py:977-979,1013-1014` — "added directly in
  _build_status_pieces(), not via the error_sources registry" — WEBSERVER's own /status errcount entry
  bypasses the registry; the C.14 fan-in accessor is kept for shape only (generated
  _collect_error_sources() does not use it) · - (low) · [H04]
- **REST.N080** SETTLED · `tests/test_asy_webserver_service.py:1052-1054` — "decision: ResetErrors
  resets every module, not scoped per-module" — ResetErrors is global · related: REST.S04 · [H04]
- **REST.N081** SETTLED · `tests/test_asy_webserver_service.py:1234-1236` — "Settled (SPECIFICATION.md
  H.7): ... the slot counts until _close_writer() returns ... The ~70 % refusals of back-to-back clients
  follow." — connection slot held until close completes; accepted cost ~70 % refusals of back-to-back
  clients (measured figure) · related: REST.T06 · [H04]
- **REST.N082** LIMIT · `tests/test_asy_webserver_service.py:1336-1342` — "a body between
  max_body_length and max_content_length is allocated in full and then thrown away - the band
  WebserverService closes by binding the two" — body-cap tests pin the read-size request, not memory;
  negative/huge Content-Length is not among the shapes tested · related: REST.S01 · [H04]
- **REST.N083** INVAR · `tests/test_asy_webserver_service.py:1433-1435` — "A future change that sets
  only one of them would silently reopen it" — max_body_length and max_content_length must stay equal;
  enforced by a structural test · related: REST.T01 · [H04]
- **REST.N084** RISK · `tests/test_asy_webserver_service.py:1615-1616,1627` — "escaping is acceptable
  here; keeping the slot is not" — a MemoryError raised by the close-failure warning may escape
  `_serve()`; only slot release is guaranteed · related: MEM.T03 (low) · [H04]
- **REST.N085** LIMIT · `tests/test_asy_webserver_service.py:1681-1683,1695-1696` — "Structurally
  unreachable through the real Microdot integration today" / "a genuine real-hardware socket failure is
  the only real trigger" — `_serve()`'s EOFError and OSError branches are defence in depth, exercised
  only via monkeypatch · - (low) · [H04]
- **REST.N086** INVAR · `tests/test_asy_webserver_service.py:1925-1927` — "the static wildcard must be
  registered after every real API route" — route registration order is load-bearing (Microdot
  first-match) · related: REST.T07 · [H04]
- **REST.N087** LIMIT · `tests/test_asy_webserver_service.py:2061-2063` — "_PieceWriter never splits a
  fragment, so this is the documented limit, not a bound" — a single scalar (up to NTP_Host's 1,024
  chars + quotes) exceeds the 256 B write chunk; I.3's need table was measured at default values only ·
  related: REST.T05 · [H04]
- **REST.N088** SETTLED · `tests/test_asy_webserver_service.py:2085-2086,2106-2107` — "its default
  (None) must reproduce today's plain-404 behavior, since no existing call site passes it" —
  `is_hotspot_active` is opt-in; captive redirect only on static-route OSError, never for `..` or
  non-GET · related: NET.T09 · [H04]
- **REST.N089** SETTLED · `tests/test_asy_webserver_service.py:2143-2144` — "Proves the \"no bespoke
  try/except needed\" decision directly" — the hotspot callback relies on the blanket
  `errorhandler(Exception)` · - (low) · [H04]
- **REST.N090** PLATFORM · `tests/test_asy_webserver_service.py:2295-2297,2332-2334` —
  "Response.__init__'s automatic Content-Type only fires for isinstance(body, (dict, list))" /
  "Response.complete() only auto-sets Content-Length for a bytes body" — relied-upon Microdot v2.6.2
  behaviour; streamed bodies set both headers explicitly · related: REST.T09 · [H04]
- **REST.N091** MIRROR · `tests/test_asy_webserver_service.py:2510-2511` — "The whole fix rests on this:
  MicroPython's OWN json.dumps() text - key order, \", \"/\": \" separators, escaping, float repr -
  reproduced by walking the value" — the streaming writer re-implements MicroPython json.dumps output
  byte for byte; must be re-checked when the pinned MicroPython version moves · related: PLAT.T11 ·
  [H04]
- **REST.N092** SETTLED · `tests/test_asy_webserver_service.py:2977-2978,2990-2991` — "start_server()'s
  own default of 5 silently capped the accept queue" / "Clamped rather than raised, matching
  LockedCounter's own out-of-range convention" — backlog derived from max_connections and clamped at
  runtime; buildgen rejects bad config · related: REST.T06 · [H04]
- **REST.N093** LIMIT · `tests/test_asy_webserver_service.py:3043-3044` — "with any non-ASCII character
  in it, a character count declares a short body" — test checks byte-accurate Content-Length only;
  per-piece size with non-ASCII (character-counted pieces) is not asserted · related: REST.S06 · [H04]
- **REST.N094** SETTLED · `tests/test_asy_webserver_service.py:3079-3080` — "microdot swallows a timeout
  there as it does for the headers, so the proxy's own log is the only trace this connection ever
  leaves" — body-read timeouts are visible only via the proxy's warning · related: REST.T08 · [H04]

## tests/test_setter_microdot_integration.py

- **REST.N095** MIRROR · `tests/test_setter_microdot_integration.py:8-10` — "any of its wiring that must
  be exercised is reimplemented locally, never imported" — Route wiring from
  src/asy_webserver_service.py and the generated device module is re-implemented in the test; drift from
  production is not detected · [H05]
- **REST.N096** MIRROR · `tests/test_setter_microdot_integration.py:99-105` — "_wifi_field_schema()
  below mirrors that scoping locally, this file never importing the generated device module" —
  setNetwork/setWiFiLED SettingsGroup scoping (post_fct only on the four network fields) is copied from
  buildgen output · [H05]
- **REST.N097** SETTLED · `tests/test_setter_microdot_integration.py:193-194` — "Final project decision:
  an unrecognized field key ... is just another per-field "Invalid" outcome" — Same decision as
  test_base_classes.py:1664 · [H05]
- **REST.N098** RISK · `tests/test_setter_microdot_integration.py:660-669` — "A broken persistence layer
  is therefore invisible to base_classes.py's "persisted" check: the response reports the ordinary Valid
  outcome" — Since WP5's deferred flush, a PUT whose flash write will fail still returns 200/"Valid";
  the failure surfaces only later as a logged errno · related: CORE.T12 · [H05]

## tests/test_strict_json.py

- **REST.N099** RISK · `tests/test_strict_json.py:86-88` — "json.dumps() never raises here, where
  CPython would ... A route that lets a non-finite value through therefore ships a body the browser
  rejects, silently" — inf/NaN in a REST response dict produces a body no browser parser accepts; pinned
  so a version bump surfaces a change · [H05]

## digital_twin/README.md

- **REST.N100** PLATFORM · `digital_twin/README.md:726-730` — "`ext/microdot.py`'s `send_file()` hands
  the response a raw file stream, so `Response.complete()`'s automatic `Content-Length` never applies" —
  `GET /` has no Content-Length on Microdot v2.6.2 · [H06]

## tests_hardware/bench/test_network_resilience.py

- **REST.N101** RISK · `tests_hardware/bench/test_network_resilience.py:646-648` — "under load that lag
  can admit connection _MAX_CONNECTIONS + 1 into the app layer. A real race" — Known transient
  over-admission by one above the ceiling; test retries up to 3×. · related: REST.T06 · [H07]
- **REST.N102** LIMIT · `tests_hardware/bench/test_network_resilience.py:690-693` — "no
  pr.err_s()/wrn_s() call anywhere on that path, so a real rejection at the connection ceiling is
  expected to leave WEBSERVER's own error/warning log untouched" — Pins that ceiling rejections are
  unlogged (invisible in errcount). · related: REST.T08 · [H07]
- **REST.N103** SETTLED · `tests_hardware/bench/test_network_resilience.py:735-738` — "Malformed JSON is
  an application-level error ... so the HTTP status is still 200 rather than a transport-level 4xx" —
  Pinned REST contract; relies on vendored microdot's literal "HTTP/1.0" status line. · [H07]
- **REST.N104** LIMIT · `tests_hardware/bench/test_network_resilience.py:969-970` — "_serve()'s outer
  wait_for(outer_cap_s) timeout logs wrnno=2 - ... the (also wrnno=2) per-call timeout path" — Two
  distinct timeouts share one warning number. · related: XCUT.T07 · [H07]

## REAL_HARDWARE_TEST_QUEUE.md (snapshot only; being updated by another session)

- **REST.N105** RISK · `REAL_HARDWARE_TEST_QUEUE.md:297` — "this fits by argument, never by measurement,
  and would not fit the 528 B measured at 7" — W5 OPEN: a ~1,026 B over-cap piece from `NTP_Host`'s
  1,024-char bound; needs one flash write. · related: REST.T05 · [H08]

## HARDWARE_TEST_HANDOVER.md (snapshot only; sitting IN PROGRESS in another session)

- **REST.N106** RISK · `HARDWARE_TEST_HANDOVER.md:159-162` — "the admission policy needs fairness (a
  writer can be starved indefinitely today)" — F18 finding and suggested direction; owner decision. ·
  related: PERF.T03 · [H08]

## scripts/_digital_twin_ci_suite.py

- **REST.N107** ASSUME · `scripts/_digital_twin_ci_suite.py:1076-1078` — "the readiness probe's own
  connection is still counted right after _wait_until_serving(), refusing one of a full burst" — Ceiling
  test depends on slot-release timing (Part H.7.1). · related: REST.T06 · [H09]

## buildgen/validate.py

- **REST.N108** ASSUME · `buildgen/validate.py:222-227` — "past it lwIP resets them, where nothing in
  src/ sees it" — backlog-vs-ceiling rationale; lwIP behaviour claim. · related: REST.T06 · [H09]

## pyproject.toml

- **REST.N109** SUPPRESS · `pyproject.toml:306-310` — "asserts its static mount is non-None purely to
  narrow the type for mypy" — src/asy_webserver_service.py: SLF001, S101, ANN401 (an `assert` in shipped
  code); digital_twin/_http_client.py: ANN401. · [H09]

## tests_scripts/test_buildgen_validate.py

- **REST.N110** ASSUME · `tests_scripts/test_buildgen_validate.py:1515-1516,1532-1533` — "a queue
  shallower than the ceiling lets lwIP reset part of a burst" / "a deeper queue buys nothing but pcbs
  held" — backlog must be in [max_connections, max_connections+1]; rationale is lwIP/_serve behaviour
  not proven here · related: REST.T06 · [H10]

## tests_scripts/test_ceiling_probe.py

- **REST.N111** MIRROR · `tests_scripts/test_ceiling_probe.py:22-24,66` — "EOF ends microdot's headers:
  it serves, slot held" — Fake encodes Microdot/_serve slot-release semantics (slot held while serving
  an EOF-ended request); must track asy_webserver_service.py's real behaviour (H.7.1) · related:
  REST.T06 · [H10]

## tests_scripts/test_digital_twin_ci_suite_errcount.py

- **REST.N112** ASSUME · `tests_scripts/test_digital_twin_ci_suite_errcount.py:180-181` — "Every
  registered error source appears in errcount whether or not it ever logged" — /status contract the
  strict helper relies on · [H10]

## tests_scripts/test_persistence_write_marker_completeness.py

- **REST.N113** MIRROR · `tests_scripts/test_persistence_write_marker_completeness.py:19-22,56-62` —
  "_ROUTE_DISPATCH_FIELDS = frozenset({\"SystemCmd\", \"PauseTime\", \"lightCmdLED\", \"ResetErrors\"})"
  — Four route-level dispatch-only fields hand-listed vs asy_webserver_service.py; the rest derived from
  `# @web ... dispatch=true` tags by regex (a field wrongly counted dispatch-only fails SILENTLY —
  :336-338) · [H10]
- **REST.N114** ASSUME · `tests_scripts/test_persistence_write_marker_completeness.py:186-190` —
  "vendored ext/microdot.py rejects it with 413 before this project's route handler" / "it pads an
  UNKNOWN sensor key, which PUT /sensors ignores silently" — Exemptions rest on Microdot's body cap and
  `_put_sensors` silently dropping unknown sensor keys (itself a seed) · related: REST.S13 · [H10]

## tests_scripts/test_request_body_cap_headroom.py

- **REST.N115** INVAR · `tests_scripts/test_request_body_cap_headroom.py:1-3,111-120` — "the largest
  body any device's own schema can legitimately produce must still fit under `max_content_length`.
  Nothing else checks this" — Enforced per device and per PUT route, cap read from src/ via ast (SPEC
  I.6); the hardware tier's "W3" checks it on silicon but not in CI · related: REST.T01 · [H10]
- **REST.N116** LIMIT · `tests_scripts/test_request_body_cap_headroom.py:79-107` — "_put_sections ...
  generate_definitions(model, ...)" — Bound is computed from the website definitions (only `@web`-tagged
  writable fields), compact JSON (no whitespace), and string `maxLength` as characters; a PUT-able field
  without an `@web` tag, pretty-printed bodies and multi-byte UTF-8 are not counted · related: WEB.T02 ·
  [H10]
- **REST.N117** ASSUME · `tests_scripts/test_request_body_cap_headroom.py:23-26` — "_MAX_JSON_NUMBER =
  len(\"-1.2345678901234567e+308\")" — "Legitimate" numbers are assumed to be at most 24 characters; a
  client may send longer numeric literals (trailing zeros) that the cap then refuses · [H10]
- **REST.N118** ASSUME · `tests_scripts/test_request_body_cap_headroom.py:28-29` — "Only /sensors nests
  its body per group ({\"SCD30\": {...}}); asy_webserver_service.py's own comment calls the rest \"flat
  settings endpoints\"" — Route-shape knowledge copied from a src comment · [H10]
- **REST.N119** INVAR · `tests_scripts/test_request_body_cap_headroom.py:32-41` — "_EXPECTED_LARGEST =
  {\"arzi\": 1312, \"dev\": 1312, ..." — Pinned per-device largest legitimate body (all 1312 B); growth
  must be deliberate and SPEC I.6's quoted figure updated with it · [H10]

## tests_scripts/test_request_timeout_ceiling.py

- **REST.N120** MIRROR · `tests_scripts/test_request_timeout_ceiling.py:296-297` — "A held socket silent
  past per_call_timeout_s is answered and logs wrnno=2" — Host test relies on the webserver's wrnno=2
  meaning; structural check keyed to local names (`extra`, `_pad`, `HELD_REQUEST_LINE`) in one bench
  test · related: XCUT.T07 · [H10]

## tests_js/live-backend-put-matrix.test.js

- **REST.N121** LIMIT · `tests_js/live-backend-put-matrix.test.js:80-83` — "the real backend's
  \"Unchanged\" detection doesn't reliably fire (SPECIFICATION.md Part H.7)" — a stated real-backend
  unreliability tolerated by the test; the cited H.7 contains no such statement · related: WEB.T01 ·
  [H11]

## tests_js/mock-server.test.js

- **REST.N122** DRIFT · `tests_js/mock-server.test.js:273-275 vs tests_js/render.test.js:702-704, 725-727`
  — "reports \"Failed\" through coerce_numeric()" vs "fails inside the callback's own cast" / "a missing
  one raises KeyError there" — two different stated server mechanisms for lightCmdLED's "Failed"; one
  relies on a KeyError from the callback (low) · related: REST.S10 · [H11] ⟨quote not matched at the
  anchor⟩

## SPECIFICATION.md Part A.5 (Microdot / REST layer, 287-335)

- **REST.N123** ASSUME · `SPECIFICATION.md:291-293` — "Upstream v2.7.0 (checked 2026-09-23) changes only
  f-strings, a `QUERY` decorator and `Vary` merging ... a bump would move none of Part H.7's serving
  walls" — Dated upstream-diff claim. · covered-by: REST.T09 · [H12]
- **REST.N124** PLATFORM · `SPECIFICATION.md:295-303` — "Every exception raised by our own code inside a
  route handler — including ... `MemoryError` — is already caught by Microdot itself" — Relies on v2.6.2
  `dispatch_request()` shape; changes with a Microdot bump. · related: REST.T09 · [H12]
- **REST.N125** LIMIT · `SPECIFICATION.md:304-307` — "The one gap: exceptions raised while writing the
  response itself ... the client hits a timeout, as expected." — Known uncaught path in vendored code;
  per-connection only. · related: REST.T09 · [H12]
- **REST.N126** INVAR · `SPECIFICATION.md:308-310` — "Microdot's own exception logging
  (`print_exception`) is not wired into this project's `PrintLog`/FRAM logging — anything caught by the
  blanket catch needs an `@app.errorhandler`" — Evidence visibility depends on registered handlers. ·
  related: REST.T13 · [H12]
- **REST.N127** LIMIT · `SPECIFICATION.md:311-313` — "`Request.json` has no internal guarding (raises
  straight out on malformed body)" — Contained by the blanket catch only. · related: REST.T02 · [H12]
- **REST.N128** PLATFORM · `SPECIFICATION.md:314-317` — "`max_content_length` (16KB default, 413 if
  exceeded) → tightened to 2048 bytes ... `max_readline` (2KB default)" — Request bounds depend on
  Microdot internals (see REST.S01 negative Content-Length). · related: REST.S01 · [H12]
- **REST.N129** PLATFORM · `SPECIFICATION.md:323-325` — "Registering `@app.errorhandler(HTTPException)`
  never fires for `abort()`." — Microdot lookup-key fact. · [H12]

## SPECIFICATION.md Part A.7 (wozi's construction order and dependency graph, 358-569)

- **REST.N130** INVAR · `SPECIFICATION.md:459-460` — "`static_mount=\"/html\"` registers the static
  route pair last, so an exact-match API route always wins" — Registration-order dependency. · related:
  REST.T07 · [H12]

## SPECIFICATION.md Part A.8 (REST API endpoint reference, 571-625)

- **REST.N131** ASSUME · `SPECIFICATION.md:578-579` — "Six endpoints: `/measurements`, `/sensors`,
  `/networking`, `/system`, `/status`, `/notification`." — Count-based route claim (static `/html`
  routes excluded). · related: REST.T02 · [H12]
- **REST.N132** INVAR · `SPECIFICATION.md:595-597` — "must build results with `.update()`, never
  `result[name] = await module.get_dict_data()`" — Past production bug; convention for GET aggregation.
  · [H12]
- **REST.N133** INVAR · `SPECIFICATION.md:604-606` — "`PauseTime` (range-checked 0-3600, rejected not
  clamped, before reaching `NotificationCoordinator.set_override_led()`)" — Validation convention
  (Invalid vs Failed semantics disputed). · related: REST.S10 · [H12]
- **REST.N134** LIMIT · `SPECIFICATION.md:617-621` — "One open exception: `SCD30_Reader.get_dict_cfg()`
  and three of `BMP3xx_Reader.get_dict_cfg()`'s fields ... can mix pre/post-write values across fields
  (BACKLOG.md)" — Non-atomic GET snapshot; open in BACKLOG. · related: SENS.T16 · [H12]

## SPECIFICATION.md Part A.9 (The frozen-HTML pipeline, 627-653)

- **REST.N135** DRIFT · `SPECIFICATION.md:633` — "over a stream `_serve_static()` opens itself, in 256 B
  reads" — A.5:292 speaks of Microdot's "1,024 B `send_file` reads" as a serving wall; code has
  `_DEFAULT_CHUNK_BYTES = const(256)` (`src/asy_webserver_service.py:108`). Which bound governs is
  stated two ways. (low) · related: REST.T07 · [H12]

## SPECIFICATION.md Part C.5 / C.5.1-C.5.3 (Config schema system, 1699-1797)

- **REST.N136** SETTLED · `SPECIFICATION.md:1787-1788` — "A per-field failure never demotes the overall
  response below `\"OK\"`/`0` — detail lives in `\"result\"`." — Envelope convention. · related:
  CORE.S06 · [H12]

## SPECIFICATION.md Part F.1 — Core platform facts

- **REST.N137** INVAR · `SPECIFICATION.md:3538-3539` — "keep piece count bounded to a small, fixed
  number of sections" — Convention for streamed responses, no mechanical cap named. · [H13]
- **REST.N138** INVAR · `SPECIFICATION.md:3568-3570` — "a value's shape is the caller's obligation,
  which is why `_write_guarded()` needing `json.dumps()` inside its own `try` is moot (I.3)" —
  Serialization safety rests on every caller, not the response layer. · related: REST.T11 · [H13]

## SPECIFICATION.md Part G.2 — Known reusable primitives

- **REST.N139** INVAR · `SPECIFICATION.md:4165-4166` — "`api_response.py`'s `make_response()` only,
  never a hand-built `{\"res\", \"code\", \"descr\", \"result\"}` dict" — Envelope rule; generated code
  and `js/` included? not stated. · related: XCUT.T15 · [H13]
- **REST.N140** INVAR · `SPECIFICATION.md:4210-4214` — "Any route whose response scales with device
  configuration returns `await _stream_dict_response(result, self._chunk_bytes)` instead of `return result`"
  — Streaming rule (dup of CLAUDE.md); no test named that every scaling route complies. · related:
  MEM.T03 · [H13]

## SPECIFICATION.md Part H.6 — Errcount and dispatch-only conventions

- **REST.N141** INVAR · `SPECIFICATION.md:4508-4512` — "`lightCmdLED` (r/g/b/t, bounds matching legacy
  exactly, rejecting not clamping) ... a well-formed submission always reports `\"Valid\"`, including on
  an identical repeat (never `\"Unchanged\"`)" — Dispatch-only semantics; plan notes `lightCmdLED`
  yields "Failed" not "Invalid" for bad keys. · related: REST.S10 · [H13]
- **REST.N142** RISK · `SPECIFICATION.md:4513-4515` — "if a `SettingsGroup`'s post-write hook raises,
  every field that group attempted is reported `\"Failed\"` ... while the overall envelope still reports
  success" — Deliberate envelope-success-with-field-failure contract. · related: XCUT.T11 · [H13]

## SPECIFICATION.md Part H.7 — Digital twin integration / connection ceiling

- **REST.N143** SETTLED · `SPECIFICATION.md:4540-4544` — "**`max_connections` is `6`** (owner decision
  ...) ... `MEMP_NUM_TCP_PCB` is at least `max_connections + 3` ... anything less is a build error" —
  Owner decision; relation enforced by `check_lwip_ensemble()`'s `SPARE_TCP_PCBS`. · related: REST.T06,
  PERF.T02 · [H13]
- **REST.N144** ASSUME · `SPECIFICATION.md:4550-4551` — "Every limit measured on silicon ran with these
  three spares; nothing leaner has been measured." — Spare count is empirical, not derived. · related:
  HW.T16 · [H13]
- **REST.N145** INVAR · `SPECIFICATION.md:4563-4568` — "`backlog` derives `max_connections + 1` ...
  buildgen refuses a `[device].backlog` below `max_connections` or above `max_connections + 1` ...
  `WebserverService` itself only clamps a lower value up" — Build-time enforced; runtime only clamps up.
  · related: REST.T06 · [H13]
- **REST.N146** SETTLED · `SPECIFICATION.md:4591-4596` — "back-to-back clients see ~70 % refused ...
  **It stays that way** (settled 2026-09-24)" — Slot held until close completes; do-not-release-earlier
  marker; pinned by unit and twin tests. · related: REST.T06 · [H13]
- **REST.N147** SETTLED · `SPECIFICATION.md:4625-4627` — "HTTP keep-alive is deliberately not
  implemented ... persistent connections proved fragile when tried in application code" — Do-not-add
  keep-alive. · related: REST.T12 · [H13]
- **REST.N148** LIMIT · `SPECIFICATION.md:4628-4629` — "`max_connections` only ever rejects a *new*
  arrival — never touches an already-open connection, reclaimed only by its own timeout" — No eviction
  of open connections. · related: REST.T06 · [H13]

## SPECIFICATION.md Part H.7.1 — Connection lifetime and instruments

- **REST.N149** ASSUME · `SPECIFICATION.md:4633-4645` — "Measured on the dev bench, 2026-09-23 ...
  **5.12 / 5.14 / 5.16 s** ... **15.08 / 15.13 s** ... drain ... **0.71–0.84 s**" — Dated bench figures;
  "No connection can be held longer than ~15 s on this firmware". · related: HW.T16, REST.T06 · [H13]
- **REST.N150** INVAR · `SPECIFICATION.md:4642-4644` — "released even when that close's own warning
  raises `MemoryError` on an exhausted heap, since a skipped release would refuse everyone until reboot"
  — Slot-release must survive MemoryError in `_serve()`'s `finally`. · related: REST.T06 · [H13]
- **REST.N151** WORKAROUND · `SPECIFICATION.md:4646-4649` — "`extmod/modlwip.c` has freed the pcb but
  its state (6) still passes the write path's error check, so microdot's 400 would reach
  `tcp_write(NULL)` ... `_TimeoutStreamProxy` drops every write once a read of the pair raised
  `OSError`" — Workaround for an upstream modlwip defect; removal trigger none stated. · related:
  REST.T06, PLAT.T04 · [H13]

## SPECIFICATION.md Part I.3 — Bounded response assembly

- **REST.N152** INVAR · `SPECIFICATION.md:4890-4895` — "Every GET route whose response grows with device
  configuration ... writes its JSON through one `_PieceWriter` ... `chunk_bytes` ... default **256**,
  that also sets the static-file read size below, so the two bounds cannot drift apart" — One parameter
  bounds both paths; piece bound is in characters per plan REST.S06. · covered-by: REST.T05 · [H13]
- **REST.N153** INVAR · `SPECIFICATION.md:4901-4903` — "The bytes are **identical** to what the routes
  emitted before ... pinned against MicroPython's own `json.dumps()` by
  `tests/test_asy_webserver_service.py`" — Byte-parity mirror `_PieceWriter.add_value()` ↔
  `json.dumps()` (separators, non-string keys), test-enforced. · related: REST.T05 · [H13]
- **REST.N154** ASSUME · `SPECIFICATION.md:4904-4909` — "that scales with module count (17 on real
  hardware, ~4.9 KB for one section ...). At 256 B `dev`'s `/status` is 29 pieces (11 at the old 1024
  B); its wall-clock on silicon is `REAL_HARDWARE_TEST_QUEUE.md` row W3" — Dated counts; permanent doc
  cites a temporary queue row ID. · related: DOC.T03, DOC.T08 · [H13]
- **REST.N155** ASSUME · `SPECIFICATION.md:4925-4926` — "Only a string config value can be that scalar —
  `errcount` holds ints alone (`_shape_errcount_entry()`), and `history_length` bounds its list" —
  Premise of the over-cap analysis; non-ASCII SSID/hostname bytes not considered (REST.S06). · related:
  REST.S06 · [H13]
- **REST.N156** WORKAROUND · `SPECIFICATION.md:4935-4944` — "`_serve_static()` now opens the file
  itself, passes it to `send_file(stream=...)`, sets that attribute on the one response to the same
  `chunk_bytes` (**256**) and adds `Content-Length`" — Wraps vendored microdot's 1,024 B
  `send_file_buffer_size` default without editing `ext/`; removal trigger none stated. · related:
  REST.T07 · [H13]
- **REST.N157** INVAR · `SPECIFICATION.md:4944-4951` — "**A write-phase failure is never a success**: a
  response whose body can still fail after its status line goes out must carry its length ...
  `_TimeoutStreamProxy.awrite()` holds the block until its blank line and sends it as one write" —
  Framing invariant plus a workaround for microdot writing headers piecewise. · related: REST.T06,
  REST.T12 · [H13]
- **REST.N158** INVAR · `SPECIFICATION.md:4971-4973` — "a `chunk_bytes` of 0 is clamped: microdot's body
  loop ends only on a short read, and `read(0)` never is one" — Guard against a microdot behaviour. ·
  related: REST.T05 · [H13]

## SPECIFICATION.md Part I.6 — Request-body cap (sits inside Part J)

- **REST.N159** PLATFORM · `SPECIFICATION.md:5176-5182` — "`handle_request()` calls `Request.create()`
  (`:1400`), which reads the body at `:426`, and only then `dispatch_request()` (`:1410`), whose 413
  check is at `:1443` ... not fixed by a version bump" — Vendored microdot ordering (v2.6.2 and upstream
  `main`), cited by line. · related: REST.T09 · [H13]
- **REST.N160** ASSUME · `SPECIFICATION.md:5190-5195` — "the largest legitimate body is **1,312 B** on
  `PUT /networking` ... real traffic measures 232 B. So 2048 clears the schema maximum with **1.56x**
  margin" — Dated per-route measurements; pinned per device by
  `tests_scripts/test_request_body_cap_headroom.py`. · related: REST.T01 · [H13]
- **REST.N161** INVAR · `SPECIFICATION.md:5197-5204` — "a cap must serve what the API accepts, not what
  one client happens to send" — Cap sized per route; `/sensors` grows per driver. · related: REST.T01 ·
  [H13]
- **REST.N162** INVAR · `SPECIFICATION.md:5206-5212` —
  "`tests_scripts/test_request_body_cap_headroom.py` computes both sides ... asserts no route can be
  sent a legitimate body the cap would reject" — Enforced guard. · related: REST.T01 · [H13]
- **REST.N163** INVAR · `SPECIFICATION.md:5214-5218` — "**Both are set from the one constructor
  parameter**, so they cannot drift apart again ... `tests/test_asy_webserver_service.py`'s F.2b section
  pins this" — Enforced; test section label "F.2b" collides visually with Part F numbering. · related:
  DOC.T03, REST.S01 · [H13]
- **REST.N164** RISK · `SPECIFICATION.md:5248-5255, 5275-5281` — "A slot is released in `_serve()`'s
  `finally`, *after* `_close_writer(writer)` has awaited the close — so it outlives the response the
  client already holds" — Slot-release lag makes an immediate follow-up request refusable; tests
  compensate with `wait_until()`/`time.sleep(1.0)`. · covered-by: PERF.T02 · [H13]

## SPECIFICATION.md Part L.7 — Product versioning

- **REST.N165** INVAR · `SPECIFICATION.md:6550-6558` — "`GET /system` gains one nested, never-flattened
  `\"build\"` sub-entry ... never through `SettingsGroup` ... Never conflate the two" — Build-info shape
  contract. · related: GEN.T14 · [H13]

## CLAUDE.md

- **REST.N166** INVAR · `CLAUDE.md:111-116` — "pinned to tag `v2.6.2` and verified byte-identical to it
  on 2026-09-10 ... No edits, no restyling, ever" — Rests on one dated check plus convention. No test,
  script or CI step re-verifies `ext/microdot.py` against upstream (no hash check in
  tests_scripts/scripts/toolchain). · related: REST.T09, LIC.T02 · [H14]
- **REST.N167** INVAR · `CLAUDE.md:360-364` — "A REST GET route whose response dict can grow ... streams
  it via `asy_webserver_service.py`'s `_stream_dict_response()`" — Convention only; used at
  src/asy_webserver_service.py:411, 418. · related: REST.T05 · [H14]
- **REST.N168** LIMIT · `CLAUDE.md:1062-1066` — "its one real gap (exceptions during response writing)
  ... what this project's own REST layer still has to add" — Vendored Microdot gap that our wrappers
  must cover (SPEC A.5). · covered-by: REST.T09 · [H14]

## BACKLOG.md

- **REST.N169** OPENQ · `BACKLOG.md:250-309` — "What is still open — and it is the load case, not the
  idle one." — #24 `ResetErrors` sweep: 3 readers reach 88-98 % of the 15 s cap, 4 exceed it (F18); fix
  = explicit elapsed-time budget sized for load and/or batched/concurrent reset near ~27 chunks —
  owner's decision. · covered-by: PERF.T03 · [H15]
- **REST.N170** SETTLED · `BACKLOG.md:306-309` — "a design-level fix at the source ... rather than a
  larger client timeout" — Raising client timeouts is ruled out as the fix. · related: PERF.T03 · [H15]
- **REST.N171** OPENQ · `BACKLOG.md:325-362` — "ISL29125 HTTP connection reset under concurrent API load
  — root-cause not yet established." — #30: PUT + 2 readers 6/18; flash-write IRQ window "suspected, not
  proven"; second candidate is the connection ceiling; next gated run reads `CEILING_RETRIES`, then
  `RangeAuto=false` bisection (queue R1). · related: REST.T06 · [H15]
- **REST.N172** LIMIT · `BACKLOG.md:332` — "The DUT logs nothing: WEBSERVER's counter stays 0, so this
  is invisible to FRAM forensics." — A real failure class leaves no persisted evidence. · related:
  XCUT.T24 · [H15]
- **REST.N173** ASSUME · `BACKLOG.md:433-437` — "Real traffic measures 232 B." — Dated body-size
  figures; derived by `tests_scripts/test_request_body_cap_headroom.py`. · [H15]

## Archive `12640c2:HEAP_FRAGMENTATION_MEASUREMENTS.md` (5,553 lines) — only items still open/undecided/deferred/next-step there, with carry status in current docs

- **REST.N174** OPENQ · `ARCH:5098-5099` — "One hypothesis still untested on top of that: refused
  clients retry at once and every refused accept still costs its stream objects and a task." — Not
  carried in SPEC H.7 or elsewhere. · related: REST.T06 · [H15]

## Commit messages (chronological)

- **REST.N175** TODO · `commit 4f75da6` — "records the still-open questions (uasyncio per-connection
  task isolation, pyproject.toml's dangling exclude entries)" — Microdot follow-ups. · status:
  per-connection isolation documented in SPECIFICATION A.5 (per CLAUDE.md); dangling-exclude question
  not re-checked (low) | related: REST.T* · [H17]
- **REST.N176** RISK · `commit e72936e (PR #27)` — "Root-caused today's arzi/neu
  permanent-unreachability incident to vendored Microdot's zero-timeout stream I/O ... a standing
  upstream gap" — Field incident on deployed units; owner-decided layered hardening design. · status:
  done in refactor (SPECIFICATION.md:623 "Connection hardening (per-call/outer-cap timeouts ...)"); the
  deployed legacy units keep the gap by rule (legacy never gets work) | related: REST.T*, PAR.T* · [H17]
- **REST.N177** PLATFORM · `commit a035736` — "asyncio.TimeoutError is an OSError subclass was wrong ...
  it's a plain Exception ... a per-call read-phase timeout is silently absorbed by Microdot's own
  blanket except-Exception" — Webserver timeout telemetry depends on a 1.28 asyncio class-hierarchy fact
  and Microdot's catch shape. · tracked: SPECIFICATION Part A.5 (per commit) | related: REST.T*, PLAT.T*
  · [H17 (also H17)]
- **REST.N178** TODO · `commit ee5310c` — "Timeout values become init-time constants ... one global
  value, defaults to be reality-checked later" — Webserver timeout defaults were provisional. · status:
  bench-measured later (BACKLOG #24 outer_cap_s 15.0 load curve) — partially done; no explicit
  "reality-checked" closure found (low) | related: PERF.T*, REST.T* · [H17]
- **REST.N179** SETTLED · `commit d49a0f7` — "deliberately keep its logger RAM-only (no fram=) to
  preserve WIRING_CONTRACT.md's five-chunk FRAM invariant" — Webserver log RAM-only at the time. ·
  status: superseded by WP1 (WEBSERVER now FRAM-backed per CLAUDE.md) | - · [H17]
- **REST.N180** SETTLED · `commit 8328943 (reverts 5d47a8b) → 029f02d` — "Real HTTP keep-alive ...
  turned out to require building persistent-connection support entirely in application code around
  vendored Microdot ... Too fragile to keep." — Keep-alive rejected; page load reduced by
  bundling/inlining instead. · tracked: SPECIFICATION Part H (per 15ed282/bc8391c) | related: REST.T*,
  WEB.T* · [H17]
- **REST.N181** NOTE(CLOSED) · `commit c304b70` — "Microdot exposes two independent limits and we set
  only one ... anything between max_body_length ... and max_content_length was read into one contiguous
  buffer and immediately thrown away"; upstream defect "filed against microdot itself (#26)" —
  Attacker-reachable 16 KB buffers. · status: done-in c304b70 (both caps 2048;
  src/asy_webserver_service.py:363-370) | related: SEC.T*, REST.T* · [H17 (also H17)]
- **REST.N182** NOTE(BUG-FOUND) · `commit 642d163 -> db1866e` — "the client gets a silently truncated
  gzip page" (HTTP/1.0, no Content-Length, 1,025 B send_file chunk MemoryError) — Silent 200 truncation.
  · status: done-in db1866e | related: REST.T* · [H17]
- **REST.N183** NOTE(QUEUED) · `commit 83b727e / 4f1bd7e / 9ebd20a` — "NTP_Host's settled
  1,024-character bound makes a ~1,026 B piece reachable on /networking, which every measured figure was
  taken below"; "New row W5 ... fits by argument and not by measurement" — Unmeasured worst-case
  response piece. · tracked: REAL_HARDWARE_TEST_QUEUE.md W5 | related: MEM.T* · [H17]
- **REST.N184** NOTE(ANSWERED) · `commit e1dff54` — item 29 answered from source (cyw43 BADAUTH
  catch-all); item 30 "gains a second candidate ... The bench test's fetch() has retried ceiling
  refusals since 2026-09-19, hiding exactly that" — ISL29125 connection reset may be ceiling refusal
  masked by the test's own retry. · tracked: BACKLOG #29 (closed stub), #30 (open) | related: REST.T* ·
  [H17]
- **REST.N185** NOTE(HW-FINDING) · `commit 3062cc7` — "R2's ResetErrors curve climbs ~3.5 s per reader
  and reaches 88-98 % of the 15 s cap at three, so BACKLOG 32's budget waits on 24's design fix"; "Four
  zero-think-time readers saturate the board (F18: PUT starved at the ceiling ...)" — ResetErrors near
  cap; writer starvation under saturation (no admission fairness). · tracked: BACKLOG #24, #32; queue
  F18 | related: REST.T* · [H17]
