# M1 — by-mode silent-failure pass: lifecycle, supervision, storage (read-only)

Slice: inventory 1.1-1.4 (C1-C61), section 3 RP2040 (H1-H13), W25Q16JV (H20-H23), FRAM (H24-H29), section 4
D1-D7 and D10-D20, section 5 L1-L24 (126 IDs). Sources read: `src/system_service.py`, `src/print_log.py`,
`src/config_manager.py`, `src/base_classes.py`, `src/asy_fram_manager.py`, `src/asy_fram_driver.py`,
`build/generated_src/sensortask_dev.py` (not regenerated), `buildgen/codegen.py:696-709`; MicroPython v1.29.0
(`git describe` = `v1.29.0`) `ports/rp2/{main.c,modmachine.c,machine_mem_backup.c,modules/_boot.py,boards/manifest.py,
mpconfigport.h}`, `shared/runtime/pyexec.c`, `shared/timeutils/timeutils.h`, `py/mpconfig.h`, `extmod/modtime.c`,
`lib/littlefs/lfs2.c`, pico-sdk `hardware_watchdog/watchdog.c`, `hardware_dma/.../dma.h`; datasheet extracts (MB85RS64V,
MB85RS2MTA, RP2040). Work order: `audit/consolidation/M_SRC_CORE.md`, `M_GEN.md`, `M_SPEC.md`, `M_SRC_SENS.md`,
`M_SCR.md`, `M_DOCS.md`; owner rows in `PROJECT_AUDIT_PLAN.md`; register `audit/REGISTER.md`. "PAP" =
`PROJECT_AUDIT_PLAN.md`; "MSC" = `audit/consolidation/M_SRC_CORE.md`.

## (A) Verdict table

| ID | verdict | evidence | note |
|---|---|---|---|
| C1 | WO | `sensortask_dev.py:172` (WDT first line of `build_system()`); M.GEN.001 (M_GEN.md:16) arms the WDT in the boot entry before any product import; M.SRC_CORE.006 (MSC:155) `begin_boot()` + `boot_phase()` record a raise as `_RR_BOOT_FAILURE + phase` read at the next boot | reset loop stays (owner backstop OR31.a (1), PAP:331); now attributed by phase |
| C2 | WO | M.SRC_CORE.015 (MSC:499) feeds after every setup unit; M.SPEC.097 (M_SPEC.md:3496) `feed.*` budget rows recomputed by `tests_scripts/test_timing_budget.py`; OR31.a (2) "every inter-feed boot step is proven well inside 8,000 ms worst case" | — |
| C3 | WO | same rows as C2 (`feed.boot_first` …); HEAD gap = sequencer < 1 s (`system_service.py:160`) + `ntp_force_sync()` (non-blocking, `asy_ntp_client.py:416-422`) + 1 s staggered starts (`:224-227`) | WO order tasks→timers→NTP→supervise (M.GEN.006) is inside the same budget rows |
| C4 | owner | M.SRC_CORE.014 (MSC:475-486): "no software timeout: the watchdog is the backstop, owner, 2026-07-18"; the hang is recorded as `BOOT_TIMERS` failure (M.SRC_CORE.006) | — |
| C5 | WO | M.SRC_CORE.014: arm failure → `err_s(..., errno=_ERR_TIMER)` then `asyncio.sleep_ms(wait)` fallback; every starter still runs | HEAD `:170-175` stops early silently |
| C6 | SF | SF-B5 | partial: see M1-06 |
| C7 | owner | OR18.a (PAP:305): "a stalled chip may recover by a reboot ... escalation through the task supervisor up to a reboot is acceptable and even intended" | rate: 4 deaths ≈ 8 s past budget (`system_service.py:236-254`) |
| C8 | WO | M.SRC_CORE.016 (MSC:530) escalation block; M.SRC_CORE.010 (MSC:302) `_reboot()` flushes stores, `_reset_when_due()` final flush | — |
| C9 | WO | M.SRC_CORE.010: `write_reset_record(_RR_STARVE_ARM_FAILED)` before the starve | — |
| C10 | WO | M.SRC_CORE.011 (MSC:346) closes every store at acceptance; M.SRC_CORE.038 refuses PUTs on a closed store; M.SRC_CORE.010 final flush on the escalation path | — |
| C11 | WO | M.SRC_CORE.009/.011/.016: commanded path stops all feeds once `_feed_owned`, escalation sets `_force_watchdog_starve` → a dropped one-shot ends in the WDT reset, never a fed hang | record says the commanded code (SF-A10 (c)) |
| C12 | safe | a refused write keeps the entry in the RAM ring and `err_count`; the next successful `_write()` packs the whole ring (`print_log.py:244-253`), so entries made during a `mempause` persist after unpause; the reset-window case is print-only by design (M.SRC_CORE.010) | — |
| C13 | SF | SF-A11 | — |
| C14 | SF | SF-B5 (unresolved signature, dead timer) | random signature never replaced by NTP: by design, value must stay stable for the boot (`system_service.py:92, 271-273`) |
| C15 | safe | latch is the contract: "stable for the rest of this boot, so a later change means a reboot happened" (`system_service.py:271-273`; owner, 2026-07-18, MSC:227) | — |
| C16 | refuted | HEAD registers setters at construction before the setup batch (`sensortask_dev.py:228`); WO resolves the provider at the top of `SystemService.setup()` (M.SRC_CORE.017) — both before the webserver exists | no window where a REST level change can arrive first |
| C17 | owner | OR126.a (2) (PAP:523): "at a raised debug level a connected, non-reading USB host may stall each console write up to 500 ms; documented for bench sessions, no code" | level 0: see C28 |
| C18 | WO | M.SRC_CORE.016 `_start_task()` persists `_ERR_TASK_STARTER_RAISED`, budget charged; escalation owner-intended (OR18.a) | — |
| C19 | WO | M.SRC_CORE.016 `_log_dead_task()` persists `_ERR_TASK_RETURNED`, `LastTaskEnd` names the task | — |
| C20 | WO | M.SRC_CORE.011 shutdown sequence: "no step has a timeout that moves on - a hung step is not fed, so the watchdog resets the unit" (OR120.a, PAP:511) | HEAD: supervisor keeps feeding during `_flush_pending_configs()` (`sensortask_dev.py:78-104`) |
| C21 | WO | M.SRC_CORE.063 `_pre_setup_slots`, M.SRC_CORE.065 merge in `setup()` | — |
| C22 | SF | SF-B12 | — |
| C23 | SF | SF-B12 (allocation path only); M.SRC_CORE.065 `stored is None` → `_diag` only, RAM-only for the boot | partial: M1-03 |
| C24 | WO | M.SRC_CORE.063 `reset() -> bool`; M.SRC_NET.123 per-key `ResetErrors` result | — |
| C25 | SF | SF-B14 | — |
| C26 | WO | M.SRC_CORE.063 newest-entry rule (OR35.b, PAP:339) | — |
| C27 | WO | M.GEN.034 catalog `"range": [1, 127]` and the catalog check (A.U2.02); M.SRC_CORE.063 refuses a negative code | unreachable for a cataloged code |
| C28 | refuted | persisted tier is level-independent: `_store_err()` runs before the level test (`print_log.py:203-211`); level 0 only silences console prints | console-only sites are judged per site in their own rows |
| C29 | NEW | `config_manager.py:408-422`; M.SRC_CORE.043 "directory → `_ERR_CFG_PATH_IS_DIR`, `return False`" sets no `faulted`, so `ConfigFaults` (M.SRC_CORE.015) omits it | M1-04 |
| C30 | WO | M.SRC_CORE.043 ENOENT split (absent file written once, OR136.a, PAP:543) | silent-mkfs case: M1-01 |
| C31 | WO | M.SRC_CORE.043 damaged file repaired once and flagged `faulted` → `ConfigFaults` | — |
| C32 | WO | M.SRC_CORE.043 (W10 with the key present → `faulted`) | — |
| C33 | owner | OR71.a (2) (PAP:413): "a config file with a bad, missing or unknown key is repaired by at most one write per boot"; OR52.a (2) migration duty starts at the release | — |
| C34 | refuted | rewrite only when the coerced type differs (`config_manager.py:453-457`), and the rewrite stores the coerced type, so the next boot reads it unchanged — one write, not one per boot | — |
| C35 | owner | SPEC C.7.3 (SPECIFICATION.md:2010-2035): "No write is ever retried ... Bounded by boots, and deliberately no further (owner, 2026-09-25 ...; confirmed by the owner, 2026-09-26)" | visibility of an absent-file write failure: M1-07 |
| C36 | owner | OR69.a (3) (PAP:409): "a power loss between a PUT's response and its deferred flash write may lose that change silently; the write never corrupts" | — |
| C37 | safe | identity check under the lock (`config_manager.py:369-373`; WO keeps it, M.SRC_CORE.044) | — |
| C38 | SF | SF-B3 | partial: M1-07 |
| C39 | safe | per-field `"Unchanged"` reaches the client (`api_response.py:93-98`); hooks run only on a change by design | not a hidden failure |
| C40 | safe | a failed push answers `"Failed"` (`base_classes.py:355-356`); a command-only field stores nothing to roll back (`:373-375`) | — |
| C41 | WO | M.SRC_CORE.038: recovery write result checked; snapshot failure persisted (errno 7) | default only after a persisted snapshot failure |
| C42 | WO | M.SRC_CORE.038 (`_ERR_RECOVERY_READ_RAISED`, recovery check) | — |
| C43 | WO | M.SRC_CORE.037 recovery ladder, streak entry persisted (OR140.a (7)) | — |
| C44 | WO | M.SRC_CORE.037 Resolved: `condition=results[0] is None` (lead ruling 2026-10-01); M.SPEC.052 | — |
| C45 | owner | OR94.a (13) (PAP:459): "a failed or unprovable read keeps the last good sample with its original timestamp, never re-stamped, and the website shows each reading's age" | — |
| C46 | WO | M.SRC_CORE.033 keeps the `except RuntimeError` tolerance deliberately (first pass B coverage note) | — |
| C47 | WO | M.SRC_CORE.092 chip-watch task escalates "declared but not set up" (owner escalation OR18.a) | — |
| C48 | refuted | `verify_present()` has no caller in `src/` or `build/generated_src/` (grep) | WO M.SRC_CORE.107 keeps it for scripts |
| C49 | WO | M.SRC_CORE.106 re-syncs WPEN/BP from the chip, errno 53 for partial protection; w28 per refused write; M.SRC_CORE.065 never overwrites an unreadable store | visible as FRAM w28 in `/status` |
| C50 | WO | M.SRC_CORE.103 (one WREN retry, chip-loss probe, one reporter) | — |
| C51 | owner | OR69.a (1) (PAP:409): "an abrupt reset mid-write may lose a module's whole FRAM error history; the loss stays all-or-nothing"; one busy block is repaired from the other (`asy_fram_manager.py:136-172`), both busy read `False` (A.U16.06 L1 case) | — |
| C52 | owner | MSC:1826-1828: "a hard failure, never a guess (owner, 2026-07-18)"; OR69.a (1) | — |
| C53 | WO | M.SRC_CORE.088: failed repair → `_ERR_FRAM_BLOCK_WRITE`, `None`; store never overwritten (M.SRC_CORE.065) | — |
| C54 | refuted | a status byte neither idle nor uninit is a content finding: the chunk reads `False` and is re-initialised (A.U16.06 (1): "both blocks with a bad status byte: False"); a non-zero factory chip costs one burst of FRAM-RAM-log entries at its first boot, never data | not silent |
| C55 | WO | M.SRC_CORE.082 (episode state removed, newest-entry rule); `mempause` is the operator's own command | — |
| C56 | SF | SF-B12 | — |
| C57 | safe | logger chunks never verify on write, but every write rewrites both blocks in full and every read checks status bytes, CRC and the twin copy (`asy_fram_manager.py:96-180`); a WEL anomaly probes the ID (M.SRC_CORE.103) | residual = OR69.a (1) all-or-nothing |
| C58 | SF | SF-B1 (aligned shift; seeded CRC) | — |
| C59 | WO | M.SRC_CORE.087 (`utc_now()` → TS uninit before sync); M.SRC_SENS.063 persists "Backup loaded without timestamp" | partial: M1-02 (merged SGP40 text can raise on `age None`) |
| C60 | refuted | rp2 v1.29: `MICROPY_EPOCH_IS_1970` (`mpconfigport.h:147`), 32-bit pointers ⇒ `MICROPY_TIMESTAMP_IMPL_UINT` (`py/mpconfig.h:1061-1084`); `mktime()` returns `mp_obj_new_int_from_uint()` (`timeutils.h:86-90`) — valid to 2106, no `OverflowError` | WO already drops the guard (M.SRC_CORE.032 "unreachable on target") |
| C61 | safe | FRAM's own logger is RAM-only by construction (logging a FRAM fault into that FRAM, SPECIFICATION.md:403-405); it is an error source on `/status` (`asy_fram_manager.py:630-634`) and each consuming module keeps its own persisted entry (OR140.a (7)) | lost at reboot by nature |
| H1 | WO | `main.c:142-145` RTC 2021-01-01; M.SRC_CORE.032 `utc_now()` → `None` before the first sync; M.SRC_CORE.006 POR → code 1 | — |
| H2 | SF | SF-B9/SF-A05 (BMP3XX self-reset); FRAM side safe: WEL is cleared at its power-up and every write re-issues WREN and verifies it (`asy_fram_driver.py:200-231`) | ISL29125 BOUTF handled (first pass A) |
| H3 | SF | SF-A10 (`modmachine.c:81-89` collapses causes); M.SRC_CORE.006 record; WDT 8000 ms < 8388 ms cap | — |
| H4 | WO | M.SRC_CORE.006 uses `mem_backup()` = scratch[0..3]/[5..7] (`machine_mem_backup.c:38-40`; OR60.a, PAP:391) | see M1-05 for the bootrom path |
| H5 | owner | OR52.a (3) (PAP:376): "Unauthenticated REST writes and `bootloader` are accepted properties, documented as known limitations" | — |
| H6 | SF | SF-A10 (RUN pin vs brown-out both read "power on"; region survival on RUN unconfirmed) | — |
| H7 | refuted | M.SPEC.049 (M_SPEC.md:1771): CS sits at 0.22-0.74 × VDD between pad pull-down and chip pull-up, "SCK and SI are pulled down with it, so no op-code can be clocked in"; M.SRC_CORE.108 | — |
| H8 | SF | SF-A07 (UART TX stall); Phase C parked point (CYW43 under a 400 ms stall); M.SPEC.097 `stall.flash_program` row | — |
| H9 | WO | M.SRC_NET.221 (RX DMA ring + OE) — UART slice; SF-A06 for FE/BE | dev only |
| H10 | WO | A.U13.R01 recovery ladder (M.SRC_CORE.037 rungs); watchdog backstop "(owner, 2026-07-24 ...)" (CLAUDE.md:201) | — |
| H11 | owner | OR126.a (2): console stall only with a host holding DTR, accepted as a debug-mode limitation; E15 is the bench host | bench only |
| H12 | safe | `dma_channel_abort()` waits for `CTRL.BUSY` to clear before returning (`dma.h:759-765`), the datasheet's restart condition (RP2040 DS 2.5.5.3) | (RU) spurious completion IRQ only matters if the UART ring enables one — UART slice |
| H13 | refuted | no `lightsleep`/`deepsleep`/`hard=True` in `src/` or generated code (grep) | — |
| H20 | safe | littlefs commits metadata pairs at sync; an interrupted program/erase leaves the old file (`lfs2.c:3146-3149, 3250-3253`) | — |
| H21 | safe | a program dropped under write inhibit fails littlefs' read-back (`lfs2.c:189-201` → `LFS2_ERR_CORRUPT` → relocate) | — |
| H22 | SF | SF-B3 (writes fail → errno 14/4, "running unpersisted") (RU: nothing in firmware sets BP) | — |
| H23 | owner | C.7.3 bound: one write per explicit change or per boot (owner, 2026-09-25/26, SPECIFICATION.md:2027-2033); C34 refuted (no per-boot rewrite) | — |
| H24 | safe | out-of-spec writes are caught at read (status bytes, CRC8, twin copy) and never restored garbled; the next write rewrites both blocks | (RU) whether the Pico W 3.3 V rail sags below 3.0 V; dev's MB85RS2MTA is 1.8-3.6 V |
| H25 | refuted | M.SPEC.049 (power-on hold met by boot timing; no op-code can be clocked during reset); at power-off CS is driven from the shared IOVDD rail | — |
| H26 | safe | busy marker set around every read (`asy_fram_manager.py:293-345`) plus the twin copy | — |
| H27 | WO | as C49 (M.SRC_CORE.106/.065/.084) | — |
| H28 | safe | SLEEP needs a bare 1-byte opcode with no further SCK (MB85RS2MTA p.11); a corrupted WREN/WRDI is the only path and lands in the WEL check + ID probe (M.SRC_CORE.103) | (RU) |
| H29 | safe | WREN before and WEL verified on every write/WRSR (`asy_fram_driver.py:200-215`) | — |
| D1 | NEW | stock frozen `ports/rp2/modules/_boot.py:7-12` (bare `except:` → `mkfs`), frozen via `boards/manifest.py` included by `scripts/build_firmware.py:43`; no WO change (grep `mkfs`: none) | M1-01 |
| D2 | owner | `main.c:237-251` + `pyexec.c:749-752`: an FS `boot.py` runs first, a raise skips `main.py`; OR59.a (1) (PAP:389) "The reflash runbook erases the filesystem on every reflash"; OR52.a (1) | stays documented (M.DOCS.044) |
| D3 | safe | `pyexec_file_if_exists()` takes the frozen `main.py` first (`pyexec.c:744-747`); OR59.a (2) puts `.frozen` first on `sys.path` (M.GEN.001) | — |
| D4 | WO | M.SRC_CORE.006 phase record; M.GEN.001; M.SRC_CORE.016 `main()` never returns | traceback stays console-only |
| D5 | SF | SF-A14 | — |
| D6 | safe | WDT survives soft reset (`main.c:265-303` never touches it) and the next autostart re-arms it first; the raw-REPL soft reset (mpremote) does not run `main.py` (`main.c:246`) → WDT reset ~8 s later: bench-only, documented (`tests_hardware/README.md:383-391`) | ResetReason misreads it as watchdog: SF-A10/A-14 family |
| D7 | safe | `gc_sweep_all()` after the UART/DMA deinit (`main.c:277-303`), first pass A | — |
| D10 | SF | SF-A11 (auto-unpause); others backed: reset (WDT, M.SRC_CORE.009/.011), sequencer (owner, C4), NTP retry (M.SRC_NET.051) | — |
| D11 | refuted | no hard IRQ callbacks (grep) | — |
| D12 | SF | SF-B4, SF-B5 (per-site ENOMEM outcomes); M.SRC_CORE.014/.010 for the others | ≤ ~11 concurrent alarms on dev vs 16 |
| D13 | WO | M.SRC_CORE.032 `TickSeconds`, M.SRC_CORE.013 uptime on measured ticks | — |
| D14 | owner | CLAUDE.md:334 "(owner, 2026-09-26: 'The firmware must be rock solid without the threshold, ...')" | — |
| D15 | WO | U30: M.SPEC.126 allocation-site catalog, OR110.a (PAP:491) | — |
| D16 | WO | M.SRC_CORE.034 `report_if_fatal()`; M.SRC_CORE.016 supervisor counts any task end; M.SPEC.128 I.4 (a)-(d) | — |
| D17 | WO | M.SRC_CORE.107 `except asyncio.TimeoutError` on the one bounded wait; M.SPEC.093 F.1 facts | — |
| D18 | owner | CLAUDE.md:199-202 "the hardware watchdog is the backstop ... (owner, 2026-07-24 ...)" | — |
| D19 | SF | SF-B3 | partial: M1-07 |
| D20 | SF | SF-A07; Phase C parked (CYW43); M.SPEC.097 | — |
| L1 | WO | M.SRC_CORE.043 (OR136.a: absent files written once), M.SRC_CORE.084 (blank block takes no busy marker); SCD30 first start = first AmbPres PUT (OR71.a (2)) | hotspot path is NET's |
| L2 | NEW | as D1: the FS mkfs is silent | M1-01 |
| L3 | WO | M.GEN.006 order construction → setup → tasks → timers → NTP (OR75.a, OR47.a (1)) | — |
| L4 | owner | M.SRC_NET.100 "Deactivated: a distinct pattern (owner, 2026-09-29)" | NET slice |
| L5 | WO | M.SRC_CORE.032 (`utc_now()` `None`), M.SRC_CORE.013 (signature), `VOCState` (M.SRC_SENS) | — |
| L6 | safe | baseline, no mode | — |
| L7 | WO | ISL29125 tick-horizon fixes M_SRC_SENS.md:2075-2077, :2138, :2281 | SENS slice |
| L8 | safe | every elapsed time via `ticks_diff`/`ticks_add`, no raw subtraction (first pass A, time/ticks) | — |
| L9 | SF | SF-B14; WO M.SRC_CORE.031 `COUNTER_CAP`, check-before-step (OR105.a) | — |
| L10 | WO | U30 (M.SPEC.126, OR110.a) | — |
| L11 | refuted | as C60: UINT timestamps on rp2 v1.29, valid to 2106; reads do not fail in 2038 | — |
| L12 | safe | era step `asy_ntp_client.py:254-257` + 2025-2100 gate | zero-timestamp → 2036 is the U18 parked delta |
| L13 | WO | M.SRC_CORE.010/.011 | — |
| L14 | WO | M.SRC_CORE.016 | — |
| L15 | SF | SF-A10; M.SRC_CORE.006 (watchdog = region 0 empty); torn chunk owner OR69.a (1) | — |
| L16 | owner | OR69.a (1) (FRAM all-or-nothing) and (3) (staged config); peripherals SF-B9 | — |
| L17 | owner | OR18.a escalation; C.7.3 flash bound; newest-entry rule (OR35.b) keeps one slot per repeating code; ResetReason/LastTaskEnd name the pass | see walk 7 |
| L18 | owner | OR52.a (3) | — |
| L19 | SF | SF-B1 (FRAM); config keys repaired (M.SRC_CORE.043, OR71.a (2)); FRAM need not survive a reflash (OR47.a (2), PAP:366) | — |
| L20 | owner | OR52.a (1) "No legacy config migration ... covered by a reflash runbook"; OR59.a (1) | — |
| L21 | WO | M.SCR.067 image record (`buildDate`, `commit`, `dirty`) beside every `.uf2`; `/system` `BuildDate` | — |
| L22 | owner | OR18.a ("a configuration not matching the hardware ... escalation ... intended"); M.SRC_CORE.092 escalates; TOML names the part (M.SPEC.049 (2)) | reboot loop by design |
| L23 | owner | CLAUDE.md:164-166 only `dev` is bench-tested "(owner, 2026-09-03, `a19691c`)"; A.S0930.28/.29 read-and-archive before an erase | — |
| L24 | owner | OR69.a (1)/(3) power-removal residuals; M.SRC_CORE.018 removes the unused `stop_uptime_timer()` | — |

## (B) Findings (NEW and partial)

Most severe first.

### M1-02 Merged SGP40 restore text compares `None` with an int when the backup has no usable age (WO-introduced)
- **Site**: M.SRC_SENS.063 (M_SRC_SENS.md:1588-1597) `_run_restore()`: "`ts is None` → `wrn_s(...)`, `ts =
  _NO_TIMESTAMP`; `age is None` with `_voc_init > 0` → ... return `False`; otherwise `self._voc_init = 0`, ... and `if
  cfg_values[1] > 0 and (age < 0 or age > 60 * cfg_values[1])`". M.SRC_CORE.087 returns `age = None` whenever the stored
  TS is uninit or NTP is not synced at the read. HEAD (`asy_sgp40_driver.py:380-396`) restores in both cases without an
  age test.
- **Class**: 4 (a sentinel the caller does not test) → 6 (the task dies, restarts, repeats). **Mode**: boot with no
  NTP within `WaitTimeNTP` (network outage, hotspot, first boot); a backup written before the first sync (undated).
- **Failure**: once the countdown reaches 0 with `age is None`, `None < 0` raises `TypeError` on MicroPython; the SGP40
  task ends, the supervisor charges +100 and restarts it, `_init_sgp()` re-arms the countdown (default 30 s), and it
  raises again: +100 per ~30 s against −15 decay ⇒ budget exceeded after ~4 passes ⇒ reboot loop for as long as NTP
  is unavailable. An undated backup raises on every boot even with NTP.
- **Effect**: all six devices (SGP40 and FRAM on every TOML; `BackupMaxAge` default 7200 > 0). Bus: none (logic only).
- **WO**: the regression is in the merged text; M.TEST_UNIT.138 pins the negative age only; the listed L1 cases
  ("WaitTimeNTP 0", "single re-read") may or may not hit `age None` at countdown end.
- **Owning unit**: U16 (M.SRC_SENS.063's unit). To confirm with the SENS slice.
- **Smallest fix**: test the bound only when `age is not None` (`... and age is not None and (age < 0 or ...)`) — an
  ordering/guard, no state; restores without an age as HEAD does (wrnno persisted). L1 cases: undated backup; dated
  backup with NTP unsynced at countdown end; both restore, nothing raises.

### M1-01 A littlefs mount failure reformats the filesystem silently; the device returns to factory config with no trace
- **Site**: stock `ports/rp2/modules/_boot.py:7-12` (`try: VfsLfs2(...) except: mkfs(...)`), frozen through
  `$(PORT_DIR)/boards/manifest.py` (`freeze("$(PORT_DIR)/modules")`, included at `scripts/build_firmware.py:43`) and run
  by `main.c:233` before any project code. Our side: every store then takes the absent-file path — HEAD
  `config_manager.py:423-426, 459-460` (wrnno 3, indistinguishable from any missing file); WO M.SRC_CORE.043 prints it
  (`pr.one(... "not present - writing the defaults once")`), and `ConfigFaults` (M.SRC_CORE.015) lists only unreadable
  or damaged files.
- **Class**: 6 (a recovery nobody can observe), 7. **Mode**: boot, first boot after FS loss, after a firmware change.
- **Layer below**: mkfs on any mount exception, no flag, no return value, nothing left for Python to read.
- **Failure**: Wi-Fi credentials, hostname, NTP, notification and sensor settings revert to defaults; empty SSID →
  hotspot → the owner's deactivation path (M.SRC_NET.100) if no one configures it. FRAM history survives and says
  nothing; `ResetReason` shows only the reset kind.
- **Effect**: all six devices; no bus.
- **WO**: not covered (grep `mkfs`/`reformat` over `audit/consolidation/`: none).
- **Owning unit**: U11 (M.SRC_CORE.043), U20 for any `/status` key.
- **Smallest fix (visibility, behaviour unchanged)**: make the absent-file branch a persisted warning in the store's
  own FRAM-backed logger instead of the `pr.one` print (a different call at an existing branch, one slot per store per
  fresh filesystem). A factory flash, the runbook erase and "Reset to defaults" (ResetReason 7) pay it once and explain
  it; a reformat behind the user's back is then visible in every `CFGMGR_<name>` history. No new state.

### M1-03 A logger whose store reads "unreadable" at setup runs RAM-only for the whole boot; only a console line says so (SF-B12 partial)
- **Site**: HEAD `print_log.py:273-279`; WO M.SRC_CORE.065 (`stored is None` → `_diag("PrintLog: FRAM unreadable -
  stored history kept, RAM-only until reboot")`, `initialized` stays `False`; no retry, A.U16.06 (4)); M.SRC_CORE.039
  `SensorReader.setup()` returns `True` regardless and `run_setups()` discards results (M.SRC_CORE.015).
- **Class**: 4/7. **Mode**: boot; FRAM fault at a chunk read (both blocks faulted, write-protected chip).
- **Failure**: the module's errcount on `/status` looks persisted but is RAM-only; everything it logs this boot is gone
  at the next reset. The FRAM layer's own fault entries (RAM logger) show a fault, not which module lost persistence.
- **Effect**: every FRAM-wired logger on all six devices; FRAM on SPI0.
- **WO**: SF-B12 covers the allocation path only (allocator full, history `MemoryError`).
- **Owning unit**: U16 (with SF-B12).
- **Smallest fix**: extend SF-B12's report to this branch — the bool `PrintLogHistoryStore.setup()` already returns
  `False`; one counted entry in FRAM's RAM logger (the chunk already holds `manager.pr`) naming the store, so `/status`
  shows which module is RAM-only. No retry (A.U16.06 stands).

### M1-07 A failed write in `ConfigManager.setup()` leaves the store unpersisted with no `/status` marker (SF-B3 partial)
- **Site**: HEAD `config_manager.py:475-485` (errno 4); WO M.SRC_CORE.043 (one write path, `_ERR_CFG_FILE_WRITE`).
  SF-B3's proposed `unpersisted` flag is set only by the deferred PUT flush.
- **Class**: 7. **Mode**: first boot (absent-file defaults), full filesystem (D19), BP-protected flash (H22).
- **Failure**: an absent file whose defaults write fails is not `faulted` (not damaged), so `ConfigFaults` stays empty;
  the store runs on RAM defaults and repeats the attempt every boot (owner-bounded, C.7.3). Only the persisted errno
  shows it.
- **Effect**: every schema-backed store, all six devices.
- **Owning unit**: U11 with SF-B3.
- **Smallest fix**: set SF-B3's flag at setup()'s failed write too (one assignment on the shared write path).

### M1-04 A config path that is a directory invalidates the store but is not listed in `ConfigFaults`
- **Site**: HEAD `config_manager.py:408-422` (errno 1, `return`, `valid` stays `False`); WO M.SRC_CORE.043
  ("directory → `_ERR_CFG_PATH_IS_DIR`, `return False`", no `faulted`).
- **Class**: 7. **Mode**: boot; leftover filesystem content (manual `mkdir`, legacy residue the runbook should erase).
- **Failure**: every get returns `None`: WIFI → deactivated for good (C70), a sensor → init fails → restart budget →
  reboot loop (owner escalation). `/status` `ConfigFaults` empty; only the CFGMGR errno, if the device is reachable.
- **Effect**: any store, all six devices; reachable only by manual action (low).
- **Owning unit**: U11.
- **Smallest fix**: `self.faulted = True` in the directory branch (the flag and the list exist). "Reset to defaults"
  deletes an empty directory (littlefs `remove`), a non-empty one ends in ResetReason 9 — both already visible.

### M1-06 With a dead uptime tick timer, `TickSeconds` can be read later than its 2**29 ms horizon (SF-B5 partial)
- **Site**: M.SRC_CORE.032 (`TickSeconds`: "a caller reads it at least once per 2**29 ms"); M.SRC_CORE.013 (the only
  periodic reader is `status_counter()`, woken by the tick flag). With the timer unarmed (SF-B5) the readers are on
  demand only: `get_uptime()` (`/status`) and the webserver's drop window (`uptime_s=sysfunct.get_uptime`, M.GEN.009).
- **Class**: 5. **Mode**: long uptime with SF-B5's failure; no client for > 6.2 days.
- **Failure**: a delta past the horizon is ignored (uptime stalls) or aliases (short by 2**30 ms multiples); the
  `HTTPDropped` bins shift wrong.
- **Effect**: all six devices; no bus.
- **Owning unit**: U11 (with SF-B5).
- **Smallest fix**: SF-B5's re-arm fallback must read `TickSeconds` each bounded sleep (its loop already does when it
  mirrors `status_counter()`); state it in SF-B5's A-C delta and add the dead-timer + 7-day-gap L1 case.

### M1-05 The bootloader reset record is probably clobbered by the bootrom (unconfirmed)
- **Site**: M.SRC_CORE.006/.011 S6: `write_reset_record(_RR_BOOTLOADER)` into region 0 (= watchdog scratch[0..3],
  `machine_mem_backup.c:38`), then `machine.bootloader()` → `reset_usb_boot(0, 0)` (`modmachine.c:91-97`). RP2040 DS
  2.8 says `_reset_to_usb_boot` "uses the watchdog facility to re-start in BOOTSEL mode"; the two mask arguments must
  survive that reset, plausibly in the low scratch registers, and the watchdog-boot vector occupies scratch[4..7]
  (DS 2.8.1.1), i.e. region 1.
- **Class**: 1/7 (cause lost). **Mode**: each kind of restart (bootloader), after a firmware change.
- **Failure**: after BOOTSEL and `picotool reboot` (watchdog) or a power cycle, `begin_boot()` reads region 0 empty →
  ResetReason 2 or 1; code 4 is never observed.
- **Effect**: any device given `bootloader` (dev bench in practice); misattribution only.
- **Owning unit**: U11 / phase C.
- **Smallest fix**: no code; a phase-C bench check (send `bootloader`, reboot out, read ResetReason) and one SPEC F.5.4
  sentence with the outcome; join SF-A10's open points.

## (C) Scenario walks (crossed pass)

1. **First boot and factory state.** Boot entry arms the WDT, `begin_boot()` sees POR (code 1). Construction allocates
   every chunk in generated order (SF-B12 if one fails). `fram.setup()` identifies the chip (3 attempts); each logger's
   `setup()` reads blank status bytes (0x00) as uninitialised, takes no busy marker (M.SRC_CORE.084) and writes its
   empty ring. A factory chip that is not 0x00 reads invalid content and re-initialises (C54, visible burst). Each store
   hits ENOENT and writes its defaults once (OR136.a); a failed write is not in `ConfigFaults` (M1-07). SCD30 stays
   unstarted until the first AmbPres PUT (owner). Empty SSID → hotspot (NET slice). FRAM absent on a TOML that declares
   it → watch task escalates → reboot loop (owner OR18.a). Nothing else found.
2. **After a firmware change.** Config: unknown/missing keys repaired once (owner), damaged values flagged. FRAM: an
   aligned layout shift is SF-B1; a non-aligned one reads invalid and re-inits (OR47.a (2)). `mem_backup` regions from
   the previous image validate by check word or read "unknown". Bootloader entry for the reflash: M1-05. Two images with
   one version: M.SCR.067 record. Nothing else.
3. **Boot.** WDT first (M.GEN.001) → imports → `begin_boot()` → construction (phase 1) → `run_setups()` fed per unit
   (phase 2; a raise ends the boot, recorded as 12) → `start_tasks()` (webserver live before timers and NTP; a command
   accepted now waits at S1 for the supervisor to start and park, ≤ ~2 s, fed once at S1) → `start_timers()` (a dropped
   stagger one-shot hangs → WDT, recorded as 14, owner) → NTP → `supervise_tasks()`. Pre-setup log entries merge
   (M.SRC_CORE.065); an unreadable store at setup: M1-03. Unreadable/damaged config listed; directory path not: M1-04.
4. **Boot path files.** Stock frozen `_boot.py` mounts or silently reformats (M1-01). An FS `boot.py` runs before the
   frozen `main.py` and a raise there leaves the REPL with no WDT armed (owner: runbook erases the FS, OR59.a (1)). An FS
   `main.py` never runs (frozen first, `pyexec.c:744-747`); `.frozen` first on `sys.path` (OR59.a (2)). `main()`
   raising → REPL with WDT armed → reset, phase-attributed (M.SRC_CORE.006). Nothing else.
5. **Each kind of restart.** POR: RTC 2021, regions cleared → code 1. Brown-out on DVDD and RUN pin also read "power
   on" (SF-A10). WDT starvation → region 0 empty → 2. `machine.reset()` outside `_reboot()` → 2 (SF-A10 (a)).
   Commanded → record 3/7/8/9; bootloader → M1-05. Soft reset (bench): WDT keeps running, raw-REPL soft reset does not
   re-arm it (documented trap). Peripherals keep their state across an MCU-only reset: FRAM WEL re-issued per write,
   a write cut mid-chunk leaves a busy block (handled), I2C boot clear (A.U13.R01). Nothing else in this slice.
6. **Power loss at any instruction.** Flash: littlefs commit-at-sync keeps the old file; WO dumps JSON before opening
   (`json.dumps` then `open("w")`, M.SRC_CORE.044/.043) — at HEAD a `MemoryError` inside `json.dump()` would close and
   commit a truncated file, which the WO removes. FRAM: busy markers + twin copy; torn between blocks → owner hard
   failure, all-or-nothing (OR69.a (1)). Staged config → owner OR69.a (3). Delete during Reset-to-defaults → OR119.a (4).
   SCD30 NVM → phase C parked. Nothing new.
7. **Boot loop.** Each pass: one ResetReason (last pass only), FRAM logger writes (no wear, owner), at most one config
   repair/defaults write per file (C.7.3), supervisor entries that, interleaved (task end, budget), evict pre-loop
   history after ~5 passes while the repeating cause stays visible; `ErrCount` keeps climbing across passes. A loop that
   never reaches `start_tasks()` (setup raise, sequencer hang) is visible only on the USB console until a pass
   succeeds (inherent). With M1-02 unfixed, a no-NTP boot becomes such a loop. No further finding.
8. **Reset countdown.** Commanded: gate → stores closed → supervisor parked → sequence feeds → `_reboot(fed=True)` →
   arm; a dropped arm fire ends in the WDT (recorded code). Escalation: entry → feed → starve → `_reboot()` flushes,
   pauses, arms; PUTs in the 4 s window are flushed by `_reset_when_due()`; the flush window plus 4 s stays inside the
   8 s WDT (record already written). `mempause` refused during a shutdown; during the escalation window its auto-unpause
   is blocked by `_reset_armed` (M.SRC_CORE.012). SF-B4/SF-A11 hold. Nothing new.
9. **Upgrade from legacy firmware.** Runbook erases the FS (owner), so no legacy `boot.py`/config survives; FRAM from the
   legacy layout reads invalid or, aligned, SF-B1; SCD30 NVM keeps legacy settings (runbook item); legacy images never
   wrote `mem_backup`. Nothing new.
10. **No graceful shutdown.** Power removal at any instant reduces to walk 6; the unused `stop_*` methods go
    (M.SRC_CORE.018). Nothing new.
11. **Long uptime.** `ticks` handled via `ticks_diff`; `TickSeconds` relies on a reader inside 6.2 days — fine while the
    tick timer runs, M1-06 when it does not. `ErrCount` saturation SF-B14; counters capped below 2**30 (OR105.a); FRAM
    `_write_gen` wraps inside the small-int range; heap U30. Nothing else.
12. **Flash writes.** Deferred flush in its own task, interrupts-off window per F.3 rows (UART RX ring absorbs it, TX
    SF-A07, CYW43 phase C); a write cut by reset/WDT leaves the old file; full FS → ENOSPC → errno, SF-B3 (+ M1-07 for
    the boot write). Nothing else.
13. **FRAM writes.** Cut part-way → busy block, repaired from the twin; failed write → layer entries (OR140.a (7));
    allocator end SF-B12; chip stops answering → WEL anomaly → ID probe → `lost` → silent chunk ops → watch task →
    re-setup or escalation (M.SRC_CORE.092/.103); on return each logger's next write re-persists its whole RAM ring.
    Unreadable at setup → M1-03. Nothing else.
14. **Supervision.** Task end → one persisted entry, budget +100, restart; past budget → escalation; a hung-but-alive
    task is not detected (owner OR31.a: no heartbeats); FRAM watch task ends count like any task. With M1-02 the SGP40
    restore becomes a periodic task death. Nothing else.
15. **Runtime limits.** Scheduler queue: periodic timers self-heal, one-shots backed by WDT except the auto-unpause
    (SF-A11); alarm pool ≤ ~11 of 16 on dev, every arm site guarded (SF-B4/SF-B5 for two); `MemoryError` and
    `asyncio.TimeoutError` handled per M.SRC_CORE.034/.107; `struct` packing in this slice is in range (`<H` ≤ 0xFFFF,
    `B` ≤ 0xFF, `<Q` timestamp). `TypeError` from a `None` comparison is not an `OSError` either — M1-02. Nothing else.

## (D) IDs per verdict

| verdict | count | IDs |
|---|---|---|
| WO | 47 | C1-C3, C5, C8-C11, C18-C21, C24, C26, C27, C30-C32, C41-C44, C46, C47, C49, C50, C53, C55, C59; H1, H4, H9, H10, H27; D4, D13, D15, D16, D17; L1, L3, L5, L7, L10, L13, L14, L21 |
| owner | 23 | C4, C7, C17, C33, C35, C36, C45, C51, C52; H5, H11, H23; D2, D14, D18; L4, L16, L17, L18, L20, L22, L23, L24 |
| SF | 22 | C6, C13, C14, C22, C23, C25, C38, C56, C58; H2, H3, H6, H8, H22; D5, D10, D12, D19, D20; L9, L15, L19 |
| safe | 20 | C12, C15, C37, C39, C40, C57, C61; H12, H20, H21, H24, H26, H28, H29; D3, D6, D7; L6, L8, L12 |
| refuted | 11 | C16, C28, C34, C48, C54, C60; H7, H13, H25; D11; L11 |
| NEW | 3 | C29 (M1-04); D1, L2 (M1-01) |
| total | 126 | |

Partial covers with findings: C59 (M1-02), C23 (M1-03), C35/C38/D19 (M1-07), C6/C14 (M1-06); walk-only: M1-05.
