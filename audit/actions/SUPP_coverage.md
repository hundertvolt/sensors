# A-L supplement — coverage gaps for range-named and moved clauses (HEAD 8a70891)

Closes the input generator's gaps: register State lines naming a unit range (G8/R61 "U10-U34", LEAD/R30 "U12-U17")
reached only the range's endpoints, and four clauses moved into wave-1 units by register fixes after those units
were written. Every (unit, block) below was checked against the block's State as the register reads now, the unit's
action file and its verify file; every site was opened at HEAD `8a70891`. Unit files owned per plan 5.0 (CORE:
`system_service.py`, `base_classes.py`, `config_manager.py`, `print_log.py`, `api_response.py`; ALGO: `math_helpers.py`,
`voc_algorithm.py`, `crc_checks.py`, `framing_codecs.py`; BUS: `asy_i2c_driver.py`, `asy_spi_driver.py`,
`asy_uart_driver.py`; PLAT: SPEC Part F and the `toolchain/versions.toml` pin, no Python file; SENS: the four sensor
drivers; STOR: `asy_fram_driver.py`, `asy_fram_manager.py`). File names are HEAD's; A.U10.37 later renames
`base_classes`/`config_manager`/`print_log`/`api_response`/`system_service` with the `asy_` prefix — A-C carries the
names through. Permanent text quoted below carries no audit ID (rule 6).

## Explicit-`Any` inventory at HEAD (G8/R61), per unit

`grep -n '\bAny\b'` over each owned file; ANN401 per-file exemptions from `pyproject.toml:216-310` (25 entries, the
register's count holds).

| unit | file | explicit `Any` sites | ANN401 exemption | result |
|---|---|---|---|---|
| U11 | `src/system_service.py` | `:29, 66, 177, 184, 216, 218, 257, 275` | none | covered by A.U10.46 (lists exactly these eight) |
| U11 | `src/base_classes.py` | `:21` import; `:189` `_get_dict_cfg(callback=)`; `:232`, `:399` `get_error_sources() -> list[Any]`; `:285` `_push_callbacks`; `:288` `_get_callbacks` | none | A.U11.S02 |
| U11 | `src/config_manager.py` | `:20` import; `:121` `coerce_numeric() -> tuple[bool, int \| float \| Any]`; `:147` `type_or_range_error() -> tuple[bool, Any]`; `:240` `_get_values() -> list[Any] \| None` | none | A.U11.S01 |
| U11 | `src/print_log.py` | `:19` import; `:49` `_FramManager.get_chunk() -> _FramChunk[Any] \| None`; `:112, 116, 120, 124, 128` `**kwargs: Any` on `err/wrn/one/evt/all`; `:203, 208` on `err_s/wrn_s`; `:238` `self.fram: _FramChunk[Any] \| None` | `:259` `"src/print_log.py" = ["ANN401"]` (category 1, comment `:253-258`) | A.U11.S03 |
| U11 | `src/api_response.py` | `:17` import; `:22` `ResponseEnvelope`; `:50` `make_response(result=)`; `:63` `parse_cmd_request()` return; `:86` `post_asy_fct` | none | A.U11.S02 |
| U11 | planned by U11 itself | A.U11.03 emits `_collect_config_stores() -> "list[Any]"`; A.U11.10 plans `run_setups(setups: "list[Callable[[], Coroutine[Any, Any, None]]]")` | — | A.U11.S04 |
| U12 | `math_helpers.py`, `voc_algorithm.py`, `crc_checks.py`, `framing_codecs.py` | none (grep: 0 each) | none | DONE-AT-HEAD |
| U13 | `asy_i2c_driver.py`, `asy_spi_driver.py`, `asy_uart_driver.py` | none (grep: 0 each) | none | DONE-AT-HEAD |
| U14 | (no Python file) | — | — | no owned file |
| U16 | `src/asy_fram_driver.py` | none (grep: 0) | none | DONE-AT-HEAD |
| U16 | `src/asy_fram_manager.py` | `:25` import; `:491`, `:685` `ntp_sync_callback: Callable[[], Coroutine[Any, Any, bool]]`; `:630` `get_error_sources() -> list[Any]` | none | A.U16.S01 |

None of U12's, U13's, U14's or U16's own actions writes an `Any` (grep of `audit/actions/U12.md`, `U13.md`, `U14.md`,
`U16.md`: 0); U11's two are A.U11.S04's.

## U11

### A.U11.S01 Type the config value channel as `CfgValue`, not `Any`
- **Why**: G8/R61 — "no hand-written `Any` remains … genuinely open values `object` … code in U10-U34 — each unit
  clears its files' findings" (owner, 2026-09-28, OR81 "do it in this audit"; typing scheme agent, 2026-09-28). Block
  not in U11's input (State names "U10-U34"). Pending lead point L1 (the Req's "Typing only: no runtime change").
- **Site**: `src/config_manager.py:20` (`from typing import Any, …`), `:121` `coerce_numeric()`, `:145-187`
  `type_or_range_error()` (int branch `:153-162`, float branch `:163-172`), `:240` `_get_values()`, `:282-297` the
  typed getters (as rewritten by A.U11.29); consumers that pass the coerced value to a narrower parameter:
  `src/asy_webserver_service.py:555-557` (`_dispatch_notification_pause()`), `src/asy_isl29125_driver.py:767-778`
  (`_checked_cfg()`), `buildgen/codegen.py:547-553` (emitted `_notification_led_callback()`).
- **Change**: (1) `coerce_numeric(...) -> "tuple[bool, CfgValue]"` — the refusal path returns the input unchanged, so
  `CfgValue` is its honest type; body unchanged. (2) `type_or_range_error(...) -> "tuple[bool, CfgValue]"`. Its int
  branch `if not ok:` (`:155`) → `if not ok or type(check_val) is not int:` and its float branch (`:165`) →
  `if not ok or type(check_val) is not float:` — the added test never fires (after `ok`, `coerce_numeric()` has
  returned an `int` resp. a `float`: `:128-141`), it is the narrowing mypy needs for `_special_bypass()` and the range
  comparisons `:161, :171`; the file's `type()` form, which mypy already narrows at `:174-180` (`len(check_val)` after
  `type(check_val) is not str`). One comment line above the int branch: "# never true after ok; narrows the type".
  (3) `_get_values() -> "list[CfgValue] | None"`. A.U11.29's `_get_typed_values(keys, scalar_type)` is written
  `Any`-free: `scalar_type: "type[T]"` with `T = TypeVar("T", int, float, str, bool)` (`:25` today lists `int, float,
  str`; `bool` joins), returning `"list[T] | None"`; each value is appended only after `isinstance(value, scalar_type)`
  (numeric fields: on the value `coerce_numeric()` returned) — the mypy-visible narrowing, and on MicroPython the same
  exact-type test A.U11.29 states, `bool` not being an `int` subclass there (`py/objbool.c:87-96`). `get_bool_values()`'s
  `return values` after an `any(not isinstance(…))` scan (`:291-297`) is not narrowable and goes with A.U11.29's
  rewrite. (4) `Any` leaves the import `:20`. (5) Consumers — each check is behaviour-neutral (unreachable once
  `is_error` is false for an `int`/`float` field): webserver `:556` `if is_error:` → `if is_error or
  type(coerced_payload) is not int:` (`_PAUSE_TIME_FIELD` is `"int"`; `NotificationPauseFct` takes `int`,
  `asy_webserver_service.py:85`); ISL29125 `_checked_cfg()` keeps its `not isinstance(coerced, (int, float))` arm as
  that narrowing, its comment `:772-774` → "# isinstance: the validator returns a CfgValue; a numeric field's accepted
  value is always int or float, and this narrows it"; generated `_notification_led_callback()`: the emitted
  `if r_err or g_err or b_err or t_err:` (`codegen.py:552`) gains `or type(r) is not int or type(g) is not int or
  type(b) is not int or type(t) is not float` (`request_signal(r: int, g: int, b: int, t: float)`,
  `asy_neopixel_driver.py:145`; mypy follows generated modules silently, `pyproject.toml:359`, so this keeps the
  emitted code honest rather than fixing a reported finding). `config_manager` leaves A.U8.24's baseline list.
- **Blast**: callers of `type_or_range_error()` whose targets are already `CfgValue`: `base_classes.py:349, 389`,
  `config_manager.py:202, 328, 447` (`check_cfg_get_default() -> tuple[bool, CfgValue]` `:190-192`, `new_cfg: CfgValue`
  `:442`), `asy_scd30_driver.py:293` (setters take the config-value union — `pyproject.toml:244-246` FBT001 comment) —
  unchanged · generated every device module with a notification LED: the callback line (`tests_scripts/
  test_buildgen_generate.py` — grep `_notification_led_callback` for a text pin at execution) · js — · tests existing
  `tests/test_config_manager.py:265-327` (`coerce_numeric()` tuples) hold, values unchanged; `tests/
  test_setter_microdot_integration.py:728-732` and `tests/test_asy_webserver_service.py:132` pass the value through
  `Any`-typed test parameters (U24 clears those files); tests forcing a non-numeric coerced value into `_checked_cfg()`
  stay (A.U15.38's blast names them) · new: none — every added check is unreachable by construction (L1 cannot
  drive it without a malformed schema, which A.U11.18 rejects statically) · twin — · docs SPEC C.10 (`:2313-2321`)
  gains: "A value leaving the shared validator is a `CfgValue`; a consumer needing `int`/`float` narrows it with
  `type()`/`isinstance()`, never a cast (C.4.2)." · toml `pyproject.toml` A.U8.24 baseline override (one module
  fewer) · uart —.
- **Depends**: A.U8.24 (baseline); co-lands with A.U11.29 (same getters), A.U11.30 (same function's comment);
  conflicts with A.U15.38 (1) (removes the ISL arm this action keeps) — A-C note 1; L1.
- **Kind**: code

### A.U11.S02 Callback and JSON aliases; clear `Any` from base classes and envelope
- **Why**: G8/R61 — "repeated callback shapes have one named alias each, REST payloads one JSON type alias, 'has this
  method' values and test fakes `Protocol` classes … each unit clears its files' findings" (owner, 2026-09-28, OR81).
  Block not in U11's input.
- **Site**: `src/base_classes.py:19-29` (`TYPE_CHECKING` block — A.U10.46's alias block, same file), `:189`, `:232`,
  `:285`, `:288`, `:399`; `src/api_response.py:15-22`, `:50`, `:63`, `:86`.
- **Change**: aliases added to A.U10.46's block (declared once, imported under `TYPE_CHECKING` by users):
  `PushFct = Callable[[CfgValue], Awaitable[bool]]` (repeated: `base_classes.py:285`, SCD30's dispatch
  `asy_scd30_driver.py:267`); `NtpSyncFct = Callable[[], Awaitable[bool]]` (repeated: `system_service.py:66`,
  `asy_fram_manager.py:491, 685`, `asy_sgp40_driver.py:141`); `AsyncCallback = Callable[[], Awaitable[None]]`
  (repeated: `api_response.py:86`, `asy_webserver_service.py:226`, A.U11.10's `run_setups()`); `JsonMapping =
  Mapping[str, JsonValue]` (A-C note 2). Every one of these callables is only awaited, never handed to
  `create_task()` (`base_classes.py:205, 351, 381`; `api_response.py:98`; `system_service.py:135`;
  `asy_fram_manager.py:540, 605`), so `Awaitable` is exact. `base_classes.py`: `:20` `Callable, Coroutine` →
  `Awaitable, Callable`; `:21` drops `Any`; `CfgValue` joins the `config_manager` `TYPE_CHECKING` import (`:26`);
  `:189` → `callback: "Callable[[], Awaitable[dict[str, CfgValue]]] | None" = None`; `:232`, `:399` →
  `-> "list[ErrorSource]"` (A.U10.46's Protocol: `SensorReader` has `name` `:171`, `get_error_counter()`,
  `reset_error_counter()` `:243`; `ConfigManager` `:221, 261, 264`); `:285` → `dict[str, PushFct]`; `:288` →
  `dict[str, Callable[[], Awaitable[CfgValue]]]` (one site, no alias). `api_response.py`: `:16` → `Awaitable, Callable`
  (+ `Mapping` if `JsonMapping` is not imported ready-made); `:17` drops `Any`; `:22` `ResponseEnvelope = dict[str,
  "str | int | JsonMapping"]`; `:50` `result: "JsonMapping | None" = None`; `:63` returns `"tuple[dict[str, object] |
  None, ResponseEnvelope | None]"` (the body is `request.json`, typed `object`, narrowed by `isinstance(req_json, dict)`
  `:72`); `:86` `post_asy_fct: "AsyncCallback | None" = None`. Both modules leave A.U8.24's baseline list.
- **Blast**: callers `_get_dict_cfg(callback=)` passers `asy_bmp3xx_driver.py:320`, `asy_isl29125_driver.py:905`,
  `asy_scd30_driver.py:248`, `asy_wifi_service.py:720` (each an `async def … -> dict[str, CfgValue]`, `:170, :716,
  :147, :197`) — compatible; push/get registrations `asy_bmp3xx_driver.py:159-168`, `asy_isl29125_driver.py:271-285`
  — compatible; `make_response(result=)` passers `api_response.py:99` (`WriteValidity`, `config_manager.py:212` — a
  `Mapping[str, JsonValue]` only because `Mapping` is covariant, A-C note 2), `asy_webserver_service.py:432, 486,
  501, 531` (`dict[str, Any]` today, U19's); `get_error_sources()` overrides `asy_wifi_service.py:723-727` (list
  concatenation, U18's annotation), `captive_dns.py`, `asy_neopixel_driver.py`, `asy_uart_link_driver.py` (their
  own units) · generated `_collect_error_sources()` (A.U10.46) · js — · tests existing `tests/test_base_classes.py:445,
  795`, `tests/test_asy_webserver_service.py:1016`, `tests/test_asy_uart_link_driver.py:122`,
  `tests/test_captive_dns.py:283` compare `get_error_sources()` with `==` — overlapping types, `strict_equality`
  holds; `tests/test_api_response.py:121-160` (`parse_cmd_request`) read `data["cmd"]` as `object` — holds · new: none
  (typing only) · twin — · docs SPEC C.10 lists the four aliases beside A.U10.46's · toml `pyproject.toml` A.U8.24
  baseline override (two modules fewer) · uart —.
- **Depends**: A.U8.24, A.U10.46 (alias block, `ErrorSource`, `JsonValue`), A.U10.37 (file name).
- **Kind**: code

### A.U11.S03 `print_log`: explicit print keywords, one FRAM chunk Protocol
- **Why**: G8/R61 — "no hand-written `Any` remains … 'has this method' values and test fakes `Protocol` classes … the
  per-file ANN401 exemptions … go file by file as the `Any` sweep clears them" (owner, 2026-09-28, OR81; RF319).
  Block not in U11's input. Pending lead point L1 for the keyword change.
- **Site**: `src/print_log.py:19`, `:30-49` (`_BufT`, `_FramChunk`, `_FramManager`), `:109-128` (`err/wrn/one/evt/all`
  and their comment), `:203-211` (`err_s/wrn_s`), `:238`; `src/asy_fram_manager.py:446`, `:461`
  (`AsyFramChunk.write_into()`/`read_into()`); `pyproject.toml:253-259`.
- **Change**: (1) The five sync methods become `def err(self, *args: object, sep: str = " ", end: str = "\n") -> None:`
  … `print(self.name, *args, sep=sep, end=end)`; `err_s`/`wrn_s` keep `errno`/`wrnno`/`repeat` and take the same `sep`/
  `end`. Defaults equal MicroPython's own (`mp/py/modbuiltins.c:390-391`); `file=`/`flush=` go — no caller passes
  any keyword but `sep`, and only one test does (AST scan of `src/`, `buildgen/` templates, `digital_twin/`, `tests/`,
  `tests_hardware/`: `tests/test_print_log.py:128`). The comment `:109-111` goes. (2) `_FramChunk` becomes
  non-generic: `def get_buffer(self) -> "LockableBuffer"`, `write_into`/`read_into(self, buf: "LockableBuffer", *,
  override_pause: bool = False) -> bool`; `_BufT`, its comment `:33-35` and `TypeVar` go; `_FramManager.get_chunk()
  -> "_FramChunk | None"`; `:238` `self.fram: _FramChunk | None`. For the real chunk to satisfy it,
  `AsyFramChunk.write_into()`/`read_into()` (`asy_fram_manager.py:446, 461`) take `buf: LockableBuffer` — both only
  call `buf.get_buf()` (`:447, 462`), a `LockableBuffer` method (`base_classes.py:74-75`); annotation only. `Any`
  leaves `:19`. (3) `pyproject.toml:259` `"src/print_log.py" = ["ANN401"]` goes (A.U11.38 then adds `["T20"]` — A-C
  note 4); the category-1 comment `:254` "(print()'s sep/end/file/flush; constructors with up to 21 keywords)" →
  "(constructors with up to 21 keywords)" — the tests entries `:260-263` below it keep the category.
  `print_log` leaves A.U8.24's baseline list.
- **Blast**: callers every `pr.err/wrn/one/evt/all/err_s/wrn_s` call (none passes a keyword beyond `errno`/`wrnno`/
  `repeat`, scan above); `make_logger()` `:282-294` and every module passing an `AsyFramManager` — compatible; other
  `write_into`/`read_into` callers `asy_fram_manager.py:444, 454` pass `AsyFramChunkBuffer` — compatible · generated
  — (templates emit no print keyword) · js — · tests existing `tests/test_print_log.py:128` (`sep="-"`) holds; FRAM
  fakes checked structurally against the Protocol: `tests/test_print_log.py:40-87` and `tests/test_base_classes.py:
  52-95` (buffers typed `LockableBuffer` — hold); `tests/test_asy_neopixel_driver.py:470-495`,
  `tests/test_asy_uart_link_driver.py:270-300`, `tests/test_asy_notification_service.py:535-580` (their own buffer
  types) reach constructors typed `AsyFramManager` through existing `# type: ignore[arg-type]` (`:495`, `:304-349`,
  `:565, 579`) — unchanged; `tests/test_asy_webserver_service.py:66-71` fake `err_s/wrn_s(**_kwargs: object)` — a
  wider signature, holds · new: none (typing only; the tested keyword stays) · twin — · docs SPEC C.10 `:2317`
  names `_FramChunk`/`_FramManager` — unchanged wording holds · toml `pyproject.toml` (a dev-tooling change → one
  line in BACKLOG's running list of build-environment changes, CLAUDE.md "Pull request workflow") · uart —.
- **Depends**: A.U8.24; co-lands with A.U11.16 (same `__init__`/`_write`/`_read` and header), A.U11.15 (same class),
  A.U11.38 (same `pyproject.toml` entry); A.U16.16 edits nearby FRAM driver comments only.
- **Kind**: code | rule

### A.U11.S04 Keep U11's new annotations free of `Any`
- **Why**: G8/R61 — "no hand-written `Any` remains" (owner, 2026-09-28, OR81); A.U11.03 and A.U11.10 plan new
  explicit `Any` (`audit/actions/U11.md:138`, `:361`), which would re-enter A.U8.24's baseline.
- **Site**: A.U11.03 step 6 (`buildgen/codegen.py`, the new `_emit_collect_config_stores()`); A.U11.10 (`src/
  system_service.py`, new `run_setups()`).
- **Change**: A.U11.03's emitted collector → `def _collect_config_stores() -> "list[cm.ConfigManager]":` (the generated
  module imports `config_manager as cm`, `buildgen/codegen.py:309`; the type matches A.U11.03's own
  `config_stores: "Callable[[], list[ConfigManager]] | None"`). A.U11.10 → `async def run_setups(self, setups:
  "list[AsyncCallback]") -> None` (A.U11.S02's alias; every `setup()` is an `async def … -> None`).
- **Blast**: as A.U11.03 and A.U11.10 · generated every device module's collector line · tests
  `tests_scripts/test_buildgen_generate.py` text pins, if any, follow A.U11.03 · docs — · toml — · uart —.
- **Depends**: A.U11.03, A.U11.10, A.U11.S02 — A-C folds this into those two actions.
- **Kind**: code

## U15

### A.U15.S01 Scale the ISL29125 thresholds inside the device session
- **Why**: LEAD/R30 — "No races (SPEC C.8's device-session model): every per-call input a multi-step device operation
  keeps in a shared buffer is written inside the device-session hold, never before it"; State "review in U12-U17 —
  every driver's shared buffers checked for the same staging-before-hold shape" (owner, 2026-09-29, OR109 "No races
  allowed (see specs)"; OR109.a (0)); precedent: ISL29125 shadow state captured before the lock (owner, 2026-09-15,
  BACKLOG.md:98-101). Block not in U15's input.
- **Site**: `src/asy_isl29125_driver.py:1161-1172` `ISL29125_I2C.set_thresholds()`.
- **Change**: the race at HEAD: `set_thresholds()` reads the resolution shadow and builds `packed` (`:1165-1170`)
  before `async with self.i2c_isl29125` (`:1171`), whose `acquire()` yields while the lock is held
  (`mp/extmod/asyncio/lock.py:33-38`). `configure(resolution=…)` changes `self._resolution` inside that same hold
  (`:1341-1378`). Sequence: the reader's `_switch_range()` (`:597-599`) enters `set_thresholds()` at 16 bits and waits
  while a REST `set_resolution(12)` (`:932-945`) holds the session in `configure()`; it then writes 16-bit-scaled
  thresholds to a chip running 12 bits, which stay wrong until `set_resolution()`'s own re-arm queues behind it —
  and with `RangeAuto` off at HEAD there is no re-arm at all. Fix: move `:1165-1170` inside the `async with`, before
  the write, so the scale and the write share one hold; `:1162-1164`'s comment stays and gains one line "Scaled inside
  the session: the resolution shadow may change while this waits for the lock." The only yield inside is the write
  itself; `struct.pack()`'s 4-byte allocation moves into the hold (no await, no bus traffic added).
- **Blast**: callers `_switch_range()` `:597, :599`; A.U15.33's new `_write_thresholds()` calls it (co-land) ·
  generated — · js — · tests existing `tests/test_asy_isl29125_driver.py:670-701` (burst shape, clamping, rescale,
  parking) hold; `:973` (`set_thresholds` poisoned) and `:3263` (address sweep) hold · new: L1
  `tests/test_asy_isl29125_driver.py` — `test_set_thresholds_scales_to_the_resolution_live_when_it_gets_the_session`,
  modelled on `:3213-3246`: `make_protocol()`, acquire `isl.i2c_isl29125.asy_lock`, create a task
  `isl.set_thresholds(0, 32768)`, `await asyncio.sleep(0)`, set `isl._resolution = 12` (standing in for a `configure()`
  holding the session), release in `finally`, await the task; `mem_writes(i2c)` shows one burst `struct.pack("<HH", 0,
  32768 >> 4)` (fails at HEAD with the unscaled `32768`) · four bus-hazard tiers, unchanged and must pass:
  `tests/test_bus_hazard_multi_device.py:162-` (ISL29125 × SGP40 interleave), `tests/
  test_digital_twin_bus_hazard_concurrency.py` (ISL29125 cases), `tests_hardware/device_scripts/
  isl29125_same_device_rw_concurrency.py`, `bus_concurrency_isl29125_write_vs_siblings.py` (flash), `tests_hardware/
  bench/test_bus_concurrency_under_api_load.py` (bench) — the change adds no transaction and moves none · twin — (chip
  model unchanged) · docs SPEC C.8's new sentence (A.U12.18) gains ", and a value derived from shared driver state is
  derived inside the same hold (the ISL29125's resolution shadow)" — A-C note 6 · toml — · uart —.
- **Depends**: co-lands with A.U15.33 (same threshold path), A.U12.18 (C.8 sentence) — A-C merges.
- **Kind**: code | test

## U16

### A.U16.S01 Clear explicit `Any` from the FRAM manager
- **Why**: G8/R61 — "no hand-written `Any` remains … repeated callback shapes have one named alias each … each unit
  clears its files' findings" (owner, 2026-09-28, OR81). Block not in U16's input.
- **Site**: `src/asy_fram_manager.py:24-25` (`TYPE_CHECKING` imports), `:491`, `:630`, `:685`.
- **Change**: `:491` and `:685` `ntp_sync_callback: "NtpSyncFct"` (A.U11.S02's alias; the callback is only awaited,
  `:540, :605`); `:630` `-> "list[ErrorSource]"` (A.U10.46's Protocol; `AsyFramManager` has `name` `:623`,
  `get_error_counter()` `:639`, `reset_error_counter()` `:739`); `:24` `from collections.abc import Callable, Coroutine`
  → `Callable` (still used by `mempause`, `:49, 419, 490`); `:25` `from typing import Any` goes; `NtpSyncFct`,
  `ErrorSource` imported under `TYPE_CHECKING` from `base_classes` (runtime import of `LockableBuffer` from it exists
  already). `asy_fram_manager` leaves A.U8.24's baseline list. (`AsyFramChunk.write_into()/read_into()`'s parameter
  widening is A.U11.S03's.)
- **Blast**: callers `get_timestamped_chunk()` — `asy_sgp40_driver.py:181-183` passes `fram_ntp_callback` (typed
  `Coroutine[Any, …]` until A.U15.43 adopts the alias — compatible either way); generated `_collect_error_sources()`
  (A.U10.46) · generated — · js — · tests `tests/test_asy_fram_manager.py` timestamped-chunk constructions pass `async
  def` callbacks — compatible · new: none (typing only) · twin — · docs — · toml `pyproject.toml` A.U8.24 baseline
  override (one module fewer) · uart —.
- **Depends**: A.U8.24, A.U10.46, A.U11.S02.
- **Kind**: code

## LEAD/R30 review record (U14, U15, U16)

Shape searched: a shared (instance-level) buffer or shadow a multi-step device operation writes, or derives a
per-call value from, outside the device-session hold with an await (lock acquisition included) between. Fact used
throughout: `Lock.release()` never yields (`mp/extmod/asyncio/lock.py:21-29`), `acquire()` yields only when the
lock is taken (`:33-38`); `Lockable.__aexit__` only releases (`src/base_classes.py:39-51`), so code right after an
`async with` runs before any other task.

| unit | driver | shared buffer / state | where filled and consumed | verdict |
|---|---|---|---|---|
| U14 | — | PLAT owns no driver (plan 5.0: Part F, `versions.toml` pin) | — | reviewed, none |
| U15 | SCD30 | `SCD30_I2C._buffer` (18 B, `:447`) | `_send_dev_command()` `:459-470`, `_read_dev_register()` `:477-487`: only called with an `i2c` from inside `async with self.i2c_scd30` (`:456, 474, 514, 578, 599-607`) | safe |
| U15 | SCD30 | `SCD30_I2C.crc` (`CRC8`, `:448`) | `add_into()`/`check_from()` in the same two helpers and `read_measurement()` `:613-619`, all inside the hold | safe |
| U15 | SCD30 | cached `_co2`/`_temperature`/`_relative_humidity` | written at `:628-630` inside the hold; setters validate scalar arguments before the hold (`:534-576`), nothing shared | safe |
| U15 | SGP40 | `_command_buffer`/`_default_command_buffer`, `_reply_buffer`, `_measure_command`, `crc` | reviewed by U12 (ledger `U12.md:533`; A.U12.18 fixes `measure_raw()`); re-read at HEAD `:612-616, 623-632, 670-688`: unchanged | covered by A.U12.18 |
| U15 | SGP40 | reader's FRAM backup buffer | `self.ts_storage.get_buffer()` per read cycle, local (`:229`) | safe (not shared) |
| U15 | BMP3xx | no scratch buffer (C.3); I2C helper `_scratch` is U13's (`U13.md:532`) | `_temp_calib`/`_pressure_calib` assigned together without an await (`:522-539`), read in `_read()`'s sync compensation | safe |
| U15 | ISL29125 | config shadow in `configure()` | mutated and written inside one hold (`:1341-1378`); `_settle_until_ms` right after release reads `cycle_ms()` with no await between (`:1379-1383`) | safe |
| U15 | ISL29125 | config shadow in `reset()` | chip reset inside the hold (`:1433-1435`), shadow reset `:1440-1448` after release with no await between; only caller `setup()` `:1419` | safe |
| U15 | ISL29125 | resolution shadow → `set_thresholds()` scale | read `:1165` before the hold `:1171` | **race — A.U15.S01** |
| U15 | ISL29125 | `read_counts()`/`get_config_snapshot()`/`_read_byte()` results | local values inside the hold (`:1122, 1143, 1389-1390`) | safe |
| U16 | FRAM_SPI | `_id_buf`, `_status_buf`, `_addr_buf`, `_wrsr_buf` (`asy_fram_driver.py:118-121`) | filled and consumed synchronously inside one CS cycle under the bus lock (`:154-195, 233-266`); `setup()`/`set_write_protected()` take the bus lock only (`:357-398`) | safe (no await between fill and use); both locks for every path: covered by A.U16.10 |
| U16 | chunk | `_sb_buf`, `_check_buf`/`_check_mv`, read-progress cells, per-chunk `crc` incremental state (`asy_fram_manager.py:61-84`) | used only inside `_op_lock` (`:97, 129, 390`) and inside `async with self.fram` (`:271, 296, 361`); CRC `add_into()`/`run_inc()`/`check_inc()` at `:277, 315, 330, 347` inside both | safe |
| U16 | chunk | CRC instance per chunk | fresh per `get_chunk()`: `CRC8()` (`print_log.py:238`), `CRC32()` (`asy_sgp40_driver.py:182`), `CRC_Pass()` default (`asy_fram_manager.py:651, 693`) — never shared across chunks | safe |
| U16 | chunk | caller data buffers | fresh per call (`get_buffer()` `:430-431, 512-515`; `print_log.py:249, 262`); the timestamp is packed into the caller's own buffer before `_op_lock` (`:557-563`) — not shared | safe |

## Ledger
| register block | unit | clause for this unit (short) | result |
|---|---|---|---|
| G8/R61 | U11 | clear the unit's files' explicit `Any`; per-file ANN401 exemptions go | new: A.U11.S01, A.U11.S02, A.U11.S03, A.U11.S04 (4); `system_service.py` covered by A.U10.46 |
| G8/R61 | U12 | same | DONE-AT-HEAD: no explicit `Any` in the four ALGO files (grep 0), no ANN401 entry; U12's actions add none |
| G8/R61 | U13 | same | DONE-AT-HEAD: no explicit `Any` in the three BUS files (grep 0), no ANN401 entry; U13's actions add none |
| G8/R61 | U14 | same | no owned file: PLAT owns SPEC Part F and the `versions.toml` pin (plan 5.0); U14's actions add no `Any` (grep 0) |
| G8/R61 | U16 | same | new: A.U16.S01 (1); `asy_fram_driver.py` DONE-AT-HEAD (grep 0) |
| LEAD/R30 | U14 | review shared buffers for staging before the hold | reviewed, none — no driver |
| LEAD/R30 | U15 | same | new: A.U15.S01 (1, ISL29125 `set_thresholds()`); SCD30, BMP3xx, rest of ISL29125 reviewed, none; SGP40 covered by A.U12.18 (list above) |
| LEAD/R30 | U16 | same | covered by A.U16.10 (`setup()`/`set_write_protected()` scratch under both locks); every other FRAM buffer reviewed, none (list above) |
| G5/R19 | U3 | "never as SGP40 'no backup' (A.U3.09)"; "persisted once, by `ConfigManager` …, callers print (A.U3.05)" | covered by A.U3.09 (SGP40 w10/e14/e15 → console; `None` chunk buffers persist 20 ALLOC) with A.U3.04 (FRAM layer persists the read fault, CRC-invalid copies and pause once), and A.U3.05 (`ConfigManager` persists 34/24, the eleven callers print) — both cite G5/R19 in Why (`U3.md:136, 218`); only the ledger row was missing |
| G4/R54 | U5 | "the sites move with U5: the constants A.U5.05, A.U5.09 and A.U5.10 introduce are tagged" (a U8 clause) | covered: A.U5.05 (`_DEFAULT_*` webserver constants), A.U5.09 (`_DEFAULT_WIFI_REFRESH_SEC` in `WifiConfig`), A.U5.10 (`NtpTiming` defaults) create them; A.U8.04, A.U8.10, A.U8.09 tag them and depend on those U5 actions (`U8.md:58-61, 101, 106-109`); no U5-own work (A-C note 5) |
| G7/R29 | U6 | "the definitions source of those entries in U6 (A.U6.22-A.U6.26)" | covered by A.U6.22 (free heap), A.U6.23 (reset reason), A.U6.24 (build info), A.U6.25 (DNSSRV history), A.U6.26 (DNS fallback servers); the sixth entry, the window description, has its definitions source in A.U9.01 (`@web AutoOn` description, `asy_notification_service.py:87`) — register fix 2 |
| G3/R36 | U7 | "the `:3215-3218` and THR `:757-759/:1138-1145` corrections are G1/R17's, done by A.U4.07 (E.6.6 via A.U7.25)" | covered by A.U7.25 (E.6.6 `:3195-3237` replaced, SCD30 NVM stated as not an exception row; C.8 `:2164-2175` and THR `:1239-1249` repointed) and A.U4.07 (THR `:757-759, 1138-1145, 1181-1183` and two test comments); U7 ledger row was missing |

## A-C notes
1. A.U15.38 (1) removes `_checked_cfg()`'s `not isinstance(coerced, (int, float))` arm as unreachable; A.U11.S01 keeps
   it as the narrowing a `CfgValue`-typed validator needs (else `_checked_cfg()` returns a `CfgValue` as `int | float`).
   If L1 is decided (a), A.U15.38 (1) keeps the arm with the new comment and only (2) proceeds.
2. A.U10.46's `JsonDict = dict[str, JsonValue]` and `JsonValue`'s `list[…]`/`dict[…]` members are invariant: a
   `dict[str, str]` or `WriteValidity` does not fit them. Parameters take `JsonMapping = Mapping[str, JsonValue]`, and
   `JsonValue`'s containers are `Sequence[JsonValue]`/`Mapping[str, JsonValue]`; `JsonDict` stays for values built
   locally. If the stub subset lacks `collections.abc.Mapping`, `typing.Mapping` is used.
3. Alias adoption across units: `NtpSyncFct` by A.U10.46 (`system_service.py:66`), A.U15.43 (`asy_sgp40_driver.py:141`)
   and A.U16.S01; `PushFct` by A.U15.43/A.U4.04 (SCD30 dispatch `:267`); `AsyncCallback` by U19
   (`asy_webserver_service.py:226`) and A.U11.S04. SPEC C.10 lists them once, with A.U10.46's.
4. A.U11.38 and A.U11.S03 edit the same `pyproject.toml:259` entry: the result is `"src/print_log.py" = ["T20"]`.
5. A.U5.09 and A.U5.10's blasts do not name the tag sites moving (A.U5.05's does for A.U8.04): add "A.U8.10's/A.U8.09's
   tag sites move to the new constants".
6. A.U12.18's SPEC C.8 sentence gains A.U15.S01's clause on derived values.

## Register fixes
1. **LEAD/R30** State: after "review in U12-U17 — every driver's shared buffers checked for the same
   staging-before-hold shape" add "; code in U15 — ISL29125 `set_thresholds()` derives the threshold scale from the
   resolution shadow before taking the session (`asy_isl29125_driver.py:1165-1171`) while `configure()` changes it
   inside the session: scaled inside the hold".
2. **G7/R29** State: "the definitions source of those entries in U6 (A.U6.22-A.U6.26)" → "… in U6 (A.U6.22-A.U6.26),
   the window description's in U9 (A.U9.01)".

## Open points (for the lead; the typing scheme is agent-rank, "(agent, 2026-09-28)")
L1. **"Typing only: no runtime change" versus three seams: read as behaviour-neutral?** (A.U11.S01, A.U11.S03)
   (a) Yes — the validator's value channel is typed `CfgValue` with unreachable `type()`/`isinstance()` narrowing at
   four sites, and `print_log`'s `**kwargs` become explicit `sep`/`end` (no caller passes anything else): every
   hand-written `Any` in U11's files goes, `print_log`'s ANN401 exemption goes; A.U15.38 (1) is withdrawn.
   (b) No — the two seams keep `Any` with a named reason and stay in A.U8.24's baseline, which then cannot end empty
   as A.U8.24 requires, against G8/R61's "no hand-written `Any` remains" (owner, 2026-09-28, OR81).
   Recommended (a); A.U11.S01 and A.U11.S03 are written as (a).
