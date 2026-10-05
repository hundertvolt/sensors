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
  A.U24.78); a generated module loaded by name only at a site SPEC F.1 names (A.U10.30's `load_generated()` dropped,
  OR141.a (2), OR142.a (3); A-C review fold): the in-process twin files call `load_device(device)` of
  `tests/_digital_twin_construction_scenarios.py`, that named file's existing `__import__(f"sensortask_{device}")` line
  (`:98`) held in one public function of the same file, the dynamic import itself unchanged — whether importing the
  library from another twin file repeats its module-level prewarm and shim calls (each must be idempotent or skipped) is
  decided at execution, with its reason recorded; then `tests/_generated_tree.py` `require_fresh()` (A.U24.46); the device set from `tests/_twin_devices.py`
  (`generated_devices()`, `wiring_plan(device)`, `device_with(*drivers)`, `devices_with_shared_bus()` — M.TEST_HELP.055
  as amended in the gap pass; A.U25.25 /
  A.U25.48, the one helper A.U24.65 also uses); catalog codes `code("E"|"W", <NAME>)` from `tests/_error_codes.py` (A.U2.03, M.TEST_HELP.045).
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

### M.TWIN.001 One twin helper module: bounded log, counter cap, buffer fill, walk, the two config groupings
- **From**: A.U25.22 (`_BoundedLog` in a new `_bounded_log.py`), A.U25.23 (`COUNTER_CAP` there), A.U25.06 (a `_fill`
  helper "in each file" — `machine.py` and `_fram_chip.py`), A.U5.15 (shared twin types `StatePaths(fram, scd30)`, `Injections(seed, faults, hangs, wifi_outcomes)`, `Walk(lo, hi,
  step)`, home unnamed), A.U25.36 / A.U25.09 (the mem-backup state path joins the state group — M.TWIN.044)
- **Site**: new `digital_twin/_twin_common.py`
- **Change**: one module, importing nothing from `digital_twin/` or `src/` (so `network.py`, `neopixel.py` and every
  chip fake import it without `machine`): header (≤ 3 lines) "Shared twin helpers: the bounded bookkeeping log, the
  saturating counter cap, the buffer fill every fake read uses, the value-walk bounds and the two runner config groups." Contents: `COUNTER_CAP =
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
  datasheet-derived (a plausibility bound)"; `StatePaths = namedtuple("StatePaths", ("fram", "scd30", "mem_backup"))`
  ("persistent state files; None keeps a chip in memory only") and `Injections = namedtuple("Injections", ("seed",
  "faults", "hangs", "wifi_outcomes"))` ("everything a run arms before boot"), shared by `launch.py` and the runner
  (M.TWIN.044, M.TWIN.047).
- **Resolved**: A.U25.06 asks for one fill helper per file while REF/R05 / OR24 ask for one material; a shared module the
  chip fakes may import without `machine` (A.U25.22's own reason for a helper module) satisfies both, so the two copies
  become one; `_bounded_log.py` (A.U25.22/.23) takes the wider name because it now holds four helpers; `_BoundedLog`
  becomes `BoundedLog` because another module imports it (G10/R07 private-by-default covers only names nobody else reads)
  — agent decisions, OR2.c list.
- **Unit**: U25 (stage U5: A.U5.15 creates the module holding `Walk`, `StatePaths(fram, scd30)` and `Injections`;
  U25 adds the rest and the third `StatePaths` field)
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
  A.U13.03, A.U2.09, A.U24.22 (Blasts: "no codes" / "sees no traffic" / independent — hold), A.U3.04 dropped (OR140.a
  (7); its Blast held here, nothing changes; A-C review fold); A.U35.28 (3)
  (the chip's write count read at exit; "an exit line field if absent" — M_SCR gap 4, gap pass G3)
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
  Payload-write bookkeeping (twin-only test surface, both listed in `TEST_API`): a WRITE whose data phase reached the
  array (not when `silent`, not when WEL was clear) and carried more than one data byte — a chunk copy, a clear or an
  erase unit, never a one-byte status write — steps `write_count: int = 0` through `saturating_add()` and
  `writes_at: dict[int, int]` at its start address (the copy's block address). `writes_at` holds at most
  `_WRITES_AT_MAX_KEYS = 2048` keys (an erase's 256-byte units plus every chunk's two block addresses fit); a write at a
  new address past the cap steps `writes_at_dropped` instead, so the bookkeeping never grows without bound
  (A.U25.22's rule). Per-logger attribution is the runner's (M.TWIN.050): the chip knows addresses, not owners.
- **Resolved**: A.U25.32's Site cites `_fram_chip.py:285-322`, past the file's end (157 lines); the code it means is
  `_load_state()` `:57-94` (read at HEAD) — line fix, no substance change. A.U25.06's local `_fill` is M.TWIN.001's
  shared `fill_buffer()`.
- **Unit**: U25 (stage U35: `write_count`/`writes_at` with A.U35.28; per-logger attribution by lead direction, gap pass G3)
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
- **Change**: header (≤ 3 lines) "The twin's wall clock: the built-in time module plus an offset that
  RTC().datetime(set) and the twin-only step() move, as an RTC set moves time.time()/gmtime() on rp2
  (ports/rp2/modtime.c:31-43, machine_rtc.c:65-95, v1.29.0). Ticks never step." Contents: `import time as _time`; `class
  WallClock` with `offset_s = 0`; `time()` → `_time.time() + self.offset_s`; `gmtime(t=None)` / `localtime(t=None)` →
  the built-in on `t` when given, else on `self.time()`; every other attribute (`mktime`, `ticks_ms/us/diff/add`,
  `sleep`, `sleep_ms`, `sleep_us`, `time_ns` when present) delegates through `__getattr__` to the built-in (MicroPython
  supports module-style `__getattr__` on a class instance); `set_wall(epoch_s)` sets `offset_s = epoch_s -
  _time.time()`; `step(seconds)` — "twin-only test knob" — adds to `offset_s`; `TEST_API = ("step",)`. Module state:
  `_clock: WallClock | None = None`; `install(modules) -> WallClock` creates the one clock on first call and rebinds the
  `time` global of each given module object whose `time` is the built-in module (a module already rebound is skipped;
  idempotent), comment "# Bound from outside, as every test adapts a product seam: src/ stays unchanged." (OR36, A-C3
  O-15); `installed() -> WallClock | None`. Every value is an `int` epoch second (the rp2 port's `time.time()` is
  integral).
- **Resolved**: —
- **Unit**: U25
- **Depends**: M.TWIN.033 [follows] (its RTC reads `installed()`); the two land in one U25 commit (A-C2)
- **Blast carried by**: `machine.RTC` → M.TWIN.033; the runner installs it for every loaded `src/` module after the
  device import (walk `sys.modules`) → M.TWIN.050; the L2 clock-jump halves A.U10.28 and A.U18.26 leave "pending U25"
  (A.U25.71 names their use of `step()` but no action writes them — a gap closed here) → new
  `tests/test_digital_twin_clock_jump.py`, M.TWIN.146; new L2 cases in
  `tests/test_digital_twin_machine.py` (an installed clock: `RTC().datetime(set)` moves `time.time()` of a rebound
  module to the set second ± 1, ticks unchanged; `step(3600)` moves `gmtime()` by an hour; an uninstalled `RTC()` keeps
  the stored tuple) → M.TWIN.128; fidelity table RTC row "fixed (installed by the runner)", `ticks_ms()` row stays →
  M.TWIN.059; README "What's here" bullet → M.TWIN.058; ruff/mypy pick it up by directory
- **Kind**: code

## digital_twin/_flash_stall.py (new)

### M.TWIN.170 The twin's flash-write stall: a config flush holds the loop for the datasheet time, interrupts off
- **From**: OR141.a (4) (g) (concurrent load "with the twin's flash write stalling the loop for the datasheet time"),
  FOLD_BRIEF F25 (U25) — A-C review fold.
- **Site**: new `digital_twin/_flash_stall.py`.
- **Change**: header (≤ 3 lines) "Models a flash write on the twin: rp2 programs its flash with interrupts off
  (ports/rp2/rp2_flash.c:170-174, v1.29.0), so a config flush holds the whole loop for the chip's erase and program
  time; installed from outside src/, as _wall_clock.py is." `install(module) -> None` rebinds the `open` the config
  manager module uses (applied from outside, no product hook, OR36) to a wrapper whose write-mode file, on `close()`,
  busy-waits on `time.ticks_us()` for one sector erase plus one page program per 256 bytes written — W25Q16JV tSE 45 ms
  typical / 400 ms max, tPP 0.4 ms / 3 ms (`datasheets/pico w/Winbond_W25Q16JV_Datasheet_RevF.pdf`, the AC timing
  table; each value cited on its line) — and marks the twin's interrupts off for that time, so the modelled UART RX
  interrupt does not run while the DMA does (M.TWIN.169). Knob `use_max = False` ("twin-only test knob": the maxima).
  `stalls` and `stalled_ms` (saturating, `_twin_common.saturating_add`) record what ran. One sector per write is an
  approximation of littlefs's erase pattern, stated in the fidelity table. The runner installs it on every boot
  (typical times; a runner flag selects the maxima, its name decided at execution with the `--test-*` family, M.TWIN.051);
  an in-process L2 test installs it where it needs the stall.
- **Resolved**: —
- **Unit**: U25.
- **Depends**: M.TWIN.001 (`saturating_add`), M.TWIN.169 (the interrupts-off flag the model reads).
- **Blast carried by**: the runner's install → M.TWIN.171; the stall cases → M.TWIN.130; the concurrent-load scenario →
  M.TWIN.171 and M.SCR.018; fidelity row → M.TWIN.059; README "What's here" bullet → M.TWIN.058.
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
  A-C2 step order: A.U14.17's part lands in U13 (A.U14.17 (a)'s code half lands with A.U13.R01 in U13 (M.SRC_SENS.008/.009: the boot clear is called from I2C.__init__ there, so every fake and the generated call move with it)).
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
  A-C2 step order: A.U17.25's part lands in U25, not U17 (it follows A.U17.25's own change, which lands in U25).
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
  A-C2 step order: A.U10.28's part lands in U16, not U10 (it follows A.U10.28's own change, which lands in U16).
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

## digital_twin/rp2.py (new)

### M.TWIN.169 The twin's time-driven DMA and UART register model, so dev's twin boots on the DMA receive path
- **From**: OR141.a (4) (a)-(d), (g) (the receive path through a DREQ-paced DMA ring; the twin fakes carry the same
  time-driven model as the unit fakes), FOLD_BRIEF F25 (the twin fakes land in U13 with the driver, so dev's twin boots)
  — A-C review fold.
- **Site**: new `digital_twin/rp2.py` (the `rp2.DMA` fake) and `digital_twin/machine.py` (the UART register block behind
  `mem32`, the modelled RX interrupt, `rx_api_calls`).
- **Change**: the same model M.TEST_HELP.069 states for the unit tier, on the twin's own classes and independent of
  `tests/` (the twin imports nothing from it, G7/R02): `rp2.DMA` with `config()`, `pack_ctrl()` (the fields the driver
  sets), `count` (TRANS_COUNT), `active()`, `close()`, the chained reload, the ring wrap on the write address, the
  natural-alignment refusal and an RP2040-E12 stale `WRITE_ADDR`; the paced channel takes bytes from the UART's RX FIFO
  (the twin link's delivered bytes, M.TWIN.027) at the DREQ pace, computed from the twin's monotonic clock at each
  register read, so a stalled loop (M.TWIN.170) does not stop it. The UART register block (UARTRSR, UARTIMSC, UARTDMACR at
  `0x40034000`/`0x40038000`, RP2040 datasheet 4.2.8): RXIM/RTIM set by every construction and `init()`
  (`machine_uart.c:455`); while set, a modelled RX interrupt drains the FIFO into rxbuf (`:162-188`) — and it does not run
  inside a twin flash stall (interrupts off), so a FIFO the DMA does not drain overflows there and sets UARTRSR OE after
  32 bytes (`machine_uart.c:90`); RXDMAE gates the DREQ. `rx_api_calls` counts receive-side `any()`/`read()`/`readinto()`/
  `readline()`/poll. Each modelled rp2 fact cites its v1.29.0 line and is pinned by M.TWIN.138 (C6); every knob says
  "twin-only test knob" and joins `TEST_API`. `rp2.DMA` has a finaliser that aborts the channel, as `rp2_dma.c:365, 637-673`
  (a soft reset in the twin is a process exit, so the finaliser is modelled for fidelity only and says so in the
  fidelity table). Lands on HEAD's twin UART in U13; M.TWIN.028's U25 rewrite of `class UART` carries the register block
  forward.
- **Resolved**: —
- **Unit**: U13 (with the driver's DMA receive path, so dev's twin boots from that unit on).
- **Depends**: M.TWIN.027 (the link's delivery, its U25 shape later); M.SRC_NET.221 (the driver's receive path).
- **Blast carried by**: the fake's own L2 cases and the shared contract's DMA checks → M.TWIN.130, M.TEST_HELP.025; the
  twin UART link tests → M.TWIN.158; fidelity rows (DMA ring, IRQ mask, OE, the finaliser) → M.TWIN.059; rp2 constants →
  M.TWIN.138; the twin mypy pass resolves `rp2` to this module (its `files` cover `digital_twin`, M.TWIN.075 — no edit).
- **Kind**: code

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
  TOOL), A.U6.30 Blast (`country()` unchanged — holds), A.U6.29 Blast (no twin entry), A.U27.28 (header over the cap),
  A.U25.63 (the file's five explicit `Any`: `:18` import, `:63`, `:65`, `:66`, `:136`; A-C3 S-09)
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
  names). No explicit `Any` (A.U25.63, G8/R61): `_stations: list[tuple[bytes]]` (rp2's one-element MAC tuples),
  `config_calls` and `connect_calls` annotated `BoundedLog` (M.TWIN.001's class; their entries are `dict[str, object]`
  and `tuple[str | None, str | None]`), `status() -> int | list[tuple[bytes]]`; the `typing.Any` import goes.
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
  A.U36.546 / A.U36.547 (SPEC E.3 and README reference name this file's tracked-task list and its `--help` block —
  SPEC/DOCS);
  A.U30.19 (L2: "a CLI fault (`--fault` vocabulary, A.U25.37) raising [the stack-exhausted `RuntimeError`] inside one
  read"; M.SRC_CORE.016's blast, carried by no TWIN change — gap pass G3)
- **Site**: `digital_twin/launch.py:1-188`
- **Change**: header → "Standalone CLI launcher for the twin (micropython digital_twin/launch.py --wiring-plan PATH
  [options]), src/-free: it builds the buses of the device whose plan it is given and periodically reads each wired
  sensor, attempts one WLAN connect and feeds a WDT. --fault/--hang expose each chip fake's FaultInjector (owner,
  2026-08-12: chosen over a probabilistic flaky mode)." (3 lines; tag form per AC_NOTES 6, A-C3 O-23); the argparse
  sentence moves to `parse_args()`'s comment: "# Hand-rolled: micropython-lib's argparse supports only store/store_const
  (python-stdlib/argparse/argparse.py:91-124)." Imports: `asyncio`, `errno`, `random`, `struct`, `sys`; `machine`,
  `network`, `from machine import I2C, SPI, WDT, Pin`; `from _bmp3xx_chip import _decode_calibration`; `from
  _twin_common import Injections, StatePaths, saturating_add`; the unwedge import goes. `_FAULT_DEVICE_OPS` → A.U25.37's
  table; new `_PERSISTENT_FAULT_OPS = {("isl29125", "int_stuck_high"), ("fram", "silent"), ("uart_link", "silent")}`
  (modes, not counted faults: `TIMES`/`MATCH` refused). `_HANG_DEVICE_OPS` → `sgp40`/`scd30` `writeto|readfrom_into`,
  `bmp3xx` `writeto|readfrom_mem|writeto_mem`, `isl29125` `writeto|readfrom_mem|writeto_mem`, `fram` `write|readinto`;
  its comment keeps the wlan reason (≤ 3 lines). New `_driver_of(key) -> str | None`: the longest vocabulary driver `d`
  with `key == d` or `key.startswith(d + "_")` (so `uart_link_init` → `uart_link`). `parse_fault_spec(spec) ->
  "tuple[str, str, int, int | None]"`: `DEVICE:OP[:TIMES[:MATCH]]`; the device resolved by `_driver_of()` (error names
  the vocabulary); a persistent op refuses `TIMES`/`MATCH`; `MATCH` parsed with `int(x, 16)`; the `wlan` `:TIMES`
  refusal goes (`MATCH` refused for `wlan`); the literal `stack` in the `TIMES` place (`DEVICE:OP:stack`, A.U30.19)
  queues one stack-exhaustion fault on a raisable op — returned as `times = 1` with the tuple's new fifth element `kind:
  str` (`"oserror"` for every other spec, `"stack"` here); `MATCH` is refused with it, and so is `stack` for `wlan` and
  the persistent ops. `parse_hang_spec()` resolves the device the same way. `_WDT_FEED_INTERVAL_S = 1.0` tagged `#
  @tunable l2.twin_wdt_feed_interval_s = 1.0` (comment "# well under the 8000 ms WDT timeout"); `_SENSOR_POLL_INTERVAL_S
  = 2.0` tagged `l2.launch_sensor_poll_interval_s`, `_WIFI_POLL_INTERVAL_S = 0.1` tagged
  `l2.launch_wifi_poll_interval_s` (A.U8.20's `l2.<name>` form; U8C rows). `_SSID`/`_PASSWORD` keep their values
  (twin-only test doubles; the S105 reason line is A.U28.29's in `pyproject.toml`). `LaunchConfig(state: StatePaths,
  injections: Injections, *, no_wdt_feed=False, duration=None, wiring_plan_path: str)` — `wiring_plan_path` required
  keyword; `StatePaths(fram, scd30, mem_backup)` and `Injections(seed, faults, hangs, wifi_outcomes)` live in
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
- **Unit**: U25 (stage U5: A.U5.15's grouping on the HEAD fields; U7: A.U7.19's `--help`; U8: the tags; U30: the
  `stack` form with A.U30.19)
- **Depends**: M.TWIN.001, M.TWIN.002, M.TWIN.010-014, M.TWIN.040
- **Blast carried by**: `run_generic_integration.py` imports `_pop_value`, the parsers and `_driver_of` → M.TWIN.047 (it
  hands each parsed fault spec, `kind` included, to the shared `_apply_fault()`, M.TWIN.049); the L2 reboot-and-code-20
  proof → SCR (Run 12, GAPS_G3 hand-off);
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
  chip lookup goes through `machine.peripheral()`), A.U30.19 (the `stack` fault, gap pass G3), A.U20.02 Blast
  (`launch.py:369` builds its own twin `WDT` — holds),
  A.U8.08 (`WDT(timeout=8000)` tagged), A.U36.546 (its tracked-task list stays the small-graph pattern SPEC E.3 names)
- **Site**: `digital_twin/launch.py:191-418`
- **Change**: `_apply_fault(device, op, times, match, chips, wlan)`: `wlan` → `wlan.raise_on[op] = (OSError, (errno.EIO,
  message), times)`; a persistent op → the chip's mode setter (`chips[d].configure_fault("isl29125:int_stuck_high")`,
  `chips[d].silent = True`); `fram:wren` → `chips[d].drop_next_wren += times`; else `chips[d].fault.inject_fault(op,
  OSError, errno.EIO, message, times=times, match=match)`; `_apply_fault()` takes the spec's `kind` as one more
  parameter, and a `stack` fault → `chips[d].fault.inject_fault(op,
  RuntimeError, _STACK_EXHAUSTED_MESSAGE)` with `_STACK_EXHAUSTED_MESSAGE = "maximum recursion depth exceeded"` and the
  comment "# twin-only test knob: no rp2 bus call raises this; it carries a C-stack overflow's exception
  (py/runtime.c:1786) into one read so the reboot path can be proven at L2"; `uart_link` reaches `_require_wired()`,
  which names the wired
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
- **Unit**: U25 (stage U30: the `stack` branch with A.U30.19)
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

### M.TWIN.050 Runner `main()` and exits: the local NTP responder, wall clock, passed watchdog, reset exit codes, one shutdown line
- **From**: OR140.a (13) (the runner's boot syncs against the twin's local NTP responder, M.TWIN.167; A-C review fold),
  A.U25.33 (2)-(3) (writes the `config_NTP.cfg` before `module.main()` unless `--online-ntp`; prints
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
  DOCS/SPEC); A.U35.28 (3) and M_SCR gap 4 (the line carries the twin FRAM chip's write count, read by M.SCR.051's rate
  assertion and M.SCR.018 (h); gap pass G3)
- **Site**: `digital_twin/run_generic_integration.py:311-439`
- **Change**: `main(config)`: first `prewarm_poll_set()`, then `patch_asy_udp_socket_for_unix_port()` (their comments
  one line each: "# first: before anything registers a poll object (unix_port_poll_prewarm.py)" / "# second: before any
  UDPSocket exists (tests_scripts/test_twin_entry_point_order.py)"); `configure_fram_state_path`,
  `configure_scd30_state_path`, `configure_mem_backup_state_path` (`""` → `None`); plan read, `configure_wiring(plan)`;
  `random.seed(seed)` when given; `_ensure_dir(config.config_dir)`; unless `config.online_ntp`, an `NtpResponder` on its
  port (M.TWIN.167) whose `serve()` joins the runner's tracked tasks and is closed by `_shutdown_cleanup()`, and
  `write_responder_ntp_config(config.config_dir)` (M.TWIN.053); the start line lists the grouped fields; `module = __import__(config.module)`
  with the comment "# loaded by its run-time name (SPECIFICATION.md F.1 named exception)"; `_wall_clock.install(m for m in sys.modules.values() if
  getattr(m, "time", None) is time)` (comment "# rp2's RTC is the wall clock: an NTP set must move time.time() here too");
  `watchdog = machine.WDT(timeout=8000)` with `# @tunable wdt.timeout_ms = 8000`; `main_task =
  create_task(module.main(watchdog=watchdog, cfg_path=config.config_dir, web_host=config.host, web_port=config.port))`;
  the readiness wait, crossover, chip collection, faults, hangs, wifi outcomes and the instrumentation tasks
  (M.TWIN.051) as today. `_print_wdt_status(config, watchdog)` prints one line `digital_twin/run_generic_integration.py
  [<device>] shutdown: would_have_triggered_count=<n> feed_count=<n> mem_backup: r0=<4 words>
  public_destinations_refused=<n> fram_writes=<n> fram_writes_by=<LOGGER>:<n>,…` (the first two from the runner's own
  WDT, the third `list(machine.mem_backup(0))`, the fourth from the shim; the fifth the wired FRAM chip's `write_count`
  — `machine._current_fram_chip`, 0 when the device wires none; the sixth one entry per FRAM-backed logger that wrote,
  sorted by name, `-` when none did: for each logger of every module-level object of the booted module that has
  `get_loggers()`, whose `fram` is a chunk, the name is the logger's `name` (SPEC A.7's names: `SCD30`, `CFGMGR_SCD30`,
  `UART_init`, …) and `n` is `chip.writes_at` summed over the chunk's two block addresses `fram._block_addr` — so one
  persisted entry counts 2 (both copies), in the same unit as the total, whose remainder is the non-logger writes
  (SGP40 backup, clears, erase units). The runner keeps the booted module in a module global `_module` beside
  `_watchdog`, so both handlers print the line; counts are per process, so a line after a simulated reset counts the
  writes up to it; a `writes_at_dropped` above 0 adds `fram_writes_unattributed=<n>`, telling the harness the
  per-logger counts are incomplete); comment
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
- **Unit**: U25 (after A.U21.06 for the unwedge removal; A.U20.02's keyword in U20 is already present; stage U35: the
  `fram_writes=`/`fram_writes_by=` fields with A.U35.28; the per-logger field by lead direction — a total can hide one
  module over its own rate, M.SCR.018 (h) and M.SCR.051 read it — gap pass G3)
  A-C2 step order: A.U24.47's part lands in U25, not U24 (it follows A.U24.47's own change, which lands in U25).
- **Depends**: M.TWIN.017, M.TWIN.019, M.TWIN.032, M.TWIN.034, M.TWIN.046, M.TWIN.047, M.TWIN.049, M.TWIN.053,
  M.TWIN.167
- **Blast carried by**: CI suite exit codes 3/4 (and 5 unused there), the `machine reset:` and shutdown-line fields
  (`mem_backup: r0=`, `public_destinations_refused=`, `fram_writes=`, `fram_writes_by=`) → A.U25.36, A.U25.33/A.U25.35, A.U35.28 (SCR,
  M.SCR.051/.018) and their L0 parser cases (M.TSC.165);
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
  A-C2 step order: A.U24.47's part lands in U25, not U24 (it follows A.U24.47's own change, which lands in U25).
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
  stays with the comment "Optional (--mem-sample-interval-ms): gc.mem_free() lives in this heap with no REST
  route; the collection is the one allow-listed instrumentation site (tests_scripts/test_gc_collect_sites.py)." at
  landing (no unit label in the text, A-C3 O-17); when B3's measurement (A.U35.25) keeps the collect, the clause "; a
  sparser interval gives Run 11 the same verdict" is appended before the closing full stop (≤ 3 lines); if it differs,
  the `gc.collect()` line goes and the comment's last clause with it (decided at execution, recorded in `timing.md`).
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

### M.TWIN.171 Concurrent load on dev's twin: both links under traffic, the webserver hammer, FRAM writes and config PUTs
- **From**: OR141.a (4) (g) ("Concurrent load: both dev link instances under traffic alongside the webserver hammer,
  FRAM log writes and config PUTs, with the twin's flash write stalling the loop for the datasheet time; both GC stages,
  zero MemoryError"), OR143.a (4) (concurrent load — maximum-size trains alongside the webserver hammer, both GC stages,
  zero MemoryError), FOLD_BRIEF F25/F27 (U25) — A-C review fold.
- **Site**: `digital_twin/run_generic_integration.py` (the DUT side: the stall installed, the links' counters on the
  shutdown line); the scenario itself in the host harness (`scripts/_digital_twin_scenarios.py`, G7/R19: request
  driving stays host-side).
- **Change**: DUT side: the runner installs `_flash_stall` (M.TWIN.170) on the booted config manager module; the shutdown
  line (M.TWIN.050) gains `uart=<instance>:transfers=<n>,failures=<n>,overruns=<n>,…` for each wired `uart_link`, read
  from the link driver's own counters and the receive path's lap count (no product hook, OR36). The scenario (host
  side, M.SCR.018): dev booted by the runner at each GC stage, the stall at its typical and then its maximum
  times; both link instances exercising; the webserver hammer; a sustained FRAM-log fault through `--fault` (persisted
  writes); config PUTs at a steady rate (each a flash write, so each a stall); and, for OR143.a, the link carrying
  maximum-size and over-cap trains (how the exerciser is made to send them from outside the product is decided at
  execution, with its reason recorded). Verdict: no link failure or overrun within the ring bound (the maximum stall is
  inside it by the ring's size derivation, OR141.a (4) (e)); an over-cap train refused and logged once; zero
  `MemoryError`/`memory allocation failed` in the run log (the twin gate, CLAUDE.md); the largest free block at the end
  not below the boot-contiguity bound.
- **Resolved**: G7/R19 keeps request driving out of the twin's heap, so the hammer and the PUTs come from the host
  harness while the stall and the counters are twin-side; the scenario is one run of the CI suite's harness.
- **Unit**: U25.
- **Depends**: M.TWIN.050, M.TWIN.169, M.TWIN.170; M.SCR.018 (the host scenario); M.SRC_NET.221 (the receive
  path's lap count); M.SRC_NET.220 (the cap and the chunked assembly).
- **Blast carried by**: the CI suite's run list and README "Automated CI suite" → M.TWIN.064 and M.SCR.018; the
  shutdown-line parser's new field → M.SCR.016, M.TSC.165.
- **Kind**: code

## digital_twin/unixport/_offline_ntp_config.py (new)

### M.TWIN.053 One NTP config writer both tiers import: offline, or the twin's local responder
- **From**: A.U25.33 (2) (`write_offline_ntp_config(cfg_dir)` writes `config_NTP.cfg` only when absent), OR140.a (13) (a
  booted twin syncs against the twin's local NTP responder, M.TWIN.167; A-C review fold), A.U18.10 (the
  `DNSFallback` key), A.U10.40 (`NTP_Host` → `NTPHost`), GAP-H3 of M_TEST_HELP (one implementation; born in
  `tests/_generated_module.py` at U20, "the twin runner imports it (or TWIN moves that one function to an import-safe
  module both tiers reach)")
- **Site**: new `digital_twin/unixport/_offline_ntp_config.py`
- **Change**: header (≤ 3 lines) "Writes the NTP config a twin or Unix-port boot starts from, so no run reaches a public
  NTP or DNS host: the twin's local responder on loopback, or TEST-NET-1 (RFC 5737) where a run must not sync; never a DNS
  fallback." `def write_ntp_config(cfg_dir: str, host: str) -> None` — writes `{"NTPHost": host, "DNSFallback": ""}` (the
  product's flat JSON config format) to `<cfg_dir>/config_NTP.cfg` only when that file is absent (an existing file is the
  run's own state); `def write_offline_ntp_config(cfg_dir: str) -> None` calls it with `"192.0.2.1"` and `def
  write_responder_ntp_config(cfg_dir: str) -> None` with `"127.0.0.1"` (the responder's host, M.TWIN.167). Imports only
  `json` and `os` (no `machine`, no `tests/`).
- **Resolved**: GAP-H3: the runner may not import `tests/` (G7/R02, A.U25.44's guard), so the function moves at U25 from
  `tests/_generated_module.py` (M.TEST_HELP.047, U20) to this import-safe module in A.U18.12's fake-free directory, which
  L1 boots already put on `sys.path` for the UDP shim; `tests/_generated_module.py` then imports it — TEST_HELP gap.
- **Unit**: U25 (the responder writer with M.TWIN.167)
- **Depends**: M.TWIN.017 (the directory), A.U10.40
- **Blast carried by**: the runner (the responder config unless `--online-ntp`) → M.TWIN.050; `tests/_generated_module.py` drops its copy and imports this →
  TEST_HELP gap (GAP-H3's resolution); the in-process twin boot helpers (C4) import it → M.TWIN.100-164; ruff/mypy scope
  by directory
- **Kind**: code

## digital_twin/unixport/_ntp_responder.py (new)

### M.TWIN.167 The twin's local NTP responder
- **From**: OR140.a (13) (the twin gets a local NTP responder, also used for new NTP-client unit tests; it replaces the
  log tolerance A.U35.38/.39 planned, which is dropped), FOLD_ANSWERS `twin-tolerates-ntp-offline` (owner, 2026-10-02:
  "A local NTP responder is built for the twin"), routine settlement `twin-choice-17` (its sync-dependent clock-jump cases
  run in the twin), OR141.a (5) (it covers the dropped hand-run NTP-outage row) — A-C review fold.
- **Site**: new `digital_twin/unixport/_ntp_responder.py`.
- **Change**: header (≤ 3 lines) "A local NTP server for twin and Unix-port runs (owner, 2026-10-02): answers each client
  request on loopback with the host's UTC time, so a booted twin syncs without reaching a public host; its test knobs
  make it silent, unsynchronised, malformed or implausible." Imports only `asyncio`, `select`, `socket`, `struct` and `time` (no
  `machine`, nothing from `tests/` or `digital_twin/`, so an L1 test may import it from the fake-free `unixport/`
  directory, M.TWIN.017). `def ntp_reply(unix_s: int, *, leap: int = 0, stratum: int = 1) -> bytes` — the 48-byte mode-4
  reply (version 3, as HEAD's test builders send), transmit timestamp `unix_s` plus `_NTP_EPOCH_DELTA = 2208988800`
  (comment "# 1900 to 1970 in seconds (RFC 5905); a local copy, pinned to src/asy_ntp_client.py's by
  tests/test_digital_twin_ntp.py"); it is `tests/_ntp_frames.py`'s `make_ntp_reply()` moved here, that module importing it (one implementation, the twin never importing `tests/`, G7/R02 — M.TEST_HELP.058).
  `class NtpResponder(port: int, host: str = "127.0.0.1")`: a non-blocking UDP socket bound at `(host, port)`;
  "twin-only test knob" attributes in `TEST_API`: `mode` — `"serve"` (default), `"silent"` (requests dropped: an outage),
  `"unsync"` (LI 3, stratum 0: a Kiss-of-Death reply), `"short"` (a 47-byte reply), `"implausible"` (a transmit time
  below the client's plausibility floor) — and `offset_s: int = 0` (added to the served time: a server whose clock
  differs from the host's); `requests: int` saturating at `_COUNTER_CAP = 0x3FFFFFFF` (comment: "# the project's counter
  cap (SPECIFICATION.md G.2), a local copy: this module imports nothing from digital_twin/", pinned equal to
  `_twin_common.COUNTER_CAP` by M.TWIN.168's test). `async def serve(self) -> None`: per round one `ipoll(0)` on its own poll
  object (iterated and checked, never truth-tested), at most one datagram read, a 48-byte mode-3 request answered per
  `mode`, then `await asyncio.sleep_ms(_POLL_MS)` (`# @tunable twin.ntp_responder_poll_ms = 10`, row basis estimated —
  measurement owed): it never blocks the loop and never waits on a real `select.poll()` with a timeout (CLAUDE.md's
  bounded-poller rule); `close()` closes the socket. The served time is `time.time() + offset_s` of the host (the Unix
  port's UTC clock). How the client's datagram to port 123 reaches it — the responder bound at `127.0.0.1:123` under the
  binary's `CAP_NET_BIND_SERVICE`, or the UDP shim (M.TWIN.017) mapping a loopback port-123 destination to the
  responder's port from the band table — is decided at execution, with its reason recorded; either way the product is
  untouched (OR36) and the shim still refuses every public destination.
- **Resolved**: the owner replaced A.U35.38/.39's tolerance (the normal-boot log check tolerating NTP's no-resolve and
  no-reply codes while unsynced) with this responder: a twin boot now syncs, and the normal-boot check expects NTP
  synced with no NTP entry (OR140.a (13), most recent owner decision). `make_ntp_reply()` and the responder's builder are
  one implementation, placed in the import-safe directory as GAP-H3 placed the offline-NTP writer.
- **Unit**: U25.
- **Depends**: M.TWIN.017 (the `unixport/` directory and the shim), M.TEST_HELP.056 (port bands), M.TEST_HELP.058 (its
  builder moves here in the same unit, its U25 stage importing it back).
- **Blast carried by**: the runner starts it unless `--online-ntp` → M.TWIN.050; the responder-config writer → M.TWIN.053;
  its L2 tests → M.TWIN.168; the new NTP-client L1 tests → M.TEST_UNIT.342; the clock-jump file's sync cases →
  M.TWIN.146; README "What's here", "Automated CI suite" Run 1 and "Runner flags" → M.TWIN.058, .064, .066; the twin
  normal-boot log checks expect NTP synced (A.U35.38/.39's tolerance dropped) → M.SCR.016, M.SCR.049, M.TSC.086, M.TSC.165; ruff
  and mypy scope by directory, the twin pass's `mypy_path` already holding `digital_twin/unixport` → M.TWIN.075 (no edit).
- **Kind**: code

## digital_twin/run_device_script.py (new)

### M.TWIN.054 Device-script runner: the plan, a recording watchdog, the GC stage, the script unchanged
- **From**: A.U26.05 (1) (`run_device_script.py <wiring-plan.json> <script.py> [--gc-threshold N]`: `configure_wiring`,
  the recording `machine.WDT(timeout=8000)` as `Board.run_isolated()` arms it, `gc.threshold(N)` default -1, `exec` of
  the script in a fresh `__main__`-like dict, exit with the script's status), A.U35.49 (runs every instrument at both GC
  stages), A.U30.18 (3) Blast (the C-stack device script builds `dev` through this route — holds), A.U25.43 / A.U25.34
  (a `main()` in `digital_twin/` that can boot a device prewarms, then shims, first), A.U25.33 (3) (the shim's
  public-destination guard covers every Unix-port run), A.U8.08 (`wdt.timeout_ms` site), A.U10.30 dropped (OR142.a (3):
  F.1's named list does not carry this file — the `exec` runs a script by path and imports nothing; A-C review fold),
  C5
- **Site**: new `digital_twin/run_device_script.py`
- **Change**: header (≤ 3 lines): "Runs one tests_hardware device script unchanged under the twin, as Board.run_isolated()
  runs it on silicon: the device's wiring plan, the one armed watchdog, the requested GC stage. Every instrument passes
  here before the hardware queue (scripts/record_twin_instrument_runs.py)." `main(argv) -> int`: first
  `prewarm_poll_set()`, then `patch_asy_udp_socket_for_unix_port()` (the A.U25.43/A.U25.34 order); parse `<plan>
  <script> [--gc-threshold N]` (hand-rolled with `launch._pop_value`; `-h`/`--help` prints usage, exits 0);
  `machine.configure_wiring(json.load(plan))`; `machine.WDT(timeout=8000)` with `# @tunable wdt.timeout_ms = 8000`
  (comment "# armed before the script runs, as Board.run_isolated() does; a script constructing WDT again gets this one
  (ports/rp2/machine_wdt.c:43-57)"); `gc.threshold(n)` (default -1, the reactive stage); `exec(compile(source, path,
  "exec"), {"__name__": "__main__", "__file__": path})` with the comment "# runs the device script by path, as the board
  runs it; no module is imported" (outside the import check: ruff S102 governs an `exec`, lead ruling 2026-10-05); a `SystemExit` from the script returns its code; any other exception prints its traceback and
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
  `runner_sha256` covers this file → A.U26.05; README "Running device scripts in the twin" → M.TWIN.074; ruff scope by
  directory; the twin mypy pass's `files` list → M.TWIN.075; the main pass's `exclude` gains
  `digital_twin/run_device_script\\.py$`
  in U26 — it calls the twin-only `machine.configure_wiring()`, which `tests/machine.py` lacks (M.TOOL.032's rule for a
  new twin-API module, M_TOOL gap 9; confirmed at landing by running the main pass) → TOOL (GAPS_G3 hand-off)
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
  A-C2 step order: A.U24.70's part lands in U25, not U24 (it follows A.U24.70's own change, which lands in U25).
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

## digital_twin/README.md

Shared for M.TWIN.058-074: every edited paragraph states current facts only (OR27.a; A.U25.65's rule: "used to",
"once", "the first version did", dated fixes and "Session-N"/"Step 5" pointers fold into the fact or go), cites no audit
ID (G9/R12), keeps owner tags on decisions (A.U0.31's list: `:5`, `:19`, `:50`, `:70`, `:104-112`, `:145`, `:155`, `:204`,
`:810-813`, `:877` — each tag travels with its sentence wherever this merge moves it), and A.U10.37/A.U10.38/A.U10.40
renames apply to every module, class and key named (C1). Device counts and device names are not copied from the TOMLs
(OR78.a, A.U36.024/A.U36.511): "every device of `devices/*.toml`". Units: each constituent edits its own lines in its own
unit; the end state below is the text after U36 (the latest constituent unit); U25 is the unit that restructures.

### M.TWIN.058 Intro and "What's here": one bullet per module, current facts, pointers to the fidelity table
- **From**: A.U36.024 (`:6` → "— any real device of `devices/*.toml`, or a synthetic fixture —"), A.U25.48 (`:6` the count is
  a fact, U36), A.U0.31 (`:5`, `:19`, `:50`, `:70`, `:104-112` incl. `:105` "independent, duplicated (not reused) copies
  (owner, 2026-08-12: the owner's choice over reuse)", `:145` tags), A.U25.25 (`:26-35` profile sugar goes), A.U25.03
  (`:18-45` states the per-id static model), A.U25.22 (`:41-45` `I2C.log` bullet states the drop count), A.U25.52 (`:36-41`
  names the identity guard), A.U25.08 (`machine.py` bullet names `mem_backup()`), A.U25.29 (`_fram_chip.py` bullet
  `:69-75`), A.U25.10 (`_sgp40_chip.py` bullet `:46-68`), A.U25.62 (class names), A.U25.26 (`:107-109` → the connect
  phase sentence), A.U25.72 (`:114-116` AP-mode gap sentence goes — the fidelity row says fixed), A.U25.33 (`network.py`
  bullet: TEST-NET addresses), A.U25.21 (`network.py`/`neopixel.py` bullet `:105-116`), A.U25.31 (`_http_client.py`
  bullet `:117-128`), A.U25.39 (`:89-101` unwedge bullet removed; the prewarm bullet's "its sibling" wording adjusted),
  A.U25.40 (`:80` and `:128` mentions of `segfault_stress_repro.py` go), A.U25.43 (4) / A.U36.040 (2) (the prewarm bullet
  keeps its how-to and points to SPEC F.7 for the defect; "a known limitation, not reported upstream (owner,
  2026-09-29)"), A.U25.09 (the runner bullet states exit codes 3/4), A.U36.513 (7) (`:136-141` → "The single entry point
  every automated level drives (SPECIFICATION.md L.4) — see "Booting a generated device" below for the general mechanism
  and "Swapping the twin in" for a manual run."), A.U25.25 (4) (launch bullet: the bus wiring of the device whose plan it
  is given), A.U25.70 / A.U24.82 (`:144-147` fault-surface paragraph: fresh exceptions, `match`, `pending()`), A.U25.59
  (`unplug`/`plug` named), A.U14.28 (shim bullet keeps its pointer), A.U7.01 (level wording follows SPEC E.6), A.SDEP.08
  (`:78` re-read at the pin), A.U25.71 / M.TWIN.019 (`_wall_clock.py` bullet, gap: no action writes it), M.TWIN.001,
  M.TWIN.053, M.TWIN.054 (new modules' bullets), M.TWIN.167 (the responder's bullet, OR140.a (13); A-C review fold)
- **Site**: `digital_twin/README.md:1-147`
- **Change**: intro `:1-14`: "— any real device of `devices/*.toml`, or a synthetic fixture —"; the real-time Timers and
  bounded random values carry "(owner, 2026-08-12)"; `:12-14` keeps the separation sentence and names
  `scripts/micropypath.toml`'s twin layout instead of copying a `MICROPYPATH` value (A.U27.15). Bullets, in this order:
  `machine.py` (Pin with rp2's ids/names/modes and the external line level; static per-id I2C/SPI/UART wired from
  `configure_wiring(plan)` — "constructing a bus before a plan is configured raises", no profile sugar, no default
  device; the IRQ-pin identity and its guard (the construction scenarios, A.U25.52); Timer as an asyncio task with rp2's
  alarm pool (owner tag `:19`); WDT that records; RTC + wall clock; `mem_backup()`/`reset_cause()`; `I2C.log`/`SPI.log`
  bounded to the last 200 with a `dropped` count; `peripheral()`/`reset_peripherals()`/`reset_test_state()` test-only);
  the four I2C chip fakes (one line each, facts that are not rows of the fidelity table: the ISL29125's non-nominal ratio
  and measured register-map behaviours with their SPEC M.1.2/M.1.4 pointers, `power_cycle()` and `set_illumination()`;
  the SGP40's general-call reset; the SCD30's provisioned default and RDY edge; the BMP3XX's inverted compensation, owner
  tag `:877`); `_fram_chip.py` (opcode protocol, size and RDID from `machine.py`'s one table, knobs `drop_next_wren`,
  `rdid_once`, `silent` — the "real bug (fixed 2026-09-04)" history goes); `_twin_common.py`; `_crc8.py` /
  `_fault_injection.py`; `_wall_clock.py`; `network.py` / `neopixel.py` (owner tag `:105`; connect phase "moves through a
  real `STAT_CONNECTING` phase and connects after `_CONNECT_DELAY_S` (0.7 s), under `_poll_sta_connect_status()`'s 5 s
  budget"; STA address in TEST-NET-1 so no twin run reaches a public resolver; AP singletons answer `192.168.4.1`; the
  NeoPixel stores a GRB bytearray; owner tag `:104-112` "reaching the host's real network through every connect phase");
  `_http_client.py` (real HTTP over real sockets, owner tag; refusal → `CeilingRefusedError`, incomplete →
  `IncompleteResponseError`, both `OSError`; strict JSON check, the lazy import's reason "so `_http_client` imports without
  `tests/` on the path"; `timeout_s`; shape parity with `tests_hardware/http_client.py`); `unixport/` (the UDP shim, the
  NTP config writer and the local NTP responder a booted twin syncs against, with its silent/unsynchronised/malformed/
  implausible knobs; L1 tests may put it on their path because it holds no hardware fake); `unix_port_poll_prewarm.py`
  (callers: every entry that boots a device with real sockets, first; the 64-port scan from 17400, a fixed row of
  `tests/_port_bands.py`; "(the defect and its removal trigger: SPECIFICATION.md F.7)"); `launch.py` (`--wiring-plan`
  required; reads every wired SCD30/SGP40/BMP3XX; owner tag on `--fault`); `run_generic_integration.py` (A.U36.513 (7)'s
  sentence; exit codes 3 reset, 4 bootloader, 5 power loss; `--test-*` flags, see "Runner flags"); `run_device_script.py`
  (see "Running device scripts in the twin"). The fault-surface paragraph `:144-147` → "Every chip fake exposes `.fault`, a
  `FaultInjector`: `inject_fault(op, exc_type, *args, times=1, match=None)` raises a fresh exception per call, optionally
  only for one command word, register or opcode; `pending(op)` counts what is queued; `inject_hang()` is a real blocking
  sleep (see `--hang`). Faults the rp2 port cannot produce are refused (fidelity table). `I2C.unplug(address)`/
  `plug(address)` model a sensor pulled and re-seated; off/clean by default (owner, 2026-08-12)."
- **Resolved**: A.U36.040 (U36) turns A.U25.43 (4)'s README account (U25) into a pointer — the later action's end state
  (SPEC F.7 is the fact's one home, both actions agree). A.U25.71 adds `_wall_clock.py` with no README line; the bullet
  is added here (gap closed).
- **Unit**: U36 (U25 restructures)
- **Depends**: M.TWIN.001-057, M.TWIN.167
- **Blast carried by**: SPEC A.10/E.6.5 point to the fidelity table → A.U25.01 (SPEC); root README recipe pointers →
  A.U36.547 (DOCS)
- **Kind**: doc

### M.TWIN.059 New "Fidelity table" section
- **From**: A.U25.01 (the section, columns `Class | Fact on silicon | Twin | Evidence | Proven at | Status`, every row it
  lists), A.C.10 / A.C.15 / A.C.19 (phase C updates rows: measured facts move rows to `fixed`/measured), A.U37.04 (close
  check reads the table), A.U36.041 (the Persistence row is the one place for the multi-instance limit; SPEC L.4
  points here), A.U0.59 (`:354` tag — void: the paragraph becomes a pointer, A.U25.01), A.U14.20 (`mem_backup()` row),
  A.U24.17 (the shared contract noted), A.U24.20 ("bus objects are static per id"), A.U24.26 (fakes cite their port
  facts), A.U24.80 ("UART stream ioctl answers as rp2"), A.U15.05 (SGP40/SCD30 timing rows may cite SPEC M.3/M.2),
  A.U11.07 (the twin `mem_backup` row), A.U25.08 / .10 / .11 / .12 / .13 / .14 / .15 / .16 / .17 / .18 / .19 / .20 / .21 /
  .26 / .27 / .55 / .59 / .68 / .71 / .72 / .73 (their rows), A.U4.06 (the SCD30 NVM write counter is a test surface, not
  chip behaviour), A.U25.54 (power loss at SPI-transaction granularity; mid-byte loss is L3's), A.S0930.27 ("SPI wire time:
  off by default, 8 µs/byte for timing proofs"), A.U35.31 (the twin countdown dies with its loop), A.U25.68 (the "Pinned
  constants" subsection lists `tests/test_digital_twin_rp2_constants.py`), adherence additions of this merge (below);
  gap pass G3: A.U26.58 (the scheduler-queue row, M.HW_DEV.106's blast), A.U30.19 (the `stack` knob row), A.U35.28 (the
  FRAM write counter is a test surface)
- **Site**: `digital_twin/README.md` new `## Fidelity table` after "What's here", before "Swapping the twin in"
- **Change**: A.U25.01's table verbatim in structure and rows (its Change text is the content spec), with these
  end-state adjustments: (1) the RTC row reads "RTC: no constructor argument, an 8-tuple, weekday recomputed, setter
  returns `None`; with the runner's wall clock installed a set moves `time.time()`/`gmtime()` (fixed,
  `tests/test_digital_twin_machine.py`); uninstalled it holds a fixed tuple" (A.U25.71's "fixed (installed by the
  runner)"); (2) rows added from merged changes: SCD30 provisioned default `measuring=True` (not datasheet-derived;
  `nvm=SCD30Nvm(…, False)` models an unprovisioned unit); SCD30 0x5204 outside [400, 2000] ignored (assumption, BACKLOG
  row with the wrong-CRC one); SCD30 0x0010 overwriting altitude compensation (Interface Description 1.4.1) not modelled
  (accepted until a driver depends on it) — an adherence addition (G7/R03: every modelling gap is a row); the SCD30
  `nvm_writes` counter counts accepted NVM commands — a test surface (A.U4.06); SGP40 unknown command keeps the pending
  reply (assumption, A.U25.11); ISL29125 PRST counter stops at its target (fixed, `tests/test_digital_twin_isl29125.py`,
  A.U25.14); I2C `unplug`/`plug` and every chip's `power_cycle()` (twin-only knobs; fixed by
  `tests/test_digital_twin_hot_replug.py`, A.U25.59); SPI power loss after k transactions, never mid-byte (L3 `fram_reset_
  race_*`, A.U25.54); SPI wire time off by default (A.S0930.27); UART: static per id, ring re-allocated on
  re-construction, `ioctl()` `EINVAL` except POLL, `readline(size)` clamped and counted, `txdone()` always `True` (the link
  delivers at once; accepted; L3 `uart_*` scripts) (A.U25.04, A.U24.80, A.U13.12, A.U13.13); the twin WDT never resets,
  so codes reached only through a real watchdog reset are L1 and phase C (A.U25.55); a runner-cancelled `main()` keeps
  the runner's loop and with it the WDT countdown alive (A.U35.31); public-destination UDP refused by the shim (fixed,
  `tests/test_digital_twin_sensortask_integration.py`, A.U25.33); the twin's `machine` fake meets the shared contract
  `tests/_machine_contract.py` (A.U24.17); the soft-timer scheduler queue (rp2: 8 deep, a callback past it dropped,
  `ports/rp2/mpconfigport.h:131`) is not modelled — twin timers call back directly, so
  `scheduler_saturation_drop.py` is a listed silicon-only exception in the twin-run record (A.U26.58, A.U26.05); `--fault
  DEVICE:OP:stack` raises a stack-overflow `RuntimeError` from a bus read, which no rp2 bus call does (twin-only knob,
  A.U30.19); the FRAM chip's `write_count`/`writes_at` are a test surface, not chip behaviour, attributed to loggers by
  the runner (A.U35.28) — one sentence under the
  table, with "every rp2 constant the twin models is
  pinned by `tests/test_digital_twin_rp2_constants.py`" as the "Pinned constants" subsection (A.U25.68). (3) Each row with
  Status `assumption` names its BACKLOG "Real-hardware work still owed" line (A.U25.01; the BACKLOG lines are DOCS's).
  (4) `[src: …]` notes are not written into the permanent README (G9/R12, C5): the table's Evidence column cites the
  source line, datasheet page or test, never an audit ID — A.U25.01's own "register and action IDs go only in `[src: …]`
  notes beside each row" is replaced by this, see Resolved.
- **Resolved**: A.U25.01 keeps `[src: A.U…]` notes "beside each row, never in the table"; G9/R12 / AC_NOTES 4 forbid
  temporary audit IDs in permanent text, and the README is permanent — the notes are dropped (adherence fix; the
  provenance stays in the audit files). A.U0.59 tags `:354`; A.U25.01 turns `:354-358` into a pointer — A.U0.59 is void
  (its own text: "void if U25's G7/R15 work removes the limitation" — the limitation is restated as the Persistence row).
- **Unit**: U25 (phase C updates by A.C.10 deltas; the scheduler row lands with A.U26.58 in U26, the `stack` row in U30,
  the write-count row in U35)
- **Depends**: M.TWIN.002-057
- **Blast carried by**: BACKLOG assumption rows → A.U25.01/.08/.10/.12/.14/.15 (DOCS); SPEC A.10/E.6.5 pointers →
  A.U25.01 (SPEC); SPEC L.4 → A.U36.041 (SPEC); close check → A.U37.04 (PROC)
- **Kind**: doc

### M.TWIN.060 "Swapping the twin in": one recipe pointer, persistent manual defaults, current facts
- **From**: A.U36.547 (`:158-163` command block → "(README.md, Recipes: <name>)", explanation kept), A.U36.024 (`:158-163`
  examples name a device; no default), A.U25.48 (`:161-162` no `wozi` default), A.U27.15 (`:178` literal layout →
  `scripts/micropypath.toml` named; `:188-195` names the file), A.U25.44 (`:188-195` names the path guard), A.U0.31 (`:155`
  "real HTTP over real sockets (owner, 2026-08-13)", `:204` "settable address, default `localhost:8080`, browser-reachable
  (owner, 2026-08-13)"), A.U25.32 (`:197-204` "defaults every state-persistence path to `None`" → "the manual entry point
  persists to `digital_twin/*.json` by default (owner, 2026-08-13); automated callers pass per-run paths or `""`"),
  A.U25.41 (`:197-198` names the reuse: parsers, `_pop_value`, `_collect_chips`, `_shutdown_cleanup` from `launch.py`),
  A.U25.46 / A.U27.32 (the soak and every HTTP scenario are host-side), A.U35.26 (`MEM_SAMPLE <ticks_ms> <mem_free>`),
  A.U10.36 (`:227-229` the `_get_settings_flat()` bug history goes — the one shape is SPEC C.6's), A.U20.06 (`:221`
  `start_and_check_tasks()` → `start_tasks()`/`supervise_tasks()`), A.U36.513 (`:217-230` hand-written module references),
  A.U24.53 (runner flags: `--config-dir`)
- **Site**: `digital_twin/README.md:149-230`
- **Change**: `:151-158`: "The generated `sensortask_<device>.py` needs zero twin-awareness … pure `MICROPYPATH` ordering"
  kept; real HTTP sentence tagged (owner, 2026-08-13); "`scripts/run_unix_port_integration.sh --device <device>` does
  exactly this (README.md, Recipes: twin launch)". `:166-195`: the build steps kept as prose; the literal `MICROPYPATH` line
  → "with `scripts/micropypath.toml`'s twin layout (`build/generated_src`, `src`, `digital_twin`, `digital_twin/unixport`,
  `ext`, `frozen_modules`, `.frozen`; never `tests`, which `tests_scripts/test_twin_never_needs_tests_on_its_path.py`
  guards)"; the `frozen_html` and ordering explanations kept. `:197-215` → the runner reuses `launch.py`'s parsers and
  helpers (one copy); "the manual entry point persists FRAM, SCD30 and mem-backup state to `digital_twin/*.json` and its
  config to `digital_twin/config/` by default (owner, 2026-08-13); automated callers pass their own `--config-dir` and `""`
  state paths"; `--host localhost --port 8080` default (owner tag); a bare run serves forever; the soak is host-side
  (`scripts/_digital_twin_ci_suite.py` Run 11) and reads the runner's `MEM_SAMPLE <ticks_ms> <gc.mem_free()>` lines by
  their position in the log. `:217-230` → "`tests/test_digital_twin_sensortask_integration.py` builds a generated graph
  against the twin buses in-process and starts only the tasks each test needs (never `supervise_tasks()`); its HTTP
  checks run host-side (`scripts/_digital_twin_scenarios.py`)." — the `_get_settings_flat()` bug history goes.
- **Resolved**: —
- **Unit**: U36
- **Depends**: M.TWIN.044-053
- **Blast carried by**: root README "Recipes" → A.U36.547 (DOCS); `scripts/micropypath.toml` twin layout gains
  `digital_twin/unixport` → SCR gap
- **Kind**: doc

### M.TWIN.061 "Booting a generated device": the plan's one shape, the passed watchdog, crossover by bus
- **From**: A.U25.25 (`:236` profile enum sentence goes), A.U36.513 (`:270-272` "(via `subprocess.Popen`, as
  `scripts/_digital_twin_ci_suite.py` does) for every device of `devices/*.toml` plus both mandatory synthetic fixtures";
  "— so a generated module is run, not only parsed."; `:276-279` → "`_collect_chips()` walks the same wiring plan
  `configure_wiring()` was given, never a hand-picked `i2c0`/`i2c1` literal."; `:282-287` goes; `:295-297` "— driven by the
  wiring plan, for whichever device declares the pair."), A.U25.28 (`:276-279`, `:288-297` the `._i2c.devices`
  description → `machine.peripheral()`), A.U17.18 (`:288-297` → "carries a fourth, optional `"uart"` key (`{"initiator_bus",
  "responder_bus"}`, the two generated UART bus globals …)" and "reads the two already-built `asy_uart_driver.UART` buses
  off the booted module by name"), A.U20.28 (`:288-291` states the shape once by pointing at `buildgen/twin_wiring.py`'s
  `TwinWiringPlan`), A.U20.02 ("Booting a generated device": the runner passes the WDT to `main(watchdog=…)`), A.U25.69 /
  OR126.a (1) (the four keywords), A.U27.15 (`:265` generated-boot form names `scripts/micropypath.toml`), A.U25.33 (the
  runner writes the NTP config before boot — since the A-C review fold the local responder's), A.U25.24 (the configure order stated once), A.U36.513 (the
  "Session-3" wording goes)
- **Site**: `digital_twin/README.md:232-297`
- **Change**: `:234-239`: "`run_generic_integration.py` boots any device by consuming a `buildgen.generate.generate_device()`
  module and the wiring plan `buildgen.twin_wiring.compute_twin_wiring()` derives from that device's TOML (SPECIFICATION.md
  L.4); both are produced host-side in CPython (the Unix port has no `tomllib`)." The Python example keeps the synthetic
  fixture path. `:253-268` keeps the "first on `MICROPYPATH`" explanation; the shell line names the layout file. New
  paragraph: "Before the boot the runner calls `machine.configure_wiring(plan)` and every `configure_*_state_path()`
  (each raises once a bus exists), starts the local NTP responder and writes the config pointing at it into its `--config-dir` unless `--online-ntp`,
  then runs
  `module.main(watchdog=machine.WDT(timeout=8000), cfg_path=…, web_host=…, web_port=…)` — the generated entry's four
  keywords (owner, 2026-09-30)." (The responder sentence: M.TWIN.167; OR140.a (13), A-C review fold.) `:270-279`, `:282-287`, `:288-297` per A.U36.513 (7) and A.U17.18, with the plan shape
  stated once: "the plan's shape is `buildgen/twin_wiring.py`'s `TwinWiringPlan` (`buses`, `spi`, `pins`, optional `uart`
  with `initiator_bus`/`responder_bus`); `tests_scripts/test_twin_wiring_contract.py` checks every reader". `:281-282`
  (launch "left alone") → "`launch.py` reads the same plan for its bus wiring (`--wiring-plan`) but boots no product
  module."
- **Resolved**: —
- **Unit**: U36
- **Depends**: M.TWIN.044-050
- **Blast carried by**: SPEC L.4 → A.U36.518 (SPEC)
- **Kind**: doc

### M.TWIN.062 FRAM and SCD30 persistence: the owner's write-cycle reason, six SCD30 values, one limit pointer
- **From**: A.U0.29 (`:301-303` "never automatically — the owner's 'don't do unnecessary write cycles' for an SSD-hosted
  state file (owner, 2026-08-12)"), A.U0.31 (`:50`, `:70` "(owner, 2026-08-12)" on explicit `save_state()`/load), A.U25.12
  (`:330-346` names the six persisted values — five settings plus the measuring status — and the pressure assumption),
  A.U15.06 / A.U4.04 (SCD30 section: compare-before-write, the counter; text from A.U4.04's Blast), A.U15.08 (`:330-335`
  five NVM-backed settings → the six, U25's), A.U25.32 (`:348-352` → "the manual entry point persists by default (owner,
  2026-08-13); automated callers pass per-run paths or `""`"; `:317-319`), A.U25.62 (`FramChip` → `FRAMChip`), A.U25.08
  (a third persisted state: `mem_backup`), A.U25.01 / A.U36.041 (`:354-358` → a pointer to the Persistence row), A.U0.59
  (void, see M.TWIN.059)
- **Site**: `digital_twin/README.md:299-358`
- **Change**: FRAM `:301-304` per A.U0.29 (owner tag); example keeps `configure_fram_state_path()`/`flush_fram()` but
  shows `_shutdown_cleanup()`; `:317-319` → "`""` (or `None` in code) runs it in memory only, as
  `tests/test_digital_twin_fram.py` does by constructing `FRAMChip(size, rdid_response)` directly"; the chunked-stream
  paragraph keeps its fact and drops "Found via … during baseline verification" (it states the rule: "streamed in
  512-byte chunks so no contiguous allocation of the whole image is needed (MicroPython's GC never relocates live
  blocks)"). SCD30 `:332-338` → "Real SCD30 hardware keeps the measurement interval, ambient pressure, altitude,
  temperature offset, ASC enable and the continuous-measurement status in NVM (Interface Description 1.4.1-1.4.8); the
  twin persists those six on explicit flush. Whether the ambient-pressure value itself persists is an assumption (the
  datasheet names only the status) — fidelity table, BACKLOG row."; `:348-352` per A.U25.32. New short paragraph
  "mem_backup: the runner writes `digital_twin/mem_backup_state.json` only on a simulated reset and the next launch
  consumes and deletes it" (the behaviour M.TWIN.032 writes; the text cites no change ID, A-C3 O-18). `:354-358` → "Only
  the last-wired SCD30 and FRAM instance persist — the fidelity table's Persistence row states the limit and the change
  that lifts it."
- **Resolved**: A.U15.08 says the five-settings text is "U25's with the fidelity row"; A.U25.12 makes it six — the U25
  text wins (later, and it names the measuring status). A.U0.59's tag on `:354` is void (M.TWIN.059 Resolved).
- **Unit**: U25 (stage U0: A.U0.29/A.U0.31 tags; U4: A.U4.04's SCD30 sentence)
- **Depends**: M.TWIN.011, M.TWIN.013, M.TWIN.032
- **Blast carried by**: `.gitignore` mem-backup line → lead gap
- **Kind**: doc

### M.TWIN.063 "Running the twin's own tests": paths from the layout file, the harness rules
- **From**: A.U27.15 (`:370` stale "currently "src:tests:frozen_modules:.frozen"" → name `scripts/micropypath.toml`), A.U25.46
  (HTTP scenarios run host-side; "Running the twin's own tests" names the harness), A.U35.09 (the test list gains two —
  U36's count line: no count, see Resolved), A.U25.07 (a test that can reach a reset catches `SimulatedRebootError` and
  calls `asyncio.new_event_loop()`), C4 (the boot discipline), CLAUDE.md segfault rule (no nested `asyncio.run()`)
- **Site**: `digital_twin/README.md:360-376`
- **Change**: `:362-372`: the per-file `sys.path` insert of `digital_twin` (and `digital_twin/unixport`) kept;
  `MICROPYPATH` → "the unit layout of `scripts/micropypath.toml`"; new 3-sentence paragraph: "A file that boots a device
  prewarms the poll set, then applies the UDP shim, at module level (`tests_scripts/test_twin_entry_point_order.py`);
  before each build it calls `machine.reset_peripherals()`, `network.reset_interfaces()`, `configure_wiring(...)` and
  writes the offline NTP config; it registers `machine.reset_test_state` and `network.reset_test_state` with
  `microtest.after_each`, catches `machine.SimulatedRebootError` where a product reset is reachable and then calls
  `asyncio.new_event_loop()`, and calls `asyncio.run()` only from synchronous test scope." `:374-376` keeps the
  determinism fact. HTTP-driving scenarios: "run host-side by `scripts/_digital_twin_scenarios.py` against a runner
  subprocess (SPECIFICATION.md E.9)"; and "A file marked `PER_DEVICE = True` runs once per generated device, named by
  `TEST_DEVICE` (`scripts/test.sh`); its driver-specific tests run on the device `tests/_twin_devices.py` picks." (A.U36.016,
  M.TWIN.108/.144/.152).
- **Resolved**: A.U35.09 says the README "test list gains the two (U36's count line)"; the README carries no test list or
  count (OR78.a/G9/R11 cut counts) — the two tests need no README line; nothing to add.
- **Unit**: U27 (stage U25: the boot discipline paragraph)
- **Depends**: M.TWIN.035, M.TWIN.040
- **Blast carried by**: —
- **Kind**: doc

### M.TWIN.064 "Automated CI suite": per-pass state archive, required device, every run's current claims
- **From**: A.U25.35 (`:388-395` "**Clean**: …" → "each pass keeps its state under `digital_twin_ci_logs/<pass>/state/`
  and archives it before every fresh start"), A.U27.16 (the logs directory archived under `build/archive/`), A.U36.024 /
  A.U25.48 (`:388-391` examples name a device; a missing device is a usage error), A.U25.55 (Run 12 added; the counts at
  `:390`, `:408`, `:412` cut to "every run"), A.U27.17 (`:410` "one more if run 11's soak retries" goes), A.U25.64 (lists
  `--only`/`--repeat`), A.U7.09 (the summary block text), A.U35.38 (Run 1: "reads, keeps and checks the logs, then
  clears them"; its NTP tolerance dropped, OR140.a (13): Run 1 boots against the local NTP responder and expects NTP
  synced; A-C review fold), A.U25.36 (Runs 3, 4, 5, 5b, 5c rewritten to their new claims: Run 3 the combined-fault escalation cell
  ending in a simulated reset with exit 3; Run 4 `ResetReason` = supervisor escalation and region 0 cleared; Run 5 counts
  failure events, codes by name; 5b the exact ring all-or-nothing; 5c through the product reboot path), A.S0930.38 /
  A.S0930.41 (`:483-489` → "5c. A commanded reboot through the controlled shutdown — FRAM drained, then every task stopped,
  then the reset — the case that must never lose anything"; Run 13's rows), A.S0930.27 (Run 13 "system commands" and its
  knob), A.U25.37 (Run 3's sustained set per instance, `fram:silent`; Run 10 `_HANG_MATRIX`; `_LEFT_OUT`; `:478-482` tag
  "(owner, 2026-09-26)" with the decision's words "an abrupt reset mid-write may lose a module's whole FRAM history,
  all-or-nothing, never partial or garbled"; `:440, :454, :460` restate Run 3's FRAM fault as `fram:silent`), A.U25.38
  (Run 2/5 text: polls, no fixed sleeps), A.U25.33 (each run's log asserts `public_destinations_refused=0`), A.U25.65
  (`:453-456` BACKLOG pointer: the clause goes, below; `:503-507` the reset-before-setup fact), A.U11.31 (`:505-507`
  "dropped by design" is U25's — carried by A.U25.65), A.U14.R01 (`:543-544` → "matching CLAUDE.md's recovery-ladder
  rule: a transfer that never returns
  is the watchdog's"), A.U11.03 (`:484` holds), A.U5.02 (`:451` `fram=fram` in the generated module — keeps its fact, the
  module wiring by `fram_target`), A.U0.43 (`:564-566` "the owner's rule (2026-09-26) that a threshold is never the fix"),
  A.U27.32 (Run 11/11b "every GET route"), A.U36.532 (`:578` H.7.1 citation lands unchanged), A.U25.09 (exit codes 3/4),
  A.U10.40 (Run 1 PUT examples use the renamed keys: `SCD30.MeasInterval`, …), A.U10.37 (`captive_dns` → `asy_captive_dns`,
  `DNSServer` → `CaptiveDNS`), A.S0930.04 (the `dev` runs in both CRC modes via `--device-toml`), A.U25.44 (Run 7's shim
  sentence points to `unixport/`), A.U25.34 (Run 7's capability check fails loudly); gap pass G3: M_DOCS gap 5 / M_PROC
  gap 3 (c) and G1's hand-off H3 (the `:453-456` clause), M.SCR.053's blast (Run 5's keyed fault), A.U30.19 (Run 12's
  code 20, M.SRC_CORE.016's blast); OR141.a (4) (g) (the dev concurrent-load run, M.TWIN.171; A-C review fold)
- **Site**: `digital_twin/README.md:378-585`
- **Change**: the section keeps its structure (intro, Clean/Build/Test, numbered runs, logs paragraph) with: intro
  `:380-386` unchanged in substance; examples `scripts/run_digital_twin_ci.sh <device>` (a missing device prints usage and
  exits 2) and `--only <run>`/`--repeat <n>`; **State** replaces **Clean** (A.U25.35's sentence) with A.U27.16's archive
  sentence; **Test** drops every run count ("runs every run twice, once per GC stage"; "a fixed port 18080"); runs 1-11b
  rewritten to A.U25.36/A.U25.37/A.U25.38/A.U35.38's claims, Run 1's reading "boots against the twin's local NTP
  responder, reads, keeps and checks the logs — no error or warning entry from any module, NTP synced — then clears
  them"; Run 3 restates the FRAM fault as `fram:silent` (the chip
  answers zeros and keeps its bytes, so nothing is torn) and whether `fram` stays out of Run 4's reset-to-0 sweep is
  recorded from one execution run (A.U25.37's own instruction); Run 5 (`:466-471`) names its fault as the suite boots
  it — `sgp40:readfrom_into:3:0x260F`, three faults on measure-raw reads only, sparing setup's serial read and the
  heater-off rung (M.SCR.053) — and runs only where the device wires an SGP40, a device without one recording a named
  skip; Run 5c per A.S0930.38's sentence; Run 7 names the shim
  in `digital_twin/unixport/` and the capability check; Run 10's matrix sentence (one bounded hang per bus-attached
  driver, each in its own process); new **Run 12** (reset reasons: power-on, bootloader with its assumption, region 0
  cleared — A.U25.55; from U30 also the C-stack code 20 after a `--fault <device>:<op>:stack` run, A.U30.19, M.TWIN.044)
  and **Run 13** (system commands: `resetconfig`, `erasefram`, the near-miss list, states, hazards,
  watchdog with the SPI wire-time knob, per-step hangs through `--test-shutdown-hang`, power loss — A.S0930.27/.38); the
  `dev` concurrent-load run (both links under traffic with the flash stall, the webserver hammer, FRAM writes and
  config PUTs, M.TWIN.171; A-C review fold); a
  sentence "every run's log is checked for zero `MemoryError`/`memory allocation failed` and for
  `public_destinations_refused=0`"; the `dev` passes run once per CRC mode (A.S0930.04). Every history clause ("used to
  stand here", "until both were corrected", "measured here at roughly 1 in 8" kept only as the measured fact with its
  date) goes per OR27.a. `:450-458`'s paragraph keeps its fact (the two logs are FRAM-backed; Run 3's faulted chip is
  why they read 0) and its last sentence loses the clause "and one nothing re-checks against a *healthy* chip
  (BACKLOG.md)" outright: no BACKLOG owed row matches it (M.DOCS.064's end state has none) and Run 5c checks every
  driver against a healthy chip (A.U25.36), so the sentence ends at "…a much weaker claim than "these never persist"."
- **Resolved**: A.U25.65's `:453-456` edit names a BACKLOG item "if one exists at execution, else the sentence goes";
  the DOCS and PROC merges found none (M_DOCS gap 5, M_PROC gap 3 (c)), so the clause is deleted (gap pass G3, G1's
  hand-off H3). A.U25.65 and A.U25.37 both edit `:453-456`/`:642-656`; A.U25.37's Blast says "A.U25.65's `:642-649` edit
  starts from this text (A-C merges)" — applied in that order. A.U11.31 hands `:505-507` to U25 (A.U25.65).
- **Unit**: U36 (U25 rewrites, the `:453-456` deletion and Run 5's fault; U27 archive; U30 Run 12's code 20; U35 Run 1
  sentence)
- **Depends**: M.TWIN.050, M.TWIN.051, M.TWIN.167, M.TWIN.171
- **Blast carried by**: `scripts/_digital_twin_ci_suite.py`, `scripts/run_digital_twin_ci.sh` → their actions (SCR)
- **Kind**: doc

### M.TWIN.065 "What the runner keeps in-process" and Run 11's numbers: sampler verdict, wire log, ticks stamps
- **From**: A.U11.08 (`:591-592` → "`gc.mem_free()` is also published as `/status`'s `MemFree`, but one poll's reading is
  not a stream: this flag samples it inside the process on a fixed timer"), A.U30.09 (same sentence — A.U11.08's), A.U30.17 /
  A.U35.25 (the sampler paragraph states the outcome of B3's sparser-interval check and the I.4(e) exception sentence),
  A.U35.26 (Run 11 paragraph: samples joined by log position; the timestamp is `ticks_ms`), A.U0.54 (the wire log
  "unbounded (agent, 2026-09-14)"), A.U27.08 (`:613-620` "100, not the 40 once used" → the measurement stays here; the
  suite's comment points to it), A.U27.17 (Run 11 decided on one attempt), A.U25.46 (`:589-590` the host-side move)
- **Site**: `digital_twin/README.md:587-640`
- **Change**: `:589-590` keeps "Almost every request-driving job runs host-side (SPECIFICATION.md E.9). Two things stay in
  the runner process, deliberately — plus the named `--test-*` instrumentation (see Runner flags)". The sampler bullet:
  A.U11.08's first sentence; "Each line carries `time.ticks_ms()` for diagnostics only; the host selects the samples
  inside its window by their position in the log, never by either process's clock."; the `gc.collect()` sentence states
  B3's verdict (kept as the one allow-listed instrumentation site at the interval B3 settled, or removed — whichever
  A.U35.25 records); the 2026-09-14 removal experiment stays as a dated measured fact. The wire-log bullet keeps its
  fact, "unbounded (agent, 2026-09-14)". Run 11's numbers: the warmup paragraph keeps the measurement (dated) and drops
  "wozi's original 40"/"not wozi's" (devices are not named: "a device with more instances settles longer"); the tolerance
  section keeps its derivation (dated measurements are facts) and gains "one attempt decides (no retry)".
- **Resolved**: —
- **Unit**: U35
- **Depends**: M.TWIN.052
- **Blast carried by**: SPEC I.4(e) twin-exception sentence → A.U30.17 (SPEC)
- **Kind**: doc

### M.TWIN.066 New "Runner flags" subsection: the runner's flags and its test-only instrumentation
- **From**: A.U25.74 (README flag table "test-only instrumentation (owner, 2026-09-30)"), A.U31.06 (`--test-loop-lag-ms`
  in the flag table), A.U35.31 (`--test-watchdog-fault` beside `--fault`/`--wifi-outcome`; the fidelity note), A.S0930.27
  (`--test-shutdown-hang` and its steps), A.U24.53 (runner flags: `--config-dir`), A.U25.32 / A.U25.09 / A.U25.33 (state
  paths, `--config-dir`, `--mem-backup-state-path`, `--online-ntp`), M.TWIN.051 (`--test-fault-status-interval-ms`),
  OR140.a (13) (`--online-ntp` off now runs the local responder, M.TWIN.050/.167; A-C review fold)
- **Site**: `digital_twin/README.md` new `### Runner flags` after "Booting a generated device"
- **Change**: a table `Flag | Default | Effect`: `--module`, `--wiring-plan` (required), `--device`, `--host`/`--port`
  (`localhost`/`8080`, owner, 2026-08-13), `--config-dir` (`digital_twin/config/`), `--fram-state-path`,
  `--scd30-state-path`, `--mem-backup-state-path` (`digital_twin/*.json`; `""` in memory), `--online-ntp` (off: the
  local NTP responder runs and the config pointing at it is written; on: neither, the stored config is used), `--seed`, `--fault DEVICE:OP[:TIMES[:MATCH]]`, `--hang DEVICE:OP:SECONDS[:TIMES]`,
  `--wifi-outcome`, `--duration`, `--gc-threshold` (32768), `--mem-sample-interval-ms`; then "Test-only instrumentation
  (owner, 2026-09-30), every flag off by default and absent from the product's entry path
  (`tests_scripts/test_twin_runner_test_flags.py`):" `--test-hold-closing-slot` (`SLOT_HELD`/`SLOT_RELEASED`),
  `--test-stall-loop-ms N` (`STALL`), `--test-conn-status-interval-ms N` (`CONN_SLOTS open= backlog=`),
  `--test-fault-status-interval-ms N` (`FAULT_PENDING`), `--test-shutdown-hang STEP` (`HANG <step>`, steps
  S1-S6), `--test-loop-lag-ms N` (`LOOP_LAG`), `--test-watchdog-fault KIND` (`WDT_AT_FAULT <feed_count>`); one sentence:
  "`main-exit` keeps the runner's loop alive, since the twin's WDT countdown dies with its loop." Exit codes: 0 normal, 1
  error, 3 simulated reset, 4 bootloader, 5 power loss.
- **Resolved**: —
- **Unit**: U25 (U31 and U35 add their rows)
- **Depends**: M.TWIN.047, M.TWIN.050, M.TWIN.051, M.TWIN.167
- **Blast carried by**: root README command-line reference → A.U36.547 (DOCS)
- **Kind**: doc

### M.TWIN.067 "Two suite-table subtleties": the strict set as the code holds it
- **From**: A.U25.65 (`:642-649` names `scd30`, `bmp3xx`, `isl29125` and the strict readers sentence), A.U25.37 (`:644-656`
  restated with `fram:silent`; whether `fram` stays out of Run 4's sweep recorded from one execution run); A.U19.14
  (BACKLOG item 24 leaves at U19; its citer `:669` repoints in the same unit — M_DOCS gap 2, gap pass G3); A.U11.31 (the
  reset runs every source concurrently, `:658-660` read)
- **Site**: `digital_twin/README.md:642-669`
- **Change**: the first subtlety: "`_NO_PERSIST_WHEN_FRAM_FAULTED` (`scd30`, `bmp3xx`, `isl29125`) is not "these logs are
  in-memory": every one is FRAM-backed; Run 3 sets the FRAM `silent`, so nothing they log reaches the chip" + A.U25.65's
  strict-readers sentence; the `fram` paragraph restated for a silent chip (no torn chunk: the bytes are kept) with the
  execution result; the `_RESET_ERRORS_TIMEOUT_S` subtlety keeps its derivation: `:658-660` "resets every registered
  source in turn, and each FRAM-backed one pays a real chunk write" → "resets every registered source at once, and each
  FRAM-backed one still pays a real chunk write" (A.U11.31's concurrent reset); `:669` "(BACKLOG item 24, which carries
  the real-hardware measurements)" → "(SPECIFICATION.md C.7)". History clauses ("It was named and described that way
  once", "The first two CI runs …", "The earlier flat 20.0 was inert …") go (OR27.a).
- **Resolved**: A.U25.37 then A.U25.65 on the same lines (A.U25.37's Blast fixes the order). M.TWIN.067 named BACKLOG item
  24 by title, but A.U19.14 deletes the item at U19, before this U25 edit; M_DOCS gap 2 repoints every citer to SPEC C.7
  in U19 (gap pass G3).
- **Unit**: U25 (stage U19: the `:669` pointer, with A.U19.14)
- **Depends**: M.TWIN.011 (`silent`); A.U19.14's SPEC C.7 text (SPEC)
- **Blast carried by**: `scripts/_digital_twin_ci_suite.py:726-736` restatement → A.U25.37 (SCR)
- **Kind**: doc

### M.TWIN.068 Fault and hang sections: the shared vocabulary, instance keys, persistent modes, refused faults
- **From**: A.U25.37 (`--hang` section `:671-680`: the new vocabulary incl. `bmp3xx:writeto`, `isl29125:writeto`; the
  `Isl29125Chip.configure_fault()` section `:682-690` now CLI-reachable as `isl29125:int_stuck_high`), A.U25.18 ("Fault
  injection" row and the `--hang` section: `fram` `readinto|wren|silent`, `write` refused), A.U25.70 (`MATCH`), A.U24.82
  (one line on `pending()`), A.U25.27 (`wlan` `:TIMES`), A.U25.62 (`ISL29125Chip`), A.U25.59 (`unplug`/`plug`), A.U0.31
  (`:145` fault injection built in, off by default "(owner, 2026-08-12)"), A.U30.19 (the `stack` form, gap pass G3)
- **Site**: `digital_twin/README.md:671-690`
- **Change**: one section `### Faults, hangs and modes`: `--fault DEVICE:OP[:TIMES[:MATCH]]` (bounded, a fresh `OSError`
  per raise, `MATCH` a hex command/register/opcode) and `--hang DEVICE:OP:SECONDS[:TIMES]` (a real blocking sleep), with
  DEVICE a driver name or an instance key `<driver>_<name_ext>`; the per-driver op table (A.U25.37 (1)); the persistent
  modes `isl29125:int_stuck_high`, `fram:silent`, `uart_link:silent` (no TIMES/MATCH) and `fram:wren:N` (the next N
  WRENs dropped); "faults the rp2 port cannot raise are refused: an SPI write never raises, a read raises only from 32
  bytes on (fidelity table)"; "`wlan` takes every `raise_on` method with `:TIMES`, and has no `--hang`" (its reason kept);
  "`pending(op)` reports what is still queued; the runner's `--test-fault-status-interval-ms` prints it"; "`--fault
  DEVICE:OP:stack` queues one `RuntimeError("maximum recursion depth exceeded")` — a twin-only knob no bus raises on
  silicon, carrying a C-stack overflow's exception into one read so the CI suite can prove the reboot and reset code 20"
  (U30 stage, A.U30.19). The
  `configure_fault()` subsection's text becomes the `int_stuck_high` line ("the bus works and conversions continue, only
  the INT line never moves — the silent failure the periodic range evaluation exists to survive").
- **Resolved**: —
- **Unit**: U25 (stage U30: the `stack` line)
- **Depends**: M.TWIN.002, M.TWIN.044
- **Blast carried by**: —
- **Kind**: doc

### M.TWIN.069 "WDT._arm()'s late-feed backstop": current facts
- **From**: A.U25.37 (Run 10 per driver, `--duration 15`), C5, A.U10.37 (`system_service.py` → `asy_system_service.py`)
- **Site**: `digital_twin/README.md:692-708`
- **Change**: the mechanism paragraph kept; "`_arm()` now checks" → "`_arm()` checks"; the closing sentence names Run 10's
  per-driver hangs (one bounded hang per bus-attached driver the device wires, `--duration 15`) instead of
  `run10_watchdog_hang_backstop.log` and SGP40 alone; `system_service.py` → `asy_system_service.py`.
- **Resolved**: —
- **Unit**: U25
- **Depends**: M.TWIN.031
- **Blast carried by**: —
- **Kind**: doc

### M.TWIN.070 "`_http_client.py`'s read paths": current facts, the incomplete-response class
- **From**: A.U25.31 (the bullet `:117-128` and this section: `IncompleteResponseError`), A.SDEP.17 (W40: the
  `readexactly()` premise re-read at the new tag — conditional), C5 (`:725` "This file's first version did." goes)
- **Site**: `digital_twin/README.md:710-745`
- **Change**: the two read paths kept; `:721-725` drops "This file's first version did." and states "an EOF inside a sized
  body raises `IncompleteResponseError`"; `:741-745` keeps the measured CI failure as a dated fact (`dev`'s figure stays a
  measurement of one device, worded "a device's frozen website of 7579 bytes"). If W40 finds `extmod/asyncio/stream.py`
  fixed at the refreshed pin, the section is rewritten to the then-current fact (a delta, A.SDEP.17).
- **Resolved**: —
- **Unit**: U25 (B0 re-check may follow)
- **Depends**: M.TWIN.016
- **Blast carried by**: —
- **Kind**: doc

### M.TWIN.071 "`_unix_port_udp_addr_shim.py`" section: new home, tuple-only src/, the order rule, loud failures
- **From**: A.U18.12 (the same sentence as the shim comment: "the opaque sockaddr bytes object this Unix build's socket
  needs; src/ only ever sees tuples"), A.U25.33 (the guard: refused destinations, counter), A.U25.34 (`:749-767` the order
  rule and the loud Run 7 failure), A.U25.65 (`:761-767` the two messages that tell the faults apart), A.U14.28 (the
  section keeps its source-level account; SPEC F.7 rows point here), A.U36.544 (SPEC points to this section), A.SDEP.16
  (W13 conditional), A.U10.37/38 (`captive_dns.py` → `asy_captive_dns.py`, `AsyUDPSocket` → `UDPSocket`, `DNSServer` →
  `CaptiveDNS`)
- **Site**: `digital_twin/README.md:747-795`
- **Change**: heading → "### `unixport/_unix_port_udp_addr_shim.py` (real UDP round trips under the Unix port)";
  `:749-759` → "`patch_asy_udp_socket_for_unix_port()` runs once, before any `UDPSocket` exists: every entry that boots a
  device calls `prewarm_poll_set()` then the shim first (`tests_scripts/test_twin_entry_point_order.py`). The port-53 tests
  need `CAP_NET_BIND_SERVICE` on the interpreter (`scripts/test.sh` and `scripts/run_digital_twin_ci.sh` grant it); Run 7
  checks the capability first and fails naming it."; the note `:761-767` → A.U25.65's two messages ("the real DNSServer
  never bound its port 53 socket" = missing capability; "real hotspot activation never started the real DNSServer task"
  = CPU starvation), "check `getcap` first", ≤ 3 lines; the three quirks kept with point 1 ending "`src/` passes and
  accepts only `(host, port)` tuples; the shim keeps the packed form outside `src/`"; new paragraph: "The shim also refuses
  any destination outside 127.0.0.0/8, 0.0.0.0 and 192.0.2.0/24 through the product's own failure path and counts it;
  the runner prints `public_destinations_refused=<n>` and the CI suite requires 0." The last paragraph's "Every real call
  site … always local" kept.
- **Resolved**: —
- **Unit**: U25
- **Depends**: M.TWIN.017
- **Blast carried by**: SPEC F.7/G.2 pointers → A.U14.28, A.U36.544 (SPEC)
- **Kind**: doc

### M.TWIN.072 "Adding a new chip fake": the current shape a new fake copies
- **From**: A.U36.516 (6) (step 5 → "5. The new driver's website fields come from its `@web` tags alone (`SPECIFICATION.md`
  Part H.5/K.4) — nothing to edit here or in any definitions file."), A.U6.04 / A.U36.515 (the same step — carried by
  A.U36.516), A.U20.28 (`:826` "add it to `buildgen/twin_wiring.py`'s own `FIXED_ADDRESSES` table" → "declare the address as
  a module-level const in the driver"), A.U25.25 (step 2: no `configure_i2c_wiring()`/wozi-dev sentence), A.U25.67 (step 3
  names `tests_scripts/test_twin_fake_catalog.py`), A.U36.039 (the SPI one-device-per-id fact: SPEC K.5 states it; this
  section points there and keeps the CS-routing note), A.U25.01 (`:844-850` moves to the fidelity table's Buses row),
  A.U0.31 (`:810-813` tags: seedable random source "(owner, 2026-08-12)", bounded random walk "(owner, 2026-08-12, round
  2)"), A.U25.73 (ranges cite their datasheet page; a judgment call says "not datasheet-derived"), A.U5.15 (`Walk`),
  A.U25.42 (`timer_factory`), A.U25.59 (`power_cycle()`), A.U25.70 (`key=` on `maybe_raise`), A.U25.68 / A.U24.18
  (knobs say "twin-only test knob" and join `TEST_API`), A.U25.62 (`<CHIP>Chip` spelled as the driver's `_NAME`),
  A.U36.543 (SPEC D.16 lists this README in the documentation line)
- **Site**: `digital_twin/README.md:797-850`
- **Change**: intro `:799-802` keeps "required whenever a new sensor driver lands (SPECIFICATION.md K.5)", drops "the three
  sensors it started with". Step 1: read the datasheet first; add `_<chip>_chip.py` with class `<NAME>Chip` (the driver's
  `_NAME` spelling); its shape: a `FaultInjector` passed `key=` on every `maybe_raise`; `random_source` (owner tag) and
  `Walk(lo, hi, step)` bounds — `lo`/`hi` citing the datasheet page, the step "not datasheet-derived" (owner tag on the
  bounded walk); `timer_factory` if it has its own measurement clock (never `import machine`); `power_cycle()`;
  `handle_*` methods answering the driver's exact transactions; every test-only knob commented "twin-only test knob".
  Step 2: a branch in `machine._build_i2c_chip()` (the wiring plan is generic); a hardwired address is a module-level const
  in the driver, which buildgen reads. Step 3: `tests/test_digital_twin_<chip>.py` plus the catalog check
  (`tests_scripts/test_twin_fake_catalog.py` fails until the fake exists) and a fidelity-table row per unmodelled fact.
  Step 4: "What's here" and `launch.py`'s op vocabulary. Step 5: A.U36.516's sentence. The SPI paragraph `:844-850` →
  "A new SPI device on an occupied bus id needs chip-select routing in the twin first (SPECIFICATION.md K.5; fidelity
  table)."
- **Resolved**: A.U6.04 (U6), A.U36.515 and A.U36.516 (U36) edit step 5; A.U36.516's text is the latest — its Why names
  the same handoff.
- **Unit**: U36 (U25 rewrites steps 1-4)
- **Depends**: M.TWIN.010-014, M.TWIN.023
- **Blast carried by**: SPEC K.5/D.16 → A.U36.039, A.U36.543 (SPEC)
- **Kind**: doc

### M.TWIN.073 Code quality, harness pitfalls and known gaps: current scope, pointers, gaps dissolved
- **From**: A.U27.23 (the twin pass's file list lives in `typecheck.ini`), A.U27.22 / A.U8.24 (strictness lines), A.U14.28
  (`:867-871` harness pitfalls keep the habit rules; Unix-port divergences point to SPEC F.7), A.SDEP.16 (`:867-918`
  re-read at the pin), A.U25.01 (`:876-886` first two bullets become fidelity rows), A.U25.40 (`:886-906` bullet goes),
  A.U25.43 (4) / A.U36.040 (the modselect account: prewarm bullet → SPEC F.7; "worth filing one upstream" → "a known
  limitation, not reported upstream (owner, 2026-09-29)"), A.U0.31 (`:877` "(owner, 2026-08-12)" on the inverted
  compensation — travels to the BMP3XX fidelity row / chip bullet), A.U25.39 (no unwedge mention remains)
- **Site**: `digital_twin/README.md:852-919`
- **Change**: "Code quality tooling" `:854-865` → "`digital_twin/` is in the ruff scope; mypy checks it in its own pass
  (`digital_twin/typecheck.ini`, whose `files` names the twin tests too), because each bare `machine`/`network`/
  `neopixel` resolves to one file per run (SPECIFICATION.md B.15)." (≤ 4 lines prose; the excluded-file list goes — the
  ini holds it). "Harness pitfalls" `:867-872` kept (habit rules), ending "Every Unix-port-vs-rp2 difference worked around
  in test code is listed in SPECIFICATION.md F.7." "Known gaps / follow-ups" `:874-919` is removed: the calibration and
  fault-queue bullets are fidelity rows (M.TWIN.059), the stress-tool bullet goes with the file (M.TWIN.055), the
  modselect account is SPEC F.7's with the README prewarm bullet pointing there (M.TWIN.058).
- **Resolved**: A.U25.43 (4) (U25) moves the modselect account into the prewarm bullet; A.U36.040 (U36) moves it to SPEC
  F.7 and leaves a pointer — end state the pointer (both actions name F.7 the one home).
- **Unit**: U36 (U25 removes the gaps section)
- **Depends**: M.TWIN.058, M.TWIN.059, M.TWIN.075
- **Blast carried by**: SPEC F.7 → A.U14.28, A.U36.040 (SPEC)
- **Kind**: doc

### M.TWIN.074 New "Running device scripts in the twin" section
- **From**: A.U26.05 (the README gains this section; the exception list lives in the record, not prose), A.U35.49 (every
  instrument through the runner at both GC stages, after B2 and B3), M.TWIN.054
- **Site**: `digital_twin/README.md` new `## Running device scripts in the twin` after "Running the twin's own tests"
- **Change**: ≤ 12 lines: what `run_device_script.py` does (plan, armed watchdog, GC stage, the script unchanged; prewarm
  and shim first); how `tests_hardware/twin_board.py`'s `TwinBoard` and `pytest tests_hardware/flash --twin` use it;
  `scripts/record_twin_instrument_runs.py` writes `tests_hardware/twin_record.json` and `tests_scripts/test_twin_record.py`
  fails when a script, the runner or the `src/` API a script imports changed since its record; a script that cannot run
  in the twin is an `exception` entry with its reason in the record (never listed here).
- **Resolved**: —
- **Unit**: U26
- **Depends**: M.TWIN.054
- **Blast carried by**: `tests_hardware/README.md` habit 5 → A.U26.05 (HW_BENCH/DOCS)
- **Kind**: doc

## tests/test_digital_twin_bmp3xx.py

### M.TWIN.100 BMP3XX fake tests: reset values, hooked probe, shared random double, renamed class
- **From**: A.U25.13 (OSR 0x02 at power-up and after 0xB6 following a 0x0D write; a queued `writeto` hang delays the
  probe; any test reading OSR before a write expecting 0 follows), A.U25.51 (`:218` asserts register state unchanged by
  the probe and a queued `writeto` fault consumed), A.U24.38 (hands `:218` to A.U25.51), A.U24.30 (`_FixedRandom` →
  `tests/_twin_random.FixedRandom`; `:151-158` asserts the recorded step ranges `(-0.1, 0.1)`, `(-0.5, 0.5)`; the "would
  violate the default bounds" comment goes), A.U25.62 (`BMP3XXChip`), A.U5.15 (constructor `temp=Walk(…)`,
  `pressure=Walk(…)`), A.U25.70 (fault calls `inject_fault(op, OSError, errno.EIO, "m", times=n)`; a `match` case on a
  register address), A.U15.R03 Blast (the twin tests re-checked against setup's reset — holds after the reset values),
  A.U25.59 (`power_cycle()` case), A.U25.01 (the 0xB6 row cites this file), C2, C5
- **Site**: `tests/test_digital_twin_bmp3xx.py` (whole file; `:9`, `:61-70`, `:94-189`, `:189-205`, `:218-257`)
- **Change**: import `BMP3XXChip` and `from _twin_common import Walk`; `_FixedRandom` (`:61-70`) deleted, `from _twin_random
  import FixedRandom` (with `tests` already on the unit layout path); every construction passes `temp=Walk(lo, hi,
  step)`/`pressure=Walk(...)` where it set `min_*`/`max_*`/`*_step`; `:151-158` asserts `chip._random.calls` holds the
  two overridden step ranges; `:189-197` gains "OSR reads 0x02 and CONFIG 0x00 at construction" and "after writing 0x0D
  to OSR, 0xB6 to CMD restores 0x02" (DS001 register table cited on the line); `:199-205` asserts the reset constants
  too; `:218-228` (probe) asserts the register image (OSR, CONFIG, status) unchanged by `handle_writeto(b"")` and that a
  queued `writeto` fault is consumed by it (`fault.pending("writeto") == 0`); new: a queued `writeto` hang of 0.05 s delays
  `handle_writeto(b"")` by at least 0.05 s (measured with `ticks_diff`, a bounded small hang), a `readfrom_mem` fault with
  `match=0x04` spares a read of 0x31 and hits the next 0x04 read, two raises of a `times=2` fault are distinct objects,
  `power_cycle()` restores OSR/CONFIG/status and keeps the walk position; `:229-257` use the class-plus-args form; the
  canonical trailer (A.U24.04).
- **Resolved**: —
- **Unit**: U25 (stage U24: `FixedRandom` import and A.U24.30's assertions)
- **Depends**: M.TWIN.010; M.TEST_HELP.059 (`FixedRandom`)
- **Blast carried by**: —
- **Kind**: test

## tests/test_digital_twin_fram.py

### M.TWIN.110 FRAM fake tests: rollover, framing, knobs, refused faults, RDID table, booted-device cases
- **From**: A.U25.15 (wrap on write/read past the end, one-write framing raises, `drop_next_wren=1` drops one WREN only,
  `rdid_once` answers once, `silent` reads zeros and ignores writes; 24-bit tests hold), A.U25.06 (RDID into an 8-byte
  buffer keeps 8 bytes), A.U25.18 (`:275-290` → a `write` injection raises `ValueError`, a `readinto` fault fires on a
  32-byte read and not a 4-byte one; `_OVERRUN_MIN_READ == machine._SPI_DMA_MIN_SIZE`), A.U25.29 (`:74` constructs with an
  explicit RDID; for every `asy_fram_driver._KNOWN_PRODUCT_IDS` entry the twin table holds `[0x04, 0x7F, pid >> 8, pid &
  0xFF]` and the key sets are equal), A.U25.32 (a 0x2000-size file into a 0x40000 chip loads blank), A.U25.62 (`FRAMChip`),
  A.U25.16 (SPI init tuples carry `firstbit` 1), A.U25.03 (a test building `SPI(0, …)` calls `reset_peripherals()` first),
  A.U16.R01 (L2: a booted write surviving one dropped WREN), A.U16.R03 (L2: a booted device whose chip goes silent — the
  FRAM task ends, a restart recovers when cleared, staying silent arms the reboot within the budget), A.U16.06 (L2: a
  booted device whose chip holds a written logger chunk and SR 0x8C: that logger's `setup()` reads `None`,
  `initialized` stays `False`, the chunk bytes unchanged), A.U16.09 (L2: a never-written chunk read twice reports
  uninitialised both times), A.U36.544 (`:303` "L.4" → the fact in place), C2, C4 (booted cases); A.U35.28 (the write
  counter's case, gap pass G3)
- **Site**: `tests/test_digital_twin_fram.py` (whole file)
- **Change**: `FRAMChip(size, rdid_response=…)` everywhere (a module constant `_MB85RS64V_RDID = bytes([0x04, 0x7F, 0x03,
  0x02])  # MB85RS64V datasheet p.10`); `:74` → "RDID reports the ID it was constructed with"; `:275-290` split into
  `test_write_fault_injection_is_refused` and `test_readinto_fault_fires_only_on_a_long_read`; `:303` comment states the
  fact ("the low address byte must survive: 0x010000 and 0x000000 are distinct cells") instead of "L.4"; new chip-level
  cases per A.U25.15/.06/.18/.32 above and `test_fram_rdid_table_matches_the_driver` (imports `asy_fram_driver` from
  `src/`, reads `_KNOWN_PRODUCT_IDS` — a `const()`-free dict, checked at execution — and compares with
  `machine._FRAM_RDID_BY_MAX_SIZE`); `test_payload_writes_are_counted_by_address` (a WREN + multi-byte WRITE steps
  `write_count` and `writes_at[addr]` by one; a one-byte status WRITE, a WRITE without WREN, a `silent` chip's WRITE and
  a dropped WREN's WRITE leave both; past `_WRITES_AT_MAX_KEYS` distinct addresses a new one steps `writes_at_dropped`). Booted-device cases
  (in-process, no HTTP; C4 discipline, a device from
  `device_with("fram")`): A.U16.R01's (`chip.drop_next_wren = 1`, one logger write → the chunk reads back intact), A.U16.06's
  (chip pre-loaded with a written chunk and SR 0x8C), A.U16.09's (double read of a blank chunk), A.U16.R03's (`silent =
  True` → the FRAM manager's task ends and the supervisor restarts it; cleared → `setup()` succeeds and the next logger
  write lands; kept silent → the reset is armed within the restart budget — asserted at the armed point
  (`sysfunct._reset_armed`) before the reset Timer fires, then the Timer is deinit'ed and the supervisor task cancelled
  from outside, as A.S0930.38 does, so no `SimulatedRebootError` strands the in-process graph). The canonical trailer.
- **Resolved**: A.U16.R03 wants the twin's "`SimulatedResetError` path"; an in-process graph that raises it strands its
  tasks (A.U25.07), so the case asserts the armed reset and stops there (A.S0930.38's pattern); the full reset-and-relaunch
  is the CI suite's subprocess territory (A.U25.09) — settled by A.U25.07's rule.
- **Unit**: U25 (A.U16's L2 cases are written in U25 on the knobs; stage U16: none — the knobs do not exist before U25;
  stage U35: the write-count case)
- **Depends**: M.TWIN.011, M.TWIN.025, M.TWIN.026, M.TWIN.035
- **Blast carried by**: —
- **Kind**: test

## tests/test_digital_twin_fram_crash_points.py (new)

### M.TWIN.112 FRAM crash-point enumeration: power loss after every SPI transaction, chunk and erase
- **From**: A.U25.54 (per FRAM size and for one logger store and the SGP40 timestamped chunk: write A; count B's SPI
  transactions; for every k, lose power after k, rebuild the manager and store over the same chip memory, assert exactly A
  or B, next write C succeeds, logged entries within {none, E31, W71, W72, W73} by catalog name), A.S0930.27 (5) (the
  erase on dev's layout: every k inside pass 1 and the first/last pass-2 unit of each allocated block; a fresh manager
  restores each ring exactly or blank; the reset command's delete loop cut after k removals), A.U2.01 (codes by name)
- **Site**: new `tests/test_digital_twin_fram_crash_points.py`
- **Change**: header (≤ 3 lines) "Crash consistency on the twin chip: power lost after every SPI transaction of one chunk
  write and of the FRAM erase; a restored history is exactly the old or the new, never another (owner, 2026-09-26)."
  Builds the manager in-process over `machine.SPI(0, …)` from `device_with("fram")`'s plan, one write per boot (no
  unbounded interleave claimed); the chip object is kept across the simulated reboot: after
  `SimulatedPowerLoss` the test calls `machine.reset_peripherals()`, constructs `SPI(0, …)` again and sets
  `machine.peripheral("spi0").device = chip` (the same memory; `device` is in `SPI.TEST_API`); codes looked up through
  `tests/_error_codes.py` `code(...)` (A.U2.03, M.TEST_HELP.045); the erase half uses the product's `erase_fram()` path (M.SRC_CORE) with
  `lose_power_after(k)`; the delete-loop half patches `os.remove` from outside to raise after k removals. Registers
  `machine.reset_test_state` (C4). k loops are bounded by the dry-run count, no wall-clock waits.
- **Resolved**: A.U25.54 says "build a fresh `AsyFramManager` + store over the **same** chip memory (`reset_peripherals()`
  keeps nothing else)"; with static per-id SPI objects the next construction wires a fresh chip, so the test re-attaches
  the kept chip through the `device` test attribute — the stated intent (same memory, nothing else kept).
- **Unit**: U25 (A.S0930.27's erase half co-lands)
- **Depends**: M.TWIN.026, M.TWIN.034, M.TWIN.035; M.SRC_CORE erase/reset sequence
- **Blast carried by**: U35's matrix row names it → A.U25.54 (PROC); fidelity row → M.TWIN.059
- **Kind**: test

## tests/test_digital_twin_generic_wiring.py

### M.TWIN.114 Wiring tests: per-device plans, RDID per table size, one-shot RDID, single-instance persistence
- **From**: A.U25.25 (`:126-189` `configure_i2c_wiring` regression tests replaced by one test per generated device
  asserting the booted buses carry the plan's attachments; `:182-190` → "constructing a bus with no plan raises
  RuntimeError"), A.U25.29 (`:98-116` → one case per table size), A.U25.03 (`reset_peripherals()` before each
  construction; bus pins from the plan), A.U25.53 (new: a tmp state path, an inline plan of two SCD30 on `i2c0`/`i2c1` with
  rp2-valid pins and one FRAM on `spi0`, persists exactly the last-constructed SCD30's settings through `flush_scd30()` and
  `flush_fram()` writes the one FRAM), A.U16.R02 (`:105-163`'s `rdid_response` override gains a one-shot bad answer —
  `rdid_once`), A.U16.17 (a dead-chip boot reaches the reboot — U25's tier: asserted at the armed point, as M.TWIN.110),
  A.U25.15 (knob users), A.U20.28 (the file reads the plan's keys — the contract test's scan), A.U25.01 (the Persistence
  row cites this file), C2
- **Site**: `tests/test_digital_twin_generic_wiring.py` (whole file)
- **Change**: every test starts `machine.reset_peripherals()`; inline plans use rp2-valid pins (`i2c0` scl 13/sda 12, `i2c1`
  scl 15/sda 14, `spi0` sck 2/mosi 3/miso 4) and carry the `pins` key; `:98-116` → `test_fram_rdid_follows_the_plans_size`
  over both table sizes and `test_unknown_fram_size_raises`; `:126-189` → `test_each_generated_device_boots_its_plans_
  attachments` (loop over `generated_devices()`: construct each plan bus with its pins, assert `peripheral(bus).devices`
  keys equal the plan's addresses and each chip's class matches the driver) and `test_constructing_a_bus_with_no_plan_
  raises`; new `test_one_shot_bad_rdid_then_good` (A.U16.R02, `chip.rdid_once = bytes(4)`), A.U16.17's dead-chip boot,
  A.U25.53's two persistence cases. `reset_test_state` registered.
- **Resolved**: —
- **Unit**: U25
- **Depends**: M.TWIN.022, M.TWIN.024, M.TWIN.025; `tests/_twin_devices.py` (M.TEST_HELP.055)
- **Blast carried by**: —
- **Kind**: test

## tests/test_digital_twin_hot_replug.py (new)

### M.TWIN.116 Hot re-plug: every bus-attached driver recovers without a reboot
- **From**: A.U25.59 (per generated device and per bus-attached driver: start the real supervisor and the reader's task,
  unplug, wait until the reader's task ended at least once, plug back within the restart budget, assert a reading again,
  `machine.reset_count` unchanged, `would_have_triggered_count == 0`; FRAM via `silent` then cleared: the task ends, its
  restart re-runs `setup()`, the next logger write lands), A.U14.38 (SPEC F.2's proof sentence names this file)
- **Site**: new `tests/test_digital_twin_hot_replug.py`
- **Change**: header (≤ 3 lines) "A sensor or the FRAM re-plugged on a running unit recovers without a reboot: the task
  ends, the supervisor restarts it, setup() runs again (owner, 2026-07-13)." C4 boot per device (`generated_devices()`),
  `supervise_tasks()` started as a tracked task; for each I2C attachment `peripheral(bus).unplug(addr)`, poll (bounded,
  tunable deadline) the supervisor's restart count for that task, `plug(addr)`, poll for a fresh reading (the reader's
  published value changes or its `TS` advances); FRAM: `chip.silent = True` … `False`. Ends by cancelling every task it
  started (`_async_harness.cancel_all`). No HTTP. Registers both reset hooks.
- **Resolved**: —
- **Unit**: U25
- **Depends**: M.TWIN.010-014, M.TWIN.024
- **Blast carried by**: SPEC F.2 → A.U14.38 (SPEC); README fault paragraph → M.TWIN.058
- **Kind**: test

## tests/test_digital_twin_http_client.py

### M.TWIN.118 HTTP client tests: refusal vs incomplete, timeout, consumption asserted, shared harness
- **From**: A.U25.31 (`b""` header terminator flips to `IncompleteResponseError`; new: close after `HTTP/1.1 200 OK\r\n
  Content-Length: 5\r\n` → `IncompleteResponseError`, reset before any byte → `CeilingRefusedError`, closed port → an
  `OSError` that is not `CeilingRefusedError`; `:85-101` holds), A.U25.51 (`:268, :273` assert the reader consumed exactly
  `n` and no request exceeded the chunk size; `:292, :297` assert EOF reached and each chunk requested once), A.U24.40
  (hands the two to A.U25.51), A.U24.08 (`:24` `run` → `_async_harness`, bounded), A.U8C.25 (`_RUN_BOUND_S = 5.0` tagged
  `l2.http_client_run_bound_s`; `_MID_BODY_PAUSE_MS = 20` tagged), A.U24.70 (the canned servers' 18099-18103 become a
  `tests/_port_bands.py` row), M.TWIN.016 (`timeout_s`)
- **Site**: `tests/test_digital_twin_http_client.py` (whole file)
- **Change**: imports `_async_harness.run`; `_RUN_BOUND_S`/`_MID_BODY_PAUSE_MS` constants with their tags at module top,
  every literal site uses them; the canned servers take ports from `PortAllocator("test_digital_twin_http_client")`; the
  header-parse tests: `parse_header_line(b"")` raises `IncompleteResponseError`; new cases per A.U25.31 and
  `fetch(..., timeout_s=0.1)` against a listener that never answers raises `asyncio.TimeoutError`; A.U25.51's four
  strengthened tests (the fake reader records each `readinto` request length and its remaining buffer). Trailer.
- **Resolved**: —
- **Unit**: U25 (stages U8C tags, U24 harness)
  A-C2 step order: A.U24.70's part lands in U25, not U24 (it follows A.U24.70's own change, which lands in U25).
- **Depends**: M.TWIN.016; M.TEST_HELP.056 (port bands)
- **Blast carried by**: —
- **Kind**: test

## tests/test_digital_twin_isl29125.py

### M.TWIN.120 ISL29125 fake tests: bounded PRST count, cited constants, grouped constructor, power cycle
- **From**: A.U25.14 ((4) the `:264-266` comment; new: under constant out-of-window light with no status read
  `_prst_count` stays at the PRST target after 50 cycles; persistence tests `:317-360` hold), A.U25.49 (`:10-27` register
  and bit constants cite FN8424 per line — `_ADDR_*` p9 Table 1, `_MODE_RGB`/`_RNG_HIGH`/`_BITS_12` p10 Tables 4-6,
  `_INTSEL_GREEN` p11 Table 11, `_STATUS_*` p12 Tables 16-19, `_DEVICE_ID` p9 Table 2), A.U15.30 (`:264-266` is U25's —
  carried by A.U25.14), A.U26.53 (the L2 equivalent unchanged — holds), A.U24.30 (`_FixedRandom` → `FixedRandom`),
  A.U5.15 (`lux=Walk(…)`), A.U25.62 (`ISL29125Chip`), M.TWIN.012 (`timer_factory`; `simulate_brownout()` →
  `power_cycle()`; a `writeto` hang on the probe; `key=` faults)
- **Site**: `tests/test_digital_twin_isl29125.py` (whole file)
- **Change**: constants cite FN8424 per line; `FixedRandom` imported; every construction `ISL29125Chip(..., lux=Walk(lo,
  hi, step))` and no `auto_refresh=` (the default builds no Timer); tests calling `simulate_brownout()` call
  `power_cycle()`; the `:264-266` comment → A.U25.14 (4)'s text; new `test_prst_count_stops_at_the_target` (50 cycles of
  `_produce_new_reading(walk=False)` with green outside the window, no status read → `_prst_count == target`), a probe
  `writeto` hang case, a `readfrom_mem` fault with `match=0x08`. Trailer.
- **Resolved**: —
- **Unit**: U25 (stage U24: `FixedRandom`)
- **Depends**: M.TWIN.012
- **Blast carried by**: L0 copy check `tests_scripts/test_isl29125_copies.py` → A.U25.49 (TSC)
- **Kind**: test

## tests/test_digital_twin_isl29125_autorange.py

### M.TWIN.122 Auto-range twin tests: plan-derived device and pins, in-process band codes, INT parking, re-arm
- **From**: A.U25.25 (`:58-60` hard-coded pins and `configure_i2c_wiring` → `device_with("isl29125")`'s plan and pins),
  A.U25.03 (`reset_peripherals()`), A.U25.49 (`:34-40` driver-derived values cite `src/asy_isl29125_driver.py` by constant
  name; `_CHIP_GAIN_RATIO` cites the chip default), A.U25.60 (band codes from `set_illumination()` scenes read in-process:
  inside → suitable, below → too dark, above → too bright, fixed range → not applicable, right after a switch → not
  applicable then suitable), A.U15.36 (dark/mid/bright → 2, 1, 3 — "through `GET /measurements`", see Resolved), A.U15.32
  (L2: a red-dominant scene on the high range with `SampleInterv` 5: over 20 s of twin time at most ⌈20/5⌉ + 2 cycles and
  the range stays high; the dead-line test `:292-307` holds), A.U15.R05 (L2: INT muted → re-arm → INT delivers), A.U2.12
  (`:96` W filter by catalog code), A.U3.14 (brownout tests assert no log — hold), A.U28.28 (`:96` B905 inline comment goes
  — the per-file entry is TOOL's), A.U36.020 (`:57` → "# A device carries this sensor only where its TOML declares an
  isl29125 instance (SPECIFICATION.md M.1.1 / # req 18)."), A.U15.39 (hands `:56` to U36 — carried by A.U36.020)
- **Site**: `tests/test_digital_twin_isl29125_autorange.py` (whole file)
- **Change**: device from `device_with("isl29125")`, its plan and bus pins; C4 boot; constants cite their sources;
  `:57` comment per A.U36.020; `:96` reads the W code through `code("W", <NAME>)`; new cases: A.U25.60's band-code
  scenes; A.U15.36's three scenes (2, 1, 3) read from the reader's published data in-process; A.U15.32's red-dominant
  scene counts reader cycles over 20 s of twin time (the twin Timer runs in real time: the test bounds it with a tunable
  `l2.` deadline and counts the reader's cycle counter, not HTTP); A.U15.R05's mute/re-arm (the chip's
  `configure_fault("isl29125:int_stuck_high", active=True)` then `False`). Trailer.
- **Resolved**: A.U15.36 phrases its L2 check "through `GET /measurements`"; G7/R19 and A.U25.46 put request driving
  host-side, and A.U25.60 (same file, same codes) reads "the reader's published data (in-process)" — the end state reads
  in-process; the GET form is the host harness's measurements scenario (A.U25.46).
- **Unit**: U25 (stage U15: A.U15.32/.36/.R05 cases written on the HEAD harness; U25 rebases them on C4)
  A-C2 step order: A.U2.12's part lands in U3, not U2 (it follows A.U2.12's own change, which lands in U3).
- **Depends**: M.TWIN.012, M.TWIN.024; `tests/_twin_devices.py`
- **Blast carried by**: `pyproject.toml` B905 per-file entry → A.U28.28 (TOOL)
- **Kind**: test

## tests/test_digital_twin_launch.py

### M.TWIN.124 Launcher tests: the new vocabulary and fault spec, required plan, persistent defaults, grouped config
- **From**: A.U25.37 (`:33-75` vocabulary parse tests follow the new tables, instance keys), A.U25.70 (parse tests gain
  `MATCH`), A.U25.27 (`wlan:…:TIMES` refusal flips to acceptance), A.U25.18 (`:41` every documented device/op parses —
  `fram` `readinto|wren|silent`), A.U25.25 (`parse_args` tests: `--wiring-plan` required), A.U25.32 (the defaults test,
  grep `fram_state_path`, flips to the persistent paths), A.U25.41 (parse tests hold with the shared `_pop_value`),
  A.U5.15 (`:212-258` `LaunchConfig(state, injections, …)`), A.U8.08 (`:216, :261` comments quoting 8000 ms → name
  `wdt.timeout_ms`), A.U8C.26 / A.U8C2.09 (`_SHORT_DURATION_S`, `_MAIN_BOUND_S`, `_FAULT_DURATION_S`, `_LONG_DURATION_S`,
  `_LONG_MAIN_BOUND_S`, `_LONG_MIN_READINGS` with their `l2.launch_*` tags), A.U8C.120 (`:230` Dependant of
  `l2.twin_wifi_connect_delay_s`), A.U7.19 (`--help` exits 0 — its L0 test is TSC; one L2 case here: `parse_args(["--help"])`
  raises `SystemExit(0)`), A.U30.19 (the `stack` form, gap pass G3)
- **Site**: `tests/test_digital_twin_launch.py` (whole file)
- **Change**: the six module constants with their tags; vocabulary tests iterate `launch._FAULT_DEVICE_OPS` and
  `_HANG_DEVICE_OPS` (no copied list); new parse cases: `scd30_x:writeto` resolves to `scd30` (`_driver_of`),
  `uart_link_init:silent` resolves to `uart_link`, `fram:silent:2` and `isl29125:int_stuck_high:0x08` refused,
  `scd30:readfrom_into:3:0x0300` → `(…, 3, 0x300)`, `wlan:status:2` accepted, `fram:write` refused;
  `sgp40:readfrom_into:stack`
  parses as one `stack` fault, `sgp40:readfrom_into:stack:0x260F`, `wlan:status:stack` and `fram:silent:stack` refused;
  applied to a chip, the next `readfrom_into` raises `RuntimeError` whose message equals `asy_print_log._STACK_EXHAUSTED`
  (read from `src/` by `src_const`) and the one after it does not; `parse_args([])`
  raises "--wiring-plan PATH is required"; defaults equal `StatePaths("digital_twin/fram_state.json",
  "digital_twin/scd30_state.json", "digital_twin/mem_backup_state.json")`; main-run tests pass a generated plan path
  (`build/generated_src/sensortask_<device>_wiring_plan.json` for `device_with("bmp3xx")`) and `""` state paths, assert
  `summary["readings"] >= _LONG_MIN_READINGS`; comments `:216, :261` name `wdt.timeout_ms`. Trailer.
- **Resolved**: —
- **Unit**: U25 (stages U5, U8C; U30 the `stack` cases)
- **Depends**: M.TWIN.044-046
- **Blast carried by**: —
- **Kind**: test

## tests/test_digital_twin_machine.py

### M.TWIN.126 Twin `machine` tests: the shared contract, Pin, buses, general call, probe, fill, WDT, reset, logs
- **From**: A.U24.17 (runs `tests/_machine_contract.py` `ALL_CHECKS` against `digital_twin/machine.py`), A.U25.02 / .05
  (Pin L2 lists), A.U25.03 (per-id I2C/SPI list), A.U25.06 (short chip reply into `bytearray`/`memoryview`), A.U25.10
  (`:140-142` asserts the wired SGP40's `resets` +1 and the BMP3XX on the same bus kept OSR/CONFIG; a general call with no
  SGP40 raises `EIO`), A.U25.12 (`:207-223` CRC-correct frame — holds), A.U25.16 (SPI LSB refused, default MSB), A.U25.17
  (empty write to an absent address `ENODEV`, one byte `EIO`, a queued `sgp40:writeto` EIO fault then `writeto(0x59, b"")`
  `ENODEV`), A.U25.22 (`BoundedLog` cap/`dropped`/order; WDT log `dropped == n - 200`), A.U25.23 (each counter at
  `COUNTER_CAP` stays), A.U25.24 (each hook raises after a construction and passes after `reset_peripherals()`; `:134`,
  `:231` post-construction resets → `reset_peripherals()` first), A.U25.25 (`:135-200` pins from the plan; `:161-194`
  `configure_i2c_wiring` → `configure_wiring(wiring_plan(...))`), A.U25.51 (`:142` → A.U25.10's assertions), A.U25.52
  (identity `:178-180` holds), A.U24.12 (`:200-236` uses a `TmpScratch("dtmachine")` path and restores `sys.path`),
  A.U24.30 (`:119` `_FixedRandom` → `FixedRandom`), A.U36.020 (`:162-163` → "# A device carries this sensor only where
  its TOML declares an isl29125 instance."), A.U15.39 (hands `:161` to U36 — carried by A.U36.020), A.U8.08 (WDT
  construction inputs 8000/8388/8389 — facts; short timeouts tuned), A.U8C.27 / A.U8C2.10 (the `l2.machine_*` constants:
  `_WDT_SHORT_TIMEOUT_MS = 150`, `_WDT_POLL_MS = 5`, `_RUN_BOUND_S = 5`, `_WDT_FED_TIMEOUT_MS = 100`, `_FEED_STEP_MS = 20`,
  `_DOUBLE_TRIGGER_BOUND_S = 8`, `_TIMER_PERIOD_MS = 20`, `_BEFORE_DEINIT_MS = 60` and A.U8C.27's remaining rows as it
  lists them, `_WDT_POLL_TRIES = 200`,
  `_FEED_ROUNDS = 6`, `_WDT_SECOND_NOTICE_POLL_TRIES = 600`, `_CHAIN_POLL_TRIES = 100`, `_FIRE_POLL_TRIES = 100`, each
  tagged), A.U10.12 (`:475-500` keeps its twin-fidelity goal; its comment stops naming the product sequencer), A.SDEP.08
  (`:319` version-stamped claim re-read), M.TWIN.001 (`fill_buffer`), M.TWIN.031 (`feed_times`), M.TWIN.019/.033 (RTC and
  wall clock cases — M.TWIN.128), M.TWIN.035 (`reset_test_state()`)
- **Site**: `tests/test_digital_twin_machine.py` `:1-330` (module setup, Pin, buses, general call, wiring, WDT)
- **Change**: module setup: `sys.path` gains `digital_twin` (kept) and the `microtest.after_each(machine.reset_test_state)`
  registration; `from _machine_contract import ALL_CHECKS` and one test per check calling it with the twin module (the
  contract's `make_injector` factory for `check_inject_fault_fifo` builds a chip's `FaultInjector`); every bus test
  takes its pins from `wiring_plan(device_with(...))["pins"]`; the cases listed under From, each one test with an exact
  assertion; the tagged constants at module top; the `:162-163` comment; `:200-236` on the scratch path. The Timer, RTC,
  reset and mem-backup cases are M.TWIN.128 (same file, separate merged change for size).
- **Resolved**: —
- **Unit**: U25 (stages U8C/U8C2 tags, U24 scratch/contract/`FixedRandom`, U36 comment)
- **Depends**: M.TWIN.020-036; `tests/_machine_contract.py` (M.TEST_HELP, A.U24.17)
- **Blast carried by**: —
- **Kind**: test

### M.TWIN.128 Twin `machine` tests, runtime half: Timer pool and schedule, reset exceptions, mem_backup, RTC
- **From**: A.U25.19 (`:460-520` hold; `:505` asserts the alarm returned to the pool; pool+1 → ENOMEM; `deinit()` frees one;
  a re-arm inside the callback runs one loop — 3 calls over three periods; `freq=10` → 100 ms; `Timer(0)` → `ValueError`; a
  soft PERIODIC raising once still runs its second; a hard one stops and frees), A.U25.51 (`:505` → that assertion),
  A.U25.07 (`:420-450` hold; `not issubclass(SimulatedRebootError, Exception)`; a Timer calling `machine.reset()` makes
  `asyncio.run()` raise `SimulatedResetError` while an `except Exception` sibling keeps nothing alive; then
  `asyncio.new_event_loop()`), A.U25.08 (sizes 4 and 3 words; identity; `-1` tuple; `2`/`-2` raise; `power_on()` clears;
  flush + configure round trip restores regions and cause 3 and deletes the file; a missing, malformed or wrong-length
  file leaves power-on; runs `tests/_mem_backup_contract.py`), A.U25.20 (`:451-455` holds; setter returns `None`; `RTC(0)`
  → `TypeError`; a 7-tuple → `ValueError`; a wrong weekday reads back corrected), A.U25.71 / M.TWIN.019 (installed clock
  cases), A.U25.23 (`reset_count`, `bootloader_count` at the cap)
- **Site**: `tests/test_digital_twin_machine.py:420-539`
- **Change**: the cases under From, one test each, using the tagged poll/bound constants of M.TWIN.126 and
  `_async_harness.run(coro, _RUN_BOUND_S)`; every test that drives a reset catches `machine.SimulatedRebootError` and
  calls `asyncio.new_event_loop()` before returning; `set_alarm_pool_free()` restored by `reset_test_state()`.
- **Resolved**: —
- **Unit**: U25
- **Depends**: M.TWIN.019, M.TWIN.030-035
- **Blast carried by**: —
- **Kind**: test

## tests/test_digital_twin_machine_uart.py

### M.TWIN.130 Twin UART tests: one static object per id, the contract via `poll_mask`, overflow, bounded settle
- **From**: A.U25.04 (`:28-43` supersede test → `test_a_second_construction_on_one_bus_id_returns_the_same_live_object`
  (same object, settings replaced, rx queue emptied, link still delivering); `make_link()` `:16-20` and `:49, :67` call
  `machine.reset_peripherals()`), A.U24.80 (`:24` the contract via `poll_mask`), A.U24.06 (the contract's completeness
  — holds), A.U25.22 (4097 bytes in flight → `dropped_overrun == 1`), A.U25.23 (`offered`/`delivered`/`dropped_overrun`/
  `would_have_blocked_bytes` at the cap stay), A.U25.30 (`settle()` inside a coroutine raises `RuntimeError`; 64 bytes at
  1200 baud settle no earlier than their wire time, with a bounded count of `_advance()` calls), A.U8C.28 (its tags),
  A.U13.12 (a `readline(n)` with fewer queued counts `n - queued` — the contract's new check), A.U13.13 (`txdone()` True),
  M.TWIN.028 (ioctl `-EINVAL` for `MP_STREAM_GET_FILENO`); OR141.a (4) (g) (the twin DMA model's own cases; A-C review
  fold)
- **Site**: `tests/test_digital_twin_machine_uart.py` (whole file)
- **Change**: as listed; UART constructions pass rp2-valid TX/RX pins from the plan; a new `test_ioctl_answers_einval_
  to_get_fileno` (`uart.ioctl(10, 0) == -errno.EINVAL`) and `test_a_buffer_below_32_is_clamped`; the `l2.machine_uart_*`
  tags per A.U8C.28. New (M.TWIN.169, U13 stage): the shared contract's DMA checks run on the twin fake and
  `test_the_finaliser_aborts_the_channel`; with M.TWIN.170 (U25): `test_the_dma_keeps_filling_the_ring_through_a_flash_
  stall` (bytes in flight across a modelled flash write: the ring holds every byte afterwards, UARTRSR OE clear) and
  `test_a_set_mask_overflows_the_fifo_inside_a_flash_stall` (RXIM left set, the same stall: OE set, bytes past 32 lost).
  Trailer.
- **Resolved**: —
- **Unit**: U25 (stage U8C; stage U13: the contract's DMA checks and the finaliser case, with M.TWIN.169)
- **Depends**: M.TWIN.027-029, M.TWIN.169, M.TWIN.170 (the two stall cases)
- **Blast carried by**: `tests/_uart_link_contract.py` (`poll_mask`, `readline(size)` check) → A.U24.80/A.U13.12 (TEST_HELP)
- **Kind**: test

## tests/test_digital_twin_bus_hazard_concurrency.py

### M.TWIN.102 Twin bus-hazard tier: devices from data, real recovery rungs, general call that resets, no in-DUT HTTP
- **From**: A.U25.48 (device choice from data, `test_wozi_*` names drop the device) as amended by A.U36.015 (A-C: loop over
  every device whose TOML puts two or more occupants on one bus, each case taking that device's own occupants; FRAM's
  same-device hazards and the WiFi-disconnect scenario run on one data-chosen device, naming that reason), A.U25.46 (the
  `_api_burst_at_the_ceiling()` half `:90-111` moves to the host harness; the bus-load half stays, no HTTP), A.U25.51
  (`:107` route set — moot once the burst moves; the host harness reads every registered GET route, A.U19.20/A.U24.36),
  A.U24.34 / A.U25.31 (`:99-104` classifier → moves with the burst), A.U25.22 (`_run_real_task_graph_and_assert_healthy()`
  asserts `shared_bus_log.dropped == 0` before its `:156` membership check; the `:368-370` comment says the helper checks
  its window), A.U25.10 (the general-call scenario now resets the twin SGP40 for real; reads after it re-checked: a read
  returns the zero reply until the next measure), A.U15.R02 (L2: heater-off on the twin concurrent with the SCD30 read loop
  on a shared bus across offsets), A.U25.11 (its L2 case authored by A.U15.R02 — here), A.U15.R01 (L2: the SCD30 soft reset
  issued while SGP40/ISL29125/BMP3XX read loops run on the same bus leaves every sibling read valid), A.U13.R02 (3) (the
  held-SDA/controller-rung scenario on the twin chips, plus two ladder cases: (a) a sustained fault on one chip until
  its reader persists wrnno 15, then the fault FIFO cleared and the reader returns; (b) as its text), A.U25.05 (its
  clear/recover cases run on the twin Pin), A.U12.18 (new: three concurrent `measure_raw()` with distinct T/RH on the twin
  SGP40, each 8-byte `writeto` followed by its own read in `I2C.log`, words matching one session each), A.U15.32 (ISL29125
  concurrency runs unchanged), A.U15.S01 / A.U15.25 / A.U15.33 / A.U13.07 / A.U13.10 / A.U16.10 / A.U30.07 / A.U15.12 /
  A.U26.32 / A.U35.21 (run unchanged and must pass — hold), A.U16.19 (`:414-432` refused write checked after unpausing;
  `:463-464` the WP-vs-override assertion goes, the WP read refusal stays asserted unpaused), A.U25.57 (new case beside
  `:501-530`: per device with FRAM, `mempause` through the generated `SystemCmd` dispatch in-process arms the 300 s unpause
  Timer (read from the manager); a 2 s pause through the manager's own entry drops a logger write, then after the
  one-shot `get_pause()` is false and the next write lands; no read or clear deferred), A.U25.50 (`:364` comment head →
  "# Recombination test (owner, 2026-09-04): the fully wired system tolerates a genuine 60 s wifi_mode_lock hold while
  concurrent bus load …"), A.U35.09 (nothing added here; `:363`'s owner tag is A.U25.50's — holds), A.U20.02 (13
  `build_system()`/`main()` calls pass `watchdog=`; `:115-133, :378-393` read the WDT they passed), A.U20.06 / A.U10.12 /
  A.U32.06 (`:118`, `:387` `start_timers()` two lists; `:119`, `:388` `start_tasks(…, task_names=…)`), A.U10.44 (starter
  names), A.U15.R04 (L2: the ISL29125 participant rung's mid-operation case, "as A.U15.R01"; M.TEST_UNIT.061's blast,
  gap pass G3), A.U25.03 / .24 / .25 (`reset_peripherals()` before each build — `:514`, `:524` simulated-reboot build;
  `:179-508` twelve `configure_i2c_wiring` → `configure_wiring(wiring_plan(...))`), A.U25.33 (offline NTP config per
  boot), A.U24.08 (`:44` `run`, `:65` `_cancel` → `_async_harness`), A.U24.70 (`:51` port allocator → `PortAllocator`),
  A.U8C.24 / A.U8C2.08 (`_WDT_FEED_INTERVAL_S` `l2.twin_wdt_feed_interval_s`, `_RUN_BOUND_S`, `_API_RUN_BOUND_S` (moot with
  the burst — its row closes), `_ESTABLISHED_POLL_S`, `_RUN_SECONDS = 9.0` and A.U8C.24's remaining rows as it lists them), A.U8.15 (the `-X heapsize` row cites
  this file's dev scenario — holds), A.U10.18 (lock renames in assertions), A.U11.24 / A.U4.02 (`:384` config writes
  follow the new `write_config` signature), A.U36.512 (`:112` "for both variants" → "for every device"), A.U36.544
  (comment pointers), A.U28.28 (`:…` bare E402 gains its reason), A.SDEP.08 (`:475` version-stamped claim re-read),
  A.U35.50 (the four-tier conformance row reads this file), A.U19.20 (`:107` route tuple — moot, moves host-side),
  A.U24.27 / A.U24.29 (the twin counterpart is A.U13.R02's — this change), C2, C4
- **Site**: `tests/test_digital_twin_bus_hazard_concurrency.py` (whole file)
- **Change**: module setup per C4 (prewarm, shim, both reset hooks); `_DEVICES_SHARED = devices_with_shared_bus()` (each
  `(device, bus, occupants)`), FRAM/WiFi cases on `device_with("fram")` with a one-line reason; tests renamed
  `test_<scenario>` and parametrised by a loop over the derived set (one assertion message names the device);
  `_run_real_task_graph_and_assert_healthy(module, watchdog, shared_bus_log, run_seconds)` drops `api_port` and the
  burst (the two `…_api_burst_during_bus_load` tests become host scenarios — SCR, A.U25.46 — and leave this file); its
  per-driver health check stays TOML-driven (the hard-coded SGP40/BMP3XX/SCD30 asserts go: the plan loop covers every
  occupant); `assert shared_bus_log.dropped == 0` precedes the general-call membership check; the general-call scenario
  asserts the SGP40's `resets` rose and its next measure after a reset answers; new cases: A.U15.R02's heater-off
  interleave, A.U15.R01's soft-reset interleave, A.U15.R04's re-apply interleave (on every device from
  `devices_with_shared_bus()` whose occupants include an ISL29125: the reader's re-apply rung — CONFIG1-3 from the shadow,
  thresholds re-armed — driven at each offset while the bus's sibling read loops run; every sibling read valid, the chip's
  configuration registers equal the shadow), A.U13.R02's ladder cases (a)/(b), A.U12.18's three-session measure,
  A.U25.57's pause cases; FRAM WP/pause cases per A.U16.19; tagged constants at module top; every reset-reachable
  case catches `SimulatedRebootError` and calls `asyncio.new_event_loop()`. The `:364` owner tag per A.U25.50.
- **Resolved**: A.U25.48 (1) picks one device for the SGP40+BMP3XX pair; A.U36.015's Blast states "A-C amends A.U25.48 (1)
  to loop over every device whose TOML puts two or more bus occupants on one bus (`devices_with_shared_bus()`)" — settled
  by that text (V24). A.U25.51 and A.U24.36 edit `:107`, which A.U25.46 moves host-side — their content travels with the
  burst (GAP-H2, SCR). The `_API_RUN_BOUND_S` row (A.U8C.24) closes with the burst's move (C3).
- **Unit**: U25 (stages: U8C tags, U13/U15 L2 cases on the HEAD harness, U16 pause edits, U20 `watchdog=`, U24 harness)
  A-C2 step order: A.U24.70's part lands in U25, not U24 (it follows A.U24.70's own change, which lands in U25).
- **Depends**: M.TWIN.014, M.TWIN.021, M.TWIN.024, M.TWIN.035; `tests/_twin_devices.py` `devices_with_shared_bus()`
  (TEST_HELP gap)
- **Blast carried by**: `tests/_twin_devices.py` gains `devices_with_shared_bus()` → TEST_HELP gap; the API-burst
  scenario host-side → A.U25.46 (SCR); SPEC C.8 per-device paragraph → A.U36.015 (SPEC)
- **Kind**: test

### M.TWIN.104 Twin bus-hazard tier, system commands: erase vs logger write, cancelled session, watchdog on the erase
- **From**: A.S0930.27 (3) (in this file: the erase racing a logger write on the twin chip — in-flight completes, later
  refused, no torn chunk; a sensor task cancelled inside its I2C session on a shared bus — the sibling's next read
  succeeds; the twin chip's rollover never reached), A.S0930.27 (4) (healthy: the dev-layout erase with
  `wire_time_us_per_byte = 8` ends with `would_have_triggered_count == 0`; a blocking hang inside one SPI transfer (the knob
  set for a 9 s transfer) is caught by `_arm()`'s late-feed backstop at the next own feed), A.S0930.38 (5) (in-process: stop
  at the armed reset (`_reset_armed` True) before the Timer fires; then from outside `sysfunct._reset_timer.deinit()`,
  `sysfunct._reset_task.cancel()` and the `supervise_tasks()` task's cancel, each awaited), A.S0930.27 (0) (FRAM evidence
  first: a copy of the twin chip's memory into the test's scratch before the command), A.U25.15 (rollover, `silent`,
  WREN-drop); OR140.a (12) (no SCD30 write while a system-command sequence runs, proven at L2 too), OR138.a (1)-(2)
  (`ConfigFaults`, the never-reading delete) and OR136.a (1) (the defaults written once at the next boot) — A-C review
  fold
- **Site**: `tests/test_digital_twin_bus_hazard_concurrency.py` (new section "system commands")
- **Change**: three cases on `device_with("fram")` (FRAM alone on its bus — stated) and one on a shared-bus device:
  `test_erase_racing_a_logger_write_never_tears_a_chunk`, `test_a_sensor_task_cancelled_inside_its_session_leaves_the_bus_
  usable`, `test_the_erase_feeds_the_watchdog_at_bus_speed` (knob 8 µs/byte; asserts `would_have_triggered_count == 0` and
  every unit address below `size`), `test_a_hung_spi_transfer_is_caught_by_the_late_feed_backstop`; each stops at the
  armed reset and tears down as A.S0930.38 (5) states; before each command the chip memory is copied into the test's
  `TmpScratch` (the FRAM-log rule, twin case). Two more on `device_with("scd30")` (A-C review fold):
  `test_no_scd30_write_reaches_the_chip_while_a_system_command_runs` — first, with the graph's tasks and timers running a
  window that covers every SCD30 cycle, the twin chip's NVM write counter (`Scd30Chip.nvm_writes`, M.TWIN.013) does not
  move; then for each of the four words in turn, from acceptance to the armed reset, every SCD30 setter field sent through
  the webserver's own in-process dispatch (the path the REST handler takes, G7/R19) at each step the sequence awaits
  answers "Failed" and the counter does not move; `test_a_damaged_config_file_is_repaired_listed_then_deleted_and_rewritten_once` —
  a corrupt-JSON `config_SYSTEM.cfg` planted in the run's config dir before the boot: the boot's one write repairs it
  (valid JSON at its defaults) and the system status data the `/status` route serialises still lists `"SYSTEM"` in
  `ConfigFaults`; `resetconfig` reaches the armed reset with no schema-backed file
  left (none read); a second boot over the same dir writes each file once with its defaults (OR136.a (1)) and
  `ConfigFaults` is `[]`.
- **Resolved**: —
- **Unit**: U25 (co-lands with SUPP_owner_0930, AC_NOTES 34/36). The two A-C review fold cases land in U25 too: OR138.a's
  L2 half comes after its U20 product and L0/L1 halves because this file's system-command section and its C4 boot are
  born here (reason recorded; nothing in U20 needs them).
- **Depends**: M.TWIN.011, M.TWIN.013, M.TWIN.026, M.TWIN.031; M.SRC_CORE controlled-shutdown sequence (`_reset_armed`,
  `_reset_task`, `_reset_timer`); M.SRC_CORE.011, M.SRC_CORE.038 (every API command, the SCD30 setters
  included, refused while a sequence runs); M.SRC_CORE.043, M.SRC_CORE.015, M.SRC_CORE.042 (the fault state, the never-reading delete); M.GEN.008, M.GEN.014 (`ConfigFaults` in the status data)
- **Blast carried by**: —
- **Kind**: test

## tests/test_digital_twin_construction_<device>.py (six, deleted) → tests/test_digital_twin_construction.py (new)

### M.TWIN.108 One per-device construction file replaces the six wrappers
- **From**: A.U24.65 (2) (the six wrappers replaced by `tests/test_digital_twin_construction.py` with
  `globals().update(register_for_device(os.getenv("TEST_DEVICE")))`, `PER_DEVICE = True`, raising at import without
  `TEST_DEVICE`), A.U25.43 (the entry file, not the library, carries the prewarm and shim calls), A.U25.34, C4, A.U24.04
  (trailer)
- **Site**: `tests/test_digital_twin_construction_{arzi,dev,grkizi,klkizi,schlafzi,wozi}.py` (deleted); new
  `tests/test_digital_twin_construction.py`
- **Change**: the new file: header (≤ 3 lines) "Digital-twin construction, wiring and boot checks for the device named by
  TEST_DEVICE - one job per generated device, dispatched by scripts/test.sh (SPECIFICATION.md E.2.1)."; `sys.path` gains
  `digital_twin` and `digital_twin/unixport`; module level `prewarm_poll_set()` then `patch_asy_udp_socket_for_unix_port()`;
  `PER_DEVICE = True`; `device = os.getenv("TEST_DEVICE")` with the import-time `RuntimeError("run through scripts/test.sh,
  or set TEST_DEVICE to one of devices/*.toml")` when unset; `globals().update(register_for_device(device))`; the
  canonical trailer.
- **Resolved**: —
- **Unit**: U24 (A.U24.65; the prewarm/shim lines move to the new file in U24 already, as the wrappers carry them — the
  wrappers at HEAD carry none because the library prewarms; A.U25.43 (U25) moves the call out of the library into this
  entry file)
  A-C2 step order: A.U24.65's part lands in U25, not U24 (it follows A.U24.65's own change, which lands in U25).
- **Depends**: M.TEST_HELP.029 (the library's `register_for_device`), M.TEST_HELP.055
- **Blast carried by**: `scripts/test.sh` per-device expansion → A.U24.65 (3) (SCR); the twin pass `files` glob picks it
  up (M.TWIN.075)
- **Kind**: test

## tests/test_digital_twin_network_neopixel.py

### M.TWIN.132 Twin network and NeoPixel tests: singletons, cyw43 status rules, AP address, byte store, structural waits
- **From**: A.U25.27 (`reset_interfaces()` before isolated constructions; singleton identity, `WLAN(5) is WLAN(AP_IF)`,
  counts per interface, `deinit()` resets link state and takes the STA link down from the AP, `raise_on` with `times=2`
  raises twice then stops; `:156-165` holds with `times=None`), A.U25.26 (`:66-70` → rssi on STA, stations on AP, the three
  raises; `_CONNECT_DELAY_S` < the service's poll budget, read through its module attribute or an L0 AST read), A.U25.72
  (AP `ifconfig()[3]` equals the STA's; config truncation; A.U18.30's deactivated-radio LED pattern on the twin NeoPixel),
  A.U18.30 ("U25 may add the L2 case" — added), A.U25.21 (`:291-323` frames compared as `bytes` or read back through
  `__getitem__`; `(256, 0, 0)` → `(0, 0, 0)`; `(1.5, 0, 0)` raises; `(10, 1.5, 0)` raises leaving G = 10), A.U25.22
  (`:79-90, :276-289, :302-312` bounded-size tests gain `dropped == n - 200`), A.U35.14 (1) (`:149`, `:251` negative
  windows become structural: after `disconnect()`, one `await asyncio.sleep(0)`, the kept connect task is `done()` and
  awaiting it raises `CancelledError`), A.U8C.29 (`_WAIT_TIMEOUT_S`, `_POLL_MS` tagged; the `l2.network_neopixel_never_
  connects_wait_s` row closes — the wait is gone, C3), A.U8C.120 (that row's Dependant note — closes with it), A.U31.13
  (real-time NeoPixel — holds), A.U28.28 / A.U28.29 (S106 reason line above the file's per-file entry — TOOL), M.TWIN.040
  (`raise_on` stores type and args; seeds `"XX"`/`"PicoW"`), A.U22.01 (new L2: a booted device whose NeoPixel signal task
  ends on the twin fake's `raise_on_write` restarts and leaves the pixel dark with the overlay restored; carried by no
  TWIN
  change — gap pass G3)
- **Site**: `tests/test_digital_twin_network_neopixel.py` (whole file)
- **Change**: every isolated `WLAN(...)` test starts `network.reset_interfaces()`; `raise_on` set with
  `(OSError, (errno.EIO, "m"), times)`; the cases listed under From; the seed test asserts `network.country() == "XX"` and
  `hostname() == "PicoW"` before any product call; the NeoPixel tests use the bytearray model; both reset hooks
  registered; trailer. New `test_a_restarted_signal_task_ends_dark_with_the_overlay_restored` (A.U22.01; C4 boot of the
  first generated device, its plan wiring the NeoPixel): overlay on, a signal requested, the twin pixel's `raise_on_write`
  set mid-ramp so the signal task ends, then cleared; the supervisor restarts the task; the pixel's writes after the
  restart are black, then the overlay colour, and no frame of the old ramp colour follows; SYSTEM persisted exactly one
  task-end entry. Bounded by a condition wait on the pixel's writes, never a fixed sleep.
- **Resolved**: A.U35.14 removes the wall-clock waits `:149`, `:251` that A.U8C.29's row `l2.network_neopixel_never_connects_
  wait_s` tags — the later action wins and the row closes (C3, A.U8C.120's Dependant note with it).
- **Unit**: U35 (stages: U8C tags, U25 the fake cases and the A.U22.01 case — its product half is U22's)
- **Depends**: M.TWIN.040, M.TWIN.042
- **Blast carried by**: `pyproject.toml` S106 per-file reason → A.U28.28/A.U28.29 (TOOL)
- **Kind**: test

## tests/test_digital_twin_poll_prewarm.py

### M.TWIN.134 Prewarm tests: canonical trailer, the returned sockaddr typed `object`
- **From**: A.U24.04 (`:11` `from microtest import run` at the top and `:142-143` `run(globals())` → the canonical
  trailer), A.SDEP.16 (W12: the file is deleted if `extmod/modselect.c` is fixed at the refreshed pin — conditional),
  A.U25.63 (`prewarm_poll_set()` returns `object`)
- **Site**: `tests/test_digital_twin_poll_prewarm.py:11, 142-143`
- **Change**: per A.U24.04; no assertion relies on the return value being a tuple; the 17400 band is the
  `tests/_port_bands.py` row.
- **Resolved**: —
- **Unit**: U24 (stage U25 for the return type)
- **Depends**: M.TWIN.057
- **Blast carried by**: L0 trailer check → A.U24.04 (TSC)
- **Kind**: test

## tests/test_digital_twin_real_website_integration.py (deleted)

### M.TWIN.136 The real-website checks move to the host harness; the file goes
- **From**: A.U25.46 (2) (its 9 HTTP tests `:98-345` move to `scripts/_digital_twin_scenarios.py`, goals and assertions
  kept), A.U25.48 (one device: the one `scripts/test.sh` built the site for, read from the bundle; `:120-128` comment),
  A.U25.45 (`:75` readiness poll), A.U25.33 / A.U25.03 / A.U25.25 / A.U20.02 / A.U24.70 (boot discipline), A.U8C.30 (tags),
  A.U36.004 (5) (`:69-71` comment), A.U36.512 (`:134` "exemplary base device"), A.U24.01 (`:26-27` `_PHASE_*` mirrors →
  `_src_const`), A.U24.60 (`:150` strict loads of the definitions), A.U27.03 (`:87-95` `DeflateIO` without `with` and its
  ignore), A.U23.47 (its `Any` sweep is U25's — moot), A.U8.18 (`:305` comment names the figure), A.U24.08, A.SDEP.07 (the
  archive-format change's L2 coverage), A.U36.517 (SPEC E text naming this file's mechanism)
- **Site**: `tests/test_digital_twin_real_website_integration.py` (whole file, deleted)
- **Change**: `git rm` in U25 once the harness carries its nine scenarios (A.U25.46); every content item above that
  applies to the moved scenarios is carried into the harness (SCR gap, GAP-H2's list extended by: the one-device choice
  from the built bundle, the `:150` strict definitions read, the concurrent page-load figure's tag). The in-process
  helpers `_boot`/`_start_webserver`/`_cancel` go with it. Edits made to this file in U8C/U20/U24 (tags, `watchdog=`,
  harness imports, mirrors) are made in their units (the file exists until U25) and removed with it.
- **Resolved**: A.U25.46 (U25) moves every test the U8C/U20/U24/U27 constituents edit; those edits land in their own
  units and the U25 deletion supersedes them — no conflict. A.U36.517 (U36) describes the L2 proof as this file "boots that
  device's generated object graph against the twin's buses and drives real HTTP" — after U25 the proof is the harness
  scenario (a runner subprocess serving the built site): SPEC gap.
- **Unit**: U25
  A-C2 step order: A.U24.70's part lands in U25, not U24 (it follows A.U24.70's own change, which lands in U25).
- **Depends**: A.U25.46 (harness, SCR)
- **Blast carried by**: harness scenarios → A.U25.46 (SCR gap with the listed items); SPEC E/H build-chain proof text →
  A.U36.517 (SPEC gap); `pyproject.toml`/`typecheck.ini` scope by glob (no entry)
- **Kind**: test

## tests/test_digital_twin_rp2_constants.py (new)

### M.TWIN.138 One L2 file pins every rp2 value the twin models
- **From**: A.U25.68 (one assertion per constant, the expected value typed from the cited source with the citation
  beside it), A.U25.08 (`PWRON_RESET`, `WDT_RESET`, region sizes), A.U25.19 (pool size, Timer defaults), A.U25.21
  (NeoPixel `ORDER`), A.U25.02/.05 (Pin constants and names), A.U25.16 (`SPI.MSB`/`LSB`), A.U25.04 (UART bounds), M.TWIN.031
  (WDT cap), M.TWIN.040 (STAT constants, seeds), M.TWIN.011 (`_OVERRUN_MIN_READ` equal to `_SPI_DMA_MIN_SIZE`)
- **Site**: new `tests/test_digital_twin_rp2_constants.py`
- **Change**: header (≤ 3 lines) "Pins every rp2 constant the twin models to the value its cited v1.29.0 source line holds;
  a pin move that changes one fails here and names the line to re-read (CLAUDE.md's re-check practice)." One test per
  constant: Pin `IN/OUT/OPEN_DRAIN/ALT/PULL_UP/PULL_DOWN/ALT_I2C/IRQ_FALLING/IRQ_RISING`, `SPI.MSB/LSB`,
  `machine._SPI_DMA_MIN_SIZE`, `UART._MP_STREAM_POLL/_MAX_BUFFER_SIZE/_MIN_BUFFER_SIZE/_UART_INVERT_MASK/_DEFAULT_BAUDRATE`,
  `_WDT_TIMEOUT_MAX_MS`, `_ALARM_POOL_SIZE`, `PWRON_RESET`, `WDT_RESET`, `len(mem_backup(0)) == 4`, `len(mem_backup(1)) == 3`,
  `NeoPixel.ORDER`, the `network.STAT_*` values and power-on seeds; each expected literal carries its source line in a
  trailing comment. Trailer.
- **Resolved**: —
- **Unit**: U25
- **Depends**: M.TWIN.021-042
- **Blast carried by**: README "Pinned constants" → M.TWIN.059
- **Kind**: test

## tests/test_digital_twin_run_generic_integration.py

### M.TWIN.140 Runner tests: grouped config, plan-driven chip lookup, prewarm first, generated device, handler helpers
- **From**: A.U25.43 (1) (prewarm then shim at module level), A.U25.28 (`_collect_chips` tests construct twin buses and pass
  the plan), A.U5.15 (`:56`, `:234` grouped `RunConfig`), A.U25.32 (`test_parse_args_minimal_valid_config` holds — both
  sides default; the boot test passes `""` state paths), A.U25.37 (`_require_wired` tests hold; instance keys), A.U25.41
  (parse tests hold), A.U25.48 (`:48` placeholder `"sensortask_x"`; `:235-236` first `generated_devices()` entry), A.U24.56
  (`:1-2` → "boots a generated module through the generic entry point"; `:136-138`, `:218-220` drop retired runner
  names), A.U36.513 (same lines — A.U24.56's), A.U20.02 (`:249` reads the WDT it passed), A.U20.28 (plan reader), A.U24.08
  (`:29` harness), A.U24.46 (`require_fresh()` at import), A.U24.70 (`:238` inline 19099 → `PortAllocator` band), A.U8.14
  (`:112` `gc.threshold_bytes` mirror site), A.U8C.31 (`_RUN_BOUND_S`, `_MAIN_RUN_BOUND_S` tagged), A.U15.R02 (`:80`
  `sgp40:writeto:2` re-derives — the expected counts follow A.U25.36's failure-event form), A.U25.09 (L2 in-process only
  the handler's pure helpers), M.TWIN.051 (`TestFlags` parse cases)
- **Site**: `tests/test_digital_twin_run_generic_integration.py` (whole file)
- **Change**: module level prewarm, shim, `require_fresh()`; `RunConfig` tests use `StatePaths`/`Injections`/`RunLimits`
  and the new flags (`--config-dir`, `--mem-backup-state-path`, `--online-ntp`, every `--test-*` defaulting off — one
  test asserts `parse_args([...]).instrumentation == _NO_TEST_FLAGS`); `_collect_chips` tests build twin buses from an
  inline plan; the boot test boots the first generated device through `main()` with `""` state paths and a scratch
  `--config-dir`, asserts `would_have_triggered_count == 0` on the WDT the runner passed and that the offline NTP file
  exists; pure-helper tests for the exit-code mapping and the shutdown line format (`mem_backup: r0=`,
  `public_destinations_refused=`, `fram_writes=`, `fram_writes_by=` — U35 stage, A.U35.28, gap pass G3; plus one booted
  case: a generated device with FRAM boots, one logger writes one entry, and the line's `fram_writes_by` names that
  logger with `2` and every other FRAM-backed logger that wrote, sorted by name); the docstring and comments per
  A.U24.56; tags; trailer.
- **Resolved**: A.U24.56 (U24) and A.U36.513 (U36) both name `:1-2`, `:136-138`, `:218-220`; A.U36.513 itself says these are
  A.U24.56's — one edit in U24.
- **Unit**: U25 (stages U8C, U24)
  A-C2 step order: A.U24.70's part lands in U25, not U24 (it follows A.U24.70's own change, which lands in U25).
- **Depends**: M.TWIN.047-053
- **Blast carried by**: —
- **Kind**: test

## tests/test_digital_twin_scd30.py

### M.TWIN.142 SCD30 fake tests: measuring status, argument CRCs, FRC, power-up, counter, graceful load, grouped constructor
- **From**: A.U25.12 (stop → no RDY edge for 3 intervals, 0x0010 → edges resume; wrong CRC → setting unchanged; interval 0
  and 1801 → unchanged; FRC 900 → 900, after 0xD304 → 400, a new chip from the same state file → 400; state file
  round-trips `measuring`; `:106-112` → set 900 reads 900; `:80-84` → data-ready 0 and FRC 400 after reset; interval tests
  keep 2-1800), A.U25.51 (`:80` per A.U25.12; `:325` `clear()` with no op → both ops answer normally (the bytes); `:426`
  state path `None` → no file created in the cwd), A.U25.70 (a fault matched to 0x0300 spares a 0x0202 read and hits the
  next 0x0300; two raises of one queued fault are distinct objects; `pending()` counts down), A.U25.32 (`:414-423` holds;
  `"[1, 2]"` and `{"altitude": "x"}` load factory defaults), A.U25.73 (`:227-230` range comment), A.U4.06 (counter test),
  A.U4.04 (two identical PUTs: the chip's NVM counter rises only for AmbPres/ForceCalRef on the second — see Resolved),
  A.U15.12 (with the CO2 walk step 0 the booted device reaches `FRCState` 4, and the three settings round-trip — see
  Resolved), A.U24.30 (`:32-40` `FixedRandom`; `:202-210` asserts `calls[3:6] == [(-5.0, 5.0), (-0.1, 0.1), (-0.5,
  0.5)]`), A.U24.38 (hands `:80, :325, :426` to A.U25.51), A.U30.05 (`:137-139, :222` decode their own way — holds),
  A.U5.15 (36 `Scd30Chip(` calls regrouped), A.U25.62 (`SCD30Chip`), M.TWIN.013 (`nvm=`, `timer_factory`, `corrupt_next()`)
- **Site**: `tests/test_digital_twin_scd30.py` (whole file)
- **Change**: constructions `SCD30Chip(co2=Walk(…), temp=…, hum=…, nvm=SCD30Nvm(interval, measuring))`, no
  `auto_refresh` (the refresh tests pass `timer_factory=machine._simulation_timer`); `corrupt_next_measurement = True` →
  `corrupt_next()`; frames written with their argument CRC (`crc8` from `_crc8`); the cases under From; the booted
  cases (A.U4.04, A.U15.12) run in-process on `device_with("scd30")` with C4: the settings are applied through the
  module's own config-apply path the REST handler calls (no HTTP), the counter read from the chip, `FRCState` read from
  the reader's published data, the CO2 walk made constant by `chip.co2 = Walk(800.0, 800.0, 0.0)`; trailer.
- **Resolved**: A.U4.04 ("through the real HTTP route") and A.U15.12 ("through `GET /measurements` … `PUT /sensors`")
  write in-DUT request driving; G7/R19 / A.U25.46 put request driving host-side, while the NVM counter and the walk knob
  are only reachable in-process — the cases run in-process through the same config-apply path the route calls, and the
  route itself is covered by the host harness's PUT and measurement scenarios (A.U25.46) — settled by G7/R19 (the same
  rule M.TWIN.122 applies).
- **Unit**: U25 (stages U4 for A.U4.06's counter test on the HEAD shape, U15 for A.U15.12's case, U24 `FixedRandom`)
- **Depends**: M.TWIN.013
- **Blast carried by**: —
- **Kind**: test

## tests/test_digital_twin_sensortask_integration.py

### M.TWIN.144 In-process system tier: per device, no HTTP; real supervisor, recovery rungs and offline boot proven inside the twin
- **From**: A.U25.46 ((2) the 8 HTTP tests `:190, :256, :275, :296, :349, :394, :558, :784` leave for the host harness;
  (3) what stays is in-process with no HTTP), A.U25.48 (module-level `import sensortask_wozi` and every `sensortask_wozi.`
  use → device from data; test names drop `wozi`), A.U36.016 (SPEC E.2.1's bar this file meets: device-generic
  scenarios per device, one device per process; a driver-specific scenario on a device chosen from data, its header
  saying why and naming the cover), A.U35.31 ((1) the zero-fault test drives the real supervisor through `main()` under
  the tracked `run()`; `_feed_watchdog_periodically()` goes; after one full WDT period past the first supervisor feed,
  `would_have_triggered_count == 0`), A.U10.07 / A.U31.03 / A.U10.23 (twin boots keep `would_have_triggered_count` 0;
  the `:421` escalation run holds — carried by that test), A.S0930.13 / A.U20.06 / A.U32.06 (`:482-523` drives
  `start_tasks(…, task_names=…)` then `supervise_tasks()` in a task, cancels it and `sysfunct._supervisor_task` from
  outside; `:425-427`'s "a local no caller can reach" goes), A.U10.44 (`:516` starter name), A.U10.12 (`:455`
  `start_timers()` two lists — the line goes with A.U35.31's rewrite), A.U18.R01 (L2: a WLAN fake raising on `status()`
  twice triggers one re-construction and the link comes back), A.U25.27 (the construction count that case reads),
  A.U25.33 (new L2: a boot with the offline config makes no send outside the allowed ranges — the shim's counter stays 0
  and no `8.8.8.8` destination is recorded; `:219`'s `NTP_Host` round trip holds and travels host-side), A.U15.17 (L2:
  `WaitTimeNTP` 0 with a seeded timestamped backup reports `RestoreTS` equal to that TS on the first cycles; `:656-667,
  :731` `WaitTimeNTP` 1 hold), A.U9.01 (L2: the notification window with On later than Off containing the current local
  hour, CO2 above `WarnCO2` → a red frame and `Triggered` true; the complementary window → no frame), A.U25.72 (`:558-640`
  hotspot test re-checked against the real AP subnet), A.U25.21 (the hotspot LED assertion on `writes`), A.U25.65 (the
  two DNS failure messages the README quotes), A.U25.45 (`:105` with `_start_webserver()`; `:586`, `:666, :694, :735,
  :772` → polls), A.U25.03 / A.U25.24 (`reset_peripherals()` before each build — `:648, :684` and the second builds;
  the post-construction resets `:702, :778` call it first), A.U25.25 (`_wiring_plan()` → `tests/_twin_devices.py`),
  A.U20.02 (`:92, :649, :683, :727, :763` builds pass `watchdog=`; `:454-464` read the WDT they passed), A.U20.28 (plan
  readers — hold through `wiring_plan()`), A.U25.43 / A.U25.34 / A.U18.12 / A.SDEP.16 (`:18-28` module setup: shim from
  its new directory; comments re-checked), A.U24.08 (`:52-60` `run`/`run_timed`, `:109` `_cancel` → `_async_harness`),
  A.U24.70 (`:63` allocator → `PortAllocator`), A.U24.73 (the file's `Any`), A.U28.28 (the four bare E402 gain one
  reason), A.U11.24 / A.U4.02 (the three `write_config(…, schema)` calls follow the new signature), A.U30.15 (`:543-546,
  :627, :705, :779` `gc.collect()` props go), A.U25.50 / A.U0.29 (`:420-423` and `:709-713` comment heads carry actor and
  date), A.U8.08 (`:461` `l2.wdt_overrun_wait_s`), A.U8C.32 / A.U8C2.11 / A.U8C.24 / A.U8C.120 (tags; rows of moved code
  withdrawn, C3), A.U15.41 (its L2 boot lives in M.TWIN.152 — this file's mention holds), OR141.a (5) (the 100 ms idle
  poll rate stays with its measurement owed in the twin and on the bench; A-C review fold), C1, C2, C4, C5
- **Site**: `tests/test_digital_twin_sensortask_integration.py` (whole file)
- **Change**: header (≤ 3 lines) "In-process twin tier for the device named by TEST_DEVICE: its generated graph booted on
  the twin buses with no HTTP (requests are driven host-side by scripts/_digital_twin_scenarios.py). Driver-specific
  scenarios run only on the device tests/_twin_devices.py picks for them (SPECIFICATION.md E.2.1)." `PER_DEVICE = True`;
  `device = os.getenv("TEST_DEVICE")` with M.TWIN.108's import-time `RuntimeError` when unset; `module =
  load_device(device)` (C2) replaces `import sensortask_wozi`. Module setup per C4 (`sys.path` gains `ext`,
  `digital_twin`, `digital_twin/unixport`; `prewarm_poll_set()` then `patch_asy_udp_socket_for_unix_port()`, one comment
  line each pointing at `digital_twin/README.md`'s shim and prewarm sections); the four E402 lines carry "# noqa: E402 -
  imported after the prewarm and the UDP shim (C4 order)" once. Imports `json`, `select`, `socket`, `_http_client` and
  `assert_sensor_payload_not_self_wrapped` go with the moved tests. Helpers: `_boot(device, port)` →
  `machine.reset_peripherals()`, `network.reset_interfaces()`, `machine.configure_wiring(wiring_plan(device))`,
  `write_offline_ntp_config(cfg_dir)`, `await module.build_system(watchdog=machine.WDT(timeout=8000), cfg_path=cfg_dir,
  web_host="127.0.0.1", web_port=port)` (`# @tunable wdt.timeout_ms = 8000`); `_start_webserver()`, `_make_dns_query()`,
  `_query_dns_and_get_answer_ip()` and their comments go; `_wait_until()` stays with `_WAIT_POLL_S` tagged; ports from
  `PortAllocator` in the file's band (`band_for_device("dtsi", device)`); `run`/`_cancel` from `tests/_async_harness.py`;
  every `Any` → the harness's coroutine alias, `object`, or the plan type. Driver-specific scenarios are defined only when
  `device == device_with(…)` for their drivers (TEST_HELP gap: `device_with(*drivers)`), each with a ≤ 3-line comment
  naming why and the L1 suite that covers every device. Tests after the move:
  (1) `test_sgp40_reading_before_scd30_has_measured_yet_logs_no_bogus_error` (driver-specific: `sgp40` and `scd30`) —
  body unchanged but for C4; its `ErrCount` assertion holds.
  (2) `test_watchdog_is_never_starved_while_the_real_supervisor_runs` (device-generic) — A.U35.31 (1):
  `main_task = create_task(module.main(watchdog=wdt, cfg_path=…, web_host="127.0.0.1", web_port=port))` under the
  tracked `run()`; poll `wdt.feed_count >= 1`, then `await asyncio.sleep(_WDT_OVERRUN_WAIT_S)` (`# @tunable
  l2.wdt_overrun_wait_s = 9.0`, A.U8.08's row) and assert `wdt.would_have_triggered_count == 0`; in the same run, the
  offline-boot case (A.U25.33): `_unix_port_udp_addr_shim.public_destinations_refused == 0` and `last_refused is None`,
  after the NTP client has made at least one sync attempt in the window (read from its own state; the executor names the
  field on the post-U18 tree). The comment block above it → A.U25.50's "# Watchdog escalation (owner, 2026-08-13: an
  automated assertion here, and a manually observable run through digital_twin/run_generic_integration.py)." plus one
  line "# Proven on the real supervisor's feed site; the planted-fault halves are runner flags read host-side
  (--test-watchdog-fault)." — the `:424-439` orphan narrative goes (the tracked `run()` cancels every task it started).
  (3) `test_the_supervisor_restarts_a_real_dead_task` (device-generic) — `task_starters =
  module._collect_task_starters()`; the class-level wrap of `SystemService._start_task` stays (its `# type:
  ignore[method-assign]` lines too); `await sysfunct.start_tasks(task_starters,
  task_names=module._collect_task_names())`, then `supervisor = create_task(sysfunct.supervise_tasks())`; the target is
  SYSTEM's own status loop (`task_starters.index(sysfunct.start_asy_status)`, A.U10.44's name: on every device, no I/O)
  with the comment "# any task: the supervisor reads only task.done()"; the asserts as today; `finally` restores the
  wrap, cancels `supervisor` and `sysfunct._supervisor_task` (A.S0930.13) and every started task, each awaited under
  `except asyncio.CancelledError`; the defensive `dns_server_task` cancel and the `gc.collect()` go (A.U30.15 — see Unit).
  (4) `test_a_failing_wlan_status_triggers_one_reconstruction_and_the_link_returns` (device-generic, A.U18.R01) — boot,
  start WiFi's connect task (`conn.start_asy_connect()`, A.U10.44), poll `conn.wlan.isconnected()`; `before =
  network.constructions[network.STA_IF]`; `network.WLAN(network.STA_IF).raise_on["status"] = (OSError, (errno.EIO,),
  2)`; poll until `network.constructions[network.STA_IF] == before + 1` and `isconnected()` again, both within the WiFi
  service's own retry budget (`_WAIT_TIMEOUT_S` scaled at execution to that budget); assert the count did not rise twice.
  (5) `test_hotspot_fallback_drives_the_status_led_and_binds_the_dns_server` (driver-specific: `neopixel`; the in-process
  half of `:558` — G7/R19 leaves request driving host-side, the LED frames are visible only in-process): `SSID` written
  through `conn.cfgmgr.write_config({"SSID": "TestNet"})`; `conn.wlan.script_connect_outcomes([network.STAT_NO_AP_FOUND] *
  8)`; the pixel's overlay task and `conn.start_asy_connect()` started; the `conn.connection_failures = 4` poke and the
  `asyncio.sleep(0.2)` go (the transition is reached by real failure cycles, as the CI suite's Run 7 does); poll
  `conn.dns_server_task is not None` with the message "real hotspot activation never started the real DNSServer task",
  then `conn.dns_server._udps.connected` (A.U10.35 private name) with "the real DNSServer never bound its port 53 socket"
  (A.U25.65's two messages verbatim), then `conn.led is pixel`, `len(pixel.pixel.writes) > 0` and
  `conn.is_hotspot_active()`. The DNS answer and the `/generate_204` redirect assertions move host-side (Blast).
  (6) `test_sgp40_voc_backup_survives_a_simulated_reboot_through_the_real_fram_chunk` and (7)
  `test_sgp40_voc_backup_unflushed_write_is_lost_…` (driver-specific: `sgp40` and `fram`) — C4 before each build (the
  second build after `machine.flush_fram()` follows `reset_peripherals()`, so the FRAM image is re-read from
  `state_path` — the simulated power cycle); the `asyncio.sleep(2.5)` init waits → `wait_for_value(lambda: sgp.voc_init,
  1, _WAIT_TIMEOUT_MS)` (A.U25.45, `tests/_twin_readiness.py`); `finally`: `machine.reset_peripherals()` then
  `machine.configure_fram_state_path(None)`; `:709-713` head → A.U25.50's "# Recombination test (owner, 2026-09-04): a
  crash between a FRAM write and the next flush - the twin analogue of tests_hardware/flash/test_bus_concurrency.py's
  hard-reset-race test.".
  (8) `test_a_restored_backup_reports_its_timestamp_without_ntp` (driver-specific: `sgp40` and `fram`; A.U15.17's L2):
  boot 1 with NTP marked synced through `ntp._set_synced(value=True)` (A.U9.01's stated method) and one flushed backup;
  boot 2 with `WaitTimeNTP` 0 and NTP unsynced; on its first cycle the reader's reported `RestoreTS` (its status data,
  the dict `/status` serializes) equals boot 1's backup timestamp.
  (9) `test_the_notification_window_spanning_midnight_flashes_red` (driver-specific: `notification` and `scd30`; A.U9.01's
  L2): `_wall_clock.install(…)` for the loaded modules (M.TWIN.019), `ntp._set_synced(value=True)`; `OnH`/`OffH` applied
  through the notification module's own config-apply path the REST handler calls, On later than Off and containing the
  hour of `ntp.cettime()`; `chip.co2 = Walk(c, c, 0.0)` with `c` above `WarnCO2`; after one monitor cycle the twin
  pixel's `writes` holds a red frame and the module's status data reports `Triggered` true; the complementary window
  (On and Off swapped) → no new frame.
  (10) `test_the_captive_dns_listener_idles_at_its_idle_rate` (driver-specific: `neopixel`, the same hotspot boot as
  test 5; A.U18.05's measurement, OR141.a (5)): with no DNS traffic for a window of `_IDLE_WINDOW_S`, the listener's
  wake-ups (its socket's `ready()` rounds, counted by wrapping the instance's bound method from the test — no product
  hook) number at most `window / poll_idle_ms + 1` and at least `window / poll_idle_ms − 1`, read with `src_const` from
  `src/asy_udp_socket.py`; the measured rate is printed as one `MEASURE udp.idle_wakeups_per_s=<n>` line, the twin half
  of the rate's measured basis (the first-answer latency after silence is measured host-side, M.PROC.022; the
  bench half is C's).
  Tunables (C3): `_WAIT_POLL_S` (`l2.sensortask_integration_wait_poll_s`), `_RUN_BOUND_S` (now `:320` only),
  `_LONG_RUN_BOUND_S` (test 2), `_WAIT_TIMEOUT_S`, `_RESTART_WAIT_TIMEOUT_S`, `_SUPERVISOR_RUN_BOUND_S`,
  `_HOTSPOT_WAIT_TIMEOUT_S` (re-measured: five real failure cycles replace the poke), `_BIND_POLL_S`,
  `_HOTSPOT_RUN_BOUND_S` (both test 5), `_REBOOT_RUN_BOUND_S` kept, `_IDLE_WINDOW_S` new (test 10,
  `l2.sensortask_integration_idle_window_s`); withdrawn with the moved code —
  `l2.sensortask_integration_dns_query_timeout_s`, `…_dns_query_poll_ms`, `…_override_poll_s`, `…_override_poll_tries`;
  `l2.twin_wdt_feed_interval_s` leaves this file (its row keeps `launch.py:41` and the bus-hazard site). Trailer canonical
  (A.U24.04).
- **Resolved**: (a) A.U9.01 ("`OnH`/`OffH` PUT over HTTP … `/status` `notification.Triggered`"), A.U15.17 ("reports
  `RestoreTS` … in `/status`") and A.U18.R01 write in-DUT request driving or REST reads; G7/R19 and A.U25.46 put request
  driving host-side while the pixel frames, the WLAN construction count and `ntp._set_synced()` are reachable only
  in-process — the cases run in-process through the same config-apply path and status data the routes use, the routes
  themselves covered by the host harness (A.U25.46) — settled by G7/R19, the rule M.TWIN.122/.142 apply. (b) A.U25.46
  moves `:558` whole, but its LED and DNS-bind assertions cannot be read host-side and OR19.a (4) keeps every assertion:
  the test splits — in-process LED/bind half here, DNS answer and captive redirect in the harness (A.U25.72's query-source
  check travels with them) — agent decision (OR2.c list). (c) A.U25.46 (1) replaces `conn.connection_failures = 4` with
  five `--wifi-outcome no_ap` for the moved scenario; the in-process half applies the same rule through the twin's own
  `script_connect_outcomes()` (twin API, no product poke, OR36). (d) A.U36.016's "one device per process" is met by the
  `PER_DEVICE` marker A.U24.65 (3)'s dispatch already reads — no SCR change. (e) A.U25.33's offline-boot case shares
  test 2's `main()` window rather than booting a second time per device — agent decision. (f) the mempause test (`:784`)
  moves host-side, where its `pause_permanent_storage(0)` call (A.S0930.12 `:811`, "holds") is an in-DUT poke (OR36):
  the harness asserts `MemPaused` true after `PUT /system {"SystemCmd": "mempause"}`, and the immediate-unpause branch is
  proven in-process by M.TWIN.104's A.U25.57 cases and at L1 — settled by A.U25.46 (4) ("replaced by a CLI flag or REST,
  never a new product hook").
- **Unit**: U35 (stages: U24 harness/allocator/`Any` (C2); U25 the move, per-device form, C4, tests 1 and 3-10 — test 10
  is A.U18.05's twin measurement, which needs the in-process hotspot boot born here, so it follows the rate's U18
  landing (reason recorded); U30 the
  `gc.collect()` props go (A.U30.15's own unit; until then they stay in tests 3, 6, 7); U35 test 2 per A.U35.31)
  A-C2 step order: A.U24.70's part lands in U25, not U24 (it follows A.U24.70's own change, which lands in U25).
- **Depends**: M.TWIN.017, M.TWIN.019, M.TWIN.031, M.TWIN.035, M.TWIN.040, M.TWIN.042, M.TWIN.053, M.TWIN.108 (marker
  form); M.TEST_HELP.047, .055, .056, .060; SRC_CORE supervisor split (A.U20.06) and `_supervisor_task`; A.U25.46's harness
  (SCR) for the moved half
- **Blast carried by**: the 8 moved tests, each with goal and assertions, into `scripts/_digital_twin_scenarios.py`
  → SCR gap (A.U25.46), carrying: `:211` comment (A.U10.36, nested `get_dict_cfg()` shape), `:219` `NTPHost` round trip
  (A.U25.33 holds; A.U10.40 key), `:300-320` reset-errors boot window (A.U10.11 re-read; A.U2.13 seed 99 stays),
  `:349-390` `PauseTime` (A.U9.09 `:354-355`/`:386` wording, A.U22.03 `:377` comment, A.U19.03 `:366` holds),
  `:394-411` SCD30 field (its NVM/`FRCState` halves are in-process in M.TWIN.142), `:558` DNS answer + redirect
  (A.U18.01 QTYPE A, A.U18.03 512-byte replies, A.U25.72 source check; A.U14.28's `:128-129` comment is moot — a CPython
  socket has `settimeout`), `:784-818` mempause (A.U10.15, A.S0930.27 `:802` hold; the unpause call goes, (f)); the
  `PER_DEVICE` dispatch → A.U24.65 (3) (SCR, unchanged); port band row `dtsi` → M.TEST_HELP.056; `device_with(*drivers)` →
  TEST_HELP gap; the gc-site checker finds no row here after U30 → A.U30.16 (TSC); SPEC E.2.1 text → A.U36.016 (SPEC);
  README "Running the twin's own tests" names the split → M.TWIN.063; test 10's measured idle rate into the rate's row
  basis → M.SPEC.156
- **Kind**: test

## tests/test_digital_twin_clock_jump.py (new)

### M.TWIN.146 L2 clock-jump injection on the twin wall clock
- **From**: A.U10.28 (L2 half "pending U25": (a) `TS` after a backward and a forward step equals the stepped clock,
  tick-based values unaffected; (b) a timestamped chunk read after a backward step is expired under a nonzero
  `BackupMaxAge` and accepted under 0; (c) the notification window evaluated across a step over `OnH:OnM` flashes at
  most once per cycle), A.U18.26 (L2 half "pending U25": (a) `cettime()` before and after a backward step across the
  March switch returns the stepped clock's offset; (b) synced at t0, the RTC stepped forward one year and back two:
  `Synced`/`LastSyncAge` follow ticks only; (c)/(d) need a successful sync — see Resolved), A.U25.71 ("A.U10.28 (c)'s and
  A.U18.26's L2 halves use `step()`"), LEAD/R05 (clock-jump injection at L1/L2), A.U36.016 (device choice), routine
  settlement `twin-choice-17` (AC_NOTES 52: with the twin's local NTP responder the two sync-dependent cases also run
  here, keeping their unit-level proofs) and OR140.a (13) (the responder, M.TWIN.167) — A-C review fold, C2, C4
- **Site**: new `tests/test_digital_twin_clock_jump.py`
- **Change**: header (≤ 3 lines) "Wall-clock consumers across an RTC step on the twin (the RTC is the wall clock, as on
  rp2): reader TS, backup age, the notification window, NTP's cettime and staleness, and a real sync against the local
  NTP responder. Each case runs on one device tests/_twin_devices.py picks; the L1 suites cover every module." Module
  setup per C4. Each case: C4 boot of its device through `build_system(watchdog=…)`, then `clock =
  _wall_clock.install(m for m in sys.modules.values() if getattr(m, "time", None) is time)` (the runner's own line,
  M.TWIN.050), `ntp._set_synced(value=True)` where a case needs a synced clock (A.U9.01's stated in-process method); steps
  through `clock.step(seconds)` only (no product hook, OR36). Cases: (1) `device_with("bmp3xx")` — one read cycle driven
  through the reader's trigger, `step(-3600)`, the next cycle's `TS` equals the stepped `time.time()` (± 1 s); same for
  `step(+86400)`; the reader's `TickSeconds` values (A.U10.02) advance by the ticks elapsed only. (2)
  `device_with("sgp40", "fram")` — one flushed timestamped backup, `step(-7200)`, a re-read of the chunk under
  `BackupMaxAge` 60 is refused as expired and under 0 accepted (U16's negative-age rule). (3) `device_with("notification",
  "scd30")` — window set through the module's config-apply path to start one minute ahead, CO2 walk above `WarnCO2`;
  `step(+120)` across `OnH:OnM` between two monitor cycles: the pixel's `writes` gains at most one alarm frame per cycle,
  never two in one cycle. (4) any device (`generated_devices()[0]`): `step()` to 2026-03-29 00:59 UTC then back across
  01:00 UTC — `ntp.cettime()` returns the offset of the clock as stepped each time (CET then CEST then CET). (5) same
  device, synced at t0: `step(+365 * 86400)` then `step(-2 * 365 * 86400)` — `Synced` stays true and `LastSyncAge`
  equals the ticks elapsed since t0 (± 1 s). (6) A.U18.26 (c), same device booted with `write_responder_ntp_config()`
  (M.TWIN.053) and an `NtpResponder` (M.TWIN.167) run from the test's coroutine, `mode = "silent"` through the boot: the
  clock stepped to rp2's boot default (2021-01-01 00:00 UTC, `ports/rp2/main.c:141-145`), then `mode = "serve"`; the
  client's next attempt (its own retry path, no product hook) sets the clock to the served time (± 1 s), `LastSyncAge`
  restarts at 0 and the staleness count runs from that moment. (7)
  A.U18.26 (d), same boot: `NTPOffset` changed through the client's own config-apply path (the one the REST handler
  calls): `Synced` reads false at once, the next sync against the responder sets the clock to the served time shifted
  by the offset (± 1 s) and `Synced` true again. Tunables tagged per C3 (`l2.clock_jump_wait_timeout_s`, row basis U8's N.1
  rule). Registers `machine.reset_test_state`; trailer canonical.
- **Resolved**: A.U18.26 (c) ("the first RTC set … by a successful sync") and (d) ("an `NTP_Offset_S` PUT followed by a
  successful sync") were left to L1 while the twin had no NTP server; the routine settlement `twin-choice-17` (AC_NOTES
  52) runs them here too through the local responder (M.TWIN.167), every run still off public hosts (the responder is on
  loopback), and their L1 cases stay. A.U25.71 says the L2 halves "use `step()`" but no action writes the file; it is created
  here (the gap M.TWIN.019 records).
- **Unit**: U25 (cases (6)-(7) after M.TWIN.167 in the same unit)
- **Depends**: M.TWIN.019, M.TWIN.033, M.TWIN.050 (install line), M.TWIN.053, M.TWIN.167; A.U10.28, A.U18.26 (L1 halves,
  fake-clock helper);
  M.TEST_HELP.055 (`device_with(*drivers)` — TEST_HELP gap)
- **Blast carried by**: SPEC C.9/F cites the tests (A.U10.28/A.U18.26's doc halves, SPEC); the `tests/test_digital_twin_*.py`
  glob picks it up (`scripts/test.sh`; `digital_twin/typecheck.ini`'s `files`, M.TWIN.075 — no edit)
- **Kind**: test

## tests/test_digital_twin_sgp40.py

### M.TWIN.150 SGP40 fake tests: general call, heater-off, keyed faults, `corrupt_next()`, `Walk`; two driver-level L2 cases
- **From**: A.U25.10 (`b"\x06"` through `handle_general_call()` clears a pending reply and counts `resets`; any other
  byte leaves it), A.U25.11 (heater-off clears a pending measure reply and counts once; the next measure answers
  normally), A.U25.70 (a fault keyed to a command word: a `readfrom_into` fault for `0x260F` spares the self-test read and
  hits the next measure read; `inject_fault(op, OSError, errno, "m", times=n)`), A.U15.13 (L2: `corrupt_next()` after
  setup, the CRC-failing measure, then the next `initialize()` gets a serial reply), A.U15.19 (L2: a booted twin publishes
  `VOCState` 0 then 1 — see Resolved), A.U24.30 (`:14-31` `_FixedRandom` → `tests/_twin_random.py` `FixedRandom`),
  A.U25.62 (`Sgp40Chip` → `SGP40Chip`), A.U5.15 (`raw: Walk` replaces `min_raw`/`max_raw`/`raw_step`, M.TWIN.014),
  A.U25.01 (the fidelity rows these tests stand behind — general call, heater-off; M.TWIN.059), A.U25.73 (range comment
  `:85-90`), M.TWIN.003 (CRC golden vector `:35` holds), C2, C4, C5
- **Site**: `tests/test_digital_twin_sgp40.py` (whole file)
- **Change**: header (≤ 3 lines) "Tests for digital_twin/_sgp40_chip.py's replies, resets and faults, plus two cases
  driving the real asy_sgp40_driver.py over the twin bus (CRC recovery; VOCState through the blackout)." `sys.path`
  comment `:4-6` → one line "# digital_twin/ is not on scripts/test.sh's MICROPYPATH; this file reaches it itself.";
  `from _twin_random import FixedRandom` (the local class goes); `SGP40Chip(random_source=FixedRandom(...), raw=Walk(lo,
  hi, step))` throughout — `test_custom_range_is_honored`, `…_clamped_to_the_configured_max/min` and
  `test_raw_step_is_configurable_via_the_constructor` pass `Walk(50, 150, 1000)`, `Walk(26000, 34000, 1000)`,
  `Walk(26000, 34000, 50)`; `:85-90` reads `chip.raw.lo`/`chip.raw.hi` (no private `_min_raw`/`_max_raw`) and its comment
  → A.U25.73's citation ("SRAW_VOC 0-65 535 ticks, SGP40 datasheet Table 1; the twin's walk is a sub-range"). Faults
  `:142-164` → the new `inject_fault` signature (C2) with codes from `errno`; new keyed case (A.U25.70): `chip.fault.
  inject_fault("readfrom_into", OSError, errno.EIO, "m", key=0x260F)` — a self-test write and read answers `0xD400`, the
  next measure-raw read raises, the one after answers. `:166-179` → `chip = SGP40Chip()` then `chip.corrupt_next()`
  (no constructor keyword); the asserts as today. New chip cases: `handle_general_call(b"\x06")` after a measure write →
  the next read returns `bytes(3)`, `resets == 1`, `_measuring` false; `handle_general_call(b"\x04")` → reply kept,
  `resets == 0`; heater-off `b"\x36\x15"` after a measure write → the pending reply cleared, `heater_offs == 1`, the next
  measure answers a valid word; `power_cycle()` → idle. Driver-level cases (C4 module setup: prewarm, shim, both reset
  hooks; registers `machine.reset_test_state`): (1) A.U15.13 — `machine.configure_wiring(wiring_plan(device_with(
  "sgp40")))`, the driver built on that bus, `await sgp.initialize()`; `chip = machine.peripheral(<bus>).devices[0x59]`
  (the public `devices` map, M.TWIN.024); `chip.corrupt_next()`; one measure raises the driver's CRC error; the next `initialize()`
  returns the serial reply. (2) A.U15.19 — C4 boot of `device_with("sgp40")` through `build_system(watchdog=…)`, the
  reader's read task started, cycles driven through its trigger event (no wall-clock wait per sample); the reader's
  published data reports `VOCState` 0 on the first cycle and 1 once the algorithm's blackout (A.U15.19's sample count)
  has passed, polled with a tagged deadline. Trailer canonical.
- **Resolved**: A.U15.19 asks the booted twin to publish through `GET /measurements`; G7/R19 / A.U25.46 put request
  driving host-side, while driving the read cycles is in-process only — the case reads the reader's published data (the
  dict the route serializes), the route covered by the host harness's measurement scenario (A.U25.46) — settled by
  G7/R19, as M.TWIN.144 (a). A.U15.13's "`_corrupt_next_reply = True` … (or a public `corrupt_next()` added by U25)"
  → `corrupt_next()` (M.TWIN.014 Resolved).
- **Unit**: U25 (stage U24: `FixedRandom`; U5: `Walk` construction)
- **Depends**: M.TWIN.001, M.TWIN.002, M.TWIN.014, M.TWIN.024; M.TEST_HELP.055, .059; A.U15.13, A.U15.19 (driver
  behaviour)
- **Blast carried by**: CI suite's keyed SGP40 fault (`sgp40:readfrom_into:3:0x260F`, AC_NOTES 31) → SCR gap; fidelity
  rows → M.TWIN.059
- **Kind**: test

## tests/test_digital_twin_timer_pool.py (new)

### M.TWIN.152 Every timer-arm degradation path at L2, per device, and the reboot arm-failure starve
- **From**: A.U25.56 ((1) pool empty at boot → each reader's trigger-arm failure ends its task, the supervisor restarts
  it, after `set_alarm_pool_free(16)` each reader reads (A.U15.41's L2); (2) the uptime timer's failure leaves `SysUptime`
  not advancing while the device serves; (3) `reboot_system()` with the pool empty → watchdog-starve fallback, `would_
  have_triggered_count >= 1` within `timeout + 1 s`, no `machine.reset()`; (4) an unpause timer that cannot arm aborts
  the pause; (5) NTP's check timer and WiFi's uptime timer re-arm once the pool frees; the Timer-finaliser class stays a
  fidelity row), SUPP_owner_0930 section C's U25 bullet (A.U25.56 (3) amended: start `start_tasks()` and
  `supervise_tasks()` as a task, `reboot_system()` → `True`, once `sysfunct._shutdown_task` is done: `_force_watchdog_starve`
  True, region 0 code 6, no `machine.reset()`/`bootloader()` call, `would_have_triggered_count >= 1` within `timeout + 1 s`
  of the last `feed_times` entry), A.S0930.36 (d) (its L2 half — this case), A.S0930.38 (co-lands with (3); the in-process
  teardown pattern: `_reset_timer`/`_reset_task`/supervisor cancelled from outside), A.U15.41 (L2 "a boot with the pool
  exhausted asserting each sensor task ends, restarts and reads"), A.U18.23 / A.U18.24 (NTP and WiFi re-arm), A.U10.12
  (trigger starts in task context), A.U25.19 (the pool and `set_alarm_pool_free()`), C4
- **Site**: new `tests/test_digital_twin_timer_pool.py` (in-process, no HTTP)
- **Change**: header (≤ 3 lines) "rp2's 16-alarm pool exhausted under the generated graph of the device named by
  TEST_DEVICE: every failed arm is handled in place and none reboots by itself (owner, 2026-07-18). The finaliser case
  is not reachable here (digital_twin/README.md fidelity table)." `PER_DEVICE = True` with M.TWIN.108's guard; C4 module
  setup; `module = load_device(device)` (C2); every case boots through `build_system(watchdog=wdt, …)` after
  `machine.set_alarm_pool_free(n)` and restores 16 in `finally`. (1) `set_alarm_pool_free(0)`; `start_timers(
  _collect_trigger_starters(), _collect_timer_starters())`, `start_tasks(…, task_names=…)`, `supervise_tasks()` as a
  task; for each reader in the plan: its task is seen done with one persisted arm-failure entry (`code("E",
  "TIMER")`-style lookup through `tests/_error_codes.py`), then restarted by the supervisor; after
  `set_alarm_pool_free(16)` each reader's data gains a reading within a tagged deadline. A device with no reader skips
  (1) with a one-line reason. (2) the uptime arm fails at boot: over two supervisor periods `SysUptime` from SYSTEM's
  status data does not advance, the device keeps serving its tasks (no task ends for it). (3) per the amended text:
  pool 0 after boot, `supervise_tasks()` as a task, `await sysfunct.reboot_system()` is `True`; poll until
  `sysfunct._shutdown_task.done()`; assert `sysfunct._force_watchdog_starve is True`, `machine.mem_backup(0)` reads code
  6 in its first word (M.TWIN.032), `machine.reset_count == 0` and `machine.bootloader_count == 0`, and
  `wdt.would_have_triggered_count >= 1` within `timeout_ms / 1000 + 1` s of `wdt.feed_times[-1]` (polled, tagged
  margin); teardown from outside: `sysfunct._reset_timer.deinit()` if armed, `_reset_task`, `_supervisor_task` and the
  `supervise_tasks()` task cancelled and awaited under `except asyncio.CancelledError` (A.S0930.38's pattern), then
  `asyncio.new_event_loop()` (C4). (4) devices with FRAM: pool 0, `mempause` through the generated `SystemCmd` dispatch
  in-process → the manager's `get_pause()` is false at once and one persisted entry names the failed arm. (5) pool 0 at
  boot, then 16: NTP's check timer and WiFi's uptime timer each show one `Timer.init` re-arm (the twin pool's free count
  drops by their alarms) and their counters advance again. Tunables per C3; trailer canonical.
- **Resolved**: A.U25.56 (3) as first written ("feeding stops … no `machine.reset()` call") would pass without the
  supervisor task, for the wrong reason; SUPP_owner_0930 section C's U25 bullet amends it to start the supervisor and
  assert at `_shutdown_task` done — the amended text is taken (owner, 2026-09-30, OR120). A.U15.41's L2 sentence names
  `tests/test_digital_twin_sensortask_integration.py`; A.U25.56 (1) carries the same case into this file (U25.md's
  coverage table row for A.U15.41 names A.U25.56) — one case, here.
- **Unit**: U25 (A.S0930.36 (d)'s L2 half co-lands; SUPP section C's amendment applies)
- **Depends**: M.TWIN.030, M.TWIN.031 (`feed_times`), M.TWIN.032, M.TWIN.034, M.TWIN.108 (marker form); SRC_CORE
  `reboot_system()` sequence (S1-S6, `_force_watchdog_starve`, `_shutdown_task`); A.U15.41, A.U18.23, A.U18.24 (product
  paths); M.TEST_HELP.045, .047, .055
- **Blast carried by**: fidelity row "Timer finaliser not modelled" → M.TWIN.059; README `machine.py` pool bullet →
  M.TWIN.058; `PER_DEVICE` dispatch by marker (SCR, unchanged)
- **Kind**: test

## tests/test_digital_twin_uart_comm_hazard.py (new)

### M.TWIN.154 UART comm hazards H1a/H1b/H2 over the twin wire, both CRC modes
- **From**: A.U17.25 (the L2 file: payload 48, timeout 100 ms, poll 1/1, both CRC modes; H1a two tasks initiating at
  once — one completes, the other returns its sentinel with the re-entrant code, the initiator's wire log parses into
  whole well-formed frames only; H1b `clear()` on the responder before the first frame, mid-train and after the last ACK
  — the transaction completes or fails cleanly and the next one succeeds; H2 a raw GET frame written from the
  responder's fake while the initiator awaits an ACK — the initiator logs the peer-initiated code and both ends recover
  within two attempts; pair on the twin's own `machine.UART` with `UARTLink` (real wire time) and `LinkPoller` (bounded),
  constructed at synchronous scope, no device named; sized under the 240 s per-file timeout), A.S0930.04 (1) (both modes
  by plan — referenced), A.U36.539 (SPEC J.7 tier map names this file — SPEC's site), LEAD/R28, C4 (UART half), C6
- **Site**: new `tests/test_digital_twin_uart_comm_hazard.py`
- **Change**: header (≤ 3 lines) "UART_Comm hazards across the twin's wire-timed crossover (SPECIFICATION.md J.7): two
  initiations on one instance, clear() racing a transaction, both ends transmitting. Each check runs with no CRC and
  with CRC16." `sys.path` puts `digital_twin` ahead of `tests` so `tests/_uart_comm_harness.py`'s `from machine import
  …` binds the twin's `UART`/`UARTLink`/`LinkPoller` — the pair is built by that harness's `Pair(payload_size=48,
  timeout=100, crc_a=crc, crc_b=crc)` (one builder for the mock and twin tiers, Part G reuse), after
  `machine.reset_peripherals()` (the twin UARTs are static per id, A.U25.04), at synchronous scope; `await
  pair.setup()` inside the one `run(coro, _RUN_LIMIT_S)` (`tests/_async_harness.py`, never nested). Checks
  `_check_two_initiations_one_instance(crc)`, `_check_clear_racing_a_transaction(crc, point)` (three points),
  `_check_both_ends_transmitting(crc)` with the assertions above; codes by name (`tests/_error_codes.py` `code()`); the
  wire logs parsed with the harness's `frames()`. Registration per mode: `for crc in (None, CRC16())` builds one
  `test_<check>_<mode>` per check into `globals()` (the mode as `nocrc`/`crc16`). Tunables per C3 (row basis U8's N.1;
  `_RUN_LIMIT_S`, the H2 recovery bound); the file's measured duration recorded in its row (A.U17.25's "measured at
  execution"). Registers `machine.reset_test_state`; trailer canonical.
- **Resolved**: A.U17.25 says "building their pair on the twin's own `machine.UART` fakes with `UARTLink` … and
  `LinkPoller`" without naming a builder; `tests/_uart_comm_harness.py`'s `Pair` already builds exactly that shape and
  resolves `machine` by path, so the twin files reuse it instead of a third copy (SPECIFICATION.md Part G discovery, REF/R05) — agent
  decision (OR2.c list).
- **Unit**: U25 (A.U17.25's L2 files need A.U25.04's `reset_peripherals()`; S0930's both-mode plan co-lands)
  A-C2: "S0930" is not a unit; its parts land in the units SUPP_owner_0930 states: A.S0930.04 in U25.
- **Depends**: M.TWIN.027, M.TWIN.028, M.TWIN.029, M.TWIN.035; M.TEST_HELP's `_uart_comm_harness` (guarded `run()`
  removed there — this file uses `_async_harness`), M.TEST_HELP.045
- **Blast carried by**: SPEC J.7 tier map row → A.U36.539 (SPEC); CLAUDE.md four-tier UART clause → A.U17.25/U36 (DOCS);
  L3/L4 halves → U26 (HW_DEV/HW_BENCH)
- **Kind**: test

## tests/test_digital_twin_uart_field_sweep.py (new)

### M.TWIN.156 UART frame and field sweep H3 through the twin wire
- **From**: A.U17.25 (payload 8, timeout 30 ms, poll 1/1; H3 to a listening responder: every value of each field in the
  first-chunk SET position with no CRC — accepted iff legal per J.3/J.4, no ACK on the responder's wire for a rejected
  one, one clean exchange after each field's sweep; with CRC16 the boundary values CMD 0x00-0x05, 0xFF; SIZE 0, 1, 2, 8,
  9, 255; CHUNKS 0, 1, 2, 255; CUR_CHUNK 0, 1, 2, 255; UID 0x00, 0xFE, 0xFF; sized under the 240 s per-file timeout — the
  no-CRC sweep's ~1,280 rejections cost one 45 ms quiet window each), A.U17.24 / A.U17.16 (verdict rules), A.S0930.04 (1),
  A.U36.539 (tier map — SPEC's site), C4 (UART half)
- **Site**: new `tests/test_digital_twin_uart_field_sweep.py`
- **Change**: header (≤ 3 lines) "Every CMD/SIZE/CHUNKS/CUR_CHUNK/UID value in a first-chunk SET, written raw into the
  twin wire to a listening responder: legal frames are answered, illegal ones are not (SPECIFICATION.md J.3/J.4). Full set
  without CRC, boundary values with CRC16." Pair from `tests/_uart_comm_harness.py` `Pair(payload_size=8, timeout=30,
  crc_a=crc, crc_b=crc)` as M.TWIN.154 (twin `machine` first on the path, `reset_peripherals()` first, synchronous
  construction); a raw frame is written through the initiator's twin fake (`pair.fake_a.write(frame)`) with the CRC
  appended by the bus's own CRC object when the arm has one; the verdict per value from the J.3/J.4 rule table the L1
  sweep (`tests/test_uart_comm_hazard.py:237-344`, A.U17.24) uses — imported from where A.U17.24 places it, not
  restated; the responder's wire is read after one quiet window (`_QUIET_WINDOW_MS`, tagged, 45). One test per field and
  mode (`test_<field>_sweep_nocrc`, `test_<field>_boundaries_crc16`), each ending with one clean exchange. If the
  measured no-CRC duration exceeds the per-file timeout's margin the executor splits by field into two files — stated in
  the row, never by raising the timeout. Registers `machine.reset_test_state`; trailer canonical.
- **Resolved**: —
- **Unit**: U25
- **Depends**: M.TWIN.154 (same builder), A.U17.24 (rule table)
- **Blast carried by**: as M.TWIN.154
- **Kind**: test

## tests/test_digital_twin_uart_link.py

### M.TWIN.158 Generated UART link on the twin: device from data, both CRC modes, a pause not a collect, a retention rate
- **From**: A.S0930.04 (2) (the generated no-CRC device; a CRC16 arm at the pair level: a `UARTLinkDriver` pair on the
  twin's `machine.UART` with `UARTLink` and `LinkPoller`, buses built with `crc=CRC16()`, at synchronous scope —
  exercise rounds complete, a mid-train corrupted byte is caught (failure counted, next round clean), `wrnno`/`errno`
  history carries only the expected codes), A.U17.13 (new L2: a pair with the responder's `payload_size` 8 larger than the
  initiator's, four SETs → the responder's history holds the link-unintelligible code, the initiator's the no-ACK code and
  not the former), A.U17.15 (SPEC J names this file as the L2 pin of that diagnosis — the same case), A.U17.04 (`:283-305`
  → `test_a_collection_length_pause_mid_transfer_does_not_break_the_link`, `pauser()` with `time.sleep_ms(_WORST_GC_PAUSE_MS)`
  = 21, `uart.gc_pause_worst_ms`; rows renamed `l2.uart_link_pause_rounds`/`…_pause_step_ms`), A.U17.05 (`:396-403`
  churn's recovery `gc.collect()` and `:387` `import gc` go), A.U30.13 (`:425-490` one test
  `test_hammering_the_link_beside_the_graph_holds`, no parameter, no in-body `gc.threshold`; messages read the stage),
  A.U30.16 (checker rows `test_many_back_to_back_transfers_do_not_degrade_or_leak.scenario` and
  `_hammer_with_the_graph_running.scenario` stay baselines — function names kept), A.U8.14 (`:490` site goes), A.U24.64
  ("the twin UART hammer's absolute bound … is U25's" — no U25 action writes it: see Resolved), A.U35.22 (`:265` gains one
  multi-chunk SET echo while the graph runs), A.U24.67 (`:200` banner compared with `asy_uart_link_driver._BANNER`, now
  `b"uart-crossover"`), A.U16.01 (`:173-174` "… IS the on-chip layout of this build."), A.U25.04 / A.U25.03 / A.U25.25
  (`:66-78` `reset_peripherals()` and `configure_wiring(wiring_plan(device))` before each build — today it builds dev on
  wozi's lazy plan), A.U25.48 / A.U24.67 (4) (device from data: `device_with("uart_link")`; no `sensortask_dev`
  literal), A.U17.18 (the two bus globals named by the plan's `uart` key), A.U20.02 (`:70` `watchdog=`), A.U24.08
  (`:48-49` → `_async_harness.run(coro, _RUN_LIMIT_S)`), A.U24.15 / A.U24.80 (`:69` poller comment), A.U36.544 (`:442`
  "Part E.7" → "E.8"), A.U28.28 (7) (`:413` PERF401: the two-statement body, else the per-file entry — TOOL decides),
  A.U8C.33 / A.U8C2.12 (tags), A.U32.06 (`:128-131` hold), A.U13.17 (`:169` holds), A.U11.01 (`:273, :478-481` hold),
  A.U13.12 / A.U13.13 (unaffected — hold), A.U25.37 / A.U25.67 (this file is the link's L2 coverage — hold), A.U30.15 (no
  prop here — hold), C1 (`UartLinkExerciser` → `UARTLinkDriver`, `UART_Comm` → `UARTComm`), C2, C4, C5
- **Site**: `tests/test_digital_twin_uart_link.py` (whole file)
- **Change**: header → "Twin-tier coverage of the generated UART crossover link (SPECIFICATION.md J.7) on the device
  tests/_twin_devices.py finds wiring a uart_link pair, its two peripherals joined as the bench jumper joins them, plus
  pair-level CRC16 and mismatch cases." Module setup per C4; `device = device_with("uart_link")`, `module =
  load_device(device)` (C2), `_buses = wiring_plan(device)["uart"]` (`initiator_bus`/`responder_bus` name the module
  globals, A.U17.18); `fakes()` and `build_linked_system()` read `getattr(module, _buses[...])`; the two exerciser
  globals found by role on the module. `build_linked_system()`: `machine.reset_peripherals()`,
  `network.reset_interfaces()`, `machine.configure_wiring(wiring_plan(device))`, `write_offline_ntp_config(cfg)`,
  `run(module.build_system(watchdog=machine.WDT(timeout=8000), cfg_path=cfg), _RUN_LIMIT_S)`, then `UARTLink(fake_a,
  fake_b)` and the bounded pollers; `:66-69` comment → "# Joined as the bench jumper joins them; the pollers are bounded
  because the twin UART's ioctl() answers EINVAL to all but POLL, so a real select.poll() never sees readiness
  (digital_twin/README.md)." `:200` → `bytes(answer) == asy_uart_link_driver._BANNER`. `:173-175` per A.U16.01.
  `:153-154` read `initiator._payload_size == responder._payload_size` and `initiator._timeout == responder._timeout`
  (`UARTComm`'s private names after M.SRC_NET.155 as amended in gap pass G2; GAPS_G2 H-3, gap pass G3; the `:147`
  comment keeps the out-of-band rule).
  `:265` test gains, after the banner GET, one `uart_set(0x02, bytes((i * 5) & 0xFF for i in range(140)))` (three data
  chunks) asserted `True` while the noise tasks run (A.U35.22). `:283-305` per A.U17.04 (comment its three lines). `:382-423`
  per A.U17.05; `:413` per A.U28.28 (7). Leak tests (`:339` and the hammer): retention as a per-transfer rate, G7/R22 —
  after the warm-up, `gc.collect()` then `gc.mem_free()` at transfer counts N1 and N2 (wire logs cleared before each
  reading), `rate = (free_N1 - free_N2) / (N2 - N1)` asserted below `_LEAK_RATE_BYTES_PER_TRANSFER`, calibrated once in
  the B3 campaign against a planted 16-byte-per-transfer leak in a test double (two figures in a ≤ 3-line comment, as
  A.U24.64); the `_LEAK_BUDGET_BYTES` row becomes `l2.uart_link_leak_rate_bytes_per_transfer`. `:425-490` per A.U30.13
  (one test, the stage read in messages); `:442` comment pointer E.8. New pair-level cases (built at synchronous scope with
  `tests/_uart_comm_harness.py`'s `Pair` for bare `UARTComm`, or two `asy_uart_driver.UART(…, crc=CRC16())` buses wrapped
  in `UARTLinkDriver`s with the chosen device's `uart_link` TOML parameters, after `reset_peripherals()`): (a)
  `test_a_crc16_exerciser_pair_completes_its_rounds`; (b) `test_a_crc16_exerciser_pair_catches_a_corrupted_byte` —
  `link.direction_from(fake_a).corrupt_indices[k] = 0xFF` mid-train: the failure is counted, the next round is clean,
  and both histories hold only the CRC and recovery codes named by `code()`; (c)
  `test_a_payload_size_mismatch_is_diagnosed_as_unintelligible` (A.U17.13: responder `payload_size` +8, four SETs, the
  two histories as stated). Tunables: A.U8C.33/A.U8C2.12 rows as listed except `l2.uart_link_collect_*` (renamed,
  A.U17.04), `gc.threshold_bytes :490` (gone), `l2.uart_link_leak_budget_bytes` (replaced by the rate row). Trailer
  canonical.
- **Resolved**: (a) A.U24.64 leaves the twin hammer's absolute 8192-byte bound "U25's" and no U25 action rewrites it;
  G7/R22 ("a rate calibrated against a real and an injected leak, never an absolute heap delta") fixes the form — the
  gap is closed here with A.U24.64's own method, agent decision (OR2.c list). (b) A.U30.13 and A.U17.04/.05 edit the same
  file's different tests — all applied (A.U30.13's own Blast says A-C merges). (c) A.S0930.04 names `UartLinkExerciser`;
  C1's rename makes it `UARTLinkDriver`.
- **Unit**: U36 (stages: U17 A.U17.04/.05/.13; U24 harness, banner; U25 device from data, C4, CRC16 arm, rate bound;
  U30 A.U30.13; U35 A.U35.22; U36 A.U36.544's pointer)
- **Depends**: M.TWIN.027-029, M.TWIN.035, M.TWIN.053; M.TEST_HELP.047, .055; A.U17.18 (plan `uart` key, GEN)
- **Blast carried by**: Part N rows renamed/withdrawn → U8 rows (SPEC); the gc-site checker's two rows hold by name
  (A.U30.16, TSC); `UART_C_PORT_CHANGELOG.md` Class B for the banner → A.U24.67 (DOCS); SPEC J text naming this file
  (A.U17.15) → SPEC
- **Kind**: test

## tests/test_digital_twin_unix_port_gc_unwedge.py (deleted)

### M.TWIN.162 The unwedge test goes with its module
- **From**: A.U25.39 (delete the module and its test)
- **Site**: `tests/test_digital_twin_unix_port_gc_unwedge.py`
- **Change**: `git rm`.
- **Resolved**: —
- **Unit**: U25
- **Depends**: M.TWIN.056
- **Blast carried by**: `scripts/test.sh` finds files by glob (no list); the gc-site checker's conditional row for
  `unwedge_heap_after_interrupt` does not apply (A.U30.16 — TSC)
- **Kind**: test

## tests/test_digital_twin_webserver_concurrency{,_arzi,_dev,_grkizi,_klkizi,_schlafzi,_wozi}.py

### M.TWIN.164 The concurrency wrappers go; the host harness derives the device set
- **From**: A.U25.46 (2) ("The per-device wrappers `tests/test_digital_twin_webserver_concurrency_<device>.py` go … once
  this harness exists; A.U24.65's generic replacement file applies only if this action lands later (A-C keeps one)"),
  A.U24.65 (2) (one generic `tests/test_digital_twin_webserver_concurrency.py` with `register_for_device(TEST_DEVICE)`),
  A.U36.546 (CLAUDE.md's two-suites bullet drops its dated example naming that file — DOCS), A.SDEP.16 / A.U28.28 /
  A.U25.43 (the wrappers' prewarm/shim lines and E402 — moot with the files)
- **Site**: the six per-device wrappers (HEAD); A.U24.65's generic file (not created)
- **Change**: at U24, A.U24.65 replaces the six wrappers with the generic file (as M.TWIN.108 does for construction);
  at U25 A.U25.46 deletes that file with its library (`tests/_webserver_concurrency_scenarios.py`, TEST_HELP) once the
  host harness runs the scenarios per device.
- **Resolved**: A.U24.65 (U24) and A.U25.46 (U25) both act on the wrappers; A.U25.46 lands later, so A.U24.65's
  generic file is an interim U24 state and the end state has none — settled by A.U25.46's own "A-C keeps one" (the
  harness).
- **Unit**: U25 (stage U24: the generic file)
- **Depends**: A.U25.46's harness (SCR), M.TEST_HELP.031/.033 (library retired)
- **Blast carried by**: `scripts/test.sh` per-device expansion has nothing to expand here after U25 (SCR);
  `digital_twin/typecheck.ini` glob — no edit (M.TWIN.075); README "Running the twin's own tests" (M.TWIN.063); CLAUDE.md
  bullet → A.U36.546 (DOCS)
- **Kind**: test

## tests/test_digital_twin_ntp.py (new)

### M.TWIN.168 The local NTP responder at L2, and a booted twin syncing, losing and regaining it
- **From**: OR140.a (13) (the responder replaces A.U35.38/.39's tolerance; the twin's normal boot expects NTP synced),
  OR141.a (5) (the dropped hand-run NTP-outage row — blocking NTP to watch the SGP40 log — is covered by the responder in
  automated tests) — A-C review fold; C2, C4, C5.
- **Site**: new `tests/test_digital_twin_ntp.py` (in-process, no HTTP).
- **Change**: header (≤ 3 lines) "The twin's local NTP responder and a generated device syncing against it: the
  responder's replies and knobs, a first sync, an outage and its recovery, and each failure reply reaching the client's
  catalog code (SPECIFICATION.md C.7.2)." Module setup per C4, the boot writing `write_responder_ntp_config()` (M.TWIN.053)
  and running one `NtpResponder` (M.TWIN.167) on a port from the file's band in the test's own coroutine (closed in
  `finally`). Cases: (1) the responder alone — a 48-byte mode-3 request over loopback gets a 48-byte mode-4 reply whose
  transmit time is within 2 s of the host's UTC; `offset_s` shifts it exactly; `"silent"` answers nothing, `"unsync"`
  LI 3 / stratum 0, `"short"` 47 bytes, `"implausible"` a time below the client's floor (read with `src_const` from
  `src/asy_ntp_client.py`); `requests` stops at `_COUNTER_CAP`, which equals `_twin_common.COUNTER_CAP`, and
  `_NTP_EPOCH_DELTA` equals the client's source value (`src_const`); a ticker task
  advancing beside `serve()` is never starved (the responder never blocks the loop). (2) device-generic
  (`generated_devices()[0]`): after the boot's first force sync `Synced` is true, the wall clock is within 2 s of the host's
  UTC, and NTP's log holds no error or warning entry — the in-process mirror of the normal-boot check (A.U35.38/.39 as
  amended). (3) outage and recovery: `mode = "silent"` from boot — `Synced` stays false, NTP's log holds its no-reply code
  in one slot, the attempts back off as C.7.2 states; then `mode = "serve"` — synced within the backoff bound. On
  `device_with("sgp40", "fram")`, the same outage with `WaitTimeNTP` above 0 and a flushed timestamped backup from a first
  boot: no restore while the responder is silent, the restore (with its `RestoreTS`) after the sync, and no SGP40 log
  entry (the wait and a timestamped restore print only). (4) `"unsync"`, `"short"`, `"implausible"` each leave
  `Synced` false with the client's `NTP_UNSYNC_REPLY`, `NTP_MALFORMED`, `NTP_IMPLAUSIBLE` entry. Tunables tagged per C3
  (`l2.ntp_sync_wait_timeout_s`, row basis U8's N.1 rule). Registers `machine.reset_test_state`; trailer canonical.
- **Resolved**: —
- **Unit**: U25 (after M.TWIN.167 in the same unit).
- **Depends**: M.TWIN.019, M.TWIN.053, M.TWIN.167; M.TEST_HELP.044, .055, .056; M.SRC_NET.046-.050 (the client's codes
  and backoff).
- **Blast carried by**: the `tests/test_digital_twin_*.py` glob picks it up (`scripts/test.sh`; `digital_twin/typecheck.ini`
  `files`, M.TWIN.075 — no edit); the port band row for this file → M.TEST_HELP.056; Part N row → SPEC (U8's rule);
  the hand-run NTP-outage row's removal from M.PROC.038 → M.PROC.038.
- **Kind**: test

## Cross-file: A-C3 sweep changes (new)

### M.TWIN.165 Docstrings become comments in this cluster's scope
- **From**: A.U10.34 (A-C3 Part S S-05: no carrier in this cluster).
- **Site**: function/class docstrings at HEAD (AST): `digital_twin/_http_client.py:48`;
  `digital_twin/unix_port_gc_unwedge.py:7`; `digital_twin/unix_port_poll_prewarm.py:30`, `:48`;
  `tests/test_digital_twin_bus_hazard_concurrency.py:90`.
- **Change**: each function, method and class docstring becomes a `#` comment block directly under the `def`/`class`
  line, same text, ≤ 3 prose lines (overflow to the owning doc per CLAUDE.md's comment rule); module docstrings stay
  (the five argparse readers included). A file a later change rewrites carries the form forward (`_http_client.py:48`
  → M.TWIN.016, `unix_port_poll_prewarm.py` → M.TWIN.057; `unix_port_gc_unwedge.py` is deleted at U25 by M.TWIN.056).
- **Resolved**: —
- **Unit**: U10.
- **Depends**: —
- **Blast carried by**: `tests_scripts/test_comment_block_cap.py` stays green → M.TSC.065.
- **Kind**: code

### M.TWIN.166 File-local builders take the private form
- **From**: A.U24.76 (A-C3 Part S S-07: these files' changes did not name it).
- **Site**: `tests/test_digital_twin_isl29125.py` (`make_chip`), `tests/test_digital_twin_isl29125_autorange.py`
  (`make_dev_reader`), `tests/test_digital_twin_machine_uart.py` (`make_link`) — one public `def make_` each at HEAD.
- **Change**: every module-level `def make_<x>` → `_make_<x>` with its uses in the file (a builder another change
  replaces by a shared helper is skipped there).
- **Resolved**: —
- **Unit**: U24.
- **Depends**: A.U24.49.
- **Blast carried by**: the L0 check (`tests_scripts/test_microtest.py`) → A.U24.76 (TSC).
- **Kind**: test

## Gaps for other clusters

- **SCR — `scripts/_digital_twin_scenarios.py` (A.U25.46 harness; also M_TEST_HELP GAP-H2)**: receives the 8 HTTP tests of
  `tests/test_digital_twin_sensortask_integration.py` with goals and assertions (M.TWIN.144 Blast lists each carried
  edit: A.U10.36 `:211`, A.U25.33/A.U10.40 `NTPHost`, A.U10.11/A.U2.13 `:300-320`, A.U9.09/A.U22.03/A.U19.03 `PauseTime`,
  A.U18.01/A.U18.03/A.U25.72 DNS answer and captive redirect, A.U10.15/A.S0930.27 mempause asserting `MemPaused` true only —
  the unpause branch is in-process, M.TWIN.104), and an equivalent of `tests/_shared_rest_roundtrip.py`'s
  `assert_sensor_payload_not_self_wrapped` on the host side; the 9 real-website tests (M.TWIN.136) and the bus-hazard burst
  (M.TWIN.102); reads `FAULT_PENDING` lines (`--test-fault-status-interval-ms`, M.TWIN.051) for A.U24.47's consumption
  proof; reads `WDT_AT_FAULT <feed_count>` for A.U35.31's three `--test-watchdog-fault` cases.
- **SCR**: `scripts/micropypath.toml` twin layout and every launch script's twin `MICROPYPATH` gain `digital_twin/unixport`
  (M.TWIN.017/.047/.053); Run 5's SGP40 fault aimed with `sgp40:readfrom_into:3:0x260F` and its expected counts re-derived
  (AC_NOTES 31; M.TWIN.014); the CI suite asserts `public_destinations_refused=0` per run log (A.U25.35).
- **TEST_HELP**: `tests/_twin_devices.py` — `device_with(*drivers)` (first generated device wiring every named driver; used
  by M.TWIN.144/.146/.150) and `devices_with_shared_bus() -> [(device, bus, occupants)]` (A.U36.015's amendment of A.U25.48
  (1); M.TWIN.102); GAP-H3 resolved by M.TWIN.053 — `tests/_generated_module.py` imports `write_offline_ntp_config` from
  `digital_twin/unixport/_offline_ntp_config.py` and drops its copy; `tests/_uart_comm_harness.py` keeps its path-resolved
  `from machine import UART, LinkPoller, UARTLink` and `Pair(crc_a=, crc_b=)` — the twin hazard files build their pair
  through it with the twin's `machine` first on the path (M.TWIN.154/.156/.158); GAP-H4: no TWIN-file change (C4 and
  M.TWIN.108's entry file serve A.U25.47's scenario).
- **TOOL**: `pyproject.toml` `mypy_path` += `digital_twin/unixport` (A.U18.12 `:365`); `:383` exclude goes (A.U25.40);
  `:294`/`:310` ANN401 per-file entries go with A.U25.63; A.U28.28 (7) PERF401 for `tests/test_digital_twin_uart_link.py`.
- **TSC**: `tests_scripts/test_twin_runner_test_flags.py` (A.U25.74) gains `--test-fault-status-interval-ms`; A.U30.16's two
  `tests/test_digital_twin_uart_link.py` rows keep their function names (M.TWIN.158).
- **HW_BENCH**: `tests_hardware/twin_board.py` `MICROPYPATH` gains `digital_twin/unixport` (M.TWIN.054, A.U26.05).
- **LEAD** (no cluster owns `.gitignore`): `digital_twin/mem_backup_state.json` ignored (A.U25.32 Blast; A.U28.33).
- **SPEC**: A.U36.517's build-chain proof names the harness; Part N rows: `l2.uart_link_collect_*` → `…_pause_*`
  (A.U17.04), `l2.uart_link_leak_budget_bytes` → `l2.uart_link_leak_rate_bytes_per_transfer` (M.TWIN.158), the withdrawn
  `l2.sensortask_integration_dns_query_*`/`…_override_poll_*` rows (M.TWIN.144), new `l2.clock_jump_wait_timeout_s`
  (M.TWIN.146); E.2.1/J.7 texts (A.U36.016, A.U36.539) name files that exist as written here.
- **DOCS**: CLAUDE.md's two-suites bullet (A.U36.546) and the four-tier UART clause (A.U17.25) name
  `tests/test_digital_twin_uart_{comm_hazard,field_sweep}.py`.

## Adherence findings (per file: rule → result; breaches fixed by M-ID or raised as Qn)

- `digital_twin/_twin_common.py`, `_wall_clock.py`, `run_device_script.py`, `unixport/*` (new): 3-line cap, no audit
  IDs (C5) → pass; imports nothing from `src/`/`tests/` where stated (G7/R02) → pass; counters saturate (OR110.a) → pass.
- `_bmp3xx_chip.py`: G7/R03 "not datasheet-derived" label → breach (`:107` false comment) fixed, M.TWIN.010.
- `_scd30_chip.py`: G7/R03 every modelling gap a fidelity row → breach (compensation unmodelled, no row) fixed, M.TWIN.013 /
  M.TWIN.059; ≤ 8 parameters (G6/R40) → pass via `SCD30Nvm`.
- `_sgp40_chip.py`, `_isl29125_chip.py`, `_fram_chip.py`, `_fault_injection.py`, `_crc8.py`: C6 citations, fresh exception
  per raise (G7/R16/OR110.a), bounded logs → pass after M.TWIN.002/.003/.011/.012/.014.
- `network.py`: fresh exception per raise (G7/R16, OR110.a no-growth) → breach (A.U25.27's stored instance) fixed, M.TWIN.040.
- `neopixel.py`, `machine.py`: rp2 semantics cited and pinned (C6), bounded logs, `TEST_API` (A.U24.18) → pass;
  bounded pollers only (CLAUDE.md hang #1) → pass.
- `launch.py`, `run_generic_integration.py`: OR125.a — `--test-*` flags off by default and kept off the production path by
  A.U25.74's L0 check → pass (M.TWIN.051); OR126.a (1) `main()` keywords → pass (M.TWIN.050); OR36/G7/R01 product
  interfaces only, the runner's stated exception named → pass; no unwedge, SIGINT override stays (CLAUDE.md) → pass.
- `README.md`: G9/R12 no audit IDs in permanent text → breach (`[src: …]` notes) fixed, M.TWIN.059; history narrative
  (OR27.a) → removed, M.TWIN.058-074.
- `typecheck.ini`: coded ignores only → pass (M.TWIN.075).
- `segfault_stress_repro.py`, `unix_port_gc_unwedge.py` and its test: deleted (M.TWIN.055/.056/.162).
- `tests/test_digital_twin_sensortask_integration.py`: G7/R19 request driving in the DUT heap → breach fixed (moved,
  M.TWIN.144); OR36-style product poke `conn.connection_failures = 4` and the mempause unpause call → removed, M.TWIN.144;
  `gc.collect()` props (OR91.a) → removed at U30, M.TWIN.144; G7/R24 device literal → fixed (per device).
- `tests/test_digital_twin_uart_link.py`: G7/R22 absolute leak delta → breach fixed (rate), M.TWIN.158; in-body
  `gc.threshold`/`gc.collect` (OR40.a/OR91.a) → removed, M.TWIN.158.
- `tests/test_digital_twin_{sgp40,scd30,isl29125*}.py`: G7/R19 in-DUT HTTP L2 cases → settled in-process, M.TWIN.122/
  .142/.150.
- Every other `tests/test_digital_twin_*` file: nested `asyncio.run()` (CLAUDE.md segfault rule) → none (fixtures built
  at synchronous scope); bounded fake pollers → pass; 3-line cap and trailer (A.U24.04) → pass after each M-ID.
- Not applicable to this cluster: `ext/`, legacy tree, credentials, wear gates, real hardware (none touched). UART
  protocol: no module change here; the banner rename is A.U24.67's Class B entry (DOCS).

## Owner questions

None — every conflict was settled by a later action, an owner row, AC_NOTES or a register rule (cited in each Resolved).

## Agent decisions for the OR2.c review

1. One `_twin_common.py` (BoundedLog public, `COUNTER_CAP`, `fill_buffer`, `Walk`, `StatePaths(fram, scd30, mem_backup)`,
   `Injections`) — M.TWIN.001.
2. `Walk` applied to all four chip fakes — M.TWIN.010-014.
3. `timer_factory` replaces `auto_refresh`; ISL `simulate_brownout` → `power_cycle` — M.TWIN.012/.013.
4. `SCD30Nvm` keeps the constructor ≤ 8 parameters; `nvm_writes` counts accepted commands — M.TWIN.013.
5. `corrupt_next()` method on SCD30 and SGP40 — M.TWIN.013/.014.
6. `fetch(timeout_s=None)` default — M.TWIN.016.
7. Shim refuses a public destination with EINVAL through the product path; shim in `digital_twin/unixport/` — M.TWIN.017.
8. `reset_test_state()` in the twin, registered by each test — M.TWIN.035.
9. `_collect_chips()` shared from `launch.py` — M.TWIN.045/.049.
10. Exit code 5 for a simulated power loss — M.TWIN.050.
11. `--test-fault-status-interval-ms` flag (consumption channel) — M.TWIN.051.
12. The runner answers `--help` — M.TWIN.047.
13. G7/R19: in-DUT HTTP L2 cases run in-process through the route's own config path — M.TWIN.122/.142/.144/.150.
14. Fidelity table drops `[src: …]` notes; WLAN `raise_on` stores type and args — M.TWIN.059/.040.
15. Offline-NTP writer moved to `digital_twin/unixport/_offline_ntp_config.py` (GAP-H3) — M.TWIN.053.
16. Hotspot test split: LED/bind in-process, DNS/redirect host-side; offline-boot case shares the watchdog test's
    `main()` window — M.TWIN.144.
17. Clock-jump L2 file created; A.U18.26 (c)/(d) stay L1 (no offline sync possible) — M.TWIN.146.
18. Twin UART hazard files reuse `tests/_uart_comm_harness.py`'s `Pair` — M.TWIN.154/.156.
19. Twin UART leak bound becomes a calibrated per-transfer rate (A.U24.64 gap) — M.TWIN.158.

## Ledger

| action ID | merged into M-ID / dropped (reason) |
|---|---|
| A.C.10 | M.TWIN.010, M.TWIN.012, M.TWIN.013, M.TWIN.040, M.TWIN.059 |
| A.C.14 | M.TWIN.040 |
| A.C.15 | M.TWIN.013, M.TWIN.059 |
| A.C.19 | M.TWIN.012, M.TWIN.059 |
| A.S0930.04 | M.TWIN.027, M.TWIN.049, M.TWIN.064, M.TWIN.154, M.TWIN.156, M.TWIN.158 |
| A.S0930.12 | M.TWIN.144 |
| A.S0930.13 | M.TWIN.144 |
| A.S0930.17 | M.TWIN.011 |
| A.S0930.24 | M.TWIN.031 |
| A.S0930.27 | M.TWIN.011, M.TWIN.026, M.TWIN.031, M.TWIN.051, M.TWIN.059, M.TWIN.064, M.TWIN.066, M.TWIN.104, M.TWIN.112, M.TWIN.144 |
| A.S0930.38 | M.TWIN.051, M.TWIN.064, M.TWIN.104, M.TWIN.110, M.TWIN.152 |
| A.S0930.41 | M.TWIN.064 |
| A.SDEP.07 | M.TWIN.136 |
| A.SDEP.08 | M.TWIN.017, M.TWIN.019, M.TWIN.021, M.TWIN.024, M.TWIN.026, M.TWIN.031, M.TWIN.057, M.TWIN.058, M.TWIN.102, M.TWIN.126 |
| A.SDEP.11 | M.TWIN.056 |
| A.SDEP.15 | M.TWIN.016, M.TWIN.057 |
| A.SDEP.16 | M.TWIN.017, M.TWIN.019, M.TWIN.029, M.TWIN.055, M.TWIN.057, M.TWIN.071, M.TWIN.073, M.TWIN.134, M.TWIN.144, M.TWIN.164 |
| A.SDEP.17 | M.TWIN.016, M.TWIN.019, M.TWIN.024, M.TWIN.070 |
| A.U0.07 | M.TWIN.010, M.TWIN.012, M.TWIN.013, M.TWIN.016, M.TWIN.020, M.TWIN.023, M.TWIN.025 |
| A.U0.29 | M.TWIN.047, M.TWIN.062, M.TWIN.144 |
| A.U0.31 | M.TWIN.002, M.TWIN.016, M.TWIN.044, M.TWIN.058, M.TWIN.060, M.TWIN.062, M.TWIN.068, M.TWIN.072, M.TWIN.073, M.TWIN.075 |
| A.U0.38 | M.TWIN.022, M.TWIN.036, M.TWIN.047 |
| A.U0.43 | M.TWIN.064 |
| A.U0.54 | M.TWIN.052, M.TWIN.065 |
| A.U0.59 | dropped (void by its own condition: A.U25.01 turns the paragraph into a pointer — M.TWIN.059 Resolved) |
| A.U1.04 | M.TWIN.027 |
| A.U1.08 | M.TWIN.027 |
| A.U1.25 | M.TWIN.027, M.TWIN.036 |
| A.U10.07 | M.TWIN.031, M.TWIN.144 |
| A.U10.11 | M.TWIN.144 |
| A.U10.12 | M.TWIN.102, M.TWIN.126, M.TWIN.144, M.TWIN.152 |
| A.U10.15 | M.TWIN.144 |
| A.U10.18 | M.TWIN.102 |
| A.U10.23 | M.TWIN.144 |
| A.U10.28 | M.TWIN.019, M.TWIN.033, M.TWIN.146 |
| A.U10.30 | M.TWIN.047, M.TWIN.054 |
| A.U10.36 | M.TWIN.060, M.TWIN.144 |
| A.U10.37 | M.TWIN.003, M.TWIN.064, M.TWIN.069, M.TWIN.071, M.TWIN.075 |
| A.U10.38 | M.TWIN.017, M.TWIN.075 |
| A.U10.40 | M.TWIN.053, M.TWIN.064, M.TWIN.075, M.TWIN.144 |
| A.U10.44 | M.TWIN.102, M.TWIN.144 |
| A.U11.01 | M.TWIN.158 |
| A.U11.03 | M.TWIN.064 |
| A.U11.05 | M.TWIN.032, M.TWIN.075 |
| A.U11.07 | M.TWIN.059 |
| A.U11.08 | M.TWIN.065 |
| A.U11.09 | M.TWIN.011 |
| A.U11.10 | M.TWIN.050 |
| A.U11.24 | M.TWIN.102, M.TWIN.144 |
| A.U11.31 | M.TWIN.064, M.TWIN.067 |
| A.U12.18 | M.TWIN.014, M.TWIN.024, M.TWIN.102 |
| A.U13.R01 | M.TWIN.021, M.TWIN.024, M.TWIN.049 |
| A.U13.R02 | M.TWIN.021, M.TWIN.102 |
| A.U13.03 | M.TWIN.011, M.TWIN.021 |
| A.U13.07 | M.TWIN.102 |
| A.U13.10 | M.TWIN.102 |
| A.U13.12 | M.TWIN.028, M.TWIN.059, M.TWIN.130, M.TWIN.158 |
| A.U13.13 | M.TWIN.028, M.TWIN.059, M.TWIN.130, M.TWIN.158 |
| A.U13.17 | M.TWIN.158 |
| A.U14.R01 | M.TWIN.064 |
| A.U14.12 | M.TWIN.030 |
| A.U14.14 | M.TWIN.024 |
| A.U14.17 | M.TWIN.021 |
| A.U14.20 | M.TWIN.059 |
| A.U14.21 | M.TWIN.026 |
| A.U14.28 | M.TWIN.017, M.TWIN.057, M.TWIN.058, M.TWIN.071, M.TWIN.073, M.TWIN.144 |
| A.U14.33 | M.TWIN.019, M.TWIN.027, M.TWIN.031 |
| A.U14.37 | M.TWIN.040 |
| A.U15.R01 | M.TWIN.013, M.TWIN.102 |
| A.U15.R02 | M.TWIN.014, M.TWIN.102, M.TWIN.140 |
| A.U15.R03 | M.TWIN.010, M.TWIN.100 |
| A.U15.R05 | M.TWIN.122 |
| A.U15.S01 | M.TWIN.102 |
| A.U15.01 | M.TWIN.013 |
| A.U15.05 | M.TWIN.059 |
| A.U15.06 | M.TWIN.062 |
| A.U15.08 | M.TWIN.062 |
| A.U15.12 | M.TWIN.013, M.TWIN.102, M.TWIN.142 |
| A.U15.13 | M.TWIN.014, M.TWIN.150 |
| A.U15.14 | M.TWIN.014 |
| A.U15.17 | M.TWIN.144 |
| A.U15.19 | M.TWIN.150 |
| A.U15.25 | M.TWIN.010, M.TWIN.102 |
| A.U15.28 | M.TWIN.012, M.TWIN.013, M.TWIN.014 |
| A.U15.30 | M.TWIN.120 |
| A.U15.32 | M.TWIN.012, M.TWIN.102, M.TWIN.122 |
| A.U15.33 | M.TWIN.102 |
| A.U15.36 | M.TWIN.122 |
| A.U15.37 | M.TWIN.012 |
| A.U15.39 | M.TWIN.122, M.TWIN.126 |
| A.U15.41 | M.TWIN.144, M.TWIN.152 |
| A.U16.R01 | M.TWIN.011, M.TWIN.110 |
| A.U16.R02 | M.TWIN.114 |
| A.U16.R03 | M.TWIN.110 |
| A.U16.01 | M.TWIN.158 |
| A.U16.06 | M.TWIN.110 |
| A.U16.09 | M.TWIN.011, M.TWIN.110 |
| A.U16.10 | M.TWIN.102 |
| A.U16.16 | M.TWIN.021 |
| A.U16.17 | M.TWIN.114 |
| A.U16.19 | M.TWIN.102 |
| A.U17.04 | M.TWIN.158 |
| A.U17.05 | M.TWIN.158 |
| A.U17.13 | M.TWIN.158 |
| A.U17.15 | M.TWIN.158 |
| A.U17.18 | M.TWIN.049, M.TWIN.061, M.TWIN.158 |
| A.U17.25 | M.TWIN.027, M.TWIN.154, M.TWIN.156 |
| A.U18.R01 | M.TWIN.040, M.TWIN.144 |
| A.U18.01 | M.TWIN.144 |
| A.U18.03 | M.TWIN.144 |
| A.U18.12 | M.TWIN.017, M.TWIN.053, M.TWIN.071, M.TWIN.075, M.TWIN.144 |
| A.U18.13 | M.TWIN.017 |
| A.U18.23 | M.TWIN.030, M.TWIN.152 |
| A.U18.27 | M.TWIN.040 |
| A.U18.28 | M.TWIN.040 |
| A.U18.30 | M.TWIN.040, M.TWIN.132 |
| A.U18.32 | M.TWIN.040 |
| A.U18.33 | M.TWIN.040 |
| A.U19.03 | M.TWIN.144 |
| A.U19.17 | M.TWIN.016 |
| A.U19.20 | M.TWIN.055, M.TWIN.102 |
| A.U2.09 | M.TWIN.011 |
| A.U2.12 | M.TWIN.122 |
| A.U2.13 | M.TWIN.144 |
| A.U20.02 | M.TWIN.045, M.TWIN.050, M.TWIN.055, M.TWIN.061, M.TWIN.102, M.TWIN.136, M.TWIN.140, M.TWIN.144, M.TWIN.158 |
| A.U20.06 | M.TWIN.050, M.TWIN.060, M.TWIN.102, M.TWIN.144 |
| A.U20.28 | M.TWIN.020, M.TWIN.025, M.TWIN.049, M.TWIN.050, M.TWIN.061, M.TWIN.072, M.TWIN.114, M.TWIN.140, M.TWIN.144 |
| A.U20.42 | M.TWIN.049, M.TWIN.055 |
| A.U22.03 | M.TWIN.144 |
| A.U23.33 | M.TWIN.034 |
| A.U23.47 | M.TWIN.136 |
| A.U24.01 | M.TWIN.136 |
| A.U24.04 | M.TWIN.100, M.TWIN.108, M.TWIN.134, M.TWIN.144 |
| A.U24.06 | M.TWIN.130 |
| A.U24.07 | M.TWIN.035 |
| A.U24.08 | M.TWIN.057, M.TWIN.102, M.TWIN.118, M.TWIN.136, M.TWIN.140, M.TWIN.144, M.TWIN.158 |
| A.U24.09 | M.TWIN.040 |
| A.U24.12 | M.TWIN.126 |
| A.U24.15 | M.TWIN.028, M.TWIN.029, M.TWIN.158 |
| A.U24.16 | M.TWIN.021 |
| A.U24.17 | M.TWIN.002, M.TWIN.021, M.TWIN.024, M.TWIN.028, M.TWIN.030, M.TWIN.031, M.TWIN.034, M.TWIN.059, M.TWIN.126 |
| A.U24.18 | M.TWIN.019, M.TWIN.021, M.TWIN.024, M.TWIN.026, M.TWIN.027, M.TWIN.028, M.TWIN.029, M.TWIN.030, M.TWIN.031, M.TWIN.033, M.TWIN.072 |
| A.U24.19 | M.TWIN.040 |
| A.U24.20 | M.TWIN.024, M.TWIN.059 |
| A.U24.22 | M.TWIN.011 |
| A.U24.23 | M.TWIN.026 |
| A.U24.26 | M.TWIN.059 |
| A.U24.27 | M.TWIN.102 |
| A.U24.29 | M.TWIN.102 |
| A.U24.30 | M.TWIN.010, M.TWIN.013, M.TWIN.100, M.TWIN.120, M.TWIN.126, M.TWIN.142, M.TWIN.150 |
| A.U24.34 | M.TWIN.016, M.TWIN.102 |
| A.U24.35 | dropped (withdrawn by its own unit; its content carried by A.U25.31 (1) — M.TWIN.016) |
| A.U24.36 | M.TWIN.102 |
| A.U24.38 | M.TWIN.100, M.TWIN.142 |
| A.U24.40 | M.TWIN.118 |
| A.U24.46 | M.TWIN.047, M.TWIN.140 |
| A.U24.53 | M.TWIN.047, M.TWIN.060, M.TWIN.066 |
| A.U24.56 | M.TWIN.140 |
| A.U24.60 | M.TWIN.016, M.TWIN.136 |
| A.U24.64 | M.TWIN.158 |
| A.U24.65 | M.TWIN.075, M.TWIN.108, M.TWIN.144, M.TWIN.164 |
| A.U24.67 | M.TWIN.158 |
| A.U24.68 | not a TWIN site (`scripts/run_unix_port_integration.sh`, SCR); blast-only on the runner — holds (the runner already takes `--device`, M.TWIN.047) |
| A.U24.69 | not a TWIN site (port lock, SCR/WEB); blast-only — holds (the in-process hotspot half of M.TWIN.144 binds 53 under `scripts/test.sh`'s lock) |
| A.U24.70 | M.TWIN.057, M.TWIN.102, M.TWIN.118, M.TWIN.136, M.TWIN.140, M.TWIN.144 |
| A.U24.73 | M.TWIN.144 |
| A.U24.77 | M.TWIN.027 |
| A.U24.80 | M.TWIN.028, M.TWIN.029, M.TWIN.049, M.TWIN.059, M.TWIN.130, M.TWIN.158 |
| A.U24.82 | M.TWIN.002, M.TWIN.058, M.TWIN.068 |
| A.U25.01 | M.TWIN.010, M.TWIN.058, M.TWIN.059, M.TWIN.062, M.TWIN.072, M.TWIN.073, M.TWIN.100, M.TWIN.114, M.TWIN.150 |
| A.U25.02 | M.TWIN.021, M.TWIN.126, M.TWIN.138 |
| A.U25.03 | M.TWIN.024, M.TWIN.026, M.TWIN.035, M.TWIN.049, M.TWIN.058, M.TWIN.102, M.TWIN.110, M.TWIN.114, M.TWIN.122, M.TWIN.126, M.TWIN.136, M.TWIN.144, M.TWIN.158 |
| A.U25.04 | M.TWIN.028, M.TWIN.059, M.TWIN.130, M.TWIN.138, M.TWIN.154, M.TWIN.158 |
| A.U25.05 | M.TWIN.021, M.TWIN.102 |
| A.U25.06 | M.TWIN.001, M.TWIN.011, M.TWIN.024, M.TWIN.026, M.TWIN.110, M.TWIN.126 |
| A.U25.07 | M.TWIN.034, M.TWIN.063, M.TWIN.110, M.TWIN.128 |
| A.U25.08 | M.TWIN.022, M.TWIN.032, M.TWIN.046, M.TWIN.058, M.TWIN.059, M.TWIN.062, M.TWIN.128, M.TWIN.138 |
| A.U25.09 | M.TWIN.001, M.TWIN.034, M.TWIN.044, M.TWIN.046, M.TWIN.047, M.TWIN.050, M.TWIN.058, M.TWIN.064, M.TWIN.066, M.TWIN.110, M.TWIN.140 |
| A.U25.10 | M.TWIN.014, M.TWIN.024, M.TWIN.058, M.TWIN.102, M.TWIN.126, M.TWIN.150 |
| A.U25.11 | M.TWIN.013, M.TWIN.014, M.TWIN.059, M.TWIN.102, M.TWIN.150 |
| A.U25.12 | M.TWIN.013, M.TWIN.062, M.TWIN.126, M.TWIN.142 |
| A.U25.13 | M.TWIN.010, M.TWIN.100 |
| A.U25.14 | M.TWIN.012, M.TWIN.059, M.TWIN.120 |
| A.U25.15 | M.TWIN.011, M.TWIN.049, M.TWIN.104, M.TWIN.110, M.TWIN.114 |
| A.U25.16 | M.TWIN.026, M.TWIN.110, M.TWIN.126, M.TWIN.138 |
| A.U25.17 | M.TWIN.024, M.TWIN.126 |
| A.U25.18 | M.TWIN.002, M.TWIN.010, M.TWIN.011, M.TWIN.044, M.TWIN.068, M.TWIN.110, M.TWIN.124 |
| A.U25.19 | M.TWIN.012, M.TWIN.013, M.TWIN.023, M.TWIN.030, M.TWIN.128, M.TWIN.138, M.TWIN.152 |
| A.U25.20 | M.TWIN.019, M.TWIN.033, M.TWIN.128 |
| A.U25.21 | M.TWIN.042, M.TWIN.058, M.TWIN.132, M.TWIN.138, M.TWIN.144 |
| A.U25.22 | M.TWIN.001, M.TWIN.020, M.TWIN.024, M.TWIN.026, M.TWIN.027, M.TWIN.028, M.TWIN.031, M.TWIN.040, M.TWIN.042, M.TWIN.052, M.TWIN.058, M.TWIN.102, M.TWIN.126, M.TWIN.130, M.TWIN.132 |
| A.U25.23 | M.TWIN.001, M.TWIN.012, M.TWIN.013, M.TWIN.014, M.TWIN.019, M.TWIN.027, M.TWIN.028, M.TWIN.031, M.TWIN.034, M.TWIN.040, M.TWIN.045, M.TWIN.126, M.TWIN.128, M.TWIN.130 |
| A.U25.24 | M.TWIN.022, M.TWIN.032, M.TWIN.035, M.TWIN.036, M.TWIN.040, M.TWIN.061, M.TWIN.126, M.TWIN.144 |
| A.U25.25 | M.TWIN.020, M.TWIN.022, M.TWIN.044, M.TWIN.045, M.TWIN.058, M.TWIN.061, M.TWIN.072, M.TWIN.114, M.TWIN.122, M.TWIN.124, M.TWIN.126, M.TWIN.136, M.TWIN.144, M.TWIN.158 |
| A.U25.26 | M.TWIN.040, M.TWIN.058, M.TWIN.132 |
| A.U25.27 | M.TWIN.040, M.TWIN.044, M.TWIN.045, M.TWIN.049, M.TWIN.068, M.TWIN.124, M.TWIN.132, M.TWIN.144 |
| A.U25.28 | M.TWIN.022, M.TWIN.035, M.TWIN.036, M.TWIN.045, M.TWIN.047, M.TWIN.049, M.TWIN.051, M.TWIN.055, M.TWIN.061, M.TWIN.140 |
| A.U25.29 | M.TWIN.011, M.TWIN.025, M.TWIN.058, M.TWIN.110, M.TWIN.114 |
| A.U25.30 | M.TWIN.027, M.TWIN.130 |
| A.U25.31 | M.TWIN.016, M.TWIN.058, M.TWIN.070, M.TWIN.102, M.TWIN.118 |
| A.U25.32 | M.TWIN.011, M.TWIN.013, M.TWIN.032, M.TWIN.044, M.TWIN.047, M.TWIN.050, M.TWIN.060, M.TWIN.062, M.TWIN.066, M.TWIN.110, M.TWIN.124, M.TWIN.140, M.TWIN.142 |
| A.U25.33 | M.TWIN.017, M.TWIN.040, M.TWIN.047, M.TWIN.050, M.TWIN.053, M.TWIN.054, M.TWIN.058, M.TWIN.059, M.TWIN.061, M.TWIN.064, M.TWIN.066, M.TWIN.071, M.TWIN.102, M.TWIN.136, M.TWIN.144, M.TWIN.146 |
| A.U25.34 | M.TWIN.017, M.TWIN.050, M.TWIN.054, M.TWIN.064, M.TWIN.071, M.TWIN.108, M.TWIN.144 |
| A.U25.35 | M.TWIN.017, M.TWIN.047, M.TWIN.050, M.TWIN.064 |
| A.U25.36 | M.TWIN.001, M.TWIN.024, M.TWIN.050, M.TWIN.064, M.TWIN.140 |
| A.U25.37 | M.TWIN.011, M.TWIN.012, M.TWIN.014, M.TWIN.044, M.TWIN.045, M.TWIN.049, M.TWIN.064, M.TWIN.067, M.TWIN.068, M.TWIN.069, M.TWIN.124, M.TWIN.140, M.TWIN.158 |
| A.U25.38 | M.TWIN.064 |
| A.U25.39 | M.TWIN.044, M.TWIN.046, M.TWIN.047, M.TWIN.050, M.TWIN.056, M.TWIN.058, M.TWIN.073, M.TWIN.162 |
| A.U25.40 | M.TWIN.017, M.TWIN.055, M.TWIN.058, M.TWIN.073, M.TWIN.075 |
| A.U25.41 | M.TWIN.010, M.TWIN.044, M.TWIN.045, M.TWIN.046, M.TWIN.047, M.TWIN.049, M.TWIN.050, M.TWIN.060, M.TWIN.124, M.TWIN.140 |
| A.U25.42 | M.TWIN.010, M.TWIN.012, M.TWIN.013, M.TWIN.014, M.TWIN.016, M.TWIN.020, M.TWIN.023, M.TWIN.025, M.TWIN.030, M.TWIN.044, M.TWIN.045, M.TWIN.047, M.TWIN.049, M.TWIN.072 |
| A.U25.43 | M.TWIN.017, M.TWIN.050, M.TWIN.054, M.TWIN.057, M.TWIN.058, M.TWIN.073, M.TWIN.108, M.TWIN.140, M.TWIN.144, M.TWIN.164 |
| A.U25.44 | M.TWIN.020, M.TWIN.047, M.TWIN.053, M.TWIN.060, M.TWIN.064 |
| A.U25.45 | M.TWIN.136, M.TWIN.144 |
| A.U25.46 | M.TWIN.051, M.TWIN.057, M.TWIN.060, M.TWIN.063, M.TWIN.065, M.TWIN.075, M.TWIN.102, M.TWIN.122, M.TWIN.136, M.TWIN.142, M.TWIN.144, M.TWIN.150, M.TWIN.164 |
| A.U25.47 | not a TWIN site (`tests/_digital_twin_construction_scenarios.py`, TEST_HELP GAP-H4); its twin boot uses C4 and the entry file M.TWIN.108 — holds |
| A.U25.48 | M.TWIN.058, M.TWIN.060, M.TWIN.064, M.TWIN.102, M.TWIN.136, M.TWIN.140, M.TWIN.144, M.TWIN.158 |
| A.U25.49 | M.TWIN.012, M.TWIN.120, M.TWIN.122 |
| A.U25.50 | M.TWIN.102, M.TWIN.144 |
| A.U25.51 | M.TWIN.100, M.TWIN.102, M.TWIN.118, M.TWIN.126, M.TWIN.128, M.TWIN.142 |
| A.U25.52 | M.TWIN.012, M.TWIN.058, M.TWIN.126 |
| A.U25.53 | M.TWIN.114 |
| A.U25.54 | M.TWIN.026, M.TWIN.032, M.TWIN.034, M.TWIN.050, M.TWIN.059, M.TWIN.112 |
| A.U25.55 | M.TWIN.059, M.TWIN.064 |
| A.U25.56 | M.TWIN.030, M.TWIN.152 |
| A.U25.57 | M.TWIN.102, M.TWIN.144 |
| A.U25.58 | not a TWIN site (`tests_scripts/`, TSC) |
| A.U25.59 | M.TWIN.010, M.TWIN.012, M.TWIN.013, M.TWIN.014, M.TWIN.024, M.TWIN.035, M.TWIN.058, M.TWIN.059, M.TWIN.068, M.TWIN.072, M.TWIN.100, M.TWIN.116 |
| A.U25.60 | M.TWIN.122 |
| A.U25.61 | not a TWIN site (`tests_hardware/device_scripts/`, HW_DEV) |
| A.U25.62 | M.TWIN.010, M.TWIN.011, M.TWIN.012, M.TWIN.013, M.TWIN.014, M.TWIN.020, M.TWIN.023, M.TWIN.025, M.TWIN.058, M.TWIN.062, M.TWIN.068, M.TWIN.072, M.TWIN.100, M.TWIN.110, M.TWIN.120, M.TWIN.142, M.TWIN.150 |
| A.U25.63 | M.TWIN.016, M.TWIN.020, M.TWIN.022, M.TWIN.023, M.TWIN.024, M.TWIN.040 (AC3 S-09), M.TWIN.045, M.TWIN.047, M.TWIN.057, M.TWIN.075, M.TWIN.134 |
| A.U25.64 | M.TWIN.064 |
| A.U25.65 | M.TWIN.064, M.TWIN.067, M.TWIN.071, M.TWIN.075, M.TWIN.144 |
| A.U25.66 | not a TWIN site (`scripts/_digital_twin_ci_suite.py`, SCR) |
| A.U25.67 | M.TWIN.022, M.TWIN.023, M.TWIN.072, M.TWIN.158 |
| A.U25.68 | M.TWIN.002, M.TWIN.011, M.TWIN.012, M.TWIN.013, M.TWIN.014, M.TWIN.021, M.TWIN.026, M.TWIN.028, M.TWIN.030, M.TWIN.031, M.TWIN.032, M.TWIN.033, M.TWIN.036, M.TWIN.042, M.TWIN.059, M.TWIN.072, M.TWIN.138 |
| A.U25.69 | M.TWIN.050, M.TWIN.061 |
| A.U25.70 | M.TWIN.002, M.TWIN.010, M.TWIN.011, M.TWIN.012, M.TWIN.013, M.TWIN.014, M.TWIN.040, M.TWIN.044, M.TWIN.045, M.TWIN.049, M.TWIN.058, M.TWIN.068, M.TWIN.072, M.TWIN.100, M.TWIN.124, M.TWIN.142, M.TWIN.150 |
| A.U25.71 | M.TWIN.019, M.TWIN.033, M.TWIN.050, M.TWIN.058, M.TWIN.059, M.TWIN.128, M.TWIN.146 |
| A.U25.72 | M.TWIN.040, M.TWIN.058, M.TWIN.132, M.TWIN.144 |
| A.U25.73 | M.TWIN.010, M.TWIN.012, M.TWIN.013, M.TWIN.014, M.TWIN.072, M.TWIN.142, M.TWIN.150 |
| A.U25.74 | M.TWIN.051, M.TWIN.066 |
| A.U26.05 | M.TWIN.013, M.TWIN.054, M.TWIN.074 |
| A.U26.07 | M.TWIN.013 |
| A.U26.32 | M.TWIN.102 |
| A.U26.53 | M.TWIN.120 |
| A.U26.70 | M.TWIN.016 |
| A.U27.01 | M.TWIN.050 |
| A.U27.03 | M.TWIN.136 |
| A.U27.08 | M.TWIN.065 |
| A.U27.15 | M.TWIN.058, M.TWIN.060, M.TWIN.061, M.TWIN.063 |
| A.U27.16 | M.TWIN.064 |
| A.U27.17 | M.TWIN.052, M.TWIN.064, M.TWIN.065 |
| A.U27.22 | M.TWIN.073, M.TWIN.075 |
| A.U27.23 | M.TWIN.073, M.TWIN.075 |
| A.U27.32 | M.TWIN.060, M.TWIN.064 |
| A.U28.27 | M.TWIN.040 |
| A.U28.28 | M.TWIN.057, M.TWIN.102, M.TWIN.122, M.TWIN.132, M.TWIN.144, M.TWIN.158, M.TWIN.164 |
| A.U28.29 | M.TWIN.044, M.TWIN.132 |
| A.U28.33 | not a TWIN site (`.gitignore`, LEAD gap); blast-only — the persistent state files it names are M.TWIN.044/.050's (holds) |
| A.U28.35 | M.TWIN.011, M.TWIN.025 |
| A.U3.04 | M.TWIN.011 |
| A.U3.14 | M.TWIN.122 |
| A.U30.05 | M.TWIN.142 |
| A.U30.06 | M.TWIN.014 |
| A.U30.07 | M.TWIN.102 |
| A.U30.09 | M.TWIN.065 |
| A.U30.13 | M.TWIN.158 |
| A.U30.14 | not a TWIN site (checker, TSC); blast-only — the runner's `--gc-threshold` set stays its one allowed site (M.TWIN.047, holds) |
| A.U30.15 | M.TWIN.055, M.TWIN.144, M.TWIN.158 |
| A.U30.16 | M.TWIN.052, M.TWIN.056, M.TWIN.144, M.TWIN.158, M.TWIN.162 |
| A.U30.17 | M.TWIN.052, M.TWIN.065 |
| A.U30.18 | M.TWIN.054 |
| A.U30.21 | M.TWIN.024 |
| A.U31.03 | M.TWIN.144 |
| A.U31.06 | M.TWIN.051, M.TWIN.066 |
| A.U31.13 | M.TWIN.132 |
| A.U31.15 | M.TWIN.040 |
| A.U32.06 | M.TWIN.102, M.TWIN.144, M.TWIN.158 |
| A.U34.11 | M.TWIN.075 |
| A.U35.09 | M.TWIN.063, M.TWIN.102 |
| A.U35.14 | M.TWIN.132 |
| A.U35.21 | M.TWIN.102 |
| A.U35.22 | M.TWIN.158 |
| A.U35.25 | M.TWIN.052, M.TWIN.065 |
| A.U35.26 | M.TWIN.052, M.TWIN.060, M.TWIN.065 |
| A.U35.31 | M.TWIN.031, M.TWIN.051, M.TWIN.059, M.TWIN.066, M.TWIN.144 |
| A.U35.38 | M.TWIN.064 |
| A.U35.49 | M.TWIN.054, M.TWIN.074 |
| A.U35.50 | M.TWIN.102 |
| A.U36.004 | M.TWIN.136 |
| A.U36.015 | M.TWIN.102 |
| A.U36.016 | M.TWIN.063, M.TWIN.144, M.TWIN.146 |
| A.U36.020 | M.TWIN.122, M.TWIN.126 |
| A.U36.024 | M.TWIN.058, M.TWIN.060, M.TWIN.064, M.TWIN.075 |
| A.U36.037 | M.TWIN.056 |
| A.U36.039 | M.TWIN.025, M.TWIN.026, M.TWIN.072 |
| A.U36.040 | M.TWIN.057, M.TWIN.058, M.TWIN.073 |
| A.U36.041 | M.TWIN.059, M.TWIN.062 |
| A.U36.043 | M.TWIN.050, M.TWIN.055 |
| A.U36.511 | M.TWIN.075 |
| A.U36.512 | M.TWIN.102, M.TWIN.136 |
| A.U36.513 | M.TWIN.047, M.TWIN.050, M.TWIN.058, M.TWIN.060, M.TWIN.061, M.TWIN.140 |
| A.U36.515 | M.TWIN.072 |
| A.U36.516 | M.TWIN.072 |
| A.U36.517 | M.TWIN.136 |
| A.U36.518 | M.TWIN.022, M.TWIN.061 |
| A.U36.532 | M.TWIN.028, M.TWIN.036, M.TWIN.064 |
| A.U36.533 | not a TWIN site (CLAUDE.md, DOCS); blast-only — `digital_twin/README.md` as the twin's fact home holds (C5) |
| A.U36.539 | M.TWIN.154, M.TWIN.156 |
| A.U36.543 | M.TWIN.025, M.TWIN.072 |
| A.U36.544 | M.TWIN.017, M.TWIN.022, M.TWIN.036, M.TWIN.040, M.TWIN.071, M.TWIN.102, M.TWIN.110, M.TWIN.158 |
| A.U36.546 | M.TWIN.044, M.TWIN.045, M.TWIN.164 |
| A.U36.547 | M.TWIN.044, M.TWIN.058, M.TWIN.060, M.TWIN.066 |
| A.U37.02 | M.TWIN.075 |
| A.U37.04 | M.TWIN.059 |
| A.U4.02 | M.TWIN.013, M.TWIN.102, M.TWIN.144 |
| A.U4.04 | M.TWIN.013, M.TWIN.062, M.TWIN.142 |
| A.U4.05 | M.TWIN.013 |
| A.U4.06 | M.TWIN.013, M.TWIN.059, M.TWIN.142 |
| A.U5.02 | M.TWIN.064 |
| A.U5.15 | M.TWIN.001, M.TWIN.010, M.TWIN.012, M.TWIN.013, M.TWIN.014, M.TWIN.023, M.TWIN.036, M.TWIN.044, M.TWIN.047, M.TWIN.072, M.TWIN.100, M.TWIN.120, M.TWIN.124, M.TWIN.140, M.TWIN.142, M.TWIN.150 |
| A.U5.17 | M.TWIN.013, M.TWIN.028 |
| A.U5.18 | M.TWIN.013, M.TWIN.028 |
| A.U6.04 | M.TWIN.072 |
| A.U6.10 | not a TWIN site (`tests_js/`, WEB M.WEB); blast-only — the runner flags it passes exist (M.TWIN.047, holds) |
| A.U6.29 | M.TWIN.040 |
| A.U6.30 | M.TWIN.040 |
| A.U7.01 | M.TWIN.058 |
| A.U7.09 | M.TWIN.064 |
| A.U7.19 | M.TWIN.044, M.TWIN.047, M.TWIN.124 |
| A.U8.08 | M.TWIN.031, M.TWIN.044, M.TWIN.045, M.TWIN.050, M.TWIN.054, M.TWIN.124, M.TWIN.126, M.TWIN.144 |
| A.U8.10 | M.TWIN.040 |
| A.U8.14 | M.TWIN.047, M.TWIN.140, M.TWIN.158 |
| A.U8.15 | M.TWIN.102 |
| A.U8.18 | M.TWIN.136 |
| A.U8.20 | M.TWIN.040, M.TWIN.044, M.TWIN.049, M.TWIN.052, M.TWIN.055 |
| A.U8.24 | M.TWIN.020, M.TWIN.073, M.TWIN.075 |
| A.U8C.24 | M.TWIN.102, M.TWIN.144 |
| A.U8C.25 | M.TWIN.118 |
| A.U8C.26 | M.TWIN.044, M.TWIN.124 |
| A.U8C.27 | M.TWIN.126 |
| A.U8C.28 | M.TWIN.130 |
| A.U8C.29 | M.TWIN.132 |
| A.U8C.30 | M.TWIN.136 |
| A.U8C.31 | M.TWIN.140 |
| A.U8C.32 | M.TWIN.144 |
| A.U8C.33 | M.TWIN.158 |
| A.U8C.120 | M.TWIN.124, M.TWIN.132, M.TWIN.144 |
| A.U8C2.08 | M.TWIN.102 |
| A.U8C2.09 | M.TWIN.044, M.TWIN.124 |
| A.U8C2.10 | M.TWIN.036, M.TWIN.126 |
| A.U8C2.11 | M.TWIN.144 |
| A.U8C2.12 | M.TWIN.158 |
| A.U9.01 | M.TWIN.144, M.TWIN.146 |
| A.U9.09 | M.TWIN.144 |
| A.U19.14 | M.TWIN.067 (gap pass G3) |
| A.U30.19 | M.TWIN.044, M.TWIN.045, M.TWIN.059, M.TWIN.064, M.TWIN.068, M.TWIN.124 (gap pass G3) |
| A.U35.28 | M.TWIN.011, M.TWIN.050, M.TWIN.059, M.TWIN.110, M.TWIN.140 (gap pass G3) |
| A.U26.58 | M.TWIN.059 (gap pass G3) |
| A.U15.R04 | M.TWIN.102 (gap pass G3) |
| A.U22.01 | M.TWIN.132 (gap pass G3) |
| A.U10.34 | M.TWIN.165 (AC3 S-05: new change) |
| A.U24.76 | M.TWIN.166 (AC3 S-07: new change) |
| AC3 S-09 | M.TWIN.040 amended: From gains A.U25.63; no explicit `Any` (adapted: the two logs are `BoundedLog`, not `deque`, at the end state) |
| AC3 O-15 | M.TWIN.019 amended: the `install()` comment cites no owner row |
| AC3 O-17 | M.TWIN.052 amended: the sampler comment names the check, the verdict clause only if B3 keeps the collect |
| AC3 O-18 | M.TWIN.062 amended: the mem_backup paragraph cites no change ID |
| AC3 O-23 | M.TWIN.044 amended: the header tag reads "(owner, 2026-08-12: …)" |

## A-C2 order notes (2026-10-01)

Unit and Depends edits made by the A-C2 work order (`audit/order/WORK_ORDER.md`); one row per edit.

| M-ID | slot | edit | reason |
|---|---|---|---|
| M.TWIN.019 | Depends | `M.TWIN.033 (RTC reads `installed()`)` → `M.TWIN.033 [follows] (its RTC reads `installed()`); the two land in one U25 commit (A-C2)` | change-level cycle M.TWIN.019<->.033: the RTC needs this module, this module only names the RTC; settled as one co-landing commit |
| M.TWIN.021 | Unit | appended: A-C2 step order: A.U14.17's part lands in U13 (A.U14.17 (a)'s code half lands with A.U13.R01 in U13 (M.SRC_SENS.008/.009: the boot clear is called from I2C.__init__ there, so every fake and the generated call move with it)). | a part lands outside the Unit slot's units by an action's own text |
| M.TWIN.027 | Unit | appended: A-C2 step order: A.U17.25's part lands in U25, not U17 (it follows A.U17.25's own change, which lands in U25). | dependency deferral (an edge ran from a later step) |
| M.TWIN.033 | Unit | appended: A-C2 step order: A.U10.28's part lands in U16, not U10 (it follows A.U10.28's own change, which lands in U16). | dependency deferral (an edge ran from a later step) |
| M.TWIN.050 | Unit | appended: A-C2 step order: A.U24.47's part lands in U25, not U24 (it follows A.U24.47's own change, which lands in U25). | dependency deferral (an edge ran from a later step) |
| M.TWIN.051 | Unit | appended: A-C2 step order: A.U24.47's part lands in U25, not U24 (it follows A.U24.47's own change, which lands in U25). | dependency deferral (an edge ran from a later step) |
| M.TWIN.057 | Unit | appended: A-C2 step order: A.U24.70's part lands in U25, not U24 (it follows A.U24.70's own change, which lands in U25). | dependency deferral (an edge ran from a later step) |
| M.TWIN.102 | Unit | appended: A-C2 step order: A.U24.70's part lands in U25, not U24 (it follows A.U24.70's own change, which lands in U25). | dependency deferral (an edge ran from a later step) |
| M.TWIN.108 | Unit | appended: A-C2 step order: A.U24.65's part lands in U25, not U24 (it follows A.U24.65's own change, which lands in U25). | dependency deferral (an edge ran from a later step) |
| M.TWIN.118 | Unit | appended: A-C2 step order: A.U24.70's part lands in U25, not U24 (it follows A.U24.70's own change, which lands in U25). | dependency deferral (an edge ran from a later step) |
| M.TWIN.122 | Unit | appended: A-C2 step order: A.U2.12's part lands in U3, not U2 (it follows A.U2.12's own change, which lands in U3). | dependency deferral (an edge ran from a later step) |
| M.TWIN.136 | Unit | appended: A-C2 step order: A.U24.70's part lands in U25, not U24 (it follows A.U24.70's own change, which lands in U25). | dependency deferral (an edge ran from a later step) |
| M.TWIN.140 | Unit | appended: A-C2 step order: A.U24.70's part lands in U25, not U24 (it follows A.U24.70's own change, which lands in U25). | dependency deferral (an edge ran from a later step) |
| M.TWIN.144 | Unit | appended: A-C2 step order: A.U24.70's part lands in U25, not U24 (it follows A.U24.70's own change, which lands in U25). | dependency deferral (an edge ran from a later step) |
| M.TWIN.154 | Unit | appended: A-C2: "S0930" is not a unit; its parts land in the units SUPP_owner_0930 states: A.S0930.04 in U25. | AC3_R R-08 (h) |

## A-C review fold (2026-10-05)

Owner answers OR136-OR143 and the routine settlements folded in (`audit/actions/FOLD_BRIEF.md`); one row per item and
action. `[fold Fnn M_FILE]` tokens in Depends/Blast name changes other fold agents add.

| Fnn | M-ID(s) | action |
|---|---|---|
| F01 | M.TWIN.104 | amended |
| F02 | — | none in this file (checked: no twin test assumes a monotonic `HTTPDropped`; the host harness is SCR's) |
| F03 | M.TWIN.104 | amended |
| F04 | — | none in this file |
| F05 | — | none in this file |
| F06 | — | none in this file |
| F07 | — | none in this file |
| F08 | — | none in this file |
| F09 | — | none in this file |
| F10 | — | none in this file |
| F11 | M.TWIN.011 | amended |
| F12 | — | none in this file |
| F13 | — | none in this file |
| F14 | — | none in this file |
| F15 | M.TWIN.104 | amended |
| F15 | M.TWIN.104 (lead ruling 2026-10-05: token replaced by M.SRC_CORE.011, M.SRC_CORE.038) | amended |
| F16 | M.TWIN.167, .168 | added |
| F16 | M.TWIN.050, .053, .058, .061, .064, .066, .146 | amended |
| F17 | — | none in this file |
| F18 | — | none in this file |
| F19 | — | none in this file |
| F20 | — | none in this file (checked: every WoZi-specific twin text already goes in its merged change) |
| F21 | M.TWIN.167 | tag |
| F22 | — | none in this file |
| F23 | M.TWIN.054, .144, .152, .158 (and convention C2) | amended |
| F23 | M.TWIN.054 (lead ruling 2026-10-05: the `exec` is ruff S102's, not the import check's; token removed) | amended |
| F24 | — | none in this file |
| F25 | M.TWIN.169, .170, .171 | added |
| F25 | M.TWIN.064, .130 | amended |
| F26 | M.TWIN.144 | amended |
| F27 | M.TWIN.171 | added |
| F28 | — | none in this file |
| F29 | — | none in this file |
| F30 | — | none in this file |
| F31 | M.TWIN.146 | amended |
| F32 | — | none in this file |
| F33 | — | none in this file |
| R54 | M.TWIN.104 (the damaged-config case: the boot repairs the corrupt file and it stays listed; test renamed `…_is_repaired_listed_then_deleted_and_rewritten_once`) | amended |
