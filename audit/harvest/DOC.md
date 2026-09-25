# Harvest — DOC: Documentation set

What the project's own comments, docs and history already record for this area (snapshot `2a88cc8`).
Recorded, not verified or triaged; `audit/HARVEST.md` explains the kinds, tags and method.

Kinds: SETTLED 22, INVAR 19, MIRROR 5, LIMIT 13, RISK 1, ASSUME 8, PLATFORM 1, TODO 5, OPENQ 1, DRIFT 224, NOTE 12 — 311 items.


## src/api_response.py

- **DOC.N001** DRIFT · `src/api_response.py:69` — "request.json has no internal guarding (see
  CLAUDE.md)" — CLAUDE.md contains no such fact; it lives in SPECIFICATION.md:311 (Part A.5), CLAUDE.md
  having moved the Microdot section there. · related: DOC.S05 · [H01]

## src/asy_fram_driver.py

- **DOC.N002** DRIFT · `src/asy_fram_driver.py:151-153` — "Scheduling points live in the public
  coroutines below (PLAN A.1.2)." — "PLAN A.1.2" resolves to no document in the repo (also
  `tests/test_asy_fram_driver.py:1204` "PLAN A.1.4"). · related: DOC.S05 · [H01]

## src/asy_fram_manager.py

- **DOC.N003** DRIFT · `src/asy_fram_manager.py:3` — "AsyFramManager is a bump-pointer allocator (see
  CLAUDE.md for the instantiation-order/on-chip-layout contract)" — The contract lives in
  SPECIFICATION.md:216, 373-374 (A.4/A.7), not CLAUDE.md. · related: DOC.S05 · [H01]

## src/asy_neopixel_driver.py

- **DOC.N004** DRIFT · `src/asy_neopixel_driver.py:3` — "Promoted from
  improved-quality/neopixel_signal.py's proven arbitration mechanism (see CLAUDE.md/BACKLOG.md)." —
  Names a deleted WIP file and a vague doc pointer. · covered-by: DOC.S05 · [H01]

## src/asy_notification_service.py

- **DOC.N005** DRIFT · `src/asy_notification_service.py:3` — "Promoted from
  improved-quality/neopixel_signal.py's `airquality_auto_signal()`/`auto_led_override()` (see
  CLAUDE.md/BACKLOG.md)" — Deleted-file provenance + vague doc pointer. · covered-by: DOC.S05 · [H01]
- **DOC.N006** DRIFT · `src/asy_notification_service.py:68-70` — "see CLAUDE.md's \"Current
  architecture\" note on this deliberate wire-format change" — CLAUDE.md has no "Current architecture"
  note. · covered-by: DOC.S05 · [H01]

## src/asy_scd30_driver.py

- **DOC.N007** DRIFT · `src/asy_scd30_driver.py:162-163` — "it's NVM-persisted and provisioned
  externally via set_ambient_pressure (see CLAUDE.md)" — CLAUDE.md only points onward to
  SPECIFICATION.md Part A.4 (CLAUDE.md:1056) (low). · related: DOC.S05 · [H01]

## src/asy_webserver_service.py

- **DOC.N008** DRIFT · `src/asy_webserver_service.py:112-113` — "per \"Criteria for this step to
  finish\": at least 400/404/405/413/500 wired." — Refers to a step-session criteria list that exists
  nowhere in the repo docs (low) · [H02]
- **DOC.N009** DRIFT · `src/asy_webserver_service.py:123-124` — "Last-registration-wins, by construction
  - decision 6 (see SPECIFICATION.md Part A.8)" — A.8 has no numbered "decision 6" and no
  last-registration-wins statement; same for "decision 7" (:387) and "decision 3" (:698) · [H02]
- **DOC.N010** DRIFT · `src/asy_webserver_service.py:689` — "except Exception as e: # bounds a hanging
  wait_closed() (F.6) as well as any raised error" — Part F.6 is "A SIGINT during gc_collect() can wedge
  the Unix-port heap" (SPECIFICATION.md:4050); no Part F text on a hanging `wait_closed()` · [H02]
- **DOC.N011** DRIFT · `src/asy_webserver_service.py:749-752` — "found missing entirely during the Step
  7 audit, unlike those two" — Historic narrative in a code comment (CLAUDE.md: docs hold current state,
  not history) (low) · [H02]

## src/config_manager.py

- **DOC.N012** DRIFT · `src/config_manager.py:5-7` — "CLAUDE.md has the cache-vs-external-corruption
  trade-off this implies." — CLAUDE.md contains no such trade-off; the nearest text is
  SPECIFICATION.md:1710-1721 · [H02]

## src/system_service.py

- **DOC.N013** DRIFT · `src/system_service.py:191-193` — "Previously logged via the non-persisting
  self.pr.err() - left zero trace in errcount" — Historic narrative in a comment (low) · [H02]

## tests/_sensortask_scenarios.py

- **DOC.N014** DRIFT · `tests/_sensortask_scenarios.py:1275` — "(this module's docstring has the
  rationale)" — the docstring (`:1-3`) only points at Part E.2.1 and gives no rationale (low) · [H03]

## tests/machine.py

- **DOC.N015** DRIFT · `tests/machine.py:2` — "see BACKLOG.md's \"Timer mypy resolution\" finding" — no
  such finding exists in BACKLOG.md (dangling citation) · covered-by: DOC.S05 · [H03]
- **DOC.N016** DRIFT · `tests/machine.py:502` — "fault knobs (A1/A3)" — "A1/A3" is an unresolved ID here
  (also `tests/test_machine_uart_link.py:24`); in `UART_C_PORT_CHANGELOG.md` A1 means CMD-bitmask
  validation (low) · related: DOC.S05 · [H03]
- **DOC.N017** DRIFT · `tests/machine.py:666` — "BACKLOG.md has the history of an earlier pass getting
  this wrong" — BACKLOG.md contains no RTC/weekday/datetime history (dangling citation) (low) · related:
  DOC.S05 · [H03]

## tests/test_asy_fram_driver.py

- **DOC.N018** DRIFT · `tests/test_asy_fram_driver.py:1034` — "WP8: \"currently write protected\"" —
  "WP8" work-package ID not resolvable in current docs (low) · related: DOC.S05 · [H03]
- **DOC.N019** DRIFT · `tests/test_asy_fram_driver.py:1202-1204` — "One hold per command keeps a shared
  bus interleavable between commands while making the envelope indivisible - PLAN A.1.4." — "PLAN A.1.4"
  resolves to no current document (dangling citation) · related: DOC.S05 · [H03]

## tests/test_asy_ntp_client.py

- **DOC.N020** DRIFT · `tests/test_asy_ntp_client.py:478-479` — "see BACKLOG.md's fifth-pass entry: an
  earlier draft got this wrong, returning 0" — BACKLOG.md contains no "fifth-pass" entry (dangling
  reference; history narrative) · - (low) · [H04]
- **DOC.N021** DRIFT · `tests/test_asy_ntp_client.py:2300-2301` — "the exact call shape api_helpers.py's
  cmd_post_check() now makes" — api_helpers.py is the deleted improved-quality file
  (src/api_response.py:2) / legacy python/ one whose cmd_post_check has a different signature; dangling
  reference (same text in test_asy_wifi_service.py:2495) · - (low) · [H04]

## tests/test_asy_scd30_driver.py

- **DOC.N022** DRIFT · `tests/test_asy_scd30_driver.py:457` — "see BACKLOG.md" — BACKLOG.md has no entry
  on the not-ready/"clear to None" decision (dangling pointer) · - (low) · [H04]
- **DOC.N023** DRIFT · `tests/test_asy_scd30_driver.py:1140` — "Regression test for BACKLOG.md's
  torn-read entry" — BACKLOG.md contains no torn-read entry (dangling reference) · - (low) · [H04]

## tests/test_asy_sgp40_driver.py

- **DOC.N024** DRIFT · `tests/test_asy_sgp40_driver.py:179,378` — "(see BACKLOG.md)" — BACKLOG.md has no
  entry on the 0x20 0x2F check or on `err_cnt_internal` (dangling pointers) · - (low) · [H04]
- **DOC.N025** DRIFT · `tests/test_asy_sgp40_driver.py:1153-1154` — "see this file's own module
  docstring on the mocking boundary and SPECIFICATION.md Part E.5.1's \"Reading the numbers\" for why" —
  neither the module docstring nor E.5.1 (a coverage false-negative section) explains const()-folded
  non-importability; pointer looks misdirected · - (low) · [H04]

## tests/test_asy_udp_socket.py

- **DOC.N026** DRIFT · `tests/test_asy_udp_socket.py:399-401 vs PROJECT_AUDIT_PLAN.md NET.S19` — "which
  confirmed the same property holds on real hardware" — plan seed NET.S19 calls lwIP's connected-PCB
  source filtering "unverified", while this comment and BACKLOG.md:197-206 (Q5, closed) say it was
  confirmed on real rp2 · related: NET.S19 · [H04]
- **DOC.N027** DRIFT · `tests/test_asy_udp_socket.py:1207,1458` — "(flagged in BACKLOG.md, out of scope
  to fix there)" / "deliberately does not guard structurally (BACKLOG.md)" — BACKLOG.md has no entry on
  captive_dns's discarded sendto() result or on write() on a server-mode socket (dangling pointers) · -
  (low) · [H04]

## tests/test_asy_webserver_service.py

- **DOC.N028** DRIFT · `tests/test_asy_webserver_service.py:1069` — "a warning, not an error - decision
  8's explicit distinction" — "decision 8" is not identifiable (SPECIFICATION.md's numbered item 8 at
  :2323 is errno numbering) · - (low) · [H04]
- **DOC.N029** DRIFT · `tests/test_asy_webserver_service.py:1100-1102` — "never a mix (CLAUDE.md Part
  F)" — CLAUDE.md has no Part F; the platform facts live in SPECIFICATION.md Part F · - (low) · [H04]
- **DOC.N030** MIRROR · `tests/test_asy_webserver_service.py:2040-2041` — "(MEASUREMENTS archive §7R.5's
  empty 200)" — test anchored to an archived measurement section that lives only in git history
  (HEAP_FRAGMENTATION_MEASUREMENTS.md:14) · - (low) · [H04]

## tests/test_asy_wifi_service.py

- **DOC.N031** DRIFT · `tests/test_asy_wifi_service.py:622-624` — "(e.g. wlan_connect()'s own startup
  path, see BACKLOG.md)" — BACKLOG.md has no entry about the ext_led/wlan_connect startup path (dangling
  pointer) · - (low) · [H04]
- **DOC.N032** DRIFT · `tests/test_asy_wifi_service.py:771-773` — "see CLAUDE.md/SPECIFICATION.md for
  the reasoning" — CLAUDE.md contains no PW-bounds reasoning · related: NET.S16 (low) · [H04]
- **DOC.N033** DRIFT · `tests/test_asy_wifi_service.py:2486-2487,2494-2495` — "for the legacy REST
  layer's own direct reads" / "the exact call shape api_helpers.py's cmd_post_check() now makes" — same
  stale references as test_asy_ntp_client.py:2258-2259/2300-2301 (no REST-layer reader of `.cfg_schema`;
  api_helpers.py deleted/legacy) · - (low) · [H04]

## tests/test_base_classes.py

- **DOC.N034** DRIFT · `tests/test_base_classes.py:479-480` — "not a caller mistake to guard against
  like a negative max_module_error would be (see BACKLOG.md's structural-pass note)" — BACKLOG.md at
  2a88cc8 has no "structural-pass" note and no `max_module_error` mention; the pointer dangles ·
  related: DOC.S05 · [H05]

## tests/test_captive_dns.py

- **DOC.N035** DRIFT · `tests/test_captive_dns.py:30` — "see scripts/test.sh's own TEST_PARALLELISM
  comment" — test.sh's TEST_PARALLELISM comment (scripts/test.sh:125-140) says nothing about the
  ephemeral range; the reasoning lives in SPECIFICATION.md E.1 (:2767-2780) · [H05]
- **DOC.N036** DRIFT · `tests/test_captive_dns.py:230-235` — "Regression test for BACKLOG.md's
  "root-domain query can't be told apart from a failed parse" entry" — Cited BACKLOG entry no longer
  exists · covered-by: DOC.S05 · [H05]
- **DOC.N037** DRIFT · `tests/test_captive_dns.py:343, 1086` — "see Step 6 note" / "Step 6
  (silent-failure-masking finding)" — References a retired step-session ID with no surviving note ·
  related: DOC.S05 · [H05]
- **DOC.N038** DRIFT · `tests/test_captive_dns.py:875, 885` — "exactly async_connect.py's own pattern"
  (test name `..._async_connects_fire_and_forget_cancel_pattern`) — Names the legacy `async_connect.py`;
  the header at :868 names the real caller asy_wifi_service.py · [H05]

## tests/test_config_manager.py

- **DOC.N039** DRIFT · `tests/test_config_manager.py:171-172` — "The old pipe-delimited-string encoding
  corrupted a str default containing "||" (see git history)" — History narrative pointing at git history
  (low) · [H05]

## tests/test_notification_neopixel_integration.py

- **DOC.N040** DRIFT · `tests/test_notification_neopixel_integration.py:2` — "the actual production
  shape src/sensortask_wozi.py wires" — `src/sensortask_wozi.py` no longer exists (generated at build
  time, SPECIFICATION.md L.2); same stale reference in test_notification_scd30_integration.py:98,
  test_notification_scd30_sgp40_integration.py:199, test_notification_sgp40_integration.py:114,
  test_config_manager.py:268,340, test_system_service.py:1413 · related: TEST.S24 · [H05]

## tests/test_notification_scd30_sgp40_integration.py

- **DOC.N041** DRIFT · `tests/test_notification_scd30_sgp40_integration.py:1` — "matching
  sensortask-wozi.py's real single notify/pixel wiring" — Names the retired
  `improved-quality/sensortask-wozi.py`; also test_ntp_fram_system_integration.py:1, 79, 341 and
  test_ntp_wifi_dns_integration.py:1, 71 · related: TEST.S24 · [H05]

## tests/test_notification_sgp40_integration.py

- **DOC.N042** DRIFT · `tests/test_notification_sgp40_integration.py:44` — "the ~180-cycle
  settle-then-spike sequence" — Code runs 160 settle + up to 40 spike cycles (:158, :164);
  test_notification_scd30_sgp40_integration.py:149 says "200" (low) · [H05]

## tests/test_print_log.py

- **DOC.N043** DRIFT · `tests/test_print_log.py:379-380` — "(see BACKLOG.md - tests/_fram_mock.py and
  its flat, non-redundant abstraction are retired" — BACKLOG.md has no `_fram_mock` entry; dangling
  pointer · related: DOC.S05 · [H05]

## tests/test_system_service.py

- **DOC.N044** DRIFT · `tests/test_system_service.py:1413-1414` — "exactly what sensortask_wozi.py's
  _collect_level_setters() does" — Names a retired hand-written module; the behaviour now lives in
  generated code · related: TEST.S24 · [H05]

## tests/test_uart_comm_hazard.py

- **DOC.N045** DRIFT · `tests/test_uart_comm_hazard.py:784-785` — "The module refuses the configuration
  instead (B17)" — Bare changelog-row ID; B17 lives in UART_C_PORT_CHANGELOG.md:88, a file slated for
  deletion at reconciliation (low) · related: DOC.S14 · [H05]

## tests/test_voc_algorithm.py

- **DOC.N046** DRIFT · `tests/test_voc_algorithm.py:552` — "not a claim that any real caller exercises
  it (see BACKLOG.md)" — BACKLOG.md has no entry about set_tuning_parameters; dangling pointer ·
  related: DOC.S05 · [H05]

## digital_twin/README.md

- **DOC.N047** DRIFT · `digital_twin/README.md:14 vs :369-371` — ":14
  `build/generated_src:src:tests:frozen_modules:.frozen`" vs ":370 currently
  `src:tests:frozen_modules:.frozen`" — The same doc states two different MICROPYPATH values for
  `scripts/test.sh`; one is stale (and README says it is "set internally per test file") · [H06] ⟨quote
  not matched at the anchor⟩
- **DOC.N048** DRIFT · `digital_twin/README.md:107-109` — "`WLAN.connect()` transitions to a successful,
  connected state immediately" — Contradicted by `network.py`'s 0.7 s async connect phase · covered-by:
  TWIN.S06 · [H06]
- **DOC.N049** DRIFT · `digital_twin/README.md:265 vs :183-188` —
  "MICROPYPATH=\"/tmp/twin_boot:src:digital_twin:ext:.frozen\"" — The generated-device example omits
  `frozen_modules`, which :183-188 says is required for `import frozen_html` · [H06]
- **DOC.N050** DRIFT · `digital_twin/README.md:234` — "consuming a Session-3
  `buildgen.generate.generate_device()`-generated module" — Retired session-numbering term in current
  doc (low) · [H06]
- **DOC.N051** DRIFT · `digital_twin/README.md:270-271` — "the same pattern
  `scripts/_digital_twin_ci_suite.py` already uses for the hand-written wozi module" — No hand-written
  wozi module exists any more (:256-257, L.2) · [H06]
- **DOC.N052** DRIFT · `digital_twin/README.md:374-376` — "All tests are deterministic — no wall-clock
  waiting, except one short-period/generous-timeout smoke test" — Stale: twin test files wait on real
  wall-clock time well beyond that one smoke test (e.g. 9 s runs and a 75 s hold in
  `tests/test_digital_twin_bus_hazard_concurrency.py:185-227, 392`; 9 s in
  `tests/test_digital_twin_sensortask_integration.py:461`) · related: TEST.T04 · [H06]
- **DOC.N053** DRIFT · `digital_twin/README.md:408, :408-412 (agent cited digital_twin/README.md:390, :408-412)`
  — "same 14-run suite" / "17 for `wozi`, 18 for `dev`" — Hard-coded run/process counts that drift as
  the suite grows (low) · related: SCR.T04 · [H06] ⟨re-anchored: quote found at line 408⟩
- **DOC.N054** DRIFT · `digital_twin/README.md:449-453` — "this line claiming otherwise — citing a Part
  A.7 that never said it — was the same stale assumption" — Historic correction narrative left in the
  doc (low) · [H06]
- **DOC.N055** DRIFT · `digital_twin/README.md:667-669` — "What is still missing is an elapsed-time
  budget well below the cap ... the suite is blind to the whole 5-15s band" — Contradicted by
  `scripts/_digital_twin_ci_suite.py:116, 273-281` (`_RESET_ERRORS_BUDGET_S = cap*0.8`, asserted) and
  BACKLOG.md:371 · [H06]
- **DOC.N056** DRIFT · `digital_twin/README.md:675-676 vs digital_twin/launch.py:71-80` —
  "`sgp40`/`scd30` (`writeto`/`readfrom_into`), `bmp3xx` (`readfrom_mem`/`writeto_mem`), `fram`
  (`write`/`readinto`)" — README's `--hang` op list omits `isl29125` (`readfrom_mem`/`writeto_mem`),
  which `_HANG_DEVICE_OPS` accepts (low) · [H06]
- **DOC.N057** DRIFT · `digital_twin/README.md:776-778` — "see `BACKLOG.md`'s \"Real-hardware
  verification gap\" entry for the full account" — BACKLOG.md:197 is now a closed stub pointing to
  `tests_hardware/README.md` (low) · [H06]
- **DOC.N058** DRIFT · `digital_twin/README.md:854-856` — "same as `src/`/`tests/` - all three are
  expected to stay fully clean" / "`ruff check src tests digital_twin`" — CLAUDE.md now describes eight
  scopes; the command/count may be stale (low) · [H06]
- **DOC.N059** DRIFT · `digital_twin/README.md:861-863` — "`digital_twin/launch.py`/every
  `tests/test_digital_twin_*.py` are excluded from the main pass" — CLAUDE.md's list also names
  `run_generic_integration.py`/`segfault_stress_repro.py`; README's list is shorter (low) · [H06]

## digital_twin/machine.py

- **DOC.N060** DRIFT · `digital_twin/machine.py:302, 310, 917` — "by whatever entry point Step 5 writes"
  / "lets a Step 5 harness" — Retired step-session references; the entry point is
  `run_generic_integration.py` (low) · related: TEST.S24 · [H06]

## digital_twin/_fault_injection.py

- **DOC.N061** DRIFT · `digital_twin/_fault_injection.py:3` — "See `machine.WDT`'s own `_countdown()`
  for why this - not a bounded raise - is what actually risks starving" — 3-line docstring holds a
  ~700-char line (comment-cap evasion) · covered-by: TEST.S22 · [H06]

## digital_twin/_scd30_chip.py

- **DOC.N062** DRIFT · `digital_twin/_scd30_chip.py:98-100, :223` — "which the class docstring explains
  staying unpersisted" / "see class docstring" — `Scd30Chip` has no class docstring; the module
  docstring (:1-2) is the only one (low) · [H06]

## digital_twin/network.py

- **DOC.N063** DRIFT · `digital_twin/network.py:2 vs digital_twin/README.md:107-109` — "`connect()`
  transitions through realistic phases over a short real delay rather than resolving instantly" — Code
  docstring contradicts README's "immediately" · covered-by: TWIN.S06 · [H06]
- **DOC.N064** DRIFT · `digital_twin/network.py:71` — "Test/Step-5-run fault injection" — Retired
  step-session term (low) · [H06]

## digital_twin/run_generic_integration.py

- **DOC.N065** DRIFT · `digital_twin/run_generic_integration.py:1` — "most usefully a Session-3
  `buildgen.generate.generate_device()`-generated one" — Retired session-numbering term (low) · [H06]
- **DOC.N066** DRIFT · `digital_twin/run_generic_integration.py:1-2` — "This file's own fault/hang chip
  lookup is the generalized form of `run_wozi_integration.py`'s..." — Very long docstring lines
  (comment-cap evasion) and references to retired runners · covered-by: TEST.S22 · [H06]
- **DOC.N067** DRIFT · `digital_twin/run_generic_integration.py:32-34, :96-98, :311-313` — "unlike
  run_wozi_integration.py/run_dev_integration.py's own static imports" / "See both call sites' own
  comments in run_wozi_integration.py" — References to deleted files; :312-313 points readers at a file
  that no longer exists · covered-by: TEST.S24 · [H06]

## tests/test_digital_twin_fram.py

- **DOC.N068** DRIFT · `tests/test_digital_twin_fram.py:303-308` — "SPECIFICATION.md Part L.4:
  _decode_addr() used to always read exactly 2 address bytes ... discovered via a real digital-twin CI
  failure" — Historic bug narrative in a test comment (low) · [H06]

## tests/test_digital_twin_http_client.py

- **DOC.N069** DRIFT · `tests/test_digital_twin_http_client.py:249` — "_soak() and _wait_until_serving()
  never look at a fetched body" — `_soak()` no longer exists anywhere in the repo (soak moved host-side)
  (low) · related: TEST.S24 · [H06]

## tests/test_digital_twin_run_generic_integration.py

- **DOC.N070** DRIFT · `tests/test_digital_twin_run_generic_integration.py:2` — "The smoke test reuses
  the hand-written sensortask_wozi module" — No hand-written module exists; also a ~700-char docstring
  line · covered-by: TEST.S24 · [H06]
- **DOC.N071** DRIFT · `tests/test_digital_twin_run_generic_integration.py:137-138, 221` — "replaces
  run_wozi_integration.py's/run_dev_integration.py's own hardcoded ..." / "the retired
  run_wozi_integration.py's own test used" — References to retired runners · covered-by: TEST.S24 ·
  [H06] ⟨quote not matched at the anchor⟩

## tests/test_digital_twin_sensortask_integration.py

- **DOC.N072** DRIFT · `tests/test_digital_twin_sensortask_integration.py:178-179, 184-186, 415-417` —
  "see the \"Construction across every real device\" section near the end of this file" — No such
  section exists in this file any more (moved to `tests/_digital_twin_construction_scenarios.py`, E.2.1)
  · [H06]

## tests_hardware/README.md

- **DOC.N073** DRIFT · `tests_hardware/README.md:770-771` — "nothing checked the real
  `max_connections=4` ceiling" — Historic value; :803 says 6 on dev (history narrative). · related:
  DOC.T05 (low) · [H08]
- **DOC.N074** DRIFT · `tests_hardware/README.md:1384` — "CLAUDE.md's implicit-FRAM-wiring rule's own
  capacity backstop" — CLAUDE.md never states that rule as a rule. · covered-by: DOC.S12 · [H08]
- **DOC.N075** DRIFT · `tests_hardware/README.md:256, 288-289, 297, 313, 317, 338, 382` —
  "`HEAP_FRAGMENTATION_MEASUREMENTS.md` archive §7O" — "archive §7…" citations resolve only at commit
  `12640c2`. · related: DOC.S04 · [H08]
- **DOC.N076** DRIFT · `tests_hardware/README.md:1179` — "(project owner, 2026-09-15, BACKLOG.md HIGH
  PRIORITY item)" — No "HIGH PRIORITY" item exists in BACKLOG.md at the snapshot (dangling). · related:
  DOC.T02 (low) · [H08]
- **DOC.N077** DRIFT · `tests_hardware/README.md:686-1296` — "## Third pass - closing real coverage
  gaps" — Eight "pass" sections are dated narrative with counts (44→54→65) — history vs current-state
  rule (stale dated counts). · covered-by: DOC.T05 (low) · [H08]

## REAL_HARDWARE_TEST_QUEUE.md (snapshot only; being updated by another session)

- **DOC.N078** DRIFT · `REAL_HARDWARE_TEST_QUEUE.md:13-14` — "the file at commit `12640c2`" — Every
  "§7…" citation in the queue resolves only against the archive commit. · related: DOC.S04 · [H08]
- **DOC.N079** DRIFT · `REAL_HARDWARE_TEST_QUEUE.md:227` — "Record it as §2.1's third and fourth [HW]
  columns." — HEAP_FRAGMENTATION_MEASUREMENTS.md has no §2.1 (sections are M1-M8) — dangling target. ·
  related: DOC.T02 · [H08]

## HARDWARE_TEST_HANDOVER.md (snapshot only; sitting IN PROGRESS in another session)

- **DOC.N080** DRIFT · `HARDWARE_TEST_HANDOVER.md:21-22` — "(86/86 MicroPython files, 2,100 pytest)" —
  Dated count; 87 test files at planning time. · covered-by: DOC.S08 · [H08]
- **DOC.N081** INVAR · `HARDWARE_TEST_HANDOVER.md:107-108` — "Measured values that only support a
  decision do not need a permanent home beyond the commit that records them." — Migration rule for
  sitting results. · related: HW.T16 (low) · [H08]
- **DOC.N082** DRIFT · `HARDWARE_TEST_HANDOVER.md:192-206` — "The full list is the queue's section 6 and
  `tests_hardware/README.md`." — Traps restated a third time (queue §6, README). · covered-by: DOC.S15
  (low) · [H08]

## dev_legacy/README.md

- **DOC.N083** SETTLED · `dev_legacy/README.md:5-9` — "**The current, maintained single source of truth
  for the physical \"dev\" RP2040 bench unit**" — Claims single-source status for wiring/bench state,
  while queue/handover/`devices/dev.toml` also hold board facts. · covered-by: DOC.S15 · [H08]

## scripts/lint.sh

- **DOC.N084** DRIFT · `scripts/lint.sh:17` — "they carry 28 findings of their own, including no shebang
  at all - see BACKLOG.md" — BACKLOG.md at 2a88cc8 contains no "28 findings"/"no shebang" entry:
  dangling reference (and a dated count). · covered-by: DOC.S05 · [H09]

## scripts/build_website.sh

- **DOC.N085** DRIFT · `scripts/build_website.sh:11` — "<device> matches an
  html/definitions/<device>.json file, e.g. \"wozi\"." — Only wozi/dev have one; lines 26-38 generate
  the rest from `devices/<device>.toml`. · covered-by: DOC.S18 · [H09]

## scripts/_strip_type_checking.py

- **DOC.N086** DRIFT · `scripts/_strip_type_checking.py:11-13` — "left untouched rather than guessed at,
  per BACKLOG.md's original prototype note" — BACKLOG.md has no such note: dangling citation. ·
  covered-by: DOC.S05 · [H09]

## buildgen/frozen_modules.py

- **DOC.N087** DRIFT · `buildgen/frozen_modules.py:3` — "feeding them to freeze() is Session 6's job" —
  Retired session label; the job is `scripts/build_firmware.py`. (low) · related: DOC.S16 · [H09]

## buildgen/generate.py

- **DOC.N088** DRIFT · `buildgen/generate.py:2-3` — "callers decide where to write them (Session 6 owns
  the real `build/<device>/` tree)" — No `build/<device>/` tree exists (outputs are
  `build/generated_src/` and `build/firmware-<device>.uf2`); SPECIFICATION.md L.2 (:6027) states the
  same layout. · related: DOC.S16 · [H09]

## buildgen/version.py

- **DOC.N089** DRIFT · `buildgen/version.py:3` — "(see that session's own account for the full consumer
  list/reasoning)" — Dangling reference to an unnamed session. (low) · related: DOC.S05 · [H09]

## .gitignore

- **DOC.N090** DRIFT · `.gitignore:27-31` — "the natural home for any future
  build/<device>/{py,html,frozen,firmware} staging tree" — Same unrealised `build/<device>/` layout as
  generate.py:3 and SPECIFICATION.md L.2. (low) · [H09]

## tests_scripts/_devices.py

- **DOC.N091** DRIFT · `tests_scripts/_devices.py:1-3` — "Six test modules carried their own copy" —
  Historic count/narrative in a header (current-state rule); count not re-verified · related: DOC.T05
  (low) · [H10]

## tests_scripts/_toml_fixtures.py

- **DOC.N092** DRIFT · `tests_scripts/_toml_fixtures.py:14-15` — "deliberately import-independent from
  buildgen/ - see the module docstring" — The module docstring (:1-3) says nothing about import
  independence — dangling pointer (low) · [H10]

## tests_scripts/buildgen_fixtures/multi_instance.toml

- **DOC.N093** DRIFT · `tests_scripts/buildgen_fixtures/multi_instance.toml:16-17` — "Not a real device
  - never flashed, never referenced outside tests_scripts/test_buildgen_*.py" — Both synthetic fixtures
  are also booted by tests_scripts/test_digital_twin_generated_boot.py:57 (globs buildgen_fixtures/) and
  used in digital_twin/README.md:247-273; same claim at novel_combo.toml:4-5 · [H10]

## tests_scripts/test_build_firmware.py

- **DOC.N094** DRIFT · `tests_scripts/test_build_firmware.py:207` — "Parametrized over all six real
  devices" — Parametrization is now discovered (`DEVICE_NAMES`), so "six" is a hardcoded count that will
  go stale on a seventh device (low) · related: DOC.T08 · [H10]

## tests_scripts/test_build_website_sh.py

- **DOC.N095** DRIFT · `tests_scripts/test_build_website_sh.py:26-29` — "see scripts/build_website.sh's
  own \"Bundling\" comment for why" — Points at a comment the plan records as removed · covered-by:
  WEB.S21 · [H10]

## tests_scripts/test_buildgen_definitions.py

- **DOC.N096** DRIFT · `tests_scripts/test_buildgen_definitions.py:178` — "proving generality beyond the
  6 real, hand-verified devices" — Hardcoded device count (low) · related: DOC.T08 · [H10]

## tests_scripts/test_buildgen_generate.py

- **DOC.N097** DRIFT · `tests_scripts/test_buildgen_generate.py:1` — "against all 6 real devices/*.toml"
  — Parametrization is discovered; "6" is a stale-prone count (low) · related: DOC.T08 · [H10]

## tests_scripts/test_buildgen_tag_comments.py

- **DOC.N098** DRIFT · `tests_scripts/test_buildgen_tag_comments.py:2,345-347` — "and the planned `# @web`/`# @web-group`
  tags" / "a short tag name (the planned \"@web\")" — `@web`/`@web-group` are implemented
  (test_buildgen_web_tag.py); the test file repeats the stale "planned" wording the plan records in
  tag_comments.py · related: GEN.S14 · [H10]

## tests_scripts/test_buildgen_twin_wiring.py

- **DOC.N099** DRIFT · `tests_scripts/test_buildgen_twin_wiring.py:1,125` — "proving generality beyond
  the 6 real, hand-verified devices" — Hardcoded device count (low) · related: DOC.T08 · [H10]

## tests_scripts/test_buildgen_version.py

- **DOC.N100** DRIFT · `tests_scripts/test_buildgen_version.py:2-3` — "no bump mechanism is assumed to
  exist (see that session's own account for why)" — Dangling pointer to an unnamed "session's own
  account" · related: DOC.T02 · [H10]

## tests_scripts/test_comment_block_cap.py

- **DOC.N101** INVAR · `tests_scripts/test_comment_block_cap.py:1-3,14` — "Python and shell only -
  JS/CSS keep their own syntax and stay review-enforced." — Machine gate for CLAUDE.md's 3-line cap
  covers `*.py`/`*.sh` in exactly 8 SCOPES (src, buildgen, digital_twin, toolchain, scripts, tests,
  tests_scripts, tests_hardware); JS, CSS, HTML, config files (TOML/YAML/INI), `devices/`, `.github/`
  are review-only · related: CI.T08 · [H10]
- **DOC.N102** LIMIT · `tests_scripts/test_comment_block_cap.py:59` — "if not any(tag in line for line
  in lines[s - 1 : s - 1 + n] for tag in _TAGS)" — An over-cap comment block is exempted wholesale if
  ANY line contains a tag substring ("@web", "@requires", ...), so prose that merely mentions a tag, or
  prose around a tag line, is never measured — weaker than CLAUDE.md's "the prose introducing them is
  not exempt" · [H10]
- **DOC.N103** LIMIT · `tests_scripts/test_comment_block_cap.py:20,34` — "_PEP723 =
  re.compile(r\"^#\\s*(///|requires-python\\s*=|dependencies\\s*=)\")" — PEP 723 exemption treats
  matching lines as punctuation anywhere in a file (not only inside a `# /// script` block); multi-line
  dependency list entries inside a block count as prose · [H10]
- **DOC.N104** LIMIT · `tests_scripts/test_comment_block_cap.py:62-85` — "if not isinstance(node,
  (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))" — Only real docstrings are
  measured; physical lines only (E501 ignored), so a paragraph packed on one long line passes ·
  covered-by: TEST.S22 · [H10]
- **DOC.N105** LIMIT · `tests_scripts/test_comment_block_cap.py:27-29` — "return
  stripped.startswith(\"#\") and not stripped.startswith(\"#!\")" — Comment detection is line-textual:
  `#` lines inside multi-line strings or shell heredocs are counted as comments (possible false
  positives, not misses) (low) · [H10]
- **DOC.N106** LIMIT · `tests_scripts/test_comment_block_cap.py:105-109` — "Guards the detector: a glob
  that silently matched nothing would pass everything vacuously." — Vacuity floor: every scope non-empty
  and > 200 files total · [H10]

## tests_scripts/test_device_tomls.py

- **DOC.N107** DRIFT · `tests_scripts/test_device_tomls.py:575-577` — "any source exposing a matching
  attribute name is structurally valid class to check against)" — Garbled comment (a clause is missing)
  (low) · [H10]
- **DOC.N108** DRIFT · `tests_scripts/test_device_tomls.py:244` — "shape/parse tests, run against the 6
  real files" — Hardcoded count (low) · related: DOC.T08 · [H10]

## tests_scripts/test_digital_twin_ci_suite_errcount.py

- **DOC.N109** DRIFT · `tests_scripts/test_digital_twin_ci_suite_errcount.py:277` — "elapsed_s=8.28) #
  the worst real twin sample" — Conflicts with :300's "the twin's worst observed dev sweep is 8.91s"
  (low) · [H10]

## tests_scripts/test_digital_twin_generated_boot.py

- **DOC.N110** DRIFT · `tests_scripts/test_digital_twin_generated_boot.py:1-2,150-152` — "the same
  pattern scripts/_digital_twin_ci_suite.py already uses for the hand-written sensortask_wozi.py; wiring
  this into scripts/run_digital_twin_ci.sh stays Session 6's job" — Hand-written sensortask modules are
  retired (L.2) and the CI suite already boots generated modules; "Session 3/6" labels are undefined ·
  related: TEST.S24 · [H10]

## tests_scripts/test_heap_map_parser.py

- **DOC.N111** DRIFT · `tests_scripts/test_heap_map_parser.py:194-203` — "a contract between ONE parser
  regex and THREE independent emitters - two device scripts and the twin probe" — `_EMITTERS` lists five
  emitters (four device scripts + the twin probe) · [H10]

## tests_scripts/test_memory_error_gate_agreement.py

- **DOC.N112** ASSUME · `tests_scripts/test_memory_error_gate_agreement.py:69-71` — "it is per-test
  scratch that 85 concurrently running test files create and delete" — Dated count of MicroPython-tier
  test files · related: DOC.S08 · [H10]

## tests_scripts/test_micropython_overrides.py

- **DOC.N113** DRIFT · `tests_scripts/test_micropython_overrides.py:1-3` — "Tests
  toolchain/micropython_overrides.py's unix_kbd_intr override in isolation" — The file also covers the
  lwip_connection_counts override, the lwIP ensemble arithmetic, the preprocessor readback and
  build_firmware wiring; header describes only the first (low) · [H10]

## tests_scripts/test_persistence_write_marker_completeness.py

- **DOC.N114** DRIFT · `tests_scripts/test_persistence_write_marker_completeness.py:194-196` — "Exactly
  one exists today and it provably persists nothing" — `_JUSTIFIED_UNREADABLE_BODIES` (:186-190) holds
  two entries (the 413 test and `_put_sized`) · [H10]
- **DOC.N115** DRIFT · `tests_scripts/test_persistence_write_marker_completeness.py:230-232,243` —
  "F15's residual, closed." / "F14's first draft is replayed verbatim" — Cites temporary queue row IDs
  from permanent code (low) · related: DOC.T03 · [H10]

## tests_scripts/test_request_body_cap_headroom.py

- **DOC.N116** DRIFT · `tests_scripts/test_request_body_cap_headroom.py:2-3` — "every new driver grows
  it - dev's `/sensors` is 338 B larger than wozi's purely for carrying one more sensor" — All six
  devices pin the same 1312 B largest body, so the binding route is not driver-dependent today; "every
  new driver grows it" does not describe the pinned maximum (low) · [H10]

## tests_scripts/test_strip_type_checking.py

- **DOC.N117** DRIFT · `tests_scripts/test_strip_type_checking.py:51-52` — "BACKLOG.md's prototype note
  says leave any compound condition untouched rather than guess" — Dangling named citation · covered-by:
  DOC.S05 · [H10]

## tsconfig.json

- **DOC.N118** DRIFT · `tsconfig.json:11-15, 29-35` — "// Everything TypeScript offers beyond
  `strict`..." — comment blocks of 5 and 7 lines exceed the 3-line cap · covered-by: CI.S10 · [H11]

## tsconfig.node.json

- **DOC.N119** DRIFT · `tsconfig.node.json:2-6, 17-21` — "// Second, separate tsc invocation ..." —
  over-cap comment blocks · covered-by: CI.S10 · [H11]

## tests_js/vitest-commands.d.ts

- **DOC.N120** DRIFT · `tests_js/vitest-commands.d.ts:1-6, 8-17, 19-23` — "// Ambient module
  augmentation for the custom Vitest browser commands ..." — three `//` paragraphs of 6, 10 and 5 prose
  lines exceed CLAUDE.md's 3-line cap, which applies to all code incl. tests_js; not in the plan's cap
  findings · related: CI.T08 · [H11]

## tests_js/live-backend-put-matrix.test.js

- **DOC.N121** DRIFT · `tests_js/live-backend-put-matrix.test.js:17-21` — "Three documented backend
  quirks ... Part H.7 has the full account." — H.7 (SPECIFICATION.md:4517-4630) has no such account; the
  quirks note is H.4 (:4367-4370). ISLCalibrate is absent from the list (wozi-only matrix) (low) · [H11]

## tests_js/main.test.js

- **DOC.N122** DRIFT · `tests_js/main.test.js:47-50, 127-129` — "build_website.sh's \"Inlining\" note" /
  "scripts/build_website.sh's own \"Inlining\" comment" — cites a comment that no longer exists (same
  dangling pointer as html/index.html:40-41) · related: WEB.S21 · [H11]

## SPECIFICATION.md front matter (1-28)

- **DOC.N123** DRIFT · `SPECIFICATION.md:6-7` — "CLAUDE.md (AI-session operating constraints — hard
  rules, working agreements, PR workflow, pre-push verification" — Calls the chroot check "pre-push
  verification", but CLAUDE.md (owner, 2026-09-18) made it a periodic owner-run check, not a push gate.
  · covered-by: DOC.S08 · [H12]
- **DOC.N124** SETTLED · `SPECIFICATION.md:6-9` — "Not here, by design: CLAUDE.md ... and BACKLOG.md
  (active working memory" — Doc-placement decision: rules stay in CLAUDE.md, open work in BACKLOG.md,
  never folded into the spec. · related: DOC.T06 · [H12]

## SPECIFICATION.md Part A.1 (Repository layout, 29-92)

- **DOC.N125** SETTLED · `SPECIFICATION.md:36-39` — "arduino/ ... Outside this project's scope (owner,
  2026-09-24): no lint/type/test, no reconciliation" — Owner decision placing the C peer entirely out of
  scope. · related: LIC.T04 · [H12]
- **DOC.N126** LIMIT · `SPECIFICATION.md:88` — "update_and_install.txt Legacy manual toolchain recipe,
  superseded by toolchain/ (kept for reference)" — A kept-but-superseded recipe; can drift from
  toolchain/. · related: DOC.S15 · [H12]
- **DOC.N127** DRIFT · `SPECIFICATION.md:90` — "scripts/ lint.sh/typecheck.sh/test.sh,
  build_frozen_html.sh, run_unix_port_integration.sh" — Layout lists 5 of ~20 scripts
  (build_firmware.py, build_website.sh, twin/hardware runners omitted). (low) · [H12]

## SPECIFICATION.md Part A.2 (Architecture at a glance, 94-127)

- **DOC.N128** DRIFT · `SPECIFICATION.md:123` — "Task supervisor (`main()` in every `sensortask-*.py`)"
  — Names the legacy files; refactor supervisor is `system_service.py` called from generated modules.
  (low) · related: DOC.S09 · [H12]
- **DOC.N129** DRIFT · `SPECIFICATION.md:125` — "Units run years unattended." — CLAUDE.md's WP6 rule
  says "months between reboots"; inconsistent lifetime claims. (low) · [H12]

## SPECIFICATION.md Part A.3 (Refactor status, 129-146)

- **DOC.N130** DRIFT · `SPECIFICATION.md:131-134` — "the still-uncovered path is the legacy
  `python/`+`build-*.sh` pipeline, BACKLOG.md" — Frames legacy CI coverage as open work; CLAUDE.md says
  the legacy tree never gets work ("the gap is the decision"). · covered-by: DOC.S21 · [H12]

## SPECIFICATION.md Part A.4 (Architecture — deep reference, 148-285)

- **DOC.N131** DRIFT · `SPECIFICATION.md:221-224` — "every current FRAM-chunk-owning construction
  (`sysfunct`, `sgp40`'s VOC chunk, `neopixel`, `notification`) is unconditional top-level" — List
  predates WP1-WP3: conn/ntp/DNSServer/webserver/cfgmgr/uart_link/isl29125 chunks omitted. · related:
  XCUT.S09 · [H12]

## SPECIFICATION.md Part A.6 (Datasheets, 337-356)

- **DOC.N132** DRIFT · `SPECIFICATION.md:339-340` — "(`bmp3xx/`, `fram/`, `pico w/`, `scd30/`,
  `sgp40/`)" — Omits `datasheets/isl29125/` (present on disk; A.1:34 lists it). · covered-by: DOC.S08 ·
  [H12]

## SPECIFICATION.md Part A.7 (wozi's construction order and dependency graph, 358-569)

- **DOC.N133** DRIFT · `SPECIFICATION.md:376` — "as of WP1/CLAUDE.md's implicit-FRAM-wiring rule" —
  Undefined `WP1`-`WP8` labels used throughout Parts A-E; CLAUDE.md never states an
  "implicit-FRAM-wiring rule" as such. · covered-by: DOC.S16 · [H12]
- **DOC.N134** DRIFT · `SPECIFICATION.md:387-389` — "no chunk of its own (Topic 11's rule: every module
  gets optional FRAM logging except the FRAM module itself" — "Topic 11" is an undefined/retired
  reference. · related: DOC.T02 · [H12]
- **DOC.N135** DRIFT · `SPECIFICATION.md:437-438` — "(WP3 - was wrongly, deliberately excluded" —
  Self-contradicting history narrative in a current-state doc. (low) · related: DOC.T05 · [H12]
- **DOC.N136** DRIFT · `SPECIFICATION.md:462-463` — "`await x.setup()` batch: `sysfunct → fram → conn → ntp → sgp40 → bmp3xx → notification`"
  — Generator emits `fram → sysfunct → ...`. · covered-by: DOC.S09 · [H12]

## SPECIFICATION.md Part A.8 (REST API endpoint reference, 571-625)

- **DOC.N137** DRIFT · `SPECIFICATION.md:585-586` — "SPECIFICATION.md Part L Session 7" — "Session N"
  labels (also :948, :2174, :2382-2384) are undefined — Part L has no Session headings. · related:
  DOC.S16 · [H12]

## SPECIFICATION.md Part B intro, B.1-B.3 (688-753)

- **DOC.N138** DRIFT · `SPECIFICATION.md:746-748` — "clean up, rebuild a vanilla Unix port as the
  standing test rig" — Two Unix ports are kept now (B.5); step list names one. (low) · [H12]

## SPECIFICATION.md Part B.4-B.9 (754-826)

- **DOC.N139** DRIFT · `SPECIFICATION.md:795` — "A completed run leaves no vanilla RP2 `firmware.uf2`;
  step 8's Unix port is the only kept artifact." — `build-settrace` is also built and kept (B.5:776,
  `toolchain/setup_toolchain.py:517`). (low) · [H12]
- **DOC.N140** DRIFT · `SPECIFICATION.md:821-826` — "Does not yet wire up `build-*.sh`'s hardcoded
  `/home/nico/rpi_pico/...` paths ... the remaining gap is the RP2040 firmware build" — Legacy framed as
  TODO (contradicts CLAUDE.md "never gets work"); firmware build now covered by `firmware-build-verify`.
  · covered-by: DOC.S08 · [H12]

## SPECIFICATION.md Part B.11 (Building this project's firmware, 931-984)

- **DOC.N141** DRIFT · `SPECIFICATION.md:939-941` — "Still assumes `python/` is checked out as
  `py-include/python` alongside `micropython`, path not yet genericized (BACKLOG.md)" — Legacy framed as
  open work vs CLAUDE.md legacy rule. · covered-by: DOC.S21 · [H12]
- **DOC.N142** DRIFT · `SPECIFICATION.md:946-948` — "replaces the former hand-written
  `boot_entry/<device>_boot.py` (retired, Session 6's finish criterion)" — Undefined "Session 6" label.
  (low) · related: DOC.S16 · [H12]
- **DOC.N143** DRIFT · `SPECIFICATION.md:972-976` — "`test_real_firmware_build_produces_a_valid_uf2`
  does the real end-to-end build (parametrized over `wozi`/`dev`)" — Test is parametrized over
  `DEVICE_NAMES` (all six, `tests_scripts/test_build_firmware.py:196`); CI runs six. · [H12]
- **DOC.N144** DRIFT · `SPECIFICATION.md:975-976` — "closing the \"no CI firmware-build stage\" gap for
  this pipeline (legacy `build-*.sh` stays open, BACKLOG.md)" — Legacy framed as open. · covered-by:
  DOC.S21 · [H12]

## SPECIFICATION.md Part B.14.1 (`unix_kbd_intr`, 1116-1213)

- **DOC.N145** DRIFT · `SPECIFICATION.md:1198-1199` — "`build_unix_port()` (both call sites - the
  frozen-verification build and the vanilla test-rig rebuild)" — Three call sites now (settrace build,
  `toolchain/setup_toolchain.py:503, 514, 517`). (low) · [H12]

## SPECIFICATION.md Part B.15 (The three mypy passes, 1413-1473)

- **DOC.N146** DRIFT · `SPECIFICATION.md:1439-1441` — "and the two shared scenario libraries
  (`_webserver_concurrency_scenarios.py`, `_digital_twin_construction_scenarios.py`)" — CLAUDE.md's
  exclusion list omits these two libraries. (low) · [H12]

## SPECIFICATION.md Part C intro, C.1-C.2 (1475-1535)

- **DOC.N147** DRIFT · `SPECIFICATION.md:1486, 1493-1494` — "A new driver adds layers 2-3 only (one
  file, `asy_<sensor>_driver.py`) plus a `_Reader` wiring block in the relevant `sensortask-*.py`." —
  Layer 4 is now buildgen-generated from `devices/*.toml`; no hand-written wiring block exists (Part
  K/L). · related: DOC.S09 · [H12]

## SPECIFICATION.md Part C.3.2 (UART variant, 1598-1622)

- **DOC.N148** MIRROR · `SPECIFICATION.md:1613` — "see `UART_C_PORT_CHANGELOG.md` B15." — Spec ↔
  temporary changelog entry ID (changelog deletion would dangle). · related: DOC.S14 · [H12]

## SPECIFICATION.md Part C.4 (Layer 3 Reader, 1624-1697)

- **DOC.N149** DRIFT · `SPECIFICATION.md:1630` — "`read_loop()` skeleton (identical across all three
  drivers)" — Four sensor drivers now (ISL29125). · covered-by: DOC.S08 · [H12]

## SPECIFICATION.md Part C.5 / C.5.1-C.5.3 (Config schema system, 1699-1797)

- **DOC.N150** DRIFT · `SPECIFICATION.md:1794-1797` — "`AsyConnTime` owns one schema but
  `/net/cmd`/`/led/cmd` each own only their own subset (`sensortask-wozi.py`'s `_cfg_subset(schema, keys)`)"
  — Routes and helper no longer exist (A.8 lists `/networking`). · covered-by: DOC.S09 · [H12]

## SPECIFICATION.md Part C.6 (Data model, 1799-1805)

- **DOC.N151** DRIFT · `SPECIFICATION.md:1801-1805` — "via `repr()`-parsing ... Known dormant landmine:
  parsing splits on `\"(\"`/`\",\"`" — Seed says the code no longer repr()-parses. · covered-by: DOC.S09
  · [H12]

## SPECIFICATION.md Part C.7 (Error handling & logging contract, 1807-1891)

- **DOC.N152** DRIFT · `SPECIFICATION.md:1823-1826` — "every FRAM-backed logger runs its own
  `pr.setup()` from *inside its task* (... SYSTEM in `start_and_check_tasks()`)" — A.7:487-497 says
  conn/ntp/sysfunct loggers set up in the pre-task boot batch; which modules set up where is stated two
  ways. (low) · related: CORE.S03 · [H12]
- **DOC.N153** DRIFT · `SPECIFICATION.md:1841-1843` — "re-run against the real FM25xx" — Chip family
  name (FM25xx, Cypress) vs MB85RS64V/MB85RS2MTA (Fujitsu) used everywhere else. (low) · related: HW.T07
  · [H12]

## SPECIFICATION.md Part C.7.1 (Running errno/wrnno table, 1893-1941)

- **DOC.N154** MIRROR · `SPECIFICATION.md:1904-1906` — "a renumbering rides a change that already needs
  deploying, updating this table and its tests with it" — Table ↔ code ↔ tests three-way mirror. · [H12]
- **DOC.N155** DRIFT · `SPECIFICATION.md:1940` — "(owner decision, 2026-09-18, )" — Empty trailing
  citation inside the parenthesis — a reference was dropped. (low) · [H12]

## SPECIFICATION.md Part C.9.1 (Read-trigger timer stagger, 2211-2298)

- **DOC.N156** DRIFT · `SPECIFICATION.md:2226, 2230-2231, 2236` — "(this file)" / "three paragraphs up
  in Part A.7's boot-latency note" / "(WP6, this Part's own text above the timer stagger)" — Relative
  references copied from elsewhere; the boot batch lives in A.7, not Part C. (low) · [H12]

## SPECIFICATION.md Part C.11 / C.11.1 (Design decisions; conformance probe, 2310-2353)

- **DOC.N157** DRIFT · `SPECIFICATION.md:2321-2322, 2326` — "SGP40's VOC-algorithm backup is the only,
  and largest, current example" / "same shape as the existing three" — Stale counts (five chip fakes
  exist: scd30, sgp40, bmp3xx, isl29125, fram). · covered-by: DOC.S08 · [H12]
- **DOC.N158** SETTLED · `SPECIFICATION.md:2351-2353` — "Chip-specific facts go to Part M, not here." —
  Doc-placement rule. · [H12]

## SPECIFICATION.md Part C.14 / C.14.1 (Instance naming, 2380-2428)

- **DOC.N159** DRIFT · `SPECIFICATION.md:2382-2384` — "Session 1 of the device-genericization initiative
  ... (Session 3 on) ... as of Session 6" — Undefined "Session N" labels. (low) · related: DOC.S16 ·
  [H12]

## SPECIFICATION.md Part C.14.2 (The `_WIRING` convention, 2430-2532)

- **DOC.N160** DRIFT · `SPECIFICATION.md:2444-1519 vs 2443-2449 (agent cited SPECIFICATION.md:1517-1519 vs 2443-2449)`
  — "`_WIRING: \"WiringSchema\" = ((toml_field_name, required_driver_class),)`" vs "A comment, never a
  real Python value ... It was a real `_WIRING` tuple until 2026-09-10" — C.2 still documents `_WIRING`
  as a 2-element Python tuple; C.14.2 says it is a 5-field `# @wiring` comment. · [H12] ⟨re-anchored:
  quote found at line 2444⟩
- **DOC.N161** DRIFT · `SPECIFICATION.md:2469` — "This reuses the existing comment-tag family
  (`@requires`, and the planned `@web`)" — `@web` is implemented (CLAUDE.md lists it as live buildgen
  input). · related: GEN.S14 · [H12]
- **DOC.N162** DRIFT · `SPECIFICATION.md:2493-2499` — "`asy_notification_service.py` imports
  `NeopixelDriver` from `asy_neopixel_driver.py` at module level ... every `fram_target`-wirable driver
  similarly imports `AsyFramManager`" — No `NeopixelDriver` import exists; `AsyFramManager` imports are
  TYPE_CHECKING-only (e.g. `src/asy_notification_service.py:29`, `src/asy_sgp40_driver.py:34`). · [H12]
- **DOC.N163** DRIFT · `SPECIFICATION.md:2510-2514` — "plus two fixed mandatory-infra edges and one
  conditional one (`sysfunct` needs its own `device.wiring.fram_target` instance, if set)" — A.7:390-392
  says conn/ntp/sysfunct each get a conditional edge onto `fram`. (low) · [H12]

## SPECIFICATION.md Part D (src/ Production-Quality Checklist, 2576-2728)

- **DOC.N164** DRIFT · `SPECIFICATION.md:2618` — "Units run years without a reboot" — Same
  lifetime-claim tension as A.2:125 vs CLAUDE.md "months". (low) · [H12]
- **DOC.N165** INVAR · `SPECIFICATION.md:2684-2686` — "Per-function explanations are `#` comments, never
  docstrings mixed into an individual function." — Holds today (0 function docstrings in `src/`); not
  mechanically gated. · [H12]

## SPECIFICATION.md Part E.3 / E.3.1 (Running; heap and timeouts, 2828-2921)

- **DOC.N166** DRIFT · `SPECIFICATION.md:2918` — "validated once in `scripts/test.sh` rather than 85
  times" — Stale file count. · covered-by: DOC.S08 · [H12]

## SPECIFICATION.md Part E.5 / E.5.1-E.5.3 (Coverage, 2951-3088)

- **DOC.N167** DRIFT · `SPECIFICATION.md:2966-2967` — "(Session 8's closing-consistency-pass PR split it
  out of `unit-tests` proper)" — Undefined "Session 8" label. (low) · related: DOC.S16 · [H12]
- **DOC.N168** DRIFT · `SPECIFICATION.md:3062-3063` — "HEAP_FRAGMENTATION_MEASUREMENTS.md §M3.7 (archive
  §1.2 item 7 and §3A)" — Archive § citations resolve only in git history. · covered-by: DOC.S04 · [H12]
- **DOC.N169** DRIFT · `SPECIFICATION.md:3071-3072` — "(`tests/test_uart_comm_hazard.py`, 84/85) on a
  tree whose (e) and (f) stages were both 85/85" — Stale file count. · covered-by: DOC.S08 · [H12]

## SPECIFICATION.md Part E.7 (Twin soak wall clock measures GC timing, 3229-3269)

- **DOC.N170** DRIFT · `SPECIFICATION.md:3235` — "where `gc` collections land on the Unix port's 8 MB
  heap" — E.3.1 says the test heap is 16M now; the 8 MB figure is from the retired run_dev_integration
  measurement. (low) · [H12]

## SPECIFICATION.md Part E.8 (Measurement traps, 3271-3362)

- **DOC.N171** DRIFT · `SPECIFICATION.md:3344-3345` — "the same standard I3.4's revert-and-confirm pass
  applies to fixes" — "I3.4" ID resolves to no SPEC Part (Part I uses `I.n`). (low) · related: DOC.T02 ·
  [H12]

## SPECIFICATION.md Part F.1 — Core platform facts

- **DOC.N172** DRIFT · `SPECIFICATION.md:3518-3519` — "every real use in `src/` is a short bounded
  timeout well inside that window" — Contradicted by stored-ticks sites the plan lists (ISL29125, UART
  hold-off). · covered-by: DOC.S23 · [H13]
- **DOC.N173** MIRROR · `SPECIFICATION.md:3583-3588` — "Always check current MicroPython/Microdot
  documentation ... Repeat every time `versions.toml`'s ref moves" — Duplicates CLAUDE.md "Platform
  target" standing practices (two homes for one rule) (low). · related: DOC.T06 · [H13]

## SPECIFICATION.md Part F.2 — Blocking calls / timeout-wrapping

- **DOC.N174** DRIFT · `SPECIFICATION.md:3632-3635 vs CLAUDE.md "Hard rules" (CYW43 bullet)` — "the
  older, stronger claim — \"a device whose API is unreachable structurally cannot have a flash write in
  flight\" — is no longer exactly true" — CLAUDE.md still states "structurally cannot have a write in
  flight" as confirmed. · related: DOC.T10 · [H13]

## SPECIFICATION.md Part F.5 — MicroPython 1.29 delta (intro)

- **DOC.N175** DRIFT · `SPECIFICATION.md:3664 vs 3852-4049` — "## F.5 MicroPython 1.29 delta (audited
  2026-09-10 ...)" — F.5.7-F.5.9 are standing UART runtime facts CLAUDE.md hard rules depend on, filed
  under a version-delta heading. · covered-by: DOC.S02 · [H13]

## SPECIFICATION.md Part F.5.2 — rp2 SPI RX-overrun EIO

- **DOC.N176** DRIFT · `SPECIFICATION.md:3735-3736` — "an earlier draft of this section that said it did
  was wrong" — Historic-path narrative in a current-state doc (low). · related: DOC.T05 · [H13]

## SPECIFICATION.md Part F.5.3 — Free wins in the 1.29 build

- **DOC.N177** DRIFT · `SPECIFICATION.md:3774` — "`HEAP_FRAGMENTATION_MEASUREMENTS.md` §M2.5 has the
  method (archive §7G the derivation)" — "archive §" citation resolves only against the git archive
  commit. · covered-by: DOC.S04 · [H13]

## SPECIFICATION.md Part F.5.6 — Smaller 1.29 facts / non-events

- **DOC.N178** DRIFT · `SPECIFICATION.md:3832` — "This project's 21 `const()`-using files are all
  unannotated." — `grep -lE '=\s*const\(' src/*.py` finds 25 files at 2a88cc8 (count stale, low; scope
  of "project" unstated). · related: DOC.T08 · [H13]

## SPECIFICATION.md Part F.6 — SIGINT during gc_collect() wedges the Unix-port heap

- **DOC.N179** DRIFT · `SPECIFICATION.md:4084-4085` — "in violation of this Part's own stated rule
  (\"call it first ... before `flush_fram()`/`flush_scd30()`\")" — The quoted rule text no longer
  appears anywhere in F.6 (only the paraphrase in `digital_twin/unix_port_gc_unwedge.py:2`) (low). ·
  related: DOC.T02 · [H13]
- **DOC.N180** DRIFT · `SPECIFICATION.md:4087-4089 vs 4107-4116` — "gated on `MICROPY_ASYNC_KBD_INTR`,
  which the `standard` build variant used here has enabled" — Present-tense statement superseded by the
  amendment (override forces it to 0) in the same Part (history narrative). · related: DOC.T05 · [H13]

## SPECIFICATION.md Part H.5 — Definitions JSON schema

- **DOC.N181** DRIFT · `SPECIFICATION.md:4393-4396` — "An earlier version of this paragraph said ...
  (resolved 2026-09-18 by reading the one consumer, `js/render.js`)" — Historic narrative in a
  current-state doc (low). · related: DOC.T05 · [H13]
- **DOC.N182** DRIFT · `SPECIFICATION.md:4399-4401` — "nearly identical field content (same three
  drivers); only `device.id`/`displayName` and I2C bus pairing differ" — `devices/dev.toml` wires
  ISL29125 too (`:103`) and `html/definitions/dev.json` carries ISL fields, so dev ≠ wozi's three
  drivers. · related: WEB.T05 · [H13]
- **DOC.N183** DRIFT · `SPECIFICATION.md:4402-4408` — "`wozi`/`dev` keep their existing hand-written
  files unchanged (`tests_js/` reads those exact files as fixtures)" — Contradicts K.4 "never
  hand-maintained" / K.8 "regenerates automatically". · covered-by: DOC.S03 · [H13]

## SPECIFICATION.md Part H.5.1 — Definitions-file autogeneration

- **DOC.N184** DRIFT · `SPECIFICATION.md:4410` — "## H.5.1 Definitions-file autogeneration" — Heading
  level `##` for a subsection. · covered-by: DOC.S01 · [H13]

## SPECIFICATION.md Part H.7 — Digital twin integration / connection ceiling

- **DOC.N185** DRIFT · `SPECIFICATION.md:4530, 4664` — "### The connection ceiling ..." / "###
  Cross-browser coverage" — Unnumbered subsections, cited elsewhere as "H.7". · covered-by: DOC.S01 ·
  [H13]

## SPECIFICATION.md Part I.3 — Bounded response assembly

- **DOC.N186** DRIFT · `SPECIFICATION.md:4960-4962` — "since an 8MB Unix-port heap trivially absorbs a
  payload this small" — `scripts/test.sh:369` now runs `-X heapsize=16M` (CLAUDE.md: 8M → 32M → 16M)
  (low). · related: DOC.T08 · [H13]

## SPECIFICATION.md Part I.4 — (f), (f.1), (g)

- **DOC.N187** DRIFT · `SPECIFICATION.md:5115-5116` — "measure B's silicon confirmation is a different
  metric (archive §7F)" — Undefined label "measure B"; archive-only citation. · covered-by: DOC.S16 ·
  [H13]

## SPECIFICATION.md Part I.5 — Real-hardware confirmation

- **DOC.N188** DRIFT · `SPECIFICATION.md:5135-5137` — "The piece cap's 2026-09-08 headroom figure (~48x)
  is withdrawn" — Withdrawn-figure narrative (low). · related: DOC.T05 · [H13]

## SPECIFICATION.md Part I.6 — Request-body cap (sits inside Part J)

- **DOC.N189** DRIFT · `SPECIFICATION.md:5165` — "## I.6 The request-body cap, and why both of
  Microdot's limits must move together" — Part I subsection placed after Part J's intro. · covered-by:
  DOC.S01 · [H13]
- **DOC.N190** DRIFT · `SPECIFICATION.md:5184-5186, 5194-5195` — "`max_connections` is 4, so up to
  **four** such buffers ... takes the four-connection worst case to 4 x 2,048 = 8,192 B" —
  `max_connections` is now 6 (H.7) → 12,288 B. · covered-by: REST.S11 · [H13]
- **DOC.N191** DRIFT · `SPECIFICATION.md:5236-5255` — "**the resets are a property of concurrency
  against `max_connections = 4`** ... 3 free slots, 4 clients, **1 refusal = the measured 25 %**" — W5
  analysis and its reset-rate curve were taken at the old ceiling of 4; not restated for 6. · related:
  REST.S11, PERF.T02 · [H13]
- **DOC.N192** DRIFT · `SPECIFICATION.md:5283-5284` — "(owner's decision; `REAL_HARDWARE_TEST_QUEUE.md`
  §2A F11 has the account)" — Deleted queue row F11 still cited. · covered-by: DOC.S06 · [H13]

## SPECIFICATION.md Part J.1 — Scope and two-implementation contract

- **DOC.N193** TODO · `SPECIFICATION.md:5328-5329` — "a temporary file, deleted once the C side is
  reconciled" — Deletion trigger unreachable while reconciliation is out of scope. · covered-by: DOC.S14
  · [H13]

## SPECIFICATION.md Part J.7 — Loopback testing model

- **DOC.N194** DRIFT · `SPECIFICATION.md:5555-5556 vs 5561-5563` — "`digital_twin/machine.py` (twin
  tier, which has no `UART` at all today)" — Contradicted four lines later ("Both models exist ...
  `digital_twin/machine.py`'s") and by `digital_twin/machine.py:481-488` (`UARTLink`). · related:
  DOC.T10 · [H13]

## SPECIFICATION.md Part J.9 — Module contract

- **DOC.N195** DRIFT · `SPECIFICATION.md:5670-5671` — "C.6's `make_dict()` repr-parsing landmine does
  not apply" — The landmine C.6 describes no longer exists in code. · covered-by: DOC.S09 · [H13]

## SPECIFICATION.md Part K (intro) and K.1 — Before writing code

- **DOC.N196** INVAR · `SPECIFICATION.md:5691-5695` — "Use it as a literal checklist ... Where a step
  doesn't apply ... say so explicitly rather than silently skipping it" — Process rule for every
  promotion; review-only. · related: TEST.T06 · [H13]

## SPECIFICATION.md Part K.4 — @web tags

- **DOC.N197** DRIFT · `SPECIFICATION.md:5785-5786` — "`html/definitions/<device>.json` is generated at
  build time from every tagged `src/` file (Part H.5.1); it is never hand-maintained" — wozi/dev
  definitions are hand-written (H.5). · covered-by: DOC.S03 · [H13]

## SPECIFICATION.md Part K.5 — Digital twin

- **DOC.N198** DRIFT · `SPECIFICATION.md:5803-5804` — "wired into `digital_twin/machine.py`'s
  `_build_i2c_chip()`/`_build_spi_chip()` dispatch (matched by `driver` string" — `_build_spi_chip()`
  does not exist (twin has `_wire_spi_device()`, FRAM only). · covered-by: DOC.S22 · [H13]

## SPECIFICATION.md Part K.6 — Tests, every tier

- **DOC.N199** DRIFT · `SPECIFICATION.md:5965-5868 vs 5966-5967 (agent cited SPECIFICATION.md:5867-5868 vs 5966-5967)`
  — "**Cross-sensor hazard coverage is automatic ... no longer hand-paired per driver.**" vs
  "(auto-generated if that capability has landed by the time you read this — check; hand-paired
  otherwise)" — K.11 still hedges on a capability K.6 says has landed; CLAUDE.md's four-tier list still
  names `test_bus_hazard_multi_device.py` as the mock tier (low). · related: DOC.T10 · [H13]
  ⟨re-anchored: quote found at line 5965⟩

## SPECIFICATION.md Part K.8 — Regenerate and spot-check

- **DOC.N200** DRIFT · `SPECIFICATION.md:5899` — "`html/definitions/<device>.json` regenerates from
  K.4's tags automatically" — Not true for hand-written wozi/dev. · covered-by: DOC.S03 · [H13]

## SPECIFICATION.md Part K.9 — Documentation

- **DOC.N201** INVAR · `SPECIFICATION.md:5907-5923` — "a new `M.<n>` section for any real,
  datasheet-derived findings ... A `C.7.1` errno/wrnno table row ... `DEVICE_REFERENCE.md` —
  end-user-facing notes only ... BACKLOG.md — only for a genuinely still-open question" — Documentation
  obligations per promotion; review-only. · related: DOC.T06 · [H13]

## SPECIFICATION.md Part K.10-K.11 — Verification and certification

- **DOC.N202** INVAR · `SPECIFICATION.md:5944-5981` — "Check off per promotion; note explicitly (not
  silently) anywhere a step didn't apply" — Certification checklist; no record of past check-offs is
  required anywhere. · [H13]

## SPECIFICATION.md Part L.1 — Device variants and acceptance criteria

- **DOC.N203** DRIFT · `SPECIFICATION.md:6006-6009 vs 5741-5772` — "**A new driver needs exactly one
  association** ... True of every driver in `src/` today." — K.3 lists `buildspec.py` rows, a
  `_build_args_<name>()` handler and a `_SENSOR_DRIVERS` entry for every new driver. · related: GEN.T06
  · [H13]

## SPECIFICATION.md Part L.2 — Core design decisions

- **DOC.N204** DRIFT · `SPECIFICATION.md:6083-6086` — "Tests are generic bodies driven by each device's
  TOML and generated module, never hand-written or generated per-variant test files." — Six hand-written
  per-device wrappers exist (`tests/test_sensortask_<device>.py`, 11 lines each) (low). · related:
  CI.T07 · [H13]

## SPECIFICATION.md Part L.3 — Device TOML schema

- **DOC.N205** DRIFT · `SPECIFICATION.md:6223 vs 4234-4236` — "**`_WIRING`'s shape** (a `# @wiring`
  comment tag, not a Python tuple — L.6)" — G.2 still describes "a `_WIRING: \"WiringSchema\"` tuple
  next to a driver's `_VAL_*` schema tuples"; `src/` has only `# @wiring` tags (e.g.
  `src/asy_bmp3xx_driver.py:114`). · related: DOC.T10 · [H13]

## SPECIFICATION.md Part L.5 — Build/generator script quality bar

- **DOC.N206** DRIFT · `SPECIFICATION.md:6371` — "trailing inline on a module-level statement, last line
  with no trailing newline, beside `_WIRING`" — `_WIRING` is no longer a Python tuple in `src/` (L.3)
  (low). · related: DOC.T16 · [H13]

## SPECIFICATION.md Part L.6.4 — Comment-tag family

- **DOC.N207** DRIFT · `SPECIFICATION.md:6495-6498` — "`asy_bmp3xx_driver.py`'s `_LIMITS` ... — the only
  driver with a real, datasheet-documented `_LIMITS` constraint today" —
  `src/asy_isl29125_driver.py:194` also carries `# @limits trigger_sec 1..3600`. · covered-by: DOC.S08 ·
  [H13]

## SPECIFICATION.md Part L.7 — Product versioning

- **DOC.N208** DRIFT · `SPECIFICATION.md:6560-6561 vs 4265-4266` — "Neither version nor the build date
  is rendered in the UI" — Contradicts H.1's "every REST endpoint's functionality must be reachable
  somewhere in the GUI". · covered-by: WEB.S20 · [H13]

## SPECIFICATION.md Part M (intro) and M.1 — ISL29125

- **DOC.N209** LIMIT · `SPECIFICATION.md:6576-6577` — "Only the ISL29125 has needed one so far." — Other
  chips (SCD30, SGP40, BMP3xx, FRAM) have no Part M entry (low). · related: TEST.S20 · [H13]

## SPECIFICATION.md Part M.1.1 — Settled requirements (owner's list)

- **DOC.N210** INVAR · `SPECIFICATION.md:6588-6589` — "the numbering is load-bearing and must not be
  re-flowed" — Requirement numbers are cited from code/tests. · related: DOC.T02 · [H13]

## CLAUDE.md

- **DOC.N211** INVAR · `CLAUDE.md:3-6` — "that section is the single place the list is kept, not
  duplicated here" — README "Further reading" is declared the one complete doc map. Convention only; the
  map omits `update_and_install.txt` and three licence files (see README:643-645 item). · related:
  DOC.S15 · [H14]
- **DOC.N212** INVAR · `CLAUDE.md:10-13` — "read them first for any hardware-interaction claim, and say
  so explicitly if one you need isn't there" — Datasheet-first rule, convention only. `datasheets/`
  holds bmp3xx, fram, isl29125, pico w, scd30 and sgp40; BMP390, RP2040, WS2812 and QSPI flash are
  missing. · related: SENS.S20, ENV.T04 · [H14]
- **DOC.N213** SETTLED · `CLAUDE.md:53-67` — "`improved-quality/` (the refactor's WIP staging directory)
  has been fully retired and deleted." — `src/sensortask_wozi.py` is retired too; every device's
  `sensortask_<device>.py` is buildgen-generated. The ConfigManager/LockedValue fix remains the
  precedent for severity-justified exceptions to hands-off rules. · [H14]
- **DOC.N214** SETTLED · `CLAUDE.md:88-91` — "If the scan surfaces a discrepancy ... do not silently fix
  it." — Flag-don't-fix rule for cross-file consistency (same as D.1 for formulas). · related: DOC.T14 ·
  [H14]
- **DOC.N215** DRIFT · `CLAUDE.md:110-111` — "Bringing the *deployed* tree forward is a reflash-campaign
  decision, not a drive-by edit (BACKLOG.md)" — BACKLOG.md has no Microdot entry (0 hits). Only item 3
  (BACKLOG.md:183-185) mentions a reflash campaign, for the MicroPython version (low). · related:
  DOC.T02 · [H14]
- **DOC.N216** SETTLED · `CLAUDE.md:156-158` — "`dev` config is a bench rig only — its quirks ... are
  explicitly out of scope. Don't fix them as if they were bugs." — | area: PAR | related: PAR.S14 ·
  [H14]
- **DOC.N217** DRIFT · `CLAUDE.md:156-157` — "LED/Neopixel REST routes referencing an object that's
  never instantiated" — The example describes legacy dev. The refactored devices/dev.toml:121-126 does
  instantiate `neopixel`, so it no longer applies to the `src/` dev (low). · related: PAR.S14 · [H14]
- **DOC.N218** DRIFT · `CLAUDE.md:511-513` — "has no lint/type config yet; extending scope there is a
  separate future decision, not assumed by this setup" — Contradicts CLAUDE.md:170-177 ("forever ...
  Don't propose closing any of these gaps — the gap is the decision"). README.md:117 says the same
  "isn't covered yet". · related: DOC.S21 · [H14]
- **DOC.N219** SETTLED · `CLAUDE.md:178-183` — "The rule is \"never test the old `python/`/`modules/`
  code\", not \"defer all tests\"" — | area: TEST | - · [H14]
- **DOC.N220** SETTLED · `CLAUDE.md:204-206` — "Don't wrap every `asyncio` primitive call in
  `try`/`except` against a theoretical internal `MemoryError` as a blanket policy" — | area: MEM |
  related: DOC.T14 · [H14]
- **DOC.N221** SETTLED · `CLAUDE.md:207-209` — "Adafruit-derived driver code is fair game to
  restructure/rewrite (keeping attribution)" — | area: LIC | related: LIC.T01 · [H14]
- **DOC.N222** DRIFT · `CLAUDE.md:240-245` — "in `tests/test_bus_hazard_multi_device.py` (mock), ..." —
  The tier file list omits `tests/test_bus_hazard_generated.py`, the TOML-driven mock-tier generator
  (low). · related: TEST.S01 · [H14]
- **DOC.N223** ASSUME · `CLAUDE.md:350` — "(86/86 on 2026-09-24)" — Dated count; there are 87
  tests/test_*.py at 2a88cc8. · covered-by: DOC.S08 · [H14]
- **DOC.N224** DRIFT · `CLAUDE.md:367-376` — "the FRAM-backed subset:
  SGP40/BMP3XX/SCD30/SYSTEM/NEOPIXEL/NOTIFY/WIFI/DNSSRV/NTP/WEBSERVER" — Omits ISL29125, which
  devices/dev.toml:109-110 wires to FRAM. The "implicit-FRAM-wiring rule" is never stated as a rule. ·
  covered-by: DOC.S12 · [H14]
- **DOC.N225** SETTLED · `CLAUDE.md:398-400` — "The refactor should end up with the *same top-level
  features*, just more consistent/stable — not a feature change." — | area: PAR | covered-by: PAR.T01 ·
  [H14]
- **DOC.N226** INVAR · `CLAUDE.md:401-403` — "update the doc in the same session rather than silently
  working around the discrepancy" — Stale-doc rule; conflicts with a findings-first audit (plan 2.3,
  PQ1). · related: DOC.T10 · [H14]
- **DOC.N227** INVAR · `CLAUDE.md:404-411` — "Documentation contains current state, future targets, and
  rules/agreements — not the historic path that got there." — Convention only. CLAUDE.md itself carries
  incident narratives (e.g. :274-283, :379-385, :613-708). · covered-by: DOC.T05 (related DOC.T07) ·
  [H14]
- **DOC.N228** INVAR · `CLAUDE.md:412-425` — "capped at 3 lines, prefer fewer ... The same 3-line cap
  applies to every inline comment block" — Owner, 2026-09-14, re-confirmed 2026-09-18. Enforced for
  Python and shell in eight scopes by tests_scripts/test_comment_block_cap.py:14. JS, CSS and config
  files are review-only. One-line 400-700-character docstrings pass because E501 is ignored. ·
  covered-by: CI.T08 (related TEST.S22, WEB.S19, CI.S10) · [H14]
- **DOC.N229** SETTLED · `CLAUDE.md:425-432` — "Machine-read tag lines are data, not commentary, and are
  exempt" — Exempt: buildgen tags, JSDoc `@typedef`/`@param`/`@returns`, and PEP 723 blocks (also exempt
  in test_comment_block_cap.py:18-19). · [H14]
- **DOC.N230** DRIFT · `CLAUDE.md:431-432` — "the `# /// script` … `# ///` block four `uv run` scripts
  carry" — Five carry it: scripts/_render_coverage.py, scripts/_digital_twin_ci_suite.py,
  scripts/_generate_sensortask_modules.py, scripts/build_firmware.py, toolchain/setup_toolchain.py. ·
  [H14]
- **DOC.N231** ASSUME · `CLAUDE.md:430` — "`js/definitions.js`'s ~37-line `@typedef` run" — Approximate
  count; the block is js/definitions.js:6-39 (34 lines) (low). · [H14]
- **DOC.N232** ASSUME · `CLAUDE.md:434-436` — "every scope measures zero over-cap blocks ... since
  2026-09-22 `scripts/`'s shell, and since 2026-09-24 the config files too" — Dated claim. For config
  files it is review-only, and CI.S10 lists over-cap blocks outside the swept list. · related: CI.S10 ·
  [H14]
- **DOC.N233** ASSUME · `CLAUDE.md:436-437` — "a naive line count measures this tree anywhere from 0 to
  458" — Counted claim, repeated in test_comment_block_cap.py:3. · [H14]
- **DOC.N234** INVAR · `CLAUDE.md:444-446` — "Prefer flagging genuinely ambiguous/architecturally
  significant decisions to the project owner over guessing" — Convention only. · [H14]
- **DOC.N235** INVAR · `CLAUDE.md:449-464` — "Step-session workflow, standing practice for any
  substantial unit of refactor/audit work" — Scope, then up to 10 questions, then TDD, implementation
  and coverage, then stop and report. Convention only. · related: DOC.T14 · [H14]
- **DOC.N236** SETTLED · `CLAUDE.md:532-539` — "Unit tests run under a real MicroPython Unix-port
  interpreter, not pytest/CPython" — | area: TEST | - · [H14]
- **DOC.N237** SETTLED · `CLAUDE.md:558-560` — "no threshold is enforced anywhere, by design (confirmed
  directly, not a placeholder for a future gate)" — | area: CI | related: CI.T11 · [H14]
- **DOC.N238** LIMIT · `CLAUDE.md:571-575` — "the measured 4-5x allocation inflation ... any allocation
  figure taken under `--coverage` is inflated" — | area: MEM | - · [H14]
- **DOC.N239** ASSUME · `CLAUDE.md:576-578` — "HEAP_FRAGMENTATION_MEASUREMENTS.md archive §11 item 0 ...
  (`test_sensortask_wozi.py` 24.6s → 9.3s)" — Single timing. The archive citation resolves only against
  the git archive. · related: DOC.S04 · [H14]
- **DOC.N240** PLATFORM · `CLAUDE.md:633-634` — "MicroPython's asyncio has no parent/child task
  tracking" — | area: PLAT | related: PLAT.T01 · [H14]
- **DOC.N241** DRIFT · `CLAUDE.md:646-647` — "Surfaced by the `system_service.py` `_timer_sequencer()`
  Timer-GC fix above" — No such fix appears above. · covered-by: DOC.S07 · [H14]
- **DOC.N242** SETTLED · `CLAUDE.md:663-664` — "Don't re-diagnose a test file that segfaults partway
  through with no `N/N passed` line as a memory bug" — | area: TEST | related: DOC.T14 · [H14]
- **DOC.N243** SETTLED · `CLAUDE.md:674-675` — "Don't re-diagnose a \"heap is locked\" `MemoryError` at
  twin shutdown as a project memory bug." — | area: TWIN | related: DOC.T14 · [H14]
- **DOC.N244** DRIFT · `CLAUDE.md:724-726` — "nine failures across
  `test_digital_twin_webserver_concurrency.py`" — That file is now split per device
  (tests/test_digital_twin_webserver_concurrency_<device>.py). · covered-by: DOC.S08 · [H14]
- **DOC.N245** ASSUME · `CLAUDE.md:798-802` — "a lock reading `ruff specifier = \"==0.15.21\"` next to
  `ruff version = \"0.16.6\"` ... (it surfaced 174 `CPY001` findings)" — Dated incident (2026-09-10).
  The pin is now ruff==0.16.6 (pyproject.toml:22) with CPY001 ignored (:192-194), so the example reads
  as history (low). · related: DOC.T05 · [H14]
- **DOC.N246** SETTLED · `CLAUDE.md:855-857` — "`improved-quality/microdot.py` no longer exists — it was
  a confirmed *unintentional* fork" — | area: REST | - · [H14]
- **DOC.N247** SETTLED · `CLAUDE.md:861-868` — "Owner decision, 2026-09-18: this is a periodic check the
  project owner runs manually, not a gate that blocks a session's push." — | area: TOOL | - · [H14]
- **DOC.N248** DRIFT · `CLAUDE.md:936-953` — "libcap2-bin is missing for the same reason" — The
  libcap2-bin paragraph appears twice. · covered-by: DOC.S11 · [H14]
- **DOC.N249** DRIFT · `CLAUDE.md:893-894` — "on by default on every real Ubuntu ISO - see \"Platform
  target\" above" — "Platform target" no longer carries the `universe` fact. · covered-by: DOC.S07 ·
  [H14]
- **DOC.N250** DRIFT · `CLAUDE.md:1026-1028` — "that recipe only exercises
  `scripts/lint.sh`/`scripts/typecheck.sh`, never the toolchain installer" — The recipe also runs
  scripts/test.sh, which builds the Unix port via setup_toolchain (:968-971). · covered-by: DOC.S11 ·
  [H14]
- **DOC.N251** SETTLED · `CLAUDE.md:1043-1046` — "The project owner has explicitly authorized creating
  pull requests proactively, at any time, without asking first" — | area: DOC | - · [H14]
- **DOC.N252** DRIFT · `CLAUDE.md:213, 370-375, 702` — "(WP6, owner-established requirement)" / "under
  WP1's implicit-FRAM-wiring rule" / "WP1+WP2" — WP1, WP2, WP3 and WP6 are undefined labels. ·
  covered-by: DOC.S16 · [H14]
- **DOC.N253** LIMIT · `CLAUDE.md (whole file)` — 1067 lines, auto-loaded — Mixes rules, facts and
  incident narratives ("Known … fixed" bullets, chroot recipe) in the auto-loaded budget. · covered-by:
  DOC.T07 · [H14]

## README.md

- **DOC.N254** DRIFT · `README.md:10-20` — "**5 units are currently deployed**: `arzi`, `wozi`, and
  three physically-identical-to-arzi units sharing the `neu` build" — The first screen describes only
  the legacy builds (`html_raw`, BMP388, neu×3); the six devices/*.toml and the neu →
  klkizi/grkizi/schlafzi mapping are missing. · covered-by: DOC.T13 · [H14]
- **DOC.N255** DRIFT · `README.md:26-29` — "This section used to hold all of that content directly; it's
  now a pointer, as part of a first-pass doc-scatter cleanup" — History narrative against the
  current-state rule (low). · related: DOC.T05 · [H14]
- **DOC.N256** SETTLED · `README.md:106-108` — "only flagged, never auto-repaired, since fixing it live
  can cycle the interface the session itself depends on" — | area: TOOL | related: TOOL.T03 · [H14]
- **DOC.N257** DRIFT · `README.md:115-117` — "the pre-refactor codebase — `python/`, `modules/` — isn't
  covered yet" — "yet" contradicts CLAUDE.md:170-177 (legacy is reference-only forever; the gap is the
  decision). · related: DOC.S21 · [H14]
- **DOC.N258** DRIFT · `README.md:176-178 vs 192` — "its coverage number advisory, its test result
  gating" vs "non-gating, never fails the build" — Coverage gating is stated both ways. · covered-by:
  DOC.S11 · [H14]
- **DOC.N259** INVAR · `README.md:210-211` — "A Node already on `PATH` that matches the pin is used
  as-is and never overridden" — | area: TOOL | related: TOOL.T13 · [H14]
- **DOC.N260** DRIFT · `README.md:278-280` — "`<device>` (positional, required) must match an
  `html/definitions/<device>.json` file (`wozi` and `dev` today" — build_firmware needs
  `devices/<device>.toml`; CI builds all six. · covered-by: DOC.S18 · [H14]
- **DOC.N261** DRIFT · `README.md:352-356` — "is documented as its own single source of truth in
  `dev_legacy/README.md`" — Its "single source of truth" status conflicts with the queue and handover;
  parts of it are stale. · covered-by: DOC.S15 (related HW.S20) · [H14]
- **DOC.N262** INVAR · `README.md:643-645` — "When a new doc is added, add it here too instead of
  letting the map go stale again." — Convention only. The map omits `update_and_install.txt`,
  `ext/LICENSE-microdot`, `ext/freezefs/LICENSE` and `src/LICENSE-captive_dns`. · covered-by: DOC.S15
  (licence files: -) · [H14]
- **DOC.N263** DRIFT · `README.md:649-654` — "pre-push verification ... (see its front matter for the
  tradeoff this creates" — The chroot check is no longer pre-push (owner, 2026-09-18).
  SPECIFICATION.md's front matter (:1-10) states no such tradeoff. · covered-by: DOC.S07, DOC.S08 ·
  [H14]
- **DOC.N264** DRIFT · `README.md:655-657` — "Resolved items move into this file or CLAUDE.md instead of
  staying there" — Conflicts with practice (migration mostly goes to SPECIFICATION). · covered-by:
  DOC.S10 · [H14]
- **DOC.N265** LIMIT · `README.md:658-663` — "the investigation's full measurement record is archived in
  git (its opening paragraph says where) and is what an \"archive §…\" citation elsewhere names" —
  Archive citations resolve only in commit 12640c2. · covered-by: DOC.S04 · [H14]
- **DOC.N266** INVAR · `README.md:719-721` — "A handover file ... Never treat one as a durable
  reference" — | area: HW | related: HW.T10 · [H14]
- **DOC.N267** DRIFT · `README.md:725-727` — "notes for configuring/operating a deployed unit (Neopixel
  LED signal legend, SGP40 FRAM backup config semantics)" — Omits the ISL29125 section
  (DEVICE_REFERENCE.md:39-101) (low). · [H14]
- **DOC.N268** OPENQ · `README.md:742-744` — "Folding it into `SPECIFICATION.md`, the way
  `src/README.md`/`tests/README.md` were, is an open option." — Placement of digital_twin/README.md is
  undecided. · related: DOC.T06 · [H14]
- **DOC.N269** LIMIT · `README.md:764-767` — "a historical, frozen-in-time snapshot ... from 2026-08-27
  (back when it still ran 1.24.1) ... not itself reviewed, promoted, or covered by lint/type/test
  config" — | area: HW | related: PAR.T08 · [H14]
- **DOC.N270** DRIFT · `README.md:780-783` — "the two still-genuinely-open items (a real, long-duration
  memory-soak run not yet executed; two bench-rig capabilities" — The BACKLOG item 8 status has moved on
  (the GPIO fault harness is SETTLED as not provisioned). · covered-by: DOC.S08 · [H14]
- **DOC.N271** DRIFT · `README.md:769-772` — "all now deleted (2026-09-04) once real-hardware execution
  was genuinely complete and verified" — Provenance narrative against the current-state rule (low). ·
  related: DOC.T05 · [H14]
- **DOC.N272** DRIFT · `README.md:789-791` — "See `SPECIFICATION.md`'s own front matter for the full
  provenance" — The front matter has no provenance text. · covered-by: DOC.S07 · [H14]

## DEVICE_REFERENCE.md

- **DOC.N273** DRIFT · `DEVICE_REFERENCE.md:3-5` — "End-user notes for configuring/operating a deployed
  unit" — The notes document refactor field names (`FlashBri`, `BackupPeriod`), while fielded units run
  the legacy build (`LedAutoFlashBri`, `SGPBackupPeriod`). · covered-by: DOC.S19 (DOC.T11) · [H14]
- **DOC.N274** INVAR · `DEVICE_REFERENCE.md:4-5` — "Add to this file, don't duplicate it elsewhere, when
  a new user-facing behavior needs explaining." — One-home rule for user-facing behaviour. Convention
  only. · related: DOC.T06 · [H14]
- **DOC.N275** LIMIT · `DEVICE_REFERENCE.md:96-98` — "Measured Gain Ratio staying blank means no usable
  pair was obtained" — | area: SENS | - · [H14]
- **DOC.N276** DRIFT · `DEVICE_REFERENCE.md:100-101` — "`wozi` carries no colour sensor and never will
  (CLAUDE.md)" — CLAUDE.md has no ISL29125 or colour-sensor statement, so the attribution dangles. The
  wiring claim (i2c1, IRQ GPIO6) matches devices/dev.toml:102-107. · related: DOC.T02 · [H14]

## update_and_install.txt

- **DOC.N277** SETTLED · `update_and_install.txt:1-2, 9` — "SUPERSEDED: this manual recipe is now
  automated by `toolchain/setup_toolchain.py`" — Kept "only as the original manual notes for reference".
  It is missing from README's "single complete" doc map. · covered-by: DOC.S15 · [H14]
- **DOC.N278** LIMIT · `update_and_install.txt:11-34` — "(libusb muss installiert sein ...) ... sudo
  make install ... --> build skripte für RPI Firmware funktionieren" — Legacy German notes for the
  legacy `build-*.sh`, reference only. The picotool `sudo make install` still happens in every `setup`.
  · related: TOOL.T09, TOOL.S08 · [H14]

## BACKLOG.md

- **DOC.N279** SETTLED · `BACKLOG.md:15-19` — "The numbered list below has gaps, and its numbers are
  never reused or renumbered." — Numbering contract: cited resolved items stay as closed stubs, uncited
  ones are deleted; a gap means "resolved and removed". · related: DOC.T02 · [H15]
- **DOC.N280** DRIFT · `BACKLOG.md:17 vs :316-318` — "a resolved item whose number is cited stays as a
  short closed stub ... (items 1, 5, 6, 9, 12 today)" — Stub list omits item 29, which calls itself
  "Kept as a stub"; items 2/3/4 are decided but not stubs. · covered-by: DOC.S13 · [H15]
- **DOC.N281** DRIFT · `BACKLOG.md:3-8` — "anything from it worth keeping permanently lives in CLAUDE.md
  ... or README.md" — Stated migration target for resolved items (CLAUDE/README) differs from practice
  (items point into SPECIFICATION.md Parts). · covered-by: DOC.S10 · [H15]
- **DOC.N282** MIRROR · `BACKLOG.md:10-13` — "Anything in here that needs the dev bench is also listed
  in REAL_HARDWARE_TEST_QUEUE.md" — Every bench-needing BACKLOG item must also have a queue row
  (convention, unchecked). · related: HW.T10, DOC.T06 · [H15]
- **DOC.N283** ASSUME · `BACKLOG.md:62-66` — "Re-measured 2026-09-11: 224 in the main src+tests pass and
  115 in the host pass" — Dated counts (224 / 115 / twin "previously 45" not re-measured / 54 unimported
  / explicit `Any` 107 in src, 213 in tests). · covered-by: DOC.S17, ENV.T06 · [H15]
- **DOC.N284** DRIFT · `BACKLOG.md:21 (agent cited BACKLOG.md:72)` — "SETTLED, do not re-raise" (under
  "## Refactor targets not yet done", :21) — A settled entry filed in the not-yet-done section. ·
  covered-by: DOC.S13 · [H15] ⟨re-anchored: quote found at line 21⟩
- **DOC.N285** DRIFT · `BACKLOG.md:93-99` — "(1) dev/build environment setup (genericized
  build-*.sh/toolchain paths)" — "Rough sequencing" still lists `build-*.sh` genericisation, which
  CLAUDE.md's legacy rule forbids forever; items (2)-(3) partly stale. (low) · related: DOC.S21 · [H15]
- **DOC.N286** DRIFT · `BACKLOG.md:145-150 vs REAL_HARDWARE_TEST_QUEUE.md:247` — "Still open: this needs
  a real-hardware re-run" — Queue R9 says the shadow-divergence fix already RAN and passed on silicon
  (archive §7H.6, `ARCH:3610-3612`); only the `Overrange` half is unrun. BACKLOG not updated. · related:
  DOC.T06 · [H15]
- **DOC.N287** DRIFT · `BACKLOG.md:248-249` — "which is REAL_HARDWARE_TEST_QUEUE.md's C7, not this item"
  — Queue row C7 no longer exists. · covered-by: DOC.S06 · [H15]
- **DOC.N288** DRIFT · `BACKLOG.md:255` — "outer_cap_s = 15.0 (asy_webserver_service.py:275, via
  asyncio.wait_for() at :667)" — Stale line refs: default is at `src/asy_webserver_service.py:322`,
  stored `:355`, `wait_for` at `:708` (`:275`/`:667` are unrelated lines). · related: DOC.T16 · [H15]
- **DOC.N289** DRIFT · `BACKLOG.md:393-394` — "the supervisor loop is the only feed site
  (system_service.py's feed_watchdog())" — The generated setup batch also feeds per setup unit. ·
  covered-by: DOC.S20 · [H15]
- **DOC.N290** DRIFT · `BACKLOG.md:669-670` — "whenever one is next scheduled
  (REAL_HARDWARE_TEST_QUEUE.md R10)" — Queue row R10 deleted. · covered-by: DOC.S06 · [H15]
- **DOC.N291** TODO · `BACKLOG.md:797-808` — "held here only until the owner's audit of the whole
  refactor closes" — Unix-port-equivalent requirement fulfilled; this entry's removal trigger is the
  audit itself. · [H15]
- **DOC.N292** DRIFT · `BACKLOG.md:809-813` — "not fully wired end-to-end yet (sensortask-wozi.py itself
  predates the per-sensor-config model — see 'Refactor targets not yet done' above)" —
  `sensortask-wozi.py` is retired (buildgen-generated); no matching entry above; current status of the
  `_DEFAULT_CONFIG`/REST/HTML-form duplication is unclear. · related: GEN.T06 · [H15]
- **DOC.N293** DRIFT · `BACKLOG.md:825-827` — "build-*.sh's hardcoded path/py-include dependency is now
  fixed too (see 'Refactor targets not yet done' above)" — No such entry above; contradicts CLAUDE.md's
  legacy rule; README has no "Toolchain setup" section (cited :826). · covered-by: DOC.S21, DOC.S07 ·
  [H15]
- **DOC.N294** TODO · `BACKLOG.md:828-832` — "missing the pico-sdk 2.0.0+ picotool major.minor
  version-matching requirement ... and the full apt package list" — `update_and_install.txt` known
  incomplete; `pico-setup` suggested as a base. · related: DOC.S15 · [H15]

## HEAP_FRAGMENTATION_MEASUREMENTS.md (current, 393 lines; owning area HW)

- **DOC.N295** INVAR · `HEAP_FRAGMENTATION_MEASUREMENTS.md:5-9` — "It holds method, not results." —
  Results/rules belong in SPEC Part I, H.7, B.14.2 and `tests_hardware/README.md`; this file is method
  only. · related: DOC.T06 · [H15]
- **DOC.N296** RISK · `HEAP_FRAGMENTATION_MEASUREMENTS.md:11-15` — "The measurement record is archived,
  not deleted ... git show 12640c2:HEAP_FRAGMENTATION_MEASUREMENTS.md" — All "archive §" citations and
  the evidence base depend on commit `12640c2` staying reachable. · covered-by: DOC.S04, DOC.T04 · [H15]

## Archive `12640c2:HEAP_FRAGMENTATION_MEASUREMENTS.md` (5,553 lines) — only items still open/undecided/deferred/next-step there, with carry status in current docs

- **DOC.N297** TODO · `ARCH:3228-3231` — "flagged in place and queued as R16" — SPEC I.3's 49,152 B
  figure suspected as a probe-pinning artefact; current SPEC no longer contains the figure and the queue
  has no R16 — apparently resolved by removal (inferred). (low) · [H15]

## UART_C_PORT_CHANGELOG.md (128 lines; owning area UART). Every entry is pending C-side reconciliation, which is out of scope (owner 2026-09-24).

- **DOC.N298** DRIFT · `UART_C_PORT_CHANGELOG.md:48-49 vs :58, :60-61, :64, :66` — "Status values:
  proposed ..., applied-python ..., reconciled" — The table uses values outside this set
  ("applied-python (no-change)", "(invariant)", "(constraint)", "proposed, owner-decided, interim in
  force", "proposed, design resolved"). Rows also run out of order (A8 and A7 before A9, A6 last). (low)
  · [H15]

## Commit messages (chronological)

- **DOC.N299** TODO · `commit 368fa83` — "Adds two small deferred-work items (LED color/pattern
  reference, documenting the FRAM 0=disabled meaning)" — Two doc deferrals. · status: FRAM 0=disabled
  done (SPECIFICATION.md:271, DEVICE_REFERENCE.md); LED colour/pattern reference not located by grep —
  check DEVICE_REFERENCE.md (low) | - · [H17]
- **DOC.N300** NOTE(TRACKED) · `commit f12c231` — "Both were flagged in review but never fixed ...
  recording them as open questions" (items 18/19) — Doc staleness. · status: done-in f8d511a | - · [H17]
- **DOC.N301** NOTE(LEFT-ALONE) · `commit bcc4c3b` — "Left alone deliberately:
  tests/test_asy_bmp3xx_driver.py, whose long blocks predate this branch" — Over-cap comments left. ·
  status: done (repo-wide zero over-cap per CLAUDE.md, gated by tests_scripts/test_comment_block_cap.py)
  | - · [H17]
- **DOC.N302** NOTE(DROPPED-BY-DESIGN) · `commit 4b85426` — "The audit-pass histories (J through Q), the
  phase-by-phase work list, the legacy violation map and the done criteria are dropped, not migrated" —
  UART_PROMOTION_REQUIREMENTS.md retired; durable facts to SPEC J.9/E.5.1/F.1. · status: done-in 4b85426
  | - · [H17]
- **DOC.N303** NOTE(MERGE-RISK) · `commit bb5a43a / 3e801ef / 41762dc` — BACKLOG numbering collisions on
  merges (16/17 -> 26/27 -> 28 -> 25-29 renumbering) — Number reuse and renumbering across branches;
  CLAUDE.md/BACKLOG say numbers are never reused, but these merges renumbered live items. · status:
  informational; present BACKLOG uses stable non-contiguous numbers | - · [H17]
- **DOC.N304** NOTE(OWNER) · `commit 706f9e0` — "BACKLOG 30 ... SPECIFICATION.md carries six subsections
  about one sensor ... The owner's ruling is to leave the specification as it stands and tidy it in a
  session of its own" — SPEC structure. · status: done-in 5b97af3 (ISL sections moved to Part M) | - ·
  [H17]
- **DOC.N305** NOTE(DEFERRED) · `commit 3a94eb2` — "BACKLOG 31 records the measured per-file counts for
  a repo-wide sweep of its own" (~200 over-cap comment blocks) — Comment-cap sweep. · status: done
  (CLAUDE.md: every scope measures zero; tests_scripts/test_comment_block_cap.py) | - · [H17]
- **DOC.N306** NOTE(DOC-DRIFT) · `commit dfb85ff` — "SPECIFICATION.md's F.2 WiFi-power-cycle-backstop
  invariant now states the accepted residual risk window precisely ... instead of the old, now-inexact
  'structurally cannot have a write in flight' claim" — SPEC F.2 (SPECIFICATION.md:3632-3640) was
  corrected, but CLAUDE.md:199-201 Hard rule still says "a device whose API is unreachable structurally
  cannot have a write in flight" — the claim SPEC calls "no longer exactly true". · UNTRACKED | related:
  NET.T*, DOC.T* · [H17 (also H17)]
- **DOC.N307** NOTE(FLAGGED) · `commit 500712e` — "The other four predate these commits (RunContext,
  _report_soak_attempt, and a 17-line module header) and are flagged rather than silently reformatted" —
  Over-cap docstrings. · status: done (repo-wide zero over-cap, test_comment_block_cap.py) | - · [H17]
- **DOC.N308** NOTE(FLAG) · `commit b7dd34e` — "CLAUDE.md's own 'Pre-push verification' section still
  reads as a blocking gate, so CLAUDE.md and BACKLOG.md now disagree" — Doc contradiction. · status:
  done-in c500bb9 (CLAUDE.md carries the owner's 2026-09-18 decision) | - · [H17]
- **DOC.N309** NOTE(LOST-THEN-RECOVERED) · `commit 323a1a7` — "Five more items main had and this branch
  did not, each re-verified here before recording (BACKLOG 37-41)" — Recovery after merge e5d2c43 —
  lists five items but NOT the D.15 reorder task, confirming that one stayed lost. · status: 37-41 later
  closed (58abf8f etc.); D.15 reorder UNTRACKED (see 41762dc item) | - · [H17]
- **DOC.N310** NOTE(DEFERRED-THEN-DONE) · `commit 4631b82 -> 35ba8ac / 5c5a2d0` — "scripts/*.sh carries
  88 over-cap blocks ... the scope is the owner's call"; "48 section references in buildgen/ ... cite
  the design record that was folded into Part L and deleted" — Shell comment cap; dangling citations. ·
  status: done-in 35ba8ac and 5c5a2d0 | - · [H17]
- **DOC.N311** NOTE(PLAN) · `commit a28513f .. 2a88cc8` — PROJECT_AUDIT_PLAN.md: "Execution is blocked
  until the owner's explicit go-ahead. Every seed is recorded unverified" — Audit plan (this harvest's
  context). · tracked: PROJECT_AUDIT_PLAN.md | - · [H17]
