# By-mode silent-failure pass, slice M3: peripherals, buses, UART link, physical environment

Read-only pass, 2026-10-06, HEAD `1b7d83d`. Sources: `src/` at HEAD, `build/generated_src/` (not regenerated),
`devices/*.toml`, the work order (`audit/consolidation/M_SRC_SENS.md`, `M_SRC_NET.md`, `M_SRC_CORE.md`, `M_SPEC.md`,
`audit/actions/U15.md`, `U16.md`, `SUPP_recovery.md`), `audit/REGISTER.md` parked deltas (SF-A*/SF-B*), MicroPython
v1.29.0 at `/root/pico-toolchain/micropython`, and the datasheet text extracts (`scratchpad/corpus/datasheets/`, cited
as `ds:<file>:<line>`). Slice: inventory 1.7-1.10, 1.13, 1.14; section 3 SCD30/SGP40/BMP3xx/ISL29125/WS2812; D24,
D25, D27, D28; section 6 Power/host/USB and Physical/sensor environment. 90 IDs.

Topology used for "effect per device and bus" (`devices/*.toml`): SCD30 on i2c0 (arzi, grkizi, klkizi, schlafzi,
wozi; `timeout = 200000`) / i2c1 (dev, with SGP40 and ISL29125); SGP40 on i2c1 everywhere (alone on arzi, grkizi,
klkizi, schlafzi; with BMP3XX on wozi); BMP3XX on i2c0 (dev, alone) / i2c1 (wozi); ISL29125 dev only; UART link x2 dev
only; every device wires SGP40 compensation from SCD30 `Temp`/`Hum` and notifications `warn_co2`/`warn_hum` (SCD30) and
`warn_voc` (SGP40). wozi is never flashed (mock/twin only).

## (A) Verdict per inventory entry

| ID | verdict | evidence | note |
|---|---|---|---|
| C94 | owner | `asy_scd30_driver.py:161-172` never sends 0x0010; "all stays as is, including the initial start of measurement at scd30" (owner, 2026-09-26, OR71.a (2); A.U15.04, `audit/actions/U15.md:107-119`) | silent part made visible by WO M.SRC_SENS.055 (A.U15.12 (4): FRC idle ticks republish `FRCState` 0 "not measuring" after two intervals); consumers of the frozen sample: M3-01 |
| C95 | SF | `:174-187` restamps, `:595-611` not-ready returns with cache intact | SF-B10 = SF-A04. The restamp is the owner's named exception (owner, 2026-07-22, `110f3db`; A.U15.22 (5)), so the SF fix is a D.1 flag |
| C96 | WO | stuck-high handled `:411-420`; stuck-low: no edge, no tick-count rise | partial: M.SRC_SENS.055 (`_frc_idle_ticks` stepped in the 500 ms tick, republish `FRCState` 0); no persisted entry and consumers unaffected → M3-01 |
| C97 | NEW | `:585-589` soft reset at every `setup()`; Interface Description 1.4.10 "same state as after powering up" (`ds:scd30__…Interface_Description.txt:1494`) | the "ASC unaffected" half is not established: M3-03 |
| C98 | WO | each `set_*` is one `_send_command` (`:534-575`) | M.SRC_SENS.053 `compare_before_write()` (U4) writes changed keys only; `AmbPres`/`ForceCalRef` always written (`always=`, owner-approved `alwaysExecuted`, A.U6.17) |
| C99 | owner | `:546-554`; tag `:67` "(starts continuous measurement)", `special:0` | SPEC A.4 `:244-247` "resending the same value is also SCD30's documented command to resume continuous measurement. Confirmed deliberate by the project owner." |
| C100 | safe | `:624-627` finiteness raise → `_read_scd()` errno 11 → streak | a counted, logged read failure; WO M.SRC_SENS.057 adds the range gate the same way |
| C101 | WO | `:505-508`; Interface Description "After repowering the sensor, the command will return the standard reference value of 400 ppm" (`ds:…Interface_Description.txt:973-975`) | M.SPEC.011 (A.4 "never Unchanged — its read-back is volatile") and M.SPEC.116; `ForceCalRef` always written (M.SRC_SENS.053) |
| C102 | owner | `asy_sgp40_driver.py:276-281`, `:531` `condition=compensated` | SPEC A.4 `:286-290` (owner, 2026-09-26: 'If configured (wired up between both sensors inside the TOML): Skip if unavailable, else runs.'). The inverse case (a frozen, non-`None` source is not "unavailable") is M3-01 |
| C103 | WO | `:214-217`, `:357-361`, `:384-387` | M.SRC_SENS.063 (`_restore_waiting`, one re-read, bound `_MAX_NTP_WAITTIME` 600 s) |
| C104 | WO | `:357` `if cfg_values[1] >= 1` leaves `voc_init` 0 | M.SRC_SENS.063 `self._voc_init = max(1, wait)` (A.U15.17 (2), owner, 2026-09-29, OR104.a) |
| C105 | NEW | `_init_sgp()` re-arms the restore at every task start (`:357-360`), algorithm state survives the restart on `SGP40_I2C` | M3-05 |
| C106 | WO | `:380-383` untimestamped backup restored without an age test | M.SRC_SENS.063 keeps W33 persisted; M.SRC_SENS.060 publishes `RestoreTS` 0 "No timestamp". Behaviour as legacy, visible |
| C107 | WO | `:391-393` | M.SRC_SENS.063 W34 `SGP_BACKUP_AGE` persisted; `VOCState` (M.SRC_SENS.064) shows the relearn |
| C108 | owner | `_VAL_BP/_VAL_BMAX` special 0 | SPEC A.4 `:276-280` (owner, 2026-07-13, `368fa83`): FRAM SGP40 backup "0 = disabled"; WO M.SRC_SENS.060 writes it into the schema special slot. Interaction with C105: M3-05 |
| C109 | owner | `:250-255` retried each cycle | "Never drop a reset, never redo the whole thing, never give up retrying (owner, 2026-07-22, `90ced2b`, 'verbatim in spirit')" `:191-193`; each retry counted, counter cap is SF-B14 |
| C110 | WO | VOC index 0 during blackout | M.SRC_SENS.060/.064 `VOCState` (0 blackout, 1 learning, 2 settled, 3 restored) |
| C111 | owner | `:586-594` | "That broadcast actually IS the accepted risk and this decision I really took. I only would not have accepted something stalling the bus itself." (owner, 2026-09-26, OR64; A.U15.15). Reaches BMP3XX on wozi, SCD30+ISL29125 on dev, nothing elsewhere |
| C112 | WO | `:597-609` `& 0xFFFF` | M.SRC_SENS.068 clamp-then-round (A.U15.14); M.SRC_SENS.064 `checked_float()` |
| C113 | SF | `:175-187` | SF-B12 (names the SGP40 `ts_storage` site) |
| C114 | safe | `asy_bmp3xx_driver.py:541-553` bounded poll raises → errno 11 → streak | a visible, counted failure; no hang |
| C115 | NEW | `:483-487` gate → `ValueError` → errno 11 (`:195`) → streak → task end → supervisor → reboot | M3-02 |
| C116 | owner | `:515-516` → init fails → restart → reboot | OR18.a (owner, 2026-09-25): a missing, defective or stalled chip escalates up to a reboot, intended (SUPP_recovery `:92`) |
| C117 | SF | OSR/IIR applied only in `_init_bmp()` `:209-223` | SF-B9 = SF-A05 (`por_detected`, EVENT 0x10) |
| C118 | WO | `:231-234` fallback `[0,0,0,15]`, errno 14 persisted | M.SRC_SENS.043 captures before the first await, keeps the persisted `_ERR_CFG_READ`; named exception of the staleness rule (A.U15.22, owner, 2026-09-29, OR94.a (13)) |
| C119 | safe | `:276` `>=` against the live period | a shrinking period fires on the next tick, a growing one keeps counting; WO M.SRC_SENS.045 moves it into the shared divider unchanged |
| C120 | safe | `asy_isl29125_driver.py:603-612` `_active_range` not updated on a failed range-bit write | next cycle re-evaluates and rewrites both absolute values (idempotent) |
| C121 | WO | `:1293` `max(0, ticks_diff(until, now))` reads up to 2**29 ms as "settling" after 6.2 days without a CONFIG1 write; `_settle_wait()` `:618-623` then sleeps it | M.SRC_SENS.086 (`time_to_settle_ms()` moves a passed deadline to now; it is called at the top of every read cycle, ≤ 3600 s apart) + M.SRC_SENS.075 unsettled discard |
| C122 | WO | `:586` compared only on the high range when peak ≤ down threshold | M.SRC_SENS.079 clamps the stored tick to `_MAX_DWELL_MS` on every high-range evaluation; every path that skips the branch for days (fixed range, task restart) passes `_switch_range()` `:610`, which refreshes it |
| C123 | WO | `:705-709` never clears `_cal_meas`; `_cal_until_ms` only read while `_calibrating` (≤ 120 s, cycles ≤ 3600 s) | M.SRC_SENS.081 clears the candidate at expiry |
| C124 | WO | `:465-479` latch | M.SRC_SENS.076: every brownout warns (W30), re-apply, one cycle without data |
| C125 | NEW | divergence checked only after a failed write (`:481-493`) or on a GET (`:716-728`) | M3-04 |
| C126 | safe | `:406-409` errno 32 persisted after an ID re-read | visible |
| C127 | WO | `:442-455` | M.SRC_SENS.077 (one re-arm per episode, parked-INT exemption) |
| C128 | safe | `:424`, tag `:182` | clipped counts are real full-scale values, flagged in the output field `Overrange` |
| C148 | WO | `_ready()` `asy_uart_comm.py:349-353` persists per refused call; setup refusal `:1086-1088` | M.SRC_NET.214 ends the exercise loop when `setup()` failed; refusal persisted once at setup |
| C149 | safe | `:200`, `:366-368` | re-entry refused with a persisted errno (asyncio.Lock is not reentrant); caller sees the failure |
| C150 | WO | `:516-525` hold-off deadline | bounded 1.5 × timeout (J.5 contract); M.SRC_NET.160 expires an aged deadline |
| C151 | WO | `:540-563` drain bound | M.SRC_NET.162 persists W54 when the bound is hit |
| C152 | owner | `:575-582` E32 | "a mismatched pair is diagnosed … never negotiated" (owner, 2026-09-11; reconciliation clause confirmed 2026-09-26, CLAUDE.md); WO M.SRC_NET.162 adds the discarded-byte count. Re-arm after `ResetErrors`: M3-07 |
| C153 | WO | `_err()` `:315-324` repeats "not persisted, not counted" | M.SRC_NET.158 + central rule (U3): every repeat counted, one slot |
| C154 | owner | `:646-652` E31 | strictly initiator/responder, simultaneous initiation out of contract (owner, 2026-08-20, `b6cb852`; 2026-09-11, `32b136f`; tag "(owner, 2026-09-11)" at `:649-650`) |
| C155 | safe | `asy_uart_driver.py:241-256`; `clear()` `asy_uart_comm.py:612-625` | no caller of `clear()`/`cancel_read_timeout()` in `src/` or `build/generated_src/` (grep); request stays latched, a rise persists W13; WO M.SRC_NET.197 wraps the sequences |
| C156 | safe | `:64-68`, `ready()` `:258-295` | stop-and-wait keeps at most one 53-byte frame unread (< rxbuf 512, `devices/dev.toml`); first byte noticed ≤ 50 ms late against a 1000 ms reply timeout; WO DMA ring M.SRC_NET.221 |
| C157 | safe | `_next_uid()` `:161-164`, train check `:758-762` | a UID is only ever compared with its immediate successor inside one train; no cross-transaction window exists; at-least-once seam documented (SPEC J `:5756`) |
| C158 | WO | `asy_uart_link_driver.py:157-160` | M.SRC_NET.216 leaves the transfer counts |
| C159 | WO | `asy_udp_socket.py:68-118` | M.SRC_NET.026/.027 (one attempt, ms backoff), M.SRC_NET.007 bind-vs-receive branch persisted; the swallowed `MemoryError` there is SF-A12 |
| C160 | WO | `asy_dns_client.py:20, 110-130` | M.SRC_NET.020 deletes `_FALLBACK_DNS_SERVERS` |
| C161 | WO | `captive_dns.py:118-136` | M.SRC_NET.007 (typed, persisted local-failure branch, ms backoff); queued-datagram drops are SF-A08 |
| C162 | NEW | `base_classes.py:60-72` `except (MemoryError, OverflowError): self.buf = None`, no text | M3-06 (SF-A12's class at a second site) |
| H30 | owner | as C94 | same owner decision; visibility via M.SRC_SENS.055 |
| H31 | safe | GET reads the chip (`get_config_snapshot()` `asy_scd30_driver.py:510-521`) | the chip NVM is the store; what the page shows is what the chip holds |
| H32 | NEW | Interface Description 1.4.6 `ds:…:821-833` | M3-03; the fresh-air part is E28 |
| H33 | safe | `@requires bus.timeout>=200000` `:108`; every SCD30 bus declares 200000 | generator-enforced; a 150 ms stretch holds the loop once a day, far under the 8 s watchdog |
| H34 | safe | write, 50 ms sleep, separate `readinto` `:477-487` | > 3 ms read header delay met; a NACKed pointer byte is SF-A01 |
| H35 | safe | `reset()` waits 2.5 s `:585-589` | > the documented < 2 s boot |
| H36 | safe | `read_measurement()` only from `_read_scd()`; getters are cache reads `:523-532` | one reader of the data-ready flag |
| H37 | WO | stuck-high `:411-420`; stuck-low → M.SRC_SENS.055 `FRCState` 0 | partial; consumers: M3-01 |
| H38 | refuted | SGP40 DS 3.1 `ds:sgp40__…Datasheet_SGP40.txt:351-358` | continuous heating IS the normal 1 Hz measurement mode ("every second without turning the heater off"); every task start ends with the general-call reset to idle (`:695`); WO adds `turn_heater_off()` as the participant rung (M.SRC_SENS.065) |
| H39 | owner | as C111 | OR64 |
| H40 | owner | `initialize()` `:670-695` | OR18.a (owner, 2026-09-25): a defective chip escalates to a reboot, intended |
| H41 | owner | 1 s PERIODIC timer `:468-477`; skip `:276-281` | gaps from missing compensation are the owner's skip rule (C102); a loop hold > 1 s coalesces one tick (ThreadSafeFlag) — bounded by one flash flush per config PUT |
| H42 | WO | `:597-609` | M.SRC_SENS.068 clamp to Table 10's range |
| H43 | SF | BMP390 DS `ds:bmp3xx__bst-bmp390-ds002.txt:458, 1394` | SF-B9 = SF-A05 |
| H44 | SF | ERR_REG `ds:…ds002.txt:1322-1324` | `fatal_err` is SF-A05; `conf_err` "only working in normal mode" — refuted for this forced-mode driver |
| H45 | safe | `setup()` `:623-632` → `reset()` 0xB6 with `cmd_err` check `:634-646` | whatever state a slow ramp leaves, init puts the chip in a defined, verified state |
| H46 | NEW | `:483-487` | M3-02 |
| H47 | WO | BOUTF read each cycle `:397-404` | M.SRC_SENS.076 (warn every brownout, re-apply) |
| H48 | safe | `reset()` verifies CONFIG1-3 read back 0 (`:1429-1439`) | |
| H49 | SF | ISL DS "the serial communication … resets itself without performing the read/write" `ds:isl29125__…:445-449` | a write so lost is a NACK the controller sees: SF-A01; a corrupted-but-ACKed byte is M3-04 |
| H50 | safe | one status reader (`read_status()` in `_read_isl()` only); dev `irq_pull_up = false` with the board's own pull-up (`devices/dev.toml:96-105`) | a dead line is caught by the periodic-only detector (W32 after WO) |
| H51 | NEW | SYNC/CONVEN live in CONFIG1/3, compared only on a GET or after a failed write | M3-04 |
| H52 | safe | `neopixel_signal()` writes (0,0,0) at task start `asy_neopixel_driver.py:159-161` | every boot that reaches the task list clears it; only a firmware that never starts its tasks (D2/D4 modes, other slice) leaves the colour |
| H53 | refuted | SPEC A.6 `:370-372` | "supplied from USB 5 V behind a level shifter, so the data-line voltage levels are settled (owner, 2026-09-25)" |
| H54 | safe | `machine.bitstream` IRQs off ≈ 30 µs per 1-LED write (first pass A, "WS2812/NeoPixel") | below one UART character time at 115200; ring receive after WO |
| D24 | WO | every stored tick in `src/` (grep): ISL `_last_switch_ms`, `_cal_until_ms`, `_cal_meas_until_ms`, `_settle_until_ms`; UART `_holdoff_deadline`; all others are function-local spans ≤ seconds | M.SRC_SENS.079/.081/.086 (ISL), M.SRC_NET.160 (UART); `_cal_until_ms` safe (read only during a ≤ 120 s run); none in the generated modules |
| D25 | refuted | rp2: `MICROPY_EPOCH_IS_1970`, no Y2100/Y1969 support → `MICROPY_TIMESTAMP_IMPL_UINT` (`py/mpconfig.h:1079-1093`); `time_mktime()` returns `mp_obj_new_int_from_uint()` (`extmod/modtime.c:93`, `shared/timeutils/timeutils.h:86-92`) | unsigned 32-bit seconds, valid to 2106; nothing raises in 2038. The "~2037 OverflowError" source comments are stale; WO removes them (M.SRC_CORE.032 "OverflowError/OSError unreachable on target", M.SRC_NET.053, M.SPEC wall-clock paragraph "valid to 2106") |
| D27 | safe | SCD30 `math.isfinite` `:626`; BMP range comparisons reject NaN/inf `:486`; `math_helpers` return `None` on NaN/out-of-domain; ISL `ema_step` `isfinite`, `min/max` clamp `:523` | no published float in this slice can be non-finite |
| D28 | safe | pack sites: `print_log.py:251` (`<H`, count clamped to `_MAX_CNT`), `:252` (`B`, bound-checked `:179-183`), FRAM TS `<Q` (`asy_fram_manager.py:35`), ISL thresholds clamped to `ceiling` (`:1166-1170`), payloads `Ns` exact length, CRC widths, VOC `32q` range-checked (M.SRC_SENS.017) | no site can be handed an out-of-range value |
| E20 | SF | BMP3XX self-reset reverts OSR/IIR | SF-B9/SF-A05; ISL brownout handled (H47); SCD30 settings in NVM; SGP40 and WS2812 self-resets have no detector: M3-09 |
| E21 | owner | USB CDC `mp_usbd_cdc.c:102-142` | "an accepted debug-mode limitation (owner, 2026-09-30)" (M_SPEC.md:621-626); `DebugLevel` 0 prints nothing |
| E22 | NEW | RP2040-E15 `ds:pico w__RP-008371-DS-1-rp2040-datasheet.txt:29715-29737` | M3-08 |
| E23 | owner | FRAM torn write `asy_fram_manager.py:172-177`; littlefs commit at close | FRAM: "hard failure, never a guess" (owner, 2026-07-18; first pass A-13); flash: old file survives (first pass B table); SCD30 NVM write cut by power: Phase C open-points row in the register |
| E24 | WO | SGP40 RH > 100 wraps `:607` | M.SRC_SENS.068 clamp. Note: WO M.SRC_SENS.057's SCD30 gate accepts RH ≤ 100 inclusive; whether the SCD30 ever reports > 100 % in condensation is not stated in its datasheet (Table 2 range 0-100) — if it does, it falls under M3-02 |
| E25 | NEW | BMP `:486`; SCD30 range gate (WO M.SRC_SENS.057, −40..70 °C) | M3-02 |
| E26 | WO | darkness: low-range threshold 0 fires on "below or equal" (`ds:isl29125__…:877`) | M.SRC_SENS.075 parks INTSEL when a flagged crossing gets no decision; saturation flagged `Overrange` (C128) |
| E27 | WO | C121/C122 | M.SRC_SENS.079/.086; fixed-range-then-auto passes `set_range_auto(True)` → `_switch_range()` `:972-979` |
| E28 | WO | ASC needs daily fresh air (`ds:…Interface_Description.txt:823-829`) | firmware cannot detect fresh air; M.SRC_SENS.051 puts the requirement in the `SelfCal` description |
| E29 | owner | unplug → reads fail → restart → reboot loop until replugged | OR18.a (owner, 2026-09-25); a hot replug of BMP3XX between reads returns with defaults: SF-B9 |
| E30 | WO | SDA held low → every transfer fails | M.SRC_SENS.008 (boot clear) and M.SRC_SENS.010 (`clear()`/`recover()` rungs, A.U13.R01) |

## (B) Findings

### M3-01 A frozen producer sample is consumed as current by the notifications and by SGP40's compensation (class 4)
- **Site**: `src/asy_notification_service.py:194-216` (`_check_one()` reads `getattr(data, field)`, no `TS` test);
  `src/asy_sgp40_driver.py:266-281` (compensation read, no `TS` test); the producers keep their last good sample with
  its original `TS` (owner rule, OR94.a (13), A.U15.22) and the SCD30 republishes it with `FRCState` 0 once idle
  (WO M.SRC_SENS.055).
- **Mode**: sensor stopped while its task stays alive — SCD30 `ContMeas=Off` PUT, RDY line broken/stuck low after data
  has flowed (C96, H37), a chip that stops measuring; SGP40 skipping for missing compensation (its last VOC stays).
  Degraded running for days. Covered nowhere: SF-B17 covers the opposite case (value `None` → inactive).
- **Failure**: none of these paths returns `None` after the first good sample, so `_check_one()` keeps comparing a
  frozen CO2/RH/VOC against the threshold: a WarnCO2 flash repeats forever on a value hours old, or never comes though
  the room changed; SGP40 keeps compensating with the frozen T/RH (its owner rule says "Skip if unavailable", and a
  frozen value is not recognised as unavailable). Only the page's `TS` age (and, after WO, `FRCState` 0) shows it.
- **Effect**: all six devices (warn_co2/warn_hum/warn_voc and SGP40 compensation are wired everywhere, i2c0 or i2c1).
- **Owning units**: U22 (notification), U15 (SGP40).
- **Minimal fix (OR149)**: a bound on the field the sample already carries — the consumer treats a sample whose `TS`
  is older than a fixed horizon (a constant of a few producer intervals, tag `@tunable`) as `None`, which then takes
  the existing paths (notification not triggered + SF-B17's reason; SGP40 skips per the owner rule). A `TS` of `None`
  (before the first NTP sync, WO `utc_now()`) is treated as current, as today. No new state or task.

### M3-02 An environmental reading outside the datasheet range escalates like a bus fault, under the bus-fault errno (class 7; OR18 tension)
- **Site**: `src/asy_bmp3xx_driver.py:483-487` (operating range gate → `ValueError` → `_read_bmp()` errno 11 `:195`);
  WO M.SRC_SENS.057 adds the same shape to SCD30 (A.U15.01, approved, owner, 2026-09-29, OR101.a) under errno 11.
- **Mode**: physical environment (temperature below −40 °C / above 85 °C at BMP3XX, outside −40..70 °C at SCD30;
  possibly RH > 100 % in condensation, unconfirmed); a sensor moved, a device placed near a heater.
- **Failure**: six consecutive rejects end the task (`_error_check()` `base_classes.py:212-223`), the WO ladder then
  resets the device and clears the bus (A.U10.R01) and the supervisor's bucket reboots the board
  (`system_service.py:249-254`): an "abnormal but harmless situation … just ending the task" (OR18, owner, 2026-09-25),
  while OR18.a's exclusion covers only a missing/defective/stalled chip. The persisted entry is errno 11 (READ), the
  same as a bus fault; the value that tripped the gate is console-only.
- **Effect**: BMP3XX on dev (i2c0) and wozi (i2c1); SCD30 on all six (after WO). Indoors the ranges are practically
  unreachable; the cost is a misleading log and a reboot loop if it ever happens.
- **Owning unit**: U15.
- **Minimal fix**: make it visible first — a distinct catalog code for "reading outside the datasheet range" in the
  existing gate's `except` path (both drivers), so the errcount tells environment from bus. Whether such a reading
  should count toward the streak at all is a behaviour question against OR18/OR18.a; the conservative, reversible
  default is to leave the escalation unchanged and log it for the owner review.

### M3-03 The SCD30 soft reset at every task start may abort automatic self-calibration's first 7-day search (class 6, unconfirmed)
- **Site**: `src/asy_scd30_driver.py:577-589` (`setup()` → `reset()` 0xD304 on every boot and every SCD30 task
  restart); WO adds a third caller, the participant rung `_recover_device()` (M.SRC_SENS.054, A.U15.R01).
- **Layer below**: Interface Description 1.4.10: soft reset "forces the sensor into the same state as after powering
  up" (`ds:…Interface_Description.txt:1494`); 1.4.6: during the first ≥ 7 days after ASC is activated "the sensor may
  not be disconnected from the power supply, otherwise the procedure to find calibration parameters is aborted and has
  to be restarted from the beginning" (`:822-826`). Whether a soft reset counts as that disconnection is not stated.
- **Mode**: sensor modes (calibration, recovery), boot, boot loop, each reboot of the MCU (which would otherwise not
  touch the SCD30's supply).
- **Failure**: if the soft reset counts, every firmware reboot or SCD30 task restart in the first week restarts the
  ASC search; nothing logs it, and WO's `SelfCal` description (M.SRC_SENS.051) names only a power loss.
- **Effect**: SCD30 on all six devices, only while ASC's first parameter set is being found.
- **Owning unit**: U15 (doc: U36).
- **Minimal fix**: visibility — the `SelfCal` description and SPEC A.4 state that the firmware's soft reset (every
  boot, task restart and recovery rung) is equivalent to a power-up per 1.4.10 and may restart the first-week search;
  a Phase C/owner item whether the boot-time soft reset is needed at all on a warm MCU reboot. No code.

### M3-04 ISL29125: the shadow-vs-chip comparison runs only after a failed write or on a GET (class 3)
- **Site**: `src/asy_isl29125_driver.py:481-493` (`_verify_after_failed_write()` returns at once unless
  `write_failures()` moved), `:716-728` (`_read_sensor_dict()`, reached only by `GET /sensors`).
- **Layer below**: no CRC on this part; a bus glitch can corrupt a written byte that the chip ACKs (ISL DS: only a
  STOP mid-byte is ignored, `ds:isl29125__…:445-449`); the status byte carries BOUTF only for a supply reset.
- **Mode**: bus disturbance, a peripheral resetting part of its state without BOUTF, a corrupted CONFIG1/3 bit (H51:
  SYNC=1 turns INT into an input; mode bits stop conversion; RNG/BITS bits scale lux by 26.7× / 16×).
- **Failure**: on a headless device nobody issues a GET, so the divergence detector — which exists — never runs; a
  stopped conversion republishes the same counts with a fresh `TS`, a wrong range bit publishes wrongly scaled lux
  under the shadow's `RangeAct`.
- **Effect**: dev only (i2c1, with SCD30 and SGP40). Also the class sibling of SF-B9 (BMP3XX) swept here.
- **Owning unit**: U15.
- **Minimal fix**: remove the `seen == self._reconciled_write_failures` early return's exclusivity — run the existing
  snapshot comparison every read cycle (one 3-byte burst, ≈ 1 ms at 50 kHz), keeping the counter for its own purpose.
  No new state.

### M3-05 A SGP40 task restart restores the FRAM backup over the live VOC algorithm state (class 4/6)
- **Site**: `src/asy_sgp40_driver.py:331-361` (`_init_sgp()` re-arms `voc_init` at every task start), `:364-396`; the
  algorithm object lives on `SGP40_I2C` and survives the restart (`:649-651`; WO builds it in `__init__`,
  M.SRC_SENS.067). WO M.SRC_SENS.063/.065 keep the restore at every init.
- **Mode**: recovery / task restart (six failed reads, a supervisor restart), combined with `BackupPeriod` 0
  (backups off) and `BackupMaxAge` 0 (any age) — both owner-confirmed values (C108).
- **Failure**: the restored state is up to one `BackupPeriod` older than the live one (≤ 1 min at the default, up to
  1440 min), and with backups off it is whatever backup FRAM still holds, possibly days old; the learned baseline
  jumps back silently. After WO only `VOCState` 3 / `RestoreTS` hint at it.
- **Effect**: all six devices (SGP40 + FRAM everywhere).
- **Owning unit**: U15. D.1 flag (verify against the legacy driver's field behaviour first).
- **Minimal fix**: test state that already exists — skip the restore when the in-RAM algorithm has been fed since boot
  (WO's `_voc_samples > 0 or _voc_restored`, A.U15.19); a boot still restores.

### M3-06 `LockableBuffer`/`RegionBuffer` swallows an allocation failure without its text; callers then misreport it (class 4; SF-A12's class)
- **Site**: `src/base_classes.py:60-72` (`except (MemoryError, OverflowError): self.buf = None`); WO M.SRC_CORE.027
  keeps it ("comments `:60-68` kept"). Callers: `asy_fram_manager.py:430-466, 512-575` (`get_buffer()` per operation,
  A.U16.05) return `False`/`(False, None, None)` on `buf is None`; `print_log.py:244-254` → `_diag("History write
  failed")`; SGP40 `_run_restore()` `:374-378` reads it as "No backup found!" and sets `voc_init = 0`.
- **Mode**: heap near full / fragmented heap over long uptime; boot (restore attempt).
- **Failure**: the four memory gates (CLAUDE.md: `MemoryError` or "memory allocation failed") never see this caught
  failure, so a degrade-and-pass hides it; in production a transient allocation failure at the restore moment abandons
  the SGP40 restore for the boot (24 h relearn) under a "no backup" label — after WO M.SRC_SENS.063 it reads as a
  blank first-boot chunk, console only; an error-log write is skipped silently.
- **Effect**: all six devices (FRAM, every FRAM-backed logger, SGP40 backup); twin and unit tiers' gates.
- **Owning unit**: U16 (U30 for the memory rule).
- **Minimal fix**: emit `str(e)` once in that `except` arm (the class has no logger: one `print`, as SF-A12 proposes
  for the UDP wrapper), so the gates and the console see "memory allocation failed"; SGP40 treats a `None` buffer as an
  allocation failure, not as "no backup" (its `_check_storage()` already holds the buffer and can test it).

### M3-07 UART `ResetErrors` zeroes `_valid_frames`, re-arming "link unintelligible" on a working link (class 3)
- **Site**: `src/asy_uart_comm.py:1140-1149` (`reset_error_counter()` sets `_valid_frames = 0`), kept by WO
  M.SRC_NET.171; the diagnostic `:575-582` fires after `_DIAG_RESYNC_STREAK` (2) resyncs with bytes while
  `_valid_frames == 0`; WO M.SRC_NET.162 also counts discarded bytes, which makes a single noisy frame qualify.
- **Mode**: UART link after a `ResetErrors`; two faults in a row (jumper disturbed, peer reset mid-frame) before the
  next valid frame.
- **Failure**: E32/E89 "check CRC algorithm, baud rate and payload_size" is persisted for a link that has worked for
  days — the wrong diagnosis, in the very history the operator just cleared to watch.
- **Effect**: dev only (both instances).
- **Owning unit**: U17 (Class B changelog line, no wire change).
- **Minimal fix**: keep `_valid_frames` across `reset_error_counter()` (it is link evidence, not error history); drop
  that one line from the reset.

### M3-08 RP2040-E15 on the bench host: the Pi 4's VL805 can hang the USB device controller (class 6, bench)
- **Site**: `tests_hardware/` bench runs over USB from the Pi 4 (CLAUDE.md, SPEC B.13); no mention of E15 in
  `SPECIFICATION.md`, `tests_hardware/README.md`, `BACKLOG.md` (grep).
- **Layer below**: RP2040 datasheet RP2040-E15: with a VL805 xHCI (Raspberry Pi 4 downstream ports) and Bulk IN
  buffers > 50 bytes the USB device controller "enters an unrecoverable state"; workaround VL805 firmware 0138c1
  (`ds:…rp2040-datasheet.txt:29715-29737`). CDC bulk IN is 64 bytes.
- **Mode**: host side, USB attached to the bench Pi 4.
- **Failure**: the board's console/`mpremote` path dies until a power cycle; a bench run reads it as a device hang.
- **Effect**: dev bench only; firmware unaffected at `DebugLevel` 0.
- **Owning unit**: U26 (bench prerequisites; doc U36).
- **Minimal fix**: one prerequisite line in `tests_hardware/README.md` naming E15 and the required VL805 firmware, and
  a read-only version check in the bench preflight. No firmware change.

### M3-09 Self-resets with no detector on the part: SGP40 and the WS2812 (class 1/7, low)
- **Site**: `src/asy_sgp40_driver.py` (no status/POR read exists: SGP40 DS Table 8 has none); `asy_neopixel_driver.py:
  70-77` (overlay written only when `on()`/`off()`/a signal end sets `led_overl_start`).
- **Mode**: a peripheral that resets on its own (supply sag under WiFi bursts, E20).
- **Failure**: SGP40 returns to idle; the next measure command restarts measurement with a cold hotplate, so a few
  raw samples are off and the VOC index (and `warn_voc`) can spike; nothing records why. A WS2812 power glitch blanks
  the pixel while the driver believes the WiFi overlay is lit, until the next notification flash or WiFi state change.
- **Effect**: all six devices; low.
- **Owning units**: U15 (SGP40 doc), U22 (LED).
- **Minimal fix**: record why it cannot be read (one sentence in SPEC M.3 and the SGP40 header, per the scan's class 1
  rule); for the LED, rewrite the overlay pixel on an event that already recurs (the end of each notification check
  already sets `led_overl_start` after a flash — do the same once per monitor cycle). No new task or timer.

## (C) Scenario walks

**Sensor modes (warm-up, calibration, recovery, absent, returning).** Boot: SCD30 soft-resets and waits 2.5 s, its
first edge follows one interval; SGP40 skips (owner rule) until SCD30 data exists, then runs its 45-sample blackout
(`VOCState` 0 after WO); BMP3XX's first forced read and ISL29125's two settle cycles follow; notifications see `None`
(SF-B17); `TS` is `None` until NTP (WO). Calibration: SCD30 FRC readiness is informational (WO, never refused);
ISL29125's run outcome is SF-B11; ASC is M3-03. Recovery: WO's ladder adds per-driver rungs; SCD30's rung is a soft
reset (M3-03), SGP40's restart restores the backup (M3-05). Absent for good: OR18.a reboot loop, intended. Returning:
picked up at the next boot; a hot return between reads is SF-B9 for BMP3XX, BOUTF for ISL29125, NVM for SCD30, and
M3-09 for SGP40. Missed by the rows: M3-01 (a stopped-but-alive producer).

**A peripheral that resets on its own.** SCD30: NVM keeps interval, ASC, offset, altitude and the measuring flag;
`AmbPres`'s value persistence is undocumented (SF-B9 note); FRC read-back drops to 400 (WO doc). BMP3XX: SF-B9/A05.
ISL29125: BOUTF caught each cycle (WO warns each time); a partial corruption without BOUTF is M3-04. SGP40 and WS2812:
M3-09. FRAM: other slice.

**Buses (wedged, contention, general call).** Wedged SDA: WO's boot clear and runtime rungs (E30); a stretched SCL holds
the loop synchronously up to the bus timeout (200 ms on SCD30 buses), the watchdog stays the backstop (owner,
2026-07-24). Contention on dev i2c1: SCD30 holds the bus lock through its 50 ms command waits (`_send_dev_command`
`:470-471`, `_read_dev_register` `:480-484`), up to ~300 ms for a config snapshot; SGP40's 1 Hz cycle (≤ 300 ms wait +
100 ms measure) and ISL29125 still fit their periods — delayed, not lost; checked, nothing silent. General call: owner
(OR64); reaches BMP3XX on wozi and SCD30/ISL29125 on dev; none of their datasheets documents a response.

**UART link (idle, peer reset mid-frame, both dev instances).** Idle: the responder parks in an unbounded listen at the
50 ms rate and clears its hold-off on every listen (`:988-991`); an idle initiator's aged hold-off is M.SRC_NET.160.
Peer reset mid-frame: the partial frame fails on the character timeout, the fault resyncs and holds off; a held-low
line inserts break bytes (SF-A06); after a peer reboot its boot drain is uncounted by design. Both instances: separate
locks and loggers; a config flush that holds the loop past the initiator's 1000 ms ACK deadline fails that transaction
visibly on both sides (counted Failures, E20/E22 persisted once per run) and the next succeeds; the ring keeps every
byte (WO M.SRC_NET.221). Missed by the rows: M3-07.

**Physical environment.** Condensation: SGP40 clamp (WO); SCD30 gate inclusive at 100 % (E24 note). Temperature
extremes: M3-02. Light: darkness INT storm parked (WO), saturation flagged `Overrange`. Stable conditions for days: tick
gates (WO). No fresh air: SelfCal description (WO). Supply sag: E20/M3-09. Unplug: OR18.a.

**Long uptime, tick arithmetic.** Every stored `ticks_ms()` value in `src/` (grep `ticks_ms|ticks_add|ticks_diff`): ISL
`_last_switch_ms` (WO .079), `_cal_until_ms` (read only inside a ≤ 120 s run, safe), `_cal_meas_until_ms` (WO .081),
`_settle_until_ms` (WO .086), UART `_holdoff_deadline` (WO M.SRC_NET.160); every other use is a function-local span
of milliseconds to seconds (BMP STATUS poll, UART drain/cancel/ready, UDP ready, notification `_next_sleep_secs`); the
generated modules store none. One residual checked and closed: WO .079's clamp tests `elapsed > _MAX_DWELL_MS` only, so
a tick already older than 2**29 ms would read negative and slip it; every path that leaves the branch unevaluated for
days passes `_switch_range()`, which refreshes the tick. Counters in this slice are bounded or capped by WO. Wall-clock
stamps run to 2106 (D25).

## (D) Counts per verdict (90 IDs)

| verdict | count | IDs |
|---|---|---|
| refuted | 3 | H38, H53, D25 |
| safe | 22 | C100, C114, C119, C120, C126, C128, C149, C155, C156, C157, H31, H33, H34, H35, H36, H45, H48, H50, H52, H54, D27, D28 |
| owner | 16 | C94, C99, C102, C108, C109, C111, C116, C152, C154, H30, H39, H40, H41, E21, E23, E29 |
| WO | 32 | C96, C98, C101, C103, C104, C106, C107, C110, C112, C118, C121, C122, C123, C124, C127, C148, C150, C151, C153, C158, C159, C160, C161, H37, H42, H47, D24, E24, E26, E27, E28, E30 |
| SF | 7 | C95, C113, C117, H43, H44, H49, E20 |
| NEW | 10 | C97, H32 (M3-03); C115, H46, E25 (M3-02); C125, H51 (M3-04); C105 (M3-05); C162 (M3-06); E22 (M3-08) |

Partial covers that point to a finding: C94/C96/C102/H37 (WO/owner, residual M3-01), C152 (owner, residual M3-07),
H49 (SF-A01, residual M3-04), E20 (SF-B9, residual M3-09). Findings from the crossed pass only: M3-01, M3-07, M3-09.
