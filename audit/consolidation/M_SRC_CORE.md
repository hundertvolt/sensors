# A-C merge SRC_CORE (HEAD ff2e004)

Cluster files (CLUSTERS.md "SRC_CORE"): `src/system_service.py`, `src/base_classes.py`, `src/config_manager.py`,
`src/print_log.py`, `src/api_response.py`, `src/math_helpers.py`, `src/crc_checks.py`, `src/framing_codecs.py`,
`src/asy_fram_manager.py`, `src/asy_fram_driver.py`; `src/asy_api_response.py` and `src/asy_base_classes.py` are the
A.U10.37 rename targets (no file at HEAD). Every action of `site_index.json`'s `by_file` for these paths was read in
full, plus the actions a grep of `audit/actions/*.md` found with one of these files or one of their classes/functions in a
Site or Change slot (A.U5.02, A.U10.18, A.U10.21, A.U10.31, A.U10.33, A.U10.35, A.U10.38, A.U10.39, A.U10.45, A.U11.S04,
A.U14.12, A.U19.16, A.U20.41, A.U28.30, A.U30.19's supervisor half, A.U35.41, A.U36.544, A.U36.548, SDEP.15 …).

Conventions used below. Line numbers are HEAD `ff2e004` (unchanged since the A-L reads: `git diff` of `src/` is empty
over the audit commits). Units run in number order (plan 4.1: U0 B0; U1-U8 B1; U9-U34 B2; U35-U37 B3-B5). After A.U10.37
(U10) the files carry their `asy_` names; a stage in U11 or later edits the renamed file. Text a merged change writes into
a permanent file carries actor tags only, never an audit ID (lead rule, AC_NOTES 4). "Blast carried by" names the
merged change (M.SRC_CORE.nnn) or the constituent/other-cluster action (A-ID) that makes each blast edit.

## src/system_service.py (→ `src/asy_system_service.py`)

End state in one paragraph (what every merged change below builds, so a reader can check the whole): `SystemService` owns
the watchdog-feed access (`feed_watchdog()`, latched one-way by `_feed_owned` and `_force_watchdog_starve`) and the
sequence's own feed (`_own_feed()`); one awaited reset path (`_reboot(code, message, action, *, fed=False)`: record →
flush → pause → [own feed] → arm; `_reset_when_due()` runs the reset); one command gate (`_request_shutdown()`, used by
all four words: reboot, bootloader, config reset, FRAM erase) that starts one controlled `_shutdown_sequence()`; the
reset-reason record and boot-phase marker in `machine.mem_backup()` regions 0/1 (codes 0-9, 10 + phase, 20); the boot
setup runner `run_setups()`; `start_tasks()` and `supervise_tasks()` (which spawns `_supervise()` as its own task and
parks on `_never`); inside `_supervise()` one scan per pass with the park point first, the shared escalation block
(task budget or C-stack) fed once and then starved one-way, and the pass-end feed; `LastTaskEnd`; uptime on
`TickSeconds`; the settings store.

### M.SRC_CORE.001 Rename the seven async core modules with `asy_`
- **From**: A.U10.37 (this cluster's seven files; `captive_dns` → `asy_captive_dns` is SRC_NET's half of the same action).
- **Site**: `src/api_response.py`, `src/base_classes.py`, `src/config_manager.py`, `src/crc_checks.py`,
  `src/framing_codecs.py`, `src/print_log.py`, `src/system_service.py` (whole files); `math_helpers.py`,
  `asy_fram_manager.py`, `asy_fram_driver.py` keep their names (no `async def` in `math_helpers.py`; the FRAM two already
  carry the prefix).
- **Change**: `git mv` each to `asy_api_response.py`, `asy_base_classes.py`, `asy_config_manager.py`, `asy_crc_checks.py`,
  `asy_framing_codecs.py`, `asy_print_log.py`, `asy_system_service.py`; every `import`/`from … import` inside the seven
  and inside `asy_fram_manager.py`/`asy_fram_driver.py`/`math_helpers.py` follows (e.g. `asy_fram_manager.py`'s
  `from crc_checks import …` → `from asy_crc_checks import …`; `system_service.py:18-20`, `:31-33`). Logger names
  (`"SYSTEM"`, `"CFGMGR_*"`) and FRAM layout names do not change. Lands before every later-unit stage below, which edit
  the renamed files.
- **Resolved**: —
- **Unit**: U10 (before A.U10.30's graph check; A.U10.33's reorder runs after it).
- **Depends**: —
- **Blast carried by**: importers in `src/` outside this cluster → SRC_NET/SRC_SENS merge A.U10.37; `buildgen/`
  (`codegen.py` imports, `import config_manager as cm`, `CORE_MODULES`, `definitions.py:347`, `validate.py:81`) → A.U20.41
  (GEN); generated modules → A.U20.41; `scripts/lint.sh:36-43`, `scripts/_digital_twin_ci_suite.py:40, 348` → A.U10.37
  (SCR); `pyproject.toml` per-file ignores (`"src/print_log.py" = ["ANN401"]`) → A.U10.37 (TOOL); `tests/test_<old>.py`
  renames and imports → A.U10.37 (TEST_UNIT/TEST_HELP); `digital_twin/` → A.U10.37 (TWIN); `tests_hardware/device_scripts/`
  → A.U10.37 (HW_DEV); SPEC/CLAUDE.md/README/BACKLOG/`tests_hardware/README.md`/`digital_twin/README.md` text → A.U10.37
  (SPEC, DOCS, HW_BENCH, TWIN); UART changelog Class B entry "`framing_codecs`/`crc_checks` renamed; no wire change" →
  A.U10.37 (DOCS, `UART_C_PORT_CHANGELOG.md`).
- **Kind**: code, doc

### M.SRC_CORE.002 Rewrite the module header and the top comment block
- **From**: A.U36.535 (5); A.U11.05 (header line naming the record); A.U0.20 (owner tag on "not a shared mutable value");
  A.S0930.31 (5) (third line); A.U5.08's blast `system_service.py:5` (`set_level_setters()` goes); A.U0.14 dropped here —
  its only `system_service.py` mention is a Blast "no code change (a future goal)", its site is BACKLOG (DOCS).
- **Site**: `src/system_service.py:1-6`.
- **Change**: docstring (three prose lines, the lone `"""` is punctuation):
  line 1 "Generic system-housekeeping service shared by every generated sensortask_<device>.py: uptime, boot signature,
  reset reason, the system commands and their controlled shutdown, the boot setup list, the task supervisor, and a
  persisted system-settings store (config_SYSTEM.cfg)."; line 2 "Every method returns a well-defined value, never
  raises." (unchanged); line 3 "Reset reason and boot phase live in machine.mem_backup() regions 0/1 - RAM that survives
  a reset, never flash or FRAM (owner, 2026-09-26)." Comment block (three lines): "# A live debug-level change is pushed
  through the other loggers' own set_level() methods (the level_setters provider, / # resolved once in setup()), not a
  shared mutable value (owner, 2026-08-11, paraphrase: SharedLevel was reverted for breaking encapsulation). / # The real
  reset a system command takes, after the controlled shutdown and _RESET_DELAY (SPECIFICATION.md Part A.8), is the intent,
  not a failure."
- **Resolved**: A.U0.20 keeps its tag; A.U5.08 removes the `set_level_setters()` name the old line 5 carried; A.U36.535's
  and A.S0930.31's edits are different lines of the same 3-line blocks, written once.
- **Unit**: U11 (stage 0 in U0: A.U0.20's tag is added to the HEAD text, since B0's actor-vocabulary check reads it; U11
  writes the final text keeping the tag). A.U36.535 (5) is pulled from U36 into U11 because the docstring must name the
  generated module the moment the file's design changes; nothing in U36 depends on the timing.
  A-C2 step order: A.S0930.31's part lands in U20, not U11 (it needs A.S0930.13, which lands in U20).
- **Depends**: M.SRC_CORE.001; M.SRC_CORE.008 (provider), M.SRC_CORE.011 (commands), M.SRC_CORE.006 (record).
- **Blast carried by**: `tests_scripts/test_comment_block_cap.py` (src scope) stays green → A.U0.20/A.U36.535 (TSC holds);
  SPEC A.8 command text → A.S0930.41 (SPEC).
- **Kind**: doc

### M.SRC_CORE.003 One import block for the module's final dependencies
- **From**: A.U10.37 (module names), A.U10.46 and A.U11.S02/A.U11.S04 (aliases, `Any` gone), A.U10.31 (quoting),
  A.U10.01/A.U11.01 (`LockedCounter` import gone, `LockedValue`, `TickSeconds`), A.U10.03 (`arm_tick_timer`), A.U10.06
  (`utc_now`), A.U30.19 (`fatal_reported`, `report_if_fatal`), A.U11.05 (`mem_backup`, `reset_cause`, `PWRON_RESET`),
  A.U5.01/A.U5.02 (`DEFAULT_LOG`, `LogConfig`), A.U11.32 (`config_filename`, `instance_name`), A.U10.39 (`name_cfg`),
  A.U19.16 (`FAILED`, `UNCHANGED`, `VALID`), A.U10.38 (`FRAMManager`).
- **Site**: `src/system_service.py:8-38`.
- **Change**: runtime imports: `asyncio`, `gc`, `random`, `time`; `from machine import PWRON_RESET, WDT, Timer,
  mem_backup, reset_cause`; the two aliased `bootloader`/`reset` imports unchanged; `from micropython import const`;
  `from asy_base_classes import LockedValue, TickSeconds, arm_tick_timer, utc_now`;
  `from asy_config_manager import FAILED, UNCHANGED, VALID, ConfigManager, config_filename, instance_name, name_cfg`;
  `from asy_print_log import DEFAULT_LOG, LogConfig, fatal_reported, make_logger, report_if_fatal` (`schema_names` stays imported while
  M.SRC_CORE.017's `get_dict_cfg()` uses it). `TYPE_CHECKING` block: `from collections.abc import Awaitable, Callable`;
  `from typing import Protocol`; `from asy_base_classes import AsyncCallback, ErrorSource, JsonMapping, NtpSyncFct,
  SetupFct, TaskStarter, TimerStarter` (`JsonMapping`: gap pass G2, M.SRC_CORE.017); `from asy_fram_manager import FRAMManager`; `from asy_config_manager import CfgValue,
  ConfigSchema, WriteValidity`; `from asy_print_log import ErrorLog, PrintLogHistory`; `_StoragePause` Protocol and its
  comment stay (the `_storage_pause` attribute keeps its keyword-only call). `Any`, `Coroutine` and the `LockedCounter`
  import go. Annotations are quoted only where they name a `TYPE_CHECKING` symbol (A.U10.31).
- **Resolved**: `SetupFct = Callable[[], Awaitable[bool]]` is new here: A.U11.S04 types `run_setups()` as
  `list[AsyncCallback]` (`Awaitable[None]`), but A.U10.21 makes every `setup()` return `bool`, and a `bool`-returning
  coroutine is not an `Awaitable[None]` to mypy; G8/R61's "one named alias per repeated callback shape" (owner,
  2026-09-28, OR81) settles the alias (two users: `run_setups()` and the generated `_collect_setups()`). The alias is
  declared in `asy_base_classes.py`'s block (M.SRC_CORE.030) (agent, 2026-10-01; "Agent decisions" 1).
- **Unit**: U11 for the file's final form; each earlier stage adds exactly the names its own change needs (U10:
  `LockedValue`, `TickSeconds`, `arm_tick_timer`, `utc_now`, aliases; U30: the two fatal names; U32: none).
- **Depends**: M.SRC_CORE.001, M.SRC_CORE.030 (aliases), M.SRC_CORE.032 (`TickSeconds`, `arm_tick_timer`, `utc_now`),
  M.SRC_CORE.034 (fatal flag), M.SRC_CORE.045 (result words), M.SRC_CORE.046 (`config_filename`), M.SRC_CORE.061
  (`LogConfig`).
- **Blast carried by**: `tests_scripts/test_mypy_any_baseline.py` list shrinks → A.U8.24 (TSC); `pyproject.toml` baseline
  override → A.U10.46 (TOOL); generated `_collect_setups()` annotation uses `SetupFct` → GAP-G1 (GEN, A.U20.06).
- **Kind**: code

### M.SRC_CORE.004 Timing constants: tags and the unfed-tail comment
- **From**: A.U8.08 (`_RESET_DELAY`, `_TASK_CHECK_TIME` tags), A.U8.12 (`_NTP_WAIT_TIME`, `_TIMER_BASE_PERIOD`,
  `_TASK_FAIL_INCREMENT`, `_TASK_FAIL_MAX` tags), A.S0930.33 (`:40` comment).
- **Site**: `src/system_service.py:40-46`.
- **Change**: each line carries its `@tunable` tag per A.U8.02's grammar: `system.reset_delay_s = 4`,
  `system.ntp_wait_s = 120`, `system.timer_base_period_ms = 1000`, `system.task_check_s = 2`,
  `system.task_fail_increment = 100`, `system.task_fail_max = 300`; values unchanged. `:40` comment → "seconds from
  arming the reset to running it; nothing feeds meanwhile, keep < watchdog timeout". `_MAX_STORAGE_PAUSE`, `_NAME` unchanged.
- **Resolved**: —
- **Unit**: U8 (tags; A.U8.02's register check needs them); U11 (the `:40` comment text, with the reset path it
  describes).
  A-C2 step order: A.S0930.33's part lands in U20, not U11 (it needs A.S0930.31, which lands in U20).
- **Depends**: A.U8.01, A.U8.02.
- **Blast carried by**: Part N rows and their Dependants (the unfed-tail dependant of A.S0930.33) → A.U8.08/A.U8.12
  (SPEC); mirror `tests/test_system_service.py:623` → A.S0930.35 (a) (TEST_UNIT); `tests_scripts/test_timer_stagger_no_coincidence.py:7`
  mirror → A.U10.13 deletes the file (TSC); A.U8.02 relation checks (`_RESET_DELAY < timeout`, `_TASK_CHECK_TIME ≪
  timeout`) → A.U8.02 (TSC).
- **Kind**: code, doc

### M.SRC_CORE.005 Named error constants for every SYSTEM code
- **From**: A.U2.04, A.U2.08, A.U3.06 (44 TASK_RETURNED), A.U10.12 (17 TIMER), A.U30.19 (C-stack errno), A.U10.06
  (retires e2).
- **Site**: `src/system_service.py` one block after the imports; call sites `:138, 145, 181, 194, 196, 251, 338` (HEAD).
- **Change**: block `_ERR_CALLBACK = const(14)`, `_ERR_TIMER = const(17)`, `_ERR_STACK_EXHAUSTED = const(25)`,
  `_ERR_TASK_STARTER_RAISED = const(40)`, `_ERR_TASK_BUDGET_REBOOT = const(41)`, `_ERR_TASK_RAISED = const(42)`,
  `_ERR_TASK_CANCELLED = const(43)`, `_ERR_TASK_RETURNED = const(44)`; every `err_s` passes one of them (no literal, no
  arithmetic). No `_ERR_CLOCK`: A.U10.06 removes SYSTEM's e2 site (catalog row 16 loses it). No `_WRN_*`: the dynamic
  `wrnno = n + 1` goes (A.U3.06, console line).
- **Resolved**: the C-stack log line needs a number and the system band 40-44 is full (A.U2.01's table); the shared band
  has 25-29 unassigned, and the condition is recorded by any module's handler, so it takes shared **25
  STACK_EXHAUSTED** "a C-stack overflow was recorded; rebooting" (agent, 2026-10-01; OR2.c list, "Agent decisions" 3).
- **Unit**: U2 (codes 14/16/40-43 at their HEAD sites — A.U2.02's catalog check needs them), U3 (44), U10 (17; e2's
  constant and site go with A.U10.06), U30 (25).
- **Depends**: A.U2.01 (catalog), A.U2.02.
- **Blast carried by**: catalog row 25 → GAP-G2 (GEN, `buildgen/error_catalog.json`, A.U2.01); catalog text of row 40
  "a task or timer starter raised" → A.U10.12 (GEN); tests pinning numbers (`tests/test_system_service.py` 13 lines,
  `tests/test_ntp_fram_system_integration.py:557, 621, 651`) → A.U2.08/A.U3.06 (TEST_UNIT); `tests_scripts/test_bench_no_task_ended_completeness.py:64-66`
  → A.U2.08 (TSC); `tests_hardware/error_log_helpers.py:30-32` → A.U2.08 (HW_BENCH); SPEC C.7/C.7.1 SYSTEM row →
  A.U2.22 (SPEC); CLAUDE.md `:391` and `tests_hardware/README.md:434-436` → A.U2.08/A.U2.23 (DOCS, HW_BENCH); mockdata
  SYSTEM rows → A.U2.25 (js, GEN/WEB).
- **Kind**: code

### M.SRC_CORE.006 The reset-reason record, boot phases and their decode
- **From**: A.U11.05, A.U11.06, A.S0930.15, A.U30.19 (code 20).
- **Site**: `src/system_service.py` new constants after M.SRC_CORE.005's block; new module functions
  `write_reset_record()`, `begin_boot()`, `_purpose_name()`; new methods `boot_phase()`, `get_reset_reason()`.
- **Change**: `_RR_MAGIC = const(0x2A5E0001)`, `_BP_MAGIC = const(0x2A5E0002)`, `_RR_CHECK = const(0x15A5A5A5)`; codes
  `_RR_UNKNOWN = const(0)`, `_RR_POWER_ON = const(1)`, `_RR_WATCHDOG = const(2)`, `_RR_REBOOT = const(3)`,
  `_RR_BOOTLOADER = const(4)`, `_RR_TASK_BUDGET = const(5)`, `_RR_STARVE_ARM_FAILED = const(6)`, `_RR_CONFIG_RESET =
  const(7)`, `_RR_FRAM_ERASED = const(8)`, `_RR_COMMAND_INCOMPLETE = const(9)`, `_RR_BOOT_FAILURE = const(10)`,
  `_RR_STACK_EXHAUSTED = const(20)  # outside the 10 + phase band of boot failures`; public phases `BOOT_CONSTRUCTION =
  const(1)`, `BOOT_SETUP = const(2)`, `BOOT_TASKS = const(3)`, `BOOT_TIMERS = const(4)`, `BOOT_NTP = const(5)`,
  `BOOT_DONE = const(6)`. `write_reset_record(code)`: `mem = mem_backup(0)`; `mem[1] = code`; `mem[2] = code ^ _RR_CHECK`;
  `mem[0] = _RR_MAGIC` (magic last). `begin_boot() -> int` (once per boot, before any construction): reads regions 0/1
  and `reset_cause()`; `PWRON_RESET` → 1; region 0 valid (word 0 `_RR_MAGIC`, word 2 == word 1 ^ `_RR_CHECK`) → its code
  (3-9, 20); region 0 empty (word 0 == 0) and region 1 valid with phase 1-5 → `_RR_BOOT_FAILURE + phase`; region 0 empty
  otherwise → 2; region 0 non-empty and invalid → 0; then clears region 0 (magic first) and marks region 1
  `[_BP_MAGIC, BOOT_CONSTRUCTION, BOOT_CONSTRUCTION ^ _RR_CHECK]`. `SystemService.boot_phase(phase)` writes region 1
  (three word stores, no allocation); `get_reset_reason() -> int` returns the constructor's `reset_reason`.
  `_purpose_name(purpose) -> str`: `"reboot"`, `"bootloader"`, `"config reset"`, `"FRAM erase"` (A.S0930.31 (2)). Every
  stored word is < 2**30 (no heap int).
- **Resolved**: A.U11.05's code table, A.S0930.15's 7-9 and A.U30.19's 20 are one table (7-9 were free, 20 lies outside
  10 + phase); SPEC A.8's code table has one owner — A.U11.05 (its own Blast asks A-C to choose; SPEC cluster carries it).
- **Unit**: U11 (record, decode, phases, 7-9 — A.S0930.15 has no own unit and lands with its gate here); U30 adds the
  `_RR_STACK_EXHAUSTED` line with its user (M.SRC_CORE.016 stage U30).
- **Depends**: M.SRC_CORE.005; the unit fake `mem_backup()`/`reset_cause()` (A.U11.07) and the twin fake (U25's G7/R07
  action) land in the **same commit** (every twin boot calls `begin_boot()`, A.U11.05 Depends).
- **Blast carried by**: generated `build_system()` head (`reset_reason = begin_boot()`), `sysfunct` line
  (`reset_reason=`), `_system_status()` `"ResetReason"`, `main()`'s five `boot_phase()` calls and the header import →
  A.U11.05/A.U11.06 codegen halves (GEN, co-land A.U20.06); `tests/machine.py` fake → A.U11.07 (TEST_HELP); twin fake →
  U25 G7/R07 action pulled into this commit (TWIN); L1 decode table incl. 7-9 and 20 → A.U11.07, A.S0930.21, A.U30.19
  (TEST_UNIT); `tests/_sensortask_scenarios.py:1121` key → A.U11.05 (TEST_HELP); js code-table labels 7-9, 20 →
  A.U23.20 (+ A.U6.23 mock sample) (WEB/GEN); SPEC A.8 code table, F.5.4, A.7 phase sentence → A.U11.05, A.U14.20,
  A.U11.11 (SPEC); `tests_hardware/README.md` reset-code rows → A.U26.28 (HW_BENCH); twin Run 12 code list → A.U25.55
  (TWIN).
- **Kind**: code

### M.SRC_CORE.007 Settings schema comment and the wiring-tag block
- **From**: A.U11.15 (`:59-60` comment), A.U10.39 (name kept, `cfg_schema` private — attribute in M.SRC_CORE.008),
  A.U5.03 (tag target `log`), A.U10.38 (`FRAMManager`), A.U36.544 (`:51` "L.4 → C.14.2").
- **Site**: `src/system_service.py:49-60`.
- **Change**: `:49-51` "# This service's one optional live cross-instance dependency (SPECIFICATION.md Part C.14.2): its
  FRAM / # error-log target, resolved from [device.wiring].fram_target implicitly because this is mandatory / # infra,
  never an [[instance]] entry." (the trailing "(Part L.4)" and the first line's "Part C.14" become the one C.14.2 cite);
  `:52` `# @wiring fram_target FRAMManager log optional kwarg`. `:59` `_VAL_DEBUG_LEVEL` unchanged (its name already
  follows its key); its comment `:59-60` → "# range matches PrintLog's six levels (0 off … 5 all); default 0 matches the
  reference file's own debug=False."
- **Resolved**: —
- **Unit**: U10 (A.U10.38 and A.U36.544's line are pure renames; A.U5.03's tag target lands in U5 as its stage, since
  A.U5.03's generated `log=` wiring reads it); A.U11.15's comment lands U11 with `PrintLog`'s accessor removal
  (M.SRC_CORE.066).
- **Depends**: A.U5.03 (U5), M.SRC_CORE.066.
- **Blast carried by**: `buildgen/validate.py`/`wiring.py` read the tag → A.U5.03/A.U10.38 (GEN);
  `tests_scripts/test_buildgen_validate.py:951-966` staged tag text → A.U5.03 (TSC); SPEC C.14.2 → A.U36.544 (SPEC).
- **Kind**: code, doc

### M.SRC_CORE.008 Constructor: final signature and fixed-size state
- **From**: A.U5.02, A.U5.08, A.U11.03 (1), A.U11.05 (`reset_reason`), A.U11.01, A.U10.01 (`boot_signature` →
  `LockedValue`), A.U10.35 (seven attributes private), A.U11.32, A.U10.39 (`_cfg_schema`), A.U11.12 (1) dropped (see
  Resolved), A.S0930.12/.13 (state), A.U20.06 (`_tasks`, `_task_starters`), A.U32.06 (`_task_names`, `_last_task_end`),
  A.U10.12 (`_sequencer_flag`), A.U10.15 (`_unpause_flag`), A.U0.41 (`:92` tag), A.U10.46 (types); OR138.a (1)
  (`_config_faults`) and routine settlement "initialized-flags" (no `initialized`) (A-C review fold).
- **Site**: `src/system_service.py:63-109`.
- **Change**: signature `(self, asy_ntp_callback: "NtpSyncFct", watchdog: WDT | None = None, storage: "FRAMManager |
  None" = None, level_setters: "Callable[[], list[Callable[[int], bool]]] | None" = None, config_stores: "Callable[[],
  list[ConfigManager]] | None" = None, reset_reason: int = _RR_UNKNOWN, cfg_path: str = "", log: LogConfig =
  DEFAULT_LOG)` — 8 parameters. State: `self.pr = make_logger(log, _NAME)`; `self.name = _NAME` (comment `:76-77`
  kept); `self._storage = storage`; `self._storage_pause = storage.set_pause if storage is not None else None` (comment
  `:73` kept); `self._uptime = TickSeconds()`; `self._uptime_event`, `self._uptime_timer`, `self._reset_timer`,
  `self._storage_timer`, `self._sequencer_timer` (comment `:86-88` → "# Preallocated like the other timers:
  start_timers() re-.init()s it for each stagger wait rather than constructing a / # fresh Timer() each time, which the
  GC would disarm before it fires (SPECIFICATION.md Part F.1)."); `self._sequencer_flag = asyncio.ThreadSafeFlag()`;
  `self._unpause_flag = asyncio.ThreadSafeFlag()`; `self._ntp_is_synced = asy_ntp_callback`; `self._start_time_set =
  False`; `self._boot_signature = LockedValue(init_value=None)` with `:92` → "# None until status_counter() resolves it
  (owner, 2026-07-18) - a later change to this value signals a reboot happened."; `self._watchdog = watchdog`;
  `self._force_watchdog_starve = False` with `:95-96` → "# One-way: set when a reset cannot be armed or the supervisor
  escalates; no feed site feeds after it."; `self._feed_owned = False` ("# One-way: set when a system command is
  accepted; from then only the shutdown sequence feeds (owner, 2026-09-30)."); `self._cfg_schema = _VAL_DEBUG_LEVEL`
  (comment `:98-100` loses "cfg_schema stays public (Part C.5's convention)"); `self.cfgmgr =
  ConfigManager(config_filename(cfg_path, instance_name(_NAME, "")), self._cfg_schema, _NAME, log=log)`;
  `self._level_setters_provider = level_setters`, `self._level_setters: list[Callable[[int], bool]] = []`;
  `self._config_stores_provider = config_stores`, `self._config_stores: list[ConfigManager] = []`; `self._reset_reason =
  reset_reason`; `self._reset_armed = False`, `self._reset_due = asyncio.ThreadSafeFlag()`, `self._reset_task:
  asyncio.Task[None] | None = None`; `self._command_lock = asyncio.Lock()` (reason on the line: "serialises the command
  gate"), `self._shutdown = 0`, `self._shutdown_task: asyncio.Task[None] | None = None`; `self._supervisor_task:
  asyncio.Task[None] | None = None`, `self._supervisor_parked = asyncio.Event()`, `self._never = asyncio.Event()` ("#
  never set: supervise_tasks() and a parked supervisor wait on it for good"); `self._task_starters: list[TaskStarter] =
  []`, `self._tasks: list[asyncio.Task[None] | None] = []`, `self._task_names: list[str] = []`, `self._last_task_end:
  dict[str, str | int] | None = None`; `self._config_faults: list[str] = []` (filled once by `run_setups()`,
  M.SRC_CORE.015). No `initialized` (Resolved (e)). Gone: `self.uptime` (`LockedCounter`), `self.timers_running`, `self.cfg_schema`,
  `self._current_debug_level` and its comment `:103-104`, the registry comment `:106-108` (→ "# Every logger's own
  set_level(), resolved once from the provider in setup() and called on every level change."). Every list is filled once
  at boot and never grows (OR110.a (1)).
- **Resolved**: (a) Parameter order: A.U11.05 lists `…, cfg_path, log, level_setters, config_stores, reset_reason`, but
  A.U5.02/A.U5.18 (G10/R15, owner, OR46.b) require every `src/` constructor with `log` to end `…, cfg_path, log` —
  A.U5.18's L0 check would fail on A.U11.05's order; the tail rule settles it (the three providers go before `cfg_path`;
  generated code passes keywords, so no caller changes). (b) `_current_debug_level`/`get_debug_level()`: A.U11.12 (1)(3)
  keep them "unless U35's G5/R54 verdict removes" them; A.U35.41's verdict table removes them (no product caller) —
  dropped. (c) `timers_running`: A.U10.12 keeps "sets `timers_running` at the end as today", but after A.U10.12
  `start_timers()` awaits inline and nothing reads the flag (grep: only the generated global A.U10.12 removes) — a
  write-only attribute is dead state (G5/R54; OR36.a (1)), so it goes (agent, 2026-10-01; "Agent decisions" 4). (d) Gap pass G2: `watchdog`, `ntp_is_synced`, `boot_signature` have no reader outside the class in `src/` or the generated
  code (the status reads `get_boot_signature()`), so G10/R07 "private by default" makes them `_watchdog`,
  `_ntp_is_synced`, `_boot_signature` (M_SRC_CORE GAP-G12 applied across `src/`); every use follows (M.SRC_CORE.009,
  .013). (e) `initialized`: not added — the routine settlement "initialized-flags" (lead, A-C review, OR36.a (1)) keeps the
  flag only where product code reads it (the FRAM, SPI, UART and logging classes), and nothing reads the service's;
  A.U10.22's L0 check narrows to those classes (A-C review fold; replaces gap pass G2's addition).
- **Unit**: stages — U5: `fram` → `storage`, `history_length`/`debug` → `log`, `level_setters` provider (A.U5.02,
  A.U5.08; A.U5.03's generated `log=`/`storage=` and A.U5.18's check need them); U10: `boot_signature` → `LockedValue`
  (must precede A.U10.01's cap in the same unit, K.03), the seven private names (A.U10.35), `_cfg_schema` (A.U10.39),
  `_sequencer_flag` (A.U10.12), `self._uptime` stays a `LockedCounter` until U11; U11: the final state above
  (`config_stores`, `reset_reason`, `TickSeconds`, gate/ownership/reset state, `_unpause_flag`, `_tasks`/`_task_starters`
  used by the U11 supervisor, M.SRC_CORE.016); U32: `_task_names`, `_last_task_end`. Fold stage U20: `_config_faults` with M.SRC_CORE.015.
- **Depends**: M.SRC_CORE.001, M.SRC_CORE.003, M.SRC_CORE.006, M.SRC_CORE.032 (`TickSeconds`), M.SRC_CORE.046
  (`config_filename`), M.SRC_CORE.061 (`LogConfig`).
- **Blast carried by**: generated `sysfunct` line (`storage=`, `log=`, `level_setters=_collect_level_setters`,
  `config_stores=_collect_config_stores`, `reset_reason=reset_reason`) → A.U5.03, A.U5.08, A.U11.03 (6), A.U11.05 (GEN);
  `_collect_config_stores() -> "list[cm.ConfigManager]"` → A.U11.S04 (GEN); `tests/test_system_service.py` constructor
  calls (24 with `fram=`/`history_length=`/`debug=`), `svc.storage_pause`/`uptime_event`/`start_time_set`/`sequencer_timer`
  reads → A.U5.02, A.U10.35 (TEST_UNIT); `tests/test_ntp_fram_system_integration.py:354, 370, 394`
  (`svc.uptime_event`) → A.U10.35/A.U11.01 (TEST_UNIT); `tests/_boot_contiguity_probe.py:78-86`
  (`sysfunct.sequencer_timer.trigger()`) → A.U10.12/A.U10.35 (TEST_HELP); device scripts constructing `SystemService`
  (`reboot_fallback_starves_the_watchdog.py`, `system_service_restarts_a_real_dead_task.py`, `fram_pause_unpause_and_gating.py`)
  → A.U5.02/A.U11.03 (HW_DEV); `tests/test_system_service.py:1290-1308` (seeds `_current_debug_level`) → A.U11.12's test
  rewritten without the attribute (TEST_UNIT, see GAP-G3); SPEC C.2/C.13/A.7 constructor text → A.U5.02 (SPEC).
- **Kind**: code

### M.SRC_CORE.009 Watchdog access: the latched feed and the sequence's own feed
- **From**: A.S0930.13 (1)(2); A.U31.07 and A.S0930.20 (6) (feed-site pin), A.U10.08 (allow-list).
- **Site**: `src/system_service.py:111-116` `feed_watchdog()`; new `_own_feed()` beside it.
- **Change**: `feed_watchdog()`: `if self._watchdog is not None and not self._force_watchdog_starve and not
  self._feed_owned: self._watchdog.feed()`; comment (3 lines) "# Every feed site but the shutdown sequence's goes through
  here (SPECIFICATION.md Part G.2); once a system command / # is accepted the sequence alone feeds (owner, 2026-09-30),
  so this is a no-op from then on; the starve flag / # stops it one-way too." `_own_feed()`: `if self._watchdog is not
  None and not self._force_watchdog_starve: self._watchdog.feed()`, comment "# The shutdown sequence's own feed, once per
  bounded step; a hung step is never fed."
- **Resolved**: OR31.a (3) "one runtime feed site, the supervisor loop" vs OR120 (feeds move to the sequence while it
  runs) and OR130 (a second, escalation feed call inside the supervisor): the most recent owner decisions win (OR120
  2026-09-30, OR130 2026-09-30); SUPP conflict 8 and OR130.a state the pinned set: `feed_watchdog()`'s body, the
  supervisor's two calls (pass end, escalation), `run_setups()`'s per-unit call, `_own_feed()`'s body, and `_own_feed()`'s
  callers (the sequence and `_reboot(..., fed=True)`).
- **Unit**: U11.
  A-C2 step order: A.S0930.13's part lands in U20, not U11 (it needs A.U20.06, which lands in U20).
- **Depends**: M.SRC_CORE.008.
- **Blast carried by**: `tests_scripts/test_watchdog_feed_sites.py` (one check, the pinned set above) → A.U10.08 +
  A.U31.07 + A.S0930.20 (6) + A.S0930.34 (2) (TSC; the three are one file's content, merged there); L1 latch/ownership
  tests → A.S0930.24, A.S0930.36 (TEST_UNIT); planted-fault scenarios → A.U35.30 (TEST_HELP); twin `feed_count` →
  A.S0930.27, A.U24.17 (TWIN/TEST_HELP); SPEC G.2 `feed_watchdog()` entry and rule sentence → A.S0930.30 (SPEC).
- **Kind**: code

### M.SRC_CORE.010 One awaited reset path: record, flush, pause, own feed, arm
- **From**: A.U11.03 (2)(3), A.U11.04 (`_reset_when_due()`), A.S0930.14 (`_flush_config_stores()` signature and result),
  A.S0930.33 (1)-(3), A.U10.15 (its reset half is A.U11.03/A.U11.04's), A.U10.35 (timer names), A.U10.45 (except-tuple
  order), A.U30.19 (`report_if_fatal`); A.U11.03 (4) dropped — superseded by A.S0930.31 (1) (M.SRC_CORE.011).
- **Site**: `src/system_service.py:118-130` `_reboot()`; new `_flush_config_stores()`, `_reset_when_due()`.
- **Change**: `async def _reboot(self, code: int, message: str, action: "Callable[[], None]", *, fed: bool = False) ->
  None`: (a) `if self._reset_armed: self.pr.evt("Reset already armed, request ignored"); return` (no deinit, no re-arm);
  (b) `self._reset_armed = True` (before the first await); (c) `write_reset_record(code)`; (d) `await
  self._flush_config_stores()`; (e) `self._storage_timer.deinit()`; `self.pr.evt(message)`; `if self._storage_pause is
  not None: self._storage_pause(value=True)`, `self.pr.evt("Storage paused")`; (f) `try:` `self._reset_task =
  asyncio.create_task(self._reset_when_due(action))`; `if fed: self._own_feed()` — the statement immediately before —
  `self._reset_timer.init(period=_RESET_DELAY * 1000, mode=Timer.ONE_SHOT, callback=lambda _b: self._reset_due.set())`;
  `except (MemoryError, OSError) as e:` cancel `self._reset_task` if created; `write_reset_record(_RR_STARVE_ARM_FAILED)`;
  `self._force_watchdog_starve = True`; `self.pr.err("Could not arm reset timer, stopping watchdog feed instead:", e)`
  with the comment "# print-only: FRAM is paused here, so a persisted entry would be dropped; / # the reset-reason record
  (code 6) is this failure's persisted trace." `async def _flush_config_stores(self, *, close: bool = False, step_done:
  "Callable[[], None] | None" = None) -> bool`: `if close:` every store's `close_writes()` first; then per store `try:
  await store.flush_pending()` / `except Exception as e: report_if_fatal(e)`; `await self.pr.err_s("Config flush before
  reset failed:", store.name, e, errno=_ERR_CALLBACK)`; `ok = False` (comment "# the stores are caller-supplied through
  the provider; one failing flush never stops the others or the arm"); `if step_done is not None: step_done()`; `return
  ok`. `async def _reset_when_due(self, action)`: `await self._reset_due.wait()`; comment (3 lines) "# After a system
  command the shutdown sequence already closed and flushed every store, so this pass finds / # nothing; after the
  supervisor escalation it is the last flush, with FRAM paused (its failure reaches the / # console only). No await
  between it and the reset, so no write can start in between."; `await self._flush_config_stores(close=True)`;
  `action()`. `_RESET_DELAY` stays 4 s for every reset.
- **Resolved**: A.U11.03's point 2 order record → flush → pause → arm (G5/R02 register fix, U11 Register fixes) plus
  A.S0930.33's own feed as the statement immediately before `reset_timer.init()` — A.U11.03 (f)'s `create_task` stays the
  first statement of the `try`, the feed sits between it and `init()`, so both texts hold (create_task does not yield).
  A.U11.04's "write accepted inside the armed window is flushed at the reset" is the escalation's alone (A.S0930.33 (2));
  for a commanded reset the pass is a proven no-op.
- **Unit**: U11 (`report_if_fatal(e)` joins the `except Exception` in U30, M.SRC_CORE.016's U30 stage — the one U30 edit
  to this function).
  A-C2 step order: A.S0930.14's part lands in U20, not U11 (it needs A.U20.06, which lands in U20); A.S0930.31's part lands in U20, not U11 (it needs A.S0930.13, which lands in U20); A.S0930.33's part lands in U20, not U11 (it needs A.S0930.31, which lands in U20).
- **Depends**: M.SRC_CORE.006, M.SRC_CORE.008, M.SRC_CORE.009, M.SRC_CORE.041 (`close_writes()`, race-free close),
  M.SRC_CORE.034.
- **Blast carried by**: `tests/test_system_service.py:618-727` reboot tests → A.U11.03 blast + A.S0930.35 (a) (TEST_UNIT);
  new L1 (a)-(e) of A.U11.03, A.U11.04's 3.9 s window test (on the escalation path), A.S0930.35 (d) no-op pin →
  (TEST_UNIT); `tests/_sensortask_scenarios.py:953-973` pumps the loop after `trigger()` → A.U11.03/A.U10.15 (TEST_HELP);
  `tests_hardware/device_scripts/reboot_fallback_starves_the_watchdog.py:38` → `asyncio.run(svc._reboot(_RR_REBOOT, "…",
  action))` → A.U11.03 (HW_DEV); `tests/test_reset_call_site_invariant.py` holds (A.U24.54); SPEC A.4 `:195-198, :226-231`,
  F.2 commanded-reset sentence → A.U11.03/A.U11.04/A.S0930.41 (SPEC); changelog lines D4.04/D4.11 → A.U11.03 (lead
  records, DOCS).
- **Kind**: code

### M.SRC_CORE.011 One command gate and one controlled shutdown for all four words
- **From**: A.S0930.12, A.S0930.14, A.S0930.31 (1)-(3), A.S0930.32 (1); A.U11.03 (4) dropped (superseded by A.S0930.31
  (1)); A.U10.46 (types); OR140.a (12), OR138.a (2) (A-C review fold).
- **Site**: `src/system_service.py:347-351` `reboot_system()`/`reboot_bootloader()`; new `reset_to_defaults()`,
  `erase_fram()`, `_request_shutdown()`, `_shutdown_sequence()`.
- **Change**: `async def reboot_system(self) -> bool: return await self._request_shutdown(_RR_REBOOT)`; likewise
  `reboot_bootloader()` (`_RR_BOOTLOADER`), `reset_to_defaults()` (`_RR_CONFIG_RESET`), `erase_fram()`
  (`_RR_FRAM_ERASED`). `_request_shutdown(purpose) -> bool`, all of it under `async with self._command_lock:` — (1) `if
  self._shutdown: return self._shutdown == purpose`; (2) `if self._reset_armed: self.pr.evt("Command refused: a reset is
  already armed"); return False`; (3) `self._shutdown = purpose`; (4) preflight, only for `_RR_CONFIG_RESET` (`not
  self._config_stores` → refuse "no config store") and `_RR_FRAM_ERASED` (`self._storage is None or not await
  self._storage.erase_ready()` → refuse "FRAM missing, not set up or write-protected"); a refusal prints one `evt` line
  naming its reason, sets `self._shutdown = 0`, returns `False`; (4a) `if self._reset_armed: self._shutdown = 0;
  self.pr.evt("Command refused: a reset is already armed"); return False` — from here to (6) nothing awaits; (5) `try:
  self._shutdown_task = asyncio.create_task(self._shutdown_sequence(purpose))` / `except MemoryError as e:
  self.pr.err("Could not start the shutdown:", e)`, `self._shutdown = 0`, `return False`; (6) `self._feed_owned = True`; then, with no await between, every store's `close_writes()` (one-way) with the
  comment "# From acceptance on nothing writes a store or a chip: no SCD30 write while the sequence runs (owner,
  2026-10-02)." — every config PUT is refused from here (M.SRC_CORE.038's closed-store refusal);
  `self.pr.evt("System command accepted, controlled shutdown for", _purpose_name(purpose))`; `return True`.
  `_shutdown_sequence(purpose) -> None` (comment ≤ 3 lines: "# One controlled shutdown for a system command (owner,
  2026-09-30): no step has a timeout that moves on - / # a hung step is not fed, so the watchdog resets the unit; the
  order is explained in SPECIFICATION.md Part A.8."): S1 `self._own_feed()`; `task = self._supervisor_task`; `if task is
  None or not task.done():` `await self._supervisor_parked.wait()`, `task = self._supervisor_task`, `task.cancel()`,
  `try: await task` / `except asyncio.CancelledError: pass`; `if task is None or not task.done(): return` (no feed
  follows); `self.pr.evt("Shutdown: supervisor stopped, the watchdog is fed by the shutdown alone")`; `self._own_feed()`.
  S2 `ok = await self._flush_config_stores(close=True, step_done=self._own_feed)`; one `evt` line; a PUT that
  already held its module's config lock at acceptance has finished its writes when S2 completes — how S2 waits it
  out (each store given its owner's `_set_lock`, or the sequence taking the module locks) is decided at execution,
  with its reason recorded. S3
  `self._storage_timer.deinit()`; `if self._storage is not None: await self._storage.quiesce(self._own_feed)`; one line.
  S4 cancel every `self._tasks` entry not done, then per entry `try: await t` / `except (asyncio.CancelledError,
  Exception) as e: report_if_fatal(e)`, `self._own_feed()`; one line. S5 only `if purpose in (_RR_CONFIG_RESET,
  _RR_FRAM_ERASED)`: config reset `for store in self._config_stores: ok = await store.delete_file() and ok;
  self._own_feed()`; erase `ok = await self._storage.erase_chip(self._own_feed) and ok`; one line ("done"/"incomplete");
  `code = purpose if ok else _RR_COMMAND_INCOMPLETE`; for reboot/bootloader `code = purpose`. S6 `await
  self._reboot(code, <"Reboot triggered" | "Reboot into bootloader triggered" | "Reboot after config reset" | "Reboot
  after FRAM erase">, system_bootloader if purpose == _RR_BOOTLOADER else system_reset, fed=True)`. No `gc.collect()`;
  allocation: the task object, log strings, the erase's one `bytearray(256)` (M.SRC_CORE.083).
- **Resolved**: A.U11.03 (4) (reboot methods call `_reboot()` directly) is superseded by A.S0930.31 (1) (OR126.a (3),
  owner, 2026-09-30); A.S0930.12's `if self._shutdown: return False` guard for the two old words is replaced by rule (1)
  (SUPP conflict 10). S4's handler: A.U30.19 requires `report_if_fatal()` as every broad handler's first statement; S4's
  `except (…, Exception)` is broad, so it binds `e` (A.S0930.14's `pass` form becomes the call; U30 stage).
  A-C review fold: OR140.a (12) — no SCD30 write can happen while the sequence runs: the only SCD30 writes are
  API-triggered config PUTs, and from acceptance every config PUT is refused (the stores closed in (6)), every
  system command by rules (1)/(2) and `mempause` by M.SRC_CORE.012; tests prove it watertight. OR138.a (2) (as
  corrected by the lead, 2026-10-05): the command is answered at acceptance, so a failed delete is logged and shows as
  reset reason 9 at the next boot (S5's `ok` → `_RR_COMMAND_INCOMPLETE`, M.SRC_CORE.042), never as an HTTP "Failed".
- **Unit**: stages — U11: gate and sequence for `reboot`, `bootloader` and `resetconfig` (S3 uses the manager's
  `quiesce()`, landed in U11 by M.SRC_CORE.083's first stage); U16: `erase_fram()`, the erase preflight and S5's erase
  branch, with the manager's erase trio (M.SRC_CORE.083). The REST words reach the gate in U19/U20 (A.S0930.09/.11).
  S1 needs the supervisor to run as its own task — it does from U11 on (M.SRC_CORE.016's U11 stage spawns `_supervise()`
  inside `start_and_check_tasks()`; U20 only splits the start loop out), which is how this lands before A.U20.06 although
  A.S0930.13 names `supervise_tasks()` (SUPP's LEAD/R32 State puts this code in U11; its Depends on A.U20.06 is met by
  the U11 stage of M.SRC_CORE.016).
  Fold stage (A-C review) — U20: the stores closed at acceptance, with M.SRC_CORE.038's refusal and M.SRC_CORE.041's
  `writes_closed()`, and its L1 proof M.TEST_UNIT.306 (fold F15); the twin proof lands in U25 M.TWIN.104 (fold F15).
  A-C2 step order: A.S0930.12's part lands in U20, not U11 (it needs A.S0930.13, which lands in U20); A.S0930.14's part lands in U20, not U11 (it needs A.U20.06, which lands in U20); A.S0930.31's part lands in U20, not U11 (it needs A.S0930.13, which lands in U20); A.S0930.32's part lands in U20, not U11 (it needs A.S0930.13, which lands in U20).
- **Depends**: M.SRC_CORE.006, .008, .009, .010, .016 (U11 stage); M.SRC_CORE.041/.042 (`close_writes()`,
  `delete_file()`); M.SRC_CORE.083 (`quiesce()`, `erase_ready()`, `erase_chip()`); M.SRC_CORE.038 (closed-store refusal),
  M.SRC_CORE.041 (`writes_closed()`); M.TEST_UNIT.306 (fold F15) (U20).
- **Blast carried by**: generated `_system_cmd_callback` returning the service's answer for five words → A.S0930.11
  (GEN); `_SYSTEM_CMDS` words → A.S0930.09 (SRC_NET); definitions dropdown → A.S0930.10 (GEN); L0-L4 tests →
  A.S0930.20-.29, .34-.40 (TSC, TEST_UNIT, TEST_HELP, TWIN, HW_DEV, HW_BENCH); wear gate counts `"resetconfig"` →
  A.S0930.19 (HW_BENCH); SPEC A.8/A.4/F.2/I.4 and operator docs → A.S0930.30, A.S0930.41 (SPEC, DOCS); U20.md's
  recovery-ladder paragraph ("→ `reboot_system()`") is audit text only (SUPP C, Part B2) — no permanent file.
- **Kind**: code

### M.SRC_CORE.012 Storage pause: refused during a shutdown; the unpause runs in a task that cannot undo a reset's pause
- **From**: A.U10.15, A.S0930.12 (`-> bool`, `_shutdown` refusal), A.U10.35 (names), A.U10.45 (tuple order); adherence
  fix (see Resolved).
- **Site**: `src/system_service.py:353-373` `pause_permanent_storage()`; new `_unpause_waiter()`, `start_asy_unpause()`;
  `:257-258` `get_task_starters()`.
- **Change**: `def pause_permanent_storage(self, duration: int) -> bool`: `if self._shutdown: return False`; then HEAD's
  body with `self._storage_timer`/`self._storage_pause`, the timer callback `lambda _b: self._unpause_flag.set()`, the
  arm failure `except (MemoryError, OSError) as e:` (abort the pause as today); `return True`. `async def
  _unpause_waiter(self) -> None`: `while True: await self._unpause_flag.wait()`; `if self._reset_armed or
  self._feed_owned: continue` with the comment "# A reset or a shutdown has paused storage for good; a late
  auto-unpause must not reopen it."; `self._storage_pause(value=False)` (guarded `is not None`); `self.pr.evt("Storage
  auto-unpaused.")`. `start_asy_unpause()` creates it; `get_task_starters()` → `[self.start_asy_uptime_counter,
  self.start_asy_unpause]` (the flag has one waiter; a restart replaces a dead one).
- **Resolved**: gap between A.U10.15 and A.U11.03/A.S0930.14: at HEAD the unpause runs in the timer callback, so
  `_reboot()`'s and S3's `storage_timer.deinit()` leaves nothing behind; with A.U10.15's deferral a flag set just before
  the deinit wakes the waiter after `_reboot()`'s pause or S3's `quiesce()` and would unpause FRAM during the reset window
  or the erase — against A.S0930.14's design ("S3 deinit's the auto-unpause timer (a mempause auto-unpause cannot fire
  mid-sequence)") and the owner-flagged "every deliberate reset pauses FRAM" (2026-08-05). The check on the one-way
  `_reset_armed`/`_feed_owned` realises the design's stated intent (agent, 2026-10-01; "Agent decisions" 5).
- **Unit**: U11 (A.U10.15 co-lands with A.U11.03/A.U11.04 by its own Depends; A.S0930.12's half is U11's).
  A-C2 step order: A.S0930.12's part lands in U20, not U11 (it needs A.S0930.13, which lands in U20).
- **Depends**: M.SRC_CORE.008, .010, .011.
- **Blast carried by**: generated `_system_cmd_callback` `mempause` (reads the bool) → A.S0930.11 (GEN); every device's
  task list gains one SYSTEM task → A.U10.15/A.U10.19 (GEN, TSC task inventory); `tests/test_system_service.py:640-790`
  pause tests run the waiter and gain `is True` → A.U10.15/A.S0930.12 (TEST_UNIT); new L1 "an unpause fire after
  `_reboot()`/after acceptance leaves storage paused" → GAP-G4 (TEST_UNIT); `tests/test_digital_twin_sensortask_integration.py:785-811`
  → A.U10.15 (TWIN); `tests_hardware/device_scripts/fram_pause_unpause_and_gating.py` starts the waiter → A.U10.15
  (HW_DEV); twin/L2 `mempause` answers "Failed" during a shutdown → A.U25.57 (TWIN).
- **Kind**: code

### M.SRC_CORE.013 Uptime and boot signature on measured ticks; one tick-timer starter
- **From**: A.U10.03 (`start_uptime_timer()`), A.U11.01, A.U11.02, A.U10.01 (K.03 half), A.U10.06 (`_ntp_boot_signature()`
  on `utc_now()`), A.U14.26 (1) dropped for `:144` (V.U18.R10 ruling), A.U2.08 (e1 → 14), A.U0.41 (`:133` tag), A.U10.35
  (names), A.U30.19 (`report_if_fatal`), A.S0930.13 (task list unaffected).
- **Site**: `src/system_service.py:132-146` `_ntp_boot_signature()`, `:198-207` starters, `:266-273` getters, `:375-394`
  `status_counter()`.
- **Change**: `start_uptime_timer()` → `arm_tick_timer(self._uptime_timer, self._uptime_event, self.pr, "uptime")`
  (result unused; the one ENOMEM wording lives there). `get_uptime()` → `return self._uptime.read()`. `status_counter()`:
  no `set_value(0)`/`set_value(None)` on (re)start; loop `await self._uptime_event.wait()`; `uptime = self._uptime.read()`;
  `self.pr.all("System uptime:", uptime)`; `if self._start_time_set: continue`; `utc = await self._ntp_boot_signature()`;
  NTP → `await self._boot_signature.set_value(utc)`, one line, `_start_time_set = True`; `elif uptime >= _NTP_WAIT_TIME:`
  random (comment `:390-391` kept). `_ntp_boot_signature()`: comment `:133` → "# None if not synced yet - a failing NTP
  callback counts as not synced (owner, 2026-07-18); / # the caller falls back to random after _NTP_WAIT_TIME.";
  the callback `try`/`except Exception as e:` keeps its guard (`report_if_fatal(e)` first from U30; `errno=_ERR_CALLBACK`);
  `if not synced: return None`; `return utc_now()` — no `try`, the errno-2 handler goes.
- **Resolved**: A.U10.06 (no `try` around the timestamp) vs A.U14.26 (1) (`except MemoryError` with a heap-int comment):
  ruled for A.U10.06 by V.U18.R10 / U18 register fix 10 (the one reachable failure is a fixed small allocation, not
  caught; CLAUDE.md memory rule, SPEC I.4(a)); a `MemoryError` there ends the uptime task and the supervisor restarts it,
  which A.U11.02 makes harmless (uptime and signature survive the restart). A.U14.26's `tests/test_system_service.py:278-300`
  rename then has no site: those tests go with A.U10.06.
- **Unit**: U11 (A.U10.03's starter, A.U10.06's site and A.U10.01's `LockedValue` are U10 stages — each is a prerequisite
  of U10's own checks: `arm_tick_timer()`'s L1, the `utc_now()` catalog retirement, the cap; U11 writes the rest).
  A-C2 step order: A.S0930.13's part lands in U20, not U11 (it needs A.U20.06, which lands in U20).
- **Depends**: M.SRC_CORE.032 (`TickSeconds`, `arm_tick_timer`, `utc_now`), M.SRC_CORE.008.
- **Blast carried by**: generated `_system_status()` (`await sysfunct.get_uptime()` unchanged) → none; tests
  `tests/test_system_service.py:238-240, 290-330, 332-477, 815-820` → A.U11.01/A.U10.06/A.U10.03 (TEST_UNIT);
  `tests/test_ntp_fram_system_integration.py:354, 370, 394` → A.U11.01 (TEST_UNIT); new L1 (drops, no RTC read, restart
  keeps signature) → A.U11.01/A.U11.02 (TEST_UNIT); driven-cap test K.02 → A.U35.35 (TEST_UNIT); long-uptime scenario →
  A.U35.33 (TEST_HELP); SPEC A.8 `SysUptime`/`BootSignature` sentences → A.U11.01/A.U11.02 (SPEC); changelog D4.20/D4.36 →
  A.U11.01/A.U11.02 (DOCS); `tests_hardware/bench/…rollover` uptime note → A.U26.36 (HW_BENCH).
- **Kind**: code

### M.SRC_CORE.014 Stagger read triggers from one shared start, in task context
- **From**: A.U10.12, A.U10.35 (`_sequencer_timer`), A.U10.45, A.U10.46 (types), A.U30.19 (`report_if_fatal`).
- **Site**: `src/system_service.py:148-175` `_timer_sequencer()` (goes), `:209-214` `start_timers()`.
- **Change**: `async def start_timers(self, triggers: "list[TimerStarter]", timers: "list[TimerStarter]") -> None`: each
  timer starter in order through a guarded call (`except Exception as e:` `report_if_fatal(e)`; `await
  self.pr.err_s("Timer starter", n, "failed:", e, errno=_ERR_TASK_STARTER_RAISED)`; continue); then `t0 =
  time.ticks_ms()`, `slot = _TIMER_BASE_PERIOD // (len(triggers) + 1)`; per trigger k: `wait =
  time.ticks_diff(time.ticks_add(t0, k * slot), time.ticks_ms())`; `if wait > 0:` `try:
  self._sequencer_timer.init(period=wait, mode=Timer.ONE_SHOT, callback=lambda _b: self._sequencer_flag.set())` /
  `except (MemoryError, OSError) as e: await self.pr.err_s("Could not arm the stagger timer, using sleep:", e,
  errno=_ERR_TIMER); await asyncio.sleep_ms(wait)` / `else: await self._sequencer_flag.wait()` (no software timeout: the
  watchdog is the backstop, owner, 2026-07-18); then the guarded starter k. No `timers_running` (M.SRC_CORE.008 (c)).
- **Resolved**: A.U10.12 keeps `timers_running.set()` at the end; dropped (no reader, M.SRC_CORE.008 Resolved (c)).
- **Unit**: U10 (A.U10.12 edits the generator's `main()`/collectors in U10 too); `report_if_fatal` in U30.
- **Depends**: M.SRC_CORE.005 (`_ERR_TIMER`, `_ERR_TASK_STARTER_RAISED`), M.SRC_CORE.030 (`TimerStarter`).
- **Blast carried by**: generated `_collect_trigger_starters()`, `main()`'s two-list call, `timers_running` global and
  `ThreadSafeFlag` import gone → A.U10.12 (GEN); `SensorReader.get_trigger_starters()` → M.SRC_CORE.039 (pointer fixed, gap pass G2); drivers' starter
  split → A.U10.12 (SRC_SENS); `tests/test_system_service.py:479-615` → A.U10.12 (TEST_UNIT); `tests/_sensortask_scenarios.py:347-368,
  774-841` fakes → A.U10.12 (TEST_HELP); `tests/_boot_contiguity_probe.py`, `heap_layout_after_full_boot_sequence.py`,
  twin callers (`test_digital_twin_bus_hazard_concurrency.py:118, 387`, `test_digital_twin_sensortask_integration.py:455`)
  → A.U10.12 (TEST_HELP, HW_DEV, TWIN); real-sequencer proof → A.U10.13/A.U11.39 (TEST_HELP, TSC); SPEC A.7/C.9 → A.U10.14
  (SPEC).
- **Kind**: code

### M.SRC_CORE.015 The boot setup list runs in one method
- **From**: A.U11.10, A.U11.S04 (typed, no `Any`), A.U10.21 (setups return `bool`), A.U20.06 (4) (the caller);
  OR138.a (1) (the `ConfigFaults` list; A-C review fold).
- **Site**: `src/system_service.py` new `run_setups()` beside `start_timers()`.
- **Change**: `async def run_setups(self, setups: "list[SetupFct]") -> None`: `gc.collect()`; `for setup in setups:
  await setup()`, `self.feed_watchdog()`, `gc.collect()`. Comments moved from the generator, two lines at most: "# fed
  after every one-time setup(), never inside a loop, so the batch cannot starve the watchdog however many modules a /
  # device wires; the collect comes after the feed - it is the slow part (the boot placement reset, SPECIFICATION.md
  Part I.4(f.1))." No guard around a setup (every `setup()` is never-raise; one that raises ends the boot, attributed by
  the phase marker); results are discarded (A.U16.17 reads FRAM's state through `fram.initialized`, not this return). After the loop:
  `self._config_faults = [store.module_name for store in self._config_stores if store.faulted]` — the modules whose
  config file existed at this boot but was unreadable or damaged, fixed for the rest of the boot (a repair write
  does not clear it), at most one name per store, built once; new `def get_config_faults(self) -> list[str]: return
  self._config_faults` (the generated `/status` block reads it, M.GEN.008).
- **Resolved**: `AsyncCallback` (A.U11.S04) vs `setup() -> bool` (A.U10.21) → `SetupFct` (M.SRC_CORE.003 Resolved).
- **Unit**: U20 (co-lands with the generator's `_collect_setups()` and the guard changes in one commit, A.U11.10 Depends).
- **Depends**: M.SRC_CORE.009, M.SRC_CORE.030; M.SRC_CORE.043/.049 (`faulted`, `module_name`, U11);
  M.TEST_UNIT.253, M.TEST_UNIT.254, M.TEST_UNIT.259, M.TEST_UNIT.306 (fold F03) (the list's L1 cases, U20).
- **Blast carried by**: generated `_collect_setups()` and `main()` call; generated module loses its `gc.collect()`s and
  feeds → A.U20.06, A.U11.10 codegen half (GEN); `scripts/lint.sh` gc/`method-assign` guards and message →
  A.U11.10 (SCR); `tests_scripts/test_gc_collect_sites.py` set `{("asy_system_service.py", "start_tasks"),
  ("asy_system_service.py", "run_setups")}` and `test_lint_sh.py:41-45` → A.U11.10 + A.U20.06 + A.U27.21 (TSC; A.U27.21's
  single checker supersedes the two files' logic, its table carries the same set); `test_digital_twin_boot_contiguity.py:242-254`
  → A.U11.10 (TSC); `tests/_boot_contiguity_probe.py:125-131`, `heap_layout_after_full_boot_sequence.py:136-139` → A.U11.10,
  A.U30.16 (TEST_HELP, HW_DEV); `tests/_sensortask_scenarios.py` `build()` and direct `build_system()` callers → A.U20.06
  (TEST_HELP, TWIN); L1 `run_setups()` order/feeds/collects → A.U11.10 (TEST_UNIT); stretch scenario → A.U31.03
  (TEST_HELP); SPEC I.4(f.1), A.7 step 16, CLAUDE.md memory rule → A.U11.10 (SPEC, DOCS); BACKLOG chroot line for
  `lint.sh` → A.U11.10 (DOCS).
- **Kind**: code

### M.SRC_CORE.016 The supervisor: start loop, own task, park point, one escalation block, pass-end feed
- **From**: A.U20.06 (3), A.S0930.13 (3)(4), A.U11.03 (5), A.S0930.32 (2), A.S0930.31 (4), A.U31.07, A.U31.17, A.U10.23,
  A.U3.06, A.U2.08, A.U28.30 (3), A.U10.10 (`:217`), A.U14.15 (`:185-187`), A.U36.544 (`:219`), A.U36.548 (`:191`),
  A.U30.19 (3), A.U32.06 (2)(4), A.U10.46 (types), A.U8.12 (constants, M.SRC_CORE.004).
- **Site**: `src/system_service.py:177-196` `_start_task()`/`_log_dead_task()`, `:216-255` `start_and_check_tasks()`;
  new `start_tasks()`, `supervise_tasks()`, `_supervise()`, `_charge_task_budget()`, `get_last_task_end()`.
- **Change** (end state):
  - `async def start_tasks(self, task_starters: "list[TaskStarter]", task_names: "list[str]") -> None`: stores
    `self._task_starters`, `self._task_names`, `self._tasks = [None] * len(task_starters)`; comment "# The boot placement
    reset (SPECIFICATION.md I.4(f.1)): the second of the two one-time boot lists that get a / # placement reset between
    their units - each collect puts the allocator's free-scan index back to zero. / # Not hygiene, not compaction, and
    never in the supervisor below."; `gc.collect()`; per starter `self._tasks[n] = await self._start_task(starter, n)`,
    `await asyncio.sleep_ms(1000 // len(task_starters))`, `gc.collect()`. No `pr.setup()` here (A.U10.10).
  - `async def supervise_tasks(self) -> None`: `self._supervisor_task = asyncio.create_task(self._supervise())`; `await
    self._never.wait()` (comment "# main() never returns and is never cancelled; the loop runs as its own task so a
    system command / # can cancel it and prove it stopped (owner, 2026-09-30).").
  - `_charge_task_budget(budget) -> int`: `return budget + _TASK_FAIL_INCREMENT if budget <= _TASK_FAIL_MAX else
    budget` (check before the step: past the budget the escalation is armed and the value stops, OR105.a (3)).
  - `async def _supervise(self) -> None`, `task_errors = 0`, `while True:` — (i) park point: `if self._feed_owned:
    self._supervisor_parked.set(); await self._never.wait()`; (ii) `escalate = 0`; `if fatal_reported() and not
    self._reset_armed: escalate = _RR_STACK_EXHAUSTED`; (iii) otherwise the scan: `no_fail = True`; `for n in
    range(len(self._tasks)):` `task = self._tasks[n]`; `if task is None or task.done():` `if task is not None: await
    self._log_dead_task(task, n)`; `if self._feed_owned: break`; `task_errors = self._charge_task_budget(task_errors)`;
    `no_fail = False`; `if task_errors > _TASK_FAIL_MAX and not self._reset_armed: escalate = _RR_TASK_BUDGET; break`
    (comment "# Escalate at the first end past the budget, fed once: a scan of every dead task could outlast the / #
    watchdog before the reset is even armed."); `self._tasks[n] = await self._start_task(self._task_starters[n], n)`;
    `self.pr.wrn("Task ended - attempting restart, error counter increased to", task_errors, "-",
    self._task_names[n])`; (iv) escalation block, `if escalate:` `await self.pr.err_s(<"Task error counter above",
    _TASK_FAIL_MAX, "- reboot triggered!"> | <"C stack exhausted - reboot triggered">, errno=<_ERR_TASK_BUDGET_REBOOT |
    _ERR_STACK_EXHAUSTED>)`; `if self._feed_owned: continue` (comment "# Re-checked after the log write, which yields: a
    system command accepted meanwhile owns the reset / # now, and nothing awaits from here until _reboot() marks it
    armed."); `self.feed_watchdog()`; `self._force_watchdog_starve = True`; `await self._reboot(escalate, <"Reboot
    triggered" | "Reboot: C stack exhausted">, system_reset)` (comment "# Resets directly: through the shutdown sequence
    it would run unfed (the starve flag stops the / # sequence's own feed too) and its first step would cancel this very
    loop."); no `return` — later passes keep restarting, unfed, until the reset; (v) decay: `if no_fail:
    self.pr.all("All tasks running.")`, `if task_errors > 0: task_errors -= 1; self.pr.evt("Task error counter reduced
    to", task_errors)`; (vi) `self.feed_watchdog()` (the pass-end feed; a no-op once starved or owned); `await
    asyncio.sleep(_TASK_CHECK_TIME)`.
  - `_start_task(starter, n) -> "asyncio.Task[None] | None"`: `except Exception as e: report_if_fatal(e)`; `await
    self.pr.err_s("Task starter", self._task_names[n], "failed to start:", e, errno=_ERR_TASK_STARTER_RAISED)`.
  - `_log_dead_task(task, n)`: comment "# A finished Task has no .exception()/.result() (Part F.1): awaiting it again is
    how to learn why it / # ended, giving the restart line below real diagnostic content."; `self._last_task_end =
    {"Task": self._task_names[n], "Uptime": self._uptime.read()}`; `try: await task`; `except asyncio.CancelledError:
    await self.pr.err_s("Task", self._task_names[n], "ended: was cancelled", errno=_ERR_TASK_CANCELLED)`; `except
    Exception as e: report_if_fatal(e)`, `… "ended with exception:", e, errno=_ERR_TASK_RAISED)`; `else: … "ended:
    returned", errno=_ERR_TASK_RETURNED)` — exactly one persisted entry per task end, no history comment (the old
    "Previously logged via …" block goes).
  - `get_last_task_end(self) -> "dict[str, str | int] | None"`: returns `self._last_task_end`.
- **Resolved**: (a) A.U31.07's escalation feed "directly followed by the starve-flag assignment (checked by `ast`)"
  (its Blast) vs its Change ("feed, then the entry, the starve flag, `_reboot()`") vs A.S0930.32 (2) (the `_feed_owned`
  re-check after the log write, before the starve flag): one order satisfies all three and OR130.a ("feeds once …, then
  stops feeding one-way and arms the reboot"): entry → re-check → feed → starve → `_reboot()`. The unfed tail then starts
  after the entry (≤ one FRAM write shorter than A.U31.07's), and the scan before it stays ≤ 4 entries. (b) A.U30.19
  (3)'s C-stack escalation "log once … `_reboot()` … then return" with "no feed after it": merged into the same block, so
  OR31.a (3)/OR130.a's "a test pins both call sites and nothing else" still holds (two `feed_watchdog()` calls in
  `_supervise()`), the escalation is fed once like the budget's (the same XCUT.S01 tear risk OR130 fixed), and no feed
  follows `_reboot()`; "then return" is dropped — the loop keeps running unfed exactly like the budget path (A.U11.03
  (5): `main()` never returns). A.U30.19 is itself an agent design on the OR2.c list; this unification goes there too
  ("Agent decisions" 6). (c) A.U10.23's "one `if budget > _TASK_FAIL_MAX:` escalation" after the scan becomes A.U31.07's
  in-scan check (owner OR130); the post-scan check is decay only. (d) A.U3.06 keeps the console text verbatim (bench grep
  `tests_hardware/bench/test_wifi_networking.py:111`) and names the task index; A.U32.06 gives names — the line keeps the
  verbatim text and appends the name. (e) A.U28.30 (3): the local `task` binding removes both `type: ignore`s (`:232,
  :234`). (f) A.U20.06 (3) runs the loop inline in `supervise_tasks()`; A.S0930.13 runs it as a task (SUPP conflict 2):
  the task form, since OR120.a (1) needs the loop cancelled and awaited to done and `main()` must not end.
  (g) `task_names`: A.U32.06 (2) makes it a keyword defaulting to `None` ("task <n>" names) so existing callers hold;
  only tests and device scripts use the default, which OR36.a (1) forbids in product code ("a parameter … that exists
  only so a test … can reach inside") — it is a required parameter; direct callers pass names (GAP-G5; agent,
  2026-10-01; "Agent decisions" 2).
- **Unit**: stages, each a prerequisite of work in its own or an earlier-numbered consumer —
  **U2/U3**: named codes at HEAD sites and one entry per task end (A.U2.02's catalog check needs them; A.U3.06's one
  entry per task end rests on OR56's "a fault or a warning, never both" for one layer and stays — A.U3.11's pair scan
  is narrowed to an error and a warning persisted for one occurrence in one function, OR140.a (7), A-C review fold). **U11** (the body above except `start_tasks()`/`supervise_tasks()`, C-stack and names): `start_and_check_tasks(
  task_starters)` keeps its name and start loop (with `sleep_ms`, the placement-reset comment and without `pr.setup()`),
  stores `self._tasks`/`self._task_starters`, then does what `supervise_tasks()` does (spawns `_supervise()`, waits on
  `_never`); `_supervise()` is final except (ii)'s C-stack branch; log lines name the task index. This is the stage the
  gate/sequence (M.SRC_CORE.011) needs, and A.U16.17's test (U16) asserts its escalation. **U20**: A.U20.06's split —
  the start loop moves to `start_tasks()`, `start_and_check_tasks()` becomes `supervise_tasks()` (no alias), codegen
  emits both calls. **U30**: (ii)'s C-stack branch, `report_if_fatal(e)` in every broad handler of the file, `_RR_STACK_EXHAUSTED`,
  `_ERR_STACK_EXHAUSTED`. **U32**: `task_names`, `_task_names`, `_last_task_end`, `get_last_task_end()`, names in the log
  lines. A.U31.07/A.U31.17 are pulled from U31 into the U11 stage (owner-decided, OR130; writing the loop once).
- **Depends**: M.SRC_CORE.005, .006, .008, .009, .010, .011, .013 (`_uptime`), M.SRC_CORE.034 (fatal flag), M.SRC_CORE.030.
- **Blast carried by**: generated `main()` (`start_tasks(_collect_task_starters(), _collect_task_names())`,
  `supervise_tasks()`) and `_collect_task_names()` → A.U20.06, A.U32.06 (GEN); lambda starters → named methods →
  A.U32.06 (SRC_NET: `asy_uart_comm.py:1133`, `asy_uart_link_driver.py:139`); UART changelog Class B for the named
  starters → A.U32.06 (DOCS); definitions `LastTaskEnd`, `_system_status()` key, js `lasttaskend` format and mock sample →
  A.U32.06 (GEN, WEB); tests: `tests/test_system_service.py` supervisor tests (`:1027-1103`, `:1129-1253`) →
  A.U20.06, A.U11.03, A.U3.06, A.U31.07, A.S0930.24, A.U30.19, A.U32.06 (TEST_UNIT); `tests/_sensortask_scenarios.py`
  fakes and scan-budget/escalation scenarios → A.U20.06, A.U10.08, A.U31.07, A.U35.30 (TEST_HELP); direct callers of
  `start_and_check_tasks()` (`_boot_contiguity_probe.py:78-86, 144`, `heap_layout_after_full_boot_sequence.py:158-166`,
  `test_digital_twin_sensortask_integration.py:482-523`, `test_ntp_fram_system_integration.py:436, 541, 607, 637`,
  `system_service_restarts_a_real_dead_task.py:1, 32`, `flash/test_task_supervisor.py`) → A.U20.06 + GAP-G5 (TEST_HELP,
  TWIN, TEST_UNIT, HW_DEV); feed-site L0 check → M.SRC_CORE.009's blast; `test_fatal_report_sites.py` → A.U30.19 (TSC);
  `test_suppression_form.py` → A.U28.30 (TSC); `test_gc_collect_sites.py` names → A.U20.06 (TSC); twin Run 3 counts,
  Run 12 code 20 → A.U25.36, A.U30.19 (TWIN); bench supervisor escalation → A.U26.28 (HW_BENCH); SPEC A.2/A.4/A.7/C.4.1/
  C.9.1/F.1/F.3/G.2/Part N (`system.scan_budget` formula) and CLAUDE.md `:623, :648` names → A.U10.09, A.U31.07,
  A.U20.06, A.U30.19, A.U14.15, A.U10.14 (SPEC, DOCS); BACKLOG `:68-72` item removed → A.U10.23 (DOCS).
- **Kind**: code

### M.SRC_CORE.017 Settings store: setup, level push, one nested dict shape, write through the store's own schema
- **From**: A.U10.10 (`setup()` begins with `pr.setup()`), A.U10.21 (`-> bool`), A.U5.08 (provider resolved in
  `setup()`), A.U11.03 (1) (config-store provider resolved in `setup()`), A.U11.12 (2) (unreadable store keeps the
  constructed level; (1)/(3) dropped per A.U35.41), A.U11.24, A.U10.36, A.U19.16, A.U10.39 (`name_cfg`, `_cfg_schema`),
  A.U2.08 (e7 → 14), A.U11.13 (setter type), A.U30.19.
- **Site**: `src/system_service.py:287-345` (`setup()`, `get_cfg_schema()`, `get_dict_cfg()`, `_set_dict_cfg()`,
  `set_level_setters()`, `_apply_level()`, `get_debug_level()`, `set_debug_level()`).
- **Change**: `async def setup(self) -> bool`: `await self.pr.setup()`; `if self._level_setters_provider is not None:
  self._level_setters = self._level_setters_provider()`; `if self._config_stores_provider is not None:
  self._config_stores = self._config_stores_provider()`; `await self.cfgmgr.setup()`; `if self.cfgmgr.writable:` read
  `level = await self.cfgmgr.get_int_values(self._cfg_schema)` and `if level is not None: await
  self._apply_level(level[0])` (an unreadable store keeps every logger at its constructed level); `return
  self.cfgmgr.valid`; comment (≤ 3 lines) "# Resolves both boot providers once, then the persisted level: the store's
  value wins over the / # constructor's debug=, an unreadable store keeps the constructed level (Part C.13's
  sync-__init__/async-setup())." `get_cfg_schema()` → `self._cfg_schema`. `async def get_dict_cfg(self)`: `names =
  schema_names(self._cfg_schema)`; `values = await self.cfgmgr.get_dict(names)`; `return {_NAME: values if values is not
  None else dict.fromkeys(names)}` (the `{type_name: {field: value}}` shape every module returns; comment `:302-304` →
  "# the nested {name: {field: value}} shape every SettingsGroup module returns (Part C.6)."). `_set_dict_cfg(data:
  "JsonMapping", cfg_vals: "ConfigSchema") -> "WriteValidity"` (the SettingsGroup call shape — the route passes the raw
  body, U19 A-C note 2; `cfg_vals` unused, the store validates against its own schema): `persisted,
  results = await self.cfgmgr.write_config(data)`; `if not persisted: return dict.fromkeys(data, FAILED)`; `if
  results.get(name_cfg(_VAL_DEBUG_LEVEL)) in (VALID, UNCHANGED):` re-read and `_apply_level()`; comment `:311-313` kept
  minus "every logger's live level stays" wording about `_current_debug_level`. `_apply_level(value)`: per setter `try:
  setter(value)` / `except Exception as e: report_if_fatal(e)`; `await self.pr.err_s("Level setter failed:", e,
  errno=_ERR_CALLBACK)`. Gone: `set_level_setters()` (A.U5.08), `get_debug_level()` and `_current_debug_level` (A.U35.41),
  `set_debug_level()` (M.SRC_CORE.018).
- **Resolved**: A.U11.12 (1)(3) vs A.U35.41 (removal) → removal (the later G5/R54 verdict; A.U11.12 conditions itself on
  it). A.U11.12 (2) uses `self.cfgmgr.writable` (A.U11.20's flag, M.SRC_CORE.043). Gap pass G2's `self.initialized = True` is withdrawn by the routine settlement "initialized-flags" (M.SRC_CORE.008
  (e); A-C review fold); `data: "JsonMapping"` per U19 A-C note 2 (M_SRC_NET gap 4: the webserver's
  `_ModuleLike._set_dict_cfg()` Protocol, M.SRC_NET.111, types the body `JsonMapping`, so every implementer accepts it).
- **Unit**: U11 (U5 stage: `set_level_setters()` → provider resolved in `setup()`; U10 stage: `pr.setup()` first,
  `-> bool`, nested `get_dict_cfg()` with the webserver's `_cfg_values()` (A.U10.36 is one change across both files),
  `name_cfg`, `_cfg_schema`; U11: provider for stores, precedence, `write_config(data)`, result constants from U19 —
  A.U19.16's constants land in U19, so U11 writes the literals and U19 swaps them (M.SRC_CORE.045 stage)).
- **Depends**: M.SRC_CORE.008, .043 (`writable`), .044 (`write_config(data)`), .045 (result constants).
- **Blast carried by**: webserver `_flatten_cfg_values()` → `_cfg_values()` → A.U10.36 (SRC_NET); generated
  `_collect_level_setters()` type `Callable[[int], bool]` → A.U20.41 (GEN); tests `test_system_service.py` level/settings
  tests (`:1259-1308`, every `set_level_setters(` call), `tests/_sensortask_scenarios.py:692-747, 937-940` (uses
  `get_debug_level()`/`set_debug_level()`), `tests/test_asy_webserver_service.py` `_FakeModule.get_dict_cfg()` nested →
  A.U5.08, A.U11.12, A.U10.36 + GAP-G3 (TEST_UNIT, TEST_HELP); `tests/test_digital_twin_sensortask_integration.py:211`,
  `digital_twin/README.md:227-229` → A.U10.36 (TWIN); SPEC A.7 registry paragraph, C.6 one shape, C.13 → A.U11.12,
  A.U10.36, A.U10.21 (SPEC).
- **Kind**: code

### M.SRC_CORE.018 Remove the service's two caller-less public methods
- **From**: adherence (OR36.a (1)); no action carries it.
- **Site**: `src/system_service.py:263-264` `stop_uptime_timer()`, `:343-345` `set_debug_level()`.
- **Change**: both methods go. `stop_uptime_timer()` has no caller in `src/`, `buildgen/`, generated code or the twin
  (grep: only `tests/test_system_service.py`); `set_debug_level()` has no `src/`/`buildgen/` caller (A.U11.12's own Blast
  says so) — its only users are `tests/_sensortask_scenarios.py:723-745, 939`, which reach the same path through the
  `/system` settings PUT (`_set_dict_cfg()` via the webserver) the product uses.
- **Resolved**: OR36/OR36.a (1) (owner, 2026-09-26): "a … function that exists only so a test … can reach inside is a
  test artifact and is removed; the test is rebuilt outside the code … with the same goal and strength" — settles it; the
  property stays testable from outside (REST PUT or `_set_dict_cfg()`), so nothing goes to the owner (agent, 2026-10-01;
  "Agent decisions" 7).
- **Unit**: U11.
- **Depends**: —
- **Blast carried by**: `tests/test_system_service.py` users, `tests/_sensortask_scenarios.py:723-745, 939` → GAP-G3
  (TEST_UNIT, TEST_HELP); SPEC E.5.1/A.7 mentions (none found by grep) —.
- **Kind**: code

### M.SRC_CORE.019 Fan-in accessors: typed error sources; the reset reports its write
- **From**: A.U10.46 (`get_error_sources() -> list[ErrorSource]`), A.U11.31 (`reset_error_counter() -> bool`).
- **Site**: `src/system_service.py:275-285`, `:396-397`.
- **Change**: `get_error_sources(self) -> "list[ErrorSource]"` (comment `:276-278` kept); `async def
  reset_error_counter(self) -> bool: return await self.pr.reset()`. `get_loggers()`, `get_error_counter()` unchanged.
- **Resolved**: —
- **Unit**: U11 (A.U11.31 co-lands with the webserver's concurrent reset; A.U10.46's annotation lands U10).
- **Depends**: M.SRC_CORE.063 (`PrintLogHistory.reset() -> bool`), M.SRC_CORE.030.
- **Blast carried by**: webserver `_put_status()` gather and per-field result → A.U11.31 (SRC_NET); js mock/render →
  A.U23's G7/R27 mirror (WEB); tests → A.U11.31 (TEST_UNIT).
- **Kind**: code

### M.SRC_CORE.020 Member order, annotation quoting and the Timer stub re-check
- **From**: A.U10.33 (D.15 order), A.U10.31 (quote only `TYPE_CHECKING` names), SDEP.15 (W10: bare `Timer()` at
  `:83-85, :89`).
- **Site**: whole class `SystemService`, module functions.
- **Change**: after every stage above, members stand in D.15's order (dunders → private → public; starters → getters →
  setters → others) and module functions after the constants; A.U10.33's AST comparison (same (name, body) set, same
  comment multiset) runs at its U10 landing, and every later stage inserts new members at their D.15 place (A.U10.32's
  standing order check keeps it). The five bare `Timer()` constructions stay (valid runtime use); if SDEP.15's `mypy src`
  shows the stub gap fixed, CLAUDE.md's Timer bullet goes (DOCS), nothing changes here.
- **Resolved**: —
- **Unit**: U10 (A.U10.33 "lands last in U10"); U0 (SDEP.15's re-check in the dependency refresh).
- **Depends**: M.SRC_CORE.001.
- **Blast carried by**: lint/typecheck baselines → A.U10.33 (TOOL); CLAUDE.md Timer-gap bullet → SDEP.15 (DOCS).
- **Kind**: code

## src/base_classes.py (→ `src/asy_base_classes.py`)

End state: the session lock (`Lockable`, `DeviceSession`), `RegionBuffer`, the lock-free shared scalars
(`LockedCounter`/`LockedFlag`/`LockedValue`) under `COUNTER_CAP`, the 24-hour `HourlyWindowCounter`, the primitives
`TickSeconds`, `arm_tick_timer()`,
`utc_now()`/`set_utc_valid()`, `ValueRef`, the typing aliases, and
`SensorReader` (logger, sample, error streak with the recovery ladder, trigger divider, timer-fault path, the whole
config GET/PUT orchestration under one per-module lock) with `SensorReaderConfig` adding the file store.

### M.SRC_CORE.030 Header, top comment, imports and the shared typing aliases
- **From**: A.U10.17 (header scalars), A.U16.05 (header buffers), A.U10.46 and A.U11.S02 (alias block, `Any` gone),
  A.U10.31 (quoting), A.U10.10 (the `:5-7` comment's premise), A.U5.01/A.U5.02, A.U10.37; `SetupFct` (M.SRC_CORE.003
  Resolved); OR137.a (4) (the docstring names the window counter; A-C review fold).
- **Site**: `src/base_classes.py:1-28`.
- **Change**: docstring line 1 "Shared base classes and primitives: the session lock (Lockable, DeviceSession), region
  buffers (RegionBuffer), shared scalars (LockedCounter, LockedFlag, LockedValue, HourlyWindowCounter: no method awaits,
  so no lock), elapsed
  seconds (TickSeconds), the UTC timestamp, and the sensor-driver base (SensorReader,
  SensorReaderConfig) with error bookkeeping, the recovery ladder and optional JSON config storage."; line 2 unchanged.
  Comment `:5-7` → "# __init__ never calls self.pr.setup() (sync vs. async): setup() does it first (SensorReader), then
  the / # store's (SensorReaderConfig) - both inside the one-time boot batch, never lazily in a task (Part A.7)."
  Runtime imports: `asyncio`, `time`, `from collections import namedtuple`, `from micropython import const`,
  `from asy_config_manager import FAILED, UNCHANGED, VALID, ConfigManager, check_cfg_get_default, config_filename,
  instance_name, schema_dict, schema_names, type_or_range_error`, `from asy_print_log import DEFAULT_LOG, LogConfig,
  make_logger`. `TYPE_CHECKING` block: `from collections.abc import Awaitable, Callable, Mapping`; `from typing import
  Literal, NamedTuple, Protocol, TypeVar`; `Self`; `from asy_config_manager import CfgValue, ConfigSchema,
  WriteValidity`; `from asy_i2c_driver import I2C, I2CDevice`; `from asy_spi_driver import SPIDevice`; `from
  asy_print_log import ErrorLog, PrintLogHistory`; `MeasDataType` unchanged; aliases declared once here:
  `TaskStarter = Callable[[], asyncio.Task[None]]`, `TimerStarter = Callable[[], None]`, `JsonValue` (recursive),
  `JsonDict = dict[str, JsonValue]`, `JsonMapping = Mapping[str, JsonValue]`, `PushFct = Callable[[CfgValue],
  Awaitable[bool]]`, `NtpSyncFct = Callable[[], Awaitable[bool]]`, `AsyncCallback = Callable[[], Awaitable[None]]`,
  `SetupFct = Callable[[], Awaitable[bool]]`, `class ErrorSource(Protocol)` (`name`, `get_error_counter()`,
  `reset_error_counter() -> Awaitable[bool]`), `class LoggerOwner(Protocol)` (`get_loggers()`). The `AsyFramManager`
  import goes (no `fram` parameter remains). Annotations quoted only for `TYPE_CHECKING` names.
- **Resolved**: `ErrorSource.reset_error_counter()` returns `bool` (A.U11.31 changes every implementation; A.U10.46 wrote
  its Protocol before that) — the later contract is typed.
- **Unit**: U10 (aliases, header, quoting); U11 adds `PushFct`/`NtpSyncFct`/`AsyncCallback`/`JsonMapping` and
  `SetupFct` with their users (A.U11.S02 is SUPP_coverage over U11); U15/U16 edit the header words for `DeviceSession`/
  `RegionBuffer` with their classes; U19 adds `HourlyWindowCounter` with its class (M.SRC_CORE.133, A-C review fold).
- **Depends**: M.SRC_CORE.001, M.SRC_CORE.061 (`LogConfig`, `DEFAULT_LOG`).
- **Blast carried by**: users importing the aliases (`asy_system_service.py` M.SRC_CORE.003, `asy_api_response.py`
  M.SRC_CORE.071, the webserver, drivers, generated modules) → A.U10.46/A.U11.S02 per file (SRC_NET, SRC_SENS, GEN);
  `tests_scripts/test_mypy_any_baseline.py` and `pyproject.toml` baseline → A.U8.24/A.U10.46 (TSC, TOOL); SPEC C.10
  alias list → A.U10.46/A.U11.S02 (SPEC).
- **Kind**: code

### M.SRC_CORE.031 One shared counter cap; lock-free shared scalars
- **From**: A.U10.01, A.U10.17, A.U10.18 (`value_lock`), A.U10.35 (`max_val` → `_max_val`).
- **Site**: `src/base_classes.py:83-148` (`LockedCounter`, `LockedFlag`, `LockedValue`); new module constant.
- **Change**: `COUNTER_CAP = const(0x3FFFFFFF)` with "# 2**30 - 1: rp2's largest small int (object repr A), 34 years in
  seconds; no counter or cap may exceed it". `LockedCounter(*, init_value: int | None = 0, max_val: int = COUNTER_CAP)`:
  `self._max_val = min(max(max_val, 0), COUNTER_CAP)` (comment `:85-87` kept, naming `_max_val`); `_clamp()` unchanged;
  `increment()`: `current = 0 if self.value is None else self.value`; `if current < self._max_val: current += 1`;
  `decrement()`: `if current > 0: current -= 1`; `_step()` goes. `LockedValue(*, init_value: int | float | None)`,
  `set_value(value: int | float | None)`, `get_value() -> int | float | None`. The three classes lose `value_lock` and
  every `async with` (each method is a single read or assignment with no await); each class states "# No method
  awaits, so no lock is needed; kept async for a uniform call shape."
- **Resolved**: A.U10.18 renames `value_lock` → `_value_lock` "(or gone per A.U10.17)": A.U10.17 removes it — gone.
- **Unit**: U10 (the `boot_signature` → `LockedValue` move, M.SRC_CORE.008's U10 stage, lands in the same commit, K.03).
- **Depends**: M.SRC_CORE.030.
- **Blast carried by**: `asy_webserver_service.py:358` `_open_conns = LockedCounter(init_value=0)` → A.U10.01 (SRC_NET);
  `asy_notification_service.py:158` → A.U9.09 (SRC_SENS); `asy_wifi_service.py:167` → A.U10.03 (SRC_NET);
  `asy_uart_comm.py:659` `COUNTER_CAP` import → A.U10.04 (SRC_NET); `tests/test_base_classes.py:278-366` → A.U10.01,
  A.U10.17 (TEST_UNIT); driven-cap tests → A.U35.35 (TEST_UNIT); `tests_scripts/test_counter_steps.py` → A.U10.05 (TSC);
  SPEC G.2 `:4184-4186`, C.8 → A.U10.01, A.U10.17 (SPEC).
- **Kind**: code

### M.SRC_CORE.133 `HourlyWindowCounter`: events in the last 24 hours, from 24 fixed hourly bins
- **From**: OR137.a (1)-(5), OR140.a (10) and the owner's status-fields note (A-C review fold); register G6/R39.
- **Site**: `src/base_classes.py` (→ `src/asy_base_classes.py`) new class beside `LockedCounter`.
- **Change**: module constants `_WINDOW_HOURS = const(24)`, `_HOUR_S = const(3600)` (the window's definition, untagged).
  `class HourlyWindowCounter:` — comment (≤ 3 lines) "# Events in the last 24 hours at hourly resolution: 24 fixed bins
  advanced lazily from the uptime / # seconds (monotonic, untouched by NTP steps), so no event, read or hour change
  allocates; an event / # leaves the window 23-24 hours after it happened (owner, 2026-10-01)."; `__init__(self) ->
  None`: `self._bins = [0] * _WINDOW_HOURS` (the one allocation, at construction), `self._hour = 0` (the uptime hour
  the bins were last advanced to). `def _advance(self, now_s: int) -> None`: `hour = now_s // _HOUR_S`; `gap = hour -
  self._hour`; `if gap <= 0: return`; `if gap >= _WINDOW_HOURS:` every bin zeroed; else the bin of each hour
  `self._hour + 1 … hour` (index `h % _WINDOW_HOURS`) zeroed; `self._hour = hour`. `async def add(self, now_s: int) ->
  None`: `self._advance(now_s)`; `i = self._hour % _WINDOW_HOURS`; `if self._bins[i] < COUNTER_CAP: self._bins[i] += 1`.
  `async def total(self, now_s: int) -> int`: `self._advance(now_s)`; `s = 0`; per bin `if b >= COUNTER_CAP - s:
  return COUNTER_CAP`, `s += b` (checked before the step, so no intermediate leaves the small-int range); `return s`.
  `async def reset(self) -> None`: every bin zeroed (the hour kept). "# No method awaits, so no lock is needed; kept
  async for a uniform call shape." as the sibling scalars. `now_s` is the caller's `SysUptime` reading
  (`SystemService.get_uptime()`, measured `TickSeconds`), passed in, so the class holds no clock of its own.
- **Resolved**: OR137.a (4) asks for "one small reusable primitive (an hourly window counter beside the other shared
  counters)": a class in `asy_base_classes` next to `LockedCounter`, entered in SPEC Part G's catalog. The bins are a
  list of small ints, each capped at `COUNTER_CAP`, so a step stores an immediate value and never allocates; `[0] * 24`
  is far below Part F.1's `[x] * n` fault range; the hour index stays a small int over the whole `COUNTER_CAP` uptime
  range. The value is the window's sum, capped at `COUNTER_CAP`; `reset()` is what `ResetErrors` reaches (M.SRC_NET.129).
- **Unit**: U19 (lands with its first user, the webserver's drop counter: M.SRC_NET.119/.127/.129).
- **Depends**: M.SRC_CORE.031 (`COUNTER_CAP`); M.TEST_UNIT.343, M.TEST_UNIT.202 (fold F02) (driven-clock L1 cases in U19: the bin shift, a gap
  of a day or more, the cap, the reset, zero heap allocation per `add()`/`total()` at `gc.threshold(-1)`).
- **Blast carried by**: the user → M.SRC_NET.119, .127, .129; the docstring names it → M.SRC_CORE.030 (U19 stage); SPEC
  Part G catalog entry and A.5/A.8 `HTTPDropped` wording ("in the last 24 hours, hourly resolution") → M.SPEC.021, M.SPEC.111, M.SPEC.121, M.SPEC.126, M.SPEC.113 (fold F02);
  the long-lived-object catalog gains the webserver's one instance (24 bins, allocated at construction) → [fold F02
  M_SPEC].
- **Kind**: code

### M.SRC_CORE.032 Elapsed seconds, the tick-timer starter and the UTC timestamp
- **From**: A.U10.02, A.U10.03 (`arm_tick_timer()`), A.U10.06 (`utc_now()`, `set_utc_valid()`), A.U10.45 (tuple order).
- **Site**: `src/base_classes.py` new, after `LockedValue`.
- **Change**: `class TickSeconds` exactly as A.U10.02 states (`__init__(*, count_down=False)`, `restart(value_s=0)`,
  `read()` with `ticks_diff()` deltas, a millisecond remainder, check-before-step saturation at `COUNTER_CAP`, a
  non-positive delta ignored; header comment "a caller reads it at least once per 2**29 ms (6.2 days, ticks_diff()'s
  horizon); a negative delta (never on target within that horizon) is ignored" and "no method awaits, so no lock").
  `def arm_tick_timer(timer: Timer, flag: asyncio.ThreadSafeFlag, pr: PrintLogHistory, what: str) -> bool`:
  `timer.init(period=1000, mode=timer.PERIODIC, callback=lambda _b: flag.set())`; `except (MemoryError, OSError) as e:
  pr.err("Could not arm", what, "timer:", e); return False`; `return True`. Module `_utc_valid = False` ("# one writer
  (the NTP client's sync success), no await between read and use"); `def set_utc_valid() -> None` sets it (one-way);
  `def utc_now() -> int | None: return time.mktime(time.gmtime()) if _utc_valid else None` — no `try`.
- **Resolved**: A.U10.06 vs A.U14.26 (1) at the timestamp: ruled for A.U10.06 (V.U18.R10, U18 register fix 10): no
  catch; A.U10.06's stated reason becomes "OverflowError/OSError unreachable on target (G4/R15); the one reachable failure,
  a fixed small allocation, is not caught (CLAUDE.md memory rule, SPEC I.4(a))" — that sentence goes into SPEC G.2's
  entry, not into a code comment. `set_utc_valid()` takes no argument: A.U10.06's tests call `set_utc_valid(True)`, but a
  `valid` parameter that only a test passes as anything else would be a test seam (OR36.a (1)); tests reset the module
  attribute `_utc_valid` from outside (the repo's module-attribute mocking) (agent, 2026-10-01; "Agent decisions" 8).
- **Unit**: U10.
- **Depends**: M.SRC_CORE.031 (`COUNTER_CAP`).
- **Blast carried by**: users `asy_system_service.py` (M.SRC_CORE.013), `asy_wifi_service.py`/`asy_ntp_client.py`
  (A.U10.03, A.U10.06 — SRC_NET), `asy_notification_service.py` (A.U9.09, A.U10.06 — SRC_SENS), the four readers'
  timestamps and store guards (A.U10.06 — SRC_SENS), `asy_fram_manager.py:547/:611` (M.SRC_CORE.087); NTP calls
  `set_utc_valid()` first in `_handle_ntp_sync_success()` → A.U10.06 (SRC_NET); L1 `tests/test_base_classes.py`
  (`TickSeconds` cases, `arm_tick_timer()`, `utc_now()`) → A.U10.02, A.U10.03, A.U10.06 (TEST_UNIT); tests setting the
  flag → A.U10.06 with the no-argument form (TEST_UNIT, TEST_HELP, TWIN); SPEC G.2 "Elapsed seconds" and "Current UTC
  timestamp" entries, C.9 → A.U10.02, A.U10.03, A.U10.06 (SPEC); catalog row 16 loses SYSTEM e2/FRAM e86/e88 → A.U10.06
  (GEN).
- **Kind**: code

### M.SRC_CORE.033 The session lock and the one shared device-session class
- **From**: A.U10.18 (`asy_lock` → `session_lock`), A.U15.40 (1) (`DeviceSession`).
- **Site**: `src/base_classes.py:31-51` (`Lockable`); new `DeviceSession` after it.
- **Change**: `Lockable.__init__(self, session_lock: asyncio.Lock | None = None)` storing `self.session_lock`;
  `__aenter__`/`__aexit__` use it (the `except RuntimeError` tolerance and its comment kept). `class
  DeviceSession(Lockable)`: `__init__(self, bus_device: "I2CDevice | SPIDevice")` → `super().__init__()`,
  `self.i2c_device = bus_device`; comment "# One device's session lock plus its bus device (SPECIFICATION.md C.2/G.2)".
- **Resolved**: —
- **Unit**: U15 (U10 stage: the rename, which every `Lockable` user in U10-U14 then uses).
- **Depends**: —
- **Blast carried by**: `asy_fram_driver.py` users of `asy_lock` → M.SRC_CORE.102; `asy_i2c_driver.py`,
  `asy_spi_driver.py`, `asy_uart_driver.py` → A.U10.18 (SRC_SENS, SRC_NET); the four `<Chip>_DeviceSession` classes go →
  A.U15.40 (SRC_SENS); UART changelog Class B "`UART.asy_lock` renamed `session_lock`" → A.U10.18 (DOCS); tests renaming
  the attribute (`tests/test_base_classes.py` 7, `test_asy_spi_driver.py` 55, …) → A.U10.18 (TEST_UNIT); L0
  `test_driver_shape.py` → A.U15.40 (TSC); SPEC C.2/C.8/G.2 → A.U10.18, A.U15.40 (SPEC).
- **Kind**: code

### M.SRC_CORE.027 `LockableBuffer` becomes a lock-free `RegionBuffer`
- **From**: A.U16.05, A.U10.35 (`buf` → `_buf`).
- **Site**: `src/base_classes.py:54-80`.
- **Change**: `class RegionBuffer:` (no base class, no `super().__init__()`); `self._buf`; `get_buf()`/`get_data_buf()`
  read `self._buf`; comments `:60-68` kept. The decision comment of A.U16.05 lives in SPEC G.2, not here.
- **Resolved**: —
- **Unit**: U16 (U10 stage: `_buf`).
- **Depends**: —
- **Blast carried by**: `asy_fram_manager.py` buffer classes and import → M.SRC_CORE.089; `asy_uart_comm.py:14, 273,
  283-284, 878` → A.U16.05 (SRC_NET); `print_log.py` `_BufT` → M.SRC_CORE.064; tests (`test_base_classes.py` 18 mentions,
  `:259-270`, `test_print_log.py`, `test_asy_uart_comm.py`, comments in `test_asy_fram_manager.py`,
  `test_crc_checks.py:719`, `test_framing_codecs.py:165`) → A.U16.05 (TEST_UNIT); UART changelog Class B → A.U16.05
  (DOCS); SPEC `:3025, 3481, 4200-4216, 4797, 4871, 5640` → A.U16.05 (SPEC).
- **Kind**: code

### M.SRC_CORE.134 `PieceBuffer`: received bytes held in pieces of at most `piece_bytes`
- **From**: OR143.a (1), (4) (A-C review fold); register G6/R21.
- **Site**: `src/base_classes.py` (→ `src/asy_base_classes.py`) new class beside `RegionBuffer`.
- **Change**: `class PieceBuffer:` with the comment (≤ 3 lines) "# Bytes too many for one allocation, held as pieces of
  at most piece_bytes: no allocation is larger / # than one piece (owner, 2026-10-05). Read through its length, its
  pieces and copy-out, never joined." `__init__(self, size: int, piece_bytes: int) -> None`: `self._size = size`,
  `self._piece_bytes = piece_bytes`, `self._pieces = [bytearray(min(piece_bytes, size - start)) for start in range(0,
  size, piece_bytes)]` — every piece allocated at construction, after the caller's cap admitted `size`; a `MemoryError`
  is not caught here (the caps bound every allocation; CLAUDE.md memory rule). `def __len__(self) -> int`; `def
  pieces(self)` iterates the pieces in order; `def write_at(self, offset: int, src: memoryview) -> bool` copies `src`
  into the pieces from `offset`, crossing a piece end by index (slice assignment per piece, no intermediate copy),
  `False` for a range outside `0 … size`; `def copy_into(self, dest: bytearray | memoryview, start: int = 0) -> int`
  copies from `start` into `dest` and returns the count. No method awaits.
- **Resolved**: OR143.a (1) asks for "a small shared primitive with length, iteration and copy-out, checked first
  against SPEC Part G's catalog (the webserver's `_PieceWriter` is the model)": Part G's `_PieceWriter` groups outgoing
  JSON text into pieces of at most `chunk_bytes` for a stream write and holds no received bytes, so it is the model,
  not the home; the new class sits beside `RegionBuffer` (the shared buffer classes) and enters Part G's catalog. The
  method names and the iteration form (the pieces, or memoryviews of them) are decided at execution, with the reason
  recorded.
- **Unit**: U17 (lands with its user, the UART receive path, M.SRC_NET.220).
- **Depends**: M.SRC_CORE.027 (`RegionBuffer`'s section, U16); M.TEST_UNIT.344, M.TEST_UNIT.345, M.TEST_UNIT.164 (fold F27) (L1 in U17: every piece at most
  `piece_bytes`, a write crossing a piece end, copy-out at offsets, the largest block measured, refusals).
- **Blast carried by**: the user → M.SRC_NET.220; SPEC Part G catalog entry and Part I's heap budget → [fold F27
  M_SPEC].
- **Kind**: code

### M.SRC_CORE.034 Record a C-stack overflow for the supervisor, in the one module every handler can import
- **From**: A.U30.19 (1)(2) — home moved from `base_classes.py` to `print_log.py` (see Resolved).
- **Site**: `src/print_log.py` (→ `asy_print_log.py`) new module flag and two functions; the broad handlers of this
  cluster's files (`base_classes.py:200, :209, :311, :322, :352, :382, :396` at HEAD and the new ones of M.SRC_CORE.037/
  .038; `system_service.py`, `config_manager.py`, `api_response.py`, `asy_fram_manager.py`, `asy_fram_driver.py` — each
  file's M names its handlers).
- **Change**: in `asy_print_log.py`: `_STACK_EXHAUSTED = "maximum recursion depth exceeded"` (`py/runtime.c:1786`,
  v1.29.0 — re-checked against the refreshed pin, OR129.a (5)); `_fatal = False`; `def report_if_fatal(e:
  BaseException) -> None:` sets `_fatal` when `isinstance(e, RuntimeError) and e.args and e.args[0] ==
  _STACK_EXHAUSTED` (allocates nothing, prints nothing); `def fatal_reported() -> bool`. Comment (≤ 3 lines): "# A
  C-stack overflow is a design defect, never a routine failure: any handler that catches it records / # it here, and the
  supervisor reboots at its next pass (SPECIFICATION.md F.1)." Every broad `except` in `src/` gets `report_if_fatal(e)`
  as its first statement, imported `from asy_print_log import report_if_fatal`.
- **Resolved**: A.U30.19 places the flag in `base_classes.py`, but `asy_config_manager.py` (A.U10.20's new outer
  handler in `_flush_staged()`) must call it and `asy_base_classes` imports `asy_config_manager` at module level
  (`base_classes.py:11`), so the import would close a cycle, which A.U10.30's import-graph check fails on (owner, standing
  rule, `6aed3c9`) and which fails at runtime on MicroPython (a partially initialised module has no such name yet — the
  same cycle U11's register fix names for `print_log` → `config_manager`). `print_log` is the one project module every
  other `src/` module already imports and which imports only `crc_checks`; it hosts the flag with no new edge (agent,
  2026-10-01; "Agent decisions" 10). A.U30.19's text for every other cluster changes only in the import line (GAP-G8).
- **Unit**: U30.
- **Depends**: M.SRC_CORE.060 (the print_log header names it).
- **Blast carried by**: supervisor use → M.SRC_CORE.016 (U30 stage); every other broad handler in `src/` and generated
  code imports it from `asy_print_log` → A.U30.19 per cluster + GAP-G8 (SRC_NET, SRC_SENS, GEN); `_handle_unhandled_exception()`
  → A.U30.19 (SRC_NET); L0 `test_fatal_report_sites.py` (accepts the call imported from `asy_print_log`) → A.U30.19 +
  GAP-G8 (TSC); L1 flag cases move to `tests/test_print_log.py` → A.U30.19 + GAP-G8 (TEST_UNIT); UART changelog Class B →
  A.U30.19 (DOCS); SPEC F.1/C.7/G.2 name `print_log.py`'s primitive → A.U30.19 + GAP-G8 (SPEC).
- **Kind**: code

### M.SRC_CORE.035 One shared value-reference type
- **From**: A.U5.11 (`ValueRef`; `SgpBackup` is the SGP40 file's).
- **Site**: `src/base_classes.py` new module-level type.
- **Change**: `ValueRef = namedtuple("ValueRef", ("source", "field"))` with its typed shadow under `TYPE_CHECKING`
  (`source: <producer with get_data()>`, `field: str`) and "# a producer plus the field to read off its get_data()
  (SPECIFICATION.md C.14)".
- **Resolved**: —
- **Unit**: U5.
- **Depends**: M.SRC_CORE.001 [follows] (renamed file only if U5 < U10: it is not — the type lands in `base_classes.py` in U5 and
  moves with the file in U10).
- **Blast carried by**: SGP40/notification users and codegen `ValueRef(<src>, "<field>")` → A.U5.11 (SRC_SENS, GEN);
  tests → A.U5.11 (TEST_UNIT, TSC); SPEC C.14.2/C.14.3/L.6.3 → A.U5.11 (SPEC).
- **Kind**: code

### M.SRC_CORE.036 `SensorReader` constructor: fixed tail, one logger path, the module's fixed-size state
- **From**: A.U5.02, A.U35.45 (`logger=` goes), A.U10.19 (`:163-165` comment — dropped: its branch is removed),
  A.U10.18 (`_datalock` → `_data_lock`), A.U4.03 (callback dicts move here), A.U11.27 (`_set_lock`), A.U10.R01 (ladder
  state), A.U15.41 (`_timer_error`), A.U8.12 (`module.max_error` default tag), A.U11.S02 (types); routine settlement "initialized-flags" (no
  `initialized`; A-C review fold).
- **Site**: `src/base_classes.py:151-176`.
- **Change**: `def __init__(self, init_data: "NamedTuple", name: str, max_module_error: int = 5, name_ext: str = "", log:
  LogConfig = DEFAULT_LOG) -> None` (the default `5` tagged `module.max_error`); `resolved_name = instance_name(name,
  name_ext)`; `self.pr = make_logger(log, resolved_name)`; `self.name = resolved_name` (comment `:171-172` kept, now
  true on the one path); `self._datastruct = init_data`; `self._data_lock = asyncio.Lock()` ("# guards the last sample
  across a reader's read and a GET"); `self._max_module_error = max_module_error`; `self._err_cnt_internal = 0`;
  `self._set_lock = asyncio.Lock()` ("# serialises one module's config GET and PUT (Part C.5.2)"); `self._push_callbacks:
  dict[str, PushFct] = {}` and `self._get_callbacks: dict[str, Callable[[], Awaitable[CfgValue]]] = {}` with their
  `:283-287` comments; `self._rungs = 0`, `self._bus_mark = 0`, `self._recovery_bus: "I2C | None" = None`;
  `self._timer_error: Exception | None = None`. No `initialized`: no product code reads a reader's readiness (routine
  settlement "initialized-flags": the flag stays only in the FRAM, SPI, UART and logging classes). Every attribute is fixed-size (OR110.a). Gap pass G2: `max_module_error` has no reader outside
  the class (G10/R07, M_SRC_CORE GAP-G12) → `_max_module_error`; gap pass G2's flag (M_SRC_NET gap 3) is withdrawn
  by the same settlement (A-C review fold).
- **Resolved**: A.U5.02 keeps `logger=None` at the tail; A.U35.45 removes it (its Depends names A.U5.02/A.U5.18/A.U10.19
  for A-C) — removed; the tail probe's `logger` allow-list loses `SensorReader` (A.U5.18).
- **Unit**: U11 (stages: U5 signature and `make_logger(log, …)`; U4 the two dicts moved; U10 `_data_lock`, ladder state
  (A.U10.R01 is SUPP_recovery's U10 half); U15 `_timer_error`; U35's removal is pulled to U11, the unit owning the file —
  A.U35.45 is a B3 cleanup with no prerequisite, and removing it with the constructor rewrite avoids a third edit).
  A-C2 step order: A.U10.R01's part lands in U13, not U10 (it needs A.U13.R01, which lands in U13).
- **Depends**: M.SRC_CORE.030, .061.
- **Blast carried by**: subclass constructors (`super().__init__(…, max_module_error=…)` by keyword; NTP/NOTIFY pass 0)
  → A.U5.02 (SRC_SENS, SRC_NET); `tests/test_base_classes.py` 49 positional calls, `:450-470` `logger=` tests →
  A.U5.02, A.U35.45 (TEST_UNIT); `tests/test_api_response.py:190`, `tests/test_fram_integration.py` → A.U5.02
  (TEST_UNIT); A.U5.18's probe allow-list → A.U5.18 (TSC); Part N `module.max_error` sites → A.U8.12 (SPEC).
- **Kind**: code

### M.SRC_CORE.037 The error streak climbs one recovery ladder; the streak increase stays a persisted entry
- **From**: A.U2.06, A.U3.03 (dropped: OR140.a (7), A-C review fold), A.U10.R01 (1)-(6), A.U11.31 (`reset_error_counter() -> bool`), A.U30.19 (handler).
- **Site**: `src/base_classes.py:218-230` `_error_check()`, `:243-248` `reset_error_counter()`; new `_recover_device()`,
  `_climb_ladder()`, `_recover_bus()`, `_init_failed()`, `_init_done()`; module constants.
- **Change**: constants `_ERR_STREAK = const(1)`, `_ERR_GIVE_UP = const(2)` … `_ERR_RECOVERY_WRITE_RAISED = const(9)`, `_ERR_CALLBACK =
  const(14)`, `_ERR_TIMER = const(17)`, `_WRN_CALLBACK_KEYS = const(1)`, `_WRN_CFG_KEYS = const(2)`,
  `_WRN_DEVICE_RECOVERY = const(14)`, `_WRN_BUS_RECOVERY = const(15)`; `_RECOVER_DEVICE_AT = const(2)`,
  `_RECOVER_BUS_AT = const(3)`, `_RECOVER_CONTROLLER_AT = const(4)` with their `@tunable` tags and the one comment line
  of A.U10.R01 (1); `_RUNG_DEVICE/_RUNG_BUS/_RUNG_CONTROLLER = const(1/2/4)`. `_error_check()`: on a failure (`any(res is
  None …) and condition`): if the streak is 0 and `_recovery_bus` is set, `self._bus_mark =
  self._recovery_bus.recoveries`; `self._err_cnt_internal += 1`; `await self.pr.err_s("Error counter increased to", n,
  errno=_ERR_STREAK)` (persisted, as at HEAD: every layer that meets a fault keeps its own entry, owner, 2026-10-02); `if n > self._max_module_error: await self.pr.err_s("Maximum error count reached!",
  errno=_ERR_GIVE_UP); return False`; else `await self._climb_ladder()`; on a non-failure pass the HEAD decrement, then
  `if self._err_cnt_internal == 0: self._rungs = 0`. The ladder methods, their logging (one warning per rung that ran,
  none for a failed participant rung beyond the hook's own error, a raising hook → one `_ERR_CALLBACK` entry after
  `report_if_fatal(e)`), the per-bus episode check and `_init_failed()`/`_init_done()` exactly as A.U10.R01 (3)-(5).
  `reset_error_counter() -> bool`: `self._err_cnt_internal = 0`; `self._rungs = 0`; `return await self.pr.reset()`.
- **Resolved**: A.U3.03 is dropped (OR140.a (7), owner, A-C review fold: "every layer that meets a fault keeps its own
  persisted entry, as today"): the streak increase stays the base class's persisted errno 1 beside the driver's own
  read-failure entry, and A.U2.06's "no `_ERR_STREAK`, errno 1 retired" falls with it (the catalog keeps row 1,
  M.GEN.034). The entry, then the ladder climb, in the same branch; the give-up test stays first (A.U10.R01 (4)). The failure test itself stays HEAD's (`any(res is None …) and condition`):
  after A.U10.06 a reader's `TS` is `None` before the first NTP sync, and each reader passes `condition=results[0] is
  None` instead (lead ruling, 2026-10-01, M_SRC_SENS GAP-15; M.SRC_SENS.083, .089-.091); the SPEC C.7 bullet stating it
  is SPEC's.
- **Unit**: U10 (A.U10.R01's U10 half; stages U2 names with `_ERR_STREAK`; U11 `-> bool`; U30 `report_if_fatal`).
  A-C2 step order: A.U10.R01's part lands in U13, not U10 (it needs A.U13.R01, which lands in U13).
- **Depends**: M.SRC_CORE.036; A.U13.R01 (`I2C.clear()`, `recover()`, `recoveries`, `take_boot_clear_status()`,
  SRC_SENS) lands before or with it.
- **Blast carried by**: drivers' `_recover_device()` overrides and `_init_failed()`/`_init_done()` calls →
  A.U15.R01-R04, A.U18.R01 (SRC_SENS, SRC_NET); catalog wrnno 14/15 → A.U2.01 merge (GEN); driver/integration tests
  re-derived → A.U10.R01 blast (TEST_UNIT); new L1 ladder cases → A.U10.R01 (TEST_UNIT); `tests/test_base_classes.py:474-739`
  streak pins keep the persisted errno 1 (A.U3.03 dropped) → M.TEST_UNIT.227; Part N rows and relation → A.U10.R01/A.U8.02 (SPEC); SPEC C.4/C.7/G.2/F.2 →
  A.U10.R01, A.U3.03 (SPEC); `tests_scripts/test_counter_steps.py` must not flag `_err_cnt_internal` (bounded by the
  give-up, pass-4 K.36) → GAP-G6 (TSC).
- **Kind**: code

### M.SRC_CORE.038 Config GET and PUT orchestration on `SensorReader`, one per-module lock
- **From**: A.U4.03, A.U11.27, A.U11.28 (`_commit_mgr_cfg()` in a `finally`), A.U19.12, A.U30.08, A.U2.06, A.U19.16,
  A.U11.S02, A.U30.19; OR140.a (12) (closed-store refusal; A-C review fold).
- **Site**: `src/base_classes.py:182-212` (`_get_mgr_cfg()`, `_get_dict_cfg()`), `:251-256`, `:290-397` (moved from
  `SensorReaderConfig`).
- **Change**: on `SensorReader`: `_get_mgr_cfg()` default `{}`; new default `_set_mgr_cfg(data: "JsonMapping", cfg_vals: "ConfigSchema") -> "tuple[bool,
  WriteValidity]"` returning `(False, {})`; new default `_commit_mgr_cfg(self) -> None` (no-op). `_get_dict_cfg(name,
  cfg_vals, callback: "Callable[[], Awaitable[dict[str, CfgValue]]] | None" = None)`: its whole body under `async with
  self._set_lock:`; wrnno/errno by name (`_WRN_CFG_KEYS`, `_ERR_CFG_GET_RAISED`, `_WRN_CALLBACK_KEYS`,
  `_ERR_CFG_CALLBACK_RAISED`). `_set_dict_cfg(data: "JsonMapping", cfg_vals: "ConfigSchema") -> "WriteValidity"` (gap pass G2: U19 A-C note 2 — the
  route passes the raw body; every override of `_set_mgr_cfg()` takes the same `JsonMapping`, M.SRC_CORE.040,
  M.SRC_NET.045/.096, M.SRC_SENS.053): whole body under `async with
  self._set_lock:`; first `if self._writes_closed(): return dict.fromkeys(data, FAILED)` with the comment "# Closed by
  an accepted system command: nothing writes, flash or chip, until the reset (owner, 2026-10-02)." — new default
  `def _writes_closed(self) -> bool: return False` on `SensorReader`, `SensorReaderConfig` reads its store
  (M.SRC_CORE.040), so no persist, push or chip write starts once the stores are closed (SCD30's chip keys included,
  M.SRC_SENS.053); `fields = schema_dict(cfg_vals)` once; the snapshot keys are those persisted (`check_cfg_get_default
  (field)[0]`) **and** having a push callback; persist through `_set_mgr_cfg()` with `_checked_write_results()`
  (module-level, unchanged); every requested key missing from `results` → `FAILED`; a not-persisted write → every key
  `FAILED`; push loop over `VALID` keys (`fields.get(key)`), a failed push → `FAILED` and `await
  self._recover_failed_push(key, old_values, cfg_vals, fields=fields)`; the pushes and recoveries sit in a `try` whose
  `finally:` calls `self._commit_mgr_cfg()`. `_recover_failed_push(…, *, fields)`: `fields.get(key)`; the getter rung
  (`_ERR_RECOVERY_READ_RAISED`); `persisted, res = await self._set_mgr_cfg({key: recovered}, cfg_vals)`, `res =
  _checked_write_results(res)`; when `not persisted` or `res.get(key) not in (VALID, UNCHANGED)`: `self.pr.err("Recovery
  of", key, "after a failed push was not stored:", res.get(key))` (console: the refusing store persisted its own entry);
  a raise → `_ERR_RECOVERY_WRITE_RAISED`. Every broad handler starts with `report_if_fatal(e)`.
- **Resolved**: A.U11.27 and A.U19.12 take the same `self._set_lock` for PUT and GET (no re-entry: nothing under the lock
  calls `_get_dict_cfg()`/`_set_dict_cfg()`); A.U11.28's `finally` and A.U11.27's lock nest as lock → try/finally.
- **Unit**: U19 (A.U19.12 is the latest constituent; stages: U2 names; U4 the move and the narrower snapshot; U11 lock,
  recovery check, deferred commit; U19 GET under the lock and result constants; U30 `fields` once and
  `report_if_fatal`; fold stage U20: the closed-store refusal, with M.SRC_CORE.011's close at acceptance and its tests
  M.TEST_UNIT.306 (fold F15)). A.U30.08 is pulled forward into U11's rewrite of the same lines (no prerequisite; one edit).
- **Depends**: M.SRC_CORE.036, M.SRC_CORE.044 (`write_config(data, defer=…)`, `commit()`), M.SRC_CORE.045 (constants).
- **Blast carried by**: SCD30 chip store overrides (`_set_mgr_cfg`/`_get_mgr_cfg`, `_commit_mgr_cfg()` no-op) → A.U4.04,
  A.U15.12 (SRC_SENS); `api_response.handle_set_cmd()` → M.SRC_CORE.072; webserver `_put_sensors()`/`_get_sensors()` →
  A.U11.27/A.U19.12 (SRC_NET); tests `tests/test_base_classes.py:1128-1617` → A.U4.03, A.U11.27, A.U11.28 (TEST_UNIT);
  `tests/test_asy_webserver_service.py:1108-1137` consistency test → A.U19.12 (TEST_UNIT); L2 twin consistency scenario
  → A.U19.12 (TWIN); SPEC C.4.3/C.5.2/C.5.2.2/A.8 `:627-631` → A.U4.03, A.U11.27, A.U11.28, A.U19.12 (SPEC).
- **Kind**: code

### M.SRC_CORE.039 Reader lifecycle helpers: setup, trigger starters, divider, timer fault, republish
- **From**: A.U10.10, A.U10.21, A.U10.12 (`get_trigger_starters()`), A.U15.40 (2) (the shared divider), A.U10.44
  (its name `_trigger_loop()`, M_SRC_SENS GAP-8), A.U10.22 (dropped: routine settlement "initialized-flags", A-C review fold), A.U15.41
  (`_timer_failed()`, `_timer_fault()`), A.U15.12 (`_republish()`).
- **Site**: `src/base_classes.py` `SensorReader` new methods.
- **Change**: `async def setup(self) -> bool: await self.pr.setup(); return True` ("True = ready; a
  logger that could not reach its store has logged it and runs in RAM"). `def get_trigger_starters(self) -> "list[TimerStarter]": return []`.
  `async def _trigger_loop(self) -> None` — the byte-identical body of the two `_base_trigger()` copies (count
  `_base_trigger_event` ticks in `_trigger_counter`, set `_read_event` every `await self._trigger_period.get_value()`; the
  private names the dividing subclasses set, M.SRC_SENS.042/.073), extended by A.U15.41: it
  begins with the re-arm `if self._timer_error is not None: self._timer_error = None; self.start_timer()` and checks `if
  await self._timer_fault(): return` after every wake. `def _timer_failed(self, e: Exception, waiter:
  asyncio.ThreadSafeFlag) -> None`: `self._timer_error = e`; `self.pr.err("Could not start timer:", e)`; `waiter.set()`.
  `async def _timer_fault(self) -> bool`: `if self._timer_error is None: return False`; `await self.pr.err_s("Read
  trigger timer not armed:", self._timer_error, errno=_ERR_TIMER)`; `return True`. `async def _republish(self, names:
  "tuple[str, ...]", **changes: object) -> None`: `async with self._data_lock: old = self._datastruct; self._datastruct
  = type(old)(*(changes[n] if n in changes else getattr(old, n) for n in names))` — no await inside the hold.
- **Resolved**: A.U15.12 names the helper `_republish(**fields)`; building a namedtuple of the old type from keywords
  needs its field names, and rp2's EXTRA_FEATURES build has no `_fields`/`_replace` (`config_manager.py:103-105`, fact
  confirmed there against `ports/rp2/mpconfigport.h`) — the caller passes its own field tuple (SCD30's `_FIELDS`).
  `SensorReader.setup()` returns `True` (A.U10.21 names returns for the other classes; a plain reader has no store).
  Gap pass G2: A.U15.40 names the divider `_divide_trigger()`, A.U10.44 (U10, earlier) names every task coroutine
  `_<what>_loop` and maps `_base_trigger` → `_trigger_loop` — A.U10.44's name (M.SRC_SENS.045, M_SRC_SENS GAP-8); the
  drivers' `start_asy_trigger()` creates it (M.SRC_SENS.045/.083). No `initialized` (routine settlement "initialized-flags",
  A-C review fold; M.SRC_CORE.036).
- **Unit**: U15 (latest: A.U15.12/.40/.41; stages U10: `setup()` and `get_trigger_starters()` — A.U10.10's boot batch
  and A.U10.12's trigger plan need them in U10).
- **Depends**: M.SRC_CORE.036, M.SRC_CORE.037 (`_ERR_TIMER`).
- **Blast carried by**: BMP3XX/ISL29125 drop their `_base_trigger()` copies and run `_trigger_loop()`; drivers'
  `start_timer()` arm failures call `_timer_failed()`; SCD30/SGP40 check `_timer_fault()`; SCD30 calls `_republish(
  _FIELDS, …)` → A.U15.40, A.U15.41, A.U15.12 (SRC_SENS); codegen `needs_setup` for a `SensorReader` subclass →
  A.U10.10 (GEN); L1 `_trigger_loop()` cases, timer-fault tests → A.U15.40, A.U15.41 (TEST_UNIT; M.TEST_UNIT already follows GAP-8); logger
  `initialized` after the batch → A.U10.10 (TEST_HELP); tests and the L0 check reading a reader's `initialized` →
  M.TEST_UNIT.078, M.TEST_UNIT.079, M.TEST_UNIT.293 (fold F28), M.TSC.112 (fold F28) (A.U10.22's scope narrowed); SPEC C.9/C.13/G.2 → A.U10.14, A.U10.21, A.U15.40 (SPEC).
- **Kind**: code

### M.SRC_CORE.040 `SensorReaderConfig`: the file store over the base orchestration
- **From**: A.U5.02, A.U11.32, A.U10.39 (`_cfg_schema`), A.U11.24 + A.U11.28 (`write_config(data, defer=True)`,
  `_commit_mgr_cfg()`), A.U10.10/A.U10.21 (`setup()`), A.U11.S02 (types); AC_NOTES 13 (the `CFGMGR_SCD30` logger stays
  RAM-only) — no action writes its mechanism (see Resolved); OR140.a (12) (`_writes_closed()`), routine settlement
  "initialized-flags" (A-C review fold).
- **Site**: `src/base_classes.py:259-414`.
- **Change**: `__init__(self, init_data, name, default_vals, max_module_error: int = 5, name_ext: str = "", cfg_path:
  str = "", log: LogConfig = DEFAULT_LOG)` → `super().__init__(init_data, name, max_module_error=max_module_error,
  name_ext=name_ext, log=log)`; `self._cfg_schema = default_vals`; comment `:274-276` kept; `self.cfgmgr =
  ConfigManager(config_filename(cfg_path, self.name), default_vals, self.name, log=log if self._CFG_LOG_FRAM else
  LogConfig(None, log.history_length, log.debug))`; class attribute `_CFG_LOG_FRAM = True` with "# False where the
  owner keeps a module's config store off FRAM (SCD30, owner, 2026-09-29: 'no extra FRAM chunk')". `_get_mgr_cfg()`
  unchanged; `_set_mgr_cfg(data: "JsonMapping", cfg_vals: "ConfigSchema")` → `return await
  self.cfgmgr.write_config(data, defer=True)`;
  `_commit_mgr_cfg()` → `self.cfgmgr.commit()`; `get_error_sources() -> "list[ErrorSource]"`; `get_loggers()`;
  `get_cfg_schema()` → `self._cfg_schema` (its "stays a public attribute" comment goes); `async def setup(self) -> bool:
  await super().setup(); await self.cfgmgr.setup(); return self.cfgmgr.valid`; `def _writes_closed(self) -> bool: return
  self.cfgmgr.writes_closed()` (the store closed by an accepted system command refuses the module's PUTs,
  M.SRC_CORE.038).
- **Resolved**: AC_NOTES 13 / the U15 lead note (OR99 "No flash writes, no extra FRAM chunk") keep `CFGMGR_SCD30`
  RAM-only while SCD30's own logger stays FRAM-wired; A.U15.12 makes `SCD30_Reader` a `SensorReaderConfig`, whose
  constructor passes one `log` to both loggers. A class attribute read at construction is the least change that keeps
  the tail rule (no ninth, non-tail parameter) and needs no generated wiring (agent, 2026-10-01; "Agent decisions" 9);
  `SCD30_Reader` sets `_CFG_LOG_FRAM = False` (GAP-G7, SRC_SENS merges A.U15.12).
- **Unit**: U15 (fold stage U20: `_writes_closed()` with M.SRC_CORE.038/.041; A.U15.12 needs the attribute; stages U5 signature/`log`, U10 `_cfg_schema`/`setup() -> bool`, U11
  `config_filename()`/`write_config(data, defer=True)`/`_commit_mgr_cfg()`).
- **Depends**: M.SRC_CORE.036, .038, .044, .046.
- **Blast carried by**: every subclass (BMP3XX, ISL29125, SGP40, NOTIFY, NTP, WIFI, SCD30) → A.U5.02 (SRC_SENS, SRC_NET);
  `AsyConnTime._set_mgr_cfg()` through `super()` → no edit (it inherits the deferral; M.SRC_NET.096 types its `data`, gap pass G2); tests reading `cfg_schema` → A.U10.39
  (TEST_UNIT, HW_DEV `isl29125_mechanism_envelope.py:109`); chunk layout per device without `CFGMGR_SCD30` → A.U16.02,
  A.U15.12 (TEST_HELP, SRC_SENS); SPEC A.7 FRAM list and CLAUDE.md FRAM bullet name the exception → GAP-G7 (SPEC,
  DOCS); SPEC C.2/C.5.1 → A.U10.39 (SPEC).
- **Kind**: code

### M.SRC_CORE.029 Member order and annotation form in `base_classes.py`
- **From**: A.U10.33, A.U10.31, A.U10.45 (the file's one tuple `(MemoryError, OverflowError)` is already ordered).
- **Site**: every class of the file.
- **Change**: D.15 order in each class after every stage (A.U10.33's AST equality at its U10 landing; later stages insert
  at their D.15 place); annotations quoted only for `TYPE_CHECKING` names.
- **Resolved**: —
- **Unit**: U10.
- **Depends**: M.SRC_CORE.001.
- **Blast carried by**: lint/typecheck baselines → A.U10.33 (TOOL).
- **Kind**: code

## src/config_manager.py (→ `src/asy_config_manager.py`)

End state: the schema helpers (unguarded, typed inputs only; malformed schemas rejected statically), the shared
`compare_before_write()` primitive, `config_filename()`, the four result-word constants, and `ConfigManager`: a store
that writes the schema defaults once for a genuinely missing file, never overwrites an unreadable one (`writable`),
records a file that existed but was unreadable or damaged (`faulted`, for `/status` `ConfigFaults`), validates
against its own schema, compares in stored form, stages only once its flush task exists, can defer the flush until the
caller's pushes finish (`commit()`), serialises before opening, closes race-free for a reset and deletes its own file
for the config reset.

### M.SRC_CORE.049 Header, comments, imports, constants and the constructor
- **From**: A.U0.42 (`:7`), A.U36.514 (`:46-48`), A.U36.004 (1) (`:217`), A.U5.02 (constructor), A.U2.04/A.U2.07
  (constants), A.U10.17 (lock reason), A.U10.18 (`config_lock` → `_config_lock`), A.U10.35 (`config_file` →
  `_config_file`), A.U11.04 (`_closed`), A.U11.20 (`writable`), A.U11.28 (`_commit_ready`), A.U11.31
  (`reset_error_counter() -> bool`), A.U11.S01 (`T` gains `bool`, `Any` goes), A.U19.16 (`Final`), A.U10.31, A.U10.37;
  OR138.a (1) (`faulted`, `module_name`; A-C review fold).
- **Site**: `src/config_manager.py:1-50`, `:215-232`, `:261-265`.
- **Change**: docstring line 1 names `asy_base_classes.py`; line 2 "Every public function/method returns a documented
  "invalid" sentinel, never raises (for typed inputs; a malformed schema fails the static schema check)." `:7` →
  "# directly - SPECIFICATION.md A.4 has the cache-vs-external-corruption trade-off this implies." `:46-48`'s cite →
  "(SPECIFICATION.md Part L.6.4)". Imports: `asyncio`, `errno`, `json`, `os`, `from micropython import const`, `from
  asy_print_log import DEFAULT_LOG, make_logger, report_if_fatal`; `TYPE_CHECKING`: `Callable`, `Final`, `Literal`,
  `NamedTuple`, `TypeVar`; `from asy_base_classes import JsonMapping` (gap pass G2: `write_config()`'s raw-body parameter,
  M.SRC_CORE.044 — a `TYPE_CHECKING` import, no runtime edge); `from asy_print_log import ErrorLog, LogConfig, PrintLogHistory`; `T = TypeVar("T", int, float,
  str, bool)`; no `Any`, no `AsyFramManager`. Constants: `_ERR_ALLOC = const(20)`, `_ERR_BAD_ARG = const(21)`,
  `_ERR_UNEXPECTED = const(23)`, `_ERR_CONTRACT = const(24)`, `_ERR_CFG_PATH_IS_DIR = const(30)`, `_ERR_CFG_NO_DEFAULTS =
  const(31)`, `_ERR_CFG_BAD_DEFAULT = const(32)`, `_ERR_CFG_FILE_WRITE = const(33)`, `_ERR_CFG_NOT_VALID = const(34)`,
  `_WRN_STORED_DEFAULT = const(10)`, `_WRN_CFG_FILE_NOT_OBJECT = const(20)`, `_WRN_CFG_FILE_JSON = const(21)`,
  `_WRN_CFG_FILE_UNREADABLE = const(22)`, `_WRN_CFG_KEYS_REMOVED = const(23)` (24 retired, A.U11.19). `__init__(self,
  filename: str, cfg_vals: "ConfigSchema", name: str, log: "LogConfig" = DEFAULT_LOG)`: `self.name = "CFGMGR_" + name`;
  `self.pr = make_logger(log, self.name)` with the comment "# Inherits its owning module's logging config - FRAM-backed
  when the module is (the implicit FRAM-wiring / # rule, SPECIFICATION.md A.7) - so its failure history survives a
  reboot like the module's own."; `self._config_lock = asyncio.Lock()` ("# serialises the config file and its staged
  snapshot"); `self._config_file`, `self._cfg_vals` (gap pass G2: no reader outside the class, G10/R07), `self.valid = False`, `self.writable = True`, `self.faulted = False` (set by `setup()`, M.SRC_CORE.043; read once
  by the system service at the end of the boot setup batch, M.SRC_CORE.015), `self.module_name = name` (the module
  name `/status` `ConfigFaults` lists; public for the same reader), `self._closed = False`,
  `self._cache`, `self._staged` (comment `:228-230` kept), `self._pending_flush`, `self._commit_ready = asyncio.Event()`
  (set: "# cleared while a deferred snapshot waits for its commit()"; `_commit_ready.set()` in `__init__`).
  `reset_error_counter() -> bool: return await self.pr.reset()`.
- **Resolved**: A.U36.004 (1)'s condition "follows A.U5.02's wording and keeps this citation" — applied.
- **Unit**: U11 (`faulted` and `module_name` with M.SRC_CORE.043's fault state, A-C review fold; stages: U0 tag lines of M.SRC_CORE.047; U2 constants at HEAD sites; U5 `log`; U10 names/lock reason;
  U36's two cite edits pulled into U11 — comment-only, the file's own unit).
- **Depends**: M.SRC_CORE.001, M.SRC_CORE.034, M.SRC_CORE.061.
- **Blast carried by**: `ConfigManager(…, fram=…)` callers → M.SRC_CORE.008/.040 and A.U5.02 (SRC_NET: webserver/Wi-Fi if
  any); tests reading `config_file`/`config_lock` → A.U10.35/A.U10.18 (TEST_UNIT); `tests/test_config_manager.py` numbers
  (9 lines, `:2356`), `test_asy_bmp3xx_driver.py:2072`, `test_setter_microdot_integration.py:683`,
  `tests_hardware/bench/test_network_resilience.py:929-935` → A.U2.07 (TEST_UNIT, HW_BENCH); mockdata `CFGMGR_*` rows →
  A.U2.25 (GEN/WEB); SPEC C.7.3/C.7.4/L.2/C.5.2 numbers → A.U2.07 (SPEC); catalog rows 22 text, 24 retired, 32 one site →
  A.U2.01 merge per U11 register fix "For A-C" and AC_NOTES 7 (GEN).
- **Kind**: code

### M.SRC_CORE.047 Schema helpers: typed inputs only; the shared compare-before-write primitive
- **From**: A.U11.17, A.U11.S01 (1)(2), A.U11.30, A.U0.39 (`:131` tag), A.U4.01, A.U11.21 (`_stored_float()`), A.U10.45.
- **Site**: `src/config_manager.py:53-208` (`_special_bypass()`, `instance_name()`, `schema_names()`, `name_cfg()`,
  `schema_dict()`, `make_dict()`, `coerce_numeric()`, `type_or_range_error()`, `check_cfg_get_default()`); new
  `checked_int()`, `checked_float()`, `checked_numeric()`, `compare_before_write()`, `_stored_float()`.
- **Change**: the five `try/except Exception` (`:80-83`, `:94-97`, `:111-114`, `:115-118`, `:150/:185-186`) and
  `check_cfg_get_default()`'s `:193/:205-206` go (bodies unchanged otherwise; the `:79`/`:93` trailing comments lose
  "malformed input -> []"/"{}"). The numeric validation is typed per kind, so no caller narrows a value at runtime:
  `coerce_numeric()` splits into `_coerce_int(check_val: object) -> int | None` (the `:128` exact-type case and the
  `:134-141` integral-float case; `None` refuses) and `_coerce_float(check_val: object) -> float | None` (the exact
  float and the `:130-133` int case) — same acceptance rules, the `:121-123` comment above `_coerce_int()` with "bool is
  excluded both ways by exact type (on MicroPython `bool` is not an `int` subclass)", `:131`'s "an accepted gap (owner,
  2026-08-24)" in `_coerce_float()`, the tuple `(OverflowError, ValueError)` kept. New `checked_int(check_val:
  object, field: "FieldSchema", *, check_special: bool = True) -> int | None` and `checked_float(...) -> float |
  None`: HEAD's int/float branch bodies (`:153-172`) over `value = _coerce_int(check_val)` / `_coerce_float(check_val)`,
  `None` on refusal, a malformed special or out-of-range, the accepted value otherwise; `checked_numeric(check_val,
  field, *, check_special=True) -> int | float | None` dispatches on `field[1]` (`"int"`/`"float"`, any other kind →
  `None`). Two comment lines above `checked_int()`: "# Per-kind validators: a caller that needs an int or a float gets
  one from the type, never by narrowing" / "# (SPECIFICATION.md C.10); the webserver's dispatch-only fields
  (asy_webserver_service.py) are checked here too." HEAD's `:126-127` comment ("Public and reused: the generated
  lightCmdLED dispatch …") goes with the public `coerce_numeric()` it described. `_special_bypass(check_val: object, …)`.
  `type_or_range_error(check_val: object, field, *, check_special=True) -> "tuple[bool,
  CfgValue]"` keeps its contract for the schema-generic callers (`base_classes.py`, this file, `asy_scd30_driver.py`):
  int/float kinds through `checked_numeric()` (`value is None` → `(True, None)`, else `(False, value)`), the str and
  bool branches as HEAD (`type(check_val) is not str` narrows for `len()`, a real check) except that every refusal
  answers `(True, None)`. `compare_before_write(data: object, cfg_vals, current, *, always=(),
  resolution=None) -> "tuple[dict[str, CfgValue], WriteValidity] | None"` exactly as A.U4.01 (per-key outcomes in `data`
  order; `None` for a non-dict `data`; logs nothing; never raises but `MemoryError`); `resolution` typed
  `dict[str, Callable[[CfgValue], CfgValue]] | None` (no `Any`). `data` and every validator's `check_val` are `object`:
  a REST value is genuinely open (G8/R61), so `type(data) is not dict` → `None` and each exact-type test are real checks. `_stored_float(v: float) -> float: return
  json.loads(json.dumps(v))` with the residual comment of A.U11.21 (idempotence on rp2 proven by the L3 script; fallback to
  the serialised text decided with evidence).
- **Resolved**: A.U4.01 types `resolution` with `Callable[[Any], CfgValue]`; A.U11.S01/G8/R61 (owner, OR81: no
  hand-written `Any`) → `Callable[[CfgValue], CfgValue]`. A.U11.S01 (1)(2)(5) add `type(...) is not int/float` tests
  that never fire, here and in three consumers; the lead's L1 answer (SUPP_coverage open points, 2026-09-30: "a
  narrowing check that can never fire is runtime code and dead code … the fix is at the type level"), restated as
  M_SRC_SENS GAP-14 (lead, 2026-10-01), rules them out: the validator gets honest per-kind returns instead and every
  never-firing check is dropped (A.U15.38 (1) stands). `coerce_numeric()` has no product reader outside this module
  once the consumers call the per-kind validators, so its two halves are private (G10/R07); the per-kind validators are
  public, called by the webserver and the ISL29125, SGP40 and BMP3XX drivers (GAP-G13 as corrected below; agent,
  2026-10-01; "Agent decisions" 13). Gap pass G2 (2026-10-01): (i) M_GEN gap 4 / U19 A-C note 5 — after A.U19.02 the
  `LightCmdLED` validation lives in the webserver against `_LIGHT_CMD_FIELDS` (M.SRC_NET.122; M.GEN.008's generated
  callback only delegates to `led_signal()`), so the generated module calls no validator and the `:126-127` comment's
  subject is gone; the lead's L1/GAP-14 ruling reaches every typed consumer, so SGP40's compensation read
  (`checked_float()`, M.SRC_SENS.064) and BMP3XX `set_trigger_s()` (`checked_int()`, M.SRC_SENS.045) take the
  per-kind validators too, beside the three GAP-G13 named. (ii) U19 A-C note 2 (M_SRC_NET gap 4): the routes pass the
  raw body (`JsonMapping`, M.SRC_CORE.017/.038/.040/.044), so a validator receives an `object`; G8/R61 ("genuinely open
  values `object`", owner OR81) types it so. `type_or_range_error()`'s refusal answers `(True, None)`, which keeps its
  return honestly `tuple[bool, CfgValue]`: no caller reads that slot on refusal (the `asy_base_classes` push and
  recovery, this file's setup repair and `compare_before_write()`, SCD30's `ContMeas`), and no test pins it (grep
  `type_or_range_error(` in `tests/`: every refusal assertion reads `[0]`) (agent, 2026-10-01; OR2.c list).
- **Unit**: U11 (A.U4.01 in U4 as its stage — A.U4.02 in U4 needs it; the guard removal and typing in U11; U0's tag at
  `:131` as a U0 stage).
- **Depends**: A.U11.18 (static schema check lands first or together, TSC).
- **Blast carried by**: schema-generic callers of `type_or_range_error()` unchanged; the webserver's
  `_dispatch_notification_led()` (R/G/B `checked_int()`, T `checked_float()`) and `_dispatch_notification_pause()`
  (`checked_int()`), `None` refusing, no `type()` tests → M.SRC_NET.122 (the generated callback validates nothing,
  M.GEN.008); SGP40 compensation → M.SRC_SENS.064; BMP3XX `set_trigger_s()` → M.SRC_SENS.045; L1 cases (a refusal's
  `(True, None)`; a list or dict value refused by every validator and by `compare_before_write()` per key) → hand-off
  TEST_UNIT (`GAPS_G2.md`); ISL29125
  `_checked_cfg()` calls `checked_numeric()` (`checked = checked_numeric(value, schema[0])`; `None` logs and returns) →
  GAP-G13 (SRC_SENS, A.U15.38 (1) arm removal stands); `tests/test_config_manager.py:265-327` (`coerce_numeric()` tuples
  → `_coerce_int`/`_coerce_float` returns) and `tests_hardware/device_scripts/float_boundary_2pow24.py:10-26` →
  GAP-G13 (TEST_UNIT, HW_DEV); SPEC C.10 sentence → GAP-G13 (SPEC); SCD30 chip store uses the primitive →
  A.U4.04 (SRC_SENS); `tests/test_config_manager.py` (`:123-162`, `:142-144`, `:216-227`, `:749-761`, `:1572-1583` go or
  shrink; primitive outcome rows; `_stored_float` substitution test) → A.U11.17, A.U4.01, A.U11.21 (TEST_UNIT); L3
  `config_float_round_trip.py` + `flash/test_config_float_round_trip.py` (`persistence_write`) → A.U11.21 (HW_DEV); js
  mock compare gap → A.U4.01/A.U11.21 via U23 (WEB); SPEC G.2 compare-before-write entry, C.5.2, C.10, C.7.3/C.5 float
  sentence → A.U4.01, A.U11.S01, A.U11.21 (SPEC); test-side comment `test_config_manager.py:355` → A.U0.39 (TEST_UNIT).
- **Kind**: code

### M.SRC_CORE.046 One builder for config file names
- **From**: A.U11.32.
- **Site**: `src/config_manager.py:70-76` (beside `instance_name()`).
- **Change**: `def config_filename(cfg_path: str, name: str) -> str: return cfg_path + "config_" + name + ".cfg"`;
  `ConfigManager` stays the one builder of `"CFGMGR_" + name`.
- **Resolved**: G5/R47's "built only by `SensorReaderConfig`" → "built only through `config_manager`'s helper and
  `ConfigManager`" (U11 register fix; the register applies it).
- **Unit**: U11.
- **Depends**: —
- **Blast carried by**: `SensorReaderConfig` → M.SRC_CORE.040; `SystemService` → M.SRC_CORE.008; L0 grep test (no
  `"config_"` concatenation in `src/` outside this file) → A.U11.32 (TSC); L1 case → A.U11.32 (TEST_UNIT); SPEC C.14.1 →
  A.U11.32 (SPEC); `tests_hardware`/`digital_twin` paths built by hand (`A.U26.10`) → unchanged strings.
- **Kind**: code

### M.SRC_CORE.045 The four result words as shared constants
- **From**: A.U19.16.
- **Site**: `src/config_manager.py:210-212`; literal sites `:320-347`.
- **Change**: beside `WriteValidity`, public module constants `VALID: "Final" = "Valid"`, `UNCHANGED: "Final" =
  "Unchanged"`, `INVALID: "Final" = "Invalid"`, `FAILED: "Final" = "Failed"` (plain assignments); every literal site of
  this file (and of `compare_before_write()`) uses them. SPEC G.2 entry "result words".
- **Resolved**: —
- **Unit**: U19.
- **Depends**: —
- **Blast carried by**: `asy_base_classes.py` (M.SRC_CORE.038), `asy_system_service.py` (M.SRC_CORE.017),
  `asy_api_response.py` (M.SRC_CORE.072) literal sites; webserver/SCD30/Wi-Fi sites → A.U19.16 (SRC_NET, SRC_SENS); js
  constant mirror → A.U19.16/U23 (WEB); L0 AST scan and its bite → A.U19.16 (TSC); SPEC G.2 → A.U19.16 (SPEC).
- **Kind**: code

### M.SRC_CORE.048 Readers: one persisting layer, exact-type getters
- **From**: A.U3.05 (the `ConfigManager` half: it persists what it detects; its caller half dropped: OR140.a (7)),
  A.U11.29, A.U11.S01 (3), A.U35.43 (2) (`get_dict()`'s `TypeError`), A.U2.07.
- **Site**: `src/config_manager.py:240-297`.
- **Change**: `_get_values(keys) -> "list[CfgValue] | None"` (`_ERR_CFG_NOT_VALID`; `KeyError` → `_ERR_CONTRACT`).
  `_get_converted_values()` goes; new `_get_typed_values(keys, coerce: "Callable[[CfgValue], T | None]") -> "list[T] |
  None"`: each value through `coerce`, appended unless it returns `None` — the getters pass `_coerce_int`,
  `_coerce_float`, `_as_str` and `_as_bool` (new one-line private helpers `return v if type(v) is str else None` and
  the `bool` twin: the exact-type test is the stored value's real check, and mypy narrows on it); any refusal → one `err_s(self._config_file, "- stored value has the wrong
  type:", key, errno=_ERR_CONTRACT)` and `None` (all-or-nothing). `get_int_values`/`get_float_values`/`get_str_values`/
  `get_bool_values` call it. `get_dict(keys)`: `_ERR_CFG_NOT_VALID`, `except KeyError as e` → `_ERR_CONTRACT` (the
  `TypeError` half goes: keys are typed); its lock-free comment `:268-270` kept.
- **Resolved**: A.U11.29 and A.U11.S01 (3) describe the same helper — merged. A.U11.S01 (3)'s `isinstance(value,
  scalar_type)` after `coerce_numeric()` never fires for a numeric field (lead L1 ruling, M.SRC_CORE.047): the
  coercer-per-type parameter gives the narrowing at the type level instead.
- **Unit**: U11 (U3 stage: the 24 reports; U2 names).
- **Depends**: M.SRC_CORE.047, .049.
- **Blast carried by**: the eleven caller sites keep their own persisted entries (A.U3.05's caller half dropped, OR140.a (7)):
  M.SRC_SENS.035/.037/.043/.044/.063/.074, M.SRC_NET.050/.057/.084/.086/.088; the 21
  getter call sites unchanged → A.U11.29; tests `test_config_manager.py:1496-1552`, caller-module tests → A.U3.05,
  A.U11.29 (TEST_UNIT); SPEC C.5 `:1731-1734`, C.5/C.7 caller rule → A.U11.29, A.U3.05 (SPEC).
- **Kind**: code

### M.SRC_CORE.044 `write_config()` and the deferred flush
- **From**: A.U4.02, A.U11.24, A.U11.25, A.U11.21, A.U11.22, A.U11.28, A.U11.23 (flush half), A.U10.20, A.U35.43 (1)(2),
  A.U2.07, A.U11.04 + A.S0930.16 (1) (closed checks), A.U11.20 (`writable` check), A.U19.16, A.U10.45, A.U14.19 (the
  superseded-write comment's pointer).
- **Site**: `src/config_manager.py:299-388`.
- **Change**: `async def write_config(self, data: "JsonMapping", *, defer: bool = False) -> "tuple[bool,
  WriteValidity]"` (the `cfg_vals` parameter goes; the manager's own schema is used). Before the lock: `if self._closed:
  self.pr.evt(self._config_file, "- writes closed for reset"); return False, {}`; `if not self.valid:` persisted
  `_ERR_CFG_NOT_VALID`, `return False, {}`; `if not self.writable: self.pr.evt(self._config_file, "- unreadable at boot,
  writes refused until the next boot"); return False, {}`. Under `async with self._config_lock:` — first the same
  `_closed` check (A.S0930.16 (1)); `try: outcome = compare_before_write(data, self._cfg_vals, self._current(),
  always=<the special-alone keys of self._cfg_vals>, resolution=<every "float" field → _stored_float>)` / `except
  MemoryError as e:` `_ERR_ALLOC`, `return False, {}`; `outcome is None` → `err_s(…, "- write data is not an object",
  errno=_ERR_BAD_ARG)`, `return False, {}`; per outcome the logging of HEAD (`INVALID` → `_ERR_BAD_ARG`, a key missing
  from the stored config → `_ERR_CONTRACT`, a special-alone key → `VALID` and the `:336` evt line); no bad-default branch
  (the manager's schema passed `setup()`'s self-check; comment "# the manager's own schema passed setup()'s self-check,
  and a malformed schema fails tests_scripts/test_config_schemas.py"); nothing to write → `:349` evt, `return True,
  results`; else `new_cache = dict(self._current())` updated with the float fields' `_stored_float(value)`; `if defer:
  self._commit_ready.clear()` else `self._commit_ready.set()`; `try: task = asyncio.create_task(self._flush_staged(
  new_cache))` / `except MemoryError as e:` `_ERR_ALLOC`, restore `_commit_ready.set()` if it was cleared, `return False,
  {}`; then `self._staged = new_cache`; `self._pending_flush = task` (no await between); `:355` evt; `return True,
  results`. `_flush_staged(staged)`: whole body in `try:` / outer `except Exception as e: report_if_fatal(e); await
  self.pr.err_s(self._config_file, "- flush task failed:", e, errno=_ERR_UNEXPECTED)`; inside: `await
  self._commit_ready.wait()`; `async with self._config_lock:` superseded check (`self._staged is not staged` → return,
  comment "# A newer snapshot was staged while this one waited for its commit or the lock: writing this one / # would
  regress a replaced value (PrintLogHistoryStore._write() applies the same rule)."); `try:` `if staged != self._cache: text = json.dumps(staged)`, `with open(self._config_file,
  "w") as f: f.write(text)`, evt "written"`; `except (MemoryError, OSError, ValueError) as e:` `_ERR_CFG_FILE_WRITE`
  (comment kept); `finally:` the bookkeeping `:384-388` unchanged.
- **Resolved**: A.U11.22 (create the task, then stage) and A.U11.28 (a deferred task waits on `_commit_ready`) keep
  their order (A.U11.28 says so). A.U11.04's "checked first, before the lock" + A.S0930.16's re-check inside the lock →
  both (SUPP conflict 1). A.U2.07's `:356` split (`MemoryError` → 20, `AttributeError` → 21) is superseded: A.U4.02 moves
  the non-dict case into the primitive's `None` (21) and A.U35.43 removes the `AttributeError` class; the remaining
  allocation failure keeps 20. A.U11.23 applies to both write sites (flush here, repair in M.SRC_CORE.043). Gap pass G2:
  `data: "JsonMapping"` — the raw REST body reaches it through `_set_mgr_cfg()` (U19 A-C note 2, M_SRC_NET gap 4); a
  `dict[str, CfgValue]` caller fits the covariant `Mapping`.
- **Unit**: U11 (U4 stage: the primitive inside; U2 names; U14 the comment's pointer, with the rule it names; U19
  constants swap; U30 `report_if_fatal`; A.U35.43 pulled
  into U11 — its reachability fact needs A.U11.28's deferral, which lands here, and its removals are the same lines).
- **Depends**: M.SRC_CORE.047, .049; M.SRC_CORE.038 (callers pass `defer=True` and commit).
- **Blast carried by**: callers `SensorReaderConfig._set_mgr_cfg()` (M.SRC_CORE.040), `SystemService._set_dict_cfg()`
  (M.SRC_CORE.017), `AsyConnTime._set_mgr_cfg()` → no edit (it reaches `write_config()` through `super()`, A.U11.24's Blast "unchanged"; gap pass G2); every test passing a second
  `write_config()` argument (counts in A.U11.24) and device scripts (`system_debug_level_*`, `reboot_persist_*`,
  `isl29125_mechanism_envelope.py`) → A.U11.24 (TEST_UNIT, HW_DEV); `tests_hardware/flash/test_reboot_persistence.py`,
  `bench/test_network_resilience.py`, `tests_hardware/README.md` call shape → A.U11.24 (HW_DEV, HW_BENCH); L1 cases
  (task-creation failure, deferred supersede, flush equal to file, serialise first, flush-task top) → A.U11.22,
  A.U11.28, A.U35.43, A.U11.23, A.U10.20 (TEST_UNIT); `tests/test_config_manager.py:2529-2541` source pins (one
  `create_task(`, zero `json.dump(`) → A.U11.23/A.U11.28 (TEST_UNIT); `tests_scripts/test_device_script_config_flush.py`
  → A.U11.28 (TSC); task-inventory row (config flush) → A.U10.19 (SPEC/TSC); SPEC C.5/C.5.2/C.7.3/F.2 → A.U4.02,
  A.U11.25, A.U11.28, A.U35.43 (SPEC).
- **Kind**: code

### M.SRC_CORE.041 Closing and flushing for a reset
- **From**: A.U11.04 (`close_writes()`, `flush_pending()` releases a deferred flush), A.U11.28 (`commit()`),
  A.S0930.16 (2) (read `_pending_flush` under the lock); OR140.a (12) (`writes_closed()`; A-C review fold).
- **Site**: `src/config_manager.py:390-400` `flush_pending()`; new `close_writes()`, `commit()`.
- **Change**: `def close_writes(self) -> None: self._closed = True` (one-way). `def writes_closed(self) -> bool:
  return self._closed` (read by the reader base's PUT refusal, M.SRC_CORE.038/.040). `def commit(self) -> None:
  self._commit_ready.set()`. `async def flush_pending(self) -> None`: `self._commit_ready.set()`; `async with
  self._config_lock: pending = self._pending_flush`; `if pending is not None: await pending`; comment (≤ 3 lines) "#
  Releases a deferred flush, then awaits the latest flush task read under the lock, so a write_config() / # that held the
  lock has finished staging first; an earlier, superseded task no-ops by its identity check."
- **Resolved**: SUPP conflict 1 (additive).
- **Unit**: U11 (fold stage U20: `writes_closed()`, with M.SRC_CORE.011's close at acceptance).
- **Depends**: M.SRC_CORE.044.
- **Blast carried by**: callers `_flush_config_stores()` (M.SRC_CORE.010), device scripts' flush guard →
  A.U11.28 (TSC `test_device_script_config_flush.py`); L1 close tests → A.U11.04, A.S0930.21/.22 (TEST_UNIT); SPEC
  C.5.2/C.7.3 "a closed store refuses writes" → A.S0930.16 (SPEC).
- **Kind**: code

### M.SRC_CORE.042 A store deletes its own file for "Reset to defaults", readable or not
- **From**: A.S0930.16 (3); OR138.a (2), OR136.a (1) (A-C review fold).
- **Site**: `src/config_manager.py` new `delete_file()`.
- **Change**: exactly A.S0930.16 (3): `async def delete_file(self) -> bool`: `self.close_writes()`; `async with
  self._config_lock:` `os.remove(self._config_file)`, `except OSError as e:` ENOENT → `True`; otherwise one retry, a second
  failure → `self.pr.err(self._config_file, "- could not be deleted:", e)`, `False`; success → `self.pr.evt(…, "- deleted,
  written with the defaults after the reboot")`, `True`. The delete never reads the file and consults neither `writable`
  nor `valid`, so a file that was unreadable or damaged at boot is deleted like any other. Comment (≤ 3 lines) "# Reset
  to defaults (owner, 2026-09-30): deletes the file unread, readable or not (owner, 2026-10-01); / # after the reboot each
  file is written once with its defaults. The SCD30's chip settings stay in its own NVM."
- **Resolved**: the comment's SCD30 clause holds for the chip settings; after A.U15.12 SCD30 owns a `config_SCD30.cfg`
  for its three FRC settings, which the reset deletes like every other store's (OR124.a "every schema-backed
  `config_<name>.cfg`") — the comment reads "the SCD30's chip settings stay in its own NVM" (agent, 2026-10-01).
  OR138.a (2) (A-C review fold): the delete was already read-free; the text now says so, and the after-reboot sentence
  follows OR136.a. The command is answered at acceptance, before S5 runs (OR126.a (3),
  M.SRC_CORE.011): a failed delete is logged (this line; console, FRAM being quiesced at S3) and shows as reset reason
  9 "command incomplete" at the next boot (S5's `ok`), never as an HTTP "Failed" (OR138.a (2) as corrected by the
  lead, 2026-10-05).
- **Unit**: U11.
- **Depends**: M.SRC_CORE.041, M.SRC_CORE.049 (`errno` import).
- **Blast carried by**: caller S5 (M.SRC_CORE.011); tests → A.S0930.21/.25/.27/.28/.29 (TEST_UNIT, TWIN, HW_DEV,
  HW_BENCH, `persistence_write` gate A.S0930.19), plus an unreadable or damaged file deleted and a failed delete ending
  in code 9 → M.TEST_UNIT.253, M.TEST_UNIT.254, M.TEST_UNIT.259, M.TEST_UNIT.306 (fold F03); SPEC C.5.2/C.7.3 → A.S0930.16/.30 (SPEC) with M.SPEC.061, M.SPEC.021, M.SPEC.020, M.SPEC.113 (fold F03).
- **Kind**: code

### M.SRC_CORE.043 `setup()`: a missing file written once with defaults; unreadable never overwritten; file faults recorded; repair serialises first
- **From**: A.U11.19 (the ENOENT split; its no-write clause superseded by OR136.a (1)), A.U11.20, A.U11.23 (repair
  half), A.U35.43 (2) (`:423`, `:479` `TypeError`), A.U2.07, A.U10.21, A.U36.004 (7), A.U10.45; OR136.a (1)-(4),
  OR138.a (1) (A-C review fold).
- **Site**: `src/config_manager.py:402-485`.
- **Change**: `async def setup(self) -> bool`; `await self.pr.setup()` with the `:403-405` comment's cite → "(the implicit
  FRAM-wiring rule, SPECIFICATION.md A.7)". Read: directory → `_ERR_CFG_PATH_IS_DIR`, `return False`; non-object →
  `_WRN_CFG_FILE_NOT_OBJECT`; bad JSON → `_WRN_CFG_FILE_JSON`; `except OSError as e:` `e.errno == errno.ENOENT` →
  `missing = True`, `self.pr.one("Config file", self._config_file, "not present - writing the defaults once")` with one
  comment line "# A genuinely absent file is written once with the defaults (owner, 2026-10-01); an unreadable one never
  is."; any other `OSError` and `except MemoryError` → `await self.pr.wrn_s("Config file", self._config_file, "could
  not be read:", e, wrnno=_WRN_CFG_FILE_UNREADABLE)`, `self.writable = False`. Schema loop as HEAD with
  `_ERR_CFG_NO_DEFAULTS` / `_ERR_CFG_BAD_DEFAULT` (`return False`) and `_WRN_STORED_DEFAULT`; `rewrite` from a readable
  file (bad or missing key, unknown keys → `_WRN_CFG_KEYS_REMOVED`, a readable file with corrupt JSON or a non-object).
  File faults: `self.faulted = True` when the file existed but could not be read (`OSError` other than ENOENT,
  `MemoryError`) or was damaged as a whole — unparseable JSON (W21) or not a JSON object (W20). A missing or unknown key,
  or a stored value the schema refuses (W10), is a repair (the one write of this boot), not damage, and sets no flag
  (lead ruling, 2026-10-05, on OR138.a (1)'s "unparseable or invalid"). The flag is never cleared during the boot, also when the write below repaired
  the file; the module's persisted warning stays (one per boot). Then `self._cache = valid_cfg`, `self.valid = True`;
  no write when not `writable`, when `valid_cfg` is empty (every field special-alone: `self.pr.one(…, "- schema stores
  no values, no file")` — a command-only schema creates no file, and its absence stays that printed note) or when the
  file is readable and nothing needs repair; otherwise the one write of this boot — the repair of a readable file, or
  the schema defaults when `missing` — through one path, compare-before-write applied to the stored state (an absent
  file stores nothing, so every default is a change and is written once): `text = json.dumps(valid_cfg)`, then `with
  open(…, "w") as f: f.write(text)`, `except (MemoryError, OSError) as e:` `_ERR_CFG_FILE_WRITE` (comments `:480`,
  `:482-483` kept). `return self.valid`. After a fresh flash, a filesystem erase or "Reset to defaults" every
  schema-backed module's file therefore exists after the first boot: one write per file per fresh filesystem.
- **Resolved**: A.U11.19 (missing) and A.U11.20 (unreadable) split HEAD's one `except (MemoryError, OSError, TypeError)`
  by errno; A.U35.43 drops `TypeError` (the filename is a typed `str`). OR136.a (owner, 2026-10-01, the most recent
  owner decision) supersedes OR71.a (2)'s "a first boot with no config file writes nothing": a genuinely absent file is
  written once at that boot; an unreadable or corrupt file is still never overwritten and a bad, missing or unknown
  key is still repaired by at most one write per boot (OR71.a (2), unchanged there). OR138.a (1): the flag is the
  store's half of `/status` `ConfigFaults` (the list: M.SRC_CORE.015; the key: M.GEN.008). Wear (CLAUDE.md rule): a
  test that boots a fresh filesystem reaches this write as a prerequisite, not as the write under test, so it stays
  unmarked by `persistence_write` (A-C review fold). One function, two occurrences: a file warning (W20/W21/W10/W22)
  and a failed repair write (`_ERR_CFG_FILE_WRITE`) are the finding and a separate failed write, so both persist; the
  narrowed pair scan (an error and a warning for one occurrence in one function, owner, 2026-09-26) allow-lists the pair
  with that reason (A-C review fold).
- **Unit**: U11 (U2 names as stage).
- **Depends**: M.SRC_CORE.049, .047; M.TEST_UNIT.024, M.TEST_UNIT.077, M.TEST_UNIT.253, M.TEST_UNIT.254, M.TEST_UNIT.256, M.TEST_UNIT.257, M.TEST_UNIT.258, M.TEST_UNIT.306 (fold F01) (the write-counter tests expect exactly one write per file on
  a fresh filesystem; the `faulted` cases) and M.TWIN.104 (fold F01) (a fresh twin config dir gets every module's file at
  its first boot) co-land in U11.
- **Blast carried by**: SystemService reads `writable` (M.SRC_CORE.017) and `faulted` (M.SRC_CORE.015); tests
  `tests/test_config_manager.py` (A.U11.19's list `:838-846`, `:1074-1126`, `:1347-1356`, `:2275-2509`; A.U11.20's
  `:2275-2298`), `tests/test_base_classes.py:1013-1016, 1449-1452` → A.U11.19, A.U11.20, A.U11.23 with the missing-file
  write and the fault flag → M.TEST_UNIT.024, M.TEST_UNIT.077, M.TEST_UNIT.253, M.TEST_UNIT.254, M.TEST_UNIT.256, M.TEST_UNIT.257, M.TEST_UNIT.258, M.TEST_UNIT.306 (fold F01) (TEST_UNIT); twin configs start empty, so a fresh twin run writes
  every module's file once → M.TWIN.104 (fold F01) (TWIN); hardware tests that boot a fresh filesystem reach the write as an
  unmarked prerequisite → M.HW_BENCH.006, M.HW_BENCH.016, M.HW_BENCH.088, M.HW_BENCH.113, M.HW_BENCH.130 (fold F01); L0 "normal boot logs nothing" → A.U35.38/.39 dropped (OR140.a (13)):
  the twin's normal-boot log check expects NTP synced → M.TWIN.168; mockdata W22/W24 rows → A.U2.25/A.U3.15
  (WEB); SPEC C.7.3, C.5.2.1, the CLAUDE.md wear and flash-write wording and the Reset-to-defaults text → A.U11.19,
  A.U11.20 with M.SPEC.061, M.SPEC.096, M.SPEC.021, M.SPEC.020, M.SPEC.097 (fold F01) and M.DOCS.082, M.DOCS.086, M.DOCS.026 (fold F01); register G5/R34 and LEAD/R32 (updated for OR136/OR138).
- **Kind**: code

## src/print_log.py (→ `src/asy_print_log.py`)

End state: `LogConfig`/`DEFAULT_LOG`/`make_logger(log, name)`; `PrintLog` with a refusing `set_level() -> bool` and
explicit `sep`/`end` keywords, no test accessors; `PrintLogHistory` with the newest-entry rule, pre-setup entries kept,
`reset() -> bool`, `setup() -> bool`; `PrintLogHistoryStore` narrowed to allocation failure, newest-state-last writes, a
tri-state read (valid / blank-or-invalid / unreadable) whose `setup()` never overwrites an unreadable store; the C-stack
fatal flag (M.SRC_CORE.034).

### M.SRC_CORE.060 Header, imports and the FRAM Protocols
- **From**: A.U3.01 (header names the rule), A.U11.16 (header's never-raise line), A.U11.S03 (2) (non-generic
  `_FramChunk`), A.U16.19 (Protocol loses `override_pause`), A.U16.06 (4) (`read_into() -> bool | None`), A.U16.05
  (`RegionBuffer`), A.U10.38/A.U10.37 (`CRCBase`, module names), A.U14.19 (`import asyncio`), A.U30.19 via
  M.SRC_CORE.034 (header names the flag); A.U10.31 (the file's one quoted annotation; AC3_S S-03).
- **Site**: `src/print_log.py:1-49`.
- **Change**: docstring: line 1 "Leveled console logging (PrintLog), a bounded error/warning history (PrintLogHistory)
  with optional FRAM-backed persistence (PrintLogHistoryStore), and the C-stack fatal flag the supervisor reads."; line
  2 "A code equal to the history's newest entry is counted and written through but spends no new slot; the console
  prints every call at its level."; line 3 "Never raises: a FRAM chunk operation fails only by allocation, which
  degrades to RAM-only logging." Imports: `asyncio`, `struct`, `from collections import deque, namedtuple`, `from
  micropython import const`, `from asy_crc_checks import CRC8`. `TYPE_CHECKING`: `from typing import Protocol,
  TypedDict`; `ErrEntry`/`ErrorLog` unchanged; `from asy_base_classes import RegionBuffer`; `from asy_crc_checks import
  CRCBase`; `class _FramChunk(Protocol)`: `def get_buffer(self) -> "RegionBuffer"`, `async def write_into(self, buf:
  "RegionBuffer") -> bool`, `async def read_into(self, buf: "RegionBuffer") -> "bool | None"`; `class
  _FramManager(Protocol)`: `get_chunk(…)` with `FRAMManager.get_chunk()`'s final parameters (M.SRC_CORE.090) `->
  "_FramChunk | None"`; the Protocol comment `:38-40` kept (cycle reason); `_BufT`, its comment `:33-35`, `TypeVar`
  and `Any` go. Every annotation in the file that names no `TYPE_CHECKING` symbol is bare (A.U10.31; 1 at HEAD); a
  forward reference stays quoted (D.6).
- **Resolved**: A.U3.01 "rewrites the header (not extends)"; A.U11.16 replaces line 3; one 3-line header carries both.
- **Unit**: U16 (latest: the Protocol's signature changes; stages U3 header line 2, U10 the bare-annotation rule
  (A.U10.31), U11 line 3 and the non-generic Protocol, U30 line 1's flag clause).
- **Depends**: M.SRC_CORE.001, M.SRC_CORE.027, M.SRC_CORE.090.
- **Blast carried by**: `asy_fram_manager.py` `write_into`/`read_into` annotations (M.SRC_CORE.090); FRAM fakes in tests
  drop `override_pause` → A.U16.19 (TEST_UNIT, TEST_HELP); `pyproject.toml:259` ANN401 entry goes (then T20, A.U11.38)
  → A.U11.S03/A.U11.38 (TOOL) + BACKLOG chroot line (DOCS); SPEC C.10 `:2317` holds.
- **Kind**: code

### M.SRC_CORE.061 One logging config object and one logger factory
- **From**: A.U5.01.
- **Site**: `src/print_log.py:282-296`.
- **Change**: `LogConfig = namedtuple("LogConfig", ("fram", "history_length", "debug"))` with the typed shadow
  (`fram: _FramManager | None`, `history_length: int`, `debug: int | None`); `DEFAULT_LOG = LogConfig(None, 10, None)`;
  `def make_logger(log: LogConfig, name: str) -> PrintLogHistory` building the RAM or store logger from the three fields
  as today (comment `:288-289` kept).
- **Resolved**: —
- **Unit**: U5.
- **Depends**: —
- **Blast carried by**: every `make_logger()` user in this cluster (M.SRC_CORE.008, .036, .049, .080 FRAM manager keeps
  RAM-only) and elsewhere → A.U5.02-A.U5.12 (SRC_NET, SRC_SENS); generated `log_<fram>`/`log_ram` → A.U5.03 (GEN); tests
  (`test_asy_uart_link_driver.py`, `test_system_service.py`, device scripts) → A.U5.01 (TEST_UNIT, HW_DEV); SPEC C.7
  `:1822-1823`, G.2 → A.U5.01 (SPEC).
- **Kind**: code

### M.SRC_CORE.066 `PrintLog`'s test-only level accessors go
- **From**: A.U11.15.
- **Site**: `src/print_log.py:74-75`, `:85-107`.
- **Change**: `get_level()` and the six `@staticmethod` level accessors are deleted; tests read `pr.level` and use the
  documented numbers 0-5.
- **Resolved**: —
- **Unit**: U11.
- **Depends**: —
- **Blast carried by**: tests (`test_print_log.py` 20, `test_system_service.py` 20, `_sensortask_scenarios.py` 14,
  `test_captive_dns.py` 12, `test_base_classes.py` 3, `test_asy_wifi_service.py` 2, `test_asy_ntp_client.py` 1;
  `test_print_log.py:107-118` goes) → A.U11.15 (TEST_UNIT, TEST_HELP); `system_service.py:59-60` comment →
  M.SRC_CORE.007.
- **Kind**: code

### M.SRC_CORE.062 `set_level()` refuses an invalid level; the print methods take explicit keywords
- **From**: A.U11.13, A.U11.S03 (1).
- **Site**: `src/print_log.py:68-83`, `:109-130`.
- **Change**: `PrintLog.__init__`: `self.level = _LOG_OFF`; `if level is not None: self.set_level(level)`.
  `set_level(self, level: int | None) -> bool`: accepts only `type(level) is int and _LOG_OFF <= level <= _LOG_ALL`,
  sets it, `True`; else `self.err("PrintLog: invalid level refused:", level)`, `False` (the "clamps …" comment goes).
  `err/wrn/one/evt/all(self, *args: object, sep: str = " ", end: str = "\n") -> None` → `print(self.name, *args,
  sep=sep, end=end)`; the comment `:109-111` goes.
- **Resolved**: G5/R24's "validate through the shared primitive" cannot hold here (`print_log` ← `config_manager`
  import, cycle); U11 register fix states the exact-type form — applied.
- **Unit**: U11.
- **Depends**: —
- **Blast carried by**: level setters typed `Callable[[int], bool]` → M.SRC_CORE.008/.017 and generated
  `_collect_level_setters()` → A.U20.41 (GEN); tests `test_print_log.py:90-100, 128, 131-136` → A.U11.13/A.U11.S03
  (TEST_UNIT); SPEC C.7 "an invalid level is refused, never clamped" → A.U11.13 (SPEC).
- **Kind**: code

### M.SRC_CORE.063 `PrintLogHistory`: newest-entry rule, pre-setup slots, honest sentinels, bool results
- **From**: A.U2.05, A.U3.01, A.U10.11 (pre-setup slot count), A.U10.35 (`err_count` → `_err_count`), A.U11.16 (`_diag()`
  comment), A.U11.31 (`reset() -> bool`), A.U11.S03 (1) (`err_s`/`wrn_s` keywords), A.U10.21 (`setup() -> bool`),
  A.U14.10 (`:136-138` comment), A.U35.35 (K.28 test — test only).
- **Site**: `src/print_log.py:133-223`.
- **Change**: `__init__` comment `:136-138` → "# Clamp to [0, _MAX_CNT] (err_count's own uint16 range) before
  allocating: `[x] * n` can segfault / # the interpreter uncatchably in a size range bytearray()'s guards don't cover - see
  SPECIFICATION.md / # Part F.1's `[x] * n` fact for the measured size boundaries."; `self._err_count = 0`;
  `self._pre_setup_slots = 0`. `_diag()` comment "# print-only: inside the logging layer itself; gated on any logging
  being enabled". `_store_err(self, min_e, max_e, errno) -> None`: count (check-before-step at `_MAX_CNT`, K.28 as HEAD);
  `if errno == _NO_ERR: return`; `code = errno + min_e`; `if errno < 0 or code > max_e: self._diag("PrintLog: Error
  number", errno, "is invalid!")`; `elif not (len(self.history) and self.history[-1] == code):` append, and while not
  `initialized` step `_pre_setup_slots` (check before the step, cap `len(self.history)`); then HEAD's uninitialised
  return and write-through. `get_log()`: an `_NO_ERR`/`_NO_WRN` slot reports `num` 0, type "N". `err_s(self, *args:
  object, errno: int = _NO_ERR, sep: str = " ", end: str = "\n")` and `wrn_s(…, wrnno: int = _NO_ERR, …)` — no
  `repeat`. `async def setup(self) -> bool: self.initialized = True; return True`. `async def reset(self) -> bool`: clear
  ring, `_err_count = 0`, `_pre_setup_slots = 0`, `if not await self._write(): self._diag(…); return False`;
  `self.initialized = True`; `return True` (comment `:214-216` kept).
- **Resolved**: —
- **Unit**: U11 (stages U2 `get_log()`/negative code, U3 the rule and `repeat` removal, U10 `_pre_setup_slots`,
  `_err_count`, `setup() -> bool`).
- **Depends**: M.SRC_CORE.060.
- **Blast carried by**: the five `repeat=` users → A.U3.02 (SRC_NET, SRC_SENS; FRAM's `_episode_wrn()` goes in M.SRC_CORE.081 — pointer fixed, gap pass G2); dedupe tests in
  webserver/notification/ISL29125/FRAM/UART suites → A.U3.01 (TEST_UNIT); `get_log()` 0x80 readers, js render → A.U2.05
  (TEST_UNIT); tests reading `err_count` → A.U10.35 (TEST_UNIT); `test_print_log.py:201-205` K.28 → A.U24.39/A.U35.35
  (TEST_UNIT); `reset()` result users → M.SRC_CORE.019/.037/.049 and A.U11.31 (SRC_NET); SPEC C.7.1 repeat text, H.6
  `:4522` → A.U3.10, A.U2.05 (SPEC).
- **Kind**: code

### M.SRC_CORE.064 `PrintLogHistoryStore` writes: allocation-only guards, little-endian format, newest state last
- **From**: A.U11.09, A.U11.16 (`__init__` and `_write()` halves), A.U11.S03 (2) (`self.fram` type), A.U14.19, AC_NOTES 17.
- **Site**: `src/print_log.py:226-255`.
- **Change**: `self._history_fmt = "<" + "B" * len(self.history)`; `__init__`: `try: self.fram: _FramChunk | None =
  fram.get_chunk(size, crc=CRC8())` / `except MemoryError: self.fram = None` (the broad-catch comments go);
  `self._write_lock = asyncio.Lock()`, `self._write_gen = 0`. `_write()`: `if self.fram is None: return False`;
  `self._write_gen = self._write_gen + 1 if self._write_gen < _WRITE_GEN_MAX else 0` (`_WRITE_GEN_MAX =
  const(0x3FFFFFFF)`, "# wraps inside the small-int range; compared only for equality"); `gen = self._write_gen`; `async
  with self._write_lock:` `if gen != self._write_gen: return True`; `buf = self.fram.get_buffer()`; `dbuf =
  buf.get_data_buf()`; `if dbuf is None: return False`; `try:` pack header and history, `return bool(await
  self.fram.write_into(buf))` / `except MemoryError: return False`. Comment (≤ 3 lines): "# Packed and written under one
  lock; a call a newer one superseded skips, so the newest state lands last / # without relying on asyncio's lock
  hand-off order (ConfigManager._flush_staged()'s rule, by count)."
- **Resolved**: A.U14.19's step `(self._write_gen + 1) & 0x3FFFFFFF` allocates a heap int at the wrap (2**30 is not a
  small int on rp2) — AC_NOTES 17 orders the conditional wrap for every sequence; applied. `COUNTER_CAP` cannot be
  imported here (`asy_base_classes` imports this module), so the file carries its own constant.
- **Unit**: U14 (stages U11: guards, format, `self.fram` type).
- **Depends**: M.SRC_CORE.060.
- **Blast carried by**: `ConfigManager._flush_staged()` comment gains "(PrintLogHistoryStore._write() applies the same
  rule)" → folded into M.SRC_CORE.044's comment text (this cluster; GAP-free); tests `test_print_log.py:42-87, 539-553,
  579-603` and the new gated-write test → A.U11.09, A.U11.16, A.U14.19 (TEST_UNIT); U30's long-lived-object table (one
  lock per store) → A.U30.02 (SPEC); F.1 asyncio list names the guard → A.U14.15 (SPEC).
- **Kind**: code

### M.SRC_CORE.065 `PrintLogHistoryStore` read and setup: merge pre-setup entries; never overwrite an unreadable store
- **From**: A.U10.11, A.U11.16 (`_read()` half), A.U16.06 (4), A.U10.21.
- **Site**: `src/print_log.py:257-279`.
- **Change**: `_read(self) -> "tuple[int, tuple[int, ...]] | bool | None"` mutates nothing: `None` if `self.fram is None`,
  `dbuf is None`, `MemoryError`, or the chunk's `read_into()` returned `None`; `False` when it returned `False` (blank or
  invalid); else `(count, entries)` unpacked from the buffer. `async def setup(self) -> bool`: `if self.fram is None or
  self.initialized: return self.initialized`; `stored = await self._read()`; `if self.initialized: return True` (a
  `reset()` or another setup won during the read); `stored is None` → `self._diag("PrintLog: FRAM unreadable - stored
  history kept, RAM-only until reboot")`, `return False`; a tuple → merge: `tail = list(self.history)[len(self.history) -
  self._pre_setup_slots:]`, `self.history.extend(entries)`, `self.history.extend(tail)`, `self._err_count =
  min(count + self._err_count, _MAX_CNT)`; `False` → keep the RAM ring (re-initialise); then `self._pre_setup_slots = 0`;
  `if await self._write(): self.initialized = True` else `self._diag("PrintLog: FRAM setup failed!")`; `return
  self.initialized`.
- **Resolved**: A.U10.11's `(count, entries) | None` and A.U16.06's `False`/`None` split are one tri-state (A.U16.06's
  Depends names this merge).
- **Unit**: U16 (A.U10.11's and A.U11.16's `_read()` halves are pulled into U16's rewrite of the same lines; no earlier
  unit's work needs them).
- **Depends**: M.SRC_CORE.063, .064, M.SRC_CORE.088 (chunk `read_into()` tri-state).
- **Blast carried by**: tests `test_print_log.py:401, 408, 586, 601, 629` and the new merge/race/unreadable cases →
  A.U10.11, A.U16.06 (TEST_UNIT); `tests/_sensortask_scenarios.py:1160-1175`, twin `:300-320` → A.U10.11 (TEST_HELP,
  TWIN); L2 write-protected chip keeps its bytes → A.U16.06 (TWIN); SPEC C.7 setup sentences, A.4 FRAM bullet →
  A.U10.11, A.U16.06 (SPEC).
- **Kind**: code

## src/api_response.py (→ `src/asy_api_response.py`)

End state: `make_response()` over one envelope code catalog (0, 1 and the shaped HTTP statuses); `handle_set_cmd()`
always answers OK with per-field results, a failing post-write hook turning its group's fields "Failed"; the shared
`_RequestLike` stand-in (with `sock` for the static routes); no `parse_cmd_request()`.

### M.SRC_CORE.070 Header states the module's current role
- **From**: A.U11.26 (header comment `:4-6`), A.U10.37 (name); adherence: the docstring's second line is history
  ("replaces the old, now-deleted improved-quality/api_helpers.py's …") — the current-state rule (CLAUDE.md working
  agreement "Documentation contains current state … not the historic path"; A.U36.548's scope "docs and comments state
  current facts, not history") — no action lists this site (GAP closed here).
- **Site**: `src/api_response.py:1-6`.
- **Change**: docstring "REST response envelope and settings-group setter dispatch for the Microdot layer; every
  function returns a well-defined value, never raises." (one line; the history clause goes). Comment `:4-6` → "# Wire
  shape: {"res": "OK"/"ERR", "code": int, "descr": str, "result": ...}; make_response() is pure and total. / #
  handle_set_cmd() drives one module's _set_dict_cfg() plus an optional post-write hook and returns the per-field / #
  outcome, a hook failure included, which the endpoint's OK envelope carries (SPECIFICATION.md Parts A.5 and C.5.3)."
- **Resolved**: —
- **Unit**: U11.
- **Depends**: M.SRC_CORE.072.
- **Blast carried by**: `tests_scripts/test_comment_block_cap.py` (holds).
- **Kind**: doc

### M.SRC_CORE.071 Typed envelope and the shared request stand-in
- **From**: A.U11.S02 (`ResponseEnvelope`, `result`, `post_asy_fct`, `Any` gone), A.U19.06 (2) (`_RequestLike.sock`,
  `_Holder`), A.U8.23 (`:25-26` reason), A.U27.07 (5) (the stand-in stays after `parse_cmd_request()` goes), A.U10.31.
- **Site**: `src/api_response.py:8-29`.
- **Change**: `TYPE_CHECKING`: `from collections.abc import Callable`; `from typing import Protocol`; `from
  asy_base_classes import AsyncCallback, JsonMapping, SensorReaderConfig`; `from asy_config_manager import ConfigSchema,
  WriteValidity`; `ResponseEnvelope = dict[str, "str | int | JsonMapping"]`; `class _Holder(Protocol): def hold(self,
  closable: object) -> None: ...`; `class _RequestLike(Protocol)`: `json` property (`object`), `sock: "tuple[_Holder,
  _Holder]"`, comment "# Structural stand-in for microdot.Request: typed via the vendored upstream stub
  (ext/typings/microdot/), / # which leaves get/put/route unannotated (v2.6.2); shared with asy_webserver_service.py.";
  `Any`/`Coroutine` go. Runtime imports: `const`, `from asy_print_log import report_if_fatal`, `from asy_config_manager
  import FAILED, VALID`.
- **Resolved**: A.U11.S02 names `_RequestLike`/`parse_cmd_request()`'s `-> tuple[dict[str, object] | None, …]` return;
  that function goes (A.U27.07), so only the Protocol's typing survives.
- **Unit**: U19 (A.U19.06's `sock` member; U11 stage: A.U11.S02's aliases; U8 stage: A.U8.23's comment).
- **Depends**: M.SRC_CORE.030.
- **Blast carried by**: `asy_webserver_service.py:28, 71` imports and comment, `_TimeoutStreamProxy.hold()`/`release()`
  → A.U19.06, A.U8.23 (SRC_NET); request builders in tests pass `sock=(_NoopHolder(), _NoopHolder())` → A.U19.06
  (TEST_UNIT, TEST_HELP); `pyproject.toml` baseline → A.U8.24 (TOOL); SPEC A.5 checklist names the stand-in → A.U19.19
  (SPEC).
- **Kind**: code

### M.SRC_CORE.072 `handle_set_cmd()` returns per-field results; a failing hook fails its group
- **From**: A.U11.26, A.U32.03, A.U2.18, A.U2.04, A.U19.16, A.U30.19.
- **Site**: `src/api_response.py:30-34`, `:81-105`.
- **Change**: `_ERR_CALLBACK = const(14)` replaces `_ERRNO_UNHANDLED_DISPATCH` and its comment `:30-33` ("# Global
  catalog numbers, valid on any logger."). `handle_set_cmd(reader, data: "JsonMapping", cfg_vals: "ConfigSchema", post_fct=None, post_asy_fct: "AsyncCallback
  | None" = None) -> "WriteValidity"` (no `ok_descr`): comment (3 lines, A.U32.03's text) "# Persist and push already
  ran per field in reader._set_dict_cfg(); a per-field outcome is detail in the endpoint's "result". / # The post-write hook runs once
  per call, only after a changed field: one hook per endpoint, not one / # per field, as legacy's post_fct/post_asy_fct
  (agent, 2026-08-03)."; `results = await reader._set_dict_cfg(data, cfg_vals)` (unwrapped: never-raise); `if
  any(status == VALID for status in results.values()):` `try:` sync hook then async hook / `except Exception as e:`
  `report_if_fatal(e)`; `await reader.pr.err_s("Post-write hook failed:", e, errno=_ERR_CALLBACK)`; `results =
  dict.fromkeys(results, FAILED)`; `return results`.
- **Resolved**: A.U2.18 allocates `_ERR_UNEXPECTED` "for any catch-all A.U11 keeps" — none kept, so not allocated (U11
  register fix "For A-C"; AC_NOTES 7). A.U32.03's comment is worded for A.U11.26's body (its own text says so). Gap pass G2 (M_SRC_NET gap 4, U19 A-C note 1):
  A.U11.26 returns the envelope, so the one product caller (`_apply_settings_groups()`) unwraps `result` through an
  `isinstance()` that can never be `False` — the lead's L1 ruling (SUPP_coverage, 2026-09-30; AC_NOTES 38: "a narrowing
  check that can never fire is runtime code and dead code … the fix is at the type level (an honest return type …)")
  settles it: the function returns the per-field `WriteValidity` (U19 A-C note 1's own proposal), the endpoint builds
  the one OK envelope (M.SRC_NET.120) — no wire change. `ok_descr` goes with the envelope: no product caller passes it
  (OR36.a (1); grep `ok_descr`: one test). `data: "JsonMapping"` per U19 A-C note 2.
- **Unit**: U11 (U2 stage: the constant name; U19 constants swap; U30 `report_if_fatal`). The return change lands with
  A.U11.26's body in U11, in one commit with the caller's U11 stage (A.U11.26 already edits `_apply_settings_groups()`'s
  `res == "ERR"` branch there; M.SRC_NET.120).
- **Depends**: M.SRC_CORE.038 (`_set_dict_cfg()` never raises), M.SRC_CORE.045, M.SRC_CORE.034; co-lands with
  M.SRC_NET.120's U11 stage.
- **Blast carried by**: webserver `_apply_settings_groups()` `res == "ERR"` branch and its `:464` comment → A.U11.26 /
  U19 (SRC_NET), the caller merging the returned dict → M.SRC_NET.120; `tests/test_api_response.py:195-332` assert the
  returned dict, `test_handle_set_cmd_ok_descr_override` goes → hand-off TEST_UNIT (M.TEST_UNIT.004/.005; `GAPS_G2.md`);
  `tests/test_api_response.py:282-332` and new hook tests → A.U11.26 (TEST_UNIT); webserver hook-failure
  tests → A.U11.26 (TEST_UNIT); js `render.js:134-160` comment → U23 (WEB); SPEC C.5.3 `:1788-1797` (one edit carrying
  A.U11.26, A.U19.15, A.U32.03) → SPEC merges the three (SPEC), its `handle_set_cmd(…, ok_descr=None)` signature and
  "inside the OK envelope" sentence follow the return change → hand-off SPEC (M.SPEC C.5.3; `GAPS_G2.md`).
- **Kind**: code

### M.SRC_CORE.073 One envelope code catalog; `parse_cmd_request()` goes
- **From**: A.U19.15, A.U27.07 (5), A.U11.26 (codes 4, 5, 100 go).
- **Site**: `src/api_response.py:36-79`.
- **Change**: `_STANDARD_CODES` = `{0: "Command executed", 1: "Invalid JSON request", 400: "Bad request", 404: "Not
  found", 405: "Method not allowed", 413: "Payload too large", 500: "Internal server error"}` with the comment "# The
  one envelope code catalog (SPECIFICATION.md C.5.3): every code listed has a producer; a shaped HTTP / # error uses its
  status as its code."; `make_response(code, descr=None, result: "JsonMapping | None" = None)` unchanged in behaviour
  (the "Unknown error" fallback stays as the totality guarantee). `parse_cmd_request()` and codes 2/3 are deleted.
- **Resolved**: A.U19.15 keeps 2/3 "only while `parse_cmd_request()` exists"; A.U27.07 deletes it (and AC_NOTES 37 drops
  A.U11.26/A.U19.15's U35 dependency, met by A.U27.07) — 2/3 go in the same change.
- **Unit**: U27 (latest: A.U27.07 removes the function and its tests together; U19 stage: the catalog without 4/5/100
  and with the HTTP statuses, which the webserver's shaped errors need in U19).
- **Depends**: M.SRC_CORE.071.
- **Blast carried by**: webserver `_ERROR_STATUSES`, `_shaped_error_handler()`, `_handle_unhandled_exception()`, `:786`
  comment → A.U19.15, A.U27.07 (SRC_NET); `js/mock-server.js` envelope mirror → A.U23.26, A.U19.15 (WEB);
  `tests/test_api_response.py:42-44, 80-100, 125-178` → A.U19.15, A.U27.07 (TEST_UNIT); `tests/test_setter_microdot_integration.py`
  rewrite, `tests/test_asy_webserver_service.py:877` → A.U27.07 (TEST_UNIT); `tests_js/render.test.js:851` → U23 (WEB);
  `pyproject.toml:408-413` override → A.U27.07 (TOOL); SPEC C.5.3/A.8/A.5/`:110`, CLAUDE.md override sentence →
  A.U19.15, A.U27.07 (SPEC, DOCS).
- **Kind**: code

## src/asy_fram_manager.py

End state: `FRAMManager` (renamed) with a RAM-only log, a bump-pointer allocator that also records its chunks, the
storage pause, the erase trio (`quiesce()`, `erase_ready()`, `erase_chip()`), a supervised chip-watch task that
escalates a dead or lost chip; `_FRAMBaseChunk` with a tri-state read (valid / blank-or-invalid /
unreadable), blank blocks never marked busy, no `override_pause`, no episode flags; `FRAMChunk`/`FRAMTimestampedChunk`
built from their manager, the timestamped one on `utc_now()`, bool first. Every layer that meets a chunk failure
keeps its own persisted entry, as at HEAD (OR140.a (7), A-C review fold): a driver guard and the chunk's own entry
both persist.

### M.SRC_CORE.080 Header, imports, constants and the `max_size` limits tag
- **From**: A.U16.01 (header pointer), A.U3.02 (`_WRN_EPISODE_BASE` goes), A.U2.04/A.U2.09/A.U3.09 (constants), A.U3.04
  (dropped: OR140.a (7), A-C review fold),
  A.U16.20 (tag), A.S0930.17 (`_ERASE_UNIT`), A.U10.37/A.U10.38 (imports, names), A.U16.S01 (types), A.U16.05
  (`RegionBuffer`), A.U10.06 (`utc_now`), A.U16.R03 (tunables are the driver's), M.SRC_CORE.034 (`report_if_fatal`).
- **Site**: `src/asy_fram_manager.py:1-38`.
- **Change**: docstring line 3 → "FRAMManager is a bump-pointer allocator (construction order is the on-chip layout,
  fixed within one build: SPECIFICATION.md A.4/A.7); every method returns a well-defined value - never raises."
  Imports: `asyncio`, `struct`, `const`; `from asy_fram_driver import FRAM_SPI`; `from asy_spi_driver import SPI`; `from
  asy_base_classes import RegionBuffer, utc_now`; `from asy_crc_checks import CRCBase, CRCPass`; `from asy_print_log
  import DEFAULT_LOG, PrintLogHistory, report_if_fatal`; `TYPE_CHECKING`: `Callable`, `from asy_base_classes import
  ErrorSource, NtpSyncFct, TaskStarter, TimerStarter`, `from asy_print_log import ErrorLog, LogConfig`; `time`,
  `Coroutine`, `Any` go. Constants: status/address constants unchanged; `_TS_FMT`, `_TS_UNINIT` unchanged; `_NAME`;
  `_ERASE_UNIT = const(256)` ("# one erase write: 2.1 ms at the 1 MHz bus, divides both chip sizes; the size class the
  webserver's chunked writes use (Part I.3)"); `_ERR_INIT = const(10)`, `_ERR_CALLBACK = const(14)`, `_ERR_ALLOC =
  const(20)`, `_ERR_BAD_ARG = const(21)`, `_ERR_UNEXPECTED = const(23)`, `_ERR_FRAM_STATUS_BYTE = const(46)`,
  `_ERR_FRAM_STATUS_DISAGREE = const(47)`, `_ERR_FRAM_CRC_FAILED = const(48)`, `_ERR_FRAM_DATA_CRC = const(49)`,
  `_ERR_FRAM_VERIFY = const(50)`, `_ERR_FRAM_COPIES_DIFFER = const(51)`, `_WRN_FRAM_PAUSED = const(25)`, and the chunk
  layer's own entries for a failure an inner layer also persisted (HEAD's 61/62, 71/72, 18, 37, 57, 80, the status-byte
  read/write codes and w71-73, kept persisted by OR140.a (7)): `_ERR_FRAM_BLOCK_WRITE`, `_ERR_FRAM_STATUS_READ`,
  `_ERR_FRAM_STATUS_WRITE`, `_ERR_FRAM_PAYLOAD_WRITE`, `_ERR_FRAM_READ`, `_ERR_FRAM_CLEAR_WRITE`, `_ERR_FRAM_CLEAR`,
  `_WRN_FRAM_BLOCK_INVALID` — new FRAM-band rows after the band's last used code, numbered at execution in landing
  order with the catalog as the numbering source (M.GEN.034); one comment line
  "# The legal chip sizes; tests_scripts/test_buildgen_limits.py keeps them equal to asy_fram_driver's
  _KNOWN_PRODUCT_IDS." and the tag `# @limits max_size in {0x2000, 0x40000}`.
- **Resolved**: e16 CLOCK (`:550`, `:614`) retires with A.U10.06; e82 (`:563`) retires with A.U35.55; neither gets a
  constant.
- **Unit**: U16 (stages: U2 constants at HEAD sites, the chunk layer's own codes included; U3 `_WRN_EPISODE_BASE`
  removal; U10 renames/imports).
- **Depends**: M.SRC_CORE.001, .027, .032, M.SRC_CORE.115; M.SRC_CORE.034 [follows] (its U30 handler lines in this file come after) (`CRCBase`, `CRCPass`).
- **Blast carried by**: `buildgen/validate.py` `_check_limits()` reads the tag; the new L0 agreement test and the
  bad-size case → A.U16.20 (GEN, TSC); fixtures `novel_combo.toml:121`, `multi_instance.toml:98` → 0x40000 → A.U16.20/
  A.U16.17 (TSC); catalog rows (46-51, 25, the chunk layer's own codes, retirements 16/82, errno 20's "A.U3.09's new FRAM buffer
  checks") → A.U2.01 merge (GEN, M.GEN.034); SPEC A.4/A.7/C.7/K.7 layout-within-one-build text, C.3.1 size sentence → A.U16.01, A.U0.38, A.U16.20
  (SPEC); `devices/dev.toml:96-98` comment → A.U16.01 (GEN); `tests/test_digital_twin_uart_link.py:173-175` → A.U16.01
  (TWIN).
- **Kind**: code, doc

### M.SRC_CORE.081 Chunk construction from the manager; no episode state
- **From**: A.U5.13, A.U10.38 (`_FRAMBaseChunk`), A.U10.17 (`_op_lock` reason), A.U3.02 (`_episode_wrns`,
  `_episode_wrn()` go), A.U16.06 (`_read_fault`), A.U10.45.
- **Site**: `src/asy_fram_manager.py:41-94`.
- **Change**: `class _FRAMBaseChunk:` `__init__(self, manager: "FRAMManager", base_addr: int, size: int, crc: CRCBase,
  verify: int = 0, check_length: int = 8)`: `self.pr = manager.pr`, `self._mempause = manager.get_pause`, `self.fram =
  manager.fram` (bound once); `self._verify_counter = 0` and `self._block_addr = (…)` (HEAD's expressions; private:
  no reader outside the chunk classes in `src/` or the generated code, G10/R07 — gap pass G2, M_SRC_CORE GAP-G12
  applied across `src/`; every use in the file follows); the rest as HEAD; `self._op_lock = asyncio.Lock()` with the reason line "# serialises this
  chunk's own write/read/clear end to end, across both blocks and the scratch buffers"; `self._read_fault = False` beside
  the other read state (`:81-84`); `_episode_wrns` and `_episode_wrn()` gone; the `(MemoryError, OverflowError)` tuple
  unchanged.
- **Resolved**: —
- **Unit**: U16 (U5 stage: the manager parameter; U3 stage: episode removal).
- **Depends**: M.SRC_CORE.080.
- **Blast carried by**: callers `get_chunk()`/`get_timestamped_chunk()` (M.SRC_CORE.091); `tests/test_asy_fram_manager.py:2350-2389`
  (`chunk.fram`) holds; episode tests `:2587-2640` → A.U3.02 (TEST_UNIT); readers of `block_addr`/`verify_counter` in
  `tests/`, `digital_twin/` and `tests_hardware/device_scripts/` (64 sites at HEAD) and the region check of M_HW_DEV
  GAP-D7 (`chunk.block_addr`) → hand-offs TEST_UNIT, TEST_HELP, HW_DEV, TSC (`GAPS_G2.md`).
- **Kind**: code

### M.SRC_CORE.082 Chunk write: silent while the chip is lost; the chunk layer keeps its own entry
- **From**: A.U16.19, A.U3.02, A.U3.04 (dropped: OR140.a (7), A-C review fold), A.U2.09, A.U16.R03 (5).
- **Site**: `src/asy_fram_manager.py:96-126` `_write()`.
- **Change**: `async def _write(self, buf: bytearray) -> bool`: `if self.fram.lost.is_set(): return False` (no log: the
  loss is its one errno-54 event); under `self._op_lock`: `if self._mempause():` `wrn_s("FRAM communication paused, not
  writing FRAM!", wrnno=_WRN_FRAM_PAUSED)`, `False`; size mismatch → `err_s(…, errno=_ERR_BAD_ARG)`; a failed block
  write → `err_s("Writing block N failed!", errno=_ERR_FRAM_BLOCK_WRITE)` (this layer's own entry beside the inner one,
  as at HEAD), `False`; verify pass: per block `valid,
  uninit, match, fault = await self._compare_with(buf, addr)`; `not valid or uninit or not match` → `err_s("Block", n,
  "write verification error!", errno=_ERR_FRAM_VERIFY)` (every verify failure persists, as at HEAD), `False`; the `_episode_wrns = 0` reset goes.
- **Resolved**: A.U16.R03 (5) also asks the driver's reporters to pass `repeat=True` for NOT_INIT while lost; A.U3.01
  removes `repeat=` from every logger, and with this entry guard no chunk operation reaches the driver while lost — that
  clause is dropped (M.SRC_CORE.103 Resolved).
- **Unit**: U16 (stages: U2 numbers; U3 episode removal).
- **Depends**: M.SRC_CORE.081, M.SRC_CORE.088 (`_compare_with()` 4-tuple), M.SRC_CORE.102 (`lost`).
- **Blast carried by**: tests asserting the multi-entry sequences (`tests/test_asy_fram_manager.py`, `:952`,
  `tests/test_fram_integration.py` 19 lines) keep them, renumbered (A.U2.09; A.U3.04 dropped) → [fold F11
  M_TEST_UNIT]; override tests
  `:428-440`, `:1117-1130` deleted, `:1109, :1253-1254` → A.U16.19 (TEST_UNIT); twin hazard file `:414-432, :463-464` →
  A.U16.19 (TWIN); device scripts `fram_pause_unpause_and_gating.py`, `fram_write_protect_roundtrip.py` → A.U16.19
  (HW_DEV); SPEC A.4 `:175, 185, 207-208`, F.5.2 `:3752`, BACKLOG `:476` → A.U16.19 and the renumbering A.U2.09 (SPEC, DOCS;
  A.U3.04's one-entry text dropped); `tests_hardware/README.md:401` → A.U2.09 (HW_BENCH; the pair stays two entries).
- **Kind**: code

### M.SRC_CORE.088 Chunk read: tri-state result, faults told from invalid data
- **From**: A.U16.06 (1)-(2), A.U3.04 (dropped: OR140.a (7), A-C review fold), A.U3.02, A.U16.08 (`:174-175` comment), A.U16.19, A.U16.R03 (5), A.U2.09.
- **Site**: `src/asy_fram_manager.py:128-221` (`_read()`, `_read_progress()`, `_read_into()`, `_compare_with()`).
- **Change**: `async def _read(self, buf: bytearray) -> bool | None`: `if self.fram.lost.is_set(): return None`; under
  `_op_lock`: paused → `wrn_s(…, wrnno=_WRN_FRAM_PAUSED)`, `None`; size mismatch → `_ERR_BAD_ARG`, `None`; block 0
  `valid, uninit, fault = await self._read_into(buf, addr0)`; not valid → "Uninitialized data in block 0, reading block 1" evt,
  else `wrn_s("Read fault in block 0, reading block 1" / "Invalid data in block 0, reading block 1",
  wrnno=_WRN_FRAM_BLOCK_INVALID)` (persisted, as HEAD's w71-73); block 1 likewise; neither valid → `None` if either
  faulted, else `False`; block 1 valid → repair block 0, a failed repair write → `err_s("Writing block 0 failed!", errno=_ERR_FRAM_BLOCK_WRITE)`, `None`; block 0 valid →
  `_compare_with()` block 1 (4-tuple), not valid → the evt (uninitialised) or `_WRN_FRAM_BLOCK_INVALID`, then repair block 1 (a failed write → `_ERR_FRAM_BLOCK_WRITE`,
  `None`); not matching →
  comment "# No generation counter says which block is newer, so a write torn between blocks leaves two valid / # but
  differing copies: a hard failure, never a guess (owner, 2026-07-18). The next write heals it." and `err_s("Both
  blocks valid but different data", errno=_ERR_FRAM_COPIES_DIFFER)`, `False`; else `True`. `_read_into()` resets
  `_read_fault` with the other state and returns `(valid, uninit, self._read_fault)`; `_compare_with()` returns
  `(valid, uninit, match, fault)` (missing scratch → persisted `_ERR_ALLOC` and `(False, False, False, True)`, A.U16.06
  (1)). No `_episode_wrn()` call and no `_episode_wrns` reset remain.
- **Resolved**: A.U3.04 is dropped (OR140.a (7), A-C review fold); the 20 at `_check_buf is None` stays — a condition
  this layer detects itself, which A.U16.06 lists as a fault. A block's invalid-data warning and a failed repair write
  of that block are the finding and a separate failed write, so both persist — the narrowed pair scan (an error and a warning for one occurrence in
  one function, owner, 2026-09-26) allow-lists it with that reason (A-C review fold).
- **Unit**: U16.
- **Depends**: M.SRC_CORE.081, .084, .085.
- **Blast carried by**: `PrintLogHistoryStore._read()` (M.SRC_CORE.065); SGP40 restore reads falsy → A.U16.06 (SRC_SENS,
  unchanged); tests `tests/test_asy_fram_manager.py:235, 839, 885-910, 1003, 1085-1096, 2094, 2210-2248, 2332, 2433` and
  new L1 cases → A.U16.06 (TEST_UNIT), the per-layer entries → M.TEST_UNIT.041, .044, .046; `_read()` joins the fault-or-warning scan's allow-list (an invalid block, then a failed repair write) → M.TSC.111; `:329-331` comment → A.U16.08 (TEST_UNIT); L2 WP chip keeps its bytes →
  A.U16.06 (TWIN); SPEC A.4 `:205-206`, `:214`, C.7 → A.U16.06, A.U16.08 (SPEC).
- **Kind**: code

### M.SRC_CORE.084 Status bytes: a blank block takes no busy marker; faults flagged; no errno arithmetic
- **From**: A.U2.09 (`err=` goes), A.U16.09, A.U16.06 (1), A.U3.04 (dropped: OR140.a (7), A-C review fold).
- **Site**: `src/asy_fram_manager.py:223-268`.
- **Change**: `_set_check_sb(self, fram, st_addr, val, *, check_idle) -> bool | None`: `check_idle` read failure →
  `await fram.report_get_values(read_status)`, `err_s("Read status byte failed!", errno=_ERR_FRAM_STATUS_READ)`, `self._read_fault = True`,
  `None`; a byte neither idle nor uninit → `err_s("Read status byte is not", _STATUS_IDLE, "but", stat[0],
  errno=_ERR_FRAM_STATUS_BYTE)`, `None`; a byte reading `_STATUS_UNINIT` → `return True` with "# a blank block is never
  read, so it takes no busy marker and stays blank"; the write → failure `err_s("Write status byte failed!", errno=_ERR_FRAM_STATUS_WRITE)`,
  `self._read_fault = True`, `None`; else `False`. The `:240-242` and `:256-257` errno-spread comments go.
  `_handle_status_bytes(self, fram, addr, val, *, check_idle) -> bool | None`: two calls without `err`; inconsistent
  pair → `err_s(…, errno=_ERR_FRAM_STATUS_DISAGREE)`, `None`.
- **Resolved**: —
- **Unit**: U16 (U2 stage: the `err=` removal with the renumbering).
- **Depends**: M.SRC_CORE.081.
- **Blast carried by**: wire-trace golden `_GOLDEN_BLANK_SETUP` (74 → 54 CS cycles), header, count test →
  A.U16.09 (TEST_UNIT); `tests/test_asy_fram_allocation_budget.py:65-66` comment, `tests/test_asy_fram_manager.py:1538,
  1686-1687, 2509-2511` → A.U16.09 (TEST_UNIT); L2 double read → A.U16.09 (TWIN); SPEC A.4 `:178`, `:201-202` →
  A.U16.09 (SPEC); the A.4 protocol account → A.U16.12 (SPEC).
- **Kind**: code

### M.SRC_CORE.085 Block operations: numbered by the catalog, faults flagged, overflow-free comments
- **From**: A.U2.09, A.U3.04 (dropped: OR140.a (7), A-C review fold), A.U16.06 (1), A.U14.10 (`:368`), A.U16.19 (`clear()`), A.U16.R03 (5) (`clear()`), A.U30.19,
  A.U10.45.
- **Site**: `src/asy_fram_manager.py:270-399` (`_write_chunk()`, `_read_chunk()`, `_clear_chunk()`, `clear()`).
- **Change**: every `_handle_status_bytes()` call loses `err=` and its "check_idle=… may only set err to err + N"
  comment; `_write_chunk()`: CRC not computable → `err_s(…, errno=_ERR_FRAM_CRC_FAILED)`; payload write failure →
  `err_s("_write_chunk failed!", errno=_ERR_FRAM_PAYLOAD_WRITE)`; `except Exception as e: report_if_fatal(e)`, `err_s(…, errno=_ERR_UNEXPECTED)`.
  `_read_chunk()`: zero-length buffer → `err_s(…, errno=_ERR_BAD_ARG)` and `_read_fault = True`; driver read failure →
  `report_get_values()`, `err_s("FRAM read error in _read_chunk!", errno=_ERR_FRAM_READ)`, fault; incremental CRC failure → `err_s(…,
  errno=_ERR_FRAM_CRC_FAILED)`, fault; data CRC mismatch → `err_s(…, errno=_ERR_FRAM_DATA_CRC)` (content, not a fault);
  `except Exception as e: report_if_fatal(e)`, `_ERR_UNEXPECTED`, fault. `_clear_chunk()`: comment `:367-368` → "#
  bytearray(n) zero-fills directly (same content as `[_STATUS_UNINIT] * n`) without building that list first / #
  `[x] * n` can segfault uncatchably for large n (Part F.1)."; write failure → `err_s(…, errno=_ERR_FRAM_CLEAR_WRITE)`; `except Exception as
  e: report_if_fatal(e)`, `_ERR_UNEXPECTED`. `clear(self) -> bool`: `if self.fram.lost.is_set(): return False`; paused →
  `wrn_s(…, wrnno=_WRN_FRAM_PAUSED)`; a failed block → `err_s("Clearing chunks failed!", errno=_ERR_FRAM_CLEAR)` (each a layer's own entry, as at
  HEAD; OR140.a (7)).
- **Resolved**: —
- **Unit**: U16 (stages U2 with the chunk layer's codes, U14 comment; U30 `report_if_fatal`).
- **Depends**: M.SRC_CORE.084.
- **Blast carried by**: as M.SRC_CORE.082/.088 (A.U2.09 test lines; A.U3.04 dropped) → M.TEST_UNIT.041, .044, .046; wire traces unchanged except the blank
  case (M.SRC_CORE.084).
- **Kind**: code

### M.SRC_CORE.086 The chunks' caller-less `get_size()` and `get_pause()` go
- **From**: A.U16.22.
- **Site**: `src/asy_fram_manager.py:381-382, 427-428, 509-510`.
- **Change**: the three methods are deleted; `get_verify()`/`set_verify()` stay (SGP40 uses both).
- **Resolved**: A.S0930.17 uses the driver's `get_size()` (OR36.a (3)), not a chunk's.
- **Unit**: U16.
- **Depends**: M.SRC_CORE.081.
- **Blast carried by**: `tests/test_asy_fram_manager.py:1995-2024` → A.U16.22 (TEST_UNIT).
- **Kind**: code

### M.SRC_CORE.089 Chunk buffers: `RegionBuffer` subclasses without the CRC accessor
- **From**: A.U16.05, A.U16.23, A.U10.38 (`FRAMChunkBuffer`, `FRAMChunkTimestampedBuffer`), A.U10.35 (`buf` → `_buf`).
- **Site**: `src/asy_fram_manager.py:402-410`, `:468-481`.
- **Change**: `class FRAMChunkBuffer(RegionBuffer)` keeps only its constructor (data region fixed; `_crc_size` gone);
  `class FRAMChunkTimestampedBuffer(RegionBuffer)` keeps its constructor and `get_ts_buf()` (reading `self._buf`),
  `_crc_size` and `get_crc_buf()` gone.
- **Resolved**: —
- **Unit**: U16.
- **Depends**: M.SRC_CORE.027.
- **Blast carried by**: `tests/test_asy_fram_manager.py:2027-2081` → A.U16.23 (TEST_UNIT); renames in tests → A.U10.38
  (TEST_UNIT); SPEC E.5.1 `:3025-3027` → A.U35.41 (SPEC).
- **Kind**: code

### M.SRC_CORE.090 Plain chunk I/O: one entry for a missing buffer; the unreachable second check stated
- **From**: A.U3.09 (the `None`-buffer 20s; its SGP40 half dropped: OR140.a (7)), A.U35.47, A.U16.06 (3), A.U16.19, A.U11.S03 (2), A.U2.09 (e84 → 21), A.U10.38 (`FRAMChunk`).
- **Site**: `src/asy_fram_manager.py:413-465`.
- **Change**: `class FRAMChunk(_FRAMBaseChunk)` with the manager constructor (the explicit `__init__` that only
  forwarded goes). `get_buffer() -> FRAMChunkBuffer`. `write(data)`: `databuf is None` → `err_s("No buffer for the chunk
  write", errno=_ERR_ALLOC)`, `False`; too long → `err_s(…, errno=_ERR_BAD_ARG)` (the `:439` "84, not 80" comment goes);
  `return await self.write_into(buf)`. `write_into(self, buf: RegionBuffer) -> bool`: `get_buf()` `None` → `_ERR_ALLOC`,
  `False`; `return await self._write(dbuf)`. `read(self) -> bytearray | None`: `if not await self.read_into(buf): return
  None`; the second accessor keeps `return None` with "# Unreachable: read_into() already failed on a missing buffer,
  and a RegionBuffer's buffer is fixed at construction - kept to narrow the Optional for the type checker."
  `read_into(self, buf: RegionBuffer) -> bool | None`: `get_buf()` `None` → `_ERR_ALLOC`, `None`; `return await
  self._read(dbuf)`.
- **Resolved**: A.U3.09 adds a persisted 20 to every `None`-buffer return (`:436, 448, 457, 463`); A.U35.47 keeps
  `:457` as an unreachable narrowing. Per line: the first accessor of a buffer is reachable (its allocation can fail)
  and persists 20; a second accessor on the same buffer is unreachable and keeps the bare return with A.U35.47's
  comment (G5/R54, A.U35.41's verdict "keep as type narrowing").
- **Unit**: U16 (stages U3: the 20s; U11: A.U11.S03's annotation; U35: A.U35.47's comment pulled into U16's rewrite of
  the same lines).
- **Depends**: M.SRC_CORE.082, .088, .089.
- **Blast carried by**: `print_log.py`'s store (M.SRC_CORE.064/.065); new L1 "a `None` chunk buffer persists 20 once" →
  A.U3.09 (TEST_UNIT); SPEC E.5.1 narrowing line → A.U35.41 (SPEC).
- **Kind**: code

### M.SRC_CORE.087 Timestamped chunk: `utc_now()`, bool-first writes, no unreachable guards
- **From**: A.U16.18, A.U10.06, A.U14.26 (1) dropped (V.U18.R10: no catch around the timestamp), A.U35.55, A.U3.09 (the `None`-buffer 20s; its SGP40 half dropped: OR140.a (7)),
  A.U35.47, A.U16.19, A.U16.S01, A.U10.35 (`_ntp_sync_callback`), A.U2.09 (85/87 → 14), A.U30.19, A.U5.13, A.U10.38.
- **Site**: `src/asy_fram_manager.py:484-615`.
- **Change**: `class FRAMTimestampedChunk(_FRAMBaseChunk)`: `__init__(self, manager, base_addr, size, ntp_sync_callback:
  "NtpSyncFct", crc, verify=0, check_length=8)` → `super().__init__(manager, base_addr, struct.calcsize(_TS_FMT) + size,
  crc, …)`, `self._ntp_sync_callback`. `write(data, *, require_ntp=False) -> tuple[bool, bool, int | None]`: missing buffer →
  `_ERR_ALLOC`, `(False, False, None)`; too long → `_ERR_BAD_ARG`; `write_into(buf, *, require_ntp=False) ->
  tuple[bool, bool, int | None]`: callback guarded (`except Exception as e: report_if_fatal(e)`, `err_s("NTP sync callback
  failed:", e, errno=_ERR_CALLBACK)`, not synced); `utc = utc_now() if ntp_synced else None`; `None` → evt "not valid",
  `ntp_synced = False`, `utc = _TS_UNINIT[0]`, and `if require_ntp: return False, False, None`; else evt "valid"; `tbuf =
  buf.get_ts_buf()`, `None` → `_ERR_ALLOC`, `(False, False, None)`; `struct.pack_into(_TS_FMT, tbuf, 0, utc)` (no guard);
  `bbuf = buf.get_buf()`, `None` → `(False, False, None)` with A.U35.47's narrowing comment; `return await
  self._write(bbuf), ntp_synced, utc`. `read(self) -> tuple[int | None, int | None, bytearray | None]` unchanged in shape
  (the second accessor keeps its narrowing comment). `read_into(self, buf) -> tuple[bool | None, int | None, int |
  None]`: `bbuf` `None` → `_ERR_ALLOC`, `(None, None, None)`; `res = await self._read(bbuf)`; not `True` → `(res, None,
  None)`; `tbuf` `None` → `(None, None, None)` (narrowing comment); `ts = int(struct.unpack_from(_TS_FMT, tbuf, 0)[0])` (no
  guard); `_TS_UNINIT` → evt, `ts = None`; else evt, callback guarded as above, `now = utc_now() if ntp_synced else
  None`, "# signed: negative after the RTC stepped back (NTP_Offset_S, a correction); the caller treats that as
  expired", `age = None if now is None else now - ts`; `return True, ts, age`.
- **Resolved**: A.U10.06 vs A.U14.26 at `:547/:611` → A.U10.06 (V.U18.R10, U18 register fix 10). A.U16.18's
  message change "Packing the timestamp failed" is moot (A.U35.55 removes the guard; A.U35.55's Depends says so).
- **Unit**: U16 (stages U10 `utc_now()`; U35's removal pulled into U16's rewrite — A.U35.55 is a B3 removal with no
  prerequisite and the same lines; U30 `report_if_fatal`).
- **Depends**: M.SRC_CORE.032, .082, .088, .089, .090.
- **Blast carried by**: SGP40 `_run_backup()` unpack order and the negative-age expiry → A.U16.18 (SRC_SENS);
  `tests/test_asy_fram_manager.py` reorders/annotations (A.U16.18's list), `:677-700`, `:1940-1974` (`utc_now()` path;
  A.U14.26's renames dropped with its handler), `:2126-2195` (two raising-`struct` tests go) → A.U16.18, A.U10.06,
  A.U35.55 (TEST_UNIT); `tests/test_ntp_fram_system_integration.py`, `tests/test_fram_integration.py:92`,
  `tests/test_asy_fram_wire_trace.py:451`, `tests/test_asy_sgp40_driver.py:1055-1056` → A.U16.18 (TEST_UNIT); device
  script `fram_pause_unpause_and_gating.py:151-154` → A.U16.18 (HW_DEV); tests setting `utc_valid` → A.U10.06
  (TEST_UNIT); catalog 82 and 86/88 retired → A.U35.55, A.U10.06 (GEN); SPEC `:214-215`, DEVICE_REFERENCE `BackupMaxAge`
  → A.U16.18 (SPEC, DOCS).
- **Kind**: code

### M.SRC_CORE.091 Manager construction, allocation, pause and fan-in
- **From**: A.U5.02, A.U5.13, A.U10.35 (`_allocated_size`), A.U0.41 (`:648`, `:690`, `:726`), A.U16.S01, A.U11.31,
  A.U10.38 (`FRAMManager`, `CRCPass`), A.S0930.17 (2) (`_chunks`), A.U16.R03 (`_was_up`, held as `initialized`, see M.SRC_CORE.092).
- **Site**: `src/asy_fram_manager.py:618-728`, `:739-740`.
- **Change**: `class FRAMManager`: `__init__(self, spi_bus: SPI, spi_cs: int, max_size: int = 0x2000, log: "LogConfig" =
  DEFAULT_LOG)`: `self.pr = PrintLogHistory(log.history_length, log.debug, name=_NAME)` ("# RAM-only: the one module
  that never logs into FRAM is the FRAM module itself (owner, SPECIFICATION.md C.7.1)"), `self.name`, `self.size`,
  `self._allocated_size = 0`, `self._pause = False`, `self._chunks: list[_FRAMBaseChunk] = []` ("# one entry per
  allocation, all made during construction"), `self.initialized = False`, `self.fram = FRAM_SPI(spi_bus, spi_cs,
  max_size=self.size, logger=self.pr)`. `get_error_sources() -> "list[ErrorSource]"`. `get_chunk(size, crc: CRCBase | None
  = None, verify=0, check_length=8) -> FRAMChunk | None` and `get_timestamped_chunk(size, ntp_sync_callback: "NtpSyncFct",
  …)`: the size-0 comment gains "(owner, 2026-07-18: reject generally at the top)"; `CRCPass()` default;
  construct with `self` as manager; append the chunk to `self._chunks`; `_allocated_size` bookkeeping as HEAD.
  `set_pause()` gains "# Finish all ongoing ops, reject new ones (owner, 2026-07-18)". `reset_error_counter()
  -> bool: return await self.pr.reset()`.
- **Resolved**: —
- **Unit**: U16 (stages U5 constructor, U10 names, U11 `-> bool` and the `_chunks` list with its append — the U11
  quiesce of M.SRC_CORE.083 walks it, U0 tags).
- **Depends**: M.SRC_CORE.080, .081, .061.
- **Blast carried by**: generated construction (`FRAMManager(..., log=log_ram)`, class name) → A.U5.03, A.U10.38 (GEN);
  every `get_chunk()`/`get_timestamped_chunk()` caller (print_log store, SGP40) unchanged; `tests/test_asy_fram_allocation_budget.py`
  bound re-derived for the `_chunks` slot → A.S0930.17 (TEST_UNIT); long-lived-object catalog gains `FRAMManager._chunks`
  ("grows once per allocation at construction") → GAP-G9 (TSC A.U30.03, SPEC A.U30.02); tests reading `allocated_size`,
  `ntp_sync_callback` → A.U10.35 (TEST_UNIT); SPEC C.3.1 FRAM API list → A.S0930.17 (SPEC).
- **Kind**: code

### M.SRC_CORE.083 Erase FRAM: close the chunk layer, then blank and zero the whole chip in fed units
- **From**: A.S0930.17 (1), (3)-(5); A.U16.R03 (5) applied to the new `invalidate()`.
- **Site**: `src/asy_fram_manager.py` new `_FRAMBaseChunk.wait_idle()`, `invalidate()` (beside `_clear_chunk()`/`clear()`);
  new `FRAMManager.quiesce()`, `erase_ready()`, `erase_chip()`.
- **Change**: exactly A.S0930.17: `wait_idle()` (`async with self._op_lock: pass`, its comment); `invalidate() -> bool`:
  `if self.fram.lost.is_set(): return False`; under `_op_lock`, per block `async with self.fram as fram:
  _handle_status_bytes(fram, addr, _STATUS_UNINIT, check_idle=False)`; `False` at the first failed block; no pause
  check (only the erase calls it, after the manager closed the chunk layer); `quiesce(step_done)`: pause, then each
  chunk's `wait_idle()` and `step_done()`; `erase_ready()`: `self.fram.initialized and not await
  self.fram.get_write_protected()`; `erase_chip(step_done) -> bool`: refuse unless ready; pass 1 `invalidate()` per chunk
  with `step_done()`; any failure → stop before pass 2 (`self.pr.err(…)`, `False`); `unit = bytearray(_ERASE_UNIT)`
  (`MemoryError` → `False`); pass 2 over `range(0, await self.fram.get_size(), _ERASE_UNIT)`: `async with self.fram as
  fram: status = fram.set_values_sync(unit, addr)`, then `if status and not await self.fram.report_set_values(status):`
  stop, `False`; `step_done()`; `await asyncio.sleep(0)`; end `self.pr.evt("FRAM erased:", size, "bytes")`, `return ok`.
  Comment at `erase_chip()` (≤ 3 lines) as A.S0930.17.
- **Resolved**: SUPP conflict 4 (not a seam). A.U16.R03's silent-while-lost rule covers `_write()`/`_read()`/`clear()`;
  `invalidate()` is new and gets the same guard so the rule holds for every chunk entry (the erase then stops at pass 1,
  code 9; `erase_ready()` already refuses a lost chip, since a loss clears `initialized`).
- **Unit**: stages — U11: `_chunks` recording (M.SRC_CORE.091), `wait_idle()` and `quiesce()`, which S3 of every
  command needs from U11 on; U16: `invalidate()`, `erase_ready()`, `erase_chip()` (A.S0930.17's own State "U16 (FRAM
  manager erase)"), with the erase word's gate branch (M.SRC_CORE.011's U16 stage).
- **Depends**: M.SRC_CORE.082, .084, .091, M.SRC_CORE.103 (`report_set_values()`), M.SRC_CORE.102 (`lost`).
- **Blast carried by**: caller S3/S5 (M.SRC_CORE.011); tests → A.S0930.20 (non-zero-init CRC pin), .21-.29 (TSC,
  TEST_UNIT, TWIN, HW_DEV, HW_BENCH); twin chip's 1,024 writes → A.S0930.27 (TWIN); SPEC A.4/C.3.1/C.8 → A.S0930.30
  (SPEC); the erase's error-log read-and-archive before it → A.S0930.28/.29 (HW), CLAUDE.md FRAM rule (DOCS).
- **Kind**: code

### M.SRC_CORE.092 Manager setup and the chip-watch task
- **From**: A.U16.17, A.U16.R03 (4), A.U10.21, A.U2.09 (83 → 10), A.U30.19, G8/R61 via A.U10.46 (task coroutines return
  `None`).
- **Site**: `src/asy_fram_manager.py:730-737` `setup()`; new `get_task_starters()`, `get_timer_starters()`,
  `start_watch_chip()`, `watch_chip()`.
- **Change**: `setup(self) -> bool`: `await self.pr.setup()`; `try: await self.fram.setup()` / `except Exception as e:
  report_if_fatal(e)`, `await self.pr.err_s("FRAM Setup failed:", e, errno=_ERR_INIT)`, `return False`;
  `self.initialized = True`; `return True`. `get_task_starters(self) -> "list[TaskStarter]": return
  [self.start_watch_chip]` (whenever the manager exists, i.e. the TOML declares a chip); `get_timer_starters()` → `[]`;
  `start_watch_chip()` creates the task; `async def watch_chip(self) -> None`: `if not self.fram.initialized:` never up
  (`not self.initialized`) → `self.pr.err("FRAM chip declared but not set up - escalating")`, `return`; was up and lost →
  `if not await self.setup(): return`; `self.pr.one("FRAM chip answers again")`; then `await self.fram.lost.wait()`;
  `return`.
- **Resolved**: A.U16.17's `get_task_starters()` returns `[]` when initialised; A.U16.R03 (4) makes it always one
  starter (SUPP_recovery Conflicts 5: R03 extends it) — R03. Both write the task as returning `False`; the typed task
  lists are `Task[None]` (G8/R61, owner OR81; A.U10.46's `TaskStarter`; A.U15.43 makes the readers' tasks `None` for
  the same reason), and the supervisor counts any end — so the coroutine returns `None`. Gap pass G2: A.U16.R03's
  `_was_up` (set on the first successful `setup()`, never cleared) is exactly G5/R14's readiness flag, which every class
  with an async `setup()` carries (A.U10.22's L0 check, M.TSC.112; M_SRC_NET gap 3) — one attribute, named
  `initialized`, rather than two with one meaning (D.10); no method guards on it (AC_NOTES 42/44's form).
- **Unit**: U16 (A.U16.R03 is SUPP_recovery's U16 half).
- **Depends**: M.SRC_CORE.091, M.SRC_CORE.106 (driver `setup()`), M.SRC_CORE.102 (`lost`).
- **Blast carried by**: generated collectors include `fram` (`codegen.py:660-664`), `_collect_task_names()` gains
  `FRAM.start_watch_chip` → A.U16.17, A.U32.06 (GEN); task counts per device, inventory table → A.U16.R03, A.U10.19 (TSC,
  TEST_HELP, SPEC); `tests/_sensortask_scenarios.py:490-545` dead-chip scenario → A.U16.17 (TEST_HELP); L1 watch-task
  cases → A.U16.17, A.U16.R03 (TEST_UNIT); L2 silent chip → A.U16.R03/U25 (TWIN); L3 CS-hijack loss case → A.U16.R03
  (HW_DEV); SPEC A.4/A.7/C.7 → A.U16.17, A.U16.R03 (SPEC).
- **Kind**: code

### M.SRC_CORE.093 Member order and annotation form in `asy_fram_manager.py`
- **From**: A.U10.33, A.U10.31.
- **Site**: every class of the file.
- **Change**: D.15 order after every stage; annotations quoted only for `TYPE_CHECKING` names.
- **Resolved**: —
- **Unit**: U10 (then kept by each stage).
- **Depends**: —
- **Blast carried by**: A.U10.33 (TOOL baselines).
- **Kind**: code

## src/asy_fram_driver.py

End state: `FRAM_SPI` (name kept: a C.2 `<CHIP>_<Role>` compound) checks — never detects — the part `max_size` names,
retries a failed WREN and a failed identification, reports a partly protected status register, an unavailable bus and a
chip lost mid-run, takes both FRAM locks for every hold (`setup()` and `set_write_protected()` included), and bounds
`verify_present()`'s one wait with `wait_for_ms`.

### M.SRC_CORE.100 SPDX header, docstring and the file's fault summary
- **From**: A.U34.07 (header order), A.U20.10 (checks, not detects) applied to the docstring (adherence, see Resolved).
- **Site**: `src/asy_fram_driver.py:1-10`.
- **Change**: lines 1-3 → "# SPDX-FileCopyrightText: 2018 Michael Schroeder for Adafruit Industries" / "#
  SPDX-License-Identifier: MIT" / "# From adafruit_fram (CircuitPython), restructured for asyncio + MicroPython - see
  THIRD_PARTY_LICENSES.md.". Docstring line 1 "Async SPI driver for one Fujitsu FRAM chip (MB85RS64V 8KB or MB85RS2MTA
  256KB, the part max_size names, checked by RDID against _KNOWN_PRODUCT_IDS): raw byte-addressed
  get_values()/set_values() plus write protection."; line 2 "… RDID checking and the two-part table are this project's own
  addition, verified against …". Comment `:8-10` → "# CRC/dual-copy recovery lives one layer up in asy_fram_manager.py.
  This file detects a device-ID mismatch, a write-enable / # latch that did not set (retried once) or clear, a partly
  protected status register, an unavailable bus and / # a chip lost mid-run, never raising (except __init__()/setup()'s
  one-time setup errors)."
- **Resolved**: A.U20.10 corrects the `:36-38` comment to "checks … does not detect" (G5/R28 Req); the docstring's
  "RDID-detected"/"dual-chip detection" state the same wrong fact two lines higher — fixed with it (agent, 2026-10-01).
- **Unit**: U34 (header lines, with A.U34.07's L0 check); the docstring and summary comment land in U16 with the code they
  describe (stage).
- **Depends**: —
- **Blast carried by**: `tests_scripts/test_third_party_attribution.py` → A.U34.07 (TSC); K.9 → A.U34.07 (SPEC);
  `pyproject.toml` CPY001 reason → A.U28.32 (TOOL).
- **Kind**: code, doc

### M.SRC_CORE.101 Constants: opcode bytes folded, status bits and catalog names, the recovery tunables
- **From**: A.U16.21, A.U10.29, A.U20.10 (`:36-38`), A.U16.15 (`_SR_BP_MASK`), A.U10.26 + A.U8.13 (timeout),
  A.U16.R01 (`_W_WEL_RETRIED`), A.U13.09 (`_SV_BUS_DOWN`), A.U16.R02 (`_ID_ATTEMPTS`), A.U16.R03 (`_PROBE_AT`,
  `_SV_CHIP_LOST`), A.U2.04/A.U2.09 (names, bit comments), A.U16.20 (message), A.U35.42 (98 retired).
- **Site**: `src/asy_fram_driver.py:31-94`.
- **Change**: `:36-38` comment → "# … keyed by max_size: setup() checks that the wired chip is the part max_size implies;
  it does not detect the part." `_SPI_OPCODE_WREN/_WRDI/_RDSR/_RDID` (`:45-47, :51`) deleted; the `_CMD_*` comment →
  "# WREN 0x06, WRDI 0x04, RDSR 0x05, RDID 0x9F (datasheet p.6), as module-level bytes rather than a bytearray built on /
  # every call - each of those lands in the 32-96 byte size class the heap-layout model cares about / #
  (HEAP_FRAGMENTATION_MEASUREMENTS.md section M1)." (the citation kept: the section exists); each
  `_CMD_* = const(b"…")`. `_SR_BP_MASK = const(0x0C)  # BP1 | BP0: any set bit protects part or all of the array`.
  `_VERIFY_PRESENT_LOCK_TIMEOUT_MS = const(1000)` tagged `fram.verify_lock_timeout_ms = 1000`, comment "# Headroom over
  a real transaction's low-single-digit-ms cost, bounding an accidental lock re-entry to a finite wait." (the
  "Not test-monkeypatchable…" sentence goes: a test fact, and the test now drives fake time). `_ID_ATTEMPTS = const(3)`
  tagged `fram.setup_id_attempts = 3`; `_PROBE_AT = const(2)` tagged `fram.chip_probe_at = 2`. Status bits:
  `_W_PROTECTED  # wrnno 28`, `_W_WEL_NOT_SET  # wrnno 26`, `_W_WEL_STUCK  # wrnno 27 - advisory`, `_W_WP_MISMATCH  #
  errno 45`, `_SV_NOT_INIT  # errno 18`, `_SV_NOT_LOCKED  # errno 24`, `_SV_BAD_RANGE  # errno 21`, `_SV_BUS_DOWN =
  const(128)  # errno 52`, `_W_WEL_RETRIED = const(256)  # console only: a recovered transient`, `_SV_CHIP_LOST =
  const(512)  # errno 54`; the `:88-90` comment → "# The guards get_values()/set_values() share, in the same bit set so
  one status carries whatever the synchronous / # body decided; the two reporters below own every message." Error
  constants: `_ERR_NOT_INIT = const(18)`, `_ERR_LOCK_TIMEOUT = const(19)`, `_ERR_BAD_ARG = const(21)`, `_ERR_CONTRACT =
  const(24)`, `_ERR_FRAM_WP_MISMATCH = const(45)`, `_ERR_FRAM_BUS_DOWN = const(52)`, `_ERR_FRAM_WP_PARTIAL = const(53)`,
  `_ERR_FRAM_CHIP_LOST = const(54)`, `_WRN_FRAM_WEL_NOT_SET = const(26)`, `_WRN_FRAM_WEL_STUCK = const(27)`,
  `_WRN_FRAM_WRITE_PROTECTED = const(28)`, `_WRN_FRAM_ID_RETRIED = const(29)`.
- **Resolved**: errno 98 (ID-check failure) retires with A.U35.42; A.U2.09 folds get/set's distinct numbers into one
  per condition (the "grouped by the raising method" comment `:320-321` goes with it).
- **Unit**: U16 (stages: U2 numbers; U8 the timeout's tag; U10 `const()` bytes and `wait_for_ms` constant; U13 bus-down
  bit).
- **Depends**: —
- **Blast carried by**: `tests/test_asy_fram_wire_trace.py:35` comment → A.U16.21 (TEST_UNIT); `tests_scripts/test_device_tomls.py`
  part-name check reads `_KNOWN_PRODUCT_IDS` → A.U20.10 (TSC); four device TOML comment lines → A.U20.10 (GEN); catalog
  rows 18/19/21/24/26-29/45/52-54 → A.U2.01 merge (GEN); Part N rows → A.U8.13, A.U16.R02, A.U16.R03 (SPEC); SPEC C.3.1
  → A.U20.10/A.U16.20 (SPEC).
- **Kind**: code

### M.SRC_CORE.102 Construction, the two locks and the loss state
- **From**: A.U10.18 (`asy_lock` → `session_lock`; explicit holds keep their reason), A.U16.10 (scratch comment),
  A.U16.16 (`wp`/`wp_pin` comment), A.U0.39 (`:130` tag), A.U16.R03 (1) (`_anomalies`, `lost`), A.U5.02 (the `logger`
  stays: the manager's reach-through, a product caller).
- **Site**: `src/asy_fram_driver.py:97-150`, `:217-220`, `:268-275`.
- **Change**: `__init__` as HEAD plus: a comment above `self._wp_pin =` "# Optional, and no generated code passes it:
  without it WP is assumed tied high. With WPEN=1 a low WP / # locks only the status register (MB85RS64V p.11); the
  array's protection is always BP1/BP0."; scratch comment → "# Pre-allocated scratch buffers, reused under the driver
  lock and the bus lock, which every path takes (C.8)."; `self._bus_lock = self._spidev.session_lock` (the SPI bus's lock
  after A.U10.18); `self._anomalies = 0`; `self.lost = asyncio.Event()`. `__aenter__`: comment's last clause → "(owner,
  2026-09-18; SPECIFICATION.md C.8)"; `await super().__aenter__()`; `try: await self._bus_lock.acquire()` / `except
  BaseException: self.session_lock.release(); raise` with "# explicit: this hold spans __aenter__/__aexit__, which async
  with cannot express". `_is_write_protected()` comment gains "with a pin, its level is read as the whole state because
  set_write_protected() always sets BP and the pin together"; `get_write_protected()` comment → "# Without a wp_pin this
  is the value setup() read from the chip (A.4); with one, the pin's level (see _is_write_protected())." and its guard
  `err_s(…, errno=_ERR_NOT_INIT)`; every `self.asy_lock.locked()` → `self.session_lock.locked()`.
- **Resolved**: A.U10.18 converts `set_write_protected()`/`setup()`'s explicit bus holds to `async with self._bus_lock:`;
  A.U16.10's `async with self:` (both locks) supersedes it at those lines (A.U16.10's Depends says so).
- **Unit**: U16 (stages U0 tag, U10 rename).
- **Depends**: M.SRC_CORE.033.
- **Blast carried by**: SPI driver's lock rename → A.U10.18 (SRC_SENS); tests (`test_asy_fram_driver.py` 5,
  `test_asy_spi_driver.py`, bus-hazard files) → A.U10.18 (TEST_UNIT); `tests/test_bus_hazard_multi_device.py:395-472`
  drive the real FRAM path → A.U35.20 (TEST_UNIT; A.U35.20 is test-only, its product lines read-only).
- **Kind**: code

### M.SRC_CORE.103 Write path: one WREN retry, chip-loss probe, bus-down status, one reporter
- **From**: A.U16.R01, A.U16.R03 (2), (5) partly (see Resolved), A.U13.09, A.U2.09, A.U10.05's check-before-step rule.
- **Site**: `src/asy_fram_driver.py:200-231` (`_enable_write()`, `_write()`), `:233-252` (`_set_write_protected()`),
  `:314-350` (`set_values_sync()`, `report_set_values()`).
- **Change**: `_enable_write() -> int`: WREN, RDSR → `_W_OK` if WEL set; else one more WREN, RDSR → `_W_WEL_RETRIED` if
  set, else `_W_WEL_NOT_SET`; comment gains "one retry, as _disable_write() retries WRDI" (block ≤ 3 lines). `_write()`:
  protected → `_W_PROTECTED`; `en = self._enable_write()`; `if en & _W_WEL_NOT_SET: return en`; send; `return en |
  (_W_OK if self._disable_write() else _W_WEL_STUCK)`; `_set_write_protected()` ORs `en` into its status the same way.
  `set_values_sync()`: not init → `_SV_NOT_INIT`; not locked → `_SV_NOT_LOCKED`; `not self._spidev.spi.available` →
  `_SV_BUS_DOWN`; bad range → `_SV_BAD_RANGE`; `status = self._write(…)`; if `status & (_W_WEL_NOT_SET | _W_WEL_STUCK)`:
  `if self._anomalies < _PROBE_AT: self._anomalies += 1`, and at `_PROBE_AT` one synchronous `_check_device_id()` — a
  match resets `_anomalies`, no match sets `self.initialized = False` and `status |= _SV_CHIP_LOST`; any other completed
  write resets `_anomalies`. `report_set_values()`: `_SV_CHIP_LOST` first → `err_s("FRAM chip stopped answering its
  identification - access stopped", errno=_ERR_FRAM_CHIP_LOST)`, `self.lost.set()`, `False`; then NOT_INIT (18),
  NOT_LOCKED (24), BUS_DOWN (52, "SPI bus not initialized"), BAD_RANGE (21), PROTECTED (w28), WEL_NOT_SET (w26) —
  each `False`; `_W_WEL_RETRIED` → `self.pr.evt("FRAM write enable latch set on the second WREN")`; WEL_STUCK (w27);
  `True`.
- **Resolved**: A.U16.R03 (2) writes `self._anomalies = min(self._anomalies + 1, _PROBE_AT)` — the step form OR105.a
  (3) forbids and A.U10.05's check fails on (`min(<expr> + <n>, <cap>)`) — rewritten check-before-step (AC_NOTES 17
  asks A-C to check every counter action for this). A.U16.R03 (5)'s "`report_*` pass `repeat=True` for NOT_INIT while
  `lost` is set" is dropped: A.U3.01 removes `repeat=` from the loggers, and M.SRC_CORE.082/.083/.085/.088's entry guards
  keep the chunk layer — the only caller that could reach the driver while lost — off it.
- **Unit**: U16 (stages U2 numbers; U13 bus-down bit and check; A.U16.R01/R03 are SUPP_recovery's U16 half).
- **Depends**: M.SRC_CORE.101, .102; A.U13.09's `SPI.available` property (SRC_SENS, `asy_spi_driver.py`).
- **Blast carried by**: `tests/_fram_chip_fake.py` `drop_next_wren` count, silent-chip switch → A.U16.R01, A.U16.R03
  (TEST_HELP); L1 driver tests (retry, loss probe, bus down) → A.U16.R01, A.U16.R03, A.U13.09 (TEST_UNIT); existing
  `drop_wren` tests keep w26 → A.U16.R01 (TEST_UNIT); L2 twin `wren` fault op, `silent` switch → A.U16.R01, A.U16.R03
  (TWIN); L3 CS-hijack cases → A.U16.R01, A.U16.R03 (HW_DEV); SPEC C.3.1/A.4 → A.U16.R01, A.U16.R03 (SPEC).
- **Kind**: code

### M.SRC_CORE.104 Read path: bus-down status and one reporter
- **From**: A.U13.09, A.U2.09.
- **Site**: `src/asy_fram_driver.py:280-312` (`get_values_sync()`, `report_get_values()`, `get_values()`).
- **Change**: `get_values_sync()`: not init, not locked, `_SV_BUS_DOWN` (after the lock check), bad range, read.
  `report_get_values()`: NOT_INIT → `_ERR_NOT_INIT`; NOT_LOCKED → `_ERR_CONTRACT` (its WP8 comment kept, ≤ 3 lines);
  BUS_DOWN → `err_s("SPI bus not initialized", errno=_ERR_FRAM_BUS_DOWN)`; BAD_RANGE → `_ERR_BAD_ARG`; else `True`.
- **Resolved**: —
- **Unit**: U16 (stages U2, U13).
- **Depends**: M.SRC_CORE.101.
- **Blast carried by**: new L1 "bus down → `False`, errno 52" → A.U13.09 (TEST_UNIT); SPEC C.3/C.7.1 → A.U13.09 (SPEC).
- **Kind**: code

### M.SRC_CORE.105 `set_write_protected()` takes both FRAM locks
- **From**: A.U16.10, A.U13.09, A.U16.R01, A.U2.09; A.U3.11 as narrowed (an error and a warning never both persisted
  for one occurrence in one function; A-C review fold).
- **Site**: `src/asy_fram_driver.py:357-379`.
- **Change**: not init → `_ERR_NOT_INIT`; `async with self:` → `status = _SV_BUS_DOWN if not
  self._spidev.spi.available else self._set_write_protected(value=value)`; `await asyncio.sleep(0)`; BUS_DOWN →
  `_ERR_FRAM_BUS_DOWN`, `False`; WEL_NOT_SET → `wrn_s(…, "write protection not changed.", wrnno=_WRN_FRAM_WEL_NOT_SET)`,
  `False`; RETRIED → evt; MISMATCH → `_ERR_FRAM_WP_MISMATCH`, `False`; STUCK → `_WRN_FRAM_WEL_STUCK`; evt; `True` —
  the mismatch is tested before the stuck latch, so one call persists the fault or the warning, never both (HEAD warns
  w27 and then errs 45 for the same call; owner, 2026-09-26).
  Comment `:358-360` → "# Takes both FRAM locks itself like setup(): never call it inside `async with fram:` (asyncio.Lock
  is not reentrant)."
- **Resolved**: —
- **Unit**: U16.
- **Depends**: M.SRC_CORE.102, .103.
- **Blast carried by**: device script `fram_write_protect_roundtrip.py:27, 63` (calls it outside the lock, holds);
  L1 exclusion case → A.U16.10 (TEST_UNIT); four-tier bus-hazard runs unchanged → A.U16.10 (TEST_UNIT, TWIN, HW_DEV,
  HW_BENCH); SPEC C.8 → A.U16.10 (SPEC); a stuck latch with a mismatched readback persists only the fault →
  M.TEST_UNIT.033; `set_write_protected()` leaves the fault-or-warning scan's allow-list → M.TSC.111.
- **Kind**: code

### M.SRC_CORE.106 `setup()`: both locks, identification retried, partial protection reported, bool contract
- **From**: A.U16.10, A.U13.09, A.U16.15, A.U16.R02, A.U16.R03 (3), A.U16.16 (WP pin init), A.U10.21, A.U10.45.
- **Site**: `src/asy_fram_driver.py:381-398`.
- **Change**: `async def setup(self) -> bool`: `await self._spidev.setup()`; `if not self._spidev.spi.available: raise
  OSError("SPI bus not initialized")`; `async with self:` up to `_ID_ATTEMPTS` `_check_device_id()` cycles, stopping at
  the first match (`attempt` kept); on a match `wp_bits = self._read_status() & _SR_WP_MASK`, `self._wp = bool(wp_bits &
  _SR_BP_MASK)` (comment "# WPEN/BP0/BP1 are nonvolatile: re-sync from the chip, not the constructor's wp="); `await
  asyncio.sleep(0)`; no match → `raise OSError("FRAM SPI device not found")`; `attempt > 1` → `wrn_s("FRAM answered its
  identification only on attempt", attempt, wrnno=_WRN_FRAM_ID_RETRIED)`; `wp_bits not in (_SR_WP_SET, _SR_WP_CLEAR)` →
  `err_s("FRAM status register partly write-protected:", hex(wp_bits), "- writes refused until set_write_protected()
  rewrites it", errno=_ERR_FRAM_WP_PARTIAL)`; WP pin → `self._wp_pin.init(self._wp_pin.OUT, value=not self._wp)  # level
  before direction: no glitch on WP`; `self.initialized = True`; `self._anomalies = 0`; `self.lost.clear()`; `self.pr.one(…)`;
  `return True`.
- **Resolved**: A.U10.21 keeps a protocol-layer setup's documented raise for a chip that fails identification and
  returns `True` otherwise — applied.
- **Unit**: U16 (stages U10 contract, U13 bus check).
- **Depends**: M.SRC_CORE.101, .102.
- **Blast carried by**: `FRAMManager.setup()` (M.SRC_CORE.092); `tests/machine.py`/twin `Pin.init(value=)` → A.U13.03
  (TEST_HELP, TWIN); L1 partial-protection and retry cases, setup-failure traces (three RDIDs) → A.U16.15, A.U16.R02
  (TEST_UNIT); twin `rdid_response` one-shot knob → A.U16.R02 (TWIN); dead-chip scenario sees three RDIDs → A.U16.R02
  (TEST_HELP); SPEC C.3.1 → A.U16.15, A.U16.R02 (SPEC).
- **Kind**: code

### M.SRC_CORE.107 `verify_present()`: `wait_for_ms` on the one wait; the unreachable ID-error branch goes
- **From**: A.U10.26, A.U10.18, A.U13.09, A.U35.42 (2), A.U16.R03 (6), A.U2.09.
- **Site**: `src/asy_fram_driver.py:400-432`.
- **Change**: not init → `_ERR_NOT_INIT`; `try: await asyncio.wait_for_ms(self.session_lock.acquire(),
  _VERIFY_PRESENT_LOCK_TIMEOUT_MS)` (reason on the line: "# explicit: a bounded wait on the acquire") / `except
  asyncio.TimeoutError:` `err_s(…, errno=_ERR_LOCK_TIMEOUT)`, `False`; `try:` bus down → `err_s("SPI bus not initialized",
  errno=_ERR_FRAM_BUS_DOWN)`, `False`; `async with self._bus_lock: present = self._check_device_id()`; `await
  asyncio.sleep(0)`; `if not present: self.initialized = False; self.lost.set()`; `finally: self.session_lock.release()`;
  `return present`. The `id_error` capture and its errno-98 entry go.
- **Resolved**: A.U35.42 (2) "follows A.U16.R03 if it changes `verify_present()`'s shape" — R03 adds only `lost.set()`,
  so the removal applies unchanged.
- **Unit**: U16 (stages U10 `wait_for_ms`/renames, U13 bus check; U35's removal pulled into U16's rewrite).
- **Depends**: M.SRC_CORE.101, .102.
- **Blast carried by**: L1 lock-busy (fake time) → A.U10.26 (TEST_UNIT); SPEC F.2 mechanism, BACKLOG `:58-67` removed →
  A.U10.26 (SPEC, DOCS); SPEC E.5.1 row → A.U35.41 (SPEC).
- **Kind**: code

### M.SRC_CORE.108 FRAM CS at power-on is a documented fact: no code, no hardware row
- **From**: A.U13.04 (AC_NOTES 11: documented fact, no board change).
- **Site**: none (`src/asy_fram_driver.py:110` stays).
- **Change**: none: the datasheets' power-on hold time is met by boot timing and the CS pad state during reset is a
  datasheet fact stated in SPEC C.3.1 by M.SPEC.049 (AC_NOTES 11, 23; the lead's note at the end of `U13.md`); no
  phase-C measurement, no BACKLOG row.
- **Resolved**: AC_NOTES 11 (U13 Open point 1 withdrawn; the power-on hold time is met by boot timing).
- **Unit**: — (no step)
- **Depends**: —
- **Blast carried by**: SPEC C.3.1 → M.SPEC.049 (1).
- **Kind**: rule

### M.SRC_CORE.109 Comment labels in the driver: no undefined plan labels, current numbers
- **From**: A.U36.544 (2) (the four "WP8:" prefixes); adherence: `:153` "(PLAN A.1.2)" is an undefined temporary-plan
  label the same rule removes (G9/R12 "permanent text never cites a temporary plan … by section or number"; A.U36.544's
  list names "PLAN B.1.x" and says "every … label", this one is missing from its grep); the WP8 comments cite HEAD's
  numbers (`wrnno=60/70/80`) that A.U2.09 retires.
- **Site**: `src/asy_fram_driver.py:151-153`, `:224-226`, `:299-301`, `:320-321`, `:340-342`.
- **Change**: `:153` "… Scheduling points live in the public coroutines below (PLAN A.1.2)." → "… Scheduling points
  live in the public coroutines below."; `:224-226` → "# Persisted by the caller, like the manager's "communication
  paused" refusal (W25): a refused-but-expected / # write against a deliberately gated chip."; `:299-301` → "# An
  internal-contract violation (a caller not holding the lock Lockable requires), not a hardware / # fault - a real code
  defect if it ever fires, so an errno, unlike the expected refusals elsewhere."; `:320-321` → "# Same internal-contract
  violation as get_values_sync() above."; `:340-342` → "# Persisted: a refused-but-expected write against a deliberately
  gated chip, like the manager's paused / # refusal (W25), not a hardware fault."
- **Resolved**: —
- **Unit**: U16 (the file's unit; A.U36.544's four prefixes pulled from U36 into the rewrite of the same lines).
- **Depends**: M.SRC_CORE.101.
- **Blast carried by**: `tests/test_asy_fram_driver.py:1034`, `tests/test_system_service.py:1370` "WP8:" prefixes →
  A.U36.544 (TEST_UNIT); `tests_scripts/test_comment_block_cap.py` holds.
- **Kind**: doc

## src/crc_checks.py (→ `src/asy_crc_checks.py`)

End state: `CRCBase` keeps its whole state private (`_num_bytes`, `_all_set`, `_msb_set`, `_crc_shift`, `_poly`, `_fmt`,
`_inc_crc`, `_inc_count`); every public method settles pass mode (`_poly is None`) itself and hands the checked polynomial
to `_crc(buf, crc, poly)`, which runs widths up to 16 bits in one word and wider ones in `_crc_wide()` as two 16-bit
words (no heap int per bit on rp2); `add_into()`/`check_from()` validate bounds before the pass-mode return, in both
modes alike; the two unreachable guards are gone; `CRCPass`, `CRC8`, `CRC16`, `CRC32` unchanged in width and bytes.

### M.SRC_CORE.115 Module and class names; the whole state private; D.15 order
- **From**: A.U10.37 (module → `asy_crc_checks`), A.U10.38 (`CRC_Base` → `CRCBase`, `CRC_Pass` → `CRCPass`), A.U10.35
  (`num_bytes`, `all_set`, `poly`, `inc_crc` → `_`-prefixed), adherence (G10/R07 "private by default": `msb_set`,
  `crc_shift`, `fmt`, `inc_count` have no reader outside the class — grep of `src/ tests/ digital_twin/ tests_hardware/
  buildgen/`: none — so they go private with the rest; the same treatment M_SRC_SENS gives no-reader attributes),
  A.U10.33 (D.15 order).
- **Site**: `src/crc_checks.py:1-2` (docstring names), `:16-27` (`__init__`), every `self.<attr>` use `:29-142`, `:145-162`
  (the four subclasses).
- **Change**: file `git mv` to `src/asy_crc_checks.py`; docstring line 2 "… plus CRCPass (a zero-length no-op)."; class
  `CRCBase`; `CRCPass(CRCBase)`, `CRC8(CRCBase)`, `CRC16(CRCBase)`, `CRC32(CRCBase)`; attributes `_num_bytes`, `_all_set`,
  `_msb_set`, `_crc_shift`, `_poly`, `_fmt`, `_inc_crc: int | None`, `_inc_count` at `:20-27` and at every use; the
  `:52-53` comment "(CRCPass, or any width constructed with poly=None)". Member order after every other edit of the
  class (D.15 as A.U10.32 rewrites it: dunders, private, public; alphabetical within a role; none of these methods is a
  starter, getter or setter): `__init__`, `_crc`, `_crc_wide` (lands in U12, M.SRC_CORE.116), `_validate_init`, `add`,
  `add_into`, `check`, `check_from`, `check_inc`, `length`, `run_inc`.
- **Resolved**: A.U10.35's site list is S09's "read only by tests" scan; the four attributes no one outside reads were
  outside that scan, not exempt from the rule it applies (agent, 2026-10-01; "Agent decisions" 12).
- **Unit**: U10 (all four constituents are U10's; A.U10.33 last in U10).
- **Depends**: —
- **Blast carried by**: every importer (`asy_fram_manager.py`, `asy_sgp40_driver.py`, `asy_scd30_driver.py`,
  `asy_uart_driver.py`, `buildgen/codegen.py`, tests) → A.U10.37 (SRC_NET, SRC_SENS, GEN, TEST_UNIT) and M.SRC_CORE.001
  (the rename in this cluster); `tests/test_crc_checks.py` attribute reads `:36, :42, :126, :132, :258, :282, :346-395,
  :576, :702, :725` → A.U10.35 (TEST_UNIT); the generated `from crc_checks import …` and `UART_CRC_MODES`'s class name
  `"CRC_Pass"` → GAP-G10; UART changelog line for the module rename → A.U10.37 (DOCS).
- **Kind**: code

### M.SRC_CORE.116 `_crc()` takes the checked polynomial; CRC32 runs in two small-int words
- **From**: A.U12.01 (`_crc_wide()`), A.U35.44 (`_crc()`'s `poly is None` return goes), A.U0.50 (the zero-padding comment
  tag at `:8`, co-lands per A.U12.01's Depends).
- **Site**: `src/crc_checks.py:8`, `:35-49` (`_crc()`), the four callers `:63`, `:80`, `:94`, `:119`/`:140`.
- **Change**: `:8` "# Zero-padding limitation inherent to this CRC class (CRC linearity; agent, 2026-07-15):".
  `async def _crc(self, buf: bytearray | memoryview, crc: int, poly: int) -> int:` — comment "# Core polynomial-division
  loop (see the module docstring for the algorithm identity per / # width), over the polynomial the caller has already
  checked; yields after every byte so a large buffer / # can't stall other tasks." (3 lines); body: `if self._num_bytes > 2:
  return await self._crc_wide(buf, crc, poly)`, then HEAD's loop with `^ poly` for `^ self.poly`. New `async def
  _crc_wide(self, buf: bytearray | memoryview, crc: int, poly: int) -> int:` exactly as A.U12.01 writes it, with `poly_hi =
  poly >> 16`, `poly_lo = poly & 0xFFFF` and `self._num_bytes`; its comment above it: "# A register wider than 16 bits
  runs as two words: rp2 small ints stop at 2**30 - 1, so a 32-bit / # register would allocate a heap int on every bit step
  (agent, 2026-09-29)." Callers pass `self._poly` where they have just settled it is not `None`: `add()` `await
  self._crc(bytearr, init, self._poly)`, `check()` likewise, `run_inc()` inside its `if self._poly is not None:`,
  `add_into()`/`check_from()` after their pass-mode returns (M.SRC_CORE.117).
- **Resolved**: A.U12.01 "keeps its first two lines" against A.U35.44 "`_crc()`'s first two lines go" → removed
  (A.U35.44 is later and names A.U12.01's reorder as its premise). Neither text keeps the file type-clean: with the guard
  gone `(crc << 1) ^ self._poly` is `int ^ int | None` under `--strict`, and A.U12.01's own `_crc_wide()` reads
  `self.poly >> 16` with no narrowing in scope; an `assert` would need an S101 exemption in `src/`. Each caller already
  narrows `_poly`, so the polynomial becomes `_crc()`'s parameter: no unreachable branch, no ignore, one extra argument
  (agent, 2026-10-01; "Agent decisions" 11).
- **Unit**: U35 (latest constituent, A.U35.44); stages: U0 `:8` tag (A.U0.50), U12 `_crc_wide()` and the dispatch line
  with the `poly` parameter (A.U12.01 — the parameter lands here, since `_crc_wide()` needs it), U35 the guard goes.
- **Depends**: M.SRC_CORE.115 (names), M.SRC_CORE.117 (caller order).
- **Blast carried by**: `tests/test_crc_checks.py:36, :42` and A.U12.01's two new vector tests call `_crc()` directly and
  gain the polynomial argument (`0x31`, `0x1021`, `0x04C11DB7`) → GAP-G11; the phase C allocation measurement → A.U12.01 /
  A.C.03 (HW_DEV); SPEC I settled list and G.2 CRC entry → A.U12.01 / A.U12.10 (SPEC); SPEC E.5.1 loses the `_crc()` entry
  → A.U35.41 (SPEC); UART changelog Class B (A.U35.44's line) → A.U35.44 (DOCS).
- **Kind**: code, test

### M.SRC_CORE.117 `add_into()`/`check_from()`: bounds first in both modes; no unreachable `pack_into` catch
- **From**: A.U12.02 (pass mode validates bounds), A.U35.44 (both `try`/`except ValueError` wrappers go).
- **Site**: `src/crc_checks.py:56-69` (`add()`), `:108-124` (`add_into()`), `:126-142` (`check_from()`).
- **Change**: `add()`: `crc_b = bytearray(self._num_bytes)`; `pack_into(self._fmt, crc_b, 0, crc)`; `return bytearr +
  crc_b` (no `try`). `add_into()`: `if size <= 0 or start < 0 or start + size + self._num_bytes > len(buffer): return
  None`; `if self._poly is None: return size  # uninitialized or "pass" mode`; `init = self._validate_init(init)`; `if init
  is None: return None`; `mv = memoryview(buffer)[start : (start + size + self._num_bytes)]`; `crc = await
  self._crc(mv[0:size], init, self._poly)`; `pack_into(self._fmt, mv, size, crc)`; `return size + self._num_bytes`.
  `check_from()`: `size = len(buffer) if size is None else size`; `if size <= self._num_bytes or start < 0 or start + size
  > len(buffer): return None`; `if self._poly is None: return size`; init validation; `mv = memoryview(buffer)[start :
  start + size]`; `if await self._crc(mv, init, self._poly) == 0: return size - self._num_bytes`; `return None`. The
  header's "Every public method returns None/False on invalid input rather than raising, except add()/check(), which
  allocate and let MemoryError propagate" stays true unchanged.
- **Resolved**: A.U35.44's Depends names A.U12.02; the two compose line by line (reorder in U12, catch removal in U35).
- **Unit**: U35 (latest); stage U12 (the reorder, A.U12.02, landing with or after A.U12.03 in SRC_NET's
  `asy_uart_driver.py`).
- **Depends**: A.U12.03 (SRC_NET: zero-length payloads never reach the CRC), M.SRC_CORE.116.
- **Blast carried by**: `asy_uart_driver.py:181, :387, :449` (a zero-length or overrunning pass-mode size now `None`) →
  A.U12.03 (SRC_NET); `asy_fram_manager.py:277` unchanged (valid sizes); new pass-mode bound tests →
  A.U12.02 (TEST_UNIT); UART changelog Class B lines → A.U12.02 / A.U35.44 (DOCS); SPEC E.5.1 loses the `pack_into` entry →
  A.U35.41 (SPEC).
- **Kind**: code, test

## src/framing_codecs.py (→ `src/asy_framing_codecs.py`)

End state: `FramingBase` (identity codec) with `max_frame` public (read by `asy_uart_comm.py`'s codec-size check) and
`_run_length`/`_trailer` private, no test-only counter; `FramingPass`; `FramingCOBS` with one long-lived scratch, encode
input bounded by `max_frame` (`_checked()`), decode input by the encoded worst case of `max_frame` minus the delimiter
(`_checked_encoded()`); comments cite the permanent Parts only.

### M.SRC_CORE.120 Module and class names, private tunables, D.15 order
- **From**: A.U10.37 (module → `asy_framing_codecs`), A.U10.38 (`Framing_Base`/`Framing_Pass`/`Framing_COBS` →
  `FramingBase`/`FramingPass`/`FramingCOBS`), A.U10.29 (`COBS_DELIMITER` stays public: two test modules import it),
  adherence (G10/R07 "private by default": `run_length` and `trailer` have no reader outside the class; `max_frame` gains
  one in U17, M.SRC_CORE.122, so it stays public), A.U10.33 (D.15 order).
- **Site**: `src/framing_codecs.py:1-3` (docstring), `:18-29` (`Framing_Base`, its two comments), `:40-47`, `:68-79`
  (`Framing_Pass`, `Framing_COBS` and their comments).
- **Change**: file `git mv` to `src/asy_framing_codecs.py`; docstring "Pluggable frame codecs for asy_uart_driver.py:
  FramingPass (byte-identical no-op, the default) / and FramingCOBS (…)."; `:19-21` "… Mirrors asy_crc_checks.py's
  CRCBase/CRCPass split, so a caller / # can hold either family behind one dispatch table."; `:23` "# Parameterized like
  asy_crc_checks.py's CRCBase, so a subclass supplies constants rather than"; `:69-70` "… - the same reason
  asy_crc_checks.py spells out CRCPass."; `self._run_length`, `self._trailer` at `:27-28` and in `overhead()` `:42-44`.
  Member order after every other edit (D.15, A.U10.32): `FramingBase` — `__init__`, `_checked`, `is_delimited` (getter),
  then Others `decode_from`, `delimiter`, `encode_into`, `max_encoded`, `overhead`, `ready`; `FramingCOBS` — `__init__`,
  `_checked`, `_checked_encoded` (U17, M.SRC_CORE.122), `is_delimited`, `decode_from`, `delimiter`, `encode_into`,
  `ready`.
- **Resolved**: the comment renames follow the class and module renames they describe (A.U10.37/A.U10.38 rename
  "every reader"; three comments here read the old names); private tunables as M.SRC_CORE.115 (agent, 2026-10-01;
  "Agent decisions" 12).
- **Unit**: U10.
- **Depends**: M.SRC_CORE.115 (the class names these comments cite).
- **Blast carried by**: importers `asy_uart_driver.py`, `asy_uart_comm.py` (via the driver), `tests/test_framing_codecs.py`,
  `tests/test_asy_uart_driver.py`, `tests/test_asy_uart_comm.py` → A.U10.37 / A.U10.38 (SRC_NET, TEST_UNIT); UART changelog
  line "`framing_codecs`/`crc_checks` modules renamed" → A.U10.37 (DOCS).
- **Kind**: code

### M.SRC_CORE.121 The test-only `allocations` counter goes
- **From**: A.U12.16.
- **Site**: `src/framing_codecs.py:29`, `:85`.
- **Change**: both `self.allocations …` lines deleted; `FramingCOBS.__init__` reads "# One long-lived scratch, sized for
  the worst case from max_frame - never per frame." / `self._scratch: bytearray | None = None` / `if max_frame > 0:` /
  `try: self._scratch = bytearray(self.max_encoded(self.max_frame))` / `except (MemoryError, OverflowError): self._scratch
  = None` (the tuple already alphabetical, A.U10.45 has no site here).
- **Resolved**: —
- **Unit**: U12.
- **Depends**: —
- **Blast carried by**: `tests/test_framing_codecs.py:176, :187-195` → A.U12.16 / A.U12.17 (TEST_UNIT); UART changelog
  Class B → A.U12.16 (DOCS).
- **Kind**: code, test

### M.SRC_CORE.122 COBS decode is bounded by the encoded worst case of the frame
- **From**: A.U17.22 (the codec half; the `UART_Comm._validate_config()` half is SRC_NET's).
- **Site**: `src/framing_codecs.py:98-99` (`_checked()`), `:126-130` (`decode_from()`).
- **Change**: new `def _checked_encoded(self, buf: bytearray, size: int) -> bool:` directly after `_checked()`, with the
  comment "# decode input is the encoded frame without its delimiter - up to the run-code bytes longer than max_frame."
  and body `return self.ready() and 0 <= size <= len(buf) and size <= self.max_encoded(self.max_frame) - self._trailer`;
  `decode_from()` calls `self._checked_encoded(buf, size)`; `encode_into()` keeps `_checked()`.
- **Resolved**: A.U17.22 names HEAD's `self.trailer`; after M.SRC_CORE.120 it is `self._trailer` (same class). `max_frame`
  stays public for A.U17.22's `self.uart.framing.max_frame` read in `asy_uart_comm.py`.
- **Unit**: U17.
- **Depends**: M.SRC_CORE.120, M.SRC_CORE.121; A.U17.22's `asy_uart_comm.py` half and its new UART errno (SRC_NET).
- **Blast carried by**: `asy_uart_driver._read_delimited()` (unchanged call) and `UART_Comm._validate_config()`'s codec
  check with `_ERR_UART_CODEC_SIZE` → A.U17.22 (SRC_NET); L1 tests in `test_framing_codecs.py`, `test_asy_uart_driver.py`,
  `test_asy_uart_comm.py` → A.U17.22 (TEST_UNIT); SPEC J.3/G.2 sentence → A.U17.22 (SPEC); UART changelog Class B →
  A.U17.22 (DOCS).
- **Kind**: code, test

### M.SRC_CORE.123 Header comment: permanent pointers only
- **From**: A.U36.544 (4) (`:5` J.3 → G.2) and (3) (`:6` changelog label A11 → the fact with a Part J pointer).
- **Site**: `src/framing_codecs.py:4-6`.
- **Change**: "# Encode order on write is build -> CRC -> encode -> delimiter, the exact reverse on read, so the / # CRC
  keeps its position underneath the codec (SPECIFICATION.md Part G.2). Selecting a delimited / # codec changes the bytes on
  the wire and is a coordinated flag day with the C peer (Part J)." (3 lines).
- **Resolved**: —
- **Unit**: U36 (no earlier action rewrites these lines).
- **Depends**: A.U12.05 (SPEC J.3 gains the COBS fact the pointer leans on).
- **Blast carried by**: `tests_scripts/test_comment_block_cap.py` holds (3 lines); A.U0.08's citation check → A.U36.544
  (TSC).
- **Kind**: doc

## src/math_helpers.py (name kept: no `async def`, A.U10.47)

End state: ten pure functions in alphabetical order (`abs_humidity`, `cct_mccamy`, `chromaticity_xy`, `dew_point`,
`ema_step`, `pressure_at_height`, `rel_humidity`, `rgb_to_hsb`, `rgb_to_xyz`, `wet_bulb_temperature`); the humidity
conversions kept and gated, never clamped (OR140.a (4), A-C review fold); Stull's wet bulb
refused in the cold-dry corner the paper excludes; the CCT span stated with its measured error; residual-error catches
kept, written `(ArithmeticError, ValueError)`, and exercised by tests through a stand-in `math`.

### M.SRC_CORE.125 Docstring and the domain-constant block
- **From**: A.U12.09 (dropped: OR140.a (4), A-C review fold — the docstring and the four `_MAGNUS_*` constants stay),
  A.U12.06 (four corner constants), A.U12.07 (the CCT span comment).
- **Site**: `src/math_helpers.py:13-16`, `:41-42`.
- **Change**: the docstring keeps "humidity conversions" and `:27-30` (`_MAGNUS_*`) stay; after `_WB_RH_MAX` the four constants `_WB_CORNER_T0 = const(-20.0)`, `_WB_CORNER_RH0 = const(75.0)`,
  `_WB_CORNER_T1 = const(10.0)`, `_WB_CORNER_RH1 = const(5.0)`; `:41-42`'s trailing comments go and one
  line above `_CCT_MIN` reads "# Output span 2000-12500 K. On the Planckian locus the cubic is within 1 % up to 9000 K,
  -1.2 % at 10000 K, / # -3.5 % at 12500 K (Planck's law, CIE 1931 2-degree observer; agent, 2026-09-29)."
- **Resolved**: A.U12.07's text writes "2° observer"; the same unit's A.U12.06 keeps this file ASCII (`degC`, RUF003), so
  the comment spells "2-degree" (agent, 2026-10-01).
- **Unit**: U12.
- **Depends**: —
- **Blast carried by**: SPEC M.1.3 sentence → A.U12.07 (SPEC); G.2 derived-quantities entry → A.U12.10 (SPEC).
- **Kind**: code, doc

### M.SRC_CORE.126 Wet bulb refused in Stull's cold-dry corner
- **From**: A.U12.06.
- **Site**: `src/math_helpers.py:45-51` (`wet_bulb_temperature()`).
- **Change**: comment `:46-47` → "# Stull (2011) empirical wet bulb, valid at 101.325 kPa only: -20..50 degC / # and
  5..99 %RH, minus the cold-dry corner below the line (-20 degC, 75 %) to (10 degC, 5 %) (Fig. 3)."; after the rectangle
  gate `if humidity < _WB_CORNER_RH0 + (_WB_CORNER_RH1 - _WB_CORNER_RH0) * (temperature - _WB_CORNER_T0) / (_WB_CORNER_T1
  - _WB_CORNER_T0): return None` (a point on the line is accepted).
- **Resolved**: —
- **Unit**: U12.
- **Depends**: M.SRC_CORE.125.
- **Blast carried by**: `asy_scd30_driver.py:197` (`WetBulb` `None` in the corner, behaviour only) → A.U12.06 (SRC_SENS
  reads it; no edit); `tests/test_math_helpers.py:49-51` corrected expectation and new L1 cases → A.U12.06 (TEST_UNIT);
  release-note line → A.U12.06 / U37 (DOCS).
- **Kind**: code, test

### M.SRC_CORE.127 `altitude_baro()` becomes `pressure_at_height()`
- **From**: A.U12.08.
- **Site**: `src/math_helpers.py:86-89`.
- **Change**: `def pressure_at_height(p0: float | None, dh: float | None, tmean: float | None) -> float | None:`;
  comment "# Barometric formula: pressure at height offset dh above the p0 reference; a negative dh / # reduces a station
  reading to sea level. Range: BMP388/390 datasheet (its only caller)."; body unchanged but for the catch tuple
  (M.SRC_CORE.130). No alias.
- **Resolved**: —
- **Unit**: U12; the function then sits at its alphabetical slot between `ema_step` and `rel_humidity` (A.U10.33's U10
  reorder ran under the old name, so the rename moves it; the D.15 check of A.U10.47 would fail otherwise).
- **Depends**: M.SRC_CORE.130 (U10's order).
- **Blast carried by**: `src/asy_bmp3xx_driver.py:243` call → A.U12.08 / A.U15.23 (SRC_SENS, already written as
  `pressure_at_height`); `tests/test_math_helpers.py:139-201` → A.U12.08 (TEST_UNIT); `tests/test_asy_bmp3xx_driver.py:1388`
  comment → A.U12.08 (TEST_UNIT); SPEC `:2611` → A.U12.08 (SPEC).
- **Kind**: code, test, doc

### M.SRC_CORE.128 The humidity conversions stay, gated to their domain and never clamped
- **From**: A.U12.09 (dropped: OR140.a (4), A-C review fold); OR140.a (4) (keep both, align their tests with the other
  helpers', the no-clamp rule); G3/R06 ("`rel_humidity()`'s 0-100 clamp is aligned", the "ice-phase" comment corrected).
- **Site**: `src/math_helpers.py:101-137` (`abs_humidity()`, `rel_humidity()`).
- **Change**: both functions stay. `rel_humidity()`: the final `max(0.0, min(100.0, rh))` goes — a result outside
  `0.0 <= rh <= 100.0` returns `None` (the project's no-clamp rule: a derived value outside its source's domain is
  `None`, never clamped); its first comment line → "# Inverse of abs_humidity's Magnus-type formula; a result outside
  0-100 % is out of domain: None, never clamped." `abs_humidity()`'s comment "a/b pick the ice- vs water-phase
  constants" no longer calls the below-zero pair an ice-phase pair: it names the legacy formula's two Magnus constant
  pairs (at/above and below 0 degC) with their source, the exact wording and reference decided at execution with the
  source recorded. Inputs, gates and formulas unchanged; the catch tuple per M.SRC_CORE.130.
- **Resolved**: OR140.a (4) (owner, 2026-10-02: "useful, complete the functional suite, small, lightweight") reverses
  the removal (AC_NOTES 8, A.U12.09); G3/R06's other branch ("the clamp is aligned") applies instead. Tag form (rule 6,
  status change): the decision's permanent text, where SPEC G.2 writes it, carries "(owner, 2026-10-02)".
- **Unit**: U12.
- **Depends**: M.SRC_CORE.130 (catch form, U10); M.TEST_UNIT.271 (the humidity tests in
  `tests/test_math_helpers.py:204-299` kept and aligned with the other helpers' shape, vectors and edge cases — the
  out-of-range result now `None` — in U12).
- **Blast carried by**: `tests/test_math_helpers.py:204-299` → M.TEST_UNIT.271; A.U35.42's stand-in tests reach
  the two kept catches too (M.SRC_CORE.130); SPEC G.2 derived-quantities entry (the Magnus domain and the no-clamp
  sentence) → A.U12.10 with M.SPEC.111 (fold F08).
- **Kind**: code, test

### M.SRC_CORE.129 Colour chain: sRGB literal note as a fact, unquoted return annotations
- **From**: A.U0.51 (`:163-164`), A.U10.31 (the three quoted return annotations; none names a `TYPE_CHECKING` symbol).
- **Site**: `src/math_helpers.py:140`, `:162-164`, `:176`.
- **Change**: `-> tuple[float, float, float] | None` at `rgb_to_hsb()` and `rgb_to_xyz()`, `-> tuple[float, float] | None`
  at `chromaticity_xy()`; `:163-164` "… a second published rounding differs in the / # 6th decimal, and neither corrects
  the other (agent, 2026-09-12; Part M.1.3). No gamma decode - this sensor is" (the block stays 3 lines).
- **Resolved**: —
- **Unit**: U10 (A.U10.31); stage U0 (A.U0.51).
- **Depends**: —
- **Blast carried by**: `tests/test_math_helpers.py` `test_rgb_to_xyz_coefficients_are_the_pinned_literals()` unchanged;
  SPEC `:6717-6722` → A.U0.44 (SPEC).
- **Kind**: code, doc

### M.SRC_CORE.130 Residual catches: one tuple form, kept and exercised; function order
- **From**: A.U10.45 (tuples alphabetical), A.U35.42 (1) (tests reach every catch; the catches stay), A.U35.41 (its
  `math_helpers.py` row: keep), A.U35.36 (the never-raise map covers this module; no raising call outside a catch at
  HEAD), A.U10.33 (module-level functions in D.15 order, OR96.a (2)).
- **Site**: `src/math_helpers.py:60`, `:82`, `:97`, `:115`, `:135` (the humidity pair stays, OR140.a (4)).
- **Change**: `except (ArithmeticError, ValueError):` at every catch; U10 order of the module-level functions
  `abs_humidity`, `altitude_baro`, `cct_mccamy`, `chromaticity_xy`, `dew_point`, `ema_step`, `rel_humidity`, `rgb_to_hsb`,
  `rgb_to_xyz`, `wet_bulb_temperature`, which U12 (M.SRC_CORE.127) turns into the end-state order above (`pressure_at_height` between `ema_step` and
  `rel_humidity`).
- **Resolved**: A.U35.42 lists `:60, :82, :97, :115, :135` "after A.U12.09/A.U12.10 remove" the helpers; A.U12.09 is
  dropped (OR140.a (4), A-C review fold), so all five catches remain and the stand-in tests reach each.
- **Unit**: U10 (A.U10.45, A.U10.33); the stand-in tests land in U35 (A.U35.42).
- **Depends**: —
- **Blast carried by**: `tests/test_math_helpers.py` stand-in tests → A.U35.42 (TEST_UNIT); SPEC E.5.1 row → A.U35.41
  (SPEC).
- **Kind**: code, test

### M.SRC_CORE.131 Out-of-range polynomial degrades fully to pass-through
- **From**: — (lead, 2026-10-01: the adherence finding "flagged, not merged" below; no constituent action)
- **Site**: `src/crc_checks.py:17-26` `CRC_Base.__init__`
- **Change**: the constructor's own documented contract ("an invalid config … silently degrades to pass-through mode")
  holds for an out-of-range polynomial too: when the validated polynomial is `None` (absent, `num_bytes == 0`, or out
  of range for the width), `num_bytes`, `all_set`, `msb_set` and `crc_shift` are all 0, so `length()` reports 0 and
  `add_into()`'s bounds reserve no CRC byte. Compute the polynomial check against the width's mask first, then set the
  width fields from the result. No contract change: the constructor still never raises. Applies on top of
  M.SRC_CORE.115/.116's attribute renames and the polynomial-as-parameter shape.
- **Resolved**: lead ruling (AC_NOTES item 39) — the documented contract settles it; the agent's "constructor
  contract change" concern does not arise.
- **Unit**: U35 (the unit of M.SRC_CORE.116, the change it amends; A-C2).
- **Depends**: M.SRC_CORE.115, M.SRC_CORE.116
- **Blast carried by**: L1 `tests/test_crc_checks.py` gains one case per width (`poly` above the width's mask → `length() == 0`, `add()` returns the buffer unchanged, `add_into()` writes nothing) → TEST_UNIT gap; SPEC J/G CRC text unchanged (it states the contract already).
- **Kind**: code, test

## src/config_manager.py, src/print_log.py, src/asy_fram_driver.py (A-C3 Part S S-04)

### M.SRC_CORE.132 D.15 member order in the remaining classes
- **From**: A.U10.33 (A-C3 Part S: the classes below had no carrier).
- **Site**: `src/config_manager.py:215` `ConfigManager`; `src/print_log.py:68` `PrintLog`, `:133` `PrintLogHistory`,
  `:226` `PrintLogHistoryStore`; `src/asy_fram_driver.py:97` `FRAM_SPI` (HEAD names and lines; the U10 module and class
  renames of A.U10.37/A.U10.38 apply).
- **Change**: A.U10.33's script-driven pure move per class, after every other U10 edit to the same file; AST
  comparison (same (name, body) set, comment multiset unchanged); later stages insert at the D.15 position (A.U10.47).
- **Resolved**: —
- **Unit**: U10 (last U10 change per file).
- **Depends**: the file's other U10 changes.
- **Blast carried by**: lint/typecheck baselines → A.U10.33 (TOOL).
- **Kind**: code

## Gaps for other clusters

- **GAP-G1** (GEN): the generated `_collect_setups()` is annotated `list[SetupFct]` (imported from `asy_base_classes`),
  not `list[AsyncCallback]`, to match `run_setups()` (M.SRC_CORE.003/.015); A.U20.06's template text names the old alias.
- **GAP-G2** (GEN): `buildgen/error_catalog.json` (A.U2.01's table) gains shared errno **25 STACK_EXHAUSTED** "a C-stack
  overflow was recorded; rebooting" (M.SRC_CORE.005), and the JS/definitions mirror with it.
- **GAP-G3** (TEST_UNIT, TEST_HELP): tests using `get_debug_level()`, `set_debug_level()`, `stop_uptime_timer()` or
  `_current_debug_level` (`tests/test_system_service.py`, `tests/_sensortask_scenarios.py:692-747, 937-940`) are rebuilt
  through the `/system` settings PUT / `_set_dict_cfg()` (M.SRC_CORE.008/.017/.018).
- **GAP-G4** (TEST_UNIT): new L1 — an unpause request after `_reboot()` or after shutdown acceptance leaves storage
  paused (M.SRC_CORE.012).
- **GAP-G5** (TEST_UNIT, TEST_HELP, TWIN, HW_DEV): every direct `start_tasks()` caller passes `task_names` (required, no
  default; M.SRC_CORE.016).
- **GAP-G6** (TSC): A.U10.05's counter-step check must not flag `SensorReader._err_cnt_internal` (bounded by the
  give-up; M.SRC_CORE.037).
- **GAP-G7** (SRC_SENS, SPEC, DOCS): `SCD30_Reader` sets `_CFG_LOG_FRAM = False`; SPEC A.7's FRAM list and CLAUDE.md's
  FRAM-log bullet name `CFGMGR_SCD30` as the RAM-only exception (M.SRC_CORE.040).
- **GAP-G8** (SRC_NET, SRC_SENS, GEN, TSC, TEST_UNIT, SPEC): `report_if_fatal()`/`fatal_reported` live in
  `asy_print_log`, not `asy_base_classes`; every A.U30.19 import line and its L1 tests follow (M.SRC_CORE.034).
- **GAP-G9** (TSC, SPEC): the long-lived-object catalog (A.U30.02/.03) gains `FRAMManager._chunks` ("grows once per
  allocation at construction"; M.SRC_CORE.091).
- **GAP-G10** (GEN, TSC): after U10 the CRC module is `asy_crc_checks` and the pass class `CRCPass`. M.GEN.024's
  `UART_CRC_MODES = {"none": ("CRC_Pass", 0), …}` and its comment ("crc_checks class … src/crc_checks.py"), A.S0930.02's
  generated `from crc_checks import CRC16`, and A.S0930.01's `test_uart_crc_modes_match_crc_checks` (an `ast` read of
  `src/crc_checks.py`) still use the HEAD names; all land in U20 or later, so they must read `CRCPass` /
  `asy_crc_checks` / `src/asy_crc_checks.py` (M.SRC_CORE.115).
- **GAP-G11** (TEST_UNIT): `CRCBase._crc()` takes the polynomial as a third argument (M.SRC_CORE.116). Direct callers
  `tests/test_crc_checks.py:36, :42` and A.U12.01's two new vector tests pass it (`0x31`, `0x1021`, `0x04C11DB7`).
- **GAP-G13** (SRC_NET, GEN, SRC_SENS, TEST_UNIT, HW_DEV, SPEC): per the lead's ruling on M_SRC_SENS GAP-14,
  `asy_config_manager` gives typed callers per-kind validators — `checked_int()`, `checked_float()`, `checked_numeric()`
  (`None` = refused) — and `coerce_numeric()` becomes the private `_coerce_int()`/`_coerce_float()` (M.SRC_CORE.047).
  A.U11.S01 (5)'s runtime `type()` checks are not written anywhere: `_dispatch_notification_pause()` calls
  `checked_int(payload, _PAUSE_TIME_FIELD)` (SRC_NET); the emitted `_notification_led_callback()` calls `checked_int()`
  for R/G/B and `checked_float()` for T (GEN); `ISL29125_Reader._checked_cfg()` calls `checked_numeric()` and returns its
  value (SRC_SENS, replacing M.SRC_SENS.082's `type_or_range_error()` + annotated local); tests of `coerce_numeric()` and
  `tests_hardware/device_scripts/float_boundary_2pow24.py` call the private halves (TEST_UNIT, HW_DEV); A.U11.S01's SPEC
  C.10 sentence becomes "A consumer that needs an `int` or a `float` calls the per-kind validator, which returns that
  type or `None`; it never narrows a validated value at runtime." (SPEC).
- **GAP-G12** (SRC_NET; orchestrator check): this cluster and M_SRC_SENS make an attribute with no reader outside its
  class private ("private by default", G10/R07, beyond S09's test-reader list). SRC_NET's classes should get the same
  treatment so the rule holds across `src/` (M.SRC_CORE.115/.120; "Agent decisions" 12).

## Adherence findings

Rules read for every file: CLAUDE.md hard rules (watchdog backstop, memory ladder, FRAM error-log rule, no
`gc.collect()` outside the boot sites, `method-assign` never suppressed in `src/`, PEP 604 unions), the owner rows naming
each function (OR31/OR113/OR117/OR119/OR120/OR126/OR128/OR130 for the watchdog and erase design, OR36 test artifacts,
OR46 unreachable branches, OR105/AC_NOTES 17 counters, OR110 bounded permanent objects), the 3-line comment cap, actor
tags only (no audit IDs in permanent text), D.15 order, private by default.

- `system_service.py`: breaches found and fixed in the merge — the unpause waiter could unpause FRAM after `_reboot()`
  or during the erase (M.SRC_CORE.012); `timers_running` is write-only dead state (M.SRC_CORE.008); `stop_uptime_timer()`
  and `set_debug_level()` exist only for tests (OR36; M.SRC_CORE.018); `task_names=None` would be a test-only default
  (M.SRC_CORE.016). Watchdog design: exactly two `feed_watchdog()` calls in `_supervise()`, the escalation fed once then
  starved, no feed after `_reboot()`, `_own_feed()` the sequence's only feed — consistent with OR119/OR120/OR126.a(3)/
  OR130.a after the C-stack path joins the shared block (M.SRC_CORE.016, "Agent decisions" 6).
- `base_classes.py`: fatal-flag home would make an import cycle (M.SRC_CORE.034, "Agent decisions" 10); counters
  check-before-step (M.SRC_CORE.031/.037). No other breach.
- `config_manager.py`: A.U11.S01's never-firing `type()` tests (validator, `_get_typed_values()`, three consumers) are
  dead runtime code (lead L1 ruling) → per-kind validators and coercers (M.SRC_CORE.047/.048, GAP-G13); otherwise no
  breach beyond what the constituents fix; the superseded-write rule is shared with the log
  store (M.SRC_CORE.044 pointer).
- `print_log.py`: A.U14.19's `(x + 1) & CAP` step allocates a heap int at the wrap on rp2 → conditional wrap (AC_NOTES 17;
  M.SRC_CORE.064).
- `api_response.py`: the docstring's second line is history, not current state → removed (M.SRC_CORE.070).
- `asy_fram_manager.py`: no breach beyond the constituents; Erase FRAM (OR117) is fed in units and closes the chunk layer
  first (M.SRC_CORE.083); FRAM keeps its own log RAM-only (M.SRC_CORE.091).
- `asy_fram_driver.py`: the docstring says "detects" where the part is checked (M.SRC_CORE.100); A.U16.R03's
  `min(x + 1, cap)` step → check-before-step (M.SRC_CORE.103); "(PLAN A.1.2)" is an undefined plan label (M.SRC_CORE.109).
- `crc_checks.py`: removing `_crc()`'s guard (A.U35.44) and A.U12.01's `_crc_wide()` both leave `self.poly` typed
  `int | None` where it is used, which fails `mypy --strict` → the polynomial becomes a parameter (M.SRC_CORE.116,
  "Agent decisions" 11); four attributes public with no outside reader → private (M.SRC_CORE.115). **Flagged, not
  merged**: an out-of-range polynomial (e.g. `CRC8(poly=0x1FF)`) leaves `_num_bytes` at the width while `_poly` is
  `None`, so `length()` reports 1 in pass mode and `add_into()` bounds include a CRC byte it never writes. No action
  covers it, no product path builds such a CRC (every construction uses the class default), and a fix changes a
  constructor contract → settled by the lead as M.SRC_CORE.131 (the documented contract already says it degrades to pass-through).
- `framing_codecs.py`: `run_length`/`trailer` public with no outside reader → private (M.SRC_CORE.120); the header cited a
  changelog label and the wrong Part (M.SRC_CORE.123, A.U36.544). The comments naming `CRC_Base`/`CRC_Pass`/
  `crc_checks.py` follow the U10 renames (M.SRC_CORE.120).
- `math_helpers.py`: A.U12.07's "2°" breaks the file's ASCII spelling that A.U12.06 keeps for RUF003 → "2-degree"
  (M.SRC_CORE.125); A.U12.08's rename moves the function out of U10's alphabetical order → it moves to its slot
  (M.SRC_CORE.127). No other breach; every catch is the documented residual-error sentinel path (A.U35.41 keep).

## Owner questions

None. Every conflict between constituents was settled from an owner row, the register, AC_NOTES or SUPP's conflict
list; the agent choices are listed below for the OR2.c review.

## Agent decisions for the OR2.c review

1. `SetupFct = Callable[[], Awaitable[bool]]` in `asy_base_classes` for `run_setups()` and the generated
   `_collect_setups()`, since A.U11.S04's `AsyncCallback` cannot type A.U10.21's `bool`-returning `setup()`
   (M.SRC_CORE.003/.015).
2. `start_tasks(..., task_names)` is required, not A.U32.06's `None` default, under OR36.a (1) (M.SRC_CORE.016).
3. The C-stack log line takes shared errno 25 STACK_EXHAUSTED (SYSTEM's band 40-44 is full) (M.SRC_CORE.005).
4. `timers_running` goes (write-only after A.U10.12) (M.SRC_CORE.008).
5. The unpause waiter does nothing once `_reset_armed` or `_feed_owned` is set (M.SRC_CORE.012).
6. The C-stack escalation shares the task-budget block: re-check `_feed_owned`, one feed, starve, `_reboot()`, no
   return (M.SRC_CORE.016).
7. `stop_uptime_timer()` and `set_debug_level()` removed as test-only (OR36) (M.SRC_CORE.018).
8. `set_utc_valid()` takes no argument (M.SRC_CORE.032).
9. `SensorReaderConfig._CFG_LOG_FRAM` class attribute keeps `CFGMGR_SCD30` RAM-only without a ninth constructor
   parameter (M.SRC_CORE.040).
10. `report_if_fatal()`/`fatal_reported` live in `asy_print_log` (an import cycle rules out `asy_base_classes`)
    (M.SRC_CORE.034).
11. `CRCBase._crc()`/`_crc_wide()` take the already-checked polynomial as a parameter, so A.U35.44's guard removal and
    A.U12.01's wide path type-check without an `assert` or ignore (M.SRC_CORE.116).
12. Attributes with no reader outside their class go private with S09's list (`CRCBase` `_msb_set`, `_crc_shift`, `_fmt`,
    `_inc_count`; `FramingBase` `_run_length`, `_trailer`) (M.SRC_CORE.115/.120).

13. The type-level form the lead's L1/GAP-14 ruling asks for: per-kind `checked_int()`/`checked_float()`/
    `checked_numeric()` returning the kind or `None`, `type_or_range_error()` kept for schema-generic callers, private
    `_coerce_int()`/`_coerce_float()`, and `_get_typed_values()` taking a coercer (M.SRC_CORE.047/.048; GAP-G13).

Smaller agent choices recorded in place (actor-tagged in the entries): the `delete_file()` comment for the SCD30's NVM
(M.SRC_CORE.042), "checks" for "detects" in the FRAM driver docstring (M.SRC_CORE.100), the api_response header without
history (M.SRC_CORE.070), A.U36.535 (5)'s header rewrite pulled into U11 (M.SRC_CORE.002), "2-degree" in the CCT comment
(M.SRC_CORE.125).

Added by gap pass G2 (2026-10-01):

14. A REST value reaches the validators as `object` and `type_or_range_error()`'s refusal answers `(True, None)` — the
    type-level form U19 A-C note 2 needs once the implementers take `JsonMapping` (M.SRC_CORE.047).
15. G10/R07 applied to the leftovers of this cluster's classes: `_watchdog`, `_ntp_is_synced`, `_boot_signature`
    (M.SRC_CORE.008), `_max_module_error` (M.SRC_CORE.036), `_cfg_vals` (M.SRC_CORE.049), `_block_addr`,
    `_verify_counter` (M.SRC_CORE.081) — attributes with no reader outside the class (M_SRC_CORE GAP-G12's sweep, run on
    HEAD with an AST scan of `self.<public> =` and a text search of `src/` and `buildgen/`).
16. `FRAMManager`'s `_was_up` is held as `initialized` (G5/R14's flag; one attribute for one meaning, M.SRC_CORE.092).
17. `SensorReader` carries `initialized`, set in its `setup()`; its subclasses inherit it (M.SRC_CORE.036/.039) —
    withdrawn by the routine settlement "initialized-flags" (A-C review fold): no reader or `SystemService` flag.

## Ledger

Every action with a site in this cluster's files (`site_index.json` `by_file`, 146) plus the actions a grep found
editing them through a class or function name (site-miss), 171 in all.

| action ID | merged into M-ID / dropped (reason) |
|---|---|
| A.1.2 | M.SRC_CORE.109 |
| A.S0930.12 | M.SRC_CORE.008, M.SRC_CORE.011, M.SRC_CORE.012 |
| A.S0930.13 | M.SRC_CORE.009, M.SRC_CORE.013, M.SRC_CORE.016 |
| A.S0930.14 | M.SRC_CORE.010, M.SRC_CORE.011 |
| A.S0930.15 | M.SRC_CORE.006 |
| A.S0930.16 | M.SRC_CORE.041, M.SRC_CORE.042, M.SRC_CORE.044 |
| A.S0930.17 | M.SRC_CORE.080, M.SRC_CORE.083, M.SRC_CORE.091 |
| A.S0930.20 | M.SRC_CORE.009 |
| A.S0930.31 | M.SRC_CORE.002, M.SRC_CORE.010, M.SRC_CORE.011, M.SRC_CORE.016 |
| A.S0930.32 | M.SRC_CORE.011, M.SRC_CORE.016 |
| A.S0930.33 | M.SRC_CORE.004, M.SRC_CORE.010 |
| A.U0.14 | dropped (its site is BACKLOG; the `system_service.py` mention is a "no code change" Blast; DOCS) |
| A.U0.20 | M.SRC_CORE.002 |
| A.U0.39 | M.SRC_CORE.047, M.SRC_CORE.102 |
| A.U0.41 | M.SRC_CORE.008, M.SRC_CORE.013, M.SRC_CORE.091 |
| A.U0.42 | M.SRC_CORE.049 |
| A.U0.50 | M.SRC_CORE.116 |
| A.U0.51 | M.SRC_CORE.129 |
| A.U10.01 | M.SRC_CORE.003, M.SRC_CORE.008, M.SRC_CORE.013, M.SRC_CORE.031 |
| A.U10.02 | M.SRC_CORE.032 |
| A.U10.03 | M.SRC_CORE.003, M.SRC_CORE.013, M.SRC_CORE.032 |
| A.U10.05 | M.SRC_CORE.103 |
| A.U10.06 | M.SRC_CORE.003, M.SRC_CORE.005, M.SRC_CORE.013, M.SRC_CORE.032, M.SRC_CORE.080, M.SRC_CORE.087; A.U14.26 (1) ruling applied |
| A.U10.08 | M.SRC_CORE.009 |
| A.U10.10 | M.SRC_CORE.016, M.SRC_CORE.017, M.SRC_CORE.030, M.SRC_CORE.039, M.SRC_CORE.040 |
| A.U10.11 | M.SRC_CORE.063, M.SRC_CORE.065 |
| A.U10.12 | M.SRC_CORE.005, M.SRC_CORE.008, M.SRC_CORE.014, M.SRC_CORE.039 |
| A.U10.15 | M.SRC_CORE.008, M.SRC_CORE.010, M.SRC_CORE.012 |
| A.U10.17 | M.SRC_CORE.030, M.SRC_CORE.031, M.SRC_CORE.049, M.SRC_CORE.081 |
| A.U10.18 | M.SRC_CORE.031, M.SRC_CORE.033, M.SRC_CORE.036, M.SRC_CORE.049, M.SRC_CORE.102, M.SRC_CORE.107 |
| A.U10.19 | M.SRC_CORE.036; `:163-165` comment dropped (branch removed) |
| A.U10.20 | M.SRC_CORE.044 |
| A.U10.21 | M.SRC_CORE.015, M.SRC_CORE.017, M.SRC_CORE.039, M.SRC_CORE.040, M.SRC_CORE.043, M.SRC_CORE.063, M.SRC_CORE.065, M.SRC_CORE.092, M.SRC_CORE.106 |
| A.U10.23 | M.SRC_CORE.016 |
| A.U10.26 | M.SRC_CORE.101, M.SRC_CORE.107 |
| A.U10.29 | M.SRC_CORE.101, M.SRC_CORE.120 |
| A.U10.31 | M.SRC_CORE.003, M.SRC_CORE.020, M.SRC_CORE.029, M.SRC_CORE.030, M.SRC_CORE.049, M.SRC_CORE.071, M.SRC_CORE.093, M.SRC_CORE.129, M.SRC_CORE.060 (AC3_S S-03) |
| A.U10.33 | M.SRC_CORE.020, M.SRC_CORE.029, M.SRC_CORE.093, M.SRC_CORE.115, M.SRC_CORE.120, M.SRC_CORE.130, M.SRC_CORE.132 (AC3_S S-04) |
| A.U10.35 | M.SRC_CORE.008, M.SRC_CORE.010, M.SRC_CORE.012, M.SRC_CORE.013, M.SRC_CORE.014, M.SRC_CORE.027, M.SRC_CORE.031, M.SRC_CORE.049, M.SRC_CORE.063, M.SRC_CORE.087, M.SRC_CORE.089, M.SRC_CORE.091, M.SRC_CORE.115 |
| A.U10.36 | M.SRC_CORE.017 |
| A.U10.37 | M.SRC_CORE.001, M.SRC_CORE.003, M.SRC_CORE.030, M.SRC_CORE.049, M.SRC_CORE.060, M.SRC_CORE.070, M.SRC_CORE.080, M.SRC_CORE.115, M.SRC_CORE.120 |
| A.U10.38 | M.SRC_CORE.003, M.SRC_CORE.007, M.SRC_CORE.060, M.SRC_CORE.080, M.SRC_CORE.081, M.SRC_CORE.087, M.SRC_CORE.089, M.SRC_CORE.090, M.SRC_CORE.091, M.SRC_CORE.115, M.SRC_CORE.120 |
| A.U10.39 | M.SRC_CORE.003, M.SRC_CORE.007, M.SRC_CORE.008, M.SRC_CORE.017, M.SRC_CORE.040 |
| A.U10.45 | M.SRC_CORE.010, M.SRC_CORE.012, M.SRC_CORE.014, M.SRC_CORE.029, M.SRC_CORE.032, M.SRC_CORE.043, M.SRC_CORE.044, M.SRC_CORE.047, M.SRC_CORE.081, M.SRC_CORE.085, M.SRC_CORE.106, M.SRC_CORE.130 |
| A.U10.46 | M.SRC_CORE.003, M.SRC_CORE.008, M.SRC_CORE.011, M.SRC_CORE.014, M.SRC_CORE.016, M.SRC_CORE.019, M.SRC_CORE.030, M.SRC_CORE.092 |
| A.U10.R01 | M.SRC_CORE.036, M.SRC_CORE.037 |
| A.U11.01 | M.SRC_CORE.003, M.SRC_CORE.008, M.SRC_CORE.013 |
| A.U11.02 | M.SRC_CORE.013 |
| A.U11.03 | M.SRC_CORE.008, M.SRC_CORE.010, M.SRC_CORE.011, M.SRC_CORE.016, M.SRC_CORE.017; (4) dropped (superseded by A.S0930.31 (1)) |
| A.U11.04 | M.SRC_CORE.010, M.SRC_CORE.041, M.SRC_CORE.044, M.SRC_CORE.049 |
| A.U11.05 | M.SRC_CORE.002, M.SRC_CORE.003, M.SRC_CORE.006, M.SRC_CORE.008 |
| A.U11.06 | M.SRC_CORE.006 |
| A.U11.09 | M.SRC_CORE.064 |
| A.U11.10 | M.SRC_CORE.015 |
| A.U11.12 | M.SRC_CORE.008, M.SRC_CORE.017; (1)(3) dropped (A.U35.41 removes the accessors) |
| A.U11.13 | M.SRC_CORE.017, M.SRC_CORE.062 |
| A.U11.15 | M.SRC_CORE.007, M.SRC_CORE.066 |
| A.U11.16 | M.SRC_CORE.060, M.SRC_CORE.063, M.SRC_CORE.064, M.SRC_CORE.065 |
| A.U11.17 | M.SRC_CORE.047 |
| A.U11.19 | M.SRC_CORE.043 |
| A.U11.20 | M.SRC_CORE.043, M.SRC_CORE.044, M.SRC_CORE.049 |
| A.U11.21 | M.SRC_CORE.044, M.SRC_CORE.047 |
| A.U11.22 | M.SRC_CORE.044 |
| A.U11.23 | M.SRC_CORE.043, M.SRC_CORE.044 |
| A.U11.24 | M.SRC_CORE.017, M.SRC_CORE.040, M.SRC_CORE.044 |
| A.U11.25 | M.SRC_CORE.044 |
| A.U11.26 | M.SRC_CORE.070, M.SRC_CORE.072, M.SRC_CORE.073 |
| A.U11.27 | M.SRC_CORE.036, M.SRC_CORE.038 |
| A.U11.28 | M.SRC_CORE.038, M.SRC_CORE.040, M.SRC_CORE.041, M.SRC_CORE.044, M.SRC_CORE.049 |
| A.U11.29 | M.SRC_CORE.048 |
| A.U11.30 | M.SRC_CORE.047 |
| A.U11.31 | M.SRC_CORE.019, M.SRC_CORE.037, M.SRC_CORE.049, M.SRC_CORE.063, M.SRC_CORE.091 |
| A.U11.32 | M.SRC_CORE.003, M.SRC_CORE.008, M.SRC_CORE.040, M.SRC_CORE.046 |
| A.U11.S01 | M.SRC_CORE.047, M.SRC_CORE.048, M.SRC_CORE.049; (2)(3)(5) never-firing checks not written (lead L1 ruling, GAP-14 of M_SRC_SENS → per-kind validators, GAP-G13) |
| A.U11.S02 | M.SRC_CORE.003, M.SRC_CORE.030, M.SRC_CORE.036, M.SRC_CORE.038, M.SRC_CORE.040, M.SRC_CORE.071 |
| A.U11.S03 | M.SRC_CORE.060, M.SRC_CORE.062, M.SRC_CORE.063, M.SRC_CORE.064, M.SRC_CORE.090 |
| A.U11.S04 | M.SRC_CORE.003, M.SRC_CORE.015 |
| A.U12.01 | M.SRC_CORE.116; "keeps its first two lines" superseded (A.U35.44) |
| A.U12.02 | M.SRC_CORE.117 |
| A.U12.06 | M.SRC_CORE.125, M.SRC_CORE.126 |
| A.U12.07 | M.SRC_CORE.125 |
| A.U12.08 | M.SRC_CORE.127 |
| A.U12.09 | M.SRC_CORE.125, M.SRC_CORE.128 |
| A.U12.16 | M.SRC_CORE.121 |
| A.U13.04 | dropped as a measurement (withdrawn, AC_NOTES 11); its fact carried by M.SPEC.049 (M.SRC_CORE.108 records it, no step) |
| A.U13.09 | M.SRC_CORE.101, M.SRC_CORE.103, M.SRC_CORE.104, M.SRC_CORE.105, M.SRC_CORE.106, M.SRC_CORE.107 |
| A.U14.10 | M.SRC_CORE.063, M.SRC_CORE.085 |
| A.U14.15 | M.SRC_CORE.016 |
| A.U14.19 | M.SRC_CORE.044, M.SRC_CORE.060, M.SRC_CORE.064; `(x+1)&CAP` step replaced by the conditional wrap (AC_NOTES 17) |
| A.U14.26 | M.SRC_CORE.013, M.SRC_CORE.087; (1) dropped (V.U18.R10: no catch around the timestamp) |
| A.U15.12 | M.SRC_CORE.039 |
| A.U15.40 | M.SRC_CORE.033, M.SRC_CORE.039 |
| A.U15.41 | M.SRC_CORE.036, M.SRC_CORE.039 |
| A.U16.01 | M.SRC_CORE.080 |
| A.U16.05 | M.SRC_CORE.027, M.SRC_CORE.030, M.SRC_CORE.060, M.SRC_CORE.080, M.SRC_CORE.089 |
| A.U16.06 | M.SRC_CORE.060, M.SRC_CORE.065, M.SRC_CORE.081, M.SRC_CORE.084, M.SRC_CORE.085, M.SRC_CORE.088, M.SRC_CORE.090 |
| A.U16.08 | M.SRC_CORE.088 |
| A.U16.09 | M.SRC_CORE.084 |
| A.U16.10 | M.SRC_CORE.102, M.SRC_CORE.105, M.SRC_CORE.106 |
| A.U16.15 | M.SRC_CORE.101, M.SRC_CORE.106 |
| A.U16.16 | M.SRC_CORE.102, M.SRC_CORE.106 |
| A.U16.17 | M.SRC_CORE.092 |
| A.U16.18 | M.SRC_CORE.087 |
| A.U16.19 | M.SRC_CORE.060, M.SRC_CORE.082, M.SRC_CORE.085, M.SRC_CORE.087, M.SRC_CORE.088, M.SRC_CORE.090 |
| A.U16.20 | M.SRC_CORE.080, M.SRC_CORE.101 |
| A.U16.21 | M.SRC_CORE.101 |
| A.U16.22 | M.SRC_CORE.086 |
| A.U16.23 | M.SRC_CORE.089 |
| A.U16.R01 | M.SRC_CORE.101, M.SRC_CORE.103, M.SRC_CORE.105 |
| A.U16.R02 | M.SRC_CORE.101, M.SRC_CORE.106 |
| A.U16.R03 | M.SRC_CORE.080, M.SRC_CORE.082, M.SRC_CORE.083, M.SRC_CORE.085, M.SRC_CORE.088, M.SRC_CORE.091, M.SRC_CORE.092, M.SRC_CORE.101, M.SRC_CORE.102, M.SRC_CORE.103, M.SRC_CORE.106, M.SRC_CORE.107 |
| A.U16.S01 | M.SRC_CORE.080, M.SRC_CORE.087, M.SRC_CORE.091 |
| A.U17.22 | M.SRC_CORE.122 |
| A.U19.06 | M.SRC_CORE.071 |
| A.U19.12 | M.SRC_CORE.038 |
| A.U19.15 | M.SRC_CORE.073 |
| A.U19.16 | M.SRC_CORE.003, M.SRC_CORE.017, M.SRC_CORE.038, M.SRC_CORE.044, M.SRC_CORE.045, M.SRC_CORE.049, M.SRC_CORE.072 |
| A.U2.04 | M.SRC_CORE.005, M.SRC_CORE.049, M.SRC_CORE.072, M.SRC_CORE.080, M.SRC_CORE.101 |
| A.U2.05 | M.SRC_CORE.063 |
| A.U2.06 | M.SRC_CORE.037, M.SRC_CORE.038 |
| A.U2.07 | M.SRC_CORE.043, M.SRC_CORE.044, M.SRC_CORE.048, M.SRC_CORE.049; `:356` split superseded (A.U4.02, A.U35.43) |
| A.U2.08 | M.SRC_CORE.005, M.SRC_CORE.013, M.SRC_CORE.016, M.SRC_CORE.017 |
| A.U2.09 | M.SRC_CORE.080, M.SRC_CORE.082, M.SRC_CORE.084, M.SRC_CORE.085, M.SRC_CORE.087, M.SRC_CORE.088, M.SRC_CORE.090, M.SRC_CORE.092, M.SRC_CORE.101, M.SRC_CORE.103, M.SRC_CORE.104, M.SRC_CORE.105, M.SRC_CORE.107, M.SRC_CORE.109 |
| A.U2.18 | M.SRC_CORE.072 |
| A.U20.06 | M.SRC_CORE.008, M.SRC_CORE.015, M.SRC_CORE.016 |
| A.U20.10 | M.SRC_CORE.100, M.SRC_CORE.101 |
| A.U27.07 | M.SRC_CORE.071, M.SRC_CORE.073 |
| A.U28.30 | M.SRC_CORE.016 |
| A.U3.01 | M.SRC_CORE.060, M.SRC_CORE.063 |
| A.U3.02 | M.SRC_CORE.080, M.SRC_CORE.081, M.SRC_CORE.082, M.SRC_CORE.088 |
| A.U3.03 | M.SRC_CORE.037 |
| A.U3.04 | M.SRC_CORE.080, M.SRC_CORE.082, M.SRC_CORE.084, M.SRC_CORE.085, M.SRC_CORE.088 |
| A.U3.05 | M.SRC_CORE.048 |
| A.U3.06 | M.SRC_CORE.005, M.SRC_CORE.016 |
| A.U3.09 | M.SRC_CORE.080, M.SRC_CORE.087, M.SRC_CORE.090 |
| A.U30.08 | M.SRC_CORE.038 |
| A.U30.19 | M.SRC_CORE.003, M.SRC_CORE.005, M.SRC_CORE.006, M.SRC_CORE.010, M.SRC_CORE.013, M.SRC_CORE.014, M.SRC_CORE.016, M.SRC_CORE.017, M.SRC_CORE.034, M.SRC_CORE.037, M.SRC_CORE.038, M.SRC_CORE.060, M.SRC_CORE.072, M.SRC_CORE.085, M.SRC_CORE.087, M.SRC_CORE.092 |
| A.U31.07 | M.SRC_CORE.009, M.SRC_CORE.016 |
| A.U31.17 | M.SRC_CORE.016 |
| A.U32.03 | M.SRC_CORE.072 |
| A.U32.06 | M.SRC_CORE.008, M.SRC_CORE.016 |
| A.U34.07 | M.SRC_CORE.100 |
| A.U35.20 | no product change (test-only; `asy_fram_driver.py` lines read-only, carried as M.SRC_CORE.102 blast; TEST_UNIT) |
| A.U35.30 | no product change (test-only planted-fault scenarios; carried as M.SRC_CORE.009/.016 blast; TEST_HELP) |
| A.U35.35 | M.SRC_CORE.063; test only |
| A.U35.36 | M.SRC_CORE.130 |
| A.U35.41 | M.SRC_CORE.017, M.SRC_CORE.130 |
| A.U35.42 | M.SRC_CORE.101, M.SRC_CORE.107, M.SRC_CORE.130 |
| A.U35.43 | M.SRC_CORE.043, M.SRC_CORE.044, M.SRC_CORE.048 |
| A.U35.44 | M.SRC_CORE.116, M.SRC_CORE.117 |
| A.U35.45 | M.SRC_CORE.036 |
| A.U35.47 | M.SRC_CORE.087, M.SRC_CORE.090 |
| A.U35.55 | M.SRC_CORE.087 |
| A.U36.004 | M.SRC_CORE.043, M.SRC_CORE.049 |
| A.U36.514 | M.SRC_CORE.049 |
| A.U36.535 | M.SRC_CORE.002 |
| A.U36.544 | M.SRC_CORE.007, M.SRC_CORE.016, M.SRC_CORE.109, M.SRC_CORE.123 |
| A.U36.548 | M.SRC_CORE.016, M.SRC_CORE.070 |
| A.U4.01 | M.SRC_CORE.047 |
| A.U4.02 | M.SRC_CORE.044 |
| A.U4.03 | M.SRC_CORE.036, M.SRC_CORE.038 |
| A.U5.01 | M.SRC_CORE.003, M.SRC_CORE.030, M.SRC_CORE.061 |
| A.U5.02 | M.SRC_CORE.003, M.SRC_CORE.008, M.SRC_CORE.030, M.SRC_CORE.036, M.SRC_CORE.040, M.SRC_CORE.049, M.SRC_CORE.091, M.SRC_CORE.102 |
| A.U5.03 | M.SRC_CORE.007 |
| A.U5.08 | M.SRC_CORE.002, M.SRC_CORE.008, M.SRC_CORE.017 |
| A.U5.11 | M.SRC_CORE.035 |
| A.U5.13 | M.SRC_CORE.081, M.SRC_CORE.087, M.SRC_CORE.091 |
| A.U8.08 | M.SRC_CORE.004 |
| A.U8.12 | M.SRC_CORE.004, M.SRC_CORE.016, M.SRC_CORE.036 |
| A.U8.13 | M.SRC_CORE.101 |
| A.U8.23 | M.SRC_CORE.071 |

Read for blast or context, no site in this cluster (carried by the named cluster): A.U12.03, A.U10.27 (SRC_NET); A.U12.18,
A.U15.23 (SRC_SENS); A.S0930.01, A.S0930.02, A.U20.13 (GEN, see GAP-G10); A.U12.04, A.U12.17, A.U4.06, A.U16.13,
A.S0930.21 (TEST_UNIT); A.U11.07, A.U24.32 (TEST_HELP); A.U10.47 (TSC); A.U12.05, A.U12.10, A.U14.06, A.U14.35, A.U15.42,
A.U2.01, A.U5.18, A.U10.30, A.U15.43 (SPEC/GEN rule sources); A.S0930.07, A.U0.30 (DOCS); A.C.03 (HW_DEV).


Gap pass G2 rows (2026-10-01; `GAPS_G2.md` lists each item and its source):

| action ID / gap item | merged into M-ID / dropped (reason) |
|---|---|
| M_GEN gap 4 (A.U11.30's `:126-127` comment; U19 A-C note 5) | M.SRC_CORE.047 (amended: the comment goes with the public `coerce_numeric()`; the validators' comment names the webserver) |
| M_GEN gap 5 (`SystemService` API the template calls) | carried as found: M.SRC_CORE.006, .008, .011, .012, .015, .016 (run_setups discards results; FRAM's state reaches the supervisor through its watch starter, M.SRC_CORE.092) |
| M_SRC_NET gap 3, SRC_CORE half (`SensorReaderConfig`'s missing `initialized`) + A.U10.22 | M.SRC_CORE.008, .017 (SystemService), .036, .039, .040 (SensorReader, inherited), .091, .092 (FRAMManager: `_was_up` held as `initialized`) (amended) |
| M_SRC_NET gap 4 (U19 A-C note 2: `_set_dict_cfg(data: JsonMapping)` implementers) | M.SRC_CORE.017, .038, .040, .044, .047, .072 (amended) |
| M_SRC_NET gap 4 (`handle_set_cmd()`'s envelope; U19 A-C note 1) | M.SRC_CORE.070, .072 (amended: returns `WriteValidity`; lead L1 ruling) |
| M_SRC_NET gap 4 (names existing before their importers' stages) | carried as found: M.SRC_CORE.027 (U16), .030 (U10/U11), .031 (U10), .033 (U10 stage), .034 (U30), .061 (U5) |
| M_SRC_SENS GAP-8 (`_trigger_loop()`) | M.SRC_CORE.039 (amended) |
| M_SRC_SENS GAP-9 (`cfg_log` parameter) | dropped: M.SRC_CORE.040's `_CFG_LOG_FRAM` settles it (G10/R15 tail rule); M.SRC_SENS.052 amended to the attribute |
| M_SRC_SENS GAP-14 | carried as found: M.SRC_CORE.047 (AC_NOTES 38), extended to SGP40/BMP3XX consumers in this pass |
| M_SRC_SENS GAP-15 | carried as found: M.SRC_CORE.037 (`_error_check()` unchanged; AC_NOTES 38) |
| M_SRC_SENS GAP-17 | carried as found for SRC_CORE's part: no SRC_CORE class is exempt; readiness added above |
| M_SRC_CORE GAP-G12 applied across `src/` (attributes with no reader outside the class) | M.SRC_CORE.008 (`_watchdog`, `_ntp_is_synced`, `_boot_signature`), .009, .013, .036/.037 (`_max_module_error`), .044/.049 (`_cfg_vals`), .081 (`_block_addr`, `_verify_counter`) (amended) |
| M_HW_DEV GAP-D9 | carried as found: no SRC_CORE change lists the two WiFi repro scripts |
| AC_NOTES 39 | carried as found: M.SRC_CORE.131 |
| A.U10.22 | M.SRC_CORE.008, .017, .036, .039, .092 (readiness flag; this pass) |
| AC3_R R-03 | M.SRC_CORE.108 amended: title, Site "none", Change "none" (documented datasheet fact, M.SPEC.049), Unit "— (no step)", Kind rule, Blast → M.SPEC.049 (1); A.U13.04's row rewritten |
| AC3_S S-03 | M.SRC_CORE.060: From gains A.U10.31; Change appends the bare-annotation rule; Unit gains stage U10 (the one HEAD instance, `make_logger() -> "PrintLogHistory"` `:287`, is already bare from U5 by M.SRC_CORE.061, so the U10 stage confirms it) |
| AC3_S S-04 | new M.SRC_CORE.132 (U10), placed after the file's highest number under its own heading, Site naming all three files |
| AC3_O O-23 | M.SRC_CORE.013 (`:133` comment tag) and M.SRC_CORE.091 (both comment tags): "(owner-confirmed, 2026-07-18 …)" → "(owner, 2026-07-18 …)" |

## A-C2 order notes (2026-10-01)

Unit and Depends edits made by the A-C2 work order (`audit/order/WORK_ORDER.md`); one row per edit.

| M-ID | slot | edit | reason |
|---|---|---|---|
| M.SRC_CORE.002 | Unit | appended: A-C2 step order: A.S0930.31's part lands in U20, not U11 (it needs A.S0930.13, which lands in U20). | dependency deferral (an edge ran from a later step) |
| M.SRC_CORE.004 | Unit | appended: A-C2 step order: A.S0930.33's part lands in U20, not U11 (it needs A.S0930.31, which lands in U20). | dependency deferral (an edge ran from a later step) |
| M.SRC_CORE.009 | Unit | appended: A-C2 step order: A.S0930.13's part lands in U20, not U11 (it needs A.U20.06, which lands in U20). | dependency deferral (an edge ran from a later step) |
| M.SRC_CORE.010 | Unit | appended: A-C2 step order: A.S0930.14's part lands in U20, not U11 (it needs A.U20.06, which lands in U20); A.S0930.31's part lands in U20, not U11 (it needs A.S0930.13, which lands in U20); A.S0930.33's part lands in U20, not U11 (it needs A.S0930.31, which lands in U20). | dependency deferral (an edge ran from a later step) |
| M.SRC_CORE.011 | Unit | appended: A-C2 step order: A.S0930.12's part lands in U20, not U11 (it needs A.S0930.13, which lands in U20); A.S0930.14's part lands in U20, not U11 (it needs A.U20.06, which lands in U20); A.S0930.31's part lands in U20, not U11 (it needs A.S0930.13, which lands in U20); A.S0930.32's part lands in U20, not U11 (it needs A.S0930.13, which lands in U20). | dependency deferral (an edge ran from a later step) |
| M.SRC_CORE.012 | Unit | appended: A-C2 step order: A.S0930.12's part lands in U20, not U11 (it needs A.S0930.13, which lands in U20). | dependency deferral (an edge ran from a later step) |
| M.SRC_CORE.013 | Unit | appended: A-C2 step order: A.S0930.13's part lands in U20, not U11 (it needs A.U20.06, which lands in U20). | dependency deferral (an edge ran from a later step) |
| M.SRC_CORE.035 | Depends | `M.SRC_CORE.001 (renamed` → `M.SRC_CORE.001 [follows] (renamed` | its own text: the type lands in U5 and moves with the file in U10 |
| M.SRC_CORE.036 | Unit | appended: A-C2 step order: A.U10.R01's part lands in U13, not U10 (it needs A.U13.R01, which lands in U13). | dependency deferral (an edge ran from a later step) |
| M.SRC_CORE.037 | Unit | appended: A-C2 step order: A.U10.R01's part lands in U13, not U10 (it needs A.U13.R01, which lands in U13). | dependency deferral (an edge ran from a later step) |
| M.SRC_CORE.080 | Depends | `M.SRC_CORE.001, .027, .032, .034, M.SRC_CORE.115` → `M.SRC_CORE.001, .027, .032, M.SRC_CORE.115; M.SRC_CORE.034 [follows] (its U30 handler lines in this file come after)` | nothing in this change uses M.SRC_CORE.034 (U30) |
| M.SRC_CORE.131 | Unit | was: the unit of M.SRC_CORE.116 → now: U35 (the unit of M.SRC_CORE.116, the change it amends; A-C2). | no Unit slot: "the unit of M.SRC_CORE.116" |

## A-C review fold (2026-10-05)

Folded per `audit/actions/FOLD_BRIEF.md` (OR136-OR143, FOLD_ANSWERS, `routine_merge.json` `outcome`, AC_NOTES 52).
`[fold Fnn M_FILE]` tokens name a change another fold agent adds; the lead replaces them.

| Fnn | M-ID(s) | action |
|---|---|---|
| F01 | M.SRC_CORE.043, .042, .049 (and the section end state); .043 again for the lead ruling of 2026-10-05 (a missing or unknown key and a refused value are a repair; `faulted` only for a file unreadable or invalid as a whole) | amended |
| F02 | M.SRC_CORE.133 | added |
| F02 | M.SRC_CORE.030 | amended |
| F03 | M.SRC_CORE.043, .049, .015, .008, .042, .011 (.042/.011 per the lead ruling of 2026-10-05: a failed delete is logged and shows as reset reason 9 at the next boot, never an HTTP "Failed") | amended |
| F04 | — | none in this file |
| F05 | — | none in this file |
| F06 | — | none in this file |
| F07 | — | none in this file |
| F08 | M.SRC_CORE.128 (A.U12.09 dropped; rewritten as keep-and-gate), .125, .127, .130 | amended |
| F09 | — | none in this file |
| F10 | — | none in this file |
| F11 | M.SRC_CORE.037, .080, .082, .084, .085, .088, .087, .090, .016, .048 (A.U3.03/.04 dropped; A.U3.05/.09 own halves kept; A.U3.11 narrowed, lead ruling 2026-10-05: .105 tests the fault before the warning; .043 and .088 name their two-occurrence pairs) | amended |
| F12 | — | none in this file |
| F13 | — | none in this file |
| F14 | — | none in this file |
| F15 | M.SRC_CORE.011, .038, .040, .041 | amended |
| F16 | M.SRC_CORE.043 (Blast pointer: A.U35.38/.39 dropped) | amended |
| F17 | — | none in this file |
| F18 | — | none in this file |
| F19 | — | none in this file |
| F20 | — | none in this file |
| F21 | — | none in this file (no permanent text here carries one of the 68 decisions' tags) |
| F22 | — | none in this file |
| F23 | — | none in this file |
| F24 | — | none in this file |
| F25 | — | none in this file |
| F26 | — | none in this file |
| F27 | M.SRC_CORE.134 | added |
| F28 | M.SRC_CORE.036, .039, .040, .008, .017 ("Agent decisions" 17 withdrawn) | amended |
| F29 | — | none in this file |
| F30 | — | none in this file |
| F31 | — | none in this file |
| F32 | — | none in this file |
| F33 | — | none in this file (M.SRC_CORE.084/.088 already give `False` for both copies BUSY, as the corrected D-T27 line reads) |
