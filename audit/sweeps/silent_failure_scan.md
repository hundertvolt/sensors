# Silent-failure scan (OR147, OR148)

Run after every unit's implementation, before its close, and once project-wide at the start of phase B. Prompted by
the UART case (OR146): `machine.UART` ignores the hardware overrun bit, so lost bytes reached the protocol undetected
unless the CRC happened to catch them. The scan looks for every such place, not only in the UART.

## Scope

- After a unit: every file the unit changed, then, for each class a finding belongs to, every other site of that class
  in `src/`, the generated device modules (`build/generated_src/`), `digital_twin/`, `js/`, and the host tooling the
  unit touched. A class found once is swept project-wide, never only where it was noticed.
- Each `machine.*`, `rp2.*`, `network`, `socket`, `asyncio`, `os`/littlefs or Microdot call the code relies on is read
  in the pinned source (MicroPython `v1.29.0` under `$PICO_TOOLCHAIN_DIR/micropython`, `ext/microdot.py`), not judged
  from its documentation alone: what does the layer below do on the failure, and does our code see it?

## The classes

1. **Ignored status from the layer below**: an error flag, status register, return code or exception the port or
   library sets or raises and then discards (`UARTRSR` OE; I2C NACK/abort reasons; SPI and DMA error bits; sensor
   status words and data-ready bits; CRC bytes a chip sends; `WDT`/reset cause; flash/littlefs results; socket and
   lwIP errors; `cyw43` link status). Our code must read it where it exists, or record why it cannot.
2. **Bounded storage that drops or overwrites silently**: ring buffers, FIFOs, queues, log histories, socket backlogs,
   request/response size caps, FRAM chunks, JS buffers. An overflow must be detected, counted and turned into a
   failure the caller (and, across a link, the peer) sees.
3. **Detection left to chance**: a check that catches a fault only probabilistically (CRC alone, a timeout alone,
   framing alone) where an explicit detector exists (a counter, a flag, a length, a sequence number).
4. **Swallowed failures**: an `except` (or JS `catch`) that neither returns a failure, nor logs and counts, nor lets
   the supervisor see it; a sentinel the caller does not test; a failure that looks like valid data (`0`, `""`, `[]`,
   `None` conflated with a real value).
5. **Windows where time or data is lost**: interrupts-off and loop-holding stretches (flash writes, GC, long blocking
   calls), soft-`Timer` callback drops, `ticks_ms()`/counter wraps, reloads, and what each loses or misreads.
6. **Faults without self-healing**: a detected fault with no recovery path, a recovery that cannot be observed (no
   log, counter or status), or a recovery that can loop without bound.
7. **Asymmetric reporting**: a fault one side of an interface detects but the other side (the peer, the REST client,
   the website, the supervisor) never learns of.

## Operating modes (OR148)

Every class is checked in each mode below and at each transition into and out of it, not only in plain operation. A
mode entered rarely is exactly where a fault hides, so each one is read as a scenario: what runs, what is suspended,
what can be lost, who would notice, and how the device returns to normal.

- **Boot**: the one-time `setup()` batches and their watchdog feeding, a driver absent or failing at setup, the UART
  boot drain, reset-cause reading, FRAM logs not yet loaded, the first reading before a sensor's warm-up.
- **Reset countdown**: `system_service`'s `_RESET_DELAY` window and its `Timer`, a failed arm and the stop-feed path,
  requests, PUTs and FRAM or flash writes arriving or in flight during it, reboot to bootloader, `ResetErrors`.
- **Flash writes**: config persistence through littlefs (XIP stall, interrupts off: what UART, DMA, soft `Timer`,
  cyw43 and lwIP lose in that window), a write cut by a reset or the watchdog and what the next boot does with the
  file, a full filesystem.
- **FRAM writes**: a chunk write cut part-way, a failed write, the allocator at its end.
- **Network**: STA connect and reconnect, link loss, the hotspot and captive-DNS mode, NTP before the first sync and
  the time step when it lands, `ticks_ms()` and multi-day rollover.
- **Sensor modes**: warm-up, calibration runs (ISL29125, SCD30 forced and automatic), recovery and re-initialisation
  after a fault, a sensor that returns after being absent.
- **Supervision**: a task restart, the task-failure ceiling and its reboot, the watchdog near expiry, the heap near
  full.
- **Runtime reconfiguration**: a PUT changing configuration while a read, write or calibration is in progress.
- **UART link**: idle, peer reset mid-frame, both `dev` instances active at once.
- **Load and shutdown**: REST hammering and bus contention; the twin's SIGINT shutdown.

A finding records its mode next to its class. A mode with no finding is still named in the unit's record as checked.

## Procedure and output

- Every finding: `file:line`, class, the failure, what the layer below does (cited at the pinned tag or datasheet),
  what our code does, and the effect per device and bus.
- Then check it against the work order: already covered by a merged change (name it), covered partly (name the gap),
  or not covered.
- Not covered or partly covered: fixed in the current unit when a step there owns the site; otherwise parked in
  `audit/REGISTER.md` as an A-C delta for the unit that owns the site, with the conservative fix (detect, count, fail
  visibly, recover) as the proposal. Nothing is dropped as "unlikely".
- The unit's record states the scan ran, over which files, classes and modes, and its result (including "none found").
