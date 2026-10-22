# Audit planning survey (raw, unverified)

The nine read-only survey reports the audit plan was built from (2026-09-25, planning baseline `0615eba`; line
anchors resolve there). Every claim is **unverified** survey output; the plan's seeds are the triaged residue.
Kept because the owner asked for the overview to survive for later discussion (`PROJECT_AUDIT_PLAN.md` 3.1).

---

## Core runtime (`src/` system service, config, logging, locks)

#### Core runtime survey: src/ core modules + buildgen boot shape (read-only)

**Scope and method.** I read these files in full: `src/system_service.py`, `base_classes.py`, `config_manager.py`, `print_log.py`, `api_response.py`, `math_helpers.py`, `crc_checks.py`, `framing_codecs.py`. I also read `buildgen/codegen.py` lines 371-709 (`build_system`/`main`/collectors/boot entry), `devices/wozi.toml`, and the SPEC Parts that were asked for (A.2, A.4, A.7, C.5-C.9, C.13-C.14, G, I.4). Where the code interacts with them I also checked parts of `src/asy_fram_manager.py`, `src/asy_webserver_service.py` and `src/asy_ntp_client.py`.
- **Not run:** no tests, no tools.
- **Not available:** there is no MicroPython source checkout on this machine. Every claim about MicroPython asyncio or Timer internals below is marked "inferred".

---

##### 1. Modules, public API, and how they interact

**system_service.py — `SystemService`, the one per-device housekeeping singleton**
- **Constants:** `_RESET_DELAY=4`s, `_MAX_STORAGE_PAUSE=3600`, `_NTP_WAIT_TIME=120`, `_TIMER_BASE_PERIOD=1000`ms, `_TASK_CHECK_TIME=2`s, `_TASK_FAIL_INCREMENT=100`, `_TASK_FAIL_MAX=300`, `_NAME="SYSTEM"`. The schema `_VAL_DEBUG_LEVEL` has one field, `("DebugLevel","int",0,0,5,None)`.
- **Constructor:** `__init__(asy_ntp_callback, watchdog=None, fram=None, history_length=10, debug=None, cfg_path="")`.
  - Creates `self.pr = make_logger(...)`, which is FRAM chunk N.
  - Then creates the embedded `ConfigManager("config_SYSTEM.cfg")`, whose logger `CFGMGR_SYSTEM` is chunk N+1.
  - Preallocates 4 Timers (uptime/reset/storage/sequencer), two `LockedCounter`s (uptime, boot_signature) and two `ThreadSafeFlag`s.
- **Public API:**
  - Watchdog and reboot: `feed_watchdog()` (G.2 primitive), `reboot_system()`, `reboot_bootloader()`, `pause_permanent_storage(duration)`.
  - Supervision: `start_timers(list)`, `start_and_check_tasks(list)`, `get_task_starters()` returns `[start_asy_uptime_counter]`, `get_timer_starters()` returns `[start_uptime_timer]`.
  - Status getters: `get_uptime()`, `get_boot_signature()`, `get_error_sources()` returns `[self, cfgmgr]`, `get_loggers()`, `get_error_counter()`, `reset_error_counter()` (self.pr only).
  - Config and debug level: `setup()`, `get_cfg_schema()`, `get_dict_cfg()`, `_set_dict_cfg()`, `set_level_setters()`, `_apply_level()`, `get_debug_level()`, `set_debug_level()`, `stop_uptime_timer()`.
- **Reboot:** `_reboot()` deinits the reset and storage timers, pauses FRAM through `fram.set_pause`, and arms a 4s ONE_SHOT that calls `machine.reset`/`bootloader`. If arming fails (`OSError`/`MemoryError`) it latches `_force_watchdog_starve=True`, which turns every later `feed_watchdog()` into a no-op.
- **Supervisor (`start_and_check_tasks`):**
  - Boot phase: `await self.pr.setup()` (the SYSTEM logger's FRAM restore happens here), then `gc.collect()`, then each starter in turn followed by `asyncio.sleep(1/N)` and `gc.collect()`.
  - Loop, every 2s: any task that is None or done → `_log_dead_task` (re-awaits the task to recover its exception; errno 5 for an exception, 6 for a cancel), `task_errors += 100`, restart, `wrn_s(wrnno=n+1)`.
  - Decay: a clean pass takes 1 off `task_errors`.
  - Escalation: `task_errors > 300` → errno 4 → `reboot_system()` → `return`. Once the supervisor returns, nothing feeds the watchdog any more.
  - Net effect: a 4th task death within about 198s causes a reboot.
- **Uptime:** `status_counter()` waits on `uptime_event`, which a PERIODIC 1000ms soft timer sets. Each wake increments uptime. It resolves the boot signature once: the NTP UTC timestamp at the moment of first sync, or `random.getrandbits(32)` at uptime ≥120.

**base_classes.py**
- **`Lockable`:** an async context manager over an `asyncio.Lock`. `__aexit__` swallows `RuntimeError` on release.
- **`LockableBuffer(size, data_start, data_length)`:** one bytearray with `memoryview` region accessors. A bad size, or a `MemoryError`/`OverflowError` on allocation, leaves `buf=None`.
- **Locked scalars:**
  - `LockedCounter(init_value, max_val)`: clamps to [0, max], `None` is a sentinel.
  - `LockedFlag` and `LockedValue`: each holds its own lock.
- **`SensorReader`:**
  - State: `pr` (or a caller-supplied `logger=`), `name = instance_name(name, name_ext)`, a `_datalock`-guarded namedtuple, `_err_cnt_internal`.
  - `_error_check()`: a streak counter using the reserved errno 1/2.
  - `_get_dict_cfg()`: guards the overridable `_get_mgr_cfg` and callback, errno 3/4 and wrnno 1/2.
  - Fan-in `get_error_sources()`/`get_loggers()`, and `reset_error_counter()`.
- **`SensorReaderConfig`:** adds `cfgmgr` (`config_<self.name>.cfg`, logger `CFGMGR_<name>`), `_push_callbacks`/`_get_callbacks` dicts, `_set_mgr_cfg` (→ `write_config`), and the setter orchestration `_set_dict_cfg`:
  1. Snapshot the old persisted values (errno 7).
  2. Write via `_set_mgr_cfg` (errno 5); `_checked_write_results` enforces a dict result.
  3. If the write failed: every key → "Failed".
  4. Missing result keys → "Failed".
  5. Push only fields marked "Valid", using the coerced value (errno 6).
  6. On a failed push: `_recover_failed_push` tries getter readback (errno 8), then the snapshot, then the default, and writes back through `_set_mgr_cfg` only (errno 9).

**config_manager.py**
- **Pure helpers:** `_special_bypass`, `instance_name`, `schema_names`, `name_cfg`, `schema_dict`, `make_dict` (getattr over an explicit fields tuple), `coerce_numeric` (exact-only: int→float always, float→int only when integral, `bool` excluded via `type()`), `type_or_range_error` (int/float/str/bool branches; `special` as a scalar bypass or an enum set), `check_cfg_get_default` (self-checks the default; special-alone fields give `use_value=False`).
- **`ConfigManager` state:** `_cache` (what is on disk), `_staged` (the read-your-write snapshot), `_pending_flush` (a Task), `config_lock`, `valid`.
- **`setup()`:**
  - Calls `pr.setup()`, then stats and loads the JSON file.
  - Repairs per key against the defaults; drops unknown keys.
  - Rewrites the file at most once. On a write failure it logs errno 4 but still marks the config valid (C.7.3).
- **Reads:** `get_dict()`, `get_*_values()`.
- **`write_config()`:**
  - Validates under `config_lock` against the caller-supplied `cfg_vals` (errno 9-13, 15).
  - Stages a full copy of `_current()`.
  - Hands the flash write to `asyncio.create_task(_flush_staged(snapshot))`.
- **`_flush_staged()`:** takes the lock again, skips if superseded (identity check), does `json.dump`, logs errno 14 on error, and always commits `_cache = staged` in `finally`.
- **`flush_pending()`:** awaits the latest flush task. The generated `_flush_pending_configs()` uses it before a commanded reboot or bootloader.

**print_log.py**
- **`PrintLog`:** levels 0-5; sync `err`/`wrn`/`one`/`evt`/`all` all print.
- **`PrintLogHistory`:**
  - A deque ring of history_length bytes. Error codes go in as `errno + 0x00` (≤0x7F); warning codes as `wrnno + 0x80` (≤0xFF).
  - `err_count` saturates at 0xFFFF.
  - `err_s`/`wrn_s` call `_store_err`, which does the following in order:
    1. Count the entry.
    2. If the code is 0, stop.
    3. Append to the ring, unless `repeat=True`.
    4. If not yet initialized, stop.
    5. Otherwise call `_write()`.
  - `reset()` writes unconditionally and marks the logger initialized when the write succeeds.
  - `get_log()` returns the `ErrorLog` envelope.
- **`PrintLogHistoryStore`:** takes one FRAM chunk (`2 + history_length` bytes, CRC8). The payload is `"<H"` + `"B"*n`. `setup()` is "read, else write current". `make_logger()` picks between RAM and FRAM.

**api_response.py**
- `make_response(code, descr, result)` builds `{res, code, descr, result}` from a catalog of 0-5 and 100.
- `parse_cmd_request()`.
- `handle_set_cmd(reader, data, cfg_vals, post_fct, post_asy_fct, ok_descr)` calls `_set_dict_cfg`, then runs the post hook if any field came back "Valid". Any exception → errno 99 on `reader.pr` and response code 100.

**math_helpers.py** — pure functions that return None on a None, out-of-domain or NaN input:
- Weather/humidity: wet bulb (Stull), dew point (Magnus with an Alduchov water branch and a Sonntag ice branch), `altitude_baro` (which returns pressure, not altitude), `abs_humidity`/`rel_humidity`.
- Colour: `rgb_to_hsb`, `rgb_to_xyz` (sRGB D65), `chromaticity_xy`, `cct_mccamy`.
- Filtering: `ema_step`.
- I spot-checked the formulas against the literature: Stull, Magnus/Alduchov, the McCamy cubic, the sRGB matrix and the barometric formula all match. The abs/rel humidity functions match the legacy file byte for byte (`237.4`/`240.7` constants).

**crc_checks.py**
- A bit-banged MSB-first CRC with no xorout. `_crc` yields with `await asyncio.sleep(0)` after every byte.
- Methods: `add()`/`check()` (allocate), `add_into()`/`check_from()` (in place), `run_inc()`/`check_inc()` (incremental; the only caller, the FRAM manager, resets with `check_inc()` first).
- Variants: CRC8 0x31, CRC16 0x1021, CRC32 0x04C11DB7, and `CRC_Pass` (width 0).

**framing_codecs.py**
- `Framing_Base`/`Framing_Pass` are the identity.
- `Framing_COBS(max_frame)` has one scratch buffer of `max_encoded(max_frame)` bytes. `encode_into` returns a view into that scratch; `decode_from` decodes in place.
- I traced the COBS logic by hand: in-place decode never overtakes unread bytes (written ≤ read), and the 254-run and empty-frame edge cases are correct.
- `Framing_COBS` is currently used only in tests. The UART driver defaults to `Framing_Pass`.

**Generated device module (`buildgen/codegen.py`)**
- **Boot order:**
  1. `build_system()` creates `WDT(timeout=8000)` first.
  2. Constructs the buses, then every node in construction order (conn/ntp/sysfunct placed after fram when `fram_target` is set), then `conn.set_ext_led`, then `WebserverService`. Webserver construction calls `_collect_error_sources()`, which covers every module except webserver itself; webserver adds its own entry.
  3. `timers_running = ThreadSafeFlag()`, then `sysfunct.set_level_setters(_collect_level_setters())`.
  4. `gc.collect()`, then the setup batch: **fram → sysfunct → conn → ntp → every `needs_setup` instance**, each followed by `sysfunct.feed_watchdog()` and `gc.collect()`.
- **`main()`:** `build_system` → `sysfunct.start_timers(timer_starters)` → `ntp.ntp_force_sync()` (just a trigger) → `sysfunct.start_and_check_tasks(task_starters)`.
- **Boot entry:** `gc.threshold(32768)`; `asyncio.run(main())`; `finally: asyncio.new_event_loop()`.
- **Collectors:** fram is excluded from the task/timer collectors. Webserver is appended to the level/task/timer collectors.

---

##### 2. Concurrency model as implemented

- **One asyncio loop.** Soft (never hard) `machine.Timer` callbacks only set a `ThreadSafeFlag` or call short sync code. Exceptions:
  - The `_timer_sequencer` chain runs driver starters inside the soft-callback context.
  - The reset callback calls `machine.reset()` or `bootloader()`.
  - The storage auto-unpause callback calls `set_pause`.
- **Timer stagger.**
  - The first timer starter runs synchronously inside `start_timers`.
  - Each following starter runs from a ONE_SHOT timer `int(1000/(N+1))` ms after the previous callback actually executed. That delay is relative to the previous run, not an absolute target, so soft-callback latency accumulates.
  - `start_timers` awaits `timers_running`.
- **Task stagger:** `asyncio.sleep(1/N)` between starters. Tasks run concurrently from then on; the supervisor only inspects `done()`.
- **Locks in this area:**
  - `ConfigManager.config_lock` serializes `write_config` validation/staging and each flush.
  - `get_dict()` takes no lock; it relies on the single atomic assignment of `_staged`.
  - Each `Locked*` scalar has its own lock.
  - `SensorReader._datalock` guards the measurement tuple.
  - The FRAM chunk `_op_lock` (in `asy_fram_manager`) serializes one chunk's read/write/clear.
  - There is **no** per-module lock around `_set_dict_cfg`'s snapshot → persist → push → recover sequence, and no lock around `PrintLogHistory` state. The ring and count are mutated synchronously; `_write` packs the state, then awaits the chunk lock.
- **Deferred flash write:** `_flush_staged` runs as an unsupervised `create_task`. Its `json.dump` is synchronous and flash writes block interrupts port-wide (per the code comment and SPEC F.2).
- **What can interleave:**
  - Concurrent HTTP handlers can run two `_set_dict_cfg` calls on one module at once.
  - A logger's `setup()` `_read` can interleave with `reset()` or `err_s` from another task.
  - The supervisor's FRAM-writing log calls can interleave with any other FRAM user.

---

##### 3. Error-handling model as implemented

- **Contract:** every public method in these modules returns a sentinel and does not raise. `crc_checks.add()`/`check()` are the documented exception: they let `MemoryError` propagate.
- **Persisted versus non-persisted logging:**
  - `err_s`/`wrn_s` persist, into a bounded ring of 10 plus a count.
  - `err`/`wrn`/`one`/`evt`/`all` only print.
  - Timer-callback failure sites (`_timer_sequencer`, `start_uptime_timer`, `_reboot`, `pause_permanent_storage`) can only use `pr.err`, so none of those failures reach `errcount`.
- **Codes in this area:**
  - base_classes: errno 1-9, wrnno 1-2.
  - config_manager: errno 1-15, wrnno 1-6.
  - system: errno 1-7; wrnno is dynamic (`n+1`, so it depends on the device's starter order).
  - api_response: errno 99.
  - I checked every one against the C.7.1 table and all match.
- **Catches:**
  - `Exception` around caller-supplied callbacks.
  - `(OSError, MemoryError)` around every `Timer.init`.
  - `(OverflowError, OSError)` around `mktime`.
  - In config_manager: `(MemoryError, OSError, TypeError)` around file I/O; `ValueError` for JSON; `(MemoryError, AttributeError)` in `write_config`; `(MemoryError, OSError, ValueError, AttributeError)` in the flush.
- **Restart ladder:**
  1. A driver's `_error_check` returns False once its streak exceeds `max_module_error` (5 in generated code); the task ends.
  2. The supervisor restarts it and adds 100 to its score. Drivers reset `_err_cnt_internal` in their own `_init_*`; the base class does not.
  3. A score above 300 → `reboot_system()`: FRAM paused, reset after 4s.
  4. If the reset timer cannot be armed → watchdog starve.
  5. If the supervisor itself hangs or returns → nothing feeds → WDT at 8s.
- **Reboot triggers:** errno 4 from the supervisor; the REST `system_cmd` "reboot"/"bootloader", which first flushes pending configs; the WDT.

---

##### 4. Memory discipline

- **Preallocation:** the Timer objects, the COBS scratch, the `LockableBuffer` single allocation, and the supervisor's `[None]*N` list.
- **`gc.collect()`:** appears only in `start_and_check_tasks` (the I.4(f.1) boot-confined placement reset) and in the generated setup batch. The generated boot entry sets `gc.threshold(32768)`.
- **Recurring allocations:**
  - Every persisted log entry calls `fram.get_buffer()`, which allocates a new `AsyFramChunkBuffer`: a bytearray plus an `asyncio.Lock` via `Lockable`. The `*self.history` star-args also build a tuple.
  - Every `write_config` copies the whole cache dict.
  - Every `pr.all(...)` call builds its argument tuple even when the level is off: once per second in `status_counter` and once every 2s in the supervisor.
  - The `crc.add()`/`check()` slices.
- **History length** is clamped to 0xFFFF before `[x]*n`, with a `MemoryError` fallback to an empty deque.

---

##### 5. Audit candidates (file:line)

**Suspicions**

1. **`system_service.py:375-394`: a restart of the uptime task corrupts uptime and boot signature.** `status_counter()` does `uptime.set_value(0)` and `boot_signature.set_value(None)` on every (re)start. `start_time_set` stays True after a supervisor restart, so the signature stays `None` for the rest of the boot and uptime silently restarts from 0. That also fakes the "a changed signature means a reboot happened" signal. No test covers a restart; `tests/test_system_service.py` has none.
2. **`config_manager.py:407-426`: any read failure makes `setup()` overwrite persisted user config with defaults.** A `MemoryError` from `json.load` on a valid file, or an `OSError` other than ENOENT (EIO), or a `TypeError`, is logged only as wrnno 3 "not found". `data` stays None, so `setup()` rewrites the file with defaults (line 459). A transient failure at boot therefore destroys the user's configuration.
3. **`print_log.py:173-176, 273-277`: errors logged before `setup()` are lost.** `_store_err` before `setup()` counts and appends in RAM. A successful `_read()` then overwrites `err_count` and the ring with the FRAM contents. SYSTEM's `_apply_level` errno 7, raised during `sysfunct.setup()`, is logged before SYSTEM's `pr.setup()`, which only runs in `start_and_check_tasks`, so it vanishes. On first boot or a corrupt chunk (the `_write` fallback) such entries do survive, so the behaviour is inconsistent.
4. **`print_log.py:213-223` against `:273-277`: `reset()` during an in-flight `setup()` read leaves RAM and FRAM disagreeing.** `reset()` clears RAM, packs, and waits on the chunk lock held by `setup()`'s `_read`. `_read` then restores the *old* history into RAM and `reset()`'s write clears FRAM. `/status` shows the old history while FRAM is cleared. The C.7 fix covers reset-before-setup only.
5. **`base_classes.py:302-358`: no per-module serialization of snapshot → persist → push → recover.** Two concurrent PUTs to the same key can interleave. A failed push in A can make `_recover_failed_push` persist A's pre-write snapshot over B's accepted and pushed value, so the persisted value and the chip diverge.
6. **`system_service.py:229-255`: watchdog feed timing under many task deaths.** The feed happens only after the full scan. Each dead task costs two persisted FRAM writes (`_log_dead_task` plus `wrn_s`); C.7 measured about 305ms per chunk write. A multi-task death burst plus the 2s sleep could approach the 8s WDT and turn a commanded, FRAM-paused reboot into an unpaused WDT reset. That is exactly the case that loses logs (the documented roughly 1-in-8 loss).
7. **ONE_SHOT soft timers on critical paths contradict C.9's own "PERIODIC for anything that must fire" rule:**
   - `_reboot` (`:126`): a dropped callback means no reset, the supervisor keeps feeding, and FRAM stays paused for the rest of the boot.
   - The storage auto-unpause (`:365`): a drop leaves storage paused.
   - The sequencer (`:164`): a drop hangs `start_timers`; recovery then relies on the WDT.
   - Probability is low (scheduler queue depth), but the arm-failure paths handle only the ENOMEM case.
8. **`system_service.py:118-126`: every `_reboot()` call re-arms the reset timer.** It deinits and re-arms, pushing the reset out another 4s. A client repeating "reboot" more often than every 4s can postpone the reset indefinitely while FRAM stays paused.
9. **`api_response.py:396-401` together with `asy_webserver_service.py:463-470`: a failing post-hook reports everything as "Failed".** When `post_fct`/`post_asy_fct` raises after fields were already persisted and pushed, the envelope is code 100 with an empty result and the webserver marks every field "Failed". The client is told the change did not apply when it did.
10. **Doc drift, `SPECIFICATION.md:1802` (C.6).** It says `make_dict()` parses `repr()` and carries a "dormant landmine". The code (`config_manager.py:100-118`) uses `getattr` over an explicit fields tuple, so the landmine text is stale. `SPECIFICATION.md:5666` repeats it.
11. **Doc drift, A.7 step 16 and its boot-latency note.** Both state the setup order as `sysfunct → fram → conn → ntp …`. The generator emits `fram → sysfunct → conn → ntp …` (`codegen.py:441-449`, the CFGMGR_SYSTEM fix).
12. **Doc drift, C.5.3.** It cites `sensortask-wozi.py`'s `_cfg_subset()`, which exists nowhere. Narrowing now happens by subsetting the *data* per `SettingsGroup`, and the full schema is passed as `cfg_vals` (`asy_webserver_service.py:450-460`).
13. **Doc drift, `config_manager.py:126-127`.** The comment says the generated `lightCmdLED` dispatch calls `coerce_numeric()`. The generated `_notification_led_callback` calls `type_or_range_error()` with synthetic `_FIELD_LED_*` schemas (`codegen.py:538-556`); `coerce_numeric` has no src caller outside `config_manager`.
14. **Doc drift, SPEC C.7.1 FRAM row: "the chunk logs into its OWNER's FRAM-backed history, not the manager's".** `AsyFramManager.get_chunk()` constructs chunks with `logger=self.pr`, the manager's RAM-only logger (`asy_fram_manager.py:665-674`). Chunk wrnno 60/70 therefore land in the non-persisted FRAM log.
15. **Doc drift, SPEC A.2 on the supervisor.** It says the loop "stops feeding the watchdog and lets it force a hard reset". The code calls `reboot_system()`, a timed `machine.reset()`, and the WDT is only the fallback. The `_reboot` comment at `system_service.py:127-128` is similarly off: the supervisor does not use watchdog-starve past `_TASK_FAIL_MAX`.
16. **Memory discipline inconsistent with the G.2 buffer-ownership rule (`print_log.py:249, 262`).** Every persisted log entry allocates a fresh `AsyFramChunkBuffer`, which also carries a never-used `asyncio.Lock` from `Lockable`, instead of one long-lived buffer per logger. No src code does `async with` on any `LockableBuffer`, so its lock is dead weight everywhere (`base_classes.py:54-56`).
17. **`system_service.py:317`: debug-level precedence.** `_set_dict_cfg`/`setup()` push the persisted DebugLevel to every registered logger, overriding the `debug=` argument given to `build_system`/`main`. The constructor `debug` only lasts until `sysfunct.setup()`. If the cfgmgr is invalid, `level is None` and `_current_debug_level` stays 0 while the loggers keep their constructor level, so `get_debug_level()` reports the wrong value. CFGMGR loggers never receive `debug` at all (`config_manager.py:220`).

**Just worth checking**

18. **`system_service.py:398-401`: supervisor-triggered reboot does not flush.** Unlike the REST path, it skips `_flush_pending_configs`. `start_and_check_tasks` returns, `main()` ends and `asyncio.run` completes, so staged flush tasks never run.
19. **`config_manager.py:390-400`: `flush_pending()` is unguarded.** A flush task that died with an unexpected exception type re-raises through `_system_cmd_callback`, and the reboot is then never issued; the dispatch catches it as errno 2. Also inferred: after the loop's exception handler has consumed a failed task's exception, what re-awaiting that task does needs checking against the pinned `extmod/asyncio`. The same question applies to `_log_dead_task` at `system_service.py:184-196`.
20. **`config_manager.py:299-347`: two schema sources.** `write_config` validates against the caller's `cfg_vals`, while `setup()`/`_cache` use `self.cfg_vals`, so there are two sources of truth. A key present in `cfg_vals` but not in the cache gives errno 13 "Failed", and a spurious errno 8 through the `_set_dict_cfg` snapshot.
21. **`config_manager.py:319, 330`: bad client input spends error-history slots.** Each invalid key in a PUT is a persisted *error* (errno 10/12) and a FRAM write while `config_lock` is held. Bad input can evict real fault evidence from the 10-slot ring, which is contrary to the repeat-rule philosophy.
22. **`system_service.py:158-159` and SPEC C.9.1 (the stagger proof).**
    - The first starter runs at offset 0, not strictly inside (0,1000).
    - Offsets are relative to each callback's actual run time, so latency accumulates.
    - SCD30's 500ms base tick makes the modulus 500ms. `int(1000/(N+1))*j == 500` for N = 3, 7, 9, …, which contradicts the claim that SCD30's arming ticks never coincide.
23. **`system_service.py:209-214`: silent partial timer start.** If `_timer_sequencer` cannot arm the next step, the remaining starters are skipped silently (only `pr.err`). Those drivers' read tasks then wait forever on flags that are never set, and the supervisor cannot see it (it only checks `done()`).
24. **`codegen.py:367, 431`: dead generated global.** `timers_running = ThreadSafeFlag()` is created in every generated module and never used, together with its import.
25. **API surface with no src caller (dead or test-only):**
    - `api_response.parse_cmd_request` (the webserver re-implements it as `_body_as_dict`, a G.1 duplicate), catalog codes 2-5, and `handle_set_cmd`'s `ok_descr`.
    - `SystemService.get_debug_level`, `set_debug_level`, `stop_uptime_timer`.
    - `LockedFlag`; `type_or_range_error(check_special=)` is never passed False.
    - `SensorReader(logger=)` has no caller.
    - `CRC16`, `rel_humidity`/`abs_humidity`, `Framing_COBS`.
26. **`base_classes.py:163-171`.** The comment says `self.pr.name` and `self.name` "always agree regardless of branch", but the `logger=` branch does not enforce it.
27. **`base_classes.py:47-50`.** `Lockable.__aexit__` swallows `RuntimeError` on a double release, which masks a real lock-discipline bug.
28. **`print_log.py:189-191`.** `get_log()` reports ErrNum 128 for a raw 0x80 "N" entry (unreachable except via FRAM contents).
29. **`print_log.py:161-166`.** An `errno=0` call still increments `err_count` but never writes FRAM, so RAM and FRAM counts can diverge. There are no such callers today.
30. **`crc_checks.py:104-111, 125-126`: pass mode skips validation.** `add_into`/`check_from` return the size without checking `start`/`size` bounds, unlike real mode. `add()`/`check()` in pass mode return the caller's own object, while real mode returns a copy (an aliasing difference).
31. **`crc_checks.py:48`: CPU cost of the per-byte yield.** `sleep(0)` after every byte, possibly while a bus lock is held (FRAM path).
32. **`config_manager.py:282-289`.** `get_int_values()` uses `int()`, which silently truncates a float-typed field or converts a `bool`, unlike `get_bool_values()`'s strict type check.
33. **`math_helpers.py`.** `altitude_baro` returns a pressure, so the name is misleading. The `abs_humidity` comment calls 7.6/240.7 "ice-phase" constants, but in the literature they are the supercooled-water pair (ice is 9.5/265.5). This mismatches `dew_point`'s Sonntag ice branch. Both are legacy-identical and unused in src.
34. **`system_service.py:238-239`.** wrnno `n+1` depends on each device's starter order, so a persisted W-code means different tasks on different devices and firmware versions, and it must stay ≤127.
35. **`asy_webserver_service.py:419-432`: two setter-dispatch paths.** `PUT /sensors` calls `module._set_dict_cfg()` directly, with no `handle_set_cmd` errno-99 guard and no post hook, while settings routes go through `handle_set_cmd`.

---

##### 6. Suggested audit topics and questions

1. **Supervisor semantics.** Is restarting via the *same captured starter* safe for every task? `status_counter` is not. Should a hung-but-alive task, such as an async deadlock or a flag that is never set, be detected by heartbeats? Should restarts back off?
2. **Watchdog budget end to end.** Measure worst-case time between feeds: WDT creation → first setup feed, the last setup feed → first supervisor feed (`start_timers` + `pr.setup` + stagger + N collects), and a supervisor scan with k dead tasks. What reliably separates a commanded reset from a WDT reset? No `machine.reset_cause()` is recorded anywhere in `src/`.
3. **Alarm-pool budget.** Count every simultaneously armed `machine.Timer` per device against the rp2 alarm-pool limit (needs source verification). Which `ENOMEM` fallbacks leave silent, non-persisted degradation?
4. **Timer-callback robustness.** Enumerate every ONE_SHOT soft timer and what a dropped callback costs.
5. **Logger lifecycle.** Confirm every FRAM-backed logger's `setup()` site. Pin the race between pre-setup errors and `setup()`/`reset()`. Is the RAM/FRAM state consistent under concurrent `err_s` calls (does chunk-lock FIFO ordering matter)? Verify that `set_level_setters` sees every logger that is ever created.
6. **Config persistence.** Should `setup()` distinguish ENOENT from other errors? Verify littlefs atomicity of `open("w")` + `json.dump` under power loss. Check two-writer and reboot-flush coverage, and the unsupervised flush task's exception path. Should `cfg_vals` be a separate parameter at all, instead of `self.cfg_vals`?
7. **Setter dispatch.** Serialization per module, concurrent-PUT ordering of pushes, the recovery-chain interaction with concurrent writes, "Unchanged" never re-pushing a diverged chip, and post-hook failure reporting.
8. **Validation primitives.** `type_or_range_error`/`coerce_numeric` edge cases on the single-precision rp2 float (int→float precision gap, bigints, ±inf/NaN), `special`-set typing, and whether buildgen or tests statically reject a malformed schema (int bounds on a float field, a tuple `special` on a special-alone field).
9. **MicroPython-version checks (D.9).** For the pinned 1.29 rp2 config versus the Unix test build:
   - asyncio re-await semantics of a finished Task, and `Lock` FIFO ordering;
   - `const()` of floats, tuples containing None, and strings;
   - deque features (non-empty initial iterable, `len`/iteration/`extend`);
   - `time.mktime` range/epoch and `random` seeding.
10. **Error-code catalogue.** Codes still inside the reserved 1-9 range (config_manager, system), the dynamic wrnno, `repeat=` use in the core modules, and whether user-input errors belong in the fault history.
11. **Memory churn.** Per-log-entry buffer and Lock allocation, `pr.all()` argument tuples on hot periodic paths, the `write_config` dict copy, the CRC `add()`/`check()` copies, and conformance with G.2's "one long-lived buffer per record".
12. **Doc/code consistency.** Items 10-15 above, the C.9.1 proof's assumptions, the A.7 setup order, and a D.10 sweep: `SystemService` duplicating `SensorReaderConfig._set_dict_cfg` with different "Unchanged" push semantics, and `get_error_sources` shapes.
13. **Dead code and API trimming.** Decide on item 25, keeping in mind frozen-bytecode cost.
14. **Codec/CRC contract.** Pass-mode validation parity, and the COBS scratch-aliasing contract: is `encode_into`'s returned view protected by the UART write lock until transmission finishes?

---

## Driver layer (buses, sensors, FRAM, UART, LED)

### Hardware driver layer survey (`src/`), read-only

**Scope.** I read all 14 modules in full (8,291 lines), plus SPECIFICATION Parts C, F.2, F.3, F.5 (.1, .2, .7–.9), J and M, and the supporting code these modules call (`base_classes.py`, `print_log.py`, `crc_checks.py`, the math_helpers fragments, `buildgen/codegen.py`'s UART block, `devices/dev.toml`). Nothing in the repo was changed and no hardware was touched. To read the datasheets I pip-installed pypdf into the scratchpad only and extracted their text to `/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/txt_*.txt`. Those files can be reused for the audit.

**Labels used below:**
- **[VERIFIED]**: read directly in code or a datasheet.
- **[INFERRED]**: reasoning I have not run.
- **[EMULATED]**: checked with CPython arithmetic, using struct round-tripping to imitate float32.

---

#### 1. Per-module summary

##### asy_i2c_driver.py (368 lines): bus layer, no logger
- **`I2C`** wraps `machine.I2C`.
  - It holds a shared `async_lock` and one long-lived 32-byte `_scratch` per bus (`_SCRATCH_SIZE`, line 19). Reads larger than 32 bytes allocate a buffer instead.
  - Main methods: `get_bits`/`set_bits` (read-modify-write with no await between the read and the write; the value is masked to `num_bits`), `get_register_struct`/`set_register_struct` (byte order comes from the format string), `readfrom_into`, `writeto`, `writeto_then_readfrom`, `scan`, `init`/`deinit`.
  - `init()` always calls `deinit()` first. `deinit()` is a no-op on rp2, and only 1.29+ has it at all (F.5.1).
- **`I2CDevice(Lockable)`** binds one address to the bus lock.
  - `_probe_for_device()` does a zero-byte `writeto`: `OSError` becomes `ValueError`, and a `None` return becomes `RuntimeError`.
  - Its async forwards (`get_bits`, `write`, `readinto`, …) contain no awaits of their own.
- **Contract:** a real `OSError` always propagates. `None` is returned only when the bus is uninitialised, the bitfield is out of range, or the format is malformed.

##### asy_spi_driver.py (213 lines): bus layer, sole consumer is FRAM
- **`SPI`**: `init`/`deinit` (no-op on rp2), and `configure()`, which raises unless the bus lock is held and calls `machine.SPI.init(...)`.
  - `write()` cannot raise on rp2. `readinto()` can raise `OSError(EIO)` on reads of 32 bytes or more (F.5.2).
  - `write_readinto()` swallows `ValueError` and returns `None`.
- **`SPIDevice(Lockable)`**:
  - Synchronous session primitives: `session_begin()` runs `configure`, asserts CS, then a blocking `sleep_us(2)` (`_CS_SETTLE_US`); `session_end()` deasserts CS.
  - `write_sync` / `readinto_sync` / `write_readinto_sync`.
  - The async `__aenter__`/`__aexit__` yield once, after the lock is released.
  - Readiness gate: `initialized`, set in `setup()`.

##### asy_uart_driver.py (455 lines): bus + CRC + codec in one class (C.3.2)
- **`UART(Lockable)`**.
  - `init()` always constructs a new `machine.UART` rather than calling `.init()` on the old one (F.5.7). It registers a `select.poll` for POLLIN|POLLOUT.
  - Two poll rates: `poll_wait_ms` is used when a wait has a deadline, `poll_idle_ms` when it does not (F.5.9).
- **Never-block design:**
  - `_buffered()` (line 118) clamps every read to `uart.any()`.
  - `ready()` always ends with `sleep_ms(0)` (line 294).
  - `_read_delimited()` yields every 16 bytes (`_DELIMITED_YIELD_BYTES`).
- **Cancel handshake:** `cancel_read_timeout()` uses a latched request and two monotonic counters (`_cancel_req`/`_cancel_ack`). The acknowledgement happens in `ready()` and in `__aexit__`. The wait is bounded by `_CANCEL_ACK_TIMEOUT_MS`=1000, and an unacknowledged cancel increments `cancel_unacknowledged`.
- **Framing:** CRC (`CRC_Pass` by default) and codec (`Framing_Pass` by default). Write order is build → CRC → encode; read is the reverse.
- **Public API:** `read`, `read_until_complete`, `readinto`, `readinto_until_complete`, `readline`, `readline_until_complete`, `write`, `writefrom`, `resync_framing`, `deinit` (returns a bool).
- Every method returns a sentinel; nothing raises.

##### asy_uart_comm.py (1149 lines): protocol class `UART_Comm` (Part J)
- **Frame:** `UID|CMD|SIZE|CHUNKS|CUR_CHUNK|payload[payload_size]`, header length 5.
  - Commands: ACK 0x01, GET 0x02, SET 0x04.
  - UID wraps 0xFE → 0 and is never 0xFF (`_next_uid`, line 161).
- **Transfers:** stop-and-wait, one ACK per frame, no NAK.
  - A SET train has `CHUNKS = max(ceil(n/payload_size)+1, 2)` (line 437).
  - A GET is a one-frame request answered by a SET train in the reverse direction.
  - The final ACK is withheld until the total-size check passes.
- **Recovery:** `_fault()` → `_err()` → `_resync()`.
  - `_resync` drains until the line has been quiet for 1.5×timeout, bounded at 4× that window (`_RESYNC_NUM/DEN`, `_DRAIN_BOUND_MULT`), then holds off writes for another 1.5×timeout (`_await_write_gate` polls a deadline in steps of at most 20 ms).
  - The diagnostic for a link that never produces a valid frame is errno 32, raised after 2 "blind" resyncs.
- **Construction checks** (`_validate_config`, line 230): codec ready, `payload_size` in 1..255, role, timeout ≥ `2*poll_wait_ms + poll_idle_ms + 21`, `rxbuf` ≥ max(one framed frame, one poll interval's worth of bytes).
  - Buffers are preallocated once: tx/rx `LockableBuffer`, ack scratch, zero padding, command scratch, and a 32-byte bitmap of rejected command ids.
- **Public API:**
  - Initiator: `uart_set`, `uart_set_into`, `uart_set_stream`, `uart_get`, `uart_get_into`, `uart_get_stream`.
  - Responder: `uart_listen` → `ListenResult`.
  - Also `clear()`, `setup()`, `_listen_loop` (exponential backoff from timeout/2 up to 5×timeout), `get_task_starters` (responder only).
- **Errno table:** errno 10–34, wrnno 10–14 (C.7.1).

##### asy_uart_link_driver.py (160 lines): `UartLinkExerciser`
- A bench-only wrapper. Its responder answers command 0x01 with a banner and 0x02 with an echo. Its initiator runs `_exercise_loop`, a GET every 1000 ms that counts `transfers`/`failures`.
- The tag is `@wiring fram_target … optional kwarg`. It is not a SensorReader and has no `_VAL_*`.

##### asy_scd30_driver.py (630 lines)
- **Layering:** `SCD30_Reader(SensorReader)` (no ConfigManager; all settings live in sensor NVM), `SCD30_DeviceSession`, and `SCD30_I2C`.
- **Protocol class:**
  - 16-bit commands with CRC-8 (poly 0x31, init 0xFF) per 16-bit word, and an 18-byte buffer.
  - Every command and every register read sleeps 50 ms (`_send_dev_command` line 471, `_read_dev_register` line 483).
  - `read_measurement()`: data-ready check, then read command, then an 18-byte read, then 6 CRC checks, then 3 big-endian floats (">f"), then a finiteness check.
  - `setup()`: probe, firmware-version read (only its CRC is checked, not the value), then soft reset and a 2.5 s wait.
- **Schema:**

  | Field | Type | Range |
  |---|---|---|
  | `TempOffs` | float | 0..655.35 |
  | `MeasInt` | int | 2..1800 |
  | `AmbPres` | int | 700..1400, special value 0 |
  | `Altitude` | int | 0..65535 |
  | `ForceCalRef` | int | 400..2000 |
  | `SelfCal` | bool | — |

  All defaults are `None`. `ContMeas` exists only as a free-standing `@web` tag, dispatched by hand in `_set_dict_cfg`.
- **Tags:** `@requires bus.timeout>=200000`, `@requires bus.frequency<=100000`, `@wiring fram_target`.
- **Triggering:** a Timer (500 ms) sets `base_trigger_event`. The RDY pin's rising IRQ sets `read_event`. `scd_init_irq` is a fallback that forces a read after `2*trigger_sec` half-second ticks.
- **Outputs:** CO2, Temp, Hum, WetBulb, DewPoint (via math_helpers), TS.

##### asy_sgp40_driver.py (690 lines)
- **Layering:** `SGP40_Reader(SensorReaderConfig)`, `SGP40_I2C`, and two default compensation sources (25 °C / 50 %RH).
- **Schema:** `BackupPeriod` 0..1440 min (default 1), `BackupMaxAge` 0..10080 min (default 7200), `WaitTimeNTP` 0..600 s (default 30), and the command-only `SGPResetVOC`.
- **Tags:** `@requires bus.frequency<=400000`; `@wiring fram_target … fram_storage`; two required `@value-wiring` entries (temperature, humidity).
- **Protocol class:**
  - Measure command 0x260F with RH/T ticks + CRC. The wait is 100 ms against a 30 ms datasheet maximum.
  - `initialize()`: serial read (one word only, which must be 0x0000 — an assumption inherited from Adafruit), self-test (high byte 0xD4, 500 ms wait), then a general-call reset (address 0x00, byte 0x06) and a 1 s wait.
  - The delay sleep happens outside the bus lock but inside the device-session lock.
- **Reader:**
  - 1 Hz Timer drives the VOC algorithm (`measure_index_and_raw`).
  - FRAM timestamped CRC32 backup/restore of the 256-byte VOC state (`_check_storage`, `_run_restore`, `_run_backup`), with an NTP wait countdown (`voc_init`/`voc_write`) and a `set_verify` period.
  - The reset is two-phase: the FRAM clear and the algorithm reset are tracked separately.
- **Outputs:** VOC, Raw, TS.

##### voc_algorithm.py (797 lines)
- A port of Sensirion's Q16.16 fixed-point VOC algorithm via DFRobot's Python.
- Internals: `_fix16_mul`/`div`/`sqrt`/`exp`, a mean-variance estimator with sigmoid gating, the MOX model, a scaled sigmoid, and an adaptive low-pass.
- Blackout of 45 samples; sraw is clamped to 20001..52767.
- The state is 32 fields packed as `"32q"` (256 bytes).
- Per F.4 its naming is deliberately non-compliant.
- I checked `vocalgorithm_process`'s order and the `_fix16_mul`/`_fix16_sqrt`/`_fix16_exp` shapes against the libfixmath/Sensirion C from memory [INFERRED match]. The C source is not in the repo.

##### asy_bmp3xx_driver.py (646 lines)
- **Layering:** `BMP3xx_Reader(SensorReaderConfig)`, `BMP3XX_I2C`. Measurements use forced mode (PWR_CTRL=0x13).
- **Schema:**

  | Field | Type | Range / values | Default |
  |---|---|---|---|
  | `SampleInterv` | int | 1..3600 | 2 |
  | `PressOvers`, `TempOvers` | int | {1,2,4,8,16,32} | 1 |
  | `FiltCoeff` | int | {0,1,3,7,…,127} | 0 |
  | `PressOffset` | float | ±500 hPa | 0 |
  | `TempOffset` | float | ±10 | 0 |
  | `SeaLevelOffs` | float | −1000..5000 m | 0 |
  | `MeanAtmTemp` | float | −50..50 | 15 |

- **Tags:** `@limits address in {0x76,0x77}`, `@limits trigger_sec 1..3600`.
- **Identity:** chip ID 0x50 (BMP384/388) or 0x60 (BMP390).
- **Calibration and compensation** [VERIFIED against the datasheet's sec 9.1–9.3 formulas]:
  - The 21-byte calibration block is rejected if it is all 0x00 or all 0xFF, then unpacked with `<HHbhhbbHHbbhbb`. T1..P11 scaling matches.
  - Range gate: 300–1250 hPa and −40..85 °C.
- **Reset:** wait for cmd_rdy, write 0xB6, wait 2 ms, check ERR_REG.
- **Data-ready wait:** status is polled every 2 ms for up to 300 ms.
- **Outputs:** Pres, Temp, SLPres (from `math_helpers.altitude_baro`, with `dh = -SeaLevelOffs`), TS.

##### asy_isl29125_driver.py (1448 lines, Part M)
- **Layering:** `ISL29125_Reader(SensorReaderConfig)`, `ISL29125_I2C`.
  - The protocol class keeps a **shadow** of CONFIG1–3 and writes the minimal burst from `configure()`. On a failed write it rolls the shadow back and increments `_write_failures`.
  - Other protocol methods: `read_status()` (a destructive read, once per cycle), `read_counts()` (6-byte read, G/R/B), `set_thresholds()` (rescales to the active resolution), `normalise()` (12-bit shift by 4, dark offset of 1 count on the low range, raw saturation check), `persist_for_interval()` (derives PRST), `matches_shadow()` (masked comparison), `reset()` (0x46, then verify the config reads 0x00).
- **Schema:** `SampleInterv`, `Resolution` {12,16}, `RangeAuto`, `Range` {375,10000}, `AutoRangeThresh` 50–95 %, `AutoRangeDwell` 0–300 s, `IrCompOffset` {0,1}, `IrCompAdjust` 0..63 (default 40), `FiltCoeff` −1..1, `GainRatio` 20–34, and the command-only `ISLCalibrate`.
- **Reader behaviour:**
  - Auto-range state machine: peak of all three channels, switch-up threshold, switch-down at `thresh/53.33`, a dwell, settling after a switch, and a "dead INT line" detector that warns (wrnno 13) after 5 decisions in a row made by the periodic path.
  - Brownout recovery and divergence re-apply.
  - EMA filter.
  - Colour outputs: HSB, CCT (McCamy, with a floor of 64 counts).
  - Calibration: measure on one range, the other, then the first again; results published as `GainMeas`.
  - `get_dict_data()` returns nested dicts.

##### asy_fram_driver.py (432 lines): `FRAM_SPI(Lockable)`
- **Identity:** RDID bytes 0x04/0x7F plus product ID looked up by `max_size` (0x2000 → 0x0302, 0x40000 → 0x4803). Address width is 3 or 4 bytes depending on size.
- **Locking:** `__aenter__` takes the driver lock, then the bus lock, and holds both for a whole block operation. The byte-level `get_values_sync`/`set_values_sync` return status bits, which `report_*` then turns into log entries.
- **Writes:** WREN then an RDSR check of WEL; WRITE; WRDI with one retry.
- **Write protection:** WPEN|BP1|BP0 = 0x8C, protecting the whole array. The WP pin is active-low.
- `verify_present()` waits at most 1 s for the lock.
- errno 89–100, wrnno 81–84.

##### asy_fram_manager.py (740 lines): `AsyFramManager` plus chunks
- **Allocator:** bump-pointer. Each chunk takes `2×(size+crc+2)`, i.e. two blocks.
- **Block layout:** `[data][crc][status1][status2]`.
- **Block write:** status bytes set to BUSY, then payload + CRC, then status bytes set to IDLE.
- **Block read:**
  - Check both status bytes are IDLE, then set them BUSY.
  - Read with an incremental CRC; the whole block must arrive in one iteration (`_read_iters == 1`).
  - Set the status bytes back to IDLE.
- **Dual copy:** if block 0 is invalid, read block 1 and repair block 0. If block 0 is valid, compare it with block 1 and repair block 1 when needed. Two valid blocks that differ is a hard failure (errno 73).
- **Other:** optional write-verify every N writes; `mempause` gating; timestamped chunk with 8-byte `<Q` UTC and NTP-gated writes; the repeat rule via `_episode_wrn`.

##### asy_neopixel_driver.py (187 lines): `NeopixelDriver`
- **Overlay:** on/off/toggle via a `ThreadSafeFlag` task.
- **Signals:** internal (`request_signal`) and external (`led_signal`) signals are arbitrated through `start_signal_lock` and `start_signal_event`, then drive a ramp up and down.
- Numeric inputs are sanitised with `_clamp_byte` and `_MIN_SIGNAL_S` (0.1 s floor).
- It keeps a logger but persists nothing.

##### asy_notification_service.py (376 lines)
- `NotificationSignal` holds one condition: source, field, a one-field threshold schema, a colour, and above/below.
- `NotificationCoordinator(SensorReaderConfig)` uses staged construction: `register()` then `finalize()`, which calls `super().__init__`.
- **Schema:** `OnH`, `OnM`, `OffH`, `OffM`, `FlashBri`, `Interv` (60–3600), `FlashDur` (0.5–10), `AutoOn`, plus per-signal thresholds injected at runtime.
- **Tasks:** `monitor_loop` (same-day on/off window, then check → signal → `sleep(2*flash_dur)`) and `auto_led_override` (1 s countdown).

---

#### 2. Consistency with Part C

**Matches:**
- Every I2C driver has the `*_DeviceSession(Lockable)` boilerplate and the layer-2-raises / layer-3-never-raises split.
- Every driver exposes `get_data`/`get_dict_data`/`get_dict_cfg`/`get_error_counter`, uses the `read_loop` shape with `_error_check`, has `_NAME` equal to its namedtuple name, and starts errno at 10 for init.

**Divergences:**
- **Constructor order (C.2).**
  - `ISL29125_Reader` makes everything after `irq_pin` keyword-only and puts `irq_pull_up` *after* `history_length` (`asy_isl29125_driver.py:197-212`).
  - SGP40 names its FRAM parameter `fram_storage` and adds `fram_ntp_callback` (lines 140-141); the others use `fram`.
- **Snapshot-read failure logging.**
  - BMP catches locally with errno 22 (`asy_bmp3xx_driver.py:174-178`) and ISL with errno 28 (`:720-727`).
  - SCD30 relies on the base catch (`asy_scd30_driver.py:147-159`), which logs the reserved base errno 4 (`base_classes.py:209-210`).
  - The BMP comment claims the base catch would "skip the dict update". That is accurate, but since SCD30 accepts that outcome, the three drivers behave differently.
- **Scratch buffers (C.3).** The spec says BMP3XX "has no scratch buffer; helpers allocate internally". The I2C layer now has a shared per-bus scratch (`asy_i2c_driver.py:33-36`), so the text is stale.
- **FRAM_SPI buffers (C.3, SPECIFICATION.md:1544-1545).** The spec says `_check_device_id()`/`_read_status()`/`_send_opcode()` allocate a fresh buffer on every call. The code preallocates them (`asy_fram_driver.py:118-121`), and `_send_opcode` no longer exists. **[DOC DRIFT]**
- **UART repeat rule (C.7.1, SPECIFICATION.md ~1908-1919).** The spec says three modules, `asy_uart_comm.py` among them, pass `repeat=True`, "which still counts it". `UART_Comm._err` sends repeats to `self.pr.err()`, which is sync, not persisted **and not counted** (`asy_uart_comm.py:319-322`; `print_log.py:158-175`). So UART repeats never appear in `ErrCount`. **[DOC DRIFT or behaviour gap]**
- **FRAM chunk logging (C.7.1 row, SPECIFICATION.md:1926).**
  - The row says "the chunk logs into its OWNER's FRAM-backed history, not the manager's". The code passes `logger=self.pr`, the **manager's in-memory** `PrintLogHistory` (`asy_fram_manager.py:622, 672, 716`). **[DOC DRIFT]**
  - The same row says "manager `errno` 17-88", but the code uses errno 10/11 (`_write_chunk` err=10, `:274`) and 19/20. **[DOC DRIFT]**
- **Unprefixed struct format.** VOC state uses `"32q"` with no byte-order prefix (`voc_algorithm.py:98,141`). F.1 says layouts stored on chip should be pinned with `"<"`. The size is the same on both targets, so this is a consistency point only.
- **Operating-range checks.** BMP has a plausibility gate; SCD30 only checks finiteness (`:626-627`), with no CO2/RH/T range gate even though C.3 says "operating-range checks live here".
- **UART vs. the other buses.** UART merges its layers into one class and never raises, which C.3.2 sanctions.

---

#### 3. Concurrency, locking and blocking

**Lock layers.**
- Layer 2 is the device-session lock (`*_DeviceSession`, and FRAM_SPI's own lock). Layer 1 is the bus lock. They are always taken in the order 2, then 1.
- FRAM takes both for a whole block operation (`asy_fram_driver.py:127-137`).
- UART has only one lock. `cancel_read_timeout` infers "a read is in flight" from `locked()`.
- UART_Comm adds a `_busy` flag that refuses re-entry rather than waiting (line 200).
- FRAM chunks have a per-chunk `_op_lock` that spans both blocks.

**Shadow and cached state.**
- ISL keeps its CONFIG shadow under the session lock, including the rollback (lines 1341-1378).
- SCD30 caches the last CO2/T/RH.
- BMP and ISL use `LockedValue` for `trigger_period`.

**Loop-blocking synchronous spans:**
- I2C: one synchronous transaction each. SCD30 clock stretching can reach 150 ms once a day (bus timeout 200 ms) [VERIFIED datasheet p.2]. An 18-byte read at 50 kHz is about 3 ms [INFERRED].
- SPI/FRAM: at most 2.8 ms per stretch; a whole block holds the bus for about 21 ms (F.5.8, measured).
- UART: clamped to ≤278 µs per call. Two remaining unyielded loops:
  - `_read_delimited`'s delimiter/skip branches (`asy_uart_driver.py:171-176`) consume buffered bytes without yielding; this is bounded by `rxbuf`.
  - `_write_all` waits on `ready(POLLOUT)` with no timeout, so a write stall polls at the *idle* rate with no deadline (`:135`, `:267`).
- CRC: `_crc` yields after every byte (`crc_checks.py`), which is good.
- VOC algorithm: `vocalgorithm_process` is one synchronous block of pure-Python fixed-point arithmetic, once per second. Its cost on the target has never been measured **[WORTH CHECKING]**.

**Bus lock held across `asyncio.sleep` (other devices on the bus stall, the loop does not):**
- SCD30 sleeps 50 ms inside the bus lock in `_send_dev_command` and `_read_dev_register`.
  - `get_config_snapshot` holds i2c1 for at least 6×50 ms (`asy_scd30_driver.py:514-520`).
  - On `dev`, i2c1 also carries SGP40, which needs an exact 1 Hz read, and ISL29125.
- `I2CDevice._probe_for_device` sleeps 2×100 ms under the bus lock during every driver's `setup()` (`asy_i2c_driver.py:261-271`).

---

#### 4. Error handling per driver

| Module | Raises / catches | Codes |
|---|---|---|
| I2C | Propagates `OSError`; returns `None` for an uninitialised bus, a bad bitfield or a malformed format; probe maps errors to `ValueError`/`RuntimeError` | none (no logger) |
| SPI | `configure` raises `RuntimeError` for misuse; EIO propagates; `write_readinto` swallows `ValueError` | none |
| UART driver | Never raises; `(OSError, MemoryError, TypeError)` are caught in `ready`; `deinit` returns a bool | none |
| UART_Comm | Never raises. Every fault goes through `_fault` (errno) and a resync. `_call` guards callbacks. A dedupe keyed on the last errno; one persisted warning per episode; a per-id rejection bitmap. | errno 10–34, wrnno 10–14 |
| SCD30 | Protocol layer raises `RuntimeError` (CRC), `ValueError` (range/NaN/non-finite), `OSError`. Reader catches each call with its own errno. | 10, 11, 13–25 (12 unused) |
| SGP40 | Protocol raises `RuntimeError` (CRC, serial, self-test). `_reset` swallows the general-call `OSError`. Reader logs errors 10–18 and warnings 10–13 (backup missing/stale). | as listed |
| BMP3xx | Raises `OSError` (reserved encodings, timeouts, short reads), `ValueError` (range), `RuntimeError` (chip ID, calibration, cmd_err) | errno 10–22 |
| ISL29125 | `_reject_unless`/`_reject_outside` raise `ValueError`; `OSError` on reads. Reader logs errno 10–35 and 38; 23, 36 and 37 are unused. Warnings: 10 brownout, 11 divergence, 13 dead INT. | as listed |
| FRAM_SPI | Only `setup` raises (`OSError`/`ValueError`). Status bits are mapped to codes. | errno 89–100, wrnno 81–84 |
| FRAM manager | Never raises; a blanket `except Exception` around each block operation | errno 10–88, wrnno 60, 70–73, 80 |
| Neopixel | Nothing persisted | — |
| Notification | Callbacks are guarded | errno 10–13, wrnno 1–5 (inside the reserved range, per C.7.1) |

---

#### 5. Audit candidates

##### SGP40 / VOC
1. **[SUSPICION, strong] `_command_buffer` stays aliased after a failed read.**
   - `SGP40_I2C.get_raw()` sets `self._command_buffer = self._measure_command` and restores it *without try/finally* (`asy_sgp40_driver.py:608-612`).
   - Any `OSError` or CRC `RuntimeError` in `_read_word_from_command` leaves the alias in place. The reader keeps the same `SGP40_I2C` object across supervisor restarts.
   - On the next restart, `initialize()` writes 0x36/0x82 and then 0x28/0x0E into the **8-byte** measure buffer and sends all 8 bytes as the serial-number and self-test commands (`:669-683`).
   - I found no test covering this.
2. **[SUSPICION, verified by arithmetic] FRAM verify period is wrong.**
   - The formula is `int(math.ceil((10*60)/p)*0.1)` (`:352, :409`).
   - For `BackupPeriod` 67–1440 it returns **0**, which disables write verification. For example p=7 gives 8, while the intended `ceil(60/p)` would be 9.
3. **[SUSPICION] Compensation ticks wrap instead of clamping.**
   - `_celsius_to_ticks`/`_relative_humidity_to_ticks` mask with `& 0xFFFF` (`:595, :602`).
   - RH −1 % gives 64882 (about 99 %), RH 101 % gives 654 (about 1 %), and T 131 °C gives about −44 °C.
   - Neither SCD30 values nor the `_Default*` sources are clamped before this point.
4. **[WORTH CHECKING] VOC = 0 is stored as a valid reading** during the 45-sample blackout after every init or reset (`voc_algorithm.py:761-762,780`; `_store_sgp` at `:444-447`). The datasheet's index range is 1–500.
5. **[WORTH CHECKING] Python integers do not wrap like C int32.**
   - `_FIX16_OVERFLOW`/`_FIX16_MINIMUM` are the positive 0x80000000 in Python, but C's value is INT32_MIN (`:41-43`).
   - In `_fix16_div`, the `if not bit` overflow check (`:248`) can never trigger in Python.
   - `F16(1)+FIX16_MAXIMUM` in the sigmoid denominator (`:628, :675, :688`) wraps negative in C but stays positive here.
   - These only diverge at the extremes; a differential test against the C reference would settle it.
6. **[WORTH CHECKING] FRAM read frequency during the NTP wait.** `_run_restore` re-reads the 260-byte chunk every second while `voc_init` counts down, for up to 600 s (`:212-215, 383-385`).
7. **[WORTH CHECKING] Unverified serial-number check.** `word[0]==0x0000` is not documented by Sensirion (`:674-678`); the code comment already says so.

##### SCD30
8. **[SUSPICION, same as legacy] Stale values re-stamped as fresh.**
   - `scd_timer_triggers` accumulates across cycles and is reset only at a read, despite the comment saying "consecutive" (`asy_scd30_driver.py:412-420`).
   - The `read_event.set()` fires whenever the count reaches the threshold, even when the RDY pin is low.
   - That forced read finds data not ready, and `read_measurement` returns without changing the cache (`:610-611`). `_read_scd` then returns the cached values with a **new timestamp** (`:174-187`).
   - Legacy has identical logic (`python/IndividualDrivers/asy_scd30_driver.py:142-144`).
9. **[VERIFIED, float32 emulated] Temperature-offset truncation.** `int(offset*100)` (`:570`) writes 0.01 K too low for about 6.5 % of 0.01-step values between 0 and 20. Examples: 0.53 → 52, 1.05 → 104, 2.10 → 209.
10. **[WORTH CHECKING] Undocumented register read.** `get_ambient_pressure()` reads command 0x0010 (`:495-496`). The Interface Description (1.4.1) documents 0x0010 only as a write; the read comes from Adafruit's driver.
11. **[WORTH CHECKING] Bus held for 50 ms sleeps.** See section 3; cross-device latency on i2c1 and SGP40's 1 Hz timing need checking.
12. **[WORTH CHECKING] No CO2 plausibility gate.** The datasheet range is 0–40000 ppm, and a CRC-valid finite outlier passes (`:621-630`).

##### BMP3xx
13. **[SUSPICION] `MeanAtmTemp` range mismatch.** The schema allows −50..50 (`asy_bmp3xx_driver.py:84`), but `altitude_baro` requires −40..85 (`math_helpers.py:25-26,92`). Values in [−50, −40) make SLPres silently `None`.
14. **[WORTH CHECKING] Plausibility gate runs before the offset.** It is applied before `PressOffset` (±500 hPa) (`:237`), so a published `Pres` can fall outside the datasheet range and SLPres then becomes `None` without a log entry.
15. **[WORTH CHECKING] Dead code.** `get_altitude()`, `get_pressure()` and `get_temperature()` have no callers in production (`:555-577`).
16. **[WORTH CHECKING] Compensation precision.** rp2 uses float32 while the Unix-port tests use double (SPEC F.1:3485), so the compensation formulas are never tested in float32. Bosch's reference uses double.

##### ISL29125
17. **[SUSPICION] Possible interrupt storm on the high range.**
    - In high range the chip INT is armed on green ≤ the down threshold (`:598-599`), but `_evaluate_range` decides on the **peak of all three channels** (`:577-583`).
    - In a colour-dominant scene (green below the threshold, red or blue above it), INT would fire every PRST window (about 606 ms). Each firing forces a read cycle (`_on_irq`, `:359-364`) regardless of `SampleInterv`, indefinitely.
    - The same thing happens while `AutoRangeDwell` suppresses a switch-down.
    - The low threshold of 0 in the low range fires in true darkness (0 counts) for the same reason.
18. **[SUSPICION] Thresholds not re-armed.** `set_autorange_thresh()` does not rewrite the chip's threshold registers (`:981-988`), unlike `set_resolution` (`:941-945`). The interrupt fast path keeps the old threshold until the next switch.
19. **[WORTH CHECKING] Dark offset in 12-bit mode.** The 1-count dark offset is subtracted after the `<<4`, so at 12 bit it removes only 1/16 of a 12-bit count (`:1262-1263`).
20. **[WORTH CHECKING] Filter state across restarts.** `_filtered` is never reset when a restart runs `_init_isl` (`:270`).
21. **[WORTH CHECKING] Calibration stalls the read loop.** Calibration legs run inside `_read_isl`: about 2 × (switch + 2×303 ms settle) per sample.

##### FRAM
22. **[SUSPICION] Reading an uninitialised block marks it BUSY.**
    - `_set_check_sb` writes BUSY even when it found UNINIT (`asy_fram_manager.py:235-250`), and `_read_chunk` returns early without restoring the status (`:306-308`).
    - Result: a second read of a never-written or cleared chunk reports "status byte is not 1 but 2" (errno 31/33) and "invalid" instead of "uninitialised".
    - No test reads a blank chunk twice.
23. **[WORTH CHECKING] Load-bearing logger invariant.**
    - `_write_chunk`/`_read_chunk` call `self.pr.err_s` while holding the FRAM driver lock (`:278-289, 320-355`).
    - This is safe only because the chunk logger is the manager's *in-memory* one.
    - If a FRAM-backed logger were ever passed, which is what SPEC C.7.1 says happens, the task would **deadlock** on the non-reentrant `asyncio.Lock`.
    - Nothing enforces the invariant.
24. **[WORTH CHECKING] Partial write protection goes unnoticed.** `setup()` sets `_wp` only when the status register equals 0x8C exactly (`asy_fram_driver.py:388`). A chip with BP bits partly set is treated as writable while the chip silently ignores writes to protected blocks.
25. **[WORTH CHECKING, INFERRED] Peripheral reset per CS session.** `SPIDevice.session_begin` calls `machine.SPI.init(...)` on every chip-select (`asy_spi_driver.py:133-139, 67`), about 25 times per block. I believe rp2's `init` calls `spi_init()`, which resets the peripheral. This may explain part of the measured "interpreter overhead". rp2 source is not available locally, so this needs checking.
26. **[WORTH CHECKING] Rarely-used and dead APIs.** `verify_present()`, `set_write_protected()`, `SPI.write_readinto` (whose `None` return is identical for success and a swallowed `ValueError`, `:83-97`) and `stop_timer()` have no callers in production.

##### UART
27. **[DOC DRIFT] Repeats uncounted.** See section 2.
28. **[WORTH CHECKING] GET frames not checked for CHUNKS=1.** `_validate_size_for_position` does not require a GET frame to have `CHUNKS=1` (`asy_uart_comm.py:484-488`), although J.4 says a GET is a one-chunk train.
29. **[WORTH CHECKING] Log flooding in two cases.**
    - The dedupe is keyed only on the *last* errno, and every valid frame clears the episode (`:319, :658-661`). A link alternating between two errnos, or between one good and one bad frame, persists on every fault.
    - `_ready()` calls `err_s` on every call with no dedupe (`:351-355`). If `setup()` fails, the exerciser's 1 Hz `uart_get` (`asy_uart_link_driver.py:110-120`) persists an entry every second, and `_listen_loop` returns at once, so the supervisor restarts it repeatedly. C.7.2 declares this out of scope; noted here for the audit.
30. **[FACT, VERIFIED] The dev link runs without CRC.** Codegen never passes `crc=` to `UART` (`buildgen/codegen.py:396-397`), so the bench link runs with `CRC_Pass`. A corrupted payload byte is only caught by structural validation.
31. **[WORTH CHECKING] Declined commands trigger backoff.** A declined command returns `cmd_id=None`, so `_listen_loop` backs off for up to 5×timeout (`:1116-1126`) while the initiator may already be sending again.
32. **[WORTH CHECKING] `readinto` with a large `nbytes`.** `UART.readinto(buf, nbytes)` with `nbytes > len(buf)` relies on `machine.UART.readinto` clamping to the buffer (`asy_uart_driver.py:353-354`).

##### Bus layer and others
33. **[WORTH CHECKING, latent] Silent no-ops on an uninitialised bus.** `I2C.readfrom_into`/`writeto` are silent no-ops when `_i2c is None` (`asy_i2c_driver.py:204-205, 222-223`). SCD30 and SGP40 would then CRC-check **stale** buffer contents, which pass. It is unreachable today because `init()` re-creates the bus synchronously.
34. **[WORTH CHECKING] Neopixel.**
    - `request_signal` and `_led_ext_signal_starter` busy-wait with `sleep(0)` for the whole length of a running signal (`asy_neopixel_driver.py:84-85, 148-149`).
    - Signal duration `t` has a floor but no ceiling (`:162-169`).
    - `neopixel_freq=0` raises `ZeroDivisionError` in `__init__` (`:68`).
    - `led_signal()` has no caller in the generated code.
35. **[WORTH CHECKING] Notification.**
    - `float(value)` sits outside the try block in `_check_one` (`asy_notification_service.py:218`); a non-numeric field would kill `monitor_loop`.
    - The on/off window cannot span midnight (`:369`), which the `@web` text documents.

---

#### 6. Datasheets

**Present** (`datasheets/`):
- `bmp3xx/`: BMP384 (ds003), BMP388 (ds001), AN006 self-test note.
- `fram/`: MB85RS64V and MB85RS2MTA.
- `isl29125/`: FN8424.
- `pico w/`: the Pico W board datasheet.
- `scd30/`: datasheet, interface description, design-in guide, low-power mode note, field calibration note.
- `sgp40/`: datasheet v1.2.

**Missing:**
- **BMP390** datasheet, although the driver accepts chip ID 0x60.
- **RP2040 chip** datasheet, needed for I2C/SPI/UART peripheral facts. Only the board datasheet is present.
- **WS2812/NeoPixel** LED datasheet.
- **Sensirion VOC Index algorithm** documentation or reference C source, needed to validate `voc_algorithm.py`.
- The UART peer is not a chip, but its source is `arduino/libraries/Async_UART_Comm/`.
- Renesas application notes are declared unobtainable (M.1.3).

---

#### 7. Suggested audit checklist

1. **Formulas vs datasheet.**
   - SCD30 float decode and offset units.
   - SGP40 tick conversions, including out-of-range behaviour.
   - BMP compensation in **float32**.
   - ISL lux, 12/16-bit scaling, PRST unit and threshold semantics ("≤ low" / "> high").
   - Sea-level reduction domain.
2. **VOC algorithm.** Run a differential test against the Sensirion C reference, including overflow edges and state restore (`muptime` is restored, so the blackout is skipped).
3. **float32 vs double.** Which computations differ between the rp2 target and the Unix-port test rig (SCD30 temp offset, BMP, `_f16` constants, ISL maths)?
4. **Recovery paths.**
   - SGP40 restart after a failed read (candidate 1).
   - ISL brownout, divergence and write rollback.
   - FRAM dual-copy repair, blank-chunk re-read (candidate 22) and torn-write handling.
   - UART resync, drain bound, hold-off and cancel.
5. **Stale-as-fresh audit.** For every driver, can a cycle publish old values with a new timestamp (SCD30 candidate 8, UART, ISL settle bound)?
6. **Timing budgets.**
   - Worst-case lock-hold per bus on `dev`'s i2c1 (SCD30's 50 ms sleeps, probe sleeps) against SGP40's 1 Hz requirement.
   - Measure VOC processing time on target.
   - FRAM block hold time.
7. **Interrupt semantics.** ISL INT storm conditions (candidate 17), SCD30 RDY fallback counter, soft-IRQ allocation.
8. **Config validation bounds vs helper domains** (`MeanAtmTemp`, `PressOffset`, `BackupPeriod` → verify, `FiltCoeff` sign convention, neopixel `t`/`freq`).
9. **Logging.**
   - errno/wrnno tables vs code (FRAM range drift, ISL gaps 23/36/37).
   - Repeat-rule counting vs C.7.1 (UART).
   - FRAM chunk-logger ownership vs C.7.1.
   - `_ready()` flooding.
10. **Doc/code drift sweep** of C.3 (FRAM buffers, I2C scratch), the C.7.1 FRAM row, and the "consecutive" comment in SCD30.
11. **Dead or untested production surface**: BMP altitude/pressure getters, `SPI.write_readinto`, `verify_present`, `set_write_protected`, `led_signal`, `stop_timer`, UART readline/stream APIs.
12. **SPI peripheral reset per session** (candidate 25): confirm against rp2 `machine_spi.c` at v1.29.0.
13. **Unverified register reads**: SCD30 0x0010 read-back, SGP40 serial word[0]==0.
14. **Latent bus-uninitialised no-ops** (candidate 33) and **UART CRC-less deployment** (candidate 30): is structural validation alone acceptable?

---

## Networking and web server

### Networking and REST survey of `src/`: pre-audit report

I read these files in full: `asy_wifi_service.py` (860 lines), `asy_ntp_client.py` (483), `asy_dns_client.py` (129), `asy_udp_socket.py` (208), `captive_dns.py` (212) and `asy_webserver_service.py` (807). I also read the parts of `ext/microdot.py` v2.6.2 the project relies on (Request create/json, Response write/body_iter/send_file, handle_request/dispatch_request/find_route), SPECIFICATION A.5, A.8, A.9, F.2, H.7, I.3, I.6 and B.14.2, the `[lwip]` table in `toolchain/versions.toml`, and the generated wiring in `buildgen/codegen.py`.

To verify internals the project depends on, I fetched MicroPython v1.29.0 source into scratch: `extmod/asyncio/stream.py`, `py/stream.c` and `ports/rp2/machine_rtc.c`.

Nothing in the repo was modified. No hardware, git or test commands were run. **[V]** means I verified it by reading source. **[I]** means inference.

---

#### 1. Modules

##### 1.1 `asy_wifi_service.py`: `AsyConnTime(SensorReaderConfig)`, logger `WIFI`

**Config schema** (lines 43-53), stored in `config_WIFI.cfg`:

| Field | Type / default | Bounds / notes |
| --- | --- | --- |
| `SSID` | str, "" | 0-32. Empty means "not configured" and goes straight to hotspot. |
| `PW` | str | 8-63, or "" for an open network |
| `Country` | str, "DE" | 2 characters |
| `Hostname` | str, "SensorNode" | 1-32; the buildgen per-device default is substituted by `_with_default` |
| `LedWifiOn` | bool | |
| `HotspotPW` | str, "12345678" | 8-63; per-device build default |

- Radio fields are checked in UTF-8 bytes at write time (`_set_mgr_cfg`, :690) and again at use (`_radio_values`, :704). Both follow C.7.4.
- `PW` and `HotspotPW` are masked as "********" in `get_dict_cfg` (:197, :718).
- **`HotspotPW` is not in any `SettingsGroup`** (`buildgen/codegen.py:607`), so it can be set at build time only, never over REST [V].

**Public API:**
- Tasks: `get_task_starters()` returns `wlan_connect`, `time_counter` and `_watch_hotspot_timeout`.
- Timers: `get_timer_starters()` sets up a 1 s PERIODIC `counter_timer`.
- Getters: `get_wlan_ifconfig`, `get_dns_server_ip`, `get_wlan_rssi` and `wlan_isconnected` all return None/False when `wifi_mode_lock.locked()`.
- `network_available()` requires the caller to hold the lock.
- `is_hotspot_active()` needs no lock.
- Also: `reconnect_wifi()`, `set_wifi_led()`, `set_ext_led()`, `get_wifi_mode_lock()`.

**State machine** (`_conn_phase`, :122-126):
- `STA_SEEKING(0)`
- `STA_ESTABLISHED(1)`
- `HOTSPOT(2)`
- `DEACTIVATED(3)`, which is terminal

**Main loop** (`wlan_connect`, :814):
- Runs every `wifi_refresh_sec` (5 s).
- A pending `reconn_wifi` calls `_handle_reconnect_trigger`: 5 s sleep, then either leave hotspot (mode switch) or a bounded STA disconnect (20 × 0.5 s), then 3 s.
- HOTSPOT phase runs `_run_hotspot_mode`. Anything else runs `_run_sta_mode`.

**STA attempt** (`_run_sta_mode`, :583, holds `wifi_mode_lock` throughout):
- If not connected: `_attempt_sta_connect`, which calls `network.country`/`hostname`, `active(True)`, `pm=0xA11140`, then `connect`. After that, `_poll_sta_connect_status` polls 10 × 0.5 s.
- Result, when connected: phase becomes ESTABLISHED and the failure count resets.
- Result, when not connected and ESTABLISHED: sleep 60 s (:473).
- Result, when not connected and SEEKING: `connection_failures++`. At `conn_fail_to_hotspot` (5) failures it enters HOTSPOT, or `_deactivate_wlan_permanently()` if `hotspot_started_once` is already set (:485).

**Hotspot:**
- `_start_hotspot` switches mode to `AP_IF` (disconnect, `active(False)`, 2 s, `deinit()`, 1 s, new `WLAN`, 1 s).
- It then configures `essid=hostname`, `password=HotspotPW` and `pm`, and starts an unsupervised `DNSServer.run()` task.
- Every tick checks stations:
  - At least one station: stop the timer and keep the LED on.
  - No stations: arm a PERIODIC `hotspot_timer` (`hotspot_time_min`, 5 min) and a flashing-LED task.
- When the timer fires, it sets a `ThreadSafeFlag`, and `_watch_hotspot_timeout` calls `reconnect_wifi()`.

**Timing summary:**
- 5 s refresh
- 5 s connect poll
- 60 s retry after an established link drops
- about 5 failed cycles (roughly 50 s) before hotspot
- 5 min hotspot with no client
- then one more STA streak before permanent deactivation

A.4 records this as intentional: only a power cycle clears it.

Errno 11-18 and 20; wrnno 1-8. The per-episode repeat rule applies (`_episode_wrn`, :623).

##### 1.2 `asy_ntp_client.py`: `AsyNtpClient(SensorReaderConfig)`, logger `NTP`

**Schema:**
- `NTP_Host`: str, 3-1024 characters. The owner settled this bound.
- `NTP_Offset_S`: ±43200
- `NTP_Interv_H`: 1-24 h
- `GMTOffset` / `DSTOffset`: ±43200

**Tasks:**
- `asy_ntp_time`: waits on `ntp_sync_trigger_event`. Reads the DHCP DNS server before taking the lock, takes `wifi_mode_lock` for the whole attempt, then runs `_run_ntp_sync_attempt`: `network_available` → config → `resolve_ipv4` → UDP fetch → parse.
- `ntp_time_hours_counter`: 10 s PERIODIC tick. While synced it triggers at the interval. While unsynced it uses exponential backoff, `retry_s` 10 → ×2 → capped at `retry_max_s` 600.
- `time_counter`: 1 s tick that ages `LastSyncAge`.

**Retries:**
- When already synced, a failure arms a ONE_SHOT 15 s retry timer, up to 3 times.
- `ntp_force_sync()` is the `post_asy_fct` of the `/networking` NTP group.

**Reply validation** (`_parse_ntp_reply`, :243):
- Rejects LI=3 and stratum 0.
- Plausibility window 2025-01-01 to 2100-01-01, with NTP-era reinterpretation.
- Uses the transmit timestamp only.
- Sets the RTC via `RTC().datetime`. The weekday argument is ignored by rp2 1.29 `machine_rtc.c` [V].

**`cettime()`** hard-codes the EU last-Sunday-of-March/October rule at 01:00 UTC. Only the offsets are configurable.

**Deployed timing** (`codegen.py:19-21`): DNS 500 ms × 1 try per server; NTP fetch 5000 ms.

Errno 11-21 (20 retired); wrnno 1-3.

##### 1.3 `asy_dns_client.py`: `resolve_ipv4()`

- Never raises. IPv4 A records only.
- Returns an IPv4 literal as-is.
- Otherwise builds a query with a 2-byte `os.urandom` transaction ID and RD=1. Labels over 63 raise ValueError, which is caught.
- Tries the DHCP DNS server, then 8.8.8.8, then 1.1.1.1 (`_FALLBACK_DNS_SERVERS`, :20). "0.0.0.0" and non-literals are skipped.
- One `AsyUDPSocket` per server, 512 B receive buffer.
- The parser checks transaction ID, QR and RCODE, and walks answers that start with a compression pointer only.

##### 1.4 `asy_udp_socket.py`: `AsyUDPSocket`

- Lazy `_connect()` under `_connect_lock`. Client mode does `connect`; server mode does `bind`. `SO_REUSEADDR`, non-blocking.
- `ready()` (:126) busy-polls `ipoll(0)` with `sleep_ms(20)` between polls. `timeout_ms <= 0` waits forever.
- `sendto`, `write`, `recvfrom` and `write_and_recvfrom` (:182) never raise; they return None-shaped sentinels.
- `disconnect()` returns a bool.

##### 1.5 `captive_dns.py`: `DNSServer` / `DNSQuery`, logger `DNSSRV`

- Binds 0.0.0.0:53 and runs `recvfrom(4096)` (:98).
- Drops senders outside the AP subnet.
- Parses the first question: opcode 0, labels decoded as UTF-8. It must end with QTYPE/QCLASS.
- Replies to every query type with one A record pointing at the AP IP, TTL 60 s, echoing the question.
- On a failed receive it backs off 0.5 → 5 s. An exception sleeps 3 s.
- It is **not supervised**: it is started, and cancelled, only by `AsyConnTime`.

##### 1.6 `asy_webserver_service.py`: `WebserverService`, logger `WEBSERVER`

Covered in section 2.

##### 1.7 lwIP settings (`toolchain/versions.toml:41-52`)

| Option | Value |
| --- | --- |
| `MEMP_NUM_TCP_PCB` | 9 (= max_connections 6 + 3 spare) |
| `MEMP_NUM_TCP_SEG` | 48 |
| `MEM_SIZE` | 12000 |
| `TCP_MSS` / `TCP_WND` / `TCP_SND_BUF` | 800 / 6400 / 6400 |
| `MEMP_NUM_UDP_PCB` | 5 (unchanged from the default 4+mDNS) |
| `PBUF_POOL_SIZE` | 16 (untouched) |

They are injected through a generated board directory and header, and checked by `check_lwip_ensemble()`, `validate.py` and `verify_lwip_macros_in_build()`.

---

#### 2. REST layer

##### 2.1 Routes (registered in `__init__`, :372-400)

**GET routes.** All are streamed through `_PieceWriter` as `Response(iter(pieces))` with an exact Content-Length:

| Route | Contents |
| --- | --- |
| `/measurements` | each sensor's `get_dict_data()`, merged with `.update()` |
| `/sensors` | each sensor's `get_dict_cfg()` |
| `/networking` | flat fields from the networking `SettingsGroup`s |
| `/system` | flat fields plus the verbatim `build` entry |
| `/notification` | flat fields |
| `/status` | networking, system, notification, sensors-maintenance, errcount (one entry per error source plus `WEBSERVER`) |

In `/status`, each section is flushed as its own piece, and each source is guarded to `{"error":"unavailable"}` plus `err_s(6)`.

**PUT routes:**
- **`/sensors`** (:420): for each `{name: {fields}}` it calls `module._set_dict_cfg()` **directly**, not `ar.handle_set_cmd`. Unknown names and non-dict values are silently skipped.
- **`/networking`, `/system`, `/notification`** go through `_apply_settings_groups` (:445). Only groups that intersect the body run, via `ar.handle_set_cmd`. Its post hooks fire if at least one field is "Valid":
  - SSID/PW/Country/Hostname → `reconnect_wifi`
  - NTP fields → `ntp_force_sync`
- **`/system`** also accepts `SystemCmd` ∈ {reboot, bootloader, mempause} (:95, :503).
- **`/notification`** also accepts `lightCmdLED` (any dict is passed to the callback, :533) and `PauseTime` (int 0-3600 via `type_or_range_error`, :545).
- **`/status`** accepts only `{"ResetErrors": true}`, which resets every error source plus its own (:631).

**Static routes** (when `static_mount` is set, registered last): `GET /` and `GET /<path:filename>`.
- A filename containing `..` gets 404.
- Otherwise it opens `mount/filename + ".gz"`, sets Content-Length from `seek`, and calls `send_file(..., compressed=True, stream=)` with `send_file_buffer_size = chunk_bytes` (256).
- A missing file gets 302 to "/" when `is_hotspot_active()` is true, otherwise 404.
- `req.path` is **not** URL-decoded before routing [V, `find_route` matches the raw path], so `%2e%2e` is harmless.

##### 2.2 Limits and hardening

- **Request size:** `Request.max_content_length = Request.max_body_length = 2048`. These are class-level, set in the constructor (:363-370). `max_readline` stays at Microdot's 2 KB default.
- **`_TimeoutStreamProxy`** (:234) wraps every `readline`, `readexactly`, `awrite`, `aclose` and `wait_closed` in a `wait_for` of `per_call_timeout_s` (5 s).
  - A read timeout is logged as `wrn_s(2)` and re-raised; Microdot swallows it and answers 400.
  - A read OSError sets `peer_gone`, and after that every write is dropped.
  - Header writes are buffered until the blank line and sent as one write.
- **`_serve`** (:692):
  - `_open_conns` is incremented first. Anything over `max_connections` (6) is decremented and closed with no response.
  - Otherwise `handle_request` runs inside `wait_for(outer_cap_s = 15 s)`.
  - Handled exceptions: CancelledError is re-raised; EOFError, TimeoutError and OSError are logged with `wrn_s`; anything else with `err_s(1)`.
  - The `finally` closes the writer and then always decrements.
- **`backlog`** defaults to `max_connections + 1` and is clamped up to at least `max_connections`.
- **Error handlers:**
  - Shaped JSON handlers for 400, 404, 405, 413 and 500.
  - An `errorhandler(Exception)` that persists `err_s(4)` and returns 500.
  - `after_request` and `after_error_request` both add `Connection: close`.

##### 2.3 Microdot behaviour the project relies on [V]

- **Handler exceptions:** `dispatch_request` catches `HTTPException`, resolved by status code, and `Exception`, resolved by exact class then MRO.
- **Parse failures:** a `Request.create` failure is `print_exception`'d and answered 400 with `req=None`.
- **Write failures:** `Response.write` mutes only OSError errnos 32, 54, 104 and 128.
- **413 timing:** the body is read in `create()` before the 413 check in dispatch, which is why the two caps are bound together.
- **JSON bodies:** `request.json` returns None unless Content-Type is `application/json`.
- **OPTIONS:** answered by the default handler with an `Allow` header and no CORS headers.
- **HEAD:** runs the full GET handler and skips the body.

---

#### 3. Security-relevant aspects

1. **The whole write surface is unauthenticated on the LAN, or in the AP when in hotspot mode.** It includes:
   - `SystemCmd: "bootloader"`: puts the device in BOOTSEL, so it is offline until physical intervention.
   - `reboot` and `mempause`.
   - `ResetErrors`: irreversibly wipes the FRAM error evidence that CLAUDE.md protects.
   - SSID/PW changes.
   - Every config write. Each accepted change that alters a value is a flash write; "Unchanged" values are skipped (`config_manager.py:347`), but alternating values are not.
   - `PUT /sensors` to the SCD30's NVM-backed setter: remote wear on limited-endurance NVM [I, the setter is outside my area].
2. **No Host-header check and no CORS headers.** Cross-origin PUTs are blocked by the preflight, but **DNS rebinding** would give a malicious web page same-origin PUT access [I, standard attack class].
3. **Hotspot credentials.** The AP password is "12345678" in all six `devices/*.toml`, and the AP SSID equals the hostname. Anyone in range of a unit in hotspot mode can read the stored SSID and re-point the unit to their own AP. CLAUDE.md records this as an accepted risk.
4. **One bogus-SSID PUT leads to permanent WLAN deactivation.** The sequence is:
   - the failure streak sends it to hotspot;
   - 5 min with no client;
   - a second streak ends in `DEACTIVATED` (:485-490);
   - `reconn_wifi` is ignored while deactivated (:823).

   A.4 records this as intentional, but it is also a remote denial of service that needs a physical power cycle.
5. **Captive DNS:**
   - It answers every QTYPE (AAAA, HTTPS/65) with an A record while echoing the original QTYPE.
   - It does not check the QR bit, so it answers responses too.
   - The on-subnet filter uses the source address, which can be spoofed within the subnet [V].
6. **NTP:** there is no origin-timestamp or mode check, so an on-path LAN attacker can set the RTC within the plausibility window. The connected UDP socket makes off-path spoofing hard [I].
7. **Request smuggling:** not applicable. HTTP/1.0, one request per connection, no proxy, and `Transfer-Encoding` is ignored.
8. **Header injection:** not possible. Header values are ours, and `redirect()` rejects CR/LF.

---

#### 4. Concurrency, locking and blocking

- **`wifi_mode_lock`** is shared by WiFi and NTP. The getters degrade instead of waiting.
- **NTP holds the lock for its whole attempt** (:433-440). That is up to three DNS servers × 500 ms plus a 5000 ms fetch, so ~6.5 s or more. During that time:
  - WiFi `time_counter` blocks, and its 1 s `ThreadSafeFlag` ticks collapse, so `WifiUptime` undercounts.
  - `/status` shows `IPv4`/`Rssi` as null.
  - The WiFi loop waits.
- **The WiFi state machine holds the lock** through the 5 s connect poll, and **through the 60 s `asyncio.sleep(60)`** in `_on_sta_disconnected` (:473 under :584) [V].
- **`getaddrinfo`:** the project never calls it. `asyncio.start_server` itself calls `socket.getaddrinfo("0.0.0.0", 80)` once, at bind time (stream.py:183) [V]. For a numeric host it is effectively non-blocking [I].
- **UDP waits** are 20 ms `ipoll(0)` busy-polls. That is fine for client timeouts, but the **captive DNS server polls at 50 Hz forever** (`timeout_ms=-1`) while the hotspot is up. This is the same idle-poll cost F.5.9 fixed for UART.
- **Every per-call timeout is its own `asyncio.wait_for`**, which means a task per read or write (F.1 measured the cost).
- **Blocking inside lwIP:** `modlwip`'s `tcp_write` retry loop can block the VM for up to 10 s if `MEM_SIZE` is exhausted (B.14.2). This has never been observed.
- **cyw43 calls:** `wlan.status("rssi")` and `ifconfig()` are synchronous cyw43 ioctls on every `/status` request.

---

#### 5. Audit candidates

**S** = suspicion (likely a real defect or gap). **W** = worth checking.

1. **S – `Content-Length: -1` bypasses the 2048 B body cap** [V by source; not executed].
   - `Request.create` (`ext/microdot.py:417-426`) calls `int(value)` on the header and reads the body when `content_length and content_length <= max_body_length`. That is true for -1.
   - `Stream.readexactly(-1)` (stream.py:42-52) calls `s.read(-1)`, which is `stream_readall` (`py/stream.c:127`). It returns everything buffered, up to about `TCP_WND` = 6400 B, grown with `vstr_extend`, then `r += r2`.
   - `n` becomes -1-k, so the next `read(n)` hits `py/stream.c`'s "negatives … will cause a MemoryError" path.
   - Net effect: a client can force ~6-13 KB of contiguous allocation per connection (×6 connections), a forced GC, and a **client-triggered `MemoryError`**, which Microdot `print_exception`s and answers 400.
   - With -2, the MemoryError is immediate.
   - This contradicts I.6's "oversized body never buffered" and the zero-`MemoryError` bar, and the twin's MemoryError grep gate would trip on it. The fix has to live outside `ext/`, for example a proxy-level `readexactly` guard for n < 0.
2. **S – Header lines and header count are unbounded before any check** [V].
   - asyncio `readline()` (stream.py:55-64) grows `l += l2` with O(n²) contiguous copies until it sees `\n`. Microdot's `max_readline` check (:533-537) runs only afterwards.
   - The header loop (:412-421) has no count limit.
   - The only bounds are the 5 s per-call timeout per line and the 15 s outer cap. On a LAN that is plenty to exhaust a ~190 KB heap, which hurts every other task.
   - This is the same "check after allocate" shape as I.6's body-cap gap, and it has no test (`grep max_readline tests/` finds nothing).
3. **S – Captive DNS `recvfrom(4096)`** (`captive_dns.py:98`) allocates about 4 KB per datagram [I, modlwip `vstr_init_len`]. Phones query DNS constantly in hotspot mode, so this is 16× the 256 B design bound (I.3). I.2 says "UDP receive buffers … small, fixed", which is spec drift. The NTP fetch also allocates 1024 B for a 48 B reply (`asy_ntp_client.py:185`). `asy_dns_client` already uses 512 (RFC 1035).
4. **S – `wifi_mode_lock` is held across `asyncio.sleep(60)`** (`asy_wifi_service.py:473` inside `_run_sta_mode` :583-590).
   - For 60 s: uptime/snapshot updates stall, a PUT-triggered `reconnect_wifi` is delayed, and the NTP task blocks on the lock.
   - Check whether the sleep should happen outside the lock.
5. **S (known, pinned) – NTP "stale sync" can never trigger.** `ntp_sec_count` resets at 1× the interval (:471), so the 3× check (:456-459) is unreachable. `Synced` stays True forever after the first success even if the server is gone. It is pinned as legacy-inherited by `tests/test_asy_ntp_client.py:1389-1410`. Worth confirming with the owner that this is still wanted.
6. **W – `_poll_sta_connect_status` does not break on `STAT_GOT_IP`** (:616-621). Every successful connect costs the full 5 s under the lock.
7. **W – 5 s connect poll, then a fresh `wlan.connect()` 5 s later.** A slow WPA handshake or DHCP can be interrupted, and five of those cycles (~50 s) mean hotspot. After a power outage where the router takes more than ~6 min (50 s + 5 min hotspot + second streak), the unit deactivates permanently. Check this against the owner's intent in A.4.
8. **W – `_run_hotspot_mode` repeats the full mode switch** (deinit and a new `WLAN`) on any tick where AP `status != STAT_GOT_IP` (:570). That makes the `active()` guard in `_configure_hotspot_ap` moot. The running DNS task is kept, and its socket survives a cyw43 deinit [I]. It also sets `hotspot_started_once` again.
9. **W – A task restart during HOTSPOT keeps the phase but immediately leaves hotspot** (`_reset_wlan_connect_state` :311 forces `reconn_wifi`) and resets `hotspot_started_once`. The comment at :305 and A.4 say "left as-is"; the effective behaviour differs.
10. **W – `_put_sensors` bypasses `ar.handle_set_cmd`** (:431), unlike the flat routes. It has no post hooks and no `Exception` guard (a raise becomes 500 with `err_s(4)`). This is a D.10 API inconsistency.
11. **W – `_put_status` is unguarded.** An exception from any `reset_error_counter()` (:636-637) leaves a partial reset and a 500. There is no confirmation for an irreversible evidence wipe.
12. **W – WEBSERVER `wrn_s` calls never pass `repeat=`** (:254, :715-724). Every idle, reclaimed connection spends a FRAM ring slot. Browsers' speculative preconnects routinely idle, so normal browsing churns the 10-slot history. The same applies to DNSSRV `wrn_s(1/2)`. Compare the repeat rule used in WIFI/NTP.
13. **W – `_fetch_ntp_reply` does not call `cli.disconnect()` in a `finally`** (:183-188), unlike `resolve_ipv4` (:117-120). Cancelling the task mid-fetch leaks a UDP PCB (pool of 5) until GC [I: whether modlwip sockets have a finaliser].
14. **W – UDP PCB budget.** `MEMP_NUM_UDP_PCB = 5` against lwIP DNS, mDNS, DHCP client or server, captive DNS and the NTP/DNS client, especially during STA↔AP transitions. Never measured [I].
15. **W – `_PieceWriter` counts characters, not bytes** (:145-148). Non-ASCII SSID or hostname values make pieces larger than `chunk_bytes`. Content-Length stays correct.
16. **W – HEAD requests and timed-out or aborted static responses never `aclose()` the opened stream** (Microdot skips `iter.aclose` for HEAD and on non-muted errors). This relies on GC. Low impact for VfsFrozen [I].
17. **W – Static files carry no `Cache-Control`** (`default_send_file_max_age` is None), so every page load re-downloads the site. That is load on a CPU-bound server with a ceiling of 6.
18. **W – `captive_dns` builds f-strings for `pr.evt` on every query** (:109-121), regardless of log level: per-request allocation churn (I.4).
19. **W – DNS query building:**
    - A trailing-dot or empty label produces a malformed query (:44-62).
    - There is no 255-octet total-QNAME check; `NTP_Host` allows 1024 characters.
    - The response is not checked for the TC bit, and only answer names that start with a compression pointer are parsed.
20. **W – `PW` accepts 8-63 characters.** That excludes a raw 64-hex-digit PSK, and the GET→PUT round trip of the masked "********" would store the mask as the password. Check the JS client and document it.
21. **W – `get_dns_server_ip()` returns None whenever the lock is held at the moment NTP samples it** (:431). NTP then silently uses only 8.8.8.8/1.1.1.1, which fails on networks that block external DNS.
22. **W – `get_wlan_rssi()` prints an error on every `/status` in hotspot mode** (:760, ValueError "STA required"). It is console-only. `WifiUptime`/`Connected` also count up in AP mode, because `STAT_GOT_IP` is not STA-only.
23. **Spec and comment drift:**
    - I.6 still says "`max_connections` is 4" and "4 × 2,048 = 8,192 B"; with 6 connections the worst case is 12,288 B.
    - I.2 describes UDP buffers as small; see item 3.
    - `asy_udp_socket.py:176` mentions `_open()`, which does not exist (the method is `_connect()`).
    - `asy_webserver_service.py:725` says "see module docstring", which says nothing about that.
    - `asy_wifi_service.py:168-169` mentions a future "combined Networking endpoint".
    - F.2 says timeout mechanisms "should standardize on one mechanism"; UDP uses a ticks loop while HTTP uses `wait_for`.
24. **Comment cap:** gated at zero for Python by `tests_scripts/test_comment_block_cap.py`. I did not re-run it. I saw no obvious over-cap blocks, though several trailing comments continue onto a standalone comment line (for example `asy_wifi_service.py:110-111`, :140-142), which reviewers may want to eyeball against the counting rule.

---

#### 6. Suggested audit checklist for this area

- [ ] Does any client-supplied value reach an allocation before its bound is checked? Cover negative, huge and non-numeric Content-Length, header line length and count, query string, cookies and JSON nesting. Add tier tests (mock and twin) for Content-Length -1/-2 and header floods, with the MemoryError gates active.
- [ ] Enumerate every lock-hold span of `wifi_mode_lock` that contains an `await asyncio.sleep` or a network timeout. What stalls, and for how long?
- [ ] WiFi state machine: model every transition, including task restart in each phase, a PUT during a mode switch, a PUT while `DEACTIVATED`, a client joining just as the hotspot timer fires, a router outage at boot longer than 6 min, and a mid-handshake interruption by the 5 s poll.
- [ ] NTP: stale-sync reachability, ONE_SHOT retry timer against the C.9 soft-callback-drop rule, lock-hold duration, socket cleanup on cancel, validation of reply mode, version and origin, and the EU-only DST rule against configurable offsets.
- [ ] UDP resource accounting: PCB pool of 5 in every phase and transition, receive-buffer sizes, idle 50 Hz polling of the server socket, `disconnect` on every exit path.
- [ ] Captive DNS: QTYPE handling (AAAA/HTTPS), QR check, TTL after leaving the hotspot, per-query allocation, and the "unsupervised task" lifetime across mode switches.
- [ ] REST: parity between `_put_sensors` and the flat routes (guarding, post hooks, result shape); guarding and confirmation for `ResetErrors`; use of the repeat flag in WEBSERVER/DNSSRV logging; HEAD and error-path stream closing; caching headers.
- [ ] Threat model to put to the owner: unauthenticated `bootloader`/`ResetErrors`/SSID writes, DNS rebinding (no Host check), remote flash and SCD30-NVM wear through alternating PUTs, and the shared default hotspot password.
- [ ] Spec reconciliation: I.6's stale 4-connection figures, I.2's UDP-buffer claim, F.2's standardise-timeouts item, and the stale comments listed in item 23.
- [ ] Re-verify on a Microdot bump: whether `readexactly`/`max_readline` ordering or Content-Length parsing changed (A.5 already notes v2.7.0 as checked). If not, confirm that the fixes stay outside `ext/`.

Scratch copies of the fetched upstream sources (`stream.py`, `pystream.c`) are in `/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/`.

---

## Build chain, toolchain and CI

#### Build chain, tooling and CI audit survey for /home/user/sensors

This was a read-only survey. I changed nothing in the repo (git status is clean). Some probes ran buildgen against scratch TOMLs in my scratchpad. Those runs created `__pycache__` in `buildgen/` and `toolchain/`, and I deleted both. A `tests_scripts/__pycache__` also appeared around 07:09 UTC; it looks like another process made it, so I left it alone. **[V]** means I checked it by reading the code or running a probe. **[I]** means it is inferred and not confirmed.

---

##### 1. The buildgen pipeline, end to end

**Entry point.** `buildgen/generate.py:63` `generate_device(toml, src_dir, ext_dir, build_date)` runs these steps in order:
1. `validate.build_model()`
2. `graph.build_construction_order()`
3. `codegen.generate_module_source()` and `generate_boot_entry_source()`
4. `frozen_modules.compute_frozen_modules()`

It returns strings only. Callers decide where they are written:
- `scripts/_generate_sensortask_modules.py` writes all six devices into `build/generated_src/`, plus a `*_wiring_plan.json` from `twin_wiring.compute_twin_wiring()`.
- `scripts/build_firmware.py` writes a temporary stage directory.
- `generate.py`'s own CLI can print or write `sensortask_<dev>.py` and `<dev>_boot.py`.

**TOML schema** (`model.py`, `buildspec.py`, `validate.py`):
- `[device]`:
  - Required: `name`, `hostname`, `hotspot_password`, `conn_fail_to_hotspot`, `hotspot_time_min`.
  - Optional ints: `max_connections`, `backlog`, `ntp_retry_s`, `ntp_retry_max_s`.
  - `hostname` must equal `SensorStation<name>` and be at most 32 characters. The password must be 8–63 characters.
- `[device.wiring]`: `led_target` and `fram_target`. Their consumers are fixed in `_DEVICE_WIRING_CONSUMERS` (validate.py:78).
- `[bus.<id>]`: ids are limited to i2c0/1, spi0/1 and uart0/1. Required and allowed fields depend on the bus kind.
- `[[instance]]`: `driver` and `name_ext`, plus the per-driver fields in `buildspec.py`. `buildspec.py` is the one hand-maintained per-driver table.
- Instance identity is (`driver`, `name_ext`). The variable name is `driver[_ext]`. `resolved_name` is the driver's `_NAME` plus `_ext`, and serves as the REST key. There are two separate collision checks, one per naming space.

**Validation** (`build_model`, validate.py:730). Each stage raises `BuildError(device, msg, instance=, field=)` naming what failed:
1. device table
2. bus tables
3. driver resolution and tag parsing, cached per source file (validate.py:313)
4. required and allowed fields, bus kind, address capability, int types
5. uart roles
6. `@limits` values
7. every declared bus is used
8. both name-collision checks
9. GPIO existence, exclusivity and role, against `pico_gpio.py`
10. per-bus address collisions
11. instance wiring, `warn_*` wiring and value wiring
12. device wiring
13. `@requires`
14. Last, coherence with the lwIP ensemble. This loads `toolchain/micropython_overrides.py` by file path (validate.py:194) and checks it against `versions.toml [lwip]`. It is followed by the NTP backoff and UART link timeout/rxbuf checks, which read `src/` defaults via the AST (`init_int_default`, `module_int_const`).

**Driver registry** (`driver_registry.py`):
- A driver named `asy_<name>_driver.py` is parsed as an AST, and must contain exactly one `SensorReader` or `SensorReaderConfig` subclass.
- `_OVERRIDES` covers `fram`, `neopixel`, `notification` and `uart_link`. `SINGLETON_SERVICE_DRIVERS` is the override set minus `uart_link`.
- `needs_setup` is derived from the base class, or from whether an `async def setup` exists.

**Tag families.** All six are built on `tag_comments.py`, which scans with `tokenize`, tracks bracket depth to tell module level from inside a block, and uses Levenshtein distance to catch near-misses (distance 1 for names of four letters or fewer, otherwise 2). Each family has a payload-shape gate so that ordinary prose is not flagged.

| Tag | Grammar | Parser |
|---|---|---|
| `@wiring` | 5-token grammar | `wiring.py:220` |
| `@value-wiring` | 4-token grammar | `value_wiring.py:280` |
| `@limits` | a range or `in {set}`, parsed by hand | `limits.py` |
| `@requires` | `bus.<f><op><v>` | `requires_tag.py:284` |
| `@web` / `@web-group` | key=value pairs, `special:<v>=`, quoted or bareword values | `web_tag.py` |

**Codegen output** (`codegen.py`), for `sensortask_<dev>.py`:
- Fixed imports.
- `const()` values for the module-error/DNS/NTP limits and the firmware/website versions and build date.
- `_FIELD_WARN_*` schemas from `_KNOWN_SIGNALS`.
- Module-level globals.
- Callbacks: system commands, LED, notification pause, SGP maintenance, networking and system status, and `_flush_pending_configs`.
- `build_system()`:
  - `WDT(timeout=8000)` and the bus constructors.
  - Nodes in construction order. conn, ntp and sysfunct are fixed infrastructure; the device's FRAM is injected into them.
  - `conn.set_ext_led` and `WebserverService(...)`.
  - The setup batch: fram, then sysfunct, conn, ntp, then instances needing setup. Each is followed by `feed_watchdog()` and `gc.collect()`.
- `_collect_*` fan-in helpers and `main()`.

The boot entry (codegen.py:696) sets `gc.threshold(32768)`, runs `asyncio.run(main())`, and is frozen as `main.py`.

**definitions.json** (`definitions.py`):
- A fixed section skeleton.
- Sensor groups from `@web` tags plus AST-evaluated `ConfigSchema` (`schema_ast.py`), limited to drivers in `_SENSOR_DRIVERS`.
- Networking and system groups come from mandatory-infrastructure files.
- Generator-owned catalogs: system command, reset, flash, pause, warning signals, and the errcount module list.
- `schemaVersion` is 1.0.0; `websiteVersion` comes from `version.py`.

**Frozen module set** (`frozen_modules.py`): `CORE_MODULES` plus each driver module, closed transitively over import statements found by AST, skipping `if TYPE_CHECKING:` blocks.

**Versioning**: `version.py` holds `FIRMWARE_VERSION` and `WEBSITE_VERSION` ("2.0b0") and `current_build_date()`, all bumped by hand.

##### 2. Toolchain installer

**`setup` subcommand** (`run_setup`, setup_toolchain.py:550):
1. apt packages from `versions.toml`, installed with sudo.
2. Full clone of MicroPython at the ref.
3. pico-sdk commit derived from MicroPython's `ls-tree lib/pico-sdk`, then a clone and the mbedtls submodule.
4. picotool: the newest tag matching pico-sdk's major.minor, from `ls-remote`. Built, then `sudo make install` into `/usr/local`.
5. rp2 and unix submodules.
6. The 8-step verification chain (line 491):
   - build mpy-cross
   - cross-compile a test module
   - build the Unix port with that module frozen in, and import it
   - build the rp2 firmware with it frozen in
   - clean up
   - rebuild `build-standard` plain and `build-settrace` with `-DMICROPY_PY_SYS_SETTRACE=1`

**`test` subcommand**: the same chain run offline. **`env --tier`**:
- `generic` adds `uv sync` (retried), `npm ci`, Node installed from nodejs.org if `.nvmrc` doesn't match, and Playwright Chromium.
- `flash` adds dialout group membership and USB vendor-ID detection (2e8a).
- `bench` adds NetworkManager, iproute2 and iptables, plus `ensure_br_netfilter` (modprobe, sysctl, and files in `/etc`) and `ensure_bench_bridge` (br0 pinned to the uplink's hardware MAC, a WPA2 AP on channel 6, randomly generated credentials).

**Isolation**: `build_env()` uses a fixed PATH with a small variable allowlist and `C.UTF-8`; `network_env()` adds proxy and CA variables. Builds fail on any `warning:` or `error:` in their output, and mbedtls is built with `-Wno-array-bounds`.

**Overrides** (`micropython_overrides.py`). Both generate files outside the checkout and check anchors first:
- `unix_kbd_intr` redirects `VARIANT_DIR` to a generated variant that `#undef`s `MICROPY_ASYNC_KBD_INTR` and sets it to 0.
- `lwip_connection_counts` redirects `BOARD_DIR` to a generated board directory whose `lwipopts.h` includes the real one, then redefines all 11 macros, with a sentinel. It checks 21 anchors and validates both the 16 lwIP relationships and 3 per-connection ones. After the build, `verify_lwip_macros_in_build()` preprocesses `opt.h` with the compiler, defines, includes and flags recorded in `flags.make`, and compares values.

##### 3. scripts/

- **test.sh** steps:
  1. Validates arguments and `GC_THRESHOLD`.
  2. Deletes `tests/_tmp` and `devices/zz_test_*.toml`.
  3. Probes the Unix-port variant with `hasattr(sys,"settrace")` and runs `setup` if the binary is missing or wrong.
  4. Picks parallelism from cgroup cores times a speed-probe multiplier.
  5. Generates the device modules.
  6. Starts `pytest tests_scripts` in the background under a 1200 s timeout.
  7. Runs `sudo setcap cap_net_bind_service` on the interpreter and builds the wozi website.
  8. Dispatches files heaviest-first with `wait -n`. Each file gets `timeout` 240 s ×3 attempts, `stdbuf`, `-X heapsize=16M`, and the path `build/generated_src:src:tests:frozen_modules:.frozen`.
  9. Greps each file's final-attempt log for `MemoryError|memory allocation failed`, even on a pass.
  10. Emits GitHub annotations (capped at 10).
  11. Exits 0, 1, or 3 (3 = only coverage rendering failed).
- **lint.sh**: ruff over 8 scopes, shellcheck, actionlint, `zizmor --offline`, plus grep guards against a `method-assign` suppression in `src/` and against `gc.collect()` outside its allowed sites.
- **typecheck.sh**: derives the stub version from `versions.toml`, runs `uv pip install --target typings`, then repairs the stubs by adding `asyncio/futures.pyi` and un-commenting `NotImplemented`. It generates the modules, then runs mypy three times: main (arguments narrow it), twin, and host.
- **build_firmware.py**:
  1. Runs `generate_device`.
  2. Resolves the frozen set to `src/` or `ext/` files and checks reserved-name collisions.
  3. Stages TYPE_CHECKING-stripped copies (`_strip_type_checking.py`, via `ast.unparse`), the generated module, and `main.py`.
  4. Calls `build_website.sh`.
  5. Writes a manifest, wipes the mpy-cross build, rebuilds mpy-cross, and runs `st.build_firmware`.
- **build_website.sh**: uses the hand-written `html/definitions/{wozi,dev}.json`, and generates definitions with buildgen for every other device. It inlines CSS and definitions (escaping `<`), concatenates `js/` with import lines removed by grep, and calls `build_frozen_html.sh` (gzip -9, then freezefs).
- **Twin**: `run_digital_twin_ci.sh <device>` runs setcap, the website build and the generator, then `_digital_twin_ci_suite.py`. That suite has 14+ runs on fixed port 18080 and real port 53, shuts down with SIGINT, runs at two gc thresholds, and runs a MemoryError gate per run log. `run_unix_port_integration.sh` is the manual twin.
- **Hardware**: `run_{flash,bench}_hardware_suite.sh` and `run_bench_soak_tests.sh` go through `_require_clean_hardware_run.sh`, which refuses unexpected skips and zero passes and reports deselected tests. `mpremote_connect.sh` and `run_manual_hardware_tests.sh` are thin wrappers.
- **Other**: `setup_cross_browser_toolchain.sh` (WebKit via apt, Edge via Microsoft's repo, Firefox via micromamba) and `_render_coverage.py`.

##### 4. CI (`.github/workflows/ci.yml`)

- **Triggers and access**: `pull_request` and push to `'**'`. `concurrency` is per branch with cancel-in-progress. `permissions: {}` globally, `contents: read` per job, `persist-credentials: false` everywhere.
- **Web tier**: `web-changes` (dorny, SHA-pinned, `base: github.ref`) gates:
  - `web-lint-and-typecheck`
  - `web-unit-tests` (after lint)
  - `web-put-matrix` (3 shards, `fail-fast: false`)
  - `web-coverage` (non-gating)
  - `web-cross-browser-smoke`

  Each needs `web-unit-tests` except lint. Timeouts are 10, 20, 20, 20 and 25 minutes.
- **Python lint lanes**: `lint-and-typecheck`, `shellcheck`, `actionlint`, `zizmor`. None has `needs`; timeouts are 15/5/5/5 minutes; each runs a retried `uv sync`.
- **Python test lanes**:
  - `unit-tests`: `needs: lint`, `if: !cancelled()`, 45 minutes.
  - `unit-tests-gc-threshold`: the same shape.
  - `unit-tests-coverage`: `needs: unit-tests`, success-gated, exit 3 is advisory, Codecov SHA-pinned with `continue-on-error`.
  - `digital-twin-e2e`: `needs: unit-tests`, success-gated, a 6-device matrix, 20 minutes.
  - `firmware-build-verify`: `needs: unit-tests` with `!cancelled()`, 6-device matrix, 15 minutes. It installs the ARM apt packages through inline Python, then runs the slow pytest.
- **Composite action**: `pip install uv`, a retried `uv sync`, then `actions/cache@v6` on `~/pico-toolchain`, keyed on `hash(versions.toml, setup_toolchain.py)`.
- **Other caches**: Playwright keyed on `package-lock.json`; Firefox under a fixed key `cross-browser-firefox-v1`.
- **Action pinning**: `actions/*` are pinned by tag (the zizmor policy allows this); third-party actions are pinned by SHA.

##### 5. Tool pins and lint ignores

- **pyproject vs uv.lock [V]**: the pins agree — mypy 2.3.1, ruff 0.16.6, types-pyserial 3.5.0.20260712, shellcheck-py 0.11.0.1, actionlint-py 1.7.12.24, zizmor 1.30.1. The lock's `requires-dev` specifiers match the resolved versions. `pytest` (9.1.1 in the lock) and `mpremote` (1.29.0) are unpinned in pyproject, although the comment at line 18 says every tool here is pinned. `actionlint-py` is locked as an sdist only and fetches its binary while building.
- **Ruff**: `select=["ALL"]`, with a documented ignore list at pyproject.toml:62-195:
  - MicroPython-impossible rules: PTH, RUF005, RUF037, FURB122, PYI024, RUF012.
  - Behavior-change rules: ASYNC110, PERF203, SIM115, TRY301.
  - Memory cost: TRY003, EM101, EM102, SIM105.
  - Spec-mandated: BLE001.
  - Docstring presence and the 3-line cap: D1xx, D205, D209.
  - Accepted risk: S104.
  - Datasheet naming: N80x, N811, N814.
  - Layout and copyright: INP001, CPY001.

  Per-file ignores are centralised, with S603/S607 for the subprocess drivers. The comment at pyproject.toml:233 says there are three known credential sites, but S105/S106 are now exempted in more files than that.
- **mypy**: strict in all three passes; `no_implicit_reexport=false` in the main pass only. Ruff's PGH003 blocks bare `# type: ignore`, so the `method-assign` grep cannot be bypassed that way.

---

##### 6. Audit candidates

**A. Verified defects**
1. **[V] The CI toolchain cache key leaves out `toolchain/micropython_overrides.py`.** The key is at `.github/actions/setup-micropython-toolchain/action.yml:38`. The `unix_kbd_intr` override is compiled into the cached `build-standard`, so an override change can survive in a stale cached binary. This is the same class of bug B.10 describes for `setup_toolchain.py`.
2. **[V] Generated code can reference a global that does not exist.** `codegen.py:563-567` emits `_sgp_maintenance_status()` using the bare global `sgp40` whenever any sgp40 instance exists. The `multi_instance.toml` fixture has only `sgp40_a`/`sgp40_b`, and generating it produces `assert sgp40 is not None` with no such global. It is registered as `("SGP40", ...)` in `maintenance_sensors`.
   - [I] At runtime this is a NameError, swallowed by `_write_guarded`, so the smoke test (`test_digital_twin_generated_boot.py:169-176`, which only checks status 200) cannot see it.
   - `definitions.py:430` has the same hardcoded-`sgp40` assumption.
3. **[V] `irq_pull_up` is never validated and is emitted with `str()`** (`codegen.py:194-195`; the int-type loop at `validate.py:386` excludes it). `irq_pull_up = "no way"` produced syntactically invalid generated source that `generate_device` returned without complaint. A crafted string value would inject code into the firmware.
4. **[V] A device TOML with no `[bus]` table crashes with a raw `KeyError: 'bus'`** at `codegen.py:489` (also line 382). `validate.py:280-282` explicitly declares that shape legal.
5. **[V] A non-table `wiring` gives a raw `AttributeError`.** Both `[device] wiring = "x"` (validate.py:693-694, also graph.py:146 and codegen.py:111) and an instance-level `wiring = "x"` (model.py:213, validate.py:645) do this, against L.5's fail-loud contract.
6. **[V] Stray `warn_*` keys on any instance are silently accepted.** `validate.py:646` and `669-672` accept `warn_*` on every driver, and graph.py:170 adds dependency edges for them. Only the notification instance's keys ever reach codegen, so a copy-paste `warn_co2` on neopixel builds cleanly.
7. **[V] `{source, field}` references never check `field`** (`validate.py:579-591`). L.6.3 states the build checks that the source's `get_data()` exposes the attribute; a typo'd field such as `"Nope"` passes.
8. **[V] The generated module is frozen with its TYPE_CHECKING block unstripped.** The comment at `build_firmware.py:95-99` says there is nothing to strip, but codegen.py:336-343 emits a TYPE_CHECKING block, and stripping changes the wozi module from 12,363 to 11,516 characters.
9. **[V] The Wi-Fi AP password leaks into logs.** `setup_toolchain.run()` echoes the full argv (line 111), including `wifi-sec.psk <password>` (lines 916-921), and line 924 prints it again. It also appears on the process command line.
10. **[V] Truncated user-facing message** at `_require_clean_hardware_run.sh:106`: "...(and/or the other --allow-* flags) to." The `--soak-tier=x` form is not detected (lines 20-23).
11. **[V] Node download can crash and does not check signatures.** `ensure_node` (setup_toolchain.py:998-1003) uses `next(...)` with no default, so it raises a raw `StopIteration` if SHASUMS changes between its two fetches of `latest-v22.x`. The checksum comes from the same origin, with no GPG check, and the version floats.
12. **[V] `definitions.py` CLI ordering differs from the codegen path.** The CLI (lines 522-524, which is what `build_website.sh` uses) never builds `construction_order`, so sensor ordering falls back to declaration order. [I] It can therefore differ from codegen's `sensors=` order.

**B. Suspicions (latent or design fragility)**
- `_strip_type_checking.py:59-63` removes the `try: from typing import TYPE_CHECKING` guard unconditionally but keeps `if TYPE_CHECKING: ... else:` and compound tests. Any remaining runtime use of the name would then be a NameError on the device. This is not present in `src/` today [V].
- `frozen_modules.py:41` skips the whole `If`, including its `orelse`, so imports in an `else:` branch are lost. Line 57 calls `ast.parse` with no `SyntaxError` → `BuildError` conversion.
- `compute_frozen_modules` never scans the generated module's own imports; `CORE_MODULES` is a hand-kept mirror of codegen's import lines. Nothing is missing today [V], and no test enforces it.
- Codegen hardcodes `fram=` for device-level consumers (codegen.py:112) and `conn.set_ext_led` (line 429) instead of using each tag's `target`. An instance-level `setter`-mode tag would pass validation and then be silently dropped.
- `tag_comments.py:200`: a column-0 comment inside a function body is treated as module level [V: a `@wiring` tag was accepted there]. `requires_tag._coerce` accepts `nan`/`inf` [V].
- `defaults.default_init_params` (defaults.py:346) ignores keyword-only arguments. `schema_ast._eval_literal` can hit unbounded recursion on a self-referencing constant (only ValueError/TypeError are caught).
- `twin_wiring.py:219` raises `ValueError`, not `BuildError`. `definitions._coerce_special_value` (lines 139-144) can raise a raw `ValueError`.
- `build_firmware.py` does not `.resolve()` `--toolchain-dir` (lines 116-161), unlike `setup_toolchain`. A relative path would feed relative `BOARD_DIR` and `#include` paths into a make that runs in `rp2_dir` [I].
- Generated `include`/`#include` paths are unquoted for make/CMake (micropython_overrides.py:78-83, 332-336), so a toolchain directory containing spaces would break [I].
- Shared mutable outputs have no locking: `frozen_modules/frozen_html.py`, `build/generated_src/`, `digital_twin/{fram,scd30}_state.json` and `config/`, `ports/rp2/build-*`, and `mpy-cross/build`. `test.sh`, `npm pretest`, `run_digital_twin_ci.sh <dev>` and `build_firmware.py` all write them, so parallel local runs clobber each other.
- The Unix-port variant probe exists only in `test.sh`. `run_digital_twin_ci.sh`, `run_unix_port_integration.sh` and `cross_browser_smoke.mjs` check only `-x`.
- `ensure_apt_packages` uses `sudo env DEBIAN_FRONTEND=...`, and sudo's `env_reset` drops the proxy variables [I]. `ensure_dialout_group` is skipped by `--skip-apt` (setup_toolchain.py:689).
- The `bench` tier modifies a live bridge (`connection up`, lines 855-859 and 922-923) with no dead-man's-switch of its own, which CLAUDE.md requires. `ensure_br_netfilter` passes no `env=` and leaks its temp file if sudo fails.
- `setcap cap_net_bind_service` is placed on a general-purpose interpreter binary (test.sh:284-288 and two other scripts), which lets any local user bind privileged ports.

**C. Supply chain and reproducibility (worth checking)**
- `pip install uv` is unpinned in every lane (`ci.yml:323`, `action.yml:18`), and `uv sync` has no `--locked`/`--frozen`, so a drifted lock re-resolves silently instead of failing. By contrast `npm ci` is lockfile-strict.
- The typings stubs `==1.29.0.*` float across post-releases and are not in the lock (`typecheck.sh:67`). `_render_coverage.py:4` declares `coverage` unpinned.
- Tags are fetched with `git fetch --tags --force` (setup_toolchain.py:193), and the MicroPython ref is a tag rather than a SHA. picotool is "newest matching tag at run time" (lines 246-255), so builds are not reproducible.
- `setup_cross_browser_toolchain.sh:159` downloads micromamba `latest` and runs it with no checksum; Firefox/geckodriver are unpinned (line 162); `arch=amd64` is hardcoded (line 139); and the CI cache key is fixed (ci.yml:301-305), so it never refreshes.
- `build_frozen_html.sh:110` runs `gzip -9` without `-n`, so the output embeds mtimes and is non-deterministic.
- `package.json` uses `@types/node ^26` while `.nvmrc` pins 22.

**D. CI logic (worth checking)**
- The `web-changes` filter (ci.yml:42-57) omits `src/**`, `buildgen/**`, `devices/**`, `digital_twin/**` and `toolchain/**`. The web tier's live-backend twin and generated definitions depend on all of them.
- `lint-and-typecheck` narrows the main mypy pass to `src tests tests_hardware/device_scripts` (ci.yml:339). That drops `digital_twin` from the main pass, which B.15 lists. The comment at `typecheck.sh:105-107` says CI passes `src tests`.
- [I] `actions/cache` saves only when the job succeeds. If `unit-tests` fails on a cold cache, `firmware-build-verify` (`!cancelled()`) fails with "no toolchain found", which is misleading. Parallel cold-cache jobs also build twice.
- The six-device matrices are hardcoded (ci.yml:577, 610), while the pytest `DEVICE_NAMES` is globbed. That contradicts L.1 criterion 2 ("one new file").
- The composite action's description lists six callers; there are nine.

**E. Doc/code drift [V]**
- B.10.1 (SPEC:907) says "180 s × 3"; the default is 240 (test.sh:314).
- B.11 (SPEC:973) says "parametrized over wozi/dev"; it is actually `DEVICE_NAMES`.
- L.6.4 says bmp3xx is the only `_LIMITS` driver; `asy_isl29125_driver.py:194` has one too.
- K.4 says definitions are "never hand-maintained"; `build_website.sh:26-38` ships the hand-written wozi/dev JSON. The golden test (`test_buildgen_definitions.py:40-69`) is order-insensitive, so order drift passes.
- L.1 criterion 1 says "exactly one association"; K.3 lists 3–4 files. There are really more: `_SENSOR_DRIVERS` (whose omission is a silent website omission), `_ERRCOUNT_CATALOG`/`_CFGMGR_LABEL`, `twin_wiring.FIXED_ADDRESSES`, and the CI suite's `_DRIVER_ERRCOUNT_NAME`/`_BUS_FAULT_OPS`.
- L.2 says the website display identity is `SensorStation<Name>`; `definitions.py:508` uses the TOML file stem.
- H.8 says the web filter covers `scripts/*.mjs`; the filter is `scripts/**`.
- Hand-mirrored constants:
  - `validate._NTP_CHECK_TICK_S = 10` mirrors `asy_ntp_client._NTP_CHECK_INTERV`, although the AST helper that could read it already exists.
  - `_SERVER_OUTER_CAP_S` in the twin CI suite is "keep in sync" by hand.
  - `_WARN_SIGNAL_WEB_CATALOG` duplicates the min/max values in `codegen._KNOWN_SIGNALS`.
- Stale comments:
  - `tag_comments.py:121-129,142-143` still say `@web` is "planned".
  - `requires_tag.py:2,323` refer to `_VAL_*`.
  - `web_tag.py:21` says "see module docstring", which doesn't cover it.
  - `test.sh:296` says pytest starts "right after the toolchain check".
  - `.gitignore:75` references the retired `run_wozi_integration.py`.

**F. Comment-cap candidates [V]**
- Outside the scopes CLAUDE.md lists as measured: `.gitignore` blocks of 4, 9, 5 and 5 lines (from lines 27, 33, 75, 84); `tsconfig.json` blocks of 5 and 7 (lines 11, 29); `tsconfig.node.json` 5 and 5 (lines 2, 17).
- Loophole: one-line docstrings that are whole paragraphs (`twin_wiring.py:1-2` and 195-196, `_digital_twin_ci_suite.py:5-7`, `_render_coverage.py:6-7`).

---

##### 7. Suggested audit questions

1. Should buildgen `ast.parse` its own generated module (and `ruff`/`compile()` it) before returning? That would catch A3-type injection and syntax faults.
2. Should every TOML value that reaches codegen through `str()`/`repr()` be type-checked (`irq_pull_up`, `role`, default-provider kwargs)?
3. Should an L.5 raw-exception sweep fuzz `build_model()` with every mis-typed table shape and assert `BuildError` only?
4. Should the generator refuse to reference a driver-named bare global (`sgp40`, `neopixel`, `fram`) when that driver can take a `name_ext`?
5. Should the cache key include `micropython_overrides.py`, and anything else feeding compiled binaries? Should cache restore verify the variant?
6. Should CI use `uv sync --locked` and pin uv and the actions? What is the policy for sdist-only tools that download binaries?
7. Does the web path filter cover every input to `build:site` and the live twin?
8. Should CI's main mypy pass include `digital_twin`?
9. Should hardware/bench scripts refuse to run without an explicit opt-in token, to enforce the go-ahead rule mechanically?
10. Should the installer arm its own recovery timer around bridge creation?
11. Should secrets be redacted in `run()` echo, and should the password be passed via stdin or a file rather than argv?
12. Should shared outputs (`frozen_modules/`, `build/generated_src`, twin state) be locked or per-invocation, to allow concurrent local runs?
13. Should definitions for wozi/dev be generated like every other device, with the golden test order-sensitive?
14. Should `CORE_MODULES` be derived from codegen's import list, with a test that the generated module's imports ⊆ the frozen set?
15. Should `pico_gpio.py` be confirmed as diagram-based, and therefore stricter than RP2040 silicon (for example GP22/GP28 do have I2C/SPI functions on the die), and is the conservatism intended?
16. Should builds be reproducible (`gzip -n`, pinned picotool and Node, tag → SHA verification)?
17. Should the duplicated catalogs between buildgen, the twin CI suite and the hardware harness be consolidated or cross-tested?

Key files: `/home/user/sensors/buildgen/{codegen,validate,model,graph,frozen_modules,definitions,tag_comments,requires_tag}.py`, `/home/user/sensors/toolchain/{setup_toolchain,micropython_overrides}.py`, `/home/user/sensors/scripts/{test.sh,typecheck.sh,build_firmware.py,build_website.sh,_strip_type_checking.py,_require_clean_hardware_run.sh,setup_cross_browser_toolchain.sh}`, `/home/user/sensors/.github/workflows/ci.yml`, `/home/user/sensors/.github/actions/setup-micropython-toolchain/action.yml`, `/home/user/sensors/pyproject.toml`, `/home/user/sensors/tests_scripts/buildgen_fixtures/multi_instance.toml`.

---

## Software test tiers and digital twin

I surveyed the software test tiers read-only and changed nothing in the repo. I read these in full: the runner and fake infrastructure (`tests/microtest.py`, `_threshold_runner.py`, `_coverage_runner.py`, `_tmp_scratch.py`, `machine.py`, `network.py`, `neopixel.py`, `_fram_chip_fake.py`, `_uart_comm_harness.py`, `_uart_link_contract.py`), `_shared_rest_roundtrip.py`, the scenario-library registration code, the twin's `_fault_injection.py`, `_sgp40_chip.py`, `_scd30_chip.py`, `_fram_chip.py` and `network.py`, and four tests_scripts meta-tests. I sampled test bodies in about 15 files. Coverage was mapped with grep/AST scripts.

Two things I ran: the comment-cap detector's own functions, under host python3 with a stub `pytest` in my scratchpad (it found 0 over-cap blocks). And the Python-side audit scripts described below. Nothing else was run. I tag findings as **[verified]** (read in code) or **[inferred]** (reasoned, not executed).

---

#### 1. Test infrastructure

**Runner (`tests/microtest.py`, 42 lines) [verified]**
- It iterates the namespace dict that `microtest.run(globals())` hands it. It calls every callable whose name starts with `test_` and catches `Exception` only.
- Its `finally:` calls `_tmp_scratch.teardown_all()`, then it always calls `sys.exit(0 or 1)`. That exit is the fix for hang #2.
- There is no skip concept and no "at least one test ran" check. A file that registers nothing prints `0/0 passed` and exits 0, which `scripts/test.sh` records as PASS (test.sh:373-376 only looks at the exit code).
- Test order is the MicroPython dict order, not source order. CLAUDE.md itself calls this non-deterministic.

**Per-file wrapping, all in `scripts/test.sh` [verified]**
- One Unix-port process per file, with `-X heapsize=16M`, `stdbuf -oL -eL`, and `timeout 240s` plus 2 retries on exit 124.
- The log is grepped for `MemoryError|memory allocation failed`, even when the file passed.
- `MICROPYPATH=build/generated_src:src:tests:frozen_modules:.frozen`.
- The 15 heaviest files are dispatched first; the rest run in parallel (`TEST_PARALLELISM`).
- The pytest tier (`tests_scripts/`) is started in the background first, and one `wait` reaps both tiers.

**Stage runners [verified]**
- `_threshold_runner.py` (the (f) stage) calls `gc.threshold(argv[2])`, then `exec`s the file with `__name__="__main__"` and passes on `SystemExit.args[0]`.
- `_coverage_runner.py` does the same under `sys.settrace` on the separate `build-settrace` binary. It traces the `src/` and `digital_twin/` prefixes only, so generated `build/generated_src/sensortask_*.py` gets no coverage at all.
- Both runners have their own pytest guards: `test_threshold_runner.py` and `test_coverage_runner.py`.

**Mock boundary: `tests/machine.py`, 707 lines [verified]**
- **I2C:** a dict-of-registers keyed by exact `(addr, memaddr)`; a FIFO `read_queue` plus a per-address queue for word-protocol chips; `nak_addresses` (EIO), `busy` (ETIMEDOUT), and a per-op `inject_fault()` FIFO. The log is a `_CallLog` capped at 4096 entries, halved on overflow, with a `dropped` counter.
- **SPI:** DMA-threshold (32 bytes) RX-overrun knobs.
- **UART:** subclasses `io.IOBase` so a real `poll.register()` works. It counts `would_have_blocked_bytes` in a class-level counter, and has `write_limit`.
- **UARTLink / `_LinkDirection`:** a byte-level crossover with deterministic fault knobs: silent, drop, corrupt, truncate, noise, delay, duplicate, capacity.
- **LinkPoller:** a bounded stand-in for `poll()`, never a real `select.poll()`.
- **Timer:** class-level `all_timers`, `raise_on_arm`/`raise_on_arm_exc`, plus `trigger()` and `drop()`.
- **RTC:** class-level datetime and `raise_exc`.
- **WDT:** a feed counter only.
- **`reset()` / `bootloader()`:** increment counters and **return**.

**Other mocks [verified]**
- `tests/_fram_chip_fake.py`: an MB85RS64V opcode interpreter subclassing the fake SPI. It has WEL knobs (`drop_wren`, `disturb_*_autoclear`, `corrupt_next_write_data`), the WP/WPEN protect table, and re-invokes the bus fault hook in `readinto`.
- `tests/network.py`: an inert WLAN driven by the test, with a `raise_on` dict and the real byte bounds on country, hostname, SSID and password.
- `tests/neopixel.py`: records every frame written.
- The allocator is the one other sanctioned seam (`_StarvedAlloc` in `test_asy_uart_comm.py`, spec E.4).

**Shared harnesses [verified]**
- `_shared_rest_roundtrip.py`: 3 helpers (all named modules constructed; payload not self-wrapped; strict-JSON drain).
- `_uart_comm_harness.py`: a `Pair`/`build_pair()` over UARTLink plus LinkPoller, with `run()` bounded by `wait_for`.
- `_uart_link_contract.py`: 20 `check_*` bodies in a hand-maintained `ALL_CHECKS` tuple. Both `test_machine_uart_link.py` (mock) and `test_digital_twin_machine_uart.py` (twin) run it, and `link.settle()` is the fidelity seam between them.
- `_bus_hazard_catalog.py`: `I2C_HAZARD_CATALOG`, a per-driver adapter (construct / seed / read_once / exercise, with optional `write_once` and `general_call`) plus generic scenarios. `test_bus_hazard_generated.py` turns these into per-device, per-bus tests from `build/generated_src/*_wiring_plan.json`.

**Per-device scenario libraries (spec E.2.1) [verified]**

| Library | Registration | Per-device wrappers | Scenarios × devices |
|---|---|---|---|
| `_sensortask_scenarios.py` | `@_register` | `test_sensortask_<dev>.py` | 56 × 6 |
| `_digital_twin_construction_scenarios.py` | `@_register_param` | `test_digital_twin_construction_<dev>.py` | 3 × 6 |
| `_webserver_concurrency_scenarios.py` | `_register(name, timeout)` | `test_digital_twin_webserver_concurrency_<dev>.py` | 21 × 6 |

Each wrapper is an 11- or 21-line file that runs `globals().update(register_for_device(dev))`. `test_uart_comm_hazard.py` registers 48 `_check_*` functions once per CRC mode, minus 2 mode-specific ones, for 94 tests.

**Counts [verified]:** 87 `tests/test_*.py` files and 3,194 statically defined `def test_` functions, plus roughly 575 dynamically registered ones. `tests_scripts/` has 60 test files.

**The four tiers (spec E.6.1):** mock (`tests/machine.py`), twin (`digital_twin/`), flash (`tests_hardware/flash/`, 10 files), bench (`tests_hardware/bench/`, 12 files). Manual (`tests_hardware/manual/`) is an execution mode, not a tier. Only `dev` is ever run on real hardware.

#### 2. Map: src module → tests

Every one of the 28 `src/*.py` modules has a dedicated `tests/test_<module>.py` [verified]. The AST/grep scan found only four public functions never named in `tests/`. Two are exercised indirectly through the task-starter list: `NeopixelDriver.start_asy_ext_cmd_watcher` and `start_asy_neopixel_signal`, which are reached via `get_task_starters()`. The other two, `after_request` and `after_error_request` in `asy_webserver_service.py`, are Protocol stubs.

The largest suites by test count:

| Test file | Tests |
|---|---|
| `test_asy_wifi_service` | 211 |
| `test_asy_isl29125_driver` | 210 |
| `test_config_manager` | 210 |
| `test_asy_webserver_service` | 187 |
| `test_asy_ntp_client` | 153 |
| `test_asy_uart_comm` | 146 (+94 in hazard) |
| `test_asy_fram_manager` | 122 |
| `test_base_classes` | 119 |
| `test_asy_bmp3xx_driver` | 114 |
| `test_asy_uart_driver` | 114 |
| `test_asy_sgp40_driver` | 109 |

Cross-module integration files: `test_fram_integration`, `test_notification_{fram,neopixel,scd30,sgp40,scd30_sgp40}_integration`, `test_ntp_{wifi_dns,fram_system}_integration`, `test_neopixel_wifi_integration`, `test_setter_microdot_integration`, `test_website_build_integration`.

Twin tier coverage:
- **Chip-fake unit tests:** `test_digital_twin_{scd30,sgp40,bmp3xx,isl29125,fram,machine,machine_uart,network_neopixel,http_client,launch,run_generic_integration,generic_wiring,poll_prewarm,unix_port_gc_unwedge}`.
- **Real driver on the twin:** `test_digital_twin_isl29125_autorange`, `bus_hazard_concurrency` (wozi and dev only), `sensortask_integration` (wozi only), `uart_link` (dev), `real_website_integration` (wozi), plus the per-device construction and webserver-concurrency files.

Gaps and observations:
- Twin bus-hazard coverage only needs wozi and dev. Every other device has one occupant per I2C bus [verified from `devices/*.toml`].
- No driver-specific twin test file exists for scd30, sgp40 or bmp3xx against the real driver. They are exercised only inside the whole-graph twin tests [inferred from file names].
- Only the ISL29125 has a C.11.1 conformance probe. SCD30, SGP40, BMP3xx and FRAM have none, and nothing guards that fakes built before that rule get one [verified].

#### 3. Digital twin

**Fakes [verified]**
- `digital_twin/machine.py` (946 lines):
  - Pins are singletons per id and edge-directional, via `simulate_edge` honouring the trigger mask.
  - I2C wires chip fakes from a wiring plan; unknown addresses raise `OSError(EIO)`; a general call to `0x00` is **silently accepted and delivered to no chip**.
  - SPI wires `FramChip`.
  - UART plus UARTLink have real wire timing from the baud rate (`settle()` waits).
  - Timers are asyncio tasks. They do not model F.1's soft-callback drop, which the mock has as `Timer.drop()`.
  - WDT enforces the 8388 ms cap and `id==0`, and uses a record-only countdown with a late-feed backstop.
  - `reset()` and `bootloader()` **raise** `SimulatedResetError` / `SimulatedBootloaderEntryError`.
  - `RTC.datetime(set)` returns the tuple where the real call returns None.
- `_scd30_chip.py`: word commands, a CRC on replies, an RDY edge per measurement interval, NVM persistence to JSON, and `corrupt_next_measurement`.
- `_sgp40_chip.py`: serial / self-test / measure-raw.
- `_bmp3xx_chip.py`: a hand-picked calibration block inverted through the real compensation formula; chip id 0x60 only.
- `_isl29125_chip.py`: the most faithful fake. Destructive `0x08` read, BOUTF semantics, persistence counter, tint, and `configure_fault` / `simulate_brownout`.
- `_fram_chip.py`: 8 KB or 256 KB with 3-byte addressing.
- `network.py`: `connect()` goes through an async 0.7 s phase plus scripted outcomes.

**Fault catalog [verified]**

| Target | Faults available |
|---|---|
| SCD30 | raise/hang on `writeto` and `readfrom_into`; corrupt-next-measurement |
| SGP40 | raise/hang on `writeto` and `readfrom_into`; corrupt-next-reply (constructor kwarg only) |
| BMP3xx | raise on `writeto`, `readfrom_mem`, `writeto_mem`; hang on the `_mem` ops only (no `writeto` hang) |
| ISL29125 | same as BMP3xx, plus persistent `configure_fault` and brownout |
| FRAM | raise/hang on `write` and `readinto` |
| SPI bus | `rx_overrun`, `rx_overrun_remaining` |
| UART link | the full knob set above |
| WLAN | `raise_on` per method, scripted connect outcomes |
| Twin I2C | no bus-level busy/ETIMEDOUT knob (the mock has `busy`) |

**Fidelity limits [verified by reading unless marked]**
- SCD30 fake:
  - It produces readings from construction onward, regardless of start/stop continuous measurement.
  - It never checks the argument CRC on written commands.
  - It accepts any measurement interval; an interval of 0 would re-arm a 0 ms periodic timer [inferred to hot-loop].
  - Soft reset is a no-op.
- SGP40 fake:
  - Command execution time is not modelled (no early-read NAK).
  - The measure-raw compensation-word CRCs are not validated.
  - It never sees the general-call reset.
- FRAM fakes (both mock and twin):
  - Transaction framing is inferred from the pairing of `write()` calls (opcode+address in one call, data in the next), not from CS.
  - Opcode, address and data in a single `write()` would lose the data. Wrap-around is not modelled, and a write past the end would grow the `bytearray` [inferred from MicroPython slice-assign semantics].
  - This couples the fakes to the driver's current call shape.
- Twin `network.py` validates no AP-mode config (no password length check).
- Spec E.8 records that the twin is 64-bit and non-frozen, so its heap figures are not board figures.

#### 4. Meta-tests and rule enforcement

**Machine-enforced [verified]**

| Rule | Guard |
|---|---|
| Comment cap (Python and shell) | `test_comment_block_cap.py`, 8 scopes |
| `gc.collect()` sites in `src/` and `buildgen/` | `test_gc_collect_sites.py` + `lint.sh` grep |
| Four MemoryError gates agree; injected messages avoid the markers | `test_memory_error_gate_agreement.py` |
| Persistence-write marker completeness and gating | `test_persistence_write_marker_completeness.py`, `test_tests_hardware_persistence_write_gating.py` |
| `method-assign` suppression banned in `src/` | `lint.sh` + `test_lint_sh.py` |
| `reset` / `WDT()` call sites | `tests/test_reset_call_site_invariant.py`, textual |
| ticks-arithmetic sweep | `tests/test_ticks_rollover.py`, `_KNOWN_TICKS_USERS` |
| Measurement NamedTuple vs `_FIELDS` agreement | `test_measurement_field_tuple_agreement.py` |
| Request timeout mirrors; body-cap headroom | `test_request_timeout_ceiling.py`, `test_request_body_cap_headroom.py` |
| Twin never needs `tests/` on its path | `test_twin_never_needs_tests_on_its_path.py` |
| `test.sh` ordering and `zz_test_*` namespace | `test_test_sh.py` |
| Boot contiguity, with a control arm | `test_digital_twin_boot_contiguity.py` |
| Bench no-task-ended; bench restores serving | `test_bench_*` |
| Device-script gc threshold and config flush | `test_device_script_*` |
| Hardware conftest constants | `test_tests_hardware_conftest_constants.py` |
| Real poll in UART doubles | `test_no_uart_built_here_polls_through_a_real_select_poll`, `test_twin_poller_is_not_a_real_select_poll` |

**Review-enforced only [verified that no guard exists]**
- The four-tier bus-hazard rule. Only the mock-generated tier fails loud, and only for a missing catalog adapter. Nothing checks for twin, flash or bench counterparts.
- Spec E.6.6 real-hardware parity.
- Spec K.6 "biting". Mutation sweeps are ad hoc and not in CI.
- `gc.collect()` inside `tests/` and `digital_twin/`: 20+ sites, none guarded.
- Nested `asyncio.run()` (the segfault rule) and the absolute-vs-rate heap bounds of E.8.
- Socket-port and `TmpScratch`-key disjointness across files.
- JS, CSS and config comment caps.
- `ALL_CHECKS` completeness in the UART link contract.

#### 5. Audit candidates

**A. Vacuous or non-biting tests**
1. **[verified] Tautology**, `tests/test_bus_hazard_generated.py:108-113`. `test_*_bus_membership_matches_the_real_toml_group` is registered only when `len(attachments) >= 2` and then asserts `len(attachments) >= 2`.
2. **[verified] Can pass without doing anything**, `tests/_bus_hazard_catalog.py` `scenario_each_occupant_never_touches_an_unexpected_address`. It wraps `exercise()` in `except Exception: pass` and asserts only `touched <= allowed`. If `exercise()` raised before any bus call, the empty set passes. There is no assertion that the device's own address was touched.
3. **[verified] Override tests that cannot fail**: `tests/test_digital_twin_scd30.py:202` and `tests/test_digital_twin_bmp3xx.py:151`, both `test_step_bounds_are_configurable_via_the_constructor`. Their scripted deltas (5.0/0.1/0.5 and 0.1/0.5) lie inside both the narrowed and the default step bounds, so `_FixedRandom`'s `a <= v <= b` passes even if the constructor ignored the override. The comments ("would violate the default bounds") are wrong.
4. **[suspicion, strong] Injected fault is probably never used**, `tests/_digital_twin_construction_scenarios.py` `_scenario_bus_fault_degrades`. It injects 5 SGP40 `writeto` faults after the build, starts only the webserver task, and `GET /measurements` goes through `get_dict_data()`→`get_data()`, which returns the stored reading and does not read the bus. The injected fault is probably never consumed, and the assertions (200, "SGP40" in body) hold without it. Its comment that `tests/machine.py` has "no comparable fault surface" is stale: that fake has `inject_fault()` and `nak_addresses`.
5. **[verified] Tautological and duplicated**, `tests/test_bus_hazard_multi_device.py:385`. The reserved-address check runs on literal constants defined in the test file itself (lines 63-66), with its own copy of the range logic (`_is_reserved` vs the catalog's `_is_reserved_i2c_address`). The generated scenario already checks the TOML addresses.
6. **[verified] Proof runs on a copy of the arithmetic**, `tests_scripts/test_timer_stagger_no_coincidence.py`. It re-implements `1000 // (n+1)` and hardcodes 1000. No test asserts `sequencer_timer.period` (grep of `tests/`), so a change to the formula in `src/system_service.py:159` would pass both tiers.
7. **[verified] Swallowed setup result**, `_uart_comm_harness.build_pair()` discards the result of `Pair.setup()` (about 60 call sites). Negative-only tests such as `test_a_write_that_never_reaches_the_peer_fails_the_same_way` (`test_asy_uart_comm.py:686-691`) assert only `is False`, which a failed setup would also produce.
8. **[verified] Overclaiming names**, `_sensortask_scenarios.py`. `..._light_cmd_led_dispatches_to_the_real_pixel_driver` and `..._round_trips_a_real_scd30_field_through_the_real_driver` assert only the "Valid" response, not a pixel write or the SCD30 register write.
9. **[verified] Silent skips count as PASS**: early `return` when a device lacks a module (`_sensortask_scenarios.py:289,890`), and the no-op branches in the catalog (`_run_write_vs_siblings_at_offset`, general-call). There is also no zero-test guard in `test.sh`.
10. **[verified] Only the first writer is exercised**. The cross-occupant write scenario uses `writers[0]` only. On dev i2c1 (TOML order scd30, sgp40, isl29125) ISL29125's write-vs-siblings is never generated.
11. **[worth checking] Must-not-raise tests on log-and-degrade code**, e.g. `test_asy_wifi_service.py:565-640,1600-1615`. These only pass if the method genuinely doesn't raise. For methods that log and degrade, they cannot detect a wrong degrade path.

**B. gc and memory discipline in tests**
12. **[verified] `gc.collect()` described as a MemoryError workaround**, contrary to CLAUDE.md's "no gc.collect() propping the result". `test_digital_twin_sensortask_integration.py:543-546` (comment: added because a later `build_system()` hit a MemoryError), `:627`, `:705`, `:779`; `_webserver_concurrency_scenarios.py:861` (after every scenario, justified as defence in depth); `test_fram_integration.py:157-177` (comment: exhausts the heap after about 7 cycles without it).
    **[suspicion]** MicroPython collects automatically when an allocation fails, whatever the threshold. So a MemoryError that only a manual collect prevents points to live retention or fragmentation (leaked tasks, sockets or buffers), not "GC timing" as the comments claim.
13. **[verified] Absolute heap bounds**, contrary to E.8's "a leak is a rate": `test_asy_webserver_service.py:1833` (`baseline - 4096` over 120 cycles) and `test_digital_twin_uart_link.py` `_hammer_with_the_graph_running` (`leaked < 8192`).

**C. Timing and flakiness (suspicion)**
14. Wall-clock bounds under 1-4× core parallelism: `test_asy_dns_client.py:332` (`<200 ms`), `test_captive_dns.py:482` (`<1000`), `test_asy_notification_service.py:1268` (`59<r<60` after `sleep_ms(50)`), `test_asy_udp_socket.py:926,994,1350`.
15. Fixed `asyncio.sleep(1.0)` waiting for the webserver to bind in `_digital_twin_construction_scenarios.py`, on a measured ~400 ms setup.
16. `test_digital_twin_bus_hazard_concurrency` has a 9 s real-clock budget that spec E.3.1 says fails at 8M heap.
17. 43 of 47 local `run()` helpers are an unbounded `asyncio.run(coro)`. A hang costs up to 3×240 s and is reported per file, not per test.

**D. Fakes diverging from real hardware (worth checking)**
18. Mock vs twin semantics:
    - `reset()` returns in `tests/machine.py:700` but raises in the twin.
    - The mock WDT accepts any timeout and id; the twin enforces 8388 ms and `id==0`.
    - Mock `Pin.init()` drops `pull` (`tests/machine.py:51-54`).
    - Mock `trigger_irq()` ignores the edge direction.
    - Mock `I2C.scan()` lists only register-seeded addresses.
19. The twin's general call reaches no chip, so the real SGP40 self-reset and any sibling that listens to general calls are not modelled.
20. The SCD30, SGP40 and FRAM gaps listed in §3.
21. **[suspicion, helper bug]** `test_asy_udp_socket.py:290` `AdversarialPeer.recv()` tests `if poller.ipoll(0):` for truthiness. `test_asy_dns_client.py:350-353` documents that this build reports a registered socket as ready on every tick, and says to check the event mask instead. `recvfrom` could then raise EAGAIN early.

**E. Test helpers and infrastructure**
22. **[verified]** `tests/test_reset_call_site_invariant.py` scans `src/` only. The real `WDT()` sites are now in `build/generated_src/`, so its `sensortask_` exemption is dead, and "exactly once per entry point" is never asserted. Its substring matching also misses an aliased import (`from machine import reset`).
23. **[verified]** Duplication:
    - 7 copies of the Timer raise-on-arm context manager (bmp3xx, isl29125, ntp, scd30, sgp40, wifi, system_service).
    - 47 local `run()` definitions and 20 files with their own `run_timed` / `_wait_until` / `_cancel`.
    - Deliberate twin/mock duplicates of network and neopixel.
24. **[verified]** Heavy private-attribute coupling (`._x` accesses): isl29125 tests 354, wifi 278, ntp 209, uart_comm 166, sgp40 161.
25. **[verified]** Class-level mutable state shared across tests in one process (`Timer.all_timers`, `raise_on_arm`, `RTC._shared_datetime`, `UART.would_have_blocked_bytes`, `machine.reset_count`, twin `Pin._registry`). Tests restore these in `finally`, but combined with the dict-order execution this is a hidden coupling risk.

**F. Documentation drift [verified]**
26. `digital_twin/README.md:107-108` says `WLAN.connect()` connects "immediately", but `digital_twin/network.py` uses a 0.7 s async phase (its own docstring says so).
27. Spec E.1 says TCP port bases are in 17400-19999, but `_webserver_concurrency_scenarios.py:77` allocates `19700+200*i`, reaching 20700+ for schlafzi.
28. CLAUDE.md says "86/86"; there are 87 test files now.

**G. Comment cap**
29. **[verified]** The detector finds 0 over-cap blocks. But it counts physical lines, E501 is ignored, and several docstrings pack a paragraph onto one line: `digital_twin/_fault_injection.py:3` is 700 characters, and `run_generic_integration.py:1-2` and `tests/test_digital_twin_run_generic_integration.py:1-2` are 447-626 characters per line. Owner decision whether to add a character bound.

#### 6. Suggested audit topics (checklist)

- [ ] **Mutation / clamp-removal sweep (spec E.8 technique)** over each guard in §5.A: shadow a mutated copy ahead of `src` on `MICROPYPATH` and require the named test to fail. Priorities: the stagger formula, SGP40 fault degrade, the reserved-address check, construction overrides, and ISL29125 as the cross-bus writer.
- [ ] **Fake-mutation sweep:** remove each fidelity rule from a fake (twin SCD30 start-measurement gating, WEL auto-clear, edge-direction masking) and check whether any test notices.
- [ ] Add a **zero-tests-ran guard** and a **"SystemExit(0) mid-file" guard** to microtest/test.sh; consider running tests in random or reversed order to expose inter-test coupling.
- [ ] Extend the `gc.collect()` structural guard to `tests/` and `digital_twin/`, with an allow-list of measurement-sampling and deliberate-GC-noise sites. Root-cause the MemoryErrors behind §5.B.12.
- [ ] Audit every absolute heap-delta bound against E.8's rate rule.
- [ ] Mechanically check socket-port and `TmpScratch`-key disjointness, and `ALL_CHECKS` completeness.
- [ ] Unify mock and twin semantics where they diverge without a stated reason (`reset`, WDT validation, `Pin.init` pull, RTC set return), or document each difference.
- [ ] Build C.11.1 conformance probes for the SCD30, SGP40, BMP3xx and FRAM fakes; decide on CRC-validated command arguments and command-timing NAKs in the fakes.
- [ ] Add a meta-test for the four-tier bus-hazard rule (every catalog driver has twin, flash and bench counterparts, or a recorded exception).
- [ ] Make "must not raise" and negative-only tests also assert the positive state (`setup()` result, fault queue drained, log entry written).
- [ ] Replace fixed sleeps and tight wall-clock bounds with `_wait_until` and generous liveness bounds; bound every local `run()`.
- [ ] Consolidate duplicated helpers into a shared test-support module.
- [ ] Review the twin's 64-bit / non-frozen heap caveat for every twin-tier allocation assertion.
- [ ] Decide on a character bound for the comment cap.

Relevant paths: `/home/user/sensors/tests/microtest.py`, `/home/user/sensors/tests/machine.py`, `/home/user/sensors/tests/_bus_hazard_catalog.py`, `/home/user/sensors/tests/test_bus_hazard_generated.py`, `/home/user/sensors/tests/_digital_twin_construction_scenarios.py`, `/home/user/sensors/tests/_sensortask_scenarios.py`, `/home/user/sensors/tests/_uart_comm_harness.py`, `/home/user/sensors/tests/test_digital_twin_scd30.py`, `/home/user/sensors/tests/test_digital_twin_bmp3xx.py`, `/home/user/sensors/tests/test_reset_call_site_invariant.py`, `/home/user/sensors/tests_scripts/test_timer_stagger_no_coincidence.py`, `/home/user/sensors/tests_scripts/test_gc_collect_sites.py`, `/home/user/sensors/digital_twin/machine.py`, `/home/user/sensors/digital_twin/_scd30_chip.py`, `/home/user/sensors/digital_twin/_sgp40_chip.py`, `/home/user/sensors/digital_twin/_fram_chip.py`, `/home/user/sensors/digital_twin/README.md`, `/home/user/sensors/scripts/test.sh`.

---

## Real-hardware tier

### Real-hardware test tier: read-only survey and audit candidates

Scope: `tests_hardware/` (all of it), `dev_legacy/README.md`, `REAL_HARDWARE_TEST_QUEUE.md`, `HARDWARE_TEST_HANDOVER.md`, `HEAP_FRAGMENTATION_MEASUREMENTS.md`, the `scripts/run_*hardware*` / `_require_clean_hardware_run.sh` / `run_bench_soak_tests.sh` / `mpremote_connect.sh` runners, and the bench-bridge half of `toolchain/setup_toolchain.py`.

Nothing was modified; `git status` is clean at `0615eba`. Nothing touched hardware or network state.
- I couldn't run `pytest --collect-only` because this sandbox has no `pyserial`, so the test counts below come from grepping `def test_` (no parametrize is used, so they are exact).
- The repo's own `tests_scripts/test_comment_block_cap.py` passes: 358 passed.
- In the findings, **[V]** means I checked it against source; **[S]** means suspicion or inference.

---

#### 1. How the tier is built

**Three automated tiers plus a manual mode** (SPECIFICATION E.6.1). All of it runs host-side under CPython and pytest, driving the board through `mpremote` and the bench through `nmcli`/`iw`/`iptables`/`tc`/`tcpdump`, all via `sudo`.

- **flash** (`tests_hardware/flash/`, 51 tests): USB serial only.
- **bench** (`tests_hardware/bench/`, 85 tests): adds the WiFi bridge. It always runs together with flash (`run_bench_hardware_suite.sh` passes both directories).
- **soak**: `long_soak`-marked tests (4) reached only through `scripts/run_bench_soak_tests.sh --tier {short,mid,long}` (60 s / 600 s / 6 h, `tests_hardware/soak_tiers.py`).
- **manual** (`tests_hardware/manual/`): a custom registry runner, deliberately not named `test_*.py`. It is run through `__main__.py` to avoid the duplicate-module registry bug described in the README.

**Opt-in gates** (`tests_hardware/conftest.py:25-113`). There are two mechanisms:
- **Skip-gated inside each test** (the flag is checked inline): `--allow-flash-cycle` (`flash_cycle`), `--soak-tier` (`long_soak`), `--allow-multi-day-rollover-wait` (`multi_day_rollover`), `--allow-neopixel-sweep` (`neopixel_sweep`).
- **Deselected at collection time** (`pytest_collection_modifyitems`, conftest.py:116-133): `persistence_write`, and `scd30_extra_write`, which is AND-gated on top of it.
  - `flash/conftest.py:18-33` is a backstop: it raises if the session SCD30 fixture runs without the flag.
  - Today 9 flash and 13 bench tests carry `persistence_write`; exactly one carries `scd30_extra_write`.
- `role_reversal` and `over_provisioned_image` are informational only.

**Harness** (`harness.py`):
- `Board` wraps `uv run mpremote connect <dev> …` and retries known transient errors. It escalates first to re-resolving the serial node, then to a `sudo tee` USB unbind/rebind (`_usb_reset_device`, harness.py:183-207).
- The device node is found by vendor ID and the `/dev/serial/by-id` symlink (`resolve_board_device`).
- `run_isolated()` (440-452) runs `exec machine.WDT(timeout=8000)`, then `run <script>`, then `soft-reset`.
- `is_reachable()` enters the raw REPL, which sends Ctrl-C to `main.py`. `is_device_present()` only opens the serial port. `tail_log()` reads serial passively.
- Also here: `discover_max_connections()` / `_walk_to_the_wall()` (the connection-ceiling probe), `restore_board_to_serving()`, and `MEMORY_ERROR_MARKERS` (shared with the soak gates).

**Device scripts** (`device_scripts/`, 57 files) are real MicroPython pushed with `mpremote run` against the frozen `src/` modules. Each prints a `RESULT: PASS|FAIL` line that the host parses. Only a real `hard_reset()` brings `main.py` back afterwards; `restore_board_to_serving()` exists for that in the bench tier.

**Bench control** (`bench_control.py`):
- AP down/up; station kick via `iw station del` (`kick_all_stations()`, the fix for the stale station-table flakiness).
- iptables FORWARD DROP for UDP 53/123; NAT PREROUTING DNAT to a local `RogueUdpResponder`; `tc netem` on the AP radio only.
- A `tcpdump -c 1` capture.
- Role reversal: the Pi's single radio stops hosting `br0-wifi-ap` and joins the DUT's own hotspot through a temporary NetworkManager profile.

**How a run is judged clean** (`_require_clean_hardware_run.sh`):
- Any nonzero pytest exit fails the run.
- It greps `-v` output for `SKIPPED` lines. The only skips allowed are one permanent entry (`test_spoofed_off_subnet_source_address_is_ignored`) and the skip-gates whose own flag is absent.
- It requires at least one pass.
- Deselected tests are invisible to all of that, so it prints the deselected count in the OK line.
- Both suite runners add `-m "not long_soak and not multi_day_rollover"`.

**Safety mechanisms, as documented:**
- The real-hardware go-ahead gate (CLAUDE.md).
- The dead-man's switch (SPEC B.13). This is a **manual procedure only**; no code arms one (grep for `systemd-run`/`bench-recovery` finds only docs).
- `br0` MAC pinning in `ensure_bench_bridge()` (setup_toolchain.py:843-930). It pins on creation and only warns on an existing bridge.
- The FRAM-forensics rule: a manual "Step 1" in the queue and handover docs.
- `kick_all_stations()` before every `hard_reset()`.
- `joined_hotspot` teardown restores the SSID and falls back to `hard_reset()`.
- `assert_no_task_ended()`.
- `error_log_helpers` resets error logs before and after each fault-injection test.

#### 2. The bench rig as documented

Sources: `dev_legacy/README.md:30-62`, `devices/dev.toml`.

| Item | Detail |
|---|---|
| Board | RP2040 Pico W `dev` unit |
| I2C0 | GP13/12 @ 50 kHz: BMP384 @0x77. The wiring table also lists an **MPRLS (reset GP10, EOC GP7)** |
| I2C1 | GP15/14 @ 50 kHz, timeout 200000: SCD30 (RDY GP11), SGP40 @0x59, ISL29125 @0x44 (INT GP6, external pull-up) |
| SPI0 | GP2/3/4: FRAM **MB85RS2MTA 256 KB** on CS GP5 (wozi uses an MB85RS64V 8 KB) |
| NeoPixel | GP18 |
| UART crossover | Permanent jumper GP0↔GP9 and GP1↔GP8 (UART0↔UART1), carrying two `uart_link` instances |
| Host | Raspberry Pi 4 on Debian trixie (GCC 14.2) |
| Network | NetworkManager bridge `br0` = `br0-eth0` + `br0-wifi-ap` (WPA2/CCMP, PMF off, channel 6, random SSID/PSK); `br_netfilter` persisted (setup_toolchain.py:815-840) |
| Optional rig | The WS2812 aimed at the ISL29125 window, for `--allow-neopixel-sweep` |
| Not present | Scope, logic analyser, GPIO fault-injection hardware (owner: none will be bought) |

The Arduino C-side UART peer exists but is out of scope.

#### 3. What is owed on silicon, and the heap-measurement method

**Queue** (`REAL_HARDWARE_TEST_QUEUE.md`): 30 rows owed.
- **D3**: always a `dev` build of the tree under test.
- **Suite runs**: S3b (NeoPixel sweep, after M1 records the rig geometry), S4 (the long soak has never been run).
- **Heap/Measure A**: T1 (in-suite AFTER `largest_block`), T2 (bus-hazard tier 4 on the A+B arm), T4 (per-command FRAM hold time; its A6 script lives **only inside the queue doc**, §1A).
- **New features**: N2 (hostname default substitution), N3 (UART W11 vs W10, which needs R13's babbling peer).
- **Investigations**: R1 (ISL29125 connection reset under load / BACKLOG 30), R2 (`ResetErrors` reader-count curve), R4 (`ResetErrors` completeness under contention), R5 (third BMP3XX config-write pass), R6/R7 (FRAM setup cost, the unexplained +0.90 s boot), R9 (`Overrange`), R13.
- **Findings**: F1 (re-verify the SSID repro that once stranded the bench), F17 (silent resets and hotspot fallbacks).
- **Tests to write**: G1, G3, G4, G6 (ticks_ms rollover method, measurement deferred), G8 (the CLAUDE.md "(e) stage" under real load has never run on silicon), G11, G12 (F.5.8 against the real driver).
- **Bench host**: H1, the two-chroot check, unsatisfied since 2026-09-12.
- **Connection limit of 6**: W3, W4 (the first full bench tier at the limit), W5 (the 1,026 B `NTP_Host` piece).

**Handover** (`HARDWARE_TEST_HANDOVER.md`) gives the running order:
1. Save `errcount`.
2. Build, flash and verify `buildDate`.
3. G11 code.
4. Flash tier.
5. Bench tier (W4, then W3).
6. The write-gated run with `--allow-persistence-writes -s` (R1, R5, T2, R4, W5).
7. M1, then S3b.
8. R2, F1, T4, R6/R7, R13+N3, N2.
9. Scripts still to write.

It lists what changed on silicon since image E6′ (webserver header/reset/slot fixes, SCD30 non-finite rejection, NTP backoff/E21, and more).

**HEAP_FRAGMENTATION_MEASUREMENTS.md** is method only; the results are archived at `12640c2`. Its main points:
- The allocator model is lowest-fit with a hint, no compaction; placement is a "knife edge".
- The preferred instrument is `mem_info(1)` block maps parsed host-side by `heap_map.py`. The bisecting probe is a cross-check only, with its own "pins its buffer" artifact visible via `retained=`.
- Which metrics work: `new_above`, `free_above_top_survivor`, `placeable(n)`.
- Thresholds are derived from the worst reachable allocation, never fitted to a reading.
- Traps §M3.1-15, including: the GC threshold is inherited across attaches, so every script sets and prints `GC_THRESHOLD=`; position decides the answer; ensemble the runs; twin fakes allocate where the board does not.
- Twin calibration: fill fraction, a 32-bit frozen twin, throughput-matching.
- Serving: the need sieve and the linker-heap formula `187,712 + (8−L)×2,324 B`.
- Ruled-out remedies (§M7).

---

#### 4. Audit candidates

##### A. Safety: wear, host lockout, evidence loss

1. **[V] The routine flash tier rebuilds the whole host environment on every run.** `flash/test_toolchain_flash_boot.py:30-42` is unmarked and runs `setup_toolchain.py env --tier flash` (~481 s). That path (setup_toolchain.py:1063-1080 and 1014-1040) does:
   - a git fetch and a full toolchain rebuild;
   - `uv sync` into the very venv pytest is running from;
   - `npm ci` (reinstalls ~200 packages) and a Playwright Chromium install;
   - `sudo apt`/`usermod` checks.

   This conflicts with CLAUDE.md's "no avoidable wear, host SSD included" rule. It also mutates the running interpreter's packages, and it makes a hardware run depend on third-party downloads, which CLAUDE.md says must never read as a red test.
2. **[V] Bridge creation arms no dead-man's switch.** `ensure_bench_bridge()` creation path (setup_toolchain.py:896-925, `nmcli connection up br0-eth0` at 922) enslaves `eth0` into `br0`. That is exactly the operation behind the 2026-09-04 lockout, and it runs with no switch armed. The switch exists only as the manual SPEC B.13 recipe, and that recipe's own script hardcodes the profile name `"Wired connection 1"` **[S: this may not be the profile name on trixie]**.
3. **[V] SCD30 NVM is reachable over REST; the documented "structural exception" is wrong.**
   - `asy_scd30_driver.py:257-275` overrides `_set_dict_cfg` with a dispatch table. It sends `TempOffs`, `MeasInt`, `AmbPres`, `Altitude`, `ForceCalRef` and `SelfCal` straight to real I2C NVM writes. Each field has an `@web` tag (lines 64-70).
   - `asy_webserver_service.py:431` calls `module._set_dict_cfg` for every sensor.
   - So `PUT /sensors {"SCD30":{...}}` does reach NVM. The manual tier even tells the operator to do it (`manual_persistence.py:40`).
   - Places that say otherwise:
     - SPEC E.6.6 exception 2 (lines ~3203-3204) and C.8 (~2153);
     - `tests_hardware/README.md:748, 1130, 1173, 1196, 1240`;
     - `bench/test_sensor_config_push_over_real_hardware.py:22`.
   - Consequences: the bench-parity exception is invalid, and the wear surface is larger than the gates assume.
4. **[V] The manual SCD30 test leaves NVM changed.** `manual_persistence.py:37-47` sets `MeasInt=7` and gives no restore step. Later SCD30 tests assume the ~2 s interval, e.g. `scd30_real_irq_edge.py:11` (`FAST_PATH_DEADLINE_S=5.0`). **[S]** They would then fail or change behaviour.
5. **[V] The manual "FRAM" power-cycle test cannot succeed as written.**
   - `manual_persistence.py:18-19` writes `WarnCO2=424242`, but the field's range is 0..3000 (`buildgen/codegen.py:28`), so the PUT returns Invalid, not the 200/Valid it waits for.
   - That config lives in the flash filesystem's config file, not FRAM.
   - The test names the chip MB85RS64V; the dev board has an MB85RS2MTA.
6. **[V] An unmarked flash write in the NeoPixel sweep.** `device_scripts/isl29125_mechanism_envelope.py:100-108, 150-162` makes about 5 `_set_dict_cfg` → `write_config()` flash writes to a scratch file per run. It runs under `neopixel_sweep` only, not `persistence_write`. The completeness guard (`tests_scripts/test_persistence_write_marker_completeness.py:55`) excludes `device_scripts/` entirely, so nothing catches it.
7. **[V] FRAM evidence has no automated safety net.** There are 80 `reset_all_error_logs` / `ResetErrors` sites across 9 files and no session fixture that snapshots `errcount` before the first reset. The flash-tier FRAM scripts also overwrite production's first chunks unconditionally. CLAUDE.md's rule is enforced only by the manual "Step 1".
   - The extended hammer soak (`test_memory_stress_bench.py:120`) resets at its start despite a docstring about preserving evidence.
   - Its `_FRAM_BACKED_MODULES` (line 22) omits WIFI, NTP, WEBSERVER, DNSSRV, `CFGMGR_*` and `UART_*`, so a WEBSERVER memory failure under the hammer would not fail it.
8. **[S] FRAM write-protect can outlive a crashed script.** `fram_write_protect_roundtrip.py` sets WPEN|BP0|BP1, which are **non-volatile** on the chip. It restores them only in a `finally`, which a watchdog reset or a killed mpremote skips. The driver's `setup()` re-reads WP from hardware (`asy_fram_driver.py:387-388`), so production would silently keep FRAM write-protected. Worth a post-run WP-clear assertion.
9. **[V] A credential-looking string is committed.** `device_scripts/wifi_reconnect_after_failed_attempts_repro.py:9-10` contains `REAL_SSID="sensors-bench-ap"`, `REAL_PW="<redacted: bench PSK, HW.T11>"`. CLAUDE.md names only the hotspot fallback password as a known credential. The owner should say whether this PSK was or is live. Separately, `dev_legacy/README.md:661` commits the Pi's `eth0` MAC (minor).
10. **[V/S] The F1 repro is probably doomed on silicon.** `wifi_service_reconnect_repro.py` (queue row F1) runs up to 13 minutes (180 s + 600 s loops) and never feeds the watchdog. The production firmware arms `WDT(timeout=8000)` in `build_system()` (codegen.py:381), and the RP2040 watchdog survives an attach.
    - **[S]** So the script is likely reset about 8 s in.
    - That would leave `config_HWTEST_WIFI.cfg`, which holds the real WiFi password, undeleted, since the cleanup `_drop_scratch` never runs.
    - The same applies to the orphan `wifi_reconnect_after_failed_attempts_repro.py`.
11. **[S] Role-reversal setup failure can strand the board.** `bench/test_hotspot_role_reversal.py:58-89` persists `SSID=""` and calls `ap_down()` *before* the `yield`. If stage 1 or 2 fails, the generator's teardown (the SSID restore and `ap_up`) never runs. The board stays in hotspot mode and the bench AP stays down for the rest of the session. The next session's `_recover_stale_dut_credentials` would likely repair it.

##### B. Tests that can pass vacuously, or whose name overstates the check

12. **[V] Four role-reversal "tests" check nothing of their own.** `test_dut_enters_hotspot_mode_after_ssid_cleared` and `test_bench_radio_associates_within_bounded_window` are `pass`. `test_hotspot_password_matches_known_fixed_value` asserts a constant equals itself. `test_hotspot_ssid_matches_configured_hostname` only checks non-empty. All at test_hotspot_role_reversal.py:~124-150, and all inflate pass counts.
13. **[V] The I2C address sweep cannot fail on NAK or ACK.** `bus_topology_autodetect_and_hazard_sweep.py:33-44`: `_probe()` returns `None` for both, so the "address sweep" and "reserved-range sweep" only catch non-`OSError` exceptions.
    - The self-hazard reads (8 reads with `sleep(0)`) probably finish before the second broadcast (0.2 s spacing), and nothing proves they overlapped.
    - **[S]** If the MPRLS in dev_legacy's table is really on i2c0, general-call `0x06` gets broadcast at an unlisted device. The docs claim "i2c0: BMP3xx alone".
14. **[V] The DNS-garbage test can't tell garbage from silence.** `bench/test_network_resilience.py:328-362` asserts NTP `E12`, which its own comment says is the same as no reply. Meanwhile the README (lines 671-679 and ~990-1000) documents that DNAT-to-loopback does **not** deliver to local listeners (`route_localnet=0`), yet also says the `RogueUdpResponder` tests are "unaffected". Those two statements contradict each other. The NTP twin test is fine: it asserts `Invalid NTP time received!`.
15. **[V] Soak tests assert less than their names claim.**
    - `test_real_hardware_memory_does_not_leak_under_real_http_soak_traffic` (bench/test_memory_stress_bench.py:136-174) never measures memory: no `mem_free` trend, only crash/reboot markers and fewer than 5 request errors.
    - `test_single_core_timing_headroom_holds…` (flash/test_memory_stress.py:87-105) measures no timing.
    - `test_scd30_real_clock_stretch…` (flash/test_bus_electrical_timing.py:83-93) is "never observed".
    - None of the three has an engagement floor. All depend on the log `DebugLevel`, so at level 0 they pass on silence.
    - **[S]** The session `board` fixture's `is_reachable()` stops `main.py`, and the watchdog reboots the board about 8 s later. So the first soak test may see reboot markers (a false fail), or, if it doesn't, the later ones read a freshly rebooted system.
16. **[V] The boot-mechanism oracle is loose.** `flash/test_reboot_persistence.py:66` accepts `"CFGMGR_" in log or "FRAM" in log`, which an error line would satisfy. The same oracle is reused at network_resilience.py:312 and 341.
17. **[V] Every device script that clears UP writes FRAM on the way.** Watchdog-starvation (`test_watchdog_starvation.py`) does not check `machine.reset_cause()`, so any hard fault within 10 s passes. **[S]**
18. **[V] Orphan device scripts with no pytest wrapper:** `wifi_country_hostname_edge_values.py` (both branches print PASS), `wifi_reconnect_after_failed_attempts_repro.py`, `wifi_service_reconnect_repro.py`, and `heap_layout_after_full_boot_sequence.py` (documented as a manual instrument).

##### C. Stale or contradictory docs

19. **[V] Test counts disagree.** README:1354 says "13 of the bench tier's **73**"; the actual count is 85, matching the queue's D1.
20. **[V] Wrong FRAM chip named for dev.** README:710, `flash/test_fram_storage.py:1` and `manual_persistence.py:3,14` say MB85RS64V; the device scripts and dev_legacy say MB85RS2MTA.
21. **[V] `hard_reset()` is described two ways.** `harness.py:466-469` and `test_reboot_persistence.py:1-2` call it a "DTR-line/DTR-based reset"; README sixth-pass item 4 calls it a real `machine.reset()`.
    - **[S, from memory; the mpremote source isn't in the sandbox]** mpremote's `reset` is an exec of `machine.reset()`. If so, it needs a raw-REPL Ctrl-C, so a board wedged in a non-interruptible C call cannot be recovered by any harness "recovery `hard_reset()`". Nothing in the harness drives a RUN pin, and the USB unbind doesn't reset the RP2040.
22. **[V] Stale `DebugLevel` comments.** `test_reboot_persistence.py:52,68,77,79` say the board is kept at `DebugLevel=0` and "restore to 0". The queue and handover say `DebugLevel 5`, and the restore script actually restores the previous level.
23. **[V] Stale rollover guidance.** README:503 still recommends `board.exec()` polling for the ticks_ms rollover test; queue G6 and the test itself (test_bus_electrical_timing.py:130-137) say that polling is self-defeating.
24. **[V] `dev_legacy/README.md` is stale on several points:**
    - "MicroPython 1.28.0" (line 19);
    - "Current bench state (as of 2026-09-02)" (595-665): VFS empty, no watchdog armed, "until the per-variant generator exists" (641), FRAM "7 chunks / ~720 B" (642), "SCD30 offset 1.5 °C" (649, overwritten since by NVM tests);
    - the whole "bench-only frozen firmware" recipe, now superseded by `scripts/build_firmware.py dev`.
25. **[V] Small pointer and message errors:**
    - README:87 and `run_bench_soak_tests.sh:4` point at `conftest.py`'s `SOAK_TIER_SECONDS`; it lives in `soak_tiers.py`.
    - README:587's datasheet list omits `isl29125/`.
    - The role-reversal file's `_HOTSPOT_PASSWORD` comment says "hardcoded in `_configure_hotspot_ap()`"; it is now the per-device schema field `HotspotPW`, and this copy isn't pinned by `test_tests_hardware_conftest_constants.py`.
    - `_require_clean_hardware_run.sh:106` prints a truncated sentence ("…flags) to.").
    - `bench_control.py:103-104`'s docstring says "OUTPUT/FORWARD", but only FORWARD rules are added.

##### D. Fragility and hardcoded assumptions

26. **[V] Pin numbers are hardcoded in every device script.** Pins appear in about 20 scripts (e.g. `I2C(1, 15, 14, …)`), plus `bus_topology…py:30`, with no guard tying them to `devices/dev.toml`. `sgp40_voc_algorithm_quality.py:46` and `sgp40_fram_backup_restore.py:54` omit `timeout=200000` on i2c1, which every other script passes. **[S]** Because rp2 I2C objects are per-bus singletons, this may reset the timeout for SCD30 on the same bus.
27. **[V/S] Silent host-side assumptions.**
    - The session-scoped `dut_ip` assumes the DUT's DHCP address is stable across dozens of `hard_reset()`s; there is no reservation noted for the DUT.
    - The whole tier needs passwordless `sudo` for `nmcli`/`iw`/`iptables`/`tc`/`tcpdump`/`picotool`/`tee`.
    - `mpremote_connect.sh` defaults to `/dev/ttyACM0`, which may be the Arduino.
    - `wait_for_link_local_teardown()` is a fixed 2 s sleep.
    - The "leave > 45 s between a reset and the next attach" trap is not enforced anywhere.
    - `pyproject.toml` leaves `mpremote` and `pytest` unpinned, despite its "PINNED like every tool" comment; `uv.lock` has 1.29.0. The harness depends on mpremote's exact raw-REPL and soft-reset behaviour.
28. **[V] Flag parsing and last-wins `-m` in the runners.**
    - `_require_clean_hardware_run.sh:19-24` only recognises `--soak-tier` as a separate argument; `--soak-tier=long` would still be whitelisted as an expected skip.
    - pytest's `-m` is last-wins, so a caller's `-m` (the README suggests `-m role_reversal`) replaces the runner's soak exclusion.

---

#### 5. Audit topics / checklist

**Desk review only (no go-ahead needed):**
- [ ] Re-derive every "structural exception" (SPEC E.6.6/C.8, README tenth pass) from source, starting with SCD30 (item 3). List every REST field that reaches NVM or flash, and check each against the gates.
- [ ] Extend the marker-completeness audit to `device_scripts/` (`write_config`, `_set_dict_cfg`, `set_*` on SCD30, scratch-file writes). Map each script to its wrapping test's markers.
- [ ] Decide whether `test_env_tier_flash_recurring_run_is_idempotent` belongs in the routine flash tier, given the host-SSD-wear and third-party-outage rules.
- [ ] Decide whether `ensure_bench_bridge()`'s creation path should arm the B.13 switch in code. Check that the recovery script's `"Wired connection 1"` exists on the trixie host.
- [ ] Owner decision on `wifi_reconnect_after_failed_attempts_repro.py`'s PSK and the committed MAC.
- [ ] Audit oracles for vacuity: probe None/None, the DNS-garbage E12, the soak tests, the four role-reversal no-ops, `"CFGMGR_" or "FRAM"`, watchdog without `reset_cause`. Also require an engagement floor (lines seen, uptime advancing, requests served) on every passive tail test.
- [ ] Reconcile the DNAT-to-loopback README contradiction.
- [ ] Update `_FRAM_BACKED_MODULES` to CLAUDE.md's list. Consider an automatic session-start `errcount` snapshot to a file before the first `ResetErrors`.
- [ ] Fix or flag the doc drift in items 19-25; decide whether `dev_legacy/README.md`'s "Current bench state" gets pruned (per the "no history" agreement).
- [ ] Add a guard that ties device-script pins, timeouts and `KNOWN_ADDRESSES` to `devices/dev.toml`, similar to `test_tests_hardware_conftest_constants.py`.
- [ ] Check that every long device script feeds the watchdog, or document that it must be run on a board with no armed watchdog (F1, the orphans).
- [ ] Runner robustness: `--flag=value` parsing, `-m` override, parametrized IDs containing spaces in the skip regex.
- [ ] Is MPRLS physically on i2c0 (owner question)? If so, update the "BMP3xx alone" claims and the self-hazard reasoning.
- [ ] Verify mpremote's `reset` semantics from its source, and decide whether the harness needs a true out-of-band reset (RUN pin).

**Needs the owner's hardware go-ahead:**
- [ ] Read and save `errcount` first (the CLAUDE.md rule), and ask what was last run against the board.
- [ ] Confirm FRAM WPEN/BP bits are clear on the dev board after the flash tier.
- [ ] Read back the SCD30's current NVM settings (MeasInt, TempOffs, AmbPres), since the manual test and the extra-write test change them without restoring.
- [ ] Verify whether `RogueUdpResponder` actually receives DNAT'd DNS queries (count datagrams host-side).
- [ ] Try F1 with a watchdog feed, or on a board with no armed watchdog.
- [ ] Run the soak tier at `DebugLevel` 5, with an engagement floor added, to see whether its passes are substantive.
- [ ] Everything in the queue and handover (W3/W4/W5, R1/R2/R4/R5/R9/R13, T1/T2/T4, G8/G12, S3b after M1, S4). H1 needs the host only, no board.

Key files:
- `/home/user/sensors/tests_hardware/conftest.py`, `harness.py`, `bench_control.py`, `README.md`
- `/home/user/sensors/tests_hardware/flash/test_toolchain_flash_boot.py`
- `/home/user/sensors/tests_hardware/bench/test_hotspot_role_reversal.py`, `test_memory_stress_bench.py`, `test_network_resilience.py`
- `/home/user/sensors/tests_hardware/manual/manual_persistence.py`
- `/home/user/sensors/tests_hardware/device_scripts/isl29125_mechanism_envelope.py`, `wifi_reconnect_after_failed_attempts_repro.py`, `wifi_service_reconnect_repro.py`, `bus_topology_autodetect_and_hazard_sweep.py`, `fram_write_protect_roundtrip.py`
- `/home/user/sensors/scripts/_require_clean_hardware_run.sh`
- `/home/user/sensors/toolchain/setup_toolchain.py`
- `/home/user/sensors/src/asy_scd30_driver.py`
- `/home/user/sensors/dev_legacy/README.md`
- `/home/user/sensors/REAL_HARDWARE_TEST_QUEUE.md`, `HARDWARE_TEST_HANDOVER.md`, `HEAP_FRAGMENTATION_MEASUREMENTS.md`

---

## Website (JS/HTML/CSS)

### Website audit survey: js/, html/, build and freeze path, definitions generation

This was a read-only survey. I read every file in js/, html/, eslint.config.js, the tsconfigs, vitest.config.js, the lint configs and both build scripts in full. I read buildgen/web_tag.py and the field-generation half of buildgen/definitions.py. I sampled the tests in tests_js/ and cross-checked everything against the src/ validation code (config_manager.py, asy_webserver_service.py, base_classes.py, asy_wifi_service.py).

**Two process notes:**
- My one `python3 -m buildgen.definitions … --out <scratchpad>` run created `buildgen/__pycache__` and `toolchain/__pycache__`. Both are gitignored. I deleted those two directories, which I had created myself, and `git status --ignored` is now clean.
- A later scratchpad-only command to measure the gzip sizes of the bundle and index was blocked by the permission classifier. I did not work around it, so **gzip sizes are unmeasured**. node_modules is not installed, so I ran no ESLint, tsc or Vitest.

Tags used below:
- **[V]**: verified by reading code or computing directly.
- **[I]**: inferred.
- **suspicion**: a probable defect.
- **worth checking**: needs a decision or a test.

---

#### 1. Architecture

##### Module map (js/, about 1,950 lines)

| Module | Lines | Role |
|---|---|---|
| `field-format.js` | 40 | Pure `formatFieldValue()`. Handles mask, enum label, `gmtimestruct`, `decimals` via `toFixed`. |
| `poll-manager.js` | 132 | `fetchWithTimeout()` (AbortController, 15000 ms), the `PollManager` single-flight promise queue exported as the `pollManager` singleton, and `startPolling()` (a self-scheduling `setTimeout` loop). |
| `definitions.js` | 257 | JSDoc typedefs, `resolveFieldValue()` (the `path` walk and the `defaultValue` fallback), `validateDefinitions()`, `validateFieldHints()`, `loadDefinitions()` (reads the inlined `<script type=application/json>` first, otherwise fetches). |
| `templates.js` | 395 | The only DOM builder: `buildField`, `buildFieldGroupCard`, `buildErrcountGroup` (with its own filter-button listeners), `buildSectionShell`, `buildNavDrawer`. |
| `render.js` | 417 | Section controller: `renderSection()`, `paint()`, `fetchOnce()`, `collectGroupBody()`, `readInputValue()`, `reconcileResults()`, `applyResultStyling()`, `groupValuesFrom()`. |
| `nav.js` | 67 | Drawer open/close, Escape key, `aria-current`. |
| `main.js` | 60 | Production entry. |
| `app.js` | 87 | Prototype entry: `?device=` allowlist of wozi/dev, then `installMockFetch`. |
| `mock-server.js` | 501 | Prototype-only fake backend that patches `window.fetch`. |

##### Data flow

1. `index.html`'s inline module imports `../js/app.js`. In a device build that path is the bundled `main.js`; under `npm run preview` it is the prototype entry.
2. `loadDefinitions()` runs, then `initNav()` builds the drawer, then `selectSection(landingSection)`.
3. `renderSection()` calls `buildSectionShell()` (`mainEl.replaceChildren()`), then `fetchOnce()` → `pollManager.request(GET)` → `paint()`.
4. Only `pollGroup === "live"` polls (`render.js:377`). "settings" and "none" behave the same: one fetch, repeated after each Apply.
5. `paint()` treats groups three ways:
   - Errcount cards are rebuilt from scratch on every tick, and the expanded state is restored by re-clicking the filter button (`render.js:296-312`).
   - Writable groups already on screen only get their captions updated in place (`render.js:321-334`).
   - Everything else is rebuilt.
6. Apply runs `collectGroupBody()`. That sends a sparse body: blank inputs are omitted, and a toggle/enum equal to its baseline is omitted unless it is `dispatch`. `/sensors` bodies are nested under the group key. The PUT then goes through `pollManager`, and the result is coloured with four states at card and field level.
7. `render.js` branches on section *keys*: `sensors` (nested body and result), `status` (every submitted field marked Valid), `notification` (a second GET of `/status` to get `PauseTime`), and `measurements`/`sensors`/`status` in `groupValuesFrom()`. There is no *device* branching, but there is endpoint-key coupling.

##### Mock server
- Intercepts the 6 REST paths only.
- Adds an 80–200 ms fake latency.
- Supports one-shot failure injection: `network`, a status number, `malformed-body`, `torn-json`, `empty-body`, `partial-result`.
- Models the real quirks: `PW` masked, `ForceCalRef` read back as 400, command-only fields omitted from GET, and `SystemCmd`/`PauseTime`/`lightCmdLED` dispatch.
- Adds random jitter to readings.

##### Formatting, errors and timeouts
- Formatting lives in `field-format.js`; it is the only place any value is rounded.
- A failed GET shows a per-section `role=alert` banner and keeps the stale data.
- A PUT counts as a whole-request failure on non-2xx, a null body, or `res:"ERR"`. Every submitted field is then marked Failed.
- Every request is bounded by the 15 s AbortController.

##### Accessibility and layout
- Accessibility basics: `aria-expanded` on the hamburger, `aria-current` on nav links, `aria-pressed` on toggles, labels with `htmlFor`, `role=alert` banners.
- Layout: `grid auto-fill minmax(280px)`, an off-canvas drawer `min(280px, 80vw)`, a single `@media (width >= 640px)` breakpoint.
- Theming: colour tokens on `:root`, with dark mode switched automatically via `prefers-color-scheme`. There is no toggle and no `color-scheme` declaration.

---

#### 2. Build and freeze path [V]

**`scripts/build_website.sh <device>`:**
1. Uses `html/definitions/<device>.json`, or runs `python3 -m buildgen.definitions` into a scratch dir if there is no hand-written file.
2. Inlines `style.css` into a `<style>` block. It does this by exact-string replacing the `<link>` tag and fails loudly if the tag is missing.
3. Inlines the definitions as `<script type="application/json" id="inlined-definitions">`, with every `<` rewritten to `<`.
4. Concatenates field-format, poll-manager, templates, definitions, render, nav, main into `js/app.js`, stripping imports with `grep -v '^import .* from "\./[^"]+\.js";$'`.
5. Hands off to `build_frozen_html.sh`: `cp -r`, then `gzip -9` every file, then `freezefs --on-import mount --target /html --overwrite always` into `frozen_modules/frozen_html.py`.

**Serving:**
- `src/asy_webserver_service.py:649-667` opens `<name>.gz` and calls `send_file(..., compressed=True)` with an explicit Content-Length and 256-byte chunks.
- It rejects `..`, and in hotspot mode redirects unknown paths to `/` (captive portal).
- **No `Cache-Control`, ETag or Last-Modified is sent**: Microdot's `default_send_file_max_age = None` (`ext/microdot.py:575`). So every visit re-downloads index and app.js; that avoids stale-cache risk after a reflash but costs 2 requests per visit.
- Content-Type comes from the extension, with no charset. Module scripts are always UTF-8, and index.html has `<meta charset>` early, so this is fine [I].

**Sizes:**
- Raw source: js ≈ 1,450 lines of production JS; style.css 480 lines.
- Definitions: wozi.json 21,108 B and dev.json 36,849 B, before being inlined into index.
- Gzip sizes: **unmeasured**.

---

#### 3. definitions.json: generated versus hand-written

- wozi and dev are **still hand-written** (`html/definitions/*.json`). The other four devices are generated at build time (`build_website.sh:26-38`).
- I ran the generator for wozi and dev into the scratchpad and diffed:
  - **Order-insensitive the output is equal** to the hand-written files, and schemaVersion 1.0.0 / websiteVersion 2.0b0 match.
  - **Field order differs [V]**:
    - wozi SCD30: generated `TempOffs, MeasInt, AmbPres, Altitude, ForceCalRef, SelfCal, ContMeas`; hand-written `MeasInt, TempOffs, AmbPres, Altitude, ContMeas, ForceCalRef, SelfCal`.
    - wozi BMP3XX differs as well.
  - So the generated devices show fields in a different order from the hand-written ones. H.5.1's "reproduces exactly (order-insensitive)" hides a real UI difference.
- Drift risks between src/ and JS:
  1. The generator infers kind/min/max/float from the src/ `FieldSchema` through an AST read, but **the hand-written wozi/dev files do not update when src/ changes**. The only guard is `tests_scripts/test_buildgen_definitions.py`'s order-insensitive comparison.
  2. The generator emits no `specialValues` for **string** fields (`_string_field`, `buildgen/definitions.py:164-173`). `PW`'s `""` sentinel (`asy_wifi_service.py:46`, minLength 8) therefore exists server-side but not in the definitions or the mock. The UI cannot send `""` anyway (an accepted gap).
  3. **The UTF-8 byte bounds** on SSID/PW/Country/Hostname/HotspotPW (C.7.4, `asy_wifi_service.py:76-82,696`) appear nowhere in the definitions or the mock. The UI text says "Length: 0 to 32 characters" and `mock-server.js:59-61` counts UTF-16 code units.
  4. `web_tag._coerce_default_value("nan"|"inf")` would produce a float that `json.dump` writes as `NaN`, which `JSON.parse` rejects. That would kill the whole inlined page (**suspicion**, `buildgen/web_tag.py:120-131`).
  5. `defaultValue`'s type is never checked against the field's kind.
  6. `_MAX_DECIMALS = 100` is mirrored by hand in JS (acknowledged in a comment).

---

#### 4. Security

- **XSS [V]**: every DOM write is `textContent`, `placeholder` or `dataset`. The only `innerHTML` is in a test (`templates.test.js:440`). Device-returned strings (SSID, hostname, the server's `descr`, `String(error)`) all land in `textContent`. Inlined JSON is escaped against `</script`. The XSS tests cover labels, the nav and errcount labels, but not the error-banner or apply-result paths, which are safe by reading.
- **No lint rule enforces the no-`innerHTML` rule** (no `no-restricted-properties` in `eslint.config.js`). It is enforced by review only.
- **Selector injection (robustness only)**: `querySelector(`[data-field-key="${field.key}"]`)` interpolates without `CSS.escape` (`render.js:78,88,111,165,268,296,320,325,329`). Keys come from build-time definitions, not the device.
- **CSRF [I]**: a cross-origin PUT with `application/json` needs a CORS preflight, and the server sends no ACAO headers. Microdot's `request.json` returns None unless the Content-Type is `application/json` (`ext/microdot.py:464-474`), so the body becomes the ERR envelope. Classic CSRF is therefore blocked structurally.
- **What CSRF blocking does not cover**:
  - **DNS rebinding**: there is no Host-header check.
  - **Clickjacking**: no X-Frame-Options or CSP.
  - **Anyone on the LAN** can `PUT /system {"SystemCmd":"bootloader"}`, which leaves the unit in its USB bootloader until someone physically reflashes it. No auth, by design.
  - Passwords travel over plain HTTP.
- **Password autofill [I]**: masked inputs are `type=password` with no `autocomplete` attribute (`templates.js:160`). A browser password manager may autofill the device's Wi-Fi PW field, and a later Apply on the identity card would send it. Suspicion.

---

#### 5. Audit candidates

##### Bugs and behaviour
1. **A dispatch toggle stays "On" and fires again (suspicion, high) [V]**
   - After Apply, a settings card is not rebuilt (`render.js:321-335`), so the `SGPResetVOC` toggle stays On. Line 252 also moves the baseline to true.
   - The next Apply on the same SGP40 card, for example after changing BackupPeriod, sends `SGPResetVOC:true` again (`dispatch` is always resubmitted, `render.js:81`). That resets the VOC algorithm and deletes its backup again.
   - `ISLCalibrate` on dev behaves the same way.
   - Repeating ResetErrors is tested and intended (`render.test.js:458`), but there it is alone on its card.
2. **Dispatch toggles in the Off position are always sent** (`render.js:81`). Every SGP40, ISL or Status Apply includes `X:false`, gets "X: Valid" in the result text, and can never show "Nothing to submit" [V].
3. **Whitespace in a number field submits 0 [V]**. The field is a text input; `" "` is not `""`, and `Number(" ") === 0` is finite (`render.js:23-30`; the composite path at `render.js:101-102` has the same problem). Hex (`0x10`) and `1e3` are also accepted client-side. A decimal comma (`1,5`) is sent as a string and rejected as Invalid.
4. **Per-field status colours go stale [V]**. `applyResultStyling` only sets fields that are in the current results (`render.js:164-169`). A field marked Invalid on the first Apply stays red after a second Apply that did not include it.
5. **The body read has no timeout (suspicion) [V]**. `fetchWithTimeout` clears its timer once headers arrive (`poll-manager.js:32-34`). `response.text()` (`poll-manager.js:63`) then has no bound, so a link that dies mid-body can block the global single-flight queue for every section.
6. **Client and server timeouts race [I]**. The client's 15000 ms starts before connect; the server's `outer_cap_s` 15.0 starts at accept. So the client almost always aborts first, which undercuts H.4's stated reason ("surface the server's own abort").
7. **Stopping a section does not cancel its requests [V]**. `startPolling`'s stop and section switches never abort in-flight or queued requests (`poll-manager.js:126-131`; there is no AbortController tied to the section). Fast navigation queues stale GETs of up to 15 s each ahead of the new section's first paint.
8. **Polling continues in hidden tabs** (no `visibilitychange` handling). On a board that saturates at roughly 2.2 requests/s with `max_connections` 6, background tabs polling `/status` every 3 s take real capacity [I].
9. **Errcount rebuild on every tick** (`render.js:305`). Keyboard focus on "Show flagged/all" is lost every 3 s. The restore logic re-dispatches synthetic clicks.
10. **In-place caption refresh bypasses `resolveFieldValue`** (`render.js:327,331` use `groupValues[field.key]`). A field with `path` or `defaultValue` in a writable group would show "—" after the first poll. This is latent: no such field exists in wozi or dev today [V].
11. **The baseline snapshot is frozen at first render** (`render.js:336` passes `groupValues` into a closure that is never refreshed). Enum/toggle "unchanged" detection ignores later GETs. This matches H.3's "full remount" rule, but worth checking.
12. **A degraded `/status` source is not surfaced.** When a source fails, the server writes `{"error":"unavailable"}` (`asy_webserver_service.py:~612`). The UI renders every field in that group as "—" with no signal [V].
13. **An Apply with no `rest.put` silently does nothing** (`render.js:197-199`), and `validateDefinitions` does not require `put` when `submit:true`.
14. **Errcount rollup and row disagree.** The rollup and "Show flagged" use the history type (E/W) while the row colour uses `counter > 0` (`templates.js:243-249` vs `283`). They can disagree. Worth checking.
15. **`console.error("Poll failed:")` is effectively dead in production.** `fetchOnce` catches everything (`render.js:350-375`), yet H.8 cites that log line as the loop's only failure diagnostic.

##### Mock-server divergences from src/ (Part G.2 mirror obligation)
16. **The WiFi UTF-8 byte bound is not mirrored** (C.7.4) [V].
17. **Unknown key in a `/sensors` sub-object**:
    - Real server: `"Invalid"` plus an errno=10 log (`config_manager.py:318-321`).
    - Mock: silently ignores it (`mock-server.js:130-131`), and its comment claims this "matches ConfigManager's own convention", which is false [V].
18. **The `partial-result` failure injection simulates a server gap that has been fixed** [V]:
    - Real server: `_apply_settings_groups` now reports every attempted field as `"Failed"` (`asy_webserver_service.py:463-469`), as H.6 says.
    - JS comments still describe it as a live gap: `render.js:133-135`, `mock-server.js:252-254`, `dropOneResultForPartialFailure`.
    - `reconcileResults` is still useful: it catches a group-key mismatch on `/sensors`. It just needs a new stated rationale.
19. **A malformed or non-object PUT body behaves differently**:
    - Real server: ERR envelope (`_body_as_dict`).
    - Mock: `JSON.parse` throws out of `fetch`, and a string body is iterated character by character (`mock-server.js:375,383`).
    - The mock also ignores the Content-Type gate.
20. **Jitter corrupts the time structs (bug, prototype) [V]**. `jitterInPlace` now recurses (added for ISL29125, `mock-server.js:289-291`). Mock `/status` jitters `status.system.LocalTime`/`UtcTime` (year 2025 ± about 20, month becomes 8.03, and so on), so `gmtimestruct` renders garbage. It also random-walks `BootSignature` and `NtpLastSync` (epochs, ±1% per poll). The stale comment at `mock-server.js:481` still says "flat object". No test covers this.
21. **`/status` PUT is not validated.** The mock does not check `ResetErrors`' type; the real server needs `is True` and returns OK either way, which is consistent. The mock is also missing the real "build" handling on PUT; harmless.

##### Build
22. **The claimed bundle-order check does not exist [V]**. H.2 says `build_website.sh` "re-checks that mechanically on every build". There is no check in the script or its test. The order is also **violated**: `templates.js` imports `resolveFieldValue` from `definitions.js` but is concatenated before it (`build_website.sh:78`). Function hoisting keeps this harmless today.
23. **Import stripping is fragile.** The single-line `grep` means a multi-line import survives into the bundle, and a duplicate `export` name across files would be a SyntaxError. Only the live-twin tests would catch either, and those **skip and pass silently** when the toolchain is absent (`live-backend.test.js:13-16`).
24. **The staging test is too weak.** `test_every_real_js_and_html_file_is_accounted_for…` (`tests_scripts/test_build_website_sh.py:117-133`) passes when a filename appears only in a comment; `mock-server.js` passes that way. Its comment at lines 26-29 cites a "Bundling" comment that the sweep removed.
25. **CI path filter gap (worth checking)**. The web filter (`ci.yml:43-58`) excludes `src/**`, `buildgen/**` and `devices/**`. Yet the live PUT matrix and live smoke tests exercise src/ validation, and generated definitions come from buildgen, so a src/ validation change never re-runs the web tier.

##### Accessibility, CSS and mobile
26. **Duplicate DOM ids [V]**: `field-${key}` is not namespaced by group. dev's sensors section has `field-SampleInterv` and `field-FiltCoeff` twice (BMP3XX and ISL29125), so clicking the ISL label focuses the BMP control. Any multi-instance device duplicates every id.
27. **Dangling label targets**: readonly fields and composite grids get `label htmlFor` pointing at an id that does not exist (`templates.js:61,71-78,135-138`).
28. **The off-canvas drawer is not `inert` or `visibility:hidden` when closed**, so Tab reaches invisible links. There is also no focus move or focus return on open/close, no `aria-controls`, and the `aria-label` stays "Open navigation" in both states.
29. **Colour-only error information**: errcount history uses colour only for N/E/W (by design, H.6), which fails WCAG 1.4.1.
30. **Light-mode contrast below 4.5:1 [V, computed]**:

    | Element | Ratio |
    |---|---|
    | Success pill | 3.13 |
    | Danger pill and error banner | 3.74 |
    | Warn pill | 4.01 |
    | Danger rollup text | 4.38 |
    | Input and card borders against the surface | about 1.39 (below 3:1 for non-text UI) |

    Dark mode passes.
31. **Password inputs are unstyled [V]**: `.field input[type=password]` is missing from the selector (`style.css:261-263`). They get no width:100% and no dark-mode colours. `color-scheme` is not declared, so native controls stay light in dark mode.
32. **Toggles change both `aria-pressed` and their visible label** (an anti-pattern). Readonly booleans render as "true"/"false".
33. **Minor**:
    - `@media (width >= 640px)` range syntax needs Safari 16.4 or later; it degrades harmlessly.
    - No `prefers-reduced-motion` handling.
    - The hamburger is 36 px.
    - `replaceChildren`, private fields and `??=` need roughly iOS 14.5 or later.

##### Dead code, duplication and stale references
34. `PollManager.isBusy` / `#activeCount` are used only by tests (`poll-manager.js:37-47`).
35. `selectSection` and the startup error-banner logic are duplicated verbatim between `app.js:62-86` and `main.js:62-86`.
36. The `"settings"` and `"none"` pollGroups behave identically.
37. Stale spec pointers:
    - `templates.js:8` cites "H.7's splitting rule"; it is in H.2.
    - `templates.js:340` cites "H.3's 'One deliberate exception' note"; no such note exists.
    - `render.js:127` cites H.3 for severity order; the coloring is described in H.4.
38. `validateDefinitions` is shallow. It checks no field key or kind, no enum options, no composite subFields, `min <= max` or key uniqueness. An unknown kind is silently rendered as a text input (`templates.js:158`), which contradicts H.4's "Strict" claim.

##### Comment-cap violations [V]
39. `html/index.html:40-43` has a 4-line `//` block.
40. Over-cap blocks in the tsconfig files:
    - `tsconfig.json:11-15` (5 lines) and `:29-35` (7 lines).
    - `tsconfig.node.json:2-6` and `:17-21` (5 lines each).
    - The tsconfig files are **not in CLAUDE.md's list of swept config files**, so it is unclear whether the cap applies to them.

    All other js/, CSS and JSDoc blocks are within 3 lines.

##### Test gaps
41. The live PUT matrix covers **wozi only** (`live-backend-put-matrix.test.js:58`). dev-only ISL29125 fields are PUT-tested against the mock only.
42. The live tests skip and pass without the toolchain.
43. No runtime HTML or a11y validation of the generated DOM: html-validate sees only the static skeleton, so it catches neither the duplicate ids nor the dangling labels.
44. No tests for: the stale field status across two Applies, the whitespace-to-0 input, the mock time-struct jitter, the sticky dispatch toggle combined with a second Apply, or a hung body read.
45. `definitions-mockdata-coverage` checks readonly fields only.

---

#### 6. Suggested audit topics

- [ ] Should `dispatch` toggles reset to Off after a successful Apply, or move to their own cards? (items 1–2)
- [ ] Should number input parsing trim whitespace, reject `0x`/`1e`, and handle a locale decimal comma? (item 3)
- [ ] Should the timeout cover body reading, and should it sit just above the server's 15 s so the server's own abort wins the race? (items 5–6)
- [ ] Should a section's requests be aborted on switch, and polling paused on `visibilitychange`? (items 7–8)
- [ ] Mock/src parity:
  - [ ] Byte bounds.
  - [ ] The unknown-key result.
  - [ ] Removing or re-scoping `partial-result`.
  - [ ] The malformed-body envelope.
  - [ ] Recursive jitter that should exclude time structs.
  - [ ] String special values in the generator.

  (items 16–20, section 3)
- [ ] Retire the hand-written wozi/dev definitions, or add an *ordered* equality check (field order drift).
- [ ] Make the bundle robust: a mechanical order and duplicate-export check, a real import strip, and fixing H.2's false claim. (items 22–24)
- [ ] Add `src/**`, `buildgen/**` and `devices/**` to the web CI path filter. (item 25)
- [ ] Accessibility: namespaced ids, inert drawer, focus management, contrast tokens, styling `password`, `color-scheme`, and an axe-style runtime check. (items 26–33)
- [ ] Surface `{"error":"unavailable"}` status degradation, and decide whether to show firmware version and build date (L.7 says no; H.1 says full REST coverage). (item 12)
- [ ] Security posture: document or accept the LAN-wide `bootloader`/`reboot`, DNS rebinding and clickjacking exposure; set `autocomplete` on password fields; add an ESLint rule banning `innerHTML`.
- [ ] Caching: is re-downloading on every visit intended? Weigh a short `max-age` against stale-after-reflash.
- [ ] Tighten `validateDefinitions` to match H.4's "strict" claim (kinds, keys, `put` required when `submit`, options). (items 13, 38)
- [ ] Clean up the dead `isBusy`, the duplicated `app.js`/`main.js` code, and the stale spec pointers and comments. (items 34–37)
- [ ] Decide whether the comment cap applies to the tsconfig files, and fix `index.html:40`. (items 39–40)
- [ ] Add a live PUT matrix for dev (ISL29125), and make CI fail when the live tests skip. (items 41–42)

---

## Documentation set

### Documentation-set audit survey (read-only), /home/user/sensors

**Method.** I read the headings and front matter of every doc and inspected the regions that looked problematic. I also ran scripts, kept in my scratchpad and not in the repo, over every git-tracked file outside `python/`, `modules/` and `arduino/`. They:
- resolved every "Part X.Y" and bare section ID against SPECIFICATION.md's headings, ignoring fenced code;
- resolved BACKLOG item numbers, test-queue row IDs and HEAP_FRAGMENTATION "archive §" citations (the archive being `git show 12640c2:HEAP_FRAGMENTATION_MEASUREMENTS.md`);
- checked quoted section names and file paths mentioned in the docs.

Each finding below is marked **VERIFIED** (checked directly) or **SUSPICION** (inferred, or needs a judgement call). Nothing was modified.

Sizes (lines / bytes): SPECIFICATION 6781 / 526 KB · tests_hardware/README 1414 / 115 KB · CLAUDE 1067 / 92 KB · digital_twin/README 919 / 73 KB · BACKLOG 874 / 77 KB · README 785 / 53 KB · dev_legacy/README 678 / 37 KB · HEAP_FRAG 393 / 30 KB · QUEUE 388 / 40 KB · UART changelog 128 / 34 KB. The whole set is about 1.1 MB.

---

#### 1. SPECIFICATION.md structure map

The table of contents (lines 11-27) lists Parts only, with no section index. For a 6.8k-line file that is a navigation weakness.

- **Part A, Repository & Architecture (l.29-687).** A.1 layout · A.2 architecture at a glance · A.3 refactor status · A.4 deep module reference · A.5 Microdot/REST guarantees · A.6 datasheets · A.7 wozi construction order, FRAM chunk order, dependency graph · A.8 REST endpoint reference · A.9 frozen-HTML pipeline · A.10 digital twin.
- **Part B, Toolchain & Build (l.688-1474).**
  - B.1-B.9: installer rationale, quick start, how it works, isolation, layout, verification, evidence (B.7.1 GCC ≥ 14 mbedtls workaround), why no venv, "not yet covered".
  - B.10 CI jobs, with B.10.1 per-job rationale.
  - B.11 firmware build · B.12 `env` tiers · B.13 bench network dead-man's switch.
  - B.14 MicroPython build-override framework: B.14.1 kbd_intr, B.14.2 lwIP counts, B.14.2.1, and B.14.3, which is documented but not implemented.
  - B.15 the three mypy passes.
- **Part C, Sensor-driver architecture (l.1475-2575).** Layering, naming, protocol class (C.3.1 SPI, C.3.2 UART), Reader layer (C.4.x), config schema/setters/response envelope (C.5.x including two `####` subsections), data model, error/logging contract (C.7.1-C.7.4), concurrency/locking (C.8), timer/IRQ contract (C.9, C.9.1), typing, new-driver decisions (C.11, C.11.1), testing, readiness gate, instance naming/wiring/fan-in (C.14.x).
- **Part D, `src/` quality checklist (l.2576-2731).** D.0-D.16.
- **Part E, Testing & coverage (l.2732-3421).** Why not pytest, framework, per-device scenario libraries, running (E.3.1 heap and timeouts), mock boundary, coverage (E.5.1-E.5.3), real-hardware model (E.6.1-E.6.6), soak wall clock, measurement traps, driver/DUT process separation.
- **Part F, Platform & MicroPython runtime facts (l.3422-4125).** F.1 core facts · F.2 blocking/backstops · F.3 long-blocking · F.4 vendor policies · F.5 1.29 delta (F.5.1-F.5.9) · F.6 SIGINT heap wedge.
- **Part G, Shared primitives (l.4126-4255).** Rule, catalog, re-validation.
- **Part H, Website (l.4256-4759).** Constraints, module map, layering, decisions, definitions schema (H.5.1 autogeneration), errcount conventions, twin integration (H.7, which also holds the lwIP connection ceiling and cross-browser coverage; H.7.1), CI/tooling (H.8.1).
- **Part I, Memory safety (l.4760-5143).** Research, hotspot catalog, bounded response assembly, the (a)-(g) ladder (I.4), real-hardware confirmation. I.6 is physically located inside Part J; see below.
- **Part J, UART protocol (l.5144-5678).** Scope/contract, roles, frame format, transactions, timing/recovery, parameters, loopback testing, memory, module contract.
- **Part K, New-module checklist (l.5679-5980).** K.1-K.11.
- **Part L, Build chain (l.5981-6567).** Variants/acceptance, design decisions, TOML schema, generator pipeline, script quality bar, wiring defaults/tags/pin legality (L.6.1-L.6.6), versioning.
- **Part M, Chip reference (l.6568-end).** ISL29125 only (M.1.1-M.1.6).

**Structural anomalies (all VERIFIED):**
1. **`## I.6` sits inside Part J** (SPECIFICATION.md:5161). It comes after Part J's intro (5144-5159) and before J.1 (5292). Its content (request-body cap, Microdot `max_content_length`/`max_body_length`, the connection-slot release lag) belongs in Part I or H/A.5. It is cited from about 20 places, so moving it means re-pointing none of them, only relocating.
2. **Wrong heading levels.** `## E.2.1` (2796) and `## H.5.1` (4406) should be `###`.
3. **Unnumbered subsections in H.7.** `### The connection ceiling…` (4526) and `### Cross-browser coverage` (4660, which sits after H.7.1). As a result "H.7" is cited for lwIP/connection-limit facts under a Part titled "Digital twin integration".
4. **F.5 is titled "MicroPython 1.29 delta (audited 2026-09-10)"** but F.5.7-F.5.9 are standing UART runtime facts that CLAUDE.md's hard rules depend on. They are not version-delta material and would be orphaned when the next version audit replaces F.5. It is the largest section (382 lines).
5. **Other sections holding history or dated measurement narrative.** I.6 carries "Fixed in the test, 2026-09-19" (SPECIFICATION.md:5279). E.3.1 (2868-2922) is an explicit heap-size history.
6. **Test-queue numbering.** The queue's sections run 0, 1, 1A, 1C, 1F, 2, 2A, 3, 4, 4A, 5, 6, with no 1B/1D/1E (REAL_HARDWARE_TEST_QUEUE.md headings). Minor.

---

#### 2. Cross-reference integrity

**SPECIFICATION "Part X.Y" references: clean (VERIFIED).** 1,318 "Part X.Y" citations across code and docs all resolve to an existing heading, as do bare `(X.Y)` and `SPECIFICATION X.Y` forms. Letter sub-labels also resolve:
- I.4(a)-(g) and (f.1) exist.
- E.6.6 "fourth item", A.7 "step 13b" and C.11 "point 9" exist.

A keyword spot-check of about 40 citations found the right content. The one weak one is L.6.4 (see 4.9).

**One ID collision (VERIFIED).** `tests/test_asy_webserver_service.py:194` cites "F.1" and "F.6/F.7". These are finding IDs from some retired audit, not SPEC Parts. SPEC has no F.7, and F.6 is the SIGINT gc wedge, so they mis-resolve. More generally, queue row IDs (F1, F17, T1 "(T.1)", C7), archive § IDs and SPEC Part IDs share one visual namespace.

**BACKLOG numbers.**
- *Resolve correctly (VERIFIED):* 1, 3, 5, 6, 8, 9, 12, 24, 29, 30, 32, 41, 44.
- *BACKLOG.md:15-18* says the closed stubs are "items 1, 5, 6, 9, 12 today", but item 29 (l.303) is also a closed stub. The sentence is stale (VERIFIED).
- *Items 2 and 4* (l.177, 190) are "Decided" and nothing cites them. By BACKLOG's own policy they should have been migrated or deleted (VERIFIED: no citations found).
- *Item 8* is SETTLED ("permanently [MANUAL]"). Yet `tests_hardware/flash/test_bus_concurrency.py:122` quotes it as "not currently provisioned", and that phrase now exists only in README.md:776 (VERIFIED).

**Named BACKLOG/CLAUDE entries that no longer exist (all VERIFIED):**
- `tests/machine.py:2`: BACKLOG "Timer mypy resolution" (no entry by that name; loosely BACKLOG ~l.672).
- `tests/test_captive_dns.py:230`: BACKLOG "root-domain query can't be told apart from a failed parse" (absent).
- `src/asy_notification_service.py:69`: CLAUDE.md "Current architecture" (no such section).
- `tests/test_asy_wifi_service.py:1791`: CLAUDE.md "physical intervention as the accepted backstop" (absent).
- `scripts/_strip_type_checking.py:13` and `tests_scripts/test_strip_type_checking.py:51`: "BACKLOG.md's (original) prototype note" (absent).
- `scripts/lint.sh:17`: BACKLOG for the legacy scripts' "28 findings … no shebang" (absent).
- `src/asy_neopixel_driver.py:3` and `src/asy_notification_service.py:3`: "see CLAUDE.md/BACKLOG.md" for the neopixel_signal promotion (no such content).
- `tests_hardware/bench/test_network_resilience.py:3`: "DHCP-client flakiness … out of scope (see BACKLOG.md)" (no DHCP entry in BACKLOG).
- `dev_legacy/README.md:624`: BACKLOG's "per-variant sensortask-*.py generator" item (gone).
- `BACKLOG.md:817`: README.md's "Toolchain setup" section (no such README heading).
- `tests_hardware/flash/test_toolchain_flash_boot.py:14,25,46`: "Item 19/20/23" (numbering from a deleted plan doc).
- `tests_hardware/bench/test_heap_under_connection_ceiling.py:161`: "Row 5 of the decision table … §5" (source document unidentifiable).

**Queue row IDs cited but not present in REAL_HARDWARE_TEST_QUEUE.md (VERIFIED).** The queue deletes rows once they are done, so these danglers are structural:
- C7: BACKLOG.md:249
- R10: BACKLOG.md:661
- F11: SPECIFICATION.md:5279 ("§2A F11"), tests_hardware/http_client.py:48
- F7: uart_link_under_concurrent_system_load.py:109
- F10: test_network_resilience.py:877
- F13: test_wifi_networking.py:32
- G9: test_rest_endpoints_over_sta.py:35, website_identity.py:2

Permanent code comments citing a temporary doc's row IDs will keep producing danglers.

**Archive § citations.** All of about 77 resolve against commit `12640c2` (VERIFIED). **SUSPICION (fragility):** that commit is reachable only from `origin/claude/automated-build-chain-nuzumw`. There is no main branch locally, so I could not check whether main contains it. If the PR is squash-merged and the branch deleted, every "archive §" citation loses its target.

**Front-matter pointers (VERIFIED).** README.md:783-784 ("see SPECIFICATION.md's own front matter for the full provenance") and README.md:652-653 ("see its front matter for the tradeoff … no longer auto-loaded") both point to text that is not in SPECIFICATION.md:1-9.

**Pointers inside CLAUDE.md (VERIFIED):**
- CLAUDE.md:893-894 says to see "Platform target" above for Ubuntu `universe`. That section has no such content; it is SPECIFICATION B.2, l.734.
- CLAUDE.md:647 refers to "the `_timer_sequencer()` Timer-GC fix above". Nothing above describes it.

---

#### 3. History, duplication, stale claims, contradictions

##### 3a. History and narrative that runs against the "current state, not history" rule
- **tests_hardware/README.md:686-1379** (about 700 lines, half the file): "Third pass" … "Tenth pass" audit-pass sections. There are no first or second passes, and "Known assumptions and open findings" (l.407-685, 279 lines) holds open items. VERIFIED.
- **README.md:673-684 and 763-784**: provenance narrative about deleted docs (DRIVER_SPEC.md, HARDWARE_TEST_PLAN.md and seven others). This sits in the very paragraph that says such material was "dropped as process narrative". VERIFIED.
- **CLAUDE.md**:
  - `improved-quality/` retirement history appears at l.53-67, 114, 190, 739, 769 and 855-858. l.855 is purely "no longer exists".
  - Six "Known … cause, fixed" incident bullets (l.613-708, about 100 lines).
  - The uv.lock merge incident (l.791-804).
  - "396MB" `test_tmp_scratch` story (l.270-283).
  - "archive §11 item 0, now decided and done" (l.576).
- **BACKLOG.md**:
  - First "Refactor targets" bullet (l.23-56): full fix narrative.
  - Item 30: "An earlier version of this item said…" (l.330).
  - l.748: "Corrects a stale claim (this entry used to say…)".
  - Several SETTLED entries with "Original framing" (l.416).
  - "FRAM `verify_present()` … SETTLED, do not re-raise" is filed under "Refactor targets not yet done" (l.58).
- **SPECIFICATION.md**:
  - A.3 "Originally prototyped as hand-written `src/sensortask_wozi.py`" (l.137), and a similar note at l.360.
  - E.3.1 heap-size history.
  - 118 dated `2026-0x-xx` stamps and about 41 "originally/previously/at the time"-style markers (counted by grep).
- **Undefined process labels (VERIFIED).** WP1-WP8 appear in 39 files and are defined nowhere. "Measure A/B" (SPECIFICATION.md:4882, 5111; handover l.21), "image E6′" and "S3" are defined only in the git archive.

##### 3b. Stale claims (VERIFIED unless marked)
- **"86/86" MicroPython files** (CLAUDE.md:350; HARDWARE_TEST_HANDOVER.md:20) and "85 times" (SPECIFICATION.md:2917). There are now **87** `tests/test_*.py`: `test_fake_timer_and_network.py` was added 2026-09-25 in commit 5936169.
- **CLAUDE.md:773** says "~157" `method-assign` ignore sites. The count is now 209 in tests/digital_twin (grep for `ignore[…method-assign`).
- **CLAUDE.md:725** names `test_digital_twin_webserver_concurrency.py`, which is now split into six per-device files.
- **SPECIFICATION.md:338-340 (A.6)** lists the datasheets as bmp3xx/fram/pico w/scd30/sgp40. `datasheets/isl29125/` exists; A.1 l.35 lists it correctly.
- **SPECIFICATION.md B.9 (821-826)** claims `build-*.sh` still has hardcoded `/home/nico/rpi_pico/...` paths and that "the remaining gap is the RP2040 firmware build". `build-wozi.sh:1-3` now uses `$(pwd)`, BACKLOG.md:817 says this is fixed, and B.11 plus the `firmware-build-verify` CI job exist.
- **C.11 (SPECIFICATION.md:2319, 2325)** says SGP40's backup is the "only" FRAM persistence example and that there are "existing three" chip fakes. There are four sensor fakes plus FRAM. C.4.1 "identical across all three drivers" (1630) predates ISL29125 (SUSPICION that ISL29125 conforms or diverges; not checked).
- **L.6.4 (SPECIFICATION.md:6491-6495)** says `asy_bmp3xx_driver.py` is "the only driver with a real `_LIMITS` constraint". `src/asy_isl29125_driver.py:194` also has `# @limits trigger_sec 1..3600`.
- **dev_legacy/README.md:19-20** says the board runs MicroPython 1.28.0 "matching `toolchain/versions.toml`". The pin is `v1.29.0`. l.595, "Current bench state (as of 2026-09-02)", predates the 2026-09-24 image described in the handover and queue. l.627-628 says "no per-variant `sensortask-*.py` exists yet".
- **README.md:774-776** says the "two still-genuinely-open items … tracked in BACKLOG". Item 8 is now SETTLED as permanently manual.
- **Terminology.** SPECIFICATION.md:6-7 and README.md:650 still describe CLAUDE.md as containing "pre-push verification". The chroot check became non-blocking and owner-run on 2026-09-18.

##### 3c. Contradictions between or within docs (VERIFIED)
- **Website definitions files.**
  - H.5 (SPECIFICATION.md:4401-4402) and `scripts/build_website.sh:26-30` say wozi/dev keep **hand-written** `html/definitions/*.json`, used as tests_js fixtures.
  - K.4 (5781-5782) says it is "generated at build time … never hand-maintained", and K.8 (5895) says it "regenerates automatically".
  - C.11 point 9 (2331) says to hand-update it.
- **ISL29125 calibration.** THIRD_PARTY_LICENSES.md:52-53 credits "FRAM-persisted gain-ratio self-calibration". M.1.5 and `src/asy_isl29125_driver.py:262` say calibration is RAM-only and user-applied.
- **Duplicate licence entry.** THIRD_PARTY_LICENSES.md has two separate `src/asy_isl29125_driver.py` entries (l.34-39 and l.46-53). l.37 also says the legacy copy is "listed under 'Shipped but not promoted' below", while l.118-120 says it "used to be listed here … entry moved up".
- **Where resolved BACKLOG items go.** Four versions disagree:
  - BACKLOG.md:5-7: CLAUDE.md or README.md.
  - README.md:656-657: "this file [README] or CLAUDE.md".
  - CLAUDE.md:406-410: CLAUDE.md/README.md.
  - QUEUE:5 and actual practice: mostly SPECIFICATION.md.
- **Coverage gating.** README.md:189 says `--coverage` "never fails the build", while README.md:183-185 and CLAUDE/E.5.3 say its *test result gates*.
- **Chroot recipe (CLAUDE.md internal).** l.1026-1028 says the recipe "only exercises lint.sh/typecheck.sh, never the toolchain installer", but the recipe's own l.968-971 runs `scripts/test.sh` "to exercise toolchain/versions.toml's apt_packages list end-to-end". The libcap2-bin explanation is duplicated within the same code block (l.936-939 and 947-953).
- **FRAM log list.** CLAUDE.md:367-376 enumerates the FRAM-backed loggers but omits ISL29125. On dev it is `fram_target = "fram"` (devices/dev.toml:109-110), and SPEC A.7 (l.477) includes its chunk.
- **Implicit-FRAM-wiring rule.** SPECIFICATION.md:376 and 396 cite "CLAUDE.md's implicit-FRAM-wiring rule", but CLAUDE.md only mentions it in passing (l.370). The rule itself is stated nowhere as a rule.
- **Uptime.** SPEC A.2 (l.123) says "Units run years unattended"; CLAUDE.md boot-latency rule says "months between reboots". Minor.
- **Legacy tree.** SPEC A.3 (l.132) calls the legacy `python/`+`build-*.sh` pipeline "still-uncovered … BACKLOG.md", framing it as a gap. CLAUDE.md:170-183 says the gap is the decision and must not be proposed for closing.
- **Licence coverage.** THIRD_PARTY_LICENSES is billed in README.md:726-731 as "every piece of vendored … third-party code in one place", but it does not mention `arduino/` (Adafruit_BusIO, Adafruit_FRAM_SPI, bsec2, BME68x and others). The scope exclusion (BACKLOG.md:406-408) explains why, but the README claim is too broad.

##### 3d. Duplicated facts likely to drift
- **The same bench state appears in two temporary docs.** Image E6′, `buildDate 2026-09-24T06:45:32Z` and "limit of 6" are in REAL_HARDWARE_TEST_QUEUE.md:46-48 and HARDWARE_TEST_HANDOVER.md:17-18. The two also have different "one sitting only" running orders (queue l.44-58 vs handover l.95).
- **Timer stub gap** is in both CLAUDE.md:821-840 and BACKLOG.md:668-679.
- **Memory-safety ladder** is in CLAUDE.md:307-366 (60 lines) and SPEC I.4.
- **CI job semantics** are in CLAUDE.md:478-490 and 601-612 and in SPEC B.10.
- **Real-hardware go-ahead / flag facts** are in CLAUDE, README, tests_hardware/README, QUEUE and HANDOVER.
- **CLAUDE.md holds facts found nowhere else** (grep counts): the nested `asyncio.run()` segfault, the `select.poll()` hang, `SO_REUSEADDR` port overlap, uv.lock specifier drift, the E402 rule, the `method-assign` rationale. This contradicts SPEC's front matter, which defines CLAUDE.md as operating constraints only.
- **Open or deferred work is spread over at least six places:**
  - BACKLOG;
  - the QUEUE;
  - tests_hardware/README "Known assumptions and open findings" plus the pass sections (BACKLOG.md:106-117 defers to "Tenth pass" rather than listing the items);
  - digital_twin/README "Known gaps / follow-ups";
  - SPEC B.9 and B.14.3;
  - dev_legacy/README:659-663, a "Still open" router DHCP-reservation item that is not in BACKLOG.
- **Map gap.** `update_and_install.txt` is absent from README's "Further reading", which is declared to be the single complete map. It appears only in SPEC A.1 l.88.
- **Temporary file that cannot expire.** UART_C_PORT_CHANGELOG is "Temporary. Delete once reconciled", but reconciliation is ruled out of scope (BACKLOG.md:406). SUSPICION: it is de facto permanent.

---

#### 4. Size and readability, CLAUDE.md in particular

These estimates come from per-bullet line counts. The classification is my inference.

CLAUDE.md, about 92 KB (roughly 23k tokens) loaded every session:

| Section | Lines | Size | Share |
|---|---|---|---|
| Hard rules | 345 | 32 KB | ~35% |
| Code-quality tooling | 393 | 36 KB | ~39% |
| Build-env recipe | 177 | 12 KB | ~13% |
| Working agreements | 70 | 6 KB | |
| Everything else | small | | |

Rough split of content:
- **Imperative rules: about 35-40%.** Hard-rule headlines, bus-hazard/wear/go-ahead gates, comment cap, PR workflow.
- **Rationale and platform/tooling facts: about 40%.** Stub defects, mypy scopes, CI shape, coverage binaries.
- **Incident narrative and history: about 20%.** "Known … fixed" bullets, improved-quality retirement, "found the hard way" accounts, dated counts.

The largest single bullets:
- memory-safety: 60 lines
- UART contract: 37
- FRAM-log forensics: 37
- comment cap: 37
- wear rule: 35
- "Scope is eight directories": 31
- coverage: 30
- known-hang #2: 28

The chroot recipe (12 KB, a runnable bash block) is auto-loaded, yet sessions can usually not run it (owner decision 2026-09-18). It is a candidate to relocate to SPEC B with a pointer.

Other docs:
- SPECIFICATION: the 10 largest sections are 150-382 lines each.
- tests_hardware/README is 115 KB, about half of it pass history.
- BACKLOG's numbered list is interleaved with unnumbered bullets under "Open questions", and several items run 30-50 lines.

---

#### 5. Audit candidates (file:line)

**Verified**
1. SPECIFICATION.md:5161: I.6 placed inside Part J.
2. SPECIFICATION.md:2796, 4406: `##` where `###` is needed. SPECIFICATION.md:4526, 4660: unnumbered subsections.
3. SPECIFICATION.md:3664, 3877-4045: standing UART facts filed under the "1.29 delta".
4. SPECIFICATION.md:4401 vs 5781, 5895 vs 2331: hand-written vs generated `html/definitions`.
5. SPECIFICATION.md:821-826 (B.9): stale.
6. SPECIFICATION.md:338-340 (A.6): omits isl29125.
7. SPECIFICATION.md:2319, 2325, 1630: "only", "three" counts.
8. SPECIFICATION.md:6491-6495: `_LIMITS` "only driver" is stale.
9. CLAUDE.md:350, HARDWARE_TEST_HANDOVER.md:20, SPECIFICATION.md:2917: 86/85 vs 87 test files.
10. CLAUDE.md:773: ~157 vs 209.
11. CLAUDE.md:725: stale test filename.
12. CLAUDE.md:367-376: ISL29125 missing from the FRAM-log list.
13. CLAUDE.md:647, 893-894: dangling "above" pointers.
14. CLAUDE.md:1026-1028 vs 968-971: recipe self-contradiction. CLAUDE.md:936-953: duplicate paragraph.
15. README.md:652-653, 783-784: dangling front-matter pointers. README.md:774-776: stale. README.md:189 vs 183-185: coverage gating.
16. BACKLOG.md:15-18: stub list omits 29. BACKLOG.md:177, 190: uncited decided items. BACKLOG.md:249 (C7), 661 (R10): dangling queue rows. BACKLOG.md:817: nonexistent README section.
17. BACKLOG.md:5-7, README.md:656-657, CLAUDE.md:406-410: conflicting migration targets.
18. THIRD_PARTY_LICENSES.md:34-53: duplicate ISL29125 entry, wrong "FRAM-persisted calibration", l.37 vs l.118 contradiction.
19. dev_legacy/README.md:19-20, 595, 624-628: stale version, state and BACKLOG pointer.
20. Dangling code-comment citations: tests/machine.py:2; tests/test_captive_dns.py:230; src/asy_notification_service.py:69; tests/test_asy_wifi_service.py:1791; scripts/_strip_type_checking.py:13; scripts/lint.sh:17; src/asy_neopixel_driver.py:3; tests_hardware/bench/test_network_resilience.py:3; tests_hardware/flash/test_toolchain_flash_boot.py:14/25/46; tests_hardware/bench/test_heap_under_connection_ceiling.py:161; tests/test_asy_webserver_service.py:194 (F.6/F.7 collision); tests_hardware/flash/test_bus_concurrency.py:122.
21. Queue row IDs cited but deleted: F7, F10, F11 (also SPECIFICATION.md:5279), F13, G9 (see section 2).
22. WP1-WP8, "measure A/B", "E6′" and "S3" are undefined in the living docs (39 files use WP labels).

**Suspicion / worth checking**
23. The archive citations (about 77) depend on commit 12640c2, which is reachable only from the feature branch.
24. UART_C_PORT_CHANGELOG is "temporary" but has no reachable deletion trigger.
25. tests_hardware/README.md:686-1379: whether the pass sections should be condensed into current-state facts plus BACKLOG items.
26. CLAUDE.md:821-840: the "12 call-overload errors … (4)/(3)/(2)" per-file counts are unverified and drift-prone. BACKLOG's explicit-`Any` counts (107/213, dated 2026-09-11) look likely to have drifted; a naive word count now gives 140/504, which is not a like-for-like measure.
27. HARDWARE_TEST_HANDOVER.md:3: "PR #58" vs PR numbers #83/#84/#105 elsewhere. Could not check on GitHub.
28. SPECIFICATION.md:3668-3671 and REAL_HARDWARE_TEST_QUEUE.md:73: dated suite counts (flash "25 passed" vs 51 tests now). The 85/51 counts in the queue match a `def test_` count.
29. README.md Further reading: omits `update_and_install.txt`.
30. Whether CLAUDE.md's unique facts (the "Known … fixed" bullets, uv.lock, E402, method-assign) belong in SPEC E/B with one-line pointers.

---

#### 6. Suggested documentation-audit topics and questions
1. **Placement:** is every SPEC section in the right Part? (I.6, H.7's lwIP ceiling, F.5's standing facts, A.2 FRAM usage.)
2. **Heading hygiene:** consistent levels, every subsection numbered, a section-level table of contents.
3. **Reference policy:** should permanent code cite temporary docs (queue rows, handover, BACKLOG by name) at all? What prevents dangling IDs once rows are deleted? Should there be a CI lint for Part/BACKLOG/row/§ references? (All Part refs resolve today; the others do not.)
4. **Archive durability:** will 12640c2 survive the merge strategy? Should the archive be a tag?
5. **Single home for open work:** consolidate the six-plus locations into BACKLOG and QUEUE.
6. **The history rule, applied to** tests_hardware/README's pass sections, README's deleted-doc provenance, CLAUDE's incident bullets and improved-quality notes, and BACKLOG narrative inside items.
7. **CLAUDE.md budget:** what must be auto-loaded (rules) versus moved to SPEC (facts, incidents, the chroot recipe)? Set a size target.
8. **Numbers with dates:** inventory every count or date claim (86/86, ~157, 21 chunks, 25/85 passes, file counts) and decide whether to keep it or make it generated or tested.
9. **Cross-doc contradiction sweep:** definitions JSON, migration target, coverage gating, ISL29125 FRAM persistence, legacy build scripts.
10. **Glossary:** WP1-8, measure A/B, image E6′, sittings, the tiers, the queue's row-ID letters.
11. **Duplication between the temporary docs:** QUEUE vs HANDOVER (board state, running order).
12. **dev_legacy/README:** is it still the "single source of truth" for bench state, or superseded by the QUEUE and handover?
13. **Licence doc:** scope statement vs `arduino/`, duplicate entries, stale attribution claims.
14. **BACKLOG hygiene:** stub list accuracy, uncited decided items, SETTLED items under "not yet done".
15. **Terminology drift:** "pre-push verification" vs owner-run periodic check.

---

## Legacy tree and parity

### Feature-parity map: legacy (`python/`, `modules/`, `html_raw/`) vs refactor (`src/`, `devices/`, buildgen, `js/`+`html/`)

This was a read-only survey. I changed no files and touched no hardware. The only thing I ran was `python3 -m buildgen.generate devices/wozi.toml`, which prints to stdout, to see the generated wiring. Throughout, **[V]** means I read it in source and confirmed it, and **[I]** means I inferred it and did not trace it end to end.

#### 1. Device mapping [V]

| Legacy entry point (build script) | Refactor TOML | Notes |
|---|---|---|
| `modules/sensortask-wozi.py` (`build-wozi.sh`) | `devices/wozi.toml` | SCD30 i2c0 13/12 IRQ 8, SGP40 + BMP3xx i2c1 19/18, FRAM SPI0 2/3/4 CS1, Neopixel 15. Pins match. The refactor adds an i2c0 `timeout=200000`. |
| `sensortask-arzi.py` (`build-arzi.sh`, `html_raw/arzi`) | `devices/arzi.toml` | i2c1 27/26, no BMP. Pins match. |
| `sensortask-neu.py` (`build-neu.sh`, **reuses `html_raw/arzi`**) | `klkizi.toml`, `grkizi.toml`, `schlafzi.toml` | Identical to arzi apart from SPI 18/19/16 and CS 17. The three TOMLs differ only in name and hostname. |
| `sensortask-dev.py` (`build-dev.sh`) | `devices/dev.toml` | Not a parity reference. Legacy dev has SHTC3, MPRLS, ISL29125, no FRAM/Neopixel/WDT (the WDT is commented out). Its `SGP40_Reader(i2c1, sgpCompCallback, trigger_sec=1, …)` call doesn't match the legacy signature. `dev_legacy/` is the real bench snapshot. SHTC3 and MPRLS have no `src/` counterpart, which is out of scope under CLAUDE.md. |

Every legacy unit used one hostname default, `"SensorNode"`. Each refactor TOML injects its own (`SensorStation<Name>`), through `asy_wifi_service.py:48` plus buildgen's `_with_default()`. BACKLOG records this as deliberate.

#### 2. What the deployed system does (legacy summary) [V]

**Boot and supervisor** (`modules/sensortask-wozi.py:76-613`):
- `WDT(8000)` is created at import. `fram.setup()` is the only one-time init.
- Timers are staggered by `timer_sequencer` (1000 ms base), then tasks start 1/n s apart, then there is a first NTP force-sync.
- The supervisor loop runs every **3 s**. Each dead task restarts, adds `+100` to the fail budget and increments `Task_ErrCnt`, and sets `Task_LastErr` to the task's index. The budget decays by 1 per clean pass.
- Once the budget exceeds 300, `all_running=False` for good, so the watchdog is starved into a hard reset with no FRAM pause.
- A failed `fram.setup()` also sets `all_running=False`. **That starves the watchdog forever, so the unit reboot-loops about every 8 s** (`:570-574`, `:605-607`).

**System service** (`python/CommonDrivers/system_service.py`):
- Uptime counter.
- Boot signature: `-1` until set, then the UTC time if NTP is synced, or `getrandbits(32)` after 120 s.
- Reboot and bootloader commands pause FRAM and reset after **5 s**.
- `mempause` pauses FRAM for 300 s (clamped at 3600 s).

**REST API** (Microdot, port 80, `cmd` envelope, `"On"`/`"Off"` strings, `"None"` strings):
- **Pages:** `GET /`, `/index.html`, `/favicon.ico`, `/nettimeconfig.html`, `/sensorconfig.html`, `/systemledconfig.html`, `/style.css`, `/functions.js`.
- **`/net`:** `GET /net/status` returns `IPv4`/`Subnet`/`Gateway`/`DNS`/`Rssi`. `GET /net/config` returns `Country`/`Hostname`/`SSID`/`PW` (masked). `PUT /net/cmd setNetwork` accepts Hostname 1-63, Country 2, SSID 2-32, PW 8-63, and triggers `reconnect_wifi`.
- **`/time`:** `GET /time/status` returns `Synced`/`Unix` plus UTC and Local `{Year..Sec}`. `GET /time/config` and `PUT /time/cmd setTiming` cover `NTP_Host` 3-1024, `NTP_Offset_S` ±43200, `NTP_Interv_H` 1-24, `GMTOffset`/`DSTOffset` ±43200. A setTiming PUT force-syncs.
- **`GET /sensors/status`:** SCD30 `{CO2, Temp, Hum, WetBulb, DewPoint, TS}`, SGP40 `{VOC, Raw, TS}`, BMP388 `{Pres, Temp, SLPres, TS}`.
- **`GET /sensors/config`:** SCD30 values are live readback from its NVM. BMP values are the stored config plus the live oversampling and filter settings.
- **`PUT /sensors/cmd`:**
  - `setSCD`: TempOffs 0-655.35, MeasInt 2-1800, AmbPres 700-1400 or 0 (always resent), Altitude 0-65535, ForceCalRef 400-2000, SelfCal, and ContMeas where `"Off"` stops measurement. Each value is **written only if it differs from the sensor readback**, via `api_helpers.py:192`.
  - `setSGP`: BackupPeriod 0-1440 min, MaxAge 0-10080 min, WaitNTP 0-600 s, ResetVOC.
  - `setBMP`: SampleInterv 1-3600 s. Oversampling and filter settings are sent as an index (0-5 and 0-7) and weighted to `2**x` or `2**x-1`. Offsets and sea-level parameters are floats.
- **LED:** `GET /led/status` returns `pauseTime`. `GET /led/config`. `PUT /led/cmd` supports:
  - `lightCmdLED`: r/g/b 0-255, t 0.5-60. It returns **error 8 "LED is busy"** if an external command is already queued.
  - `pauseAutoLED`: 0-3600.
  - `setAutoLED`: OnH/M, OffH/M, FlashBri 1-255, Interv 60-3600, FlashDur 0.5-10, WarnCO2 0-3000, WarnVOC 0-500, WarnHum 0-100.
  - `setWiFiLED`.
- **`GET /system/status`:** `Sys_Uptime`, `Wifi_Uptime`, `NTP_LastSync`, `Boot_Signature`, `Error_Status` (an On/Off aggregate), `Task_ErrCnt`, `Task_LastErr`, the per-sensor `ErrCnt` values (RAM only), `SGP40_Backup_TS`/`Restore_TS` (with `"No TS"`/`"None"` coding) and `SGP40_MemErr_Critical`/`Uncritical`/`Last`.
- **`PUT /system/cmd`:** `reboot`, `bootloader`, `mempause`.
- **Error codes:** 0-10 (`api_helpers.py:160-183`).

**Config:** one flat `config.json` (`_DEFAULT_CONFIG`, `:21`). It is re-read from file on every access, and if any key is missing the whole file is overwritten with defaults (`async_manager.py:100-131`).

**WiFi** (`async_connect.py`):
- A 5 s refresh.
- On connect, 10 × 0.5 s status polls. After 5 failures it switches to a hotspot (essid = hostname, hardcoded password, power-save off, captive DNS).
- An 8 min hotspot timer runs while no client is connected, then it retries STA once.
- A second failure streak after the hotspot means permanent WLAN deactivation.
- Once connected, it retries every 60 s and never falls back to the hotspot.
- LED: on when connected, off when not, toggling while connecting, 2.9 s on / 0.1 s off in the hotspot with no client.

**NTP:**
- A 10 s tick. Unsynced, it retries every 10 s forever.
- Synced, it resyncs every `NTP_Interv_H`. A failed resync is retried 3 × 15 s.
- It resolves the server with `getaddrinfo` under the long-block lock.
- `ntp_force_sync()` **sets Synced=False immediately**.
- CET/CEST switch at 01:00 UTC on the last Sunday of March/October.

**Neopixel** (`neopixel_signal.py`):
- 20 Hz ramps and a white overlay at brightness 50.
- Air-quality check every `Interv` s, only inside the On–Off window and with NTP synced. Checks in order: CO2 (red), then `sleep 2×dur`, then VOC (green), then `sleep 2×dur`, then humidity (blue), each with a `>=` comparison.
- If the config is invalid: auto mode off, interval 600 s.

**Sensors:**
- SCD30: IRQ-driven, with a kick after the pin has stayed high for `2×trigger_sec` half-seconds. Soft reset at boot.
- SGP40: 1 s timer. Compensated from the last good SCD30 reading, and skipped if there is none.
- BMP: forced mode, `SLPres = altitude_baro(P-POffs, -SeaLevel, AtmTemp)`.
- Each sensor task aborts after more than 5 consecutive errors.

**FRAM:** one timestamped chunk holding the SGP40 VOC state (248 B, no CRC).

**Web UI** (`html_raw/`): four static pages. Measurements poll every 2 s, and status pages every 500 ms. Cards are colour-coded by the PUT result.

#### 3. Parity table

| Legacy feature | Refactor | Status |
|---|---|---|
| Nine REST routes with a cmd envelope | `src/asy_webserver_service.py:372-382`: six routes, sparse PUT, native bool/null | **Changed, deliberate** (A.8, C.5.3, H.1, H.4) [V]. Old bookmarks such as `/sensorconfig.html` now 404. |
| Measurement field names | `asy_scd30_driver.py:94`, `asy_sgp40_driver.py:71`, `asy_bmp3xx_driver.py:102` | Kept, except the group key is `BMP388` → **`BMP3XX`** [V] |
| SCD30 config and bounds | `asy_scd30_driver.py:57-62` | Bounds identical [V]. **The only-if-changed write is gone** (candidate S2). |
| SGP40 config and bounds | `asy_sgp40_driver.py:51-53` | Identical, with the "SGP" prefix dropped (deliberate, C.5.3) [V]. The `WaitTimeNTP=0` semantics changed (S1). |
| BMP config and bounds | `asy_bmp3xx_driver.py:74-84` | Same bounds and defaults. Oversampling/filter now take real values instead of an index (wire change) [V]. |
| WiFi config | `asy_wifi_service.py:43-53` | Hostname 1-63 → **1-32** (commented as the `network.hostname` cap). SSID min 2 → **0**. PW now allows `""` (open network). New `HotspotPW`, not exposed over REST [V]. |
| NTP config and bounds | `asy_ntp_client.py:65-69` | Identical [V]. GMT/DST moved to `/system` and no longer force a sync. |
| LED auto config and bounds | `asy_notification_service.py:71-78`, `buildgen/codegen.py:28-30` | Identical and colours identical. The `Led` prefix is dropped (deliberate, A.4) [V]. |
| `lightCmdLED` and `pauseAutoLED` | `asy_webserver_service.py:533-566`, codegen `:544-556` | Bounds identical. **Busy semantics and status mapping changed** (S3, W4). |
| `/net/status`, `/time/status`, `/system/status`, `/led/status` | Generated `_networking_status`/`_system_status`/`_notification_status`, served in `/status` | Covered and restructured [V]. `Error_Status` is replaced by the UI's errcount roll-up. `Task_ErrCnt`/`Task_LastErr` become SYSTEM `wrnno=n+1` history entries (`system_service.py:238`). `SGP40_MemErr_*` moves to the owning modules' logs. Counters are now FRAM-persisted. |
| Reboot, bootloader, mempause | `system_service.py:40`, `:347-373`; codegen `_system_cmd_callback` | Delay 5 s → **4 s**. Pending configs are flushed first [V]. |
| Task supervisor | `system_service.py:44`, `:216-255` | Check period 3 s → **2 s**, so the budget decays about 1.5× faster. Past the max it **calls `reboot_system()`** (FRAM paused) instead of starving the watchdog [V]. A.2 still says "stops feeding the watchdog". |
| Setup failure leads to a reboot loop | Generated `build_system()` ignores the `setup()` result | Changed. The legacy loop is gone [V/I]. Probably an improvement, but undocumented. |
| WiFi state machine, timings, LED | `asy_wifi_service.py:138-139`, `:345`, `:473`, `:527-533`, `:593` | Preserved [V] |
| NTP | `asy_ntp_client.py:36-42`, `:416-471` | Unsynced retry now backs off from 10 s up to 600 s (**deliberate**, C.7.2). Adds plausibility and KoD checks. Force-sync semantics changed (W2). Adds a public-DNS fallback (S4). |
| DST math | `asy_ntp_client.py:384-414` | Byte-identical formula [V] |
| Air-quality sequencing | `asy_notification_service.py:369-374` | Preserved. The only difference: it also sleeps `2×dur` after the **last** signal [V]. |
| SGP40 FRAM backup | `asy_sgp40_driver.py:195-440` | Mostly preserved. S1 and W3 are the deviations. |
| Config storage | `config_manager.py` setup `:402-485`; per-module `config_<NAME>.cfg` (`base_classes.py:277`, `system_service.py:102`) | **Changed. `config.json` is never read** (M1). |
| FRAM layout | A.7 chunk order; VOC state 256 B (`voc_algorithm.py:52`) instead of 248 B; CRC added | Changed. The legacy data is not decodable (M2). |
| Favicon | `html/index.html:7` uses `rel=icon href="data:,"` | Deliberately suppressed [V] |
| Web UI | `js/`, generated definitions (`landingSection: measurements`, poll 3000 ms) | Full coverage [V]. The measurement poll goes from 2 s to 3 s. |

#### 4. The A.4 "confirmed intentional" behaviours

All of these are preserved [V]:
- Sequenced LED warnings (`asy_notification_service.py:370-374`).
- The two SGP40 backup zeros: BackupPeriod 0 disables backups (`_check_storage` `cfg_values[0] > 0`), and MaxAge 0 disables the age check (`:420`).
- Permanent WiFi deactivation, and `DEACTIVATED`/`HOTSPOT` surviving a task restart (`asy_wifi_service.py:304`, `:487-499`).
- No hotspot fallback once STA has connected (`:470-474`).
- The SGP40 skip without compensation data, excluded from the error streak through `condition=compensated` (`asy_sgp40_driver.py:274-279`, `:526`).
- The On–Off window not wrapping past midnight (`:369`).
- `get_ambient_pressure()` reusing the set command (`asy_scd30_driver.py:495-496`).

The FRAM "8 KB ample headroom over SGP40's ~250 B" rationale is **stale**. FRAM now holds about 17 logger/cfgmgr chunks on wozi and 21 on dev, plus the VOC chunk. I did not re-check the total against 8 KB (W7).

#### 5. Audit candidates

**Suspicions** (I confirmed the code path; the impact still needs judging):

- **S1: `WaitTimeNTP=0` disables the VOC restore entirely.**
  - Legacy with 0 falls back to `voc_init=1` and restores once, immediately, at the first tick (legacy SGP40 `__init__.py` read_sgp `:80-83`, `:100-124`).
  - The refactor only sets `voc_init` when the value is ≥1 (`asy_sgp40_driver.py:355-358`), so `deserialize` is never True (`:83-86`).
  - The web label `special:0="Never wait for NTP sync"` (`:64`) implies the legacy meaning.
- **S2: SCD30 PUT writes NVM for every field present, even when unchanged.**
  - Legacy `set_sensor_value` only calls the setter if the value differs from the readback, or if forced for AmbPres (`api_helpers.py:192`).
  - The refactor `SCD30_Reader._set_dict_cfg` calls the setter unconditionally and never reports `"Unchanged"` (`asy_scd30_driver.py:257-298`).
  - This matters for SCD30 NVM wear (CLAUDE.md's `scd30_extra_write` gate) and for `ForceCalRef` re-triggering recalibration.
  - C.5.2 only says "SCD30 keeps hand-rolled setters".
- **S3: REST `lightCmdLED` now uses `request_signal()`, not `led_signal()`.**
  - The generated callback is at `buildgen/codegen.py:555`. `request_signal()` spins until any running ramp ends (`asy_neopixel_driver.py:145-153`).
  - With `t` up to 60 s, the HTTP request can block past `outer_cap_s=15` s, where legacy returned "busy" (error 8) at once.
  - `led_signal()` and `start_asy_ext_cmd_watcher` (`:104`, `:137-143`) are now effectively dead.
  - Undocumented. The spec only mentions `request_signal` for notifications.
- **S4: Undocumented public DNS fallback.** `asy_dns_client.py:20` and `:110` try `8.8.8.8` and `1.1.1.1` after the DHCP server. Legacy only used the system resolver. This is a network and privacy behaviour change. I found no mention of it in SPECIFICATION or BACKLOG.
- **S5: NTP "out of sync after 3× interval" can never trigger, in both trees.** `ntp_sec_count` is reset to 0 at every due resync, including failed ones (legacy `async_connect.py:451-461`; refactor `asy_ntp_client.py:456-471`). So a unit synced once stays "Synced" forever, even when every later sync fails. Parity is preserved, but the comment's intent isn't met.

**Worth checking** (behaviour changes whose documentation I couldn't confirm):

- **W1: Supervisor timing and exit path.** `_TASK_CHECK_TIME` changed 3 → 2 s and `_RESET_DELAY` 5 → 4 s. The loop now reboots explicitly instead of starving the watchdog. BACKLOG asks for a supervisor change "without changing observed behavior", and A.2's text is stale.
- **W2: `ntp_force_sync()` no longer clears Synced** (`asy_ntp_client.py:416-422`). Legacy cleared it at `async_connect.py:129-135`. After a PUT of NTP settings with a bad host, local time and notifications keep running on the old sync, where legacy paused them.
- **W3: SGP40 backups after the first NTP-stamped write.** The refactor resets `voc_write = WaitTimeNTP` after every stamped write (`asy_sgp40_driver.py:432-436`), so each later backup waits for NTP again. Legacy set `voc_write=0` for good.
- **W4: `lightCmdLED` status mapping.** A missing key or out-of-range value now yields per-field `"Failed"`, because the callback returns False and the dispatcher maps that to Failed (`asy_webserver_service.py:533-543`). Legacy returned `"Invalid"`/code 7. H.6 says Invalid is reserved for structurally wrong payloads, and `PauseTime` returns Invalid on a range error. The two command fields are inconsistent.
- **W5: Sparse-PUT `""` semantics.** In legacy, `""` meant "unchanged". In the refactor, `"PW": ""` sets an open network (`asy_wifi_service.py:46`). This only matters to external clients or scripts; the UI blocks it (H.4).
- **W6: External REST consumers.** Do any of the five units have scrapers or home-automation hooking the legacy routes, `"On"`/`"Off"` strings or the `BMP388` key? A.8 and H.1 cover only the UI.
- **W7: FRAM budget.** Sum all chunk sizes per device against `max_size=0x2000`. The A.4 headroom statement predates WP1–WP3.
- **W8: Build info** (`/system` → `build`) is not rendered anywhere in `js/`. H.1 says every REST function must be reachable in the GUI.
- **W9: Doc drift.** C.5.3's last paragraph still refers to `/net/cmd`, `/led/cmd` and `sensortask-wozi.py`'s `_cfg_subset`. DEVICE_REFERENCE describes the WiFi LED as "static preference, not a live connectivity signal", but the code still toggles and flashes it with connection state, as legacy did.
- **W10: Minor timing deltas.** An extra `2×FlashDur` sleep after the last warning, and a 2 s → 3 s UI measurement poll.

**Migration issues for a legacy→refactor reflash:**

- **M1: All stored settings reset (verified).**
  - Nothing in `src/` or `buildgen/` reads `config.json` (grep). Every module creates `config_<NAME>.cfg` from its defaults, and the orphan `config.json` stays on flash.
  - The units come back with SSID `""`, so they go straight to the hotspot (`asy_wifi_service.py:441-443`) using the TOML hostname and hotspot password.
  - **If nobody joins within 8 minutes, the second streak permanently deactivates WLAN until a power cycle.** That behaviour is intentional, but it's a real hazard for a reflash campaign.
  - Tuned values are lost too (LED thresholds, NTP, SGP backup settings, BMP offsets). BACKLOG #2's statement that the refactor "avoids this structurally" covers key-adding updates, not the legacy→refactor transition.
  - SCD30 settings survive because they live in its NVM.
- **M2: Legacy FRAM contents are misread after reflash.**
  - Legacy chunk 0 (the SGP40 VOC state: status bytes, 8 B timestamp, 248 B, no CRC) sits at the address where the refactor's first chunk, WIFI's log, now lives. The refactor format adds a CRC and uses a 256 B VOC state.
  - Expect CRC or status-byte errors on the first boot, which could seed misleading errcount entries (see CLAUDE.md's FRAM-evidence rule).
  - The VOC baseline is lost, so the index relearns and sits at 0 for the first 45 samples.
- **M3: The littlefs region has to survive a 1.26→1.29 firmware swap.** That needs the same `MICROPY_HW_FLASH_STORAGE_BYTES` on both versions (B.14.3). I didn't verify this against 1.26.
- **M4: Hostname changes** from the user-set or `"SensorNode"` value to `SensorStation<Name>`, which affects DHCP reservations, DNS names and the hotspot SSID.
- **M5: The deployed wozi unit.** CLAUDE.md says the refactored wozi is "never physically flashed". If the fielded wozi unit is eventually reflashed, its first real flash is a production one. Worth an owner confirmation.

#### 6. Suggested parity-audit checklist

1. Is the REST wire change also accepted for non-UI consumers, and is a compatibility shim wanted (W6)?
2. Is a config-migration step or a documented reflash runbook wanted (M1, M4)? Should `config.json` be imported or deleted on first boot?
3. Should the refactor clear or format the FRAM on first boot after migration, and are first-boot FRAM errors expected and documented (M2)?
4. SCD30: should it restore "skip if unchanged" to spare NVM writes and avoid repeated forced recalibration (S2)?
5. SGP40: which is the intended `WaitTimeNTP=0` behaviour (S1)? Is the per-backup NTP re-wait intended (W3)?
6. LED command: should the "busy" reply be kept, and is `lightCmdLED` Invalid-versus-Failed intended (S3, W4)?
7. NTP: should force-sync clear Synced (W2)? Should staleness actually trigger (S5)? Is the public-DNS fallback acceptable (S4)?
8. Supervisor: do the 2 s tick, 4 s reset and explicit-reboot exit count as "observed behaviour" per BACKLOG (W1)? Does the A.2 wording need updating?
9. Does the per-device FRAM chunk budget fit in 8 KB on all six devices (W7)?
10. Hostname 63→32, SSID min 2→0, and the new configurable `HotspotPW` with no REST exposure: are all deliberate?
11. Is it acceptable that `/system`'s `build` isn't shown in the UI (W8)?
12. Can doc drift be cleaned up: C.5.3's stale routes, A.2's watchdog text, the DEVICE_REFERENCE LED text, and A.4's FRAM headroom note (W9)?
13. Littlefs region equality between 1.26 and 1.29 for `RPI_PICO_W` (M3).
14. Is the loss of the legacy reboot-loop on FRAM setup failure an intended improvement, and should it be recorded?

#### 7. `arduino/` (out of scope)

`arduino/` holds the Arduino peer's side of the project:
- The C implementation of the UART protocol (`libraries/Async_UART_Comm`, `Async_UART`, `CRC_Check`).
- BME688/BSEC2 sketches (`basic_bme688`, `gas_sensor`) and the vendored Bosch BSEC 2.6.1.0 release.
- Supporting libraries: `Adafruit_BusIO`, `Adafruit_FRAM_SPI`, `FlashStorage`, `wdt_samd21`, `BME68x_Sensor_library`, plus a `crc_test` sketch.

Per the owner, it gets no lint, type-checking, tests or reconciliation.
