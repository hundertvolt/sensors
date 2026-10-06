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

The list is a floor, not a ceiling. Each unit re-derives the modes its changes take part in from five sources and adds
what is missing here: (1) every state variable, flag or counter in the changed code that alters behaviour; (2) every
REST command and config field that starts, stops or reconfigures something; (3) every reset and power path of the
RP2040 (datasheet 2.12-2.13: power-on, brown-out, RUN pin, debug port, watchdog, software reset; `CHIP_RESET` bits)
and of each peripheral chip, from its datasheet; (4) the device lifecycle, from first boot to months of uptime; (5) the
environment (network, host, USB). Then (6) the pairs: two rare modes at once (a countdown during a flash write, a
reconnect during calibration, a PUT before setup has finished).

**Lifecycle and power**
- **First boot and factory state**: empty filesystem, no config file, blank FRAM, FRAM absent (optional hardware).
- **After a firmware change**: a config file or FRAM layout written by an older firmware (unknown, removed or
  re-typed keys), the frozen website against a browser still caching the old one, reboot to bootloader.
- **Boot**: the one-time `setup()` batches and their watchdog feeding, a driver absent or failing at setup, the UART
  boot drain, the reset cause, FRAM logs not yet loaded, the first reading before warm-up, the API reachable before
  every driver is set up.
- **Each kind of restart**: power-on, brown-out, watchdog, `machine.reset()`, RUN pin, and a soft reset (REPL `Ctrl-D`,
  `mpremote`), which restarts the interpreter but not every peripheral: a running DMA channel, PIO state machine,
  UART or timer from the previous run can still be active.
- **Power loss at any instruction**: mid flash write, mid FRAM chunk, mid SCD30 NVM write, mid UART frame.
- **Boot loop**: a fault that recurs at every boot; what each pass writes, what survives to diagnose it (within the
  bound in SPECIFICATION.md Part C.7.3).
- **Reset countdown**: `system_service`'s `_RESET_DELAY` window and its `Timer`, a failed arm and the stop-feed path,
  requests, PUTs and FRAM or flash writes arriving or in flight during it, `ResetErrors`.
- **Long uptime**: `ticks_ms()` wrap, counters at their `max_val`, error logs full, heap fragmentation over weeks,
  sensor drift and self-calibration over months, multi-day rollover.

**Storage**
- **Flash writes**: config persistence through littlefs (XIP stall, interrupts off: what UART, DMA, soft `Timer`,
  cyw43 and lwIP lose in that window), a write cut by a reset or the watchdog and what the next boot does with the
  file, a full filesystem.
- **FRAM writes**: a chunk write cut part-way, a failed write, the allocator at its end, a chip that stops answering.

**Network and time**
- **WiFi**: STA connect and reconnect, link loss, the `isconnected()` false positive, DHCP renewal and an IP change,
  router restart, the hotspot and captive-DNS mode.
- **Time**: the RTC at its reset epoch before the first NTP sync, NTP never reachable, the time step when sync lands
  (including backwards), DNS failure.
- **REST clients**: hammering, several clients at once (two browsers editing the same value), a slow or half-open
  client, malformed and oversized requests, socket exhaustion, a page left open while the device reboots.

**Peripherals**
- **Sensor modes**: warm-up, measurement-interval and range changes, calibration runs (ISL29125, SCD30 forced and
  automatic), recovery and re-initialisation after a fault, a sensor absent for good, one that returns.
- **A peripheral that resets on its own** (supply glitch): it comes back with defaults while we assume our settings.
- **Buses**: a wedged I2C bus, contention between devices, the general-call hazard.
- **UART link**: idle, peer reset mid-frame, both `dev` instances active at once.
- **Outputs**: NeoPixel and notification states across a reboot or fault.

**Supervision and resources**
- **Degraded running**: the device running for long periods with a sensor, FRAM, WiFi or NTP missing.
- **Supervision**: a task restart, the task-failure ceiling and its reboot, the watchdog near expiry, the heap near
  full.
- **Runtime reconfiguration**: a PUT changing configuration while a read, write or calibration is in progress.

**Host side**
- **Console**: USB attached with no reader (does logging output stall the loop?), `Ctrl-C` on the REPL raising
  `KeyboardInterrupt` inside a running task.
- **Twin and tooling**: the twin's SIGINT shutdown, a build or generator killed mid-way leaving partial outputs, a
  re-run over a dirty tree, an offline run.

A finding records its mode next to its class. A mode with no finding is still named in the unit's record as checked.
Sleep modes (`lightsleep`/`deepsleep`) are not used by `src/` today (grep, 2026-10-06); a change that adds one adds
the mode.

## Procedure and output

- Every finding: `file:line`, class, the failure, what the layer below does (cited at the pinned tag or datasheet),
  what our code does, and the effect per device and bus.
- Then check it against the work order: already covered by a merged change (name it), covered partly (name the gap),
  or not covered.
- Not covered or partly covered: fixed in the current unit when a step there owns the site; otherwise parked in
  `audit/REGISTER.md` as an A-C delta for the unit that owns the site, with the conservative fix (detect, count, fail
  visibly, recover) as the proposal. Nothing is dropped as "unlikely".
- The unit's record states the scan ran, over which files, classes and modes, and its result (including "none found").
