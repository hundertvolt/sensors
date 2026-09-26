# Harvest H05 — unit/mock test tier, part C of `tests/` (snapshot 2a88cc8)

Cross-file aggregate items are listed first under "Partition-wide aggregates"; per-file sections follow.

## Partition-wide aggregates
- SUPPRESS | tests/test_base_classes.py:23; tests/test_fram_integration.py:21; tests/test_notification_fram_integration.py:24; tests/test_ntp_fram_system_integration.py:28; tests/test_print_log.py:13; tests/test_system_service.py:16; tests/test_voc_algorithm.py:14 | "asy_spi_driver._SPI = FakeMB85RS64V  # type: ignore[misc]" | 7 files replace the real SPI class module-wide with the FRAM chip fake at import time; this is safe only because every test file runs as its own Unix-port process ("Same one-process-per-test-file swap"), so the process-per-file model is load-bearing | area: TEST | related: TEST.T07
- SUPPRESS | partition-wide (45 sites incl. combined codes: test_config_manager.py 36, test_base_classes.py 3, test_captive_dns.py 3, test_crc_checks.py 1, test_ntp_fram_system_integration.py 1, test_ntp_wifi_dns_integration.py 1) | "# type: ignore[arg-type]" | Deliberate wrong-type inputs for defensive-contract tests; the largest suppression class in this partition | area: TEST | -
- SUPPRESS | partition-wide (39 sites incl. combined `[assignment, misc]`: test_captive_dns.py 17, test_config_manager.py 6, test_ntp_fram_system_integration.py 4, test_system_service.py 4, test_ntp_wifi_dns_integration.py 3, test_bus_hazard_multi_device.py/test_notification_scd30_sgp40_integration.py/test_notification_sgp40_integration.py/test_print_log.py/test_tmp_scratch.py 1 each) | "# type: ignore[assignment]" | Module-global monkeypatching (asyncio.sleep, udps, DNSQuery, json, AsyUDPSocket) is the mocking mechanism; each site silences mypy | area: TEST | related: TEST.T11
- SUPPRESS | tests/test_base_classes.py:897,1162; tests/test_system_service.py:486,1304; tests/test_uart_comm_hazard.py:530,1003,1044 | "# type: ignore[method-assign]" | 7 method-assign suppressions in this partition (CLAUDE.md's "~157" repo-wide count is already flagged stale by DOC.S08) | area: TEST | related: DOC.S08
- SUPPRESS | tests/test_ticks_rollover.py:35,49,51,61,62,70,71,88,89 | "# type: ignore[type-var]  # stub gap, see module docstring" | 9 suppressions for a stub gap in `time.ticks_add()`'s typing (see test_ticks_rollover.py section) | area: TEST | -
- SUPPRESS | tests/test_captive_dns.py:113-114,383-384,717-718,779-780; tests/test_system_service.py (17 CancelledError sites, 342-1228); tests/test_uart_comm_hazard.py (3); tests/test_neopixel_wifi_integration.py:40; tests/test_notification_*_integration.py (4); tests/test_ntp_*_integration.py (3) | "except asyncio.CancelledError: pass" / "except (TypeError, AttributeError): pass" | Expected exceptions swallowed with no further assertion: CancelledError in cancel/cleanup helpers, and in test_captive_dns.py the pinned contract that a non-str input RAISES TypeError/AttributeError (not degrades) | area: TEST | related: TEST.T01
- INVAR | tests/test_base_classes.py:41; tests/test_captive_dns.py:21; tests/test_config_manager.py:21; tests/test_crc_checks.py:17; tests/test_fram_integration.py:42 (and most files) | "drives a coroutine to completion for these sync test_* functions" | Each file keeps its own local `run()` wrapper around `asyncio.run()`; the CLAUDE.md no-nested-`asyncio.run()` rule depends on these only ever being called from sync scope, review-only | area: TEST | related: TEST.T06, TEST.S18
- PLATFORM | tests/test_base_classes.py:27; tests/test_captive_dns.py:11; tests/test_config_manager.py:11; tests/test_crc_checks.py:7; tests/test_bus_hazard_generated.py:21 (and most files) | "typing isn't available on the real MicroPython test interpreter" | Every file guards `from typing import TYPE_CHECKING` with try/except ImportError; depends on the Unix-port build lacking `typing` (low) | area: PLAT | -

## tests/test_base_classes.py
- LIMIT | tests/test_base_classes.py:54-56 | "proving SensorReader's FRAM-backed path stays exception-safe against the general _FramManager/_FramChunk Protocol contract" | The raise-path tests use a local fake because the real AsyFramManager's own try/except means write_into()/read_into() can no longer raise, so those defensive branches are exercised only through a double | area: TEST | -
- INVAR | tests/test_base_classes.py:61-63, 85-87 | "Every parameter below keeps its exact name (and stays unused)" | The fakes must keep the Protocol's exact parameter names because mypy matches Protocols structurally by name and print_log.py calls `get_chunk(size, crc=CRC8())` by keyword | area: TEST | -
- MIRROR | tests/test_base_classes.py:54 | "Minimal local fake (mirroring tests/test_print_log.py's)" | The raising FRAM fakes here are copies of test_print_log.py's; two copies to keep aligned | area: TEST | related: TEST.T08
- PLATFORM | tests/test_base_classes.py:213 | "bytearray(-1) would raise MemoryError on real MicroPython if unguarded" | Negative-size allocation raises MemoryError (not ValueError) on MicroPython; the guard's reason depends on that runtime behaviour | area: PLAT | -
- PLATFORM | tests/test_base_classes.py:231-232 | "confirmed directly against the real MicroPython interpreter that bytearray(2**62) raises MemoryError" | Heap-exhaustion technique confirmed on the 64-bit Unix port only | area: PLAT | -
- PLATFORM | tests/test_base_classes.py:239-241 | "bytearray(n) raises OverflowError instead of MemoryError once n hits the signed-64-bit machine-word boundary (2**63)" | The OverflowError threshold is a 64-bit-host fact; on the 32-bit RP2040 the boundary sits elsewhere, so this test pins host behaviour only | area: PLAT | -
- ASSUME | tests/test_base_classes.py:344-346 | "A negative max_val is a dev-time-typo risk, never a runtime-computed value" | LockedCounter clamps a negative max_val to 0, justified by the assumption that max_val is never computed at runtime | area: CORE | -
- LIMIT | tests/test_base_classes.py:389-390 | "LockedValue does no range clamping (unlike LockedCounter)" | LockedValue stores NaN/inf and any value untouched; no range guarantee | area: CORE | -
- DRIFT | tests/test_base_classes.py:479-480 | "not a caller mistake to guard against like a negative max_module_error would be (see BACKLOG.md's structural-pass note)" | BACKLOG.md at 2a88cc8 has no "structural-pass" note and no `max_module_error` mention; the pointer dangles | area: DOC | related: DOC.S05
- ASSUME | tests/test_base_classes.py:682-684, 694-696 | "AsyFramManager.get_chunk() never actually raises (confirmed by its own src/ promotion audit)" | Claims about the real manager (get_chunk never raises; `_write_chunk` wraps its whole body) rest on a past promotion audit and are exercised only through fakes | area: STOR | -
- INVAR | tests/test_base_classes.py:699-701 | "history_length=4 matches _RaisingFramChunk.get_buffer()'s hardcoded 6-byte buffer" | The test's history_length must match the fake's hardcoded buffer, or the test fails for the wrong reason (buffer size, not raise_on_write) | area: TEST | -
- RISK | tests/test_base_classes.py:1013-1015 | "setup() on a brand-new config file already records one wrn_s() ("Config file ... not found")" | Every first boot records a persisted (`_s`) FRAM warning for a routine missing-file condition, so a fresh unit's errcount is nonzero by design | area: CORE | -
- LIMIT | tests/test_base_classes.py:1019-1021 | ""ok" means "no exception", not "every field valid"" | write_config returns (True, ...) for a request whose only key is unrecognized; callers must read per-field results, not the flag | area: CORE | -
- LIMIT | tests/test_base_classes.py:1054-1059 | "a repair warning uses pr.wrn()/pr.err(), never the persisting _s() variants, so neither logger writes to FRAM" | ConfigManager's malformed-file repair is not persisted to the FRAM error log even when FRAM-backed; that evidence is lost on reboot | area: CORE | -
- ASSUME | tests/test_base_classes.py:1081-1083 | "allocated_size can never exceed size by construction, so that comparison alone is a tautology" | WP4/Topic 6's per-device FRAM-capacity check is only meaningful through the None-chunk signal; a check using allocated_size alone would be vacuous (retired WP4/Topic 6 ID) | area: STOR | related: TEST.T01
- SETTLED | tests/test_base_classes.py:1132-1133 | "Persist-first, then push (project decision)" | A value reaches hardware only after it is on flash | area: CORE | -
- SETTLED | tests/test_base_classes.py:1135-1136 | "there are no generic force-resend semantics, SCD30's AmbPres being the only case that needed them and not using this path" | Push fires only on "Valid", never "Unchanged"; AmbPres is the single exception handled elsewhere | area: SENS | -
- SETTLED | tests/test_base_classes.py:1205-1207 | "a failed push triggers _recover_failed_push, which corrects the persisted value back" | Failed push → persisted value restored via getter / pre-write snapshot / schema default chain; status stays "Failed" | area: CORE | -
- INVAR | tests/test_base_classes.py:1320-1322 | "its return value is not statically known to satisfy the field's schema" | A getter's return value used in recovery must pass type_or_range_error; an invalid getter value falls to the next rung | area: CORE | -
- MIRROR | tests/test_base_classes.py:1405-1407 | "Mirrors legacy's cmd_keys exclusion from the getter/config/default fallback chain" | Command-only fields are skipped in push-failure recovery, matching legacy cmd_keys | area: PAR | -
- ASSUME | tests/test_base_classes.py:1429-1434 | "Real finding (2026-09-08, real bench hardware): ... logging one spurious CFGMGR_<name> errno=8 on every single write" | Regression pin for a single dated bench finding (special-alone field snapshot fetch); the fix filters the snapshot to persisted keys | area: CORE | -
- RISK | tests/test_base_classes.py:1449-1451 | "a fresh special-alone-only schema's own setup() legitimately logs two benign warnings" | Two warnings (no config file, no storage values) are logged by design for a command-only schema | area: CORE | -
- LIMIT | tests/test_base_classes.py:1493-1495 | "_get_dict_cfg() does no filtering of its own, so including Trigger would exercise a separate, pre-existing characteristic" | _get_dict_cfg reading a special-alone field is a known, unexplored characteristic the test deliberately steps around | area: CORE | -
- LIMIT | tests/test_base_classes.py:1531-1533 | "Unreachable via _set_dict_cfg's normal flow" | Tests a defensive early return that normal flow never reaches (low) | area: TEST | -
- MIRROR | tests/test_base_classes.py:1641-1642 | "matching the legacy pipeline's own default (set_sensor_value only pushes on prev_updated or force=True)" | Unchanged value is a hardware no-op, claimed to match legacy | area: PAR | -
- SETTLED | tests/test_base_classes.py:1664-1666 | "Final project decision: an unrecognized key is just another per-field "Invalid" outcome" | An unknown key does not invalidate the rest of a multi-field request | area: CORE | -
- SETTLED | tests/test_base_classes.py:1731-1733 | "every key in the request comes back "Failed", not silently dropped or "Invalid"" | An invalid ConfigManager makes every requested key report "Failed" | area: CORE | -
- LIMIT | tests/test_base_classes.py:1790-1792 | "The real ConfigManager-backed _set_mgr_cfg never does this, but a subclass override could" | Malformed-override tests (raise / non-dict / missing key) cover shapes only a misbehaving subclass could produce (low) | area: TEST | -
- SETTLED | tests/test_base_classes.py:1825-1826 | "Registered once per instance at construction time (project decision)" | Push callbacks are per-instance, never shared across instances | area: CORE | -
- SUPPRESS | tests/test_base_classes.py:611, 686, 702, 724, 1775 | "# type: ignore[return-value]" / "# type: ignore[arg-type]" | Deliberately malformed overrides and Protocol-fake arguments | area: TEST | -

## tests/test_bus_hazard_generated.py
- ASSUME | tests/test_bus_hazard_generated.py:41-43 | "tests/ runs as the Unix-port interpreter's cwd == repo root (scripts/test.sh's own convention" | The relative path `build/generated_src` works only when test.sh's cwd convention holds | area: TEST | -
- INVAR | tests/test_bus_hazard_generated.py:48-50, 64 | "discovered from whichever wiring-plan JSONs scripts/_generate_sensortask_modules.py already wrote" | The file depends on generation having run first (asserts non-empty); a stale build dir would test stale wiring | area: TEST | related: TEST.T09
- PLATFORM | tests/test_bus_hazard_generated.py:52-54, 58-60 | "MicroPython's Unix-port test build has no glob module" / "MicroPython's os module has no .path submodule" | Directory scan uses os.listdir and "/".join because of missing modules in the Unix-port build | area: PLAT | -
- LIMIT | tests/test_bus_hazard_generated.py:68-73 | "assert bus_name.startswith("i2c"), f"unexpected I2C bus key shape" | The generated scheme handles I2C buses only; any SPI bus key in a wiring plan would abort the file, and SPI hazards stay hand-written | area: TEST | -
- INVAR | tests/test_bus_hazard_generated.py:69-71 | "the trailing digit IS the real hardware port id" | Relies on buildgen's "buses" key being exactly the TOML string `i2cN` | area: GEN | -
- LIMIT | tests/test_bus_hazard_generated.py:104-106 | "a lone occupant on its own bus has no cross-sensor hazard to prove anything about" | Cross-occupant scenarios are generated only for buses with 2+ occupants; the membership test is then tautological | area: TEST | covered-by: TEST.S01
- INVAR | tests/test_bus_hazard_generated.py:139-141 | "a real occupant with no tests/_bus_hazard_catalog.py adapter yet must abort with a clear, actionable message" | A new driver on an I2C bus needs a catalog adapter, and the file must fail loud rather than skip | area: TEST | related: TEST.T06

## tests/test_bus_hazard_multi_device.py
- SETTLED | tests/test_bus_hazard_multi_device.py:1-3 | "Holds only driver-agnostic hazard shapes ... Runs alongside test_bus_hazard_generated.py, not a staging area for it" | Division of labour between the hand-written and generated mock bus-hazard tiers | area: TEST | -
- PLATFORM | tests/test_bus_hazard_multi_device.py:66 | "hard-wired (FN8424 p15) - dev-only, sharing i2c1 with SCD30 and SGP40" | ISL29125 address is a datasheet fact (FN8424 p15) | area: SENS | -
- INVAR | tests/test_bus_hazard_multi_device.py:68-70 | "every real device address this codebase uses must fall outside both, and only SGP40's own documented _reset() may ever address 0x00" | Reserved-address rule for all devices; the check runs on constants in the test file itself | area: BUS | covered-by: TEST.S05
- MIRROR | tests/test_bus_hazard_multi_device.py:78-80, 99-100 | "the same one test_asy_bmp3xx_driver.py uses" | BMP3xx calibration/ADC dataset and STATUS register shape copied from test_asy_bmp3xx_driver.py | area: TEST | related: TEST.T08
- PLATFORM | tests/test_bus_hazard_multi_device.py:156-157 | "MicroPython's builtin zip() doesn't accept keyword arguments (confirmed against the pinned Unix-port interpreter)" | zip(strict=) unavailable | area: PLAT | -
- LIMIT | tests/test_bus_hazard_multi_device.py:275-276 | "This is the ROGUE-broadcast case tests/_bus_hazard_catalog.py's TOML-driven scheme cannot generate" | Rogue general-call coverage exists only as this hand-written test | area: TEST | -
- PLATFORM | tests/test_bus_hazard_multi_device.py:282, 296 | "BMP3xx doesn't ack general calls (datasheet-confirmed)" | Datasheet claim that BMP3xx never ACKs a general call; the test swallows the resulting OSError | area: SENS | -
- LIMIT | tests/test_bus_hazard_multi_device.py:391-392 | "The generated TOML-driven scheme cannot produce this shape (every device TOML puts the FRAM alone on spi0)" | Multi-device SPI is covered only by this synthetic pair; no real device has two SPI occupants | area: TEST | -
- INVAR | tests/test_bus_hazard_multi_device.py:420-421 | "take the bus lock, run the whole CS cycle synchronously, release, then yield - never yielding with CS asserted" | Convention asy_fram_driver.py's command bodies must follow | area: BUS | -
- PLATFORM | tests/test_bus_hazard_multi_device.py:466 | "32+ bytes: the DMA path, the only one that can raise" | Relies on 1.29's new OSError(EIO) raise site on 32+ byte SPI reads (Part F.5) | area: PLAT | -
- SUPPRESS | tests/test_bus_hazard_multi_device.py:52, 457 | "# type: ignore[assignment]" / "# type: ignore[union-attr]  # the fake SPI behind the wrapper" | asyncio.sleep patch; reaching into the fake SPI behind the wrapper | area: TEST | -
- LIMIT | tests/test_bus_hazard_multi_device.py:36-38 | "asyncio.gather() itself returns a Future, not a Coroutine - mypy rejects passing it straight to run()" | Typing workaround convention (wrap gather in a scenario coroutine) shared with test_asy_i2c_driver.py (low) | area: TEST | -
- ASSUME | tests/test_bus_hazard_multi_device.py:350-352 | "I2CDevice's session lock is the shared bus lock, so this proves the same mechanism" | Per-device session serialization is the bus lock itself (low) | area: BUS | -

## tests/test_captive_dns.py
- INVAR | tests/test_captive_dns.py:29-31 | "Below the OS ephemeral range (32768-60999) so a concurrently-running ephemeral socket can never be assigned this port" | UDP base 22000 (E.1's per-file disjoint port bases) is kept disjoint by review only; `make_port()` increments per call (8 call sites today) toward the 23000 ntp_client base (low) | area: TEST | related: TEST.T06, TEST.S21
- DRIFT | tests/test_captive_dns.py:30 | "see scripts/test.sh's own TEST_PARALLELISM comment" | test.sh's TEST_PARALLELISM comment (scripts/test.sh:125-140) says nothing about the ephemeral range; the reasoning lives in SPECIFICATION.md E.1 (:2767-2780) | area: DOC | -
- WORKAROUND | tests/test_captive_dns.py:41-44 | "rejects a plain (host, port) tuple in bind()/sendto() with "TypeError: object with buffer protocol required" (micropython/micropython#6924)" | Unix-port-only defect; tests resolve via getaddrinfo first; removal trigger: none stated | area: TEST | -
- LIMIT | tests/test_captive_dns.py:95-96 | "A previously-silent gap: an out-of-range octet used to shift bits past its own byte position" | Regression pin for a fixed false-subnet-match bug in `_ipv4_to_int` (low) | area: NET | -
- LIMIT | tests/test_captive_dns.py:104-114, 704-718, 769-780 | "a wrongly-typed value must raise one of the exact types every caller in this file already guards against" | `_ipv4_to_int`, `DNSServer.run()` and `DNSQuery.response()` RAISE on non-str input rather than degrade; the str-typed public signature relies on callers only passing str | area: NET | -
- DRIFT | tests/test_captive_dns.py:230-235 | "Regression test for BACKLOG.md's "root-domain query can't be told apart from a failed parse" entry" | Cited BACKLOG entry no longer exists | area: DOC | covered-by: DOC.S05
- INVAR | tests/test_captive_dns.py:279-281 | "a wrong list here drops DNSSRV out of /status's errcount and out of the level registry, both silently" | The duck-typed fan-in accessor pair must list DNSSRV's logger; a wrong list fails silently at runtime, only this test catches it | area: NET | -
- LIMIT | tests/test_captive_dns.py:327-333, 800-806 | "this environment can never itself produce a real string addr[0] for a server-mode socket" | In the Unix-port build recvfrom() returns an opaque raw sockaddr, so the real-socket tests can only assert liveness/rebind; reply-to-client over a real socket is never tested at this tier | area: TEST | -
- DRIFT | tests/test_captive_dns.py:343, 1086 | "see Step 6 note" / "Step 6 (silent-failure-masking finding)" | References a retired step-session ID with no surviving note | area: DOC | related: DOC.S05
- ASSUME | tests/test_captive_dns.py:479-482 | "well under that margin proves the guard is actually what's preventing it" | Wall-clock bound `elapsed_ms < 1000` against a 3 s backoff | area: TEST | covered-by: TEST.S14
- INVAR | tests/test_captive_dns.py:810-812 | "safe only because AsyUDPSocket.disconnect() fully resets state for the next _connect()" | Reusing one DNSServer across hotspot activations depends on disconnect() fully resetting the socket state | area: NET | -
- MIRROR | tests/test_captive_dns.py:867-872 | "replicates asy_wifi_service.py's real DNSServer usage exactly. That module cannot be imported here" | Test hand-copies the real caller's construct-once / create_task / fire-and-forget cancel() pattern (src/asy_wifi_service.py:170, 299-301, 329-330, 394); must be kept in sync by hand | area: TEST | -
- DRIFT | tests/test_captive_dns.py:875, 885 | "exactly async_connect.py's own pattern" (test name `..._async_connects_fire_and_forget_cancel_pattern`) | Names the legacy `async_connect.py`; the header at :868 names the real caller asy_wifi_service.py | area: DOC | -
- LIMIT | tests/test_captive_dns.py:902-904 | "The one fault category that genuinely cannot be produced for real ... simulated with a monkeypatched DNSQuery" | run()'s catch-all backoff is reachable only by monkeypatching a dependency | area: TEST | -
- ASSUME | tests/test_captive_dns.py:981-983 | "measured at ~5 wrn_s() lines/second before the fix" | Single measurement of the pre-fix empty-recvfrom spin rate; now backs off 0.5→1→2 s, cap 5 s (C.9) | area: NET | -
- ASSUME | tests/test_captive_dns.py:1005-1017 | "possibly a 5th call too (run() loops straight back into recvfrom() again after replying, racing this test's own _wait_until poll)" | Backoff-gap tests assert wall-clock windows (400-800, 900-1400, 1900-2600 ms) and tolerate a known race on call count | area: TEST | related: TEST.S14
- INVAR | tests/test_captive_dns.py:1086-1088 | "AsyUDPSocket.disconnect() never raises, but now reports a failed unregister()/close() via its bool return - run() must actually check it and log" | Callers of disconnect() must check its bool; enforced here for captive_dns only | area: NET | -
- SUPPRESS | tests/test_captive_dns.py:44, 934, 947 | "# type: ignore[return-value]" / "# type: ignore[assignment,misc]" / "# type: ignore[misc]" | getaddrinfo sockaddr typing; DNSQuery class monkeypatch | area: TEST | -
- INVAR | tests/test_captive_dns.py:146-147 | "it must reuse the caller's logger identity/history, not get an independent PrintLogHistory of its own" | DNSQuery is built per request and must share DNSSRV's logger (low) | area: NET | -

## tests/test_config_manager.py
- LIMIT | tests/test_config_manager.py:130-132 | "Documented, not guarded against: nothing in the codebase relies on rejecting this shape" | A bare string passed as a ConfigSchema is iterated per character and accepted | area: CORE | -
- RISK | tests/test_config_manager.py:148-150 | "Ambiguous but benign: a single field named "" ... returns the same "" a malformed or empty schema does" | name_cfg cannot distinguish an empty-named field from a malformed schema; accepted as benign | area: CORE | -
- DRIFT | tests/test_config_manager.py:171-172 | "The old pipe-delimited-string encoding corrupted a str default containing "||" (see git history)" | History narrative pointing at git history (low) | area: DOC | -
- LIMIT | tests/test_config_manager.py:339-341 | "this is a defensive check on the function's own general contract, not a reachable production path" | coerce_numeric non-(int,float) scalar_type branch is unreachable in production (low) | area: TEST | -
- RISK | tests/test_config_manager.py:347-357 | "Documented, accepted risk: no registered float field's bounds go near this range, and this build cannot reproduce the real single-precision threshold" | int→float is a blanket accept; float(int) silently rounds beyond the mantissa (24 bits on RP2040, 52 on the Unix port); the test proves only the double-precision boundary | area: CORE | -
- ASSUME | tests/test_config_manager.py:348-349 | "the largest today is BMP3xx's SeaLevelOffs at 5000.0" | The accepted-risk argument rests on a dated survey of float-field bounds; a new wide-range float field would invalidate it | area: CORE | -
- PLATFORM | tests/test_config_manager.py:351-352 | "24 bits on the real RP2040's single-precision build, 52 on this Unix-port double-precision one" | Float precision differs between the test interpreter and the target, so float edge cases on the unit tier do not transfer | area: PLAT | related: TEST.T19
- PLATFORM | tests/test_config_manager.py:406-408 | "MicroPython's int(float) raises ValueError for NaN and OverflowError for the infinities (confirmed against py/objint.c)" | Runtime fact behind NaN/inf int-coercion rejection | area: PLAT | -
- LIMIT | tests/test_config_manager.py:477-479 | "A wrong-typed "special" ... makes this always return True regardless of check_val - reachable in principle" | type_or_range_error rejects everything for a malformed special; only check_cfg_get_default's self-check guards it in practice | area: CORE | -
- LIMIT | tests/test_config_manager.py:661-663 | "An authoring mistake (min/max swapped) makes `val_min <= check_val <= val_max` unsatisfiable" | A swapped-bounds schema rejects every value; not detected as a schema error by this function (low) | area: CORE | -
- PLATFORM | tests/test_config_manager.py:702-704 | "str length bounds are codepoint bounds, not byte bounds, on this MicroPython build" | Confirmed on the Unix-port build only; depends on the target also enabling Unicode str support | area: PLAT | -
- SETTLED | tests/test_config_manager.py:809-811 | "Deliberate, longstanding asymmetry" | The bool branch of type_or_range_error never inspects "special"; a wrong-typed bool special surfaces only via the self-check | area: CORE | -
- PLATFORM | tests/test_config_manager.py:870-871 | "os.stat()/open() raise TypeError (not OSError) for a non-string path on this interpreter" | setup() treats that as "not found"; interpreter-specific exception type | area: PLAT | -
- PLATFORM | tests/test_config_manager.py:912-914 | "MicroPython's json module writes NaN/inf ... but cannot read that token back" | A NaN in a stored config makes the file unreadable and triggers a rebuild from defaults | area: PLAT | -
- PLATFORM | tests/test_config_manager.py:929-935 | "re-confirmed against the pinned v1.29.0 interpreter ... (fixed upstream in 2025, commit 9ef16b466" | json.load() leniency: an omitted value before a comma/brace produces a mangled dict instead of raising; accepted because per-key checks fall back to defaults; re-check on version bumps | area: PLAT | -
- ASSUME | tests/test_config_manager.py:964-966 | "setup()'s `type(coerced_cfg) is not type(new_cfg)` check (not `!=`, which 7 != 7.0 would miss)" | setup()'s rewrite trigger compares on type identity; the comment's reasoning pins that exact implementation (low) | area: CORE | -
- LIMIT | tests/test_config_manager.py:1201-1206 | "the "123" string key actually on disk matches nothing, _cache never being rebuilt from the file after setup()" | A non-string field name is never rejected and diverges between _cache and disk | area: CORE | -
- LIMIT | tests/test_config_manager.py:1440-1441, 1524-1526 | "No partial success: the loop raises KeyError on the first missing key and the whole call returns None" | get_dict/get_int_values are all-or-nothing across fields | area: CORE | -
- SETTLED | tests/test_config_manager.py:1450-1452, 1474 | "Deliberate consequence of _cache (see module docstring): get_dict never re-opens the file" | _cache is the sole source of truth for reads; out-of-band file deletion/edits have no effect until reboot | area: CORE | -
- PLATFORM | tests/test_config_manager.py:1730-1732 | "an RP2040 flash write disables interrupts port-wide, and inline it reset the HTTP connection whose PUT triggered it" | Why write_config defers the flash write to a separate task (Part F.2) | area: PLAT | -
- ASSUME | tests/test_config_manager.py:1743-1745, 1974-1976 | "two separate top-level run() calls would race the independently-scheduled flush task" | Tests must keep write+read in one coroutine with no await; test determinism depends on that discipline | area: TEST | related: TEST.T04
- LIMIT | tests/test_config_manager.py:1750-1752 | "Deliberately not asserting mgr._cache's exact value here" | Whether the deferred flush has run is non-deterministic under this harness, so that state is left unasserted | area: TEST | -
- ASSUME | tests/test_config_manager.py:1763-1765 | "The "at most one unflushed staged value per sensor at a time" assumption WP5's design rests on" | WP5's deferred-flush design assumes at most one pending staged value per sensor; the superseded-snapshot check covers back-to-back writes to the same key | area: CORE | -
- LIMIT | tests/test_config_manager.py:1775 | "only ever holds the LATEST task - see flush_pending()'s own note" | flush_pending() tracks only the most recent flush task | area: CORE | -
- SETTLED | tests/test_config_manager.py:1901-1903 | "A schema self-check failure for ANY key hard-aborts the entire call (return False, {})" | Malformed schema → whole write_config aborted, no partial write | area: CORE | -
- SETTLED | tests/test_config_manager.py:1932-1934 | "an externally-corrupted file does not block a write - it is silently overwritten (repaired) from _cache" | Replaced the pre-cache "detect and fail" design | area: CORE | -
- SETTLED | tests/test_config_manager.py:1954-1958 | "The validated value stays in effect (C.7.3): its push already reached the module" | A failed deferred flush only logs an errno; the read side keeps the new value | area: CORE | -
- LIMIT | tests/test_config_manager.py:2207-2212 | "no config file small enough to be safe in a test can provoke it" | MemoryError arms of setup()/write_config()/_flush_staged() are reachable only by substituting the module's `json` name | area: TEST | -
- PLATFORM | tests/test_config_manager.py:2240 | "MemoryError is not an OSError subclass (CLAUDE.md), _flush_staged's except clause lists it explicitly" | Runtime exception-hierarchy fact | area: PLAT | -
- RISK | tests/test_config_manager.py:2259-2261 | "open(..., "w") already truncated it before json.dump() ran, so a mid-dump failure leaves it unparseable" | A failed flush leaves an unparseable config file on flash until the next real change (resubmitting the same value is "Unchanged" and writes nothing); the next boot then rebuilds from defaults | area: CORE | -
- SETTLED | tests/test_config_manager.py:2322-2323 | "a failed write costs persistence, never the config, and nothing ever retries a write" | C.7.3 write-loop guarantee | area: CORE | -
- INVAR | tests/test_config_manager.py:2530-2541 | "exactly setup()'s and _flush_staged()'s opens for writing, and nothing in the module that could re-run one on its own" | Enforced by a source-text scan: 2 × `open(self.config_file, "w")`, no Timer/sleep/`while `, exactly one `create_task(`; string counting, so a renamed call escapes it | area: CORE | -
- INVAR | tests/test_config_manager.py:2118-2119 | "without config_lock serializing them, the second writer overwriting first's read would silently drop one field's update" | Concurrent write_config calls rely on config_lock | area: CORE | -
- SUPPRESS | tests/test_config_manager.py:2360 | "# noqa: B905 - MicroPython zip() rejects strict=" | Ruff rule suppressed for a MicroPython limitation | area: TEST | -
- SUPPRESS | tests/test_config_manager.py:820-821, 1216, 2348, 2352 | "# type: ignore[arg-type, comparison-overlap]" / "[list-item, comparison-overlap]" / "[attr-defined]" | Non-string-name schema tests; module-level `open` shadowing | area: TEST | -
- LIMIT | tests/test_config_manager.py:1119-1121 | "A schema with zero storable fields ... init still succeeds and writes an empty {} config file" | A command-only schema still creates a config file on flash (low) | area: CORE | -
- INVAR | tests/test_config_manager.py:1223-1225 | "check_cfg_get_default's use_value=False path skips popping it, so it's caught and removed by the "unexpected keys remaining" cleanup instead" | Two setup() paths must cooperate to purge stale special-only values after a schema change | area: CORE | related: CORE.T12
- RISK | tests/test_config_manager.py:2356 | "a missing file's wrnno 3 is routine, not a failure" | The routine missing-file warning is persisted and counted on every first boot | area: CORE | -

## tests/test_crc_checks.py
- PLATFORM | tests/test_crc_checks.py:27, 40 | "Table 10 of the SGP40 datasheet" / "0xBEEF -> 0x92 is Sensirion's other commonly-quoted worked example (e.g. SHT3x datasheet)" | CRC8 test vectors come from datasheets; the SHT3x datasheet is not a chip this repo drives | area: SENS | -
- LIMIT | tests/test_crc_checks.py:629-631 | "if a caller starts feeding a new logical buffer via run_inc() without finalizing ... the old bytes are still folded into inc_crc/inc_count" | A dangling incremental sequence silently corrupts the next one; callers must always finalize with check_inc() | area: CORE | -
- INVAR | tests/test_crc_checks.py:648-649 | "always finalize with check_inc() before starting the next one" | Reuse of one CRC instance across sequences is caller discipline; non-concurrent use only | area: CORE | -
- OPENQ | tests/test_crc_checks.py:692-694 | "Empty-payload asymmetry between add() and check() - flagged, not silently fixed (see PR discussion)" | add() encodes a zero-byte payload that no check* method can ever verify; the fix was deferred to a PR discussion not recorded in the docs | area: CORE | -
- INVAR | tests/test_crc_checks.py:707-712 | "Every caller must catch it - see asy_uart_driver.py's guarded call sites" | add()/check() are the documented exception to "never raises" and propagate MemoryError; every caller must guard (tested in test_asy_uart_driver.py only) | area: CORE | -
- LIMIT | tests/test_crc_checks.py:734-740 | "no real bytearray can force that to fail" | check()'s MemoryError arm is reachable only through a stand-in buffer whose slice raises | area: TEST | -
- ASSUME | tests/test_crc_checks.py:778-780 | "Observed under the real interpreter: exactly one tick per byte processed, asserted against half that" | The cooperative-yield test pins a Unix-port scheduler observation with a 2x margin | area: TEST | -
- SUPPRESS | tests/test_crc_checks.py:761 | "# type: ignore[arg-type]" | Stand-in buffer passed where bytearray is typed | area: TEST | -
- INVAR | tests/test_crc_checks.py:123-124 | "num_bytes == 0 always nullifies it back to None (CRC_Base's own existing invariant)" | CRC_Pass accepts but discards poly (low) | area: ALGO | related: ALGO.S04

## tests/test_fake_timer_and_network.py
- MIRROR | tests/test_fake_timer_and_network.py:1-3 | "a fake that drifts from silicon would let a test pass for code that fails on the board" | tests/machine.py Timer (ONE_SHOT spent after one fire, PERIODIC re-arms, drop() models F.1's lost soft callback) and tests/network.py byte bounds (C.7.4) are asserted against the fakes only, never against rp2 silicon or source here | area: TEST | related: TEST.T19, TEST.T05
- PLATFORM | tests/test_fake_timer_and_network.py:69-91 | ""ÄT" is 2 characters and 3 bytes" / "65 bytes" / "33 bytes" | Byte-bound facts the fake models: country exactly 2 bytes (ValueError), hostname ≤32 bytes (ValueError), WLAN key ≤64 bytes (OSError), SSID ≤32 bytes (AssertionError); the exception types are rp2/CYW43 facts to re-check on version moves | area: PLAT | -
- LIMIT | tests/test_fake_timer_and_network.py:86 | "the fake's connect_calls is test-only, absent from the board stub" | The test reads a fake-only attribute | area: TEST | -
- INVAR | tests/test_fake_timer_and_network.py:74-75, 81 | "network.country("DE")" / "network.hostname("SensorNode")" | Tests mutate process-global fake network state and restore it by hand at the end (low) | area: TEST | related: TEST.T07
- SUPPRESS | tests/test_fake_timer_and_network.py:64 | "# type: ignore[operator]" | Generic `_raises()` helper | area: TEST | -

## tests/test_fram_integration.py
- DRIFT | tests/test_fram_integration.py:3-5 | "Real RP2040 SPI write()/readinto() cannot raise or report a fault at all once constructed" | Contradicts SPECIFICATION.md F.5.2 (:3710-3714) and CLAUDE.md: since 1.29 rp2 SPI readinto() of 32+ bytes can raise OSError(EIO); test_bus_hazard_multi_device.py:466 relies on that raise. The "deliberately not modeled" SPI fault rationale is stale | area: STOR | related: CORE.T11
- MIRROR | tests/test_fram_integration.py:37-38 | "asy_fram_manager.py's own _STATUS_* are micropython.const() and compiled away - not importable" | The test hand-copies the on-chip status constants; drift from src is not detected | area: TEST | -
- WORKAROUND | tests/test_fram_integration.py:159-164, 177 | "gc.collect() each cycle: without it this tight allocate-heavy loop exhausts the Unix-port binary's heap after ~7 cycles" | A gc.collect() in a test loop props up a MemoryError, attributed to a "test-environment GC-timing artifact" (CLAUDE.md forbids gc.collect() in test setup propping a result); removal trigger: none stated | area: TEST | covered-by: TEST.S11
- SETTLED | tests/test_fram_integration.py:296-301 | "That loss is accepted behavior, not a defect (project owner, 2026-09-11)" | Power loss leaving both blocks BUSY loses the history; no recovery scheme wanted; only all-or-nothing is required | area: STOR | related: STOR.T12
- MIRROR | tests/test_fram_integration.py:304-305 | "Mirrored at the twin tier (Run 5b) and on real silicon (tests_hardware/flash/test_fram_storage.py)" | Same both-blocks-BUSY scenario is claimed at three tiers | area: TEST | -
- INVAR | tests/test_fram_integration.py:219-221 | "reattaching fresh manager and reader objects to the same chip, in the same instantiation order, must decode both" | FRAM layout depends on a static allocation order across boots | area: STOR | -
- INVAR | tests/test_fram_integration.py:333-334 | "a wedged chunk that never takes a write again would be a real defect even under the accepted-loss rule" | After both-BUSY loss the chunk must still accept writes | area: STOR | -
- SUPPRESS | tests/test_fram_integration.py:21 | "# type: ignore[misc]" | See partition-wide `_SPI` swap aggregate | area: TEST | -
- LIMIT | tests/test_fram_integration.py:132-134 | "get_chunk() needs no successful setup(), so reader.pr.fram is a real but permanently unusable chunk, not None" | A chip dead at boot yields a non-None but unusable chunk; a None-chunk capacity check does not detect it | area: STOR | related: STOR.S08

## tests/test_framing_codecs.py
- INVAR | tests/test_framing_codecs.py:157-158 | "skipping *empty frames on the wire* is the read loop's job, not this layer's" | Division of responsibility between the COBS codec and asy_uart_driver's read loop | area: UART | -
- LIMIT | tests/test_framing_codecs.py:172-175 | "the except clause that catches a real MemoryError/OverflowError ... had no test of its own" | The allocation-failure arm is exercised with a `1 << 40` bound on the 64-bit host; whether it raises MemoryError or OverflowError is host-specific | area: TEST | -
- INVAR | tests/test_framing_codecs.py:188 | "allocated once from the frame bound, never per frame" | COBS scratch must be allocated once (asserted via the `allocations` counter) | area: MEM | -

## tests/test_machine_uart_link.py
- MIRROR | tests/test_machine_uart_link.py:1-3 | "The backend-agnostic half lives in _uart_link_contract.py and is re-run against digital_twin/machine.py's own link" | Mock and twin UART link models share one contract suite; link-model specifics (A1) and the bounded poller (A2) are mock-only | area: TEST | related: TEST.T05
- INVAR | tests/test_machine_uart_link.py:103 | "Without this the timeout paths are unreachable and every timeout test passes blindly" | `force_not_ready(n)` is the only way timeout paths get exercised; tests that skip it cannot reach them | area: TEST | -
- INVAR | tests/test_machine_uart_link.py:114-120 | "The standing rule, asserted rather than left to review. Compared by type *name*" | CLAUDE.md's "bounded fake poller, never a real select.poll()" rule is machine-checked only for `LinkPoller` itself, by a type-name comparison; other fake-stream doubles remain review-only | area: TEST | related: TEST.T06
- ASSUME | tests/test_machine_uart_link.py:171-173 | "measured at ~18 entries per fake per protocol transaction, which exhausts the interpreter heap on a long run" | Single measurement behind bounding the fakes' call log at `_LOG_MAXLEN` | area: TEST | -
- LIMIT | tests/test_machine_uart_link.py:171-186 | "Bounded now, and the drop is visible rather than silent" | The fake's `log` drops old entries past `_LOG_MAXLEN`; any assertion on early log entries in a long test silently sees a truncated log unless it checks `log.dropped` | area: TEST | -
- INVAR | tests/test_machine_uart_link.py:77, 159 | "an endpoint belongs to exactly one link" / "no module-level shared link object" | Cross-test isolation of fake UART links rests on per-test make_link() | area: TEST | related: TEST.T07

## tests/test_math_helpers.py
- LIMIT | tests/test_math_helpers.py:40 | "0.5% used to be the (incorrect) lower bound; Stull's paper only validates 5-99% RH" | wet_bulb_temperature's validity domain comes from Stull's paper; below 5% RH returns None | area: ALGO | related: ALGO.T01
- LIMIT | tests/test_math_helpers.py:95-100 | "measured, they disagree by about 1.03 degC right at the boundary at 50% RH" | dew_point's water/ice coefficient sets are discontinuous at 0 °C (~1.03 °C measured); the test tolerates 1.5 °C and only guards against growth | area: ALGO | related: ALGO.T01, ALGO.S03
- INVAR | tests/test_math_helpers.py:189-190 | "the -40..85 degC range check must reject it before the division ever runs" | altitude_baro's divide-by-zero at tmean=-273.15 is prevented only by the range check | area: ALGO | -
- PLATFORM | tests/test_math_helpers.py:429-434 | "Exact equality, not approx(): two published roundings of this matrix differ in the 6th decimal (Part M.1.3)" | Pins the sRGB→XYZ literals by exact float equality on the double-precision Unix port; on RP2040 float32 the same literals round differently, so this pins source text, not device values | area: ALGO | related: ALGO.T06
- MIRROR | tests/test_math_helpers.py:430-431 | "The constants are const()-folded and not readable as attributes" | The test hand-copies the matrix; src and test values must be kept in sync by hand | area: ALGO | -
- LIMIT | tests/test_math_helpers.py:535-537 | "must return None, never a clamped 2000.0/12500.0" | cct_mccamy returns None outside the 2000-12500 K validity span | area: ALGO | -
- INVAR | tests/test_math_helpers.py:569 | "-1.0 is FiltCoeff's own documented "filter off" convention throughout src/" | ema_step and every FiltCoeff user share the -1.0 sentinel | area: ALGO | -
- INVAR | tests/test_math_helpers.py:593-594 | "A NaN/inf previous state ... must not poison every future value forever" | ema_step resets on a non-finite previous state | area: ALGO | -

## tests/test_neopixel_wifi_integration.py
- MIRROR | tests/test_neopixel_wifi_integration.py:1-2 | "proving the LEDControl Protocol (on/off/toggle) holds end to end - test_asy_wifi_service.py only exercises a FakeLED double" | The real NeopixelDriver-as-ext_led seam is proven only here, with fixed 0.05 s sleeps between steps | area: LED | -
- SUPPRESS | tests/test_neopixel_wifi_integration.py:40-41 | "except asyncio.CancelledError: pass" | Cancel helper; see aggregate | area: TEST | -

## tests/test_notification_fram_integration.py
- INVAR | tests/test_notification_fram_integration.py:83-85 | "the "number and order of registered signals stays constant" invariant this design relies on" | NotificationCoordinator's combined FRAM chunk layout (built once in finalize()) decodes across reboots only if signal registration order/count never changes | area: LED | -
- LIMIT | tests/test_notification_fram_integration.py:119-121 | "NeopixelDriver structurally can't fail on any of its own real code paths" | The FRAM history of the NEOPIXEL logger is exercised directly, not via a real failure | area: LED | -
- SUPPRESS | tests/test_notification_fram_integration.py:24 | "# type: ignore[misc]" | See partition-wide `_SPI` swap aggregate | area: TEST | -

## tests/test_notification_neopixel_integration.py
- ASSUME | tests/test_notification_neopixel_integration.py:60-61, 94, 120, 145-147 | "one triggered cycle's real settle time (2*0.5=1.0s) + margin" | Fixed real-time sleeps (1.3 s, 2.5 s, 0.1 s, 1.5 s) with ~0.3-0.5 s margins; host load can fail them | area: TEST | related: TEST.T04
- DRIFT | tests/test_notification_neopixel_integration.py:2 | "the actual production shape src/sensortask_wozi.py wires" | `src/sensortask_wozi.py` no longer exists (generated at build time, SPECIFICATION.md L.2); same stale reference in test_notification_scd30_integration.py:98, test_notification_scd30_sgp40_integration.py:199, test_notification_sgp40_integration.py:114, test_config_manager.py:268,340, test_system_service.py:1413 | area: DOC | related: TEST.S24
- INVAR | tests/test_notification_neopixel_integration.py:128-129 | "registration order (CO2 then VOC) must produce a fully-contiguous red block before any green frame" | Arbitration contract between notification signals: no interleaving | area: LED | -

## tests/test_notification_scd30_integration.py
- LIMIT | tests/test_notification_scd30_integration.py:139-141 | "driven directly instead of through the full irq/timer machinery" | Integration tests hand-drive read_loop's per-cycle steps; the irq/timer path is not part of this integration | area: TEST | -
- MIRROR | tests/test_notification_scd30_integration.py:139-141 | "Exactly what read_loop() itself does per cycle (see asy_scd30_driver.py)" | The test re-implements read_loop()'s per-cycle call sequence; drift in src is not detected | area: TEST | -
- INVAR | tests/test_notification_scd30_integration.py:210-212 | "one faulted cycle logs twice (asy_scd30_driver.py's own _read_scd() catch, errno=11, then base_classes.py's generic _error_check() streak-counter increment, errno=1" | One fault produces two persisted entries per cycle; pins the double-logging shape | area: SENS | -
- INVAR | tests/test_notification_scd30_integration.py:227-236 | "MicroPython's asyncio does not reject that with a clean RuntimeError as CPython does - it corrupts the scheduler badly enough to segfault" | Frame builders call `asyncio.run()` via crc8_byte(), so they must stay at sync top level; review-only convention | area: TEST | related: TEST.T06
- INVAR | tests/test_notification_scd30_integration.py:260-262 | "it only decrements the internal consecutive-failure streak (a plain sync pr.err(), not pr.err_s()" | A later success never erases persisted history | area: CORE | -
- ASSUME | tests/test_notification_scd30_integration.py:148, 176, 201, 253 | "one triggered cycle's real settle time (2*0.5=1.0s) + margin" | Fixed real-time sleeps with 0.3 s margin | area: TEST | related: TEST.T04
- SUPPRESS | tests/test_notification_scd30_integration.py:63 | "# type: ignore[return-value]" | Reaching the raw fake bus through the wrapper chain | area: TEST | -

## tests/test_notification_scd30_sgp40_integration.py
- DRIFT | tests/test_notification_scd30_sgp40_integration.py:1 | "matching sensortask-wozi.py's real single notify/pixel wiring" | Names the retired `improved-quality/sensortask-wozi.py`; also test_ntp_fram_system_integration.py:1, 79, 341 and test_ntp_wifi_dns_integration.py:1, 71 | area: DOC | related: TEST.S24
- MIRROR | tests/test_notification_scd30_sgp40_integration.py:84, 122 | "register/data frame builders, verbatim from test_notification_scd30_integration.py" / "word/CRC builders, verbatim from test_notification_sgp40_integration.py" | Verbatim copies of helpers across three files | area: TEST | related: TEST.T08
- LIMIT | tests/test_notification_scd30_sgp40_integration.py:145-150 | "scd_reader's real reading is deliberately not used" | SGP40 compensation uses a fixed stand-in, not the real SCD30 reading, so the scd30→sgp40 compensation seam is not exercised here | area: TEST | -
- ASSUME | tests/test_notification_scd30_sgp40_integration.py:228-231 | "may run one after another rather than simultaneously ... generous margin covers either ordering" | Fixed 2.6 s sleep for two 1.0 s ramps | area: TEST | related: TEST.T04
- SUPPRESS | tests/test_notification_scd30_sgp40_integration.py:48 | "# type: ignore[assignment]  # deliberate monkeypatch" | Process-wide asyncio.sleep replacement (_FastAsyncSleep) | area: TEST | -

## tests/test_notification_sgp40_integration.py
- ASSUME | tests/test_notification_sgp40_integration.py:3-9 | "a higher raw tick count moves the index down, raw increase meaning cleaner air on this sensor's convention" | Calibration facts about the VOC algorithm (45-interval blackout, settle toward 100) "verified directly"; the test's two-phase design depends on them | area: ALGO | -
- MIRROR | tests/test_notification_sgp40_integration.py:156-160 | "_VOCALGORITHM_INITIAL_BLACKOUT=45 plus settling time" | 160 settle cycles and an exact `VOC == 100` assertion depend on voc_algorithm's constants | area: ALGO | -
- DRIFT | tests/test_notification_sgp40_integration.py:44 | "the ~180-cycle settle-then-spike sequence" | Code runs 160 settle + up to 40 spike cycles (:158, :164); test_notification_scd30_sgp40_integration.py:149 says "200" (low) | area: DOC | -
- INVAR | tests/test_notification_sgp40_integration.py:202-204 | "a nested one segfaults the interpreter - found the hard way while writing this test" | No-nested-asyncio.run rule, second confirmed instance | area: TEST | related: TEST.T06
- ASSUME | tests/test_notification_sgp40_integration.py:181, 211, 255 | "one triggered cycle's real settle time (2*0.5=1.0s) + margin" | Fixed real-time sleeps | area: TEST | related: TEST.T04
- SUPPRESS | tests/test_notification_sgp40_integration.py:52 | "# type: ignore[assignment]  # deliberate monkeypatch" | Process-wide asyncio.sleep replacement | area: TEST | -

## tests/test_ntp_fram_system_integration.py
- ASSUME | tests/test_ntp_fram_system_integration.py:2, 304-309 | "Proves the "no cross-lock contention" assumption asy_fram_manager.py's comments rely on" | ntp_issynced() must only touch SensorReader's `_datalock`, never `wifi_mode_lock`; tested with a 1.0 s wait_for bound | area: NET | -
- ASSUME | tests/test_ntp_fram_system_integration.py:326-328 | "1.0s, not a razor-thin 0.2s ... margin enough that scheduling jitter cannot produce a false failure" | Timing margin claim | area: TEST | related: TEST.T04
- SETTLED | tests/test_ntp_fram_system_integration.py:406-408 | "an unreachable NTP server is routine, handled inside the task (Part C.7.2) ... each restart costs 100 of 300 there" | NTP failures must never cost supervisor reboot budget; budget numbers (100 of 300) quoted here | area: CORE | -
- ASSUME | tests/test_ntp_fram_system_integration.py:443, 550, 614, 644 | "real wall-clock wait for start_and_check_tasks()'s own 2s poll" | Fixed 2.5 s waits against a 2 s supervisor poll | area: TEST | related: TEST.T04
- LIMIT | tests/test_ntp_fram_system_integration.py:504-509, 589-591 | "by tests a coverage audit found had never been called at all before" / "flagged SCD30 and SGP40 as the two Readers never driven through a real SystemService" | Coverage-audit findings; only BMP3xx, SCD30, SGP40 starters are driven through real start_and_check_tasks here | area: TEST | related: TEST.T15
- PLATFORM | tests/test_ntp_fram_system_integration.py:543-545 | "sleep(0) never advances wall-clock time on this Unix-port event loop" | Tests needing real sleeps inside drivers must use real sleeps | area: PLAT | -
- WORKAROUND | tests/test_ntp_fram_system_integration.py:148-150 | "redirects _NTP_UDP_PORT away from the real privileged port 123, and pre-resolves AsyUDPSocket's addr" | Unix-port-only workaround (privileged port; #6924 tuple rejection); removal trigger: none stated | area: TEST | -
- MIRROR | tests/test_ntp_fram_system_integration.py:56-58, 126-127 | "kept file-local rather than imported (no test file in this suite imports another, SPECIFICATION.md Part E's per-file self-containment convention)" | FakeNtpServer/_RedirectNtpNetworking and conn/ntp builders duplicated from test_ntp_wifi_dns_integration.py by convention | area: TEST | related: TEST.T08
- INVAR | tests/test_ntp_fram_system_integration.py:130-131 | "Below the OS ephemeral range (32768-60999)" | UDP port base 26000 disjointness is review-only; same dangling "TEST_PARALLELISM comment" pointer as test_captive_dns.py:30 | area: TEST | related: TEST.T06
- MIRROR | tests/test_ntp_fram_system_integration.py:370 | "past _NTP_WAIT_TIME (120s, one tick per uptime second)" | Test hardcodes 121 ticks against system_service's 120 s constant | area: TEST | -
- SUPPRESS | tests/test_ntp_fram_system_integration.py:28, 138, 163, 168, 173, 528, 596, 626 | "# type: ignore[misc]" / "[return-value]" / "[arg-type]" / "[assignment, misc]" / "[assignment]" | Module-level socket/SPI/bus monkeypatches | area: TEST | -

## tests/test_ntp_wifi_dns_integration.py
- SETTLED | tests/test_ntp_wifi_dns_integration.py:2 | "AsyNtpClient used to call get_dns_server_ip() after acquiring the shared wifi_mode_lock ... Fixed via _safe_get_dns_server(), called before acquiring the lock" | Ordering invariant: DNS-server lookup must happen before taking wifi_mode_lock | area: NET | -
- LIMIT | tests/test_ntp_wifi_dns_integration.py:3-5 | "No real port-53 or port-123 end-to-end test is attempted, both needing root and neither being CI-portable" | NTP/DNS real-port paths untested at this tier; note CLAUDE.md says test.sh grants CAP_NET_BIND_SERVICE via setcap for a real port-53 DNS-server test, so "needing root" is at least partly stale (low) | area: TEST | -
- LIMIT | tests/test_ntp_wifi_dns_integration.py:89-91 | "Bypasses the real wlan_connect() state machine, out of scope here" | WLAN connected state is set directly on the fake | area: TEST | -
- MIRROR | tests/test_ntp_wifi_dns_integration.py:41-44, 113-114 | "Narrows to Any once here, matching test_asy_wifi_service.py's helper" / "duplicated, not imported" | `_wlan()` and `_last_err()` helpers duplicated across files | area: TEST | related: TEST.T08
- PLATFORM | tests/test_ntp_wifi_dns_integration.py:77-78 | "One single f-string, not a plain-string-literal-adjacent-to-an-f-string concatenation - same MicroPython gotcha" | MicroPython string-concatenation gotcha with f-strings | area: PLAT | -
- ASSUME | tests/test_ntp_wifi_dns_integration.py:365-367 | "a real arping probe got zero responses from a DUT `iw station dump` called associated" (BACKLOG open question 6, closed 2026-09-04) | Single dated real-hardware finding (CYW43 false-positive link) reproduced at mock tier as "sent, nothing back" | area: NET | -
- SETTLED | tests/test_ntp_wifi_dns_integration.py:400-402 | "the silent timeout persisted as errno 21 - once for the whole run (C.7.1's repeat rule) while still counted every time" | NTP handles its own failures (C.7.2); persistence deduplicates repeats | area: NET | -
- WORKAROUND | tests/test_ntp_wifi_dns_integration.py:261-263 | "redirects _NTP_UDP_PORT away from the real privileged port 123, and pre-resolves AsyUDPSocket's addr" | Same Unix-port-only workaround as the NTP suites | area: TEST | -
- INVAR | tests/test_ntp_wifi_dns_integration.py:243-244 | "Below the OS ephemeral range (32768-60999)" | UDP base 25000; same dangling TEST_PARALLELISM pointer | area: TEST | -
- ASSUME | tests/test_ntp_wifi_dns_integration.py:216-217 | "_fetch_ntp_reply() blocks for its own _NTP_CONN_TIMEOUT (5s), giving this test a window" | Lock-held observation window depends on a 5 s src constant | area: TEST | -
- SUPPRESS | tests/test_ntp_wifi_dns_integration.py:142, 167, 251, 276, 284, 289 | "# type: ignore[assignment]  # deliberate monkeypatch" etc. | Resolver/socket monkeypatches | area: TEST | -
- LIMIT | tests/test_ntp_wifi_dns_integration.py:182-184 | "it degrades via self.pr.err(), debug-level only and never persisted" | A wlan.ifconfig() exception leaves no FRAM evidence (observation-tier query) | area: NET | -

## tests/test_print_log.py
- LIMIT | tests/test_print_log.py:186-187 | "errno=0 (_NO_ERR, the default) still bumps the counter, but _store_err returns before appending anything to history - a real, easy-to-miss asymmetry" | err_s() with the default errno counts but leaves no history entry | area: CORE | -
- LIMIT | tests/test_print_log.py:209-210 | "errno=200 pushed past _MAX_ERR (0x7F) once _NO_ERR is added - out of the valid error sub-range, so the count still increments but nothing is appended" | Out-of-range errnos are counted but invisible in history | area: CORE | -
- PLATFORM | tests/test_print_log.py:297-299 | "Empirically confirmed under the real MicroPython interpreter that append()/extend() on it are silent no-ops" | deque(maxlen=0) behaviour | area: PLAT | -
- PLATFORM | tests/test_print_log.py:307-309 | "deque(maxlen=...) raises ValueError on a negative maxlen (confirmed directly against the real MicroPython interpreter)" | Constructor clamps instead | area: PLAT | -
- PLATFORM | tests/test_print_log.py:317-323 | "`[x] * n`, what building this deque does internally, segfaults the whole process for some huge-but-representable n" | Uncatchable segfault gap between MemoryError and OverflowError ranges; the fix caps history_length before allocating (CLAUDE.md/Part F fact) | area: PLAT | -
- LIMIT | tests/test_print_log.py:331-336 | "cannot be forced deterministically through a real allocation at any size small enough to be safe in a test" | PrintLogHistory's MemoryError fallback is reachable only by substituting the module's `deque` name | area: TEST | -
- DRIFT | tests/test_print_log.py:379-380 | "(see BACKLOG.md - tests/_fram_mock.py and its flat, non-redundant abstraction are retired" | BACKLOG.md has no `_fram_mock` entry; dangling pointer | area: DOC | related: DOC.S05
- ASSUME | tests/test_print_log.py:461-466 | "Regression test for a real bug: _store_err()'s "not initialized" guard used to return early only when self.level > _LOG_OFF" | With logging off (the production case), a pre-setup err_s() used to overwrite FRAM history; pinned now | area: CORE | related: CORE.T11
- SETTLED | tests/test_print_log.py:477-479 | "SPECIFICATION.md Part C.7: reset() deliberately has no "uninitialized" guard" | A reset persists immediately so a later setup() cannot restore the old history | area: CORE | -
- INVAR | tests/test_print_log.py:490-492 | "the webserver can answer a ResetErrors PUT before that has happened. The reset must survive the setup() that follows it" | Boot window: ResetErrors may land before a logger's own pr.setup() | area: CORE | related: CORE.T11
- INVAR | tests/test_print_log.py:512-513 | "claiming initialization on a FAILED write would make the later setup() return early, leaving a logger that believes it is persisted and is not" | reset() must only mark initialized on a successful write | area: CORE | -
- PLATFORM | tests/test_print_log.py:540-542 | "MicroPython's struct defaults a no-prefix format to "@", native alignment and padding, not "<"" | On-chip layout pins "<H"; the FRAM byte format is part of the persisted contract | area: PLAT | -
- ASSUME | tests/test_print_log.py:580-582, 590-592 | "AsyFramManager.get_chunk() never actually raises (confirmed by its own src/ promotion audit)" | Same past-audit claim as test_base_classes.py:682-696; the defensive paths are exercised only via a Protocol fake | area: STOR | -
- MIRROR | tests/test_print_log.py:43-45 | "A minimal local fake, not a full FRAM simulation" | Source of the raising-fake pattern copied into test_base_classes.py | area: TEST | related: TEST.T08
- SUPPRESS | tests/test_print_log.py:13, 345, 349 | "# type: ignore[misc]" / "# type: ignore[assignment,misc]" | `_SPI` swap; `deque` substitution | area: TEST | -

## tests/test_reset_call_site_invariant.py
- INVAR | tests/test_reset_call_site_invariant.py:15-26 | "any other call site would bypass storage_pause()/the _RESET_DELAY wait this invariant relies on" | Reset/bootloader confinement to system_service.py, enforced by substring scan of `src/` only | area: CORE | covered-by: TEST.S17
- DRIFT | tests/test_reset_call_site_invariant.py:1-3, 30-45 | "WDT() is constructed exactly once per sensortask_<device>.py entry point" | `src/` has no `sensortask_*.py` (generated at build time), so the exemption branch is dead and "exactly once per entry point" is never asserted; the test only checks absence elsewhere in src/ | area: CORE | covered-by: TEST.S17
- SETTLED | tests/test_reset_call_site_invariant.py:30-31 | ""must be hardcoded so no error ever can circumvent it when it is set active" - the owner's comment" | Owner decision: WDT construction only at each device's entry point | area: CORE | -
- ASSUME | tests/test_reset_call_site_invariant.py:7 | "scripts/test.sh always invokes tests from the repo root" | Relative `src` path depends on cwd | area: TEST | -

## tests/test_sensortask_arzi.py
- INVAR | tests/test_sensortask_arzi.py:1-2 | "one of six wrappers over the shared tests/_sensortask_scenarios.py library (SPECIFICATION.md Part E.2.1)" | The six per-device wrappers are hand-added (unlike test_bus_hazard_generated.py's auto-discovery); a 7th device needs a new wrapper file, and nothing enforces it (scripts/test.sh:392-415 only lists them for scheduling) | area: TEST | related: TEST.S09
## tests/test_sensortask_dev.py
- MIRROR | tests/test_sensortask_dev.py:1-11 | "one of six wrappers" | Identical to the other five apart from the device name (see arzi item) | area: TEST | -
## tests/test_sensortask_grkizi.py
- MIRROR | tests/test_sensortask_grkizi.py:1-11 | "one of six wrappers" | Identical wrapper (see arzi item) | area: TEST | -
## tests/test_sensortask_klkizi.py
- MIRROR | tests/test_sensortask_klkizi.py:1-11 | "one of six wrappers" | Identical wrapper (see arzi item) | area: TEST | -
## tests/test_sensortask_schlafzi.py
- MIRROR | tests/test_sensortask_schlafzi.py:1-11 | "one of six wrappers" | Identical wrapper (see arzi item) | area: TEST | -
## tests/test_sensortask_wozi.py
- MIRROR | tests/test_sensortask_wozi.py:1-11 | "one of six wrappers" | Identical wrapper (see arzi item); the scenario bodies live in tests/_sensortask_scenarios.py (not this partition) | area: TEST | related: TEST.S08, TEST.S09

## tests/test_setter_microdot_integration.py
- MIRROR | tests/test_setter_microdot_integration.py:8-10 | "any of its wiring that must be exercised is reimplemented locally, never imported" | Route wiring from src/asy_webserver_service.py and the generated device module is re-implemented in the test; drift from production is not detected | area: REST | -
- SETTLED | tests/test_setter_microdot_integration.py:19-21 | "scripts/test.sh's MICROPYPATH deliberately excludes ext/, and changing that would be a scripts/ change needing a full clean-chroot re-verification" | Per-file `sys.path.insert(0, "ext")` (also tests/test_website_build_integration.py:13) instead of changing MICROPYPATH | area: TEST | -
- TODO | tests/test_setter_microdot_integration.py:24-25 | "ext/ isn't on this project's mypy search path yet (see pyproject.toml's [tool.mypy]) - same gap as src/asy_webserver_service.py's own import" | microdot imports are unchecked by mypy; suppressed with import-not-found | area: CI | -
- SUPPRESS | tests/test_setter_microdot_integration.py:27 | "# type: ignore[import-not-found]" | See TODO above | area: TEST | -
- MIRROR | tests/test_setter_microdot_integration.py:99-105 | "_wifi_field_schema() below mirrors that scoping locally, this file never importing the generated device module" | setNetwork/setWiFiLED SettingsGroup scoping (post_fct only on the four network fields) is copied from buildgen output | area: REST | -
- SETTLED | tests/test_setter_microdot_integration.py:193-194 | "Final project decision: an unrecognized field key ... is just another per-field "Invalid" outcome" | Same decision as test_base_classes.py:1664 | area: REST | -
- INVAR | tests/test_setter_microdot_integration.py:253-254 | "toggling the WiFi status LED must never reconnect the WiFi connection" | setWiFiLED passes no post_fct | area: NET | -
- LIMIT | tests/test_setter_microdot_integration.py:276-277 | "No real TCP socket is opened: Request is constructed directly" | Microdot parsing from a socket stream is not exercised here | area: TEST | -
- ASSUME | tests/test_setter_microdot_integration.py:505-510 | "asy_ntp_client.py's module docstring claims base_classes.py's generic _set_dict_cfg() gives full setter support" | The NTP setter path is proven only through a test-local route shaped like the real handler | area: NET | -
- SETTLED | tests/test_setter_microdot_integration.py:640-646 | "SGP40's whole setter surface is bus-independent" | No I2C in the SGP40 REST path; SGPResetVOC only arms RAM flags for read_loop() | area: SENS | -
- RISK | tests/test_setter_microdot_integration.py:660-669 | "A broken persistence layer is therefore invisible to base_classes.py's "persisted" check: the response reports the ordinary Valid outcome" | Since WP5's deferred flush, a PUT whose flash write will fail still returns 200/"Valid"; the failure surfaces only later as a logged errno | area: REST | related: CORE.T12
- DRIFT | tests/test_setter_microdot_integration.py:4-6, 688-697, 709-710 | "the one sensor whose REST surface is hand-rolled per field instead of schema-driven" / "exactly as in the real file" / "the real generated module builds this once" | The SCD30 section never calls `SCD30_Reader._set_dict_cfg()`; it re-implements a local dispatch, while src/asy_scd30_driver.py:257-289 now holds a "Schema-driven setter" dispatch; the test's local field schemas (defaults 2/0/400, :700-704) also differ from src's `def=None` (`src/asy_scd30_driver.py:58-61`) | area: TEST | -
- LIMIT | tests/test_setter_microdot_integration.py:692-693 | "only the three fields this file exercises are mirrored, not all seven" | SCD30 REST coverage here spans 3 of 7 fields | area: TEST | -
- ASSUME | tests/test_setter_microdot_integration.py:695-697 | "Every SCD30 setter already returns bool and never raises (SPECIFICATION.md Part C)" | Contract assumption behind the plain bool mapping | area: SENS | -
- PLATFORM | tests/test_setter_microdot_integration.py:701, 817 | "special=0 matches SCD30's own documented AmbPres=0 "disable compensation" bypass value" | Datasheet fact | area: SENS | -
- INVAR | tests/test_setter_microdot_integration.py:709-710, 783-785 | "iterated in a fixed order, which the one-shot bus fault below relies on" | The fault-injection test depends on dispatch order (tests/machine.py inject_fault is a FIFO) | area: TEST | -

## tests/test_strict_json.py
- PLATFORM | tests/test_strict_json.py:1-2, 56 | "rejects each separator slip the interpreter's own lenient json.loads() lets through" | MicroPython json.loads accepts invalid JSON; tests/_strict_json.py is the oracle the suite relies on | area: PLAT | related: TEST.T17
- RISK | tests/test_strict_json.py:86-88 | "json.dumps() never raises here, where CPython would ... A route that lets a non-finite value through therefore ships a body the browser rejects, silently" | inf/NaN in a REST response dict produces a body no browser parser accepts; pinned so a version bump surfaces a change | area: REST | -
- PLATFORM | tests/test_strict_json.py:97 | "bytes, dumped as a string rather than refused" | json.dumps(b"x") == '"x"' on MicroPython | area: PLAT | -

## tests/test_system_service.py
- ASSUME | tests/test_system_service.py:77-79 | "a single sleep(0) not always being enough to drain a multi-await iteration" | `_pump()` uses 5 sleep(0) yields per tick; a loop iteration with more awaits could outrun it | area: TEST | related: TEST.T04
- PLATFORM | tests/test_system_service.py:104-109, 576-578, 672-674, 789-791, 849-851 | "Real rp2 Timer(period=..., ...) can raise OSError(ENOMEM) under alarm-pool exhaustion (confirmed against ports/rp2/machine_timer.c)" | Every Timer arm site guards OSError and MemoryError; the fake's `raise_on_arm` models it | area: PLAT | related: PLAT.T03
- PLATFORM | tests/test_system_service.py:141-142 | "Bound-method identity isn't guaranteed (each attribute access can mint a fresh bound-method object)" | Runtime fact affecting identity-based tests | area: PLAT | -
- SETTLED | tests/test_system_service.py:194-196, 1053-1055 | "_force_watchdog_starve is _reboot()'s one-way "let the hardware watchdog do it instead" signal" | When the reset timer cannot arm, the supervisor stops feeding the WDT | area: CORE | related: XCUT.T13
- PLATFORM | tests/test_system_service.py:278-280 | "MicroPython's real `time` module is a read-only builtin (assigning time.mktime raises AttributeError)" | Tests must patch the importing module's `time` name | area: PLAT | -
- RISK | tests/test_system_service.py:428-429 | "each retry logged its own failure - bounded by print_log.py's own history/count caps" | A persistently raising NTP callback logs via err_s (errno=1, `src/system_service.py:138`) on every uptime tick until the 120 s fallback: 120 persisted entries per boot | area: CORE | -
- SETTLED | tests/test_system_service.py:450-452 | "the value must stay perfectly stable for the rest of this boot once resolved - never re-picked, never "upgraded" from random to NTP" | Boot signature resolves once per boot; outside observers detect reboots by change | area: CORE | related: CORE.S01
- PLATFORM | tests/test_system_service.py:527-532 | "Regression test for a real GC-drop bug: _timer_sequencer() built a fresh, unstored Timer per chain step" | F.1's soft-Timer GC-drop gotcha; timers must be preallocated and referenced | area: PLAT | -
- MIRROR | tests/test_system_service.py:623, 754, 761, 1237-1239 | "_RESET_DELAY: micropython.const(), compiled away, hardcoded per SPECIFICATION.md Part E.5.1" | Tests hardcode 4 s reset delay, 3600 s max storage pause, `_TASK_FAIL_MAX` 300 (+100 per restart), `_TASK_CHECK_TIME` 2 s | area: TEST | -
- SETTLED | tests/test_system_service.py:849-851 | "owner-confirmed design: unlike reboot_system()'s reset_timer guard, this degrades gracefully rather than forcing a reboot" | Uptime-timer arm failure → no uptime, no reboot, logged via non-persisting pr.err() (no FRAM evidence) | area: CORE | -
- INVAR | tests/test_system_service.py:1008-1010 | "The supervisor underneath is the run phase, where I.4 forbids one - so the count must not move once spinning" | Boot-confined gc.collect() (I.4(f.1)) enforced by counting collects via a fake `gc` module | area: MEM | -
- PLATFORM | tests/test_system_service.py:1133-1135 | "MicroPython's asyncio Task has no .exception()/.result()" | Why `_log_dead_task()` exists | area: PLAT | -
- ASSUME | tests/test_system_service.py:1168-1173 | "Regression test for the real "wrnno=10" bench-hardware bug: _log_dead_task()'s CancelledError branch used to log via the non-persisting self.pr.err()" | Single dated bench finding; CancelledError deaths now persist errno=6 | area: CORE | -
- LIMIT | tests/test_system_service.py:1291-1293 | "The one branch in setup() no other test reaches: get_int_values() answering None" | Corrupt system-settings store keeps the constructed debug level | area: CORE | -
- DRIFT | tests/test_system_service.py:1413-1414 | "exactly what sensortask_wozi.py's _collect_level_setters() does" | Names a retired hand-written module; the behaviour now lives in generated code | area: DOC | related: TEST.S24
- SUPPRESS | tests/test_system_service.py:16, 96, 294, 318, 486, 982, 1304 | "# type: ignore[misc]" / "[assignment]" / "[method-assign]" / "[method-assign, assignment]  # deliberate monkeypatch" | Module/method monkeypatches | area: TEST | -
- ASSUME | tests/test_system_service.py:1370-1371 | "WP8: every other caller-supplied-callback call site in this codebase already persists via err_s()" | Codebase-wide consistency claim made from a retired work-package pass | area: CORE | -

## tests/test_ticks_rollover.py
- PLATFORM | tests/test_ticks_rollover.py:1, 21-23, 99-100 | "rp2's 2**30 vs. this Unix-port rig's 2**62 period" | rp2 ticks wrap at 2**30 ms (~12.4 days); the unit tier runs at 2**62, so no test here exercises the real rp2 boundary; the rig period is discovered by bisection | area: PLAT | related: XCUT.T25
- PLATFORM | tests/test_ticks_rollover.py:25-27 | "time.ticks_add()'s accepted-delta range is exactly [-period/2, period/2), confirmed against extmod/modtime.c" | Delta ≥ period/2 raises OverflowError | area: PLAT | related: XCUT.T25
- WORKAROUND | tests/test_ticks_rollover.py:32-35 (9 sites :35-89) | "Stub gap: typings/time.pyi types ticks_add()'s first parameter as the opaque _Ticks TypeVar, excluding plain int" | Stub defect worked around with `type: ignore[type-var]`; removal trigger: none stated | area: TEST | -
- ASSUME | tests/test_ticks_rollover.py:2 | "Every real src/ ticks_ms()/ticks_diff() use site shares the same bounded-short-timeout shape" | The test enforces only "no raw subtraction"; the bounded-short claim is not checked, and stored-ticks sites contradict it | area: CORE | covered-by: DOC.S23
- LIMIT | tests/test_ticks_rollover.py:98-110 | "its absence next to a subtraction is the thing to catch" | The subtraction scan is a per-line heuristic over `src/` only: a `now - t0` on a line without `ticks_`, generated `sensortask_*.py`, and digital_twin/ are not scanned | area: TEST | related: XCUT.T25
- INVAR | tests/test_ticks_rollover.py:8-18, 113-126 | "Named explicitly so a module that silently stops using ticks - or a new one that starts - is visible here" | `_KNOWN_TICKS_USERS` hand list (6 modules), enforced both ways by the test itself | area: TEST | -

## tests/test_tmp_scratch.py
- SETTLED | tests/test_tmp_scratch.py:165-178 | "This replaces a test that populated the shared root with 400,000 real sibling directories ... at a measured 396MB of physical disk writes per run" | Structural invariant (no TmpScratch op reads tests/_tmp's shared root) replaces brute force, per CLAUDE.md's host-wear rule | area: TEST | -
- INVAR | tests/test_tmp_scratch.py:195-196 | "mkdir(_ROOT) is the one legitimate touch of the root itself: idempotent, EEXIST-swallowed, and what makes concurrent construction from several test processes safe" | Concurrent-process safety of the scratch root | area: TEST | -
- INVAR | tests/test_tmp_scratch.py:81-83 | "the actual mechanism that used to make a "Valid" write silently read back as "Unchanged"" | Construction wipes the whole key subtree to kill stale leftovers; hence two concurrently running files sharing one key would wipe each other, so keys must stay disjoint (E.1, review-only) | area: TEST | related: TEST.T06
- SUPPRESS | tests/test_tmp_scratch.py:87-88, 208-209, 214-215, 230-231 | "except OSError: pass" | Cleanup errors swallowed in test helpers | area: TEST | -
- SUPPRESS | tests/test_tmp_scratch.py:182 | "# type: ignore[assignment]" | `os` binding swap inside _tmp_scratch | area: TEST | -

## tests/test_uart_comm_hazard.py
- SETTLED | tests/test_uart_comm_hazard.py:48-50 | "Standing rule (project owner, 2026-09-12): every check runs both with and without a CRC - the deployed link is CRC_Pass" | Every check is registered in both CRC modes except the two mode-specific payload-corruption checks (:1271-1277) | area: UART | -
- MIRROR | tests/test_uart_comm_hazard.py:33-45 | "_CMD_ACK = 0x01 / _CMD_GET = 0x02 / _CMD_SET = 0x04 ... _FRAME = 5 + _PAYLOAD" | Wire constants and field offsets hand-copied from src/asy_uart_comm.py's `const()`s (Class A contract values); drift is not detected | area: UART | related: UART.T01
- ASSUME | tests/test_uart_comm_hazard.py:30-32 | "every value still clears the module's own floor of 2 x poll_wait_ms + poll_idle_ms plus the worst-case GC pause - 24ms here" | The 30 ms tier timeout rests on the measured worst-case GC pause | area: UART | related: UART.T10
- ASSUME | tests/test_uart_comm_hazard.py:62-64, 68-70 | "measured as transactions timing out at this tier's deliberately tiny 30ms" / "at 1x the no-CRC arm sits 1.25x over the 24ms floor, well inside the scheduling gap scripts/test.sh's own 16-way oversubscription produces" | Timeout budgets (×8 for CRC and sustained runs) are sized from measurements under test.sh's parallelism; derivation in Part J.7 | area: TEST | related: TEST.T04
- SETTLED | tests/test_uart_comm_hazard.py:207-208, 625-626 | "Simultaneous initiation is out of contract - there is no arbitration anywhere in the design" | Tests prove detection and recovery, never that it works | area: UART | -
- INVAR | tests/test_uart_comm_hazard.py:187-188 | "The unbounded listen wait holds the bus lock, so this is the only safe interruption" | clear() is the only safe way to unstick a parked listener | area: UART | related: UART.T09
- ASSUME | tests/test_uart_comm_hazard.py:490-492 | "With it raised, 120/120 complete with zero errors in both CRC modes, so the shortfall was the harness's" | Single measurement behind the 3-rounds-per-transaction listen budget | area: TEST | -
- ASSUME | tests/test_uart_comm_hazard.py:502-515, 1014-1017, 1059-1063 | "gc.collect()" | Eight gc.collect() calls bracket gc.mem_alloc() samples in the heap-retention/hammer measurements; measurement-only, not a MemoryError prop, but they sit inside tests that must pass at gc.threshold(-1) (low) | area: TEST | related: TEST.T03
- ASSUME | tests/test_uart_comm_hazard.py:533-535, 1029-1034, 1055-1057, 1073-1078 | "0 B locally, 64 B and 288 B on two runners" / "~3.4kB ... Measured constant at 10, 30, 60 and 120 failures" / "~114 B/failure" | Heap-rate bounds (< one frame, < 6 B/tx, < 16 B/failure) rest on dated host measurements | area: MEM | related: TEST.S12
- LIMIT | tests/test_uart_comm_hazard.py:539-541 | "every test above asserts ErrCount, none ErrNum, so a fault reporting the wrong code would pass the whole suite" | Errno-specific coverage exists only in the later catalog section | area: TEST | -
- PLATFORM | tests/test_uart_comm_hazard.py:642-644, 866-868 | "A framing/parity/overrun fault never raises on rp2 (SPECIFICATION.md Part C.3.2)" | Electrical faults reach the protocol only as dropped/duplicated/delayed bytes or 0x00 runs | area: PLAT | -
- RISK | tests/test_uart_comm_hazard.py:705-707, 741-743 | "with no CRC configured, a bit flip in the payload passes every structural check and reaches the caller as good data" | Documented property of the deployed CRC_Pass configuration: payload corruption is undetected | area: UART | covered-by: UART.S04
- INVAR | tests/test_uart_comm_hazard.py:745-746, 766-767 | "a transaction that times out returns None here too, which would read as "the corruption was caught" and quietly retire the claim" | Corruption tests must use the sustained budget or pass vacuously | area: TEST | related: TEST.T01
- DRIFT | tests/test_uart_comm_hazard.py:784-785 | "The module refuses the configuration instead (B17)" | Bare changelog-row ID; B17 lives in UART_C_PORT_CHANGELOG.md:88, a file slated for deletion at reconciliation (low) | area: DOC | related: DOC.S14
- SETTLED | tests/test_uart_comm_hazard.py:796-798 | "parameters are agreed out of band and never negotiated, so a pair configured differently is diagnosed (errno 32), never recovered" | Owner decision (J.6) | area: UART | -
- SETTLED | tests/test_uart_comm_hazard.py:854-856 | "Pins the known blind spot, not the desired behaviour: errno 32 never fires here ... Accepted rather than fixed (SPECIFICATION.md Part J.6); this inverts if it is" | Test pins a known limitation: mismatch on this path reports as generic errno 22 | area: UART | -
- RISK | tests/test_uart_comm_hazard.py:1108-1110 | "a lost one leaves the peer having accepted the whole train while this side reports failure. A caller that retries on False must tolerate that" | At-least-once delivery seam | area: UART | covered-by: UART.T08
- MIRROR | tests/test_uart_comm_hazard.py:1223-1225 | "the C peer appends its own CRC in the platform's NATIVE order and is deliberately not wire-compatible with this one (SPECIFICATION.md Part J, UART_C_PORT_CHANGELOG.md A7)" | Python↔C byte-order divergence pinned big-endian here | area: UART | related: UART.S04
- INVAR | tests/test_uart_comm_hazard.py:1244-1246 | "gc.threshold() is global, so each body restores it" | The hammer checks run at both -1 and 32768 inside one process, so the (e) stage's -1 run also executes a 32768 phase here | area: MEM | related: TEST.T18
- INVAR | tests/test_uart_comm_hazard.py:527, 602-603, 1121-1123 | "hazard_pair(crc) is built out here (its asyncio.run() cannot nest)" | No-nested-asyncio.run rule applied to hazard_pair()/errnos()/_clean_ack_bytes() | area: TEST | related: TEST.T06
- INVAR | tests/test_uart_comm_hazard.py:23-24, 50 | "CRC_Base carrying state the two ends must not share" | A CRC instance must never be shared between link ends | area: UART | -
- LIMIT | tests/test_uart_comm_hazard.py:1092-1093 | "the three cases the systematic sweep over the general UART failure taxonomy found uncovered" | Lost final ACK, peer reboot mid-train, and mid-frame reconnect were late additions | area: TEST | -
- SUPPRESS | tests/test_uart_comm_hazard.py:530, 1003, 1044 | "fake.log.append = lambda entry: None  # type: ignore[method-assign]" | Fake recorders muted so heap numbers are src/'s alone | area: TEST | -

## tests/test_voc_algorithm.py
- PLATFORM | tests/test_voc_algorithm.py:90-91, 103-104 | "Datasheet Table 1: VOC Index output range is 1-500" / "datasheet SRAW_VOC is 0-65535 ticks; the algorithm's own valid processing window is narrower" | Datasheet facts; blackout is `<=` so processing starts at call 46 | area: ALGO | -
- LIMIT | tests/test_voc_algorithm.py:127-132, 143-145 | "only reached once the internal variance estimate has grown large" | Several estimator branches are reachable only with adversarial sustained input, found by tracing | area: ALGO | related: ALGO.T02
- SETTLED | tests/test_voc_algorithm.py:238-244 | "not Sensirion's own get_states()/set_states(), which carry mean and std only, but a full 32-field dump and restore" | Reboot survival uses a full-state dump; a restore also advances state by one sample | area: ALGO | related: ALGO.T05
- LIMIT | tests/test_voc_algorithm.py:315-321 | "only reached with a negative operand ... leaving them exercised only via process()'s internal calls" | `_fix16_mul` negative branches were previously untested directly | area: ALGO | -
- MIRROR | tests/test_voc_algorithm.py:360-361 | "Values from the C reference's own overflow guards (x >= f16(10.3972) -> FIX16_MAXIMUM, x <= f16(-11.7835) -> 0)" | Constants copied from the Sensirion C reference, which is not in the repo | area: ALGO | related: ALGO.T02, ALGO.T07
- ASSUME | tests/test_voc_algorithm.py:368-373, 379-381 | "the one value whose absolute magnitude does not fit back into a signed 32-bit remainder" | FIX16_MINIMUM division edge cases, compared mod 2**32; Python ints do not wrap like C int32 | area: ALGO | related: ALGO.S01, ALGO.S06
- INVAR | tests/test_voc_algorithm.py:445-446 | "asy_sgp40_driver.py's _run_restore() never calls unpack_from() at all once read_into() has failed" | Restore must short-circuit on a failed FRAM read | area: SENS | -
- PLATFORM | tests/test_voc_algorithm.py:531-533 | "MicroPython's struct.pack_into() raises ValueError for a negative offset, unlike CPython's" | Caught by pack_into()'s try/except | area: PLAT | -
- LIMIT | tests/test_voc_algorithm.py:547-549 | "_vocalgorithm_set_tuning_parameters() has no caller anywhere in this codebase today" | Dead, Sensirion-mirroring API kept on purpose; smoke-tested only | area: ALGO | related: CORE.T10
- DRIFT | tests/test_voc_algorithm.py:552 | "not a claim that any real caller exercises it (see BACKLOG.md)" | BACKLOG.md has no entry about set_tuning_parameters; dangling pointer | area: DOC | related: DOC.S05
- SUPPRESS | tests/test_voc_algorithm.py:14 | "# type: ignore[misc]" | See partition-wide `_SPI` swap aggregate | area: TEST | -

## tests/test_website_build_integration.py
- INVAR | tests/test_website_build_integration.py:5-7 | "scripts/test.sh builds it first; the import mounts /html once per process" | Depends on test.sh having built frozen_modules/frozen_html.py for wozi before this file runs; only one device's build is tested | area: WEB | -
- SUPPRESS | tests/test_website_build_integration.py:15-16, 50 | "# type: ignore[import-not-found]  # noqa: F401  # mounts /html on import" / "# type: ignore[no-any-return]" | Side-effect import, unchecked microdot import | area: TEST | -
- WORKAROUND | tests/test_website_build_integration.py:42-44 | "No `with`: the real object supports it but the stubs don't declare __enter__/__exit__ (the same stub-gap class as Timer()/I2C.deinit())" | Stub gap for DeflateIO; gzip header auto-detect "confirmed on v1.29.0"; removal trigger: none stated | area: PLAT | -
- MIRROR | tests/test_website_build_integration.py:73-75, 102-103, 119-128 | "The seven production modules are concatenated into one js/app.js at staging time (Part H.7)" | The test hand-lists the seven js modules and their distinctive declarations; a new js module needs a manual update here | area: WEB | -
- LIMIT | tests/test_website_build_integration.py:132-137 | "A leftover `export { ... } from "./local-file.js";` re-export ... is not caught by the import-line check above - checked directly after a real instance ... was caught only by manually tracing the build" | The bundle's integrity is checked by string patterns, each added after a manual find | area: WEB | -

## Coverage

| file | comment/doc lines read | items |
| --- | --- | --- |
| tests/test_base_classes.py | 323 | 30 |
| tests/test_bus_hazard_generated.py | 30 | 7 |
| tests/test_bus_hazard_multi_device.py | 86 | 13 |
| tests/test_captive_dns.py | 283 | 19 |
| tests/test_config_manager.py | 523 | 38 |
| tests/test_crc_checks.py | 147 | 9 |
| tests/test_fake_timer_and_network.py | 13 | 5 |
| tests/test_fram_integration.py | 101 | 9 |
| tests/test_framing_codecs.py | 36 | 3 |
| tests/test_machine_uart_link.py | 35 | 6 |
| tests/test_math_helpers.py | 73 | 8 |
| tests/test_neopixel_wifi_integration.py | 12 | 2 |
| tests/test_notification_fram_integration.py | 29 | 3 |
| tests/test_notification_neopixel_integration.py | 25 | 3 |
| tests/test_notification_scd30_integration.py | 59 | 7 |
| tests/test_notification_scd30_sgp40_integration.py | 49 | 5 |
| tests/test_notification_sgp40_integration.py | 51 | 6 |
| tests/test_ntp_fram_system_integration.py | 149 | 11 |
| tests/test_ntp_wifi_dns_integration.py | 97 | 12 |
| tests/test_print_log.py | 152 | 15 |
| tests/test_reset_call_site_invariant.py | 13 | 4 |
| tests/test_sensortask_arzi.py | 2 | 1 |
| tests/test_sensortask_dev.py | 2 | 1 |
| tests/test_sensortask_grkizi.py | 2 | 1 |
| tests/test_sensortask_klkizi.py | 2 | 1 |
| tests/test_sensortask_schlafzi.py | 2 | 1 |
| tests/test_sensortask_wozi.py | 2 | 1 |
| tests/test_setter_microdot_integration.py | 222 | 16 |
| tests/test_strict_json.py | 9 | 3 |
| tests/test_system_service.py | 259 | 17 |
| tests/test_ticks_rollover.py | 48 | 6 |
| tests/test_tmp_scratch.py | 42 | 5 |
| tests/test_uart_comm_hazard.py | 259 | 23 |
| tests/test_voc_algorithm.py | 133 | 11 |
| tests/test_website_build_integration.py | 42 | 5 |
| (partition-wide aggregates, cross-file) | - | 8 |

All 35 files read in full via the comment dump (3312 lines), plus code-level greps for suppressions, swallowed exceptions, early returns, gc calls and the keyword families; surrounding code opened where needed. Nothing unreadable.

## Totals per kind

| kind | items |
| --- | --- |
| INVAR | 56 |
| LIMIT | 55 |
| ASSUME | 40 |
| PLATFORM | 39 |
| SETTLED | 31 |
| MIRROR | 30 |
| SUPPRESS | 29 |
| DRIFT | 16 |
| RISK | 11 |
| WORKAROUND | 6 |
| OPENQ | 1 |
| TODO | 1 |
| **total** | **315** |
## Top 10
1. DRIFT `tests/test_fram_integration.py:3-5`: "Real RP2040 SPI write()/readinto() cannot raise" contradicts F.5.2's 1.29 `OSError(EIO)` on 32+ byte SPI reads, so the FRAM chain is never tested against an SPI-level fault on stale grounds.
2. DRIFT/LIMIT `tests/test_setter_microdot_integration.py:4-6, 688-710`: the "real Microdot end to end" SCD30 section never calls `SCD30_Reader._set_dict_cfg()` (now schema-driven in `src/asy_scd30_driver.py:257-289`); it tests a local re-implementation whose field defaults differ from src.
3. RISK `tests/test_setter_microdot_integration.py:660-669`: since WP5's deferred flush, a PUT whose flash write fails still answers 200/"Valid"; the failure is visible only as a later errno.
4. RISK `tests/test_config_manager.py:2259-2261`: a mid-`json.dump()` failure leaves an unparseable config file on flash, and resubmitting the same value is "Unchanged" and writes nothing.
5. SETTLED `tests/test_uart_comm_hazard.py:854-856`: a test pins a known blind spot (mismatched peer reports errno 22, not 32), "accepted rather than fixed"; alongside `:741-743` (undetected payload corruption under the deployed CRC_Pass).
6. LIMIT/PLATFORM `tests/test_ticks_rollover.py:1, 21-23, 98-110`: the rig's tick period is 2**62, not rp2's 2**30, and the no-raw-subtraction guard is a per-line heuristic over `src/` only.
7. RISK/PLATFORM `tests/test_config_manager.py:347-357`: int→float blanket accept is exact only up to the mantissa (24 bits on RP2040), and the unit tier cannot reproduce the single-precision threshold.
8. RISK `tests/test_system_service.py:428-429`: a persistently raising NTP callback persists an `err_s` entry on every uptime tick, i.e. 120 per boot.
9. RISK `tests/test_strict_json.py:86-88`: MicroPython `json.dumps()` emits inf/NaN without raising, so a route that lets one through silently ships a body no browser accepts.
10. LIMIT `tests/test_captive_dns.py:327-333, 800-806`: on the Unix port a real server socket never yields a string `addr[0]`, so the captive-DNS reply path over a real socket is untested at this tier.
