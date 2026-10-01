# A-C merge TEST_HELP (HEAD dd06040)

Scope: CLUSTERS.md "## TEST_HELP" — the `tests/_*` helpers and scenario modules, the fakes `tests/machine.py`,
`tests/network.py`, `tests/neopixel.py`, the runner `tests/microtest.py`, and `tests/README.md` (absent at HEAD), plus
the new `tests/_*` helper files actions create. Constituents per file: the index's `by_file` actions plus every action
whose Site, Change or Blast slot names the file (grep of `audit/actions/*.md` by path and basename, 1545 blocks
scanned). A Blast entry naming a cluster file with no edit owed gets a ledger row "blast-only, holds" after the end state
was checked against it. `git diff 8e36b1e dd06040 -- tests src digital_twin` is empty, so every line cited holds.

**Conventions every merged change below applies** (each change names the ones it uses; mechanics are not repeated).

- **H0 Lines and units.** Line numbers are HEAD `dd06040`. Units run in number order (U0 B0; U1-U8 B1; U9-U34 B2;
  U35-U37 B3-B5). A merged change lands in the latest unit of its constituents unless a stage is listed; a stage is
  split out only where a same-unit consumer needs it earlier. Fake semantics restated here were re-read in the
  scratchpad `mp/` checkout (v1.29.0) and are re-checked against the refreshed pin before execution (AC_NOTES 34):
  `ports/rp2/machine_pin.c:243-248`, `machine_i2c.c:61-112`, `machine_spi.c:161-214`, `machine_uart.c:455-480`,
  `machine_timer.c:50-145`, `machine_wdt.c:55-57`, `machine_rtc.c:50-98`, `machine_mem_backup.c:36-43`,
  `extmod/machine_mem.c:131-148`, `extmod/modselect.c:252-266`, `extmod/network_cyw43.c:357-392`.
- **H1 U10 rename sweep** (mechanical, lands with each renaming action in U10, found by that action's own grep and
  typecheck): module names (A.U10.37: `system_service` → `asy_system_service`, `print_log` → `asy_print_log`,
  `config_manager` → `asy_config_manager`, `base_classes` → `asy_base_classes`, `crc_checks` → `asy_crc_checks`
  (`CRC_Base` → `CRCPass`, M.SRC_CORE), `framing_codecs` → `asy_framing_codecs`, `api_response` → `asy_api_response`,
  `captive_dns` → `asy_captive_dns`); class names (A.U10.38: `AsyFramManager` → `FRAMManager`, `AsyConnTime` →
  `WifiService`, `UART_Comm` → `UARTComm`, `UartLinkExerciser` → `UARTLinkDriver`, `BMP3xx_Reader` → `BMP3XX_Reader`,
  `AsyUDPSocket` → `UDPSocket`, …); attributes made private (A.U10.35); lock names (A.U10.18); REST/config keys
  (A.U10.40 map: `NTP_Host` → `NTPHost`, `MeasInt` → `MeasInterval`, `lightCmdLED` → `LightCmdLED`, …); unit suffixes
  (A.U10.43); starter names (A.U10.44); the supervisor split (M.SRC_CORE.016: `start_and_check_tasks()` →
  `start_tasks(starters, task_names)` + `supervise_tasks()`, `task_names` required — GAP-G5).
- **H2 Harness migration** (U24): `run()`/`run_timed()`/`_cancel*` → `tests/_async_harness.py` (M.TEST_HELP.043, a
  bounded copy keeps its bound); `const()` mirrors → `tests/_src_const.py` (M.TEST_HELP.044); response bodies →
  `strict_loads()` (M.TEST_HELP.008); the device set and wiring plans → `tests/_twin_devices.py` (M.TEST_HELP.055);
  generated modules through `load_generated()`/`boot_generated()` after `require_fresh()` (M.TEST_HELP.046/.047);
  catalog codes `code("E"|"W", NAME)` (`tests/_error_codes.py`, M.TEST_HELP.045); `inject_fault(op, exc_type, *args,
  times=…)` (M.TEST_HELP.015).
- **H3 `@tunable` tags** (A.U8C, grammar A.U8.02): every tagged literal becomes the module constant its row writes,
  except a literal a later constituent deletes — its row is withdrawn and named.
- **H4 Permanent text.** Comments and docstrings cite no audit ID (G9/R12, AC_NOTES 4), carry actor tags
  "(owner|agent, YYYY-MM-DD)", state current facts, and every block is ≤ 3 prose lines under A.U27.28's counting; a
  header a constituent rewrites is written to that bar in the same edit (A.U27.28's gate then finds nothing here).
- **H5 Function-level imports** (A.U0.07, owner unit U24 for `tests/`): every function-body import in a cluster file
  moves to module level (or to the `TYPE_CHECKING` block when used only in annotations) in the file's U24 change, and its
  `_PENDING` entry leaves `tests_scripts/test_import_placement.py` in the same commit; by-name loads go through
  `load_generated()` (A.U10.30, the one named F.1 exception for `tests/`) and the two runners' `exec()` (F.1 named).
- **H6 Ordering last** (A.U36.038): each Python file here is re-sorted to D.15 by the script-driven pure move after every
  other change on it (U36), the decorator `_register` in each scenario library being the named import-time exception.

## tests/microtest.py

### M.TEST_HELP.001 Runner reports skips, empty files and aborts honestly
- **From**: A.U7.07, A.U24.03, A.U24.17 (microtest half)
- **Site**: `tests/microtest.py:6-42` `run()`.
- **Change**: `class Skip(Exception)` (message = reason). Per test, in order: `result = fn()`; a non-`None` result →
  FAIL "returned a value - an async def test_* or a stray return; microtest runs synchronous functions only" (a
  generator result is `close()`d first); `except Skip` → `skipped += 1`, `SKIP <name>: <reason>`; `except Exception` →
  FAIL with traceback (as today); `except BaseException as exc` → if `isinstance(exc, getattr(sys.modules.get("machine"),
  "SimulatedRebootError", ()))` the test FAILs "reset reached without a catch" and the run continues; otherwise `ABORT
  <name>:` with the traceback, `_tmp_scratch.teardown_all()`, the closing line `f"{passed}/{total} passed, {failed}
  failed, {skipped} skipped - aborted at {name}, later tests not run"` and `sys.exit(1)`. Normal end: `f"{total - failed
  - skipped}/{total} passed, {failed} failed, {skipped} skipped"`; `total == 0` prints `"0/0 passed, 0 failed, 0 skipped
  - no test_* function collected"` and exits 1. The final `sys.exit(1 if failed else 0)` stays unconditional on every
  path (CLAUDE.md "Known hang cause #2"); its comment `:35-41` → one ≤ 3-line block: "# Always exit explicitly:
  MicroPython's asyncio has no parent/child tracking, so tasks a test leaves parked would keep / # the process alive
  after the summary line (SPECIFICATION.md E.3)."
- **Resolved**: A.U24.17's "SimulatedRebootError is that test's FAIL" refines A.U24.03's BaseException ABORT; the class
  is looked up on whichever `machine` module is loaded (unit fake or twin fake, A.U25.07's names) so microtest imports no
  fake and still runs where none exists (`tests/lwip_host/`, A.U21.13) — agent decision D1.
- **Unit**: stage 1 U7 (Skip, empty-file rule, three-count closing line — A.U7.03's summary parser in U7 reads it);
  stage 2 U24 (value check, BaseException/reset handling, the abort line).
- **Depends**: M.TEST_HELP.002 (same loop, U24); A.U7.03 (parser).
- **Blast carried by**: test.sh summary parser of the three counts and the abort suffix → A.U7.03 (SCR); every test file's
  `async def test_*` (none at HEAD per A.U24.03's grep) — none owed; twin tests that reach a product reset catch
  `SimulatedRebootError` → A.U25.07 (TWIN, M_TWIN C4).
- **Kind**: test

### M.TEST_HELP.002 After-each hooks restore process state and catch leaks
- **From**: A.U24.07 (1), A.U24.08 (microtest check), A.U24.15 (3), A.U30.14 (allowance), A.U27.28 (header)
- **Site**: `tests/microtest.py:1-42` (header, `run()` per-test loop).
- **Change**: module docstring (≤ 3 lines): "Minimal test runner for the MicroPython Unix port: runs each `test_*`
  function of a namespace, resets process state after each, prints one summary line and always exits explicitly." New
  `_AFTER_EACH: list = []` and `after_each(fn)` (append). `run()` snapshots `sys.path[:]` and `gc.threshold()` (the
  zero-argument read) at start; after every test, in a `finally`: (a) the scheduler check runs first — if `"asyncio" in
  sys.modules` and (`asyncio.core._task_queue.peek() is not None` or `asyncio.core._io_queue.map`) the test FAILs "left a
  task parked on the scheduler", every task on `_task_queue` is cancelled and drained with one `run_until_complete`
  round, and every `_io_queue.map` entry is unregistered from the prewarmed poller and deleted (`_io_queue` itself is
  never replaced); (b) each registered hook runs, a hook's exception counting as that test's FAIL "teardown: <exc>";
  (c) `sys.path[:] = saved_path` and `gc.threshold(saved_threshold)`. A test already counted FAIL is not counted twice.
- **Resolved**: A.U24.08 names its check the hook list's first entry and A.U24.15 adds `real_poll_queries` to "the hook
  list" — merged as microtest's built-in step (a) first, then the fakes' registered `reset_test_state()` hooks, which own
  the `real_poll_queries` check (M.TEST_HELP.010) so microtest names no fake; A.U30.14's allowance (`tests/microtest.py`
  restores the threshold it read at start) matches (c) exactly.
- **Unit**: U24 (A.U27.28's header lands early in the same edit; its U27 gate finds it).
- **Depends**: M.TEST_HELP.001; M.TEST_HELP.043 (`_async_harness` tasks are the ones the check backstops).
- **Blast carried by**: per-test manual resets removed from test files → A.U24.07 (4) (TEST_UNIT, TWIN); in-body
  `gc.threshold` pairs → A.U30.12/A.U30.13 (TEST_UNIT, TWIN); checker allowance → A.U30.14 (TSC); CLAUDE.md "Known hang
  cause #2" bullet's new shape → A.U36.546 (DOCS); SPEC E.3 mechanism paragraph → A.U36.546 (SPEC).
- **Kind**: test

## tests/_threshold_runner.py

### M.TEST_HELP.003 Threshold runner never passes an incomplete file
- **From**: A.U24.05, A.U28.28, A.U27.28, A.U10.30 (F.1 entry), A.U0.07 (`_PENDING` entry), A.U30.14 (allowance)
- **Site**: `tests/_threshold_runner.py:1-27` (`#` header `:1-9`, `_run()` `:12-24`, `exec` `:20` with `# noqa: S102`).
- **Change**: the `#` header → a module docstring (≤ 3 lines): "Runs one test file at a given `gc.threshold()` stage:
  sets the threshold, executes the file as `__main__`, returns the file's exit code." `_run()`: `sys.argv[:] =
  [test_file]` after the runner reads its own arguments; `exec()` returning with no `SystemExit` prints `"runner: <file>
  ended without microtest's exit - no trailer, or it never ran"` and returns 1; `SystemExit` returns `exc.args[0]` when
  an int, 1 for a non-int argument, 0 for none; any other `BaseException` prints the traceback and returns 1. The inline
  `# noqa: S102` goes (pyproject per-file entry, A.U28.28). The `exec` stays the F.1-named by-path load (A.U10.30); its
  `_PENDING` entry becomes a `_NAMED_EXCEPTIONS` entry.
- **Resolved**: —
- **Unit**: U24 (the noqa removal waits for A.U28.28's per-file entry, U28: until then the inline noqa stays — stage 2
  U28 removes it).
- **Depends**: M.TEST_HELP.001.
- **Blast carried by**: per-file `S102` entry → A.U28.28 (TOOL); F.1 list → A.U10.30 (SPEC); checker allowance (sets the
  stage) → A.U30.14 (TSC); test.sh dispatch → A.U7.03 (SCR); the twin scenario harness's own GC stages → A.U27.38 (SCR).
- **Kind**: test

## tests/_coverage_runner.py

### M.TEST_HELP.004 Coverage runner dumps on every path, traces generated modules
- **From**: A.U24.05, A.U24.72 (1), A.U28.28, A.U27.28, A.U10.30, A.U0.07, A.U36.526 (blast)
- **Site**: `tests/_coverage_runner.py:1-71` (`#` header, `_TRACED_PREFIXES` `:24`, `_run()` `:27-68`, dump `:65-66`).
- **Change**: header → module docstring (≤ 3 lines): "Runs one test file under `sys.settrace` and dumps the executed
  lines of the traced prefixes as JSON for `scripts/_render_coverage.py` (SPECIFICATION.md E.5)."
  `_TRACED_PREFIXES = ("src/", "digital_twin/", "build/generated_src/")`. `_run()` follows M.TEST_HELP.003's exit rules
  (no `SystemExit` → message and 1; non-int → 1; escape → traceback, 1; `sys.argv[:] = [test_file]`), and the JSON dump
  moves into the `finally` so it is written on every path. Inline `# noqa: S102` goes (A.U28.28); F.1-named `exec`.
- **Resolved**: —
- **Unit**: U24 (noqa stage U28 as M.TEST_HELP.003).
- **Depends**: M.TEST_HELP.003.
- **Blast carried by**: third render and host coverage → A.U24.72 (2) (SCR); SPEC E.5 text and false-negative classes →
  A.U24.72 (3), A.U36.526 (SPEC); `S102` entry → A.U28.28 (TOOL).
- **Kind**: test

## tests/_tmp_scratch.py

### M.TEST_HELP.005 Scratch teardown touches only its own tree
- **From**: A.U24.10, A.U24.11, A.U37.03 (kept)
- **Site**: `tests/_tmp_scratch.py:1-87` (`_remove_tree()` with eight bare `except OSError: pass`, `TmpScratch(key)`).
- **Change**: `_remove_tree()` walks with `os.ilistdir()` (type from the entry, no extra `stat`) and swallows only
  `ENOENT` (already gone) and, on `mkdir`, `EEXIST`; any other `OSError` propagates with its path. `TmpScratch(key)`
  asserts the key is not already live in this process (`AssertionError("TmpScratch key <key> already in use")`), so two
  fixtures never share a tree. The structural no-shared-root property `tests/test_tmp_scratch.py` pins holds (no
  `listdir` of the shared root).
- **Resolved**: A.U37.03's pattern search lists the file as a live helper, kept — no change.
- **Unit**: U24
- **Depends**: —
- **Blast carried by**: `tests/test_tmp_scratch.py` cases for the errno filter and duplicate key → A.U24.10/A.U24.11
  (TEST_UNIT).
- **Kind**: test

## tests/neopixel.py

### M.TEST_HELP.006 NeoPixel fake stores GRB bytes as micropython-lib does
- **From**: A.U24.25, A.U22.01 (blast), A.U25.21 (twin half, shape match), A.U24.18 (`TEST_API`), A.U24.07 (no class state)
- **Site**: `tests/neopixel.py:1-37` (docstring, `NeoPixel`).
- **Change**: docstring (≤ 3 lines, the over-long line 2 rewrapped) cites micropython-lib
  `micropython/drivers/led/neopixel/neopixel.py:9-46`. `NeoPixel(pin, n, bpp=3, timing=1)`: `pin.init(pin.OUT)`
  (recorded by M.TEST_HELP.012's `Pin`), `self.buf = bytearray(n * bpp)`, `ORDER = (1, 0, 2, 3)`; `__setitem__(i, v)`
  stores `self.buf[offset + ORDER[k]] = v[k]` for `k in range(bpp)` in order (a bytearray store: an int ≥ 256 or < 0
  truncates as on the board, a float raises `TypeError` at that component with earlier ones written, a short tuple
  raises `IndexError`); `__getitem__` reads back through `ORDER`; `__len__`, `fill(v)`; `write()` keeps
  `raise_on_write` and appends the frame decoded to RGB tuples to `writes` (`writes[-1][0] == (r, g, b)` keeps its
  form). `TEST_API = ("writes", "raise_on_write")`.
- **Resolved**: A.U22.01 states `write()` cannot fail on silicon (one `machine.bitstream()` with self-built arguments);
  `raise_on_write` stays as a fault knob for the supervisor-restart path, its line saying "twin-only test knob: no
  silicon fault reaches write()" — agent decision D2 (the knob is the only way L1 reaches the restart rung A.U22.01
  names).
- **Unit**: U24
- **Depends**: M.TEST_HELP.012 (`Pin.init` record).
- **Blast carried by**: `tests/test_asy_neopixel_driver.py:527-531, 612, 644` comments and wrap assertions → A.U24.25
  (TEST_UNIT); twin fake → A.U25.21 (TWIN); driver sanitiser the tests bite on → A.U9.06 (SRC_SENS).
- **Kind**: test

## tests/network.py

### M.TEST_HELP.007 Network fake: power-on seeds, cyw43 status raises, static interfaces
- **From**: A.U24.09, A.U24.19, A.U24.81, A.U24.07 (3), A.U24.18, A.U18.27 (blast), A.U18.28 (blast), A.U14.37 (holds),
  A.U24.73
- **Site**: `tests/network.py:1-106` (docstring `:1-3`, comment `:4-9`, seeds `:21-22`, `WLAN` `:41-106`).
- **Change**: (1) Seeds `_country_code = ["XX"]` (`extmod/modnetwork.c:71`) and `_hostname_value = ["PicoW"]`
  (`ports/rp2/boards/RPI_PICO_W/mpconfigboard.h:8`), each cited on its line. (2) `WLAN(if_id=STA_IF)` returns the one
  object per interface from a module table `_WLANS` (`extmod/network_cyw43.c:96-103`) and increments
  `WLAN.constructions[if_id]`; `deinit()` marks both interfaces inactive and disconnected (`network_cyw43.c:133-137`).
  (3) `status()` → link status; `"rssi"` off `STA_IF` → `ValueError("STA required")`; `"stations"` off `AP_IF` →
  `ValueError("AP required")`; any other string → `ValueError("unknown status param")`; a literal `None` argument →
  `TypeError` (`network_cyw43.c:352-392`); every call first appends its `param` to `self.status_calls`. An AP object's
  link status follows `active()`: `STAT_GOT_IP` while active (the AP netif is up with its address,
  `cyw43/src/cyw43_lwip.c:300-315`), `STAT_IDLE` otherwise; a test may still set `_status`. (4) `reset_test_state()`
  restores the seeds in place, clears `_WLANS` and `WLAN.constructions`, registered with `microtest.after_each` at
  import. (5) `TEST_API` tuple lists `config_calls`, `connect_calls`, `status_calls`, `raise_on`, `constructions`,
  `deinit_called`, `disconnect_called`. (6) Docstring ≤ 3 lines (line 2's 200-character run rewrapped); the comment
  `:4-9` → "# Status values are the cyw43 link codes `network` exports; 2 is CYW43_LINK_NOIP (joined, no IP yet), which
  / # network exports no name for (cyw43.h:100, extmod/modnetwork.c:197-202, v1.29.0)." — the "internal consistency,
  not fidelity" paragraph goes (the fake now models rp2). `country()`/`hostname()`/`connect()` bounds already match
  C.7.4 (A.U14.37) — unchanged. No `Any` remains.
- **Resolved**: A.U18.28's blast asks U24 to model "an active AP with an address reports `STAT_GOT_IP`" (a fidelity
  row) — merged as (3)'s last sentence, verified against the fetched cyw43 source.
- **Unit**: U24
- **Depends**: M.TEST_HELP.002 (`after_each`).
- **Blast carried by**: `tests/test_asy_wifi_service.py:2962-3014` seed assertions → A.U24.09; status-call counts →
  A.U24.32 (4); AP `STAT_GOT_IP` comment `:2729-2730` and the hotspot tests → A.U18.28 (TEST_UNIT); twin
  `WLAN.status()` → A.U25.26 (TWIN); `mypy tests/network.py` run alone → A.U27.23 (TOOL); baseline excluded-file
  record → A.U0.06 (audit artefact only).
- **Kind**: test

## tests/_strict_json.py

### M.TEST_HELP.008 Strict JSON oracle rejects duplicate keys, serves every body
- **From**: A.U24.60, A.U14.11 (pointer), A.U10.27 (consumer), A.SDEP.17 (W39), A.U24.73
- **Site**: `tests/_strict_json.py:1-3` (header), `:83-100` (`_members`, `_pair`), `:119-125` `check_strict_json()`.
- **Change**: the object branch keeps a `set` of decoded keys (each key token decoded with `json.loads()`, so `"\/"`
  and `"/"` collide) and raises "duplicate key"; new `strict_loads(body) -> object` = `check_strict_json(body)` then
  `json.loads(body)`. Header (≤ 3 lines): "Strict RFC 8259 check for response bodies: MicroPython's `json.loads()`
  accepts doubled or missing commas and keeps the last of duplicate keys (SPECIFICATION.md F.1), which the browser's
  `JSON.parse()` rejects or reads differently. No `src/` writer emits a key twice."
- **Resolved**: A.SDEP.17 W39 (a future modjson fix) leaves the oracle as defence — no change now.
- **Unit**: U24
- **Depends**: —
- **Blast carried by**: every response-body `json.loads(` → `strict_loads(` in `tests/test_asy_webserver_service.py`,
  `tests/test_setter_microdot_integration.py` → A.U24.60 (TEST_UNIT); `_sensortask_scenarios.py` → M.TEST_HELP.035;
  `_shared_rest_roundtrip.py` → M.TEST_HELP.009; the L0 `json.loads(` allow-list → A.U24.60 (3) (TSC); non-finite
  scenario → M.TEST_HELP.041 (A.U10.27); SPEC F.1 sentence → A.U14.11 (SPEC).
- **Kind**: test

## tests/_shared_rest_roundtrip.py

### M.TEST_HELP.009 REST round-trip helpers parse strictly, state current facts
- **From**: A.U24.60, A.U24.73
- **Site**: `tests/_shared_rest_roundtrip.py:1-41`.
- **Change**: `drain_json_response_body()` keeps its check; a new `drain_json(body) -> object` returns
  `strict_loads(drained)` for callers that parse. `assert_sensor_payload_not_self_wrapped(payload: "dict[str, object]",
  …)` (no `Any`, the JSON alias of A.U11.S02 where it lands); its docstring → "Checks GET /measurements and /sensors
  return each sensor's fields directly, not wrapped again under the sensor's own name, and never empty." (the "was
  {...}" history goes, H4). Runs under CPython too (`tests_hardware/`), so nothing MicroPython-only is added.
- **Resolved**: —
- **Unit**: U24
- **Depends**: M.TEST_HELP.008.
- **Blast carried by**: CPython callers in `tests_hardware/` (unchanged signatures) — none owed.
- **Kind**: test

## tests/machine.py

One edit per class in U24 (the unit-fake half of U24/U25's fidelity work); the module-level reset/mem-backup half lands
in U11 with its product (staged, M.TEST_HELP.011). Every class gains its `TEST_API` tuple (A.U24.18) in the class's own
change; the shared header, reset hook and citations are M.TEST_HELP.010.

### M.TEST_HELP.010 Fake header, per-test reset hook, citations, test-API lists
- **From**: A.U24.07 (2)/(4), A.U24.15 (3), A.U24.18 (1), A.U24.26 (1)/(3), A.U27.03, A.SDEP.08, A.U36.532 (`:407`),
  A.U24.73, A.U27.28 (header bar), A.U5.17/A.U5.18 (blast), A.U28.29 (blast), A.U36.546 (blast), A.U7.01 (blast),
  A.U14.12 (blast)
- **Site**: `tests/machine.py:1-2` (docstring), `:100-112` (`_CallLog`), each class's header comment, the version
  claims `:26, :153, :205-211, :351`, `:407`; new `reset_test_state()` at the end of the module.
- **Change**: (1) Docstring (≤ 3 lines): "Test-only fake `machine` module for the unit tier: models the rp2 port's
  raw I2C/SPI/UART/Pin/Timer/RTC/WDT surface (MicroPython v1.29.0), so the real drivers run against it (SPECIFICATION.md
  E.4). It also models rp2's zero-argument `Timer()`, which the board stub lacks (B.15)." — the dangling BACKLOG pointer
  goes. (2) `def reset_test_state() -> None` restores every class- and module-level knob to its declared default, lists
  cleared in place (`Timer.all_timers`, `Timer.raise_on_arm`/`raise_on_arm_exc`, `Timer.clock_ms`, `RTC.raise_exc`,
  the RTC seconds, `UART.would_have_blocked_bytes`, `UART.real_poll_queries`, `Pin.reset_registry()`,
  `I2C.reset_registry()` and `I2C.raise_on_construct`, `reset_count`, `bootloader_count`, `reset_cause_value`, both
  backup regions zeroed); before resetting it records `UART.real_poll_queries`, and after resetting raises
  `AssertionError("a real select.poll() queried a UART fake")` when it was non-zero (microtest counts it as that test's
  teardown FAIL); registered by `microtest.after_each(reset_test_state)` at import (a script without microtest, e.g.
  the boot probe, imports `microtest` harmlessly). (3) Every fake class declares `TEST_API: tuple[str, ...]` (its
  test-only knobs and every public `self.<name>` real `machine` lacks), checked by A.U24.18's L0 surface test. (4) Each
  modelled constant cites its v1.29.0 source on its line (A.U24.26 (1)'s list), and each class header gains one "Not
  modelled: …" line (UART: baudrate/bits/stop validation, pin muxing; I2C: clock-stretch timing, arbitration loss; SPI:
  baudrate rounding). (5) The version claims at `:26, :153, :205-211, :351` are re-verified at each pin move (A.SDEP.08)
  and say "v1.29.0" uniformly; `:407`'s "Part F.5.8" → "Part F.8.2" (A.U36.532, U36). (6) No `Any` (`_CallLog.append`
  takes `tuple[object, ...]`).
- **Resolved**: A.U24.15's "hook list gains the `real_poll_queries == 0` check" lands inside this module's own hook
  (record, reset, then assert), so the counter is zeroed even when the check fails — agent decision D3.
- **Unit**: U24 (the `:407` repoint U36, A.U36.532; the pin-move re-check A.SDEP.08's unit).
- **Depends**: M.TEST_HELP.002 (`after_each`); M.TEST_HELP.011-021 (the knobs it resets).
- **Blast carried by**: per-test manual resets removed → A.U24.07 (4) (TEST_UNIT); L0 surface check → A.U24.18 (TSC);
  SPEC B.15 stub-workaround list → A.U27.03 (SPEC); PLR0913 exemption for `UART.__init__`/`SPI.__init__` → A.U5.17/
  A.U5.18 (TOOL); pyproject ANN401 comments for this file → A.U28.29 (TOOL); CLAUDE.md stub-gap bullet → A.U36.546
  (DOCS); SPEC E.6.1 ladder names this fake as L1's → A.U7.01 (SPEC); twin Timer pool/finaliser → A.U25.19 (TWIN; the
  unit fake keeps `raise_on_arm`, A.U14.12's F.1 text).
- **Kind**: test

### M.TEST_HELP.011 Reset never returns; reset cause and backup regions modelled
- **From**: A.U24.17 (`check_reset_never_returns`, WDT bound), A.U11.07, A.U11.05 (blast), A.S0930.24, A.S0930.36,
  A.S0930.21 (blast), A.U35.30 (blast), A.U24.26 (WDT cite), A.U24.07 (2)
- **Site**: `tests/machine.py:684-707` (`WDT`, the `reset()`/`bootloader()` comment `:694-695`, counters, functions).
- **Change**: (1) `PWRON_RESET = 1`, `WDT_RESET = 3` (`ports/rp2/modmachine.c:65-66`, values `RP2_RESET_*`), module
  state `reset_cause_value = PWRON_RESET`, two static regions `array("I", 4 × 0)` and `array("I", 3 × 0)` with one
  `memoryview` each, created once (`ports/rp2/machine_mem_backup.c:36-43`); `mem_backup(region=0)`: `-1` → a tuple of
  both views, `0`/`1` → that view (the same object on every call, as rp2's static table), any other →
  `ValueError("invalid region")` (`extmod/machine_mem.c:135-148`); `reset_cause()` returns `reset_cause_value`;
  test-only `power_on()` zeroes both regions and sets `PWRON_RESET`. (2) `class SimulatedRebootError(BaseException)`
  with `SimulatedResetError`/`SimulatedBootloaderEntryError` subclasses (the twin's names); `reset()`/`bootloader()`
  increment their counter, set `reset_cause_value = WDT_RESET` (what rp2 reports after `watchdog_reboot()`), then raise
  their error — code after a reset never runs; the comment `:694-695` → "# Real reset()/bootloader() never return: the
  fake records the call, sets the cause rp2 then reports, and raises so no later line runs." (3) `WDT(id=0,
  timeout=5000)`: `timeout > 8388` → `ValueError` (`ports/rp2/machine_wdt.c:55-57`, cap `:32-38`); `feed()` increments
  `feed_count` and appends `time.ticks_ms()` to `feed_times`, a `_CallLog`-bounded list. (4) `TEST_API` for `WDT`:
  `feed_count`, `feed_times`; module test names `reset_count`, `bootloader_count`, `reset_cause_value`, `power_on`,
  `Simulated*Error` listed in a module-level `TEST_API`.
- **Resolved**: A.U11.07's "`reset()`/`bootloader()` set `WDT_RESET`" and A.U24.17's "count then raise" combine as
  count → cause → raise; A.U11.07's `mem_backup()` gains rp2's `-1` tuple and object identity (verified in the pinned
  source above; the twin half, A.U25.08, asserts both — one contract, M.TEST_HELP.049).
- **Unit**: stage 1 U11 (cause, regions, `power_on()`, `mem_backup()` — A.U11.05's product lands in the same commit,
  and the main mypy pass resolves `machine` to this fake); stage 2 U24 (the raising `reset()`/`bootloader()`, WDT bound,
  `TEST_API`); `feed_times` lands with A.S0930.24 (U11, system-command work) inside stage 1.
- **Depends**: M.TEST_HELP.010; M.TEST_HELP.001 (microtest reports an uncaught `SimulatedRebootError` as a FAIL).
- **Blast carried by**: every test that triggers the product reset timer or calls a reboot path catches
  `machine.SimulatedRebootError` — `tests/test_system_service.py` reboot sections → A.U24.17/A.S0930.21/A.S0930.36
  (TEST_UNIT), `tests/_sensortask_scenarios.py:953-973` → M.TEST_HELP.040; reset-code L1 cases → A.U11.07 (TEST_UNIT);
  planted-fault scenarios → M.TEST_HELP.042; twin fake → A.U25.07/A.U25.08 (TWIN).
- **Kind**: test

### M.TEST_HELP.012 Pin fake follows rp2's id, mode, pull, alt, value
- **From**: A.U24.16, A.U13.03 (`init(value=)`), A.U14.17 (a) and A.U13.R01 (open drain, external level), A.U24.17
  (`check_pin_*`), A.U16.16 (holds), A.U24.45 (holds), A.U25.02/A.U25.05 (twin half, same semantics)
- **Site**: `tests/machine.py:12-70` (`class Pin`: constants, `__init__` `:32-49`, `init()` `:51-54`, `value()`
  `:56-63`).
- **Change**: `IN = 0`, `OUT = 1`, `OPEN_DRAIN = 2`, `ALT = 3` (`ports/rp2/machine_pin.h:34-37`), `PULL_UP = 1`,
  `PULL_DOWN = 2`, `ALT_I2C = <GPIO_FUNC_I2C>` (value read from pico-sdk's `gpio_function` enum at the pinned submodule
  and cited), IRQ edge constants at their rp2 values; `__init__(id, mode=None, pull=None, *, value=None, alt=<SIO>)`:
  int ids 0-29 or the Pico W board/CPU names (`ports/rp2/boards/RPI_PICO_W/pins.csv`, `boards/make-pins.py:95-108`;
  `LED` is `EXT_GPIO0`), unknown name → `ValueError('unknown named pin "<n>"')`, other → `ValueError("invalid pin")`
  (`machine_pin.c:185, 191`); external pins refuse a pull or non-SIO alt (`:256-262`); `id` alone configures nothing
  (`:318-323`), else `init()` runs. `init(mode=None, pull=None, *, value=None, alt=<SIO>)`: `None` mode keeps the mode;
  `OUT` applies `value` before the mode; `OPEN_DRAIN` drives low for 0 and releases otherwise; `ALT` records `alt`;
  pull is set unconditionally (`None` → none). Per-id state in a class table (two `Pin(5)` share mode, pull, level,
  log). Test API: `Pin.set_external_level(id, level)` (int, or callable `(pin_id, value_log) -> int` evaluated per
  read), `Pin.value_log(id)`, `Pin.reset_registry()`; `value()` on an input or released open-drain pin returns the
  external level, on `OUT` the driven level. `TEST_API` lists them.
- **Resolved**: —
- **Unit**: U24, except `init(value=)`, which lands with A.U13.03 in U13 (its product calls `init(OUT, value=…)`);
  the U24 edit keeps that keyword.
- **Depends**: M.TEST_HELP.010.
- **Blast carried by**: bus-clear L1 cases (`_clear_bus()` status mask, SCL release) → A.U13.R01/A.U14.17 (TEST_UNIT);
  `wp_pin` cases `tests/test_asy_fram_driver.py:533-606` hold (A.U16.16); stale fake-Pin reason
  `tests/test_asy_wifi_service.py:141-143` → A.U24.45 (TEST_UNIT); twin `Pin` → A.U25.02/A.U25.05 (TWIN); shared checks
  → M.TEST_HELP.048.
- **Kind**: test

### M.TEST_HELP.013 I2C fake keeps per-id bus state across constructions
- **From**: A.U24.20, A.U13.R01 (`recover()` keeps state; construction raising), A.U25.03 (twin half)
- **Site**: `tests/machine.py:114-135` (`I2C.__init__`).
- **Change**: bus state (`registers`, `read_queue`, `read_queue_by_address`, `nak_addresses`, `attached`, `busy`, the
  fault queue, `log`) lives in a class table keyed by `id`; `I2C(id, …)` binds to that entry, logs `("init", freq,
  timeout)` and re-configures `scl`/`sda`/`freq`/`timeout` (default `timeout=50000`, `ports/rp2/machine_i2c.c:38`);
  `I2C.reset_registry()` (hook) and `I2C.reset_id(id)` (a power-cycled controller, called by every test-side fresh-bus
  helper); `I2C.raise_on_construct: BaseException | None` makes the next construction raise. `TEST_API` lists them
  with the state names.
- **Resolved**: —
- **Unit**: U24
- **Depends**: M.TEST_HELP.010, M.TEST_HELP.012.
- **Blast carried by**: the file-local `make_i2c()` of five driver tests and `tests/test_bus_hazard_generated.py:74-81`
  call `reset_id()` → A.U24.20 (TEST_UNIT); `tests/_bus_hazard_catalog.py:41` → M.TEST_HELP.026; recovery L1 ("status 8")
  → A.U13.R01 (TEST_UNIT); twin → A.U25.03 (TWIN).
- **Kind**: test

### M.TEST_HELP.014 I2C probe raises ENODEV; scan never raises
- **From**: A.U24.21, A.U14.14 (doc), A.U30.21 (holds), A.U24.17 (`check_scan_never_raises`)
- **Site**: `tests/machine.py:115-117` (class comment), `:160-167` `scan()`, `:177-181` `writeto()`.
- **Change**: `writeto(addr, b"")`: `busy` → `OSError(ETIMEDOUT)`, NAKed or unattached address → `OSError(ENODEV)`,
  else 0 (rp2's zero-length write is a soft-I2C transfer, `ports/rp2/machine_i2c.c:127-145`); non-empty writes keep
  EIO/ETIMEDOUT. `attached: set[int]` (an address answers a probe when attached or holding a register). `scan()` probes
  0x08-0x77 (`extmod/machine_i2c.c:345`) and lists the addresses that returned 0 — `busy` → `[]`, nothing raises. The
  class comment states the three results (EIO, ETIMEDOUT, ENODEV only from a NAKed zero-length probe). Whole-buffer
  `readfrom_into`/`writeto` accept a bytearray or a view (no type assertion exists — A.U30.21 holds).
- **Resolved**: the `inject_fault("scan", …)` op goes (A.U24.21; refused by M.TEST_HELP.015's op check).
- **Unit**: U24
- **Depends**: M.TEST_HELP.013.
- **Blast carried by**: probe-ENODEV and scan L1 → A.U24.21 (TEST_UNIT); catalog adapters add their address to
  `attached` → M.TEST_HELP.026 (A.U24.43 (2)); SPEC F.1/C.12 → A.U14.14 (SPEC); twin → A.U25.03 family (TWIN).
- **Kind**: test

### M.TEST_HELP.015 Both bus fakes take the twin's fault-queue convention
- **From**: A.U24.78, A.U25.70 (convention), A.U24.17 (`check_inject_fault_fifo`), A.U24.47 (comment fact)
- **Site**: `tests/machine.py:137-151` (`I2C.inject_fault()`, `_maybe_raise()`), `:274-290` (`SPI.inject_fault()`,
  `_maybe_raise()`).
- **Change**: `inject_fault(op, exc_type, *args, times=1, match=None)` (I2C also `address=None`) raises a fresh
  `exc_type(*args)` per matching call, FIFO; I2C `match` = command key (first two written bytes of a raw word write,
  `memaddr` for `*_mem`), `address=` a separate filter; SPI `match` = opcode; an op rp2 cannot raise on is refused with
  `ValueError` (`scan`; SPI `write`); an SPI read fault fires only on a transfer of ≥ `_SPI_DMA_MIN_SIZE` bytes
  (`ports/rp2/machine_spi.c:267-318`) — the comment saying the queue is not size-gated goes; `pending(op) -> int`.
  Both in `TEST_API`.
- **Resolved**: A.U24.78 vs A.U25.70 on `match`: I2C `match` is the command key and `address=` the address filter (A.U24.78's
  verified text, the twin's own key) — settled.
- **Unit**: U24
- **Depends**: M.TEST_HELP.013, M.TEST_HELP.016.
- **Blast carried by**: 25 unit call sites `inject_fault(op, OSError(errno.X, "m"), times=n)` → `inject_fault(op,
  OSError, errno.X, "m", times=n)` → A.U24.78 (TEST_UNIT); `tests/_bus_hazard_catalog.py` → M.TEST_HELP.026;
  `tests/_digital_twin_construction_scenarios.py` → M.TEST_HELP.031; twin `pending()` → A.U24.82 (TWIN).
- **Kind**: test

### M.TEST_HELP.016 SPI fake uses rp2's bit-order numbers
- **From**: A.U24.23, A.U24.26 (cite), A.U14.21 (holds), A.U16.14 (holds), A.U13.08 (blast), A.U25.16 (twin half)
- **Site**: `tests/machine.py:200-262` (`_SPI_DMA_MIN_SIZE` `:204-206`, class comment `:209-212`, `MSB`/`LSB`
  `:213-214`, default `:227`, `init()` LSB check `:258-261`).
- **Change**: `MSB = 1`, `LSB = 0` (pico-sdk `hardware/spi.h:184-187`; `ports/rp2/machine_spi.c:41, 150, 202-203,
  255-256`), default `firstbit = MSB`; `init()` refuses `LSB` with `NotImplementedError` as rp2; `_SPI_DMA_MIN_SIZE = 32`
  cites `ports/rp2/machine_spi.c:267`; the class comment keeps "only a ≥ 32-byte reading transfer can raise (RX overrun,
  `OSError(EIO)`, F.5.2)"; `deinit()` cites F.5.1 (no-op). `TEST_API` lists `rx_overrun`, `read_queue`, `log`,
  `inject_fault`, `pending`.
- **Resolved**: —
- **Unit**: U24 (same commit as A.U25.16: product code is shared by both tiers).
- **Depends**: M.TEST_HELP.010.
- **Blast carried by**: `tests/test_asy_spi_driver.py:229, 234-241, 982`, `tests/test_asy_fram_wire_trace.py:33-34`
  expected tuples → A.U24.23 (TEST_UNIT); LSB-trigger tests → A.U13.08 (TEST_UNIT); twin → A.U25.16 (TWIN).
- **Kind**: test

### M.TEST_HELP.017 UART fake never lends stdin to a real poll
- **From**: A.U24.15 (1)/(2)/(4), A.U14.28 (F.7 row 12 co-land), A.U36.532 (blast), AC_NOTES 29
- **Site**: `tests/machine.py:326-329` (class comment), `:330` `_MP_STREAM_POLL`, `:385-393` `ioctl()`, `:579-596`
  `LinkPoller` (comment `:580-582`, `ipoll()`).
- **Change**: `ioctl(req, arg)`: `MP_STREAM_POLL` answers through `poll_mask(arg)`; every other request (notably
  `MP_STREAM_GET_FILENO`) returns `-errno.EINVAL`, rp2's answer, so a real poll consults this `ioctl()` every round
  instead of watching fd 0 (`extmod/modselect.c:252-266`); each POLL request increments `UART.real_poll_queries`.
  `poll_mask(mask) -> int` (public test API, the old POLL branch body) is what `LinkPoller.ipoll()` and the contract
  read. Comments, one line each: class `:326-329` → "# Bounded stand-in, never a real select.poll(): the fake's
  readiness must be scripted, not polled in real time (CLAUDE.md "Known hang cause")."; `LinkPoller` `:580-582` → the
  same line. `TEST_API` adds `poll_mask`, `real_poll_queries`.
- **Resolved**: AC_NOTES 29 — CLAUDE.md's mechanism ("never detects readiness") is wrong; the real cause is the fakes
  answering `GET_FILENO` with 0 — fixed here at the fake, the F.7 row 12 text co-landing (A.U14.28).
- **Unit**: U24
- **Depends**: M.TEST_HELP.010 (the `real_poll_queries` teardown check).
- **Blast carried by**: contract readiness reads → M.TEST_HELP.025; old-mechanism comments in `tests/test_asy_uart_driver.py:24-25,
  32-33, 44-45, 439-441, 857-859`, `tests/test_asy_uart_link_driver.py:43` → A.U24.15 (TEST_UNIT); `tests/_uart_comm_harness.py:67-68`
  → M.TEST_HELP.023; new L1 registering a real `select.poll()` (zeroes the counter itself) → A.U24.15 (TEST_UNIT); twin
  `poll_mask()` → A.U24.80 (TWIN); SPEC F.7 row 12 → A.U14.28 (SPEC); CLAUDE.md hang bullet → A.U36.546 (DOCS).
- **Kind**: test

### M.TEST_HELP.018 UART fake models readline size, TX drain, buffer clamp
- **From**: A.U13.12 (fake), A.U13.13 (fake), A.U24.26 (1)/(2), A.U25.22 (holds: unit `feed_rx` stays), A.U36.532
- **Site**: `tests/machine.py:331-387` (constants, `__init__` validation and its comment `:351-353`, `feed_rx`),
  `:403-407` (`would_have_blocked_bytes` comment), `:436-447` `readline()`, `:449-462` `write()`.
- **Change**: (1) `readline(size=-1)`: serves at most `size` bytes up to `\n`; `size > queued` counts `size - queued`
  into `would_have_blocked_bytes`; `size == -1` with no `\n` queued counts the one probe byte past the buffer; its
  comment → "# Clamped to any() like every counted read." (2) `txdone() -> bool`: `True` unless `tx_pending_rounds > 0`,
  which each call decrements (test knob, reset by the hook). (3) `rxbuf`/`txbuf` below 32 clamp to 32
  (`ports/rp2/machine_uart.c:372-373, 387-388`), so the validation comment loses that item; constants cite
  `machine_uart.c:68-69, 82-84` and the validation order `:353-392`; `write()`'s short count/`None` cites
  `mp_machine_uart_write`'s lines. (4) The `would_have_blocked_bytes` comment's "Part F.5.8" → "F.8.2" (U36,
  A.U36.532). `TEST_API` adds `feed_rx`, `rx_queue`, `writable`, `write_limit`, `tx_pending_rounds`,
  `would_have_blocked_bytes`, `log`, `deinit_count`, and the stored constructor fields (no getters on real UART).
- **Resolved**: A.U25.22 removes the *twin's* `feed_rx()` only; the unit fake keeps it (`tests/test_asy_uart_comm.py`
  uses it).
- **Unit**: (1) and (2) land with A.U13.12/A.U13.13 in U13 (the driver calls `readline(want)`/`txdone()`); (3)-(4) U24
  / U36.
- **Depends**: M.TEST_HELP.017.
- **Blast carried by**: `tests/test_asy_uart_driver.py:1068, :1775` patched readlines gain `size`; comments `:1629,
  :1648, :1670, :1873`; TX-ring L1 → A.U13.12/A.U13.13 (TEST_UNIT); contract check → M.TEST_HELP.025; twin
  `readline(size)`/`txdone()` → A.U13.12/A.U13.13 (TWIN).
- **Kind**: test

### M.TEST_HELP.019 UART link drops the unused direction lookup
- **From**: A.U24.77, A.U25.30 (holds), A.U25.04 (holds), A.U24.73
- **Site**: `tests/machine.py:500-530` (`UARTLink`, `direction_to()` `:527-530`), `:559-563` `settle()`.
- **Change**: `direction_to()` removed (no caller). The class comment's "(A1/A3)" labels go (G9/R12) → "one
  independent FIFO per direction with its own fault knobs"; `settle()` stays a synchronous no-op (every caller is
  synchronous test scope). `_LinkDirection` and `UARTLink` gain `TEST_API` (they are wholly test-only: the tuple is
  "all public names").
- **Resolved**: —
- **Unit**: U24
- **Depends**: —
- **Blast carried by**: twin `direction_to()` → A.U25.22 (TWIN).
- **Kind**: test

### M.TEST_HELP.020 Timer fake records a fake clock and real keywords
- **From**: A.U11.39, A.U10.12 (`:609` comment), A.U24.73 (explicit keywords), A.U24.26 (ENOMEM cite), A.U24.07,
  A.U35.33/A.U35.34 (holds: `trigger()`/`drop()`), A.U14.12 (holds)
- **Site**: `tests/machine.py:604-661` (`class Timer`; comments `:607-610`, `:612-619`; `__init__` `:621-629`).
- **Change**: `Timer.clock_ms: ClassVar[int] = 0` (advanced only by tests); each `init()` records
  `(Timer.clock_ms, period, mode)` in `self.arms`; `__init__(self, id=-1, *, mode=PERIODIC, period=-1, freq=None,
  callback=None, hard=None)` — the keyword list `init()` takes (`ports/rp2/machine_timer.c:50-145`), calling `init()`
  only when any is given; the `:609` comment → "# Records every construction, so a test can assert the product reuses
  one preallocated Timer through init() (SPECIFICATION.md F.1)." (no sequencer name); the ENOMEM line cites
  `machine_timer.c:107`. `trigger()` and `drop()` unchanged. `TEST_API`: `all_timers`, `raise_on_arm`,
  `raise_on_arm_exc`, `clock_ms`, `arms`, `trigger`, `drop`, `deinit_called`, `callback`, `period`, `mode`.
- **Resolved**: —
- **Unit**: U11 (`clock_ms`/`arms`, with A.U11.39's scenario); U24 (keywords, comments, `TEST_API`).
- **Depends**: M.TEST_HELP.010.
- **Blast carried by**: per-device sequencer scenario → M.TEST_HELP.038; `tests_scripts/test_timer_stagger_no_coincidence.py`
  retired → A.U11.39 (TSC); twin Timer → A.U25.19 (TWIN).
- **Kind**: test

### M.TEST_HELP.021 RTC fake returns what rp2's getter returns
- **From**: A.U24.24, A.U24.07
- **Site**: `tests/machine.py:663-681` (`class RTC`, comment `:664-666`).
- **Change**: setter: exactly 8 items or `ValueError` (`ports/rp2/machine_rtc.c:84`); year-second converted to epoch
  seconds by pure calendar arithmetic (no host `mktime`), weekday and subseconds ignored (`:85-92`); getter: the stored
  seconds back, date normalised, weekday recomputed (Monday 0), subseconds 0 (`:67-81`). The class comment (and its
  BACKLOG history pointer) → those three facts with the citation. The stored seconds are class state (one peripheral),
  reset by the hook. `TEST_API`: `raise_exc`.
- **Resolved**: —
- **Unit**: U24
- **Depends**: M.TEST_HELP.010.
- **Blast carried by**: tests passing an out-of-range field now read a normalised date → A.U24.24 (TEST_UNIT); NTP/RTC
  tests holding a 9-tuple or 7-tuple (grep at landing) → A.U24.24 (TEST_UNIT).
- **Kind**: test

## tests/_fram_chip_fake.py

### M.TEST_HELP.022 FRAM fake: real sizes, cited latch rules, cut and count knobs
- **From**: A.U24.22, A.U16.R01 (one-shot WREN drop), A.S0930.25 (`cut_after_bytes`), A.U10.08/A.U35.28 (write
  counter), A.U24.78 (opcode match), A.SDEP.08 (`:106`), A.S0930.21 (holds), A.U35.20 (holds), A.U16.14 (holds)
- **Site**: `tests/_fram_chip_fake.py:1-121` (`FakeMB85RS64V.__init__` `:24-46`, `_decode_addr()` `:52-53`, `write()`
  `:55-101`, `readinto()` `:103-121`).
- **Change**: (1) `FakeMB85RS64V(…, size=0x2000, rdid=…)`: `memory = bytearray(size)`; address width 2 bytes for
  `size <= 0x10000`, 3 above (MB85RS64V DS501-00015 p.9, MB85RS2MTA DS501-00032 p.9; upper bits beyond the array
  ignored); `_decode_addr()` and the READ/WRITE data split follow the width. (2) Each WEL rule cites its page on its
  line (set by WREN; cleared by WRDI and at CS rise after WRITE/WRSR, p.6-7; WRSR needs WEL and the protect table,
  p.11). (3) Knobs: `drop_next_wren = 0` (WREN dropped while > 0, decrementing) beside `drop_wren`/`drop_next_wrdi`;
  `cut_after_bytes: int | None` — after that many further WRITE data bytes the fake stops applying writes (a power
  cut), the test raising its own `PowerCut`; counters `write_transactions` (WRITE commands that reached the data
  phase) and `bytes_written`. (4) The fault hook passes the pending opcode as the SPI `match` key, so
  `inject_fault("readinto", OSError, errno.EIO, match=_OPCODE_READ)` targets one command (M.TEST_HELP.015's size gate
  still applies). (5) `:106` "1.29" → "v1.29.0". `TEST_API` lists every knob and counter.
- **Resolved**: A.U10.08 offers "wrap the SYSTEM logger's `_write()` *or* add a write counter to the chip fake" —
  merged as the chip counter, which A.U35.28 then reuses (one mechanism; agent decision D4).
- **Unit**: U24; `drop_next_wren` lands earlier with A.U16.R01's test (U16) — stage 1; `write_transactions` lands with
  A.U10.08's scan-budget scenario (U10) — stage 1; `cut_after_bytes` with A.S0930.25 (its unit).
- **Depends**: M.TEST_HELP.015, M.TEST_HELP.016.
- **Blast carried by**: `_FakeMB85RS2MTA`/`_FRAM_FAKE_BY_MAX_SIZE` → M.TEST_HELP.035; power-cut L1 → A.S0930.25
  (TEST_UNIT); WREN-retry L1 → A.U16.R01 (TEST_UNIT); scan-budget and fault-storm scenarios → M.TEST_HELP.037/M.TEST_HELP.042; twin FRAM
  → M.TWIN.011 (TWIN).
- **Kind**: test

## tests/_uart_comm_harness.py

### M.TEST_HELP.023 UART pair harness: shared bounded runner, asserted setup
- **From**: A.U24.08, A.U24.31, A.U24.15 (4), A.U5.12, A.U13.17, A.U10.37/A.U10.38 (H1), A.U24.67 (2), A.U24.73,
  A.S0930.03 (holds), A.U35.06 (holds), A.SDEP.17 (holds), A.U17.20 (holds)
- **Site**: `tests/_uart_comm_harness.py:1-3` (docstring), `:37-39` `run()`, `:46-83` `Pair.__init__`, `:116-119`
  `build_pair()`.
- **Change**: (1) `run()` deleted; callers use `_async_harness.run(coro, RUN_LIMIT_S)` (the sync-scope guard makes a
  nested call raise instead of segfaulting). (2) `build_pair()` → `pair = Pair(**…)`; `assert await pair.setup(),
  "Pair.setup() failed - both roles must be ready before the test's own assertions mean anything"`; it stays a
  coroutine, built inside the one coroutine `run()` drives (never calls `run()` itself). (3) `Pair.__init__`: drivers
  `UART(…, poll_wait_ms=POLL_WAIT_MS, poll_idle_ms=POLL_WAIT_MS, crc=…)` (the new idle default of 50 ms would slow
  every listener; 2 × 1 + 1 + 21 ≤ `TIMEOUT_MS` holds the J.6 floor); the responder gets `callbacks=
  ResponderCallbacks(get_callback, set_callback, None)`; `**comm_kwargs` → the explicit keywords `UARTComm.__init__`
  takes beyond those `Pair` sets (read from its signature at landing); types `CRCPass`, `UARTComm` (H1). (4) The
  poller comment `:67-68` → "# Bounded stand-in, never a real select.poll(): the fake's readiness must be scripted, not
  polled in real time (CLAUDE.md "Known hang cause")." (5) Docstring line 2 → "driven as concurrent tasks the way a
  bench board drives them across its jumper." No `Any` (`Coroutine` alias from `_async_harness`).
- **Resolved**: —
- **Unit**: U24 (the `poll_idle_ms` argument lands with A.U13.17 in U13: the default changes there — stage 1).
- **Depends**: M.TEST_HELP.043, M.TEST_HELP.017.
- **Blast carried by**: `tests/test_uart_comm_hazard.py` `hazard_pair()` and every `run()` caller → A.U24.08 (TEST_UNIT;
  a fixture is built in sync scope, A.U14.18's rule); `tests/test_asy_uart_link_driver.py` local `run()`/`build_pair()`
  → A.U24.08/A.U24.31 (TEST_UNIT); the exerciser's CRC-mode registration copies the shape → A.S0930.03 (TEST_UNIT);
  latency proof on the loopback pair → A.U35.06 (TEST_UNIT).
- **Kind**: test

### M.TEST_HELP.024 UART harness bounds become public tagged constants
- **From**: A.U8C.03, A.U8C.19 (importer), A.U8C.17 (importer)
- **Site**: `tests/_uart_comm_harness.py:33-34` (`TIMEOUT_MS`, `POLL_WAIT_MS`), `:37` (run limit 10), `:103` (drain 5).
- **Change**: tags `# @tunable l1.uart_comm_harness_timeout_ms = 100` above `TIMEOUT_MS` and `# @tunable
  l1.uart_comm_harness_poll_wait_ms = 1` above `POLL_WAIT_MS`; new `RUN_LIMIT_S = 10` (`# @tunable
  l1.uart_comm_harness_run_limit_s = 10`) passed to `_async_harness.run()` by the callers; new `LISTENER_DRAIN_S = 5`
  (`# @tunable l1.uart_comm_harness_listener_drain_s = 5`) used at `:103`. Rows per A.U8C.03 (basis "estimated
  (agent, <commit>) — measurement owed", re-check trigger "the code under test or the host class changes").
- **Resolved**: A.U8C.03 names them `_RUN_LIMIT_S`/`_LISTENER_DRAIN_S` while A.U8C.19 imports them into another
  module; a name imported across modules is public (D.15/G10), so they are written without the underscore —
  agent decision D5.
- **Unit**: U8C (B1, after A.U8.01-A.U8.03); the `run()` deletion (M.TEST_HELP.023, U24) keeps the constant.
- **Depends**: —
- **Blast carried by**: `tests/test_asy_uart_link_driver.py:25-29, :58` imports `RUN_LIMIT_S`/`LISTENER_DRAIN_S` (not
  `_…`) → GAP-T1 (TEST_UNIT, A.U8C.19); `tests/test_asy_uart_comm.py` likewise → A.U8C.17 (TEST_UNIT).
- **Kind**: test

## tests/_uart_link_contract.py

### M.TEST_HELP.025 Link contract reads readiness by mask, checks clamped readline
- **From**: A.U24.15 (2), A.U24.80, A.U13.12 (contract), A.U24.06, A.U36.532 (`:197`), A.U25.04/A.U25.30 (hold),
  A.U24.73
- **Site**: `tests/_uart_link_contract.py:55-70` (`check_pollin_follows_fifo_content`,
  `check_pollout_follows_writable_gate`), `:195-197` (comment "F.5.8"), `:209-215` (readline check comment), `:225-246`
  `ALL_CHECKS`.
- **Change**: readiness reads `b.poll_mask(select.POLLIN)` / `a.poll_mask(select.POLLOUT)` instead of `ioctl(3, …)`;
  new `check_readline_with_a_size_is_clamped_and_counted` (a `readline(n)` with fewer than `n` queued counts `n -
  queued`, identically in both fakes) listed in `ALL_CHECKS`; the readline comment `:211` → "clamped to `any()` like
  every counted read"; `:197` "F.5.8" → "F.8.2" (U36). `LinkFactory` typed through `_protocols.UARTLike`.
- **Resolved**: —
- **Unit**: U24 (the new check lands with A.U13.12's fakes in U13 — stage 1; the `:197` repoint U36).
- **Depends**: M.TEST_HELP.017, M.TEST_HELP.018.
- **Blast carried by**: completeness test `test_every_contract_check_is_registered` in `tests/test_machine_uart_link.py`
  → A.U24.06 (TEST_UNIT); twin `poll_mask()` and `readline(size)` → A.U24.80/A.U13.12 (TWIN).
- **Kind**: test

## tests/_bus_hazard_catalog.py

### M.TEST_HELP.026 Hazard adapters: fresh buses, attached probes, declared exceptions
- **From**: A.U24.20 (`make_i2c`), A.U24.21/A.U24.43 (2) (`attached`), A.U24.01 (4), A.U15.25 (7), A.U15.27,
  A.U15.28, A.U15.R02, A.U15.R01/A.U15.R03 (hold), A.U15.01/A.U15.12/A.U4.05/A.U12.18/A.U30.06 (hold), A.U35.16
  (adapter flag), A.U35.19, A.U24.28 (`exercise_raises`), A.U24.78 (call form), A.U36.544 (`:281-282`), A.U24.73,
  A.U10.38 (H1)
- **Site**: `tests/_bus_hazard_catalog.py:41-42` `make_i2c()`, `:86` `_BMP_EXPECTED_TEMPERATURE`, `:97-104`
  `seed_bmp_ready()`, `:135-152` `I2CHazardAdapter`, seeders `:154-…`, `_exercise_*` (`:174-196`, `:216-226`, `:286-300`),
  `:281-282` comment, constructors `:308-323`, catalog `:328-332`.
- **Change**: (1) `make_i2c(port_id=1)` calls `machine.I2C.reset_id(port_id)` before constructing (a power-cycled
  controller). (2) Every adapter's `seed()` adds its address to the fake's `attached`. (3) `BMP_EXPECTED_TEMPERATURE =
  28.460795242070162` (public, one definition, its hand calculation from the planted calibration bytes cited on the
  line — BMP388 datasheet §9.2), imported by `tests/test_asy_bmp3xx_driver.py` and
  `tests/test_bus_hazard_multi_device.py`. (4) `seed_bmp_ready(i2c, address=0x77, chip_id=0x50)`, its `:102` comment →
  "# _REGISTER_CHIPID: 0x50 (BMP384/388) by default, 0x60 (BMP390) on request - both documented IDs". (5)
  `I2CHazardAdapter` gains `exercise_raises: tuple[type[BaseException], ...] = ()`, `releases_bus_mid_read: bool =
  False` (True for `sgp40` only) and `default_address: Callable[[I2C], int]` (constructs the driver with no address
  and returns its `I2CDevice.device_address`). (6) Each `_exercise_*` loop catches only its adapter's
  `exercise_raises`, never `Exception`; `_exercise_bmp3xx` calls `get_pressure_altitude`; `_exercise_sgp40` gains
  `instance.turn_heater_off` (the sweep then proves it touches 0x59 only); `_exercise_scd30` keeps `setup()` (which
  now reads one extra register frame, seeded). (7) `_construct_scd30/_sgp40/_isl29125` build without `address=`
  (the adapter signature keeps `address` for seeding and BMP3XX). (8) `:281-282` → "# Volatile config register (the
  OSR register is volatile, BMP388 datasheet §5.3) - no real-hardware write budget." after the executor confirms the
  page in `datasheets/bmp3xx/`. (9) `inject_fault` calls take the class-plus-args form. (10) `_RESERVED_I2C_RANGES`/`_is_reserved` become public
  `RESERVED_I2C_RANGES`/`is_reserved` (A.U35.19 imports them into `tests/test_bus_hazard_multi_device.py`; a name
  imported across modules is public). Typed through `_protocols.I2CLike`, no `Any`.
- **Resolved**: A.U24.28 removes the sweep's blanket `except`; the same rule is applied to the per-call `except
  Exception: pass` inside each `_exercise_*` (otherwise the sweep's "an exercise that raised before its first
  transfer fails" never bites) — agent decision D6.
- **Unit**: U24 (stage 1 U15: (4), (6)'s `get_pressure_altitude`/`turn_heater_off`, (7) land with A.U15.25/.27/.28/.R02,
  whose product changes break the old calls; stage 2 U24; (8) U36; (5)'s two U35 fields with A.U35.16/A.U35.19).
- **Depends**: M.TEST_HELP.013, M.TEST_HELP.014, M.TEST_HELP.015.
- **Blast carried by**: per-ID loop in `tests/test_bus_hazard_multi_device.py:114` and its `switches` floors →
  A.U15.25/A.U35.16 (TEST_UNIT); reserved-address check → A.U35.19 (TEST_UNIT); BMP temperature importers → A.U24.01
  (TEST_UNIT); scenario consumers → M.TEST_HELP.027.
- **Kind**: test

### M.TEST_HELP.027 Hazard scenarios: every writer, recovery, exact sweep, honest skips
- **From**: A.U24.27, A.U24.28, A.U13.R02 (1), A.U35.16 (generated assertion), A.U15.15 (`:507`), A.U25.10 (holds),
  A.U7.07 (`Skip`)
- **Site**: `tests/_bus_hazard_catalog.py:365-384` (all-occupants reads, floor `:381-384`), `:387-425`
  (write-vs-siblings), `:502-524` (general call, docstring `:507`, "no broadcaster" `:515-518`), `:523-542` (address
  sweep), `:531` (actionable `KeyError`).
- **Change**: (1) Write-vs-siblings loops over every writer: for each writer and offset a fresh bus, that writer
  writes while every other occupant reads; failures collected per `(writer, offset)`. (2) No writer → `raise
  microtest.Skip("no occupant of this bus has a safe write")`; the general-call scenario likewise `Skip("no occupant
  broadcasts a general call")`. (3) `SPI_HAZARD_CATALOG` (empty at HEAD: every SPI bus has one occupant) with the same
  actionable `KeyError` for an SPI occupant missing from it. (4) New `scenario_bus_recovery_does_not_disturb_concurrent_
  siblings(build_fresh_bus_and_occupants, iterations=6, offsets=None)`: per offset, every occupant's read loop runs
  while one task calls `i2c.recover()` after `offset` yields; asserts every sibling read valid, no transfer in the log
  between the clear's first pin event and the re-construction's `("init", …)` entry, and that recovery ran (that
  `init` entry present). (5) All-occupants reads: `sibling_inside_window(log, owner_addr)` (helper, one-line comment
  naming its limit) asserted for every `releases_bus_mid_read` occupant with a sibling; the `switches >=
  len(occupants)` floor stays only for buses with no flagged occupant. (6) Address sweep: `await adapter.exercise()`
  catching only `exercise_raises`; it also runs `write_once` and `general_call`; assertion `touched == {address}` (or
  `{address, 0x00}` with a general call). (7) `:507` → "(the owner-decided general-call reset, SPECIFICATION.md Part
  C.8)".
- **Resolved**: —
- **Unit**: U24 ((4) lands with A.U13.R01's `recover()` in U13 — stage 1; (5) U35; (7) U15).
- **Depends**: M.TEST_HELP.026, M.TEST_HELP.001 (`Skip`).
- **Blast carried by**: `tests/test_bus_hazard_generated.py` bus kinds and `spi<n>` port ids → A.U24.27 (TEST_UNIT);
  L1/L2 recovery runs → A.U13.R02 (TEST_UNIT, TWIN); twin general call resets the SGP40 → A.U25.10 (TWIN); L3/L4 sweep
  scripts → A.U13.R02 (HW_DEV, HW_BENCH).
- **Kind**: test

## tests/_boot_contiguity_probe.py

### M.TEST_HELP.028 Boot probe follows the generated boot sequence step for step
- **From**: A.U24.79, A.U20.02, A.U20.06, A.U10.12, A.U11.10, A.U32.06, A.U10.30, A.U24.46, A.U24.43 (2), A.U24.22,
  A.U8C.01, A.U8C.72 (mirror), A.U27.28, A.U36.544 (`:7`), A.U0.07 (`:125-126`), A.U10.37/A.U10.35 (H1), A.U10.07,
  A.U30.16, A.U31.03, A.U31.17, A.S0930.13 (hold), A.U24.07 (hold), A.U24.73
- **Site**: `tests/_boot_contiguity_probe.py:1-7` (header), `:12` (`fram_fake_class` import), `:33-38` (bounds),
  `:42-48` `_dump()` (comment `:43-44`), `:76-113` (`_drive_timers()`, `_run_starter_loop()`), `:116-161` `_main()`.
- **Change**: (1) Header → module docstring (≤ 3 lines): "Boots one generated device and prints a labelled
  `micropython.mem_info(1)` map at each end of the two one-time boot lists, the placement collects live or
  suppressed; run by `tests_scripts/test_digital_twin_boot_contiguity.py` (SPECIFICATION.md E.8)." — the `:7` pointer
  is E.8, which gains the platform-print sentence (A.U36.544). (2) `_main()`: `require_fresh()`; seeds the plan's I2C
  occupants (`_sensortask_scenarios.seed_occupants(device)`, M.TEST_HELP.035) and installs the device's FRAM fake
  factory; one `_ProbeGc` on `asy_system_service.gc`, its label switched by wrapping
  `asy_system_service.SystemService.run_setups` ("batch" inside, "starter" outside), since both lists run in
  `SystemService` (A.U11.10); `_dump("baseline")`; timed `module, wdt = await boot_generated(device, cfg_path=…,
  web_host="127.0.0.1", web_port=0)` (construction plus `run_setups()`); `_dump("after_batch")`; then main()'s order:
  `await asyncio.wait_for(sysfunct.start_tasks(module._collect_task_starters(),
  task_names=module._collect_task_names()), _STARTER_LOOP_TIMEOUT_MS / 1000)` — it returns after its last placement
  collect, so `_dump("after_starter_loop_end")` follows at once and the counting wrapper (and its `method-assign`
  ignore) goes; then `_drive_timers(sysfunct, module._collect_trigger_starters(), module._collect_timer_starters())`
  runs `start_timers(triggers, timers)` as a task and calls `sysfunct._sequencer_timer.trigger()` whenever its callback
  is armed, bounded by `_TIMERS_TIMEOUT_S`. The supervisor is never entered. (3) Bounds: `_STARTER_LOOP_TIMEOUT_MS`
  and `_TIMERS_TIMEOUT_S` keep A.U8C.01's tags; `_STARTER_LOOP_GRACE_MS` and the `sleep_ms(20)` poll go with the loop
  (their rows withdrawn, H3). (4) `:43-44` "(MEASUREMENTS M2.2's pinning artefact)" and `:160` "(MEASUREMENTS M3.9)" →
  "(HEAP_FRAGMENTATION_MEASUREMENTS.md archive §M2.2 / §M3.9, commit `12640c2`)" where those headings exist in the
  archive, else the parenthesis goes (A.U36.544 (2)'s rule). (5) Function-level `import system_service` moves to module
  level as `import asy_system_service`; no `__import__` (H5). No `Any`.
- **Resolved**: A.U10.12's "probe adapted to the two-list `start_timers()`" and A.U20.06's "switch to `start_tasks()`,
  never enter the supervisor" combine with M_GEN's `main()` order (tasks before timers): the probe measures the
  sequence `main()` runs. A.U8C.01's grace and poll rows exist only for the counting loop `start_tasks()` makes
  unnecessary — withdrawn (agent decision D8).
- **Unit**: U32 (latest: `task_names=`); stage U20 carries the boot entry/`main()` split, `run_setups()` and
  `start_tasks()` (with A.U20.02/A.U20.06/A.U11.10); stage U10 the two-list `start_timers()`; U8C tags; U24 the helper
  calls and header; U36 the `:7` repoint.
- **Depends**: M.TEST_HELP.047 (`boot_generated`), M.TEST_HELP.046 (`require_fresh`), M.TEST_HELP.035
  (`seed_occupants`, FRAM factory).
- **Blast carried by**: the board mirror `tests_hardware/device_scripts/heap_layout_after_full_boot_sequence.py`
  follows the same order and drops `_STARTER_LOOP_GRACE_MS` → GAP-H1 (HW_DEV, A.U8C.72/A.U20.06);
  `tests_scripts/test_digital_twin_boot_contiguity.py:262` `_MIRRORED_BOUNDS` drops `_STARTER_LOOP_GRACE_MS` and its
  `:242-254` source counts read `_collect_setups()` → GAP-H1 (TSC, A.U11.10); GC-site checker rows `_dump`,
  `_ProbeGc.collect` hold → A.U30.16 (TSC).
- **Kind**: test

## tests/_digital_twin_construction_scenarios.py

After U25 this library keeps only in-process L2 work (construction, wiring, boot sequence, pin identity — no HTTP);
its two HTTP scenarios move to the host-side harness (A.U25.46, OR125.a).

### M.TEST_HELP.029 Twin construction library: derived devices, shared boot, honest checks
- **From**: A.U24.79, A.U20.02, A.U20.06, A.U24.65 (1)/(4), A.U24.70, A.U24.08, A.U24.06, A.U24.50 (twin `Skip`),
  A.U24.43 (1) (derived names), A.U10.30, A.U24.46, A.U25.03/A.U25.24 (`reset_peripherals()` first), A.U25.33
  (offline NTP), A.U25.48 (`:1`), A.U8C.02 (`_RUN_TIMEOUT_S`), A.U20.42 (holds), A.U25.43 (holds), A.U27.23 (holds),
  A.U0.07, A.U10.40 (H1 key), A.U24.73
- **Site**: `tests/_digital_twin_construction_scenarios.py:1-3` (docstring), `:41-42` `run_timed()`, `:47`
  `_DEVICES`, `:50-53` `_wiring_plan()`, `:56-61` `_cancel()`, `:64-67` port comment and `_PORT_BASE_BY_DEVICE`, `:95-100`
  `_boot_device()`, `:103-118` `_present_optional_instances()`, `:121-132` boots scenario (mandatory tuple `:128`),
  `:216-232` `register_for_device()`.
- **Change**: (1) Docstring `:1` "across all 6 real devices" → "across every generated device"; `:2-3` E.2.1 pointer
  holds (now `### E.2.1`). (2) `run_timed`/`_cancel` copies go (`_async_harness`). (3) `_DEVICES`/`_wiring_plan()` →
  `_twin_devices.generated_devices()`/`wiring_plan()`; the "one of this module's own real devices" assert reads the
  derived set. (4) Port base: this library's band from `_port_bands` (A.U24.70), the device's offset its index in
  `generated_devices()`, band-end asserted; the port comment `:64-66` → one line naming the band table. (5)
  `_boot_device(port, device)`: `machine.reset_peripherals()`, `network.reset_interfaces()`,
  `machine.configure_wiring(wiring_plan(device))`, then `module, wdt = await boot_generated(device, cfg_path=cfg_dir,
  web_host="127.0.0.1", web_port=port)`, whose `offline_ntp=True` default writes the offline NTP config through the one
  `write_offline_ntp_config()` (M.TEST_HELP.047; key `NTPHost`, A.U10.40 lands first); `require_fresh()` once at
  import. (6) Boots scenario: `"watchdog"` leaves the mandatory tuple (the global is gone) and the mandatory and optional
  names come from the plan (buses from `plan["buses"]`/`plan["spi"]`, instances from `plan["instances"]`), not a
  literal list (agent decision D11, A.U24.43 (1)'s rule applied to this library); the `run_timed(…, 10.0)` literal → `_RUN_TIMEOUT_S = 10.0` (`# @tunable
  l2.construction_scenarios_run_timeout_s = 10.0`). (7) `register_for_device()` asserts the count of module-level
  `_scenario_*` functions equals `len(_PARAM_SCENARIOS)`; a scenario whose device lacks the driver raises
  `microtest.Skip("<device> declares no <x>")`. No `Any`.
- **Resolved**: A.U25.43 exempts a scenario library from the prewarm rule; this one keeps its two module-level calls (it
  boots devices itself) — unchanged.
- **Unit**: U25 (latest: reset/offline NTP); stage U24 carries the harness, device set, port band, `boot_generated`,
  register assert (A.U24.08's deletion of `run_timed` would otherwise break the file in U24); stage U20 the `main()`/
  `watchdog=` change; U8C the tag.
- **Depends**: M.TEST_HELP.043, M.TEST_HELP.046, M.TEST_HELP.047, M.TEST_HELP.055, M.TEST_HELP.056 (port bands).
- **Blast carried by**: six wrappers → `tests/test_digital_twin_construction.py` (`PER_DEVICE = True`) → A.U24.65
  (TWIN); `test.sh` per-device expansion → A.U24.65 (3) (SCR); the twin runner's own offline write imports the same helper → GAP-H3 (TWIN, A.U25.33).
- **Kind**: test

### M.TEST_HELP.030 Twin construction library gains boot-sequence and IRQ-pin scenarios
- **From**: A.U25.47, A.U25.52, A.U20.07 (recorder)
- **Site**: `tests/_digital_twin_construction_scenarios.py` (two new `@_register_param` scenarios).
- **Change**: (1) `boot_sequence_matches_the_generated_expectation`: boot through the real `main(watchdog=…)` with
  `tests/_boot_recorder.py`'s recorders wrapped around the real `SystemService` methods and every instance's `setup`,
  stopped at `supervise_tasks()` entry; the recorded list equals `sensortask_<device>_expected.json`'s
  `boot_sequence`; the twin WDT's `would_have_triggered_count == 0` over the boot; the first NTP force sync follows the
  timer starts. (2) `irq_pins_are_shared_by_chip_fake_and_driver`: after the boot, for every plan attachment with
  `irq_pin`, the reader's IRQ `Pin` `is machine.Pin(attachment["irq_pin"])` and `is` the chip fake's `_rdy_pin`/
  `_int_pin`; an ISL29125 INT line reads high at idle.
- **Resolved**: A.U25.47 imports "the same recorder A.U20.07 writes for L1 … from its helper, not copied"; A.U20.07
  sites it inside `tests/_sensortask_scenarios.py`, which a twin process must not import (it binds unit-tier FRAM
  fakes) — the recorder is its own module `tests/_boot_recorder.py` (M.TEST_HELP.061), used by both (agent decision D9).
- **Unit**: U25
- **Depends**: M.TEST_HELP.029, M.TEST_HELP.061.
- **Blast carried by**: expected JSON writer → A.U20.07 (GEN/SCR); twin `Pin` identity and chip pins → A.U25.03/A.U25.52
  (TWIN).
- **Kind**: test

### M.TEST_HELP.031 Twin HTTP scenarios move to the host-side harness
- **From**: A.U25.46 (2), A.U24.47, A.U0.29 (E08), A.U20.28 (`:174`), A.U25.31, A.U25.45 (`:147`, `:193`), A.U25.70
  (`:182`), A.U24.82, A.U8C.02 (deferred sleeps), A.U36.004 (none here), A.U24.67/A.U25.48 (hold)
- **Site**: `tests/_digital_twin_construction_scenarios.py:135-210` (`_scenario_measurements_and_sensors_shape`,
  `_scenario_bus_fault_degrades`), and the `_http_client` / `assert_sensor_payload_not_self_wrapped` imports.
- **Change**: both scenarios leave this file in U25 (deleted here; their goals and assertions are rewritten in
  `scripts/_digital_twin_scenarios.py` by A.U25.46). The content their constituents owed travels with them (GAP-H2):
  the measurements/sensors GET compares strict-parsed bodies; the bus-fault scenario injects a sustained fault
  (`times=1000`, class-plus-args form) on the SGP40 chip's `writeto` through the runner's fault spec, starts the SGP40
  reader's own starters, waits until the injector's `pending()` count fell (consumed by a real read), then `GET
  /measurements` → 200 with strict JSON whose SGP40 measured fields are all `null`, and `GET /status` shows SGP40's error
  count ≥ 1; its comment carries "(owner, 2026-08-13)" for the "might point us to oversights" value and drops the false
  "no tests/machine.py-backed fake has a comparable fault surface" clause; the SGP40 bus comes from the plan through
  `fixed_address()`, not the removed `FIXED_ADDRESSES`; readiness by poll (A.U25.45's `wait_until_serving`), never a
  1.0 s sleep (A.U8C.02's deferred sleeps closed "polled"); a refusal is `CeilingRefusedError` (A.U25.31). The two
  imports leave with them.
- **Resolved**: A.U24.47 (U24) rewrites `_scenario_bus_fault_degrades` in place, A.U25.46 (U25) moves it host-side —
  the scenario is not edited in U24; A.U24.47's content is written once, in the host harness (agent decision D10:
  avoids rewriting an in-DUT scenario that is deleted one unit later; nothing in U24 depends on it).
- **Unit**: U25
- **Depends**: M.TEST_HELP.029.
- **Blast carried by**: host-side rewrite → A.U25.46 with A.U24.47/A.U0.29/A.U20.28/A.U25.45 content → GAP-H2 (TWIN/SCR,
  `scripts/_digital_twin_scenarios.py`).
- **Kind**: test

## tests/_webserver_concurrency_scenarios.py

### M.TEST_HELP.032 Concurrency library: U24 keeps it running on the shared helpers
- **From**: A.U24.08, A.U24.79, A.U24.65 (1)/(4), A.U24.70, A.U24.06, A.U24.46, A.U10.30, A.U20.02, A.U20.06,
  A.U24.21 (seeding through the shared boot), A.U0.07, A.U10.37/A.U10.40 (H1), A.U5.04 (constructor objects, blast)
- **Site**: `tests/_webserver_concurrency_scenarios.py:55` `run_timed`, `:61` `_DEVICES`, `:70-81`
  `_PORT_BASE_BY_DEVICE`, `:97-102` `_boot()`, `:144` `_cancel`, `:266-273`/`:844-866` registration.
- **Change**: the mechanical stage only, so the file keeps working between U24 and its retirement in U25: harness
  imports (`run_timed`, `cancel`), the derived device set and port band (as M.TEST_HELP.029 (3)-(4)), `_boot()` →
  `boot_generated(device, …)` with `require_fresh()` at import, the scenario-count assert in `register_for_device()`,
  H1 renames as each lands. No scenario body changes.
- **Resolved**: every content action on this file (M.TEST_HELP.033's list) is written once, into the host harness —
  agent decision D10 (as M.TEST_HELP.031).
- **Unit**: U24 (H1 parts with their U10 actions; `watchdog=`/`run_setups` with U20).
- **Depends**: M.TEST_HELP.043, M.TEST_HELP.047, M.TEST_HELP.055, M.TEST_HELP.056.
- **Blast carried by**: — (the file and its six wrappers go in U25, M.TEST_HELP.033).
- **Kind**: test

### M.TEST_HELP.033 Retire the in-DUT concurrency library into the host harness
- **From**: A.U25.46, A.U25.74, A.U27.38 (runner), A.U27.23 (file leaves the twin pass list); content constituents
  travelling host-side: A.U24.34, A.U24.36, A.U24.37, A.U8C.04, A.U8C2.01, A.U8.18 (`:694`), A.U0.28 (`:482`), A.U0.35
  (`:753`), A.U19.21 (`:215-218`, `:569-571`), A.U5.05 (`:105`, `:518`), A.U25.31, A.U25.45 (`:128-140`, `:495`, `:532`,
  `:741`), A.U30.15 (`:861`), A.U36.004 (`:129-131`), A.U36.544 (`:251`, `:591`), A.U14.28 (F.7 row 1), A.U19.20
  (`:659` route set), A.U20.28 (plan reader), A.U8.23 (`:37` ignore), A.U25.24/A.U25.33/A.U25.43 (boot discipline),
  A.U24.65 (wrappers); hold: A.U11.24, A.U19.07, A.U19.08, A.U26.64, A.U35.29, A.S0930.18, A.SDEP.06, A.SDEP.16,
  A.SDEP.18, A.U5.04
- **Site**: the whole of `tests/_webserver_concurrency_scenarios.py` (866 lines) and the six
  `tests/test_digital_twin_webserver_concurrency_<device>.py` wrappers.
- **Change**: in U25 the file and its six wrappers are deleted; every scenario and helper (all 22) is rewritten in
  `scripts/_digital_twin_scenarios.py` against a booted twin process (`scripts/_twin_process.py`), DUT-side control
  through A.U25.74's `--test-…` flags. Each content constituent above lands in that rewrite (GAP-H2 lists them per
  scenario); none is applied to this file. No third `PER_DEVICE` wrapper is created (A.U24.65 vs A.U25.46: A.U25.46's
  outcome kept, as both actions state).
- **Resolved**: A.U24.34 vs A.U25.31 on a refused connection — A.U25.31's verified client text settles it (a refusal is
  `CeilingRefusedError`, an `OSError`; an `open_connection` failure propagates as `OSError`); A.U24.65 vs A.U25.46 on the
  wrappers — A.U25.46 kept (both name it); A.S0930.18's port block reference (`:71-77`) moves to its new home in
  `tests/_port_bands.py` (A.U24.70) — settled by A.U24.70.
- **Unit**: U25
- **Depends**: M.TEST_HELP.032; A.U25.46/A.U25.74 (host harness, flags).
- **Blast carried by**: host harness rewrite with every content item → GAP-H2 (TWIN/SCR); `scripts/test.sh` and
  `run_digital_twin_ci.sh` jobs → A.U27.38 (SCR); `digital_twin/typecheck.ini` `files` drops the file → A.U27.23
  (TOOL); SPEC citers of `tests/_webserver_concurrency_scenarios.py:193` (H.7.1) repoint to the harness → A.U36.532
  (SPEC); A.S0930.18's test cites the port table → A.U24.70 (TEST_UNIT).
- **Kind**: test

## tests/_sensortask_scenarios.py

The unit-tier (L1) per-device scenario library: 57 scenarios at HEAD, run per derived device through one
`PER_DEVICE` file after U24 (A.U24.65). Grouped by site area; each group is one merged change.

### M.TEST_HELP.034 Scenario library text: constants from source, current facts, renames
- **From**: A.U24.01 (`:27-31`), A.U24.67 (`:854`), A.U36.004 (`:860-862`), A.U0.35 (`:967`), A.U0.37 (`:501`),
  A.U0.39 (`:691`), A.U36.544 (`:216`, `:652`), A.U19.05 (`:1245`, `:1257`), A.U8.23 (`:22`), A.U9.03 (`:1068-1082`
  comment), A.U19.02 (`:1071-1073` → A.U9.03's), A.U2.13 (holds), A.U10.37/A.U10.38/A.U10.35/A.U10.40/A.U10.43/
  A.U10.44 (H1), A.U0.07 (H5: `:344-345`, `:384`, `:555-560`, `:575`, `:622`, `:636`, `:807-808`), A.U24.73,
  A.U36.038 (H6)
- **Site**: `tests/_sensortask_scenarios.py:1-3` (docstring), `:22` (`# type: ignore[import-not-found]`), `:27-31`
  (`_PHASE_*` mirrors), comments `:216`, `:501-503`, `:651-652`, `:691`, `:854`, `:860-862`, `:967`, `:1068-1082`,
  `:1245`, `:1257`; every function-level import; every `Any`.
- **Change**: (1) `_PHASE_STA_SEEKING`/`_PHASE_HOTSPOT` read through `_src_const.src_const("src/asy_wifi_service.py",
  "_PHASE_…")`, the three-line mirror comment gone. (2) `:22`'s ignore goes once Microdot's stub is vendored (A.U8.23).
  (3) Comments: `:216` "(Part L.3)" → "(Part L.2)", L.2 gaining "Instances of equal rank keep their TOML declaration
  order (`buildgen/graph.py:54-57`)"; `:652` "WP6 (SPECIFICATION.md Part D.9/G.2)" → "the boot batch's watchdog feed
  (SPECIFICATION.md A.7, G.2)"; `:501` "Owner requirement:" → "Owner requirement (owner, 2026-08-11):"; `:691` →
  "(owner, 2026-08-11: system-wide, no shared mutable value)"; `:860-862` → "# The implicit FRAM-wiring rule
  (SPECIFICATION.md A.7): every device's TOML declares [device.wiring].fram_target, / # so webserver's self.pr is
  FRAM-backed on every device, like conn/ntp/sysfunct. No device-level / # fram_target is covered at the codegen level
  instead."; `:967` → "unlike the accepted power-loss residual risk (owner, 2026-09-26; Part F.2)"; `:854` states the
  mechanism with no device name or count; `:1068-1082` → "a second command would find the first still queued and be
  refused"; `:1245`, `:1257` name `_StaticRoutes.serve()`. (4) Every function-level import moves to module level
  (H5); module names and keys follow H1 as each renaming action lands. (5) No `Any` (JSON alias, `_protocols`,
  `object`). (6) U36: D.15 order, `_register` the named import-time exception.
- **Resolved**: —
- **Unit**: U24 (stages: H1 with each U10 action; `:22` U8; `:501`/`:691`/`:967` U0; `:216`/`:652` U36; `:860` U36;
  `:1068-1082` U9; `:1245`/`:1257` U19).
- **Depends**: M.TEST_HELP.044.
- **Blast carried by**: SPEC L.2 sentence → A.U36.544 (SPEC).
- **Kind**: test

### M.TEST_HELP.035 Scenario infrastructure: shared boot, derived sets, strict bodies
- **From**: A.U24.79, A.U24.08, A.U24.43 (1)/(2), A.U24.65 (1)/(2), A.U24.22 (2), A.U24.21 (seeding), A.U24.46,
  A.U10.30, A.U24.60, A.U24.50 (1), A.U24.06, A.U20.02, A.U20.06, A.U11.10, A.U20.11 (`_all_loggers` via
  `get_loggers()`), A.U15.12/GAP-10 (SCD30 cfgmgr), A.U19.06 (`sock=`), A.S0930.37 (1) (`_dispatch_async`), A.U19.11
  (holds), A.U20.42 (holds), A.U24.09 (holds), A.U5.02/A.U5.04 (constructor blast), A.U18.10 (offline NTP config)
- **Site**: `tests/_sensortask_scenarios.py:41-42` `run()`, `:52-57` `status_body()`, `:62` `_DEVICES`, `:65-90`
  FRAM fakes and `fram_fake_class()`, `:84-87` `_wiring_plan()`, `:120-133` (`_OPTIONAL_INSTANCE_NAMES`, `_boot()`,
  `build()`), `:136-173` (`_device_of`, `_present_optional_instances`, `_has`, `_has_uart_link`), `:176-206`
  `_all_loggers()`, `:237-243` `_sensor_reader_owners()`, `:246-252` `_dispatch()`, `:1279-1294`
  `register_for_device()`.
- **Change**: (1) `run()` → `_async_harness.run`; every bounded wait is the caller's own bound. (2) `_DEVICES`,
  `_wiring_plan()` → `_twin_devices.generated_devices()`/`wiring_plan()`; `require_fresh()` at import. (3) FRAM:
  `_FakeMB85RS2MTA` goes; `fram_fake_for(device)` returns a constructor bound to `FakeMB85RS64V(size=…, rdid=…)` from
  `_FRAM_FAKE_BY_MAX_SIZE = {0x2000: (0x2000, <MB85RS64V RDID>), 0x40000: (0x40000, bytes([0x04, 0x7F, 0x48,
  0x03]))}` read off the plan's `max_size` (public: the boot probe imports it). (4) New public `seed_occupants(device)`:
  for every plan I2C bus, constructs the fake `machine.I2C(id, …)` (the per-id entry the product then reuses) and runs
  each occupant's catalog adapter `seed()` (which adds the address to `attached`); an occupant with no adapter fails
  with the catalog's actionable message. (5) `_boot(device, cfg_path=None, **kw)` → `seed_occupants(device)`, install
  the FRAM factory, `return await boot_generated(device, cfg_path=…, **kw)` — whose default `offline_ntp=True` writes
  `config_NTP.cfg` = `{"NTPHost": "192.0.2.1", "DNSFallback": ""}` into the cfg dir when absent (A.U18.10: L1 boots
  set it through the stored config, so no L1 run queries a public DNS server) (module and WDT; construction plus
  `run_setups()`); `build()` = `run(_boot(…))` and only ever called from synchronous scenario scope. (6) Owners and
  optional names derive from the plan (`plan["instances"]` drivers other than `uart_link`, plus `plan["uart"]`'s two
  variables, plus the mandatory services) — `_OPTIONAL_INSTANCE_NAMES` and the hand owner list go. (7) `_all_loggers()`
  = for each plan-derived owner in construction order, `owner.get_loggers()` (the fan-in `_collect_level_setters()`
  uses), so SCD30's RAM-only `cfgmgr.pr` and any new driver join with no edit; the "scd30 before sgp40 …" comment and
  `_has_uart_link()`'s "Only \"dev\" has it today" go (no device-set claim, G8/R01).
  (8) `_dispatch()` builds the request with `sock=(_NoopHolder(), _NoopHolder())` (a one-method `_Holder` fake) and is
  `run(_dispatch_async(…))`; `_dispatch_async(module, method, path, json_body=None)` returns `await
  app.dispatch_request(req)` for scenarios already inside one coroutine. (9) Every response body is parsed with
  `strict_loads()` (32 sites) and `status_body()` drains then strict-checks. (10) `if not _has(…): return` →
  `raise microtest.Skip("<device> declares no <x>")` everywhere (the "every real device has … today" comments go).
  (11) `register_for_device(device)` asserts the device is in the derived set, uses its `TmpScratch` key, and asserts
  the count of module-level `_scenario_*` functions equals `len(_SCENARIOS)`.
- **Resolved**: A.U24.79's `boot_generated()` replaces the three libraries' `_boot()` bodies, while A.U24.43 (2)
  requires seeding before `setup()`; the per-id fake bus (M.TEST_HELP.013) lets seeding precede construction, so the
  shared helper stays generic and the unit seeding stays here (agent decision D12). A.U20.11 asks the FRAM check to read
  `get_loggers()`; `_all_loggers()` is rebuilt on the same fan-in so the two cannot disagree (agent decision D13).
- **Unit**: U24 (stages: `sock=` with A.U19.06 in U19; `watchdog=`/`run_setups()` with A.U20.02/A.U20.06/A.U11.10 in
  U20; `_dispatch_async` with A.S0930.37).
- **Depends**: M.TEST_HELP.008, M.TEST_HELP.022, M.TEST_HELP.026, M.TEST_HELP.043, M.TEST_HELP.046, M.TEST_HELP.047,
  M.TEST_HELP.055.
- **Blast carried by**: the six `tests/test_sensortask_<device>.py` → `tests/test_sensortask.py` (`PER_DEVICE = True`,
  `TEST_DEVICE`) → A.U24.65 (TEST_UNIT); `scripts/test.sh` expansion → A.U24.65 (3) (SCR); boot probe imports
  `fram_fake_for`/`seed_occupants` → M.TEST_HELP.028.
- **Kind**: test

### M.TEST_HELP.036 FRAM layout scenarios read the real chunks, derive every expectation
- **From**: A.U16.02 (1), A.U20.11, A.U15.12/GAP-10 (AC_NOTES 13, GAP-G7), A.U5.07 (chunk order), A.U16.03, A.U16.13
  (holds), A.U16.17, A.U16.R02, A.U16.R03, A.U0.37 (`:501`, M.TEST_HELP.034), A.U24.22, A.S0930.21 (holds)
- **Site**: `tests/_sensortask_scenarios.py:210-234` `_expected_fram_chunk_calls()`, `:377-417` (layout scenario,
  `method-assign` wraps `:388-415`), `:419-475` (`fram_chunks_are_all_successfully_allocated_not_out_of_memory`),
  `:480-489` (only-FRAM-in-memory scenario), `:490-545` (`_DeadFramChip`, never-insists scenario).
- **Change**: (1) `_expected_fram_chunk_owners(module)` replaces the call list: owner names in construction order
  (from `sensortask_<device>_expected.json`'s construction part), each constructed module contributing its logger,
  then `CFGMGR_<NAME>` only when its config log is FRAM-backed (`type(owner)._CFG_LOG_FRAM`), SGP40's backup as
  `"SGP40_BACKUP"`, `"WEBSERVER"` last — so the NeoPixel-before-WiFi order of A.U5.07 and SCD30's RAM-only config log
  need no edit (agent decision D7: A.U16.02's hand-ordered list is already wrong after A.U5.07). (2) Layout scenario renamed `fram_chunk_layout_is_contiguous_deterministic_and_in_owner_order`: the
  chunks are every `PrintLogHistoryStore.fram` of `_all_loggers(module)` plus each SGP40 `ts_storage`; sorted by base
  address the first starts at 0, each next at the previous plus `2 * (size + crc.length() + 2)`, the last ends at
  `module.fram.allocated_size`, owner names in address order equal (1), and a second `build()` yields the identical
  `(name, base, size)` list; the two `method-assign` wraps go. (3) Allocation scenario: reads
  `expected_facts()["fram_wired"]` (from the expected JSON) and, for every named module, asserts each logger of
  `get_loggers()` has `pr.fram is not None` except a config logger whose class sets `_CFG_LOG_FRAM = False` (must be
  `None`), and every unnamed module only `fram is None`; SGP40 `ts_storage is not None` stays explicit; the hand list
  and `_has()` gates go. (4) The in-memory-only scenario allows exactly the FRAM manager's own log and the RAM-only
  config logs derived in (3). (5) New `first_boot_after_a_reflash_reinitialises_every_chunk_without_flood` (A.U16.03's
  body). (6) Dead-chip scenario renamed `a_declared_dead_fram_chip_escalates_to_a_reboot`: keeps its construction and
  RAM-logging assertions, sees three RDID cycles in the fake's log (A.U16.R02), `module.fram.get_task_starters()` has
  one starter, and driving `start_tasks(…, task_names=…)` then `supervise_tasks()` with `asyncio.sleep` shortened from
  outside arms the reboot with the task-budget reset reason, catching `machine.SimulatedRebootError` from the fake
  timer; its comment keeps the owner requirement with its tag.
- **Resolved**: GAP-10 / GAP-G7 / AC_NOTES 13 — A.U15.12's "two chunks" and A.U20.11's "every logger FRAM-backed" are
  superseded for SCD30's config log by the RAM-only ruling; (1) and (3) derive the exemption from the class attribute,
  never from a name (AC_NOTES 13: "derive, not name").
- **Unit**: U24 (stages: (6) with A.U16.17/A.U16.R02 in U16; the owner list with A.U16.02 in U16; `fram_wired` with
  A.U20.11 in U20; SCD30 exemption with A.U15.12/GAP-G7 in U15).
- **Depends**: M.TEST_HELP.035, M.TEST_HELP.022.
- **Blast carried by**: `expected_facts()["fram_wired"]` and the expected JSON → A.U20.07/A.U20.11 (GEN, SCR); L0
  `tests_scripts/test_fram_chunk_owner_sites.py` → A.U16.02 (2) (TSC); SPEC A.7 chunk list naming `CFGMGR_SCD30` RAM-only
  → GAP-G7 (SPEC).
- **Kind**: test

### M.TEST_HELP.037 Boot scenarios: setup batch, boot sequence, feeds, stretches
- **From**: A.U24.79 (`:651-677`), A.U10.10 (`:550-…`), A.U11.10, A.U20.07 (L1), A.U10.07 (3), A.U31.03, A.U10.08
  (L1 scan budget), A.U11.07 (setup-phase code), A.U20.38 (3), A.U11.34, A.U9.10 (c), A.U10.19 (L1 inventory),
  A.U11.35 (holds), A.U31.01 (holds), A.U31.17 (holds)
- **Site**: `tests/_sensortask_scenarios.py:552-650` (setup batch order scenario), `:651-677`
  (`_scenario_boot_feeds_the_watchdog`); new scenarios.
- **Change**: (1) `setup_batch_runs_every_unit_in_the_collected_order` (renamed from the
  `…sysfunct_then_fram_then_conn…` name): records `run_setups()`'s units through the recorder of
  `tests/_boot_recorder.py` and asserts they equal `_collect_setups()`'s order, which now includes scd30, neopixel and
  webserver; the per-class function-level imports go. (2) Boot feeds: asserts `module.sysfunct.watchdog is wdt` and
  `wdt.feed_count` rises by one per setup unit (the WP label goes, M.TEST_HELP.034). (3) New
  `boot_sequence_matches_the_generated_expectation` (A.U20.07's L1): `main()` run until `supervise_tasks()` is entered
  (the recorder raises its stop exception there), the list equals the expected JSON's `boot_sequence`. (4) New unfed-
  stretch scenario (A.U10.07 (3)) and setup-unit no-wait scenario (A.U31.03), both on `run_setups()` and the start
  lists, fake clock on `asy_system_service.time`. (5) New supervisor scan-budget scenario (A.U10.08): k task deaths
  before one round; persisted writes counted by the FRAM fake's `write_transactions` (M.TEST_HELP.022) ≤ k and one
  `_TASK_CHECK_TIME` sleep. (6) New setup-failure scenario (A.U11.07): one module's `setup()` replaced to raise stops the
  boot and the next `begin_boot()` reads 12. (7) New dropped-logger scenario (A.U20.38 (3)), every-measurement-starts-
  `None` scenario (A.U11.34), timer-starter seam check (A.U9.10 (c)), and the per-device task inventory fan-in (A.U10.19).
- **Resolved**: —
- **Unit**: U24 (each new scenario lands with its constituent: A.U10.07/A.U10.08/A.U10.19 U10, A.U11.07/A.U11.10/A.U11.34
  U11, A.U20.07/A.U20.38 U20, A.U31.03 U31; (2) U24).
- **Depends**: M.TEST_HELP.035, M.TEST_HELP.061.
- **Blast carried by**: Part N rows `boot.unfed_stretch_*`/`boot.setup_unit_stretch_ms` → A.U10.07/A.U31.03 (SPEC);
  L0 feed-site check → A.U10.08 (TSC); expected JSON → A.U20.07 (GEN).
- **Kind**: test

### M.TEST_HELP.038 Starter scenarios: trigger lists, real sequencer, real supervisor
- **From**: A.U10.12 (`:774-796`), A.U10.13, A.U11.39, A.U24.43 (3), A.U24.50 (2), A.U32.06/GAP-G5, A.U20.06, A.U16.R03
  (task count), A.U5.08 (`_collect_level_setters` holds)
- **Site**: `tests/_sensortask_scenarios.py:750-796` (section comment `:750-753`, the two collect scenarios), `:804-841`
  (fake `sysfunct` methods in the main-call-order scenario).
- **Change**: (1) Collect scenarios cover task, timer and trigger starters (`_collect_trigger_starters()`); before
  collecting, every owner's `get_timer_starters`/`get_trigger_starters` is wrapped by a counting wrapper (restored in
  `finally`) and each wrapper ran exactly once; FRAM's starter is present on every FRAM device. (2) Task names:
  `_collect_task_names()` equals the starters in length, names unique; every direct `start_tasks()` call passes
  `task_names=module._collect_task_names()`. (3) The section comment `:750-753` → "# Task/timer starter collection and
  the real supervisor, driven under the tracked harness with a fake clock." (4) The main-call-order scenario's fake
  `sysfunct` methods follow the split API (`run_setups`, `start_tasks`, `start_timers(triggers, timers)`,
  `supervise_tasks`) and assert `main()`'s order (setups → tasks → timers → force sync → supervise). (5) New
  `read_triggers_follow_the_stagger_on_the_real_sequencer` (A.U10.13 and A.U11.39 merged): the real
  `start_timers(_collect_trigger_starters(), _collect_timer_starters())` driven by `Timer.clock_ms` and
  `_sequencer_timer.trigger()`; offsets equal `k·slot`, same-bus pairs furthest apart. (6) New
  `every_task_starter_runs_under_the_real_supervisor` (A.U24.43 (3)): `start_tasks()` then one `supervise_tasks()` check
  under `run_timed` with the fake clock over one `_TASK_CHECK_TIME`; each owner's started task is alive.
- **Resolved**: A.U10.13 (U10) and A.U11.39 (U11) each add a per-device real-sequencer scenario under a fake clock;
  A.U11.39's records `Timer.clock_ms` per arm, A.U10.13's patches `system_service.time` — one scenario, A.U11.39's
  mechanism (it needs no module patch), A.U10.13's assertions; `tests_scripts/test_timer_stagger_no_coincidence.py`
  goes once (agent decision D14).
- **Unit**: U32 (task names); stages U10 (trigger collector, (1), (5) assertions), U11 ((5) mechanism), U20 ((4)), U24
  ((6)).
- **Depends**: M.TEST_HELP.035, M.TEST_HELP.020.
- **Blast carried by**: retired `tests_scripts/test_timer_stagger_no_coincidence.py` → A.U10.13 (TSC); generated
  collectors → A.U10.12/A.U32.06 (GEN).
- **Kind**: test

### M.TEST_HELP.039 Debug-level scenarios go through the REST setting
- **From**: GAP-G3 (M.SRC_CORE.008/.017/.018), A.U11.12, A.U11.15, A.U11.19 (holds), A.U5.08, A.U0.39 (`:691`)
- **Site**: `tests/_sensortask_scenarios.py:689-747` (section comment, four scenarios), `:933-940` (DebugLevel PUT).
- **Change**: levels are the documented `DebugLevel` numbers 0-5 and a logger's level is read from its public
  `pr.level` (the `PrintLog.get_level()`/`level_*()` accessors are gone). (1) Collect-level-setters: each setter called
  with 4 sets that logger's `pr.level` to 4. (2) Seed scenario: `build(device, debug=2)` with no file → `GET /system`
  `DebugLevel` 0 and every `pr.level == 0`. (3) Set scenario: `PUT /system {"DebugLevel": 1}` → "Valid"; every logger
  reads 1 (no `set_debug_level()` call). (4) Survives-reboot: the PUT, then a second `build()` over the same cfg dir →
  `GET /system` 1 and every logger 1. (5) `:933-940` asserts `GET /system`'s `DebugLevel` and `conn.pr.level`, not
  `get_debug_level()`.
- **Resolved**: GAP-G3 (the getters/setter removed by M.SRC_CORE) — carried here.
- **Unit**: U11 (with M.SRC_CORE.017/.018 and A.U11.15).
- **Depends**: M.TEST_HELP.035.
- **Blast carried by**: — 
- **Kind**: test

### M.TEST_HELP.040 System-command scenarios run as one tracked coroutine each
- **From**: A.U11.03, A.U11.04, A.U10.15, A.S0930.11 (holds), A.S0930.26, A.S0930.37, A.U11.31, A.U17.19 (holds),
  A.U19.01, A.U24.17 (reset raises), A.U0.35 (`:967`)
- **Site**: `tests/_sensortask_scenarios.py:953-984` (reboot arms the timer, reboot flushes a pending write, invalid
  command), `:1146-1179` (ResetErrors); new scenarios.
- **Change**: a command scenario is one coroutine driven by one `run()` from synchronous scope: `module, wdt = await
  boot_generated(device, …)`, `await sysfunct.start_tasks(…, task_names=…)`, `sup = create_task(sysfunct.supervise_tasks())`,
  `await _dispatch_async(…)`, `await sysfunct._shutdown_task`, the fake reset timer's `trigger()` inside `try … except
  machine.SimulatedResetError` (or `SimulatedBootloaderEntryError`), `sleep(0)` until the reset task is done, then
  `sup` cancelled and awaited — never `build()`/`_dispatch()` inside it. (1) Reboot: "Valid"; after the trigger
  `machine.reset_count == before + 1` and the reset cause reads WDT. (2) Reboot flushes: a `PUT /networking
  {"LedWifiOn": …}` before the trigger is on disk after it; a write after the trigger is refused. (3) Invalid
  command "Invalid". (4) New `resetconfig`, `erasefram`, bootloader and reboot scenarios at both GC stages (A.S0930.26/
  A.S0930.37's bodies). (5) ResetErrors scenarios assert `result["ResetErrors"] == "Valid"`. (6) New: `PUT /networking
  {"NoSuchKey": 1}` → `"Invalid"` (A.U19.01).
- **Resolved**: —
- **Unit**: U24 (stages with A.U11.03/A.U11.04 U11, A.S0930.* their unit, A.U19.01 U19).
- **Depends**: M.TEST_HELP.035, M.TEST_HELP.011.
- **Blast carried by**: —
- **Kind**: test

### M.TEST_HELP.041 REST scenarios assert what their names claim
- **From**: A.U24.32 (1)/(2), A.U4.04, A.U19.02, A.U9.03, A.U10.40 (keys), A.U18.21, A.U18.33, A.U18.38, A.U18.39,
  A.U5.07, A.U11.05, A.U11.08, A.U19.10, A.U23.22, A.U32.06, A.U6.21, A.U24.63, A.U10.27, A.U19.13, A.U15.12 (holds),
  A.U20.16 (holds), A.U23.33 (holds), A.U19.11 (holds)
- **Site**: `tests/_sensortask_scenarios.py:869-950` (measurements/sensors/networking/NTP/GMT scenarios), `:986-1093`
  (LED command, PauseTime, WarnCO2), `:1102-1142` (status keys, build info), `:1185-1262` (hotspot); new scenarios.
- **Change**: (1) SCD30 PUT: after `PUT /sensors {"SCD30": {"MeasInterval": 4}}` (A.U10.40 key), `GET /sensors` shows 4
  and the fake bus log holds the SCD30 set-interval command (the fake answers the chip-store snapshot, A.U4.04). (2) LED
  command: the scenario named for a log asserts it through `tests/_recording_print.py`; the seven malformed payloads
  answer `"Invalid"` (A.U19.02); new back-to-back case: first `"Valid"`, second `"Failed"` within 100 ms
  (A.U9.03). (3) Networking: new mask-string PUT (`PW`, `HotspotPW` "********" stored verbatim, GET masked; A.U18.39);
  new `HotspotPW` PUT configures the next hotspot start (A.U18.38); NTP settings change clears `Synced` (A.U18.21);
  status snapshot with `wifi_mode_lock` held answers `Connected: true` and `IPv4 == IP`, AP mode `RSSI` null with no
  rssi query (A.U18.33); WiFi LED construction passes `led_pin` (A.U5.07). (4) Status keys: `ResetReason`, `MemFree`
  (int), `HTTPDropped`, `WifiTS`, `UnixTime`, `LastTaskEnd`, and `UtcTime is None` before sync; new scenarios for
  `UtcTime`/`UnixTime` after `set_utc_valid(True)`, `HTTPDropped` rising after a forced refusal. (5) Build info equals
  the generated module's embedded values via `src_const` (A.U24.63). (6) New non-finite scenario: every float field and
  float config value set to NaN/±inf in turn, every GET route strict-parses with `null` there (A.U10.27). (7) New
  serving-demand scenario (A.U19.13's L1). Keys follow A.U10.40's map as it lands.
- **Resolved**: A.U24.32's "SCD30 PUT path" and A.U4.04's chip-store PUT co-land on `:898-905` — merged as (1) (A.U4.04's
  path, A.U24.32's assertion).
- **Unit**: U24 (stages with each constituent's unit: U4, U5, U6, U9, U10, U11, U18, U19, U23, U32).
- **Depends**: M.TEST_HELP.035, M.TEST_HELP.050.
- **Blast carried by**: A.U6.22 status-field parity (definitions both ways) → GEN/WEB.
- **Kind**: test

### M.TEST_HELP.042 Robustness scenarios under a driven clock
- **From**: A.U35.28 (L1), A.U35.30, A.U35.33, A.U35.34, A.U35.03 (review), A.U35.10 (`DrivenTime`)
- **Site**: `tests/_sensortask_scenarios.py` (new scenarios, per derived device).
- **Change**: (1) Fault-storm log rate (A.U35.28): persisted writes counted by the FRAM fake's counters stay within the
  `rate.persisted_log` row. (2) Four planted-failure scenarios (A.U35.30): an exception escaping the supervisor, a
  cancelled `main()`, and the two escalation cases — each after two supervisor feeds, then every live fake Timer
  triggered and every Pin IRQ fired, `watchdog.feed_count` frozen at its value at the planted event (`feed_times`
  read for order); a reset reached inside is caught as `machine.SimulatedRebootError`. (3)
  `forty_days_of_uptime_keep_every_invariant` (A.U35.33) with `DrivenTime.jump()`. (4)
  `dropped_one_second_wake_ups_never_skew_elapsed_values` (A.U35.34) using `Timer.drop()`.
- **Resolved**: —
- **Unit**: U35
- **Depends**: M.TEST_HELP.035, M.TEST_HELP.065 (`DrivenTime`).
- **Blast carried by**: `audit/b3/review.md` rows → A.U35.03 (audit artefact).
- **Kind**: test

## New helper files

Each is a new `tests/_*.py` module (MicroPython-runnable unless noted), with a ≤ 3-line docstring stating its job, no
`Any`, public names only for what other modules import, and D.15 order (H4-H6).

### M.TEST_HELP.043 Create the one async harness with its two guarantees
- **From**: A.U24.08, A.U24.73 (`Coroutine` alias), A.U35.48 (caller), A.U14.18 (rule it enforces)
- **Site**: new `tests/_async_harness.py`.
- **Change**: `run(coro, limit_s: float | None = None)`, `run_timed(coro, timeout_s)`, `cancel(task)`,
  `cancel_all(tasks)`, and the alias `CoroutineOf = Coroutine[object, object, T]` (under `TYPE_CHECKING`). `run`/
  `run_timed`: (a) refuse to start inside a running loop — `if asyncio.core.cur_task is not None: raise
  RuntimeError("run() called from inside a coroutine - build the fixture in the test's synchronous scope")` (`cur_task`
  is set during `run_until_complete()`, `extmod/asyncio/core.py:167, 181, 200`), so the nested `asyncio.run()` that
  segfaults the Unix port raises instead; (b) wrap `asyncio.create_task` and `asyncio.core.create_task` for the call
  (`core.py:266-267`), record every task, and in a `finally` cancel and await every unfinished one in one extra
  `run_until_complete` round, then restore both names. `run(coro, limit_s)` wraps `asyncio.wait_for(coro, limit_s)`
  when a bound is given. Docstring: "One way to drive a coroutine from a synchronous test: refuses to nest inside a
  running loop and cancels every task the call created. A task parked on an Event or on another task is on neither
  scheduler queue and is not seen here; microtest's after-each check is the backstop."
- **Resolved**: —
- **Unit**: U24
- **Depends**: M.TEST_HELP.002 (after-each scheduler check).
- **Blast carried by**: the ~50 file-local `run()`/`run_timed()`/`_cancel*` copies → A.U24.08 (TEST_UNIT, TWIN), the
  helper-library copies → M.TEST_HELP.023/.029/.032/.035; CLAUDE.md hang/segfault bullets → A.U36.546 (DOCS).
- **Kind**: test

### M.TEST_HELP.044 Create the src-constant reader
- **From**: A.U24.01 (1)/(3), A.U24.02 (consumer), A.U24.63 (consumer)
- **Site**: new `tests/_src_const.py`.
- **Change**: `src_consts(path) -> dict[str, object]` (cached per path) evaluates every single-line `<_NAME> =
  const(<expr>)` in order with the names bound so far; `src_const(path, name)` raises `KeyError(f"{name} is not a
  const() in {path}")`; `NTP_EPOCH_DELTA = 2208988800  # RFC 5905 section 6, 1900 -> 1970`. Docstring as A.U24.01
  (1) (cites `py/parse.c:857`, v1.29.0). `re`-free.
- **Resolved**: —
- **Unit**: U24
- **Depends**: —
- **Blast carried by**: the mirrors in 17 test files → A.U24.01 (2) (TEST_UNIT, TWIN); L0 mirror check → A.U24.02
  (TSC); scenario uses → M.TEST_HELP.034/.041.
- **Kind**: test

### M.TEST_HELP.045 Create the shared error-catalog lookup
- **From**: A.U2.03, A.U24.02 (rule (c))
- **Site**: new `tests/_error_codes.py` (runs under MicroPython and host CPython).
- **Change**: `code(kind: str, name: str) -> int` (`kind` "E"/"W") reads `buildgen/error_catalog.json` once (path
  relative to its own file, `json` only) and raises `KeyError` for an unknown or retired name.
- **Resolved**: —
- **Unit**: U2
- **Depends**: A.U2.01 (catalog).
- **Blast carried by**: product-code expectations in `tests/` → A.U2.05-A.U2.20 (TEST_UNIT); `tests_hardware/
  error_log_helpers.py` imports it → A.U2.03 (HW_BENCH); `scripts/_digital_twin_ci_suite.py` → A.U2.03 (SCR).
- **Kind**: test

### M.TEST_HELP.046 Create the generated-tree freshness guard
- **From**: A.U24.46 (2)
- **Site**: new `tests/_generated_tree.py`.
- **Change**: `require_fresh()` (MicroPython `os.stat()[8]`, `os.listdir`): `build/generated_src/.inputs_stamp.json`
  exists, its path set equals the current input set and no input is newer than recorded; else `RuntimeError(
  "build/generated_src/ is missing or stale - run: uv run scripts/_generate_sensortask_modules.py")`.
- **Resolved**: —
- **Unit**: U24
- **Depends**: the stamp writer → A.U24.46 (1) (SCR).
- **Blast carried by**: callers (three scenario libraries, the probe, `tests/test_bus_hazard_generated.py`,
  `tests/test_digital_twin_run_generic_integration.py`) → M.TEST_HELP.028/.029/.032/.035, A.U24.46 (TEST_UNIT, TWIN).
- **Kind**: test

### M.TEST_HELP.047 Create the generated-module loader and boot helper
- **From**: A.U10.30, A.U24.79, A.U18.10/A.U25.33 (offline NTP), A.U20.02, A.U20.06, A.U11.10
- **Site**: new `tests/_generated_module.py`.
- **Change**: `load_generated(device) -> module` (the one F.1-named `tests/` load by a data-derived name);
  `write_offline_ntp_config(cfg_dir)` writes `config_NTP.cfg` = `{"NTPHost": "192.0.2.1", "DNSFallback": ""}` only when
  absent (RFC 5737 TEST-NET-1; the product's flat JSON format); `async boot_generated(device, *, offline_ntp=True,
  **kwargs) -> tuple[module, WDT]`: constructs one `machine.WDT` with the timeout parsed from
  `build/generated_src/<device>_boot.py`'s `watchdog = WDT(timeout=<n>)` line (never a copied 8000), writes the offline
  config into `kwargs["cfg_path"]` when asked, `await module.build_system(watchdog=wdt, **kwargs)`, `await
  module.sysfunct.run_setups(module._collect_setups())`, returns both.
- **Resolved**: A.U25.33 places `write_offline_ntp_config()` in the twin runner (U25), but unit-tier boots need it from
  U20 on (A.U20.07's L1 runs `main()` through the first force sync, A.U18.10: "L1 boots set it through the stored
  config") — the one implementation is born here in U20 (agent decision D16); the twin runner imports it (GAP-H3).
- **Unit**: U24 (stage U10: `load_generated()`; stage U20: `boot_generated()` and the offline write, with the boot entry
  and `run_setups()`).
- **Depends**: M.TEST_HELP.046.
- **Blast carried by**: the seven `__import__(f"sensortask_{device}")` sites → M.TEST_HELP.028/.029/.032/.035, A.U10.30
  (TEST_UNIT); SPEC F.1 named list → A.U10.30 (SPEC); twin runner → GAP-H3 (TWIN).
- **Kind**: test

### M.TEST_HELP.048 Create the shared machine-fake contract suite
- **From**: A.U24.17, A.U25.02 (twin half), A.S0930.24 (`feed_times`), A.U24.78/A.U24.82 (`pending()`), A.U24.20
- **Site**: new `tests/_machine_contract.py`.
- **Change**: checks taking a module object (or, for faults, a backend factory `make_injector() -> (inject, trigger)`):
  `check_pin_constants`, `check_pin_pull_semantics`, `check_pin_defaults`, `check_wdt_timeout_bounds` (8388 cap, 8000
  accepted), `check_wdt_feed_times`, `check_reset_never_returns`, `check_irq_edge_values`, `check_scan_never_raises`,
  `check_inject_fault_fifo` (fresh objects, FIFO, `times=`, `match`, `pending`), `check_readfrom_mem_into_delegates`,
  `check_i2c_state_survives_reconstruction`; `ALL_CHECKS` plus a completeness test (A.U24.06's pattern).
- **Resolved**: —
- **Unit**: U24
- **Depends**: M.TEST_HELP.011-016.
- **Blast carried by**: runners `tests/test_fakes.py` (renamed by A.U24.16) → A.U24.17 (TEST_UNIT) and
  `tests/test_digital_twin_machine.py` → A.U24.17 (TWIN).
- **Kind**: test

### M.TEST_HELP.049 Create the shared mem-backup contract
- **From**: A.U25.08, A.U25.01 (cites it), A.U11.07
- **Site**: new `tests/_mem_backup_contract.py`.
- **Change**: checks both tiers run: region sizes 4 and 3 words, the same object on every call, `-1` returns the tuple
  of both, `2`/`-2` raise `ValueError("invalid region")`, `power_on()` clears both regions and sets `PWRON_RESET`, a
  `reset()` leaves the regions and reports `WDT_RESET`; `ALL_CHECKS` with its completeness test.
- **Resolved**: kept as its own module beside `_machine_contract.py` (both actions create one; the twin fidelity row
  cites this path, A.U25.01) — agent decision D15 (no fold, no extra blast).
- **Unit**: U25 (stage U11 for the unit half's L1 cases, A.U11.07, which the contract later absorbs).
- **Depends**: M.TEST_HELP.011.
- **Blast carried by**: runners → A.U25.08 (TWIN, TEST_UNIT).
- **Kind**: test

### M.TEST_HELP.050 Create the recording-print wrapper
- **From**: A.U24.32
- **Site**: new `tests/_recording_print.py`.
- **Change**: `record_prints(pr)` wraps a `PrintLog` instance's `err/wrn/one/evt/all` from outside, recording `(level,
  args)` while still printing; returns the record list; a context manager restores the methods.
- **Resolved**: —
- **Unit**: U24
- **Depends**: —
- **Blast carried by**: `tests/test_asy_wifi_service.py`, `tests/test_system_service.py`, `tests/test_asy_bmp3xx_driver.py`
  renamed tests → A.U24.32 (TEST_UNIT); LED scenario → M.TEST_HELP.041.
- **Kind**: test

### M.TEST_HELP.051 Create the boundary protocols for typed fakes
- **From**: A.U24.73
- **Site**: new `tests/_protocols.py` (type-checking only; empty at run time).
- **Change**: under `TYPE_CHECKING`: `I2CLike`, `UARTLike`, `WLANLike`, `WriterLike` `Protocol`s, one per boundary the
  fakes stand in for, each listing exactly the methods the product calls.
- **Resolved**: —
- **Unit**: U24
- **Depends**: —
- **Blast carried by**: per-file `Any` removal and ANN401 exemptions → A.U24.73 (TEST_UNIT, TOOL).
- **Kind**: test

### M.TEST_HELP.052 Create the one fast async sleep double
- **From**: A.U24.49, A.U35.10 (sits beside it), A.U31.09/A.U31.14/A.U31.17 (`sleep_ms`, via M_SRC_SENS)
- **Site**: new `tests/_fast_sleep.py`.
- **Change**: `FastAsyncSleep` — the union of the ten file-local variants' behaviour (records every requested delay,
  returns after `sleep(0)`), patching both `asyncio.sleep` and `asyncio.sleep_ms`; a parameter for the one behaviour
  difference among the copies (whether a recorded delay is also counted per caller).
- **Resolved**: —
- **Unit**: U24
- **Depends**: —
- **Blast carried by**: the ten copies → A.U24.49 (TEST_UNIT).
- **Kind**: test

### M.TEST_HELP.053 Create the timer-arm failure context
- **From**: A.U24.49
- **Site**: new `tests/_fake_timer_arm.py`.
- **Change**: `RaiseOnArm(exc=OSError)` sets `machine.Timer.raise_on_arm`/`raise_on_arm_exc` and restores them in
  `__exit__`.
- **Resolved**: —
- **Unit**: U24
- **Depends**: M.TEST_HELP.020.
- **Blast carried by**: seven `_RaiseOnArm` copies → A.U24.49 (TEST_UNIT).
- **Kind**: test

### M.TEST_HELP.054 Create the shared fake time sources
- **From**: A.U24.49
- **Site**: new `tests/_fake_time.py`.
- **Change**: `FakeTime`, `OverflowingTime`, `tick()` — one shape each, a parameter where the copies differed.
- **Resolved**: —
- **Unit**: U24
- **Depends**: —
- **Blast carried by**: the five notification-test copies and `_OverflowingTime`/`_tick` copies → A.U24.49 (TEST_UNIT).
- **Kind**: test

### M.TEST_HELP.055 Create the derived device-set helper
- **From**: A.U24.65 (1), A.U25.25 (2), A.U25.48 (`device_with_shared_bus`), A.U36.015/A.U36.016 (cite it)
- **Site**: new `tests/_twin_devices.py`.
- **Change**: `generated_devices() -> list[str]` (sorted stems of `build/generated_src/sensortask_*_wiring_plan.json`,
  asserted non-empty), `wiring_plan(device) -> dict`, `device_with(driver) -> str`, `device_with_shared_bus(a, b) ->
  str`; each raises with the device set it searched when nothing matches.
- **Resolved**: A.U24.65 and A.U25.25 each create a derived-device helper and both say "one helper" — merged here at U24
  (A.U24.65 lands first), U25 adding the two property lookups.
- **Unit**: U24 (stage U25: `device_with*`).
- **Depends**: —
- **Blast carried by**: twin tests' device choice → A.U25.48 (TWIN); SPEC C.8/E.2.1 cite the module → A.U36.015/A.U36.016
  (SPEC).
- **Kind**: test

### M.TEST_HELP.056 Create the one port-band table
- **From**: A.U24.70, A.S0930.18 (port block)
- **Site**: new `tests/_port_bands.py`.
- **Change**: `BANDS = {"<owner>": (first, last, "tcp"|"udp")}` — disjoint rows below 32768, fixed rows for the JS
  twins, the cross-browser smoke, the CI suite's 18080, `unix_port_poll_prewarm.py`'s scan band and the inline 19099;
  `PortAllocator(owner)` (raises `AssertionError(f"{owner} ran past its port band {first}-{last}")`);
  `band_for_device(owner, device)` splits a band evenly over `generated_devices()`; an `EADDRINUSE` in a user re-raises
  "port <n> (band <owner>) is taken".
- **Resolved**: —
- **Unit**: U24
- **Depends**: M.TEST_HELP.055.
- **Blast carried by**: twelve allocators → A.U24.70 (TEST_UNIT, TWIN); L0 `tests_scripts/test_port_bands.py` and SPEC
  E.1 → A.U24.70 (TSC, SPEC).
- **Kind**: test

### M.TEST_HELP.057 Create the shared FRAM manager builder
- **From**: A.U24.49; M_TEST_UNIT's gap (rebuild over an existing chip)
- **Site**: new `tests/_fram_builders.py`.
- **Change**: `make_fram_manager(chip=None, *, size=0x2000, …)` builds a `FRAMManager` over a fresh `FakeMB85RS64V` or,
  when `chip` is given, over that existing chip (a simulated reboot keeps the memory).
- **Resolved**: the TEST_UNIT merge needs the rebuild form (its bmp3xx and FRAM-manager merges) — added as the `chip=`
  parameter.
- **Unit**: U24
- **Depends**: M.TEST_HELP.022.
- **Blast carried by**: eight `make_fram_manager`/`make_manager` copies → A.U24.49 (TEST_UNIT).
- **Kind**: test

### M.TEST_HELP.058 Create the NTP frame builder and fake server
- **From**: A.U24.49, A.U24.76
- **Site**: new `tests/_ntp_frames.py`.
- **Change**: `make_ntp_reply(…)` (with `_src_const.NTP_EPOCH_DELTA`) and one public `FakeNtpServer`.
- **Resolved**: —
- **Unit**: U24
- **Depends**: M.TEST_HELP.044.
- **Blast carried by**: three `make_ntp_reply`/`FakeNtpServer` copies → A.U24.49/A.U24.76 (TEST_UNIT).
- **Kind**: test

### M.TEST_HELP.059 Create the recording fixed random source
- **From**: A.U24.30
- **Site**: new `tests/_twin_random.py`.
- **Change**: `FixedRandom` returning its fixed value and recording every `uniform(a, b)` as `(a, b)` in `calls`.
- **Resolved**: —
- **Unit**: U24
- **Depends**: —
- **Blast carried by**: five twin-test copies and the two override tests → A.U24.30 (TWIN).
- **Kind**: test

### M.TEST_HELP.060 Create the twin readiness polls
- **From**: A.U25.45
- **Site**: new `tests/_twin_readiness.py`.
- **Change**: `async wait_until_serving(module, host, port)` (probe `fetch(read_body=False)` until 200, retrying every
  50 ms on `CeilingRefusedError`/connection errors, deadline a tunable) then `await drained(module)`; `drained()` moved
  from the concurrency library; `wait_for_value(read, expected, limit_ms)` for the admission and init polls.
- **Resolved**: —
- **Unit**: U25
- **Depends**: —
- **Blast carried by**: the 13 sleep sites → A.U25.45 (TWIN; the concurrency library's sites travel host-side with it,
  GAP-H2).
- **Kind**: test

### M.TEST_HELP.061 Create the boot-sequence recorder
- **From**: A.U20.07 (L1 recorder), A.U25.47 (imports it), A.U10.10 (setup order)
- **Site**: new `tests/_boot_recorder.py`.
- **Change**: `BootRecorder(module)`: wraps from outside the real `SystemService` methods (`run_setups`, `start_tasks`,
  `start_timers`, `supervise_tasks`, `boot_phase`) and every instance's `setup`, appending `(kind, name)` entries; entering
  `supervise_tasks()` raises its private `_Stop`; `restore()` undoes every wrap. Tier-neutral (imports no fake).
- **Resolved**: see M.TEST_HELP.030 (agent decision D9).
- **Unit**: U20
- **Depends**: —
- **Blast carried by**: L1 and L2 boot-sequence scenarios → M.TEST_HELP.037/.030.
- **Kind**: test

### M.TEST_HELP.062 Create the write counters for files and SCD30 NVM
- **From**: A.U4.06
- **Site**: new `tests/_write_counters.py`.
- **Change**: `WriteCountingOpen(module, *, fail_writes=False, error=None)` and `scd30_nvm_writes(fake_i2c,
  address=0x61) -> dict[int, int]` (asserts `fake_i2c.log.dropped == 0`), each frame word cited (SCD30 Interface
  Description §1.4.1-1.4.3, §1.4.6-1.4.8).
- **Resolved**: —
- **Unit**: U4
- **Depends**: —
- **Blast carried by**: `tests/test_config_manager.py`, `tests/test_asy_bmp3xx_driver.py` → A.U4.06 (TEST_UNIT); twin
  `Scd30Chip.nvm_writes` → A.U4.06 (TWIN).
- **Kind**: test

### M.TEST_HELP.063 Create the shared radio-shape corpus
- **From**: A.U6.29 (4), A.U6.30, A.U10.41, A.U18.10
- **Site**: new `tests/_radio_shape_cases.json`.
- **Change**: one JSON object keyed by shape, each `{"accept": [...], "reject": [...]}`: `hostLabel` (A.U6.29's lists,
  no variant name), `countryCode` (A.U6.30), `hostName` (`pool.ntp.org`, `192.168.1.1` accept; `-a.b`, a 64-character
  label, `a..b`, `a b` reject), `ipv4List` (A.U18.10's lists). Read by the L1 test, the L0 pytest and the L0 vitest.
- **Resolved**: —
- **Unit**: U6 (stages U10, U18 add their keys).
- **Depends**: —
- **Blast carried by**: the three readers → A.U6.29 (TEST_UNIT, TSC, WEB).
- **Kind**: test

### M.TEST_HELP.064 Create the 2**30-wrap time source
- **From**: A.U14.34, A.U17.06 (user), A.U35.10 (builds on it)
- **Site**: new `tests/_ticks30.py`.
- **Change**: `Ticks30Time` with settable `now`, `ticks_ms()`, `ticks_diff()`, `ticks_add()` per
  `extmod/modtime.c:166-196` at period 2**30 (`OverflowError` outside (−2**29, 2**29)), `advance(ms)`, every other
  attribute delegating to the real `time`.
- **Resolved**: —
- **Unit**: U14
- **Depends**: —
- **Blast carried by**: rollover tests → A.U14.34/A.U17.06 (TEST_UNIT).
- **Kind**: test

### M.TEST_HELP.065 Create the driven clock for L1
- **From**: A.U35.10
- **Site**: new `tests/_driven_time.py`.
- **Change**: `DrivenTime` as A.U35.10 specifies (`install(*modules)`, `advance(ms)`, `run_until(pred, limit_ms)`,
  `jump(ms)`, shimmed `sleep`/`sleep_ms`/`wait_for`/`wait_for_ms`, a round cap that fails with the virtual time reached,
  restore in `__exit__`), its "no task runnable" test reading the same queue as microtest's after-each check.
- **Resolved**: —
- **Unit**: U35
- **Depends**: M.TEST_HELP.064, M.TEST_HELP.052.
- **Blast carried by**: self-test `tests/test_driven_time.py` and users → A.U35.10 (TEST_UNIT); scenarios →
  M.TEST_HELP.042.
- **Kind**: test

### M.TEST_HELP.066 Create the UDP port redirect
- **From**: A.U18.11, A.U18.45
- **Site**: new `tests/_udp_port_redirect.py`.
- **Change**: `redirect_udp_port(module, real_port, fake_port)` context manager: replaces `module.UDPSocket` (renamed
  by A.U10.38) with a subclass mapping `(host, real_port)` to `(host, fake_port)` before the real constructor, restored
  in `__exit__`.
- **Resolved**: —
- **Unit**: U18
- **Depends**: —
- **Blast carried by**: the three NTP test files and the DNS client test → A.U18.11/A.U18.45 (TEST_UNIT).
- **Kind**: test

### M.TEST_HELP.067 Create the cancel-at-each-await sweep
- **From**: A.U35.48
- **Site**: new `tests/_cancel_sweep.py`.
- **Change**: `cancel_at_each_await(build, start, invariants, *, max_steps=200)` (synchronous) as A.U35.48 specifies:
  per k, one `_async_harness.run()` from its own sync scope over a coroutine that awaits `build()`, starts the path,
  steps k turns, cancels, asserts `CancelledError` (or completion ends the sweep), then `invariants(fixture)`; no
  `asyncio.run()`-based builder inside; pollers are bounded fakes.
- **Resolved**: —
- **Unit**: U35
- **Depends**: M.TEST_HELP.043.
- **Blast carried by**: one sweep per path in its test file → A.U35.48 (TEST_UNIT).
- **Kind**: test

## tests/README.md

Absent at HEAD; no action creates it. A.U0.42 and A.U36.546 delete README.md's "the way `src/README.md`/
`tests/README.md` were" sentence (DOCS) — no change owed here (ledger rows only).

## Gaps for other clusters

- **GAP-T1 (TEST_UNIT)**: `tests/test_asy_uart_link_driver.py` (A.U8C.19) and `tests/test_asy_uart_comm.py` (A.U8C.17)
  import the harness bounds as public `RUN_LIMIT_S`/`LISTENER_DRAIN_S` (not `_RUN_LIMIT_S`/`_LISTENER_DRAIN_S`), and
  drive pairs with `_async_harness.run(coro, RUN_LIMIT_S)`; `build_pair()` now asserts setup (M.TEST_HELP.023/.024).
- **GAP-T2 (TEST_UNIT)**: `machine.reset()`/`bootloader()` raise `SimulatedResetError`/`SimulatedBootloaderEntryError`
  after counting (M.TEST_HELP.011): every test that triggers the reset timer or calls a reboot path catches
  `machine.SimulatedRebootError` (`tests/test_system_service.py` reboot, bootloader, escalation and starve tests;
  A.S0930.21/.24/.36, A.U11.03/.04/.07); `WDT(timeout > 8388)` raises `ValueError`.
- **GAP-T3 (TEST_UNIT)**: the RTC fake refuses a non-8-tuple and returns a normalised date with weekday recomputed
  (M.TEST_HELP.021); `Pin` state is per id and `I2C` state per bus id across constructions (M.TEST_HELP.012/.013) — a
  test needing an independent fresh bus calls `machine.I2C.reset_id(id)`.
- **GAP-T4 (TEST_UNIT)**: `UART.ioctl()` answers `-EINVAL` to every request but POLL; a direct `ioctl(3, …)` read in a
  test becomes `poll_mask()`; the new L1 that registers a real `select.poll()` zeroes `UART.real_poll_queries` itself,
  else the after-each hook fails it (M.TEST_HELP.010/.017).
- **GAP-T5 (TEST_UNIT)**: the `network` fake seeds `"XX"`/`"PicoW"`, returns one static object per interface, raises
  on `status("rssi")` off STA / `status("stations")` off AP, and an active AP reports `STAT_GOT_IP` (M.TEST_HELP.007):
  `tests/test_asy_wifi_service.py:2729-2730`'s comment and the hotspot tests follow (A.U18.28's blast).
- **GAP-T6 (TEST_UNIT)**: the NeoPixel fake stores a GRB bytearray: an out-of-range int wraps, a float raises
  `TypeError` (M.TEST_HELP.006, A.U24.25's three test comments).
- **GAP-H1 (HW_DEV, TSC)**: the board mirror `tests_hardware/device_scripts/heap_layout_after_full_boot_sequence.py`
  follows the probe's order (setups → `start_tasks(…, task_names=…)` → `start_timers(triggers, timers)`) and drops
  `_STARTER_LOOP_GRACE_MS`; `tests_scripts/test_digital_twin_boot_contiguity.py:262` `_MIRRORED_BOUNDS` drops it too
  (M.TEST_HELP.028, agent decision D8).
- **GAP-H2 (TWIN/SCR — `scripts/_digital_twin_scenarios.py`, carrier A.U25.46)**: the content owed to the moved in-DUT
  scenarios lands in the host harness, never in the deleted files (M.TEST_HELP.031/.033, agent decision D10):
  bus-fault scenario per A.U24.47 (sustained fault consumed before the GET, SGP40 fields `null`, SGP40 error count ≥
  1) with A.U0.29's "(owner, 2026-08-13)" tag and A.U20.28's `fixed_address()`; refusals classified per A.U25.31
  (`CeilingRefusedError`) with A.U24.34's per-site rule; served bodies compared with an uncontended answer and the
  route set read from the one route table (A.U24.36, A.U19.20); the concurrent config write PUTs `/networking
  {"GMTOffset": 3600 + 60*(i+1)}` (A.U24.37); tags A.U8C.04/A.U8C2.01 and `web.connections_per_page_load` (A.U8.18);
  owner tags `:482` (A.U0.28), `:753` (A.U0.35), OpenHAB `:215-218`, `:569-571` (A.U19.21); `_DEFAULT_OUTER_CAP_S`/
  `_DEFAULT_MAX_CONTENT_LENGTH` names (A.U5.05); readiness polls not sleeps (A.U25.45); no `gc.collect()` prop
  (A.U30.15); the A.7 citation (A.U36.004) and A.U36.544's `:251`/`:591` repoints (C.8 gaining the `config_lock`
  sentence); A.U14.28's F.7 row 1 text; the zero-think readers scenario (A.U35.29).
- **GAP-H3 (TWIN)**: `write_offline_ntp_config(cfg_dir)` has one implementation, in `tests/_generated_module.py`
  (born U20, M.TEST_HELP.047); A.U25.33's twin runner `digital_twin/run_generic_integration.py` imports it (or TWIN moves
  that one function to an import-safe module both tiers reach) — not a second copy.
- **GAP-H4 (TWIN)**: A.U25.47's twin boot-sequence scenario imports `tests/_boot_recorder.py` (M.TEST_HELP.061), not
  `tests/_sensortask_scenarios.py`; A.U25.33/A.U25.03's boot discipline in the construction library is applied by
  M.TEST_HELP.029.
- **GAP-H5 (SPEC)**: SPEC L.2 gains the equal-rank-order sentence (A.U36.544), E.8 the platform-print sentence
  (A.U36.544), and every H.7.1 citer list (A.U36.532) drops `tests/_webserver_concurrency_scenarios.py:193` (the file is
  deleted; its sentence moves with the harness).
- **GAP-H6 (TSC)**: `tests_scripts/test_import_placement.py` — the `_PENDING` entries for this cluster's files leave in
  U24 (H5); `_NAMED_EXCEPTIONS` holds `tests/_generated_module.py` (`load_generated`) and the two runners' `exec` (A.U10.30
  F.1 list).
- **GAP-H7 (GEN)**: the scenarios read `expected_facts()` through `build/generated_src/sensortask_<device>_expected.json`
  (`boot_sequence`, `fram_wired`); `fram_wired` lists module labels only — the RAM-only config log is derived by the
  scenario from `_CFG_LOG_FRAM` (M.TEST_HELP.036, AC_NOTES 13), so GEN must not emit a per-logger exemption list.

## Adherence findings

- `tests/microtest.py`: header docstring missing → fixed M.TEST_HELP.002; forced `sys.exit()` kept on every path
  (CLAUDE.md hang #2) → M.TEST_HELP.001; per-test `gc.threshold` and `sys.path` restore → M.TEST_HELP.002; comment cap →
  M.TEST_HELP.001.
- `tests/_threshold_runner.py`, `tests/_coverage_runner.py`: `#` headers instead of docstrings (A.U27.28) and inline
  `# noqa: S102` → fixed M.TEST_HELP.003/.004.
- `tests/_tmp_scratch.py`: eight bare `except OSError: pass` (OR19.a (1) swallowing) → fixed M.TEST_HELP.005.
- `tests/neopixel.py`, `tests/network.py`: over-long docstring lines (3-line cap counts `ceil(len/110)`) → fixed
  M.TEST_HELP.006/.007; network's "fidelity not required" comment contradicts the rp2-modelling rule → fixed
  M.TEST_HELP.007.
- `tests/machine.py`: docstring cites a BACKLOG finding that no longer exists (G9/R12) → fixed M.TEST_HELP.010; RTC
  comment's BACKLOG history pointer (OR27.a history) → fixed M.TEST_HELP.021; `UARTLink` comment's "(A1/A3)" changelog
  labels (G9/R12) → fixed M.TEST_HELP.019; comments restating the wrong poll mechanism (AC_NOTES 29) → fixed
  M.TEST_HELP.017; bounded poller rule (CLAUDE.md "Known hang cause") → holds (`LinkPoller`, no real poll); `**kwargs:
  Any` → fixed M.TEST_HELP.020.
- `tests/_shared_rest_roundtrip.py`: docstring history ("was {...}") → fixed M.TEST_HELP.009.
- `tests/_uart_comm_harness.py`: nested `asyncio.run()` risk — `run()` deleted for the guarded harness, `build_pair()`
  stays a coroutine → M.TEST_HELP.023; cross-module private names → fixed M.TEST_HELP.024.
- `tests/_bus_hazard_catalog.py`: blanket `except Exception: pass` in the sweep and the exercise loops → fixed
  M.TEST_HELP.026/.027; a pointer to another file's comment instead of the fact (G9/R12) → fixed M.TEST_HELP.026; private
  names imported across modules → fixed M.TEST_HELP.026 (10).
- `tests/_boot_contiguity_probe.py`: undefined labels "MEASUREMENTS M2.2/M3.9" (G9/R12) → fixed M.TEST_HELP.028;
  `# type: ignore[method-assign]` (allowed in tests) removed with the loop.
- `tests/_digital_twin_construction_scenarios.py`: "owner decision 10" label → fixed (travels, M.TEST_HELP.031); "all 6
  real devices" and the hand mandatory list (G8/R01 device-set claim) → fixed M.TEST_HELP.029.
- `tests/_sensortask_scenarios.py`: "WP3"/"WP6" labels, "Part L.3", "every real device has … today", "Only dev has it
  today" (G9/R12, G8/R01) → fixed M.TEST_HELP.034/.035/.036; hand-kept registries and orders → derived
  (M.TEST_HELP.035/.036); function-level imports (A.U0.07) → fixed M.TEST_HELP.034.
- `tests/_webserver_concurrency_scenarios.py`: OR125.a (request driving inside the DUT heap) → the file retires
  (M.TEST_HELP.033).
- Every merged change: no audit ID in permanent text, actor tags "(owner|agent, YYYY-MM-DD)" (H4); no product hook added
  for a test (OR36 — every wrap is applied from outside); every new log or list bounded (OR110.a: `feed_times` through
  `_CallLog`); no hardware or wear-gated operation touched.

## Owner questions

None. Every conflict in this cluster was settled by an owner row, a verified action text or the lead rulings (AC_NOTES
13, 29, 33, 38-39); the remaining choices are agent decisions below.

## Agent decisions for the OR2.c review

1. D1 — microtest finds `SimulatedRebootError` on whichever `machine` module is loaded (M.TEST_HELP.001).
2. D2 — the NeoPixel fake keeps `raise_on_write`, marked a test knob (M.TEST_HELP.006).
3. D3 — the `real_poll_queries` check lives in the machine fake's own reset hook: record, reset, then assert
   (M.TEST_HELP.010).
4. D4 — the FRAM chip fake carries the write counters A.U10.08 and A.U35.28 both use (M.TEST_HELP.022).
5. D5 — the UART harness bounds are public names (M.TEST_HELP.024).
6. D6 — the catalog's exercise loops catch only declared exception classes (M.TEST_HELP.026).
7. D7 — FRAM chunk owners derived from construction order and `_CFG_LOG_FRAM` (M.TEST_HELP.036).
8. D8 — the boot probe follows `main()`'s order and drops the grace/poll bounds (M.TEST_HELP.028).
9. D9 — the boot recorder is its own tier-neutral module (M.TEST_HELP.030/.061).
10. D10 — content owed to in-DUT scenarios that move host-side is written once, in the host harness (M.TEST_HELP.031/
    .032/.033).
11. D11 — the construction library derives its mandatory and optional names from the plan (M.TEST_HELP.029).
12. D12 — unit seeding precedes construction through the per-id bus, keeping `boot_generated()` generic
    (M.TEST_HELP.035).
13. D13 — `_all_loggers()` is rebuilt on `get_loggers()` (M.TEST_HELP.035).
14. D14 — one real-sequencer scenario: A.U11.39's mechanism, A.U10.13's assertions (M.TEST_HELP.038).
15. D15 — `_mem_backup_contract.py` stays its own module (M.TEST_HELP.049).
16. D16 — `write_offline_ntp_config()` is born in `tests/_generated_module.py` at U20 (M.TEST_HELP.047).

## Ledger

| action ID | merged into M-ID / dropped (reason) |
|---|---|
| A.U0.07 | M.TEST_HELP.003, M.TEST_HELP.004, M.TEST_HELP.028, M.TEST_HELP.029, M.TEST_HELP.032, M.TEST_HELP.034 |
| A.U0.28 | M.TEST_HELP.033 |
| A.U0.29 | M.TEST_HELP.031 |
| A.U0.35 | M.TEST_HELP.033, M.TEST_HELP.034, M.TEST_HELP.040 |
| A.U0.37 | M.TEST_HELP.034, M.TEST_HELP.036 |
| A.U0.39 | M.TEST_HELP.034, M.TEST_HELP.039 |
| A.U2.03 | M.TEST_HELP.045 |
| A.U2.13 | M.TEST_HELP.034 (blast-only: end state checked, holds) |
| A.U4.04 | M.TEST_HELP.041 |
| A.U4.05 | M.TEST_HELP.026 (blast-only: end state checked, holds) |
| A.U4.06 | M.TEST_HELP.062 |
| A.U5.02 | M.TEST_HELP.035 (blast-only: end state checked, holds) |
| A.U5.04 | M.TEST_HELP.032, M.TEST_HELP.033, M.TEST_HELP.035 (holds at M.TEST_HELP.032, M.TEST_HELP.035) |
| A.U5.05 | M.TEST_HELP.033 |
| A.U5.07 | M.TEST_HELP.036, M.TEST_HELP.041 |
| A.U5.08 | M.TEST_HELP.038, M.TEST_HELP.039 (holds at M.TEST_HELP.038) |
| A.U5.12 | M.TEST_HELP.023 |
| A.U5.17 | M.TEST_HELP.010 (blast-only: end state checked, holds) |
| A.U5.18 | M.TEST_HELP.010 (blast-only: end state checked, holds) |
| A.U6.21 | M.TEST_HELP.041 |
| A.U6.29 | M.TEST_HELP.063 |
| A.U6.30 | M.TEST_HELP.063 |
| A.U7.01 | M.TEST_HELP.010 (blast-only: end state checked, holds) |
| A.U7.07 | M.TEST_HELP.001, M.TEST_HELP.027 |
| A.U8.18 | M.TEST_HELP.033 |
| A.U8.23 | M.TEST_HELP.033, M.TEST_HELP.034 |
| A.U8C.01 | M.TEST_HELP.028 |
| A.U8C.02 | M.TEST_HELP.029, M.TEST_HELP.031 |
| A.U8C.03 | M.TEST_HELP.024 |
| A.U8C.04 | M.TEST_HELP.033 |
| A.U8C.17 | M.TEST_HELP.024 |
| A.U8C.19 | M.TEST_HELP.024 |
| A.U8C.72 | M.TEST_HELP.028 |
| A.U8C2.01 | M.TEST_HELP.033 |
| A.U9.03 | M.TEST_HELP.034, M.TEST_HELP.041 |
| A.U9.10 | M.TEST_HELP.037 |
| A.U10.07 | M.TEST_HELP.028, M.TEST_HELP.037 |
| A.U10.08 | M.TEST_HELP.022, M.TEST_HELP.037 |
| A.U10.10 | M.TEST_HELP.037, M.TEST_HELP.061 |
| A.U10.12 | M.TEST_HELP.020, M.TEST_HELP.028, M.TEST_HELP.038 |
| A.U10.13 | M.TEST_HELP.038 |
| A.U10.15 | M.TEST_HELP.040 |
| A.U10.19 | M.TEST_HELP.037 |
| A.U10.27 | M.TEST_HELP.008, M.TEST_HELP.041 |
| A.U10.30 | M.TEST_HELP.003, M.TEST_HELP.004, M.TEST_HELP.028, M.TEST_HELP.029, M.TEST_HELP.032, M.TEST_HELP.035, M.TEST_HELP.047 |
| A.U10.35 | M.TEST_HELP.028, M.TEST_HELP.034 |
| A.U10.37 | M.TEST_HELP.023, M.TEST_HELP.028, M.TEST_HELP.032, M.TEST_HELP.034 |
| A.U10.38 | M.TEST_HELP.023, M.TEST_HELP.026, M.TEST_HELP.034 |
| A.U10.40 | M.TEST_HELP.029, M.TEST_HELP.032, M.TEST_HELP.034, M.TEST_HELP.041 |
| A.U10.41 | M.TEST_HELP.063 |
| A.U10.43 | M.TEST_HELP.034 |
| A.U10.44 | M.TEST_HELP.034 |
| A.U11.03 | M.TEST_HELP.040 |
| A.U11.04 | M.TEST_HELP.040 |
| A.U11.05 | M.TEST_HELP.011, M.TEST_HELP.041 (holds at M.TEST_HELP.011) |
| A.U11.07 | M.TEST_HELP.011, M.TEST_HELP.037, M.TEST_HELP.049 |
| A.U11.08 | M.TEST_HELP.041 |
| A.U11.10 | M.TEST_HELP.028, M.TEST_HELP.035, M.TEST_HELP.037, M.TEST_HELP.047 |
| A.U11.12 | M.TEST_HELP.039 |
| A.U11.15 | M.TEST_HELP.039 |
| A.U11.19 | M.TEST_HELP.039 (blast-only: end state checked, holds) |
| A.U11.24 | M.TEST_HELP.033 |
| A.U11.31 | M.TEST_HELP.040 |
| A.U11.34 | M.TEST_HELP.037 |
| A.U11.35 | M.TEST_HELP.037 (blast-only: end state checked, holds) |
| A.U11.39 | M.TEST_HELP.020, M.TEST_HELP.038 |
| A.U12.18 | M.TEST_HELP.026 (blast-only: end state checked, holds) |
| A.U13.03 | M.TEST_HELP.012 |
| A.U13.08 | M.TEST_HELP.016 (blast-only: end state checked, holds) |
| A.U13.12 | M.TEST_HELP.018, M.TEST_HELP.025 |
| A.U13.13 | M.TEST_HELP.018 |
| A.U13.17 | M.TEST_HELP.023 |
| A.U13.R01 | M.TEST_HELP.012, M.TEST_HELP.013 |
| A.U13.R02 | M.TEST_HELP.027 |
| A.U14.11 | M.TEST_HELP.008 |
| A.U14.12 | M.TEST_HELP.010, M.TEST_HELP.020 (blast-only: end state checked, holds) |
| A.U14.14 | M.TEST_HELP.014 |
| A.U14.17 | M.TEST_HELP.012 |
| A.U14.18 | M.TEST_HELP.043 |
| A.U14.21 | M.TEST_HELP.016 (blast-only: end state checked, holds) |
| A.U14.28 | M.TEST_HELP.017, M.TEST_HELP.033 |
| A.U14.34 | M.TEST_HELP.064 |
| A.U14.37 | M.TEST_HELP.007 (blast-only: end state checked, holds) |
| A.U15.01 | M.TEST_HELP.026 (blast-only: end state checked, holds) |
| A.U15.12 | M.TEST_HELP.026, M.TEST_HELP.035, M.TEST_HELP.036, M.TEST_HELP.041 (holds at M.TEST_HELP.026, M.TEST_HELP.041) |
| A.U15.15 | M.TEST_HELP.027 |
| A.U15.25 | M.TEST_HELP.026 |
| A.U15.27 | M.TEST_HELP.026 |
| A.U15.28 | M.TEST_HELP.026 |
| A.U15.R01 | M.TEST_HELP.026 (blast-only: end state checked, holds) |
| A.U15.R02 | M.TEST_HELP.026 |
| A.U15.R03 | M.TEST_HELP.026 (blast-only: end state checked, holds) |
| A.U16.02 | M.TEST_HELP.036 |
| A.U16.03 | M.TEST_HELP.036 |
| A.U16.13 | M.TEST_HELP.036 (blast-only: end state checked, holds) |
| A.U16.14 | M.TEST_HELP.016, M.TEST_HELP.022 (blast-only: end state checked, holds) |
| A.U16.16 | M.TEST_HELP.012 (blast-only: end state checked, holds) |
| A.U16.17 | M.TEST_HELP.036 |
| A.U16.R01 | M.TEST_HELP.022 |
| A.U16.R02 | M.TEST_HELP.036 |
| A.U16.R03 | M.TEST_HELP.036, M.TEST_HELP.038 |
| A.U17.06 | M.TEST_HELP.064 |
| A.U17.19 | M.TEST_HELP.040 (blast-only: end state checked, holds) |
| A.U17.20 | M.TEST_HELP.023 (blast-only: end state checked, holds) |
| A.U18.10 | M.TEST_HELP.035, M.TEST_HELP.047, M.TEST_HELP.063 |
| A.U18.11 | M.TEST_HELP.066 |
| A.U18.21 | M.TEST_HELP.041 |
| A.U18.27 | M.TEST_HELP.007 (blast-only: end state checked, holds) |
| A.U18.28 | M.TEST_HELP.007 (blast-only: end state checked, holds) |
| A.U18.33 | M.TEST_HELP.041 |
| A.U18.38 | M.TEST_HELP.041 |
| A.U18.39 | M.TEST_HELP.041 |
| A.U18.45 | M.TEST_HELP.066 |
| A.U19.01 | M.TEST_HELP.040 |
| A.U19.02 | M.TEST_HELP.034, M.TEST_HELP.041 |
| A.U19.05 | M.TEST_HELP.034 |
| A.U19.06 | M.TEST_HELP.035 |
| A.U19.07 | M.TEST_HELP.033 |
| A.U19.08 | M.TEST_HELP.033 |
| A.U19.10 | M.TEST_HELP.041 |
| A.U19.11 | M.TEST_HELP.035, M.TEST_HELP.041 (blast-only: end state checked, holds) |
| A.U19.13 | M.TEST_HELP.041 |
| A.U19.20 | M.TEST_HELP.033 |
| A.U19.21 | M.TEST_HELP.033 |
| A.U20.02 | M.TEST_HELP.028, M.TEST_HELP.029, M.TEST_HELP.032, M.TEST_HELP.035, M.TEST_HELP.047 |
| A.U20.06 | M.TEST_HELP.028, M.TEST_HELP.029, M.TEST_HELP.032, M.TEST_HELP.035, M.TEST_HELP.038, M.TEST_HELP.047 |
| A.U20.07 | M.TEST_HELP.030, M.TEST_HELP.037, M.TEST_HELP.061 |
| A.U20.11 | M.TEST_HELP.035, M.TEST_HELP.036 |
| A.U20.16 | M.TEST_HELP.041 (blast-only: end state checked, holds) |
| A.U20.28 | M.TEST_HELP.031, M.TEST_HELP.033 |
| A.U20.38 | M.TEST_HELP.037 |
| A.U20.42 | M.TEST_HELP.029, M.TEST_HELP.035 (blast-only: end state checked, holds) |
| A.U22.01 | M.TEST_HELP.006 (blast-only: end state checked, holds) |
| A.U23.22 | M.TEST_HELP.041 |
| A.U23.33 | M.TEST_HELP.041 (blast-only: end state checked, holds) |
| A.U24.01 | M.TEST_HELP.026, M.TEST_HELP.034, M.TEST_HELP.044 |
| A.U24.02 | M.TEST_HELP.044, M.TEST_HELP.045 |
| A.U24.03 | M.TEST_HELP.001 |
| A.U24.05 | M.TEST_HELP.003, M.TEST_HELP.004 |
| A.U24.06 | M.TEST_HELP.025, M.TEST_HELP.029, M.TEST_HELP.032, M.TEST_HELP.035 |
| A.U24.07 | M.TEST_HELP.002, M.TEST_HELP.006, M.TEST_HELP.007, M.TEST_HELP.010, M.TEST_HELP.011, M.TEST_HELP.020, M.TEST_HELP.021, M.TEST_HELP.028 (holds at M.TEST_HELP.028) |
| A.U24.08 | M.TEST_HELP.002, M.TEST_HELP.023, M.TEST_HELP.029, M.TEST_HELP.032, M.TEST_HELP.035, M.TEST_HELP.043 |
| A.U24.09 | M.TEST_HELP.007, M.TEST_HELP.035 (holds at M.TEST_HELP.035) |
| A.U24.10 | M.TEST_HELP.005 |
| A.U24.11 | M.TEST_HELP.005 |
| A.U24.15 | M.TEST_HELP.002, M.TEST_HELP.010, M.TEST_HELP.017, M.TEST_HELP.023, M.TEST_HELP.025 |
| A.U24.16 | M.TEST_HELP.012 |
| A.U24.17 | M.TEST_HELP.001, M.TEST_HELP.011, M.TEST_HELP.012, M.TEST_HELP.014, M.TEST_HELP.015, M.TEST_HELP.040, M.TEST_HELP.048 |
| A.U24.18 | M.TEST_HELP.006, M.TEST_HELP.007, M.TEST_HELP.010 |
| A.U24.19 | M.TEST_HELP.007 |
| A.U24.20 | M.TEST_HELP.013, M.TEST_HELP.026, M.TEST_HELP.048 |
| A.U24.21 | M.TEST_HELP.014, M.TEST_HELP.026, M.TEST_HELP.032, M.TEST_HELP.035 |
| A.U24.22 | M.TEST_HELP.022, M.TEST_HELP.028, M.TEST_HELP.035, M.TEST_HELP.036 |
| A.U24.23 | M.TEST_HELP.016 |
| A.U24.24 | M.TEST_HELP.021 |
| A.U24.25 | M.TEST_HELP.006 |
| A.U24.26 | M.TEST_HELP.010, M.TEST_HELP.011, M.TEST_HELP.016, M.TEST_HELP.018, M.TEST_HELP.020 |
| A.U24.27 | M.TEST_HELP.027 |
| A.U24.28 | M.TEST_HELP.026, M.TEST_HELP.027 |
| A.U24.30 | M.TEST_HELP.059 |
| A.U24.31 | M.TEST_HELP.023 |
| A.U24.32 | M.TEST_HELP.041, M.TEST_HELP.050 |
| A.U24.34 | M.TEST_HELP.033 |
| A.U24.36 | M.TEST_HELP.033 |
| A.U24.37 | M.TEST_HELP.033 |
| A.U24.43 | M.TEST_HELP.026, M.TEST_HELP.028, M.TEST_HELP.029, M.TEST_HELP.035, M.TEST_HELP.038 |
| A.U24.45 | M.TEST_HELP.012 (blast-only: end state checked, holds) |
| A.U24.46 | M.TEST_HELP.028, M.TEST_HELP.029, M.TEST_HELP.032, M.TEST_HELP.035, M.TEST_HELP.046 |
| A.U24.47 | M.TEST_HELP.015, M.TEST_HELP.031 |
| A.U24.49 | M.TEST_HELP.052, M.TEST_HELP.053, M.TEST_HELP.054, M.TEST_HELP.057, M.TEST_HELP.058 |
| A.U24.50 | M.TEST_HELP.029, M.TEST_HELP.035, M.TEST_HELP.038 |
| A.U24.60 | M.TEST_HELP.008, M.TEST_HELP.009, M.TEST_HELP.035 |
| A.U24.63 | M.TEST_HELP.041, M.TEST_HELP.044 |
| A.U24.65 | M.TEST_HELP.029, M.TEST_HELP.032, M.TEST_HELP.033, M.TEST_HELP.035, M.TEST_HELP.055 |
| A.U24.67 | M.TEST_HELP.023, M.TEST_HELP.031, M.TEST_HELP.034 (holds at M.TEST_HELP.031) |
| A.U24.70 | M.TEST_HELP.029, M.TEST_HELP.032, M.TEST_HELP.056 |
| A.U24.72 | M.TEST_HELP.004 |
| A.U24.73 | M.TEST_HELP.007, M.TEST_HELP.008, M.TEST_HELP.009, M.TEST_HELP.010, M.TEST_HELP.019, M.TEST_HELP.020, M.TEST_HELP.023, M.TEST_HELP.025, M.TEST_HELP.026, M.TEST_HELP.028, M.TEST_HELP.029, M.TEST_HELP.034, M.TEST_HELP.043, M.TEST_HELP.051 |
| A.U24.76 | M.TEST_HELP.058 |
| A.U24.77 | M.TEST_HELP.019 |
| A.U24.78 | M.TEST_HELP.015, M.TEST_HELP.022, M.TEST_HELP.026, M.TEST_HELP.048 |
| A.U24.79 | M.TEST_HELP.028, M.TEST_HELP.029, M.TEST_HELP.032, M.TEST_HELP.035, M.TEST_HELP.037, M.TEST_HELP.047 |
| A.U24.80 | M.TEST_HELP.025 |
| A.U24.81 | M.TEST_HELP.007 |
| A.U24.82 | M.TEST_HELP.031, M.TEST_HELP.048 |
| A.U25.01 | M.TEST_HELP.049 |
| A.U25.02 | M.TEST_HELP.012, M.TEST_HELP.048 |
| A.U25.03 | M.TEST_HELP.013, M.TEST_HELP.029 |
| A.U25.04 | M.TEST_HELP.019, M.TEST_HELP.025 (blast-only: end state checked, holds) |
| A.U25.05 | M.TEST_HELP.012 |
| A.U25.08 | M.TEST_HELP.049 |
| A.U25.10 | M.TEST_HELP.027 (blast-only: end state checked, holds) |
| A.U25.16 | M.TEST_HELP.016 |
| A.U25.21 | M.TEST_HELP.006 |
| A.U25.22 | M.TEST_HELP.018 (blast-only: end state checked, holds) |
| A.U25.24 | M.TEST_HELP.029, M.TEST_HELP.033 |
| A.U25.25 | M.TEST_HELP.055 |
| A.U25.30 | M.TEST_HELP.019, M.TEST_HELP.025 (blast-only: end state checked, holds) |
| A.U25.31 | M.TEST_HELP.031, M.TEST_HELP.033 |
| A.U25.33 | M.TEST_HELP.029, M.TEST_HELP.033, M.TEST_HELP.047 |
| A.U25.43 | M.TEST_HELP.029, M.TEST_HELP.033 (holds at M.TEST_HELP.029) |
| A.U25.45 | M.TEST_HELP.031, M.TEST_HELP.033, M.TEST_HELP.060 |
| A.U25.46 | M.TEST_HELP.031, M.TEST_HELP.033 |
| A.U25.47 | M.TEST_HELP.030, M.TEST_HELP.061 |
| A.U25.48 | M.TEST_HELP.029, M.TEST_HELP.031, M.TEST_HELP.055 (holds at M.TEST_HELP.031) |
| A.U25.52 | M.TEST_HELP.030 |
| A.U25.70 | M.TEST_HELP.015, M.TEST_HELP.031 |
| A.U25.74 | M.TEST_HELP.033 |
| A.U26.64 | M.TEST_HELP.033 |
| A.U27.03 | M.TEST_HELP.010 |
| A.U27.23 | M.TEST_HELP.029, M.TEST_HELP.033 (holds at M.TEST_HELP.029) |
| A.U27.28 | M.TEST_HELP.002, M.TEST_HELP.003, M.TEST_HELP.004, M.TEST_HELP.010, M.TEST_HELP.028 |
| A.U27.38 | M.TEST_HELP.033 |
| A.U28.28 | M.TEST_HELP.003, M.TEST_HELP.004 |
| A.U28.29 | M.TEST_HELP.010 (blast-only: end state checked, holds) |
| A.U30.06 | M.TEST_HELP.026 (blast-only: end state checked, holds) |
| A.U30.14 | M.TEST_HELP.002, M.TEST_HELP.003 |
| A.U30.15 | M.TEST_HELP.033 |
| A.U30.16 | M.TEST_HELP.028 |
| A.U30.21 | M.TEST_HELP.014 (blast-only: end state checked, holds) |
| A.U31.01 | M.TEST_HELP.037 (blast-only: end state checked, holds) |
| A.U31.03 | M.TEST_HELP.028, M.TEST_HELP.037 |
| A.U31.09 | M.TEST_HELP.052 |
| A.U31.14 | M.TEST_HELP.052 |
| A.U31.17 | M.TEST_HELP.028, M.TEST_HELP.037, M.TEST_HELP.052 (holds at M.TEST_HELP.037) |
| A.U32.06 | M.TEST_HELP.028, M.TEST_HELP.038, M.TEST_HELP.041 |
| A.U35.03 | M.TEST_HELP.042 |
| A.U35.06 | M.TEST_HELP.023 (blast-only: end state checked, holds) |
| A.U35.10 | M.TEST_HELP.042, M.TEST_HELP.052, M.TEST_HELP.064, M.TEST_HELP.065 |
| A.U35.16 | M.TEST_HELP.026, M.TEST_HELP.027 |
| A.U35.19 | M.TEST_HELP.026 |
| A.U35.20 | M.TEST_HELP.022 (blast-only: end state checked, holds) |
| A.U35.28 | M.TEST_HELP.022, M.TEST_HELP.042 |
| A.U35.29 | M.TEST_HELP.033 |
| A.U35.30 | M.TEST_HELP.011, M.TEST_HELP.042 (holds at M.TEST_HELP.011) |
| A.U35.33 | M.TEST_HELP.020, M.TEST_HELP.042 (holds at M.TEST_HELP.020) |
| A.U35.34 | M.TEST_HELP.020, M.TEST_HELP.042 (holds at M.TEST_HELP.020) |
| A.U35.48 | M.TEST_HELP.043, M.TEST_HELP.067 |
| A.U36.004 | M.TEST_HELP.031, M.TEST_HELP.033, M.TEST_HELP.034 |
| A.U36.015 | M.TEST_HELP.055 |
| A.U36.016 | M.TEST_HELP.055 |
| A.U36.038 | M.TEST_HELP.034 |
| A.U36.526 | M.TEST_HELP.004 (blast-only: end state checked, holds) |
| A.U36.532 | M.TEST_HELP.010, M.TEST_HELP.017, M.TEST_HELP.018, M.TEST_HELP.025 (holds at M.TEST_HELP.017) |
| A.U36.544 | M.TEST_HELP.026, M.TEST_HELP.028, M.TEST_HELP.033, M.TEST_HELP.034 |
| A.U36.546 | M.TEST_HELP.010 (blast-only: end state checked, holds) |
| A.U37.03 | M.TEST_HELP.005 |
| A.S0930.03 | M.TEST_HELP.023 (blast-only: end state checked, holds) |
| A.S0930.11 | M.TEST_HELP.040 (blast-only: end state checked, holds) |
| A.S0930.13 | M.TEST_HELP.028 (blast-only: end state checked, holds) |
| A.S0930.18 | M.TEST_HELP.033, M.TEST_HELP.056 |
| A.S0930.21 | M.TEST_HELP.011, M.TEST_HELP.022, M.TEST_HELP.036 (blast-only: end state checked, holds) |
| A.S0930.24 | M.TEST_HELP.011, M.TEST_HELP.048 |
| A.S0930.25 | M.TEST_HELP.022 |
| A.S0930.26 | M.TEST_HELP.040 |
| A.S0930.36 | M.TEST_HELP.011 |
| A.S0930.37 | M.TEST_HELP.035, M.TEST_HELP.040 |
| A.SDEP.06 | M.TEST_HELP.033 |
| A.SDEP.08 | M.TEST_HELP.010, M.TEST_HELP.022 |
| A.SDEP.16 | M.TEST_HELP.033 |
| A.SDEP.17 | M.TEST_HELP.008, M.TEST_HELP.023 (holds at M.TEST_HELP.023) |
| A.SDEP.18 | M.TEST_HELP.033 |
| A.U0.06 | dropped (audit baseline artefact only; names `tests/network.py`/the twin library as excluded files — A.U27.23 runs `tests/network.py` alone, M.TEST_HELP.007) |
| A.U0.42 | dropped (README.md sentence only; `tests/README.md` absent, nothing owed here) |
| A.U10.11 | blast-only, holds (`tests/_sensortask_scenarios.py:1160-1175` boot-window ResetErrors scenario re-read against the merged `setup()`: its assertions hold; kept in M.TEST_HELP.040) |
| A.U21.13 | blast-only, holds (uses `tests/microtest.py` from `tests/lwip_host/`; M.TEST_HELP.001 keeps microtest free of any fake import) |
| A.U25.26 | blast-only (twin `WLAN.status()`; the unit half is A.U24.19 in M.TEST_HELP.007) |
| A.U30.12 | blast-only, holds (in-body threshold pairs removed by TEST_UNIT; the per-test restore it relies on is M.TEST_HELP.002) |
| A.U36.014 | dropped (CLAUDE.md hazard-rule text only; no helper change) |
