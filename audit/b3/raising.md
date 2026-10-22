# Raising calls in the never-raise modules (M.PROC.025, A.U35.36)

Requirement: per never-raise module an `ast` walk lists every call outside a `try` that catches it and every `raise`, each classified from the pinned source as handled (the catching `except`), unreachable (with the proof, an E.5.1 verdict) or a defect (fixed at the right layer with a test injecting the raise and asserting the sentinel). Completion: no row left unclassified. A defect any file records goes the OR12.a path (fixed with a regression test seen failing first, or an owner question), never a note alone, and passes A-C as a delta before it is applied (OR106.a). The file is complete when every row is terminal: biting, fixed, or justified with its reason. Opened by A.U35.01 / M.PROC.022 (agent, 2026-10-22); deleted with `audit/` at phase D.

## Walk summary

Walked over `src/` as of `b1bf1f3` by `audit/b3/raising_walk.py` (agent, 2026-10-22). Re-run it on the integration head: lanes P
and Y edit four of these modules in U35. A row left "open" needs its per-site proof from the pinned source in the B3 campaign.

Sites per module (call or raise) by the `try` enclosing them: inside one catching `Exception` (broad), inside one
catching named classes only (narrow), or none. Broad sites are handled by construction; the rows below are the rest.

| module | calls broad | calls narrow | calls none | raises |
|---|---|---|---|---|
| asy_base_classes.py | 16 | 4 | 164 | 1 |
| asy_config_manager.py | 7 | 30 | 132 | 0 |
| asy_print_log.py | 2 | 15 | 108 | 0 |
| asy_system_service.py | 53 | 9 | 198 | 0 |
| asy_fram_manager.py | 45 | 2 | 244 | 0 |
| asy_fram_driver.py | 1 | 3 | 165 | 4 |
| math_helpers.py | 0 | 10 | 35 | 0 |

Rows outside a broad `try`, by verdict: inherently safe 12, open 414, transitive 487, unreachable 206.

## Raises

| module:line | function | call or raise | can raise (pinned source) | verdict | proof or action |
|---|---|---|---|---|---|
| asy_base_classes.py:364 | _checked_write_results | `raise TypeError('_set_mgr_cfg returned a non-dict result')` | the raise itself | handled | both callers sit in a try catching Exception: asy_base_classes.py:507 (except :508) and :689 (except :690); the raise is that try's logged failure, as its comment says |
| asy_fram_driver.py:158 | FRAM_SPI.__aenter__ | `raise` | the raise itself | inherently safe | cleanup then re-raise: a BaseException (a cancel) while waiting for the bus lock releases the session lock first; a cancellation must propagate |
| asy_fram_driver.py:203 | FRAM_SPI._check_device_id | `raise ValueError(f"FRAM max_size {self._max_size:#x} has no known product ID to verify against -` | the raise itself | exempt (setup) | one-time identification error, outside M.PROC.025's scope; reached from FRAM_SPI.setup(), whose one caller asy_fram_manager.py:795 sits in a try catching Exception (except :796) |
| asy_fram_driver.py:447 | FRAM_SPI.setup | `raise OSError('SPI bus not initialized')` | the raise itself | exempt (setup) | one-time setup error, outside M.PROC.025's scope; the one caller asy_fram_manager.py:795 sits in a try catching Exception (except :796) |
| asy_fram_driver.py:461 | FRAM_SPI.setup | `raise OSError('FRAM SPI device not found')` | the raise itself | exempt (setup) | one-time setup error, outside M.PROC.025's scope; the one caller asy_fram_manager.py:795 sits in a try catching Exception (except :796) |

## Calls outside a broad try (grouped by module and callee)

| module:line | function | call or raise | can raise (pinned source) | verdict | proof or action |
|---|---|---|---|---|---|
| asy_base_classes.py:32 | <module> | `TypeVar` at :32 | not classified | open | - |
| asy_base_classes.py:67 | <module> | `namedtuple` at :67 | not classified | open | - |
| asy_base_classes.py:70 | <module> | `const` at :70, :72, :74, :75, :78, :79, :80, :81, :82, :83, :84, :85 (+13) | nothing at run time | unreachable | folded at compile time (py/compile.c, MICROPY_COMP_CONST) |
| asy_base_classes.py:109 | Lockable.__init__ +1 | `asyncio.Lock` at :109, :416, :419 | MemoryError (py/gc.c gc_alloc via m_malloc_fail) | open | setup-only or run-time allocation decides (I.4) |
| asy_base_classes.py:112 | Lockable.__aenter__ | `self.session_lock.acquire` at :112 | not classified | open | - |
| asy_base_classes.py:124 | Lockable.__aexit__ | `self.session_lock.release` at :124; narrow except RuntimeError | not classified | open | - |
| asy_base_classes.py:126 | Lockable.__aexit__ +4 | `report_if_fatal` at :126, :451, :466, :497, :509, :537, :563, :675, :691 | what the callee raises | transitive | the callee's own rows here |
| asy_base_classes.py:134 | DeviceSession.__init__ +2 | `super` at :134, :134, :794, :794, :837, :837 | TypeError/ValueError on unsupported operands (py/modbuiltins.c, py/obj.c) | open | operand-type proof |
| asy_base_classes.py:153 | RegionBuffer.__init__ +1 | `bytearray` at :153, :175; narrow except MemoryError/OverflowError | MemoryError (py/gc.c gc_alloc via m_malloc_fail) | open | setup-only or run-time allocation decides (I.4) |
| asy_base_classes.py:156 | RegionBuffer.__init__ +1 | `console` at :156, :383 | what the callee raises | transitive | the callee's own rows here |
| asy_base_classes.py:165 | RegionBuffer.get_data_buf +2 | `memoryview` at :165, :189, :213 | MemoryError (py/gc.c gc_alloc via m_malloc_fail) | open | setup-only or run-time allocation decides (I.4) |
| asy_base_classes.py:175 | PieceBuffer.__init__ +4 | `min` at :175, :218, :232, :238, :355 | TypeError/ValueError on unsupported operands (py/modbuiltins.c, py/obj.c) | open | operand-type proof |
| asy_base_classes.py:175 | PieceBuffer.__init__ +2 | `range` at :175, :303, :306, :317 | TypeError/ValueError on unsupported operands (py/modbuiltins.c, py/obj.c) | open | operand-type proof |
| asy_base_classes.py:182 | PieceBuffer.copy_into +2 | `len` at :182, :186, :188, :203, :211, :216, :218, :218 | TypeError/ValueError on unsupported operands (py/modbuiltins.c, py/obj.c) | open | operand-type proof |
| asy_base_classes.py:184 | PieceBuffer.copy_into +1 | `divmod` at :184, :214 | TypeError/ValueError on unsupported operands (py/modbuiltins.c, py/obj.c) | open | operand-type proof |
| asy_base_classes.py:196 | PieceBuffer.pieces | `iter` at :196 | TypeError/ValueError on unsupported operands (py/modbuiltins.c, py/obj.c) | open | operand-type proof |
| asy_base_classes.py:204 | PieceBuffer.trim | `self._pieces.pop` at :204 | not classified | open | - |
| asy_base_classes.py:232 | LockedCounter.__init__ +2 | `max` at :232, :238, :355 | TypeError/ValueError on unsupported operands (py/modbuiltins.c, py/obj.c) | open | operand-type proof |
| asy_base_classes.py:233 | LockedCounter.__init__ +1 | `self._clamp` at :233, :244 | what the callee raises | transitive | the callee's own rows here |
| asy_base_classes.py:311 | HourlyWindowCounter.add +1 | `self._advance` at :311, :321 | what the callee raises | transitive | the callee's own rows here |
| asy_base_classes.py:338 | TickSeconds.__init__ +2 | `time.ticks_ms` at :338, :341, :357 | TypeError only for a non-int argument | inherently safe | small-int arguments (extmod/modtime.c:150-196) |
| asy_base_classes.py:342 | TickSeconds.read | `time.ticks_diff` at :342 | TypeError only for a non-int argument | inherently safe | small-int arguments (extmod/modtime.c:150-196) |
| asy_base_classes.py:363 | _checked_write_results | `isinstance` at :363 | TypeError/ValueError on unsupported operands (py/modbuiltins.c, py/obj.c) | open | operand-type proof |
| asy_base_classes.py:364 | _checked_write_results | `TypeError` at :364 | not classified | open | - |
| asy_base_classes.py:381 | arm_tick_timer | `timer.init` at :381; narrow except MemoryError/OSError | not classified | open | - |
| asy_base_classes.py:381 | arm_tick_timer | `flag.set` at :381; narrow except MemoryError/OSError | not classified | open | - |
| asy_base_classes.py:387 | arm_tick_timer | `pr.err` at :387 | what the callee raises | transitive | the callee's own rows here |
| asy_base_classes.py:411 | SensorReader.__init__ | `instance_name` at :411 | what the callee raises | transitive | the callee's own rows here |
| asy_base_classes.py:412 | SensorReader.__init__ | `make_logger` at :412 | what the callee raises | transitive | the callee's own rows here |
| asy_base_classes.py:442 | SensorReader._get_dict_cfg | `schema_names` at :442 | what the callee raises | transitive | the callee's own rows here |
| asy_base_classes.py:443 | SensorReader._get_dict_cfg +1 | `dict.fromkeys` at :443, :486, :517 | MemoryError (py/gc.c gc_alloc via m_malloc_fail) | open | setup-only or run-time allocation decides (I.4) |
| asy_base_classes.py:452 | SensorReader._get_dict_cfg +5 | `self.pr.err_s` at :452, :467, :498, :510, :538, :564, :584, :586, :676, :692, :720 | what the callee raises | transitive | the callee's own rows here |
| asy_base_classes.py:484 | SensorReader._set_dict_cfg | `self._writes_closed` at :484 | what the callee raises | transitive | the callee's own rows here |
| asy_base_classes.py:487 | SensorReader._set_dict_cfg | `schema_dict` at :487 | what the callee raises | transitive | the callee's own rows here |
| asy_base_classes.py:491 | SensorReader._set_dict_cfg | `fields.items` at :491 | not classified | open | - |
| asy_base_classes.py:492 | SensorReader._set_dict_cfg +1 | `check_cfg_get_default` at :492, :664 | what the callee raises | transitive | the callee's own rows here |
| asy_base_classes.py:523 | SensorReader._set_dict_cfg | `results.setdefault` at :523 | not classified | open | - |
| asy_base_classes.py:524 | SensorReader._set_dict_cfg | `data.items` at :524 | not classified | open | - |
| asy_base_classes.py:525 | SensorReader._set_dict_cfg | `results.get` at :525 | not classified | open | - |
| asy_base_classes.py:527 | SensorReader._set_dict_cfg | `self._push_callbacks.get` at :527 | not classified | open | - |
| asy_base_classes.py:528 | SensorReader._set_dict_cfg +1 | `fields.get` at :528, :661 | not classified | open | - |
| asy_base_classes.py:533 | SensorReader._set_dict_cfg +1 | `type_or_range_error` at :533, :682 | what the callee raises | transitive | the callee's own rows here |
| asy_base_classes.py:542 | SensorReader._set_dict_cfg | `self._recover_failed_push` at :542 | what the callee raises | transitive | the callee's own rows here |
| asy_base_classes.py:544 | SensorReader._set_dict_cfg | `self._commit_mgr_cfg` at :544 | what the callee raises | transitive | the callee's own rows here |
| asy_base_classes.py:567 | SensorReader._climb_ladder +2 | `self.pr.wrn_s` at :567, :606, :639, :642 | what the callee raises | transitive | the callee's own rows here |
| asy_base_classes.py:569 | SensorReader._climb_ladder +1 | `self._recover_bus` at :569, :571, :616 | what the callee raises | transitive | the callee's own rows here |
| asy_base_classes.py:580 | SensorReader._error_check | `any` at :580 | not classified | open | - |
| asy_base_classes.py:588 | SensorReader._error_check | `self._climb_ladder` at :588 | what the callee raises | transitive | the callee's own rows here |
| asy_base_classes.py:592 | SensorReader._error_check +2 | `self.pr.err` at :592, :696, :710 | what the callee raises | transitive | the callee's own rows here |
| asy_base_classes.py:604 | SensorReader._init_done | `bus.take_boot_clear_status` at :604 | not classified | open | - |
| asy_base_classes.py:624 | SensorReader._rearm_timer +1 | `self._timer_fault` at :624, :730 | what the callee raises | transitive | the callee's own rows here |
| asy_base_classes.py:626 | SensorReader._rearm_timer | `self.start_timer` at :626 | not classified | open | - |
| asy_base_classes.py:638 | SensorReader._recover_bus | `bus.clear` at :638 | what the callee raises | transitive | the callee's own rows here |
| asy_base_classes.py:641 | SensorReader._recover_bus | `bus.recover` at :641 | not classified | open | - |
| asy_base_classes.py:670 | SensorReader._recover_failed_push | `self._get_callbacks.get` at :670 | not classified | open | - |
| asy_base_classes.py:685 | SensorReader._recover_failed_push | `old_values.get` at :685 | not classified | open | - |
| asy_base_classes.py:694 | SensorReader._recover_failed_push | `res.get` at :694, :696 | not classified | open | - |
| asy_base_classes.py:703 | SensorReader._republish | `getattr` at :703 | TypeError/ValueError on unsupported operands (py/modbuiltins.c, py/obj.c) | open | operand-type proof |
| asy_base_classes.py:704 | SensorReader._republish | `type` at :704, :704 | TypeError/ValueError on unsupported operands (py/modbuiltins.c, py/obj.c) | open | operand-type proof |
| asy_base_classes.py:711 | SensorReader._timer_failed | `waiter.set` at :711 | not classified | open | - |
| asy_base_classes.py:726 | SensorReader._trigger_loop | `self._rearm_timer` at :726 | what the callee raises | transitive | the callee's own rows here |
| asy_base_classes.py:729 | SensorReader._trigger_loop | `self._base_trigger_event.wait` at :729 | not classified | open | - |
| asy_base_classes.py:733 | SensorReader._trigger_loop | `self._trigger_period.get_value` at :733 | what the callee raises | transitive | the callee's own rows here |
| asy_base_classes.py:735 | SensorReader._trigger_loop | `self._read_event.set` at :735 | not classified | open | - |
| asy_base_classes.py:747 | SensorReader.get_error_counter | `self.pr.get_log` at :747 | what the callee raises | transitive | the callee's own rows here |
| asy_base_classes.py:766 | SensorReader.reset_error_counter | `self.pr.reset` at :766 | what the callee raises | transitive | the callee's own rows here |
| asy_base_classes.py:770 | SensorReader.setup | `self.pr.setup` at :770 | what the callee raises | transitive | the callee's own rows here |
| asy_base_classes.py:776 | utc_now | `time.mktime` at :776 | not classified | open | - |
| asy_base_classes.py:776 | utc_now | `time.gmtime` at :776 | not classified | open | - |
| asy_base_classes.py:799 | SensorReaderConfig.__init__ | `LogConfig` at :799 | not classified | open | - |
| asy_base_classes.py:800 | SensorReaderConfig.__init__ | `ConfigManager` at :800 | not classified | open | - |
| asy_base_classes.py:800 | SensorReaderConfig.__init__ | `config_filename` at :800 | what the callee raises | transitive | the callee's own rows here |
| asy_base_classes.py:804 | SensorReaderConfig._get_mgr_cfg +1 | `self.pr.evt` at :804, :812 | what the callee raises | transitive | the callee's own rows here |
| asy_base_classes.py:807 | SensorReaderConfig._get_mgr_cfg | `self.cfgmgr.get_dict` at :807 | what the callee raises | transitive | the callee's own rows here |
| asy_base_classes.py:813 | SensorReaderConfig._set_mgr_cfg | `self.cfgmgr.write_config` at :813 | what the callee raises | transitive | the callee's own rows here |
| asy_base_classes.py:816 | SensorReaderConfig._commit_mgr_cfg | `self.cfgmgr.commit` at :816 | what the callee raises | transitive | the callee's own rows here |
| asy_base_classes.py:820 | SensorReaderConfig._writes_closed | `self.cfgmgr.writes_closed` at :820 | what the callee raises | transitive | the callee's own rows here |
| asy_base_classes.py:838 | SensorReaderConfig.setup | `self.cfgmgr.setup` at :838 | what the callee raises | transitive | the callee's own rows here |
| asy_config_manager.py:27 | <module> | `TypeVar` at :27 | not classified | open | - |
| asy_config_manager.py:55 | <module> | `const` at :55, :56, :57, :58, :59, :60, :61, :62, :63, :64, :65, :66 (+2) | nothing at run time | unreachable | folded at compile time (py/compile.c, MICROPY_COMP_CONST) |
| asy_config_manager.py:72 | _as_bool +11 | `type` at :72, :76, :82, :84, :96, :98, :112, :112, :113, :118, :162, :162 (+11); narrow except MemoryError | TypeError/ValueError on unsupported operands (py/modbuiltins.c, py/obj.c) | open | operand-type proof |
| asy_config_manager.py:88 | _coerce_float +1 | `float` at :88, :103 | TypeError/ValueError on unsupported operands (py/modbuiltins.c, py/obj.c) | open | operand-type proof |
| asy_config_manager.py:100 | _coerce_int | `int` at :100; narrow except OverflowError/ValueError | TypeError/ValueError on unsupported operands (py/modbuiltins.c, py/obj.c) | open | operand-type proof |
| asy_config_manager.py:113 | _special_bypass | `any` at :113 | not classified | open | - |
| asy_config_manager.py:129 | _stored_float | `json.loads` at :129 | OSError/MemoryError/ValueError/TypeError (extmod/modjson.c) | open | - |
| asy_config_manager.py:129 | _stored_float +1 | `json.dumps` at :129, :584; narrow except MemoryError/OSError | OSError/MemoryError/ValueError/TypeError (extmod/modjson.c) | open | - |
| asy_config_manager.py:142 | check_cfg_get_default +1 | `isinstance` at :142, :519, :531; narrow except MemoryError/OSError/ValueError | TypeError/ValueError on unsupported operands (py/modbuiltins.c, py/obj.c) | open | operand-type proof |
| asy_config_manager.py:145 | check_cfg_get_default +2 | `type_or_range_error` at :145, :211, :561 | what the callee raises | transitive | the callee's own rows here |
| asy_config_manager.py:154 | checked_float | `_coerce_float` at :154 | what the callee raises | transitive | the callee's own rows here |
| asy_config_manager.py:159 | checked_float +2 | `_special_bypass` at :159, :173, :302 | what the callee raises | transitive | the callee's own rows here |
| asy_config_manager.py:168 | checked_int | `_coerce_int` at :168 | what the callee raises | transitive | the callee's own rows here |
| asy_config_manager.py:184 | checked_numeric | `checked_int` at :184 | what the callee raises | transitive | the callee's own rows here |
| asy_config_manager.py:186 | checked_numeric | `checked_float` at :186 | what the callee raises | transitive | the callee's own rows here |
| asy_config_manager.py:203 | compare_before_write +2 | `schema_dict` at :203, :541, :613; narrow except MemoryError | what the callee raises | transitive | the callee's own rows here |
| asy_config_manager.py:206 | compare_before_write | `data.items` at :206 | not classified | open | - |
| asy_config_manager.py:207 | compare_before_write | `fields.get` at :207 | not classified | open | - |
| asy_config_manager.py:222 | compare_before_write | `resolution.get` at :222 | not classified | open | - |
| asy_config_manager.py:224 | compare_before_write | `res` at :224, :224 | not classified | open | - |
| asy_config_manager.py:259 | make_dict | `getattr` at :259 | TypeError/ValueError on unsupported operands (py/modbuiltins.c, py/obj.c) | open | operand-type proof |
| asy_config_manager.py:263 | name_cfg +2 | `schema_names` at :263, :348, :368; narrow except KeyError | what the callee raises | transitive | the callee's own rows here |
| asy_config_manager.py:264 | name_cfg +2 | `len` at :264, :305, :542 | TypeError/ValueError on unsupported operands (py/modbuiltins.c, py/obj.c) | open | operand-type proof |
| asy_config_manager.py:295 | type_or_range_error | `checked_numeric` at :295 | what the callee raises | transitive | the callee's own rows here |
| asy_config_manager.py:318 | ConfigManager.__init__ | `make_logger` at :318 | what the callee raises | transitive | the callee's own rows here |
| asy_config_manager.py:319 | ConfigManager.__init__ | `asyncio.Lock` at :319 | MemoryError (py/gc.c gc_alloc via m_malloc_fail) | open | setup-only or run-time allocation decides (I.4) |
| asy_config_manager.py:339 | ConfigManager.__init__ | `asyncio.Event` at :339 | MemoryError (py/gc.c gc_alloc via m_malloc_fail) | open | setup-only or run-time allocation decides (I.4) |
| asy_config_manager.py:340 | ConfigManager.__init__ +3 | `self._commit_ready.set` at :340, :469, :493, :657 | not classified | open | - |
| asy_config_manager.py:345 | ConfigManager._get_typed_values | `self._get_values` at :345 | what the callee raises | transitive | the callee's own rows here |
| asy_config_manager.py:350 | ConfigManager._get_typed_values | `enumerate` at :350 | TypeError/ValueError on unsupported operands (py/modbuiltins.c, py/obj.c) | open | operand-type proof |
| asy_config_manager.py:351 | ConfigManager._get_typed_values | `coerce` at :351 | not classified | open | - |
| asy_config_manager.py:353 | ConfigManager._get_typed_values +2 | `self._read_run_starts` at :353, :362, :370, :436, :444 | what the callee raises | transitive | the callee's own rows here |
| asy_config_manager.py:354 | ConfigManager._get_typed_values +5 | `self.pr.err_s` at :354, :363, :371, :419, :437, :445, :528, :543, :551, :590, :604, :619 (+5); narrow except MemoryError/OSError | what the callee raises | transitive | the callee's own rows here |
| asy_config_manager.py:356 | ConfigManager._get_typed_values | `typed.append` at :356 | not classified | open | - |
| asy_config_manager.py:365 | ConfigManager._get_values +1 | `self.pr.all` at :365, :439 | what the callee raises | transitive | the callee's own rows here |
| asy_config_manager.py:367 | ConfigManager._get_values +2 | `self._current` at :367, :441, :617, :645; narrow except KeyError/MemoryError | what the callee raises | transitive | the callee's own rows here |
| asy_config_manager.py:377 | ConfigManager._closed_for_reset +2 | `self.pr.evt` at :377, :485, :607, :637, :639, :660 | what the callee raises | transitive | the callee's own rows here |
| asy_config_manager.py:417 | ConfigManager._flush_staged | `report_if_fatal` at :417 | what the callee raises | transitive | the callee's own rows here |
| asy_config_manager.py:429 | ConfigManager.get_bool_values +3 | `self._get_typed_values` at :429, :454, :457, :460 | what the callee raises | transitive | the callee's own rows here |
| asy_config_manager.py:451 | ConfigManager.get_error_counter | `self.pr.get_log` at :451 | what the callee raises | transitive | the callee's own rows here |
| asy_config_manager.py:474 | ConfigManager.delete_file | `self.close_writes` at :474 | what the callee raises | transitive | the callee's own rows here |
| asy_config_manager.py:477 | ConfigManager.delete_file | `range` at :477 | TypeError/ValueError on unsupported operands (py/modbuiltins.c, py/obj.c) | open | operand-type proof |
| asy_config_manager.py:479 | ConfigManager.delete_file | `os.remove` at :479; narrow except OSError | OSError (extmod/vfs*.c) | open | - |
| asy_config_manager.py:487 | ConfigManager.delete_file | `self.pr.err` at :487 | what the callee raises | transitive | the callee's own rows here |
| asy_config_manager.py:501 | ConfigManager.reset_error_counter | `self.pr.reset` at :501 | what the callee raises | transitive | the callee's own rows here |
| asy_config_manager.py:507 | ConfigManager.setup | `self.pr.setup` at :507 | what the callee raises | transitive | the callee's own rows here |
| asy_config_manager.py:514 | ConfigManager.setup | `os.stat` at :514; narrow except MemoryError/OSError | OSError (extmod/vfs*.c) | open | - |
| asy_config_manager.py:516 | ConfigManager.setup | `open` at :516, :585; narrow except MemoryError/OSError | OSError (extmod/vfs*.c) | open | - |
| asy_config_manager.py:518 | ConfigManager.setup | `json.load` at :518; narrow except MemoryError/OSError/ValueError | OSError/MemoryError/ValueError/TypeError (extmod/modjson.c) | open | - |
| asy_config_manager.py:522 | ConfigManager.setup | `self.pr.wrn_s` at :522, :525, :539, :566, :576; narrow except MemoryError/OSError/ValueError | what the callee raises | transitive | the callee's own rows here |
| asy_config_manager.py:535 | ConfigManager.setup | `self.pr.one` at :535, :580, :582, :587; narrow except MemoryError/OSError | what the callee raises | transitive | the callee's own rows here |
| asy_config_manager.py:548 | ConfigManager.setup | `defaults.items` at :548 | not classified | open | - |
| asy_config_manager.py:549 | ConfigManager.setup +1 | `check_cfg_get_default` at :549, :615; narrow except MemoryError | what the callee raises | transitive | the callee's own rows here |
| asy_config_manager.py:560 | ConfigManager.setup | `data.pop` at :560 | not classified | open | - |
| asy_config_manager.py:586 | ConfigManager.setup | `f.write` at :586; narrow except MemoryError/OSError | what the callee raises | transitive | the callee's own rows here |
| asy_config_manager.py:601 | ConfigManager.write_config | `self._closed_for_reset` at :601, :610 | what the callee raises | transitive | the callee's own rows here |
| asy_config_manager.py:615 | ConfigManager.write_config | `tuple` at :615; narrow except MemoryError | MemoryError (py/gc.c gc_alloc via m_malloc_fail) | open | setup-only or run-time allocation decides (I.4) |
| asy_config_manager.py:615 | ConfigManager.write_config | `fields.items` at :615, :616; narrow except MemoryError | not classified | open | - |
| asy_config_manager.py:617 | ConfigManager.write_config | `compare_before_write` at :617; narrow except MemoryError | what the callee raises | transitive | the callee's own rows here |
| asy_config_manager.py:627 | ConfigManager.write_config | `dict_results.items` at :627 | not classified | open | - |
| asy_config_manager.py:645 | ConfigManager.write_config | `dict` at :645; narrow except MemoryError | MemoryError (py/gc.c gc_alloc via m_malloc_fail) | open | setup-only or run-time allocation decides (I.4) |
| asy_config_manager.py:646 | ConfigManager.write_config | `write.items` at :646; narrow except MemoryError | not classified | open | - |
| asy_config_manager.py:647 | ConfigManager.write_config | `_stored_float` at :647; narrow except MemoryError | what the callee raises | transitive | the callee's own rows here |
| asy_config_manager.py:648 | ConfigManager.write_config | `asyncio.create_task` at :648; narrow except MemoryError | MemoryError (py/gc.c gc_alloc via m_malloc_fail) | open | setup-only or run-time allocation decides (I.4) |
| asy_config_manager.py:648 | ConfigManager.write_config | `self._flush_staged` at :648; narrow except MemoryError | what the callee raises | transitive | the callee's own rows here |
| asy_config_manager.py:655 | ConfigManager.write_config | `self._commit_ready.clear` at :655 | what the callee raises | transitive | the callee's own rows here |
| asy_print_log.py:55 | <module> | `const` at :55, :56, :57, :58, :59, :60, :63, :64, :65, :66, :67, :68 (+3) | nothing at run time | unreachable | folded at compile time (py/compile.c, MICROPY_COMP_CONST) |
| asy_print_log.py:84 | PrintLog.__init__ | `self.set_level` at :84 | what the callee raises | transitive | the callee's own rows here |
| asy_print_log.py:89 | PrintLog.set_level | `type` at :89 | TypeError/ValueError on unsupported operands (py/modbuiltins.c, py/obj.c) | open | operand-type proof |
| asy_print_log.py:92 | PrintLog.set_level | `self.err` at :92 | what the callee raises | transitive | the callee's own rows here |
| asy_print_log.py:97 | PrintLog.all +8 | `print` at :97, :101, :105, :109, :128, :171, :248, :263, :437, :439 | TypeError/ValueError on unsupported operands (py/modbuiltins.c, py/obj.c) | open | operand-type proof |
| asy_print_log.py:133 | PrintLogHistory.__init__ +1 | `super` at :133, :133, :271, :271 | TypeError/ValueError on unsupported operands (py/modbuiltins.c, py/obj.c) | open | operand-type proof |
| asy_print_log.py:137 | PrintLogHistory.__init__ +3 | `min` at :137, :160, :188, :191 | TypeError/ValueError on unsupported operands (py/modbuiltins.c, py/obj.c) | open | operand-type proof |
| asy_print_log.py:137 | PrintLogHistory.__init__ | `max` at :137 | TypeError/ValueError on unsupported operands (py/modbuiltins.c, py/obj.c) | open | operand-type proof |
| asy_print_log.py:139 | PrintLogHistory.__init__ | `deque` at :139, :142; narrow except MemoryError | not classified | open | - |
| asy_print_log.py:143 | PrintLogHistory.__init__ +3 | `console` at :143, :283, :315, :342 | what the callee raises | transitive | the callee's own rows here |
| asy_print_log.py:156 | PrintLogHistory._clear +1 | `self._since_kept` at :156, :294 | what the callee raises | transitive | the callee's own rows here |
| asy_print_log.py:157 | PrintLogHistory._clear +1 | `range` at :157, :295 | TypeError/ValueError on unsupported operands (py/modbuiltins.c, py/obj.c) | open | operand-type proof |
| asy_print_log.py:157 | PrintLogHistory._clear +5 | `len` at :157, :176, :179, :191, :274, :275, :294, :295, :398 | TypeError/ValueError on unsupported operands (py/modbuiltins.c, py/obj.c) | open | operand-type proof |
| asy_print_log.py:159 | PrintLogHistory._clear +1 | `self._since_counted` at :159, :293 | what the callee raises | transitive | the callee's own rows here |
| asy_print_log.py:167 | PrintLogHistory._count +5 | `self._diag` at :167, :201, :206, :219, :285, :353, :362, :368, :387, :410 | what the callee raises | transitive | the callee's own rows here |
| asy_print_log.py:177 | PrintLogHistory._keep | `self.history.append` at :177 | not classified | open | - |
| asy_print_log.py:196 | PrintLogHistory._store_err +1 | `self._count` at :196, :222 | what the callee raises | transitive | the callee's own rows here |
| asy_print_log.py:203 | PrintLogHistory._store_err +1 | `self._keep` at :203, :223 | what the callee raises | transitive | the callee's own rows here |
| asy_print_log.py:208 | PrintLogHistory._store_err +1 | `self._write_through` at :208, :408 | what the callee raises | transitive | the callee's own rows here |
| asy_print_log.py:216 | PrintLogHistory._write_through +2 | `self._write` at :216, :360, :404 | what the callee raises | transitive | the callee's own rows here |
| asy_print_log.py:235 | PrintLogHistory.get_log | `err_num.append` at :235, :238, :241 | not classified | open | - |
| asy_print_log.py:236 | PrintLogHistory.get_log | `err_type.append` at :236, :239, :242 | not classified | open | - |
| asy_print_log.py:246 | PrintLogHistory.err_s +1 | `self._store_err` at :246, :261 | what the callee raises | transitive | the callee's own rows here |
| asy_print_log.py:251 | PrintLogHistory.reset +1 | `self._clear` at :251, :364 | what the callee raises | transitive | the callee's own rows here |
| asy_print_log.py:268 | PrintLogHistoryStore | `struct.calcsize` at :268 | ValueError/TypeError on a bad format or short buffer (py/modstruct.c) | open | format and buffer size proof |
| asy_print_log.py:279 | PrintLogHistoryStore.__init__ | `fram.get_chunk` at :279; narrow except MemoryError | what the callee raises | transitive | the callee's own rows here |
| asy_print_log.py:279 | PrintLogHistoryStore.__init__ | `CRC8` at :279; narrow except MemoryError | not classified | open | - |
| asy_print_log.py:286 | PrintLogHistoryStore.__init__ | `asyncio.Lock` at :286 | MemoryError (py/gc.c gc_alloc via m_malloc_fail) | open | setup-only or run-time allocation decides (I.4) |
| asy_print_log.py:293 | PrintLogHistoryStore._pack_reset +1 | `struct.pack_into` at :293, :336, :337; narrow except MemoryError | ValueError/TypeError on a bad format or short buffer (py/modstruct.c) | open | format and buffer size proof |
| asy_print_log.py:303 | PrintLogHistoryStore._read +1 | `self.fram.get_buffer` at :303, :331; narrow except MemoryError | what the callee raises | transitive | the callee's own rows here |
| asy_print_log.py:304 | PrintLogHistoryStore._read +1 | `buf.get_data_buf` at :304, :332; narrow except MemoryError | what the callee raises | transitive | the callee's own rows here |
| asy_print_log.py:307 | PrintLogHistoryStore._read | `self.fram.read_into` at :307; narrow except MemoryError | what the callee raises | transitive | the callee's own rows here |
| asy_print_log.py:312 | PrintLogHistoryStore._read | `struct.unpack_from` at :312, :313; narrow except MemoryError | ValueError/TypeError on a bad format or short buffer (py/modstruct.c) | open | format and buffer size proof |
| asy_print_log.py:339 | PrintLogHistoryStore._write | `self._pack_reset` at :339; narrow except MemoryError | what the callee raises | transitive | the callee's own rows here |
| asy_print_log.py:340 | PrintLogHistoryStore._write | `bool` at :340; narrow except MemoryError | TypeError/ValueError on unsupported operands (py/modbuiltins.c, py/obj.c) | open | operand-type proof |
| asy_print_log.py:340 | PrintLogHistoryStore._write | `self.fram.write_into` at :340; narrow except MemoryError | what the callee raises | transitive | the callee's own rows here |
| asy_print_log.py:352 | PrintLogHistoryStore.reset | `self._paused` at :352, :361 | not classified | open | - |
| asy_print_log.py:381 | PrintLogHistoryStore.setup | `self.err_s` at :381, :388, :411 | what the callee raises | transitive | the callee's own rows here |
| asy_print_log.py:383 | PrintLogHistoryStore.setup | `self._read` at :383 | what the callee raises | transitive | the callee's own rows here |
| asy_print_log.py:390 | PrintLogHistoryStore.setup +1 | `isinstance` at :390, :462 | TypeError/ValueError on unsupported operands (py/modbuiltins.c, py/obj.c) | open | operand-type proof |
| asy_print_log.py:394 | PrintLogHistoryStore.setup | `self.history.extend` at :394, :399, :400 | not classified | open | - |
| asy_print_log.py:398 | PrintLogHistoryStore.setup | `list` at :398 | MemoryError (py/gc.c gc_alloc via m_malloc_fail) | open | setup-only or run-time allocation decides (I.4) |
| asy_print_log.py:427 | <module> | `namedtuple` at :427 | not classified | open | - |
| asy_print_log.py:429 | <module> | `LogConfig` at :429 | not classified | open | - |
| asy_print_log.py:450 | make_logger | `PrintLogHistory` at :450 | not classified | open | - |
| asy_print_log.py:451 | make_logger | `pr.one` at :451, :454 | what the callee raises | transitive | the callee's own rows here |
| asy_print_log.py:453 | make_logger | `PrintLogHistoryStore` at :453 | not classified | open | - |
| asy_system_service.py:45 | <module> | `const` at :45, :46, :47, :48, :49, :50, :51, :52, :53, :54, :55, :58 (+35) | nothing at run time | unreachable | folded at compile time (py/compile.c, MICROPY_COMP_CONST) |
| asy_system_service.py:132 | _write_region +1 | `mem_backup` at :132, :146, :147 | not classified | open | - |
| asy_system_service.py:148 | begin_boot | `reset_cause` at :148 | not classified | open | - |
| asy_system_service.py:158 | begin_boot | `range` at :158 | TypeError/ValueError on unsupported operands (py/modbuiltins.c, py/obj.c) | open | operand-type proof |
| asy_system_service.py:158 | begin_boot +2 | `len` at :158, :750, :759, :769, :780 | TypeError/ValueError on unsupported operands (py/modbuiltins.c, py/obj.c) | open | operand-type proof |
| asy_system_service.py:160 | begin_boot +2 | `_write_region` at :160, :166, :669 | what the callee raises | transitive | the callee's own rows here |
| asy_system_service.py:181 | SystemService.__init__ | `make_logger` at :181 | what the callee raises | transitive | the callee's own rows here |
| asy_system_service.py:187 | SystemService.__init__ | `TickSeconds` at :187 | not classified | open | - |
| asy_system_service.py:188 | SystemService.__init__ | `asyncio.ThreadSafeFlag` at :188, :194, :220 | MemoryError (py/gc.c gc_alloc via m_malloc_fail) | open | setup-only or run-time allocation decides (I.4) |
| asy_system_service.py:189 | SystemService.__init__ | `Timer` at :189, :190, :193 | not classified | open | - |
| asy_system_service.py:198 | SystemService.__init__ | `LockedValue` at :198 | not classified | open | - |
| asy_system_service.py:211 | SystemService.__init__ | `ConfigManager` at :211 | not classified | open | - |
| asy_system_service.py:211 | SystemService.__init__ | `config_filename` at :211 | what the callee raises | transitive | the callee's own rows here |
| asy_system_service.py:211 | SystemService.__init__ | `instance_name` at :211 | what the callee raises | transitive | the callee's own rows here |
| asy_system_service.py:222 | SystemService.__init__ | `asyncio.Lock` at :222 | MemoryError (py/gc.c gc_alloc via m_malloc_fail) | open | setup-only or run-time allocation decides (I.4) |
| asy_system_service.py:226 | SystemService.__init__ | `asyncio.Event` at :226, :227 | MemoryError (py/gc.c gc_alloc via m_malloc_fail) | open | setup-only or run-time allocation decides (I.4) |
| asy_system_service.py:248 | SystemService._set_dict_cfg | `self.cfgmgr.write_config` at :248 | what the callee raises | transitive | the callee's own rows here |
| asy_system_service.py:250 | SystemService._set_dict_cfg | `dict.fromkeys` at :250 | MemoryError (py/gc.c gc_alloc via m_malloc_fail) | open | setup-only or run-time allocation decides (I.4) |
| asy_system_service.py:251 | SystemService._set_dict_cfg | `results.get` at :251 | not classified | open | - |
| asy_system_service.py:251 | SystemService._set_dict_cfg | `name_cfg` at :251 | what the callee raises | transitive | the callee's own rows here |
| asy_system_service.py:252 | SystemService._set_dict_cfg +1 | `self.cfgmgr.get_int_values` at :252, :739 | what the callee raises | transitive | the callee's own rows here |
| asy_system_service.py:254 | SystemService._set_dict_cfg +1 | `self._apply_level` at :254, :741 | what the callee raises | transitive | the callee's own rows here |
| asy_system_service.py:265 | SystemService._apply_level +8 | `report_if_fatal` at :265, :289, :308, :320, :407, :414, :477, :484, :596 | what the callee raises | transitive | the callee's own rows here |
| asy_system_service.py:266 | SystemService._apply_level +10 | `self.pr.err_s` at :266, :290, :306, :309, :311, :321, :408, :415, :478, :485, :495, :598 (+1) | what the callee raises | transitive | the callee's own rows here |
| asy_system_service.py:279 | SystemService._flush_config_stores +1 | `store.close_writes` at :279, :394 | what the callee raises | transitive | the callee's own rows here |
| asy_system_service.py:294 | SystemService._flush_config_stores | `step_done` at :294 | not classified | open | - |
| asy_system_service.py:302 | SystemService._log_dead_task +2 | `self._uptime.read` at :302, :502, :662 | what the callee raises | transitive | the callee's own rows here |
| asy_system_service.py:325 | SystemService._ntp_boot_signature | `utc_now` at :325 | what the callee raises | transitive | the callee's own rows here |
| asy_system_service.py:330 | SystemService._own_feed +1 | `self._watchdog.feed` at :330, :679 | not classified | open | - |
| asy_system_service.py:335 | SystemService._reboot +4 | `self.pr.evt` at :335, :340, :343, :378, :395, :417, :509, :690, :693 | what the callee raises | transitive | the callee's own rows here |
| asy_system_service.py:338 | SystemService._reboot +1 | `write_reset_record` at :338, :354, :390 | what the callee raises | transitive | the callee's own rows here |
| asy_system_service.py:339 | SystemService._reboot | `self._flush_config_stores` at :339 | what the callee raises | transitive | the callee's own rows here |
| asy_system_service.py:342 | SystemService._reboot +2 | `self._storage_pause` at :342, :508, :691, :694 | not classified | open | - |
| asy_system_service.py:345 | SystemService._reboot +2 | `asyncio.create_task` at :345, :381, :786; narrow except MemoryError/OSError | MemoryError (py/gc.c gc_alloc via m_malloc_fail) | open | setup-only or run-time allocation decides (I.4) |
| asy_system_service.py:345 | SystemService._reboot | `self._reset_when_due` at :345; narrow except MemoryError/OSError | what the callee raises | transitive | the callee's own rows here |
| asy_system_service.py:347 | SystemService._reboot | `self._own_feed` at :347; narrow except MemoryError/OSError | what the callee raises | transitive | the callee's own rows here |
| asy_system_service.py:348 | SystemService._reboot | `self._reset_timer.init` at :348; narrow except MemoryError/OSError | not classified | open | - |
| asy_system_service.py:348 | SystemService._reboot | `self._reset_due.set` at :348; narrow except MemoryError/OSError | not classified | open | - |
| asy_system_service.py:353 | SystemService._reboot | `self._reset_task.cancel` at :353 | not classified | open | - |
| asy_system_service.py:358 | SystemService._reboot +1 | `self.pr.err` at :358, :384 | what the callee raises | transitive | the callee's own rows here |
| asy_system_service.py:372 | SystemService._request_shutdown | `self._storage.erase_ready` at :372 | what the callee raises | transitive | the callee's own rows here |
| asy_system_service.py:381 | SystemService._request_shutdown | `self._shutdown_sequence` at :381; narrow except MemoryError | what the callee raises | transitive | the callee's own rows here |
| asy_system_service.py:395 | SystemService._request_shutdown | `_purpose_name` at :395 | what the callee raises | transitive | the callee's own rows here |
| asy_system_service.py:497 | SystemService._status_loop +2 | `asyncio.sleep_ms` at :497, :759, :777 | not classified | open | - |
| asy_system_service.py:499 | SystemService._status_loop +1 | `arm_tick_timer` at :499, :612 | what the callee raises | transitive | the callee's own rows here |
| asy_system_service.py:501 | SystemService._status_loop | `self._uptime_event.wait` at :501 | not classified | open | - |
| asy_system_service.py:503 | SystemService._status_loop | `self.pr.all` at :503 | what the callee raises | transitive | the callee's own rows here |
| asy_system_service.py:504 | SystemService._status_loop +1 | `time.ticks_diff` at :504, :771 | TypeError only for a non-int argument | inherently safe | small-int arguments (extmod/modtime.c:150-196) |
| asy_system_service.py:504 | SystemService._status_loop +2 | `time.ticks_ms` at :504, :696, :768, :771 | TypeError only for a non-int argument | inherently safe | small-int arguments (extmod/modtime.c:150-196) |
| asy_system_service.py:512 | SystemService._status_loop | `self._ntp_boot_signature` at :512 | what the callee raises | transitive | the callee's own rows here |
| asy_system_service.py:514 | SystemService._status_loop | `self._boot_signature.set_value` at :514, :520 | what the callee raises | transitive | the callee's own rows here |
| asy_system_service.py:515 | SystemService._status_loop +1 | `self.pr.one` at :515, :521, :781 | what the callee raises | transitive | the callee's own rows here |
| asy_system_service.py:520 | SystemService._status_loop | `random.getrandbits` at :520 | not classified | open | - |
| asy_system_service.py:607 | SystemService.start_asy_status +1 | `asyncio.get_event_loop` at :607, :754 | not classified | open | - |
| asy_system_service.py:608 | SystemService.start_asy_status | `evtloop.create_task` at :608 | not classified | open | - |
| asy_system_service.py:608 | SystemService.start_asy_status | `self._status_loop` at :608 | what the callee raises | transitive | the callee's own rows here |
| asy_system_service.py:614 | SystemService.start_uptime_timer | `self._uptime_event.set` at :614 | not classified | open | - |
| asy_system_service.py:619 | SystemService.get_boot_signature | `self._boot_signature.get_value` at :619 | what the callee raises | transitive | the callee's own rows here |
| asy_system_service.py:634 | SystemService.get_dict_cfg | `self.cfgmgr.get_dict` at :634 | what the callee raises | transitive | the callee's own rows here |
| asy_system_service.py:634 | SystemService.get_dict_cfg | `schema_names` at :634 | what the callee raises | transitive | the callee's own rows here |
| asy_system_service.py:638 | SystemService.get_error_counter | `self.pr.get_log` at :638 | what the callee raises | transitive | the callee's own rows here |
| asy_system_service.py:672 | SystemService.erase_fram +3 | `self._request_shutdown` at :672, :700, :703, :713 | what the callee raises | transitive | the callee's own rows here |
| asy_system_service.py:687 | SystemService.pause_permanent_storage | `min` at :687 | TypeError/ValueError on unsupported operands (py/modbuiltins.c, py/obj.c) | open | operand-type proof |
| asy_system_service.py:687 | SystemService.pause_permanent_storage | `max` at :687 | TypeError/ValueError on unsupported operands (py/modbuiltins.c, py/obj.c) | open | operand-type proof |
| asy_system_service.py:696 | SystemService.pause_permanent_storage +1 | `time.ticks_add` at :696, :771 | TypeError only for a non-int argument | inherently safe | small-int arguments (extmod/modtime.c:150-196) |
| asy_system_service.py:710 | SystemService.reset_error_counter | `self.pr.reset` at :710 | what the callee raises | transitive | the callee's own rows here |
| asy_system_service.py:718 | SystemService.run_setups +1 | `gc.collect` at :718, :722, :751, :760 | not classified | open | - |
| asy_system_service.py:720 | SystemService.run_setups | `setup` at :720 | what the callee raises | transitive | the callee's own rows here |
| asy_system_service.py:721 | SystemService.run_setups | `self.feed_watchdog` at :721 | what the callee raises | transitive | the callee's own rows here |
| asy_system_service.py:728 | SystemService.setup | `self.pr.setup` at :728 | what the callee raises | transitive | the callee's own rows here |
| asy_system_service.py:730 | SystemService.setup | `self._level_setters_provider` at :730 | not classified | open | - |
| asy_system_service.py:732 | SystemService.setup | `self._config_stores_provider` at :732 | not classified | open | - |
| asy_system_service.py:733 | SystemService.setup | `self.cfgmgr.setup` at :733 | what the callee raises | transitive | the callee's own rows here |
| asy_system_service.py:737 | SystemService.setup | `self.pr.wrn_s` at :737 | what the callee raises | transitive | the callee's own rows here |
| asy_system_service.py:755 | SystemService.start_tasks | `loop.get_exception_handler` at :755 | not classified | open | - |
| asy_system_service.py:756 | SystemService.start_tasks | `loop.set_exception_handler` at :756 | not classified | open | - |
| asy_system_service.py:757 | SystemService.start_tasks +1 | `enumerate` at :757, :766, :770 | TypeError/ValueError on unsupported operands (py/modbuiltins.c, py/obj.c) | open | operand-type proof |
| asy_system_service.py:758 | SystemService.start_tasks | `self._start_task` at :758 | what the callee raises | transitive | the callee's own rows here |
| asy_system_service.py:767 | SystemService.start_timers | `self._run_timer_starter` at :767, :780 | what the callee raises | transitive | the callee's own rows here |
| asy_system_service.py:774 | SystemService.start_timers | `self._sequencer_timer.init` at :774; narrow except MemoryError/OSError | not classified | open | - |
| asy_system_service.py:774 | SystemService.start_timers | `self._sequencer_flag.set` at :774; narrow except MemoryError/OSError | not classified | open | - |
| asy_system_service.py:779 | SystemService.start_timers | `self._sequencer_flag.wait` at :779 | not classified | open | - |
| asy_system_service.py:786 | SystemService.supervise_tasks | `self._supervise` at :786 | what the callee raises | transitive | the callee's own rows here |
| asy_system_service.py:788 | SystemService.supervise_tasks | `self._never.wait` at :788 | not classified | open | - |
| asy_system_service.py:790 | SystemService.supervise_tasks | `self._supervisor_task.cancel` at :790 | not classified | open | - |
| asy_fram_manager.py:28 | <module> | `const` at :28, :29, :30, :31, :32, :33, :34, :35, :36, :37, :40, :41 (+18) | nothing at run time | unreachable | folded at compile time (py/compile.c, MICROPY_COMP_CONST) |
| asy_fram_manager.py:69 | _owner_seed | `min` at :69 | TypeError/ValueError on unsupported operands (py/modbuiltins.c, py/obj.c) | open | operand-type proof |
| asy_fram_manager.py:69 | _owner_seed +2 | `crc.length` at :69, :667, :718 | not classified | open | - |
| asy_fram_manager.py:73 | _owner_seed | `owner.encode` at :73 | not classified | open | - |
| asy_fram_manager.py:95 | _FRAMBaseChunk.__init__ +5 | `self.crc.length` at :95, :184, :205, :360, :456, :524 | not classified | open | - |
| asy_fram_manager.py:97 | _FRAMBaseChunk.__init__ | `asyncio.Lock` at :97 | MemoryError (py/gc.c gc_alloc via m_malloc_fail) | open | setup-only or run-time allocation decides (I.4) |
| asy_fram_manager.py:101 | _FRAMBaseChunk.__init__ +3 | `bytearray` at :101, :103, :467, :537, :762; narrow except MemoryError/OverflowError | MemoryError (py/gc.c gc_alloc via m_malloc_fail) | open | setup-only or run-time allocation decides (I.4) |
| asy_fram_manager.py:107 | _FRAMBaseChunk.__init__ +1 | `console` at :107, :764 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_manager.py:109 | _FRAMBaseChunk.__init__ +2 | `memoryview` at :109, :173, :504 | MemoryError (py/gc.c gc_alloc via m_malloc_fail) | open | setup-only or run-time allocation decides (I.4) |
| asy_fram_manager.py:124 | _FRAMBaseChunk._set_check_sb | `fram.get_values_sync` at :124 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_manager.py:126 | _FRAMBaseChunk._set_check_sb | `fram.report_get_values` at :126 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_manager.py:127 | _FRAMBaseChunk._set_check_sb +15 | `self.pr.err_s` at :127, :133, :140, :159, :167, :192, :206, :228, :243, :250, :318, :361 (+16) | what the callee raises | transitive | the callee's own rows here |
| asy_fram_manager.py:136 | _FRAMBaseChunk._set_check_sb +1 | `fram.set_values_sync` at :136, :769 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_manager.py:139 | _FRAMBaseChunk._set_check_sb | `fram.report_set_values` at :139 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_manager.py:158 | _FRAMBaseChunk._clear_chunk +5 | `report_if_fatal` at :158, :317, :403, :562, :597, :797 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_manager.py:175 | _FRAMBaseChunk._compare_with +1 | `self._read_chunk` at :175, :331 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_manager.py:185 | _FRAMBaseChunk._handle_status_bytes | `self._set_check_sb` at :185, :188 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_manager.py:199 | _FRAMBaseChunk._read +5 | `self.fram.lost.is_set` at :199, :354, :417, :433, :644, :779 | not classified | open | - |
| asy_fram_manager.py:202 | _FRAMBaseChunk._read +2 | `self._mempause` at :202, :357, :420 | not classified | open | - |
| asy_fram_manager.py:203 | _FRAMBaseChunk._read +2 | `self.pr.wrn_s` at :203, :213, :215, :221, :223, :239, :241, :358, :421 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_manager.py:205 | _FRAMBaseChunk._read +4 | `len` at :205, :206, :360, :361, :378, :423, :482, :482, :483, :483, :485, :580 (+4) | TypeError/ValueError on unsupported operands (py/modbuiltins.c, py/obj.c) | open | operand-type proof |
| asy_fram_manager.py:208 | _FRAMBaseChunk._read | `self._read_into` at :208, :216 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_manager.py:211 | _FRAMBaseChunk._read +7 | `self.pr.evt` at :211, :219, :237, :377, :383, :412, :427, :555, :557, :569, :604, :609 (+2) | what the callee raises | transitive | the callee's own rows here |
| asy_fram_manager.py:225 | _FRAMBaseChunk._read +1 | `self.pr.all` at :225, :230, :232, :245, :252, :363, :368 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_manager.py:227 | _FRAMBaseChunk._read +1 | `self._write_chunk` at :227, :242, :364, :369 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_manager.py:233 | _FRAMBaseChunk._read +1 | `self._compare_with` at :233, :379 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_manager.py:320 | _FRAMBaseChunk._read_chunk | `self._read_progress` at :320 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_manager.py:349 | _FRAMBaseChunk._read_progress +3 | `range` at :349, :378, :423, :767 | TypeError/ValueError on unsupported operands (py/modbuiltins.c, py/obj.c) | open | operand-type proof |
| asy_fram_manager.py:424 | _FRAMBaseChunk.clear | `self._clear_chunk` at :424 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_manager.py:438 | _FRAMBaseChunk.invalidate | `self._handle_status_bytes` at :438 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_manager.py:451 | FRAMChunkBuffer.__init__ +2 | `super` at :451, :451, :499, :499, :519, :519 | TypeError/ValueError on unsupported operands (py/modbuiltins.c, py/obj.c) | open | operand-type proof |
| asy_fram_manager.py:456 | FRAMChunk.get_buffer | `FRAMChunkBuffer` at :456 | not classified | open | - |
| asy_fram_manager.py:459 | FRAMChunk.read +3 | `self.get_buffer` at :459, :477, :528, :575 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_manager.py:460 | FRAMChunk.read +1 | `self.read_into` at :460, :529 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_manager.py:462 | FRAMChunk.read +3 | `buf.get_data_buf` at :462, :478, :532, :576 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_manager.py:470 | FRAMChunk.read_into +3 | `buf.get_buf` at :470, :490, :540, :615 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_manager.py:474 | FRAMChunk.read_into +1 | `self._read` at :474, :544 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_manager.py:487 | FRAMChunk.write +1 | `self.write_into` at :487, :585 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_manager.py:494 | FRAMChunk.write_into +1 | `self._write` at :494, :620 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_manager.py:519 | FRAMTimestampedChunk.__init__ +2 | `struct.calcsize` at :519, :524, :524, :718 | ValueError/TypeError on a bad format or short buffer (py/modstruct.c) | open | format and buffer size proof |
| asy_fram_manager.py:523 | FRAMTimestampedChunk.get_buffer | `FRAMChunkTimestampedBuffer` at :523 | not classified | open | - |
| asy_fram_manager.py:548 | FRAMTimestampedChunk.read_into +1 | `buf.get_ts_buf` at :548, :610 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_manager.py:553 | FRAMTimestampedChunk.read_into | `int` at :553 | TypeError/ValueError on unsupported operands (py/modbuiltins.c, py/obj.c) | open | operand-type proof |
| asy_fram_manager.py:553 | FRAMTimestampedChunk.read_into | `struct.unpack_from` at :553 | ValueError/TypeError on a bad format or short buffer (py/modstruct.c) | open | format and buffer size proof |
| asy_fram_manager.py:565 | FRAMTimestampedChunk.read_into +1 | `utc_now` at :565, :600 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_manager.py:614 | FRAMTimestampedChunk.write_into | `struct.pack_into` at :614 | ValueError/TypeError on a bad format or short buffer (py/modstruct.c) | open | format and buffer size proof |
| asy_fram_manager.py:628 | FRAMManager.__init__ | `PrintLogHistory` at :628 | not classified | open | - |
| asy_fram_manager.py:636 | FRAMManager.__init__ | `FRAM_SPI` at :636 | not classified | open | - |
| asy_fram_manager.py:642 | FRAMManager._watch_chip_loop +3 | `self.pr.err` at :642, :664, :677, :715, :728, :752, :759, :771 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_manager.py:645 | FRAMManager._watch_chip_loop | `self.setup` at :645 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_manager.py:647 | FRAMManager._watch_chip_loop +2 | `self.pr.one` at :647, :669, :682, :720, :736 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_manager.py:648 | FRAMManager._watch_chip_loop | `self.fram.lost.wait` at :648 | not classified | open | - |
| asy_fram_manager.py:657 | FRAMManager.start_asy_watch_chip | `asyncio.get_event_loop` at :657 | not classified | open | - |
| asy_fram_manager.py:658 | FRAMManager.start_asy_watch_chip | `evtloop.create_task` at :658 | not classified | open | - |
| asy_fram_manager.py:658 | FRAMManager.start_asy_watch_chip | `self._watch_chip_loop` at :658 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_manager.py:666 | FRAMManager.get_chunk +1 | `CRCPass` at :666, :717 | not classified | open | - |
| asy_fram_manager.py:679 | FRAMManager.get_chunk | `FRAMChunk` at :679 | not classified | open | - |
| asy_fram_manager.py:679 | FRAMManager.get_chunk +1 | `_owner_seed` at :679, :732 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_manager.py:680 | FRAMManager.get_chunk +1 | `self._chunks.append` at :680, :734 | not classified | open | - |
| asy_fram_manager.py:690 | FRAMManager.get_error_counter | `self.pr.get_log` at :690 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_manager.py:731 | FRAMManager.get_timestamped_chunk | `FRAMTimestampedChunk` at :731 | not classified | open | - |
| asy_fram_manager.py:751 | FRAMManager.erase_chip | `self.erase_ready` at :751 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_manager.py:756 | FRAMManager.erase_chip | `chunk.invalidate` at :756 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_manager.py:757 | FRAMManager.erase_chip +1 | `step_done` at :757, :773, :787 | not classified | open | - |
| asy_fram_manager.py:766 | FRAMManager.erase_chip | `self.fram.get_size` at :766 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_manager.py:770 | FRAMManager.erase_chip | `self.fram.report_set_values` at :770 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_manager.py:774 | FRAMManager.erase_chip | `asyncio.sleep` at :774 | MemoryError (py/gc.c gc_alloc via m_malloc_fail) | open | setup-only or run-time allocation decides (I.4) |
| asy_fram_manager.py:779 | FRAMManager.erase_ready | `self.fram.get_write_protected` at :779 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_manager.py:784 | FRAMManager.quiesce | `self.set_pause` at :784 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_manager.py:786 | FRAMManager.quiesce | `chunk.wait_idle` at :786 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_manager.py:790 | FRAMManager.reset_error_counter | `self.pr.reset` at :790 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_manager.py:793 | FRAMManager.setup | `self.pr.setup` at :793 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_driver.py:34 | <module> | `const` at :34, :35, :45, :46, :47, :52, :53, :54, :55, :59, :60, :61 (+33) | nothing at run time | unreachable | folded at compile time (py/compile.c, MICROPY_COMP_CONST) |
| asy_fram_driver.py:128 | FRAM_SPI.__init__ +2 | `super` at :128, :128, :153, :153, :171, :171 | TypeError/ValueError on unsupported operands (py/modbuiltins.c, py/obj.c) | open | operand-type proof |
| asy_fram_driver.py:130 | FRAM_SPI.__init__ | `SPIDevice` at :130 | not classified | open | - |
| asy_fram_driver.py:135 | FRAM_SPI.__init__ | `Pin` at :135 | not classified | open | - |
| asy_fram_driver.py:138 | FRAM_SPI.__init__ | `bytearray` at :138, :139, :140, :140, :141 | MemoryError (py/gc.c gc_alloc via m_malloc_fail) | open | setup-only or run-time allocation decides (I.4) |
| asy_fram_driver.py:147 | FRAM_SPI.__init__ | `asyncio.Event` at :147 | MemoryError (py/gc.c gc_alloc via m_malloc_fail) | open | setup-only or run-time allocation decides (I.4) |
| asy_fram_driver.py:157 | FRAM_SPI.__aenter__ +1 | `self.session_lock.release` at :157, :499 | not classified | open | - |
| asy_fram_driver.py:168 | FRAM_SPI.__aexit__ | `self._bus_lock.release` at :168; narrow except RuntimeError | not classified | open | - |
| asy_fram_driver.py:170 | FRAM_SPI.__aexit__ | `report_if_fatal` at :170 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_driver.py:176 | FRAM_SPI._is_write_protected +2 | `bool` at :176, :303, :458 | TypeError/ValueError on unsupported operands (py/modbuiltins.c, py/obj.c) | open | operand-type proof |
| asy_fram_driver.py:176 | FRAM_SPI._is_write_protected +1 | `self._wp_pin.value` at :176, :185, :193, :197 | not classified | open | - |
| asy_fram_driver.py:181 | FRAM_SPI._set_write_protected +1 | `self._enable_write` at :181, :310 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_driver.py:188 | FRAM_SPI._set_write_protected +2 | `self._send_command` at :188, :228, :231, :238, :241 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_driver.py:189 | FRAM_SPI._set_write_protected +2 | `self._read_status` at :189, :303, :457 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_driver.py:190 | FRAM_SPI._set_write_protected +1 | `self._disable_write` at :190, :314 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_driver.py:201 | FRAM_SPI._check_device_id | `_KNOWN_PRODUCT_IDS.get` at :201 | not classified | open | - |
| asy_fram_driver.py:203 | FRAM_SPI._check_device_id | `ValueError` at :203 | not classified | open | - |
| asy_fram_driver.py:204 | FRAM_SPI._check_device_id +2 | `self._send_and_read` at :204, :245, :248 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_driver.py:219 | FRAM_SPI._check_write_anomaly +2 | `self._check_device_id` at :219, :454, :494 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_driver.py:229 | FRAM_SPI._disable_write +1 | `self._wel_is_set` at :229, :232, :239, :242 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_driver.py:245 | FRAM_SPI._read_address +1 | `self._setup_addr_buffer` at :245, :313 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_driver.py:254 | FRAM_SPI._report_chip_lost +6 | `self.pr.err_s` at :254, :343, :370, :379, :387, :398, :402, :404, :406, :418, :421, :424 (+5) | what the callee raises | transitive | the callee's own rows here |
| asy_fram_driver.py:255 | FRAM_SPI._report_chip_lost | `self.lost.set` at :255 | not classified | open | - |
| asy_fram_driver.py:259 | FRAM_SPI._send_and_read +2 | `spidev.session_begin` at :259, :268, :282 | not classified | open | - |
| asy_fram_driver.py:261 | FRAM_SPI._send_and_read +2 | `spidev.write_sync` at :261, :270, :271, :284 | not classified | open | - |
| asy_fram_driver.py:262 | FRAM_SPI._send_and_read | `spidev.readinto_sync` at :262 | not classified | open | - |
| asy_fram_driver.py:264 | FRAM_SPI._send_and_read +2 | `spidev.session_end` at :264, :273, :286 | not classified | open | - |
| asy_fram_driver.py:292 | FRAM_SPI._setup_addr_buffer +2 | `len` at :292, :334, :362 | TypeError/ValueError on unsupported operands (py/modbuiltins.c, py/obj.c) | open | operand-type proof |
| asy_fram_driver.py:306 | FRAM_SPI._write +1 | `self._is_write_protected` at :306, :345 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_driver.py:313 | FRAM_SPI._write | `self._send_and_write` at :313 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_driver.py:320 | FRAM_SPI.get_values | `self.get_values_sync` at :320 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_driver.py:321 | FRAM_SPI.get_values +4 | `asyncio.sleep` at :321, :349, :374, :459, :495 | MemoryError (py/gc.c gc_alloc via m_malloc_fail) | open | setup-only or run-time allocation decides (I.4) |
| asy_fram_driver.py:322 | FRAM_SPI.get_values | `self.report_get_values` at :322 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_driver.py:330 | FRAM_SPI.get_values_sync +1 | `self.session_lock.locked` at :330, :357 | not classified | open | - |
| asy_fram_driver.py:336 | FRAM_SPI.get_values_sync | `self._read_address` at :336 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_driver.py:348 | FRAM_SPI.set_values | `self.set_values_sync` at :348 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_driver.py:350 | FRAM_SPI.set_values | `self.report_set_values` at :350 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_driver.py:364 | FRAM_SPI.set_values_sync +1 | `self._check_write_anomaly` at :364, :373 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_driver.py:364 | FRAM_SPI.set_values_sync | `self._write` at :364 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_driver.py:373 | FRAM_SPI.set_write_protected | `self._set_write_protected` at :373 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_driver.py:376 | FRAM_SPI.set_write_protected +2 | `self._report_chip_lost` at :376, :415, :501 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_driver.py:382 | FRAM_SPI.set_write_protected +2 | `self.pr.wrn_s` at :382, :390, :432, :435, :440, :463 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_driver.py:385 | FRAM_SPI.set_write_protected +1 | `self.pr.evt` at :385, :391, :438 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_driver.py:445 | FRAM_SPI.setup | `self._spidev.setup` at :445 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_driver.py:447 | FRAM_SPI.setup | `OSError` at :447, :461 | not classified | open | - |
| asy_fram_driver.py:466 | FRAM_SPI.setup | `hex` at :466 | not classified | open | - |
| asy_fram_driver.py:470 | FRAM_SPI.setup | `self._wp_pin.init` at :470 | not classified | open | - |
| asy_fram_driver.py:473 | FRAM_SPI.setup | `self.lost.clear` at :473 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_driver.py:474 | FRAM_SPI.setup | `self.pr.one` at :474 | what the callee raises | transitive | the callee's own rows here |
| asy_fram_driver.py:485 | FRAM_SPI.verify_present | `asyncio.wait_for_ms` at :485; narrow except TimeoutError | not classified | open | - |
| asy_fram_driver.py:485 | FRAM_SPI.verify_present | `self.session_lock.acquire` at :485; narrow except TimeoutError | not classified | open | - |
| math_helpers.py:13 | <module> | `const` at :13, :14, :15, :16, :17, :18, :19, :20, :21, :22, :23, :24 (+18) | nothing at run time | unreachable | folded at compile time (py/compile.c, MICROPY_COMP_CONST) |
| math_helpers.py:67 | abs_humidity +1 | `math.pow` at :67, :166; narrow except ArithmeticError/ValueError | not classified | open | - |
| math_helpers.py:81 | cct_mccamy | `abs` at :81 | TypeError/ValueError on unsupported operands (py/modbuiltins.c, py/obj.c) | open | operand-type proof |
| math_helpers.py:117 | dew_point | `math.log` at :117; narrow except ArithmeticError/ValueError | not classified | open | - |
| math_helpers.py:128 | ema_step | `math.isfinite` at :128, :132 | not classified | open | - |
| math_helpers.py:146 | pressure_at_height | `math.exp` at :146; narrow except ArithmeticError/ValueError | not classified | open | - |
| math_helpers.py:182 | rgb_to_hsb | `max` at :182 | TypeError/ValueError on unsupported operands (py/modbuiltins.c, py/obj.c) | open | operand-type proof |
| math_helpers.py:183 | rgb_to_hsb | `min` at :183 | TypeError/ValueError on unsupported operands (py/modbuiltins.c, py/obj.c) | open | operand-type proof |
| math_helpers.py:221 | wet_bulb_temperature | `math.atan` at :221, :222, :223, :224; narrow except ArithmeticError/ValueError | not classified | open | - |
| math_helpers.py:221 | wet_bulb_temperature | `math.sqrt` at :221, :224; narrow except ArithmeticError/ValueError | not classified | open | - |
