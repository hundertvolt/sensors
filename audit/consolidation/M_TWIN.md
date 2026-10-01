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
- **Blast carried by**: both runners insert `digital_twin/unixport` into `sys.path` and call the patch after the prewarm
  → M.TWIN.049, M.TWIN.044 (`launch.py` boots no product UDP but follows the one rule, see M.TWIN.044); every twin test
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
