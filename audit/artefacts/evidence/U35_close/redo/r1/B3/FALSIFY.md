B3 falsification, written by the agent (Tue Nov  3 17:40:18 UTC 2026)

Scope: `cc5daeb7` in `S/wt-b3f` against `90691b6d` and `25caf528`. Runs through `S/u35/lead/run.sh` (logs in
`S/u35/lead/<label>.log`), one at a time, ten in all: b3f_rebuild, b3f_probe, b3f_sizes (`S/b3f_tmp/sizes_b3f.sh`;
the five base files written into the worktree and restored with `git checkout --`, status clean after), b3f_wire,
b3f_twinfram, b3f_hzmock, b3f_hztwin, b3f_crc, b3f_collect, b3f_fw. Test files ran at gc -1 and 32768 in one run.
Datasheets: absent in `S/wt-b3f/datasheets/` (submodule not checked out); MB85RS64V read from the main checkout's
`datasheets/fram/` PDF (p.1, read only), MB85RS2MTA from `S/ds/mb85rs2mta.txt` (AC table, its p.14).
The probe (`S/b3f_tmp/probe_b3f.py`, label b3f_probe) locks the heap around one product call only, so each
MemoryError is the product's own allocation failing (control A0: a non-allocating call under the lock answers ok).

## Verdicts

1. STANDS. No fixed-zero check, no RDID after setup, no `lost`, no `is_ready()`, no E54 in src/buildgen/js/html/twin
   (git grep). Writes to a silent chip stop at the latch (asy_fram_driver.py:279-281, W26) and the chunk entries
   (asy_fram_manager.py:141-144, :391-392, :357-358); nothing clears `initialized`, so they resume; the watch parks
   (asy_fram_manager.py:619-625). `verify_present()` asy_fram_driver.py:417-437: 1000 ms bounded wait, E19,
   `initialized = False` on a mismatch; no caller outside the driver (git grep). Twin 59/59 both stages
   (b3f_twinfram). Tried: an SO that reads high instead of low (a different board) makes writes answer True with
   W27 (WEL reads set), i.e. silent data loss; the owner's 2026-10-28 ruling (SO floats, pad pull-down) rules it out
   here, and 25caf528 behaves the same, so no refutation.
2. STANDS. Blank both blocks: asy_fram_manager.py:213-221 answers None on a fault, else False, no probe; the watch
   keeps its escalation for a chip that never set up (:622-624) and otherwise waits (:625). Twin test
   `test_a_blank_read_beside_a_held_session_stays_blank_makes_no_rdid_and_logs_nothing` passes (b3f_twinfram).
   Note: the test holds the driver's session lock after the block reads, where nothing takes a lock any more, so it
   passes by construction; it pins absence, it cannot fail on timing.
3. STANDS as a description (asy_fram_manager.py:755-756; asy_system_service.py:365-376, no catch, no re-check; an
   uninitialised manager short-circuits; for a protected chip get_write_protected() reads :406's flag). The catch
   being gone reintroduces the defect ad1fae73 fixed: finding F1 below. The re-check's removal is sound: in the product
   the preflight cannot yield (the manager is set up only after the driver, and no product path clears the driver's).
4. REFUTED (narrow). Read/write/clear: the RuntimeError from asy_spi_driver.py:50-51 is caught at
   asy_fram_manager.py:312-316/:404-406/:159-161 as E23 (probe D1: read None, write False, three E23); setup E10
   (probe D2). But the chunk layer's `invalidate()` (asy_fram_manager.py:429-437) and the erase loop (:744-749)
   have no catch: `erase_chip()` raises the RuntimeError (probe D3) instead of logging E23 and answering False, so
   an erase on a dropped bus ends in `_shutdown_sequence`'s catch (asy_system_service.py:471-473) and a watchdog
   reset reading 9, where 90691b6d answered E52 and an orderly code-9 reboot. 25caf528 had no erase. Reach: no
   product path drops the bus (SPI.deinit() is called only by SPI.init(), asy_spi_driver.py:67; git grep).
   `SPI.available` and E52 are gone (git grep).
5. REFUTED. The clock is 8 MHz (asy_fram_driver.py:124; rp2 48 MHz / 6, exact), inside MB85RS64V's 20 MHz (DS p.1)
   and MB85RS2MTA's 40 MHz at 2.7-3.6 V (AC table, p.14); the wire trace's init event reads 8000000
   (tests/test_asy_fram_wire_trace.py:34; b3f_wire 9/9 both stages). Texts that still disagree:
   - tests_hardware/flash/test_system_commands.py:54: the mid-erase resets (200, 1000, 2000 ms) are "inside the
     256 KB erase, about 2.2 s at the 1 MHz bus". At 8 MHz the wire time of 256 KB is ~0.26 s (bench: 1 KB in
     ~1.5 ms at 8 MHz, SPECIFICATION.md:7299), so the 1000 and 2000 ms cases very likely land after the erase and
     the test's own guard (:248, "the reset did not land inside the erase") fails at round 1. Not run (hardware).
   - digital_twin/machine.py:669: the twin knob's "real clock" is "8 us/byte at 1 MHz".
   - tests/test_digital_twin_bus_hazard_concurrency.py:1173: the timed erase runs "at its real wire time
     (8 us/byte)", against :107 of the same file ("an 8x-slow bus ... 1 us").
   Also, not a disagreement: tests_hardware/device_scripts/fram_conformance_probe.py:110 probes the chip at rp2's
   1 MHz default, so the hardware conformance check no longer runs at the product's clock.
6. STANDS. One `bytearray(...)` per read (asy_fram_manager.py:462, :527); a missing buffer answers None/(None,)*3
   with no entry (:464-468, :529-532); a missing check buffer: `_compare_with()` answers not valid, no fault
   (:164-166), so block 1 takes W63 and a rewrite (:231-240) on every read, no ALLOC (only the console line at
   construction, :107-111). Same outcome as 25caf528's `_read()` (its W "Invalid data in block 1" and rewrite).
7. STANDS. Protected means `(SR & 0x8C) == 0x8C` (asy_fram_driver.py:406), as 25caf528; no E53 (git grep).
   `setup()` (:400) and `set_write_protected()` (:338) take the bus lock only; both bodies under it are synchronous
   (no await between acquire and release), and every chunk block holds that same bus lock for its whole block
   (:140-150), `verify_present()` too (:430), so nothing runs inside either. Tried: a holder of the driver lock
   without the bus lock between awaits - none exists (git grep of session_lock/_bus_lock). Note: a partly
   protected chip (e.g. BP0 only) reads unprotected, so `erase_ready()` passes and the erase silently skips the
   protected part; no writer of a partial value exists here (this driver writes 0x8C/0x00, as does the legacy one,
   legacy/firmware/python/IndividualDrivers/asy_fram_driver.py:139-141).
8. STANDS. Both answer None (asy_fram_driver.py:396, asy_fram_manager.py:769); `run_setups()` ignores the result
   (asy_system_service.py:683-691); generated code only lists the bound method. Note: 25caf528's FRAMManager.setup()
   answered a bool (its asy_fram_manager.py:730), so None is not the pre-audit form; no reader, so harmless.
9. STANDS. Width fields: asy_crc_checks.py:24-28 match 25caf528 src/crc_checks.py field for field (an
   out-of-range poly again keeps `length()` = width in pass mode); add_into()/check_from() (:93-106, :120-136) are
   90691b6d's line for line. The product builds only default polynomials (asy_print_log.py:270,
   asy_scd30_driver.py:680, asy_sgp40_driver.py:228 and :623, asy_uart_driver.py:129 via buildgen/buildspec.py:71).
   tests/test_asy_crc_checks.py 76/76 both stages (b3f_crc); B3 removed only width assertions and the three
   pure-pass-through tests of the reverted width rule, no vector.
10. STANDS. asy_fram_manager.py:738-742 answers False; asy_system_service.py:455-470 then reboots with code 9
    through `_reboot()`. Edge: the line at :741 allocates a 2-tuple (probe A4 raises with no heap); on a heap too
    full for that, the raise ends in the shutdown's catch and a watchdog reset that still reads 9.
11. STANDS. No FRAM_BUS_DOWN/FRAM_WP_PARTIAL/FRAM_CHIP_LOST, errno 52-54 or "E52/53/54" anywhere outside audit/
    (git grep); error_catalog.json's 52-54 rows left are W codes of other owners (:153-155). E19 (:42), E20 (:43),
    W29 (:134), E49 (:66), W63 (:161) present.
12. REFUTED. The order is the pre-a4f0ccea/pre-8cf55c6b one (asy_system_service.py:489-494, :498-507, :656-659),
    but the guarded points do raise on a heap with no room, and the supervisor's restart does not take it:
    - probe A1: `FRAMManager.set_pause(value=False)` raises at its log line (asy_fram_manager.py:722) before the
      flag changes; A2: `pr.one("...")` raises building its *args tuple.
    - probe B1 (the real status loop, the real set_pause failing): the loop ends, storage stays paused, the deadline
      is gone, and a restarted loop never unpauses (paused, pending) = (True, False) after 5 more passes.
    - probe B2 (the real loop at 120 s, the real `one` failing its tuple): the restarted loop draws a second boot
      signature (before != after), which a client reads as a reboot.
    The owner's 2026-11-03 06:00 ruling says such a line raises and "the restart and watchdog backstops take it";
    here the restart is what goes wrong.
13. STANDS as far as run. Mock tier tests/test_bus_hazard_multi_device.py 22/22 both stages (b3f_hzmock); twin tier
    tests/test_digital_twin_bus_hazard_concurrency.py 25/25 both stages (b3f_hztwin, 233 s); no memory marker in
    any of my test logs. Flash and bench files still carry FRAM
    cases (test_bus_concurrency.py:312, :323, :339, :369; test_bus_concurrency_under_api_load.py:411), and collect
    (b3f_collect: 34/42 collected, 8 deselected by the default gates, the five FRAM cases and the three mid-erase
    resets among them).
    Run 13's superset check (scripts/_digital_twin_ci_suite.py:1094-1125) is untouched by B3 and was not run (a
    suite part, outside a single-file run).
14. STANDS. Each change traced to an item: the wire golden drops only the post-blank RDID line (count 56 -> 55) and
    takes the 8 MHz init event; the twin FRAM tests, readiness gates (`is_ready` row, setup's None), device
    scripts (setup's None -> `.initialized`) and the removed tests each pin a removed mechanism (lost chain, bus-down
    status, ALLOC entries, partial WP, driver-lock waits). Hardware scenario 4 asserted the removed chip-lost entry;
    recovery after a CS fault stays pinned by scenarios 1-3 (test_bus_concurrency.py:331-334). Run 3's responder skip
    (scripts/_digital_twin_ci_suite.py:1258-1259): at 90691b6d the responder's only E came from the RDID chain (a
    silent chip's blank read became "not read", so every FRAM-backed logger logged E28, asy_print_log.py:379-382); now
    the blank read leads to the setup write and a console-only line (:389-390), as at 25caf528, and a silent link logs
    nothing for a responder. The setup-write allowance (:1281) follows from the same. Not a test change but weakened
    by the clock: the hardware mid-erase resets, item 5.
15. Numbers STAND, the Run 3 margin is fragile. Bytecode (b3f_sizes, the v1.29.0 mpy-cross, bare names): 196,591 B
    over 28 modules; the five changed modules at 90691b6d total 1,652 B more (crc -3, driver -885, manager -688,
    spi -45, system -31), so 198,243 B; none grew. Image: dev's imageFreeBytes 56,684 B (b3f_fw).
    Run 3 on the CRC16-derived TOML can fail with no product defect. A FRAM-backed logger whose setup write fails
    never writes again (asy_print_log.py:207-210), so every attempt the silent chip sees is a one-time setup write
    (one per logger, two WRENs each, asy_fram_driver.py:213-217); dev wires about twenty such loggers, matching the
    20 seen. Those do not scale with the window, yet with the console off (`_diag()` prints only above level 0,
    asy_print_log.py:171-173) the allowance is 0 and the bound is int(window / 627 ms) * 2 alone: 24 at 7.7 s, 20
    below 6.90 s, 18 below 6.27 s. A window ~1.4 s shorter, or five more FRAM-backed loggers on dev, fails it.
    How short the window can get was not measured (a suite part, not a single file): its floor is the 4 s reset
    delay plus boot and the first supervisor pass.

## Findings outside the claims

F1 (reintroduced, ad1fae73's defect). The erase preflight's call raises with no heap: creating `erase_ready()`'s
   coroutine fails (probe A3). With no catch (asy_system_service.py:365-376) `_shutdown` stays set. Probe B3 (the real
   coroutine failing its own allocation): the command raises, `_shutdown` = 8, then `reboot` answers False, a
   mempause 0 answers False, a second `erasefram` answers True with no shutdown sequence started and no feed owned.
   Every system command and every mempause stays wedged until a reboot. Same premise as item 12 (owner, 06:00 ruling).
F2 (item 5's consequence). tests_hardware/flash/test_system_commands.py:54/:241-248 will very likely go red at
   round 1 for after_ms 1000 and 2000, because the 8 MHz erase is over before the reset. Defect in B3's deliverable.
F3 (low). Run 3's FRAM attempt check counts the setup writes only through console lines, so its strength depends on
   the console level (item 15); counting the loggers (or the "setup failed" condition) would not.

## Process notes
- One slip: while b3f_fw built I started a local wait loop (grep on runs.txt every 5 s, no host work) instead of only
  waiting for the run's notice; it ended by itself when b3f_fw finished. No refused command.
- Left in the worktree, all gitignored: build/b3f-firmware-dev.{uf2,json}, the rebuilt build/ inputs and the probe's
  tests/_tmp/sysservice. `git status` clean at cc5daeb7. S/b3f_tmp holds the probe, the sizes script and two
  size tables, no source.
