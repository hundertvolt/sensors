
######## SubagentHandback 2026-10-13T16:14:43.607Z
WIP d7e455a (lane F, branch audit/u24-f on e75d363). Stopped here, waiting for <API>.

1. Base: rebuild.sh rc 0. node_modules came from the lead. The record file `S/u24/laneF/report.md` was refused: the harness blocks subagents from writing report files. The full record follows below the line for you to file. Every scratch log is in `S/u24/laneF/` (after/, before/, seen_failing_*.log, mypy_*.log, precommit_f1*.log).
2. What F1 contains, end to end:
   - **`machine.reset_test_state()`**: registered at import by `microtest.after_each(reset_test_state)` (tests/machine.py:1499). It records `UART.real_poll_queries`, resets every knob, then raises AssertionError if a real poll had queried a UART fake.
   - **network**: its own reset hook is at tests/network.py:182.
   - **Pin**: `Pin(id: int|str|Pin, mode=None, pull=None, *, value=None, alt=SIO)` follows rp2:
     - ids 0-29 or board/CPU names; anything else raises ValueError("invalid pin") or 'unknown named pin "<n>"'.
     - The WLAN chip's pins take ids 30-32 and refuse a pull, an alt, or any mode but IN/OUT.
     - The pull is set on every configuring construction or init(): None means no pull, otherwise `pull & 3`.
     - State is shared per GPIO; `mode`, `pull` and `alt` are properties that read None until configured.
   - **I2C**:
     - Each id 0-1 is static from its first construction; reset_id()/reset_registry() clear it; new `attached` set.
     - A zero-length write raises ETIMEDOUT when busy and ENODEV for a NAKed or silent address.
     - scan() covers 0x08-0x77 and returns [] when busy.
     - A multi-byte register access reads and writes consecutive registers.
   - **Fault queue**: `inject_fault(op, exc_type, *args, times=1, match=None[, address=None])` raises a fresh exception per call; `pending(op)` counts what is queued.
     - Unknown ops or times<1 raise ValueError; I2C `scan` and SPI `write` are refused.
     - SPI faults and overruns fire only on transfers of 32 bytes or more; SPI match is the opcode of the last write.
   - **SPI**: MSB=1, LSB=0, LSB refused.
   - **UART**: ioctl answers -EINVAL to everything but POLL; POLL goes through `poll_mask(mask)` and counts `real_poll_queries`. rxbuf/txbuf below 32 clamp to 32.
   - **RTC**: no constructor argument; exactly 8 fields; the getter recomputes the date and weekday; boot value 2021-01-01.
   - **WDT**: a timeout above 8388 ms or an id other than 0 raises ValueError.
   - **reset()/bootloader()**: count, then raise SimulatedReset/BootloaderEntryError, both subclasses of SimulatedRebootError(BaseException).
   - **Timer**: takes rp2's keywords; `Timer(id != -1)` raises ValueError.
   - **Housekeeping**: TEST_API on every class and the module; `direction_to()` removed.
   - **network**: XX/PicoW seeds; one static WLAN per interface plus `constructions`; deinit drops both links; status() raises as cyw43 does and records `status_calls`.
   - **NeoPixel**: G-R-B `buf`, ORDER, fill, len, `timing=`; `writes` is bounded at 4096 frames with a `dropped` count.
   - **Twin**: -EINVAL plus `poll_mask()`, LinkPoller reads it, SPI constants, `FaultInjector.pending()`.
   - **Contract**: the readiness checks now read `poll_mask()`. I did this early because the counting POLL turned the unit contract test red.
3. Steps: 17 applied, 3 partly. TEST_HELP.010 (6) keeps `Any` in `_CallLog`/`mem_backup`, because removing it breaks every consumer's typing. TEST_HELP.018 is in end form for (1)(2) since U13; TEST_HELP.022 is (3) only, per the brief. Still open after <API>: TEST_HELP.048, the .025 completeness test, TEST_UNIT.264's contract runner, TWIN.126/.130/.166, steps 254 and 299.
4. Deviations:
   - `Pin(id, None)` alone configures nothing (rp2 would clear the pull); the line says so.
   - Timer keywords default to None so "any keyword given" is exact.
   - `WLAN.status(*params)` is the only way to tell status() from status(None).
   - test_fakes.py uses a local `_FakeWLAN` Protocol until H's `_protocols.WLANLike` is available.
   - The NeoPixel knob comment says "Test-only", not "twin-only".
5. Seen failing first: every new behaviour case failed on the old fakes; the full list with failing lines is in the record. Guards that passed at once: Pin(id) alone, open-drain release, ALT, reset_id, raise_on_construct.
6. Red until <API>: tests/machine.py:1499 and tests/network.py:182 raise AttributeError at import, so every unit-tier file importing machine/network dies. The mypy main pass reports tests/machine.py:1499 attr-defined. The hook-pair test also needs H's sorted order. My three unit files pass with a scratch microtest mirror; the two twin files pass on the plain tree.
7. Lines for you to retire: `tests_scripts/_decision_vocab_allowlist.txt:219` (the sentence is gone) and `pyproject.toml:480` "test_fake_timer_and_network" (renamed; test_fakes has no explicit Any). The `scripts/_render_coverage.py:15` red is classed as expected, as you said.
8. Consumer mypy reds, first line per file (all wave 2): test_asy_spi_driver:36, scd30:751, notification_scd30_integration:211, isl29125:820, ntp_client:1284, fram_manager:695, bmp3xx:1682, system_service:2097, setter_microdot:892, sgp40:793, i2c_driver:525. 37 errors across these 11 files.
9. Silent-failure findings: (a) the unit queue fires the oldest *matching* fault, while TWIN.002's end state fires only the head entry; the tiers must agree before the contract pins `match`. (b) The twin injector re-raises one exception object (U25). (c) The twin UART counts no real-poll queries (A-3).
10. Facts owed:
    - X: E.4 (fault convention, ports cited, Not-modelled lines), C.12 (ENODEV probe, scan never raises), F.7 row 12 / J.7 (both fakes answer GET_FILENO with EINVAL), K.2 (None and omitted pull are the same).
    - Y: none yet.
    - No @tunable added; no ANN401 line retired.
11. Runs: rebuild, 2 seen-failing loops, the 15 F1 file runs at -1, 32768 and settrace, 15 before-runs on a git archive of e75d363, 3 pytest before-commit runs and a few mirror trials. All exited rc 0 except the expected fails noted; RUNS.md is closed and `ps` shows nothing of mine.

---- RECORD (for S/u24/laneF/report.md) ----
Wall times at nice 19, -1 / 32768 / settrace:

| file | after F1 | before (e75d363) |
|---|---|---|
| test_fakes (was test_fake_timer_and_network) | 45/45, 0.1/0.2/0.5 s | 8/8, 0.0/0.1/0.3 s |
| test_machine_uart_link | 17/17, 0.2/0.8/0.8 s | 15/15, 0.2/1.0/0.8 s |
| test_write_counters | 9/9, 0.0/0.1/0.1 s | 9/9, 0.0/0.1/0.1 s |
| twin uart | 12/12, 3.8/4.4/6.0 s | 10/10, 3.9/4.5/5.8 s |
| twin machine | 62/62, 1.3/1.3/1.4 s | 60/60, 1.3/1.3/1.4 s |

No MemoryError or "memory allocation failed" in any log. Ruff is clean on all 13 files, and so is the twin mypy pass. Before-commit tests_scripts: 614 passed, 2 failed (the two lead lines in item 7).

Seen failing (old fakes, one process per test):
- **test_fakes.py**:
  - Pin: pull kept (:184), "GP7" TypeError (machine.py:48), Pin(1.5) TypeError (:211), external pin TypeError (:228).
  - I2C: 5-argument inject TypeError (:258, :330), address= (:343), id 2 accepted (:285), no attached (:292, :312), scan op accepted (:324), burst returned [c1,0,0] (:357).
  - SPI: MSB 0 (:374), 5-argument inject (:384), match= (:396), write fault accepted (:406).
  - UART rxbuf 8 (:415); RTC 7-tuple (:428) and getter as set (:436); WDT 8389 accepted (:447); SimulatedResetError missing (:455); Timer hard= (machine.py:1051).
  - Network: seeds DE (:136), statics (:142), deinit (:156), rssi on AP (:167).
  - NeoPixel: buf (:471), timing (:479), dropped (:491).
  - reset_test_state missing (:538); hook pair (:525).
- **test_machine_uart_link.py**: the real poll reported stdin's readiness (:129); ioctl(10,0) returned 0 (:141); the contract test failed teardown with "real select.poll() queried a UART fake 5 times".
- **Twin**: ioctl(10,0) returned 0 (uart:40), no poll_mask (:45), SPI.MSB 0 (machine:301), no pending (:308).

Datasheets: the FRAM WEL citations use MB85RS64V DS501-00015 p.6 (WEL reset), p.7 (WREN/WRDI), p.8 (WRSR leaves bit 1 alone), p.11 (WRITING PROTECT), all read in the extracted text. The ISL29125 burst write and burst read are FN8424 p.7-8. All rp2 facts were read in /root/pico-toolchain/micropython v1.29.0 (files and lines cited on each fake line).

Findings outside my set: none edited. The consumer list for wave 2 comes after <API>.
