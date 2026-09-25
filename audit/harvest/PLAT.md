# Harvest — PLAT: MicroPython/RP2040 platform facts

What the project's own comments, docs and history already record for this area (snapshot `2a88cc8`).
Recorded, not verified or triaged; `audit/HARVEST.md` explains the kinds, tags and method.

Kinds: SETTLED 4, INVAR 5, LIMIT 2, RISK 2, ASSUME 7, PLATFORM 361, WORKAROUND 8, SUPPRESS 3, DRIFT 5 — 397 items.


## src/asy_bmp3xx_driver.py

- **PLAT.N001** WORKAROUND · `src/asy_bmp3xx_driver.py:152-154` — "Bare Timer() is valid on rp2 (id
  defaults to -1) despite the installed stub package requiring a positional id" — Stub inaccuracy
  tolerated (only hidden by `tests/machine.py` in the combined mypy run, per CLAUDE.md); removal
  trigger: none stated. · related: PLAT.T05 · [H01]
- **PLAT.N002** PLATFORM · `src/asy_bmp3xx_driver.py:349-351` — "int(float('inf'))/int(float('-inf'))
  raise OverflowError, not ValueError - confirmed against the real MicroPython Unix-port interpreter" —
  Runtime fact verified on the Unix port only, not on rp2. · related: PLAT.T13 · [H01]
- **PLAT.N003** WORKAROUND · `src/asy_bmp3xx_driver.py:424-426, 590` — "micropython-stubs' const() stub
  types indexing as Any even though it's genuinely int at runtime - explicit int narrows it back" — Stub
  typing defect worked around with annotated locals; removal trigger: none stated. · related: PLAT.T05 ·
  [H01]

## src/asy_i2c_driver.py

- **PLAT.N004** PLATFORM · `src/asy_i2c_driver.py:61, 172-173` — "addrsize=None omits the kwarg instead
  of duplicating machine.I2C's own default (8)" — Relies on machine.I2C defaults (addrsize 8, timeout)
  staying as documented. · related: BUS.T10 · [H01]
- **PLAT.N005** PLATFORM · `src/asy_i2c_driver.py:98-100` — "MicroPython's struct has no '?' typecode
  ... A zero-field format (\"\" or \"2x\") unpacks to an empty tuple despite nonzero calcsize" — struct
  behaviour facts on MicroPython. · related: PLAT.T02 · [H01]
- **PLAT.N006** PLATFORM · `src/asy_i2c_driver.py:152-154` — "Unlike CPython, struct.pack silently
  truncates/zero-pads a value that doesn't fit reg_format" — Part F struct truncation fact relied on
  here. · related: PLAT.T02 · [H01]
- **PLAT.N007** PLATFORM · `src/asy_i2c_driver.py:181-185` — "machine.I2C.deinit() does NOT deactivate
  the rp2 bus ... the hard MicroPython 1.29 floor this call carries: SPECIFICATION.md Part F.5" — deinit
  is a no-op on rp2 and only exists from 1.29 (F.5.1). · related: BUS.T06, PLAT.T03 · [H01]

## src/asy_fram_manager.py

- **PLAT.N008** PLATFORM · `src/asy_fram_manager.py:367-368` — "`[x] * n` can segfault uncatchably for
  large n (CLAUDE.md)" — Relies on the Part F `[x] * n` segfault fact. · related: PLAT.T02 · [H01]
- **PLAT.N009** PLATFORM · `src/asy_fram_manager.py:549, 613` — "rp2's mktime() raises OverflowError
  past its ~2037 32-bit epoch range" — Unsourced (not in SPECIFICATION Part F) platform fact to re-check
  at 1.29. · related: PLAT.T02 · [H01]

## src/asy_isl29125_driver.py

- **PLAT.N010** PLATFORM · `src/asy_isl29125_driver.py:230-232, 359-362` — "a set with no waiter is
  remembered, so an INT mid-cycle coalesces into one extra cycle" / "Soft IRQ (rp2's Pin.irq() defaults
  to hard=False) ... (extmod/asyncio/event.py sanctions it from IRQ context)" — ThreadSafeFlag/soft-IRQ
  semantics relied on; two setters for one flag. · related: SENS.T05, XCUT.T21, PLAT.T01 · [H01]
- **PLAT.N011** WORKAROUND · `src/asy_isl29125_driver.py:235-236` — "Bare Timer() is valid on rp2 (id
  defaults to -1) despite the installed stub package requiring a positional id" — Stub defect; removal
  trigger: none stated. · related: PLAT.T05 · [H01]
- **PLAT.N012** WORKAROUND · `src/asy_isl29125_driver.py:262-264` — "A flag plus a bare deadline, not an
  Optional one: time.ticks_ms() types as the stubs' _TicksMs, unspellable in an annotation (F.1)." —
  Stub typing forces stored-ticks deadlines that stay "live" forever. · covered-by: XCUT.T25 · [H01]
- **PLAT.N013** PLATFORM · `src/asy_isl29125_driver.py:872` — "Timer.deinit() IS real on rp2, unlike
  I2C/SPI (Part F.5.1)" — stop_timer has no production caller. · covered-by: SENS.S26 · [H01]
- **PLAT.N014** PLATFORM · `src/asy_isl29125_driver.py:881-883` — "_asdict()/_fields need a ROM level
  above rp2's own" — namedtuple API availability depends on rp2 ROM level (MICROPY_CPYTHON_COMPAT). ·
  related: PLAT.T13 · [H01]
- **PLAT.N015** PLATFORM · `src/asy_isl29125_driver.py:1133-1135` — "The payload is already bytes of the
  exact length because struct.pack() truncates silently on MicroPython." — Relies on Part F struct fact.
  · related: PLAT.T02 · [H01]
- **PLAT.N016** PLATFORM · `src/asy_isl29125_driver.py:1233-1234` — "round() returns an int on
  MicroPython as well as on CPython (verified directly against the pinned Unix-port interpreter)" —
  Verified on Unix port only. · related: PLAT.T13 · [H01]

## src/asy_notification_service.py

- **PLAT.N017** WORKAROUND · `src/asy_notification_service.py:25-27` — "The stubs model a ticks_ms()
  value as an opaque type ... from _mpy_shed.time_mp import _TicksMs" — Imports a private stub-package
  module for typing; breaks if the stub layout changes; removal trigger: none stated. · related:
  PLAT.T05 · [H01]
- **PLAT.N018** PLATFORM · `src/asy_notification_service.py:181-185` — "except (OverflowError, OSError):
  # rp2's mktime()/gmtime() raise past its ~2037 32-bit epoch range" — Unsourced platform fact; failure
  silently yields TS None. · related: PLAT.T02 · [H01]

## src/asy_ntp_client.py

- **PLAT.N019** PLATFORM · `src/asy_ntp_client.py:194-196` — "Uncontended asyncio.Lock.acquire() never
  yields (extmod/asyncio/lock.py), so nothing can run between this get and the following set." —
  Read-modify-write atomicity of the NTP namedtuple rests on this asyncio fact (and on no contention). ·
  related: PLAT.T01, CORE.T08 · [H01]
- **PLAT.N020** PLATFORM · `src/asy_ntp_client.py:262-263` — "RTC().datetime((tm[0], tm[1], tm[2], tm[6]
  + 1, tm[3], tm[4], tm[5], 0))" — Weekday +1 mapping and RTC tuple layout are rp2-specific (no
  comment); RTC is set to offset-shifted time. · related: NET.T11, PLAT.T03 · [H01]
- **PLAT.N021** PLATFORM · `src/asy_ntp_client.py:264-268` — "MicroPython's struct raises plain
  ValueError, not struct.error" + err "Malformed NTP response, treating as no response:" errno=15 —
  struct exception-type fact; malformed replies swallowed. · related: PLAT.T02 · [H01]
- **PLAT.N022** PLATFORM · `src/asy_ntp_client.py:407-411` — "rp2's mktime()/gmtime() raise
  OverflowError past its ~2037 32-bit epoch range - treat exactly like \"not ready\"" + err_s "Time
  calculation failed:" errno=19 — Unsourced platform fact; errno 19 persisted per call (every
  notification poll) with no repeat rule. · related: PLAT.T02, XCUT.T07 · [H01]

## src/asy_spi_driver.py

- **PLAT.N023** PLATFORM · `src/asy_spi_driver.py:4-6, 76-77, 88-90` — "a 32+ byte READ can raise
  OSError(EIO) on an RX overrun since 1.29" / "OSError(EIO) ... is deliberately not caught - it
  propagates" — Version-specific raise site (F.5); FRAM block reads rely on callers catching it. ·
  related: BUS.T01, PLAT.T03 · [H01]
- **PLAT.N024** PLATFORM · `src/asy_spi_driver.py:45-51` — "machine.SPI.deinit() does NOT deactivate the
  rp2 hardware bus - it is forwarded for portability only" — rp2 deinit no-op (F.5.1). · related:
  BUS.T06 · [H01]
- **PLAT.N025** PLATFORM · `src/asy_spi_driver.py:72` — "rp2: always returns None (confirmed against
  extmod/machine_spi.c)" — Write has no error surface. · related: BUS.T01 · [H01]
- **PLAT.N026** PLATFORM · `src/asy_spi_driver.py:153-155` — "Pin.value() writes the GPIO register
  unconditionally regardless of direction, so entering before setup() would silently fail to assert CS"
  — rp2 Pin fact motivating the guard. · related: BUS.T11 · [H01]

## src/asy_uart_comm.py

- **PLAT.N027** PLATFORM · `src/asy_uart_comm.py:151-153` — "memoryview(b\"...\") passes any type check
  and raises only on the first real assignment... A zero-length slice assignment allocates nothing and
  raises in exactly the same case (Part F.1)." — MicroPython memoryview read-only detection behaviour
  relied on by `_is_writable` · related: PLAT.T02 · [H02]
- **PLAT.N028** PLATFORM · `src/asy_uart_comm.py:371-373` — "bytearray assignment truncates silently
  here - 0x101 leaves as 0x01" — MicroPython-specific silent truncation on bytearray item assignment
  (CPython raises) relied on for the range check's rationale · related: PLAT.T02 · [H02]
- **PLAT.N029** PLATFORM · `src/asy_uart_comm.py:409-410` — "never struct.pack()'d: pack() truncates
  silently on this platform" — Part F `struct.pack()` truncation fact · related: PLAT.T02 · [H02]
- **PLAT.N030** PLATFORM · `src/asy_uart_comm.py:671-673` — "MicroPython has no inspect/iscoroutine, and
  a coroutine is structurally a generator here - `send` is what distinguishes one" — Sync/async callback
  detection via `hasattr(result, "send")` · related: PLAT.T01 · [H02]

## src/asy_uart_driver.py

- **PLAT.N031** PLATFORM · `src/asy_uart_driver.py:6` — "A framing/parity/overrun fault on rp2 never
  raises (C.3.2); every method returns a sentinel." — rp2-specific silent RX fault behaviour (overrun
  absorbed) the never-raise contract rests on · related: BUS.T12 · [H02]
- **PLAT.N032** PLATFORM · `src/asy_uart_driver.py:119-121` — "machine.UART.read/readinto wait out
  timeout_char per byte asked for that has not arrived, synchronously - 4.4ms of held loop for one
  53-byte frame at 115200 baud." — rp2 blocking read behaviour + single dated measurement (F.5.8) behind
  the never-block clamp · covered-by: BUS.T05 · [H02]
- **PLAT.N033** INVAR · `src/asy_uart_driver.py:199-200` — "The _UART(...) below must stay a
  construction, never self._uart.init(...): only make_new() re-roots the ring buffers (F.5.7)." — rp2
  port fact (1.29) governing re-init · related: PLAT.T03 · [H02]
- **PLAT.N034** PLATFORM · `src/asy_uart_driver.py:225-227` — "machine.UART.deinit() turns the hardware
  bus off and never raises; poller.unregister() can" — Contrasts with I2C/SPI `deinit()` no-ops on rp2
  (F.5.1) · related: PLAT.T03 · [H02]
- **PLAT.N035** PLATFORM · `src/asy_uart_driver.py:417-418` — "readline() ready via poll can still
  return b\"\" (e.g. a zero-length read)" — Assumed rp2 `readline()` behaviour · related: BUS.S06 ·
  [H02]

## src/asy_webserver_service.py

- **PLAT.N036** PLATFORM · `src/asy_webserver_service.py:166` — "json.dumps() quotes a non-str key's own
  JSON text (True -> \"true\"), never str(key)." — MicroPython `json` key behaviour relied on · related:
  PLAT.T11 · [H02]
- **PLAT.N037** PLATFORM · `src/asy_webserver_service.py:197-199` — "Never an `async def ... yield`
  generator - that syntax segfaults the interpreter (Part F.1)." — Platform segfault fact constraining
  the response shape; also "without it a client reads to EOF, which real-socket soak testing timed out
  against" · related: REST.T05 · [H02]
- **PLAT.N038** WORKAROUND · `src/asy_webserver_service.py:256-260` — "modlwip has freed the pcb yet
  still accepts writes, which reach tcp_write(NULL) - so the 400 microdot answers a muted reset with is
  never sent." — Works around a modlwip reset-then-write behaviour via `peer_gone`; removal trigger none
  stated · related: PLAT.T04 · [H02]
- **PLAT.N039** PLATFORM · `src/asy_webserver_service.py:405` — "MicroPython doesn't support `await`
  inside [a dict comprehension]" — Language-feature gap · [H02]
- **PLAT.N040** PLATFORM · `src/asy_webserver_service.py:736-737` — "backlog is explicit, never
  MicroPython's own default of 5 (extmod/asyncio/stream.py)" — asyncio default backlog fact at 1.29 ·
  related: PLAT.T04 · [H02]

## src/asy_wifi_service.py

- **PLAT.N041** PLATFORM · `src/asy_wifi_service.py:128-129` — "network.STAT_* value seen mid-connect...
  not yet exposed as a named constant by MicroPython's network module itself" — Magic status 2; re-check
  at each version bump · covered-by: NET.T12 · [H02]
- **PLAT.N042** PLATFORM · `src/asy_wifi_service.py:194` — "except (OverflowError, OSError): # rp2's
  mktime()/gmtime() raise past its ~2037 32-bit epoch range" — rp2 time-range fact; `TS` silently
  becomes None after 2037 · related: PLAT.T02 · [H02]
- **PLAT.N043** PLATFORM · `src/asy_wifi_service.py:386, 452` — "self.wlan.config(pm=0xA11140) # disable
  power-save mode" — Magic PM value vs `WLAN.PM_*` constants · covered-by: NET.T12 · [H02]
- **PLAT.N044** PLATFORM · `src/asy_wifi_service.py:725-726` — "never a `[*x, y]` display - that raises
  SyntaxError at parse time on the pinned MicroPython build (Part F.1)" — Language-feature gap at 1.29 ·
  related: PLAT.T02 · [H02]

## src/captive_dns.py

- **PLAT.N045** PLATFORM · `src/captive_dns.py:102-106` — "addr[0] isn't guaranteed to be a str
  (confirmed: can come back as a plain int)" — Socket address shape quirk; `except Exception: addr_int = None`
  swallows it (SUPPRESS) · related: NET.T06 · [H02]

## src/config_manager.py

- **PLAT.N046** PLATFORM · `src/config_manager.py:103-105` — "rp2 builds at
  MICROPY_CONFIG_ROM_LEVEL_EXTRA_FEATURES, one level below the EVERYTHING that _asdict()/_fields need
  (confirmed against ports/rp2/mpconfigport.h)" — Build-config fact to re-check at each pin move ·
  related: PLAT.T13 · [H02]
- **PLAT.N047** PLATFORM · `src/config_manager.py:137-138` — "MicroPython/CPython alike: ValueError for
  NaN, OverflowError for +-inf (py/objint.c's mp_obj_new_int_from_float)" — Source-cited runtime
  behaviour · related: CORE.T03 · [H02]
- **PLAT.N048** PLATFORM · `src/config_manager.py:302-304` — "an RP2040 flash write disables interrupts
  port-wide, and inline it reset the very HTTP connection whose PUT triggered it" — Flash-write IRQ-off
  fact (F.2) behind the deferred flush · related: PLAT.T12 · [H02]
- **PLAT.N049** PLATFORM · `src/config_manager.py:370-373` — "Defensive, so \"last write wins\" never
  depends on asyncio's scheduling being FIFO." — asyncio Lock FIFO order not relied upon · related:
  PLAT.T01 · [H02]
- **PLAT.N050** PLATFORM · `src/config_manager.py:408-409` — "0x4000 = MP_S_IFDIR, MicroPython's own
  stat-mode bit (extmod/vfs.h), uniform across VFS backends incl. littlefs." — VFS stat-mode constant ·
  [H02]

## src/framing_codecs.py

- **PLAT.N051** PLATFORM · `src/framing_codecs.py:41` — "Integer arithmetic only: no float division on a
  target without an FPU." — RP2040 has no FPU · [H02]

## src/math_helpers.py

- **PLAT.N052** PLATFORM · `src/math_helpers.py:10-12` — "const() + a leading underscore keeps them
  compile-time-inlined, so naming them costs no RAM on-device." — Assumes float `const()` folding on the
  target; float32 vs double at freeze time unverified · covered-by: ALGO.T06 · [H02]

## src/print_log.py

- **PLAT.N053** PLATFORM · `src/print_log.py:136-139` — "`[x] * n` can segfault the interpreter
  uncatchably in a size range bytearray()'s own guards don't cover - see CLAUDE.md's
  list-repeat-segfault gotcha for the measured failure-size boundaries" — Platform segfault fact; the
  boundaries live in SPECIFICATION.md:3463, not CLAUDE.md (pointer drift, low) · related: PLAT.T02 ·
  [H02]
- **PLAT.N054** PLATFORM · `src/print_log.py:227` — "_HDR_FMT = \"<H\" # explicit little-endian, no
  padding - bare format defaults to \"@\" here, not \"<\"" — struct default-format fact; `_history_fmt`
  (:234) is a bare "B"*n (harmless for bytes, but outside F.1's pin-"<" rule) (low) · related: ALGO.S02
  · [H02]

## src/system_service.py

- **PLAT.N055** PLATFORM · `src/system_service.py:86-89, 161-163` — "an unstored Timer is GC-eligible
  before its ONE_SHOT callback fires (Part F.1's soft-callback-drop gotcha)" — Timer-GC fact;
  `start_timers()` otherwise hangs forever · related: XCUT.T04 · [H02]
- **PLAT.N056** PLATFORM · `src/system_service.py:144-146` — "except (OverflowError, OSError) as e: #
  rp2's mktime() raises OverflowError past its ~2037 32-bit epoch range" — Time-range fact; errno 2
  persisted each second after 2037 until the random fallback · related: XCUT.T18 · [H02]
- **PLAT.N057** PLATFORM · `src/system_service.py:185-187` — "A finished Task carries no
  .exception()/.result() in MicroPython's asyncio - awaiting it again is the only way to recover why it
  ended" — Re-await semantics of a finished task relied on · covered-by: CORE.S09 · [H02]
- **PLAT.N058** PLATFORM · `src/system_service.py:390-391` — "get_rand_32()-seeded (pico-sdk pico_rand,
  real ring-oscillator entropy) - unique per boot, not a fixed/repeatable seed" — rp2 random-seeding
  fact at 1.29 · covered-by: PLAT.T02 · [H02]

## src/voc_algorithm.py

- **PLAT.N059** PLATFORM · `src/voc_algorithm.py:22, 25, 28, 30, 32, 37` —
  "_VOCALGORITHM_INITI_TRANSITION_MEAN = const(0.01)" (and five other float `const()`s) — Float
  `const()`s evaluated/frozen for a float32 target vs C's double · covered-by: ALGO.T06 · [H02]

## tests/_boot_contiguity_probe.py

- **PLAT.N060** PLATFORM · `tests/_boot_contiguity_probe.py:6-7` — "The map goes to the platform print
  rather than sys.stdout, so it cannot be read back in-process" — `micropython.mem_info(1)` output path
  fact the design depends on (Part I.4(f.1)) · [H03]
- **PLAT.N061** ASSUME · `tests/_boot_contiguity_probe.py:45-46` — "mem_info(1) allocates nothing, so it
  cannot perturb what it measures" — unverified-in-code platform claim the whole measurement rests on
  (MEASUREMENTS M2.2) · [H03]

## tests/_coverage_runner.py

- **PLAT.N062** PLATFORM · `tests/_coverage_runner.py:54-56` — "the MicroPython Unix port doesn't
  register the executed script in sys.modules[\"__main__\"]" — runtime fact the exec-dict design depends
  on · [H03]
- **PLAT.N063** PLATFORM · `tests/_coverage_runner.py:59-61` — "MicroPython's SystemExit has no .code
  attribute (unlike CPython's) -- .args is what's actually populated" — version-sensitive runtime fact,
  "confirmed directly against the built interpreter" · [H03]

## tests/_fram_chip_fake.py

- **PLAT.N064** PLATFORM · `tests/_fram_chip_fake.py:104-106` — "the 1.29 RX-overrun path is only
  testable one layer up" — depends on the MicroPython 1.29 SPI RX-overrun `OSError(EIO)` raise site
  (Part F.5) · [H03]

## tests/_sensortask_scenarios.py

- **PLAT.N065** PLATFORM · `tests/_sensortask_scenarios.py:284-293` — "SCD30 documents up to 150ms of
  clock stretching once per day ... and rp2's I2C timeout default is 50ms" — datasheet + rp2 default the
  SCD30 bus's `timeout >= 150000` µs and the other bus's `== 50000` rest on · related: BUS.T10 · [H03]
- **PLAT.N066** PLATFORM · `tests/_sensortask_scenarios.py:702-704,765-767` — "MicroPython bound methods
  don't expose __self__ ... but they compare equal" — membership-by-equality relies on this
  Unix-port-confirmed runtime behaviour; bound-method identity not guaranteed · [H03]

## tests/_strict_json.py

- **PLAT.N067** PLATFORM · `tests/_strict_json.py:1-3` — "MicroPython's json.loads() accepts a leading,
  doubled or missing comma ('{,\"a\":1 \"b\":2}' parses)" — version-specific json-parser leniency that
  makes this separate oracle necessary; re-check on a MicroPython bump · [H03]

## tests/_threshold_runner.py

- **PLAT.N068** PLATFORM · `tests/_threshold_runner.py:22` — "MicroPython's SystemExit carries .args,
  not CPython's .code" — same runtime fact as `_coverage_runner.py:59-60` · [H03]

## tests/_uart_link_contract.py

- **PLAT.N069** PLATFORM · `tests/_uart_link_contract.py:44` — "real rp2: None, not b\"\", on an empty
  FIFO" — rp2 `UART.read()` empty-FIFO return the fakes model · [H03]

## tests/_webserver_concurrency_scenarios.py

- **PLAT.N070** PLATFORM · `tests/_webserver_concurrency_scenarios.py:16-17` — "the pinned Unix port's
  asyncio.open_connection() has no local_addr" — version-specific asyncio API gap · [H03]

## tests/machine.py

- **PLAT.N071** PLATFORM · `tests/machine.py:21-30` — "Real rp2 values (confirmed against
  ports/rp2/machine_pin.c ... GPIO_IRQ_EDGE_RISE=0x08 ... GPIO_PULL_UP 1, GPIO_PULL_DOWN 2)" — pin
  constants copied from rp2 source at v1.29.0; re-check on a version bump · related: TEST.T19 · [H03]
- **PLAT.N072** PLATFORM · `tests/machine.py:33-39` — "Real rp2 Pin() raises for an invalid id:
  TypeError for a non-int, ValueError outside GPIO0-28." — modelled rp2 fact · [H03]
- **PLAT.N073** PLATFORM · `tests/machine.py:57-58` — "Real rp2 Pin.value(): reads back gpio_get() even
  for an OUT pin (confirmed against ports/rp2/machine_pin.c)" — modelled rp2 fact · [H03]
- **PLAT.N074** PLATFORM · `tests/machine.py:115-117` — "rp2's I2C raises only OSError(EIO) ... or
  OSError(ETIMEDOUT) for bus-busy/clock-stretch" — the raise surface the whole BUS contract (Part D.2)
  is built on · related: BUS.T01 · [H03]
- **PLAT.N075** PLATFORM · `tests/machine.py:118` — "timeout: int = 50000" — the fake's I2C default
  timeout mirrors rp2's 50 ms default, which `_sensortask_scenarios.py:300` asserts on · [H03]
- **PLAT.N076** PLATFORM · `tests/machine.py:153-155,295-297` — "Real rp2 I2C.deinit() exists only from
  1.29 and is a silent no-op even there" — I2C/SPI `deinit()` no-op modelled per Part F.5.1 · [H03]
- **PLAT.N077** PLATFORM · `tests/machine.py:204-212,281-283` — "DMA_MIN_SIZE_THRESHOLD is 32 in
  ports/rp2/machine_spi.c" — 1.29 SPI RX-overrun `OSError(EIO)` only on DMA-path reads of 32+ bytes ·
  [H03]
- **PLAT.N078** PLATFORM · `tests/machine.py:255-261` — "Real rp2 hardware SPI only implements MSB-first
  (confirmed: machine_spi_init()'s own ... mp_raise_NotImplementedError" — modelled rp2 fact · [H03]
- **PLAT.N079** PLATFORM · `tests/machine.py:316-319` — "raises ValueError before any transfer if the
  two buffers' lengths differ" — modelled `write_readinto()` contract · [H03]
- **PLAT.N080** PLATFORM · `tests/machine.py:327-333` — "needs the C-level stream slot only io.IOBase
  carries - a plain class makes register() raise. Reads answer None (MP_EAGAIN)" — Unix-port/rp2 stream
  facts the UART fake depends on (Part F.5) · [H03]
- **PLAT.N081** PLATFORM · `tests/machine.py:421,432,445` — "MicroPython bytearray has no slice-delete,
  unlike CPython" — runtime difference the fake codes around · [H03]
- **PLAT.N082** PLATFORM · `tests/machine.py:450-452` — "Real rp2 uart.write() can accept fewer bytes
  than given ... or none at all (None, MP_EAGAIN)" — short-write contract callers must retry on · [H03]
- **PLAT.N083** PLATFORM · `tests/machine.py:613-614` — "real rp2 Timer.init() raises OSError(ENOMEM) on
  an exhausted alarm pool, and a bare Timer() never reaches that path" — modelled rp2 fact (Part F) ·
  [H03]
- **PLAT.N084** PLATFORM · `tests/machine.py:664-666` — "the real rp2 setter uses only indices
  0/1/2/4/5/6, extracting weekday and never writing it" — RTC fact; the fake returns the tuple exactly
  as set (weekday/subseconds unrecomputed) and `datetime(dt)` returns None · related: TEST.T05 · [H03]

## tests/microtest.py

- **PLAT.N085** PLATFORM · `tests/microtest.py:7-9` — "not part of the Unix port's default \"standard\"
  build, and pulling it in via mip would add a network dependency" — reason `unittest` is not used ·
  [H03]
- **PLAT.N086** PLATFORM · `tests/microtest.py:11-13` — "the MicroPython Unix port doesn't register the
  top-level script in `sys.modules[\"__main__\"]`" — runtime fact the namespace-dict API depends on ·
  [H03]

## tests/neopixel.py

- **PLAT.N087** PLATFORM · `tests/neopixel.py:1-2` — "the MicroPython Unix port build has no real
  `neopixel` module (confirmed directly: `import neopixel` raises ImportError)" — Unix-port fact · [H03]
- **PLAT.N088** PLATFORM · `tests/neopixel.py:4-6` — "a real rp2 NeoPixel.write() is a single busy-wait
  bit-bang call with no return value and no error path at all (confirmed against
  ports/rp2/machine_bitstream.c)" — rp2 fact; the busy-wait blocking duration and colour order are not
  modelled · related: TWIN.T11 · [H03]

## tests/network.py

- **PLAT.N089** PLATFORM · `tests/network.py:1-2` — "the MicroPython Unix port build has no real network
  module (confirmed directly: `import network` raises ImportError)" — Unix-port fact; same MICROPYPATH
  resolution-order dependency as `tests/neopixel.py:2` · [H03]
- **PLAT.N090** PLATFORM · `tests/network.py:4-6,14-19` — "STAT_IDLE=0, STAT_CONNECTING=1, \"obtaining
  IP\"=2 with no named constant on the real port either, STAT_GOT_IP=3" — CYW43 status values the fake
  mirrors · [H03]
- **PLAT.N091** PLATFORM · `tests/network.py:27,35` — "extmod/modnetwork.c: exactly 2 BYTES, else
  ValueError" / "MICROPY_PY_NETWORK_HOSTNAME_MAX_LEN, in bytes" — country/hostname limits modelled from
  MicroPython source · related: NET.S17 · [H03]

## tests/test_asy_bmp3xx_driver.py

- **PLAT.N092** PLATFORM · `tests/test_asy_bmp3xx_driver.py:613-615` — "a negative sea_level_pressure
  gives a confusing TypeError(\"can't convert complex to float\")" — MicroPython-specific numeric
  behaviour confirmed on the Unix port · [H03]
- **PLAT.N093** PLATFORM · `tests/test_asy_bmp3xx_driver.py:918-920` — "int(float('inf')) raises
  OverflowError, not ValueError - confirmed against the real Unix-port interpreter" — runtime fact ·
  [H03]
- **PLAT.N094** PLATFORM · `tests/test_asy_bmp3xx_driver.py:1083-1085` — "on MicroPython it has no base
  type at all, so even isinstance() would reject it (Part F.1)" — bool/int runtime difference behind
  `type(x) is not int` · [H03]
- **PLAT.N095** PLATFORM · `tests/test_asy_bmp3xx_driver.py:1818-1820` — "Real rp2 Timer.init() raises
  OSError(ENOMEM) when the alarm pool is exhausted (confirmed against ports/rp2/machine_timer.c)" — rp2
  fact · related: XCUT.T04 · [H03]
- **PLAT.N096** PLATFORM · `tests/test_asy_bmp3xx_driver.py:1835-1837` — "MemoryError is not an OSError
  subclass (SPECIFICATION.md Part F)" — runtime fact behind the two-arm except · [H03]

## tests/test_asy_dns_client.py

- **PLAT.N097** PLATFORM · `tests/test_asy_dns_client.py:350-355` — "this build reports a registered
  socket ready on every tick regardless of pending data, almost certainly POLLOUT rather than POLLIN" —
  Unix-port `ipoll()` behaviour ("almost certainly" — inferred) the event-mask check depends on ·
  related: TEST.S16 · [H03]

## tests/test_asy_fram_manager.py

- **PLAT.N098** PLATFORM · `tests/test_asy_fram_manager.py:450-451` — "machine.SPI's fake makes write()
  non-injectable on purpose, matching the real rp2 write-only path's own inability to fail (Part F.5.2)"
  — fake-fidelity assumption about rp2 SPI writes · [H03]
- **PLAT.N099** PLATFORM · `tests/test_asy_fram_manager.py:678-680` — "mktime() genuinely raises
  OverflowError past ~2037 on the rp2 port (32-bit signed epoch)" — Y2038 limit for timestamped chunks ·
  related: XCUT.T18, PLAT.T02 · [H03]
- **PLAT.N100** PLATFORM · `tests/test_asy_fram_manager.py:687-689` — "the real builtin module (which
  rejects attribute assignment on this interpreter)" — patching `time` must target the importing
  module's namespace · [H03]
- **PLAT.N101** PLATFORM · `tests/test_asy_fram_manager.py:1480-1482` — "bytearray(negative_int) raises
  MemoryError here too, the negative count being reinterpreted as a huge unsigned request" —
  MicroPython-specific allocation behaviour the degrade path relies on · [H03]
- **PLAT.N102** PLATFORM · `tests/test_asy_fram_manager.py:1599-1602` — "MicroPython's asyncio.gather()
  always returns a list (extmod/asyncio/funcs.py)" — stub/runtime mismatch, suppressed with `type: ignore[return-value]`
  · [H03]
- **PLAT.N103** PLATFORM · `tests/test_asy_fram_manager.py:2203-2206,2252-2254` — "MicroPython 1.29's
  SPI RX-overrun raise site ... The 32-byte DMA threshold is a property of the live path too" — only
  chunks with >= 32-byte reads can hit the overrun · related: STOR.T11 · [H03]
- **PLAT.N104** PLATFORM · `tests/test_asy_fram_manager.py:2595` — "zip(strict=) has no MicroPython
  equivalent" — runtime gap · [H03]

## tests/test_asy_i2c_driver.py

- **PLAT.N105** PLATFORM · `tests/test_asy_i2c_driver.py:34-51` — "the forwarded machine.I2C.deinit() is
  a no-op on rp2 (SPECIFICATION.md Part F.5)" — only the wrapper's dropped reference makes the bus
  "unavailable"; the peripheral keeps running · related: BUS.T06 · [H03]
- **PLAT.N106** PLATFORM · `tests/test_asy_i2c_driver.py:290-292,905-907` — "MicroPython's struct.pack
  silently truncates an out-of-range value (unlike CPython's struct.error)" / "silently zero-fills a
  field this single-value method never supplies" — `set_register_struct` catches only malformed formats,
  never overflow · related: PLAT.T02 · [H03]
- **PLAT.N107** PLATFORM · `tests/test_asy_i2c_driver.py:314-316` — "struct.pack(\"f\", ...) never
  raises for NaN/+-inf" — non-finite values can reach a register write (Part D.12) · related: XCUT.T23 ·
  [H03]
- **PLAT.N108** PLATFORM · `tests/test_asy_i2c_driver.py:446-447,459-461` — "real hardware I2C raises
  OSError(EIO) for a NAK'd/non-responding device, not ENODEV (that's SoftI2C-specific" /
  "OSError(ETIMEDOUT) against ports/rp2/machine_i2c.c" — rp2 raise surface · related: BUS.T01 · [H03]
- **PLAT.N109** PLATFORM · `tests/test_asy_i2c_driver.py:802-804` — "MicroPython's asyncio still runs
  __aexit__ via CancelledError propagating through `async with`, same as CPython" — cancellation-safety
  fact · related: XCUT.T19 · [H03]
- **PLAT.N110** PLATFORM · `tests/test_asy_i2c_driver.py:870-872` — "memoryview slicing clamps
  out-of-range start/end exactly like plain bytes/list slicing" — runtime fact behind the no-raise claim
  · [H03]
- **PLAT.N111** PLATFORM · `tests/test_asy_i2c_driver.py:888-899` — "struct.unpack(\"\", ...) returns an
  empty tuple ... calcsize(\"2x\") == 2, but unpack(\"2x\", ...) == ()" — runtime facts behind the
  empty-tuple guard · [H03]

## tests/test_asy_isl29125_driver.py

- **PLAT.N112** PLATFORM · `tests/test_asy_isl29125_driver.py:296-297,2170,2178` — "int() raises
  ValueError for NaN and OverflowError for inf on MicroPython" — runtime fact · [H03]
- **PLAT.N113** DRIFT · `tests/test_asy_isl29125_driver.py:2835 vs tests/test_asy_bmp3xx_driver.py:1083-1085`
  — "bool is an int subclass in MicroPython as in CPython" — contradicts SPECIFICATION.md:3469-3471
  ("`bool` is NOT a subclass of `int` on MicroPython") and the BMP3xx test's own note · [H03]

## tests/test_asy_neopixel_driver.py

- **PLAT.N114** DRIFT · `tests/test_asy_neopixel_driver.py:541` — "bool is a legitimate int subtype for
  a byte value" — contradicts SPECIFICATION.md:3469-3471 (bool is not an int subclass on MicroPython);
  the assertion itself (`_clamp_byte(True) == 1`) still holds via int() coercion (low) · [H03]
- **PLAT.N115** DRIFT · `tests/test_asy_neopixel_driver.py:542-543` — "confirmed directly against the
  real MicroPython 1.28.0 Unix-port interpreter" — version-stamped fact predates the 1.29.0 pin;
  re-verification not recorded (low) · related: PLAT.T02 · [H03]

## tests/test_asy_notification_service.py

- **PLAT.N116** PLATFORM · `tests/test_asy_notification_service.py:1444-1446,1468-1470` — "MicroPython's
  real `time` module is a read-only builtin" / "rp2's real mktime() raises OverflowError past its ~2037
  32-bit epoch range" — runtime facts; degrade to TS=None · related: XCUT.T18 · [H03]

## tests/test_asy_ntp_client.py

- **PLAT.N117** PLATFORM · `tests/test_asy_ntp_client.py:2336` — "MicroPython zip() rejects strict=" —
  MicroPython-specific builtin limitation the suppression depends on · [H04]
- **PLAT.N118** PLATFORM · `tests/test_asy_ntp_client.py:928-930` — "ipoll(0) returns an always-truthy
  iterator on this port (confirmed directly)" — Unix-port poll fact that test peers (and
  asy_udp_socket.ready()) must iterate event flags rather than truth-test; repeated at :2105-2106 ·
  related: TEST.S16 · [H04]
- **PLAT.N119** PLATFORM · `tests/test_asy_ntp_client.py:1418-1424` — "time.gmtime() returns a 9-element
  tuple (trailing isdst=0), not the 8-element shape MicroPython documents for embedded ports" —
  Unix-port vs rp2 gmtime() shape differs; cettime()'s `len(cet) == 8` would return None on the Unix
  port, so every test normalizes gmtime via a shim — the real Unix-port path is never exercised · [H04]
- **PLAT.N120** PLATFORM · `tests/test_asy_ntp_client.py:1460-1462` — "MicroPython mishandles the latter
  when the plain part contains a literal brace ... raising a spurious KeyError" — implicit concatenation
  of a plain literal containing `{` with an f-string raises KeyError in MicroPython; a parser defect
  code must avoid · [H04]
- **PLAT.N121** PLATFORM · `tests/test_asy_ntp_client.py:1545-1547` — "Real rp2 time.gmtime() always
  returns exactly 8 elements - cettime()'s own `len(cet) == 8` check can't actually fail" — the
  defensive length branch is unreachable on rp2 and only faked in tests · [H04]

## tests/test_asy_scd30_driver.py

- **PLAT.N122** PLATFORM · `tests/test_asy_scd30_driver.py:415-416` — "CRC-valid NaN/inf still decodes,
  and json.dumps() would ship it as bare nan/inf (Part F.1)" — MicroPython json.dumps emits bare nan/inf
  (invalid JSON); SCD30 gates per word · covered-by: XCUT.T23 · [H04]
- **PLAT.N123** PLATFORM · `tests/test_asy_scd30_driver.py:668-670` — "Real rp2 Timer.init() raises
  OSError(ENOMEM) when the alarm pool is exhausted (confirmed against ports/rp2/machine_timer.c)" — rp2
  alarm-pool failure mode the start_timer() guard depends on; also MemoryError is not an OSError
  subclass (:696-698) · related: XCUT.T04 · [H04]

## tests/test_asy_sgp40_driver.py

- **PLAT.N124** PLATFORM · `tests/test_asy_sgp40_driver.py:800-802` — "confirmed against the real
  interpreter that NaN raises ValueError and Inf OverflowError" — int() on non-finite floats:
  NaN→ValueError, Inf→OverflowError; compensation values are validated only for "not None" · related:
  SENS.S03 · [H04]

## tests/test_asy_spi_driver.py

- **PLAT.N125** PLATFORM · `tests/test_asy_spi_driver.py:43-44,57-59` — "machine.SPI's .deinit protocol
  slot is NULL, so the peripheral keeps running and every raw bus op still works" — rp2 `SPI.deinit()`
  is a no-op; only the wrapper's dropped reference makes ops no-op (F.5) · related: PLAT.T03 · [H04]
- **PLAT.N126** PLATFORM · `tests/test_asy_spi_driver.py:152-154,727-728` —
  "machine.SPI.write_readinto() itself raises ValueError(\"buffers must be the same length\") here,
  confirmed against extmod/machine_spi.c" — length check happens before any transfer; the wrapper
  swallows the ValueError into a None return · covered-by: BUS.S04 · [H04]
- **PLAT.N127** PLATFORM · `tests/test_asy_spi_driver.py:166-168` — "confirmed against
  ports/rp2/machine_spi.c at v1.29.0, whose only reported failure is a 32+ byte RX overrun" — the only
  rp2 SPI hardware fault is the 1.29 RX-overrun OSError(EIO) on DMA-path reads · related: PLAT.T03 ·
  [H04]
- **PLAT.N128** PLATFORM · `tests/test_asy_spi_driver.py:238-240` — "rp2 hardware SPI only implements
  MSB-first, sourced from ports/rp2/machine_spi.c's machine_spi_init()" — configure() rejects LSB;
  FakeSPI.LSB mirrors the real constant; no caller uses LSB · [H04]
- **PLAT.N129** PLATFORM · `tests/test_asy_spi_driver.py:285-287` — "Pin.value() writes the GPIO output
  register regardless of direction (confirmed against ports/rp2/machine_pin.c)" — entering a session
  before setup() would silently fail to assert CS; guarded by a RuntimeError · related: BUS.S08 · [H04]
- **PLAT.N130** PLATFORM · `tests/test_asy_spi_driver.py:690-692,699-700` — "only sets its failure flag
  when dest != NULL" / "Transfers below ... dma_min_size_threshold (32) use the blocking software path,
  which has no overrun check" — overrun OSError only on reads ≥32 bytes; write-only transfers can never
  fail; fake models this split · related: PLAT.T03 · [H04]

## tests/test_asy_uart_comm.py

- **PLAT.N131** PLATFORM · `tests/test_asy_uart_comm.py:49-50,1467-1468,1490-1491,1505-1506` —
  "MicroPython's zip() has no strict= parameter to satisfy B905" — index-based pairing used instead of
  zip(strict=) (four sites) · [H04]
- **PLAT.N132** PLATFORM · `tests/test_asy_uart_comm.py:472-473` — "struct.pack() truncates silently on
  this platform" — frame header fields must be range-checked before packing · related: PLAT.T02 · [H04]
- **PLAT.N133** PLATFORM · `tests/test_asy_uart_comm.py:1345-1347` — "bytearray assignment truncates
  silently on this platform, so 0x101 went out as 0x01" — out-of-range cmd id silently became a
  different valid command; guarded now · related: PLAT.T02 · [H04]
- **PLAT.N134** PLATFORM · `tests/test_asy_uart_comm.py:2012` — "not a byte count, and not an int on
  this runtime either (F.1)" — claims `True` is not an int on MicroPython, so a bool return is rejected
  as a byte count · - (low) · [H04]
- **PLAT.N135** PLATFORM · `tests/test_asy_uart_comm.py:2054-2055` — "the Unix port is 64-bit, so a
  native \"L\" is 8 bytes there and 4 on the rp2040" — struct native sizes differ between the test host
  and target; legacy "bbbbL" with hardcoded size 8 holds only on rp2 · related: TWIN.T06 · [H04]

## tests/test_asy_uart_driver.py

- **PLAT.N136** PLATFORM · `tests/test_asy_uart_driver.py:32-34` — "the Unix port never re-checks a
  Python object's ioctl() after registration" — Unix-port select.poll() cannot observe not-ready→ready
  on a pure-Python stream (the CLAUDE.md CI-only hang) · [H04]
- **PLAT.N137** PLATFORM · `tests/test_asy_uart_driver.py:428-429` — "machine.UART exposes neither - so
  this driver remembers what it was constructed with" — machine.UART has no getter for rxbuf/baudrate;
  the driver caches its construction values · - (low) · [H04]
- **PLAT.N138** PLATFORM · `tests/test_asy_uart_driver.py:1201-1203,1219-1220` — "rp2's own write() can
  return a short count" / "matching real MP_EAGAIN -> None" — rp2 UART write returns short counts or
  None on its internal timeout; the driver loops on the return value · related: PLAT.T03 · [H04]
- **PLAT.N139** PLATFORM · `tests/test_asy_uart_driver.py:1629-1630` — "the C read would otherwise spin
  out its EAGAIN probe on every empty call, for the ~1ms it takes ticks_ms() to advance" — rp2
  readline() on an empty ring busy-waits ~1 ms; hence the any() gate · related: BUS.S06 · [H04]
- **PLAT.N140** PLATFORM · `tests/test_asy_uart_driver.py:1728-1730` — "mp_machine_uart_any() drains the
  FIFO and returns ringbuf_avail(), with no raise site (SPECIFICATION.md Part C.3.2)" — the any() raise
  guard is defence in depth, unreachable on rp2 · - (low) · [H04]
- **PLAT.N141** PLATFORM · `tests/test_asy_uart_driver.py:1748-1750` — "The ring can drain between any()
  and the read, and rp2 returns None (MP_EAGAIN) rather than raising" — counted read loops must
  terminate on the None sentinel · related: BUS.T05 · [H04]

## tests/test_asy_udp_socket.py

- **PLAT.N142** PLATFORM · `tests/test_asy_udp_socket.py:356-357` — "sendto() with a payload over the
  ~65507-byte max IPv4 UDP payload raises OSError (EMSGSIZE)" — confirmed on the Unix port only; lwIP's
  behaviour for oversized sends is not stated · related: PLAT.T04 (low) · [H04]
- **PLAT.N143** PLATFORM · `tests/test_asy_udp_socket.py:534-535` — "confirmed directly it is NOT an
  OSError subclass in MicroPython, and RP2040's 264KB SRAM makes allocation failure realistic" — every
  except OSError in asy_udp_socket must also catch MemoryError · [H04]
- **PLAT.N144** PLATFORM · `tests/test_asy_udp_socket.py:975-977` — "Confirmed empirically: a connected
  UDP client socket with a pending ICMP port-unreachable reports POLLOUT|POLLERR, never POLLIN" —
  POLLERR handling proven on the Unix port only; BACKLOG.md Q5 records POLLERR/POLLHUP "never observed"
  on rp2, so the handled path is effectively dead there · related: PLAT.T04 · [H04]

## tests/test_asy_webserver_service.py

- **PLAT.N145** PLATFORM · `tests/test_asy_webserver_service.py:889-890` — "MicroPython's json module
  deserializes the same way CPython's does for a duplicate-key object literal - confirmed directly
  against the pinned interpreter" — duplicate-key JSON behaviour relied upon (last wins); Unix-port
  confirmation · related: PLAT.T11 (low) · [H04]
- **PLAT.N146** PLATFORM · `tests/test_asy_webserver_service.py:1299-1301,1322-1324` —
  "asyncio.TimeoutError, a plain Exception and not an OSError (confirmed against the pinned
  interpreter's extmod/asyncio/core.py)" — Microdot's blanket catch answers 400 for read timeouts and
  EOFError; our wrapper never sees them · related: REST.T09 · [H04]
- **PLAT.N147** PLATFORM · `tests/test_asy_webserver_service.py:1648-1658` — "on silicon that write
  reaches tcp_write(NULL) (state 6 passes modlwip's error check), logs a spurious warning and can spin a
  slot for 5 s" — modlwip ECONNRESET/pcb-freed behaviour; nothing is written after a reset read (silicon
  finding, 1.29) · related: PLAT.T04 · [H04]
- **PLAT.N148** PLATFORM · `tests/test_asy_webserver_service.py:2270-2272` — "`async def ... yield`:
  that produces a broken runtime object here and segfaults the interpreter when driven past an await" —
  MicroPython has no working async generators; streaming bodies must be sync iterators (F.1) · [H04]

## tests/test_asy_wifi_service.py

- **PLAT.N149** PLATFORM · `tests/test_asy_wifi_service.py:439-441` — "network.hostname()'s real
  32-character cap, confirmed against extmod/modnetwork.h on both the v1.26.1 pin and the v1.29.0
  target" — hostname schema max 32 derives from the MicroPython constant · related: NET.S17 · [H04]
- **PLAT.N150** PLATFORM · `tests/test_asy_wifi_service.py:882` — "MicroPython's Task has no cancelled()
  at all (see typings/)" — tests and code must use done() · related: PLAT.T01 (low) · [H04]
- **PLAT.N151** PLATFORM · `tests/test_asy_wifi_service.py:1153-1154` — "Real rp2/cyw43 raises
  ValueError(\"STA required\") when queried outside STA mode (confirmed against extmod/network_cyw43.c)"
  — RSSI query fails routinely in hotspot mode · related: NET.S15 · [H04]
- **PLAT.N152** PLATFORM · `tests/test_asy_wifi_service.py:1319` — "a watcher already parked in wait()
  wakes through the poller, not at once" — ThreadSafeFlag wake semantics relied on by the test ·
  related: PLAT.T12 (low) · [H04]
- **PLAT.N153** PLATFORM · `tests/test_asy_wifi_service.py:1901-1903` — "asyncio.create_task() requires
  a real coroutine object, not the awaitable asyncio.sleep(...) itself returns on this port" —
  MicroPython-specific asyncio constraint · related: PLAT.T01 (low) · [H04]
- **PLAT.N154** PLATFORM · `tests/test_asy_wifi_service.py:2792-2794` — "must not reapply
  essid/password/active(True), or the real CYW43 firmware can interrupt its beacon" — bench-hardware
  finding behind the AP reconfiguration idempotency guard · related: NET.T09 · [H04]

## Partition-wide aggregates

- **PLAT.N155** PLATFORM · `tests/test_base_classes.py:27; tests/test_captive_dns.py:11; tests/test_config_manager.py:11; tests/test_crc_checks.py:7; tests/test_bus_hazard_generated.py:21 (and most files)`
  — "typing isn't available on the real MicroPython test interpreter" — Every file guards `from typing import TYPE_CHECKING`
  with try/except ImportError; depends on the Unix-port build lacking `typing` (low) · [H05]

## tests/test_base_classes.py

- **PLAT.N156** PLATFORM · `tests/test_base_classes.py:213` — "bytearray(-1) would raise MemoryError on
  real MicroPython if unguarded" — Negative-size allocation raises MemoryError (not ValueError) on
  MicroPython; the guard's reason depends on that runtime behaviour · [H05]
- **PLAT.N157** PLATFORM · `tests/test_base_classes.py:231-232` — "confirmed directly against the real
  MicroPython interpreter that bytearray(2**62) raises MemoryError" — Heap-exhaustion technique
  confirmed on the 64-bit Unix port only · [H05]
- **PLAT.N158** PLATFORM · `tests/test_base_classes.py:239-241` — "bytearray(n) raises OverflowError
  instead of MemoryError once n hits the signed-64-bit machine-word boundary (2**63)" — The
  OverflowError threshold is a 64-bit-host fact; on the 32-bit RP2040 the boundary sits elsewhere, so
  this test pins host behaviour only · [H05]

## tests/test_bus_hazard_generated.py

- **PLAT.N159** PLATFORM · `tests/test_bus_hazard_generated.py:52-54, 58-60` — "MicroPython's Unix-port
  test build has no glob module" / "MicroPython's os module has no .path submodule" — Directory scan
  uses os.listdir and "/".join because of missing modules in the Unix-port build · [H05]

## tests/test_bus_hazard_multi_device.py

- **PLAT.N160** PLATFORM · `tests/test_bus_hazard_multi_device.py:156-157` — "MicroPython's builtin
  zip() doesn't accept keyword arguments (confirmed against the pinned Unix-port interpreter)" —
  zip(strict=) unavailable · [H05]
- **PLAT.N161** PLATFORM · `tests/test_bus_hazard_multi_device.py:466` — "32+ bytes: the DMA path, the
  only one that can raise" — Relies on 1.29's new OSError(EIO) raise site on 32+ byte SPI reads (Part
  F.5) · [H05]

## tests/test_config_manager.py

- **PLAT.N162** PLATFORM · `tests/test_config_manager.py:351-352` — "24 bits on the real RP2040's
  single-precision build, 52 on this Unix-port double-precision one" — Float precision differs between
  the test interpreter and the target, so float edge cases on the unit tier do not transfer · related:
  TEST.T19 · [H05]
- **PLAT.N163** PLATFORM · `tests/test_config_manager.py:406-408` — "MicroPython's int(float) raises
  ValueError for NaN and OverflowError for the infinities (confirmed against py/objint.c)" — Runtime
  fact behind NaN/inf int-coercion rejection · [H05]
- **PLAT.N164** PLATFORM · `tests/test_config_manager.py:702-704` — "str length bounds are codepoint
  bounds, not byte bounds, on this MicroPython build" — Confirmed on the Unix-port build only; depends
  on the target also enabling Unicode str support · [H05]
- **PLAT.N165** PLATFORM · `tests/test_config_manager.py:870-871` — "os.stat()/open() raise TypeError
  (not OSError) for a non-string path on this interpreter" — setup() treats that as "not found";
  interpreter-specific exception type · [H05]
- **PLAT.N166** PLATFORM · `tests/test_config_manager.py:912-914` — "MicroPython's json module writes
  NaN/inf ... but cannot read that token back" — A NaN in a stored config makes the file unreadable and
  triggers a rebuild from defaults · [H05]
- **PLAT.N167** PLATFORM · `tests/test_config_manager.py:929-935` — "re-confirmed against the pinned
  v1.29.0 interpreter ... (fixed upstream in 2025, commit 9ef16b466" — json.load() leniency: an omitted
  value before a comma/brace produces a mangled dict instead of raising; accepted because per-key checks
  fall back to defaults; re-check on version bumps · [H05]
- **PLAT.N168** PLATFORM · `tests/test_config_manager.py:1730-1732` — "an RP2040 flash write disables
  interrupts port-wide, and inline it reset the HTTP connection whose PUT triggered it" — Why
  write_config defers the flash write to a separate task (Part F.2) · [H05]
- **PLAT.N169** PLATFORM · `tests/test_config_manager.py:2240` — "MemoryError is not an OSError subclass
  (CLAUDE.md), _flush_staged's except clause lists it explicitly" — Runtime exception-hierarchy fact ·
  [H05]

## tests/test_fake_timer_and_network.py

- **PLAT.N170** PLATFORM · `tests/test_fake_timer_and_network.py:69-91` — ""ÄT" is 2 characters and 3
  bytes" / "65 bytes" / "33 bytes" — Byte-bound facts the fake models: country exactly 2 bytes
  (ValueError), hostname ≤32 bytes (ValueError), WLAN key ≤64 bytes (OSError), SSID ≤32 bytes
  (AssertionError); the exception types are rp2/CYW43 facts to re-check on version moves · [H05]

## tests/test_ntp_fram_system_integration.py

- **PLAT.N171** PLATFORM · `tests/test_ntp_fram_system_integration.py:543-545` — "sleep(0) never
  advances wall-clock time on this Unix-port event loop" — Tests needing real sleeps inside drivers must
  use real sleeps · [H05]

## tests/test_ntp_wifi_dns_integration.py

- **PLAT.N172** PLATFORM · `tests/test_ntp_wifi_dns_integration.py:77-78` — "One single f-string, not a
  plain-string-literal-adjacent-to-an-f-string concatenation - same MicroPython gotcha" — MicroPython
  string-concatenation gotcha with f-strings · [H05]

## tests/test_print_log.py

- **PLAT.N173** PLATFORM · `tests/test_print_log.py:297-299` — "Empirically confirmed under the real
  MicroPython interpreter that append()/extend() on it are silent no-ops" — deque(maxlen=0) behaviour ·
  [H05]
- **PLAT.N174** PLATFORM · `tests/test_print_log.py:307-309` — "deque(maxlen=...) raises ValueError on a
  negative maxlen (confirmed directly against the real MicroPython interpreter)" — Constructor clamps
  instead · [H05]
- **PLAT.N175** PLATFORM · `tests/test_print_log.py:317-323` — "`[x] * n`, what building this deque does
  internally, segfaults the whole process for some huge-but-representable n" — Uncatchable segfault gap
  between MemoryError and OverflowError ranges; the fix caps history_length before allocating
  (CLAUDE.md/Part F fact) · [H05]
- **PLAT.N176** PLATFORM · `tests/test_print_log.py:540-542` — "MicroPython's struct defaults a
  no-prefix format to "@", native alignment and padding, not "<"" — On-chip layout pins "<H"; the FRAM
  byte format is part of the persisted contract · [H05]

## tests/test_strict_json.py

- **PLAT.N177** PLATFORM · `tests/test_strict_json.py:1-2, 56` — "rejects each separator slip the
  interpreter's own lenient json.loads() lets through" — MicroPython json.loads accepts invalid JSON;
  tests/_strict_json.py is the oracle the suite relies on · related: TEST.T17 · [H05]
- **PLAT.N178** PLATFORM · `tests/test_strict_json.py:97` — "bytes, dumped as a string rather than
  refused" — json.dumps(b"x") == '"x"' on MicroPython · [H05]

## tests/test_system_service.py

- **PLAT.N179** PLATFORM · `tests/test_system_service.py:104-109, 576-578, 672-674, 789-791, 849-851` —
  "Real rp2 Timer(period=..., ...) can raise OSError(ENOMEM) under alarm-pool exhaustion (confirmed
  against ports/rp2/machine_timer.c)" — Every Timer arm site guards OSError and MemoryError; the fake's
  `raise_on_arm` models it · related: PLAT.T03 · [H05]
- **PLAT.N180** PLATFORM · `tests/test_system_service.py:141-142` — "Bound-method identity isn't
  guaranteed (each attribute access can mint a fresh bound-method object)" — Runtime fact affecting
  identity-based tests · [H05]
- **PLAT.N181** PLATFORM · `tests/test_system_service.py:278-280` — "MicroPython's real `time` module is
  a read-only builtin (assigning time.mktime raises AttributeError)" — Tests must patch the importing
  module's `time` name · [H05]
- **PLAT.N182** PLATFORM · `tests/test_system_service.py:527-532` — "Regression test for a real GC-drop
  bug: _timer_sequencer() built a fresh, unstored Timer per chain step" — F.1's soft-Timer GC-drop
  gotcha; timers must be preallocated and referenced · [H05]
- **PLAT.N183** PLATFORM · `tests/test_system_service.py:1133-1135` — "MicroPython's asyncio Task has no
  .exception()/.result()" — Why `_log_dead_task()` exists · [H05]

## tests/test_ticks_rollover.py

- **PLAT.N184** PLATFORM · `tests/test_ticks_rollover.py:1, 21-23, 99-100` — "rp2's 2**30 vs. this
  Unix-port rig's 2**62 period" — rp2 ticks wrap at 2**30 ms (~12.4 days); the unit tier runs at 2**62,
  so no test here exercises the real rp2 boundary; the rig period is discovered by bisection · related:
  XCUT.T25 · [H05]
- **PLAT.N185** PLATFORM · `tests/test_ticks_rollover.py:25-27` — "time.ticks_add()'s accepted-delta
  range is exactly [-period/2, period/2), confirmed against extmod/modtime.c" — Delta ≥ period/2 raises
  OverflowError · related: XCUT.T25 · [H05]

## tests/test_uart_comm_hazard.py

- **PLAT.N186** PLATFORM · `tests/test_uart_comm_hazard.py:642-644, 866-868` — "A framing/parity/overrun
  fault never raises on rp2 (SPECIFICATION.md Part C.3.2)" — Electrical faults reach the protocol only
  as dropped/duplicated/delayed bytes or 0x00 runs · [H05]

## tests/test_voc_algorithm.py

- **PLAT.N187** PLATFORM · `tests/test_voc_algorithm.py:531-533` — "MicroPython's struct.pack_into()
  raises ValueError for a negative offset, unlike CPython's" — Caught by pack_into()'s try/except ·
  [H05]

## tests/test_website_build_integration.py

- **PLAT.N188** WORKAROUND · `tests/test_website_build_integration.py:42-44` — "No `with`: the real
  object supports it but the stubs don't declare __enter__/__exit__ (the same stub-gap class as
  Timer()/I2C.deinit())" — Stub gap for DeflateIO; gzip header auto-detect "confirmed on v1.29.0";
  removal trigger: none stated · [H05]

## digital_twin/README.md

- **PLAT.N189** PLATFORM · `digital_twin/README.md:125-126` — "the interpreter's own `json.loads()`
  accepts a missing or stray comma the browser rejects" — MicroPython json lenience fact (F.1) the
  oracle compensates for · [H06]
- **PLAT.N190** PLATFORM · `digital_twin/README.md:534-540` — "real rp2040 `machine.I2C` calls have no
  `await` point (SPECIFICATION.md Part F.2), so a genuinely wedged real peripheral blocks the whole
  single-threaded interpreter" — Hang simulation relies on this platform fact; twin WDT window stated as
  8000 ms · related: TWIN.T02 · [H06]
- **PLAT.N191** PLATFORM · `digital_twin/README.md:712-717` — "`Stream.readexactly()` and
  `Stream.read(-1)` both accumulate with `r += r2` ... Confirmed by reading the pinned interpreter's own
  source" — asyncio stream allocation behaviour tied to the pinned version · [H06]
- **PLAT.N192** PLATFORM · `digital_twin/README.md:721-725` — "**`readinto()` can return `None`** ...
  must be retried; only a real `0` means the peer closed" — Stream API fact the client depends on ·
  [H06]
- **PLAT.N193** PLATFORM · `digital_twin/README.md:775-780` — "The real rp2/lwIP module
  (`extmod/modlwip.c`) accepts the plain tuple directly" — rp2 socket API fact that `src/` relies on ·
  [H06]
- **PLAT.N194** PLATFORM · `digital_twin/README.md:869-872` — "no `socket.getsockname()`;
  `getaddrinfo()` returns a packed `sockaddr`; `asyncio` offers `Lock` and `Event` but no `Semaphore`;
  `os.environ` is missing" — Unix-port facts tied to the pinned build; `mem_info()` with any argument
  prints the full block map · [H06]
- **PLAT.N195** PLATFORM · `digital_twin/README.md:894-906` — "a dangling-pointer dereference at
  `extmod/modselect.c:132` ... `MICROPY_PY_SELECT_POSIX_OPTIMISATIONS` ... defaults to 0 and is only
  turned on by the Unix port's own config" — Root cause and "rp2 unaffected" claim, re-verify on version
  bump · related: TWIN.T07 · [H06]

## digital_twin/machine.py

- **PLAT.N196** PLATFORM · `digital_twin/machine.py:12` — "`_SPI_DMA_MIN_SIZE = 32 # ports/rp2/machine_spi.c's own dma_min_size_threshold`"
  — Copied rp2 port constant; must track the pinned source · related: TWIN.T02 · [H06]
- **PLAT.N197** PLATFORM · `digital_twin/machine.py:48-50` — "Real rp2 values (ports/rp2/machine_pin.c
  at v1.29.0: GPIO_PULL_UP 1, GPIO_PULL_DOWN 2)" — Version-pinned constants (also IRQ_FALLING
  0x04/IRQ_RISING 0x08, uncommented) · [H06]
- **PLAT.N198** PLATFORM · `digital_twin/machine.py:250-252` — "Real rp2 I2C.deinit() exists only from
  1.29, and even there the port's protocol slot is NULL - a silent no-op" — Version-specific platform
  fact (Part F.5.1) · [H06]
- **PLAT.N199** PLATFORM · `digital_twin/machine.py:368-371` — "1.29 added an RX-overrun check to rp2's
  SPI transfer path, reached only by READING 32+ bytes (Part F.5.2)" — Models a version-specific port
  behaviour; sticky and counted forms are twin knobs · [H06]
- **PLAT.N200** PLATFORM · `digital_twin/machine.py:384` — "real rp2 hardware SPI is MSB-first only" —
  Enforced in `init()` only; the constructor accepts `firstbit=LSB` unchecked (low) · [H06]
- **PLAT.N201** PLATFORM · `digital_twin/machine.py:398-399` — "Same NULL-slot no-op as I2C.deinit()
  above, and on rp2 SPI it has always been one" — Version-specific fact · [H06]
- **PLAT.N202** PLATFORM · `digital_twin/machine.py:417-418` — "Below DMA_MIN_SIZE_THRESHOLD (32 in
  ports/rp2/machine_spi.c) a transfer takes the blocking software path, which has no overrun check" —
  Port-internal behaviour, re-check on version bump · [H06]
- **PLAT.N203** PLATFORM · `digital_twin/machine.py:584` — "MicroPython's deque has no clear()" —
  Runtime fact · [H06]
- **PLAT.N204** PLATFORM · `digital_twin/machine.py:604-606` — "`_MP_STREAM_POLL = 3 # py/stream.h`" /
  "`_MAX_BUFFER_SIZE = 32766`" / "`_UART_INVERT_MASK = 3`" — Copied interpreter/port constants; the last
  two cite no source · [H06]
- **PLAT.N205** PLATFORM · `digital_twin/machine.py:792-794` — "keeps real machine_timer_make_new()'s
  \"init helper only runs when the constructor was actually given settings\" behavior for a bare
  Timer()" — Port behaviour mirrored; `freq=` and other real Timer kwargs are not accepted (low) · [H06]
- **PLAT.N206** PLATFORM · `digital_twin/machine.py:828-829` — "a Task cannot cancel itself in
  MicroPython" — Runtime fact · [H06]
- **PLAT.N207** PLATFORM · `digital_twin/machine.py:835-838` — "RP2040 hard cap: 0xffffff / 2 / 1000
  (ports/rp2/machine_wdt.c) ... 1.29 added a separate RP2350 branch" — WDT 8388 ms cap and id-0-only
  mirrored from v1.29.0 · related: TWIN.T02 · [H06]

## digital_twin/_fault_injection.py

- **PLAT.N208** PLATFORM · `digital_twin/_fault_injection.py:3` — "real rp2040 `machine.I2C` calls are
  synchronous C-level HAL calls with no `await` point (SPECIFICATION.md Part F.2)" — Hang model relies
  on this; `time.sleep()` freezes every twin task incl. Timers and WDT countdown · related: TWIN.T05 ·
  [H06]

## digital_twin/_http_client.py

- **PLAT.N209** PLATFORM · `digital_twin/_http_client.py:150-152` — "reader/writer are the same
  underlying Stream object on this build ... close() is a no-op here, the socket only actually closes
  via wait_closed()" — Build-specific asyncio stream fact · [H06]
- **PLAT.N210** PLATFORM · `digital_twin/_http_client.py:75-82` — "readinto() does one
  queue_read()+readinto() pair with no retry loop, so a spurious None ... must be retried" — Pinned
  asyncio stream behaviour · [H06]

## digital_twin/unix_port_gc_unwedge.py

- **PLAT.N211** PLATFORM · `digital_twin/unix_port_gc_unwedge.py:9-11` — "gc.collect() is the recovery
  and the only one that works ... heap_unlock() is not a substitute" — Depends on `py/gc.c` lock-depth
  internals of the pinned version · [H06]

## digital_twin/unix_port_poll_prewarm.py

- **PLAT.N212** PLATFORM · `digital_twin/unix_port_poll_prewarm.py:4-7` — "asyncio.core is a private
  implementation module (the whole point here is reaching into its _io_queue)" — Depends on private
  asyncio internals (`_core._io_queue.poller`); `# type: ignore[import-not-found]` · [H06]
- **PLAT.N213** PLATFORM · `digital_twin/unix_port_poll_prewarm.py:25, :31-33` — "SO_REUSEADDR does not
  let two live listeners share a port (that is SO_REUSEPORT)" / "the Unix port exposes no getsockname()"
  — Host/port facts behind the port scan · [H06]
- **PLAT.N214** ASSUME · `digital_twin/unix_port_poll_prewarm.py:51-70` — "Grow asyncio's shared
  `select.poll()` pollfds array to `ceiling` slots via real loopback connections, then release them" —
  Relies on the pollfds array never shrinking after unregister (an implementation detail of modselect.c)
  · related: TWIN.T07 · [H06]

## digital_twin/network.py

- **PLAT.N215** PLATFORM · `digital_twin/network.py:42, :50` — "extmod/modnetwork.c: exactly 2 BYTES,
  else ValueError" / "MICROPY_PY_NETWORK_HOSTNAME_MAX_LEN, in bytes" — Copied port limits · [H06]

## digital_twin/launch.py

- **PLAT.N216** PLATFORM · `digital_twin/launch.py:351-356` — "MicroPython's `random` has no
  instantiable Random class, unlike CPython" — Runtime fact; conflicts with `machine.py:28`'s "or a
  seeded random.Random" framing of the injection seam (low) · [H06]

## digital_twin/run_generic_integration.py

- **PLAT.N217** PLATFORM · `digital_twin/run_generic_integration.py:198-199` — "MicroPython dicts do not
  preserve insertion order as CPython's do" — Runtime fact the chip lookup depends on · [H06]

## tests/test_digital_twin_bus_hazard_concurrency.py

- **PLAT.N218** PLATFORM · `tests/test_digital_twin_bus_hazard_concurrency.py:161` — "str.removeprefix()
  isn't used here since it's unproven under this MicroPython target" — Unverified runtime capability ·
  [H06]

## tests/test_digital_twin_http_client.py

- **PLAT.N219** PLATFORM · `tests/test_digital_twin_http_client.py:123-135, 175-179` —
  "Stream.readinto() can legitimately return None right after poll() said the socket was readable" —
  Pinned asyncio stream behaviour the client depends on · [H06]

## tests/test_digital_twin_isl29125_autorange.py

- **PLAT.N220** PLATFORM · `tests/test_digital_twin_isl29125_autorange.py:95, 106-107` — "MicroPython's
  zip() rejects it" / "No star-unpacking in a list display: MicroPython rejects it outright" — Runtime
  language gaps (RUF005 exemption) · [H06]

## tests/test_digital_twin_machine.py

- **PLAT.N221** PLATFORM · `tests/test_digital_twin_machine.py:319-320, 329-330` — "Confirmed directly
  against the pinned v1.29.0 ports/rp2/machine_wdt.c source" — WDT id/cap facts pinned to v1.29.0 ·
  [H06]

## tests/test_digital_twin_network_neopixel.py

- **PLAT.N222** PLATFORM · `tests/test_digital_twin_network_neopixel.py:326-327, 352, 358` — "Mirrors
  extmod/modnetwork.c: country() takes exactly 2 BYTES, hostname() at most 32" / "65 bytes:
  cyw43_ll_wifi_join()'s -CYW43_EINVAL" / "33 bytes would overflow the driver's SSID buffer" —
  Port/driver limits copied into the fake · [H06]

## tests/test_digital_twin_poll_prewarm.py

- **PLAT.N223** PLATFORM · `tests/test_digital_twin_poll_prewarm.py:16-17` — "getaddrinfo() returns a
  packed sockaddr on this port, not the (host, port) tuple CPython gives" — Unix-port fact · [H06]

## tests/test_digital_twin_unix_port_gc_unwedge.py

- **PLAT.N224** PLATFORM · `tests/test_digital_twin_unix_port_gc_unwedge.py:20-22` — "gc.collect()
  clears the stuck collect flag but not heap_lock()'s depth counter, and heap_unlock() does the reverse"
  — py/gc.c internals · [H06]

## tests_hardware/flash/test_bus_concurrency.py

- **PLAT.N225** PLATFORM · `tests_hardware/flash/test_bus_concurrency.py:140-143` — "Both claims were
  read out of the rp2 port's own protocol tables and modelled in tests/machine.py and
  digital_twin/machine.py - but a fake agreeing with a fake proves nothing about silicon" — F.5.1
  deinit/singleton claims need silicon confirmation. · related: PLAT.T06 · [H07]

## tests_hardware/flash/test_bus_electrical_timing.py

- **PLAT.N226** PLATFORM · `tests_hardware/flash/test_bus_electrical_timing.py:99-101` — "BACKLOG item
  12 answered the soft_reset() question ... the counter is free-running - but ... every `mpremote exec`
  starves the watchdog into a hard reset that DOES zero it" — ticks_ms survives soft reset; a WDT reset
  zeroes it. · related: HW.T06 · [H07]

## tests_hardware/flash/test_watchdog_starvation.py

- **PLAT.N227** PLATFORM · `tests_hardware/flash/test_watchdog_starvation.py:1-3` — "WDT(timeout=...)
  always re-arms fresh, so the short device-script timeout governs" — Relies on rp2 WDT re-init with a
  shorter timeout taking effect after run_isolated's 8000 ms arm. · related: HW.T06 · [H07]

## tests_hardware/device_scripts/allocation_need_per_source.py

- **PLAT.N228** PLATFORM · `tests_hardware/device_scripts/allocation_need_per_source.py:23-25` —
  "mpremote's raw-REPL soft reset keeps whatever threshold was in force - the boot entry's 32768, or -1
  if the attach interrupted main.py first (MEASUREMENTS M3.8)" — GC threshold survives soft reset;
  script pins -1 explicitly. · [H07]
- **PLAT.N229** PLATFORM · `tests_hardware/device_scripts/allocation_need_per_source.py:26-32` — "GC
  block: 16 B on the RP2040, 32 B on the 64-bit twin"; "The real WDT.feed() is C and allocates nothing
  ... the twin's fake allocates" — Block size and feed-allocation facts the instrument depends on. ·
  [H07]

## tests_hardware/device_scripts/bmp3xx_plausibility_read.py

- **PLAT.N230** PLATFORM · `tests_hardware/device_scripts/bmp3xx_plausibility_read.py:29-30` — "~15s
  worst case exceeds the 8.388s hardware WDT ceiling; soft-reset doesn't reset that timer" — WDT
  persists across soft reset; scripts must feed. · related: HW.T06 · [H07]

## tests_hardware/device_scripts/bus_deinit_is_a_noop_on_real_hardware.py

- **PLAT.N231** PLATFORM · `tests_hardware/device_scripts/bus_deinit_is_a_noop_on_real_hardware.py:1-3, 26-27`
  — "machine.I2C/SPI .deinit() are silent no-ops and each bus id is a static singleton ... never
  observed on real silicon"; "(1.29 floor - it raises AttributeError on 1.28)" — F.5.1 version-specific
  facts; re-check on a pin move. · related: PLAT.T06 · [H07]

## tests_hardware/device_scripts/float_boundary_2pow24.py

- **PLAT.N232** PLATFORM · `tests_hardware/device_scripts/float_boundary_2pow24.py:1-3` — "RP2040's real
  firmware is MICROPY_FLOAT_IMPL_FLOAT (24-bit mantissa ...) - the Unix-port test rig uses doubles and
  can't reproduce this" — Float representation gap between target and test rig. · related: PLAT.T08 ·
  [H07]

## tests_hardware/device_scripts/fram_cs_hijack_fault_injection_and_recovery.py

- **PLAT.N233** PLATFORM ·
  `tests_hardware/device_scripts/fram_cs_hijack_fault_injection_and_recovery.py:38-39` — "Reading an
  output pin back gives its driven level on rp2" — rp2 Pin readback fact the injection proof rests on. ·
  [H07]

## tests_hardware/device_scripts/fram_error_log_reset_race_verify.py

- **PLAT.N234** PLATFORM · `tests_hardware/device_scripts/fram_error_log_reset_race_verify.py:58-60` —
  "MicroPython has no iterable unpacking inside a list display ... a runtime SyntaxError on target and
  neither ruff nor mypy sees it (caught by the real board, 2026-09-11)" — Target-only syntax gap
  invisible to host tooling. · related: PLAT.T07 · [H07]

## tests_hardware/device_scripts/fram_pause_unpause_and_gating.py

- **PLAT.N235** PLATFORM · `tests_hardware/device_scripts/fram_pause_unpause_and_gating.py:26-28` —
  "mpremote's soft reset does NOT disarm an armed rp2 watchdog, so a script running past the ~8s timeout
  resets the board mid-run, presenting as a bare serial EIO" — Load-bearing WDT fact every long device
  script depends on. · related: HW.T06 · [H07]

## tests_hardware/device_scripts/scheduler_saturation_drop.py

- **PLAT.N236** PLATFORM · `tests_hardware/device_scripts/scheduler_saturation_drop.py:1-3` —
  "MICROPY_SCHEDULER_DEPTH=8 on rp2, SPECIFICATION.md Part F.1" — Version/port-specific constant. ·
  related: PLAT.T03 · [H07]

## tests_hardware/device_scripts/timer_alarm_pool_exhaustion.py

- **PLAT.N237** PLATFORM · `tests_hardware/device_scripts/timer_alarm_pool_exhaustion.py:1-3, 12` —
  "Timer.init() raises OSError(ENOMEM) once the RP2040's real hardware alarm pool is exhausted"; "the
  real pool is small and fixed" — F.2 platform claim confirmed on silicon (count reported, not pinned).
  · related: PLAT.T03 · [H07]

## tests_hardware/device_scripts/uart_read_never_blocks_the_loop.py

- **PLAT.N238** PLATFORM · `tests_hardware/device_scripts/uart_read_never_blocks_the_loop.py:68-71` —
  "POLLIN firing on a nearly empty buffer is the precondition for the whole finding" — rp2 UART
  readiness semantics (F.5.8), re-check on a version move. · related: PLAT.T06 · [H07]

## tests_hardware/device_scripts/watchdog_starvation_reset.py

- **PLAT.N239** PLATFORM · `tests_hardware/device_scripts/watchdog_starvation_reset.py:2-3, 7-9` — "Arms
  a short 1500ms window and never feeds it" — Relies on re-arming an already-armed rp2 WDT (8000 ms from
  run_isolated) with a shorter timeout; result read host-side without `reset_cause()`. · covered-by:
  HW.S15 · [H07]

## tests_hardware/README.md

- **PLAT.N240** PLATFORM · `tests_hardware/README.md:316-319` — "`__del__` never runs on user-class
  instances and `MICROPY_PY_WEAKREF` is off" — rp2 has no exact end-of-GC signal; an `await`-less
  `get_value()` is an always-truthy coroutine. · related: PLAT.T13 · [H08]
- **PLAT.N241** SETTLED · `tests_hardware/README.md:415-419` — "resolved (2026-09-11): it has,
  repeatedly." — Bench has run 1.29.0; kept as struck-through history. · related: DOC.T05 (low) · [H08]
- **PLAT.N242** PLATFORM · `tests_hardware/README.md:463-471` — "`asy_uart_driver.UART.deinit()` does
  not release the GPIO function select" — Moving a UART's pins poisons the peripheral until a hard
  reset; soft resets don't restore pin defaults. · related: PLAT.T03 · [H08]
- **PLAT.N243** PLATFORM · `tests_hardware/README.md:479-484` — "only a genuine `hard_reset()` resumes
  the live system; `exec()`/`run_isolated()` never do" — mpremote soft-reset never re-runs boot/main
  (resolved). · covered-by: HW.T06 · [H08]
- **PLAT.N244** PLATFORM · `tests_hardware/README.md:667-671` — "real rp2/lwIP does not appear to
  propagate ICMP errors onto a connected UDP socket's poll state" — Zero POLLERR/POLLHUP in 6 retry
  cycles; `AsyUDPSocket.ready()` handling effectively dead on rp2. · related: PLAT.T04 · [H08]
- **PLAT.N245** PLATFORM · `tests_hardware/README.md:953-966` — "the soft-reset boot path in
  `ports/rp2/main.c` only re-runs `main.py` when that's `FRIENDLY_REPL`" — Raw-REPL entry always
  soft-resets and leaves `main.py` stopped; only a hard reset resumes. · covered-by: HW.T06 · [H08]

## dev_legacy/README.md

- **PLAT.N246** PLATFORM · `dev_legacy/README.md:122-129` — "can raise `MemoryError` mid-import even
  with ~200 KB free" — Mount-import compiles on-device; precompile with version-matched `mpy-cross`
  (check `mpy vX.Y`). · [H08]
- **PLAT.N247** PLATFORM · `dev_legacy/README.md:130-132` — "`micropython.const()` names can't be
  imported across modules under either approach" — Const names compiled away at definition site (E.5.1).
  · related: PLAT.T02 · [H08]
- **PLAT.N248** PLATFORM · `dev_legacy/README.md:581-586` — "the Pico W's `cyw43439` WiFi chip's WPA2
  handshake silently fails against a PMF-enabled/mixed config" — `wifi-sec.pmf disable` + WPA2/CCMP-only
  are load-bearing for the AP. · [H08]
- **PLAT.N249** RISK · `dev_legacy/README.md:602-614` — "falls back to a **filesystem**
  `boot.py`/`main.py` if the frozen path returns instead of blocking forever" — A stale VFS `/main.py`
  auto-started despite a frozen `_boot.py`; never `cp` entry scripts to the VFS. · related: PLAT.T10,
  PAR.T08, XCUT.T20 · [H08]

## dev_legacy/*.py (reference-only 2026-08-27 on-device snapshot, MicroPython 1.24.1 — plan §2.2; field/bench behaviour only)

- **PLAT.N250** PLATFORM · `dev_legacy/asy_spi_driver.py:44-46` — "micropython build for rp2 does not
  recognize \"pins\" keyword!" — 1.24.1-era rp2 `SPI.init()` fact (version-specific). · related: BUS.S03
  (low) · [H08]

## scripts/test.sh

- **PLAT.N251** PLATFORM · `scripts/test.sh:20-21` — "The Unix port's time.mktime() calls the host's
  real libc, which reads $TZ - unlike the rp2 firmware's TZ-agnostic override" — Unix-port vs rp2
  `mktime` divergence (ports/unix/modtime.c vs ports/rp2/datetime_patch.c) is a version-specific fact
  the test tier depends on. · related: XCUT.T18 · [H09]
- **PLAT.N252** PLATFORM · `scripts/test.sh:327` — "prints \"memory allocation failed, ...\"
  (py/runtime.c:1692/1696)" — Gate wording and line citation are tied to the pinned MicroPython source;
  re-check on a pin move. · related: TEST.T18 · [H09]

## scripts/typecheck.sh

- **PLAT.N253** WORKAROUND · `scripts/typecheck.sh:83-97` — "Two verified regressions in
  micropython-stdlib-stubs 1.29.0.post1/.post2, repaired at the stub tree" — Recreates
  `asyncio/futures.pyi` and un-comments `NotImplemented` in `builtins.pyi`; removal trigger: upstream
  re-ships the fix (repair then no-ops). Must not be replaced with `type: ignore` in src/ (CLAUDE.md). ·
  covered-by: PLAT.T05 · [H09]

## scripts/run_bench_soak_tests.sh

- **PLAT.N254** PLATFORM · `scripts/run_bench_soak_tests.sh:8` — "The ~12.4-day ticks_ms() rollover" —
  Depends on rp2 `ticks_ms` period (`MICROPY_PY_TIME_TICKS_PERIOD` = 2^30). · related: PLAT.T13 · [H09]

## scripts/_strip_type_checking.py

- **PLAT.N255** PLATFORM · `scripts/_strip_type_checking.py:1-3` — "`mpy-cross` doesn't
  dead-code-eliminate these (SPECIFICATION.md Part B.11)" — mpy-cross optimisation behaviour at the
  pinned version is the reason the stripper exists. · related: SCR.T03 · [H09]

## scripts/build_firmware.py

- **PLAT.N256** PLATFORM · `scripts/build_firmware.py:96-97` — "Frozen as \"main.py\" rather than
  \"<device>_boot.py\" ... a custom _boot.py would cost USB entirely" — Source-confirmed rp2 boot fact
  at the pinned version. · related: PLAT.T10 · [H09]

## scripts/_digital_twin_ci_suite.py

- **PLAT.N257** PLATFORM · `scripts/_digital_twin_ci_suite.py:185` — "(py/runtime.c:1692/1696)" — Line
  citation into pinned MicroPython source. · [H09]

## toolchain/versions.toml

- **PLAT.N258** PLATFORM · `toolchain/versions.toml:9-10` — "ref = \"v1.29.0\"" — The single MicroPython
  pin; every move triggers CLAUDE.md's standing full re-check (Part F.5), stub re-derivation and the
  overrides' anchor checks. · related: TOOL.T12 · [H09]

## toolchain/micropython_overrides.py

- **PLAT.N259** PLATFORM · `toolchain/micropython_overrides.py:179-182` — "tcp_alloc() never reclaims
  one at equal priority; modlwip aborts it after 10 s ... The pattern every limit ever measured on
  silicon ran at" — SPARE_TCP_PCBS = 3 rests on lwIP/modlwip behaviour and silicon measurements. ·
  related: PLAT.T04 · [H09]
- **PLAT.N260** PLATFORM · `toolchain/micropython_overrides.py:183-186` — "IP_HLEN is 40, not 20: pbuf.h
  picks it on LWIP_IPV6, which ports/rp2/lwip_inc/lwipopts.h enables" — Header-size constant (74) and
  `_MEM_ALIGNMENT = 4` hand-copied from pinned sources. · covered-by: TOOL.T04 · [H09]
- **PLAT.N261** PLATFORM · `toolchain/micropython_overrides.py:214-215` — "The port leaves
  MEMP_MEM_MALLOC, LWIP_WND_SCALE and LWIP_DISABLE_*_SANITY_CHECKS at 0 and LWIP_TCP/LWIP_UDP at 1" —
  Unverified-at-runtime assumption about port config that makes every check live. · covered-by: TOOL.T04
  · [H09]
- **PLAT.N262** PLATFORM · `toolchain/micropython_overrides.py:269-271` — "modlwip.c's tcp_write()
  always sets TCP_WRITE_FLAG_COPY" — Pinned-source fact behind the MEM_SIZE floor. · related: PLAT.T04 ·
  [H09]

## toolchain/setup_toolchain.py

- **PLAT.N263** PLATFORM · `toolchain/setup_toolchain.py:353-357, 375` — "settrace_flag =
  \"-DMICROPY_PY_SYS_SETTRACE=1 \" if settrace else \"\"" — The settrace variant is the same `standard`
  variant plus a `-D`, which works only because `MICROPY_PY_SYS_SETTRACE` is `#ifndef`-guarded upstream
  (unlike `MICROPY_ASYNC_KBD_INTR`). · related: TOOL.T05 · [H09]

## buildgen/pico_gpio.py

- **PLAT.N264** PLATFORM · `buildgen/pico_gpio.py:5, 36-37` — "WIRELESS_RESERVED_GPIOS = frozenset({23,
  24, 25, 29})" — Pico W wireless-reserved GPIOs (datasheet p.7). · covered-by: GEN.T07 · [H09]

## buildgen/codegen.py

- **PLAT.N265** PLATFORM · `buildgen/codegen.py:348-350` — "lines.append(f\"_FIRMWARE_VERSION =
  const({FIRMWARE_VERSION!r})\")" — Emits `const('<str>')`; depends on MicroPython 1.29 accepting string
  consts. · covered-by: GEN.T14 · [H09]

## buildgen/validate.py

- **PLAT.N266** PLATFORM · `buildgen/validate.py:112-113` — "below it the CYW43 cannot bring the hotspot
  up at all" — CYW43 WPA2 minimum. · [H09]

## pyproject.toml

- **PLAT.N267** PLATFORM · `pyproject.toml:46-49, 357-358` — "target-version = \"py310\"" /
  "python_version = \"3.10\"" — Checked-code syntax floor set to 3.10 as a proxy for MicroPython. ·
  [H09]
- **PLAT.N268** SUPPRESS · `pyproject.toml:116-129` — "MicroPython has no PEP 448 unpacking in displays
  ... (verified)" / "deque takes no keyword arguments (TypeError, verified)" — Ignore RUF005, RUF037,
  RUF012, PYI024; platform facts verified on the pinned interpreter. · related: PLAT.T02 · [H09]
- **PLAT.N269** SUPPRESS · `pyproject.toml:150-153` — "FURB122's `f.writelines()` does not exist on
  MicroPython file objects (AttributeError, verified on the pinned interpreter)." — Ignore FURB122;
  platform fact. · related: PLAT.T02 · [H09]
- **PLAT.N270** SUPPRESS · `pyproject.toml:348-351` — "`itertools` does not exist in the rp2 port at
  all" — tests_hardware/device_scripts/**: RUF007; platform fact. · [H09]

## .gitignore

- **PLAT.N271** PLATFORM · `.gitignore:35-38` — "py/builtinimport.c's MP_FROZEN_PATH_PREFIX \".frozen/\"
  ... routes straight to the compiled-in frozen-module table" — Import-sentinel fact that forces
  `frozen_modules/`; re-check on pin moves. · [H09]

## tests_scripts/test_buildgen_validate.py

- **PLAT.N272** PLATFORM · `tests_scripts/test_buildgen_validate.py:164` — "\"SensorStation\" (13) + 20
  = 33, one over network.hostname()'s cap" — network.hostname() 32-char cap is a MicroPython/CYW43 fact
  to re-check on version moves · related: NET.T07 · [H10]
- **PLAT.N273** PLATFORM · `tests_scripts/test_buildgen_validate.py:1499-1500` — "a closing connection's
  FIN_WAIT pcb outlives its slot, and lwIP never reclaims one at equal priority" — lwIP PCB fact behind
  the "max_connections + 3 spare PCBs" rule (SPARE_TCP_PCBS) · related: PLAT.T04 · [H10]

## tests_scripts/test_coverage_runner.py

- **PLAT.N274** PLATFORM · `tests_scripts/test_coverage_runner.py:52` — "MicroPython's SystemExit
  carries .args, not CPython's .code" — Runtime difference the runner's exit propagation depends on ·
  [H10]
- **PLAT.N275** PLATFORM · `tests_scripts/test_coverage_runner.py:71-72` — "the Unix port prints an
  uncaught traceback to STDOUT (verified directly)" — test.sh must merge 2>&1 before scanning; single
  verification · related: SCR.T01 · [H10]

## tests_scripts/test_device_script_gc_threshold.py

- **PLAT.N276** PLATFORM · `tests_scripts/test_device_script_gc_threshold.py:2-3` — "mpremote's raw-REPL
  soft reset keeps the boot entry's threshold (rp2 runs gc_init() once, outside that loop)" —
  rp2/mpremote fact; heap results not naming their threshold are void (MEASUREMENTS M3.8) · related:
  HW.T16 · [H10]

## tests_scripts/test_heap_map_parser.py

- **PLAT.N277** PLATFORM · `tests_scripts/test_heap_map_parser.py:18-27` — "32 B per block (the Unix
  port's size; the rp2 port's is 16, and the parser derives it rather than assuming either)" — Depends
  on the exact `micropython.mem_info(1)`/`gc_dump_info` text format (header lines, 64 blocks per line,
  map glyphs); a format change upstream breaks every heap-map assertion · related: PLAT.T07 · [H10]

## tests_scripts/test_memory_error_gate_agreement.py

- **PLAT.N278** PLATFORM · `tests_scripts/test_memory_error_gate_agreement.py:12-15` — "The
  interpreter's own MemoryError messages, from py/runtime.c:1692/1696 - the only two in the pinned
  source." — Gate wording depends on the pinned MicroPython source's messages/line numbers; re-check on
  a version move · related: PLAT.T07 · [H10]

## tests_scripts/test_micropython_overrides.py

- **PLAT.N279** PLATFORM · `tests_scripts/test_micropython_overrides.py:464-477` — "876, not 856:
  pbuf.h's PBUF_IP_HLEN is 40 under LWIP_IPV6, which the rp2 port enables" — rp2 enables LWIP_IPV6; a
  constant in the Python restatement was previously wrong · [H10]

## tests_scripts/test_test_sh.py

- **PLAT.N280** PLATFORM · `tests_scripts/test_test_sh.py:494-506` — "gc.threshold() raises
  OverflowError only near 2^63 (measured) - so the bound asserted here is the rp2040's" / "py/modgc.c
  maps every one of them to (size_t)-1" — GC_THRESHOLD validated to the rp2040's 32-bit range; any
  negative = reactive default · [H10]

## tests_scripts/test_threshold_runner.py

- **PLAT.N281** PLATFORM · `tests_scripts/test_threshold_runner.py:76-77,90-92` — "MicroPython's
  SystemExit carries .args, not CPython's .code" / "the Unix port prints an uncaught traceback to
  STDOUT, not stderr (verified directly)" — Runtime facts the runner and gate depend on · [H10]

## SPECIFICATION.md Part A.5 (Microdot / REST layer, 287-335)

- **PLAT.N282** PLATFORM · `SPECIFICATION.md:318-322` — "each accepted connection runs in its own
  independent `asyncio.Task` (confirmed against `extmod/asyncio/stream.py`)" — Isolation relies on
  pinned asyncio. · related: PLAT.T01 · [H12]

## SPECIFICATION.md Part A.6 (Datasheets, 337-356)

- **PLAT.N283** LIMIT · `SPECIFICATION.md:345-347` — "the RP2040 *silicon* datasheet is not in the repo,
  so its GPIO function-mux table is not readable here" — Missing primary reference; pin-mux substituted
  by MicroPython macros. · covered-by: SENS.S20 · [H12]

## SPECIFICATION.md Part A.8 (REST API endpoint reference, 571-625)

- **PLAT.N284** PLATFORM · `SPECIFICATION.md:613-615` — "NaN/±inf attempting int-coercion are caught via
  MicroPython's own `int(float)` exception shapes" — Depends on MicroPython's exception types for
  int(nan/inf). · related: CORE.T03 · [H12]

## SPECIFICATION.md Part A.9 (The frozen-HTML pipeline, 627-653)

- **PLAT.N285** PLATFORM · `SPECIFICATION.md:634-637` — "`.frozen/` is a hardcoded MicroPython
  import-machinery sentinel (`MP_FROZEN_PATH_PREFIX`)" — Version-specific import fact. · [H12]

## SPECIFICATION.md Part B.4-B.9 (754-826)

- **PLAT.N286** PLATFORM · `SPECIFICATION.md:807-809` — "this project's pinned MicroPython vendors an
  mbedtls commit predating that fix" — Version-specific fact to re-check on each pin move. · [H12]

## SPECIFICATION.md Part B.11 (Building this project's firmware, 931-984)

- **PLAT.N287** PLATFORM · `SPECIFICATION.md:950-958` — "That entry point is frozen under the literal
  name `\"main.py\"`, NOT imported from a custom `_boot.py` — load-bearing, re-confirmed against pinned
  v1.29.0" — Relies on `ports/rp2/main.c` boot order (USB after frozen `_boot.py`); upstream #15230. ·
  related: PLAT.T10 · [H12]

## SPECIFICATION.md Part B.14 (MicroPython build overrides framework, 1063-1114)

- **PLAT.N288** INVAR · `SPECIFICATION.md:1077-1080` — "these anchors are exactly the kind of thing to
  re-verify on the next `toolchain/versions.toml` `[micropython] ref` bump" — Manual re-verification
  obligation beyond the literal anchor check. · related: PLAT.T07 · [H12]

## SPECIFICATION.md Part B.14.1 (`unix_kbd_intr`, 1116-1213)

- **PLAT.N289** PLATFORM · `SPECIFICATION.md:1136-1138` — "`MICROPY_ASYNC_KBD_INTR (!MICROPY_PY_THREAD_GIL)`
  - true for this project's non-threaded \"standard\" variant build" — Pinned-source anchor. · [H12]
- **PLAT.N290** INVAR · `SPECIFICATION.md:1202-1213` — "Re-verification checklist for a MicroPython
  version bump ... re-run this section's own hammer-loop verification ... do not assume \"it built\" is
  sufficient" — Manual version-bump obligation. · related: PLAT.T06 · [H12]

## SPECIFICATION.md Part B.14.2 / B.14.2.1 (`lwip_connection_counts`, 1215-1379)

- **PLAT.N291** PLATFORM · `SPECIFICATION.md:1225-1228` — "`MEMP_NUM_NETCONN` is dead on this port." —
  `LWIP_NETCONN 0`/`LWIP_SOCKET 0` in pinned lwipopts_common.h. · related: PLAT.T04 · [H12]
- **PLAT.N292** PLATFORM · `SPECIFICATION.md:1229-1234` — "`MEMP_NUM_UDP_PCB` is a bare `#define` (`4 + LWIP_MDNS_RESPONDER`),
  and so is `LWIP_STATS 0`" — Pinned-source guard shapes. · related: NET.T05 · [H12]
- **PLAT.N293** PLATFORM · `SPECIFICATION.md:1245-1248` — "`py/mkrules.cmake:81` folds
  `$ENV{CFLAGS_EXTRA}` into `CMAKE_C_FLAGS`" — Line-anchored upstream citation; drifts with the pin. ·
  [H12]
- **PLAT.N294** RISK · `SPECIFICATION.md:1309-1316` — "`modlwip.c`'s write retries `tcp_write()` up to
  200 x 50 ms, blocking the whole VM for up to 10 s ... no asyncio timeout can interrupt it. Never
  observed on silicon" — Latent 10 s VM block when the arena is exhausted. · covered-by: PLAT.T04 ·
  [H12]
- **PLAT.N295** PLATFORM · `SPECIFICATION.md:1309-1311` — "`extmod/modlwip.c:802` calls `tcp_write()`
  with `TCP_WRITE_FLAG_COPY` unconditionally" — Line-anchored upstream fact. · [H12]
- **PLAT.N296** LIMIT · `SPECIFICATION.md:1376-1379` — "this firmware never calls lwIP's C
  `stats_display()`, so reading them needs a probe of its own" — No pool-exhaustion diagnostics in the
  field. · [H12]

## SPECIFICATION.md Part C intro, C.1-C.2 (1475-1535)

- **PLAT.N297** PLATFORM · `SPECIFICATION.md:1516-1517` — "`_VAL_<ABBREV> = const(((\"<Field>\", \"<type>\", default, min, max, special),))`"
  — Relies on `const()` accepting tuples on the pinned MicroPython. · related: PLAT.T02 · [H12]

## SPECIFICATION.md Part C.5 / C.5.1-C.5.3 (Config schema system, 1699-1797)

- **PLAT.N298** PLATFORM · `SPECIFICATION.md:1706-1708` — "A schema constant referenced inside another
  `const()`-wrapped tuple must itself be `const()`-wrapped — `const()` only folds references to other
  `const()`-defined names." — Compiler folding rule. · related: PLAT.T02 · [H12]

## SPECIFICATION.md Part C.6 (Data model, 1799-1805)

- **PLAT.N299** PLATFORM · `SPECIFICATION.md:1802` — "not `_fields`/`_asdict()` (MicroPython's
  namedtuple provides neither)" — Port-feature claim to re-check at 1.29
  (`MICROPY_PY_COLLECTIONS_NAMEDTUPLE__ASDICT`). · related: PLAT.T13 · [H12]

## SPECIFICATION.md Part C.9.1 (Read-trigger timer stagger, 2211-2298)

- **PLAT.N300** PLATFORM · `SPECIFICATION.md:2260-2272` — "a `Timer.PERIODIC`'s underlying Pico-SDK
  repeating alarm reschedules itself by returning `-self->delta_us` from its own alarm callback" —
  Pinned `ports/rp2/machine_timer.c` drift-freedom fact. · related: PLAT.T03 · [H12]

## SPECIFICATION.md Part D (src/ Production-Quality Checklist, 2576-2728)

- **PLAT.N301** PLATFORM · `SPECIFICATION.md:2625` — "Dual-core Cortex-M0+ @ up to 133MHz, 264KB SRAM
  (F.1)" — Silicon facts. · [H12]
- **PLAT.N302** PLATFORM · `SPECIFICATION.md:2638-2643` — "`typing` isn't importable at all on the
  Unix-port test interpreter. `mpy-cross` does not dead-code-eliminate `if TYPE_CHECKING:` blocks" —
  Interpreter/compiler facts behind the guard and strip step. · [H12]
- **PLAT.N303** PLATFORM · `SPECIFICATION.md:2665-2670` — "the build target has moved to the latest
  stable (currently v1.29.0 — the last pass's findings are catalogued in Part F.5)" — Version-pinned
  statement to update on bump. · related: PLAT.T06 · [H12]

## SPECIFICATION.md Part E.3 / E.3.1 (Running; heap and timeouts, 2828-2921)

- **PLAT.N304** PLATFORM · `SPECIFICATION.md:2841-2846` — "`.frozen` is a literal MicroPython sentinel,
  not an ordinary directory" — Needed on MICROPYPATH. · [H12]
- **PLAT.N305** PLATFORM · `SPECIFICATION.md:2897-2898` — "MicroPython block-buffers 4096 bytes whenever
  stdout is not a tty" — Reason for `stdbuf`. · [H12]

## SPECIFICATION.md Part E.8 (Measurement traps, 3271-3362)

- **PLAT.N306** PLATFORM · `SPECIFICATION.md:3355-3356` — "because `bool` is not an `int` subclass here
  at all (F.1)" — MicroPython-specific type fact. · [H12]

## SPECIFICATION.md Part F.1 — Core platform facts

- **PLAT.N307** PLATFORM · `SPECIFICATION.md:3426-3430` — "Deployed units run **MicroPython 1.26** ...
  The refactor pins **v1.29.0** ... targets whatever's most recent stable at the time" — Two runtimes in
  play (1.26 fielded, 1.29.0 refactor); "most recent stable" is a moving target the pin must be
  re-checked against. · related: PLAT.T07 · [H13]
- **PLAT.N308** PLATFORM · `SPECIFICATION.md:3432-3433` — "`machine.WDT` hard-caps at **8388ms**;
  current code uses `WDT(timeout=8000)` (388ms margin) — don't casually increase" — Silicon/port cap and
  the 388 ms margin every watchdog budget rests on. · related: XCUT.T01, PERF.T01 · [H13]
- **PLAT.N309** PLATFORM · `SPECIFICATION.md:3433-3435` — "USB (`mp_usbd_init()`) initializes only
  *after* the frozen `_boot.py` returns" — A blocking `_boot.py` means USB never comes up on a hard
  reset; port-version-specific boot-order fact. · related: PLAT.T10 · [H13]
- **PLAT.N310** PLATFORM · `SPECIFICATION.md:3435-3437` — "RP2040: dual-core Cortex-M0+ @ up to 133MHz,
  264KB SRAM ... Pico W's littlefs partition (~848KB)" — Silicon/board sizing facts (partition size
  depends on CYW43 blob size, i.e. on the firmware build). · [H13]
- **PLAT.N311** PLATFORM · `SPECIFICATION.md:3443-3444` — "`importlib` isn't frozen into this project's
  own manifest today" — Manifest-dependent fact (low). · [H13]
- **PLAT.N312** PLATFORM · `SPECIFICATION.md:3446-3450` — "`mp_sched_schedule()` drops it if
  MicroPython's fixed-depth scheduler queue (depth 8 on rp2 ...) is full, with no exception" — Soft
  Timer callbacks can be silently lost; depth-8 is a port/version constant. · covered-by: XCUT.T22 ·
  [H13]
- **PLAT.N313** PLATFORM · `SPECIFICATION.md:3455-3461` — "Iterable unpacking inside a list/tuple/set
  *display* (`[*a, b]`) raises `SyntaxError: *x must be assignment target`" — Parser gap on the pinned
  version; code relies on `a + [b]` concatenation instead — re-check on bump. · related: PLAT.T02 ·
  [H13]
- **PLAT.N314** PLATFORM · `SPECIFICATION.md:3463-3467` — "`[x] * n` (list repeat) can segfault the
  interpreter for n in roughly 2⁶¹-2⁶³" — Measured only on the 64-bit Unix port (rp2 cannot express such
  n); cause "likely" an overflow — inferred, not traced. · related: PLAT.T02 · [H13]
- **PLAT.N315** PLATFORM · `SPECIFICATION.md:3469-3478` — "`bool` is NOT a subclass of `int` on
  MicroPython ... Verified directly against the pinned v1.29.0 build" — Validators rely on
  `isinstance(x, int)` excluding bool; a version change could alter `mp_type_bool`. · related: CORE.S12
  · [H13]
- **PLAT.N316** PLATFORM · `SPECIFICATION.md:3480-3481` — "`machine.Timer.init()` can raise
  `OSError(ENOMEM)` if the RP2040's alarm pool is exhausted — every call site must handle it" —
  rp2-specific failure mode; per-site handling is a convention. · covered-by: XCUT.T04 · [H13]
- **PLAT.N317** PLATFORM · `SPECIFICATION.md:3481-3483` — "**`MemoryError` is not an `OSError`
  subclass** ... catch `(OSError, MemoryError)` wherever both are plausible" — Exception-hierarchy fact
  every except clause depends on. · [H13]
- **PLAT.N318** PLATFORM · `SPECIFICATION.md:3485-3488` — "RP2040's real firmware uses single-precision
  `float` ... this project's Unix-port test rig uses double precision" — Test rig and target differ
  numerically; `coerce_numeric()` int→float rounding accepted "since no real schema field's bounds go
  near it". · related: PLAT.T08, MEM.T07 · [H13]
- **PLAT.N319** PLATFORM · `SPECIFICATION.md:3490-3494` — "`'L'` is 4 bytes on rp2 and 8 on the 64-bit
  Unix-port test interpreter" — Native-size struct codes read differently on target vs rig; rule:
  explicit `"<"` prefix. · related: PLAT.T02 · [H13]
- **PLAT.N320** PLATFORM · `SPECIFICATION.md:3496-3499` — "overflow checks added to `py/binary.c` are
  gated behind `MICROPY_PREVIEW_VERSION_2` ... Expect this fact to flip when upstream ships 2.0" —
  Silent pack truncation; explicit future-flip trigger. · related: PLAT.T02 · [H13]
- **PLAT.N321** PLATFORM · `SPECIFICATION.md:3501-3510` — "A `bytearray` destination *resizes* on a
  length mismatch ... a `memoryview` destination raises `ValueError`" — Slice-assignment contracts,
  measured on the Unix port only (not on rp2); plus "no `memoryview.readonly`" and the zero-length-slice
  writability probe. · [H13]
- **PLAT.N322** DRIFT · `SPECIFICATION.md:3512-3515` — "A `micropython.const()`-wrapped value does not
  survive as an importable module attribute in a frozen build" — Upstream MicroPython docs say only
  underscore-prefixed `const()` names are hidden; non-underscore names stay module globals — claim may
  be wrong or narrower than stated (low, not investigated). · related: PLAT.T02 · [H13]
- **PLAT.N323** PLATFORM · `SPECIFICATION.md:3517-3519` — "`time.ticks_ms()` wraps every `2**30` ms
  (~12.4 days) on rp2**; `ticks_diff()` is correct ... under `2**29` ms" — rp2 tick period fact. ·
  covered-by: XCUT.T25 · [H13]
- **PLAT.N324** PLATFORM · `SPECIFICATION.md:3525-3534` — "`globals()` does not preserve a module's
  top-level statement order ... Nesting `asyncio.run()` ... segfaults ... `await` inside a comprehension
  is a `SyntaxError` ... async generator ... segfaults" — Four runtime traps; the `/status` streaming
  design (collect into list, `iter()`) exists because of the async-generator one. · related: TEST.T01 ·
  [H13]
- **PLAT.N325** PLATFORM · `SPECIFICATION.md:3540-3541` — "`asyncio.TimeoutError` is a plain
  `Exception`, not `OSError` — catch it separately" — Exception-hierarchy fact. · related: PLAT.T01 ·
  [H13]
- **PLAT.N326** PLATFORM · `SPECIFICATION.md:3543-3548` — "`gc.threshold()`: no-arg call returns the
  current threshold (or `-1` if disabled ...); called with an argument ... always returns `None`" — GC
  API semantics the (e)/(f) test stages depend on. · [H13]
- **PLAT.N327** PLATFORM · `SPECIFICATION.md:3560-3562` — "MicroPython's `json.loads()` is not a JSON
  validator: `extmod/modjson.c`'s tokenizer skips `,` and `:`" — Accepts malformed JSON; tests of
  emitted JSON must use `tests/_strict_json.py`. · related: XCUT.T23 · [H13]
- **PLAT.N328** PLATFORM · `SPECIFICATION.md:3564-3574` — "`json.dumps()` is not a JSON serializer
  either — it never raises (measured against the pinned interpreter, 2026-09-24)" — Emits bare
  `nan`/`inf`, `<object>`; rp2 overflows to inf at ~3.4e38; measured on the Unix port. · covered-by:
  XCUT.T23 · [H13]

## SPECIFICATION.md Part F.2 — Blocking calls / timeout-wrapping

- **PLAT.N329** PLATFORM · `SPECIFICATION.md:3594-3597` — "`socket.getaddrinfo()` belongs in this same
  bucket ... (confirmed against real MicroPython issue-tracker reports). Moot for DNS" — Can't be
  timeout-wrapped; "moot" only for the project's own DNS — the plan notes `getaddrinfo` is still reached
  inside `asyncio.start_server`. · related: PLAT.T04 · [H13]
- **PLAT.N330** PLATFORM · `SPECIFICATION.md:3612-3614` — "A well-documented, long-standing upstream
  MicroPython characteristic (open since v1.19.1/2022) ... no upstream fix" — Upstream status to
  re-check on a version bump. · [H13]
- **PLAT.N331** PLATFORM · `SPECIFICATION.md:3629-3631` — "the RP2040 flash write disables interrupts
  port-wide for its duration, and doing it inline was resetting the very HTTP connection" — rp2
  flash-write IRQ-off fact behind the deferred flush. · related: PLAT.T12 · [H13]

## SPECIFICATION.md Part F.5 — MicroPython 1.29 delta (intro)

- **PLAT.N332** ASSUME · `SPECIFICATION.md:3669-3671` — "The pin is field-proven on the dev bench
  (2026-09-11) ... flash tier (25 passed), bench tier (85 passed) and mid soak tier (4 passed)" — Dated
  suite counts backing the 1.29 pin; will drift as tiers grow. · covered-by: DOC.S17 · [H13]

## SPECIFICATION.md Part F.5.1 — I2C/SPI deinit no-ops

- **PLAT.N333** PLATFORM · `SPECIFICATION.md:3680-3685` — "**Both are no-ops on this port** ... rp2's
  `machine_i2c_p`/`machine_spi_p` ... never set that slot" — rp2 `deinit()` of I2C/SPI does nothing;
  peripheral and pin functions stay. · covered-by: PLAT.T03 · [H13]
- **PLAT.N334** PLATFORM · `SPECIFICATION.md:3689-3694` — "`machine.I2C(id)`/`machine.SPI(id)` return a
  **static per-bus singleton** ... nothing is reclaimable on a `deinit()`" — No way to release an rp2
  bus from Python; re-construction reconfigures the shared object. · related: BUS.T10 · [H13]
- **PLAT.N335** PLATFORM · `SPECIFICATION.md:3701-3703` — "`machine.UART.deinit()`,
  `machine.Timer.deinit()` and `network.WLAN.deinit()` are **real** on rp2" — Which deinits actually
  release hardware. · covered-by: PLAT.T03 · [H13]

## SPECIFICATION.md Part F.5.2 — rp2 SPI RX-overrun EIO

- **PLAT.N336** PLATFORM · `SPECIFICATION.md:3712-3714` — "`machine_spi_transfer()` gained an RX-overrun
  check (upstream #18471) ... `mp_raise_OSError(MP_EIO)`" — New 1.29 raise site on SPI reads. ·
  covered-by: PLAT.T03 · [H13]
- **PLAT.N337** PLATFORM · `SPECIFICATION.md:3724-3727` — "Write-only transfers can still never raise
  ... Only transfers of ≥ 32 bytes are affected — `dma_min_size_threshold` is 32" — Precise bounds of
  the fault; version-specific constants. · covered-by: PLAT.T03 · [H13]

## SPECIFICATION.md Part F.5.3 — Free wins in the 1.29 build

- **PLAT.N338** PLATFORM · `SPECIFICATION.md:3750-3756` — "The interpreter core now genuinely runs from
  SRAM ... Cost ... **12,918 B** of RAM no longer available as Python GC heap" — Build-layout fact tied
  to 1.29's linker rule; affects every Part I budget. · related: MEM.T01 · [H13]
- **PLAT.N339** DRIFT · `SPECIFICATION.md:3778-3780` — "`-fno-math-errno` is now on ... so `math.sqrt`
  compiles to the hardware instruction" — RP2040 is a Cortex-M0+ with no FPU/sqrt instruction; "hardware
  instruction" is doubtful (low, not investigated). · related: PLAT.T08 · [H13]

## SPECIFICATION.md Part F.5.4 — machine.mem_backup()

- **PLAT.N340** PLATFORM · `SPECIFICATION.md:3784-3789` — "**28 bytes** across two regions ...
  **Survives a WDT reset, `machine.reset()` and a deepsleep wake; lost on power-off.**" — rp2
  watchdog-scratch facts, enabled by default in 1.29. · covered-by: PLAT.T03 · [H13]
- **PLAT.N341** SETTLED · `SPECIFICATION.md:3793-3797` — "**Deliberately not adopted** (project owner,
  2026-09-11) ... deliberate, temporary instrumentation, never normal-path code" — Owner decision; the
  plan's PLAT.T03 lists "`mem_backup()` adoption (F.5.4)" as a topic — must be triaged as settled. ·
  related: PLAT.T03, XCUT.S10 · [H13]

## SPECIFICATION.md Part F.5.5 — Stub defects repaired at install

- **PLAT.N342** ASSUME · `SPECIFICATION.md:3802-3803` — "accounted for **every one of the 26 findings**
  the version bump surfaced" — Dated count tied to stub `1.29.0.post1/.post2`. · related: DOC.T08 ·
  [H13]

## SPECIFICATION.md Part F.5.6 — Smaller 1.29 facts / non-events

- **PLAT.N343** PLATFORM · `SPECIFICATION.md:3828-3831` — "**`X: int = const(...)` now folds.** ...
  `\"_A\" in globals()` `True` on 1.28, `False` on 1.29" — Parser behaviour change; fielded 1.26 still
  has the footgun. · related: PLAT.T02 · [H13]
- **PLAT.N344** PLATFORM · `SPECIFICATION.md:3838-3840` — "**`extmod/asyncio/` is byte-identical between
  the two tags** ... no timeout/cancellation support added to `socket.getaddrinfo()`" — Ruled-out item
  for the next bump. · covered-by: PLAT.T06 · [H13]
- **PLAT.N345** PLATFORM · `SPECIFICATION.md:3841-3843` — "**Zero commits** to `py/profile.c`,
  `py/modsys.c`, `extmod/modselect.c`, `shared/timeutils/` ... the E.3 `select.poll()` GH-Actions hang
  cause and the `TZ=UTC` Unix-port fact both stand" — Non-events that keep two test-rig facts valid. ·
  covered-by: PLAT.T06 · [H13]
- **PLAT.N346** PLATFORM · `SPECIFICATION.md:3844-3848` — "I2C `WRITE1` transfer fix is behind
  `MICROPY_PY_MACHINE_I2C_TRANSFER_WRITE1`, which rp2 leaves at 0 ... DHCP's new `send_router` ... the
  captive portal is unaffected ... `gc.mem_free()` ... still call the slow `gc_info()`" — Several
  ruled-out 1.29 changes; "captive portal is unaffected" is an inference. · covered-by: PLAT.T06 · [H13]
- **PLAT.N347** PLATFORM · `SPECIFICATION.md:3847-3848` — "The RP2350 watchdog ~16 s fix is RP2350-only
  — the 8388 ms cap in F.1 stands." — Silicon-specific. · covered-by: PLAT.T06 · [H13]
- **PLAT.N348** PLATFORM · `SPECIFICATION.md:3849-3850` — "`SOCK_RAW` is now default-on and present in
  the built firmware. Noted only" — Unused capability; F.2 settles the reachability-probe question. ·
  covered-by: PLAT.T06 · [H13]

## SPECIFICATION.md Part F.5.7 — UART.deinit() RX buffer unrooted

- **PLAT.N349** PLATFORM · `SPECIFICATION.md:3858-3867` — "`mp_machine_uart_deinit()` clears
  `MP_STATE_PORT(rp2_uart_rx_buffer[id])` ... the UART IRQ handler resumes writing into memory the
  collector is free to hand out" — Upstream heap-corruption hazard on `deinit()`+same-size `init()`
  (rp2, 1.29.0 source). · related: PLAT.T03 · [H13]

## SPECIFICATION.md Part F.5.8 — UART read() blocks the loop

- **PLAT.N350** PLATFORM · `SPECIFICATION.md:3882-3888` — "`mp_machine_uart_read()` loops once per
  requested byte ... `mp_event_handle_nowait()` ... **never yields to asyncio** ...
  `mp_machine_uart_ioctl()` reports `POLLIN` as soon as the FIFO holds *one* byte" — rp2 1.29.0 UART
  read semantics behind the never-block rule; `timeout_char=1` is this project's value. · covered-by:
  BUS.T05 · [H13]
- **PLAT.N351** ASSUME · `SPECIFICATION.md:3914-3915` — "The docs' lower-bound wording (\"may return 1
  even if there is more than one character available\") costs nothing here: under-reporting only ever
  means another round" — Relies on documented `any()` semantics. · related: PLAT.T03 · [H13]
- **PLAT.N352** PLATFORM · `SPECIFICATION.md:3979-3981` — "`machine.I2C`/`machine.SPI` expose no
  equivalent ... an SCD30's 18-byte read *is* a ~1.8ms synchronous span by construction" — No
  partial-read API on rp2 I2C/SPI. · related: BUS.T10 · [H13]

## SPECIFICATION.md Part F.6 — SIGINT during gc_collect() wedges the Unix-port heap

- **PLAT.N353** ASSUME · `SPECIFICATION.md:4075-4076` — "**`src/` needs nothing** — it has no
  `KeyboardInterrupt` shutdown path, and rp2 has no SIGINT" — Claim about src/ and about rp2 (USB-REPL
  Ctrl-C raises KeyboardInterrupt on rp2 too) (low). · [H13]

## SPECIFICATION.md Part H.7 — Digital twin integration / connection ceiling

- **PLAT.N354** PLATFORM · `SPECIFICATION.md:4545-4549` — "`tcp_alloc()` reclaims TIME_WAIT, LAST_ACK
  and CLOSING pcbs ... a FIN_WAIT one only at a lower priority ... `extmod/modlwip.c` aborts a close
  still unfinished only after 10 s" — lwIP/modlwip version-specific behaviour. · related: PLAT.T04 ·
  [H13]
- **PLAT.N355** PLATFORM · `SPECIFICATION.md:4557-4560` — "an arrival that finds it full is reset inside
  lwIP (`ERR_BUF`), where nothing in `src/` can see it" — Invisible refusal path. · related: PLAT.T04 ·
  [H13]
- **PLAT.N356** PLATFORM · `SPECIFICATION.md:4586-4590` — "A refusal is a FIN ~6 ms after connect, or an
  RST if the client's request bytes had already arrived (`modlwip.c` frees them unread ...)" — lwIP
  close semantics. · related: PLAT.T04 · [H13]

## SPECIFICATION.md Part I.1 — MicroPython memory-management facts

- **PLAT.N357** PLATFORM · `SPECIFICATION.md:4774-4778` — "**The collector is mark-and-sweep,
  non-compacting** ... a 16-byte block on a 32-bit target" — GC design facts behind every contiguity
  rule. · related: MEM.T06 · [H13]
- **PLAT.N358** PLATFORM · `SPECIFICATION.md:4793-4796` — "**No async-generator-shaped alternative
  exists anywhere** ... every MicroPython PEP 525 discussion converges on the same \"not implemented\"
  status" — Upstream-status fact to re-check on a version bump. · related: PLAT.T07 · [H13]
- **PLAT.N359** PLATFORM · `SPECIFICATION.md:4809-4816` — "`gc_alloc()` takes `(size_t n_bytes, unsigned int alloc_flags)`
  and nothing else (`py/gc.c:891`) ... `MICROPY_GC_SPLIT_HEAP` is unavailable on this board:
  `ports/rp2/mpconfigport.h:100-101`" — Pinned-source line citations that move with the version. ·
  related: PLAT.T13 · [H13]

## SPECIFICATION.md Part I.4 — Multi-stage memory-error scheme, (a)-(e)

- **PLAT.N360** PLATFORM · `SPECIFICATION.md:5016-5021` — "the interpreter's own `MemoryError` message
  is `\"memory allocation failed, allocating N bytes\"` (or `\", heap is locked\"`; both raised from
  `py/runtime.c:1692/1696`, and there is no third wording in the pinned source)" — Gate patterns depend
  on pinned-source wording and line numbers. · related: TEST.T18 · [H13]
- **PLAT.N361** PLATFORM · `SPECIFICATION.md:5033-5036` — "rp2 resolves to
  `MICROPY_ERROR_REPORTING_NORMAL` (through `MICROPY_CONFIG_ROM_LEVEL_EXTRA_FEATURES`) — of the four
  reporting levels only `NONE` ... strips exception messages" — Hardware-gate premise tied to build
  config. · related: PLAT.T13 · [H13]

## SPECIFICATION.md Part I.4 — (f), (f.1), (g)

- **PLAT.N362** PLATFORM · `SPECIFICATION.md:5079-5081` — "`gc_collect_end()` resets the allocator's
  free-scan index to zero (`py/gc.c`), so the following module's permanent objects take the lowest
  fitting holes" — The placement effect depends on this allocator detail of the pinned version. ·
  related: PLAT.T13 · [H13]

## CLAUDE.md

- **PLAT.N363** PLATFORM · `CLAUDE.md:17-24` — "MicroPython 1.26/RP2040 specifics, what the 1.29 pin
  changed (Part F.5), the WDT 8388ms cap" — Platform facts (8388 ms WDT cap, soft-Timer drop, `[x] * n`
  segfault, `Timer.init()` ENOMEM, MemoryError not an OSError, `struct.pack` truncation) live only in
  SPEC Part F and must be re-checked when the version moves. · related: PLAT.T06 · [H14]
- **PLAT.N364** INVAR · `CLAUDE.md:29-31` — "Always check current MicroPython and Microdot documentation
  before asserting how an API behaves" — Standing session practice, convention only. · related: PLAT.T06
  · [H14]
- **PLAT.N365** INVAR · `CLAUDE.md:32-41` — "repeat it every time `toolchain/versions.toml`'s
  MicroPython `ref` moves" — The full re-check on every pin move is convention only:
  `--latest`/`write_micropython_ref()` move the pin without prompting it. · covered-by: TOOL.T12 (also
  TOOL.S09) · [H14]
- **PLAT.N366** ASSUME · `CLAUDE.md:42-45` — "Last run: 1.28.0 → 1.29.0, 2026-09-10; results in
  SPECIFICATION.md Part F.5" — One dated pass. Its findings: I2C/SPI `deinit()` are no-ops; a new
  OSError(EIO) on 32+ byte SPI reads; `extmod/asyncio/` byte-identical, so `getaddrinfo()` still can't
  be timeout-wrapped. · related: PLAT.T06, PLAT.T07 · [H14]
- **PLAT.N367** PLATFORM · `CLAUDE.md:43-44` — "a new `OSError(EIO)` raise site on 32+ byte SPI reads" —
  A 1.29-specific raise site that the SPI/FRAM read paths depend on. · related: PLAT.T03 · [H14]
- **PLAT.N368** PLATFORM · `CLAUDE.md:224-226` — "`machine.UART.read()/readinto()` wait out
  `timeout_char` ... inside `mp_event_handle_nowait()`, which never yields" — rp2 1.29 runtime fact
  behind the rule. · related: PLAT.T03 · [H14]
- **PLAT.N369** PLATFORM · `CLAUDE.md:650-657` — "a nested `asyncio.run()` while any other task is still
  parked ... segfaults the MicroPython Unix port" — Deterministic and uncatchable; CPython would raise
  RuntimeError. · related: PLAT.T01 · [H14]
- **PLAT.N370** PLATFORM · `CLAUDE.md:710-714` — "`ports/rp2/datetime_patch.c` overrides this with
  `shared/timeutils`' pure, TZ-agnostic epoch arithmetic" — rp2 vs Unix `mktime` semantics; `src/`
  relies on `time.mktime(time.gmtime())` round-tripping. · related: XCUT.T18, PLAT.T02 · [H14]
- **PLAT.N371** PLATFORM · `CLAUDE.md:743-746` — "MicroPython parses but never evaluates annotation
  expressions at all" — Confirmed on the 1.26 and 1.29.0 Unix ports. · [H14]
- **PLAT.N372** PLATFORM · `CLAUDE.md:832-840` — "rp2 leaves the protocol's `.deinit` slot `NULL`, so
  the method mypy now accepts is a **silent no-op on real hardware**" — I2C/SPI objects are static
  per-bus singletons; the real `deinit()`s are UART, Timer and WLAN. · related: PLAT.T03, BUS.T10 ·
  [H14]

## README.md

- **PLAT.N373** PLATFORM · `README.md:394-396` — "The one real, fixed ~12.4-day wait (time.ticks_ms()'s
  2**30 rollover)" — rp2 tick period of 2**30 ms; stored ticks older than 2**29 flip sign. · related:
  XCUT.T25 · [H14]

## BACKLOG.md

- **PLAT.N374** SETTLED · `BACKLOG.md:183-189` — "deployed code stays pinned to 1.26 until a deliberate
  reflash campaign" — #3 refactor pins 1.29.0; F.1's standing re-check at every pin move. · related:
  PLAT.T07 · [H15]
- **PLAT.N375** PLATFORM · `BACKLOG.md:237-249` — "The counter is free-running hardware time and
  survives the soft reset mpremote performs on raw-REPL entry" — #12: `ticks_ms` survives soft reset;
  `mpremote exec` stops `main.py` and the WDT hard-resets ~8 s later; `_WRAP_FLOOR_MS` guard added; "Do
  not re-investigate". · [H15]
- **PLAT.N376** PLATFORM · `BACKLOG.md:850-852` — "machine.I2C.readfrom_mem_into() was verified against
  the pinned 1.29.0 source rather than from memory" — Version-specific (`extmod/machine_i2c.c`). · [H15]

## HEAP_FRAGMENTATION_MEASUREMENTS.md (current, 393 lines; owning area HW)

- **PLAT.N377** PLATFORM · `HEAP_FRAGMENTATION_MEASUREMENTS.md:24-31` — "Lowest-fit over one fixed heap
  area." / "The hint advances only on a one-block allocation" — Allocator facts read from `py/gc.c` at
  v1.29.0; re-check on a pin move. · related: PLAT.T07 · [H15]
- **PLAT.N378** PLATFORM · `HEAP_FRAGMENTATION_MEASUREMENTS.md:65-66` — "Block size: 16 B on the RP2040
  and on the 32-bit twin, 32 B on the 64-bit Unix port." — A hard-coded ×32 once doubled figures; derive
  from the binary. · related: PLAT.T08 · [H15]
- **PLAT.N379** PLATFORM · `HEAP_FRAGMENTATION_MEASUREMENTS.md:69-70` — "On the board mem_info writes to
  the platform print, not sys.stdout, so the device cannot parse its own map" — Host-side parse
  (`tests_hardware/heap_map.py`) required. · [H15]
- **PLAT.N380** PLATFORM · `HEAP_FRAGMENTATION_MEASUREMENTS.md:155-157` — "An underscore-named
  micropython.const() scalar is inlined at compile time and is not a module attribute" — Reading one
  raises `AttributeError`, hidden by a broad `except`. · related: PLAT.T02 · [H15]
- **PLAT.N381** PLATFORM · `HEAP_FRAGMENTATION_MEASUREMENTS.md:165-170` — "MICROPY_PY_SYS_SETTRACE
  allocates a frame and a code object on every call and generator resume" — 4-5x non-uniform inflation;
  constants calibrated on one binary must be re-derived on the other. · related: TOOL.T05 · [H15]
- **PLAT.N382** PLATFORM · `HEAP_FRAGMENTATION_MEASUREMENTS.md:254-258` — "the latter omits
  extmod/asyncio" / "A module on MICROPYPATH still wins over a frozen one" — Frozen-twin build facts. ·
  [H15]
- **PLAT.N383** PLATFORM · `HEAP_FRAGMENTATION_MEASUREMENTS.md:344-347` — "187,712 + (8 − L) × 2,324 B
  for max_connections = L" — `dev` linker heap at 1.29.0; a mismatch means the image is not the one
  described. · related: HW.T19 · [H15]

## Commit messages (chronological)

- **PLAT.N384** PLATFORM · `commit 5dbf4df` — "a related MicroPython-only struct.pack quirk: it silently
  zero-pads/truncates mismatched values/arg counts instead of raising" — struct.pack silent truncation.
  · tracked: CLAUDE.md "Platform target" / SPECIFICATION Part F | related: PLAT.T* · [H17]
- **PLAT.N385** PLATFORM · `commit db06f3b` — "[x] * n ... MemoryError below ~2**61, OverflowError
  at/above 2**63, but segfaults the whole interpreter process in between" — Uncatchable list-repeat
  segfault range (Unix port measurement). · tracked: CLAUDE.md "Platform target" / SPECIFICATION Part F
  | related: PLAT.T* · [H17]
- **PLAT.N386** PLATFORM · `commit b087dc7` — "A value omitted before a comma/brace (e.g. {\"Count\": ,
  \"Offset\": 1.5}) doesn't raise on this MicroPython version - it desyncs the parser into a mangled
  dict" — MicroPython json.load leniency relied on to degrade via per-key default fallback;
  json.dumps(nan) writes a token json.loads cannot read back. Version-specific (checked at 1.28). ·
  status: covered by a test per commit; not found restated in SPECIFICATION (grep "omitted"/"desync" in
  config_manager.py/SPEC) — UNTRACKED as a platform fact to re-check on version bumps (low) | related:
  PLAT.T* · [H17]
- **PLAT.N387** PLATFORM · `commit 9712cea` — "random.getrandbits(32)'s seed on rp2 comes from
  get_rand_32(), backed primarily by real ring-oscillator entropy" — Boot-signature uniqueness rests on
  an rp2/pico-sdk RNG fact (1.28 source). · tracked: src/system_service.py call-site comment (per
  commit) | - · [H17]
- **PLAT.N388** PLATFORM · `commit d92da47` — "cancelling a task before its first scheduler step can
  raise CancelledError to the awaiter no matter what try/except exists inside the coroutine" — asyncio
  property relied on as irrelevant because the real caller never awaits the DNS task. · status: not
  restated in SPECIFICATION (low) — UNTRACKED | - · [H17]
- **PLAT.N389** PLATFORM · `commit 59d6b7b` — "machine.UART never raises for a hardware-level
  framing/overrun fault on rp2 (silently corrupts/drops instead)" — UART fault silence verified at 1.28.
  · tracked: SPECIFICATION Part C.3.2 (per commit) | related: UART.T*, PLAT.T* · [H17]
- **PLAT.N390** PLATFORM · `commit 7310484` — "concurrent-TCP-PCB-ceiling question (confirmed 5, from
  rp2's lwipopts_common.h)" — Historic PCB ceiling; later superseded by the lwIP override
  (max_connections 6). · status: superseded (BACKLOG "connection-limit work", PR #106) | related:
  REST.T* · [H17]
- **PLAT.N391** PLATFORM · `commit fef4b54` — "MicroPython's import machinery hardcodes \".frozen/\" as
  a sentinel routing straight to the compiled-in frozen-module table" — Reason for frozen_modules/
  directory. · tracked: SPECIFICATION (per commit) | - · [H17]
- **PLAT.N392** PLATFORM · `commit e554073` — "rp2's main.c only initializes USB after the frozen
  _boot.py call returns ... freezing each device's boot_entry/<device>_boot.py content under the literal
  name \"main.py\"" — Firmware autostart design depends on 1.28 rp2 main.c ordering (micropython#15230).
  · tracked: SPECIFICATION Parts B.11/F.1 | related: TOOL.T*, PLAT.T* · [H17]
- **PLAT.N393** PLATFORM · `commit 6f430c7` — "micropython.const()-wrapped values don't survive as
  importable module attributes in a frozen build" — One-off scripts must hand-copy schema tuples; mirror
  obligation. · tracked: SPECIFICATION Part F.1 | related: MIRROR · [H17]
- **PLAT.N394** PLATFORM · `commit 6d08fdb` — "an `async def ... yield` async generator: ... produces a
  broken runtime object (no __aiter__/__anext__) that segfaults when driven past a real await via plain
  next()" — Streaming uses a plain list, not async generators. · tracked: SPECIFICATION Part F.1 | - ·
  [H17]
- **PLAT.N395** PLATFORM · `commit 6aed3c9` — "a confirmed MicroPython quirk (SyntaxError on `[*x, y]`
  star-unpacking in a list display) and the dynamic-import ban" — Language-subset facts to recheck on
  version bumps. · tracked: SPECIFICATION Part F.1 | - · [H17]
- **PLAT.N396** PLATFORM · `commit 90e8c17` — "MicroPython 1.29 added an RX-overrun check to
  ports/rp2/machine_spi.c for reading transfers of 32+ bytes ... Whether asy_fram_manager.py should
  retry a transient overrun is left as an open question (BACKLOG.md #15)" — SPI EIO on 32+ byte reads. ·
  tracked: SPECIFICATION Part F.5.2; BACKLOG "A transient SPI RX overrun is not retried - SETTLED,
  owner, 2026-09-24" | - · [H17 (also H17)]
- **PLAT.N397** SETTLED · `commit 2aceae6 / 154643d / edf11c2` — "The SRAM-resident-code change -
  settled 2026-09-11, project owner's call: the question is RAM, not speed ... the linker-map figure is
  never to be quoted as a measured speedup" — 1.29 SRAM win never timed by decision. · tracked:
  SPECIFICATION.md:3750-3768 (Part F.5.3) | - · [H17]
