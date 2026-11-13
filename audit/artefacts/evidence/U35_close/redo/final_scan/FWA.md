# FWA: firmware - sensors, buses, storage (asy_base_classes, asy_i2c_driver, asy_spi_driver, asy_bmp3xx_driver, asy_scd30_driver, asy_sgp40_driver, voc_algorithm, asy_isl29125_driver, asy_fram_driver, asy_fram_manager, crc_checks, math_helpers, asy_config_manager, asy_print_log)

## Verdict (3-6 lines): do the rulings hold in this scope; are drift leftovers gone?
The rulings hold in this scope. The big drift patterns named in PICTURE section 4 and DRIFT 2.9 are gone: the 26 "bus not initialized" raises, the per-episode log flags, the BMP3XX STATUS polling, the per-byte CRC under a FRAM lock, the ~120 C-stack report calls, the Locked* primitives and the hardcoded age checks.
One typing-only guard chain (the M4 pattern) survives, in `compare_before_write()`.
The 2026-11-10 FRAM C-stack rework left two small duplicates behind: a second copy of the "FRAM bus not available" begin, and an orphaned `SPIDevice.session_begin()`.
One agent-widened reading (`CFGMGR_SCD30` kept RAM-only) sits against the owner's 2026-11-09 logger rule.
The rest are leaner forms of pre-audit duplication. None of them is a gap.

## Shape since the baseline (a few lines: what was added/removed and what it is for)
- **asy_base_classes** (414 -> 653 lines). Added: the recovery ladder in one place (`_climb_ladder`/`_recover_bus`/`_recover_device`/`_init_done`), `DeviceSession`, `RegionBuffer` (no lock), the tick primitives (`TickSeconds`/`TickGrid`/`HourlyWindowCounter`/`utc_now`), the shared `_trigger_loop`, `_republish` and the PUT-closure hook. Typing aliases sit under TYPE_CHECKING. Removed: `LockedCounter`/`LockedFlag`/`LockedValue`.
- **asy_i2c_driver.** Gained the boot clear, the `clear()`/`recover()` bus rungs, the NACK->EIO write/read path (`_point_at`/`_write_all`, a real machine.I2C gap) and `get_register_bytes`. **asy_spi_driver** gained the configured-for cache and `begin_sync()`.
- **Drivers.** BMP3XX: one conversion sleep instead of STATUS polling. SCD30: FRC readiness (OR98/OR99) and a range gate. SGP40: VOCState, the heater-off rung and the ValueRef compensation. ISL29125: INT parking, CalLight and the participant rung. The colour chain moved here from math_helpers.
- **FRAM.** Driver and manager are synchronous with no locks (one `begin()` per chunk operation), the CRC is seeded per owner, there is a tri-state read, the chip watch and the erase. The per-episode warning flags are gone.
- **crc_checks.** One viper engine, widths of 1-4 bytes. **voc_algorithm.** Precomputed Q16.16 constants and native multiply/divide.
- **asy_print_log.** Synchronous `err_s`/`wrn_s` (owner 11-07, option B), the newest-entry rule, level 0 silent, and the C-stack record at the logger entry point.
- **asy_config_manager.** `compare_before_write`, exact-type getters, staged flush behind the owner's PUT lock, reset closure and fault flags (all read by asy_system_service).

## Findings (most important first, max 15)

### FWA-1 [class L] [VERIFIED] A typing-only non-dict guard chain around `compare_before_write()`
- **Where:**
  - asy_config_manager.py:194/:200/:204-205: `data: object`, the `| None` return type, and the `type(data) is not dict` branch.
  - asy_config_manager.py:599-601: write_config's "write data is not an object" branch, which persists BAD_ARG.
  - asy_scd30_driver.py:278: `# type: ignore[misc]`, carried only because of that Optional return.
- **What:**
  - Both callers pass a dict:
    - write_config's `data` is typed `JsonMapping`;
    - SCD30's `rest` is a dict comprehension.
  - The REST boundary already refuses a non-object field map:
    - asy_webserver_service.py:792 answers "Invalid";
    - asy_webserver_service.py:642 builds the settings subset as a dict.
  - The system service passes the same dict on (asy_system_service.py:244).
  - So the None branch, its persisted error and the SCD30 ignore cannot be reached. They exist only because the parameter is typed `object`.
  - Introduced with the primitive in U4 (f44b9411, 2026-10-06). Baseline `write_config` iterated `data.items()` directly.
- **Ruling/pillar it meets:** M4 and the owner's 2026-10-27 rule ("catching errors which can only happen for the reason of unfulfilled typing are overkill"); L2.
- **Decision record:** the owner's typing-only rule. The typing-only inventory (owner_report_items.md:122) removed 14 such checks, but this one is not named there. No decision keeps it.
- **Smallest fix:**
  - Type `data` as `JsonMapping` and return the tuple unconditionally (delete :204-205).
  - Delete write_config :599-601.
  - Drop the `[misc]` ignore at asy_scd30_driver.py:278.

### FWA-2 [class R] [SUSPECTED: interpretation] `CFGMGR_SCD30` stays RAM-only on an agent-widened reading, against the 2026-11-09 logger rule
- **Where:**
  - asy_base_classes.py:598-599 and :617: the `_CFG_LOG_FRAM` class flag and the `LogConfig(None, ...)` rebuild.
  - asy_scd30_driver.py:193-194.
  - CLAUDE.md:320-322 and SPECIFICATION.md:844/:7713, which state the exception.
- **What:**
  - The SCD30's ConfigManager stores FRCNoise/FRCRate/FRCWindow in a file. It has real entries to log:
    - an unreadable or damaged file: asy_config_manager.py:504-517 and :544;
    - a failed write: :412 and :570.
  - Those entries are lost at every reboot, unlike every other `CFGMGR_<name>` logger on a FRAM device.
  - The owner's OR99 words (2026-09-29), "No flash writes, no extra FRAM chunk (FRAM stays optional)", were the conditions for the FRC readiness feature (its counters).
  - The lead widened them on 2026-09-30 to forbid the config logger's chunk too (archive audit/actions/U15.md:1632, "Lead, 2026-09-30: the CFGMGR_SCD30 FRAM chunk is not taken").
  - The owner's later general rule (2026-11-09 21:27) is: "either it gets FRAM if it has something to log, or it should get no logger at all".
  - The chunk would cost 30 B of FRAM: 2 x (2 + 10 + 1 + 2).
- **Ruling/pillar it meets:** 2026-11-09 logger rule; 2026-11-10 precedence rule (a later clear decision supersedes an earlier agent-backed one); P7 (evidence survives); L5 (one shape: a special-case flag in the shared base for one driver).
- **Decision record:**
  - OR99 (owner, 2026-09-29), quoted above; the lead's widening of it, 2026-09-30.
  - No owner word applies the 11-09 rule to SCD30 or exempts it.
- **Smallest fix:**
  - Delete `_CFG_LOG_FRAM`: asy_base_classes.py:598-599, and :617 becomes `log=log`.
  - Delete the SCD30 override at asy_scd30_driver.py:193-194.
  - Owner must decide, since OR99's words can be read either way.

### FWA-3 [class L] [VERIFIED] The "FRAM bus not available" begin exists twice
- **Where:** asy_fram_manager.py:67-75 (`_begin(fram, pr)`, used at :178, :267, :325, :337, :620) and asy_fram_driver.py:153-161 (`FRAM_SPI._begin_or_refuse()`, used at :299, :345).
- **What:**
  - The two bodies are identical:
    - `begin()` inside `try`/`except Exception`;
    - `err_s("FRAM bus not available:", e, errno=23)`;
    - `return False`.
  - They run on the same logger object (asy_fram_manager.py:94, :496).
  - Both came with the 2026-11-10 single-session rework (910a0a62). One contract is copied in two modules.
- **Ruling/pillar it meets:** L3/L5 (one mechanism, one place); the 11-07 lean lens.
- **Decision record:** none found for keeping two copies.
- **Smallest fix:**
  - Make the driver's helper public (`begin_or_refuse()`).
  - Call it from the manager's five sites and delete asy_fram_manager.py:67-75. The call depth stays the same.

### FWA-4 [class L] [VERIFIED] `SPIDevice.session_begin()` was orphaned by `begin_sync()`: two shapes for the synchronous session start
- **Where:** asy_spi_driver.py:197-202 (`session_begin`) beside asy_spi_driver.py:179-189 (`begin_sync`).
- **What:**
  - At the baseline, `session_begin()` was the FRAM driver's per-command session and `__aenter__`'s body.
  - Since 910a0a62 (2026-11-10, shortening the FRAM path for the C stack):
    - FRAM uses `begin_sync()` (asy_fram_driver.py:318);
    - `__aenter__` uses `_begin()` (asy_spi_driver.py:134).
  - No `src/` code calls `session_begin()`. tests/test_asy_fram_wire_trace.py:504-530 even patches it to assert the product never calls it.
  - Both methods repeat the same refusal check (`session_lock.locked()` -> RuntimeError).
- **Ruling/pillar it meets:** one shape per job (L5); 11-07 lean lens.
- **Decision record:** none found. The owner's standing rule (2026-11-09 18:30) applies: "Before removing any function which could be a feature which is just unused, ask me".
- **Smallest fix:** delete `session_begin()`; `begin_sync()` is the one synchronous start. Owner must decide (a library method with no caller).

### FWA-5 [class E] [VERIFIED] `SensorReader._republish()` is a generic base mechanism with one caller
- **Where:** asy_base_classes.py:537-542, which carries a `type: ignore[arg-type]`. Its only caller is asy_scd30_driver.py:400.
- **What:**
  - The one call passes all eight field names and changes seven of them; only `TS` survives.
  - The same job is done inline elsewhere:
    - asy_scd30_driver.py:531 writes `self._datastruct = SCD30(...)` directly;
    - asy_ntp_client.py:440 republishes `NTP(Synced=False, LastSyncAge=None, TS=data.TS)` inline.
  - So there are two shapes for "republish keeping TS". The base method also allocates a generator and needs an ignore.
- **Ruling/pillar it meets:** one shape per job; the base carries only what several drivers share (L5); 11-09 "simpler at micro level".
- **Decision record:** none found. It is listed as a primitive in SPECIFICATION.md:7710, which is agent text.
- **Smallest fix:**
  - asy_scd30_driver.py:400 becomes one direct store: `SCD30(None, None, None, None, None, _FRC_NOT_MEASURING, None, <old TS>)`, the way :529-531 already read the old sample.
  - Delete `_republish` and its SPEC line.

### FWA-6 [class E] [VERIFIED] The timer-arm contract is copied into four drivers
- **Where:**
  - asy_bmp3xx_driver.py:316-325
  - asy_scd30_driver.py:546-555
  - asy_sgp40_driver.py:562-571
  - asy_isl29125_driver.py:1002-1011
- **What:**
  - Four identical blocks: `Timer.init(period=..., mode=PERIODIC, callback=lambda _b: <flag>.set())` inside `try`/`except (OSError, MemoryError)` with the same "Could not start timer:" line.
  - Only the period and the flag differ.
  - The base already hosts the shared divider (`_trigger_loop`, asy_base_classes.py:544-552) and the `start_timer` annotation.
  - The copies are pre-audit. The 11-07 lens asks whether they could be leaner.
- **Ruling/pillar it meets:** L3 ("one mechanism in the shared base, not a copy per driver"); L5; 11-07.
- **Decision record:** none found.
- **Smallest fix:**
  - One base helper (`_arm_timer(timer, period_ms, flag)`) holds the try/except.
  - Each `start_timer` becomes one call, plus its `irq()` line where one exists (SCD30, ISL29125).

### FWA-7 [class E] [VERIFIED] The FRAM bump allocator is written out twice
- **Where:** asy_fram_manager.py:515-540 (`get_chunk`) and :557-593 (`get_timestamped_chunk`).
- **What:**
  - The two bodies repeat the same steps:
    - the zero-size refusal;
    - the `CRCPass` default;
    - the two "Storage for ... / Allocation successful" lines;
    - the capacity check;
    - the append and the bump.
  - They differ only in the timestamp's size and the chunk class.
  - The duplication is pre-audit (baseline :645-716). It runs only at construction.
- **Ruling/pillar it meets:** 11-07 lean lens; one shape per job.
- **Decision record:** none found.
- **Smallest fix:** one private placement step that takes the full size and the built chunk. Both public methods keep their signatures (nothing dropped), and about 15 lines go.

## Checked and clean (one line each)
- **Recovery ladder.** It is one mechanism in the base. The bus rungs sit in I2C with one-per-bus dedupe. The driver-side `raise OSError` counts are back to the baseline (BMP3XX 8->9, the one new site being the OSR read gate; ISL29125 4; SCD30/SGP40 0). The "bus not initialized" cascade is gone.
- **C-stack record.** One check sits in `PrintLog._line()`. Explicit calls remain only where no logger sees `e` (asy_base_classes.py:130, asy_isl29125_driver.py:959). Decided (review "ok", B1).
- **Per-episode log flags.** None left in scope (the manager's `_episode_wrn`/`repeat=` are gone); the newest-entry rule is the one dedupe.
- **Hardcoded timed checks and age deadlines.** None in scope. What remains are datasheet waits; the BMP3XX conversion wait is bench-measured (80/80 ready, SPECIFICATION.md:11888).
- **Polling.** The BMP3XX STATUS poll is replaced by one sleep and one 7-byte burst. ISL29125's `_settle_wait` sleeps the exact remainder. The SCL release wait is a clock-stretch bound.
- **Long holds under a lock.** The FRAM operations take no lock and never suspend. The CRC is native (viper). The owner accepted the 12.7 ms per entry (11-10, option a).
- **Allocation cuts.** No new churn-avoiding scratch for short-lived temporaries beyond the pre-audit I2C scratch and the per-chunk status buffers.
- **Console at level 0.** Silent. RegionBuffer's optional logger is the owner-agreed form (owner 2026-11-02, B1 item 2).
- **I2C NACK -> EIO (`_point_at`/`_write_all`).** It closes a real machine.I2C silent-NACK gap: `readfrom_mem_into` leaves the buffer stale.
- **ISL29125 INT parking.** Its datasheet basis was checked and it was kept (redo FINDINGS). Its other mechanisms are pre-audit.
- **FRAM WREN retry and identification retries.** Owner-kept (fram.setup_id_attempts, owner 2026-10-28; WREN retry kept under OR113).
- **FRAM owner seed, chip watch, erase, write order.** Already decided; not re-raised.
- **SCD30 FRC readiness, the range gate and the `_temp_offset_ticks` gate base.** Owner feature, kept.
- **SGP40 VOCState, ResetVOC, the restore/backup flow and the default sources.** Owner, legacy or principle-backed.
- **crc_checks.** One engine, widths of 4 bytes or fewer (owner 11-09); no incremental API left.
- **math_helpers.** The colour chain and the EMA moved beside their one caller; the humidity helpers stay (owner).
- **asy_print_log.** Synchronous FRAM write (owner 11-07, option B), the newest-entry rule and the unreadable-store entry only (E28 shrunk).
- **asy_config_manager.** Every state flag has a reader (asy_system_service.py:274-285, :446, :592, :675, :686); the staged flush waits for the owner's PUT lock.
- **Loggers on modules with nothing to log.** None in scope. FRAMManager's RAM-only logger is the logical exception (it cannot log into itself).

## Notes (anything else, one line each)
- **BMP3XX derived-domain gate (marginal, not a finding).** asy_bmp3xx_driver.py:295-297 re-checks the 300-1250 hPa domain that math_helpers.py:81 already gates. Warning on `slp is None` would drop the duplicate bounds.
- **Library methods with no product caller, left alone under the 11-09 rule.**
  - `FRAM_SPI.verify_present`/`set_write_protected`;
  - `FRAMChunk.read`/`write`, `FRAMTimestampedChunk.read`/`write`;
  - `I2C.scan`/`writeto_then_readfrom`, `I2CDevice.write_then_readinto`;
  - `SensorReader(logger=)` reach-through (no caller at the baseline either);
  - `ConfigManager.get_str_values`.
- **Pre-audit, marginal.** math_helpers' `try`/`except (ArithmeticError, ValueError)` blocks cannot fire inside their own domain gates. `ConfigManager.get_dict()` and `_get_values()` repeat one valid/KeyError body.
- **Removed parameters.** The I2C `out_start/out_end/in_start/in_end` and `setup(probe=)` options went in U5/U10 (2026-10-06/07, before the 11-09 ask-first rule). They had no caller. Recorded here only.
- **I2C boot clear.** It drives the async `_clear_bus` with one `.send(None)`, which is correct only because `awaited=False` never suspends. One routine serves both uses, which is good, but the idiom should be noted if it is ever changed.
