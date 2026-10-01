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
- **Function-level imports** (A.U0.07: `tests/` holds 91 in 29 files in its `_PENDING` set, which U24 empties, plus the
  dynamic sites A.U10.30 names): every `import`/`from … import` inside a test function or helper moves to the file's
  module-level imports (an alias such as `import time as _time` becomes the module's `time`), so the L0
  `tests_scripts/test_import_placement.py` entry for that file can leave `_PENDING`; the `if __name__ == "__main__":`
  `import microtest` is module level and stays. A file's section names this only where it changes more than an import
  line.
- **Timestamps before the first sync** (A.U10.06, M.SRC_CORE.032, GAP-15 ruling): `utc_now()` is `None` until
  `set_utc_valid()` (no argument) runs. A test that needs a real `TS` calls `asy_base_classes.set_utc_valid()` and resets
  `asy_base_classes._utc_valid = False` in `finally`; a test that calls a reader's `_error_check(results)` directly (not
  through `_read_loop()`) on a successful cycle does the same, since only the reader's own `condition` keeps a pre-sync
  `TS` from counting (M.SRC_SENS.083, .089-.091).
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
    offset captured before); `test_a_failed_read_keeps_the_last_good_sample_and_its_timestamp` (`set_utc_valid()`,
    `asy_base_classes._utc_valid = False` in `finally`, M.SRC_CORE.032's no-argument form; a good cycle then a NAKed one: `get_data()` equals the first sample, its `TS` unchanged);
    `test_a_read_before_the_first_sync_publishes_with_ts_none` (and steps no error streak: `_error_check()` sees the
    reader's `condition` exclude the trailing `TS`, M_SRC_SENS GAP-15).
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

## tests/test_asy_fram_manager.py

End state: the chunk layer's tests against M.SRC_CORE.080-093 — `FRAMManager`/`FRAMChunk`/`FRAMTimestampedChunk`, one
persisted entry per failure at the detecting layer (the rest console lines), the catalog's FRAM band, a tri-state
read, blank blocks never marked busy, no `override_pause`, no episodes (the central newest-entry rule), bool-first
timestamped writes on `utc_now()`, the erase trio, the chip-watch task. **Code map for every assertion of this file**
(A.U2.09 + A.U3.04): 31/34 → `code("E", "FRAM_STATUS_BYTE")` (46), 36 → FRAM_STATUS_DISAGREE (47), 17/38 →
FRAM_CRC_FAILED (48), 46 → FRAM_DATA_CRC (49), 63/64 → FRAM_VERIFY (50), 73 → FRAM_COPIES_DIFFER (51), 83 → INIT
(10), 85/87 → CALLBACK (14), 26/47/58 → UNEXPECTED (23), 48/60/70/81/84 → BAD_ARG (21), w60/w70/w80 → `code("W",
"FRAM_PAUSED")` (25); 10/11/18/19/20/30/32/33/35/37/39/50/51(HEAD)/57/61/62/71/72/80 become console lines — an
assertion on one of them becomes "the operation's result and no persisted entry from this layer" (recorded console
lines through `tests/_recording_print.py` where the test's point is the message); 82/86/88 retire with their handlers.

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
  L1), A.U16.06 (new tri-state L1), A.U3.04 (new one-entry-per-fault L1), A.U3.09 (new missing-buffer L1).
- **Site**: `tests/test_asy_fram_manager.py:212-350`, `:984-1096`, `:1525-1580`, `:1644-1852`, `:2476-2584`; new
  tests after `:350`.
- **Change**: every code assertion follows the map above (e.g. `:235` `31` → `code("E", "FRAM_STATUS_BYTE")`, `:614`
  `73` → FRAM_COPIES_DIFFER); console-only codes (`:816-817` 10/61, `:838-839` 32/72, `:1054` 71, `:1082` 72, `:1673`
  62, `:1717` 11, `:1761` 18, `:1783` 37, `:1830` 39, `:1850` 57) become "the operation's result, and the log holds only
  the detecting layer's entry" (for a planted driver failure, the driver's own code; for an injected sentinel failure,
  no entry). `:329-331` → "# A write torn between block 0 and block 1: both blocks valid (CRC_Pass, both status bytes
  IDLE) but / # different, and no generation counter says which is right, so the read fails rather than guesses /
  # (owner, 2026-07-18)." and the test asserts exactly one FRAM_COPIES_DIFFER entry. `:1538` and `:1686-1687` (UNINIT
  planted into one byte): a mixed pair still fails the consistency check (one FRAM_STATUS_DISAGREE) and the idle byte
  keeps its busy marker; a fully blank block is not marked. `:2509-2511` comment → "# A blank chip's whole read is two
  status-byte reads per block that find UNINIT and return, so the / # yield after that pair must come before those early
  returns." New: `test_a_never_written_chunk_read_twice_reports_uninitialised_both_times` (both `read_into()` `False`,
  both status bytes still 0x00, no FRAM-log entry; the same after `clear()`);
  `test_read_into_is_tri_state` (driver not initialised → `None`; both blocks with a bad status byte → `False`; a blank
  chunk → `False`; a failed repair write → `None`); `test_each_planted_fault_adds_exactly_one_entry` (driver not
  initialised, WEL not set, status byte BUSY, CRC mismatch in block 0 with a good block 1, both blocks invalid,
  verification mismatch — one operation each, one persisted entry each with the mapped code);
  `test_after_a_failed_setup_ten_writes_leave_one_slot_and_errcount_ten` (RF171);
  `test_a_verify_pass_whose_block_read_fails_the_crc_adds_one_entry` (FRAM_DATA_CRC);
  `test_an_unallocatable_check_length_adds_one_alloc_entry_on_read_and_write` (`code("E", "ALLOC")`);
  `test_a_missing_chunk_buffer_persists_alloc_once` (A.U3.09).
- **Resolved**: A.U3.04 and A.U2.09 co-land (same sites); the map above is their joint end state.
- **Unit**: U16 (stages U2 numbers, U3 persist/print split).
- **Depends**: M.SRC_CORE.082, .084, .085, .088, .090; A.U2.03.
- **Blast carried by**: SPEC A.4 FRAM error flow → A.U3.04 (SPEC); L2 double read → A.U16.09 (TWIN).
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
- **From**: A.U2.09/A.U3.04 (`:774-790`, `:798-980`, `:1393-1436`, `:1444-1520`), A.U13.08 (`:1409-1436`), A.U24.56
  (`:886` tag), A.U8C.08 (`:751`).
- **Site**: `tests/test_asy_fram_manager.py:720-980`, `:1376-1520`.
- **Change**: `:751` `wait_for(…, 5)` → `_READ_WAIT_S` (`# @tunable l1.asy_fram_manager_read_wait_s = 5`). `:774-790`
  → `test_oversized_write_persists_one_bad_arg_entry` (`code("E", "BAD_ARG")` once; the "84 not colliding with clear's
  80" claim goes: `clear()`'s failure is a console line now). `:886` → "# Intended, accepted behaviour, not a defect
  (owner, 2026-09-11; SPEC A.4):"; `:909-910` → the read refused (`None`), the driver's write-protected warning the one
  persisted entry, data intact after unprotect. `:952-975`: write/read/clear each fail, the log holds `code("E",
  "NOT_INIT")` (driver guard), identical repeats in one slot with `ErrCount` 3. `:1393-1407` → `code("E", "INIT")`.
  `:1410-1436` → `test_chunk_operations_fail_cleanly_when_the_bus_is_deinitialized_mid_run`: each operation fails, the
  log holds `code("E", "FRAM_BUS_DOWN")` (the driver's status, M.SRC_CORE.104) and no UNEXPECTED entry; its comment →
  "# A deinitialised bus is reported by the driver as bus-down; the chunk layer fails the operation and prints."
- **Resolved**: —
- **Unit**: U16 (stages U2, U8C tag, U13 bus-down, U24 tag text).
- **Depends**: M.SRC_CORE.082-.085, .104.
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

### M.TEST_UNIT.046 The status-byte errno spread becomes one entry per event
- **From**: A.U2.09 (the `err=` arithmetic goes), A.U3.04 (status-byte read/write failures print).
- **Site**: `tests/test_asy_fram_manager.py:2336-2470`.
- **Change**: banner → "# Status-byte failures, branch by branch: the detecting layer persists one entry (Part
  C.7.1); a propagated failure prints." The six tests keep their injection points and become: idle-mark write failure on
  byte 1 / byte 2 → `write()` `False`, no persisted entry (the injected report persisted nothing; the chunk layer
  prints); busy-mark byte-2 read failure → read `None`, no entry; byte 2 neither idle nor uninit (`0x7F`) → exactly one
  `code("E", "FRAM_STATUS_BYTE")`; busy-mark byte-2 write failure → no entry; clear's byte-2 failure → `clear()`
  `False`, no entry. Names drop the HEAD numbers (`…reports_errno_19` → `…fails_the_write_without_a_second_entry`, …).
- **Resolved**: the per-byte numbers they pinned are retired by A.U2.09 (one code per condition); one-entry-per-event
  (OR56.a (1)) is the replacement guard.
- **Unit**: U16.
- **Depends**: M.SRC_CORE.084, .085.
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
- **Depends**: M.SRC_SENS.008, .010; TEST_HELP `tests/machine.py` `Pin` `OPEN_DRAIN`/`ALT`/`ALT_I2C`/scripted levels/value
  log (A.U24.16), per-id I2C state and `raise_on_construct` (A.U24.20), fake clock for `ticks_us` (A.U14.34/A.U35.10).
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
- **From**: A.U24.67 (`:826-827` comment), A.U2.12 (`:862`, `:897`), A.U3.05 (`:875`), A.U10.R01 + A.U15.R04
  (`_init_failed()`/`_init_done()`; config-read failure runs no rung), A.U15.34 (new restart L1), A.U10.10.
- **Site**: `tests/test_asy_isl29125_driver.py:825-923`.
- **Change**: `:826-827` → "# Requirement 20, satisfied here or nowhere: every generated device's object graph is built
  against a fake holding no ISL registers." The three construction tests drop `all_timers.clear()`.
  `test_init_returns_false_and_logs_errno_10…` → `…logs_an_init_error_and_reinitialises_the_controller`: `errors()[-1]
  == code("E", "INIT")` and one `code("W", "BUS_RECOVERY")` (`_init_failed()`'s controller rung on `_recovery_bus`).
  `…errno_12_when_the_config_is_unreadable` → `…_config_is_unreadable_logs_in_the_config_store_only`: the ISL29125 log
  is empty, `CFGMGR_ISL29125` holds exactly one `code("E", "CFG_NOT_VALID")`, `reader._recovery_bus.recoveries` is
  unchanged (no rung). `…errno_13_when_applying_the_config_raises` → `…logs_chip_set…`: `code("E", "CHIP_SET")` then
  `code("W", "BUS_RECOVERY")`. `test_init_leaves_no_state_behind_after_a_failed_attempt` holds. New (A.U15.34):
  `test_a_restart_resets_the_output_filter` (filter 0.5 on, two samples stored, `_init_isl()` again: the next stored
  `Lux` equals that cycle's raw lux) and `test_an_edge_seen_before_a_restart_is_not_credited_after_it` (`_irq_fired =
  True`, `_init_isl()`, then a periodic-led switching cycle counts one periodic-only decision).
- **Resolved**: —
- **Unit**: U15 (stages U2 numbers, U3 console, U10 ladder).
- **Depends**: M.SRC_SENS.074, M.SRC_CORE.037.
- **Blast carried by**: SPEC M.1.2 restart table → A.U15.34 (SPEC).
- **Kind**: test

### M.TEST_UNIT.061 The read loop and the streak: ladder, give-up, pre-sync cycles
- **From**: A.U10.R01 + A.U15.R04 (`:953`, `:2539` re-derived; new participant-rung L1), A.U10.44 (`_read_loop`),
  A.U15.43 (the loop returns `None`), A.U2.06 + A.U3.03 (`:1056` comment; RF175 brownout entry), A.U10.35
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
    `code("W", "BUS_RECOVERY")`), and the log ends `code("E", "GIVE_UP")`; no streak entry per cycle.
  - `test_a_dark_room_never_increments_the_error_counter` and `test_brownout_does_not_feed_the_leaky_bucket…` call
    `set_utc_valid()` first (flag reset in `finally`): both call `_error_check(results)` directly, where a pre-sync
    `TS` would count. `:1056` → `assert errors(counters) == []  # a dark cycle is no failure; the streak itself only
    prints`. The brownout-bucket test adds: after the brownout cycle the log holds exactly one entry,
    `code("W", "ISL_BROWNOUT")` (A.U3.03 RF175).
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
- **Unit**: U15 (stages U3 console streak, U10 ladder/`_read_loop`/`TS`).
- **Depends**: M.SRC_SENS.075, .076, .083, M.SRC_CORE.032, .037.
- **Blast carried by**: the mid-operation re-apply case → M.TEST_UNIT in `test_bus_hazard_multi_device.py` (A.U15.R04,
  L1) and A.U15.R04 (TWIN); twin Run 5c holds → A.U15.R04 (SCR).
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
- **Depends**: M.SRC_SENS.072, .075, .077, .078, .081, .084.
- **Blast carried by**: `tests_scripts/test_measurement_field_tuple_agreement.py` → A.U24.57 (TSC); L2 dark/mid/bright
  `CalLight` → A.U15.36 (TWIN); `mockdata/dev.json` → A.U15.36 (WEB).
- **Kind**: test

### M.TEST_UNIT.063 Filter and store: the cached coefficient, the captured span
- **From**: A.U15.22 (3) (`:1127-1146` holds; `:1149-1175` goes; the store reads no config), A.U3.05 (`:1168`, gone
  with its test), A.U11.24 (`:1141` `write_config`), A.U24.61 (`:1141` `cfg_schema`), A.U36.506 (read: the `None`
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

### M.TEST_UNIT.064 The settle window: the bound's reason, a module `time`
- **From**: A.U15.22 (`:1291-1310` comment), A.U10.30 (`:1301, 1306` `__import__("time")`), A.U0.07.
- **Site**: `tests/test_asy_isl29125_driver.py:1269-1310`.
- **Change**: `:1292-1293` → "# The bound keeps the loop from starving; past it the cycle is discarded (see
  test_an_unsettled_cycle_is_no_failure)."; the four `__import__("time")` calls read the module-level `time`
  (`reader._isl._settle_until_ms = time.ticks_add(time.ticks_ms(), 500)`). `test_no_sample_is_reported_during_the_settle_window`
  holds (its `asyncio.sleep_ms` swap stays local and restored in `finally`; the shared `FastAsyncSleep` patches
  `sleep_ms` as HEAD's did).
- **Resolved**: —
- **Unit**: U10 (the dynamic import, A.U10.30) and U15 (the comment).
- **Depends**: M.SRC_SENS.079.
- **Blast carried by**: `tests_scripts/test_import_placement.py` `_PENDING` loses the two entries → A.U0.07 (TSC).
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
- **From**: A.U10.10 (`:3284`), A.U2.07 (`:3293` 4 → CFG_FILE_WRITE), A.U3.05 + A.U2.12 (`:3292` "12 not in"), A.U24.07
  (`:3280`).
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
  `_cancel_all` `:45-51`), A.U22.04 (`:12`, `:21` typing), A.U10.37/A.U10.38 (`crc_checks.CRC_Base`), A.U10.10 +
  GAP-17 lead ruling (AC_NOTES 38: `NeopixelDriver` gets an `initialized` gate), A.U5.02.
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
- **Depends**: M.SRC_SENS.021, .023, .024; TEST_HELP `tests/_driven_time.py` (A.U35.10), `tests/neopixel.py` (A.U24.25);
  the `initialized` gate on `NeopixelDriver` (GAP, see "Gaps for other clusters").
- **Blast carried by**: Part N `l1.asy_neopixel_driver_*` rows withdrawn → A.U35.13 (SPEC); the same IDs' other site
  `tests/test_neopixel_wifi_integration.py` → M.TEST_UNIT in that file (A.U8C.35 vs A.U35.13).
- **Kind**: test

### M.TEST_UNIT.079 Overlay and logger tests: private state, the gate, the FRAM-backed reboot
- **From**: A.U10.18 (`led_overl_lock` → `_overlay_lock`), A.U10.35/GAP-5 (`led_overl_on` → `_overlay_on`), A.U22.01
  (existing counts hold: one more frame per task start), A.U10.10 (`:453-464`), GAP-17 lead ruling, A.U5.02 (`:495`,
  `:504` `fram=` → `log=`), A.U16.19 (`:475`, `:479` `override_pause` goes), A.U11.S03 (hold: the `arg-type` ignore),
  A.U24.39 (`:667`), A.U35.13.
- **Site**: `tests/test_asy_neopixel_driver.py:54-177`, `:448-524`, `:648-674`.
- **Change**:
  - Overlay tests read `driver._overlay_on`, `driver._overlay_lock.locked()`; `:163-165` comment → "# request_signal()
    returns once the request is queued, not when the ramp ends; the task keeps the scenario reading top to bottom."
    (it pointed at a module docstring this file does not have). `test_repeated_on_is_idempotent…` holds (its count is
    relative to a snapshot taken after the tasks started).
  - `test_pr_setup_runs_before_any_ramp_is_committed` → `test_setup_initialises_the_logger_and_the_driver_before_any_task`:
    a driver built with `NeopixelDriver(0)` (no builder) has `pr.initialized is False` and `initialized is False`;
    `run(driver.setup()) is True`; both are `True` before any task starts (no task calls `pr.setup()` any more).
  - `_FakeFramChunk.write_into(buf)`/`read_into(buf)` lose `override_pause`; the reboot test builds
    `NeopixelDriver(0, log=LogConfig(fram, 10, None))` (the `arg-type` ignore and its reason stay) and calls
    `await driverN.setup()` in place of `pr.setup()` (the `:498-499` comment goes).
  - `test_get_task_starters_returns_three_callables` → `…returns_the_overlay_and_signal_starters`:
    `[s.__name__ for s in starters] == ["start_asy_overlay", "start_asy_signal"]`. `test_get_timer_starters…`'s
    vacuous `get_task_starters is not None` line goes.
  - `test_on_off_toggle_satisfy_led_control_protocol_signatures` → `test_on_off_toggle_drive_the_pixel_through_the_overlay_task`
    (A.U24.39): with the tasks started under driven time, `on()` records the overlay colour, `off()` `(0, 0, 0)`,
    `toggle()` the overlay colour again.
- **Resolved**: A.U10.10's "`pr.initialized` after task start → after `setup()`" and the GAP-17 gate land in one test.
- **Unit**: U10 (stages U5 `log=`, U16 fake keyword, U24 assertion).
- **Depends**: M.SRC_SENS.023, .024, .025; M.SRC_CORE.090 (`get_chunk()`'s parameters, which the fake manager mirrors).
- **Blast carried by**: per-class readiness L1 → M.TEST_UNIT in `tests/test_readiness_gates.py` (A.U10.22).
- **Kind**: test

### M.TEST_UNIT.080 Signal arbitration: refused at once while busy, a bounded internal wait
- **From**: A.U9.02 (`:333-346` holds, comment; `:348-372` flips; `:319-331`, `:374-402`, `:409-423` hold; new L1), A.U9.04
  (`:229-264` hold; new deadline L1), A.U9.05 (`:185-312`, `:425-446` hold; new cancel L1), A.U22.01 (new restart L1
  (1)-(3)), A.U35.13 (`:290` "needs real time", `:305`, `:395`).
- **Site**: `tests/test_asy_neopixel_driver.py:180-446`; new tests after `:446`.
- **Change**:
  - `:337-338` comment → "# No task started: led_signal() decides on _start_signal_event alone, with no await."
  - `test_led_signal_returns_true_while_a_previous_request_is_already_animating` →
    `test_led_signal_is_refused_at_once_while_a_ramp_runs_and_nothing_is_queued`: mid-ramp
    `driver._start_signal_event.is_set()`, `led_signal(0, 10, 0, 0.1) is False`, and after the ramp no frame with a
    green component exists; its `:349-355` comment block → "# The busy signal is _start_signal_event, set for the
    whole ramp; an external request while it is set is refused, never queued." The `start_signal_lock`/
    `ext_start_signal` asserts go.
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
- **Unit**: U9 (stages U22 restart cases, U35 driven time).
- **Depends**: M.SRC_SENS.026, .027, .028, .025; M.SRC_CORE (supervisor task-ended code, A.U3.06).
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
- **Depends**: M.SRC_SENS.022; TEST_HELP `tests/neopixel.py` (A.U24.25).
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
  `asy_base_classes.JsonDict` and drops `Coroutine`/`Any`/`TypeVar`/`T`/`NoReturn`. `_FakeTime` stays; `_FakeValue(value:
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
  (`:665-686` breaks the real config store), A.U22.02/A.U23.37 (`:682` goes), A.U9.10 (`:689-693` stays), A.U10.10.
- **Site**: `tests/test_asy_notification_service.py:592-720`.
- **Change**: the in-scenario `pr.setup()` lines go (the builder ran `setup()`).
  `test_signal_value_failure_and_own_time_callback_failure_share_one_history`: `ErrCount == 2`, the ring holds
  `code("E", "SOURCE")` then `code("E", "CALLBACK")`. `test_check_one_degrades_and_logs_when_the_threshold_config_cannot_be_read`
  → `…threshold_config_cannot_be_read_logs_in_the_config_store`: the patched `get_float_values` goes; the test pops
  `"WarnCO2"` from `service.cfgmgr._cache` (a missing key in the real store); `_check_one()` is `False`; the NOTIFY log
  is empty; `CFGMGR_NOTIFY` holds one `code("E", "CONTRACT")`; `:682` goes. `test_two_signals_failures_share_one_errno…`
  → `…share_one_code_and_one_slot`: `ErrCount == 2`, the newest entry `code("E", "SOURCE")` and one slot for both
  (the names are in the console lines). `test_the_defaulted_signal_sink…` holds.
- **Resolved**: —
- **Unit**: U3 (stages U2 codes, U22 attribute removal).
- **Depends**: M.SRC_SENS.034, .035; M.SRC_CORE (`_get_values()` → CONTRACT on a `KeyError`).
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
- **Depends**: M.SRC_SENS.036; M.SRC_CORE `TickSeconds` (A.U10.02).
- **Blast carried by**: twin `:349-390` and bench `:115-141` → A.U9.09 (TWIN, HW_BENCH).
- **Kind**: test

### M.TEST_UNIT.091 Own-config read failures print; the next sleep in milliseconds
- **From**: A.U3.05 + A.U3.02 (`:1350-1407` rewritten: the store logs, NOTIFY prints), A.U31.14 (`:1256-1279`
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
  (shared, both sleeps): `…persists_one_slot` asserts the task still runs, the NOTIFY log is empty, and
  `CFGMGR_NOTIFY` has `ErrCount > 5` with exactly one `code("E", "CONTRACT")` in its ring; `…persists_the_config_read_warning_afresh_after_a_good_read`
  → `test_monitor_loop_config_failures_before_and_after_a_good_read_share_one_slot` (the store's ring holds one
  CONTRACT entry, `ErrCount` counts both runs; the HEAD "afresh" claim is retired by the newest-entry rule, OR35.b);
  `…self_heals_in_place…` calls `set_utc_valid()` first (flag reset in `finally`) so `ts_after is not None` still
  proves a stored cycle.
- **Resolved**: A.U8C2.02's `next_sleep_min_s = 59.0` follows A.U31.14's millisecond return: the constant and its row ID
  take the ms unit (A.U10.43's suffix rule) — agent decision, OR2.c list.
- **Unit**: U31 (stages U3 log path, U8 tags, U10 sync).
- **Depends**: M.SRC_SENS.034, .037; M.SRC_CORE.032.
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
