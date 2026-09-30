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
  `from typing import Protocol`; `from asy_base_classes import AsyncCallback, ErrorSource, NtpSyncFct, SetupFct,
  TaskStarter, TimerStarter`; `from asy_fram_manager import FRAMManager`; `from asy_config_manager import CfgValue,
  ConfigSchema, WriteValidity`; `from asy_print_log import ErrorLog, PrintLogHistory`; `_StoragePause` Protocol and its
  comment stay (the `_storage_pause` attribute keeps its keyword-only call). `Any`, `Coroutine` and the `LockedCounter`
  import go. Annotations are quoted only where they name a `TYPE_CHECKING` symbol (A.U10.31).
- **Resolved**: `SetupFct = Callable[[], Awaitable[bool]]` is new here: A.U11.S04 types `run_setups()` as
  `list[AsyncCallback]` (`Awaitable[None]`), but A.U10.21 makes every `setup()` return `bool`, and a `bool`-returning
  coroutine is not an `Awaitable[None]` to mypy; G8/R61's "one named alias per repeated callback shape" (owner,
  2026-09-28, OR81) settles the alias (two users: `run_setups()` and the generated `_collect_setups()`). The alias is
  declared in `asy_base_classes.py`'s block (M.SRC_CORE.030).
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
  A.U10.12 (`_sequencer_flag`), A.U10.15 (`_unpause_flag`), A.U0.41 (`:92` tag), A.U10.46 (types).
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
  `self._unpause_flag = asyncio.ThreadSafeFlag()`; `self.ntp_is_synced = asy_ntp_callback`; `self._start_time_set =
  False`; `self.boot_signature = LockedValue(init_value=None)` with `:92` → "# None until status_counter() resolves it
  (owner, 2026-07-18) - a later change to this value signals a reboot happened."; `self.watchdog = watchdog`;
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
  dict[str, str | int] | None = None`. Gone: `self.uptime` (`LockedCounter`), `self.timers_running`, `self.cfg_schema`,
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
  write-only attribute is dead state (G5/R54; OR36.a (1)), so it goes (agent, 2026-10-01; "Agent decisions" 4).
- **Unit**: stages — U5: `fram` → `storage`, `history_length`/`debug` → `log`, `level_setters` provider (A.U5.02,
  A.U5.08; A.U5.03's generated `log=`/`storage=` and A.U5.18's check need them); U10: `boot_signature` → `LockedValue`
  (must precede A.U10.01's cap in the same unit, K.03), the seven private names (A.U10.35), `_cfg_schema` (A.U10.39),
  `_sequencer_flag` (A.U10.12), `self._uptime` stays a `LockedCounter` until U11; U11: the final state above
  (`config_stores`, `reset_reason`, `TickSeconds`, gate/ownership/reset state, `_unpause_flag`, `_tasks`/`_task_starters`
  used by the U11 supervisor, M.SRC_CORE.016); U32: `_task_names`, `_last_task_end`.
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
- **Change**: `feed_watchdog()`: `if self.watchdog is not None and not self._force_watchdog_starve and not
  self._feed_owned: self.watchdog.feed()`; comment (3 lines) "# Every feed site but the shutdown sequence's goes through
  here (SPECIFICATION.md Part G.2); once a system command / # is accepted the sequence alone feeds (owner, 2026-09-30),
  so this is a no-op from then on; the starve flag / # stops it one-way too." `_own_feed()`: `if self.watchdog is not
  None and not self._force_watchdog_starve: self.watchdog.feed()`, comment "# The shutdown sequence's own feed, once per
  bounded step; a hung step is never fed."
- **Resolved**: OR31.a (3) "one runtime feed site, the supervisor loop" vs OR120 (feeds move to the sequence while it
  runs) and OR130 (a second, escalation feed call inside the supervisor): the most recent owner decisions win (OR120
  2026-09-30, OR130 2026-09-30); SUPP conflict 8 and OR130.a state the pinned set: `feed_watchdog()`'s body, the
  supervisor's two calls (pass end, escalation), `run_setups()`'s per-unit call, `_own_feed()`'s body, and `_own_feed()`'s
  callers (the sequence and `_reboot(..., fed=True)`).
- **Unit**: U11.
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
  (1)); A.U10.46 (types).
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
  self.pr.err("Could not start the shutdown:", e)`, `self._shutdown = 0`, `return False`; (6) `self._feed_owned = True`;
  `self.pr.evt("System command accepted, controlled shutdown for", _purpose_name(purpose))`; `return True`.
  `_shutdown_sequence(purpose) -> None` (comment ≤ 3 lines: "# One controlled shutdown for a system command (owner,
  2026-09-30): no step has a timeout that moves on - / # a hung step is not fed, so the watchdog resets the unit; the
  order is explained in SPECIFICATION.md Part A.8."): S1 `self._own_feed()`; `task = self._supervisor_task`; `if task is
  None or not task.done():` `await self._supervisor_parked.wait()`, `task = self._supervisor_task`, `task.cancel()`,
  `try: await task` / `except asyncio.CancelledError: pass`; `if task is None or not task.done(): return` (no feed
  follows); `self.pr.evt("Shutdown: supervisor stopped, the watchdog is fed by the shutdown alone")`; `self._own_feed()`.
  S2 `ok = await self._flush_config_stores(close=True, step_done=self._own_feed)`; one `evt` line. S3
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
- **Unit**: U11 (gate, sequence, all four words; the REST words reach it in U19/U20 through A.S0930.09/A.S0930.11). The
  sequence's S1 needs the supervisor to run as its own task — it does from U11 on (M.SRC_CORE.016's U11 stage spawns
  `_supervise()` inside `start_and_check_tasks()`; U20 only splits the start loop out), which is how this lands before
  A.U20.06 although A.S0930.13 names `supervise_tasks()`.
- **Depends**: M.SRC_CORE.006, .008, .009, .010, .016 (U11 stage); M.SRC_CORE.041/.042 (`close_writes()`,
  `delete_file()`); M.SRC_CORE.083 (`quiesce()`, `erase_ready()`, `erase_chip()`).
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
  NTP → `await self.boot_signature.set_value(utc)`, one line, `_start_time_set = True`; `elif uptime >= _NTP_WAIT_TIME:`
  random (comment `:390-391` kept). `_ntp_boot_signature()`: comment `:133` → "# None if not synced yet - a failing NTP
  callback counts as not synced (owner-confirmed, 2026-07-18); / # the caller falls back to random after _NTP_WAIT_TIME.";
  the callback `try`/`except Exception as e:` keeps its guard (`report_if_fatal(e)` first from U30; `errno=_ERR_CALLBACK`);
  `if not synced: return None`; `return utc_now()` — no `try`, the errno-2 handler goes.
- **Resolved**: A.U10.06 (no `try` around the timestamp) vs A.U14.26 (1) (`except MemoryError` with a heap-int comment):
  ruled for A.U10.06 by V.U18.R10 / U18 register fix 10 (the one reachable failure is a fixed small allocation, not
  caught; CLAUDE.md memory rule, SPEC I.4(a)); a `MemoryError` there ends the uptime task and the supervisor restarts it,
  which A.U11.02 makes harmless (uptime and signature survive the restart). A.U14.26's `tests/test_system_service.py:278-300`
  rename then has no site: those tests go with A.U10.06.
- **Unit**: U11 (A.U10.03's starter, A.U10.06's site and A.U10.01's `LockedValue` are U10 stages — each is a prerequisite
  of U10's own checks: `arm_tick_timer()`'s L1, the `utc_now()` catalog retirement, the cap; U11 writes the rest).
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
  `ThreadSafeFlag` import gone → A.U10.12 (GEN); `SensorReader.get_trigger_starters()` → M.SRC_CORE.031; drivers' starter
  split → A.U10.12 (SRC_SENS); `tests/test_system_service.py:479-615` → A.U10.12 (TEST_UNIT); `tests/_sensortask_scenarios.py:347-368,
  774-841` fakes → A.U10.12 (TEST_HELP); `tests/_boot_contiguity_probe.py`, `heap_layout_after_full_boot_sequence.py`,
  twin callers (`test_digital_twin_bus_hazard_concurrency.py:118, 387`, `test_digital_twin_sensortask_integration.py:455`)
  → A.U10.12 (TEST_HELP, HW_DEV, TWIN); real-sequencer proof → A.U10.13/A.U11.39 (TEST_HELP, TSC); SPEC A.7/C.9 → A.U10.14
  (SPEC).
- **Kind**: code

### M.SRC_CORE.015 The boot setup list runs in one method
- **From**: A.U11.10, A.U11.S04 (typed, no `Any`), A.U10.21 (setups return `bool`), A.U20.06 (4) (the caller).
- **Site**: `src/system_service.py` new `run_setups()` beside `start_timers()`.
- **Change**: `async def run_setups(self, setups: "list[SetupFct]") -> None`: `gc.collect()`; `for setup in setups:
  await setup()`, `self.feed_watchdog()`, `gc.collect()`. Comments moved from the generator, two lines at most: "# fed
  after every one-time setup(), never inside a loop, so the batch cannot starve the watchdog however many modules a /
  # device wires; the collect comes after the feed - it is the slow part (the boot placement reset, SPECIFICATION.md
  Part I.4(f.1))." No guard around a setup (every `setup()` is never-raise; one that raises ends the boot, attributed by
  the phase marker); results are discarded (A.U16.17 reads FRAM's state through `fram.initialized`, not this return).
- **Resolved**: `AsyncCallback` (A.U11.S04) vs `setup() -> bool` (A.U10.21) → `SetupFct` (M.SRC_CORE.003 Resolved).
- **Unit**: U20 (co-lands with the generator's `_collect_setups()` and the guard changes in one commit, A.U11.10 Depends).
- **Depends**: M.SRC_CORE.009, M.SRC_CORE.030.
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
  only so a test … can reach inside") — it is a required parameter; direct callers pass names (GAP-G5).
- **Unit**: stages, each a prerequisite of work in its own or an earlier-numbered consumer —
  **U2/U3**: named codes at HEAD sites and one entry per task end (A.U2.02's catalog check, A.U3.11's pair scan need
  them). **U11** (the body above except `start_tasks()`/`supervise_tasks()`, C-stack and names): `start_and_check_tasks(
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
  "# the nested {name: {field: value}} shape every SettingsGroup module returns (Part C.6)."). `_set_dict_cfg(data,
  cfg_vals)` (the SettingsGroup call shape; `cfg_vals` unused, the store validates against its own schema): `persisted,
  results = await self.cfgmgr.write_config(data)`; `if not persisted: return dict.fromkeys(data, FAILED)`; `if
  results.get(name_cfg(_VAL_DEBUG_LEVEL)) in (VALID, UNCHANGED):` re-read and `_apply_level()`; comment `:311-313` kept
  minus "every logger's live level stays" wording about `_current_debug_level`. `_apply_level(value)`: per setter `try:
  setter(value)` / `except Exception as e: report_if_fatal(e)`; `await self.pr.err_s("Level setter failed:", e,
  errno=_ERR_CALLBACK)`. Gone: `set_level_setters()` (A.U5.08), `get_debug_level()` and `_current_debug_level` (A.U35.41),
  `set_debug_level()` (M.SRC_CORE.018).
- **Resolved**: A.U11.12 (1)(3) vs A.U35.41 (removal) → removal (the later G5/R54 verdict; A.U11.12 conditions itself on
  it). A.U11.12 (2) uses `self.cfgmgr.writable` (A.U11.20's flag, M.SRC_CORE.043).
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
(`LockedCounter`/`LockedFlag`/`LockedValue`) under `COUNTER_CAP`, the primitives `TickSeconds`, `arm_tick_timer()`,
`utc_now()`/`set_utc_valid()`, `ValueRef`, the typing aliases, and
`SensorReader` (logger, sample, error streak with the recovery ladder, trigger divider, timer-fault path, the whole
config GET/PUT orchestration under one per-module lock) with `SensorReaderConfig` adding the file store.

### M.SRC_CORE.030 Header, top comment, imports and the shared typing aliases
- **From**: A.U10.17 (header scalars), A.U16.05 (header buffers), A.U10.46 and A.U11.S02 (alias block, `Any` gone),
  A.U10.31 (quoting), A.U10.10 (the `:5-7` comment's premise), A.U5.01/A.U5.02, A.U10.37; `SetupFct` (M.SRC_CORE.003
  Resolved).
- **Site**: `src/base_classes.py:1-28`.
- **Change**: docstring line 1 "Shared base classes and primitives: the session lock (Lockable, DeviceSession), region
  buffers (RegionBuffer), shared scalars (LockedCounter, LockedFlag, LockedValue: no method awaits, so no lock), elapsed
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
  `RegionBuffer` with their classes.
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
- **Blast carried by**: `asy_fram_driver.py` users of `asy_lock` → M.SRC_CORE.103; `asy_i2c_driver.py`,
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
- **Depends**: M.SRC_CORE.001 (renamed file only if U5 < U10: it is not — the type lands in `base_classes.py` in U5 and
  moves with the file in U10).
- **Blast carried by**: SGP40/notification users and codegen `ValueRef(<src>, "<field>")` → A.U5.11 (SRC_SENS, GEN);
  tests → A.U5.11 (TEST_UNIT, TSC); SPEC C.14.2/C.14.3/L.6.3 → A.U5.11 (SPEC).
- **Kind**: code

### M.SRC_CORE.036 `SensorReader` constructor: fixed tail, one logger path, the module's fixed-size state
- **From**: A.U5.02, A.U35.45 (`logger=` goes), A.U10.19 (`:163-165` comment — dropped: its branch is removed),
  A.U10.18 (`_datalock` → `_data_lock`), A.U4.03 (callback dicts move here), A.U11.27 (`_set_lock`), A.U10.R01 (ladder
  state), A.U15.41 (`_timer_error`), A.U8.12 (`module.max_error` default tag), A.U11.S02 (types).
- **Site**: `src/base_classes.py:151-176`.
- **Change**: `def __init__(self, init_data: "NamedTuple", name: str, max_module_error: int = 5, name_ext: str = "", log:
  LogConfig = DEFAULT_LOG) -> None` (the default `5` tagged `module.max_error`); `resolved_name = instance_name(name,
  name_ext)`; `self.pr = make_logger(log, resolved_name)`; `self.name = resolved_name` (comment `:171-172` kept, now
  true on the one path); `self._datastruct = init_data`; `self._data_lock = asyncio.Lock()` ("# guards the last sample
  across a reader's read and a GET"); `self.max_module_error = max_module_error`; `self._err_cnt_internal = 0`;
  `self._set_lock = asyncio.Lock()` ("# serialises one module's config GET and PUT (Part C.5.2)"); `self._push_callbacks:
  dict[str, PushFct] = {}` and `self._get_callbacks: dict[str, Callable[[], Awaitable[CfgValue]]] = {}` with their
  `:283-287` comments; `self._rungs = 0`, `self._bus_mark = 0`, `self._recovery_bus: "I2C | None" = None`;
  `self._timer_error: Exception | None = None`. Every attribute is fixed-size (OR110.a).
- **Resolved**: A.U5.02 keeps `logger=None` at the tail; A.U35.45 removes it (its Depends names A.U5.02/A.U5.18/A.U10.19
  for A-C) — removed; the tail probe's `logger` allow-list loses `SensorReader` (A.U5.18).
- **Unit**: U11 (stages: U5 signature and `make_logger(log, …)`; U4 the two dicts moved; U10 `_data_lock`, ladder state
  (A.U10.R01 is SUPP_recovery's U10 half); U15 `_timer_error`; U35's removal is pulled to U11, the unit owning the file —
  A.U35.45 is a B3 cleanup with no prerequisite, and removing it with the constructor rewrite avoids a third edit).
- **Depends**: M.SRC_CORE.030, .061.
- **Blast carried by**: subclass constructors (`super().__init__(…, max_module_error=…)` by keyword; NTP/NOTIFY pass 0)
  → A.U5.02 (SRC_SENS, SRC_NET); `tests/test_base_classes.py` 49 positional calls, `:450-470` `logger=` tests →
  A.U5.02, A.U35.45 (TEST_UNIT); `tests/test_api_response.py:190`, `tests/test_fram_integration.py` → A.U5.02
  (TEST_UNIT); A.U5.18's probe allow-list → A.U5.18 (TSC); Part N `module.max_error` sites → A.U8.12 (SPEC).
- **Kind**: code

### M.SRC_CORE.037 The error streak climbs one recovery ladder; one entry per failed cycle
- **From**: A.U2.06, A.U3.03, A.U10.R01 (1)-(6), A.U11.31 (`reset_error_counter() -> bool`), A.U30.19 (handler).
- **Site**: `src/base_classes.py:218-230` `_error_check()`, `:243-248` `reset_error_counter()`; new `_recover_device()`,
  `_climb_ladder()`, `_recover_bus()`, `_init_failed()`, `_init_done()`; module constants.
- **Change**: constants `_ERR_GIVE_UP = const(2)` … `_ERR_RECOVERY_WRITE_RAISED = const(9)`, `_ERR_CALLBACK =
  const(14)`, `_ERR_TIMER = const(17)`, `_WRN_CALLBACK_KEYS = const(1)`, `_WRN_CFG_KEYS = const(2)`,
  `_WRN_DEVICE_RECOVERY = const(14)`, `_WRN_BUS_RECOVERY = const(15)`; `_RECOVER_DEVICE_AT = const(2)`,
  `_RECOVER_BUS_AT = const(3)`, `_RECOVER_CONTROLLER_AT = const(4)` with their `@tunable` tags and the one comment line
  of A.U10.R01 (1); `_RUNG_DEVICE/_RUNG_BUS/_RUNG_CONTROLLER = const(1/2/4)`. `_error_check()`: on a failure (`any(res is
  None …) and condition`): if the streak is 0 and `_recovery_bus` is set, `self._bus_mark =
  self._recovery_bus.recoveries`; `self._err_cnt_internal += 1`; `self.pr.err("Error counter increased to", n)`
  (console, A.U3.03); `if n > self.max_module_error: await self.pr.err_s("Maximum error count reached!",
  errno=_ERR_GIVE_UP); return False`; else `await self._climb_ladder()`; on a non-failure pass the HEAD decrement, then
  `if self._err_cnt_internal == 0: self._rungs = 0`. The ladder methods, their logging (one warning per rung that ran,
  none for a failed participant rung beyond the hook's own error, a raising hook → one `_ERR_CALLBACK` entry after
  `report_if_fatal(e)`), the per-bus episode check and `_init_failed()`/`_init_done()` exactly as A.U10.R01 (3)-(5).
  `reset_error_counter() -> bool`: `self._err_cnt_internal = 0`; `self._rungs = 0`; `return await self.pr.reset()`.
- **Resolved**: A.U3.03's console `pr.err()` for the streak and A.U10.R01's ladder climb sit in the same branch; the
  give-up test stays first (A.U10.R01 (4)).
- **Unit**: U10 (A.U10.R01's U10 half; stages U2 names, U3 console streak line; U11 `-> bool`; U30 `report_if_fatal`).
- **Depends**: M.SRC_CORE.036; A.U13.R01 (`I2C.clear()`, `recover()`, `recoveries`, `take_boot_clear_status()`,
  SRC_SENS) lands before or with it.
- **Blast carried by**: drivers' `_recover_device()` overrides and `_init_failed()`/`_init_done()` calls →
  A.U15.R01-R04, A.U18.R01 (SRC_SENS, SRC_NET); catalog wrnno 14/15 → A.U2.01 merge (GEN); driver/integration tests
  re-derived → A.U10.R01 blast (TEST_UNIT); new L1 ladder cases → A.U10.R01 (TEST_UNIT); `tests/test_base_classes.py:474-739`
  streak pins → A.U3.03 (TEST_UNIT); Part N rows and relation → A.U10.R01/A.U8.02 (SPEC); SPEC C.4/C.7/G.2/F.2 →
  A.U10.R01, A.U3.03 (SPEC); `tests_scripts/test_counter_steps.py` must not flag `_err_cnt_internal` (bounded by the
  give-up, pass-4 K.36) → GAP-G6 (TSC).
- **Kind**: code

### M.SRC_CORE.038 Config GET and PUT orchestration on `SensorReader`, one per-module lock
- **From**: A.U4.03, A.U11.27, A.U11.28 (`_commit_mgr_cfg()` in a `finally`), A.U19.12, A.U30.08, A.U2.06, A.U19.16,
  A.U11.S02, A.U30.19.
- **Site**: `src/base_classes.py:182-212` (`_get_mgr_cfg()`, `_get_dict_cfg()`), `:251-256`, `:290-397` (moved from
  `SensorReaderConfig`).
- **Change**: on `SensorReader`: `_get_mgr_cfg()` default `{}`; new default `_set_mgr_cfg(data, cfg_vals) -> tuple[bool,
  WriteValidity]` returning `(False, {})`; new default `_commit_mgr_cfg(self) -> None` (no-op). `_get_dict_cfg(name,
  cfg_vals, callback: "Callable[[], Awaitable[dict[str, CfgValue]]] | None" = None)`: its whole body under `async with
  self._set_lock:`; wrnno/errno by name (`_WRN_CFG_KEYS`, `_ERR_CFG_GET_RAISED`, `_WRN_CALLBACK_KEYS`,
  `_ERR_CFG_CALLBACK_RAISED`). `_set_dict_cfg(data, cfg_vals) -> WriteValidity`: whole body under `async with
  self._set_lock:`; `fields = schema_dict(cfg_vals)` once; the snapshot keys are those persisted (`check_cfg_get_default
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
  `report_if_fatal`). A.U30.08 is pulled forward into U11's rewrite of the same lines (no prerequisite; one edit).
- **Depends**: M.SRC_CORE.036, M.SRC_CORE.044 (`write_config(data, defer=…)`, `commit()`), M.SRC_CORE.045 (constants).
- **Blast carried by**: SCD30 chip store overrides (`_set_mgr_cfg`/`_get_mgr_cfg`, `_commit_mgr_cfg()` no-op) → A.U4.04,
  A.U15.12 (SRC_SENS); `api_response.handle_set_cmd()` → M.SRC_CORE.072; webserver `_put_sensors()`/`_get_sensors()` →
  A.U11.27/A.U19.12 (SRC_NET); tests `tests/test_base_classes.py:1128-1617` → A.U4.03, A.U11.27, A.U11.28 (TEST_UNIT);
  `tests/test_asy_webserver_service.py:1108-1137` consistency test → A.U19.12 (TEST_UNIT); L2 twin consistency scenario
  → A.U19.12 (TWIN); SPEC C.4.3/C.5.2/C.5.2.2/A.8 `:627-631` → A.U4.03, A.U11.27, A.U11.28, A.U19.12 (SPEC).
- **Kind**: code

### M.SRC_CORE.039 Reader lifecycle helpers: setup, trigger starters, divider, timer fault, republish
- **From**: A.U10.10, A.U10.21, A.U10.12 (`get_trigger_starters()`), A.U15.40 (2) (`_divide_trigger()`), A.U15.41
  (`_timer_failed()`, `_timer_fault()`), A.U15.12 (`_republish()`).
- **Site**: `src/base_classes.py` `SensorReader` new methods.
- **Change**: `async def setup(self) -> bool: await self.pr.setup(); return True` ("True = ready; a logger that could not
  reach its store has logged it and runs in RAM"). `def get_trigger_starters(self) -> "list[TimerStarter]": return []`.
  `async def _divide_trigger(self) -> None` — the byte-identical body of the two `_base_trigger()` copies (count
  `base_trigger_event` ticks, set `read_event` every `await self.trigger_period.get_value()`), extended by A.U15.41: it
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
- **Unit**: U15 (latest: A.U15.12/.40/.41; stages U10: `setup()` and `get_trigger_starters()` — A.U10.10's boot batch
  and A.U10.12's trigger plan need them in U10).
- **Depends**: M.SRC_CORE.036, M.SRC_CORE.037 (`_ERR_TIMER`).
- **Blast carried by**: BMP3XX/ISL29125 drop their `_base_trigger()` copies and call `_divide_trigger()`; drivers'
  `start_timer()` arm failures call `_timer_failed()`; SCD30/SGP40 check `_timer_fault()`; SCD30 calls `_republish(
  _FIELDS, …)` → A.U15.40, A.U15.41, A.U15.12 (SRC_SENS); codegen `needs_setup` for a `SensorReader` subclass →
  A.U10.10 (GEN); L1 `_divide_trigger()` cases, timer-fault tests → A.U15.40, A.U15.41 (TEST_UNIT); logger
  `initialized` after the batch → A.U10.10 (TEST_HELP); SPEC C.9/C.13/G.2 → A.U10.14, A.U10.21, A.U15.40 (SPEC).
- **Kind**: code

### M.SRC_CORE.040 `SensorReaderConfig`: the file store over the base orchestration
- **From**: A.U5.02, A.U11.32, A.U10.39 (`_cfg_schema`), A.U11.24 + A.U11.28 (`write_config(data, defer=True)`,
  `_commit_mgr_cfg()`), A.U10.10/A.U10.21 (`setup()`), A.U11.S02 (types); AC_NOTES 13 (the `CFGMGR_SCD30` logger stays
  RAM-only) — no action writes its mechanism (see Resolved).
- **Site**: `src/base_classes.py:259-414`.
- **Change**: `__init__(self, init_data, name, default_vals, max_module_error: int = 5, name_ext: str = "", cfg_path:
  str = "", log: LogConfig = DEFAULT_LOG)` → `super().__init__(init_data, name, max_module_error=max_module_error,
  name_ext=name_ext, log=log)`; `self._cfg_schema = default_vals`; comment `:274-276` kept; `self.cfgmgr =
  ConfigManager(config_filename(cfg_path, self.name), default_vals, self.name, log=log if self._CFG_LOG_FRAM else
  LogConfig(None, log.history_length, log.debug))`; class attribute `_CFG_LOG_FRAM = True` with "# False where the
  owner keeps a module's config store off FRAM (SCD30, owner, 2026-09-29: 'no extra FRAM chunk')". `_get_mgr_cfg()`
  unchanged; `_set_mgr_cfg(data, cfg_vals)` → `return await self.cfgmgr.write_config(data, defer=True)`;
  `_commit_mgr_cfg()` → `self.cfgmgr.commit()`; `get_error_sources() -> "list[ErrorSource]"`; `get_loggers()`;
  `get_cfg_schema()` → `self._cfg_schema` (its "stays a public attribute" comment goes); `async def setup(self) -> bool:
  await super().setup(); await self.cfgmgr.setup(); return self.cfgmgr.valid`.
- **Resolved**: AC_NOTES 13 / the U15 lead note (OR99 "No flash writes, no extra FRAM chunk") keep `CFGMGR_SCD30`
  RAM-only while SCD30's own logger stays FRAM-wired; A.U15.12 makes `SCD30_Reader` a `SensorReaderConfig`, whose
  constructor passes one `log` to both loggers. A class attribute read at construction is the least change that keeps
  the tail rule (no ninth, non-tail parameter) and needs no generated wiring (agent, 2026-10-01; "Agent decisions" 9);
  `SCD30_Reader` sets `_CFG_LOG_FRAM = False` (GAP-G7, SRC_SENS merges A.U15.12).
- **Unit**: U15 (A.U15.12 needs the attribute; stages U5 signature/`log`, U10 `_cfg_schema`/`setup() -> bool`, U11
  `config_filename()`/`write_config(data, defer=True)`/`_commit_mgr_cfg()`).
- **Depends**: M.SRC_CORE.036, .038, .044, .046.
- **Blast carried by**: every subclass (BMP3XX, ISL29125, SGP40, NOTIFY, NTP, WIFI, SCD30) → A.U5.02 (SRC_SENS, SRC_NET);
  `AsyConnTime._set_mgr_cfg()` through `super()` → A.U11.28 (SRC_NET); tests reading `cfg_schema` → A.U10.39
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
that serves defaults from RAM for a missing file (no write), never overwrites an unreadable one (`writable`), validates
against its own schema, compares in stored form, stages only once its flush task exists, can defer the flush until the
caller's pushes finish (`commit()`), serialises before opening, closes race-free for a reset and deletes its own file
for the config reset.

### M.SRC_CORE.049 Header, comments, imports, constants and the constructor
- **From**: A.U0.42 (`:7`), A.U36.514 (`:46-48`), A.U36.004 (1) (`:217`), A.U5.02 (constructor), A.U2.04/A.U2.07
  (constants), A.U10.17 (lock reason), A.U10.18 (`config_lock` → `_config_lock`), A.U10.35 (`config_file` →
  `_config_file`), A.U11.04 (`_closed`), A.U11.20 (`writable`), A.U11.28 (`_commit_ready`), A.U11.31
  (`reset_error_counter() -> bool`), A.U11.S01 (`T` gains `bool`, `Any` goes), A.U19.16 (`Final`), A.U10.31, A.U10.37.
- **Site**: `src/config_manager.py:1-50`, `:215-232`, `:261-265`.
- **Change**: docstring line 1 names `asy_base_classes.py`; line 2 "Every public function/method returns a documented
  "invalid" sentinel, never raises (for typed inputs; a malformed schema fails the static schema check)." `:7` →
  "# directly - SPECIFICATION.md A.4 has the cache-vs-external-corruption trade-off this implies." `:46-48`'s cite →
  "(SPECIFICATION.md Part L.6.4)". Imports: `asyncio`, `errno`, `json`, `os`, `from micropython import const`, `from
  asy_print_log import DEFAULT_LOG, make_logger, report_if_fatal`; `TYPE_CHECKING`: `Callable`, `Final`, `Literal`,
  `NamedTuple`, `TypeVar`; `from asy_print_log import ErrorLog, LogConfig, PrintLogHistory`; `T = TypeVar("T", int, float,
  str, bool)`; no `Any`, no `AsyFramManager`. Constants: `_ERR_ALLOC = const(20)`, `_ERR_BAD_ARG = const(21)`,
  `_ERR_UNEXPECTED = const(23)`, `_ERR_CONTRACT = const(24)`, `_ERR_CFG_PATH_IS_DIR = const(30)`, `_ERR_CFG_NO_DEFAULTS =
  const(31)`, `_ERR_CFG_BAD_DEFAULT = const(32)`, `_ERR_CFG_FILE_WRITE = const(33)`, `_ERR_CFG_NOT_VALID = const(34)`,
  `_WRN_STORED_DEFAULT = const(10)`, `_WRN_CFG_FILE_NOT_OBJECT = const(20)`, `_WRN_CFG_FILE_JSON = const(21)`,
  `_WRN_CFG_FILE_UNREADABLE = const(22)`, `_WRN_CFG_KEYS_REMOVED = const(23)` (24 retired, A.U11.19). `__init__(self,
  filename: str, cfg_vals: "ConfigSchema", name: str, log: "LogConfig" = DEFAULT_LOG)`: `self.name = "CFGMGR_" + name`;
  `self.pr = make_logger(log, self.name)` with the comment "# Inherits its owning module's logging config - FRAM-backed
  when the module is (the implicit FRAM-wiring / # rule, SPECIFICATION.md A.7) - so its failure history survives a
  reboot like the module's own."; `self._config_lock = asyncio.Lock()` ("# serialises the config file and its staged
  snapshot"); `self._config_file`, `self.cfg_vals`, `self.valid = False`, `self.writable = True`, `self._closed = False`,
  `self._cache`, `self._staged` (comment `:228-230` kept), `self._pending_flush`, `self._commit_ready = asyncio.Event()`
  (set: "# cleared while a deferred snapshot waits for its commit()"; `_commit_ready.set()` in `__init__`).
  `reset_error_counter() -> bool: return await self.pr.reset()`.
- **Resolved**: A.U36.004 (1)'s condition "follows A.U5.02's wording and keeps this citation" — applied.
- **Unit**: U11 (stages: U0 tag lines of M.SRC_CORE.047; U2 constants at HEAD sites; U5 `log`; U10 names/lock reason;
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
  `compare_before_write()`, `_stored_float()` after `check_cfg_get_default()`.
- **Change**: the five `try/except Exception` (`:80-83`, `:94-97`, `:111-114`, `:115-118`, `:150/:185-186`) and
  `check_cfg_get_default()`'s `:193/:205-206` go (bodies unchanged otherwise; the `:79`/`:93` trailing comments lose
  "malformed input -> []"/"{}"). `coerce_numeric(...) -> "tuple[bool, CfgValue]"`; comment `:124` → "bool is excluded
  both ways by exact type (on MicroPython `bool` is not an `int` subclass)"; `:126-127` → "# Public and reused: every
  numeric check calls it through type_or_range_error(), the generated / # lightCmdLED dispatch included (synthetic
  FieldSchemas, buildgen/codegen.py)."; `:131` "an accepted gap" → "an accepted gap (owner, 2026-08-24)"; the tuple
  `(OverflowError, ValueError)` stays (already ordered). `type_or_range_error(...) -> "tuple[bool, CfgValue]"`: int branch
  `if not ok or type(check_val) is not int:` and float branch `if not ok or type(check_val) is not float:` with one line
  "# never true after ok; narrows the type". `compare_before_write(data, cfg_vals, current, *, always=(),
  resolution=None) -> "tuple[dict[str, CfgValue], WriteValidity] | None"` exactly as A.U4.01 (per-key outcomes in `data`
  order; `None` for a non-dict `data`; logs nothing; never raises but `MemoryError`); `resolution` typed
  `dict[str, Callable[[CfgValue], CfgValue]] | None` (no `Any`). `_stored_float(v: float) -> float: return
  json.loads(json.dumps(v))` with the residual comment of A.U11.21 (idempotence on rp2 proven by the L3 script; fallback to
  the serialised text decided with evidence).
- **Resolved**: A.U4.01 types `resolution` with `Callable[[Any], CfgValue]`; A.U11.S01/G8/R61 (owner, OR81: no
  hand-written `Any`) → `Callable[[CfgValue], CfgValue]`.
- **Unit**: U11 (A.U4.01 in U4 as its stage — A.U4.02 in U4 needs it; the guard removal and typing in U11; U0's tag at
  `:131` as a U0 stage).
- **Depends**: A.U11.18 (static schema check lands first or together, TSC).
- **Blast carried by**: schema callers (typed consts) and the generated `lightCmdLED` dispatch (`or type(r) is not int …`
  narrowing) → A.U11.S01 (GEN); webserver pause dispatch narrowing → A.U11.S01 (SRC_NET); ISL29125 `_checked_cfg()` arm →
  A.U11.S01 vs A.U15.38 (1) conflict, SRC_SENS merges (SUPP_coverage A-C note 1); SCD30 chip store uses the primitive →
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
- **From**: A.U3.05, A.U11.29, A.U11.S01 (3), A.U35.43 (2) (`get_dict()`'s `TypeError`), A.U2.07.
- **Site**: `src/config_manager.py:240-297`.
- **Change**: `_get_values(keys) -> "list[CfgValue] | None"` (`_ERR_CFG_NOT_VALID`; `KeyError` → `_ERR_CONTRACT`).
  `_get_converted_values()` goes; new `_get_typed_values(keys, scalar_type: "type[T]") -> "list[T] | None"`: per value,
  `int`/`float` through `coerce_numeric(v, scalar_type)` then appended only after `isinstance(value, scalar_type)`,
  `str`/`bool` by `type(v) is scalar_type`; any refusal → one `err_s(self._config_file, "- stored value has the wrong
  type:", key, errno=_ERR_CONTRACT)` and `None` (all-or-nothing). `get_int_values`/`get_float_values`/`get_str_values`/
  `get_bool_values` call it. `get_dict(keys)`: `_ERR_CFG_NOT_VALID`, `except KeyError as e` → `_ERR_CONTRACT` (the
  `TypeError` half goes: keys are typed); its lock-free comment `:268-270` kept.
- **Resolved**: A.U11.29 and A.U11.S01 (3) describe the same helper — merged (exact-type test is also mypy's narrowing).
- **Unit**: U11 (U3 stage: the 24 reports; U2 names).
- **Depends**: M.SRC_CORE.047, .049.
- **Blast carried by**: the eleven caller sites print instead of persisting → A.U3.05 (SRC_SENS, SRC_NET); the 21
  getter call sites unchanged → A.U11.29; tests `test_config_manager.py:1496-1552`, caller-module tests → A.U3.05,
  A.U11.29 (TEST_UNIT); SPEC C.5 `:1731-1734`, C.5/C.7 caller rule → A.U11.29, A.U3.05 (SPEC).
- **Kind**: code

### M.SRC_CORE.044 `write_config()` and the deferred flush
- **From**: A.U4.02, A.U11.24, A.U11.25, A.U11.21, A.U11.22, A.U11.28, A.U11.23 (flush half), A.U10.20, A.U35.43 (1)(2),
  A.U2.07, A.U11.04 + A.S0930.16 (1) (closed checks), A.U11.20 (`writable` check), A.U19.16, A.U10.45.
- **Site**: `src/config_manager.py:299-388`.
- **Change**: `async def write_config(self, data: "dict[str, CfgValue]", *, defer: bool = False) -> "tuple[bool,
  WriteValidity]"` (the `cfg_vals` parameter goes; the manager's own schema is used). Before the lock: `if self._closed:
  self.pr.evt(self._config_file, "- writes closed for reset"); return False, {}`; `if not self.valid:` persisted
  `_ERR_CFG_NOT_VALID`, `return False, {}`; `if not self.writable: self.pr.evt(self._config_file, "- unreadable at boot,
  writes refused until the next boot"); return False, {}`. Under `async with self._config_lock:` — first the same
  `_closed` check (A.S0930.16 (1)); `try: outcome = compare_before_write(data, self.cfg_vals, self._current(),
  always=<the special-alone keys of self.cfg_vals>, resolution=<every "float" field → _stored_float>)` / `except
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
  regress a replaced value."); `try:` `if staged != self._cache: text = json.dumps(staged)`, `with open(self._config_file,
  "w") as f: f.write(text)`, evt "written"`; `except (MemoryError, OSError, ValueError) as e:` `_ERR_CFG_FILE_WRITE`
  (comment kept); `finally:` the bookkeeping `:384-388` unchanged.
- **Resolved**: A.U11.22 (create the task, then stage) and A.U11.28 (a deferred task waits on `_commit_ready`) keep
  their order (A.U11.28 says so). A.U11.04's "checked first, before the lock" + A.S0930.16's re-check inside the lock →
  both (SUPP conflict 1). A.U2.07's `:356` split (`MemoryError` → 20, `AttributeError` → 21) is superseded: A.U4.02 moves
  the non-dict case into the primitive's `None` (21) and A.U35.43 removes the `AttributeError` class; the remaining
  allocation failure keeps 20. A.U11.23 applies to both write sites (flush here, repair in M.SRC_CORE.043).
- **Unit**: U11 (U4 stage: the primitive inside; U2 names; U19 constants swap; U30 `report_if_fatal`; A.U35.43 pulled
  into U11 — its reachability fact needs A.U11.28's deferral, which lands here, and its removals are the same lines).
- **Depends**: M.SRC_CORE.047, .049; M.SRC_CORE.038 (callers pass `defer=True` and commit).
- **Blast carried by**: callers `SensorReaderConfig._set_mgr_cfg()` (M.SRC_CORE.040), `SystemService._set_dict_cfg()`
  (M.SRC_CORE.017), `AsyConnTime._set_mgr_cfg()` → A.U11.24/A.U11.28 (SRC_NET); every test passing a second
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
  A.S0930.16 (2) (read `_pending_flush` under the lock).
- **Site**: `src/config_manager.py:390-400` `flush_pending()`; new `close_writes()`, `commit()`.
- **Change**: `def close_writes(self) -> None: self._closed = True` (one-way). `def commit(self) -> None:
  self._commit_ready.set()`. `async def flush_pending(self) -> None`: `self._commit_ready.set()`; `async with
  self._config_lock: pending = self._pending_flush`; `if pending is not None: await pending`; comment (≤ 3 lines) "#
  Releases a deferred flush, then awaits the latest flush task read under the lock, so a write_config() / # that held the
  lock has finished staging first; an earlier, superseded task no-ops by its identity check."
- **Resolved**: SUPP conflict 1 (additive).
- **Unit**: U11.
- **Depends**: M.SRC_CORE.044.
- **Blast carried by**: callers `_flush_config_stores()` (M.SRC_CORE.010), device scripts' flush guard →
  A.U11.28 (TSC `test_device_script_config_flush.py`); L1 close tests → A.U11.04, A.S0930.21/.22 (TEST_UNIT); SPEC
  C.5.2/C.7.3 "a closed store refuses writes" → A.S0930.16 (SPEC).
- **Kind**: code

### M.SRC_CORE.042 A store deletes its own file for "Reset to defaults"
- **From**: A.S0930.16 (3).
- **Site**: `src/config_manager.py` new `delete_file()`.
- **Change**: exactly A.S0930.16 (3): `async def delete_file(self) -> bool`: `self.close_writes()`; `async with
  self._config_lock:` `os.remove(self._config_file)`, `except OSError as e:` ENOENT → `True`; otherwise one retry, a second
  failure → `self.pr.err(self._config_file, "- could not be deleted:", e)`, `False`; success → `self.pr.evt(…, "- deleted,
  defaults at the next boot")`, `True`. Comment (≤ 3 lines) "# Reset to defaults (owner, 2026-09-30): the next boot
  serves the schema defaults; the SCD30 keeps its / # settings in its own NVM and has no file."
- **Resolved**: the comment's SCD30 clause holds for the chip settings; after A.U15.12 SCD30 owns a `config_SCD30.cfg`
  for its three FRC settings, which the reset deletes like every other store's (OR124.a "every schema-backed
  `config_<name>.cfg`") — the comment reads "the SCD30's chip settings stay in its own NVM" (agent, 2026-10-01).
- **Unit**: U11.
- **Depends**: M.SRC_CORE.041, M.SRC_CORE.049 (`errno` import).
- **Blast carried by**: caller S5 (M.SRC_CORE.011); tests → A.S0930.21/.25/.27/.28/.29 (TEST_UNIT, TWIN, HW_DEV,
  HW_BENCH, `persistence_write` gate A.S0930.19); SPEC C.5.2/C.7.3 → A.S0930.16/.30 (SPEC).
- **Kind**: code

### M.SRC_CORE.043 `setup()`: missing file writes nothing; unreadable never overwritten; repair serialises first
- **From**: A.U11.19, A.U11.20, A.U11.23 (repair half), A.U35.43 (2) (`:423`, `:479` `TypeError`), A.U2.07, A.U10.21,
  A.U36.004 (7), A.U10.45.
- **Site**: `src/config_manager.py:402-485`.
- **Change**: `async def setup(self) -> bool`; `await self.pr.setup()` with the `:403-405` comment's cite → "(the implicit
  FRAM-wiring rule, SPECIFICATION.md A.7)". Read: directory → `_ERR_CFG_PATH_IS_DIR`, `return False`; non-object →
  `_WRN_CFG_FILE_NOT_OBJECT`; bad JSON → `_WRN_CFG_FILE_JSON`; `except OSError as e:` `e.errno == errno.ENOENT` →
  `missing = True`, `self.pr.one("Config file", self._config_file, "not present - defaults in RAM until the first
  change")`; any other `OSError` and `except MemoryError` → `await self.pr.wrn_s("Config file", self._config_file, "could
  not be read:", e, wrnno=_WRN_CFG_FILE_UNREADABLE)`, `self.writable = False`. Schema loop as HEAD with `_ERR_CFG_NO_DEFAULTS`
  / `_ERR_CFG_BAD_DEFAULT` (`return False`) and `_WRN_STORED_DEFAULT`; `rewrite` only from a readable file (bad or missing
  key, unknown keys → `_WRN_CFG_KEYS_REMOVED`, a readable file with corrupt JSON or a non-object). Then `self._cache =
  valid_cfg`, `self.valid = True`; no write when `missing`, when not `writable`, when `valid_cfg` is empty (every field
  special-alone: `self.pr.one(…, "- schema stores no values, no file")`) or when nothing needs repair; otherwise the one
  repair write: `text = json.dumps(valid_cfg)`, then `with open(…, "w") as f: f.write(text)`, `except (MemoryError,
  OSError) as e:` `_ERR_CFG_FILE_WRITE` (comments `:480`, `:482-483` kept). `return self.valid`.
- **Resolved**: A.U11.19 (missing) and A.U11.20 (unreadable) split HEAD's one `except (MemoryError, OSError, TypeError)`
  by errno; A.U35.43 drops `TypeError` (the filename is a typed `str`).
- **Unit**: U11 (U2 names as stage).
- **Depends**: M.SRC_CORE.049, .047.
- **Blast carried by**: SystemService reads `writable` (M.SRC_CORE.017); tests `tests/test_config_manager.py` (A.U11.19's
  list `:838-846`, `:1074-1126`, `:1347-1356`, `:2275-2509`; A.U11.20's `:2275-2298`), `tests/test_base_classes.py:1013-1016,
  1449-1452` → A.U11.19, A.U11.20, A.U11.23 (TEST_UNIT); twin configs start empty → holds (TWIN, README note A.U11.19);
  L0 "normal boot logs nothing" → A.U35.38/.39 (TSC, TWIN); mockdata W22/W24 rows → A.U2.25/A.U3.15 (WEB); SPEC C.7.3,
  C.5.2.1, LEAD/R32 register fix 2 → A.U11.19, A.U11.20 (SPEC, register).
- **Kind**: code
