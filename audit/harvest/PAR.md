# Harvest — PAR: Legacy parity and field migration

What the project's own comments, docs and history already record for this area (snapshot `2a88cc8`).
Recorded, not verified or triaged; `audit/HARVEST.md` explains the kinds, tags and method.

Kinds: SETTLED 31, INVAR 95, MIRROR 12, LIMIT 44, RISK 13, ASSUME 22, PLATFORM 11, WORKAROUND 1, SUPPRESS 1, TODO 2, OPENQ 1, DRIFT 14, NOTE 11 — 258 items.


## src/api_response.py

- **PAR.N001** NOTE(PAR) · `src/api_response.py:36-38` — "generalizes the legacy special_err closed
  Literal enum into an open set, same envelope shape" — Claims envelope shape parity with legacy
  `api_helpers.py`'s `special_err`. · related: PAR.T11 · [H01]

## src/asy_neopixel_driver.py

- **PAR.N002** NOTE(PAR) · `src/asy_neopixel_driver.py:3` — "proven arbitration mechanism" — Claims the
  arbitration is the field-proven legacy mechanism (legacy `neopixel_signal.py`). · related: LED.T01 ·
  [H01]

## src/asy_notification_service.py

- **PAR.N003** NOTE(PAR) · `src/asy_notification_service.py:70` — "Ranges/defaults mirror the legacy
  REST handler's own already-validated bounds." — Claimed legacy parity of
  OnH/OnM/OffH/OffM/FlashBri/Interv/FlashDur bounds and defaults. · related: PAR.T01 · [H01]

## src/asy_ntp_client.py

- **PAR.N004** NOTE(PAR) · `src/asy_ntp_client.py:63-64` — "min/max mirror the already-validated bounds
  the deployed, pre-refactor REST handler uses" — Claimed legacy parity of NTP field bounds (NTP_Host
  3..1024 etc.). · related: PAR.T01, NET.S14 · [H01]

## src/asy_scd30_driver.py

- **PAR.N005** NOTE(PAR) · `src/asy_scd30_driver.py:596-598` — "If not ready, leaves the cache
  untouched, matching the legacy driver." — Legacy-identical stale-cache behaviour. · covered-by:
  SENS.S08 · [H01]

## src/asy_sgp40_driver.py

- **PAR.N006** NOTE(PAR) · `src/asy_sgp40_driver.py:64` — "special:0=\"Never wait for NTP sync\"" — UI
  label implies legacy meaning; code disables restore instead. · covered-by: PAR.S01 · [H01]
- **PAR.N007** NOTE(PAR) · `src/asy_sgp40_driver.py:666-667` — "the feature-set check the legacy driver
  had isn't datasheet-documented" — Deliberate removal of a legacy check. · related: PAR.T01 · [H01]

## src/asy_uart_comm.py

- **PAR.N008** MIRROR · `src/asy_uart_comm.py:869-870` — "one right-sized copy, against the legacy's 254
  reallocations and its ~2x peak at the final concatenation" — Stated improvement over legacy allocation
  behaviour (low) · [H02]

## src/asy_uart_driver.py

- **PAR.N009** MIRROR · `src/asy_uart_driver.py:398-399` — "No CRC framing here... matching the original
  driver's own scope." — readline scope kept identical to the legacy driver (low) · [H02]

## src/asy_webserver_service.py

- **PAR.N010** MIRROR · `src/asy_webserver_service.py:550-552` — "legacy rejected an out-of-range
  pauseTime as Invalid - so reject it here too" — Legacy-parity statement for PauseTime validation ·
  related: REST.S10 · [H02]

## src/base_classes.py

- **PAR.N011** MIRROR · `src/base_classes.py:374-375` — "mirrors legacy's own cmd_keys exclusion from
  this exact fallback chain" — Legacy-parity statement · related: PAR.T01 · [H02]

## src/math_helpers.py

- **PAR.N012** MIRROR · `src/math_helpers.py:207-209` — "promoted from the legacy SHTC3/MPRLS readers. A
  coefficient outside (0, 1] means \"filter off\", the convention FiltCoeff = -1.0 relies on." —
  Legacy-derived EMA; `FiltCoeff = -1.0` config convention depends on this range test · related:
  ALGO.T01 · [H02]

## tests/_sensortask_scenarios.py

- **PAR.N013** NOTE(PAR) · `tests/_sensortask_scenarios.py:1043-1066` — "legacy's led_cmd() rejects
  out-of-range r/g/b (0-255) ... Legacy's own t bound is 0.5-60.0" — parity bounds for `lightCmdLED`
  pinned against legacy behaviour · [H03]

## tests/test_asy_bmp3xx_driver.py

- **PAR.N014** NOTE(PAR) · `tests/test_asy_bmp3xx_driver.py:887` — "int(45.7) == 45, same truncation as
  the original driver" — float trigger seconds truncate, kept for legacy parity · [H03]
- **PAR.N015** MIRROR · `tests/test_asy_bmp3xx_driver.py:900-902` — "Bound is 1-3600 seconds, matching
  the deployed production validation for this exact field (modules/sensortask-wozi.py's BMPSampleInterv
  bounds" — bound mirrored from legacy · [H03]

## tests/test_asy_fram_driver.py

- **PAR.N016** NOTE(PAR) · `tests/test_asy_fram_driver.py:90-92` — "the legacy check was `manf_wrong AND prod_wrong`,
  so a correct manufacturer byte alone made the whole check pass" — legacy field firmware accepts a
  wrong/corrupted FRAM product ID · [H03]

## tests/test_asy_neopixel_driver.py

- **PAR.N017** PLATFORM · `tests/test_asy_neopixel_driver.py:282-284` — "int(0.1 * 0.5 * 1) == 0 without
  an explicit steps>=1 clamp - a real ZeroDivisionError risk in the original code" — legacy defect the
  promoted driver clamps · [H03]

## tests/test_asy_uart_comm.py

- **PAR.N018** LIMIT · `tests/test_asy_uart_comm.py:2159-2161` — "the deployed rxbuf of 32 clears J.6's
  27-byte whole-frame floor but not its 80-byte per-poll floor" — a legacy-faithful port must raise
  rxbuf; everything else legacy declared (115200, 1000 ms, payload 20, CRC16) is accepted unchanged
  (:2171-2172) · related: UART.S04 · [H04]

## tests/test_base_classes.py

- **PAR.N019** MIRROR · `tests/test_base_classes.py:1405-1407` — "Mirrors legacy's cmd_keys exclusion
  from the getter/config/default fallback chain" — Command-only fields are skipped in push-failure
  recovery, matching legacy cmd_keys · [H05]
- **PAR.N020** MIRROR · `tests/test_base_classes.py:1641-1642` — "matching the legacy pipeline's own
  default (set_sensor_value only pushes on prev_updated or force=True)" — Unchanged value is a hardware
  no-op, claimed to match legacy · [H05]

## dev_legacy/README.md

- **PAR.N021** LIMIT · `dev_legacy/README.md:667-678` — "`sensortask-dev.py` itself is
  stale/non-functional as captured" — Snapshot (MicroPython 1.24.1, 2026-08-27) is unreviewed reference;
  `sensortask_test.py` "more internally-consistent". · related: PAR.S14 · [H08]

## dev_legacy/*.py (reference-only 2026-08-27 on-device snapshot, MicroPython 1.24.1 — plan §2.2; field/bench behaviour only)

- **PAR.N022** TODO · `dev_legacy/asy_scd30_driver.py:35` — "# TODO: Stop Measurement command" — Legacy
  snapshot TODO (reference only, never actioned here). · - (low) · [H08]
- **PAR.N023** PLATFORM · `dev_legacy/async_connect.py:388` — "try to reconnect once after hotspot time
  if no client connected (maybe router reboot after power loss)" — Legacy hotspot timer was ONE_SHOT
  (:384-386); refactor now PERIODIC (handover :42). · related: NET.T01 (low) · [H08]
- **PAR.N024** PLATFORM · `dev_legacy/async_connect.py:529` — "getaddrinfo may block for some time" —
  Legacy held a long-block lock around `getaddrinfo` (F.2's un-timeout-able call). · - (low) · [H08]
- **PAR.N025** ASSUME · `dev_legacy/system_service.py:11, 15` — "_RESET_DELAY = const(4) # seconds
  between reset command and execution (keep < watchdog timeout!)" — Dev-bench snapshot already had 4 s
  reset delay and 2 s task check, while `dev_legacy/sensortask-dev.py:25` still has `_TASK_CHECK_TIME = const(5)`
  — relevant to which legacy supervisor timing PAR.S04 compares against. · related: PAR.S04 (low) ·
  [H08]
- **PAR.N026** ASSUME · `dev_legacy/sensortask-dev.py:122` — "#watchdog = WDT(timeout = 8000)" — Legacy
  dev bench ran without a watchdog (also `sensortask_test.py:24`). · - (low) · [H08]
- **PAR.N027** ASSUME · `dev_legacy/asy_uart.py, dev_legacy/asy_uart_comm.py` — "# Message format:
  [UID][CMD][SIZE][CHUNKS][CUR_CHUNK][...Payload...]" — Both files byte-identical to
  `python/IndividualDrivers/` copies: the dev bench ran the deployed UART protocol version
  (asy_uart_comm.py:21). · - (low) · [H08]
- **PAR.N028** ASSUME · `dev_legacy/microdot.py:1-7` — "servers for MicroPython and standard Python." —
  A third Microdot snapshot (1,494 lines) distinct from `python/CommonDrivers/microdot.py` (1,445) and
  `ext/microdot.py` (1,570). · related: PAR.T11 (low) · [H08]
- **PAR.N029** SUPPRESS · `dev_legacy/*.py (12 sites)` — "# type: ignore[call-arg]" — 12 `type: ignore[...]`
  (asy_bmp3xx_driver.py:168, asy_fram_manager.py:449, 503, asy_scd30_driver.py:141,
  asy_sgp40_driver.py:282, asy_spi_driver.py:44, asy_udp_socket.py:40, async_connect.py:19, 247, 648,
  651, system_service.py:121), 2 `pylint: disable` (asy_sgp40_driver.py:504, voc_algorithm.py:43), 1
  `noinspection` (asy_spi_driver.py:43); directory is outside every lint scope by design. · - (low) ·
  [H08]

## devices/wozi.toml

- **PAR.N030** ASSUME · `devices/wozi.toml:1-3` — "The source of truth buildgen reads" — Unlike the four
  field TOMLs, no legacy wiring source is cited for wozi's pins. (low) · related: PAR.T02 · [H09]

## devices/arzi.toml

- **PAR.N031** MIRROR · `devices/arzi.toml:1-2` — "distinct wiring from the \"neu\" family ... Wiring
  sourced from modules/sensortask-arzi.py (legacy, read-only reference)." — Pin parity with the legacy
  module. · covered-by: PAR.T02 · [H09]

## devices/klkizi.toml

- **PAR.N032** ASSUME · `devices/klkizi.toml:1-3` — "one of three \"ArZi neu\" units (own file for
  expected future hardware divergence from grkizi/schlafzi) ... Wiring sourced from
  modules/sensortask-neu.py" — Three byte-identical-except-name files anticipate divergence; pins mirror
  legacy `sensortask-neu.py`. · covered-by: PAR.T13 · [H09]

## devices/grkizi.toml

- **PAR.N033** ASSUME · `devices/grkizi.toml:1-3` — "one of three \"ArZi neu\" units (own file for
  expected future hardware divergence from klkizi/schlafzi)" — Identical to klkizi except name/hostname.
  · covered-by: PAR.T13 · [H09]

## devices/schlafzi.toml

- **PAR.N034** ASSUME · `devices/schlafzi.toml:1-3` — "one of three \"ArZi neu\" units (own file for
  expected future hardware divergence from klkizi/grkizi)" — Identical to klkizi except name/hostname. ·
  covered-by: PAR.T13 · [H09]

## SPECIFICATION.md Part A.1 (Repository layout, 29-92)

- **PAR.N035** ASSUME · `SPECIFICATION.md:42-44` — "Legacy, still-deployed ... superseded by html/ for
  devices the refactor has reached (H.1)" — Which devices the refactor has "reached" is unstated;
  deployed units still run html_raw. · related: PAR.T10 · [H12]
- **PAR.N036** DRIFT · `SPECIFICATION.md:47-49` — "sensortask-{arzi,dev,neu,wozi}.py per-device app" —
  Legacy has 4 device apps (incl. `neu`), refactor has 6 TOMLs; the neu→klkizi/grkizi/schlafzi mapping
  is not stated here. (low) · related: PAR.T02 · [H12]

## SPECIFICATION.md Part A.2 (Architecture at a glance, 94-127)

- **PAR.N037** RISK · `SPECIFICATION.md:102-104` — "self-heals corruption by overwriting the entire file
  with hardcoded defaults (data-loss risk on firmware upgrades that add keys — BACKLOG.md)" — Deployed
  ConfigManager's known data-loss risk; relevant to reflash migration. · related: PAR.S08 · [H12]

## SPECIFICATION.md Part A.3 (Refactor status, 129-146)

- **PAR.N038** SETTLED · `SPECIFICATION.md:145-146` — "Goal throughout: same top-level features as
  today's deployed units, not a feature change." — Parity goal the PAR area audits against. · related:
  PAR.T01 · [H12]

## SPECIFICATION.md Part A.4 (Architecture — deep reference, 148-285)

- **PAR.N039** SETTLED · `SPECIFICATION.md:152-155` — "exposes `get_long_block_lock()` ... `src/` splits
  this ... and retires the lock (F.2)" — Retired legacy lock; must not be reintroduced. · [H12]
- **PAR.N040** SETTLED · `SPECIFICATION.md:263-265` — "Config field names drop the \"Led\" prefix
  everywhere ... a deliberate wire-format change; only legacy `html_raw/` isn't updated (accepted debt,
  H.1)" — Wire change deliberate; legacy UI incompatible by accepted debt. · related: PAR.S06 · [H12]
- **PAR.N041** SETTLED · `SPECIFICATION.md:269-285` — "Functional behaviors confirmed intentional by the
  project owner — don't \"fix\" these" — Do-not-reopen list (LED sequencing, BackupPeriod/BackupMaxAge
  0=disabled, permanent WiFi deactivation, no STA→hotspot after first success, raw-number UI, SGP40 skip
  without SCD30 comp, no UART flow control, no midnight-wrap window, SCD30 AmbPres readback). ·
  covered-by: PAR.T03 · [H12]

## SPECIFICATION.md Part A.5 (Microdot / REST layer, 287-335)

- **PAR.N042** DRIFT · `SPECIFICATION.md:332-335` — "one drift: its `HTTPException` branch invokes a
  status-code handler directly ... irrelevant today since neither app registers handlers there" —
  Understates legacy/vendored gap: CLAUDE.md records the deployed copy as a pre-v2.1.0 snapshot ~441
  lines behind. (low) · related: PAR.T11 · [H12]

## SPECIFICATION.md Part B.14.3 (`littlefs_flash_storage_size`, 1381-1410)

- **PAR.N043** PLATFORM · `SPECIFICATION.md:1391-1397` — "`set(MICROPY_HW_FLASH_STORAGE_BYTES 868352) endif()`
  (848KB; `mpconfigport.h`'s own generic rp2 default ... `1408 * 1024`" — littlefs size facts relevant
  to the 1.26 → 1.29 reflash. · covered-by: PAR.S10 · [H12]
- **PAR.N044** RISK · `SPECIFICATION.md:1405-1410` — "shrinking the reserved littlefs region changes the
  on-flash layout of a board that may already have deployed units carrying real persisted state" —
  Real-hardware data risk. · related: PAR.T06 · [H12]

## SPECIFICATION.md Part C.5 / C.5.1-C.5.3 (Config schema system, 1699-1797)

- **PAR.N045** SETTLED · `SPECIFICATION.md:1790-1792` — "every bool field is native JSON `true`/`false`,
  replacing legacy's `\"On\"`/`\"Off\"` string dtype. Only legacy `html_raw/` isn't updated (H.1)." —
  Deliberate wire change. · related: PAR.S06 · [H12]

## SPECIFICATION.md Part F.5 — MicroPython 1.29 delta (intro)

- **PAR.N046** OPENQ · `SPECIFICATION.md:3672` — "Deployed units stay on 1.26 regardless (BACKLOG open
  question 3)" — Field migration to 1.29 is an open question held in BACKLOG. · related: PAR.T11,
  PAR.T14 · [H13]

## SPECIFICATION.md Part H.1 — Website purpose and constraints

- **PAR.N047** SETTLED · `SPECIFICATION.md:4273-4276` — "`html_raw/{general,arzi,dev,wozi}` is the
  legacy, still-deployed site ... This Part's website targets the refactored REST shape from the start —
  not a reskin." — Legacy site is reference; new site speaks only the new REST shape. · related: PAR.T10
  · [H13]

## SPECIFICATION.md Part I.6 — Request-body cap (sits inside Part J)

- **PAR.N048** MIRROR · `SPECIFICATION.md:5290-5292` — "mirrors the deployed pre-refactor handler
  (`modules/sensortask-*.py`'s `update_valid_json(..., 3, 1024, ...)`)" — Legacy ↔ refactor bound
  parity. · related: PAR.T01 · [H13]

## SPECIFICATION.md Part J.8 — Memory model

- **PAR.N049** LIMIT · `SPECIFICATION.md:5611-5617` — "the receiver grows `res` by `+=` across the whole
  train (254 reallocations and a ~2× peak at the final copy for a maximum 12192-byte transfer" — Legacy
  behaviour the refactor replaced (parity/migration context). · [H13]

## SPECIFICATION.md Part M (intro) and M.1 — ISL29125

- **PAR.N050** SETTLED · `SPECIFICATION.md:6581-6584` — "CLAUDE.md's rule to verify a driver against the
  legacy driver's field-proven behaviour **has no purchase here** ... (owner)" — Legacy ISL29125 parity
  explicitly not a reference. · [H13]

## CLAUDE.md

- **PAR.N051** SETTLED · `CLAUDE.md:92-101` — "Do not \"fix\" `modules/_boot.py`'s `import sensortask.py`"
  — A trace at 1.28/1.29 says the plain import is correct and the dotted one should raise. Units run
  1.26, never verified, so the rule stands. Convention only. · related: PAR.T09 · [H14]
- **PAR.N052** ASSUME · `CLAUDE.md:97-99` — "these units run 1.26, whose own import machinery was never
  separately verified and never will be" — Accepted unexplained behaviour: why the dotted import works
  on 1.26 stays unknown by decision. · related: PAR.T09 · [H14]
- **PAR.N053** SETTLED · `CLAUDE.md:102-104` — "`python/CommonDrivers/microdot.py` is vendored
  third-party code. Don't restyle or \"clean up\" it" — Changing it is a deliberate fork decision. ·
  [H14]
- **PAR.N054** ASSUME · `CLAUDE.md:104-110` — "*untagged snapshot between `v2.0.1` and `v2.1.0`* ...
  ~441 lines behind" — Dated comparison (2026-09-10). "Unmodified relative to that snapshot, as far as
  can be told" is inferred. · related: PAR.T11 · [H14]
- **PAR.N055** SETTLED · `CLAUDE.md:170-177` — "The legacy tree is reference-only, forever — it never
  gets work of any kind (project owner, 2026-09-11)" — `python/`, `modules/` and the four `build-*.sh`.
  Partly mechanical: lint.sh:13 (ruff scope) and :15-18 (shellcheck `scripts/*.sh` only) leave them out.
  · related: DOC.S21 · [H14]
- **PAR.N056** INVAR · `CLAUDE.md:447-448` — "verify against the legacy driver's own actually-proven
  field behavior" — Convention only. · covered-by: PAR.T12 · [H14]

## README.md

- **PAR.N057** ASSUME · `README.md:7-8` — "Code ships as frozen bytecode compiled into the MicroPython
  firmware, not loaded from the device filesystem at runtime" — Assumes nothing on littlefs shadows or
  pre-empts the frozen modules; legacy residue (`/html`, `main.py`, `*.py`) could. · related: PAR.T08,
  XCUT.S14 · [H14]

## BACKLOG.md

- **PAR.N058** SETTLED · `BACKLOG.md:165-176` — "mechanism answered; the file is never changed
  regardless." — #1 `modules/_boot.py`'s `import sensortask.py`: closed stub kept for CLAUDE.md and
  `test_reboot_persistence.py` citations. · related: PAR.T09 · [H15]
- **PAR.N059** ASSUME · `BACKLOG.md:171-174` — "Why it nonetheless works on the deployed 1.26 firmware
  was never verified ... and never will be" — Deployed autostart rests on an unexplained mechanism
  (1.28/1.29 trace says the dotted import should raise). · [H15]
- **PAR.N060** RISK · `BACKLOG.md:177-182` — "Decided: not patched on the current codebase — accepted
  (reconfigure via web UI after a key-adding update)." — #2 legacy ConfigManager can wipe WiFi
  credentials on a key-adding update; refactor claimed to avoid it "structurally". · related: PAR.S08,
  DOC.S13 · [H15]

## python/CommonDrivers/api_helpers.py

- **PAR.N061** INVAR · `python/CommonDrivers/api_helpers.py:160-183` — "# 0: Success, no error ... # 8:
  LED is busy ... # 10: Invalid or unknown system command" — Legacy wire error-code catalogue 0-10 (6
  unknown, 7 invalid LED cmd, 8 LED busy, 9 invalid pause time, 10 invalid system cmd); src
  `api_response._STANDARD_CODES` keeps 0-5 and adds 100 "Generic command error", codes 6-10 gone ·
  related: PAR.T11, REST.S09 · [H16]
- **PAR.N062** DRIFT · `python/CommonDrivers/api_helpers.py:129,136` — "Invalid JSON Request" /
  okDescr="Command exectuted" — Legacy wire `descr` strings differ from src (`"Invalid JSON request"`,
  `"Command executed"`, src/api_response.py:40-41) — a client matching on descr text sees a change (low)
  · related: PAR.T11 · [H16]
- **PAR.N063** SETTLED · `python/CommonDrivers/api_helpers.py:33,42-45` — "an empty input (\"\") will be
  considered as valid value for \"don't change\"." — Legacy PUT semantics: `""` for any key means
  "Unchanged" (no write); refactor gives `""` real meaning for some keys (e.g. `PW` = open network) ·
  related: NET.S17, PAR.S06 · [H16]
- **PAR.N064** LIMIT · `python/CommonDrivers/api_helpers.py:38-41` — "json_validity[json_key] =
  \"Invalid\"" (key not in request) — Legacy per-key validation marks every absent key "Invalid"
  (non-sparse PUT; clients sent every field), contrast with the refactor's sparse PUT · related: PAR.S06
  · [H16]
- **PAR.N065** INVAR · `python/CommonDrivers/api_helpers.py:90-99` — "if state_val == \"On\": val = True
  elif state_val == \"Off\"" — Legacy wire booleans are the strings "On"/"Off" (`toSwitch()` :119-120 on
  GET); refactor uses native JSON bool · covered-by: PAR.S06 · [H16]
- **PAR.N066** SETTLED · `python/CommonDrivers/api_helpers.py:102-114` — "if val ==
  dst_json_value[json_key]: ... \"Unchanged\"" — Legacy skipped both the flash save and the setter when
  the value equalled the stored one; only a changed storage key set `any_set` (flash write);
  command-only keys never trigger a save · related: PAR.S02, SENS.T07 · [H16]
- **PAR.N067** LIMIT · `python/CommonDrivers/api_helpers.py:66-75` — "except ValueError:" — int/float
  coercion catches only ValueError: a JSON `null`/list/object raises TypeError out of the handler
  (Microdot 500), and `int(1.9)` silently truncates to 1 (low) · related: PAR.T11 · [H16]
- **PAR.N068** LIMIT · `python/CommonDrivers/api_helpers.py:47-53` — "val = str(json_in[json_key])" —
  Any JSON value (number, bool) is accepted for a "str" field via `str()`; the ValueError branch is
  unreachable (low) · related: NET.T07 · [H16]
- **PAR.N069** SETTLED · `python/CommonDrivers/api_helpers.py:185-221` — "in case of sensor update
  errors, try to load values from sensor ... If this also fails, take default value." — Legacy
  sensor-setter fallback chain: setter fails → "Failed", then read back from sensor, then from
  config.json, then `default`; `force` re-applies even unchanged values (SCD30 AmbPres) · related:
  PAR.S02, SENS.T07 · [H16]
- **PAR.N070** INVAR · `python/CommonDrivers/api_helpers.py:146-149` — "dst_json_value.pop(key, None) #
  ignore for saving, but keep validity result" — Command-only keys are stripped before `write_config`,
  so they never persist · related: PAR.T01 · [H16]
- **PAR.N071** LIMIT · `python/CommonDrivers/api_helpers.py:124-127` — "except: req_json = None" — Any
  body-parse failure (bare except) maps to code 1 · related: PAR.T11 · [H16]

## python/CommonDrivers/asy_udp_socket.py

- **PAR.N072** ASSUME · `python/CommonDrivers/asy_udp_socket.py:1-5` — "no formal LICENSE in that repo,
  but treated as the author's own public offer of the code" — Attribution/licence assumption for the
  karfas AsyUDPClient-derived shape, inherited by `src/asy_udp_socket.py` · related: LIC · [H16]
- **PAR.N073** LIMIT · `python/CommonDrivers/asy_udp_socket.py:13,29-42` — "conn_tries=1" / "except
  Exception as e: tries += 1; await asyncio.sleep(0.5)" — Legacy connect/bind is attempted once by
  default, errors swallowed silently; since `self.sock` stays non-None, a failed bind is never retried
  and `ready()` returns False forever · related: NET (src/asy_udp_socket.py retry/degrade) · [H16]
  ⟨quote not matched at the anchor⟩
- **PAR.N074** LIMIT · `python/CommonDrivers/asy_udp_socket.py:44-56` — "if (timeout_ms > 0) and ...
  await asyncio.sleep(wait_time_ms)" — `ready()` spins on `ipoll(0)` with `sleep(0)` (busy-yield) and
  `timeout_ms<=0` waits forever · related: PERF · [H16]
- **PAR.N075** LIMIT · `python/CommonDrivers/asy_udp_socket.py:73-77` — "for _ in range(tries): ...
  return await self.recvfrom(" — `write_and_recvfrom(tries=N)` returns after the first iteration:
  retries never happen (low) · related: NET · [H16]
- **PAR.N076** PLATFORM · `python/CommonDrivers/asy_udp_socket.py:24` — "SO_REUSEADDR, 1" — Legacy sets
  SO_REUSEADDR on every UDP socket (the refactor's captive DNS relies on the same) · related: NET ·
  [H16]

## python/CommonDrivers/captive_dns.py

- **PAR.N077** SETTLED · `python/CommonDrivers/captive_dns.py:1-5` — "SPDX-FileCopyrightText: Copyright
  2019 p-doyle ... see src/LICENSE-captive_dns" — Apache-2.0 derivative attribution; the referenced
  `src/LICENSE-captive_dns` exists at the snapshot · related: LIC · [H16]
- **PAR.N078** LIMIT · `python/CommonDrivers/captive_dns.py:13,20,35-37` — "except Exception as e: ...
  await asyncio.sleep(3)" — Legacy captive DNS binds 0.0.0.0:53 once; on a failed bind `recvfrom`
  returns (None, None), `DNSQuery(None)` raises and the loop sleeps 3 s forever (silent dead DNS) ·
  related: NET (src captive_dns/asy_udp_socket degrade) · [H16]
- **PAR.N079** INVAR · `python/CommonDrivers/captive_dns.py:47-55,59-67` — "tipo = (data[2] >> 3) & 15 #
  Opcode bits" / "if self.domain:" — Only opcode-0 queries are answered; every standard query of any
  QTYPE gets one A record pointing at the AP IP, ANCOUNT=QDCOUNT, flags 0x8180, TTL 0x3C (60 s) ·
  related: NET · [H16]
- **PAR.N080** LIMIT · `python/CommonDrivers/captive_dns.py:62` — "packet += self.data[12:] # Original
  Domain Name Question" — The whole query tail (incl. any EDNS/additional records) is echoed before the
  answer while ARCOUNT is zeroed — malformed reply for EDNS queries (low) · related: NET · [H16]
- **PAR.N081** LIMIT · `python/CommonDrivers/captive_dns.py:20` — "await self.udps.recvfrom(4096)" —
  Receive buffer 4096 bytes per query (heap allocation per request) · related: MEM · [H16]

## python/CommonDrivers/math_helpers.py

- **PAR.N082** INVAR · `python/CommonDrivers/math_helpers.py:7` — "if (-20.0 <= temperature <= 50.0) and
  (0.5 <= humidity <= 99.0):" — Legacy wet-bulb (Stull) validity window −20..50 °C, 0.5..99 %RH, else
  None · related: ALGO (src/math_helpers.py:50) · [H16]
- **PAR.N083** INVAR · `python/CommonDrivers/math_helpers.py:21-28` — "(-40.0 <= temperature <= 50.0)
  and (0.1 <= humidity <= 100.0)" — Legacy dew point window and Magnus coefficient pairs (243.04/17.625
  water, 272.62/22.46 ice) · related: ALGO (src/math_helpers.py:66-76) · [H16]
- **PAR.N084** DRIFT · `python/CommonDrivers/math_helpers.py:33-37` — "def altitude_baro(p0, dh, tmean):
  return p0 * math.exp(" — Named altitude but returns a pressure (barometric formula) — legacy-identical
  naming carried into src · covered-by: ALGO.S03 · [H16] ⟨quote not matched at the anchor⟩
- **PAR.N085** ASSUME · `python/CommonDrivers/math_helpers.py:43-49` — "a = 7.6 b = 240.7" — Below 0 °C
  uses 7.6/240.7 (supercooled-water pair, not ice 9.5/265.5); window −30..40 °C · covered-by: ALGO.S03 ·
  [H16]
- **PAR.N086** LIMIT · `python/CommonDrivers/math_helpers.py:57-66` — "if (-30.0 <= temperature <=
  40.0): ... if rh > 100.0: rh = 100.0" — Legacy `rel_humidity` range-checks temperature only and clamps
  RH to 0..100; src additionally bounds `abs_hum` (src/math_helpers.py:125) (low) · related: ALGO.S05 ·
  [H16]

## python/CommonDrivers/system_service.py

- **PAR.N087** INVAR · `python/CommonDrivers/system_service.py:8-10` — "_RESET_DELAY = const(5) ...
  _MAX_STORAGE_PAUSE = const(3600) ... _NTP_WAIT_TIME = const(120)" — Legacy reboot delay 5 s (src 4 s,
  src/system_service.py:40), storage pause cap 1 h, random boot signature after 120 s without NTP ·
  covered-by: PAR.S04 · [H16]
- **PAR.N088** SETTLED · `python/CommonDrivers/system_service.py:35-51` — "self.storage_pause(True) ...
  self.reset_timer.init(period=_RESET_DELAY * 1000, mode=Timer.ONE_SHOT, callback=lambda b:
  SystemReset())" — Legacy reboot/bootloader: pause FRAM storage first, then reset from a one-shot Timer
  callback after 5 s · related: PAR.S04, CORE · [H16]
- **PAR.N089** INVAR · `python/CommonDrivers/system_service.py:53-67` — "if duration <= 0: duration = 0
  elif duration > _MAX_STORAGE_PAUSE:" — Storage pause clamped to 0..3600 s; 0 unpauses immediately;
  expiry via one-shot Timer · related: STOR · [H16]
- **PAR.N090** INVAR · `python/CommonDrivers/system_service.py:72,78,85-92` — "UTC timestamp if NTP
  synced, random number otherwise after wait time" / "set_data([-1])" — Legacy boot signature is −1
  until resolved (src: None, src/system_service.py:271), then NTP UTC timestamp or `getrandbits(32)`
  after 120 s · related: PAR.T01 · [H16]
- **PAR.N091** PLATFORM · `python/CommonDrivers/system_service.py:18-20,30` — "self.uptime_timer =
  Timer()" / "period=1000, mode=Timer.PERIODIC, callback=lambda b: self.uptime_event.set()" — Legacy
  uptime is driven by a 1 s soft Timer → ThreadSafeFlag (ticks collapse if the loop is slow; same
  pattern in src) · related: NET.S02, PLAT · [H16]

## python/CommonDrivers/async_manager.py

- **PAR.N092** INVAR · `python/CommonDrivers/async_manager.py:6,22-27` — "_50_YEARS_SEC =
  const(1576800000) # seconds of 50 years(!!) perfectly fits into 32bit signed" — Legacy counters
  (uptime, WiFi uptime, last NTP sync) saturate at 50 years instead of wrapping · related: CORE · [H16]
- **PAR.N093** RISK · `python/CommonDrivers/async_manager.py:115-129` — "if not key in data: ...
  valid_config = False" → "json.dump(default_config, f)" — Legacy `ConfigManager`: invalid JSON or ANY
  missing key overwrites the whole `config.json` with defaults — a firmware adding a key wipes WiFi and
  all settings · related: PAR.S08, PAR.T06 · [H16]
- **PAR.N094** RISK · `python/CommonDrivers/async_manager.py:126-127,178-179` — "with
  open(self.config_file, \"w\") as f: json.dump(" — Legacy config writes are in-place, non-atomic (no
  temp+rename): a power loss mid-write leaves invalid JSON → defaults on next boot · related: CORE,
  PAR.T06 · [H16]
- **PAR.N095** LIMIT · `python/CommonDrivers/async_manager.py:133-149` — "with open(self.config_file,
  \"r\") as f: data = json.load(f)" — Every legacy config read opens and parses the whole single
  `config.json` (no cache); every write re-reads, merges, rewrites it · related: PAR.T06 · [H16]
- **PAR.N096** INVAR · `python/CommonDrivers/async_manager.py:172-177` — "if self.debug: print(\"Config
  data key error.\"); return False" — `write_config` refuses the whole write if any key is unknown to
  the stored file · related: CORE · [H16]
- **PAR.N097** LIMIT · `python/CommonDrivers/async_manager.py:81-90` — "return [self.default] * length"
  — `DataManager.get_data` with an invalid range returns `[default]*length` (empty list when
  `length=-1`) (low) · related: CORE · [H16]

## python/CommonDrivers/async_connect.py

- **PAR.N098** INVAR · `python/CommonDrivers/async_connect.py:12-16` — "_NTP_ASYNC_INTERV = const(3) ...
  _NTP_CHECK_INTERV = const(10) ... _NTP_CONN_TIMEOUT = const(5000) ... _NTP_SYNC_RETRIES = const(3) ...
  _NTP_RETRY_INTERV = const(15)" — Legacy NTP timing: 10 s check tick, 5 s per send/receive, 3 retries
  15 s apart, "stale" after 3× interval · related: PAR.T04, NET.S03 · [H16]
- **PAR.N099** INVAR · `python/CommonDrivers/async_connect.py:19,25` — "conn_fail_to_hotspot=5, ...
  wifi_refresh_sec=5, hotspot_time_min=5" — Legacy WiFi defaults: 5 failed attempts → hotspot, 5 s loop
  cadence, 5 min hotspot window · related: PAR.T04, NET · [H16]
- **PAR.N100** LIMIT · `python/CommonDrivers/async_connect.py:87-104` — "if
  self.wifi_mode_lock.locked(): return [\"\"] * 4" / "return \"---\"" — During a mode switch legacy
  reports not-connected, ifconfig `["","","",""]` and RSSI string `"---"` (also on any RSSI error, e.g.
  AP mode); src reports null · related: NET.S02, PAR.T01 · [H16]
- **PAR.N101** SETTLED · `python/CommonDrivers/async_connect.py:129-135` — "await
  self.ntp_synced.setFalse(); await self.last_ntp_sync.set_counter(-1)" — Legacy `ntp_force_sync()`
  cleared Synced and last-sync (−1) · covered-by: NET.S06 · [H16] ⟨quote not matched at the anchor⟩
- **PAR.N102** INVAR · `python/CommonDrivers/async_connect.py:140-149` — "await asyncio.sleep(2.9) ...
  await asyncio.sleep(0.1)" — Legacy WiFi LED in hotspot-without-client: on 2.9 s / off 0.1 s · related:
  PAR.T04, LED.S04 · [H16]
- **PAR.N103** INVAR · `python/CommonDrivers/async_connect.py:151-166` — "await asyncio.sleep(2) ...
  await asyncio.sleep(1) ... await asyncio.sleep(1)" — Legacy mode switch: disconnect, inactive, 2 s,
  deinit, 1 s, new WLAN, 1 s, WiFi uptime reset (NET.S08's src repeat) · related: NET.S08 · [H16]
- **PAR.N104** RISK · `python/CommonDrivers/async_connect.py:183-192` — "else: # valid ...
  wlan_deactivated = True" — An invalid config read at `wlanConnect()` start deactivates WLAN for the
  task's lifetime (the local flag is never cleared; a REST reconnect does not revive it) · related:
  PAR.S08 · [H16]
- **PAR.N105** INVAR · `python/CommonDrivers/async_connect.py:204,225` — "await asyncio.sleep(5) # allow
  final tasks of calling function" / "await asyncio.sleep(3)" — Legacy reconnect waits 5 s (let the REST
  response go out) then 3 s settle · related: PAR.T04 · [H16]
- **PAR.N106** SETTLED · `python/CommonDrivers/async_connect.py:241` — "self.wlan.config(essid=hostname,
  password='12345678')" — Legacy hotspot SSID = hostname, hardcoded password — the known accepted-risk
  credential CLAUDE.md names · related: SEC, PAR.S11 · [H16]
- **PAR.N107** LIMIT · `python/CommonDrivers/async_connect.py:236-250` — "del ssid, pw, country,
  hostname, wifiled, valid, evtloop, own_ip" — With an invalid config read in hotspot start,
  `evtloop`/`own_ip` are unbound and the `del` raises NameError, ending the WiFi task (low) · related:
  NET · [H16]
- **PAR.N108** PLATFORM · `python/CommonDrivers/async_connect.py:243,299` — "self.wlan.config(pm =
  0xa11140) # Stromsparmodus ausschalten" — Legacy disables CYW43 power saving with the raw value
  0xa11140 in both AP and STA mode · related: NET, PLAT · [H16]
- **PAR.N109** INVAR · `python/CommonDrivers/async_connect.py:266-283` — "if len(stations) > 0: # at
  least one client connected ... self.hotspot_timer.deinit()" — Hotspot stays up indefinitely while any
  client is associated; with none, a one-shot 5 min timer triggers one STA reconnect attempt ("maybe
  router reboot after power loss") · related: NET, PAR.T04 · [H16]
- **PAR.N110** INVAR · `python/CommonDrivers/async_connect.py:292-294` — "if (ssid == \"\"): # invalid
  or empty config ... connection_failures = self.conn_fail_to_hotspot # immediate hotspot mode" — Empty
  SSID → immediate hotspot (factory/first-boot path) · related: PAR.S08 · [H16]
- **PAR.N111** LIMIT · `python/CommonDrivers/async_connect.py:301-324` — "for i in range(10): ... elif
  status == network.STAT_GOT_IP: ... connection successful" — Legacy connect poll is 10×0.5 s and also
  does not break on GOT_IP — the full 5 s is spent on success, legacy-identical to src · related:
  NET.S07 · [H16]
- **PAR.N112** PLATFORM · `python/CommonDrivers/async_connect.py:308` — "elif status == 2: # not defined
  by constant in class yet!" — CYW43 link status 2 (got link, no IP) had no `network.STAT_*` constant at
  1.26 · related: PLAT · [H16]
- **PAR.N113** INVAR · `python/CommonDrivers/async_connect.py:343-345` — "neuer Versuch in 1 Minute...
  await asyncio.sleep(60)" — After one successful connect, legacy never falls back to hotspot: it
  retries every 60 s (+5 s loop) forever · related: PAR.T04, NET · [H16]
- **PAR.N114** RISK · `python/CommonDrivers/async_connect.py:347-362` — "Dauerhaft keine
  WLAN-Verbindung, keine Verbindung zu Hotspot. Deaktiviere WLAN!" — Second failure streak after a
  hotspot phase permanently deactivates WLAN (`wlan.deinit()`) until reboot — the legacy origin of the
  refactor's permanent-deactivation hazard · related: PAR.S08, PAR.T06 · [H16]
- **PAR.N115** INVAR · `python/CommonDrivers/async_connect.py:377,457` — "if (not self.hotspot_mode) and
  (self.wlan.status() == network.STAT_GOT_IP):" — NTP is skipped in hotspot/no-IP; while unsynced every
  10 s tick re-triggers a sync (effective unsynced retry cadence 10 s); the 3×15 s retries apply only
  when already synced · related: PAR.T04, NET.S03 · [H16]
- **PAR.N116** SETTLED · `python/CommonDrivers/async_connect.py:381,389-390` — "await
  self.asy_long_block_lock.acquire() # getaddrinfo may block for some time" — Legacy serialised blocking
  `getaddrinfo` behind the long-block lock (retired in src per F.3) and used the system resolver ·
  related: NET.S04 · [H16]
- **PAR.N117** LIMIT · `python/CommonDrivers/async_connect.py:397-407` — "except: cli = None ...
  finally: await cli.disconnect()" — If the NTP exchange raises, `cli` is set to None and the `finally`
  calls `None.disconnect()` → AttributeError ends the NTP task (supervisor restart) (low) · related: NET
  · [H16]
- **PAR.N118** PLATFORM · `python/CommonDrivers/async_connect.py:426-429` — "(struct.unpack(\"!I\",
  msg[40:44])[0]) - 2208988800 + ntp_offs" — No NTP reply validation (mode/stratum/LI/zero timestamp),
  era-0 only (2036 rollover), `NTP_Offset_S` added before setting the RTC · related: NET · [H16]
- **PAR.N119** INVAR · `python/CommonDrivers/async_connect.py:444-447` — "if not valid: ntp_interv = 12"
  — Unreadable NTP config → 12 h interval default · related: NET · [H16]
- **PAR.N120** LIMIT · `python/CommonDrivers/async_connect.py:451-461` — "if (self.ntp_sec_count <
  (_NTP_ASYNC_INTERV * ntp_interv * 60 * 60)):" — Counter resets at every due resync, so the 3×-interval
  stale rule can never fire — legacy origin of the src behaviour · covered-by: NET.S03 · [H16]
- **PAR.N121** ASSUME · `python/CommonDrivers/async_connect.py:472-482` — "HHMarch = time.mktime((year,3
  ,(31-(int(5*year/4+4))%7),1,0,0,0,0,0)) #Time of March change to CEST" — Legacy local time hard-codes
  the EU DST rule (last Sunday Mar/Oct, 01:00 UTC) for any `GMTOffset`/`DSTOffset` · related: NET, LED ·
  [H16]
- **PAR.N122** INVAR · `python/CommonDrivers/async_connect.py:484-501` — "else: await
  self.wifi_uptime.set_counter(0)" / "await self.last_ntp_sync.set_counter(-1)" — WiFi uptime resets
  whenever status != GOT_IP; last-sync is seconds since sync, −1 when unsynced · related: PAR.T01,
  NET.S15 · [H16]

## python/CommonDrivers/microdot.py

- **PAR.N123** ASSUME · `python/CommonDrivers/microdot.py:1-7` — "The ``microdot`` module defines a few
  classes that help implement HTTP-based servers" — The file carries no version, copyright or licence
  header; its provenance (untagged snapshot between v2.0.1 and v2.1.0, re-checked 2026-09-10) is stated
  only in CLAUDE.md and its licence (© 2019 Miguel Grinberg, MIT) only in THIRD_PARTY_LICENSES.md:18
  (low) · related: PAR.T11, LIC · [H16]
- **PAR.N124** SETTLED · `python/CommonDrivers/microdot.py:15,601,777,789,803` — "from functools import
  partial" / "if max_age is not None:" / "filename.endswith('.gz')" / "self.segments = []" — The v2.1.0
  markers CLAUDE.md cites for the snapshot dating are present at the snapshot (functools.partial
  dispatch, max_age, .gz handling, URLPattern segments) · related: PAR.T11 · [H16]

## python/IndividualDrivers/asy_bmp3xx_driver.py

- **PAR.N125** DRIFT · `python/IndividualDrivers/asy_bmp3xx_driver.py:56-59` — "The previous (0, 2, 4,
  8, 16, 32, 64, 128) tuple here didn't match ... see BACKLOG.md's asy_bmp3xx_driver.py entry" — The
  legacy driver was edited after the initial commit (2bda920, 2026-07-22): HEAD is NOT what fielded wozi
  runs (old tuple); and BACKLOG.md has no `asy_bmp3xx_driver.py` entry any more (dangling pointer) ·
  related: PAR.T15, PAR.T12 · [H16]
- **PAR.N126** PLATFORM · `python/IndividualDrivers/asy_bmp3xx_driver.py:204-213` — "def setup(self,
  sea_level_pressure: float = 1013.25) -> None: await self._i2c.setup()" — `setup()` is a plain `def`
  containing `await`; it works only because MicroPython compiles it as a generator that `await` can
  drive (CPython would reject it) — presumably, unverified at 1.26 (low) · related: PLAT · [H16]
- **PAR.N127** INVAR · `python/IndividualDrivers/asy_bmp3xx_driver.py:206-210` — "if chip_id not in
  (_BMP388_CHIP_ID, _BMP390_CHIP_ID):" — Legacy accepts chip ID 0x50 (BMP388) or 0x60 (BMP390), reads
  calibration, then soft-resets (0xB6) with no post-reset wait · related: SENS · [H16]
- **PAR.N128** LIMIT · `python/IndividualDrivers/asy_bmp3xx_driver.py:212,272-277` — "self._wait_time =
  0.002" / "while await self._read_byte(_REGISTER_STATUS) & 0x60 != 0x60:" — Forced-mode read polls
  STATUS every 2 ms with no timeout (a sensor that never sets both DRDY bits hangs the task; WDT
  backstop) — legacy-identical cadence · related: SENS.S23 · [H16]
- **PAR.N129** LIMIT · `python/IndividualDrivers/asy_bmp3xx_driver.py:140-141,215-223` — "Pressure =
  await self.bmp.get_pressure() / Temperature = await self.bmp.get_temperature()" — Each sample triggers
  two separate forced conversions (pressure from one, temperature from the next) · related: PAR.T12 ·
  [H16]
- **PAR.N130** INVAR · `python/IndividualDrivers/asy_bmp3xx_driver.py:162-175` — "POffs = 0.0 TOffs =
  0.0 SeaLevel = 0.0 AtmTemp = 15.0" / "altitude_baro(Pressure - POffs, -SeaLevel, AtmTemp)" — Published
  BMP values: pressure − offset, temperature − offset, sea-level pressure from `BMPSeaLevelOffs` (a
  height in m) and `BMPMeanAtmTemp`; unreadable config falls back to 0/0/0/15 °C · related: PAR.T12,
  ALGO.S03 · [H16]
- **PAR.N131** INVAR · `python/IndividualDrivers/asy_bmp3xx_driver.py:64,110-134,150-160` —
  "trigger_sec=1, max_i2c_err=5" / "return False # Abbruch der Schleife führt zu System-Reset" — Legacy
  reader pattern (all sensors): setup/config failure or >5 net errors (leaky: −1 per good read) ends the
  task, which the supervisor turns into a reboot · related: PAR.S04, PAR.S12 · [H16]
- **PAR.N132** INVAR · `python/IndividualDrivers/asy_bmp3xx_driver.py:258-261` — "await
  self._write_register_byte(_REGISTER_CONFIG, _IIR_SETTINGS.index(coef) << 1)" — Filter-coefficient
  write replaces the whole CONFIG register · related: SENS · [H16]

## python/IndividualDrivers/asy_fram_driver.py

- **PAR.N133** LIMIT · `python/IndividualDrivers/asy_fram_driver.py:45-47` — "if (read_buffer[0] !=
  _SPI_MANF_ID) and (prod_id != _SPI_PROD_ID): raise OSError" — Legacy FRAM detection accepts a chip
  when EITHER the manufacturer ID (0x04) OR the product ID (0x0302) matches · related: STOR, HW · [H16]
- **PAR.N134** LIMIT · `python/IndividualDrivers/asy_fram_driver.py:48-50` —
  "self._wp_pin.init(_wp_pin.OUT)" — The WP-pin path references an undefined name and would raise
  NameError; no legacy unit passes `wp_pin` (low) · related: STOR · [H16]
- **PAR.N135** INVAR · `python/IndividualDrivers/asy_fram_driver.py:31,148-158` — "max_size: int=0x2000"
  / "if self._max_size > 0xFFFF: # > 16bit address" — Legacy FRAM size 8 KB with 2-byte addressing
  (3-byte only above 64 KB) · related: STOR, PAR.T14 · [H16]
- **PAR.N136** INVAR · `python/IndividualDrivers/asy_fram_driver.py:68-71,81-84` — "if not
  self.async_lock.locked(): ... return None" — Reads/writes are refused unless the caller already holds
  the chip lock (`async with fram`) — convention only · related: STOR · [H16]
- **PAR.N137** LIMIT · `python/IndividualDrivers/asy_fram_driver.py:118-127` — "for i in range(0,
  data_length): await spidev.write(bytearray([data[i]]))" — Legacy writes one byte per SPI call
  (allocation per byte) with WREN/WRDI around each write · related: PERF, STOR · [H16]

## python/IndividualDrivers/asy_fram_manager.py

- **PAR.N138** INVAR · `python/IndividualDrivers/asy_fram_manager.py:8-16,117-119` — "# [...Data
  0...][Status 0-1][Status 0-2][...Data 1...][Status 1-1][Status 1-2]" — Legacy chunk layout: two
  copies, two status bytes each (0x00 uninit, 0x01 idle, 0x02 busy), no CRC, allocated sequentially from
  address 0 in constructor call order · covered-by: PAR.S09 · [H16]
- **PAR.N139** PLATFORM · `python/IndividualDrivers/asy_fram_manager.py:87,96` — "ts =
  struct.pack(\"Q\", utc)" — Timestamped chunk prefixes an 8-byte native-endian UTC timestamp; 0 =
  written while unsynced · related: PAR.T14, STOR · [H16]
- **PAR.N140** INVAR · `python/IndividualDrivers/asy_fram_manager.py:77-89,97-106` — "if require_ntp:
  return False, None, False" / "age = time.mktime(time.gmtime()) - ts" — Unsynced writes are stored with
  ts=0 unless `require_ntp`; age is computed only while currently synced · related: PAR.S01, PAR.S03 ·
  [H16]
- **PAR.N141** LIMIT · `python/IndividualDrivers/asy_fram_manager.py:279-329` — "res = await
  fram.set_values(addr + self.size + _ADDR_STATUS_1, bytearray([_STATUS_BUSY]))" — Every legacy read
  writes both status bytes BUSY then IDLE (4 FRAM writes per copy read); a status byte left BUSY by a
  power cut marks that copy invalid (errors 21/24) · related: STOR, PAR.T14 · [H16]
- **PAR.N142** RISK · `python/IndividualDrivers/asy_fram_manager.py:219-223` — "if data0 != data1: ...
  self.last_error = 50 ... return None" — Two valid but different copies → error 50 and no data (backup
  unusable for the session, not repaired) · related: STOR, PAR.T14 · [H16]
- **PAR.N143** INVAR · `python/IndividualDrivers/asy_fram_manager.py:163-178,256-347` — "self.last_error
  = 40" / "last_error = 10 ... 33" — Legacy FRAM last-error codes 10-15 write, 20-29 read, 30-33 clear,
  40 verify mismatch, 50 copy mismatch; surfaced as `SGP40_MemErr_Last` · related: PAR.T01, STOR · [H16]
- **PAR.N144** INVAR · `python/IndividualDrivers/asy_fram_manager.py:32-37,143-146` — "if (not
  override_pause) and (self.fram_mgr.get_pause()):" — A global pause flag (reboot, `mempause`) blocks
  reads, writes and clears unless overridden · related: STOR · [H16]

## python/IndividualDrivers/asy_i2c_driver.py

- **PAR.N145** INVAR · `python/IndividualDrivers/asy_i2c_driver.py:7,38-54` — "frequency=100000" /
  "return self._i2c.readfrom_into(address, buffer, True)" — Legacy I2C defaults to 100 kHz (every unit
  passes 50 kHz) and always sends STOP (no repeated start) · related: BUS · [H16]
- **PAR.N146** LIMIT · `python/IndividualDrivers/asy_i2c_driver.py:81-108,232-242` — "mem_value =
  self._i2c.readfrom_mem(address, reg_addr, reg_width)" — Bit/struct register helpers take no bus lock
  themselves; callers must hold `async with device` — convention only · related: BUS · [H16]
- **PAR.N147** LIMIT · `python/IndividualDrivers/asy_i2c_driver.py:260-280` —
  "self.i2c.writeto(self.device_address, b\"\")" — Probe is a zero-length write, falling back to a
  1-byte read; all I2C calls are synchronous inside async wrappers (no yield during a transfer) ·
  related: BUS, PLAT · [H16]

## python/IndividualDrivers/asy_isl29125_driver.py

- **PAR.N148** INVAR · `python/IndividualDrivers/asy_isl29125_driver.py:89-98` — "# ISLOperationMode:
  0b101 = 5 = RGB ... # ISLIrCompensation = 63 = on / max (-1 = off)" — Legacy ISL29125 defaults (RGB,
  10k lux, 16-bit, IR comp 63, no interrupt) — dev-only in legacy · related: PAR.S14 · [H16]
- **PAR.N149** LIMIT · `python/IndividualDrivers/asy_isl29125_driver.py:140` — "if (self.irq_pin.value()
  == 0) and not self.irq_waiting:" — The base trigger dereferences `irq_pin` unconditionally; without an
  IRQ pin the trigger task raises (low) · related: PAR.S14 · [H16]
- **PAR.N150** LIMIT · `python/IndividualDrivers/asy_isl29125_driver.py:324-328` — "red = await
  self._get_reg(0x0B, \"H\") green = ... blue = ..." — Legacy publishes raw channel counts read as three
  separate transactions (no lux conversion, channels not from one atomic read) · related: PAR.T12,
  PAR.S14 · [H16]
- **PAR.N151** LIMIT · `python/IndividualDrivers/asy_isl29125_driver.py:354-356,377-379` — "values =
  (\"POWERDOWN\", \"GREEN_ONLY\", ...)" — Getters return string names while setters take ints, so a GET
  readback is not PUT-able · related: PAR.S14 · [H16]
- **PAR.N152** LIMIT · `python/IndividualDrivers/asy_isl29125_driver.py:484,500` — "if not (0 <= value
  <= 65536):" — Threshold bound admits 65536, which cannot be packed into 16 bits (low) · related:
  PAR.S14 · [H16]

## python/IndividualDrivers/asy_mprls_driver.py

- **PAR.N153** INVAR · `python/IndividualDrivers/asy_mprls_driver.py:143-148,237-241` — "if FiltCoeff >
  0.0: # optional first-order lowpass filter" / "psi * 68.947572932" — Legacy MPRLS: 10-90 % transfer
  function, 0-25 psi → hPa, optional EMA; no src counterpart (dev-only sensor) · related: PAR.S14 ·
  [H16]
- **PAR.N154** LIMIT · `python/IndividualDrivers/asy_mprls_driver.py:211-226` — "while True: ... await
  asyncio.sleep(0.005) # 5ms conversion time" — Busy-poll with no timeout while holding the I2C bus lock
  (low) · related: PAR.S14 · [H16]

## python/IndividualDrivers/asy_scd30_driver.py

- **PAR.N155** INVAR · `python/IndividualDrivers/asy_scd30_driver.py:55,61,77-78,137-146` —
  "trigger_sec=3" / "period=500" / "# CO2 Sensor IRQ triggern falls es nicht läuft (Pin bleibt HIGH wenn
  nicht gelesen!)" — Legacy SCD30: read on RDY rising edge; a 500 ms timer counts RDY-high ticks and
  forces a read after 2×trigger_sec ticks (6 = 3 s) · covered-by: SENS.S08 · [H16]
- **PAR.N156** WORKAROUND · `python/IndividualDrivers/asy_scd30_driver.py:243-246` — "await
  asyncio.sleep(0.2) # not mentioned by datasheet, but required to avoid IO error" — 200 ms settle after
  the soft reset every read-task (re)start; removal trigger: none stated · related: SENS.S22 · [H16]
- **PAR.N157** SETTLED · `python/IndividualDrivers/asy_scd30_driver.py:89-99,239-241` — "await
  self.scd.setup()" → "await self.reset()" — Legacy also soft-resets (0xD304) on every read-task
  (re)start and never issues a start-continuous command at boot (relies on the sensor's stored state) ·
  related: SENS.S22 · [H16]
- **PAR.N158** INVAR · `python/IndividualDrivers/asy_scd30_driver.py:129-134` — "await
  self.meas_data.set_data([CO2, Temperature, Humidity, math_helpers.wet_bulb_temperature(" — Published
  SCD30 tuple: CO2, T, RH, wet bulb, dew point, timestamp; temperature offset is applied only by the
  sensor's NVM setting, not in software · related: PAR.T12 · [H16]
- **PAR.N159** ASSUME · `python/IndividualDrivers/asy_scd30_driver.py:292-296` — "return await
  self._read_register(_CMD_CONTINUOUS_MEASUREMENT)" — `AmbPres` GET reads back the
  continuous-measurement command register 0x0010 — the unverified read-back A.4 builds on · related:
  SENS.T09 · [H16]
- **PAR.N160** LIMIT · `python/IndividualDrivers/asy_scd30_driver.py:329-335` — "if offset > 655.35:
  raise" / "int(offset * 100)" — Only an upper bound; a negative offset would fail in byte packing;
  truncation, not rounding (REST bound 0.0-655.35 keeps negatives out) · related: SENS.S09 · [H16]
- **PAR.N161** INVAR · `python/IndividualDrivers/asy_scd30_driver.py:399,408` — "await
  asyncio.sleep(0.05) # 3ms min delay" / "await asyncio.sleep(0.005) # min 3 ms delay" — Legacy waits 50
  ms after every command and 5 ms between register write and read · related: SENS.T06, PAR.T04 · [H16]
- **PAR.N162** LIMIT · `python/IndividualDrivers/asy_scd30_driver.py:350-379` — "if await
  self.data_available(): await self._read_data() return self._co2" — Each of CO2/T/RH checks data-ready
  separately and returns the cached value when not ready (stale values re-stamped with a fresh
  timestamp) · covered-by: SENS.S08 · [H16]

## python/IndividualDrivers/asy_sgp40_driver/__init__.py

- **PAR.N163** RISK · `python/IndividualDrivers/asy_sgp40_driver/__init__.py:339,341-352` —
  "self._reset()" (no await) / "# This is a general call Reset." — The legacy "general-call reset" never
  ran: `_reset()` is an un-awaited coroutine, and even if run it writes 0x0006 to the SGP40's own
  address 0x59, not general-call 0x00 — so the refactor's real broadcast (SPECIFICATION.md:2047,
  accepted risk) is new field behaviour, not parity · related: BUS, SENS · [H16]
- **PAR.N164** INVAR · `python/IndividualDrivers/asy_sgp40_driver/__init__.py:20-22,83,207` —
  "_FRAM_VERIFY_MINS = const(60)" / "int(math.ceil((10 * _FRAM_VERIFY_MINS) / backup_period) * 0.1)" —
  Legacy verifies an FRAM backup roughly once per hour of backups · related: STOR · [H16]
- **PAR.N165** INVAR · `python/IndividualDrivers/asy_sgp40_driver/__init__.py:84-86` — "if 1 <= wait_ntp
  <= 600: # wait ntp between 1sec and 10mins" — `SGPWaitTimeNTP` 0 (or out of range) → one immediate
  restore attempt, contrary to the UI's "0 = never wait" meaning · covered-by: PAR.S01 · [H16]
- **PAR.N166** ASSUME · `python/IndividualDrivers/asy_sgp40_driver/__init__.py:108-127` — "if age is
  None: if voc_init > 0: ... deserialize = None" — While NTP is unsynced a timestamped backup is retried
  each second; when the wait expires the backup is restored WITHOUT the max-age check; `SGPBackupMaxAge`
  0 = no age limit · related: PAR.S01 · [H16]
- **PAR.N167** INVAR · `python/IndividualDrivers/asy_sgp40_driver/__init__.py:132-134,141-142` —
  "backup_counter >= (60 * backup_period)" / "if backup_counter >= 100000:" — Backup every
  `60×SGPBackupPeriod` loop ticks (1 s timer); counter wraps at 100000 · related: XCUT.T21 · [H16]
- **PAR.N168** SETTLED · `python/IndividualDrivers/asy_sgp40_driver/__init__.py:211-238` — "require_ntp
  = (voc_write > 0)" / "voc_write = 0" — Until the first synced write, backups require NTP (skipped, not
  errors); after it, `voc_write` stays 0 so later backups never wait again · covered-by: PAR.S03 · [H16]
- **PAR.N169** LIMIT · `python/IndividualDrivers/asy_sgp40_driver/__init__.py:158-160` — "if (Temp is
  None) or (Hum is None): ... hat keine Kompensationsdaten!" — Without SCD30 T/RH the SGP40 is not
  sampled at all that second (VOC algorithm not fed) · related: PAR.T12 · [H16]
- **PAR.N170** INVAR · `python/IndividualDrivers/asy_sgp40_driver/__init__.py:321-338` — "if
  serialnumber[0] != 0x0000:" / "if featureset[0] & 0xFF00 != 0x3200:" / "if self_test[0] != 0xD400:" —
  Legacy checks serial word 0 == 0, feature set 0x32xx and the full self-test word == 0xD400 (src checks
  the high byte only) · related: SENS.S21, SENS.S06 · [H16]
- **PAR.N171** ASSUME · `python/IndividualDrivers/asy_sgp40_driver/__init__.py:367,386` — "temp_ticks =
  int(((temperature + 45) * 65535) / 175) & 0xFFFF" — Legacy truncates temperature ticks but rounds
  humidity ticks; src rounds both — a small compensation-input delta · related: PAR.T12 · [H16]
- **PAR.N172** INVAR · `python/IndividualDrivers/asy_sgp40_driver/__init__.py:392-398` — "read_value =
  await self._read_word_from_command(delay_ms=500)" — Legacy waits 500 ms per measurement (src 100 ms,
  datasheet 30 ms) · related: SENS.S07 · [H16]
- **PAR.N173** TODO · `python/IndividualDrivers/asy_sgp40_driver/__init__.py:474` — "# TODO: Take 2-byte
  command as int (0x280E, 0x0006) and packinto command buffer" — Upstream Adafruit TODO carried in the
  legacy driver; not a to-do here (legacy rule) (low) · [H16]

## python/IndividualDrivers/asy_sgp40_driver/voc_algorithm.py

- **PAR.N174** SETTLED · `python/IndividualDrivers/asy_sgp40_driver/voc_algorithm.py:1-12` —
  "SPDX-FileCopyrightText: Copyright (c) 2010 DFRobot Co.Ltd ... * Author(s): yangfeng" — Legacy VOC
  algorithm is DFRobot's Python port (MIT), not Sensirion's C reference directly · related: ALGO, LIC ·
  [H16]
- **PAR.N175** MIRROR · `python/IndividualDrivers/asy_sgp40_driver/voc_algorithm.py:91-164` — "return
  struct.pack(\"31q\"," — Legacy state is 31 native-endian int64 fields (248 B, all algorithm params
  incl. uptime); src packs "32q" (src/voc_algorithm.py:98, 141) — the formats are not interchangeable
  across reflash or rollback · related: PAR.S09, ALGO.S02, PAR.T14 · [H16]
- **PAR.N176** INVAR · `python/IndividualDrivers/asy_sgp40_driver/voc_algorithm.py:18,384-387,414` —
  "_VOCALGORITHM_INITIAL_BLACKOUT = const(45)" — Legacy publishes VOC index 0 for the first 45 samples
  after init or reset; restoring a backup restores uptime and skips the blackout · related: SENS.S04 ·
  [H16]
- **PAR.N177** LIMIT · `python/IndividualDrivers/asy_sgp40_driver/voc_algorithm.py:91-93,125-126` —
  "except: return None" — A pack failure silently yields no backup (counted as a serialise error by the
  reader) (low) · related: ALGO · [H16]

## python/IndividualDrivers/asy_shtc3_driver.py

- **PAR.N178** INVAR · `python/IndividualDrivers/asy_shtc3_driver.py:164-178` — "tc = Temperature -
  TOffs ... rh = math_helpers.rel_humidity(tc, ah)" — Legacy SHTC3 applied a software temperature offset
  and re-derived RH via absolute humidity, plus optional EMA — dropped with the sensor (dev-only) ·
  related: PAR.S14 · [H16]
- **PAR.N179** LIMIT · `python/IndividualDrivers/asy_shtc3_driver.py:313-315` — "return (temperature,
  humidity)" (on CRC mismatch) — A CRC failure returns (None, None) without raising, so the reader's
  `Temperature - TOffs` raises TypeError and ends the task (low) · related: PAR.S14 · [H16]

## python/IndividualDrivers/asy_spi_driver.py

- **PAR.N180** INVAR · `python/IndividualDrivers/asy_spi_driver.py:39-47,129-138,140-147` —
  "self._spi.init(baudrate=baudrate," / "await asyncio.sleep_ms(1)" — Legacy re-inits the SPI peripheral
  (1 MHz, mode 0, always MSB) on every CS transaction and sleeps 1 ms after CS assert and after release
  · related: BUS, PERF · [H16]
- **PAR.N181** LIMIT · `python/IndividualDrivers/asy_spi_driver.py:31-37` — "self.deinit()" (in
  `SPI.__aexit__`) — Using the bus object itself as a context manager deinits and deletes the
  peripheral; only `SPIDevice` is used as one, so the path is dormant (low) · related: BUS · [H16]

## python/IndividualDrivers/asy_uart.py

- **PAR.N182** MIRROR · `python/IndividualDrivers/asy_uart.py:198-241` — "crc = crc >> 1 ... crc = crc ^
  self.poly" / "struct.pack(\"H\", crc)" — Legacy CRC16 shifts right with poly 0x1021/preset 0xFFFF,
  little-endian, check = CRC over data+CRC == 0; src CRC16 shifts left (src/crc_checks.py:44) — a
  wire-level difference on the UART protocol's origin (dev-only, no field peer) · related: UART · [H16]
- **PAR.N183** LIMIT · `python/IndividualDrivers/asy_uart.py:83-99` — "add = self.uart.read(nbytes -
  len(msg))" — After POLLIN the legacy reads the whole remaining frame in one call — the blocking-read
  pattern CLAUDE.md/F.5.8 forbid in src · related: UART · [H16]
- **PAR.N184** LIMIT · `python/IndividualDrivers/asy_uart.py:10,57-72` — "poll_wait_ms=0" / "await
  asyncio.sleep_ms(self.poll_wait_ms)" — `ready()` polls with `sleep_ms(0)` by default — busy-yield, no
  idle cadence (contrast F.5.9's `poll_idle_ms`) · related: UART, PERF · [H16]

## python/IndividualDrivers/asy_uart_comm.py

- **PAR.N185** INVAR · `python/IndividualDrivers/asy_uart_comm.py:8-23,187-199` — "# Message format:
  [UID][CMD][SIZE][CHUNKS][CUR_CHUNK][...Payload...]" / "payload_size=48, timeout=1000" — Legacy
  protocol origin: 5-byte header + 48-byte zero-padded payload, 1 s timeout, UID 0..0xFE, first chunk
  carries the command ID · related: UART · [H16]
- **PAR.N186** DRIFT · `python/IndividualDrivers/asy_uart_comm.py:164` — "if num_chunks > 0xFF: # 16bit
  payload field" — Comment says 16-bit while the check and the field are 8-bit (low) · related: UART ·
  [H16]
- **PAR.N187** INVAR · `python/IndividualDrivers/asy_uart_comm.py:38-46,205` — "timeout = int(1.5 *
  self.timeout)" / "if not (msg[_MSG_CMD] & exp_cmd):" — Recovery drains until 1.5×timeout of silence
  then blocks writes one more 1.5×timeout; command check is a bitmask (a frame with several bits set
  passes) · related: UART · [H16]

## python/IndividualDrivers/neopixel_signal.py

- **PAR.N188** INVAR · `python/IndividualDrivers/neopixel_signal.py:8,11,56-62` — "_MAX_OVERRIDE_TIME =
  const(3600)" / "neopixel_freq=20, led_overl_bri=50" — Legacy LED: 20 Hz ramp, WiFi-LED overlay white
  at brightness 50, auto-signal pause clamped 0..3600 s · related: PAR.T04, LED · [H16]
- **PAR.N189** INVAR · `python/IndividualDrivers/neopixel_signal.py:67-73` — "if
  self.ext_start_signal.is_set(): return False" — A REST LED command is rejected at once (→ code 8 "LED
  is busy") when one is already pending · covered-by: REST.S09 · [H16]
- **PAR.N190** INVAR · `python/IndividualDrivers/neopixel_signal.py:128-150` — "self.rgbt[3] = 0.1 if
  self.rgbt[3] < 0.1 else self.rgbt[3]" / "async with self.asy_long_block_lock:" — Ramp up/down over `t`
  seconds (min 0.1 s) while holding the long-block lock, then LED off and WiFi-overlay state restored ·
  related: LED, PAR.T04 · [H16]
- **PAR.N191** SETTLED · `python/IndividualDrivers/neopixel_signal.py:164-170` — "if onMinOfDay <=
  curMinOfDay <= offMinOfDay:" — Auto-signal window must lie within one day (no midnight wrap; UI says
  so) and only runs with NTP-derived local time · related: LED (A.4 midnight-window decision) · [H16]
- **PAR.N192** INVAR · `python/IndividualDrivers/neopixel_signal.py:173-186` — "await asyncio.sleep(2 *
  flashDur)" — CO2 red, VOC green, humidity blue; a 2×FlashDur gap follows CO2 and VOC but not the last
  (humidity) warning · covered-by: LED.S03 · [H16]
- **PAR.N193** INVAR · `python/IndividualDrivers/neopixel_signal.py:159-162,188-192` — "Interv = 600" /
  "if (rem_interv < 0.1): rem_interv = 0.1" — Interval counted from loop start (warnings included);
  unreadable config → auto off, 600 s · related: PAR.T04 · [H16]

## python/Manifest/manifest.py

- **PAR.N194** INVAR · `python/Manifest/manifest.py:1-2` —
  "include(\"$(PORT_DIR)/boards/RPI_PICO_W/manifest.py\")" / "freeze(\".\")" — Legacy freezes the whole
  staged build directory (all CommonDrivers incl. microdot, the per-build driver set, frozen_html) on
  top of the stock board manifest · related: PAR.T09 · [H16]

## modules/_boot.py

- **PAR.N195** SETTLED · `modules/_boot.py:16` — "import sensortask.py" — The frozen boot imports the
  frozen `sensortask` with a literal `.py`; never to be changed without hardware testing (CLAUDE.md hard
  rule, BACKLOG #1) · related: PAR.T09 · [H16]
- **PAR.N196** RISK · `modules/_boot.py:4-12` — "# Try to mount the filesystem, and format the flash if
  it doesn't exist." / "except: vfs.VfsLfs2.mkfs(bdev, progsize=256)" — Legacy formats the littlefs
  (wiping `config.json`) on ANY mount exception — matters for a rollback onto a filesystem last written
  by 1.29 · related: PAR.T14, PAR.S10 · [H16]
- **PAR.N197** ASSUME · `modules/_boot.py:16` — "import sensortask.py" — The app runs from `_boot`
  itself and never returns, so a filesystem `boot.py`/`main.py` on a legacy unit presumably never
  executed — relevant to what a reflash finds (unverified) (low) · related: PAR.T08 · [H16]

## modules/sensortask-wozi.py

- **PAR.N198** INVAR · `modules/sensortask-wozi.py:20-21` — "_DEFAULT_CONFIG =
  const(\"{\\\"LedAutoOn\\\": true, ... \\\"SGPWaitTimeNTP\\\": 30}\")" — Legacy defaults: auto LED on
  10:00-18:00, interval 300 s, FlashDur 2, Bri 200, CO2 1600, VOC 350, Hum 65; GMT/DST 3600; NTP
  pool.ntp.org/12 h/offset 0; SSID ""; Hostname "SensorNode"; Country DE; BMP interval 2, overs 1,
  filter 0, sea-level 0, atm 15 °C; SGP backup 1 min/max age 7200 min/NTP wait 30 s · related: PAR.T01,
  PAR.S11 · [H16]
- **PAR.N199** INVAR · `modules/sensortask-wozi.py:23-27` — "_TASK_CHECK_TIME = const(3)
  _TASK_FAIL_INCREMENT = const(100) _TASK_FAIL_MAX = const(300)" / "_FRAM_PAUSE_SEC = const(300)" —
  Supervisor 3 s / +100 per restart / >300 stops feeding; `mempause` = 300 s · covered-by: PAR.S04 ·
  [H16]
- **PAR.N200** INVAR · `modules/sensortask-wozi.py:77-90` — "watchdog = WDT(timeout = 8000)" / "i2c0 =
  asy_i2c_driver.I2C(0, 13, 12, frequency=50000)" — Wozi wiring: WDT 8 s at import; i2c0 SCL13/SDA12,
  i2c1 SCL19/SDA18, both 50 kHz; SPI0 2/3/4, FRAM CS1 8 KB; SCD30 on i2c0 RDY GP8; SGP40+BMP on i2c1;
  NeoPixel GP15; hotspot window 8 min — matches `devices/wozi.toml` pins at a glance · related: PAR.T02
  · [H16]
- **PAR.N201** INVAR · `modules/sensortask-wozi.py:86,90-91` — "sgp_backup =
  fram.get_timestamped_chunk(_SGP40_Memsize, conn.ntp_issynced)" / "conn.set_ext_led(pixel)" — FRAM
  chunk 0 is the SGP40 backup (only FRAM user); the NeoPixel doubles as the WiFi LED · related: PAR.S09,
  LED.S04 · [H16]
- **PAR.N202** RISK · `modules/sensortask-wozi.py:100-109` — "starter = Timer(period=delay,
  mode=Timer.ONE_SHOT, callback=lambda b: timer_sequencer(" — Legacy staggers timer starts (1000
  ms/(n+1)) through one-shot Timers held in a local only — the unreferenced-Timer GC pattern the src
  `_timer_sequencer` fix addressed · related: XCUT.S05 · [H16]
- **PAR.N203** INVAR · `modules/sensortask-wozi.py:113-143` — "@app.get('/favicon.ico')" /
  "send_file('html/index.html', compressed=True, file_extension='.gz')" — Legacy static routes: `/`,
  `/index.html`, `/favicon.ico`, `/nettimeconfig.html`, `/sensorconfig.html`, `/systemledconfig.html`,
  `/style.css`, `/functions.js`, all gzip from the frozen `html/` · related: PAR.S06, PAR.S15 · [H16]
- **PAR.N204** INVAR · `modules/sensortask-wozi.py:146-166` — "\"IPv4\": netConfig[0], ... \"Rssi\":
  Rssi" / "cfg_data[\"PW\"] = \"********\"" — GET `/net/status` {IPv4, Subnet, Gateway, DNS, Rssi}; GET
  `/net/config` {Country, Hostname, SSID, PW:"********"} (PW null on read error) · related: PAR.T01,
  NET.S16 · [H16]
- **PAR.N205** INVAR · `modules/sensortask-wozi.py:168-182` — "update_valid_json(req_json, \"Hostname\",
  \"str\", res, 1, 63" — PUT `/net/cmd` `setNetwork`: Hostname 1-63, Country exactly 2, SSID 2-32, PW
  8-63; saves then reconnects (5 s delay) · covered-by: NET.S17 · [H16]
- **PAR.N206** INVAR · `modules/sensortask-wozi.py:185-219` — "system = {\"Synced\": \"On\" if synced
  else \"Off\", \"Unix\": time.mktime(gmt)}" — GET `/time/status` {System{Synced "On"/"Off", Unix},
  UTC{...}, Local{... or "None" strings}}; PUT `setTiming`: NTP_Host 3-1024, offsets ±43200, interval
  1-24 h; then force-resync · related: PAR.T01, NET.S06 · [H16]
- **PAR.N207** INVAR · `modules/sensortask-wozi.py:222-248` — "\"WetBulb\": \"None\" if
  scd_meas[_SCD30_WetBulb] is None else" — GET `/sensors/status` groups
  SCD30{CO2,Temp,Hum,WetBulb,DewPoint,TS}, SGP40{VOC,Raw,TS}, BMP388{Pres,Temp,SLPres,TS}; absent values
  mix JSON null and the string "None" · covered-by: PAR.S06 · [H16]
- **PAR.N208** INVAR · `modules/sensortask-wozi.py:250-304` — "\"SelfCal\": toSwitch(await
  scd_reader.get_self_calibration_enabled())" — GET `/sensors/config` reads SCD30 settings live from the
  sensor (all "None" on any error), BMP oversampling/filter live from the chip as values, the rest from
  config.json · related: PAR.T01 · [H16]
- **PAR.N209** RISK · `modules/sensortask-wozi.py:316-321` — "data[\"MeasInt\"] = await
  scd_reader.get_measurement_interval()," — Trailing commas make the readback of
  MeasInt/AmbPres/Altitude/ForceCalRef/SelfCal 1-tuples, so the "Unchanged" comparison never matches:
  legacy wrote those to SCD30 NVM on EVERY non-empty PUT value (only TempOffs was skipped when equal;
  the UI sends "" for untouched fields) — same at arzi/neu :277-281 · related: PAR.S02, SENS.T07 · [H16]
- **PAR.N210** INVAR · `modules/sensortask-wozi.py:322-344` — "data[\"ContMeas\"] = True # not readable
  from sensor" / "# datamanager = None --> Don't write system config here" — PUT `setSCD`: TempOffs
  0.0-655.35, MeasInt 2-1800, AmbPres 0 or 700-1400 (force), Altitude 0-65535, ForceCalRef 400-2000,
  SelfCal switch, ContMeas "Off" only → stop; nothing persisted to config.json; a failed sensor readback
  returns code 4 · related: PAR.S02, PAR.T01 · [H16]
- **PAR.N211** INVAR · `modules/sensortask-wozi.py:346-358` — "update_valid_json(req_json,
  \"SGPBackupMaxAge\", \"int\", res, 0, 10080" — PUT `setSGP`: BackupPeriod 0-1440 min, MaxAge 0-10080
  min, WaitTimeNTP 0-600 s, SGPResetVOC command-only ("On") · related: PAR.S01, PAR.T01 · [H16]
- **PAR.N212** INVAR · `modules/sensortask-wozi.py:360-379` — "update_valid_json(req_json,
  \"BMPPressOvers\", \"int\", res, 0, 5, weight_fct=lambda x : 2 ** x" — PUT `setBMP`: interval 1-3600,
  oversampling as exponent 0-5 (GET returns the value 1-32), FiltCoeff 0-7 → 2**x−1 (HEAD; fielded wozi
  had 2**x with special 0), offsets P ±500, T ±10, sea-level −1000..5000, atm ±50 · related: PAR.S06,
  PAR.T15 · [H16]
- **PAR.N213** INVAR · `modules/sensortask-wozi.py:382-395` — "return {\"pauseTime\": pausetime}" /
  "cfg_data[\"LedAutoOn\"] = toSwitch(" — GET `/led/status` {pauseTime}; GET `/led/config` 12 Led* keys
  with On/Off strings for the two switches · related: PAR.T01 · [H16]
- **PAR.N214** INVAR · `modules/sensortask-wozi.py:402-419` — "default = { \"r\": 0, \"g\": 0, \"b\": 0,
  \"t\": 1.0 }" — `lightCmdLED`: r/g/b 0-255, t 0.5-60 s; an empty field falls back to the default
  (0/0/0/1.0) but an absent key is code 7; busy → code 8; nothing saved · related: REST.S09, REST.S10 ·
  [H16]
- **PAR.N215** INVAR · `modules/sensortask-wozi.py:421-453` — "update_valid_json(req_json,
  \"pauseTime\", \"int\", res, 0, 3600" / "\"LedAutoInterv\", \"float\", res, 60.0, 3600.0" —
  `pauseAutoLED` 0-3600 (bad → code 9); `setAutoLED`: hours 0-23, minutes 0-59, Bri 1-255, Interv
  60-3600 s, FlashDur 0.5-10 s, CO2 0-3000, VOC 0-500, Hum 0-100 · related: PAR.T01, LED · [H16]
- **PAR.N216** INVAR · `modules/sensortask-wozi.py:455-462` — "res = await set_sensor_value(res,
  conn.set_wifi_led, cfgmgr, default=True" — `setWiFiLED` switch applied live and persisted · related:
  LED.S04 · [H16]
- **PAR.N217** INVAR · `modules/sensortask-wozi.py:465-506` — "\"Error_Status\": toSwitch(ErrorStatus),"
  / "sgpback = \"No TS\"" — GET `/system/status` keys: Sys_Uptime, Wifi_Uptime, NTP_LastSync,
  Boot_Signature, Error_Status, Task_ErrCnt, Task_LastErr (task-list index), per-sensor ErrCnt, SGP40
  Backup/Restore TS ("None"/"No TS"), SGP40 MemErr counters; no persistent error log · related: PAR.T01,
  PAR.S05 · [H16]
- **PAR.N218** INVAR · `modules/sensortask-wozi.py:508-537` — "special_val=[\"reboot\", \"bootloader\",
  \"mempause\"]" — PUT `/system/cmd` `systemCmd` content ∈ {reboot, bootloader, mempause}; anything else
  code 10 · related: PAR.T01 · [H16]
- **PAR.N219** INVAR · `modules/sensortask-wozi.py:540-583` — "async_onetime.append(fram.setup)" /
  "await asyncio.sleep(1.0 / len(task_starters))" / "await conn.ntp_force_sync() # first sync" — Boot
  order: fram.setup → timers staggered over 1 s → 16 tasks spread over 1 s (webserver last) → forced
  first NTP sync → supervisor · related: XCUT.T01, PAR.T04 · [H16]
- **PAR.N220** RISK · `modules/sensortask-wozi.py:570-573,585-608` — "if task_errors > _TASK_FAIL_MAX:
  all_running = False" / "watchdog.feed()" — `all_running` never recovers once false: a failed
  `fram.setup()` or a 4th quick task restart starves the WDT → reset; a sensor whose setup keeps failing
  therefore reboot-loops the unit (~12 s + 8 s) · covered-by: PAR.S12 · [H16]
- **PAR.N221** DRIFT · `modules/sensortask-wozi.py:604-607` — "if all_running: ... watchdog.feed()" —
  PAR.S12 cites `:604-606` for the feed; the feed block is `:605-607` (off by one) (low) · related:
  PAR.S12 · [H16]

## modules/sensortask-arzi.py

- **PAR.N222** INVAR · `modules/sensortask-arzi.py:21,69-73` — "i2c1 = asy_i2c_driver.I2C(1, 27, 26,
  frequency=50000)" / "spi0 = asy_spi_driver.SPI(0, 2, 3, 4)" — Arzi = wozi minus BMP388 (no BMP keys,
  routes or counters); i2c1 on SCL27/SDA26; SPI0 2/3/4 with FRAM CS1 — matches `devices/arzi.toml` at a
  glance · related: PAR.T02 · [H16]

## modules/sensortask-neu.py

- **PAR.N223** INVAR · `modules/sensortask-neu.py:72-73` — "spi0 = asy_spi_driver.SPI(0, 18, 19, 16)" /
  "fram = asy_FRAM_manager(spi0, 17, max_size=0x2000" — Neu differs from arzi only in SPI0
  (SCK18/MOSI19/MISO16, FRAM CS17) and shares arzi's web UI (`build-neu.sh:12`); matches
  grkizi/klkizi/schlafzi TOMLs at a glance · related: PAR.T02, PAR.T13 · [H16]

## modules/sensortask-dev.py

- **PAR.N224** DRIFT · `modules/sensortask-dev.py:91,97` — "sysfunct = System_Service(debug=debug)" /
  "SGP40_Reader(i2c1, sgpCompCallback, trigger_sec=1," — Legacy dev entry point cannot run against the
  current legacy drivers (missing required `asy_ntp_callback`/`asy_cfg_callback`, unknown
  `trigger_sec`), and `build-dev.sh` never freezes it — a stale bench file, not a parity target ·
  covered-by: PAR.S14 · [H16]
- **PAR.N225** SETTLED · `modules/sensortask-dev.py:89-90,103-104,428` — "#watchdog = WDT(timeout =
  8000)" / "#pixel = Neopixel_Signal(16, ..." / "pausetime = await pixel.get_override_led()" — Dev:
  debug on, no watchdog, NeoPixel commented out while the LED routes still reference `pixel` — the quirk
  CLAUDE.md declares out of scope · related: PAR.S14 · [H16]
- **PAR.N226** INVAR · `modules/sensortask-dev.py:94-100` — "i2c1 = asy_i2c_driver.I2C(1, 15, 14,
  frequency=50000)" / "mprls_reader = MPRLS_Reader(i2c0, ..., reset_pin=10, eoc_pin=9" — Legacy dev
  wiring: SHTC3+MPRLS on i2c0, SCD30 (RDY GP11)+SGP40+ISL29125 (INT GP8) on i2c1 SCL15/SDA14; no FRAM,
  no UART despite `build-dev.sh` freezing the UART modules · related: PAR.S14, HW · [H16]

## build-wozi.sh / build-arzi.sh / build-neu.sh / build-dev.sh

- **PAR.N227** ASSUME · `build-wozi.sh:1-3` — "this script has always assumed it's run from inside
  py-include/ regardless of how that directory got there" — Legacy builds assume a `py-include/`
  checkout inside a MicroPython tree and build whatever MicroPython ref that tree holds — the scripts
  pin no version (1.26 is a doc claim); same at build-arzi/neu/dev.sh:1-3 · related: PAR.T15, PAR.T09 ·
  [H16]
- **PAR.N228** DRIFT · `build-wozi.sh:1-3,40` — "PY_INCLUDE_DIR=\"$(pwd)\"" /
  "FROZEN_MANIFEST=\"$PY_INCLUDE_DIR/python/build/manifest.py\"" — All four scripts were edited after
  the initial commit (b6cb852, hardcoded `/home/nico/...` path replaced) — HEAD scripts are not
  byte-identical to what built the fielded firmware · related: PAR.T15, DOC.S21 · [H16]
- **PAR.N229** INVAR · `build-wozi.sh:11-16` — "gzip -9 ./*" / "python3 -m freezefs -s html
  frozen_html.py" — Web files are gzipped then frozen with an unpinned host `freezefs` (`-s` = silent,
  default mount at `/html`) — so a legacy littlefs presumably holds no `/html` (unverified for the
  version used) · related: XCUT.S14, PAR.T08 · [H16]
- **PAR.N230** INVAR · `build-wozi.sh:17-27,30-32` — "cp -r ../CommonDrivers/* ." / "cp
  ./modules/sensortask-wozi.py ../ports/rp2/modules/sensortask.py" — Per-unit frozen set: all
  CommonDrivers + I2C/SPI/FRAM/NeoPixel/SCD30/SGP40 (+BMP3xx on wozi); `_boot.py` and `sensortask.py`
  swapped into `ports/rp2/modules` for the build · related: PAR.T09 · [H16]
- **PAR.N231** INVAR · `build-neu.sh:12,31` — "cp -r ../../../html_raw/arzi/* ." / "cp
  ./modules/sensortask-neu.py" — Neu builds use arzi's HTML with neu's sensortask · related: PAR.T10,
  PAR.T13 · [H16]
- **PAR.N232** INVAR · `build-dev.sh:12,22-23,32-33` — "cp ../IndividualDrivers/asy_uart.py ." / "cd
  ../.. # now inside py-include" — The dev build freezes UART/SHTC3/MPRLS/ISL drivers but does not
  install the custom `_boot.py` or a frozen `sensortask` (stock boot) · related: PAR.S14 · [H16]

## html_raw/general/functions.js

- **PAR.N233** INVAR · `html_raw/general/functions.js:27-39` — "requestData[field] =
  inputFields[field].value; inputFields[field].value = \"\";" — The legacy UI sends every field as a
  string, `""` for untouched fields (= "Unchanged" server-side), and clears inputs after Apply ·
  related: PAR.T10, PAR.S02 · [H16]
- **PAR.N234** INVAR · `html_raw/general/functions.js:48-66` — "parent.style.backgroundColor = color;" /
  "setTimeout(updateCurrentValues, 2000, currentValues);" — Per-field colours from the `result` map
  (Valid green, Unchanged grey, Invalid red, Failed lavender) and a single re-fetch 2 s after Apply ·
  related: PAR.T10 · [H16]
- **PAR.N235** INVAR · `html_raw/general/functions.js:98-112` — "if ((inputFields[key].textContent !==
  \"Off\") && (inputFields[key].textContent !== \"On\")) { // uninitialized" — Switch buttons start
  empty (sends ""), first click sets the given start state, later clicks toggle · related: PAR.T10 ·
  [H16]
- **PAR.N236** LIMIT · `html_raw/general/functions.js:70-81` — "function getColorForCode(value) {" —
  Defined but not called by any legacy page (low) · related: PAR.T10 · [H16]

## html_raw/general/nettimeconfig.html

- **PAR.N237** INVAR · `html_raw/general/nettimeconfig.html:207-214` — "setInterval(updateCurrentValues,
  500, currentTimeStatus);" — Legacy polls `/time/status` and `/net/status` every 500 ms each while the
  page is open · related: PAR.T04, PAR.S07 · [H16]
- **PAR.N238** INVAR · `html_raw/general/nettimeconfig.html:28-48,74-110` — "<p>Valid values: 1 to 63
  characters</p>" / "<input type=\"text\" id=\"input_net_pw\"/>" — UI-stated bounds mirror the handler
  (Hostname 1-63, SSID 2-32, PW 8-63, NTP host 3-1024, offsets ±43200, interval 1-24 h); password
  entered in a plain text field · related: PAR.T10, NET.S17 · [H16]

## html_raw/wozi/index.html

- **PAR.N239** INVAR · `html_raw/wozi/index.html:70-71` — "setInterval(updateCurrentValues, 2000,
  measurements);" — Measurements page polls `/sensors/status` every 2 s and shows raw unrounded values ·
  covered-by: PAR.S07 · [H16]

## html_raw/wozi/sensorconfig.html

- **PAR.N240** DRIFT · `html_raw/wozi/sensorconfig.html:105,195` — "<p class=\"p_dyn\"
  id=\"shtc_result\"></p>" / "result: document.getElementById(\"sgp_result\")" — The SGP40 Apply result
  element id does not exist, so the result text never shows (JS error after colouring) — same in arzi
  and dev (low) · related: PAR.T10 · [H16]
- **PAR.N241** SETTLED · `html_raw/wozi/sensorconfig.html:92` — "Wait time for NTP sync before using
  timestamped backups.<br>0 = never wait." — The UI's documented meaning of `SGPWaitTimeNTP` 0 ·
  covered-by: PAR.S01 · [H16]
- **PAR.N242** INVAR · `html_raw/wozi/sensorconfig.html:29-50,118,130,142` — "0 = Compensation off / use
  Altitude" / "2 ** <input" / "(2 ** <input ...>) - 1" — UI semantics: AmbPres starts continuous
  measurement; Altitude only used with AmbPres 0; oversampling/filter entered as exponents; HEAD label
  "(2**x)−1" differs from the fielded "2 ** x" (2bda920) · related: PAR.T10, PAR.T15 · [H16]
- **PAR.N243** LIMIT · `html_raw/wozi/sensorconfig.html:239` —
  "updateCurrentValues(currentSensorValues);" — Sensor config values are fetched once on load (and 2 s
  after Apply), never polled · related: PAR.T10 · [H16]

## html_raw/wozi/systemledconfig.html

- **PAR.N244** SETTLED · `html_raw/wozi/systemledconfig.html:63-66` — "Auto On and Off times must be on
  the <b>same day</b>.<br> Auto On must be <b>before</b> Off" — The legacy UI documents the
  no-midnight-wrap window as a user constraint · related: LED (A.4 midnight-window decision) · [H16]
- **PAR.N245** INVAR · `html_raw/wozi/systemledconfig.html:32-47` — "Valid values: 0 to 255<br>Default =
  0" / "Valid values: 0.5 to 60.0<br>Default = 1.0" — LED command fields document defaults used when
  left blank · related: REST.S10 · [H16]
- **PAR.N246** INVAR · `html_raw/wozi/systemledconfig.html:300-306` — "setInterval(updateCurrentValues,
  500, currentStatusSys);" — `/led/status` and `/system/status` polled every 500 ms; LED config fetched
  once · related: PAR.T04, PAR.S07 · [H16]
- **PAR.N247** INVAR · `html_raw/wozi/systemledconfig.html:174-177` — "<i>- mempause</i> pause backups
  for 5 minutes" — System commands exposed through a free-text field · related: PAR.T10 · [H16]

## html_raw/arzi/index.html, html_raw/arzi/sensorconfig.html, html_raw/arzi/systemledconfig.html

- **PAR.N248** INVAR · `html_raw/arzi/sensorconfig.html:1-179` — (diff vs wozi) — Arzi pages = wozi
  pages minus every BMP388 card/field/counter; otherwise identical (also used by neu) · related: PAR.T10
  · [H16] ⟨quote not matched at the anchor⟩

## html_raw/dev/index.html, html_raw/dev/sensorconfig.html, html_raw/dev/systemledconfig.html

- **PAR.N249** INVAR · `html_raw/dev/sensorconfig.html:109-231` — "<h2>ISL29125 - RGB Brightness</h2>" /
  "Valid values: -1 to 3600000" — Dev pages add SHTC3/MPRLS/ISL29125 cards (ISL auto-clear −1 off / 0
  immediate / >0 ms) — bench only · related: PAR.S14 · [H16]
- **PAR.N250** DRIFT · `html_raw/dev/sensorconfig.html:143-146` — "<h2>Pressure Offset [K]</h2> ...
  Valid values: -500.0 to 500.0 K" — MPRLS pressure offset labelled in K (low) · related: PAR.S14 ·
  [H16]

## html_raw/general/favicon.ico

- **PAR.N251** INVAR · `html_raw/general/favicon.ico` — (binary, 15406 B, 3 icons 16/32 px) — Served
  gzip-compressed at `/favicon.ico` by every legacy unit · covered-by: PAR.S15 · [H16]

## Commit messages (chronological)

- **PAR.N252** SETTLED · `commit b64857d` — "arzi/neu pressure compensation (accepted limitation) ...
  the hotspot password (accepted for now)" — Owner accepted arzi/neu's missing pressure compensation as
  a limitation and the hardcoded hotspot password "for now"; the pressure-compensation acceptance is not
  restated in SPECIFICATION (grep "compensat" finds only SGP40/SCD30 compensation) (low). · status:
  hotspot pw tracked: CLAUDE.md "one known real credential"; pressure-compensation acceptance UNTRACKED
  (low) | related: PAR.T* · [H17]
- **PAR.N253** DRIFT · `commit 2bda920` — "python/IndividualDrivers/asy_bmp3xx_driver.py (deployed
  production driver): same tuple correction ... modules/sensortask-wozi.py ...
  html_raw/wozi/sensorconfig.html" — The IIR fix edited the reference-only legacy tree, so
  `python/`/`modules/`/`html_raw/` no longer match the firmware actually deployed (which still uses
  0,2,4,...,128); deployed units' stored BMPFiltCoeff values (2,4,8,...) are outside the refactor's
  accepted set {0,1,3,7,...}, and the migration consequence is stated nowhere (SPECIFICATION has no
  IIR/FiltCoeff migration note). · status: UNTRACKED | related: PAR.T* · [H17]
- **PAR.N254** SETTLED · `commit 0c54c6f` — "BMP3xx's raw-value wire format (index-based in legacy) is
  confirmed the intended, final design ... \"empty string means don't change\" convention is confirmed
  deliberately replaced by \"an omitted key means don't change\"" — Two legacy REST wire-format
  conventions deliberately dropped (field-migration impact on any legacy client/UI). · tracked:
  DRIVER_SPEC (now SPECIFICATION Part C.5) per fceca0d | related: PAR.T* · [H17]
- **PAR.N255** SETTLED · `commit b6cb852` — "modules/_boot.py itself stays untouched (targets the
  deployed 1.26 firmware, a different version, per CLAUDE.md's hard rule)" — _boot.py import rule. ·
  tracked: CLAUDE.md hard rule, BACKLOG #1 | - · [H17]
- **PAR.N256** DRIFT · `commit b6cb852` — "build-*.sh: removed the hardcoded /home/nico/rpi_pico/...
  path; each script now derives its own FROZEN_MANIFEST path" — A second edit to the reference-only
  legacy tree (build-*.sh) after 2bda920; the build scripts differ from what produced the deployed
  images. · status: UNTRACKED as a "legacy tree ≠ deployed" fact (low; build scripts don't change
  runtime behaviour) | related: PAR.T* · [H17]
- **PAR.N257** DRIFT · `commit e05f015` — "it runs the deployed fleet's actual MicroPython 1.24.1 and
  holds code changes made directly on-device that were never copied to any host machine" — Contradicts
  CLAUDE.md/BACKLOG #3/SPECIFICATION.md:3426 ("deployed units run MicroPython 1.26"); also shows at
  least one unit carried on-device code not in the repo, weakening "legacy tree = deployed behaviour".
  dev_legacy/README.md:671 now only says the bench unit ran 1.24.1. · status: UNTRACKED (fleet version
  and on-device divergence never reconciled) | related: PAR.S10, PAR.T* · [H17]
- **PAR.N258** NOTE(PAR) · `commit 43364bc` — "Applied arzi/klkizi/grkizi/schlafzi's SCD30 i2c0 bus the
  same timeout=200000 clock-stretch headroom ... its absence there was a driver limitation, not a
  considered per-device difference" — Refactored field devices deliberately differ from legacy I2C
  timing; legacy arzi/neu build no BMP3xx. · tracked: devices/*.toml (bus.i2c0 timeout),
  SPECIFICATION.md:383 | related: PAR.T* · [H17]
