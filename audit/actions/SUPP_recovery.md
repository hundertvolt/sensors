# A-L supplement — recovery-ladder pass over U10, U13, U15, U16, U17, U18 (HEAD 5469a09)

Why: OR113 (owner, 2026-09-30) "always try to solve / recover from issues with the smallest possible blast radius …
escalating up to a full bus reset is absolutely allowed if the mild measures don't work out. Apply this idea
throughout!"; OR113.a (2) gives the ladder — retry the transaction → recover the one participant (its own reset command
or re-configuration) → clear the bus (SCL clock-out and STOP, under the bus lock) → re-initialise the bus controller →
restart the task → reboot → hardware watchdog last; each rung bounded, logged once per event (OR35.b, OR56.a (1)),
race-free under the device-session model (OR109.a), tested at every level that can reach it; the SGP40 general-call reset
stays the one owner-accepted reset reaching other devices; an in-flight rp2 transfer cannot be interrupted (G4/R22), so
the ladder acts after a transfer returns an error. OR113.a (1): each I2C bus is cleared once at boot before its
controller is constructed (A.U14.17 option (a)). Register: G4/R22 (rewritten), G4/R44 (lwIP, OR112.a — A.U14.30 and the
U19 `TCP_NODELAY` action own it; not repeated here), harmonization 38.

Method: every `except`, error return, retry/give-up, supervisor restart and reset command in the files the six units own
(plan 5.0: BUS `asy_i2c_driver.py`, `asy_spi_driver.py`, `asy_uart_driver.py`; SENS the four sensor drivers; STOR
`asy_fram_driver.py`, `asy_fram_manager.py`; UART `asy_uart_comm.py`, `asy_uart_link_driver.py`; NET
`asy_wifi_service.py`, `asy_ntp_client.py`, `asy_dns_client.py`, `captive_dns.py`, `asy_udp_socket.py`; XCUT the
cross-cutting escalation contract in `base_classes.py`'s `_error_check()` and the supervisor it hands off to) was opened at
HEAD `5469a09`; `git diff --stat <unit HEAD> 5469a09 -- src/ buildgen/ tests/ tests_hardware/ digital_twin/
SPECIFICATION.md CLAUDE.md` is empty for every unit file's HEAD (`4a84b57`, `cc9c8b0`, `02b631e`, `c202e16`, `3d0ba2e`),
so their line citations hold. Rungs owned elsewhere are referenced, never repeated: boot bus clear A.U14.17 (a); lwIP send
sizing A.U14.30 / OR112.a; supervisor reboot path A.U11.03/A.U11.05 (U11); one entry per task death A.U3.06; the UART
ladder V.U17.20 / A.U17.33. rp2 facts cite MicroPython v1.29.0 in the scratchpad `mp/`; the pinned pico-sdk submodule
is **not** checked out there (`mp/lib/pico-sdk/` is empty), so what `i2c_init()`/`spi_init()` do to the peripheral block
is stated as unread, never assumed. Datasheet text from the scratchpad `dstxt/`. Permanent text quoted in the actions
carries no audit ID (rule 6).

New catalog codes requested from A.U2.01 (A-C merges): shared wrnno `DEVICE_RECOVERY` "a participant recovery (the
chip's own reset or re-configuration) ran after repeated failures" and `BUS_RECOVERY` "the I2C bus was cleared and its
controller re-initialised after repeated failures", written here as 14 and 15 because shared wrnno 11 is already claimed
twice (A.U15.24 `DERIVED_DOMAIN`, A.U18.15 `SOCKET_TEARDOWN` — Conflicts 7); FRAM errno 54 `FRAM_CHIP_LOST` "the chip
stopped answering its identification; FRAM access stopped until it is set up again" (FRAM band 45-54; 52, 53 taken by
A.U13.09, A.U16.15).

Rung abbreviations in the tables: R1 retry · R2 participant · R3 bus clear · R4 controller re-init · R5 task restart ·
R6 reboot · R7 watchdog.

## Rung tables

### U10 — XCUT: the escalation contract

| fault path | rungs at HEAD (evidence) | rungs by existing actions | missing → action / disposition |
|---|---|---|---|
| a sensor/WLAN cycle fails (`_error_check()` `src/base_classes.py:218-230`; callers SCD30 `asy_scd30_driver.py:407`, SGP40 `asy_sgp40_driver.py:530`, BMP3XX `asy_bmp3xx_driver.py:392`, ISL29125 `asy_isl29125_driver.py:1048`, WIFI `asy_wifi_service.py:836`) | R1 the next triggered cycle (each `read_loop()`'s `read_event`); streak count `:221-223`; R5 give-up `:224-226` → the task returns `False` → supervisor restart `system_service.py:229-241` (`_init_*()` re-runs setup: probe, ID, the chip's reset — R2 fused into R5); R6 budget past `_TASK_FAIL_MAX` `:249-253`; R7 feed only in the supervisor loop `:248-249` | A.U3.03 (streak increase prints, give-up persists); A.U10.23 (budget arithmetic); A.U11.03/A.U11.05 (reboot path, reason); A.U10.08 (single feed site) | **R2 and R3/R4 between R1 and R5 missing** — no participant recovery and no bus recovery before the task ends and spends restart budget; a task restart does not rebuild the bus (SPEC F.2 `:3617-3623`) → **A.U10.R01** (contract, hooks, thresholds, logging), hooks A.U15.R01-R04, A.U18.R01; bus primitive A.U13.R01 |
| a reader's `_init_*()` fails (errno 10: SCD30 `:169`, SGP40 `:339`, BMP3XX `:204`, ISL29125 `:298`) | R2 inside setup (probe, ID, reset), R5 by returning `False`, R6, R7 | A.U10.21 (`setup() -> bool` contract); A.U14.17 (a) boot clear at construction only | **R3/R4 missing before R5/R6**: a held bus survives every task restart and reaches a reboot, whose boot clear then frees it — a bigger blast radius than a bus clear → **A.U10.R01** (5) `_init_failed()`, called from each driver (A.U15.R01-R04) |
| any supervised task ends (return, raise, cancel) | R5 restart `system_service.py:229-241`, R6 `:249-253`, R7 | A.U3.06 (one entry per death), A.U11.03 (one awaited `_reboot()`), A.U10.09 (starve fallback described); L3 `tests_hardware/device_scripts/system_service_restarts_a_real_dead_task.py`, `reboot_fallback_starves_the_watchdog.py`, `watchdog_starvation_reset.py` | DONE-AT-HEAD with those actions: bounded (100 per death, decay 1 per 2 s, reboot past 300), logged once per death, L1 `tests/test_system_service.py`, L2 `tests/test_digital_twin_sensortask_integration.py:421`, L3 the three scripts |
| a Timer arm fails (alarm pool, `OSError(ENOMEM)`/`MemoryError`) | none: printed, the sensor stays untriggered until reboot (e.g. `asy_scd30_driver.py:219-221`) | A.U15.41 (task wakes, persists, ends; its restart re-arms), A.U18.23/A.U18.24 (NTP, WIFI), A.U10.12 (trigger starts in task context) | covered by those actions: R1 = re-arm on restart, R5, R6 by budget |
| a blocking `machine.I2C`/`machine.SPI` transfer never returns | R7 only | — | disposition: no await point exists inside the call (`ports/rp2/machine_i2c.c:120-158` blocking `i2c_*_timeout_us()`; `machine_spi.c:265-342`), so no rung below R7 can run while it is in flight (G4/R22 fact kept by OR113.a); rp2's I2C transfer is itself bounded by the bus `timeout` (`machine_i2c.c:125, 147` pass `self->timeout`), so a held SDA normally returns `ETIMEDOUT` and the ladder then acts; the unbounded case left is the watchdog's |
| the supervisor loop dies or the loop blocks | R7 | OR31.a (5) planted-fault tests (U10/U24 per register G5/R01) | DONE by design: R7 is the last rung |
| a deferred config flush fails (`config_manager.py` `_flush_staged()`) | error logged, values stay in effect (C.7.3) | A.U10.20 (task top persists 23), A.U11.19/A.U11.20 | disposition: R1 is the next accepted `PUT`'s flush or the next boot's one repair of a readable file (OR71.a (2)); an automatic re-write would be a flash write no request asked for, which the owner's write rule forbids (CLAUDE.md wear rule; OR42.c) |
| FRAM `verify_present()` lock wait times out (`asy_fram_driver.py:407-411`) | returns `False`, errno 97 (19 after A.U2.01) | A.U10.26 (`wait_for_ms`) | disposition: no product caller (grep `verify_present(` in `src/`, `buildgen/`: none); A.U16.R03 gives the chip-loss path its own call site under the bus lock instead |

### U13 — BUS: I2C, SPI, UART bus layer

| fault path | rungs at HEAD (evidence) | rungs by existing actions | missing → action / disposition |
|---|---|---|---|
| I2C transfer raises `OSError(EIO)` (NAK, bus error) or `OSError(ETIMEDOUT)` (held/stretched line) — `_read_into_scratch()` `src/asy_i2c_driver.py:58-68`, `_writeto_mem()` `:70-75`, `readfrom_into()` `:194-208`, `writeto()` `:210-231`; raise surface `ports/rp2/machine_i2c.c:150-155` | propagates to the driver (header `:4-6`): R1/R2/R5 are the driver's and the supervisor's (U10 table) | A.U13.07 (bool results), A.U13.09 (drivers raise on an unavailable bus) | **R3 bus clear and R4 controller re-init mid-operation missing** — the wrapper has no way to release a held SDA or rebuild the controller after construction (`init()` `:163-178` is reached only from `__init__` `:37`) → **A.U13.R01** (`I2C.recover()`), escalated by A.U10.R01, four-tier coverage **A.U13.R02** |
| I2C bus held at power-up / after an MCU-only reset (a slave stopped mid-byte) | none: construction drives no SCL pulse (`machine_i2c.c:106-115`) | A.U14.17 option (a) (boot clear before construction; no longer pending, OR113.a (1)) | R3 at boot owned by A.U14.17; its runtime twin is A.U13.R01, sharing one clock-out function; its "never at runtime" wording conflicts (Conflicts 1); the boot result is logged through A.U10.R01's `_init_done()` |
| a slave holds **SCL** low (stretch past the bus timeout, stuck clock) | transfers end `ETIMEDOUT` (`machine_i2c.c:151-152`) | — | disposition for R3: a clock-out needs SCL; A.U13.R01 waits for SCL release up to the bus timeout (a legitimate SCD30 stretch is ≤ 150 ms, Interface Description p.2, under the 200 ms `@requires` timeout `asy_scd30_driver.py:108`), then reports `SCL held` and still runs R4; what frees a slave holding SCL is its own reset (R2, if its interface still answers) or a power cycle — an operator action (A.U14.17's DEVICE_REFERENCE line, U36) |
| I2C `scan()` never raises; a wedged bus shortens the list (`extmod/machine_i2c.c:341-356`) | caller's problem (`scan()` has no product caller: grep `.scan(` in `src/` → `asy_i2c_driver.py:192` only) | — | disposition: no product fault path |
| zero-length probe NAK → `ValueError("No I2C device …")` (`_probe_for_device()` `:261-273`) | at setup only: the reader's `_init_*()` fails (errno 10) → R5 → R6 | A.U10.21 (`setup()` contract), A.U8.13 (`_PROBE_SETTLE_S`) | R3/R4 before R5 via A.U10.R01 (5) `_init_failed()`; note: the probe runs rp2's soft-I2C path on the same pins (`machine_i2c.c:127-145`), which treats a held-low SDA as an ACK, so a held bus is found by the first real transfer, not by the probe — nothing to change, the ladder acts on that transfer's error |
| I2C/SPI construction raises (`ValueError` bad id or pin, `machine_i2c.c:82-103`, `machine_spi.c:161-191`) | at boot, uncaught in `build_system()` → boot fails → R7 | — | disposition: a configuration not matching the hardware (OR18 exclusion; OR18.a: escalation to reboot intended); buildgen's pin checks (G4/R25) make it unreachable for a generated device |
| SPI read of 32+ bytes raises `OSError(EIO)` on an RX overrun (`asy_spi_driver.py:75-81, 83-97`; `machine_spi.c:303-316, 340-342`) | propagates to FRAM; the dual copy absorbs one (U16 table) | A.U13.08 (bool results) | disposition for R1-R4 at the bus layer: the port clears the overrun flag itself inside the failing call ("Clear the flag for future transfers", `machine_spi.c:309-310`) and aborts the RX DMA (`:313`), so no latched state is left for a retry, clear or re-init to remove; the retry is the dual copy's (owner, 2026-09-24: "So no retry is added … the dual-copy layer already covers the read path", SPECIFICATION.md:3755) |
| SPI "held bus" | — | — | disposition for R3: an SPI slave drives no shared line while deselected — the FRAM's SO is High-Z whenever CS is high and "inputs from other pins are ignored" (MB85RS64V `dstxt/fram__MB85RS64V…:40-44`, MB85RS2MTA `…:45`); every CS cycle ends with CS inactive, in `finally` (`asy_fram_driver.py:158-162, 166-171, 175-180`) and on a raised `session_begin()` (`asy_spi_driver.py:142-144`) — the SPI "bus clear" is DONE-AT-HEAD on every transaction |
| SPI controller state | `configure()` re-applies baud rate and format on every session (`asy_spi_driver.py:67` → `machine_spi_init()` `machine_spi.c:219-262`) | A.U13.08 | disposition for R4: the controller is re-configured at every session already; a re-construction adds only `spi_init()` (pico-sdk, not in the scratch tree) and the pin function select, which nothing in `src/` changes after construction; no fault class is left for it |
| UART driver fault paths (`asy_uart_driver.py`: short write `:127-141`, `None` reads, `cancel_read_timeout()` `:241-256`, `resync_framing()` `:103-107`, re-init only by construction `:183-222`) | sentinels to the comm layer | V.U17.20 / A.U17.33 (UART ladder in J.5), A.U13.12-A.U13.14, A.U13.18 | cross-reference only (U17 did the pass): R1 the caller's retry, the resync drain as the line-level "clear", `cancel_read_timeout()` bounded by `_CANCEL_ACK_TIMEOUT_MS` and counted (`:251-254`), R4 dispositioned by A.U17.33 (rp2 latches no receive error, `ports/rp2/machine_uart.c:162-190`); U13 adds nothing |

### U15 — SENS: the four sensor drivers

Common to all four (so not repeated per row): R1 is the next triggered read (each `read_loop()` waits on its
`read_event`), R5 the give-up past `max_module_error` (A.U10 table), R6/R7 the supervisor's; REST-triggered get/set
failures (SCD30 errno 12-25 `asy_scd30_driver.py:303-397`, BMP3XX `asy_bmp3xx_driver.py:326-383`, ISL29125 per-field
forwards `asy_isl29125_driver.py:911-1030`) report `None`/`"Failed"` to the caller and feed no streak — disposition: R1
for a request is the client's (the page shows the failure; an automatic re-send of an SCD30 set would be a second NVM
write nobody asked for, CLAUDE.md wear rule), and the bus-level rungs are driven by the periodic read of any reader on
that bus, which fails on the same held bus within one period.

| fault path | rungs at HEAD (evidence) | rungs by existing actions | missing → action / disposition |
|---|---|---|---|
| SCD30 periodic read fails (`_read_scd()` `asy_scd30_driver.py:174-187`: bus `OSError`, CRC `:613-619`, non-finite `:626-627`) | R1, R2 only inside R5 (`_init_scd()` `:161-172` → `setup()` `:577-583`: probe, firmware-version read, soft reset `:585-589`), R5, R6, R7 | A.U13.09 (bus-down raise), A.U15.01 (range gate), A.U3.03 (logging) | **R2 before R5 and R3/R4** → **A.U15.R01** (soft reset as `_recover_device()`, recovery bus, init hooks) + A.U10.R01 |
| SCD30 data-ready interrupt edge missed (pin stays high) | R2-level re-trigger: `scd_init_irq()` `:412-420` counts 500 ms ticks with the pin high and sets `read_event` itself | A.U15.03 (saturating tick count), A.U15.41 (timer arm failure ends and re-arms) | DONE-AT-HEAD: bounded (fires after `trigger_half_sec` ticks, re-armed by the read), no log needed (a recovered edge is not a fault entry; `pr.evt` `:419`); L1 `tests/test_asy_scd30_driver.py` stuck-pin tests, L3 `scd30_real_irq_edge.py` |
| SCD30 goes silent — data-ready never rises again (`read_loop()` waits on `read_event` `:402-403`, set only by the pin IRQ `:222-225` or by `scd_init_irq()` when the pin stays **high** `:412-420`) | none: no cycle runs, so no failure is counted; the last sample stays with its own `TS` | A.U15.12 (`_frc_idle_ticks` publishes "not measuring", FRC state 0, after two intervals without data) | disposition: silence is not a fault signal on this chip — it is also the designed state before the first `AmbPres` PUT starts continuous measurement and after `ContMeas=false` stops it (Interface Description 1.4.1, `SPECIFICATION.md:269-282` owner list; LEAD/R14 operator action), so a rung fired on silence would soft-reset an unprovisioned sensor and, through the streak, reboot the device; A.U15.12's published state is the visible signal; a held bus is still caught, because the data-ready line is a separate GPIO and the next edge's read fails and counts |
| SCD30 setup fails at a task (re)start (errno 10 `:168-170`) | R5 by `False`, R6 | A.U10.21 | R3/R4 before R5 → A.U15.R01 (`_init_failed()`) |
| SGP40 read fails (`_read_sgp()` `asy_sgp40_driver.py:282-328`: bus `OSError`, CRC `:578-580`, CRC generation `:627-631`) | R1; R2 only inside R5 (`_init_sgp()` `:330-340` → `setup()`/`initialize()` `:664-694`: serial, self-test, then the general call `_reset()` `:585-593`); R5-R7 | A.U15.13 (command buffer restored; serial read), A.U15.15 (the general call as the owner's decision), OR109.a (0) race fix | **R2 before R5 missing** → **A.U15.R02** (device-addressed heater-off, not the general call) + recovery bus + init hooks |
| SGP40 skips a cycle for missing compensation (`condition=compensated`, `:530`) | no streak by design | — | disposition: not a chip fault — the SCD30's own ladder covers its source (SPEC A.4 "SGP40 skipping its VOC read … SCD30's own error counter covers it", owner-confirmed list `SPECIFICATION.md:269-282`) |
| SGP40 FRAM backup write or restore fails (`_run_backup()` errno 14 `:427-429`, `_run_restore()` w10 `:373-377`) | R1 the next backup period / the next boot's restore | A.U15.17, A.U15.18, A.U16.06 (unreadable vs invalid) | disposition: the FRAM rungs are U16's (A.U16.R01-R03); the SGP40 keeps measuring (backup is optional, owner "no module insists on FRAM", 2026-08-11) |
| BMP3XX read fails (`_read_bmp()` `asy_bmp3xx_driver.py:185-196`: bus `OSError`, STATUS timeout `_wait_status_bits()` `:541-553`, burst check `:446-447`, operating range `:486-487`) | R1; R2 only inside R5 (`_init_bmp()` `:198-225` → `setup()` `:623-632`: probe, chip ID, calibration, soft reset `:634-645`, then the stored OSR/IIR re-applied `:209-223`); R5-R7 | A.U13.09, A.U13.10, A.U15.25 (conversion wait) | **R2 before R5 missing** → **A.U15.R03** (soft reset plus the stored configuration) + recovery bus + init hooks |
| ISL29125 read fails (`_read_isl()` `asy_isl29125_driver.py:368-431`: status read errno 31 `:389-393`, confirmed bus-fault pattern errno 32 `:406-409`, any other raise errno 11 `:428-430`) | R1; R2 mid-operation for two specific causes — brownout → whole configuration re-applied (`_recover_brownout()` `:465-479`), a failed write → chip read back and diverged configuration re-applied (`_verify_after_failed_write()` `:481-493`, `_check_divergence()` `:745-755`); a `configure()` write failure rolls the shadow back inside the lock (`:1370-1378`); R2 by reset only inside R5 (`setup()` `:1415-1427` → `reset()` 0x46 `:1429-1439`); R5-R7 | A.U15.32/A.U15.33/A.U15.34 (INT park, thresholds, restart state), A.U3.14 (brownout logging), A.U15.S01 (resolution shadow race) | **R2 for a plain read-failure streak missing** (status/data read failing with no brownout) → **A.U15.R04** (the brownout re-apply as `_recover_device()`) + recovery bus + init hooks |
| a driver's chip identification fails at setup (SCD30 firmware read, SGP40 serial/self-test, BMP3XX chip ID `:626-628`, ISL29125 device ID `:1402-1407`) | R5, R6 (OR18.a: a missing/defective chip escalates, intended) | — | R3/R4 once before R5 via `_init_failed()` (A.U15.R01-R04); no further rung: a wrong or absent chip is a configuration fault (OR18 exclusion), which the ladder must not "contain" (OR18.a) — it still reaches the reboot |
| the SGP40 general call reaches the other devices on its bus | fires at every SGP40 setup (`initialize()` `:694`) | A.U15.15 (records it as the owner's decision) | unchanged by this pass: OR113.a keeps it "the one owner-accepted reset that reaches other devices"; A.U15.R02 deliberately does not add a mid-operation general call (the participant rung must reach only the participant); A.U15.15's boundary wording conflicts with OR113.a (Conflicts 2) |

### U16 — STOR: FRAM

FRAM is the only device on its SPI bus in every shipped TOML (`devices/*.toml`: six `bus = "spi0"` attachments, all
`driver = "fram"`), so no rung here can reach another device. The FRAM manager's own log is RAM-only (owner, 2026-09-16,
G5/R32), so FRAM warnings cost no FRAM writes.

| fault path | rungs at HEAD (evidence) | rungs by existing actions | missing → action / disposition |
|---|---|---|---|
| write-enable latch does not set after WREN (`_enable_write()` `src/asy_fram_driver.py:200-205`, used by `_write()` `:228-229` and `_set_write_protected()` `:236-237`) | none: the write is aborted, wrnno 82 (`:345-347`; 26 after A.U2.01) → chunk errno 61/62 → the caller's next write | A.U2.01 (w26 `FRAM_WEL_NOT_SET`), A.U13.09 (bus-down entry check first) | **R1 missing** — the symmetric WRDI already gets one retry (`_disable_write()` `:207-215`) → **A.U16.R01** |
| latch does not clear after WRDI (`_disable_write()` `:207-215`) | R1 one WRDI retry, then advisory wrnno 81 (27 after A.U2.01; payload landed) | A.U2.01 (w27) | DONE-AT-HEAD (R1 bounded to one; logged once per operation, central repeat rule OR35.b); a latch that stays stuck on every write is also a lost-chip symptom → feeds A.U16.R03 |
| chip identification fails at `setup()` (`:381-398`, RDID `:182-188`) | none inside setup; `AsyFramManager.setup()` contains it (`asy_fram_manager.py:730-737`) | A.U16.17 (the result escalates: one supervised task that ends, R5 → R6), A.U16.10 (both locks), A.U10.21 | **R1 missing** before the escalation → **A.U16.R02** (bounded identification retry inside `setup()`, before any logger reads, so A.U16.06's reason against a later recovery does not apply) |
| chip stops answering mid-operation (RDID never re-checked after boot: `verify_present()` `:400-432` has no product caller, grep) | none: every write fails or warns, every consumer degrades to RAM, nothing escalates | — | **R1-R2 detection, R5, R6 missing** → **A.U16.R03** (latch anomalies trigger one identification probe under the held bus lock; a lost chip stops FRAM access and ends the manager's task; its restart re-runs `setup()`; the budget reboots) |
| 32+ byte read raises `OSError(EIO)` (`_read_chunk()` `except` `asy_fram_manager.py:353-356`, errno 47) | the other copy (`_read()` `:136-157`) | A.U16.06 (fault vs content), G5/R27 | disposition: R1 is the dual copy by owner decision ("So no retry is added … the dual-copy layer already covers the read path", owner, 2026-09-24, SPECIFICATION.md:3755); R3/R4 have nothing to clear (U13 table: the port clears the overrun flag itself) |
| one copy invalid or blank (`_read()` `:136-172`) | R2-level repair: the valid copy rewrites the other (`:149-157`, `:165-172`) | A.U16.06, A.U16.09 | DONE-AT-HEAD; a failed repair write fails the read (legacy field-proven reason, G5/R25) |
| both copies valid but different (`:173-177`, errno 73; 51 after A.U2.01) | hard failure; the next write heals it | A.U16.08 (owner tag restored) | disposition: owner rule "a hard failure, not a guess" (owner, 2026-07-18, OR87.a (d)) — no rung may pick a copy |
| write verification mismatch (`:114-123`, errno 63/64; 50 after A.U2.01) | the write reports `False`; the next write rewrites both copies | — | disposition: R1 is the caller's next write (loggers on the next entry, SGP40 on the next backup); an immediate rewrite would double wear on a chip whose readback already disagrees, and a persistent disagreement reaches A.U16.R03 through the latch/identity probe only if the chip is gone — a chip that answers its ID but stores wrong data is the torn-write/corruption case the dual copy and CRC report (G5/R25) |
| torn write by a reset (busy markers left, `_write_chunk()` `:270-291`) | the next boot reads the block invalid and re-initialises | A.U16.06 | disposition: owner-accepted all-or-nothing loss (owner, 2026-09-13, G5/R25) |
| storage paused (`_mempause()` `:98-100, :130-132, :391-393`) or chip write-protected (`_W_PROTECTED` `:223-227`) | refusal, w25 / w28 | A.U16.19 | disposition: commanded states, not faults — no rung may override an operator's pause or protection |
| write-protection readback mismatch (`_set_write_protected()` `:243-248`, errno 95; 45 after A.U2.01) | returns `False` | A.U16.15 (partial protection) | disposition: an explicit command with no product caller (grep `set_write_protected(` in `src/`, `buildgen/`: definition only); the caller's retry |
| `verify_present()` lock wait times out (`:407-411`) | returns `False`, errno 97 (19 after A.U2.01) | A.U10.26 | disposition: no product caller; A.U16.R03 probes from inside the hold instead |
| SPI bus clear / controller re-init | — | — | disposition: U13 table (CS deasserts in `finally` on every cycle; the controller is re-configured every session) |

### U17 — UART (check and cross-reference only)

V.U17.20 did this pass and A.U17.33 carries it into SPEC J.5; checked against OR113.a here, nothing redone.

| fault path | rungs (evidence per V.U17.20) | check against OR113.a |
|---|---|---|
| a frame fails (CRC, timeout, wrong kind) — `asy_uart_comm.py` `_read_frame()` `:498-505` | R1 the caller's next exchange (J.5, J.9; the exerciser retries each period, `asy_uart_link_driver.py:114-120`); line-level "clear": `_fault()` → `_resync()` drain-until-quiet ×4 bounded, then hold-off (`:536-596`); `clear()` from outside (`:612-625`); boot drain in `setup()` (`:1093-1102`) | consistent: bounded (×4 drain, hold-off window), logged once per episode (A.U3.08, the central rule), race-free (drain inside `async with self.uart`), L1 `tests/test_uart_comm_hazard.py`, L2 `tests/test_digital_twin_uart_link.py:219`, L3 `uart_crossover_recovery.py`; L4 `tests_hardware/bench/test_uart_link_under_api_load.py` runs the link under full API load (no fault injected there — A.U17.25's tier map lists the L3/L4 fault-injection gaps for U26) |
| controller re-init | not a rung | A.U17.33 dispositions it from source (rp2 latches no receive error, `ports/rp2/machine_uart.c:162-190`), lead-resolved (AC_NOTES 16) — consistent with the ladder's "escalate only when the milder step does not work": no fault class exists for this step to fix |
| construction refused / task ends | R5 (responder at HEAD, initiator A.U17.07), R6, R7 | consistent |
| participant (the peer MCU) | not reachable from this side | disposition as in A.U17.33: the protocol is initiator/responder with no reset command (CLAUDE.md UART rule; no negotiation, owner 2026-09-11) |

No conflict with A.U17.33 or any other U17 action; A.U14.R01's F.2 text points to J.5 for the UART ladder.

### U18 — NET: WiFi, NTP, DNS, captive DNS, UDP sockets

The network side has no shared bus to clear; its "participant" is the CYW43 radio (local) or a remote server (not
recoverable from here). OR18/OR18.a split the cases: an abnormal but harmless situation (an unreachable server, an absent
AP) is handled inside the module and must not escalate; a failing chip may escalate to a reboot.

| fault path | rungs at HEAD (evidence) | rungs by existing actions | missing → action / disposition |
|---|---|---|---|
| a WLAN hardware call raises (`hw_op_failed` set at `src/asy_wifi_service.py:292, 347, 350, 374, 455, 500, 598`; errno 11-16/18) | R1 the next `wifi_refresh_sec` iteration; streak `_error_check()` `:836-841` → give-up errno 17 → R5 (task restart: `_reset_wlan_connect_state()` `:295-316` disconnects, never re-initialises the radio) → R6 → R7 | A.U18.32 (retry wait unlocked), A.U18.34 (lock table), A.U3.03 | **R2 missing** — the CYW43's own reset (power it off and reload its firmware) exists in the code only as the STA↔AP mode switch (`_switch_wlan_mode()` `:278-293`) → **A.U18.R01** through A.U10.R01's hook |
| STA connect fails (`STAT_WRONG_PASSWORD`/`NO_AP_FOUND`/`CONNECT_FAIL`, `:604-619`) or a link is lost | R1 retry every refresh / 60 s after an established link (`:469-477`); after `conn_fail_to_hotspot` failures the hotspot (`:479-489`); after a second streak the permanent deactivation (`:491-501`) | A.U18.28-A.U18.30 (hotspot repeat, restart, deactivated LED), A.U18.36 | disposition: an absent AP or a wrong password is an environment/configuration condition handled inside the module (OR18, OR18.a); the terminal deactivation is owner-confirmed behaviour — "permanent WiFi deactivation after a second STA failure streak … only a physical power-cycle clears it" (SPEC A.4 owner-confirmed list, `SPECIFICATION.md:269-274`; LED pattern owner, 2026-09-29, OR97.a (19)) — so no rung past it |
| CYW43 `isconnected()` false positive (link gone, reported up) | none by design; power cycle | — | disposition: owner rule — "a power cycle/`hard_reset()` is a deliberately stable, intended recovery feature … don't propose an independent reachability-probe mechanism" (CLAUDE.md hard rules; SPEC F.2 `:3625-3636`); without a detection signal no rung can fire |
| hotspot timer cannot be armed (`:419-422`) | R1 the next refresh re-arms | A.U18.24 (persists) | DONE-AT-HEAD with A.U18.24 |
| NTP: name does not resolve, no reply, reply rejected, request not sent (`asy_ntp_client.py:167-191, 213-241, 243-268`) | R1: resolver tries every server (DHCP then fallback, `asy_dns_client.py:110-118`); synced device 3 retries × 15 s (`:272-293`); unsynced device retries forever with backoff (`:434-444`, C.7.2 "never gives up"); each fetch builds a fresh socket (`:175-191`) | A.U18.10 (fallback servers as config), A.U18.14 (send failure logged), A.U18.15 (disconnect in `finally`), A.U18.20-A.U18.23 | disposition for R2-R6: a remote server is not a local participant, and OR18's own example is this case ("NTP … just stalling its task if the server was unreachable instead of handling it internally … should be fixed", owner, 2026-09-25) — the module handles it inside, never ends its task on it |
| NTP retry/refresh timer cannot be armed (`:281-290`, `:332-350`) | cancels this retry cycle; the regular check recovers | A.U18.22, A.U18.23 (re-arm from its task) | DONE with A.U18.23 |
| a UDP socket cannot be set up, bound or connected (`asy_udp_socket.py:73-102`) | R1+R2 in one: the socket is torn down (`_disconnect_locked()` `:104-124`) and a fresh one is built on the next call — a lazy re-create per call | A.U18.13 (one attempt per call; the next call retries), A.U18.05 (idle poll rate) | DONE-AT-HEAD: bounded by the callers' own cadence (captive DNS backoff `captive_dns.py:122-127`, NTP/DNS per attempt), no log inside the class (it owns none; callers log, A.U18.15) |
| a send/receive on a live UDP socket fails (`sendto()`/`write()`/`recvfrom()` `:152-180` return `None`) | R1 the caller's next call; the socket is kept | A.U18.14, A.U18.17 (POLLERR verdict) | disposition for a re-create rung: on rp2 a bound UDP socket's state changes only at creation and on close or a failed use of an unconnected pcb (`extmod/modlwip.c:1008, 1276-1282, 1710`), so a failure on a live socket is a transient (e.g. `MemoryError` for the receive buffer) that the next call retries; A.U18.17 records that its `POLLERR` arm never fires on rp2 |
| captive DNS loop error (`captive_dns.py:84-137`) | per-packet drop; `None` data → warning and backoff up to its max (`:122-127`); any other exception → errno 2, 3 s, continue (`:133-136`); ends only on cancel or an invalid `ifconfig()` pair (`:88-92`) | A.U18.02-A.U18.07 | DONE-AT-HEAD: the task never dies of a fault; its socket re-creates lazily (above); an invalid AP address is a configuration fault (OR18 exclusion) |
| TCP send stall on a full lwIP arena (10 s `ERR_MEM` retry, `extmod/modlwip.c:800-812`) | none | A.U14.30 (lwIP sizing), U19's `TCP_NODELAY` action (OR112.a) | referenced, not repeated: OR112.a closes it by sizing; phase C tests it |

## Actions

**U10**

### A.U10.R01 One escalation ladder in `SensorReader._error_check()`
- **Why**: G4/R22 — "Work (OR113.a (2), all bus units …): the ladder per bus and participant — … U10 (escalation
  contract)"; OR113.a (2) "retry the transaction; recover the one participant (its own reset command or
  re-configuration); clear the bus …; re-initialise the bus controller; restart the task; reboot" (owner, 2026-09-30);
  harmonization 38.
- **Site**: `src/base_classes.py` module constants (after the imports, `:9-28`); `SensorReader.__init__` `:151-176`;
  `_error_check()` `:218-230`; `reset_error_counter()` `:243-248`; the TYPE_CHECKING block `:19-28`.
- **Change**: (1) Constants `_RECOVER_DEVICE_AT = const(2)` and `_RECOVER_BUS_AT = const(3)` with tag lines
  `# @tunable module.recover_device_at = 2` / `# @tunable module.recover_bus_at = 3`, and `_RUNG_DEVICE = const(1)`,
  `_RUNG_BUS = const(2)`; one comment line: "# Recovery ladder: participant at the 2nd failed cycle, bus at the 3rd,
  task end past max_module_error (owner, 2026-09-30: smallest blast radius first)." (2) `__init__` gains
  `self._rungs = 0` (a two-bit mask, never grows) and `self._recovery_bus: "I2C | None" = None`, the bus a driver
  whose chip sits on I2C sets after construction (TYPE_CHECKING import `from asy_i2c_driver import I2C`; no runtime
  import, so `base_classes.py` keeps no bus dependency). (3) Overridable hook `async def _recover_device(self) -> bool |
  None: return None` — `None` means "this reader has no participant rung" and logs nothing; an override returns
  `True`/`False` for done/failed and never raises. (4) `_error_check()`: the give-up test `:224-226` stays first; when
  the streak is at or below `max_module_error`, `await self._climb_ladder()`; in the decrement branch `:227-229`, when
  `_err_cnt_internal` reaches 0, `self._rungs = 0` (the episode ends). New private `_climb_ladder()`: `n =
  self._err_cnt_internal`; if `n >= _RECOVER_DEVICE_AT and not self._rungs & _RUNG_DEVICE`: set the bit, then `ok =
  await self._recover_device()`, and when `ok is not None` one `await self.pr.wrn_s("Device recovery after", n,
  "failed cycles:", "done" if ok else "failed", wrnno=_WRN_DEVICE_RECOVERY)`; return (one rung per failed cycle). Else
  if `n >= _RECOVER_BUS_AT`: `await self._recover_bus()`. New private `_recover_bus()`: returns at once when
  `self._recovery_bus is None` or the `_RUNG_BUS` bit is set; else sets the bit, `status = await
  self._recovery_bus.recover()` (A.U13.R01) and logs one `await self.pr.wrn_s("I2C bus cleared and controller
  re-initialised, status", status, wrnno=_WRN_BUS_RECOVERY)`. The bit is set before the first await, so a second
  caller in the same task cannot re-enter. (5) `async def _init_failed(self) -> None: await self._recover_bus()` — the
  drivers' `_init_*()` failure branches call it before `return False` (A.U15.R01-R04), so a bus held across a task
  restart is cleared before the restart budget reaches the reboot; a successful `_init_*()` calls the new
  `async def _init_done(self) -> None`, which ends the episode (`self._rungs = 0`) and, when `_recovery_bus` is set,
  reports the boot clear once: `status = self._recovery_bus.take_boot_clear_status()` (A.U13.R01: returns the stored
  construction-time status and zeroes it, so only the first reader on that bus logs it) and, when non-zero, one
  `await self.pr.wrn_s("I2C bus was held at boot and cleared, status", status, wrnno=_WRN_BUS_RECOVERY)` — the boot
  rung of OR113.a (1) then leaves a persisted, attributable entry although the bus wrapper owns no logger. `_rungs` is
  deliberately not cleared at a task (re)start: a rung that already fired in this episode is not repeated per restart —
  the next rung (R5, then R6) takes over. (6) `reset_error_counter()`
  also sets `self._rungs = 0`. Resulting order per reader: R1 each failed cycle is retried by the next trigger; R2 at the
  2nd consecutive failure; R3+R4 at the 3rd; R5 past `max_module_error` (5, `buildgen/codegen.py:18`); R6 by the
  supervisor budget; R7. A reader whose `max_module_error` is below a threshold simply skips that rung (the give-up
  test runs first). Bounded: each rung at most once per episode, an episode ending only at a streak of 0 or a
  successful init; restarts are bounded by the supervisor budget. Logged once per event: one persisted warning per rung
  fired; the failing cycles themselves keep the driver's own entry (A.U3.03). Race-free: `_error_check()` runs in the
  reader's own task after its read's `async with` blocks have exited, so it holds no device session or bus lock; each
  hook takes the locks like any transaction (no nested acquisition, `asyncio.Lock` is not re-entrant); `_rungs` is
  tested and set with no await between.
- **Blast**: callers every `_error_check()` caller (SCD30 `:407`, SGP40 `:530`, BMP3XX `:392`, ISL29125 `:1048`,
  WIFI `:836`) — signature unchanged; the hooks are added by A.U15.R01-R04 and A.U18.R01 · generated — (the generated
  modules call no `_error_check`; `_MAX_MODULE_ERROR = 5` `buildgen/codegen.py:18` unchanged) · js — (mock data rows for
  the two new wrnno are A.U2.21's generator) · tests existing: `tests/test_base_classes.py:472-510` (streak tests on a
  plain `SensorReader`, `max_module_error` 0 or 3: base hook returns `None`, no recovery bus → unchanged);
  driver tests that drive a streak to ≥ 2 with a hooked driver re-derive their scripted transactions and error counts
  at execution: `tests/test_asy_bmp3xx_driver.py:1400-1411, 1977-1988`, `tests/test_asy_isl29125_driver.py:953, 2539`,
  `tests/test_asy_scd30_driver.py:1286-1331`, `tests/test_asy_sgp40_driver.py:369-443, 505-510, 585-589`,
  `tests/test_asy_wifi_service.py` streak tests (grep `max_module_error=`), `tests/test_notification_scd30_integration.py`,
  `tests/test_notification_scd30_sgp40_integration.py` (`ErrCount` values after a streak); new L1
  `tests/test_base_classes.py` — a `SensorReader` subclass with a counting `_recover_device()` and a stub bus whose
  `recover()` counts: failures 1…6 fire nothing / device once / bus once / nothing / nothing / give-up (errno 2); one
  success after the 3rd failure then more failures fire nothing new until the streak returned to 0; `max_module_error=1`
  fires no rung; `reset_error_counter()` re-arms both rungs; `_init_failed()` runs the bus rung once per episode; `_init_done()`
  re-arms both rungs and logs a stub bus's non-zero boot-clear status once, a second reader on the same stub bus
  logging nothing; a hook
  returning `None` logs nothing; each firing adds exactly one persisted entry; a hook that raises is a test failure
  (the contract says it must not) — L2-L4 through the driver actions · twin — · docs SPEC C.7 `_error_check()`
  paragraph (`:1885-1890`) gains: "Between the retry and the give-up it climbs the recovery ladder once per episode: at
  the second consecutive failure the driver's own participant recovery (`_recover_device()`), at the third the bus's
  (`I2C.recover()`: clear, then re-initialise the controller); each fired rung logs one warning, and an episode ends when
  the streak is back to 0 or setup succeeds (owner, 2026-09-30: smallest blast radius first; F.2)." SPEC C.4.1 skeleton
  (`:1639-1660`) unchanged (no new call site); SPEC F.2 (A.U14.R01); Part N rows `module.recover_device_at`,
  `module.recover_bus_at` with the relation `module.recover_device_at < module.recover_bus_at <= module.max_error`
  (A.U8.02's relation checks) · toml — · uart —.
- **Depends**: A.U3.03 (`:223`, same function), A.U2.01 (the two wrnno, and `_ERR_*`/`_WRN_*` names, A.U2.04), A.U5.02
  (constructor shape), A.U8.01/A.U8.02 (tag grammar, relation rows), A.U10.18 (lock names in the hooks), A.U10.33 (D.15
  member order for the new methods), A.U13.R01 (`I2C.recover()`); co-lands with A.U15.R01-R04, A.U18.R01 — A-C merges.
- **Kind**: code | test | doc

**U13**

### A.U13.R01 `I2C.recover()`: clear the bus, then rebuild its controller
- **Why**: G4/R22 — "code+test in U13 (bus layer rungs)"; OR113.a (2) "clear the bus (release a held line: SCL clock-out
  and STOP, under the bus lock so no other device session is interleaved); re-initialise the bus controller … A full
  bus reset is allowed mid-operation when the milder measures fail" (owner, 2026-09-30); OR113.a (1) boot clear
  (A.U14.17 option (a)); G4/R19 (no code depends on bus identity; `deinit()` releases nothing on rp2).
- **Site**: `src/asy_i2c_driver.py` — module constants (`:17-19`), `I2C.__init__` `:23-37`, `init()` `:163-178`, new
  `recover()` after `init()`/`deinit()`; the module function `_clear_bus()` A.U14.17 (a) adds beside `I2C`; header
  `:4-6`.
- **Change**: (1) `init()` stores its arguments: `self._args = (port_id, scl_pin, sda_pin, frequency, timeout)` (a
  fixed 5-tuple, replaced not grown) before constructing; A.U14.17 (a)'s boot `_clear_bus()` call in `__init__` stores
  its result in `self._boot_clear_status` (0 when SDA read high). (2) `_clear_bus(scl_pin, sda_pin) -> int` (A.U14.17's
  function, one shared implementation) returns a status mask instead of nothing: `_REC_SDA_LOW = const(1)` SDA read low
  and pulses were sent, `_REC_SDA_STUCK = const(2)` SDA still low after the ninth pulse; it builds its pins with
  `pull=Pin.PULL_UP` (a `Pin()` given no `pull` removes the pull-ups, `ports/rp2/machine_pin.c:299-306`) — SCL and SDA both
  `Pin.OPEN_DRAIN` `value=1` (rp2 emulates open drain by direction: 1 releases the line and reads it, 0 drives it low,
  `ports/rp2/mphalport.h:158-168`), so SDA can be read while released and driven low for the STOP — clocks at most 9 times (`time.sleep_us(_CLEAR_HALF_PERIOD_US)` per half
  period, `_CLEAR_HALF_PERIOD_US = const(5)` tagged `# @tunable i2c.clear_half_period_us = 5`, 100 kHz, the SCD30's
  ceiling, SCD30 Interface Description p.2) and ends with a STOP (SDA low while SCL high, then released); `_CLEAR_PULSES
  = const(9)` is the I2C byte-plus-acknowledge count, a protocol constant, untagged. (3) New `def
  take_boot_clear_status(self) -> int`: returns `self._boot_clear_status` and sets it to 0 (read once by A.U10.R01's
  `_init_done()`). (4) New `async def recover(self) -> int`, the one runtime entry, whole body under `async with
  self.async_lock:` (A.U10.18's `bus_lock`), so no device session's transfer can run between the clear and the
  rebuilt controller: (a) SCL wait — read SCL through `Pin(scl, Pin.IN, pull=Pin.PULL_UP)`; while it reads low, `await
  asyncio.sleep_ms(1)`, up to the bus timeout (`self._args[4]`, or rp2's 50,000 µs default when `None`,
  `machine_i2c.c:38`); still low → status `_REC_SCL_HELD = const(4)` and no pulses; (b) otherwise `status =
  _clear_bus(scl, sda)`; (c) controller re-init: `self.init(*self._args)` inside `try:`, `except (OSError, ValueError)`
  → `status |= _REC_NO_CONTROLLER = const(8)` with `_i2c` left `None` (the unavailable-bus path, A.U13.07/A.U13.09);
  return `status`. On rp2 "re-initialise the controller" can only be a re-construction with arguments:
  `machine.I2C.init()` raises `OSError("I2C operation not supported")` because the port's protocol has no `init` slot
  (`extmod/machine_i2c.c:320-326`, `ports/rp2/machine_i2c.c:161-164`), `deinit()` is a no-op (F.5.1), and a
  construction with arguments re-runs `i2c_init()`, `i2c_set_baudrate()`, `gpio_set_function(…, GPIO_FUNC_I2C)` and the
  pull-ups on the same static per-id object (`machine_i2c.c:50-53, 87, 106-114`) — which is also what hands the pins
  back from the GPIO clock-out, exactly as the port's own zero-length probe hands them back after bit-banging the same
  pins (`machine_i2c.c:140-144`). What `i2c_init()` does inside the block (pico-sdk) is not in the scratch tree and is
  read at execution from the pinned submodule; the bench row of A.U13.R02 measures the effect. `init()` passes the full
  stored set (A.U14.04's rule: an omitted `timeout` would fall back to 50,000 µs for every user of the id). (5) Header
  `:4-6` gains one line: "# recover() is the bus rung of the recovery ladder: clear a held SDA, then rebuild the
  controller, under the bus lock (SPECIFICATION.md F.2)." Race-free: the clear and the re-construction run under the
  bus lock every transfer holds (`I2CDevice` sessions share `self.async_lock`, `:256-258`); a device session split
  across two bus sessions (SCD30 write → 50 ms → read, `asy_scd30_driver.py:477-487`; SGP40 `asy_sgp40_driver.py:572-576`;
  BMP3XX trigger → poll → read `:429-447`) can see the clear between its halves: the idle slave sees SCL pulses with no
  START and a STOP, which returns an I2C slave interface to idle without touching its registers (ISL29125 FN8424: "If a
  stop is issued in the middle of a Data byte … the serial communication of ISL29125 resets itself without performing the
  read/write. The contents of the register array are not affected", `dstxt/isl29125…:452-456`); the SCD30/SGP40/BMP3XX
  datasheets state no more than the I2C protocol, so A.U13.R02 proves "no sibling corruption" at every tier, as the
  general-call hazard test does. Bounded: at most nine pulses (≈ 100 µs) and one construction; the SCL wait at most the
  bus timeout, yielding every ms; no allocation beyond the `Pin` objects of one call.
- **Blast**: callers `SensorReader._recover_bus()` (A.U10.R01) is the only runtime caller; `take_boot_clear_status()`
  from `_init_done()` (A.U10.R01); construction sites unchanged in signature — the generated `build_system()` per
  `[bus.i2c*]` (`buildgen/codegen.py:387`) and every device script constructing `asy_i2c_driver.I2C` (grep at
  execution, as A.U14.17 (a)) · generated — (no codegen change) · js — · tests existing:
  `tests/test_asy_i2c_driver.py` construction tests hold (the fake records the same construction kwargs); tests that
  count `machine.I2C` constructions or read `i2c._i2c` identity after a recovery (grep `._i2c` in `tests/`) re-derive,
  since a recovery assigns the re-constructed object; new L1 `tests/test_asy_i2c_driver.py` — SDA high: no SCL edge,
  status 0, one re-construction with the stored `freq` and `timeout`; SDA released after k pulses: k pulses, STOP,
  status 1; SDA held: 9 pulses, STOP, status 3; SCL held beyond the timeout (fake clock): no pulse, status 4, the
  re-construction still happens; construction raising: status 8 and `_i2c is None`; a session holding the bus lock
  delays `recover()` until it exits and a session started during `recover()` waits for it; `take_boot_clear_status()`
  returns the boot value once, then 0. Fakes (U24/U25 execute): `tests/machine.py` `Pin` gains `OPEN_DRAIN`, a
  scripted input level per pin and a recorded value log (already required by A.U14.17 (a)); `tests/machine.py` `I2C`
  and `digital_twin/machine.py` `I2C` keep per-id state across constructions — attached devices, injected faults,
  `busy`, the log — as rp2's static per-id object keeps its slaves (`machine_i2c.c:50-53, 87`); today the twin's
  constructor re-wires fresh chip instances (`digital_twin/machine.py:238-247` → `_wire_i2c_devices()` `:234-235`),
  which a mid-run re-construction would silently replace (SCD30 NVM state, fault injectors of
  `digital_twin/run_generic_integration.py:225-248`) · twin as above · docs SPEC C.3 bus text states `recover()` and
  its status bits; SPEC F.5.1 (A.U14.04's bullet) gains "re-construction is also the only controller re-init rp2 offers:
  `machine.I2C.init()` raises `OSError` (`extmod/machine_i2c.c:320-326`)"; SPEC F.2 (A.U14.R01); SPEC G.2 I2C entry
  (A.U13.01) names `recover()`; Part N row `i2c.clear_half_period_us` · toml — · uart —.
- **Depends**: A.U14.17 (a) (the shared `_clear_bus()`; Conflicts 1), A.U14.04 (full parameter set), A.U13.07
  (bool/None contract of an unavailable bus), A.U13.16 (`deinit()`), A.U10.18 (`bus_lock` name), A.U10.R01 (the caller),
  A.U8.01 (tag grammar); fakes U24/U25.
- **Kind**: code | test | doc

### A.U13.R02 Bus-hazard coverage for the bus rung at every tier
- **Why**: CLAUDE.md standing rule — "A new bus-facing (I2C/SPI) device gets bus-hazard test coverage across all four
  test tiers that apply to it — never forget this" (owner direction, CLAUDE.md hard rules); OR113.a (2) "each rung …
  race-free … and tested at every level that can reach it" (owner, 2026-09-30); G4/R22 "hardware in C".
- **Site**: `tests/_bus_hazard_catalog.py` (new scenario beside `scenario_general_call_does_not_disturb_concurrent_siblings`
  `:505-524`); `tests/test_bus_hazard_multi_device.py`; `tests/test_digital_twin_bus_hazard_concurrency.py`;
  `tests_hardware/device_scripts/bus_topology_autodetect_and_hazard_sweep.py`; new
  `tests_hardware/device_scripts/i2c_held_sda_recovery.py`; `tests_hardware/flash/test_bus_concurrency.py`;
  `tests_hardware/bench/test_bus_concurrency_under_api_load.py` (read-only).
- **Change**: (1) Catalog: `scenario_bus_recovery_does_not_disturb_concurrent_siblings(build_fresh_bus_and_occupants,
  iterations=6, offsets=None)` — for each timing offset, every occupant's read loop runs while one extra task calls
  `i2c.recover()` after `offset` yields; asserts every sibling read is valid (the adapters' `read_once` checks), that
  the fake bus log shows no transfer between the clear's first pin event and the re-construction, and that the recovery
  really ran (a `recover` marker in the log). (2) L1 `tests/test_bus_hazard_multi_device.py` runs it for every generated
  bus topology (the file's existing per-bus parametrisation), plus one split-session case per driver that has one
  (SCD30 command → read, SGP40 command → read, BMP3XX trigger → read): the recovery lands between the halves and the
  driver's transaction still returns a valid value. (3) L2 `tests/test_digital_twin_bus_hazard_concurrency.py` runs the
  scenario on the twin chips and adds a ladder case: `fault.inject_fault("readfrom_mem", OSError(EIO), times=3)` on one
  chip drives its reader's streak to the bus rung (A.U10.R01), siblings keep reading valid data, the chips keep their
  state across the re-construction (the per-id twin bus of A.U13.R01's blast), and exactly one wrnno 15 is persisted.
  (4) L3: the sweep script gains a step that interleaves `recover()` with every discovered device's reads on a healthy
  bus (status 0, reads unaffected); the new script `i2c_held_sda_recovery.py` makes the fault on silicon without extra
  hardware: with the wrapper's bus lock held it bit-bangs START, a discovered device's read address, the ACK clock,
  and stops SCL low right after the ACK of a register whose first data bit is 0 (e.g. a chip-ID register read back as a
  byte below 0x80 — the script picks one from the discovered set and records it), so the slave keeps SDA low; asserts a
  transfer then fails (`ETIMEDOUT` or `EIO`), `recover()` returns status 1 without 2, every device on the bus answers
  its identification and one valid read each afterwards; records the recovery's duration; run from
  `tests_hardware/flash/test_bus_concurrency.py` beside the sweep. (5) L4: not reachable — making a held line needs raw
  REPL access, which stops `main.py` (SPEC, G4/R59), so the full-stack tier cannot inject it; the existing
  `test_bus_concurrency_under_api_load.py` runs unchanged and must pass (no behaviour change on a healthy bus). The L3
  script is the silicon proof, and a BACKLOG hardware row carries the pico-sdk `i2c_init()` observation (scope: SCL/SDA
  during re-construction).
- **Blast**: callers — · generated — · js — · tests as above; the flash wrapper gains one `run_isolated(…
  "i2c_held_sda_recovery.py" …)` call (no `flash_cycle`/`persistence_write` marker: no flash or NVM write) · twin
  `digital_twin/machine.py` per-id bus (A.U13.R01) · docs `tests_hardware/README.md` lists the new script and the
  held-SDA technique; SPEC C.8's bus-hazard standing rule names the recovery scenario · toml — · uart —.
- **Depends**: A.U13.R01, A.U10.R01; fakes U24/U25; U26 (hardware scripts) executes (4).
- **Kind**: test | hardware

**U15**

### A.U15.R01 SCD30: soft reset as the participant rung
- **Why**: G4/R22 — "code+test in … U15 … (participant rungs)"; OR113.a (2) "recover the one participant (its own reset
  command or re-configuration)" (owner, 2026-09-30); Interface Description 1.4.10 "forces the sensor into the same state
  as after powering up … The sensor is able to receive the command at any time, regardless of its internal state"
  (`dstxt/scd30__Sensirion_CO2_Sensors_SCD30_Interface_Description.txt:1512-1520`).
- **Site**: `src/asy_scd30_driver.py` `SCD30_Reader.__init__` `:118-145` (after `self.scd = SCD30_I2C(i2c)` `:139`);
  `_init_scd()` `:161-172`; new `_recover_device()` override in `SCD30_Reader`.
- **Change**: (1) `__init__`: `self._recovery_bus = i2c`. (2) `async def _recover_device(self) -> bool`: `try: await
  self.scd.reset()` (the existing 0xD304 command and its 2.5 s boot wait, `:585-589`) `except Exception as e:
  self.pr.err("Soft reset failed:", e); return False` `else: return True`. No re-configuration follows: the interval,
  ASC, temperature offset, altitude and continuous measurement are kept in the chip's non-volatile memory and restored by
  the reset (Interface Description `:257, :421, :846-847, :1126-1127, :1275`), so the rung writes no NVM (outside the
  `persistence_write` gate by construction). (3) `_init_scd()`: before `return False` in the setup-failure branch
  (`:168-170`) `await self._init_failed()`; before `self.pr.one("initialized")` (`:171`) `await self._init_done()`.
  Race-free: the reset's write holds the device session and the bus lock (`_send_command()` `:455-457`) and the 2.5 s
  restart runs outside both; a REST read landing inside that window fails like one during a task restart today (errno
  12, reported to that request) — a transient answer, not shared state; the reader's own next read waits for the next
  data-ready edge or the stuck-pin re-trigger.
- **Blast**: callers `_error_check()` (A.U10.R01) · generated — · js — · tests existing:
  `tests/test_asy_scd30_driver.py:1286-1331` (`…recovers_error_counter_after_a_good_read_following_failures`,
  `max_module_error=5`, two failures then a good read) now reaches the participant rung at the 2nd failure — it stubs
  `reader.scd.reset` (else a real 2.5 s sleep) and asserts one call and one wrnno 14; `:1214`, `:1256-1283`
  (`max_module_error=1`) unchanged (the give-up test runs first); setup tests unchanged;
  `tests/test_notification_scd30_integration.py:211-216, 262-264`, `tests/test_notification_scd30_sgp40_integration.py:282`
  (`ErrCount` after a streak) re-derive with A.U3.03; new L1 `tests/test_asy_scd30_driver.py` — two failing reads: one
  soft-reset command on the fake bus log, one persisted wrnno 14 "done"; a reset whose write raises: wrnno 14 "failed",
  no raise; a third failure: one `recover()` on the bus and one wrnno 15; a failed setup: one `recover()` before the task
  returns; a successful setup after a held boot bus: one wrnno 15 with the boot status · four tiers: the reset command is
  already in the address/command sweep (`tests/_bus_hazard_catalog.py:176-177` `instance.reset`) and in the
  cross-device write-vs-sibling scenarios (L1 `tests/test_bus_hazard_multi_device.py`, L2
  `tests/test_digital_twin_bus_hazard_concurrency.py`, L3 `bus_concurrency_scd30_write_vs_siblings.py`, L4
  `test_bus_concurrency_under_api_load.py`) — its new mid-operation timing adds a case to L1 and L2: the reset issued
  while SGP40/ISL29125/BMP3XX read loops run on the same bus leaves every sibling read valid; L3/L4 unchanged (same
  command, same locks); the bus rung's coverage is A.U13.R02 · twin `digital_twin/_scd30_chip.py:39, 175` already
  answers 0xD304 · docs SPEC A.4 SCD30 bullet (A.U15.06's rewrite) gains "a second consecutive failed read soft-resets
  the chip (no NVM write)"; SPEC F.2 (A.U14.R01) · toml — · uart —.
- **Depends**: A.U10.R01, A.U13.R01; co-lands with A.U15.40 (session class), A.U15.41 (`_init_scd()` / timer re-arm
  lines), A.U10.10 (`pr.setup()` leaves `_init_scd()`), A.U13.09 (`:470, :480, :484, :608`) — A-C merges.
- **Kind**: code | test | doc

### A.U15.R02 SGP40: heater-off to idle as the participant rung
- **Why**: G4/R22 (as A.U15.R01); OR113.a (2) "recover the one participant … the SGP40 general-call reset stays the one
  owner-accepted reset that reaches other devices" (owner, 2026-09-30); SGP40 datasheet Table 14 "sgp4x_turn_heater_off
  0x36 0x15 This command turns the hotplate off and stops the measurement. Subsequently, the sensor enters idle mode."
  (`dstxt/sgp40__Sensirion_Gas_Sensors_Datasheet_SGP40.txt:585-590`); the only reset the chip offers is the general call
  (Table 17, `:607-614`), which reaches every device on the bus.
- **Site**: `src/asy_sgp40_driver.py` `SGP40_Reader.__init__` (the `self.sgp = SGP40_I2C(i2c)` line); `_init_sgp()`
  `:330-361`; `SGP40_I2C` (new `turn_heater_off()` beside `_reset()` `:585-593`); new `_recover_device()` override.
- **Change**: (1) `SGP40_I2C.turn_heater_off()`: under `async with self.i2c_sgp40 as sgp40, sgp40.i2c_device as i2c:`
  write the constant `_CMD_HEATER_OFF = b"\x36\x15"` (module constant, no per-call buffer — a staged `_command_buffer`
  would reopen the OR109.a (0) shape), then `await asyncio.sleep(_HEATER_OFF_MAX_S)` outside the locks, with
  `_HEATER_OFF_MAX_S = const(0.001)` the command's maximum duration (Table 8 "sgp4x_turn_heater_off 0x36 0x15 – – 0.1 1",
  typ./max. ms, `dstxt/sgp40__…Datasheet_SGP40.txt:512`) — a datasheet fact, untagged. (2) `SGP40_Reader._recover_device()`: `try: await
  self.sgp.turn_heater_off()` `except Exception as e: self.pr.err("Heater-off failed:", e); return False` `else: return
  True`; the VOC algorithm state is untouched and the next `measure_raw()` re-enters measurement ("Calling the
  sgp40_measure_raw_signal command launches/continues the VOC measurement mode", §3.1, `…Datasheet_SGP40.txt:359-360`),
  so no restore is needed; the first sample after it comes from a hotplate that was briefly off — one sample of a
  recovered episode, accepted as such. (3) `self._recovery_bus = i2c`; `_init_sgp()`'s setup-failure branch `:338-340` gains `await
  self._init_failed()`, its two success returns (`:343-344`, `:360-361`) `await self._init_done()`. The general call stays
  where it is — once per setup, i.e. once per task (re)start (A.U15.15) — so this pass does not make it more frequent.
- **Blast**: callers `_error_check()` · generated — · js — · tests existing: `tests/test_asy_sgp40_driver.py:369-443`
  (streak tests at `max_module_error=2`), `:505-510`, `:585-589` see the heater-off write at the 2nd failure — re-derive
  their bus-log and `ErrCount` assertions; the address sweep `tests/_bus_hazard_catalog.py:216-226` gains
  `instance.turn_heater_off` in `_exercise_sgp40` (address 0x59 only — the sweep then proves the new command touches no
  other address); new L1 `tests/test_asy_sgp40_driver.py` — two failed cycles: exactly one `0x36 0x15` write to 0x59 and
  no write to 0x00 beyond setup's; wrnno 14 once; the VOC algorithm object unchanged; a raising write → "failed", no
  raise · four tiers (a new command on a shared bus): L1 `tests/test_bus_hazard_multi_device.py` — heater-off concurrent
  with the SCD30 read loop on dev's shared bus across offsets (same-device: heater-off vs the SGP40's own measure
  sequence, serialised by the device session); L2 `tests/test_digital_twin_bus_hazard_concurrency.py` — the same on the
  twin, `digital_twin/_sgp40_chip.py:59-76` gains an explicit 0x3615 branch (clears the pending reply, idle) instead of the
  catch-all ignore (U25); L3 `tests_hardware/device_scripts/bus_topology_autodetect_and_hazard_sweep.py` — the SGP40's
  command sweep adds 0x3615 and a sibling read after it; `bus_concurrency_cross_device_scd30_sgp40.py` gains a
  heater-off step; L4 `test_bus_concurrency_under_api_load.py` — unchanged (no REST path reaches the command), must pass ·
  twin as above · docs SPEC C.8 (A.U15.15's paragraph) gains "A failing SGP40 is first recovered by the device-addressed
  heater-off (Table 14), which reaches only the SGP40; the general call stays at setup"; SPEC A.4 SGP40 bullet · toml — ·
  uart —.
- **Depends**: A.U10.R01, A.U13.R01; co-lands with A.U15.13 (command buffer), A.U15.15 (same C.8 paragraph), A.U15.40
  (session class), OR109.a (0)'s `measure_raw()` fix — A-C merges.
- **Kind**: code | test | doc

### A.U15.R03 BMP3XX: soft reset plus the stored configuration
- **Why**: G4/R22 (as A.U15.R01); OR113.a (2) "its own reset command or re-configuration" (owner, 2026-09-30); BMP388
  DS001 "0xB6 softreset Triggers a reset, all user configuration settings are overwritten"
  (`dstxt/bmp3xx__bst-bmp388-ds001.txt:1717`, command list `:958`), so a reset alone would leave the chip on its
  default oversampling and filter.
- **Site**: `src/asy_bmp3xx_driver.py` `BMP3XX_Reader.__init__` (the `self.bmp = BMP3XX_I2C(i2c)` line); `_init_bmp()`
  `:198-225`; new `_apply_stored_config()` and `_recover_device()`.
- **Change**: (1) The config half of `_init_bmp()` (`:207-223`: read `_VAL_SI + _VAL_POV + _VAL_TOV + _VAL_FC`, apply
  trigger seconds, OSR, IIR) moves unchanged into `async def _apply_stored_config(self) -> bool` (logs its own errno 12/13
  as today and returns `False` on them); `_init_bmp()` calls it. (2) `_recover_device()`: `try: await self.bmp.reset()`
  (`:634-645`: waits `cmd_rdy`, writes 0xB6, settles 2 ms, checks `ERR_REG`) `except Exception as e:
  self.pr.err("Soft reset failed:", e); return False`; then `return await self._apply_stored_config()`. The sea-level value and
  the calibration coefficients are unaffected: the trimming coefficients "are stored into the devices' non-volatile
  memory (NVM) during production" (DS001 §3.11, `dstxt/bmp3xx__bst-bmp388-ds001.txt:1194`) and the driver's copy is
  re-read only by `setup()` (`:629`).
  (3) `self._recovery_bus = i2c`; every `return False` of `_init_bmp()` (the setup failure `:203-205` and the one after
  `_apply_stored_config()`) is preceded by `await self._init_failed()`, the success `:224` by `await self._init_done()`. Race-free: `reset()` and each setter hold the device session
  (`:640-645`, `:506-507`, `:620-621`); a PUT landing between the reset and the re-apply could otherwise see its chip
  write overwritten by the re-apply of the value stored before it, so `_recover_device()` holds the reader's per-module
  PUT lock (A.U11.27's `_set_lock`) from before the reset until the re-apply ends — a PUT then runs wholly before (its
  value is the stored one the re-apply writes) or wholly after (it writes the chip itself); no other lock is held on
  entry (`_error_check()` runs lock-free), so the order is `_set_lock` → device session → bus lock, the same as a PUT's.
- **Blast**: callers `_error_check()`, `_init_bmp()` · generated — · js — · tests existing:
  `tests/test_asy_bmp3xx_driver.py:1400-1411, 1977-1988` (`max_module_error=2`) see the reset and three config writes at
  the 2nd failure — re-derive; the reset tests `:351-364` unchanged; new L1 `tests/test_asy_bmp3xx_driver.py` — two
  failed reads: one 0xB6 to CMD, then OSR and IIR written with the stored values, wrnno 14 "done"; a rejected reset
  (`ERR_REG` cmd_err): "failed", no config writes; a PUT racing the recovery ends with the PUT's value in the chip · four
  tiers: reset and OSR/IIR writes are in the existing sweep and write-vs-sibling scenarios (`tests/_bus_hazard_catalog.py`
  `_exercise_bmp3xx` `:286-`, L3 `bmp3xx_same_device_rw_concurrency.py`); L1/L2 gain the mid-operation recovery
  concurrent with siblings (as A.U15.R01); L3/L4 unchanged, must pass · twin `digital_twin/_bmp3xx_chip.py:36` answers
  0xB6 · docs SPEC A.4 BMP3XX bullet · toml — · uart —.
- **Depends**: A.U10.R01, A.U13.R01, A.U11.27 (`_set_lock`); co-lands with A.U15.25, A.U15.26, A.U15.40, A.U10.21 (the
  `setup()` parameters) — A-C merges.
- **Kind**: code | test | doc

### A.U15.R04 ISL29125: the brownout re-apply as the participant rung
- **Why**: G4/R22 (as A.U15.R01); OR113.a (2) "its own reset command or re-configuration" (owner, 2026-09-30); the
  driver already re-applies its whole configuration after a brownout (`_recover_brownout()` `asy_isl29125_driver.py:465-
  479`); FN8424 "Write 46h to register 0x00 … the device will reset all registers to their default states"
  (`dstxt/isl29125__REN_isl29125_DST_20151201_1.txt:684`) — the heavier reset stays setup's (task restart), the
  re-configuration is the smaller step.
- **Site**: `src/asy_isl29125_driver.py` `ISL29125_Reader.__init__` `:198-270`; `_recover_brownout()` `:465-479`;
  `_init_isl()` `:292-348`; new `_reapply_configuration()` and `_recover_device()`.
- **Change**: (1) `_recover_brownout()`'s body after its warning (`:473-479`: `configure(force=True)`,
  `clear_brownout()`, `_switch_range(self._active_range)` under auto-range) becomes `async def
  _reapply_configuration(self) -> bool`, which keeps errno 33's message; `_recover_brownout()` = its warning + that
  call. (2) `_recover_device()` = `return await self._reapply_configuration()` (it never raises: `configure()`'s raise is
  caught there, `_switch_range()` logs its own). (3) `self._recovery_bus = i2c`; `_init_isl()` failure branches `:297-299,
  :316-317, :340-341` `await self._init_failed()` before `return False`, success `:346-347` `await self._init_done()`.
  Race-free: `configure()` mutates and writes the shadow inside the device session and rolls back inside it
  (`:1310-1383`); `_switch_range()`'s derivation race is A.U15.33's fix, which this path inherits.
- **Blast**: callers `_error_check()`, `_read_isl()` (brownout path unchanged in effect) · generated — · js — · tests
  existing: `tests/test_asy_isl29125_driver.py:953` (`max_module_error=3`), `:2539` (2) see the re-apply at the 2nd
  failure — re-derive; brownout tests keep their wrnno 30 (A.U3.14) and now call the shared body; new L1 — two failed
  status reads without brownout: CONFIG1-3 re-written from the shadow (one burst), thresholds re-armed under auto-range,
  wrnno 14 "done"; a raising burst: errno 33 and "failed" · four tiers: the burst and threshold writes are in the existing
  ISL29125 write-vs-sibling scenarios (L1/L2 catalog `_write_once_isl29125`, L3 `bus_concurrency_isl29125_write_vs_siblings.py`,
  `isl29125_same_device_rw_concurrency.py`, L4 the bench sweep); L1/L2 gain the mid-operation case (as A.U15.R01) ·
  twin — · docs SPEC M.1.2 (A.U15.34's restart-state table) gains "a second consecutive failed cycle re-applies the
  whole configuration, as a brownout does" · toml — · uart —.
- **Depends**: A.U10.R01, A.U13.R01, A.U3.14 (brownout logging), A.U15.32/A.U15.33/A.U15.34 (same functions) — A-C merges.
- **Kind**: code | test | doc

**U16**

### A.U16.R01 Retry a WREN whose latch did not set, once
- **Why**: G4/R22 — "code+test in … U16 … (participant rungs)"; OR113.a (2) "retry the transaction" first (owner,
  2026-09-30); the driver's own comment names the fault it guards: "catches a corrupted WREN transfer, which the chip
  would otherwise silently ignore the following WRITE/WRSR for" (`src/asy_fram_driver.py:201-203`), and its WRDI twin
  already retries once (`:207-215`).
- **Site**: `src/asy_fram_driver.py:200-205` `_enable_write()`; `:79-86` (`_W_*` status bits); `:327-350`
  `report_set_values()`; `:370-372` in `set_write_protected()`.
- **Change**: `_enable_write()` → WREN, RDSR; if WEL is clear, one more WREN, RDSR; return the second result — the
  comment gains "one retry, as _disable_write() retries WRDI" (one line, the block stays ≤ 3). A retry that succeeded is
  reported through a new status bit `_W_WEL_RETRIED = const(256)` (above A.U13.09's `_SV_BUS_DOWN = const(128)`), which
  `_write()`/`_set_write_protected()` OR into their status; `report_set_values()` and `set_write_protected()` print it
  with `self.pr.evt("FRAM write enable latch set on the second WREN")` (console: a recovered transient spends no slot);
  a second failure keeps today's w26 path. Bounded: two WREN at most per operation, each its own CS cycle (the CS rising
  edge ends any half-received command, MB85RS64V `dstxt/fram__MB85RS64V…:40-44`). Race-free: inside the synchronous
  body, under the bus lock the caller holds (`_send_command()` `:154-162`), no await added. No extra write cycle to the
  array: WREN/RDSR touch only the status register's volatile latch.
- **Blast**: callers `_write()` `:228`, `_set_write_protected()` `:236` · generated — · js — · tests existing:
  `tests/test_asy_fram_wire_trace.py` goldens hold (the healthy path sends one WREN); tests asserting w26 after a single
  dropped WREN (grep `wrnno=82`/`26` and the fake's WEL knobs in `tests/test_asy_fram_driver.py`,
  `tests/_fram_chip_fake.py:23-60`) now need two dropped WRENs; new L1 `tests/test_asy_fram_driver.py` — the fake drops
  the first WREN: the write lands, the trace shows WREN, RDSR, WREN, RDSR, WRITE…, one console line, no w26; drops both:
  w26 and nothing written · four tiers (same-device only, FRAM being alone on its bus): L1 above; L2
  `digital_twin/_fram_chip.py` gains a `wren` fault op in its `FaultInjector` (drop the next WREN, U25) and
  `tests/test_digital_twin_fram.py` a booted write surviving one dropped WREN; L3
  `tests_hardware/device_scripts/fram_cs_hijack_fault_injection_and_recovery.py` gains a case deasserting CS inside the
  first WREN of a write (its `_CsHijack` seam) — the write reads back intact; L4 not reachable (no FRAM fault injection
  under the full stack), existing bench runs unchanged · twin as above · docs SPEC C.3.1 FRAM bullet: "a WREN whose
  latch did not set is repeated once, like WRDI" · toml — · uart —.
- **Depends**: A.U13.09 (`_SV_BUS_DOWN` bit and entry check), A.U2.01 (w26); co-lands with A.U16.15 (same
  `_set_write_protected()`), A.U16.10 — A-C merges.
- **Kind**: code | test | doc

### A.U16.R02 `FRAM_SPI.setup()` retries identification before giving up
- **Why**: G4/R22 (as A.U16.R01); OR113.a (2) "retry … at boot and mid-operation" (owner, 2026-09-30); A.U16.17's
  escalation (owner "5. the same as all other chips", 2026-09-29, OR89.a (5)) otherwise turns a single disturbed RDID at
  boot into a reboot.
- **Site**: `src/asy_fram_driver.py:381-398` `setup()`; constants `:74-77`.
- **Change**: inside the existing bus-lock hold, `present = self._check_device_id()` → up to `_ID_ATTEMPTS = const(3)`
  (tagged `# @tunable fram.setup_id_attempts = 3`) back-to-back RDID cycles, stopping at the first match; each is its own
  CS cycle (CS high between them resets the chip's command state). When the match came on a retry, after the lock is
  released: `await self.pr.wrn_s("FRAM answered its identification only on attempt", n, wrnno=_WRN_FRAM_ID_RETRIED)`
  (FRAM wrnno 29, band 25-29, A.U2.01 merge; RAM-only log). No match after the last attempt: raise as today (A.U16.17
  then escalates). Placement keeps A.U16.17's rule: the retry is inside `setup()`, which runs first in the boot batch,
  before any logger reads its chunk — so no logger is left RAM-only by it.
- **Blast**: callers `AsyFramManager.setup()` `asy_fram_manager.py:733`, the generated boot batch, device scripts that
  call `FRAM_SPI.setup()` (grep `.setup()` in `tests_hardware/device_scripts/fram_*.py`) · generated — · js — · tests
  existing: `tests/test_asy_fram_driver.py` setup-failure tests (RDID mismatch) now see three RDID cycles in the fake's
  log before the raise — trace assertions re-derive; `tests/test_asy_fram_wire_trace.py` `_GOLDEN_BLANK_SETUP` holds
  (one RDID on success); `tests/_sensortask_scenarios.py:499-545` (A.U16.17's dead-chip scenario) sees three RDIDs;
  new L1: a fake answering garbage once, then the right ID → setup succeeds with one wrnno 29 · four tiers (FRAM alone
  on its bus): L2 `tests/test_digital_twin_generic_wiring.py:105-163`'s `rdid_response` override gains a one-shot bad
  answer case; L3 `fram_manager_roundtrip.py` runs unchanged (healthy chip); L4 unchanged · twin `digital_twin/_fram_chip.py`
  `rdid_response` one-shot knob (U25) · docs SPEC C.3.1 / A.4 FRAM bullet (A.U16.17's text gains "after up to three
  identification attempts"); Part N row · toml — · uart —.
- **Depends**: A.U16.10 (both locks in `setup()`), A.U16.15 (partial protection readback, same function), A.U10.21
  (`setup() -> bool`), A.U10.45 (raise message), A.U16.17.
- **Kind**: code | test | doc

### A.U16.R03 A chip lost mid-operation stops FRAM access and escalates
- **Why**: G4/R22 (as A.U16.R01); OR113.a (2) "every bus, every participant, boot and mid-operation … restart the task;
  reboot" (owner, 2026-09-30); OR89.a (5) "a FRAM chip declared in the device TOML but dead or absent is treated like
  every other declared chip" (owner, 2026-09-29); OR18.a "a reboot may recover a stalled chip" (owner, 2026-09-25). At
  HEAD a chip that goes silent after boot is never identified again: a silent SO reads back a constant status byte, so
  every write ends in "latch did not set" (0x00) or "latch did not clear" (0xFF — the payload is then reported as
  landed, `:348-350`), consumers fall back to RAM, and nothing escalates.
- **Site**: `src/asy_fram_driver.py` `FRAM_SPI.__init__` `:98-125`, `set_values_sync()` `:314-325`,
  `report_set_values()` `:327-350`, `setup()` `:381-398`; `src/asy_fram_manager.py` `AsyFramManager` `:618-740` (the task starter A.U16.17 adds).
- **Change**: (1) `FRAM_SPI.__init__` gains `self._anomalies = 0` (saturates at `_PROBE_AT`, never grows) and
  `self.lost = asyncio.Event()`. (2) `set_values_sync()` (`:314-325`, the synchronous body every chunk write goes
  through under the caller's block hold — `_set_check_sb()` `asy_fram_manager.py:244`, `_write_chunk()` `:280`,
  `_clear_chunk()` `:369`): after `self._write(...)`, a result carrying `_W_WEL_NOT_SET` or `_W_WEL_STUCK` does
  `self._anomalies = min(self._anomalies + 1, _PROBE_AT)`, any other completed write (`_W_OK`, or A.U16.R01's
  `_W_WEL_RETRIED`) sets it to 0 (the clean path never reaches
  `report_set_values()`, which runs only for a non-zero status, `asy_fram_manager.py:245-247`). On reaching `_PROBE_AT =
  const(2)` (tagged `# @tunable fram.chip_probe_at = 2`): one `self._check_device_id()` (synchronous RDID, one CS cycle,
  under the held bus lock, no await); a match → `self._anomalies = 0` (a latch or content problem, not a lost chip; the
  w26/w27 entries already describe it); no match → `self.initialized = False` (every later operation refuses at its
  entry guard with no bus traffic, errno 18 NOT_INIT per A.U2.01) and the result gains a new bit `_SV_CHIP_LOST =
  const(512)`. `report_set_values()` handles that bit first: `await self.pr.err_s("FRAM chip stopped answering its
  identification - access stopped", errno=_ERR_FRAM_CHIP_LOST)` (54), `self.lost.set()`, return `False`. (3) `setup()` on
  success clears `self.lost` and `self._anomalies`. (4) `AsyFramManager` (extending A.U16.17): `get_task_starters()`
  returns one starter whenever the manager exists, i.e. whenever the TOML declares a chip (no longer `[]` when
  initialised — Conflicts 5); the task `watch_chip()`: `if not self.fram.initialized:` — never up since boot → A.U16.17's
  behaviour unchanged (print, `return False`); was up and got lost → `await self.setup()` once (A.U16.R02's retries
  included), `False` → `return False`, `True` → `self.pr.one("FRAM chip answers again")` and continue; then `await
  self.fram.lost.wait()` and `return False`. A `_was_up` flag set by the first successful `setup()` tells the two apart.
  Result per reader of the ladder: R1 the next write / R2 the chip's command state reset by every CS rising edge / R3,R4
  not applicable on this bus (U13 table) / R5 the task ends and its restart re-runs `setup()` / R6 the supervisor budget
  reboots when it stays lost / R7. Bounded: one probe per `_PROBE_AT` anomalies, one `setup()` per task restart, the
  restarts by the supervisor budget. Logged once per event: one errno 54 per loss (the flag stops further probes), one
  supervisor entry per task end (A.U3.06). Race-free: the probe runs inside the block hold that already owns both
  FRAM locks; `setup()` in the task takes both locks (A.U16.10); `initialized` is read by every entry guard inside the
  same holds. Consumers: loggers set up while the chip was up keep their stores; their writes are refused while lost and
  the first write after recovery re-persists the whole ring from RAM (`PrintLogHistoryStore._write()` packs the full
  state, `src/print_log.py:244-256`), so nothing stale is left on the chip.
- **Blast**: callers the chunk layer (`_set_check_sb()`, `_write_chunk()`, `_clear_chunk()`), the generated task
  collectors (A.U16.17's `codegen.py:664` change: `fram` now always contributes one starter) · generated every FRAM
  device's task list gains the manager's task permanently (six devices; `tests/_sensortask_scenarios.py` task-count and
  task-name expectations, A.U10.19's inventory, re-derive) · js — · tests existing: `tests/_sensortask_scenarios.py:499-545`
  (A.U16.17's rewrite) holds for the boot case; boot-sequence tests counting supervised tasks per device (grep
  `len(_collect_task_starters` / task counts in `tests/test_sensortask_*.py`, `tests/test_digital_twin_*`) gain one;
  `tests_scripts/test_buildgen_generate.py` collector expectations; new L1 `tests/test_asy_fram_driver.py` — a fake chip
  switched silent (SO stuck 0x00; and 0xFF) mid-run: the second anomalous write probes once, `initialized` False, one
  errno 54, `lost` set, later operations make no bus traffic; an anomaly with a matching RDID resets the count and keeps
  the chip up; L1 `tests/test_asy_fram_manager.py` — the task waits while healthy, returns `False` on a loss, a restart
  with the chip back re-runs `setup()` and waits again, and the next logger write re-persists the RAM ring
  (`tests/test_print_log.py`'s store helpers); L2 `digital_twin/_fram_chip.py` gains a `silent` switch (U25) and
  `tests/test_digital_twin_fram.py` a booted device whose chip goes silent: the FRAM task ends, a restart recovers when
  the switch is cleared, and staying silent arms the reboot within the budget (the twin's `SimulatedResetError` path, as
  A.U16.17's scenario); L3 `fram_cs_hijack_fault_injection_and_recovery.py` gains "CS held inactive across two block
  writes" (a deselected chip is silent) → errno 54 and `initialized` False, then CS released → `setup()` succeeds and a
  write reads back; L4 not reachable (no chip-silencing under the full stack), bench runs unchanged; FRAM alone on its
  bus, so no cross-device case exists · twin as above · docs SPEC A.4 FRAM bullet (A.U16.17's text) gains "A chip that
  stops answering its identification after boot stops all FRAM access, ends the manager's task and is set up again by
  its restart; a chip that stays lost reboots the device through the supervisor"; SPEC A.7 task list; SPEC C.7.1 row for
  errno 54 (A.U2.22 generates); Part N rows · toml — · uart —.
- **Depends**: A.U16.17 (the task and collector change — extended, Conflicts 5), A.U16.10, A.U16.R01, A.U16.R02,
  A.U13.09, A.U2.01 (errno 54), A.U3.06, A.U10.19 (task inventory); co-lands with U20's collector rewrite.
- **Kind**: code | test | doc

**U18**

### A.U18.R01 WiFi: re-initialise the radio as the participant rung
- **Why**: G4/R22 / OR113.a (2) "every bus, every participant … recover the one participant (its own reset command or
  re-configuration) … restart the task; reboot" (owner, 2026-09-30); OR18.a — a failing chip may escalate, and a
  reboot "may recover a stalled chip" (owner, 2026-09-25); the WLAN hardware-exception streak today goes from retry
  straight to a task restart that never resets the radio (`_reset_wlan_connect_state()` `src/asy_wifi_service.py:295-316`
  only disconnects).
- **Site**: `src/asy_wifi_service.py` `_select_wifi_mode()` `:271-276`, `_switch_wlan_mode()` `:278-293`; new
  `_recover_device()` override in `AsyConnTime`.
- **Change**: (1) `_switch_wlan_mode()` returns `bool` (`True` after the re-construction `:288`, `False` in its `except`
  `:291-293`, which keeps `hw_op_failed` and errno 11); `_select_wifi_mode()` returns it. (2) `async def
  _recover_device(self) -> bool | None`: `if self._conn_phase == _PHASE_DEACTIVATED: return None` (no radio in use, no
  rung); else `return await self._select_wifi_mode(network.AP_IF if self._conn_phase == _PHASE_HOTSPOT else
  network.STA_IF)` — the same disconnect, `active(False)`, `deinit()`, re-construction the mode switch performs. On the
  pinned cyw43-driver `WLAN.deinit()` powers the chip off and resets its state ("Power off the WLAN chip and make sure all
  state is reset", `cyw43/src/cyw43_ctrl.c:118-146`, via `network_cyw43.c:133-138`), and the next `active(True)` drives
  `WL_REG_ON` low for 20 ms, then high, and reloads the firmware (`cyw43_ensure_up()` `cyw43_ctrl.c:148-175`) — the
  radio's own hardware reset. The next loop iteration reconnects as after any mode switch (STA: `_run_sta_mode()`; hotspot:
  `_run_hotspot_mode()` restarts the AP, whose own mode select repeats the re-initialisation once — bounded, 4 s of
  sleeps). No `_recovery_bus` (the radio's bus is inside the cyw43 driver). Resulting ladder: R1 each refresh, R2 at the
  2nd consecutive failed iteration (one wrnno 14, A.U10.R01), R5 past `max_module_error` (5, `:140`), R6, R7. Race-free:
  the re-initialisation holds `wifi_mode_lock` (`:272-276`), the lock every radio user takes (A.U18.34's table), and runs
  in the WiFi task itself; NTP's sync waits on the same lock (`asy_ntp_client.py:433-441`); open webserver connections
  drop as on any mode switch (lwIP netif removed by `cyw43_cb_tcpip_deinit()`, `cyw43_ctrl.c:126-127`) and clients
  reconnect.
- **Blast**: callers `_error_check()` (A.U10.R01), `_start_hotspot()` `:353-368`, `_leave_hotspot_mode()` `:327-334` (the
  new bool is ignored there, unchanged behaviour) · generated — · js — · tests existing:
  `tests/test_asy_wifi_service.py` streak tests (grep `max_module_error=` and `errno=17` there) see one mode re-select at
  the 2nd failed iteration — their WLAN-fake call logs re-derive; mode-switch tests hold (the bool is additive); new L1
  `tests/test_asy_wifi_service.py` — two consecutive `hw_op_failed` iterations: one `deinit()` and one `WLAN(STA_IF)`
  construction on the fake, one wrnno 14; in hotspot phase the AP mode is re-selected; deactivated: no call; a raising
  `deinit()` → errno 11 and "failed" · L2 `tests/test_digital_twin_sensortask_integration.py` (twin `network.WLAN`) —
  a WLAN fake raising on `status()` twice triggers one re-construction and the link comes back; the fake must count
  constructions per interface (U25) · L3 `tests_hardware/device_scripts/wifi_reconnect_after_failed_attempts_repro.py`
  gains a step calling `_recover_device()` on a connected STA and asserting the link returns within the connect budget
  (records the time) · L4 `tests_hardware/bench/test_network_resilience.py` unchanged (its AP-down/up scenarios are
  environment faults, which stay inside the module); no bus-hazard tier applies (no I2C/SPI) · twin as above · docs SPEC
  A.4 WiFi bullet: "repeated WLAN hardware errors first re-initialise the radio (power-cycled by the driver) before the
  task gives up"; SPEC F.2 (A.U14.R01) · toml — · uart —.
- **Depends**: A.U10.R01; co-lands with A.U18.32/A.U18.34 (lock hold table gains this holder), A.U18.28-A.U18.30
  (hotspot and deactivated paths), A.U10.18 (`wifi_mode_lock` name) — A-C merges. U18's verifier is still running: A-C
  re-checks these line numbers against its applied changes.
- **Kind**: code | test | doc

**U14** — the ladder's home text (no action existed)

G4/R22's State assigns "doc in U14/U36 (SPEC F.2, CLAUDE.md wedged-bus rule rewritten)" and OR113.a says "CLAUDE.md's
wedged-bus rule, SPEC F.2 and G4/R22 are rewritten to this ladder"; `audit/actions/U14.md` predates OR113 and carries no
such action (grep `OR113`/`ladder` in `U14.md` and `verify/U14.md`: none), so it is written here with a U14 ID.

### A.U14.R01 F.2 and CLAUDE.md state the recovery ladder
- **Why**: OR113.a "CLAUDE.md's wedged-bus rule, SPEC F.2 and G4/R22 are rewritten to this ladder" (owner, 2026-09-30);
  G4/R22 State "doc in U14/U36"; harmonization 38.
- **Site**: `SPECIFICATION.md:3604` (F.2 heading), `:3606-3608` (the wedged-bus head sentence, also edited by A.U0.37 and
  A.U14.16), `:3617-3623` (the hot-unplug paragraph, also A.U14.17 and A.U14.38); `CLAUDE.md:193-196` (hard rule, also
  A.U0.22).
- **Change**: (1) Heading → "## F.2 Blocking calls and the recovery ladder". (2) `:3606-3608` → "**Recovery follows one
  ladder, smallest blast radius first, escalating only when the milder step fails** (owner, 2026-09-30: 'always try to
  solve / recover from issues with the smallest possible blast radius … escalating up to a full bus reset is absolutely
  allowed if the mild measures don't work out'): retry; the participant's own reset or re-configuration; clear the bus;
  re-initialise its controller; restart the task; reboot; the hardware watchdog last. A `machine.I2C`/`machine.SPI`
  transfer in flight cannot be interrupted — no await point exists inside it — so the ladder acts after a transfer
  returns an error; rp2 bounds each I2C transfer by the bus timeout, and a call that never returns is the watchdog's (a
  stalled chip may still reach a reboot, owner, 2026-09-25)." — followed by A.U14.16's getaddrinfo/timeout-wrap text
  unchanged. (3) `:3617-3623` → "**The I2C ladder, per sensor** (C.7): a failed cycle is retried by the next trigger; at
  the second consecutive failure the driver recovers its chip (SCD30 and BMP3XX soft reset, BMP3XX then re-applying its
  stored configuration; ISL29125 re-applying its whole configuration; SGP40 heater-off to idle); at the third the bus is
  recovered — `I2C.recover()` clocks a held SDA free with up to nine SCL pulses and a STOP as plain GPIO, then
  re-constructs the controller with the full parameter set (rp2's only controller re-init: `machine.I2C.init()` is
  unsupported and `deinit()` a no-op, F.5.1), all under the bus lock; past `max_module_error` the task ends and the
  supervisor restarts it with a fresh setup (probe, identification, the chip's reset); the restart budget reboots the
  device, and every I2C bus is cleared once at boot before its controller is constructed. Each rung fires at most once
  per failure episode and logs one warning. The SGP40 general call stays the one reset that reaches other devices, at
  setup only (C.8). **Hot-unplug/replug is a kept feature: 'Live bus reconnect must be preserved' (owner, 2026-07-13)** —
  a chip unplugged and replugged is recovered by these rungs without a reboot when it is back before the restart budget
  runs out, as for every declared chip; a slave holding SCL, or one that nine pulses do not free, needs a power cycle — an
  operator action (DEVICE_REFERENCE.md). FRAM (C.3.1, A.4): a WREN retried once, identification retried at setup, a chip
  lost mid-operation stopped and set up again by its task's restart. WiFi (A.4): repeated radio errors re-initialise the
  radio before the task gives up. UART: J.5." — A.U14.38's proof sentence appends to this paragraph. (4) `CLAUDE.md:193-196`
  → "- **A wedged I2C bus or sensor recovers through the recovery ladder, smallest blast radius first — retry, the
  participant's own reset, bus clear and controller re-init, task restart, reboot, the hardware watchdog last** (owner,
  2026-09-30); a transfer in flight cannot be interrupted, so the ladder acts after it returns an error, and a call that
  never returns is the watchdog's. Full ladder and which waits can be timeout-wrapped: SPECIFICATION.md Part F.2." [src:
  OR113.a, G4/R22, harmonization 38]
- **Blast**: callers — · generated — · js — · tests — (no test pins F.2's or CLAUDE.md's wording: grep "accepted
  backstop" in `tests*/`: none; the old heading text appears nowhere else outside `audit/`, grep "wedged-bus backstop":
  `SPECIFICATION.md:3604` only) · twin — · docs BACKLOG `:58-67` (A.U14.16 / A.U0.22 wording: the deferred goal of a
  non-blocking alternative to an uninterruptible transfer stays, its "backstopped by the hardware watchdog" becomes
  "the ladder acts once it returns; one that never returns is the watchdog's"); SPEC C.7 (A.U10.R01), C.8 (A.U15.R02,
  Conflicts 2), C.3 (A.U13.R01), F.5.1 (A.U14.04 + A.U13.R01's sentence); DEVICE_REFERENCE.md operator actions (U36,
  LEAD/R14) gains the power-cycle line A.U14.17 names · toml — · uart —.
- **Depends**: A.U14.16, A.U14.17 (Conflicts 1), A.U14.38, A.U0.22, A.U0.37 (same sentences — Conflicts 3, 4); the
  mechanisms A.U10.R01, A.U13.R01, A.U15.R01-R04, A.U16.R01-R03, A.U18.R01; U36 owns CLAUDE.md's final wording pass.
- **Kind**: doc | rule

## Conflicts with existing actions

| action | conflict | correction |
|---|---|---|
| 1. A.U14.17 | Status "pending"; Change (a) head "never at runtime (OR64.a (2))"; "`init()` itself (the re-init path) never clears, so nothing touches a bus whose controller exists"; its F.2 text "once per bus at boot, never at runtime (owner, <answer date>)"; Blast (a) "CLAUDE.md's wedged-bus rule (runtime, watchdog backstop) unchanged"; Why cites OR64.a (2)'s boundary. OR113.a overtakes that reading and allows a mid-operation bus reset. | Status → "option (a), settled by OR113.a (1) (owner, 2026-09-30)"; Change (b) and Blast (b) go; Change (a) head → "a boot-time clear, once per bus, before the controller is constructed; the same clock-out is the runtime bus rung (A.U13.R01)"; "`init()` itself … never clears, so nothing touches a bus whose controller exists" → "`init()` itself does not clear; the runtime clear is `recover()`'s, under the bus lock"; `_clear_bus()` returns A.U13.R01's status mask and `__init__` stores it for `take_boot_clear_status()`; F.2 text "once per bus at boot, never at runtime (owner, <answer date>)" → merged into A.U14.R01's paragraph ("every I2C bus is cleared once at boot before its controller is constructed"); Blast (a) CLAUDE.md line → "rewritten by A.U14.R01"; Why: OR64.a (2)'s boundary → "OR113.a (1)/(2) (owner, 2026-09-30), overtaking the OR64.a (2) reading". |
| 2. A.U15.15 | Planned C.8 text: "The controller and the bus are not stalled … nothing may stall, hold or restart a bus or its controller, and the mechanism is not to be replaced (owner, 2026-09-26)" — attributes to the owner a boundary OR113.a overtakes ("A full bus reset is allowed mid-operation when the milder measures fail"). | "…; nothing may stall, hold or restart a bus or its controller, and the mechanism is not to be replaced (owner, 2026-09-26)" → "…; the mechanism is not to be replaced (owner, 2026-09-26). It stays the one reset that reaches other devices; every other recovery reaches only its own chip, or the bus as a whole through the recovery ladder's bus rung under the bus lock (owner, 2026-09-30; F.2)." The sentence "The controller and the bus are not stalled: the write is bounded by the bus timeout …" stays (a fact). |
| 3. A.U0.22 | CLAUDE.md:193 head → "For a genuinely wedged I2C bus/sensor, the hardware watchdog is the backstop" and :194-196 "— the current state, backstopped …" — names the watchdog as the recovery, with no ladder before it. | A-C takes A.U14.R01's CLAUDE.md bullet in place of A.U0.22's two CLAUDE.md edits; A.U0.22's BACKLOG deferred goal stays, its list item "a `machine.I2C` transfer on a wedged bus" → "a `machine.I2C` transfer in flight on a wedged bus (the recovery ladder acts once it returns; one that never returns is the watchdog's)". |
| 4. A.U0.37 | SPEC:3606-3608 → "… the hardware watchdog is the backstop (owner, 2026-09-25: 'a stalled chip may recover by a reboot'; escalation up to a reboot is intended)." — same issue at F.2's head. | A-C takes A.U14.R01 (2)'s sentence, which keeps the 2026-09-25 owner clause as "a stalled chip may still reach a reboot, owner, 2026-09-25". |
| 5. A.U16.17 | "No retry within the boot: the reboot re-runs construction and the whole batch"; `get_task_starters()` "returns `[]` when `self.fram.initialized`"; new L1 "after a good one, `[]`". | "No retry after `setup()` returns: `setup()` itself retries identification up to three times (A.U16.R02); a recovery later in the boot would leave loggers RAM-only (A.U16.06), so the reboot re-runs the batch"; `get_task_starters()` → one starter whenever a chip is declared (its task ends at once when the chip never came up, as written, and otherwise waits for a mid-operation loss, A.U16.R03); L1 "after a good one, `[]`" → "after a good one, one starter whose task waits on `fram.lost`". |
| 6. A.U14.38 | Keeps HEAD's paragraph body, which says the respawn "doesn't reconstruct the underlying `machine.I2C` peripheral (only a full reboot does that)" and that watchdog starvation "is what actually reconstructs `machine.I2C`" — false once A.U13.R01 lands. | Its owner-rule head and proof sentence attach to A.U14.R01 (3)'s rewritten paragraph; the two HEAD sentences go. |
| 7. A.U15.24 / A.U18.15 (A-C note, not a ladder conflict) | Both claim shared wrnno 11 (`DERIVED_DOMAIN`, `SOCKET_TEARDOWN`). | A-C assigns 11 to one and 12 to the other; this file's two codes are written as 14/15 and shift with them. |

No conflict found in: A.U13.01-A.U13.19 (none forbids a clear or re-init; A.U13.06's "the UART clamp-and-yield technique
is not applied to I2C/SPI" is about reads, not recovery), A.U10.* (A.U10.23 keeps the supervisor arithmetic; A.U10.26's
"FRAM bus-lock acquisition … gets no timeout" is about awaitable waits), A.U15.41 (timer re-arm on restart is the R1/R5
of its own fault), A.U16.* other than A.U16.17, A.U17.* (A.U17.33 consistent), A.U18.* (A.U18.13 keeps the per-call
re-create; A.U18.30's terminal deactivation is owner-confirmed behaviour, not a missing rung).

## Register fixes

1. **G4/R22** Req: "A call MicroPython cannot interrupt … is not wrapped in an asyncio timeout: a wedged bus, sensor or
   chip is recovered by task restart escalating to reboot and the hardware watchdog, never by an I2C-level timeout; the
   UART clamp-and-yield technique is not generalised to I2C/SPI, and a task respawn does not rebuild the bus
   peripheral." → "A call MicroPython cannot interrupt … is not wrapped in an asyncio timeout; a wedged bus, sensor or
   chip is recovered by the ladder below, whose bus rung — not a task respawn — rebuilds the I2C controller
   (re-construction with the full parameter set, the only re-init rp2 offers); the UART clamp-and-yield technique is not
   generalised to I2C/SPI." State: the "Work (OR113.a (2) …)" clause gains its actions — "code+test U10 (A.U10.R01),
   U13 (A.U13.R01, A.U13.R02), U15 (A.U15.R01-R04), U16 (A.U16.R01-R03), U18 (A.U18.R01; network side); U17 DONE
   (A.U17.33); doc U14 (A.U14.R01, with A.U14.17 option (a))". Evidence: `src/asy_i2c_driver.py:163-178` (the wrapper
   can re-construct), `extmod/machine_i2c.c:320-326` (`init()` unsupported on rp2).
2. **G3/R38** Req "Boundary: nothing may stall, hold or restart the bus or its controller." → "Boundary: it stays the one
   reset that reaches other devices; every other recovery reaches only its own participant, or the bus as a whole
   through the recovery ladder's bus rung under the bus lock (OR113.a)." Rank gains "OR113.a (owner, 2026-09-30)
   overtakes the OR64.a (2) boundary reading".
3. **G4/R19** Req "fakes return a fresh bus object and list that in the fidelity table" → "fakes keep per-id bus state
   across constructions (attached devices, injected faults, log), as rp2's static per-id object does
   (`ports/rp2/machine_i2c.c:50-53, 87`), because the recovery ladder re-constructs a bus mid-operation"; State gains
   "code in U24/U25 (per-id fakes, A.U13.R01)". Evidence: `digital_twin/machine.py:238-247` re-wires fresh chips per
   construction.
4. **G5/R27** Req "The FRAM layer does not retry" → "The FRAM layer does not retry a read (the dual copy is the read
   path's retry, owner, 2026-09-24); a WREN whose latch did not set is repeated once, like WRDI (OR113.a)". State gains
   "code in U16 (A.U16.R01)".
5. **G5/R32** State (the RF153 clause) gains: "a chip lost after boot stops FRAM access and ends the manager's task,
   whose restart re-runs `setup()`; `get_task_starters()` returns one starter whenever a chip is declared (A.U16.R03,
   OR113.a); `FRAM_SPI.setup()` retries identification (A.U16.R02)".
6. **LEAD/R29** Req "recovers without a reboot (task end, supervisor restart, fresh `setup()`)" → "recovers without a
   reboot through the recovery ladder (participant recovery, the bus rung, task restart with a fresh `setup()`), when it
   is back before the restart budget reboots the device — as for every declared chip (OR89.a (5)); the FRAM through
   A.U16.R03" — the L2 twin test keeps the absence shorter than the escalation. Evidence: `src/system_service.py:229-253`
   (an init that keeps failing reaches the reboot after four restarts).
7. **G6/R27** State gains "code in U18 — a `hw_op_failed` streak re-initialises the radio before the task gives up
   (A.U18.R01, OR113.a)".
8. **G4/R22** State "any getaddrinfo residue …" unchanged; its "hardware in C — one row measures it" gains the two L3
   rows of this file: the held-SDA recovery script (A.U13.R02) and the FRAM CS-held-inactive loss case (A.U16.R03).

## Open points

None left for the owner after self-resolution. Settled by reading, each with its source:
- Participant rung for the SGP40 is the device-addressed heater-off, not the general call: OR113.a (2) "recover the one
  participant" plus "the SGP40 general-call reset stays the one owner-accepted reset that reaches other devices" — the
  general call stays at setup, its frequency unchanged (A.U15.R02).
- The retry rung for I2C readers is the next triggered cycle, not an immediate in-cycle repeat: the legacy loop the
  owner field-proved retries the same way (`python/IndividualDrivers/*`: reset at setup only, no in-cycle retry), and
  no fault class was found that a same-cycle repeat fixes and the next cycle does not (U10/U15 tables).
- FRAM reads get no retry beyond the dual copy (owner, 2026-09-24, SPECIFICATION.md:3755); the WREN retry and the
  identification retry are write/identity transactions outside that decision (A.U16.R01, A.U16.R02).
- A FRAM chip lost mid-operation escalates like a sensor (OR89.a (5) "the same as all other chips" + OR113.a (2)
  "mid-operation … reboot"); the resulting reboot loop on a chip that stays dead is the same as for a dead declared
  sensor (A.U16.R03).
- The WiFi terminal deactivation and the CYW43 false-positive case get no further rung: owner-confirmed behaviour
  (SPEC A.4 list, CLAUDE.md hard rule), and OR18/OR18.a keep environment conditions inside the module.
- UART controller re-init stays a non-rung (lead, AC_NOTES 16; A.U17.33).
- Thresholds (participant at the 2nd, bus at the 3rd consecutive failure; FRAM probe at the 2nd anomaly; three
  identification attempts) are agent tunables with Part N rows, to be confirmed on the bench (phase C) — not owner
  choices.
