# `digital_twin/` — hardware simulator for any buildgen-generated device

A set of fake `machine`/`network`/`neopixel`/`rp2` modules, sitting at the same raw I2C/SPI/UART
bus-transaction mocking boundary `tests/machine.py` establishes for unit tests, but built for a
different purpose: real-time-firing `Timer`s and bounded random-walk sensor values (owner,
2026-08-12), so a full assembled, buildgen-generated `sensortask_<device>.py` module — any real
device of `devices/*.toml`, or a synthetic fixture — can run under the real MicroPython Unix-port
interpreter and behave like it's attached to real hardware, not just satisfy a hand-driven test
double. See SPECIFICATION.md Part A.10 for how this fits into the rest of the architecture, and Part
C.11 point 9 for the per-driver "add a matching chip fake" requirement. How faithful each fake is,
and where it is not, is the "Fidelity table" below.

**Not `tests/machine.py`, and does not import it.** Kept off the default unit-test path, so nothing
here can accidentally affect the deterministic unit-test suite `scripts/test.sh` runs by default
(`MICROPYPATH` set to the unit layout of `scripts/micropypath.toml`): a test that needs a twin
module puts its directory on `sys.path` itself — `digital_twin/` for the `tests/test_digital_twin_*.py`
files and their scenario libraries, `digital_twin/unixport/` (no fake there) for a test needing only
the UDP shim or the NTP responder (see "Running the twin's own tests" below).

## What's here

- `machine.py` — `Pin`/`I2C`/`SPI`/`UART`/`Timer`/`WDT`/`RTC`, `mem_backup()`/`reset_cause()` and
  `reset()`/`bootloader()`. `Timer` fires for real on a wall-clock
  schedule via an internal `asyncio` task, not `_thread` (upstream's own `_thread.rst` docs state
  outright that it "is highly experimental and its API is not yet fully settled" — not a fit for
  load-bearing behavior here, and every real `Timer` callback in this codebase is already trivial
  enough that true preemption buys nothing); an armed `Timer` takes one of rp2's 16 alarms, and the
  seventeenth raises `OSError(ENOMEM)` until one is freed. `Pin` takes rp2's GPIO ids and the Pico W's
  board and CPU names, its modes, pulls and alternate functions, and a line level a test scripts
  through `set_external_level()`. `Pin`
  identity is shared by id (`Pin(8)` constructed twice returns the same underlying pin state), since
  a real GPIO pin is one fixed physical resource and chip fakes and drivers may each construct their
  own `Pin` object for the same id: the chip fake's own `rdy_pin` must be the object the real
  driver's own IRQ `Pin` uses, or a simulated edge never reaches its handler, and the construction
  scenarios (`irq_pins_are_shared_by_chip_fake_and_driver`) check it on every device. `I2C`, `SPI`
  and `UART` are one static object per bus id, as rp2's are: a re-construction re-initialises the
  controller and keeps what is wired to it. Their chips come from a generic **wiring plan**
  (`configure_wiring(plan)`, a plain dict in the exact shape `buildgen.twin_wiring.compute_twin_wiring()`
  produces from a device's own TOML, see "Booting a generated device" below): constructing a bus
  before a plan is configured raises, a plan cannot be replaced once a bus exists, and there is no
  default device. Any address the plan does not wire NAKs — a real bus
  with a fixed, known set of devices on it, not an unbounded fixture. `WDT` records a
  would-have-reset instead of resetting (see "`WDT._arm()`'s late-feed backstop"); `RTC` follows
  rp2's argument rules and, with the runner's wall clock installed, moves `time.time()`/`gmtime()`
  (`_wall_clock.py`). `mem_backup()` keeps rp2's two watchdog scratch regions with their survive and
  clear rules, and `reset()`/`bootloader()` raise `SimulatedResetError`/
  `SimulatedBootloaderEntryError`, `BaseException`s no product `except Exception` survives, so a
  reset ends the event loop as it ends the program on silicon. `I2C.log`/`SPI.log` (an ad-hoc
  introspection aid) keep the most recent 200 entries and count what they dropped;
  `WDT.feed_times` is bounded the same way: the `ticks_ms()` stamp of each `feed()`, oldest first,
  so a test can read the gaps between feeds. `peripheral()` (a booted bus by name),
  `reset_peripherals()` and `reset_test_state()` are test-only.
- `rp2.py` — the DMA channel surface a UART receive ring uses: a paced channel takes the bytes
  `machine.py`'s `UART` receives as their wire time elapses, never per event-loop turn.
- `_sgp40_chip.py` / `_scd30_chip.py` / `_bmp3xx_chip.py` / `_isl29125_chip.py` — one chip fake per
  sensor, each verified against its own datasheet in `datasheets/` for the raw transaction shape and
  sensible value ranges, each class spelled as its driver's `_NAME` (`SGP40Chip`, `SCD30Chip`,
  `BMP3XXChip`, `ISL29125Chip`), each with a `power_cycle()` a re-plug test drives. The SGP40 resets on
  the I2C general call and idles on heater-off. `_scd30_chip.py` starts as a provisioned unit
  (measuring), its RDY pin fires a real rising edge on its own internal
  measurement-interval cadence, exercising the real driver's normal IRQ-driven path; it reports its
  temperature walk less the set temperature offset, as the chip does, and persists its NVM-backed
  settings and measuring status (see "SCD30 persistence" below). `_bmp3xx_chip.py` answers raw ADC
  bytes found by inverting the real compensation formula (owner, 2026-08-12).
  `_isl29125_chip.py` is **dev-only** (`wozi` does not carry this sensor) and is the one fake whose
  high range's full scale is a deliberately non-nominal multiple of its low range's, so the driver's
  user-triggered gain-ratio calibration (SPECIFICATION.md Part M.1.5) has something real to converge
  on instead of the nominal constant it starts from. It also models the destructive `0x08` status
  read (which clears `RGBTHF`, `CONVENF` and `BOUTF` and releases the INT line — `BOUTF` being
  read-to-clear contradicts the datasheet and was measured on real silicon, see SPECIFICATION.md
  Part M.1.2), `BOUTF` high at power-up but **not** after the `0x46` reset command
  (`simulate_brownout()` is the seam for a supply event, which raises it again), the flat address
  pointer that walks the whole `0x00`-`0x0E` map in one burst and then pads with zeros, reserved
  config bits reading back zero, per-resolution clipping at `(1 << bits) - 1`, and
  `set_illumination(lux, tint=(r, g, b))` so a scene can clip one channel while green stays
  mid-scale. Every one of those register-map behaviours was measured against the real part — see
  SPECIFICATION.md Parts C.11.1, M.1.2 and M.1.4 for the divergences those runs found, the subtlest
  being that the threshold **persistence counter** restarts when `RGBTHF` is cleared, not on every
  status read, and a fake that reset it on every read makes the interrupt unreachable at the
  driver's own default sampling rate. Its INT line is **active-low** (`simulate_edge(0)` to assert),
  the opposite of `_scd30_chip.py`'s RDY. A chip with its own measurement clock takes a
  `timer_factory` from `machine.py` rather than importing `machine` itself.
- `_fram_chip.py` — `FRAMChip`, the FRAM chip's SPI opcode protocol (WREN/WRDI/RDSR/WRSR/READ/WRITE/
  RDID), its size and RDID reply from `machine.py`'s one table (`_FRAM_RDID_BY_MAX_SIZE`, pinned to
  the driver's), its memory in 4 KB pages, plus explicit `save_state()`/on-construction load JSON
  persistence (owner, 2026-08-12; see "FRAM persistence" below). Twin-only knobs: `drop_next_wren`,
  `stick_next_wrdi` (a WRDI that leaves WEL set), `corrupt_next_write` (a payload stored with one bit
  flipped), `rdid_once`, `silent` (a chip that answers zeros and ignores every write), and the
  `write_count`/`writes_at` bookkeeping a test reads.
- `_twin_common.py` — the shared helpers every fake imports: the bounded bookkeeping log, the
  saturating counter cap, the buffer fill every fake read uses, the value-walk bounds (`Walk`) and the
  runners' config groups.
- `_crc8.py` / `_fault_injection.py` — small shared helpers (CRC-8 for SGP40/SCD30's word protocol;
  `FaultInjector`, the op-keyed queue of bounded faults and hangs every chip fake carries, mirroring
  `tests/machine.py`'s own `inject_fault()`/`_maybe_raise()` convention).
- `_wall_clock.py` — the twin's wall clock: the built-in `time` module plus an offset that
  `RTC().datetime(set)` and the twin-only `step()` move, as an RTC set moves `time.time()`/`gmtime()`
  on rp2; ticks never step, and `gmtime()`/`localtime()` answer rp2's 8-field tuple. The runner
  installs it into the product modules; the clock-jump tests drive it.
- `_flash_stall.py` — a config flush holds the whole loop for the flash's erase and program time, as
  rp2 programs its flash with interrupts off; the runner installs it under `asy_config_manager`.
- `unix_port_idle_poll.py` — `skip_idle_flag_polls()` removes a wait the Unix port adds and rp2 lacks.
  With a non-fd stream registered (a `ThreadSafeFlag` a task waits on), `extmod/modselect.c:353-370`
  (v1.29.0) calls `poll()` with `MICROPY_PY_SELECT_IOCTL_CALL_PERIOD_MS` (1 ms) even for a zero
  timeout, while rp2 builds without `MICROPY_PY_SELECT_POSIX_OPTIMISATIONS` and polls once and
  returns (:400-412). asyncio polls with a zero timeout before every task step, so each step cost the
  twin about 1 ms while a flag waited: 1.4 s of each 2 s re-plug ladder in
  `tests/test_digital_twin_hot_replug.py`, whose FRAM log writes yield once per CRC byte (measured;
  agent, 2026-10-27). Only a zero-timeout round in which every registered stream is a clear
  `ThreadSafeFlag` is skipped, the one round whose poll can report nothing; every other round takes
  the real poll; `tests/test_digital_twin_unix_port_idle_poll.py` pins which rounds those are.
  Called at module level after the prewarm and the UDP shim by the hot-replug and NTP files, each
  shown on its own rounds at both GC stages to skip only rounds whose real poll wakes nothing and
  leaves the stream map unchanged; the bus-hazard file measured no gain. It goes
  when a pin re-check finds that branch bounding its wait by the timeout.
- `unix_port_poll_prewarm.py` — a workaround for the Unix port's `extmod/modselect.c` poll-set
  growth, which corrupts a poll object registered over a non-fd stream (compiled out on rp2; the
  defect and its removal trigger: SPECIFICATION.md F.7, row 12). A known limitation, not reported
  upstream (owner, 2026-09-29); the workaround goes when a pin re-check finds the growth path fixed.
  Called in `run_generic_integration.py`'s own `main()` right after `install()` below, and at
  module level by every `tests/` entry point that boots a device with real sockets, before anything
  else in the process registers a poll object (`tests_scripts/test_twin_entry_point_order.py`
  checks every entry point). Its listener scans upward from port 17400
  across a 64-port window, a fixed row of `tests/_port_bands.py`, rather than binding one fixed port,
  and fails loudly naming the window if
  none binds: `scripts/test.sh` runs usable cores x 1-4 files at once (`TEST_PARALLELISM`
  overrides), so a fixed port made concurrent imports die
  with `EADDRINUSE` (28 of 30 concurrent prewarms; 0 of 30 with the scan), and port 0 is no
  alternative since this port has no `getsockname()`.
- `unix_port_unretrieved_report.py` — the PC tiers' asyncio exception handler: every task that ends
  raising with nobody awaiting it prints a fixed `UNRETRIEVED TASK EXCEPTION:` line and its
  traceback at every DebugLevel, then the handler releases the dead task from asyncio's context dict.
  `install()` is the first statement of every launcher's `main()` (`run_generic_integration.py`,
  `launch.py`), of `tests/microtest.py`'s `run()` and of
  `tests/_boot_contiguity_probe.py`'s `_main()`; the firmware's `start_tasks()` then keeps
  it instead of installing SYSTEM's level-gated report, so the memory gates still see a task that
  died of an exhausted heap at level 0 (SPECIFICATION.md Parts F.1 and I.4(e)).
- `network.py` / `neopixel.py` — independent, deliberately duplicated (not reused) copies of
  `tests/network.py`/`tests/neopixel.py`'s own fakes, for full runtime independence from `tests/`
  (owner, 2026-08-12). `WLAN` is one object per interface, as cyw43's are: `STA_IF` answers the
  station, any other id the access point, and `deinit()` powers the one radio down for both. A
  station connect moves through a real `STAT_CONNECTING` phase and connects after
  `_CONNECT_DELAY_S` (0.7 s), under `_poll_sta_connect_status()`'s 5 s budget, so a live run's WiFi
  polling loop never waits forever the way the
  unit-test fixture (inert, hand-driven by test code) would. It only fakes *connection
  state* — actual traffic (NTP/DNS/HTTP) goes through the real `socket` module, a genuine wrapper
  around the Unix port's own BSD sockets, reaching the host's real network through every connect
  phase (owner, 2026-08-12). A connected station reports an address in RFC 5737 TEST-NET-1
  (`192.0.2.42`, its DHCP DNS `192.0.2.1`), so no twin run reaches a public resolver; an active
  access point reports cyw43's /24 layout on the host loopback (`127.0.0.1`, the AP its own gateway),
  where every twin client is, since silicon's `192.168.4.1` would put each client off the subnet the
  captive DNS answers. `config()` truncates an AP's SSID and key as cyw43 does, and `status()`
  answers by cyw43's interface rules. Two
  twin-only knobs model what the WiFi service has to ride
  out: `set_access_point_up(up=False)` takes the home network's access point away from every
  interface object until it is switched back, and a `WLAN` object's `stations_chip_down` makes its
  hotspot's `status("stations")` answer 32 unfilled entries, as rp2 does when its radio cannot be
  brought up. `raise_on` fails a method a given number of times, `status` optionally only for one
  query, and `script_connect_outcomes()` queues connect outcomes. `NeoPixel` stores its pixels as
  micropython-lib's driver does, a GRB `bytearray`, and keeps a bounded log of written frames;
  `power_dip()` blanks what `displayed()` shows until the next `write()`.
- `_http_client.py` — minimal hand-rolled HTTP/1.1 client over `asyncio.open_connection()`: real
  HTTP over real sockets (owner, 2026-08-13; no HTTP client
  library is frozen into the pinned Unix-port build). Every response it sees is `Connection: close`
  (`asy_webserver_service.py`'s own hook), so it never needs keep-alive support. A connection
  refused at the webserver's ceiling is closed without a response byte, and the peer sees either an
  RST or a clean FIN (kernel TCP state `src/` does not choose): either raises `CeilingRefusedError`; a
  response cut short inside its head or its sized body raises `IncompleteResponseError`; both are
  `OSError` subclasses, so every caller's `except OSError` treats them as the transport failures they
  are, while a non-empty malformed status line still raises `ValueError`. `fetch()` takes a
  `timeout_s`. `.json()` checks every body with `tests/_strict_json.py` first, since the interpreter's
  own `json.loads()` accepts a missing or stray comma the browser rejects (SPECIFICATION.md Part F.1);
  the import sits inside `.json()`, so `_http_client` itself imports without `tests/` on the path;
  only `.json()` requires it.
- `unixport/` — the fake-free directory a unit test may put on its path: the UDP shim (see
  "`unixport/_unix_port_udp_addr_shim.py`" below), the NTP config writer (`_offline_ntp_config.py`)
  and the local NTP responder a booted twin syncs against (`_ntp_responder.py`, owner, 2026-10-02),
  which answers each client request on the loopback with the host's UTC time and whose test knobs
  make it silent, unsynchronised, malformed or implausible.
- `launch.py` — standalone, `src/`-free CLI demo (`micropython digital_twin/launch.py --wiring-plan
  PATH [options]`): builds the buses of the device whose plan it is given and periodically drives one
  real bus-level read per wired SCD30/SGP40/BMP3XX, a `WLAN.connect()` attempt, and WDT feeding.
  `--fault`/`--hang` drive each chip fake's existing `FaultInjector` (owner, 2026-08-12: chosen over a
  probabilistic flaky mode). Lighter and
  narrower in scope than `run_generic_integration.py` below, which boots the real object graph instead.
- `run_generic_integration.py` — boots **any** `sensortask_<device>` module (most usefully a
  freshly-`buildgen.generate.generate_device()`-generated one), for any real device, against a
  `--wiring-plan` JSON file, resolving the module via `__import__(--module)` instead of a static
  import. The single entry point every automated level drives (SPECIFICATION.md L.4) — see "Booting
  a generated device" below for the general mechanism and "Swapping the twin in" for a manual run.
  A simulated reset ends the run with exit code 3, a bootloader entry with 4 and a simulated power
  loss with 5; its `--test-*` flags are test-only instrumentation (see "Runner flags").

Every chip fake exposes `.fault`, a `FaultInjector`: `inject_fault(op, exc_type, *args, times=1,
match=None)` raises a fresh exception per call, optionally only for one command word, register or
opcode; `pending(op)` counts what is queued; `inject_hang()` is a real blocking `time.sleep()` for
simulating a genuinely wedged bus (see "Faults, hangs and modes" below), distinct from a bounded,
immediately-raised fault. Faults the rp2 port cannot produce are refused (fidelity table).
`I2C.unplug(address)`/`plug(address)` model a sensor pulled and re-seated. All of it is off/clean by
default (owner, 2026-08-12).

## Fidelity table

Every hardware fact the twin models, does not model or cannot model, grouped by class, with its
evidence and the level that proves it. Status is `fixed` with the test that pins it, an
acceptance carrying its reason and its actor's tag, or `assumption` with its BACKLOG.md
"Real-hardware work still owed" row. `D` stands for `tests/test_digital_twin_`, so `D machine::x` is
`tests/test_digital_twin_machine.py::test_x`; "L2 only" marks a property no other level proves.

| Class | Fact on silicon | Twin | Evidence | Proven at | Status |
|---|---|---|---|---|---|
| Buses | an I2C transfer takes time; `freq`, `timeout`, clock stretching, repeated start, a stuck SDA, ghost addresses | zero transaction time, none of those | — | L3, L4 | accepted (agent, 2026-10-14): an electrical verdict is the flash and bench tiers' |
| Buses | SPI baud rate, mode and a floating MISO | not modelled | — | L3 | accepted (agent, 2026-10-14): electrical, as above |
| Buses | several SPI devices share a bus through their chip selects | one device per bus id, no CS routing | the one SPI device promoted is the FRAM | L3 | accepted (agent, 2026-10-14) until a second SPI device is promoted, which adds CS routing ("Adding a new chip fake") |
| Buses | one static `I2C`/`SPI`/`UART` object per id, re-construction re-initialising it, rp2's pin pairs | the same | `ports/rp2/machine_i2c.c:80-87`, `machine_spi.c:161-167`, `machine_uart.c:469` | L2 | fixed: `D machine::i2c_is_one_object_per_id_keeping_chips_and_log_across_constructions`, `D machine::spi_is_one_object_per_id_that_each_construction_reinitialises`, `D machine_uart::a_second_construction_on_one_bus_id_returns_the_same_live_object` |
| Buses | `Pin` ids 0-29, the Pico W board and CPU names, pulls cleared on re-configuration, open-drain and alternate-function modes | the same, plus a scripted external line level | `boards/RPI_PICO_W/pins.csv`, `machine_pin.c` | L2 | fixed: `D machine::pin_takes_rp2s_ids_and_names_as_one_object`, `D machine::pin_reconfigured_without_a_pull_loses_it`, `D machine::pin_open_drain_reads_the_wired_and_of_its_drive_and_the_line` |
| Buses | a NAKed zero-length probe raises `ENODEV`, a NAKed data write `EIO`; `scan()` never raises | the same | `machine_i2c.c:127-145`, `extmod/machine_i2c.c:199-203` | L2 | fixed: `D machine::i2c_an_empty_write_to_an_absent_address_reads_enodev_a_data_write_eio` |
| Buses | the general call reaches the chips that listen to it | the SGP40 resets; the other fakes ignore it | SGP40 datasheet Table 17 | L2 | fixed: `D machine::i2c_a_general_call_reaches_only_the_chips_that_listen`, `D sgp40::a_general_call_reset_clears_the_pending_reply_and_counts_one_reset` |
| Buses | whether the other chips ACK or NAK a general call | ignored without a NAK | no datasheet states it | — | assumption: BACKLOG "Whether the chips other than the SGP40 ACK or NAK a general call" |
| Buses | SPI `MSB` 1, `LSB` 0, LSB-first refused | the same | pico-sdk `hardware/spi.h:184-187` | L2 | fixed: `D machine::spi_bit_order_numbers_are_rp2s`, `D machine::spi_init_updates_settings_and_rejects_lsb_first` |
| Buses | an SPI RX overrun only on a read of 32 bytes or more (the DMA path); a write never raises | the same; a write fault is refused | `machine_spi.c` `dma_min_size_threshold` | L2 | fixed: `D fram::readinto_fault_fires_only_on_a_long_read`, `D fram::write_fault_injection_is_refused` |
| Buses | a read fills the caller's buffer, never shrinks it | the same | — | L2 | fixed: `D machine::i2c_reads_fill_the_callers_buffer_whatever_its_type` |
| Buses | UART framing, `txdone()` | wire time counts 10 bits a byte (8N1) whatever framing is set; `txdone()` always `True` | — | L3 | accepted (agent, 2026-10-14): the link delivers at once; L3 `uart_crossover_*.py` |
| Buses | UART receive: the RX interrupt, a DMA channel or the 32-byte FIFO with OE on overflow, by wire time; `ioctl()` answers `EINVAL` but to POLL | the same | `machine_uart.c:163-176, 694-697` | L2 | fixed: `D machine_uart::delivery_takes_real_wire_time`, `D machine_uart::the_dma_keeps_filling_the_ring_through_a_flash_stall`, `D machine_uart::ioctl_answers_einval_to_get_fileno` |
| Buses | UART init takes rp2's keywords only | an unknown keyword raises `TypeError` | `machine_uart.c` | L2 | fixed: `D machine_uart::init_refuses_a_keyword_rp2_does_not_take` |
| Buses | a NeoPixel `write()` busy-waits for the bit stream | returns at once | — | L3 | accepted (agent, 2026-10-14): timing only, no state |
| Buses | NeoPixel stores GRB bytes; `__setitem__` writes per component | the same | micropython-lib `neopixel.py:9` | L2 | fixed: `D network_neopixel::neopixel_stores_bytes_in_grb_order_as_the_library_does` |
| Chips | the SGP40 takes time per command; compensation shifts the raw signal | neither | — | L3 | accepted (agent, 2026-10-14): the driver waits its datasheet delays regardless |
| Chips | the SGP40's heater-off returns it to idle | the same | SGP40 datasheet | L2 | fixed: `D sgp40::heater_off_clears_the_pending_measure_reply_and_the_next_measure_answers` |
| Chips | the SGP40's reaction to an unknown command | ignored, the pending reply kept | the datasheet states none | — | assumption: BACKLOG "The SGP40's reaction to an unknown command" |
| Chips | the SCD30 measures nothing before continuous measurement starts; soft reset is a power-up; the FRC readback is volatile | the same; the twin starts provisioned (measuring), not datasheet-derived | Interface Description 1.4.1-1.4.6 | L2 | fixed: `D scd30::an_unprovisioned_chip_measures_nothing_until_started`, `D scd30::a_soft_reset_drops_the_unread_measurement_and_the_frc_reference`, `D scd30::the_forced_recalibration_reference_reads_back_the_last_one_until_a_power_up` |
| Chips | the SCD30's reaction to a wrong argument CRC, an interval outside 2-1800 s or an FRC outside 400-2000 ppm | ignored and counted | the datasheet states none | — | assumption: BACKLOG "The SCD30's reaction to a wrong argument CRC or an out-of-range interval" |
| Chips | whether the SCD30's 0x0010 ambient-pressure value itself persists in NVM | persisted | Interface Description 1.4.1 names only the measuring status | — | assumption: BACKLOG "Whether the SCD30 keeps the ambient pressure across a power cycle" |
| Chips | the SCD30's 0x0010 overrides altitude compensation | not modelled | Interface Description 1.4.1 | — | accepted (agent, 2026-10-14) until a driver depends on it |
| Chips | the SCD30's temperature offset shifts the reported RH | RH reported as walked | no datasheet gives the formula | — | accepted (agent, 2026-10-14): no invented RH model |
| Chips | the SCD30's NVM writes | counted per NVM command the fake carries out | — | L2 | a test surface, not chip behaviour: `D scd30::nvm_writes_counts_each_accepted_nvm_command_and_nothing_else` |
| Chips | the BMP3XX chip id: 0x60 (BMP390), 0x50 (BMP384, BMP388) | 0x60 only | DS001-DS003 §4.3.1 | L3 | accepted (agent, 2026-10-14): the driver accepts both |
| Chips | the BMP3XX calibration block is factory-trimmed | synthetic, round-tripping through the real compensation formula | `D bmp3xx::calibration_block_is_not_degenerate` | — | accepted (agent, 2026-10-14) until the real block is read: BACKLOG "The BMP3XX's real calibration block" |
| Chips | a BMP3XX conversion takes time; 0xB6 resets OSR and CONFIG | no conversion time; the reset as on silicon | DS001 | L2, L3 | fixed for the reset: `D bmp3xx::power_cycle_restores_the_power_up_registers_and_keeps_the_walk`, `D bmp3xx::soft_reset_command_restores_command_ready_status`; conversion time accepted (agent, 2026-10-14), L3 |
| Chips | ISL29125 lux response | linear, with a deliberately non-nominal high-range ratio a calibration converges on | SPECIFICATION.md M.1.5 | L2 | accepted (agent, 2026-10-14): a test needs a ratio to converge on |
| Chips | the ISL29125 PRST counter stops at its target | the same | FN8424 | L2 | fixed: `D isl29125::prst_count_stops_at_the_target` |
| Chips | whether a CONFIG1 write restarts an in-flight ISL29125 conversion | restarted, never tuned to | FN8424 Table 7 says only "ADC start at I2C write 0x01" | — | assumption: BACKLOG "Whether a CONFIG1 write restarts an in-flight ISL29125 conversion" |
| Chips | the FRAM frames a transaction by CS | by `write()` pairing; opcode, address and data in one `write()` refused | `asy_fram_driver.py` sends them in separate calls under one CS | L2 | accepted (agent, 2026-10-14): a driver merging them would lose the data, so the fake raises |
| Chips | the FRAM's address wraps at its end | the same | MB85RS datasheets | L2 | fixed: `D fram::a_write_across_the_last_address_wraps_to_address_zero` |
| Chips | the MB85RS2MTA (`dev`) keeps WEL set after a WRITE or WRSR (continual programming); the MB85RS64V clears it | WEL cleared at every WRITE and WRSR, the MB85RS64V's behaviour, on every chip size | DS501-00032-3v0-E p.6, DS501-00015-4v0-E p.6 | L2 | accepted (agent, 2026-10-27): the driver's WRDI epilogue clears WEL on both parts, and `stick_next_wrdi` plants the WEL a lost WRDI leaves on the MB85RS2MTA |
| Chips | a chip's value ranges | inside its datasheet's ranges; each walk step says "not datasheet-derived" | each fake's constants | L2 | fixed: `D scd30::default_ranges_stay_inside_the_datasheets_own_documented_ranges`, `D sgp40::measure_raw_default_range_stays_inside_the_sgp40_datasheets_own_tick_range` |
| Chips | a chip re-plugged mid-run powers up | `I2C.unplug()`/`plug()` and each chip's `power_cycle()` | — | L2 only (L4 manual step owed, F.2) | fixed: `D hot_replug::every_bus_attached_driver_recovers_from_a_replug_without_a_reboot`, `D machine::an_unplugged_chip_answers_nothing_until_plugged_back_powered_up` |
| Runtime | a soft `Timer` callback runs from rp2's scheduler queue, dropped when its 8 entries are full; a hard callback runs in the IRQ | an asyncio task on a wall-clock schedule: no pre-emption, no queue, no drop of its own (the row below), no exact period while the loop is blocked | `ports/rp2/mpconfigport.h:131`, `shared/runtime/mpirq.c:105` | L3, L4 | accepted (agent, 2026-10-14) while every product Timer callback stays trivial; `scheduler_saturation_drop.py` (L3, `flash/test_bus_electrical_timing.py`) is a silicon-only exception in the twin record, since a synchronous script gives the twin's Timer tasks no turn |
| Runtime | a soft `Timer` callback is dropped while the depth-8 scheduler queue is full: `mp_sched_schedule()`'s refusal is ignored, a PERIODIC alarm re-arms, a ONE_SHOT is lost | dropped only when a test sets `Timer.drop_next_soft_callbacks`: the next N soft callbacks of any Timer, a hard one never | `shared/runtime/mpirq.c:105`, `ports/rp2/machine_timer.c:50-60`, `py/scheduler.c:163-181`, `ports/rp2/mpconfigport.h:131` (v1.29.0) | L2 | fixed: `D machine::a_periodic_timer_fires_again_after_its_soft_callbacks_are_dropped`, `D machine::a_dropped_one_shot_never_fires_and_frees_its_alarm_while_a_hard_callback_is_never_dropped` |
| Runtime | rp2's 16-alarm pool, `OSError(ENOMEM)` past it; a raising soft callback keeps its alarm, a hard one stops it | the same | pico-sdk `pico/time.h:352-362`, `py/scheduler.c:115`, `machine_timer.c:50-60` | L2 | fixed: `D machine::the_seventeenth_alarm_raises_enomem_until_one_is_freed`, `D machine::a_soft_callback_failure_is_printed_and_the_schedule_goes_on`, `D machine::a_hard_callback_failure_stops_the_schedule_and_frees_its_alarm` |
| Runtime | the finaliser disarms an unreferenced armed Timer | not modelled: the twin's task keeps the Timer referenced | `machine_timer.c:115-116, 161-163` | L1, L3 | accepted (agent, 2026-10-14): L1 fake-clock tests and L3 `timer_alarm_pool_exhaustion.py` |
| Runtime | a Pin IRQ runs from the interrupt | synchronously in the caller | — | L3 | accepted (agent, 2026-10-14) |
| Runtime | `machine.reset()`/`bootloader()` end the program | `SimulatedRebootError`, a `BaseException`, ends the loop; the runner exits 3 or 4 | — | L2 | fixed: `D machine::a_reset_and_a_power_loss_are_no_exceptions_a_product_can_swallow`, `D machine::a_timer_calling_reset_ends_the_loop_past_an_except_exception_sibling` |
| Runtime | `mem_backup()` regions survive a reset and clear at power-on; `reset_cause()`; a console soft reset keeps both regions and the last hard reset's cause | the same, carried to the next launch through a state file; a soft reset is a launch that keeps both | `machine_mem_backup.c:36-40` | L2 | fixed: `D machine::the_twin_meets_the_shared_mem_backup_contract` (`tests/_mem_backup_contract.py`), `D machine::a_flushed_mem_backup_reaches_the_next_launch_once`, `D loop_end::a_console_soft_reset_after_ctrl_c_reads_21` |
| Runtime | whether `reset_usb_boot()` keeps the scratch registers, and the cause read after BOOTSEL | kept; a watchdog reset | the bootrom is not in the pinned source | — | assumption: BACKLOG "`mem_backup()` and `reset_cause()` after a BOOTSEL round trip" |
| Runtime | the WDT resets the chip | records a would-have-reset and never resets; the runner prints `WATCHDOG_WOULD_TRIGGER` | — | L2 | accepted (owner, 2026-08-12); a reset code reached only through a real watchdog reset is L1's and the bench's |
| Runtime | the RTC takes no constructor argument, an 8-tuple, recomputes the weekday, its setter returns `None`; a set moves `time.time()` | the same with the runner's wall clock installed; uninstalled it holds a fixed tuple | `machine_rtc.c:52, 64-97`, `ports/rp2/modtime.c:31-43` | L2 | fixed: `D machine::an_installed_clock_makes_an_rtc_set_move_the_wall_clock`, `D machine::an_uninstalled_rtc_keeps_its_tuple_by_rp2s_rules` |
| Runtime | a flash write holds the loop with interrupts off | a config flush stalls the loop for its pages' erase and program time | `rp2_flash.c:167-173` | L2, L3 | fixed: `D machine_uart::a_config_flush_through_the_installed_open_stalls_once_for_its_pages` |
| Runtime | power lost at any instruction | lost after the k-th SPI transaction, never mid-byte | — | L2 (mid-byte: L3 `fram_reset_race_*`) | fixed: `D machine::spi_lose_power_after_k_fails_the_next_transaction_with_a_power_loss`, `tests/test_digital_twin_fram_crash_points.py` |
| Runtime | `ticks_ms()` wraps at 2**30 ms | never reached (the Unix port's period is 2**62) | — | L1 | accepted (agent, 2026-10-14): the wrap proofs are L1 fake-clock tests |
| Runtime | `time.time()` an int, the RTC TZ-free | a float, `TZ=UTC` | SPECIFICATION.md F.7 | — | accepted (agent, 2026-10-14) |
| Runtime | a 32-bit heap of frozen code | a 64-bit heap of source-loaded code | — | L3, L4 | accepted (agent, 2026-10-14): a heap figure here is a tripwire only |
| Runtime | the largest free block after the built graph | not the silicon's: the Unix port keeps every module's bytecode and the fakes' state in its GC heap (about 1.2 MB live after the `dev` load, against the board's 88 KB built graph), in 32-byte blocks | the shutdown line's GC summary and `gc_block_bytes` | L3 | accepted (agent, 2026-10-15): the twin's figure is a tripwire only; the board's is `tests_hardware/device_scripts/heap_headroom_after_full_system_build.py` |
| Runtime | every rp2 constant the twin models | pinned to its cited source line | v1.29.0 | L2 | fixed: `tests/test_digital_twin_rp2_constants.py` |
| Network | the radio and lwIP carry the traffic: TCP PCBs, the pbuf pool, `MEM_SIZE`, TIME_WAIT, the backlog, the `ERR_MEM` send path (B.14) | the host's Linux stack carries it; `WLAN` fakes connection state only, the Pico W the only modelled board (owner, 2026-09-26) | — | L4 | accepted (agent, 2026-10-14): every connection-ceiling, hotspot and load verdict is L4's |
| Network | CYW43 `isconnected()` false positives, spontaneous link loss, DHCP, config validation | not modelled | — | L4 | accepted (agent, 2026-10-14) |
| Network | a STA connect passes through `STAT_CONNECTING` inside the service's 5 s budget | 0.7 s | `network.py` `_CONNECT_DELAY_S` | L2 | fixed: `D network_neopixel::one_connect_phase_fits_the_services_poll_budget` |
| Network | the AP reports an address and `STAT_GOT_IP`, shares lwIP's one DNS server with STA, truncates its SSID and key | the same, with cyw43's /24 layout on the loopback (`127.0.0.1`), where every twin client is | `cyw43_config.h:194, 206`, `extmod/network_lwip.c:70-73`, `cyw43.h:431-448` | L2 | fixed: `D network_neopixel::the_access_point_comes_up_with_its_address_and_the_shared_dns`, `D network_neopixel::config_truncates_as_cyw43_and_reads_the_essid_back` |
| Network | `status("rssi")` off STA and `status("stations")` off AP raise; one object per interface; `deinit()` powers the one radio down | the same | `extmod/network_cyw43.c:96-103, 133-137, 363-392` | L2 | fixed: `D network_neopixel::status_answers_by_cyw43s_interface_rules`, `D network_neopixel::one_wlan_object_per_interface_any_other_id_the_access_point`, `D network_neopixel::deinit_powers_the_one_radio_down` |
| Network | the home network's access point goes away | `set_access_point_up(up=False)`, a twin-only knob: a joined link, addressed or not, drops to `STAT_CONNECTING` (cyw43's LINK_JOIN) and keeps its address, the device's own AP stays up, and the link stays down until the next `connect()` (no firmware rejoin is modelled); a completed connect ends `STAT_NO_AP_FOUND` | `cyw43_ctrl.c:402-413, 434-437, 613-617`, `cyw43_lwip.c:296-298` | L2 | fixed: `D network_neopixel::a_downed_access_point_fails_the_station_until_switched_back`, `D network_neopixel::a_joined_link_with_no_address_holds_status_two` |
| Network | `connect()` on an inactive STA (never activated, deactivated, or after the radio's `deinit()`) raises `OSError(EPERM)`, before the key check | the same | `cyw43_ctrl.c:637-640`, `extmod/network_cyw43.c:308-311` | L2 | fixed: `D network_neopixel::connect_on_an_inactive_station_raises_eperm` |
| Network | deactivating the STA leaves the network and takes its netif down with its DHCP: unlinked, unaddressed, a pending connect gone; a link that was joined reads `STAT_CONNECTING` (cyw43's LINK_JOIN) until the DISASSOC event clears the join state | the same, but `STAT_IDLE` at once: a simplification of the twin | `extmod/network_cyw43.c:146-149`, `cyw43_ctrl.c:353-355, 579-582, 666-669`, `cyw43_lwip.c:251-254, 267` (cyw43-driver v1.1.1, as pinned at v1.29.0) | L2 | fixed: `D network_neopixel::deactivating_the_station_drops_its_link_its_address_and_a_pending_connect`; the instant `STAT_IDLE` accepted (agent, 2026-10-21): no product path reads `status()` between `active(False)` and `deinit()` (`asy_wifi_service.py`'s mode switch) |
| Network | a hotspot's stations query with the radio down answers 32 entries | 32 one-element tuples of 6 zeroed bytes (silicon leaves them unfilled; the service reads only the count), a twin-only knob | `extmod/network_cyw43.c:371-388` | L2 | fixed: `D network_neopixel::a_chip_down_stations_answer_is_32_unfilled_entries` |
| Network | a UDP send reaches any address | the UDP shim refuses any destination outside loopback, 0.0.0.0 and TEST-NET-1 through the product's own failure path and counts it | — | L2 | fixed: `D ntp::a_public_destination_is_refused_counted_and_fails_on_the_products_own_path` |
| Network | an NTP server on the unit's network | the local responder on the loopback | RFC 5905 | L2 | fixed: `D ntp::a_booted_device_syncs_at_its_first_sync_with_a_clean_log` |
| Persistence | every SCD30 and FRAM a device wires keeps its own state | only the last-wired SCD30 and FRAM instance persist (one module-global handle each) | — | L2 | accepted (agent, 2026-09-13) while only the two synthetic fixtures wire several; the change wiring a second real instance adds per-instance persistence: `D generic_wiring::flush_scd30_persists_only_the_last_constructed_chip` |
| Fault surface | a bus fails in many shapes | one generic op-keyed `FaultInjector` queue, not a per-condition simulator, plus the FRAM chip's latch and data knobs (`drop_next_wren`, `stick_next_wrdi`, `corrupt_next_write`) | — | L2 | accepted (agent, 2026-10-14) for the queue; the FRAM write defences fixed (agent, 2026-10-27): `D fram::a_latch_one_wrdi_leaves_set_clears_on_the_retry_and_a_stuck_one_warns_once_per_event_with_the_payload_landed`, `D fram::a_verified_write_the_chip_stored_wrong_fails_once_rewrites_nothing_and_the_next_write_heals` |
| Fault surface | the port raises only certain faults | faults it cannot produce are refused | — | L2 | fixed: `D fram::write_fault_injection_is_refused`, `D launch::parse_fault_spec_has_no_fram_write_fault` |
| Fault surface | no rp2 bus call raises a stack overflow | `--fault DEVICE:OP:stack` queues one, a twin-only knob proving the reboot path | `py/runtime.c:1786` | L2 only | fixed: `D launch::a_stack_fault_raises_one_stack_exhaustion_on_the_chips_next_read` |
| Fault surface | the FRAM chip's writes | `write_count`/`writes_at`, a test surface, not chip behaviour | — | L2 | a test surface: `D fram::payload_writes_are_counted_by_address` |
| Runtime | the watchdog counts down in hardware, whatever the program does | the countdown is a task on the runner's loop, so it dies with that loop: a runner-cancelled `main()` keeps the loop and the countdown alive | `ports/rp2/machine_wdt.c` | L2 | accepted (agent, 2026-10-26): `--test-watchdog-fault main-exit` cancels only `main()`, the scenario harness's `watchdog_fault_main_exit` |

The twin's `machine` fake meets the same contract as the unit tier's (`tests/_machine_contract.py`,
`D machine::the_twin_meets_the_shared_machine_contract_but_for_its_pending_checks`), and every rp2
constant it models is pinned by `tests/test_digital_twin_rp2_constants.py`.

## Swapping the twin in for a Unix-port run

A device's generated `sensortask_<device>.py` (built fresh by `buildgen` from its own TOML — no static
copy is committed any more, SPECIFICATION.md Part L.2) needs **zero
twin-awareness** — no `if` branch anywhere distinguishing real hardware from simulated. The swap is
pure `MICROPYPATH` ordering, the same mechanism `tests/machine.py` already uses transparently for
the unit-test suite. `run_generic_integration.py` also drives real HTTP over real sockets against
the real `WebserverService` — never Microdot's `app.dispatch_request()` bypass, the same "full
HTTP" standard the real system meets. The dedicated entry point, `scripts/run_unix_port_integration.sh`,
does exactly this for any real device, named by its required `--device` (without it the script prints its
usage and the valid device names and exits 2):

```bash
scripts/run_unix_port_integration.sh --device <device>                        # just launch + serve forever
scripts/run_unix_port_integration.sh --device <device> --fault sgp40:writeto  # manual fault-injection exploration
```

Under the hood (builds the toolchain, generates every device's `sensortask_<device>.py` +
`sensortask_<device>_wiring_plan.json` into `build/generated_src/` via
`scripts/_generate_sensortask_modules.py` — see "Booting a generated device" below for the general
mechanism this is built on — then builds the real website for the chosen device into
`frozen_modules/frozen_html.py` via `scripts/build_website.sh <device>`, matching what a real
deployed unit serves — then runs
`digital_twin/run_generic_integration.py --module sensortask_<device> --wiring-plan
build/generated_src/sensortask_<device>_wiring_plan.json --device <device>` — the real orchestrator,
not the generated boot entry (`sensortask_<device>_main.py`) directly, since it also needs to drive
the fault-injection/`--duration`-forever logic around `<module>.main()`, not just block on it), on
the twin layout of `scripts/micropypath.toml` (`micropypath twin` of `scripts/_unix_port.sh` prints
it; the runner puts `digital_twin/unixport` on its own path):

```bash
MICROPYPATH="build/generated_src:src:digital_twin:ext:frozen_modules:.frozen" <micropython-unix-port-binary> digital_twin/run_generic_integration.py --module sensortask_<device> --wiring-plan build/generated_src/sensortask_<device>_wiring_plan.json --device <device> [flags]
```

`build/generated_src` is listed first so `import sensortask_<device>` resolves to the freshly
buildgen-generated module, not any same-named file that might otherwise be found later on this
path — no static `src/sensortask_<device>.py` exists any more. `frozen_modules` is required here too
(see `SPECIFICATION.md` Part A.9 for the full pipeline) — the generated module does an
unconditional module-level `import frozen_html`, which resolves from that segment (see
`scripts/build_frozen_html.sh`'s own comment for why it can't be `.frozen` itself). Omitting it
fails the run at import time with `ImportError: no module named 'frozen_html'` before any twin code
ever runs. `digital_twin` sits between `src` and `frozen_modules`/`.frozen` — never together with
plain `tests` on the same `MICROPYPATH` (that would let `tests/machine.py`/`tests/network.py`/
`tests/neopixel.py` shadow this package's own same-named modules, or vice versa, depending on
ordering — the two are meant to never be on the same path at once). This is a **separate**
invocation from `scripts/test.sh`'s own unit layout (the same file's `unit` entry) —
`scripts/run_unix_port_integration.sh` is not part of `scripts/test.sh`'s own default
`tests/test_*.py` glob loop (it can run forever in `--duration`-omitted/manual mode, which would
hang that loop if it were discovered there instead).

`digital_twin/run_generic_integration.py` reuses `launch.py`'s fault, hang and WiFi-outcome parsers
directly (the same vocabulary). A manual run keeps its state in `digital_twin/` across runs
(owner, 2026-08-13: "a persistent file inside digital_twin/"): the FRAM image, the SCD30's NVM and
the watchdog scratch registers in `digital_twin/fram_state.json`, `digital_twin/scd30_state.json` and
`digital_twin/mem_backup_state.json`, the product's config in `digital_twin/config/`; an automated
caller passes its own per-run paths, or `""` to keep a chip in memory. By default the run writes an
NTP config pointing at the local responder it starts, so the device syncs without leaving the host
(`--online-ntp` turns both off). Defaults to `--host localhost --port 8080` (browser-reachable). A
bare, no-flags run just launches the real object graph and serves forever, the same as a real rp2040
boot would. There is no `--soak` flag: the automated HTTP+memory-trend soak check is host-side
(SPECIFICATION.md's "Driver/DUT process separation" Part): the twin only exposes the one
piece of itself a host-side driver cannot get as a stream, `gc.mem_free()` (`/status`'s `MemFree`
is one poll's reading), via the opt-in `--mem-sample-interval-ms N` flag (prints
`MEM_SAMPLE <time.ticks_ms()> <gc.mem_free()>` lines to its own stdout on that cadence; unset by
default, no sampling). `--stop-file PATH` makes
`--duration` an upper bound: the run ends as soon as `PATH` exists, on the same clean path a finished
duration takes (`tests_scripts/test_digital_twin_generated_boot.py` writes it once its smoke loop is
done, rather than idling out the bound) (agent, 2026-10-08). See "Runner flags" below for every flag,
and `scripts/_digital_twin_ci_suite.py`'s Run 11 (`_run_11_soak()`) for the actual soak methodology —
a plain host-side HTTP-cycling loop parsing those `MEM_SAMPLE` lines back out of the twin's
captured log, the same pattern `_would_have_triggered_count()` already used for the watchdog
counter.

A second, lighter integration tier also exists:
`tests/test_digital_twin_sensortask_integration.py` builds the device's real object graph
against the real twin buses, one Unix-port process per generated device (`PER_DEVICE = True`), but
only ever starts the specific tasks each test needs and never runs the generated `main()` (its
supervisor tests drive `start_tasks()`/`supervise_tasks()` themselves and cancel what they started);
it drives no HTTP itself — every request-driving scenario runs host-side, in
`scripts/_digital_twin_scenarios.py` (SPECIFICATION.md E.9). It runs under `scripts/test.sh`'s own
default loop like any
other test file (via the same per-file `sys.path.insert(0, "digital_twin")` trick every other
`tests/test_digital_twin_*.py` file already uses), giving fast, everyday regression coverage of the
twin wiring without needing the separate `MICROPYPATH` invocation above.

`tests/test_digital_twin_wifi_modes.py` is the same tier for the Wi-Fi modes: one boot of a
generated device's real graph, the first plan wiring a neopixel and a FRAM, walks the Wi-Fi modes
after a hotspot ran (the stations rule, a settings change landing in the fresh-boot state, the
silent mode and its later link) with the WiFi service's own sleeps scaled down, in a file of its own
for that wall time.

### Booting a generated device

`run_generic_integration.py` boots **any** device by consuming a
`buildgen.generate.generate_device()`-generated module directly, with the wiring plan derived from
that device's own TOML (SPECIFICATION.md Part L.4 has the full design account). Two things have to
be produced **host-side, in a plain CPython process**, before this file's own MicroPython process can
even start — `buildgen` needs `tomllib`, which the MicroPython Unix port doesn't have:

```python
from pathlib import Path
import json
from buildgen.generate import generate_device
from buildgen.twin_wiring import compute_twin_wiring

generated = generate_device(Path("tests_scripts/buildgen_fixtures/novel_combo.toml"), Path("src"), Path("ext"))
# In tests_scripts/buildgen_fixtures/ for the two synthetic fixtures - devices/ for a real one.
Path("/tmp/twin_boot/sensortask_novel_combo.py").write_text(generated.module_source)
Path("/tmp/twin_boot/wiring_plan.json").write_text(json.dumps(compute_twin_wiring(generated.model)))
```

(`uv run scripts/_generate_sensortask_modules.py --device-toml PATH --out-dir DIR` does the same for
one TOML.) Then the MicroPython process, with the generated module's own directory placed **first** on
`MICROPYPATH` (so `import sensortask_novel_combo` resolves to the freshly-generated file, not any
same-named file that might otherwise be found elsewhere on this path — every real device is
generated exactly the same way; no device has a hand-written
`sensortask_<device>.py` any more, SPECIFICATION.md Part L.2. `scripts/test.sh`/
`scripts/run_unix_port_integration.sh`/`scripts/run_digital_twin_ci.sh` all generate into the fixed
`build/generated_src/` directory via `scripts/_generate_sensortask_modules.py` rather than a fresh
temp directory per run, so every device's module exists at a
predictable path before any test file runs; every other import the generated module itself needs,
e.g. `asy_i2c_driver`, still falls through to `src/`):

```bash
MICROPYPATH="/tmp/twin_boot:src:digital_twin:ext:.frozen" <micropython-unix-port-binary> \
    digital_twin/run_generic_integration.py --module sensortask_novel_combo \
    --wiring-plan /tmp/twin_boot/wiring_plan.json --device novel_combo --host 127.0.0.1 --port 8080
```

The runner stands in for the device's boot entry: it arms the twin `WDT` with the entry's own
timeout (`_WDT_TIMEOUT_MS`, 8000 ms, a mirror, since the twin cannot import `buildgen/`) and passes it
as `main(watchdog=..., cfg_path=..., web_host=..., web_port=...)`. The generated `main()` then runs
the whole boot sequence itself - `build_system()` (construction only), the setup list through
`run_setups()`, the task starters, the timers, `ntp_force_sync()` and the supervisor - while the
runner waits for `build_system()`'s last global (`webserver`) and then wires the UART jumper and any
faults. Before the module loads it installs its wall clock into the product modules and its flash
stall under `asy_config_manager`. Its shutdown line reads `would_have_triggered_count` off that same
`WDT`; the generated module keeps no watchdog global.

`tests_scripts/test_digital_twin_generated_boot.py` does exactly this (via `subprocess.Popen`, the
same pattern `scripts/_digital_twin_ci_suite.py` uses) for every real device plus both mandatory
synthetic fixtures (`novel_combo.toml`, `multi_instance.toml`), asserting a real `GET` against five
real REST endpoints all return 200 — the first point a generated module is actually *run*, not just
`ast.parse()`d. `run_generic_integration.py`'s own fault/hang chip lookup (`_collect_chips()`) walks
the same wiring plan `configure_wiring()` was given and reaches each chip through
`machine.peripheral()`, never through a product wrapper's private attribute.

`launch.py` stays a `src/`-free raw-bus-read demo, for the different, static-demo use case its own
module docstring gives (no `sensortask_*` import at all).

`compute_twin_wiring()`'s plan (`TwinWiringPlan`: `device`, `buses`, `spi`, `pins`, `uart`,
`instances`) carries an optional `"uart"` key (`{"initiator_bus", "responder_bus"}`, the two
generated UART bus globals, each named after its `[bus.<id>]` table — `None` for any device with no
`uart_link` pair) alongside `"buses"`/`"spi"`. Unlike those two, this key is consumed *after*
construction, not by `machine.configure_wiring()` itself: `_wire_uart_crossover()` (called from
`main()` right after `_wait_until_built()`) reads the two already-built `asy_uart_driver.UART` buses
off the booted module by name, joins their underlying `machine.UART` fakes with
`attach_crossover_jumper()`, and swaps in the returned bounded `LinkPoller`s. `"pins"` holds every
`[bus.<id>]` table's wire pins by role.

### Runner flags

`run_generic_integration.py --help` prints the list; each flag's default and effect:

| Flag | Default | Effect |
|---|---|---|
| `--module NAME` | required | the generated `sensortask_<device>` module to boot |
| `--wiring-plan PATH` | required | its wiring-plan JSON |
| `--device LABEL` | the module name | the device name the log lines carry |
| `--host HOST`, `--port N` | `localhost`, `8080` (owner, 2026-08-13) | where the webserver listens |
| `--config-dir PATH/` | `digital_twin/config/` | the product's config directory; refused without its trailing `/`, since each config file's name is that path plus `config_<name>.cfg` (`config_filename()` in `src/asy_config_manager.py`) |
| `--debug-level N` | off, as on the device | every logger built at level N, until the stored `DebugLevel` applies; a level `PrintLog.set_level()` refuses is refused |
| `--fram-state-path`, `--scd30-state-path`, `--mem-backup-state-path PATH` | `digital_twin/fram_state.json`, `scd30_state.json`, `mem_backup_state.json` | where that state persists; `""` keeps it in memory |
| `--online-ntp` | off | off: the local NTP responder runs and the config pointing at it is written; on: neither, the stored config is used |
| `--seed N` | none | seeds every chip's random walk |
| `--fault DEVICE:OP[:TIMES[:MATCH]]` | none | see "Faults, hangs and modes" |
| `--hang DEVICE:OP:SECONDS[:TIMES]` | none | see "Faults, hangs and modes" |
| `--wifi-outcome OUTCOME` | none | queues a `WLAN.connect()` outcome: `success`, `no_ap`, `wrong_password`, `connect_fail` |
| `--duration SECONDS`, `--stop-file PATH` | serve forever | stop after this long, or once the file exists |
| `--gc-threshold N` | `32768` | `gc.threshold()` for the run, as the firmware boot entry sets it |
| `--mem-sample-interval-ms N` | off | print a `MEM_SAMPLE` line every N ms |

Test-only instrumentation (owner, 2026-09-30), every flag off by default and absent from the
product's entry path (`tests_scripts/test_twin_runner_test_flags.py`), each printing the line the
host-side harness reads:

| Flag | Prints | Effect |
|---|---|---|
| `--test-hold-closing-slot` | `SLOT_HELD`, `SLOT_RELEASED` | each closed connection holds its slot until a `SLOT_RELEASE` line arrives on stdin |
| `--test-stall-loop-ms N` | `STALL` | a `STALL_TRIGGER` line on stdin stops the whole loop for N ms |
| `--test-conn-status-interval-ms N` | `CONN_SLOTS open=<n> backlog=<n>` | the connection gauge every N ms |
| `--test-fault-status-interval-ms N` | `FAULT_PENDING ...` | each chip's queued faults every N ms |
| `--test-shutdown-hang STEP` | `HANG <step>`; for S1 also `HUNG S1` | the controlled shutdown's step S1, S2, S3, S4, S5reset, S5erase or S6 never completes, so only the watchdog ends it; `HUNG S1` comes when the rebound dead-task report is first entered |
| `--test-flash-stall-max` | — | every flash stall at its datasheet maximum |
| `--test-uart-over-cap` | `UART_OVER_CAP <key> sent\|refused` | per initiating `uart_link`, right after its next transfer, one stream of the link's cap plus one byte, which the protocol refuses before its first frame and logs |
| `--test-hold-system-entry ERRNO[:cut]` | `ENTRY_HELD`, `ENTRY_RELEASED` | SystemService's logger holds its entry with that errno (the supervisor's escalation entry) until an `ENTRY_RELEASE` line arrives on stdin; the service's bounded wait on that entry starts at the release, so the hold never counts against its bound. With `:cut` the entry's real write starts and is held inside its first FRAM block, after that block's busy mark, never released: the bound counts the hold and its cancel cuts the block, as a write that never finishes would (no `ENTRY_RELEASED`) |
| `--test-loop-lag-ms N` | `LOOP_LAG max_us=<n> p99_us=<n> samples=<n> <link key>=<transfers> ...` | a task sleeping N ms at a time records each wake's overshoot; one line per 5 s window, that window's figures alone (SPECIFICATION.md Part F.3's `lag.loop`), ending with each wired `uart_link`'s transfers so far, one `<link key>=<transfers>` per link |
| `--test-drop-timer-fire reset\|sequencer` | `DROP_ARMED <site>`, `FIRE_DROPPED <site> callbacks=<n>` | the twin's soft-callback drop is set before that one-shot's arm and cleared once its fire was dropped, as rp2's full scheduler queue loses it (SPECIFICATION.md Part F.1) |
| `--test-kbd-traceback` | `KBD_CAPTURED <bool>`, `KBD_TRACEBACK` | the interpreter's one `KeyboardInterrupt` object, caught at start through a SIGINT to itself; a `KBD_TRACEBACK` line on stdin prints where the newest interrupt was raised |
| `--test-watchdog-fault supervisor-raise\|main-exit\|block` | `WDT_AT_FAULT <feed_count>` | after the supervisor's first feed, one fault that ends the feeding: the dead-task report raises as a task ends, the product's `main()` is cancelled, or the whole loop blocks past the watchdog timeout |
| `--test-defer-faults` | `FAULTS_ARMED` | every `--fault` is held back until a `FAULT_ARM` line arrives on stdin, then queued at once, so the boot meets none of them and a fault matching a read the boot shares reaches only what runs after it; a later `FAULT_ARM` queues nothing more |
| `--test-pin-send-buffer` | `SNDBUF_PINNED bytes=<n> accepted_bytes=<n>` | each socket the server accepts has its send buffer set to the kernel's floor (socket(7): a request is doubled, then clamped) before it is served, as rp2's lwIP one is small and fixed (`TCP_SND_BUF` 6,400 B); both sizes are read back through libc's `getsockopt()`. Unpinned, a loopback socket starts with megabytes, so a whole page fits the kernel at once and a client's reset meets a finished write; pinned, a body larger than both ends' buffers is still being written when the client resets, on any host |

`main-exit` keeps the runner's loop alive, since the twin's WDT countdown dies with its loop.

The runner prints `WATCHDOG_WOULD_TRIGGER count=<n>` whenever its WDT would have reset silicon, and
one shutdown line naming `would_have_triggered_count`, `feed_count`, `largest_feed_gap_ms`,
`wdt_timeout_ms`, the kept scratch registers, `public_destinations_refused`, `flash_stall_longest_ms`,
`gc_block_bytes`, the FRAM chip's payload writes (`fram_writes`, `fram_writes_by` per FRAM-backed
logger, `fram_silent_writes`, `fram_silent_wrens`, and `fram_writes_unattributed` once the address
table is full) and, per UART link, its transfers, failures and overruns (laps and receive errors
counted together). The line comes after a `gc.collect()` and `micropython.mem_info()`'s GC summary,
whose last line ends `max free sz: <blocks>`; `scripts/_twin_process.py`'s `ShutdownLine` refuses a
line without that summary above it and reads the largest free block from it. Exit codes: 0 a clean
end, 1 an error, 3 a simulated reset, 4 a bootloader entry, 5 a simulated power loss.

Each boot-phase mark the product writes (`asy_system_service.boot_phase()`, SPECIFICATION.md Part
A.7) also prints as one `[<device>] boot phase: <BOOT_NAME>` line, so a run's log shows its boot
order. The printer is installed once per process; in a process that boots more than once (a test
file calling `main()` again) each line names the device of the latest boot.

### FRAM persistence

The FRAM twin reads back exactly what was written, including across process restarts, but only
ever writes to disk on an **explicit** call — never automatically — the owner's 'don't do
unnecessary write cycles' for an SSD-hosted state file (owner, 2026-08-12). Any entry point that
boots a real `sensortask_<device>` object graph against the twin
(`digital_twin/run_generic_integration.py` is the real example, flushing in its
`_shutdown_cleanup()`) should:

```python
import asyncio
import machine  # digital_twin/machine.py, once MICROPYPATH is set as above

machine.configure_fram_state_path("digital_twin_fram_state.json")  # before constructing spi0
try:
    asyncio.run(main())
finally:
    machine.flush_fram()
```

`""` (or `None` in code) runs it in memory only, as `tests/test_digital_twin_fram.py` does by
constructing `FRAMChip(size, rdid_response)` directly (that file never goes through `machine.SPI` at
all). A missing state file starts a factory-fresh chip silently (a first launch); a file that cannot
be loaded — no `memory_hex` marker, another chip size, a truncated image — prints one `FRAM state
<path> not loaded (<reason>): starting from a factory-fresh chip` line and starts blank. A save writes
`<path>.tmp` and renames it over the file, so a twin killed mid-save leaves the previous image whole.

**`save_state()`/`_load_state()` stream the memory image in fixed-size chunks (512 bytes / 1024 hex
chars), never materializing one contiguous string for the whole buffer**, so no contiguous
allocation of the whole image is needed (MicroPython's GC never relocates live blocks):
`json.dump({"memory_hex": bytes(self.memory).hex()})` needed one contiguous ~2x-size allocation
(16385 bytes for a 0x2000-byte FRAM), which failed with a real `MemoryError` after a few seconds of
the real task supervisor fragmenting the heap, with ~1.5MB of *total* `gc.mem_free()` still
available. Chunked reads/writes only ever need one small chunk contiguous at a time.

**A save writes the image only up to the chip's last nonzero byte** (the header's `"used"`; a file
without it holds the whole chip, and one naming more than the chip holds loads blank): the blank
tail a factory-fresh chip reads as zeros is never written to the host, CLAUDE.md's host-wear rule.
A twin process saves once, at its shutdown, and a `dev` pass of the twin CI launches 94 in its suite
parts alone: each save of the 256 KB chip wrote 524,328 bytes of hex before, up to 49.3 MB over
those 94, and the 63 images one pass left behind now hold 45-2,328 bytes (agent, 2026-10-26).

**`writes_at` is sized for its 2048-key cap when the chip is built** (`dict.fromkeys()` over 2048
items, then one `del`: `py/objdict.c:288-296`, `py/map.c:281-290`), so counting a new address never
rehashes. A rehash needs one contiguous table, 19,568 bytes from 919 to 1223 slots on the Unix port
(`py/map.c:68-73, 131-148`), and inside the product's erase on a fragmented -1 heap that allocation
failed: the shutdown's catch-all ended the sequence (`asy_system_service.py`), nothing fed the
watchdog, and the twin, whose watchdog only records, hung until the suite killed it, so the next
boot read a power-on. Run 13's erasefram cell went red in 1 of 8 replays before and 0 of 40 after
(agent, 2026-10-26).

**The memory itself is held in 4KB pages (`_PagedMemory`), never one bytearray for the whole chip.**
Same cause, at chip construction: dev's 256KB MB85RS2MTA as one `bytearray` needs a 256KB contiguous
run, and under the coverage build's inflated allocations `tests/test_digital_twin_bus_hazard_concurrency.py`
failed to build it with ~15MB of the 16MB heap free, once an unrelated edit reordered the file's tests
(agent, 2026-10-07). The pages read and write like the bytearray they replace, and a write past the
chip's end is refused rather than growing the chip.

### SCD30 persistence

Real SCD30 hardware keeps the measurement interval, ambient pressure, altitude, temperature offset,
ASC enable and the continuous-measurement status in NVM (Interface Description 1.4.1-1.4.8); the twin
persists those six on explicit flush, with the same design as FRAM persistence above — never
automatic. Whether the ambient-pressure value itself persists is an assumption (the datasheet names
only the status) — fidelity table, BACKLOG row. The live CO2/temperature/humidity readings always
restart fresh on a new process, matching what a real power cycle does to the sensor's in-flight
measurement state:

```python
machine.configure_scd30_state_path("digital_twin_scd30_state.json")  # before constructing i2c0
try:
    asyncio.run(main())
finally:
    machine.flush_scd30()
```

`""` (or `None` in code) runs the SCD30 twin in memory only, same convention as FRAM. The manual
entry points persist by default (owner, 2026-08-13); automated callers pass per-run paths or `""`.
A missing state file starts factory-fresh settings silently; malformed or truncated JSON, a non-dict
or a mistyped value prints one `SCD30 state <path> not loaded (<reason>): starting from factory-fresh
settings` line and starts factory-fresh. A save writes `<path>.tmp` and renames it, as the FRAM's does.

The firmware compares a `PUT /sensors` against a fresh chip snapshot and writes only what changed
(compare-before-write, SPECIFICATION.md Part G.2): an identical TempOffset/MeasInterval/Altitude/SelfCal
spends no NVM write, `AmbPres`/`ForceCalRef` always do. `SCD30Chip.nvm_writes` counts every
NVM-writing command `handle_writeto()` receives (0x0010, 0x4600, 0x5102, 0x5204, 0x5306, 0x5403 and
the stop command 0x0104; Interface Description 1.4.1-1.4.3, 1.4.6-1.4.8), the same frames
`tests/_write_counters.py`'s `scd30_nvm_writes()` counts on a fake bus. It is a test surface, not
chip behaviour: a twin test asserts the writes a PUT spends.

`mem_backup()`'s two regions persist the same way, only on a simulated reset: the runner writes
`digital_twin/mem_backup_state.json` when the run ends in one, and the next launch consumes and
deletes it; a simulated power loss writes nothing, as power-on clears the registers.

Only the last-wired SCD30 and FRAM instance persist — the fidelity table's Persistence row states the
limit and the change that lifts it.

## Running the twin's own tests

Its unit tests live in `tests/test_digital_twin_*.py` (matching every other `src/` module's own
test-file convention), but reach this package via a per-file `sys.path.insert(0, "digital_twin")`
(and `digital_twin/unixport` where needed) —
the same confirmed-safe pattern `tests/test_setter_microdot_integration.py` already uses for
`ext/microdot.py` — rather than a `scripts/test.sh`/`MICROPYPATH` change, so they run under the
exact same default invocation as every other test file:

```bash
scripts/test.sh   # discovers and runs them like any other tests/test_*.py - MICROPYPATH is set
                   # internally per test file to the unit layout of scripts/micropypath.toml, not
                   # read from the calling shell's environment
```

A file that boots a device prewarms the poll set, then applies the UDP shim, at module level
(`tests_scripts/test_twin_entry_point_order.py`); before each build it calls
`machine.reset_peripherals()` and `network.reset_interfaces()`, configures the wiring plan and writes
the offline NTP config. It registers `machine.reset_test_state` and `network.reset_test_state` with
`microtest.after_each`, and drives its coroutines through `tests/_async_harness.py`'s `run()`/
`run_timed()` from synchronous test scope, never a nested `asyncio.run()` (CLAUDE.md).
A file marked `PER_DEVICE = True` runs once per generated device, named by `TEST_DEVICE`
(`scripts/test.sh`); its driver-specific tests run on the device `tests/_twin_devices.py` picks.
HTTP-driving scenarios run host-side, by `scripts/_digital_twin_scenarios.py` against a runner
subprocess (SPECIFICATION.md E.9). A runner or harness started from a test or a script reads the
twin layout of `scripts/micropypath.toml`, never `tests/` (`tests_scripts/test_twin_never_needs_tests_on_its_path.py`).

`machine.Timer.drop_next_soft_callbacks` (a class attribute, 0 by default, in `Timer.TEST_API`) is
reached only by a test: the next N soft callbacks of any Timer are dropped as rp2's full depth-8
scheduler queue drops them. A PERIODIC alarm re-arms, a ONE_SHOT is lost and frees its alarm, a
hard callback is never dropped, and `machine.reset_test_state()` clears it.

The chip-fake and fake-module tests are deterministic — no wall-clock waiting, except one
short-period/generous-timeout smoke test in `tests/test_digital_twin_machine.py`
(`test_timer_fires_for_real_on_a_short_period`) that proves the real-time scheduling mechanism itself
works at all, not a precise-cadence assertion. The tiers that boot a device's real graph run on real
time and wait for each state by a bounded poll (`tests/_twin_readiness.py`), every bound a Part N row.

## Running device scripts in the twin

`digital_twin/run_device_script.py <plan.json> <script.py> [--gc-threshold N] [--state-dir DIR]` runs
one `tests_hardware/device_scripts/` script unchanged, as `Board.run_isolated()` runs it on silicon:
the device's wiring plan, the one armed watchdog, the requested GC stage, after the poll prewarm and
the UDP shim; a plan naming a UART pair (`dev`) gets the bench's crossover jumper first. It exits 0,
1 (raised), 2 (usage), 3 (reset), 4 (bootloader) or 6 (watchdog starved). `tests_hardware/twin_board.py`'s
`TwinBoard` launches it behind `Board`'s API (`pytest tests_hardware/flash --twin`), each board's
FRAM, SCD30 and `mem_backup()` state and its filesystem (each run's working directory) in one
directory kept across its runs, so nothing a script writes lands in the checkout.
`scripts/record_twin_instrument_runs.py` writes the twin record (twin_record.json in
`tests_hardware/`); `tests_scripts/test_twin_record.py` fails when a script, the runner or the `src/`
API a script imports changed since its entry. A script that cannot run here is an `exception` entry
with its reason in the record, never listed in this file.

## Automated CI suite

`scripts/run_digital_twin_ci.sh` turns the manual on-demand walkthrough above (fresh boot, every
GET/PUT endpoint, `DebugLevel=5` verbose logging, bus fault injection, settings/error persistence
across a real reboot, soak) into an automated, CI-gating check — wired in as the `digital-twin-e2e`
job in `.github/workflows/ci.yml`, one job per device, GC stage and part via that job's own
`strategy.matrix` (SPECIFICATION.md Part L.4, mirroring `firmware-build-verify`'s own precedent). See
`SPECIFICATION.md`'s "Digital twin" section (Part A.10) for the full architectural account of what
it checks and why; this section is the practical how-to.

```bash
scripts/run_digital_twin_ci.sh <device>                     # a device of devices/*.toml: build -> suite -> harness, both GC stages
scripts/run_digital_twin_ci.sh <device> --gc-threshold -1 --part suite   # one stage, one part: what one CI job runs
uv run scripts/_digital_twin_ci_suite.py --micropython-bin <path> --device <device> --only 5,5b --repeat 3   # diagnosis
```

A missing or unknown device prints the usage and the valid devices and exits 2. The runner then
takes ports 53 and 18080 (a port another suite holds fails the run at once, naming that suite), and
before any build moves the device's previous logs and state, `digital_twin_ci_logs/<device>/`, into
`build/archive/digital_twin_ci_<device>/<UTC>/`, keeping the newest three. The suite run alone takes
the same two ports itself, the harness run alone port 53.

**State**: each pass keeps its state under `digital_twin_ci_logs/<device>/<pass>/state/`, never
`digital_twin/`'s manual defaults, and archives it to `state_archive/NN_before_<label>/` before every
fresh start — nothing inside a run is deleted, so the FRAM image and logs of every earlier run of it
stay readable.

**Build**: asks `scripts/_unix_port.sh ensure standard` for the MicroPython Unix port (built when
missing, of another flavour or stale against the toolchain record, cached at `$PICO_TOOLCHAIN_DIR`,
as for `scripts/test.sh`/`scripts/run_unix_port_integration.sh`), generates every real
device's own `sensortask_<device>.py` + wiring-plan JSON into `build/generated_src/`
(`scripts/_generate_sensortask_modules.py`), and the real website for the chosen device into
`frozen_modules/frozen_html.py` (`scripts/build_website.sh <device>`). Must succeed before any
test phase runs.

**Test**: hands off to `scripts/_digital_twin_ci_suite.py --device <device>`, a self-contained
`uv run` CPython script (stdlib-only — no `uv sync` needed) that drives
`digital_twin/run_generic_integration.py` as a real subprocess, over real HTTP/UDP (`http.client`/
`socket`, not `_http_client.py` — this script runs under CPython, not the twin's own MicroPython
process), through a sequence of real subprocess runs on a fixed port (`18080`, distinct from
the manual entry point's `8080` default, so both can run side by side without colliding). **The
whole sequence runs twice, not just once** — once at `--gc-threshold -1` (MicroPython's own real
reactive-only default) and once at `32768` (the project's chosen value, matching every real firmware
boot), each pass writing its own subdirectory under `digital_twin_ci_logs/<device>/`
(`gc_threshold_neg1/`, `gc_threshold_32768/`); `--gc-threshold` runs one. This is CLAUDE.md's/
SPECIFICATION.md Part I.4(e)'s standing rule applied to the *entire* suite, not just the soak
check (run 11, below) — every run's log is checked for zero `MemoryError`/`memory allocation
failed` (caught-and-logged included; a missing, unreadable or empty log fails the gate) and for
`public_destinations_refused=0` on its shutdown line, and every suite and harness shutdown line for a
feed gap above 75 % of the armed watchdog timeout (`l2.feed_gap_share_max`), except the runs that
starve the watchdog on purpose (run 10, the hung-step scenario). The routes a run walks come from the
device's API reference, `build/generated_src/api/sensortask_<device>.json`, whose absence fails the
pass naming it. A device wiring a `uart_link` pair runs Run 3 again on a TOML derived with
`crc = "crc16"` on both ends (`--device-toml`, under `digital_twin_ci_logs/<device>/crc16/`), so the
link runs in both CRC modes. The
fault matrix in runs 3/4/5c/10 is derived from that device's own real wiring plan and instances,
never a hardcoded driver list, and every fault it leaves out is printed with its reason (`_LEFT_OUT`):

1. **Baseline boot, then the reformat relaunch** — walk every `GET` route of the device's API
   reference and `/`, then read, keep (`runs/run1_errcount.json`) and check the logs — no error or
   warning entry from any module — then clear them (`ResetErrors`); with no station link the clock
   has never synced, so `UTCTime`, `LocalTime` and `TimeStale` read null. Shut down cleanly through
   the stop file (`main()`'s clean path, which flushes the FRAM/SCD30 state as the `SIGINT` handler
   does; `SIGINT` is the fallback, never `SIGTERM`) and confirm the state files landed on disk. Then
   relaunch on an emptied config directory beside the kept FRAM state, as a reformatted filesystem
   leaves a unit: `SYSTEM` logs exactly one W `CONFIG_LOST` (kept in `runs/`), and a setting is
   `PUT` on each of `/system` (`DebugLevel=5`), `/notification` (`WarnCO2=1800`), `/sensors`
   (`SCD30.MeasInterval=4`), `/networking` (`Hostname`) and `/status` (`ResetErrors`) — every
   route that accepts `PUT`.
2. **Real reboot, settings persistence** — a fresh subprocess against the *same* persisted state
   (the whole point is testing what survives). Confirms every setting
   from run 1 is still there after a genuine process restart, and that the now-persisted
   `DebugLevel=5` produces real, multi-module verbose log output (`asy_print_log.py`'s
   `print(name, *args)` convention — checked for known `_NAME` prefixes like `SYSTEM`/`SGP40`/
   `SCD30`/`WEBSERVER`) from the very start of boot, polled for rather than slept on.
3. **The combined-fault escalation** — every instance this device wires boots with its sustained
   fault (`<instance>:writeto:500` for each sensor, `fram:silent`, `uart_link:silent`): each faulted
   module records a real `"E"` entry while the process lives, then the supervisor's restart budget
   runs out and the device resets itself — exit code 3 with one reset line, never a crash, and the
   (simulated) watchdog never starves. `fram:silent` makes the chip answer zeros and keep its bytes,
   so nothing is torn.
4. **Relaunch fault-free on run 3's state** — `ResetReason` is the supervisor's escalation code,
   the boot cleared the reset record (`mem_backup` region 0 reads zero at shutdown), every measuring
   driver produces real readings again, and SCD30/BMP3XX/ISL29125, whichever this device wires, read
   `0`. **Not** because those logs are in-memory: they are FRAM-backed like every other, the module
   wiring each logger through its `fram_target`. They read `0` for a narrower, situational reason:
   the FRAM was silent for all of run 3, so nothing they logged could reach the chip — a much weaker
   claim than "these never persist", whose chip-healthy half run 5c proves. The FRAM's own log is
   out of that sweep: a chip that answered zeros for a whole run is found blank, and the
   self-healing read logs that afresh on this boot — the driver working as designed.
5. **A small *bounded* fault, and recovery** — on a fresh state, three faults on SGP40's
   measure-raw reads only (`<sgp40>:readfrom_into:3:0x260F`), sparing setup's serial read and the
   heater-off rung; a station link is configured, so the clock syncs against the twin's local NTP
   responder and each read carries a timestamp. Confirms exactly three failed reads were recorded (each
   one `READ` and one `STREAK` failure event, the only `"E"` codes; every `"W"` a recovery rung or an
   SGP40 storage warning, by catalog name), that the count stays put across two observed read cycles
   once the fault is spent, and that measurements resume. A device wiring no SGP40 records a named
   skip of runs 5 and 5b.
   **5b. Reboot straight onto run 5's state, fault-free — the restore is all-or-nothing.** Run 5
   left exactly three failures on a *healthy* chip, write-through (`asy_print_log.py`'s
   `_store_err()` writes on every push — there is no deferred flush to race), so they should come
   back. But run 5 shut down abruptly, and that can catch a chunk write in flight: both status bytes
   go to `_STATUS_BUSY` before the payload is touched, so an interrupted write leaves them there,
   `PrintLogHistoryStore.setup()`'s `_read()` then fails, and its `_write()` fallback stores the
   empty ring (measured at roughly **1 abrupt restart in 8**). That loss is **accepted** (owner,
   2026-09-11; confirmed 2026-09-26, paraphrase: no recovery scheme wanted for a reboot that catches
   the chip mid-operation; the loss stays all-or-nothing, never partial or garbled), so this run
   asserts the invariant that does hold: the restore is run 5's exact ring and count, or none of it,
   which is the dual-block + CRC + busy-flag protocol's actual job.
   **5c. A commanded reboot through the controlled shutdown — FRAM drained, then every task stopped,
   then the reset — the case that loses nothing at all.** One bounded fault per chip instance the
   device wires, each in its own process, chained onto the previous link's persisted state, each link
   ending in `PUT /system {"SystemCmd": "reboot"}` and exit code 3 — one fault per process because
   three drivers faulted together exhaust the task-restart budget (SPECIFICATION.md Part C.4.1) and
   the *device* reboots itself, which is not the commanded reboot this run tests. The final
   fault-free boot reads the REST reboot's `ResetReason`, then every recorded count and its counter
   exactly, every *other* registered error source (`SYSTEM`/`NOTIFY`/`NTP`/`WEBSERVER`/`DNSSRV`, every
   FRAM-backed `CFGMGR_*`, every `uart_link` instance) at least what it held, the same set of sources
   registered, the storage pause *not* surviving (RAM-only), and a `ResetErrors` PUT clearing the
   restored history on the chip. `FRAM` and `CFGMGR_SCD30` are the RAM-only sources, exempt from the
   sweep, and `tests/_sensortask_scenarios.py` pins the same set from the real object graph. The same
   all-or-nothing claim is mirrored at the mock tier (`tests/test_fram_integration.py`) and on real
   silicon (`tests_hardware/flash/test_fram_storage.py`'s reset-race test).
6. **Clean boot, configure a real SSID** (persisted) — needed for run 7's genuine STA-connect-
   failure cycle, not the `SSID==""` unconfigured shortcut.
7. **Reboot with 5 scripted `"no access point found"` WiFi outcomes** — drives the real STA →
   hotspot-fallback state machine (`conn_fail_to_hotspot=5`), starts the real `CaptiveDNS`, and
   confirms it actually answers a real UDP DNS query sent from outside the process — not just that
   the internal state flipped — and that the five identical verdicts spent one history slot and the
   fallback warning one more. Only possible because of
   `digital_twin/unixport/_unix_port_udp_addr_shim.py` — see the
   "`unixport/_unix_port_udp_addr_shim.py`" section below for the three Unix-port-only `socket`
   quirks it works around, entirely from twin-side code, with `src/` left untouched and correct for
   real hardware. `src/asy_captive_dns.py`'s `CaptiveDNS` binds the real, privileged port 53
   unconditionally (correct for real hardware, which has no user/privilege concept at all), so
   `scripts/run_digital_twin_ci.sh` grants the built interpreter binary `CAP_NET_BIND_SERVICE` (via
   `setcap`, fresh on every invocation, since a cached toolchain archive doesn't preserve it), and
   this run checks the capability first and fails naming it when it is missing.
8. **Reboot fault-free** — WIFI's own persistence-correctness check (FRAM-backed, the same
   all-or-nothing abrupt-restart guarantee as SGP40's run 5b — the five scripted failures plus the
   persisted `WLAN_TO_HOTSPOT` fallback warning, six events in two history slots, come back whole or
   not at all), the station link's first NTP sync against the twin's local responder with both time
   fields present, plus an unreachable NTP host configured (`192.0.2.1`, RFC 5737 TEST-NET-1) for
   run 9.
9. **Reboot with NTP permanently unreachable** — the other "network connections" real-world case.
   Confirms the webserver stays fully healthy past NTP's own 5s fetch timeout, not just eventually,
   that NTP logs `NTP_NO_REPLY` where the host has a route for the request and `NTP_NOT_SENT`
   where it has none (a network namespace holding only `lo`), never both, and that no task ended and
   was restarted meanwhile. The watch ends on the third NTP failure event, then one supervisor pass
   (`l2.ntp_unreachable_failures`, inside the 90 s `l2.ntp_unreachable_watch_s` bound): the 10 s
   doubling backoff puts the failures at about 4, 22 and 62 s of serving (`dev`, 2026-10-15).
10. **The dedicated watchdog-backstop case** — one bounded real, *blocking* (`time.sleep()`, not
    `asyncio.sleep()`) hang per bus-attached instance the device wires (`--hang <instance>:<op>:12`,
    `writeto` for a sensor, `readinto` for the FRAM), each in its own process with `--duration 15`,
    genuinely freezing the whole interpreter past the 8000ms WDT window.
    `digital_twin/_fault_injection.py`'s `inject_hang()` is what makes this possible — real rp2040
    `machine.I2C` calls have no `await` point (SPECIFICATION.md Part F.2), so a genuinely wedged
    real peripheral blocks the whole single-threaded interpreter, not just one asyncio task; a real
    blocking sleep is the only way this twin can reproduce that specific failure mode faithfully.
    Confirms the process survives and exits cleanly, and — the one thing sustained-but-bounded
    errors (run 3) cannot demonstrate — that the watchdog backstop itself actually engages
    (`would_have_triggered_count >= 1`), matching CLAUDE.md's recovery-ladder rule: a transfer that
    never returns is the watchdog's. Each run ends on its `WATCHDOG_WOULD_TRIGGER` line, inside the
    45 s `l2.hang_run_exit_wait_s` bound.
11. **Clean soak run — host-driven, not a twin-side `--soak` flag.** A fresh clean-boot twin
    subprocess is armed with `--mem-sample-interval-ms` only; the *host* (this script's own
    `_run_11_soak()`, plain CPython) drives warm-up cycles until no cycle has set a new `MEM_SAMPLE`
    floor for 20 cycles (`l2.soak_plateau_cycles`; at most 100, `l2.soak_warmup_cycles`), then 80
    measured cycles, each walking every `GET` route of the device's API reference and `/` directly
    over HTTP (see "Run 11's calibrated numbers" below), checks zero HTTP failures and
    `would_have_triggered_count == 0`, then parses the twin's own captured
    `MEM_SAMPLE <time.ticks_ms()> <gc.mem_free()>` log lines lying between the cycles' first and
    last byte offsets in the log (`/status`'s `MemFree` is one poll's reading, not a stream —
    SPECIFICATION.md's "Driver/DUT process separation" Part) and computes the early-quarter-vs-late-quarter memory-trend check
    (`_mem_trend()`, unit-tested directly in
    `tests_scripts/test_digital_twin_ci_suite_soak.py` — no live subprocess needed for that half).
    One boot, one verdict (owner, 2026-09-26: 'A retry or a longer timeout never counts as a race
    fix'). The check is host-side because an in-DUT loop contaminates the
    resources it measures (SPECIFICATION.md's "Driver/DUT process separation" Part; no `gc.collect()`
    propping up a result, Part I.4(e)). A CI `MemoryError` here (`allocating ~6100 bytes` on
    `GET /status`) is the standing example of the owner's rule (2026-09-26) that a threshold is never
    the fix: its root cause was the client's growth-by-concatenation reads, fixed by `_http_client.py`'s
    `_read_exact()`/`_read_until_close()` (one right-sized buffer per `fetch()`).

    **Run 11b — the full connection ceiling under real simultaneous load** (`_run_11b_full_ceiling_
    concurrency()`). A fresh twin; the host reads the device's own ceiling through buildgen's
    `device_max_connections()` (`devices/<device>.toml`, else `src/`'s default) and fires exactly
    that many simultaneous GETs cycling over every `GET` route of the device's API reference, three
    rounds, from CPython threads on
    a barrier with one real socket each — every one must be served `200` with a body that parses as
    a JSON object, the twin must still serve afterwards and shut down
    cleanly, and the suite's own no-`MemoryError` log check applies at both thresholds. A 1 s settle
    precedes **every** round, the first included: a slot is released only after the close is awaited
    (SPECIFICATION.md H.7.1), and the readiness probe's own connection is still counted when round 0
    would otherwise start. Driven from a separate process because an in-process client measures its
    own buffers (SPECIFICATION.md Part E.9).
12. **The reset reasons reachable at L2** — a fresh boot reads the power-on code; `bootloader` exits
    with code 4 and the relaunch reads its code (the fidelity table's bootloader assumption) with the
    record cleared at boot; a SIGINT relaunch reads power-on, the twin's non-reset launch. Last, on
    the same state, a C-stack overflow in one read of the plan's first bus device (I2C buses in plan
    order before SPI): `--fault <instance>:<read op>:stack` (`readfrom_into` for SCD30 and SGP40,
    `readfrom_mem` for BMP3XX and ISL29125, `readinto` for the FRAM) queues one, the handler that
    catches it records it and the supervisor resets the device — exit code 3, the watchdog never
    starved — and the relaunch reads code 20 with SYSTEM's one `STACK_EXHAUSTED` entry; a device
    wiring no bus driver records a named skip of the cell. Escalation is run 4's, the REST reboot run
    5c's, the config-reset and FRAM-erase codes run 13's.
13. **The system commands end to end**, each cell in fresh state — `resetconfig` (every config file
    deleted unread, the relaunch writing each at its defaults, the TOML's `Hostname` back, its reset
    code, `ConfigFaults` empty), the same over damaged files (`ConfigFaults` names the unparseable and
    the out-of-range file, never the missing key's), `erasefram` (the FRAM evidence saved first, a
    planted entry, then every FRAM-backed count 0 and its reset code), the near misses of every
    command word (each `"Invalid"`, the device serving on, the watchdog never starved), and `reboot`
    and `bootloader` through the controlled shutdown (its four step lines in order, the reset line,
    then a relaunch keeping `DebugLevel` and every FRAM-backed history a superset of what it held).
    The command states, the hazards and a hang at each shutdown step are the scenario harness's.

**The host-side scenario harness** (`scripts/_digital_twin_scenarios.py`, SPECIFICATION.md E.9)
runs after the suite at each GC stage, holding port 53 (`--exclusive-port-53`), so its DNS scenarios
run too; without that lock they are deselected and listed. Each scenario boots the device's
generated graph in a twin and drives it over HTTP, reading only the runner's stdout and its
`--test-*` lines. Every boot logs at error level, so a caught allocation failure's line reaches the
memory gate (the owner's option 1 for the unit tests, owner, 2026-10-20, asked, paraphrase, whether
to turn logging on at error level or above in the unit tests that can actually run out of memory, in
every unit test, or in none: "Option 1 is good"; applied to the harness too, agent, 2026-10-20):
the runner's `--debug-level 1` over a stored `DebugLevel` of 1 planted before the spawn unless one
is stored, but for the scenario reading the settings routes' defaults, which boots unplanted at the
default level. Every boot also carries
`--test-kbd-traceback`, so a twin that ignores its shutdown SIGINT is described before the kill:
where its interrupt was raised, then what a second SIGINT does (`scripts/_twin_process.py`'s
`shutdown()`), the verdict staying the kill's. Each scenario declares its family (webserver
concurrency, sensortask integration, the real
website, bus hazards, system commands, webserver requests, UART load), the drivers it needs (a
device without them skips it) and whether it may share a boot. The sharing ones run first on one twin
per group, with an idle check between two of them — the twin alive, every slot drained, the kernel's
accept queue empty, the error counts after the drain, the memory gate — and a failure names its
scenario and sends the next to a fresh boot. A shared twin is retired before
`l2.scenario_shared_boot_deadline_s`, the earliest its own SGP40 untimestamped-backup warning can
land with no NTP sync in the hotspot, and a count an idle check reads moved past it fails by name
(agent, 2026-10-19). The hung-step scenario ends on the runner's
`WATCHDOG_WOULD_TRIGGER` line (S1 on its `HUNG S1` line); the UART-load scenario
(`uart_ring_under_concurrent_load`) drives both links of a device that wires a pair through a
webserver hammer at the ceiling, FRAM log writes and config flushes, each flush stalling the loop as
rp2's flash write does, in a typical then a maximum stall round (`--test-flash-stall-max`): no
overrun, one over-cap refusal logged once per initiator (`--test-uart-over-cap`), and the largest
free block asserted at the threshold stage only (at -1 it is printed). Run alone, the harness takes
port 53 itself; a held one fails the run naming its holder, no twin booted.

Each run's subprocess stdout/stderr is captured to `digital_twin_ci_logs/<device>/<pass>/run<N>_*.log`,
the harness's under `digital_twin_ci_logs/<device>/scenarios/gc_threshold_<stage>/` (gitignored; the
previous run's under `build/archive/digital_twin_ci_<device>/`; uploaded as the CI build artifact
`digital-twin-ci-logs-<device>-gc<stage>-<part>` via the `digital-twin-e2e` job's own `if: always()`
upload step, so a failure's full boot log is inspectable from the Actions run itself, not just the
pass/fail summary). The suite ends with the summary block (SPECIFICATION.md E.10) and exits non-zero
if any check fails, failing the CI job.

### What `run_generic_integration.py` keeps in-process, and why

Almost every request-driving and response-observing job moved host-side (SPECIFICATION.md's
"Driver/DUT process separation"). Two things could not, and both are deliberate:

- **`--mem-sample-interval-ms`** — `gc.mem_free()` is also published as `/status`'s `MemFree`, but
  one poll's reading is not a stream: this flag samples it inside the process on a fixed timer
  rather than once per host-driven cycle, because the host has no way to signal "a cycle finished"
  without adding the very channel this design avoids. Each line carries `time.ticks_ms()` for
  diagnostics only; the host selects the samples inside its window by their position in the log,
  never by either process's clock — the same way it scrapes the watchdog counter from stdout, never
  by calling back in. Its `gc.collect()` is measurement instrumentation, Part I.4(e)'s one twin
  exception (owner, 2026-09-26), kept at the calibrated 100 ms, a quarter of the 25 ms it replaced,
  where Run 11 still tells the planted leak below from the unplanted tree (agent, 2026-10-26), not
  a pressure workaround: on a fixed timer, reaching no webserver or driver, it
  cannot mask a real `MemoryError`. Verified by removing it (2026-09-14) — the trend check got
  *worse*, swinging min=99808/max=1347104 on a healthy run, a false positive from incidental
  reactive-GC timing.
- **The `wire_log` clearer.** `UARTLink.wire_log` keeps the newest 4,096 bytes per direction and
  counts the rest, so a unit test with direct object access can assert what crossed the wire, and
  every such test clears it itself. This process has no such access — it boots the twin as a
  subprocess and never reads the log — so `_wire_log_clearer()` clears each log in place on a timer
  (`l2.twin_wire_log_clear_interval_ms`); unbounded and uncleared, it grew for as long as the link
  carried traffic, which made Run 11's memory trend fail for the one device with a wired pair.
  Clearing it changes nothing over-the-wire: nothing in the request path or `asy_uart_comm.py` ever
  reads it back.

### Run 11's calibrated numbers

**`_SOAK_WARMUP_CYCLES = 100`: a device with more instances settles longer after boot.** `dev`'s two extra `uart_link` instances
mean more one-time post-boot settling — module-level caches and config-derived structures
populated once, the same asymptotically-decaying-then-flat shape wozi's boot shows on a smaller
scale, not an unbounded leak. Confirmed 2026-09-14: `gc.mem_free()` plateaus for both devices given
enough idle wall clock, wozi's curve flattening well inside 40 cycles' worth and dev's needing
roughly 2.5x that, reproduced with the UART tasks fully disabled — so it is settling proportional
to module count, not UART traffic. 100 gives every device room to finish before the measured
window starts. It is now the warm-up's bound, not its length: the warm-up ends once no cycle has set
a new `MEM_SAMPLE` floor for 20 cycles (`_SOAK_PLATEAU_CYCLES`), so a device settles for as long as
it needs and no longer; `dev` ran 84 and 63 cycles in all at the two GC stages (2026-10-15), against
the fixed 120 before.

**The memory-trend tolerance is self-calibrating, and a scaling law is why.** The original
calibration — five 100-cycle soaks, 25-sample quarters, trend deltas of +2623, +796, -410, +1729,
-116 bytes — gave a flat 8192-byte tolerance, about 3.1x the worst magnitude and scattered around
zero. Porting that forward as `8192 * sqrt(25/quarter)` assumed a trend's standard error shrinks
with `1/sqrt(quarter_size)`, as it would for independent samples. It does not, and CI kept tripping
it on a different device each time.

Measured directly: sliding a 206-sample window across a region 20+ seconds past all settling and
visibly flat in the raw trace, the trend statistic's own standard deviation came in at 1496-1964
bytes — 3.4-4.5x what the formula predicts at this quarter size, because consecutive 25ms
`gc.mem_free()` samples are heavily autocorrelated. More samples buy far less noise reduction than
independent-sample statistics assume, so the formula tightened fastest exactly where it had to be
loosest.

`_mem_trend()` now measures the spread *within* each quarter, decoupled from the early-vs-late
difference the trend itself measures — so a genuine leak's decline cannot inflate the tolerance
meant to catch it — and sets the tolerance as a generous multiple of that. Self-calibrating per
device, run and quarter size, with no constant to re-derive, and it covers the observed worst case
(5889 bytes) with room left.

**80 measured cycles, a `MEM_SAMPLE` every 100 ms, a tolerance of 4.0 times the quarter noise**
(agent, 2026-10-26), calibrated on `dev` against a planted leak, a 40-byte `bytearray` kept per
request. The plant turned Run 11 red in all 4 boots, two per GC stage (a decline of 55.5-58.9 KB
against tolerances of 33.2-41.5 KB), and the unplanted tree stayed green at both stages (7.1 KB
against 23.9 KB at -1, 7.8 KB against 22.9 KB at 32768). The former 20 cycles at 3.0, sampled every
25 ms, passed the same plant in all 6 boots (8.9-14.9 KB against 15.3-22.3 KB): 20 cycles of a slow
leak stay inside one run's own noise. The owner accepted the longer run (owner, 2026-10-23, asked
whether Run 11's calibrated leak check, about 75-90 s more per run, stays: "Question 1: This is
okay, go ahead."). One attempt decides, with no retry.

### Two suite-table subtleties worth reading before changing one

**`_NO_PERSIST_WHEN_FRAM_FAULTED` (`scd30`, `bmp3xx`, `isl29125`) is not "these logs are
in-memory".** Every one of them is FRAM-backed; Run 3 sets the FRAM `silent`, so nothing they log
reaches the chip. The property is "with the FRAM silent, nothing persisted", a much weaker claim,
which is why Run 5b/5c exist to make the chip-healthy one for every bus-attached driver the device
wires.

`fram` is deliberately absent from that set even though its own log genuinely is in-memory-only.
A chip that answered zeros for the whole of Run 3 is found blank on Run 4's boot, and the
dual-block+CRC self-healing read every restore goes through logs that as a fresh FRAM-level entry —
not old data surviving and not a defect: self-healing detecting a blank store is the driver working.

`sgp40` is absent for a reason of its own: it is Run 5b's abrupt-restart subject
(`_PERSISTED_ERROR_MODULES`), so its persistence is proven on a healthy chip there instead of being
swept to 0 here.

**`_RESET_ERRORS_TIMEOUT_S` is derived, not chosen.** `PUT /status {"ResetErrors": true}` resets
every registered source at once, and each FRAM-backed one still pays a real chunk write — 10+ of them on
`dev`, which is why it exceeds `_http()`'s plain 5s default.

The value sits just **above** the server's own `outer_cap_s`, deliberately: below it a legitimate
slow reset reads as a client timeout, and at or above it the client timeout can never fire at all,
since the server aborts first — so the suite observes the server's own diagnosable abort instead of
a bare "something took too long". That timeout is a backstop, not a performance assertion; the
elapsed-time budget is `_RESET_ERRORS_BUDGET_S`, 80 % of the cap (12 s), sized from the twin's and the
bench's slowest legitimate resets, and the reset must also answer `Valid` (SPECIFICATION.md C.7).

### Faults, hangs and modes

`--fault DEVICE:OP[:TIMES[:MATCH]]` (`launch.py` and `run_generic_integration.py`) queues `TIMES`
(default 1) bounded faults on one bus op, each a fresh `OSError` raised by the next matching call,
`MATCH` a hex command word, register or opcode the call must carry. `--hang
DEVICE:OP:SECONDS[:TIMES]` queues a real, blocking `time.sleep(SECONDS)` before the next `TIMES`
calls to that op proceed instead. `DEVICE` is a driver name or an instance key
`<driver>_<name_ext>`. Unlike `--fault` (a bounded,
immediately-raised `OSError` — the driver's own normal error path), a hang genuinely freezes the
whole interpreter for real wall-clock seconds, the only way to simulate a truly wedged bus rather
than a bus that merely errors.

| Driver | `--fault` ops | `--hang` ops |
|---|---|---|
| `scd30` | `writeto`, `readfrom_into` | `writeto`, `readfrom_into` |
| `sgp40` | `writeto`, `readfrom_into`, `general_call` | `writeto`, `readfrom_into` |
| `bmp3xx` | `writeto`, `readfrom_mem`, `writeto_mem` | `writeto`, `readfrom_mem`, `writeto_mem` |
| `isl29125` | `writeto`, `readfrom_mem`, `writeto_mem`, `int_stuck_high` | `writeto`, `readfrom_mem`, `writeto_mem` |
| `fram` | `readinto`, `wren`, `silent` | `write`, `readinto` |
| `uart_link` | `silent` | — |
| `wlan` | `active`, `connect`, `disconnect`, `deinit`, `isconnected`, `status`, `config`, `ifconfig` | — |

The modes `isl29125:int_stuck_high`, `fram:silent` and `uart_link:silent` stay set for the run and
take no `TIMES` or `MATCH`; `fram:wren:N` drops the next `N` write-enables. With
`isl29125:int_stuck_high` the bus works and conversions continue, only the INT line never moves —
the silent failure the driver's periodic range evaluation exists to survive. Faults the rp2 port
cannot raise are refused: an SPI write never raises, a read raises only from 32 bytes on (fidelity
table). `wlan` takes every `raise_on` method with `:TIMES` and no `MATCH`, and has no `--hang`
vocabulary — its faults are a synchronous `raise_on[]` check, not a bus transaction with a real HAL
call underneath. `--fault DEVICE:OP:stack` queues one `RuntimeError("maximum recursion depth
exceeded")` — a twin-only knob no bus raises on silicon, carrying a C-stack overflow's exception
into one read so the reboot path can be proven at L2. A fault or hang naming a chip the run never
wired is refused by name. `pending(op)` reports what is still queued; the runner's
`--test-fault-status-interval-ms` prints it.

### `WDT._arm()`'s late-feed backstop

A real `--hang` freezes the whole interpreter, so every asyncio task — including `WDT`'s own
pending `_countdown()` sleep — sits unable to run for the hang's full real duration. Once the
interpreter unfreezes, `asy_system_service.py`'s periodic `feed()` (its own check interval is
deliberately shorter than any real watchdog `timeout`) can win the race to run before
`_countdown()`'s own already-expired `sleep_ms()` gets its turn, since both became ready at the
same moment. A plain cancel-and-restart in `_arm()` would silently erase that already-elapsed
deadline — real hardware can't un-reset itself just because a feed arrived right after it should
already have fired. `_arm()` checks, before cancelling the previous `_countdown()` task,
whether its own deadline had already elapsed; if so it credits the would-have-triggered event
itself, exactly once per elapsed window, before rearming — `_countdown()` still owns the normal,
not-yet-hung case, so this is purely the "a feed arrived too late" backstop, not a second counting
path. Run 10's per-driver hangs (one bounded hang per bus-attached driver the device wires,
`--duration 15`) depend on this, and on that `--duration` giving each hung call time to be reached
behind the other drivers' startup I/O before the run exits.

### `_http_client.py`'s read paths (why neither one uses `Stream.read()`)

The twin's own HTTP client reads bodies two ways, and both avoid the obvious call for the same
reason: `extmod/asyncio/stream.py`'s `Stream.readexactly()` and `Stream.read(-1)` both accumulate
with `r += r2` on every partial read — a fresh, larger contiguous object per read, the previous one
abandoned. Over a several-KB body arriving in several TCP reads that is several progressively
bigger allocate-copy-discard cycles per fetch, which is exactly what fragments this heap under
repeated soak cycles. Confirmed by reading the pinned interpreter's own source, not inferred.

- **Sized (`Content-Length`; every response this webserver writes, `GET /` included) →** one
  right-sized `bytearray` filled through `Stream.readinto()` (`_read_exact()`), which does a single
  non-accumulating read per call and so has to be looped. One allocation per fetch, made once the
  final size is known. **`readinto()` can return `None`** — poll said readable, the read still
  came back empty, the race `Stream.read()`'s own retry loop exists to ride out. It reaches this
  caller directly and must be retried; only a real `0` means the peer closed, and an EOF inside a
  sized body raises `IncompleteResponseError`. Conflating the two
  reads as an intermittent, environment-dependent false `IncompleteResponseError` under scheduling
  jitter, which a quiet sandbox rarely reproduces.
- **Unsized (no `Content-Length`) →** a fallback, not a live path: `src/asy_webserver_service.py`
  sends the header on every response — `Response.complete()` adds it for a bytes body,
  `_pieces_response()` for the streamed JSON routes, and `_StaticRoutes.serve()` sets it from the
  opened file's size for the frozen website — so none of its responses ends at EOF. Here
  `_read_until_close()` collects fixed-size chunks in a list and joins them once, rather than one
  bigger contiguous copy per read.

Either path still makes one whole-body allocation, `_read_exact()`'s buffer or the final
`b"".join(chunks)` (~16KB for the largest device's `GET /` page; the bundle `/js/app.js` is ~28KB
on every device). That is fine for a caller that needs the bytes, but **no real device ever holds
one**: the static route reads and writes the file in `chunk_bytes` pieces (256 B; it sets the
response's `send_file_buffer_size`, Microdot's 1,024 B default otherwise; SPECIFICATION.md
Part I.3), and a browser assembles the body from those over the wire. A caller that only checks
`status_code` passes `read_body=False` and takes the matching drain sibling instead,
`_drain_exact()` (or `_drain_until_close()` for an unsized body) — SPECIFICATION.md Part I.4(g),
relieve the pressure at its source rather than paper over an avoidable allocation with a GC-policy
change. No explicit `gc.collect()` belongs anywhere near this: `py/gc.c`'s `gc_alloc()` already
runs a full collect-and-retry before it ever raises `MemoryError`, so a stale response's garbage is
reclaimed exactly when an allocation needs the room.

That distinction was found by a real CI failure, and is the reason `read_body=False` exists: one
device's frozen website (its `GET /` page, then 7579 bytes, 168-483 bytes larger than the other
devices') tipped that one allocation over a fragmented-heap edge at `gc.threshold(-1)` where the
slightly smaller sites did not. The fix was calling the draining sibling from the hot soak loop —
not shrinking the site, and not reaching for a threshold.

### `unixport/_unix_port_udp_addr_shim.py` (real UDP round trips under the Unix port)

The file sits in `digital_twin/unixport/`, a directory holding no `machine`, `network` or
`neopixel` fake, so a unit test can put it on `sys.path` without the twin's fakes shadowing
`tests/`' own. Every importer inserts that directory itself,
`sys.path.insert(0, "digital_twin/unixport")`, `run_generic_integration.py` included, so no
`MICROPYPATH` needs to name it; and it stays inside `digital_twin/`, so the lint and type scopes
are unchanged (both mypy passes carry the directory on their `mypy_path`).

`patch_asy_udp_socket_for_unix_port()` runs once, before any `UDPSocket` exists: every entry that
boots a device calls `prewarm_poll_set()` then the shim first
(`tests_scripts/test_twin_entry_point_order.py`). The port-53 tests need `CAP_NET_BIND_SERVICE` on
the interpreter (`scripts/test.sh` and `scripts/run_digital_twin_ci.sh` grant it); Run 7 checks the
capability first and fails naming it.

> **Two messages tell the two port-53 faults apart**: "the real DNSServer never bound its port 53
> socket" is a missing capability (a file run directly skips `scripts/test.sh`'s `setcap` — check
> `getcap` first); "real hotspot activation never started the real DNSServer task" is CPU starvation.

Works
around three confirmed MicroPython-Unix-port-only `socket` quirks that otherwise make a real UDP
round trip (DNS, NTP) impossible under this harness, entirely from twin-side code (the divergence
and its trigger: SPECIFICATION.md Part F.7):

1. `bind()`/`connect()` reject `UDPSocket`'s own plain `(host: str, port: int)` tuple with
   `TypeError: object with buffer protocol required` — the Unix port's `socket` module
   (`ports/unix/modsocket.c`) requires a pre-resolved buffer-protocol sockaddr instead. The real
   rp2/lwIP module (`extmod/modlwip.c`) accepts the plain tuple directly (confirmed by reading both
   C sources side by side, not just the type stub — see `BACKLOG.md`'s "Real-hardware verification
   gap" entry for the full account), so this is genuinely two different implementations, not one
   port being stricter about the same contract. `src/` passes and accepts only `(host, port)`
   tuples; the shim keeps the packed form outside `src/`.
2. `sendto()` has this exact same requirement (`micropython/micropython#6924` is specifically about
   this method) — but its destination address is a per-call argument (a DNS/NTP client's ephemeral
   reply address, learned dynamically), not the constructor-time address point 1 already covers.
3. `recvfrom()` hands back the raw 16-byte packed C `struct sockaddr_in` as a plain `bytes` object,
   not the `(ip: str, port: int)` tuple `lwip_socket_recvfrom()` returns on real hardware and
   `asy_captive_dns.py`'s own subnet check expects — confirmed directly against a real captured reply,
   not just the C source (this build's actual behavior differs from what a first look at
   `modsocket.c`'s own separate `socket.sockaddr()` utility function would suggest).

The patch pre-resolves via `socket.getaddrinfo()` before `bind()`/`connect()`/`sendto()` (same
pattern `unix_port_poll_prewarm.py`'s `prewarm_poll_set()` already uses for a different call site)
and unpacks `recvfrom()`'s raw struct into the `(host, port)` tuple production code expects, so
`src/` only ever sees tuples. The shim also refuses any destination outside `127.0.0.0/8`, `0.0.0.0`
and `192.0.2.0/24` through the product's own failure path and counts it; the runner prints
`public_destinations_refused=<n>` and the CI suite requires 0. Every real call site
this project has (`asy_captive_dns.py`'s `"0.0.0.0"`, `asy_ntp_client.py`'s already-DNS-resolved NTP
server IP via `asy_dns_client.py`) already hands over an already-numeric address, so the
`getaddrinfo()` calls here are always fast and local, never a real DNS lookup.

A server's wildcard bind (`asy_captive_dns.py`'s `("0.0.0.0", 53)`) is bound on `127.0.0.1`, the
host loopback where every twin interface lives (the device's "all interfaces"). The host's wildcard
would also claim the host's other interfaces. Linux also refuses it beside a socket that holds one
specific address on the port without `SO_REUSEADDR`: some CI runners carry a `dns-resolver` on
`127.0.0.100:53`, on which the twin's captive DNS never bound (`DNSSRV` E10). The twin's
`127.0.0.1:53` shares no address with it. `tests/test_asy_udp_socket.py` holds such a socket and
binds beside it.

## Adding a new chip fake

**Required whenever a new sensor driver lands in `src/`** (see `SPECIFICATION.md` C.11's own
checklist item for this — do it the same session the driver is promoted, not deferred) — the
digital twin exists to track the *whole* real driver portfolio. For a new **I2C** sensor this is a
small, mechanical addition:

1. Read the sensor's own datasheet first (`CLAUDE.md`'s standing "read the PDF first" rule, `datasheets/`)
   and add a new `_<chip>_chip.py` whose class is `<NAME>Chip`, spelled as the driver's `_NAME`
   (`SCD30Chip`, `ISL29125Chip`), matching the established shape:
   - a `FaultInjector` (`self.fault`, see `_fault_injection.py`) for provoking a bus NAK/
     CRC-corruption/timeout on demand, passed the command word, register or opcode as `key=` on every
     `maybe_raise()`, so a fault can target one command;
   - a `random_source` constructor seam (owner, 2026-08-12; default `None` → falls back to the real
     `random` module) so tests can script deterministic values, and `digital_twin/launch.py --seed`
     can reseed every chip's walk from one shared source;
   - a `Walk(lo, hi, step)` per value, a bounded random walk (owner, 2026-08-12, round 2): `lo`/`hi`
     inside the datasheet's range, citing its page, the step a **not**-datasheet-derived
     physical-plausibility judgment call, said so in a comment;
   - a `timer_factory` if the chip has its own measurement clock (never `import machine` itself),
     and a `power_cycle()` that puts it back in its power-up state;
   - `handle_writeto()`/`handle_readfrom_into()` (word/CRC-framed protocols like SCD30/SGP40) or
     `handle_writeto_mem()`/`handle_readfrom_mem()` (register-addressed protocols like BMP3xx's)
     answering the *exact* raw transaction shape the real `*_I2C` driver class sends — confirmed
     directly against that file's own source, never assumed;
   - every test-only knob commented "twin-only test knob" and listed in its `TEST_API`.
2. Wire it into `machine.py`'s `_build_i2c_chip()`: add an `if driver == "<name>":` branch
   constructing the new chip fake (the wiring plan itself — which bus, which address — is already
   generic and needs no per-chip code; see "Booting a generated device" above). If the chip's real
   I2C address is hardwired (no TOML `address` field), declare it as a module-level const in the
   driver (`_<DRIVER>_ADDR = const(<int>)`), which buildgen reads (`buildgen/twin_wiring.py`'s
   `fixed_address()`); generation stops with a named error if the driver has none.
3. Add `tests/test_digital_twin_<chip>.py` — deterministic unit tests of the chip fake in isolation
   (no real `machine.I2C` involved) — then extend `tests/test_digital_twin_machine.py`'s own dispatch
   tests if the new chip shares a bus id those tests already probe.
   `tests_scripts/test_twin_fake_catalog.py` fails until the fake, its dispatch and its test exist.
   Every fact the fake does not model is a fidelity-table row.
4. Update this file's "What's here" list to mention the new chip, and
   consider whether `digital_twin/launch.py`'s own `_sensor_loop()`/`_FAULT_DEVICE_OPS` should read
   from it too.
5. The new driver's website fields come from its `@web` tags alone (`SPECIFICATION.md` Part H.5/K.4) —
   nothing to edit here or in any definitions file.

A new SPI device on an occupied bus id needs chip-select routing in the twin first: `machine.SPI`
wires one fixed device per bus id, while real multi-device chip-select is bit-banged by the caller
(`asy_spi_driver.py`'s `SPIDevice`), so a twin `SPI.write()`/`readinto()` would have to route by which
CS `Pin` is asserted low, the way `machine.I2C` routes by address (fidelity table).

## Code quality tooling

`digital_twin/` is in the ruff scope; mypy checks it in its own pass (`digital_twin/typecheck.ini`,
which `scripts/typecheck.sh` always runs with no paths, its `files` naming the twin tests too), because
each bare `machine`/`network`/`neopixel` resolves to one file per run (SPECIFICATION.md B.15).

## Harness pitfalls

- **Unix-port facts that break a harness written by habit** (confirmed against the pinned build):
  no `socket.getsockname()`; `getaddrinfo()` returns a packed `sockaddr` (both: SPECIFICATION.md
  Part F.7, with their trigger); `asyncio` offers `Lock` and `Event` but no `Semaphore`;
  `os.environ` is missing, so read `os.getenv()`; and `micropython.mem_info()` with any argument
  prints the full block map. Every Unix-port-vs-rp2 difference worked around in test code is listed
  in SPECIFICATION.md F.7.
- **A launch string over 255 bytes kills the Unix port before its script runs**: every argument
  from the script on, the script's real directory and every `MICROPYPATH` entry but a `~/` one built
  from `$HOME` is interned as a qstr, and a longer one raises outside any handler (`FATAL: uncaught
  NLR`, exit 1), which reads as a twin that exited before ever serving. A deep logs directory or a
  long scenario name reaches it through the state paths, so `scripts/_twin_process.py`'s `spawn()`,
  `scripts/test.sh`, `tests_js/_twin_process.js`'s `spawnTwin()`, `tests_hardware/twin_board.py` and
  `scripts/run_unix_port_integration.sh` refuse such a launch first, naming each string and its size
  (SPECIFICATION.md F.7 row 32). A module path over 255 bytes, a directory those checks pass plus the
  imported file's name, is not refused: it fails at that import with a plain
  `RuntimeError: name too long` traceback naming the import (`py/builtinimport.c:242`), so its cause
  reads plainly.

## Known gaps / follow-ups for later sessions

The one Unix-port defect the twin still works around, the poll-set growth `unix_port_poll_prewarm.py`
prevents, is stated in SPECIFICATION.md F.7 (row 12) with its removal trigger; every other modelling
gap is a row of the fidelity table above. `unix_port_idle_poll.py` removes a cost rather than a defect:
its entry above names its removal trigger.
