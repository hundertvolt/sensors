
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

######## SubagentHandback 2026-10-13T17:51:25.525Z
U24 lane F, phase 2: done. Branch audit/u24-f (worktree S/wt-u24f), nothing pushed. Report files are blocked, so the record follows below the line.

1. **Commits:**
   - 5836113: merge of `<API>` 876bc9e, no conflicts; rebuild.sh rc 0.
   - 0b4b370: the after-API work.
   - 3050b0f: two fake fixes the consumer sweep exposed.
2. **Steps after `<API>`:**
   - Applied (7): TEST_HELP.048, TEST_UNIT.264, TWIN.126, TEST_UNIT.335, TSC.089, TWIN.166, TEST_UNIT.341.
   - Already landed (1): TEST_HELP.019. It went in at F1; `git grep direction_to -- tests` is empty.
   - Partly (2):
     - TEST_HELP.025: ALL_CHECKS is complete and has a registry test. The UARTLike typing is not done, so LinkFactory stays Any.
     - TWIN.130: the contract runs through poll_mask on the harness. The static object per id and the buffer clamp are not done; they are twin product scope, so U25.
   - **Your four items:**
     - 1 is done: a `_OMITTED` sentinel, so `Pin(id, None)` runs init and clears the pull.
     - 2 is done: `reset_test_state()` closes every `_DMA_CHANNELS` entry.
     - 3 is done: `_FakeWLAN(WLANLike, Protocol)`.
     - 4 is noted: the runner pins single-entry fault queues only.
3. **Seen failing first:**
   - `Pin(10, None)` kept the pull (test_fakes.py:267).
   - A leaked DMA channel (test_fakes.py:53). The sorted-order case `test_a_delimited_frame_of_the_wrong_length_counts_as_discarded` failed at test_asy_uart_comm.py:662; after the release the file passes 191/191.
   - `_machine_contract` missing gave an ImportError.
   - The contract against the base fake failed 7 checks. The twin fails exactly its 4 `_TWIN_PENDING` checks.
   - The UART registry check bit on a planted check (test_machine_uart_link.py:38).
   - The surface check failed 9 times on the base and caught a planted knob. A missing checkout gives ERROR, not a skip.
   - The twin machine file had 16 parked-task failures before; 63/63 after.
   - In 3050b0f, the wrapped-WLAN count failed with an AttributeError at network.py:65, and Pin `irq_*` was missing.
4. **Green:**
   - My 5 files at -1, 32768 and settrace, with no MemoryError: test_fakes 50/50, machine_uart_link 18/18, write_counters 9/9, twin machine 63/63, twin uart 12/12.
   - ruff is clean on all 8 scopes except H's `tests/_protocols.py:28` FBT001 (expected).
   - The mypy twin and host passes are clean. The main pass has only the 37 consumer errors in 11 files, the same list as before.
5. **Red checks** (before-commit run: 649 passed, 3 failed):
   - `test_import_placement` reports `_PENDING` rows that no longer occur: lines 83-86 and 98-99 (your list).
   - The surface check fails on U2's doubles: `_FakeModule.set_calls`, `_FakeLogger.err_count` and `reset_calls` (test_asy_webserver_service.py).
6. **Wave 2 red list:** I ran 91 consumer files read-only at -1.
   - 40 are green.
   - 31 fail only on "left a task parked". That is H's harness; the files and owners are in the record and match H's list.
   - 20 have reds the fakes caused. Each is per file in the record with its owner and first line. 11 of the causes were confirmed by undoing the one fake behaviour in a scratch runner, which turned the red green.
7. **Facts owed:**
   - **X:**
     - E.4: the surface rule and its check, the machine contract, the twin pending list, port citations, the fault-queue convention, the corrected lightweight sentence.
     - C.12: a NAKed probe raises ENODEV, and `scan()` never raises.
     - F.5.1: I2C is a static object per id.
     - F.7 row 12 and J.7: GET_FILENO gets EINVAL; POLL goes through `poll_mask`.
     - F.9: the bounded-poll wording.
     - K.2: an omitted pull and `pull=None` are the same.
   - **Y:** the CLAUDE.md "Known hang cause" mechanism sentence. A real poll over a fake is now counted, and the after-each check fails it.
   - **Lead:**
     - `pyproject.toml:252`'s ANN401 reason is stale. Timer takes explicit keywords now; the remaining sites are `_CallLog.__getitem__`, `UART._channel` and `mem_backup`.
     - The Any baseline keeps `machine` and `_uart_link_contract`.
     - No `@tunable` was added.
   - **U2:** `asy_ntp_client.py:329` writes weekday `tm[6]+1`, but rp2 ignores it. `machine_rtc.c:85-96` reads fields 0-2 and 4-6 only, and the getter recomputes the weekday. Not a product bug.
   - **U25 mapping:**
     - `check_inject_fault_fifo` → A.U25.70 / M.TWIN.002.
     - `check_pin_defaults` and `check_pin_pull_semantics` → A.U25.02 and .05 / M.TWIN.021.
     - `check_reset_never_returns` → A.U25.07 / M.TWIN.034.
     - The twin surface pending → M.TWIN.020-036 (TEST_API).
8. **Decision for you:** whether the unit UART fake should model rp2's TX/RX pin rule (`machine_uart.c:71-80, 314-323`).
   - Today the fake's "Not modelled" line declares it, and I left it that way, which is the conservative choice.
   - If modelled, test_asy_uart_driver.py:245 goes green, and :178's `UART(1, tx_pin=0, rx_pin=1)` goes red, because it is invalid on rp2.
9. **Runs:** every run of mine has a RUNS.md line with its exit code, from 904 to 1058. All are closed, and `ps` shows nothing of mine.
   - Besides those, I ran 8 foreground diagnostics of 2 s or less with no RUNS.md line. They are listed in the record.
   - My wait loop b0dos0x10 was stopped with TaskStop.

---- RECORD ----

**Wave 2 reds the fakes caused** (owner, file and first line). In each case the fake follows rp2 and the fix goes in the consumer. "cf" marks a cause confirmed by undoing it in `S/u24/laneF/tools/counterfactual.py`.

- **U4 test_asy_fram_manager.py:721:** an SPI fault fires only on transfers of 32 bytes or more (`machine_spi.c:267`). The 4-byte chunk read never takes it. The injection at :695 also uses the old shape, an exception instance; the new one is `exc_type, *args`.
- **U4 test_asy_fram_wire_trace.py:116** (`_cycles`, all 9 tests): the golden reads `init 1000000/0/0/8/0`, but firstbit is now `SPI.MSB` = 1.
- **U4 test_asy_i2c_driver.py:**
  - :153: `scan()` now lists the registered 0x50 too.
  - :517: `scan()` never raises when the bus is busy (`machine_i2c.c:341-356`).
  - :527, :564 and :1277: the old inject shape.
  - :1179: the stop-sending probe goes to an unattached 0x60 and gets ENODEV; attach 0x60. cf probe_any.
- **U4 test_asy_spi_driver.py:**
  - :287: `firstbit=0` is LSB, which raises NotImplementedError("LSB") (`machine_spi.c:202-203`).
  - :842: the old inject shape.
  - :1087: the golden's firstbit should be 1, not 0.
- **U1 test_asy_isl29125_driver.py:**
  - :822 and :835: the old inject shape.
  - :979: an omitted pull reads 0 (`machine_pin.c:300-306`).
  - :2963 and :2983: `_irq_trigger` and `_irq_handler` should become the `irq_trigger` and `irq_handler` added in 3050b0f.
- **U1 test_asy_scd30_driver.py:**
  - :753: the old inject shape.
  - :772: the probe of an unattached 0x61 gets ENODEV; attach 0x61.
  - :812, :842 and :862: `_irq_trigger` should become `irq_trigger`.
- **U1 test_asy_sgp40_driver.py:1319** (`_backup_rig`): all 46 failures come from `_init_sgp` → setup → a probe of the unattached 0x59. Attach it in `make_i2c`. cf: 155/155 pass when every probe is answered.
- **U2 test_asy_ntp_client.py:**
  - :1241: the read-back weekday is `tm[6]`, not `tm[6]+1`; the getter recomputes it.
  - :1284, :2130 and :2179: `RTC._shared_datetime` is gone; set the time through `RTC().datetime()`.
- **U2 test_asy_wifi_service.py** (rerun on 3050b0f: 12 other failures plus 13 parked; 4 more were my count bug, fixed):
  - `status("stations")` on the STA object raises ValueError("AP required") (`network_cyw43.c:371-388`): :3230, :3236, :3255, :3326, :3352, :3362, :4608. cf stations_any.
  - `_HotspotRadio._build` (:4184-4196) calls `answer(None)`, and `status(None)` raises TypeError. It also re-wraps the static AP object on every build: :4265, :4334, :4365, :4389, :4440. cf status_none plus fresh_wlan.
- **U2 test_asy_webserver_service.py:940:** `reset()` now raises SimulatedResetError and never returns; the test has to catch it.
- **U2 test_setter_microdot_integration.py:914:** the static I2C keeps its log across `make_scd_reader()` rebuilds; call `reset_id` per case. cf fresh_bus.
- **U3 test_asy_system_service.py:1650:** first of 24 tests (through `_drive` :1326) that reach `reset()` without a catch.
- **U3 test_asy_uart_driver.py:**
  - :245: `tx_pin=29` is a valid rp2 GPIO; the real raise comes from the pin rule, which the fake does not model (item 8).
  - :259: `Pin("0")` raises ValueError('unknown named pin "0"'), as rp2 does.
  - :310: with pin 29 valid, the error is "UART(99) doesn't exist", which has no "pin" in it.
- **D tests/_bus_hazard_catalog.py:256** (test_bus_hazard_generated, dev_i2c1 same-occupant): `configure(ir_adjust=20)` writes CONFIG2-3, and a CONFIG1-3 burst now reads that write (FN8424 p.7-8). Both `bytes(3)` and `00 14 00` are whole states, so this is not a tear; the check has to accept both. cf own_key_store.
- **D tests/_sensortask_scenarios.py** (all 6 wrappers):
  - :2115 `(10, 0, 0)`: the SCD30 probe at 0x61 is unattached. cf probe_any.
  - Reset reached without a catch at :2167, :2189, :1932 and :1964.
  - dev only, 7 tests: teardown reports "a real select.poll() queried a UART fake 1 times". dev's UART links poll through a real `select.poll()`, which is the CI hang mechanism, so they need a bounded poller.

**Parked-only files** (H's harness), 31 in total:
- U3: api_response 4, base_classes 5, config_manager 2, uart_link_driver 2, digital_twin_uart_link 19.
- U4: notification_service 9.
- U2: neopixel_wifi 5, ntp_fram_system 5, ntp_wifi_dns 1.
- D: twin bus_hazard_concurrency 18, construction ×6 (3 each), generic_wiring 7, isl29125_autorange 20, launch 4, network_neopixel 1, real_website 9, run_generic_integration 3, scd30 1, sensortask_integration 15, webserver_concurrency ×6 (20 each), wifi_modes 1.
- Parked failures inside the fake-caused files: system_service 30, wifi 13, isl29125 3, ntp 3, webserver 3, setter 3, sensortask 10 per device.

**Unlisted foreground diagnostics** (all read-only, 2 s or less each):
- 2 wifi traceback reprints.
- 4 status_none counterfactual processes.
- 2 scan probes.

**Logs** are in `S/u24/laneF/`:
- sweep/, sweep2/: the consumer sweep and the rerun.
- final2/: my 5 files at three stages.
- cf_batch*.log, cf_sgp40_all.log: the counterfactual checks.
- mypy_*3.log, precommit_w2.log: type checks and the before-commit run.
- logs_sf_wave2*.log: the 3050b0f seen-failing runs.

**Datasheets:** ISL29125 FN8424 p.7-8 (burst access); MB85RS64V DS501-00015 p.6/7/8/11 (WEL lines). All rp2 facts were read in /root/pico-toolchain/micropython v1.29.0.
