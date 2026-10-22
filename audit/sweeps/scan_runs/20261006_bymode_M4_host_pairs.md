# M4 — by-mode pass: console, host side, twin, tooling, dangerous pairs

Slice: inventory §4 D8, D9, D29, D30; §7 S1-S19; §8 P1-P34 (57 IDs); plus the crossed pass over the two first-pass
reports' "checked, nothing found" sites. Read-only; nothing run. Pinned sources: MicroPython v1.29.0 at
`/root/pico-toolchain/micropython` (`git describe` = v1.29.0), `ext/microdot.py`. Line numbers are HEAD's. "WO" = work
order (`audit/consolidation/M_*.md`), "REG" = `audit/REGISTER.md`.

Two platform facts this slice rests on, checked first:

- **USB CDC TX** (`shared/tinyusb/mp_usbd_cdc.c:102-142`, `ports/rp2/mphalport.h:36`): with DTR clear the 256-byte
  TX FIFO is overwritable (`lib/tinyusb/src/class/cdc/cdc_device.c:428-433`) and a write never waits; with DTR set and
  the host not reading, each `mp_hal_stdout_tx_strn()` call waits until 500 ms pass **without progress** (the timer
  restarts on every partial write, `:121-123`), so a slowly draining host can hold one call longer. While waiting it
  calls `mp_event_wait_ms(1)` (`:130-134`), which runs `mp_handle_pending()` (`py/scheduler.c:259-291`): soft-Timer
  and Pin-IRQ callbacks are **delivered** during a console stall, and a pending `KeyboardInterrupt` is raised from
  inside the `print()`.
- **The VL805 errata**: the firmware is built with `PICO_RP2040_USB_DEVICE_UFRAME_FIX=1` (RP2040-E15) and
  `PICO_RP2040_USB_DEVICE_ENUMERATION_FIX=1` (RP2040-E5) (`ports/rp2/build-RPI_PICO_W/CMakeFiles/firmware.dir/flags.make:13`).
  A residual controller hang leaves DTR latched set, so to the firmware it looks exactly like a host that holds the
  port open without reading.

## (A) Verdict table

| ID | verdict | evidence | note |
|---|---|---|---|
| D8 | safe | DTR clear → FIFO overwritable (`cdc_device.c:428-433`), write never waits (`mp_usbd_cdc.c:111-118`); every project fault that matters is persisted to FRAM independently of the console | what is lost with no reader is console-only output; the part of that which nothing else records (cyw43-driver warnings) is M4-01 (c) |
| D9 | owner (partial → M4-01) | M.SPEC.018 (9): "an accepted debug-mode limitation (owner, 2026-09-30)"; client traffic at level 0 proven silent by M.TEST_UNIT.208 and M.HW_BENCH (L4 console-starvation test) | claim refined: the 500 ms restarts on progress, and the scheduler runs during the wait. Not covered: output printed **at DebugLevel 0** by layers below us (M4-01 a-c) and the persisted-level boot loop (M4-01 d) |
| D29 | WO | M.SCR.070 "Line-preserving stripper, no `ast.unparse`": TYPE_CHECKING blocks blanked line for line, so frozen line numbers equal source | — |
| D30 | WO | SIGINT path: `unix_kbd_intr` override applied and proven on every Unix build (M.TOOL.037, M.TOOL.056 `verify_unix_kbd_intr_in_build`); a segfaulting/hung file has no count line and is reported, not passed (M.SCR.040 `.noverdict`, crashed-log case in M.TSC) | the nested-`asyncio.run()` and non-fd-poll rules are CLAUDE.md test-authoring rules; a violation crashes or times out visibly |
| S1 | WO | M.SCR.068: everything built in memory, any `BuildError` → nothing written, every file via tmp + `os.replace()`, stamps last (a kill mid-loop leaves an old stamp → the freshness check in M.TEST_HELP reports "stale") | supersedes SF-B18 for this one file |
| S2 | WO | M.SCR.068 prunes every output whose device stem is not current ("Pruned N stale output(s)") | — |
| S3 | owner | M.SCR.066/.067: "real builds stamp their UTC build time … (owner, 2026-10-05)"; commit and dirty flag in the image record (M.SCR.067) | `BuildDate` (second resolution) is the device→record link |
| S4 | WO (partial → M4-07) | M.SCR.067 records `commit`, `dirty`, `BuildDate` beside every `.uf2` | the `.uf2` copy itself is not atomic and a kill can pair a new image with the previous record |
| S5 | WO | M.SCR.065: the toolchain lock "held from before the `mpy-cross` wipe until the record is written"; M.TOOL.062 fail-fast `flock`; an interrupted rebuild is wiped and rebuilt by the next run (`scripts/build_firmware.py:154-157`) | — |
| S6 | WO | M.TOOL.050 (`rev-parse --verify HEAD` before reuse, interrupted clone named), M.TOOL.061 (record written last via `os.replace`; missing record = incomplete toolchain, refused by M.SCR.065), M.TOOL.062 (lock) | — |
| S7 | WO | M.TOOL.046 (`run()` bounded, network steps retried, one named error); `run()` already raises `SetupError` (`toolchain/setup_toolchain.py:190-205`); twin offline: M.TWIN.167/.053 local NTP responder (owner, 2026-10-02) | loud, never silent |
| S8 | WO | M.TOOL.002/.013, M.SCR.014 (one retried `uv sync --locked`); CLAUDE.md "Don't 'simplify' the retry away (owner, 2026-09-26)" | — |
| S9 | WO | M.TOOL.078 "The lock is refreshed, then re-written for every pin change, and checked against the pins" | — |
| S10 | SF (SF-B13) | `digital_twin/_fram_chip.py:57-106`; flush-at-exit only is owner-decided (M.TWIN.062: "never automatically … (owner, 2026-08-12)"), blank-on-malformed too (owner, 2026-08-13) | SF-B13's atomic write + load message close the silent part |
| S11 | refuted | `digital_twin/config/` is gitignored (`.gitignore:82`), `git ls-files digital_twin/config` is empty; the manual entry point persists by design (owner, 2026-08-13; M.TWIN), automated callers pass per-run `--config-dir` | no committed fixture is mutated |
| S12 | WO | M.SCR.012/.013/.039 one lock per product-fixed port (53, 18080), JS twin shares it (`tests_js/_port_lock.js`) | — |
| S13 | WO | M.TOOL.037/.056: the override is applied and its presence proven after every Unix build | — |
| S14 | WO (partial → M4-06) | M.SCR.040: a pass after a retry is `RETRIED-PASS k/n`, printed as a root-cause item | the memory gate still reads only the deciding attempt's log |
| S15 | WO | M.SCR.038 (trap first, exact-pid kill), M.SCR.039 (port-53 lock, released in `_cleanup`), M.SCR.012 (stale lock taken over); `setcap` from `libcap2-bin` in `apt_packages`, tier commands checked up front (M.TOOL.065) | residual: after a SIGKILL the stale-lock takeover checks only the recorded pid, while orphaned children live on for at most their own `timeout` (240 s + 10 s); their cross-talk fails tests visibly (CLAUDE.md "two suites" bullet). Not filed |
| S16 | owner | CLAUDE.md: "Two Unix-port binaries are built, not one (owner decision, 2026-09-21)"; SPEC E.5.2 | — |
| S17 | WO (partial → M4-08) | ticks period: M.PROC.024 (2**30 scratch build), M.TOOL.080/M.SCR.074 (rollover image on silicon), `DrivenTime`; struct sizes: SPEC F.1 rule; TZ: `scripts/test.sh` pins UTC; float: M.HW_DEV.152 (one float round trip on silicon) | float32 behaviour and the 31-bit small-int heap cost have no host tier |
| S18 | owner | CLAUDE.md "No test may inflict avoidable wear … (project owner's explicit, standing direction, 2026-09-17)" and "(owner's clarification, 2026-09-18)"; the verdict names the deselected count | — |
| S19 | owner | CLAUDE.md "Owner decision, 2026-09-18: this is a periodic check the project owner runs manually"; the recipe states it "verifies what is on disk, not what is on a branch" | the `git ls-files` gap of a copied worktree is already a REG U36 parked delta |
| P1 | SF (SF-A11) | one-shots dropped by a full scheduler queue: unpause = SF-A11; reset arm (WDT backstop, M.SRC_CORE.009-.011), stagger (owner WDT backstop 2026-07-18, M.SRC_CORE.014), NTP retry (owner-accepted, M.SRC_NET.051) | D9 part refuted: a console stall drains the queue every ms (`mp_usbd_cdc.c:130-134` → `scheduler.c:284-291`). The real accumulator is a flash `close()` (several erase/program cycles, IRQs re-enabled between them, VM not running until it returns) |
| P2 | owner (partial → M4-05) | SPEC A.4: "permanent WiFi deactivation after a second STA failure streak … only a physical power-cycle clears it" (owner, 2026-07-13, `368fa83`; restart guard owner 2026-08-11); distinct deactivated LED pattern (owner, 2026-09-29; M.SRC_NET.100) | the terminal event is console-only, lost at the power cycle that is its only exit |
| P3 | owner (partial → M4-05) | same owner decision; M.SRC_NET.088 keeps the deactivation `pr.one` | a household power cut where the router outlasts 5 attempts + 8 min hotspot leaves no persisted trace |
| P4 | NEW (M4-02) | producers keep the last sample with its old TS (owner, 2026-09-29, OR94.a (13)); the SCD30 is never started by the firmware (owner, 2026-09-26, `asy_scd30_driver.py:162-163`); consumers ignore `TS` (`asy_sgp40_driver.py:263-281`, `asy_notification_service.py:198-209`) | — |
| P5 | SF (SF-A04 = SF-B10) (partial → M4-02) | restamp fixed by SF-B10/SF-A04 | after that fix the old sample still drives WarnCO2/WarnHum |
| P6 | SF (SF-B9 / SF-A05) | SPEC C.8 "Known structural gap, accepted risk (`SGP40_I2C._reset()`)" (`SPECIFICATION.md:2085-2093`); sibling self-reset detection: ISL29125 BOUTF at HEAD (M.SRC_SENS.082), BMP3XX `por_detected` = SF-A05/SF-B9 | the SPEC sentence carries no actor tag (decision-record rule 1, for U0's vocabulary check) |
| P7 | WO (partial → M4-01) | owner-intended escalation (OR18.a); ladder first (M.SRC_CORE.037), one slot per repeat (M.SRC_CORE.063), escalation through `_reboot()` which pauses FRAM before the arm (M.SRC_CORE.016) | with a non-reading USB host each task death's unconditional traceback starves the watchdog first (M4-01 a) |
| P8 | owner | dual copy + busy status byte, interrupted chunk = hard failure (owner-confirmed, 2026-07-18, `c9dde56`; `SPECIFICATION.md:180-190`); commanded resets drain FRAM first (owner, 2026-09-30) | — |
| P9 | SF (SF-B1) | `asy_fram_manager.py:645-680` address + CRC8 only | — |
| P10 | owner | "a power loss landing in that same brief window loses the just-accepted config change silently … accepted by the owner (owner, 2026-09-26)" (`SPECIFICATION.md:3694-3697`) | the flush-failure half is SF-B3 |
| P11 | WO | M.SRC_NET.221 DMA receive ring (owner, 2026-10-05: "not crossed"), OE → failed transaction (M.SRC_NET.221 (6), OR146) | FE/BE = SF-A06; TX stall = SF-A07 |
| P12 | WO | M.SRC_NET.088 "retry wait outside the lock" (`asyncio.sleep(_STA_RETRY_AFTER_LOSS_S)` after the `async with`) | — |
| P13 | SF (SF-B17) | `asy_notification_service.py:364-365` (`cettime()` None → not evaluated) | — |
| P14 | NEW (M4-03) | HEAD `asy_sgp40_driver.py:380-395`; WO M.SRC_SENS.063 restore text | — |
| P15 | WO | M.SRC_SENS.079 (stored tick bounded to `_MAX_DWELL_MS`, A.U15.35), Ticks30 crossing case (c), M.PROC.024 | — |
| P16 | WO | A.U15.35 → M.SRC_SENS.081 (`_measured_ratio()` clears; `_cal_until_ms` bounded), Ticks30 crossing case (b) | — |
| P17 | WO | M.SRC_SENS.068 `_relative_humidity_to_ticks()` "clamped to Table 10's range, never wrapped" (A.U15.14); HEAD wraps (`asy_sgp40_driver.py:607` `& 0xFFFF`) | — |
| P18 | refuted | rp2 timestamps are `mp_uint_t` (`shared/timeutils/timeutils.h:38-42`, no Y2100 option on rp2): valid to 2106, so 2038 does not overflow; M.SRC_CORE.032's ruling (G4/R15) "OverflowError/OSError unreachable on target"; bogus replies gated to 2025-2100 (`asy_ntp_client.py:258`) | a bogus in-window reply (zero transmit timestamp → 2036) is the REG parked U18 NTP delta |
| P19 | WO | M.SRC_CORE.043 (directory → `_ERR_CFG_PATH_IS_DIR`, unreadable never overwritten, `faulted`), M.SRC_CORE.015 `ConfigFaults`, M.SRC_NET.084 (missing LED config → deactivated with persisted `_WRN_CFG_READ` and the visible pattern) | reboot loop bounded by SPEC C.7.3 |
| P20 | NEW (M4-04) | `ports/rp2/modules/_boot.py:7-12` (bare `except:` → `mkfs`); HEAD logs a missing file persistently (`config_manager.py:423-426`, wrnno 3); M.SRC_CORE.043 makes it print-only | — |
| P21 | owner (partial → M4-01) | M.SPEC.018 (9) (owner, 2026-09-30); A.S0930.41 names the reset-tail case | the persisted `DebugLevel` turning the stall into a boot loop is not named (M4-01 d) |
| P22 | WO | M.SRC_NET.123 (per-key result), M.SRC_CORE.063/.091 `reset() -> bool` (FRAM paused → "Failed") | — |
| P23 | owner | CLAUDE.md: trusted-home-LAN threat model, hotspot fallback password "accepted permanently … (owner, 2026-09-26)"; reset code 4 recorded (A.S0930) | — |
| P24 | WO | controlled shutdown (owner, 2026-09-30): stores closed at S2, later PUTs answer "Failed"; M.SRC_CORE.010/.011 | — |
| P25 | WO | M.SRC_CORE.014: every starter guarded and the loop continues; stagger arm failure falls back to `sleep_ms` with `_ERR_TIMER` | — |
| P26 | WO | a sag-corrupted write fails CRC/dual-copy at the next read (M.SRC_CORE.088 tri-state, FRAM layer entry) | whether the Pico W 3V3 rail sags below 3.0 V is not decidable from source (Phase C) |
| P27 | NEW (M4-10) | MB85RS64V "CS > VDD × 0.8" during tpu/tpd (DS501-00015 "POWER ON/OFF SEQUENCE"); RP2040 pads reset to pull-down | hardware-only |
| P28 | SF (SF-B9 / SF-A05) | `asy_bmp3xx_driver.py:429-447` never reads EVENT | — |
| P29 | WO | M.SRC_NET.127/.129 (`HTTPDropped`, 24 h window), M.TOOL.038 (lwIP floors) | UDP queue = SF-A08, DHCP pool = SF-A09 |
| P30 | NEW (M4-09) | M.SPEC.097 timing budget has no WLAN mode-switch row | — |
| P31 | safe | `asy_scd30_driver.py:108` `# @requires bus.timeout>=200000`, enforced per bus by `buildgen/requires_tag.py`; generated: every SCD30 bus carries `timeout=200000` (`sensortask_*.py:160-174`) | a co-located device inherits the bus timeout; a misplaced SCD30 fails the build |
| P32 | SF (SF-B12) | FRAM's own setup failure shows in its RAM errcount until reboot; RAM-only modules unflagged = SF-B12 | — |
| P33 | SF (SF-B13) | `_fram_chip.py:57-106` | — |
| P34 | WO (partial → M4-06) | M.SCR.040 `RETRIED-PASS`, root-cause line | — |

## (B) Findings

### M4-01 Console output that no `DebugLevel` controls starves the watchdog under a non-reading USB host and erases the cause
- **Sites**: (a) asyncio's default exception handler: a supervised task that ends with an exception is re-queued
  and printed (`extmod/asyncio/core.py:208-240, 294-297`: message, `future:` line, `sys.print_exception`), at any level.
  Nothing in `src/`, `build/generated_src/` or the WO calls `set_exception_handler` (grep, also `audit/consolidation/`).
  The supervisor only sees the death on its next 2 s pass (`system_service.py:229-240`). (b) Microdot prints
  `print_exception(exc)` **before** dispatching to our `errorhandler(Exception)` (`ext/microdot.py:1518`, and `:1543`
  for a failing handler); `:1408` (read phase) is covered for client faults by M.SRC_NET.118/M.TEST_UNIT.208.
  (c) cyw43-driver warnings: `CYW43_WARN` → `CYW43_PRINTF` → `mp_printf(MP_PYTHON_PRINTER, …)`
  (`lib/cyw43-driver/src/cyw43_config.h:176`, `extmod/cyw43_config_common.h:45`; 30 sites, e.g. `cyw43_ll.c:416`
  "could not find valid firmware", `:482` verify failure, `:691` "STALL … timeout"). (d) `DebugLevel` is persisted
  (`system_service.py:312-321`) and pushed to every logger from the boot batch's second unit on
  (`sensortask_dev.py:228, 235`).
- **Class**: 5 (loop held) and 7 (the death's cause never reaches FRAM; the reset reads as a watchdog reset); (c) is
  also class 1 (a lower-layer fault reported only to the console, lost with no reader, D8).
- **Mode**: console, USB host holding the port open without reading (a stalled bench monitor, a VL805 controller hang);
  pairs: × a task crash, × a handler exception, × a cyw43 fault; (d) × a raised `DebugLevel`.
- **Mechanism**: with DTR set and the FIFO already full, every write call waits 500 ms. A task traceback is roughly 40-60
  calls (each `print` argument, separator and `mp_printf` fragment is one call), so 20-30 s pass with the loop held.
  The 8 s watchdog fires before `_log_dead_task()` persists errno 5 and before the budget is charged. A.S0930.41 and
  M.SPEC.018 (9) describe the stall at raised levels and the reset-tail case only. At level 0 the client-traffic proof
  (M.TEST_UNIT.208, the L4 bench test) does not reach (a)-(c). First pass A's "DebugLevel 0 prints nothing" is wrong
  for these sources.
- **Effect**: all six devices whenever such a host is attached. In practice that is `dev` on the Pi 4 bench: a crash
  seen under the serial monitor turns into a watchdog reset with no errno 5, and with a crash-looping driver into a
  watchdog boot loop instead of the task-budget reboot (errno 4) the supervisor would record. Undetectable with no host
  attached; then (c) is lost entirely.
- **WO**: not covered ((a), (b), (c)); (d) partly (owner-accepted stall, loop unnamed).
- **Owning units**: U11 (a: `SystemService.start_tasks()`, M.SRC_CORE.016), U19 (b), U14 (c: SPEC F), U33/U36 (d: docs).
- **Smallest fix**:
  - (a) One `asyncio.get_event_loop().set_exception_handler(...)` in `start_tasks()` routing `context["exception"]` to
    SYSTEM's `pr.err` (level-gated, one `str(e)` line). The death is already persisted by `_log_dead_task()`. Check
    first that every memory-gated tier runs at `DebugLevel` ≥ 1, so the gates still see "memory allocation failed"
    from an uncaught task `MemoryError`.
  - (b) At `WebserverService` construction, `microdot.print_exception = self.pr.err`: a module-attribute assignment
    from our own code, not an edit of the vendored file. Put it on the owner-review list against the vendoring rule.
  - (c) No code: one SPEC F sentence that cyw43-driver faults reach only the USB console, cannot be read from Python,
    are lost with no reader and block with a non-reading one.
  - (d) One SPEC A.8/F.2 clause: a raised, persisted `DebugLevel` with such a host can starve the watchdog at every
    boot. Exits: close the host program, unplug, or `PUT DebugLevel 0` inside the window.

### M4-02 Consumers act on a frozen sample as if it were current: CO2/humidity alerts and VOC compensation
- **Sites**: `src/asy_notification_service.py:198-209` (`_check_one()` uses `getattr(data, field)`, never `data.TS`);
  `src/asy_sgp40_driver.py:263-281` (compensation `Temp`/`Hum` used whatever their age; only `None` skips).
- **Class**: 4 (a stale value conflated with a current one), 7. **Mode**: pairs. SCD30 measurement stopped
  (`ContMeas=false` PUT, factory chip state; the firmware never starts it, owner 2026-09-26) × consumers. Also an SCD30
  RDY line that never rises, an SCD30 read-failure streak, or a wedged bus. Each one leaves the last sample in place
  with its original `TS` (owner, 2026-09-29, OR94.a (13)).
- **Effect**: all six devices (SCD30, SGP40 and notification on every one). WarnCO2/WarnHum keep flashing or stay dark
  on a value hours or days old. SGP40 compensates with stale T/RH, which skews the VOC index and so WarnVOC. Nothing is
  logged: P4's "zero errors anywhere" holds for the measurement-off case. First pass B's "SGP40 compensation missing →
  no gap" read only the `None` case.
- **WO**: not covered. SF-B10/SF-A04 stop the restamp (P5), SF-B17 makes "not evaluated" visible, and RF333 is
  display-only. None bounds the age a consumer accepts.
- **Owning units**: U22 (notification), U15 (SGP40).
- **Smallest fix**: a bound on a value already returned. In both consumers, a sample whose `TS` is older than a tagged
  limit, compared with `utc_now()` when both are known, takes the existing `None` path: SGP40 skips (C.14.2), the
  notification is "not evaluated" (SF-B17's state). When the age is unknown (before NTP sync) today's behaviour stays,
  documented. No new state.

### M4-03 SGP40 restore with an unknown age: silent at HEAD, a `None < 0` comparison in the merged rewrite
- **Sites**: HEAD `src/asy_sgp40_driver.py:380-395`. A timestamped backup read while NTP is unsynced returns
  `age=None` (`asy_fram_manager.py:589-615`). Once `voc_init` reaches 0, the `elif age is None` branch falls through to
  `restored_from = ts; return True`, with no age check and no persisted note. WO M.SRC_SENS.063 rewrites it as
  "otherwise … `if cfg_values[1] > 0 and (age < 0 or age > 60 * cfg_values[1])`". That branch is reached with
  `age=None` both when the NTP wait expires and for an untimestamped backup. `BackupMaxAge` defaults to 7200, so it
  raises `TypeError` on MicroPython.
- **Class**: 4 (HEAD), 6 (WO). **Mode**: pairs. Hotspot/no-NTP or NTP unreachable × reboot × an existing FRAM
  backup (P14).
- **Effect**: SGP40 on all six devices (all wire the FRAM backup). HEAD: a baseline of any age is restored silently.
  WO as written: the restore never succeeds. Depending on the enclosing handler, the result is either a logged error
  every cycle or a task death and restart loop.
- **WO**: the rewrite introduces the defect; the L1 cases named in its blast (WaitTimeNTP 0, −60 s age) do not pin the
  `age is None` path.
- **Owning unit**: U16 (M.SRC_SENS.063, latest stage), with U15.
- **Smallest fix**: in that branch, test `age is None` before the comparison. Restore and persist the existing
  "loaded without timestamp" warning (`_WRN_SGP_RESTORED_NO_TS`): "age unknown" has the same consequence as "no
  timestamp". Add one L1 case: backup with a timestamp, NTP never synced, wait expired.

### M4-04 A littlefs reformat at boot becomes indistinguishable from a first boot once the WO lands
- **Sites**: `ports/rp2/modules/_boot.py:7-12`. A failed mount is caught by a bare `except:` and answered with `mkfs`,
  silently, below our code. HEAD then logs every missing config file persistently (`src/config_manager.py:423-426`,
  wrnno 3), which leaves a trail in FRAM. M.SRC_CORE.043 makes the absent-file branch print-only ("not present - writing
  the defaults once"), and M.SCR.049 pins "nothing logged on a normal boot".
- **Class**: 7, 1. **Mode**: pairs. littlefs unmountable at boot (D1) × the first-boot path, then × P2: the empty SSID
  sends the device straight to hotspot, and 8 min later WiFi is deactivated until a power cycle (owner design).
- **Effect**: all six devices. A flash fault or a cut write that broke the filesystem shows up as a factory reset
  followed by a dead network, with no persisted trace. FRAM still holds the earlier life's history, which then looks
  like a contradiction.
- **WO**: makes it worse (removes HEAD's only trace).
- **Owning unit**: U11 (M.SRC_CORE.043; `SystemService.setup()`).
- **Smallest fix**: combine two facts already known at boot. In `SystemService.setup()` (second in the batch, after
  `fram.setup()`): if its own store reported the file absent while its FRAM history chunk read back valid (non-blank),
  and the reset record is not "config reset" (code 7), persist one warning: "config file absent while FRAM history
  exists (filesystem reformatted or wiped)". A clean first boot (blank FRAM) and the twin's Run 1 stay silent.

### M4-05 Permanent WiFi deactivation leaves no persisted trace
- **Site**: `src/asy_wifi_service.py:491-501` (`_deactivate_wlan_permanently()`: `pr.one` only; only a failure of the
  radio calls is persisted). M.SRC_NET.088 keeps that.
- **Class**: 7. **Mode**: pairs. A router outage at boot that outlasts 5 attempts plus the 8 min hotspot window (P3),
  or a factory/unconfigured device nobody joins (P2).
- **Effect**: all six devices. The owner-designed terminal state (owner, 2026-07-13; LED pattern owner, 2026-09-29) is
  left only by a power cycle. That power cycle is also when an investigator first reaches the device, and nothing
  then says why it was offline.
- **WO**: not covered. **Owning unit**: U18.
- **Smallest fix**: make the owner-accepted behaviour visible without changing it: `wrn_s` instead of `pr.one`, one
  catalog code. It is one entry per boot by construction, since the state is terminal.

### M4-06 The memory gate reads only the deciding attempt, so a `MemoryError` in a timed-out attempt is erased
- **Site**: `scripts/test.sh:356-382`: `: >"$log_file"` truncates on every attempt; `_flag_memory_errors` runs only
  on the attempt that decides. M.SCR.040 keeps this (`RETRIED-PASS` is reported, the memory text is not).
- **Class**: 4. **Mode**: tooling, a timeout retry (S14) × an intermittent hang (P34).
- **Effect**: the L1/L2 tiers for every device. A caught-and-logged allocation failure printed before a timeout
  vanishes when attempt 2 passes. The file then reads `RETRIED-PASS`, never "MemoryError seen". This is the relaxation
  CLAUDE.md forbids ("caught-and-logged included … don't relax that").
- **Owning unit**: U27 (M.SCR.040; stage U7).
- **Smallest fix**: an ordering change. Run `_flag_memory_errors` on each attempt's log before it is truncated (or
  stop truncating; `tee -a` already appends), so a marker from any attempt fails the file. The comment's reason
  ("partial output cannot fail a passing file") goes.

### M4-07 The `.uf2` copy is not atomic, and a kill can pair a new image with the previous record
- **Site**: `scripts/build_firmware.py:162` `shutil.copy(uf2, output)`. M.SCR.067 then writes the record via tmp +
  `os.replace`.
- **Class**: 6, 4. **Mode**: tooling, a build killed mid-way, then a flash or a bench run over the leftovers.
- **Effect**: whichever device is built; the bench (`dev`). A kill during the copy leaves a truncated `.uf2` under the
  normal name. Picotool's handling of missing UF2 blocks is not confirmed from source. A kill between the copy and the
  record write leaves a new image beside the previous build's record, which M.HW_BENCH.060's image check trusts.
- **WO**: partly (SF-B18 lists `build_firmware.py:56,98-99,149`, all inside the throwaway stage dir; not `:162`, not
  the pairing).
- **Owning unit**: U27 (M.SCR.067).
- **Smallest fix**: an ordering change. Unlink the old record first, copy the `.uf2` to a same-dir tmp and
  `os.replace` it, then write the record. A record then exists only beside the image it describes.

### M4-08 The host rig cannot show float32 or 31-bit small-int behaviour; the rollover has its own image, these do not
- **Sites**: rp2 builds `MICROPY_FLOAT_IMPL_FLOAT` (`ports/rp2/mpconfigport.h:128-129`), while the Unix rig is double
  (`ports/unix/variants/mpconfigvariant_common.h:40-41`). rp2 small ints are 31-bit, so every current epoch timestamp
  (≈1.79e9 > 2**30) from `utc_now()` is a heap-allocated big int on silicon (`timeutils_obj_from_timestamp`) and a
  small int on the 64-bit rig.
- **Class**: 3 (detection left to chance). **Mode**: twin and tooling.
- **Effect**: float32-only defects pass L1/L2 by construction. The SCD30 offset truncation (REG parked U15) and
  RF207's config float that never settles were both found outside the tiers. Heap figures at L1/L2 under-count one big
  int per timestamp per reading. SPEC F.1's acceptance (owner, 2026-08-24) covers `coerce_numeric()` only.
- **WO**: partly: M.PROC.024 does this for ticks only; M.HW_DEV.152 covers one known float site.
- **Owning units**: U35 (procedure, M.PROC.024 pattern), U21 (build flavour), U30 (heap note).
- **Smallest fix**: the M.PROC.024 pattern once more. A scratch Unix build with
  `CFLAGS_EXTRA=-DMICROPY_FLOAT_IMPL=MICROPY_FLOAT_IMPL_FLOAT` (the common variant guards it with `#ifndef`) runs the L1
  files touching floats at both GC stages, with results in `timing.md`. Add one SPEC F.1/I sentence that heap figures
  from the 64-bit rig exclude timestamp big ints. The permanent alternative is building `build-standard` single
  precision: one make var, but it moves every float test, so it is an owner choice.

### M4-09 The WLAN mode-switch stall is missing from the timing budget
- **Site**: M.SPEC.097's table (consumer rows `con.uart_reply`, `con.uart_rx_ring`; stall rows `flash_program`,
  `console`, `sync_wait`, `uart_call`, `voc_process`, `fram_command`). `wlan.active()`/`deinit()` and the cyw43
  firmware upload run synchronously in the loop (only the scheduler runs inside `cyw43_delay_ms`).
- **Class**: 5. **Mode**: pairs. An STA↔AP transition (P30) × the `dev` UART link's reply deadline, NeoPixel ramps.
- **Effect**: `dev`. Both link instances stall together, and the initiator can find its tick deadline passed with the
  reply already in the ring. The result is a counted link failure blamed on the link, not on the radio. LED stutter is
  cosmetic. Whether the deadline is crossed is not confirmed from source.
- **WO**: not covered (same shape as SF-A07). **Owning unit**: U31 (with U18 for the measurement).
- **Smallest fix**: one `stall.wlan_switch` row ("owed" until measured in phase C) against `con.uart_reply`. No code
  unless it crosses.

### M4-10 FRAM chip-select during a reset or power-off is pulled toward low by the RP2040 pad default
- **Site**: hardware. MB85RS64V requires "CS > VDD × 0.8" during tpu (0.6 ms at 3.3 V) and tpd (400 ns)
  (DS501-00015, POWER ON/OFF SEQUENCE). CS has an internal pull-up of unstated strength (pin description). Every
  RP2040 reset (watchdog, `machine.reset()`, RUN, brown-out) returns the CS GPIO to input with pull-down (PADS_BANK0
  PDE reset 1), and nothing in firmware can hold it through a reset.
- **Class**: 5. **Mode**: each kind of restart, power loss.
- **Effect**: FRAM on spi0, all six devices (dev: MB85RS2MTA, whose datasheet sets the same rule). With SCK also
  pulled low, no command can be clocked, so the realistic risk is the power-off edge only. Not decidable from source.
- **WO**: not covered (REG's Phase C list names the MISO pull-up, not CS). **Owning unit**: Phase C (U16 for the SPEC
  line).
- **Smallest fix**: no code. One Phase C bench check (scope CS against VDD across a watchdog reset and a supply
  removal). If CS falls below 0.8·VDD inside tpd, a board-level pull-up is the remedy.

### M4-11 After 511 unread host bytes, Ctrl-C no longer reaches the firmware (bench, low)
- **Site**: `shared/tinyusb/mp_usbd_cdc.c:76-99`. The interrupt character is recognised only while the 512-byte stdin
  ring (`ports/rp2/mphalport.c:56-57`) has room. The firmware never reads stdin, so once a host program has sent 511
  bytes (a terminal, a probe), a later 0x03 stays in the USB buffer.
- **Class**: 2. **Mode**: console.
- **Effect**: `dev` bench. mpremote's Ctrl-C/raw-REPL entry fails against the autostart image with a generic error,
  which looks like a board fault. (The other way round, a stray 0x03 from a host program ends the event loop: SF-A14.)
- **WO**: not covered. Scripted bench use takes the no-autostart image (M.SCR.065, M.GEN.019), which is unaffected.
- **Owning unit**: U26/U33 (`tests_hardware/README.md`).
- **Smallest fix**: no code. One README line naming the symptom and its exit (a reset by RUN/power, or the
  no-autostart image).

## (C) Scenario walks

**Console.** *No host*: nothing ever waits (D8). Output that nothing else records is lost: the asyncio traceback
(persisted anyway by `_log_dead_task()`) and the cyw43 warnings (M4-01 c). *Draining host*: no effect. *Host holding
the port without reading* (a stalled monitor, a VL805 hang with DTR latched; the E15 and E5 workarounds are compiled
in): soft callbacks keep being delivered during the stall (P1's D9 half refuted). At raised levels this is the
owner-accepted stall, but the persisted level makes it a boot loop (M4-01 d). At level 0 the unconditional outputs (a)-(c)
still block the loop for tens of seconds, so a task crash becomes an unexplained watchdog reset (M4-01).
*Ctrl-C*: `KeyboardInterrupt` passes every `except Exception`. The three `except BaseException` sites re-raise
(`asy_spi_driver.py:142, 162`, `asy_fram_driver.py:134`), and `async with` exits deassert CS. The loop ends, the boot
entry's `finally` makes a new loop, and the REPL runs with the watchdog armed, which resets the board within 8 s; a
pending flush is lost (SF-A14). It can also arrive from inside a blocked `print()` (`mp_handle_pending` in
`mp_event_wait_ms`), and from any stray 0x03 a host program sends. Its mirror image, a full stdin ring, is M4-11.
*mpremote soft reset*: in raw-REPL mode `main.py` is not run (`ports/rp2/main.c:245-247`, `PYEXEC_MODE_FRIENDLY_REPL`
only), so the previous run's watchdog stays armed and unfed and ends any mpremote command within 8 s. Scripted bench
use is covered by the no-autostart image (M.SCR.065/M.GEN.019); nothing new.

**Twin and tooling.** SIGINT shutdown: the `unix_kbd_intr` override is proven on every build and the heap unwedge
stays as a backstop (S13, D30). A twin killed before `finally`: SF-B13. A generator killed mid-loop: all or nothing,
stamps last (M.SCR.068). A firmware build killed: the toolchain lock and a wiped work dir cover the build. The `.uf2`
copy and its record are not covered (M4-07). Re-run over a dirty tree: the generated tree is pruned (M.SCR.068), the
build work dir is wiped at start (M.SCR.065), and the twin config dir persists only for the manual entry point (owner,
2026-08-13). M.TWIN.053's offline NTP config is written "only when absent", so a leftover manual `config_NTP.cfg` would
be used by a later manual run; automated runs use fresh per-run dirs. Offline run: twin NTP comes from the local
responder (M.TWIN.167); setup steps retry and fail by name (M.TOOL.046). Stale module for a removed device: pruned
(M.SCR.068). Image from uncommitted edits: `dirty` in the record (M.SCR.067), linked to the board by `BuildDate`.
Rig fidelity: ticks are covered (M.PROC.024); floats and big ints are not (M4-08). Test retries: visible
(`RETRIED-PASS`), but the memory gate is not (M4-06).

**Pairs.** Walked P1-P34 above. New gaps: **SCD30 stopped × consumers** (M4-02); **NTP never × SGP40 restore**
(M4-03); **reformat × first-boot path × hotspot timeout** (M4-04: a filesystem fault ends 8 min later as a dead radio
with no trace); **router outage at boot × deactivation** (M4-05); **console stall × task crash** (M4-01, the P7/P21
crossing); **WLAN switch × UART deadline** (M4-09); **reset or power-off × FRAM CS** (M4-10). The dangerous flash
pair is the scheduler queue, not the console. One `close()` spans several erase/program cycles with the VM stopped,
so soft-timer fires accumulate; the one-shot that matters is SF-A11.

### (C2) Crossed pass over the first-pass reports' "checked, nothing found" sites

| First-pass site | Mode that changes the reading | Result |
|---|---|---|
| A "USB CDC stdout … `DebugLevel` 0 prints nothing" | console, level 0 | **wrong**: asyncio handler, Microdot `print_exception`, cyw43 warnings print at any level → M4-01 |
| A "WDT … soft reset … the next boot re-arms it first" | mpremote raw REPL | not when the soft reset happens in raw REPL (`main.c:245-247`): the old WDT runs unfed; covered by the no-autostart image (walk) |
| A "machine.SPI … nothing silent" | Ctrl-C, soft reset | the DMA wait is a C busy loop with no pending-check (`machine_spi.c:299-305`), channels unclaimed before return; nothing |
| A "FRAM chip" | reflash with another FRAM size | RDID product ID checked against `max_size` (`asy_fram_driver.py:182-187`); safe |
| A "network/cyw43 … all STAT_* mapped" | console | cyw43-driver faults bypass STAT_* and go only to the console → M4-01 (c) |
| A "os/littlefs/flash … full FS logged" | littlefs unmountable at boot | the `mkfs` path is silent and the WO removes HEAD's trail → M4-04 |
| A "Flash write window … soft Timers delayed, coalesced" | pairs (P1) | the whole `close()` holds the VM: callbacks queue across several erases; one-shot loss = SF-A11 |
| A "machine.Timer", "Pin.irq", "time/ticks", "RTC", "Microdot caps", "socket", "gc" | console, twin | nothing new (callbacks are delivered during a console stall; host ticks covered by M.PROC.024) |
| B "Supervisor: dead task … M.SRC_CORE.016"; "`_TASK_FAIL_MAX` reboot trace"; "Absent chip → reboot loop" | console, non-reading host | the unconditional traceback starves the watchdog before the entry or the budget → M4-01 (a) |
| B "SGP40 compensation missing → … no gap" | SCD30 stopped (stale, not `None`) | → M4-02 |
| B `asy_sgp40_driver.py` "checked, nothing new" | no NTP × reboot | → M4-03 |
| B "first boot: config written once" | reformat | → M4-04 |
| B `asy_webserver_service.py` "checked, covered" | console | Microdot's pre-handler `print_exception` → M4-01 (b) |
| B generated modules "nothing else found" | console; Ctrl-C | no exception handler set → M4-01 (a); Ctrl-C = SF-A14 |
| B `digital_twin/` (B13 only) | offline run, dirty tree | covered (M.TWIN.167/.053; per-run dirs); manual leftover config noted in the walk |
| B `asy_fram_driver.py` "nothing new" | hardware script against a deployed board | SF-B1's per-owner CRC seed also makes a script-built manager's chunks fail; nothing new |
| B "API before every driver's `setup()`", "two browsers", "power loss mid flash", "UART boot drain" | pairs, console | nothing new |

## (D) Counts per verdict (57 IDs)

| verdict | count | IDs |
|---|---|---|
| refuted | 2 | S11, P18 |
| safe | 2 | D8, P31 |
| owner | 11 | D9, S3, S16, S18, S19, P2, P3, P8, P10, P21, P23 |
| WO | 28 | D29, D30, S1, S2, S4, S5, S6, S7, S8, S9, S12, S13, S14, S15, S17, P7, P11, P12, P15, P16, P17, P19, P22, P24, P25, P26, P29, P34 |
| SF | 9 | S10, P1, P5, P6, P9, P13, P28, P32, P33 |
| NEW | 5 | P4, P14, P20, P27, P30 |

Of these, 10 rows are partly covered and carry a finding: D9, P21, P7 → M4-01; P5 → M4-02; P2, P3 → M4-05; S14, P34 →
M4-06; S4 → M4-07; S17 → M4-08. Findings M4-01, M4-11 and part of M4-04 came from the walks and the crossed pass.
