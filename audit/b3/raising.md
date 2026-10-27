# Raising calls in the never-raise modules (M.PROC.025, A.U35.36)

Requirement: per never-raise module an `ast` walk lists every call outside a `try` that catches it and every `raise`, each classified from the pinned source as handled (the catching `except`), unreachable (with the proof, an E.5.1 verdict) or a defect (fixed at the right layer with a test injecting the raise and asserting the sentinel). Completion: no row left unclassified. A defect any file records goes the OR12.a path (fixed with a regression test seen failing first, or an owner question), never a note alone, and passes A-C as a delta before it is applied (OR106.a). The file is complete when every row is terminal: biting, fixed, or justified with its reason. Opened by A.U35.01 / M.PROC.022 (agent, 2026-10-22); deleted with `audit/` at phase D.

## Walk summary

Walked over `src/` as of `1298e714` by `audit/b3/raising_walk.py` (agent, 2026-10-22). Re-run it on the integration head: lanes P
and Y edit four of these modules in U35. A row left "open" needs its per-site proof from the pinned source in the B3 campaign.

Sites per module (call or raise) by the `try` enclosing them: inside one catching `Exception` (broad), inside one
catching named classes only (narrow), or none. Broad sites are handled by construction; the rows below are the rest.

| module | calls broad | calls narrow | calls none | raises |
|---|---|---|---|---|
| asy_base_classes.py | 16 | 4 | 164 | 1 |
| asy_config_manager.py | 6 | 29 | 134 | 0 |
| asy_print_log.py | 2 | 15 | 113 | 0 |
| asy_system_service.py | 53 | 9 | 202 | 0 |
| asy_fram_manager.py | 49 | 2 | 248 | 0 |
| asy_fram_driver.py | 1 | 3 | 165 | 4 |
| math_helpers.py | 0 | 10 | 35 | 0 |

Rows outside a broad `try`, by verdict: handled 10, inherently safe 12, open 398, transitive 500, unreachable 213.

## Raises

| module:line | function | call or raise | can raise (pinned source) | verdict | proof or action |
|---|---|---|---|---|---|
| asy_base_classes.py:370 | _checked_write_results | `raise TypeError('_set_mgr_cfg returned a non-dict result')` | the raise itself | handled | both callers sit in a try catching Exception: asy_base_classes.py:507 (except :508) and :689 (except :690); the raise is that try's logged failure, as its comment says |
| asy_fram_driver.py:162 | FRAM_SPI.__aenter__ | `raise` | the raise itself | inherently safe | cleanup then re-raise: a BaseException (a cancel) while waiting for the bus lock releases the session lock first; a cancellation must propagate |
| asy_fram_driver.py:207 | FRAM_SPI._check_device_id | `raise ValueError(f"FRAM max_size {self._max_size:#x} has no known product ID to verify against -` | the raise itself | exempt (setup) | one-time identification error, outside M.PROC.025's scope; reached from FRAM_SPI.setup(), whose one caller asy_fram_manager.py:795 sits in a try catching Exception (except :796) |
| asy_fram_driver.py:455 | FRAM_SPI.setup | `raise OSError('SPI bus not initialized')` | the raise itself | exempt (setup) | one-time setup error, outside M.PROC.025's scope; the one caller asy_fram_manager.py:795 sits in a try catching Exception (except :796) |
| asy_fram_driver.py:469 | FRAM_SPI.setup | `raise OSError('FRAM SPI device not found')` | the raise itself | exempt (setup) | one-time setup error, outside M.PROC.025's scope; the one caller asy_fram_manager.py:795 sits in a try catching Exception (except :796) |

## Calls outside a broad try (grouped by module and callee)

| module:line | function | call or raise | can raise (pinned source) | verdict | proof or action |
|---|---|---|---|---|---|
| asy_base_classes.py:38 | <module> | `TypeVar` at :38 | not classified | open | - |
| asy_base_classes.py:73 | <module> | `namedtuple` at :73 | not classified | open | - |
| asy_base_classes.py:76 | <module> | `const` at :76, :78, :80, :81, :84, :85, :86, :87, :88, :89, :90, :91 (+13) | nothing at run time | unreachable | folded at compile time (py/compile.c, MICROPY_COMP_CONST) |
| asy_base_classes.py:115 | Lockable.__init__ +1 | `asyncio.Lock` at :115, :423, :426 | MemoryError (py/gc.c gc_alloc via m_malloc_fail) | open | setup-only or run-time allocation decides (I.4) |
| asy_base_classes.py:118 | Lockable.__aenter__ | `self.session_lock.acquire` at :118 | not classified | open | - |
| asy_base_classes.py:130 | Lockable.__aexit__ | `self.session_lock.release` at :130; narrow except RuntimeError | not classified | open | - |
| asy_base_classes.py:132 | Lockable.__aexit__ +4 | `report_if_fatal` at :132, :458, :473, :504, :516, :544, :570, :682, :698 | what the callee raises | transitive | the callee's own rows here |
| asy_base_classes.py:140 | DeviceSession.__init__ +2 | `super` at :140, :140, :801, :801, :844, :844 | TypeError/ValueError on unsupported operands (py/modbuiltins.c, py/obj.c) | open | operand-type proof |
| asy_base_classes.py:159 | RegionBuffer.__init__ +1 | `bytearray` at :159, :181; narrow except MemoryError/OverflowError | MemoryError (py/gc.c gc_alloc via m_malloc_fail) | open | setup-only or run-time allocation decides (I.4) |
| asy_base_classes.py:162 | RegionBuffer.__init__ +1 | `console` at :162, :389 | what the callee raises | transitive | the callee's own rows here |
| asy_base_classes.py:171 | RegionBuffer.get_data_buf +2 | `memoryview` at :171, :195, :219 | MemoryError (py/gc.c gc_alloc via m_malloc_fail) | open | setup-only or run-time allocation decides (I.4) |
| asy_base_classes.py:181 | PieceBuffer.__init__ +4 | `min` at :181, :224, :238, :244, :361 | TypeError/ValueError on unsupported operands (py/modbuiltins.c, py/obj.c) | open | operand-type proof |
| asy_base_classes.py:181 | PieceBuffer.__init__ +2 | `range` at :181, :309, :312, :323 | TypeError/ValueError on unsupported operands (py/modbuiltins.c, py/obj.c) | open | operand-type proof |
| asy_base_classes.py:188 | PieceBuffer.copy_into +2 | `len` at :188, :192, :194, :209, :217, :222, :224, :224 | TypeError/ValueError on unsupported operands (py/modbuiltins.c, py/obj.c) | open | operand-type proof |
| asy_base_classes.py:190 | PieceBuffer.copy_into +1 | `divmod` at :190, :220 | TypeError/ValueError on unsupported operands (py/modbuiltins.c, py/obj.c) | open | operand-type proof |
| asy_base_classes.py:202 | PieceBuffer.pieces | `iter` at :202 | TypeError/ValueError on unsupported operands (py/modbuiltins.c, py/obj.c) | open | operand-type proof |
| asy_base_classes.py:210 | PieceBuffer.trim | `self._pieces.pop` at :210 | not classified | open | - |
| asy_base_classes.py:238 | LockedCounter.__init__ +2 | `max` at :238, :244, :361 | TypeError/ValueError on unsupported operands (py/modbuiltins.c, py/obj.c) | open | operand-type proof |
| asy_base_classes.py:239 | LockedCounter.__init__ +1 | `self._clamp` at :239, :250 | what the callee raises | transitive | the callee's own rows here |
| asy_base_classes.py:317 | HourlyWindowCounter.add +1 | `self._advance` at :317, :327 | what the callee raises | transitive | the callee's own rows here |
| asy_base_classes.py:344 | TickSeconds.__init__ +2 | `time.ticks_ms` at :344, :347, :363 | TypeError only for a non-int argument | inherently safe | small-int arguments (extmod/modtime.c:150-196) |
| asy_base_classes.py:348 | TickSeconds.read | `time.ticks_diff` at :348 | TypeError only for a non-int argument | inherently safe | small-int arguments (extmod/modtime.c:150-196) |
| asy_base_classes.py:369 | _checked_write_results | `isinstance` at :369 | TypeError/ValueError on unsupported operands (py/modbuiltins.c, py/obj.c) | open | operand-type proof |
| asy_base_classes.py:370 | _checked_write_results | `TypeError` at :370 | not classified | open | - |
| asy_base_classes.py:387 | arm_tick_timer | `timer.init` at :387; narrow except MemoryError/OSError | not classified | open | - |
| asy_base_classes.py:387 | arm_tick_timer | `flag.set` at :387; narrow except MemoryError/OSError | not classified | open | - |
| asy_base_classes.py:393 | arm_tick_timer | `pr.err` at :393 | what the callee raises | transitive | the callee's own rows here |
| asy_base_classes.py:418 | SensorReader.__init__ | `instance_name` at :418 | what the callee raises | transitive | the callee's own rows here |
| asy_base_classes.py:419 | SensorReader.__init__ | `make_logger` at :419 | what the callee raises | transitive | the callee's own rows here |
| asy_base_classes.py:449 | SensorReader._get_dict_cfg | `schema_names` at :449 | what the callee raises | transitive | the callee's own rows here |
| asy_base_classes.py:450 | SensorReader._get_dict_cfg +1 | `dict.fromkeys` at :450, :493, :524 | MemoryError (py/gc.c gc_alloc via m_malloc_fail) | open | setup-only or run-time allocation decides (I.4) |
| asy_base_classes.py:459 | SensorReader._get_dict_cfg +5 | `self.pr.err_s` at :459, :474, :505, :517, :545, :571, :591, :593, :683, :699, :727 | what the callee raises | transitive | the callee's own rows here |
| asy_base_classes.py:491 | SensorReader._set_dict_cfg | `self._writes_closed` at :491 | what the callee raises | transitive | the callee's own rows here |
| asy_base_classes.py:494 | SensorReader._set_dict_cfg | `schema_dict` at :494 | what the callee raises | transitive | the callee's own rows here |
| asy_base_classes.py:498 | SensorReader._set_dict_cfg | `fields.items` at :498 | not classified | open | - |
| asy_base_classes.py:499 | SensorReader._set_dict_cfg +1 | `check_cfg_get_default` at :499, :671 | what the callee raises | transitive | the callee's own rows here |
| asy_base_classes.py:530 | SensorReader._set_dict_cfg | `results.setdefault` at :530 | not classified | open | - |
| asy_base_classes.py:531 | SensorReader._set_dict_cfg | `data.items` at :531 | not classified | open | - |
| asy_base_classes.py:532 | SensorReader._set_dict_cfg | `results.get` at :532 | not classified | open | - |
| asy_base_classes.py:534 | SensorReader._set_dict_cfg | `self._push_callbacks.get` at :534 | not classified | open | - |
| asy_base_classes.py:535 | SensorReader._set_dict_cfg +1 | `fields.get` at :535, :668 | not classified | open | - |
| asy_base_classes.py:540 | SensorReader._set_dict_cfg +1 | `type_or_range_error` at :540, :689 | what the callee raises | transitive | the callee's own rows here |
| asy_base_classes.py:549 | SensorReader._set_dict_cfg | `self._recover_failed_push` at :549 | what the callee raises | transitive | the callee's own rows here |
| asy_base_classes.py:551 | SensorReader._set_dict_cfg | `self._commit_mgr_cfg` at :551 | what the callee raises | transitive | the callee's own rows here |
| asy_base_classes.py:574 | SensorReader._climb_ladder +2 | `self.pr.wrn_s` at :574, :613, :646, :649 | what the callee raises | transitive | the callee's own rows here |
| asy_base_classes.py:576 | SensorReader._climb_ladder +1 | `self._recover_bus` at :576, :578, :623 | what the callee raises | transitive | the callee's own rows here |
| asy_base_classes.py:587 | SensorReader._error_check | `any` at :587 | not classified | open | - |
| asy_base_classes.py:595 | SensorReader._error_check | `self._climb_ladder` at :595 | what the callee raises | transitive | the callee's own rows here |
| asy_base_classes.py:599 | SensorReader._error_check +2 | `self.pr.err` at :599, :703, :717 | what the callee raises | transitive | the callee's own rows here |
| asy_base_classes.py:611 | SensorReader._init_done | `bus.take_boot_clear_status` at :611 | not classified | open | - |
| asy_base_classes.py:631 | SensorReader._rearm_timer +1 | `self._timer_fault` at :631, :737 | what the callee raises | transitive | the callee's own rows here |
| asy_base_classes.py:633 | SensorReader._rearm_timer | `self.start_timer` at :633 | not classified | open | - |
| asy_base_classes.py:645 | SensorReader._recover_bus | `bus.clear` at :645 | what the callee raises | transitive | the callee's own rows here |
| asy_base_classes.py:648 | SensorReader._recover_bus | `bus.recover` at :648 | not classified | open | - |
| asy_base_classes.py:677 | SensorReader._recover_failed_push | `self._get_callbacks.get` at :677 | not classified | open | - |
| asy_base_classes.py:692 | SensorReader._recover_failed_push | `old_values.get` at :692 | not classified | open | - |
| asy_base_classes.py:701 | SensorReader._recover_failed_push | `res.get` at :701, :703 | not classified | open | - |
| asy_base_classes.py:710 | SensorReader._republish | `getattr` at :710 | TypeError/ValueError on unsupported operands (py/modbuiltins.c, py/obj.c) | open | operand-type proof |
| asy_base_classes.py:711 | SensorReader._republish | `type` at :711, :711 | TypeError/ValueError on unsupported operands (py/modbuiltins.c, py/obj.c) | open | operand-type proof |
| asy_base_classes.py:718 | SensorReader._timer_failed | `waiter.set` at :718 | not classified | open | - |
| asy_base_classes.py:733 | SensorReader._trigger_loop | `self._rearm_timer` at :733 | what the callee raises | transitive | the callee's own rows here |
| asy_base_classes.py:736 | SensorReader._trigger_loop | `self._base_trigger_event.wait` at :736 | not classified | open | - |
| asy_base_classes.py:740 | SensorReader._trigger_loop | `self._trigger_period.get_value` at :740 | what the callee raises | transitive | the callee's own rows here |
| asy_base_classes.py:742 | SensorReader._trigger_loop | `self._read_event.set` at :742 | not classified | open | - |
| asy_base_classes.py:754 | SensorReader.get_error_counter | `self.pr.get_log` at :754 | what the callee raises | transitive | the callee's own rows here |
| asy_base_classes.py:773 | SensorReader.reset_error_counter | `self.pr.reset` at :773 | what the callee raises | transitive | the callee's own rows here |
| asy_base_classes.py:777 | SensorReader.setup | `self.pr.setup` at :777 | what the callee raises | transitive | the callee's own rows here |
| asy_base_classes.py:783 | utc_now | `time.mktime` at :783 | not classified | open | - |
| asy_base_classes.py:783 | utc_now | `time.gmtime` at :783 | not classified | open | - |
| asy_base_classes.py:806 | SensorReaderConfig.__init__ | `LogConfig` at :806 | not classified | open | - |
| asy_base_classes.py:807 | SensorReaderConfig.__init__ | `ConfigManager` at :807 | not classified | open | - |
| asy_base_classes.py:807 | SensorReaderConfig.__init__ | `config_filename` at :807 | what the callee raises | transitive | the callee's own rows here |
| asy_base_classes.py:811 | SensorReaderConfig._get_mgr_cfg +1 | `self.pr.evt` at :811, :819 | what the callee raises | transitive | the callee's own rows here |
| asy_base_classes.py:814 | SensorReaderConfig._get_mgr_cfg | `self.cfgmgr.get_dict` at :814 | what the callee raises | transitive | the callee's own rows here |
| asy_base_classes.py:820 | SensorReaderConfig._set_mgr_cfg | `self.cfgmgr.write_config` at :820 | what the callee raises | transitive | the callee's own rows here |
| asy_base_classes.py:823 | SensorReaderConfig._commit_mgr_cfg | `self.cfgmgr.commit` at :823 | what the callee raises | transitive | the callee's own rows here |
| asy_base_classes.py:827 | SensorReaderConfig._writes_closed | `self.cfgmgr.writes_closed` at :827 | what the callee raises | transitive | the callee's own rows here |
| asy_base_classes.py:845 | SensorReaderConfig.setup | `self.cfgmgr.setup` at :845 | what the callee raises | transitive | the callee's own rows here |
| asy_config_manager.py:30 | <module> | `TypeVar` at :30 | not classified | open | - |
| asy_config_manager.py:58 | <module> | `const` at :58, :59, :60, :61, :62, :63, :64, :65, :66, :67, :68, :69 (+2) | nothing at run time | unreachable | folded at compile time (py/compile.c, MICROPY_COMP_CONST) |
| asy_config_manager.py:75 | _as_bool +11 | `type` at :75, :79, :85, :87, :99, :101, :115, :115, :116, :121, :165, :165 (+11); narrow except MemoryError | TypeError/ValueError on unsupported operands (py/modbuiltins.c, py/obj.c) | open | operand-type proof |
| asy_config_manager.py:91 | _coerce_float +1 | `float` at :91, :106 | TypeError/ValueError on unsupported operands (py/modbuiltins.c, py/obj.c) | open | operand-type proof |
| asy_config_manager.py:103 | _coerce_int | `int` at :103; narrow except OverflowError/ValueError | TypeError/ValueError on unsupported operands (py/modbuiltins.c, py/obj.c) | open | operand-type proof |
| asy_config_manager.py:116 | _special_bypass | `any` at :116 | not classified | open | - |
| asy_config_manager.py:132 | _stored_float | `json.loads` at :132 | OSError/MemoryError/ValueError/TypeError (extmod/modjson.c) | open | - |
| asy_config_manager.py:132 | _stored_float +1 | `json.dumps` at :132, :592; narrow except MemoryError/OSError | OSError/MemoryError/ValueError/TypeError (extmod/modjson.c) | open | - |
| asy_config_manager.py:145 | check_cfg_get_default +1 | `isinstance` at :145, :527, :539; narrow except MemoryError/OSError/ValueError | TypeError/ValueError on unsupported operands (py/modbuiltins.c, py/obj.c) | open | operand-type proof |
| asy_config_manager.py:148 | check_cfg_get_default +2 | `type_or_range_error` at :148, :214, :569 | what the callee raises | transitive | the callee's own rows here |
| asy_config_manager.py:157 | checked_float | `_coerce_float` at :157 | what the callee raises | transitive | the callee's own rows here |
| asy_config_manager.py:162 | checked_float +2 | `_special_bypass` at :162, :176, :305 | what the callee raises | transitive | the callee's own rows here |
| asy_config_manager.py:171 | checked_int | `_coerce_int` at :171 | what the callee raises | transitive | the callee's own rows here |
| asy_config_manager.py:187 | checked_numeric | `checked_int` at :187 | what the callee raises | transitive | the callee's own rows here |
| asy_config_manager.py:189 | checked_numeric | `checked_float` at :189 | what the callee raises | transitive | the callee's own rows here |
| asy_config_manager.py:206 | compare_before_write +2 | `schema_dict` at :206, :549, :621; narrow except MemoryError | what the callee raises | transitive | the callee's own rows here |
| asy_config_manager.py:209 | compare_before_write | `data.items` at :209 | not classified | open | - |
| asy_config_manager.py:210 | compare_before_write | `fields.get` at :210 | not classified | open | - |
| asy_config_manager.py:225 | compare_before_write | `resolution.get` at :225 | not classified | open | - |
| asy_config_manager.py:227 | compare_before_write | `res` at :227, :227 | not classified | open | - |
| asy_config_manager.py:262 | make_dict | `getattr` at :262 | TypeError/ValueError on unsupported operands (py/modbuiltins.c, py/obj.c) | open | operand-type proof |
| asy_config_manager.py:266 | name_cfg +2 | `schema_names` at :266, :351, :371; narrow except KeyError | what the callee raises | transitive | the callee's own rows here |
| asy_config_manager.py:267 | name_cfg +2 | `len` at :267, :308, :550 | TypeError/ValueError on unsupported operands (py/modbuiltins.c, py/obj.c) | open | operand-type proof |
| asy_config_manager.py:298 | type_or_range_error | `checked_numeric` at :298 | what the callee raises | transitive | the callee's own rows here |
| asy_config_manager.py:321 | ConfigManager.__init__ | `make_logger` at :321 | what the callee raises | transitive | the callee's own rows here |
| asy_config_manager.py:322 | ConfigManager.__init__ | `asyncio.Lock` at :322 | MemoryError (py/gc.c gc_alloc via m_malloc_fail) | open | setup-only or run-time allocation decides (I.4) |
| asy_config_manager.py:342 | ConfigManager.__init__ | `asyncio.Event` at :342 | MemoryError (py/gc.c gc_alloc via m_malloc_fail) | open | setup-only or run-time allocation decides (I.4) |
| asy_config_manager.py:343 | ConfigManager.__init__ +3 | `self._commit_ready.set` at :343, :477, :501, :665 | not classified | open | - |
| asy_config_manager.py:348 | ConfigManager._get_typed_values | `self._get_values` at :348 | what the callee raises | transitive | the callee's own rows here |
| asy_config_manager.py:353 | ConfigManager._get_typed_values | `enumerate` at :353 | TypeError/ValueError on unsupported operands (py/modbuiltins.c, py/obj.c) | open | operand-type proof |
| asy_config_manager.py:354 | ConfigManager._get_typed_values | `coerce` at :354 | not classified | open | - |
| asy_config_manager.py:356 | ConfigManager._get_typed_values +2 | `self._read_run_starts` at :356, :365, :373, :444, :452 | what the callee raises | transitive | the callee's own rows here |
| asy_config_manager.py:357 | ConfigManager._get_typed_values +5 | `self.pr.err_s` at :357, :366, :374, :420, :445, :453, :536, :551, :559, :598, :612, :627 (+5); narrow except MemoryError/OSError | what the callee raises | transitive | the callee's own rows here |
| asy_config_manager.py:359 | ConfigManager._get_typed_values | `typed.append` at :359 | not classified | open | - |
| asy_config_manager.py:368 | ConfigManager._get_values +1 | `self.pr.all` at :368, :447 | what the callee raises | transitive | the callee's own rows here |
| asy_config_manager.py:370 | ConfigManager._get_values +2 | `self._current` at :370, :449, :625, :653; narrow except KeyError/MemoryError | what the callee raises | transitive | the callee's own rows here |
| asy_config_manager.py:380 | ConfigManager._closed_for_reset +2 | `self.pr.evt` at :380, :493, :615, :645, :647, :668 | what the callee raises | transitive | the callee's own rows here |
| asy_config_manager.py:418 | ConfigManager._flush_staged | `report_if_fatal` at :418 | what the callee raises | transitive | the callee's own rows here |
| asy_config_manager.py:432 | ConfigManager._write_file +1 | `open` at :432, :524; narrow except MemoryError/OSError | OSError (extmod/vfs*.c) | open | - |
| asy_config_manager.py:433 | ConfigManager._write_file | `f.write` at :433 | what the callee raises | transitive | the callee's own rows here |
| asy_config_manager.py:437 | ConfigManager.get_bool_values +3 | `self._get_typed_values` at :437, :462, :465, :468 | what the callee raises | transitive | the callee's own rows here |
| asy_config_manager.py:459 | ConfigManager.get_error_counter | `self.pr.get_log` at :459 | what the callee raises | transitive | the callee's own rows here |
| asy_config_manager.py:482 | ConfigManager.delete_file | `self.close_writes` at :482 | what the callee raises | transitive | the callee's own rows here |
| asy_config_manager.py:485 | ConfigManager.delete_file | `range` at :485 | TypeError/ValueError on unsupported operands (py/modbuiltins.c, py/obj.c) | open | operand-type proof |
| asy_config_manager.py:487 | ConfigManager.delete_file | `os.remove` at :487; narrow except OSError | OSError (extmod/vfs*.c) | open | - |
| asy_config_manager.py:495 | ConfigManager.delete_file | `self.pr.err` at :495 | what the callee raises | transitive | the callee's own rows here |
| asy_config_manager.py:509 | ConfigManager.reset_error_counter | `self.pr.reset` at :509 | what the callee raises | transitive | the callee's own rows here |
| asy_config_manager.py:515 | ConfigManager.setup | `self.pr.setup` at :515 | what the callee raises | transitive | the callee's own rows here |
| asy_config_manager.py:522 | ConfigManager.setup | `os.stat` at :522; narrow except MemoryError/OSError | OSError (extmod/vfs*.c) | open | - |
| asy_config_manager.py:526 | ConfigManager.setup | `json.load` at :526; narrow except MemoryError/OSError/ValueError | OSError/MemoryError/ValueError/TypeError (extmod/modjson.c) | open | - |
| asy_config_manager.py:530 | ConfigManager.setup | `self.pr.wrn_s` at :530, :533, :547, :574, :584; narrow except MemoryError/OSError/ValueError | what the callee raises | transitive | the callee's own rows here |
| asy_config_manager.py:543 | ConfigManager.setup | `self.pr.one` at :543, :588, :590, :595; narrow except MemoryError/OSError | what the callee raises | transitive | the callee's own rows here |
| asy_config_manager.py:556 | ConfigManager.setup | `defaults.items` at :556 | not classified | open | - |
| asy_config_manager.py:557 | ConfigManager.setup +1 | `check_cfg_get_default` at :557, :623; narrow except MemoryError | what the callee raises | transitive | the callee's own rows here |
| asy_config_manager.py:568 | ConfigManager.setup | `data.pop` at :568 | not classified | open | - |
| asy_config_manager.py:594 | ConfigManager.setup | `self._write_file` at :594; narrow except MemoryError/OSError | what the callee raises | transitive | the callee's own rows here |
| asy_config_manager.py:609 | ConfigManager.write_config | `self._closed_for_reset` at :609, :618 | what the callee raises | transitive | the callee's own rows here |
| asy_config_manager.py:623 | ConfigManager.write_config | `tuple` at :623; narrow except MemoryError | MemoryError (py/gc.c gc_alloc via m_malloc_fail) | open | setup-only or run-time allocation decides (I.4) |
| asy_config_manager.py:623 | ConfigManager.write_config | `fields.items` at :623, :624; narrow except MemoryError | not classified | open | - |
| asy_config_manager.py:625 | ConfigManager.write_config | `compare_before_write` at :625; narrow except MemoryError | what the callee raises | transitive | the callee's own rows here |
| asy_config_manager.py:635 | ConfigManager.write_config | `dict_results.items` at :635 | not classified | open | - |
| asy_config_manager.py:653 | ConfigManager.write_config | `dict` at :653; narrow except MemoryError | MemoryError (py/gc.c gc_alloc via m_malloc_fail) | open | setup-only or run-time allocation decides (I.4) |
| asy_config_manager.py:654 | ConfigManager.write_config | `write.items` at :654; narrow except MemoryError | not classified | open | - |
| asy_config_manager.py:655 | ConfigManager.write_config | `_stored_float` at :655; narrow except MemoryError | what the callee raises | transitive | the callee's own rows here |
| asy_config_manager.py:656 | ConfigManager.write_config | `asyncio.create_task` at :656; narrow except MemoryError | MemoryError (py/gc.c gc_alloc via m_malloc_fail) | open | setup-only or run-time allocation decides (I.4) |
| asy_config_manager.py:656 | ConfigManager.write_config | `self._flush_staged` at :656; narrow except MemoryError | what the callee raises | transitive | the callee's own rows here |
| asy_config_manager.py:663 | ConfigManager.write_config | `self._commit_ready.clear` at :663 | what the callee raises | transitive | the callee's own rows here |
| asy_print_log.py:59 | <module> | `const` at :59, :60, :61, :62, :63, :64, :67, :68, :69, :70, :71, :72 (+4) | nothing at run time | unreachable | folded at compile time (py/compile.c, MICROPY_COMP_CONST) |
| asy_print_log.py:89 | PrintLog.__init__ | `self.set_level` at :89 | what the callee raises | transitive | the callee's own rows here |
| asy_print_log.py:96 | PrintLog._line +2 | `print` at :96, :184, :461, :463 | TypeError/ValueError on unsupported operands (py/modbuiltins.c, py/obj.c) | open | operand-type proof |
| asy_print_log.py:99 | PrintLog._line +2 | `isinstance` at :99, :414, :486 | TypeError/ValueError on unsupported operands (py/modbuiltins.c, py/obj.c) | open | operand-type proof |
| asy_print_log.py:100 | PrintLog._line +4 | `console` at :100, :155, :297, :329, :356 | what the callee raises | transitive | the callee's own rows here |
| asy_print_log.py:106 | PrintLog.set_level | `type` at :106 | TypeError/ValueError on unsupported operands (py/modbuiltins.c, py/obj.c) | open | operand-type proof |
| asy_print_log.py:109 | PrintLog.set_level | `self.err` at :109 | what the callee raises | transitive | the callee's own rows here |
| asy_print_log.py:113 | PrintLog.all +6 | `self._line` at :113, :116, :119, :122, :140, :263, :277 | what the callee raises | transitive | the callee's own rows here |
| asy_print_log.py:145 | PrintLogHistory.__init__ +1 | `super` at :145, :145, :285, :285 | TypeError/ValueError on unsupported operands (py/modbuiltins.c, py/obj.c) | open | operand-type proof |
| asy_print_log.py:149 | PrintLogHistory.__init__ +3 | `min` at :149, :173, :203, :207 | TypeError/ValueError on unsupported operands (py/modbuiltins.c, py/obj.c) | open | operand-type proof |
| asy_print_log.py:149 | PrintLogHistory.__init__ | `max` at :149 | TypeError/ValueError on unsupported operands (py/modbuiltins.c, py/obj.c) | open | operand-type proof |
| asy_print_log.py:151 | PrintLogHistory.__init__ | `deque` at :151, :154; narrow except MemoryError | not classified | open | - |
| asy_print_log.py:169 | PrintLogHistory._clear +1 | `self._since_kept` at :169, :308 | what the callee raises | transitive | the callee's own rows here |
| asy_print_log.py:170 | PrintLogHistory._clear +1 | `range` at :170, :309 | TypeError/ValueError on unsupported operands (py/modbuiltins.c, py/obj.c) | open | operand-type proof |
| asy_print_log.py:170 | PrintLogHistory._clear +5 | `len` at :170, :190, :194, :207, :288, :289, :308, :309, :422 | TypeError/ValueError on unsupported operands (py/modbuiltins.c, py/obj.c) | open | operand-type proof |
| asy_print_log.py:172 | PrintLogHistory._clear +1 | `self._since_counted` at :172, :307 | what the callee raises | transitive | the callee's own rows here |
| asy_print_log.py:180 | PrintLogHistory._count +5 | `self._diag` at :180, :217, :222, :235, :299, :367, :372, :382, :392, :411, :434 | what the callee raises | transitive | the callee's own rows here |
| asy_print_log.py:191 | PrintLogHistory._keep | `self.history.append` at :191 | not classified | open | - |
| asy_print_log.py:212 | PrintLogHistory._store_err +1 | `self._count` at :212, :238 | what the callee raises | transitive | the callee's own rows here |
| asy_print_log.py:219 | PrintLogHistory._store_err +1 | `self._keep` at :219, :239 | what the callee raises | transitive | the callee's own rows here |
| asy_print_log.py:224 | PrintLogHistory._store_err +1 | `self._write_through` at :224, :432 | what the callee raises | transitive | the callee's own rows here |
| asy_print_log.py:232 | PrintLogHistory._write_through +2 | `self._write` at :232, :380, :428 | what the callee raises | transitive | the callee's own rows here |
| asy_print_log.py:251 | PrintLogHistory.get_log | `err_num.append` at :251, :254, :257 | not classified | open | - |
| asy_print_log.py:252 | PrintLogHistory.get_log | `err_type.append` at :252, :255, :258 | not classified | open | - |
| asy_print_log.py:262 | PrintLogHistory.err_s +1 | `self._store_err` at :262, :276 | what the callee raises | transitive | the callee's own rows here |
| asy_print_log.py:266 | PrintLogHistory.reset +1 | `self._clear` at :266, :384 | what the callee raises | transitive | the callee's own rows here |
| asy_print_log.py:282 | PrintLogHistoryStore | `struct.calcsize` at :282 | ValueError/TypeError on a bad format or short buffer (py/modstruct.c) | open | format and buffer size proof |
| asy_print_log.py:293 | PrintLogHistoryStore.__init__ | `fram.get_chunk` at :293; narrow except MemoryError | what the callee raises | transitive | the callee's own rows here |
| asy_print_log.py:293 | PrintLogHistoryStore.__init__ | `CRC8` at :293; narrow except MemoryError | not classified | open | - |
| asy_print_log.py:300 | PrintLogHistoryStore.__init__ | `asyncio.Lock` at :300 | MemoryError (py/gc.c gc_alloc via m_malloc_fail) | open | setup-only or run-time allocation decides (I.4) |
| asy_print_log.py:307 | PrintLogHistoryStore._pack_reset +1 | `struct.pack_into` at :307, :350, :351; narrow except MemoryError | ValueError/TypeError on a bad format or short buffer (py/modstruct.c) | open | format and buffer size proof |
| asy_print_log.py:317 | PrintLogHistoryStore._read +1 | `self.fram.get_buffer` at :317, :345; narrow except MemoryError | what the callee raises | transitive | the callee's own rows here |
| asy_print_log.py:318 | PrintLogHistoryStore._read +1 | `buf.get_data_buf` at :318, :346; narrow except MemoryError | what the callee raises | transitive | the callee's own rows here |
| asy_print_log.py:321 | PrintLogHistoryStore._read | `self.fram.read_into` at :321; narrow except MemoryError | what the callee raises | transitive | the callee's own rows here |
| asy_print_log.py:326 | PrintLogHistoryStore._read | `struct.unpack_from` at :326, :327; narrow except MemoryError | ValueError/TypeError on a bad format or short buffer (py/modstruct.c) | open | format and buffer size proof |
| asy_print_log.py:353 | PrintLogHistoryStore._write | `self._pack_reset` at :353; narrow except MemoryError | what the callee raises | transitive | the callee's own rows here |
| asy_print_log.py:354 | PrintLogHistoryStore._write | `bool` at :354; narrow except MemoryError | TypeError/ValueError on unsupported operands (py/modbuiltins.c, py/obj.c) | open | operand-type proof |
| asy_print_log.py:354 | PrintLogHistoryStore._write | `self.fram.write_into` at :354; narrow except MemoryError | what the callee raises | transitive | the callee's own rows here |
| asy_print_log.py:366 | PrintLogHistoryStore.reset | `self._paused` at :366, :381 | not classified | open | - |
| asy_print_log.py:405 | PrintLogHistoryStore.setup | `self.err_s` at :405, :412, :435 | what the callee raises | transitive | the callee's own rows here |
| asy_print_log.py:407 | PrintLogHistoryStore.setup | `self._read` at :407 | what the callee raises | transitive | the callee's own rows here |
| asy_print_log.py:418 | PrintLogHistoryStore.setup | `self.history.extend` at :418, :423, :424 | not classified | open | - |
| asy_print_log.py:422 | PrintLogHistoryStore.setup | `list` at :422 | MemoryError (py/gc.c gc_alloc via m_malloc_fail) | open | setup-only or run-time allocation decides (I.4) |
| asy_print_log.py:451 | <module> | `namedtuple` at :451 | not classified | open | - |
| asy_print_log.py:453 | <module> | `LogConfig` at :453 | not classified | open | - |
| asy_print_log.py:474 | make_logger | `PrintLogHistory` at :474 | not classified | open | - |
| asy_print_log.py:475 | make_logger | `pr.one` at :475, :478 | what the callee raises | transitive | the callee's own rows here |
| asy_print_log.py:477 | make_logger | `PrintLogHistoryStore` at :477 | not classified | open | - |
| asy_system_service.py:51 | <module> | `const` at :51, :52, :53, :54, :55, :56, :57, :58, :59, :60, :61, :64 (+36) | nothing at run time | unreachable | folded at compile time (py/compile.c, MICROPY_COMP_CONST) |
| asy_system_service.py:139 | _write_region +2 | `mem_backup` at :139, :153, :154, :176, :177 | not classified | open | - |
| asy_system_service.py:161 | begin_boot | `reset_cause` at :161 | not classified | open | - |
| asy_system_service.py:167 | begin_boot | `range` at :167 | TypeError/ValueError on unsupported operands (py/modbuiltins.c, py/obj.c) | open | operand-type proof |
| asy_system_service.py:167 | begin_boot +2 | `len` at :167, :769, :778, :788, :799 | TypeError/ValueError on unsupported operands (py/modbuiltins.c, py/obj.c) | open | operand-type proof |
| asy_system_service.py:169 | begin_boot +2 | `_write_region` at :169, :185, :688 | what the callee raises | transitive | the callee's own rows here |
| asy_system_service.py:180 | record_loop_end +2 | `write_reset_record` at :180, :357, :373, :409 | what the callee raises | transitive | the callee's own rows here |
| asy_system_service.py:200 | SystemService.__init__ | `make_logger` at :200 | what the callee raises | transitive | the callee's own rows here |
| asy_system_service.py:206 | SystemService.__init__ | `TickSeconds` at :206 | not classified | open | - |
| asy_system_service.py:207 | SystemService.__init__ | `asyncio.ThreadSafeFlag` at :207, :213, :239 | MemoryError (py/gc.c gc_alloc via m_malloc_fail) | open | setup-only or run-time allocation decides (I.4) |
| asy_system_service.py:208 | SystemService.__init__ | `Timer` at :208, :209, :212 | not classified | open | - |
| asy_system_service.py:217 | SystemService.__init__ | `LockedValue` at :217 | not classified | open | - |
| asy_system_service.py:230 | SystemService.__init__ | `ConfigManager` at :230 | not classified | open | - |
| asy_system_service.py:230 | SystemService.__init__ | `config_filename` at :230 | what the callee raises | transitive | the callee's own rows here |
| asy_system_service.py:230 | SystemService.__init__ | `instance_name` at :230 | what the callee raises | transitive | the callee's own rows here |
| asy_system_service.py:241 | SystemService.__init__ | `asyncio.Lock` at :241 | MemoryError (py/gc.c gc_alloc via m_malloc_fail) | open | setup-only or run-time allocation decides (I.4) |
| asy_system_service.py:245 | SystemService.__init__ | `asyncio.Event` at :245, :246 | MemoryError (py/gc.c gc_alloc via m_malloc_fail) | open | setup-only or run-time allocation decides (I.4) |
| asy_system_service.py:267 | SystemService._set_dict_cfg | `self.cfgmgr.write_config` at :267 | what the callee raises | transitive | the callee's own rows here |
| asy_system_service.py:269 | SystemService._set_dict_cfg | `dict.fromkeys` at :269 | MemoryError (py/gc.c gc_alloc via m_malloc_fail) | open | setup-only or run-time allocation decides (I.4) |
| asy_system_service.py:270 | SystemService._set_dict_cfg | `results.get` at :270 | not classified | open | - |
| asy_system_service.py:270 | SystemService._set_dict_cfg | `name_cfg` at :270 | what the callee raises | transitive | the callee's own rows here |
| asy_system_service.py:271 | SystemService._set_dict_cfg +1 | `self.cfgmgr.get_int_values` at :271, :758 | what the callee raises | transitive | the callee's own rows here |
| asy_system_service.py:273 | SystemService._set_dict_cfg +1 | `self._apply_level` at :273, :760 | what the callee raises | transitive | the callee's own rows here |
| asy_system_service.py:284 | SystemService._apply_level +8 | `report_if_fatal` at :284, :308, :327, :339, :426, :433, :496, :503, :615 | what the callee raises | transitive | the callee's own rows here |
| asy_system_service.py:285 | SystemService._apply_level +10 | `self.pr.err_s` at :285, :309, :325, :328, :330, :340, :427, :434, :497, :504, :514, :617 (+1) | what the callee raises | transitive | the callee's own rows here |
| asy_system_service.py:298 | SystemService._flush_config_stores +1 | `store.close_writes` at :298, :413 | what the callee raises | transitive | the callee's own rows here |
| asy_system_service.py:313 | SystemService._flush_config_stores | `step_done` at :313 | not classified | open | - |
| asy_system_service.py:321 | SystemService._log_dead_task +2 | `self._uptime.read` at :321, :521, :681 | what the callee raises | transitive | the callee's own rows here |
| asy_system_service.py:344 | SystemService._ntp_boot_signature | `utc_now` at :344 | what the callee raises | transitive | the callee's own rows here |
| asy_system_service.py:349 | SystemService._own_feed +1 | `self._watchdog.feed` at :349, :698 | not classified | open | - |
| asy_system_service.py:354 | SystemService._reboot +4 | `self.pr.evt` at :354, :359, :362, :397, :414, :436, :528, :709, :712 | what the callee raises | transitive | the callee's own rows here |
| asy_system_service.py:358 | SystemService._reboot | `self._flush_config_stores` at :358 | what the callee raises | transitive | the callee's own rows here |
| asy_system_service.py:361 | SystemService._reboot +2 | `self._storage_pause` at :361, :527, :710, :713 | not classified | open | - |
| asy_system_service.py:364 | SystemService._reboot +2 | `asyncio.create_task` at :364, :400, :805; narrow except MemoryError/OSError | MemoryError (py/gc.c gc_alloc via m_malloc_fail) | open | setup-only or run-time allocation decides (I.4) |
| asy_system_service.py:364 | SystemService._reboot | `self._reset_when_due` at :364; narrow except MemoryError/OSError | what the callee raises | transitive | the callee's own rows here |
| asy_system_service.py:366 | SystemService._reboot | `self._own_feed` at :366; narrow except MemoryError/OSError | what the callee raises | transitive | the callee's own rows here |
| asy_system_service.py:367 | SystemService._reboot | `self._reset_timer.init` at :367; narrow except MemoryError/OSError | not classified | open | - |
| asy_system_service.py:367 | SystemService._reboot | `self._reset_due.set` at :367; narrow except MemoryError/OSError | not classified | open | - |
| asy_system_service.py:372 | SystemService._reboot | `self._reset_task.cancel` at :372 | not classified | open | - |
| asy_system_service.py:377 | SystemService._reboot +1 | `self.pr.err` at :377, :403 | what the callee raises | transitive | the callee's own rows here |
| asy_system_service.py:391 | SystemService._request_shutdown | `self._storage.erase_ready` at :391 | what the callee raises | transitive | the callee's own rows here |
| asy_system_service.py:400 | SystemService._request_shutdown | `self._shutdown_sequence` at :400; narrow except MemoryError | what the callee raises | transitive | the callee's own rows here |
| asy_system_service.py:414 | SystemService._request_shutdown | `_purpose_name` at :414 | what the callee raises | transitive | the callee's own rows here |
| asy_system_service.py:516 | SystemService._status_loop +2 | `asyncio.sleep_ms` at :516, :778, :796 | not classified | open | - |
| asy_system_service.py:518 | SystemService._status_loop +1 | `arm_tick_timer` at :518, :631 | what the callee raises | transitive | the callee's own rows here |
| asy_system_service.py:520 | SystemService._status_loop | `self._uptime_event.wait` at :520 | not classified | open | - |
| asy_system_service.py:522 | SystemService._status_loop | `self.pr.all` at :522 | what the callee raises | transitive | the callee's own rows here |
| asy_system_service.py:523 | SystemService._status_loop +1 | `time.ticks_diff` at :523, :790 | TypeError only for a non-int argument | inherently safe | small-int arguments (extmod/modtime.c:150-196) |
| asy_system_service.py:523 | SystemService._status_loop +2 | `time.ticks_ms` at :523, :715, :787, :790 | TypeError only for a non-int argument | inherently safe | small-int arguments (extmod/modtime.c:150-196) |
| asy_system_service.py:531 | SystemService._status_loop | `self._ntp_boot_signature` at :531 | what the callee raises | transitive | the callee's own rows here |
| asy_system_service.py:533 | SystemService._status_loop | `self._boot_signature.set_value` at :533, :539 | what the callee raises | transitive | the callee's own rows here |
| asy_system_service.py:534 | SystemService._status_loop +1 | `self.pr.one` at :534, :540, :800 | what the callee raises | transitive | the callee's own rows here |
| asy_system_service.py:539 | SystemService._status_loop | `random.getrandbits` at :539 | not classified | open | - |
| asy_system_service.py:626 | SystemService.start_asy_status +1 | `asyncio.get_event_loop` at :626, :773 | not classified | open | - |
| asy_system_service.py:627 | SystemService.start_asy_status | `evtloop.create_task` at :627 | not classified | open | - |
| asy_system_service.py:627 | SystemService.start_asy_status | `self._status_loop` at :627 | what the callee raises | transitive | the callee's own rows here |
| asy_system_service.py:633 | SystemService.start_uptime_timer | `self._uptime_event.set` at :633 | not classified | open | - |
| asy_system_service.py:638 | SystemService.get_boot_signature | `self._boot_signature.get_value` at :638 | what the callee raises | transitive | the callee's own rows here |
| asy_system_service.py:653 | SystemService.get_dict_cfg | `self.cfgmgr.get_dict` at :653 | what the callee raises | transitive | the callee's own rows here |
| asy_system_service.py:653 | SystemService.get_dict_cfg | `schema_names` at :653 | what the callee raises | transitive | the callee's own rows here |
| asy_system_service.py:657 | SystemService.get_error_counter | `self.pr.get_log` at :657 | what the callee raises | transitive | the callee's own rows here |
| asy_system_service.py:691 | SystemService.erase_fram +3 | `self._request_shutdown` at :691, :719, :722, :732 | what the callee raises | transitive | the callee's own rows here |
| asy_system_service.py:706 | SystemService.pause_permanent_storage | `min` at :706 | TypeError/ValueError on unsupported operands (py/modbuiltins.c, py/obj.c) | open | operand-type proof |
| asy_system_service.py:706 | SystemService.pause_permanent_storage | `max` at :706 | TypeError/ValueError on unsupported operands (py/modbuiltins.c, py/obj.c) | open | operand-type proof |
| asy_system_service.py:715 | SystemService.pause_permanent_storage +1 | `time.ticks_add` at :715, :790 | TypeError only for a non-int argument | inherently safe | small-int arguments (extmod/modtime.c:150-196) |
| asy_system_service.py:729 | SystemService.reset_error_counter | `self.pr.reset` at :729 | what the callee raises | transitive | the callee's own rows here |
| asy_system_service.py:737 | SystemService.run_setups +1 | `gc.collect` at :737, :741, :770, :779 | not classified | open | - |
| asy_system_service.py:739 | SystemService.run_setups | `setup` at :739 | what the callee raises | transitive | the callee's own rows here |
| asy_system_service.py:740 | SystemService.run_setups | `self.feed_watchdog` at :740 | what the callee raises | transitive | the callee's own rows here |
| asy_system_service.py:747 | SystemService.setup | `self.pr.setup` at :747 | what the callee raises | transitive | the callee's own rows here |
| asy_system_service.py:749 | SystemService.setup | `self._level_setters_provider` at :749 | not classified | open | - |
| asy_system_service.py:751 | SystemService.setup | `self._config_stores_provider` at :751 | not classified | open | - |
| asy_system_service.py:752 | SystemService.setup | `self.cfgmgr.setup` at :752 | what the callee raises | transitive | the callee's own rows here |
| asy_system_service.py:756 | SystemService.setup | `self.pr.wrn_s` at :756 | what the callee raises | transitive | the callee's own rows here |
| asy_system_service.py:774 | SystemService.start_tasks | `loop.get_exception_handler` at :774 | not classified | open | - |
| asy_system_service.py:775 | SystemService.start_tasks | `loop.set_exception_handler` at :775 | not classified | open | - |
| asy_system_service.py:776 | SystemService.start_tasks +1 | `enumerate` at :776, :785, :789 | TypeError/ValueError on unsupported operands (py/modbuiltins.c, py/obj.c) | open | operand-type proof |
| asy_system_service.py:777 | SystemService.start_tasks | `self._start_task` at :777 | what the callee raises | transitive | the callee's own rows here |
| asy_system_service.py:786 | SystemService.start_timers | `self._run_timer_starter` at :786, :799 | what the callee raises | transitive | the callee's own rows here |
| asy_system_service.py:793 | SystemService.start_timers | `self._sequencer_timer.init` at :793; narrow except MemoryError/OSError | not classified | open | - |
| asy_system_service.py:793 | SystemService.start_timers | `self._sequencer_flag.set` at :793; narrow except MemoryError/OSError | not classified | open | - |
| asy_system_service.py:798 | SystemService.start_timers | `self._sequencer_flag.wait` at :798 | not classified | open | - |
| asy_system_service.py:805 | SystemService.supervise_tasks | `self._supervise` at :805 | what the callee raises | transitive | the callee's own rows here |
| asy_system_service.py:807 | SystemService.supervise_tasks | `self._never.wait` at :807 | not classified | open | - |
| asy_system_service.py:809 | SystemService.supervise_tasks | `self._supervisor_task.cancel` at :809 | not classified | open | - |
| asy_fram_manager.py:30 | <module> | `const` at :30, :31, :32, :33, :34, :35, :36, :37, :38, :39, :42, :43 (+18) | nothing at run time | unreachable | folded at compile time (py/compile.c, MICROPY_COMP_CONST) |
| asy_fram_manager.py:71 | _owner_seed | `min` at :71 | TypeError/ValueError on unsupported operands (py/modbuiltins.c, py/obj.c) | open | operand-type proof |
| asy_fram_manager.py:71 | _owner_seed +2 | `crc.length` at :71, :688, :739 | not classified | open | - |
| asy_fram_manager.py:75 | _owner_seed | `owner.encode` at :75 | not classified | open | - |
| asy_fram_manager.py:97 | _FRAMBaseChunk.__init__ +5 | `self.crc.length` at :97, :195, :216, :372, :477, :545 | not classified | open | - |
| asy_fram_manager.py:99 | _FRAMBaseChunk.__init__ | `asyncio.Lock` at :99 | MemoryError (py/gc.c gc_alloc via m_malloc_fail) | open | setup-only or run-time allocation decides (I.4) |
| asy_fram_manager.py:103 | _FRAMBaseChunk.__init__ +3 | `bytearray` at :103, :104, :107, :488, :558, :783; narrow except MemoryError/OverflowError | MemoryError (py/gc.c gc_alloc via m_malloc_fail) | open | setup-only or run-time allocation decides (I.4) |
| asy_fram_manager.py:111 | _FRAMBaseChunk.__init__ +1 | `console` at :111, :785 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_manager.py:113 | _FRAMBaseChunk.__init__ +2 | `memoryview` at :113, :184, :525 | MemoryError (py/gc.c gc_alloc via m_malloc_fail) | open | setup-only or run-time allocation decides (I.4) |
| asy_fram_manager.py:128 | _FRAMBaseChunk._set_check_sb | `fram.get_values_sync` at :128 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_manager.py:130 | _FRAMBaseChunk._set_check_sb | `fram.report_get_values` at :130 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_manager.py:131 | _FRAMBaseChunk._set_check_sb +15 | `self.pr.err_s` at :131, :137, :144, :170, :178, :203, :217, :240, :255, :262, :330, :373 (+16) | what the callee raises | transitive | the callee's own rows here |
| asy_fram_manager.py:140 | _FRAMBaseChunk._set_check_sb +1 | `fram.set_values_sync` at :140, :790 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_manager.py:143 | _FRAMBaseChunk._set_check_sb | `fram.report_set_values` at :143 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_manager.py:152 | _FRAMBaseChunk._blank_verdict | `self.fram.verify_present` at :152 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_manager.py:152 | _FRAMBaseChunk._blank_verdict +6 | `self.fram.lost.is_set` at :152, :210, :366, :438, :454, :665, :801 | not classified | open | - |
| asy_fram_manager.py:169 | _FRAMBaseChunk._clear_chunk +5 | `report_if_fatal` at :169, :329, :424, :583, :618, :819 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_manager.py:186 | _FRAMBaseChunk._compare_with +1 | `self._read_chunk` at :186, :343 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_manager.py:196 | _FRAMBaseChunk._handle_status_bytes | `self._set_check_sb` at :196, :199 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_manager.py:213 | _FRAMBaseChunk._read +2 | `self._mempause` at :213, :369, :441 | not classified | open | - |
| asy_fram_manager.py:214 | _FRAMBaseChunk._read +2 | `self.pr.wrn_s` at :214, :224, :226, :232, :234, :251, :253, :370, :442 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_manager.py:216 | _FRAMBaseChunk._read +4 | `len` at :216, :217, :372, :373, :388, :444, :503, :503, :504, :504, :506, :601 (+4) | TypeError/ValueError on unsupported operands (py/modbuiltins.c, py/obj.c) | open | operand-type proof |
| asy_fram_manager.py:219 | _FRAMBaseChunk._read | `self._read_into` at :219, :227 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_manager.py:222 | _FRAMBaseChunk._read +7 | `self.pr.evt` at :222, :230, :249, :387, :393, :433, :448, :576, :578, :590, :625, :630 (+2) | what the callee raises | transitive | the callee's own rows here |
| asy_fram_manager.py:236 | _FRAMBaseChunk._read | `self._blank_verdict` at :236 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_manager.py:237 | _FRAMBaseChunk._read +1 | `self.pr.all` at :237, :242, :244, :257, :264, :375 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_manager.py:239 | _FRAMBaseChunk._read +1 | `self._write_chunk` at :239, :254, :376, :380 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_manager.py:245 | _FRAMBaseChunk._read +1 | `self._compare_with` at :245, :389 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_manager.py:332 | _FRAMBaseChunk._read_chunk | `self._read_progress` at :332 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_manager.py:361 | _FRAMBaseChunk._read_progress +3 | `range` at :361, :388, :444, :788 | TypeError/ValueError on unsupported operands (py/modbuiltins.c, py/obj.c) | open | operand-type proof |
| asy_fram_manager.py:445 | _FRAMBaseChunk.clear | `self._clear_chunk` at :445 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_manager.py:459 | _FRAMBaseChunk.invalidate | `self._handle_status_bytes` at :459 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_manager.py:472 | FRAMChunkBuffer.__init__ +2 | `super` at :472, :472, :520, :520, :540, :540 | TypeError/ValueError on unsupported operands (py/modbuiltins.c, py/obj.c) | open | operand-type proof |
| asy_fram_manager.py:477 | FRAMChunk.get_buffer | `FRAMChunkBuffer` at :477 | not classified | open | - |
| asy_fram_manager.py:480 | FRAMChunk.read +3 | `self.get_buffer` at :480, :498, :549, :596 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_manager.py:481 | FRAMChunk.read +1 | `self.read_into` at :481, :550 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_manager.py:483 | FRAMChunk.read +3 | `buf.get_data_buf` at :483, :499, :553, :597 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_manager.py:491 | FRAMChunk.read_into +3 | `buf.get_buf` at :491, :511, :561, :636 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_manager.py:495 | FRAMChunk.read_into +1 | `self._read` at :495, :565 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_manager.py:508 | FRAMChunk.write +1 | `self.write_into` at :508, :606 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_manager.py:515 | FRAMChunk.write_into +1 | `self._write` at :515, :641 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_manager.py:540 | FRAMTimestampedChunk.__init__ +2 | `struct.calcsize` at :540, :545, :545, :739 | ValueError/TypeError on a bad format or short buffer (py/modstruct.c) | open | format and buffer size proof |
| asy_fram_manager.py:544 | FRAMTimestampedChunk.get_buffer | `FRAMChunkTimestampedBuffer` at :544 | not classified | open | - |
| asy_fram_manager.py:569 | FRAMTimestampedChunk.read_into +1 | `buf.get_ts_buf` at :569, :631 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_manager.py:574 | FRAMTimestampedChunk.read_into | `int` at :574 | TypeError/ValueError on unsupported operands (py/modbuiltins.c, py/obj.c) | open | operand-type proof |
| asy_fram_manager.py:574 | FRAMTimestampedChunk.read_into | `struct.unpack_from` at :574 | ValueError/TypeError on a bad format or short buffer (py/modstruct.c) | open | format and buffer size proof |
| asy_fram_manager.py:586 | FRAMTimestampedChunk.read_into +1 | `utc_now` at :586, :621 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_manager.py:635 | FRAMTimestampedChunk.write_into | `struct.pack_into` at :635 | ValueError/TypeError on a bad format or short buffer (py/modstruct.c) | open | format and buffer size proof |
| asy_fram_manager.py:649 | FRAMManager.__init__ | `PrintLogHistory` at :649 | not classified | open | - |
| asy_fram_manager.py:657 | FRAMManager.__init__ | `FRAM_SPI` at :657 | not classified | open | - |
| asy_fram_manager.py:663 | FRAMManager._watch_chip_loop +3 | `self.pr.err` at :663, :685, :698, :736, :749, :773, :780, :792 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_manager.py:666 | FRAMManager._watch_chip_loop | `self.setup` at :666 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_manager.py:668 | FRAMManager._watch_chip_loop +2 | `self.pr.one` at :668, :690, :703, :741, :757 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_manager.py:669 | FRAMManager._watch_chip_loop | `self.fram.lost.wait` at :669 | not classified | open | - |
| asy_fram_manager.py:678 | FRAMManager.start_asy_watch_chip | `asyncio.get_event_loop` at :678 | not classified | open | - |
| asy_fram_manager.py:679 | FRAMManager.start_asy_watch_chip | `evtloop.create_task` at :679 | not classified | open | - |
| asy_fram_manager.py:679 | FRAMManager.start_asy_watch_chip | `self._watch_chip_loop` at :679 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_manager.py:687 | FRAMManager.get_chunk +1 | `CRCPass` at :687, :738 | not classified | open | - |
| asy_fram_manager.py:700 | FRAMManager.get_chunk | `FRAMChunk` at :700 | not classified | open | - |
| asy_fram_manager.py:700 | FRAMManager.get_chunk +1 | `_owner_seed` at :700, :753 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_manager.py:701 | FRAMManager.get_chunk +1 | `self._chunks.append` at :701, :755 | not classified | open | - |
| asy_fram_manager.py:711 | FRAMManager.get_error_counter | `self.pr.get_log` at :711 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_manager.py:752 | FRAMManager.get_timestamped_chunk | `FRAMTimestampedChunk` at :752 | not classified | open | - |
| asy_fram_manager.py:772 | FRAMManager.erase_chip | `self.erase_ready` at :772 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_manager.py:777 | FRAMManager.erase_chip | `chunk.invalidate` at :777 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_manager.py:778 | FRAMManager.erase_chip +1 | `step_done` at :778, :794, :809 | not classified | open | - |
| asy_fram_manager.py:787 | FRAMManager.erase_chip | `self.fram.get_size` at :787 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_manager.py:791 | FRAMManager.erase_chip | `self.fram.report_set_values` at :791 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_manager.py:795 | FRAMManager.erase_chip | `asyncio.sleep` at :795 | MemoryError (py/gc.c gc_alloc via m_malloc_fail) | open | setup-only or run-time allocation decides (I.4) |
| asy_fram_manager.py:801 | FRAMManager.erase_ready | `self.fram.is_ready` at :801 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_manager.py:801 | FRAMManager.erase_ready | `self.fram.get_write_protected` at :801 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_manager.py:806 | FRAMManager.quiesce | `self.set_pause` at :806 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_manager.py:808 | FRAMManager.quiesce | `chunk.wait_idle` at :808 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_manager.py:812 | FRAMManager.reset_error_counter | `self.pr.reset` at :812 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_manager.py:815 | FRAMManager.setup | `self.pr.setup` at :815 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_driver.py:38 | <module> | `const` at :38, :39, :49, :50, :51, :56, :57, :58, :59, :63, :64, :65 (+33) | nothing at run time | unreachable | folded at compile time (py/compile.c, MICROPY_COMP_CONST) |
| asy_fram_driver.py:132 | FRAM_SPI.__init__ +2 | `super` at :132, :132, :157, :157, :175, :175 | TypeError/ValueError on unsupported operands (py/modbuiltins.c, py/obj.c) | open | operand-type proof |
| asy_fram_driver.py:134 | FRAM_SPI.__init__ | `SPIDevice` at :134 | not classified | open | - |
| asy_fram_driver.py:139 | FRAM_SPI.__init__ | `Pin` at :139 | not classified | open | - |
| asy_fram_driver.py:142 | FRAM_SPI.__init__ | `bytearray` at :142, :143, :144, :144, :145 | MemoryError (py/gc.c gc_alloc via m_malloc_fail) | open | setup-only or run-time allocation decides (I.4) |
| asy_fram_driver.py:151 | FRAM_SPI.__init__ | `asyncio.Event` at :151 | MemoryError (py/gc.c gc_alloc via m_malloc_fail) | open | setup-only or run-time allocation decides (I.4) |
| asy_fram_driver.py:161 | FRAM_SPI.__aenter__ +1 | `self.session_lock.release` at :161, :507 | not classified | open | - |
| asy_fram_driver.py:172 | FRAM_SPI.__aexit__ | `self._bus_lock.release` at :172; narrow except RuntimeError | not classified | open | - |
| asy_fram_driver.py:174 | FRAM_SPI.__aexit__ | `report_if_fatal` at :174 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_driver.py:180 | FRAM_SPI._is_write_protected +2 | `bool` at :180, :307, :466 | TypeError/ValueError on unsupported operands (py/modbuiltins.c, py/obj.c) | open | operand-type proof |
| asy_fram_driver.py:180 | FRAM_SPI._is_write_protected +1 | `self._wp_pin.value` at :180, :189, :197, :201 | not classified | open | - |
| asy_fram_driver.py:185 | FRAM_SPI._set_write_protected +1 | `self._enable_write` at :185, :314 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_driver.py:192 | FRAM_SPI._set_write_protected +2 | `self._send_command` at :192, :232, :235, :242, :245 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_driver.py:193 | FRAM_SPI._set_write_protected +2 | `self._read_status` at :193, :307, :465 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_driver.py:194 | FRAM_SPI._set_write_protected +1 | `self._disable_write` at :194, :318 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_driver.py:205 | FRAM_SPI._check_device_id | `_KNOWN_PRODUCT_IDS.get` at :205 | not classified | open | - |
| asy_fram_driver.py:207 | FRAM_SPI._check_device_id | `ValueError` at :207 | not classified | open | - |
| asy_fram_driver.py:208 | FRAM_SPI._check_device_id +2 | `self._send_and_read` at :208, :249, :252 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_driver.py:223 | FRAM_SPI._check_write_anomaly +2 | `self._check_device_id` at :223, :462, :502 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_driver.py:233 | FRAM_SPI._disable_write +1 | `self._wel_is_set` at :233, :236, :243, :246 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_driver.py:249 | FRAM_SPI._read_address +1 | `self._setup_addr_buffer` at :249, :317 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_driver.py:258 | FRAM_SPI._report_chip_lost +6 | `self.pr.err_s` at :258, :347, :378, :387, :395, :406, :410, :412, :414, :426, :429, :432 (+5) | what the callee raises | transitive | the callee's own rows here |
| asy_fram_driver.py:259 | FRAM_SPI._report_chip_lost | `self.lost.set` at :259 | not classified | open | - |
| asy_fram_driver.py:263 | FRAM_SPI._send_and_read +2 | `spidev.session_begin` at :263, :272, :286 | not classified | open | - |
| asy_fram_driver.py:265 | FRAM_SPI._send_and_read +2 | `spidev.write_sync` at :265, :274, :275, :288 | not classified | open | - |
| asy_fram_driver.py:266 | FRAM_SPI._send_and_read | `spidev.readinto_sync` at :266 | not classified | open | - |
| asy_fram_driver.py:268 | FRAM_SPI._send_and_read +2 | `spidev.session_end` at :268, :277, :290 | not classified | open | - |
| asy_fram_driver.py:296 | FRAM_SPI._setup_addr_buffer +2 | `len` at :296, :338, :370 | TypeError/ValueError on unsupported operands (py/modbuiltins.c, py/obj.c) | open | operand-type proof |
| asy_fram_driver.py:310 | FRAM_SPI._write +1 | `self._is_write_protected` at :310, :349 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_driver.py:317 | FRAM_SPI._write | `self._send_and_write` at :317 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_driver.py:324 | FRAM_SPI.get_values | `self.get_values_sync` at :324 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_driver.py:325 | FRAM_SPI.get_values +4 | `asyncio.sleep` at :325, :357, :382, :467, :503 | MemoryError (py/gc.c gc_alloc via m_malloc_fail) | open | setup-only or run-time allocation decides (I.4) |
| asy_fram_driver.py:326 | FRAM_SPI.get_values | `self.report_get_values` at :326 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_driver.py:334 | FRAM_SPI.get_values_sync +1 | `self.session_lock.locked` at :334, :365 | not classified | open | - |
| asy_fram_driver.py:340 | FRAM_SPI.get_values_sync | `self._read_address` at :340 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_driver.py:356 | FRAM_SPI.set_values | `self.set_values_sync` at :356 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_driver.py:358 | FRAM_SPI.set_values | `self.report_set_values` at :358 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_driver.py:372 | FRAM_SPI.set_values_sync +1 | `self._check_write_anomaly` at :372, :381 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_driver.py:372 | FRAM_SPI.set_values_sync | `self._write` at :372 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_driver.py:381 | FRAM_SPI.set_write_protected | `self._set_write_protected` at :381 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_driver.py:384 | FRAM_SPI.set_write_protected +2 | `self._report_chip_lost` at :384, :423, :509 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_driver.py:390 | FRAM_SPI.set_write_protected +2 | `self.pr.wrn_s` at :390, :398, :440, :443, :448, :471 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_driver.py:393 | FRAM_SPI.set_write_protected +1 | `self.pr.evt` at :393, :399, :446 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_driver.py:453 | FRAM_SPI.setup | `self._spidev.setup` at :453 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_driver.py:455 | FRAM_SPI.setup | `OSError` at :455, :469 | not classified | open | - |
| asy_fram_driver.py:474 | FRAM_SPI.setup | `hex` at :474 | not classified | open | - |
| asy_fram_driver.py:478 | FRAM_SPI.setup | `self._wp_pin.init` at :478 | not classified | open | - |
| asy_fram_driver.py:481 | FRAM_SPI.setup | `self.lost.clear` at :481 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_driver.py:482 | FRAM_SPI.setup | `self.pr.one` at :482 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_driver.py:493 | FRAM_SPI.verify_present | `asyncio.wait_for_ms` at :493; narrow except TimeoutError | not classified | open | - |
| asy_fram_driver.py:493 | FRAM_SPI.verify_present | `self.session_lock.acquire` at :493; narrow except TimeoutError | not classified | open | - |
| math_helpers.py:16 | <module> | `const` at :16, :17, :18, :19, :20, :21, :22, :23, :24, :25, :26, :27 (+18) | nothing at run time: the parser folds `_X = const(v)` (py/parse.c:832-866); a non-constant value is a SyntaxError at compile time (:842) | unreachable | no call is left at run time: each const() is replaced by its value while parsing (py/parse.c:864, MICROPY_COMP_CONST) and the underscore names are dropped from the module (:855-858); the frozen build parses them in mpy-cross, so a bad value fails the build, never a boot |
| math_helpers.py:70 | abs_humidity | `math.pow` at :70; narrow except ArithmeticError/ValueError | ValueError when finite arguments give a non-finite result (math_generic_2, py/modmath.c:53-60, math_error :40-42); TypeError for a non-number (py/obj.c:414) | handled | the ValueError (and an OverflowError, an ArithmeticError) is caught by math_helpers.py:71's except (ArithmeticError, ValueError), which returns None: the never-raise residual E.5.1 keeps on rp2's single-precision float; TypeError cannot occur: both arguments are float arithmetic on `temperature`, a `float | None` the gate at :61 has compared |
| math_helpers.py:84 | cct_mccamy | `abs` at :84 | TypeError for an operand with no abs (mp_unary_op, py/modbuiltins.c:91-93) | unreachable | `denominator` is `0.1858 - chroma_y`, a float: chroma_y is the `float | None` the gate at :81 compared, None excluded at :79; abs() of a float is a float |
| math_helpers.py:120 | dew_point | `math.log` at :120; narrow except ArithmeticError/ValueError | ValueError for an argument <= 0 or a non-finite result (mp_math_log, py/modmath.c:261-272); TypeError for a non-number (py/obj.c:414) | handled | caught by math_helpers.py:123's except (ArithmeticError, ValueError), which returns None; the gate at :111 bounds humidity to 0.1-100, so the argument is 0.001-1 and the catch stays as the residual guard E.5.1 keeps; TypeError cannot occur (humidity is the compared `float | None`) |
| math_helpers.py:131 | ema_step | `math.isfinite` at :131, :135 | TypeError for a non-number (MATH_FUN_1_TO_BOOL calls mp_obj_get_float, py/modmath.c:69-71, py/obj.c:414); it returns a bool, so it allocates nothing | unreachable | :131's argument is `sample` after its `is None` test on the same line and :135's is `previous` after its own: both the `float | None` of the signature, so mp_obj_get_float always converts |
| math_helpers.py:149 | pressure_at_height | `math.exp` at :149; narrow except ArithmeticError/ValueError | ValueError when a finite argument gives an infinite result (math_generic_1, py/modmath.c:44-51, math_error :40-42); TypeError for a non-number (py/obj.c:414) | handled | caught by math_helpers.py:150's except (ArithmeticError, ValueError), which returns None (the residual E.5.1 keeps); TypeError cannot occur: the argument is float arithmetic on dh and tmean, compared by the gate at :145 |
| math_helpers.py:169 | rel_humidity | `math.pow` at :169; narrow except ArithmeticError/ValueError | ValueError when finite arguments give a non-finite result (py/modmath.c:53-60); TypeError for a non-number (py/obj.c:414) | handled | caught by math_helpers.py:170's except (ArithmeticError, ValueError), which returns None (the residual E.5.1 keeps); TypeError cannot occur: the arguments are float arithmetic on `temperature`, compared by the gate at :160 |
| math_helpers.py:185 | rgb_to_hsb | `max` at :185 | TypeError when two arguments do not compare (mp_builtin_min_max's many-args arm, py/modbuiltins.c:274-285); with three positional arguments the empty-sequence ValueError (:266) is the one-argument arm's only | unreachable | the three arguments are the `float | None` triple the gate at :183 compared (None excluded at :181), and float compares with float; it returns one of its arguments, so it allocates nothing |
| math_helpers.py:186 | rgb_to_hsb | `min` at :186 | TypeError when two arguments do not compare (py/modbuiltins.c:274-285) | unreachable | as max at :185: the same compared float triple; it returns one of its arguments |
| math_helpers.py:224 | wet_bulb_temperature | `math.atan` at :224, :225, :226, :227; narrow except ArithmeticError/ValueError | ValueError only for a non-finite result from a finite argument (py/modmath.c:44-51), which atan never gives; TypeError for a non-number (py/obj.c:414) | handled | all four calls sit in the try whose except (ArithmeticError, ValueError) at math_helpers.py:230 returns None; atan of a finite float is finite and every argument is float arithmetic on the compared temperature and humidity (gate :218) |
| math_helpers.py:224 | wet_bulb_temperature | `math.sqrt` at :224, :227; narrow except ArithmeticError/ValueError | ValueError for a negative argument (a NaN result from a finite argument, py/modmath.c:44-51); TypeError for a non-number (py/obj.c:414) | handled | both calls sit in the try whose except (ArithmeticError, ValueError) at math_helpers.py:230 returns None; the gate at :218 bounds humidity to 5-99, so both arguments (humidity + 8.313659 and humidity) are positive |
