# A-C merge TEST_UNIT (HEAD b07fa6e)

Scope: CLUSTERS.md "## TEST_UNIT" — the L1 unit-test files of `tests/` (51 paths, 255 action-site pairs in
`site_index.json`), not the twin tests and not the `tests/_*` helpers/fakes (TWIN, TEST_HELP). Each file's constituents
are the index's actions plus every action whose Site, Change or Blast slot names the file (grep of `audit/actions/*.md`,
brief step "Inputs"); a product action whose Blast names a test change in one of these files is merged here as that
test change (the product clusters carry those items as "→ A-ID (TEST_UNIT)").

**Conventions used by every merged change below.**

- Line numbers are HEAD `b07fa6e` (`git diff ff2e004 b07fa6e -- tests/` is empty: the audit commits since the A-L
  close touch `audit/` only).
- **File renames** (A.U10.37, "their test files `tests/test_<old>.py` → `tests/test_<new>.py`"): the eight renamed
  modules take their test files with them — `test_api_response.py` → `test_asy_api_response.py`, `test_base_classes.py`
  → `test_asy_base_classes.py`, `test_captive_dns.py` → `test_asy_captive_dns.py`, `test_config_manager.py` →
  `test_asy_config_manager.py`, `test_crc_checks.py` → `test_asy_crc_checks.py`, `test_framing_codecs.py` →
  `test_asy_framing_codecs.py`, `test_print_log.py` → `test_asy_print_log.py`, `test_system_service.py` →
  `test_asy_system_service.py`. The rename lands in U10 (`git mv`, imports and `<old>.` attribute references in every
  test file follow); every later merged change on those files is written against the new name and applies to the
  renamed file. Section headings below keep the HEAD path so the ledger maps to the index.
- **Harness migration, per file** (U24): `run()`/`run_timed()`/`_cancel*` → `tests/_async_harness.py` (A.U24.08, the
  bounded copies keep their bound: `run(coro, <limit>)`); shared doubles `_RaiseOnArm`/`_FastAsyncSleep`/`_FakeTime`/
  `_OverflowingTime`/`_tick`/`make_fram_manager`/`make_ntp_reply`/`FakeNtpServer` → `tests/_fake_timer_arm.py`,
  `_fast_sleep.py`, `_fake_time.py`, `_fram_builders.py`, `_ntp_frames.py` (A.U24.49, A.U24.76); file-local doubles and
  builders take the private role names `_Fake…`/`_Recording…`/`_Raising…`/`_make_…` (A.U24.76); folded product
  `const()` mirrors read with `tests/_src_const.py` (A.U24.01); `.cfg_schema` → `.get_cfg_schema()` (A.U24.61);
  `inject_fault(op, OSError(errno.X, "m"), times=n)` → `inject_fault(op, OSError, errno.X, "m", times=n)` (A.U24.78);
  bus lock attribute `async_lock` → `bus_lock`, device-session `asy_lock` → `session_lock` (A.U10.18); log expectations
  by catalog name `code("E"|"W", <NAME>)` from `tests/_error_codes.py` (A.U2.03) and the newest-entry rule (A.U3.01,
  A.U3.12). Each file's merged change names which of these apply; the mechanics are not repeated.
- **U10 rename sweep, per file** (mechanical, landing with each rename in U10, checked by the renaming action's own
  grep/typecheck method): module names (A.U10.37), class names (A.U10.38: e.g. `BMP3xx_Reader` → `BMP3XX_Reader`,
  `AsyFramManager` → `FRAMManager`, `AsyConnTime` → `WifiService`, `AsyNtpClient` → `NTPClient`, `AsyUDPSocket` →
  `UDPSocket`, `UART_Comm` → `UARTComm`, `UartLinkExerciser` → `UARTLinkDriver`, `DNSServer` → `CaptiveDNS`,
  `CRC_*`/`Framing_*` → `CRC*`/`Framing*`), test-read attributes made private (A.U10.35), lock names (A.U10.18:
  `asy_lock` → `session_lock`, `async_lock` → `bus_lock`, `config_lock` → `_config_lock`, `network_available` →
  `network_available_locked`), REST/config keys (A.U10.40's map, e.g. `SampleInterv` → `SampleInterval`,
  `PressOvers` → `PresOvers`, `PressOffset` → `PresOffset`, `SeaLevelOffs` → `SeaLevelOffset`, `MeasInt` →
  `MeasInterval`, `TempOffs` → `TempOffset`, `NTP_Host` → `NTPHost`, `LedWifiOn` → `LEDWifiOn`, `lightCmdLED` →
  `LightCmdLED`), unit suffixes (A.U10.43: `set_trigger_secs` → `set_trigger_s`, `trigger_sec` → `trigger_s`),
  starters and task coroutines (A.U10.44: `read_loop` → `_read_loop`, `_base_trigger` → `_trigger_loop`, …). Each
  file's merged change names the renames that reach it; the mechanics are the renaming action's.
- **Setup and fixtures follow the boot batch** (A.U10.10, A.U10.21): a test building a reader calls `await
  reader.setup()` (logger store, then config store; `-> bool`) where it called `cfgmgr.setup()`/`pr.setup()` itself;
  every file-local fresh-bus helper calls `machine.I2C.reset_id(<id>)` before constructing (A.U24.20); manual resets of
  fake state that `microtest.after_each(reset_test_state)` now performs (`Timer.all_timers.clear()`, `raise_on_arm`
  restores, `reset_count = 0`) go unless a test resets mid-body on purpose (A.U24.07 (4)); a reader built on FRAM passes
  `log=LogConfig(<manager>, 10, None)` (A.U5.02, M.SRC_CORE's `LogConfig(fram, history_length, debug)`).
- **Function-level imports** (A.U0.07: `tests/` holds 91 in 29 files in its `_PENDING` set, which U24 empties; the
  dynamic sites A.U10.30 named stay as SPEC F.1's named host/test exceptions, untouched — OR141.a (2), OR142.a, A-C review
  fold): every `import`/`from … import` inside a test function or helper moves to the file's
  module-level imports (an alias such as `import time as _time` becomes the module's `time`), so the L0
  `tests_scripts/test_import_placement.py` entry for that file can leave `_PENDING`; the `if __name__ == "__main__":`
  `import microtest` is module level and stays. A file's section names this only where it changes more than an import
  line.
- **Timestamps before the first sync** (A.U10.06, M.SRC_CORE.032, GAP-15 ruling): `utc_now()` is `None` until
  `set_utc_valid()` (no argument) runs. A test that needs a real `TS` calls `asy_base_classes.set_utc_valid()` and resets
  `asy_base_classes._utc_valid = False` in `finally`; a test that calls a reader's `_error_check(results)` directly (not
  through `_read_loop()`) on a successful cycle does the same, since only the reader's own `condition` keeps a pre-sync
  `TS` from counting (M.SRC_SENS.083, .089-.091).
  The NTP client's sync success sets the one-way flag; the after-each hook resets it (TEST_HELP gap, "Gaps"), so no
  test inherits another's sync.
- **Deferred work never outlives a `run()` call** (M.TEST_HELP.043 (b): the shared `run()` cancels every task the call
  created and left unfinished): a test that inspects a file, `_cache` or a flush outcome after `write_config()` (or a
  reader/system setter that stages one) drives the write and `await <manager>.flush_pending()` inside the same
  coroutine — the HEAD pattern of `run(write)` followed by a separate `run(flush_pending())` would await a task the
  first call already cancelled (D-T21).
- **Private by default, the gap-pass G2 sweep** (M_SRC_CORE GAP-G12, GAPS_G2 H-2 (c); gap pass G3): attributes with no
  reader outside their class became private in M.SRC_CORE.008 (`SystemService._watchdog`, `_ntp_is_synced`,
  `_boot_signature`), .036/.037 (`_max_module_error`), .049 (`ConfigManager._cfg_vals`), .081 (`_block_addr`,
  `_verify_counter`), M.SRC_NET.009 (`DNSQuery._data`), .044-.050 (NTP `_network_available_locked`, `_get_dns_server`,
  `_dns_timeout_ms`, `_dns_tries`, `_ntp_fetch_timeout_ms`, `_retry_s`, `_retry_max_s`), .078 (`_hotspot_time`,
  `_conn_fail_to_hotspot`), .155/.156 (`UARTComm._uart`, `_role`, `_payload_size`, `_timeout`, `_uid`), .192/.195
  (`UART._cancel`, `_txbuf`), .213/.215 (`UARTLinkDriver._role`). A test that reads or writes one of these on its
  instance follows in the unit of the product change; the readers at HEAD are `tests/test_system_service.py:162, 167,
  189, 228, 947-948` (`svc.watchdog`), `tests/test_asy_fram_manager.py` and `tests/test_fram_integration.py`
  (`chunk.block_addr`, `verify_counter`; also `test_ntp_fram_system_integration.py`, `test_voc_algorithm.py`,
  `test_print_log.py`, `test_notification_fram_integration.py` for `block_addr`), `tests/test_asy_uart_comm.py:96, 844,
  936, 1414, 1595-1596, 1922, 1955, 2173, 2184` (`payload_size`, `uart`), `tests/test_asy_uart_driver.py` (`cancel`
  writes, `:839-841`), `tests/test_asy_ntp_client.py` (M.TEST_UNIT.111's timeout write). Constructor keywords keep their
  public names; a grep per attribute is qualified by its object, since `timeout`, `cancel`, `data` and `cfg_vals` also
  name unrelated locals and fake attributes. SLF001 is ignored under `tests/**`.
- **`@tunable` tags** (A.U8C/A.U8C2, test-tier grammar A.U8.02): a literal a later constituent deletes (driven time
  A.U35.13/.14, the removed 5 s caps A.U35.15, the removed in-body `gc.threshold` A.U30.12/.13) takes no tag — its
  row is withdrawn (A.U35.13/.14/.15 and A.U30.12/.13 say so); every other tagged literal becomes its module constant
  exactly as the U8C action writes it. Row basis text is U8's (SPEC Part N, not this cluster).
- **Standing test rules checked on every file's end state** (brief "Special care"): real MicroPython Unix port; both GC
  stages with zero `MemoryError` markers (both spellings; `scripts/test.sh` gate); bounded fake pollers only; no nested
  `asyncio.run()` (A.U24.08's `run()` now refuses it); no brute-force host I/O; `method-assign` ignores stay inline in
  tests; the four-tier bus-hazard rule; a pinned behaviour a product change retires is adapted or retired with the
  guard that replaces it named (OR111.a (2)); no test is skipped or disabled to get green (`microtest.Skip` is used only
  where A.U7.07/A.U24.50 make a vacuous path report SKIP — a device that declares nothing to exercise).
- Adherence was read per file: the touched sites and their context in full; the whole end-state file mechanically
  (grep) for the rule patterns — `select.poll`, `asyncio.run(`, `gc.collect`/`gc.threshold`, `MemoryError` catches,
  `type: ignore[method-assign]`, comment blocks > 3 prose lines, temporary audit IDs (`G\d/R\d`, `U\d+`, `OR\d+`, `WP\d`,
  `Topic`, `session`), variant names.

## tests/lwip_host/test_modlwip_eagain.py (new)

### M.TEST_UNIT.001 Hammer the patched modlwip send path on the lwIP host build
- **From**: A.U21.13 (whole file). Read: A.U24's cross-unit table row (the file runs under `tests/microtest.py`
  unchanged; A.U24.04's trailer check and A.U24.08's guard cover `tests/lwip_host/`), AC_NOTES 21 and 24 (branch proof,
  one-time control run, failed bound goes to the owner as an override change).
- **Site**: new `tests/lwip_host/test_modlwip_eagain.py`.
- **Change**: as A.U21.13 writes it — seven tests (write-bound with the pool measured in-process; queue-limit edge;
  segment-pool edge; a reading peer receives every byte intact; capacity returns after peers close; repeated rounds
  stable; per-round cost of the `EAGAIN` spin), every socket built at synchronous test scope, driven by non-blocking
  `write()`/`recv()`/`accept()` in bounded loops pumped with `time.sleep_ms(1)`; the only `select.poll()` use is one
  timeout-0 readiness check per test on a real lwIP socket (never a fake stream, never a waiting poll), which proves the
  edge is the patched branch (`EAGAIN` while `POLLOUT` is set) and fails naming the send-buffer edge otherwise. Module
  constants for the seven tunables tagged in A.U8.02's test-tier grammar (`l1.lwip_host_write_bound_ms = 250`,
  `l1.lwip_host_recovery_s = 15`, `l1.lwip_host_rounds = 20`, `l1.lwip_host_connect_bound_ms`,
  `l1.lwip_host_spin_rounds`, `l1.lwip_host_spin_round_max_us`, `l1.lwip_host_spin_round_alloc_max_b`), values fixed by
  the executor's first measured run and each row's basis "estimated (agent, <commit>) — measurement owed". `import lwip`
  carries `# type: ignore[import-not-found]` with its reason only if the installed board stub ships no `lwip` module
  (checked after the stub move). Test (7) measures `gc.mem_alloc()` before and after each round and sets no
  `gc.threshold` itself: the file runs at both GC stages like every L1 file (a collection inside a round can only lower
  the delta), which keeps G4/R49's "no in-body stage override" (the rule the webserver file's merged change below applies). Header ≤ 3 lines; canonical
  `microtest.run(globals())` trailer. The one-time sensitivity run against `build-lwip-control` (throwaway worktree,
  deleted afterwards) is recorded in the audit working file, never committed.
- **Resolved**: A.U21.13's "measured at `gc.threshold(-1)`" read as "meaningful at the (e) stage; no in-body threshold
  set" (agent decision D-T1, OR2.c list) — G4/R49/OR40.a (2) forbid an in-body stage change whose subject is not the
  threshold.
- **Unit**: U21.
- **Depends**: A.U21.12 (the `build-lwip` binary and `scripts/test.sh`'s `tests/lwip_host/` loop, SCR/TOOL); A.U21.09
  (the override); A.U8.02 (tag grammar); A.U19.24 (the L1 webserver half, M.TEST_UNIT in `test_asy_webserver_service.py`).
- **Blast carried by**: runner and `MemoryError` gate → A.U21.12 (SCR); Part N rows for the seven tunables → A.U8.01
  (SPEC); SPEC E.1/E.3 second L1 set → A.U21.13 docs (SPEC); phase-C bound → A.U21.14 (HW_BENCH); `tests/microtest.py`
  unchanged (TEST_HELP).
- **Kind**: test

## tests/test_api_response.py (→ `tests/test_asy_api_response.py`)

End state: tests of `make_response()` over the one code catalog {0, 1, 400, 404, 405, 413, 500} (M.SRC_CORE.073) with a
producer-totality test, and of `handle_set_cmd()` answering OK with a raising hook failing its group (M.SRC_CORE.072);
no `parse_cmd_request()` tests.

### M.TEST_UNIT.002 Rename the file; shared harness and schema name
- **From**: A.U10.37 (rename; imports), A.U24.08 (`run()` → `_async_harness`), A.U24.01 (`_VAL_SI` →
  `_TEST_SCHEMA_SI`, no test name shadowing a `src/` const), A.U24.76 (read: `_make_reader` already private).
- **Site**: `tests/test_api_response.py:1-33` (imports, `TYPE_CHECKING` block, `run()`, `_VAL_SI`) and every
  `_VAL_SI` use (`:187, 198, 207, 217, 229, 240, 255, 273, 292, 306, 327, 352`).
- **Change**: `git mv` to `tests/test_asy_api_response.py`; `import asy_api_response as ar`, `from asy_base_classes
  import SensorReaderConfig`, `import asy_config_manager as cm` (under `TYPE_CHECKING`); the local `run()` and its
  `Coroutine`/`TypeVar` typing go, `from _async_harness import run`; `_VAL_SI` → `_TEST_SCHEMA_SI` at its definition and
  all twelve uses.
- **Resolved**: —
- **Unit**: U10 (rename, imports) → U24 (harness, name). Staged: U10's rename is a prerequisite of every later unit's
  edit of this file.
- **Depends**: M.SRC_CORE (A.U10.37 rename of the module); A.U24.08's `tests/_async_harness.py`, A.U24.01's
  `tests/_src_const.py` (TEST_HELP).
- **Blast carried by**: `scripts/test.sh` discovers by glob (A.U10.37 Blast) — none; `tests_scripts/test_const_mirrors.py`
  pin → A.U24.02 (TSC).
- **Kind**: test

### M.TEST_UNIT.003 `make_response()` tests follow the one catalog
- **From**: A.U19.15 (`:80-88` new set, `:95-100` rename, new producer-totality L1), A.U27.07 (codes 2/3 go),
  A.U11.26 (codes 4, 5, 100 go).
- **Site**: `tests/test_api_response.py:62-117`.
- **Change**: `:75-77` `test_make_response_standard_error_text_can_be_overridden` uses code 404 (`descr="Custom
  not-found text"`, expected `{"res": "ERR", "code": 404, …}`) instead of the retired code 2. `:80-88`
  `test_make_response_every_standard_code_present` iterates `(0, 1, 400, 404, 405, 413, 500)`; `res` "OK" for 0 only.
  `:90-93` unchanged (the totality test). `:95-100` renamed `test_make_response_unknown_code_with_descr_keeps_the_given_descr`,
  its comment → "# Totality only: an uncatalogued code keeps the given text; the catalog itself is closed (C.5.3)."
  New `test_every_catalogued_code_has_a_producer_and_every_produced_code_is_catalogued`: the produced set is every
  integer literal passed as the first argument of `make_response(` in `src/*.py` (a text scan: each occurrence of
  `make_response(` followed by digits) plus `src_const("src/asy_webserver_service.py", "_ERROR_STATUSES")`; it equals the
  catalog's key set read the same way from `src/asy_api_response.py`'s `_STANDARD_CODES` block (each `<int>:` key), both
  ways. `:111-113` comment (A.U0.35, M.TEST_UNIT.004).
- **Resolved**: the U19 stage keeps codes 2 and 3 (M.SRC_CORE.073 stages: 2/3 go with `parse_cmd_request()` in U27);
  the U19 list is `(0, 1, 2, 3, 400, 404, 405, 413, 500)` and U27 drops 2/3; `:75` moves to 404 already in U19 (it tests
  the override, not code 2). Code 2's own override case is not kept anywhere (its catalog entry goes).
- **Unit**: U27 (stage U19: catalog without 4/5/100 with the HTTP statuses and the producer test, co-landing with
  M.SRC_CORE.073's U19 stage; U27: 2/3 go with M.SRC_CORE.073).
- **Depends**: M.SRC_CORE.073, M.SRC_NET.112 (`_ERROR_STATUSES` const), M.TEST_UNIT.002 (`src_const`).
- **Blast carried by**: `tests_js/render.test.js:851` → U23 (WEB); SPEC C.5.3 → A.U19.15 (SPEC).
- **Kind**: test

### M.TEST_UNIT.004 Owner/agent labels on the envelope and hook comments
- **From**: A.U0.35 (`:112`, `:183`), A.U11.26 (the section header's premise changes with the hook semantics);
  M.SRC_CORE.072 as amended in gap pass G2 (`handle_set_cmd()` returns the per-field result, the endpoint builds the
  envelope; GAPS_G2 H-2 (a), gap pass G3).
- **Site**: `tests/test_api_response.py:111-113`, `:180-184`.
- **Change**: `:112-113` → "# (owner, 2026-09-26): per-field failures don't demote the overall response - res not OK
  would mean the request itself was broken; individual field outcomes live in "result"." (2 lines). Section header
  `:180-184` → "# handle_set_cmd - drives SensorReaderConfig._set_dict_cfg and the post-write hook and returns the
  per-field result; / # a raising hook turns its group's fields "Failed", caught as defense in depth on top of
  Microdot's own / # per-request catch (agent, 2026-08-03: prior field experience with Microdot behaving unexpectedly)."
  between the two `# ----` rules (3 prose lines).
- **Resolved**: A.U0.35 relabels a header whose premise ("its own try/except as defense-in-depth" around the whole
  call) A.U11.26 narrows to the hook; one text carries both.
- **Unit**: U11 (stage U0: A.U0.35's two labels on the HEAD text; U11 rewrites the header with the hook change).
- **Depends**: M.TEST_UNIT.005.
- **Blast carried by**: `tests_scripts/test_comment_block_cap.py` (holds, ≤ 3).
- **Kind**: doc

### M.TEST_UNIT.005 `handle_set_cmd()` tests: constructor tail, OK envelope on a raising hook
- **From**: A.U5.02 (`:190` constructor), A.U11.26 (`:282-332` re-expected; new mixed-result and no-Valid tests),
  A.U2.18 (persisted `code("E", "CALLBACK")`), A.U4.02, A.U32.03, A.U11.S02 (read: hold); M.SRC_CORE.072 as amended in
  gap pass G2 (the return is the per-field `WriteValidity`, `ok_descr` gone; GAPS_G2 H-2 (a), gap pass G3).
- **Site**: `tests/test_api_response.py:187-192` (`_make_reader`), `:195-355` (every `handle_set_cmd()` test), new tests
  after `:355`.
- **Change**: `_make_reader` builds `SensorReaderConfig(Meas(20.0, 50), name, cfg_vals, max_module_error=3,
  cfg_path=path_prefix)` (M.SRC_CORE.040's order). Every `handle_set_cmd()` test asserts the returned per-field dict, not
  an envelope: `:195` `== {"SampleInterv": "Valid"}` (name `…_valid_change_returns_its_per_field_result`); `:204`
  `test_handle_set_cmd_ok_descr_override` goes (no `ok_descr`; no product caller passed one); `:214`
  `…partial_failure_…` asserts the mixed dict; the hook tests `:225-281` assert the dict and the hook calls; `:335`
  `…whole_persist_failure_…` → `…_marks_every_field_failed` (`{"SampleInterv": "Failed"}`); `:349` `…empty_data_…` →
  `== {}`. The three raising-hook tests each assert `result == {"SampleInterv": "Failed"}`, `reader.pr.err_count == 1`,
  and exactly one entry in `reader.pr.get_log()` with number `code("E", "CALLBACK")` and `ErrType` "E"; names →
  `…_sync_post_fct_raising_fails_its_group`, `…_async_post_fct_raising_fails_its_group`; `:313` keeps its name and
  "never scheduled" assertion, its comment's last sentence → "… and the group's fields read Failed."; the `:283-285`
  comment → "# A raising post-write hook is caller-supplied code outside _set_dict_cfg(): its failure is its group's
  outcome." New: `test_handle_set_cmd_hook_raising_after_a_mixed_result_fails_every_key` (`{"SampleInterv": 42,
  "Ghost": 1}` with a raising `post_fct` → both keys "Failed", one CALLBACK entry);
  `test_handle_set_cmd_never_calls_a_hook_when_nothing_is_valid` (`{"SampleInterv": 9999}` → "Invalid", neither hook
  called).
- **Resolved**: A.U11.26's "one persisted CALLBACK entry" and A.U2.18's "new L1 … persists exactly `code("E",
  "CALLBACK")`" are one assertion on the rewritten tests (no separate test); the reader here has no FRAM (`log` default),
  so "persisted" is the logger's history entry read through `get_log()`.
- **Unit**: U11 (stage U5: the constructor call co-lands with A.U5.02's signature change).
- **Depends**: M.SRC_CORE.036, M.SRC_CORE.040, M.SRC_CORE.072; A.U2.03 (`tests/_error_codes.py`).
- **Blast carried by**: webserver hook-failure tests → M.TEST_UNIT in `test_asy_webserver_service.py` (A.U11.26); the
  envelope around the returned dict is the endpoint's (M.SRC_NET.120), asserted by the webserver PUT tests.
- **Kind**: test

### M.TEST_UNIT.006 Remove the `parse_cmd_request()` tests and their request stand-in
- **From**: A.U27.07 (Blast: `:125-178` seven tests and `:42-44` `_FakeRequest` go).
- **Site**: `tests/test_api_response.py:42-54`, `:120-178`.
- **Change**: `_FakeRequest` and the `parse_cmd_request` section (banner and seven tests) are deleted with the function
  (M.SRC_CORE.073). What they pinned for the REST path — a non-JSON or non-object body answers code 1 — is pinned on the
  real app by the rewired `tests/test_setter_microdot_integration.py` (A.U27.07 (3)) and
  `tests/test_asy_webserver_service.py:877` (renamed `…_malformed_json_body_answers_code_1`).
- **Resolved**: OR111.a (2): the retired pins name their replacing guards (above).
- **Unit**: U27.
- **Depends**: M.SRC_CORE.073.
- **Blast carried by**: the replacing tests → M.TEST_UNIT in `test_setter_microdot_integration.py` and
  `test_asy_webserver_service.py` (A.U27.07).
- **Kind**: test

## tests/test_asy_bmp3xx_driver.py

End state: the driver's tests against M.SRC_SENS.038-048 — `BMP3XX_Reader`/`BMP3XX_I2C` with the conversion wait, the
driver-owned burst buffer, bool bus results, `get_pressure_altitude()`, the captured compensation config, the W11
domain warning, the participant rung and catalog numbers; every schema value read from source, every datasheet value
an independent cited copy. U10 renames reaching this file: `BMP3xx_Reader` → `BMP3XX_Reader`, `AsyFramManager` →
`FRAMManager`, `print_log`/`config_manager` → `asy_print_log`/`asy_config_manager`, `reader.bmp` → `reader._bmp`,
`bmp.i2c_bmp3xx` → `bmp._i2c_bmp3xx`, `trigger_period`/`trigger_counter`/`trigger_timer`/`base_trigger_event`/
`read_event` → their `_`-names, `asy_lock` → `session_lock`, `set_trigger_secs`/`_push_trigger_secs` →
`set_trigger_s`/`_push_trigger_s`, `read_loop` → `_read_loop`, `_base_trigger` → `_trigger_loop`, keys
`SampleInterv`/`PressOvers`/`PressOffset`/`SeaLevelOffs` → `SampleInterval`/`PresOvers`/`PresOffset`/`SeaLevelOffset`.

### M.TEST_UNIT.007 Header block: cited datasheet copies, shared doubles and harness
- **From**: A.U24.01 (`:21-36` datasheet copies stay, each citing its source; `:124` `_EXPECTED_TEMPERATURE` →
  `tests/_bus_hazard_catalog.BMP_EXPECTED_TEMPERATURE`), A.U24.08 (`run()`), A.U24.49 (`_FastAsyncSleep` `:64-78`,
  `_RaiseOnArm` `:81-93` → shared), A.U31.11 (the shared fast sleep patches `asyncio.sleep_ms` too), A.U8.07 (its
  comments name constants, not values), A.U24.20 (`make_i2c()` `:136` resets the id), A.U10.37/A.U10.38 imports.
- **Site**: `tests/test_asy_bmp3xx_driver.py:1-56` (imports, the `:17-19` SPI swap comment, `:21-36` copies,
  `TYPE_CHECKING`, `run()`), `:59-93`, `:98-125`, `:136-137`.
- **Change**: imports `from asy_bmp3xx_driver import BMP3XX, BMP3XX_I2C, BMP3XX_Reader`, `from asy_print_log import
  LogConfig, PrintLogHistoryStore`, `from _async_harness import run`, `from _fast_sleep import FastAsyncSleep`, `from
  _fake_timer_arm import RaiseOnArm`, `from _bus_hazard_catalog import BMP_EXPECTED_TEMPERATURE`, `from _src_const import
  src_const`, `from _error_codes import code`; `AsyFramManager` import goes (M.TEST_UNIT.017 builds through
  `tests/_fram_builders.py`). The `:21-23` comment → "# BMP388/390 register map and encodings, copied from
  BST-BMP388-DS001 section 4.3 (Tables 25-45) and BST-BMP390-DS002 Table 26 - an independent oracle, not the driver's
  const() values." (3 lines); each copy keeps its value. `_EXPECTED_TEMPERATURE` goes (uses read
  `BMP_EXPECTED_TEMPERATURE`); `_EXPECTED_PRESSURE_HPA` stays with the `:101-102` hand-calculation comment. The local
  `run()`, `_FastAsyncSleep` and `_RaiseOnArm` classes go (callers use `FastAsyncSleep()`/`RaiseOnArm(exc)`); `_settle()`
  stays. `make_i2c()` → `FakeI2C.reset_id(0)` then the construction.
- **Resolved**: —
- **Unit**: U24 (stage U10: imports/renames).
- **Depends**: TEST_HELP's `_async_harness.py`, `_fast_sleep.py`, `_fake_timer_arm.py`, `_src_const.py`,
  `_error_codes.py` (A.U2.03), `_bus_hazard_catalog.BMP_EXPECTED_TEMPERATURE` (A.U24.01 (4)), `machine.I2C.reset_id`
  (A.U24.20).
- **Blast carried by**: `tests_scripts/test_const_mirrors.py` pins the copies → A.U24.02 (TSC).
- **Kind**: test

### M.TEST_UNIT.008 Chip-ID and calibration tests assert what setup did
- **From**: A.U24.38 (`:217, 224, 231`), A.U10.21 + A.U31.11 (`:298-307` goes), A.U15.25 (2) (held: both IDs,
  all-0x00/0xFF rejected).
- **Site**: `tests/test_asy_bmp3xx_driver.py:212-307`.
- **Change**: the three "accepts" tests each assert, after `setup()` returns `True` (A.U10.21's `-> bool`), that the
  fake's log holds one `readfrom_mem` of `_REGISTER_CHIPID` and that `bmp._temp_calib[0] == 28617 * 256` and
  `bmp._pressure_calib[4] == 30462 * 8` (the seeded bytes read back); each is paired in the same test with a rejected
  neighbour ID (`0x51` for the 0x50 tests, `0x61` for BMP390) whose `setup()` raises `RuntimeError`.
  `test_setup_applies_custom_sea_level_pressure_and_wait_time` (`:298-307`) is removed: `setup()` takes no parameter
  (A.U10.21), `_wait_time` is gone (the poll step is `_STATUS_POLL_MS`, A.U31.11) and the sea level is the constant
  `_SEA_LEVEL_PRESSURE_HPA` (M.SRC_SENS.040) — no input reaches either, so nothing is left to pin.
- **Resolved**: A.U24.38 asks for "the driver's stored chip id"; `BMP3XX_I2C.setup()` stores none (it checks and
  discards it, `asy_bmp3xx_driver.py:626-628`), and adding one for the test is a test-only artifact (OR36). The
  observable effect — the ID read, the coefficients stored, the neighbour refused — carries the claim instead (agent
  decision D-T3).
- **Unit**: U24 (stage U15: `:298-307` goes with M.SRC_SENS.048's U15 stage — A.U10.21's parameter removal lands in U10,
  so the test goes in U10).
- **Depends**: M.SRC_SENS.048.
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.009 `reset()` tests: immediate failure on a dead bus, the command on the wire
- **From**: A.U13.09 (`:351-364`), A.U24.38 (`:380`), A.U15.R03 (read: reset tests unchanged).
- **Site**: `tests/test_asy_bmp3xx_driver.py:314-380`.
- **Change**: `test_reset_raises_oserror_when_bus_deinitialized_mid_poll` asserts the `OSError` message is "I2C bus not
  initialized" (M.SRC_SENS.048's `_wait_status_bits()`), so it proves the immediate refusal, not a timeout; its comment
  `:352-354` → "# A deinitialized bus makes the status poll raise at once (bool bus results, SPECIFICATION.md C.3)."
  `test_reset_succeeds_when_err_reg_clear` asserts the fake's log holds a `writeto_mem` of `0xB6` to register `0x7E`
  (BMP388 datasheet section 4.3.22, Table 45 — cited in a one-line comment).
- **Resolved**: —
- **Unit**: U13 (A.U13.09's product change); `:380` in U24.
- **Depends**: M.SRC_SENS.048.
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.010 `_read()` tests: conversion wait, driver-owned burst, one timestamp
- **From**: A.U15.25 (3) and its two new L1 cases, A.U31.11 (the wait as `sleep_ms(129)`), A.U13.09 (`:458-470`),
  A.U13.10 + A.U30.07 (`_BadBurstRead` `:161-209` and its two users `:486-529`), A.U10.06 (the failed-read tuple),
  A.U2.10 (`:526`), A.U15.25 (Blast: register-sequence asserts gain the OSR read — none in this file compares the
  full read sequence; `_count_forced_mode_triggers` counts writes only and holds).
- **Site**: `tests/test_asy_bmp3xx_driver.py:161-209`, `:387-563`.
- **Change**: `_BadBurstRead` wraps `bmp._i2c_bmp3xx.i2c_device.get_register_into` (inline `# type:
  ignore[method-assign]`, test file only) and answers `False` for `_REGISTER_PRESSUREDATA`, passing every other register
  through; its comment (≤ 3 lines) states the case: "the burst read reports no bus (`get_register_into()` → False)".
  `test_read_raises_oserror_when_the_data_burst_returns_an_unexpected_result` → `…_when_the_data_burst_read_fails`,
  one case (the short/long blobs are impossible once the driver reads into its own 6-byte buffer), asserting `OSError`
  "I2C bus not initialized". `test_read_bmp_logs_and_degrades…` → `…_when_the_data_burst_read_fails`: `results[0] is
  None and results[1] is None`, `results[2] is None` (no clock sync in this file: `utc_now()` is `None`), newest entry
  `code("E", "READ")`, type "E". `test_read_raises_oserror_when_bus_deinitialized_mid_poll` asserts the "I2C bus not
  initialized" message. New `test_read_waits_the_computed_conversion_time_at_x32_x32`: OSR register seeded `0b101101`
  (×32/×32), `asyncio.sleep_ms` wrapped from outside by a recorder (restored in `finally`); after `_read()` the recorder
  holds `129` (`(939 + 2000 * 64 + 999) // 1000`, DS001 3.9.2) and the fake log shows at most two STATUS reads (STATUS
  seeded ready). New `test_read_raises_within_the_measurement_bound_when_status_never_reports_ready`: STATUS 0, the
  conversion sleep and poll sleeps recorded; `OSError` raised after at most `_MEAS_TIMEOUT_MS // _STATUS_POLL_MS + 1`
  polls (constants via `src_const`).
- **Resolved**: A.U15.25's "patched sleep receives 0.128939 s" is A.U31.11's `sleep_ms(129)` (U31 conflict row 2,
  M.SRC_SENS.048). The timeout test counts polls, not wall time (no brute-force wait).
- **Unit**: U31 (stages: U13 bool results and `_BadBurstRead` on `get_register_bytes`/`None`; U15 wait and OSR read;
  U30 `get_register_into`; U31 `sleep_ms`).
  A-C2 step order: A.U2.10's part lands in U3, not U2 (it follows A.U2.10's own change, which lands in U3).
- **Depends**: M.SRC_SENS.048, M.SRC_SENS.043; M.TEST_UNIT.007.
- **Blast carried by**: four-tier hazard cases for the OSR read → M.TEST_UNIT in `test_bus_hazard_multi_device.py`
  (A.U15.25 (7)).
- **Kind**: test

### M.TEST_UNIT.011 Pressure altitude: renamed method, the sea-level guard tests retire
- **From**: A.U15.27 (`:584-619`), M.SRC_SENS.040 (GAP-6: the `<= 0` guard goes, the sea level is a constant),
  A.U10.35 (`sea_level_pressure` private — superseded: the attribute is gone).
- **Site**: `tests/test_asy_bmp3xx_driver.py:566-634`.
- **Change**: section comment → "# get_pressure_altitude() - hardware API with no product caller (NOAA pressure altitude
  over the ISA 1013.25 hPa sea level)."; `test_get_altitude_computes_a_plausible_value…` →
  `test_get_pressure_altitude_computes_a_plausible_value…` calling `get_pressure_altitude()` (assertion unchanged).
  `test_get_altitude_raises_value_error_for_zero_sea_level_pressure` and `…_for_negative_sea_level_pressure` are
  removed: the guard they pin is removed as unreachable (the sea level is `_SEA_LEVEL_PRESSURE_HPA`, never written —
  OR46.a (2); the replacing guarantee is the constant itself, M.SRC_SENS.040).
- **Resolved**: GAP-6 of M_SRC_SENS settled here (OR111.a (2): the retired pins name the constant that replaces them).
- **Unit**: U15.
- **Depends**: M.SRC_SENS.040, M.SRC_SENS.048.
- **Blast carried by**: `tests/_bus_hazard_catalog.py:293` → A.U15.27 (TEST_HELP); the sweep `:2037` → M.TEST_UNIT.023.
- **Kind**: test

### M.TEST_UNIT.012 Oversampling/filter tests follow the session names
- **From**: A.U10.18 + A.U10.35 (`bmp.i2c_bmp3xx` `:691`), A.U15.40 (the session object is `DeviceSession`).
- **Site**: `tests/test_asy_bmp3xx_driver.py:637-718`.
- **Change**: `async with bmp.i2c_bmp3xx:` → `async with bmp._i2c_bmp3xx:`; every assertion holds (the setters still
  raise `ValueError` for a refused value before any bus access).
- **Resolved**: —
- **Unit**: U15 (stage U10 names).
- **Depends**: M.SRC_SENS.048.
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.013 A deinitialized bus fails writes as well as reads
- **From**: A.U13.07 (`set_bits()` → `bool`) with M.SRC_SENS.048 (`_set_osr_setting()`/`set_filter_coefficient()`
  raise on `False`) — no action names this test (gap closed here).
- **Site**: `tests/test_asy_bmp3xx_driver.py:816-834` `test_bus_deinit_write_no_ops_silently_but_read_raises_oserror`.
- **Change**: renamed `test_bus_deinit_fails_the_write_and_the_read_with_oserror`: after `i2c.deinit()`,
  `set_pressure_oversampling(8)` raises `OSError("I2C bus not initialized")` and `get_pressure_oversampling()` raises
  `OSError`; the comment block `:817-823` → "# A deinitialized bus: every register helper reports it (None or False) and
  the driver turns each into an OSError (SPECIFICATION.md C.3)." The pinned "silent no-op" was the asymmetry A.U13.07
  removes; the new assertion is its replacement guard (OR111.a (2)).
- **Resolved**: —
- **Unit**: U13.
- **Depends**: M.SRC_SENS.011, M.SRC_SENS.048.
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.014 Reader builders and the trigger-interval setter
- **From**: A.U5.02, A.U10.10 (builders call `setup()`), A.U10.43 (`set_trigger_s`), A.U15.26 (`:887` 45.7 refused; new
  `True` case), A.U2.10 (21 → `code("E", "BAD_ARG")`), A.U1.25 + A.U24.67 (`:901` legacy path, no variant name),
  A.U10.35 (`_trigger_period`), A.U11.24 (`write_config(data)`), A.U10.40 (keys).
- **Site**: `tests/test_asy_bmp3xx_driver.py:841-966`.
- **Change**: `make_reader()`/`make_clean_reader()` → `_make_reader()`/`_make_clean_reader()` (A.U24.76), constructing
  `BMP3XX_Reader(i2c, address=_ADDR, max_module_error=…, cfg_path=…)` and `run(reader.setup())`. Trigger tests call
  `set_trigger_s()` and read `reader._trigger_period`; the in-scenario `await reader.pr.setup()` lines go (the builder's
  `setup()` did it). `test_reader_set_trigger_secs_accepts_valid_values` → `test_reader_set_trigger_s_accepts_whole_seconds_and_refuses_a_fraction`:
  30 → value 30; `set_trigger_s(45.7)` → `False`, value still 30, newest entry `code("E", "BAD_ARG")`. New
  `test_reader_set_trigger_s_refuses_a_bool`: `set_trigger_s(True)` → `False`, value unchanged, one BAD_ARG entry.
  Every `ErrNum[-1] == 21` → `== code("E", "BAD_ARG")`. `:899-901` comment → "# Bound 1-3600 s, the deployed
  validation of this field (the legacy firmware's sensortask module, legacy/firmware/modules/); a refused value is
  logged, never raised." `:908-910` comment → "# The shared type_or_range_error() refuses NaN and ±inf like any
  out-of-range value." `test_init_bmp_soft_degrades_on_out_of_range_stored_sample_interval` writes
  `write_config({"SampleInterval": 7200})` and pokes `reader.cfgmgr._cache["SampleInterval"]`; its BAD_ARG assertion
  holds (a provoked fault, A.U35.37 class (b)).
- **Resolved**: A.U15.26's "`set_trigger_secs(True)`" is written with A.U10.43's name (U10 lands first).
- **Unit**: U15 (stages U5 constructor, U10 names/setup, U11 `write_config`, U24 builders' names).
  A-C2 step order: A.U2.10's part lands in U3, not U2 (it follows A.U2.10's own change, which lands in U3).
- **Depends**: M.SRC_SENS.042, M.SRC_SENS.045, M.SRC_CORE.040.
- **Blast carried by**: SPEC M.4 sentence → A.U15.26 (SPEC).
- **Kind**: test

### M.TEST_UNIT.015 Schema tests read the schema from source
- **From**: A.U24.01 (`:991-1003` `_VAL_*` ×8 → `src_const`), A.U15.23 (`:1003`, `:1014` −40; new MeanAtmTemp L1),
  A.U10.39/A.U10.40 (the source names `_VAL_SAMPLE_INTERVAL`, `_VAL_PRES_OVERS`, `_VAL_TEMP_OVERS`, `_VAL_FILT_COEFF`,
  `_VAL_PRES_OFFSET`, `_VAL_TEMP_OFFSET`, `_VAL_SEA_LEVEL_OFFSET`, `_VAL_MEAN_ATM_TEMP` and keys), A.U11.24 (`write_config`
  loses its schema argument, 16 calls), A.U24.32 (RF286 `:1124-1141`), A.U15.R03 + A.U10.R01 (the chip-write failure
  climbs to the controller rung).
- **Site**: `tests/test_asy_bmp3xx_driver.py:969-1215`.
- **Change**: the eight test-local tuples become `_VAL_… = src_const("src/asy_bmp3xx_driver.py", "_VAL_…")` under the
  source names, `_FULL_SCHEMA` their concatenation (the "mirrors … cannot be imported" banner `:970-972` → "#
  Configuration schema read from the driver's source (tests/_src_const.py), exercised through the real ConfigManager.");
  `_FIELD_BOUNDS` and `_DISCRETE_FIELDS` are derived from `_FULL_SCHEMA` (`{name: (kind, lo, hi)}` for the rows whose
  allowed-set slot is `None`, `{name: allowed}` for the others) instead of hand-kept — so A.U15.23's −40 needs no test
  edit. Every `write_config({...}, _FULL_SCHEMA)` → `write_config({...})`. The RF286 test
  (`…stored_oversampling_is_outside_hardware_domain`) asserts, besides `_init_bmp() is False`, the BMP3XX log's entries
  from this call: one `code("E", "CHIP_SET")` (type "E") followed by one `code("W", "BUS_RECOVERY")` from
  `_init_failed()`'s controller rung (A.U10.R01 (5)). New `test_mean_atm_temp_below_minus_40_is_refused_and_minus_40_yields_a_sea_level_pressure`:
  `{"MeanAtmTemp": -45.0}` → "Invalid", `-40.0` → "Valid"; with it stored, a planted read (`_ADC_P`/`_ADC_T`) stores a
  numeric `SLPres` (the D4.64 regression).
- **Resolved**: deriving the bound tables from the schema (agent decision D-T2) makes A.U15.23's two table edits one
  source edit; A.U24.01's rule "a test … reads or derives it from its source" covers the derived tables.
- **Unit**: U24 (stages U10 names/keys, U11 `write_config`, U15 MeanAtmTemp and the rung assertion).
  A-C2 step order: A.U10.R01's part lands in U13, not U10 (it follows A.U10.R01's own change, which lands in U13).
- **Depends**: M.SRC_SENS.041, M.SRC_SENS.044, M.SRC_CORE.040; M.TEST_UNIT.007.
- **Blast carried by**: generated definitions `MeanAtmTemp` min → A.U15.23 (GEN).
- **Kind**: test

### M.TEST_UNIT.016 The config snapshot's lock hold is proven with a forced interleaving
- **From**: A.U35.11 (`:1223-1248`), A.U10.18 + A.U10.35 (`reader._bmp._i2c_bmp3xx.session_lock`), A.U10.40 (keys in
  `:1165-1210`).
- **Site**: `tests/test_asy_bmp3xx_driver.py:1165-1248`.
- **Change**: the two `get_dict_cfg()` tests read `cfg["PresOvers"]`, `cfg["SampleInterval"]`. The snapshot test keeps
  its acquire count (`session_lock.acquire` counted) and adds the forced interleaving as A.U35.11 writes it: the device's
  `get_bits` wrapped (inline `# type: ignore[method-assign]`) so its first call awaits an `asyncio.Event` the test holds;
  snapshot task started and gated, `set_pressure_oversampling(8)` started and shown blocked (`not write_task.done()`),
  gate released; snapshot `== (1, 1, 0)` (the chip's reset encodings, DS001 Tables 34/36) and the OSR write appears in
  the fake log only after the snapshot's three reads. The `:1228-1230` comment → "# The gate holds the snapshot inside
  its session while a setter waits for the same lock."
- **Resolved**: —
- **Unit**: U35 (stage U10 names).
- **Depends**: M.SRC_SENS.048; M.TEST_UNIT.007 (`FastAsyncSleep` moved).
- **Blast carried by**: planted-fault proof (per-field lock) → A.U35.04 (B3).
- **Kind**: test

### M.TEST_UNIT.017 Reader integration: catalog numbers, config failures, the rung, the capture rule
- **From**: A.U2.10 (`:1306, 1325, 1343, 1382, 1437`), A.U3.05 dropped (OR140.a (7): the reader keeps its own entry for
  a config-read failure beside `CFGMGR_BMP3XX`'s; A-C review fold), A.U15.22 (2) (`_store_bmp()`
  uses the captured values; new capture and last-sample L1), A.U15.24 (W11 L1), A.U10.06 (L1 `TS` before sync),
  A.U10.R01 + A.U15.R03 (`:1393-1411` re-derived; four new rung L1), A.U2.06, A.U3.03 dropped (OR140.a (7): the
  streak entry stays),
  A.U5.02 + A.U10.10 (`:1468-1510` FRAM-backed reader), A.U12.08 (`:1388` comment), A.U24.49 (FRAM builder).
- **Site**: `tests/test_asy_bmp3xx_driver.py:1217-1510`; new tests after `:1510`.
- **Change**:
  - `test_each_reader_level_setting_getter_degrades_with_its_own_errno_on_a_dead_bus` →
    `…degrades_with_a_chip_get_entry_on_a_dead_bus`: each getter returns `None`, `ErrCount` rose by three, the newest
    entry is `code("E", "CHIP_GET")`; comment → "# The three getters share the catalog's CHIP_GET class (numbers name
    the failure class, not the call site)." — the distinct 15/17/19 the test pinned are retired by the catalog's
    class numbering (A.U2.10); the degrade-to-None and one-count-per-call claims stay.
  - `test_init_bmp_fails_and_logs_when_setup_raises`: the BMP3XX log gains `code("E", "INIT")` then `code("W",
    "BUS_RECOVERY")` (`_init_failed()` re-initialises the controller, A.U10.R01 (5)); `ErrCount` re-derived from those
    two entries.
  - `test_init_bmp_fails_and_logs_when_config_data_unreadable`: `reader.cfgmgr.valid = False`; `_init_bmp()` is
    `False`; the BMP3XX log's newest entry is its own config-read code (HEAD's 12, by the catalog name the fold gives
    it back) and `CFGMGR_BMP3XX` holds `code("E", "CFG_NOT_VALID")`; no bus rung ran (the fake log holds no `recover`
    marker).
  - `test_store_bmp_falls_back_to_default_compensation_values_when_config_unreadable` → `…read_bmp_captures_the_default_compensation…`:
    baseline as today (offsets written with `write_config({...})`, read + store, offsets applied); then
    `reader.cfgmgr.valid = False`, `results = _read_bmp()` (the capture falls back to `[0.0, 0.0, 0.0, 15.0]`), `_store_bmp(results)`;
    assertions: `CFGMGR_BMP3XX` newest entry `code("E", "CFG_NOT_VALID")`, the BMP3XX log's newest entry its own
    compensation-read code (HEAD's 14, type "E", by the catalog name the fold gives it back), `Pres == results[0]`,
    `Temp == results[1]`, `SLPres == results[0]` (`:1386-1388` comment names `pressure_at_height()`), `TS == results[2]`.
  - `test_reader_read_error_check_threshold_and_self_heal`: outcomes stay `[True, True, False, True]`; the log shows one
    `code("E", "CHIP_SET")` "Soft reset failed" from the device rung at the 2nd failure (NAKed reset), then
    `code("E", "GIVE_UP")`, with the streak's own entry per failed cycle between them as at HEAD (OR140.a (7)).
  - `test_reader_uses_fram_backed_print_log_when_fram_provided`: manager built with `make_fram_manager()`
    (`tests/_fram_builders.py`, A.U24.49), reader `BMP3XX_Reader(i2c, address=_ADDR, cfg_path=cfg_path,
    log=LogConfig(manager, 10, None))`, `await reader.setup()` replaces the `pr.setup()` call and its `:1477-1482`
    comment (the logger is set up in the reader's own `setup()`, A.U10.10); the simulated reboot rebuilds the manager
    over the same chip memory through the same builder.
  - New L1 (A.U15.R03): `test_two_failed_reads_reset_the_chip_and_reapply_the_stored_config` (two injected burst-read
    faults, `inject_fault("readfrom_mem_into", OSError, EIO, times=2, match=_REGISTER_PRESSUREDATA)`: one `0xB6` to CMD,
    then OSR and IIR written with the stored values, one `code("W", "DEVICE_RECOVERY")`);
    `test_a_rejected_reset_logs_one_chip_set_error_and_writes_no_config` (ERR_REG cmd_err set: exactly one CHIP_SET
    entry, no W14, no OSR/IIR write); `test_a_config_read_failure_at_setup_runs_no_bus_rung`;
    `test_a_put_racing_the_recovery_ends_with_the_puts_value_in_the_chip` (a `PresOvers` PUT gated to land between the
    reset and the re-apply waits on `_set_lock` and ends with 8 in the chip and the store).
  - New L1 (A.U15.22 (2), A.U10.06): `test_a_pres_offset_put_during_a_conversion_does_not_change_the_stored_sample`
    (`get_pressure_and_temperature()` wrapped to await a `PresOffset` PUT mid-conversion; the stored `Pres` uses the
    offset captured before); `test_a_failed_read_keeps_the_last_good_sample_and_its_timestamp` (`set_utc_valid()`,
    `asy_base_classes._utc_valid = False` in `finally`, M.SRC_CORE.032's no-argument form; a good cycle then a NAKed one: `get_data()` equals the first sample, its `TS` unchanged);
    `test_a_read_before_the_first_sync_publishes_with_ts_none` (and steps no error streak: `_error_check()` sees the
    reader's `condition` exclude the trailing `TS`, M_SRC_SENS GAP-15).
  - New L1 (A.U15.24): `PresOffset` 450 on the planted 713.77 hPa reading → `Pres` 263.77, `SLPres` `None`, one
    `code("W", "DERIVED_DOMAIN")`; a second such cycle leaves one slot and `ErrCount` 2 (newest-entry rule); `PresOffset`
    10 → no entry.
- **Resolved**: A.U15.24's example (raw 1000 hPa, `PressOffset` 750) is outside the schema's ±500 hPa bound, so no
  write can store it; the same domain exit is produced by an in-schema offset on the file's planted reading (agent
  correction). A.U15.R03's "logs its own errno 12/13 as today" stands as written (A.U3.05's print-only reading dropped,
  OR140.a (7)).
- **Unit**: U15 (stages U2 numbers, U5 constructor, U10 setup/ladder/TS, U24 builder).
  A-C2 step order: A.U10.R01's part lands in U13, not U10 (it follows A.U10.R01's own change, which lands in U13).
- **Depends**: M.SRC_SENS.043, M.SRC_SENS.044, M.SRC_SENS.047, M.SRC_CORE.037, M.SRC_CORE.040 (as the fold reverts
  A.U3.03/A.U3.05); A.U2.03; [fold F11 M_GEN] (catalog names for the restored reader and streak codes).
- **Blast carried by**: four tiers of the mid-operation reset → M.TEST_UNIT in `test_bus_hazard_multi_device.py`
  (A.U15.R03, L1), A.U13.R02/A.U15.R03 (TWIN, HW_DEV); catalog W11/W14/W15 rows → A.U2.01 (GEN).
- **Kind**: test

### M.TEST_UNIT.018 Deinitialized-bus getter tests hold
- **From**: A.U13.09/A.U13.10 (read: `get_register_bytes()`/`get_bits()` keep the `None` contract the messages cover).
- **Site**: `tests/test_asy_bmp3xx_driver.py:1513-1560`.
- **Change**: none beyond the U10 names; the expected messages are unchanged in M.SRC_SENS.048 for these three paths
  (A.U10.45 renames only the `:502, :619, :628` raise texts; each assertion here is re-read against the final text at
  execution and follows it).
- **Resolved**: —
- **Unit**: U10.
- **Depends**: M.SRC_SENS.048.
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.019 Data getters, starters, timer arm and the PUT path
- **From**: A.U10.06 (`:1573-1597` numeric `TS`), A.U10.12 (`:1757-1759`, `:1820` comment), A.U24.61 (`:1613-1616`),
  A.U10.40 (`:1622` keys and the `_set_dict_cfg` bodies), A.U24.78 (`:1666`), A.U15.41 (`:1797-1842` hold; new L1),
  A.U24.07 (`all_timers.clear()` lines), A.U10.35/A.U10.44 names, A.U8C.05 (`:1808`), A.U4.02 (hold).
- **Site**: `tests/test_asy_bmp3xx_driver.py:1567-1842`.
- **Change**: `test_get_data_and_get_dict_data_reflect_a_stored_reading` calls `set_utc_valid()` first (`asy_base_classes._utc_valid =
  False` in `finally`, M.SRC_CORE.032). `test_get_cfg_schema_matches_the_full_schema`: `reader.get_cfg_schema() == _FULL_SCHEMA` (the
  source-read schema, M.TEST_UNIT.015); the `== reader.cfg_schema` line and the `:1612-1614` comment go.
  `test_push_callbacks_registered…` expects `{"SampleInterval", "PresOvers", "TempOvers", "FiltCoeff"}`. The
  `_set_dict_cfg` tests use the new keys; `:1666` → `inject_fault("writeto_mem", OSError, errno_mod.EIO, "no ACK on
  write")`. `test_push_wrapper_functions_reject…` names `_push_trigger_s`. `test_get_timer_starters_returns_the_trigger_timer_starter`
  → `test_trigger_starters_hold_the_trigger_timer_and_timer_starters_nothing`: `get_trigger_starters() ==
  [reader.start_timer]`, `get_timer_starters() == []`. Timer tests read `reader._trigger_timer`/`_base_trigger_event`;
  their `FakeTimer.all_timers.clear()` lines go (the after-each hook); the `wait_for(…, 1)` at `:1808` →
  `_EVENT_WAIT_S` (module constant tagged `# @tunable l1.asy_bmp3xx_driver_event_wait_s = 1`); the `:1818-1820` comment
  → "# Real rp2 Timer.init() raises OSError(ENOMEM) when the alarm pool is exhausted; start_timer() runs inside
  SystemService.start_timers()' trigger sequencing and must not raise into it." The two arm-failure tests keep their
  assertions and add `reader._base_trigger_event.is_set()` (the waiter is woken, A.U15.41). New
  `test_a_failed_trigger_arm_ends_the_trigger_task_with_one_timer_entry_and_a_restart_rearms` (both `OSError(ENOMEM)` and
  `MemoryError`, via `RaiseOnArm`): `start_timer()` under the raise, then `_trigger_loop()` as a task ends at once with
  exactly one `code("E", "TIMER")` entry; a restart without the raise performs one `Timer.init` and a `trigger()` sets
  `_read_event` after the configured period.
- **Resolved**: —
- **Unit**: U15 (stages U8C tag, U10 names/split/TS, U24 schema/inject/hook).
- **Depends**: M.SRC_SENS.046, M.SRC_CORE.037 (`_timer_failed`/`_timer_fault`), M.SRC_CORE.032 (`set_utc_valid`).
- **Blast carried by**: Part N row `l1.asy_bmp3xx_driver_event_wait_s` → A.U8.01 (SPEC).
- **Kind**: test

### M.TEST_UNIT.020 The trigger divider is tested through the shared loop
- **From**: A.U15.40 (`_base_trigger()` → the shared divider; `:1857-1858` comment), A.U10.44 (`_trigger_loop`),
  A.U10.35 (`_trigger_counter`, `_base_trigger_event`, `_read_event`), A.U8C.05 (`:1879`), A.U24.08 (tracked tasks).
- **Site**: `tests/test_asy_bmp3xx_driver.py:1845-1882`.
- **Change**: section comment → "# _trigger_loop() - the shared 1 Hz base tick divided down by the sample interval
  (SPECIFICATION.md C.9)."; the test → `test_trigger_loop_sets_the_read_event_once_the_configured_period_elapses`,
  starting `reader._trigger_loop()`; `wait_for(…, 1)` → `_EVENT_WAIT_S`; assertions unchanged on the private names.
- **Resolved**: A.U15.40 names the shared coroutine `_divide_trigger()`, A.U10.44 `_trigger_loop()` — M.SRC_SENS.045
  settles `SensorReader._trigger_loop()` (its GAP-8).
- **Unit**: U15 (stage U10 rename).
- **Depends**: M.SRC_SENS.045, M.SRC_CORE.039.
- **Blast carried by**: the shared divider's own L1 (n = 1 and 3) → M.TEST_UNIT in `test_base_classes.py` (A.U15.40).
- **Kind**: test

### M.TEST_UNIT.021 Reader-level setters log CHIP_SET
- **From**: A.U2.10 (`:1920, :1940` 18/20 → 13).
- **Site**: `tests/test_asy_bmp3xx_driver.py:1885-1928`.
- **Change**: `ErrNum[-1] == 18` and `== 20` → `== code("E", "CHIP_SET")`; the builders' `setup()` replaces the
  in-scenario `pr.setup()`.
- **Resolved**: —
- **Unit**: U2 (numbers; `code()` form in U24 with A.U2.03's helper — the helper lands in U2, so U2).
  A-C2 step order: A.U2.10's part lands in U3, not U2 (it follows A.U2.10's own change, which lands in U3).
- **Depends**: M.SRC_SENS.047.
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.022 Reader-loop tests: the private loop ends, returns nothing
- **From**: A.U10.44 (`_read_loop`), A.U15.43 (`None`), A.U8.07 + A.U31.11 (`:1983` comment), A.U10.06 (`TS` needs a
  sync), A.U10.R01 (the rung inside the give-up run), A.U24.08.
- **Site**: `tests/test_asy_bmp3xx_driver.py:1931-2021`.
- **Change**: both tests start `reader._read_loop()`; the happy test calls `set_utc_valid()` (flag reset in `finally`) before
  asserting `data.TS is not None`, its `:1983` comment → "# let _init_bmp()'s reset settle (_RESET_SETTLE_MS) pass";
  `test_read_loop_gives_up_and_returns_false_after_max_errors` → `…_gives_up_and_ends_after_max_errors`, asserting the
  task is done and returned `None`, and that the log ends with `code("E", "GIVE_UP")`.
- **Resolved**: —
- **Unit**: U15 (stage U10 name).
  A-C2 step order: A.U10.R01's part lands in U13, not U10 (it follows A.U10.R01's own change, which lands in U13).
- **Depends**: M.SRC_SENS.046.
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.023 The address sweep calls the renamed method
- **From**: A.U15.27 (`:2019`).
- **Site**: `tests/test_asy_bmp3xx_driver.py:2023-2058`.
- **Change**: `bmp.get_altitude` → `bmp.get_pressure_altitude` in the sweep list; the rest holds (the sweep exercises
  every public method; the reset and the new OSR read stay on `0x77`).
- **Resolved**: —
- **Unit**: U15.
- **Depends**: M.SRC_SENS.048.
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.024 The unwritable-config test uses the shared write counter
- **From**: A.U4.06 (`:2040-2076` → `WriteCountingOpen`), A.U2.07 (`:2072` 4 → `code("E", "CFG_FILE_WRITE")`),
  A.U2.10 (`:2071` "12 not in" — 12 is CHIP_GET after the renumbering), A.U3.05 dropped (OR140.a (7); the reader logs
  nothing here either way: its config is valid on the defaults); OR136.a (1) (the one setup write of the absent file
  into the missing directory is the CFG_FILE_WRITE entry) — A-C review fold.
- **Site**: `tests/test_asy_bmp3xx_driver.py:2062-2072`.
- **Change**: the local `counting_open` and the `config_manager.open` swap become `with
  WriteCountingOpen(asy_config_manager) as counter:` (`tests/_write_counters.py`), asserting `counter.writes == 0`;
  `:2071` → the BMP3XX log holds no entry (`ErrCount == 0`); `:2072` → `CFGMGR_BMP3XX`'s newest entry is `code("E",
  "CFG_FILE_WRITE")`. The builder's `setup()` replaces `cfgmgr.setup()`.
- **Resolved**: —
- **Unit**: U4 (stage U2 codes).
- **Depends**: M.SRC_CORE (config manager codes, A.U2.07).
- **Blast carried by**: —
- **Kind**: test

## tests/test_asy_dns_client.py

End state: the resolver's tests against M.SRC_NET.020-024 — `ipv4_to_int()` (its one test home), `_build_query()`'s
RFC 1035 refusals, `resolve_ipv4(host, dns_servers, timeout_ms, tries, *, pr)` over the caller's servers only, port 53
redirected by the shared `tests/_udp_port_redirect.py`, the teardown warning, and the cancel sweep.

### M.TEST_UNIT.025 File harness: shared run, port band, address shim, port redirect, logger
- **From**: A.U24.08 (`run()`), A.U24.70 (`:31-37` allocator → `tests/_port_bands.py`), A.U18.12 (`_ResolvingAsyUDPSocket`
  `:45-65` goes; the address shim imported once), A.U18.45 (the port redirect replaces it and counts constructions),
  A.U18.10 (`:67-77` fallback swap goes), A.U18.13 (`conn_tries` leaves the doubles), A.U18.15 (a `pr` for every call),
  A.U10.29 (read: names this file's wrapper as the precedent A.U18.11 generalises), A.U10.38 (`UDPSocket`).
- **Site**: `tests/test_asy_dns_client.py:1-77`.
- **Change**: imports `from asy_dns_client import _build_query, _parse_response, ipv4_to_int, resolve_ipv4`, `from
  _async_harness import run`, `from _port_bands import PortAllocator`, `from _udp_port_redirect import
  redirect_udp_port`, `from asy_print_log import PrintLogHistory`, and the address shim module applied once at import
  (A.U18.12's new location on `sys.path`). `_next_port`/`make_port()` → `_PORTS = PortAllocator("test_asy_dns_client")`,
  `_PORTS.next()` at each use. `_resolved()` stays for the fake server's own raw socket only, its comment → "# This
  Unix build's raw bind()/sendto() need getaddrinfo()'s opaque sockaddr (SPECIFICATION.md F.7); only the fake server's
  own socket uses it." (2 lines; the `cast` comment stays). `_ResolvingAsyUDPSocket`, `_RealAsyUDPSocket`, the permanent
  `asy_dns_client.AsyUDPSocket` swap, `_UNREACHABLE_LOOPBACK_FALLBACK` and the `_FALLBACK_DNS_SERVERS` assignment and
  its comment go. New `def _make_pr() -> PrintLogHistory` (an in-memory logger named "DNSTEST", the
  `tests/test_captive_dns.py:25-26` shape). Every networked test runs inside `with redirect_udp_port(asy_dns_client, 53,
  port) as redirect:` (the helper's construction counter is `redirect.constructed`).
- **Resolved**: A.U18.12 ("the shim covers the address") and A.U18.45 ("the port-redirect wrapper … also replaces
  `_ResolvingAsyUDPSocket`") describe one replacement: the shim rewrites the address, the redirect maps the port.
- **Unit**: U18 (stage U24: harness, port band).
  A-C2 step order: A.U24.70's part lands in U25, not U24 (it needs A.U24.65, which lands in U25).
- **Depends**: M.SRC_NET.023, M.SRC_NET.026; TEST_HELP `tests/_udp_port_redirect.py` (A.U18.11/A.U18.45),
  `tests/_port_bands.py` (A.U24.70), `tests/_async_harness.py`; the shim's move (A.U18.12, TWIN/TOOL).
- **Blast carried by**: `pyproject.toml` `mypy_path` for the shim → A.U18.12 (TOOL); port table row → A.U24.70 (TEST_HELP).
- **Kind**: test

### M.TEST_UNIT.026 One home for the dotted-quad parser's tests
- **From**: A.U18.08 (`:7, 81-105` rewritten; `tests/test_captive_dns.py:77-122, 607-630` move here).
- **Site**: `tests/test_asy_dns_client.py:80-105`; new section after it.
- **Change**: the section banner `_is_ipv4_literal` → `ipv4_to_int`; the two tests become
  `test_ipv4_to_int_accepts_every_valid_dotted_quad` (`ipv4_to_int(host) is not None` over the same hosts) and
  `test_ipv4_to_int_rejects_hostnames_and_malformed_input` (`is None` over the same list); the six
  `test_ipv4_to_int_*` tests (`:77-122`, the wrong-type test among them) move here verbatim from
  `tests/test_captive_dns.py` (their expected integers are RFC 791 arithmetic, unchanged), importing `ipv4_to_int` from
  `asy_dns_client`; the `_bad_ipv4_values()` list (`:607-628`) stays in the captive-DNS file, whose four matrix tests
  iterate it (D-T20).
- **Resolved**: —
- **Unit**: U18.
- **Depends**: M.SRC_NET.021.
- **Blast carried by**: the moved tests' removal from the captive-DNS file → M.TEST_UNIT in `test_captive_dns.py`.
- **Kind**: test

### M.TEST_UNIT.027 `_build_query()` tests: RFC 1035 refusals, the store fact
- **From**: A.U24.58 (`:171-177`, `:186-189` comments), A.U10.41 (`:173` "NTP_Host allows 1024 characters"), A.U18.09
  (new refusals and the 253/254 boundary pair; the two label tests hold).
- **Site**: `tests/test_asy_dns_client.py:108-194`; new tests after `:194`.
- **Change**: `:171-177` comment → "# A dot-free label of 64+ octets: RFC 1035 SS3.1's 63-octet limit refuses it here,
  whatever the caller checked / # (resolve_ipv4() is public; the NTPHost PUT's hostName shape check refuses it
  earlier)." `:186-189` comment → A.U24.58's text: "# A label past 255 octets: MicroPython stores n & 0xFF into the
  bytearray without raising (py/binary.c:512-521, / # v1.29.0), so the query would carry a wrong length byte; the guard
  rejects it before the store." (test name `…_past_the_bytearray_byte_range` kept). New
  `test_build_query_refuses_an_empty_label_a_trailing_dot_and_an_empty_name` (`b"a..b"`, `b"pool.ntp.org."`, `b""` →
  `ValueError`); `test_build_query_accepts_a_253_octet_name_and_refuses_254` (labels 63, 63, 63, 61 accepted, wire 255;
  63, 63, 63, 62 refused).
- **Resolved**: A.U24.58's replacement text named `NTP_Host` and "used to" (history); the merged comment states the
  current mechanism with the renamed key (A.U10.40) and A.U10.41's shape check.
- **Unit**: U18 (stage U24 comment at `:186-189`).
- **Depends**: M.SRC_NET.022; A.U10.41 (`hostName` shape).
- **Blast carried by**: SPEC F.1 truncation fact → A.U24.58 docs (SPEC).
- **Kind**: test

### M.TEST_UNIT.028 `resolve_ipv4()` over a real loopback fake server
- **From**: A.U18.45 (the nine `port=` calls drop it), A.U18.10 (`:449-520` multi-server rewrites), A.U18.15
  (`pr=_make_pr()` on every call; teardown-failure L1), A.U18.09 (refused names construct no socket), A.U10.41 (`:534`
  comment), A.U24.76 (`FakeDNSServer` → `_FakeDNSServer`), A.U24.33 (the event-mask fact for the `answer_once` comment),
  A.U8C.06 (tags), A.U35.48 (cancel sweep), M.SRC_NET.023 (the construction `try` is removed as unreachable).
- **Site**: `tests/test_asy_dns_client.py:319-615`.
- **Change**:
  - Tags as A.U8C.06 writes them, on the surviving literals: `_PROMPT_RETURN_MAX_MS = 200` (`:332`),
    `_FAKE_SERVER_WAIT_MS = 2000` (`answer_once`'s default), `_FAKE_SERVER_POLL_MS = 5`, `_REPLY_TIMEOUT_MS = 1000`,
    `_NO_REPLY_TIMEOUT_MS = 100`, `_BAD_REPLY_TIMEOUT_MS = 300`, `_FALLBACK_TIMEOUT_MS = 200`,
    `_CNAME_REPLY_TIMEOUT_MS = 500`, each tagged `# @tunable l1.asy_dns_client_<…> = <v>`; the `udp.conn_tries_default`
    mirror tags of `:57, :548` have no site left (both doubles go) and are not written.
  - `test_resolve_ipv4_literal_ip_returns_immediately…`: `pr=_make_pr()`, inside the redirect; adds
    `redirect.constructed == 0` (the structural proof) beside the elapsed bound.
  - `_FakeDNSServer`: the `answer_once` comment `:334-340` → "# Checks each event's mask: poll.ipoll() returns an
    iterator, always truthy (extmod/modselect.c:583-594, v1.29.0)." (the "almost certainly POLLOUT" guess goes; the
    code already reads the mask).
  - The success, no-server, garbage, NXDOMAIN, parse-raising and CNAME tests: `port=` dropped, run inside
    `redirect_udp_port(asy_dns_client, 53, port)`, `pr=_make_pr()`.
  - `…falls_back_to_the_second_server_when_the_first_is_unreachable` → `…tries_the_callers_servers_in_order`:
    `dns_servers=("10.255.255.254", _HOST)`; `…skips_unset_and_malformed_dns_server_entries`: `dns_servers=("0.0.0.0",
    "", "not-an-ip", _HOST)`, and `redirect.constructed == 1` (the skipped entries open nothing);
    `…no_servers_at_all_and_no_reachable_fallback_returns_none` → `…with_no_servers_returns_none_and_opens_no_socket`:
    `dns_servers=()`, `redirect.constructed == 0` (no built-in server). The fallback-swap `try`/`finally` blocks go.
  - `…memoryerror_building_the_query_returns_none` holds (`pr=`). `…overlong_dns_label_returns_none…`: comment → "# A
    300-octet name cannot come from the NTPHost PUT (253 characters, hostName shape); resolve_ipv4() is public and
    refuses it itself."; asserts `None` and `redirect.constructed == 0`; plus the three A.U18.09 refused names
    (`"a..b"`, `"pool.ntp.org."`, a 254-character name) each → `None` with no construction.
  - `_RaisingAsyUDPSocket` and `test_resolve_ipv4_malformed_port_construction_returns_none_not_an_exception` are removed
    with the product's construction `try` (M.SRC_NET.023: the port is the constant 53 and `server` a validated `str`,
    so no input reaches it — the guarantee replacing the pin is the constructor's own tuple check, A.U18.12, tested in
    `tests/test_asy_udp_socket.py`).
  - New `test_a_failed_socket_teardown_logs_one_warning_and_keeps_the_answer`: the redirect's socket class made to
    report `disconnect()` `False` (its `close()` raising through the file's `_RaisingSocketModule`-style double); the
    lookup still returns the planted IP and the passed `pr` holds exactly one `code("W", "SOCKET_TEARDOWN")`.
  - New `test_cancelling_a_resolve_at_each_await_leaves_no_socket_open` (A.U35.48's `cancel_at_each_await()` from
    `tests/_cancel_sweep.py`): build = fake server + redirect, start = `resolve_ipv4(...)`, invariants = every socket
    the redirect constructed is disconnected and the fake server closed; the path's sockets are real loopback fds, so
    the real poll inside `UDPSocket` is allowed (CLAUDE.md's hang rule concerns non-fd objects).
- **Resolved**: the shared wrnno 11 is `SOCKET_TEARDOWN` = 12 after M.SRC_SENS.043's resolution (U15's `DERIVED_DOMAIN`
  keeps 11) — the test names it by catalog name, so the number follows the catalog.
- **Unit**: U18 (stages U8C tags, U24 names, U35 sweep).
- **Depends**: M.SRC_NET.023, M.SRC_NET.029; M.TEST_UNIT.025; TEST_HELP `tests/_cancel_sweep.py` (A.U35.48).
- **Blast carried by**: Part N rows → A.U8.01 (SPEC); catalog wrnno → A.U2.01 (GEN).
- **Kind**: test

## tests/test_asy_fram_allocation_budget.py

### M.TEST_UNIT.029 Per-binary budgets; the tautology test goes; blank-read shape updated
- **From**: A.U24.42 (3) (`:3-5` header, `:89-93` removed), A.U16.09 (`:65-66` comment), A.S0930.17 (Blast:
  "re-derive its bound"), A.U24.08 (`run()`), A.U24.49 (`make_fram_manager()`), A.U5.02 (`:59` construction), A.U10.37 +
  A.U10.38 (names), A.U16.05 + A.U30.16 (read: budgets are ceilings and hold; `_priced`'s collect is an allowed
  measurement baseline).
- **Site**: `tests/test_asy_fram_allocation_budget.py:1-99`.
- **Change**: header comment `:3-5` → "# Absolute figures are binary-dependent, not board figures: plain runs use
  build-standard; --coverage runs / # build-settrace, which inflates every figure 4-5x - one budget per binary
  (SPECIFICATION.md E.5.2)." (2 lines). `:32-34` → "# Measured 2026-09-18, mock tier, median of five, ~15% margin:
  build-settrace 296,448 B blank / 234,592 B valid; / # build-standard 28,864 / 20,512 - the pair whose ratios carry to
  the board." (the "was" figures go with the test that read them). Imports `from asy_print_log import
  PrintLogHistoryStore`, `from asy_fram_manager import FRAMManager` (typing only), `from _async_harness import run`,
  `from _fram_builders import make_fram_manager`; `_rig()` builds the manager with `make_fram_manager()` (the shared
  builder owns the constructor shape A.U5.02 changes) and asserts its `setup()`. The blank test's comment `:65-66` →
  "# A blank chip: setup()'s _read() finds no valid copy, so _write() lays down both. 14 byte-level / # commands over 54
  CS cycles - the most expensive shape the boot batch ever asks for." `test_the_budgets_are_not_trivially_satisfied` is
  removed: two constant comparisons that cannot fail; the budgets' power is proven once by the B3 campaign's planted
  per-call allocation in the FRAM path (A.U35.04; OR21.a (2): no permanent control arm) — that plant is the guard the
  retired test pretended to be. The two budgets are re-measured at the landing tree of U16 (A.U16.09 shrinks the blank
  read; A.S0930.17 adds one registry slot per chunk at construction, outside the priced window) and the comment's
  figures follow the measurement; a budget is never widened without the measurement that justifies it (OR30.a (3)).
- **Resolved**: —
- **Unit**: U24 (stages: U16 comment and re-measure with A.U16.09; U10 names).
- **Depends**: M.SRC_CORE (FRAM manager/`print_log` renames), TEST_HELP `tests/_fram_builders.py`, `_async_harness.py`.
- **Blast carried by**: the planted-allocation proof → A.U35.04 (B3); `tests_scripts/test_gc_collect_sites.py` allowed
  row `_priced` → A.U30.16 (TSC).
- **Kind**: test

## tests/test_asy_fram_driver.py

End state: `FRAM_SPI` tests against M.SRC_CORE.100-109 — identification retried, partial protection reported, WREN
retried, the chip-loss probe, bus-down statuses, both locks for every hold, `verify_present()` bounded by
`wait_for_ms` on driven time, catalog names for every code; the same-device FRAM bus-hazard L1 stays here (A.U24.27).

### M.TEST_UNIT.030 Harness, builders and the 256 KB fake
- **From**: A.U24.08 (`run()`), A.U24.76 (`make_bus`/`make_fram`/`setup_fram` → `_make_bus`/`_make_fram`/`_setup_fram`),
  A.U24.22 (`FakeMB85RS64V(size=)`; new L1 at `0x3FFF0`), A.U10.37 (`asy_print_log`), A.U10.21 (`setup()` → `True`),
  A.U16.22 (read: `:57` `FRAM_SPI.get_size()` stays).
- **Site**: `tests/test_asy_fram_driver.py:1-48`; every `max_size=0x40000` construction; new test after `:260`.
- **Change**: imports `from asy_print_log import PrintLogHistory`, `from _async_harness import run`; the three builders
  take the private names; `_make_fram(max_size=…)` constructs the chip fake with the matching `size=` (A.U24.22's
  factory) so a 256 KB `FRAM_SPI` runs over 256 KB of fake memory with 3-byte addresses; `_setup_fram()` asserts
  `await fram.setup() is True`. New `test_a_write_and_read_near_the_top_of_the_256kb_part_round_trip_with_a_3_byte_address`:
  `set_values(b"top!", 0x3FFF0)` then `get_values()` equal, and the fake's SPI log shows the 4-byte opcode+address
  header.
- **Resolved**: —
- **Unit**: U24 (stage U10 names/setup).
- **Depends**: TEST_HELP `tests/_fram_chip_fake.py` `size=` (A.U24.22).
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.031 Identification: three attempts, one warning, partial protection reported
- **From**: A.U16.R02 (setup-failure traces show three RDID cycles; new retry L1), A.U16.15 (new partial-protection
  L1), A.U2.09 (codes).
- **Site**: `tests/test_asy_fram_driver.py:55-260`; new tests after `:260`.
- **Change**: the RDID-mismatch tests keep their `OSError`/`RuntimeError` expectations; any that assert the SPI log
  expect `_ID_ATTEMPTS` (3, via `src_const`) RDID cycles before the raise. New
  `test_setup_succeeds_when_the_chip_answers_garbage_once_then_its_id` (a one-shot garbage RDID, then the right ID →
  `True`, one `code("W", "FRAM_ID_RETRIED")`). New `test_a_partly_protected_status_register_is_reported_and_writes_refused`
  over statuses 0x04, 0x08, 0x0C, 0x84: after `setup()` `get_write_protected()` is `True`, one `code("E",
  "FRAM_WP_PARTIAL")`, `set_values()` inside `async with fram:` returns `False` with `code("W",
  "FRAM_WRITE_PROTECTED")`; 0x80 (WPEN only): `get_write_protected()` `False` and one FRAM_WP_PARTIAL; then
  `set_write_protected(value=False)` clears the register to 0x00 and a write succeeds.
- **Resolved**: —
- **Unit**: U16.
- **Depends**: M.SRC_CORE.106; TEST_HELP fake (one-shot `rdid_response`).
- **Blast carried by**: dead-chip scenario three RDIDs → A.U16.R02 (TEST_HELP); L2 → A.U16.R02 (TWIN).
- **Kind**: test

### M.TEST_UNIT.032 WEL: the one retry, the loss probe, the chip gone mid-run
- **From**: A.U16.R01 (existing `drop_wren` tests keep w26; new one-shot drop), A.U16.R03 (new loss-probe L1), A.U2.09.
- **Site**: `tests/test_asy_fram_driver.py:353-419`; new tests after `:419`.
- **Change**: the four existing WEL tests hold (persistent `drop_wren` drops both WRENs → aborted, w26); none asserts a
  trace. New `test_a_write_lands_when_only_the_first_wren_is_dropped` (`drop_next_wren = 1`: the write lands, the SPI log
  shows WREN, RDSR, WREN, RDSR, WRITE…, one console line from `pr.evt`, no w26 entry) and
  `test_a_write_is_refused_when_both_wrens_are_dropped` (`drop_next_wren = 2`: w26, memory untouched). New
  `test_a_chip_gone_silent_mid_run_is_probed_once_and_marked_lost` (the fake switched silent, SO stuck 0x00, and again
  with 0xFF: the second anomalous write probes RDID once, `initialized` is `False`, one `code("E", "FRAM_CHIP_LOST")`,
  `fram.lost.is_set()`, and later `get_values()`/`set_values()` add no SPI traffic); `…an_anomaly_with_a_matching_id_keeps_the_chip_up`
  (the probe's RDID matches: the anomaly count resets, `initialized` stays `True`); `…after_a_loss_ten_writes_add_no_log_entry`
  (ten further `set_values()` → no FRAM-log entry beyond the one FRAM_CHIP_LOST — the entry guards keep callers off a
  lost chip).
- **Resolved**: —
- **Unit**: U16.
- **Depends**: M.SRC_CORE.103; TEST_HELP fake (`drop_next_wren` count, silent switch — A.U16.R01/A.U16.R03).
- **Blast carried by**: L2/L3 halves → A.U16.R01/A.U16.R03 (TWIN, HW_DEV); four tiers for the FRAM (same-device only)
  → this file (L1), A.U16.R01's twin case, HW_DEV CS-hijack cases.
- **Kind**: test

### M.TEST_UNIT.033 Write protection: both locks, exclusion proven
- **From**: A.U16.10 (existing WP cases hold; new exclusion L1), A.U16.16 (read: `wp_pin` cases hold, the fake's
  `Pin.init(value=)` is A.U13.03's), A.U2.09 (95 → `code("E", "FRAM_WP_MISMATCH")`, 83 → FRAM_WEL_NOT_SET).
- **Site**: `tests/test_asy_fram_driver.py:421-605`, `:690-708`; new test after `:605`.
- **Change**: existing assertions hold. New `test_set_write_protected_and_setup_wait_for_a_held_driver_lock`: a task
  holds `async with fram:` on an `asyncio.Event` gate; `set_write_protected(value=True)` started in a second task leaves
  the fake chip's status unchanged until the gate opens, then applies; likewise a second `setup()`.
- **Resolved**: —
- **Unit**: U16.
- **Depends**: M.SRC_CORE.105, M.SRC_CORE.106.
- **Blast carried by**: flash/bench WP cases run unchanged → A.U16.10 (HW_DEV, HW_BENCH).
- **Kind**: test

### M.TEST_UNIT.034 `verify_present()`: driven lock timeout, lost on a failed probe
- **From**: A.U10.26 (the lock-busy test on driven time), A.U16.R03 (6) (a failed `verify_present()` sets `lost`),
  A.U2.09 (97 → `code("E", "LOCK_TIMEOUT")`, 96 → NOT_INIT).
- **Site**: `tests/test_asy_fram_driver.py:607-670`, `:776-792`.
- **Change**: `test_verify_present_false_reverts_to_uninitialized…` also asserts `fram.lost.is_set()`, and `setup()`
  again clears it (`:640-649`). The lock-busy test (`:652-670`) installs `DrivenTime` on `asy_fram_driver` (A.U35.10's
  `wait_for_ms` shim), starts `verify_present()` inside `async with fram:`, `await clock.advance(999)` → not done,
  `advance(1)` → `False`; `initialized` still `True`; exactly one `code("E", "LOCK_TIMEOUT")`; its comment `:653-658` →
  "# verify_present() takes the driver lock itself: inside an existing `async with fram:` it waits out its bounded /
  # timeout on driven time instead of hanging (asyncio.Lock is not reentrant)." (the "sits out the real ~1s" text
  goes).
- **Resolved**: —
- **Unit**: U16 (stage U35 `DrivenTime` — A.U35.10's helper must land before U16's rewrite of this test, or the test
  is written in U35; order: A.U35.10 is a TEST_HELP helper — staged here as U35).
- **Depends**: M.SRC_CORE.107; TEST_HELP `tests/_driven_time.py` (A.U35.10).
- **Blast carried by**: SPEC F.2 → A.U10.26 (SPEC).
- **Kind**: test

### M.TEST_UNIT.035 A bus that goes down later is reported, not raised
- **From**: A.U13.08 (`:823-842` → returns `False` and logs bus-down, renamed), A.U13.09, A.U16.04 (new L1).
- **Site**: `tests/test_asy_fram_driver.py:794-843`; new test after `:843`.
- **Change**: section banner `:794-797` → "# Construction errors raise at boot (asy_spi_driver.py's contract); a bus
  that goes down later is reported by status, never raised." The two construction tests hold. `:823` →
  `test_bus_deinit_mid_operation_returns_false_and_logs_bus_down`: after `fram._spidev.spi.deinit()`, `async with fram:
  get_values(bytearray(1), 0)` returns `False` and the log holds exactly one `code("E", "FRAM_BUS_DOWN")`; its comment
  → "# A deinitialised bus is reported as bus-down by the driver (bool SPI results, C.3), not raised." New
  `test_verify_present_and_set_write_protected_report_a_bus_down_after_setup`: each returns `False`, one
  FRAM_BUS_DOWN entry per call, nothing raised.
- **Resolved**: the pinned `RuntimeError` is the behaviour A.U13.08 replaces; the new status assertions are its guard
  (OR111.a (2)).
- **Unit**: U13 (stage U16 for the new `verify_present`/WP case, which needs M.SRC_CORE.105/.107).
- **Depends**: M.SRC_CORE.104, .105, .107; M.SRC_SENS (SPI `available`, `session_begin()` → `False`).
- **Blast carried by**: `tests/test_asy_fram_manager.py:1409-1436` → M.TEST_UNIT in that file (A.U13.08).
- **Kind**: test

### M.TEST_UNIT.036 Persisted-logging tests name catalog codes
- **From**: A.U2.09 (`:908-1053` numbers), A.U36.544 (`:1034` "WP8:" prefix), A.U3.01 (newest-entry rule read: each
  test causes one event).
- **Site**: `tests/test_asy_fram_driver.py:894-1053`.
- **Change**: history/`ErrNum` literals → catalog names: 89/90/92/94/96 → `code("E", "NOT_INIT")`, 91/93 →
  `code("E", "BAD_ARG")`, 95 → `code("E", "FRAM_WP_MISMATCH")`, 99 → `code("E", "CONTRACT")`, `0x80 + 82`/`0x80 + 83`
  → `0x80 + code("W", "FRAM_WEL_NOT_SET")`, `0x80 + 81` → `0x80 + code("W", "FRAM_WEL_STUCK")`, 84 → `code("W",
  "FRAM_WRITE_PROTECTED")`; `:1052` → `[code("E", "CONTRACT"), code("W", "FRAM_WRITE_PROTECTED")]`. `:1034-1036`
  comment → "# "Currently write protected" (a benign, expected refusal, as the manager's "communication paused") and
  "access / # not locked" (a caller contract violation, so an errno) both persist." (the "WP8:" label and the
  "replacing the print-only degrade" history go). The banner `:895-897` loses "(not initialized, … timeout)"'s list
  only if a code moved class (none did).
- **Resolved**: —
- **Unit**: U2 (numbers via A.U2.03's helper, which lands in U2) — stage U36 label pulled into U16's rewrite of the
  file's comments (M.SRC_CORE.109 does the same for the product).
- **Depends**: M.SRC_CORE.101; A.U2.03.
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.037 Lock names, the hazard interleaving gate, typed recorder
- **From**: A.U10.18 (`:1096, 1102, 1341, 1388` `asy_lock` → `session_lock`; `:1168` `async_lock` → `bus_lock`),
  A.U35.12 (`:1140`, `:1189` single-yield review), A.U28.28 (8) + A.U24.73 (`:1263` `Any` goes), A.U2.09 (`:1282, 1296,
  1311` numbers), A.U24.27 (read: the FRAM same-device tests stay here).
- **Site**: `tests/test_asy_fram_driver.py:1056-1312`.
- **Change**: lock attributes renamed. `:1140`: the writer awaits an `asyncio.Event` the reader sets after its first
  completed read (the "partway" claim becomes a gate); `:1189` keeps its one yield, its comment → "# one yield lets the
  competitor start and park (a limit, not an interleaving claim)". `record_warnings()`'s `capture(*args: object,
  wrnno: int = 0, **kwargs: object)` (the `noqa: ANN401` goes). The three warning-record tests expect `code("W",
  "FRAM_WRITE_PROTECTED")`, `code("W", "FRAM_WEL_NOT_SET")`, `code("W", "FRAM_WEL_STUCK")` with the messages of
  M.SRC_CORE.103 (unchanged texts).
- **Resolved**: —
- **Unit**: U16 (stages U10 names, U24 typing, U35 gate).
- **Depends**: M.SRC_CORE.102, .103.
- **Blast carried by**: `pyproject.toml` per-file ANN401 entry → A.U28.28 (TOOL).
- **Kind**: test

### M.TEST_UNIT.038 Two-lock entry/exit: the injected fault is asserted, the bound tagged
- **From**: A.U24.39 (RF282 `:1344-1374`), A.U8C.07 (`:1374` 1.0), A.U10.18 (names).
- **Site**: `tests/test_asy_fram_driver.py:1314-1390`.
- **Change**: `test_a_later_operation_still_works_after_a_failed_bus_lock_acquisition`: `first()`'s `OSError` is
  captured and asserted (`e.args[0] == 5`, `calls[0] == 1`) instead of passed; `wait_for(second(), _LOCK_WAIT_S)` with
  `_LOCK_WAIT_S = 1.0` (module constant, `# @tunable l1.asy_fram_driver_lock_wait_s = 1.0`); `asy_lock` →
  `session_lock` in both lock-leak asserts.
- **Resolved**: —
- **Unit**: U24 (stages U8C tag, U10 names).
- **Depends**: M.SRC_CORE.102.
- **Blast carried by**: Part N row → A.U8.01 (SPEC).
- **Kind**: test

## tests/test_asy_fram_manager.py

End state: the chunk layer's tests against M.SRC_CORE.080-093 — `FRAMManager`/`FRAMChunk`/`FRAMTimestampedChunk`, every
layer that meets a failure keeping its own persisted entry as at HEAD (OR140.a (7): the planned one-entry-per-fault
split of A.U3.04 is dropped; A-C review fold), the catalog's FRAM band, a tri-state read, blank blocks never marked busy, no `override_pause`, no episodes (the central newest-entry rule), bool-first
timestamped writes on `utc_now()`, the erase trio, the chip-watch task. **Code map for every assertion of this file**
(A.U2.09 + A.U3.04): 31/34 → `code("E", "FRAM_STATUS_BYTE")` (46), 36 → FRAM_STATUS_DISAGREE (47), 17/38 →
FRAM_CRC_FAILED (48), 46 → FRAM_DATA_CRC (49), 63/64 → FRAM_VERIFY (50), 73 → FRAM_COPIES_DIFFER (51), 83 → INIT
(10), 85/87 → CALLBACK (14), 26/47/58 → UNEXPECTED (23), 48/60/70/81/84 → BAD_ARG (21), w60/w70/w80 → `code("W",
"FRAM_PAUSED")` (25); 10/11/18/19/20/30/32/33/35/37/39/50/51(HEAD)/57/61/62/71/72/80 stay persisted entries of the
layer that logs them at HEAD, each asserted by the catalog name the fold gives it back ([fold F11 M_GEN]; A.U2.09's
"not allocated (a print after U3)" row no longer applies to them); 82/86/88 retire with their handlers.

### M.TEST_UNIT.039 Harness, builders, folded constants, names
- **From**: A.U24.08 (`run()`), A.U24.49 (`make_manager` → `tests/_fram_builders.make_fram_manager()`), A.U24.76
  (`make_bus`, `setup_manager`, `make_written_chunk`, `status_byte_addrs`, `fail_*_at`, `errnums` → `_`-names),
  A.U24.01 (`:26-31` `_STATUS_*` → `src_const`), A.U5.02 (the manager's `log=`), A.U10.37 + A.U10.38 (`FRAMManager`,
  `FRAMChunk`, `FRAMChunkBuffer`, `FRAMChunkTimestampedBuffer`, `asy_crc_checks`, `CRCPass`, `asy_print_log`), A.U10.18
  and A.U10.35 (`allocated_size` `:1309` → `_allocated_size`, `chunk.ntp_sync_callback` `:1929` →
  `_ntp_sync_callback`), A.U16.05 (`:1445`, `:2051` comments `LockableBuffer` → `RegionBuffer`).
- **Site**: `tests/test_asy_fram_manager.py:1-70`; the named lines.
- **Change**: imports `from asy_fram_manager import FRAMChunk, FRAMChunkBuffer, FRAMChunkTimestampedBuffer,
  FRAMManager`, `from asy_crc_checks import CRC8, CRC16, CRC32, CRCPass`, `from _async_harness import run`, `from
  _fram_builders import make_fram_manager`, `from _src_const import src_const`, `from _error_codes import code`. The
  `:26-28` comment → "# The chunk's status-byte values, read from source (tests/_src_const.py)."; `_STATUS_UNINIT/_IDLE/
  _BUSY = src_const("src/asy_fram_manager.py", "_STATUS_…")`. `_make_manager(max_size, history_length)` returns
  `make_fram_manager(max_size=…, history_length=…)`'s manager and chip (the builder passes `log=LogConfig(None,
  history_length, None)`). `_INJECTED_FAILURE` stays (a test sentinel, its comment correct).
- **Resolved**: —
- **Unit**: U24 (stages U5 constructor, U10 names).
- **Depends**: M.SRC_CORE.080, .091; TEST_HELP builders.
- **Blast carried by**: `tests_scripts/test_const_mirrors.py` → A.U24.02 (TSC).
- **Kind**: test

### M.TEST_UNIT.040 Allocator: layout within one build; the chunk layer logs into RAM
- **From**: A.U0.38 (V12) + A.U16.01 (`:90`), A.U16.13 (new L1), A.S0930.17 (read: allocator tests hold; one list slot
  per allocation).
- **Site**: `tests/test_asy_fram_manager.py:71-116`; new test after `:100`.
- **Change**: `:88-90` comment → "# Whichever get_chunk()/get_timestamped_chunk() call happens first claims the lower
  offset regardless of / # size, which is why call order must be fixed within one build." New
  `test_every_chunk_and_the_driver_log_into_the_managers_ram_history`: `type(manager.pr) is PrintLogHistory`,
  `manager.fram.pr is manager.pr`, and `chunk.pr is manager.pr` for a plain and a timestamped chunk.
- **Resolved**: A.U0.38 and A.U16.01 name the same sentence; one text (A.U16.01's Depends: "one wording").
- **Unit**: U16 (stage U0 for the comment).
- **Depends**: M.SRC_CORE.081, .091.
- **Blast carried by**: SPEC C.8 sentence → A.U16.13 (SPEC).
- **Kind**: test

### M.TEST_UNIT.041 Dual copy, status bytes and torn writes, by catalog code
- **From**: A.U2.09/A.U3.04 (`:235, 283, 325, 592, 614, 756, 1548, 1576, 2332`), A.U16.08 (`:329-331` comment and the
  owner tag), A.U16.09 (`:1538`, `:1686-1687` re-read against the mixed-pair rule; `:2509-2511` comment; new blank-read
  L1), A.U16.06 (new tri-state L1), A.U3.04 dropped (OR140.a (7): every layer keeps its own persisted entry; A-C review
  fold), A.U3.09 (new missing-buffer L1; its one-entry half dropped with A.U3.04), A.U26.43
  (blast: the seam count the reset-race seed script relies on; M.HW_DEV.060/.063 → TSC, placed here, gap pass G3).
- **Site**: `tests/test_asy_fram_manager.py:212-350`, `:984-1096`, `:1525-1580`, `:1644-1852`, `:2476-2584`; new
  tests after `:350`.
- **Change**: every code assertion follows the map above (e.g. `:235` `31` → `code("E", "FRAM_STATUS_BYTE")`, `:614`
  `73` → FRAM_COPIES_DIFFER); the multi-layer sequences (`:816-817` 10/61, `:838-839` 32/72, `:1054` 71, `:1082` 72,
  `:1673` 62, `:1717` 11, `:1761` 18, `:1783` 37, `:1830` 39, `:1850` 57) keep HEAD's per-layer entries, each by its
  catalog name, under the newest-entry rule (an identical newest code spends no slot). `:329-331` → "# A write torn between block 0 and block 1: both blocks valid (CRC_Pass, both status bytes
  IDLE) but / # different, and no generation counter says which is right, so the read fails rather than guesses /
  # (owner, 2026-07-18)." and the test asserts exactly one FRAM_COPIES_DIFFER entry. `:1538` and `:1686-1687` (UNINIT
  planted into one byte): a mixed pair still fails the consistency check (one FRAM_STATUS_DISAGREE) and the idle byte
  keeps its busy marker; a fully blank block is not marked. `:2509-2511` comment → "# A blank chip's whole read is two
  status-byte reads per block that find UNINIT and return, so the / # yield after that pair must come before those early
  returns." New: `test_a_never_written_chunk_read_twice_reports_uninitialised_both_times` (both `read_into()` `False`,
  both status bytes still 0x00, no FRAM-log entry; the same after `clear()`);
  `test_read_into_is_tri_state` (driver not initialised → `None`; both blocks with a bad status byte → `False`; a blank
  chunk → `False`; a failed repair write → `None`); `test_a_planted_fault_leaves_an_entry_at_every_layer_it_reaches`
  (driver not initialised, WEL not set, status byte BUSY, CRC mismatch in block 0 with a good block 1, both blocks
  invalid, verification mismatch — one operation each: the detecting layer's entry first, then each propagating
  layer's own, in HEAD's order, so the history shows how far the fault reached, OR140.a (7));
  `test_a_verify_pass_whose_block_read_fails_the_crc_logs_fram_data_crc` (FRAM_DATA_CRC among the entries);
  `test_an_unallocatable_check_length_logs_alloc_on_read_and_write` (`code("E", "ALLOC")` from the detecting site, the
  propagating layers' entries after it); `test_a_missing_chunk_buffer_logs_alloc` (A.U3.09's check, per-layer); the
  one-slot RF171 test (`…ten_writes_leave_one_slot…`) is not written (it needed A.U3.04's single entry);
  `test_one_chunk_write_is_five_driver_transfers_in_seam_order` (A.U26.43): the manager's driver `set_values_sync`
  wrapped by a recording instance attribute; one `_write_chunk()` (one block of the dual-copy write, the first one a
  `write_into()` makes) is exactly five calls, in the order the seed script's `SEAM` 1-5 names them — status byte 1
  BUSY, status byte 2 BUSY, payload+CRC, status byte 1 IDLE, status byte 2 IDLE (address and first byte asserted per
  call) — so a changed write sequence fails here before a flash round.
- **Resolved**: A.U3.04 is dropped by OR140.a (7) (owner, 2026-10-02: "upstream layers reacting to a downstream fault
  may encounter following errors … a notion of a traceback and blast radius of an error is actually desirable"); A.U2.09
  alone renames the sites, and the per-layer entries keep HEAD's order (A-C review fold). A.U26.43 asks for its
  seam-count check "read by `ast` or pinned by an L1 test with a recording fake"; the status writes go through one
  helper called per byte (`asy_fram_manager.py:244`), so an `ast` count of call sites is not the transfer count — the
  L1 form is taken (M.HW_DEV.060/.063 named TSC; gap pass G3).
- **Unit**: U16 (stages U2 numbers; the seam-count test with A.U26.43 in U26).
- **Depends**: M.SRC_CORE.082, .084, .085, .088, .090 (as the fold reverts A.U3.04's split); A.U2.03; [fold F11 M_GEN]
  (catalog names for the per-layer codes A.U2.09 left unallocated).
- **Blast carried by**: SPEC A.4 FRAM error flow keeps its per-layer entries (A.U3.04's text dropped, SPEC); L2 double
  read → A.U16.09 (TWIN).
- **Kind**: test

### M.TEST_UNIT.042 Pause: no override seam; the queued read fault proves the gate
- **From**: A.U16.19 (`:428-440`, `:1117-1130` deleted; `:387` → "pause"; `:1109`, `:1253-1254` unpause first),
  A.U24.78 (`:457` `inject_fault` shape; the chunk grows over the 32-byte DMA threshold; `pending("readinto") == 1`),
  A.U2.09 (`:470` 70 → FRAM_PAUSED), A.U3.12 (new L1: a commanded mempause's W25 spends one slot across chunks),
  A.U16.22 (read: `manager.get_pause()` stays).
- **Site**: `tests/test_asy_fram_manager.py:387-506`, `:1099-1135`, `:1234-1260`; new test after `:506`.
- **Change**: banner `:387` → "# pause"; the two override tests are deleted (the seam is gone: `invalidate()` is the
  one path past the pause and only the erase calls it, M.SRC_CORE.083); `:1099-1115` and `:1234-1260` unpause, then
  read/write. `:445-484`: `get_chunk(40, crc=CRC8())` (a 41-byte read, over the 32-byte DMA threshold),
  `chip.inject_fault("readinto", OSError, 5, "SPI RX overrun", times=1)`, after the paused read
  `chip.pending("readinto") == 1` (the discriminator its comment names), then unpaused the fault fires; `70` →
  `code("W", "FRAM_PAUSED")`. New `test_a_commanded_mempause_spends_one_slot_across_chunks` (two chunks, writes, reads
  and `clear()` while paused: one FRAM_PAUSED slot, `ErrCount` counting every refusal).
- **Resolved**: —
- **Unit**: U16 (stage U24 fault shape).
- **Depends**: M.SRC_CORE.082, .085, .088; TEST_HELP fake `pending()` (A.U24.78).
- **Blast carried by**: twin hazard file override lines → A.U16.19 (TWIN); device scripts → A.U16.19 (HW_DEV).
- **Kind**: test

### M.TEST_UNIT.043 Timestamped chunk: bool-first writes, `utc_now()`, signed age
- **From**: A.U16.18 (unpacks `:541-565, 645-650, 668-672, 702-709, 1242, 1253, 1269, 1358, 1874, 1886, 1905, 2093`;
  annotations), A.U10.06 (`:677-718` and `:1940-1974` removed with their handlers; tests expecting a valid timestamp call
  `set_utc_valid()`), A.U14.26 (its rename of those two tests — dropped with them, M.SRC_CORE.087 Resolved),
  A.U35.55 (`:2120-2195` removed), A.U2.09 (`:674` 85, `:1893` 81, `:1938` 87), A.U10.28 (b) (new L1, the manager
  half), A.U10.35 (`_ntp_sync_callback`).
- **Site**: `tests/test_asy_fram_manager.py:530-653`, `:655-718`, `:1209-1275`, `:1333-1372`, `:1853-1995`,
  `:2085-2200`.
- **Change**: every `ntp_synced, utc, write_ok = await chunk.write(…)` → `write_ok, ntp_synced, utc = …` and the
  tuple asserts reorder (`:650` → `(False, False, None)`); return annotations `tuple[bool, bool, int | None]`. Tests whose
  `_synced` write must store a real timestamp call `asy_base_classes.set_utc_valid()` first and reset
  `asy_base_classes._utc_valid = False` in `finally` (M.SRC_CORE.032's no-argument form). `:659-675` keeps its goal; the assertion → one `code("E", "CALLBACK")` entry, and its message (the "told
  apart from the read-path one (87)" claim goes — both paths are CALLBACK by class; the log message tells them apart).
  `:677-718` (`test_mktime_overflow…`) and `:1941-1974` (`…age_computation_overflow…`) are removed: `utc_now()` has no
  handler to pin — `mktime()`/`gmtime()` cannot raise for in-range years on target (G4/R15, M.SRC_CORE.032), the guard
  replacing them is that source fact plus `tests/test_base_classes.py`'s `utc_now()` cases. `:2120-2195` (`_RaisingPackInto`,
  `_RaisingUnpackFrom` and their two tests) are removed with the guards (A.U35.55: no failing input on target); the
  uninitialised-timestamp read path stays covered by the blank-chip reads here. `:1880-1893` → `code("E", "BAD_ARG")`;
  `:1923-1938` → `chunk._ntp_sync_callback`, `code("E", "CALLBACK")`. New
  `test_a_read_after_the_rtc_stepped_back_returns_a_negative_age` (synced write at T, the RTC set back 60 s through
  `DrivenTime`'s wall clock, read: `age == -60`; the expiry decision is SGP40's, M.TEST_UNIT in
  `test_asy_sgp40_driver.py`).
- **Resolved**: A.U10.06 vs A.U14.26 at the two handler tests → A.U10.06 (V.U18.R10, U18 register fix 10).
- **Unit**: U16 (stages U10 `utc_now()`/removals; U35's removal pulled into U16 with M.SRC_CORE.087).
- **Depends**: M.SRC_CORE.087, M.SRC_CORE.032.
- **Blast carried by**: SGP40 half of the negative age → A.U16.18/A.U10.28 (TEST_UNIT sgp40 file).
- **Kind**: test

### M.TEST_UNIT.044 Fault-injection, regression and edge tests by catalog code
- **From**: A.U2.09 (`:774-790`, `:798-980`, `:1393-1436`, `:1444-1520`), A.U3.04 dropped (OR140.a (7): every layer
  keeps its own persisted entry; A-C review fold), A.U13.08 (`:1409-1436`), A.U24.56 (`:886` tag), A.U8C.08 (`:751`).
- **Site**: `tests/test_asy_fram_manager.py:720-980`, `:1376-1520`.
- **Change**: `:751` `wait_for(…, 5)` → `_READ_WAIT_S` (`# @tunable l1.asy_fram_manager_read_wait_s = 5`). `:774-790`
  → `test_oversized_write_persists_a_bad_arg_entry` (`code("E", "BAD_ARG")`; the "84 not colliding with clear's 80"
  claim becomes the two catalog names, both still persisted). `:886` → "# Intended, accepted behaviour, not a defect
  (owner, 2026-09-11; SPEC A.4):"; `:909-910` → the read refused (`None`), the driver's write-protected warning and the
  chunk layer's own entry persisted as at HEAD, data intact after unprotect. `:952-975`: write/read/clear each fail, the
  log holds the driver guard's `code("E", "NOT_INIT")` and each chunk layer's own entry per operation, as at HEAD, under
  the newest-entry rule. `:1393-1407` → `code("E", "INIT")`.
  `:1410-1436` → `test_chunk_operations_fail_cleanly_when_the_bus_is_deinitialized_mid_run`: each operation fails, the
  log holds `code("E", "FRAM_BUS_DOWN")` (the driver's status, M.SRC_CORE.104) and the chunk layer's own entry, no
  UNEXPECTED entry; its comment → "# A deinitialised bus is reported by the driver as bus-down; the chunk layer fails
  the operation and logs its own entry."
- **Resolved**: —
- **Unit**: U16 (stages U2, U8C tag, U13 bus-down, U24 tag text).
- **Depends**: M.SRC_CORE.082-.085, .104 (as the fold reverts A.U3.04's split); [fold F11 M_GEN] (catalog names for
  the per-layer codes).
- **Blast carried by**: Part N row → A.U8.01 (SPEC).
- **Kind**: test

### M.TEST_UNIT.045 Accessor and slice tests of removed methods go; RX overrun restamped
- **From**: A.U16.22 (`:1995-2024`), A.U16.23 (`:2027-2048`; `:2072`, `:2081` lines), A.U16.06 (overrun assertions), A.SDEP.08 (`:2204` "MicroPython
  1.29's" restamped at the new pin), A.U2.09 (`:2228, 2248, 2268` 47 → UNEXPECTED, `:2332` 31).
- **Site**: `tests/test_asy_fram_manager.py:1995-2120`, `:2204-2335`.
- **Change**: the three accessor tests and the two `get_crc_buf()` slice tests are deleted with their methods (no
  product caller; OR46.a (2)); section comment `:1995-1996` → "# The buffers' remaining accessors."; `:2072`, `:2081`
  `get_crc_buf()` lines go. `:2204` → "# The rp2 SPI RX-overrun raise site (<pin version>; SPECIFICATION.md F.5.2),
  driven through the live path …" with the version the pin re-check confirms. Overrun assertions → `code("E",
  "UNEXPECTED")` where the caught raise is the subject. The two overrun tests over the 40-byte chunk gain (A.U16.06):
  one overrun → `read_into()` `True`, block 0 rewritten, no "Invalid data in block 0" console line; a sticky overrun →
  `read_into()` `None` and the chip's memory unchanged by the read path except the status bytes.
- **Resolved**: —
- **Unit**: U16 (stage: A.SDEP.08's re-stamp lands with the pin move, U0/U37).
- **Depends**: M.SRC_CORE.086, .089.
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.046 The status-byte errno spread: one code per condition, every layer's entry kept
- **From**: A.U2.09 (the `err=` arithmetic goes), A.U3.04 dropped (status-byte read/write failures keep persisting,
  OR140.a (7); A-C review fold).
- **Site**: `tests/test_asy_fram_manager.py:2336-2470`.
- **Change**: banner → "# Status-byte failures, branch by branch: one code per condition (Part C.7.1); each layer the
  failure reaches keeps its own entry (owner, 2026-10-02)." The six tests keep their injection points and their HEAD entries, each asserted
  by the condition's catalog name instead of its per-byte number: idle-mark write failure on byte 1 / byte 2 → `write()`
  `False` with the chunk layer's status-byte write entry; busy-mark byte-2 read failure → read `None` with the status-byte
  read entry; byte 2 neither idle nor uninit (`0x7F`) → `code("E", "FRAM_STATUS_BYTE")`; busy-mark byte-2 write failure
  → the status-byte write entry; clear's byte-2 failure → `clear()` `False` with clear's entry. Names drop the HEAD
  numbers (`…reports_errno_19` → `…logs_the_status_byte_write_failure`, …).
- **Resolved**: the per-byte numbers they pinned are retired by A.U2.09 (one code per condition); the planned print-only
  split (A.U3.04, read from OR56.a (1)) is dropped by OR140.a (7), so the entries stay.
- **Unit**: U16.
- **Depends**: M.SRC_CORE.084, .085 (as the fold reverts A.U3.04's split); [fold F11 M_GEN] (catalog names for the
  status-byte read/write and clear codes).
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.047 Episode tests become central-rule tests
- **From**: A.U3.02 (`:2585-2658`), A.U3.01.
- **Site**: `tests/test_asy_fram_manager.py:2585-2658`.
- **Change**: banner → "# The central newest-entry rule (asy_print_log.py, SPECIFICATION.md C.7.1): a repeated identical
  code spends no / # new slot; ErrCount counts every event." `_warnings()` → `_entries()` (number, type pairs).
  `…keeps_failing_persists_one_warning_per_episode…` → `…keeps_failing_spends_one_slot`: five corrupted reads leave one
  `code("E", "FRAM_DATA_CRC")` slot and `ErrCount` 5. `…a_clean_read_ends_the_episode…` → `…a_recurrence_after_recovery_stays_one_slot`
  (OR35.b: one slot, `ErrCount` 2). `…a_held_mempause_persists_one_refusal…` → paused writes and reads are one code
  (FRAM_PAUSED): one slot, `ErrCount` 8.
- **Resolved**: —
- **Unit**: U3.
- **Depends**: M.SRC_CORE (print_log newest-entry rule), M.SRC_CORE.082/.088.
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.048 Erase, watch task and power-cut proofs at the chunk layer
- **From**: A.S0930.21 (b)-(c) (erase result, erased chip boots like a new one, all-zero block never validates),
  A.S0930.25 (1)-(2) (structural and enumerated power cuts), A.S0930.23 (read: its mock-tier half is
  `test_bus_hazard_multi_device.py`), A.U16.17 + A.U16.R03 (watch-task L1), A.U24.22 (`size=` fakes).
- **Site**: new section at the end of `tests/test_asy_fram_manager.py`.
- **Change**: `test_erase_chip_zeroes_every_byte_in_ascending_units` (8 KB and 256 KB fakes seeded with valid logger
  chunks and 0xA5: `erase_chip(step)` `True`, `chip.memory == bytearray(size)`, `size // 256` unit writes at ascending
  addresses, each after every chunk's pass-1 status writes, `step` called once per chunk and unit);
  `test_an_erased_chip_boots_like_a_new_one` (fresh manager and loggers: every logger `initialized`, `ErrCount` 0, no
  error entry); `test_an_all_zero_block_never_validates_even_with_an_idle_status` (status 0x01 0x01 over zero data and
  CRC, CRC8 and CRC32 chunks: read not `True`); `test_erase_refuses_a_write_protected_or_uninitialised_chip`;
  `test_a_failed_invalidate_stops_before_pass_2`. Power cuts with the fake's `cut_after_bytes` knob and a test-local
  `PowerCut(BaseException)`: structural (after pass 1 every allocated block's status bytes read 0x00, and no pass-2
  data byte precedes the last pass-1 status write in the SPI log) and enumerated (every pass-1 status byte; the first,
  a middle and the last byte of every pass-2 unit overlapping an allocated block: a fresh manager restores each ring
  exactly or blank, logs only FRAM_STATUS_DISAGREE or nothing, and the next write lands). Watch task:
  `test_the_watch_task_waits_while_healthy_and_ends_on_a_loss` (`get_task_starters() == [manager.start_watch_chip]`
  always; healthy → still running after `fram.lost` stays clear; a loss → the task ends; a restart with the chip back
  re-runs `setup()` and waits; a restart after a never-set-up chip prints the escalation line and ends).
- **Resolved**: A.U16.17's "returns `[]` when initialised" is superseded by A.U16.R03 (4) (always one starter,
  M.SRC_CORE.092); the task returns `None` (M.SRC_CORE.092 Resolved), so the test asserts it ended, not `False`.
- **Unit**: U16 (A.S0930's erase tests land with M.SRC_CORE.083's U16 stage; the watch task with A.U16.R03).
- **Depends**: M.SRC_CORE.083, .092; TEST_HELP fake `cut_after_bytes`, `size=` (A.S0930.25, A.U24.22).
- **Blast carried by**: SystemService-level erase sequence, refusals and races → M.TEST_UNIT in `test_system_service.py`
  (A.S0930.21/.22/.24/.25); L2 → A.S0930.27 (TWIN); next-write re-persists the RAM ring → `tests/test_print_log.py`
  (A.U16.R03).
- **Kind**: test

## tests/test_asy_fram_wire_trace.py

### M.TEST_UNIT.049 Header: the contract, its owner account, the one deliberate change
- **From**: A.U0.40 (L74, `:2` relabelled agent), A.U16.12 (`:2` archive pointer → SPEC A.4), A.U16.09 (header names
  the blank-read change).
- **Site**: `tests/test_asy_fram_wire_trace.py:1-2` (module docstring).
- **Change**: line 2 → "A restructure of asy_spi_driver.py/asy_fram_driver.py/asy_fram_manager.py must leave these
  byte-identical - the contract the 2026-09-18 heap restructure was held to (agent, 2026-09-18); what each protocol
  element is for is SPECIFICATION.md A.4 (owner, 2026-09-18)."; a third line "One deliberate change since: a blank
  block is read without a busy marker (agent, 2026-09-29)." (docstring 3 lines).
- **Resolved**: A.U0.40 and A.U16.12 rewrite different halves of the same line and A.U16.09 appends; one text.
- **Unit**: U16 (stage U0 relabel).
- **Depends**: M.TEST_UNIT.050.
- **Blast carried by**: `tests_scripts/test_comment_block_cap.py` (holds).
- **Kind**: doc

### M.TEST_UNIT.050 Goldens: rp2's MSB number, the blank read without busy markers, bool-first write
- **From**: A.U24.23 (`:33-34` `_INIT_EVENT`), A.U16.21 (`:35` comment), A.U16.09 (`_GOLDEN_BLANK_SETUP` `:163-238`; the
  count `74 → 54`; `:65-66`-style comment in the count test), A.U16.12 (`:499` comment), A.U16.18 (`:451`),
  A.U24.08 (`run()`), A.U5.02 + A.U10.37/A.U10.38 (`FRAMManager`, `FRAMTimestampedChunk`, `asy_crc_checks`,
  `asy_print_log`; `_rig()`'s construction), A.U16.R01/A.U16.R02/A.U16.06/A.U13.08/A.U25.16 (read: goldens hold — one
  WREN, one RDID, no wire change).
- **Site**: `tests/test_asy_fram_wire_trace.py:7-40`, `:148-157`, `:163-238`, `:428-462`, `:498-507`.
- **Change**: `_INIT_EVENT = "init 1000000/0/0/8/1"` with the comment "# The one bus config SPIDevice.__aenter__
  applies (firstbit MSB = 1 on rp2), as one recorded event."; `_WRDI` comment → "# asy_fram_driver.py's _CMD_WRDI is
  module-private". `_rig()` builds `FRAMManager(bus, 1, max_size=0x2000)` (default `log`). `_GOLDEN_BLANK_SETUP`
  loses the four `w:06 / w:05 r:02 / w:0200xx w:02 / w:04 / w:05 r:00` groups that follow each blank status read
  `r:00`; `test_cs_cycle_counts_are_the_measured_figures` asserts blank 54 (the other four counts unchanged) and its
  comment `:499-501` → "# Every one of these cycles stays by design (SPECIFICATION.md A.4). / # The restructure removed
  allocations, not CS cycles, so a change here is a protocol change and not an / # optimisation." `_collect()`:
  `assert written[0]  # (wrote_ok, ntp_synced, utc) - the clock is deliberately unsynced`.
- **Resolved**: —
- **Unit**: U16 (stages U10 names, U24 `_INIT_EVENT` with A.U24.23's fake change).
- **Depends**: M.SRC_CORE.084, .087; TEST_HELP `tests/machine.py` SPI `MSB = 1` (A.U24.23).
- **Blast carried by**: SPEC A.4 sentences → A.U16.09/A.U16.11/A.U16.12 (SPEC).
- **Kind**: test

### M.TEST_UNIT.051 The status bytes' endurance computed from the recorded trace
- **From**: A.U16.11.
- **Site**: new test after `tests/test_asy_fram_wire_trace.py:507`.
- **Change**: `test_status_bytes_outlast_the_parts_endurance_at_the_bus_ceiling` as A.U16.11 writes it: from
  `_collect()`'s traces, the cell operations on one status-byte address per chunk `_write()` (2) and valid `_read()` (3)
  are counted and asserted; the lifetime at one block operation per (write commands × 2,833 µs + read commands × 783 µs,
  the recorded valid-read mix, SPEC F.5.8's minima) — ≈ 13.7 ms, 3 cell operations each — against 10^12 (MB85RS64V p.17)
  exceeds 100 years (the computed figure ≈ 144 years is stated in the ≤ 3-line comment; the 100-year floor is a stated
  bound, not a tuned value).
- **Resolved**: —
- **Unit**: U16.
- **Depends**: M.TEST_UNIT.050 (the valid trace is unchanged by the blank-read change).
- **Blast carried by**: SPEC A.4 endurance sentence → A.U16.11 (SPEC).
- **Kind**: test

## tests/test_asy_i2c_driver.py

End state: the I2C wrapper's tests against M.SRC_SENS.006-013 — bool results for every transfer and write, the new
read helpers, the boot bus clear, `clear()`/`recover()` with their status bits and `recoveries` sequence, the bus and
session lock names, and the fake's rp2 probe/scan semantics.

### M.TEST_UNIT.052 Harness and names
- **From**: A.U24.08 (`run()`), A.U24.20 (`make_i2c()` `:26` resets the id), A.U24.76 (`make_i2c`/`fake` →
  `_make_i2c`/`_fake`), A.U10.18 (`async_lock` → `bus_lock` 18 sites, `device.asy_lock` → `session_lock`), A.U24.78
  (`:484, :521, :533` fault shape), A.U8C.09 (`:719` 1.0, `:843` 0.2), A.U24.01 principle (`:1067` `_SCRATCH_SIZE` via
  `src_const`), A.U31.12 (read: probe tests run the real 200 ms wait, unchanged).
- **Site**: `tests/test_asy_i2c_driver.py:1-33`; the lock, fault and wait lines named.
- **Change**: `from _async_harness import run`; `_make_i2c()` → `FakeI2C.reset_id(0)` then the construction; every
  lock reference renamed (`:362` → `device.session_lock is i2c.bus_lock`); `inject_fault("readfrom_into", OSError,
  errno.EIO, "no ACK")` form at the three sites; `_GATHER_WAIT_S = 1.0` (`# @tunable l1.asy_i2c_driver_gather_wait_s =
  1.0`) and `_DEADLOCK_WAIT_S = 0.2` (`# @tunable l1.asy_i2c_driver_deadlock_wait_s = 0.2`) at `:719`, `:843`; `:1066`
  `size = src_const("src/asy_i2c_driver.py", "_SCRATCH_SIZE") + 8` (comment → "# one past the shared scratch, read from
  source").
- **Resolved**: —
- **Unit**: U24 (stages U8C tags, U10 names).
- **Depends**: M.SRC_SENS.009, .013; TEST_HELP fakes.
- **Blast carried by**: Part N rows → A.U8.01 (SPEC).
- **Kind**: test

### M.TEST_UNIT.053 Deinit returns `True`; a dead bus answers `False`/`None` by contract
- **From**: A.U13.16 (`:40-58, 563-568` `deinit() is True`), A.U13.07 (`:69-98`, `:234-238`, `:343-352`, `:571-586`;
  `:140, 417, 479-490, 993` assert `True`; new "every completed transfer returns `True`"), A.U24.21 (`:72` holds).
- **Site**: `tests/test_asy_i2c_driver.py:35-160`, `:216-352`, `:408-436`, `:479-490`, `:544-610`, `:970-1000`.
- **Change**: `deinit()` asserted `is True` (twice for the idempotence test); after deinit `readfrom_into`/`set_bits`/
  `set_register_struct`/`writeto_then_readfrom` and the device forwarders assert `False` (getters keep `None`, `scan()`
  `None`, `writeto` `None`); `:234-238` malformed format → `set_register_struct(...) is False`; `:343` →
  `test_set_register_struct_type_mismatch_returns_false_instead_of_raising`; `:571-586` mid-session `readinto` →
  `False`, buffer untouched; each completed call at `:140, :417, :479-490, :993` asserts `True`. New
  `test_every_completed_transfer_and_write_returns_true` (readfrom_into, writeto_then_readfrom, set_bits,
  set_register_struct, device readinto/write/write_then_readinto).
- **Resolved**: —
- **Unit**: U13.
- **Depends**: M.SRC_SENS.009, .011, .012, .013.
- **Blast carried by**: driver callers → M.TEST_UNIT for each driver file.
- **Kind**: test

### M.TEST_UNIT.054 Probe and scan follow rp2's zero-length transfer
- **From**: A.U24.21 (`:112`, `:157`; zero-length writes raise `ENODEV`), A.U24.38 (`:378` probe ACKed), A.U10.45 +
  A.U10.21 (probe message and `setup() -> True`).
- **Site**: `tests/test_asy_i2c_driver.py:107-113`, `:147-160`, `:378-406`, `:494-506`, `:881-885`.
- **Change**: `:107` scan lists `0x10` only (registers, minus NAK) — unchanged result, now through the probe;
  `:147-160`: `scan()` after a NAKed address returns the short list without raising (asserted, not only "no raise").
  `test_probe_succeeds_when_device_acks`: `setup()` is `True` and the log holds exactly one zero-length `writeto` to
  `0x50`. Probe-failure tests assert the message `f"no I2C device at address: {0x50:#x}"` (M.SRC_SENS.013). `:881-885`:
  `writeto(0x50, b"")` on an address with no device raises `OSError(ENODEV)`; with `fake.attached.add(0x50)` it returns
  0. New `test_scan_on_a_busy_bus_returns_an_empty_list`.
- **Resolved**: —
- **Unit**: U24 (fake semantics; stage U10 message, U13 bool).
- **Depends**: TEST_HELP `tests/machine.py` `attached`, zero-length semantics (A.U24.21).
- **Blast carried by**: SCD30/SGP40 probes in other files gain `attached.add()` → A.U24.21 (each driver file's M-change).
- **Kind**: test

### M.TEST_UNIT.055 The read helpers: bytes copy, caller's buffer, one scratch view
- **From**: A.U13.10 (`get_register_bytes()` L1), A.U30.07 (`get_register_into()` L1), A.U30.21 (identity and partial
  view L1; the scratch view is one object), A.U13.01 (read: `:1022-1060` hold).
- **Site**: new tests after `tests/test_asy_i2c_driver.py:1070`.
- **Change**: `test_get_register_bytes_returns_a_copy_of_exactly_length_bytes` (copy: mutating the scratch afterwards
  leaves it unchanged; `None` on no bus and `length <= 0`; over `_SCRATCH_SIZE` uses the allocating fallback; a bus
  `OSError` propagates); `test_get_register_into_fills_exactly_the_callers_buffer` (shared scratch untouched; `False` on
  no bus and on an empty buffer; `OSError` propagates); `test_a_full_buffer_transfer_hands_the_fake_the_callers_object`
  (identity for whole buffers in `readinto`/`write`, a view of the right range for a partial one) and
  `test_the_scratch_view_is_one_object_for_the_bus_life`.
- **Resolved**: —
- **Unit**: U30 (stage U13 for `get_register_bytes`).
- **Depends**: M.SRC_SENS.011, .012.
- **Blast carried by**: four tiers wire-identical → A.U13.10/A.U30.07/A.U30.21 (bus-hazard files run unchanged).
- **Kind**: test

### M.TEST_UNIT.056 Boot bus clear, runtime `clear()`/`recover()`, the recoveries sequence
- **From**: A.U14.17 (a) (boot clear L1; OR113.a (1)), A.U13.R01 (the `clear()`/`recover()` L1 list), M_SRC_SENS GAP-2
  (`recoveries` wraps at `COUNTER_CAP`).
- **Site**: new section at the end of `tests/test_asy_i2c_driver.py`.
- **Change**: boot clear (through construction, read with `take_boot_clear_status()`): SDA high → no SCL edge, status
  0; SDA released after k pulses → k pulses, STOP, status 1; SDA held → 9 pulses, STOP, status 3, construction proceeds;
  SCL held past the timeout → no pulse, status 4; a later `init()` never clears; `take_boot_clear_status()` returns the
  value once, then 0. Runtime `clear()`: SDA high → no SCL edge, status 0, no construction, both pins end `ALT_I2C`
  with pull-up; k pulses → status 1; held → 9 pulses, STOP, status 3; SCL held beyond the timeout on the fake clock →
  status 4; a fake holding SCL k ms mid-pulse still sees nine effective pulses. `recover()`: the same cases followed by
  one re-construction with the stored `freq`/`timeout` (also after status 4); construction raising
  (`I2C.raise_on_construct`) → status 8 and `_i2c is None`. Each `clear()`/`recover()` steps `recoveries` once;
  `recoveries` at `COUNTER_CAP` (imported from `asy_base_classes`: a public `const()` name stays a module attribute) steps to 0. A session holding
  `bus_lock` delays `clear()`/`recover()` until it exits (gated), and a session started during either waits for it.
- **Resolved**: A.U13.R01's "each call increments once" with M.SRC_SENS.010's single step per public call.
- **Unit**: U13.
  A-C2 step order: stage U14 — the SCL-held timeout cases, which drive `ticks_us` through A.U14.34's fake time, land in U14; the pulse, STOP and status cases land in U13 with the clear.
- **Depends**: M.SRC_SENS.008, .010; TEST_HELP `tests/machine.py` `Pin` `OPEN_DRAIN`/`ALT`/`ALT_I2C`/scripted
  levels/value log (M.TEST_HELP.012's A.U13.R01 part, U13; A.U24.16 [follows]), per-id I2C state and
  `raise_on_construct` (M.TEST_HELP.013's A.U13.R01 part, U13; A.U24.20 [follows]), fake clock for `ticks_us` (A.U14.34;
  A.U35.10 [follows] replaces it in U35).
- **Blast carried by**: four-tier coverage of the bus rung → M.TEST_UNIT in `test_bus_hazard_multi_device.py`
  (A.U13.R02 L1), A.U13.R02 (TWIN, HW_DEV, HW_BENCH).
- **Kind**: test

### M.TEST_UNIT.057 Range parameters stay off the combined transfers
- **From**: A.U5.14 (`:79, 93, 142, 420, 486, 558, 979, 988, 996` pass none — unchanged), A.U28.27 (read: the `x != x`
  NaN idiom at `:320` keeps its comment; the ruff entry is TOOL's).
- **Site**: `tests/test_asy_i2c_driver.py:131-139`, `:869-880` (start/end on `readfrom_into`/`writeto` only).
- **Change**: none beyond M.TEST_UNIT.053's bool assertions — the sliced calls are `readfrom_into`/`writeto`, which keep
  `start`/`end` (M.SRC_SENS.012).
- **Resolved**: —
- **Unit**: U5.
- **Depends**: M.SRC_SENS.012.
- **Blast carried by**: `pyproject.toml` PLR0124 entry → A.U28.27 (TOOL).
- **Kind**: test


## tests/test_asy_isl29125_driver.py

### M.TEST_UNIT.058 Header, product-value reads, shared doubles and builders
- **From**: A.U24.01 (`:38-42` → `src_const`), A.U8C.10 (mirror tags `:39, :40, :42`), A.U15.28 (`:138-140`
  `make_protocol()` without `address=`), A.U24.49 + A.U31.09 (`_FastAsyncSleep` `:66-86`, `_RaiseOnArm` `:89-101` →
  shared), A.U24.08 (`run()` `:62-63`), A.U24.20 (`make_i2c()` `:113`), A.U24.07 (`FakeTimer.all_timers.clear()` `:778,
  828, 837, 846, 3280`), A.U24.73 (`Any` typing), A.U28.28 (1) (`:176` B905 noqa), A.U10.37 (TYPE_CHECKING imports
  `config_manager`/`print_log`), A.U10.10 (builders call `setup()`), A.U10.35 (`reader.isl` → `_isl`), A.U24.76 (role
  names), A.U2.03 (`code()`).
- **Site**: `tests/test_asy_isl29125_driver.py:1-185`, `:771-822`.
- **Change**: imports gain `from _async_harness import run, cancel`, `from _fast_sleep import FastAsyncSleep`, `from
  _fake_timer_arm import RaiseOnArm`, `from _src_const import src_const`, `from _error_codes import code`; the
  TYPE_CHECKING block imports `asy_config_manager`/`asy_print_log` and drops `Any`/`TypeVar`/`T` (the coroutine alias
  is `_async_harness`'s, A.U24.73). `:18-20` banner → "# FN8424 register/command copies, each citing its page: hardware
  facts kept as an independent source (tests/_src_const.py reads the project's own values)."; `:21-37` stay. `:38-42`
  → `_GAIN_RATIO_NOMINAL`, `_GAIN_RATIO_MIN`, `_GAIN_RATIO_MAX`, `_AR_DOWN_DIVISOR`, `_CAL_CONVERGE_N =
  src_const("src/asy_isl29125_driver.py", "<same name>")`, their trailing "mirrors" comments gone. The local
  `run()`, `_FastAsyncSleep`, `_RaiseOnArm` go; every use reads `run`, `FastAsyncSleep()`, `RaiseOnArm(exc)`.
  `make_i2c()` → `_make_i2c()` calling `machine.I2C.reset_id(0)` first. `make_protocol()`/`ready_protocol()` →
  `_make_protocol()`/`_ready_protocol()` building `ISL29125_I2C(i2c)`; `seed()`/`seed_healthy_chip()` keep their
  `address=_ADDR` parameter (the fake's register keys). `:174-175` comment and `# noqa: B905` go (`pyproject.toml`'s
  B905 entry carries the reason). `make_reader()` → `_make_reader()`: no `all_timers.clear()`, `run(reader.setup())`
  in place of `run(reader.cfgmgr.setup())`; `ready_reader()` → `_ready_reader()` writes `reader._isl._settle_until_ms
  = time.ticks_ms()` (module `time`), its `import time as _time` gone; `init_reader()`/`seed_cycle()`/`counts_burst()`/
  `fake()`/`mem_writes()`/`mem_reads()` keep their shape under `_`-names. `logged()`/`errors()`/`warnings()` stay (they
  filter by kind); every expected number they are compared with is written `code("E"|"W", <NAME>)`.
- **Resolved**: A.U8C.10's mirror tags vs A.U24.01's source reads — the source read wins: after A.U24.01 no literal is
  left to tag, and each value reads the product constant M.SRC_SENS.071 already tags (`isl29125.gain_ratio_min/max`,
  `isl29125.cal_converge_n`); the three tags are not written (the rows lose no product site).
- **Unit**: U24 (stages U10 names/setup, U15 address).
- **Depends**: M.SRC_SENS.071, .073, .085; TEST_HELP `tests/_src_const.py`, `_async_harness.py`, `_fast_sleep.py` (both
  `sleep` and `sleep_ms`), `_fake_timer_arm.py`, `machine.I2C.reset_id`.
- **Blast carried by**: `pyproject.toml` B905 entry → A.U28.28 (TOOL); `tests_scripts/test_const_mirrors.py` →
  A.U24.02 (TSC); ANN401 exemption → A.U24.73 (TOOL).
- **Kind**: test

### M.TEST_UNIT.059 Protocol-layer tests: comments, the settle wrap, bus down
- **From**: A.U30.07 (`:192-210`, `:705-712` hold), A.U13.10 (`:706-708` comment), A.U15.30 (`:634-636` comment),
  A.U14.34 + A.U15.35 (`:652-662` rewrite; new crossing case (a)), A.U24.78 (`:717`, `:730`), A.U13.09 (new: ISL writes
  raise on a bus that is down), A.U15.S01 (`:670-701` hold), A.U10.35 (`isl.i2c_isl29125` → `_i2c_isl29125`).
- **Site**: `tests/test_asy_isl29125_driver.py:187-765`.
- **Change**: `:634-636` → "# Two cycles: Table 7 starts the ADC at an I2C write to 0x01 and leaves open whether a
  conversion in flight restarts, so the second cycle is the margin; it costs one sample." `:706-708` → "# Named for the
  trap: one 6-byte burst, never three 2-byte reads, so the three channels come from one conversion."; its assertions
  hold (`readfrom_mem_into` is what the fake records as `readfrom_mem`). `inject_fault(op, OSError, errno_mod.EIO, "no
  ACK")`. `test_time_to_settle_stays_sane_across_a_ticks_wrap` → `test_time_to_settle_crosses_the_ticks_wrap`:
  installs `Ticks30Time` (`tests/_ticks30.py`) as `asy_isl29125_driver.time` with `now = 2**30 - 5`, arms a deadline
  10 ms ahead (it lands past the wrap); `time_to_settle_ms()` is positive at `now + 9`, `0` at `now + 11`; restored in
  `finally`; its `import time as _time` goes. New `test_a_passed_settle_deadline_never_ages_past_the_tick_horizon`
  (A.U15.35 (a)): same fake, a deadline armed, then `advance(3_600_000)` repeated until 2**29 + 1000 ms have passed,
  `time_to_settle_ms()` read once per step: 0 at every step, and `_settle_wait()` sleeps on none (a recording
  `sleep_ms`). New `test_every_protocol_write_raises_on_a_bus_that_is_down` (A.U13.09): `i2c.deinit()` on the asy
  wrapper, then `configure(resolution=12)`, `set_thresholds(0, 1000)` and `clear_brownout()` each raise `OSError` and
  the shadow still encodes 16 bit.
- **Resolved**: —
- **Unit**: U15 (stages U13 bus contract, U14 helper, U24 inject form).
- **Depends**: M.SRC_SENS.086; TEST_HELP `tests/_ticks30.py` (A.U14.34).
- **Blast carried by**: four tiers wire-identical (A.U30.07/A.U13.10 blasts: bus-hazard files run unchanged).
- **Kind**: test

### M.TEST_UNIT.060 Reader construction and init: catalog numbers, the init rungs, restart state
- **From**: A.U24.67 (`:826-827` comment), A.U2.12 (`:862`, `:897`), A.U3.05 dropped (OR140.a (7): `:875` keeps the
  reader's own entry beside the store's; A-C review fold), A.U10.R01 + A.U15.R04
  (`_init_failed()`/`_init_done()`; config-read failure runs no rung), A.U15.34 (new restart L1), A.U10.10.
- **Site**: `tests/test_asy_isl29125_driver.py:825-923`.
- **Change**: `:826-827` → "# Requirement 20, satisfied here or nowhere: every generated device's object graph is built
  against a fake holding no ISL registers." The three construction tests drop `all_timers.clear()`.
  `test_init_returns_false_and_logs_errno_10…` → `…logs_an_init_error_and_reinitialises_the_controller`: `errors()[-1]
  == code("E", "INIT")` and one `code("W", "BUS_RECOVERY")` (`_init_failed()`'s controller rung on `_recovery_bus`).
  `…errno_12_when_the_config_is_unreadable` → `…_config_is_unreadable_logs_in_both_layers`: the ISL29125 log's newest
  entry is its own config-read code (HEAD's 12, by the catalog name the fold gives it back), `CFGMGR_ISL29125` holds
  `code("E", "CFG_NOT_VALID")`, `reader._recovery_bus.recoveries` is unchanged (no rung). `…errno_13_when_applying_the_config_raises` → `…logs_chip_set…`: `code("E", "CHIP_SET")` then
  `code("W", "BUS_RECOVERY")`. `test_init_leaves_no_state_behind_after_a_failed_attempt` holds. New (A.U15.34):
  `test_a_restart_resets_the_output_filter` (filter 0.5 on, two samples stored, `_init_isl()` again: the next stored
  `Lux` equals that cycle's raw lux) and `test_an_edge_seen_before_a_restart_is_not_credited_after_it` (`_irq_fired =
  True`, `_init_isl()`, then a periodic-led switching cycle counts one periodic-only decision).
- **Resolved**: —
- **Unit**: U15 (stages U2 numbers, U10 ladder).
  A-C2 step order: A.U10.R01's part lands in U13, not U10 (it follows A.U10.R01's own change, which lands in U13).
- **Depends**: M.SRC_SENS.074, M.SRC_CORE.037 (as the fold reverts A.U3.05); [fold F11 M_GEN] (the restored code's name).
- **Blast carried by**: SPEC M.1.2 restart table → A.U15.34 (SPEC).
- **Kind**: test

### M.TEST_UNIT.061 The read loop and the streak: ladder, give-up, pre-sync cycles
- **From**: A.U10.R01 + A.U15.R04 (`:953`, `:2539` re-derived; new participant-rung L1), A.U10.44 (`_read_loop`),
  A.U15.43 (the loop returns `None`), A.U2.06 (`:1056` comment), A.U3.03 dropped (OR140.a (7): the streak entry and the
  brownout's two entries stay; A-C review fold), A.U10.35
  (`read_event` → `_read_event`), A.U24.08 (`_cancel_and_join` → `cancel`), A.U10.06 + GAP-15 lead ruling (pre-sync
  L1; direct `_error_check()` callers sync first).
- **Site**: `tests/test_asy_isl29125_driver.py:926-991`, `:1039-1057`, `:1597-1612`, `:2535-2592`.
- **Change**:
  - `test_read_loop_calls_error_check_exactly_once_per_cycle`: starts `reader._read_loop()` (the builder's `setup()`
    ran), sets `reader._read_event`, ends with `await cancel(task)`; the spy keeps its inline `method-assign` ignore.
  - `test_read_loop_exits_after_max_module_error_consecutive_failures` (`max_module_error=3`) →
    `…climbs_the_ladder_then_gives_up`: three failed cycles return `True`, the fourth `False`; the 2nd failure ran the
    participant rung once (`_reapply_configuration()` on the NAKed bus: one `code("E", "CHIP_SET")`, no
    `DEVICE_RECOVERY`), the 3rd the bus rung once (`reader._recovery_bus.recoveries` stepped by one, one
    `code("W", "BUS_RECOVERY")`), and the log ends `code("E", "GIVE_UP")`; each failed cycle also keeps the streak's own
    entry (by its catalog name), as at HEAD.
  - `test_a_dark_room_never_increments_the_error_counter` and `test_brownout_does_not_feed_the_leaky_bucket…` call
    `set_utc_valid()` first (flag reset in `finally`): both call `_error_check(results)` directly, where a pre-sync
    `TS` would count. `:1056` → `assert errors(counters) == []  # a dark cycle is no failure`. The brownout-bucket test
    keeps HEAD's two entries by name: `code("W", "ISL_BROWNOUT")` from the driver, then the streak's own entry from the
    all-None sample (each layer the brownout reaches logs, OR140.a (7)).
  - `test_the_read_loop_stores_healthy_samples_and_gives_up…` (`max_module_error=2`): drives `reader._read_loop()`
    (its `_read_event.wait` patched with the inline ignore), asserts the coroutine returned `None`; the two healthy
    cycles reach the store and publish; the 2nd failed cycle ran the participant rung (the healthy fake takes the
    re-apply: one CONFIG1-3 burst, one `code("W", "DEVICE_RECOVERY")`) and the log ends `code("E", "GIVE_UP")`; its
    `:2536-2538` comment names `_read_loop()`.
  - `test_the_read_loop_gives_up_immediately_when_the_chip_is_not_there_at_all`: `_read_loop()` returns `None` without
    entering the wait; the log holds `code("E", "INIT")` and one `code("W", "BUS_RECOVERY")`.
  - New (A.U15.R04): `test_two_failed_status_reads_reapply_the_shadow_and_rearm_the_thresholds` (two cycles with the
    status read failing, no BOUTF: after the 2nd `_error_check()` one CONFIG1-3 burst from the shadow and one threshold
    burst, one `code("W", "DEVICE_RECOVERY")`); `test_a_raising_reapply_burst_logs_one_chip_set_and_no_recovery_warning`
    (the burst write faulted: exactly one `code("E", "CHIP_SET")`, no `DEVICE_RECOVERY`).
  - New (GAP-15): `test_a_read_before_the_first_sync_steps_no_streak_and_publishes_ts_none` (no sync; a healthy cycle
    through `_read_loop()`: `_err_cnt_internal == 0`, `get_data()` carries the values and `TS is None`); and
    `test_an_unsettled_cycle_is_no_failure` (A.U15.22 (4): a CONFIG1 write stream keeping `time_to_settle_ms() > 0`
    past the bound — `_read_isl()` returns all `None` with `_unsettled_cycle` set, `_read_loop()` steps no streak and
    stores nothing; the next settled cycle publishes).
- **Resolved**: A.U15.R04's "see the re-apply at the 2nd failure" and A.U10.R01's rung order give the expected logs
  above; GAP-15's per-reader condition (M.SRC_SENS.083: `results[0] is None and not self._unsettled_cycle`) is what
  the two new cycles pin.
- **Unit**: U15 (stages U10 ladder/`_read_loop`/`TS`).
  A-C2 step order: A.U10.R01's part lands in U13, not U10 (it follows A.U10.R01's own change, which lands in U13).
- **Depends**: M.SRC_SENS.075, .076, .083, M.SRC_CORE.032, .037 (as the fold reverts A.U3.03); [fold F11 M_GEN] (the
  streak's catalog entry).
- **Blast carried by**: the mid-operation re-apply case → M.TEST_UNIT.238 (L1) and M.TWIN.102 (L2); twin Run 5c holds →
  A.U15.R04 (SCR).
- **Kind**: test

### M.TEST_UNIT.062 Read path and outputs: CalLight, the nested body, the bus-fault re-read
- **From**: A.U15.36 (`:1068` key set; new band-edge L1), A.U24.57 (new nested-body L1), A.U10.06 (`:1018`; last-sample
  `TS`), A.U15.22 (new L1: a failed read keeps the last sample), A.U2.12 (`:1209`), A.U15.29 (new ID re-read L1),
  GAP-15 (`:999-1001` comment).
- **Site**: `tests/test_asy_isl29125_driver.py:994-1125`, `:1175-1267`.
- **Change**:
  - `:1000-1001` → "# The narrow tuple keeps CCT out: it is legitimately None in a dark room, and the read loop's
    condition counts only a cycle whose measured values are gone."
  - `test_the_results_tuple_carries_the_range…`: `:1018` → `assert results[4] == _RANGE_HIGH_LUX  # the span` and
    `assert results[5] is None  # TS: no NTP sync in this test` (the HEAD comment named index 4 the timestamp).
  - `test_store_produces_the_documented_nested_body`: the group's key set gains `"CalLight"`.
  - New `test_the_nested_body_carries_every_tuple_field_exactly_once` (A.U24.57): `reader._set_meas_data()` stores an
    `ISL29125` with a distinct value per field; a table maps `Red`/`Green`/`Blue` → `RGB.R/G/B`, `Hue`/`Sat`/`Bri` →
    `HSB.H/S/B`, every other field flat; `get_dict_data()["ISL29125"]` holds each value once at its path and no other
    leaf, and the table's field set equals `ISL29125._fields`.
  - New (A.U15.36): `test_cal_light_marks_the_calibration_band_at_its_edges` — high range, `AutoRangeThresh` 85, `lo =
    fraction_to_counts(_down_thresh())`, `hi = fraction_to_counts(85.0)`: green `lo` → 2, `lo + 1` → 1, `hi - 1` → 1,
    `hi` → 3 (through `_read_isl()` + `_store_isl()`, read from `get_data().CalLight`); `RangeAuto` off → 0; a cycle that
    switches range → 0; and `_band_code(g) == 1` exactly where the calibration run accepts the scene at the same four
    edges (`_measure_gain_ratio()` with `queue_legs`).
  - `test_a_bus_fault_pattern_is_confirmed…`: `code("E", "ISL_BUS_FAULT") in errors(counters)`. New
    `test_a_raising_device_id_re_read_prints_and_adds_no_second_entry` (A.U15.29): the same all-ones cycle with the ID
    read faulted (`inject_fault("readfrom_mem", OSError, errno_mod.EIO, "no ACK", times=1, match=_REG_ID)`): exactly one
    persisted entry, `code("E", "ISL_BUS_FAULT")`, and one console line from `reader.pr.err` (spied with the inline
    `method-assign` ignore).
  - New `test_a_failed_read_keeps_the_last_good_sample_and_its_timestamp` (A.U15.22, OR94.a (13)): `set_utc_valid()`
    (reset in `finally`); a good cycle stored, then a cycle with the data burst faulted: `get_data()` equals the first
    sample, `TS` included.
- **Resolved**: —
- **Unit**: U15 (stages U2 number, U10 `TS`, U24 nested-body test).
  A-C2 step order: A.U2.12's part lands in U3, not U2 (it follows A.U2.12's own change, which lands in U3).
- **Depends**: M.SRC_SENS.072, .075, .077, .078, .081, .084.
- **Blast carried by**: `tests_scripts/test_measurement_field_tuple_agreement.py` → A.U24.57 (TSC); L2 dark/mid/bright
  `CalLight` → A.U15.36 (TWIN); `mockdata/dev.json` → A.U15.36 (WEB).
- **Kind**: test

### M.TEST_UNIT.063 Filter and store: the cached coefficient, the captured span
- **From**: A.U15.22 (3) (`:1127-1146` holds; `:1149-1175` goes; the store reads no config), A.U3.05 dropped (OR140.a
  (7); `:1168` goes with its test for A.U15.22 (3)'s reason anyway; A-C review fold), A.U11.24 (`:1141` `write_config`), A.U24.61 (`:1141` `cfg_schema`), A.U36.506 (read: the `None`
  cases are A.U15.22's), adherence (`:1847-1872`'s injection point no longer exists).
- **Site**: `tests/test_asy_isl29125_driver.py:1127-1172`, `:1847-1872`.
- **Change**: `test_output_filter_applies_only_when_filtcoeff_is_positive` holds; its `:1141` line →
  `run(reader.cfgmgr.write_config({"FiltCoeff": 0.1}))[0] is True` (kept: it persists the value the cache holds).
  `test_the_store_path_survives_a_config_read_that_fails_or_answers_the_wrong_shape` is removed — the store makes no
  config read, so its goal (a sample is never lost to a config read) holds by construction (M.SRC_SENS.078); the guard
  that replaces it is `test_a_restart_resets_the_output_filter` plus the filter test above, which read the coefficient
  the cycle captured. `test_a_rangeauto_push_landing_between_the_read_and_the_store_cannot_renormalise_the_sample`:
  the `get_float_values` patch goes (`_store_isl()` awaits nothing before it scales, so the patched read would never
  run and the test would pass without a push); the push lands between the two calls instead —
  `results = run(reader._read_isl())`, `assert run(reader.set_range_auto(flag=False)) is True`,
  `run(reader._store_isl(results))` — and the `0.30 < Green < 0.31` assertion holds (the span travels in `results`).
  Its comment → "# The span travels with the sample, so a RangeAuto push between read and store cannot renormalise
  it: 20000 counts on the 10000 lx range stay 0.305 of the span, not a clamped 1.0."
- **Resolved**: —
- **Unit**: U15 (stages U11 `write_config`, U24 schema accessor).
- **Depends**: M.SRC_SENS.078, .084, M.SRC_CORE.044.
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.064 The settle window: the bound's reason
- **From**: A.U15.22 (`:1291-1310` comment), A.U10.30 (`:1301, 1306` `__import__("time")`) dropped (OR141.a (2),
  OR142.a (3): this file is one of the host/test sites SPEC F.1 lists by name and the owner judges harmless — the
  loader stays, no change; A-C review fold), A.U0.07 (no function-level import statement remains at these lines).
- **Site**: `tests/test_asy_isl29125_driver.py:1269-1310`.
- **Change**: `:1292-1293` → "# The bound keeps the loop from starving; past it the cycle is discarded (see
  test_an_unsettled_cycle_is_no_failure)."; the four `__import__("time")` calls at `:1301, 1306` stay as written (an F.1
  named site). `test_no_sample_is_reported_during_the_settle_window` holds (its `asyncio.sleep_ms` swap stays local and
  restored in `finally`; the shared `FastAsyncSleep` patches `sleep_ms` as HEAD's did).
- **Resolved**: A.U10.30's rewrite of this file's dynamic site is dropped by OR141.a (2)/OR142.a (any change that
  rewrites a named loader to remove its dynamic import is dropped); the function-level-import moves elsewhere in the file
  are unaffected.
- **Unit**: U15 (the comment).
- **Depends**: M.SRC_SENS.079.
- **Blast carried by**: SPEC F.1's named list keeps `tests/test_asy_isl29125_driver.py` and the dynamic-import check
  allows it by name; `tests_scripts/test_import_placement.py` treats these two lines as that named site, not as `_PENDING`
  entries → A.U10's F.1 list and check (TSC, SPEC).
- **Kind**: test

### M.TEST_UNIT.065 Auto-range: catalog numbers, the parked INT, the dead-line re-arm, the dwell horizon
- **From**: A.U2.12 (`:1426-1445` 29/30, `:1479, 1504, 1546` w13), A.U24.78 (`:1419, 1431`), A.U10.35 (`reader.isl`),
  A.U15.32 (`wrnno`/`periodic_only`/`threshold_fired` tests hold; four new L1), A.U15.R05 (new re-arm L1), A.U15.35 (c)
  (dwell crossing), A.U0.07 (`:1365`, `:1377` local imports).
- **Site**: `tests/test_asy_isl29125_driver.py:1313-1547`; new tests after `:1547`.
- **Change**:
  - `:1365`/`:1377` use the module `time`; `reader.isl` → `reader._isl` throughout.
  - `test_a_failed_threshold_write_logs_errno_29_and_the_range_write_logs_errno_30` →
    `test_a_failed_threshold_write_and_a_failed_range_write_each_log_chip_set`: after both failures the ISL29125 log
    has `ErrCount == 2` and its newest entry `code("E", "CHIP_SET")` (one slot, A.U3.01); `_active_range` still
    `_RANGE_HIGH_LUX` after each.
  - `:1479`, `:1546` → `code("W", "ISL_PERIODIC_ONLY") in warnings(counters)`; `:1504` → `not in`.
  - `test_five_periodic_led_decisions_in_a_row_report_a_possibly_dead_interrupt` (A.U15.R05) also asserts one
    CONFIG1-3 burst (`configure(force=True)`) and one threshold burst after the fifth decision; then
    `_note_decision_source(threshold_fired=True)` clears `_int_rearmed`. New
    `test_the_interrupt_is_rearmed_once_per_dead_line_episode`: ten periodic-only decisions give two
    `ISL_PERIODIC_ONLY` warnings and one re-arm; an interrupt-led decision, then five more periodic-only ones, re-arm
    again.
  - New (A.U15.32): `test_an_int_the_peak_rule_overrules_is_parked_until_green_is_back_in_its_window` (high range,
    green 10, red 60000, status `RGBTHF` with `_irq_fired`: the cycle writes the CONFIG2-3 burst from 0x02 with INTSEL
    00 and sets `_int_held`; five periodic cycles write no CONFIG2-3 burst and raise no `ISL_PERIODIC_ONLY`; green above
    the down threshold re-arms with one CONFIG2-3 burst, INTSEL 01); `test_darkness_on_the_low_range_parks_the_zero_threshold`
    (all channels 0 with the flag: disarmed, stays disarmed while dark, re-armed at the first green ≥ 1 below the up
    threshold); `test_a_parked_int_stays_parked_across_a_periodic_down_switch` (INTSEL 00 and `_int_held` until green is
    inside the new range's window, then one re-arm burst; no `ISL_PERIODIC_ONLY` across five periodic switches while
    held); `test_set_range_auto_racing_a_parking_cycle_leaves_intsel_and_the_flag_agreeing` (`_switch_range` patched to
    yield once, with the inline `method-assign` ignore; `set_range_auto(True)` run as a task during it; afterwards
    `encode_shadow()[2] & 0x03 == _INTSEL_GREEN` exactly when `_int_held` is `False`).
  - New (A.U15.35 (c)): `test_a_switch_down_is_never_suppressed_by_a_week_old_switch_tick` — `Ticks30Time` installed,
    high range, dwell 10 s, a bright scene (green above the down threshold) evaluated once per simulated hour for 7
    days, then a dark scene: `_evaluate_range()` returns `_RANGE_LOW_LUX` at the first dark evaluation.
- **Resolved**: —
- **Unit**: U15 (stages U2 numbers, U14 helper, U24 inject form).
  A-C2 step order: A.U2.12's part lands in U3, not U2 (it follows A.U2.12's own change, which lands in U3).
- **Depends**: M.SRC_SENS.075, .077, .079, .080; TEST_HELP `tests/_ticks30.py`.
- **Blast carried by**: four tiers of the CONFIG2-3 burst: L1 → M.TEST_UNIT in `test_bus_hazard_multi_device.py`
  (A.U15.32, run unchanged), L2 → A.U15.32 (TWIN: `test_digital_twin_bus_hazard_concurrency.py` unchanged, red-dominant
  scene), L3/L4 → A.U15.32 (HW_DEV, HW_BENCH unchanged); L2 INT-muted re-arm → A.U15.R05 (TWIN); catalog W32 → A.U2.01
  (GEN).
- **Kind**: test

### M.TEST_UNIT.066 Brownout: every event warns into one slot; re-apply failures log CHIP_SET
- **From**: A.U3.14 (`:1566-1577` keep one slot, add `ErrCount == 5`; `:1580-1595` one slot, OR35.b), A.U3.01 (the
  newest-entry rule), A.U2.12 (w10 → 30, e33 → 13), A.U15.R04 (brownout through the shared re-apply body),
  A.U24.78 (`:1621`), M.SRC_SENS.075 (the brownout return carries the cycle's `TS`).
- **Site**: `tests/test_asy_isl29125_driver.py:1549-1626`.
- **Change**: `test_brownout_reapplies_the_whole_configuration_and_discards_one_cycle`: `assert results[:5] == (None,)
  * 5` (the trailing element is the cycle's `utc_now()`), writes as HEAD. `test_repeated_brownout_warns_once_per_event_not_once_per_cycle`
  → `test_repeated_brownouts_each_warn_into_one_slot`: the log holds one entry, `code("W", "ISL_BROWNOUT")`, with
  `ErrCount == 5`. `test_a_recovered_brownout_warns_again_on_the_next_real_event` → one slot, `ErrCount == 2`.
  `test_a_brownout_recovery_write_failure_logs_errno_33` → `…_logs_chip_set`: `inject_fault("writeto_mem", OSError,
  errno_mod.EIO, "no ACK", times=5)`; the log holds `code("W", "ISL_BROWNOUT")` then `code("E", "CHIP_SET")`.
- **Resolved**: A.U3.14 retires the per-episode latch (`_brownout_seen` goes, M.SRC_SENS.073): "once per event" is now
  one warning per detected brownout, folded into one slot by the newest-entry rule (OR35.b); the HEAD claim "not once
  per cycle" is retired by that owner rule, guarded by the `ErrCount` assertions.
- **Unit**: U3 (stages U2 numbers, U15 shared body).
  A-C2 step order: A.U2.12's part lands in U3, not U2 (it follows A.U2.12's own change, which lands in U3).
- **Depends**: M.SRC_SENS.076; M.SRC_CORE (newest-entry rule, A.U3.01).
- **Blast carried by**: SPEC `:6675-6678` → A.U3.14/A.U3.10 (SPEC).
- **Kind**: test

### M.TEST_UNIT.067 Config read-back and divergence: catalog numbers, keys, the two-argument snapshot
- **From**: A.U2.12 (`:1657` `_snapshot_field(0, 29, …)`; `:1671` w1; `:1700` 28; `:1719-1720, 1737` w11/w10), A.U10.40
  (`IrCompOffset`/`IrCompAdjust` → `IRCompOffset`/`IRCompAdjust`, `SampleInterv` → `SampleInterval`, `ISLCalibrate` →
  `Calibrate`), A.U10.35 (`reader.isl`).
- **Site**: `tests/test_asy_isl29125_driver.py:1629-1750`.
- **Change**: the `_read_sensor_dict()` key sets → `{"Resolution", "Range", "IRCompOffset", "IRCompAdjust"}`;
  `run(reader._snapshot_field(0, "resolution"))`; `:1661` comment → "wrnno CALLBACK_KEYS" and `:1671` →
  `code("W", "CALLBACK_KEYS") not in warnings(counters)`; `:1700` → `code("E", "CHIP_GET") in errors(counters)`;
  `:1717-1720` → comment "# ISL_DIVERGED, not ISL_BROWNOUT: a chip that disagrees with the shadow for any other reason
  is a different event." and `warnings(counters).count(code("W", "ISL_DIVERGED")) == 1`, `code("W", "ISL_BROWNOUT") not
  in …`; `:1737` → `ISL_DIVERGED` not in. `test_get_dict_cfg_excludes_the_command_only_field`: `"Calibrate" not in`,
  `"SampleInterval" in`, the key set with `SampleInterval`, `IRCompOffset`, `IRCompAdjust`.
  `reader.isl.decode_config = …` → `reader._isl.decode_config` (inline ignore kept).
- **Resolved**: —
- **Unit**: U2 (numbers, `_snapshot_field` signature), stage U10 keys.
  A-C2 step order: A.U2.12's part lands in U3, not U2 (it follows A.U2.12's own change, which lands in U3).
- **Depends**: M.SRC_SENS.082, .084.
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.068 Schema coverage and the pushes; threshold inputs reach the chip
- **From**: A.U24.61 (`:1760`, `:2680-2682`), A.U10.40 (keys `:1770`, `:1779-1782`, `:1801-1802`, `:2067`), A.U10.43
  (`trigger_secs` → `trigger_s`, `_MIN_TRIGGER_S`), A.U10.35 (`trigger_period`), A.U24.62 (`:1775-1776`), A.U15.33
  (`:2047-2057` gains the burst; new L1), A.U2.12 + A.U3.01 (`:2642`, `:2664`).
- **Site**: `tests/test_asy_isl29125_driver.py:1753-1845`, `:2047-2072`, `:2621-2687`.
- **Change**:
  - `names = [field[0] for field in reader.get_cfg_schema()]`; getter keys `["IRCompAdjust", "IRCompOffset", "Range",
    "Resolution"]`; the wrong-type dict and the pushes use `SampleInterval`, `IRCompOffset`, `IRCompAdjust`,
    `Calibrate`; `:1775-1776` → "# type(value) is not int, deliberately: on MicroPython bool is not an int subclass
    (py/objbool.c), while CPython's is - `type(x) is int` states the rule the same way on both."
  - `:1826-1828` loop variable `trigger_s`, `persist_for_interval(trigger_s)`; `:1838` comment names `_MIN_TRIGGER_S`;
    `:2068` reads `reader._trigger_period`.
  - `test_pushing_the_software_knobs_changes_only_driver_state` → `…_write_only_the_thresholds_they_derive`: after the
    three pushes `_ar_thresh == 90.0`, `_ar_dwell_s == 30.0`, `_filt_coeff == 0.25`, and `mem_writes(i2c) ==
    [(_REG_THRESHOLDS, struct.pack("<HH", ISL29125_I2C.fraction_to_counts(90.0 / _AR_DOWN_DIVISOR), 65535))]` (the
    high range's down crossing, the up crossing parked); comment → "# AutoRangeThresh moves the chip's down crossing at
    once; AutoRangeDwell and FiltCoeff are driver state only."
  - New (A.U15.33): `test_set_autorange_thresh_on_the_low_range_writes_the_up_crossing` (`(0,
    fraction_to_counts(90.0))` to 0x04-0x07); `test_a_failed_threshold_write_leaves_the_cached_threshold` (bus faulted:
    `False`, `_ar_thresh` unchanged, one `code("E", "CHIP_SET")`); `test_set_resolution_rescales_the_thresholds_with_auto_range_off`
    (`RangeAuto` off, `set_resolution(12)`: one threshold burst at the 12-bit scale, `>> 4`).
  - `test_pinning_a_range_while_autorange_is_off…`: `ErrCount == 2`, newest `code("E", "CHIP_SET")`.
    `test_the_two_remaining_auto_range_knobs_reject…_with_errno_27` → `…_with_bad_arg`: `ErrCount == 5`, newest
    `code("E", "BAD_ARG")`; value assertions hold. `test_an_out_of_band_knob_is_rejected_by_the_schema_rung…` passes
    `reader.get_cfg_schema()`.
- **Resolved**: —
- **Unit**: U15 (stages U2/U3 numbers, U10 names, U24 accessor and comment).
  A-C2 step order: A.U2.12's part lands in U3, not U2 (it follows A.U2.12's own change, which lands in U3).
- **Depends**: M.SRC_SENS.072, .080, .084, .086.
- **Blast carried by**: four tiers of the threshold write (one 4-byte write per setter call): L1 → M.TEST_UNIT in
  `test_bus_hazard_multi_device.py` (A.U15.33, unchanged), L2/L3/L4 → A.U15.33 (TWIN, HW_DEV, HW_BENCH, unchanged).
- **Kind**: test

### M.TEST_UNIT.069 Failed writes and reconciliation: the wrapping sequence, a silent re-read
- **From**: A.U15.31 (`:1920-1957` hold; new wrap L1), A.U15.29 (new reconciliation L1), A.U2.12 (`:1893` w12,
  `:1935`, `:1985` w11, `:2016` 24), A.U24.78 (`:1902, 1926, 1996, 2012`), A.U10.35 (`reader.isl`).
- **Site**: `tests/test_asy_isl29125_driver.py:1875-2044`.
- **Change**: `:1893` → `assert reader._last_overrange is False, "no saturation happened"` (the retired W12 had moved
  to the `Overrange` field; a number assertion on it proved nothing). `:1935`, `:1985` → `code("W", "ISL_DIVERGED")`.
  `test_re_deriving_the_transient_rejection_logs_errno_24…` → `…logs_chip_set…`: `code("E", "CHIP_SET") in
  errors(…)`; its `:2005-2007` comment → "# CONFIG3 is a real chip write and fails like any other; the console line
  names the derived window, so a reader does not look for a bad SampleInterval or Resolution." The reconciliation
  tests hold on `reader._isl`. `test_a_reconciling_re_read_that_itself_fails…` adds: the failed re-read leaves
  `ErrCount` unchanged and prints one line through `reader.pr.err` (spy, inline ignore) (A.U15.29). New
  `test_the_write_failure_sequence_wraps_and_still_reconciles` (A.U15.31): `reader._isl._write_failures =
  reader._reconciled_write_failures = COUNTER_CAP` (imported from `asy_base_classes`), one injected failed configure
  write → `write_failures() == 0`; the next `_read_isl()` reads the snapshot once (`mem_reads` holds one
  `(_REG_CONFIG1, 3)`) and leaves the two counts equal.
- **Resolved**: A.U15.31's "`_SEQ_MASK`" is M.SRC_SENS.085's `COUNTER_CAP` wrap (AC_NOTES 17).
- **Unit**: U15 (stages U2 numbers, U24 inject form).
  A-C2 step order: A.U2.12's part lands in U3, not U2 (it follows A.U2.12's own change, which lands in U3).
- **Depends**: M.SRC_SENS.077, .082, .085.
- **Blast carried by**: U35's L0 counter check lists the site as a sequence → A.U15.31 (TSC).
- **Kind**: test

### M.TEST_UNIT.070 Reader setters and getters: catalog classes, one slot per kind, the removed arm
- **From**: A.U2.12 (`:2128` 38, `:2162` 18, `:2180` 25, `:2186-2188` 16/20/22, `:2206` 15/17/19/21, `:2532` 26,
  `:2790-2792`, `:2808` 18, `:2827-2828` 25/27), A.U3.01 (`:2180`, `:2532` one slot, `ErrCount` by k), A.U10.43
  (`set_trigger_secs` → `set_trigger_s`), A.U10.10 (`:2174` `pr.setup()`), A.U10.40 (`ISLCalibrate`), A.U24.61
  (`:2246, 2269, 2284, 2285`), A.U24.62 (`:2834-2835`), A.U24.73 (`dict[str, Any]`, `list[Any]`), A.U24.78 (`:2123,
  2139`), A.U15.38 (`:2878-2890` goes), A.U4.02 + A.U19.16 (hold: the result words stay literals in tests).
- **Site**: `tests/test_asy_isl29125_driver.py:2074-2290`, `:2517-2532`, `:2778-2890`.
- **Change**:
  - `test_turning_autorange_off_logs_errno_38…` → `…logs_chip_set…`; `:2162`, `:2808` → `code("E", "CHIP_SET")`.
  - `test_set_trigger_secs_logs_errno_25…` → `test_set_trigger_s_refuses_bad_values_with_bad_arg_and_never_raises`:
    `set_trigger_s(...)` throughout, `:2174` goes, `ErrCount == 4` with the newest entry `code("E", "BAD_ARG")`
    (comment "# One event per rejected value, one slot: a non-number, +inf, and both out-of-range ends."),
    `reader._trigger_period` reads 30.
  - `test_every_hardware_setter_logs_its_own_errno…` → `…logs_chip_set_on_a_bus_fault`: the table loses its numbers;
    each newest entry `code("E", "CHIP_SET")`. `test_every_getter_logs_its_own_errno…` → `…logs_chip_get…`, each
    newest `code("E", "CHIP_GET")`. Comments name the class ("numbers name the failure class; the console line names
    the field").
  - The recovery-chain and calibration tests pass `reader.get_cfg_schema()`, the key `Calibrate`, `dict[str, object]`/
    `list[object]` annotations; `"Failed"`/`"Valid"`/`"Invalid"` stay literal (the wire contract).
  - `test_the_filter_coefficient_rejects…_errno_26` → `…_with_bad_arg`: `ErrCount == 4`, newest `code("E",
    "BAD_ARG")`, comment "one event per rejected value; the two boundaries add none". 
  - `test_every_hardware_backed_setter_reports_a_rejected_field_without_writing`: `ErrCount == 3`, newest
    `code("E", "CHIP_SET")`, `mem_writes(i2c) == []` (the per-setter numbers are retired by the class catalog; the
    claim "each setter surfaces the refusal" holds through the three `False` returns).
  - `test_a_fractional_setting_is_rejected…`: `set_trigger_s(12.5)` / `(30.0)`; `ErrCount == 1` with newest `code("E",
    "BAD_ARG")` replaces the 25/27 pair (the accepted values prove which one was refused); `_trigger_period` 30.
  - `test_a_bool_is_never_accepted…`: `set_trigger_s(True)`; `:2835-2836` → "# A True reaching a numeric field must be
    refused on both interpreters; inside these fields' bounds it would otherwise store 1."
  - `test_a_malformed_schema_record_is_refused_rather_than_returned_as_a_setting` is removed with the unreachable
    arm (M.SRC_SENS.082; G5/R54); its guard is the schema self-check every reader's schema passes at `setup()` and
    `tests_scripts/test_config_schemas.py`.
- **Resolved**: A.U2.12 gives the getters one CHIP_GET and the setters one CHIP_SET; tests that told setters apart by
  number keep their per-setter `False` assertions instead (OR111.a (2): the distinct-number pin is retired by the
  catalog rows A.U2.01).
- **Unit**: U2 (numbers), stages U3 slot rule, U10 names, U15 removal, U24 accessor/typing.
  A-C2 step order: A.U2.12's part lands in U3, not U2 (it follows A.U2.12's own change, which lands in U3).
- **Depends**: M.SRC_SENS.080, .082, .084; A.U2.03 (`code()`).
- **Blast carried by**: SPEC E.5.1 rows → A.U35.41 (SPEC).
- **Kind**: test

### M.TEST_UNIT.071 Calibration: the candidate's hold across the tick horizon, catalog numbers
- **From**: A.U15.35 (`:3022, 3041, 3057` hold; `:3083` holds; new crossing case (b)), A.U2.12 (`:3137-3138` 35/11,
  `:3163` 29), A.U24.78 (`:3161`), A.U24.76 (`queue_legs`, `calibrating_reader`), A.U10.35, A.U0.07 (`:3014, 3030,
  3049, 3064, 3076` local imports).
- **Site**: `tests/test_asy_isl29125_driver.py:2291-2306`, `:2920-3167`.
- **Change**: `_queue_legs()` patches `reader._isl.read_counts` (inline ignore); `_calibrating_reader()`; the local
  `import time as _time` lines go (module `time`). `test_a_failed_partner_read_logs_errno_35…` →
  `…logs_a_read_error_and_puts_the_range_back`: the newest entry is `code("E", "READ")`, `ErrCount >= 1`, the range is
  back on `_RANGE_HIGH_LUX`; the `:3122-3123` comment and the "11 not in" assertion go. `:3163` → `code("E",
  "CHIP_SET")`. New `test_a_published_candidate_expires_and_stays_expired_across_a_week` (A.U15.35 (b)): `Ticks30Time`
  installed, a candidate published (`_publish_candidate(25.9)`), then `advance(3_600_000)` for 7 days with
  `_measured_ratio()` read each step: `None` from the first step past the 10-minute hold onwards, and `_cal_meas is
  None` once it expired.
- **Resolved**: the distinct-number claim (35 vs the periodic 11) is retired by the catalog's class numbering (A.U2.01:
  both are READ); the console line "Paired gain-ratio reading failed" tells the two apart (OR111.a (2)).
- **Unit**: U15 (stages U2 numbers, U14 helper, U24 names/inject).
  A-C2 step order: A.U2.12's part lands in U3, not U2 (it follows A.U2.12's own change, which lands in U3).
- **Depends**: M.SRC_SENS.081; TEST_HELP `tests/_ticks30.py`.
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.072 Trigger divider, timer arm, starters and the empty sample
- **From**: A.U15.40 + A.U10.44 (`:2314-2330`, `:2353-2371` → the shared `_trigger_loop()`), A.U10.43 (`set_trigger_s`),
  A.U10.35 (`base_trigger_event`, `read_event`, `trigger_timer`), A.U10.12 (`:2412`), A.U15.41 (`:2396` holds; new arm
  L1), A.U24.49 (`_RaiseOnArm`), A.U24.08 + A.SDEP.16 + A.U14.28 (`_cancel_and_join` `:2333-2341`, `_drain_flag`
  `:2344-2350`), A.U15.36 (`:2419` gains a field), A.U24.07.
- **Site**: `tests/test_asy_isl29125_driver.py:2309-2420`.
- **Change**: section comment → "# _trigger_loop() - the shared 1 Hz base tick divided down by the sample interval
  (SPECIFICATION.md C.9)". The two divider tests start `reader._trigger_loop()` (via `asyncio.create_task`), call
  `set_trigger_s()`, set `reader._base_trigger_event`, read `reader._read_event`, and end with `await cancel(task)`;
  assertions hold (3 events in 9 ticks; `[1, 2, 3]`). `_cancel_and_join()` goes (its use is `_async_harness.cancel`,
  whose own header carries the reason); `_drain_flag()` stays with a two-line comment: "# Reads ThreadSafeFlag's own
  state and clears it: a wait_for_ms() probe registers a poll object per call (SPECIFICATION.md F.7 row 12)." — if the
  pin re-check (A.SDEP.16 W12) retires that row, the comment keeps only "Reads the flag's own state and clears it: the
  question is 'was it set'". Timer tests read `reader._trigger_timer`; `test_task_and_timer_starters_are_registered` →
  `test_task_and_trigger_starters_are_registered`: task starters `["start_asy_read", "start_asy_trigger"]`,
  `[fn.__name__ for fn in reader.get_trigger_starters()] == ["start_timer"]`, `reader.get_timer_starters() == []`.
  `test_start_timer_degrades…` uses `RaiseOnArm(exc)`, asserts the IRQ handler is wired and
  `reader._base_trigger_event` is set (the waiter woken). New `test_a_failed_trigger_arm_ends_the_trigger_task_with_one_timer_entry_and_a_restart_rearms`
  (`OSError(ENOMEM)` and `MemoryError`): `start_timer()` under the raise, `_trigger_loop()` as a task ends at once with
  exactly one `code("E", "TIMER")`; `start_timer()` again without it performs one `Timer.init`, and one tick on the
  fake timer sets `_read_event` at `SampleInterval` 1. `:2419` → `ISL29125(*(None,) * 13)` compared field-for-field.
- **Resolved**: A.U15.40 (`_divide_trigger()`) vs A.U10.44 (`_trigger_loop()`): M.SRC_SENS.045's GAP-8 settlement, the
  shared `SensorReader._trigger_loop()`. A.U14.28 (keep the comment, add the F.7 row) vs A.SDEP.16 (the reason changes
  once W12 is fixed): both, staged — the row pointer while the row stands, the reduced reason after the re-check.
- **Unit**: U15 (stages U10 names/split, U14 row pointer, U24 harness, U0 pin re-check).
- **Depends**: M.SRC_SENS.083, M.SRC_SENS.045, M.SRC_CORE.037 (`_timer_failed`).
- **Blast carried by**: shared divider L1 (n = 1, 3) → M.TEST_UNIT in `test_base_classes.py` (A.U15.40).
- **Kind**: test

### M.TEST_UNIT.073 Divergence re-arm and the status-read failure
- **From**: A.U2.12 (`:2467` 34, `:2512` 31), M.SRC_SENS.075 (the failure return carries `TS`), A.U10.35.
- **Site**: `tests/test_asy_isl29125_driver.py:2422-2514`.
- **Change**: `test_a_failed_re_apply_after_divergence_logs_errno_34…` → `…logs_chip_set…`: `code("E", "CHIP_SET") in
  errors(counters)`; the threshold assertion holds. `test_a_failed_status_read_drops_the_whole_sample…`: `assert
  results[:5] == (None,) * 5`, `code("E", "ISL_STATUS_READ") in errors(counters)`. `reader.isl` → `reader._isl`.
- **Resolved**: —
- **Unit**: U2.
  A-C2 step order: A.U2.12's part lands in U3, not U2 (it follows A.U2.12's own change, which lands in U3).
- **Depends**: M.SRC_SENS.075, .082.
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.074 Layer-one `None` answers: the bool and bytes contracts
- **From**: A.U13.10 (`:2599-2611`: `silent_none` patches `get_register_bytes`), A.U30.07 (also `get_register_into`,
  returning `False`), A.U10.35 (`i2c_isl29125`).
- **Site**: `tests/test_asy_isl29125_driver.py:2595-2618`.
- **Change**: per call, `device = isl._i2c_isl29125.i2c_device`; `device.get_register_bytes` → an async stub returning
  `None` and `device.get_register_into` → one returning `False` (both with the inline `method-assign` ignore); every one
  of `get_device_id`, `read_status`, `get_config_snapshot`, `read_counts`, `reset` raises `OSError`. Comment `:2596-2598`
  → "# Layer 1 answers None (bytes) or False (into a buffer) for a bus it cannot use; each protocol read raises instead,
  so a caller's error path sees one shape. reset() is listed because its verify read IS the settle."
- **Resolved**: —
- **Unit**: U30 (stage U13).
- **Depends**: M.SRC_SENS.086.
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.075 The hardware driver's field guard: datasheet bytes, the removed fallback
- **From**: A.U24.38 (`:2727` asserts the encoding), A.U15.38 (2) (`:2896-2906` goes).
- **Site**: `tests/test_asy_isl29125_driver.py:2689-2906`.
- **Change**: `test_configure_accepts_every_value_the_datasheet_does_allow`: after each call the fake's CONFIG1-3
  bytes equal the FN8424 encoding of that value (a table in the test, citing p10-p11: resolution 12 → BITS `0x10`, 16 →
  0; range 375 → RNG 0, 10000 → `0x08`; IR offset 1 → CONFIG2 bit 7; IR adjust 63 → CONFIG2 `0x3F`; persist 1/2/4/8 →
  PRST 00/01/10/11 in CONFIG3 bits 3:2). `test_encode_shadow_falls_back_to_the_shortest_persistence_for_an_impossible_shadow`
  is removed with the fallback (M.SRC_SENS.086: `encode_shadow()` without the `try`); its guard is `configure()`'s
  refusal of `persist=3` and `persist=2.0` in `test_configure_rejects_a_field_the_chip_cannot_take…`, which holds.
- **Resolved**: —
- **Unit**: U24 (assertion strength), U15 (removal).
- **Depends**: M.SRC_SENS.086.
- **Blast carried by**: SPEC E.5.1 rows → A.U35.41 (SPEC).
- **Kind**: test

### M.TEST_UNIT.076 Same-device hazards: a gated interleaving, the scaled threshold write
- **From**: A.U35.12 (`:3199` gate, `:3236` stated limit), A.U10.18 + A.U10.35 (`isl.i2c_isl29125.asy_lock` →
  `isl._i2c_isl29125.session_lock`), A.U15.S01 (new L1 modelled on `:3213-3246`), A.U15.33 (new race L1), A.U24.73
  (`_gather` typing), A.U15.S01 (`:3263` sweep holds).
- **Site**: `tests/test_asy_isl29125_driver.py:3170-3275`; new tests after `:3246`.
- **Change**: `test_concurrent_read_and_write_never_interleave_on_the_wire`: the reader sets an `asyncio.Event` after its
  first `read_status()`; the writer awaits it in place of the `:3199` yield (the "partway" claim becomes a gate);
  assertions hold. `test_configure_never_exposes_the_shadow…`: `lock = isl._i2c_isl29125.session_lock`; the `:3236`
  comment → "# one yield lets configure() park on the held lock (a limit, not an interleaving claim)"; the `:3215-3224`
  comment block is cut to three lines ("# configure() mutates the shadow only under the device-session lock (C.8):
  holding that lock stands in for an operation in flight, and the shadow must not move meanwhile."). `_gather(a, b)`
  typed `Coroutine[object, object, object]`. New `test_set_thresholds_scales_to_the_resolution_live_when_it_gets_the_session`
  (A.U15.S01): `_make_protocol()`, the test acquires `session_lock`, creates `isl.set_thresholds(0, 32768)` as a task,
  yields once, sets `isl._resolution = 12` (standing in for a `configure()` holding the session), releases in
  `finally`, awaits the task: `mem_writes(i2c) == [(_REG_THRESHOLDS, struct.pack("<HH", 0, 32768 >> 4))]`. New
  (A.U15.33) `test_a_threshold_push_racing_a_range_switch_leaves_chip_and_cache_agreeing` (`set_autorange_thresh(90)`
  against `_switch_range()` with `_isl.set_thresholds` patched to yield once: afterwards the 0x04-0x07 bytes equal the
  counts derived from `_ar_thresh` and `_active_range`) and `test_two_concurrent_threshold_pushes_end_on_the_later_one`.
- **Resolved**: —
- **Unit**: U15 (stages U10 names, U24 typing, U35 gate).
- **Depends**: M.SRC_SENS.080, .086.
- **Blast carried by**: four tiers of the threshold write → A.U15.S01/A.U15.33 blasts (L1 hazard file M.TEST_UNIT,
  TWIN, HW_DEV, HW_BENCH, unchanged); C.8 table `_threshold_lock` → GAP-13 (SPEC, TSC).
- **Kind**: test

### M.TEST_UNIT.077 The unwritable config file
- **From**: A.U10.10 (`:3284`), A.U2.07 (`:3293` 4 → CFG_FILE_WRITE), A.U2.12 (`:3292` "12 not in"), A.U3.05 dropped
  (OR140.a (7); nothing here depended on it), OR136.a (1) (the setup write of the absent file is the CFG_FILE_WRITE
  entry) — A-C review fold, A.U24.07 (`:3280`).
- **Site**: `tests/test_asy_isl29125_driver.py:3278-3293`.
- **Change**: built through `_make_i2c()`, `run(reader.setup())` (no `all_timers.clear()`); `:3292` → the ISL29125 log
  has `ErrCount == 0`; `:3293` → `CFGMGR_ISL29125`'s newest entry is `code("E", "CFG_FILE_WRITE")`. Comment `:3279` →
  "# A failed config write does not end the read task: the reader runs on the defaults (SPECIFICATION.md C.7.3)."
- **Resolved**: —
- **Unit**: U2 (stage U10 setup).
- **Depends**: M.SRC_SENS.074, M.SRC_CORE.044.
- **Blast carried by**: —
- **Kind**: test

## tests/test_asy_neopixel_driver.py

### M.TEST_UNIT.078 Builders under driven time: fixed product values set from outside, the boot `setup()`
- **From**: A.U17.27 (`:31-35` `make_driver()` sets the values after construction), A.U31.13 (`neopixel_dt` →
  `_frame_ms`), GAP-5 (M_SRC_SENS: the `_overlay_*` stem), A.U10.35 (`driver.pixel` ×35 via `_pixel()`), A.U35.13
  (`DrivenTime` replaces the 36 real sleeps), A.U8C.11 (tags on those sleeps), A.U35.12 (`:41`), A.U24.08 (`run`,
  `_cancel_all` `:45-51`), A.U22.04 (`:12`, `:21` typing), A.U10.37/A.U10.38 (`crc_checks.CRC_Base`), A.U10.10,
  GAP-17 lead ruling (AC_NOTES 38: an `initialized` gate on `NeopixelDriver`) dropped (routine settlement
  `initialized-flags`, AC_NOTES 52; A-C review fold), A.U5.02.
- **Site**: `tests/test_asy_neopixel_driver.py:1-52`.
- **Change**: imports `from _async_harness import run, cancel`, `from _driven_time
  import DrivenTime`, `from _error_codes import code`, `from asy_print_log import LogConfig`; TYPE_CHECKING drops
  `Coroutine`/`Any`/`TypeVar`/`T` and imports `asy_crc_checks.CRCBase`. `_pixel()` returns `driver._pixel`.
  `make_driver(neopixel_freq=100, led_overl_bri=50, debug=None)` → `_make_driver(freq: int = 100, overlay_bri: int =
  50)`: `driver = NeopixelDriver(0)`, then `driver._neopixel_freq = freq`, `driver._frame_ms = 1000 // freq`,
  `driver._overlay_bri = overlay_bri` (the inline attribute writes are the product's own state, A.U17.27), then
  `run(driver.setup())`; the `debug` parameter goes (no caller passes it); comment → "# 100 Hz keeps five frames per
  ramp direction at the 0.1 s floor, so mid-ramp state is observable; time is driven, not waited." Every scenario runs
  inside `with DrivenTime() as clock: clock.install(asy_neopixel_driver)`, and each real `asyncio.sleep(x)` becomes
  `await clock.advance(<ms>)` (a ramp: `2 * max(int(t * 0.5 * freq), 1) * _frame_ms` plus one frame) or `await
  clock.run_until(<the expected frame recorded>, <that bound>)` (an overlay write), with no margin. `_start_all_tasks()`
  keeps its one `sleep(0)` with the comment "# one yield lets each task park on its first wait (a limit, not an
  interleaving claim)"; `_cancel_all()` becomes `cancel(*tasks)` from the harness.
- **Resolved**: A.U8C.11's `l1.asy_neopixel_driver_*` tags vs A.U35.13: the literals they tag are deleted by driven
  time, so the tags are not written and their rows are withdrawn (A.U35.13's Blast says so; Conventions "`@tunable`
  tags"). A.U10.35's mechanical `led_overl_*` names vs M.SRC_SENS.023's `_overlay_*`: the product's (GAP-5).
- **Unit**: U35 (driven time; stages U9 arbitration, U10 names/`setup()`, U17 fixed values, U22 typing, U24 harness,
  U31 `_frame_ms`).
- **Depends**: M.SRC_SENS.021, .023, .024; TEST_HELP `tests/_driven_time.py` (A.U35.10), `tests/neopixel.py` (A.U24.25).
- **Blast carried by**: Part N `l1.asy_neopixel_driver_*` rows withdrawn → A.U35.13 (SPEC); the same IDs' other site
  `tests/test_neopixel_wifi_integration.py` → M.TEST_UNIT in that file (A.U8C.35 vs A.U35.13).
- **Kind**: test

### M.TEST_UNIT.079 Overlay and logger tests: private state, the gate, the FRAM-backed reboot
- **From**: A.U10.18 (`led_overl_lock` → `_overlay_lock`), A.U10.35/GAP-5 (`led_overl_on` → `_overlay_on`), A.U22.01
  (existing counts hold: one more frame per task start), A.U10.10 (`:453-464`), GAP-17 lead ruling dropped (routine
  settlement `initialized-flags`, AC_NOTES 52: no `initialized` on `NeopixelDriver`; A-C review fold), A.U5.02 (`:495`,
  `:504` `fram=` → `log=`), A.U16.19 (`:475`, `:479` `override_pause` goes), A.U11.S03 (hold: the `arg-type` ignore),
  A.U24.39 (`:667`), A.U35.13.
- **Site**: `tests/test_asy_neopixel_driver.py:54-177`, `:448-524`, `:648-674`.
- **Change**:
  - Overlay tests read `driver._overlay_on`, `driver._overlay_lock.locked()`; `:163-165` comment → "# request_signal()
    returns once the request is queued, not when the ramp ends; the task keeps the scenario reading top to bottom."
    (it pointed at a module docstring this file does not have). `test_repeated_on_is_idempotent…` holds (its count is
    relative to a snapshot taken after the tasks started).
  - `test_pr_setup_runs_before_any_ramp_is_committed` → `test_setup_initialises_the_logger_and_the_driver_before_any_task`:
    a driver built with `NeopixelDriver(0)` (no builder) has `pr.initialized is False` (the logger's own flag);
    `run(driver.setup()) is True`; `pr.initialized` is `True` before any task starts (no task calls `pr.setup()` any
    more). The driver itself carries no `initialized` flag (nothing in the product reads one).
  - `_FakeFramChunk.write_into(buf)`/`read_into(buf)` lose `override_pause`; the reboot test builds
    `NeopixelDriver(0, log=LogConfig(fram, 10, None))` (the `arg-type` ignore and its reason stay) and calls
    `await driverN.setup()` in place of `pr.setup()` (the `:498-499` comment goes).
  - `test_get_task_starters_returns_three_callables` → `…returns_the_overlay_and_signal_starters`:
    `[s.__name__ for s in starters] == ["start_asy_overlay", "start_asy_signal"]`. `test_get_timer_starters…`'s
    vacuous `get_task_starters is not None` line goes.
  - `test_on_off_toggle_satisfy_led_control_protocol_signatures` → `test_on_off_toggle_drive_the_pixel_through_the_overlay_task`
    (A.U24.39): with the tasks started under driven time, `on()` records the overlay colour, `off()` `(0, 0, 0)`,
    `toggle()` the overlay colour again.
- **Resolved**: A.U10.10's "`pr.initialized` after task start → after `setup()`" lands in this test; the GAP-17 gate is
  not added (routine settlement `initialized-flags`).
- **Unit**: U10 (stages U5 `log=`, U16 fake keyword, U24 assertion).
- **Depends**: M.SRC_SENS.023, .024, .025; M.SRC_CORE.090 (`get_chunk()`'s parameters, which the fake manager mirrors).
- **Blast carried by**: per-class readiness L1 → M.TEST_UNIT in `tests/test_readiness_gates.py` (A.U10.22).
- **Kind**: test

### M.TEST_UNIT.080 Signal arbitration: refused at once while busy, a bounded internal wait
- **From**: A.U9.02 (`:333-346` holds, comment; `:348-372` flips; `:319-331`, `:374-402`, `:409-423` hold; new L1), A.U9.04
  (`:229-264` hold; new deadline L1), A.U9.05 (`:185-312`, `:425-446` hold; new cancel L1), A.U22.01 (new restart L1
  (1)-(3)), A.U35.13 (`:290` "needs real time", `:305`, `:395`); OR140.a (5) (internal requests wait then queue,
  external ones are refused with a retry-later message; A-C review fold).
- **Site**: `tests/test_asy_neopixel_driver.py:180-446`; new tests after `:446`.
- **Change**:
  - `:337-338` comment → "# No task started: led_signal() decides on _start_signal_event alone, with no await."
  - `test_led_signal_returns_true_while_a_previous_request_is_already_animating` →
    `test_led_signal_is_refused_at_once_while_a_ramp_runs_and_nothing_is_queued`: mid-ramp
    `driver._start_signal_event.is_set()`, `led_signal(0, 10, 0, 0.1) is False`, and after the ramp no frame with a
    green component exists; the refusal's console line (captured with `record_prints()`) is M.SRC_SENS.026's refusal
    text, which tells the caller to retry later (OR140.a (5)); its `:349-355` comment block → "# The busy signal is
    _start_signal_event, set for the whole ramp; an external request while it is set is refused, never queued (owner,
    2026-10-02)." The
    `start_signal_lock`/`ext_start_signal` asserts go.
  - `test_request_signal_low_freq_boundary_never_divides_by_zero` (`freq=1`, `_frame_ms` 1000) and the fractional-`t`
    and large-`t` tests advance the virtual clock by the ramp's own length; their "needs real time" comments go; the
    `>= 30` count becomes `== 31` (15 frames per direction at 20 Hz plus the final black, hand-computed from
    `int(1.5 * 0.5 * 20)`).
  - New (A.U9.02): `test_led_signal_is_refused_while_an_internal_request_is_queued_and_no_task_runs`; after the queued
    ramp ends (tasks started, clock advanced), `led_signal()` is `True` again.
  - New (A.U9.04): `test_request_signal_gives_up_at_its_deadline_when_the_signal_task_never_runs` (event set, no
    task: `False` after `advance(src_const("src/asy_neopixel_driver.py", "_SIGNAL_WAIT_MS"))`, still pending one frame
    before); `test_request_signal_behind_a_running_ramp_returns_true_only_after_it_ends` (no frame of the second colour
    precedes the first ramp's final black).
  - New (A.U9.05): `test_cancelling_the_signal_task_mid_ramp_leaves_the_pixel_dark_and_the_slot_free` (cancel once a
    non-black frame is recorded: last frame black, `_start_signal_event` clear, a restarted task writes no frame of the
    cancelled colour).
  - New (A.U22.01): `test_a_restarted_overlay_task_reapplies_the_overlay` (overlay on, its task cancelled and a new one
    started: the overlay colour is written again with no `on()`); `test_a_signal_task_ended_mid_ramp_restarts_dark_and_restores_the_overlay`
    (`_pixel(driver).raise_on_write` set mid-ramp, cleared before the restart: black, then the overlay colour, no frame
    of the old ramp colour after the restart); `test_the_supervisor_restarts_a_failed_signal_task_with_one_system_entry`
    (the same failure under a real `SystemService` supervisor loop over the driver's starters, built as
    `tests/test_system_service.py`'s supervisor tests build it: one restart, SYSTEM's newest entry `code("E",
    "TASK_RAISED")` once).
- **Resolved**: —
- **Unit**: U9 (stages U22 restart cases, U24 `record_prints()` for the refusal line, U35 driven time).
- **Depends**: M.SRC_SENS.026 (its refusal text as the fold amends it), .027, .028, .025; M.SRC_CORE (supervisor
  task-ended code, A.U3.06); M.TEST_HELP.050 (`record_prints()`).
- **Blast carried by**: `tests/test_notification_neopixel_integration.py:133-154` flip → M.TEST_UNIT in that file
  (A.U9.02); L2 restart case → A.U22.01 (TWIN).
- **Kind**: test

### M.TEST_UNIT.081 The sanitiser: wrap-aware clamp tests, refused non-numbers, the duration bounds
- **From**: A.U9.06 (`:534-548` add two cases; `:550-646` hold; `:567-570` comment; new L1), A.U24.25 (`:527-531`, `:612`,
  `:644` comments; assert the wrap is absent), A.U24.62 (`:541`), A.U14.10 + A.SDEP.08 (`:542-544`).
- **Site**: `tests/test_asy_neopixel_driver.py:527-646`.
- **Change**: section comment `:528-530` → "# _clamp_byte(): a real NeoPixel stores into a bytearray, so an out-of-range
  int wraps silently (0x12C stores as 0x2C) and a float raises TypeError; every value is clamped where the request
  enters." `test_clamp_byte_direct` gains `_clamp_byte("12") == 0` and `_clamp_byte(None) == 0`; `:541` → "# a bool
  counts as 0/1 for a byte value (the clamp's own rule)"; `:542-544` → "# int(inf) raises OverflowError, int(nan)
  ValueError (Part F.1, v1.29.0). Regression test for the gap / # _clamp_byte()'s original except (TypeError,
  ValueError) clause missed entirely." (the version stamp re-checked at the refreshed pin, A.SDEP.08). The out-of-range
  tests keep their clamped assertions and add the wrapped values' absence: 300 → no 44, 999 → no 231, -5 → no 251
  (`:603-617`); -10 → no 246, 500 → no 244 (`:620-633`); brightness 999 → no `(231, 231, 231)` (`:635-645`); their
  "would raise ValueError" comments → "an unclamped value would wrap (or raise TypeError for a float)". `:567-570` →
  "# A non-finite t is mapped to the 0.1 s floor by _signal_values() before any ramp runs." New
  `test_a_non_numeric_signal_value_is_refused_without_a_frame` (`request_signal(None, 0, 0, 0.5)`, `("10", 0, 0, 0.5)`,
  `(10, 0, 0, "1")`, and `led_signal()` with the same: `False`, no frame, no exception);
  `test_a_long_signal_is_capped_at_sixty_seconds` (`t = 600.0` at 20 Hz: `int(60 * 0.5 * 20) = 600` frames per direction
  recorded, then black); `test_a_negative_duration_takes_the_floor` (`t = -1.0`: one step each way at 20 Hz).
- **Resolved**: —
- **Unit**: U9 (stages U14 comment, U24 fake fidelity).
- **Depends**: M.SRC_SENS.022; M.TEST_HELP.006 (the GRB-bytearray fake: wrap and float `TypeError`, GAP-T6).
- **Blast carried by**: twin fake fidelity → A.U25.21 (TWIN).
- **Kind**: test

## tests/test_asy_notification_service.py

### M.TEST_UNIT.082 Doubles and builders: construction-time signals, value references, driven cycles
- **From**: A.U10.37/A.U10.38 (`NotificationCoordinator` → `NotificationService`), A.U5.06 (signals at construction),
  A.U5.11 (`make_signal()` with `ValueRef`), A.U5.02 (`debug=` → `log=`), A.U10.10 (the builder calls `setup()`),
  A.U24.76 (`FakeValue`/`FakeClock`/`FakeSignalCb` → `_Fake…`, `make_*` → `_make_*`), A.U9.08 (`FakeValue.value: object`),
  A.U24.08 (`run`), A.U24.49 + A.U31.14 (`_FastAsyncSleep` `:100-114` → the shared one, `sleep_ms` included), A.U35.13
  (`_one_cycle()` `:138-146` under `DrivenTime`), A.U8C.12 (`_CYCLE_WAIT_S` tag), A.U22.04 + A.U24.73 (`:15`, `:23`
  typing), A.U10.37 (`crc_checks`/`print_log` TYPE_CHECKING imports).
- **Site**: `tests/test_asy_notification_service.py:1-148`.
- **Change**: imports `from asy_notification_service import NotificationService, NotificationSignal`, `from
  asy_base_classes import ValueRef, set_utc_valid`, `from asy_print_log import LogConfig`, `from _async_harness import
  run, cancel`, `from _driven_time import DrivenTime`, `from _fast_sleep import FastAsyncSleep`, `from _error_codes import
  code`, `from _src_const import src_const`; TYPE_CHECKING imports `asy_crc_checks.CRCBase`, `asy_print_log.ErrorLog`,
  `asy_base_classes.JsonDict` and drops `Coroutine`/`Any`/`TypeVar`/`T`/`NoReturn`. `_FakeTime` → the shared `FakeTime` of `tests/_fake_time.py` (M.TEST_HELP.054, the five notification copies); `_FakeValue(value:
  object = None, field="Value")`; `_FakeClock`, `_FakeSignalCb` unchanged in behaviour. `make_coordinator(...)` →
  `_make_service(signals: tuple[NotificationSignal, ...] = (), cfg_path=None, local_time=None, signal_cb=None)`
  constructing `NotificationService(cb, clock.get, signals, cfg_path=path)` and `run(service.setup())`, returning
  `(service, clock, cb)`. `make_signal()` → `_make_signal()` building `NotificationSignal(name, ValueRef(fv, name),
  field_schema, color, above=above)`. `_one_cycle(clock, task, wait_ms)` → `await clock.advance(wait_ms)` then `await
  cancel(task)`; its comment → "# One monitor cycle in virtual time: wait_ms covers every triggered flash's own 2 x
  FlashDur settle." Every scenario that starts a loop runs under `with DrivenTime() as clock:
  clock.install(asy_notification_service)`; the `_CYCLE_WAIT_S`-style constants are not written.
- **Resolved**: A.U8C.12's tags on the wait literals vs A.U35.13: the literals become the product's own durations under
  driven time, the tags are not written and their rows withdrawn (A.U35.13 Blast).
- **Unit**: U35 (stages U5 construction/`ValueRef`/`log`, U9 typing of `_FakeValue`, U10 names/`setup()`, U22/U24
  typing and names, U31 `sleep_ms`).
- **Depends**: M.SRC_SENS.030, .033; TEST_HELP `_driven_time.py`, `_fast_sleep.py`, `_async_harness.py`.
- **Blast carried by**: Part N `l1.asy_notification_service_*` wait rows withdrawn → A.U35.13 (SPEC).
- **Kind**: test

### M.TEST_UNIT.083 Signal refusal happens at construction and persists once at `setup()`
- **From**: A.U5.06 (`:150-231`, `:623-662`; new L1), A.U2.17 (w1/w2 → W44/W45; w3/w4 retired), A.U10.40 (`Interv` →
  `FlashInterval` in `:217`).
- **Site**: `tests/test_asy_notification_service.py:150-231`, `:623-662`.
- **Change**: the section → "# Signals at construction: validated in order, a refusal printed at once and persisted
  by setup()". `test_register_before_finalize_is_accepted_in_call_order` → `test_signals_are_accepted_in_tuple_order`
  (`_make_service((a, b))`: `service._registered == (a, b)`). The two collision tests and the zero-/two-field tests
  pass the signals to the constructor and assert the accepted tuple; each also asserts, after `setup()`, the newest
  entry `code("W", "NOTIFY_NAME_COLLISION")` (collisions) or `code("W", "NOTIFY_SCHEMA_SHAPE")` (schema shape).
  `test_finalize_builds_the_exact_combined_schema` → `test_construction_builds_the_exact_combined_schema` with
  `FlashInterval` in the expected list. `test_register_after_finalize_is_rejected` and
  `test_finalize_called_twice_is_a_no_op_second_time` are removed with the two methods (no call order exists to get
  wrong). `test_a_rejected_registration_surfaces_as_a_warning_with_its_own_wrnno` →
  `test_a_refused_signal_is_printed_at_once_and_persisted_once_by_setup`: before `setup()` the pending buffer holds one
  entry and the log is empty; after `setup()` the buffer is empty and the log holds exactly one `code("W",
  "NOTIFY_NAME_COLLISION")`; a second `setup()` adds none; and the service answers `get_dict_cfg()` immediately.
  `test_every_rejection_reason_keeps_its_own_distinct_wrnno` → `…the_two_refusal_reasons_keep_distinct_codes`: a
  collision and a zero-field schema give the two distinct codes.
- **Resolved**: A.U2.17 retires the after-finalize and finalize-again codes (46/47) with the methods; the HEAD claim
  "four reasons, four numbers" is retired by A.U5.06 (two reasons remain) — guard: the two distinct codes above.
- **Unit**: U5 (stages U2 codes, U10 key).
  A-C2 step order: A.U2.17's part lands in U3, not U2 (it follows A.U2.17's own change, which lands in U3).
- **Depends**: M.SRC_SENS.031, .033.
- **Blast carried by**: generated `signals=` argument → A.U5.06 (GEN); SPEC C.4.3 → A.U5.06 (SPEC).
- **Kind**: test

### M.TEST_UNIT.084 Combined config: the renamed interval key, typed results
- **From**: A.U5.06 (every `register()`/`finalize()`/`cfgmgr.setup()` triple → the builder), A.U10.40 (`Interv` →
  `FlashInterval`), A.U22.04 (`:261`, `:309`, `:403`, `:481`, `:520` result and body types), A.U4.02 + A.U11.24 +
  A.U19.16 (hold: the write path's results unchanged, the result words stay literal, the `write_config()` comments
  `:274`, `:329` still name the method).
- **Site**: `tests/test_asy_notification_service.py:233-531`.
- **Change**: each test builds `_make_service((signal,))` (or `()`), dropping its `register`/`finalize`/`cfgmgr.setup()`
  lines; `_INT_FLOAT_FIELD_BOUNDS` and every body use `"FlashInterval"`; the scenario return types read `JsonDict`
  (bodies) and `WriteValidity` (per-field results) instead of `dict[str, Any]`; the `:410-413`, `:443-445` comments
  say "a signal's field" for "a registered NotificationSignal's field". Assertions hold.
- **Resolved**: A.U22.04 offers `JsonDict` "only once the unit that retypes those methods has landed" — M.SRC_SENS.033
  and M.SRC_CORE type `get_dict_cfg()` with `JsonDict`, so the end state uses it.
- **Unit**: U5 (stages U10 key, U22 typing).
- **Depends**: M.SRC_SENS.032, .033, M.SRC_CORE.044.
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.085 The FRAM-backed reboot: `log=` and the boot `setup()`
- **From**: A.U5.06, A.U5.02 (`:565`, `:579` `fram=` → `log=LogConfig(fram, 10, None)`), A.U16.19 (`:545`, `:549`
  `override_pause` goes), A.U11.S03 (hold: the `arg-type` ignores), A.U10.10 (`pr.setup()` → `setup()`), A.U10.37.
- **Site**: `tests/test_asy_notification_service.py:534-589`.
- **Change**: the fake chunk's `write_into(buf)`/`read_into(buf)` lose the keyword; `get_chunk(…, crc: "CRCBase | None"
  = None, …)`; both services are `NotificationService(cbN, clockN.get, (aN,), cfg_path=path, log=LogConfig(fram, 10,
  None))` with the `arg-type` ignore kept, and `run(serviceN.setup())` replaces the `cfgmgr.setup()` + `pr.setup()`
  pair; assertion holds.
- **Resolved**: —
- **Unit**: U5 (stages U10 setup, U16 fake keyword).
- **Depends**: M.SRC_SENS.033, M.SRC_CORE.090.
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.086 Shared history: catalog numbers, one slot per repeat, config reads fail in the store
- **From**: A.U2.17 (`:619`, `:686`, `:720`), A.U3.01 (`:696-720` `[10, 10]` → one slot, `ErrCount == 2`), A.U3.05
  (`:665-686` breaks the real config store; its print-only half dropped, OR140.a (7): NOTIFY keeps its own entry; A-C
  review fold), A.U22.02/A.U23.37 (`:682` goes), A.U9.10 (`:689-693` stays), A.U10.10.
- **Site**: `tests/test_asy_notification_service.py:592-720`.
- **Change**: the in-scenario `pr.setup()` lines go (the builder ran `setup()`).
  `test_signal_value_failure_and_own_time_callback_failure_share_one_history`: `ErrCount == 2`, the ring holds
  `code("E", "SOURCE")` then `code("E", "CALLBACK")`. `test_check_one_degrades_and_logs_when_the_threshold_config_cannot_be_read`
  → `…threshold_config_cannot_be_read_logs_in_both_layers`: the patched `get_float_values` goes; the test pops
  `"WarnCO2"` from `service.cfgmgr._cache` (a missing key in the real store); `_check_one()` is `False`; the NOTIFY log's
  newest entry is its own config-read code (HEAD's 11, by the catalog name the fold gives it back); `CFGMGR_NOTIFY` holds
  `code("E", "CONTRACT")`; `:682` goes. `test_two_signals_failures_share_one_errno…`
  → `…share_one_code_and_one_slot`: `ErrCount == 2`, the newest entry `code("E", "SOURCE")` and one slot for both
  (the names are in the console lines). `test_the_defaulted_signal_sink…` holds.
- **Resolved**: —
- **Unit**: U3 (stages U2 codes, U22 attribute removal).
- **Depends**: M.SRC_SENS.034, .035 (as the fold reverts A.U3.05); M.SRC_CORE (`_get_values()` → CONTRACT on a
  `KeyError`); [fold F11 M_GEN] (the restored NOTIFY code's name).
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.087 `_check_one()`: the return is the state, non-numeric values are refused
- **From**: A.U22.02 + A.U23.37 (`:815-816`, `:833-834` go; `:856-870` renamed), A.U3.12 (`:838-853`), A.U9.08
  (`:768-801` hold; `:873-893` gains rows; new SOURCE L1), A.U2.17.
- **Site**: `tests/test_asy_notification_service.py:723-888`.
- **Change**: each test passes its signals to `_make_service()`. The `last_value`/`triggered` asserts go (the
  `result is False` asserts stay). `test_check_one_get_value_raises…`: `pr.err_count == 1` and the newest entry
  `code("E", "SOURCE")`. `test_check_one_indefinite_logging_no_cap`: comment → "# Confirmed by the project owner: no
  failure-escalation cap - every failing cycle logs to console and count; a repeat spends no slot."; asserts
  `err_count == 5` and exactly one `code("E", "SOURCE")` entry in the ring. `test_check_one_last_value_and_triggered_reflect_most_recent_call_only`
  → `test_check_one_returns_the_most_recent_trigger_state` (`True` for 2000, then `False` for 0). `test_check_one_never_raises`
  adds the values `"abc"`, `[1]`, `"1800"`. New `test_a_non_numeric_value_logs_one_source_entry_and_never_triggers`
  (`"1800"`: `False`, one `code("E", "SOURCE")`; a `_monitor_loop()` task under driven time keeps cycling and a second
  cycle with a numeric value flashes).
- **Resolved**: —
- **Unit**: U9 (stages U2 codes, U3 slot rule, U22 removal).
  A-C2 step order: A.U2.17's part lands in U3, not U2 (it follows A.U2.17's own change, which lands in U3).
- **Depends**: M.SRC_SENS.035.
- **Blast carried by**: catalog row 15 wording → A.U9.08 (GEN).
- **Kind**: test

### M.TEST_UNIT.088 Flash ordering under driven time
- **From**: A.U35.13 (`:912`, `:933`, `:958`, `:982`, `:1005`, `:1008`), A.U8C.12 (their tags), A.U10.44
  (`start_asy_notify_monitor` → `start_asy_monitor`), A.U10.40 (`Interv`), A.U5.06.
- **Site**: `tests/test_asy_notification_service.py:890-1016`.
- **Change**: signals passed in the constructor's tuple; `{"FlashInterval": 3600.0, "FlashDur": 0.5}`; tasks start with
  `service.start_asy_monitor()`; `_one_cycle(clock, task, <n_triggered × 2 × 500 + one tick>)` replaces the 3.5/1.2 s
  waits (the `:908-909` comment → "# FlashDur's schema minimum 0.5 s: each triggered signal settles 2 × 0.5 s of virtual
  time."). `test_registration_order_drives_poll_order_not_construction_order` → `test_tuple_order_drives_poll_order_not_construction_order`
  (the signals built A, B, C and passed as `(c, a, b)`). `test_flashes_run_strictly_sequentially_not_interleaved`: the
  0.05 s settle → one `sleep(0)` round (comment "one yield lets the monitor park on the stalled callback (a limit)"),
  the 1.3 s → `clock.advance(1000)` (the first flash's own settle). Assertions hold.
- **Resolved**: as M.TEST_UNIT.082 (the wait tags are withdrawn).
- **Unit**: U35 (stages U5, U10).
- **Depends**: M.SRC_SENS.036, .037.
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.089 The sleep window: across midnight, across a clock step
- **From**: A.U9.01 (`:1024-1073` hold; new `_in_window()` table and a 23:30 cycle), A.U10.28 (c) (new window-step
  L1), A.U35.13, A.U2.17 (`:1112`), A.U10.40.
- **Site**: `tests/test_asy_notification_service.py:1019-1131`; new tests after `:1073`.
- **Change**: the five gating tests take the constructor tuple, `FlashInterval`, driven cycles; their `"FlashDur":
  0.01` writes go (0.01 is below the field's 0.5 minimum, so the write was refused as `Invalid` and never shortened
  anything; the virtual clock covers the default). `test_local_time_callback_raises_treated_as_none`: newest entry
  `code("E", "CALLBACK")`. New `test_in_window_handles_same_day_overnight_and_whole_day_windows`: the A.U9.01 table
  through `asy_notification_service._in_window(on_min, off_min, cur_min)` — 22:00-06:00 at 21:59 False, 22:00, 23:59,
  00:00, 06:00 True, 06:01, 12:00 False; 10:00-10:00 at 10:00 True, 10:01 False; 00:00-23:59 True at every hour. New
  `test_an_overnight_window_flashes_at_23_30` (window 22-6, `_FakeClock(23, 30)`, one cycle: one flash). New
  `test_a_clock_step_across_on_time_flashes_at_most_once_per_cycle` (A.U10.28 (c)): window from 10:00, the fake clock
  stepped from 09:59 to 10:01 and back between and within cycles: never two flashes in one cycle.
- **Resolved**: —
- **Unit**: U9 (stages U2 code, U10 key, U35 driven time).
  A-C2 step order: A.U2.17's part lands in U3, not U2 (it follows A.U2.17's own change, which lands in U3); A.U10.28's part lands in U16, not U10 (it needs A.U16.18, which lands in U16).
- **Depends**: M.SRC_SENS.037.
- **Blast carried by**: L2 window scene → A.U9.01 (TWIN); the twin RTC step hook (L2 half of A.U10.28) → A.U10.28
  (TWIN, pending U25).
- **Kind**: test

### M.TEST_UNIT.090 The LED override: a measured pause in virtual time
- **From**: A.U9.09 (`:1133-1168` adapted; `:1170-1206` holds), A.U10.44 (`start_asy_auto_override` →
  `start_asy_pause`, `auto_led_override()` → `_pause_loop()`, `monitor_loop()` → `_monitor_loop()`), A.U20.06
  (`:1176` `start_and_check_tasks()`), A.U35.13 (`:1147`, `:1153`, `:1155`, `:1184`, `:1186`, `:1192`), A.U8C.12 +
  A.U8C.120 (withdrawn), A.U8C2.02 (`:1152`, `:1185` `_OVERRIDE_SECS`), A.U22.03 (withdrawn: nothing to merge).
- **Site**: `tests/test_asy_notification_service.py:1133-1229`.
- **Change**: `test_override_active_blocks_checks_and_resumes_after_countdown`: `_OVERRIDE_SECS = 2` (module level,
  `# @tunable l1.asy_notification_service_override_secs = 2`); the pause task `service.start_asy_pause()`; `before`
  after one `sleep(0)` round; `set_override_led(_OVERRIDE_SECS)`; `clock.advance(1000)` → `during is False`;
  `clock.run_until(lambda: service._auto_active, 2000 + 1000)` → `after is True` at the pause's measured end; its
  `:1134-1140` comment → "# _pause_loop() is _auto_active's only writer; the monitor only reads it. The override ends
  at the first one-second round after its measured end." (three lines at most), `:1149-1151` goes. `test_monitor_loop_restart_does_not_clobber…`:
  the same names, `clock.advance(1000)` steps, `_monitor_loop()` restarted through `start_asy_monitor()`; `:1176`
  names `start_tasks()`/`supervise_tasks()`. `test_set_override_led_above_the_max_clamps…`: `:1209-1214` comment →
  "# The public override API clamps to _MAX_OVERRIDE_TIME (read from source)."; `3600` →
  `src_const("src/asy_notification_service.py", "_MAX_OVERRIDE_TIME")`.
- **Resolved**: A.U9.09's 3.2 s wall-clock bound becomes a virtual-time bound (A.U35.13); the override tick tags of
  A.U8C.12/A.U8C.120 are withdrawn with their literals, `_OVERRIDE_SECS` (a stimulus, not a wait) keeps its tag.
- **Unit**: U35 (stages U9 measured pause, U10 names, U8 tag).
  A-C2 step order: A.U9.09's part lands in U10, not U9 (it follows A.U9.09's own change, which lands in U10).
- **Depends**: M.SRC_SENS.036; M.SRC_CORE `TickSeconds` (A.U10.02).
- **Blast carried by**: twin `:349-390` and bench `:115-141` → A.U9.09 (TWIN, HW_BENCH).
- **Kind**: test

### M.TEST_UNIT.091 Own-config read failures log in both layers; the next sleep in milliseconds
- **From**: A.U3.02 (`:1350-1407` rewritten to the central slot rule), A.U3.05 dropped (OR140.a (7): NOTIFY keeps its
  own entry beside the store's; A-C review fold), A.U31.14 (`:1256-1279`
  `_next_sleep_ms`), A.U8C.12 (`:1266` `_ELAPSED_STIMULUS_MS`), A.U8C2.02 (`:1268` `_NEXT_SLEEP_MIN_S`), A.U35.13
  (`:1245`), A.U10.06 (`:1439` needs a sync), A.U24.49 (`_FastAsyncSleep`).
- **Site**: `tests/test_asy_notification_service.py:1232-1279`, `:1350-1440`.
- **Change**: `test_malformed_own_config_read_degrades_gracefully…` runs one driven cycle (`advance(100)`) and also
  asserts the task is still running. `test_next_sleep_secs_subtracts_elapsed_time` → `test_next_sleep_ms_subtracts_elapsed_time`:
  module-level `_ELAPSED_STIMULUS_MS = 50` (`# @tunable l1.asy_notification_service_elapsed_stimulus_ms = 50`) for the
  real `time.sleep_ms()`, `_NEXT_SLEEP_MIN_MS = 59000` (`# @tunable l1.asy_notification_service_next_sleep_min_ms =
  59000`), `_NEXT_SLEEP_MIN_MS < service._next_sleep_ms(60.0, t0) < 60000`; the local `import time` goes (module level).
  `…floors_at_point_one…` → `test_next_sleep_ms_floors_at_the_minimum_when_elapsed_exceeds_the_interval`: `== 100`.
  The three config-failure tests keep popping `"FlashBri"` from the real store's cache and run under `FastAsyncSleep()`
  (shared, both sleeps): `…persists_one_slot` asserts the task still runs, the NOTIFY log holds its own config-read
  code (HEAD's 11, by the catalog name the fold gives it back) in one slot with `ErrCount > 5`, and `CFGMGR_NOTIFY`
  likewise one `code("E", "CONTRACT")` slot; `…persists_the_config_read_warning_afresh_after_a_good_read`
  → `test_monitor_loop_config_failures_before_and_after_a_good_read_share_one_slot` (each of the two rings holds one
  slot, `ErrCount` counts both runs; the HEAD "afresh" claim is retired by the newest-entry rule, OR35.b);
  `…self_heals_in_place…` calls `set_utc_valid()` first (flag reset in `finally`) so `ts_after is not None` still
  proves a stored cycle.
- **Resolved**: A.U8C2.02's `next_sleep_min_s = 59.0` follows A.U31.14's millisecond return: the constant and its row ID
  take the ms unit (A.U10.43's suffix rule) — agent decision, OR2.c list.
- **Unit**: U31 (stages U3 slot rule, U8 tags, U10 sync).
- **Depends**: M.SRC_SENS.034, .037 (as the fold reverts A.U3.05); M.SRC_CORE.032; [fold F11 M_GEN] (the restored
  NOTIFY code's name).
- **Blast carried by**: Part N row ID `l1.asy_notification_service_next_sleep_min_ms` → GAP (SPEC, see "Gaps").
- **Kind**: test

### M.TEST_UNIT.092 Edge cases: callback failures in one slot, the retired pre-finalize guards
- **From**: A.U2.17 + A.U3.01 (`:1327`), A.U5.06 (`:1330-1347` goes with the guards), A.U10.44 (`:1344-1345`),
  A.U35.13 (`:1296`, `:1322`), A.U8C.12 (`:1322` tag), GAP-17 lead ruling (AC_NOTES 38).
- **Site**: `tests/test_asy_notification_service.py:1282-1347`.
- **Change**: `test_zero_registered_signals_just_sleeps_no_crash` → `test_no_signals_just_sleeps_no_crash`, one driven
  cycle. `test_request_signal_cb_raising_is_caught_and_the_loop_continues`: one driven cycle of `2 × 1000` ms; `len(cb.calls)
  == 2`, `err_count == 2`, one `code("E", "CALLBACK")` slot. `test_methods_called_before_finalize_degrade_gracefully_not_raise`
  is removed with `finalize()` and its guards (M.SRC_SENS.033: the service is complete at construction); the
  behaviour before `setup()` is the readiness L1's (M.TEST_UNIT in `tests/test_readiness_gates.py`), whose expected
  answers for this class wait on the lead question below.
- **Resolved**: —
- **Unit**: U5 (stages U2/U3 codes, U35 driven time).
  A-C2 step order: A.U2.17's part lands in U3, not U2 (it follows A.U2.17's own change, which lands in U3).
- **Depends**: M.SRC_SENS.033, .034.
- **Blast carried by**: the readiness L1 → A.U10.22 (TEST_UNIT).
- **Kind**: test

### M.TEST_UNIT.093 The `_now()` overflow tests go with `_now()`
- **From**: A.U10.06 (`:1443-1498` removed), A.U14.26 (`_RaisingGmtime` → `MemoryError`: dropped), A.U24.49
  (`_OverflowingTime` shared: moot here), A.U14.34 (read: `:1440-1450` cited as the module-time mocking example).
- **Site**: `tests/test_asy_notification_service.py:1443-1498`.
- **Change**: `_OverflowingTime`, `_RaisingGmtime` and the two `test_now_*` tests are removed: `_now()` is gone and
  `utc_now()` has no handler (M.SRC_SENS.034). The guard that replaces them is the `utc_now()` L1 in
  `tests/test_base_classes.py` (`None` before sync, a number after).
- **Resolved**: A.U10.06 vs A.U14.26 at the timestamp — ruled for A.U10.06 (V.U18.R10; M.SRC_SENS.034, M.SRC_CORE.032).
- **Unit**: U10.
- **Depends**: M.SRC_SENS.034.
- **Blast carried by**: `utc_now()` L1 → A.U10.06 (TEST_UNIT, `test_base_classes.py`).
- **Kind**: test

### M.TEST_UNIT.094 Starter names
- **From**: A.U10.44, A.U5.06.
- **Site**: `tests/test_asy_notification_service.py:1500-1508`.
- **Change**: built with `_make_service()`; `[s.__name__ for s in service.get_task_starters()] == ["start_asy_monitor",
  "start_asy_pause"]`; `get_timer_starters() == []`.
- **Resolved**: —
- **Unit**: U10.
- **Depends**: M.SRC_SENS.036.
- **Blast carried by**: —
- **Kind**: test

## tests/test_asy_ntp_client.py

### M.TEST_UNIT.095 Header, schema read from source, the timing builder, shared doubles, plain addresses
- **From**: A.U10.37/A.U10.38 (`AsyNtpClient` → `NTPClient`, `AsyFramManager` → `FRAMManager`, `print_log` →
  `asy_print_log`), A.U24.08 (`run`), A.U24.01 (`:50-57` `_VAL_*` mirrors → `src_const`), A.U10.41 + A.U18.10 (`:53`
  mirror: moot after the source read), A.U5.10 + A.U5.15 (`make_client()` takes an `NtpTiming`), A.U5.02 (`debug=`/
  `fram=` → `log=`), A.U10.18 (`network_available` → `network_available_locked`), A.U28.28 (2) (`:85`, `:87` lambdas →
  local `def`s), A.U8C.13 (`:73-77` tags), A.U18.10 (G2/R22: no L1 builder reaches a public resolver), A.U10.10 (the
  builder calls `setup()`), A.U24.49 (`_RaiseOnArm`), A.U24.70 (`:142-160` → `PortAllocator`), A.U18.12 (`make_addr()`
  `:146-150` → a plain tuple, the address shim at import), A.U18.11 (`:154-156` comment), A.U24.76, A.U24.73.
- **Site**: `tests/test_asy_ntp_client.py:1-160`.
- **Change**: imports `from asy_ntp_client import NTPClient, NtpTiming`, `from asy_fram_manager import FRAMManager`,
  `from asy_print_log import LogConfig, PrintLogHistoryStore`, `from asy_base_classes import set_utc_valid`, `from
  _async_harness import run, cancel`, `from _fake_timer_arm import RaiseOnArm`, `from _port_bands import PortAllocator`,
  `from _udp_port_redirect import redirect_udp_port`, `from _ntp_frames import FakeNtpServer, make_ntp_reply`, `from
  _src_const import NTP_EPOCH_DELTA, src_const`, `from _error_codes import code`, `from _fake_time import tick`, the
  address shim applied once at import; TYPE_CHECKING drops `Any`/`TypeVar`/`T`/`NoReturn` (A.U24.73's coroutine alias).
  `:50-57` → `_SCHEMA = src_const("src/asy_ntp_client.py", "_VAL_NTP_HOST") + … + "_VAL_DNS_FALLBACK"` (six reads, in
  the constructor's order), comment "# The client's schema, read from source (tests/_src_const.py)." Module constants
  `_DNS_TIMEOUT_MS = src_const("src/asy_dns_client.py", "_DNS_TIMEOUT_MS")`, `_DNS_TRIES = src_const(…, "_DNS_TRIES")`,
  `# @tunable ntp.fetch_timeout_ms = 5000` / `_FETCH_TIMEOUT_MS = 5000`, `_RETRY_S`/`_RETRY_MAX_S = src_const(
  "src/asy_ntp_client.py", "_DEFAULT_RETRY_S"/"_DEFAULT_RETRY_MAX_S")`. `make_client(...)` → `_make_client(*,
  wifi_mode_lock=None, network_available_locked=None, get_dns_server=None, timing: NtpTiming | None = None, log:
  LogConfig = DEFAULT_LOG, cfg_path=None, dns_fallback: str | None = "")`: defaults through local `def`s (no lambdas),
  `timing` defaulting to `NtpTiming(_DNS_TIMEOUT_MS, _DNS_TRIES, _FETCH_TIMEOUT_MS, _RETRY_S, _RETRY_MAX_S)`,
  `NTPClient(lock, net, dns, timing, cfg_path=…, log=log)`, `run(client.setup())`, then, unless `dns_fallback is None`,
  `run(client.cfgmgr.write_config({"DNSFallback": dns_fallback}))` (comment "# No L1 client asks a public resolver: the
  fallback list is empty unless a test sets it."). `make_client_with_json()`/`make_invalid_cfg_client()` →
  `_make_client_with_json()`/`_make_invalid_cfg_client()` (keys per A.U10.40). Every former `make_client(retry_s=a,
  retry_max_s=b, …)` call passes `timing=NtpTiming(_DNS_TIMEOUT_MS, _DNS_TRIES, _FETCH_TIMEOUT_MS, a, b)` through one
  `_timing(**overrides)` helper. `_RaiseOnArm` goes (shared `RaiseOnArm`). `_next_port`/`make_port()`/`make_addr()` →
  `_PORTS = PortAllocator("test_asy_ntp_client")` and `_make_addr() -> ("127.0.0.1", _PORTS.next())` (a plain tuple:
  the shim rewrites it for this Unix build); the `:148-149` and `:154-156` comments go.
- **Resolved**: A.U8C.13's mirror tags on `:73-77` vs A.U24.01's source-read rule: values the product still defines
  (`_DNS_TIMEOUT_MS`/`_DNS_TRIES` in the resolver, `_DEFAULT_RETRY_S`/`_DEFAULT_RETRY_MAX_S`, M.SRC_NET.020/.042) are read
  from source and take no tag; `ntp.fetch_timeout_ms` has no `src/` constant left (M.SRC_NET.042: codegen owns it), so
  its test copy keeps the mirror tag. A.U18.10's G2/R22 rule vs its recorder tests' schema-default assertions: the
  builder empties the fallback by default and the recorder tests pass `dns_fallback=None` (they do no I/O).
- **Unit**: U18 (stages U5 timing/log, U10 names/setup, U24 harness, ports, doubles).
  A-C2 step order: A.U24.70's part lands in U25, not U24 (it follows A.U24.70's own change, which lands in U25).
- **Depends**: M.SRC_NET.041-.044; TEST_HELP `_ntp_frames.py` (`FakeNtpServer`, `make_ntp_reply`), `_port_bands.py`,
  `_udp_port_redirect.py`, `_fake_time.tick`, the moved address shim (A.U18.12).
- **Blast carried by**: Part N `ntp.fetch_timeout_ms` further site → A.U8.01 (SPEC); `pyproject.toml` E731 noqa removal →
  A.U28.28 (TOOL).
- **Kind**: test

### M.TEST_UNIT.096 Construction, starters and the FRAM-backed logger
- **From**: A.U10.40 (keys), A.U11.15 (`:224` `get_level()` → `level`), A.U5.02 (`debug=3`, `fram=manager`), A.U10.44
  (`:227-272` starter names), A.U24.39 (`:275-282` asserts the entry lands in the chunk), A.U10.38, A.U18.10
  (`DNSFallback` in the stored set), A.U24.08.
- **Site**: `tests/test_asy_ntp_client.py:162-283`.
- **Change**: the section comment → "# Construction: the client owns its config_NTP.cfg and schema (SensorReaderConfig)."
  (the "no externally-injected ConfigManager … see SPECIFICATION.md/BACKLOG.md" history goes). The defaults test reads
  `["NTPHost", "NTPOffset", "NTPInterval", "GMTOffset", "DSTOffset", "DNSFallback"]` and expects
  `"DNSFallback": ""` (the builder's) beside the HEAD values. The two `_get_ntp_config()` tests unpack `host, _fallback,
  _offset` and compare `host == "time.example.org"`. `test_debug_level_propagates…`: `_make_client(log=LogConfig(None,
  10, 3))`, `client.pr.level == 3`. `test_get_task_starters_returns_all_three_ntp_tasks`: `[client.start_asy_sync,
  client.start_asy_refresh, client.start_asy_sync_age]`; timer starters `[client.start_check_timer,
  client.start_sync_age_timer]`; the two "returns a real task" tests call `start_asy_refresh()`/`start_asy_sync_age()` and
  end with `await cancel(task)`. `test_fram_given_uses_fram_backed_logging` → `…_logs_into_the_fram_chunk`: `manager =
  FRAMManager(bus, 1, max_size=0x2000)`, `_make_client(log=LogConfig(manager, 10, None))`, the logger is a
  `PrintLogHistoryStore`, and an `err_s("probe", errno=code("E", "CALLBACK"))` through `client.pr` is read back by a
  second `PrintLogHistoryStore` over the same manager.
- **Resolved**: —
- **Unit**: U10 (stages U5 log, U11 level, U18 fallback, U24 assertion).
- **Depends**: M.SRC_NET.043, .044, .054; M.SRC_CORE (`PrintLogHistoryStore`, `FRAMManager`).
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.097 The getter quartet: renamed keys, the fallback field, no history pointer
- **From**: A.U18.21 + A.U0.40 (`:286-287` comment), A.U10.40, A.U18.10, A.U10.06 (`TS` before sync), A.U10.10 (`:360`,
  `:373`, `:381` `pr.setup()` lines).
- **Site**: `tests/test_asy_ntp_client.py:285-386`.
- **Change**: `:286-287` → "# get_dict_cfg / get_data / get_dict_data / get_error_counter - the base-class getter quartet
  (SPECIFICATION.md Part C.4.2)." The three `get_dict_cfg()` expectations use `NTPHost`/`NTPOffset`/`NTPInterval` and
  gain `"DNSFallback"` (`""` for the builder's client, `None` for the invalid store; the on-disk JSON test's file omits
  it, so the schema default `"8.8.8.8,1.1.1.1"` shows). The never-synced test asserts `data.TS is None`. The in-test
  `pr.setup()` lines go.
- **Resolved**: A.U0.40 rewrites the `:287` sentence ("The setters come from … by inheritance (since `3f1fcc0`) …");
  A.U18.21 (U18, later) removes it. Removed: after M.SRC_NET.045 the client has its own `_set_mgr_cfg()` override, so
  "by inheritance" no longer holds, and a commit pointer is history in a comment (CLAUDE.md "current state").
- **Unit**: U18 (stages U10 keys).
- **Depends**: M.SRC_NET.043.
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.098 State helpers: `_now()` and the age increment go
- **From**: A.U10.06 (`:398-435` go), A.U14.26 (`:405-425` `_RaisingTimeForNow` → a `MemoryError`: dropped), A.U10.03
  (`:477-506` go; "preserves the Synced flag" moves to the publish path), A.U8C2.03 (`:402` tag: no site left).
- **Site**: `tests/test_asy_ntp_client.py:388-506`.
- **Change**: the section comment → "# The state helpers _set_synced()/_set_last_sync_age(): each does an unlocked
  get-then-set with no await between (see asy_ntp_client.py's comment on _set_synced())." (three lines at most).
  `test_now_returns_a_real_unix_timestamp`, `_RaisingTimeForNow` and the two `test_now_returns_none_*` tests are removed
  (`_now()` is gone; `utc_now()`'s L1 is `tests/test_base_classes.py`'s). The four `_increment_last_sync_age()` tests are
  removed; `test_the_sync_age_publish_keeps_the_synced_flag` replaces the last of them (synced, one `_sync_age_loop()`
  tick: `Synced` stays `True`). The four `_set_synced()`/`_set_last_sync_age()` tests hold.
- **Resolved**: A.U10.06 vs A.U14.26 at `_now()` — ruled for A.U10.06 (V.U18.R10; M.SRC_NET.052).
- **Unit**: U10.
- **Depends**: M.SRC_NET.052, .058.
- **Blast carried by**: `utc_now()` L1 → A.U10.06 (TEST_UNIT, `test_base_classes.py`).
- **Kind**: test

### M.TEST_UNIT.099 Timer starters record their outcome; a second failed arm ends the sync task
- **From**: A.U10.44 (`start_ntp_timer`/`stop_ntp_timer`/`start_counter_timer`/`stop_counter_timer` →
  `start_check_timer`/`stop_check_timer`/`start_sync_age_timer`/`stop_sync_age_timer`), A.U10.35 (`ntp_timer`,
  `counter_timer`, `ntp_timer_trigger_event` → private), A.U18.23 (`:540-589` gain the flags; new L1), A.U10.03 (`:562-589`
  hold), A.U8C.13 (`:517` `ntp.check_interval_s` mirror, `:527` `l1.asy_ntp_client_event_wait_s`), A.U24.49, A.U11.15/
  A.U5.02 (`debug=1`).
- **Site**: `tests/test_asy_ntp_client.py:508-589`.
- **Change**: `# @tunable ntp.check_interval_s = 10` / `_CHECK_INTERVAL_S = 10` (module level) and `assert
  client._ntp_timer.period == _CHECK_INTERVAL_S * 1000`; `# @tunable l1.asy_ntp_client_event_wait_s = 0.2` /
  `_EVENT_WAIT_S = 0.2` for every `wait_for(…, 0.2)` in the file. Each degrade test uses `RaiseOnArm(exc)` and adds
  `client._check_armed is False` (check timer) or `client._tick_armed is False` (sync-age timer); the `debug=1`
  builders become the default log (the expected-output `print` lines stay). New
  `test_an_arm_failing_twice_ends_the_sync_task_with_one_timer_entry` (`start_check_timer()` under `RaiseOnArm`, then
  `_sync_loop()` as a task with the raise still on: the task ends at its first `_rearm_failed_timers()` with one
  `code("E", "TIMER")`) and `test_a_restarted_sync_task_rearms_the_check_timer` (arm failed once, raise cleared,
  `_sync_loop()` started: `_ntp_timer.period == _CHECK_INTERVAL_S * 1000`, `PERIODIC`, `_check_armed is True`).
- **Resolved**: —
- **Unit**: U18 (stages U10 names, U8 tags).
- **Depends**: M.SRC_NET.054, .056; M.SRC_CORE `arm_tick_timer()`.
- **Blast carried by**: twin 16-alarm pool L2 → A.U18.23 (TWIN); Part N rows → A.U8.01 (SPEC).
- **Kind**: test

### M.TEST_UNIT.100 A forced resync clears `Synced`
- **From**: A.U18.21 (`:597-613` gains the `Synced` assertion; new L1), A.U10.35 (`ntp_retries`, `ntp_retry_timer`,
  `ntp_sync_trigger_event`), A.U8C.13 (`:607`).
- **Site**: `tests/test_asy_ntp_client.py:592-620`.
- **Change**: the first test starts synced (`_set_synced(value=True)`) and asserts `not await client.ntp_issynced()`
  after `ntp_force_sync()`, beside the HEAD asserts on the private names; the wait uses `_EVENT_WAIT_S`. New
  `test_a_forced_resync_reports_unsynced_and_no_local_time_until_the_next_success` (synced, `ntp_force_sync()`:
  `ntp_issynced()` False and `cettime()` `None`; `_handle_ntp_sync_success(tm)`: both return again).
- **Resolved**: —
- **Unit**: U18.
- **Depends**: M.SRC_NET.055.
- **Blast carried by**: per-device PUT scenario → A.U18.21 (TEST_HELP, `tests/_sensortask_scenarios.py`).
- **Kind**: test

### M.TEST_UNIT.101 Config reads: the three-value tuple and the stored-host use path
- **From**: A.U10.40 (keys in `_VALID_JSON` and the inline JSON), A.U18.10 (`_get_ntp_config()` returns `(host,
  fallback, offset)`), A.U10.41 (use-path check of a stored `NTPHost`, M.SRC_NET.046).
- **Site**: `tests/test_asy_ntp_client.py:622-706`.
- **Change**: `_VALID_JSON` and the four inline JSON strings use `NTPHost`/`NTPOffset`/`NTPInterval`; every
  `ntp_host, ntp_offs = ntp_cfg` → `host, fallback, offset = ntp_cfg` with scalar expectations (`"time.example.org"`,
  `5`; defaults `"pool.ntp.org"`, `0`), and `fallback == "8.8.8.8,1.1.1.1"` where the file omits the key (the
  `_make_client_with_json()` builder passes `dns_fallback=None` so the file's content stands). New
  `test_a_stored_host_that_is_not_a_host_name_uses_its_default` (a file with `"NTPHost": "-bad-.example"`: the read
  returns `"pool.ntp.org"` and the log holds one `code("W", "STORED_DEFAULT")`).
- **Resolved**: —
- **Unit**: U18 (stage U10 keys).
- **Depends**: M.SRC_NET.045, .046.
- **Blast carried by**: the `hostName` corpus → A.U10.41 (TEST_HELP `_radio_shape_cases.json`).
- **Kind**: test

### M.TEST_UNIT.102 DNS-server callback and server resolution: one code class, the fallback list in order
- **From**: A.U2.15 (`:742-743` w3 → `CALLBACK` E; `:838-839` e12 → `NTP_DNS`), A.U18.10 (`:758-833` third argument,
  recorder tuples gain the fallback; new L1), A.U18.15 (`_RecordingResolver` accepts `pr`), A.U10.10 (`pr.setup()`
  lines), A.U10.38 (`AsyConnTime.get_dns_server_ip` → `WifiService.get_dns_server_ip` in `:710`), A.U10.44 (`:711`
  `asy_ntp_time()` → `_sync_loop()`), A.U18.33 (read: the callback name is unchanged).
- **Site**: `tests/test_asy_ntp_client.py:709-848`.
- **Change**: section comments name `WifiService.get_dns_server_ip` and `_sync_loop()`.
  `test_safe_get_dns_server_callback_raising_persists_a_warning` → `…persists_a_callback_error`: newest `code("E",
  "CALLBACK")`, type `"E"`. `_RecordingResolver.__call__(host, dns_servers=(), timeout_ms=0, tries=0, pr=None)`; its
  clients are built with `dns_fallback=None`; the recorded tuples become `("pool.ntp.org", ("192.0.2.53", "8.8.8.8",
  "1.1.1.1"), 500, 1)`, `("pool.ntp.org", ("8.8.8.8", "1.1.1.1"), 500, 1)` and `…, 1234, 3)` (the timing test passes
  `timing=_timing(dns_timeout_ms=1234, dns_tries=3)`); every direct `_resolve_ntp_server(host, dns)` call passes the
  third argument (`""` or the stored list). `…dns_failure_persists_an_error`: newest `code("E", "NTP_DNS")`. New
  `test_resolve_ntp_server_asks_dhcp_first_then_the_fallback_list_in_order` and
  `test_an_empty_fallback_asks_only_the_dhcp_server` (recorder). `:842-848` keep their two three-line blocks.
- **Resolved**: —
- **Unit**: U18 (stages U2 codes, U10 names).
  A-C2 step order: A.U2.15's part lands in U3, not U2 (it follows A.U2.15's own change, which lands in U3).
- **Depends**: M.SRC_NET.046, .047.
- **Blast carried by**: L1 "no `UDPSocket` constructed with an empty fallback" → M.TEST_UNIT in
  `tests/test_ntp_wifi_dns_integration.py` (A.U18.10).
- **Kind**: test

### M.TEST_UNIT.103 The fetch: own write and receive, 48 bytes, a gated responder, teardown
- **From**: A.U18.14 (`:865-900` the fake exposes `write()`/`recvfrom()`/`disconnect()`; new never-connected L1), A.U18.13
  (`:871` `conn_tries` leaves the double), M.SRC_NET.048 (the construction `try` is removed: `:856-859` and `:897-903`
  go), A.U2.15 (`:912` 21 → `NTP_NO_REPLY`), A.U35.12 (`:945-948` → a ready event), A.U14.28 (`:928-930` row-13
  pointer), A.U18.15 (new cancel and teardown L1), A.U18.16 (new 90 B L1), A.U8C.13 (`:871`, `:876` tags: no site;
  `:936`, `:940` `l1.asy_ntp_client_fake_server_poll_ms`), A.U8C2.03 (`:927` `l1.asy_ntp_client_responder_poll_tries`),
  A.U10.38 (`AsyUDPSocket` → `UDPSocket`).
- **Site**: `tests/test_asy_ntp_client.py:851-953`.
- **Change**: `test_fetch_ntp_reply_invalid_addr_returns_none` and `…ipv6_shaped_four_tuple_addr_returns_none` are
  removed with the construction guard (the only caller passes `(ip, 123)` from the resolver; G5/R54). `_RecordingUDPSocket`
  → `_FakeUDPSocket(addr, mode="client")` recording `write(msg, timeout_ms)` and `recvfrom(n, timeout_ms)` calls (each
  returning the None-shaped sentinel the real socket returns for silence) and `disconnect() -> bool` (settable result);
  `test_fetch_ntp_reply_forwards_the_constructors_own_fetch_timeout` swaps `asy_ntp_client.UDPSocket` and asserts the
  9999 ms timeout reached both calls and `recvfrom` asked for 48 bytes. `…no_server_listening…`: newest `code("E",
  "NTP_NO_REPLY")`. The responder test: `responder(ready: asyncio.Event)` sets `ready` right after `bind()` and
  `register()`; the scenario awaits `ready.wait()` in place of the `:945` yield and its three-line comment; `:928-930`
  → "# ipoll(0) returns an always-truthy iterator: test the event flags (SPECIFICATION.md F.7 row 13)."; module
  constants `# @tunable l1.asy_ntp_client_responder_poll_tries = 500` / `_RESPONDER_POLL_TRIES = 500` and `# @tunable
  l1.asy_ntp_client_fake_server_poll_ms = 10` / `_FAKE_SERVER_POLL_MS = 10`. New (A.U18.14):
  `test_a_never_connected_socket_logs_not_sent_and_returns_before_the_fetch_timeout` (the fake's `write()` returns `None`:
  one `code("E", "NTP_NOT_SENT")`, no `NTP_NO_REPLY`, returns at once). New (A.U18.15):
  `test_a_cancelled_fetch_still_disconnects` (a fake whose `recvfrom()` parks on an event; the task cancelled: the cancel
  re-raised and `disconnect()` called) and `test_a_failed_teardown_leaves_one_socket_teardown_warning` (`disconnect()`
  → `False`: one `code("W", "SOCKET_TEARDOWN")`). New (A.U18.16): `test_a_long_reply_is_read_as_its_48_byte_header` (a
  real loopback responder sends 90 bytes whose first 48 are a valid header: the client syncs from it).
- **Resolved**: —
- **Unit**: U18 (stages U2 codes, U14 pointer, U35 gate).
  A-C2 step order: A.U2.15's part lands in U3, not U2 (it follows A.U2.15's own change, which lands in U3).
- **Depends**: M.SRC_NET.048; M.SRC_NET.026/.029 (`UDPSocket` surface).
- **Blast carried by**: SPEC F.7 rows → A.U14.28 (SPEC); `udp.round_trip_tries_default` dropped → A.U18.14 (SPEC).
- **Kind**: test

### M.TEST_UNIT.104 Reply parsing: shared frames, the 2057 hand check, reachable failures only
- **From**: A.U24.49 (`make_ntp_reply()` `:968-977` → `tests/_ntp_frames.py`), A.U24.01 (`:965` `_NTP_EPOCH_DELTA` →
  `_src_const.NTP_EPOCH_DELTA`; `:1095, 1104, 1113` → `src_const`), A.U24.42 (`:1024-1027` asserts the hand-computed
  time), A.U14.26 (`:1030-1047` goes; new structural and `MemoryError` L1; `:1073-1074` comment), A.U8.09 (the window
  mirrors, now source reads), A.U24.24 (blast: the RTC read-back at `:987-989`; M_TEST_HELP GAP-T3, gap pass G3);
  routine settlement `ntp-malformed-text` (AC_NOTES 52: the allocation failure logs the shared ALLOC 20, errno 69 stays
  "malformed" only; A-C review fold).
- **Site**: `tests/test_asy_ntp_client.py:956-1155`.
- **Change**: the local `_NTP_EPOCH_DELTA`/`make_ntp_reply()` go (imported). `test_parse_ntp_reply_arbitrary_binary_content_never_raises`
  → `…decodes_arbitrary_bytes_as_their_transmit_timestamp`: `bytes(range(48))` gives `(2057, 6, 14, 17, 21, 47, …)`
  (hand-computed from bytes 40-43 = `0x28292A2B` seconds since 1900, the era rule and the window; the computation in one
  comment line). `_OverflowingTime` and `test_parse_ntp_reply_gmtime_overflow_returns_none_not_raise` go (no reachable
  input: the window keeps every accepted value below 2**32). New `test_the_plausibility_ceiling_fits_the_device_clock`:
  `src_const("src/asy_ntp_client.py", "_NTP_MAX_PLAUSIBLE_UNIX_TIME") < 2**32`. New
  `test_an_allocation_failure_while_parsing_returns_none` (`asy_ntp_client.time` replaced by a stand-in whose `gmtime()`
  raises `MemoryError("injected for the parse path")` — worded clear of the gate's markers — restored in `finally`:
  `None` and one `code("E", "ALLOC")` — the shared allocation code; `NTP_MALFORMED` stays the malformed-reply code). `:1073-1074` → "# NTP's 32-bit seconds-since-1900 field wraps in 2036,
  unrelated to the device clock, which runs to 2106 (Part F.1); a post-2036 server sends a small wrapped value." The
  floor/ceiling tests read `_FLOOR`/`_CEILING = src_const("src/asy_ntp_client.py", "_NTP_MIN_PLAUSIBLE_UNIX_TIME"/
  "_NTP_MAX_PLAUSIBLE_UNIX_TIME")` (their "compiled away, hardcoded" comments go).
  `test_parse_ntp_reply_valid_packet_returns_gmtime_and_sets_the_rtc` (`:980-989`): the read-back expects `(tm[0], tm[1],
  tm[2], tm[6], tm[3], tm[4], tm[5], 0)` — the RTC fake recomputes the weekday (Monday 0, gmtime's own convention) and
  ignores the `tm[6] + 1` the client writes, as rp2's setter does (`ports/rp2/machine_rtc.c:85-92`; M.TEST_HELP.021);
  one comment line says so.
- **Resolved**: A.U8.09's mirror sites `:1095, 1104, 1113` become source reads (A.U24.01), so the rows lose those test
  sites rather than gaining tags.
- **Unit**: U14 (stages U24 shared frames, source reads and the RTC read-back with M.TEST_HELP.021).
- **Depends**: M.SRC_NET.042, .049; TEST_HELP `_ntp_frames.py`, `_src_const.NTP_EPOCH_DELTA`, M.TEST_HELP.021.
- **Blast carried by**: — (catalog 69 keeps its "malformed" text; the allocation failure uses the shared ALLOC entry).
- **Kind**: test

### M.TEST_UNIT.105 Sync failure and success: codes, mirrors, one slot per repeat
- **From**: A.U10.35 (`ntp_retries`, `ntp_retry_timer`, `ntp_sync_trigger_event`), A.U2.15 (`:1222` 16 → `TIMER`),
  A.U8C.13 (`:1175` `ntp.retry_interval_s` mirror, `:1186` event wait), A.U8C2.03 (`:1198` `ntp.sync_retries`), A.U3.12
  (new: `TIMER` and `NTP_RETRIES` repeated spend one slot), A.U10.06 (success sets the UTC flag), A.U10.44 (`:1166`
  comment names `_refresh_loop()`).
- **Site**: `tests/test_asy_ntp_client.py:1158-1238`.
- **Change**: private names throughout; `# @tunable ntp.retry_interval_s = 15` / `_RETRY_INTERVAL_S = 15` and `period ==
  _RETRY_INTERVAL_S * 1000`; `# @tunable ntp.sync_retries = 3` / `_SYNC_RETRIES = 3` for `:1198`; `:1213-1215` comment →
  "the same TIMER error is persisted"; `:1222` → `code("E", "TIMER")`. The success tests also assert `data.TS is not
  None` (the flag set by the success; the after-each hook resets it). New
  `test_repeated_retry_arm_failures_count_each_and_keep_one_slot` (two failing arms: `ErrCount == 2`, one `TIMER` slot)
  and `test_repeated_retry_exhaustion_counts_each_and_keeps_one_slot` (`NTP_RETRIES` twice).
- **Resolved**: —
- **Unit**: U18 (stages U2 codes, U3 slot rule, U8 tags, U10 names).
  A-C2 step order: A.U2.15's part lands in U3, not U2 (it follows A.U2.15's own change, which lands in U3).
- **Depends**: M.SRC_NET.051, .052.
- **Blast carried by**: Part N mirror sites → A.U8.01 (SPEC).
- **Kind**: test

### M.TEST_UNIT.106 The refresh loop: staleness on the measured age, the legacy pin inverted
- **From**: A.U10.44 (`ntp_time_hours_counter()` → `_refresh_loop()`), A.U10.35 (`ntp_timer_trigger_event`,
  `ntp_sync_trigger_event`, `ntp_sec_count`), A.U24.49 (`_tick` `:1246-1250` → `tests/_fake_time.tick`), A.U35.12
  (`:1250`, `:1374`), A.U18.20 (`:1364-1386` driven ticks; `:1388-1410` inverted; two new L1), A.U8C.13 (`:1275, 1296,
  1326, 1350`, `:2446` waits), A.U8C2.03 (`:1375` `ntp.async_intervals`), A.U10.40 (keys).
- **Site**: `tests/test_asy_ntp_client.py:1241-1410`, `:2438-2468`.
- **Change**: the loop is started as `asyncio.create_task(client._refresh_loop())` and ended with `await cancel(task)`;
  `_tick(flag, n)` → the shared `tick(flag, n)` (its two `sleep(0)` rounds commented "two yields let one loop iteration
  finish (a limit, not an interleaving claim)" in the helper); `# @tunable l1.asy_ntp_client_fired_probe_s = 0.05` /
  `_FIRED_PROBE_S = 0.05` for `:1296`, `:2446`. `test_ntp_time_hours_counter_marks_out_of_sync_past_the_async_interval_multiple`
  → `test_refresh_marks_the_sync_stale_three_intervals_after_the_last_success`: `Ticks30Time` installed on
  `asy_base_classes` (the `TickSeconds` clock), `NTPInterval` 1, synced through `_handle_ntp_sync_success()`, ticks
  driven with the fake clock advanced 10 s per tick: `Synced` stays `True` up to `_ASYNC_INTERVALS × 3600 s` and turns
  `False` at the first tick past it (`# @tunable ntp.async_intervals = 3` / `_ASYNC_INTERVALS = 3`); no
  `_ntp_sec_count` poke. `…never_naturally_reaches_the_async_interval_multiple…` (the legacy pin) is inverted to
  `test_ntp_goes_stale_when_every_due_resync_fails` (every resync attempt failing through a fake resolver returning
  `None`; 3 h of driven ticks: `Synced` False at the first tick past 10,800 s and not before). New
  `test_a_successful_resync_restarts_the_age` (success at 2.5 h: still synced at 4 h) and
  `test_the_due_counter_never_exceeds_one_interval` (5 simulated days: `_ntp_sec_count < 3600` at every tick). The
  unsynced backoff tests (`:1289-1314`, `:2438-2468`) hold with the private names.
- **Resolved**: A.U18.20 retires the legacy-inherited pin "never naturally reaches 3×" by owner-backed intent (agent,
  2026-09-27; the comment in M.SRC_NET.057 cites legacy's own intent); guard: the inverted test.
- **Unit**: U18 (stages U10 names, U24 shared tick, U8 tags).
- **Depends**: M.SRC_NET.057; TEST_HELP `tests/_ticks30.py`, `_fake_time.tick`.
- **Blast carried by**: SPEC C.7.2/DEVICE_REFERENCE `NtpSynced` → A.U18.20 (SPEC, DOCS).
- **Kind**: test

### M.TEST_UNIT.107 `cettime()`: switch dates for the whole window, clock steps, no failure catch
- **From**: A.U14.28 (`:1418-1424` comment gains its F.7 row-4 pointer), A.SDEP.16 W41 (the normalisation and
  `test_this_interpreters_gmtime_returns_nine_elements_not_eight` go if the pin re-check finds an 8-element `gmtime()`),
  M.SRC_NET.053 + A.U14.26 as corrected by U18 register fix 10 (`:1535-1541` retired), A.U18.25 (new switch-date L1),
  A.U18.26 (new clock-step L1), A.U10.40 (`_client_with_offsets()` keys).
- **Site**: `tests/test_asy_ntp_client.py:1413-1570`.
- **Change**: `:1418-1424` → three lines: "# This Unix port's gmtime() returns 9 elements (trailing isdst) where rp2 returns
  8, so a shim truncates it for cettime()'s length check (SPECIFICATION.md F.7 row 4)."; the "Real finding, flagged…"
  paragraph goes (the finding is the F.7 row). `test_cettime_mktime_or_gmtime_failure_returns_none_not_raise` is
  removed (no catch remains; an allocation failure propagates by the register fix's rule). `_client_with_offsets()` uses
  the new keys. New `test_cettime_switches_on_the_last_sundays_of_march_and_october` (A.U18.25: 2025-2099, switch dates
  from the interpreter's own calendar, `_FixedNowTime` at 01:00 UTC minus 1 s and at it; one comment line on rp2's exact
  single-precision `5 * year / 4` to 2106). New (A.U18.26): `test_cettime_follows_a_backward_rtc_step_across_the_march_switch`,
  `test_sync_state_follows_measured_ticks_not_rtc_steps` (a year forward, two back: `Synced`/`LastSyncAge` unchanged),
  `test_the_first_sync_from_the_boot_default_restarts_the_age` (RTC at 2021-01-01, success at a 2026 time: age 0), and
  `test_an_offset_put_then_a_sync_shifts_the_rtc_and_cycles_synced`.
- **Resolved**: A.U14.28 (keep the shim, add the row) and A.SDEP.16 (remove it if the re-check finds the port fixed):
  staged — the U0 re-check decides; the row pointer stands while the row does.
- **Unit**: U18 (stages U0 re-check, U14 pointer).
- **Depends**: M.SRC_NET.053; TEST_HELP the settable-wall-clock fake of A.U10.28.
- **Blast carried by**: L2 RTC-step half → A.U10.28/A.U18.26 (TWIN, pending U25).
- **Kind**: test

### M.TEST_UNIT.108 The sync-age loop publishes the measured age
- **From**: A.U10.03 (`:1578-1610` rewritten on measured ticks; new 2.5 s L1), A.U10.44 (`time_counter()` →
  `_sync_age_loop()`), A.U10.35 (`time_counter_trigger_event`).
- **Site**: `tests/test_asy_ntp_client.py:1573-1610`.
- **Change**: section comment names `_sync_age_loop()`. `test_time_counter_increments_while_synced` →
  `test_sync_age_follows_measured_time_while_synced`: `Ticks30Time` installed on `asy_base_classes`, synced through
  `_handle_ntp_sync_success()`, three ticks each after `advance(1000)`: `get_last_ntp_sync() == 3`. New
  `test_a_late_wake_advances_the_age_by_the_measured_seconds` (one tick after `advance(2500)`: age 2). The never-synced
  test holds (`None`).
- **Resolved**: —
- **Unit**: U10.
- **Depends**: M.SRC_NET.058; M.SRC_CORE `TickSeconds`.
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.109 The sync attempt: three-value config, the renamed callback, console config line
- **From**: A.U10.18 (`network_available` → `network_available_locked`), A.U2.15 (`:1656-1657` w1 → `CALLBACK` E),
  A.U18.10 (fakes return `(host, fallback, offset)`; `_resolve_ntp_server(host, dns, fallback)`), A.U36.544 (`:1695`),
  A.U10.44 (`:1694` `asy_ntp_time()` → `_sync_loop()`), A.U24.73 (`list[Any]`).
- **Site**: `tests/test_asy_ntp_client.py:1613-1790`.
- **Change**: builders pass `network_available_locked=`; every `fake_get_cfg()` returns `("pool.ntp.org", "", 0)` (type
  `tuple[str, str, int] | None`); every `fake_resolve(_host, dns_server, _fallback)` takes three arguments (the
  `method-assign` ignores stay inline). `…network_available_raising_persists_a_warning` →
  `…persists_a_callback_error`: newest `code("E", "CALLBACK")`, type `"E"`. `:1693-1695` → "# Proves the attempt
  forwards its own dns_server unchanged: the value comes from _sync_loop()'s _safe_get_dns_server() call, read before
  wifi_mode_lock is taken (see that method's own comment)." `received: list[str | None]`, `handled_with: list[tuple[int,
  ...]]`.
- **Resolved**: —
- **Unit**: U18 (stages U2 code, U10 names).
  A-C2 step order: A.U2.15's part lands in U3, not U2 (it follows A.U2.15's own change, which lands in U3).
- **Depends**: M.SRC_NET.050.
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.110 The sync task: `async with`, no lazy logger, one slot per repeat, cancel safety
- **From**: A.U10.44 (`asy_ntp_time()` → `_sync_loop()`), A.U10.18 (`async with` replaces the try/finally release),
  A.U10.10 (`:1881-1897` lazy-setup test), A.U3.02 (`:1970-1976` episode masks; `:1994-2007` inverted; `:2010-2025`),
  A.U2.15 (`:1928`), A.U5.10 (`retry_s`/`retry_max_s` through `timing`), A.U8C.13 (`:1844`), A.U35.48 (new cancel sweep),
  A.U10.35.
- **Site**: `tests/test_asy_ntp_client.py:1793-2040`.
- **Change**: the section comment names `_sync_loop()` ("…the lock is released by `async with` even if the attempt
  raises"). Every `client.asy_ntp_time()` → `client._sync_loop()`, `ntp_sync_trigger_event` → `_ntp_sync_trigger_event`,
  task ends through `cancel()`. `test_asy_ntp_time_swallows_an_already_released_wifi_lock` is removed with the guard it
  pinned (an attempt releasing the shared lock itself is out of contract; `async with` owns the release); the guard
  that remains is `…releases_the_wifi_lock_even_if_the_attempt_raises`, which holds. `test_asy_ntp_time_calls_pr_setup_before_entering_its_loop`
  → `test_setup_initialises_the_logger_before_any_task`: `NTPClient(...)` built without the builder has
  `pr.initialized is False`; after `setup()` it is `True`; `_sync_loop()` does not call it. The never-gives-up test
  asserts `ErrCount == 0` in place of "`20` not in" (the retired give-up code). The backoff tests pass
  `timing=_timing(retry_s=10, retry_max_s=70)` etc. `test_a_successful_sync_resets_the_backoff_and_ends_the_failure_episode`
  → `test_a_successful_sync_resets_the_backoff` (the `_episode_*` lines go). `…persists_each_distinct_failure_code_once_per_episode…`
  is inverted (OR35.a (3)): the attempt logs `err_s(…, errno=code("E", "NTP_DNS"))` and `…"NTP_NO_REPLY"` alternately
  through `client.pr`; `ErrCount == 5` and the ring holds five slots (alternation spends a slot each).
  `test_episode_log_persists_a_code_again_after_a_successful_sync` → `test_a_recurring_code_after_a_success_keeps_one_slot`
  (through `client.pr`: `NTP_NO_REPLY` twice, a success, `NTP_NO_REPLY` again, `NTP_UNSYNC_REPLY` twice: `ErrCount ==
  5`, the last ring slots `[NTP_NO_REPLY, NTP_UNSYNC_REPLY]` by code). New
  `test_the_sync_task_survives_a_cancel_at_every_await` (`cancel_at_each_await()` from `tests/_cancel_sweep.py` over
  `_sync_loop()` with a fake attempt gated per await: afterwards `wifi_mode_lock` unlocked and no fake socket left open).
- **Resolved**: A.U3.02's central newest-entry rule supersedes the per-episode masks: "persisted afresh after a success"
  is retired by OR35.b (the newest entry decides), guarded by the `ErrCount` assertions.
- **Unit**: U18 (stages U3 rule, U5 timing, U10 names/setup, U35 sweep).
- **Depends**: M.SRC_NET.056; TEST_HELP `tests/_cancel_sweep.py` (A.U35.48).
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.111 Real-network integration: the port redirect, a bool `serve_once()`, no wall-clock caps
- **From**: A.U27.30 (`:2043`, `:2047` `# ===` rules → `# ---`), A.U18.11 (`_RedirectNtpNetworking` `:2050-2084` →
  `redirect_udp_port()`; `:2518` uses the literal 123), A.U18.12/A.U18.13 (`_Resolving` goes), A.U24.49 + A.U24.76
  (`FakeNtpServer` `:2087-2121` → the shared class), A.U35.15 (`wait_for(…, 5)` wrappers go; `serve_once()` asserted
  `True`), A.U8C.13/A.U8C2.03 (`:2140, 2190, 2228, 2242, 2487, 2519` serve waits withdrawn; `:2144, 2219, 2237` state poll
  ms; `:2167`; `:2191`; `:2141`, `:2216`, `:2234` poll tries; `:2475`, `:2488` fetch timeouts), A.U3.02 (`:2495-2505`),
  A.U2.15 (`:2505` 21), A.U18.21 (`:2225-2240` re-read), A.U10.44/A.U10.35.
- **Site**: `tests/test_asy_ntp_client.py:2043-2255`, `:2471-2524`.
- **Change**: banner → "# ----" rules, text "# Integration: the real network path through the whole _sync_loop() task -
  cfgmgr, the resolver, UDPSocket, a real loopback NTP server - up to the public getters." `_RedirectNtpNetworking`
  goes: each test runs inside `with redirect_udp_port(asy_ntp_client, 123, server.port):` with `server =
  FakeNtpServer(_PORTS.next())` (the shared class). Every `await asyncio.wait_for(server_task, 5)`/`…(served, 5)` →
  `assert await server.serve_once(reply) is True` (concurrently with the client where the test needs it, as a task
  awaited and asserted); the serve-wait tag rows are withdrawn. Module constants with tags: `_STATE_POLL_MS = 20`
  (`l1.asy_ntp_client_state_poll_ms`), `_SYNCED_POLL_TRIES = 50`, `_STATE_POLL_TRIES = 200`, `_RETRY_ARMED_POLL_TRIES =
  300`, `_NO_ANSWER_WAIT_S = 1`, `_REPLY_PROCESS_S = 0.2`, `_NO_REPLY_FETCH_TIMEOUT_MS = 100`, `_PAST_FETCH_TIMEOUT_MS =
  200`, each `# @tunable l1.asy_ntp_client_<…> = <v>` as A.U8C.13/A.U8C2.03 name them. `:2167` comment → "# longer than
  one failed attempt against a closed loopback port" (`_NTP_CONN_TIMEOUT` is gone). The recovery test re-reads its
  `Synced` waits after A.U18.21: `ntp_force_sync()` clears `Synced`, so `_wait_synced(target=True)` after the retry is
  the meaningful check (holds). The self-heal test: `client._ntp_fetch_timeout_ms = _NO_REPLY_FETCH_TIMEOUT_MS` (private after M.SRC_NET.050 as
  amended in gap pass G2); the
  `_episode_errs` element of its return goes; `ErrCount == 3` and one `code("E", "NTP_NO_REPLY")` slot. The last test
  fetches `("127.0.0.1", 123)` under the redirect ("# 123 is a const() in the product, not a module attribute; the
  redirect maps it").
- **Resolved**: A.U8C.13's `l1.asy_ntp_client_serve_wait_s` tags vs A.U35.15: the literals go, so do the tags (A.U35.15
  says so).
- **Unit**: U18 (stages U24 shared server, U27 rules, U35 caps).
- **Depends**: M.SRC_NET.048, .056; TEST_HELP `_ntp_frames.FakeNtpServer` with `serve_once() -> bool` (A.U35.15, see
  "Gaps"), `_udp_port_redirect.py`.
- **Blast carried by**: Part N rows withdrawn → A.U35.15 (SPEC); `tests_scripts/test_comment_block_cap.py` `_DIVIDER` →
  A.U27.30 (TSC).
- **Kind**: test

### M.TEST_UNIT.112 Schema accessor and PUTs: source oracle, the shape override, `write_config(data)`
- **From**: A.U24.61 (`:2261`, `:2296` → the source-read schema), A.U10.39 (`:2258-2259` comment), A.U24.01 (the oracle),
  A.U11.24 (`:2305` `write_config(data)`), A.U10.40 (keys), A.U18.10 + A.U10.41 (new PUT-reject L1 through the override),
  M.SRC_NET.045 (the persist-only claim is no longer whole).
- **Site**: `tests/test_asy_ntp_client.py:2257-2311`.
- **Change**: `test_get_cfg_schema_matches_the_public_attribute` and `test_cfg_schema_matches_what_cfgmgr_was_built_with`
  merge into `test_get_cfg_schema_is_the_schema_in_source` (`client.get_cfg_schema() == _SCHEMA`; the `cfg_schema`
  comparisons and the "stays a public attribute" comments go). `test_set_dict_cfg_works_out_of_the_box_with_zero_driver_changes`
  → `test_set_dict_cfg_persists_plain_fields_through_the_base_path` with comment "# Fields other than NTPHost and
  DNSFallback persist through SensorReaderConfig's generic path; nothing is pushed live." and keys `NTPHost`/
  `NTPInterval`. The invalid-field test uses `NTPInterval`. `test_write_config_via_public_cfg_schema…` →
  `test_write_config_round_trips_a_real_value` (`write_config({"NTPHost": "time.example.org"})`; its comment names the
  REST path, not `api_helpers.py`). `test_no_push_callbacks…` holds. New (A.U18.10/A.U10.41):
  `test_a_put_of_a_malformed_dns_fallback_is_invalid_and_stores_nothing` (`"8.8.8.8,"`, `"8.8.8.8 ,1.1.1.1"`, four
  addresses, `"x"`: each `"Invalid"`, the stored value unchanged, one `code("E", "BAD_ARG")` each),
  `test_a_put_of_an_ntp_host_that_is_not_a_host_name_is_invalid` (`"-a.b"`, a 64-character label: `"Invalid"`), and
  `test_a_put_of_a_valid_host_or_ipv4_list_is_valid` (`"pool.ntp.org"`, `"192.168.1.1"`; `""`, three addresses).
- **Resolved**: —
- **Unit**: U18 (stages U10 keys, U11 signature, U24 oracle).
- **Depends**: M.SRC_NET.043, .045; M.SRC_CORE.044.
- **Blast carried by**: the shared `hostName`/`ipv4List` corpus → A.U18.10/A.U10.41 (TEST_HELP, WEB).
- **Kind**: test

### M.TEST_UNIT.113 Failure sites under the central slot rule
- **From**: A.U3.02 (`:2314-2420` rewritten to the central rule), A.U2.15 (codes 11 → console, 12 → `NTP_DNS`, 13 → gone,
  14 → `NTP_IMPLAUSIBLE`, 15 → `NTP_MALFORMED`, 21 → `NTP_NO_REPLY`, w2 → `NTP_UNSYNC_REPLY`), A.U3.05 (`:2340-2347`
  breaks the real store), M.SRC_NET.048 (`:2360-2362` goes), A.U28.28 (1) (`:2336` B905 noqa), A.U5.10 (`:2321`
  constructor), A.U8C.13 (`:2366`), A.U10.10 (`_twice_one_slot`'s `pr.setup()`); A.U3.05's print-only half dropped (OR140.a
  (7): the NTP log keeps its own entry; A-C review fold).
- **Site**: `tests/test_asy_ntp_client.py:2314-2436`.
- **Change**: section comment → "# Part C.7.2: never give up, back off while unsynced, one ring slot per repeated code
  (the central newest-entry rule)". `test_backoff_defaults_are_ten_seconds_doubling_to_ten_minutes` builds
  `NTPClient(asyncio.Lock(), _net_ok, _no_dns, NtpTiming(_DNS_TIMEOUT_MS, _DNS_TRIES, _FETCH_TIMEOUT_MS, _RETRY_S,
  _RETRY_MAX_S), cfg_path=…)` and expects `(_RETRY_S, _RETRY_MAX_S, _RETRY_S, 0)` (the source values 10/600).
  `_twice_one_slot()` drops its `pr.setup()` and its `noqa` (the per-file B905 entry carries the reason).
  `test_missing_config_failure_is_counted_twice_but_persisted_once` → `…logs_in_both_layers_one_slot_each`: the real
  store broken (`_make_invalid_cfg_client()`); the NTP log holds its own config-read code (HEAD's 11, by the catalog name
  the fold gives it back) in one slot, `ErrCount` counting both attempts, and `CFGMGR_NTP` holds one `code("E",
  "CFG_NOT_VALID")` slot with `ErrCount == 4` (the attempt reads the store twice, M.SRC_NET.046). The DNS, no-reply, implausible, malformed and unsync tests expect `(2, [code("E", "NTP_DNS")],
  ["E"])`, `(2, [NTP_NO_REPLY], ["E"])`, `(2, [NTP_IMPLAUSIBLE], …)`, `(2, [NTP_MALFORMED], …)`, `(2,
  [code("W", "NTP_UNSYNC_REPLY")], ["W"])`; `# @tunable l1.asy_ntp_client_no_reply_fetch_timeout_ms = 100` on the
  no-reply timing. `test_invalid_server_address_is_counted_twice_but_persisted_once` is removed with the construction
  guard. `test_the_same_number_as_error_and_as_warning_are_separate_episode_codes` →
  `test_an_error_and_a_warning_with_the_same_number_are_different_codes` (through `client.pr.err_s(…, errno=n)` and
  `wrn_s(…, wrnno=n)`: two slots, types `["E", "W"]`). `test_every_distinct_failure_code_keeps_its_own_slot_within_one_episode`
  → `test_distinct_codes_each_keep_a_slot` over the six live NTP codes through `client.pr`. The backoff-restart test
  holds.
- **Resolved**: the test's goal — a repeated failure is counted, not re-persisted — holds in both layers under the
  newest-entry rule; A.U3.05's console move (M.SRC_NET.050) is dropped by OR140.a (7), and A.U2.15's "11 → console"
  with it.
- **Unit**: U3 (stages U2 codes, U5 constructor, U18 removal and keys).
- **Depends**: M.SRC_NET.046-.050 (.050 as the fold reverts A.U3.05); M.SRC_CORE (`_get_values()` codes, newest-entry
  rule); [fold F11 M_GEN] (the restored NTP code's name).
- **Blast carried by**: `pyproject.toml` B905 entry → A.U28.28 (TOOL).
- **Kind**: test

### M.TEST_UNIT.342 The NTP client against the twin's local responder: function, failures, staleness, recovery
- **From**: OR140.a (13) (new NTP-client unit tests use the twin's local NTP responder: function, error handling, the
  biting cases and regressions), FOLD_ANSWERS `ntp-synced-goes-stale` (status ok) and `twin-tolerates-ntp-offline`
  (owner, 2026-10-02) — A-C review fold.
- **Site**: new section at the end of `tests/test_asy_ntp_client.py`.
- **Change**: banner "# ---- The client against the twin's local NTP responder (digital_twin/unixport/_ntp_responder.py):
  a real UDP round trip on loopback per attempt ----". `from _ntp_responder import NtpResponder` (the directory already on
  the file's path for the UDP shim). Each test builds a real `NTPClient` through the file's builder with `NTPHost`
  `"127.0.0.1"` and an empty `DNSFallback`, starts `NtpResponder(_PORTS.next())`'s `serve()` beside the client in one
  coroutine under `with redirect_udp_port(asy_ntp_client, 123, responder_port):` (M.TEST_HELP.066), and closes both in
  `finally`. Function: `test_a_sync_against_the_responder_sets_the_rtc_and_synced` — one forced sync: `Synced` true,
  `LastSyncAge` 0, the RTC fake's time within 2 s of the served time; `test_the_servers_offset_moves_the_set_time` —
  `offset_s = 3600`: the set time moves by 3600 s (± 1 s). Error handling, one test per failure mode, each run twice: `"silent"`
  → `code("E", "NTP_NO_REPLY")` in one slot, `ErrCount` 2, the retry interval doubling from `_RETRY_S` toward
  `_RETRY_MAX_S` (`src_const`); `"unsync"` → `code("W", "NTP_UNSYNC_REPLY")`; `"short"` → `code("E", "NTP_MALFORMED")`;
  `"implausible"` → `code("E", "NTP_IMPLAUSIBLE")`. Biting: every failure test also asserts what a sync would have changed
  stays unchanged — the RTC fake untouched, `Synced` false, `LastSyncAge` not reset — so a client that ignored the
  failure fails the test; and the function test first asserts `Synced` false with the responder `"silent"`, so a client
  syncing without a reply fails it. Regressions: `test_a_failed_resync_never_resets_the_staleness_count` (synced, then
  the responder silent for more than the stale threshold's intervals, driven by the file's fake time: `Synced` turns
  false, no failed attempt reset the count — the owner-reviewed `ntp-synced-goes-stale` rule); `test_a_responder_back_
  mid_backoff_syncs_at_the_next_attempt` (silent, two failed attempts, then `"serve"`: synced on the next attempt, the
  backoff back at `_RETRY_S`). Tunables tagged per the file's convention (`l1.asy_ntp_client_responder_wait_ms`, row
  basis U8's N.1 rule).
- **Resolved**: the file's `FakeNtpServer` cases (M.TEST_UNIT.111) stay: they script single replies byte for byte;
  these exercise the client against the same responder a booted twin syncs with (M.TWIN.167/.168), their reply builder
  one implementation with `make_ntp_reply()` (M.TEST_HELP.058).
- **Unit**: U25 (after M.TWIN.167, same unit).
- **Depends**: M.TWIN.167; M.TEST_HELP.044, .056, .058, .066; M.SRC_NET.046-.050 (the client's codes, backoff and
  staleness).
- **Blast carried by**: Part N row → SPEC (U8's rule); the port band row for this file's responder ports →
  M.TEST_HELP.056.
- **Kind**: test

## tests/test_asy_scd30_driver.py

### M.TEST_UNIT.114 Header, builders and shared doubles: a config reader built with `setup()`
- **From**: A.U10.37 (`config_manager`, `crc_checks`, `print_log` modules), A.U24.08 (`run`), A.U24.20 (`make_i2c()`
  `:40`), A.U15.12 + A.U5.02 + A.U10.43 (`make_reader()` `:54-55`: `trigger_s`, `cfg_path` in a scratch dir, the boot
  `setup()`), A.U10.35 (`reader.scd.i2c_scd30` `:59`), A.U24.49 + A.U31.09 + A.U8.07 (`_FastAsyncSleep` `:91-105`,
  `_RaiseOnArm` `:108-122` → shared; the comment names the constant), A.U15.28 (`:37` comment), A.U24.73 (`Any`),
  A.U24.76 (role names).
- **Site**: `tests/test_asy_scd30_driver.py:1-123`.
- **Change**: imports `import asy_config_manager as cm`, `from asy_crc_checks import CRC8`, `from _async_harness import
  run`, `from _fast_sleep import FastAsyncSleep`, `from _fake_timer_arm import RaiseOnArm`, `from _tmp_scratch import
  TmpScratch`, `from _error_codes import code`, `from asy_base_classes import set_utc_valid`; TYPE_CHECKING imports
  `asy_print_log.ErrorLog` and drops `Any`/`TypeVar`/`T`. `_ADDR = 0x61  # Interface Description 1.1.1: the address is
  fixed` (a datasheet copy). `make_i2c()` → `_make_i2c()` with `machine.I2C.reset_id(0)` first; `make_scd()` →
  `_make_scd()`; `make_reader(trigger_sec=3, …)` → `_make_reader(trigger_s: int = 3, max_module_error: int = 5)`:
  `SCD30_Reader(_make_i2c(), irq_pin=5, trigger_s=trigger_s, max_module_error=max_module_error,
  cfg_path=_scratch.dir())` then `run(reader.setup())` (`_scratch = TmpScratch("scd30")`); `reader_fake_i2c()` →
  `_reader_fake_i2c()` reading `reader._scd._i2c_scd30.i2c_device.i2c._i2c`. `crc8_byte()`, `register_frame()`,
  `data_frame()`, `_settle()` stay (the `run()` inside `crc8_byte()` is called only from synchronous scope, as the
  `:908-910` comment states). The local `_FastAsyncSleep` (its comment naming "real 0.05s") and `_RaiseOnArm` go; uses
  read `FastAsyncSleep()` (both sleeps) and `RaiseOnArm(exc)`.
- **Resolved**: —
- **Unit**: U15 (stages U5/U10 constructor, U24 harness, U31 `sleep_ms`).
- **Depends**: M.SRC_SENS.052; TEST_HELP `_fast_sleep.py`, `_fake_timer_arm.py`, `machine.I2C.reset_id`.
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.115 Wire format and setter ranges: rounded offsets, the whole two-decimal range
- **From**: A.U4.05 (offset words; new 0.29 L1), A.U15.07 (new exhaustive L1 after `:331-340`), A.U28.35 (read: `:127`
  names a datasheet path, opens nothing), A.U15.01 (read: setter ranges unchanged).
- **Site**: `tests/test_asy_scd30_driver.py:125-375`.
- **Change**: the wire-format and range tests hold (5.0 °C sends 500 under rounding as under truncation). New
  `test_temperature_offset_rounds_to_the_nearest_tick` (`set_temperature_offset(0.29)` sends word 29: the double
  `28.999999999999996` truncated to 28). New `test_every_two_decimal_temperature_offset_is_sent_as_typed` (A.U15.07: `n`
  over `range(0, 65536)`, `value = n / 100`, a `FakeI2C` keeping only the last frame, the argument word equals `n`; the
  three-line comment of A.U15.07; if the run exceeds the per-file budget at execution, the loop covers 0.00-20.00 plus
  every 1.00 step to 655.00 and the comment says so).
- **Resolved**: A.U4.05 (the 0.29 case, U4) and A.U15.07 (the exhaustive proof, U15) both stand: the named case lands
  first and stays as the readable instance of the rule.
- **Unit**: U4 (0.29), U15 (exhaustive).
- **Depends**: M.SRC_SENS.050 (`_temp_offset_ticks()`), .057.
- **Blast carried by**: hardware TempOffs 0.53 read-back → A.U15.07 (HW_DEV, gated by `persistence_write`).
- **Kind**: test

### M.TEST_UNIT.116 Measurement reads: the range gate, an independent decode, the not-ready rule, bus down
- **From**: A.U2.11 (`:451` 11 → `READ`), A.U15.01 (new range-gate L1), A.U30.05 (new decode L1; `:172-186`, `:397-` hold),
  A.U13.09 (new bus-down L1), A.U0.28 + A.U15.22 (`:454-457` comment), M.SRC_SENS.055/.057 (`read_measurement() -> bool`;
  `_read_scd()` returns the results with `new_data` beside them), A.U10.06 (the results' `TS`).
- **Site**: `tests/test_asy_scd30_driver.py:377-521`.
- **Change**: the not-ready tests also assert `run(scd.read_measurement()) is False`; the ready ones `is True`.
  `test_reader_turns_a_non_finite_measurement_into_a_logged_failed_read…`: `results, _new_data = await
  reader._read_scd()`, `results[:3] == (None, None, None)`, newest entry `code("E", "READ")`. `:454-457` → "# Matches
  the legacy driver's proven behaviour: a not-ready read neither raises nor clears the cache (owner, 2026-07-22,
  `110f3db`; SPECIFICATION.md A.4)." New (A.U15.01): `test_read_measurement_accepts_each_range_boundary_and_rejects_just_outside`
  (0/40000 ppm, −40/70 °C, 0/100 %RH accepted; one value just outside each raises `ValueError` "outside measurement
  range", cache untouched); `test_the_reader_logs_an_out_of_range_frame_as_a_failed_read_and_stores_nothing`;
  `test_the_temperature_gate_applies_the_cached_offset` (`scd._temp_offset_ticks = 1000`: −45 °C accepted, −51 °C
  rejected). New (A.U30.05): `test_read_measurement_decodes_every_word_like_struct_unpack` (0.0, 400.0, −12.5, 1e-3, a
  subnormal and the datasheet example, each word compared with `struct.unpack(">f", …)` in the test). New (A.U13.09):
  `test_a_deinitialised_bus_fails_the_read_without_checking_a_stale_buffer` (a valid frame left in `scd._buffer`, the
  asy bus deinitialised: `read_measurement()` raises `OSError` and the cache is unchanged).
- **Resolved**: A.U0.28 (tag the "per project-owner direction" phrase) and A.U15.22 (rewrite the comment, dropping its
  dangling BACKLOG pointer) on one comment: A.U15.22's text carries A.U0.28's tag.
- **Unit**: U15 (stages U2 code, U13 bus-down, U30 decode).
- **Depends**: M.SRC_SENS.055, .057.
- **Blast carried by**: twin chip stays in range → A.U15.01 (TWIN); release note D4.62 → A.U15.01 (DOCS, U37).
- **Kind**: test

### M.TEST_UNIT.117 Bus faults and `setup()`: the offset read joins the sequence
- **From**: A.U15.01 (`setup()` gains one register read: `:613-621`), A.U24.78 (`:596`).
- **Site**: `tests/test_asy_scd30_driver.py:523-634`.
- **Change**: `test_setup_probes_reads_firmware_version_then_soft_resets` →
  `…then_soft_resets_and_reads_the_temperature_offset`: queues a second `register_frame(450)`; ops `["writeto",
  "writeto", "readfrom_into", "writeto", "writeto", "readfrom_into"]`, the fifth write `bytes([0x54, 0x03])`, and
  `scd._temp_offset_ticks == 450`. `:596` → `inject_fault("readfrom_into", OSError, 5, "read half failed")`.
- **Resolved**: —
- **Unit**: U15 (stage U24 inject form).
- **Depends**: M.SRC_SENS.057.
- **Blast carried by**: scripted `setup()` queues elsewhere gain the frame → A.U15.01 (TEST_HELP `_bus_hazard_catalog.py`).
- **Kind**: test

### M.TEST_UNIT.118 Reader timers, starters and the stuck-pin task
- **From**: A.U27.30 (`:636`, `:639` `# ===` → `# ---`), A.U10.35 (`irq_pin`, `start_trigger_timer`, `base_trigger_event`,
  `read_event` → private), A.U10.43 (`trigger_sec`/`trigger_half_sec` → `trigger_s`/`_trigger_half_ticks`), A.U10.44
  (`scd_init_irq()` → `_irq_loop()`, `start_asy_init` → `start_asy_irq`), A.U24.07 (`all_timers.clear()` lines), A.U8C.14
  (`:652` `scd30.start_trigger_period_ms`, `:660, 661, 689, 745` `l1.asy_scd30_driver_event_wait_s`), A.U10.12 (`:670`
  comment), A.U15.41 (`:668-702` hold; `:677-679` comment; new arm L1), A.U15.03 (`:726-786` hold; two new L1), A.U24.49.
- **Site**: `tests/test_asy_scd30_driver.py:636-783`.
- **Change**: banner rules `# ---`, text "# Integration: SCD30_Reader on the real asy_i2c_driver, asy_base_classes and
  asy_print_log - only the raw I2C bus is a fake." Private names throughout; the `FakeTimer.all_timers.clear()` lines
  go. Module constants `# @tunable scd30.start_trigger_period_ms = 500` / `_START_TRIGGER_PERIOD_MS = 500` (`period ==
  _START_TRIGGER_PERIOD_MS`) and `# @tunable l1.asy_scd30_driver_event_wait_s = 1` / `_EVENT_WAIT_S = 1`. `:668-670` →
  "# Real rp2 Timer.init() raises OSError(ENOMEM) when the alarm pool is exhausted (ports/rp2/machine_timer.c);
  start_timer() runs inside SystemService's timer start and must not raise into it." `:677-679` → "# start_timer() is
  synchronous and persists nothing itself; the waiting _irq_loop() records the TIMER error and ends (see the test
  below)." — the `ErrCount == 0` assertion holds; the two degrade tests add `reader._base_trigger_event.state` set (the
  waiter woken). `test_reader_get_task_starters_and_timer_starters_shape`: `[reader.start_asy_read,
  reader.start_asy_irq]`, `[reader.start_timer]`, `reader.get_trigger_starters() == []`. The two stuck-pin tests start
  `reader._irq_loop()` with `trigger_s=` and end through `cancel(task)`. New (A.U15.41)
  `test_a_failed_trigger_arm_ends_the_irq_task_with_one_timer_entry_and_a_restart_rearms` (`OSError(ENOMEM)` and
  `MemoryError`). New (A.U15.03) `test_the_stuck_pin_count_saturates_at_the_threshold` (pin high for `3 ×
  _trigger_half_ticks` ticks, nothing consuming: `_scd_timer_triggers == _trigger_half_ticks`, `_read_event` set) and
  `test_stuck_pin_ticks_accumulate_across_a_low_gap` (high 2, low 10, high 4 with threshold 6: fires).
- **Resolved**: —
- **Unit**: U15 (stages U8 tags, U10 names, U24 hook, U27 rules).
- **Depends**: M.SRC_SENS.055; M.SRC_CORE.037 (`_timer_failed`/`_timer_fault`).
- **Blast carried by**: SPEC C.9.1 "counts ticks with the pin high since the last read" → A.U15.03 (SPEC).
- **Kind**: test

### M.TEST_UNIT.119 Reader getters and setters: catalog classes
- **From**: A.U2.11 (`:845` 14/16/18/20/22/24, `:863` 15/17/19/21/23/25, `:947` 13), A.U3.01 (one slot per repeated
  code), A.U24.73 (`tuple[Any, ...]`).
- **Site**: `tests/test_asy_scd30_driver.py:785-948`.
- **Change**: `test_reader_getters_log_the_correct_errno_on_bus_nak` → `…log_chip_get_on_bus_nak`: `ErrCount == 6`, one
  `code("E", "CHIP_GET")` slot; its `:827-829` comment → "# Every forward logs its failure (SPECIFICATION.md C.7): one
  CHIP_GET class for all six; the console line names the field." The setter twin → `ErrCount == 6`, one `CHIP_SET`
  slot. `:947` → `code("E", "CHIP_SET")`. `tuple[Any, ...]` → `tuple[object, ...]`. The rest holds.
- **Resolved**: the per-forward distinct numbers are retired by the class catalog (A.U2.01); the per-forward claim "every
  forward logs" holds through `ErrCount` (OR111.a (2)).
- **Unit**: U2 (stage U3 slot rule).
- **Depends**: M.SRC_SENS.056.
- **Blast carried by**: `tests/test_setter_microdot_integration.py:734, 858-864` → M.TEST_UNIT in that file (A.U2.11).
- **Kind**: test

### M.TEST_UNIT.120 The config PUT path: snapshot first, fixed order, compare-before-write
- **From**: A.U4.04 (`:950-1085` queue the snapshot; `:1078-1090` fixed order; new (a)-(f)), A.U10.40 (`TempOffs` →
  `TempOffset`, `MeasInt` → `MeasInterval`), A.U15.09 (new ContMeas L1), A.U15.12 (FRC keys go to the file store),
  A.U4.06 (`WriteCountingOpen`, `scd30_nvm_writes`).
- **Site**: `tests/test_asy_scd30_driver.py:950-1085`.
- **Change**: a helper `_queue_snapshot(i2c, temp_offset=0, interval=2, pressure=0, altitude=0, frc=400, asc=0)` queues
  the six register frames; every `_set_dict_cfg` test with a chip-side key (ContMeas included) calls it first. Keys
  `TempOffset`/`MeasInterval`. `test_set_dict_cfg_reports_contmeas_false_as_failed_on_bus_fault`: the snapshot itself
  fails → `"Failed"`, zero writes, one `code("E", "CHIP_GET")`. The spy tests keep their inline `method-assign` ignores
  (the write path calls the reader's `set_*` forwarders). `test_set_dict_cfg_multiple_fields_in_one_call…` asserts the
  writes in `_APPLY_ORDER` (TempOffset, then AmbPres, then SelfCal) from the fake log. The `:985-988` section comment →
  "# _set_dict_cfg through SCD30's chip store: snapshot, compare, validate, write in a fixed order (SPECIFICATION.md
  C.4.3)." New (A.U15.09): `test_contmeas_rejects_an_int_and_a_string` (`1`, `"false"`: `"Invalid"`, zero writes). New
  (A.U4.04): `test_a_repeated_put_of_a_stored_chip_value_is_unchanged_and_writes_nothing` (TempOffset, MeasInterval,
  Altitude, SelfCal; `scd30_nvm_writes == 0` on the second); `test_ambpres_and_forcecalref_always_write` ("Valid" and one
  write each time); `test_a_reversed_body_writes_in_the_fixed_order` and `test_ambpres_with_contmeas_false_ends_stopped_in_either_key_order`;
  `test_a_failing_snapshot_fails_every_key_and_writes_nothing` (one CHIP_GET entry); `test_tempoffset_compares_at_tick_resolution`
  (12.345 against a chip value of 1235: "Unchanged"); `test_get_dict_cfg_after_a_failing_snapshot_shows_none_and_one_entry`.
  New (A.U15.12 (g)): `test_frc_keys_stay_in_the_file_and_chip_keys_on_the_chip` (`WriteCountingOpen` +
  `scd30_nvm_writes`).
- **Resolved**: —
- **Unit**: U4 (stages U10 keys, U15 FRC routing and ContMeas).
- **Depends**: M.SRC_SENS.053; TEST_HELP `tests/_write_counters.py` (A.U4.06).
- **Blast carried by**: L2 identical-PUT NVM counter → A.U4.04 (TWIN); `tests/test_setter_microdot_integration.py:686-760`
  → M.TEST_UNIT in that file (A.U4.04).
- **Kind**: test

### M.TEST_UNIT.121 Config GET and the measurement body: nine keys, eight fields
- **From**: A.U15.12 (nine-key schema and `get_dict_cfg()`; eight-field `SCD30`), A.U10.40 (keys), A.U10.37 (`cm`),
  A.U4.04 (`:1124-1136` bus fault: one CHIP_GET entry), A.U10.35 (`reader.scd`), A.U24.49 (`_FastAsyncSleep`), A.U24.73.
- **Site**: `tests/test_asy_scd30_driver.py:1087-1194`.
- **Change**: `test_get_dict_cfg_reports_every_schema_field_by_name` uses the new keys and also expects `FRCNoise` 20.0,
  `FRCRate` 10.0, `FRCWindow` 60 (file defaults). `test_get_cfg_schema_returns_every_settable_field_by_name`: the nine
  names; its `:1113-1118` comment → "# _put_sensors() calls get_cfg_schema() on every sensor; SCD30's covers six chip keys
  and three file keys." The bus-fault test expects the six chip keys `None`, the three FRC defaults, and one
  `code("E", "CHIP_GET")`. The atomic-snapshot test writes through `reader._scd.set_temperature_offset(9.99)` under
  `FastAsyncSleep()`; its `:1140-1146` comment block → three lines ("# get_config_snapshot() holds the device session for
  all six reads: a concurrent offset write lands only after them (two log entries per register)."). The data test
  builds `SCD30(400.0, 20.0, 50.0, 15.2, 9.3, 1, 0, 123456)` and also reads `FRCState`/`FRCWait`.
- **Resolved**: —
- **Unit**: U15 (stages U4 snapshot, U10 keys).
- **Depends**: M.SRC_SENS.051-.053.
- **Blast carried by**: `tests/test_digital_twin_scd30.py` key set → A.U15.12 (TWIN).
- **Kind**: test

### M.TEST_UNIT.122 Init, the read loop and the ladder; FRC readiness; the staleness rules
- **From**: A.U10.44 (`read_loop()` → `_read_loop()`), A.U15.43 (returns `None`), A.U15.R01 + A.U10.R01 (`:1286-1331`
  re-derived; new rung L1), A.U2.06, A.U3.03 dropped (OR140.a (7): the streak keeps its entry; A-C review fold), A.U10.06 (`:1251` needs a sync), GAP-15 lead ruling
  (pre-sync L1), A.U15.22 (new last-sample and not-ready L1), A.U15.12 (new FRC L1 (a)-(f), (h), (i)), A.U10.35
  (`reader.scd`, `read_event`), M.SRC_SENS.057 (`read_measurement()` returns `bool`).
- **Site**: `tests/test_asy_scd30_driver.py:1196-1370`; new tests after `:1370`.
- **Change**: the section comment names `_read_loop()`; the fakes patch `reader._scd.setup`/`read_measurement`/getters
  (inline ignores kept) and the read fake returns `True` (new data). `test_init_scd_returns_false_immediately_when_probe_fails…`
  adds: one `code("E", "INIT")` and one `code("W", "BUS_RECOVERY")` (`_init_failed()`'s controller rung). The full-iteration
  test calls `set_utc_valid()` first (flag reset by the hook) for `data.TS is not None`. The give-up test
  (`max_module_error=1`) drives `_read_loop()`, asserts the task returned `None`, and the ring holds `code("E", "READ")`,
  the streak's own entry per failed cycle (by its catalog name) and then `code("E", "GIVE_UP")`, `ErrCount` re-derived
  from those entries (the rung never runs below its threshold). The recovery test
  (`max_module_error=5`, two failures then a good read) stubs `reader._scd.reset` (else a real 2.5 s wait) and asserts
  one call and one `code("W", "DEVICE_RECOVERY")`, and the third read stored. `test_read_loop_returns_false_when_init_fails`
  → `…ends_when_init_fails` (`None`). The two starter tests call `start_asy_read()`/`start_asy_irq()` and end through
  `cancel()`. New (A.U15.R01): `test_a_raising_reset_logs_one_chip_set_and_no_recovery_warning`,
  `test_the_third_failure_clears_the_bus_and_the_fourth_reinitialises_the_controller` (one `recoveries` step and one
  `BUS_RECOVERY` each), `test_a_held_boot_bus_is_reported_once_at_setup`, `test_a_put_during_the_recovery_completes_after_it`.
  New (GAP-15): `test_a_read_before_the_first_sync_steps_no_streak_and_publishes_ts_none`. New (A.U15.22):
  `test_a_failed_read_keeps_the_last_good_sample_and_its_timestamp` (synced) and
  `test_a_not_ready_cycle_republishes_the_cached_reading_with_a_fresh_ts_and_no_error`. New (A.U15.12): FRC readiness
  cases (a) a stream at interval 2 s reaches 4 after max(180, 5) samples plus one closed window with `FRCWait` falling to
  0; (b) slope, noise and a 10 °C step give 2/3/2; (c) a 1.6-interval gap, a MeasInterval write and an AmbPres write
  reset to 1, `ContMeas=false` publishes 0 with the old `TS`; (d) 4 × interval idle ticks publish 0; (e) counters
  saturate at their targets when driven past them; (f) a `ForceCalRef` PUT in state 1 is `"Valid"` and written; (h) a
  `_store_scd()` interleaved into a republish (a `_get_meas_data` patched to yield) keeps the fresh sample; (i) after
  1,800 samples every stored sum is a `float` below 2**30.
- **Resolved**: A.U15.R01's "stubs `reader.scd.reset`" is written with A.U10.35's private name.
- **Unit**: U15 (stages U10 ladder/`TS`/names).
  A-C2 step order: A.U10.R01's part lands in U13, not U10 (it follows A.U10.R01's own change, which lands in U13).
- **Depends**: M.SRC_SENS.054, .055, .090; M.SRC_CORE.037 (as the fold reverts A.U3.03); SRC_CORE
  `SensorReader._republish()` (A.U15.12); [fold F11 M_GEN] (the streak's catalog entry).
- **Blast carried by**: the mid-operation reset across siblings → M.TEST_UNIT in `test_bus_hazard_multi_device.py`
  (A.U15.R01) and A.U15.R01 (TWIN, HW_DEV); notification `ErrCount`s → M.TEST_UNIT in the two SCD30 notification files.
- **Kind**: test

### M.TEST_UNIT.123 Success paths and the CRC-generation guard hold
- **From**: A.U10.45 (read: the message "CRC generation failed" without "!"; `in str(e)` holds), A.U24.62 (none here).
- **Site**: `tests/test_asy_scd30_driver.py:1372-1418`.
- **Change**: none beyond the builder; `_WrongLengthCRC.add_into(…)` keeps the `asy_crc_checks` signature (`start`
  named).
- **Resolved**: —
- **Unit**: U10.
- **Depends**: M.SRC_SENS.057.
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.124 Same-device hazards: wire copies renamed, a gated writer
- **From**: A.U24.01 (`:1433-1435` → `_WIRE_GET_DATA_READY` etc.), A.U35.12 (`:1482` → a gate), A.U24.73 (`_gather`
  typing), A.U15.01 (the sweep tolerates `setup()`'s extra read: holds), A.U24.49.
- **Site**: `tests/test_asy_scd30_driver.py:1420-1529`.
- **Change**: `_WIRE_GET_DATA_READY = b"\x02\x02"  # Interface Description 1.4.4`, `_WIRE_READ_MEASUREMENT = b"\x03\x00"
  # 1.4.5`, `_WIRE_SET_TEMPERATURE_OFFSET = b"\x54\x03"  # 1.4.7` and their uses in `_parse_scd30_log()`. The writer
  awaits an `asyncio.Event` the reader sets after its first `read_measurement()` returns, in place of the `:1482` yield.
  `FastAsyncSleep()`; `_gather(a, b)` typed `Coroutine[object, object, object]`.
- **Resolved**: —
- **Unit**: U24 (stage U35 gate).
- **Depends**: M.SRC_SENS.057.
- **Blast carried by**: `tests_scripts/test_const_mirrors.py` → A.U24.02 (TSC).
- **Kind**: test

## tests/test_asy_sgp40_driver.py

### M.TEST_UNIT.125 Builders, doubles and names follow the merged reader
- **From**: A.U5.11 (constructor with `ValueRef`/`SgpBackup`), A.U10.10 (`setup()` replaces `pr.setup()`/
  `cfgmgr.setup()`), A.U10.35 (private attribute names), A.U10.40 (`ResetVOC`), A.U15.19 (four-field `SGP40`),
  A.U24.20 (`:110` fresh bus), A.U24.49 (`_RaiseOnArm`, `_FastAsyncSleep` → shared helpers), A.U2.06 (catalog names),
  A.U15.40 (`_i2c_sgp40` session path), A.U30.06 (`sleep_ms` patches).
- **Site**: `tests/test_asy_sgp40_driver.py:1-131` (header, imports, `run`, `_last_err`, `make_i2c`, `bus`,
  `queue_successful_init`, `make_sgp`), `:343-375` (`_FakeCompSource`, `make_reader`), `:559-570` (`_RaiseOnArm`),
  `:1463-1477` (`_FastAsyncSleep`), `:1539-1576` (FRAM helpers) and every reader construction and attribute read in the
  file.
- **Change**: header docstring kept in substance and trimmed to ≤ 3 lines (the mocking boundary: raw I2C transactions
  only, the real `VOCAlgorithm` unmocked); the `:2-3` comment block kept. `from _async_harness import run` replaces the
  local `run`; `from _error_codes import code`; `make_i2c()` calls `machine.I2C.reset_id(1)` before `I2C(1, …)`.
  `bus(i2c)` reads `i2c._i2c` unchanged; every `reader.sgp.i2c_sgp40.i2c_device.i2c` chain → `reader._sgp._i2c_sgp40.
  i2c_device.i2c` (one helper `_fake_bus_of(reader)` carries it). `make_reader(**kwargs)` builds
  `SGP40_Reader(make_i2c(), ValueRef(_FakeCompSource(), "Temp"), ValueRef(_FakeCompSource(), "Hum"),
  max_module_error=2, cfg_path=…, **kwargs)` then `run(reader.setup())`; `_FakeCompSource`'s comment → "# Structural
  stand-in for a compensation producer (Part C.14, L.6.3): only get_data() is read, through each ValueRef's field." and
  `get_data() -> object`. Each direct `SGP40_Reader(…, temperature_source=…, temperature_field=…, humidity_source=…,
  humidity_field=…, fram_storage=…, fram_ntp_callback=…)` call → the positional `ValueRef` pair plus
  `backup=SgpBackup(<manager>, <ntp callback>)`; each `run(reader.cfgmgr.setup())`/`run(reader.pr.setup())` →
  `run(reader.setup())`. Attribute reads follow the private names: `_sgp`, `_read_event`, `_trigger_timer`,
  `_backup_counter`, `_voc_init`, `_voc_write`, `_ts_storage`, `_last_backup`, `_restored_from`, `_reset_pending`
  (was `reset`), `_reset_fram_cleared`, `_reset_algo_applied`. Every `SGP40(a, b, c)` tuple gains `VOCState` in third
  place (`SGP40(None, None, None, None)` for the empty result). `_RaiseOnArm` → `from _fake_timer_arm import
  RaiseOnArm`; `_FastAsyncSleep` → `from _fast_sleep import FastAsyncSleep` (patches `sleep` and `sleep_ms`); every
  bare errno/wrnno literal in an assertion → `code("E"|"W", NAME)`.
- **Resolved**: —
- **Unit**: U24 (stages U2 names, U5 constructor, U10 names/setup, U15 tuple/session).
- **Depends**: M.SRC_SENS.058, .060, .062, .067; M.TEST_HELP.043, .045, .052, .053; M.SRC_CORE.032 (`ValueRef` in
  `asy_base_classes`).
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.126 initialize(): identity messages, three-word serial, self-test effect
- **From**: A.U0.28 (`:129` comment), A.U10.45 (lowercase messages), A.U15.13 (serial reads 9 bytes, word-2 CRC
  raises, no `None` paths), A.U24.38 (`:167` self-test pass).
- **Site**: `tests/test_asy_sgp40_driver.py:128-212`.
- **Change**: section comment `:129` → "# initialize() - serial number / self-test gates (feature-set check removed: not in
  datasheet Table 8; owner-confirmed, 2026-07-21)". The message assertions follow the merged texts: `"serial number does
  not match" in str(e)`, `"self test failed" in str(e)`, `"CRC check failed while reading data" in str(e)`. New
  `test_the_serial_read_asks_for_nine_bytes` (the fake records `readinto` length 9 after the `0x3682` write);
  `test_a_crc_error_in_the_third_serial_word_raises` (word 2's CRC byte corrupted → `RuntimeError` with the CRC text, no
  self-test command written). `:167` (self-test `0xD4FF` passes) → `initialize()` returns `None` and the bus log's next
  exchange after the self-test read is the general call `0x06` to `0x00` (the reset only runs on a passed self-test).
- **Resolved**: A.U24.38 asks for "the reader's self-test status reads pass"; the merged protocol stores no self-test
  status (M.SRC_SENS.069), so the observable effect is asserted instead (agent decision D-T12, same reading as D-T3).
- **Unit**: U15 (stages U0 comment, U10 messages, U24 assertion).
- **Depends**: M.SRC_SENS.068, .069.
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.127 General-call reset: comment and exact bus log
- **From**: A.U15.15 (`:215`), A.U35.17 (`:219` unchanged), A.U24.38 (`:228`), A.U13.09 (`_reset()` raises on an
  uninitialised bus).
- **Site**: `tests/test_asy_sgp40_driver.py:215-232`.
- **Change**: `:215` → "# _reset() - one I2C general call, datasheet Table 17 (owner, 2026-09-26; SPECIFICATION.md C.8)"
  (dated per OR64.a (3), tag form AC_NOTES 6; A-C3 O-23). `:228` (general call NAKed) → the fake bus log holds exactly
  one write, `0x06` to `0x00`, and nothing else. New `test_reset_raises_when_the_bus_is_not_initialised` (the fake's
  `writeto` returning `None` → `OSError("I2C bus not initialized")`). The test at `:219` stays as written.
- **Resolved**: —
- **Unit**: U15 (stages U13, U24).
- **Depends**: M.SRC_SENS.069.
- **Blast carried by**: four-tier general-call hazards → A.U15.15 (TWIN, HW_DEV).
- **Kind**: test

### M.TEST_UNIT.128 Tick conversions clamp to Table 10
- **From**: A.U15.14 (`:240-262` hold; new clamp table).
- **Site**: `tests/test_asy_sgp40_driver.py:236-265`.
- **Change**: the Table 10 point and rounding tests hold. New `test_ticks_clamp_to_table_10_never_wrap`:
  `_celsius_to_ticks()` at −45.1, −45, 130, 131, 1e6 → 0x0000, 0x0000, 0xFFFF, 0xFFFF, 0xFFFF and
  `_relative_humidity_to_ticks()` at −1, 0, 100, 101 → 0x0000, 0x0000, 0xFFFF, 0xFFFF (expected values from datasheet
  Table 10, cited in the test's one comment line).
- **Resolved**: —
- **Unit**: U15.
- **Depends**: M.SRC_SENS.068.
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.129 Measurement paths: held behaviour, restored command, construction
- **From**: A.U12.18 (`:273-301` hold), A.U30.04 (`:329` holds; new construction L1), A.U15.13 (CRC failure restores
  the command buffer), A.U13.09 (bus-down read fails before any CRC), A.U30.06 (`sleep_ms` patches).
- **Site**: `tests/test_asy_sgp40_driver.py:269-335`.
- **Change**: the `measure_raw`/`get_raw`/`measure_index_and_raw` tests hold; any patch of `asyncio.sleep` used to skip
  the command wait patches `asyncio.sleep_ms` as well (through `FastAsyncSleep`). New
  `test_a_crc_failing_get_raw_restores_the_default_command` (a corrupted reply CRC → `RuntimeError`; a following
  `initialize()` writes `0x3682` then `0x280e`, never the measure command); `test_a_read_on_a_down_bus_fails_without_a_crc_check`
  (the fake's `readinto` reporting failure → `OSError("I2C bus not initialized")`, the stale reply buffer never
  CRC-checked); `test_the_voc_algorithm_exists_at_construction` (right after `SGP40_I2C(make_i2c())` the algorithm
  exists with `params.muptime == 0`; a second instance fed the same raw values from a fresh construction returns the
  same first index).
- **Resolved**: —
- **Unit**: U30 (stages U12 hold, U13, U15).
- **Depends**: M.SRC_SENS.067, .068.
- **Blast carried by**: four-tier race fix → A.U12.18 (TEST_UNIT `tests/test_bus_hazard_multi_device.py`, TWIN, HW_DEV).
- **Kind**: test

### M.TEST_UNIT.130 Compensation reads: references, checked values, the source code
- **From**: A.U5.11 (`ValueRef`), A.U15.14 (NaN/inf/`True` → READ before bus traffic; `:855-876` holds), A.U2.13
  (18 → 15 SOURCE, 11 READ), A.U10.06 (`TS`), GAP-15 (lead ruling, M.SRC_SENS.091), A.U15.19 (tuples).
- **Site**: `tests/test_asy_sgp40_driver.py:378-465`, `:799-880`.
- **Change**: the no-compensation tests build through the `ValueRef` pair and assert `SGP40(None, None, None, None),
  False, False`; their logs stay empty after `setup()`. `test_read_sgp_with_compensation_data_stores_a_result` sets the
  UTC flag (`asy_base_classes.set_utc_valid()`, reset in `finally`) before asserting `data.TS is not None`. The
  raising-source test (`:799-880`) asserts `code("E", "SOURCE")` (was 18); the non-numeric field test keeps its read
  failure, now `code("E", "READ")` from the finite check. New
  `test_a_nan_inf_or_bool_temperature_is_a_read_failure_without_bus_traffic` (`float("nan")`, `float("inf")`, `True` for
  `Temp`: one `code("E", "READ")` each, the fake bus log empty); `test_a_pre_sync_read_publishes_ts_none_and_steps_no_streak`
  (UTC flag unset: a successful read returns `TS is None` with `VOC`/`Raw` set, `_read_loop`'s condition
  `compensated and data[0] is None` is false, `_err_cnt_internal` stays 0, the stored data carries `TS` None).
- **Resolved**: —
- **Unit**: U15 (stages U2, U5, U10).
  A-C2 step order: A.U2.13's part lands in U3, not U2 (it follows A.U2.13's own change, which lands in U3).
- **Depends**: M.SRC_SENS.064, .091; M.SRC_CORE.032.
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.131 Store guard, storage checks and memory status
- **From**: A.U10.06 (store guard on values only), A.U15.17 (`:481-485` seed holds), A.U10.35.
- **Site**: `tests/test_asy_sgp40_driver.py:466-500`.
- **Change**: `test_store_sgp_ignores_partial_none_results` stores `SGP40(None, 100, 1, 12345)`; the complete case
  `SGP40(42, 31000, 2, 12345)`. New `test_store_sgp_accepts_a_result_without_a_timestamp` (`SGP40(42, 31000, 1, None)` is
  stored). The storage and memory-status tests read and seed `_voc_init`, `_voc_write`, `_last_backup`,
  `_restored_from`.
- **Resolved**: —
- **Unit**: U15 (stages U10).
- **Depends**: M.SRC_SENS.065, .066.
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.132 Streak tests follow the ladder; the heater-off rung
- **From**: A.U10.R01, A.U15.R02 (re-derive `:369-443`, `:505-510`, `:585-589`; new heater-off L1), A.U3.03 dropped
  (OR140.a (7): each streak step keeps its entry; A-C review fold), A.U2.06.
- **Site**: `tests/test_asy_sgp40_driver.py:502-512`, `:584-600`.
- **Change**: `test_get_error_counter_reflects_logged_errors` → three failed checks at `max_module_error=2`: the 2nd
  writes `0x36 0x15` to `0x59` once and logs one `code("W", "DEVICE_RECOVERY")`; the 3rd logs `code("E", "GIVE_UP")`;
  each streak step keeps its own entry (by its catalog name) as at HEAD, `ErrCount` re-derived from the ring's entries. The give-up and recover tests keep their return values; the recover test
  also asserts the heater-off write happened once. New `test_two_failed_cycles_turn_the_heater_off_once` (exactly one
  `0x36 0x15` write to `0x59`, no write to `0x00` beyond setup's, one `DEVICE_RECOVERY`, the VOC algorithm object
  identical before and after); `test_a_raising_heater_off_logs_one_chip_set_and_no_recovery_warning` (the write faults:
  one `code("E", "CHIP_SET")`, no `DEVICE_RECOVERY`, no raise).
- **Resolved**: —
- **Unit**: U15 (stages U2, U10).
  A-C2 step order: A.U10.R01's part lands in U13, not U10 (it follows A.U10.R01's own change, which lands in U13).
- **Depends**: M.SRC_CORE.037 (as the fold reverts A.U3.03); M.SRC_SENS.065, .069; [fold F11 M_GEN] (the streak's
  catalog entry).
- **Blast carried by**: twin/L3 heater-off tiers → A.U15.R02 (TWIN, HW_DEV); hazard sweep → M.TEST_UNIT for
  `tests/_bus_hazard_catalog.py` is TEST_HELP's (A.U15.R02).
- **Kind**: test

### M.TEST_UNIT.133 Timer, starters and the read event
- **From**: A.U8C.15 (`:539` tag), A.U10.12 (`:563` comment; `:1263-1266` starters), A.U15.41 (arm failure wakes the
  read task), A.U15.20 (two fires, one cycle), A.U24.49.
- **Site**: `tests/test_asy_sgp40_driver.py:534-581`, `:1263-1266`.
- **Change**: module level `# @tunable l1.asy_sgp40_driver_event_wait_s = 1` / `_EVENT_WAIT_S = 1`; `:539`'s literal →
  `_EVENT_WAIT_S`. `:562-564` comment → "# start_timer() runs as a trigger starter (get_trigger_starters()); a raise
  there would leave this sensor untriggered, so an arm failure degrades instead." The degrade test uses
  `RaiseOnArm()` and asserts one `code("E", "TIMER")` and that `_read_event` is set (the read task wakes and sees the
  fault). `:1263-1266` → `get_task_starters() == [reader.start_asy_read]`, `get_trigger_starters() ==
  [reader.start_timer]`, `get_timer_starters() == []`. New `test_two_trigger_fires_before_the_loop_waits_give_one_cycle`
  (two `_trigger_timer.trigger()` calls, one `_read_sgp` call recorded, `_backup_counter` stepped by one).
- **Resolved**: —
- **Unit**: U15 (stages U8C tag, U10 starters).
- **Depends**: M.SRC_SENS.066; M.TEST_HELP.053.
- **Blast carried by**: Part N row `l1.asy_sgp40_driver_event_wait_s` → A.U8C.15 (SPEC).
- **Kind**: test

### M.TEST_UNIT.134 reset_voc() and its push callback
- **From**: A.U10.40 (`ResetVOC`), A.U10.25 (push returns True for a well-typed no-op), A.U15.21 (`:631-637` goes).
- **Site**: `tests/test_asy_sgp40_driver.py:602-689`.
- **Change**: every `SGPResetVOC` key → `ResetVOC`; `reader.reset` → `reader._reset_pending`. The non-bool push test
  `:631-637` goes (the push guard is removed; the type check lives in the shared validation). New
  `test_push_reset_voc_reports_success_for_a_well_typed_no_op` (`_push_reset_voc(False)` returns `True` while
  `_reset_pending` stays `False`).
- **Resolved**: —
- **Unit**: U15 (stages U10).
- **Depends**: M.SRC_SENS.060, .066.
- **Blast carried by**: L0 setter contract → A.U10.25 (TSC).
- **Kind**: test

### M.TEST_UNIT.135 Reset sub-parts through references; the lost-reset regression
- **From**: A.U5.11 (`:691-796` direct `temperature_source` reassign), A.U3.09 dropped (OR140.a (7): the FRAM clear
  failure keeps SGP40's own entry; A-C review fold),
  A.U15.14 (lost-reset regression), A.U10.35.
- **Site**: `tests/test_asy_sgp40_driver.py:691-796`.
- **Change**: each `reader.temperature_source = …`/`humidity_source = …` reassignment → `reader._temperature =
  ValueRef(<source>, "Temp")`/`reader._humidity = ValueRef(<source>, "Hum")`; the sub-part flags read
  `_reset_fram_cleared`/`_reset_algo_applied`. A FRAM clear failure keeps the SGP40 log's own entry (HEAD's
  "Error clearing FRAM!", by the catalog name the fold gives it back) beside FRAM's. The
  `:770-776` mypy narrowing workaround and its comment go (the algorithm is no longer optional, A.U30.04). New
  `test_a_nan_cycle_keeps_a_pending_algorithm_reset` (`reset_voc(flag=True)`, a cycle with `Temp = nan` leaves
  `_reset_algo_applied` `False`, the next valid cycle applies the reset).
- **Resolved**: —
- **Unit**: U15 (stages U5, U30).
- **Depends**: M.SRC_SENS.062, .064, .067 (as the fold reverts A.U3.09); [fold F11 M_GEN] (the restored SGP40 code's name).
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.136 Backup writes: FRAM and SGP40 each log a failure, every untimestamped backup warns
- **From**: A.U3.09 (`:883-913`; new three cases) with its one-entry half dropped (OR140.a (7): SGP40 keeps its own
  entry beside FRAM's; A-C review fold), A.U3.02 (`:1068-1140`), A.U15.18 (`(0, 0)` memory status; `:966`
  comment), A.U16.18 (`:1055-1056` bool-first stub), A.U2.13 (13 → 35), A.U15.17 (`:916-961` holds).
- **Site**: `tests/test_asy_sgp40_driver.py:883-1128`.
- **Change**: `:883-913` → FRAM's log holds `code("W", "FRAM_PAUSED")` and SGP40's log its own backup-write entry
  (HEAD's 14, by the catalog name the fold gives it back). Escape-hatch tests
  hold with `_voc_init` seeding; `:966`'s "-1" sentinel comment → "# 0 = no timestamp (the special value)". `_w13_slots`
  → `_written_no_ts_slots` counting `code("W", "SGP_WRITTEN_NO_TS")`; each run of untimestamped backups spends one slot
  (identical repeats spend none) while `ErrCount` counts every backup; the "ends the episode" tests flip to one slot.
  `failing_write_into` stubs return `(False, False, -1)` → bool-first `(False, <ntp_synced>, <ts>)` order per the merged
  `write_into()` shape. New: `test_crc_invalid_backup_logs_in_fram_and_in_sgp40`,
  `test_a_paused_store_logs_in_fram_and_in_sgp40`, `test_a_failed_backup_write_logs_in_fram_and_in_sgp40` (each layer the
  failure reaches keeps one entry of its own, the history showing how far it reached);
  `test_an_untimestamped_backup_restores_to_memory_status_zero_zero` (`get_mem_status() == (0, 0)`).
- **Resolved**: —
- **Unit**: U16 (stages U2, U3 slot rule, U15).
  A-C2 step order: A.U2.13's part lands in U3, not U2 (it follows A.U2.13's own change, which lands in U3).
- **Depends**: M.SRC_SENS.063 (as the fold reverts A.U3.09); FRAM manager return shape (M.SRC_CORE, A.U16.18); [fold F11 M_GEN]
  (the restored SGP40 codes' names).
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.137 Backup counter and the verify-period table
- **From**: A.U15.17 (1) (`_verify_every()` table; `:1162-1184` holds), A.U8.13 (counter cap name).
- **Site**: `tests/test_asy_sgp40_driver.py:1131-1184`.
- **Change**: the wrap test reads the cap through `src_const("src/asy_sgp40_driver.py", "_BACKUP_COUNTER_MAX")`. New
  `test_verify_every_table` (`_verify_every(p)` at p = 1, 7, 32, 60, 66, 67, 1440 → 60, 8, 1, 1, 1, 1, 1, the expected
  values worked from the formula by hand with the `max(1, …)` floor).
- **Resolved**: —
- **Unit**: U15.
  A-C2: stage U24 — until M.TEST_HELP.044's `src_const()` exists the wrap test keeps a local mirror of the cap (the HEAD form); U24 swaps in `src_const()`.
- **Depends**: M.SRC_SENS.059, .063; M.TEST_HELP.044.
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.138 Restore paths: wait semantics, age bounds, one read per wait
- **From**: A.U15.17 (2)-(4) (WaitTimeNTP 0; −60 s age; one `read_into()` while waiting; first-boot blank chunk;
  blackout skip), A.U16.18 (negative age expired under a nonzero limit, limit 0 accepts any age), A.U10.28 (age signed),
  A.U10.06 (`_OldTime` → UTC flag), A.U30.04 (`:1601` comment), A.U11.24 (`write_config(data)`), A.U2.13 (11 → 33,
  12 → 34), A.U3.09 dropped (OR140.a (7): an unreadable backup keeps SGP40's own warning beside FRAM's entry; A-C
  review fold).
- **Site**: `tests/test_asy_sgp40_driver.py:1187-1250`, `:1579-1770`, `:2064-2225`.
- **Change**: `_OldTime` (monkeypatching `asy_fram_manager.time.mktime`) → the test drives the timestamp through
  `asy_base_classes.set_utc_valid()` and a fake `time` on `asy_base_classes` (reset in `finally`). `:1601` comment →
  "built at construction". Each `write_config({…}, schema)` → `write_config({…})`. Branch comments "wrnno=11"/"12" →
  the catalog names; asserts `code("W", "SGP_RESTORED_NO_TS")`/`code("W", "SGP_BACKUP_AGE")`; an unreadable backup
  (`read_into()` `None`) keeps SGP40's own no-backup warning (HEAD's w10, by the catalog name the fold gives it back)
  beside FRAM's entry, while a blank chunk (`False`, a first boot) logs nothing (A.U15.17). New: `test_wait_time_ntp_zero_restores_on_the_first_cycle` (timestamped backup, NTP never
  synced: restored on cycle one, `_restored_from` = the backup's TS); `test_a_backup_dated_in_the_future_is_refused_under_a_limit`
  (age −60 s, `BackupMaxAge` 120 → refused, one `SGP_BACKUP_AGE`); `test_a_zero_age_limit_accepts_a_future_dated_backup`
  (age −60 s, `BackupMaxAge` 0 → restored); `test_waiting_for_ntp_reads_the_chunk_once` (30 cycles unsynced: one
  `read_into()`; after `ntp_synced` turns True, one more); `test_a_first_boot_blank_chunk_logs_nothing` (SGP40's and FRAM's
  logs empty); `test_a_restore_after_the_blackout_gives_a_nonzero_index_at_once`.
- **Resolved**: M.SRC_SENS.063 writes A.U15.17 (3)'s `age < 0 or (limit > 0 and age > 60*limit)`, calling it "the same
  condition" as A.U16.18's; they differ at limit 0 with a negative age. A.U16.18 quotes the register text (G5/R31: "a
  staleness limit of 0 accepts any age; a negative age … counts as expired under a nonzero limit"), A.U15.17's own
  wording ("0 = no age limit") agrees; settled by the register — the tests pin A.U16.18's condition and the product
  fix is GAP-U1 (SRC_SENS) below.
- **Unit**: U16 (stages U2, U3, U10, U11, U15, U30).
  A-C2 step order: A.U2.13's part lands in U3, not U2 (it follows A.U2.13's own change, which lands in U3).
- **Depends**: M.SRC_SENS.063 (with the gap's condition; as the fold reverts A.U3.09); M.SRC_CORE.032;
  M.TEST_HELP.057; [fold F11 M_GEN] (the restored SGP40 code's name).
- **Blast carried by**: L2 twin backup cases → A.U15.17 (TWIN).
- **Kind**: test

### M.TEST_UNIT.139 VOCState: blackout, learning, settled, restored
- **From**: A.U15.19 (new L1 cases).
- **Site**: new tests in `tests/test_asy_sgp40_driver.py`.
- **Change**: `test_voc_state_is_zero_through_the_blackout_then_learning` (46 samples from a fresh algorithm: VOC 0,
  state 0; the 47th: state 1); `test_a_restored_state_reads_three_then_settles` (state 3 at once; with `_voc_samples`
  set one below `_VOC_SETTLED_SAMPLES` read via `src_const`, the next cycle reads 2); `test_reset_voc_returns_to_blackout`
  (after `reset_voc(flag=True)` the next samples read 0 then 1); `test_the_sample_counter_saturates_at_the_cap`
  (seeded at the cap, one more cycle leaves it there).
- **Resolved**: —
- **Unit**: U15.
- **Depends**: M.SRC_SENS.059, .064.
- **Blast carried by**: L2 `tests/test_digital_twin_sgp40.py` → A.U15.19 (TWIN).
- **Kind**: test

### M.TEST_UNIT.140 Config schema read from source; special slot 0
- **From**: A.U24.01 (`:1277-1283`), A.U24.61 (`:1289`), A.U15.17 (5) (special slot 0), A.U10.40, A.U15.17
  (`:1339-1343` holds), A.U11.24.
- **Site**: `tests/test_asy_sgp40_driver.py:1253-1455`.
- **Change**: the four mirrors and their comment → `_SGP = "src/asy_sgp40_driver.py"`; `_VAL_BP = src_const(_SGP,
  "_VAL_BACKUP_PERIOD")`, `_VAL_BMAX = src_const(_SGP, "_VAL_BACKUP_MAX_AGE")`, `_VAL_WT = src_const(_SGP,
  "_VAL_WAIT_TIME_NTP")`, `_VAL_RESET = src_const(_SGP, "_VAL_RESET_VOC")`; `test_get_cfg_schema_matches_the_public_attribute`
  → `test_get_cfg_schema_is_the_module_schema` asserting `get_cfg_schema() == _VAL_BP + _VAL_BMAX + _VAL_WT + _VAL_RESET`
  (comment: "inherited from SensorReaderConfig"). The dict-shape test keeps its key set. Each `write_config({…},
  schema)` → `write_config({…})`.
- **Resolved**: A.U15.17's "update the special slot to 0" is satisfied by reading the source (no literal left).
- **Unit**: U24 (stages U10, U11, U15).
- **Depends**: M.SRC_SENS.060; M.TEST_HELP.044.
- **Blast carried by**: `tests_scripts/test_const_mirrors.py` → A.U24.02 (TSC).
- **Kind**: test

### M.TEST_UNIT.141 Read loop returns None; fast sleep shared
- **From**: A.U10.44 (`_read_loop`), A.U15.43 (`:2299` → `None`), A.U24.49.
- **Site**: `tests/test_asy_sgp40_driver.py:1480-1531`, `:2294-2299`.
- **Change**: `reader.read_loop()` → `reader._read_loop()`; `FastAsyncSleep()`; its comment "3ms/500ms/100ms…1s" →
  the constant names (`_SERIAL_READ_WAIT_MS`, `_SELF_TEST_WAIT_MS`, `_MEASURE_WAIT_MS`, `_GENERAL_CALL_RESET_WAIT_S`).
  `:2299` → `assert run(reader._read_loop()) is None` with the INIT entry and one `code("W", "BUS_RECOVERY")`
  (`_init_failed()`).
- **Resolved**: —
- **Unit**: U15 (stages U8 names, U10).
- **Depends**: M.SRC_SENS.059, .065, .066.
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.142 Compensation encoding and the FRAM-backed log hold
- **From**: A.U12.18 (`:1810-1820`, `:2357-2363` hold), A.U3.09 dropped (OR140.a (7); these holds never depended on
  it; A-C review fold), A.U2.13.
- **Site**: `tests/test_asy_sgp40_driver.py:1778-1959`, `:2349-2370`.
- **Change**: hold, with the shared builders (`make_fram_manager(chip=…)`, M.TEST_HELP.057, for the reboot-shaped
  cases), `run(reader.setup())`, catalog names in the assertions and the four-field tuples.
- **Resolved**: —
- **Unit**: U24.
  A-C2 step order: A.U2.13's part lands in U3, not U2 (it follows A.U2.13's own change, which lands in U3).
- **Depends**: M.TEST_HELP.057.
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.143 Init failures: INIT plus controller rung; config reads in both layers
- **From**: A.U15.R02 (3) (`_init_failed()`), A.U10.R01 (5), A.U3.05 (`:1995-2002`, `:2047-2054`: the real store broken)
  with its print-only half dropped (OR140.a (7): SGP40 keeps its own entry; A-C review fold), A.U15.41 (re-arm in
  `_init_sgp()`), A.U15.17 (`:2005-2030` cap holds).
- **Site**: `tests/test_asy_sgp40_driver.py:1968-2054`.
- **Change**: `:1968-1978` → newest `code("E", "INIT")` and one `code("W", "BUS_RECOVERY")`. `:1980-2002` and
  `:2031-2054` break the real `ConfigManager` (an invalid stored key) instead of patching the read: the SGP40 log keeps
  its own config-read entry (HEAD's 12/13, by the catalog name the fold gives it back), `CFGMGR_SGP40` holds `code("E",
  "CFG_NOT_VALID")`. The stale-wait cap test holds with `_voc_init`/
  `_voc_write`. New `test_init_rearms_a_failed_timer_first` (`_timer_error` set: `_init_sgp()` clears it and arms the
  trigger timer before the setup exchange).
- **Resolved**: —
- **Unit**: U15 (stage U10).
  A-C2 step order: A.U10.R01's part lands in U13, not U10 (it follows A.U10.R01's own change, which lands in U13).
- **Depends**: M.SRC_SENS.063, .065 (as the fold reverts A.U3.05); M.SRC_CORE.037; [fold F11 M_GEN] (the restored SGP40 code's
  name).
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.144 _read_sgp branches: algorithm-state code, the format comment
- **From**: A.U2.13 (16/17 → 58), A.U12.14 (`:2262-2265`).
- **Site**: `tests/test_asy_sgp40_driver.py:2235-2286`.
- **Change**: the serialize/deserialize failure assertions → `code("E", "SGP_ALGO_STATE")`; `_TooSmallBuf`'s comment
  "32q" → "<32q".
- **Resolved**: —
- **Unit**: U15 (stages U2, U12).
  A-C2 step order: A.U2.13's part lands in U3, not U2 (it follows A.U2.13's own change, which lands in U3).
- **Depends**: M.SRC_SENS.064.
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.145 None-word paths retire; word readers pinned
- **From**: A.U15.13 (`:2302-2345` go), A.U30.06 (`_read_word`/`_read_words` L1; fakes patch `_read_word`), A.U8.07
  (`:2330-2333` mirror site goes).
- **Site**: `tests/test_asy_sgp40_driver.py:2302-2345`.
- **Change**: the `_NoneReadWord` tests and the `:2330-2333` wait mirror go — the `None` paths no longer exist (guard:
  the merged `_exchange()` raises on every failure, pinned by M.TEST_UNIT.126/.129). Any fake patching
  `_read_word_from_command` patches `_read_word`. New `test_read_word_decodes_one_word_in_place` (one reply → the int,
  no list) and `test_read_words_returns_three_serial_words`.
- **Resolved**: —
- **Unit**: U30 (stages U8, U15).
- **Depends**: M.SRC_SENS.068.
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.146 Address sweep by equality, heater-off included
- **From**: A.U24.29, A.U15.R02 (heater-off joins).
- **Site**: `tests/test_asy_sgp40_driver.py:2378-2404`.
- **Change**: as A.U24.29: every public coroutine method of `SGP40_I2C` from `dir()` minus `setup`/`initialize`/`_reset`
  (`get_raw`, `measure_raw`, `measure_index_and_raw`, `turn_heater_off`) runs from an argument table (a method missing
  from the table fails) and the touched set equals `{0x59}`; `_reset()` alone touches `{0x00}` with payload `0x06`;
  `setup()`/`initialize()` touch `{0x59, 0x00}`. The `except Exception: pass` goes; the fake is seeded per call.
- **Resolved**: —
- **Unit**: U24 (stage U15 method).
- **Depends**: M.SRC_SENS.069.
- **Blast carried by**: twin sweep → A.U13.R02 (TWIN).
- **Kind**: test

### M.TEST_UNIT.147 Unwritable config: defaults run, CFGMGR holds the write
- **From**: A.U5.11, A.U10.10, A.U2.06.
- **Site**: `tests/test_asy_sgp40_driver.py:2405-2428`.
- **Change**: constructor and `setup()` per M.TEST_UNIT.125; `12 not in …` → the SGP40 log's `ErrCount == 0`;
  the CFGMGR assertion → `code("E", "CFG_FILE_WRITE")`.
- **Resolved**: —
- **Unit**: U15.
- **Depends**: M.SRC_SENS.062.
- **Blast carried by**: —
- **Kind**: test

## tests/test_asy_spi_driver.py

### M.TEST_UNIT.148 Harness, lock and attribute names, wait tags, version stamps
- **From**: A.U10.18 (`async_lock` → `bus_lock` 55 sites, `device.asy_lock` → `session_lock`), A.U10.35
  (`cs_active_value` private; M.SRC_SENS.004 makes `cs_pin` and the five siblings private too), A.U8C.16 (`:655` 1.0,
  `:831` 0.2), A.U8C.09/A.U8C.18 (read: shared IDs, no site of theirs here), A.SDEP.08 (`:168`, `:685` stamps),
  A.U24.78 (`:736` fault shape).
- **Site**: `tests/test_asy_spi_driver.py:1-42`; every lock and CS attribute reference; `:168`, `:655`, `:685`, `:736`,
  `:831`.
- **Change**: harness migration (Conventions: `from _async_harness import run`); `spi.async_lock` → `spi.bus_lock`
  everywhere; `:263` → `assert device.session_lock is spi.bus_lock`; `device.cs_pin` → `device._cs_pin`,
  `device.cs_active_value`/`other.cs_active_value` → `._cs_active_value`. Module level `# @tunable
  l1.asy_i2c_driver_gather_wait_s = 1.0` / `_GATHER_WAIT_S = 1.0` and `# @tunable l1.asy_i2c_driver_deadlock_wait_s =
  0.2` / `_DEADLOCK_WAIT_S = 0.2`; the literals at `:655`, `:831` become them. `:168` "at v1.29.0" and `:685` "added in
  MicroPython 1.29" carry the version the pin re-check confirms (or the fact is corrected with F.5). `:736` →
  `fake(spi).inject_fault("readinto", OSError, errno.EIO, "SPI RX overrun")` (64 bytes: at or above the fake's DMA
  threshold, so the queued fault fires).
- **Resolved**: —
- **Unit**: U24 (stages U0/U37 stamps, U8C tags, U10 names).
- **Depends**: M.SRC_SENS.003, .004; M.TEST_HELP.015, .016, .043.
- **Blast carried by**: Part N rows (shared with `tests/test_asy_i2c_driver.py`, M.TEST_UNIT.052) → A.U8.01 (SPEC).
- **Kind**: test

### M.TEST_UNIT.149 A dead bus answers False; deinit returns True
- **From**: A.U13.08 (`:89-95`, `:97-110` assert `False`; `:118-122`; `:151-160`; `:205-218`; `:427-440`; new L1s),
  A.U13.16 (`:48-78` `deinit()` is `True`), A.U24.38 (`:89` no transfer logged).
- **Site**: `tests/test_asy_spi_driver.py:48-160`, `:200-218`, `:427-440`.
- **Change**: the three deinit tests gain `assert spi.deinit() is True` (both calls in the double-deinit test).
  `test_operations_after_deinit_return_none_or_noop` → `…_return_false` asserting each of `write`, `readinto`,
  `write_readinto` returns `False` and `len(mock.log)` is unchanged; the device-level twin of it → `…_return_false`,
  each awaited op `False`, and its comment → "# Bypasses `async with device:` on purpose: this pins the transfer-level
  False contract, reached directly as the I2C equivalent test does." `test_write_forwards_buffer_and_returns_none` →
  `…_returns_true` asserting `spi.write(b"abc") is True`. The mismatch test → `…_returns_false_instead_of_raising`, each
  call `is False`, its comment's "turned into a None return" → "turned into a False return".
  `test_configure_raises_if_bus_deinitialized_even_with_lock_held` → `test_configure_returns_false_on_a_deinitialized_bus_with_the_lock_held`
  (`spi.configure() is False`, no `init` logged). `test_deinit_mid_session_…` asserts the mid-session `readinto()`
  returns `False` (buffer untouched). New `test_every_completed_transfer_returns_true` (write, readinto,
  write_readinto, configure under the lock) and `test_async_write_readinto_inside_a_session_fills_the_buffer` (`async
  with device:` on a live bus: `buffer_in` filled, `True`). `:1052-1056`'s length-mismatch-before-overrun comment's
  "the wrapper's None" → "the wrapper's False".
- **Resolved**: A.U24.38 writes "each returns `None`" for `:89`; the merged product returns `False` (M.SRC_SENS.003,
  A.U13.08, an earlier unit whose contract A.U24.38's assertion text predates) — its substance, "the fake bus log gains
  no transfer", is kept with the product's value.
- **Unit**: U13 (stage U24 log assertion).
- **Depends**: M.SRC_SENS.003, .004.
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.150 Configure tuples use rp2's MSB number
- **From**: A.U24.23 (`:229`, `:234-241`, `:982`).
- **Site**: `tests/test_asy_spi_driver.py:221-252`, `:964-982`.
- **Change**: `:229` passes `firstbit=FakeSPI.MSB` and expects `("init", 2000000, 1, 1, 8, 1)`; `:982` expects
  `("init", 1000000, 0, 0, 8, 1)`; the `:238-240` comment ("FakeSPI.LSB mirrors the real constant value") holds as now
  true.
- **Resolved**: —
- **Unit**: U24.
- **Depends**: M.TEST_HELP.016.
- **Blast carried by**: golden `_INIT_EVENT` → M.TEST_UNIT.050 (`tests/test_asy_fram_wire_trace.py`).
- **Kind**: test

### M.TEST_UNIT.151 Setup cannot glitch CS; LSB triggers the session-entry failures
- **From**: A.U13.03 (setup tests hold; new CS recorder L1), A.U13.08 (`:465-495`, `:940-960` trigger; new
  session-begin case).
- **Site**: `tests/test_asy_spi_driver.py:266-282`, `:465-495`, `:940-960`; a new test.
- **Change**: the setup tests hold (reading `_cs_pin`). New `test_setup_never_drives_the_active_level_as_an_output`: a
  test-local `_RecordingPin(machine.Pin)` overriding `init()`/`value()` to append `(mode, level)` after each call is put
  in the device's `_cs_pin` before `setup()`; no recorded state has `mode == Pin.OUT` with the active level, for both
  `cs_active_value` settings. `test_aenter_releases_the_lock_if_configure_raises`: the trigger becomes
  `SPIDevice(spi, 1, firstbit=FakeSPI.LSB)` (set up), whose `configure()` the fake refuses with `NotImplementedError`;
  `except RuntimeError` → `except NotImplementedError`; the retry runs on a fresh `make_device(spi)`; its comment →
  "# If configure() raises after __aenter__ took the lock, `async with` never calls __aexit__: __aenter__ must release
  the lock itself before the exception propagates." `test_session_begin_deasserts_cs_if_configure_raises_mid_session`:
  same LSB trigger, `except NotImplementedError`. New `test_session_begin_returns_false_on_a_deinitialized_bus`
  (`session_begin()` is `False`, CS never asserted, the caller's lock hold intact) and
  `test_aenter_on_a_deinitialized_bus_holds_the_lock_and_every_transfer_is_false` (the session enters, each transfer
  returns `False`, CS never asserted, the lock released after).
- **Resolved**: —
- **Unit**: U13.
- **Depends**: M.SRC_SENS.004; M.TEST_HELP.012 (`Pin.init(value=)`), .016 (LSB refusal).
- **Blast carried by**: L2-L4 tiers → A.U13.03 (TWIN, HW_DEV; no wire effect, sweeps unchanged).
- **Kind**: test

### M.TEST_UNIT.152 RX-overrun pins name their observable effect
- **From**: A.U24.38 (`:689`, `:698`), A.U35.20 (`:736`, `:1055` stay).
- **Site**: `tests/test_asy_spi_driver.py:684-740`, `:1050-1080`.
- **Change**: `:689` (long write, overrun armed) → the write lands in the log (`log[-1] == ("write", bytes(64))`) and
  `rx_overrun` is still `True`; `:698` (short reads) → with scripted bytes queued, both reads return them and
  `rx_overrun` stays `True` (the DMA path not taken). `:736` and `:1055` hold (driver-level duplicates kept per
  A.U35.20).
- **Resolved**: —
- **Unit**: U24.
- **Depends**: M.TEST_HELP.016.
- **Blast carried by**: —
- **Kind**: test

## tests/test_asy_uart_comm.py

### M.TEST_UNIT.153 Imports, harness bounds, wire copies, tagged waits, dividers
- **From**: GAP-T1 (M.TEST_HELP.023/.024: `RUN_LIMIT_S` public, `run(coro, RUN_LIMIT_S)`, `build_pair()` asserts setup),
  A.U24.31 (60 `build_pair(` sites), A.U8C.03/A.U8C.17 (tags; `POLL_WAIT_MS` imported), A.U8C2.04 (`:949`, `:952`),
  A.U8C2.51 (read: SPEC Dependants), A.U8C.19 (read: shared IDs), A.U24.01 (`:33-42` kept as J.3 copies, `:43-44`
  mirrors go), A.U10.37/A.U10.38 (module and class names), A.U16.05 (`:19`), A.U24.73 (`Any`, 23 lines), A.U27.30
  (dividers), A.U10.18 (`bus.asy_lock` → `session_lock`), A.U2.20/A.U2.03 (catalog names), A.U0.07 (function-level
  imports).
- **Site**: `tests/test_asy_uart_comm.py:1-62` and every `run(`, divider, lock and wait-literal line A.U8C.17/A.U8C2.04
  list.
- **Change**: imports `from _async_harness import run`; `from _uart_comm_harness import PAYLOAD_SIZE, POLL_WAIT_MS,
  RUN_LIMIT_S, TIMEOUT_MS, Pair, accept_set, build_pair, echo_get, frames`; `from _error_codes import code`; `from
  asy_uart_comm import ROLE_INITIATOR, ROLE_RESPONDER, ListenResult, ResponderCallbacks, UARTComm, _next_uid`; `from
  asy_base_classes import RegionBuffer`; `from asy_crc_checks import CRC16`; `from asy_framing_codecs import
  FramingCOBS`; `import time` module level (the two in-function imports at `:497`, `:509`, `:749` go). `_CMD_ACK`…
  `_PAYLOAD` keep their values with one comment line "# The wire layout of SPECIFICATION.md Part J.3 - the protocol's
  own copy, pinned to the module by tests_scripts/test_const_mirrors.py."; `_ERR_ALLOC`/`_ERR_RXBUF` go — every use
  reads `code("E", "ALLOC")`/`code("E", "UART_RXBUF")`. `persisted()` keeps its shape and gains the helpers `_e(name) ->
  str` / `_w(name) -> str` returning `f"E{code('E', name)}"`/`f"W{code('W', name)}"`, used by every expected list.
  Every bare `run(x)` → `run(x, RUN_LIMIT_S)` (the harness's old default bound kept explicit), every `run(x, limit=N)`
  → `run(x, <the A.U8C.17 constant for N at that line>)`. Module constants with tags exactly as A.U8C.17 lists
  (`_SHORT_REPLY_TIMEOUT_MS = 30`, `_STEP_BOUND_S = 10`, `_LOOP_SURVIVAL_WAIT_MS = 20`, `_SILENT_BOUND_S = 15`,
  `_LISTENER_RUN_BOUND_S = 25`, `_SHORT_BOUND_S = 5`, `_PAST_DEADLINE_BOUND_S = 2`, `_FLOOD_STEP_MS = 1`, `_RUN_BOUND_S
  = 20`, `_LISTENER_PARK_MS = 10`, `_INSIDE_LOCK_MS = 5`, `_LISTENER_SHORT_BOUND_S = 8`, `_ASYNC_CALLBACK_YIELD_MS = 1`,
  `_BSEC_RUN_BOUND_S = 60`) and `_PROMPT_HOLD_MS = 5` (tagged) / `_PAST_CANCEL_ACK_HOLD_MS = 1300` (untagged, derived) per
  A.U8C2.04; the `poll_wait_ms=1` literals at `:57, :82, :145, :156, :160, :177, :183` → `POLL_WAIT_MS`. Every
  `# ====…` divider (12) → `# ----…` of the same length. `bus.asy_lock` (`:1955-1975`) → `bus.session_lock`. `Any`
  annotations → `object` or the harness's callback protocols per A.U24.73's scheme.
- **Resolved**: —
- **Unit**: U24 (stages U8C tags, U10 names, U27 dividers).
- **Depends**: M.TEST_HELP.023, .024, .043, .045; M.SRC_NET.150, .151, .153.
- **Blast carried by**: Part N rows → A.U8.01 (SPEC); `tests_scripts/test_const_mirrors.py` row for the J.3 copies →
  A.U24.02 (TSC); the divider gate → A.U27.30 (TSC).
- **Kind**: test

### M.TEST_UNIT.154 Construction passes one callbacks object; callback attributes private
- **From**: A.U5.12 (12 `UART_Comm(` calls, 88 callback keywords, `make_comm()`), A.U10.35 (`get_callback`,
  `message_callback` private; M.SRC_NET.155 adds `set_callback`), A.U13.17 (`poll_idle_ms` equal to `poll_wait_ms`
  where one rate is assumed), GAP (M_SRC_NET gap 5: `set_callback` readers).
- **Site**: `tests/test_asy_uart_comm.py:54-62` (`make_comm`), every `UART_Comm(`/`UART(` construction, `:1527`,
  `:1555`, `:1700`.
- **Change**: `make_comm(**kwargs)` builds `UART(0, tx_pin=0, rx_pin=1, poll_wait_ms=POLL_WAIT_MS,
  poll_idle_ms=POLL_WAIT_MS)` and maps its `get_callback`/`set_callback`/`message_callback` keywords into
  `callbacks=ResponderCallbacks(get, set, message)` (absent when none is given) before `UARTComm(bus, role, **params)`;
  every direct `UART_Comm(…)` → `UARTComm(…)`; every test `UART(…)` passes `poll_idle_ms` equal to its `poll_wait_ms`
  (`:57, 82, 108, 145, 156, 160, 168, 177, 183`). `logger=own.pr` (`:207`) stays. `pair.responder.get_callback =
  reentrant` → `pair.responder._get_callback = reentrant`; `pair.responder.message_callback is None` →
  `._message_callback is None`; `pair.responder.get_callback = None` → `._get_callback = None`.
- **Resolved**: —
- **Unit**: U5 (stages U10 names, U13 idle rate).
- **Depends**: M.SRC_NET.154, .155.
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.155 Construction refusals: poll range, timeout ceiling, codec size
- **From**: A.U17.20 (`:105-111`, `:165-170`; new L1s), A.U17.22 (`:177`, `:183` hold; new L1), A.U2.20 (`:181`
  code); OR141.a (4) (e) (the rxbuf floor becomes the DMA ring's size floor, refused the same way; A-C review fold).
- **Site**: `tests/test_asy_uart_comm.py:102-185`; new tests after `:185`.
- **Change**: `:105-111` → `poll_wait_ms=9, poll_idle_ms=9` (floor 2 × 9 + 9 + 21 = 48: 30 still refused, 200
  accepted). `:165-170` → `poll_wait_ms=9` and a 64-byte receive ring (not an rxbuf: from U17 the floor applies to the
  ring); `assert …` equals the ring-floor refusal's code (M.SRC_NET's, by catalog name); comment → "# A 9ms poll interval
  plus the module's 5ms of scheduling slack admits ~161 bytes at 115200 baud, so a 64-byte ring loses the tail of
  anything sustained even though a frame fits." New `test_the_ring_floor_covers_the_longest_flash_write` (the floor is
  the larger of one framed frame, one poll interval's bytes and the stop-and-wait bytes the peer can send during the
  longest synchronous flash write, rounded up to a power of two — each term computed by the test from its own inputs,
  W25Q16JV tSE max 400 ms; one power of two below it refused, exactly it accepted).`:181` → `code("E", "ALLOC")`; `Framing_COBS` → `FramingCOBS`. New
  `test_the_timeout_ceiling_keeps_every_deadline_a_valid_tick_delay` (89_478_485 accepted, its `_resync_window_ms() * 4`
  and `_backoff_max_ms` both below 2**29 by the test's own arithmetic; 89_478_486 refused with
  `code("E", "UART_TIMEOUT_PARAM")`); `test_a_poll_rate_outside_one_to_nine_ms_is_refused` (0 and 10 →
  `code("E", "UART_POLL_RATE")`; 1 and 9 accepted, rxbuf and timeout sized to pass);
  `test_a_codec_below_one_frame_is_refused` (a `FramingCOBS` one byte below `5 + payload_size + crc.length()` →
  `code("E", "UART_CODEC_SIZE")`, exactly that size accepted, and a pair on exact-sized codecs completes a GET and a SET
  with no CRC and with CRC16).
- **Resolved**: —
- **Unit**: U17 (the ring-floor cases with OR141.a (4)'s U17 part).
- **Depends**: M.SRC_NET.152, .153, .156; [fold F25 M_SRC_NET] (the ring-size floor in `asy_uart_comm.py`).
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.156 One plain error helper: catalog codes, the central repeat rule
- **From**: A.U3.02 (`:221-231` `_last_errno` goes; `:234-273` rewritten), A.U3.01, A.U10.04 (`:225` holds), A.U17.13
  and A.U17.14 (`:221-231` hold), A.U2.20.
- **Site**: `tests/test_asy_uart_comm.py:221-273`.
- **Change**: the synthetic `_err(19, …)`/`_err(20, …)` → `_err(code("E", "UART_FRAME_INVALID"), …)`/`code("E",
  "UART_NO_ACK")`. `test_reset_clears_the_history_and_the_streak_state`: the `_last_errno` assertion goes (the attribute
  is gone); `_blind_resyncs == 0` and `ErrCount == 0` hold. `test_a_repeated_identical_fault_stops_persisting` →
  `test_a_repeated_identical_fault_spends_one_slot_and_counts_every_time`: 21 identical faults leave one slot of that
  code and `ErrCount == 21`; `comm._note_valid_frame()` (synchronous now, no `run`) adds nothing; a different code then
  spends a second slot. `test_a_single_transient_fault_leaves_one_entry_not_a_pair` holds with the synchronous call.
  `test_a_repeatedly_declined_command_does_not_refill_the_history`: five declines → `persisted == [_w("UART_CMD_DECLINED")]`
  with `ErrCount == 5`; a second id `0x43` is the same code and spends no slot (`persisted` unchanged, `ErrCount == 6`);
  its comment → "# A declined command persists W56 each time; identical codes share one slot under the central rule
  (C.7.1), whatever the id." and `run(…, limit=10)` → `run(…, RUN_LIMIT_S)`.
- **Resolved**: —
- **Unit**: U3 (stage U2 names).
- **Depends**: M.SRC_NET.158, .163, .164; M.SRC_CORE (A.U3.01 newest-entry rule).
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.157 Range-sweep tests retire for the L0 catalog check
- **From**: A.U2.02 (`:275-303`, `:306-317` removed), A.U24.50 (3) (`:308-316` keyword floor).
- **Site**: `tests/test_asy_uart_comm.py:275-317`.
- **Change**: both tests and the `_SRC` constant's use there go (`_SRC` stays for `:400`'s structural test). Guard
  named: `tests_scripts/test_error_catalog.py` (A.U2.02) — every logging call is catalogued, by keyword and one idiom.
- **Resolved**: A.U24.50 (3) (U24) hardens `:308-316` against matching nothing; A.U2.02 (U2) removes that test first
  with its `_ERRNO_MIN/_MAX` source. The test's own target is gone, so A.U24.50 (3)'s non-vacuity requirement moves to the
  L0 check that replaces it (agent decision D-T14; carried as GAP-U2 (TSC)).
- **Unit**: U2.
  A-C2 step order: A.U2.02's part lands in U3, not U2 (it follows A.U2.02's own change, which lands in U3).
- **Depends**: M.SRC_NET.153.
- **Blast carried by**: the keyword-matched-at-least-once floor → GAP-U2 (TSC, `tests_scripts/test_error_catalog.py`).
- **Kind**: test

### M.TEST_UNIT.158 Five buffers in region buffers
- **From**: A.U3.02 (`:347-365` five-tuple), A.U16.05 (`:337`, `:1256`, `:2182`), A.U2.20 (`:362`).
- **Site**: `tests/test_asy_uart_comm.py:333-365`, `:1253-1260`, `:2176-2186`.
- **Change**: `starved()` unpacks `tx, rx, _ack, _zero, _cmd = real_allocate(self)` and returns `tx, rx, bytearray(0),
  bytearray(0), bytearray(0)`; `UART_Comm._allocate` → `UARTComm._allocate` (the two inline `method-assign` ignores
  stay); `:362` → `code("E", "ALLOC")`. The `:337` and `:1256` comments' `LockableBuffer` → `RegionBuffer`. `:2182` →
  `comm._rx = RegionBuffer(-1)` (a region buffer whose allocation failed) with the same `get_buf() is None` premise
  check.
- **Resolved**: —
- **Unit**: U16 (stage U3 tuple).
- **Depends**: M.SRC_NET.157; M.SRC_CORE `RegionBuffer` (A.U16.05).
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.159 Starters by name; the listen loop re-listens after a command
- **From**: A.U32.06 + A.U10.44 (`:392-393`), A.U17.17 (`:425-431`, `:434-460`, `:1514-1560` hold; new L1s),
  A.U17.20 (backoff under the ceiling), A.U3.08 (`:449`).
- **Site**: `tests/test_asy_uart_comm.py:386-460`; new tests after `:460`.
- **Change**: `:392-393` → `responder.get_task_starters() == [responder.start_asy_listen]`. New
  `test_a_declined_get_does_not_back_off_the_next_answer` (pair built at sync scope `run(build_pair(…), RUN_LIMIT_S)`;
  the responder's real listen task; `get_callback` declines 9, answers 1; four `uart_get(9)` → `None`, then `uart_get(1)`
  right after the initiator's recovery returns the answer; a recorder replacing `asy_uart_comm.asyncio.sleep_ms`
  (restored in `finally`) holds no delay ≥ `_backoff_initial_ms` between the first decline and the answer);
  `test_a_dead_link_still_doubles_its_backoff` (noise fed each round, `_LISTEN_FAILED` each time: the recorded sleeps
  double); `test_the_backoff_stays_a_valid_tick_delay_at_the_timeout_ceiling` (`timeout = 89_478_485`, `uart_listen`
  replaced on the instance by a coroutine returning `_LISTEN_FAILED`, the module's `sleep_ms` by an immediate recorder,
  8 rounds: delays double from `_backoff_initial_ms` to `_backoff_max_ms`, each below 2**29). The two delivery tests
  (`:1514-1560`) call `start_asy_listen()` by name instead of indexing the starter list.
- **Resolved**: —
- **Unit**: U17 (stages U10 starter, U32 hold).
- **Depends**: M.SRC_NET.170.
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.160 Exchange layer: owner tag; the hold-off crosses a real wrap
- **From**: A.U0.28 (`:704`), A.U17.12 (read: `:704` holds after A.U0.28), A.U14.34 (`:748-757`), A.U17.06 (new (a)-(c);
  `:725-736` holds), A.U25.30 (read: `:641`, `:664` use the unit fake's `settle()`), A.U17.16 (read: `:529`, `:613` hold).
- **Site**: `tests/test_asy_uart_comm.py:700-757`; new tests after `:757`.
- **Change**: `:704` "folded into failure by decision" → "folded into failure (owner, 2026-09-11, `b131169`)".
  `test_the_hold_off_deadline_survives_the_ticks_rollover` crosses a real 2**30 wrap: `Ticks30Time` installed as
  `asy_uart_comm.time` (restored in `finally`), `now` set just below the wrap, the hold-off armed, the clock advanced
  past the wrap by more than a window → the gate returns at once. New (A.U17.06):
  `test_a_hold_off_aged_past_the_tick_horizon_expires` (armed at `now`, advanced 2**29 + 1000 ms → returns at once, flag
  cleared); `test_the_aliased_band_holds_at_most_one_window` (advanced 2**30 + window/2 → still held, released once a
  helper task advancing the fake clock 20 ms per real `sleep_ms(1)` has moved it a further window/2);
  `test_an_unaged_hold_off_releases_at_its_window` (window − 1 → held; window + 1 → released).
- **Resolved**: —
- **Unit**: U17 (stages U0 tag, U14 wrap).
- **Depends**: M.SRC_NET.160; M.TEST_HELP.064.
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.161 Resyncs print; only the drain bound persists W54
- **From**: A.U3.08 (`:801-835`; new L1), A.U17.14 (new L1), A.U10.04 (new L1), A.U2.20.
- **Site**: `tests/test_asy_uart_comm.py:801-855`; new tests after `:855`.
- **Change**: `test_a_drain_that_hits_its_bound_spends_the_episode_slot_on_the_more_specific_warning` →
  `test_a_drain_that_hits_its_bound_persists_the_drain_warning` (`persisted == [_w("UART_DRAIN_BOUND")]`; comment →
  "# W54 separates a babbling or misconfigured peer from ordinary line noise; a quiet resync only prints.");
  `test_a_quiet_resync_still_persists_the_plain_resync_warning` → `test_a_quiet_resync_persists_nothing`
  (`persisted == []`). The boot-drain test holds. New `test_one_fault_on_a_quiet_line_adds_one_entry` (the errno only) and
  `test_one_fault_hitting_the_drain_bound_adds_the_errno_and_w54`; `test_the_blind_resync_streak_saturates` (`_blind_resyncs`
  set to the streak threshold read with `src_const(_SRC, "_DIAG_RESYNC_STREAK")`; a further blind resync leaves it there
  and still persists `code("E", "UART_LINK_UNINTELLIGIBLE")`); `test_the_valid_frame_count_saturates` (`_valid_frames =
  COUNTER_CAP`, one more validated frame leaves it at `COUNTER_CAP`; `COUNTER_CAP` from `asy_base_classes`).
- **Resolved**: A.U17.14 says the threshold literal is "tagged with its Part N row"; read from source instead, the
  test carries no copy (A.U24.01's rule) — the row's Dependants name the test (agent decision, same as D-T4).
- **Unit**: U17 (stages U3, U10).
  A-C2: stage U24 — until M.TEST_HELP.044's `src_const()` exists the streak threshold is a local mirror (the HEAD form); U24 swaps in `src_const()`.
- **Depends**: M.SRC_NET.162, .164; M.TEST_HELP.044.
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.162 Cancel-unacknowledged: W55 and the two hold constants
- **From**: A.U8C2.04 (`:949`, `:952`), A.U2.20 (W13 → 55), A.U8C.17 (`:945`, `:949`, `:952` bounds).
- **Site**: `tests/test_asy_uart_comm.py:925-953`.
- **Change**: `scenario(1300)` → `scenario(_PAST_CANCEL_ACK_HOLD_MS)`, `scenario(5)` → `scenario(_PROMPT_HOLD_MS)`; the
  comment "past the driver's own 1000ms acknowledgement bound" stays; `["W13"]` → `[_w("UART_CANCEL_UNACKED")]`; the
  comment's "wrnno 13" → "W55".
- **Resolved**: —
- **Unit**: U8C (stage U2 code).
- **Depends**: M.SRC_NET.153.
- **Blast carried by**: Part N `uart.cancel_ack_timeout_ms` Dependants → A.U8C2.51 (SPEC).
- **Kind**: test

### M.TEST_UNIT.163 Gate first, then arguments; API-only section header
- **From**: A.U17.01 (`:187-197`, `:1255-1260`, `:1336`, `:1353`, `:1365`, `:1390`, `:1430`, `:1443`, `:1451` hold; new
  L1s), A.U17.02 (header after `:1336`), A.U2.20 (`:1450` 34 → BAD_ARG).
- **Site**: `tests/test_asy_uart_comm.py:187-197`, `:1336-1451`; new tests.
- **Change**: `:1450` `assert 34 in log["ErrNum"]` → `code("E", "BAD_ARG") in log["ErrNum"]`. After `:1336` the header
  "# ---- General-purpose initiator API: no product caller; kept as the standalone module's API (owner, 2026-09-29) ----"
  heads the stream/into tests that follow. New `test_every_initiator_entry_point_answers_not_initialised_before_setup`
  (`uart_get_into(1, None)`, `uart_get_stream(1, None)`, `uart_set_stream(1, 4, None)`, `uart_get(256)` before
  `setup()` each persist `code("E", "NOT_INIT")`, not ALLOC/BAD_ARG); `test_a_responder_refuses_the_role_before_any_argument`
  (the same six calls with invalid arguments on a set-up responder each persist `code("E", "UART_ROLE_REFUSED")`);
  `test_the_command_id_is_checked_first_on_an_initiator` (`uart_set_stream(256, -1, None)` persists `code("E",
  "BAD_ARG")` for the id).
- **Resolved**: —
- **Unit**: U17 (stage U2).
- **Depends**: M.SRC_NET.167.
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.164 Fault histories without the resync warning; renumbered codes
- **From**: A.U3.02 + A.U3.08 (`:1458-1506`, `:1729-1746`, `:1763, 1781, 1841, 1884, 1944, 2033`, `:1983-2000`),
  A.U2.20 (`:1666`, `:1702`, `:1822`, and every `persisted()` literal), A.U10.35 (`:1700`); OR143.a (1)-(2) (the
  peer-sized destination and right-sizing allocations and their caught-`MemoryError` sites go; A-C review fold).
- **Site**: `tests/test_asy_uart_comm.py:1458-1506`, `:1640-2033`.
- **Change**: `test_a_repeating_fault_does_not_bury_the_errno_under_resync_warnings` → `…_spends_one_slot`: five
  identical no-ACK faults leave `recorded == [("E", code("E", "UART_NO_ACK"))]` and `ErrCount == 5` (no resync warning
  exists). `test_a_recovered_link_starts_a_fresh_episode` → `test_a_recovered_link_counts_every_later_fault`: after the
  recovery and one more fault, `ErrCount == 3` and the history still holds one no-ACK slot (identical to the newest
  entry); its comment states the central rule. `test_a_rejected_command_is_distinguishable_from_a_link_fault`: `("W",
  14)` → `("W", code("W", "UART_CMD_DECLINED"))`. `:1666` `["W14"]` → `[_w("UART_CMD_DECLINED")]`; `:1702` `["E16"]` →
  `[_e("BAD_ARG")]`; `"E21"` → `_e("UART_WRITE_FAILED")`, `"E29"` → `_e("UART_GET_ID_MISMATCH")`, `"E14"` (`:1944`, the
  internal-buffer recheck) → `_e("ALLOC")`; the four starved-destination tests (`:1825-1910`, `"E24"`) go with the
  allocations they starve (guard: M.TEST_UNIT.345's chunk and cap cases), `"E25"` → `_e("UART_SIZE_MISMATCH")`, `"E33"` → `_e("UART_STREAM_SHORT")`, `"E26"` → `_e("CALLBACK")`;
  every `"W10"` element goes from its expected list (`[errno, "W10"]` → `[errno]`), and `:1729-1746`'s `"W10" in log`
  becomes an assertion that the resync ran (`_holdoff_active is True`). The comments naming "errno 21"/"errno 33"/
  "errno 26" name the catalog codes. `test_two_declined_ids_in_rotation_do_not_refill_the_history_either` →
  `persisted == [_w("UART_CMD_DECLINED")]` after the twelve refusals (`ErrCount == 12`), unchanged after the third id;
  after `reset_error_counter()` one more refusal gives the same one-slot history; comment → "# Alternating declined ids
  are one code, W56: one slot, every refusal counted (C.7.1)."
- **Resolved**: —
- **Unit**: U3 (stage U2 numbers, U10 names; stage U17: the four starved-destination tests go with OR143.a's chunking).
- **Depends**: M.SRC_NET.153, .158, .162, .163; [fold F27 M_SRC_NET] (the chunked assembly, from U17).
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.165 A FRAM-backed comm log survives a second logger
- **From**: A.U24.45 (1), A.U5.12 (`log=` object).
- **Site**: new test in `tests/test_asy_uart_comm.py` (after `:217`).
- **Change**: `test_a_fram_backed_log_reads_back_through_a_second_logger`: `manager = make_fram_manager()` (setup run),
  `comm = make_comm(name="UART_X", log=LogConfig(manager, 10, None))`, one failed transaction (a silent peer) logs
  `code("E", "UART_NO_ACK")`; a second logger over the same manager (`make_logger(LogConfig(manager, 10, None),
  "UART_X")`, set up) reads the same newest entry back.
- **Resolved**: —
- **Unit**: U24 (stage U5 log object).
- **Depends**: M.SRC_NET.155; M.TEST_HELP.057; M.SRC_CORE `LogConfig`/`make_logger`.
- **Blast carried by**: `tests/test_asy_uart_link_driver.py:258-266` comment → M.TEST_UNIT in that file (A.U24.45).
- **Kind**: test

### M.TEST_UNIT.166 Cancellation at every await of the initiator and listener
- **From**: A.U35.48 (one sweep per path), A.U10.18 (`:1955-1975` lock name).
- **Site**: `tests/test_asy_uart_comm.py:1946-1977`; new test.
- **Change**: the cancelled-transaction test reads `bus.session_lock.locked()`. New
  `test_cancelling_at_each_await_leaves_no_lock_or_busy_flag` drives `cancel_at_each_await(build, start, invariants)`
  from synchronous scope over `uart_set`, `uart_get` and `uart_listen` (build: a `Pair` on the harness's bounded
  `LinkPoller`, set up inside the coroutine; invariants: `_busy is False`, the bus `session_lock` unlocked,
  `_in_resync is False`).
- **Resolved**: —
- **Unit**: U35 (stage U10 name).
- **Depends**: M.TEST_HELP.067; M.SRC_NET.167, .168.
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.167 Legacy BSEC demonstration: paths, tags, codes
- **From**: A.U1.25 (`:2037`, `:2041`, `:2138`), A.U0.35 (`:2159`), A.U36.544 (`:2161`), A.U36.027 (read: SPEC J.1),
  A.S0930.03 (`:2163` CRC16 holds), A.U2.20 (`:2168-2169`), A.U35.22 (read: L1 trains named in the level matrix).
- **Site**: `tests/test_asy_uart_comm.py:2035-2186`.
- **Change**: `dev_legacy/…` → `legacy/dev_drivers/…` at the three sites; `:2159` "Kept rather than relaxed" → "Kept rather
  than relaxed (agent, 2026-09-13)"; `:2161` "(SPECIFICATION.md Part J.1)" → "(SPECIFICATION.md Parts J.5, J.6)";
  `UART_Comm` → `UARTComm`; `:2168-2169` `_ERR_RXBUF` → `code("E", "UART_RXBUF")`; `run(scenario(), limit=60)` →
  `run(scenario(), _BSEC_RUN_BOUND_S)`.
- **Resolved**: —
- **Unit**: U36 (stages U0 tag, U1 path, U2 code).
- **Depends**: M.SRC_NET.153.
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.345 The link over the DMA ring: a lap is an overrun; chunked assembly and the receive cap
- **From**: OR141.a (4) (c), (e) (a lap handled as J.7's receive overrun, the ring-size floor), OR143.a (1)-(4)
  (`chunk_bytes` with a reasoned default; a train without a caller destination assembled in pieces of at most
  `chunk_bytes` in the shared piece primitive; `max_transfer_bytes` refusing a declared size before any allocation
  through the withheld ACK, logged once; a caller-supplied destination unchanged; tests: no receive allocation above
  `chunk_bytes` by a largest-block measurement, refusal before any allocation, a maximum-size train assembled
  correctly, hammering with repeated maximum-size and over-cap trains), FOLD_BRIEF F25/F27 (U17) — A-C review fold.
- **Site**: new sections in `tests/test_asy_uart_comm.py`; the piece primitive's cases in the test file of the module
  that holds it (decided with the product change, [fold F27 M_SRC_NET]).
- **Change**: (a) Lap: `test_a_lapped_ring_is_a_receive_overrun_and_the_link_resyncs` (a pair whose responder's consumer
  is held past the ring bound while the initiator streams: the overrun is logged by its catalog code once, J.7's
  resync runs, the next transaction completes; no lapped byte is delivered to a callback). (b) Chunking:
  `test_the_default_chunk_bytes_is_the_reasoned_one` (read from source with `src_const`, the reason in a one-line
  comment); `test_a_dont_care_set_is_assembled_in_pieces_no_larger_than_chunk_bytes` and the same for `uart_get(exp_size=
  None)` — the largest single receive allocation of a maximum-size train is at most `chunk_bytes` (OR143.a (4)'s
  largest-block measurement; whether it reads each piece's size through the primitive or the heap's largest free block
  around the transfer is decided at execution, with its reason recorded — never by filling the heap, CLAUDE.md's
  structural-proof rule), and the train completes with every byte equal to what was sent, read through the primitive's
  length, iteration and copy-out;
  `test_a_caller_supplied_destination_is_still_filled_in_place` (the zero-copy path: no piece allocated);
  `test_chunk_bytes_outside_its_range_is_refused` (the constructor's refusal by its code). (c) Cap:
  `test_a_declared_size_over_max_transfer_bytes_is_refused_before_any_allocation` (CHUNKS × payload over the cap: the
  ACK withheld, the sender's transfer fails as J states, one entry by its catalog code, and `gc.mem_alloc()` unchanged
  across the refusal); the same for `exp_size` over the cap; `test_a_train_at_the_cap_is_accepted`. (d) Hammering:
  `test_repeated_maximum_size_and_over_cap_trains_keep_the_heap_flat` (200 alternating maximum-size and over-cap trains in
  each direction: every maximum-size train intact, every over-cap one refused, `gc.mem_free()` and the largest free
  block after the run within the first train's reading; zero `MemoryError` in the output — the suite gate). (e) The piece
  primitive's own cases (length, iteration, copy-out into a caller buffer, a copy-out larger than the buffer refused, no
  allocation after construction), beside the webserver's `_PieceWriter` cases it is modelled on. Tunables tagged per the
  file's convention.
- **Resolved**: the four starved-destination tests (`:1825-1910`) retire with the caught-`MemoryError` sites (M.TEST_UNIT
  .164); their goal — a peer-sized allocation never lands unguarded mid-transfer — is met by refusing before allocation
  and capping each piece, which (b)-(d) prove.
- **Unit**: U17; stage U24: `src_const()` and the shared pair harness replace the file's local mirror and runner (as
  M.TEST_UNIT.153's harness stage does).
- **Depends**: [fold F25 M_SRC_NET] (the ring floor and lap handling in `asy_uart_comm.py`), [fold F27 M_SRC_NET]
  (`chunk_bytes`, `max_transfer_bytes`, the piece primitive); M.TEST_UNIT.344; M.TEST_HELP.023, .044 (U24 stage).
- **Blast carried by**: the C-port changelog rows (Class A refusal, "no C impact" ring) → [fold F27 M_SRC_NET], [fold F25
  M_SRC_NET]; the concurrent-load and bench maximum-size transfers → M.TWIN.171, C.
- **Kind**: test

## tests/test_asy_uart_driver.py

### M.TEST_UNIT.168 Harness, names, tagged waits, one-line poller rule
- **From**: A.U24.08 (`:23-27` bound 5), A.U8C.18 (tags), A.U8C2.50 (`:1593`, `:1597`), A.U8C.09/A.U8C.16 (shared
  `l1.asy_i2c_driver_deadlock_wait_s` at `:1372`), A.U8C2.51 (read: `:1862` a Dependant), A.U10.37/A.U10.38 (imports,
  codec class names), A.U10.29 (`COBS_DELIMITER` stays public), A.U10.18 (`asy_lock` → `session_lock`, 9 sites),
  A.U24.15 (4) (`:24-25, 32-33, 44-45, 439-441, 857-859` comments), A.U36.532 (`:1465`, `:1561`, `:1584` F.5.x →
  F.8.x), A.U24.73 (`Any`), A.SDEP.16 (W14: `_StepPoller` stays, only its stated cause is re-read).
- **Site**: `tests/test_asy_uart_driver.py:1-56`, the lock lines, the comment and wait-literal lines named.
- **Change**: imports `from _async_harness import run`; `from asy_crc_checks import CRC16, CRCBase, CRCPass`; `from
  asy_framing_codecs import COBS_DELIMITER, FramingBase, FramingCOBS, FramingPass` (class uses follow). The local `run()`
  goes; calls pass `_RUN_BOUND_S` (`# @tunable l1.asy_uart_driver_run_bound_s = 5`). Module constants and tags exactly
  as A.U8C.18 lists, except `_WEDGED_HOLD_MS` (withdrawn, M.TEST_UNIT.171); `_DEADLOCK_WAIT_S = 0.2` carries the shared
  `l1.asy_i2c_driver_deadlock_wait_s` tag; `:1593` → `>= 2 * _IDLE_POLL_MS`, `:1597` → `< _IDLE_POLL_MS`. Every
  `uart.asy_lock` → `uart.session_lock`. The poller comments at `:24-25`, `:32-33`, `:44-45`, `:439-441`, `:857-859`
  each become the one line "# Bounded stand-in, never a real select.poll(): the fake's readiness must be scripted, not
  polled in real time (CLAUDE.md "Known hang cause")." (`_StepPoller`'s second and third comment lines describing its
  stepping stay). "F.5.7"/"F.5.8"/"F.5.9" → "F.8.1"/"F.8.2"/"F.8.3" at U36. `Any` → `object` per A.U24.73.
- **Resolved**: —
- **Unit**: U24 (stages U8C tags, U10 names, U36 repoint).
- **Depends**: M.TEST_HELP.043; M.SRC_NET.190, .191, .193.
- **Blast carried by**: Part N rows → A.U8.01 (SPEC).
- **Kind**: test

### M.TEST_UNIT.169 Readiness from the ring's fill level; the real-poll guard holds
- **From**: A.U24.15 (`:438-445` stay as local checks), GAP-T4 (M.TEST_HELP.010/.017), OR141.a (4) (b), (f) (`ready()`
  reads the ring's fill level, never a receive-side poll; A-C review fold).
- **Site**: `tests/test_asy_uart_driver.py:438-445`.
- **Change**: `test_no_uart_built_here_polls_through_a_real_select_poll` holds and gains `rx_api_calls == 0` (from U13 the
  receive side never polls, M.TEST_UNIT.344). No test in this file reads readiness through `ioctl(…)` (grep at HEAD:
  none), so GAP-T4's `poll_mask()` rewrite has no site here; every test runs under the after-each `real_poll_queries ==
  0` check and needs nothing more (none registers a real poll).
- **Resolved**: —
- **Unit**: U24 (stage U13: the `rx_api_calls` assertion with M.TEST_HELP.069).
- **Depends**: M.TEST_HELP.010, .017, .069.
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.170 Default poll rates change; timing tests re-checked
- **From**: A.U13.17 (`make_uart()` defaults 2/50; re-check `:371, 405-420, 700-830, 875, 1140-1150`), A.U8C2.50.
- **Site**: `tests/test_asy_uart_driver.py:30-36`, `:362-425`, `:690-850`, `:869-878`, `:1131-1170`, `:1582-1598`.
- **Change**: `make_uart()` passes `poll_wait_ms=1, poll_idle_ms=1` unless the test names its own rates, so the
  interleavings at the listed lines keep their HEAD timing (each was written against equal 20/20 rates and a bound in
  ms; at 1/1 every bound keeps its margin). `test_a_deadlineless_wait_polls_at_the_idle_rate_and_a_bounded_one_does_not`
  keeps its explicit `poll_wait_ms=_POLL_WAIT_MS, poll_idle_ms=_IDLE_POLL_MS`. New
  `test_the_default_rates_are_two_and_fifty_ms` (`UART(0, tx_pin=0, rx_pin=1)` built directly: `poll_wait_ms == 2`,
  `poll_idle_ms == 50`).
- **Resolved**: A.U13.17 says "re-check at execution the timing-dependent ones"; pinning the file's builder to one fast
  rate keeps every listed interleaving's premise without per-test edits, and the defaults get their own assertion
  (agent decision D-T16).
- **Unit**: U13.
- **Depends**: M.SRC_NET.192.
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.171 The wedged holder waits on an event, not a sleep
- **From**: A.U35.14 (3) (`:790-806`), A.U8C.18 (`:799` row withdrawn, `:804` kept).
- **Site**: `tests/test_asy_uart_driver.py:791-811`.
- **Change**: `wedged()` awaits an `asyncio.Event` the test never sets (instead of `sleep_ms(400)`); the scenario
  cancels the holder in `finally` and awaits it out; `cancel_read_timeout(timeout_ms=_SHORT_CANCEL_ACK_MS)` keeps its real
  50 ms with one comment line "# A product bound waited out (the cancel acknowledgement), tagged as such." Assertions
  unchanged. No `_WEDGED_HOLD_MS` constant or tag.
- **Resolved**: —
- **Unit**: U35.
- **Depends**: M.TEST_HELP.065 (A.U35.10).
- **Blast carried by**: Part N row `l1.asy_uart_driver_wedged_hold_ms` withdrawn → A.U35.14 (SPEC).
- **Kind**: test

### M.TEST_UNIT.172 Cancel handshake at the counter cap
- **From**: A.U17.28 (`:402-835` hold; new L1s), A.U2.20 (the rise warning's code).
- **Site**: new tests after `:851`.
- **Change**: `test_a_cancel_at_the_counter_cap_wraps_and_is_acknowledged` (`_cancel_req` and `_cancel_ack` set to
  `COUNTER_CAP`; a cancel against a holder that acknowledges returns with request 0 acknowledged);
  `test_the_unacknowledged_count_wraps_and_clear_still_reports_a_rise` (`cancel_unacknowledged = COUNTER_CAP`, a wedged
  holder wraps it to 0; `UARTComm.clear()` over that driver still persists `code("W", "UART_CANCEL_UNACKED")`).
  `COUNTER_CAP` from `asy_base_classes`.
- **Resolved**: —
- **Unit**: U17.
- **Depends**: M.SRC_NET.197.
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.173 Writes wait for an empty TX ring, at most txbuf at a time
- **From**: A.U13.13 (`:1090-1140` hold; new L1s), A.U14.31 (read: the L1 proof is this one).
- **Site**: new tests after `:1250`.
- **Change**: `test_a_long_message_goes_out_in_txbuf_sized_writes` (`txbuf=32`, a 96-byte message: three `write()`
  entries in the fake log, each ≤ 32); `test_no_write_happens_while_the_ring_is_draining` (the fake's `txdone()` false
  for N rounds: no `write` logged in those rounds and a counter task runs at least once per round);
  `test_cancel_or_deinit_during_the_drain_wait_returns_false`.
- **Resolved**: —
- **Unit**: U13.
- **Depends**: M.SRC_NET.195; M.TEST_HELP.018 (fake `txdone()`/`tx_pending_rounds`).
- **Blast carried by**: L2 GET-answer case → A.U13.13 (TWIN).
- **Kind**: test

### M.TEST_UNIT.174 A zero-length payload is nothing to send
- **From**: A.U12.03 (`:937-944`, `:1090-1102` hold; `:1866-1870` flips), A.U12.02 (`:648-658` holds).
- **Site**: `tests/test_asy_uart_driver.py:1865-1870`.
- **Change**: `test_a_crc_framed_write_of_nothing_is_refused_rather_than_sent_as_a_bare_crc` →
  `test_a_crc_framed_write_of_nothing_succeeds_and_sends_nothing` (`locked_writefrom(uart, bytearray(8), 0) is True`,
  `written(uart) == b""`), comment → "# A zero-length payload is nothing to transfer: writefrom() reports success and
  sends nothing, never a bare CRC." New `test_a_crc_framed_read_of_nothing_returns_empty` (`crc=CRC16()`:
  `read_until_complete(0) == bytearray()`, `readinto_until_complete(buf, 0) == 0`, nothing read).
- **Resolved**: —
- **Unit**: U12.
- **Depends**: M.SRC_NET.200, .201, .203.
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.175 Readline paths read the ring, capped
- **From**: A.U13.12 (`:920-929, 1040-1070, 1628-1660, 1872-1880` hold; `:1068`, `:1775` gain `size`; comments; new L1)
  superseded by OR141.a (4) (b) (the driver never calls `uart.readline()`: a line is read from the DMA ring by index) and
  OR143.a (2) (the readline cap) — A-C review fold.
- **Site**: `tests/test_asy_uart_driver.py:1040-1070`, `:1628-1660`, `:1670`, `:1770-1785`, `:1873`.
- **Change**: the readline tests feed their lines through the fake link and assert the lines returned (`:1040-1070`,
  `:1628-1660`, `:1872-1880` keep their goals: a multi-part line, an empty read, no probe of an empty buffer); the
  `patched_readline()` (`:1068`) and `no_readline()` (`:1775`) stand-ins go (the driver calls no `uart.readline()`;
  guard: `rx_api_calls == 0`, M.TEST_UNIT.344); the "no count to clamp" comments at `:1629`, `:1648`, `:1670`, `:1873`
  → "read from the ring by index, never through the FIFO API". The clamped-rounds test is not written (no `readline()`
  request exists to clamp); the cap's cases are M.TEST_UNIT.344 (d).
- **Resolved**: —
- **Unit**: U13.
- **Depends**: M.SRC_NET.202 (as the fold reworks it for the ring); [fold F25 M_SRC_NET]; M.TEST_HELP.069.
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.176 Delimited reads: yields, discard counts, exact codec size, deinit races
- **From**: A.U13.14 (`:600-676` hold; new L1), A.U17.13 (new L1s), A.U17.22 (`:514`, `:600-603`, `:678` hold; new L1),
  A.U13.18 (new L1), A.U13.19 (new L1); OR141.a (4) (f) (readiness from the ring's fill level; A-C review fold).
- **Site**: new tests in the B2 and never-raises sections.
- **Change**: `test_a_run_of_delimiters_lets_another_task_run` (64 delimiters then a frame: a counter task runs ≥ 4 times
  before the frame returns); discard-count cases on `discarded_bytes` — a mid-frame timeout adds the partial length, a
  CRC16 failure the whole frame, a COBS decode failure the consumed bytes, a start timeout 0, a good frame nothing, and
  a count set near `COUNTER_CAP` wraps without passing it; `test_an_exact_size_codec_delivers_a_full_frame`
  (`cobs_uart(max_frame=<frame + CRC>)` through `readinto_until_complete()`); `test_a_deinit_during_readys_closing_yield_hands_back_no_dead_uart`
  (a ready round — the fake DMA's fill level stepping from 0 to a frame — followed by a task calling `deinit()`: `read()`, `readinto_until_complete()`,
  `write()` return `None`/`False` and the fake logs nothing after the deinit; the same for `_read_delimited()` with a
  COBS codec after 16 bytes); `test_an_idle_wait_beyond_the_ticks_range_returns_false`: `poll_idle_ms = 2**61` (the rig's
  half-period: `ticks_add()` refuses a delta ≥ period/2, `extmod/modtime.c:191-192`, and the 64-bit Unix port's period is
  2**62, SPEC F.1); first assert the precondition `time.ticks_add(time.ticks_ms(), 2**61)` raises `OverflowError` on this
  interpreter (else the test fails naming the rig, never passes vacuously); then a ring empty on the first round and
  holding a frame on every later one (so the round reaches `asyncio.sleep_ms(poll_idle_ms)`):
  `ready(timeout_ms=-1)` returns `False` without raising — the arm answers before the second poll, which would have
  reported ready; without the `OverflowError` arm the sleep's raise fails the test.
- **Resolved**: A.U13.19's `2**29` is outside rp2's range (period 2**30) but inside the Unix rig's (2**62), so on the rig
  the sleep raised nothing and the never-ready poller returned `False` without reaching the degrade path the test is
  named for (SPEC merge hand-back, late gap 3; M_SPEC gap 3). The rig's half-period and a ring holding a frame from its
  second round (a poller ready on its second poll before the DMA receive path) make the test reach that path; F.8.2's rp2 sentence (M.SPEC.108) is unchanged (gap pass G3, 2026-10-01).
- **Unit**: U17 (stage U13).
- **Depends**: M.SRC_NET.196, .199, .200, .201; M.TEST_HELP.069 (the fill-level stepping, U13).
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.177 Cancellation at every await of a session and of ready()
- **From**: A.U35.48.
- **Site**: new test in `tests/test_asy_uart_driver.py`.
- **Change**: `test_cancelling_a_session_at_each_await_releases_the_lock` drives `cancel_at_each_await()` from
  synchronous scope over a locked `read_until_complete()` and a `write()` on `make_uart()` (its `_StepPoller` bounded);
  invariants: `session_lock` unlocked, `cancel_unacknowledged` unchanged, no `read`/`write` logged after the
  cancellation.
- **Resolved**: —
- **Unit**: U35.
- **Depends**: M.TEST_HELP.067.
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.344 The DMA receive ring: unit and hammering tests; the capped readline
- **From**: OR141.a (4) (b)-(d), (f), (g) (the receive path through a DREQ-paced DMA ring: count reload and modular wrap,
  a frame split across the ring end, a lap read as an overrun, the mask cleared after every init, the refusals, zero
  allocation per read; hammering), OR143.a (2), (4) (`readline_until_complete()` capped, no growth by concatenation,
  over the cap the line discarded with a logged error), FOLD_BRIEF F25/F27 (U13) — A-C review fold.
- **Site**: new sections in `tests/test_asy_uart_driver.py`; the file's existing receive tests.
- **Change**: (a) The file's existing receive tests run on the DMA model (M.TEST_HELP.069): bytes fed through the fake
  link or the RX FIFO reach the driver through the ring; a test that scripted readiness with `_StepPoller` scripts the
  fake DMA's arrival instead (`_StepPoller` stays only where the transmit side still polls); a test asserting receive-side
  `read`/`readinto`/`readline` entries in the fake log asserts the bytes it returns instead — M.TEST_UNIT.169, .175 and
  .176 carry their specifics. (b) New unit cases: `test_every_init_clears_the_rx_interrupt_mask_and_enables_rx_dma`
  (after `setup()` and after each re-`init()` the driver makes: UARTIMSC RXIM/RTIM clear, UARTDMACR RXDMAE set);
  `test_the_receive_path_never_touches_the_fifo_api` (a run of reads, readlines and waits: `rx_api_calls == 0`, the
  `machine.UART` rxbuf at its minimum, 32); `test_progress_is_read_from_the_transfer_count_only` (the fake's E12-stale
  `WRITE_ADDR` never changes a result); `test_the_count_reload_keeps_reception_going` (the paced channel's count driven to
  0: the chained channel reloads it, no byte lost, the reload value ≤ 2**30 − 1 so `count` is a small int);
  `test_the_fill_level_is_the_modular_difference_of_totals` (totals across the count's wrap); `test_a_frame_split_across_
  the_ring_end_reads_whole` (a frame whose bytes straddle the last ring byte, every codec and CRC mode); `test_a_lap_is_an_
  overrun_never_data` (more unread bytes than the ring holds: the read reports the overrun, counted, and no lapped byte
  is returned); the refusals (a ring size not a power of two or outside 2-32768, a misaligned ring — each refused with the
  driver's code, no channel armed; the size floor is the link's, M.TEST_UNIT.345/.155); `test_a_read_allocates_nothing`
  (after a warm-up read, `gc.mem_alloc()` does not rise across 1 000 frame reads copied by index into the frame buffer —
  measured in the `-1` stage run, holding at 32768; no in-body `gc.threshold`); `test_the_ring_is_allocated_once_in_setup`
  (its identity unchanged across a task restart and re-`init()`); `test_ready_keeps_its_yield_and_rates_on_the_fill_level`
  (`ready()` yields once per round and polls at `poll_wait_ms`/`poll_idle_ms`, reading the fill level). (c) Hammering:
  `test_thousands_of_back_to_back_frames_at_line_rate_lose_nothing` (5 000 frames at 11.52 B/ms with the ring held at its
  fill boundary by the consumer's pacing: every frame intact, no overrun) and `test_random_consumer_stalls_within_and_
  beyond_the_bound` (stalls drawn from a seeded generator — file-local until U24, then `FixedRandom` (M.TEST_HELP.059) —
  up to and past the ring's time bound:
  zero loss within it, one detected overrun per stall beyond it, the link back in step after). (d) The readline cap
  (OR143.a (2)): `test_a_line_over_the_cap_is_discarded_and_logged_once` (`None`, one error entry by its catalog name, the
  next line returned intact); `test_a_line_at_the_cap_is_returned`; `test_a_line_arriving_in_fifty_pieces_allocates_no_
  more_than_one_arriving_whole` (`gc.mem_alloc()` deltas compared: no growth by concatenation). Tunables tagged per the
  file's convention (U8's N.1 rule).
- **Resolved**: —
- **Unit**: U13 (with the driver's receive path and the fakes; the readline cap is OR143.a's U13 part); stage U24: the
  shared `run()` and `FixedRandom` replace the file-local forms (M.TEST_UNIT.168's harness stage).
- **Depends**: [fold F25 M_SRC_NET] (the DMA receive path), [fold F27 M_SRC_NET] (the readline cap); M.TEST_HELP.069;
  M.TEST_HELP.043, .059 (U24 stage).
- **Blast carried by**: the comm-level ring floor and lap → M.TEST_UNIT.345; L2 → M.TWIN.130, .171; bench → C.
- **Kind**: test

## tests/test_asy_uart_link_driver.py

### M.TEST_UNIT.178 Harness bounds imported; local pair asserts setup and takes a CRC
- **From**: GAP-T1 (M.TEST_HELP.023/.024), A.U8C.19 (`:25`, `:26`, `:29`, `:58` imported; `:151`, `:370` tagged),
  A.U8C.03 (importer), A.U24.08 (`:29-31`), A.U24.31 (`:71-74`, 8 callers), A.U24.15 (`:43` comment), A.U13.17
  (`:38-39`, `:78` idle rate), A.U17.20 (read: this file polls at 1), A.S0930.03 (`Pair`/`build_pair` gain `crc`; the
  byte-moving tests run in both modes), A.U10.37/A.U10.38 (names), A.U24.73 (`Any`).
- **Site**: `tests/test_asy_uart_link_driver.py:1-75`, `:151`, `:370`, and the byte-moving tests `:163, :175, :188, :200,
  :227, :236, :247, :357`.
- **Change**: imports `from _async_harness import run`; `from _uart_comm_harness import LISTENER_DRAIN_S,
  POLL_WAIT_MS, RUN_LIMIT_S, TIMEOUT_MS`; `from asy_uart_link_driver import UARTLinkDriver`; `from asy_print_log import
  LogConfig, make_logger`; `from asy_crc_checks import CRC16`. The local `PAYLOAD_SIZE = 8` stays (the exerciser's own
  test size); `TIMEOUT_MS`/`POLL_WAIT_MS` and `run()` local definitions go; every `run(x)` → `run(x, RUN_LIMIT_S)`;
  `:58` `wait_for(listener, 5)` → `wait_for(listener, LISTENER_DRAIN_S)`. `# @tunable l1.asy_uart_link_driver_round_poll_s =
  0.005` / `_ROUND_POLL_S = 0.005` (`:151`) and `# @tunable l1.asy_uart_link_driver_ticker_step_ms = 1` / `_TICKER_STEP_MS
  = 1` (`:370`). `Pair(payload_size, timeout, crc=None)` builds both `UART(…, poll_wait_ms=POLL_WAIT_MS,
  poll_idle_ms=POLL_WAIT_MS, crc=crc() if crc else None)` and `UARTLinkDriver(…)`; its poller comment → "# Bounded
  stand-in, never a real select.poll(): the fake's readiness must be scripted, not polled in real time (CLAUDE.md "Known
  hang cause")."; `build_pair(payload_size, timeout, crc=None)` → `assert await pair.setup(), "Pair.setup() failed - both
  roles must be ready before the test's own assertions mean anything"`. The eight byte-moving tests become `_check_*`
  functions registered per mode by a file-local `_register_both_crc_modes()` (`("nocrc", None), ("crc16", CRC16)`, names
  suffixed `_nocrc`/`_crc16`), the shape of `tests/test_uart_comm_hazard.py`'s (copied: the harness owns the protocol
  layer's). Every `test_*` constructing `UART(…, poll_wait_ms=POLL_WAIT_MS)` adds `poll_idle_ms=POLL_WAIT_MS`.
- **Resolved**: A.U8C.19 imports `_LISTENER_DRAIN_S`/`_RUN_LIMIT_S`; M.TEST_HELP.024 published them without the
  underscore (D5 there), so this file imports the public names (GAP-T1).
- **Unit**: U24 (stages U8C, U10, U13; A.S0930.03 in U24).
- **Depends**: M.TEST_HELP.023, .024, .043; M.SRC_NET.211, .213.
- **Blast carried by**: Part N rows → A.U8.01 (SPEC).
- **Kind**: test

### M.TEST_UNIT.179 Constructor log object, private counters, named starters
- **From**: A.U5.02 (9 `fram=` sites → `log=`), A.U5.01 (`:334`-area `make_logger(` call), A.U5.12 (`logger=` stays),
  A.U10.38 (`UartLinkExerciser` → `UARTLinkDriver`), A.U10.35 + M_SRC_NET gap 5 (`transfers`/`failures` →
  `_transfers`/`_failures`; `_comm.get_callback` → `_comm._get_callback`), A.U32.06 + A.U10.44 (`:89-90`, `:107`,
  `:210`), A.U11.S02 (read: `:122` holds), A.U11.S03 (read: ignores kept).
- **Site**: every `UartLinkExerciser(` call; `:84-108`, `:122`, `:136-175`, `:210`, `:270-356`.
- **Change**: `UartLinkExerciser(…)` → `UARTLinkDriver(…)`; each `fram=<manager>` → `log=LogConfig(<manager>, 10,
  None)` (the inline `# type: ignore[arg-type]` moves with the fake manager to that argument); `make_logger(_FakeFramManager(),
  name="UART_fram_test")` → `make_logger(LogConfig(_FakeFramManager(), 10, None), "UART_fram_test")`; `logger=owner.pr`
  stays. Every `.transfers`/`.failures` → `._transfers`/`._failures` (the `_one_exercise_round` poll included);
  `pair.responder._comm.get_callback = …` → `pair.responder._comm._get_callback = …` (its trailing comment kept). The
  initiator starter test asserts `initiator.get_task_starters() == [initiator.start_asy_exercise]` before calling it;
  the responder's asserts `== [responder._comm.start_asy_listen]`; `:210` calls `pair.responder.get_task_starters()[0]()`
  unchanged; the `:89` comment's `UART_Comm` → `UARTComm`.
- **Resolved**: —
- **Unit**: U10 (stages U5 log object, U32 hold).
- **Depends**: M.SRC_NET.213, .215; M.SRC_CORE `LogConfig`/`make_logger` (A.U5.01).
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.180 The reset leaves the link counters; the counters cap
- **From**: A.U17.19 (`:133-140` inverts), A.U17.29 (new L1).
- **Site**: `tests/test_asy_uart_link_driver.py:133-140`; new tests after `:245`.
- **Change**: `test_reset_error_counter_also_resets_link_counters` → `test_reset_error_counter_leaves_the_link_counters`:
  `_transfers = 5`, `_failures = 2`, one `err_s` logged; after `reset_error_counter()` (returns `True`) the counters read
  5 and 2 and the comm's history is empty. New `test_the_transfer_count_stops_at_the_counter_cap` (`_transfers =
  COUNTER_CAP`, one successful `_one_exercise_round` leaves it there) and `test_the_failure_count_stops_at_the_counter_cap`
  (the same with a silent peer).
- **Resolved**: —
- **Unit**: U17.
- **Depends**: M.SRC_NET.214, .216.
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.181 The banner is read from source
- **From**: A.U24.67 (1) (`:189-195`), M_SRC_NET gap 5 (M.SRC_NET.212's `src_const` resolution).
- **Site**: `tests/test_asy_uart_link_driver.py:186-195`.
- **Change**: `assert bytes(answer) == b"dev-uart-crossover"` → `assert bytes(answer) == src_const(
  "src/asy_uart_link_driver.py", "_BANNER")` (the module's `const(b"uart-crossover")`); the comment's "(SPECIFICATION.md
  Part A.7 step 13b)" kept.
- **Resolved**: A.U24.67 asks for an import of a plain global; M.SRC_NET.212 keeps `_BANNER` a folded `const()` (A.U10.29)
  — the test reads it with `src_const` (agent decision there, carried here).
- **Unit**: U24.
- **Depends**: M.SRC_NET.212; M.TEST_HELP.044.
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.182 A refused link ends its tasks
- **From**: A.U17.07 (`:143-245` hold; new L1).
- **Site**: new test after `:245`.
- **Change**: `test_a_refused_construction_ends_every_task_for_both_roles`: for each role, an exerciser built with
  `payload_size=0` on a `LinkPoller` bus (as `Pair` builds it) — `setup()` returns `False`, `initialized is False`, every
  task its starters return is done within 200 ms (`run(…, RUN_LIMIT_S)` around a bounded wait), and its history holds
  `code("E", "UART_PAYLOAD_SIZE")` and no `code("E", "NOT_INIT")`.
- **Resolved**: —
- **Unit**: U17.
- **Depends**: M.SRC_NET.214, .215.
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.183 Optional FRAM support: section comment, fake chunk, behaviour asserted
- **From**: A.U24.45 (`:258-266`), A.U36.544 (`:310`), A.U16.19 (`:280`, `:284` keyword), A.U24.39 (`:300`), A.U10.10
  (setup before reading a persisted log: holds), A.U2.20 (read: `:252-254` seed 7 stays).
- **Site**: `tests/test_asy_uart_link_driver.py:250-392`.
- **Change**: the section comment → "# ---- Optional FRAM support: UARTLinkDriver forwards log=/logger= into UARTComm, whose
  FRAM-backed history is unit-tested in test_asy_uart_comm.py ----" plus one line naming what these cover (forwarding,
  the default, the allocation-failure fallback, the logger reach-through, a reboot roundtrip). `_FakeFramChunk.write_into`/
  `read_into` drop `override_pause`. `test_fram_kwarg_gives_the_instance_its_own_fram_backed_logger` →
  `test_a_fram_log_config_lands_entries_in_the_managers_chunk`: an `err_s` through the instance lands in the fake chunk
  and a second logger over the same manager reads it back. `test_no_fram_kwarg_stays_ram_only_exactly_as_before_wp3` →
  `test_the_default_log_stays_ram_only`, comment → "# The default (no log=) stays a RAM-only history." The `print_log`
  in-function imports move to module level from `asy_print_log`.
- **Resolved**: —
- **Unit**: U24 (stages U5, U16, U36).
- **Depends**: M.SRC_CORE `PrintLogHistoryStore` (A.U5.01, A.U16.19).
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.184 Cancellation at each await of the exercise round
- **From**: A.U35.48.
- **Site**: new test.
- **Change**: `test_cancelling_an_exercise_round_at_each_await_leaves_the_bus_unlocked` drives `cancel_at_each_await()`
  from synchronous scope over `_exercise_loop()` on a `Pair` built inside its coroutine; invariants: the initiator
  bus's `session_lock` unlocked, the comm's `_busy is False`, `_transfers + _failures ≤ 1`.
- **Resolved**: —
- **Unit**: U35.
- **Depends**: M.TEST_HELP.067.
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.185 A corrupted frame costs one failure, CRC16 only
- **From**: A.S0930.03 (new CRC16-only case).
- **Site**: new test.
- **Change**: `test_a_corrupted_frame_counts_one_failure_and_the_next_transfer_succeeds_crc16`: one payload byte flipped
  on the link (the `UARTLink` corruption knob) during one exercise round — `_failures` rises by one, the next round's
  `_transfers` rises, the banner answer intact.
- **Resolved**: —
- **Unit**: U24.
- **Depends**: M.TEST_UNIT.178.
- **Blast carried by**: SPEC J.7 tier-map row "exerciser" → A.S0930.03 (SPEC).
- **Kind**: test

## tests/test_asy_udp_socket.py

### M.TEST_UNIT.186 Tuple addresses through the moved shim; ports from the band table
- **From**: A.U18.12 (`:30-51` `make_addr()`/`resolve_addr()` and users; `:73-80` inverts; `:115-121` gains bytes),
  A.U24.70 (`_next_port = 21000` → `PortAllocator`), A.U24.76 (`AdversarialPeer`, `make_*` → private names), A.U10.38
  (`AsyUDPSocket` → `UDPSocket`), A.U10.35 (`.sock` → `._sock`), harness migration (Conventions), A.U24.73 (`Any`).
- **Site**: `tests/test_asy_udp_socket.py:1-80`, `:110-121`, `:769-774` (`unbindable_addr()`), every `make_addr()`/
  `resolve_addr()`/`.sock` use.
- **Change**: imports `from _async_harness import run`, `from _port_bands import PortAllocator`, `from asy_udp_socket
  import UDPSocket`, and the Unix-port address shim from its moved, hardware-fake-free location (A.U18.12; path per
  TWIN's merge), whose patch function is called once at module level after the imports (no `# noqa: E402`). `_PORTS =
  PortAllocator("asy_udp_socket")`; `_make_addr() -> tuple[str, int]: return (_HOST, _PORTS.next())` and `_make_port()`
  likewise, their sockaddr comments gone; `resolve_addr(host, port)` goes (callers write the tuple);
  `_unbindable_addr()` returns `("10.255.255.254", 51999)` with its first comment sentence kept. `test_init_accepts_a_
  pre_resolved_bytes_like_addr` → `test_init_rejects_a_pre_resolved_sockaddr` (a `bytes` and a `bytearray` sockaddr each
  raise `TypeError`); `test_init_rejects_addr_of_the_wrong_type_entirely` gains `b"\x00" * 16`. Every comparison of a
  received address with a pre-resolved sockaddr compares with the `(host, port)` tuple. `AdversarialPeer` →
  `_AdversarialPeer` (its own `self.sock` is a raw socket and keeps its name); every `UDPSocket` attribute read `.sock`
  → `._sock` (`:71, 562, 598-636, 680, 707-711, 811, 839, 960, 1013, 1034`); `AsyUDPSocket` → `UDPSocket` in code and
  comments.
- **Resolved**: —
- **Unit**: U18 (stages U10 names, U24 ports/names).
  A-C2 step order: A.U24.70's part lands in U25, not U24 (it follows A.U24.70's own change, which lands in U25).
- **Depends**: M.SRC_NET.026; M.TEST_HELP.043, .056; TWIN shim move (A.U18.12).
- **Blast carried by**: the shim's location and `mypy_path` → A.U18.12 (TWIN, TOOL).
- **Kind**: test

### M.TEST_UNIT.187 Tagged waits; withdrawn rows where the literal goes
- **From**: A.U8C.20 (tags), A.U8C.120 (read: Dependants), A.U8.11 (read: behaviour unchanged), A.U18.05 (`:758`, `:919`,
  `:1605` lose `wait_time_ms`), A.U18.13 (`:786` test goes), A.U35.14 (2) (`:1365`, `:1368` driven).
- **Site**: every literal line A.U8C.20 lists.
- **Change**: module constants with tags exactly as A.U8C.20 writes them for every literal that survives. No constant
  or tag for: `l1.asy_udp_socket_ready_poll_ms` (`:758`, `:919` — the `wait_time_ms` argument goes) and
  `l1.asy_udp_socket_forever_poll_ms` (`:1605`, likewise); `l1.asy_udp_socket_fix_address_after_retry_s` (`:786`, its
  test goes); `l1.asy_udp_socket_fix_address_after_s` (`:1368`, driven time); `l1.asy_udp_socket_retry_cycle_min_ms`
  (`:1350`, derived from the product backoff, M.TEST_UNIT.190). `_FIRST_ATTEMPT_S = 0.1` keeps its tag for `:1340`,
  `:1394`, `:1423`; `:1365` (the driven test) no longer uses it.
- **Resolved**: A.U35.14 withdraws `l1.asy_udp_socket_first_attempt_s` with its test's literal, but three other tests
  keep the 0.1 s park — the row stays for them (Conventions: a literal a later constituent deletes takes no tag, every
  other tagged literal keeps its constant; agent decision D-T17).
- **Unit**: U8C (stages U18, U35 withdrawals).
- **Depends**: —
- **Blast carried by**: Part N rows (kept and withdrawn) → A.U8.01/A.U35.14 (SPEC).
- **Kind**: test

### M.TEST_UNIT.188 One connect attempt per call; constructor without retries
- **From**: A.U18.13 (`:64-70`; `:122-148`; `:777-797` goes; `:799-820` renamed; `:1237-1270` goes; `:1330-1340` one
  backoff), A.U31.16 (read: `:786` comment goes with its test; `:519-530` recorder unchanged).
- **Site**: `tests/test_asy_udp_socket.py:64-148`, `:769-820`, the fifth-pass `_connect` tests (`:1194-1270`).
- **Change**: `test_init_accepts_every_valid_mode_and_conn_tries_combination` → `test_init_accepts_every_valid_mode`
  (both modes; `_mode`, `connected is False`, `_sock is None`); `test_init_rejects_non_int_conn_tries` goes and the three
  combined-invalid cases drop `conn_tries=` (each still mixes two or more invalid arguments: addr and mode).
  `test_conn_tries_retries_within_a_single_connect_call` goes — the property no longer exists; guard named: the
  renamed self-heal test below (one attempt, then a fresh one). `test_connect_self_heals_after_conn_tries_exhausted` →
  `test_connect_self_heals_after_a_failed_bind` (one failed attempt, `_sock is None`, then a fresh successful one on the
  next call), its comment's "fully-exhausted conn_tries" → "a failed attempt". `test_connect_self_heals_when_conn_tries_
  mutated_to_a_non_int` goes (no attribute); the section comment "_addr/_conn_tries" → "_addr". Every `conn_tries=N`
  construction drops the argument.
- **Resolved**: —
- **Unit**: U18.
- **Depends**: M.SRC_NET.026, .027.
- **Blast carried by**: the doubles mirroring the signature → M.TEST_UNIT.025 (DNS), M.TEST_UNIT.103/.111 (NTP).
- **Kind**: test

### M.TEST_UNIT.189 ready(): two rates through the recorder; wait_time_ms gone
- **From**: A.U18.05 (`:513-531` renamed; `:758`, `:919`, `:1605` drop the argument; `:1561-1575` goes; `:1538`
  comment; `:905-930` rewritten; new L1; `:168-173, 234-235, 383` margins re-checked), A.U10.26 (new L1: a bounded
  `ready()` leaves no runner), A.U24.59 (`:494-496` comment), A.U18.17 (`:970-994` holds).
- **Site**: `tests/test_asy_udp_socket.py:483-531`, `:739-760`, `:897-930`, `:1538-1610`.
- **Change**: `_RecordingAsyncio` comment → "# asyncio is a frozen Python package whose attributes tests may assign
  (test_asy_bmp3xx_driver.py patches asyncio.sleep); this wraps it instead so the recording also sees ready()'s own
  sleep_ms() calls through asy_udp_socket's module-level name, the way _RaisingSocketModule replaces the read-only C
  `socket`." (≤ 3 lines). `test_ready_default_wait_time_ms_does_not_busy_spin` →
  `test_ready_with_a_deadline_polls_at_the_transaction_rate` (`timeout_ms=_READY_EMPTY_TIMEOUT_MS`; every recorded sleep
  equals `src_const(_UDP, "_POLL_WAIT_MS")`). New `test_ready_without_a_deadline_polls_at_the_idle_rate` (a task over
  `ready(POLLIN)` with no deadline, cancelled after two recorded rounds: every recorded sleep equals `_POLL_IDLE_MS` read
  the same way). `test_ready_wait_time_ms_is_milliseconds_not_seconds` → `test_ready_sleeps_milliseconds_not_seconds`
  (through the recorder: the recorded values are the two constants, 20 and 100, not 0.02/0.1). The `wait_time_ms=`
  arguments at `:758`, `:919`, `:1605` go; `test_ready_returns_false_sentinel_for_a_malformed_wait_time_ms` goes (no
  parameter; guard: the malformed-`timeout_ms` and malformed-mask tests); the sixth-pass section comment loses
  `wait_time_ms`. New `test_a_bounded_ready_leaves_no_poll_task_behind` (`ready(timeout_ms=50)` on a never-ready poller
  returns `False` and no task is left runnable afterwards — the after-each queue check). The three real-socket tests
  waiting with no deadline keep their ≥ 300 ms datagram margins (re-checked against the 100 ms idle rate).
- **Resolved**: —
- **Unit**: U18 (stage U10 `_poll()`).
- **Depends**: M.SRC_NET.028; M.TEST_HELP.044.
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.190 Connect-lock concurrency under one attempt and driven time
- **From**: A.U18.13 (`:1330-1340` one backoff), A.U35.14 (2) (`:1354-1382` `DrivenTime`), A.U8C.20.
- **Site**: `tests/test_asy_udp_socket.py:1265-1370` (the fifth-pass concurrency tests).
- **Change**: `test_disconnect_no_longer_crashes_a_concurrent_in_flight_connect_retry`: constructions drop
  `conn_tries`; its comment's "bounded by conn_tries * the backoff" → "bounded by one backoff"; `assert elapsed >= 1000`
  → `assert elapsed >= src_const(_UDP, "_RETRY_BACKOFF_MS") - int(_FIRST_ATTEMPT_S * 1000)` with "# disconnect() waited
  out the one backoff the failed attempt holds the lock for"; the upper bound keeps `_RETRY_CYCLE_MAX_MS`.
  `test_concurrent_caller_joins_an_in_flight_connect_instead_of_a_premature_none`: `DrivenTime` installed on
  `asy_udp_socket` (restored in `finally`); the fixer sets `sock._addr` once `run_until()` sees A's first failed attempt
  counted, then `advance(500)`; assertions unchanged. The two cancellation tests drop `conn_tries` and hold.
- **Resolved**: —
- **Unit**: U35 (stage U18).
- **Depends**: M.SRC_NET.027; M.TEST_HELP.065.
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.191 write_and_recvfrom(): tries required; a failed send is not waited out
- **From**: A.U18.14 (calls omitting `tries` pass `tries=1`; `:217-260`, `:1054-1140`, `:1524-1535`, `:1640-1650` hold; new
  L1), A.U18.16 (read: `:1054-1140` builds its own replies).
- **Site**: every `write_and_recvfrom(` call; new test after `:260`.
- **Change**: every call without `tries` passes `tries=1`. New `test_a_failed_send_returns_without_waiting_for_a_reply`
  (`asy_udp_socket.socket` replaced by the `_RaisingSocketModule` technique with a `send` that raises `OSError`:
  `write_and_recvfrom(b"x", 64, timeout_ms=400, tries=1)` returns `(None, None)` in under 200 ms).
- **Resolved**: —
- **Unit**: U18.
- **Depends**: M.SRC_NET.029.
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.192 The adversarial peer reads by event; the context-manager tests go
- **From**: A.U24.33 (`:286-295`), A.U18.46 (`:998-1030` go), A.U36.544 (`:399`).
- **Site**: `tests/test_asy_udp_socket.py:286-295`, `:395-401`, `:996-1030`.
- **Change**: `_AdversarialPeer.recv()`: `for _obj, event in poller.ipoll(0): if event & select.POLLIN: return
  self.sock.recvfrom(bufsize)` before the timeout check and the `_PEER_POLL_MS` sleep; `poller.unregister(self.sock)` in
  a `finally` (a real poll on a real socket, not a fake stream). Every `.recv(` user is re-derived: a test that passed
  because `recv()` raised `EAGAIN` into an expected-failure path now receives and states what it receives. `:399`'s
  "BACKLOG.md's open question 5" → "(SPECIFICATION.md F.1, UDP on rp2/lwIP)". The "async with support" section and its
  two tests go (the context manager is removed; guard: `test_disconnect_is_idempotent_and_resets_state` covers teardown).
- **Resolved**: —
- **Unit**: U24 (stages U18, U36).
- **Depends**: M.SRC_NET.031.
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.193 Cancellation at each await of connect and ready
- **From**: A.U35.48.
- **Site**: new test.
- **Change**: `test_cancelling_connect_or_ready_at_each_await_leaves_the_lock_free` drives `cancel_at_each_await()` from
  synchronous scope over `_connect()` against `_unbindable_addr()` and over `recvfrom()` with no deadline; invariants:
  `_connect_lock` unlocked, `_sock is None or connected`, a following `_connect()` to a good address succeeds.
- **Resolved**: —
- **Unit**: U35.
- **Depends**: M.TEST_HELP.067.
- **Blast carried by**: —
- **Kind**: test

## tests/test_asy_webserver_service.py

### M.TEST_UNIT.194 Imports, harness, typed Microdot, strict response parsing, tagged waits
- **From**: A.U8.23 (`:17` ignore goes), A.U24.08 (`run`, `run_timed`), A.U24.60 (85 `json.loads(` of response bodies →
  `strict_loads(`), A.U10.37/A.U10.38 (`config_manager` → `asy_config_manager`), A.U24.73 (39 `Any` lines), A.U19.17
  (read: fakes typed against the Protocols hold; `_make_service(**kwargs)` stays the one `Any`-free forwarder), A.U8C.21,
  A.U8C2.05 (tags), A.U8.17 (`:1285`, `:1835`), A.U2.19/A.U2.03 (catalog names, 26 lines), A.SDEP.06/A.SDEP.07 (read:
  re-vendored Microdot and freezefs; `:16`, `:1848` hand-built `VfsFrozen` re-checked), A.U36.544 (`:1102`, `:1591`,
  `:2377-2431` pointers).
- **Site**: `tests/test_asy_webserver_service.py:1-50`; every response `json.loads(`; the literal lines A.U8C.21/A.U8C2.05
  list; `:1102`, `:1591`, `:2377-2378`, `:2410-2411`, `:2430-2431`.
- **Change**: imports: `from _async_harness import run, run_timed`; `from _strict_json import strict_loads`; `from
  _error_codes import code`; `from microdot import Microdot, Request, Response` without its `type: ignore` (the vendored
  stub types it); `import asy_config_manager as cm`; `from asy_webserver_service import ROUTES, RouteSources,
  ServingLimits, SettingsGroup, StaticSite, WebserverService, _PieceWriter, _shape_errcount_entry, _stream_dict_response,
  _TimeoutStreamProxy`; the local `run`/`run_timed` go (`run_timed(coro, 5.0)` keeps its bound as `_RUN_BOUND_S`).
  Every `json.loads(<response body>)` → `strict_loads(…)`; request-body JSON the test writes is not a response and keeps
  `json.dumps`. Module constants and tags exactly as A.U8C.21 and A.U8C2.05 list; `:1285` → `timeout_s=outer_cap *
  _SERVE_BACKSTOP_CAP_MULT` (`# @tunable l1.serve_backstop_cap_mult = 20`), `:1835` → `_LEAK_SCENARIO_TIMEOUT_S`
  (`# @tunable l1.webserver_leak_scenario_timeout_s = 60.0`). Every bare errno/wrnno in an assertion → `code(…)` by the
  catalog name of M.SRC_NET.112 (e4 → `UNEXPECTED`, e6/e3/e5 → `CALLBACK`, …). `:1102` "CLAUDE.md Part F" →
  "SPECIFICATION.md A.8"; `:1591` "Step 6 (silent-failure-masking finding):" goes; the three comments naming
  `test_h2_stream_yields_many_small_chunks_not_one_precomputed_buffer()` name
  `test_h2_stream_yields_one_piece_per_top_level_section_not_one_precomputed_buffer()`. `Any` → the A.U24.73 scheme.
- **Resolved**: —
- **Unit**: U24 (stages U8 tags, U10 names, U19 typed Microdot, U36 pointers).
- **Depends**: M.SRC_NET.110, .112; M.TEST_HELP.043, .045; TEST_HELP `_strict_json.strict_loads` (A.U24.60).
- **Blast carried by**: `tests_scripts/test_microtest.py` `json.loads(` allow-list → A.U24.60 (TSC); Part N rows →
  A.U8.01 (SPEC).
- **Kind**: test

### M.TEST_UNIT.195 Fakes: declared surface, nested config, bool reset, reader `read()`
- **From**: A.U24.18 (`:52-56` comment; `_FakeModule`/`_FakeLogger` surface ⊆ the real classes'), A.U10.36
  (`_FakeModule.get_dict_cfg()` nested), A.U11.31 (`_FakeLogger.reset()` → `True`; `_FakeModule.reset_error_counter() ->
  bool`), A.U19.07 (reader fakes gain `read(n)`), A.U11.S03 (read: wider `err_s`/`wrn_s` signatures hold), A.U10.40
  (`NTP_Host` → `NTPHost` in fake schemas), A.U19.05 (`:2085`, `:2170`, `:2200` comments).
- **Site**: `tests/test_asy_webserver_service.py:52-241`, `:396-416`, `:1345-1358`, `:1647-1653`, `:3089-3091`, and the
  fake schemas naming `NTP_Host`.
- **Change**: section comment `:52-56` → "# Registered-module doubles. Their public surface is the real classes' (SensorReaderConfig,
  PrintLogHistory) — tests_scripts/test_fake_surface_conformance.py checks it; anything test-only is listed in TEST_API."
  (≤ 3 lines); `_FakeModule`/`_FakeLogger` gain `TEST_API` (`set_calls`, `reset_calls`, `history` …) and lose any method
  the check flags. `_FakeModule.get_dict_cfg()` returns `{self.name: dict(self._values)}` (make_dict's shape); every
  test reading `run(mod.get_dict_cfg())["X"]` reads `[mod.name]["X"]`. `_FakeLogger.reset()` returns `True`;
  `reset_error_counter() -> bool` returns it. `_NestedCfgModule`'s comment loses the "two real production bugs" history:
  "# make_dict()'s {name: {field: value}} shape, what every module's get_dict_cfg()/get_dict_data() returns." Reader
  fakes gain `async def read(self, n: int) -> bytes`: `_ScriptedReader` returns up to `n` bytes after one `_pull()`
  (`b""` at EOF), `_HangingReader` hangs, `_ClosedReader` returns `b""`, `_ResetReader` raises `OSError(104)`;
  `_BodySizeReader`/`_ResetDuringBodyReader` keep their `readexactly()` overrides. Fake schemas `NTP_Host` → `NTPHost`.
  The three `_serve_static()` comments name `_StaticRoutes.serve()`.
- **Resolved**: —
- **Unit**: U24 (stages U10, U11, U19).
- **Depends**: M.SRC_NET.111, .116, .118, .124.
- **Blast carried by**: the conformance L0 → A.U24.18 (TSC).
- **Kind**: test

### M.TEST_UNIT.196 The builder makes the three config objects; millisecond attributes
- **From**: A.U5.04 (`_make_service()` builds `RouteSources`/`ServingLimits`/`StaticSite`; its 153 call sites stay),
  A.U5.02 (`history_length=` → `log=LogConfig(None, n, None)`), A.U5.05 (defaults read from the constants), A.U8.04
  (`:255`, `:1362`, `:1954`, `:2469`, `:2501` mirror the shipped defaults), A.U31.18 (`:1673` `1.0` → `1000`; `:1974`
  `_ms`), A.U19.06 (request builders pass `sock=`).
- **Site**: `tests/test_asy_webserver_service.py:251-268`, `:1362`, `:1673`, `:1954`, `:1974`, `:2469`, `:2501`.
- **Change**: `_make_service(**kwargs)` splits its keywords into `RouteSources(sensors, settings, build_info, system_cmd,
  notification_led, notification_pause, status_sources, maintenance_sensors, error_sources)`, `ServingLimits(…)` and
  (when `static_mount` is given) `StaticSite(mount, index, is_hotspot_active)`, maps `history_length=n` to
  `log=LogConfig(None, n, None)`, and calls `WebserverService(app, routes, serving, static, log)` then `run(service.setup())`;
  its defaults read the constants: `max_content_length = src_const(_WS, "_DEFAULT_MAX_CONTENT_LENGTH")` (comment "tracks
  the shipped default"), `chunk_bytes = src_const(_WS, "_DEFAULT_CHUNK_BYTES")`, the test-tier tiny bounds unchanged.
  `_BODY_CAP`, `_WIRE_CHUNK_BYTES`, `_HAMMER_PIECE_BUDGET` and `_written()`'s `max_bytes` default read the same two
  constants (their "restated: a const() is not a module attribute" comments go). `_make_request()` passes
  `sock=(_NoopHolder(), _NoopHolder())` (a one-method `hold()` fake). `:1673` → `_TimeoutStreamProxy(writer, 1000,
  _FakeLogger("X"), [False], [False])`; `:1974` → `service._per_call_timeout_ms, service._outer_cap_ms = 2000, 4000`.
- **Resolved**: —
- **Unit**: U24 (stages U5 objects, U8 mirrors, U19 sock, U31 ms).
- **Depends**: M.SRC_NET.112, .118, .119; M.TEST_HELP.044.
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.197 Unknown keys answer Invalid; dispatch keys are never double-reported
- **From**: A.U19.01 (`:356-362`; `:847-853`; new L1s), A.U11.26 (hook-failure tests see "Failed" from the envelope),
  A.U27.07 (`:877` rename), A.U10.40 (keys).
- **Site**: `tests/test_asy_webserver_service.py:356-470`, `:839-937`.
- **Change**: `test_sensors_put_unknown_sensor_key_ignored` → `…_answers_invalid`: `result == {"BOGUS": "Invalid"}`,
  `scd.set_calls == []`. `test_b_unknown_top_level_key_silently_ignored_on_every_settings_endpoint` →
  `…_answers_invalid_on_every_settings_endpoint`: `body["result"]["Bogus"] == "Invalid"`, `res == "OK"`.
  `test_b_malformed_json_body_handled_like_the_legacy_parse_cmd_request_path` → `test_b_malformed_json_body_answers_code_1`.
  `test_networking_put_raising_post_fct_marks_every_attempted_field_in_that_group_failed` holds (now from the envelope
  itself); its comment → "# A raising post hook marks every field of its group "Failed" (handle_set_cmd(), SPEC
  H.6)." `NTP_Host` → `NTPHost`. New `test_a_non_object_sensor_entry_answers_invalid` (`PUT /sensors {"SCD30": 5}` →
  `{"SCD30": "Invalid"}`), `test_a_dispatch_key_is_answered_once` (`PUT /system {"SystemCmd": "reboot", "Bogus": 1}`:
  `SystemCmd` from the dispatcher, `Bogus` "Invalid"), `test_status_put_answers_unknown_keys` (`{"ResetErrors": true,
  "X": 1}` → `{"ResetErrors": "Valid", "X": "Invalid"}`).
- **Resolved**: —
- **Unit**: U19 (stages U10, U11, U27).
- **Depends**: M.SRC_NET.120, .123.
- **Blast carried by**: per-device `PUT /networking {"NoSuchKey": 1}` → A.U19.01 (TEST_HELP `_sensortask_scenarios.py`).
- **Kind**: test

### M.TEST_UNIT.198 SystemCmd: exact words only
- **From**: A.S0930.21 (`:520-590`; new L1), A.S0930.09 (`:520-541` holds), A.U19.04 (`:520-556` hold; new L1).
- **Site**: `tests/test_asy_webserver_service.py:514-586`; new tests.
- **Change**: the existing SystemCmd tests hold. New `test_system_put_systemcmd_runs_only_on_the_exact_action_word`: the
  near-miss list of A.S0930.20 (4) (prefixes, case variants, padded and aliased words) as JSON bodies → "Invalid" and the
  fake callback records no call; `"resetconfig"`/`"erasefram"` → one call each with that exact word, "Valid" for a `True`
  return, "Failed" for `False`, "Failed" plus one `code("E", "CALLBACK")` for a raise.
  `test_system_put_systemcmd_non_string_values_are_invalid` (`1`, `["reboot"]`, `{"x": 1}`, `null`, `true` → "Invalid",
  no call).
- **Resolved**: —
- **Unit**: U19 (stage S0930 words).
  A-C2: "S0930" is not a unit; its parts land in the units SUPP_owner_0930 states: A.S0930.09 in U19, A.S0930.21 in U24.
- **Depends**: M.SRC_NET.121.
- **Blast carried by**: L0 mirror of the word list → A.S0930.20 (TSC).
- **Kind**: test

### M.TEST_UNIT.199 Notification dispatch: LightCmdLED members and the pause through schemas
- **From**: A.U19.02 (`:660-670`, `:791-800`, `:804-821` fakes; `:674`; new L1s), A.U19.03 (`:705-717` hold; new L1),
  A.U10.40 (`lightCmdLED` → `LightCmdLED`, `r/g/b/t` → `R/G/B/T`), A.U1.25 (`:742` comment), A.U9.09 (read: `:742` wording).
- **Site**: `tests/test_asy_webserver_service.py:646-825`.
- **Change**: every `"lightCmdLED"` → `"LightCmdLED"` with members `R/G/B/T`; the fake `notification_led(payload)` →
  `notification_led(r, g, b, t)` recording tuples; `:674` → `led_calls == [(10, 20, 30, 5.0)]`. `:742` "(modules/
  sensortask-wozi.py)" → "(the legacy firmware's sensortask module, legacy/firmware/modules/)". New
  `test_a_malformed_led_command_is_invalid_and_never_dispatched` (missing `T`, extra `"x"`, `R` 256, `T` `True` → each
  "Invalid", callback never called); `test_an_integral_float_channel_is_coerced` (`R` `10.0` → the callback receives `int`
  10); `test_a_led_callback_returning_false_answers_failed`; `test_a_pause_time_of_the_wrong_shape_is_invalid`
  (`[60]`, `{"s": 60}` → "Invalid", callback not called).
- **Resolved**: —
- **Unit**: U19 (stages U1 path, U10 keys).
- **Depends**: M.SRC_NET.112, .122.
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.200 ResetErrors answers per source, concurrently
- **From**: A.U11.31 (`:59-90`, `:624-633`, `:635-644`, `:1019-1081` hold plus the result word; new L1s), A.U0.35
  (`:1052-1053`), A.U0.29 (`:1069`), A.U11.05 (read: `:592-604` unaffected), A.U11.S02 (read: `:1016` `==` holds).
- **Site**: `tests/test_asy_webserver_service.py:587-645`, `:967-1083`.
- **Change**: `{"ResetErrors": False}` now answers `{"ResetErrors": "Invalid"}` (still no reset); `True` answers
  `"Valid"`. `:1052-1053` → "# Both reset together by this global action (owner, 2026-09-26: global only, permanently) -
  the isolation property under test is that resetting doesn't cross-wire one module's history into another's."; `:1069`
  → "# a warning, not an error - the owner's warning-not-error rule (SPEC A.8)". New
  `test_a_failing_source_reset_answers_failed_and_the_others_still_reset` (one fake's reset returns `False`) and
  `test_reset_errors_runs_every_source_at_once` (three sources whose resets each suspend on an `Event` record that the
  others started before any finishes).
- **Resolved**: —
- **Unit**: U11 (stage U0 tags).
- **Depends**: M.SRC_NET.123.
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.201 The torn-read characterisation becomes a consistency test
- **From**: A.U19.12 (`:1108-1137`).
- **Site**: `tests/test_asy_webserver_service.py:1108-1137`.
- **Change**: `test_e_scd30_bmp3xx_live_readback_torn_read_is_a_known_characterization_not_a_regression` →
  `test_e_a_config_get_never_mixes_values_from_before_and_after_a_concurrent_put`: a real `SensorReaderConfig` subclass
  whose `_get_mgr_cfg()` reads two fields across an `await asyncio.sleep(0)` and whose `_set_mgr_cfg()` writes both with a
  yield between; `PUT /sensors` and `GET /sensors` started together through `app.dispatch_request()`; the GET body is
  all-old or all-new, never a mix. Guard named: this test (the old one pinned the gap, OR111.a (2)).
- **Resolved**: —
- **Unit**: U19.
- **Depends**: SRC_CORE config-lock read path (A.U19.12).
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.202 Connection lifecycle: every drop logged once, split timeouts, released stream
- **From**: A.U19.08 (ceiling refusals logged; peer-reset entries; seven-refusals L1), A.U2.19 (49 vs 50; new L1), A.U3.11
  (new L1: one W52), A.U24.41 (`:1590-1597`, `:1606-1611`), A.U14.03 (`:1656-1665` holds, `:1657-1658` pointer), A.SDEP.13
  (read: `:1648-1660` path re-checked at the pin), A.U19.06 (new L1s: closed stream on HEAD, raising and timed-out
  writes; `Cache-Control`), A.U3.12 (reclaim repeats spend one slot), A.U3.01; OR137.a (1)-(3) (`get_dropped_count()` is
  the 24-hour window's sum, cleared by `ResetErrors`, each drop still traced once; A-C review fold).
- **Site**: `tests/test_asy_webserver_service.py:1149-1720`, `:3052-3101`.
- **Change**: `test_f1_connections_up_to_ceiling_accepted_beyond_ceiling_silently_closed` → `…_closed_and_logged`: the
  refusal adds one `code("W", "HTTP_REFUSED")` and `get_dropped_count()` reads 1; the F1 slot-held test's refusal
  likewise. `test_close_writer_logs_a_persisted_warning_when_close_raises`/`…_when_wait_closed_raises` assert one entry,
  `ErrType` "W", `code("W", "HTTP_CLOSE_RAISED")`/`code("W", "HTTP_WAIT_CLOSED")`. `test_nothing_is_written_to_a_peer_whose_
  read_saw_a_reset` and its body-phase sibling: one `code("W", "HTTP_PEER_RESET")` (`err_count == 1`), nothing written;
  `:1657-1658` comment points to H.7.1 as A.U14.03 writes it. `test_serve_absorbs_an_eoferror_raised_directly_by_handle_
  request` → `test_an_eoferror_from_handle_request_is_an_unexpected_error` (the `EOFError` arm is gone: one
  `code("E", "UNEXPECTED")`, slot freed). `test_a_write_phase_timeout_is_logged_once_not_twice` asserts
  `code("W", "HTTP_CALL_TIMEOUT")`. New: `test_seven_refusals_count_seven_and_spend_one_slot` (`get_dropped_count()` 7,
  `ErrCount` +7, one history slot); `test_dropped_connections_leave_the_count_after_a_day` (the service's uptime source
  driven from the test: two refusals, then 23 h later still 2, 24 h later 0, a new refusal 1 — the window is the
  primitive's, M.TEST_UNIT.343); `test_reset_errors_clears_the_dropped_count` (three refusals, then the service's
  `ResetErrors` path: `get_dropped_count() == 0`, the next refusal 1); `test_an_outer_cap_timeout_logs_the_request_cap_code` (a Slowloris-paced request tripping only
  the outer cap → one `code("W", "HTTP_REQUEST_CAP")`); `test_a_close_that_raises_and_whose_wait_fails_adds_one_w52`;
  `test_repeated_reclaims_spend_one_slot` (five per-call reclaims: `ErrCount` 5, one slot);
  `test_a_head_request_closes_the_opened_static_stream`, `test_a_failed_or_timed_out_static_body_write_closes_the_stream`
  (a stub mount whose file object records `close()`), `test_a_static_get_answers_cache_control_no_cache`.
- **Resolved**: —
- **Unit**: U19 (stages U2, U3, U14, U24).
- **Depends**: M.SRC_NET.124, .126, .127, .129; [fold F02 M_SRC_NET] (the drop path counting into the window, its reset);
  M.TEST_UNIT.343.
- **Blast carried by**: twin concurrency scenarios → A.U19.08 (TWIN).
- **Kind**: test

### M.TEST_UNIT.203 Request-head bounds and the adversarial-client matrix
- **From**: A.U19.07 (adversarial matrix through `_serve()`; `:897-917` comment; class-comment wording).
- **Site**: `tests/test_asy_webserver_service.py:897-917`, `:1268-1345`; new section after `:1720`.
- **Change**: `:897-917`'s depth comment keeps its measured facts (depth 1,000 within the 2,048 B cap; the pinned
  interpreter parses 3,000). New adversarial-client tests, each through `_serve()` with `print` and
  `microdot.print_exception` captured (module attribute, test-only): `Content-Length: -1` with a 3,000 B body → shaped 400,
  no negative `readexactly`, nothing printed; `Content-Length: 99999999999999999999` → 413; `Content-Length: abc` and a
  repeated `Content-Length` → 400; a short body (`Content-Length: 50`, 20 bytes) → 400; a header line over
  `Request.max_readline`, more than 32 header lines, a head over 2,048 B, a non-UTF-8 line, a two-token request line, a
  header without `:`, any `Transfer-Encoding` → each one `code("W", "HTTP_BAD_HEAD")` and 400, nothing printed.
- **Resolved**: —
- **Unit**: U19.
- **Depends**: M.SRC_NET.118, .127.
- **Blast carried by**: L2 raw-socket case → A.U19.07 (TWIN).
- **Kind**: test

### M.TEST_UNIT.204 Server start: bounded retry, cancel closes the port
- **From**: A.U19.09 (new L1s; `:3005-3020` holds), A.S0930.18 (new L1 on a file-owned port block), A.U10.44
  (`_start_serving()`/`_run()` by name → `start_asy_serve`).
- **Site**: `tests/test_asy_webserver_service.py:1777-1802`, `:2996-3021`; new tests.
- **Change**: F8 tests call `service.start_asy_serve()` by name (`get_task_starters() == [service.start_asy_serve]`);
  `test_f8_start_serving_runs_a_real_asyncio_start_server_backed_task` binds to a port from `PortAllocator(
  "asy_webserver_service")` (the Unix port has no `getsockname()`). New `test_a_start_that_fails_twice_then_serves` (a
  fake `start_server` failing twice: two printed lines, no persisted entry, then serving; `_START_RETRY_S` sleeps through
  `FastAsyncSleep`); `test_a_start_that_fails_three_times_logs_once_and_raises` (one `code("W", "HTTP_START_FAILED")`,
  re-raised); `test_cancelling_the_serve_task_closes_the_listening_port` (real `asyncio.start_server()` on the
  file-owned port; after the cancel a fresh bind to the same port succeeds).
- **Resolved**: —
- **Unit**: U19 (stages U10, S0930).
  A-C2: "S0930" is not a unit; its parts land in the units SUPP_owner_0930 states: A.S0930.18 in U19.
  A-C2: stage U24 — until M.TEST_HELP.052/.056 exist the tests use the file's own sleep double and port allocator (the HEAD form); U24 swaps in `FastAsyncSleep` and the port-band table.
- **Depends**: M.SRC_NET.128, .129; M.TEST_HELP.052, .056.
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.205 The soak measures a leak rate, not a drop
- **From**: A.U24.64 (`:1822-1836`), A.U30.16 (read: the scenario is named in the allocation register), A.U8.17
  (`:1835`).
- **Site**: `tests/test_asy_webserver_service.py:1806-1836`.
- **Change**: after the 20-cycle warm-up, `gc.collect()` then `gc.mem_free()` at 0, 60 and 180 cycles on the same service;
  `rate = (free_60 - free_180) / 120` must be below `_LEAK_RATE_MAX_B = 8` (`# @tunable l1.webserver_leak_rate_max_b = 8`)
  with the comment (≤ 3 lines) naming the calibration: a planted 16-byte-per-cycle leak exceeds it, the healthy path stays
  under (figures recorded once in the B3 campaign). Each `gc.collect()` is followed directly by its reading; the function
  -level `import gc` moves to module level. `run_timed(scenario(), _LEAK_SCENARIO_TIMEOUT_S)`.
- **Resolved**: —
- **Unit**: U24.
- **Depends**: —
- **Blast carried by**: Part N row → A.U8.01 (SPEC).
- **Kind**: test

### M.TEST_UNIT.206 Static routes, bytes pieces and non-finite floats
- **From**: A.U19.05 (static tests through the builder), A.U19.11 (`:2497-2583` bytes; `:3021-3029`; new L1s), A.U10.27
  (new L1 NaN), A.U10.41 (`:2071-2083` the largest scalar), A.SDEP.18 (`:1977` holds), A.U19.15 (`descr` tests hold).
- **Site**: `tests/test_asy_webserver_service.py:1839-2210`, `:2497-2583`, `:3021-3048`.
- **Change**: `_written()` → `list[bytes]`; its users compare `b"".join(pieces) == json.dumps(value).encode()`; the piece
  writer tests use bytes (`[len(p) …] == [255, 256, 1, 300, 14]` over encoded fragments, `pieces == [b"x"]`); `:3021-3029`
  → `[b"abcd", b"e"]`. `test_g3_a_scalar_at_ntp_hosts_own_bound_still_makes_exactly_one_whole_piece` →
  `…_fits_one_piece`: `longest = src_const("src/asy_ntp_client.py", "_VAL_NTP_HOST")[0][4]` (253); the value and its two
  quotes (255 B) fit the 256 B cap, so no piece exceeds it and the piece holding it is whole; its comment → "# The longest
  string any schema permits (NTPHost, RFC 1035's 253), read from source." New `test_h2_piece_writer_counts_bytes_not_characters`
  (`_PieceWriter(pieces, max_bytes=4)` fed `"é"` three times → `[b"\xc3\xa9\xc3\xa9", b"\xc3\xa9"]`);
  `test_a_networking_get_with_a_multibyte_ssid_stays_bounded` (a 200-character SSID of `"€"` keeps every piece ≤ 256 B
  except the one-fragment rule); `test_h2_a_non_finite_float_is_written_as_null` (`float("nan")` → `null`).
- **Resolved**: —
- **Unit**: U19 (stages U10, U24).
- **Depends**: M.SRC_NET.114, .115, .124; M.TEST_HELP.044.
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.207 Hammers run at the process's GC stage; one test each
- **From**: A.U30.12 (`:5`, `:1466-1492`, `:2584-2593`, `:2625-2642`, `:2756-2793`, `:2822-2853`, `:2899-2916`,
  `:2949-2966`), A.U8.14 (tags on those 32768 literals withdrawn with them), A.U24.07 (read: the hook backstops the
  restores that go), A.U0.28 (`:2733`), A.U24.36 (`:2886` from `ROUTES`), A.U19.20 (new L1 route table).
- **Site**: `tests/test_asy_webserver_service.py:1464-1495`, `:2584-2970`.
- **Change**: every `orig_threshold = gc.threshold()` / `gc.threshold(<n>)` / restore goes (39 calls); the pairs collapse
  to `test_h3_hammer_concurrent_status_requests_stay_valid`, `test_i2_hammer_concurrent_measurements_requests_stay_valid`,
  `test_i2_hammer_concurrent_sensors_requests_stay_valid`, `test_i2b_hammer_concurrent_{networking,system,notification}_
  requests_stay_valid` (`_run_settings_hammer(endpoint, path)`), `test_i3_hammer_every_memory_bounded_get_route_concurrently`,
  `test_i4_hammer_measurements_and_sensors_concurrently_with_a_real_config_write`; the two F.2b tests stay two, their
  threshold lines gone. Section comment `:2590-2593` → "# Each hammer runs at its process's GC stage: scripts/test.sh runs
  every file at gc.threshold(-1) and again at 32768 (SPECIFICATION.md I.4(e)/(f))."; `:1469`'s "I.4(e) first" comment goes;
  top-level `import gc` stays only for the soak (M.TEST_UNIT.205). `:2733` "the project owner's own named top candidate" →
  "the owner's named top candidate (owner, 2026-09-07)". `_ALL_MEMORY_BOUNDED_GET_ROUTES = tuple(p for m, p, _ in ROUTES if m
  == "GET")`. New `test_the_route_table_is_registered_exactly` (Microdot's URL map equals `ROUTES`, in order).
- **Resolved**: —
- **Unit**: U30 (stages U0 tag, U8 withdrawn tags, U19 table, U24 route set).
- **Depends**: M.SRC_NET.112, .119.
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.208 Load without prints; the EAGAIN writer
- **From**: A.U19.23 (new L1), A.U19.24 (new section and `_EagainWriter` double), A.U35.28 (read: PERF gap scenario is
  TEST_HELP/TWIN's per-device library).
- **Site**: new section after `:1771`; new double beside `_ScriptedWriter`.
- **Change**: `test_client_faults_print_nothing_at_debug_level_zero`: `print` and `microdot.print_exception` replaced by a
  fake that blocks 500 ms per call (restored in `finally`); `DebugLevel` 0; for a driven 10 s (`DrivenTime`), six Slowloris
  connections, refused heads, truncated bodies, resets and ceiling refusals run against `_serve()`; the fake is never
  called and a feeder task's largest gap stays below 2,000 ms. `_EagainWriter(_ScriptedWriter)`: its `awrite()` refuses
  the first N sends as a full lwIP queue would (`None`, one round each) and then accepts; tests: a stuck write ends at the
  per-call timeout with one `code("W", "HTTP_CALL_TIMEOUT")`, the feeder's largest gap stays bounded, and the other
  concurrent requests are served intact.
- **Resolved**: —
- **Unit**: U19.
  A-C2: stage U35 — until M.TEST_HELP.065 exists the driven window runs on the file's own time double (the HEAD form); U35 swaps in `DrivenTime`.
- **Depends**: M.SRC_NET.118, .127; M.TEST_HELP.065.
- **Blast carried by**: phase-C hardware row → A.U19.23 (HW_BENCH).
- **Kind**: test

### M.TEST_UNIT.209 Cancellation at each await of serving
- **From**: A.U35.48.
- **Site**: new test.
- **Change**: `test_cancelling_a_connection_at_each_await_frees_its_slot` drives `cancel_at_each_await()` from
  synchronous scope over `_serve()` with a scripted request; invariants: `_open_conns` back to 0, the writer closed, the
  held static stream released.
- **Resolved**: —
- **Unit**: U35.
- **Depends**: M.TEST_HELP.067.
- **Blast carried by**: —
- **Kind**: test

## tests/test_asy_wifi_service.py

### M.TEST_UNIT.210 Header: schema and phases from source, the config object, shared doubles
- **From**: A.U24.01 (`:14-29` mirrors → `src_const`), A.U10.38 (`AsyConnTime` → `WifiService`), A.U10.39 (`_VAL_CTRY`/
  `_VAL_HOST`/`_VAL_LED` → `_VAL_COUNTRY`/`_VAL_HOSTNAME`/`_VAL_LED_WIFI_ON`), A.U10.40 (`LedWifiOn` → `LEDWifiOn`),
  A.U18.40 + A.U5.09 (`make_client()` builds a `WifiConfig`; `led_pin`, `wifi_refresh_sec` go; `:139-141` comment goes),
  A.U24.45 (2) (`:141-143` stale Pin reason goes; its led_pin L1s void, M.SRC_NET.078), A.U5.02 (`debug=` → `log=`),
  A.U5.07 (`ext_led` at construction), A.U24.67 (device strings), A.U24.49 (`_RaiseOnArm`, `_FastAsyncSleep` → shared; `:272-286, 2540`), A.U31.15
  (`_FastAsyncSleep` also patches `sleep_ms` and records durations), A.U8.10 (`:208` comment), A.U24.08 (`run`,
  `_cancel`), A.U24.76 (`FakeLED` → `_FakeLED`, `make_*` → `_make_*`), A.U24.73 (13 `Any` lines), A.U10.35 (`.wlan` →
  `._wlan`, `hw_op_failed` → `_hw_op_failed`, the other privatised names), A.U10.37 (`print_log` → `asy_print_log`),
  A.U28.28 (read: the `S106` per-file entry with its reason), A.U29.03 (read: the 19 `12345678` lines point at A.11).
- **Site**: `tests/test_asy_wifi_service.py:1-222`; every attribute read the renames reach.
- **Change**: imports `from asy_wifi_service import WIFI, WifiConfig, WifiService`, `from asy_udp_socket import
  UDPSocket`, `from _async_harness import run, cancel`, `from _fake_timer_arm import RaiseOnArm`, `from _fast_sleep import
  FastAsyncSleep`, `from _src_const import src_const`, `from _error_codes import code`, `from asy_print_log import
  LogConfig`. `:14-29` → `_WIFI = "src/asy_wifi_service.py"`; `_PHASE_STA_SEEKING = src_const(_WIFI,
  "_PHASE_STA_SEEKING")` … (the four), `_VAL_SSID`, `_VAL_PW`, `_VAL_COUNTRY`, `_VAL_HOSTNAME`, `_VAL_LED_WIFI_ON`,
  `_VAL_HOTSPOT_PW` read the same way, one comment line "# Read from source: const() folds them out of the module
  (tests/_src_const.py)." `_wlan(client)` returns `client._wlan` (its comment kept in substance). `_make_client(
  conn_fail_to_hotspot=5, ext_led=None, hotspot_time_min=5, max_module_error=5, cfg_path=None, debug=None)` builds
  `WifiService(WifiConfig("SensorNode", "12345678", conn_fail_to_hotspot, hotspot_time_min), ext_led=ext_led,
  max_module_error=…, cfg_path=…, log=LogConfig(None, 10, debug))` and calls `run(client.setup())`; `_make_client_with_json`
  likewise; every direct construction (`:245, 255, 2845, 2855, 2864, 2995`) passes a `WifiConfig` with both strings; the
  14 `wifi_refresh_sec=0` arguments go (each such test runs its loop under `FastAsyncSleep()`, added where missing). The
  `:208` comment's "2s+1s+1s" names `_WLAN_DOWN_SETTLE_S`/`_WLAN_DEINIT_SETTLE_S`/`_WLAN_MODE_SETTLE_S`. Every
  `LedWifiOn` key → `LEDWifiOn`; every `wlan_connect`/`time_counter`/`_watch_hotspot_timeout` call → `_connect_loop`/
  `_uptime_loop`/`_hotspot_timeout_loop` (A.U10.44); private attribute reads follow M.SRC_NET.078. Device strings used
  as test input (`"SensorStationWozi"`, `"SensorStationDev"`, `"SensorStationSomethingElse"`, `:245-3000`, A.U24.67 (4))
  → neutral values (`"SensorStationTest"`, `"SensorStationOther"`); the inline `# noqa: S106` comments go (the file's
  per-file `S106` entry carries the reason, A.U28.28; an inline one would then trip RUF100).
- **Resolved**: A.U24.45 (2) asks for `led_pin` L1s; the merged constructor has no `led_pin` (M.SRC_NET.078, ruling
  V.U18.D) — those tests are void; the stale-comment half applies.
- **Unit**: U24 (stages U5, U10, U18, U31).
- **Depends**: M.SRC_NET.072, .077, .078, .079; M.TEST_HELP.043, .044, .052, .053.
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.211 Construction, starters and the uptime tick
- **From**: A.U10.44 + A.U32.01 (starters by name), A.U18.24 (`:272-293` gain `_tick_armed is False`; new L1s),
  A.U10.03 (`:272-293` hold; `:956-998` → driven ticks; `:2609` → `get_wifi_uptime()`; new L1 delayed wake), A.U11.15
  (`:299` level accessor), A.U10.10 (`:2060-2095` both loggers in `setup()`), A.U0.35 (`:649`), A.SDEP.08 (`:440` stamp),
  A.U1.26 (`:439-440`).
- **Site**: `tests/test_asy_wifi_service.py:229-300`, `:439-462`, `:648-656`, `:952-1002`, `:2054-2110`, `:2508-2546`,
  `:2596-2612`.
- **Change**: `get_task_starters() == [client.start_asy_connect, client.start_asy_uptime, client.start_asy_hotspot_timeout]`;
  `get_timer_starters() == [client.start_uptime_timer]`; the counter-timer tests call `start_uptime_timer()`/
  `stop_uptime_timer()` and the degrade tests assert `client._tick_armed is False`. The three `time_counter()` tests
  drive `_uptime_loop()` with `_tick()` and read `get_wifi_uptime()`. `:299`'s level read follows A.U11.15's accessor
  removal (the logger's level attribute read directly). The two lazy-setup tests (`:2061-2093`) → `test_setup_runs_both_
  loggers_in_the_boot_batch` (`run(client.setup())` initialises `pr` and `_dns_server.pr`; the connect loop calls neither).
  `:649` "Project-wide decision" → "(owner, 2026-09-26)". `:439-440`'s legacy path and version stamp follow A.U1.26 and
  the pin re-check. New `test_a_failed_tick_arm_is_retried_by_the_next_loop_iteration` (a failed arm, two iterations: the
  second re-arms, or logs one `code("E", "TIMER")` if it fails again); `test_max_failed_rearms_end_the_loop`;
  `test_a_delayed_wake_advances_uptime_by_the_measured_time` (a wake 2.5 s late adds 2 s).
- **Resolved**: —
- **Unit**: U18 (stages U10, U11).
- **Depends**: M.SRC_NET.079, .094, .100, .101.
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.212 Config bounds, shapes and what GET shows
- **From**: A.U18.37 (`:307-312`, `:526-545` hold; `:2964-3016` gain "GET shows the default"; new L1), A.U6.29 (`:2893-2941`;
  `_BYTE_BOUNDS` drops Hostname; corpus L1s), A.U6.30 (`:236-238`, `:326-377` hold; corpus L1s), A.U24.56 (`:306-307`),
  A.U36.513 (`:306-307`), A.U24.61 (`:2482, 2489, 2499`), A.U10.39 (`:2487`), A.U11.24 (5 `write_config` sites), A.U24.09
  (`:2962-2975, 2988-3000, 3004-3014`; tests reading `network.country()`/`hostname()` re-derived), A.U18.39 (the mask
  resubmitted is stored and connects with `********`), A.U10.25 (push returns True for a well-typed no-op), A.U18.41
  (`:729-737` renamed), A.U32.01 (read: `:1645-1651` holds), A.U4.02 (read: hold).
- **Site**: `tests/test_asy_wifi_service.py:302-816`, `:2477-2507`, `:2841-3056`.
- **Change**: `:306-307` → "# the /networking GET masks PW (SPEC A.8)". The bound tests read the source schema
  (`_VAL_*` above). `get_cfg_schema()` replaces `.cfg_schema` reads; `test_get_cfg_schema_matches_the_public_attribute` →
  asserts equality with the source schema; each `write_config({…}, schema)` → `write_config({…})`. `:2907-2911` call
  `_radio_value_ok(field, value)`; `_BYTE_BOUNDS` loses the Hostname row; the refusal text asserted is "outside the radio's
  accepted form". Each stored-over-bound test adds that `get_dict_cfg()` shows the default in use. `:729-737` →
  `test_led_wifi_on_push_narrowing_arm_returns_false_for_a_non_bool`. New: `test_a_stored_overlong_ssid_reads_back_as_the_
  default_with_no_log` (33-byte SSID → `""`, no entry added by the GET); corpus-driven `test_every_host_label_and_country_
  case_is_judged_as_the_corpus_says` (`tests/_radio_shape_cases.json`: PUT of each reject case answers `Invalid` and stores
  nothing; a stored reject case runs on the default with one `code("W", "STORED_DEFAULT")`); `test_a_resubmitted_password_
  mask_is_stored_and_connects_with_it` (A.U18.39: the WLAN fake's `connect()` record shows `"********"`);
  `test_push_wifi_led_reports_success_for_a_well_typed_no_op`. Tests reading `network.country()`/`hostname()` without
  setting them expect the product default (A.U24.09).
- **Resolved**: —
- **Unit**: U18 (stages U6, U10, U11, U24).
- **Depends**: M.SRC_NET.072, .075, .080, .096; M.TEST_HELP.063 (the corpus).
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.213 LED: construction-time LED, one flash task, two patterns
- **From**: A.U5.07 (`:699-715` `set_ext_led` test goes), A.U18.30 (`:1701-1709` gains `client._led is not None`; `:2109`
  gains the deactivated pattern; new L1s), A.U18.31 (`:657-690` inverted; `:2626-2640`, `:866-884` hold), A.U10.20 (new
  L1 through a raising `_led_on` double, M_SRC_NET gap 5), A.U24.38 (`:565-575`, `:621-640` via recorded prints), A.U24.32
  (read here: the `record_prints` helper), A.U31.15 (`:659` comment; durations 100/2900 ms), A.U18.40 (`set_wifi_led`
  selects the ext LED); OR140.a (17) (the Wi-Fi-off pattern respects the Wi-Fi LED setting: silent when off, the
  current pattern when turned on; A-C review fold).
- **Site**: `tests/test_asy_wifi_service.py:558-768`, `:1377-1387`, `:1695-1716`, `:2109-2134`, `:2618-2646`.
- **Change**: `test_set_wifi_led_true_selects_the_ext_led_when_no_gpio_pin` → `…selects_the_ext_led`.
  `test_set_ext_led_never_touches_push_callbacks_or_triggers_a_reconnect` goes (no setter; guard: the generated
  construction passes `ext_led=`, A.U5.07's L0). The no-LED tests assert via `record_prints()` that no LED failure line
  appears and the state is unchanged; the raising-LED tests assert exactly one `pr.err` line ("LED on() failed:" /
  off / toggle) and that the next call still reaches the LED. `test_flash_led_off_cancelled_mid_off_phase_still_leaves_
  the_led_on` → `test_a_cancelled_flash_leaves_the_led_as_the_canceller_sets_it` (after `_hotspot_client_connected()` the
  LED is on; after `_reset_wlan_connect_state()` it is off and stays off once the cancelled task has run; awaiting the
  cancelled task raises `CancelledError`). New `test_the_hotspot_pattern_is_on_2900_off_100` and
  `test_deactivated_with_the_led_enabled_blinks_100_on_2900_off` (the recorded `sleep_ms` durations); `…deactivated_with_
  the_led_disabled_stays_dark` (no LED call at all); `test_turning_the_wifi_led_on_while_deactivated_starts_its_pattern`
  and `test_turning_the_wifi_led_off_mid_pattern_goes_dark` (the setting changed through the `LEDWifiOn` config-apply
  path while deactivated: on → the 100/2900 ms pattern, off → the LED off and no further LED call; when the change takes
  effect within the running pattern follows M.SRC_NET.077/.100); `test_a_raising_led_helper_ends_the_flash_task_with_one_unexpected_entry` (`_led_on`
  replaced on the instance by a raising double — the real helper absorbs the LED's own raise — one `code("E",
  "UNEXPECTED")`).
- **Resolved**: A.U10.20's L1 ("an LED whose `on()` raises") cannot reach the task top through the real helper; it is
  driven through a replaced `_led_on` (M_SRC_NET gap 5, G5/R54).
- **Unit**: U18 (stages U5, U10, U24, U31).
- **Depends**: M.SRC_NET.084, .087, .092, .098, .100 (.077/.100 as the fold states OR140.a (17)); M.TEST_HELP.050
  (`record_prints`).
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.214 Locks: `async with`, no release helper, the retry wait unlocked
- **From**: A.U10.18 (21 sites; `network_available` → `network_available_locked`), A.U18.32 (`:1661-1685`; `:1179-1230`
  inverted), A.U35.12 (`:196`, `:858`, `:877` parks reviewed), A.U8C.120 (read: `:1215` Dependant), A.U8.10 (`:1179`,
  `:1663` comments).
- **Site**: `tests/test_asy_wifi_service.py:817-891`, `:1066-1086`, `:1174-1246`, `:1654-1694`.
- **Change**: the two `_release_wifi_lock()` tests go (the helper is gone; guard: `test_locked_wlan_status_releases_the_
  lock_even_if_the_status_read_raises`, now through `async with`). `network_available()` → `network_available_locked()`
  with the lock held by the test. `test_on_sta_disconnected_retries_after_a_minute_when_previously_connected` asserts the
  returned `True` and that `_run_sta_mode()` sleeps `_STA_RETRY_AFTER_LOSS_S` with `wifi_mode_lock.locked() is False`
  during the wait. `test_status_getters_return_locked_defaults_during_a_real_concurrent_outage_retry` →
  `test_status_getters_return_the_last_snapshot_during_an_outage_retry` (during the retry wait `get_data()`,
  `get_dns_server_ip()`, `is_hotspot_active()` answer from held state). Each `asyncio.sleep(0)` park at `:196`, `:858`,
  `:877` that claims an interleaving becomes an `Event` gate; one that only lets a task park says so in its comment.
- **Resolved**: —
- **Unit**: U18 (stages U10, U35).
- **Depends**: M.SRC_NET.081, .088, .098.
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.215 The snapshot replaces the radio getters
- **From**: A.U18.33 (`:893-1060`; `:1027-1044` go; `:1046-1064` read the snapshot; `:1135-1158` rssi → snapshot),
  A.U18.42 (`:1160-1175` go; `:1135` comment; `:1208`), A.U24.19 (`:1146-1157`; hotspot rssi/STA stations cases),
  A.U10.06 + A.U14.26 (`:2545-2590` `_now()` tests retire), A.U18.27 (`:2667` named status).
- **Site**: `tests/test_asy_wifi_service.py:892-1173`, `:2547-2590`.
- **Change**: `WIFI(...)` tuples carry eight fields (`Mode, Connected, IP, Subnet, Gateway, DNS, RSSI, TS`); the snapshot
  tests assert the four address fields from `ifconfig()` and `RSSI` from `status("rssi")` only in STA with a link; the
  `get_wlan_ifconfig`/`get_wlan_rssi`/`wlan_isconnected` tests go (guard: the snapshot tests; the raw read stays
  reachable through `_wlan`); `get_dns_server_ip()` reads `_dhcp_dns`: "returns the last snapshot value while the lock is
  held". New `test_hotspot_snapshot_has_no_rssi` (AP selected: `RSSI is None`, no `status("rssi")` call) and
  `test_deactivated_snapshot_makes_no_radio_call` (`Connected False`, addresses and `RSSI` `None`). The two `_now()`
  overflow tests and `_OverflowingTime` go with the method (guard: `utc_now()`'s own L1, M.TEST_UNIT in
  `tests/test_base_classes.py`). `:2667` `_status = 2` → the mirror `_STAT_JOINED_NO_IP = src_const(_WIFI,
  "_STAT_JOINED_NO_IP")`, the comment pointing to the constant's own.
- **Resolved**: —
- **Unit**: U18 (stages U10, U14).
- **Depends**: M.SRC_NET.074, .080, .091, .098; M.TEST_HELP.007 (GAP-T5: `status("rssi")` raises off STA).
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.216 Hotspot: timer failures persist, the selected AP is re-activated in place
- **From**: A.U18.24 (`:1363-1378` one `TIMER` entry; `:1349-1360` holds), A.U18.28 (`:1864-1875` holds; new sibling;
  `:2724-2770` header reworded; `:2729-2730` comment), GAP-T5 (M.TEST_HELP.007: an active AP reports `STAT_GOT_IP`),
  A.U18.29 (`:1957-2012` hold; new end-to-end L1), A.U20.06 (read: `:2767` names `start_tasks()`), A.U18.43 (read:
  `:1833-1848` hold), A.SDEP.17 (read: W42).
- **Site**: `tests/test_asy_wifi_service.py:1247-1387`, `:1833-1949`, `:1950-2053`, `:2674-2876`.
- **Change**: the two alarm-pool degrade tests gain one `code("E", "TIMER")` in the WIFI log. New
  `test_run_hotspot_mode_re_activates_without_a_mode_switch_when_the_selected_ap_reports_no_link` (`_ap_selected =
  True`, status IDLE: `_select_wifi_mode` not called, `_bring_up_hotspot_ap` and `_hotspot_client_absent` called). The
  leak-test section header → "# _run_hotspot_mode() brings the selected AP up again on a tick without a link; it must
  never leak a second DNS server task." and `:2729-2730`'s comment states the fake now reports `STAT_GOT_IP` for an active
  AP (M.TEST_HELP.007). New `test_a_restart_in_hotspot_ends_in_sta_with_a_fresh_streak` (restart in HOTSPOT, two loop
  iterations: STA, `_hotspot_started_once False`, DNS task cancelled).
- **Resolved**: —
- **Unit**: U18 (stage U24 fake).
- **Depends**: M.SRC_NET.083, .086, .087, .093; M.TEST_HELP.007.
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.217 Codes renumbered; connect verdicts under the central rule
- **From**: A.U2.14 (44 lines; `:2653, 2660, 2667` RF287 names), A.U3.02 (`:1505-1560` rewritten; the "ends the episode"
  test flips), A.U3.12 (WIFI BAD_ARG and STORED_DEFAULT repeats spend one slot), A.U18.36 (`:1463-1471` renamed), A.U36.544
  (`:1527` pointer; `:2592` "attempt operations" convention), A.U24.32 (`:2653-2671` print assertions), A.U18.27
  (`pm=0xA11140` literals), A.U8.10 (`:1564` comment).
- **Site**: `tests/test_asy_wifi_service.py:1388-1592`, `:2590-2672`.
- **Change**: every errno/wrnno in a test name and assertion follows the catalog: `…persists_errno_11` →
  `…persists_wlan_mode_switch` (`code("E", "WLAN_MODE_SWITCH")`), 12 → `WLAN_AP_START`, 13 → `WLAN_STA_START`, 14 →
  `WLAN_STA_POLL`, 15 → `WLAN_STA_DISCONNECT`; `wrnno_4` → `…authentication_failure_persists_wlan_auth_failed`, 5 →
  `WLAN_NO_AP`, 6 → `WLAN_CONNECT_FAILED`, 7 → `WLAN_STATUS_UNKNOWN`. The episode section comment → "# A repeated connect
  verdict is one code: one slot, every attempt counted (C.7.1's central rule)."; the first test keeps its assertions with
  `code(…)`; the different-verdict test expects both codes; `test_a_successful_connection_ends_the_episode_so_a_later_
  outage_persists_again` → `test_a_recurrence_after_recovery_stays_one_slot` (`[NO_AP]`, `ErrCount == 2`). `:1527`'s
  pointer → "(SPECIFICATION.md C.7.1, `W4`)" as A.U36.544 writes it; `:2592` states the plain fact. The three in-progress
  status tests (`:2653-2671`) assert their printed state line through `record_prints()` (IDLE, CONNECTING, "WLAN obtaining
  IP") and that nothing persists. `pm=0xA11140` literals → `src_const(_WIFI, "_PM_NO_POWERSAVE")`. `:1564` comment names
  `_STA_DISCONNECT_WAIT_ITERS × _STA_DISCONNECT_POLL_MS` and the test runs under `FastAsyncSleep()`.
- **Resolved**: —
- **Unit**: U18 (stages U2, U3, U36).
- **Depends**: M.SRC_NET.077, .089; M.TEST_HELP.050.
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.218 Missing config logs in both layers; the give-up keeps both entries; the radio rung
- **From**: A.U3.05 (`:1700-1737` break the real store) and A.U3.07 (`:2229-2238`, `:3050`), each with its one-entry half
  dropped (OR140.a (7): WIFI keeps its own config-read entry beside `CFGMGR_WIFI`'s, and the give-up keeps WIFI's own
  entry beside the base GIVE_UP; A-C review fold), A.U10.R01 + A.U18.R01
  (streak tests re-derived; new L1s), A.U10.18 (read: the give-up test's patched loop).
- **Site**: `tests/test_asy_wifi_service.py:1695-1749`, `:2220-2283`, `:3040-3056`; new tests.
- **Change**: the three missing-config tests break the real `ConfigManager` (`_make_invalid_cfg_client()`): WIFI's log
  keeps its own config-read entry (HEAD's code, by the catalog name the fold gives it back), `CFGMGR_WIFI` holds
  `code("E", "CFG_NOT_VALID")`; the names lose `persists_wrnno_N`. `test_wlan_connect_gives_up_after_repeated_hardware_
  failures_and_persists_errno_17` → `test_connect_loop_gives_up_after_repeated_hardware_failures_and_persists_both_
  entries` (runs under `FastAsyncSleep()`: the 2nd failure's radio rung sleeps its settles; the log holds the base
  `code("E", "GIVE_UP")` and WIFI's own give-up entry, HEAD's 17 by the catalog name the fold gives it back, each once);
  `:3050` → neither of the two codes is in the log. New
  `test_two_failed_iterations_re_select_the_radio_once` (one `deinit()` and one `WLAN(STA_IF)` construction on the fake,
  one `code("W", "DEVICE_RECOVERY")`); `…in_hotspot_the_ap_is_re_selected`; `…deactivated_makes_no_radio_call`;
  `test_a_raising_deinit_logs_one_mode_switch_entry_and_no_recovery_warning`; `test_the_radio_rung_fires_again_after_a_
  restart_and_a_good_iteration`.
- **Resolved**: —
- **Unit**: U18 (stage U10).
  A-C2 step order: A.U10.R01's part lands in U13, not U10 (it follows A.U10.R01's own change, which lands in U13).
- **Depends**: M.SRC_NET.084, .100, .102 (as the fold reverts A.U3.05/A.U3.07); M.SRC_CORE.037; [fold F11 M_GEN] (the restored WIFI
  codes' names).
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.219 STA connect: one status call on success, the authentication wording
- **From**: A.U18.32 (one status call on success), A.U18.36, A.U35.12, A.U24.81 (two clients expect independent WLAN
  objects: re-derived against the one static object per interface, GAP-T5), A.U18.01 (`:2312-2319` QTYPE comment),
  A.U0.35 (`:1790-1791`).
- **Site**: `tests/test_asy_wifi_service.py:1593-1694`, `:1750-1832`, `:2416-2476`, `:2312-2319`.
- **Change**: `_poll_sta_connect_status()` with `STAT_GOT_IP` returns after one `status()` call (asserted on the fake's
  call log). `:1790-1791`'s "CLAUDE.md's 'physical intervention as the accepted backstop' pattern" → "CLAUDE.md's
  power-cycle recovery (owner, 2026-09-04)". Tests building two clients that expected independent WLAN objects assert the shared per-interface object
  instead (the network fake returns one static object per interface). `:2315`'s comment "QTYPE=A/QCLASS=IN, never read
  by parsing that stops at the QNAME terminator" → "QTYPE=A/QCLASS=IN: an A query gets the A record".
- **Resolved**: —
- **Unit**: U18 (stage U24 fake).
- **Depends**: M.SRC_NET.089; M.SRC_NET (captive DNS QTYPE, A.U18.01); M.TEST_HELP.007.
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.220 Captive-DNS integration: tuple addresses, port band, ordered proof
- **From**: A.U18.12 (`:2303-2309`, `:2320-2345` tuples, shim), A.U24.70 (`:2301-…` → `PortAllocator`), A.U18.05
  (`:2320-2345` wake at 100 ms, margins re-checked), A.U35.14 (4) (`:2343` ordered proof; row withdrawn), A.U8C.22 (tags),
  A.U8C2.06 (tags), A.U10.38 (`AsyUDPSocket` → `UDPSocket`, `DNSServer` → `CaptiveDNS`), A.U27.30 (4 dividers),
  A.U36.544 (read: none here beyond `:2592`), A.U25.37 (read: the twin fault matrix names this file's scope only).
- **Site**: `tests/test_asy_wifi_service.py:2284-2476`.
- **Change**: `make_addr()` → `_make_addr()` returning `("127.0.0.1", _PORTS.next())` (`PortAllocator("asy_wifi_service")`),
  the shim applied once at module level; the comments naming the sockaddr workaround go. `:2343`'s `sleep(0.3)` → after the
  malformed datagram the test sends one well-formed query and waits for its reply; the only reply carries the well-formed
  query's ID and the task is alive (no `_NO_REPLY_WAIT_S`; its row withdrawn). Module constants and tags as A.U8C.22 and
  A.U8C2.06 write them for the surviving literals (`_CONNECT_BOUND_S`, `_SENT_POLL_MS`/`_SENT_POLL_TRIES`,
  `_OFF_SUBNET_WAIT_S`, `_CONNECT_POLL_MS`/`_TRIES`, `_PHASE_POLL_MS`/`_TRIES`, `_FLASH_CANCEL_BOUND_S`). The four
  `# ====` dividers → `# ----`.
- **Resolved**: —
- **Unit**: U24 (stages U18, U27, U35).
  A-C2 step order: A.U24.70's part lands in U25, not U24 (it follows A.U24.70's own change, which lands in U25).
- **Depends**: M.SRC_NET (`UDPSocket`, `CaptiveDNS`); M.TEST_HELP.056.
- **Blast carried by**: Part N rows → A.U8.01 (SPEC).
- **Kind**: test

### M.TEST_UNIT.221 Cancellation at each await of the WiFi tasks
- **From**: A.U35.48.
- **Site**: new test.
- **Change**: `test_cancelling_a_wifi_task_at_each_await_leaves_the_mode_lock_free` drives `cancel_at_each_await()` from
  synchronous scope over `_run_sta_mode()` and the LED flash task (`FastAsyncSleep` inside the coroutine); invariants:
  `wifi_mode_lock` unlocked, `_ledflash` either `None` or done, the LED state a canceller set.
- **Resolved**: —
- **Unit**: U35.
- **Depends**: M.TEST_HELP.067.
- **Blast carried by**: —
- **Kind**: test

## tests/test_base_classes.py (→ `tests/test_asy_base_classes.py`)

### M.TEST_UNIT.222 Header: renamed modules, shared builders, no shadowing schema names
- **From**: A.U10.37/A.U10.38 (file rename; `base_classes`/`print_log`/`config_manager` → `asy_*`; `AsyFramManager` →
  `FRAMManager`), A.U24.01 (2) (`:103` `_VAL_SI` → `_TEST_SCHEMA_SI`), A.U24.08 (`run`), A.U24.49 (`make_fram_manager`),
  A.U16.05 (18 `LockableBuffer` mentions → `RegionBuffer`), A.U16.19 (`:69`, `:74` fake chunks drop `override_pause`),
  A.U11.S03 (read: `:52-95` buffer types hold under the rename), A.U10.18 (7 lock-name sites).
- **Site**: `tests/test_base_classes.py:1-113`; every lock and buffer reference.
- **Change**: the file moves to `tests/test_asy_base_classes.py` (U10 `git mv`). Imports `from asy_base_classes import
  COUNTER_CAP, Lockable, LockedCounter, LockedFlag, LockedValue, RegionBuffer, SensorReader, SensorReaderConfig,
  TickSeconds, ValueRef, arm_tick_timer, set_utc_valid, utc_now`; `import asy_base_classes`; `from asy_print_log import
  LogConfig, PrintLog, PrintLogHistory, PrintLogHistoryStore`; `from _async_harness import run`; `from _fram_builders
  import make_fram_manager` (the local builder goes; `asy_fram_manager.FRAMManager` in its users). The two
  `_RaisingFram*` doubles type their buffers `RegionBuffer` and drop `override_pause`. `_VAL_SI`/`_VAL_BOOL`/`_VAL_SPECIAL`
  → `_TEST_SCHEMA_SI`/`_TEST_SCHEMA_BOOL`/`_TEST_SCHEMA_SPECIAL` with every use (no test name shadows a src const); the
  special-alone comment names `asy_sgp40_driver.py`'s `ResetVOC`. Every `.asy_lock` → `.session_lock`.
- **Resolved**: —
- **Unit**: U24 (stages U10 rename/names, U16 buffer).
- **Depends**: M.SRC_CORE.027, .030, .033; M.TEST_HELP.043, .057.
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.223 Region buffers hold no lock
- **From**: A.U16.05 (`:259-266` deleted; `:269-270` → `test_regionbuffer_holds_no_lock`), A.U24.39 (`:269` behaviour
  assertion: superseded by the deletion).
- **Site**: `tests/test_base_classes.py:116-272`.
- **Change**: the `LockableBuffer` tests become `RegionBuffer` tests (same region assertions). `test_lockablebuffer_is_
  still_lockable` goes (it tests the removed lock; guard: the next test). `test_lockablebuffer_is_a_lockable_instance` →
  `test_regionbuffer_holds_no_lock` (`not isinstance(RegionBuffer(4), Lockable)` and no `session_lock` attribute).
- **Resolved**: A.U24.39 rewrites `:269` to "its lock serialises two holders"; A.U16.05 (U16, the decision) removes the
  lock that sentence would test — the deletion and the decision-pinning test stand (agent decision D-T18).
- **Unit**: U16.
- **Depends**: M.SRC_CORE.027.
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.224 Shared scalars: the cap, lock-free, None round-trips
- **From**: A.U10.01 (`:278-281` → `COUNTER_CAP`, `_max_val`; `:284-360` hold; new L1s), A.U10.17 (`:357-366` holds;
  `value_lock` references go).
- **Site**: `tests/test_base_classes.py:274-396`.
- **Change**: `test_lockedcounter_defaults` asserts `_max_val == COUNTER_CAP`. Any `value_lock` read goes. New
  `test_a_max_val_above_the_cap_is_clamped_to_it` (`LockedCounter(max_val=COUNTER_CAP + 5)._max_val == COUNTER_CAP`);
  `test_increment_near_the_cap_stays_there` (set to `COUNTER_CAP - 1`, two increments → `COUNTER_CAP`, no exception);
  `test_lockedvalue_round_trips_none_and_a_32_bit_value`.
- **Resolved**: —
- **Unit**: U10.
- **Depends**: M.SRC_CORE.031.
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.225 New primitives: TickSeconds, arm_tick_timer, utc_now, ValueRef
- **From**: A.U10.02 (fake ticks cases), A.U10.03 (`arm_tick_timer()` L1), A.U10.06 + A.U10.28 (`utc_now()` before/after
  `set_utc_valid()`; stepped clock), A.U5.11 (`ValueRef`).
- **Site**: new section after `:396`.
- **Change**: with `asy_base_classes.time` replaced by a fake ticks source (restored in `finally`): up — 999 ms reads 0,
  +1 ms reads 1, 3 × 700 ms reads 2 with 100 ms kept; down — `restart(3)`, 2500 ms reads 1, 600 ms more reads 0, more
  reads 0; saturation — `restart(COUNTER_CAP - 1)`, +5000 ms reads `COUNTER_CAP`; a fake clock with a 2**30 period
  crossing its wrap counts the true elapsed time. `arm_tick_timer()` arms PERIODIC 1000 ms and returns `True`; under
  `RaiseOnArm(OSError)` and `RaiseOnArm(MemoryError)` it returns `False` and prints one line (`record_prints()`).
  `utc_now()` is `None` before `set_utc_valid()` and an int after (`_utc_valid = False` restored in `finally`); with a
  settable wall clock, `utc_now()` follows a backward and a forward step while a running `TickSeconds` is unaffected.
  `ValueRef(src, "Temp")` exposes `source`/`field`.
- **Resolved**: —
- **Unit**: U10.
  A-C2 step order: A.U10.28's part lands in U16, not U10 (it needs A.U16.18, which lands in U16).
  A-C2: stage U24 — until M.TEST_HELP.050/.053 exist the print capture and the arm-failure double are file-local (the HEAD form); U24 swaps in `record_prints()` and `RaiseOnArm`.
- **Depends**: M.SRC_CORE.032, .035; M.TEST_HELP.050, .053.
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.226 SensorReader construction: one log path, no logger reach-through
- **From**: A.U5.02 (49 calls and 7 subclasses; `fram=`/`history_length=`/`debug=` → `log=`), A.U35.45 (`:450-470`
  `logger=` tests go), A.U5.12 (read: the reach-through is removed here by A.U35.45), A.U11.15 + A.U11.13 (`:409-415`
  level reads hold for valid levels), A.U11.S02 (read: `:445`, `:795` `==` hold), A.U10.10 (`:650-740` `pr.initialized`
  after `setup()`).
- **Site**: `tests/test_base_classes.py:399-740`.
- **Change**: every `SensorReader(…)`/`SensorReaderConfig(…)` construction passes `log=LogConfig(<fram or None>,
  <history_length>, <debug>)` by keyword and `max_module_error=` by keyword. `test_sensorreader_reuses_a_given_logger_
  instead_of_constructing_a_fresh_one` and its sibling go (the parameter is removed; guard: the one-path construction
  test `…name_is_baked_into_a_freshly_constructed_logger`). The FRAM-backed cases call `run(reader.setup())` where they
  read a persisted log; `test_sensorreader_fram_backed_error_check_without_setup_never_raises` keeps its premise (no
  setup) and asserts the RAM fallback.
- **Resolved**: —
- **Unit**: U5 (stages U10, U11, U35).
- **Depends**: M.SRC_CORE.036, .039.
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.227 The streak keeps its entry; the ladder climbs one rung per failure
- **From**: A.U3.03 dropped (OR140.a (7): every layer that meets a fault keeps its own persisted entry, the base class's
  streak entry included; A-C review fold), A.U2.06 (5 lines), A.U10.R01 (`:472-510` hold; new ladder L1s), A.U11.31 (reset returns
  `True`).
- **Site**: `tests/test_base_classes.py:472-740`; new tests.
- **Change**: the tests that use the streak entry to persist (`:474, 638, 647, 658, 668, 690, 706, 718, 739`) keep it,
  asserted by its catalog name instead of the number 1 (the name the fold gives the streak code back, [fold F11 M_GEN]).
  `test_sensorreader_reset_error_counter_clears_history` asserts `run(reader.reset_error_counter()) is True`. New
  `test_a_failing_cycle_keeps_the_drivers_and_the_streaks_entries` (a failing cycle: the driver's own entry, then the
  streak's, under the newest-entry rule; the give-up adds `code("E", "GIVE_UP")`);
  `test_the_ladder_fires_each_rung_once_in_order` (a subclass with a counting `_recover_device()` and a stub bus whose
  `clear()`/`recover()` count: failures 1…6 fire nothing / device once / bus clear once / controller once / nothing /
  give-up); `test_a_success_mid_streak_fires_nothing_new_until_the_streak_returns_to_zero`;
  `test_an_externally_zeroed_streak_re_arms_every_rung` (a task restart, one good cycle, a new streak climbs again).
- **Resolved**: —
- **Unit**: U10 (stages U2, U11).
  A-C2 step order: A.U10.R01's part lands in U13, not U10 (it follows A.U10.R01's own change, which lands in U13).
- **Depends**: M.SRC_CORE.037 (as the fold reverts A.U3.03); [fold F11 M_GEN] (the streak's catalog entry).
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.228 The shared trigger divider and the timer fault
- **From**: A.U15.40 (new L1 for the shared divider, n = 1, 3), A.U15.41 (`_timer_failed()`/`_timer_fault()` L1),
  A.U10.44 + M_SRC_SENS GAP-8 (the divider is `SensorReader._trigger_loop()`, M.SRC_SENS.045, M.SRC_CORE.039), A.U10.35
  (`_read_event` private; gap pass G3).
- **Site**: new tests.
- **Change**: `test_trigger_loop_sets_the_read_event_on_every_nth_tick` (`reader._trigger_loop()` driven by setting
  `_base_trigger_event`, with `_trigger_period` answering n = 1 and n = 3: `_read_event` set on ticks 1, 2, 3 … and 3,
  6 …); `test_a_failed_timer_wakes_the_reader_and_logs_once` (`_timer_failed(e, flag)` sets the flag and prints;
  `_timer_fault()` then persists one `code("E", "TIMER")` and returns `True`);
  `test_trigger_loop_re_arms_a_failed_timer_first` (`_timer_error` set: the loop's first act is `start_timer()`, the
  error cleared).
- **Resolved**: A.U15.40 names the divider `_divide_trigger()`; A.U10.44 (earlier) names it `_trigger_loop()`, the name
  M.SRC_CORE.039 and M.SRC_SENS.045 carry (M_SRC_SENS GAP-8) — the tests use it (gap pass G3).
- **Unit**: U15.
- **Depends**: M.SRC_CORE.039.
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.229 SensorReaderConfig: schema getter, setup verdict, FRAM rule comment
- **From**: A.U24.61 (`:840`; `:833` comment goes), A.U10.39 (`cfg_schema` → `get_cfg_schema()`), A.U36.004 (`:984-986`),
  A.U11.17 (read: `:945-957` holds), A.U11.19 (`:1013-1016` baseline 1 → 0), A.U35.37 (checks A.U11.19 landed),
  A.U11.24 (5 `write_config` sites), A.U10.10 (`setup() -> bool`).
- **Site**: `tests/test_base_classes.py:743-1127`.
- **Change**: `.cfg_schema` reads → `get_cfg_schema()`; `:833`'s "self.cfg_schema stays public too" comment goes;
  `test_sensorreaderconfig_setup_awaits_cfgmgr_setup` asserts `run(reader.setup()) is True` for a valid manager.
  `:984-986` → "# The implicit FRAM-wiring rule (SPECIFICATION.md A.7): SensorReaderConfig forwards its own in-scope /
  # log config into the ConfigManager it owns, in its own chunk, separate from reader.pr's." `:1013-1016`'s first-boot
  baseline → no entry (`0`); each `write_config({…}, schema)` → `write_config({…})`. New
  `test_a_cfg_log_fram_false_class_keeps_its_config_store_ram_only` (a subclass with `_CFG_LOG_FRAM = False` given a FRAM
  log: `cfgmgr.pr` is a RAM history, `reader.pr` the store).
- **Resolved**: —
- **Unit**: U11 (stages U10, U24, U36).
- **Depends**: M.SRC_CORE.040.
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.230 Write orchestration on SensorReader: lock, deferred commit, concurrent recovery
- **From**: A.U4.03 (`:1128-1136` comment; `:1203-1524` hold; new L1s), A.U11.27 (`:1204-1617` hold; `:1544-1577`; new
  L1s), A.U11.28 (`:1204-1235` write count; new L1s with `WriteCountingOpen`), A.U30.08 (read: same results), A.U0.35
  (`:1132`, `:1664`, `:1825`), A.U19.15 (read: `:1664`), A.U24.38 (`:1530` unknown key → config unchanged on read-back),
  A.U11.19 + A.U35.37 (`:1449-1452` comment), A.U19.12 (read: single-task read path holds), A.U35.41 (read: E.5.1 row),
  A.U4.02 (read: hold).
- **Site**: `tests/test_base_classes.py:1128-1851`.
- **Change**: `:1128-1136` → "# The write orchestration lives on SensorReader; SensorReaderConfig adds the file store (SCD30's
  AmbPres uses this path as an always key). Persist first, then push (owner, 2026-09-26): …" (≤ 3 lines; the push-only-on-
  change sentence kept). `:1664` "Final project decision:" → "(owner, 2026-09-26):"; `:1825` "(project decision)" →
  "(agent, 2026-08-03)"; `:1449-1452`'s "two benign warnings" → none (the test asserts no entry). `:1530` → the schema
  values and the config file read back unchanged. `test_set_dict_cfg_push_callback_returning_false_marks_the_field_
  failed` gains a write count (`WriteCountingOpen`). New: `test_a_plain_sensorreader_answers_every_key_failed`;
  `test_a_key_without_a_push_callback_triggers_no_pre_write_read`; `test_concurrent_puts_keep_the_later_value` (the
  first PUT's push suspended on an `Event` then failing, the second accepted meanwhile: the stored value is the second's);
  `test_a_recovery_write_answering_false_prints_and_persists_nothing_of_its_own`;
  `test_a_push_that_fails_and_recovers_writes_nothing`; `test_a_successful_push_writes_once_after_it_returned` (the fake
  push records the write count it saw: 0); `test_a_put_cancelled_mid_push_still_flushes_its_staged_value`.
- **Resolved**: —
- **Unit**: U11 (stages U0 tags, U4, U19, U24, U30).
- **Depends**: M.SRC_CORE.038; M.TEST_HELP.062 (`WriteCountingOpen`).
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.343 The hourly window counter under a driven clock
- **From**: OR137.a (1)-(4) (`HTTPDropped` counts the last 24 hours in 24 hourly bins: a reusable primitive beside the
  shared counters, tested under a driven clock — bin shift, a gap of a day or more, the cap, the reset, no heap
  allocation per drop or read), FOLD_ANSWERS `status-fields-added-and-left-out` (owner's note, 2026-10-02) — A-C review
  fold.
- **Site**: new section after the shared-scalar tests (`tests/test_base_classes.py`, after M.TEST_UNIT.225's section).
- **Change**: section comment "# The hourly window counter (SPECIFICATION.md G): 24 fixed bins advanced lazily from the
  uptime seconds; a count leaves the window 23-24 hours after it happened." The uptime seconds are fed from the test
  (the primitive reads the `SysUptime` count it is given, OR137.a (1); its call shape follows the product change).
  Cases: `test_counts_in_one_hour_sum` (three adds at t, t + 10 s, t + 3599 s → 3); `test_the_bins_shift_hour_by_hour`
  (one add per hour for 30 hours → 24 after the 30th, the oldest six gone; a read at the start of hour h + 24 no longer
  holds hour h's count); `test_a_count_leaves_the_window_between_23_and_24_hours` (an add at the end of an hour still
  counted 23 h later, gone at the 24 h boundary; an add at the start of an hour counted until 24 h); `test_a_gap_of_a_day_
  or_more_clears_every_bin` (adds, then a read 86 400 s and 10 × 86 400 s later → 0, then new adds count from 1);
  `test_a_bin_and_the_sum_saturate_at_the_cap` (`COUNTER_CAP` adds into one bin stays `COUNTER_CAP`; bins whose sum
  exceeds it read `COUNTER_CAP`, driven by setting the bins from the test, never by a brute-force loop — CLAUDE.md's
  structural-proof rule); `test_reset_clears_every_bin` (then counting resumes in the current hour);
  `test_no_add_or_read_allocates` (at the process's GC stage, no in-body `gc.threshold` (A.U30.12/.13): `gc.mem_alloc()`
  does not rise across 1 000 adds and reads spanning several hour changes, after one warm-up add — the bins are
  allocated once at construction); `test_the_bins_are_allocated_once_at_construction` (the bin store's identity
  unchanged across adds, reads, hour changes and `reset()`).
- **Resolved**: —
- **Unit**: U19 (the primitive lands with its first user, OR137.a).
- **Depends**: [fold F02 M_SRC_CORE] (the primitive in `base_classes.py`); M.SRC_CORE.031 (`COUNTER_CAP`).
- **Blast carried by**: SPEC Part G catalog entry → [fold F02 M_SPEC]; the webserver's use → M.TEST_UNIT.202.
- **Kind**: test

## tests/test_bus_hazard_generated.py

### M.TEST_UNIT.231 Freshness guard, every bus kind, a test per writer
- **From**: A.U24.46 (`require_fresh()` first), A.U24.27 (`:66-71` `_port_id_for_bus()` takes `spi<n>`; `:130-132` loop
  over `plan["buses"]` and `plan["spi"]`; generated names gain the writer), A.U24.20 (`:74-81` builds through the
  catalog's `make_i2c()`, which resets the id), A.U24.28 (`:84-87` the sweep asserts by equality, in the catalog),
  A.U35.16 (read: the all-occupants cases carry the window check, in the catalog), A.U15.25 (read: the generated
  scenarios keep the default BMP chip id), A.U24.08 (`run`), A.U24.73 (`Any`), A.U0.07 (`import asyncio` at the top).
- **Site**: `tests/test_bus_hazard_generated.py:1-133`.
- **Change**: `import asyncio` joins the module imports at the top; `from _async_harness import run`; `from
  _generated_tree import require_fresh` called once at module level before `_all_device_wiring_plans()`;
  `_generated_src_dir()`'s comment kept. `_port_id_for_bus()` accepts `i2c<n>` and `spi<n>` (the assertion message names
  both); the registration loop walks `plan["buses"]` and `plan.get("spi", {})`; an SPI bus with ≥ 2 occupants builds
  through `SPI_HAZARD_CATALOG` (an occupant missing from it raises the catalog's actionable `KeyError`). The write-vs-
  siblings registration registers one test per writer: `test_<device>_<bus>_a_<driver>_write_does_not_disturb_
  concurrent_sibling_reads_across_timing_offsets`; a bus with no writer or no broadcaster reports SKIP with the
  catalog's reason (A.U7.07), never a silent pass. `_all_device_wiring_plans()`'s docstring → a `#` comment (≤ 3 lines,
  the one header block rule).
- **Resolved**: —
- **Unit**: U24.
- **Depends**: M.TEST_HELP.026, .027, .046.
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.232 A bus recovery mid-read, per generated bus
- **From**: A.U13.R02 (2) (the recovery scenario for every generated bus topology), A.U35.50 (read: the conformance
  matrix lists this cell), A.U36.014 (read: CLAUDE.md points to SPEC C.8's list).
- **Site**: `tests/test_bus_hazard_generated.py:89-127` (`_register_bus_tests`).
- **Change**: every I2C bus with ≥ 2 occupants also registers `test_<device>_<bus>_a_bus_recovery_does_not_disturb_
  concurrent_sibling_reads_across_timing_offsets` running `scenario_bus_recovery_does_not_disturb_concurrent_siblings(
  _make_build_fresh(bus_name, attachments))`.
- **Resolved**: A.U13.R02 (2) places the L1 "for every generated bus topology (the file's existing per-bus
  parametrisation)" in `tests/test_bus_hazard_multi_device.py`; that per-bus parametrisation is this file's, so the
  per-topology case lands here and the per-driver split-session cases stay in the hand-paired file (agent decision
  D-T19).
- **Unit**: U13.
- **Depends**: M.TEST_HELP.027 (4); M.SRC_SENS (A.U13.R01 `recover()`).
- **Blast carried by**: L2-L4 tiers → A.U13.R02 (TWIN, HW_DEV, HW_BENCH).
- **Kind**: test

## tests/test_bus_hazard_multi_device.py

### M.TEST_UNIT.233 Header, shared doubles, catalog constants, no address keywords
- **From**: A.U24.08 (`run`), A.U24.49 + A.U31.09 + A.U31.11 (`:42-56` `_FastAsyncSleep` → shared, patches `sleep_ms`
  too), A.U24.01 (4) (`:87` `BMP_EXPECTED_TEMPERATURE` from the catalog), A.U15.28 (`:117, 166-167, 210, 249-250, 316-317,
  358` no `address=`), A.U10.18 (6 lock sites), A.U24.67 (variant names in comments), A.U24.73 (`Any`), A.U15.15 (`:68-70`
  comment holds), A.U0.33 (read: SPEC's "permanent home" wording), A.U36.014 (read: CLAUDE.md points to C.8), A.U36.544
  (read: a SPEC comment naming this file).
- **Site**: `tests/test_bus_hazard_multi_device.py:1-112`; the constructions and lock references named.
- **Change**: `from _async_harness import run`; `from _fast_sleep import FastAsyncSleep`; `from _bus_hazard_catalog import
  BMP_EXPECTED_TEMPERATURE, RESERVED_I2C_RANGES, fake, is_reserved, make_i2c, seed_bmp_ready, seed_isl_ready, sgp_word`;
  the local `_FastAsyncSleep`, `seed_bmp_ready`, `_BMP_EXPECTED_TEMPERATURE` and the reserved-range copy go (the file's
  `_BMP_EXPECTED_PRESSURE_HPA` stays with its derivation note). Every `SGP40_I2C(i2c, address=_SGP_ADDR)` /
  `ISL29125_I2C(i2c, address=_ISL_ADDR)` → no address keyword (fixed addresses). `bus.async_lock` → `bus.bus_lock`;
  `.cs_pin`/`.cs_active_value` → `._cs_pin`/`._cs_active_value`. Comments naming a variant ("matches wozi's real i2c1 port
  id", "dev's own i2c1 grouping", "dev's real i2c0 wiring") state the wiring fact instead ("the BMP3XX+SGP40 pairing on
  i2c1", "the ISL29125+SGP40 pairing on i2c1").
- **Resolved**: —
- **Unit**: U24 (stages U10, U15, U31).
- **Depends**: M.TEST_HELP.026, .043, .052.
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.234 Cross-device interleaves: both BMP chip ids, the window check
- **From**: A.U15.25 (`:114` runs once per chip id `(0x50, 0x60)`), A.U35.16 (`:152-159`, `:193-197` → `sibling_inside_
  window`), A.U12.18 (read: `:138`, `:186` calls unchanged), A.U15.S01 (read: no transaction moved), A.U15.32/A.U15.33
  (read: ISL write-vs-read cases run unchanged), A.U13.07/A.U13.09/A.U13.10/A.U15.01/A.U15.12/A.U15.13/A.U30.06/A.U30.07
  (read: healthy-bus cases hold).
- **Site**: `tests/test_bus_hazard_multi_device.py:114-197`.
- **Change**: the BMP3XX+SGP40 test loops over `(0x50, 0x60)` (`seed_bmp_ready(i2c, chip_id=…)`), each run asserting the
  BMP results and the SGP40 words. Both tests replace `switches >= 2` with `assert sibling_inside_window(fake_bus.log,
  _SGP_ADDR), "no sibling transaction landed inside an SGP40 conversion window - the bus was held across the delay"`;
  the result assertions stay.
- **Resolved**: —
- **Unit**: U35 (stage U15 chip ids).
- **Depends**: M.TEST_HELP.026, .027 (`sibling_inside_window`).
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.235 General call: count pinned, the lone-BMP case moves to silicon
- **From**: A.U35.17 (`:240-242` deleted), A.U35.21 (`:271-306` deleted; L3 replaces it), A.U15.15 (`:282` comment goes
  with the deleted test).
- **Site**: `tests/test_bus_hazard_multi_device.py:200-306`.
- **Change**: in `test_sgp40_general_call_reset_does_not_disturb_a_concurrent_bmp3xx_read` the comment and the
  `all(entry[1] != _BMP_ADDR …)` line (filtered to address 0x00, it can never fail) go; the count and payload assertions
  stay. `test_general_call_absent_sibling_bmp3xx_alone_on_the_bus_survives_a_broadcast_too` goes — guard named: the new
  L3 `tests_hardware/device_scripts/bmp3xx_alone_survives_a_general_call.py` with its flash test (A.U35.21, HW_DEV); the
  SGP40-issued broadcast cases (`:207`, `:245`) and the generated sweep keep L1.
- **Resolved**: —
- **Unit**: U35.
- **Depends**: —
- **Blast carried by**: the L3 script and flash test → A.U35.21 (HW_DEV).
- **Kind**: test

### M.TEST_UNIT.236 Fault isolation bounded; sessions with distinct commands; reserved addresses from adapters
- **From**: A.U35.18 (`:314-354` bounded, lock free after), A.U24.74 (`:356-377` distinct sessions), A.U35.19 (`:63-75`,
  `:385-388` from the adapters), A.U8.02 (tag grammar).
- **Site**: `tests/test_bus_hazard_multi_device.py:309-388`.
- **Change**: the fault-isolation gather runs under `asyncio.wait_for(…, _ISOLATION_BOUND_S)` (`# @tunable
  l1.bus_fault_isolation_bound_s = 5`), a `TimeoutError` failing with "the shared I2C lock was not released after the
  SGP40's EIO - the ISL29125 loop never finished"; after it `assert not i2c.bus_lock.locked()`. The three-sessions test
  uses distinct inputs (25 °C/50 %, 10 °C/30 %, 35 °C/80 %); the expected 8-byte command per session is computed in the
  test from the SGP40 datasheet's measure-raw layout (command 0x260F, RH ticks and T ticks each with its CRC-8, poly 0x31
  init 0xFF, cited) — not from the driver's tick helpers; the fake answers `0x8000 + k` per read; asserts the log is
  three `writeto(0x59, …)` each directly followed by its `readfrom_into(0x59, …)`, the payload set equals the expected
  set with valid CRCs, and each session's value is the word read right after its own write. The reserved-address test
  loops over every catalog adapter's `default_address(i2c)` and asserts each is outside `RESERVED_I2C_RANGES`, naming the
  driver; the hand-kept address constants stay only where a test uses them as fixture addresses.
- **Resolved**: —
- **Unit**: U35 (stage U12 with the race fix).
- **Depends**: M.SRC_SENS.068 (A.U12.18 staging); M.TEST_HELP.026.
- **Blast carried by**: Part N row → A.U8.01 (SPEC); L2/L3 of the race fix → A.U12.18 (TWIN, HW_DEV).
- **Kind**: test

### M.TEST_UNIT.237 SPI: a real FRAM against an async session; the overrun through the FRAM path
- **From**: A.U35.20 (`:395`, `:449`), A.U10.18 (`async_lock` → `bus_lock`).
- **Site**: `tests/test_bus_hazard_multi_device.py:390-487`.
- **Change**: `:395`'s synchronous worker becomes a real `FRAM_SPI` over the same `SPI` wrapper (CS 6, `FakeMB85RS64V` on
  that CS) looping `async with fram: fram._read_address(0, buf)`; the async worker holds its session across an `await
  asyncio.sleep(0)` inside the CS window; `overlap_observed` stays false only because `FRAM_SPI.__aenter__` takes the bus
  lock; counts and final CS/lock states stay. `:449`: `bus._spi.rx_overrun = True`, then `async with fram:
  fram._read_address(0, bytearray(32))` raises `OSError` (caught by the test); then, inside `asyncio.wait_for(…,
  _ISOLATION_BOUND_S)`, a neighbour `SPIDevice` takes the bus and writes; FRAM's CS inactive, the neighbour's write logged,
  `not bus.bus_lock.locked()`; the test's own lock/`finally` goes.
- **Resolved**: —
- **Unit**: U35.
- **Depends**: M.SRC_CORE (FRAM_SPI sessions, A.U16.10); M.TEST_UNIT.236 (`_ISOLATION_BOUND_S`).
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.238 New hazard cases: recovery split sessions, SCD30 reset, heater-off, FRAM erase
- **From**: A.U13.R02 (2) (one split-session case per driver), A.U15.R01 (mid-operation SCD30 reset while sibling loops
  run), A.U15.R02 (heater-off concurrent with the SCD30 read loop across offsets; same-device vs the SGP40's own measure),
  A.U15.R04 (the ISL29125 participant rung's mid-operation case, "as A.U15.R01"; M.TEST_UNIT.061's blast, gap pass G3),
  A.S0930.23 (a)-(c) (erase hazards, mock tier), A.S0930.35 (read: names this file for the erase harness), A.U35.50 (read:
  conformance matrix rows).
- **Site**: new section in `tests/test_bus_hazard_multi_device.py`.
- **Change**: `test_a_recovery_between_a_split_session_still_returns_a_valid_value` per driver with one (SCD30 command →
  read, SGP40 command → read, BMP3XX trigger → read): `i2c.recover()` lands between the halves, the transaction returns a
  valid value. `test_an_scd30_soft_reset_mid_read_leaves_every_sibling_read_valid` (SGP40/ISL29125/BMP3XX loops on the
  same bus, the reset at each offset). `test_an_isl29125_reapply_mid_read_leaves_every_sibling_read_valid` (A.U15.R04: the
  re-apply rung — CONFIG1-3 burst from the shadow, thresholds re-armed — run at each offset while the sibling read loops
  of its bus run, as the dev wiring places them; every sibling read valid, the shadow written whole, one
  `code("W", "DEVICE_RECOVERY")`).
  `test_sgp40_heater_off_does_not_disturb_a_concurrent_scd30_read_loop` across offsets,
  and `test_heater_off_and_an_sgp40_measure_serialise_through_the_device_session`. FRAM erase: (a) `erase_chip()` started
  while a chunk write and a chunk read are suspended mid-operation — in-flight ones finish with both copies equal, later
  ones refused, no chunk torn, each erase unit's five sessions contiguous in the SPI log; (b) a sensor cancelled inside its
  I2C session leaves the next sibling transaction succeeding and the lock free; (c) the erase units cover `[0, size)` once,
  ascending, with the 3-byte header on the 256 KB fake and 2-byte on the 8 KB one, no `_SV_BAD_RANGE`; pass-1 status
  writes touch exactly each allocated block's two status bytes.
- **Resolved**: —
- **Unit**: U15 (A.U15.R01/R02/R04; stage U13 recovery, S0930 erase).
  A-C2: "S0930" is not a unit; its parts land in the units SUPP_owner_0930 states: A.S0930.23 in U24.
- **Depends**: M.SRC_SENS (A.U13.R01, A.U15.R01, A.U15.R02, A.U15.R04); M.SRC_CORE (`erase_chip()`, A.S0930.17).
- **Blast carried by**: L2 → M.TWIN.102 (A.U15.R01/R02/R04, A.U13.R02); L3-L4 → A.U13.R02, A.U15.R01, A.U15.R02,
  A.S0930.27-.29 (HW_DEV, HW_BENCH).
- **Kind**: test

## tests/test_captive_dns.py (→ `tests/test_asy_captive_dns.py`)

### M.TEST_UNIT.239 File harness: renames, shared run/cancel, port band, plain tuples
- **From**: A.U10.37 (file and module rename), A.U10.38 (`DNSServer` → `CaptiveDNS`, `AsyUDPSocket` → `UDPSocket`,
  `AsyConnTime` → `WifiService` in comments), A.U10.35 (`server.udps` → `server._udps`, `udps.sock` → `_udps._sock`),
  A.U24.08 (`:23` local `run`, `:379` `_cancel` → `_async_harness`), A.U24.70 (`:31-37` → `PortAllocator`), A.U18.12
  (`:39-44` `resolve_addr` shim; `:583, :839, :876` tuples), A.U18.15 (read: `:25-26` `make_pr` is the shape other files
  copy — holds), A.U24.73 (the 9 `Any` sites), A.U0.07 (`:910` `import captive_dns as captive_dns_module` → module level).
- **Site**: `tests/test_captive_dns.py:1-75`, every `DNSServer(`/`.udps` site, `:376-381`, `:583-602`, `:809-900`, `:910`.
- **Change**: imports `from asy_captive_dns import CaptiveDNS, DNSQuery` (no `_ipv4_to_int`), `import asy_captive_dns`,
  `from asy_print_log import LogConfig, PrintLogHistory, PrintLogHistoryStore`, `from asy_udp_socket import UDPSocket`,
  `from _async_harness import cancel, run`, `from _error_codes import code`, `from _port_bands import PortAllocator`,
  `from _src_const import src_const`, and the address shim applied once at import (A.U18.12's location, as
  M.TEST_UNIT.025). `_next_port`/`make_port()` → `_PORTS = PortAllocator("test_asy_captive_dns")`, `_PORTS.next()` at
  each use. Every `UDPSocket(...)` built by a test takes a plain `("127.0.0.1", port)` tuple; `resolve_addr()` survives
  only as `_resolved()` for the raw peer sockets' `bind()`/`sendto()` (comment "# This Unix build's raw bind()/sendto()
  need getaddrinfo()'s opaque sockaddr (SPECIFICATION.md F.7); only the peer sockets use it."). `_cancel()` goes for
  `cancel()`; `make_pr()` stays (it is a module-level builder used by `DNSQuery` tests; name unchanged, the shape other
  files cite). Every `DNSServer(...)` → `CaptiveDNS(...)`, every `server.udps = fake  # type: ignore[assignment]` →
  `server._udps = fake  # type: ignore[assignment]` (the fake is not a `UDPSocket`; the ignore stays inline), every
  `.udps.sock` read → `._udps._sock`. Section banners name `CaptiveDNS`/`UDPSocket`; `:810-812`, `:862-866` and `:878`
  name `WifiService` building one `CaptiveDNS` and cancelling it fire-and-forget (`async_connect.py`'s name goes).
  `Any` sites: `recv_call_times_ms: list[object]`, the bad-value tables `list[object]`/`tuple[tuple[object, object],
  ...]` (A.U24.73's "genuinely open values `object`"); `_cancel`'s `Task[Any]` goes with it.
- **Resolved**: —
- **Unit**: U18 (stages U10 names, U24 harness/ports/typing).
  A-C2 step order: A.U24.70's part lands in U25, not U24 (it follows A.U24.70's own change, which lands in U25).
- **Depends**: M.SRC_NET.001, .006, .026; M.TEST_HELP.043 (`run`/`cancel`), .056 (`PortAllocator`), .045 (`code`), .044
  (`src_const`); the shim's move (A.U18.12, TWIN/TOOL).
- **Blast carried by**: port table row → A.U24.70 (TEST_HELP); `pyproject.toml` ANN401 exemption → A.U24.73 (TOOL).
- **Kind**: test

### M.TEST_UNIT.240 Tag the tuned literals of the captive-DNS tests
- **From**: A.U8C.23 (every row but the mirror), A.U8C2.07 (`:889` `cleanup_tick_count`), A.U8.11 (`:952` mirror,
  `:1067` Dependant), A.U8C.120 (read: Dependant rows of the error wait and the backoff), A.U31.16 (`:1067` band
  unchanged in value).
- **Site**: `tests/test_captive_dns.py:370-375, 423, 482, 512, 595-597, 647, 824-890, 941-1067, 1077, 1096`.
- **Change**: module constants exactly as A.U8C.23 writes them, each tagged `# @tunable l1.captive_dns_<name> = <value>`:
  `_WAIT_UNTIL_TIMEOUT_MS = 1000`, `_WAIT_UNTIL_POLL_MS = 10`, `_STRAY_REPLY_WAIT_MS = 20`, `_NO_BACKOFF_ELAPSED_MAX_MS
  = 1000`, `_REACH_RECV_MS = 20`, `_BIND_WAIT_MS = 50`, `_REPLY_WAIT_MS = 200`, `_CYCLE_WAIT_MS = 100`,
  `_CLEANUP_TICK_MS = 10`, `_CLEANUP_TICK_COUNT = 10` (A.U8C2.07), `_BACKOFF_WAIT_TIMEOUT_MS = 5000`,
  `_BACKOFF_SERIES_TIMEOUT_MS = 15000`, `_GAP_INITIAL_MIN_MS = 400`/`_MAX_MS = 800`, `_GAP_DOUBLED_MIN_MS = 900`/`_MAX_MS
  = 1400`, `_GAP_QUAD_MIN_MS = 1900`/`_MAX_MS = 2600`, `_GAP_NO_BACKOFF_MAX_MS = 300`, `_BACKOFF_CAP_TIMEOUT_MS = 20000`,
  `_GAP_CAP_MIN_MS = 4700`/`_MAX_MS = 5400`; each literal site reads its constant. `:952` `elapsed_ms >= 3000` →
  `elapsed_ms >= src_const("src/asy_captive_dns.py", "_ERROR_RETRY_WAIT_S") * 1000` (comment "# the real
  _ERROR_RETRY_WAIT_S pause ran, unlike the malformed-data path"), no tag.
- **Resolved**: A.U8C.23 lists `:952` as the `dns_server.error_retry_wait_s` mirror and A.U8.11 names it a mirror site,
  while A.U24.01's rule reads a value the product still defines from source: the product defines `_ERROR_RETRY_WAIT_S`
  (M.SRC_NET.004), so the source read stands and the row loses the test site (as M.TEST_UNIT.095/.104).
- **Unit**: U8 (stage U24 source read).
- **Depends**: M.SRC_NET.004; M.TEST_HELP.044.
- **Blast carried by**: SPEC Part N rows → A.U8.01 (SPEC).
- **Kind**: test

### M.TEST_UNIT.241 Dotted-quad tests leave; comments name `ipv4_to_int()`
- **From**: A.U18.08.
- **Site**: `tests/test_captive_dns.py:6`, `:76-122`, `:605-635`, `:673`, `:704-705`, `:769`, `:786`.
- **Change**: the `_ipv4_to_int` import goes; the banner `:76-80` and the six `test_ipv4_to_int_*` tests move to
  `tests/test_asy_dns_client.py` (M.TEST_UNIT.026). `_bad_ipv4_values()` stays here with banner "# Every distinct fault
  shape a caller could hand a dotted-quad parameter: wrong type, and every malformed string ipv4_to_int() rejects."
  (2 lines); the comments at `:632-633, :673, :704-705, :769, :786` read `ipv4_to_int()` (a non-str value still raises
  through its `ip.split()`, M.SRC_NET.021 keeps the body).
- **Resolved**: A.U18.08 moves `:607-630` too, but that span is `_bad_ipv4_values()`, the list four tests of this file
  iterate (`:671, :680, :767, :789`); moving it would leave them without it — it stays (D-T20).
- **Unit**: U18.
- **Depends**: M.SRC_NET.021, M.TEST_UNIT.026.
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.242 `DNSQuery`: drop rules, boundary pair, QTYPE-dependent answers
- **From**: A.U18.02 (`:205-220` flips; `malformed_query_cases()` five shapes; 255/256 boundary pair), A.U18.01 (QTYPE
  cases; existing A-query assertions hold).
- **Site**: `tests/test_captive_dns.py:46-75`, `:129-265`; new tests after `:265`.
- **Change**: `make_query()` gains `qtype: bytes = b"\x00\x01"` (default A, so every existing caller and answer
  assertion holds). `malformed_query_cases()` gains five shapes, each with its comment: QR bit set, QDCOUNT 0, QDCOUNT 2,
  a `0xC0` pointer byte as the first label length, a `0x40` reserved label type — `test_dns_query_malformed_or_truncated_
  data_yields_empty_domain` (`:140`) and every `run()` test iterating the list cover them. `:205-220` →
  `test_a_query_declaring_two_questions_is_dropped`: `domain == ""` and `response(ip) is None`. `:176-203` (EDNS0 OPT,
  ARCOUNT 1) holds. New: `test_a_name_of_255_octets_is_answered_and_256_is_dropped` (labels 63, 63, 63, 61 answered;
  63, 63, 63, 62 dropped); `test_an_a_or_any_query_gets_the_a_record` (QTYPE 1 and 255: ANCOUNT 1, the A record);
  `test_other_query_types_get_an_empty_noerror_reply` (QTYPE 28, 65, 15 and the root query with QTYPE 2: flags
  `0x8180`, QDCOUNT 1, ANCOUNT 0, question echoed, `len(packet) == 12 + question_len`). Expected bytes are assembled in
  the test from the RFC 1035 §4.1.1 header layout and §3.2.2/§3.2.3 QTYPE values (cited in a one-line comment), never
  from `response()`.
- **Resolved**: —
- **Unit**: U18.
- **Depends**: M.SRC_NET.008, .009.
- **Blast carried by**: L4 AAAA query and `dns_probe.build_query(qtype=)` → A.U18.01 (HW_BENCH); `test_asy_wifi_service.py:
  2315` comment → M.TEST_UNIT.219.
- **Kind**: test

### M.TEST_UNIT.243 Construction and logging: one log path, level numbers, entry assertions
- **From**: A.U5.02 (10 constructor calls → `log=`), A.U11.15 (12 accessor sites → `pr.level` and the numbers 0-5),
  A.U11.13 (`:298-308` valid levels hold), A.U20.38 (`:279-281` fan-in test kept as this module's own), A.U11.S02 (read:
  `:283` `==` holds), A.U24.39 (`:287` in-memory logging), A.U11.31 (`reset_error_counter() -> bool`).
- **Site**: `tests/test_captive_dns.py:271-322`.
- **Change**: `:273` `CaptiveDNS(log=LogConfig(None, 10, 5))`, asserts `_udps._addr == ("0.0.0.0", 53)`, `_mode ==
  "server"`, `_sock is None`. `:287` → `test_captive_dns_logs_in_memory_without_fram`: `run(server.pr.err_s("probe",
  errno=code("E", "UNEXPECTED")))` lands as the newest `get_log()` entry and the logger is not a
  `PrintLogHistoryStore`. Level tests: `log=LogConfig(None, 10, 1)` → `server.pr.level == 1`; `LogConfig(None, 10,
  None)` → `0`; default → `0` (the `PrintLog.level_*()` calls go; numbers per SPEC A.8's `DebugLevel`). `:318`'s
  `errno=1` → `code("E", "UNEXPECTED")`. New: `test_reset_error_counter_returns_true_and_clears` (`ErrCount` 0 after).
- **Resolved**: —
- **Unit**: U11 (stages U5 `log=`, U18 annotation, U24 assertion).
- **Depends**: M.SRC_NET.006; M.SRC_CORE (`LogConfig`, accessor removal A.U11.15).
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.244 `run()` on the fake transport: codes, one slot per repeat, 512-byte receive
- **From**: A.U24.41 (`:562-574` one entry, `ErrType` "W", repeated twice without a new slot), A.U3.12 (W41 and W42
  repeats spend one slot), A.U2.16 (err_count checks by code), A.U18.06 (fake `connected`, W42 text), A.U18.03 (`:349`
  comment; `run()` passes 512), A.U18.04 (read: no message-text assertion in the file — none added).
- **Site**: `tests/test_captive_dns.py:337-370`, `:520-580`.
- **Change**: `_FakeUDPS` gains `self.connected = True` and `self.bufsizes: list[int] = []` (`recvfrom(self, bufsize,
  _timeout_ms=-1)` appends it); its comment → "# CaptiveDNS calls recvfrom(512)/sendto(packet, addr): the fake records
  the buffer size; the timeout is never passed." `:528` (BAD_ARG) asserts one entry, `ErrType` "E", `code("E",
  "BAD_ARG")`, and `_udps._sock is None`. `:544` sendto test: two queries both refused (`sendto_results = [None, None]`)
  → `ErrCount` 2 and one `code("W", "DNS_REPLY_DROPPED")` entry. `:562` → `test_run_failed_receive_logs_one_warning_
  per_code`: two `(None, None)` with the fake connected → `ErrCount` 2, one entry, `ErrType` "W", `code("W",
  "DNS_RECV_FAILED")`. New: `test_run_reads_with_the_rfc_1035_udp_limit` — after one query, `fake.bufsizes == [512,
  ...]` (RFC 1035 §2.3.4, cited).
- **Resolved**: —
- **Unit**: U18 (stages U2 codes, U3 slot rule, U24 assertions).
- **Depends**: M.SRC_NET.004, .007; M.TEST_HELP.045.
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.245 A socket that never bound: one E10, its own backoff
- **From**: A.U18.06 (new L1, the growth branch).
- **Site**: new test after `:580`.
- **Change**: `test_run_bind_failure_logs_init_once_and_backs_off`: `asy_udp_socket.socket` replaced for the test by
  a module whose socket's `bind()` raises `OSError(EADDRINUSE)` (the `_RaisingSocketModule` technique of
  `tests/test_asy_udp_socket.py`, restored in `finally`); `server._udps` is a `_TimedUDPSocket(UDPSocket)` subclass
  recording each `recvfrom()`'s entry and return ticks (no method assignment). After three receives: one entry,
  `code("E", "INIT")`, `ErrCount` 3, no `DNS_RECV_FAILED` entry; the server's own pauses (next entry − previous return)
  fall in `_GAP_INITIAL_*` then `_GAP_DOUBLED_*` (0.5 s then 1.0 s; the UDP layer's own one-attempt backoff,
  M.SRC_NET.027, lies inside each call and is excluded by construction).
- **Resolved**: —
- **Unit**: U18 (stage U31 ms backoff, unchanged values).
- **Depends**: M.SRC_NET.007, .027.
- **Blast carried by**: `tests_hardware/README.md:879, 893` wording → A.U18.06 (DOC).
- **Kind**: test

### M.TEST_UNIT.246 Cancellation re-raised after cleanup; disconnect outcomes
- **From**: A.U18.07 (`:505-516` comment, `:1070-1082` rename, new L1), A.U18.15 (`:1085-1103` count holds, number
  `SOCKET_TEARDOWN`), A.U2.16 (codes of `:965`, `:1085`).
- **Site**: `tests/test_captive_dns.py:505-516`, `:956-980`, `:1070-1103`; new test.
- **Change**: `:512` comment → "# run() cleans up and re-raises the cancellation; cancel() absorbs it". `:965` asserts
  one `code("E", "UNEXPECTED")` entry. `:1070` → `test_run_disconnect_reporting_a_second_cancellation_propagates_without
  _logging` (`err_count == 0`; `cancel()` absorbs the propagated `CancelledError`). `:1085` asserts one entry,
  `ErrType` "W", `code("W", "SOCKET_TEARDOWN")`. `:876-893` fire-and-forget holds (`_udps._sock is None`). New:
  `test_awaiting_a_cancelled_run_raises_after_disconnect` — awaits the cancelled task directly, asserts
  `CancelledError` and `fake.disconnect_called` set before it surfaced.
- **Resolved**: —
- **Unit**: U18.
- **Depends**: M.SRC_NET.007.
- **Blast carried by**: SPEC C.8 cancellation line → A.U18.07 (SPEC).
- **Kind**: test

### M.TEST_UNIT.247 Error and backoff paths: comments, unexpected-exception wait, receive backoff
- **From**: A.U18.06 (backoff tests hold: their fake is connected), A.U8.11/A.U31.16 (read: values unchanged; tags in
  M.TEST_UNIT.240), A.U30.19 (read: `report_if_fatal(e)` precedes the logged error; a `RuntimeError` is not fatal, so
  `:908`'s count holds).
- **Site**: `tests/test_captive_dns.py:896-952`, `:980-1068`.
- **Change**: the `:896-906` banner names `_ERROR_RETRY_WAIT_S` for "the 3s backoff" and `asy_captive_dns.DNSQuery`
  for the patched class (`captive_dns_module` → the module-level `asy_captive_dns`); `:931` asserts one `code("E",
  "UNEXPECTED")` entry. The `:982-988` banner → "# run()'s receive-failure backoff: a receive that keeps returning
  (None, None) on a bound socket logs DNS_RECV_FAILED and backs off 0.5, 1, 2 … 5 s (SPECIFICATION.md Part C.9).", the
  "measured at ~5 wrn_s() lines/second before the fix" and "previously had none" history going; the bind-failure case
  points to M.TEST_UNIT.245's test.
- **Resolved**: —
- **Unit**: U18.
- **Depends**: M.SRC_NET.007; M.SRC_NET.011 [follows] (its U30 `report_if_fatal` lines).
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.248 Cancellation at each await of the server loop
- **From**: A.U35.48.
- **Site**: new test.
- **Change**: `test_cancelling_run_at_each_await_disconnects_and_logs_nothing` drives `cancel_at_each_await()` from
  synchronous scope over `server.run("127.0.0.1", "255.0.0.0")` on a `_FakeUDPS` with one query (the build constructs
  the server and fake inside the swept coroutine); invariants: `CancelledError` raised, `disconnect()` called exactly
  once, `ErrCount == 0`, no further `recvfrom()` after the cancel.
- **Resolved**: —
- **Unit**: U35.
- **Depends**: M.TEST_HELP.067; M.SRC_NET.007.
- **Blast carried by**: —
- **Kind**: test

## tests/test_config_manager.py (→ `tests/test_asy_config_manager.py`)

### M.TEST_UNIT.249 File harness: module name, shared run, write counter, code helpers
- **From**: A.U10.37 (`import config_manager as cm` → `import asy_config_manager as cm`), A.U24.08 (`:21-22` `run`),
  A.U4.06 (`:2324-2352` `_WriteCountingOpen` → shared), A.U0.07 (nine `from collections import namedtuple` in tests →
  module level), A.U24.73 (`Any` sites), A.U2.07 (`:74-78` `_last_errno` reads codes by name), A.U28.28 (`:2360` inline
  `noqa: B905` goes), A.U11.19 (`:2356` comment), A.U10.35/A.U10.18 (`:2118` comment `_config_lock`).
- **Site**: `tests/test_config_manager.py:1-89`, `:2118`, `:2321-2362`.
- **Change**: imports `import asy_config_manager as cm`, `from collections import namedtuple`, `from _async_harness
  import run`, `from _error_codes import code`, `from _write_counters import WriteCountingOpen`; the local `run`, the
  `TYPE_CHECKING` `TypeVar` and `_real_open`/`_WriteCountingOpen` go; every `_WriteCountingOpen(...)` (14 uses) →
  `WriteCountingOpen(cm, ...)` with the same arguments. New `async def _write_flushed(mgr, data)` (`await
  mgr.write_config(data)`, then `await mgr.flush_pending()`, returns the write's result — the convention "Deferred work
  never outlives a `run()` call"). `_last_errno()` → `_newest_code(mgr) -> int` (same body); `_log_entry()` keeps its
  shape, comment → "# (count, codes) of the persisted errors; warnings are asserted by the tests that expect them.",
  the `zip()` line without its noqa (B905 joins the MicroPython-run per-file entries, A.U28.28). `bad_values: list[Any]`
  → `list[object]`. The `:2118` comment names `_config_lock`.
- **Resolved**: —
- **Unit**: U11 (stages U4 counter, U10 names, U24 harness/typing, U28 noqa).
- **Depends**: M.TEST_HELP.043, .045, .062.
- **Blast carried by**: `pyproject.toml` B905 entry → A.U28.28 (TOOL).
- **Kind**: test

### M.TEST_UNIT.250 Schema helpers take typed input only; one file-name builder
- **From**: A.U11.17 (`:123-127`, `:159-162` lose their `None`/`(1, 2, 3)` lines; `:142-144`, `:216-227`, `:749-751`,
  `:759-761` go; `:129-133`, `:147-153` hold), A.U11.32 (`:93-104` hold; new `config_filename()` L1), A.U11.18 (guard
  named: the static schema check).
- **Site**: `tests/test_config_manager.py:93-261`, `:715-822`, `:881-893`, `:1188-1197`.
- **Change**: as A.U11.17 lists, plus the same class at three sites the list does not name, each of which raises once
  the guards are gone: `:719-721` (`type_or_range_error(1, ())`, wrong-length field), `:881-893` (`cfg_vals=None`/`5`
  into `setup()`), `:1188-1197` (a five-element field record into `setup()`) go. `:815-830` (non-string name, stray
  element) hold — no exception path. New: `test_config_filename_builds_the_one_file_name_shape` —
  `cm.config_filename("p/", "SGP40_2") == "p/config_SGP40_2.cfg"` and `cm.config_filename("", "SYSTEM") ==
  "config_SYSTEM.cfg"`.
- **Resolved**: the three unnamed sites are A.U11.17's class (type-violating input that now raises); retired with the
  guard named — `tests_scripts/test_config_schemas.py` rejects a malformed schema statically (A.U11.18, OR111.a (2)).
- **Unit**: U11.
- **Depends**: M.SRC_CORE.046, .047.
- **Blast carried by**: L0 `"config_"` concatenation grep → A.U11.32 (TSC).
- **Kind**: test

### M.TEST_UNIT.251 Numeric coercion: the private halves and the per-kind validators
- **From**: GAP-G13 (M.SRC_CORE.047: `coerce_numeric()` → `_coerce_int()`/`_coerce_float()`; per-kind validators),
  A.U11.S01 (read: `:265-327` tuples hold in value), A.U19.02 + A.U36.513 (`:268`, `:340` comments), A.U24.62
  (`:322-323`), A.U0.39 (`:355`); M.SRC_CORE.047 as amended in gap pass G2 (every validator takes `object`;
  `type_or_range_error()` refuses with `(True, None)`; GAPS_G2 H-2 (b), gap pass G3).
- **Site**: `tests/test_config_manager.py:263-363`; new tests after it.
- **Change**: each `cm.coerce_numeric(v, int) == (True, x)` → `cm._coerce_int(v) == x` (same for `float` →
  `_coerce_float`), each `(False, v)` → `is None`; the identity, int↔float, `-0.0`, fractional, NaN/inf, bool and
  wrong-type tests keep their value lists; the `type(coerced) is …` asserts stay. `:338-344` →
  `test_checked_numeric_refuses_a_non_numeric_kind`: `cm.checked_numeric(5, ("X", "str", None, 1, 5, None)) is None`.
  `:346-363` → `_coerce_float(2**53) == float(2**53)` and `_coerce_float(2**53 + 1) == float(2**53)`, its comment's
  third paragraph → "Accepted risk (owner, 2026-08-24): no registered float field's bounds go near this range; this
  build cannot reproduce the single-precision threshold." Banner `:263-270` → "# Numeric coercion (SPECIFICATION.md
  C.10): the private halves behind checked_int()/checked_float(), / # which the webserver's pause dispatch, the
  generated LED callback and the ISL29125 driver call." `:322-323` → "# on MicroPython bool is not an int subclass
  (py/objbool.c), while CPython's is - type(x) is int states the rule the same way on both". New:
  `test_checked_int_and_checked_float_return_the_typed_value_or_none` — in range → the value with its type (`5.0` for an
  int field → `5`, `5` for a float field → `5.0`), out of range / fractional for int / wrong type → `None`, the special
  with `check_special=True` → the value, with `False` → `None`; `checked_numeric()` dispatches the same.
  `test_a_refusal_carries_no_value`: `type_or_range_error()` answers `(True, None)` for an out-of-range int, a fractional
  value for an int field, a too-long str and an int for a bool field (the second slot is `None`, never the refused
  value). `test_a_list_or_dict_value_is_refused_by_every_validator`: `[5]` and `{"v": 5}` → `None` from
  `checked_int`/`checked_float`/`checked_numeric` and `(True, None)` from `type_or_range_error()`, for an int, a float, a
  str and a bool field; `compare_before_write({"X": [5]}, …)` reports `"X": "Invalid"` and stages nothing.
- **Resolved**: A.U19.02 renames the `:268`/`:340` callers to the webserver's dispatcher; GAP-G13's end state has three
  callers of the per-kind validators and none of the halves outside the module — the banner names all three.
- **Unit**: U11 (stages U0 tag line, U24 comment).
- **Depends**: M.SRC_CORE.047.
- **Blast carried by**: `float_boundary_2pow24.py` → GAP-G13 (HW_DEV).
- **Kind**: test

### M.TEST_UNIT.252 Range checks hold; bool comments state the platform fact
- **From**: A.U24.62 (`:547-549`, `:692-694`; the mypy remark at `:548` stays), A.S0930.09 (read: `:556-565` hold),
  A.U11.S01 (read).
- **Site**: `tests/test_config_manager.py:366-830`.
- **Change**: comments only: `:547` and `:692-694` say "on MicroPython bool is not an int subclass (py/objbool.c), while
  CPython's is — `type(x) is int` states the rule the same way on both"; `:548`'s trailing mypy remark stays. Every
  `type_or_range_error()`/`check_cfg_get_default()` assertion holds (the contract is unchanged, M.SRC_CORE.047), except
  the removals of M.TEST_UNIT.250.
- **Resolved**: —
- **Unit**: U24.
- **Depends**: —
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.253 `setup()`: an absent file is written once with the defaults; error history by code
- **From**: A.U11.19 as superseded by OR136.a (1)-(3) (an absent file is written once, at that boot, with the schema
  defaults through the compare-before-write path; a command-only schema has no file; A-C review fold) (`:838-846`,
  `:1074-1126`, `:1347-1356`, `:2395-2406`; new L1s), OR138.a (1) (a damaged file is a config fault; A-C review fold),
  A.U2.07 (`:2141-2205` counts → codes), A.U14.11 + A.SDEP.08 (`:929-935` comment), A.U35.37 (read: first-boot W24
  retired, checked landed).
- **Site**: `tests/test_config_manager.py:833-1360`, `:2135-2205`, `:2395-2406`.
- **Change**: `:838` → `test_configmanager_writes_the_defaults_once_when_the_file_is_absent`: valid, the file holds the four
  defaults, `WriteCountingOpen(cm)` counts exactly one write-mode open during `setup()`, no persisted entry, no config
  fault. The four special-only tests `:1074-1116` hold as at HEAD (the file written at setup lacks the special key,
  `get_dict([special])` still `None`). `:1118` → `…entirely_special_only_creates_no_file`: a command-only schema has no
  file after setup and after `write_config({"Special": 3})`, no persisted entry (OR136.a (3)). `:1347` (missing parent
  directory) holds as at HEAD with the code by name: the one defaults write fails, valid, defaults served, one
  `code("E", "CFG_FILE_WRITE")`. `:2395` holds as at HEAD (setup creates the valid file the second manager reads).
  `:1200` (non-string field name) and `:1449` (cache after delete) hold as at HEAD (the file exists after setup).
  `:929-935` → "# MicroPython's json.load() pairs tokens in order (Part F.1), re-confirmed on the pinned <pin version>
  interpreter; distinct from the "unterminated" case / # (fixed upstream in 2025, commit 9ef16b466, which only covers a
  missing closing brace or bracket)." (second block stays). `:2157` asserts one `code("E", "CFG_PATH_IS_DIR")`; `:2173`
  adds `code("E", "CFG_NOT_VALID")` (ErrCount 2); `:2189` one `code("W", "CFG_FILE_JSON")`. New:
  `test_an_absent_file_is_written_once_per_boot_and_never_again` (`WriteCountingOpen(cm)`: one write through the first
  setup holding exactly the defaults, then a second manager's `setup()` on the now-present file and an unchanged PUT open
  nothing — one write per file per fresh filesystem, OR136.a (4); the serialise-first half of that write is
  M.TEST_UNIT.257's `:2301`). Config faults (OR138.a (1), U11
  stage of the fault state): a file that is unparseable (`:929` corrupt JSON), not an object, or invalid (a value outside
  its field) reports the store's config fault after `setup()`, and still reports it after the boot repair rewrote the
  file; an absent file, a valid file and a directory path report none (the directory is `CFG_PATH_IS_DIR`'s refusal,
  not a file that existed) — the fault accessor is M.SRC_CORE's ([fold F03 M_SRC_CORE]).
- **Resolved**: A.U11.19's "a missing file writes nothing" (OR71.a (2)'s first-boot clause) is superseded by OR136.a
  (most recent owner decision wins): the HEAD expectations of `:838`, `:1074-1116`, `:1200`, `:1347`, `:1449` and `:2395`
  return, `:838` gaining the write count; A.U11.19's surviving halves stay — the unreadable file (M.TEST_UNIT.254), the
  command-only schema (`:1118`) and the error-history codes. Which damaged shapes count as "invalid" (a value outside its
  field certainly; a missing or unknown key per M.SRC_CORE's definition) is decided with the product change, the rows
  following it.
- **Unit**: U11 (stages U2 codes, U14 comment; the version stamp with the pin move, U0/U37).
- **Depends**: M.SRC_CORE.043 (as the fold amends it, OR136.a); [fold F03 M_SRC_CORE] (the config-fault state);
  M.TEST_HELP.062 (`WriteCountingOpen`).
- **Blast carried by**: `tests/test_base_classes.py:1013-1016, 1449-1452` → M.TEST_UNIT.229, .230 (this file's base
  counterpart, merged there: no persisted entry for an absent file, a command-only schema writes no file — both hold
  under OR136.a); SPEC F.1 paragraph → A.U14.11 (SPEC).
- **Kind**: test

### M.TEST_UNIT.254 `setup()`: an unreadable file is never overwritten
- **From**: A.U11.20 (`:2275-2298`; new L1s), A.U35.43 (2) (`:869-878` goes: a non-string filename), OR138.a (1) (an
  unreadable file is a config fault, listed for the rest of the boot; A-C review fold).
- **Site**: `tests/test_config_manager.py:869-878`, `:2275-2298`; new tests.
- **Change**: `:869-878` goes (typed `str` filename; guard: mypy on every constructor call, G5/R18). `:2275` →
  `…memoryerror_from_json_load_serves_defaults_and_keeps_the_file`: valid, defaults served, the file still holds
  `{"Count": 7}`, one `code("W", "CFG_FILE_UNREADABLE")`, `mgr.writable is False`, `write_config({"Count": 8}) == (False,
  {})`, and the store reports its config fault. New: `test_an_eio_on_stat_or_open_leaves_the_file_untouched` — `cm.os` replaced by a module whose `stat` raises
  `OSError(5)`, then (second case) `cm.open` raising `OSError(5)` for reads (both restored in `finally`): zero write-mode
  opens, file bytes unchanged, one W22, defaults served, `write_config()` → `(False, {})`, the config fault reported.
  An `ENOENT` from the same stand-in is no fault: the absent-file path of M.TEST_UNIT.253 runs (one defaults write).
- **Resolved**: —
- **Unit**: U11.
- **Depends**: M.SRC_CORE.043; [fold F03 M_SRC_CORE] (the config-fault state).
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.255 Readers: exact-type getters, one CONTRACT entry per refusal
- **From**: A.U11.29 (`:1534-1540` inverts; new L1s; `:1496-1532`, `:1542-1552` hold), A.U3.05 (refusals persist one
  24 in the store; its "none in the caller" half dropped, OR140.a (7); A-C review fold), A.U11.17 (`:1572-1583` goes),
  A.U35.43 (2) (`:1462-1470` goes).
- **Site**: `tests/test_config_manager.py:1359-1584`.
- **Change**: `:1496`, `:1504`, `:1523` keep `None` and assert one `code("E", "CONTRACT")` entry (comments → "# a str value
  is not an int/float"); `:1534` → `test_get_str_values_refuses_a_non_str_value`: `get_str_values(_VAL_INT) is None` plus
  one CONTRACT; `:1542` comment → "# the stored value's exact type is checked (a bool field holding a str is refused)"
  plus one CONTRACT; `:1554` (unknown key) asserts one CONTRACT. `:1462` and `:1572` go (typed keys; guard: mypy). New:
  `test_get_int_values_never_truncates_a_float` — a float field holding `2.5` read by `get_int_values` → `None`, holding
  `2.0` → `[2]`; a bool field → `None`.
- **Resolved**: —
- **Unit**: U11 (stage U3 entries).
- **Depends**: M.SRC_CORE.048.
- **Blast carried by**: caller-module L1 (one entry in `CFGMGR_<name>` and the caller's own entry, per layer, OR140.a
  (7)) → the base/driver files' sections (M.TEST_UNIT.017, .060, .086, .091, .113, .143, .218).
- **Kind**: test

### M.TEST_UNIT.256 `write_config()`: own schema, compare-before-write, stored-form floats
- **From**: A.U11.24 (62 second-argument sites; `:1826-1836` goes), A.U11.25 (`:1900-1911` goes), A.U4.01 (`:1813-1823`
  holds; outcome-row L1s), A.U11.21 (`_stored_float` L1), A.U2.07 (`:1988` 14 → CFG_FILE_WRITE), A.U35.43 (2) (read),
  OR136.a (1) (`:1949`'s file exists after setup; A-C review fold).
- **Site**: `tests/test_config_manager.py:1586-2133`.
- **Change**: every `write_config(data, <schema>)` loses its second argument (no test's outcome depends on a narrower
  schema: each passes a sub-schema of the manager's own records, grep). `:1813` asserts `(False, {})` and one
  `code("E", "BAD_ARG")`. `:1784` simulates the drift on `_cache` (`del mgr._cache["Count"]`), the file no longer read.
  `:1914` writes the corrupted file by hand after setup, then `_write_flushed` → "Valid", file holds 7. `:1949` keeps
  `os.remove(path)` (setup wrote the absent file's defaults, OR136.a), its write/read/flush run as one coroutine and it
  asserts `code("E", "CFG_FILE_WRITE")`. Tests reading the file or `_cache` after a write (`:1638`, `:1655`, `:1703`, `:1736`,
  `:1762`, `:1860`, `:1931`, `:2117`) do so through `_write_flushed` or one coroutine ending in `flush_pending()`.
  New: `test_compare_before_write_outcome_rows` (unknown key, type error, range error, `always` key, missing current key,
  equal at resolution, different at resolution, int-for-float coercion — each row's outcome and returned value) and
  `test_compare_before_write_refuses_a_non_object` (`None`, `5`, `"abc"`, `[…]` → `None`);
  `test_a_float_equal_in_stored_form_is_unchanged` (`cm._stored_float` replaced by a 3-decimal round, restored in
  `finally`: `write_config({"Offset": 1.23456})` stages `1.235`, the repeat answers "Unchanged" with zero writes).
- **Resolved**: A.U35.43 (2) removes "the tests passing … a non-dict `data`" while A.U4.01 keeps `:1813` "through the
  `None` sentinel": the product keeps the branch (`compare_before_write()` returns `None` and `write_config()` logs
  BAD_ARG, M.SRC_CORE.044), so the test holds as A.U4.01 says.
- **Unit**: U11 (stages U2 codes, U4 primitive rows).
- **Depends**: M.SRC_CORE.044, .047.
- **Blast carried by**: L3 float round trip → A.U11.21 (HW_DEV).
- **Kind**: test

### M.TEST_UNIT.257 Deferred flush: create then stage, commit, supersede, serialise first
- **From**: A.U11.22 (task-creation failure L1), A.U11.28 (equal snapshot opens nothing; deferred `create_task` failure;
  `:1736-1782` hold), A.U35.43 (1) (supersede L1), A.U11.23 (`_MemoryErrorJson.dumps`; `:2239-2272`, `:2301-2320`; serialise-
  first L1), A.U10.20 (unserialisable snapshot L1), A.U11.19 (`:2301` starts from a readable file; as superseded by
  OR136.a (1), the absent-file case returns beside it; A-C review fold).
- **Site**: `tests/test_config_manager.py:1729-1782`, `:2206-2320`; new tests.
- **Change**: `_MemoryErrorJson` gains `dumps(obj)` raising on `raise_on_dump` (`dump` stays for symmetry of the
  fake; comment names both). `:2239`: write and flush in one coroutine under the fault; the file still holds setup's
  defaults `{"Count": 5}` byte for byte (serialisation fails before the open), `_cache == {"Count": 8}`, one `code("E",
  "CFG_FILE_WRITE")`; then "Unchanged" for 8 and a flushed 9 writes `{"Count": 9}` (the truncation comment goes).
  `:2301` keeps HEAD's absent file (the defaults write's `dumps` fails: no file appears, valid, defaults served, one
  `code("E", "CFG_FILE_WRITE")` — the one write of OR136.a (1) goes through the serialise-first path) and gains a second
  case from a readable file holding an out-of-range `Count`: the repair's `dumps` fails, valid, defaults served, newest
  code CFG_FILE_WRITE, file bytes unchanged. New: `test_a_failed_task_creation_stages_nothing` —
  `cm.asyncio.create_task` replaced by a raiser of `MemoryError` (restored in `finally`), for `defer=False` and
  `defer=True`: `(False, {})`, `get_dict()` the old value, `_staged is None`, one `code("E", "ALLOC")`;
  `test_a_flush_equal_to_the_cache_opens_nothing`; `test_two_deferred_writes_then_one_commit_write_the_second_once`
  (`WriteCountingOpen`: one write holding the second value, the first task returns without writing);
  `test_flush_pending_releases_an_uncommitted_deferred_write`; `test_a_failed_serialisation_leaves_the_file_byte_identical`
  (pre-existing file, `dumps` raising: bytes equal, zero write-mode opens); `test_an_unserialisable_snapshot_ends_the_
  flush_task_with_one_unexpected_entry` (`mgr._cache["Name"] = object()` poked, then a valid flushed change: one
  `code("E", "UNEXPECTED")`, `_pending_flush is None`).
- **Resolved**: —
- **Unit**: U11.
- **Depends**: M.SRC_CORE.041, .044.
- **Blast carried by**: `tests/test_base_classes.py` push/write-count L1s → M.TEST_UNIT.230;
  `tests_scripts/test_device_script_config_flush.py` → A.U11.28 (TSC).
- **Kind**: test

### M.TEST_UNIT.258 Write-count guarantees and the source pin
- **From**: A.U11.19 (`:2364-2376`, `:2409-2416`, `:2419-2433`, `:2472-2493`, `:2496-2509` start from a readable file
  with a bad key) superseded by OR136.a (1) (an absent file's one defaults write is the write those tests fail, as at
  HEAD; A-C review fold), A.U4.02 (unchanged PUT opens nothing; `:2472` extended past the reboot), A.U2.07 (`[4]`, `[14, 12, 14,
  10]`), A.U35.43 (2) (`:2409`'s `TypeError` class), A.U11.23 (`json.dump(` count 0), A.U4.01 (source pin covers the new
  function), A.U10.35 (`self._config_file`), A.U11.28 (read: `create_task(` count 1 holds).
- **Site**: `tests/test_config_manager.py:2321-2541`.
- **Change**: the five setup-write-failure tests keep HEAD's absent file (the one write of the defaults is the write
  that fails; `:2496`'s next boot finds the file still absent and its one write is the defaults again, comment "# the
  next boot's one write of the defaults"); each `(1, [4])` → `(1, [code("E", "CFG_FILE_WRITE")])`;
  `:2409` iterates `OSError(28)`, `OSError(5)`, `MemoryError` (the `TypeError` case goes: the path is a typed `str`);
  `:2453` → `[CFG_FILE_WRITE, BAD_ARG, CFG_FILE_WRITE, BAD_ARG]` by `code()` (alternating codes: four slots under the
  newest-entry rule). Each write/flush pair runs as one coroutine. `:2472` continues after the fresh boot: the same
  `{"Count": 3}` again answers "Unchanged" with zero writes (A.U4.02, no second copy of the test). `:2529`:
  `source.count('open(self._config_file, "w")') == 2`, `source.count('"w"') == 2`, `source.count("json.dump(") == 0`,
  `create_task(` count 1, and the forbidden-token scan also covers `compare_before_write()`'s body. New:
  `test_an_unchanged_put_schedules_no_flush` (`_pending_flush is None`, zero writes).
- **Resolved**: —
- **Unit**: U11 (stages U2 codes, U4 counter).
- **Depends**: M.SRC_CORE.043, .044; M.TEST_HELP.062.
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.259 Closing for a reset, `delete_file()`, the store-level interleavings
- **From**: A.U11.04 (closed-store L1s), A.S0930.21 (f) (`delete_file()`), A.S0930.22 (2) (config flush in flight at
  close), A.S0930.16 (read: `:1736-1782`, `create_task(` count hold), OR138.a (2) (the delete never reads the file and
  does not depend on the store's readable state; A-C review fold).
- **Site**: new section after `:2135`.
- **Change**: `test_a_closed_store_refuses_writes_and_opens_nothing` (`close_writes()`, then `write_config()` → `(False,
  {})`, zero write-mode opens); `test_delete_file_*` — an existing file → `True`, gone; absent → `True`; `cm.os.remove`
  raising `OSError(5)` twice → `False`, one console line, file present; raising once then succeeding → `True`, gone;
  `write_config()` afterwards → `(False, {})`. `test_delete_file_removes_an_unreadable_or_damaged_file_without_reading_
  it` (OR138.a (2)): a store whose `setup()` met an `OSError(5)` read (`writable is False`, the config fault reported)
  and a store whose file holds corrupt JSON each answer `True` and the file is gone, with `WriteCountingOpen(cm)`
  counting zero opens of any mode during `delete_file()`. Interleavings, each forced by a gate, never a sleep: (a) a flush held at
  the lock (the test holds `mgr._config_lock`) when `close_writes()` + `flush_pending()` arrive — after release the
  file holds the accepted value; (b) a `write_config()` suspended inside the lock (its logger's `err_s` gated on an
  `asyncio.Event`, one invalid key in the request) finishes staging and its flush is the one `flush_pending()` awaits;
  (c) a `write_config()` queued behind the held lock at close time answers `(False, {})`.
- **Resolved**: A.S0930.22 lists `tests/test_config_manager.py` beside the system-service sequence; its (2) store
  mechanics land here, the command-level interleavings in `tests/test_system_service.py` (as M.TEST_UNIT.048 placed
  the FRAM half). A "gated `open` stand-in" cannot suspend (`open()` is synchronous); the lock and the logger are the
  store's two await points inside the write path, so the gates sit there.
- **Unit**: U11 (A.S0930 cases land with A.S0930.16, the reset unit); stage U20 (A-C review fold): the unreadable/damaged-
  file deletion test, with the never-reading delete path (OR138.a (2)).
- **Depends**: M.SRC_CORE.041, .042; [fold F03 M_SRC_CORE] (the delete path that never reads).
- **Blast carried by**: twin/L3/L4 reset legs → A.S0930.27-.29 (TWIN, HW_DEV, HW_BENCH).
- **Kind**: test

## tests/test_crc_checks.py (→ `tests/test_asy_crc_checks.py`)

### M.TEST_UNIT.260 Names, private state, shared run, the polynomial argument
- **From**: A.U10.37/A.U10.38 (`from asy_crc_checks import CRC8, CRC16, CRC32, CRCBase, CRCPass`), A.U10.35 + M.SRC_CORE.115
  (attribute reads `:36, :42, :126, :132, :258, :282, :346-395, :576, :702, :725` → `_all_set`, `_poly`, `_num_bytes`,
  `_inc_crc`), GAP-G11 + A.U35.44 (`:36`, `:42` call `_crc()` with its real polynomial — hold, gaining the argument),
  A.U24.08 (`:17-18` `run`), A.U16.05 (`:719` comment), A.U24.73 (`Any`).
- **Site**: `tests/test_crc_checks.py:1-42`, the attribute sites above, `:711-720`.
- **Change**: imports as above plus `from _async_harness import run`; the local `run` and its `TypeVar` go. `:36`
  `run(crc8._crc(data, crc8._all_set, 0x31))`, `:42` likewise. Section banners and test names read `CRCPass`/`CRCBase`
  (`test_crc_pass_*` names unchanged). `:716` `crc8._num_bytes = 2**62`; `:719` comment names "the RegionBuffer tests"
  (A.U16.05's rename). `:28-31` keep their vectors.
- **Resolved**: —
- **Unit**: U10 (stages U12 `_crc` argument with A.U12.01, U24 harness).
- **Depends**: M.SRC_CORE.115, .116; M.TEST_HELP.043.
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.261 Vectors cited to their datasheets; CRC16/CRC32 check values
- **From**: A.U12.04 (`:27`, `:40` comments), A.U12.01 (two vector tests, the non-default-init round trip; yield tests
  `:773-831` and `:69, :452-494, :501-525, :607-620` hold), A.U24.39 (`:360` reference values), A.U31.01 (read: the
  stall-budget row cites this file; no change).
- **Site**: `tests/test_crc_checks.py:26-42`, `:360-363`; new tests after `:620`.
- **Change**: `:27` → "# SGP40 datasheet v1.2 Table 10: the CRC byte printed beside the default, minimum and maximum
  RH/T tick words."; `:40` → "# SGP40 datasheet v1.2 Table 7's example, CRC(0xBE 0xEF) = 0x92; the SCD30 Interface
  Description §1.1.3 gives the same.". `:360` `test_init_boundary_values_accepted` compares `add(b"x", init=0) ==
  b"x\x41"` and `add(b"x", init=0xFF) == b"x\xed"` under the comment "# CRC-8 poly 0x31 over 0x78, MSB first: from
  init 0x00 the register ends at 0x41, from 0xFF at 0xED." New: `test_crc16_matches_the_ccitt_false_check_value`
  (`run(CRC16()._crc(bytearray(b"123456789"), 0xFFFF, 0x1021)) == 0x29B1`), `test_crc32_matches_the_mpeg2_check_value`
  (`0x0376E6E7` for `b"123456789"`, `0xE55E964F` for `bytearray(256)`, `0x494A116A` for `bytearray(range(256))`, poly
  `0x04C11DB7`, init `0xFFFFFFFF`) with A.U12.01's oracle comment, and `test_crc32_round_trips_at_a_non_default_init`
  (`init=0x12345678`).
- **Resolved**: —
- **Unit**: U12 (stage U24 reference values).
- **Depends**: M.SRC_CORE.116.
- **Blast carried by**: phase C allocation measurement → A.U12.01 (HW_DEV).
- **Kind**: test

### M.TEST_UNIT.262 Pass mode validates bounds; an out-of-range polynomial is pure pass-through
- **From**: A.U12.02 (pass-mode bound L1s; `:200-205` hold), M.SRC_CORE.131 (lead ruling, AC_NOTES 39: one case per
  width).
- **Site**: `tests/test_crc_checks.py:118-205`, `:342-363`; new tests.
- **Change**: `:346` `test_poly_above_all_set_degrades_to_pass_mode` also asserts `base.length() == 0`. New:
  `test_pass_mode_add_into_and_check_from_refuse_bad_bounds` — for `CRCPass()` and `CRC8(poly=None)`: `add_into(buf, 0)`,
  `add_into(buf, -1)`, `add_into(buf, 1, start=-1)`, `add_into(bytearray(2), 3)` and the same four through
  `check_from()` → `None`. `test_a_polynomial_above_the_width_mask_is_pure_pass_through` — per width, `CRCBase(1, 0x1FF,
  ">B")`, `CRCBase(2, 0x1FFFF, ">H")`, `CRCBase(4, 0x1FFFFFFFF, ">L")`: `length() == 0`, `add(data)` returns `data`
  unchanged, and `add_into(buf, 2)` on a buffer one CRC wider than the payload returns `2` with `buf` byte-identical.
- **Resolved**: —
- **Unit**: U12 (A.U12.02); the M.SRC_CORE.131 cases land with M.SRC_CORE.116's unit (U35).
- **Depends**: M.SRC_CORE.117, .131.
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.263 Trailing zero padding passes every check
- **From**: A.U12.04 (new test).
- **Site**: new test after `:620`.
- **Change**: `test_trailing_zero_padding_passes_every_check_so_callers_pass_the_true_length` — for `CRC8`, `CRC16`,
  `CRC32`, a payload with its CRC plus k = 1..3 zero bytes: `check(padded)` returns `padded` minus its last
  `_num_bytes`, `check_from(padded, len(padded))` returns `len(padded) - _num_bytes`, and a `run_inc()`/`check_inc()`
  sequence over `padded` returns the same — the documented limitation (`asy_crc_checks.py:8-10`) pinned.
- **Resolved**: —
- **Unit**: U12.
- **Depends**: —
- **Blast carried by**: —
- **Kind**: test

## tests/test_fakes.py (new: `tests/test_fake_timer_and_network.py` renamed)

### M.TEST_UNIT.264 One fake-fidelity file: rename, the machine contract, per-fake cases
- **From**: A.U24.16 (the rename, G2/R26 "no second fakes file"; the `Pin` cases), A.U24.17 (the file runs
  `tests/_machine_contract.py` against `tests/machine.py`), A.U24.20 (`I2C` per bus id), A.U24.24 (RTC), A.U24.26 (UART
  `rxbuf`), A.U24.81 (one `WLAN` object per interface), GAP-T2/T3/T5 (the fake end states the cases pin).
- **Site**: `tests/test_fake_timer_and_network.py:1-96` (`git mv` → `tests/test_fakes.py`); new tests.
- **Change**: docstring → "Fidelity tests for the tests/ hardware fakes other suites lean on: each case states what
  rp2 does (the machine contract, Timer one-shots, network bounds and seeds, Pin/I2C/RTC/UART per-peripheral state);
  a fake that drifts from silicon lets a test pass for code that fails on the board." (3 lines). The seven HEAD tests
  hold; the restoring tails `network.country("DE")` (`:73`) and `network.hostname("SensorNode")` (`:80`) go (the
  network fake's `reset_test_state()` restores the seeds after each test, M.TEST_HELP.007 (4)); `wlan: Any` →
  `wlan = network.WLAN(network.STA_IF)` read through the fake's `TEST_API` (no `Any`). New:
  `test_the_unit_machine_fake_meets_the_shared_contract` — every `_machine_contract.ALL_CHECKS` entry against `machine`
  (the completeness test is the contract module's); `Pin` cases exactly as A.U24.16 lists (`Pin(5, Pin.IN)` clears an
  earlier pull, `Pin(5)` changes nothing, `"GP5"`/`"GPIO5"` alias `Pin(5)`, `Pin(30)`/`Pin(1.5)` → `ValueError("invalid
  pin")`, `Pin("GP23")` → `ValueError('unknown named pin "GP23"')`, `Pin("LED", Pin.IN, Pin.PULL_UP)` raises, open-drain
  release reads the external level, `ALT` with `alt=Pin.ALT_I2C` recorded); `I2C` (a second `I2C(0, …)` sees the first's
  registers and faults, a new `timeout` updates it, `reset_id(0)` empties it, `raise_on_construct` raises once); RTC
  (`(2026, 9, 30, 0, 12, 0, 0, 99)` reads back weekday 2 and subseconds 0, a 7-tuple raises `ValueError`, `(2026, 2, 29,
  …)` reads back 2026-03-01); `UART(0, …, rxbuf=8).rxbuf == 32`; `WLAN(STA_IF) is WLAN(STA_IF)`, `deinit()` drops both
  links, counters reset between tests; `machine.reset()` raises `SimulatedResetError` after counting and `WDT(timeout=
  8389)` raises `ValueError` (through the contract checks).
- **Resolved**: —
- **Unit**: U24.
- **Depends**: M.TEST_HELP.007, .010-.013, .021, .048.
- **Blast carried by**: the twin runner `tests/test_digital_twin_machine.py` → A.U24.17 (TWIN); `tests_scripts/
  test_import_placement.py` / file lists naming the old path → A.U24.16 (TSC, if any by grep).
- **Kind**: test

## tests/test_fram_integration.py

### M.TEST_UNIT.265 Harness, names, constructors and the reboot rebuild
- **From**: A.U24.08 (`:42-43` `run`), A.U24.49 + M.TEST_HELP.057 (`make_manager` → `make_fram_manager()`; the reboot
  rebuild `manager2.fram._spidev.spi._spi = chip` at `:240, :283, :320` → `make_fram_manager(chip=chip)`), A.U24.01
  (`:37-39` `_STATUS_BUSY` → `src_const`), A.U10.37/A.U10.38 (`FRAMManager`, `FRAMChunk`, `asy_crc_checks`, `CRCPass`,
  `asy_base_classes`, `asy_print_log`; docstring names), A.U5.02 (the 12 `SensorReader(Meas(…), 3, fram=manager)` calls
  `:71-403`), A.U10.10 (`reader.pr.setup()` → `reader.setup()`), A.U16.18 (`:92` unpack order), A.U24.56 (`:300`),
  A.U2.09 (the 19 code lines: literal errno/wrnno values), A.U3.04 dropped (OR140.a (7); the 19 lines are test-chosen
  codes, so nothing here depended on it; A-C review fold), A.U24.73 (`Any`).
- **Site**: `tests/test_fram_integration.py:1-56`, `:68-415`.
- **Change**: docstring → "Full-stack integration: tests/_fram_chip_fake.py's MB85RS64V under asy_spi_driver/
  asy_fram_driver/asy_fram_manager and their real consumers in asy_print_log/asy_base_classes - mocked at the SPI bus,
  not at FRAMManager's boundary (SPECIFICATION.md Part E.4)." (3 lines). Imports per the names above plus `from
  _async_harness import run`, `from _fram_builders import make_fram_manager`, `from _src_const import src_const`, `from
  _error_codes import code`, `from asy_print_log import LogConfig`; the local `run`, `make_manager` and `TypeVar` go.
  `_STATUS_BUSY = src_const("src/asy_fram_manager.py", "_STATUS_BUSY")` under "# The chunk's busy status value, read
  from source.". Each reader is `SensorReader(Meas(…), log=LogConfig(manager, 3, None))` and is set up with
  `run(reader.setup())`. The reboot tests build `manager2, _ = make_fram_manager(chip=chip)` (same chip, fresh objects).
  `:92` → `write_ok, *_ = await value_chunk.write_into(buf)`. Each literal `errno=`/`wrnno=` value and the
  `ErrNum[-1] == <n>` it is read back as become distinct catalog codes by name (`code("E", "CALLBACK")`, `code("E",
  "UNEXPECTED")`, `code("E", "BAD_ARG")`, `code("E", "CONTRACT")`, `code("E", "LOCK_TIMEOUT")`, `code("W",
  "STORED_DEFAULT")`, one per HEAD number); `:300` "(project owner, 2026-09-11)" → "(owner, 2026-09-11)".
- **Resolved**: —
- **Unit**: U24 (stages U2/U3 codes, U5 constructors, U10 names/setup, U16 unpack).
- **Depends**: M.TEST_HELP.043, .044, .045, .057; M.SRC_CORE (`LogConfig`, A.U16.18's return order).
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.266 The bus-fault comment states rp2's one SPI fault; no collect props up the cycle test
- **From**: A.U16.14 (`:3-5`), A.U25.18 (read: the comment is U16's), A.U30.15 (`:159-163`, `:177`, `import gc`), A.U29.03
  (read: the digit strings are FRAM payload bytes, not the hotspot password — no change).
- **Site**: `tests/test_fram_integration.py:3-8`, `:158-180`.
- **Change**: `:3-5` → "# No bus-level fault here: rp2 SPI's only one, an RX overrun raising OSError(EIO) on a 32+ byte
  read (SPECIFICATION.md / # F.5.2), is modelled by tests/machine.py's rx_overrun and driven through this same stack in
  test_asy_fram_manager.py." The `gc.collect()` in the 40-cycle loop and its two-paragraph comment go, the loop stays as
  the state-leak regression ("# Forty cycles: a stale CRC, verify counter or lock state would show by the second."), and
  `import gc` goes. Proof owed by the landing unit: the file ten times at `gc.threshold(-1)` and ten at
  `GC_THRESHOLD=32768` with zero markers of either spelling; a failure is root-caused at the allocation (A.U30.15),
  never patched back with a collect.
- **Resolved**: —
- **Unit**: U30 (stage U16 comment).
- **Depends**: M.SRC_CORE (FRAM manager allocation shape, U16/U30).
- **Blast carried by**: —
- **Kind**: test

## tests/test_framing_codecs.py (→ `tests/test_asy_framing_codecs.py`)

### M.TEST_UNIT.267 Names, the bounded shared run, no test-only counter
- **From**: A.U10.37/A.U10.38 (`from asy_framing_codecs import COBS_DELIMITER, FramingCOBS, FramingPass`; docstring),
  A.U10.29 (read: `COBS_DELIMITER` stays public for this import), A.U24.08 (`:21-22` bounded copy keeps its 5 s),
  A.U8C.34 (`:22` `l1.framing_codecs_run_bound_s`), A.U12.16 (`:176`, `:187-195`), A.U16.05 (`:165` comment), A.U12.05
  (read: `:82-125` already pin the property).
- **Site**: `tests/test_framing_codecs.py:1-37`, `:163-195`.
- **Change**: docstring line 1 names `src/asy_framing_codecs.py`; `from _async_harness import run`; `_RUN_BOUND_S = 5
  # @tunable l1.framing_codecs_run_bound_s = 5` and the helpers call `run(codec.…(…), _RUN_BOUND_S)` (the local `run` and
  `TypeVar` go); type hints `FramingPass | FramingCOBS`. `:165` comment "the same guard RegionBuffer applies". `:176`
  `assert codec._scratch is None`. `:187-195` → `scratch = codec._scratch` before the two encodes, `codec._scratch is
  scratch` after, and the second encode's bytes sit where the first's were (reuse seen from outside).
- **Resolved**: —
- **Unit**: U12 (stages U8 tag, U10 names, U24 harness).
- **Depends**: M.SRC_CORE.120, .121; M.TEST_HELP.043.
- **Blast carried by**: SPEC Part N row → A.U8.01 (SPEC).
- **Kind**: test

### M.TEST_UNIT.268 Every length round-trips; views alias the scratch; decode bound
- **From**: A.U12.17 (two L1 tests), A.U17.22 (every length 0 … 262 at `max_frame = 262`; one byte past the encoded
  bound refused; `:83-189` hold).
- **Site**: new tests after `:125`.
- **Change**: `test_cobs_round_trips_every_length_up_to_the_frame_bound` (sizes 0..300 step 1; all-zero, no-zero and
  zero-every-third patterns; `FramingCOBS(303)`); `test_a_returned_view_aliases_the_scratch_until_the_next_encode`
  (A.U12.17's snapshot comparison); `test_a_262_byte_frame_bound_decodes_every_length_and_refuses_one_past`
  (`FramingCOBS(262)`: every frame length 0..262 encodes and `decode_from()` returns the length; a decode input of
  `max_encoded(262)` bytes — one past `max_encoded(262) − 1` — returns `None`).
- **Resolved**: —
- **Unit**: U17 (A.U12.17's tests stage in U12 and hold under U17's bound, `FramingCOBS(303)` passing either rule).
- **Depends**: M.SRC_CORE.122.
- **Blast carried by**: SPEC G.2 aliasing sentence → A.U12.17 (SPEC); the driver/comm halves → M.TEST_UNIT.153-.177.
- **Kind**: test

## tests/test_generated_boot_entry.py (new)

### M.TEST_UNIT.269 Every generated boot entry executes at L1
- **From**: A.U24.55 (1) (the L1 half; (2) is `tests_scripts/test_digital_twin_generated_boot.py`'s, TSC).
- **Site**: new `tests/test_generated_boot_entry.py`.
- **Change**: per derived device (the device list from `tests/_generated_tree.py`, `require_fresh()` first): read
  `build/generated_src/sensortask_<device>_main.py` (M.GEN.019's name) and `exec()` it in a fresh namespace from the
  test's synchronous scope, with `sys.modules["sensortask_<device>"]` a stub module whose `async def main(*, watchdog,
  **_kw)` records the watchdog and `gc.threshold()` at its call, and `asyncio.new_event_loop` wrapped from outside to
  record its call; `sys.path`, `sys.modules` and `asyncio.new_event_loop` restored in `finally`. Case 1: the stub saw a
  `machine.WDT` whose timeout is 8000 (read from `src_const("buildgen/codegen.py", "_WDT_TIMEOUT_MS")`, not a copy) and
  threshold 32768, `micropython.alloc_emergency_exception_buf` was reached (the entry ran past it), and
  `new_event_loop` ran in the `finally`. Case 2: the stub's `main()` raises `RuntimeError("stub")` — it propagates out of
  `exec()` and `new_event_loop` still ran. The no-autostart entry (`…_main_noautostart.py`): executing it prints the
  manual start line naming `main(watchdog=WDT(timeout=8000))` (`tests/_recording_print.py`) and never calls `main()`.
  `gc.threshold` is restored by the after-each hook (A.U24.07). Module docstring ≤ 3 lines naming the rule (G8/R03:
  every generated module and its boot entry is executed by at least one tier).
- **Resolved**: A.U24.55 names the file `build/generated_src/<device>_boot.py` (A.U24.54); M.GEN.019 settles the name
  `sensortask_<device>_main.py` (M_GEN gap 1) — the test reads that name. A.U24.55 covers the autostart entry; the
  no-autostart entry M.GEN.019 also emits is executed here too so both entries meet G8/R03 (agent decision D-T26).
- **Unit**: U24.
- **Depends**: M.GEN.001, M.GEN.019; M.TEST_HELP.044, .046, .050; A.U24.54 (the generated tree, SCR).
- **Blast carried by**: SPEC L.5 "the boot entry is executed at L1" → A.U24.55 (SPEC); twin half → A.U24.55 (2) (TSC).
- **Kind**: test

## tests/test_math_helpers.py

### M.TEST_UNIT.270 Wet bulb: the cold-dry corner refused; edge inputs against hand-worked values
- **From**: A.U12.06 (`:49-51` corrected; new corner L1s; `:25-68` hold), A.U24.39 (`:49` (rewritten by A.U12.06),
  `:118`, `:183`, `:328`, `:493`, `:541` compared with hand-worked references; `:236`/`:287` — the humidity helpers stay,
  OR140.a (4): those two land in M.TEST_UNIT.271's aligned humidity section; A-C review fold).
- **Site**: `tests/test_math_helpers.py:49-51`, `:118-120`, `:183-185`, `:328-330`, `:493-495`, `:541-543`; new test after
  `:68`.
- **Change**: `:49` asserts `(-20.0, 75.0)`, `(10.0, 5.0)`, `(50.0, 5.0)`, `(50.0, 99.0)` accepted (the corner line's
  end points and the far edge; Stull 2011 Fig. 3). New `test_wet_bulb_is_refused_in_the_cold_dry_corner`: `(-10.0,
  20.0)`, `(-20.0, 74.9)`, `(5.0, 15.0)` → `None`, `(5.0, 20.0)` accepted, and the paper's worked example `(20.0, 50.0)`
  → 13.699 ± 0.001. Edge inputs with the arithmetic in a ≤ 3-line comment each: `dew_point(50.0, 100.0)` → 50.0 (RH 100 %
  makes the Magnus log term 0) and `dew_point(-40.0, 0.1)` → −88.357 (Sonntag ice branch 22.46/272.62, ln 0.001);
  `pressure_at_height(300.0, -9000.0, -40.0)` → 1121.6 hPa and `(1250.0, 9000.0, 85.0)` → 529.76 hPa (barometric
  formula with the inlined g, M, R); `rgb_to_hsb(0, 0, 0) == (0.0, 0.0, 0.0)` and `(1, 1, 1) == (0.0, 0.0, 1.0)` (HSB
  hexcone: no chroma, brightness the max); `chromaticity_xy(1e-12, 0, 0)` and `(1e9, 0, 0)` → `(1.0, 0.0)` (x = X/(X+Y+Z));
  `cct_mccamy(0.0, 0.0)` → 2021.3 K (n = −0.332/0.1858), each at the neighbouring tests' tolerance.
- **Resolved**: —
- **Unit**: U12 (stage U24 references).
- **Depends**: M.SRC_CORE.126.
- **Blast carried by**: SCD30 `WetBulb` in the corner → A.U12.06 (SRC_SENS, behaviour only).
- **Kind**: test

### M.TEST_UNIT.271 `altitude_baro` tests renamed; humidity-conversion tests kept and aligned
- **From**: A.U12.08 (`:139-201` banner and ten tests), A.U12.09 dropped (OR140.a (4): `abs_humidity()`/`rel_humidity()`
  stay, their tests aligned with the other helpers' and the helpers with the no-clamp rule; A-C review fold), A.U24.39
  (`:236`, `:287` compared with hand-worked references, moved here from M.TEST_UNIT.270).
- **Site**: `tests/test_math_helpers.py:138-299`.
- **Change**: banner `pressure_at_height`; every `mh.altitude_baro(` → `mh.pressure_at_height(` and `test_altitude_baro_*`
  → `test_pressure_at_height_*` (mechanical). The `abs_humidity`/`rel_humidity` section (`:204-299`) stays and takes the
  neighbouring helpers' shape: one banner per function; `None` inputs; reference vectors with the arithmetic in a ≤ 3-line
  comment each, at the neighbouring tests' tolerance, replacing the range check `8.0 < result < 9.5` (`:213-216`) — the
  legacy Magnus form `13.23454 · RH / (T + 273.15) · 10^(a·T / (b + T))`, water branch a 7.5, b 237.4, ice branch 7.6,
  240.7: `abs_humidity(20.0, 50.0)` → 8.6365 g/m³, `(40.0, 100.0)` → 50.983, `(-30.0, 100.0)` → 0.4505 (ice branch),
  `(0.0, 100.0)` → 4.8452 and `(-0.1, 100.0)` → 4.8118 (the branch switch at 0 °C); the boundary tests `:236`/`:287`
  compare with those hand-worked values instead of `is not None`; out-of-domain inputs and NaN/±inf → `None` as today;
  `rel_humidity()` round-trips each vector within the tolerance. No clamp (G.2 "nothing clamps"): `test_rel_humidity_
  clamped_high` (`:255-260`) → `test_rel_humidity_refuses_a_value_above_saturation` — `rel_humidity(20.0, 20.0)` (115.8 %)
  and `(40.0, 100.0)` (196 %) → `None`, never 100.0; its comment states the rule in one line.
- **Resolved**: AC_NOTES 8 / A.U12.09's removal is overtaken by the owner's later answer (OR140.a (4), most recent owner
  decision wins); the no-clamp rule is A.U12.10's G.2 wording ("returns `None` outside the domain … nothing clamps"),
  which the kept helpers now follow.
- **Unit**: U12.
- **Depends**: M.SRC_CORE.127; [fold F08 M_SRC_CORE] (the humidity helpers kept, `rel_humidity()` without its clamp).
- **Blast carried by**: `tests/test_asy_bmp3xx_driver.py:1388` comment → M.TEST_UNIT.007-.024 (bmp section, A.U12.08).
- **Kind**: test

### M.TEST_UNIT.272 McCamy against the Planckian locus; the span comment
- **From**: A.U12.07 (new L1; `:526-549` hold; `:535-536` comment), A.U28.27 (`:419` test name `…_sRGB_…` → `…_srgb_…`).
- **Site**: `tests/test_math_helpers.py:419`, `:534-539`; new test after `:549`.
- **Change**: `:535-536` → "# … outside the helper's output span (2000-12500 K) must return None, never a clamped
  2000.0/12500.0 …"; `:419` → `test_rgb_to_xyz_pure_red_matches_the_srgb_matrix_column`. New
  `test_cct_mccamy_tracks_the_planckian_locus_within_its_stated_error` with A.U12.07's six (x, y, T, bound) points, the
  `(0.52668, 0.4133)` → `None` and `(0.26858, 0.27355)` → ≈ 12463 K cases, comment "# Oracle: colour-science 0.4.7
  blackbody spectra against the CIE 1931 2-degree CMFs (agent, 2026-09-29) - / # not this port's own output." (2 lines).
- **Resolved**: —
- **Unit**: U12 (stage U28 name).
- **Depends**: M.SRC_CORE.125.
- **Blast carried by**: SPEC M.1.3 error sentence → A.U12.07 (SPEC).
- **Kind**: test

### M.TEST_UNIT.273 Every residual catch reached through a stand-in `math`
- **From**: A.U35.42 (1) (one test per function with a residual catch), OR140.a (4) (the humidity helpers stay; A-C
  review fold).
- **Site**: new tests at the end of `tests/test_math_helpers.py`.
- **Change**: `test_residual_math_errors_return_none` — for `wet_bulb_temperature`, `dew_point`, `pressure_at_height`,
  `abs_humidity`, `rel_humidity` (the five catches A.U35.42 lists): `mh.math` replaced by a stand-in whose
  `log`/`exp`/`atan`/`sqrt`/`pow` raise `ValueError("stand-in domain error")`, then `OverflowError` (an
  `ArithmeticError`); each call with an in-domain argument returns `None`; the real `math` restored in `finally`.
- **Resolved**: A.U35.42 lists five catches; A.U12.09's removal of two of them is dropped (OR140.a (4), A-C review fold),
  so all five stay (M.SRC_CORE.130 as the fold amends it).
- **Unit**: U35.
- **Depends**: M.SRC_CORE.130; [fold F08 M_SRC_CORE] (the two humidity helpers kept with their catches).
- **Blast carried by**: SPEC E.5.1 row → A.U35.41 (SPEC).
- **Kind**: test

## tests/test_neopixel_wifi_integration.py

### M.TEST_UNIT.274 A real NeopixelDriver behind WifiService, driven by condition, not sleeps
- **From**: A.U9.10 (a) (the three sleeps → a condition wait; `:70-88` goes with A.U5.07), A.U8C.35 (`:53, :56, :59, :83`
  tags), A.U17.27 (`:45, :74` construct `NeopixelDriver(0)`, values set after), A.U5.07 (`ext_led` only at
  construction; `set_ext_led()` gone), A.U18.40 + A.U5.09 (`:46, :75` the `WifiConfig`, no `led_pin`), A.U10.44
  (`start_asy_neopixel_led_overl` → `start_asy_overlay`), A.U10.38 (`AsyConnTime` → `WifiService`), A.U10.35/GAP-5
  (`pixel.pixel` → `pixel._pixel`), A.U22.04 (`:18`, `:23` typing), A.U24.08 (`:36` `_cancel`, `run`).
- **Site**: `tests/test_neopixel_wifi_integration.py:1-94`.
- **Change**: docstring line 1 names `asy_wifi_service.py`'s `ext_led=` and `WifiService` (≤ 3 lines). Imports `from
  _async_harness import cancel, run`, `from _driven_time import DrivenTime`, `import asy_neopixel_driver`, `from
  asy_wifi_service import WifiConfig, WifiService`; `TYPE_CHECKING` keeps nothing it does not use. The test builds
  `pixel = NeopixelDriver(0)`; `pixel._neopixel_freq = 100`; `pixel._frame_ms = 10` (the product's own state, set from
  outside as M.TEST_UNIT.078 does), `run(pixel.setup())`, and `conn = WifiService(WifiConfig("SensorNode",
  "12345678", 5, 5), ext_led=pixel, cfg_path=_tmp_cfg_dir())`, `run(conn.setup())`. Inside `with DrivenTime() as
  clock: clock.install(asy_neopixel_driver)` it starts `pixel.start_asy_overlay()`, calls `set_wifi_led(status=True)`,
  then each of `_led_on()`, `_led_off()`, `_led_toggle()` is followed by `await clock.run_until(lambda:
  pixel._pixel.writes[-1][0] == <expected>, <one ramp bound>)` instead of `asyncio.sleep(0.05)`; `cancel(task)` at the
  end; the assertions `(50, 50, 50)`, `(0, 0, 0)`, `(50, 50, 50)` hold (`:65` default overlay brightness holds). The
  `set_ext_led()` test (`:70-88`) goes (guard: `ext_led` reaches `WifiService` only at construction, pinned by
  `tests_scripts/test_buildgen_generate.py`'s conn line, A.U5.07).
- **Resolved**: A.U8C.35's `l1.asy_neopixel_driver_overlay_settle_s` tags vs A.U9.10 (a): the sleeps they tag are
  replaced by a condition wait and `:83` leaves with its test — no tag is written, the row loses these sites (as
  M.TEST_UNIT.078).
- **Unit**: U9 (stages U5, U10, U17, U18, U22, U24; driven time U35).
- **Depends**: M.SRC_SENS.021, .023; M.SRC_NET.078; M.TEST_HELP.043, .065.
- **Blast carried by**: Part N row → A.U8C.35/A.U35.13 (SPEC).
- **Kind**: test

### M.TEST_UNIT.275 New seams: NeopixelDriver as an error source; its empty timer list
- **From**: A.U9.10 (b), (c).
- **Site**: new tests in `tests/test_neopixel_wifi_integration.py`.
- **Change**: `test_a_neopixel_driver_is_an_error_source_of_the_webserver` — a real `NeopixelDriver` in a real
  `WebserverService`'s `error_sources`: after one logged entry through `pixel.pr`, `GET /status`'s `errcount` carries
  `NEOPIXEL` with it; `PUT /status {"ResetErrors": true}` answers "Valid" and clears it.
  `test_the_drivers_empty_timer_list_reaches_a_generated_device` — one device built through
  `tests/_sensortask_scenarios.py`'s `build()` collects `NeopixelDriver.get_timer_starters()`'s empty list in
  `_collect_timer_starters()` without error.
- **Resolved**: —
- **Unit**: U9.
- **Depends**: M.SRC_NET.123 (`ResetErrors`); TEST_HELP `_sensortask_scenarios.build()`.
- **Blast carried by**: SPEC C.14 seam-proof line → A.U9.10 (SPEC).
- **Kind**: test

## tests/test_notification_neopixel_integration.py

### M.TEST_UNIT.276 Construction-time signals, value references, driven ramps
- **From**: A.U10.37/A.U10.38 (`NotificationCoordinator` → `NotificationService`), A.U5.06 (7 sites: signals at
  construction, no `register()`/`finalize()`), A.U5.11 (`:86, :106, :109, :137` `NotificationSignal(…, ValueRef(…), …)`),
  A.U10.10 (`notify.cfgmgr.setup()` → `notify.setup()`; `pixel.setup()`), A.U10.40 (`Interv` → `FlashInterval`),
  A.U17.27 (`:62` `NeopixelDriver(0)`, values set after), A.U10.44 (starter names), A.U35.13 (`:94, :120, :145, :147`
  under `DrivenTime`), A.U8C.36 (tags on those four), A.U8C.12/.37/.38/.39 (read: shared IDs sited here), A.U24.49
  (`_FakeTime` → `tests/_fake_time.FakeTime`), A.U24.08 (`run`, `:73` `_cancel_all` → `cancel`), A.U22.04 (`:20`, `:25`
  typing), A.U36.513 (`:2` docstring), A.U10.35/GAP-5 (`pixel.pixel` → `pixel._pixel`).
- **Site**: `tests/test_notification_neopixel_integration.py:1-130`.
- **Change**: docstring line 2 "… - the shape every generated build_system() wires (buildgen/codegen.py)." (3 lines in
  all). Imports `NotificationService, NotificationSignal`, `ValueRef` from `asy_base_classes`, `FakeTime` from
  `_fake_time`, `run`/`cancel` from `_async_harness`, `DrivenTime`, `asy_neopixel_driver`, `asy_notification_service`.
  `_FakeSource` keeps its shape (an object carrying one named attribute); each signal is `NotificationSignal(name,
  ValueRef(source, name), schema, colour)`. `make_pair(signals)` → `_make_pair(signals)`: `pixel = NeopixelDriver(0)`,
  `pixel._neopixel_freq = 100`, `pixel._frame_ms = 10`, `notify = NotificationService(pixel.request_signal,
  _local_time, signals, cfg_path=…)`, both `setup()` run. Scenarios set `{"FlashInterval": 3600.0, "FlashDur": 0.5}` and
  run inside `with DrivenTime() as clock: clock.install(asy_neopixel_driver, asy_notification_service)`, each wait an
  `await clock.advance(<ms>)` sized by the product's own durations (one triggered cycle `2 × FlashDur`; two cycles
  twice that), never a margin; `_start_all()` keeps its one `sleep(0)` with the M.TEST_UNIT.078 comment.
- **Resolved**: A.U8C.36's tags vs A.U35.13: the four literals become the product's own durations under driven time, so
  no tag is written and the rows lose these sites (as M.TEST_UNIT.082).
- **Unit**: U35 (stages U5, U10, U17, U22, U24, U36 docstring).
- **Depends**: M.SRC_SENS.021, .023, .030, .033; M.TEST_HELP.043, .054, .065.
- **Blast carried by**: Part N rows → A.U35.13 (SPEC).
- **Kind**: test

### M.TEST_UNIT.277 A busy LED refuses at once; local-time and default-sink seams
- **From**: A.U9.02 (`:133-154` flips), A.U9.10 (d), (e).
- **Site**: `tests/test_notification_neopixel_integration.py:133-154`; new tests.
- **Change**: `:133` → `test_led_signal_during_a_notification_ramp_is_refused_at_once`: mid-ramp (`clock.advance(100)`),
  `pixel.led_signal(11, 22, 33, 0.1)` returns `False` with no `await`; after the ramp's own duration `(11, 22, 33)` was
  never written. New `test_the_window_check_reads_a_real_ntp_clock` — a real `NTPClient`, marked synced, its `cettime`
  as `local_time_callback`; one cycle with a window around the returned `hour`/`minute` flashes, one with a window
  outside it does not. New `test_a_service_on_the_default_sink_completes_a_cycle_silently` — `NotificationService(
  _DefaultSignalSink().request_signal, …)` completes a triggered cycle, sets `Triggered`, logs nothing and writes no
  frame (no pixel exists).
- **Resolved**: — (the HEAD test pinned the queueing that A.U9.02 retires; guard: the refusal assertion itself and
  M.TEST_UNIT.080's unit cases, OR111.a (2))
- **Unit**: U9.
- **Depends**: M.SRC_SENS.021, .022, .036 (sink); M.SRC_NET NTP client (`cettime`).
- **Blast carried by**: SPEC C.14 seam line → A.U9.10 (SPEC).
- **Kind**: test

## tests/test_notification_scd30_integration.py

### M.TEST_UNIT.278 SCD30 → notification → pixel: construction, sync, driven ramps
- **From**: A.U10.37/A.U10.38 (`NotificationService`, `SCD30Reader`/the module's end-state class name, `asy_crc_checks`),
  A.U5.06 (4 sites), A.U5.11 (signals over `ValueRef(scd_reader, "CO2")`/`"Hum"`), A.U15.12 + A.U10.43 (`SCD30_Reader(i2c,
  irq_pin=5, trigger_s=3, max_module_error=5, cfg_path=…)` then `setup()`: it owns `config_SCD30.cfg`), A.U10.35
  (`reader.scd.i2c_scd30…` → `reader._scd._i2c_scd30.i2c_device.i2c._i2c`), A.U10.10 (`notify.setup()`), A.U10.40
  (`FlashInterval`), A.U17.27 (`:99`, `:113`), A.U35.13 (`:148, :176, :201, :253`), A.U8C.37 (tags on those),
  A.U8C.12/.36/.38/.39 (read: shared IDs), A.U24.49 (`_FakeTime`), A.U24.08 (`run`, `:123` `_cancel_all`), A.U24.78
  (`inject_fault` form), A.U15.01 (read: `:135, :166, :238` readings in range — hold), A.U10.06 + GAP-15 (the direct
  `_error_check()` calls on good reads), A.U36.513 + A.U36.544 (`:3`, `:5-6`, `:96-98` comments).
- **Site**: `tests/test_notification_scd30_integration.py:1-186`, `:223-264`.
- **Change**: docstring and comments: `:3`'s quotation of C.7 is either quoted exactly from SPEC C.7 or written without
  quotation marks ("matching SPECIFICATION.md Part C.7: each driver owns its own error log"); `:5-6`, `:96-98` cite
  "SPECIFICATION.md Part C.14.3" and "the registration shape the generated build_system() emits". Builders: `_make_scd_
  reader()` calls `machine.I2C.reset_id(0)` first and `run(reader.setup())`; `_make_stack(signals)` builds
  `NeopixelDriver(0)` (freq 100, `_frame_ms` 10 set after) and `NotificationService(pixel.request_signal, _local_time,
  (NotificationSignal("WarnCO2", ValueRef(scd_reader, "CO2"), …),), cfg_path=…)`, both set up (the separate
  `make_hum_stack` keeps its own instance, signal over `"Hum"`). The direct read cycles run with
  `asy_base_classes.set_utc_valid()` set (reset in `finally`) so a good read's `TS` is real and `_error_check()` returns
  `True`. Waits run under `DrivenTime` installed on `asy_neopixel_driver` and `asy_notification_service` (product
  durations, no tags); `inject_fault("writeto", OSError, errno.EIO, "simulated bus fault")`.
- **Resolved**: A.U8C.37's tags vs A.U35.13 — not written (as M.TEST_UNIT.276).
- **Unit**: U35 (stages U5, U10, U15, U24, U36).
- **Depends**: M.SRC_SENS.052-.058 (SCD30 config reader), .030, .033; M.TEST_HELP.043, .054, .065.
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.279 A faulted SCD30 cycle: the driver's and the streak's entries, attributed to SCD30 alone
- **From**: A.U3.03 dropped (OR140.a (7): `:211-216`, `:262-264` keep HEAD's `ErrCount` 2, the streak entry kept; A-C
  review fold), A.U2.06 + A.U2.11 (`:211-216` codes by name), A.U10.R01 + A.U15.R01 (read: one failure fires no recovery rung; re-derived counts hold at 1).
- **Site**: `tests/test_notification_scd30_integration.py:189-264`.
- **Change**: `:209-216`: `still_running is True`; `ErrCount == 2`; the last two entries are `code("E", "READ")` and the
  streak's own entry by its catalog name (the `_last_two_err_nums()` helper keeps its role, reading codes by name); the
  comment → "# One faulted cycle persists the driver's read error and the reader's streak step: each layer the fault
  reaches keeps its entry (owner, 2026-10-02; SPECIFICATION.md C.7)." (no audit ID, A-C3 O-16) `:220` comment names `_signal_loop()`'s
  startup off frame. `:259-264`: `ErrCount == 2`, the same two entries, comment "# history keeps the fault; the later
  success only resets the streak." NOTIFY counts stay 0.
- **Resolved**: —
- **Unit**: U3 (stage U2 codes).
  A-C2 step order: A.U10.R01's part lands in U13, not U10 (it follows A.U10.R01's own change, which lands in U13).
- **Depends**: M.SRC_CORE.037 (as the fold reverts A.U3.03: the streak entry per failing cycle); M.SRC_SENS (SCD30 read
  error); [fold F11 M_GEN] (the streak's catalog entry).
- **Blast carried by**: —
- **Kind**: test

## tests/test_notification_scd30_sgp40_integration.py

### M.TEST_UNIT.280 Two sensors, one service: construction, shared doubles, driven waits
- **From**: A.U10.37/A.U10.38, A.U5.06 (3), A.U5.11 (`:203-204`), A.U15.12 + A.U10.43 (`:89`), A.U10.35 (`:90`, `:168`),
  A.U10.10 (`:167`, `:208`), A.U10.40, A.U17.27 (`:200`), A.U35.13 (`:231`, `:270`), A.U8C.38 (tags), A.U8C.12/.36/.37/.39
  (read), A.U35.14 (read: no wall-clock wait remains to state), A.U31.09 + A.U24.49 (`:39-52` `_FastAsyncSleep` → shared,
  both sleeps; `_FakeTime`), A.U24.08 (`run`, `:75`), A.U24.78, A.U15.01 + A.U15.19 (read: field access by name holds),
  A.U24.56 (`:1`), A.U24.67 (the 2 variant-name sites `:1`, `:199`), A.U36.513 + A.U36.544 (`:198-199`), A.U10.06 +
  GAP-15, A.U5.11 (`ValueRef` compensation pair for SGP40).
- **Site**: `tests/test_notification_scd30_sgp40_integration.py:1-238`, `:248-277`.
- **Change**: docstring `:1` "… matching the generated build_system()'s single notification/pixel wiring)" (≤ 3 lines in
  all); `:198-199` "(SPECIFICATION.md Part C.14.3), the registration shape the generated build_system() emits."; the
  local `_FastAsyncSleep` goes for `FastAsyncSleep()` (patching `sleep` and `sleep_ms`, so the 50 ms command delays no
  longer run in real time), `_FakeTime` for the shared one. SCD30 builder as M.TEST_UNIT.278; SGP40 builder
  `SGP40_Reader(i2c, ValueRef(comp, "Temp"), ValueRef(comp, "Hum"), max_module_error=2, cfg_path=…)` with
  `machine.I2C.reset_id(1)` first and `run(reader.setup())`, its bus read through `reader._sgp._i2c_sgp40.i2c_device.i2c.
  _i2c`. `drive_scd_cycle()`/`_drive_sgp_cycle()` → `_drive_*` and run with the UTC flag set (reset in `finally`), the
  SGP40 helper passing the condition `_read_loop()` computes (M.SRC_SENS.091). `make_dual_stack()` → the service built
  with both signals over `ValueRef`s. Waits under `DrivenTime` (two ramps: the product's `2 × 2 × FlashDur`; one ramp:
  `2 × FlashDur`), no tags. `:282` keeps HEAD's `ErrCount == 2`, the codes by name: the driver's `code("E", "READ")` and the
  streak's own entry (A.U3.03's single entry dropped, OR140.a (7); A-C review fold).
- **Resolved**: A.U8C.38's tags vs A.U35.13 — not written.
- **Unit**: U35 (stages U3, U5, U10, U15, U24, U31, U36).
- **Depends**: M.TEST_UNIT.278 (SCD30 builder), M.TEST_UNIT.281 (SGP40 builder); M.SRC_SENS.067, .068, .091.
- **Blast carried by**: —
- **Kind**: test

## tests/test_notification_sgp40_integration.py

### M.TEST_UNIT.281 SGP40 → notification → pixel: value references, shared fast sleep, driven ramps
- **From**: A.U10.37/A.U10.38, A.U5.06 (2), A.U5.11 (compensation `ValueRef` pair; the signal over `ValueRef(sgp_reader,
  "VOC")`), A.U10.35 (`:109`), A.U10.10 (`:108`, `:121`), A.U10.40, A.U17.27 (`:115`), A.U35.13 (`:181`, `:211`, `:255`),
  A.U8C.39 (tags), A.U8C.12/.36/.37/.38 (read), A.U24.49 + A.U31.09 (`:42-56` `_FastAsyncSleep`, `_FakeTime`), A.U24.08
  (`run`, `:135`), A.U15.19 (read: `VOC` read by name; the calibration counts hold), A.U36.513 + A.U36.544 (`:113-114`),
  A.U10.06 + GAP-15, A.U10.R01 (read: two faulted cycles at `max_module_error=2` reach the device rung; the assertions
  `err_count >= 1` and the later spike hold).
- **Site**: `tests/test_notification_sgp40_integration.py:1-266`.
- **Change**: `:113-114` "(SPECIFICATION.md Part C.14.3), the registration shape the generated build_system() emits.";
  `:3-9` calibration note keeps naming `voc_algorithm.py` (not among A.U10.37's eight renamed modules) and stays 3 lines per paragraph. Builders as
  M.TEST_UNIT.280's SGP40 half; `_drive_one_cycle()` runs with the UTC flag set and the `_read_loop()` condition;
  `FastAsyncSleep()` shared; waits under `DrivenTime`, no tags; `:196` `nak_addresses` unchanged. The `:202-204` comment
  → "# Awaited directly: this coroutine already runs under run(), which now refuses a nested call
  (tests/_async_harness.py)."
- **Resolved**: A.U8C.39's tags vs A.U35.13 — not written.
- **Unit**: U35 (stages U5, U10, U15, U24, U31, U36).
- **Depends**: M.SRC_SENS.067, .068, .091; M.TEST_HELP.043, .052, .054, .065.
- **Blast carried by**: —
- **Kind**: test

## tests/test_ntp_fram_system_integration.py

### M.TEST_UNIT.282 Header and fixtures: generated-wiring parity, shared NTP frames, port redirect
- **From**: A.U24.44 (`:75-90` `make_ntp()` keeps its local construction; `:79`, `:338-342` comments cite the generated
  wiring; the L0 parity check is TSC's), A.U24.49 (`:57-58` self-containment sentence goes; `FakeNtpServer`,
  `make_ntp_reply`, `make_fram_manager`, `_tick` → shared), A.U24.76 (`make_*` → `_make_*`), A.U24.70 (`:132` → port
  band), A.U10.29 + A.U18.11 (`:147-173` `_RedirectNtpNetworking` → `redirect_udp_port(asy_ntp_client, 123, port)`),
  A.U18.12 + A.U18.13 (`:149-172` pre-resolution and `conn_tries` go; plain tuples), A.U24.01 (`:206` → `NTP_EPOCH_DELTA`
  via the shared builder; `:462` `_STATUS_BUSY` → `src_const`), A.U5.09 + A.U18.40 (`:71` `WifiService(WifiConfig(…))`),
  A.U5.10 + A.U18.10 (`NTPClient(lock, net, dns, NtpTiming(…), cfg_path=…)`, `DNSFallback` empty), A.U10.40 (the
  hand-written `config_NTP.cfg` keys), A.U10.38/A.U10.37 (class/module names), A.U10.18 (7: `network_available` →
  `network_available_locked`, `wifi_mode_lock`), A.U10.35 (`conn.wlan` → `conn._wlan`, `svc.uptime_event` →
  `svc._uptime_event`, `reader.bmp/scd/sgp` chains), A.U10.10 (setups), A.U18.33 (the DNS server read after one
  `_update_wifi_snapshot()`), A.U24.08 (`run`, `_cancel`), A.U24.67 (3 variant sites `:1`, `:79`, `:341`), A.U24.73,
  A.U8C.40 + A.U8C2.13 (tags), A.U8.17 (`:313`, `:329` constants), A.U29.03 (read: payload digits).
- **Site**: `tests/test_ntp_fram_system_integration.py:1-240`, `:462`.
- **Change**: docstring → "Integration across the real chain WifiService -> NTPClient -> {a timestamped FRAM chunk,
  SystemService}, wired as the generated build_system() wires them (buildgen/codegen.py); proves the chain's value/
  timing behaviour and the no-deadlock assumption around wifi_mode_lock." (3 lines). Imports per the renames plus
  `from _async_harness import cancel, run`, `from _fram_builders import make_fram_manager`, `from _ntp_frames import
  FakeNtpServer, make_ntp_reply`, `from _port_bands import PortAllocator`, `from _udp_port_redirect import
  redirect_udp_port`, `from _fake_time import tick`, `from _src_const import src_const`, `from _error_codes import code`,
  the address shim at import. `_make_conn()` → `WifiService(WifiConfig("SensorNode", "12345678", 5, 5), cfg_path=…)`,
  `run(conn.setup())`. `_make_ntp(conn, host, fetch_timeout_ms=_FETCH_TIMEOUT_MS)` writes `{"NTPHost": host,
  "NTPOffset": 0, "NTPInterval": 12, "GMTOffset": 0, "DSTOffset": 0, "DNSFallback": ""}` and builds
  `NTPClient(conn.get_wifi_mode_lock(), conn.network_available_locked, conn.get_dns_server_ip, NtpTiming(_DNS_TIMEOUT_MS,
  _DNS_TRIES, fetch_timeout_ms, _RETRY_S, _RETRY_MAX_S), cfg_path=…)`, `run(ntp.setup())`; its comment "# The generated
  build_system() wiring (buildgen/codegen.py): the three providers passed positionally, the real bound methods." `_connect_
  wlan()` sets the fake's state through `conn._wlan` and then runs `run(conn._update_wifi_snapshot())`. The local
  `FakeNtpServer`, `make_ntp_reply`, `_NTP_EPOCH_DELTA`, `make_fram_manager`, `_tick`, `_RedirectNtpNetworking`,
  `_next_port`/`make_addr()`/`make_port()` go (`_PORTS = PortAllocator("test_ntp_fram_system_integration")`; an
  unreachable address is `("127.0.0.1", _PORTS.next())`). `_sync_real_ntp_chain()` uses `with
  redirect_udp_port(asy_ntp_client, 123, server.port)`, starts `ntp._sync_loop()`, sets `ntp._sync_trigger_event` (the
  private name of M.SRC_NET's NTP section), waits under `_SERVE_WAIT_S = 5  # @tunable l1.asy_ntp_client_serve_wait_s`
  and the `_SYNCED_POLL_TRIES`/`_STATE_POLL_MS` constants (tags `l1.asy_ntp_client_synced_poll_tries = 50`,
  `l1.asy_ntp_client_state_poll_ms = 20`). Module constants: `_FETCH_TIMEOUT_MS = 5000  # @tunable ntp.fetch_timeout_ms`,
  `_LOCK_HOLD_FETCH_TIMEOUT_MS = 2000  # @tunable l1.fram_lock_fetch_timeout_ms` (`:313`), `_WRITE_PROMPT_S = 1.0  #
  @tunable l1.fram_write_prompt_s` (`:329`), `_UTC_TOLERANCE_S = 5` (`:263, :360`), `_SCAN_WAIT_S = 2.5` (`:443, :550,
  :614, :644`), `_START_POLL_S = 0.01`/`_START_POLL_TRIES = 200` (`:542-548`, `:608-612`, `:638-642`) each with its
  `l1.ntp_fram_system_integration_*` tag. `_STATUS_BUSY = src_const("src/asy_fram_manager.py", "_STATUS_BUSY")`.
- **Resolved**: A.U8C.40's `udp.conn_tries_default` (`:161`) and `l1.asy_ntp_client_fake_server_poll_ms`/A.U8C2.13's
  `…_fake_server_poll_tries` (`:190-200`) sites leave with the local classes (the shared `FakeNtpServer` carries them,
  TEST_HELP); not written here.
- **Unit**: U24 (stages U5, U10, U18, U8).
  A-C2 step order: A.U24.70's part lands in U25, not U24 (it follows A.U24.70's own change, which lands in U25).
- **Depends**: M.SRC_NET.041-.044, .078, the WiFi snapshot (M.SRC_NET A.U18.33); M.TEST_HELP.043, .054, .056-.058, .066.
- **Blast carried by**: L0 provider-parity check → A.U24.44 (TSC).
- **Kind**: test

### M.TEST_UNIT.283 FRAM timestamp tests: the write return order, setup-first chunks
- **From**: A.U16.18 (`:256`, `:277` annotations; `:260`, `:281`, `:329`, `:397`, `:475-476` unpacks: `written` first),
  A.U10.06 (read: the chunk's timestamp is `utc_now()` once synced — the real chain sets the flag; tests that run
  unsynced keep `TS`/`utc` `None`), A.U35.12 (`:437` one `sleep(0)` states its limit).
- **Site**: `tests/test_ntp_fram_system_integration.py:241-337`, `:379-500`.
- **Change**: `chunk.write(...)` results unpack `write_ok, ntp_synced, utc` (annotations `tuple[bool, bool, int | None]`);
  `:281` `== (False, False, None)`; `:329` `write_ok, *_ = await asyncio.wait_for(chunk.write(b"12345678"),
  _WRITE_PROMPT_S)` with its comment trimmed to "# A fraction of _LOCK_HOLD_FETCH_TIMEOUT_MS: checks the write completes
  promptly, not stuck behind the lock."; the reboot test builds `manager2, _ = make_fram_manager(chip=chip)`. Each
  chunk's manager runs `setup()` before allocation as today.
- **Resolved**: —
- **Unit**: U16 (stage U24).
- **Depends**: M.SRC_CORE (A.U16.18's return order); M.TEST_HELP.057.
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.284 SystemService seams: measured uptime, split supervision, the task-end record
- **From**: A.U11.01 (`:354`, `:370`, `:394` pumps advance the fake clock 1000 ms each), A.U20.06 + A.U32.06 (`:436`,
  `:541`, `:607`, `:637` `start_and_check_tasks()` → `start_tasks()` then `supervise_tasks()`), GAP-G5 (`task_names`
  required), A.U2.08 + A.U3.06 (`:557`, `:621`, `:651` "wrnno=1" → the task end's `code("E", "TASK_RETURNED")`), A.U2.15
  (read: NTP failures keep `ErrCount == 20`; A.U3.12's one slot leaves the count), A.U5.02 (`SystemService(…)` `log=`
  where passed), A.U10.44 (`start_asy_ntp_client()` → the NTP sync starter; `read_loop` → `_read_loop`), A.U15.12 +
  A.U10.43 (SCD30 reader config), A.U5.11 (SGP40 compensation `ValueRef`s over the SCD30 reader), A.U35.12 (`:437`), A.U8C.120
  (read: `_SCAN_WAIT_S` a Dependant of `system.task_check_s`).
- **Site**: `tests/test_ntp_fram_system_integration.py:339-454`, `:502-651`.
- **Change**: the boot-signature tests pump `tick(svc._uptime_event, n)` with the fake clock `TickSeconds` reads
  advanced 1000 ms per pump (the shared `tick()`'s step parameter); `121` pumps → 121 s measured. Each supervisor test:
  `await svc.start_tasks([spy_starter], ["NTP"])` (or `["BMP3XX"]`/`["SCD30"]`/`["SGP40"]`), then `sup =
  asyncio.create_task(svc.supervise_tasks())`, the `:437` `sleep(0)` comment "# one yield: the start ran inside
  start_tasks(); this only lets the supervisor park (a limit, not an interleaving claim)"; `cancel(sup)` at the end.
  Assertions: NTP — `len(starts) == 1`, SYSTEM `ErrCount == 0`, NTP `ErrCount == 20`; each reader — `len(starts) == 2`,
  SYSTEM `ErrCount == 1` with newest `code("E", "TASK_RETURNED")` (comment "# the task's end is persisted; the restart
  line is console-only"). Builders: `_make_bmp_reader()`/`_make_scd30_reader()`/`_make_sgp40_reader()` call
  `machine.I2C.reset_id(<bus>)` first and `run(reader.setup())`; `SCD30_Reader(i2c, irq_pin=5, trigger_s=…, max_module_
  error=…, cfg_path=…)`; `SGP40_Reader(i2c, ValueRef(scd, "Temp"), ValueRef(scd, "Hum"), max_module_error=…, cfg_path=…)`;
  attribute chains through `_bmp`/`_scd`/`_sgp`.
- **Resolved**: GAP-G5 (task names required) and A.U20.06's split land in the same lines.
- **Unit**: U20 (stages U2/U3 codes, U11 uptime, U15 readers).
- **Depends**: M.SRC_CORE.005, .013, the supervisor (M.SRC_CORE `start_tasks`/`supervise_tasks`); M.TEST_HELP.054.
- **Blast carried by**: —
- **Kind**: test

## tests/test_ntp_wifi_dns_integration.py

### M.TEST_UNIT.285 Header and fixtures: the generated wiring, shared frames, the port redirect, an empty fallback
- **From**: A.U24.44 (`:66-80` `make_ntp()` kept local; `:71` comment), A.U24.49 + A.U24.76 (`FakeNtpServer`,
  `make_ntp_reply`, `_tick`, `make_*`), A.U24.70 (`:245` port band), A.U10.29 + A.U18.11 (`:262-288` → `redirect_udp_port`),
  A.U18.12 + A.U18.13 (pre-resolution and `conn_tries` go), A.U24.01 (`:322` `NTP_EPOCH_DELTA` via the shared builder),
  A.U5.09 + A.U18.40 (`make_conn()` `WifiService(WifiConfig(…))`), A.U5.10 + A.U18.10 (`NTPClient(…, NtpTiming(…))`,
  `DNSFallback` empty), A.U10.40 (config keys), A.U10.38/A.U10.37, A.U10.18 (7 lock-name sites), A.U10.35 (`conn.wlan`,
  `ntp_sync_trigger_event`, `wifi_mode_lock` reads), A.U10.44 (`asy_ntp_time()` → `_sync_loop()`), A.U10.10 (setups;
  `ntp.pr.setup()` `:193`, `:439` → `ntp.setup()` already run by the builder, the lines go), A.U24.08, A.U24.67 (2
  variant sites `:1`, `:71`), A.U24.73 (7 `Any` lines), A.U8C.41 + A.U8C2.14 (tags), A.U36.544 (`:365`), A.U18.08 (`:429`).
- **Site**: `tests/test_ntp_wifi_dns_integration.py:1-118`, `:238-332`, `:365-370`, `:427-432`.
- **Change**: docstring → "Integration across the real chain WifiService -> NTPClient -> asy_dns_client.resolve_ipv4(),
  wired as the generated build_system() wires them (buildgen/codegen.py): calling order, error handling and value
  propagation a recorder-based unit test cannot observe." (3 lines; the "found and fixed a real bug" history goes). The
  `:3-8` comment block → "# No real port-53 or port-123 exchange (both need root): a literal-IP NTPHost skips DNS, and
  an / # empty DNSFallback with a 0.0.0.0 DHCP server leaves no candidate to ask." (2 lines). Builders as
  M.TEST_UNIT.282 (`_make_conn()`, `_make_ntp(conn, host, cfg_path=None, fetch_timeout_ms=_FETCH_TIMEOUT_MS)`, the
  written config file carrying `"DNSFallback": ""`); `_connect_wlan()` sets the fake through `conn._wlan` and runs one
  `conn._update_wifi_snapshot()` (A.U18.33: the DNS server flows through the snapshot); the local `FakeNtpServer`,
  `make_ntp_reply`, `_NTP_EPOCH_DELTA`, `_tick`, `_cancel`, `_RedirectNtpNetworking`, `_next_port`/`make_*` go for the
  shared ones, `PortAllocator("test_ntp_wifi_dns_integration")` and `redirect_udp_port(asy_ntp_client, 123,
  server.port)`. `_last_err()` stays (its "duplicated, not imported" comment → "# The newest entry of a log field."). Tag
  constants: `_LOCK_BLOCKED_WAIT_S = 0.05` (`:229`), `_FETCH_TIMEOUT_NO_REPLY_MS = 100` (`:379`), `_PAST_FETCH_TIMEOUT_MS =
  150` (`:388`), `_FAILURE_CYCLES = 8` (`:386`), `_SERVE_WAIT_S`, `_SYNCED_POLL_TRIES`, `_STATE_POLL_MS` (`:347-351`), each
  tagged with its A.U8C.41/A.U8C2.14 ID. `:365` "(BACKLOG.md open question 6, closed 2026-09-04)" → "(SPECIFICATION.md
  F.2)". `:429-431`: `import asy_dns_client` moves to module level; the comment names `ipv4_to_int()`.
- **Resolved**: A.U8C.41's `udp.conn_tries_default` (`:274`) and the fake-server poll rows leave with the local classes.
- **Unit**: U24 (stages U5, U10, U18, U8).
  A-C2 step order: A.U24.70's part lands in U25, not U24 (it follows A.U24.70's own change, which lands in U25).
- **Depends**: M.TEST_UNIT.282's builders (same shape); M.SRC_NET.041-.044, .078; M.TEST_HELP.043, .054, .056, .058, .066.
- **Blast carried by**: L0 provider-parity check → A.U24.44 (TSC).
- **Kind**: test

### M.TEST_UNIT.286 Value propagation and locking through the WiFi snapshot
- **From**: A.U18.33 (`:122-190` one snapshot step before sampling), A.U18.34 (new L1s (a)-(c); `:226` flips), A.U18.15
  (`_RecordingResolver` accepts `pr=`), A.U18.10 (the recorder sees the DHCP server alone; new L1: no socket built
  without a candidate), A.U10.18 (`ntp._wifi_mode_lock is conn.get_wifi_mode_lock()`).
- **Site**: `tests/test_ntp_wifi_dns_integration.py:120-236`; new tests.
- **Change**: `_RecordingResolver.__call__(host, dns_servers=(), timeout_ms=0, tries=0, *, pr)` records the four
  values; `:155` `== [("pool.ntp.org", ("203.0.113.9",), 500, 1)]` and `:178` `("0.0.0.0",)` hold (empty fallback list).
  `:181-197` reads `ntp._safe_get_dns_server()` after a snapshot step taken with `ifconfig` raising: `None`, and
  `_resolve_ntp_server()` still returns `("127.0.0.1", 123)`. `:207` → `ntp._wifi_mode_lock is
  conn.get_wifi_mode_lock()`. `:213-235`: while the NTP attempt holds the lock, `conn.get_dns_server_ip() ==
  "192.0.2.53"` (the pre-attempt snapshot, A.U18.34 (a) — HEAD's `is None` retired; guard: the snapshot test (a)
  below) and the mode switch stays blocked past `_LOCK_BLOCKED_WAIT_S`. New: `test_a_held_lock_serves_the_snapshot_
  and_uptime_keeps_counting` (A.U18.34 (a): a resolver taking 3 s of fake time holds the lock; `get_dns_server_ip()`
  and the `/status` networking fields return the snapshot, `WifiUptime` advances by the fake ticks);
  `test_the_wifi_loop_resumes_after_the_lock_without_a_fault` ((b): `_hw_op_failed` False, no log entry);
  A.U18.34 (c)'s reconnect case as written there; `test_no_socket_is_built_without_a_dns_candidate` (A.U18.10: empty
  `DNSFallback`, DHCP `0.0.0.0`, a non-literal host — zero `UDPSocket` constructions, counted through the port
  redirect's wrapper).
- **Resolved**: —
- **Unit**: U18.
- **Depends**: M.SRC_NET.044 (`_safe_get_dns_server`), the WiFi snapshot (M.SRC_NET.074/.091, A.U18.33/.34), M.TEST_HELP.066.
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.287 Full chain: sync, a silent server in one slot, no candidate at all
- **From**: A.U2.15 (`:407` 21 → `NTP_NO_REPLY` 71; `:453` 12 → `NTP_DNS` 67), A.U3.12 (the repeated no-reply spends one
  slot), A.U18.10 (`:425-445` the fallback swap → `DNSFallback` stored empty), A.U5.10 (`retry_max_s` read from the
  timing), A.U2.14 (read: no WiFi code literal in this file, grep — the six lines are NTP's).
- **Site**: `tests/test_ntp_wifi_dns_integration.py:334-454`.
- **Change**: `:334` holds under the shared server and redirect. `:364-407`: `_FAILURE_CYCLES` triggers each
  `_PAST_FETCH_TIMEOUT_MS` apart; `still_running`, not synced, `ntp._retry_wait_s == <the timing's retry cap>`;
  `ErrCount == 8` and the ring holds exactly one entry, newest `code("E", "NTP_NO_REPLY")`; the comment → "# Never
  synced, but the task handles it (Part C.7.2): still running, backed off to its cap, and the / # silent timeout
  persisted once for the run (C.7.1's repeat rule) while counted every time." `:427` →
  `test_dns_resolution_with_no_candidate_persists_the_dns_error`: `ntp._set_dict_cfg({"DNSFallback": ""}, …)` already
  holds via the builder (no module swap), newest `code("E", "NTP_DNS")`, `ErrType` "E".
- **Resolved**: —
- **Unit**: U18 (stages U2, U3).
  A-C2 step order: A.U2.15's part lands in U3, not U2 (it follows A.U2.15's own change, which lands in U3).
- **Depends**: M.SRC_NET.042, .045-.049.
- **Blast carried by**: —
- **Kind**: test

## tests/test_print_log.py (→ `tests/test_asy_print_log.py`)

### M.TEST_UNIT.288 Harness, names, structural FRAM fakes that fail only by allocation
- **From**: A.U10.37 (`print_log` → `asy_print_log`; `import asy_print_log`), A.U10.38 (`FRAMManager`, `FRAMChunk`,
  `CRCBase`), A.U16.05 (`:24`, `:53-63` `LockableBuffer` → `RegionBuffer`, 6 sites), A.U16.19 (`:58`, `:63`
  `override_pause` goes), A.U11.S03 (2) (the fakes checked structurally against the non-generic Protocols — hold),
  A.U11.16 (`:42-87` fakes raise `MemoryError`), A.U24.08 (`run`), A.U24.49 + M.TEST_HELP.057 (`make_fram_manager`; the
  three reboot rebuilds `manager2.fram._spidev.spi._spi = chip` → `make_fram_manager(chip=chip)`), A.U10.35 (`err_count`
  → `_err_count`), A.U0.07 (`:54` function-level import).
- **Site**: `tests/test_print_log.py:1-84`; every `err_count` and rebuild site.
- **Change**: imports `import asy_print_log`, `from asy_print_log import DEFAULT_LOG, LogConfig, PrintLog,
  PrintLogHistory, PrintLogHistoryStore, fatal_reported, make_logger, report_if_fatal`, `from asy_fram_manager import
  FRAMChunk`, `from asy_base_classes import RegionBuffer`, `from _async_harness import run`, `from _fram_builders import
  make_fram_manager`, `from _recording_print import record_prints`; TYPE_CHECKING imports `asy_crc_checks.CRCBase` and
  drops `Coroutine`/`Any`/`TypeVar`. `_RaisingFramChunk(raise_on_write, raise_on_read, none_buffer=False)`: `get_buffer()
  -> RegionBuffer` (`RegionBuffer(6, data_start=0, data_length=6)`, or one whose data buffer is `None` when
  `none_buffer`); `write_into(self, buf)`/`read_into(self, buf)` raise `MemoryError("simulated allocation failure")`
  when set; `_RaisingFramManager.get_chunk(self, size, crc=None, verify=0, check_length=8)` (`FRAMManager.get_chunk()`'s
  final parameters, M.SRC_CORE.090) raises `MemoryError`. Their comments → "# Fails only by allocation, the one failure
  the real chunk documents (SPECIFICATION.md C.7); parameter names / # stay exact so mypy checks the fake against
  asy_print_log's Protocols." Every `.err_count` → `._err_count`; the `deque` swap targets `asy_print_log.deque`.
- **Resolved**: —
- **Unit**: U16 (stages U10 names, U11 fakes, U24 harness).
- **Depends**: M.SRC_CORE.060; M.TEST_HELP.043, .050, .057.
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.289 Levels: numbers, refusal, what prints at each level
- **From**: A.U11.15 (20 sites → `pr.level` and 0-5; `:107-118` goes), A.U11.13 (`:90-100`, `:131-136`; new L1), A.U24.38
  (`:120` → recorded prints), A.U11.S03 (1) (read: `:128` `sep="-"` holds).
- **Site**: `tests/test_print_log.py:85-146`, `:306-313`, `:355-375`.
- **Change**: section banner "# PrintLog - levels 0 (off) .. 5 (all), refused when invalid". `:90` `PrintLog(None).level ==
  0`; `:95` → `test_an_out_of_range_level_is_refused_not_clamped`: `PrintLog(-5).level == 0`; `pr = PrintLog(2)`,
  `pr.set_level(10) is False`, `pr.level == 2`; `:102`, `:131` with numbers (`2`; `0` then `set_level(5) is True`).
  `:107-118` goes (it tested only the removed accessors; guard: the refusal test). `:120` →
  `test_each_level_prints_exactly_its_lines`: under `record_prints()`, level 0 prints none of `err/wrn/one/evt/all`, level
  1 only `err`, level 5 all five, `all("a", sep="-")` printing `"-"`-joined (the "(expected) …" console banner goes). New
  `test_set_level_refuses_non_int_and_out_of_range_values`: `set_level(True)`, `set_level(2.0)`, `set_level(None)`,
  `set_level(6)` each `False` with the level unchanged; `set_level(3)` `True`. `:306-313` comment → "# deque(maxlen=…)
  raises ValueError on a negative maxlen (pinned interpreter); the constructor clamps it to zero." `:359`, `:369` →
  `level=0`.
- **Resolved**: —
- **Unit**: U11 (stage U24 recorded prints).
- **Depends**: M.SRC_CORE.062, .066; M.TEST_HELP.050.
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.290 History: the newest-entry rule, honest sentinels, pre-setup entries, bool results
- **From**: A.U3.01 (new L1 per history type), A.U2.05 (42 code lines; `0x80` slot → `{num 0, "N"}`; negative code L1),
  A.U24.39 + A.U35.35 (`:201-205` from `0xFFFE`), A.U10.11 (new L1s: merge, pre-setup repeat, reset inside setup's read),
  A.U11.31 (`:217-225`, `:366-380` `reset()` returns `True`), A.U10.21 (read: `setup() -> bool`).
- **Site**: `tests/test_print_log.py:148-375`; new tests.
- **Change**: `:201-205` → `test_err_count_saturates_at_max_and_never_wraps`: `_err_count = 0xFFFE`; one `err_s` →
  `0xFFFF`, a second (a different code) → still `0xFFFF` (`:289-293` then merges into it and goes as a duplicate).
  `:217`, `:366` assert `run(hist.reset()) is True`; `:160` asserts `run(hist.setup()) is True`. The raw-history tests
  (`:175`, `:182`, `:266`, `:279`) hold (they read the ring's stored bytes); `:226-232` `get_log()` expectations hold (the
  initial slot reports `0, "N"`). New: `test_a_sustained_identical_code_spends_one_slot` per history type
  (`PrintLogHistory`; `PrintLogHistoryStore` over a counting fake chunk): ten identical `err_s` → `ErrCount` 10, the
  earlier entries intact, one chunk write per call; a different code between spends a slot; a recovered-then-recurring
  identical code stays one slot; the console printed all ten (`record_prints()`). `test_a_restored_0x80_byte_reads_back_
  as_no_entry` (store over the real chip: a `0x80` byte written into the stored ring reads back `num 0`, `"N"`).
  `test_a_negative_code_is_counted_diagnosed_and_takes_no_slot`. `test_pre_setup_entries_are_kept_after_the_stored_
  ones` (two stored entries, one pre-setup entry: after `setup()` the ring ends with the pre-setup entry, `ErrCount` 3;
  a pre-setup repeat counts and takes no slot); `test_a_reset_landing_during_setups_read_clears_ram_and_chunk` (a fake
  chunk whose `read_into()` awaits a barrier; `reset()` runs there; both end cleared).
- **Resolved**: —
- **Unit**: U11 (stages U2, U3, U10, U24).
- **Depends**: M.SRC_CORE.063, .065.
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.291 Store: allocation-only failures, the tri-state read, newest state last
- **From**: A.U11.16 (`:579-603`: fakes raise `MemoryError`; `:589-597` goes; new L1 `None` data buffer), A.U16.06
  (`:401`, `:408`, `:586`, `:601`, `:629`; new L1s: unreadable store kept, blank re-initialised), A.U11.31 (`:476-524`,
  `:555-577` gain `reset()`'s result; `:511-524` → `False`; new L1), A.U11.09 (`:539-553` holds, gains the history bytes),
  A.U14.19 (new gated-write L1; the existing fakes are not gated), A.U16.R03 (read: `tests/test_asy_fram_manager.py`'s
  re-persist case uses this file's store pattern, M.TEST_UNIT.048); routine settlement `unit-test-d-t27` and AC_NOTES 52
  (`:629` stays `False`; A-C review fold).
- **Site**: `tests/test_print_log.py:377-691`; new tests.
- **Change**: `:399-401` (`fram is None`): `_write()` `False`, `_read()` `None`. `:408` (blank chunk) `_read() is False`
  holds. `:536` → `run(store._read()) == (1, ())` (the read returns the stored count and entries). `:546` sets
  `_err_count`; `:539-553` holds with the two history bytes asserted after the header. `:579-586` (get_chunk raising
  `MemoryError`): `fram is None`, `_write()` `False`, `_read()` `None`. `:589-597` goes (the real chunk's `write_into()`
  cannot raise; guard: `:598`'s MemoryError read case and the `None`-buffer case below). `:598-601` → `_read()` `None`.
  `:629` (both copies BUSY) keeps `_read() is False` (blank or invalid, started fresh; not unreadable). `:484`, `:505`, `:561` assert `reset()` is `True`;
  `:518` asserts `run(store.reset()) is False`. New: `test_a_none_data_buffer_fails_write_and_read_without_raising`
  (`none_buffer=True`: `_write()` `False`, `_read()` `None`); `test_an_unreadable_store_keeps_its_bytes_and_stays_ram_
  only` (a chunk reading `None` at `setup()`: chip bytes untouched, `initialized is False`, `setup()` `False`, a later
  `err_s()` writes nothing to the chip); `test_a_blank_store_is_reinitialised` (reads `False`: written, initialized);
  `test_a_store_whose_reset_cannot_write_returns_false`; `test_concurrent_writes_land_newest_last` (a fake chunk whose
  `write_into()` awaits a test-held `asyncio.Event` and records payloads; three concurrent `err_s()`: releasing the gate
  lets exactly two writes through, the first and the newest, the last payload holds all three entries, the superseded
  call returns `True`).
- **Resolved**: A.U16.06 lists `:629` among the fault fakes going to `None`, but the merged code answers `False` there:
  M.SRC_CORE.084 returns `None` from a busy status byte without setting the fault flag, so M.SRC_CORE.088 reads the
  chunk as invalid with no fault (`False`), and G5/R25 re-initialises exactly such a chunk — `:629` stays `_read() is
  False` (agent decision D-T27, corrected by the routine settlement `unit-test-d-t27`, AC_NOTES 52; A-C review fold).
- **Unit**: U16 (stages U11, U14).
- **Depends**: M.SRC_CORE.064, .065, .088.
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.292 The logger factory and the C-stack fatal flag
- **From**: A.U5.01 (new L1), GAP-G8 + A.U30.19 (the flag L1 moves here from `tests/test_base_classes.py`).
- **Site**: new tests at the end of `tests/test_print_log.py`.
- **Change**: `test_make_logger_builds_a_store_or_a_ram_history_by_config` — `make_logger(LogConfig(manager, 4, 2),
  "SGP40")` is a `PrintLogHistoryStore` named "SGP40" at level 2 over a chunk of the manager; `make_logger(DEFAULT_LOG,
  "X")` a `PrintLogHistory` named "X". `test_report_if_fatal_flags_only_a_stack_overflow` —
  `report_if_fatal(RuntimeError("maximum recursion depth exceeded"))` sets `fatal_reported()`; `RuntimeError("CRC check
  failed while reading data")`, `ValueError("maximum recursion depth exceeded")` and `MemoryError()` do not (each checked
  from a cleared flag; the after-each hook resets it, A.U24.07). The expected message is cited to `py/runtime.c:1786`
  (v1.29.0) in a one-line comment.
- **Resolved**: A.U30.19 places this L1 in `tests/test_base_classes.py`; M.SRC_CORE.034 moved the flag to
  `asy_print_log` (GAP-G8), so the test lives with its module.
- **Unit**: U30 (factory case U5).
- **Depends**: M.SRC_CORE.034, .061; TEST_HELP after-each flag reset (A.U24.07).
- **Blast carried by**: —
- **Kind**: test

## tests/test_readiness_gates.py (new)

### M.TEST_UNIT.293 Every class with an async setup answers before and after a failed setup
- **From**: A.U10.22 (the L1 half; the L0 AST check is `tests_scripts/test_readiness_gates.py`, TSC), A.U10.21 (a
  refused construction: `setup()` `False`, the refusal persisted), GAP-17 lead ruling (AC_NOTES 38); routine settlement
  `initialized-flags` (AC_NOTES 52, OR36.a (1): `initialized` only where product code reads it; A-C review fold).
- **Site**: new `tests/test_readiness_gates.py`.
- **Change**: one table of `(class, builder, forced-failure, {public method: documented answer})` rows, one row per `src/`
  class with an async `setup()` that A.U10.22's L0 check gates (the same class list, read from the L0 test's exported
  set so the two cannot drift): for each, every public method is called before `setup()` and after a `setup()` forced to
  fail (a NAK'd bus, a directory in place of the config file, a write-dropping FRAM fake, a refused construction), and
  the answer is the documented one — a sentinel (`None`, `False`, `{}`), `"Failed"` per requested key, or the documented
  raise — never an `AttributeError`; a refused construction's `setup()` returns `False` and its log holds the refusal.
  Exempt by name, as the L0 check names them (AC_NOTES 38): the chip protocol classes (`BMP3XX_I2C`, `SCD30_I2C`,
  `SGP40_I2C`, `ISL29125_I2C`) and `I2CDevice`; `ConfigManager` is gated on `valid`. An `initialized` assertion appears
  only in the rows of classes whose product code reads that flag — the FRAM, SPI, UART and logging classes (`FRAMManager`:
  `initialized` replaces `_was_up`, before `setup()` a chunk request answers as the not-up manager did); `SensorReader`
  and through it every `SensorReaderConfig` subclass (`WifiService`, the NTP client, the notification service, every
  reader), `WebserverService` and `NeopixelDriver` carry no such flag, and their rows, like every other row, assert only the
  public answers and `setup()`'s `bool`. `NeopixelDriver`'s row: `on()`/`off()`/`toggle()`/
  `led_signal()`/`request_signal()` before `setup()` answer as M.SRC_SENS.023/.024 state after the fold; `NotificationService`'s
  row: every public method before `setup()` answers the construction defaults — `get_data()` `NOTIFY(Triggered=False,
  TS=None)`, `get_dict_cfg()` the config store's not-valid answer, `get_error_counter()` an empty log — never an
  `AttributeError`. Rows added by gap pass G2's `bool` setups (GAPS_G2 H-2 (d); gap pass G3): `SystemService`,
  `SensorReader`/`SensorReaderConfig`, `FRAMManager`, `WifiService` and `WebserverService` (each `setup()` returns `bool`,
  asserted `True` after a healthy setup and `False` after the forced failure). Module docstring ≤ 3 lines naming G5/R14's
  rule in words.
- **Resolved**: AC_NOTES 38 settles the exempt set; the routine settlement `initialized-flags` (AC_NOTES 52) supersedes
  the `NeopixelDriver` gate (AC_NOTES 38/44) and AC_NOTES 42 (2)'s `NotificationService.initialized`, and narrows A.U10.22's
  check scope to the classes whose product code reads the flag: no row reads a flag only a test would read.
- **Unit**: U10 (lands after U13's `deinit()` bool, as A.U10.22 states).
- **Depends**: M.SRC_CORE.008, .036, .039, .092, M.SRC_NET.079, .119 (the `bool` setups; the flags as amended by the
  fold); M.TEST_UNIT.079 (NeopixelDriver before-`setup()` cases); M.SRC_SENS.023, .024, .033 as amended by the fold;
  every class's M.SRC_* `setup()` end state.
- **Blast carried by**: L0 → A.U10.22 (TSC); SPEC C.13 → A.U10.22 (SPEC).
- **Kind**: test

## tests/test_reset_call_site_invariant.py

### M.TEST_UNIT.294 Reset sites confined to the system service; the watchdog armed first in the boot entry
- **From**: A.U24.54 (2)-(3) (the WDT half repointed to the generated boot entry; the reset half widened to aliased
  imports and the generated modules; the comment `:30-35`), A.U20.02 (read: the boot entry arms the WDT; `src/` holds no
  `watchdog` global), A.U10.08 + A.U8.08 (read: `:30-45` "U24 repoints it"; no value here), A.U10.37 (`system_service.py`
  → `asy_system_service.py`).
- **Site**: `tests/test_reset_call_site_invariant.py:1-45`.
- **Change**: docstring → "Regression test: every reset goes through SystemService._reboot(), and the watchdog is armed
  once, first, in each generated boot entry - another call site would reintroduce an unpaused reset or a circumventable
  watchdog." Reset half: the excluded file is `asy_system_service.py`; the scan covers `src/*.py` and
  `build/generated_src/sensortask_<device>.py` (after `require_fresh()`); offenders are the four needles, any `from machine
  import` line naming `reset` or `bootloader`, and any `import machine as <alias>` followed by `<alias>.reset(` or
  `<alias>.bootloader(`. WDT half: no `WDT(` in `src/*.py` or `sensortask_<device>.py`; each
  `build/generated_src/sensortask_<device>_main.py` (one per `devices/*.toml`, the floor checked) holds exactly one
  `WDT(`, and its first two statements after the docstring are `from machine import WDT` and `watchdog =
  WDT(timeout=8000)`; each `sensortask_<device>_main_noautostart.py` constructs no `WDT` (an `ast` walk finds no call; its
  `WDT(` appears only inside the printed start line). Comment `:30-35` → `# "must be hardcoded so no error ever can
  circumvent it" (owner, 2026-08-11, eaafc2f) is about injection; / # placement first in the boot entry is the owner's
  (2026-09-25).`
- **Resolved**: A.U24.54 names the boot entry `<device>_boot.py`; M.GEN.019 settles `sensortask_<device>_main.py` (M_GEN
  gap 1). M.GEN.019 also emits the no-autostart entry, whose printed start line contains `WDT(timeout=8000)` as text —
  a plain substring count would flag it, so that file is checked by `ast` for no construction (agent decision D-T28).
- **Unit**: U24.
- **Depends**: M.GEN.001, .019; M.TEST_HELP.046 (`require_fresh`).
- **Blast carried by**: the generated tree's writer → A.U24.54 (SCR, `scripts/_generate_sensortask_modules.py`).
- **Kind**: test

## tests/test_setter_microdot_integration.py

### M.TEST_UNIT.295 One product fixture: real readers in a real WebserverService on the vendored Microdot
- **From**: A.U27.07 (1), (6), (7) (the fixture; header; the decorator override goes once no local route remains),
  A.U8.23 (`:24-27` import ignore → the vendored stub on `mypy_path`), A.U27.15 (`:17-20` comment → the unit tier's
  `MICROPYPATH` rule), A.SDEP.06 (`:2`, `:272` "v2.6.2" re-stamped at the pin), A.U24.49 (`:5-10` the self-containment
  sentence goes), A.U36.544 (`:274`, `:355`, `:374` pointers), A.U36.527 (read: the override and its CLAUDE.md sentence go
  with the rewiring), A.U5.09 + A.U18.40 + A.U18.38 (`:64` `WifiService(WifiConfig(…))`), A.U5.10 + A.U18.10 + A.U10.18
  (`:71` `NTPClient(lock, net, dns, NtpTiming(…))`, empty `DNSFallback`, local `def`s for the providers), A.U5.04 (the
  webserver's construction config objects), A.U24.60 (17 `json.loads(res.body)` → `strict_loads`), A.U24.73 (9 `Any`
  lines), A.U24.08 (`run`), A.U10.37/A.U10.38 (names), A.U10.10 (setups).
- **Site**: `tests/test_setter_microdot_integration.py:1-90`, `:258-283`.
- **Change**: docstring → "End to end over the product's REST routes: real readers, a real WebserverService and the
  vendored Microdot (<pin>)." with the pin the re-check confirms. The `:4-10` scope comment and the self-containment
  sentence go. `sys.path.insert(0, "ext")` stays under the comment "# The unit tier's MICROPYPATH holds src/ and tests/
  only (scripts/micropypath.toml); this file alone reaches ext/microdot.py." (A.U27.15), and `from microdot import
  Microdot, Request` carries no ignore (the stub is on `mypy_path`, A.U8.23). One builder `_make_service()` constructs
  the real `WifiService`, `NTPClient`, `SystemService`, `BMP3XX_Reader`, `SGP40_Reader` and `SCD30_Reader` (each
  `setup()` run; fake buses `reset_id` first) and a real `WebserverService` whose `sensors` are the three readers and whose
  `settings` are the `SettingsGroup` lists exactly as `buildgen/codegen.py` emits them: `"networking"` — `conn` (`SSID`,
  `PW`, `Country`, `Hostname`, `post_fct=conn.reconnect_wifi`), `conn` (`LEDWifiOn`), `ntp` (`NTPHost`, `NTPOffset`,
  `NTPInterval`, `post_asy_fct=ntp.ntp_force_sync`); `"system"` — `sysfunct` (`DebugLevel`), `ntp` (`GMTOffset`,
  `DSTOffset`); requests go through `_make_request()` (kept) and `service.app.dispatch_request()`. Every response body is
  read with `strict_loads()` (A.U24.60). `_FakeRequest`, the `_simulated_*` endpoints, `_wifi_field_schema()`,
  `_wifi_app()`, `_bmp_app()`, `_ntp_*_app()`, `_sgp_app()`, `_scd_*` helpers and every `@app.put`/`@app.get` local route
  go.
- **Resolved**: —
- **Unit**: U27 (stages U5, U8, U10, U18, U24).
- **Depends**: M.SRC_NET (webserver construction and routes, M.SRC_NET.110-.132), M.SRC_CORE.072 (`parse_cmd_request()`
  deleted, U27), M.GEN (settings groups); M.TEST_HELP.008 (`strict_loads`), .043.
- **Blast carried by**: `pyproject.toml:408-413` override removal → A.U27.07 (TOOL); CLAUDE.md sentence → A.U36.527
  (DOCS); `tests/test_api_response.py:125-178`, `:42-44`, `:80-88` → M.TEST_UNIT.003-.005.
- **Kind**: test

### M.TEST_UNIT.296 Networking requests: sparse bodies, scoped groups, body-shape refusals
- **From**: A.U27.07 (2), (3) (`:136-256` the mocked block and the scoping tests on the real app), A.U0.35 + A.U19.15
  (`:193` "Final project decision:" → "(owner, 2026-09-26):"), A.U19.01 (`:193-199` an unknown key "Invalid", never a
  whole-request refusal), A.U4.02 + A.U11.24 (read: the setters run on the store's own schema; unchanged PUT schedules
  no flush), A.U10.40 (`LEDWifiOn`), A.U10.35 (`reconn_wifi` → the private flag M.SRC_NET.078 names).
- **Site**: `tests/test_setter_microdot_integration.py:136-283`.
- **Change**: each HEAD case on `PUT /networking` with a sparse body: fine data → `res` "OK", code 0, the four results
  "Valid", the reconnect flag set, `get_dict()` the stored values; partial → mixed results, the reconnect still fires,
  the refused keys at their defaults; a body that is not JSON (`req._body = b"{not valid json"`) → `res` not OK, code
  1; a JSON array or a scalar → the same; `{}` → OK with an empty result and no reconnect; an unknown key → "Invalid"
  beside the valid one (comment "# (owner, 2026-09-26): an unknown key is a per-field Invalid, never a whole-request
  refusal."). The scoping tests keep their claims on the product groups: `{"LEDWifiOn": false}` alone → "Valid", no
  reconnect; `{"Hostname": "NewHost", "LEDWifiOn": false}` → both "Valid", one reconnect (the Wi-Fi group changed);
  `{"SSID": "Hacked"}` reaches the Wi-Fi group only. The two "missing/unrecognized `cmd`" tests go with the envelope
  (no `cmd` exists; guard: the unknown-key case).
- **Resolved**: A.U27.07 retires `cmd` envelopes (OR58.a); A.U19.01's `:193-199` rewire is the same lines — one test.
- **Unit**: U27.
- **Depends**: M.TEST_UNIT.295; M.SRC_NET webserver `_body_as_dict()`, unknown-key result (A.U19).
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.297 Microdot's own semantics on the real app
- **From**: A.U27.07 (4) (`:335-369`), A.U19.06 (read: `:284` never reaches a static route — unchanged).
- **Site**: `tests/test_setter_microdot_integration.py:303-369`.
- **Change**: an unregistered path → 404; `PUT /measurements` (the one GET-only route) → 405; the raising-handler case
  uses a reader whose `_set_dict_cfg` raises (a test subclass) behind `PUT /sensors`, reaching the service's own 500
  path, and the "(expected) traceback" banner names it. The comment `:374` → "Microdot's blanket catch (SPECIFICATION.md
  A.5)".
- **Resolved**: —
- **Unit**: U27.
- **Depends**: M.TEST_UNIT.295.
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.298 Sensor PUTs: BMP3XX and SGP40 faults, the real SCD30 path for all seven fields
- **From**: A.U27.07 (2) (`PUT /sensors {"<name>": {…}}` per reader, names from `_NAME`), A.U24.42 (2) + A.U4.04
  (`:686-760` the local SCD30 dispatch goes; the real path for the seven product-schema fields), A.U2.07 (`:683` 14 →
  `CFG_FILE_WRITE`), A.U2.11 (`:734` helper literal 30 and `:858-864` 15 → `CHIP_SET`), A.U24.78 (`inject_fault` form),
  A.U10.43 (`trigger_sec` → `trigger_s`), A.U15.12 (SCD30 owns its config store), A.U11.S01 (read: `:728-732` `Any`
  parameters cleared by the rewire), A.U10.40 (`PressOvers` → `PresOvers`, `MeasInt` → `MeasInterval`), A.U10.35
  (`reader.reset` → `reader._reset_pending`).
- **Site**: `tests/test_setter_microdot_integration.py:375-869`.
- **Change**: BMP3XX: `PUT /sensors {"<BMP3XX name>": {"PresOvers": 8}}` with the address NAK'd → "Failed", the stored
  value unchanged; the write-only fault → "Failed" and the live getter's value stored. SGP40: `{"SGPResetVOC": true,
  "BackupPeriod": 5}` → both "Valid", `_reset_pending` set, `BackupPeriod` stored, `SGPResetVOC` never stored; the bus
  fault case "Valid"; the flush-write fault case (its write and flush in one coroutine, convention) newest
  `code("E", "CFG_FILE_WRITE")`. SCD30: the reader over the fake bus inside the service; one test per product-schema
  field (`src_const("src/asy_scd30_driver.py", "_VAL_…")` for the seven) PUTs a valid value and asserts "Valid" and the
  command word on the bus log (`0x4600` interval, `0x0010` ambient pressure, `0x5204` FRC reference, `0x5403` temperature
  offset, `0x5102` altitude, `0x5306` ASC, the FRC store field per M.SRC_SENS's SCD30 schema); an out-of-range field
  never reaches the bus; a faulted chip write → "Failed" with newest `code("E", "CHIP_SET")`; `AmbPres` 0 (the
  documented bypass) holds.
- **Resolved**: A.U24.42 (2) and A.U27.07's re-target land on the same lines (A.U27.07's Depends says so): one rewritten
  section.
- **Unit**: U27 (stages U2, U4, U15, U24).
- **Depends**: M.TEST_UNIT.295; M.SRC_SENS SCD30 setters and store (A.U4.04, A.U15.12), BMP3XX/SGP40 setters.
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.299 Time settings over `/networking` and `/system`: persisted, one resync per valid change
- **From**: A.U27.07 (2) (`GET /time/config` → `GET /networking` + `GET /system`; `PUT /time/cmd` → `PUT /networking`
  and `PUT /system`), A.U10.40 (NTP keys), A.U10.35 (`ntp_retries` → `_ntp_retries`).
- **Site**: `tests/test_setter_microdot_integration.py:460-561`.
- **Change**: `GET /networking` carries the NTP schema defaults and, after a valid `PUT /networking {"NTPHost":
  "time.example.org"}`, the new host; `GET /system` carries `GMTOffset`/`DSTOffset`. `PUT /networking {"NTPHost":
  "time.example.org"}` → "Valid", stored, the forced resync fired once (`_ntp_retries == 0`); `PUT /system {"GMTOffset":
  99999}` → "Invalid", the default kept, no resync; `PUT /system {"GMTOffset": 7200}` → "Valid", stored.
- **Resolved**: —
- **Unit**: U27.
- **Depends**: M.TEST_UNIT.295; M.SRC_NET NTP settings group.
- **Blast carried by**: —
- **Kind**: test

## tests/test_strict_json.py

### M.TEST_UNIT.300 The canonical trailer; the positive check bites; duplicate keys refused
- **From**: A.U24.04 (`:7`, `:100-101` trailer), A.U24.40 (`:48-51`: each valid document with one appended `,` must be
  rejected), A.U24.60 (new L1: duplicate keys; `strict_loads`), A.U10.27 (read: `:85` pins the emit-side fact the route
  gate relies on — holds), A.SDEP.17 (read: W39 — if the pinned `modjson.c` now rejects the slips, `:54-62`'s
  `json.loads(text)` line is the one to re-check at the pin; the oracle stays as defence).
- **Site**: `tests/test_strict_json.py:1-101`.
- **Change**: the top-level `from microtest import run` goes; the file ends `if __name__ == "__main__":` / `import
  microtest` / `microtest.run(globals())`. `:48` → `test_every_valid_document_passes_and_one_extra_comma_fails`: each
  valid document passes as text and as bytes, and the same text with one `,` appended raises "not strict JSON" (so the
  positive check cannot pass on an accept-all recogniser). New `test_a_duplicate_key_is_refused`: `{"a":1,"a":2}`, an
  escaped duplicate `{"\/":1,"/":2}` and `{"A":1,"A":2}` raise "duplicate key"; nested objects keep their own key
  sets (`{"a":{"x":1},"b":{"x":2}}` passes). New `test_strict_loads_returns_the_decoded_value` (`strict_loads(b'{"a": 1}')
  == {"a": 1}`, a slip raises).
- **Resolved**: —
- **Unit**: U24.
- **Depends**: M.TEST_HELP.008.
- **Blast carried by**: L0 trailer check → A.U24.04 (TSC); L0 `json.loads(` allow-list → A.U24.60 (TSC).
- **Kind**: test

## tests/test_system_service.py (→ `tests/test_asy_system_service.py`)

### M.TEST_UNIT.301 Harness and builder: the final constructor, providers, shared doubles, driven uptime
- **From**: A.U10.37/A.U10.38 (`system_service` → `asy_system_service`, `FRAMManager`, `asy_print_log`), A.U5.02 (24
  constructor calls: `fram=`/`history_length=`/`debug=` → `storage=`/`log=`), A.U5.01 (one `LogConfig`), A.U5.08 +
  A.U11.03 (1) (`set_level_setters()` → the `level_setters` provider; `config_stores` provider), A.U11.05 (read:
  `reset_reason=`), A.U24.08 (`run`), A.U24.49 (`_RaiseOnArm` `:103`, `_FastAsyncSleep` `:86`, `make_fram_manager` → shared),
  A.U31.17 (the fast sleep patches `sleep_ms` too), A.U24.07 (read: the after-each hook restores `Timer.all_timers`,
  `raise_on_arm`, `reset_count`, `gc.threshold`; manual resets go unless mid-body), A.U10.35 (private attribute reads),
  A.U11.01 (the pump advances the fake clock), A.U24.73 (`Any`), A.U24.67 (read: one variant-name site, `:1413`, M.TEST_UNIT.312),
  GAP-T2 (reset/bootloader raise after counting).
- **Site**: `tests/test_system_service.py:1-121`; every constructor call and private read.
- **Change**: imports `import asy_system_service`, `import asy_base_classes`, `from asy_system_service import
  SystemService`, `from asy_print_log import LogConfig, PrintLogHistory, PrintLogHistoryStore`, `from _async_harness import
  cancel, run`, `from _fast_sleep import FastAsyncSleep`, `from _fake_timer_arm import RaiseOnArm`, `from _fram_builders
  import make_fram_manager`, `from _driven_time import DrivenTime`, `from _error_codes import code`, `from _src_const
  import src_const`, `from _recording_print import record_prints`, `from _write_counters import WriteCountingOpen`.
  `make_service(…)` → `_make_service(ntp=None, *, watchdog=None, storage=None, log=DEFAULT_LOG, cfg_path="",
  level_setters=None, config_stores=None)` passing keywords to `SystemService(ntp, watchdog=…, storage=…,
  level_setters=…, config_stores=…, cfg_path=…, log=…)`. `_pump(flag, ticks, clock, settle=5)` advances `clock` by 1000
  ms before each `flag.set()` (scenarios run `with DrivenTime() as clock: clock.install(asy_base_classes)`, where
  `TickSeconds` reads the clock). The local `_FastAsyncSleep`, `_RaiseOnArm`, `make_fram_manager`, `run` and the
  `TYPE_CHECKING` `TypeVar`/`NoReturn`/`Self` go. Private reads: `_storage_pause`, `_uptime_event`, `_uptime_timer`,
  `_reset_timer`, `_storage_timer`, `_sequencer_timer`, `_start_time_set`, `_err_count`. Every path that lets the reset
  task run (`_reset_when_due()` calls `machine.reset()`/`bootloader()`) is driven inside `try:` … `except
  machine.SimulatedResetError` (or `SimulatedBootloaderEntryError`): the fake counts, then raises (GAP-T2).
- **Resolved**: —
- **Unit**: U11 (stages U5, U10, U24, U31).
- **Depends**: M.SRC_CORE.008; M.TEST_HELP.011 (reset raises), .043, .050, .052, .053, .057, .062, .065.
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.302 Construction and the latched feed
- **From**: A.U5.02, A.U11.15 (level accessors → `pr.level` and numbers), A.U10.35 (`storage_pause` → `_storage_pause`),
  A.S0930.13 (1)(2) (read: `feed_watchdog()` also stops once `_feed_owned`; the takeover cases are M.TEST_UNIT.309).
- **Site**: `tests/test_system_service.py:123-231`.
- **Change**: `:128` `_storage_pause is None`, the logger a `PrintLogHistory` named "SYSTEM". `:135` builds with
  `storage=manager, log=LogConfig(manager, 10, None)`: a `PrintLogHistoryStore`, `_storage_pause` reaches the manager's
  pause. `:149` `log=LogConfig(None, 10, 1)` → `svc.pr.level == 1`; `:154` `LogConfig(None, 3, None)` → three slots;
  `:204`, `:213` likewise (`run(svc.pr.setup())` then one `err_s` with `code("E", "CALLBACK")`, `_err_count == 1`); `:220`
  all four together with `level == 5`. The `feed_watchdog()` tests hold; new
  `test_feed_watchdog_stops_once_a_command_owns_the_feed` (`_feed_owned = True` → `feed_count` unchanged).
- **Resolved**: —
- **Unit**: U11 (stage U5).
- **Depends**: M.SRC_CORE.008, .009.
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.303 Uptime and boot signature on measured ticks
- **From**: A.U11.01 (`:238-240` hold; `:332-346`, `:370-477` pumps advance the clock; new L1 (a)-(d)), A.U11.02 (`:449-477`
  holds; new L1: a restarted counter keeps the signature), A.U10.06 (`:290-330` mktime/gmtime tests go; a synced
  signature is `utc_now()`), A.U14.26 (read: its `:278-300` rename has no site once A.U10.06 removes them,
  M.SRC_CORE.013 Resolved), A.U10.01 (`:245` comment; new L1 `1_790_000_000` round-trips), A.U3.12 (the repeated
  callback failure spends one slot), A.U2.08 (codes).
- **Site**: `tests/test_system_service.py:233-472`.
- **Change**: `:245` comment "# LockedValue(init_value=None)'s own default". The synced tests (`:260`, `:349`, `:432`, `:449`)
  call `asy_base_classes.set_utc_valid()` first (reset in `finally`, convention). `:269` asserts one `code("E",
  "CALLBACK")` entry. `:277-325` (`_OverflowingTime`, `_RaisingGmtime` and their two tests) go: the timestamp has no
  `try` (M.SRC_CORE.013); guard: `test_a_synced_signature_reads_utc_now` below. `:332` five pumps (5000 ms) → uptime 5;
  `:390`, `:410` 120 pumps (120 s) → fallback; `:430` `ErrCount == 120` and one CALLBACK slot (comment "# every tick
  retried and was counted; the repeat spends one slot"). New: `test_uptime_is_measured_not_counted` (A.U11.01 (a)
  three wake-ups over 7,500 ms → 7; (b) none for 5,000 ms, then one → 5; (c) `_uptime_timer.drop()` loses nothing; (d)
  `asy_system_service.time` replaced by a stub whose `gmtime`/`mktime`/`time` raise — uptime still advances);
  `test_a_restarted_counter_keeps_the_signature` (A.U11.02, NTP and random cases); `test_a_32_bit_signature_round_
  trips` (A.U10.01: a signature of `1_790_000_000` reads back unchanged); `test_a_synced_signature_reads_utc_now`.
- **Resolved**: —
- **Unit**: U11 (stages U2, U3, U10).
  A-C2: stage U35 — until M.TEST_HELP.065 exists the pumps run on the file's own clock double (the HEAD form); U35 swaps in the driven clock.
- **Depends**: M.SRC_CORE.013, .032; M.TEST_HELP.065.
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.304 Staggered triggers from one shared start
- **From**: A.U10.12 (`:479-615` the seven sequencer tests rewritten to `start_timers(triggers, timers)`), A.U24.32 (5)
  (`:552` renamed; the starter failure shown), A.U11.39 (read: the retired file's five tests live in the scenario),
  A.U35.12 (`:509` one `sleep(0)` states its limit), A.U24.07 (manual `Timer.all_timers.clear()` go).
- **Site**: `tests/test_system_service.py:474-611`.
- **Change**: `test_start_timers_with_no_starters_arms_nothing`; `test_a_single_trigger_starts_without_a_stagger_timer`;
  `test_triggers_start_in_order_on_the_one_preallocated_timer` (three triggers: after each `_sequencer_timer.trigger()`
  the next starts; `id(svc._sequencer_timer)` constant; `Timer.all_timers` unchanged); the timer starters run first
  in order; `test_a_raising_starter_is_persisted_and_sequencing_continues` (one `code("E", "TASK_STARTER_RAISED")` entry
  and the recorded print "Timer starter 0 failed:" with the `RuntimeError`, `record_prints()`); the two arm-failure tests
  → `test_an_arm_failure_falls_back_to_a_sleep_and_still_starts_every_trigger` (`RaiseOnArm(OSError)` and
  `RaiseOnArm(MemoryError)` under `FastAsyncSleep()`: one `code("E", "TIMER")` entry each, every trigger started). The
  `svc._timer_sequencer = …  # type: ignore[method-assign]` site goes with the method.
- **Resolved**: A.U24.32 (5) asserts a printed `pr.err` line; M.SRC_CORE.014 persists the starter failure
  (`err_s(…, errno=_ERR_TASK_STARTER_RAISED)`, A.U10.12's goal "a raising starter is persisted") — the test asserts the
  entry and the printed line (err_s prints too).
- **Unit**: U10 (stage U24 recorded print).
- **Depends**: M.SRC_CORE.014.
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.305 Reboot and bootloader through the command gate; `_reboot()` directly for the arm failures
- **From**: A.S0930.35 (a)-(c), (e), (f), A.U11.03 (existing `:618-727`; new L1 (a)-(e)), A.S0930.12 (results read), A.U8.08 +
  A.U8C.42 (`:623` mirror), A.U10.15 (the storage-unpause timer deinit), A.U11.07 (record codes), GAP-T2.
- **Site**: `tests/test_system_service.py:613-727`; new tests.
- **Change**: a scenario harness (one coroutine per test, `run()` at synchronous scope; the supervisor running as its
  task over two sleeping supervised fakes; `FastAsyncSleep()`). The five arm-and-fire tests (`:618`, `:629`, `:639`,
  `:711`, `:720`): `await svc.reboot_system()` is `True`; once `svc._shutdown_task` is done `_reset_timer` is ONE_SHOT with
  period `src_const("src/asy_system_service.py", "_RESET_DELAY") * 1000` (the source read replaces A.U8C.42's mirror
  tag, as M.TEST_UNIT.240), storage paused, `_storage_timer.deinit_called`; `trigger()` then a pump raises
  `SimulatedResetError` (caught) and `reset_count` rose by one (`bootloader_count` for the bootloader). The six
  arm-failure tests (`:648-708`) call `await svc._reboot(_RR_REBOOT, "…", system_reset)` /
  `(_RR_BOOTLOADER, …, system_bootloader)` directly (constants by `src_const`): `_force_watchdog_starve` True, region 0
  code 6, storage paused where wired. New: one test per command drives the arm failure through the sequence (S6's
  `Timer.init` raising `OSError(12)`): starve set, code 6; `test_reboot_takes_over_closes_quiesces_stops_then_resets_with_
  code_3` and the bootloader twin with code 4 (A.S0930.35 (b): the recorded order park → supervisor done → close×2 →
  flush×2 → pause → `wait_idle` per chunk → tasks done → no delete, chip unchanged → code 3 → armed); results (A.S0930.35
  (c): twice → both `True`, one task, one `init`; the other word → `False`; under an escalation's armed reset → `False`;
  `pause_permanent_storage(300)` during a reboot → `False`; `create_task` raising `MemoryError` → `False`, nothing
  changed); A.U11.03 (a) `_reboot()` twice — the second neither deinits nor re-arms; (b) a store whose `flush_pending()`
  raises — still armed, one `code("E", "CALLBACK")`, the others flushed; (d) the record precedes the flush and the pause
  follows it (a store fake recording `manager.get_pause()` during its flush sees `False`); (e) `create_task` raising
  inside `_reboot()` — starve, code 6, no timer; A.S0930.35 (f) a healthy reboot with no writer leaves the chip
  byte-identical and opens no file.
- **Resolved**: A.U11.03 (a)'s "two `reboot_system()` calls" is realised twice: through the gate (A.S0930.35 (c), one
  task) and on `_reboot()` itself (the armed-reset guard), since A.S0930.31 moved the public words onto the gate
  (M.SRC_CORE.011 Resolved).
- **Unit**: U11 (the gate stage; U16 adds the erase word's cases, M.TEST_UNIT.306).
  A-C2 step order: A.S0930.12's part lands in U20, not U11 (it follows A.S0930.12's own change, which lands in U20).
- **Depends**: M.SRC_CORE.006, .010, .011; M.TEST_HELP.011, .044.
- **Blast carried by**: device script `reboot_fallback_starves_the_watchdog.py:38` → A.U11.03 (HW_DEV).
- **Kind**: test

### M.TEST_UNIT.306 Config reset and FRAM erase: the sequence, refusals, step errors, power cuts
- **From**: A.S0930.21 (a)-(e), A.S0930.25 (power-cut proof), A.S0930.22 (1)-(5) (states and hazards, per purpose),
  A.S0930.32 (the escalation-vs-preflight and command-during-escalation-log interleavings), A.U22.01 (read: a task ending
  persists exactly one entry — M.TEST_UNIT.308); OR136.a (1) (the rebuild writes each deleted file once with its
  defaults), OR138.a (2) (the reset deletes every schema-backed file whatever its readable state; a failed delete is
  logged and answers "Failed"), OR140.a (12) (no SCD30 write while a sequence runs) — A-C review fold.
- **Site**: new section after the reboot tests.
- **Change**: as A.S0930.21 lists: (a) `test_reset_to_defaults_closes_flushes_quiesces_stops_deletes_then_reboots_with_
  code_7`, one of the stores built over an unreadable file (`OSError(5)` at its `setup()`: `writable is False`, the config
  fault reported) and one over a corrupt-JSON file, both deleted like the rest with no read of either (OR138.a (2)); (b) `test_erase_fram_zeroes_every_byte_and_reboots_with_code_8` on the 8 KB and 256 KB fakes; (c)
  `test_an_erased_chip_boots_like_a_new_one`, `test_an_all_zero_block_never_validates_even_with_an_idle_status`; (d) the
  refusals (reset armed, no store, no storage, chip uninitialised, write-protected 0x8C, `create_task` raising, the other
  command under way, the same one), each answering `False` with nothing changed and the supervisor still feeding; (e) the
  step errors, each continuing to code 9 without hanging; a store whose delete fails twice logs its line and the command
  reports "Failed" for it (OR138.a (2)) — where that answer surfaces (the command result or the code 9 the next boot
  reports) is M.SRC_CORE.011's as the fold amends it, the assertion following it. A.S0930.25: the fake's `cut_after_bytes` knob and a test-local
  `PowerCut(BaseException)`: (1) structural — after pass 1 every allocated block's status bytes are 0x00 and no pass-2
  byte precedes the last pass-1 status write; (2) enumerated cut points (each status byte of pass 1; first, middle and
  last byte of each overlapping pass-2 unit): a rebuild restores each ring exactly or blank, logging only {status bytes
  disagree, block uninitialised}; config: `cm.os` replaced so `remove` raises `PowerCut` after k removals, k = 0 … stores:
  the rebuild serves the remaining files unchanged (no write to any of them) and writes each removed file once with its
  defaults (OR136.a (1): one write per absent file, counted by `WriteCountingOpen`). A.S0930.22 (1)-(5) per purpose (boot
  accepted before the supervisor ran; a flush in flight; a FRAM write between its blocks; a bus session cancelled by S4;
  `mempause` active then `erase_fram()`), (6)-(9) (armed reset refused, the supervisor dying past budget during the
  sequence arms nothing, both orders of two commands, a command + reboot + mempause at once, a PUT during S5 answering
  "Failed" — the SCD30 setter fields among them, M.TEST_HELP.040 (8) proving the zero chip writes on the real graph), each interleaving forced by an `asyncio.Event` gate, never a sleep. A.S0930.32:
  `test_an_escalation_armed_during_the_erase_preflight_refuses_the_command` and
  `test_a_command_accepted_while_the_escalation_logs_keeps_its_own_reset`.
- **Resolved**: A.S0930.22 lists `tests/test_config_manager.py` beside this file; the store-level mechanics land in
  M.TEST_UNIT.259, the command-level cases here. It also lists `tests/test_asy_fram_manager.py`: case (3) runs here
  through the command sequence with the gated fake chip, so that file gains nothing (A-C3 S-18).
- **Unit**: U11 (config reset), U16 (erase); stage U20 (A-C review fold): the unreadable/damaged-store deletion and the
  failed-delete answer, with the delete path (OR138.a (2)); the power-cut rebuild's defaults write lands in U11 with OR136.a.
  A-C2 step order: A.S0930.32's part lands in U20, not U11 (it needs A.S0930.13, which lands in U20).
- **Depends**: M.SRC_CORE.011, .041, .042, .083 (as the fold amends them for OR136.a/OR138.a); [fold F03 M_SRC_CORE]
  (the config-fault state and the never-reading delete); TEST_HELP fake `cut_after_bytes`, `size=` (A.S0930.25,
  A.U24.22); M.TEST_HELP.062 (`WriteCountingOpen`).
- **Blast carried by**: L2-L4 → A.S0930.27-.29 (TWIN, HW_DEV, HW_BENCH).
- **Kind**: test

### M.TEST_UNIT.307 Storage pause: the waiter task, refusals, a reset's pause stays
- **From**: A.U10.15 (`:640-790` run the waiter; new L1), A.S0930.12 (`-> bool`, refused during a shutdown), GAP-G4 (new
  L1), A.U10.35 (names).
- **Site**: `tests/test_system_service.py:730-808`; new tests.
- **Change**: each pause test starts `svc.start_asy_unpause()` and, after `_storage_timer.trigger()`, pumps until the
  waiter ran; results read: `pause_permanent_storage(…)` is `True` (a call with no storage stays a no-op with the timer
  unarmed). `:743` (negative) and `:750-762` (clamp to `src_const(…, "_MAX_STORAGE_PAUSE") * 1000`, the comments' "compiled
  away, hardcoded" go) hold. New: `test_an_unpause_fire_with_the_waiter_running_unpauses_and_logs_one_line`;
  `test_an_unpause_after_a_reset_or_an_accepted_command_leaves_storage_paused` (GAP-G4: a pending unpause fires after
  `_reboot()` armed, and after a command was accepted — storage stays paused, no line).
- **Resolved**: —
- **Unit**: U11.
  A-C2 step order: A.S0930.12's part lands in U20, not U11 (it follows A.S0930.12's own change, which lands in U20).
- **Depends**: M.SRC_CORE.012.
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.308 Starters, the error counter, task ends: one entry each
- **From**: A.U10.03 (`:839-869` hold), M.SRC_CORE.018 (`:815-820` goes with `stop_uptime_timer()`), A.U10.15
  (`get_task_starters()` has two), A.U11.31 (`reset_error_counter()` returns `True`), A.U3.06 (`:1129-1131`, `:1195-1206`,
  the clean-return test: one entry per end; new L1 42/43/44 and 40), A.U2.08 (13 numeric lines), A.U22.01 (read: one
  entry per task end), A.U0.28 (`:850` comment).
- **Site**: `tests/test_system_service.py:810-935`, `:1104-1234`.
- **Change**: `:815` goes (no product caller; guard: none needed — the method is removed). `:823` `len(starters) == 2`
  (uptime counter and unpause waiter), each starter returns a task, both cancelled. `:850` comment "owner-confirmed
  design (2026-07-18, `1df8bc4`)". `:876`, `:889` use `code("E", "CALLBACK")` for the probe and `run(svc.reset_error_counter())
  is True`. `:925` one `code("E", "TASK_STARTER_RAISED")`. The task-end tests run `start_tasks([...], ["T"])` then the
  supervisor task (M.TEST_UNIT.309's shape): `:1104` restart observed, newest `code("E", "TASK_RETURNED")`; `:1132`
  `code("E", "TASK_RAISED")` in the ring; `:1167` exactly one entry, `code("E", "TASK_CANCELLED")` (the "plus the
  routine warning" comment goes: the restart line is console-only); `:1206` no `TASK_RAISED`, one `TASK_RETURNED`. New
  `test_each_task_end_adds_exactly_one_entry` (raised/cancelled/returned → 42/43/44; a starter raising at restart → only
  40).
- **Resolved**: —
- **Unit**: U3 (stages U2, U10, U11, U20).
- **Depends**: M.SRC_CORE.005, .012, .016, .018, .019.
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.309 The supervisor: split start, its own task, the scan budget, the takeover
- **From**: A.U20.06 + GAP-G5 (`start_and_check_tasks()` → `start_tasks(starters, names)` + `supervise_tasks()`), A.S0930.13
  (`:1027-1103` the loop in a task), A.U10.23 (escalation tests hold), A.U11.03 (`:1236-1253` reworked), A.U31.07
  (new L1: 22 dead fakes; 3 deaths), A.U8C.42 + A.U8C2.51 (`:1249` `_RUN_BOUND_S`, `:1251` `>= 4` restarts Dependant),
  A.U11.10 (new `run_setups()` L1), A.U36.544 (`:1008` "Measure B (PLAN B.1.2 …)" → "The boot placement reset
  (SPECIFICATION.md I.4(f.1))"), A.S0930.24 + A.S0930.36 (takeover, healthy feed counts, hangs, arm failure, refused
  commands), A.U30.19 (C-stack escalation L1), A.U32.06 (`get_last_task_end()` L1), A.U8.12 (read: escalation
  arithmetic unchanged), A.U31.01 (read: the stall budgets cite this file's section), A.U35.12 (`:945` limit comment).
- **Site**: `tests/test_system_service.py:936-1254`; new tests.
- **Change**: `_count_collects_during_supervision()` patches `asy_system_service.gc` and runs `await svc.start_tasks(
  starters, ["T"] * len(starters))` then the supervisor task; `:1007-1025` hold (N + 1 boot collects, none in the
  supervisor; an empty list collects once). `:941`, `:1027`, `:1052`, `:1081`: `start_tasks()` then `sup =
  create_task(svc.supervise_tasks())`, `feed_count` asserted, `cancel(sup)`. `:1236` →
  `test_the_supervisor_escalates_past_the_failure_budget`: `_RUN_BOUND_S = 5  # @tunable l1.system_service_run_bound_s`
  bounds the wait for `svc._reset_armed`; the supervisor task is then cancelled, `_reset_timer.trigger()` and a pump
  (`SimulatedResetError` caught): `reset_count == 1`, region 0 code 5, one `code("E", "TASK_BUDGET_REBOOT")`, `call_count
  >= 4` (A.U8C2.51's Dependant). New: A.U31.07's 22-dead pass (exactly 4 task-end entries plus the escalation entry,
  `feed_count` +1 inside the pass, starters called for the first three ends only) and 3 deaths (all restarted, decay);
  A.U11.03 (c) (a store's staged write flushed before the arm; the supervisor still pending two passes later;
  `feed_watchdog()` no longer feeds); A.U30.19 (the fatal flag set → one pass calls `_reboot()` with code 20, no feed
  after it); A.U32.06 (`get_last_task_end()`: `None` before, `{"Task": "X", "Uptime": <fake uptime>}` after, a starter
  raising at start sets nothing, two tasks of one module differ); A.U11.10 (`run_setups()` awaits in order, feeds once
  after each, collects N + 1 times with the feed first, a raising setup propagates and nothing after it runs); A.S0930.24
  (a)-(e) and A.S0930.36 (a)-(e) as listed there (takeover leaves direct/supervisor/`run_setups()` feeds unchanged; the
  healthy count `2 + stores + chunks + tasks + (…) + 1` with the gap bounds from `_TASK_CHECK_TIME` read from source; one
  hang test per step S1-S6, 1 s pumped with `feed_count` frozen; the S6 arm failure; a refused command never stops the
  supervisor's feeding). Every task fake's `Task` name is passed through `start_tasks()`'s names.
- **Resolved**: A.U20.06 (the split) and GAP-G5 (names required) land on the same calls.
- **Unit**: U20 (stages U11 supervisor-as-task and takeover, U30 C-stack, U31 escalation feed, U32 names).
- **Depends**: M.SRC_CORE.015, .016; M.TEST_HELP.052 (sleep_ms), `tests/machine.py` `WDT.feed_times` (A.S0930.24, TEST_HELP).
- **Blast carried by**: twin/L3 supervisor checks → A.U20.06, A.S0930.28 (TWIN, HW_DEV); scan-budget scenario →
  A.U10.08/A.U31.07 (TEST_HELP).
- **Kind**: test

### M.TEST_UNIT.310 The reset-reason record and boot phases
- **From**: A.U11.07 (new section), A.U26.28 (read: the bench reads this file's boot-phase tests as the L1 reference).
- **Site**: new section.
- **Change**: each intended path — `reboot_system()`, `reboot_bootloader()`, the supervisor escalation, the arm-failure
  starve — then the trigger or starve, then `begin_boot()` returns 3, 4, 5, 6 and clears region 0; `machine.power_on()`
  → 1 even with a stale valid record; no record after a complete boot → 2; a wrong check word → 0; for p in 1-5:
  `begin_boot()`, `boot_phase(q)` for every q ≤ p, then a simulated watchdog reset (`reset_cause_value = WDT_RESET`,
  regions kept) → `begin_boot()` returns `10 + p`; after `boot_phase(BOOT_DONE)` → 2; the command codes 7, 8, 9 and 20
  through their paths (M.TEST_UNIT.306, .309). Phase and code constants read with `src_const`.
- **Resolved**: —
- **Unit**: U11 (codes 7-9 with the gate; 20 in U30).
- **Depends**: M.SRC_CORE.006; M.TEST_HELP (`mem_backup`, `reset_cause`, `power_on`, A.U11.07).
- **Blast carried by**: generated-device boot-phase scenario → A.U11.07 (TEST_HELP).
- **Kind**: test

### M.TEST_UNIT.311 The settings store: through `_set_dict_cfg()`, the provider, the stored level wins
- **From**: GAP-G3 (`get_debug_level()`/`set_debug_level()`/`_current_debug_level` gone: tests go through `_set_dict_cfg()`),
  A.U5.08 (every `set_level_setters(` → the provider), A.U11.12 (`:1290-1308` rewritten; `:1271-1288` hold; new L1),
  A.U10.36 (nested `get_dict_cfg()`), A.U11.24 (read: the store writes on its own schema), A.U2.08 (`:1380` 7 →
  `CALLBACK`), A.U11.32 (read: `config_SYSTEM.cfg` path assertions hold), A.U36.544 (`:1370` "WP8:" label dropped).
- **Site**: `tests/test_system_service.py:1256-1420`.
- **Change**: a level is set with `await svc._set_dict_cfg({"DebugLevel": n}, svc.get_cfg_schema())` (the `/system`
  PUT's call) and read back through `get_dict_cfg() == {"SYSTEM": {"DebugLevel": n}}` and the registered setters'
  recorded calls. `:1271` → `cfgmgr.valid`, `get_dict_cfg()` reads 0. `:1278` `level_setters=lambda: [calls.append]`;
  `calls == [0]`. `:1290` → `test_an_unreadable_store_keeps_the_constructed_level` (A.U11.12: `log=LogConfig(None, 10,
  3)`, the store unreadable via a directory-free `cm.os` stand-in raising `OSError(5)` — `writable is False` — every
  registered logger keeps 3, no setter call; the private seeding and the `get_int_values` method assignment go).
  `:1310` → `…_set_dict_cfg_persists_and_calls_every_setter`; `:1323` → `{"DebugLevel": 99}` answers "Invalid", no setter
  call; `:1335` before `setup()` → every key "Failed"; `:1341` holds through `_set_dict_cfg`; `:1353` holds; `:1369` →
  `test_a_bad_setter_persists_one_callback_entry` (newest `code("E", "CALLBACK")`, the "WP8:" label goes); `:1384` reboot
  survives: a second service over the same `cfg_path` reads the stored level (flush in the same coroutine, convention);
  `:1395` holds; `:1401` (`set_level_setters()` replaces) goes with the method (guard: the provider is resolved once in
  `setup()`, `:1278`). New: `test_a_stored_level_wins_over_the_constructed_one` (stored 4, `log=LogConfig(None, 10, 2)`:
  every logger incl. `CFGMGR_SYSTEM` reads 4 after `setup()`).
- **Resolved**: GAP-G3 (M_SRC_CORE) is this rewrite.
- **Unit**: U11 (stages U5 provider, U10 nested shape).
- **Depends**: M.SRC_CORE.017, .018, .043.
- **Blast carried by**: `tests/_sensortask_scenarios.py:692-747, 937-940` → GAP-G3 (TEST_HELP).
- **Kind**: test

### M.TEST_UNIT.312 The logger registry end to end; comment names
- **From**: A.U36.513 (`:1413-1414`), A.U11.13 (setters return `bool`), A.U11.15 (`get_level()` → `.level`).
- **Site**: `tests/test_system_service.py:1412-1420`.
- **Change**: `level_setters=lambda: [svc.pr.set_level]` cannot reference `svc` before construction — the provider closes
  over a one-element list filled after construction (`holder = []`; `level_setters=lambda: [holder[0].pr.set_level]`);
  `_set_dict_cfg({"DebugLevel": 1}, …)` → `svc.pr.level == 1`. Comment → "# (exactly what every generated module's
  _collect_level_setters() does for every module, sysfunct's own included)".
- **Resolved**: —
- **Unit**: U11 (stage U36 comment).
- **Depends**: M.SRC_CORE.017, .062.
- **Blast carried by**: —
- **Kind**: test

## tests/test_ticks_rollover.py

### M.TEST_UNIT.313 Interpreter-level wrap tests stay; the line sweep moves to L0; docstring states the proof
- **From**: A.U14.32 (docstring line 2; `:25-27` comment; `:57-73` unchanged), A.U14.33 (`:94-107` removed to the L0 scan,
  `:110-123` kept and shared with it), A.SDEP.15 (`:35, :49, :51, :61-62, :70-71, :88-89` `type-var` ignores re-checked
  against the refreshed stub), A.U14.28 (read: this file and the 2**30 fake are the tick-period row's mitigation).
- **Site**: `tests/test_ticks_rollover.py:1-131`.
- **Change**: docstring → "Real-interpreter checks of ticks_ms()/ticks_diff()/ticks_add() wraparound (SPECIFICATION.md
  F.1: rp2's 2**30 period vs this rig's 2**62). No src/ tick user subtracts ticks directly; stored ticks and their
  horizon are checked by the L0 scan and the 2**30 fake (Part F.1)." (3 lines). `:25-27` → "# time.ticks_add() accepts a
  delta strictly between -period/2 and period/2 / # (extmod/modtime.c:178-196, <pin>) - the bisection finds the positive
  bound." The wrap tests `:45-91` hold. `test_no_src_module_measures_elapsed_time_by_subtraction` (`:94-111`) goes
  (guard: the L0 AST scan of A.U14.33 over `src/`, `digital_twin/` and every generated module, with its known-bad
  fixtures). `_KNOWN_TICKS_USERS` stays as the one list both tiers read and follows the end-state tick users the scan
  finds (`asy_base_classes.py` joins with `TickSeconds`; `asy_udp_socket.py` leaves once its `ready()` waits through
  `wait_for_ms` with no tick use, M.SRC_NET.028); `test_every_known_ticks_user_…` (`:114-125`) holds over that list. The
  `# type: ignore[type-var]` lines stay while the pinned stub still types `ticks_add()`'s first parameter as `_Ticks`;
  they go (with `warn_unused_ignores` then flagging any left) if the re-check finds the gap fixed.
- **Resolved**: A.U14.34 names `asy_udp_socket.py` among the users to cross-test; M_SRC_NET's UDP end state has no tick
  site left (M_SRC_NET gap 5), so its crossing tests have nothing to cross and are not written (agent decision D-T30).
- **Unit**: U14 (stage U0/U37 stub re-check).
- **Depends**: M.SRC_NET.028; L0 scan (A.U14.33, TSC).
- **Blast carried by**: L0 scan file and fixtures → A.U14.33 (TSC); SPEC F.1 sentence → A.U14.32 (SPEC).
- **Kind**: test

### M.TEST_UNIT.314 One crossing test per tick call site under the 2**30-period fake
- **From**: A.U14.34 (the crossing tests; the helper is TEST_HELP's `tests/_ticks30.py`).
- **Site**: new tests in `tests/test_ticks_rollover.py`.
- **Change**: `test_ticks30_matches_the_real_module_away_from_the_wrap` (the fake's own self-test against the real
  `time` on values away from the wrap). Then, per `ticks_diff()`/`ticks_add()` call site of the end-state users
  (`asy_base_classes.py`, `asy_bmp3xx_driver.py`, `asy_isl29125_driver.py`, `asy_notification_service.py`,
  `asy_uart_comm.py`, `asy_uart_driver.py`), grouped by function: `Ticks30Time` installed as the module's own `time`
  (restored in `finally`), `now` placed so the function's interval straddles 2**30, and its result equals the same call
  with `now = 10_000`. The ISL29125 stored-tick and UART `_holdoff_active` sites get their crossing tests with the U15/U17
  fixes (M.TEST_UNIT.059 and .160 carry the rewritten rollover tests).
- **Resolved**: —
- **Unit**: U14 (stage U15/U17 for their sites).
- **Depends**: M.TEST_HELP.064 (`_ticks30.py`); the end-state tick sites (M.SRC_CORE.032, M.SRC_SENS, M.SRC_NET UART).
- **Blast carried by**: SPEC F.1 names the fake → A.U14.32 (SPEC).
- **Kind**: test

## tests/test_uart_comm_hazard.py

### M.TEST_UNIT.315 Imports, shared runner, sync-scope pair, wire copies, header comments
- **From**: GAP-T1 (M.TEST_HELP.023/.024: the harness `run()` is deleted, `RUN_LIMIT_S` public), A.U8C.03 (blast:
  `POLL_WAIT_MS`/`RUN_LIMIT_S` imported, not restated), A.U24.08 (via M.TEST_HELP.023's blast: `hazard_pair()` builds
  its fixture at synchronous scope), A.U10.37/A.U10.38 (`crc_checks` → `asy_crc_checks`, `CRC_Base` → `CRCBase`,
  `UART_Comm` → `UARTComm`), A.U24.73 (the five `Any` lines), A.U0.07 (the function-level imports at `:488`, `:786-787`,
  `:999`, `:1040`, `:1251`), A.U24.02 (rule (b) for the J.3 copies), A.U13.17 (`:32` comment), A.U0.40 (`:48` comment),
  A.S0930.03 (read: the both-modes rule is owner-confirmed).
- **Site**: `tests/test_uart_comm_hazard.py:1-112`; every `run(` in the file.
- **Change**: imports `import asyncio`, `import gc`; `from _async_harness import run`; `from _error_codes import code`;
  `from _uart_comm_harness import POLL_WAIT_MS, RUN_LIMIT_S, Pair, accept_set, echo_get, frames`; `from asy_crc_checks
  import CRC16`; `from asy_uart_comm import ROLE_INITIATOR, ROLE_RESPONDER, ResponderCallbacks, UARTComm`; `from
  asy_uart_driver import UART as Driver`; under `TYPE_CHECKING`: `from asy_crc_checks import CRCBase`, `from
  asy_uart_comm import ListenResult` (`typing.Any` goes). `CrcMaker = Callable[[], CRCBase] | None`, its comment's
  `CRC_Base` → `CRCBase`. `listen_once()` → `-> "tuple[ListenResult, bytes]"`; the two `scenario()` returns at `:145`,
  `:213` → `"tuple[bytearray | None, bytearray | None]"` / `"tuple[bool, bytearray | None]"`. `:30-32` comment's last
  clause → "… - 24ms here, the harness setting poll_idle_ms equal to poll_wait_ms." `:48-49` → "# Every check runs
  both with and without a CRC (agent, 2026-09-12; owner, 2026-09-30) - the dev wiring selects CRCPass, but a CRC
  changes / # which corruptions are detectable at all (SPECIFICATION.md Part E.8). `crc()` builds a fresh instance per
  pair: CRCBase carries state." The `_CMD_ACK` … `_POS` block gains one comment line "# The wire layout of
  SPECIFICATION.md Part J.3 - the protocol's own copy, pinned to the module by tests_scripts/test_const_mirrors.py."
  (as M.TEST_UNIT.153). `hazard_pair()` stays synchronous: `assert run(pair.setup(), RUN_LIMIT_S) is True`; `raw_frame()`
  `run(crc().add(frame), RUN_LIMIT_S)` (both called only from a check's synchronous scope — the shared `run()` now
  raises if not). Every bare `run(x)` → `run(x, RUN_LIMIT_S)`; every `run(x, limit=N)` → the M.TEST_UNIT.316 constant.
- **Resolved**: A.U0.40 rewrites the `:48` tag to "(agent, 2026-09-12)"; A.S0930.03 records the owner confirming the
  both-modes rule at every level (2026-09-30, OR116/OR118.a (1)) — the later owner row adds its tag beside the agent's.
- **Unit**: U24 (stages U10 names, U13 comment, U0 tag).
- **Depends**: M.TEST_HELP.023, .024, .043, .045; M.SRC_CORE.115; M.SRC_NET.153, .154.
- **Blast carried by**: the J.3 copies' check → A.U24.02 (TSC); `tests_scripts/test_import_placement.py` `_PENDING` entry
  → A.U0.07 (TSC).
- **Kind**: test

### M.TEST_UNIT.316 Tuned literals become tagged module constants
- **From**: A.U8C.43, A.U8C2.15, A.U8.14 (read: the `:1247` threshold site goes with M.TEST_UNIT.323).
- **Site**: `tests/test_uart_comm_hazard.py` — every line A.U8C.43 and A.U8C2.15 list.
- **Change**: exactly as the two actions write them: `# @tunable l1.uart_comm_hazard_timeout_ms = 30` above
  `_TIMEOUT_MS`; new tagged `_LIMIT_S = 10`, `_TASK_BOUND_S = 8`, `_LISTENER_SETTLE_MS = 5`, `_CONCURRENCY_LIMIT_S = 25`,
  `_LOCK_TAKE_MS = 1`, `_IN_FLIGHT_MS = 2`, `_LISTENER_PARK_MS = 5`, `_EXCHANGE_LIMIT_S = 20`, `_RECOVERY_LIMIT_S = 30`,
  `_RETENTION_LIMIT_S = 120`, `_STEP_BOUND_S = 5`, `_FRAGMENT_GAP_MS = 3`, `_MISMATCH_LIMIT_S = 60`, `_HAMMER_LIMIT_S =
  300`, tags above `_WARMUP` (20), `_MEASURED` (100), `_HAMMER_ROUNDS` (150); `_CRC_TIMEOUT_FACTOR = 8` (`timeout_for()`
  returns `_TIMEOUT_MS * _CRC_TIMEOUT_FACTOR`), `_SUSTAINED_TIMEOUT_FACTOR = 8` (`_SUSTAINED_TIMEOUT_MS = _TIMEOUT_MS *
  _SUSTAINED_TIMEOUT_FACTOR`), `_RECOVERY_ATTEMPTS = 4`, `_RETENTION_PER_TRANSACTION_MAX_BYTES = 6.0`,
  `_RETENTION_PER_FAILURE_MAX_BYTES = 16.0`, each tagged with its `l1.uart_comm_hazard_*` ID, each listed literal
  replaced. The `4` exchanges of the mismatch check stay a derived count (M.TEST_UNIT.319). The `gc.threshold_bytes`
  mirror A.U8C.43 tags at `:1247` takes no tag: the line goes (A.U30.13).
- **Resolved**: A.U8C.43 tags `:1247`; A.U30.13 deletes it and withdraws its `gc.threshold_bytes` site (conventions
  bullet "`@tunable` tags").
- **Unit**: U8C.
- **Depends**: A.U8.01-A.U8.03 (grammar, register).
- **Blast carried by**: Part N rows and SPEC J.7's citation of the two factor IDs → A.U8C.43, A.U8C2.15 (SPEC).
- **Kind**: test

### M.TEST_UNIT.317 Direct constructions take one callbacks object; the rxbuf refusal names its code
- **From**: A.U5.12 (`:789`, `:808`, `:1115`, `:1171`), A.U13.17 (the driver's idle default is now 50 ms), A.U2.20
  (rxbuf code), A.U13.13 (read: frames fit the driver buffers — holds), A.U24.73 (`:1182`); adherence (`:783` changelog
  label; a vacuous refusal assertion); OR141.a (4) (e) (the refusal is the ring floor's from U17; A-C review fold).
- **Site**: `tests/test_uart_comm_hazard.py:781-791`, `:805-811`, `:1113-1118`, `:1170-1192`.
- **Change**: `_mismatched_responder()`, the lost-ACK responder and `reborn` → `UARTComm(pair.driver_b, ROLE_RESPONDER,
  payload_size=…, timeout=pair.responder.timeout, callbacks=ResponderCallbacks(echo_get(b"v"), accept_set(), None),
  name=…)`; `_mismatched_responder() -> UARTComm`. The construction-refusal check builds `Driver(0, tx_pin=0, rx_pin=1,
  rxbuf=32, txbuf=256, poll_wait_ms=POLL_WAIT_MS, poll_idle_ms=POLL_WAIT_MS)` — with the new 50 ms idle default the
  timeout floor (2 × 1 + 50 + 21) would refuse it first and the bare `_init_errno != 0` would pass for the wrong reason
  — and asserts `comm._init_errno == code("E", "UART_RXBUF")`; from U17 the same check builds the driver with a ring below
  the floor and asserts the ring-floor code (M.SRC_NET's, by catalog name); its comment's "(B17)" → "(SPECIFICATION.md
  Part J.6)".
  The reset-peer check creates each attempt's listener inside `one()` (no task created at synchronous scope, no
  default-argument binding), `one() -> "bytearray | None"`.
- **Resolved**: —
- **Unit**: U5 (stages U13 idle rate, U2 code, U17 ring floor, U36 label).
- **Depends**: M.SRC_NET.154, .155, .156; M.SRC_NET (driver `poll_idle_ms = 50`, A.U13.17).
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.318 Expected codes by catalog name; the errno helper's premise restated
- **From**: A.U2.20 + A.U24.02 (rule (c): the RF135 copies `:544-550` go), A.U3.08 (a resync persists only W54 on the
  drain bound, M.SRC_NET.162 — the helper comment's premise), A.U24.73.
- **Site**: `tests/test_uart_comm_hazard.py:538-640`.
- **Change**: the seven `_ERR_*` copies go; assertions read `code("E", "UART_NO_ACK")`, `code("E", "TIMEOUT")` (was
  `_ERR_READ_TIMEOUT`, the shared 22), `code("E", "UART_PAYLOAD_TOO_LARGE")`, `code("E", "UART_SIZE_MISMATCH")`,
  `code("E", "UART_REENTRANT")`, `code("E", "UART_PEER_INITIATED")`, `code("E", "BAD_ARG")`. Section comment `:539-541`'s
  "(SPECIFICATION.md Part J, errno 10-34)" → "(the global catalog's UART band, SPECIFICATION.md Part C.7.1)".
  `errnos()`/`last_errno()` take `UARTComm`; the `errnos()` comment → "# Errors only: ErrNum holds both kinds and
  ErrType tells them apart. Indexed, not zip()ed: MicroPython has no strict=." `_check_a_bad_argument_reports_errno_34_
  before_anything_reaches_the_wire` → `_check_a_bad_argument_reports_bad_arg_before_anything_reaches_the_wire` (the
  number is no longer 34). `:633-634` `assert run(pair.setup(), RUN_LIMIT_S) is True`. The two "Read outside the
  coroutine" comments stay (the shared `run()` raises on nesting; reading in sync scope is still required).
- **Resolved**: —
- **Unit**: U2 (stage U3 comment).
- **Depends**: M.SRC_NET.153, .162; M.TEST_HELP.045.
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.319 The mismatch diagnostic fires: blind spot inverted, CRC16 case added
- **From**: A.U17.13 (`:836-862` inverts; new CRC16-only L1 and its `_MODE_SPECIFIC` entry), A.U2.20 (`:801` copy goes),
  A.U8C2.51 (read: the exchange count is the `uart.diag_resync_streak` row's Dependant), A.U17.15 (read: SPEC J.6 names
  this check), A.U26.33 (read: the L1 resync tests stay the recovery bound's source — hold).
- **Site**: `tests/test_uart_comm_hazard.py:795-862`; new check after `:862`; `_MODE_SPECIFIC` `:1273-1276`.
- **Change**: section comment `:796-799` "diagnosed (errno 32)" → "diagnosed (E89, link unintelligible)"; `_ERR_LINK_
  UNINTELLIGIBLE = 32` goes, uses read `code("E", "UART_LINK_UNINTELLIGIBLE")`. `_check_a_peer_that_never_produces_a_
  valid_frame_is_diagnosed`: one exchange in its own `run(…, _RETENTION_LIMIT_S)`, then `code("E",
  "UART_LINK_UNINTELLIGIBLE") not in errnos(responder)`; three more exchanges in a second `run()`, then it is in; the
  "Pins the known blind spot" comment → "# A speak-when-spoken-to peer with a mismatched payload_size: its frames die
  inside the failing read, which now counts them, so the diagnostic fires once the streak is reached (J.6)."; the
  `_ERR_READ_TIMEOUT in codes` assertion and the "invert this test" message go. New
  `_check_a_peer_whose_frames_all_fail_their_crc_is_diagnosed` (`_MODE_SPECIFIC` "crc16"): `hazard_pair(crc)`, the
  initiator→responder direction's `corrupt_indices = {k * wire_frame(crc) - 1: 0x01 for k in 1..16}` (each frame's last
  CRC byte flipped, every frame completing), four `uart_set(0x02, b"x")` exchanges with a listener each → `code("E",
  "UART_LINK_UNINTELLIGIBLE") in errnos(pair.responder)`. The checks whose instances see at most one blind resync before
  their assertion (`:567-589`) or assert only convergence or `ErrCount` (`:648-711`, `:930-996`, `:1036-1095`) hold; the
  executor re-runs both modes to confirm (A.U17.13's own step).
- **Resolved**: —
- **Unit**: U17 (stage U2 code).
- **Depends**: M.SRC_NET.162, .169; M.SRC_NET driver `discarded_bytes` (.196/.200/.201).
- **Blast carried by**: the driver's `discarded_bytes` L1 cases → M.TEST_UNIT.176 (this cluster); L2 mismatched
  pair → A.U17.13 (TWIN); SPEC J.6 and changelog B26 → A.U17.15 (SPEC, DOCS); Part N Dependants → A.U8C2.51 (SPEC);
  SPEC E.8 single-mode count → GAP (SPEC, "Gaps").
- **Kind**: test

### M.TEST_UNIT.320 A GET must declare one chunk: sweep and wire representatives
- **From**: A.U17.16 (new sweep; no-ACK list entry), A.U17.24 (the "GET with SIZE 2" representative), A.U17.12 (read:
  the existing sweeps `:237-339` and the no-ACK list hold).
- **Site**: `tests/test_uart_comm_hazard.py:237-301`.
- **Change**: new `_check_the_chunks_field_sweep_accepts_only_one_for_a_get`: for `chunks` 0…255,
  `pair.responder._validate(bytearray(raw_frame(cmd=_CMD_GET, size=1, chunks=chunks, cur=1, crc=crc)), _CMD_GET, 1,
  None, None) == 0` iff `chunks == 1`. `_check_no_ack_is_emitted_for_any_rejected_frame`'s list gains `("GET with CHUNKS
  2", raw_frame(cmd=_CMD_GET, chunks=2, crc=crc))` and `("GET with SIZE 2", raw_frame(cmd=_CMD_GET, size=2, chunks=1,
  crc=crc))`. `:211` (GET, one chunk) and `:627` (GET with two chunks where an ACK is due — rejected as the wrong kind
  first) hold.
- **Resolved**: A.U17.24 (3) sweeps a GET's CHUNKS too and cites A.U17.16 for it — the one CHUNKS sweep is this check;
  M.TEST_UNIT.321's GET-field sweep covers the other four fields.
- **Unit**: U17.
- **Depends**: M.SRC_NET.159.
- **Blast carried by**: L2 sweep → A.U17.25 (TWIN); SPEC J.4 sentence → A.U17.16 (SPEC); changelog Class A A13 →
  A.U17.16 (DOCS).
- **Kind**: test

### M.TEST_UNIT.321 Field sweeps at every position, and a train ending in an empty chunk
- **From**: A.U17.24, A.U2.20 (codes in the ACK case).
- **Site**: new checks after `:339`.
- **Change**: at `_validate()` level, all 256 values each, J.3/J.4 as the independent oracle:
  `_check_the_last_chunk_size_sweep_follows_the_train_shape` (`chunks=3, cur=3` accepted iff 1 ≤ size ≤ `_PAYLOAD`;
  `chunks=2, cur=2` iff 0 ≤ size ≤ `_PAYLOAD`); `_check_every_ack_field_sweep_accepts_only_the_ack_shape` (expecting
  an ACK for UID `u`: CMD iff 0x01, SIZE iff 0, CHUNKS iff 1, CUR_CHUNK iff 1, UID iff `u` — 0xFF returns `code("E",
  "UART_FRAME_INVALID")`, any other mismatched UID `code("E", "UART_NO_ACK")`, asserted apart);
  `_check_every_get_field_sweep_accepts_only_a_one_byte_first_chunk` (CMD iff 0x02, first-chunk SIZE iff 1, CUR_CHUNK
  iff 1, UID iff ≤ 0xFE); `_check_the_data_chunk_uid_sweep_accepts_only_the_successor` (`chunks=3, cur=2` against the
  expected next UID of 0x00, 0x7F and 0xFE — the 0xFE → 0 wrap); `_check_the_chunks_constancy_sweep_accepts_only_the_
  latched_total` (chunk 2 of a train latched at 4, accepted iff CHUNKS == 4); `_check_the_command_sweep_against_an_
  expected_ack_and_get` (the SET sweep's twin for the other two kinds). `_check_a_three_chunk_train_ending_in_an_empty_
  chunk_is_rejected`: chunks 1-3 fed (UIDs 1-3, SIZE 1, `_PAYLOAD`, 0, `chunks=3`), `result.cmd_id is None` and exactly
  two ACK frames (`2 * wire_frame(crc)` bytes) on the responder's wire.
- **Resolved**: —
- **Unit**: U17.
- **Depends**: M.SRC_NET.159; M.TEST_HELP.045.
- **Blast carried by**: tier map row → A.U17.25 (SPEC).
- **Kind**: test

### M.TEST_UNIT.322 Cancel or clear a transaction at every await, then recover
- **From**: A.U17.23, A.U10.18 (`session_lock`), A.U10.44/A.U32.06 (the restart path is `start_asy_listen()`), A.U17.25
  and A.U36.539 (read: the tier map lists this file as H1/H2/H3 L1 — holds).
- **Site**: new section "Cancellation and restart at every await" before the registration block (`:1270`).
- **Change**: section comment (≤ 3 lines) "# A transaction cancelled or cleared at any await leaves the instance free and
  the peer recovering through J.5; the reboot case is the reset-peer check above." Helper `_sweep(crc, make_work,
  cancel: bool)`: for k = 1, 2, … it builds `pair = hazard_pair(crc)` at synchronous scope and drives one `run(…,
  _EXCHANGE_LIMIT_S)` holding a listener (`_listen_rounds`), the work task and a watcher that cancels the work (or awaits
  `pair.responder.clear()` when `cancel` is false) at its k-th step and records whether the work had already finished; a
  step is one `await asyncio.sleep_ms(0)` of the watcher without a CRC and one new driver I/O entry in `fake.log` with
  CRC16. After each k: `_busy is False`, `_in_resync is False`, `driver.session_lock.locked() is False`, and `not
  _holdoff_active or 0 < time.ticks_diff(_holdoff_deadline, time.ticks_ms()) <= _resync_window_ms()`; then at most two
  further transactions (each in its own `run()` with its own listener), the second at the latest delivering exactly
  the payload, a failed first one having logged a code. The sweep ends at the first k the work finished first. Checks:
  `_check_cancelling_a_set_at_every_await_leaves_both_ends_consistent` (`uart_set(1, bytes(_PAYLOAD * 2))`);
  `_check_cancelling_a_get_at_every_await_leaves_both_ends_consistent` (`uart_get(1)` against `echo_get(bytes(_PAYLOAD *
  2))`); `_check_cancelling_a_set_stream_at_every_await_leaves_both_ends_consistent` (`uart_set_stream()` with a pull
  callback); `_check_cancelling_a_listener_at_every_await_leaves_it_restartable` (the responder's `uart_listen()`
  cancelled mid-SET, then `pair.responder.start_asy_listen()` answers within two attempts, its task cancelled in the same
  `run()`); `_check_clear_at_every_await_leaves_the_transaction_whole_or_failed` (the watcher calls `clear()`). If the
  file then exceeds `scripts/test.sh`'s per-file timeout, the section moves to `tests/test_uart_comm_cancel_sweep.py`
  (A.U17.23), never a per-file override.
- **Resolved**: A.U17.23 calls the restart through `get_task_starters()[0]()`; the starter is named (M.SRC_NET.170) and
  called by name, as in M.TEST_UNIT.159. `_sweep` stays file-local rather than built on `tests/_cancel_sweep.py`: its
  step is an I/O call in CRC16 mode and it has a `clear()` variant, neither of which that helper offers; the per-path
  invariant sweeps of M.TEST_UNIT.166 stay (agent decision D-T31).
- **Unit**: U17 (stage U10 lock name).
- **Depends**: M.SRC_NET.160, .167, .168, .170; M.TEST_HELP.043.
- **Blast carried by**: SPEC J.5 "Unsticking from outside" sentence → A.U17.23 (SPEC).
- **Kind**: test

### M.TEST_UNIT.323 Stress checks run at the process's GC stage; baselines stay
- **From**: A.U30.13 (`:1244-1268`), A.U8.14 (`:1247` goes), A.U17.05 and A.U30.16 (the collects in
  `_measure_retention`, `_hammer_clean.hammer`, `_hammer_faulted.hammer` are measurement baselines on the allow-list),
  A.U8C2.15 (the two retention bounds).
- **Site**: `tests/test_uart_comm_hazard.py:455-536`, `:987-1089`, `:1244-1268`.
- **Change**: `_GC_THRESHOLDS` and `_under_threshold()` go; `_check_sustained_hammering_never_degrades_or_grows_the_heap
  (crc)` calls `_hammer_clean(crc)` once and `_check_hammering_a_faulted_link_never_raises_and_still_recovers(crc)` calls
  `_hammer_faulted(crc)` once; the comment `:1244-1246` → "# Stress checks run at their process's GC stage:
  scripts/test.sh runs this file at gc.threshold(-1) and again at 32768 (SPECIFICATION.md I.4(e)/(f))." The `gc.collect()`
  calls at `:502, :506, :509, :514, :1014, :1016, :1059, :1062` stay (heap baselines, not props); the in-function `import
  gc` lines go to the module import. `:1033` → `per_transaction < _RETENTION_PER_TRANSACTION_MAX_BYTES`, `:1077` →
  `per_failure < _RETENTION_PER_FAILURE_MAX_BYTES`.
- **Resolved**: —
- **Unit**: U30 (stage U8C bounds).
- **Depends**: M.TEST_UNIT.316.
- **Blast carried by**: the allow-list rows `(tests/test_uart_comm_hazard.py, _measure_retention | _hammer_clean.hammer
  | _hammer_faulted.hammer)` → A.U30.16 (SCR/TSC).
- **Kind**: test

### M.TEST_UNIT.324 A latency regression below the sustained budget is caught
- **From**: A.U35.06.
- **Site**: `tests/test_uart_comm_hazard.py` (one new check at most).
- **Change**: at execution, plant `await asyncio.sleep_ms(20)` (then 100 ms) in `UARTComm`'s frame write path in the
  worktree and run the file. If a check turns red, SPEC J.7's sentence names it and this file is unchanged. If none
  does, add `_check_a_clean_transaction_completes_within_its_virtual_time_bound`: on `hazard_pair(crc)` with
  `DrivenTime` installed on `asy_uart_driver` and `asy_uart_comm` (restored on exit), one clean `uart_set(1, b"x")` with
  its listener completes within the healthy virtual duration plus a stated margin, the bound a tagged constant per
  A.U8.02 (`# @tunable l1.uart_comm_hazard_clean_transaction_virtual_ms = <measured + margin>`); the plant is re-run to
  show it red. Either way J.7's "accepted trade-off" goes.
- **Resolved**: —
- **Unit**: U35.
- **Depends**: M.TEST_HELP.065.
- **Blast carried by**: SPEC J.7 `:5613-5617` and the bound's Part N row → A.U35.06 (SPEC).
- **Kind**: test

### M.TEST_UNIT.325 Integrity-envelope comments; the byte-order check is CRC16-only
- **From**: A.U0.40 (`:705`, `:743`), A.U36.544 (`:1225` changelog label), A.S0930.03 (read: the both-modes
  registration `:1279-1296` holds); adherence (a check that returns early in one mode passes vacuously).
- **Site**: `tests/test_uart_comm_hazard.py:704-707`, `:740-745`, `:1221-1241`, `:1273-1276`.
- **Change**: `:705` "The deployed link runs CRC_Pass" → "The dev wiring selects CRCPass"; `:743` "the deployed
  configuration" → "the dev configuration"; `:1224-1225` "(SPECIFICATION.md Part J, UART_C_PORT_CHANGELOG.md A7)" →
  "(SPECIFICATION.md Part J)". `_check_the_crc_appears_on_the_wire_big_endian_after_the_payload` loses its `if crc is
  None: return` and its comment; `_MODE_SPECIFIC` gains `"the_crc_appears_on_the_wire_big_endian_after_the_payload":
  "crc16"` (with M.TEST_UNIT.319's entry, four single-mode checks); the `_MODE_SPECIFIC` comment → "… Some checks are
  about one configuration by construction, not omission: a corruption detectable only with a CRC, or a CRC's own wire
  form, would assert the opposite or nothing in the other mode."
- **Resolved**: the early return passed the no-CRC instance vacuously; registering the check for CRC16 only states
  its subject instead (agent decision D-T32).
- **Unit**: U36 (stage U0 comments).
- **Depends**: —
- **Blast carried by**: SPEC E.8 count → GAP (SPEC, "Gaps").
- **Kind**: test

## tests/test_voc_algorithm.py

### M.TEST_UNIT.326 Harness, shared FRAM builder, names, comments that state facts
- **From**: A.U24.08 (`:28-29` `run`), A.U24.49 + M.TEST_HELP.057 (`make_fram_manager()`/`make_fram_manager_sharing()`
  `:32-44` → the shared builder; the reboot rebuild `make_fram_manager(chip=chip)`), A.U10.37/A.U10.38 (`asy_crc_checks`,
  `FRAMManager`), A.U24.73 (`Any`), A.U14.18 (sync-scope rule, held); adherence (`:12-13` comment points at other files'
  comments instead of stating the fact; `:440`, `:445`, `:530-534` history wording and a `BACKLOG.md` pointer to an
  entry that does not exist).
- **Site**: `tests/test_voc_algorithm.py:1-45`, `:393-499` (the three FRAM tests), `:440-534`.
- **Change**: imports `from _async_harness import run`; `from _fram_builders import make_fram_manager`; `from
  asy_crc_checks import CRC32`; the local `run`, both builders, `AsyFramManager`/`SPI` imports and the `TYPE_CHECKING`
  block go. `:12-13` → "# One FRAM chip type per test process: every SPI bus built here talks to a fake MB85RS64V." The
  reboot test builds `manager, chip = make_fram_manager()` then `manager2, _ = make_fram_manager(chip=chip)`; each
  manager's `setup()`, write and read run inside one coroutine per phase as today (no deferred work crosses a `run()`).
  `write_into()` → `bool` and `read_into()` → `bool | None` (M.SRC_CORE plain-chunk shape): the `is True`/`is False`
  assertions hold. Section header `:440` "Untested-but-safe conditions found during a deeper review pass" → "Negative
  offsets and the uncalled tuning API"; `:445` "but previously untested; no real caller passes a negative offset" →
  "no real caller passes a negative offset"; `:530-534` → "# No caller in this codebase uses it; kept as Sensirion-
  mirroring API surface. A smoke test that it threads the values through and leaves the algorithm usable."
- **Resolved**: —
- **Unit**: U24 (stage U10 names).
- **Depends**: M.TEST_HELP.043, .057; M.SRC_CORE.091 (plain chunk returns).
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.327 Fix16 sentinels are INT32_MIN; the unbounded divide terminates
- **From**: A.U12.11 (`:338-383` expectations; new overflow and termination cases).
- **Site**: `tests/test_voc_algorithm.py:336-383`; new tests after `:383`.
- **Change**: `:340`, `:348` and `:383` expect `-0x80000000` (C's `fix16_t` INT32_MIN), their `# _FIX16_*` notes kept.
  `test_fix16_div_dividing_the_minimum_value_takes_the_shifted_quotient_branch`: `algo._fix16_div(-2147483648, 0x20000)
  == -0x40000000`, comment → "# Dividing FIX16_MINIMUM by 2 drives divider to bit 31, the branch the divisions above
  never reach." (the mod-2**32 paragraph goes). New `test_fix16_div_overflow_returns_the_overflow_sentinel`
  (`_fix16_div(-2147483648, 1)` and `_fix16_div(0x7FFFFFFF, 1)` return `-0x80000000` — C's `if (!bit)` path);
  `test_fix16_div_by_a_multiple_of_two_to_the_32_returns_at_once` (`_fix16_div(F16(1), -(1 << 32))` returns
  `-0x80000000` — the wrapped divisor is 0 — instead of looping). The mul-overflow test (`:343-348`) is the "product
  overflows" case.
- **Resolved**: — (OR101.a approved the fix with a regression test; these are the pinned-defect tests OR12.a names,
  adapted.)
- **Unit**: U12.
- **Depends**: M.SRC_SENS.015, .016.
- **Blast carried by**: release-note line → A.U12.11 via U37 (DOCS); SPEC F.4 sentence → A.U12.15 (SPEC).
- **Kind**: test

### M.TEST_UNIT.328 Helper and whole-algorithm reference vectors
- **From**: A.U12.12.
- **Site**: new tests in `tests/test_voc_algorithm.py`; data in `tests/voc_reference_vectors.py` (M.TEST_UNIT.331).
- **Change**: `test_fix16_helpers_match_the_c_reference_vectors` — for every tuple of the data module's `MUL`, `DIV`,
  `SQRT`, `EXP` tables the port helper returns the recorded C value. `test_the_index_sequence_matches_the_c_reference`
  — a fresh `VOCAlgorithm()` (`vocalgorithm_init()`) is fed the data module's `sraw_sequence()` (its documented LCG walk
  inside 20001..52767 plus the out-of-range samples 0 and 65000); every 500th index equals the recorded value and the
  CRC32 of the whole index list (computed with `asy_crc_checks.CRC32`) equals the recorded checksum. Length 20 000; if
  the file then exceeds `scripts/test.sh`'s per-file budget at execution, 5 000 and the docstring says so (A.U12.12). If
  the archived `Sensirion/embedded-sgp` source is unreachable at execution, the second test is not written and the gap
  is reported "open until the source is available" (OR4.a) — never a skip.
- **Resolved**: —
- **Unit**: U12.
- **Depends**: M.TEST_UNIT.327 (helpers match C first), M.TEST_UNIT.331.
- **Blast carried by**: SPEC F.4 names the vector source → A.U12.15 (SPEC); licence entry → A.U34.04 (DOCS).
- **Kind**: test

### M.TEST_UNIT.329 The persisted state: little-endian, range-checked, clamped, never refusing its own
- **From**: A.U12.14 (`:52` format; four new L1s), A.U12.13 (blast: the uptime-limit L1, placed here).
- **Site**: `tests/test_voc_algorithm.py:51-52`; new tests after `:356`.
- **Change**: `:52` → `struct.calcsize("<32q")` (still 256). New: `test_unpack_from_refuses_a_field_outside_int32`
  (a valid packed buffer with one field set to `2**31` → `unpack_from()` is `False` and `params.__dict__` is unchanged);
  `test_a_restored_uptime_above_the_small_int_limit_is_clamped` (`m_mean_variance_estimator_uptime_gamma` packed as
  `F16(32766)` restores as `F16(16382)`, `…_uptime_gating` likewise); `test_pack_into_writes_little_endian` (a state with
  known fields packed equals the bytes built by hand with `int.to_bytes(8, "little")` per field in the 32-field order);
  `test_the_ports_own_state_always_restores` (the data module's `sraw_sequence()`, after every 500th sample `pack_into()`
  → all 32 fields in −0x80000000..0x7FFFFFFF and `unpack_from()` of that buffer `True`);
  `test_the_lowered_uptime_limit_leaves_the_output_unchanged` (two instances identical except both uptime fields at
  `F16(32766)` in one and `F16(16382)` in the other, fed the same 2 000 post-blackout samples: identical indices and
  identical `pack_into()` bytes apart from the two uptime fields).
- **Resolved**: A.U12.13 writes its L1 without a file; `tests/test_voc_algorithm.py` is `voc_algorithm.py`'s L1 file
  (agent decision D-T33).
- **Unit**: U12.
- **Depends**: M.SRC_SENS.015, .017; M.TEST_UNIT.331 (`sraw_sequence()`).
- **Blast carried by**: A.U10.05's counter exemptions and uptime assertion → A.U12.13 (TSC); SPEC F.4 deviation sentence
  → A.U12.15 (SPEC); `tests/test_asy_sgp40_driver.py:2262-2265` comment → M.TEST_UNIT.144 (this cluster).
- **Kind**: test

### M.TEST_UNIT.330 Out-of-window samples checked against a reference, not only their type
- **From**: A.U24.39 (RF279, `:102`).
- **Site**: `tests/test_voc_algorithm.py:96-107`.
- **Change**: after 50 × 30000, `process(0)` and then `process(65535)` each return an index in 1-500 (comment cites the
  SGP40 datasheet's VOC Index range 1-500) equal to what a second `VOCAlgorithm()` (initialised, same 50 × 30000) returns
  for 30000 once and then once more — an out-of-window sample leaves the raw state as a repeat of the last valid one
  would. The `isinstance` assertions go.
- **Resolved**: —
- **Unit**: U24.
- **Depends**: —
- **Blast carried by**: —
- **Kind**: test

## tests/voc_reference_vectors.py (new)

### M.TEST_UNIT.331 The C reference values as a data module
- **From**: A.U12.12 (data module, generation, header), A.U34.04 (blast: the header cites the BSD-3-Clause source).
- **Site**: new `tests/voc_reference_vectors.py`.
- **Change**: generated once at execution by a throwaway host harness kept in the scratchpad, never committed: it
  `#include`s `Sensirion/gas-index-algorithm`'s fixpoint `sensirion_gas_index_algorithm.c` (`fix16_mul`/`fix16_div`/
  `fix16_sqrt`/`fix16_exp`, `:64-281`) built `-O0 -fwrapv`, and the archived `Sensirion/embedded-sgp`
  `sgp40_voc_index/sensirion_voc_algorithm.c`. Contents: a 3-line docstring "Generated from Sensirion/gas-index-algorithm
  <commit> fixpoint helpers and Sensirion/embedded-sgp <commit> (BSD-3-Clause), <date>; expected values, not the port's
  output. Contains no Sensirion code."; tuple tables `MUL`, `DIV`, `SQRT`, `EXP` over zero, ±1, ±F16(1), INT32_MAX,
  INT32_MIN, values around each overflow edge and 200 LCG pairs (seed and generator stated); `sraw_sequence()` building
  the 20 000-sample walk from its stated LCG (no stored list); `INDEX_EVERY_500` and `INDEX_CRC32`. No `test_` names, so
  `scripts/test.sh` imports it only through the test file; in `tests/` lint and type scope. If the embedded-sgp archive is
  unreachable, `INDEX_EVERY_500`/`INDEX_CRC32` are absent and reported open (OR4.a).
- **Resolved**: —
- **Unit**: U12.
- **Depends**: —
- **Blast carried by**: `THIRD_PARTY_LICENSES.md` entry naming the file → A.U34.04 (DOCS); SPEC F.4 → A.U12.15 (SPEC).
- **Kind**: test

## tests/test_website_build_integration.py

### M.TEST_UNIT.332 Imports, shared runner, typed Microdot, the service built from its three objects
- **From**: A.U24.08 (`:37-38` `run`), A.U23.47 (`:27`, `:37` `Any`), A.U8.23 (`:16` ignore; the vendored stubs, OR131 —
  firm), A.U28.28 (`:15` F401 `noqa` → `allowed-unused-imports`), A.U0.07 (`:45`, `:47` function-level imports), A.U27.03
  (`:42-44` DeflateIO removal trigger), A.SDEP.08 (`:43` version-stamped claim), A.U5.04 + A.U19.05 (construction with
  a static site), A.U19.06 (`:54` request carries `sock=`), A.SDEP.06/A.SDEP.07 (read: re-vendored Microdot and freezefs —
  the dispatch and mount assertions hold), A.U36.517 (read: SPEC's description of this file holds).
- **Site**: `tests/test_website_build_integration.py:1-60`.
- **Change**: imports `import deflate`, `import io`, `import sys`; `sys.path.insert(0, "ext")` as today; `import
  frozen_html  # type: ignore[import-not-found]  # mounts /html on import` (no `noqa`); `from microdot import Microdot,
  Request` (no ignore); `from _async_harness import run`; `from _src_const import src_const`; `from _strict_json import
  strict_loads`; `from _twin_devices import generated_devices`; `from asy_webserver_service import RouteSources,
  ServingLimits, StaticSite, WebserverService`. The local `run`, `Coroutine`/`Any`/`TypeVar` go; `_ResponseBody` stays
  under `TYPE_CHECKING`. `_decompress()` comment → "# send_file() streams from a file-like object; DeflateIO(AUTO) detects
  the gzip header (<pin>). No `with` and an ignore: the stub declares neither __enter__/__exit__ nor a typed read() -
  removal trigger: SPECIFICATION.md B.15." with `<pin>` the version the A.SDEP.08 re-check confirms. `_make_request()`
  passes `sock=(_NoopHolder(), _NoopHolder())` (a file-local one-method `hold()` fake, as M.TEST_UNIT.196).
  `_make_app()` builds `WebserverService(app, RouteSources([], [], None, None, None, None, [], [], []),
  ServingLimits(<each field from its src/ default via src_const>), StaticSite("/html", "index.html", None))` and runs
  `run(service.setup())`, unbounded like the file's dispatch calls.
- **Resolved**: A.U23.47 retypes the local `run()`; A.U24.08 deletes it for the shared harness, whose `Coroutine` alias
  carries the typing — the deletion is the end state. Test files do not import one another, so A.U19.05's "through
  A.U5.04's helper" is the same three-object construction written here, not an import of `test_asy_webserver_service`'s
  `_make_service()`.
- **Unit**: U24 (stages U0 imports, U5 objects, U8/U0 stub re-vendor, U19 `sock`, U20 noqa, U27 trigger). The `:15`
  `noqa` goes in U20, in the commit that adds `allowed-unused-imports = ["frozen_html"]` (M.TOOL.031's U20 stage): RUF100
  fails on the stale `noqa` the same day, so it cannot wait for U28 (M_TOOL gap 5, gap pass G3).
- **Depends**: M.TEST_HELP.008 (`_strict_json`), .043, .044, .055 (`_twin_devices`);
  M.SRC_NET (webserver construction, A.U5.04; `sock` holders, A.U19.06); M.GEN.050 (stubs).
- **Blast carried by**: `pyproject.toml` `allowed-unused-imports` → M.TOOL.031 (U20 stage); SPEC B.15 list → A.U27.03 (SPEC).
- **Kind**: test

### M.TEST_UNIT.333 Device and bundle facts read from the build, not hand lists
- **From**: A.U24.67 (three variant sites `:5`, `:77`, `:98`), A.U6.04 (blast: `:77` still true — generated definitions
  are never served), A.U23.38 (`:109`, `:120-129` hand lists → derived from the bundle), A.U23.01/A.U23.02 (`:123`
  marker rename), A.U23.07 (`:127` marker holds), A.U24.60 (`:97` → `strict_loads`); adherence (`:5-7`, `:135-137`,
  `:144` describe the pre-A.U23.38 build and a debugging history).
- **Site**: `tests/test_website_build_integration.py:5-7`, `:72-158`.
- **Change**: `:5-7` → "# The real chain: html/ and js/ -> scripts/build_website.sh <first derived device> (staged by
  scripts/_stage_website.py) -> / # frozen_modules/frozen_html.py -> `import frozen_html` (mount on import) ->
  WebserverService. scripts/test.sh builds it / # first; the import mounts /html once per process." `:77`'s path list →
  `("/style.css", "/definitions.json", *(f"/definitions/{d}.json" for d in generated_devices()))`; `:97` →
  `strict_loads(body[start:end])`; `:98` → `== generated_devices()[0]` (the site `scripts/test.sh` builds is the first
  derived device, M.SCR.039; both lists are the sorted TOML stems, the `zz_test_` fixtures sorting last). A helper
  `_bundle_modules(body) -> list[str]` reads the module list from the bundle's banner line. `:101-111`: `/js/app.js` is
  200 and every banner module other than `main.js` is 404 at `/js/<name>`. `:114-130` →
  `test_bundled_js_carries_every_banner_module_and_no_local_imports`: each banner module has a non-empty `// ---- js/<name>
  ----` section, the import/re-export line loop stays, and its comment → "# Nor an `export … from "./x.js"` re-export: the
  bundle has no such path to resolve (scripts/_stage_website.py refuses one; this checks the served result)." `:144`
  "(see scripts/build_website.sh)" → "(scripts/_stage_website.py)". `:154-158` holds.
- **Resolved**: A.U23.02 renames the `fetchWithTimeout` marker "or derived from the bundle banner once A.U23.38 lands";
  A.U23.38 lands the derivation, so the marker list goes and neither rename nor A.U23.07's hold has a site left. The
  per-module check relies on the bundle keeping its `// ---- js/<file> ----` separators (today's format; A.U23.38 (3)
  rewrites the banner, not the separators) — agent decision D-T34, carried as a gap to the staging script's owner.
- **Unit**: U23 (stages U24 variant names and strict parsing, U6 hold).
- **Depends**: M.TEST_UNIT.332; A.U23.38's `scripts/_stage_website.py` (WEB/SCR); M.SCR.039.
- **Blast carried by**: the separator format → GAP (WEB/SCR, "Gaps").
- **Kind**: test


## Cross-file: the 23 L1 files without a header block

### M.TEST_UNIT.334 Every L1 test file opens with one header docstring
- **From**: AC_NOTES 42 (1) (lead, 2026-10-01: G9/R16 "every file opens with exactly one header block", every-file
  scope owner PQ6, 2026-09-26; the gate checks presence), A.U27.28 (5) (header presence: the 23 `tests/test_*.py` of its
  count, each "a ≤ 3-line header naming what the file tests").
- **Site**: line 1 of each file below (HEAD has no module docstring in any of them; new and renamed paths as the
  conventions give them).
- **Change**: each file gains a module docstring of ≤ 3 lines (one line where it suffices), naming what its tests
  prove, from the tests themselves:
  - `tests/test_asy_api_response.py` — "The REST response envelope: field shapes, status mapping and the logged codes."
  - `tests/test_asy_bmp3xx_driver.py` — "BMP3XX driver and reader against the fake I2C bus: calibration, conversion,
    configuration, error ladder and FRAM-backed logs."
  - `tests/test_asy_dns_client.py` — "The DNS client: query encoding, reply parsing, retries and timeouts over a real UDP
    socket on loopback."
  - `tests/test_asy_fram_driver.py` — "FRAM_SPI against the fake MB85RS64V: identification, protection, WREN latching,
    chip loss and the session lock."
  - `tests/test_asy_fram_manager.py` — "FRAMManager and its chunks: allocation, dual-copy reads and writes, CRC, pause,
    timestamped chunks and logged faults."
  - `tests/test_asy_i2c_driver.py` — "The I2C bus and device wrappers: the bus lock, recovery ladder, scratch buffers and
    deadlock bounds."
  - `tests/test_asy_isl29125_driver.py` — "ISL29125 driver and reader: ranges, conversions, interrupt handling, stored
    state and the error ladder."
  - `tests/test_asy_neopixel_driver.py` — "NeopixelDriver: signals, overlays, the readiness gate and its FRAM-backed log."
  - `tests/test_asy_notification_service.py` — "NotificationService: signal validation, thresholds, the sleep window,
    pause and override, all under driven time."
  - `tests/test_asy_ntp_client.py` — "NTPClient: request and reply handling, plausibility, retries, DNS fallback and the
    sync flag, against a fake server."
  - `tests/test_asy_spi_driver.py` — "The SPI bus and device wrappers: chip select, the session lock and rp2's RX-overrun
    fault."
  - `tests/test_asy_uart_driver.py` — "The UART driver: non-blocking reads, framing codecs, the cancel handshake, discard
    counts and write pacing."
  - `tests/test_asy_uart_link_driver.py` — "UARTLinkDriver: the bench exerciser's transfers, failures and banner across a
    real UARTComm pair, in both CRC modes."
  - `tests/test_asy_udp_socket.py` — "UDPSocket: bind, send and receive with readiness waits, retries and logged
    failures."
  - `tests/test_asy_wifi_service.py` — "WifiService: connect, reconnect, hotspot fallback, LED handling and the network
    snapshot, against the network fake."
  - `tests/test_asy_base_classes.py` — "The SensorReader base classes: counters, readiness, timestamps, error checks and
    the trigger loop."
  - `tests/test_asy_captive_dns.py` — "The captive DNS server: query parsing, the derived domain, replies and socket
    teardown on a real port."
  - `tests/test_asy_config_manager.py` — "ConfigManager: schema validation, coercion, stored defaults, deferred writes and
    the logged refusals."
  - `tests/test_asy_crc_checks.py` — "CRC8/16/32 and CRCPass against cited check values: bounds, pass mode and
    incremental use."
  - `tests/test_math_helpers.py` — "The derived-quantity formulas (dew point, wet bulb, altitude, …) against reference
    values computed from their cited sources."
  - `tests/test_asy_print_log.py` — "PrintLogHistory: levels, the bounded history, the central repeat rule, FRAM storage
    and the fatal report."
  - `tests/test_asy_system_service.py` — "SystemService: the boot batch, task supervision, staggered triggers, reboots and
    the watchdog."
  - `tests/test_voc_algorithm.py` — "The VOC Index port: fixed-point helpers and the whole algorithm against Sensirion's
    C, persisted state and restore."
  Each obeys the 3-line cap as `tests_scripts/test_comment_block_cap.py` counts it; where a merged change above already
  rewrites a file's opening comment, the two land as one block.
- **Resolved**: AC_NOTES 42 (1) settles the former owner question 1 (presence is required).
- **Unit**: U27 (with the header-presence check).
- **Depends**: the merged changes of each file (renames U10).
- **Blast carried by**: the presence check and the over-cap rewraps of (3) → A.U27.28 (TSC,
  `tests_scripts/test_comment_block_cap.py`); `tests/microtest.py`'s header → M.TEST_HELP.002.
- **Kind**: test

## tests/test_machine_uart_link.py (no cluster in CLUSTERS.md; taken here, gap pass G3)

### M.TEST_UNIT.335 The UART fake answers a real poll as rp2 does; the contract registry is complete
- **From**: A.U24.15 (new L1: a real `select.poll()` over the fake UART; `ioctl(10, 0)` → `-EINVAL`; `:113-119` holds as a
  local check), A.U24.06 (new `test_every_contract_check_is_registered`); M_TEST_HELP GAP-T4 and the Blast lines of
  M.TEST_HELP.017/.025 (both name this file for TEST_UNIT; it sits in no cluster, gap pass G3).
- **Site**: `tests/test_machine_uart_link.py:1-203`; new tests after `:133`.
- **Change**: the docstring (3 lines) and the HEAD tests hold; `test_poller_is_not_a_real_select_poll` (`:113-119`) holds.
  New `test_a_real_poll_consults_the_fake_and_is_counted`: `poller = select.poll()`, `poller.register(fake_b,
  select.POLLIN)`; `ipoll(0)` reports no event while the fake's RX queue is empty and `POLLIN` once one byte crossed the
  link; `UART.real_poll_queries` rose with each query; `finally`: `poller.unregister(fake_b)` and, after the count was
  asserted, `UART.real_poll_queries = 0` (else the fake's after-each check, M.TEST_HELP.010, fails the test). Only
  `ipoll(0)` is used — a zero-timeout query that never waits, so CLAUDE.md's hang case (a real poll awaited with
  `timeout_ms=-1`) cannot arise; one comment line says so. New `test_an_unknown_ioctl_request_answers_einval`:
  `fake.ioctl(10, 0) == -errno.EINVAL` (`MP_STREAM_GET_FILENO`; rp2's answer, `ports/rp2/machine_uart.c:694-697`,
  re-checked against the refreshed pin). New `test_every_contract_check_is_registered`: the module attributes of
  `_uart_link_contract` named `check_*` equal `{f.__name__ for f in ALL_CHECKS}`, with no duplicate in `ALL_CHECKS`.
- **Resolved**: A.U24.15 and A.U24.06 name this file, which CLUSTERS.md lists under no cluster; M_TEST_HELP's blasts send
  both to TEST_UNIT, which no merged change carried — this one does (gap pass G3, 2026-10-01).
- **Unit**: U24.
- **Depends**: M.TEST_HELP.010, .017, .025.
- **Blast carried by**: CLUSTERS.md entry for this file → orchestrator (GAPS_G3 hand-off).
- **Kind**: test

## tests/test_notification_fram_integration.py (no cluster in CLUSTERS.md; taken here, gap pass G3)

### M.TEST_UNIT.336 Two independent FRAM chunks, built and booted as the generated wiring does
- **From**: A.U2.17 (the six `errno=1` sites `:122-123`, `:145-146`, `:164-165`), A.U5.06 (`:87-88` `register()`/
  `finalize()` → signals at construction), A.U5.11 (`ValueRef`), A.U5.02 (`fram=` → `log=`), A.U10.10 (`pr.setup()` →
  `setup()`), A.U10.37/A.U10.38 (`FRAMManager`, `FRAMChunk`, `NotificationService`, `asy_print_log`), A.U24.08 (`run`),
  A.U24.49/M.TEST_HELP.057 (`make_manager` and the `:151` rebuild), A.U24.73 (`Any`), A.U8C (`:40` untagged: the
  WarnCO2 REST entry is API domain, U8C row), AC_NOTES 42 (1) (header); M.SRC_SENS.031's Blast line names this file for
  TEST_UNIT (gap pass G3).
- **Site**: `tests/test_notification_fram_integration.py:1-171`.
- **Change**: docstring → "Full-stack FRAM integration of the NeoPixel driver and the notification service: their two
  logger chunks are independent, non-overlapping allocations off one FRAMManager, and both histories survive a simulated
  reboot." (3 lines). `:4-9` → "# The generated wiring gives both modules a FRAM-backed log; the service's one chunk covers
  its own fields and every / # signal's check failures. Mocked at the SPI bus, not at FRAMManager's boundary." (2 lines).
  Imports: `from _async_harness import run`, `from _error_codes import code`, `from _fram_builders import
  make_fram_manager`, `from _tmp_scratch import TmpScratch`, `from asy_base_classes import ValueRef`, `from
  asy_fram_manager import FRAMChunk, FRAMManager`, `from asy_neopixel_driver import NeopixelDriver`, `from
  asy_notification_service import NotificationService, NotificationSignal`, `from asy_print_log import LogConfig,
  PrintLogHistoryStore`; the local `run`, `make_manager`, the `asy_spi_driver._SPI` swap (the builder owns it) and the
  `TypeVar`/`Any` lines go. `_FakeSource` carries `WarnCO2 = None` (its comment: "# A producer whose field is always
  None: the test pins the chunk layout, not a threshold."). `make_pixel(manager)` → `NeopixelDriver(0,
  log=LogConfig(manager, 10, None))` (the history length M.TEST_UNIT.079's reboot test uses); `make_notify(manager,
  cfg_path)` → `NotificationService(_request_signal_stub, _local_time_stub, (NotificationSignal("WarnCO2",
  ValueRef(_FakeSource(), "WarnCO2"), _FIELD_WARN_CO2, (1, 0, 0)),), cfg_path=cfg_path, log=LogConfig(manager, 10, None))`
  with the comment "# The same signals in the same order every time: the FRAM layout must decode identically across
  the simulated reboot." Each scenario awaits `pixel.setup()` and `notify.setup()` (not `pr.setup()`); the manager is
  `manager, chip = make_fram_manager()` then `run(manager.setup())`, and the reboot builds `manager2, _ =
  make_fram_manager(chip=chip)` (same chip, fresh objects; `:151` goes). The six `errno=1` sites write and read back
  `_PLANTED = code("E", "CALLBACK")` (one module constant: "# any catalog code; the tests pin separation and survival,
  not the code"); `:107` compares `pixel.pr.fram._block_addr != notify.pr.fram._block_addr` (private after
  M.SRC_CORE.081, gap pass G2); `:119-121` → "# A planted entry: the driver reports no faults of its own (Part A.4); this exercises
  the FRAM-backed history." `PrintLogHistoryStore` and `FRAMChunk` `isinstance` checks hold.
- **Resolved**: the file is in no CLUSTERS.md list, so no merge carried M.SRC_SENS.031's A.U2.17 pointer or the U5/U10
  constructor changes its sibling files take (M.TEST_UNIT.265, .276) — written here to the same end states (gap pass G3).
- **Unit**: U24 (stages U2 codes, U5 constructors, U10 names and `setup()`).
  A-C2 step order: A.U2.17's part lands in U3, not U2 (it follows A.U2.17's own change, which lands in U3).
- **Depends**: M.SRC_SENS.023, .024, .033; M.SRC_CORE (`LogConfig`, `FRAMManager`); M.TEST_HELP.043, .045, .057.
- **Blast carried by**: CLUSTERS.md entry → orchestrator (GAPS_G3 hand-off).
- **Kind**: test

## tests/test_sensortask_<device>.py (six, deleted) → tests/test_sensortask.py (new; no cluster in CLUSTERS.md)

### M.TEST_UNIT.337 One per-device scenario file replaces the six wrappers
- **From**: A.U24.65 (2) (the six `tests/test_sensortask_<device>.py` wrappers replaced by `tests/test_sensortask.py`,
  `globals().update(register_for_device(os.getenv("TEST_DEVICE")))`, `PER_DEVICE = True`, raising at import without
  `TEST_DEVICE`); M.TEST_HELP.035's Blast line ("→ A.U24.65 (TEST_UNIT)", gap pass G3); A.U24.04 (trailer).
- **Site**: `tests/test_sensortask_{arzi,dev,grkizi,klkizi,schlafzi,wozi}.py` (deleted); new `tests/test_sensortask.py`.
- **Change**: the new file: header (≤ 3 lines) "Generated build_system() construction and wiring scenarios for the device
  named by TEST_DEVICE - one job per generated device, dispatched by scripts/test.sh (SPECIFICATION.md E.2.1)."; `import
  os`; `from _sensortask_scenarios import register_for_device`; `PER_DEVICE = True`; `device = os.getenv("TEST_DEVICE")`
  and, when unset, `raise RuntimeError("run through scripts/test.sh, or set TEST_DEVICE to one of devices/*.toml")` at
  import; `globals().update(register_for_device(device))`; the canonical trailer. The six wrappers are `git rm`'d in the
  same commit, as M.TWIN.108 does for the construction wrappers.
- **Resolved**: A.U24.65 creates three `PER_DEVICE` files; M.TWIN.108 carries the construction one, A.U25.46 retires the
  concurrency one (M.TWIN.164), and this file — sited in no cluster — had no carrier (gap pass G3).
- **Unit**: U24.
  A-C2 step order: A.U24.65's part lands in U25, not U24 (it follows A.U24.65's own change, which lands in U25).
- **Depends**: M.TEST_HELP.035 (`register_for_device`), M.TEST_HELP.055 (derived devices).
- **Blast carried by**: `scripts/test.sh` per-device expansion and heavy list → A.U24.65 (3) (SCR, M.SCR.040-.042); L0
  dispatch case → M.TSC.135; SPEC E.2.1/E.3.1 → A.U24.65 (SPEC); README `:157` status-tag example `[test_sensortask_dev]`
  → DOCS (GAPS_G3 hand-off); CLUSTERS.md entry → orchestrator.
- **Kind**: test

## tests/test_tmp_scratch.py (no cluster in CLUSTERS.md; taken here, gap pass G3)

### M.TEST_UNIT.338 Scratch tests: the errno filter, one live key, the recorded calls include the new walk
- **From**: A.U24.10 (blast: the recording `os` wrapper records `ilistdir` and `stat`; the root assertion; new L1 errno
  cases), A.U24.11 (1) (blast: the duplicate-key refusal); M.TEST_HELP.005's Blast line (gap pass G3); AC_NOTES 42 (1);
  A.U24.38 (`:116-123`; A-C3 S-08).
- **Site**: `tests/test_tmp_scratch.py:1-3` (docstring), `:116-123`, `:138-157` (`_RecordingOs`), `:191-197`
  (assertions); new tests.
- **Change**: docstring → "Regression coverage for _tmp_scratch.py's TmpScratch, the per-test-file scratch directory:
  every operation stays inside its own key's subtree, and a cleanup failure other than absence is raised." (2 lines; the
  "now uses instead of its own copy-pasted … trio" history goes). `_RecordingOs` gains `ilistdir(path)` and
  `stat(path)` (record, then forward). In the shared-root test the first assertion becomes `assert not (name in
  ("listdir", "ilistdir", "stat") and path.rstrip("/") == _ROOT)` and the second allows `_ROOT` only for `mkdir` (`assert
  (name == "mkdir" and path.rstrip("/") == _ROOT) or path.startswith(own + "/") or path == own`), so a reintroduced
  `ilistdir(_ROOT)` fails. New, each through a `_RecordingOs` subclass raising on one call: `rmdir` raising
  `OSError(errno.EACCES)` propagates out of `teardown()` with its path; `mkdir` raising `OSError(errno.EEXIST)` is
  silent; `remove` of an absent path (`ENOENT`) is silent. New: a second `TmpScratch` with a key still live raises
  `AssertionError("TmpScratch key <key> already in use")`; after `teardown_all()` the key can be taken again. Each test's
  keys keep the `scratchtest_` prefix. `test_construction_and_teardown_tolerate_a_missing_key_directory_entirely`
  runs under `_RecordingOs`: the recorded calls touch only the key path (never the shared root), and the key directory
  does not exist afterwards.
- **Resolved**: —
- **Unit**: U24.
- **Depends**: M.TEST_HELP.005.
- **Blast carried by**: the cross-file key-uniqueness L0 → A.U24.11 (2) (TSC, M.TSC.118); CLUSTERS.md entry → orchestrator.
- **Kind**: test

## tests/test_driven_time.py (new)

### M.TEST_UNIT.339 The driven clock's own self-test
- **From**: A.U35.10 (L1 self-test `tests/test_driven_time.py`); M.TEST_HELP.065's Blast line (gap pass G3).
- **Site**: new `tests/test_driven_time.py`.
- **Change**: header (≤ 3 lines) "Self-test of tests/_driven_time.py's DrivenTime: virtual time moves only on advance(),
  sleepers wake in order and never early, and every replaced name is restored." Cases as A.U35.10 lists them: two
  sleepers wake in deadline order; `advance()` never runs a sleeper before its deadline; a `ticks_diff()` across the
  installed clock's 2**30 wrap equals the elapsed virtual time; every replaced module attribute is restored when the
  `with` block exits through an exception; a shimmed `wait_for(sleeper, 1)` raises `TimeoutError` after `advance(1000)`
  and not before; a busy loop hits the round cap and fails naming the virtual time reached (the cap is the bound, never a
  wall-clock wait). Driven from synchronous test scope through `_async_harness.run()` (CLAUDE.md's nested-`run()` rule);
  the canonical trailer.
- **Resolved**: —
- **Unit**: U35.
- **Depends**: M.TEST_HELP.065, .064, .043.
- **Blast carried by**: —
- **Kind**: test

## Cross-file: A-C3 sweep changes (new)

### M.TEST_UNIT.340 Docstrings become comments in this cluster's scope
- **From**: A.U10.34 (A-C3 Part S S-05: no carrier in this cluster).
- **Site**: function/class docstrings at HEAD (AST): `tests/test_asy_uart_link_driver.py:143`;
  `tests/test_bus_hazard_generated.py:47`; `tests/test_system_service.py:959`, `:977` (renamed
  `tests/test_asy_system_service.py` in the same unit, A.U10.37).
- **Change**: each function, method and class docstring becomes a `#` comment block directly under the `def`/`class`
  line, same text, ≤ 3 prose lines (overflow to the owning doc per CLAUDE.md's comment rule); module docstrings stay
  (the five argparse readers included). A file a later change rewrites carries the form forward.
- **Resolved**: —
- **Unit**: U10.
- **Depends**: —
- **Blast carried by**: `tests_scripts/test_comment_block_cap.py` stays green → M.TSC.065.
- **Kind**: code

### M.TEST_UNIT.341 File-local builders take the private form
- **From**: A.U24.76 (A-C3 Part S S-07: these files' changes did not name it).
- **Site**: public module-level `def make_` builders at HEAD (count): `tests/test_asy_bmp3xx_driver.py` (4),
  `test_asy_neopixel_driver.py` (1), `test_asy_sgp40_driver.py` (5), `test_asy_spi_driver.py` (2),
  `test_asy_uart_comm.py` (1), `test_asy_uart_driver.py` (1), `test_base_classes.py` (1), `test_captive_dns.py` (3),
  `test_fram_integration.py` (1), `test_machine_uart_link.py` (1), `test_notification_fram_integration.py` (3),
  `test_notification_neopixel_integration.py` (1), `test_notification_scd30_integration.py` (3),
  `test_notification_scd30_sgp40_integration.py` (3), `test_notification_sgp40_integration.py` (2), `test_print_log.py`
  (1), `test_setter_microdot_integration.py` (4), `test_system_service.py` (3), `test_voc_algorithm.py` (2) — all under
  `tests/`, HEAD paths (the U10 file renames apply, conventions above).
- **Change**: every module-level `def make_<x>` → `_make_<x>` with its uses in the file (a builder another change
  replaces by a shared helper is skipped there, e.g. `make_fram_manager` → `tests/_fram_builders.py`, A.U24.49).
- **Resolved**: —
- **Unit**: U24.
- **Depends**: A.U24.49.
- **Blast carried by**: the L0 check (`tests_scripts/test_microtest.py`) → A.U24.76 (TSC).
- **Kind**: test

## Gaps for other clusters

- **GAP-U1 (SRC_SENS)**: M.SRC_SENS.063's backup-age condition follows the register reading of A.U16.18 (G5/R31):
  `cfg_values[1] > 0 and (age < 0 or age > 60 * cfg_values[1])` — a limit of 0 accepts any age, a negative age
  expires. M.TEST_UNIT.138 pins it (agent decision D-T13).
- **GAP-U2 (TSC)**: `tests_scripts/test_error_catalog.py` (A.U2.02) asserts that each of its keyword idioms (`errno=`,
  `wrnno=`) matches at least once over `src/` — A.U24.50 (3)'s non-vacuity floor moves there with the L1 test it
  hardened, which A.U2.02 removes (M.TEST_UNIT.157, D-T14).
- **GAP-U3 (SRC_SENS)** — closed by M.SRC_SENS.023/.024 as amended (AC_NOTES 44), then void: the routine settlement
  `initialized-flags` (AC_NOTES 52, A-C review fold) adds no `initialized` to `NeopixelDriver`; the readiness row asserts
  its public answers only. Original text: AC_NOTES 38 gives `NeopixelDriver` an `initialized` gate, but no merged product change adds it:
  where it is set (`setup()`), and what `on()`/`off()`/`toggle()`/`led_signal()`/`request_signal()` answer before
  `setup()`. M.TEST_UNIT.079 and the readiness L1 (M.TEST_UNIT.293) assert those answers once defined.
- **GAP-U4 (SRC_SENS, observation)**: a stored config value outside the chip's domain (a stale file) makes
  `_apply_stored_config()` return code 2 on its `ValueError`, which climbs to the controller rung and re-initialises the
  bus; OR113's smallest-blast-radius rule suggests code 1 for that case. Tests assert whichever code the product keeps.
- **GAP-U5 (SRC_NET)**: the captive DNS server's `_WRN_SOCKET_TEARDOWN = const(11)` collides with M.SRC_SENS.043's
  catalog numbering (`DERIVED_DOMAIN` 11, `SOCKET_TEARDOWN` 12); the merged tests read `code("W", "SOCKET_TEARDOWN")`, so
  the product constant follows the catalog.
- **GAP-U6 (SRC_NET)**: per GAP-G8, `report_if_fatal()` is imported from `asy_print_log` in the networking modules; the
  L1 tests reach it there (M.TEST_UNIT.292).
- **GAP-U7 (TEST_HELP)**: `microtest`'s after-each hook resets `asy_base_classes._utc_valid = False` and the fatal-report
  flag, so no test inherits another's sync or fatal state (conventions bullet "Timestamps before the first sync").
- **GAP-U8 (TEST_HELP)**: `_ntp_frames.FakeNtpServer.serve_once()` returns `bool` (A.U35.15) and takes its port from
  `PortAllocator` (M.TEST_HELP.056).
- **GAP-U9 (SPEC)**: the Part N row for the notification loop's minimum sleep is `l1.asy_notification_service_next_sleep_min_ms
  = 59000` (A.U8C2.02 writes `_s` = 59.0; A.U31.14 moves the unit to ms) — M.TEST_UNIT.091, D-T7.
- **GAP-U10 (SPEC)**: SPEC E.8's "48 checks, 96 tests … Two are single-mode" for `tests/test_uart_comm_hazard.py`
  follows the end-state registration (four single-mode checks after M.TEST_UNIT.319/.325, plus the new checks of
  M.TEST_UNIT.319-.322); the sentence "The deployed link runs `CRC_Pass`" takes A.U0.40's "the dev wiring selects".
- **GAP-U11 (WEB/SCR)**: `scripts/_stage_website.py` (A.U23.38) keeps writing one `// ---- js/<file> ----` separator per
  bundled module after its derived banner; M.TEST_UNIT.333 reads both (D-T34).
- Carried in, settled in this file (no further action elsewhere): GAP-T1-T6 (TEST_HELP), GAP-G3/G4/G5/G8/G11/G13
  (SRC_CORE), GAP-2/5/6/15 (SRC_SENS), M_SRC_NET gap 5, M_GEN gaps 1 and 2, AC_NOTES 38/39/41/42 — each cited at its
  merged change.

## Adherence findings

- Comments stating history, labels or dead pointers, fixed at their merged change: changelog labels in test comments
  (`test_uart_comm_hazard.py:783` "(B17)" → M.TEST_UNIT.317; `:1225` A7 → .325); "until now"/"previously untested"/a
  `BACKLOG.md` pointer to no entry (`test_voc_algorithm.py:440-534` → .326); a pointer to other files' comments instead
  of the fact (`test_voc_algorithm.py:12-13` → .326); a debugging history (`test_website_build_integration.py:135-137`
  → .333); `test_print_log.py:306-313` claimed `set_level()` clamps (→ .289); `test_asy_isl29125_driver.py:1018` named
  index 4 wrongly (→ .062, D-T6); the errno helper's resync-warning premise (`test_uart_comm_hazard.py:553-555` → .318).
- Vacuous or wrong-reason passes, fixed: the rxbuf refusal asserted only `_init_errno != 0`, which the new idle default
  would satisfy through the timeout floor (→ .317); the byte-order check returned early without a CRC (→ .325, D-T32);
  an ISL29125 fault injected at a point that no longer exists (→ .063, D-T5); notification `FlashDur 0.01` writes that
  were refused as `Invalid` and never exercised the path (→ .089, D-T8).
- Restated product values in tests, replaced by source reads: `_MAX_OVERRIDE_TIME` (→ .090, D-T9), the UART blind-resync
  streak (→ .161, D-T15), ISL29125 register mirrors (→ .058, D-T4), the hazard file's seven errno copies (→ .318).
- Allocation and heap-rate budgets in L1 files carry no Part N row where no U8C action tags them (G4/R54) — left to the B2
  per-file pass (AC_NOTES 14); the UART hazard budgets are tagged (.316).
- 23 L1 files carry no header docstring at all (G9/R16: every file opens with exactly one header block) → each gets one,
  M.TEST_UNIT.334 (AC_NOTES 42 (1)).
- Every merged change re-read against CLAUDE.md's test rules: real Unix port only; no `gc.collect()` outside measurement
  baselines on A.U30.16's allow-list and no in-body `gc.threshold` (A.U30.12/.13); bounded fake pollers only; every
  `asyncio.run()` driver at synchronous scope (the shared `run()` refuses nesting); no brute-force host I/O; inline
  `method-assign` ignores only in tests; the four-tier bus-hazard rule for every bus-facing change (L1 here, L2-L4 carried
  to TWIN/HW_DEV/HW_BENCH); pinned behaviour retired with its guard named (.157, .250, .294, .313); no test skipped or
  disabled (the VOC whole-algorithm vectors are reported open, never skipped, if their source is unreachable — .328).

## Owner questions

None open. Both questions this merge raised are settled by AC_NOTES 42 (lead, 2026-10-01):
1. Header block on the 23 L1 files without one — settled by G9/R16 (every file opens with exactly one header block,
   every-file scope owner PQ6; the gate checks presence): M.TEST_UNIT.334.
2. `NotificationService`'s readiness gate — AC_NOTES 38's `_finalized` reading is void; per G5/R14 the class carries
   `self.initialized` and stays in A.U10.22's check: M.TEST_UNIT.293's row. Superseded in the A-C review fold by the
   routine settlement `initialized-flags` (AC_NOTES 52): no `initialized` on `NotificationService`; its row asserts the
   construction defaults only.

## Agent decisions for the OR2.c review

1. D-T1 — the lwIP host test (7) runs at the process's GC stage, no in-body threshold (M.TEST_UNIT.001).
2. D-T2 — BMP3XX bound tables derived from the source schema (M.TEST_UNIT.015).
3. D-T3 — no stored chip id: the observable effects (calibration, log, neighbour) are asserted (M.TEST_UNIT.008, .126).
4. D-T4 — ISL29125 register mirrors read with `src_const`, so A.U8C.10's mirror tags have no literal (M.TEST_UNIT.058).
5. D-T5 — the ISL29125 stored-state fault re-injected between read and store (M.TEST_UNIT.063).
6. D-T6 — the ISL29125 `:1018` comment names index 4 as the span (M.TEST_UNIT.062).
7. D-T7 — the notification minimum-sleep row in ms (M.TEST_UNIT.091; GAP-U9).
8. D-T8 — `FlashDur 0.01` writes dropped as refused input (M.TEST_UNIT.089).
9. D-T9 — `_MAX_OVERRIDE_TIME` read from source (M.TEST_UNIT.090).
10. D-T10 — the NTP builder empties `DNSFallback` by default; recorder tests pass `None` (M.TEST_UNIT.095).
11. D-T11 — the NTP lock-swallow test retires with `async with` (M.TEST_UNIT.110).
12. D-T12 — SGP40 self-test status is not stored: the reset that follows is asserted (M.TEST_UNIT.126).
13. D-T13 — SGP40 negative backup age per the A.U16.18 register reading (M.TEST_UNIT.138; GAP-U1).
14. D-T14 — UART range-sweep tests retire for the L0 catalog check; the floor moves to L0 (M.TEST_UNIT.157; GAP-U2).
15. D-T15 — the blind-resync streak read from source, not a tagged literal (M.TEST_UNIT.161).
16. D-T16 — `make_uart()` pins poll 1/1 rather than per-test re-checks after A.U13.17 (M.TEST_UNIT.170).
17. D-T17 — the UDP first-attempt row kept for its three surviving sites; the retry-cycle minimum derived (M.TEST_UNIT.187).
18. D-T18 — the base-class lock-serialise rewrite superseded by the attribute's deletion (M.TEST_UNIT.223).
19. D-T19 — per-topology recovery L1 in the generated bus-hazard file, split-session cases in the multi-device file
    (M.TEST_UNIT.232).
20. D-T20 — `_bad_ipv4_values()` stays in the captive-DNS test (four users) (M.TEST_UNIT.026, .241).
21. D-T21 — deferred work never outlives a `run()` call: write and flush in one coroutine (Conventions; config, FRAM,
    system tests).
22. D-T22 — three config-manager tests retire with A.U11.17's class; guard `tests_scripts/test_config_schemas.py`
    (M.TEST_UNIT.250).
23. D-T23 — L1s for the new `checked_int/float/numeric` API (M.TEST_UNIT.251).
24. D-T24 — the non-dict data test holds: the product keeps its `None` branch (M.TEST_UNIT.256).
25. D-T25 — A.S0930.22 (2) gates at the lock and logger, `open()` being synchronous (M.TEST_UNIT.259).
26. D-T26 — the no-autostart boot entry is executed too (M.TEST_UNIT.269).
27. D-T27 — print-log both-busy read answers `False` (blank or invalid, started fresh), not `None` (M.TEST_UNIT.291;
    corrected in the A-C review fold, routine settlement `unit-test-d-t27`).
28. D-T28 — the no-autostart entry is checked by `ast` for no `WDT` construction (M.TEST_UNIT.294).
29. D-T29 — a failing starter is persisted and printed (M.TEST_UNIT.304).
30. D-T30 — no UDP crossing tests: the UDP module keeps no tick site (M.TEST_UNIT.313).
31. D-T31 — the hazard cancel/clear sweep stays file-local; M.TEST_UNIT.166's per-path sweeps stay (M.TEST_UNIT.322).
32. D-T32 — the CRC byte-order check registered for CRC16 only (M.TEST_UNIT.325).
33. D-T33 — A.U12.13's uptime-limit L1 placed in `tests/test_voc_algorithm.py` (M.TEST_UNIT.329).
34. D-T34 — the bundle check reads the per-module separators (M.TEST_UNIT.333; GAP-U11).

## Ledger

Every action whose Site, Change or Blast names one of this cluster's 51 files (`site_index.json` plus the brief's grep),
and every action merged here from another cluster's blast, one row each. "blast-only, holds (read)" marks an action whose
text names the file only to state that it is unchanged; the M-ID is where that was re-checked.

| action ID | merged into M-ID / dropped (reason) |
|---|---|
| A.U0.07 | M.TEST_UNIT.064, M.TEST_UNIT.065, M.TEST_UNIT.071, M.TEST_UNIT.153, M.TEST_UNIT.231, M.TEST_UNIT.239, M.TEST_UNIT.249, M.TEST_UNIT.288, M.TEST_UNIT.315, M.TEST_UNIT.332 |
| A.U0.28 | M.TEST_UNIT.116, M.TEST_UNIT.126, M.TEST_UNIT.160, M.TEST_UNIT.207, M.TEST_UNIT.308 |
| A.U0.29 | M.TEST_UNIT.200 |
| A.U0.33 | blast-only, holds (read) at M.TEST_UNIT.233 |
| A.U0.35 | M.TEST_UNIT.004, M.TEST_UNIT.167, M.TEST_UNIT.200, M.TEST_UNIT.211, M.TEST_UNIT.219, M.TEST_UNIT.230, M.TEST_UNIT.296 |
| A.U0.38 | M.TEST_UNIT.040 |
| A.U0.39 | M.TEST_UNIT.251 |
| A.U0.40 | M.TEST_UNIT.049, M.TEST_UNIT.097, M.TEST_UNIT.315, M.TEST_UNIT.325 |
| A.U1.25 | M.TEST_UNIT.014, M.TEST_UNIT.167, M.TEST_UNIT.199 |
| A.U1.26 | M.TEST_UNIT.211 |
| A.U2.02 | M.TEST_UNIT.157 |
| A.U2.03 | M.TEST_UNIT.058, M.TEST_UNIT.153, M.TEST_UNIT.194 |
| A.U2.05 | M.TEST_UNIT.290 |
| A.U2.06 | M.TEST_UNIT.017, M.TEST_UNIT.061, M.TEST_UNIT.122, M.TEST_UNIT.125, M.TEST_UNIT.132, M.TEST_UNIT.147, M.TEST_UNIT.227, M.TEST_UNIT.279 |
| A.U2.07 | M.TEST_UNIT.024, M.TEST_UNIT.077, M.TEST_UNIT.249, M.TEST_UNIT.253, M.TEST_UNIT.256, M.TEST_UNIT.258, M.TEST_UNIT.298 |
| A.U2.08 | M.TEST_UNIT.284, M.TEST_UNIT.303, M.TEST_UNIT.308, M.TEST_UNIT.311 |
| A.U2.09 | M.TEST_UNIT.031, M.TEST_UNIT.032, M.TEST_UNIT.033, M.TEST_UNIT.034, M.TEST_UNIT.036, M.TEST_UNIT.037, M.TEST_UNIT.041, M.TEST_UNIT.042, M.TEST_UNIT.043, M.TEST_UNIT.044, M.TEST_UNIT.045, M.TEST_UNIT.046, M.TEST_UNIT.265 |
| A.U2.10 | M.TEST_UNIT.010, M.TEST_UNIT.014, M.TEST_UNIT.017, M.TEST_UNIT.021, M.TEST_UNIT.024 |
| A.U2.11 | M.TEST_UNIT.116, M.TEST_UNIT.119, M.TEST_UNIT.279, M.TEST_UNIT.298 |
| A.U2.12 | M.TEST_UNIT.060, M.TEST_UNIT.062, M.TEST_UNIT.065, M.TEST_UNIT.066, M.TEST_UNIT.067, M.TEST_UNIT.068, M.TEST_UNIT.069, M.TEST_UNIT.070, M.TEST_UNIT.071, M.TEST_UNIT.073, M.TEST_UNIT.077 |
| A.U2.13 | M.TEST_UNIT.130, M.TEST_UNIT.136, M.TEST_UNIT.138, M.TEST_UNIT.142, M.TEST_UNIT.144 |
| A.U2.14 | M.TEST_UNIT.217; holds (read) at M.TEST_UNIT.287 |
| A.U2.15 | M.TEST_UNIT.102, M.TEST_UNIT.103, M.TEST_UNIT.105, M.TEST_UNIT.109, M.TEST_UNIT.110, M.TEST_UNIT.111, M.TEST_UNIT.113, M.TEST_UNIT.287; holds (read) at M.TEST_UNIT.284 |
| A.U2.16 | M.TEST_UNIT.244, M.TEST_UNIT.246 |
| A.U2.17 | M.TEST_UNIT.083, M.TEST_UNIT.086, M.TEST_UNIT.087, M.TEST_UNIT.089, M.TEST_UNIT.092, M.TEST_UNIT.336 |
| A.U2.18 | M.TEST_UNIT.005 |
| A.U2.19 | M.TEST_UNIT.194, M.TEST_UNIT.202 |
| A.U2.20 | M.TEST_UNIT.153, M.TEST_UNIT.155, M.TEST_UNIT.156, M.TEST_UNIT.158, M.TEST_UNIT.161, M.TEST_UNIT.162, M.TEST_UNIT.163, M.TEST_UNIT.164, M.TEST_UNIT.167, M.TEST_UNIT.172, M.TEST_UNIT.317, M.TEST_UNIT.318, M.TEST_UNIT.319, M.TEST_UNIT.321; holds (read) at M.TEST_UNIT.183 |
| A.U3.01 | M.TEST_UNIT.036, M.TEST_UNIT.047, M.TEST_UNIT.066, M.TEST_UNIT.068, M.TEST_UNIT.070, M.TEST_UNIT.086, M.TEST_UNIT.092, M.TEST_UNIT.119, M.TEST_UNIT.156, M.TEST_UNIT.202, M.TEST_UNIT.290 |
| A.U3.02 | M.TEST_UNIT.047, M.TEST_UNIT.091, M.TEST_UNIT.110, M.TEST_UNIT.111, M.TEST_UNIT.113, M.TEST_UNIT.136, M.TEST_UNIT.156, M.TEST_UNIT.158, M.TEST_UNIT.164, M.TEST_UNIT.217 |
| A.U3.03 | M.TEST_UNIT.017, M.TEST_UNIT.061, M.TEST_UNIT.122, M.TEST_UNIT.132, M.TEST_UNIT.227, M.TEST_UNIT.279 |
| A.U3.04 | M.TEST_UNIT.041, M.TEST_UNIT.044, M.TEST_UNIT.046, M.TEST_UNIT.265 |
| A.U3.05 | M.TEST_UNIT.017, M.TEST_UNIT.024, M.TEST_UNIT.060, M.TEST_UNIT.063, M.TEST_UNIT.077, M.TEST_UNIT.086, M.TEST_UNIT.091, M.TEST_UNIT.113, M.TEST_UNIT.143, M.TEST_UNIT.218, M.TEST_UNIT.255 |
| A.U3.06 | M.TEST_UNIT.284, M.TEST_UNIT.308 |
| A.U3.07 | M.TEST_UNIT.218 |
| A.U3.08 | M.TEST_UNIT.159, M.TEST_UNIT.161, M.TEST_UNIT.164, M.TEST_UNIT.318 |
| A.U3.09 | M.TEST_UNIT.041, M.TEST_UNIT.135, M.TEST_UNIT.136, M.TEST_UNIT.138, M.TEST_UNIT.142 |
| A.U3.11 | M.TEST_UNIT.202 |
| A.U3.12 | M.TEST_UNIT.042, M.TEST_UNIT.087, M.TEST_UNIT.105, M.TEST_UNIT.202, M.TEST_UNIT.217, M.TEST_UNIT.244, M.TEST_UNIT.284, M.TEST_UNIT.287, M.TEST_UNIT.303 |
| A.U3.14 | M.TEST_UNIT.066 |
| A.U4.01 | M.TEST_UNIT.256, M.TEST_UNIT.258 |
| A.U4.02 | M.TEST_UNIT.005, M.TEST_UNIT.019, M.TEST_UNIT.070, M.TEST_UNIT.084, M.TEST_UNIT.258; holds (read) at M.TEST_UNIT.212, M.TEST_UNIT.230, M.TEST_UNIT.296 |
| A.U4.03 | M.TEST_UNIT.230 |
| A.U4.04 | M.TEST_UNIT.120, M.TEST_UNIT.121, M.TEST_UNIT.298 |
| A.U4.05 | M.TEST_UNIT.115 |
| A.U4.06 | M.TEST_UNIT.024, M.TEST_UNIT.120, M.TEST_UNIT.249 |
| A.U5.01 | M.TEST_UNIT.179, M.TEST_UNIT.292, M.TEST_UNIT.301 |
| A.U5.02 | M.TEST_UNIT.005, M.TEST_UNIT.014, M.TEST_UNIT.017, M.TEST_UNIT.029, M.TEST_UNIT.039, M.TEST_UNIT.050, M.TEST_UNIT.078, M.TEST_UNIT.079, M.TEST_UNIT.082, M.TEST_UNIT.085, M.TEST_UNIT.095, M.TEST_UNIT.096, M.TEST_UNIT.099, M.TEST_UNIT.114, M.TEST_UNIT.179, M.TEST_UNIT.196, M.TEST_UNIT.210, M.TEST_UNIT.226, M.TEST_UNIT.243, M.TEST_UNIT.265, M.TEST_UNIT.284, M.TEST_UNIT.301, M.TEST_UNIT.302, M.TEST_UNIT.336 |
| A.U5.04 | M.TEST_UNIT.196, M.TEST_UNIT.295, M.TEST_UNIT.332 |
| A.U5.05 | M.TEST_UNIT.196 |
| A.U5.06 | M.TEST_UNIT.082, M.TEST_UNIT.083, M.TEST_UNIT.084, M.TEST_UNIT.085, M.TEST_UNIT.088, M.TEST_UNIT.092, M.TEST_UNIT.094, M.TEST_UNIT.276, M.TEST_UNIT.278, M.TEST_UNIT.280, M.TEST_UNIT.281, M.TEST_UNIT.336 |
| A.U5.07 | M.TEST_UNIT.210, M.TEST_UNIT.213, M.TEST_UNIT.274 |
| A.U5.08 | M.TEST_UNIT.301, M.TEST_UNIT.311 |
| A.U5.09 | M.TEST_UNIT.210, M.TEST_UNIT.274, M.TEST_UNIT.282, M.TEST_UNIT.285, M.TEST_UNIT.295 |
| A.U5.10 | M.TEST_UNIT.095, M.TEST_UNIT.110, M.TEST_UNIT.113, M.TEST_UNIT.282, M.TEST_UNIT.285, M.TEST_UNIT.287, M.TEST_UNIT.295 |
| A.U5.11 | M.TEST_UNIT.082, M.TEST_UNIT.125, M.TEST_UNIT.130, M.TEST_UNIT.135, M.TEST_UNIT.147, M.TEST_UNIT.225, M.TEST_UNIT.276, M.TEST_UNIT.278, M.TEST_UNIT.280, M.TEST_UNIT.281, M.TEST_UNIT.284, M.TEST_UNIT.336 |
| A.U5.12 | M.TEST_UNIT.154, M.TEST_UNIT.165, M.TEST_UNIT.179, M.TEST_UNIT.317; holds (read) at M.TEST_UNIT.226 |
| A.U5.13 | blast-only, holds (`test_asy_fram_manager.py:2350-2389` reads `chunk.fram`, unchanged by the binding) |
| A.U5.14 | M.TEST_UNIT.057 |
| A.U5.15 | M.TEST_UNIT.095 |
| A.U6.04 | M.TEST_UNIT.333 |
| A.U6.29 | M.TEST_UNIT.212 |
| A.U6.30 | M.TEST_UNIT.212 |
| A.U8.02 | M.TEST_UNIT.236 |
| A.U8.04 | M.TEST_UNIT.196 |
| A.U8.06 | blast-only, holds (UART tunables: behaviour unchanged; the derived test sites are A.U8C2.51's Dependants) |
| A.U8.07 | M.TEST_UNIT.007, M.TEST_UNIT.022, M.TEST_UNIT.114, M.TEST_UNIT.145 |
| A.U8.08 | M.TEST_UNIT.305; holds (read) at M.TEST_UNIT.294 |
| A.U8.09 | M.TEST_UNIT.104 |
| A.U8.10 | M.TEST_UNIT.210, M.TEST_UNIT.214, M.TEST_UNIT.217 |
| A.U8.11 | M.TEST_UNIT.240; holds (read) at M.TEST_UNIT.187, M.TEST_UNIT.247 |
| A.U8.12 | blast-only, holds (read) at M.TEST_UNIT.309 |
| A.U8.13 | M.TEST_UNIT.137 |
| A.U8.14 | M.TEST_UNIT.323; holds (read) at M.TEST_UNIT.316; withdrawn at M.TEST_UNIT.207 |
| A.U8.17 | M.TEST_UNIT.194, M.TEST_UNIT.205, M.TEST_UNIT.282 |
| A.U8.23 | M.TEST_UNIT.194, M.TEST_UNIT.295, M.TEST_UNIT.332 |
| A.U8C.03 | M.TEST_UNIT.153, M.TEST_UNIT.178, M.TEST_UNIT.315 |
| A.U8C.05 | M.TEST_UNIT.019, M.TEST_UNIT.020 |
| A.U8C.06 | M.TEST_UNIT.028 |
| A.U8C.07 | M.TEST_UNIT.038 |
| A.U8C.08 | M.TEST_UNIT.044 |
| A.U8C.09 | M.TEST_UNIT.052, M.TEST_UNIT.168; holds (read) at M.TEST_UNIT.148 |
| A.U8C.10 | M.TEST_UNIT.058 |
| A.U8C.11 | M.TEST_UNIT.078 |
| A.U8C.12 | M.TEST_UNIT.082, M.TEST_UNIT.088, M.TEST_UNIT.091, M.TEST_UNIT.092, M.TEST_UNIT.276, M.TEST_UNIT.278, M.TEST_UNIT.280, M.TEST_UNIT.281; withdrawn at M.TEST_UNIT.090 |
| A.U8C.13 | M.TEST_UNIT.095, M.TEST_UNIT.099, M.TEST_UNIT.100, M.TEST_UNIT.103, M.TEST_UNIT.105, M.TEST_UNIT.106, M.TEST_UNIT.110, M.TEST_UNIT.113; withdrawn at M.TEST_UNIT.111 |
| A.U8C.14 | M.TEST_UNIT.118 |
| A.U8C.15 | M.TEST_UNIT.133 |
| A.U8C.16 | M.TEST_UNIT.148, M.TEST_UNIT.168 |
| A.U8C.17 | M.TEST_UNIT.153, M.TEST_UNIT.162 |
| A.U8C.18 | M.TEST_UNIT.168; holds (read) at M.TEST_UNIT.148; withdrawn at M.TEST_UNIT.171 |
| A.U8C.19 | M.TEST_UNIT.178; holds (read) at M.TEST_UNIT.153 |
| A.U8C.20 | M.TEST_UNIT.187, M.TEST_UNIT.190 |
| A.U8C.21 | M.TEST_UNIT.194 |
| A.U8C.22 | M.TEST_UNIT.220 |
| A.U8C.23 | M.TEST_UNIT.240 |
| A.U8C.34 | M.TEST_UNIT.267 |
| A.U8C.35 | M.TEST_UNIT.274 |
| A.U8C.36 | M.TEST_UNIT.276 |
| A.U8C.37 | M.TEST_UNIT.278 |
| A.U8C.38 | M.TEST_UNIT.280 |
| A.U8C.39 | M.TEST_UNIT.281 |
| A.U8C.40 | M.TEST_UNIT.282 |
| A.U8C.41 | M.TEST_UNIT.285 |
| A.U8C.42 | M.TEST_UNIT.305, M.TEST_UNIT.309 |
| A.U8C.43 | M.TEST_UNIT.316 |
| A.U8C.120 | blast-only, holds (read) at M.TEST_UNIT.187, M.TEST_UNIT.214, M.TEST_UNIT.240, M.TEST_UNIT.284; withdrawn at M.TEST_UNIT.090 |
| A.U8C2.02 | M.TEST_UNIT.090, M.TEST_UNIT.091 |
| A.U8C2.03 | M.TEST_UNIT.098, M.TEST_UNIT.103, M.TEST_UNIT.105, M.TEST_UNIT.106; withdrawn at M.TEST_UNIT.111 |
| A.U8C2.04 | M.TEST_UNIT.153, M.TEST_UNIT.162 |
| A.U8C2.05 | M.TEST_UNIT.194 |
| A.U8C2.06 | M.TEST_UNIT.220 |
| A.U8C2.07 | M.TEST_UNIT.240 |
| A.U8C2.13 | M.TEST_UNIT.282 |
| A.U8C2.14 | M.TEST_UNIT.285 |
| A.U8C2.15 | M.TEST_UNIT.316, M.TEST_UNIT.323 |
| A.U8C2.50 | M.TEST_UNIT.168, M.TEST_UNIT.170 |
| A.U8C2.51 | M.TEST_UNIT.309; holds (read) at M.TEST_UNIT.153, M.TEST_UNIT.168, M.TEST_UNIT.319 |
| A.U9.01 | M.TEST_UNIT.089 |
| A.U9.02 | M.TEST_UNIT.080, M.TEST_UNIT.277 |
| A.U9.04 | M.TEST_UNIT.080 |
| A.U9.05 | M.TEST_UNIT.080 |
| A.U9.06 | M.TEST_UNIT.081 |
| A.U9.07 | dropped (superseded by A.U17.27, M.SRC_SENS.021 Resolved) |
| A.U9.08 | M.TEST_UNIT.082, M.TEST_UNIT.087 |
| A.U9.09 | M.TEST_UNIT.090; holds (read) at M.TEST_UNIT.199 |
| A.U9.10 | M.TEST_UNIT.086, M.TEST_UNIT.274, M.TEST_UNIT.275, M.TEST_UNIT.277 |
| A.U10.01 | M.TEST_UNIT.224, M.TEST_UNIT.303 |
| A.U10.02 | M.TEST_UNIT.225 |
| A.U10.03 | M.TEST_UNIT.098, M.TEST_UNIT.099, M.TEST_UNIT.108, M.TEST_UNIT.211, M.TEST_UNIT.225, M.TEST_UNIT.308 |
| A.U10.04 | M.TEST_UNIT.156, M.TEST_UNIT.161 |
| A.U10.06 | M.TEST_UNIT.010, M.TEST_UNIT.017, M.TEST_UNIT.019, M.TEST_UNIT.022, M.TEST_UNIT.043, M.TEST_UNIT.061, M.TEST_UNIT.062, M.TEST_UNIT.091, M.TEST_UNIT.093, M.TEST_UNIT.097, M.TEST_UNIT.098, M.TEST_UNIT.105, M.TEST_UNIT.116, M.TEST_UNIT.122, M.TEST_UNIT.130, M.TEST_UNIT.131, M.TEST_UNIT.138, M.TEST_UNIT.215, M.TEST_UNIT.225, M.TEST_UNIT.278, M.TEST_UNIT.280, M.TEST_UNIT.281, M.TEST_UNIT.303; holds (read) at M.TEST_UNIT.283 |
| A.U10.08 | blast-only, holds (read) at M.TEST_UNIT.294 |
| A.U10.10 | M.TEST_UNIT.014, M.TEST_UNIT.017, M.TEST_UNIT.058, M.TEST_UNIT.060, M.TEST_UNIT.070, M.TEST_UNIT.077, M.TEST_UNIT.078, M.TEST_UNIT.079, M.TEST_UNIT.082, M.TEST_UNIT.085, M.TEST_UNIT.086, M.TEST_UNIT.095, M.TEST_UNIT.097, M.TEST_UNIT.102, M.TEST_UNIT.110, M.TEST_UNIT.113, M.TEST_UNIT.125, M.TEST_UNIT.147, M.TEST_UNIT.183, M.TEST_UNIT.211, M.TEST_UNIT.226, M.TEST_UNIT.229, M.TEST_UNIT.265, M.TEST_UNIT.276, M.TEST_UNIT.278, M.TEST_UNIT.280, M.TEST_UNIT.281, M.TEST_UNIT.282, M.TEST_UNIT.285, M.TEST_UNIT.295, M.TEST_UNIT.336 |
| A.U10.11 | M.TEST_UNIT.290 |
| A.U10.12 | M.TEST_UNIT.019, M.TEST_UNIT.072, M.TEST_UNIT.118, M.TEST_UNIT.133, M.TEST_UNIT.304 |
| A.U10.15 | M.TEST_UNIT.305, M.TEST_UNIT.307, M.TEST_UNIT.308 |
| A.U10.17 | M.TEST_UNIT.224 |
| A.U10.18 | M.TEST_UNIT.012, M.TEST_UNIT.016, M.TEST_UNIT.037, M.TEST_UNIT.038, M.TEST_UNIT.039, M.TEST_UNIT.052, M.TEST_UNIT.076, M.TEST_UNIT.079, M.TEST_UNIT.095, M.TEST_UNIT.109, M.TEST_UNIT.110, M.TEST_UNIT.148, M.TEST_UNIT.153, M.TEST_UNIT.166, M.TEST_UNIT.168, M.TEST_UNIT.214, M.TEST_UNIT.222, M.TEST_UNIT.233, M.TEST_UNIT.237, M.TEST_UNIT.249, M.TEST_UNIT.282, M.TEST_UNIT.285, M.TEST_UNIT.286, M.TEST_UNIT.295, M.TEST_UNIT.322; holds (read) at M.TEST_UNIT.218 |
| A.U10.20 | M.TEST_UNIT.213, M.TEST_UNIT.257 |
| A.U10.21 | M.TEST_UNIT.008, M.TEST_UNIT.030, M.TEST_UNIT.054, M.TEST_UNIT.293; holds (read) at M.TEST_UNIT.290 |
| A.U10.22 | M.TEST_UNIT.293 |
| A.U10.23 | M.TEST_UNIT.309 |
| A.U10.25 | M.TEST_UNIT.134, M.TEST_UNIT.212 |
| A.U10.26 | M.TEST_UNIT.034, M.TEST_UNIT.189 |
| A.U10.27 | M.TEST_UNIT.206; holds (read) at M.TEST_UNIT.300 |
| A.U10.28 | M.TEST_UNIT.043, M.TEST_UNIT.089, M.TEST_UNIT.138, M.TEST_UNIT.225 |
| A.U10.29 | M.TEST_UNIT.168, M.TEST_UNIT.282, M.TEST_UNIT.285; holds (read) at M.TEST_UNIT.025, M.TEST_UNIT.267 |
| A.U10.30 | M.TEST_UNIT.064 |
| A.U10.35 | M.TEST_UNIT.011, M.TEST_UNIT.012, M.TEST_UNIT.014, M.TEST_UNIT.016, M.TEST_UNIT.019, M.TEST_UNIT.020, M.TEST_UNIT.039, M.TEST_UNIT.043, M.TEST_UNIT.058, M.TEST_UNIT.059, M.TEST_UNIT.061, M.TEST_UNIT.065, M.TEST_UNIT.067, M.TEST_UNIT.068, M.TEST_UNIT.069, M.TEST_UNIT.071, M.TEST_UNIT.072, M.TEST_UNIT.073, M.TEST_UNIT.074, M.TEST_UNIT.076, M.TEST_UNIT.078, M.TEST_UNIT.079, M.TEST_UNIT.099, M.TEST_UNIT.100, M.TEST_UNIT.105, M.TEST_UNIT.106, M.TEST_UNIT.108, M.TEST_UNIT.110, M.TEST_UNIT.111, M.TEST_UNIT.114, M.TEST_UNIT.118, M.TEST_UNIT.121, M.TEST_UNIT.122, M.TEST_UNIT.125, M.TEST_UNIT.131, M.TEST_UNIT.135, M.TEST_UNIT.148, M.TEST_UNIT.154, M.TEST_UNIT.164, M.TEST_UNIT.179, M.TEST_UNIT.186, M.TEST_UNIT.210, M.TEST_UNIT.239, M.TEST_UNIT.249, M.TEST_UNIT.258, M.TEST_UNIT.260, M.TEST_UNIT.274, M.TEST_UNIT.276, M.TEST_UNIT.278, M.TEST_UNIT.280, M.TEST_UNIT.281, M.TEST_UNIT.282, M.TEST_UNIT.285, M.TEST_UNIT.288, M.TEST_UNIT.296, M.TEST_UNIT.298, M.TEST_UNIT.299, M.TEST_UNIT.301, M.TEST_UNIT.302, M.TEST_UNIT.307 |
| A.U10.36 | M.TEST_UNIT.195, M.TEST_UNIT.311 |
| A.U10.37 | M.TEST_UNIT.002, M.TEST_UNIT.007, M.TEST_UNIT.029, M.TEST_UNIT.030, M.TEST_UNIT.039, M.TEST_UNIT.050, M.TEST_UNIT.058, M.TEST_UNIT.078, M.TEST_UNIT.082, M.TEST_UNIT.085, M.TEST_UNIT.095, M.TEST_UNIT.114, M.TEST_UNIT.121, M.TEST_UNIT.153, M.TEST_UNIT.168, M.TEST_UNIT.178, M.TEST_UNIT.194, M.TEST_UNIT.210, M.TEST_UNIT.222, M.TEST_UNIT.239, M.TEST_UNIT.249, M.TEST_UNIT.260, M.TEST_UNIT.265, M.TEST_UNIT.267, M.TEST_UNIT.276, M.TEST_UNIT.278, M.TEST_UNIT.280, M.TEST_UNIT.281, M.TEST_UNIT.282, M.TEST_UNIT.285, M.TEST_UNIT.288, M.TEST_UNIT.294, M.TEST_UNIT.295, M.TEST_UNIT.301, M.TEST_UNIT.315, M.TEST_UNIT.326, M.TEST_UNIT.336 |
| A.U10.38 | M.TEST_UNIT.007, M.TEST_UNIT.025, M.TEST_UNIT.029, M.TEST_UNIT.039, M.TEST_UNIT.050, M.TEST_UNIT.078, M.TEST_UNIT.082, M.TEST_UNIT.095, M.TEST_UNIT.096, M.TEST_UNIT.102, M.TEST_UNIT.103, M.TEST_UNIT.153, M.TEST_UNIT.168, M.TEST_UNIT.178, M.TEST_UNIT.179, M.TEST_UNIT.186, M.TEST_UNIT.194, M.TEST_UNIT.210, M.TEST_UNIT.220, M.TEST_UNIT.222, M.TEST_UNIT.239, M.TEST_UNIT.260, M.TEST_UNIT.265, M.TEST_UNIT.267, M.TEST_UNIT.274, M.TEST_UNIT.276, M.TEST_UNIT.278, M.TEST_UNIT.280, M.TEST_UNIT.281, M.TEST_UNIT.282, M.TEST_UNIT.285, M.TEST_UNIT.288, M.TEST_UNIT.295, M.TEST_UNIT.301, M.TEST_UNIT.315, M.TEST_UNIT.326, M.TEST_UNIT.336 |
| A.U10.39 | M.TEST_UNIT.015, M.TEST_UNIT.112, M.TEST_UNIT.210, M.TEST_UNIT.212, M.TEST_UNIT.229 |
| A.U10.40 | M.TEST_UNIT.014, M.TEST_UNIT.015, M.TEST_UNIT.016, M.TEST_UNIT.019, M.TEST_UNIT.067, M.TEST_UNIT.068, M.TEST_UNIT.070, M.TEST_UNIT.083, M.TEST_UNIT.084, M.TEST_UNIT.088, M.TEST_UNIT.089, M.TEST_UNIT.096, M.TEST_UNIT.097, M.TEST_UNIT.101, M.TEST_UNIT.106, M.TEST_UNIT.107, M.TEST_UNIT.112, M.TEST_UNIT.120, M.TEST_UNIT.121, M.TEST_UNIT.125, M.TEST_UNIT.134, M.TEST_UNIT.140, M.TEST_UNIT.195, M.TEST_UNIT.197, M.TEST_UNIT.199, M.TEST_UNIT.210, M.TEST_UNIT.276, M.TEST_UNIT.278, M.TEST_UNIT.280, M.TEST_UNIT.281, M.TEST_UNIT.282, M.TEST_UNIT.285, M.TEST_UNIT.296, M.TEST_UNIT.298, M.TEST_UNIT.299 |
| A.U10.41 | M.TEST_UNIT.027, M.TEST_UNIT.028, M.TEST_UNIT.095, M.TEST_UNIT.101, M.TEST_UNIT.112, M.TEST_UNIT.206 |
| A.U10.43 | M.TEST_UNIT.014, M.TEST_UNIT.068, M.TEST_UNIT.070, M.TEST_UNIT.072, M.TEST_UNIT.114, M.TEST_UNIT.118, M.TEST_UNIT.278, M.TEST_UNIT.280, M.TEST_UNIT.284, M.TEST_UNIT.298 |
| A.U10.44 | M.TEST_UNIT.019, M.TEST_UNIT.020, M.TEST_UNIT.022, M.TEST_UNIT.061, M.TEST_UNIT.072, M.TEST_UNIT.088, M.TEST_UNIT.090, M.TEST_UNIT.092, M.TEST_UNIT.094, M.TEST_UNIT.096, M.TEST_UNIT.099, M.TEST_UNIT.102, M.TEST_UNIT.105, M.TEST_UNIT.106, M.TEST_UNIT.108, M.TEST_UNIT.109, M.TEST_UNIT.110, M.TEST_UNIT.111, M.TEST_UNIT.118, M.TEST_UNIT.122, M.TEST_UNIT.141, M.TEST_UNIT.159, M.TEST_UNIT.179, M.TEST_UNIT.204, M.TEST_UNIT.211, M.TEST_UNIT.274, M.TEST_UNIT.276, M.TEST_UNIT.284, M.TEST_UNIT.285, M.TEST_UNIT.322, M.TEST_UNIT.228 |
| A.U10.45 | M.TEST_UNIT.054, M.TEST_UNIT.126; holds (read) at M.TEST_UNIT.123 |
| A.U10.R01 | M.TEST_UNIT.015, M.TEST_UNIT.017, M.TEST_UNIT.022, M.TEST_UNIT.060, M.TEST_UNIT.061, M.TEST_UNIT.122, M.TEST_UNIT.132, M.TEST_UNIT.143, M.TEST_UNIT.218, M.TEST_UNIT.227; holds (read) at M.TEST_UNIT.279, M.TEST_UNIT.281 |
| A.U11.01 | M.TEST_UNIT.284, M.TEST_UNIT.301, M.TEST_UNIT.303 |
| A.U11.02 | M.TEST_UNIT.303 |
| A.U11.03 | M.TEST_UNIT.301, M.TEST_UNIT.305, M.TEST_UNIT.309 |
| A.U11.04 | M.TEST_UNIT.259 |
| A.U11.05 | blast-only, holds (read) at M.TEST_UNIT.200, M.TEST_UNIT.301 |
| A.U11.07 | M.TEST_UNIT.305, M.TEST_UNIT.310 |
| A.U11.09 | M.TEST_UNIT.291 |
| A.U11.10 | M.TEST_UNIT.309 |
| A.U11.12 | M.TEST_UNIT.311 |
| A.U11.13 | M.TEST_UNIT.226, M.TEST_UNIT.243, M.TEST_UNIT.289, M.TEST_UNIT.312 |
| A.U11.15 | M.TEST_UNIT.096, M.TEST_UNIT.099, M.TEST_UNIT.211, M.TEST_UNIT.226, M.TEST_UNIT.243, M.TEST_UNIT.289, M.TEST_UNIT.302, M.TEST_UNIT.312 |
| A.U11.16 | M.TEST_UNIT.288, M.TEST_UNIT.291 |
| A.U11.17 | M.TEST_UNIT.250, M.TEST_UNIT.255; holds (read) at M.TEST_UNIT.229 |
| A.U11.18 | M.TEST_UNIT.250 |
| A.U11.19 | M.TEST_UNIT.229, M.TEST_UNIT.230, M.TEST_UNIT.249, M.TEST_UNIT.253, M.TEST_UNIT.257, M.TEST_UNIT.258 |
| A.U11.20 | M.TEST_UNIT.254 |
| A.U11.21 | M.TEST_UNIT.256 |
| A.U11.22 | M.TEST_UNIT.257 |
| A.U11.23 | M.TEST_UNIT.257, M.TEST_UNIT.258 |
| A.U11.24 | M.TEST_UNIT.014, M.TEST_UNIT.015, M.TEST_UNIT.063, M.TEST_UNIT.084, M.TEST_UNIT.112, M.TEST_UNIT.138, M.TEST_UNIT.140, M.TEST_UNIT.212, M.TEST_UNIT.229, M.TEST_UNIT.256; holds (read) at M.TEST_UNIT.296, M.TEST_UNIT.311 |
| A.U11.25 | M.TEST_UNIT.256 |
| A.U11.26 | M.TEST_UNIT.003, M.TEST_UNIT.004, M.TEST_UNIT.005, M.TEST_UNIT.197 |
| A.U11.27 | M.TEST_UNIT.230 |
| A.U11.28 | M.TEST_UNIT.230, M.TEST_UNIT.257; holds (read) at M.TEST_UNIT.258 |
| A.U11.29 | M.TEST_UNIT.255 |
| A.U11.31 | M.TEST_UNIT.195, M.TEST_UNIT.200, M.TEST_UNIT.227, M.TEST_UNIT.243, M.TEST_UNIT.290, M.TEST_UNIT.291, M.TEST_UNIT.308 |
| A.U11.32 | M.TEST_UNIT.250; holds (read) at M.TEST_UNIT.311 |
| A.U11.39 | blast-only, holds (read) at M.TEST_UNIT.304 |
| A.U11.S01 | blast-only, holds (read) at M.TEST_UNIT.251, M.TEST_UNIT.252, M.TEST_UNIT.298 |
| A.U11.S02 | blast-only, holds (read) at M.TEST_UNIT.005, M.TEST_UNIT.179, M.TEST_UNIT.200, M.TEST_UNIT.226, M.TEST_UNIT.243 |
| A.U11.S03 | M.TEST_UNIT.079, M.TEST_UNIT.085, M.TEST_UNIT.288, M.TEST_UNIT.289; holds (read) at M.TEST_UNIT.179, M.TEST_UNIT.195, M.TEST_UNIT.222 |
| A.U12.01 | M.TEST_UNIT.261 |
| A.U12.02 | M.TEST_UNIT.174, M.TEST_UNIT.262 |
| A.U12.03 | M.TEST_UNIT.174 |
| A.U12.04 | M.TEST_UNIT.261, M.TEST_UNIT.263 |
| A.U12.05 | blast-only, holds (read) at M.TEST_UNIT.267 |
| A.U12.06 | M.TEST_UNIT.270 |
| A.U12.07 | M.TEST_UNIT.272 |
| A.U12.08 | M.TEST_UNIT.017, M.TEST_UNIT.271 |
| A.U12.09 | M.TEST_UNIT.271 |
| A.U12.11 | M.TEST_UNIT.327 |
| A.U12.12 | M.TEST_UNIT.328, M.TEST_UNIT.331 |
| A.U12.13 | M.TEST_UNIT.329 |
| A.U12.14 | M.TEST_UNIT.144, M.TEST_UNIT.329 |
| A.U12.16 | M.TEST_UNIT.267 |
| A.U12.17 | M.TEST_UNIT.268 |
| A.U12.18 | M.TEST_UNIT.129, M.TEST_UNIT.142; holds (read) at M.TEST_UNIT.234 |
| A.U13.01 | blast-only, holds (read) at M.TEST_UNIT.055 |
| A.U13.03 | M.TEST_UNIT.033, M.TEST_UNIT.151 |
| A.U13.05 | blast-only, holds (`test_asy_fram_wire_trace.py:3-5, 107-109` one `init` per CS cycle, unchanged) |
| A.U13.07 | M.TEST_UNIT.013, M.TEST_UNIT.053; holds (read) at M.TEST_UNIT.234 |
| A.U13.08 | M.TEST_UNIT.035, M.TEST_UNIT.044, M.TEST_UNIT.149, M.TEST_UNIT.151; holds (read) at M.TEST_UNIT.050 |
| A.U13.09 | M.TEST_UNIT.009, M.TEST_UNIT.010, M.TEST_UNIT.035, M.TEST_UNIT.059, M.TEST_UNIT.116, M.TEST_UNIT.127, M.TEST_UNIT.129; holds (read) at M.TEST_UNIT.018, M.TEST_UNIT.234 |
| A.U13.10 | M.TEST_UNIT.010, M.TEST_UNIT.055, M.TEST_UNIT.059, M.TEST_UNIT.074; holds (read) at M.TEST_UNIT.018, M.TEST_UNIT.234 |
| A.U13.12 | M.TEST_UNIT.175 |
| A.U13.13 | M.TEST_UNIT.173; holds (read) at M.TEST_UNIT.317 |
| A.U13.14 | M.TEST_UNIT.176 |
| A.U13.16 | M.TEST_UNIT.053, M.TEST_UNIT.149 |
| A.U13.17 | M.TEST_UNIT.154, M.TEST_UNIT.170, M.TEST_UNIT.178, M.TEST_UNIT.315, M.TEST_UNIT.317 |
| A.U13.18 | M.TEST_UNIT.176 |
| A.U13.19 | M.TEST_UNIT.176 |
| A.U13.R01 | M.TEST_UNIT.056 |
| A.U13.R02 | M.TEST_UNIT.232, M.TEST_UNIT.238 |
| A.U14.03 | M.TEST_UNIT.202 |
| A.U14.10 | M.TEST_UNIT.081 |
| A.U14.11 | M.TEST_UNIT.253 |
| A.U14.17 | M.TEST_UNIT.056 |
| A.U14.18 | M.TEST_UNIT.326 |
| A.U14.19 | M.TEST_UNIT.291 |
| A.U14.26 | M.TEST_UNIT.043, M.TEST_UNIT.093, M.TEST_UNIT.098, M.TEST_UNIT.104, M.TEST_UNIT.107, M.TEST_UNIT.215; holds (read) at M.TEST_UNIT.303 |
| A.U14.28 | M.TEST_UNIT.072, M.TEST_UNIT.103, M.TEST_UNIT.107; holds (read) at M.TEST_UNIT.313 |
| A.U14.31 | blast-only, holds (read) at M.TEST_UNIT.173 |
| A.U14.32 | M.TEST_UNIT.313 |
| A.U14.33 | M.TEST_UNIT.313 |
| A.U14.34 | M.TEST_UNIT.059, M.TEST_UNIT.160, M.TEST_UNIT.314; holds (read) at M.TEST_UNIT.093 |
| A.U15.01 | M.TEST_UNIT.116, M.TEST_UNIT.117, M.TEST_UNIT.124; holds (read) at M.TEST_UNIT.115, M.TEST_UNIT.234, M.TEST_UNIT.278, M.TEST_UNIT.280 |
| A.U15.03 | M.TEST_UNIT.118 |
| A.U15.07 | M.TEST_UNIT.115 |
| A.U15.09 | M.TEST_UNIT.120 |
| A.U15.12 | M.TEST_UNIT.114, M.TEST_UNIT.120, M.TEST_UNIT.121, M.TEST_UNIT.122, M.TEST_UNIT.278, M.TEST_UNIT.280, M.TEST_UNIT.284, M.TEST_UNIT.298; holds (read) at M.TEST_UNIT.234 |
| A.U15.13 | M.TEST_UNIT.126, M.TEST_UNIT.129, M.TEST_UNIT.145; holds (read) at M.TEST_UNIT.234 |
| A.U15.14 | M.TEST_UNIT.128, M.TEST_UNIT.130, M.TEST_UNIT.135 |
| A.U15.15 | M.TEST_UNIT.127, M.TEST_UNIT.233, M.TEST_UNIT.235 |
| A.U15.16 | blast-only, holds (the SGP40 skip tests hold; value-wiring stays required) |
| A.U15.17 | M.TEST_UNIT.131, M.TEST_UNIT.136, M.TEST_UNIT.137, M.TEST_UNIT.138, M.TEST_UNIT.140, M.TEST_UNIT.143 |
| A.U15.18 | M.TEST_UNIT.136 |
| A.U15.19 | M.TEST_UNIT.125, M.TEST_UNIT.130, M.TEST_UNIT.139; holds (read) at M.TEST_UNIT.280, M.TEST_UNIT.281 |
| A.U15.20 | M.TEST_UNIT.133 |
| A.U15.21 | M.TEST_UNIT.134 |
| A.U15.22 | M.TEST_UNIT.017, M.TEST_UNIT.062, M.TEST_UNIT.063, M.TEST_UNIT.064, M.TEST_UNIT.116, M.TEST_UNIT.122 |
| A.U15.23 | M.TEST_UNIT.015 |
| A.U15.24 | M.TEST_UNIT.017 |
| A.U15.25 | M.TEST_UNIT.008, M.TEST_UNIT.010, M.TEST_UNIT.234; holds (read) at M.TEST_UNIT.231 |
| A.U15.26 | M.TEST_UNIT.014 |
| A.U15.27 | M.TEST_UNIT.011, M.TEST_UNIT.023 |
| A.U15.28 | M.TEST_UNIT.058, M.TEST_UNIT.114, M.TEST_UNIT.233 |
| A.U15.29 | M.TEST_UNIT.062, M.TEST_UNIT.069 |
| A.U15.30 | M.TEST_UNIT.059 |
| A.U15.31 | M.TEST_UNIT.069 |
| A.U15.32 | M.TEST_UNIT.065; holds (read) at M.TEST_UNIT.234 |
| A.U15.33 | M.TEST_UNIT.068, M.TEST_UNIT.076; holds (read) at M.TEST_UNIT.234 |
| A.U15.34 | M.TEST_UNIT.060 |
| A.U15.35 | M.TEST_UNIT.059, M.TEST_UNIT.065, M.TEST_UNIT.071 |
| A.U15.36 | M.TEST_UNIT.062, M.TEST_UNIT.072 |
| A.U15.38 | M.TEST_UNIT.070, M.TEST_UNIT.075 |
| A.U15.40 | M.TEST_UNIT.012, M.TEST_UNIT.020, M.TEST_UNIT.072, M.TEST_UNIT.125, M.TEST_UNIT.228 |
| A.U15.41 | M.TEST_UNIT.019, M.TEST_UNIT.072, M.TEST_UNIT.118, M.TEST_UNIT.133, M.TEST_UNIT.143, M.TEST_UNIT.228 |
| A.U15.43 | M.TEST_UNIT.022, M.TEST_UNIT.061, M.TEST_UNIT.122, M.TEST_UNIT.141 |
| A.U15.R01 | M.TEST_UNIT.122, M.TEST_UNIT.238; holds (read) at M.TEST_UNIT.279 |
| A.U15.R02 | M.TEST_UNIT.132, M.TEST_UNIT.143, M.TEST_UNIT.146, M.TEST_UNIT.238 |
| A.U15.R03 | M.TEST_UNIT.015, M.TEST_UNIT.017; holds (read) at M.TEST_UNIT.009 |
| A.U15.R04 | M.TEST_UNIT.060, M.TEST_UNIT.061, M.TEST_UNIT.066, M.TEST_UNIT.238 |
| A.U15.R05 | M.TEST_UNIT.065 |
| A.U15.S01 | M.TEST_UNIT.059, M.TEST_UNIT.076; holds (read) at M.TEST_UNIT.234 |
| A.U16.01 | M.TEST_UNIT.040 |
| A.U16.04 | M.TEST_UNIT.035 |
| A.U16.05 | M.TEST_UNIT.039, M.TEST_UNIT.153, M.TEST_UNIT.158, M.TEST_UNIT.222, M.TEST_UNIT.223, M.TEST_UNIT.260, M.TEST_UNIT.267, M.TEST_UNIT.288; holds (read) at M.TEST_UNIT.029 |
| A.U16.06 | M.TEST_UNIT.041, M.TEST_UNIT.045, M.TEST_UNIT.291; holds (read) at M.TEST_UNIT.050 |
| A.U16.08 | M.TEST_UNIT.041 |
| A.U16.09 | M.TEST_UNIT.029, M.TEST_UNIT.041, M.TEST_UNIT.049, M.TEST_UNIT.050 |
| A.U16.10 | M.TEST_UNIT.033 |
| A.U16.11 | M.TEST_UNIT.051 |
| A.U16.12 | M.TEST_UNIT.049, M.TEST_UNIT.050 |
| A.U16.13 | M.TEST_UNIT.040 |
| A.U16.14 | M.TEST_UNIT.266 |
| A.U16.15 | M.TEST_UNIT.031 |
| A.U16.16 | blast-only, holds (read) at M.TEST_UNIT.033 |
| A.U16.17 | M.TEST_UNIT.048 |
| A.U16.18 | M.TEST_UNIT.043, M.TEST_UNIT.050, M.TEST_UNIT.136, M.TEST_UNIT.138, M.TEST_UNIT.265, M.TEST_UNIT.283 |
| A.U16.19 | M.TEST_UNIT.042, M.TEST_UNIT.079, M.TEST_UNIT.085, M.TEST_UNIT.183, M.TEST_UNIT.222, M.TEST_UNIT.288 |
| A.U16.21 | M.TEST_UNIT.050 |
| A.U16.22 | M.TEST_UNIT.045; holds (read) at M.TEST_UNIT.030, M.TEST_UNIT.042 |
| A.U16.23 | M.TEST_UNIT.045 |
| A.U16.R01 | M.TEST_UNIT.032; holds (read) at M.TEST_UNIT.050 |
| A.U16.R02 | M.TEST_UNIT.031; holds (read) at M.TEST_UNIT.050 |
| A.U16.R03 | M.TEST_UNIT.032, M.TEST_UNIT.034, M.TEST_UNIT.048; holds (read) at M.TEST_UNIT.291 |
| A.U16.S01 | blast-only, holds (typing of the FRAM manager tests unchanged) |
| A.U17.01 | M.TEST_UNIT.163 |
| A.U17.02 | M.TEST_UNIT.163 |
| A.U17.05 | M.TEST_UNIT.323 |
| A.U17.06 | M.TEST_UNIT.160 |
| A.U17.07 | M.TEST_UNIT.182 |
| A.U17.12 | blast-only, holds (read) at M.TEST_UNIT.160, M.TEST_UNIT.320 |
| A.U17.13 | M.TEST_UNIT.156, M.TEST_UNIT.176, M.TEST_UNIT.319 |
| A.U17.14 | M.TEST_UNIT.156, M.TEST_UNIT.161 |
| A.U17.15 | blast-only, holds (read) at M.TEST_UNIT.319 |
| A.U17.16 | M.TEST_UNIT.320; holds (read) at M.TEST_UNIT.160 |
| A.U17.17 | M.TEST_UNIT.159 |
| A.U17.18 | blast-only, holds (`.uart` attribute reads stay) |
| A.U17.19 | M.TEST_UNIT.180 |
| A.U17.20 | M.TEST_UNIT.155, M.TEST_UNIT.159; holds (read) at M.TEST_UNIT.178 |
| A.U17.22 | M.TEST_UNIT.155, M.TEST_UNIT.176, M.TEST_UNIT.268 |
| A.U17.23 | M.TEST_UNIT.322 |
| A.U17.24 | M.TEST_UNIT.320, M.TEST_UNIT.321 |
| A.U17.25 | M.TEST_UNIT.322 |
| A.U17.27 | M.TEST_UNIT.078, M.TEST_UNIT.274, M.TEST_UNIT.276, M.TEST_UNIT.278, M.TEST_UNIT.280, M.TEST_UNIT.281 |
| A.U17.28 | M.TEST_UNIT.172 |
| A.U17.29 | M.TEST_UNIT.180 |
| A.U18.01 | M.TEST_UNIT.219, M.TEST_UNIT.242 |
| A.U18.02 | M.TEST_UNIT.242 |
| A.U18.03 | M.TEST_UNIT.244 |
| A.U18.04 | blast-only, holds (read) at M.TEST_UNIT.244 |
| A.U18.05 | M.TEST_UNIT.187, M.TEST_UNIT.189, M.TEST_UNIT.220 |
| A.U18.06 | M.TEST_UNIT.244, M.TEST_UNIT.245, M.TEST_UNIT.247 |
| A.U18.07 | M.TEST_UNIT.246 |
| A.U18.08 | M.TEST_UNIT.026, M.TEST_UNIT.241, M.TEST_UNIT.285 |
| A.U18.09 | M.TEST_UNIT.027, M.TEST_UNIT.028 |
| A.U18.10 | M.TEST_UNIT.025, M.TEST_UNIT.028, M.TEST_UNIT.095, M.TEST_UNIT.096, M.TEST_UNIT.097, M.TEST_UNIT.101, M.TEST_UNIT.102, M.TEST_UNIT.109, M.TEST_UNIT.112, M.TEST_UNIT.282, M.TEST_UNIT.285, M.TEST_UNIT.286, M.TEST_UNIT.287, M.TEST_UNIT.295 |
| A.U18.11 | M.TEST_UNIT.025, M.TEST_UNIT.095, M.TEST_UNIT.111, M.TEST_UNIT.282, M.TEST_UNIT.285 |
| A.U18.12 | M.TEST_UNIT.025, M.TEST_UNIT.095, M.TEST_UNIT.111, M.TEST_UNIT.186, M.TEST_UNIT.220, M.TEST_UNIT.239, M.TEST_UNIT.282, M.TEST_UNIT.285 |
| A.U18.13 | M.TEST_UNIT.025, M.TEST_UNIT.103, M.TEST_UNIT.111, M.TEST_UNIT.187, M.TEST_UNIT.188, M.TEST_UNIT.190, M.TEST_UNIT.282, M.TEST_UNIT.285 |
| A.U18.14 | M.TEST_UNIT.103, M.TEST_UNIT.191 |
| A.U18.15 | M.TEST_UNIT.025, M.TEST_UNIT.028, M.TEST_UNIT.102, M.TEST_UNIT.103, M.TEST_UNIT.246, M.TEST_UNIT.286; holds (read) at M.TEST_UNIT.239 |
| A.U18.16 | M.TEST_UNIT.103; holds (read) at M.TEST_UNIT.191 |
| A.U18.17 | M.TEST_UNIT.189 |
| A.U18.20 | M.TEST_UNIT.106 |
| A.U18.21 | M.TEST_UNIT.097, M.TEST_UNIT.100, M.TEST_UNIT.111 |
| A.U18.23 | M.TEST_UNIT.099 |
| A.U18.24 | M.TEST_UNIT.211, M.TEST_UNIT.216 |
| A.U18.25 | M.TEST_UNIT.107 |
| A.U18.26 | M.TEST_UNIT.107 |
| A.U18.27 | M.TEST_UNIT.215, M.TEST_UNIT.217 |
| A.U18.28 | M.TEST_UNIT.216 |
| A.U18.29 | M.TEST_UNIT.216 |
| A.U18.30 | M.TEST_UNIT.213 |
| A.U18.31 | M.TEST_UNIT.213 |
| A.U18.32 | M.TEST_UNIT.214, M.TEST_UNIT.219 |
| A.U18.33 | M.TEST_UNIT.215, M.TEST_UNIT.282, M.TEST_UNIT.286; holds (read) at M.TEST_UNIT.102 |
| A.U18.34 | M.TEST_UNIT.286 |
| A.U18.36 | M.TEST_UNIT.217, M.TEST_UNIT.219 |
| A.U18.37 | M.TEST_UNIT.212 |
| A.U18.38 | M.TEST_UNIT.295 |
| A.U18.39 | M.TEST_UNIT.212 |
| A.U18.40 | M.TEST_UNIT.210, M.TEST_UNIT.213, M.TEST_UNIT.274, M.TEST_UNIT.282, M.TEST_UNIT.285, M.TEST_UNIT.295 |
| A.U18.41 | M.TEST_UNIT.212 |
| A.U18.42 | M.TEST_UNIT.215 |
| A.U18.43 | blast-only, holds (read) at M.TEST_UNIT.216 |
| A.U18.45 | M.TEST_UNIT.025, M.TEST_UNIT.028 |
| A.U18.46 | M.TEST_UNIT.192 |
| A.U18.R01 | M.TEST_UNIT.218 |
| A.U19.01 | M.TEST_UNIT.197, M.TEST_UNIT.296 |
| A.U19.02 | M.TEST_UNIT.199, M.TEST_UNIT.251 |
| A.U19.03 | M.TEST_UNIT.199 |
| A.U19.04 | M.TEST_UNIT.198 |
| A.U19.05 | M.TEST_UNIT.195, M.TEST_UNIT.206, M.TEST_UNIT.332 |
| A.U19.06 | M.TEST_UNIT.196, M.TEST_UNIT.202, M.TEST_UNIT.332; holds (read) at M.TEST_UNIT.297 |
| A.U19.07 | M.TEST_UNIT.203; holds (read) at M.TEST_UNIT.195 |
| A.U19.08 | M.TEST_UNIT.202 |
| A.U19.09 | M.TEST_UNIT.204 |
| A.U19.11 | M.TEST_UNIT.206 |
| A.U19.12 | M.TEST_UNIT.201; holds (read) at M.TEST_UNIT.230 |
| A.U19.15 | M.TEST_UNIT.003, M.TEST_UNIT.206, M.TEST_UNIT.296; holds (read) at M.TEST_UNIT.230 |
| A.U19.16 | M.TEST_UNIT.070, M.TEST_UNIT.084 |
| A.U19.17 | blast-only, holds (read) at M.TEST_UNIT.194 |
| A.U19.20 | M.TEST_UNIT.207 |
| A.U19.23 | M.TEST_UNIT.208 |
| A.U19.24 | M.TEST_UNIT.208 |
| A.U20.02 | blast-only, holds (read) at M.TEST_UNIT.294 |
| A.U20.06 | M.TEST_UNIT.090, M.TEST_UNIT.284, M.TEST_UNIT.309; holds (read) at M.TEST_UNIT.216 |
| A.U20.08 | blast-only, holds (names `test_asy_i2c_driver.py` as an unchanged reader) |
| A.U20.10 | blast-only, holds (grep "tell which" in `test_asy_fram_driver.py`: none) |
| A.U20.38 | M.TEST_UNIT.243 |
| A.U21.13 | M.TEST_UNIT.001 |
| A.U22.01 | M.TEST_UNIT.079, M.TEST_UNIT.080; holds (read) at M.TEST_UNIT.306, M.TEST_UNIT.308 |
| A.U22.02 | M.TEST_UNIT.086, M.TEST_UNIT.087 |
| A.U22.03 | dropped (withdrawn: nothing to merge, M.TEST_UNIT.090) |
| A.U22.04 | M.TEST_UNIT.078, M.TEST_UNIT.082, M.TEST_UNIT.084, M.TEST_UNIT.274, M.TEST_UNIT.276 |
| A.U23.01 | M.TEST_UNIT.333 |
| A.U23.02 | M.TEST_UNIT.333 |
| A.U23.07 | M.TEST_UNIT.333 |
| A.U23.37 | M.TEST_UNIT.086, M.TEST_UNIT.087 |
| A.U23.38 | M.TEST_UNIT.333 |
| A.U23.47 | M.TEST_UNIT.332 |
| A.U24.01 | M.TEST_UNIT.002, M.TEST_UNIT.007, M.TEST_UNIT.015, M.TEST_UNIT.039, M.TEST_UNIT.052, M.TEST_UNIT.058, M.TEST_UNIT.095, M.TEST_UNIT.104, M.TEST_UNIT.112, M.TEST_UNIT.124, M.TEST_UNIT.140, M.TEST_UNIT.153, M.TEST_UNIT.210, M.TEST_UNIT.222, M.TEST_UNIT.233, M.TEST_UNIT.265, M.TEST_UNIT.282, M.TEST_UNIT.285 |
| A.U24.02 | M.TEST_UNIT.315, M.TEST_UNIT.318 |
| A.U24.04 | M.TEST_UNIT.001, M.TEST_UNIT.300, M.TEST_UNIT.337 |
| A.U24.07 | M.TEST_UNIT.019, M.TEST_UNIT.058, M.TEST_UNIT.072, M.TEST_UNIT.077, M.TEST_UNIT.118, M.TEST_UNIT.304; holds (read) at M.TEST_UNIT.207, M.TEST_UNIT.301 |
| A.U24.08 | M.TEST_UNIT.001, M.TEST_UNIT.002, M.TEST_UNIT.007, M.TEST_UNIT.020, M.TEST_UNIT.022, M.TEST_UNIT.025, M.TEST_UNIT.029, M.TEST_UNIT.030, M.TEST_UNIT.039, M.TEST_UNIT.050, M.TEST_UNIT.052, M.TEST_UNIT.058, M.TEST_UNIT.061, M.TEST_UNIT.072, M.TEST_UNIT.078, M.TEST_UNIT.082, M.TEST_UNIT.095, M.TEST_UNIT.096, M.TEST_UNIT.114, M.TEST_UNIT.168, M.TEST_UNIT.178, M.TEST_UNIT.194, M.TEST_UNIT.210, M.TEST_UNIT.222, M.TEST_UNIT.231, M.TEST_UNIT.233, M.TEST_UNIT.239, M.TEST_UNIT.249, M.TEST_UNIT.260, M.TEST_UNIT.265, M.TEST_UNIT.267, M.TEST_UNIT.274, M.TEST_UNIT.276, M.TEST_UNIT.278, M.TEST_UNIT.280, M.TEST_UNIT.281, M.TEST_UNIT.282, M.TEST_UNIT.285, M.TEST_UNIT.288, M.TEST_UNIT.295, M.TEST_UNIT.301, M.TEST_UNIT.315, M.TEST_UNIT.326, M.TEST_UNIT.332, M.TEST_UNIT.336 |
| A.U24.09 | M.TEST_UNIT.212 |
| A.U24.15 | M.TEST_UNIT.168, M.TEST_UNIT.169, M.TEST_UNIT.178, M.TEST_UNIT.335 |
| A.U24.16 | M.TEST_UNIT.264 |
| A.U24.17 | M.TEST_UNIT.264 |
| A.U24.18 | M.TEST_UNIT.195 |
| A.U24.19 | M.TEST_UNIT.215 |
| A.U24.20 | M.TEST_UNIT.007, M.TEST_UNIT.052, M.TEST_UNIT.058, M.TEST_UNIT.114, M.TEST_UNIT.125, M.TEST_UNIT.231, M.TEST_UNIT.264 |
| A.U24.21 | M.TEST_UNIT.053, M.TEST_UNIT.054 |
| A.U24.22 | M.TEST_UNIT.030, M.TEST_UNIT.048 |
| A.U24.23 | M.TEST_UNIT.050, M.TEST_UNIT.150 |
| A.U24.24 | M.TEST_UNIT.264, M.TEST_UNIT.104 |
| A.U24.25 | M.TEST_UNIT.081 |
| A.U24.26 | M.TEST_UNIT.264 |
| A.U24.27 | M.TEST_UNIT.231; holds (read) at M.TEST_UNIT.037 |
| A.U24.28 | M.TEST_UNIT.231 |
| A.U24.29 | M.TEST_UNIT.146 |
| A.U24.31 | M.TEST_UNIT.153, M.TEST_UNIT.178 |
| A.U24.32 | M.TEST_UNIT.015, M.TEST_UNIT.217, M.TEST_UNIT.304; holds (read) at M.TEST_UNIT.213 |
| A.U24.33 | M.TEST_UNIT.028, M.TEST_UNIT.192 |
| A.U24.36 | M.TEST_UNIT.207 |
| A.U24.38 | M.TEST_UNIT.008, M.TEST_UNIT.009, M.TEST_UNIT.054, M.TEST_UNIT.075, M.TEST_UNIT.126, M.TEST_UNIT.127, M.TEST_UNIT.149, M.TEST_UNIT.152, M.TEST_UNIT.213, M.TEST_UNIT.230, M.TEST_UNIT.289, M.TEST_UNIT.338 (AC3 S-08) |
| A.U24.39 | M.TEST_UNIT.038, M.TEST_UNIT.079, M.TEST_UNIT.096, M.TEST_UNIT.183, M.TEST_UNIT.223, M.TEST_UNIT.243, M.TEST_UNIT.261, M.TEST_UNIT.270, M.TEST_UNIT.290, M.TEST_UNIT.330 |
| A.U24.40 | M.TEST_UNIT.300 |
| A.U24.41 | M.TEST_UNIT.202, M.TEST_UNIT.244 |
| A.U24.42 | M.TEST_UNIT.029, M.TEST_UNIT.104, M.TEST_UNIT.298 |
| A.U24.44 | M.TEST_UNIT.282, M.TEST_UNIT.285 |
| A.U24.45 | M.TEST_UNIT.165, M.TEST_UNIT.183, M.TEST_UNIT.210 |
| A.U24.46 | M.TEST_UNIT.231 |
| A.U24.49 | M.TEST_UNIT.007, M.TEST_UNIT.017, M.TEST_UNIT.029, M.TEST_UNIT.039, M.TEST_UNIT.058, M.TEST_UNIT.072, M.TEST_UNIT.082, M.TEST_UNIT.091, M.TEST_UNIT.093, M.TEST_UNIT.095, M.TEST_UNIT.099, M.TEST_UNIT.104, M.TEST_UNIT.106, M.TEST_UNIT.111, M.TEST_UNIT.114, M.TEST_UNIT.118, M.TEST_UNIT.121, M.TEST_UNIT.124, M.TEST_UNIT.125, M.TEST_UNIT.133, M.TEST_UNIT.141, M.TEST_UNIT.210, M.TEST_UNIT.222, M.TEST_UNIT.233, M.TEST_UNIT.265, M.TEST_UNIT.276, M.TEST_UNIT.278, M.TEST_UNIT.280, M.TEST_UNIT.281, M.TEST_UNIT.282, M.TEST_UNIT.285, M.TEST_UNIT.288, M.TEST_UNIT.295, M.TEST_UNIT.301, M.TEST_UNIT.326, M.TEST_UNIT.336 |
| A.U24.50 | M.TEST_UNIT.157 |
| A.U24.54 | M.TEST_UNIT.294 |
| A.U24.55 | M.TEST_UNIT.269 |
| A.U24.56 | M.TEST_UNIT.044, M.TEST_UNIT.212, M.TEST_UNIT.265, M.TEST_UNIT.280 |
| A.U24.57 | M.TEST_UNIT.062 |
| A.U24.58 | M.TEST_UNIT.027 |
| A.U24.59 | M.TEST_UNIT.189 |
| A.U24.60 | M.TEST_UNIT.194, M.TEST_UNIT.295, M.TEST_UNIT.300, M.TEST_UNIT.333 |
| A.U24.61 | M.TEST_UNIT.019, M.TEST_UNIT.063, M.TEST_UNIT.068, M.TEST_UNIT.070, M.TEST_UNIT.112, M.TEST_UNIT.140, M.TEST_UNIT.212, M.TEST_UNIT.229 |
| A.U24.62 | M.TEST_UNIT.068, M.TEST_UNIT.070, M.TEST_UNIT.081, M.TEST_UNIT.123, M.TEST_UNIT.251, M.TEST_UNIT.252 |
| A.U24.64 | M.TEST_UNIT.205 |
| A.U24.67 | M.TEST_UNIT.014, M.TEST_UNIT.060, M.TEST_UNIT.181, M.TEST_UNIT.210, M.TEST_UNIT.233, M.TEST_UNIT.280, M.TEST_UNIT.282, M.TEST_UNIT.285, M.TEST_UNIT.333; holds (read) at M.TEST_UNIT.301 |
| A.U24.70 | M.TEST_UNIT.025, M.TEST_UNIT.095, M.TEST_UNIT.186, M.TEST_UNIT.220, M.TEST_UNIT.239, M.TEST_UNIT.282, M.TEST_UNIT.285 |
| A.U24.73 | M.TEST_UNIT.037, M.TEST_UNIT.058, M.TEST_UNIT.070, M.TEST_UNIT.076, M.TEST_UNIT.082, M.TEST_UNIT.095, M.TEST_UNIT.109, M.TEST_UNIT.114, M.TEST_UNIT.119, M.TEST_UNIT.121, M.TEST_UNIT.124, M.TEST_UNIT.153, M.TEST_UNIT.168, M.TEST_UNIT.178, M.TEST_UNIT.186, M.TEST_UNIT.194, M.TEST_UNIT.210, M.TEST_UNIT.231, M.TEST_UNIT.233, M.TEST_UNIT.239, M.TEST_UNIT.249, M.TEST_UNIT.260, M.TEST_UNIT.265, M.TEST_UNIT.282, M.TEST_UNIT.285, M.TEST_UNIT.295, M.TEST_UNIT.301, M.TEST_UNIT.315, M.TEST_UNIT.317, M.TEST_UNIT.318, M.TEST_UNIT.326, M.TEST_UNIT.336 |
| A.U24.74 | M.TEST_UNIT.236 |
| A.U24.76 | M.TEST_UNIT.028, M.TEST_UNIT.030, M.TEST_UNIT.039, M.TEST_UNIT.052, M.TEST_UNIT.058, M.TEST_UNIT.071, M.TEST_UNIT.082, M.TEST_UNIT.095, M.TEST_UNIT.111, M.TEST_UNIT.114, M.TEST_UNIT.186, M.TEST_UNIT.210, M.TEST_UNIT.282, M.TEST_UNIT.285, M.TEST_UNIT.341 (AC3 S-07); holds (read) at M.TEST_UNIT.002 |
| A.U24.78 | M.TEST_UNIT.019, M.TEST_UNIT.042, M.TEST_UNIT.052, M.TEST_UNIT.059, M.TEST_UNIT.065, M.TEST_UNIT.066, M.TEST_UNIT.069, M.TEST_UNIT.070, M.TEST_UNIT.071, M.TEST_UNIT.117, M.TEST_UNIT.148, M.TEST_UNIT.278, M.TEST_UNIT.280, M.TEST_UNIT.298 |
| A.U24.81 | M.TEST_UNIT.219, M.TEST_UNIT.264 |
| A.U25.16 | blast-only, holds (read) at M.TEST_UNIT.050 |
| A.U25.18 | blast-only, holds (read) at M.TEST_UNIT.266 |
| A.U25.22 | blast-only, holds (`direction_from()` unaffected) |
| A.U25.30 | blast-only, holds (read) at M.TEST_UNIT.160 |
| A.U25.37 | blast-only, holds (read) at M.TEST_UNIT.220 |
| A.U26.28 | blast-only, holds (read) at M.TEST_UNIT.310 |
| A.U26.33 | blast-only, holds (read) at M.TEST_UNIT.319 |
| A.U27.03 | M.TEST_UNIT.332 |
| A.U27.07 | M.TEST_UNIT.003, M.TEST_UNIT.006, M.TEST_UNIT.197, M.TEST_UNIT.295, M.TEST_UNIT.296, M.TEST_UNIT.297, M.TEST_UNIT.298, M.TEST_UNIT.299 |
| A.U27.15 | M.TEST_UNIT.295 |
| A.U27.28 | M.TEST_UNIT.334 ((5) header presence for this cluster's 23 files; (3)'s rewraps stay with the action itself, TSC) |
| A.U27.30 | M.TEST_UNIT.111, M.TEST_UNIT.118, M.TEST_UNIT.153, M.TEST_UNIT.220 |
| A.U28.27 | M.TEST_UNIT.272; holds (read) at M.TEST_UNIT.057 |
| A.U28.28 | M.TEST_UNIT.037, M.TEST_UNIT.058, M.TEST_UNIT.095, M.TEST_UNIT.113, M.TEST_UNIT.249, M.TEST_UNIT.332; holds (read) at M.TEST_UNIT.210 |
| A.U28.29 | blast-only (a `pyproject.toml` comment; no test edit) |
| A.U28.35 | blast-only, holds (read) at M.TEST_UNIT.115 |
| A.U29.03 | blast-only, holds (read) at M.TEST_UNIT.210, M.TEST_UNIT.266, M.TEST_UNIT.282 |
| A.U30.04 | M.TEST_UNIT.129, M.TEST_UNIT.138 |
| A.U30.05 | M.TEST_UNIT.116 |
| A.U30.06 | M.TEST_UNIT.125, M.TEST_UNIT.129, M.TEST_UNIT.145; holds (read) at M.TEST_UNIT.234 |
| A.U30.07 | M.TEST_UNIT.010, M.TEST_UNIT.055, M.TEST_UNIT.059, M.TEST_UNIT.074; holds (read) at M.TEST_UNIT.234 |
| A.U30.08 | blast-only, holds (read) at M.TEST_UNIT.230 |
| A.U30.12 | M.TEST_UNIT.207 |
| A.U30.13 | M.TEST_UNIT.323 |
| A.U30.15 | M.TEST_UNIT.266 |
| A.U30.16 | M.TEST_UNIT.323; holds (read) at M.TEST_UNIT.029, M.TEST_UNIT.205 |
| A.U30.19 | M.TEST_UNIT.292, M.TEST_UNIT.309; holds (read) at M.TEST_UNIT.247 |
| A.U30.21 | M.TEST_UNIT.055 |
| A.U31.01 | blast-only, holds (read) at M.TEST_UNIT.261, M.TEST_UNIT.309 |
| A.U31.07 | M.TEST_UNIT.309 |
| A.U31.09 | M.TEST_UNIT.058, M.TEST_UNIT.114, M.TEST_UNIT.233, M.TEST_UNIT.280, M.TEST_UNIT.281 |
| A.U31.11 | M.TEST_UNIT.007, M.TEST_UNIT.008, M.TEST_UNIT.010, M.TEST_UNIT.022, M.TEST_UNIT.233 |
| A.U31.12 | blast-only, holds (read) at M.TEST_UNIT.052 |
| A.U31.13 | M.TEST_UNIT.078 |
| A.U31.14 | M.TEST_UNIT.082, M.TEST_UNIT.091 |
| A.U31.15 | M.TEST_UNIT.210, M.TEST_UNIT.213 |
| A.U31.16 | M.TEST_UNIT.240; holds (read) at M.TEST_UNIT.188, M.TEST_UNIT.247 |
| A.U31.17 | M.TEST_UNIT.301 |
| A.U31.18 | M.TEST_UNIT.196 |
| A.U32.01 | M.TEST_UNIT.211; holds (read) at M.TEST_UNIT.212 |
| A.U32.03 | M.TEST_UNIT.005 |
| A.U32.06 | M.TEST_UNIT.159, M.TEST_UNIT.179, M.TEST_UNIT.284, M.TEST_UNIT.309, M.TEST_UNIT.322 |
| A.U34.04 | M.TEST_UNIT.331 |
| A.U35.04 | blast-only (the planted-fault/allocation proofs run at B3; cited in M.TEST_UNIT.016 and M.TEST_UNIT.029 Blast) |
| A.U35.06 | M.TEST_UNIT.324 |
| A.U35.11 | M.TEST_UNIT.016 |
| A.U35.12 | M.TEST_UNIT.037, M.TEST_UNIT.076, M.TEST_UNIT.078, M.TEST_UNIT.103, M.TEST_UNIT.106, M.TEST_UNIT.124, M.TEST_UNIT.214, M.TEST_UNIT.219, M.TEST_UNIT.283, M.TEST_UNIT.284, M.TEST_UNIT.304, M.TEST_UNIT.309 |
| A.U35.13 | M.TEST_UNIT.078, M.TEST_UNIT.079, M.TEST_UNIT.080, M.TEST_UNIT.082, M.TEST_UNIT.088, M.TEST_UNIT.089, M.TEST_UNIT.090, M.TEST_UNIT.091, M.TEST_UNIT.092, M.TEST_UNIT.276, M.TEST_UNIT.278, M.TEST_UNIT.280, M.TEST_UNIT.281 |
| A.U35.14 | M.TEST_UNIT.171, M.TEST_UNIT.187, M.TEST_UNIT.190, M.TEST_UNIT.220; holds (read) at M.TEST_UNIT.280 |
| A.U35.15 | M.TEST_UNIT.111 |
| A.U35.16 | M.TEST_UNIT.234; holds (read) at M.TEST_UNIT.231 |
| A.U35.17 | M.TEST_UNIT.127, M.TEST_UNIT.235 |
| A.U35.18 | M.TEST_UNIT.236 |
| A.U35.19 | M.TEST_UNIT.236 |
| A.U35.20 | M.TEST_UNIT.152, M.TEST_UNIT.237 |
| A.U35.21 | M.TEST_UNIT.235 |
| A.U35.22 | blast-only, holds (read) at M.TEST_UNIT.167 |
| A.U35.28 | blast-only, holds (read) at M.TEST_UNIT.208 |
| A.U35.35 | M.TEST_UNIT.290 |
| A.U35.37 | M.TEST_UNIT.229, M.TEST_UNIT.230; holds (read) at M.TEST_UNIT.253 |
| A.U35.41 | blast-only, holds (read) at M.TEST_UNIT.230 |
| A.U35.42 | M.TEST_UNIT.273 |
| A.U35.43 | M.TEST_UNIT.254, M.TEST_UNIT.255, M.TEST_UNIT.256, M.TEST_UNIT.257, M.TEST_UNIT.258 |
| A.U35.44 | M.TEST_UNIT.260 |
| A.U35.45 | M.TEST_UNIT.226 |
| A.U35.48 | M.TEST_UNIT.028, M.TEST_UNIT.110, M.TEST_UNIT.166, M.TEST_UNIT.177, M.TEST_UNIT.184, M.TEST_UNIT.193, M.TEST_UNIT.209, M.TEST_UNIT.221, M.TEST_UNIT.248 |
| A.U35.50 | blast-only, holds (read) at M.TEST_UNIT.232, M.TEST_UNIT.238 |
| A.U35.55 | M.TEST_UNIT.043 |
| A.U36.004 | M.TEST_UNIT.229 |
| A.U36.014 | blast-only, holds (read) at M.TEST_UNIT.232, M.TEST_UNIT.233 |
| A.U36.027 | blast-only, holds (read) at M.TEST_UNIT.167 |
| A.U36.506 | blast-only, holds (read) at M.TEST_UNIT.063 |
| A.U36.513 | M.TEST_UNIT.212, M.TEST_UNIT.251, M.TEST_UNIT.276, M.TEST_UNIT.278, M.TEST_UNIT.280, M.TEST_UNIT.281, M.TEST_UNIT.312 |
| A.U36.517 | blast-only, holds (read) at M.TEST_UNIT.332 |
| A.U36.527 | blast-only, holds (read) at M.TEST_UNIT.295 |
| A.U36.532 | M.TEST_UNIT.168 |
| A.U36.539 | blast-only, holds (read) at M.TEST_UNIT.322 |
| A.U36.544 | M.TEST_UNIT.036, M.TEST_UNIT.109, M.TEST_UNIT.167, M.TEST_UNIT.183, M.TEST_UNIT.192, M.TEST_UNIT.194, M.TEST_UNIT.217, M.TEST_UNIT.278, M.TEST_UNIT.280, M.TEST_UNIT.281, M.TEST_UNIT.285, M.TEST_UNIT.295, M.TEST_UNIT.309, M.TEST_UNIT.311, M.TEST_UNIT.325; holds (read) at M.TEST_UNIT.220, M.TEST_UNIT.233 |
| A.U36.546 | blast-only (CLAUDE.md text; no test edit) |
| A.U37.11 | blast-only, holds (`test_asy_webserver_service.py:491, :508` unchanged) |
| A.S0930.03 | M.TEST_UNIT.167, M.TEST_UNIT.178, M.TEST_UNIT.185; holds (read) at M.TEST_UNIT.315, M.TEST_UNIT.325 |
| A.S0930.09 | M.TEST_UNIT.198; holds (read) at M.TEST_UNIT.252 |
| A.S0930.12 | M.TEST_UNIT.305, M.TEST_UNIT.307 |
| A.S0930.13 | M.TEST_UNIT.302, M.TEST_UNIT.309 |
| A.S0930.16 | blast-only, holds (read) at M.TEST_UNIT.259 |
| A.S0930.17 | M.TEST_UNIT.029; holds (read) at M.TEST_UNIT.040 |
| A.S0930.18 | M.TEST_UNIT.204 |
| A.S0930.21 | M.TEST_UNIT.048, M.TEST_UNIT.198, M.TEST_UNIT.259, M.TEST_UNIT.306 |
| A.S0930.22 | M.TEST_UNIT.259, M.TEST_UNIT.306 |
| A.S0930.23 | M.TEST_UNIT.238; holds (read) at M.TEST_UNIT.048 |
| A.S0930.24 | M.TEST_UNIT.309 |
| A.S0930.25 | M.TEST_UNIT.048, M.TEST_UNIT.306 |
| A.S0930.26 | blast-only, holds (names the `_priced` shape for the L2 reference; no change in this file) |
| A.S0930.32 | M.TEST_UNIT.306 |
| A.S0930.35 | M.TEST_UNIT.305; holds (read) at M.TEST_UNIT.238 |
| A.S0930.36 | M.TEST_UNIT.309 |
| A.SDEP.06 | M.TEST_UNIT.295; holds (read) at M.TEST_UNIT.194, M.TEST_UNIT.332 |
| A.SDEP.07 | blast-only, holds (read) at M.TEST_UNIT.194, M.TEST_UNIT.332 |
| A.SDEP.08 | M.TEST_UNIT.045, M.TEST_UNIT.081, M.TEST_UNIT.148, M.TEST_UNIT.211, M.TEST_UNIT.253, M.TEST_UNIT.332 |
| A.SDEP.13 | blast-only, holds (read) at M.TEST_UNIT.202 |
| A.SDEP.15 | M.TEST_UNIT.313 |
| A.SDEP.16 | M.TEST_UNIT.072, M.TEST_UNIT.107, M.TEST_UNIT.168 |
| A.SDEP.17 | blast-only, holds (read) at M.TEST_UNIT.216, M.TEST_UNIT.300 |
| A.SDEP.18 | M.TEST_UNIT.206 |
| A.U26.43 | M.TEST_UNIT.041 (gap pass G3) |
| A.U24.06 | M.TEST_UNIT.335 (gap pass G3) |
| A.U24.65 | M.TEST_UNIT.337 (gap pass G3) |
| A.U24.10 | M.TEST_UNIT.338 (gap pass G3) |
| A.U24.11 | M.TEST_UNIT.338 (gap pass G3) |
| A.U35.10 | M.TEST_UNIT.339 (gap pass G3) |
| A.U10.34 | M.TEST_UNIT.340 (AC3 S-05: new change) |
| AC3 S-08 | M.TEST_UNIT.338 amended: From/Site gain A.U24.38 `:116-123`; the missing-key test runs under `_RecordingOs` |
| AC3 S-18 | M.TEST_UNIT.306 amended: Resolved names `tests/test_asy_fram_manager.py` (case (3) runs here) |
| AC3 O-16 | M.TEST_UNIT.279 amended: the comment cites SPECIFICATION.md C.7, not an action ID |
| AC3 O-23 | M.TEST_UNIT.127 amended: the `:215` tag reads "(owner, 2026-09-26; SPECIFICATION.md C.8)" |

## A-C2 order notes (2026-10-01)

Unit and Depends edits made by the A-C2 work order (`audit/order/WORK_ORDER.md`); one row per edit.

| M-ID | slot | edit | reason |
|---|---|---|---|
| M.TEST_UNIT.010 | Unit | appended: A-C2 step order: A.U2.10's part lands in U3, not U2 (it follows A.U2.10's own change, which lands in U3). | dependency deferral (an edge ran from a later step) |
| M.TEST_UNIT.014 | Unit | appended: A-C2 step order: A.U2.10's part lands in U3, not U2 (it follows A.U2.10's own change, which lands in U3). | dependency deferral (an edge ran from a later step) |
| M.TEST_UNIT.015 | Unit | appended: A-C2 step order: A.U10.R01's part lands in U13, not U10 (it follows A.U10.R01's own change, which lands in U13). | dependency deferral (an edge ran from a later step) |
| M.TEST_UNIT.017 | Unit | appended: A-C2 step order: A.U10.R01's part lands in U13, not U10 (it follows A.U10.R01's own change, which lands in U13). | dependency deferral (an edge ran from a later step) |
| M.TEST_UNIT.021 | Unit | appended: A-C2 step order: A.U2.10's part lands in U3, not U2 (it follows A.U2.10's own change, which lands in U3). | dependency deferral (an edge ran from a later step) |
| M.TEST_UNIT.022 | Unit | appended: A-C2 step order: A.U10.R01's part lands in U13, not U10 (it follows A.U10.R01's own change, which lands in U13). | dependency deferral (an edge ran from a later step) |
| M.TEST_UNIT.025 | Unit | appended: A-C2 step order: A.U24.70's part lands in U25, not U24 (it needs A.U24.65, which lands in U25). | dependency deferral (an edge ran from a later step) |
| M.TEST_UNIT.056 | Depends | `value log (A.U24.16), per-id I2C state and `raise_on_construct` (A.U24.20), fake clock for `ticks_us` (A.U14.34/A.U35.10)` → `value log (M.TEST_HELP.012's A.U13.R01 part, U13; A.U24.16 [follows]), per-id I2C state and `raise_on_construct` (M.TEST_HELP.013's A.U13.R01 part, U13; A.U24.20 [follows]), fake clock for `ticks_us` (A.U14.34; A.U35.10 [follows] replaces it in U35)` | the fakes land with A.U13.R01 in U13; A.U24.16/.20 and A.U35.10 complete or replace them later |
| M.TEST_UNIT.056 | Unit | appended: A-C2 step order: stage U14 — the SCL-held timeout cases, which drive `ticks_us` through A.U14.34's fake time, land in U14; the pulse, STOP and status cases land in U13 with the clear. | Depends edge ran from a later step: A.U14.34's fake time lands in U14 |
| M.TEST_UNIT.060 | Unit | appended: A-C2 step order: A.U10.R01's part lands in U13, not U10 (it follows A.U10.R01's own change, which lands in U13). | dependency deferral (an edge ran from a later step) |
| M.TEST_UNIT.061 | Unit | appended: A-C2 step order: A.U10.R01's part lands in U13, not U10 (it follows A.U10.R01's own change, which lands in U13). | dependency deferral (an edge ran from a later step) |
| M.TEST_UNIT.062 | Unit | appended: A-C2 step order: A.U2.12's part lands in U3, not U2 (it follows A.U2.12's own change, which lands in U3). | dependency deferral (an edge ran from a later step) |
| M.TEST_UNIT.065 | Unit | appended: A-C2 step order: A.U2.12's part lands in U3, not U2 (it follows A.U2.12's own change, which lands in U3). | dependency deferral (an edge ran from a later step) |
| M.TEST_UNIT.066 | Unit | appended: A-C2 step order: A.U2.12's part lands in U3, not U2 (it follows A.U2.12's own change, which lands in U3). | dependency deferral (an edge ran from a later step) |
| M.TEST_UNIT.067 | Unit | appended: A-C2 step order: A.U2.12's part lands in U3, not U2 (it follows A.U2.12's own change, which lands in U3). | dependency deferral (an edge ran from a later step) |
| M.TEST_UNIT.068 | Unit | appended: A-C2 step order: A.U2.12's part lands in U3, not U2 (it follows A.U2.12's own change, which lands in U3). | dependency deferral (an edge ran from a later step) |
| M.TEST_UNIT.069 | Unit | appended: A-C2 step order: A.U2.12's part lands in U3, not U2 (it follows A.U2.12's own change, which lands in U3). | dependency deferral (an edge ran from a later step) |
| M.TEST_UNIT.070 | Unit | appended: A-C2 step order: A.U2.12's part lands in U3, not U2 (it follows A.U2.12's own change, which lands in U3). | dependency deferral (an edge ran from a later step) |
| M.TEST_UNIT.071 | Unit | appended: A-C2 step order: A.U2.12's part lands in U3, not U2 (it follows A.U2.12's own change, which lands in U3). | dependency deferral (an edge ran from a later step) |
| M.TEST_UNIT.073 | Unit | appended: A-C2 step order: A.U2.12's part lands in U3, not U2 (it follows A.U2.12's own change, which lands in U3). | dependency deferral (an edge ran from a later step) |
| M.TEST_UNIT.083 | Unit | appended: A-C2 step order: A.U2.17's part lands in U3, not U2 (it follows A.U2.17's own change, which lands in U3). | dependency deferral (an edge ran from a later step) |
| M.TEST_UNIT.087 | Unit | appended: A-C2 step order: A.U2.17's part lands in U3, not U2 (it follows A.U2.17's own change, which lands in U3). | dependency deferral (an edge ran from a later step) |
| M.TEST_UNIT.089 | Unit | appended: A-C2 step order: A.U2.17's part lands in U3, not U2 (it follows A.U2.17's own change, which lands in U3); A.U10.28's part lands in U16, not U10 (it needs A.U16.18, which lands in U16). | dependency deferral (an edge ran from a later step) |
| M.TEST_UNIT.090 | Unit | appended: A-C2 step order: A.U9.09's part lands in U10, not U9 (it follows A.U9.09's own change, which lands in U10). | dependency deferral (an edge ran from a later step) |
| M.TEST_UNIT.092 | Unit | appended: A-C2 step order: A.U2.17's part lands in U3, not U2 (it follows A.U2.17's own change, which lands in U3). | dependency deferral (an edge ran from a later step) |
| M.TEST_UNIT.095 | Unit | appended: A-C2 step order: A.U24.70's part lands in U25, not U24 (it follows A.U24.70's own change, which lands in U25). | dependency deferral (an edge ran from a later step) |
| M.TEST_UNIT.102 | Unit | appended: A-C2 step order: A.U2.15's part lands in U3, not U2 (it follows A.U2.15's own change, which lands in U3). | dependency deferral (an edge ran from a later step) |
| M.TEST_UNIT.103 | Unit | appended: A-C2 step order: A.U2.15's part lands in U3, not U2 (it follows A.U2.15's own change, which lands in U3). | dependency deferral (an edge ran from a later step) |
| M.TEST_UNIT.105 | Unit | appended: A-C2 step order: A.U2.15's part lands in U3, not U2 (it follows A.U2.15's own change, which lands in U3). | dependency deferral (an edge ran from a later step) |
| M.TEST_UNIT.109 | Unit | appended: A-C2 step order: A.U2.15's part lands in U3, not U2 (it follows A.U2.15's own change, which lands in U3). | dependency deferral (an edge ran from a later step) |
| M.TEST_UNIT.122 | Unit | appended: A-C2 step order: A.U10.R01's part lands in U13, not U10 (it follows A.U10.R01's own change, which lands in U13). | dependency deferral (an edge ran from a later step) |
| M.TEST_UNIT.130 | Unit | appended: A-C2 step order: A.U2.13's part lands in U3, not U2 (it follows A.U2.13's own change, which lands in U3). | dependency deferral (an edge ran from a later step) |
| M.TEST_UNIT.132 | Unit | appended: A-C2 step order: A.U10.R01's part lands in U13, not U10 (it follows A.U10.R01's own change, which lands in U13). | dependency deferral (an edge ran from a later step) |
| M.TEST_UNIT.136 | Unit | appended: A-C2 step order: A.U2.13's part lands in U3, not U2 (it follows A.U2.13's own change, which lands in U3). | dependency deferral (an edge ran from a later step) |
| M.TEST_UNIT.137 | Unit | appended: A-C2: stage U24 — until M.TEST_HELP.044's `src_const()` exists the wrap test keeps a local mirror of the cap (the HEAD form); U24 swaps in `src_const()`. | Depends edge ran from a later step: M.TEST_HELP.044 lands in U24 |
| M.TEST_UNIT.138 | Unit | appended: A-C2 step order: A.U2.13's part lands in U3, not U2 (it follows A.U2.13's own change, which lands in U3). | dependency deferral (an edge ran from a later step) |
| M.TEST_UNIT.142 | Unit | appended: A-C2 step order: A.U2.13's part lands in U3, not U2 (it follows A.U2.13's own change, which lands in U3). | dependency deferral (an edge ran from a later step) |
| M.TEST_UNIT.143 | Unit | appended: A-C2 step order: A.U10.R01's part lands in U13, not U10 (it follows A.U10.R01's own change, which lands in U13). | dependency deferral (an edge ran from a later step) |
| M.TEST_UNIT.144 | Unit | appended: A-C2 step order: A.U2.13's part lands in U3, not U2 (it follows A.U2.13's own change, which lands in U3). | dependency deferral (an edge ran from a later step) |
| M.TEST_UNIT.157 | Unit | appended: A-C2 step order: A.U2.02's part lands in U3, not U2 (it follows A.U2.02's own change, which lands in U3). | dependency deferral (an edge ran from a later step) |
| M.TEST_UNIT.161 | Unit | appended: A-C2: stage U24 — until M.TEST_HELP.044's `src_const()` exists the streak threshold is a local mirror (the HEAD form); U24 swaps in `src_const()`. | Depends edge ran from a later step: M.TEST_HELP.044 lands in U24 |
| M.TEST_UNIT.173 | Depends | `M.TEST_HELP.017` → `M.TEST_HELP.018` | the fake `txdone()`/`tx_pending_rounds` is M.TEST_HELP.018 (lands in U13), not .017 (U24) |
| M.TEST_UNIT.175 | Depends | `M.TEST_HELP.017` → `M.TEST_HELP.018` | the fake `readline(size)` is M.TEST_HELP.018 (lands in U13), not .017 (U24) |
| M.TEST_UNIT.186 | Unit | appended: A-C2 step order: A.U24.70's part lands in U25, not U24 (it follows A.U24.70's own change, which lands in U25). | dependency deferral (an edge ran from a later step) |
| M.TEST_UNIT.198 | Unit | appended: A-C2: "S0930" is not a unit; its parts land in the units SUPP_owner_0930 states: A.S0930.09 in U19, A.S0930.21 in U24. | AC3_R R-08 (h) |
| M.TEST_UNIT.204 | Unit | appended: A-C2: "S0930" is not a unit; its parts land in the units SUPP_owner_0930 states: A.S0930.18 in U19. | AC3_R R-08 (h) |
| M.TEST_UNIT.204 | Unit | appended: A-C2: stage U24 — until M.TEST_HELP.052/.056 exist the tests use the file's own sleep double and port allocator (the HEAD form); U24 swaps in `FastAsyncSleep` and the port-band table. | Depends edge ran from a later step: M.TEST_HELP.052/.056 land in U24 |
| M.TEST_UNIT.208 | Unit | appended: A-C2: stage U35 — until M.TEST_HELP.065 exists the driven window runs on the file's own time double (the HEAD form); U35 swaps in `DrivenTime`. | Depends edge ran from a later step: M.TEST_HELP.065 lands in U35 |
| M.TEST_UNIT.218 | Unit | appended: A-C2 step order: A.U10.R01's part lands in U13, not U10 (it follows A.U10.R01's own change, which lands in U13). | dependency deferral (an edge ran from a later step) |
| M.TEST_UNIT.220 | Unit | appended: A-C2 step order: A.U24.70's part lands in U25, not U24 (it follows A.U24.70's own change, which lands in U25). | dependency deferral (an edge ran from a later step) |
| M.TEST_UNIT.225 | Unit | appended: A-C2 step order: A.U10.28's part lands in U16, not U10 (it needs A.U16.18, which lands in U16). | dependency deferral (an edge ran from a later step) |
| M.TEST_UNIT.225 | Unit | appended: A-C2: stage U24 — until M.TEST_HELP.050/.053 exist the print capture and the arm-failure double are file-local (the HEAD form); U24 swaps in `record_prints()` and `RaiseOnArm`. | Depends edge ran from a later step: M.TEST_HELP.050/.053 land in U24 |
| M.TEST_UNIT.227 | Unit | appended: A-C2 step order: A.U10.R01's part lands in U13, not U10 (it follows A.U10.R01's own change, which lands in U13). | dependency deferral (an edge ran from a later step) |
| M.TEST_UNIT.238 | Unit | appended: A-C2: "S0930" is not a unit; its parts land in the units SUPP_owner_0930 states: A.S0930.23 in U24. | AC3_R R-08 (h) |
| M.TEST_UNIT.239 | Unit | appended: A-C2 step order: A.U24.70's part lands in U25, not U24 (it follows A.U24.70's own change, which lands in U25). | dependency deferral (an edge ran from a later step) |
| M.TEST_UNIT.247 | Depends | `M.SRC_NET.007, .011` → `M.SRC_NET.007; M.SRC_NET.011 [follows] (its U30 `report_if_fatal` lines)` | the U18 tests do not exercise the U30 handler lines |
| M.TEST_UNIT.279 | Unit | appended: A-C2 step order: A.U10.R01's part lands in U13, not U10 (it follows A.U10.R01's own change, which lands in U13). | dependency deferral (an edge ran from a later step) |
| M.TEST_UNIT.282 | Unit | appended: A-C2 step order: A.U24.70's part lands in U25, not U24 (it follows A.U24.70's own change, which lands in U25). | dependency deferral (an edge ran from a later step) |
| M.TEST_UNIT.285 | Unit | appended: A-C2 step order: A.U24.70's part lands in U25, not U24 (it follows A.U24.70's own change, which lands in U25). | dependency deferral (an edge ran from a later step) |
| M.TEST_UNIT.286 | Depends | `M.SRC_NET.0xx` → `M.SRC_NET.074/.091` | unknown reference M.SRC_NET.000 ("0xx"): the snapshot changes are M.SRC_NET.074 and .091 |
| M.TEST_UNIT.287 | Unit | appended: A-C2 step order: A.U2.15's part lands in U3, not U2 (it follows A.U2.15's own change, which lands in U3). | dependency deferral (an edge ran from a later step) |
| M.TEST_UNIT.303 | Unit | appended: A-C2: stage U35 — until M.TEST_HELP.065 exists the pumps run on the file's own clock double (the HEAD form); U35 swaps in the driven clock. | Depends edge ran from a later step: M.TEST_HELP.065 lands in U35 |
| M.TEST_UNIT.305 | Unit | appended: A-C2 step order: A.S0930.12's part lands in U20, not U11 (it follows A.S0930.12's own change, which lands in U20). | dependency deferral (an edge ran from a later step) |
| M.TEST_UNIT.306 | Unit | appended: A-C2 step order: A.S0930.32's part lands in U20, not U11 (it needs A.S0930.13, which lands in U20). | dependency deferral (an edge ran from a later step) |
| M.TEST_UNIT.307 | Unit | appended: A-C2 step order: A.S0930.12's part lands in U20, not U11 (it follows A.S0930.12's own change, which lands in U20). | dependency deferral (an edge ran from a later step) |
| M.TEST_UNIT.336 | Unit | appended: A-C2 step order: A.U2.17's part lands in U3, not U2 (it follows A.U2.17's own change, which lands in U3). | dependency deferral (an edge ran from a later step) |
| M.TEST_UNIT.337 | Unit | appended: A-C2 step order: A.U24.65's part lands in U25, not U24 (it follows A.U24.65's own change, which lands in U25). | dependency deferral (an edge ran from a later step) |

## A-C review fold (2026-10-05)

Owner answers OR136-OR143 and the routine settlements folded in (`audit/actions/FOLD_BRIEF.md`); one row per item and
action. `[fold Fnn M_FILE]` tokens in Depends/Blast name changes other fold agents add.

| Fnn | M-ID(s) | action |
|---|---|---|
| F01 | M.TEST_UNIT.024, .077, .253, .254, .256, .257, .258, .306 | amended |
| F02 | M.TEST_UNIT.343 | added |
| F02 | M.TEST_UNIT.202 | amended |
| F03 | M.TEST_UNIT.253, .254, .259, .306 | amended |
| F04 | — | none in this file |
| F05 | — | none in this file |
| F06 | — | none in this file |
| F07 | — | none in this file |
| F08 | M.TEST_UNIT.270, .271, .273 | amended |
| F09 | M.TEST_UNIT.080 | amended |
| F10 | — | none in this file |
| F11 | M.TEST_UNIT.017, .024, .041, .044, .046, .060, .061, .063, .077, .086, .091, .113, .122, .132, .135, .136, .138, .142, .143, .218, .227, .255, .265, .279, .280 | amended |
| F12 | — | none in this file |
| F13 | — | none in this file |
| F14 | — | none in this file |
| F15 | M.TEST_UNIT.306 | amended |
| F16 | M.TEST_UNIT.342 | added |
| F17 | — | none in this file |
| F18 | — | none in this file |
| F19 | M.TEST_UNIT.213 | amended |
| F20 | — | none in this file (checked: the remaining WoZi mentions in these test files are legacy citations or test input data; the device-naming comments already go in M.TEST_UNIT.199/.233/.251) |
| F21 | M.TEST_UNIT.046, .080, .279 | tag |
| F22 | — | none in this file |
| F23 | M.TEST_UNIT.064 (and the Conventions bullet "Function-level imports") | amended |
| F24 | — | none in this file (checked: the VOC tests use upstream names only) |
| F25 | M.TEST_UNIT.344, .345 | added |
| F25 | M.TEST_UNIT.155, .169, .175, .176, .317 | amended |
| F26 | — | none in this file (the idle-rate twin measurement is M.TWIN.144 test 10) |
| F27 | M.TEST_UNIT.344 (d), .345 | added |
| F27 | M.TEST_UNIT.164 | amended |
| F28 | M.TEST_UNIT.078, .079, .293 (and GAP-U3, Owner questions 2) | amended |
| F29 | M.TEST_UNIT.104 | amended |
| F30 | — | none in this file |
| F31 | — | none in this file |
| F32 | — | none in this file |
| F33 | M.TEST_UNIT.291 (and the D-T27 entry of the agent-decision list) | amended |
