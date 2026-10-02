# Harvest — BUS: Bus layer

What the project's own comments, docs and history already record for this area (snapshot `2a88cc8`, moved to `4dc80ef` by V11).
Recorded, not verified or triaged; `audit/HARVEST.md` explains the kinds, tags and method.

Kinds: SETTLED 15, INVAR 43, MIRROR 2, LIMIT 26, RISK 4, ASSUME 16, PLATFORM 14, SUPPRESS 11, TODO 3, OPENQ 1, DRIFT 1, NOTE 5 — 141 items.


## src/asy_i2c_driver.py

- **BUS.N001** DRIFT · `src/asy_i2c_driver.py:1-2` — "used by every I2C sensor driver
  (asy_scd30_driver.py, asy_sgp40_driver.py, asy_bmp3xx_driver.py)" — Omits `asy_isl29125_driver.py`,
  which also imports `I2CDevice` (`src/asy_isl29125_driver.py:19`) (low). · [H01]
- **BUS.N002** INVAR · `src/asy_i2c_driver.py:4-6` — "A method returns None only for a non-hardware
  failure ...; a real OSError always propagates to the caller. One-time setup ... is exempt and may
  raise." — Module-wide raise/sentinel contract; by convention. · covered-by: BUS.T01 · [H01]
- **BUS.N003** ASSUME · `src/asy_i2c_driver.py:17-19` — "Covers every read the drivers actually make
  (BMP3XX's 21-byte calibration block is the largest ...)" — 32-byte scratch sized from a survey of
  current drivers; oversize falls back to allocation (silent churn if a new driver reads more). ·
  related: BUS.T02, MEM.T04 · [H01]
- **BUS.N004** INVAR · `src/asy_i2c_driver.py:33-36` — "Sharing it across this bus's devices is sound
  only because every method fills and decodes it with no await between, and no Timer/Pin.irq callback
  here touches I2C - both checked (Part G.2)." — Shared-scratch soundness rests on two conventions;
  "checked" by review, no mechanical guard named. · covered-by: BUS.T02 · [H01]
- **BUS.N005** INVAR · `src/asy_i2c_driver.py:59-61` — "valid only until the next read on this bus, so a
  caller that keeps the value must copy it out" — Returned memoryview aliasing contract; caller
  discipline. · covered-by: BUS.T02 · [H01]
- **BUS.N006** SUPPRESS · `src/asy_i2c_driver.py:103-106, 108-111` — "except ValueError: # malformed
  reg_format" → return None — Malformed format swallowed to None sentinel. · related: BUS.T01 · [H01]
- **BUS.N007** SUPPRESS · `src/asy_i2c_driver.py:155-160` — "except (ValueError, TypeError): return" — A
  bad value/format (and an uninitialised bus) makes `set_register_struct` a silent no-op with `None`
  return — callers cannot tell a write was skipped. · related: BUS.S01, BUS.T06 · [H01]
- **BUS.N008** PLATFORM · `src/asy_i2c_driver.py:189` — "machine.I2C.scan(): every ACKing address in
  0x08-0x77." — Scan range fact; `scan()` has no production caller (low). · related: BUS.T08 · [H01]
- **BUS.N009** LIMIT · `src/asy_i2c_driver.py:204-205, 222-223` — "if self._i2c is None: return"
  (readfrom_into/writeto) — Uninitialised bus: reads are silent no-ops leaving the caller's buffer
  stale. · covered-by: BUS.S01 · [H01]
- **BUS.N010** ASSUME · `src/asy_i2c_driver.py:219-228` — "str input assumes Latin-1 (single byte per
  char); a codepoint above 255 raises ValueError, caught below" — Swallowed to None (SUPPRESS) (low). ·
  [H01]
- **BUS.N011** LIMIT · `src/asy_i2c_driver.py:246-250` — "Not a native machine.I2C primitive - a write
  then a read via this class's own writeto()/readfrom_into()." — Two separate calls; a
  failed/uninitialised write is not detected before the read; unused API (low). · related: BUS.T08 ·
  [H01]
- **BUS.N012** SUPPRESS · `src/asy_i2c_driver.py:261-273` — "except OSError: raise ValueError(...) from
  None" / "await asyncio.sleep(0.1)" ×2 — Probe converts any OSError into "no device" and sleeps 2×100
  ms around it (under the bus lock when called from setup). · covered-by: BUS.S02 · [H01]

## src/asy_spi_driver.py

- **BUS.N013** INVAR · `src/asy_spi_driver.py:2` — "Sole consumer: asy_fram_driver.py's FRAM_SPI." —
  Async transfers are kept for a hypothetical future driver (:200-201). · covered-by: BUS.T08 · [H01]
- **BUS.N014** PLATFORM · `src/asy_spi_driver.py:17-20` — "Both parts specify tCSU/tCSH >= 10 ns and tD
  >= 40 ns (MB85RS2MTA) / 60 ns (MB85RS64V) ... rp2's sleep_us() busy-waits on time_us_64(), where
  sleep_us(1) only promises an elapsed time in (0, 1] us" — CS settle constant from both FRAM datasheets
  and rp2 sleep_us semantics; blocking. · related: BUS.T04, STOR.T11 · [H01]
- **BUS.N015** ASSUME · `src/asy_spi_driver.py:55, 109` — "baudrate: int = 1000000" — 1 MHz mode-0
  default is what FRAM runs at (no baudrate from codegen). · covered-by: STOR.T11 · [H01]
- **BUS.N016** INVAR · `src/asy_spi_driver.py:61-67` — "Programmer-error guards: only ever called from
  SPIDevice.__aenter__, on an initialized, lock-held bus." — Guard checks the bus lock is held by
  someone; comment is stale — `session_begin()` (used by FRAM's sync path) is the real caller;
  `machine.SPI.init()` runs on every CS assertion. · covered-by: BUS.S03 · [H01]
- **BUS.N017** LIMIT · `src/asy_spi_driver.py:70-71, 78-79, 91-92` — "if self._spi is None: return" —
  Uninitialised bus: silent no-ops (reads leave buffers stale). · related: BUS.T06 · [H01]
- **BUS.N018** SUPPRESS · `src/asy_spi_driver.py:93-96` — "except ValueError: # length mismatch" →
  return None — Success and swallowed failure indistinguishable. · covered-by: BUS.S04 · [H01]
- **BUS.N019** LIMIT · `src/asy_spi_driver.py:117, 124, 181-184` — "self.cs_pin = Pin(cs_pin)" / "cs_pin
  isn't configured as an output until setup() runs" — CS pad state undefined until setup(). ·
  covered-by: BUS.S08 · [H01]
- **BUS.N020** INVAR · `src/asy_spi_driver.py:126-129, 146-148` — "for a caller that already holds the
  bus lock - configure()'s own guard enforces that" / "The caller's own try/finally is what guarantees
  this runs" — session_end relies on caller try/finally (FRAM driver does). · related: STOR.T04 · [H01]
- **BUS.N021** RISK · `src/asy_spi_driver.py:128-129, 141, 150` — "The settle blocks on purpose: an
  awaited one would hand the loop to another task with CS asserted and the bus locked." — Deliberate
  blocking sleep_us(2) twice per CS cycle. · covered-by: BUS.T04 · [H01]
- **BUS.N022** INVAR · `src/asy_spi_driver.py:173-178` — "the yield afterwards is this path's one
  scheduling point, placed after the release so a burst of sessions cannot starve the loop" — Yield
  placement convention. · related: PERF.T08 · [H01]

## src/asy_uart_driver.py

- **BUS.N023** PLATFORM · `src/asy_uart_driver.py:4-5` — "GPIO24/25 (UART1) and GPIO28/29 (UART0) are
  valid pin-mux pairs, but the Pico W datasheet (p.8) hands GPIO23/24/25/29 to the wireless chip" —
  Board/datasheet pin fact a wiring choice must respect (dev uses GPIO0/1, 8/9) · related: BUS.T11 ·
  [H02]
- **BUS.N024** SUPPRESS · `src/asy_uart_driver.py:22` — "except ImportError: # typing has no runtime
  presence on MicroPython" — Swallowed ImportError for `typing` · [H02]
- **BUS.N025** ASSUME · `src/asy_uart_driver.py:30-33` — "A healthy holder acknowledges within one poll
  round; only a genuinely wedged one reaches this bound" — `_CANCEL_ACK_TIMEOUT_MS = 1000` assumes every
  poll round (incl. `poll_idle_ms`, dev: 50) is well under 1 s; a slower idle rate would count healthy
  holders as unacknowledged · related: BUS.T05 · [H02]
- **BUS.N026** ASSUME · `src/asy_uart_driver.py:35-38` — "yielding per byte would cost a task switch
  every ~87us of wire time at 115200 baud; 16 bounds the loop's hold at ~1.4ms instead" — Yield
  granularity derived for 115200 baud; the skip/delimiter branches do not count toward it · covered-by:
  BUS.S05 · [H02]
- **BUS.N027** INVAR · `src/asy_uart_driver.py:65-68` — "it bounds how late a frame's first byte is
  noticed, so it belongs well under the peer's reply timeout" — `poll_idle_ms` vs peer timeout; enforced
  on this side by `UART_Comm._min_timeout()` only · related: UART.T05 · [H02]
- **BUS.N028** INVAR · `src/asy_uart_driver.py:90-92, 96-98` — "Acknowledging here, not only inside
  ready()'s loop, is what makes cancel_read_timeout() terminating" — Cancel protocol's termination rests
  on every holder leaving via `__aexit__` · related: BUS.T05 · [H02]
- **BUS.N029** SETTLED · `src/asy_uart_driver.py:110-112` — "Kept deliberately, unlike
  SPIDevice/I2CDevice: cancel_read_timeout() infers \"a read is in flight\" purely from
  asy_lock.locked()" — Deliberate I2C/SPI/UART asymmetry; a lock-less caller silently gets `None` ·
  related: BUS.T07 · [H02]
- **BUS.N030** SUPPRESS · `src/asy_uart_driver.py:124-125` — "except (OSError, MemoryError): #
  never-raises contract - see the module docstring" — `any()` failure silently reads as "0 bytes
  buffered" · [H02]
- **BUS.N031** PLATFORM · `src/asy_uart_driver.py:128` — "rp2 uart.write() can short-write instead of
  raising, so retry with what is left" — rp2 write semantics; the retry waits on `ready(POLLOUT)` with
  no deadline at the idle rate · covered-by: BUS.S05 · [H02]
- **BUS.N032** LIMIT · `src/asy_uart_driver.py:171-176` — "if self._skip_to_delimiter: # the fragment a
  resync landed in the middle of" — Skip and empty-frame branches consume bytes without counting toward
  the 16-byte yield · covered-by: BUS.S05 · [H02]
- **BUS.N033** LIMIT · `src/asy_uart_driver.py:202-204` — "machine.UART exposes neither back... (a frame
  that does not fit rxbuf loses its tail silently)" — Driver keeps its own copies of rxbuf/baudrate; RX
  overflow is silent · related: BUS.T12 · [H02]
- **BUS.N034** SUPPRESS · `src/asy_uart_driver.py:234-235` — "except (OSError, MemoryError): ok = False"
  — Failed unregister reported only via return value; this class has no logger, "the caller logs"
  (:226-227) · related: BUS.T01 · [H02]
- **BUS.N035** INVAR · `src/asy_uart_driver.py:243-244` — "True means a cancel is outstanding, so it
  must not [take the lock and drain]." — Caller discipline on `cancel_read_timeout()`'s result · [H02]
- **BUS.N036** RISK · `src/asy_uart_driver.py:253` — "self.cancel_unacknowledged += 1 # a wedged holder;
  the request stays latched" — A latched, unacknowledged cancel aborts the next unrelated read ·
  related: UART.T09 · [H02]
- **BUS.N037** SUPPRESS · `src/asy_uart_driver.py:271` — "return False # type: ignore[unreachable] #
  mypy can't see the mutation" — mypy suppression in shipped code (concurrent `deinit()` guard) · [H02]
- **BUS.N038** SUPPRESS · `src/asy_uart_driver.py:287-290` — "except (OSError, MemoryError, TypeError):
  # TypeError: a malformed mask/timeout_ms" — Poll errors, MemoryError and caller type errors all
  collapse to "not ready" · related: BUS.T01 · [H02]
- **BUS.N039** INVAR · `src/asy_uart_driver.py:291-294` — "The one yield every read loop relies on:
  ipoll() reports the mask with no await of its own" — CLAUDE.md never-block hard rule's single
  enforcement point (F.5.8) · covered-by: BUS.T05 · [H02]
- **BUS.N040** LIMIT · `src/asy_uart_driver.py:353-354` — "want = self._buffered(uart, len(buf) if
  nbytes is None else nbytes)" — `nbytes > len(buf)` relies on `machine.UART.readinto` clamping ·
  covered-by: BUS.S05 · [H02]
- **BUS.N041** INVAR · `src/asy_uart_driver.py:366-367` — "return None # the caller's buffer must hold
  the worst-case encoded frame" — Caller-sized buffer contract for delimited codecs · [H02]
- **BUS.N042** LIMIT · `src/asy_uart_driver.py:395, 410` — "add = uart.readline() # reads until b\"\\n\"
  or the buffer runs empty" — readline paths skip the `any()` clamp; no production caller · covered-by:
  BUS.S06 · [H02]
- **BUS.N043** INVAR · `src/asy_uart_driver.py:442-443` — "buf belongs to this call for its duration -
  the caller must not mutate it until the call returns." — Caller discipline, not enforced · [H02]

## tests/_bus_hazard_catalog.py

- **BUS.N044** SETTLED · `tests/_bus_hazard_catalog.py:507` — "A real general-call broadcast
  (SPECIFICATION.md Part C.8's known structural gap)" — general-call hazard is a documented, accepted
  structural gap; the scenario only tests it against siblings · related: TWIN.S02, HW.T09 · [H03]

## tests/_uart_link_contract.py

- **BUS.N045** LIMIT · `tests/_uart_link_contract.py:211-213` — "readline() carries no count to clamp,
  so the driver gates it on one buffered byte" — a fake counting only counted reads would let that gate
  regress (Part E.8 sweep) · related: BUS.S06 · [H03]

## tests/machine.py

- **BUS.N046** ASSUME · `tests/machine.py:210,275-277` — "SPI has no ACK/NAK, so write() cannot raise
  ... the real write-only path has no failure mode to model" — the fake's SPI `write()` is never
  injectable · [H03]

## tests/test_asy_bmp3xx_driver.py

- **BUS.N047** INVAR · `tests/test_asy_bmp3xx_driver.py:669-671,685-687` — "get_bits()/set_bits() never
  yield between" — the shared-OSR read-modify-write race fix depends on the I2C layer never yielding
  inside get_bits/set_bits · related: BUS.T02 · [H03]
- **BUS.N048** SETTLED · `tests/test_asy_bmp3xx_driver.py:819-827` — "set_bits() returns None
  unconditionally, so a write-shaped call can silently no-op. Not a bug in this driver: it is the lower
  layer's deliberate \"non-hardware failure\" carve-out" — a write on a deinitialized bus silently does
  nothing, by design · related: BUS.S01, BUS.T06 · [H03]

## tests/test_asy_fram_wire_trace.py

- **BUS.N049** INVAR · `tests/test_asy_fram_wire_trace.py:3-5,107-109` — "Every cycle is asserted to be
  framed by exactly one SPI.init() at the fixed bus config and one CS low/high pair" — the goldens pin
  one `machine.SPI.init()` per CS cycle, so changing BUS.S03's per-CS init cost breaks this test by
  design · related: BUS.S03, BUS.T04 · [H03]

## tests/test_asy_i2c_driver.py

- **BUS.N050** LIMIT · `tests/test_asy_i2c_driver.py:76-96,572-586` — "no-op, must not raise" — on a
  deinitialized bus every I2C/I2CDevice op silently does nothing (pinned behaviour), including
  mid-session · covered-by: BUS.S01 · [H03]
- **BUS.N051** LIMIT · `tests/test_asy_i2c_driver.py:242-248` — "the unpack()-specific except, and the
  \"unpacked value is not int/float/bytes\" fallback below it, are unreachable through any real
  malformed format string" — defensive branches proven only by faking `struct` · [H03]
- **BUS.N052** LIMIT · `tests/test_asy_i2c_driver.py:480-482` — "the two are genuinely separate bus
  transactions at this layer, not one atomic operation with rollback" — write-then-read is not atomic ·
  [H03]
- **BUS.N053** LIMIT · `tests/test_asy_i2c_driver.py:495-496` — "Both real failure modes (EIO/ETIMEDOUT)
  collapse to the same \"no device\" message today - documents existing behavior" — probe cannot
  distinguish a stuck bus from a missing device (pins current behaviour) · related: BUS.S02 · [H03]
- **BUS.N054** INVAR · `tests/test_asy_i2c_driver.py:662-664` — "locking is the caller's job, not
  something write()/readinto() provide" — every caller must wrap I2CDevice ops in `async with device:`
  (convention) · related: BUS.T02 · [H03]
- **BUS.N055** INVAR · `tests/test_asy_i2c_driver.py:831-833` — "Not reentrant by design, being a plain
  asyncio.Lock: nesting `async with device:` on one device within one task deadlocks" — nested session
  use is forbidden by convention only · [H03]
- **BUS.N056** SETTLED · `tests/test_asy_i2c_driver.py:914-916` — "This driver deliberately doesn't
  range-check `address` itself (SPECIFICATION.md Part D.2's \"don't defend against out-of-contract
  input\"" — address validity left to machine.I2C · [H03]
- **BUS.N057** INVAR · `tests/test_asy_i2c_driver.py:1050-1051` — "a returned value that still pointed
  into it would silently change under its owner at the next read on any of them" — values returned from
  the shared per-bus scratch must never alias it · covered-by: BUS.T02 · [H03]

## tests/test_asy_spi_driver.py

- **BUS.N058** LIMIT · `tests/test_asy_spi_driver.py:77,92-108` — "the wrapper's own `is not None`
  guard, not anything the hardware enforces" — after deinit, SPI write/readinto/write_readinto are
  silent no-ops (no error), pinned by tests · related: BUS.T06 · [H04]
- **BUS.N059** LIMIT · `tests/test_asy_spi_driver.py:166-172` — "a disconnected MISO or clock wire is
  invisible at this layer on real hardware" — SPI has no ACK, so a disconnected device is undetectable;
  the test pins the fake's zero-filled read, which is the fake's model, not a measured hardware value ·
  [H04]
- **BUS.N060** SUPPRESS · `tests/test_asy_spi_driver.py:386-389` — "__aexit__ must still deassert CS and
  swallow the resulting double-release RuntimeError" — src `SPIDevice.__aexit__` swallows a RuntimeError
  from releasing an already-released lock · [H04]
- **BUS.N061** SETTLED · `tests/test_asy_spi_driver.py:467-472` — "Without __aenter__'s own try/except
  the lock would leak permanently" — `__aenter__` must release the lock itself when configure() raises,
  since `async with` never calls `__aexit__` then · [H04]
- **BUS.N062** INVAR · `tests/test_asy_spi_driver.py:498-500,1084-1091` — "no pass inside the CS window
  (the hazard), one pass per session (the burst's fairness)" — the settle inside the CS window is
  blocking (no await), so no other task runs while CS is asserted; fairness relies on `__aexit__`'s
  trailing sleep(0) (:1120-1122) · related: BUS.T04 · [H04]
- **BUS.N063** SETTLED · `tests/test_asy_spi_driver.py:708-710` — "Deliberately NOT swallowed: a
  transfer that overran left garbage in the buffer" — SPI RX overrun OSError propagates, matching the
  I2C "real OSError always propagates" contract · related: BUS.T01 · [H04]
- **BUS.N064** INVAR · `tests/test_asy_spi_driver.py:841-843,867-868` — "The caller holds the bus lock -
  configure()'s own guard enforces that contract." — synchronous `session_begin`/`session_end` never
  take the lock; the caller-holds-lock contract is enforced by configure()'s programmer-error guard ·
  [H04]
- **BUS.N065** INVAR · `tests/test_asy_spi_driver.py:1056-1057` — "the deassert obligation is the
  caller's try/finally - which is exactly the shape asy_fram_driver.py's block operations use" —
  synchronous SPI sessions rely on each caller deasserting CS in its own finally (caller discipline) ·
  related: STOR.T11 (low) · [H04]

## tests/test_asy_uart_driver.py

- **BUS.N066** LIMIT · `tests/test_asy_uart_driver.py:91-93` — "Real mp_machine_uart_init_helper() has
  no raising validation at all for bits/parity/stop" — neither rp2 nor asy_uart_driver.py validates
  bits/parity/stop; bad values pass silently · - (low) · [H04]
- **BUS.N067** LIMIT · `tests/test_asy_uart_driver.py:101-103` — "Real hardware silently ignores a
  non-positive baudrate ... it makes no claim the fake models the silent-ignore behavior itself" —
  baudrate ≤ 0 is accepted silently on rp2; the fake does not model the keep-previous-value behaviour ·
  related: TEST.T19 · [H04]
- **BUS.N068** LIMIT · `tests/test_asy_uart_driver.py:248-250` — "a failing re-init cannot roll back to
  the previous working bus - the instance is left deinitialized" — re-init failure leaves UART (and
  I2C/SPI) deinitialized until a valid re-init · related: BUS.T06 · [H04]
- **BUS.N069** SETTLED · `tests/test_asy_uart_driver.py:288-290` — "a failed unregister() must be
  reported via the return value, not just silently swallowed" — deinit() reports poller-unregister
  failure via return value (same pattern as asy_udp_socket.disconnect()) · - (low) · [H04]
- **BUS.N070** INVAR · `tests/test_asy_uart_driver.py:375-377` — "Fixed to re-check every iteration,
  matching asy_udp_socket.py's ready()" — ready() must re-check `_uart`/`poller` for None every loop
  iteration (concurrent deinit) · [H04]
- **BUS.N071** SUPPRESS · `tests/test_asy_uart_driver.py:394-396` — "ready() must catch it itself and
  degrade to False rather than propagating" — ready() swallows a TypeError from a non-int poll mask · -
  (low) · [H04]
- **BUS.N072** LIMIT · `tests/test_asy_uart_driver.py:1132-1134` — "write() calls ready() with no
  timeout_ms (waits forever), so cancellation is the only way it ever returns False" — UART writes wait
  for POLLOUT with no deadline · covered-by: BUS.S05 · [H04]
- **BUS.N073** SETTLED · `tests/test_asy_uart_driver.py:1362-1363` — "Not reentrant by design (a plain
  asyncio.Lock, same as I2CDevice/SPIDevice's shared bus lock)" — bus locks are non-reentrant
  asyncio.Locks · related: XCUT.T06 · [H04]
- **BUS.N074** LIMIT · `tests/test_asy_uart_driver.py:1419-1421` — "this path is unreachable through any
  real CRC object" — write()'s CRC add()-returns-None branch is dead defensive code, reached only via a
  fake · - (low) · [H04]
- **BUS.N075** INVAR · `tests/test_asy_uart_driver.py:1559-1561,1583-1584` — "Every read loop reaches
  the peripheral through ready(), so \"ready() always yields\" bounds how long any of them holds the
  loop" — the never-block guarantee lives in ready()'s yield plus the any() clamp; deadline vs
  no-deadline waits use two poll rates (F.5.9) · related: BUS.T05 · [H04]
- **BUS.N076** INVAR · `tests/test_asy_uart_driver.py:1669-1670,1834-1836,1862` — "_read_delimited()
  consumes one buffered byte per round without ever reaching ready()'s own yield" — delimited reads
  yield every 16 bytes via an explicit counter, proven by a competing-task count · related: BUS.S05 ·
  [H04]
- **BUS.N077** INVAR · `tests/test_asy_uart_driver.py:1873-1874` — "readline() has no count to clamp, so
  its only bound is ready()'s deadline" — readline's only termination is the caller's deadline ·
  related: BUS.S06 · [H04]

## tests/test_bus_hazard_multi_device.py

- **BUS.N078** INVAR · `tests/test_bus_hazard_multi_device.py:68-70` — "every real device address this
  codebase uses must fall outside both, and only SGP40's own documented _reset() may ever address 0x00"
  — Reserved-address rule for all devices; the check runs on constants in the test file itself ·
  covered-by: TEST.S05 · [H05]
- **BUS.N079** INVAR · `tests/test_bus_hazard_multi_device.py:420-421` — "take the bus lock, run the
  whole CS cycle synchronously, release, then yield - never yielding with CS asserted" — Convention
  asy_fram_driver.py's command bodies must follow · [H05]
- **BUS.N080** ASSUME · `tests/test_bus_hazard_multi_device.py:350-352` — "I2CDevice's session lock is
  the shared bus lock, so this proves the same mechanism" — Per-device session serialization is the bus
  lock itself (low) · [H05]

## dev_legacy/*.py (reference-only 2026-08-27 on-device snapshot, MicroPython 1.24.1 — plan §2.2; field/bench behaviour only)

- **BUS.N081** ASSUME · `dev_legacy/asy_i2c_driver.py:253-257` — "if you get an OSError it means the
  device is not there or that the device does not support these means of probing" — Probe semantics
  conflate absence with unsupported probing. · related: HW.S12 (low) · [H08]

## devices/dev.toml

- **BUS.N082** PLATFORM · `devices/dev.toml:26-31` — "SCD30 clock-stretch headroom (datasheet: up to
  150ms/day, past rp2's 50ms default)." — `timeout = 200000` on the SCD30 bus rests on a datasheet
  figure and the rp2 default I2C timeout. · related: GEN.T08 · [H09]

## devices/wozi.toml

- **BUS.N083** PLATFORM · `devices/wozi.toml:21-26` — "SCD30 clock-stretch headroom (datasheet: up to
  150ms/day, past rp2's 50ms default)." — Same datasheet-derived timeout. · related: GEN.T08 · [H09]

## SPECIFICATION.md Part A.7 (wozi's construction order and dependency graph, 358-569)

- **BUS.N084** PLATFORM · `SPECIFICATION.md:382-385` — "`i2c0` ... sets `timeout=200000` (200ms): SCD30
  documents up to 150ms clock stretching/day, past rp2's 50ms default" — Datasheet + rp2 default fact;
  per-bus singleton reconfig risk. · related: HW.S18 · [H12]

## SPECIFICATION.md Part C.3 (Layer 2 protocol class, 1537-1566)

- **BUS.N085** PLATFORM · `SPECIFICATION.md:1556-1560` — "`asy_spi_driver.py`'s `write()` cannot raise
  at all on rp2 ... `readinto()`/`write_readinto()` can raise `OSError(EIO)` on a 32+ byte RX overrun
  since MicroPython 1.29" — rp2 1.29-specific raise surface. · related: PLAT.T03 · [H12]
- **BUS.N086** LIMIT · `SPECIFICATION.md:1559-1560` — "`write_readinto()` additionally turns a
  caller-input `ValueError` into `None`." — Success and swallowed error both return None. · covered-by:
  BUS.S04 · [H12]
- **BUS.N087** INVAR · `SPECIFICATION.md:1564-1567` — "A multi-transaction sequence that must not be
  interleaved holds the session lock for the whole sequence" — Locking convention. · related: XCUT.T06 ·
  [H12]

## SPECIFICATION.md Part C.3.1 (SPI sensor variant, 1567-1596)

- **BUS.N088** LIMIT · `SPECIFICATION.md:1571-1575` — "SPI sensor variant — best effort, non-proven ...
  Needs extra datasheet/hardware scrutiny the first time used." — Unproven guidance for any SPI sensor.
  · [H12]
- **BUS.N089** PLATFORM · `SPECIFICATION.md:1579-1580` — "No bus-level presence probe exists for SPI,
  unlike I2C's zero-byte-write NAK check." — Identity must be content-checked. · [H12]
- **BUS.N090** INVAR · `SPECIFICATION.md:1586-1593` — "The settle inside the CS window must block
  (`time.sleep_us(2)`) — an awaited one hands the loop to another task with CS asserted and the bus
  locked" — Must-not-await rule inside CS. · related: BUS.T04 · [H12]

## SPECIFICATION.md Part C.3.2 (UART variant, 1598-1622)

- **BUS.N091** PLATFORM · `SPECIFICATION.md:1617-1619` — "raise contract (re-verified against
  `ports/rp2/machine_uart.c` at v1.29.0): a hardware framing/parity/overrun error is never raised ...
  `write()` can short-write" — rp2 UART error semantics. · related: BUS.T05 · [H12]
- **BUS.N092** ASSUME · `SPECIFICATION.md:1619-1625` — "`any()` cannot raise either (re-traced
  2026-09-13 ...) ... `_buffered()`'s `except (OSError, MemoryError)` is therefore defence in depth
  against a future port, not a reachable rp2 case" — Dated trace; catch kept as unreachable defence. ·
  [H12]

## SPECIFICATION.md Part C.7.1 (Running errno/wrnno table, 1893-1941)

- **BUS.N093** ASSUME · `SPECIFICATION.md:1943` — "Deliberately no logging — every failure surfaces to
  exactly one upstream owner. Coverage audit closed, no gaps." — Closed-audit claim for
  i2c/spi/udp/dns-client. · [H12]

## SPECIFICATION.md Part C.12 (Testing, 2355-2361)

- **BUS.N094** PLATFORM · `SPECIFICATION.md:2367-2369` — "real hardware only raises `OSError(EIO)` or
  `OSError(ETIMEDOUT)` — never `ENODEV` (`SoftI2C`-specific)" — rp2 hardware-I2C error set tests must
  model. · related: TEST.T05 · [H12]

## SPECIFICATION.md Part D (src/ Production-Quality Checklist, 2576-2728)

- **BUS.N095** PLATFORM · `SPECIFICATION.md:2620-2622` — "I2C raises broadly; SPI raises only from a 32+
  byte read (F.5.2), never from a write; UART never raises from a transfer at all." — Per-bus raise
  surface on rp2 1.29. · related: BUS.T01 · [H12]

## SPECIFICATION.md Part F.2 — Blocking calls / timeout-wrapping

- **BUS.N096** SETTLED · `SPECIFICATION.md:3601-3603` — "For a genuinely wedged I2C bus/sensor, the
  hardware watchdog is the accepted backstop ... Settled." — Do-not-reopen: no I2C-level timeout
  mechanism. · related: DOC.T14 · [H13]
- **BUS.N097** LIMIT · `SPECIFICATION.md:3612-3618` — "doesn't reconstruct the underlying `machine.I2C`
  peripheral (only a full reboot does that)" — Task respawn recovers a sensor, not a wedged bus; bus
  faults rely on `task_errors` escalating to watchdog starvation. · related: XCUT.T02 · [H13]

## SPECIFICATION.md Part F.5.1 — I2C/SPI deinit no-ops

- **BUS.N098** PLATFORM · `SPECIFICATION.md:3704-3708` — "`machine.I2C.deinit()` did not exist at all
  before 1.29 ... a hard **1.29 floor** on its `deinit()` path" — `asy_i2c_driver.py` raises
  `AttributeError` on 1.28/1.26 via `deinit()`/re-`init()`; refactor code is not 1.26-compatible there.
  · related: PLAT.T03 · [H13]
- **BUS.N099** ASSUME · `SPECIFICATION.md:3717` — "Nothing in `src/` observes bus identity." — The
  singleton divergence is safe only while this holds; the plan records a per-bus singleton reconfigured
  by a later construction (`HW.S18`). · related: BUS.T10 · [H13]

## SPECIFICATION.md Part F.5.2 — rp2 SPI RX-overrun EIO

- **BUS.N100** INVAR · `SPECIFICATION.md:3738-3742` — "It propagates uncaught out of `get_values()`,
  matching `asy_i2c_driver.py`'s \"a real `OSError` always propagates\" contract" — Bus-wrapper
  contract: no swallowing of real OSError at the bus layer. · related: BUS.T01 · [H13]

## SPECIFICATION.md Part F.5.6 — Smaller 1.29 facts / non-events

- **BUS.N101** ASSUME · `SPECIFICATION.md:3842` — "the one `to_bytes` call in `src/` is always
  non-negative" — Single-site claim (src/asy_i2c_driver.py:141). · [H13]

## SPECIFICATION.md Part F.5.8 — UART read() blocks the loop

- **BUS.N102** INVAR · `SPECIFICATION.md:3914-3924` — "`asy_uart_driver.UART._buffered()` is that clamp,
  and **every** read in the module goes through it ... `readline()` has no count to clamp and gates on
  `any()` instead" — Every read must clamp to `any()`; the plan records
  `readline()`/`readline_until_complete()` calling `machine.UART.readline()` without the clamp
  (`BUS.S06`). · related: BUS.S06 · [H13]
- **BUS.N103** INVAR · `SPECIFICATION.md:3925-3935` — "the yield belongs there and nowhere else — `await asyncio.sleep_ms(0)`
  immediately before it returns `True` ... **no path through this driver reaches a read without having
  just yielded.**" — Single-point yield guarantee in `ready()`; `_read_delimited()` is the one loop that
  bypasses it, yielding every `_DELIMITED_YIELD_BYTES` (16). · related: BUS.S05 · [H13]
- **BUS.N104** INVAR · `SPECIFICATION.md:3937-3938` — "A zero-length round additionally falls back to
  `sleep_ms(poll_wait_ms)`, so the retry can never become an unyielding spin" — Guard against
  `any()`/`POLLIN` disagreement. · covered-by: BUS.T05 · [H13]
- **BUS.N105** ASSUME · `SPECIFICATION.md:3979-3985` — "**All seven read paths are guarded, and that was
  established by breaking each one.** ... (2026-09-12) initially failed a named test for only four of
  the seven" — Dated mutation sweep; the plan's BUS.S06 contests two of the seven (readline paths). ·
  related: BUS.S06, TEST.T02 · [H13]
- **BUS.N106** SETTLED · `SPECIFICATION.md:3988-3994` — "**This does not generalise to
  `asy_i2c_driver.py`/`asy_spi_driver.py`, and must not be applied there.**" — Do-not-extend rule;
  I2C/SPI blocking stays under F.2's watchdog backstop. · related: DOC.T14 · [H13]
- **BUS.N107** LIMIT · `SPECIFICATION.md:4003-4007` — "No device TOML wires a second SPI device, so the
  21 ms figure is a contract statement ... **That is structurally untestable rather than merely
  untested**" — SPI contention with FRAM is unobservable in every variant. · related: PERF.T04 · [H13]
- **BUS.N108** ASSUME · `SPECIFICATION.md:4013-4017` — "`mp_machine_uart_write()` short-writes rather
  than waiting once `timeout` (0 here) elapses ... theoretical worst case is the ~1 ms it takes
  `ticks_ms()` to advance" — Write-path bound relies on `timeout=0` wiring and the port's short-write
  behaviour. · covered-by: BUS.T05 · [H13]

## SPECIFICATION.md Part G.2 — Known reusable primitives

- **BUS.N109** INVAR · `SPECIFICATION.md:4218-4221` — "`_scratch` is the one shared by more than one
  caller ... sound only because each method fills and decodes it with no `await` in between" —
  Convention-only safety of the shared I2C scratch. · covered-by: BUS.T02 · [H13]
- **BUS.N110** SETTLED · `SPECIFICATION.md:4227-4230` — "never a new `async with` per transfer. I2C
  deliberately has no equivalent (BACKLOG's deferred list)" — Deliberate I2C/SPI asymmetry, deferred in
  BACKLOG. · covered-by: BUS.T07 · [H13]

## SPECIFICATION.md Part I.2 — Hotspot catalog

- **BUS.N111** RISK · `SPECIFICATION.md:4864-4865` — "`asy_uart_driver.py`'s accumulation loops (wrapped
  in `try/except MemoryError`, bounded or documented-unbounded-and-accepted)" — Accepted unbounded
  accumulation paths in the UART driver. · related: BUS.S06, MEM.T03 · [H13]
- **BUS.N112** INVAR · `SPECIFICATION.md:4878-4881` — "safe only because each of these methods fills and
  decodes it with no `await` in between and no `Timer`/`Pin.irq` callback in this codebase touches I2C —
  both verified against the real code" — Shared-scratch safety invariant (verified 2026-09-18, not
  mechanically guarded). · covered-by: BUS.T02 · [H13]
- **BUS.N113** LIMIT · `SPECIFICATION.md:4881-4886` — "A read larger than the scratch ... falls back to
  the allocating call ... **That fallback is structurally unexercised on this hardware**" — Dead-on-dev
  fallback kept deliberately; "BMP3XX's 21-byte calibration block is the largest" is a dated inventory
  claim. · related: BUS.T08 · [H13]

## SPECIFICATION.md Part J.5 — Timing, flow control, recovery

- **BUS.N114** INVAR · `SPECIFICATION.md:5475-5482` — "`asy_uart_driver.py` keeps
  `cancel_read_timeout()` and infers \"a read is in flight\" from the lock rather than a flag ...
  **latched and bounded** ... (changelog B15)" — Cancel-handshake contract. · covered-by: BUS.T05 ·
  [H13]

## CLAUDE.md

- **BUS.N115** SETTLED · `CLAUDE.md:193-196` — "settled, don't re-propose an I2C-level timeout
  mechanism" — For a wedged I2C bus the WDT is the accepted backstop; `getaddrinfo()` is in the same
  bucket (F.2). · related: BUS.T09 (tests the premise) · [H14]
- **BUS.N116** INVAR · `CLAUDE.md:221-223` — "`asy_uart_driver.py` and `asy_uart_comm.py` may never
  block the asyncio loop — not even in a wait state." — Owner, 2026-09-11. Partly enforced by tests:
  tests/test_asy_uart_driver.py:1529, 1564, 1600, 1787, 1833 (clamp and yield tests). · covered-by:
  BUS.T05 · [H14]
- **BUS.N117** ASSUME · `CLAUDE.md:226-227` — "(measured: 4.4ms per 53-byte frame at 115200 baud)" —
  Single measurement. · related: BUS.T05 · [H14]
- **BUS.N118** INVAR · `CLAUDE.md:229-231` — "The yield lives in `ready()` itself, which every read loop
  goes through" — One guarantee in one place. `readline()`/`readline_until_complete()` bypass the
  `any()` clamp. · related: BUS.S06 · [H14]
- **BUS.N119** INVAR · `CLAUDE.md:231-233` — "a listener waiting on traffic that may never come must not
  idle at the transaction rate" — `poll_idle_ms` for waits with no deadline. Convention; `_write_all`
  waits with no deadline at the idle rate. · related: BUS.S05, PERF.T07 · [H14]
- **BUS.N120** SETTLED · `CLAUDE.md:234-236` — "why this must **not** be generalised to
  `asy_i2c_driver.py`/`asy_spi_driver.py`" — No partial-read API to clamp to; the WDT backstop applies.
  · related: BUS.T07 · [H14]
- **BUS.N121** MIRROR · `CLAUDE.md:839-840` — "`src/asy_i2c_driver.py`, `src/asy_spi_driver.py`,
  `tests/machine.py` and `digital_twin/machine.py` all state the real semantics now" — Four places must
  keep the deinit semantics in agreement. · related: TEST.T05 · [H14]

## BACKLOG.md

- **BUS.N122** SETTLED · `BACKLOG.md:613-624` — "a known and deliberate asymmetry rather than an
  inconsistency to tidy up" — `SPIDevice` has a sync session, `I2CDevice` none. · covered-by: BUS.T07 ·
  [H15]
- **BUS.N123** INVAR · `BACKLOG.md:705-710` — "asy_uart_driver.UART.deinit()/init() do not respect the
  session lock" — Unguarded by design; "No caller does". · related: UART.T09 · [H15]
- **BUS.N124** INVAR · `BACKLOG.md:896-899` — "every one of these methods fills and decodes with no
  await in between, and no Timer/Pin.irq callback in this codebase touches I2C" — Shared 32-byte I2C
  scratch is safe by convention only. · covered-by: BUS.T02 · [H15]
- **BUS.N125** LIMIT · `BACKLOG.md:898-899` — "A read larger than the scratch ... falls back to
  allocating rather than refusing." — Unexercised fallback (no read > 32 B today). · [H15]

## HEAP_FRAGMENTATION_MEASUREMENTS.md (current, 393 lines; owning area HW)

- **BUS.N126** INVAR · `HEAP_FRAGMENTATION_MEASUREMENTS.md:369-372` — "the CS path must keep a
  scheduling point per session, after deassert and lock release" — Without it a 74-session setup starved
  the loop; the settle inside CS must block (bus hazard). · related: BUS.T04 · [H15]

## UART_C_PORT_CHANGELOG.md (128 lines; owning area UART). Every entry is pending C-side reconciliation, which is out of scope (owner 2026-09-24).

- **BUS.N127** TODO · `UART_C_PORT_CHANGELOG.md:83` — "asy_uart_driver.py may gain optional-buffer
  parameters (buf=None" — B12, future and optional. It becomes Class A only if emitted bytes change. ·
  [H15]
- **BUS.N128** SETTLED · `UART_C_PORT_CHANGELOG.md:85` — "B14 — asy_uart_driver.py gains a pluggable
  framing codec" | Pass-through is the default. · related: ALGO.T04 · [H15]
- **BUS.N129** MIRROR · `UART_C_PORT_CHANGELOG.md:86` — "a C-side equivalent — if the C implementation
  has one at all — must be equally terminating" — B15: `cancel_read_timeout()` is bounded; holders that
  never acknowledge are counted in `cancel_unacknowledged`. · related: UART.T02 · [H15]
- **BUS.N130** PLATFORM · `UART_C_PORT_CHANGELOG.md:95` — "Measured on the dev bench's jumper at 4.4ms
  of held loop per 53-byte frame at 115200 baud" — B24: clamp to `any()` plus yield. The clamp alone
  gave 14.6 ms. Dated figures; owner direction 2026-09-11. · covered-by: BUS.T05 · [H15]
- **BUS.N131** ASSUME · `UART_C_PORT_CHANGELOG.md:96` — "measured in the digital twin as a third of the
  event loop with nothing on the wire at all" — B25: yield moved into `ready()`; `poll_idle_ms` is 50 ms
  on dev. · related: PERF.T07 · [H15]

## Commit messages (chronological)

- **BUS.N132** INVAR · `commit 417c827` — "BACKLOG.md tracks that a future caller adopting
  repeated-start must pass out_stop=False explicitly" — Repeated-start I2C reads need explicit
  out_stop=False; the BACKLOG entry no longer exists, only the code comment remains. · tracked:
  src/asy_i2c_driver.py:247-248 comment | - · [H17]
- **BUS.N133** TODO · `commit a5fe9fd` — "future SPIDevice consumers need the same \"does every call
  site actually catch what this can raise\" check" — SPI raises
  ValueError/RuntimeError/NotImplementedError on setup/programmer-error paths; each new consumer's call
  sites must be audited. · status: no dedicated tracker found (ISL29125 is I2C; FRAM is the only SPI
  consumer) (low) — UNTRACKED | related: BUS.T* · [H17]
- **BUS.N134** TODO · `commit 3383dee` — "Bus hot-reconnect completeness only field-tested at the
  task-restart level, never confirmed complete (open)" — Restored open item on I2C hot-reconnect
  completeness. · tracked: SPECIFICATION.md:3612-3614 (two-tier recovery statement) | related: BUS.T* ·
  [H17]
- **BUS.N135** RISK · `commit f5c9f90` — "Document the SGP40 general-call reset broadcast as a known,
  accepted risk" — General-call broadcast not protected by either lock layer. · tracked:
  SPECIFICATION.md:2056-2061 (Part C.8) | related: BUS.T* · [H17]
- **BUS.N136** OPENQ · `commit f5c9f90` — "the only structural fix (a bus-wide \"quiesce all sibling
  sessions\" mechanism) is a real architectural addition, flagged for a project-owner decision" —
  General-call hazard left as accepted risk; the quiesce mechanism decision is not recorded as taken or
  declined. · tracked: SPECIFICATION.md:2056-2061 (accepted risk); explicit decline not found (low) |
  related: BUS.T* · [H17]
- **BUS.N137** NOTE(FACT) · `commit 6d9ba2d` — legacy set_register_struct() raises OverflowError;
  src/asy_i2c_driver.py's struct.pack() silently truncates — Bus-layer divergence. · tracked: SPEC Part
  F (struct.pack truncation) | related: BUS.T* · [H17]
- **BUS.N138** NOTE(DEFER-NOTE) · `commit 715cd73` — BACKLOG readfrom_mem_into() item "worth doing
  before the ISL29125 is migrated; that migration happened without it" — Deferred bus API. · status:
  done (BACKLOG.md:890 "done (owner decision, 2026-09-18)") | - · [H17]
- **BUS.N139** NOTE(NOT-A-FIX) · `commit f6a182d` — "This is a churn, latency and hazard-surface fix,
  NOT a fix for the heap fragmentation ... Recorded so the next session does not read this commit as the
  remediation" — CS settle blocking 2us. · status: done | - · [H17]
- **BUS.N140** NOTE(REPORTED-NOT-CHANGED) · `commit 04ef56a` — "I2CDevice inherits Lockable's
  __aenter__/__aexit__ unchanged, so an I2C session burst has no scheduling point either ... recorded
  for a decision rather than fixed here" — I2C session bursts hold the event loop (no yield between
  sessions), unlike SPI after 04ef56a. Recorded only in HEAP_FRAGMENTATION_MEASUREMENTS.md, whose
  2026-09-24 condensation (17b4354) dropped it; it survives only in the git archive
  (12640c2:HEAP_FRAGMENTATION_MEASUREMENTS.md:5227). BACKLOG.md:613-624 records the related
  SPI-sync/I2C-async API asymmetry as deliberate, but not the missing between-session yield for an I2C
  burst. · UNTRACKED (low; partly covered by BACKLOG.md:613) | related: BUS.T*, PERF.T* · [H17]
- **BUS.N141** NOTE(FLAGGED-DELIBERATE) · `commit 9415902 / 88245b2` — "SPIDevice has a synchronous
  session, I2CDevice does not and has nothing equivalent to make synchronous" — API asymmetry. ·
  tracked: BACKLOG.md:613-624 | related: BUS.T* · [H17]
