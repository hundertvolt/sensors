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
- **H2 Harness migration** (U24): `run()`/`run_timed()`/`_cancel*` → `tests/_async_harness.py` (M.TEST_HELP.040, a
  bounded copy keeps its bound); `const()` mirrors → `tests/_src_const.py` (M.TEST_HELP.042); response bodies →
  `strict_loads()` (M.TEST_HELP.012); the device set and wiring plans → `tests/_twin_devices.py` (M.TEST_HELP.055);
  generated modules through `load_generated()`/`boot_generated()` after `require_fresh()` (M.TEST_HELP.046/.047);
  catalog codes `code("E"|"W", NAME)` (`tests/_error_codes.py`, M.TEST_HELP.050); `inject_fault(op, exc_type, *args,
  times=…)` (M.TEST_HELP.021).
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
  the `real_poll_queries` check (M.TEST_HELP.016) so microtest names no fake; A.U30.14's allowance (`tests/microtest.py`
  restores the threshold it read at start) matches (c) exactly.
- **Unit**: U24 (A.U27.28's header lands early in the same edit; its U27 gate finds it).
- **Depends**: M.TEST_HELP.001; M.TEST_HELP.040 (`_async_harness` tasks are the ones the check backstops).
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
  scenario → M.TEST_HELP.035 (A.U10.27); SPEC F.1 sentence → A.U14.11 (SPEC).
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
  source above; the twin half, A.U25.08, asserts both — one contract, M.TEST_HELP.048).
- **Unit**: stage 1 U11 (cause, regions, `power_on()`, `mem_backup()` — A.U11.05's product lands in the same commit,
  and the main mypy pass resolves `machine` to this fake); stage 2 U24 (the raising `reset()`/`bootloader()`, WDT bound,
  `TEST_API`); `feed_times` lands with A.S0930.24 (U11, system-command work) inside stage 1.
- **Depends**: M.TEST_HELP.010; M.TEST_HELP.001 (microtest reports an uncaught `SimulatedRebootError` as a FAIL).
- **Blast carried by**: every test that triggers the product reset timer or calls a reboot path catches
  `machine.SimulatedRebootError` — `tests/test_system_service.py` reboot sections → A.U24.17/A.S0930.21/A.S0930.36
  (TEST_UNIT), `tests/_sensortask_scenarios.py:953-973` → M.TEST_HELP.039; reset-code L1 cases → A.U11.07 (TEST_UNIT);
  planted-fault scenarios → M.TEST_HELP.041; twin fake → A.U25.07/A.U25.08 (TWIN).
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
  `tests/_digital_twin_construction_scenarios.py` → M.TEST_HELP.034; twin `pending()` → A.U24.82 (TWIN).
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
  (TEST_UNIT); WREN-retry L1 → A.U16.R01 (TEST_UNIT); scan-budget and fault-storm scenarios → M.TEST_HELP.041; twin FRAM
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
- **Depends**: M.TEST_HELP.040, M.TEST_HELP.017.
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
  page in `datasheets/bmp3xx/`. (9) `inject_fault` calls take the class-plus-args form. Typed through
  `_protocols.I2CLike`, no `Any`.
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

