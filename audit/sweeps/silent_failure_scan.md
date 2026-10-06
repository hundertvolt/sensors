# Silent-failure scan (OR147)

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

## Procedure and output

- Every finding: `file:line`, class, the failure, what the layer below does (cited at the pinned tag or datasheet),
  what our code does, and the effect per device and bus.
- Then check it against the work order: already covered by a merged change (name it), covered partly (name the gap),
  or not covered.
- Not covered or partly covered: fixed in the current unit when a step there owns the site; otherwise parked in
  `audit/REGISTER.md` as an A-C delta for the unit that owns the site, with the conservative fix (detect, count, fail
  visibly, recover) as the proposal. Nothing is dropped as "unlikely".
- The unit's record states the scan ran, over which files and classes, and its result (including "none found").
