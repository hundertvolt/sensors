A scan, written by the lane (Wed Oct 28 07:46:35 UTC 2026)

# SCAN-FW group A (core and storage): firmware changes 25caf528..497b3eda against the pre-audit code

Files: `src/asy_base_classes.py` (was `base_classes.py`), `asy_system_service.py` (was `system_service.py`),
`asy_config_manager.py` (was `config_manager.py`), `asy_print_log.py` (was `print_log.py`), `asy_fram_manager.py`,
`asy_fram_driver.py`, `asy_api_response.py` (was `api_response.py`), `asy_crc_checks.py` (was `crc_checks.py`),
`math_helpers.py`, `asy_framing_codecs.py` (was `framing_codecs.py`). Worktree `S/wt-u35int` at `497b3eda`, read only.
Every row was taken from the diff against the old name; commits by `git log -S` on the row's anchor text; origins from
the action files (`audit/actions/U*.md`, "Why"), `audit/consolidation/M_SRC_CORE.md` ("From"), `audit/REGISTER.md`,
`audit/sweeps/open_findings.md`, the commit messages and the lane hand-backs in `S/u35r/handbacks_redo/`; owner
quotes from `PROJECT_AUDIT_PLAN.md`'s OR table (cited `PAP:<line>`), `S/u35r/recovered/owner_rulings_after_LN118.md`
(`ORL:<line>`) and the code's own `(owner, date)` tags. Line counts are source lines in the cited range at
`497b3eda`, comments included, rounded.

## Legend

Classes as the brief defines them. Two conventions of this lane: a hypothetical that this scan **confirmed** is
class **K** (the knowledge is real; whether its code is the minimal form is the open point) and goes on the
minimal-change list; a removal the owner ruled for is class R with a negative size.

Scheme rules cited in the `scheme` field (violated, or "claims" when the change names it as its reason):
- **MIN** owner 2026-10-28: "the way it flows into the firmware and buildgen is *really* minimal change" (brief :5).
- **HYP** owner 2026-10-28: "Speculative and hypothetical effects maybe, maybe not." / "Hypothetical findings which
  are suspicious to be real need to be verified" (brief :6, :8).
- **CAS** owner 2026-10-28: "Resulting cascades are a red flag at least." (brief :7).
- **DELAY** owner: "hardcoded delay checks like this are a very bad, very awkward pattern" (brief :106).
- **P4** `audit/CONSOLIDATION.md:27` "Premium code, one material, nothing in the product for tests".
- **P6** `CONSOLIDATION.md:29` "Efficient and compact on low-end hardware". **P7** `:30` "Evidence survives and
  stays readable". **P9** `:32` least wear.
- **OR35b** `PAP:339` (owner, 2026-09-26) "just don't repeat the same error in the slots. Pure and simple." with its
  integration "No per-origin, per-module or per-episode special cases."
- **D1** `SPECIFICATION.md:4765-4766` "do not silently change it — flag and ask before altering real output".
- **D2** `SPECIFICATION.md:4778-4779` "Don't defend against out-of-contract input at runtime if static typing already
  enforces it".
- **TYP** owner 2026-10-27 (`ORL:93`): "A strong hint for an unnecessary check is that it is proven to be fully
  covered by typing adherence alone, and that it is unreachable with today's code".
- **MEMC** `CLAUDE.md:250-257` the one `MemoryError` criterion; `asyncio` primitives never blanket-wrapped.
- **FEAT** `CLAUDE.md:508-512` "same *top-level features*".

Verifications V1-V11 are in their own section below; rows cite them. A field a short row leaves out reads: legacy no
(no such mechanism in `legacy/firmware/python/`), form design, depends on none, scheme none.

# Rows by file

## src/asy_base_classes.py (was src/base_classes.py)

Checked for non-changes: the `asy_lock` → `session_lock` and other attribute renames, private names, the typing
aliases and Protocols, `DeviceSession` (four byte-identical per-driver session classes merged, A.U15.40), the
`_set_dict_cfg()` move from `SensorReaderConfig` to `SensorReader` (A.U4.03, same orchestration), the
`_trigger_loop()` divider moved from BMP3XX/ISL29125 (A.U15.40 (2)), `@tunable` tags, the D.15 reorder and the
`logger=` parameter (removed and restored in the range, net unchanged). None counted.

### A-B1 One counter cap, `LockedCounter` saturates at it
- where: `:76`, `:247-279`. what: a `LockedCounter` without an explicit `max_val` caps at 2**30 − 1 (was 255);
  every cap clamps to that value. commits `41b47f1d`.
- origin: A.U10.01 (M.SRC_CORE.031). evidence **O**: OR103 "No unbounded counters anywhere." (`PAP:476`); OR105 "I
  want to exactly avoid allocations happening at some point." (`PAP:480`).
- legacy: partly, `TimeCounterManager` capped at 50 years (`legacy/firmware/python/CommonDrivers/async_manager.py:6,
  22-27`). form: design (one constant). depends: none. cost: ≈4 changed lines; nothing at run time.
- class **R**. scheme: none (claims P1).

### A-B2 The shared scalars lose their `asyncio.Lock`
- where: `:247-306`. what: `LockedCounter`/`LockedFlag`/`LockedValue` no longer acquire a lock (no method awaits).
  commits `41b47f1d`. origin: A.U10.17/A.U10.18 (M.SRC_CORE.031). evidence **H** (reading: no await inside).
- legacy: no, legacy locks each (`async_manager.py:8-66`). form: design (simplification). depends: none.
- cost: −3 lines of locking, −1 `Lock` per instance, fewer awaits per access.
- class **H**; triage *implausible* as a gap (nothing interleaves either way); a removal, neutral to keep or revert.
  scheme: none (claims P6).

### A-B3 `HourlyWindowCounter`: drops in the last 24 h, 24 hourly bins
- where: `:80-81`, `:309-349` (≈41 lines). what: the webserver's `HTTPDropped` counts the last 24 h, hourly
  resolution, no allocation per event or read. commits `f5c82557`. origin M.SRC_CORE.133.
- evidence **O**: OR137 "I would like the idea of showing the last 24h sliding through ... Maybe something like using
  24 hourly counter bins, shifting through, with 1h resolution" (`PAP:544`); tag "(owner, 2026-10-01)" `:312`.
- legacy: no. form: design. depends: A-B1. cost: one 24-int list per instance (one instance, the webserver); per
  drop/read ≤ 24 bin writes. class **R**. scheme: none.

### A-B4 `TickSeconds`: elapsed seconds measured from `ticks_ms()` deltas
- where: `:351-379` (≈29 lines). what: uptime-type values are measured time, not a count of 1 s wakes (a coalesced or
  dropped wake no longer loses a second). commits `41b47f1d`. origin A.U10.02 (D4.36).
- evidence **O**: OR101 "My decision: Fix the bugs, and make sure the fix of (4) does not depend on a UTC timestamp
  (ant not on UTC at all)" (`PAP:472`); OR104 "the "never UTC" goes for the others as well" (`PAP:478`).
- legacy: no, legacy counts wakes (`legacy/firmware/python/CommonDrivers/system_service.py:76-81`). form: design.
- depends: none; used by A-S19 and by WiFi/NTP (other groups). cost: per read one `ticks_ms()` and integer
  arithmetic, no allocation. class **R**. scheme: none.

### A-B5 `utc_now()`/`set_utc_valid()`: every timestamp is None until the NTP client set the clock this boot
- where: `:381-388`, `:785-788`. what: one UTC primitive; it answers None until a sync set the RTC, then stays valid
  for the boot (a stale sync keeps it). commits `41b47f1d`, `656fc82f` (stale clock).
- evidence **O**: OR104 "...might be a good candidate for a function which lives in the system service or the base
  classes" (`PAP:478`); owner 2026-10-21 "Clock time: Option b, but with a flag in /status showing it might be
  stale..." (`ORL:15`). The `OverflowError` catches it replaced were unreachable on target (A.U10.06, G4/R15).
- legacy: partly, a timestamp only while `ntp_is_synced()` (`system_service.py:84-85`). form: design. depends: none.
- cost: ≈9 lines; a module bool. class **R**. scheme: none.

### A-B6 `arm_tick_timer()`: one 1 s tick starter, a refused arm answered False
- where: `:390-402` (≈13 lines). what: the three 1 s tick timers (uptime, WiFi uptime, NTP age) arm through one helper;
  a refused arm returns False (the caller degrades), its `MemoryError` text printed at every level, a re-arm inside an
  episode quiet. commits `41b47f1d`, `06a8ae5d` (console arm), `72b12815` (quiet).
- origin: A.U10.03 (RF262: "the ENOMEM degrade is worded three ways"), OF-88 (console), OF-29 (quiet). evidence **H**.
- legacy: no, legacy arms unguarded (`system_service.py:29-30`). form: design for the consolidation; the console and
  quiet arms are patches around a print and a flood. depends: the console arm on A-P12.
- cost: −2 duplicate starters, +13 lines. class **H**; triage *implausible*: V6 refutes alarm-pool exhaustion in normal
  operation (≤ 12 `Timer` objects on the largest device, ≈ 8 armed at steady state, pool of 16, only `machine.Timer`
  draws on the default pool in `ports/rp2`). scheme: claims P4 (one material); the console/quiet arms rest on HYP.

### A-B7 One per-module lock (`_set_lock`) serialises a module's config PUTs and GETs
- where: `:431`, `:446-485`, `:493-557`. what: one PUT to a module at a time, and a GET reads all of a module's
  fields between PUTs, never torn. commits `8d44fd14` (PUT), `f5c82557` (GET).
- origin: A.U11.27 (CORE.S05), A.U19.12 (C15). evidence **O**: OR71 "... 8. b" with OR71.a (8) "a live-readback
  `GET /sensors` reads all of a module's fields in one step, so a concurrent PUT cannot tear it" (`PAP:412-413`); the
  PUT half is OR37.a (2)'s race audit ("1. yes 2. yes 3. yes, all exactly like this.", `PAP:343`) on a read finding.
- legacy: partly, one file lock per store (`async_manager.py:101-187`), no module lock. form: design.
- depends: none (A-S9's flush takes it, A-C14). cost: one `Lock` per module; a PUT holds it across its pushes (OF-27:
  a push that never returns queues later PUTs, the watchdog's case). class **R**. scheme: none.

### A-B8 A config GET answers `{"error": "unavailable"}` when the store could not be read
- where: `:446-484`, `:814-818`. what: an unreadable store or a failing callback sends the marker, not a map of nulls
  or of defaults. commits `f5c82557`, `9bf22747` (constant), `f76385a6` (`writable`). origin: U19 subject "the
  unavailable marker on unreadable config", OF-91, OF-94. evidence **H** (scan).
- legacy: partly, legacy answered ERR code 4 "Internal config read error" (`api_helpers.py:11-12`); the pre-audit
  `src/` had lost that signal (it sent nulls).
- form: design. depends: A-C1 (`writable`). cost: ≈8 lines, no run-time cost.
- class **K**: the finding (a read failure reported as values) is real against legacy parity; triage *implausible* as
  a frequent trigger (an unreadable file at boot). scheme: claims FEAT (legacy reported it).

### A-B9 A module's PUT answers every key "Failed" once a system command is accepted
- where: `:497-499`, `:749-751`, `:829-831`. what: from a command's acceptance nothing writes flash or a chip.
  commits `f76385a6`. evidence **O**: tag "(owner, 2026-10-02)" `:499`; OR140.a (12) "no SCD30 write can happen while a
  system-command sequence runs" (integrated text, `PAP:551`).
- legacy: no. form: design. depends: A-S7/A-S9 (the commands). cost: ≈7 lines; one bool check per PUT.
- class **R**. scheme: none.

### A-B10 A PUT stages, pushes, then releases one flash write after the pushes
- where: `:493-557`, `:585-587`, `:820-827` (with A-C11). what: the config file is written once, after the live
  pushes and any failed-push recovery, never before them. commits `8d44fd14`. origin A.U11.28 (RF208: "a failed push
  spends up to two flash writes for no net change"). evidence **H** (reading).
- legacy: yes, legacy wrote once after the setters (`api_helpers.py:140-157` after `set_sensor_value()`).
- form: design. depends: none; A-C11 and A-C16 exist for it. cost: ≈12 lines here, an `Event` per store.
- class **H**; triage *implausible* (a push failing during a PUT; at most two extra writes). scheme: claims P9; CAS
  (A-C11, A-C16 follow).

### A-B11 The pre-write snapshot covers only keys with a push callback
- where: `:500-511`. what: a PUT reads back old values only for fields a failed push could recover (SCD30's chip
  store pays no second read). commits `f44b9411`. origin A.U4.03 context. evidence **H**.
- legacy: n/a. form: design (optimisation). depends: none. cost: fewer reads per PUT, 3 lines.
- class **H**; triage *implausible* as a gap (an optimisation). scheme: none.

### A-B12 A failed-push recovery checks its own write
- where: `:701-704`. what: a recovery the store refused prints one console line. commits `8d44fd14`. origin
  A.U11.27 ("the recovery's own result is checked, not discarded"). evidence **H**.
- legacy: no (`api_helpers.py:162-195` writes without a check). form: patch (print only). cost: 3 lines.
- class **H**; triage *implausible* (print only). scheme: MIN.

### A-B13 The recovery ladder: device rung, bus clear, controller re-init, then the task end
- where: `:100-110`, `:567-583`, `:589-628`, `:640-660` (≈75 lines). what: a reader's 2nd failed cycle runs its
  chip's own recovery, the 3rd clears the bus, the 4th and later re-initialise the controller, each once per episode
  and once per bus; a failed `_init_*()` clears and rebuilds the bus before the restart budget. commits `cbb65df2`
  (`5689e2f4` per driver). origin A.U10.R01 (SUPP_recovery).
- evidence **O**: OR113 "always try to solve / recover from issues with the smallest possible blast radius ...
  escalating up to a full bus reset is absolutely allowed if the mild measures don't work out. Apply this idea
  throughout!" (`PAP:496`); tag "(owner, 2026-09-30: smallest blast radius first; thresholds agent, 2026-09-30)" `:101`.
- legacy: no, legacy gives up after `max_i2c_err` (`asy_scd30_driver.py:119-123`). form: design.
- depends: `I2C.clear()`/`recover()` (bus group). cost: ≈75 lines, 3 `@tunable`s; per failed cycle at most one rung
  (bus transactions), ≤ 3 persisted warnings per episode. class **R** (thresholds agent-set). scheme: none; MIN asks
  whether the per-bus episode bookkeeping (`_bus_mark`, `recoveries`) is the smallest form.

### A-B14 A refused read-trigger arm is persisted once, ends the task, and the restart re-arms
- where: `:412-444`, `:630-638`, `:717-747` (≈35 lines). what: a sensor whose trigger timer could not be armed no
  longer stays untriggered for the boot silently. commits `5689e2f4`, `06a8ae5d` (`_rearm_timer`). origin A.U15.41
  (G5/R09), OF-50. evidence **H** on the principle OR31.a "make sure the tasks themselves are written such that they
  either really work or return / end in any other case which cannot be handled internally" (`PAP:331`).
- legacy: no (unguarded arm). form: design. depends: none. cost: ≈35 lines; one None check per wake.
- class **H**; triage *implausible*: V6 (no pool exhaustion in normal operation). scheme: HYP; claims OR31.a.

### A-B15 `_republish()`: the last sample again with named fields changed, one hold
- where: `:709-715`. what: SCD30 republishes its FRC readiness without overwriting a concurrent store. commits
  `5689e2f4`. origin A.U15.12 (OR98.a, owner 2026-09-29, SCD30 group). evidence O (through its user).
- form: design. depends: SCD30 FRC readiness (other group). cost: 7 lines; one namedtuple per call.
- class **C** (root: SCD30 FRC readiness, other group). scheme: none.

### A-B16 `setup()` sets up the logger first and answers bool
- where: `:779-783`, `:846-850`. what: every reader's logger store is set up inside the boot batch; `setup()` answers
  readiness. commits `41b47f1d`. origin A.U10.10/A.U10.21. evidence **O**: OR47 "Ensure that the startup procedures
  in the system service do queue correctly, ensure a guaranteed fixed order for the FRAM chunk allocations"
  (`PAP:365`) with OR47.a (2) "every chunk setup (`pr.setup()`) moves into the one-time boot `setup()` batch".
- legacy: partly (`fram.setup` in `async_onetime`, `legacy/firmware/modules/sensortask-wozi.py:542`). form: design.
- cost: 3 lines. class **R**. scheme: none.

### A-B17 SCD30's config store logs RAM-only
- where: `:791-792`, `:809-811`. what: no extra FRAM chunk for `CFGMGR_SCD30`. commits `5689e2f4`. evidence **O**:
  tag "(SCD30, owner, 2026-09-29: 'no extra FRAM chunk')" `:791`. legacy: n/a. form: design. cost: 3 lines.
- class **R**. scheme: none.

### A-B18 `RegionBuffer`: the buffer's unused lock goes; a failed allocation prints its text
- where: `:144-171`. what: one `Lock` less per FRAM chunk buffer (built per chunk operation); a heap failure prints one
  ungated line. commits `2977c4e0`, `f1f800e7` (print). origin A.U16.05 (unused lock), SF-M3-06 /
  M.SRC_CORE.027 (1) (print). evidence **H**.
- legacy: n/a. form: design (lock), patch (print for the gates). depends: the print on A-P12.
- cost: −1 `Lock` allocation per chunk operation (a P6 gain); +3 lines. class **H** (lock: neutral simplification;
  print: C of A-P12). scheme: claims P6; the print claims the memory gates (CLAUDE.md:395-), P4 tension (exists for the
  test tiers' gates).

### A-B19 `PieceBuffer`: received bytes in pieces of at most `piece_bytes`
- where: `:174-244` (≈71 lines; `read_at()` `:204-217`, `trim()` `:219-229`). what: a UART train with no caller
  destination is assembled in pieces; no receive allocation exceeds one piece. commits `c11ca0aa`, `3a24c773`
  (`read_at`), `1d2b3cca` (callers catch its `MemoryError`).
- evidence **O**: OR143 "a reasonably defaulted chunk size constructor argument which limits the maximum size of
  contiguous allocations ... shall be added here as well" (`PAP:556`); tag "(owner, 2026-10-05)" `:176`; the catch
  "Do option (c) as you recommended" (owner, 2026-10-27, `ORL:97`).
- legacy: no. form: design. depends: the UART caps (UART group); `read_at()` exists for the dev echo (UM2).
- cost: ≈71 lines; per received train ⌈n/piece_bytes⌉ allocations. class **R** (`read_at()`: C, root the dev link's
  echo). scheme: none.

### A-B20 `reset_error_counter()` answers bool and re-arms the ladder
- where: `:771-777`. what: `ResetErrors` reports a store's failed reset per field. commits `8d44fd14`, `cbb65df2`.
  evidence **O**: OR70 "6. a" (`PAP:410`), OR70.a (6) "a `ResetErrors` whose `_write()` reports a detected failure
  answers "Failed" for that field". cost: 2 lines. class **R**. scheme: none.

### A-B21 Removed: `_checked_write_results()` (a runtime dict check of a typed return)
- where: was base `:241-246` and its two calls. what: a malformed `_set_mgr_cfg()` shape is no longer checked at run
  time. commits `7008730e`. evidence **O**: owner 2026-10-27 "if the check you remove really solely covers typing
  breakages and nothing else it can go (option b)" (`ORL:91`). cost: −10 lines. class **R**. scheme: claims TYP, D2.

### A-B22 `report_if_fatal()` in 9 handlers of this file
- where: `:131`, and the broad `except`s in `_get_dict_cfg`, `_set_dict_cfg`, `_climb_ladder`, `_recover_failed_push`.
  what: a caught C-stack overflow is recorded for the supervisor. commits `06a8ae5d`. origin A.U30.19. evidence H.
- class **C** (root A-S15). cost: 9 calls, no allocation. scheme: CAS, HYP (root unverified).

### A-B23 The base band of the global error catalog
- where: `:83-98`. what: codes 1-9 unchanged; new E14 CALLBACK, E17 TIMER, W14/W15 recovery. commits `43aced07` and
  later. evidence **O**: OR28 "Globally harmonize errno and wrnno numbers." (`PAP:324`). class **R**. cost: none.

## src/asy_system_service.py (was src/system_service.py)

Checked for non-changes: attribute renames and privatisation, the typing aliases, `@tunable` tags (the values
`_RESET_DELAY` 4, `_TASK_CHECK_TIME` 2, `_NTP_WAIT_TIME`, the budget numbers are unchanged since `25caf528`), the
`config_filename()`/`instance_name()` name building (same file name), D.15 order, the header rewrite. None counted.
`asyncio.sleep(1.0 / n)` → `sleep_ms(1000 // n)` at the task-start spread (A.U31.17) rounds a fraction of a
millisecond down; not counted.

### A-S1 The reset-reason record in `mem_backup()` region 0, published as `ResetReason`
- where: `:82-96`, `:137-143`, `:183-186`, writes in `_reboot()`/the gate/the escalation. what: every intended reset
  writes its code (3 reboot, 4 bootloader, 5 task budget, 6 reset arm failed, 7 config reset, 8 FRAM erased, 9 command
  incomplete) into RAM that survives the reset; the next boot reads, clears and publishes it. commits `8d44fd14`,
  `f76385a6`. origin A.U11.05, A.S0930.15 (M.SRC_CORE.006).
- evidence **O**: OR60 "b, but don't use FRAM, as it's optional. Micropython 1.29 offers a special RAM storage area
  surviving reboots ... integrate it into the system service and its endpoints (e.g. "reset_reason" with a
  corresponding number code)" (`PAP:390`).
- legacy: no. form: design. depends: none. cost: ≈40 lines; 3 RAM word stores per reset, one read and clear at boot.
- class **R**. scheme: none (claims P7).

### A-S2 The boot-phase marker in region 1: a reset during boot reads 10 + phase
- where: `:105-110`, `:148-170`, `:690-692`. what: each boot-phase transition stores its index; a watchdog reset before
  `BOOT_DONE` decodes as a boot failure with its phase. commits `8d44fd14`. origin A.U11.06.
- evidence **O**: OR102 "6. a, bot only if this is possible with the special RAM section, and for sure without flash
  writes and without FRAM. If not, leave it silent." (`PAP:474`).
- legacy: no. form: design. depends: A-S1. cost: ≈15 lines; 3 word stores × 6 transitions per boot. class **R**.
  scheme: none.

### A-S3 A console soft reset keeps the last hard reset's cause
- where: `:154-166` (the decode order in `begin_boot()`). what: under a power-on cause a valid record or an in-boot
  phase marker is read first, so a Ctrl-D/`mpremote` soft reset keeps the earlier code. commits `5f63546e` (F4d),
  `c60d1ae2` (F4e).
- evidence **O**: Q4 "B is fine, very rare edge case"; Q9 "Option b, should be in line with the prior similar
  decision" (`ORL:67`, `ORL:74`); tag "(owner, 2026-10-26)" `:156`.
- legacy: no. form: design. depends: A-S1, A-S2. cost: 0 run-time cost (the checks reordered). class **R**. scheme:
  none.

### A-S4 `ResetBits`: the chip's raw reset flags, read once at boot
- where: `:99-104`, `:145`, `:156`, `:678-679`. what: `/status` shows the WATCHDOG REASON and CHIP_RESET bits
  undecoded. commits `cbb65df2`. origin SF-A10 (`audit/REGISTER.md:114` "exposing them is the one way they reach a
  reader"). evidence **H**.
- legacy: no. form: design (diagnostic). depends: none. cost: ≈8 lines; two `mem32` reads per boot.
- class **H**; triage *implausible* as a gap (diagnostic only; OF-40: it cannot tell a soft from a hard reset anyway).
  scheme: MIN (a diagnostic field from a scan).

### A-S5 Loop-end codes 21 (Ctrl-C) and 22 (any other exception after boot)
- where: `:97-98`, `:173-180` (and the generated boot entry). what: an exception ending the event loop records its own
  code before the watchdog resets; during boot it writes nothing. commits `f76385a6` (21), `16121317` (22, F4b).
  origin SF-A14 (`REGISTER.md:115`), F4b "(agent, 2026-10-26)". evidence **H**.
- legacy: no. form: design (diagnostic). depends: A-S1. cost: ≈10 lines here, a clause in the boot entry; runs once.
- class **H**; triage *implausible* (without it the next boot reads 2, watchdog; nothing else changes). scheme: MIN.

### A-S6 One awaited reset path: record, flush every store, pause storage, arm, starve until it fires
- where: `:351-377`, `:421-431`. what: every reset (commands and the supervisor) writes its code, awaits the config
  flushes, pauses FRAM, then a one-shot sets a flag a task waits on (final flush, then the reset); a second request
  never postpones an armed reset; nothing feeds during the countdown, so a dropped one-shot still ends in a watchdog
  reset; a refused arm records 6 and starves. commits `8d44fd14`, `f76385a6`. origin A.U11.03/A.U11.04, A.S0930.33
  (D4.04 "supervisor reboot skips the config flush", D4.11 "ends `main()` 4 s early").
- evidence **O**: OR101 "My decision: Fix the bugs" (`PAP:472`, D4.04/D4.11 among the twelve); OR69 "1. a"
  (`PAP:408`) with OR69.a (1) "a commanded reboot loses nothing".
- legacy: partly: pause, then a one-shot reset; no flush, no record, a repeat re-arms (`system_service.py:35-51`).
- form: design. depends: A-S1. cost: ≈40 lines; per reset one task, one one-shot timer, the flush awaits.
- class **R**. scheme: none.

### A-S7 One command gate for the four system commands
- where: `:379-419`. what: the same command under way answers True and starts nothing; any other command, or one
  while a reset is armed, is refused and changes nothing; acceptance records 9, closes every store and starts the
  shutdown task. A raising preflight restores the gate (`:394-397`). commits `f76385a6`, `ad1fae73` (BR2).
- evidence **O**: OR119 "The commands must fit and sync into the system flow, they might occur in any state and must
  take care not to break anything except what can be expected by the erase operation." (`PAP:508`); OR126 "(3)
  reboot and bootloader on the controlled shutdown sequence: "a"" (`PAP:522`). The BR2 restore is H (raising walk:
  the erase preflight's coroutine raising), class C.
- legacy: partly, reboot/bootloader called directly (`legacy/firmware/modules/sensortask-wozi.py:520-529`).
- form: design. depends: A-S9. cost: ≈40 lines; one `Lock`; one task per accepted command. class **R** (BR2 restore
  `:394-397`: **C**, root this gate). scheme: none (BR2: HYP, CAS).

### A-S8 Two new system commands: "Reset to defaults" and "Erase FRAM"
- where: `:126-134`, `:694-696`, `:735-736` (+ the sequence, A-S9). what: `SystemCmd` gains the two words. commits
  `f76385a6`. evidence **O**: OR117 "To the system commands (currently reboot or bootloader, as far as I remember), I
  want to have added: "Reset to defaults" (...) and "Erase FRAM", which plainly clears the whole chip." (`PAP:504`);
  OR124 "Yes, option a." (Wi-Fi included, `PAP:518`).
- legacy: no (reboot, bootloader, mempause only: `sensortask-wozi.py:519`). form: design. cost: ≈15 lines here.
- class **R**. scheme: FEAT is changed by the owner's own request (not a violation).

### A-S9 The controlled shutdown sequence
- where: `:442-501` (≈60 lines). what: park and cancel the supervisor and prove it stopped, close and flush every
  store, quiesce FRAM, cancel every supervised task, delete the config files or erase FRAM, then the reset; fed once
  per bounded step; a hung step is never fed. commits `f76385a6`. origin A.S0930.13/14.
- evidence **O**: OR119 "shut all down controlled, erase, reboot" (`PAP:508`); OR120 "Probably it's best to
  completely stop the loop feeding the watchdog, really making sure it actually IS stopped, and feeding it inside the
  sequence doing the reset work." (`PAP:510`); tag "(owner, 2026-09-30)" `:443`.
- legacy: no. form: design. depends: A-S7, A-S10, A-S12, A-M13, A-C14/15. cost: ≈60 lines; one task per command;
  per step one feed. class **R**. scheme: none.

### A-S10 Watchdog ownership: once a command is accepted only the sequence feeds
- where: `:274-276`, `:346-349`, `:697-702`. what: `feed_watchdog()` becomes a no-op one-way; the sequence feeds through
  its own `_own_feed()`. commits `f76385a6`. evidence **O**: OR120 (as A-S9); tags `:221`, `:699`.
- legacy: partly, one feed site in the supervisor loop (`sensortask-wozi.py:605-607`). form: design. cost: ≈10 lines.
- class **R**. scheme: none.

### A-S11 `ResetErrors` is refused from any reset decision on
- where: `:222-225`, `:687-688`, `:728-733` (+ sets in the gate, the escalation and the supervisor's fault). what: the
  FRAM logs that explain a reset survive it. commits `72b12815`, `06a8ae5d`.
- evidence **O**: owner 2026-10-13 "1 b, 2 b" to "Clear nothing when ResetErrors answers Failed in mempause?" and
  "Refuse ResetErrors from the supervisor's own reboot decision too?" (U30 commit `06a8ae5d`); tag `:730`.
- legacy: no. form: design. cost: ≈8 lines. class **R**. scheme: none (claims P7).

### A-S12 The supervisor runs as its own task and parks for a command
- where: `:547-621` (frame), `:806-813`. what: `supervise_tasks()` spawns `_supervise()` so the sequence can cancel it
  and await it to done; a pass start parks once a command passed the gate. commits `f76385a6`. evidence **O**: OR120
  "really making sure it actually IS stopped" (`PAP:510`); OR120.a (1) "the task is cancelled and awaited to done".
- legacy: no, the loop is inline in `main()` (`sensortask-wozi.py:585-608`). form: design. cost: one task, two
  `Event`s, ≈15 lines. class **R**. scheme: none.

### A-S13 Escalation at the first task end past the budget: feed once, starve, reboot through the reset path
- where: `:571-610`. what: past the budget the supervisor stops scanning, records 5, feeds once, stops feeding and
  arms the reboot with FRAM paused. commits `8d44fd14`, `72b12815`. origin A.U31.07.
- evidence **O**: OR130 "Watchdog feed: option a as recommended" (`PAP:530`).
- legacy: partly: past `_TASK_FAIL_MAX` legacy stops feeding (watchdog reset, FRAM unpaused, no record;
  `sensortask-wozi.py:597-607`); the pre-audit `src/` called `reboot_system()` and returned out of `main()` (D4.11).
- form: design. depends: A-S6. cost: ≈25 lines. class **R**. scheme: none.

### A-S14 The escalation's entry write is bounded to 1200 ms
- where: `:77`, `:591-602`. what: the reboot's log entry is cancelled after 1.2 s (and a `MemoryError` building it
  prints) so a lock left held cannot stop the reboot. commits `72b12815`. origin OF-222 (a C-stack overflow inside a
  lock's `release()` leaves the lock held, so the entry write waits for ever). evidence **H**.
- legacy: no. form: patch (a timed wait around one call, for a fault two levels removed). depends: A-S15.
- cost: ≈12 lines; one `wait_for_ms` per escalation, a 1200 ms `@tunable`.
- class **C** (root A-S15). triage of the root: unverified (V7). scheme: CAS, HYP, DELAY (a hardcoded timed wait,
  "a fifth of the 6 s").

### A-S15 A caught C-stack overflow escalates: the supervisor reboots with code 20 / E25
- where: `:96`, `:567-570`, `:589-593` (+ `report_if_fatal()` in 10 handlers here, 28 in group A, A-P14). what: a
  `RuntimeError("maximum recursion depth exceeded")` caught by any broad handler sets a flag; the supervisor's next
  pass reboots instead of scanning. commits `06a8ae5d`. origin A.U30.19 (LEAD/R06; OR26.a's raising-call method).
  evidence **H** (reading: "At HEAD the error is swallowed everywhere a broad handler sits above the overflow").
- legacy: no. form: design (a flag every handler sets). depends: none; it is the root of cascade 1.
- cost: ≈15 lines here, 28 `report_if_fatal()` calls in group A (124 references project-wide), a fatal flag; per
  caught exception one `isinstance` and string compare.
- class **H**; triage *suspicious* (concrete mechanism; a rare trigger with a severe consequence: a task that keeps
  re-entering an overflowing path). V7: **unverified**: the longest await chain is pinned at 28 levels
  (`SPECIFICATION.md:12237`) but "the per-level cost is owed to the flash tier" — only the board can tell whether 28
  levels come near 7,936 B. Hardware round HW2. scheme: HYP, CAS (the largest cascade in group A).

### A-S16 The supervisor's own exception is persisted (E115) and counts as a reset decision
- where: `:611-616`. what: a fault in the supervisor loop logs once before the unfed watchdog resets. commits
  `72b12815`. origin OF-26 (U11 scan). evidence **H**. legacy: no. form: design. cost: 5 lines.
- class **H**; triage *implausible* (the watchdog resets either way; only the entry is new). scheme: none.

### A-S17 Task names and `LastTaskEnd` in `/status`
- where: `:300-303`, `:316-321`, `:669-673`. what: the last supervised task to end, by name, with the uptime then.
  commits `970b63ba`. origin A.U32.06. evidence **O**: OR128 "(a) Yes: publish it as `LastTaskEnd` in `/status`."
  (`PAP:526`).
- legacy: partly, `Task_LastErr` (the index) (`sensortask-wozi.py:93, 496, 591`). form: design. cost: two fields,
  ≈10 lines, no allocation per end. class **R**. scheme: none.

### A-S18 A dead task's slot is emptied before the escalation; a returned task logs E44
- where: `:316-330`, `:577-583`. what: an ended task is awaited once, then its slot is None until a restart; a task
  that returned is logged like a raised or cancelled one. commits `8d44fd14` (slot), `65a0df3b` (E44). origin: U11
  commit "an escalating pass left it for later passes to await again"; A.U3.06. evidence **H**.
- legacy: no (legacy restarts in the same pass). form: patch for the slot (protects A-S13's break-out).
- cost: ≈6 lines. class **C** (root A-S13) for the slot; E44 **H** *implausible* (a supervised task never returns by
  design). scheme: CAS.

### A-S19 Uptime is measured; a status-task restart keeps uptime and the boot signature
- where: `:253`, `:511-545`, `:684-685`. what: `SysUptime` is `TickSeconds`; a supervisor restart of the status task no
  longer zeroes uptime and the signature (no faked reboot). commits `8d44fd14`. origin A.U11.01/A.U11.02 (D4.36,
  D4.20). evidence **O**: OR101 "My decision: Fix the bugs ..." (`PAP:472`).
- legacy: no, counted wakes, reset at task start (`system_service.py:76-81`). form: design. depends: A-B4.
- cost: ≈10 lines. class **R**. scheme: none.

### A-S20 An unarmed uptime tick falls back to 1 s sleeps, re-arms each pass, one E17 per episode
- where: `:304-305`, `:515-523`, `:633-637`. what: a refused uptime arm no longer leaves uptime and the signature
  unresolved for the boot. commits `8d44fd14`, `72b12815` (quiet). origin A.U10.03/G5/R09, OF-29. evidence **H**.
- legacy: no. form: patch (a fallback loop for a refused arm). depends: A-B6. cost: ≈12 lines.
- class **H**; triage *implausible*: V6. scheme: HYP.

### A-S21 The mempause auto-unpause is a deadline on the status pass, not a one-shot timer
- where: `:302-303`, `:525-531`, `:704-720`. what: the 300 s pause ends on the first 1 s pass after its deadline; it is
  refused while a command shuts down and never reopens a reset's pause; the deadline is cleared only after its unpause
  ran (BR2). commits `8d44fd14`, `f76385a6`, `a4f0ccea` (BR2). origin A.U10.15 (G5/R08: "today three callbacks do
  work"). evidence **H**.
- legacy: yes, the one-shot timer form (`system_service.py:53-67`).
- form: design for the deadline; the shutdown refusal and BR2's order are C. depends: A-S9 (refusal).
- cost: ≈15 lines; one ticks comparison per pass; one Timer less.
- class **H**; triage *suspicious* (a dropped one-shot leaves FRAM paused until reboot: evidence loss). V8:
  mechanism **confirmed** in the pinned source (`shared/runtime/mpirq.c:105` ignores `mp_sched_schedule()`'s False;
  `py/scheduler.c:163-180` drops when full; depth 8, `ports/rp2/mpconfigport.h:131`); the trigger needs a manual
  mempause expiring during a burst of ≥ 8 pending callbacks: frequency **unverified** (HW5). The refusal and BR2 parts:
  **C** (roots A-S9, the deadline). scheme: HYP, CAS.

### A-S22 The boot signature's flag is set with its value
- where: `:537-545`. what: a raising log line after the store no longer lets a restart draw a second signature.
  commits `8cf55c6b` (BR2). origin BR2 D3 (raising walk). evidence **H**. legacy: n/a. form: patch (one line moved).
- cost: 0 (a reorder). class **H**; triage *implausible* (`pr.one()` raising). scheme: none (tiny).

### A-S23 The boot setup list runs in one method, fed and collected after each setup
- where: `:738-746`. what: `run_setups()` awaits each `setup()`, feeds the watchdog, then the placement collect.
  commits `f76385a6`. origin A.U11.10. evidence **O**: OR84 "a sysfunct function which gets the list of the setup
  functions to be called, and all of the looping, collecting and feeding is done automatically." (`PAP:438`).
- legacy: partly, an unfed loop (`sensortask-wozi.py:570-573`). form: design. cost: ≈8 lines. class **R**. scheme: none.

### A-S24 `ConfigFaults` and `ConfigUnpersisted` in `/status`
- where: `:298-299`, `:647-652`, `:745`. what: the modules whose file was unreadable or damaged at boot, and those
  running on values the flash lacks. commits `f76385a6`. evidence **O** for `ConfigFaults`: OR138 "Unreadable or
  damaged files should be visible in some status field, not silently swallowed." (`PAP:546`); **H** for
  `ConfigUnpersisted` (OF-91's U20 routing).
- legacy: no. form: design. depends: A-C3, A-C5. cost: ≈8 lines; a list built per `/status` read (unpersisted).
- class **R** (`ConfigFaults`); **H** *implausible* (`ConfigUnpersisted`: a failed config write). scheme: none.

### A-S25 `start_tasks()` installs SYSTEM's report as the asyncio exception handler
- where: `:776-779`. what: a task dying unawaited is reported by SYSTEM's level-gated line instead of asyncio's
  default print (which keeps ≈ 3 KB alive). commits `8d44fd14`. origin OF-25. evidence **H**.
- legacy: no. form: design. depends: A-P13. cost: 3 lines. class **H**; triage *implausible* as a gap. Owner ruled its
  level-0 silence: Q6 "Option a" (`ORL:70`). scheme: none.

### A-S26 Read triggers start from one shared start in task context; other timers first
- where: `:785-804`. what: the 1 s non-sensor timers start unstaggered; the read triggers start at t0 + k·slot,
  waited in the task on a one-shot that only sets a flag; a refused stagger arm sleeps instead. commits `41b47f1d`.
  origin A.U10.12 (G5/R07-R09). evidence **H** under the owner's intent OR47 "the sensor timer starters will be
  started in a way that prevents race conditions / timers firing at the same time" (`PAP:365`), which the pre-audit
  chain already met (even spread over 1 s).
- legacy: partly, a chain of one-shots from callbacks (`sensortask-wozi.py:100-109`). form: design.
- cost: ≈20 lines; one one-shot per trigger at boot. class **H**; triage *implausible* (a dropped callback during boot
  stalls the chain: V8's mechanism, at boot only). scheme: none.

### A-S27 A raising timer starter is persisted (E40)
- where: `:433-440`. what: was a print. commits `41b47f1d`. evidence **H**. cost: 2 lines. class **H** *implausible*.
  scheme: none.

### A-S28 `W69 CONFIG_LOST`: a missing settings file beside surviving FRAM history
- where: `:757-760`. what: a filesystem reformat by the stock `_boot.py` leaves one warning. commits `8d44fd14`. origin
  `REGISTER.md:123` ("makes a previously silent fault visible"). evidence **H**.
- legacy: no. form: patch (an inference from two flags). depends: A-C4, A-P2's `restored`.
- cost: ≈5 lines. class **H**; triage *implausible* (a reformat); OF-184: every scratch build writes a false W69 into
  the production SYSTEM history. scheme: HYP; P7 (it plants entries that read as evidence).

### A-S29 Providers resolved in `setup()`; an unreadable settings store keeps the constructed level
- where: `:748-765`. what: level setters and config stores come from providers; the persisted level applies only when
  the store is readable. commits `c3df14e1`, `8d44fd14`. origin A.U11.12 ("owner requirement: system-wide, but no
  shared mutable value (owner, 2026-08-11)" for the registry, pre-existing). evidence **H** (the unreadable half).
- cost: ≈6 lines. class **H** *implausible*. scheme: none.

### A-S30 `report_if_fatal()` in 10 handlers of this file
- class **C** (root A-S15). cost: 10 calls. scheme: CAS, HYP (root unverified).

### A-S31 Removed: `get_debug_level()`, `set_debug_level()`, `set_level_setters()`, `stop_uptime_timer()`
- what: caller-less public methods go. commits `8d44fd14`, `c3df14e1`. evidence **O**: OR46.a (2) "confirmed leftovers
  … are removed" (quoted in A.U16.21); OR36 "contains zero artifacts specifically added for testing" (`PAP:340`).
- cost: −≈15 lines. class **R**. scheme: claims P4.

### A-S32 `pause_permanent_storage()` is refused during a shutdown and answers bool
- where: `:704-707`. class **C** (root A-S9). cost: 2 lines.

### A-S33 SYSTEM's codes on the global catalog; the dynamic `wrnno = n + 1` retired
- what: E40-E44, E115, W69; one entry per task end (A.U3.06). commits `43aced07`, `65a0df3b`. evidence **O**: OR28
  (`PAP:324`); OR35.b for the single entry. class **R**. cost: none.

## src/asy_config_manager.py (was src/config_manager.py)

Checked for non-changes: the result words as constants (A.U19.16), `config_filename()` (A.U11.32, same name),
`checked_int`/`checked_float`/`checked_numeric` replacing `coerce_numeric()` with the same acceptance rule, the
`write_config()` signature losing `cfg_vals` (every caller passed the store's own schema), attribute renames, D.15
order, comment moves. `compare_before_write()` (U4) is a new shared primitive, but `write_config()`'s outcomes are
unchanged by it (OR42.c (4) "file-backed modules unchanged in behaviour"); listed once as A-C21.

### A-C1 An unreadable file is never overwritten; writes are refused until the next boot
- where: `:329`, `:563-571`, `:616-618`. what: an I/O error or a `MemoryError` reading the file no longer reads as
  "absent" and triggers a rewrite with defaults; the store serves defaults RAM-only and refuses PUTs. commits
  `8d44fd14`. origin A.U11.20 (G5/R34).
- evidence **O**: OR70 "3. a (never write without user / api interaction as a standing rule)" (`PAP:410`); OR136.a (2)
  "Unchanged: an unreadable or corrupt file is never overwritten" (integrated, `PAP:543`).
- legacy: no, legacy rewrote defaults on any read failure (`legacy/firmware/python/CommonDrivers/async_manager.py:
  118-131`). form: design. depends: none. cost: ≈8 lines, one flag. class **R**. scheme: none (claims P9).

### A-C2 A genuinely absent file is written once with defaults; a command-only schema creates no file
- where: `:539-546`, `:586-596`. what: absent (ENOENT) → one write at that boot; a schema with no stored values writes
  nothing (the pre-audit code wrote `{}`). commits `8d44fd14`.
- evidence **O**: OR136 "if the file is genuinely missing, it shall be written once with defaults." (`PAP:542`), its
  (3) "A command-only schema persists no field, so it has no file to write".
- legacy: partly, legacy wrote defaults whenever the file was missing or invalid (`async_manager.py:126-131`).
- form: design. cost: ≈6 lines. class **R**. scheme: none.

### A-C3 A damaged file is repaired once and listed as a fault
- where: `:530-532`, `:548-552`, `:573-585`. what: unparseable, not an object, or a stored value the schema refuses →
  repaired with defaults at that boot and the module named in `ConfigFaults`. commits `8d44fd14`, `f76385a6`.
- evidence **O**: OR138 "Unreadable or damaged files should be visible in some status field, not silently
  swallowed." (`PAP:546`); OR71.a (2) "a config file with a bad, missing or unknown key is repaired by at most one
  write per boot".
- legacy: partly, legacy rewrote silently (`async_manager.py:105-131`). form: design. cost: ≈8 lines. class **R**.

### A-C4 `absent_at_boot`
- where: `:331`, `:540`. what: feeds SYSTEM's W69. class **C** (root A-S28). cost: 2 lines. scheme: CAS.

### A-C5 `unpersisted`: a failed file write leaves the store listed
- where: `:333`, `:409-411`, `:433-434`, `:598-600`. what: feeds `ConfigUnpersisted` and the commanded reset's
  completeness (code 9). commits `8d44fd14`. evidence **H**. class **C** (roots A-S24's `ConfigUnpersisted`, A-S9's
  completeness). cost: 4 lines. scheme: CAS.

### A-C6 A run of failed reads persists one entry
- where: `:334`, `:345-375`, `:422-427`, `:439-456`, `:507-512`. what: a store invalid for the boot logs its first failed
  read, then stays quiet until a good read or a cleared history. commits `06a8ae5d`. origin U30 commit "A config
  store's or a reader's failed reads log once per episode"; OF-51 (console and count repeating per read cycle).
  evidence **H**.
- legacy: n/a (no histories). form: patch (an episode flag around four log calls). cost: ≈12 lines, one flag.
- class **H**; triage *implausible* (an invalid store; the newest-entry rule already spends no slot, only the console
  line and `ErrCount` repeat). scheme: **OR35b** violated (a per-module episode special case beside the global rule);
  MIN.

### A-C7 Typed getters validate the stored value by exact type
- where: `:74-108`, `:345-361`, `:436-468`. what: `get_int_values()` no longer `int()`-truncates a float or converts a
  bool; a wrong-type stored value persists E24 and answers None. commits `8d44fd14`. origin A.U11.29 (CORE.S12).
  evidence **H**.
- legacy: n/a. form: design. cost: ≈25 lines. class **X** (right intent: no silent cast; more code than needed):
  triage *implausible*: every cached value already passed the schema's own type check at `setup()` and at every write,
  so the per-read type check is unreachable with today's code. scheme: **TYP** (an unreachable check typing and the
  store's own validation cover), D2.

### A-C8 Floats are compared and staged in the form the file reloads as
- where: `:128-133`, `:625-627`, `:644-647`. what: a float PUT compares `json.loads(json.dumps(v))` with the stored
  value, so a repeat of the same value after a reboot answers "Unchanged" instead of writing again. commits `8d44fd14`.
  origin A.U11.21 (RF207). evidence **H**; OR42 "Check and search deeply for any situation which could do accidental
  heavy or even looped writes" (`PAP:352`) is the owner's audit order it answers.
- legacy: no. form: design. cost: ≈8 lines; per float field in a PUT one `dumps`+`loads` (small allocations).
- class **H**; triage *suspicious* (normal-operation trigger: the website re-sends unchanged numeric fields; P9 wear).
  V9: **unverified**: the Unix port's doubles round-trip, rp2's single-precision repr is the open point; it needs the
  on-device round-trip script the code comment names (HW3). scheme: claims P9.

### A-C9 The payload is serialised before the file is opened
- where: `:402-404`, `:429-434`, `:591-593`. what: `json.dumps()` first, then one `write()` of the text; a failure
  leaves the file as it was. commits `8d44fd14`, `656fc82f` (`_write_file()`, the single write kept). origin A.U11.23
  (G5/R35). evidence **H**.
- legacy: same latent form, `json.dump()` into an open "w" file (`async_manager.py:126-129, 178-180`).
- form: design. cost: ≈4 lines; the text is built whole (a config file is under 1 KB).
- class **K**; triage *suspicious* (rare trigger, severe consequence: a `MemoryError` mid-dump leaves a truncated file
  the next boot repairs to defaults, Wi-Fi included). V2: **confirmed**: a `json.dump()` that fails part-way leaves an
  unparseable 1,650-byte prefix and the old content is gone (3/3 runs). scheme: none (claims P2).

### A-C10 A flush equal to the file writes nothing
- where: `:399-400`. what: a staged snapshot equal to `_cache` skips the write. commits `8d44fd14`. origin A.U11.28
  (RF208, the failed-push recovery). evidence **H**. cost: 1 line. class **H** *implausible* (a failed push).
  scheme: claims P9.

### A-C11 Deferred flush: `write_config(defer=True)`, `commit()`, `_commit_ready`
- where: `:340-343`, `:391-394`, `:475-477`, `:662-666`. what: a PUT's flush waits for the reader base to commit after
  its pushes. commits `8d44fd14`. class **C** (root A-B10). cost: ≈10 lines, one `Event` per store. scheme: CAS.

### A-C12 A write stages only once its flush task exists
- where: `:643-661`. what: a `MemoryError` creating the flush task answers "Failed" with nothing staged, instead of
  serving a value that is neither in effect nor stored. commits `8d44fd14`. origin A.U11.22 (D4.35). evidence **H**.
- legacy: n/a (legacy wrote inline). form: design (an order). cost: ≈4 lines.
- class **K**; triage *suspicious* (rare trigger; the GET then shows a value the device does not use and will lose at
  reboot). V3: **confirmed** on the pre-audit code: `write_config()` answered `(False, {})`, `get_dict()` then served
  `{'X': 5}`, the file kept `{"X": 1}` (3/3 runs). scheme: none.

### A-C13 `write_config()` validates against the store's own schema
- what: an API change (`cfg_vals` dropped); no caller passed a different schema. commits `8d44fd14`. class **H**,
  *implausible* as a gap; no behaviour change today. cost: −1 parameter. scheme: none.

### A-C14 `close_writes()` / `writes_closed()`: a store closed for a commanded reset refuses every write
- where: `:336`, `:377-381`, `:470-473`, `:607-608`, `:619-620`, `:671-673`. commits `8d44fd14`, `f76385a6`.
  evidence **O** through its root (OR119; tag "(owner, 2026-10-02)" at the caller). class **C** (root A-S7/A-S9, both
  R). cost: ≈10 lines. scheme: none.

### A-C15 `delete_file()` for "Reset to defaults", unread, one retry
- where: `:479-496`. what: the file is removed whether readable or not; ENOENT counts as done; one retry on another
  `OSError`. commits `8d44fd14`. evidence **O**: OR138 "even such files must be deletable by the user when triggering
  the newly added "delete config" command" (`PAP:546`); tags `:480`.
- legacy: no. form: design (the retry: OR113's "retry the transaction"). cost: ≈17 lines. class **R**. scheme: none.

### A-C16 `flush_pending()` releases a deferred flush and reads the task under the lock
- where: `:498-505`. class **C** (roots A-C11, A-S9). cost: 3 lines. scheme: CAS.

### A-C17 The flush task's own top catches and persists (E23)
- where: `:413-420`. what: an unexpected raise in the flush task is persisted and marks the store unpersisted. commits
  `41b47f1d`. origin A.U10.20 (G5/R16). evidence **H**. cost: ≈7 lines.
- class **H**; triage *implausible* (the body already catches its file and serialisation errors). scheme: HYP.

### A-C18 The boot repair write takes the config lock
- where: `:592-593`. class **C** (root A-C15: the delete takes the same lock). commits `656fc82f`. cost: 1 line.

### A-C19 A directory at the file's path is a file fault
- where: `:556-559`. class **C** (root A-C3, R). cost: 1 line.

### A-C20 Removed: the schema helpers' `try/except` guards and `write_config()`'s bad-default abort
- what: malformed schemas are refused statically (`tests_scripts/test_config_schemas.py`), not at run time. commits
  `8d44fd14`. evidence **O**: "Per project owner feedback: don't guard against inputs violating their already-declared
  types" (owner, 2026-08-06, `b5502c8`, quoted in A.U11.17); D2. cost: −≈20 lines. class **R**. scheme: claims D2, TYP.

### A-C21 `compare_before_write()`: the one compare-before-write primitive
- where: `:193-232` (≈40 lines). what: shared by the file store and SCD30's chip store; for the file store the outcomes
  are unchanged. commits `f44b9411`. evidence **O**: OR42 "2. yes, but check again - as far as I remember, the current
  value inside the SCD30 storage is already checked and only written if different" (`PAP:353`). class **R** (its
  behaviour lands in the SCD30 group). scheme: claims Part G.

### A-C22 CFGMGR codes on the global catalog
- what: E20/E21/E23/E24/E30-E34, W10/W20-W23 (was E1-E15, W1-W6). commits `43aced07`. evidence **O**: OR28
  (`PAP:324`). class **R**. cost: none.

## src/asy_print_log.py (was src/print_log.py)

Checked for non-changes: `LogConfig`/`make_logger(log, name)` (one config object, A.U5.01), the print methods' explicit
`sep`/`end` keywords (typing), the `"<"` byte order of the history format (byte-identical on little-endian rp2,
A.U11.09), `_diag()` comments, D.15 order. None counted.

### A-P1 The newest-entry rule, in the logger itself
- where: `:186-197`, `:209-224`. what: a code equal to the history's newest entry is counted and written through but
  spends no slot, for every logger; callers no longer pass `repeat=`. commits `65a0df3b`, `f1f800e7`.
- evidence **O**: OR35.b "just don't repeat the same error in the slots. Pure and simple." (`PAP:339`).
- legacy: n/a. form: design. depends: none. cost: ≈12 lines; one compare per entry. class **R**. scheme: none.

### A-P2 Entries logged before `setup()` survive it
- where: `:155`, `:186-197`, `:398-437`. what: the stored ring is restored first and the pre-setup entries appended as
  newest, counts added. commits `41b47f1d`, `2977c4e0`, `06a8ae5d`. origin A.U10.11 (CORE.S03/S04). evidence **H**.
- legacy: n/a. form: design. cost: ≈20 lines. class **H**; triage *implausible* (entries before `setup()` occur only on a
  construction fault). scheme: claims P7; HYP.

### A-P3 A history that cannot reach FRAM records it: `LOG_RAM_ONLY` (E28)
- where: `:76`, `:229-239`, `:398-437`. what: the first failed write of a run, an unreadable store at setup, a heap
  failure of its chunk and a failed setup write each leave one counted RAM entry. commits `f1f800e7`, `2977c4e0`,
  `06a8ae5d`. origin OF-61, SF-B12, SF-M1-03. evidence **H**.
- legacy: n/a. form: design. cost: ≈20 lines, one flag. class **H**; triage *implausible* (a failing FRAM after boot;
  the FRAM layer's own entries already show it). scheme: claims P7; HYP.

### A-P4 An unreadable store keeps its bytes and runs RAM-only for the boot
- where: `:312-331`, `:409-416`. what: `setup()` re-initialises only a store proven blank or invalid; a read fault no
  longer writes the current ring over the stored history. commits `2977c4e0`. origin A.U16.06 (G5/R25). evidence
  **H**.
- legacy: n/a. form: design. depends: A-M3 (the chunk's tri-state). cost: ≈12 lines here.
- class **K**; triage *suspicious* (rare trigger, P7 consequence: the one diagnostic record a reboot keeps is
  overwritten, `CLAUDE.md`'s FRAM-evidence rule). V11: **confirmed by reading** the pre-audit `setup()`: `if await
  self._read() or await self._write():` (base `print_log.py:273-279`) writes after any failed read, fault or not; the
  trigger (a fault on both copies while the chip is up) is rare and unmeasured. scheme: claims P7.

### A-P5 After a valid read, `setup()` writes back only when pre-setup entries were merged
- where: `:414-419`. class **C** (root A-P2: the merge would otherwise double every logger's boot traffic, 97 against
  47 CS cycles, `REGISTER.md:488`). Against the pre-audit code (a clean read wrote nothing) there is no net change.

### A-P6 `ResetErrors` on a FRAM store: refused under a pause; the cleared image is written before RAM clears
- where: `:304-310`, `:362-396`. what: a refused or failed reset write leaves RAM, the count and the chip as they were;
  "Failed" means nothing was cleared. commits `06a8ae5d`.
- evidence **O**: owner 2026-10-13 "1 b, 2 b" ("Clear nothing when ResetErrors answers Failed in mempause?"), and
  2026-10-20 "I would like it to be fixed now, and your proposal without extra allocation sounds promising, check if
  this works and implement it accordingly" (U30 commit `06a8ae5d`); tag `:364`.
- legacy: n/a. form: design. cost: ≈25 lines; the image is packed into the chunk's own buffer. class **R**.

### A-P7 Overlapping resets on one logger each keep their own window
- where: `:72-73`, `:157-165`, `:167-208`, `:362-396` (≈40 lines of state). what: up to 29 concurrent `reset()`s each
  keep what arrived after they began, a repeat of the newest code marks every reset begun, a 30th is refused.
  commits `656fc82f`. origin OF-221 ("read from the code at the close, not run"; U35 R-10). evidence **H**.
- legacy: n/a. form: patch (a bit-set protocol for one race). depends: A-P6, A-P1.
- cost: ≈40 lines, five wrapping counters/bit sets per logger; per entry two counter steps.
- class **X** (and **C** of A-P6 + A-P1); triage *implausible*: two `ResetErrors` at once on one logger, the newest
  code repeating between their starts, and a pause on the later write. scheme: **HYP, CAS, MIN, P6**.

### A-P8 One write lock and a generation count: the newest state lands last
- where: `:300-302`, `:333-360`. what: a write whose state an earlier write already landed skips; the packing happens
  under the lock. commits `1cff5a26`. origin A.U14.19 (RF203: "relies on FIFO hand-off (FIFO in practice at v1.29.0)").
  evidence **H**.
- legacy: n/a. form: design. cost: ≈10 lines; one `Lock` per FRAM-backed logger. class **H**; triage *implausible*:
  the finding itself states the lock hand-off is FIFO at the pinned version, so the newest state already landed last.
  scheme: HYP.

### A-P9 An empty warning slot reads 0, not 128; a negative code is diagnosed
- where: `:247-249`, `:219-221`. commits `43aced07`. evidence **H**. cost: 2 lines. class **H** *implausible* (0x80
  is never stored: a warning number 0 records nothing). scheme: none.

### A-P10 `set_level()` refuses an invalid level and answers bool
- where: `:85-110`. what: was clamped. commits `8d44fd14`. origin A.U11.13 (RF162). evidence **H**. cost: ≈6 lines.
- class **H**; triage *implausible* (REST range-checks `DebugLevel`; constructors get generated values). scheme: none.

### A-P11 `console()` and the at-every-level `MemoryError` line
- where: `:456-463`, `:91-101`, `:153-154`, `:291-298`, `:328-330`, `:356-358`. what: one ungated print; a caught
  `MemoryError` handed to any gated log call prints its text at every level. commits `f1f800e7`, `06a8ae5d`,
  `68224efb` (F3r). origin: the memory gates read printed text (CLAUDE.md:395-; SPEC I.4(e)); OF-77, OF-88, F3r.
  evidence **H**.
- legacy: no. form: design for `console()`; `_line()`'s scan is a patch around the gated levels.
- cost: ≈20 lines; per gated call below its level one loop over the arguments; OF-83: a line can hold the loop up to
  500 ms behind an unread USB host.
- class **C** (root: the test tiers' memory gates). triage *implausible* as a device gap. scheme: **P4** (product output
  that exists for the test gates), CAS (A-B18, A-F2, A-B6, A-S14, A-M10 follow), MIN.

### A-P12 `report_unretrieved()`: SYSTEM's asyncio exception handler
- where: `:124-137`. what: a task ending raised with nobody awaiting it prints one gated line and drops its context.
  commits `8d44fd14`. origin OF-25. evidence **H**; its level-0 silence is ruled: Q6 "Option a" (`ORL:70`).
- cost: ≈14 lines. class **H** *implausible* as a gap (asyncio's default handler prints the same, keeping ≈ 3 KB).
  scheme: none.

### A-P13 `report_if_fatal()`, `fatal_reported()`, `_fatal`
- where: `:80-81`, `:466-488`. class **H** (the root of cascade 1, A-S15; V7 unverified). cost: ≈12 lines. scheme: HYP.

### A-P14 The chunk request names its owner
- where: `:294`. class **C** (root A-M1). cost: 1 argument.

### A-P15 The FRAM allocator's refusal records nothing; a heap failure of the chunk records E28
- where: `:289-298`, `:400-405`. commits `f1f800e7`, `2977c4e0`. evidence **O** for the refusal: (owner, 2026-09-16:
  'we do not even add errno/wrnno for the out of FRAM memory … Handle via mpremote.') `:402`; **H** for the heap half.
- cost: ≈8 lines. class **R** (refusal); the heap half **H** *implausible*.

### A-P16 Removed: `get_level()` and the six static level accessors
- commits `8d44fd14`. evidence **O**: OR36 "contains zero artifacts specifically added for testing" (`PAP:340`).
  cost: −≈25 lines. class **R**. scheme: claims P4.

## src/asy_fram_manager.py

Checked for non-changes: class renames (`AsyFramManager` → `FRAMManager`, `_AsyBaseFramChunk` → `_FRAMBaseChunk`,
buffers), chunk construction from the manager (A.U5.13, same state), private attributes, the timestamped chunk's
bool-first result tuple (an API reorder, its caller moved with it), D.15 order (`fccb464d`), the comment on the
differing-copies rule. None counted.

### A-M1 Each chunk's CRC is seeded by its owner's name
- where: `:68-77`, `:99-100`, `:316`, `:425`, `:692-718`, `:736-773`. what: after a reflash that shifts the layout by
  whole chunks, a chunk another owner wrote fails its CRC and reads blank, never as this owner's history. commits
  `2977c4e0`. origin SF-B1 (`REGISTER.md:825`), minimal form under OR149 "the fixes required for such reliability (if
  required at all, if not already safe inherently) are minimal, low complexity" (`PAP:570`). evidence **H**.
- legacy: n/a (legacy chunks carry no CRC and no logs).
- form: design (no new bytes). depends: none; A-P14 and SGP40's `owner=` follow. cost: ≈14 lines; per chunk operation
  the seed passed as `init=`.
- class **K**; triage *suspicious* (a trigger every layout-changing reflash produces; consequence: one module's FRAM
  history shown under another's name, the evidence `CLAUDE.md`'s FRAM rule says to read first). V5: **confirmed** on
  the pre-audit code: with the first of two equal-size chunks dropped from the layout, the second owner's new chunk
  read `b'L1-history!!'` as valid (3/3 runs). The owner's 2026-10-26 rule fits it: "If things happen at first boot,
  they must be triggered by evidence (e.g. no config available, FRAM image does no longer fit the layout)"
  (`ORL:48`). scheme: claims P7.

### A-M2 A blank block takes no busy marker on read
- where: `:133-134`. what: reading a never-written block leaves it blank, so a second read again reports
  "uninitialised" instead of "invalid". commits `2977c4e0`. origin A.U16.09 (STOR.S01). evidence **H**.
- legacy: **same defect in the field firmware**: legacy writes BUSY to the first status byte after reading UNINIT and
  returns without restoring (`legacy/firmware/python/IndividualDrivers/asy_fram_manager.py:288-307`).
- form: design (2 lines). cost: −2 CS cycles on a blank read.
- class **K**; triage *suspicious* (normal operation: any chunk read twice before its first write, e.g. a backup chunk
  across reboots on a fresh or erased chip). V1: **confirmed** on the pre-audit code: after one read both status bytes
  were BUSY (2, 2); the second read logged E31, W71, E31, W72 in the FRAM history and read invalid (3/3 runs).
  scheme: none.

### A-M3 The chunk read is tri-state: valid, blank or invalid, not read
- where: `:113`, `:122-147`, `:174-190`, `:217-275`, `:347-355`. what: a fault (bus, guard, status transfer) is told
  apart from bad content; a fault without a valid copy beside it returns None and the stored bytes are kept; the log
  store's setup keeps them (A-P4). commits `2977c4e0`. origin A.U16.06 (G5/R25, RF167). evidence **H**.
- legacy: no. form: design. depends: none. cost: ≈25 lines of fault flags across four methods.
- class **K** (V11, through A-P4); MIN asks whether the four flag sites are the smallest form. scheme: claims P7.

### A-M4 A blank verdict asks the chip's RDID first
- where: `:149-154`. what: an undriven bus reads 0x00, the blank status value; before reporting blank, one RDID tells
  a lost chip apart. commits `656fc82f`. origin OF-167. evidence **H**.
- form: patch (a probe on one path). depends: A-D1. cost: 6 lines; one RDID per blank read.
- class **C** (root A-D1). scheme: CAS, HYP.

### A-M5 Every chunk operation is silent while the chip is lost
- where: `:217-219`, `:375-377`, `:447-449`, `:461-465`. class **C** (root A-D1). cost: ≈8 lines; one `is_set()` per
  operation. scheme: CAS.

### A-M6 The chip watch: a declared chip that never set up escalates; a lost one is set up again
- where: `:670-690`, `:825-834` (`initialized`). what: the FRAM manager has a supervised task that ends at once when a
  declared chip failed setup (the supervisor then restarts it and reboots past its budget) and that waits on `lost`
  otherwise. commits `2977c4e0`. origin A.U16.17, A.U16.R03.
- evidence **O**: OR89 "5. the same as all other chips" (`PAP:448`); tag `:672`.
- legacy: no, a dead chip runs RAM-only (`asy_fram_manager.py:25-30`; the pre-audit `src/` the same).
- form: design. depends: A-D1 for the re-setup half. cost: ≈20 lines; one task per device; a dead declared FRAM now
  reboots the unit at each budget exhaustion instead of running RAM-only (the owner's "same as all other chips").
- class **R** (the re-setup of a lost chip: **C**, root A-D1). scheme: none.

### A-M7 A chunk write reads block 1's status pair first and writes a non-idle copy first
- where: `:375-391`, `:406-421`. what: one 2-byte READ picks the first block, so two cuts in a row can no longer leave
  both copies BUSY and lose the store. commits `656fc82f`. origin OF-255 (U35 G2/G3).
- evidence **F** + **O**: a cancel sweep failed on the pre-audit order from a BUSY start state, "cancelled after 1
  turns: from start (1, (2, 2)): blocks [0, 1] both left BUSY" (`audit/artefacts/evidence/U35_close/lead/handbacks/
  G3_final.md:4`, run on `069b9fe`, whose `_write()` still had the pre-audit order, block 0 then block 1; a
  constructed start state, no bench or field observation); owner 2026-10-22 "Solutions you proposed
  agreed." (U35 commit `656fc82f`).
- legacy: no, fixed order 0 then 1 (`asy_fram_manager.py:143-161`). form: design.
- cost: ≈12 lines; +1 CS cycle per chunk write; a 2-byte buffer per chunk. class **R**. scheme: none (claims P7).

### A-M8 Removed: the per-chunk episode warnings (`_episode_wrn`, `_WRN_EPISODE_BASE`)
- commits `65a0df3b`. evidence **O**: OR35.b (`PAP:339`). cost: −≈12 lines. class **R**. scheme: claims OR35b.

### A-M9 Without its check buffer a read returns block 0 unchecked and leaves block 1; one ALLOC entry
- where: `:174-180`, `:248-262`. commits `06a8ae5d`. origin OF-63. evidence **H**. cost: ≈8 lines.
- class **H**; triage *implausible* (an 8-byte allocation at construction). scheme: HYP.

### A-M10 The read's data copy degrades to "not read" on a `MemoryError`
- where: `:192-200`. commits `7ceb50b2` (BR3). origin BR3's raising walk. evidence **H**. cost: 9 lines.
- class **H**; triage *implausible* (a chunk-sized copy failing). scheme: HYP; MEMC is met (a true degrade path).

### A-M11 A missing buffer persists ALLOC instead of a silent False
- where: `:500-526`, `:571-653`. commits `65a0df3b`, `7ceb50b2`. origin A.U3.09. evidence **H**. cost: ≈10 lines.
- class **H** *implausible*. scheme: HYP.

### A-M12 Erase FRAM: blank every chunk, then zero the chip in fed 256-byte units
- where: `:39`, `:461-471`, `:780-808`. commits `2977c4e0`. evidence **O**: OR117 ""Erase FRAM", which plainly clears
  the whole chip" (`PAP:504`); tag `:781`. legacy: no. form: design. cost: ≈40 lines; one 256 B buffer per erase.
- class **R**. scheme: none.

### A-M13 `quiesce()` / `wait_idle()`: the chunk layer closed for a command
- where: `:473-477`, `:814-820`. commits `8d44fd14`. class **C** of A-S9 (R): evidence O by its root (OR119 "shutting
  down all processes and write access to any storage"). cost: ≈10 lines.

### A-M14 `erase_ready()`: the driver ready, the chip not lost, not write-protected
- where: `:810-812`. commits `2977c4e0`, `c56b366b`, `d4c51d7b` (F2r: "no in-tree path opens the window").
  class **C** (roots A-M12, A-D1). OF-250 stays open. cost: 2 lines. scheme: CAS.

### A-M15 The timestamped chunk stamps through `utc_now()`; its unreachable catches go
- where: `:571-653`. what: no timestamp before the clock is set this boot; the `mktime()` `OverflowError` and the
  pack/unpack catches are removed. commits `41b47f1d`, `2977c4e0`. evidence **O** (OR104, as A-B5; the removals:
  G4/R15 unreachable on target and the owner's 2026-10-27 rule, `ORL:93`). cost: −≈10 lines. class **R**.

### A-M16 A paused or refused read answers None (not read)
- where: `:227-229`. class **C** (root A-M3). cost: 0.

### A-M17 Removed: the `override_pause` test seam, the chunks' `get_size()`/`get_pause()`, `get_crc_buf()`
- commits `2977c4e0`. evidence **O**: OR36 "contains zero artifacts specifically added for testing" (`PAP:340`);
  OR46.a (2). cost: −≈25 lines. class **R**. scheme: claims P4.

### A-M18 `report_if_fatal()` in 6 handlers
- class **C** (root A-S15). cost: 6 calls. scheme: CAS, HYP (root unverified).

### A-M19 FRAM codes on the catalog; the chunk layer keeps its own entry
- what: E100-E106 beside the driver's own; W63 block invalid. commits `43aced07`, `2977c4e0`. evidence **O**: OR140.a
  (7) "every layer that meets a fault keeps its own persisted entry, as today" (`PAP:551`); OR28. class **R**.

## src/asy_fram_driver.py

Checked for non-changes: the SPDX header form, the folded opcode bytes (`_CMD_*` as `const`), the four removed unused
`_SPI_OPCODE_*` constants, `session_lock`, the `@tunable` `_VERIFY_PRESENT_LOCK_TIMEOUT_MS` (1.0 s → 1000 ms, same
wait), `wait_for` → `wait_for_ms`, the method reorder. None counted.

### A-D1 A lost chip is found on the write path and stops FRAM access
- where: `:64`, `:85`, `:104`, `:114`, `:141-151`, `:212-226`, `:255-259`, `:360-372`. what: two write-latch
  anomalies in a row, or a status byte with bit 0 set (both datasheets fix it at 0), trigger one RDID; a silent chip
  sets `initialized` False, persists E54 once and sets `lost`. commits `2977c4e0`. origin A.U16.R03.
- evidence **H** under the owner's principle OR113 ("Apply this idea throughout!", `PAP:496`) and OR89 "5. the same
  as all other chips" (`PAP:448`): the finding is the reading "a silent SO reads back a constant status byte ... 0xFF
  — the payload is then reported as landed" (SUPP_recovery A.U16.R03).
- legacy: no (`asy_fram_driver.py:111-127` checks nothing). form: design. depends: none; the root of cascade 2.
- cost: ≈35 lines; a counter and an `Event`; a clean write reads no extra byte.
- class **H**; triage *suspicious* (rare trigger, severe consequence: writes reported as landed on a dead chip). V10:
  **unverified**: whether an absent chip's SO reads 0x00 (RP2040 pad pull-down, OF-167) or 0xFF (a breakout pull-up)
  decides between "refused with a warning" (no silent loss) and "reported as landed"; MB85RS64V p.10 gives SO High-Z
  with CS high. Hardware round HW1. scheme: HYP, CAS.

### A-D2 One WREN retry
- where: `:95`, `:238-246`. what: a write-enable latch that did not set gets one more WREN (each its own CS cycle).
  commits `2977c4e0`. evidence **O**: OR113 "retry the transaction" as the ladder's first rung (`PAP:496-497`); its
  WRDI twin already retried once. legacy: no. cost: ≈6 lines; one extra WREN+RDSR on a fault only.
- class **R**. scheme: none.

### A-D3 `setup()` identifies the chip up to three times
- where: `:82`, `:451-470`. what: a single disturbed RDID at boot no longer fails setup (which A-M6 would turn into
  a reboot); a retry leaves W29. commits `2977c4e0`. evidence **O**: OR113 (`PAP:496`; A.U16.R02 "retry … at boot and
  mid-operation"). legacy: no, one try (`asy_fram_driver.py:39-47`). cost: ≈8 lines. class **R** (also C of A-M6).

### A-D4 A partly protected status register is reported (E53) and counts as protected
- where: `:64-68`, `:465-476`. commits `2977c4e0`. origin A.U16.15 (G5/R29). evidence **H**. cost: ≈8 lines.
- class **H**; triage *implausible* (the firmware only writes all-or-nothing and no product path calls
  `set_write_protected()`). scheme: HYP.

### A-D5 A bus that is not initialised fails every entry point (E52)
- where: `:103`, `:112`, `:334-335`, `:366-367`, `:384-388`, `:410-411`, `:432-434`, `:453-454`, `:492-494`.
  commits `cbb65df2`. origin A.U13.09 (G3/R20). evidence **H**.
- cost: ≈12 lines; one attribute read per operation. class **X**; triage *implausible*: a bus that failed construction
  fails `setup()`, after which the existing NOT_INIT guard refuses every call. scheme: claims D2's "a wrapper whose bus
  is not initialised answers None/False"; MIN.

### A-D6 `setup()` and `set_write_protected()` take the driver lock too
- where: `:374-383`, `:457-463`. commits `2977c4e0`. origin A.U16.10 (the owner's one-hold-per-block-operation model,
  2026-09-18). evidence **H**. cost: 2 lines.
- class **H**; triage *implausible* (setup runs alone in the boot batch; `set_write_protected()` has no product caller).

### A-D7 A write-protection readback mismatch persists the error, never the warning too
- where: `:392-397`. commits `2977c4e0`. evidence **O**: OR56 "Either it's a fault or a warning, but never both at a
  time." (`PAP:382`). cost: 0 (an order). class **R**.

### A-D8 The WP pin is driven to its level before its direction
- where: `:477-478`. commits `2977c4e0`. evidence **H**. class **H** *implausible* (no generated device passes
  `wp_pin`). cost: 1 line.

### A-D9 `verify_present()` reports a lost chip; its unreachable ID-error branch goes
- where: `:485-510`. commits `2977c4e0`. class **C** (root A-D1) for the report; the removal **R** (unreachable, the
  2026-10-27 rule, `ORL:93`). cost: ±0.

### A-D10 `is_ready()`
- where: `:351-353`. commits `d4c51d7b`. class **C** (root A-M14). cost: 3 lines.

### A-D11 `report_if_fatal()` in `__aexit__`
- class **C** (root A-S15). cost: 1 call. scheme: CAS, HYP (root unverified).

### A-D12 FRAM driver codes on the catalog
- commits `43aced07`. evidence **O**: OR28 (`PAP:324`). class **R**.

## src/asy_api_response.py (was src/api_response.py)

Checked for non-changes: the typed envelope, the `_RequestLike` stand-in, `_UNKNOWN_DESCR`. None counted.

### A-A1 `handle_set_cmd()` returns per-field results; a raising post-write hook fails its group
- where: `:55-74`. what: the endpoint answers OK with per-field words; a hook that raises persists E14 and marks every
  key of the group "Failed"; `_set_dict_cfg()` (never-raise) is no longer wrapped. commits `8d44fd14`, `f5c82557`.
  origin A.U11.26. evidence **O**: OR69 "4. a (res not \"OK\" means that the request itself was broken, not invalid
  content)" (`PAP:408`).
- legacy: partly: a raising hook propagated to Microdot; a write failure answered code 5 (`api_helpers.py:135-157`).
- cost: ≈15 lines. class **R**. scheme: none.

### A-A2 One envelope code catalog
- where: `:35-46`. what: codes 2-5 and 100 go (no producer left), 400/404/405/413/500 are the shaped HTTP errors.
  commits `f5c82557`, `15b8633c`. origin A.U19.15. evidence **O**: OR69 (4) (`PAP:408`); OR58.a "The refactor's API ...
  is the only reference" (`PAP:387`). legacy: partly (0-10, `api_helpers.py:162-177`). class **R**. cost: 0.

### A-A3 Removed: `parse_cmd_request()` (no caller)
- commits `15b8633c`. evidence **O**: OR46.a (2) "confirmed leftovers … are removed". cost: −≈17 lines. class **R**.

### A-A4 `report_if_fatal()` in the hook handler
- class **C** (root A-S15). cost: 1 call. scheme: CAS, HYP (root unverified).

## src/asy_crc_checks.py (was src/crc_checks.py)

Checked for non-changes: class renames (`CRC_Base` → `CRCBase`, `CRC_Pass` → `CRCPass`), private state, `_crc()`
taking the checked polynomial (typing), D.15 order. None counted.

### A-K1 CRC32 runs as two 16-bit words
- where: `:16`, `:38-62` (`_crc_wide()`, ≈22 lines). what: a 32-bit register no longer leaves rp2's small-int range,
  so the bit loop allocates nothing; output identical. commits `2949ed97`. origin A.U12.01 (D4.43: "~6,000 per
  256-byte SGP40 chunk"). evidence **H**.
- legacy: n/a (legacy has no CRC32). form: design. depends: none. cost: ≈22 lines; 416 B per call against 160 B on the
  Unix port (`REGISTER.md:339`), the rp2 figure owed to the board.
- class **K**; triage *suspicious* (normal operation: every SGP40 VOC backup and restore runs CRC32 over 256 B). V4:
  **confirmed** from the pinned source: rp2 is `MICROPY_OBJ_REPR_A` (`ports/rp2/mpconfigport.h:163`), whose small ints
  are 31-bit signed on a 32-bit word (`py/smallint.h:39-42`), so a register value ≥ 2**30 is a heap integer at every
  shift and xor. Consequence: transient churn once per backup period, none of the brief's severe classes; HW4 would
  measure it. scheme: claims the memory rule (churn of same-shaped objects); MIN asks whether 22 lines are warranted.

### A-K2 Pass mode checks bounds like real mode
- where: `:116-128`, `:143-158`. what: `add_into()`/`check_from()` in pass mode refuse a zero, negative or overrunning
  size. commits `2949ed97`. origin A.U12.02. evidence **H**. cost: ≈4 lines.
- class **H**; triage *implausible* (every caller passes a fixed, valid size). scheme: none.

### A-K3 An out-of-range polynomial degrades every width field to pass-through
- where: `:25-35`. commits `656fc82f`. origin M.SRC_CORE.131 ("(lead, 2026-10-01: ... flagged, not merged)").
  evidence **H**. class **H** *implausible* (no such construction exists). cost: ±0.

### A-K4 Removed: two unreachable `pack_into` `ValueError` catches
- commits `656fc82f`. evidence **O**: owner 2026-10-27 (`ORL:93`). cost: −≈6 lines. class **R**. scheme: claims TYP.

## src/asy_framing_codecs.py (was src/framing_codecs.py)

Checked for non-changes: class renames, private tunables, D.15 order, the header pointers. None counted.

### A-F1 COBS decoding accepts the encoded worst case of a full frame
- where: `:92-97`, `:102-104`. what: a codec sized to the frame no longer refuses every full-size frame. commits
  `c11ca0aa`. origin A.U17.22 (G6/R16 RF215: "latent while production selects `Framing_Pass`"). evidence **H**.
- legacy: n/a. cost: 4 lines. class **H**; triage *implausible* on these devices: no generated device selects
  `FramingCOBS`. scheme: none.

### A-F2 A failed scratch allocation prints its text
- where: `:86-89`. commits `06a8ae5d`. origin OF-77. class **C** (root A-P11). cost: 2 lines. scheme: CAS, P4.

### A-F3 Removed: the test-only `allocations` counter
- commits `2949ed97`. evidence **O**: OR36 (`PAP:340`). cost: −2 lines. class **R**.

## src/math_helpers.py

Checked for non-changes: `altitude_baro()` → `pressure_at_height()` (rename, one caller), the function reorder, the
McCamy span comment, the unquoted return annotations, the catch tuple order. None counted. Note: `abs_humidity()` and
`rel_humidity()` have no caller in `src/` or the generated modules, so A-H2..A-H4 change nothing a device does today.

### A-H1 The wet bulb is refused in Stull's cold-dry corner
- where: `:20-23`, `:213-231`. what: `WetBulb` is None below the line (−20 °C, 75 %)–(10 °C, 5 %). commits
  `2949ed97`. origin A.U12.06 (Stull 2011, Fig. 3). evidence **H**: no owner text names it; A.U12.06 cites OR101.a, whose
  G3/R06 item is D4.64 (`MeanAtmTemp`), not the corner (`PAP:473`).
- legacy: no, legacy accepts it (`legacy/firmware/python/CommonDrivers/math_helpers.py:7`). form: design. cost: 6 lines.
- class **H**; triage *implausible* on these devices: all six are rooms (arzi, dev, grkizi, klkizi, schlafzi, wozi),
  the corner needs < 10 °C. scheme: **D1** (real output changed without an owner decision), MIN.

### A-H2 The ≥ 0 °C Magnus water pair is 7.5/237.3 (legacy 237.4)
- where: `:55-75`, `:162-176`. commits `2949ed97`. evidence **O**: (owner, 2026-10-07: 'Adapt the humidity to the
  verified range') `:58`. legacy: changed from `math_helpers.py:46-50, 59-63`. cost: 2 constants. class **R**.

### A-H3 `rel_humidity()` refuses a result outside 0-100 % instead of clamping
- where: `:157-176`. commits `2949ed97`. evidence **O**: OR140.a (4) "`abs_humidity()`/`rel_humidity()` stay ("useful,
  complete the functional suite, small, lightweight"), their tests aligned with the other helpers' and the helpers with
  the no-clamp rule" (`PAP:551`). legacy: clamps (`math_helpers.py:65-66`). cost: 3 lines. class **R**.

### A-H4 A saturated reading's 0.001 % rounding step above 100 % is accepted
- where: `:38-39`, `:172`. commits `2949ed97`. origin `REGISTER.md:332` ("the inverse of a 100 % reading lands one
  rounding step above 100 and was refused"). class **C** (root A-H3). cost: 2 lines. scheme: CAS.

# Per-file totals

Rows and code lines per class (a row split between two classes counts in each; lines are net, removals negative).

| file | R | K | H | X | C |
|---|---|---|---|---|---|
| asy_base_classes.py | 13 rows, 230 | 1, 8 | 7, 66 | 0 | 3, 30 |
| asy_system_service.py | 17, 281 | 0 | 14, 100 | 0 | 6, 39 |
| asy_config_manager.py | 7, 59 | 2, 8 | 5, 28 | 1, 25 | 7, 31 |
| asy_print_log.py | 4, 16 | 1, 12 | 8, 88 | 1, 40 | 3, 27 |
| asy_fram_manager.py | 7, 20 | 3, 41 | 3, 27 | 0 | 7, 37 |
| asy_fram_driver.py | 5, 6 | 0 | 4, 46 | 1, 12 | 3, 8 |
| asy_api_response.py | 3, −2 | 0 | 0 | 0 | 1, 1 |
| asy_crc_checks.py | 1, −6 | 1, 22 | 2, 4 | 0 | 0 |
| asy_framing_codecs.py | 1, −2 | 0 | 1, 4 | 0 | 1, 2 |
| math_helpers.py | 2, 5 | 0 | 1, 6 | 0 | 1, 2 |
| **group A** | **60, 607** | **8, 91** | **45, 369** | **3, 77** | **32, 177** |

Scheme violations per file (rows naming the rule as violated; one row may name several):

| file | HYP | CAS | MIN | P4 | other |
|---|---|---|---|---|---|
| asy_base_classes.py | 3 | 2 | 2 | 1 | — |
| asy_system_service.py | 7 | 6 | 2 | 0 | DELAY 1 (A-S14), P7 1 (A-S28) |
| asy_config_manager.py | 1 | 4 | 1 | 0 | OR35b 1 (A-C6), TYP 1 and D2 1 (A-C7) |
| asy_print_log.py | 5 | 2 | 2 | 1 | P6 1 (A-P7) |
| asy_fram_manager.py | 5 | 4 | 1 | 0 | — |
| asy_fram_driver.py | 3 | 2 | 1 | 0 | — |
| asy_api_response.py | 1 | 1 | 0 | 0 | — |
| asy_crc_checks.py | 0 | 0 | 1 | 0 | — |
| asy_framing_codecs.py | 0 | 1 | 0 | 1 | — |
| math_helpers.py | 0 | 1 | 1 | 0 | D1 1 (A-H1) |
| **group A** | **25** | **23** | **11** | **3** | DELAY 1, P7 1, P6 1, OR35b 1, TYP 1, D2 1, D1 1 |

Most violated, in order: **HYP** (25 rows: code standing on a scan finding nobody observed; 28 of the
`report_if_fatal()` sites alone hang on one unverified root), **CAS** (23 rows: additions that exist for other
additions), **MIN** (11), then P4 (3: product console output that exists for the test tiers' memory gates). The
owner-decided rows (R, 60) violate nothing. Three rows clash with a written owner rule: A-C6 with OR35.b's "no
per-module or per-episode special cases", A-C7 with the 2026-10-27 unnecessary-check rule (TYP), A-H1 with D.1's
"flag and ask before altering real output".

# Cascades

1. **C-stack escalation** (root A-S15/A-P13, H, V7 unverified) → `report_if_fatal()` in 28 handlers of group A (A-B22,
   A-S30, A-C17's catch, A-M18, A-D11, A-A4; 124 references project-wide) → the supervisor's stack branch (code 20,
   E25) → the 1200 ms bound on the escalation's entry write (A-S14, OF-222: a lock left held by an overflow inside
   its own `release()`) → that wait's `MemoryError` console arm. About 60 lines in group A for a trigger the board has
   not shown.
2. **Lost FRAM chip** (root A-D1, H, V10 unverified) → `lost` `Event` and E54 → every chunk operation silent while lost
   (A-M5) → the blank verdict's RDID probe (A-M4, OF-167) → the chip watch's re-setup of a lost chip (A-M6's second
   half) → `erase_ready()`'s chip checks (A-M14, F2r) → `FRAM_SPI.is_ready()` (A-D10) → `verify_present()`'s report
   (A-D9); OF-250 (erase readiness in the loss window) still open.
3. **Memory-gate visibility** (root: the test tiers read printed `MemoryError` text, A-P11) → `console()` lines in
   `RegionBuffer` (A-B18), `FramingCOBS` (A-F2), `arm_tick_timer()` (A-B6), the escalation entry (A-S14), the FRAM read
   copy (A-M10) and the logger's own allocations → `_line()` printing a caught `MemoryError` at every level (F3r) →
   OF-83 (a console line can hold the loop 500 ms behind an unread USB host, open).
4. **Deferred config flush** (root A-B10, H implausible) → `defer=`/`commit()`/`_commit_ready` (A-C11) →
   `flush_pending()` releasing it (A-C16) → `_commit_mgr_cfg()` in a `finally` for a cancelled PUT.
5. **ResetErrors under a pause** (A-P6, R) + **the newest-entry rule** (A-P1, R) → overlapping-reset bit sets, 29 in
   flight, a 30th refused (A-P7, X, OF-221).
6. **The shutdown sequence** (A-S9, R) → `owner_lock` on every store (A-B7, A-S9) → the boot repair write under the
   config lock (A-C18) → `close_writes()` (A-C14) → PUT refusal (A-B9) → mempause refused during a shutdown (A-S21,
   A-S32) → the gate's restore on a raising preflight (A-S7, BR2). All roots owner-decided; only the BR2 tail is H.
7. **The mempause deadline** (A-S21, H) → not reopening a reset's pause → BR2's "deadline spent only after its unpause".
8. **Escalation at the first end past the budget** (A-S13, R) → the dead slot retired before the break-out (A-S18).
9. **No-clamp `rel_humidity()`** (A-H3, R) → the 0.001 % rounding allowance (A-H4), found when a saturated inverse was
   refused.
10. **W69 CONFIG_LOST** (A-S28, H) → `absent_at_boot` (A-C4) and the logger's `restored` flag → OF-184 (false W69 in the
    production history after every scratch build).
11. **Tri-state chunk read** (A-M3, K) → the log store keeping an unreadable store's bytes (A-P4, K) → a paused read
    answering None (A-M16).
12. **Owner-seeded CRC** (A-M1, K) → `owner=` on every chunk request (A-P14, SGP40's call).
13. **Failed-read episode flag** (A-C6, H) → `reset_error_counter()` ending the run (config store) — the code that
    clashes with OR35.b.

# Verifications

Runs as the brief prescribes (`unshare -n S/u24/ns_xdg.sh nice -n 19`, RUNS.md lines "U35 scan A ..."), three runs
each, the pinned Unix port `build-standard`, `-X heapsize=16M`, `MICROPYPATH` = the pre-audit `src/` and `tests/`
extracted by `git archive 25caf528` into `S/u35r/scan/work_A/base/`. Scripts in `S/u35r/scan/work_A/scripts/`, logs in
`S/u35r/scan/work_A/logs/`.

- **V1** (A-M2) a never-written chunk read twice, pre-audit FRAM manager on the fake MB85RS64V:
  `v1_v5_fram_blank_and_shift.py`. Outcome **confirmed** (3/3): read 1 → None and block 0's status bytes left
  `(2, 2)` (BUSY); read 2 → None with `ErrNum [... 31, 71, 31, 72]` (E31 twice, W71, W72) in FRAM's history.
- **V2** (A-C9) a `json.dump()` failing part-way into an open "w" file: `v2_json_dump_truncation.py` (the failure is a
  nesting too deep for the C stack; an unserialisable object did not fail, MicroPython writes its repr). Outcome
  **confirmed** (3/3): the old `{"A": 1, "B": 2.5}` is gone, the file holds a 1,650-byte prefix that does not parse.
  On rp2 littlefs commits what was written at the `with`'s close, the same shape (the code's own note, lfs2.c:3473).
- **V3** (A-C12) a `MemoryError` creating the flush task, pre-audit `ConfigManager`: `v3_stage_before_task.py`.
  Outcome **confirmed** (3/3): `write_config()` → `(False, {})`, `get_dict()` → `{'X': 5}`, the file `{"X": 1}`.
- **V4** (A-K1) rp2 small ints, pinned source: `ports/rp2/mpconfigport.h:163` `MICROPY_OBJ_REPR_A`, `py/smallint.h:39-42`
  (31-bit signed on a 32-bit word). Outcome **confirmed**: a CRC32 register ≥ 2**30 is a heap integer; the pre-audit
  loop shifts and xors it per bit.
- **V5** (A-M1) a layout shifted by one equal-size chunk, pre-audit manager: same script. Outcome **confirmed** (3/3):
  the dropped owner's `b'L1-history!!'` reads as the next owner's valid data.
- **V6** (A-B6, A-B14, A-S20) alarm-pool exhaustion in normal operation: source and inventory. `machine.Timer` is the
  only default-pool user in `ports/rp2` (`machine_timer.c:107, 117`); `src/` constructs 12 `Timer`s on the largest
  device (dev: system 3, NTP 3, WiFi 2, SCD30, SGP40, BMP3XX, ISL29125), of which about 8 stay armed (the reset,
  sequencer, NTP-retry and hotspot timers are one-shots armed rarely); the pool holds 16 (SPECIFICATION.md:6336).
  Outcome **refuted** for normal operation.
- **V7** (A-S15) does the longest await chain come near the C-stack limit? The static chain is 28 levels and the limit
  7,936 B (`SPECIFICATION.md:6445-6452, :12237`); the per-level cost on rp2 is "owed to the flash tier". Outcome
  **unverified**: it needs the board's `c_stack_budget.py` reading (HW2).
- **V8** (A-S21, A-S6, A-S26) a soft one-shot's fire lost: pinned source `shared/runtime/mpirq.c:105` ignores
  `mp_sched_schedule()`'s result, `py/scheduler.c:163-180` returns False when the queue is full, depth 8
  (`ports/rp2/mpconfigport.h:131`). Mechanism **confirmed**; how often ≥ 8 callbacks wait at once on these devices is
  **unverified** (HW5).
- **V9** (A-C8) does a config float survive `json.dumps`/`json.loads` on rp2's single-precision build? The Unix port
  (doubles) cannot show it. Outcome **unverified** (HW3).
- **V10** (A-D1) what an absent FRAM chip's SO reads: MB85RS64V p.10 (High-Z with CS high), the RP2040 pad's reset
  pull-down (OF-167) versus a breakout pull-up. Outcome **unverified** (HW1).
- **V11** (A-P4) the pre-audit log store's setup after a failed read: by reading, base `print_log.py:273-279`
  `if await self._read() or await self._write():` writes the current ring after any failed read. Outcome **confirmed
  by reading**; the trigger (a fault on both copies while the chip answers) is unmeasured.

# Hardware-round list

- **HW1** FRAM: SO's level with the chip absent or lost on the bench board (decides A-D1 and its cascade).
- **HW2** C stack: `c_stack_budget.py` along the 28-level chain (decides A-S15 and cascade 1).
- **HW3** Config floats: the on-device `json` round trip of every float field's range ends (decides A-C8).
- **HW4** CRC32: `gc.mem_alloc()` around one 256-byte `CRC32().check_from()`, old and new loop (sizes A-K1's gain).
- **HW5** The scheduler queue: whether ≥ 8 soft callbacks queue at once, e.g. right after a long flash write
  (decides A-S21 and the reset path's starve, A-S6).
- Carried, not new: OF-40's soft-versus-hard reset bits (A-S4) and OF-83's console hold with an unread USB host.

# Minimal-change list (R and confirmed items), against the pre-audit code

Size in source lines; "as landed" where the landed form is already the smallest this lane sees; the pinning test is
an existing one at `497b3eda` where named, else what it would assert.

Confirmed hypotheticals (K):
- **A-M2** blank read takes no busy mark: in `_set_check_sb()`, return True on UNINIT before the BUSY write; 2 lines.
  Test `tests/test_asy_fram_manager.py::test_a_never_written_chunk_read_twice_reports_uninitialised_both_times`.
- **A-M1** owner-seeded CRC: a seed function and `init=` at the two CRC calls, `owner=` on the two chunk requests;
  ≈14 lines. Tests `test_asy_fram_manager.py::test_a_chunk_written_by_another_owner_reads_blank`,
  `tests_scripts/test_fram_chunk_owner_sites.py::test_every_owner_across_the_devices_has_its_own_seed_at_every_width`.
- **A-C9** serialise first: `text = json.dumps(x)` then `f.write(text)` at the flush and the setup write; 4 lines.
  Test `tests/test_asy_config_manager.py::test_a_failed_serialisation_leaves_the_file_byte_identical`.
- **A-C12** stage after the task exists: move `self._staged = new_cache` below `create_task()` inside the `try`;
  ≈3 lines. Test `test_asy_config_manager.py::test_a_failed_task_creation_stages_nothing`.
- **A-P4 + A-M3** keep an unreadable store: the chunk read returns None for a fault (one fault flag set where a status
  read, a guard or a block read fails, ≈10 lines), `setup()` skips the write on None (2 lines). Test
  `tests/test_asy_print_log.py::test_an_unreadable_store_keeps_its_bytes_and_stays_ram_only`.
- **A-K1** CRC32 in two words: `_crc_wide()`, ≈22 lines (or leave it: the cost is transient churn once per backup,
  HW4 would size it). Test `tests/test_asy_crc_checks.py::test_crc32_matches_the_mpeg2_check_value`.
- **A-B8** the GET's unavailable marker (legacy parity with code 4): `{name: {"error": "unavailable"}}` on a failed
  store read, ≈5 lines. Test: a GET of a module whose store could not be read answers the marker, not nulls.

Owner-decided (R), smallest form:
- **A-B1** cap: `COUNTER_CAP` and the default `max_val`; 2 lines. Test `test_asy_base_classes.py::
  test_increment_near_the_cap_stays_there`.
- **A-B3** `HourlyWindowCounter`: as landed, ≈35 lines (the owner specified the bins). Test `test_the_bins_shift_hour_by_hour`.
- **A-B4/A-S19** measured uptime, restart keeps it: for `SysUptime` alone ≈12 lines in the status loop (a `ticks_diff`
  accumulator kept on the service, not reset at task start); `TickSeconds` (29) only if WiFi/NTP adopt it too. Test:
  a restarted status task keeps uptime and signature (`test_asy_system_service.py`, the D4.20 regression).
- **A-B5** `utc_now()`: ≈9 lines. Test `test_utc_now_is_none_until_the_clock_is_marked_valid`.
- **A-B7** `_set_lock`: one `Lock` and two `async with` (≈4 lines). Test: a GET racing a PUT reads one side only
  (the C15 consistency test in `test_asy_webserver_service.py`).
- **A-B9** writes closed: ≈6 lines. Test `test_asy_config_manager.py::
  test_writes_closed_answers_whether_close_writes_or_delete_file_closed_the_store` with the reader-base PUT refusal.
- **A-B13** recovery ladder: ≈75 lines as landed; a smaller form would drop the cross-reader bus episode marks
  (`_bus_mark`) and run each rung per reader (≈55 lines), at the cost of two readers on one bus both clearing it.
  Test: the ladder cases in `test_asy_base_classes.py` (`:1301-`).
- **A-B16/A-B17/A-B20/A-B23, A-S33, A-C22, A-D12, A-M19** catalog and setup contracts: as landed.
- **A-B19** `PieceBuffer`: ≈45 lines without `read_at()`/`trim()`; those two (≈25) exist for the dev link's echo and the
  short train. Test `test_piecebuffer_holds_its_size_in_pieces_of_at_most_piece_bytes`.
- **A-B21, A-C20, A-K4, A-M15's removals, A-M17, A-P16, A-S31, A-A3, A-F3, A-D9's removal** removals: as landed
  (net −≈150 lines).
- **A-S1/A-S2/A-S3** reset record and boot phase: ≈55 lines. Tests `test_a_console_soft_reset_after_a_power_on_boot_
  reads_the_recorded_code`, `test_a_console_soft_reset_after_a_boot_phase_failure_reads_10_plus_the_phase`.
- **A-S6** one reset path: ≈40 lines. Test: a supervisor reboot flushes a staged config write before the reset (D4.04)
  and keeps `main()` running until it fires (D4.11).
- **A-S7/A-S8/A-S9/A-S10/A-S12** commands, gate, shutdown, feed ownership, supervisor task: ≈150 lines as landed
  (OR117-OR120 ask for each part). Tests `test_the_same_command_again_answers_true_and_any_other_answers_false`,
  `test_a_fault_in_a_shutdown_step_is_logged_and_the_watchdog_still_resets`.
- **A-S11** `ResetErrors` refused after a reset decision: ≈8 lines. Test: `ResetErrors` during an armed reset answers
  "Failed" and clears nothing.
- **A-S13** escalation, feed once: ≈25 lines. Test: the budget escalation feeds exactly once, then never.
- **A-S17** `LastTaskEnd`: ≈10 lines. Test `test_get_last_task_end_names_the_last_ended_slot_and_the_uptime_then`.
- **A-S23** `run_setups()`: ≈8 lines. Test `test_run_setups_awaits_in_order_feeds_after_each_and_collects_after_each_feed`.
- **A-S24** `ConfigFaults`: ≈4 lines. Test: a damaged file at boot lists its module in `ConfigFaults`.
- **A-C1/A-C2/A-C3** unreadable never overwritten, absent written once, damaged repaired and listed: ≈22 lines. Tests
  `test_an_absent_file_is_written_once_per_boot_and_never_again`, an unreadable file's bytes unchanged after boot.
- **A-C15** `delete_file()`: ≈12 lines without the retry, 17 with it. Test
  `test_delete_file_removes_an_unreadable_or_damaged_file_without_reading_it`.
- **A-C21** `compare_before_write()`: as landed (SCD30's write path needs it). Test: SCD30 writes only changed fields.
- **A-P1** newest-entry rule: ≈8 lines. Test: a repeated newest code spends no slot and is still counted.
- **A-P6** reset under a pause: ≈20 lines without A-P7's bit sets (one reset at a time, the write before the clear).
  Test `test_a_reset_while_storage_is_paused_clears_nothing_and_the_history_survives_the_pause`.
- **A-P15** allocator refusal records nothing: 1 line (no entry). Test: a refused chunk leaves no entry.
- **A-M6** chip watch for a declared chip that never set up: ≈8 lines (end at once when not initialised); the re-setup
  half belongs to cascade 2. Test `test_the_watch_task_ends_at_once_for_a_chip_never_set_up`.
- **A-M7** write order: ≈12 lines, +1 CS cycle per write. Test: a write from a BUSY block-1 pair writes block 1 first
  (the G3 order test in `test_asy_fram_manager.py`).
- **A-M12/A-M13** erase and quiesce: ≈45 lines. Test `test_erase_chip_zeroes_every_byte_in_ascending_units`.
- **A-D2/A-D3** WREN retry, ID retries: ≈14 lines. Tests: a disturbed first WREN still writes; an RDID that answers on
  the second attempt sets up with W29.
- **A-D7** one entry for a WP mismatch: an order. Test: a mismatch persists E45 and no W27.
- **A-A1/A-A2** per-field hook failure, one code catalog: ≈15 lines. Test `test_asy_api_response.py`'s raising-hook case
  (every group key "Failed", code 0, one E14).
- **A-H2/A-H3** water pair and no clamp: 5 lines (no caller today). Tests `test_abs_humidity_matches_hand_worked_values`,
  a `rel_humidity()` above 100 % answering None.
