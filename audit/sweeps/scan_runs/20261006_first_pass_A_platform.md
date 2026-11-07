# Silent-failure scan, half A: the platform boundary (classes 1, 2, 3, 5)

Scope: every `machine.*` / `rp2` / `network`+cyw43 / `socket`+lwIP / `select` / `asyncio` / `os`+littlefs+flash /
`time` / `gc` / `micropython` / Microdot API that `src/` and the generated `build/generated_src/sensortask_*.py`
(regenerated with `scripts/_generate_sensortask_modules.py`, 6 devices) rely on, read at MicroPython **v1.29.0**
(`/root/pico-toolchain/micropython`, `git describe` = `v1.29.0`; pico-sdk 2.3.0; littlefs `lib/littlefs/lfs2.c`) and
`ext/microdot.py`; chips against the extracted datasheets. Read-only; no hardware touched. Line numbers are HEAD's.
Modes per OR148 (silent_failure_scan.md "Operating modes"); each finding carries a `mode:` field.

Devices/buses (from `devices/*.toml`): SCD30 on i2c0 (arzi, grkizi, klkizi, schlafzi, wozi) / i2c1 (dev); SGP40 on
i2c1 (all); BMP3XX on i2c0 (dev) / i2c1 (wozi); ISL29125 on i2c1 (dev only); FRAM on spi0 (all); NeoPixel (all, 1 LED);
UART link x2 (dev only). wozi is never flashed (twin/unit tiers only); dev is the bench board.

## Findings (not covered or partly covered)

### A-01 I2C: a data byte the device NACKs is accepted as a complete write
- **Site**: `src/asy_i2c_driver.py:71-75` (`_writeto_mem`, used by `set_bits()` :140-142 and `set_register_struct()`
  :161), `:231` (`writeto()` returns the ACK count), `:344` (`I2CDevice.write()` discards it), `:249`
  (`writeto_then_readfrom()` discards it). Callers: `asy_scd30_driver.py:470, 480` (every command, every register
  pointer, every NVM config write), `asy_sgp40_driver.py:574` (every command), BMP3XX `set_register_struct`/`set_bits`
  (PWR_CTRL, OSR, IIR, CMD), ISL29125 config writes.
- **Class**: 1. **Mode**: plain operation, bus disturbance, a peripheral resetting mid-transaction, runtime
  reconfiguration (PUT of an SCD30/BMP/ISL setting).
- **Failure**: the address is ACKed but a later byte is NACKed (ABRT_TXDATA_NOACK).
- **Layer below**: pico-sdk `hardware_i2c/i2c.c:229-231` returns `byte_ctr` (a non-negative short count) for
  ABRT_TXDATA_NOACK, not an error; `ports/rp2/machine_i2c.c:150-158` passes any non-negative value through;
  `extmod/machine_i2c.c:467-472` `writeto()` raises only for `ret < 0` and returns the ACK count; `:640-648`
  `writeto_mem()` raises only for `ret < 0` and returns `None`, so its short count is not even observable.
  (Also noted, unconfirmed in effect: the SDK carries "TODO Could there be an abort while waiting for the STOP
  condition here?" at `i2c.c:193-195`, i.e. an abort during the final STOP wait is not examined.)
- **Our code**: never compares the count with the length; `writeto_mem` gives it nothing to compare.
- **Effect**: SCD30 (all six devices): a `set_*` whose argument bytes were NACKed returns True → REST answers "Valid"
  for an NVM setting the chip never took; a register-pointer write cut short leaves the following CRC-valid read
  answering for a pointer we did not set (whether the SCD30 then returns another register's word is not stated in
  the Interface Description — unconfirmed). BMP3XX (dev i2c0, wozi i2c1): an OSR/IIR write silently not applied
  (a lost PWR_CTRL write ends visibly in the drdy timeout). ISL29125 (dev i2c1): config write silently not applied.
  SGP40: a cut measure command → the following read is NACKed (datasheet SGP40 §"I2C communication", lines 438-441:
  busy/no-data reads are NACKed) → OSError, visible.
- **Work order**: **not covered**. M.SRC_SENS.011/.012 (U13/U30) make the helpers return `bool`, but the bool means
  "bus initialised" (`writeto(...) is not None`), not "all bytes ACKed"; M.SRC_SENS.057's "bool-checked write" inherits
  that. No M entry or register row mentions the ACK count.
- **Owner unit**: U13 (`src/asy_i2c_driver.py`, M.SRC_SENS.011/.012). **Conservative fix**: at the I2C choke point,
  raise `OSError(EIO)` when `writeto()` returns fewer ACKs than bytes; replace `writeto_mem()` (no count) with a
  `writeto()`/`writevto()` of register+payload whose count is checked. Count it on the bus object. Every driver's
  existing `OSError` path then reports it. Fakes (`tests/machine.py`, `digital_twin/machine.py`) need a short-ACK mode
  for the L1/L2 proof.

### A-02 I2C: a register-address NACK on a register read returns stale bytes from the shared scratch buffer
- **Site**: `src/asy_i2c_driver.py:58-68` (`_read_into_scratch` over the per-bus `_scratch`), reached by `get_bits()`
  :91, `get_register_struct()` :107 and the read half of `set_bits()` :136 (read-modify-write).
- **Class**: 1 (and 3: the data has no CRC on BMP3XX/ISL29125). **Mode**: plain operation, bus disturbance,
  a peripheral resetting on its own.
- **Failure**: device ACKs its address but NACKs the register-address byte.
- **Layer below**: rp2 sets no `transfer_supports_write1` (`ports/rp2/machine_i2c.c:160-163`), so
  `extmod/machine_i2c.c:554-559` `read_mem()` writes the memaddr with `nostop`, and on `ret != memaddr_len` issues a STOP
  and **returns that short count (0)**; `readfrom_mem_into()` (`:625-628`) raises only for `ret < 0`, so it returns
  `None` with the destination buffer untouched.
- **Our code**: decodes the scratch view as if freshly read — it still holds the previous read on that bus.
- **Effect**: BMP3XX (dev i2c0, wozi i2c1): the STATUS poll can see the last cycle's drdy bits, the data burst can
  return the previous burst → a previous measurement re-reported with a new timestamp (the range gate passes, it is a
  real value); `set_bits()` RMW writes field bits derived from a stale byte into OSR/CONFIG. ISL29125 (dev i2c1, shares
  the scratch with no other scratch user): stale status/counts. SCD30/SGP40 are not affected (plain write + `readinto`
  into their own buffers, CRC-checked).
- **Work order**: **not covered** (M.SRC_SENS.011 keeps `readfrom_mem_into` and the scratch view).
- **Owner unit**: U13 (M.SRC_SENS.011; U30 stage). **Fix**: do the register read as `writeto(addr, reg, stop=False)`
  with its ACK count checked (A-01) followed by `readfrom_into`, or check `read_mem`'s outcome another way; never
  decode the scratch after a transfer that did not fill it.

### A-03 I2C abort reason is discarded below us (record why it cannot be read)
- **Site**: every `OSError` from `machine.I2C` in `src/asy_i2c_driver.py`.
- **Class**: 1. **Mode**: plain, wedged bus, absent sensor.
- **Layer below**: the SDK reads `IC_TX_ABRT_SOURCE` and clears it (clear-on-read, `i2c.c:180-186, 300-303`), then
  folds address-NACK, unknown aborts and arbitration loss into `PICO_ERROR_GENERIC` (`:222-235, 319-328`);
  `machine_i2c.c:150-155` maps everything but a timeout to `EIO`. So "no device", "lost arbitration" and "other
  abort" are one `EIO`; the register is already clear when Python could look.
- **Our code**: treats all `OSError`s alike (correct given the information).
- **Work order**: not covered (nothing records that the distinction is unavailable). **Owner**: U13. **Fix**: one
  sentence in SPEC F.5/F.2 (and the I2C header) stating that the abort cause is not recoverable at v1.29.0 and why;
  no code.

### A-04 SCD30: a trigger without data-ready re-stores the cached reading with a fresh timestamp
- **Site**: `src/asy_scd30_driver.py:595-611` (`read_measurement()` returns without touching the cache when not
  ready), `:174-187` (`_read_scd()` then returns the cached CO2/T/RH with a new `timestamp`), `:189-202`
  (`_store_scd()` stores them).
- **Class**: 1 (data-ready status read but its "not ready" outcome not propagated). **Mode**: RDY line fault (stuck
  high/floating), a spurious RDY edge, SCD30 resetting on its own or `ContMeas=false` with RDY held, warm-up.
- **Layer below**: Interface Description §1.4.4 ("returns 1 [when a measurement is available] and 0 otherwise");
  datasheet RDY pin "High when data is ready for read-out" (SCD30 Datasheet, pin table, line 174).
- **Our code**: `scd_init_irq()` (:412-420) sets `read_event` after `trigger_sec` of RDY high; if the register says 0
  every such trigger re-publishes the last values as current, indefinitely and without any log.
- **Effect**: all six devices: frozen CO2/T/RH (and derived WetBulb/DewPoint, and the WarnCO2/WarnHum notifications)
  presented with current `TS`.
- **Work order**: **partly covered**. M.SRC_SENS.055/.057 (U15/U31) make `read_measurement()` return `new_data` and
  thread it next to the results, but use it only for the FRC step; `_store_scd()` still stores when values are
  non-`None`. **Owner**: U15. **Fix**: do not store (keep the previous `TS`) when `new_data` is False; count consecutive
  not-ready triggers and persist one warning at a threshold (the ISL29125 "periodic-only" detector shape,
  `asy_isl29125_driver.py:433-446`).

### A-05 BMP3XX: chip self-reset (por_detected) and fatal_err are never read
- **Site**: `src/asy_bmp3xx_driver.py:429-447` (read path), config applied at init/PUT only (`:503-507, :587-621`);
  ERR_REG read only after our own soft reset (`:636-646`, cmd_err only).
- **Class**: 1. **Mode**: a peripheral resetting on its own (supply glitch), long uptime.
- **Layer below**: BMP390 DS002 §4.3.8 Table 33 / BMP388 DS001 §4.3.7: EVENT (0x10) `por_detected` = 1 after power-up
  or soft reset, clear-on-read; §4.3.3 Table 28: ERR_REG bit 0 `fatal_err`. OSR (0x1C) / CONFIG (0x1F) return to their
  reset values on a reset (register map, DS002 Table 24).
- **Our code**: PWR_CTRL is rewritten each cycle, so forced reads continue after a chip reset — under default
  oversampling/IIR, while GET /sensors reports the configured values. `fatal_err` never consulted.
- **Effect**: dev (i2c0), wozi (i2c1): noisier/differently filtered pressure reported as configured, no log.
- **Work order**: **not covered** (no `por_detected`/EVENT/`fatal_err` in any M entry or the register).
  **Owner**: U15 (M.SRC_SENS.043/.044/.048). **Fix**: read EVENT (and ERR_REG) once per cycle with the burst; on
  `por_detected` log once and re-apply the stored config through the existing re-apply path (M.SRC_SENS.044);
  `fatal_err` fails the read into the recovery ladder; consume the `por_detected` our own soft reset raises in init.

### A-06 UART: framing, break (and parity) errors are not read — the plan reads only OE
- **Site**: `src/asy_uart_driver.py` receive path (planned choke point of M.SRC_NET.221 (6)).
- **Class**: 3 (CRC/framing left to detect what a flag reports explicitly) and 1. **Mode**: plain, peer reset mid-frame
  (line held low → break), boot (line glitches before the peer is up), dev only.
- **Layer below**: `ports/rp2/machine_uart.c:162-188` drops UARTDR[11:8] (the motivating case); the planned DMA ring
  reads UARTDR as 8-bit transfers, which also drops them. RP2040 DS Table 427: UARTRSR FE (bit 0), PE (1), BE (2) are
  sticky until a UARTECR write, like OE (3); Table 426: a break loads one 0x00 character into the FIFO.
- **Our code (as planned)**: reads UARTRSR on every fill-level read, acts on OE only.
- **Effect**: dev (both instances; later the C peer): a corrupted or break-inserted byte reaches the codec as data;
  caught only by CRC (optional per the plan's own text) or framing.
- **Work order**: **partly covered** by M.SRC_NET.221 (6) (OE). **Owner**: U13. **Fix**: in the same UARTRSR read, treat
  FE|BE (|PE when parity is configured; the generated `UART(...)` uses none today) as the same receive fault — fail the
  frame, clear via UARTECR, count separately from OE. Receiver-side tightening only (Class A, no wire change).
  Unconfirmed: the PL011's RSR is updated per DR read; whether DMA reads update RSR identically to CPU reads is not
  stated in the RP2040 datasheet — the bench test of (6) should cover FE as well.

### A-07 UART TX stalls mid-frame during a flash erase
- **Site**: `src/asy_uart_driver.py:127-141` (`_write_all()` returns once bytes are queued); the config flush
  (`src/config_manager.py:375-376`) can run right after.
- **Class**: 5. **Mode**: flash write (config flush, boot repair) during UART traffic; dev only.
- **Layer below**: `machine_uart.c:625-664` queues into a ring and returns; the ring is refilled into the 32-byte TX
  FIFO from the UART IRQ (`:217`); `rp2_flash.c:279-281, 298-300, 311-313, 345-347` disable interrupts for each
  erase/program; W25Q16JV tSE 4 KB = 45 ms typ / 400 ms max, tPP 0.4/3 ms (datasheet AC table, lines 3040-3041).
- **Effect**: a frame longer than the 32-byte FIFO (the 53-byte frames of F.5.8) can pause on the wire for up to
  ~400 ms. Whether the receiver's deadline (J timing) fires inside that gap is **not confirmed** from source; the
  worst outcome is a failed, retried transaction (visible), not silent loss.
- **Work order**: **partly covered**: the timing-budget change (M.SPEC, `stall.flash_program`, U31) takes the RX
  consumer off the crossing (`con.uart_rx_ring`) but has no TX row. **Owner**: U13 (driver) / U31 (budget table).
  **Fix**: add a TX consumer row (max tSE vs the receive deadline) and a twin/bench check; no code unless it crosses.

### A-08 lwIP UDP: per-socket receive queue of 4 datagrams, extras dropped with no trace
- **Site**: `src/asy_udp_socket.py:126-148` (`ready()` polls every `wait_time_ms=20`), `src/captive_dns.py:98`
  (server mode).
- **Class**: 2. **Mode**: hotspot / captive-DNS mode (a phone's captive-portal probe burst); NTP/DNS clients expect one
  reply and are unaffected.
- **Layer below**: `extmod/modlwip.c:299` `LWIP_INCOMING_PACKET_QUEUE_LEN (4)`; `:456-461` "No room in the inn, drop
  the packet" — freed in the lwIP callback, no counter, no flag.
- **Our code**: cannot see it; one datagram per wake.
- **Effect**: all six devices in hotspot mode: queries beyond 4 per poll interval are lost; clients retry on their own
  timeout (seconds of portal delay), nobody counts it.
- **Work order**: **not covered** (M.SRC_NET.007/.028/.030 bound the size and the poll, not the queue).
  **Owner**: U18. **Fix**: record why it cannot be counted (C.7.2 / F.5 sentence + comment at `recvfrom`); drain every
  queued datagram per wake before sleeping; make sure M.SRC_NET.028's idle rate does not lengthen the server's poll.
- Related, covered: a datagram longer than the receive size is cut silently (`modlwip.c:719`) — documented by
  M.SRC_NET.030 (U18/U28); harmless for NTP (48 B header) and DNS (512 B, answer parse fails closed).

### A-09 Hotspot DHCP server: 8 leases for 24 h; a request with no free slot is ignored
- **Site**: hotspot mode in `src/asy_wifi_service.py:353-420` (`_start_hotspot()`), `:232-246`
  (`_get_hotspot_stations()` counts associated stations).
- **Class**: 2. **Mode**: hotspot/AP.
- **Layer below**: `shared/netutils/dhcpserver.h:32` `DHCPS_MAX_IP (8)`; `dhcpserver.c:68` lease 24 h;
  `:234-236` "No more IP addresses left" → `goto ignore_request` (no NAK, no counter).
- **Our code**: an associated station without a lease still counts as "client present" and keeps the hotspot open,
  while it can reach neither the captive DNS nor the setup page.
- **Effect**: all six devices; only after 8 distinct client MACs within 24 h (MAC-randomising phones make this
  reachable).
- **Work order**: **not covered** (THIRD_PARTY_LICENSES.md's DHCP note, M.DOCS.012, is licensing only). **Owner**: U18.
  **Fix**: record the cap and that it is invisible to Python in SPEC's hotspot paragraph; no code.

### A-10 Reset cause: the hardware distinguishes what `machine.reset_cause()` collapses
- **Site**: HEAD never reads a reset cause (`grep reset_cause` over `src/` and `build/generated_src/`: none); planned
  `begin_boot()` (M.SRC_CORE.006) decodes `reset_cause()` + the `mem_backup` record.
- **Class**: 1. **Mode**: boot; each reset kind; reset countdown; boot loop; KeyboardInterrupt (A-14).
- **Layer below**: `ports/rp2/modmachine.c:74-89`: `machine.reset()` is `watchdog_reboot(0, SRAM_END, 0)`, and
  `reset_cause()` returns WDT_RESET whenever `watchdog_hw->reason != 0`, else PWRON_RESET. The hardware keeps more:
  WATCHDOG REASON (0x40058008) TIMER (bit 0, starvation) vs FORCE (bit 1, set by `_watchdog_enable(0)` →
  `WATCHDOG_CTRL_TRIGGER`, pico-sdk `watchdog.c:65-66`; RP2040 DS Table 548); SCRATCH4 (0x4005801C) =
  `0x6ab73121` after `watchdog_enable()` (machine.WDT), 0 after `machine.reset()`, `0xb007c0d3` for a pc reboot
  (`watchdog.c:79-84, 98-110`); CHIP_RESET (0x40064008) HAD_POR (POR **or brown-out**), HAD_RUN, HAD_PSM_RESTART (RP2040 DS
  Table 191, §2.12.7).
- **Our code (as planned)**: "region 0 empty + WDT_RESET → watchdog (2)"; PWRON → "power on (1)".
- **Effect**: all six devices: (a) a `machine.reset()` outside `_reboot()` (mpremote/REPL `reset`, bench harness) is
  recorded as a watchdog reset; (b) RUN-pin reset, brown-out, power-on and debugger reset all read "power on";
  (c) a watchdog that fires after `_reboot()` wrote its record (a hung flush, a dropped arm) is recorded as the
  commanded code, not as "the watchdog fired".
- **Work order**: **partly covered** by M.SRC_CORE.006 (U11). **Owner**: U11. **Fix**: in `begin_boot()` also read
  REASON and CHIP_RESET via `machine.mem32` (both read-only, survive until the next reset) and keep them with the
  decoded code; if SCRATCH4 is used it must be read before the boot entry's `WDT(timeout=8000)` (M.GEN.001 arms it
  first), because `machine_wdt.c:59` → `watchdog_enable()` overwrites it. Unconfirmed: whether `mem_backup` region 0
  survives a RUN-pin reset (the datasheet only says scratch "persists through soft reset of the chip").

### A-11 Storage auto-unpause is a single soft one-shot; a dropped fire leaves FRAM paused until reboot
- **Site**: `src/system_service.py:354-374` (`pause_permanent_storage()`, `Timer.ONE_SHOT`); planned
  M.SRC_CORE.012 keeps the one-shot, now setting `_unpause_flag`.
- **Class**: 5. **Mode**: `mempause` system command (300 s, generated `_system_cmd_callback`), heap/scheduler pressure.
- **Layer below**: `shared/runtime/mpirq.c:103-106` ignores `mp_sched_schedule()`'s result; `py/scheduler.c:163-181`
  returns false when the queue is full (depth 8, `ports/rp2/mpconfigport.h:131`); `machine_timer.c:56-57` does not
  re-arm a one-shot.
- **Effect**: all six devices: every FRAM write refused for the rest of the uptime — FRAM-backed error logs and the
  SGP40 baseline backup stop; the "paused" warnings themselves cannot persist (FRAM is paused). No backstop.
- **Work order**: **not covered** (M.SRC_CORE.012 handles the reset/shutdown race, not a lost fire; SPEC C.9's
  "PERIODIC for anything that must keep firing" does not reach it). **Owner**: U11. **Fix**: deadline-based unpause
  (`ticks_add(now, duration)` checked by an existing 1 Hz tick or the supervisor pass), or a PERIODIC timer deinit'd by
  the waiter on its first delivered fire (F.1's hotspot-shutoff pattern); count a late unpause.
- Same mechanism, already covered: the reset arm (`:126`) — WDT backstop once the feed is latched (M.SRC_CORE.009/.010/
  .011); the boot sequencer (`:165-169`) — WDT backstop by owner decision (M.SRC_CORE.014) and recorded as a boot-phase
  failure (M.SRC_CORE.006); the NTP retry (`asy_ntp_client.py:281-285`) — owner-accepted, next regular sync
  (M.SRC_NET.051).

### A-12 UDP socket swallows `MemoryError` without its text, so the memory gates cannot see it (pointer for half B)
- **Site**: `src/asy_udp_socket.py:145, 159, 167, 178` (`except (OSError, MemoryError, TypeError)` → `None`/`False`, no
  log by design — the class owns no logger).
- **Class**: 1 at our side of the boundary (4 proper — handed to half B). **Mode**: heap near full.
- **Layer below**: `modlwip.c:642-646` `pbuf_alloc` failure → `ENOMEM`; MicroPython heap `MemoryError` from the
  receive buffer allocation.
- **Effect**: all devices: an allocation failure in NTP/DNS/captive DNS is logged only as "no reply"/"receive failed";
  the four CLAUDE.md memory gates grep for `memory allocation failed` and never see it.
- **Work order**: not covered (M.SRC_NET.030 keeps the tuples). **Owner**: U18 (U30 for the memory rule).
  **Fix**: return a distinguishable sentinel or let `MemoryError` propagate (CLAUDE.md memory rule), so the caller logs
  `str(e)`.

### A-13 FRAM: a write torn between block 0 and block 1 is discarded at the next boot (covered by owner decision)
- **Site**: `src/asy_fram_manager.py:172-177` ("Both blocks valid but different" → False), `src/print_log.py:273-279`
  (`setup()`: read False → `_write()` overwrites both blocks).
- **Class**: 6/1. **Mode**: power loss or reset mid FRAM chunk write.
- **Layer below**: MB85RS has no write-status/error bits beyond WEL/BP (DS501-00015 / -00032 status register);
  detection is ours (status bytes, CRC, dual copy) and works: a BUSY status byte fails the block (`:226-233`).
- **Work order**: covered by the owner decision "hard failure, never a guess" (2026-07-18; M.SRC_CORE.065 and the
  `_read()` rewrite at M_SRC_CORE.md:1818-1828, U16). Residual, stated for completeness: the newer block-0 copy (written
  first) is lost with the older one; at most the entries of the torn write.

### A-14 `KeyboardInterrupt` from a USB host ends the whole event loop; recorded as a watchdog reset
- **Site**: boot entry (`buildgen/codegen.py:696-709`; M.GEN.001) `try: asyncio.run(main()) finally: ...`.
- **Class**: 1 (cause lost). **Mode**: KeyboardInterrupt from the REPL (mpremote sends Ctrl-C), bench only.
- **Layer below**: `extmod/asyncio/core.py:154, 194` catch only `(CancelledError, Exception)`; a `KeyboardInterrupt`
  raised inside any task leaves `run_until_complete()`; the WDT is not stopped and resets the board ≤ 8 s later.
- **Effect**: dev bench: a pending deferred config flush task never runs (accepted change not persisted); the reset
  decodes as "watchdog" (A-10). **Work order**: not covered. **Owner**: U20 (boot entry). **Fix** (conservative): in the
  boot entry write a distinct reset-reason code for an interrupted run before returning to the REPL.

## Checked, nothing found (per API family)

- **machine.SPI** (`asy_spi_driver.py`, FRAM): rp2 `machine_spi.c:264-340` detects RX overrun on the ≥ 32-byte DMA path
  (RORRIS, clears it, raises EIO for reads), the < 32-byte path cannot overrun (in-flight bound); our code lets
  `OSError` propagate (`:75-81, 90-96`), the FRAM manager logs it (errno 47/26). DMA claim failure falls back to the
  blocking path (`:275, 330-337`). Nothing silent.
- **FRAM chip** (MB85RS64V/MB85RS2MTA): only WEL/BP/WPEN status exists; WREN is verified via RDSR before every
  write/WRSR, WP readback verified, RDID checked at setup/re-probe (`asy_fram_driver.py:182-252`). An absent chip
  reads 0x00 (RP2040 pad default pull-down, PADS_BANK0 GPIOx PDE reset 1; rp2 `machine_spi.c` sets no pull) → WEL not
  set → visible failure. Unconfirmed residual: a board pull-up on MISO would make RDSR read 0xFF (WEL "set", and
  "stuck" only as warning 81).
- **ISL29125**: BOUTF (brownout) handled and config re-applied, RGBTHF and the reserved-bit mask checked, a dead INT line
  detected (`asy_isl29125_driver.py:390-404, 433-470`); CONVENF is advisory. Only A-01/A-02 apply.
- **SGP40**: every reply word CRC-checked, self-test checked (`asy_sgp40_driver.py:578-582, 682-694`); busy reads are
  NACKed by the chip (datasheet lines 438-441) → OSError. Only A-01 applies, and visibly.
- **WS2812/NeoPixel**: no readback exists on the part; `machine.bitstream` holds IRQs off (`machine_bitstream.c:67,
  114`) for 1 LED ≈ 30 µs — negligible against every consumer.
- **machine.UART TX**: short writes handled (`_write_all()` loop; `machine_uart.c:646-652` returns the partial count
  or EAGAIN→`None`). OE: covered by M.SRC_NET.221 (6).
- **machine.Timer**: every `init()` site catches `(OSError, MemoryError)` for ENOMEM (`machine_timer.c:107-110`);
  periodic soft-timer drops self-heal (F.1); interrupt-off delays only coalesce fires — counts now come from
  `ticks_diff` (`TickSeconds`, M.SRC_CORE.032/.013, M.SRC_NET.052/.058, wifi uptime M.SRC_NET U18).
- **Pin.irq (soft)**: SCD30 RDY and ISL29125 INT can be dropped like timer callbacks (`mpirq.c:105`); both have a
  periodic path (SCD30 500 ms stuck-pin tick; ISL divider + dead-INT detector). Edge events during interrupts-off are
  latched (RP2040 DS Table 286, INTR EDGE bits are write-to-clear) and delivered afterwards.
- **time/ticks**: every elapsed-time use goes through `ticks_diff`/`ticks_add` (grep: asy_bmp3xx :545-551, isl29125,
  notification :178, uart_comm :521-550, uart_driver :250-284, udp_socket :133-142); no raw subtraction. `time.time()`
  only in `cettime()` (wall clock, correct use). Pre-sync timestamps: covered (`utc_now()` → `None` before sync,
  M.SRC_CORE.032; M.SRC_SENS.089/.090).
- **machine.RTC**: `machine_rtc.c:95` ignores `aon_timer_set_time()`'s bool, which is false only for out-of-range
  dates; our input is gated to 2025-2100 first (`asy_ntp_client.py:258`, before `RTC().datetime()` at `:263`). Unreachable.
- **WDT**: `WDT(timeout=8000)` within the 8388 ms cap (`machine_wdt.c:38, 56-58`); stop-feed path and latched feed:
  covered (M.SRC_CORE.009/.010). Soft reset (Ctrl-D) does not stop the hardware watchdog (none of `main.c:265-304`
  touches it) — the next boot re-arms it first.
- **Soft reset**: `main.c:265-304` resets the UARTs (`uart_deinit` → `uart_reset`, `machine_uart.c:483-497`,
  `uart.c:95-98`) before `gc_sweep_all()` runs the DMA and Timer finalisers (`machine_timer.c:162` `__del__`), so the
  planned ring's channel loses its DREQ before its buffer is freed — consistent with M.SRC_NET.221 (5). PIO state
  machines reset, cyw43 PIO programs kept (`rp2_pio.c:177-202`); I2C/SPI objects are static and not deinitialised
  (harmless).
- **os / littlefs / flash**: write and close errors raise (`vfs_lfsx_file.c:172-188`, `py/stream.c:254-268` used by
  `json.dump`), caught and logged (errno 14/4). `rp2_flash.c:283, 324, 348` "TODO check return value" — `flash_range_*`
  return nothing — is compensated by littlefs reading back every program (`lfs2.c:189-200`, `LFS2_ERR_CORRUPT` →
  relocate). Power loss mid write: `O_TRUNC` only marks the open file dirty (`lfs2.c:3146-3149`), the commit is at
  close, so the old file survives and the accepted change is lost (owner-accepted residual, SPEC F.2). Full
  filesystem → ENOSPC → logged, running unpersisted.
- **Flash write window** (interrupts off ≤ 400 ms per sector erase): UART RX — covered by the DMA ring; UART TX — A-07;
  soft Timers — delayed, coalesced, counts from ticks (covered); Pin edges — latched; ticks/RTC — hardware counters,
  no loss; WDT — far below 8 s; cyw43/lwIP — the CYW43 firmware buffers frames internally and lwIP's timers run late;
  what the closed CYW43 firmware drops under a 400 ms host stall **cannot be confirmed from source**.
- **network/cyw43**: all `STAT_*` outcomes mapped (`asy_wifi_service.py:601-621`, NOIP as `_STAT_OBTAINING_IP`); DHCP
  failure stays NOIP → not connected → reconnect; an IP change is read live (`ifconfig()` each use, server bound to
  0.0.0.0). The `isconnected()` false positive is owner-accepted (SPEC F.2).
- **socket send/receive**: send failures surface as `None` and are no longer waited out (M.SRC_NET.029, .048);
  POLLERR/POLLHUP reported by `ready()` (`:139-141`).
- **Microdot**: request-line/header/body caps (`microdot.py:291-317, 535-537, 1443-1445`) — set to the device value
  (`asy_webserver_service.py:363-370`); the parse-failure console traceback (`:1406-1407`) is replaced by the bounded
  head (M.SRC_NET.118, M.SPEC (6)); listen backlog explicit (`:353, 738`).
- **USB CDC stdout**: with a host holding the port open and not reading, each write blocks ≤ 500 ms then drops the
  rest (`shared/tinyusb/mp_usbd_cdc.c:102-142`, `mphalport.h:36`); without a reader-less open port it never blocks.
  Owner-accepted debug-mode limitation (M.SPEC (9), 2026-09-30); `DebugLevel` 0 prints nothing (`print_log.py:53-71`).
- **gc / micropython**: no failure statuses; emergency exception buffer added by M.GEN.001; soft callbacks allocate
  nothing (`lambda _b: flag.set()`).

## Not done in this half
Classes 4, 6, 7 except where a platform fact forced a note (A-12, A-13, A-14); `js/`, `digital_twin/` and host tooling;
the C peer (`arduino/`, out of scope); SCD30 NVM write interrupted by power loss (the Interface Description says
nothing about it — unconfirmable).

## Addendum: smallest inherent change per finding (owner rule on fix proposals)

Is the site already safe by construction? None of A-01..A-12 or A-14 is (each cites the code path that loses the
status); A-13 is safe by owner decision. Smallest change that closes each gap:

- A-01: test the value `writeto()` already returns (ACK count == len, else raise `OSError(EIO)` at the one choke
  point); `writeto_mem()` returns nothing, so its two call paths become a `writeto()` of a preassembled buffer — a
  different call, no new state.
- A-02: an ordering change — write the register address with `writeto(..., stop=False)` (count tested as in A-01), then
  `readfrom_into()`; no new state.
- A-03: no code; one SPEC sentence.
- A-04: test the bool M.SRC_SENS.057 already returns (`new_data`) in `_store_scd()`; the persisted "stuck RDY" warning
  needs one counter, only because nothing else distinguishes a single late edge from a line that never clears.
- A-05: one extra register read per cycle (EVENT, clear-on-read) and reuse of the existing re-apply path; no new state.
- A-06: widen the mask the planned UARTRSR read already tests (OE → OE|FE|BE); a separate count only if the owner wants
  FE/BE told apart from OE.
- A-07: no code unless the budget row shows a crossing; one timing-table row.
- A-08: an ordering change — receive until the queue is empty before sleeping; plus a SPEC/comment sentence (the drop
  itself cannot be counted from Python).
- A-09: no code; one SPEC sentence.
- A-10: two `machine.mem32` reads in `begin_boot()` stored with the decoded code (a seed of existing information, not a
  new mechanism); SCRATCH4 only if read before `WDT()`.
- A-11: a bound instead of a fire — store the unpause deadline (`ticks_add`) and test it on a tick that already runs
  (uptime flag or supervisor pass); this removes the one-shot rather than adding a timer.
- A-12: a different return value (or letting `MemoryError` propagate per the CLAUDE.md memory rule) so the caller can
  log `str(e)`.
- A-14: one record write (an existing primitive, `write_reset_record()`) in the boot entry's exit path.
