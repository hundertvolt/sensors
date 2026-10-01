# A-C merge TWIN (HEAD dd06040)

Scope: CLUSTERS.md "## TWIN" — every file under `digital_twin/` and every `tests/test_digital_twin_*` file (the 44
index paths plus the HEAD files the index does not name: `digital_twin/_crc8.py`, `tests/test_digital_twin_fram.py`,
the twelve per-device wrappers `tests/test_digital_twin_{construction,webserver_concurrency}_<device>.py`, and the new
files actions create here: `digital_twin/_twin_common.py`, `_wall_clock.py`, `run_device_script.py`,
`digital_twin/unixport/`, `tests/test_digital_twin_{rp2_constants,timer_pool,hot_replug,fram_crash_points,
uart_comm_hazard,uart_field_sweep}.py`). Constituents per file: the index's actions, plus every action whose Site,
Change or Blast slot names the file (grep of `audit/actions/*.md` by full path and by basename; 434 actions mention a
cluster path, 243 of them in a Site or Change slot). A product action whose Blast names an edit in a cluster file is
merged here as that edit; a Blast entry that names a cluster file with no edit owed ("holds", "unchanged", "— no twin
change") gets a ledger row "blast-only, holds" after the end state was checked against it.

**Conventions used by every merged change below** (each merged change names which apply; the mechanics are not repeated).

- **C0 Lines and units.** Line numbers are HEAD `dd06040`; `git diff 6b19da7 dd06040 -- digital_twin tests/test_digital_twin_*`
  is empty, so every U25 citation (written at `6b19da7`) holds verbatim. Units run in number order (plan 4.1: U0 B0;
  U1-U8 B1; U9-U34 B2; U35-U37 B3-B5). A merged change lands in the latest unit among its constituents unless a stage
  is listed. Every upstream line cited below is v1.29.0 and is re-checked against the refreshed pin before execution
  (OR129.a (5), AC_NOTES 34 (second)); fake semantics this merge restates were re-read in the scratchpad `mp/` checkout
  (v1.29.0): `ports/rp2/machine_i2c.c:61-112`, `machine_spi.c:161-214`, `machine_uart.c:455-480`,
  `machine_timer.c:50-145`, `machine_mem_backup.c:36-43`, `extmod/machine_mem.c:131-148`, `modmachine.c:57-88`,
  `machine_rtc.c:50-98`, `shared/runtime/mpirq.c:68-108`, `py/scheduler.c:100-118`.
- **C1 U10 rename sweep reaching the twin** (mechanical, landing with each renaming action in U10, found by its own
  grep/typecheck method; `digital_twin/` and the twin tests are type-checked by the twin pass): module names (A.U10.37:
  `system_service` → `asy_system_service`, `print_log` → `asy_print_log`, `captive_dns` → `asy_captive_dns`,
  `config_manager` → `asy_config_manager`, `base_classes` → `asy_base_classes`, `crc_checks` → `asy_crc_checks`,
  `framing_codecs` → `asy_framing_codecs`, `api_response` → `asy_api_response`), class names (A.U10.38:
  `AsyUDPSocket` → `UDPSocket`, `AsyFramManager` → `FRAMManager`, `AsyConnTime` → `WifiService`, `UART_Comm` →
  `UARTComm`, `UartLinkExerciser` → `UARTLinkDriver`, `DNSServer` → `CaptiveDNS`, `BMP3xx_Reader` → `BMP3XX_Reader`,
  …; the twin's own chip classes are A.U25.62's, M.TWIN.010-014), attributes made private (A.U10.35, S09's list, e.g.
  `UDPSocket.sock` → `_sock`; `UDPSocket.connected` stays public per M.SRC_NET.026), lock names (A.U10.18),
  REST/config keys (A.U10.40 map: `NTP_Host` → `NTPHost`, `MeasInt` → `MeasInterval`, `TempOffs` → `TempOffset`,
  `lightCmdLED` → `LightCmdLED`, …), unit suffixes (A.U10.43), starter/coroutine names (A.U10.44), the supervisor split
  (A.U20.06: `start_and_check_tasks()` → `start_tasks(starters, task_names=…)` + `supervise_tasks()`; `task_names`
  required, GAP-G5 of M_SRC_CORE). Each test file's merged change names which reach it.
- **C2 Harness migration in the twin tests** (U24/U25): `run()`/`run_timed()`/`_cancel*` → `tests/_async_harness.py`
  (A.U24.08; a bounded copy keeps its bound, `run(coro, <s>)`); `_FixedRandom` → `tests/_twin_random.py` `FixedRandom`
  (A.U24.30); MicroPython-side port allocators → `tests/_port_bands.py` (A.U24.70); folded `const()` mirrors →
  `tests/_src_const.py` (A.U24.01); response bodies → `strict_loads()` (A.U24.60); the canonical trailer (A.U24.04);
  `inject_fault(op, OSError(errno.X, "m"), times=n)` → `inject_fault(op, OSError, errno.X, "m", times=n)` (A.U25.70 /
  A.U24.78); generated modules through `tests/_generated_module.py` `load_generated(device)` (A.U10.30) after
  `tests/_generated_tree.py` `require_fresh()` (A.U24.46); the device set from `tests/_twin_devices.py`
  (`generated_devices()`, `wiring_plan(device)`, `device_with(driver)`, `device_with_shared_bus(a, b)`; A.U25.25 /
  A.U25.48, the one helper A.U24.65 also uses); catalog codes `code("E"|"W", <NAME>)` (A.U2.03).
- **C3 `@tunable` tags** (A.U8C/A.U8C2, grammar A.U8.02): every tagged literal becomes the module constant the U8C row
  writes, except a literal a later constituent deletes (polls of A.U25.45, the removed in-body `gc.threshold` of
  A.U30.13, the driven windows of A.U35.14, the in-DUT HTTP code A.U25.46 moves host-side): its row is withdrawn, named in
  the merged change. Row basis texts are U8's (SPEC Part N, SPEC cluster).
- **C4 Twin boot discipline for an L2 file that builds a device graph in-process** (after U25): module level, first
  `prewarm_poll_set()` then `patch_asy_udp_socket_for_unix_port()` (A.U25.43, A.U25.34, checked by
  `tests_scripts/test_twin_entry_point_order.py`); before each build `machine.reset_peripherals()`,
  `network.reset_interfaces()`, `machine.configure_wiring(wiring_plan(device))` (A.U25.03, A.U25.24, A.U25.25,
  A.U25.27) and `write_offline_ntp_config(cfg_dir)` into the test's own scratch config dir (A.U25.33); the graph is
  booted through the generated `main(watchdog=machine.WDT(timeout=8000), cfg_path=…, web_host=…, web_port=…)` or its
  `build_system()`/`start_tasks(…, task_names=…)` halves (A.U20.02, A.U20.06, A.U25.69 keywords kept); a test that can
  reach a product reset catches `machine.SimulatedRebootError` and calls `asyncio.new_event_loop()` before the next test
  (A.U25.07); a reader's `TS` is `None` until the first NTP sync and a pre-sync cycle steps no error streak (AC_NOTES
  38's GAP-15 ruling) — so no L2 boot expects a sensor-task restart for want of NTP.
- **C5 Permanent text.** Comments, docstrings and README text cite no audit ID (G9/R12, AC_NOTES 4), carry actor tags
  "(owner|agent, YYYY-MM-DD)", state current facts (OR27.a; no "used to", "once", "the first version"), and every block
  is ≤ 3 prose lines under A.U27.28's counting (a line counts `ceil(len/110)`); a header that a constituent rewrites is
  written to that bar in the same edit, so A.U27.28's gate finds nothing left to rewrap in this cluster.
- **C6 rp2 fidelity.** Every modelled rp2 fact cites its v1.29.0 source line on its comment line and is pinned by
  `tests/test_digital_twin_rp2_constants.py` (A.U25.68) or by the fake's own test; every knob that models nothing on
  silicon says "twin-only test knob" (A.U25.68), and every test-only public name is listed in the class's `TEST_API`
  tuple (A.U24.18's twin half).

## digital_twin/_twin_common.py (new)

### M.TWIN.001 One twin helper module: bounded log, counter cap, buffer fill, walk
- **From**: A.U25.22 (`_BoundedLog` in a new `_bounded_log.py`), A.U25.23 (`COUNTER_CAP` there), A.U25.06 (a `_fill`
  helper "in each file" — `machine.py` and `_fram_chip.py`), A.U5.15 (shared twin type `Walk(lo, hi, step)`, home unnamed)
- **Site**: new `digital_twin/_twin_common.py`
- **Change**: one module, importing nothing from `digital_twin/` or `src/` (so `network.py`, `neopixel.py` and every
  chip fake import it without `machine`): header (≤ 3 lines) "Shared twin helpers: the bounded bookkeeping log, the
  saturating counter cap, the buffer fill every fake read uses, and the value-walk bounds." Contents: `COUNTER_CAP =
  0x3FFFFFFF` with the comment "2**30 - 1, the project's shared counter cap (SPECIFICATION.md G.2); the twin keeps its own
  copy - it imports nothing from src/ (owner, 2026-08-12)"; `def saturating_add(value: int, n: int = 1) -> int` (`value +
  n if value <= COUNTER_CAP - n else COUNTER_CAP`; every twin counter steps through it or the `if x < COUNTER_CAP: x += 1`
  form); `LOG_MAXLEN = 200`; `class BoundedLog` (public: it crosses modules) — a `deque((), maxlen)` plus `dropped: int`,
  `append()` bumps `dropped` (saturating) when `len() == maxlen` before appending (a MicroPython `deque` drops its
  oldest item silently, `py/objdeque.c:107-118`), `__iter__`/`__len__`/`__getitem__(-1)` delegate (the twin tests index
  the newest entry), comment "Keep-last-N bookkeeping with a visible drop count; nothing in a running twin reads it.";
  `def fill_buffer(buf, data, idle: int = 0x00) -> None` — copies `n = min(len(buf), len(data))` bytes into `buf[:n]`
  and writes `idle` into the rest, never shrinking a `bytearray` or raising on a `memoryview`, comment "the level an idle
  MISO/SDA reads is the fake's documented choice: 0x00 (idle line, fidelity table)"; `Walk = namedtuple("Walk",
  ("lo", "hi", "step"))` with the comment "A chip fake's value range and per-reading step; the step is not
  datasheet-derived (a plausibility bound)".
- **Resolved**: A.U25.06 asks for one fill helper per file while REF/R05 / OR24 ask for one material; a shared module the
  chip fakes may import without `machine` (A.U25.22's own reason for a helper module) satisfies both, so the two copies
  become one; `_bounded_log.py` (A.U25.22/.23) takes the wider name because it now holds four helpers; `_BoundedLog`
  becomes `BoundedLog` because another module imports it (G10/R07 private-by-default covers only names nobody else reads)
  — agent decisions, OR2.c list.
- **Unit**: U25 (stage U5: A.U5.15 creates the module holding `Walk` only, U25 adds the rest)
- **Depends**: A.U10.01 (cap value)
- **Blast carried by**: users `machine.py` (M.TWIN.024-036), `network.py` (M.TWIN.040), `neopixel.py` (M.TWIN.042), the
  chip fakes (M.TWIN.010-014), `launch.py` (M.TWIN.044); A.U10.05's counter-step AST check scans `digital_twin/*.py` and
  pins `COUNTER_CAP` equal to `src/`'s value (A.U25.23, TSC cluster: `tests_scripts/test_counter_steps.py`); new L2
  `tests/test_digital_twin_machine.py` cases for `BoundedLog` (cap, `dropped`, order) and `fill_buffer` (bytearray keeps
  its length, memoryview does not raise) (M.TWIN.126); ruff scope and the twin mypy pass pick the file up by directory
  (no config change); README "What's here" bullet (M.TWIN.058)
- **Kind**: code

## digital_twin/_fault_injection.py

### M.TWIN.002 `FaultInjector`: fresh exceptions, targeted entries, refused ops, pending count
- **From**: A.U25.70 (fresh `exc_type(*args)` per raise, `match`, `pending()` named as A.U24.78's contract), A.U24.82
  (`pending(op)`), A.U25.18 (`raisable_ops`), A.U24.17 (`check_inject_fault_fifo` runs on a chip's injector), A.U25.68
  ("twin-only test knob" wording), A.U27.28 (header over the cap: three lines of ~240-600 characters), A.U0.31 (no tag
  here; its `launch.py:2` tag covers the CLI that exposes this API)
- **Site**: `digital_twin/_fault_injection.py:1-40` (header, `FaultInjector`)
- **Change**: header → "Twin-only test knob shared by every chip fake: an op-keyed FIFO of bounded faults (fresh exceptions,
  optionally aimed at one command key) and of blocking hangs. A hang is a real time.sleep(), not asyncio.sleep(): an rp2
  bus call has no await point, so a wedged peripheral freezes the whole interpreter (SPECIFICATION.md F.2)." (3 lines;
  the address-level NAK sentence goes — `machine.py`'s `I2C` docstring states it). Class: `__init__(self, raisable_ops:
  "tuple[str, ...] | None" = None)`; `_queues: dict[str, list[tuple[type[BaseException], tuple[object, ...], int |
  None]]]`; `inject_fault(op, exc_type, *args, times=1, match=None)` — refuses `times < 1` with `ValueError`, refuses an
  op outside `raisable_ops` (when given) with `ValueError(f"{op!r} cannot raise on this bus (rp2) - see
  digital_twin/README.md's fidelity table")`, then appends `times` entries `(exc_type, args, match)`;
  `maybe_raise(op, key=None)` raises `exc_type(*args)` — a fresh instance every time — when the head entry's `match` is
  `None` or equals `key`, and leaves the queue unchanged otherwise; `pending(op) -> int` returns the queued entry count
  (0 for none); `inject_hang`/`maybe_hang`/`clear` unchanged in behaviour (their comments ≤ 3 lines, `clear()` gains
  "# empties both queues for one op, or every op"). `match` means the key the transfer carries: the 16-bit command word
  of a word protocol (`(data[0] << 8) | data[1]`), the register address of a `*_mem` transfer, the opcode of an SPI
  transaction — the same meaning A.U24.78 gives the unit fakes, plus their separate `address=` filter, which the twin
  needs no equivalent of (each injector belongs to one chip). `TEST_API = ("inject_fault", "maybe_raise",
  "inject_hang", "maybe_hang", "clear", "pending")`.
- **Resolved**: U25 conflicts row 9 (one meaning of `match`) — settled by A.U24.78's own text, written after A.U25.70:
  the unit fakes adopt the twin's key meaning and keep the device address as a separate `address=` filter; nothing left
  to decide. A.U24.82 and A.U25.70 both add `pending()` — one method.
- **Unit**: U25
- **Depends**: M.TWIN.001
- **Blast carried by**: chip fakes pass `key` and build their injector (`FRAMChip` with `raisable_ops=("readinto",)`) →
  M.TWIN.010-014; both runners' `_apply_fault()` pass `(OSError, errno.EIO, message)` and an optional `match` →
  M.TWIN.045, M.TWIN.050; the CLI `--fault DEVICE:OP[:TIMES[:MATCH]]` → M.TWIN.044; the 16 `.fault.inject_fault(` calls in
  `tests/test_digital_twin_*.py` and `tests/_digital_twin_construction_scenarios.py:182` → C2 per file (M.TWIN.100-164) and
  TEST_HELP (A.U25.70 / A.U24.47); `tests/_machine_contract.py` `check_inject_fault_fifo` (A.U24.17, TEST_HELP) runs on
  a chip injector; new L2 `tests/test_digital_twin_scd30.py` cases (a fault matched to `0x0300` spares a `0x0202` read
  and hits the next `0x0300`; two raises of one queued fault are distinct objects; `pending()` counts down) →
  M.TWIN.142; README fault section → M.TWIN.068
- **Kind**: code

## digital_twin/_crc8.py

### M.TWIN.003 CRC-8 header names the renamed product module
- **From**: A.U10.37 (C1: `src/crc_checks.py` → `src/asy_crc_checks.py`, named in the docstring); U25 G2/R07 row (golden
  vector DONE-AT-HEAD at `tests/test_digital_twin_sgp40.py:35` — nothing to do); A.U8 tunable scan (`_crc8.py:3` the CRC
  polynomial: a datasheet fact, untagged — nothing to do)
- **Site**: `digital_twin/_crc8.py:1`
- **Change**: "`src/crc_checks.py`'s own CRC8" → "`src/asy_crc_checks.py`'s CRC8"; the one-line header (≈ 290 characters,
  3 counted lines) stays within A.U27.28's cap; `_CRC_POLY = 0x31` gains its source on the line "# Sensirion CRC-8:
  0x31, init 0xFF (SGP40 datasheet Table 7, SCD30 Interface Description 1.1.3)" (G7/R03 / C6; read in `dstxt/sgp40…:487-491`, `dstxt/scd30…Interface_Description.txt:161-170`).
- **Resolved**: —
- **Unit**: U10 (the citation lands with M.TWIN.014 in U25)
- **Depends**: A.U10.37
- **Blast carried by**: none beyond the file (text only)
- **Kind**: doc

## digital_twin/_bmp3xx_chip.py

### M.TWIN.010 BMP3xx fake: reset values, hooked probe, keyed faults, power cycle, cited ranges
- **From**: A.U25.13 (reset values on construction and 0xB6, `maybe_hang("writeto")` on the probe, chip-ID comment),
  A.U25.62 (`Bmp3xxChip` → `BMP3XXChip`), A.U25.42 (`import random` to module top), A.U25.41 (this file keeps the one
  `_decode_calibration()`), A.U25.70 (key = register address on `*_mem`), A.U25.59 (`power_cycle()`), A.U25.18 (I2C
  fakes keep every op raisable — no change), A.U25.73 (value-range citations — gap here, see Resolved), A.U25.01
  (fidelity rows reference this file), A.U27.28 (header over the cap), A.U15.R03 Blast ("twin resets `_osr` and
  `_config` … U25"), A.U24.30 Blast (random steps unchanged), A.U15.25 Blast (`:184` OSR readback unchanged), A.U0.07
  (its `_PENDING` entry `_bmp3xx_chip.py:101` empties), A.U5.15 (the walk bounds take `Walk`), A.C.16 (phase-C delta)
- **Site**: `digital_twin/_bmp3xx_chip.py:1-2` (header), `:21` (chip ID), `:33-40` (constants, calibration comment),
  `:89-120` (class, `__init__`), `:149-171` (`handle_writeto`, `handle_writeto_mem`), `:173-192` (`handle_readfrom_mem`)
- **Change**: header → "Twin fake of the Bosch BMP388/BMP390 (I2C 0x77): answers asy_bmp3xx_driver.py's register
  protocol with raw ADC bytes that decode, through the real compensation formula inverted by Newton's method, to a
  walked pressure and temperature. The calibration block is synthetic (digital_twin/README.md fidelity table)." (3
  lines). `import random as _random_module` at module top; the in-function import goes. `_BMP390_CHIP_ID = 0x60  #
  BMP390's id; BMP384/BMP388 answer 0x50 (fidelity table)`. New `_OSR_RESET = 0x02`, `_CONFIG_RESET = 0x00`, each cited
  to the BMP388 datasheet register table (`dstxt/bmp3xx__bst-bmp388-ds001.txt:1272-1283`, "DS001 register map" on the
  line). The `:38-39` comment → "# T1-T3, P1-P11 raw coefficients: synthetic, chosen so the inverted compensation
  round-trips across the walk's range (fidelity table)". Class `BMP3XXChip(random_source=None, temp: Walk =
  Walk(15.0, 30.0, 1.0), pressure: Walk = Walk(950.0, 1050.0, 5.0))` (A.U5.15 grouping), with the bounds comment
  "# not datasheet-derived: room ranges inside the BMP388's 300-1250 hPa, -40-85 C operating range (DS001 Table 1);
  the step is a plausibility bound"; `self._osr`, `self._config` start at the reset constants and `_status =
  _STATUS_CMD_RDY`. `handle_writeto(_data)`: `self.fault.maybe_hang("writeto")`, `self.fault.maybe_raise("writeto")`;
  its two comment blocks → one "# Only the driver's zero-byte presence probe calls plain writeto(); every register access
  goes through writeto_mem()." `handle_writeto_mem`/`handle_readfrom_mem` pass `key=reg_addr` to `maybe_raise`. 0xB6
  sets `_osr`, `_config` to the reset constants and `_status = _STATUS_CMD_RDY` (the DS001 sentence cited:
  `ds001:1717-1718`). New `power_cycle()` — "twin-only test knob: a re-plugged chip powers up" — restores the
  construction state except the walk position: reset constants, `_status = _STATUS_CMD_RDY`, `_burst = bytes(6)`.
- **Resolved**: A.U25.73 cites the SGP40/SCD30 ranges only; this file's `:107` comment "Not datasheet-derived (the
  min/max above are)" is false (15-30 °C / 950-1050 hPa are room ranges, the part's range is 300-1250 hPa, -40-85 °C) —
  G7/R03's "a judgment-call value is labelled 'not datasheet-derived'" settles the wording; adherence fix, agent. A.U5.15
  groups only the SCD30 and ISL29125 constructors; the same `Walk` grouping is applied to this fake and the SGP40's so the
  four chip fakes share one constructor shape (D.10 API consistency; agent, OR2.c list).
- **Unit**: U25
- **Depends**: M.TWIN.001, M.TWIN.002; A.U15.R03 (the driver rung that re-applies OSR/IIR)
- **Blast carried by**: `machine._build_i2c_chip()` constructs `BMP3XXChip` → M.TWIN.023; `launch.py`'s calibration copy
  goes and imports `_decode_calibration` → M.TWIN.044; `_HANG_DEVICE_OPS["bmp3xx"]` gains `writeto` → M.TWIN.044; tests
  (OSR 0x02 at power-up and after 0xB6 following 0x0D; a queued `writeto` hang delays the probe; the probe test asserts
  register state unchanged and a queued `writeto` fault consumed; `BMP3XXChip` rename; `FixedRandom` and the step
  override assertion) → M.TWIN.100; hot-replug per driver → M.TWIN.116; fidelity rows (chip id, synthetic calibration,
  no conversion time, 0xB6 reset values) → M.TWIN.059; phase-C probe keys `C01`/`C02` compared with this fake's reset
  (A.C.16, PROC/HW cluster; a divergence is an A.C.10 delta)
- **Kind**: code

## digital_twin/_fram_chip.py

### M.TWIN.011 FRAM fake: required RDID, rollover, strict framing, fill, rp2 fault surface, knobs, graceful load
- **From**: A.U25.15 (rollover, strict framing, `drop_next_wren`/`rdid_once`/`silent`, fault ops `wren`/`silent`),
  A.U25.06 (no shrinking `buf[:] = …` at `:149, :151, :153`), A.U25.18 (`raisable_ops=("readinto",)`, `maybe_raise`
  only for reads ≥ `_OVERRUN_MIN_READ = 32`), A.U25.29 (RDID required; `_DEFAULT_RDID` and the wozi/dev docstring go),
  A.U25.32 (3) (a file whose `"size"` differs loads nothing), A.U25.62 (`FramChip` → `FRAMChip`), A.U25.70 (`key` =
  opcode), A.U25.68 (knobs say "twin-only test knob"), A.U28.35 (`:22`'s `datasheets/fram/` citation — goes with the
  constant it sits on; the RDID citations move to `machine.py`'s table, M.TWIN.025), A.U27.28 (header), A.U25.37 (the
  `fram` vocabulary `readinto|wren|silent`), A.S0930.17 / A.S0930.27 Blast (the erase's 1,024 × 256 B writes and the
  WREN-drop refusal run against this fake), A.U16.R01/R02/R03 Blasts (the three knobs, "U25"), A.U16.09, A.U11.09,
  A.U13.03, A.U2.09, A.U3.04, A.U24.22 (Blasts: "no codes" / "sees no traffic" / independent — hold)
- **Site**: `digital_twin/_fram_chip.py:1-3, 13-33, 36-46, 57-94, 108-157`
- **Change**: header → "Twin fake of an SPI FRAM: answers asy_fram_driver.py's opcode/CS-session protocol, independent
  of tests/_fram_chip_fake.py. It frames each transaction by write() pairing, not by CS (fidelity table); its size and
  RDID come from machine.py's table." (3 lines). Constants: `_DEFAULT_RDID` goes; new `_OVERRUN_MIN_READ = 32  #
  ports/rp2/machine_spi.c DMA threshold, the one SPI path that can raise (pinned equal to machine._SPI_DMA_MIN_SIZE)`;
  `_SAVE_CHUNK_SIZE`'s comment → "# bytes per chunk streamed to disk: no one contiguous allocation for the whole image
  (README "FRAM persistence")". `class FRAMChip(size: int, rdid_response: bytes, state_path: str | None = None)` — `size`
  and `rdid_response` required; `self.fault = FaultInjector(raisable_ops=("readinto",))`; knobs, each commented
  "twin-only test knob": `drop_next_wren: int = 0` (each WREN while > 0 leaves WEL clear and decrements),
  `rdid_once: bytes | None = None` (answered by the next RDID only, then cleared), `silent: bool = False` (every
  `readinto()` fills `0x00`, every `write()` changes nothing: a deselected or lost chip). `_decode_addr()` masks
  `% self.size`. `_load_state()`: after the marker check, read `"size": N` from the 128-character header; a missing,
  non-integer or different size returns with `self.memory` blank (a state file of the other chip), the comment "#
  missing, malformed, truncated or other-size file: the factory-fresh chip (owner, 2026-08-13)". `write(buf)`:
  `maybe_hang("write")` stays (a hang models a stalled interpreter), `maybe_raise("write")` goes (rp2 SPI writes never
  raise); `silent` → return; the data phase copies byte by byte at `(addr + i) % self.size` (`self.memory` never grows),
  WEL auto-clear unchanged; a first `write()` whose opcode is WRITE and whose length exceeds opcode + address bytes
  raises `ValueError("FRAM fake: opcode, address and data in one write() - the fake frames by write() pairing
  (fidelity table)")`; WREN honours `drop_next_wren`. `readinto(buf, _write_value=0x00)`: `maybe_hang("readinto")`;
  `maybe_raise("readinto", key=self._pending_op)` only when `len(buf) >= _OVERRUN_MIN_READ` (a queued fault waits for
  the next long read); `silent` → `fill_buffer(buf, b"")`; READ fills byte by byte modulo `self.size`; RDSR and RDID
  through `fill_buffer()` (RDID from `rdid_once` when set, then cleared); every other case `fill_buffer(buf, b"")`.
- **Resolved**: A.U25.32's Site cites `_fram_chip.py:285-322`, past the file's end (157 lines); the code it means is
  `_load_state()` `:57-94` (read at HEAD) — line fix, no substance change. A.U25.06's local `_fill` is M.TWIN.001's
  shared `fill_buffer()`.
- **Unit**: U25
- **Depends**: M.TWIN.001, M.TWIN.002; A.U16.R01-R03 (driver users of the knobs)
- **Blast carried by**: `machine._wire_spi_device()` passes size and RDID from the one table → M.TWIN.025; `_apply_fault`
  for `fram:wren` (queues `drop_next_wren += times`) and `fram:silent` (sets the switch) in both runners → M.TWIN.044,
  M.TWIN.049; `tests/test_digital_twin_fram.py` (24-bit tests hold; new: write across the last address wraps, a read past
  the end wraps, one-write framing raises, `drop_next_wren=1` drops one WREN only, `rdid_once` answers once, `silent`
  reads zeros and ignores writes, RDID into an 8-byte buffer keeps 8 bytes, a 0x2000-size file into a 0x40000 chip loads
  blank, `write` injection raises `ValueError`, a `readinto` fault fires on a 32-byte read and not a 4-byte one,
  `_OVERRUN_MIN_READ == machine._SPI_DMA_MIN_SIZE`, one case per table RDID; the MB85RS64V-by-default test constructs
  with an explicit RDID; A.U16.R01/R02/R03's L2 cases; A.U16.09's double read) → M.TWIN.110; the CI suite's
  `_BUS_FAULT_OPS["fram"] = "write"` → `fram:silent` (A.U25.37, SCR cluster); `tests/test_fram_integration.py:3-5`
  comment (U16's, TEST_UNIT); fidelity rows (framing by pairing, rollover, refused faults, power loss granularity) →
  M.TWIN.059; Erase-FRAM L2 runs against rollover/`silent`/WREN-drop → M.TWIN.104, M.TWIN.051 (A.S0930.27)
- **Kind**: code

## digital_twin/_isl29125_chip.py

### M.TWIN.012 ISL29125 fake: bounded PRST count, hooked probe, keyed faults, timer factory, power cycle, assumption row
- **From**: A.U25.14 (PRST count stops at the target, `maybe_hang("writeto")` on the probe, CONFIG1-restart comment as an
  assumption), A.U25.62 (`Isl29125Chip` → `ISL29125Chip`), A.U25.42 (module-top `import random`; `from machine import
  Timer` goes, a `timer_factory` replaces it), A.U25.19 (the factory builds `Timer(_pool=False)`), A.U5.15 (`lux: Walk`
  grouping), A.U25.70 (key = register address), A.U25.59 (`power_cycle()` = the brownout), A.U25.68 (knobs say
  "twin-only test knob"), A.U25.37 (`int_stuck_high` reachable from the CLI — no change here, `configure_fault()` is the
  entry), A.U25.23 (`:194` counter — carried by A.U25.14's bound), A.U25.73 (ISL29125 range already cites p1 — holds),
  A.U25.52 (`:96-100` INT idles high — holds), A.U0.07 (`_PENDING` entries `:82, :121` empty), A.U27.28 (header over the
  cap), A.C.19 (phase-C delta), A.U15.28 / A.U15.32 / A.U15.37 Blasts (address unchanged; PRST/INTSEL already modelled;
  own register names — hold)
- **Site**: `digital_twin/_isl29125_chip.py:1-2` (header), `:4-25` (imports, Protocols), `:68-125` (class, `__init__`,
  `_start_timer`), `:183-203` (`_update_int`), `:217-222` (`simulate_brownout`), `:229-235` (`configure_fault`),
  `:239-246` (`handle_writeto`, `handle_writeto_mem`), `:265-270` (CONFIG1 comment), `:301-303` (`handle_readfrom_mem`)
- **Change**: header → "Twin fake of the Renesas ISL29125 RGB sensor (I2C 0x44): answers asy_isl29125_driver.py's
  register protocol with G/R/B counts from a modelled illumination through range gain, resolution and clipping, plus the
  destructive 0x08 read, the active-low INT and BOUTF at power-up (digital_twin/README.md fidelity table)." (3 lines).
  `import random as _random_module` at module top; the `TYPE_CHECKING` block keeps `Protocol`, imports `Callable` and
  `Timer` type-only, and the `:14` comment → "# type-only: machine passes the simulation Timer in through
  timer_factory". Class `ISL29125Chip(random_source=None, int_pin=None, lux: Walk = Walk(5.0, 9000.0, 400.0),
  gain_ratio=25.9, dark_counts=1, *, timer_factory: "Callable[[], Timer] | None" = None)`; the `:86-88` comment → "# lo/hi
  inside the datasheet's 375 / 10000 lux ranges (FN8424 p1); the step is not datasheet-derived (a plausibility bound)".
  `_start_timer()` builds `self._timer = self._timer_factory()` once (`None` factory → no Timer: the fake converts only
  on `set_illumination()`), the "reused, never replaced" comment kept. `_update_int()`: `target = _PRST_CYCLES[(…) >> 2]`
  read once; `if self._prst_count < target: self._prst_count += 1`; `if self._prst_count < target: return` (A.U25.14 (1)).
  `simulate_brownout()` → `power_cycle()`, comment "twin-only test knob: a supply event, not the 0x46 reset - every
  register to its power-on default and BOUTF up again (p12), the flag the driver's recovery keys on" (3 lines);
  `configure_fault()`'s comment gains "twin-only test knob" (the 3-line block keeps its reason). `handle_writeto(_data)`:
  `maybe_hang("writeto")`, `maybe_raise("writeto")`, comment "# Only the driver's zero-byte presence probe calls plain
  writeto(); every register access goes through writeto_mem()." (the pointer to `_bmp3xx_chip.py`'s comment goes — that
  comment is rewritten by M.TWIN.010). `handle_writeto_mem`/`handle_readfrom_mem` pass `key=reg_addr`. The `:265-267`
  comment → A.U25.14 (3)'s text ("# Assumption, not measured: a write to 0x01 restarts the conversion ('ADC start at I2C
  write 0x01', FN8424 Table 7, is all the datasheet says); the data registers keep the previous cycle until the next
  one completes. Fidelity row; never tuned to.").
- **Resolved**: A.U5.15 keeps `*, auto_refresh` in the grouped signature; A.U25.42 (later, U25) makes the chip's Timer
  come from `timer_factory` with `None` meaning no refresh — the two keywords would say one thing twice, so
  `timer_factory` replaces `auto_refresh` (tests' `auto_refresh=False` drops; the few that want the refresh pass
  `timer_factory=lambda: machine.Timer(_pool=False)`) — agent decision, OR2.c list. A.U25.59 asks for `power_cycle()` on
  every chip and names the ISL29125's as `simulate_brownout()`; one name across the four fakes, so the method is renamed
  and A.U25.68's knob list reads `power_cycle` — agent decision, OR2.c list. A.U25.49's L0 copy check (TSC) compares the
  chip's constants with the driver's by value; `_REG_CONFIG3` has no driver counterpart after A.U15.37 (U15) and is not
  compared (the chip keeps it: the fake models the register).
- **Unit**: U25 (stage U5: A.U5.15's `lux: Walk`)
- **Depends**: M.TWIN.001, M.TWIN.002, M.TWIN.030 (`Timer(_pool=False)`)
- **Blast carried by**: `machine._build_i2c_chip()` → M.TWIN.023; `_apply_fault` `isl29125:int_stuck_high` →
  `configure_fault()` in both runners → M.TWIN.044, M.TWIN.049; `_HANG_DEVICE_OPS["isl29125"]` gains `writeto` →
  M.TWIN.044; tests (A.U25.14's 50-cycle bounded-count case, the `:264-266` comment, A.U25.49 citations, renames,
  `power_cycle`, `timer_factory`) → M.TWIN.120, M.TWIN.122; A.U25.52's idle-high INT assertion (TEST_HELP's
  construction scenarios) reads `_int_pin`, unchanged; hot-replug → M.TWIN.116; fidelity rows (PRST bound, CONFIG1
  restart "assumption, never tuned to", BOUTF read-to-clear measured) → M.TWIN.059; BACKLOG real-hardware row "measure
  whether a CONFIG1 write restarts an in-flight ISL29125 conversion" (A.U25.14, DOCS cluster); phase C: A.C.19 (3)
  compares each SPEC M.1.2 row with this fake and a divergence is an A.C.10 delta (PROC/HW)
- **Kind**: code

## digital_twin/_scd30_chip.py

### M.TWIN.013 SCD30 fake: measuring status, argument CRCs, power-up reset, volatile FRC, NVM counter, graceful load
- **From**: A.U25.12 ((1)-(6): `_measuring` persisted, argument CRC, interval range, soft reset = power-up, volatile FRC,
  pressure-persistence assumption comment; (7) is `js/`, WEB cluster), A.U4.06 (`nvm_writes`), A.U25.32 (3) (non-dict,
  wrong-type, non-bool `measuring` load as factory), A.U25.73 (range and command citations), A.U25.62 (`Scd30Chip` →
  `SCD30Chip`), A.U25.42 (module-top `import random`; `timer_factory`), A.U25.19 (`Timer(_pool=False)` via the factory),
  A.U5.15 (`co2/temp/hum: Walk` grouping, ≤ 8 parameters), A.U25.70 (key = command word), A.U25.59 (`power_cycle()`),
  A.U25.23 (saturating counters), A.U25.68 ("twin-only test knob"), A.U27.28 (header), A.U0.07 (`_PENDING` `:74, :146`
  empty), A.C.15 (phase-C delta), A.U15.12 Blast ("a constant-CO2 knob is U25's if the step cannot be set to 0 from a
  test"), A.U15.R01 / A.U15.01 / A.U4.05 / A.U26.07 / A.U24.30 / A.U15.28 Blasts (0xD304 answered; range 400-2000 never
  left; raw offset word stored; 0x4600/0x0202/0x0010 modelled; random steps; address — hold)
- **Site**: `digital_twin/_scd30_chip.py:1-2` (header), `:4-28` (imports, Protocols), `:30-42` (command constants),
  `:54-108` (class, `__init__`), `:110-143` (`_load_state`, `save_state`), `:145-165` (`_start_timer`,
  `_produce_new_reading`), `:167-196` (`handle_writeto`), `:198-228` (`handle_readfrom_into`)
- **Change**: header → "Twin fake of the Sensirion SCD30 (I2C 0x61): answers asy_scd30_driver.py's word-command protocol
  with walked CO2/T/RH, checked argument CRCs and an RDY edge per measurement. The NVM-backed settings and the measuring
  status persist to a state file (digital_twin/README.md "SCD30 persistence")." (3 lines). `import random as
  _random_module` at module top; `from collections import namedtuple` at module top; `TYPE_CHECKING` imports `Callable` and `Timer` type-only. Command
  constants each cite their Interface Description v1.0 section on the line (`0x0010` §1.4.1, `0x0104` §1.4.2, `0x4600`
  §1.4.3, `0x0202` §1.4.4, `0x0300` §1.4.5, `0x5306` §1.4.6, `0x5204` §1.4.6 FRC, `0x5403` §1.4.7, `0x5102` §1.4.8,
  `0xD100` §1.4.9, `0xD304` §1.4.10 — read in `dstxt/scd30…Interface_Description.txt:252-1520`); new `_INTERVAL_MIN_S =
  2`, `_INTERVAL_MAX_S = 1800` (§1.4.3), `_FRC_MIN_PPM = 400`, `_FRC_MAX_PPM = 2000`, `_FRC_POWER_UP_PPM = 400` (§1.4.6
  FRC). New `SCD30Nvm = namedtuple("SCD30Nvm", ("measurement_interval_s", "measuring"))` and
  `_PROVISIONED_NVM = SCD30Nvm(2, True)` with A.U25.12 (1)'s comment ("not datasheet-derived: a factory SCD30 is idle
  until 0x0010; the twin starts from a provisioned unit so every boot produces readings - pass measuring=False to model an
  unprovisioned sensor"). Class `SCD30Chip(random_source=None, co2: Walk = Walk(400.0, 2000.0, 50.0), temp: Walk =
  Walk(15.0, 30.0, 1.0), hum: Walk = Walk(20.0, 70.0, 3.0), rdy_pin=None, nvm: SCD30Nvm = _PROVISIONED_NVM, *,
  timer_factory: "Callable[[], Timer] | None" = None, state_path: "str | None" = None)` (8 parameters); the walk comment
  → A.U25.73's "# not datasheet-derived: room ranges inside the datasheet's 400-10 000 ppm, -40-70 C, 0-100 %RH (SCD30
  datasheet :12, :67, :76); the steps are plausibility bounds"; the three walks are public attributes `co2`, `temp`,
  `hum`, commented "twin-only test knob: a test may replace a walk, e.g. step 0 for a constant CO2". State:
  `_measuring` (from `nvm`, then the state file), `_frc_reference = _FRC_POWER_UP_PPM`, `_corrupt_next = False`, counters
  `nvm_writes`, `bad_crc_commands` (both saturating through `saturating_add`). `corrupt_next()` (replaces the public
  attribute `corrupt_next_measurement`, same shape as `SGP40Chip.corrupt_next()`), "twin-only test knob". `_load_state()`:
  a non-dict JSON, a non-int value for any of the five settings, or a non-bool `measuring` returns with the factory
  values set above (comment "# missing, malformed, truncated or mistyped file: the factory-fresh chip (owner,
  2026-08-13)"); `measuring` loads beside the five. `save_state()` writes the six keys; the pressure key carries A.U25.12
  (6)'s comment ("persistence of the pressure value itself is an assumption (Interface Description 1.4.1 names only the
  status as NVM); BACKLOG real-hardware row"). `_start_timer()`: `None` factory → return; else `self._timer` built once by
  the factory and `init()`ed at the stored interval. `_produce_new_reading()` returns early while not `_measuring` (no
  data, no RDY edge). `handle_writeto(data)`: `maybe_hang("writeto")`; `key = (data[0] << 8) | data[1]` when `len(data)
  >= 2` else `None`; `maybe_raise("writeto", key=key)`; a 2-byte frame: `0x0104` sets `_measuring = False`, counts one
  NVM write; `0xD304` → `_power_up()`; a 5-byte frame whose `data[4] != crc8(data[2:4])` → `bad_crc_commands` +1 and
  return (comment "# assumption: the datasheet states no reaction to a wrong argument CRC; the fake ignores the command
  (fidelity row)"); 0x4600 outside [2, 1800] ignored the same way (assumption row; removes HEAD's 0 ms periodic Timer);
  0x5204 stores its argument in `_frc_reference` when in [400, 2000], else ignored (assumption row); 0x0010 sets
  `_measuring = True` and the pressure; every accepted 5-byte NVM command (0x0010, 0x4600, 0x5102, 0x5204, 0x5306,
  0x5403) and 0x0104 add one to `nvm_writes` (A.U4.06's set, Interface Description §1.4.1-1.4.3, §1.4.6-1.4.8).
  `_power_up()` (used by 0xD304 and `power_cycle()`): `_data_ready = False`, `_buffer = bytes(18)`, RDY driven low if it
  was high, `_frc_reference = 400`, the Timer re-armed at the stored interval; NVM values and the walk kept; comment "#
  Soft reset: 'the same state as after powering up' (Interface Description 1.4.10); NVM settings survive". New
  `power_cycle()` = `_power_up()`, "twin-only test knob: a re-plugged chip". `handle_readfrom_into(nbytes)`:
  `maybe_raise("readfrom_into", key=self._last_cmd)`; the FRC readback returns `word(self._frc_reference)` with the
  comment "# 'the most recently used reference … after repowering … 400 ppm' (Interface Description 1.4.6)"; the
  corruption flips word 1's CRC when `_corrupt_next` is set, then clears it. The class docstring's "regardless" claim
  and the `:193`, `:223` comments go (replaced as above).
- **Resolved**: A.U5.15's eight-parameter `Scd30Chip(random_source, co2, temp, hum, measurement_interval_s, rdy_pin, *,
  auto_refresh, state_path)` plus A.U25.12's `measuring` would be nine (over G6/R40's 8, outside A.U5.17/A.U5.18's exact
  exempt set); the two NVM defaults group into `SCD30Nvm` and `auto_refresh` gives way to A.U25.42's `timer_factory`, so
  the end state is 8 — agent decision, OR2.c list. A.U4.06 counts frames in `handle_writeto()` "the same frames" as the
  L1 bus helper; the fake counts only the commands it accepts (an ignored wrong-CRC or out-of-range command writes no
  NVM), the helper counts frames sent — documented in the fidelity row's counter line (agent decision, OR2.c list).
  A.U15.12's constant-CO2 need is met by the public walk attributes (step 0), so no separate knob. The public
  `corrupt_next_measurement` attribute becomes `corrupt_next()` for one shape with A.U25.11's SGP40 method (D.10; agent
  decision). Not in any action: §1.4.1 "Setting the ambient pressure will overwrite previous settings of altitude
  compensation" is not modelled — a G7/R03 fidelity row added (M.TWIN.059; adherence).
- **Unit**: U25 (stages: U4 — A.U4.06 adds `nvm_writes` on the HEAD shape, plain `+= 1` guarded `< COUNTER_CAP` once
  M.TWIN.001 lands; U5 — A.U5.15's walk grouping; U25 the rest). The U4 stage is needed by A.U4.02/A.U4.04's L2 tests.
- **Depends**: M.TWIN.001, M.TWIN.002, M.TWIN.030; A.U15.R01 (the driver rung that sends 0xD304)
- **Blast carried by**: `machine._build_i2c_chip()` (factory, `rdy_pin`, `state_path`) → M.TWIN.023; tests (A.U25.12's
  L2 set, A.U25.32's `"[1, 2]"`/`{"altitude": "x"}` cases, A.U4.06's counter test, A.U15.12's FRCState-4 boot with
  step 0, FRC 900/400 cases, the `:80-84` and `:106-112` rewrites, the `:227-230` range comment, 36 constructor calls
  regrouped) → M.TWIN.142; `tests/test_digital_twin_machine.py:207-223` (CRC-correct frame, holds) → M.TWIN.126;
  `js/mock-server.js` FRC readback and its test → A.U25.12 (7), WEB cluster; `tests_js/live-backend-put-matrix.test.js:21`
  → A.U25.12, WEB; README "SCD30 persistence" (six values, the assumption) → M.TWIN.062; fidelity rows (measuring
  default, CRC/interval/FRC assumptions, pressure persistence, counter line, altitude overwrite) → M.TWIN.059;
  `SPECIFICATION.md:4385` FRC sentence → A.U25.12, SPEC cluster; BACKLOG rows (pressure persistence, wrong-CRC reaction)
  → A.U25.12 / A.C.15, DOCS; phase C: A.C.15's script runs through the twin first (A.U26.05) and a silicon "accepted"
  is an A.C.10 delta (PROC/HW)
- **Kind**: code

## digital_twin/_sgp40_chip.py

### M.TWIN.014 SGP40 fake: general-call reset, heater-off, keyed faults, one corruption knob, cited range
- **From**: A.U25.10 (`handle_general_call()`, `resets`, docstring drops "general-call-reset"), A.U25.11 (heater-off
  branch, `_measuring`, `heater_offs`, `corrupt_next()`, unknown-command assumption comment), A.U25.73 (raw-range
  citation), A.U25.62 (`Sgp40Chip` → `SGP40Chip`), A.U25.70 (key = command word), A.U25.59 (`power_cycle()` = idle),
  A.U25.37 (`general_call` in the vocabulary), A.U25.23 (saturating counters), A.U25.68 ("twin-only test knob"),
  A.U27.28 (header), A.U5.15 (`raw: Walk`, applied for constructor consistency — M.TWIN.010 Resolved), A.U15.R02 Blast
  (the 0x3615 branch "U25" — carried by A.U25.11), A.U15.13 Blast (a public `corrupt_next()` "added by U25"), A.U12.18
  Blast (three concurrent measures each answered — holds, the reply is per write), A.U15.14 Blast (any tick words
  accepted — holds), A.U30.06 / A.U15.28 Blasts (unchanged — hold); A.U25.42 names three chip fakes, not this one (its
  `random` import is already at module top — nothing to do)
- **Site**: `digital_twin/_sgp40_chip.py:1-2` (header), `:23-25` (commands), `:28-57` (class, `__init__`,
  `_maybe_corrupt`), `:59-81` (handlers)
- **Change**: header → "Twin fake of the Sensirion SGP40 (I2C 0x59): answers asy_sgp40_driver.py's word commands
  (serial number, self-test, measure-raw, heater-off) with walked SRAW_VOC ticks, and resets on the I2C general call
  (datasheet Table 17). Independent of tests/machine.py's fake I2C." (3 lines). `_CMD_HEATER_OFF = b"\x36\x15"  #
  datasheet Table 14: hotplate off, idle mode`; `_CMD_MEASURE_RAW`'s line cites §3.1 ("launches/continues the VOC
  measurement mode"). Class `SGP40Chip(random_source=None, raw: Walk = Walk(26000, 34000, 1000))`; the
  `corrupt_next_reply` keyword goes; the range comment → A.U25.73's "# not datasheet-derived: a typical indoor walk
  inside the datasheet's SRAW_VOC range 0-65 535 ticks (SGP40 datasheet Table 1); the step is a plausibility bound".
  State: `_measuring = False`, `_last_cmd: int | None = None`, `_corrupt_next = False`, counters `resets`, `heater_offs`
  (saturating). `corrupt_next()` — "twin-only test knob: flips the CRC of the next reply's last word" — arms
  `_corrupt_next`. `handle_writeto(data)`: `maybe_hang("writeto")`; `self._last_cmd = (data[0] << 8) | data[1]` when
  `len(data) >= 2`; `maybe_raise("writeto", key=self._last_cmd)`; serial and self-test unchanged; measure-raw (8 bytes)
  sets `_measuring = True` and steps the walk; heater-off sets `_measuring = False`, `_pending_reply = bytes(3)`,
  `heater_offs` +1, returns; the catch-all keeps the pending reply, comment "# assumption: the datasheet states no
  reaction to an unknown command (fidelity row)". `handle_readfrom_into(nbytes)`: `maybe_raise("readfrom_into",
  key=self._last_cmd)`. New `handle_general_call(data)`: `maybe_raise("general_call")`; on `data == b"\x06"` →
  `_idle()` and `resets` +1, comment "# soft_reset 0x00 0x06 'resetting all devices connected to the same I2C bus'
  (datasheet Table 17); the gas walk is kept". `_idle()`: `_pending_reply = bytes(3)`, `_measuring = False`. New
  `power_cycle()` = `_idle()`, "twin-only test knob: a re-plugged chip". `_measuring` is read by tests only (no reply
  depends on it), commented so.
- **Resolved**: A.U15.13's L2 case sets `_corrupt_next_reply` "or a public `corrupt_next()` added by U25" and A.U25.11
  adds that method — the method is the one knob and the constructor keyword goes (its one caller,
  `tests/test_digital_twin_sgp40.py:170`, calls `corrupt_next()` after construction) — settled by A.U25.11's text. Read
  faults keyed by the last command word give the CI suite a way to aim Run 5's SGP40 fault at measure reads only
  (`sgp40:readfrom_into:3:0x260F`), sparing setup's serial read and the heater-off rung that AC_NOTES 31 found consuming
  the faults — the suite change is SCR's (Gaps).
- **Unit**: U25 (stage U5 for the `Walk` constructor)
- **Depends**: M.TWIN.001, M.TWIN.002; A.U15.R02 (driver rung), M.TWIN.024 (general-call delivery)
- **Blast carried by**: `I2C.writeto(0x00, …)` delivery and the EIO-when-nobody-answers case → M.TWIN.024;
  `machine._build_i2c_chip()` → M.TWIN.023; tests (`b"\x06"` clears a pending reply, other bytes do not; heater-off
  clears and counts once, next measure normal; `corrupt_next()` then `initialize()` gets a serial reply (A.U15.13);
  rename, `Walk`) → M.TWIN.150; general-call machine test (`resets` +1, BMP3xx on wozi `i2c1` keeps OSR/CONFIG; no
  SGP40 → EIO) → M.TWIN.126; bus-hazard general-call scenario now resets the twin SGP40, A.U15.R02's heater-off L2 case,
  A.U12.18's three-session case → M.TWIN.102; fidelity rows (general call reaches only chips that document it — ACK of
  others an assumption; unknown command; heater-off) → M.TWIN.059; BACKLOG row "does a general call to 0x00 on a bus
  without an SGP40 ACK or NAK on dev's buses" → A.U25.10 (DOCS); README `_sgp40_chip.py` bullet → M.TWIN.058
- **Kind**: code

## digital_twin/_http_client.py

### M.TWIN.016 Twin HTTP client: refusal vs incomplete response, typed stream, timeout parameter, tagged header
- **From**: A.U25.31 ((1) EOF mid-headers raises `IncompleteResponseError`; (2) pre-response `OSError` →
  `CeilingRefusedError`, after the status line → `IncompleteResponseError`; (3) is TEST_HELP's classifiers; (4) the
  `:35` ignore names its stub gap and removal trigger), A.U24.35 (withdrawn — carried by A.U25.31 (1)), A.U25.63 (`_Stream`
  Protocol; `json()` returns A.U10.46's alias), A.U25.42 (b) (the lazy `_strict_json` import stays, a named exception),
  A.U0.07 (its `_PENDING` entry `:32` becomes that named exception), A.U0.31 (`:1` tag "(owner, 2026-08-13)"), A.U26.70
  (docstrings name each other and the parity test; parameter names and order `host, port, method, path, json_body,
  timeout_s, read_body`), A.U27.28 (header over the cap), A.SDEP.15 (W11: the `:35` ignore is self-checking — removed
  if the refreshed stubs type `json.loads()` for a buffer), A.SDEP.17 (W40: if `extmod/asyncio/stream.py` stops
  re-concatenating, `readexactly()` becomes usable — a delta, no change otherwise), A.U24.60 Blast (`check_strict_json`
  already called — holds), A.U24.34 Blast (twin client via A.U25.31 — this change), A.U19.17 (names this file in
  `pyproject.toml`'s ANN401 category-2 comment — see Resolved)
- **Site**: `digital_twin/_http_client.py:1-2` (header), `:7-13` (typing), `:16-36` (`HttpResponse`), `:48-72`
  (`CeilingRefusedError`, parsers), `:75-138` (readers), `:141-181` (`fetch`)
- **Change**: header → "Minimal HTTP/1.1 client over asyncio.open_connection(): real HTTP over real sockets (owner,
  2026-08-13), hand-rolled because the Unix-port build freezes no client library. tests_hardware/http_client.py keeps
  the same shape, pinned by tests_scripts/test_http_client_shape_parity.py." (3 lines; the `Connection: close` sentence
  moves to `fetch()`'s comment). `TYPE_CHECKING` block: `from typing import Protocol`; `from asy_base_classes import
  JsonDict` (type-only, A.U10.46); `class _Stream(Protocol)` with `readline()`, `readinto(buf)`, `write(data)`, `drain()`,
  `wait_closed()` (async where MicroPython's `Stream` is), comment "# MicroPython's one Stream serves both directions
  (extmod/asyncio/stream.py)". `json() -> "JsonDict"`; the `:25-27` comment → "# Every body this client decodes is a
  JSON object - the REST envelope or a flat settings dict."; `:29-31` kept; `:32` keeps "here, not at the top: tests/ is
  absent from a standalone twin's path" (SPEC F.1 named exception, A.U25.42 (b)); `:35`'s ignore gains A.U25.31 (4)'s
  trigger ("- remove when micropython-stdlib-stubs types json.loads() for bytearray (stub gap: mod_json_loads() reads any
  buffer, v1.29.0 extmod/modjson.c)"). New `class IncompleteResponseError(OSError)` beside `CeilingRefusedError`, docstring
  "The server began a response and closed before finishing its header block or body." `CeilingRefusedError`'s docstring
  kept (3 lines). `parse_status_line(b"")` raises `CeilingRefusedError` (unchanged); `parse_header_line()` returns `None`
  only for `b"\r\n"`/`b"\n"`, and `b""` raises `IncompleteResponseError("connection closed inside the header block")`,
  comment "# None ends the header block; an EOF before the blank line is an incomplete response". `_read_exact`,
  `_read_until_close`, `_drain_until_close`, `_drain_exact` take `reader: "_Stream"`; `_read_exact`/`_drain_exact`'s
  `EOFError` → `IncompleteResponseError("connection closed inside the body")`. `fetch(host, port, method, path,
  json_body=None, timeout_s: float | None = None, *, read_body=True)`: with `timeout_s` the whole exchange runs under
  `asyncio.wait_for(…, timeout_s)` (an `asyncio.TimeoutError` propagates); `open_connection()`'s own `OSError` propagates
  unchanged (nothing listening); an `OSError` (EOF included) from `drain()` or the status-line read before any response
  byte is re-raised as `CeilingRefusedError(e.errno, "connection refused without a response (reject-when-full)")`; any
  `OSError` after the status line is re-raised as `IncompleteResponseError`; the `:150-152` comment → "# reader and
  writer are one Stream on this build; the socket closes only in wait_closed() below. Every response this client sees
  carries Connection: close (owner, 2026-08-13)".
- **Resolved**: A.U26.70 lists `timeout_s` between `json_body` and `read_body`; the twin's `fetch()` has none — it gains
  `timeout_s: float | None = None` (unbounded by default, today's behaviour; the parity test compares names and order,
  not defaults), agent decision, OR2.c list. A.U25.63 says `json()` returns A.U10.46's JSON alias; A.U26.70 requires the
  object-only form — A.U10.46's `JsonDict` (`dict[str, JsonValue]`) is both. A.U19.17 rewrites `pyproject.toml`'s ANN401
  category-2 comment to name only this file, and A.U25.63 (U25, later) removes this file's last `Any` — the
  per-file `ANN401` entry `pyproject.toml:310` and that mention go with A.U25.63 (TOOL gap).
- **Unit**: U25
- **Depends**: A.U10.46 (`JsonDict`); A.U24.34 (its classifier list, co-landing)
- **Blast carried by**: every `fetch()`/`.json()` caller in `tests/test_digital_twin_*.py` (success paths unchanged;
  nested indexing narrows with an `isinstance` assertion where mypy needs it) → C2/M.TWIN.100-164; the refusal
  classifiers in `tests/_webserver_concurrency_scenarios.py` (`:738` not a classifier, stays `except OSError`) →
  A.U25.31 (3) / A.U24.34 (TEST_HELP); `tests/test_digital_twin_bus_hazard_concurrency.py:99-104` classifier →
  M.TWIN.102; `tests/test_digital_twin_http_client.py` (`b""` terminator flips to the raise; new: close after
  `HTTP/1.1 200 OK\r\nContent-Length: 5\r\n` raises `IncompleteResponseError`, reset before any byte raises
  `CeilingRefusedError`, a closed port raises an `OSError` that is not `CeilingRefusedError`, `timeout_s=0.1` against a
  silent listener raises `asyncio.TimeoutError`) → M.TWIN.118; hardware client and parity test → A.U26.70 (HW_BENCH,
  TSC); README `_http_client.py` bullet and read-paths section → M.TWIN.058, M.TWIN.070; `pyproject.toml:310` →
  TOOL gap; SPEC F.1 exception list (b) → A.U25.42 (SPEC)
- **Kind**: code

## digital_twin/_unix_port_udp_addr_shim.py → digital_twin/unixport/_unix_port_udp_addr_shim.py

### M.TWIN.017 Move the UDP shim beside no fake; tuple-only src; public-destination guard
- **From**: A.U18.12 (move to "a directory holding no hardware fake (e.g. `unixport/…`)", main-pass `mypy_path`,
  `digital_twin/typecheck.ini`, both runners' `sys.path`; `:33-35` comment text), A.U18.13 Blast (wraps `_connect`
  unchanged — holds), A.U25.33 (3) (refuse destinations outside `127.0.0.0/8`, `0.0.0.0`, `192.0.2.0/24`;
  `public_destinations_refused` saturating; last refused destination recorded), A.U25.34 (1) (order enforced by an L0
  AST test; the module states the rule), A.U10.38 / A.U10.35 (C1: `AsyUDPSocket` → `UDPSocket`), A.U27.28 (header over the
  cap), A.SDEP.16 (W13: each Unix-port quirk fixed upstream → that half of the shim goes; conditional), A.SDEP.08 Blast
  (re-check at the pin move, catalog W13), A.U14.28 (F.7 row "led by" this file — SPEC; the file stays the
  workaround's home), A.U36.544 (SPEC pointer to the README's shim section — SPEC/DOCS)
- **Site**: `digital_twin/_unix_port_udp_addr_shim.py:1-77` (whole file; `git mv` to `digital_twin/unixport/`)
- **Change**: the file moves to `digital_twin/unixport/_unix_port_udp_addr_shim.py` (a directory holding no `machine`,
  `network` or `neopixel` fake, so an L1 test may put it on `sys.path` without the twin's fakes shadowing `tests/`';
  `digital_twin/` stays the ruff/mypy scope by directory — no ninth scope). Header → "Twin-side fix for the Unix port's
  sockaddr quirks (micropython#6924: bind/connect/sendto take a packed sockaddr, recvfrom returns one), so src/ only
  ever sees (host, port) tuples; it also refuses any UDP destination outside loopback and TEST-NET-1. Applied once,
  before any UDPSocket exists (digital_twin/README.md "_unix_port_udp_addr_shim.py")." (3 lines). `AsyUDPSocket` →
  `UDPSocket` throughout. `_resolve_plain_addr()`'s comment → "# getaddrinfo()'s sockaddr slot here is the opaque bytes
  object this Unix build's socket needs; src/ only ever sees tuples (IPv4-only project)." New
  constants `_ALLOWED_PREFIXES = ("127.", "192.0.2.")`, `_ALLOWED_HOSTS = ("0.0.0.0",)`, and `_REFUSED_SOCKADDR =
  struct.pack("<H", socket.AF_INET) + bytes(2)` with the comment "# A 4-byte AF_INET sockaddr: the host kernel's
  connect()/bind()/sendto() reject it with EINVAL inside src/'s own try, so a refusal takes the product's handled
  failure path (backoff included) and nothing leaves the host"; module counters `public_destinations_refused = 0`
  (saturating via `saturating_add`) and `last_refused: "tuple[str, int] | None" = None`, both "twin-only test knob" in
  `TEST_API = ("public_destinations_refused", "last_refused")`. `_refused(addr) -> bool` — a `(str, int)` tuple whose host
  matches neither list; on refusal it counts and records. `_patched_connect(self)`: when `self._addr` is a refused tuple
  (or already `_REFUSED_SOCKADDR`), count, record (first time) and set `self._addr = _REFUSED_SOCKADDR`; else resolve as
  today; then `await _real_connect(self)`. `_patched_sendto(self, msg, addr, timeout_ms=-1)`: a refused `addr` counts and
  sends to `_REFUSED_SOCKADDR` (the product's `sendto()` returns `None`); else resolves as today. `_patched_recvfrom`
  unchanged. `patch_asy_udp_socket_for_unix_port()` keeps its name (C1 does not rename it: it patches the module
  `asy_udp_socket`, whose name is kept) and its three `# type: ignore[method-assign]` (twin scope, allowed — CLAUDE.md
  forbids them in `src/` only); its comment "# Called by every twin entry point after prewarm_poll_set() and before any
  build_system()/main(); tests_scripts/test_twin_entry_point_order.py checks it."
- **Resolved**: A.U25.33 (3) says "refuse … with `OSError(errno.ENETUNREACH)`"; the shim's wrappers sit outside
  `UDPSocket._connect()`'s `try` and `ready()` calls `_connect()` unguarded (M.SRC_NET.028), so a raise there would
  escape `sendto()`/`write()`/`recvfrom()`, breaking G6/R34 ("`UDPSocket` I/O … never raise") and G7/R01 (the twin
  reaches the product only through its normal interfaces); the refusal therefore enters through the product's own socket
  call, with the host kernel's `EINVAL` instead of `ENETUNREACH` (the product handles every `OSError` alike) — agent
  decision, OR2.c list, verified against `ports/unix/modsocket.c:198-236, 364-378` (v1.29.0: the sockaddr goes to the
  kernel as given). Location `digital_twin/unixport/` (A.U18.12 "e.g. `unixport/`" names no parent): inside
  `digital_twin/` keeps the eight lint/type scopes of CLAUDE.md unchanged and the main pass already computes the file's
  module name from its own directory (no `__init__.py`), the same name `mypy_path` gives it — agent decision, OR2.c list.
- **Unit**: U25 (stage U18: A.U18.12 moves the file and rewrites `:33-35`; U10 for the C1 class rename)
- **Depends**: M.TWIN.001 (`saturating_add`); M.SRC_NET.026 (tuple-only constructor)
- **Blast carried by**: `run_generic_integration.py` inserts `digital_twin/unixport` into `sys.path` and calls the patch after the
  prewarm → M.TWIN.049 (A.U18.12's other runner, `segfault_stress_repro.py`, is deleted by A.U25.40) (`launch.py` boots no product module and opens no UDP socket: it imports neither); every twin test
  and scenario library imports it from the new place (C4) → M.TWIN.100-164, TEST_HELP (`tests/_webserver_concurrency_
  scenarios.py`, `tests/_digital_twin_construction_scenarios.py`); L1 users (`tests/test_asy_udp_socket.py`,
  `test_captive_dns.py`, `test_asy_wifi_service.py`, `test_asy_ntp_client.py`, `test_asy_dns_client.py`,
  `test_ntp_fram_system_integration.py`, `test_ntp_wifi_dns_integration.py`) → A.U18.12 (TEST_UNIT); `pyproject.toml`
  `mypy_path` += `digital_twin/unixport` → TOOL gap (A.U18.12 names `pyproject.toml:365`, TOOL's file);
  `digital_twin/typecheck.ini` `mypy_path` → M.TWIN.075; `scripts/micropypath.toml` twin layout → SCR gap; L0 order check
  `tests_scripts/test_twin_entry_point_order.py` → A.U25.34/A.U25.43 (TSC); L2 offline-boot case (counter 0, no
  refused 8.8.8.8 send) → M.TWIN.144; CI suite asserts `public_destinations_refused=0` per run log → A.U25.35 (SCR);
  README shim section → M.TWIN.071; SPEC F.7 row → A.U14.28 (SPEC)
- **Kind**: code

## digital_twin/_wall_clock.py (new)

### M.TWIN.019 Twin wall clock the RTC steps, installed from outside src/
- **From**: A.U25.71 (`WallClock`, `install()`, `step()`), A.U10.28 / A.U18.26 (their L2 clock-jump halves use it),
  A.U25.20 (the uninstalled RTC behaviour it falls back to)
- **Site**: new `digital_twin/_wall_clock.py`
- **Change**: header (≤ 3 lines) "The twin's wall clock: the built-in time module plus an offset that RTC().datetime(set)
  and the twin-only step() move, as an RTC set moves time.time()/gmtime() on rp2 (ports/rp2/modtime.c:31-43,
  machine_rtc.c:65-95, v1.29.0). Ticks never step." Contents: `import time as _time`; `class WallClock` with `offset_s =
  0`; `time()` → `_time.time() + self.offset_s`; `gmtime(t=None)` / `localtime(t=None)` → the built-in on `t` when given,
  else on `self.time()`; every other attribute (`mktime`, `ticks_ms/us/diff/add`, `sleep`, `sleep_ms`, `sleep_us`,
  `time_ns` when present) delegates through `__getattr__` to the built-in (MicroPython supports module-style
  `__getattr__` on a class instance); `set_wall(epoch_s)` sets `offset_s = epoch_s - _time.time()`; `step(seconds)` —
  "twin-only test knob" — adds to `offset_s`; `TEST_API = ("step",)`. Module state: `_clock: WallClock | None = None`;
  `install(modules) -> WallClock` creates the one clock on first call and rebinds the `time` global of each given module
  object whose `time` is the built-in module (a module already rebound is skipped; idempotent), comment "# From outside,
  as the tests adapt every product seam: no src/ change (OR36)"; `installed() -> WallClock | None`. Every value is an
  `int` epoch second (the rp2 port's `time.time()` is integral).
- **Resolved**: —
- **Unit**: U25
- **Depends**: M.TWIN.033 (RTC reads `installed()`)
- **Blast carried by**: `machine.RTC` → M.TWIN.033; the runner installs it for every loaded `src/` module after the
  device import (walk `sys.modules`) → M.TWIN.050; the L2 clock-jump halves A.U10.28 and A.U18.26 leave "pending U25"
  (A.U25.71 names their use of `step()` but no action writes them — a gap closed here) → new
  `tests/test_digital_twin_clock_jump.py`, M.TWIN.146; new L2 cases in
  `tests/test_digital_twin_machine.py` (an installed clock: `RTC().datetime(set)` moves `time.time()` of a rebound
  module to the set second ± 1, ticks unchanged; `step(3600)` moves `gmtime()` by an hour; an uninstalled `RTC()` keeps
  the stored tuple) → M.TWIN.128; fidelity table RTC row "fixed (installed by the runner)", `ticks_ms()` row stays →
  M.TWIN.059; README "What's here" bullet → M.TWIN.058; ruff/mypy pick it up by directory
- **Kind**: code

## digital_twin/machine.py

Shared for M.TWIN.020-036: every class gains a `TEST_API` tuple naming each public name the real rp2 type lacks
(A.U24.18's twin half — its L0 check `tests_scripts/test_fake_surface_conformance.py` adds this file to its scope, TSC),
listed per class below; every counter steps through `saturating_add`/the check-before-step form (A.U25.23; A.U10.05's L0
AST scan `tests_scripts/test_counter_steps.py` adds `digital_twin/*.py`, TSC); every tick use stays a `ticks_diff()`
delta (A.U14.33's L0 scan reads this file, TSC — the `:503-522`, `:862-871` sites pass at HEAD); the modelled rp2
facts are re-read at the refreshed pin (A.SDEP.08 `:48, :250, :368, :836`; A.SDEP.17 W26 `deinit()`; A.SDEP.16 W12 the
`:757` comment) and any change is a delta, not done here.

### M.TWIN.020 Module header, imports and types: no profile sugar, no explicit Any
- **From**: A.U25.25 (docstring drops `configure_i2c_wiring()`), A.U25.42 ((a) the four chip modules and `_twin_common`
  imported at module top; no function-level import remains), A.U25.63 (local `TypedDict` family mirroring A.U20.28's
  `TwinWiringPlan`; `_I2CDevice` a union of per-method Protocols; `_current_*_chip` typed; the "stays Any" comments go),
  A.U25.62 (`FramChip` type import → `FRAMChip`), A.U25.22 (`:13-14` `_LOG_MAXLEN` moves to `_twin_common`), A.U25.44
  (MicroPython-only imports stay out of module scope where the twin must import under CPython-hosted tooling — see
  Resolved), A.U27.28 (header over the cap), A.U0.07 (its `_PENDING` entries `:214, :220, :224, :228, :331` empty)
- **Site**: `digital_twin/machine.py:1-43`
- **Change**: header → "Twin fake of the rp2 machine module: real-time Timer and WDT, static per-id I2C/SPI/UART
  objects wired to chip fakes by configure_wiring(plan) (buildgen's per-device plan), rp2's Pin, mem_backup() and
  reset rules. Independent of tests/machine.py; digital_twin/README.md has the fidelity table." (3 lines). Imports:
  `asyncio`, `errno`, `io`, `json` only if still used (A.U25.25 removes its one user, `configure_i2c_wiring()`: `json`
  goes), `select`, `time`, `from array import array` (M.TWIN.032), `from collections import deque`; `from _twin_common
  import COUNTER_CAP, LOG_MAXLEN, BoundedLog, fill_buffer, saturating_add`; `from _bmp3xx_chip import BMP3XXChip`, `from
  _fram_chip import FRAMChip`, `from _isl29125_chip import ISL29125Chip`, `from _scd30_chip import SCD30Chip`, `from
  _sgp40_chip import SGP40Chip`, `import _wall_clock` (no cycle: no chip module imports `machine`, M.TWIN.010-014).
  `_SPI_DMA_MIN_SIZE = 32` keeps its line, citation made exact: "# ports/rp2/machine_spi.c dma_min_size_threshold
  (v1.29.0); only a read this long can raise (SPI._maybe_overrun)". `TYPE_CHECKING` block: `Callable`, `Protocol`,
  `TypedDict`; `_RandomSource` unchanged; per-method Protocols `_WritesTo` (`handle_writeto`), `_ReadsInto`
  (`handle_readfrom_into`), `_ReadsMem` (`handle_readfrom_mem`), `_WritesMem` (`handle_writeto_mem`), `_GeneralCall`
  (`handle_general_call`), `_PowerCycles` (`power_cycle`); `_I2CChip = SCD30Chip | SGP40Chip | BMP3XXChip |
  ISL29125Chip` (what `_build_i2c_chip()` returns and `I2C.devices` holds); the wiring-plan `TypedDict`s `_I2CAttachment`
  (`driver`, `address`, `irq_pin` not required), `_SPIAttachment` (`driver`, `max_size`), `_UARTPlan` (`initiator_bus`,
  `responder_bus`), `_BusPins`, `_WiringPlan` (`buses`, `spi`, `uart` not required, `pins`) — the key names exactly
  A.U20.28's `TwinWiringPlan` (comment "# Mirrors buildgen/twin_wiring.py's TwinWiringPlan: the twin cannot import
  buildgen; tests_scripts/test_twin_wiring_contract.py checks every key this module reads"). No `Any` remains.
- **Resolved**: A.U25.44 requires `machine.py`'s module-level imports (outside `TYPE_CHECKING`) to be a subset of
  CPython's stdlib plus the twin's own modules, so CPython tooling can import it (its new case in
  `tests_scripts/test_twin_never_needs_tests_on_its_path.py`, TSC); A.U25.42 adds module-top imports — every one above is
  stdlib (`array`, `asyncio`, `collections`, `errno`, `io`, `select`, `time`) or a twin module whose own module-level
  imports are stdlib or twin (`_crc8`, `json`, `random`, `struct`, `collections`), and nothing MicroPython-only
  (`ticks_*`, `asyncio.sleep_ms`, the overflow-checking `deque` flag) runs at import — both hold. A.U25.42's
  module-top chip imports need the chip modules to stop importing `machine` (M.TWIN.012/013's `timer_factory`) — same
  unit, one commit.
- **Unit**: U25
- **Depends**: M.TWIN.001, M.TWIN.010-014, M.TWIN.019; A.U20.28 (plan shape), A.U10.46 (none used here)
- **Blast carried by**: `pyproject.toml:241-243` ANN401 entry and comment for this file → A.U25.63 (TOOL); A.U8.24's
  twin `disallow_any_explicit` baseline loses this file → M.TWIN.075; the plan-key contract test → A.U20.28 (TSC); SPEC
  F.1 named-exception list loses (a) → A.U25.42 (SPEC)
- **Kind**: code

### M.TWIN.021 `Pin`: rp2 ids and names, init rule, open-drain/ALT, external level and value log
- **From**: A.U25.02 (ids 0-29, names via `pins.csv`, `ValueError("invalid pin")`, rp2's init helper, `pull=None`
  unconditional, value before OUT), A.U25.05 (`OPEN_DRAIN = 2`, `ALT = 3`, `ALT_I2C = 3`, wired-AND line level,
  `set_external_level(id, level)`, `value_log(id)`, `alt` validation), A.U24.16 (the names, defaults `mode=None`,
  `alt=<SIO>`, callable external level, external pins' refusals — the twin meets A.U24.17's contract), A.U24.17
  (`check_pin_constants`, `check_pin_pull_semantics`, `check_pin_defaults`, `check_irq_edge_values` run on this class),
  A.U13.03 / A.U16.16 (`init(value=)` applied before the mode), A.U14.17 (a) (`OPEN_DRAIN`; SDA reads high → the boot
  clear is a no-op in every twin boot), A.U13.R01 Blast (`ALT`, `ALT_I2C`, `alt=`), A.U25.68 (constants cited and
  pinned; `set_external_level` "twin-only test knob"), A.U24.18 (`TEST_API`), A.SDEP.08 (`:48` re-check)
- **Site**: `digital_twin/machine.py:45-137` (`class Pin`)
- **Change**: constants, each with its source on the line: `IN = 0`, `OUT = 1`, `OPEN_DRAIN = 2`, `ALT = 3`
  (`ports/rp2/machine_pin.h:34-37`), `PULL_UP = 1`, `PULL_DOWN = 2` (`machine_pin.c` GPIO_PULL_*, kept), `ALT_I2C = 3`
  (`GPIO_FUNC_I2C`, `machine_pin.c:513`, value from pico-sdk's `gpio_function` enum at the pinned submodule),
  `IRQ_FALLING = 0x04`, `IRQ_RISING = 0x08` (`machine_pin.c:507-508`, values from pico-sdk's GPIO IRQ enum), and a
  private `_ALT_SIO` (the SIO function number from the same enum) as the `alt` default. Class header comment (≤ 3
  lines): "Configuration follows rp2's init helper: a Pin re-configured without pull loses its pull, value is applied
  before an output mode, and every Pin(n) is one static object (ports/rp2/machine_pin.c v1.29.0)." `__new__(cls, id,
  *a, **k)`: an `int` in 0-29 or a name — Pico W board names `"GP0"`-`"GP22"`, `"GP26"`-`"GP28"`, `"WL_GPIO0"`-
  `"WL_GPIO2"`, `"LED"` and CPU names `"GPIO0"`-`"GPIO29"`, `"EXT_GPIO0"`-`"EXT_GPIO2"` (one module table `_PIN_NAMES`
  from `ports/rp2/boards/RPI_PICO_W/pins.csv` and `boards/make-pins.py:95-108`, `LED` = `EXT_GPIO0`) resolving to the same
  object as its id; an unknown name raises `ValueError(f'unknown named pin "{id}"')`, any other id
  `ValueError("invalid pin")`. `__init__(self, id, mode=None, pull=None, *, value=None, alt=_ALT_SIO)`: with no argument
  beyond `id` nothing changes (`machine_pin.c:318-323`); otherwise `self.init(...)`. `init(mode=None, pull=None, *,
  value=None, alt=_ALT_SIO)`: an external pin (`WL_GPIO*`/`LED`) refuses a non-None pull or a non-SIO alt with rp2's
  messages (`:256-262`); `value` is applied before an `OUT`/`OPEN_DRAIN` mode; `mode` set when not `None`; `ALT` records
  `alt`, and an `alt` outside the pin's `rp2040_af.csv` row raises `ValueError(f"invalid pin af: {alt}")`; `pull` set
  unconditionally (`None` → no pull). Line model: per-pin `_driven` (OUT level, or 0 when an `OPEN_DRAIN` pin is driven
  low, `None` when released/input/ALT) and the class table `_external: dict[int, int | Callable]` (default 1: an
  undriven line reads high, the I2C pull-ups); `value()` returns the driven level on `OUT`, else the wired-AND of the
  driven level and the external level (a callable is called with `(pin_id, value_log)` on every read); `value(x)`,
  `on()`, `off()`, `toggle()` set the driven level and append it to the pin's value log (a `BoundedLog`).
  `simulate_edge(new_value)` keeps its behaviour, now through the external level (it sets `_external[id]` and fires the
  handler on a level change matching the trigger) and its comment ≤ 3 lines with "twin-only test knob".
  Class methods `set_external_level(id, level)` and `value_log(id) -> BoundedLog`, both "twin-only test knob";
  `reset_registry()` keeps its comment (test-only) and also clears `_external`. `TEST_API = ("id", "mode", "pull",
  "alt", "simulate_edge", "set_external_level", "value_log", "reset_registry")`.
- **Resolved**: A.U25.02/A.U25.05/A.U24.16 are one edit (A.U25.02's own Depends): A.U24.16's defaults and names are the
  shared contract's, so the twin takes them verbatim; A.U25.02's `mode=-1`-sentinel `init(mode=-1, …)` becomes
  `mode=None` per A.U24.16 / `check_pin_defaults` (rp2's `mode=None`, `machine_pin.c:243-248`) — settled by A.U24.17
  (the contract), which both cite.
- **Unit**: U25
- **Depends**: M.TWIN.001; A.U24.16, A.U24.17 (contract, U24)
- **Blast carried by**: `_build_i2c_chip()`'s `Pin(id, mode=Pin.IN)` → M.TWIN.023 (same final state after the driver's
  own `Pin(id, Pin.IN, Pin.PULL_UP)`); `launch.py`'s `Pin(13)` holds; I2C initialising construction sets the bus pins
  to `ALT`/`ALT_I2C`/`PULL_UP` → M.TWIN.024; tests (A.U25.02's and A.U25.05's L2 lists, the contract runner, any `.pull`
  assertion after a re-bind flips) → M.TWIN.126; A.U13.R02's clear/recover L2 cases → M.TWIN.102; fidelity rows "Pin
  modes", "Pin ids/names" → M.TWIN.059; constants pinned → M.TWIN.138
- **Kind**: code

### M.TWIN.022 Configure hooks: refused after construction, one explicit plan, flushes state their reason
- **From**: A.U25.24 (`_require_unconstructed()`; comments; `:310-311` loses "Step 5"), A.U25.25 (1)
  (`configure_i2c_wiring()` goes; `_current_wiring_plan()` raises when unset; no wozi default), A.U25.28 (`:302-304`
  text), A.U0.38 (V59, same `:302-304`), A.U36.544 (`:310-311` states the reason in place), A.U25.08
  (`configure_mem_backup_state_path`/`flush_mem_backup` join the hooks — M.TWIN.032), A.U25.63 (typed plan), A.U36.518
  (SPEC L.4 sentence — SPEC), A.U25.67 Blast (no change here)
- **Site**: `digital_twin/machine.py:140-205, 297-315`
- **Change**: new `def _require_unconstructed(hook: str) -> None` raising `RuntimeError(f"machine.{hook}() after a bus
  was constructed has no effect - call it before build_system(), or machine.reset_peripherals() first")` when any of
  `_I2C_OBJECTS`, `_SPI_OBJECTS`, `_UART_OBJECTS` is non-empty; `configure_random_source`, `configure_scd30_state_path`,
  `configure_wiring`, `configure_fram_state_path`, `configure_mem_backup_state_path` call it first. Their comments
  become one line each, the rule stated once above `_require_unconstructed`: "# Every configure_*() hook runs before the
  buses it affects exist; a later call raises instead of silently doing nothing." `configure_wiring(plan:
  "_WiringPlan")` keeps its key check and comment's first sentence. `configure_i2c_wiring()` is deleted;
  `_current_wiring_plan()` returns the plan or raises `RuntimeError("no wiring plan configured - call
  machine.configure_wiring(plan) before constructing a bus")` (its comment goes; no `type: ignore`). `:302-304` →
  "# Called before build_system() constructs spi0; src/ never calls it (owner, 2026-08-13: src/ is never edited only to
  make the twin run)." `flush_fram()`/`flush_scd30()` comments → "# Called once at shutdown by each twin entry point,
  never from src/: an explicit save, so a run costs the host one state-file write (README "FRAM persistence")."
  `_current_scd30_chip: "SCD30Chip | None"`, `_current_fram_chip: "FRAMChip | None"`.
- **Resolved**: A.U0.38 (U0) writes V59's text at `:302-304`; A.U25.28 (U25) replaces it, its Depends saying "this
  action's text wins, one edit, A-C merges" — staged: U0 then U25, end state A.U25.28's.
- **Unit**: U25 (stage U0: A.U0.38's V59 text)
- **Depends**: M.TWIN.035 (registries)
- **Blast carried by**: every test re-configuring between builds calls `machine.reset_peripherals()` first (C4) →
  M.TWIN.100-164 and TEST_HELP (`tests/_digital_twin_construction_scenarios.py`, `tests/_webserver_concurrency_
  scenarios.py`); the post-construction resets (`tests/test_digital_twin_sensortask_integration.py:702, :778`,
  `test_digital_twin_bus_hazard_concurrency.py:531`, `test_digital_twin_machine.py:134, :231`) → M.TWIN.144, M.TWIN.102,
  M.TWIN.126; `configure_i2c_wiring` callers (`test_digital_twin_generic_wiring.py`, `test_digital_twin_machine.py:161-194`,
  `test_digital_twin_isl29125_autorange.py:58`, `test_digital_twin_bus_hazard_concurrency.py` (12 sites)) →
  M.TWIN.114, M.TWIN.126, M.TWIN.122, M.TWIN.102; `tests_scripts/test_buildgen_twin_wiring.py:44-62` → A.U25.25 (TSC);
  `tests_hardware/isl29125_conformance.py:34` → A.U26.45 (HW_DEV); README "What's here", "Booting", "Adding a new chip
  fake" step 2 → M.TWIN.058, M.TWIN.061, M.TWIN.072; SPEC L.4 → A.U36.518 (SPEC)
- **Kind**: code

### M.TWIN.023 `_build_i2c_chip()`: module-top classes, simulation Timer factory, typed result
- **From**: A.U25.42 (a) (no function-level imports; `timer_factory=lambda: Timer(_pool=False)`), A.U25.19 (the
  chip-side Timer skips the alarm pool), A.U25.62 (class names), A.U25.63 (returns `_I2CChip`; the Any comment goes),
  A.U5.15 (chip construction blast), A.U25.67 (its fake-catalog test reads this function's compared string literals —
  keep them literal), A.U0.07 (`:214-228` entries)
- **Site**: `digital_twin/machine.py:207-231`
- **Change**: `def _build_i2c_chip(attachment: "_I2CAttachment") -> "_I2CChip"`; comment (≤ 3 lines) "Dispatches on the
  plan's driver string - the twin's chip-fake catalog (tests_scripts/test_twin_fake_catalog.py pins it against
  devices/*.toml); the chip Timers are simulation clocks, not rp2 alarms." Branches: `"scd30"` → `SCD30Chip(random_source=
  _random_source, rdy_pin=Pin(attachment["irq_pin"], mode=Pin.IN), timer_factory=_simulation_timer,
  state_path=_scd30_state_path)` (sets `_current_scd30_chip`); `"sgp40"` → `SGP40Chip(random_source=_random_source)`;
  `"bmp3xx"` → `BMP3XXChip(random_source=_random_source)`; `"isl29125"` → `ISL29125Chip(random_source=_random_source,
  int_pin=Pin(attachment["irq_pin"], mode=Pin.IN), timer_factory=_simulation_timer)`; the unknown-driver `ValueError`
  unchanged. New module function `_simulation_timer() -> "Timer"` returning `Timer(_pool=False)` (a named function, not
  a lambda, so the chip fakes' annotation `Callable[[], Timer]` reads it).
- **Resolved**: —
- **Unit**: U25
- **Depends**: M.TWIN.012, M.TWIN.013, M.TWIN.030
- **Blast carried by**: A.U25.67's L0 catalog test (TSC); tests constructing chips directly → M.TWIN.100, .120, .142,
  .150
- **Kind**: code

### M.TWIN.024 `I2C`: one static object per id, rp2 pin rules, general call, ENODEV probe, fill, replug knobs
- **From**: A.U25.03 (1) (`_I2C_OBJECTS`, id 0-1, chips/faults/log survive, pin validation, initialising construction
  sets the bus pins), A.U13.R01 / A.U24.20 Blasts (per-id state across constructions — this change), A.U25.10
  (general call delivered to chips with `handle_general_call`, else `EIO`), A.U25.17 (zero-length NAK → `ENODEV`; a
  `writeto` fault consumed by a zero-length transfer surfaces as `ENODEV` unless `ETIMEDOUT`; `scan()` never raises),
  A.U25.06 (no shrinking `buf[:] = …` at `:277, :289`), A.U25.22 (`log` a `BoundedLog`), A.U25.59 (`unplug(address)` /
  `plug(address)`), A.U25.63 (typed), A.U24.17 (`check_scan_never_raises`, `check_readfrom_mem_into_delegates`,
  `check_i2c_state_survives_reconstruction` run on it), A.U24.18 (`TEST_API`), A.U30.21 Blast (writes into any writable
  buffer — `fill_buffer` keeps it), A.U12.18 Blast (the log shows each session's write then read — entry shapes kept),
  A.U14.14 Blast (the ENODEV fact — this change), A.SDEP.08 / A.SDEP.17 W26 (`:250` `deinit()` re-check)
- **Site**: `digital_twin/machine.py:234-294` (`_wire_i2c_devices()`, `class I2C`)
- **Change**: `I2C.__new__(cls, id, *a, **k)` returns `_I2C_OBJECTS[id]` when registered; an `id` outside 0-1 raises
  `ValueError(f"I2C({id}) doesn't exist")` (`machine_i2c.c:80-82`); a new object gets `devices` from
  `_wire_i2c_devices(id)`, an empty `_unplugged: dict[int, _I2CChip]`, `log = BoundedLog(LOG_MAXLEN)`, `freq = 0` and is
  registered. `__init__(self, id, freq=400000, *, scl, sda, timeout=50000)`: `scl`/`sda` (a `Pin` or an int, resolved
  to `Pin(n)`) are validated by rp2's rule — SCL `n & 1 == 1`, SDA `n & 1 == 0`, both `(n & 2) >> 1 == id`
  (`machine_i2c.h:65-66`) — raising `ValueError("bad SCL pin")`/`("bad SDA pin")` (`machine_i2c.c:89-103`); then the
  initialisation (`:105-115`): `freq`, `timeout` stored, `("init", freq, timeout)` logged, both pins set to
  `init(Pin.ALT, Pin.PULL_UP, alt=Pin.ALT_I2C)`; `devices`, `_unplugged`, chip fault queues and the log are kept. Class
  comment (≤ 3 lines): "# One static object per bus id, as ports/rp2/machine_i2c.c:80-87 (v1.29.0): a re-construction
  re-initialises the controller and keeps the wired chips, their queued faults and the log." `deinit()` keeps its
  3-line comment and flag. `scan()` returns `sorted(self.devices)` (unplugged chips are absent; never raises).
  `_device_or_nak(address, nbytes)` raises `OSError(errno.ENODEV)` when `nbytes == 0`, else `OSError(errno.EIO, "no ACK
  from device")`. `writeto(address, buf, stop=True)`: `data = bytes(buf)`; address 0 → `self.log.append(("writeto", 0,
  data, stop))`, then every chip in `devices` that has `handle_general_call` gets `handle_general_call(data)`; when none
  has it, `OSError(errno.EIO, "no ACK from device")` (comment "# The general call reaches only chips whose datasheet
  documents it (the SGP40, Table 17); no listener means no ACK"); otherwise `device.handle_writeto(data)` inside
  `try … except OSError as e:` that, for `len(data) == 0` and `e.errno != errno.ETIMEDOUT`, re-raises
  `OSError(errno.ENODEV)` (comment "# A zero-length probe goes through soft I2C: a NAK surfaces as ENODEV
  (extmod/machine_i2c.c:199-203, v1.29.0)"). `readfrom_into`: `fill_buffer(buf, device.handle_readfrom_into(len(buf)))`.
  `readfrom_mem_into`: `fill_buffer(buf, self.readfrom_mem(...))` (its delegation comment kept). New `unplug(address)`
  moves the chip from `devices` to `_unplugged` and `plug(address)` calls the chip's `power_cycle()` and moves it back,
  both "twin-only test knob: a sensor pulled and re-seated on a running unit". `TEST_API = ("id", "scl", "sda", "freq",
  "timeout", "deinit_called", "devices", "log", "unplug", "plug")`. `_wire_i2c_devices(bus_id)` reads
  `_current_wiring_plan()["buses"].get(f"i2c{bus_id}", [])` (unchanged).
- **Resolved**: A.U25.03 says the init runs "only when the construction passes more than the id"; the pinned source
  initialises also on the first construction (`if (n_args > 1 || n_kw > 0 || self->freq == 0)`,
  `ports/rp2/machine_i2c.c:105`, read in `mp/` v1.29.0), and the twin keeps `scl`/`sda` required (every product
  construction passes them), so every twin construction initialises — the end state follows the source (C0 check).
- **Unit**: U25
- **Depends**: M.TWIN.001, M.TWIN.021, M.TWIN.023, M.TWIN.035
- **Blast carried by**: A.U13.R01's `recover()` re-construction keeps the chips (product, SRC_SENS — no change);
  `run_generic_integration._collect_chips()` reads `machine.peripheral(name).devices` → M.TWIN.049; tests (A.U25.03's,
  .06's, .10's, .17's L2 lists; general call raises `EIO` with no SGP40; re-construction keeps a queued fault) →
  M.TWIN.126; hot-replug → M.TWIN.116; bus-hazard general-call scenario → M.TWIN.102; CI Run 5/5c consume faults at the
  probe (A.U25.36, SCR); fidelity rows (static per-id objects; general call; ENODEV/ETIMEDOUT only on a probe) →
  M.TWIN.059
- **Kind**: code

### M.TWIN.025 One FRAM ID table, both chips listed, unknown size refused
- **From**: A.U25.29 (table lists both chips with datasheet p.10 citations; `_DEV_FRAM_*` go; unknown size raises;
  `FRAMChip` RDID required), A.U20.28 (the table stays here, pinned to `asy_fram_driver._KNOWN_PRODUCT_IDS`), A.U25.62
  (`FramChip` → `FRAMChip`), A.U25.42 (no function-level import), A.U28.35 (the `:318` `datasheets/fram/` citation stays
  valid after the submodule move — holds), A.U36.039 / A.U36.543 (SPEC C.11/D facts naming `_wire_spi_device()` — the
  name is kept), A.U0.07 (`:331` entry)
- **Site**: `digital_twin/machine.py:317-336`
- **Change**: `_FRAM_RDID_BY_MAX_SIZE: "dict[int, bytes]" = {0x2000: bytes([0x04, 0x7F, 0x03, 0x02]), 0x40000:
  bytes([0x04, 0x7F, 0x48, 0x03])}` — one entry per line with its comment "# MB85RS64V, datasheets/fram/MB85RS64V-DS501-
  00015-4v0-E.pdf p.10" / "# MB85RS2MTA, datasheets/fram/MB85RS2MTA-DS501-00032-3v0-E.pdf p.10"; the block comment →
  "# Keyed by size, the only chip fact a device TOML carries; pinned to asy_fram_driver._KNOWN_PRODUCT_IDS by
  tests/test_digital_twin_fram.py." `_DEV_FRAM_SIZE`/`_DEV_FRAM_RDID` go. `_wire_spi_device(bus_id) -> "FRAMChip |
  None"`: an unknown `max_size` raises `ValueError(f"no FRAM RDID for size {max_size:#x} - add it to
  machine._FRAM_RDID_BY_MAX_SIZE")`; `FRAMChip(size=max_size, rdid_response=…, state_path=_fram_state_path)`.
- **Resolved**: —
- **Unit**: U25
- **Depends**: M.TWIN.011
- **Blast carried by**: `tests/test_digital_twin_generic_wiring.py:98-116` (one case per table size) → M.TWIN.114;
  `tests/test_digital_twin_fram.py` table-vs-driver pin and RDID cases → M.TWIN.110; README `_fram_chip.py` bullet →
  M.TWIN.058
- **Kind**: code

### M.TWIN.026 `SPI`: static per-id object, rp2 bit order, power-loss and wire-time knobs, bounded log
- **From**: A.U25.03 (1) (`_SPI_OBJECTS`, ids 0-1, re-init with rp2 defaults for omitted arguments, SCK/MOSI/MISO
  validation), A.U25.16 (`MSB = 1`, `LSB = 0`, `firstbit=MSB` default, constructor refuses LSB), A.U24.23 Blast (same),
  A.U25.54 (`lose_power_after(k)`, `SimulatedPowerLoss(BaseException)`), A.S0930.27 (4) (`wire_time_us_per_byte`, default
  0, a blocking `time.sleep_us(len(buf) * n)` per transfer), A.U25.22 (`log` a `BoundedLog`), A.U25.06 (no shrinking
  fill when nothing is wired), A.U14.21 Blast (the fake models the raise only — holds), A.U25.68 (`_SPI_DMA_MIN_SIZE`
  cited and pinned), A.U24.18 (`TEST_API`), A.SDEP.08 (`:368` re-check), A.U36.039 (one device per SPI id, no chip
  select routing — holds, stated in the fidelity table)
- **Site**: `digital_twin/machine.py:339-431` (`class SPI`)
- **Change**: `MSB = 1`, `LSB = 0` with "# pico-sdk SPI_MSB_FIRST/SPI_LSB_FIRST at the pinned submodule
  (hardware/spi.h:184-187)". `__new__(cls, id, *a, **k)` returns `_SPI_OBJECTS[id]` when registered; an `id` outside 0-1
  raises `ValueError(f"SPI({id}) doesn't exist")`; a new object gets `device = _wire_spi_device(id)`, `log =
  BoundedLog(LOG_MAXLEN)`, `baudrate = 0`, the overrun knobs, `_power_left: int | None = None`, `wire_time_us_per_byte
  = 0`. `__init__(self, id, baudrate=1000000, *, polarity=0, phase=0, bits=8, firstbit=MSB, sck, mosi, miso)`: pins
  (`Pin` or int) validated by `machine_spi.c:89-95`'s rules, raising `ValueError("bad SCK pin")`/`("bad MOSI pin")`/
  `("bad MISO pin")` (`:169-193`); the initialisation (`:195-214`) applies every setting from this construction's
  arguments (rp2's defaults for omitted ones), raises `NotImplementedError("LSB")` for `firstbit == LSB`, logs
  `("init", baudrate, polarity, phase, bits, firstbit)`. Class comment (≤ 3 lines): "# One static object per bus id, as
  ports/rp2/machine_spi.c:161-167 (v1.29.0): a re-construction re-applies every setting, omitted ones at rp2's
  defaults, and keeps the wired chip." `init()` keeps its `-1` sentinels; its check reads `firstbit == self.LSB`.
  `write()` and `readinto()` first call `self._transaction(len(buf))`: when `_power_left` is set it counts down and at 0
  raises `SimulatedPowerLoss("power lost after the armed SPI transaction count")`; then, when `wire_time_us_per_byte`,
  `time.sleep_us(nbytes * wire_time_us_per_byte)` (comment "# twin-only test knob: blocking wire time, so a long FRAM
  pass takes its real clock (8 us/byte at 1 MHz)"). `readinto()` with no wired device → `fill_buffer(buf, b"")`.
  `lose_power_after(k: int)` sets `_power_left = k` ("twin-only test knob: the k+1-th transaction loses power"). The
  overrun model `:368-372`, `:416-425` unchanged (its comment ≤ 3 lines). `TEST_API = ("id", "sck", "mosi", "miso",
  "baudrate", "polarity", "phase", "bits", "firstbit", "deinit_called", "device", "log", "rx_overrun",
  "rx_overrun_remaining", "lose_power_after", "wire_time_us_per_byte")`. New module class `SimulatedPowerLoss(BaseException)`
  beside the reset exceptions (M.TWIN.034).
- **Resolved**: A.U25.03's SPI half says the init runs "with more than the id"; the source also initialises on the
  first construction (`self->baudrate == 0`, `machine_spi.c:195`) and every twin construction names its pins, so every
  construction initialises (C0 check, as M.TWIN.024).
- **Unit**: U25 (A.S0930.27's knob co-lands per its Depends)
- **Depends**: M.TWIN.001, M.TWIN.021, M.TWIN.025, M.TWIN.034, M.TWIN.035
- **Blast carried by**: SPI log init tuples carry `firstbit` 1 (`tests/test_digital_twin_fram.py`/`_machine.py` greps of
  `"init"`) → M.TWIN.110, M.TWIN.126; LSB refusal, default MSB, re-init resets baudrate, bad SCK pin → M.TWIN.126;
  crash-point enumeration → M.TWIN.112; erase timing with the knob and power loss over the erase → M.TWIN.104,
  M.TWIN.112 (A.S0930.27 (4)-(5)); `--test-shutdown-hang` S5 erase path → M.TWIN.051; fidelity rows (power loss at
  transaction granularity, mid-byte is L3's; wire time off by default) → M.TWIN.059; the unit fake's swap and the FRAM
  wire-trace golden `…/8/1` → A.U24.23 (TEST_UNIT)
- **Kind**: code

### M.TWIN.027 UART link: overflow-checked in-flight queue, capped delay buffer, bounded settle, saturating counters
- **From**: A.U25.22 (`in_flight` built with `deque((), _UART_INFLIGHT_MAX, 1)` so `IndexError` really counts
  `dropped_overrun`; `pending` capped at `capacity` with `dropped_delayed`; `direction_to()` goes), A.U24.77
  (`direction_to()` unused — carried by A.U25.22), A.U25.23 (`offered`, `dropped_overrun`, `delivered` saturate),
  A.U25.30 (`settle()` refuses inside a running task; bounded wait; comment), A.U1.25 (`:482` "(dev_legacy/README.md)" →
  "(tests_hardware/README.md 'The dev bench')"), A.U1.04 / A.U1.08 Blasts (the same `:482` comment — carried by A.U1.25),
  A.U17.25 Blast (the fake already supports `UARTLink`/`LinkPoller` — holds), A.S0930.04 (both CRC modes run over this
  link — no fake change, the link is byte-transparent), A.U14.33 (`:503-522` stay `ticks_diff()` deltas)
- **Site**: `digital_twin/machine.py:435-597` (`_UART_*` constants, `_LinkDirection`, `attach_crossover_jumper()`,
  `UARTLink`)
- **Change**: `_LinkDirection.__init__`: `self.in_flight = deque((), _UART_INFLIGHT_MAX, 1)` with "# flag 1 =
  FLAG_CHECK_OVERFLOW: a full queue raises IndexError instead of silently dropping its oldest byte
  (py/objdeque.c:107-118)"; new `self.dropped_delayed = 0`. `shape()`: `self.offered = saturating_add(self.offered)`.
  `_schedule()`'s `except IndexError` steps `dropped_overrun` through `saturating_add`; `_advance()` likewise for
  `dropped_overrun` and `delivered`. `transmit()`'s delay branch keeps at most `direction.capacity - len(pending)` bytes
  and counts the rest into `dropped_delayed` (saturating). `detach()`'s two rebinds use the same three-argument
  constructor. `direction_to()` is deleted. `attach_crossover_jumper()`'s comment `:482` → "# Models the dev bench's
  permanent GP0<->GP9 / GP1<->GP8 jumper (tests_hardware/README.md 'The dev bench'): the twin's dev graph builds both
  ends but joins neither. The returned pollers are bounded (CLAUDE.md's known CI hang)." (3 lines). `settle()`: first
  `if _in_running_task(): raise RuntimeError("settle() blocks the interpreter - call it from synchronous test code,
  outside asyncio.run()")` (`_in_running_task()` a module helper: `asyncio.current_task()` succeeding, the probe
  `Timer.deinit()` uses); the deadline is the last in-flight byte's due time plus one byte time, computed once; the loop
  advances and sleeps until it, never open-ended; comment (3 lines) A.U25.30's "Test-only (no alternative: a synchronous
  assertion cannot await the wire): waits out the in-flight bytes' own wire time, never inside a running task."
  `UARTLink.TEST_API` — the class is twin-only (no rp2 counterpart): its docstring line says so and the A.U24.18 check
  does not scope it (it checks classes standing in for rp2 types).
- **Resolved**: —
- **Unit**: U25 (stage U1: A.U1.25's comment)
- **Depends**: M.TWIN.001
- **Blast carried by**: tests (4097 bytes in flight → `dropped_overrun == 1`; `settle()` inside a coroutine raises; a
  64-byte settle at 1200 baud returns after its wire time with a bounded number of `_advance()` calls; each counter at
  `COUNTER_CAP` stays) → M.TWIN.130; `tests/_uart_link_contract.py` (no `direction_to`, unchanged) — TEST_HELP holds;
  the unit fake's `direction_to()` → A.U24.77 (TEST_HELP); both-CRC-mode L2 runs over the link → M.TWIN.154, M.TWIN.158
- **Kind**: code

### M.TWIN.028 `UART`: one static object per id with rp2's init rules; EINVAL ioctl; clamped readline; txdone
- **From**: A.U25.04 (static per-id object; rp2 init rules; buffers reset to 256 unless given, clamp below 32, raise
  above 32766; `timeout_char` floor; TX/RX pin rule; first-construction default 115200; `rx_queue` emptied; link kept;
  `_supersede()`/`superseded`/`_live` go; `deinit()` keeps it registered; one comment line), A.U24.80 (`ioctl()` answers
  `-errno.EINVAL` to every request but `MP_STREAM_POLL`; public `poll_mask(mask)`; comments `:603`, `:757-758`), A.U24.15
  Blast (the same fd-mechanism wording), A.U25.22 (`feed_rx()` goes), A.U25.23 (`would_have_blocked_bytes` saturates;
  `superseded` removed with A.U25.04), A.U13.12 Blast (`readline(size=-1)`: at most `size` bytes up to `\n`, overask
  counted; `size == -1` with no `\n` counts the one extra byte; comment `:733-734` → "clamped to `any()` like every
  counted read"), A.U13.13 Blast (`txdone()` → `True`; `txbuf` kept), A.U25.68 (`_MP_STREAM_POLL`, `_MAX_BUFFER_SIZE`,
  `_UART_INVERT_MASK`, the check order and `write()` returning `None` each cited and pinned), A.U36.532 (`:702` "Part
  F.5.8" → "Part F.8.2"), A.U24.17 (shared UART link contract unchanged), A.U24.18 (`TEST_API`), A.U5.17 / A.U5.18
  (`UART.__init__`'s parameter count is in the exact PLR0913 exempt set — holds; the per-file entry is TOOL's)
- **Site**: `digital_twin/machine.py:600-752` (`class UART`)
- **Change**: class constants with sources on their lines: `_MP_STREAM_POLL = 3  # py/stream.h:39`, `_MAX_BUFFER_SIZE =
  32766  # ports/rp2/machine_uart.c:69`, new `_MIN_BUFFER_SIZE = 32` (same file's `MIN_BUFFER_SIZE`), `_DEFAULT_BUFFER_SIZE
  = 256`, `_DEFAULT_BAUDRATE = 115200` (`:39`), `_UART_INVERT_MASK = 3  # :82-84`. The `:601-603` comment → "# Held to
  tests/_uart_link_contract.py's semantics; ioctl() answers EINVAL to all but POLL as rp2 does (machine_uart.c:694-697),
  so a real select.poll() never takes the fd path (extmod/modselect.c:252-266) - tests still swap in a bounded poller."
  `__new__(cls, id, *a, **k)` returns `_UART_OBJECTS[id]` when registered (ids 0-1, `ValueError(f"UART({id}) doesn't
  exist")`), else a new registered object with `baudrate = 0`, `rx_queue = bytearray()`, `_link = None`, `writable =
  True`, `write_limit = None`, `deinit_called = False`, `timeout_char = 0`. `__init__(self, id, baudrate=0, bits=0,
  parity=-1, stop=0, *, tx=None, rx=None, txbuf=0, rxbuf=0, timeout=-1, timeout_char=-1, invert=-1)` (rp2's
  not-configured sentinels, `machine_uart.c:264-278`): `rxbuf`/`txbuf` reset to 256 first (`:470-473`), the check order
  as rp2 (`:458-466, :355-356, :370-375`): TX/RX validated by `:73-78`'s RP2040 rule (`ValueError("bad TX pin")`/
  `("bad RX pin")`), `invert & ~mask` → `ValueError("bad inversion mask")`, a given buffer below 32 clamps to 32 and above
  32766 raises `"rxbuf too large"`/`"txbuf too large"`; each other setting is applied only when given; then, when the
  construction passes any argument beyond the id or the baudrate is still 0 (`:400-404`), a zero baudrate becomes 115200 and `timeout_char`
  is floored at `13000 // baudrate + 1` (`:406-410`); `rx_queue` is emptied (rp2 re-allocates the ring); an attached
  link stays (the jumper is wiring). One comment line: "# One static object per UART id, as ports/rp2/machine_uart.c:469
  (v1.29.0); a re-construction re-initialises it." `deinit()` sets `deinit_called` only (the object stays registered).
  `ioctl(req, arg)` returns `-errno.EINVAL` unless `req == _MP_STREAM_POLL`, which returns `self.poll_mask(arg)`;
  `poll_mask(mask)` holds today's POLL body. `would_have_blocked_bytes` steps via `saturating_add`; its comment
  `:701-703` cites "SPECIFICATION.md Part F.8.2". `readline(size=-1)`: serves at most `size` bytes (all when -1) up to
  and including `\n`; counts `size - queued` when `size > queued`; with `size == -1` and no `\n` queued counts one extra
  byte (the C read's probe past the buffer); comment "# Clamped to any() like every counted read: readline() reads
  byte by byte, each missing byte a blocking wait (F.8.2)". New `txdone() -> bool` returning `True` ("# the link
  schedules each byte at once; nothing waits in a TX FIFO"). `feed_rx()` is deleted. `write()` returns `None` when a
  `write_limit` leaves nothing to write, comment citing `machine_uart.c`'s write path (`:593-622`). `TEST_API = ("id",
  "tx", "rx", "baudrate", "bits", "parity", "stop", "rxbuf", "txbuf", "timeout", "timeout_char", "invert",
  "deinit_called", "rx_queue", "writable", "write_limit", "would_have_blocked_bytes", "poll_mask", "ioctl")` (`ioctl` is
  the `io.IOBase` stream hook — rp2 implements the stream protocol in C, not as a Python method).
- **Resolved**: A.U36.532 renumbers F.5.8 → F.8.2 (U36) after A.U13.12 (U13) and A.U25.68 (U25) write comments naming
  F.5.8; the end state names F.8.2 — the later action's map, which its own text says other actions' new citations
  follow (A-C).
- **Unit**: U25 (A.U36.532's renumber lands in U36 on the U25 text)
- **Depends**: M.TWIN.001, M.TWIN.021, M.TWIN.035
- **Blast carried by**: `tests/test_digital_twin_machine_uart.py:28-43` (supersede test → same-object test), `make_link()`
  and `:49, :67` call `machine.reset_peripherals()`, the contract via `poll_mask` → M.TWIN.130;
  `tests/test_digital_twin_uart_link.py:66-78` (`reset_peripherals()` before each build) and `:69` comment → M.TWIN.158;
  `run_generic_integration._wire_uart_crossover()` reads `machine.peripheral(...)` → M.TWIN.049; fidelity row "UART
  stream ioctl answers as rp2", "static per-id UART" → M.TWIN.059; constants pinned → M.TWIN.138; CLAUDE.md hang-cause
  text and SPEC J.7 → A.U24.15 (DOCS/SPEC, AC_NOTES 29); `pyproject.toml` PLR0913 per-file entry → A.U5.17 (TOOL)
- **Kind**: code

### M.TWIN.029 `LinkPoller`: reads the POLL mask through `poll_mask()`; comment states the fd mechanism
- **From**: A.U24.80 (`ipoll()` uses `poll_mask()`; the `:757-758` comment), A.U24.15 Blast (wording), A.SDEP.16 W12
  (the `:757` comment's pointer to the prewarm segfault — re-checked at the pin; goes if `extmod/modselect.c` is fixed)
- **Site**: `digital_twin/machine.py:755-777`
- **Change**: comment → "# Bounded select.poll() stand-in, as tests/machine.py's: a real poll over the fake would ask it
  for a file descriptor (extmod/modselect.c:252-266) and, on the Unix port, can segfault on its pollfds growth
  (digital_twin/unix_port_poll_prewarm.py)." (3 lines). `ipoll()` calls `self._uart.poll_mask(select.POLLIN |
  select.POLLOUT)`. `force_not_ready()` gains "twin-only test knob". The class is twin-only (no rp2 type), outside
  A.U24.18's scope.
- **Resolved**: —
- **Unit**: U25
- **Depends**: M.TWIN.028
- **Blast carried by**: the runner's poller swap → M.TWIN.049 (unchanged mechanism); `tests/test_digital_twin_uart_link.py`
  → M.TWIN.158
- **Kind**: code

### M.TWIN.030 `Timer`: rp2 signature and period maths, one schedule per Timer, 16-alarm pool, soft exceptions survive
- **From**: A.U25.19 ((1) signature, `id != -1` → `ValueError`, `freq`/`tick_hz` maths floored at 1 µs, bare `Timer()`
  takes no alarm; (2) module pool `_ALARMS_FREE` from `_ALARM_POOL_SIZE`, every `init()` takes one, `OSError(ENOMEM)` when
  empty, freed by `deinit()`/re-`init()`/a fired ONE_SHOT, test-only `set_alarm_pool_free(n)`; (3) generation number
  ends a superseded loop; (4) soft-callback exceptions printed and the schedule continues, a raising `hard=True`
  callback ends it and frees its alarm; the finaliser not modelled), A.U25.42 / A.U25.19 Blast (twin-only `_pool=False`
  for the chip simulation clocks), A.U14.12 (pool size read from SPEC F.1, 16 until then), A.U18.23 / A.U25.56 (their
  L2 cases need the pool), A.U25.68 (Timer init rules cited, pinned; `Timer(freq=)` source), A.U24.18 (`TEST_API`),
  A.U24.17 (no Timer check in the contract — holds)
- **Site**: `digital_twin/machine.py:780-832` (`class Timer`)
- **Change**: module state `_ALARM_POOL_SIZE = 16` ("# PICO_TIME_DEFAULT_ALARM_POOL_MAX_TIMERS, SPECIFICATION.md F.1")
  and `_ALARMS_FREE = _ALARM_POOL_SIZE`; `def set_alarm_pool_free(n: int) -> None` ("# Test-only: lets an L2 test
  exhaust or refill rp2's alarm pool; silicon has no such call"). `class Timer`: `ONE_SHOT = 0`, `PERIODIC = 1`;
  `__init__(self, id=-1, *, mode=PERIODIC, callback=None, period=0xFFFFFFFF, tick_hz=1000, freq=None, hard=False,
  _pool=True)`: `id != -1` raises `ValueError("Timer doesn't exist")` (`machine_timer.c:127-129`); `_pool=False` marks
  a chip-side simulation clock ("# twin-only: a chip fake's simulation clock, not an rp2 alarm - it never touches the
  pool"); with any argument beyond the twin-only `_pool`, `init()` runs (`:131-136`), a bare `Timer()` takes no alarm.
  `init(*, mode=PERIODIC, callback=None, period=0xFFFFFFFF, tick_hz=1000, freq=None, hard=False)`: cancels a running
  schedule first (returning its alarm), computes `self._period_us` as `int(1_000_000 / freq)` when `freq` is given, else
  `period * 1_000_000 // tick_hz`, floored at 1 (`:88-103`); takes one alarm unless `_pool` is off, raising
  `OSError(errno.ENOMEM)` when `_ALARMS_FREE == 0` (`:108-110`, "# rp2 adds the alarm whether or not a callback is given
  (:107)"); bumps `self._gen` and starts `_run(self._gen)`. `_run(gen)`: sleeps `asyncio.sleep_ms(max(1, period_us //
  1000))` ("# the Unix-port asyncio schedules in ms (fidelity row)"), returns when `self._gen != gen` (a re-`init()`
  from inside the callback supersedes this loop), then calls the callback — a `hard` callback that raises ends the
  schedule and frees the alarm; a soft one's `Exception` is printed (`sys.print_exception`) and the loop continues
  ("# A soft callback's exception is printed by the scheduler and the alarm re-arms (py/scheduler.c:115,
  machine_timer.c:50-60, v1.29.0); only a hard one stops"); a ONE_SHOT returns after one call and frees its alarm. A
  `BaseException` (the twin's `SimulatedRebootError`, `SimulatedPowerLoss`) is not caught and leaves the loop — it ends
  `asyncio.run()` (M.TWIN.034). `deinit()`: cancels the task unless it is the running one, frees the alarm once, bumps
  `_gen`; its "Skip the self-cancel" comment → "# A callback that re-arms runs inside the old loop's task, which a
  MicroPython Task cannot cancel; the bumped generation ends that loop after the callback returns." `TEST_API = ("id",
  "mode", "callback", "period")` (rp2's Timer exposes none of them).
- **Resolved**: A.U25.19 (2) says a "ONE_SHOT that fired" returns its alarm — on rp2 `alarm_callback()` returns 0 and
  the pool frees the alarm (`machine_timer.c:53-57`), consistent. The finaliser that disarms an unreferenced armed Timer
  is not modelled (A.U25.19's own sentence) — a fidelity row, its proof L1/L3.
- **Unit**: U25
- **Depends**: A.U14.12 (pool-size fact in SPEC F.1)
- **Blast carried by**: every product Timer (no `src/` change); chip fakes' factory → M.TWIN.023; tests (`:460-520`
  hold; `:505` asserts the alarm returned; pool+1 → ENOMEM; `deinit()` frees one; re-arm inside the callback runs one loop
  — 3 calls over three periods; `freq=10` → 100 ms; `Timer(0)` → `ValueError`; a soft PERIODIC raising once still runs
  its second; a hard one stops and frees) → M.TWIN.128; degradation paths per device → M.TWIN.152; fidelity rows (ms
  scheduling, soft-callback exception, finaliser not modelled) → M.TWIN.059; Timer facts pinned → M.TWIN.138
- **Kind**: code

### M.TWIN.031 `WDT`: saturating counters, bounded logs with a drop count, `feed_times`, fault-instant line support
- **From**: A.U25.22 (`would_have_triggered_log` a `BoundedLog`), A.U25.23 (`would_have_triggered_count`, `feed_count`
  saturate), A.S0930.24 (twin `feed_times`, `ticks_ms()` stamps, bounded like the other logs — A.U24.17's contract),
  AC_NOTES 36 (A.U24.17's twin WDT `feed_times` co-lands), A.U35.31 (`_countdown()`/`_arm()` read by its flag; no class
  change — the `WDT_AT_FAULT <feed_count>` line is the runner's), A.U10.07 Blast (the twin WDT records
  `would_have_triggered_count`; boots assert 0 — holds), A.S0930.27 (4) (`_arm()`'s late-feed backstop catches a blocking
  hang — holds), A.U8.08 (`_WDT_TIMEOUT_MAX_MS = 8388` is a fact, untagged — holds), A.U24.17 (`check_wdt_timeout_bounds`
  — holds at HEAD), A.U25.68 (the cap comment already cites the source), A.U27.28 (the `:835-838` comment block is 4
  lines), A.U24.18 (`TEST_API`), A.SDEP.08 (`:836` re-check), A.U14.33 (`:862-871` deltas — hold)
- **Site**: `digital_twin/machine.py:835-896`
- **Change**: the cap comment → "# RP2040 cap: 0xffffff / 2 / 1000 ms (ports/rp2/machine_wdt.c:32-38, v1.29.0, SPECIFICATION.md
  F.1); a larger timeout or any id but 0 raises ValueError, as rp2." (2 lines). `__init__`: `self.feed_count = 0`,
  `self.would_have_triggered_count = 0`, `self.would_have_triggered_log = BoundedLog(LOG_MAXLEN)`, `self.feed_times =
  BoundedLog(LOG_MAXLEN)` ("# ticks_ms() of each feed, newest last: the gap checks of the ownership tests read it");
  the two comment blocks at `:852-858` → one 3-line block "Twin-only: an asyncio countdown since the last feed() that
  records a would-have-reset rather than acting, with no disable API (a real armed WDT has none) - digital_twin/
  README.md 'WDT._arm()'s late-feed backstop'." `_record_would_trigger()` and `feed()` step their counters through
  `saturating_add`; `feed()` appends `time.ticks_ms()` to `feed_times` before re-arming. `_armed_at_ms: "int | None"`
  (an opaque ticks value, typed `int`). `TEST_API = ("id", "timeout", "feed_count", "would_have_triggered_count",
  "would_have_triggered_log", "feed_times")`.
- **Resolved**: —
- **Unit**: U25 (A.S0930.24's `feed_times` co-lands, AC_NOTES 36)
- **Depends**: M.TWIN.001
- **Blast carried by**: tests (WDT log `dropped == n - 200`; counters at the cap stay; `feed_times` grows per feed and
  is bounded) → M.TWIN.126; the contract's `feed_times` check → A.U24.17 / A.S0930.24 (TEST_HELP); the runner's exit
  WDT line, `WDT_AT_FAULT` and `HANG <step>` lines → M.TWIN.050, M.TWIN.051
- **Kind**: code

### M.TWIN.032 `mem_backup()` and `reset_cause()` with rp2's regions and survive/clear rules
- **From**: A.U25.08 (constants, two regions, identity, `-1` tuple, `ValueError("invalid region")`, `reset_cause()`,
  test-only `power_on()`, `configure_mem_backup_state_path()`/`flush_mem_backup()` with load-then-delete, header
  comment, bootloader carry-over an assumption), A.U11.05 Blast ("U25's G7/R07 fake must land in the same commit or
  every twin boot fails"), A.U25.32 (3) (graceful load), A.U25.24 (the new hook calls `_require_unconstructed`),
  A.U25.68 (`mem_backup()` model cited, pinned), A.U25.54 (a power loss clears the regions — the runner does not flush
  them, M.TWIN.050)
- **Site**: new block in `digital_twin/machine.py` after `WDT`, before `RTC`
- **Change**: `PWRON_RESET = 1`, `WDT_RESET = 3` (`ports/rp2/modmachine.c:57-58, 65-66`); `_MEM_BACKUP = (memoryview(array("I",
  [0] * 4)), memoryview(array("I", [0] * 3)))` built at import (`machine_mem_backup.c:38-40`); `reset_cause_value =
  PWRON_RESET`; `mem_backup(region: int = 0)` returns `_MEM_BACKUP[region]` (the same object each call,
  `extmod/machine_mem.c:145-148`), `-1` the tuple (`:136-143`), anything else `ValueError("invalid region")`;
  `reset_cause()` returns `reset_cause_value`; `power_on()` — "Test-only: a power-on/RUN clear (RP2040 datasheet 4.7.4)"
  — zeroes both regions and sets `PWRON_RESET`. `configure_mem_backup_state_path(path: str | None)` (after
  `_require_unconstructed`): a present, valid file `{"cause": int, "regions": [[4 ints], [3 ints]]}` is applied and then
  **deleted**; a missing, malformed, wrong-length or mistyped file leaves power-on (comment "# a launch not preceded by a
  simulated reset is a power-on"); `flush_mem_backup()` writes the file — called only by the runners' reset handler.
  Header comment A.U25.08's (3 lines): "mem_backup(): rp2's two watchdog-scratch regions; they survive machine.reset()
  (carried to the next launch by the reset handler) and are cleared by power-on (v1.29.0 machine_mem_backup.c:36-40);
  the bootloader carry-over is an assumption (digital_twin/README.md fidelity table)."
- **Resolved**: —
- **Unit**: U25 (stage U11: the block without the `_require_unconstructed` call lands in A.U11.05/.06/.07's commit —
  A.U11.05's Blast: every twin boot calls `mem_backup()`/`reset_cause()` from U11 on, so the twin needs them then; U25 adds
  the late-call check, `reset()`'s cause (M.TWIN.034) and the runners' flush (M.TWIN.050))
- **Depends**: M.TWIN.022 (`_require_unconstructed`), M.TWIN.034
- **Blast carried by**: runners' reset handler flushes it (exit 3/4) and `--mem-backup-state-path` → M.TWIN.050, M.TWIN.044;
  tests (sizes, identity, `-1`, `2`/`-2` raise, `power_on()`, round trip, bad file) and the shared
  `tests/_mem_backup_contract.py` → M.TWIN.128 and A.U25.08 (TEST_HELP); `.gitignore` gains
  `digital_twin/mem_backup_state.json` → A.U25.32 (`.gitignore` is in no cluster — gap to the lead); fidelity rows and the BACKLOG BOOTSEL row → M.TWIN.059,
  A.U25.08 (DOCS)
- **Kind**: code

### M.TWIN.033 `RTC`: rp2's constructor and 8-tuple rules; the setter steps the installed wall clock
- **From**: A.U25.20 (`RTC()` takes no argument; `datetime(dt)` needs 8 fields, stores Y/M/D/h/m/s, returns `None`;
  the getter recomputes the weekday and sets field 7 to 0), A.U25.71 (an installed wall clock: the setter sets its
  offset, the getter reads it; uninstalled keeps the stored tuple), A.U10.28 / A.U18.26 (their L2 halves need it),
  A.U25.68 (cited), A.U24.18 (`TEST_API`)
- **Site**: `digital_twin/machine.py:898-913` (`class RTC`)
- **Change**: class comment → "# One static peripheral (class-level state, as rp2). With the runner's wall clock
  installed (_wall_clock.py) a set moves time.time()/gmtime() as on silicon (ports/rp2/machine_rtc.c:65-98, v1.29.0)."
  `__init__(self) -> None` (no `id`: `machine_rtc.c:52`). `datetime(self, dt=None) -> "tuple[int, ...] | None"`: with
  `dt` — `len(dt) != 8` raises `ValueError("tuple/list has wrong length")` (`:84`); the six fields Y, M, D, h, m, s are
  stored in `_shared_datetime` and, when `_wall_clock.installed()` is set, its `set_wall(time.mktime((Y, M, D, h, m, s,
  0, 0)))` is called; returns `None` (`:95-98`). Without `dt`: when a clock is installed, its `gmtime()` gives the
  fields, else `_shared_datetime`; the result is `(Y, M, D, weekday, h, m, s, 0)` with the weekday recomputed from the
  date (`time.gmtime(time.mktime(...))[6]`). The `:907-909` comment goes. `TEST_API = ()` (nothing beyond rp2's surface).
- **Resolved**: G7/R05's "The RTC holds a fixed tuple, never advances" and A.U25.71's advancing installed clock: A.U25.71
  is the later action and names the fidelity row's new state ("fixed (installed by the runner)") — the uninstalled RTC
  keeps the fixed tuple, so both hold.
- **Unit**: U25
- **Depends**: M.TWIN.019
- **Blast carried by**: `src/asy_ntp_client.py:263` set call ignores the return (no change); any twin test using the
  setter's return switches to a separate get (grep `datetime((` in `tests/test_digital_twin_*.py`) → M.TWIN.128 and per
  file; `tests/test_digital_twin_machine.py:451-455` holds; new L2 (setter returns `None`, `RTC(0)` → `TypeError`, a
  7-tuple → `ValueError`, a wrong weekday reads back corrected, installed-clock cases) → M.TWIN.128; fidelity RTC row →
  M.TWIN.059
- **Kind**: code

### M.TWIN.034 Reset exceptions end the loop; `reset()` records the boot cause; a power loss is a sibling
- **From**: A.U25.07 (`SimulatedRebootError(BaseException)`, comment, `reset()` records `WDT_RESET`, `bootloader()` the
  same as an assumption, the "Step 5 harness" comment goes), A.U24.17 (`check_reset_never_returns`; the unit fake adopts
  these names — U25 conflicts row 7, settled by A.U24.17's text), A.U23.33 Blast (`reboot`/`bootloader` not driven live:
  the twin raises and does not restart — holds), A.U25.23 (`reset_count`, `bootloader_count` saturate), A.U25.54
  (`SimulatedPowerLoss(BaseException)`, a sibling, not a subclass), A.U25.09 (the runners' handler, M.TWIN.050)
- **Site**: `digital_twin/machine.py:916-946`
- **Change**: `class SimulatedRebootError(BaseException)` with A.U25.07's comment (3 lines): "BaseException, not
  Exception: no product `except Exception` may survive a reset, and asyncio re-raises it out of the running loop
  (extmod/asyncio/core.py:154, 194, v1.29.0) - the twin's reset ends the process as silicon's ends the program."
  `SimulatedResetError`, `SimulatedBootloaderEntryError` keep their names. New `class SimulatedPowerLoss(BaseException)`
  — "# Twin-only: SPI.lose_power_after() fired; a runner seeing it flushes FRAM/SCD30 state but never mem_backup (a
  power-on clears it, machine_mem_backup.c:36-40)". `reset()`: `reset_count = saturating_add(reset_count)`,
  `reset_cause_value = WDT_RESET` ("# machine.reset() is watchdog_reboot() on rp2, so the next boot reads WDT_RESET
  (ports/rp2/modmachine.c:74-88)"), then raise; `bootloader()`: count, the same cause ("# assumption: fidelity table"),
  raise. The `:935-937` comment keeps its one fact in ≤ 3 lines.
- **Resolved**: U25 conflicts row 7 (A.U24.17 reset names) — settled in A.U24.17's text (the unit fake adopts the
  twin's names and `BaseException`).
- **Unit**: U25
- **Depends**: M.TWIN.032 (the cause constants)
- **Blast carried by**: runners' `except SimulatedRebootError` exit 3/4 and `SimulatedPowerLoss` handling →
  M.TWIN.050; every L2 file that can reach a product reset catches it and calls `asyncio.new_event_loop()` (C4) →
  M.TWIN.100-164; new L2 (`not issubclass(SimulatedRebootError, Exception)`; a Timer calling `reset()` ends
  `asyncio.run()` with `SimulatedResetError` while an `except Exception` sibling keeps nothing alive) → M.TWIN.128; the
  unit fake → A.U24.17 (TEST_HELP); fidelity rows → M.TWIN.059
- **Kind**: code

### M.TWIN.035 `peripheral()`, `reset_peripherals()` and the twin's per-test state reset
- **From**: A.U25.03 (2)-(3) (`peripheral(name)`, test-only `reset_peripherals()` clearing the three registries; its
  comment quoting the owner), A.U25.28 (`peripheral()` is the runner's and tests' one inspection entry), A.U24.07 Blast
  ("twin `digital_twin/machine.py`/`network.py` carry their own class state (U25, same shape, G2/R07 contract)" — no
  U25 action writes the twin's per-test reset: a gap closed here), A.U25.24 (`reset_peripherals()` is what a late
  configure needs first), A.U25.59 (re-plug keeps the chip; `reset_peripherals()` is not a re-plug)
- **Site**: new module functions in `digital_twin/machine.py` (after `Pin`'s registry, beside the configure hooks)
- **Change**: `_I2C_OBJECTS: "dict[int, I2C]" = {}`, `_SPI_OBJECTS: "dict[int, SPI]" = {}`, `_UART_OBJECTS: "dict[int,
  UART]" = {}`. `peripheral(name: str) -> "I2C | SPI | UART | None"` — `"i2c<n>"`/`"spi<n>"`/`"uart<n>"` → the
  registered object or `None` ("# Twin-only: the one way the runner and tests reach a booted bus, never through a
  product wrapper's private attribute"). `reset_peripherals()` clears the three registries in place ("# Test-only:
  silicon never forgets its peripherals; test isolation needs it (owner, 2026-09-25: \"Only if there is no alternative,
  and keep tiny anyway\")"). New `reset_test_state()` — "Test-only: restores every process-wide twin knob a test can
  change" — calls `reset_peripherals()` and `Pin.reset_registry()`, sets `_wiring_plan`, `_random_source`,
  `_fram_state_path`, `_scd30_state_path`, `_mem_backup_state_path`, `_current_fram_chip`, `_current_scd30_chip` to
  `None`, `_ALARMS_FREE` to `_ALARM_POOL_SIZE`, `UART.would_have_blocked_bytes`, `reset_count`, `bootloader_count` to 0,
  `power_on()`, and `RTC._shared_datetime` to its default. It imports no test module (the twin never has `tests/` on its
  path); the twin test files register it themselves with `microtest.after_each(machine.reset_test_state)` (C4).
- **Resolved**: A.U24.07 gives the unit fake `reset_test_state()` registered through `microtest.after_each` and says the
  twin carries "the same shape"; the twin cannot import `microtest` (G7/R02: `tests/` is absent from a standalone twin's
  path), so the function lives here and the registration lives in each twin test file — agent decision, OR2.c list.
- **Unit**: U25
- **Depends**: M.TWIN.024, M.TWIN.026, M.TWIN.028, M.TWIN.030, M.TWIN.032
- **Blast carried by**: every twin test file registers `machine.reset_test_state` and `network.reset_test_state` (C4)
  → M.TWIN.100-164 and TEST_HELP's scenario libraries; `run_generic_integration` uses `peripheral()` → M.TWIN.049; new L2
  (two constructions are one object; `peripheral("i2c1") is` it; `reset_test_state()` restores each knob) → M.TWIN.126
- **Kind**: code

### M.TWIN.036 Remaining `machine.py` comments: no plan pointers, cited facts
- **From**: A.U25.24 / A.U36.544 (`:310-311` — carried by M.TWIN.022), A.U25.28 / A.U0.38 (`:302-304` — M.TWIN.022),
  A.U1.25 (`:482` — M.TWIN.027), A.U36.532 (`:702` — M.TWIN.028), A.U25.68 (the remaining cited constants — M.TWIN.021,
  .026, .028, .030, .031, .032), A.U27.28 (every block ≤ 3 lines), A.U8C2.10 Blast ("twin `digital_twin/machine.py`
  unchanged" — holds), A.U5.15 Blast (chip construction — M.TWIN.023)
- **Site**: `digital_twin/machine.py` (whole file, comment pass)
- **Change**: the comment blocks the merged changes above do not already rewrite are read once for C5: `:156-158`,
  `:164-165` (M.TWIN.022), `:443-445` (`_LinkDirection`, 3 lines, kept), `:489-491`, `:500-502`, `:533-534`, `:539-540`,
  `:578-579` (kept, each ≤ 3 lines, current facts), `:695-697` (`any()`, kept). No "Step 5", "this step", "used to",
  "the old" wording remains (grep at execution).
- **Resolved**: —
- **Unit**: U25
- **Depends**: M.TWIN.020-035
- **Blast carried by**: A.U27.28's gate (TSC) finds nothing to rewrap in this file
- **Kind**: doc

## digital_twin/network.py

### M.TWIN.040 Twin WLAN: per-interface singletons, cyw43 status rules, AP address, TEST-NET STA, bounded logs
- **From**: A.U25.27 (singletons from `_INTERFACES`, `constructions` count, one radio `deinit()`, test-only
  `reset_interfaces()`, `raise_on[method] = (exc, times)`), A.U25.26 (`status()` raises as cyw43; the 0.7 s connect
  phase pinned), A.U25.72 (AP `active(True)` → `STAT_GOT_IP` and `192.168.4.1/255.255.255.0/192.168.4.1/<shared DNS>`;
  `config()` truncates `essid` 32/`password` 64 and answers `config("essid")`), A.U25.33 (1) (`_CONNECTED_IFCONFIG` →
  TEST-NET-1 `("192.0.2.42", "255.255.255.0", "192.0.2.1", "192.0.2.1")`), A.U25.22 (`config_calls`, `connect_calls` as
  `BoundedLog`), A.U25.23 (`constructions` saturate), A.U25.24 (`:71-72` "Test/Step-5-run" pointer), A.U18.33 / A.U24.19
  Blasts (status raises outside the mode — this change), A.U18.28 Blast (AP reports `STAT_GOT_IP` — A.U25.72), A.U18.32
  Blast (`_CONNECT_DELAY_S`'s comment names the 5 s budget), A.U18.27 Blast ("twin status constants (U25 reads the
  list)" — no U25 action does: closed here), A.U24.09 Blast ("twin … same 'DE'/'SensorNode' seeds (U25, same values)" —
  the unit fake moves to rp2's power-on `"XX"`/`"PicoW"`; no U25 action follows: closed here), A.U14.37 Blast (the
  country/hostname byte bounds "identically in fakes" — hold at `:42`, `:50`; AP config truncation is A.U25.72's),
  A.C.14 Blast (the measured unknown-country reaction modelled once recorded — phase-C delta via A.C.10), A.U8.10 /
  A.U8.20 / A.U31.15 (`_CONNECT_DELAY_S` tagged `l2.twin_wifi_connect_delay_s`, a Dependant of the 5 s poll total),
  A.U36.544 (`:137` "A.4" → F.1), A.U28.27 (ruff S104's per-file reason names "the fake's unset `ifconfig()` address" —
  TOOL), A.U6.30 Blast (`country()` unchanged — holds), A.U6.29 Blast (no twin entry), A.U27.28 (header over the cap)
- **Site**: `digital_twin/network.py:1-151` (whole file)
- **Change**: header → "Twin fake of the rp2 network module (the Unix port has none): WLAN fakes connection state only
  - real NTP/DNS/HTTP traffic uses the host's sockets. Per-interface singletons with cyw43's status rules and a 0.7 s
  connect phase; independent of tests/network.py (digital_twin/README.md fidelity table)." (3 lines). `from _twin_common
  import LOG_MAXLEN, BoundedLog, saturating_add`; `_CALL_LOG_MAXLEN` and its 4-line comment go. Status constants each
  cite `extmod/network_cyw43.c`/`cyw43.h` on the line (`STAT_IDLE = 0`, `STAT_CONNECTING = 1`, `STAT_GOT_IP = 3`,
  `STAT_CONNECT_FAIL = -1`, `STAT_NO_AP_FOUND = -2`, `STAT_WRONG_PASSWORD = -3`, read from the CYW43 link-status defines
  at the pinned submodule) and are pinned by M.TWIN.138. `_CONNECT_DELAY_S = 0.7` gains `# @tunable
  l2.twin_wifi_connect_delay_s = 0.7` (row basis U8C's; Dependant of the 5 s connect-poll budget), its comment → "# One
  real STAT_CONNECTING phase, under _poll_sta_connect_status()'s 5 s budget (pinned by a test)". Seeds `_country_code =
  ["XX"]  # extmod/modnetwork.c:71 (v1.29.0) power-on value` and `_hostname_value = ["PicoW"]  #
  ports/rp2/boards/RPI_PICO_W/mpconfigboard.h:8`. `_CONNECTED_IFCONFIG` → the TEST-NET-1 tuple with "# RFC 5737
  TEST-NET-1: the DHCP-provided DNS is unroutable, so no twin run reaches a public resolver"; `_UNSET_IFCONFIG =
  ("0.0.0.0",) * 4`; `_AP_IFCONFIG_BASE = ("192.168.4.1", "255.255.255.0", "192.168.4.1")  # cyw43_config.h:194, 206`;
  `_dns = ["192.0.2.1"]` (one lwIP DNS server shared by both interfaces, `extmod/network_lwip.c:70-73`). `_INTERFACES:
  dict[int, WLAN] = {}`, `constructions = {STA_IF: 0, AP_IF: 0}`. `WLAN.__new__(cls, if_id=STA_IF)` returns the STA
  singleton for `STA_IF`, the AP singleton for any other id (`network_cyw43.c:96-103`), steps `constructions` (saturating)
  and creates state on the first construction only (`__init__` guards with an `_initialised` flag). `raise_on: dict[str,
  tuple[type[BaseException], tuple[object, ...], int | None]]` with comment "# twin-only test knob: method -> (exception
  type, args, times); times None raises until cleared"; `_maybe_raise()` raises `exc_type(*args)` — a fresh instance
  each time — and decrements a counted entry, removing it at 0. `active(value)`: on the AP singleton
  `True` sets `STAT_GOT_IP` and `_AP_IFCONFIG_BASE + (_dns[0],)`, `False` restores `STAT_IDLE` and `_UNSET_IFCONFIG`.
  `_run_connect()` on success sets `_CONNECTED_IFCONFIG` and `_dns[0] = _CONNECTED_IFCONFIG[3]`. `deinit()` powers the
  one radio down: both singletons inactive, disconnected, `STAT_IDLE`, `_UNSET_IFCONFIG`, pending connects cancelled,
  `deinit_called = True` ("# one cyw43_state behind both interfaces (cyw43_ctrl.c:118-146)"). `status(param=None)`:
  `None` → the link status; `"rssi"` raises `ValueError("STA required")` off STA; `"stations"` raises `ValueError("AP
  required")` off AP; any other string `ValueError("unknown status param")`; comment "# As extmod/network_cyw43.c:355-392
  (v1.29.0); SPECIFICATION.md F.1 states the contract." `config(*args, **kw)`: with one positional name returns the
  stored value (`essid`, `password` read back); with keywords stores a copy, `essid` cut to 32 and `password` to 64
  bytes ("# cyw43 truncates silently (cyw43.h:130-131, 431-448)"), and appends the copy to `config_calls`.
  `config_calls`/`connect_calls` are `BoundedLog(LOG_MAXLEN)`. New module functions `reset_interfaces()` ("# Test-only,
  as machine.Pin.reset_registry(): silicon never forgets its interfaces") clearing `_INTERFACES` and the counts, and
  `reset_test_state()` restoring `reset_interfaces()`, the two seeds and `_dns` (registered by the twin tests, C4).
  `WLAN.TEST_API = ("if_id", "config_calls", "connect_calls", "deinit_called", "disconnect_called", "raise_on",
  "script_connect_outcomes")` (comment: the L0 surface check covers `machine` fakes; this list documents the twin-only
  names).
- **Resolved**: A.U25.27 writes `raise_on[method] = (exc, times)` with one exception instance; G7/R16 ("faults …
  raise a fresh exception each time", OR21.a (1)) and A.U25.70's reason (a re-raised MicroPython instance grows its
  traceback — with `times=None` without bound, against OR110.a's no-growth rule) settle the stored form as a type and
  its arguments, the same as `FaultInjector` (adherence fix). The per-interface singleton (A.U25.27) and HEAD's
  per-construction state: A.U25.27's `__new__` creates
  state once, so A.U25.72's AP state and A.U25.33's STA address live on the singletons — one model. A.U18.27 and A.U24.09
  each leave a twin follow-up to U25 that no U25 action writes; both are closed here as their Blasts state (the seeds'
  values from A.U24.09's cited sources; the status constants cited and pinned).
- **Unit**: U25
- **Depends**: M.TWIN.001; A.U18.33, A.U18.32 (service reads and budget constant), A.U18.R01 (re-init rung user)
- **Blast carried by**: `src/asy_wifi_service.py` mode switches get the same objects (product, SRC_NET — no change); the
  AP-mode rssi / STA-mode stations paths reach the raise at L2 — the executor records whether a service path logs it
  (then A.U18.33's, SRC_NET); `captive_dns` reads `192.168.4.1` (SRC_NET — no change); runners' `_apply_fault()` for
  `wlan` passes `times` → M.TWIN.044, M.TWIN.049; `launch.parse_fault_spec()`'s `wlan` `:TIMES` refusal goes →
  M.TWIN.044; tests (`reset_interfaces()` before isolated constructions; status rules; singleton identity, counts,
  one-radio `deinit()`, `raise_on` times; AP address and truncation; `ifconfig()[3]` shared; bounded logs `dropped == n -
  200`; the deactivated-radio LED pattern (A.U18.30); seeds `"XX"`/`"PicoW"`; `_CONNECT_DELAY_S` < the service budget)
  → M.TWIN.132; the hotspot test's DNS query path re-checked → M.TWIN.144; the A.U18.R01 L2 rung → M.TWIN.144;
  `pyproject.toml` S104 per-file reason → A.U28.27 (TOOL); fidelity rows → M.TWIN.059; README `network.py` bullet →
  M.TWIN.058
- **Kind**: code

## digital_twin/neopixel.py

### M.TWIN.042 Twin NeoPixel stores bytes as micropython-lib does; bounded frame log with a drop count
- **From**: A.U25.21 (`buf = bytearray(n * bpp)`, `ORDER = (1, 0, 2, 3)`, `__setitem__` per component in order — int
  truncated, float `TypeError` after earlier components land; `__getitem__` rebuilds; `writes` records `bytes(buf)`; the
  docstring's "no behavioral change" goes), A.U25.22 (`writes` a `BoundedLog`), A.U25.68 (NeoPixel blocking and colour
  order cited and pinned), A.U27.28 (header)
- **Site**: `digital_twin/neopixel.py:1-32`
- **Change**: header → "Twin fake of micropython-lib's neopixel module (the Unix port has none): a bytearray in GRB order
  as drivers/led/neopixel/neopixel.py stores it, and a bounded log of every written frame. Independent of
  tests/neopixel.py." (2-3 lines). `from _twin_common import LOG_MAXLEN, BoundedLog`; `_WRITES_MAXLEN` and its comment go.
  `class NeoPixel`: `ORDER = (1, 0, 2, 3)  # GRB(W), micropython-lib neopixel.py:9 (pinned version)`;
  `__init__(self, pin, n, bpp=3)` (HEAD's signature): `self.buf =
  bytearray(n * bpp)`, `self.writes = BoundedLog(LOG_MAXLEN)`, `self.raise_on_write: Exception | None = None` (comment
  "twin-only test knob"); `__setitem__(i, v)`: `offset = i * self.bpp`; `for k in range(self.bpp): self.buf[offset +
  self.ORDER[k]] = v[k]` (comment "# As micropython-lib neopixel.py:28-31: an int keeps its low byte (py/binary.c:512-521),
  a float raises TypeError at its component"); `__getitem__(i)` returns `tuple(self.buf[offset + self.ORDER[k]] for k in
  range(self.bpp))`; `write()` raises `raise_on_write` when set, else
  appends `bytes(self.buf)` ("# The real write() is one blocking bitstream call with no return value (machine.bitstream,
  micropython-lib neopixel.py write())"). `_buf` goes.
- **Resolved**: —
- **Unit**: U25
- **Depends**: M.TWIN.001; A.U9.06 (driver clamps before the store)
- **Blast carried by**: `src/asy_neopixel_driver.py` (only ints 0-255 reach it after A.U9.06 — no change); tests (frames
  compared as `bytes` or read back through `__getitem__`; `(256, 0, 0)` reads `(0, 0, 0)`; `(1.5, 0, 0)` raises;
  `(10, 1.5, 0)` raises with G = 10; `dropped == n - 200`) → M.TWIN.132; hotspot LED assertions on `writes` →
  M.TWIN.144; fidelity row "NeoPixel" → M.TWIN.059; README bullet → M.TWIN.058
- **Kind**: code

## digital_twin/launch.py

### M.TWIN.044 Launcher header, shared fault/hang vocabulary, parsers and grouped config
- **From**: A.U25.25 (4) (required `--wiring-plan PATH`; docstring "the bus wiring of the device whose plan it is
  given"; the `_FAULT_DEVICE_OPS["isl29125"]` comment goes), A.U25.37 (1) (instance keys `<driver>_<name_ext>`; per-driver
  ops: `scd30` `writeto|readfrom_into`, `sgp40` `writeto|readfrom_into|general_call`, `bmp3xx`
  `writeto|readfrom_mem|writeto_mem`, `isl29125` `writeto|readfrom_mem|writeto_mem|int_stuck_high`, `fram`
  `readinto|wren|silent`, `uart_link` `silent`, `wlan` every `raise_on` method with `:TIMES`; `_HANG_DEVICE_OPS` gains
  `bmp3xx:writeto`, `isl29125:writeto`), A.U25.18 (`fram` vocabulary without `write`), A.U25.27 (`wlan` `:TIMES`
  accepted), A.U25.70 (`--fault DEVICE:OP[:TIMES[:MATCH]]`, `MATCH` hex), A.U25.41 (`_pop_value` shared; the docstring's
  argparse sentence; `_decode_calibration` imported), A.U25.32 (1) (`LaunchConfig` defaults persist to
  `digital_twin/*.json`; `""` = in-memory), A.U25.09 (the mem-backup path joins both configs — see Resolved), A.U5.15
  (`LaunchConfig(state, injections, *, no_wdt_feed, duration)`, `StatePaths`, `Injections`), A.U0.31 (`:2` tag "(owner's
  choice over a probabilistic flaky mode, 2026-08-12)"), A.U7.19 (`--help` exits 0 before any side effect), A.U25.42
  (`import random` at module top), A.U25.39 (the `unix_port_gc_unwedge` import goes), A.U8.20 (`:41-43` tagged), A.U8.08
  (`:369` `WDT(timeout=8000)` tagged `wdt.timeout_ms`; `:41` `l2.twin_wdt_feed_interval_s`), A.U27.28 (header), A.U8C.26 /
  A.U8C2.09 (the test file's rows — M.TWIN.124), A.U28.29 (`pyproject.toml`'s S105/S106 reason above this file — TOOL),
  A.U36.546 / A.U36.547 (SPEC E.3 and README reference name this file's tracked-task list and its `--help` block — SPEC/DOCS)
- **Site**: `digital_twin/launch.py:1-188`
- **Change**: header → "Standalone CLI launcher for the twin (micropython digital_twin/launch.py --wiring-plan PATH
  [options]), src/-free: it builds the buses of the device whose plan it is given and periodically reads each wired
  sensor, attempts one WLAN connect and feeds a WDT. --fault/--hang expose each chip fake's FaultInjector (owner's choice
  over a probabilistic flaky mode, 2026-08-12)." (3 lines); the argparse sentence moves to `parse_args()`'s comment:
  "# Hand-rolled: micropython-lib's argparse supports only store/store_const
  (python-stdlib/argparse/argparse.py:91-124)." Imports: `asyncio`, `errno`, `random`, `struct`, `sys`; `machine`,
  `network`, `from machine import I2C, SPI, WDT, Pin`; `from _bmp3xx_chip import _decode_calibration`; `from
  _twin_common import Injections, StatePaths, saturating_add`; the unwedge import goes. `_FAULT_DEVICE_OPS` → A.U25.37's
  table; new `_PERSISTENT_FAULT_OPS = {("isl29125", "int_stuck_high"), ("fram", "silent"), ("uart_link", "silent")}`
  (modes, not counted faults: `TIMES`/`MATCH` refused). `_HANG_DEVICE_OPS` → `sgp40`/`scd30` `writeto|readfrom_into`,
  `bmp3xx` `writeto|readfrom_mem|writeto_mem`, `isl29125` `writeto|readfrom_mem|writeto_mem`, `fram` `write|readinto`;
  its comment keeps the wlan reason (≤ 3 lines). New `_driver_of(key) -> str | None`: the longest vocabulary driver
  `d` with `key == d` or `key.startswith(d + "_")` (so `uart_link_init` → `uart_link`). `parse_fault_spec(spec) ->
  "tuple[str, str, int, int | None]"`: `DEVICE:OP[:TIMES[:MATCH]]`; the device resolved by `_driver_of()` (error names
  the vocabulary); a persistent op refuses `TIMES`/`MATCH`; `MATCH` parsed with `int(x, 16)`; the `wlan` `:TIMES`
  refusal goes (`MATCH` refused for `wlan`). `parse_hang_spec()` resolves the device the same way. `_WDT_FEED_INTERVAL_S
  = 1.0` tagged `# @tunable l2.twin_wdt_feed_interval_s = 1.0` (comment "# well under the 8000 ms WDT timeout");
  `_SENSOR_POLL_INTERVAL_S = 2.0` tagged `l2.launch_sensor_poll_interval_s`, `_WIFI_POLL_INTERVAL_S = 0.1` tagged
  `l2.launch_wifi_poll_interval_s` (A.U8.20's `l2.<name>` form; U8C rows). `_SSID`/`_PASSWORD` keep their values
  (twin-only test doubles; the S105 reason line is A.U28.29's in `pyproject.toml`). `LaunchConfig(state:
  StatePaths, injections: Injections, *, no_wdt_feed=False, duration=None, wiring_plan_path: str)` — `wiring_plan_path`
  required keyword; `StatePaths(fram, scd30, mem_backup)` and `Injections(seed, faults, hangs, wifi_outcomes)` live in
  `_twin_common` (M.TWIN.001's module, shared with `RunConfig`). `parse_args(argv)`: `-h`/`--help` first → prints the
  usage block (synopsis, every flag with its default) and `sys.exit(0)`; flags `--wiring-plan` (required: a missing one
  raises `ValueError("--wiring-plan PATH is required")`), `--seed`, `--fram-state-path` (default
  `digital_twin/fram_state.json`), `--scd30-state-path` (`digital_twin/scd30_state.json`), `--mem-backup-state-path`
  (`digital_twin/mem_backup_state.json`), `""` meaning in-memory for each, `--fault`, `--hang`, `--wifi-outcome`,
  `--no-wdt-feed`, `--duration`; `_pop_value()` stays here (the runner imports it).
- **Resolved**: A.U25.32 (1) gives `LaunchConfig` the `mem_backup_state_path` default while A.U25.09 (3) says `launch.py`
  gets no reset handler (nothing there reaches `machine.reset()`); the path is still configured, so a launch after a
  runner's simulated reset on the same files boots with the carried regions — consistent with the twin's "a launch not
  preceded by a reset is a power-on" (M.TWIN.032); one `StatePaths` with three fields serves both configs (A.U5.15's
  two-field shape grows by A.U25.09/.32's third path) — agent decision, OR2.c list.
- **Unit**: U25 (stage U5: A.U5.15's grouping on the HEAD fields; U7: A.U7.19's `--help`; U8: the tags)
- **Depends**: M.TWIN.001, M.TWIN.002, M.TWIN.010-014, M.TWIN.040
- **Blast carried by**: `run_generic_integration.py` imports `_pop_value`, the parsers and `_driver_of` → M.TWIN.047;
  `tests/test_digital_twin_launch.py` (every documented device/op parses, `MATCH`, `wlan:…:TIMES` accepted, persistent
  ops refuse `TIMES`, `--wiring-plan` required, defaults flip to the persistent paths, `--help`) → M.TWIN.124; L0
  `tests_scripts/test_tool_help.py` → A.U7.19 (TSC); the CI matrix tables (`_SUSTAINED_FAULT`, `_HANG_MATRIX`, `_LEFT_OUT`)
  and the L0 matrix-completeness test → A.U25.37 (SCR, TSC); README `--fault`/`--hang`/`configure_fault()` text →
  M.TWIN.068; README command-line reference block → A.U36.547 (DOCS)
- **Kind**: code

### M.TWIN.045 Launcher body: plan-driven buses, shared chip lookup, fresh-exception faults, saturating summary
- **From**: A.U25.25 (4) (every I2C/SPI bus the plan lists, with the plan's pins; reads by the plan's address), A.U25.70
  (`inject_fault(op, OSError, errno.EIO, message, times=, match=)`), A.U25.27 (wlan `raise_on` with times), A.U25.37 (the
  persistent modes: `isl29125:int_stuck_high` → `configure_fault()`, `fram:silent` → `silent = True`, `fram:wren` →
  `drop_next_wren += times`, `uart_link:silent` refused here — no link), A.U25.41 (`_decode_calibration` imported; the
  local copy `:216-235` goes), A.U25.42 (`random` at the top), A.U25.23 (`summary["readings"]` saturates), A.U25.28 (the
  chip lookup goes through `machine.peripheral()`), A.U20.02 Blast (`launch.py:369` builds its own twin `WDT` — holds),
  A.U8.08 (`WDT(timeout=8000)` tagged), A.U36.546 (its tracked-task list stays the small-graph pattern SPEC E.3 names)
- **Site**: `digital_twin/launch.py:191-418`
- **Change**: `_apply_fault(device, op, times, match, chips, wlan)`: `wlan` → `wlan.raise_on[op] = (OSError, (errno.EIO,
  message), times)`; a persistent op → the chip's mode setter (`chips[d].configure_fault("isl29125:int_stuck_high")`,
  `chips[d].silent = True`); `fram:wren` → `chips[d].drop_next_wren += times`; else `chips[d].fault.inject_fault(op,
  OSError, errno.EIO, message, times=times, match=match)`; `uart_link` reaches `_require_wired()`, which names the wired
  set. `_apply_hang` unchanged but for the resolved key. New `_collect_chips(plan) -> dict[str, chip]`: for each
  attachment of each plan bus, `machine.peripheral(bus_name)` (absent → skipped: the bus was never constructed) and
  `.devices[address]` / `.device`, keyed by the plan's instance key (`<driver>` or `<driver>_<name_ext>`) — the one
  implementation; `run_generic_integration.py` imports it (M.TWIN.049). `_decode_bmp3xx_calibration()` is deleted;
  `_read_bmp3xx()` calls `_decode_calibration()`. `_read_scd30(bus, addr)`, `_read_sgp40(bus, addr)`,
  `_read_bmp3xx(bus, addr)` take the address. `main(config)`: `random.seed(config.injections.seed)` (module-top import;
  the 6-line comment → 3 lines: "MicroPython's random has no instantiable Random, but every chip fake falls back to this
  module generator, so one seed seeds every walk; configure_random_source() remains for a distinct generator."); reads the
  plan JSON from `config.wiring_plan_path`, calls `machine.configure_wiring(plan)`, `configure_fram_state_path`,
  `configure_scd30_state_path`, `configure_mem_backup_state_path` (each with `""` → `None`); `watchdog = WDT(timeout=8000)`
  with `# @tunable wdt.timeout_ms = 8000` (A.U8.08's row, this file one of its sites); constructs `I2C(n, scl=Pin(p["scl"]),
  sda=Pin(p["sda"]), freq=50000)` for every `i2c<n>` in `plan["buses"]` and `SPI(n, sck=…, mosi=…, miso=…)` for every
  `spi<n>` in `plan["spi"]`, pins from `plan["pins"]`; `chips = _collect_chips(plan)`; the sensor loop reads every wired
  SCD30/SGP40/BMP3xx at its plan address, each read isolated as today, `summary["readings"] =
  saturating_add(summary["readings"])`. The tracked-task list, the `finally` (cancel, WLAN status, WDT count, flushes,
  summary line) stay; the flushes go through `_shutdown_cleanup()` (M.TWIN.046). `summary` stays a plain `dict` typed
  `dict[str, int | None]` (no `Any`, A.U25.63).
- **Resolved**: A.U25.28 places `_collect_chips(plan)` in `run_generic_integration.py`; `launch.py` needs the identical
  lookup once A.U25.25 (4) makes it plan-driven (its `chips` literal `:375` becomes per-plan) — REF/R05/OR24 "one
  material" puts the one copy here, beside the other shared helpers the runner already imports from `launch`
  (A.U25.41's pattern) — agent decision, OR2.c list.
- **Unit**: U25
- **Depends**: M.TWIN.044, M.TWIN.024, M.TWIN.026, M.TWIN.035, M.TWIN.040
- **Blast carried by**: `tests/test_digital_twin_launch.py` main-run cases (a plan path from `tests/_twin_devices.py`,
  readings counted, a `--fault` per op class applied) → M.TWIN.124; README "What's here" launch bullet and "Booting" →
  M.TWIN.058, M.TWIN.061
- **Kind**: code

### M.TWIN.046 Launcher `__main__`: one shared shutdown cleanup, no unwedge
- **From**: A.U25.39 (the unwedge call and its comment go after A.U21.06's proof; one replacement line), A.U25.41
  (`_shutdown_cleanup()` holds the flush pair, imported by the runner for its SIGINT and reset handlers), A.U25.09 (3)
  (no reset handler here), A.U25.08 (the mem-backup file is flushed only by a reset handler — never on SIGINT)
- **Site**: `digital_twin/launch.py:420-435`
- **Change**: new module function `_shutdown_cleanup() -> None` calling `machine.flush_fram()` and
  `machine.flush_scd30()`, comment "# The one synchronous cleanup every twin exit path runs (SIGINT, a simulated reset in
  the runner)". `__main__`: `except KeyboardInterrupt:` → the A.U25.39 line "# Reached when the interrupt lands while
  main() is suspended: its finally never runs, so this is the only cleanup (SPECIFICATION.md F.1, asyncio.run() catches
  only CancelledError and Exception)." then `_shutdown_cleanup()` and the "interrupted" line. `main()`'s `finally` calls
  `_shutdown_cleanup()` too.
- **Resolved**: —
- **Unit**: U25 (after A.U21.06, A.U25.39's Depends)
- **Depends**: M.TWIN.045; A.U21.06 (the SIGINT-override proof)
- **Blast carried by**: the runner imports `_shutdown_cleanup` → M.TWIN.050; SPEC F.6/B.14.1 and CLAUDE.md unwedge text
  → A.U25.39 / U36 (SPEC, DOCS)
- **Kind**: code

## digital_twin/run_generic_integration.py

### M.TWIN.047 Runner header, imports and grouped run config with per-run state paths
- **From**: A.U25.28 / A.U36.513 (docstring `:1-3` current facts; `:32-34`, `:96-98` drop the retired runners), A.U5.15
  (`RunConfig(module, wiring_plan_path, host, port, device, state, injections, *, run)`, `RunLimits(duration,
  gc_threshold, mem_sample_interval_ms)`, `__eq__`/`__repr__`), A.U25.32 ((1) state-path defaults persist to
  `digital_twin/*.json`, `""` in-memory; (2) `--config-dir PATH`, default `digital_twin/config/`; `_ensure_dir()`
  swallows only `EEXIST`), A.U25.09 (1) (`--mem-backup-state-path`), A.U25.33 (`--online-ntp` skips the offline config),
  A.U25.41 (`_pop_value` imported from `launch`), A.U25.42 (`import errno`, `os`, `random` at the top), A.U25.39 (the
  unwedge import goes), A.U25.63 (no explicit `Any`: the booted module a `ModuleType` plus a `_Booted` Protocol), A.U8.14
  (`_GC_THRESHOLD_DEFAULT = 32768` tagged `gc.threshold_bytes`), A.U24.53 (the `tests_js` launches pass `--config-dir`
  — the flag is A.U25.32's), A.U10.30 (`__import__(config.module)` is F.1's named exception — stays), A.U24.46
  (`require_fresh()` — see Resolved), A.U27.28 (header), A.U0.38 / A.U0.29 (owner tags of the persistent default: E09
  "(owner, 2026-08-13)")
- **Site**: `digital_twin/run_generic_integration.py:1-190`
- **Change**: header → "Generic twin entry point: boots any buildgen-generated sensortask_<device> module against its
  wiring-plan JSON and serves until stopped; chips are found through machine.peripheral() by walking the plan. Its
  --test-* flags are test-only instrumentation, off by default (owner, 2026-09-30)." (≈ 290 characters, 3 counted
  lines; the README pointer moves to `main()`'s comment). Imports: `asyncio`, `errno`, `gc`, `json`, `os`, `random`, `sys`, `time`;
  `import machine`; `from launch import _collect_chips, _driver_of, _parse_wifi_outcome, _pop_value, _shutdown_cleanup,
  parse_fault_spec, parse_hang_spec` (comment "# one implementation of each, in launch.py"); `from _twin_common import
  Injections, StatePaths`; `from _offline_ntp_config import write_offline_ntp_config` (M.TWIN.053); `from
  _unix_port_udp_addr_shim import patch_asy_udp_socket_for_unix_port`; `from unix_port_poll_prewarm import
  prewarm_poll_set`; `import _wall_clock`; the `sys.path` gains `digital_twin/unixport` before those imports when the
  launch's `MICROPYPATH` lacks it (the launch scripts set it — SCR gap). `_CONFIG_DIR_DEFAULT = "digital_twin/config/"`
  (comment "# the manual run's persistent default (owner, 2026-08-13); automated callers pass their own --config-dir").
  `_booted_module: "_Booted | None"` with comment "# the module is chosen at run time (--module)". `_GC_THRESHOLD_DEFAULT
  = 32768` with `# @tunable gc.threshold_bytes = 32768` (A.U8.14's row) and its 3-line comment kept. `RunConfig(module,
  wiring_plan_path, host="localhost", port=8080, device=None, state=None, injections=None, *, run=None, config_dir=
  _CONFIG_DIR_DEFAULT, online_ntp=False, instrumentation=None)` — `state: StatePaths | None` (None → the three
  persistent defaults), `injections: Injections | None` (None → empty), `run: RunLimits | None` (None →
  `RunLimits(None, _GC_THRESHOLD_DEFAULT, None)`), `instrumentation: TestFlags | None` (M.TWIN.051); `RunLimits` a
  namedtuple in this file; `__eq__`/`__repr__` compare/print the grouped fields; the `:96-98` comment keeps its first
  two lines (the run_wozi clause goes). `parse_args(argv)`: `-h`/`--help` prints the usage block and exits 0 (A.U7.19's
  set — `run_unix_port_integration.sh` documents the runner's flags; see Resolved); flags: `--module`, `--wiring-plan`
  (both required), `--host`, `--port`, `--device`, `--fram-state-path`, `--scd30-state-path`, `--mem-backup-state-path`
  (defaults `digital_twin/{fram,scd30,mem_backup}_state.json`; `""` → in-memory), `--config-dir`, `--online-ntp`,
  `--seed`, `--fault`, `--hang`, `--wifi-outcome`, `--duration`, `--gc-threshold`, `--mem-sample-interval-ms`, and the
  `--test-*` flags (M.TWIN.051). `_ensure_dir(path)` (module-top `os`): `os.mkdir(path)`; `except OSError as e: if
  e.errno != errno.EEXIST: raise OSError(e.errno, f"cannot create config dir {path!r}")`.
- **Resolved**: A.U24.46 says the twin runner "reads plans too (U25 adds the call)" to `tests/_generated_tree.py`
  `require_fresh()`; the runner must never import from `tests/` (G7/R02; A.U25.44's path guard fails a launch site with
  `tests` on its path), so the freshness guard is the caller's: every automated launch site already runs from a tree
  `scripts/test.sh`/`run_digital_twin_ci.sh` regenerated, and the in-process twin tests call `require_fresh()` (C2) — the
  runner itself adds no call (G7/R02 settles it; recorded for the OR2.c review). A.U7.19's `--help` set names
  `run_unix_port_integration.sh` and `digital_twin/launch.py`, not this runner; the runner answers `--help` the same way
  because it is the manual entry the README documents (D.10 consistency) — agent decision, OR2.c list.
- **Unit**: U25 (stages: U5 grouping; U8 tag)
- **Depends**: M.TWIN.001, M.TWIN.044, M.TWIN.046, M.TWIN.053
- **Blast carried by**: `tests/test_digital_twin_run_generic_integration.py` parse tests (defaults flip to persistent
  paths; the boot test passes `""` explicitly; grouped config) → M.TWIN.140; automated callers pass `--config-dir` and
  `""` state paths: `tests_scripts/test_digital_twin_generated_boot.py:155-164` → A.U25.32 (TSC),
  `scripts/cross_browser_smoke.mjs:451` → A.U25.32 (SCR), `tests_js/_live_twin_command.js`/`_live_matrix_command.js` →
  A.U24.53 / A.U25.09 (WEB), the CI suite → A.U25.35 (SCR); `scripts/run_unix_port_integration.sh:78` (manual run now
  persists) → A.U25.32 (SCR); README runner flag table → M.TWIN.066
- **Kind**: code

### M.TWIN.049 Runner wiring: chips by `peripheral()`, plan-keyed crossover, fresh faults, polled readiness
- **From**: A.U25.28 (`_collect_chips(plan)` through `machine.peripheral()`; `_wire_uart_crossover(plan)` with
  `initiator_bus`/`responder_bus`, pollers written through the module's public bus global — the `._uart` read goes),
  A.U17.18 (3) (plan keys `initiator_bus`/`responder_bus`; its comment `:265-272`), A.U25.70 (`(OSError, errno.EIO,
  message)`, `match`), A.U25.37 (instance keys, persistent modes, `uart_link:silent` applied after the crossover is
  built), A.U25.27 (wlan `times`), A.U25.15 (`fram:wren`, `fram:silent`), A.U25.42 (`import errno` at the top), A.U25.41
  (`_require_wired` shared — see Change), A.U24.80 Blast (the poller swap unchanged), A.U25.03 (registries), A.U13.R01
  Blast (per-id bus keeps the injected FIFO), A.U20.42 Blast (`getattr(module, "webserver", None)` already), A.U8.20
  (`:257` readiness-poll step → `l2.twin_ready_poll_ms`), A.U20.28 (3) / M_GEN gap 3 (the runner's plan keys are what
  the contract test reads), A.S0930.04 Blast (the crossover wiring is CRC-blind — holds)
- **Site**: `digital_twin/run_generic_integration.py:193-285`
- **Change**: `_collect_chips` is imported from `launch` (M.TWIN.045; this file's copy `:193-222` goes, its two comments
  with it). `_apply_fault`/`_apply_hang`/`_require_wired` are imported from `launch` too (the bodies are identical once
  both read `_collect_chips()`'s keys; the runner's message prefix becomes a parameter `source="run_generic_integration.py"`)
  — one implementation (REF/R05, the A.U25.41 pattern); `uart_link:silent` resolves to the instance's outgoing
  direction through `link.direction_from(machine.peripheral(<that instance's bus>))` and sets `silent = True`, applied
  after `_wire_uart_crossover()`. `_wait_until_built(module, timeout_s=10.0)`: the poll step becomes
  `_READY_POLL_MS = 20` with `# @tunable l2.twin_ready_poll_ms = 20` (A.U8.20's row) and the comment "# webserver is the
  last global build_system() assigns before its setup batch, so faults applied after it reach setup (the CI suite counts
  on that, scripts/_digital_twin_ci_suite.py)". `_wire_uart_crossover(module, plan) -> "UARTLink | None"`: `uart_plan =
  plan.get("uart")`; `a = machine.peripheral(uart_plan["initiator_bus"])`, `b = machine.peripheral(uart_plan[
  "responder_bus"])`; `link, poll_a, poll_b = machine.attach_crossover_jumper(a, b)`; `getattr(module,
  uart_plan["initiator_bus"]).poller = poll_a`, the responder likewise; comment (3 lines): "# Wires the bench's permanent
  crossover jumper between the two generated UART buses once the module has built them; the bounded pollers replace the
  product's public poller from outside, since a real select.poll() over the twin's UART never reports readiness on CI
  runners (CLAUDE.md known hang cause)." The three `assert` lines become one `if a is None or b is None: raise
  RuntimeError("the plan names a UART pair the booted module never constructed")`.
- **Resolved**: A.U25.28 keeps `_collect_chips(plan)` in this file; M.TWIN.045 makes it the shared `launch` helper (one
  copy) — agent decision, OR2.c list (the same reasoning as A.U25.41's `_pop_value`).
- **Unit**: U25
- **Depends**: M.TWIN.035, M.TWIN.045; A.U17.18 (plan keys, U17), A.U20.28 (plan producer)
- **Blast carried by**: `tests/test_digital_twin_run_generic_integration.py` `_collect_chips`/`_require_wired` tests
  (construct twin buses and pass the plan) → M.TWIN.140; `tests_scripts/test_twin_wiring_contract.py` (the runner's key
  reads `initiator_bus`/`responder_bus`, `buses`, `spi`, `pins`) → A.U20.28 (TSC); README `:276-279`, `:288-297` →
  M.TWIN.061
- **Kind**: code

### M.TWIN.050 Runner `main()` and exits: offline NTP, wall clock, passed watchdog, reset exit codes, one shutdown line
- **From**: A.U25.33 (2)-(3) (writes the offline `config_NTP.cfg` before `module.main()` unless `--online-ntp`; prints
  the shim's refused count in the shutdown line), A.U25.71 (installs the wall clock for every loaded `src/` module after
  the import), A.U20.02 (passes `watchdog=machine.WDT(timeout=8000)` to `module.main()`; reads its own WDT, not the
  removed module global), A.U20.06 (the `main()` keywords the runner passes), A.U25.69 / OR126.a (1) (the four
  keywords stay — the runner passes `watchdog`, `cfg_path`, `web_host`, `web_port`), A.U25.09 ((1) configure the
  mem-backup path; (2) `except machine.SimulatedRebootError` → cleanup, `machine reset:` line, WDT line, exit 3/4;
  `main()`'s `finally` tolerates a reset during cleanup), A.U25.36 (2) (the shutdown line prints `mem_backup:
  r0=<4 words>`), A.U25.39 (unwedge calls and comments go; one replacement line), A.U25.41 (`_shutdown_cleanup()`),
  A.U25.32 (`--config-dir` is the `cfg_path`; `_ensure_dir`), A.U25.43 / A.U25.34 (prewarm, then the shim, the first two
  statements of `main()`), A.U25.54 (`SimulatedPowerLoss` flushes FRAM/SCD30, never `mem_backup`), A.U27.01 (the
  runner prints its `Serving forever` or shutdown line — holds), A.U36.513 (`:311-312` comment), A.U24.47 / GAP-H2
  (consumption proof host-side — see M.TWIN.051), A.U8.08 (`WDT(timeout=8000)` tagged), A.U11.10 Blast (the runner boots
  through `main()`, which runs the setups — holds), A.U36.043 (CLAUDE.md/SPEC lists drop `segfault_stress_repro.py` —
  DOCS/SPEC)
- **Site**: `digital_twin/run_generic_integration.py:311-439`
- **Change**: `main(config)`: first `prewarm_poll_set()`, then `patch_asy_udp_socket_for_unix_port()` (their comments
  one line each: "# first: before anything registers a poll object (unix_port_poll_prewarm.py)" / "# second: before any
  UDPSocket exists (tests_scripts/test_twin_entry_point_order.py)"); `configure_fram_state_path`,
  `configure_scd30_state_path`, `configure_mem_backup_state_path` (`""` → `None`); plan read, `configure_wiring(plan)`;
  `random.seed(seed)` when given; `_ensure_dir(config.config_dir)`; unless `config.online_ntp`,
  `write_offline_ntp_config(config.config_dir)`; the start line lists the grouped fields; `module = __import__(config.module)`
  with the comment "# loaded by its run-time name (SPECIFICATION.md F.1 named exception)"; `_wall_clock.install(m for m in sys.modules.values() if
  getattr(m, "time", None) is time)` (comment "# rp2's RTC is the wall clock: an NTP set must move time.time() here too");
  `watchdog = machine.WDT(timeout=8000)` with `# @tunable wdt.timeout_ms = 8000`; `main_task =
  create_task(module.main(watchdog=watchdog, cfg_path=config.config_dir, web_host=config.host, web_port=config.port))`;
  the readiness wait, crossover, chip collection, faults, hangs, wifi outcomes and the instrumentation tasks
  (M.TWIN.051) as today. `_print_wdt_status(config, watchdog)` prints one line `digital_twin/run_generic_integration.py
  [<device>] shutdown: would_have_triggered_count=<n> feed_count=<n> mem_backup: r0=<4 words> public_destinations_refused=<n>`
  (the first two from the runner's own WDT, the third `list(machine.mem_backup(0))`, the fourth from the shim); comment
  (A.U36.513's text): "# Called from main()'s finally and from the KeyboardInterrupt handler: an interrupt landing while
  main() is suspended never enters that finally (F.6)." `main()`'s `finally`: the unwedge call and its two comment blocks
  go; `_print_wdt_status`, cancel the runner tasks, `main_task.cancel()`, `await main_task` under `except
  (asyncio.CancelledError, KeyboardInterrupt, machine.SimulatedRebootError)`, then `_shutdown_cleanup()`. `__main__`:
  `gc.threshold(...)` as today; `try: asyncio.run(main(_config))`; `except KeyboardInterrupt:` → A.U25.39's one line,
  `_shutdown_cleanup()`, `_print_wdt_status`, "interrupted"; `except machine.SimulatedRebootError as e:` →
  `_shutdown_cleanup()`, `machine.flush_mem_backup()`, the line `digital_twin/run_generic_integration.py [<device>]
  machine reset: kind=<reset|bootloader> reset_count=<n> bootloader_count=<n>`, `_print_wdt_status`, `sys.exit(3 if
  reset else 4)` via `_EXIT_SIMULATED_RESET = 3`, `_EXIT_SIMULATED_BOOTLOADER = 4`; `except machine.SimulatedPowerLoss:` →
  `_shutdown_cleanup()` only (no mem-backup flush: a power loss clears it), a `power lost` line, `sys.exit(5)` via
  `_EXIT_SIMULATED_POWER_LOSS = 5`. The runner's WDT reference is a module global `_watchdog` set by `main()` so both
  handlers print it.
- **Resolved**: A.U25.54 says a runner that sees `SimulatedPowerLoss` flushes FRAM/SCD30 but not `mem_backup` and names
  no exit code; a distinct code (5) keeps it apart from a reset for the host (A.U25.09's 3/4 convention extended) —
  agent decision, OR2.c list; the in-process crash-point test (M.TWIN.112) never goes through the runner.
- **Unit**: U25 (after A.U21.06 for the unwedge removal; A.U20.02's keyword in U20 is already present)
- **Depends**: M.TWIN.017, M.TWIN.019, M.TWIN.032, M.TWIN.034, M.TWIN.046, M.TWIN.047, M.TWIN.049, M.TWIN.053
- **Blast carried by**: CI suite exit codes 3/4 (and 5 unused there), the `machine reset:` and shutdown-line fields
  (`mem_backup: r0=`, `public_destinations_refused=`) → A.U25.36, A.U25.33/A.U25.35 (SCR) and their L0 parsers (TSC);
  `tests_scripts/test_digital_twin_generated_boot.py` reset run (`--fault sgp40:writeto:500` exits 3) → A.U25.09 (TSC);
  the generated-`main()` keyword contract → A.U20.28 (3) (TSC; M_GEN gap 3: runner keywords ⊆ `main()`'s);
  README "Automated CI suite" exit codes and "What's here" runner bullet → M.TWIN.064, M.TWIN.058; L2 in-process only
  the handler's pure helpers → M.TWIN.140
- **Kind**: code

### M.TWIN.051 Runner instrumentation: named `--test-*` flags, off by default, unreachable from the product path
- **From**: A.U25.74 (`--test-hold-closing-slot`, `--test-stall-loop-ms N`, `--test-conn-status-interval-ms N`,
  `--test-shutdown-hang <step>`; every rebind reached only under its flag; the L0 guard), A.S0930.27 (4)
  (`--test-shutdown-hang` steps S1-S6 and what each rebinds; the `HANG <step>` line), A.S0930.38 / OR126.a (3) (reboot and
  bootloader run the controlled sequence — the same steps apply to them), A.U31.06 (1) (`--test-loop-lag-ms N`,
  `LOOP_LAG max_us= p99_us= samples=` every 5 s), A.U35.31 (2) (`--test-watchdog-fault
  {supervisor-raise,main-exit,block}` and the `WDT_AT_FAULT <feed_count>` line), A.U24.47 / GAP-H2 of M_TEST_HELP (the
  host-side bus-fault scenario reads "the twin's fault counter through the harness's status channel" — no action names
  the channel: closed here by `--test-fault-status-interval-ms N`), OR125.a (1)-(3), G7/R01 (the runner is the stated
  exception), G7/R19, OR36 (no product hook)
- **Site**: `digital_twin/run_generic_integration.py` — `parse_args()`, a new `TestFlags` namedtuple, a new section
  "test-only instrumentation" after `_wire_log_clearer()`, `main()` after `_wire_uart_crossover()`
- **Change**: `TestFlags = namedtuple("TestFlags", ("hold_closing_slot", "stall_loop_ms", "conn_status_interval_ms",
  "fault_status_interval_ms", "shutdown_hang", "loop_lag_ms", "watchdog_fault"))` with `_NO_TEST_FLAGS = TestFlags(False,
  None, None, None, None, None, None)` — every flag off by default; section comment (3 lines): "# Test-only
  instrumentation (owner, 2026-09-30): the runner, never src/ or the image, may rebind a booted object from outside or
  print internal state when a named --test-* flag asks; tests_scripts/test_twin_runner_test_flags.py keeps every one off
  by default and out of the production entry path." Each flag's code is one function, called from `main()` only inside
  `if config.instrumentation.<field>:` — `_test_hold_closing_slot(module)` (rebinds `module.webserver._close_writer` to
  wait on a runner event, prints `SLOT_HELD`/`SLOT_RELEASED`; released by `--test-hold-closing-slot`'s companion: the
  host closes the held socket); `_test_stall_loop(ms)` (one task that, on each `STALL_TRIGGER` read from the runner's
  stdin, blocks with `time.sleep_ms(ms)` and prints `STALL`); `_test_conn_status(module, ms)` (prints `CONN_SLOTS
  open=<n> backlog=<n>` from `webserver._open_conns.get_value()`/`_backlog` every `ms`); `_test_fault_status(chips, ms)`
  (prints `FAULT_PENDING <key>:<op>=<n> …` for every chip injector op with a queued entry, via `fault.pending(op)`, every
  `ms` — the host reads consumption before its GET); `_test_shutdown_hang(module, step)` with `step` in
  `S1|S2|S3|S4|S5reset|S5erase|S6`: S1 rebinds `module.sysfunct._log_dead_task` to a coroutine that never returns and
  ends one supervised task; S2 a config store's `flush_pending`; S3 holds one FRAM chunk's `_op_lock` from a runner task;
  S4 starts a supervised-task stand-in that swallows `CancelledError`; S5reset holds a store's `_config_lock`; S5erase
  rebinds the FRAM driver's `report_set_values` and sets the twin chip's `drop_next_wren = 1` (so pass 2 reaches it);
  S6 replaces `sysfunct._reset_timer` with a twin `Timer` whose callback never fires — each prints `HANG <step>` when
  armed; `_test_loop_lag(ms)` (A.U31.06's probe and line); `_test_watchdog_fault(module, kind, main_task)` (after the
  first supervisor feed, observed as `watchdog.feed_count >= 1`: `supervisor-raise` rebinds `sysfunct._log_dead_task` to
  raise and ends one task, `main-exit` cancels `main_task` while the runner loop stays alive, `block` runs one blocking
  `time.sleep(9)` in a runner task; each prints `WDT_AT_FAULT <feed_count>`). Parsing: `--test-hold-closing-slot`
  (bool), `--test-stall-loop-ms N`, `--test-conn-status-interval-ms N`, `--test-fault-status-interval-ms N`,
  `--test-shutdown-hang STEP` (validated against the seven names), `--test-loop-lag-ms N`, `--test-watchdog-fault KIND`.
  Every rebinding comment names the product object and why it is the one the step waits on (≤ 3 lines each). Nothing
  under `src/`, no generated module and no frozen module references a `--test-` name, this file or `digital_twin/`.
- **Resolved**: AC_NOTES 33/36: OR125 settles U25 Q2 as (a); A.U25.74 owns the flag list and its L0 check, and
  A.S0930.27/A.U31.06/A.U35.31 each add their flag to that one table — merged into one section here. The consumption
  channel for the moved bus-fault scenario is unnamed in A.U24.47/A.U25.46 ("the harness's status channel"); a named
  flag of A.U25.74's kind serves it (OR125.a (2)) — agent decision, OR2.c list. The rebinds touch private product names
  (`_log_dead_task`, `_op_lock`, `_config_lock`, `_reset_timer`, `_close_writer`): G7/R01's runner-only exception
  (OR125.a (1)) covers exactly these, under their flags; A.U25.28's "reads no private product attribute" applies to the
  runner's ordinary path, which keeps none.
- **Unit**: U25 (A.S0930.27's step list co-lands per AC_NOTES 36; A.U31.06 and A.U35.31 add their flag in U31/U35 to
  this section)
- **Depends**: M.TWIN.047, M.TWIN.050; M.SRC_CORE names (`_log_dead_task`, `_reset_timer`, `_config_lock`, `_op_lock`,
  `flush_pending`, `report_set_values`)
- **Blast carried by**: L0 `tests_scripts/test_twin_runner_test_flags.py` (each flag's default off, every rebind under its
  flag's `if`, no `--test-` name in `src/`/generated/frozen, a bite fixture; table gains `--test-fault-status-interval-ms`)
  → A.U25.74 (TSC, gap: the new flag); the host harness that drives these flags (`scripts/_digital_twin_scenarios.py`) →
  A.U25.46, A.S0930.27, A.U31.06, A.U35.31 (SCR); README flag table "test-only instrumentation (owner, 2026-09-30)" →
  M.TWIN.066; SPEC E.9 runner-only exception names the flags → A.U25.74 / A.U31.06 (SPEC)
- **Kind**: code

### M.TWIN.052 Soak sampler and wire-log clearer: tagged, tick-stamped, kept or trimmed by B3's measurement
- **From**: A.U35.25 (the sampler kept only if a 4× sparser interval gives Run 11 the same verdict; else its
  `gc.collect()` goes), A.U35.26 (`MEM_SAMPLE` timestamp `time.time()` → `time.ticks_ms()`, diagnostics only), A.U30.16 /
  A.U30.17 (the sampler's `gc.collect()` is an allow-listed instrumentation site while kept), A.U0.54 (`:302` "unbounded
  by design" → "unbounded (agent, 2026-09-14)"), A.U8.20 (`_WIRE_LOG_CLEAR_INTERVAL_MS = 5000` tagged
  `l2.twin_wire_log_clear_interval_ms`), A.U25.22 (the link's `wire_log` stays unbounded and the clearer stays: nothing
  reads it in the runner — see Resolved)
- **Site**: `digital_twin/run_generic_integration.py:288-308`
- **Change**: `_mem_sampler(interval_ms)`: prints `MEM_SAMPLE {time.ticks_ms()} {gc.mem_free()}`; its `gc.collect()`
  stays with the 3-line comment "Optional (--mem-sample-interval-ms): gc.mem_free() lives in this heap with no REST
  route; the collection is the one allow-listed instrumentation site (tests_scripts/test_gc_collect_sites.py), kept
  while B3 shows the sparser interval gives Run 11 the same verdict." — if B3's measurement (A.U35.25) differs, the
  `gc.collect()` line goes and the comment's last clause with it (decided at execution, recorded in `timing.md`).
  `_WIRE_LOG_CLEAR_INTERVAL_MS = 5000` with `# @tunable l2.twin_wire_log_clear_interval_ms = 5000`. `_wire_log_clearer`
  comment → "# UARTLink.wire_log is unbounded (agent, 2026-09-14) and nothing in this process reads it, so it grows with
  link traffic unless cleared - the growth Run 11's trend check caught for dev (README "Run 11's two calibrated
  numbers")." (3 lines).
- **Resolved**: A.U25.22 caps the twin's bookkeeping "or clears it by its owner"; `wire_log` keeps the second form (the
  runner clears it), so G7/R21 holds without a cap.
- **Unit**: U35 (stage U25 for the comment and tag lands earlier: U0 for A.U0.54's tag, U8 for the tag, U35 for the
  sampler's verdict and the ticks stamp)
- **Depends**: A.U35.27 (planted leak), A.U27.17 (Run 11 rewrite)
- **Blast carried by**: `scripts/_digital_twin_ci_suite.py` `_parse_mem_samples()` by log offset → A.U35.26 (SCR) and its
  L0 cases (TSC); `tests_scripts/test_gc_collect_sites.py` allow-list row → A.U30.16 (TSC); README sampler reasoning and
  Run 11 paragraph → M.TWIN.065
- **Kind**: code

## digital_twin/unixport/_offline_ntp_config.py (new)

### M.TWIN.053 One offline-NTP config writer both tiers import
- **From**: A.U25.33 (2) (`write_offline_ntp_config(cfg_dir)` writes `config_NTP.cfg` only when absent), A.U18.10 (the
  `DNSFallback` key), A.U10.40 (`NTP_Host` → `NTPHost`), GAP-H3 of M_TEST_HELP (one implementation; born in
  `tests/_generated_module.py` at U20, "the twin runner imports it (or TWIN moves that one function to an import-safe
  module both tiers reach)")
- **Site**: new `digital_twin/unixport/_offline_ntp_config.py`
- **Change**: header (≤ 3 lines) "Writes the offline NTP config a twin or Unix-port boot starts from, so no run reaches a
  public NTP or DNS host: TEST-NET-1 (RFC 5737) as the NTP host and no DNS fallback." `def
  write_offline_ntp_config(cfg_dir: str) -> None` — writes `{"NTPHost": "192.0.2.1", "DNSFallback": ""}` (the product's
  flat JSON config format) to `<cfg_dir>/config_NTP.cfg` only when that file is absent (an existing file is the run's own
  state). Imports only `json` and `os` (no `machine`, no `tests/`).
- **Resolved**: GAP-H3: the runner may not import `tests/` (G7/R02, A.U25.44's guard), so the function moves at U25 from
  `tests/_generated_module.py` (M.TEST_HELP.047, U20) to this import-safe module in A.U18.12's fake-free directory, which
  L1 boots already put on `sys.path` for the UDP shim; `tests/_generated_module.py` then imports it — TEST_HELP gap.
- **Unit**: U25
- **Depends**: M.TWIN.017 (the directory), A.U10.40
- **Blast carried by**: the runner → M.TWIN.050; `tests/_generated_module.py` drops its copy and imports this →
  TEST_HELP gap (GAP-H3's resolution); the in-process twin boot helpers (C4) import it → M.TWIN.100-164; ruff/mypy scope
  by directory
- **Kind**: code

## digital_twin/run_device_script.py (new)

### M.TWIN.054 Device-script runner: the plan, a recording watchdog, the GC stage, the script unchanged
- **From**: A.U26.05 (1) (`run_device_script.py <wiring-plan.json> <script.py> [--gc-threshold N]`: `configure_wiring`,
  the recording `machine.WDT(timeout=8000)` as `Board.run_isolated()` arms it, `gc.threshold(N)` default -1, `exec` of
  the script in a fresh `__main__`-like dict, exit with the script's status), A.U35.49 (runs every instrument at both GC
  stages), A.U30.18 (3) Blast (the C-stack device script builds `dev` through this route — holds), A.U25.43 / A.U25.34
  (a `main()` in `digital_twin/` that can boot a device prewarms, then shims, first), A.U25.33 (3) (the shim's
  public-destination guard covers every Unix-port run), A.U8.08 (`wdt.timeout_ms` site), A.U10.30 (F.1's named `exec`
  exception), C5
- **Site**: new `digital_twin/run_device_script.py`
- **Change**: header (≤ 3 lines): "Runs one tests_hardware device script unchanged under the twin, as Board.run_isolated()
  runs it on silicon: the device's wiring plan, the one armed watchdog, the requested GC stage. Every instrument passes
  here before the hardware queue (scripts/record_twin_instrument_runs.py)." `main(argv) -> int`: first
  `prewarm_poll_set()`, then `patch_asy_udp_socket_for_unix_port()` (the A.U25.43/A.U25.34 order); parse `<plan>
  <script> [--gc-threshold N]` (hand-rolled with `launch._pop_value`; `-h`/`--help` prints usage, exits 0);
  `machine.configure_wiring(json.load(plan))`; `machine.WDT(timeout=8000)` with `# @tunable wdt.timeout_ms = 8000`
  (comment "# armed before the script runs, as Board.run_isolated() does; a script constructing WDT again gets this one
  (ports/rp2/machine_wdt.c:43-57)"); `gc.threshold(n)` (default -1, the reactive stage); `exec(compile(source, path,
  "exec"), {"__name__": "__main__", "__file__": path})` with the comment "# SPECIFICATION.md F.1 named exception: a test
  file executed by path"; a `SystemExit` from the script returns its code; any other exception prints its traceback and
  returns 1; `machine.SimulatedRebootError` returns 3/4 (the runner's codes) after printing the `machine reset:` line.
  `__main__`: `sys.exit(main(sys.argv[1:]))`. No `tests/` import; no instrumentation flag (the script is the
  instrument).
- **Resolved**: A.U26.05 lists the binary's `MICROPYPATH` as `digital_twin:build/generated_src:src:ext`; the shim's new
  directory (M.TWIN.017) joins it in `tests_hardware/twin_board.py` — HW_BENCH gap.
- **Unit**: U26 (A.U26.05; the prewarm/shim lines need M.TWIN.017's U25 move, which precedes it)
- **Depends**: M.TWIN.017, M.TWIN.022, M.TWIN.031, M.TWIN.044 (`_pop_value`)
- **Blast carried by**: `tests_hardware/twin_board.py` (spawns it; `MICROPYPATH` + `digital_twin/unixport`),
  `tests_hardware/conftest.py --twin`, `scripts/record_twin_instrument_runs.py`, `tests_hardware/twin_record.json`, L0
  `tests_scripts/test_twin_record.py`/`test_twin_board.py` → A.U26.05, A.U35.49 (HW_BENCH, SCR, TSC); the
  `runner_sha256` covers this file → A.U26.05; README "Running device scripts in the twin" → M.TWIN.074; ruff/mypy scope by
  directory; the twin mypy pass's `files` list → M.TWIN.075
- **Kind**: code

## digital_twin/segfault_stress_repro.py (deleted)

### M.TWIN.055 Retire the segfault stress tool
- **From**: A.U25.40 (delete; README `:80`, `:128`, `:886-906` mentions; `typecheck.ini:9`; `pyproject.toml:383`),
  A.U30.15 (its `:92` `gc.collect()` — goes with the file), A.U36.043 (CLAUDE.md `:525-526` and SPEC `:1447` lists drop
  it — DOCS/SPEC), A.SDEP.16 (W12: "deleted by A.U25.40 in any case"), A.U25.28 (its private-attribute reads — gone with
  it); dropped with the file: A.U8.20's `l2.twin_ready_poll_ms` site `:24`, A.U20.02's caller entry, A.U20.42's `:23`
  `getattr` adaptation, A.U19.20's `:18` endpoint tuple (U25 conflicts table rows 3 and 1 — settled by A.U25.40's own
  Blast: "A.U8.20's tag … and A.U20.02's caller entry disappear")
- **Site**: `digital_twin/segfault_stress_repro.py` (whole file)
- **Change**: `git rm digital_twin/segfault_stress_repro.py`; README edits → M.TWIN.058/.073; `typecheck.ini` → M.TWIN.075;
  `pyproject.toml:383` exclude line → A.U25.40 (TOOL).
- **Resolved**: the earlier units that edit it (A.U8.20 in U8, A.U19.20, A.U20.02, A.U20.42 in U19-U20) run before U25:
  each edits the file in its own unit (the file still exists then and must keep passing lint/typecheck) and the U25
  deletion removes the result — staged, no conflict; A.U8.20's Part N row drops this site at U25 (SPEC).
- **Unit**: U25
- **Depends**: M.TWIN.057 (the modselect account's new home)
- **Blast carried by**: `pyproject.toml:383` → A.U25.40 (TOOL); CLAUDE.md/SPEC lists → A.U36.043 (DOCS, SPEC); SPEC
  `:4622` A33 tag → A.U25.40 / U36 (SPEC)
- **Kind**: code

## digital_twin/unix_port_gc_unwedge.py (deleted)

### M.TWIN.056 Retire the heap-unwedge helper after the SIGINT-override proof
- **From**: A.U25.39 (delete the module and its test; remove the import and the three calls with their comments),
  A.SDEP.11 (re-check of the override at the new tag; the helper's retirement stays A.U25.39's after A.U21.06), A.U36.037
  (SPEC F.6 keeps the mechanism and the `gc.collect()` recovery; B.14.1 and CLAUDE.md record the retirement — SPEC/DOCS),
  A.U30.16 (its allow-list row exists only until A.U25.39 lands — TSC)
- **Site**: `digital_twin/unix_port_gc_unwedge.py` (whole file)
- **Change**: `git rm`; call sites → M.TWIN.046 (`launch.py`), M.TWIN.050 (runner); test file → M.TWIN.162; README
  `:89-101` bullet → M.TWIN.058.
- **Resolved**: —
- **Unit**: U25, after A.U21.06 (A.U25.39's Depends)
- **Depends**: A.U21.06
- **Blast carried by**: SPEC F.6/B.14.1, CLAUDE.md `:665-680` → A.U36.037 (SPEC, DOCS); `tests_scripts/test_gc_collect_sites.py`
  row → A.U30.16 (TSC)
- **Kind**: code

## digital_twin/unix_port_poll_prewarm.py

### M.TWIN.057 Poll-set prewarm: the stated limitation, a margin from the TOMLs, no explicit Any
- **From**: A.U25.43 (3) (the `_DEFAULT_CEILING` comment states the margin against the highest in-process concurrency,
  re-derived once A.U25.46 moves the load host-side; L0 `3 × max_connections < 512`), A.U25.43 (4) (the modselect account
  is the prewarm bullet's; "a known limitation, not reported upstream (owner, 2026-09-29)"), A.U25.63 / A.U28.28 (8)
  (returns `object`; the `noqa: ANN401` goes), A.SDEP.08 / A.SDEP.16 (W12: the `modselect.c` growth path re-read at the
  new tag; fixed → the module and its 15 call files go — conditional delta), A.SDEP.15 (W11: `import asyncio.core`'s
  `import-not-found` ignore self-checking), A.U24.70 (its scan band `17400-17463` is a fixed row of `tests/_port_bands.py`
  — the file unchanged), A.U24.08 (cites `:7` as the `asyncio.core` precedent — holds), A.U14.28 (SPEC F.7 row 12 —
  SPEC), A.U36.040 (SPEC F home of the fact — SPEC), A.U27.28 (header over the cap)
- **Site**: `digital_twin/unix_port_poll_prewarm.py:1-2, 4-7, 16-21, 48-50`
- **Change**: header → "Workaround for the Unix port's extmod/modselect.c pollfds growth, which corrupts poll objects
  registered over non-fd streams (rp2-immune: compiled out there): grow asyncio's poll set once, before anything
  registers. A known limitation, not reported upstream (owner, 2026-09-29); SPECIFICATION.md F.7 states it." (3 lines);
  the `:4-6` comment → "# asyncio.core is private: reaching its _io_queue is the point (the stubs cover only the public
  API)." (1 line; the `type: ignore[import-not-found]` stays, self-checking under `warn_unused_ignores`). `TYPE_CHECKING`
  block and `Any` go: `_bind_free_listener(...) -> "tuple[socket.socket, object]"`, `prewarm_poll_set(...) -> object`
  (comment "# returns the packed sockaddr it bound (a bytes object on the Unix port)"), the `noqa` goes. `_DEFAULT_CEILING
  = 512` comment → "# A raised threshold, not a fix: well above 3 x the largest max_connections of any devices/*.toml
  (the peak accepted sockets of any tier; tests_scripts/test_twin_entry_point_order.py checks it); ~45 ms at startup."
  (the "every device's max_connections is 6" and the scenario-file reference go). The port-band comment `:23-25` keeps
  its reason and gains "(a fixed row of tests/_port_bands.py)".
- **Resolved**: A.U25.43 (3) says the margin is re-derived after A.U25.46; the host-driven load still lands in the twin
  process (its accepted sockets register here), bounded by the product's own ceiling and backlog, so `3 ×
  max_connections` remains the bound — the comment states that rule, not a number.
- **Unit**: U25
- **Depends**: A.U25.46 (the in-process load leaves), A.U24.70 (port band row)
- **Blast carried by**: L0 entry-order and margin checks → A.U25.43 (TSC, `tests_scripts/test_twin_entry_point_order.py`);
  `tests/test_digital_twin_poll_prewarm.py` (canonical trailer, prewarm return type) → M.TWIN.134; README prewarm bullet
  (with the modselect account) → M.TWIN.058; SPEC F.7 row → A.U14.28 / A.U36.040 (SPEC)
- **Kind**: code

## digital_twin/typecheck.ini

### M.TWIN.075 Twin mypy pass: its own file list, coded ignores, the Any baseline that empties, the shim's path
- **From**: A.U27.23 (1) (`files = digital_twin, tests/test_digital_twin_*.py, tests/_webserver_concurrency_scenarios.py,
  tests/_digital_twin_construction_scenarios.py`; "a file A.U25.46/A.U24.65 retires leaves the list with it"), A.U27.22
  (`enable_error_code = ignore-without-code` with its comment line), A.U8.24 (`disallow_any_explicit = True` plus
  `[mypy-<module>]` baseline sections at U8's end), A.U34.11 / A.U37.02 (the baseline sections empty and go), A.U25.40
  (`:9` drops `segfault_stress_repro.py`), A.U18.12 (`mypy_path` gains the shim's directory), A.U25.63 (the twin's
  modules leave the baseline as their `Any` clears in U25), A.U11.05 Blast ("`digital_twin/typecheck.ini`'s pass needs the
  same names" — `mem_backup`/`reset_cause` exist in the twin, M.TWIN.032), C5
- **Site**: `digital_twin/typecheck.ini:1-28`
- **Change**: header comment block `:1-10` → three blocks of ≤ 3 lines: "# mypy config for the twin pass scripts/typecheck.sh
  runs beside the main one: mypy resolves each bare module name to one file per run, and the twin needs machine/network/
  neopixel to mean its own fakes (SPECIFICATION.md B.15)." / "# digital_twin first so the twin's modules win; its
  unixport/ subdirectory for the UDP shim and the offline-NTP writer; build/generated_src for the runner's device import
  (typecheck.sh generates it first)." (the "Confirmed empirically" block keeps its 2 lines). `[mypy]`: `mypy_path =
  digital_twin:digital_twin/unixport:src:build/generated_src:typings:tests`; `files = digital_twin, tests/test_digital_
  twin_*.py, tests/_digital_twin_construction_scenarios.py` (`tests/_webserver_concurrency_scenarios.py` is retired by
  A.U25.46 in U25, so it leaves the list there; the twelve per-device wrappers go with A.U25.46 — the glob no longer
  matches them); `enable_error_code = ignore-without-code` with "# a bare `# type: ignore` is itself an error, so no
  suppression hides its code"; `disallow_any_explicit = True` from U8's end, its `[mypy-<module>]` baseline sections
  listing the twin modules with findings then (comment as A.U8.24), each section removed in the unit that clears it —
  `machine`, `run_generic_integration`, `_http_client`, `launch`, `network`, `unix_port_poll_prewarm` in U25 (A.U25.63);
  none left at U34 (A.U34.11).
- **Resolved**: A.U27.23 (U27) writes the file list after U25 has already retired `_webserver_concurrency_scenarios.py` —
  its own rule ("a file A.U25.46/A.U24.65 retires leaves the list with it") gives the end state without it.
- **Unit**: U27 (stages: U8 the flag and baseline; U25 the baseline sections it clears, `:9`, `mypy_path`; U34 the empty
  baseline's removal)
- **Depends**: M.TWIN.017, M.TWIN.053
- **Blast carried by**: `scripts/typecheck.sh:118` becomes `mypy --config-file digital_twin/typecheck.ini` → A.U27.23
  (SCR); `tests_scripts/test_mypy_any_baseline.py` reads the sections → A.U8.24 / A.U34.11 (TSC); `pyproject.toml`
  main pass: `:383` exclude goes (A.U25.40), `mypy_path` += `digital_twin/unixport` (A.U18.12) → TOOL
- **Kind**: rule
