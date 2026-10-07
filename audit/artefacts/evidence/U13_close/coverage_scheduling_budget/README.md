# Coverage-build failures on a loaded host: two wall-clock bounds against fake time (U13)

Seen on d8ac624's coverage run under load (`../coverage_tracer_heap/coverage_d8ac624_under_load.log.gz`):
`test_{dev,wozi}_i2c1_a_bus_recovery_does_not_disturb_concurrent_sibling_reads_across_timing_offsets` (status 4) and
`tests/test_digital_twin_uart_link.py` `test_a_maximum_length_train_completes_and_still_yields` ("the maximum-length train
did not complete"). Root-caused by a separate investigator by stall injection (`time.sleep_ms(D)` once at a chosen
poll); neither is a product defect. Same class as OF-33.

## I2C recovery scenario (`i2c/`)
- The planted slave (`tests/_bus_hazard_catalog.py` `hold_sda_through_a_stretched_clear`) stretches SCL for a count of
  reads (5 in the scenario); `src/asy_i2c_driver.py` `_scl_released()` bounds each wait by wall clock (50 ms default).
  Status 4 alone is the lead-in wait running out: the one wait during which the sibling readers still run (the last
  reaches its lock request ~2 ms into the clear, `probe_settrace_locktrace.log`).
- Reproduction (`probe_recovery.py`): plain binary D=44 ms passes, D=46 ms gives status 4 (k=2, lead-in) or 5 (k=7); the
  32768 stage the same; settrace flips at 44 ms. Original grid 11/21 cells flip (statuses 4, 5, 7).
- On hardware a False needs SCL really low at a read 50 ms after `start` with no master edge between: a real hold. A
  late poll cannot invent one, so the bound is a scheduling budget only against the read-counting fake.
- Fix (`fix_bus_hazard_catalog.patch`, landed in the lead's form): the catalog's `PollRoundClock` (each driver sleep plus
  1 us per read), now entered inside `recover_marking_the_clear()` so the multi-device file's held-bus-clear test is
  covered too. Stall sweep 42/42 to 1000 ms both stages; planted P1 (clear outside the bus lock) and P2 (stretched pulse
  taken as held) still fail.
- `driver_test_stall.log`: `tests/test_asy_i2c_driver.py` `test_clear_waits_out_a_stretched_clock_...` flips with one
  60 ms stall (46 ms passes): open as OF-49 with the synchronous boot-clear checks.

## Twin UART maximum-length train (`uart/`)
- The assertion is `uart_set()` returning False: the product's 1000 ms reply `timeout`
  (`src/asy_uart_link_driver.py`), checked in `src/asy_uart_driver.py`. Both link ends share one interpreter and the
  twin delivers bytes by real wire time; under the tracer one `UARTLink._advance()` runs ~21k traced lines (117-220 ms in
  the first frames after the build), and under load one 1.1-2.2 s loop-blocking step at chunk 1: initiator 81 "no ACK
  for frame", responder 22 "train stalled at chunk".
- Reproduction (`probe_max_train.py`): D=900 ms passes, D=1100 ms fails with the same message and the 81/22 pair.
- Fix (`fix_uart_link_max_train.patch`, landed in the lead's form): the test's `_PollRoundClock` over `asy_uart_driver`
  and `asy_uart_comm` (each sleep plus 1 ms per read; the first form without the per-read tick turned planted U2, a
  loop-holding wait, into a hang). Planted U1 (wrong ACK uid), U2, U3 (spurious error) still fail.

## The landed form and its guards (`fix_check/`)
- `tests/test_bus_hazard_multi_device.py` `test_a_host_stall_inside_a_stretched_clear_does_not_read_as_a_held_clock`:
  a 60 ms interpreter stall inside the first SCL read (`hold_sda_through_a_stretched_clear(host_stall_ms=)`).
- The maximum-length train carries one 1100 ms stall after UART sleep 2000 (of about 4350 in a train).
- `seen_*.log` (`run_seen_failing.sh`): on a copy with the clock removed both guards fail with the original signatures
  (status 4; the train did not complete); with it both pass. Whole-file results: the U13 scan record.
