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
  the delta), which keeps G4/R49's "no in-body stage override" (M.TEST_UNIT.113's rule). Header ≤ 3 lines; canonical
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
- **From**: A.U0.35 (`:112`, `:183`), A.U11.26 (the section header's premise changes with the hook semantics).
- **Site**: `tests/test_api_response.py:111-113`, `:180-184`.
- **Change**: `:112-113` → "# (owner, 2026-09-26): per-field failures don't demote the overall response - res not OK
  would mean the request itself was broken; individual field outcomes live in "result"." (2 lines). Section header
  `:180-184` → "# handle_set_cmd - drives SensorReaderConfig._set_dict_cfg, the post-write hook and the envelope; a
  raising / # hook turns its group's fields "Failed" inside the OK envelope, caught as defense in depth on top of / #
  Microdot's own per-request catch (agent, 2026-08-03: prior field experience with Microdot behaving unexpectedly)."
  between the two `# ----` rules (3 prose lines).
- **Resolved**: A.U0.35 relabels a header whose premise ("its own try/except as defense-in-depth" around the whole
  call) A.U11.26 narrows to the hook; one text carries both.
- **Unit**: U11 (stage U0: A.U0.35's two labels on the HEAD text; U11 rewrites the header with the hook change).
- **Depends**: M.TEST_UNIT.005.
- **Blast carried by**: `tests_scripts/test_comment_block_cap.py` (holds, ≤ 3).
- **Kind**: doc

### M.TEST_UNIT.005 `handle_set_cmd()` tests: constructor tail, OK envelope on a raising hook
- **From**: A.U5.02 (`:190` constructor), A.U11.26 (`:282-332` re-expected; new mixed-result and no-Valid tests),
  A.U2.18 (persisted `code("E", "CALLBACK")`), A.U4.02, A.U32.03, A.U11.S02 (read: hold).
- **Site**: `tests/test_api_response.py:187-192` (`_make_reader`), `:282-332` (three raising-hook tests), new tests
  after `:355`.
- **Change**: `_make_reader` builds `SensorReaderConfig(Meas(20.0, 50), name, cfg_vals, max_module_error=3,
  cfg_path=path_prefix)` (M.SRC_CORE.040's order). The three raising-hook tests each assert `resp == {"res": "OK",
  "code": 0, "descr": "Command executed", "result": {"SampleInterv": "Failed"}}`, `reader.pr.err_count == 1`, and
  exactly one entry in `reader.pr.get_log()` with number `code("E", "CALLBACK")` and `ErrType` "E"; names →
  `…_sync_post_fct_raising_fails_its_group_inside_an_ok_envelope`, `…_async_post_fct_raising_fails_its_group_inside_an_ok_envelope`;
  `:313` keeps its name and "never scheduled" assertion, its comment's last sentence → "… and the group's fields read
  Failed inside the OK envelope."; the `:283-285` comment → "# A raising post-write hook is caller-supplied code outside
  _set_dict_cfg(): its failure is its group's outcome." New: `test_handle_set_cmd_hook_raising_after_a_mixed_result_fails_every_key`
  (`{"SampleInterv": 42, "Ghost": 1}` with a raising `post_fct` → both keys "Failed", code 0, one CALLBACK entry);
  `test_handle_set_cmd_never_calls_a_hook_when_nothing_is_valid` (`{"SampleInterv": 9999}` → "Invalid", neither hook
  called).
- **Resolved**: A.U11.26's "one persisted CALLBACK entry" and A.U2.18's "new L1 … persists exactly `code("E",
  "CALLBACK")`" are one assertion on the rewritten tests (no separate test); the reader here has no FRAM (`log` default),
  so "persisted" is the logger's history entry read through `get_log()`.
- **Unit**: U11 (stage U5: the constructor call co-lands with A.U5.02's signature change).
- **Depends**: M.SRC_CORE.036, M.SRC_CORE.040, M.SRC_CORE.072; A.U2.03 (`tests/_error_codes.py`).
- **Blast carried by**: webserver hook-failure tests → M.TEST_UNIT in `test_asy_webserver_service.py` (A.U11.26).
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
- **From**: A.U2.10 (`:1306, 1325, 1343, 1382, 1437`), A.U3.05 (`:1323-1343`, `:1346-1390`), A.U15.22 (2) (`_store_bmp()`
  uses the captured values; new capture and last-sample L1), A.U15.24 (W11 L1), A.U10.06 (L1 `TS` before sync),
  A.U10.R01 + A.U15.R03 (`:1393-1411` re-derived; four new rung L1), A.U2.06 + A.U3.03 (no errno-1 streak entry),
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
    `False`; the BMP3XX log has no entry (a console line only, A.U3.05) and `CFGMGR_BMP3XX` has exactly one
    `code("E", "CFG_NOT_VALID")`; no bus rung ran (the fake log holds no `recover` marker).
  - `test_store_bmp_falls_back_to_default_compensation_values_when_config_unreadable` → `…read_bmp_captures_the_default_compensation…`:
    baseline as today (offsets written with `write_config({...})`, read + store, offsets applied); then
    `reader.cfgmgr.valid = False`, `results = _read_bmp()` (the capture falls back to `[0.0, 0.0, 0.0, 15.0]`), `_store_bmp(results)`;
    assertions: `CFGMGR_BMP3XX` newest entry `code("E", "CFG_NOT_VALID")`, the BMP3XX log unchanged, `Pres == results[0]`,
    `Temp == results[1]`, `SLPres == results[0]` (`:1386-1388` comment names `pressure_at_height()`), `TS == results[2]`.
  - `test_reader_read_error_check_threshold_and_self_heal`: outcomes stay `[True, True, False, True]`; the log shows one
    `code("E", "CHIP_SET")` "Soft reset failed" from the device rung at the 2nd failure (NAKed reset), then
    `code("E", "GIVE_UP")`; no streak entry per failed cycle (A.U3.03).
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
    offset captured before); `test_a_failed_read_keeps_the_last_good_sample_and_its_timestamp` (`set_utc_valid(True)`,
    restored in `finally`; a good cycle then a NAKed one: `get_data()` equals the first sample, its `TS` unchanged);
    `test_a_read_before_the_first_sync_publishes_with_ts_none`.
  - New L1 (A.U15.24): `PresOffset` 450 on the planted 713.77 hPa reading → `Pres` 263.77, `SLPres` `None`, one
    `code("W", "DERIVED_DOMAIN")`; a second such cycle leaves one slot and `ErrCount` 2 (newest-entry rule); `PresOffset`
    10 → no entry.
- **Resolved**: A.U15.24's example (raw 1000 hPa, `PressOffset` 750) is outside the schema's ±500 hPa bound, so no
  write can store it; the same domain exit is produced by an in-schema offset on the file's planted reading (agent
  correction). A.U15.R03's "logs its own errno 12/13 as today" is M.SRC_SENS.044's code-returning helper (config
  unreadable prints only).
- **Unit**: U15 (stages U2 numbers, U3 console/CFGMGR, U5 constructor, U10 setup/ladder/TS, U24 builder).
- **Depends**: M.SRC_SENS.043, M.SRC_SENS.044, M.SRC_SENS.047, M.SRC_CORE.037, M.SRC_CORE.040; A.U2.03.
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
- **Change**: `test_get_data_and_get_dict_data_reflect_a_stored_reading` calls `set_utc_valid(True)` first (restored in
  `finally`). `test_get_cfg_schema_matches_the_full_schema`: `reader.get_cfg_schema() == _FULL_SCHEMA` (the
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
- **Depends**: M.SRC_SENS.047.
- **Blast carried by**: —
- **Kind**: test

### M.TEST_UNIT.022 Reader-loop tests: the private loop ends, returns nothing
- **From**: A.U10.44 (`_read_loop`), A.U15.43 (`None`), A.U8.07 + A.U31.11 (`:1983` comment), A.U10.06 (`TS` needs a
  sync), A.U10.R01 (the rung inside the give-up run), A.U24.08.
- **Site**: `tests/test_asy_bmp3xx_driver.py:1931-2021`.
- **Change**: both tests start `reader._read_loop()`; the happy test sets `set_utc_valid(True)` (restored) before
  asserting `data.TS is not None`, its `:1983` comment → "# let _init_bmp()'s reset settle (_RESET_SETTLE_MS) pass";
  `test_read_loop_gives_up_and_returns_false_after_max_errors` → `…_gives_up_and_ends_after_max_errors`, asserting the
  task is done and returned `None`, and that the log ends with `code("E", "GIVE_UP")`.
- **Resolved**: —
- **Unit**: U15 (stage U10 name).
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
  A.U3.05 + A.U2.10 (`:2071` "12 not in" — 12 is CHIP_GET after the renumbering).
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
  `test_ipv4_to_int_*` value tests and the type-matrix test move here verbatim from `tests/test_captive_dns.py` (their
  expected integers are RFC 791 arithmetic, unchanged), importing `ipv4_to_int` from `asy_dns_client`.
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

