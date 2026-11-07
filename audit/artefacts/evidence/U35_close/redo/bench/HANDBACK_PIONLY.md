PIONLY hand-back, written by the agent (Thu Nov  5 13:58 UTC 2026)
Worktree `S/wt-pionly` at `5f763f25`, rebuilt (the bench ran `1d2f900a`: `src/asy_uart_driver.py` differs only in a comment, and the SCD30 scenario, `asy_scd30_driver.py` and `asy_i2c_driver.py`'s probe are the same). Runs: 6 light (`pio_uart_probe`, `pio_scd30_probe`..`probe5`), 1 heavy (`pio_load1`: six processes on core 3, lock taken and released). The probes were scratch scripts in `ftmp/` (deleted). I changed no code.

## 1. `test_two_concurrent_cancellers_both_return`: (b) test assumption
- **Assumption:** both cancellers (`create_task` at `tests/test_asy_uart_driver.py:962` and `:963`) run before the holder's next poll round. `_make_uart` (`:110-111`) polls every 1 ms, so a gap of 1 ms or more between the two calls (preemption, a GC pass, a millisecond edge) lets the holder run between them. It acknowledges the first request, leaves `async with` and frees the lock. The second canceller then finds the lock free and returns False, as the contract says (`src/asy_uart_driver.py:390`: "nothing was in flight"). The test asserts True at `:970`.
- **Reproduced:** a 2 ms busy wait between the two `create_task` calls failed 93 of 200 runs unloaded and 50-59 of 200 on one shared core. Every failure was `(True, False)` in the order: first starts, holder leaves, second starts with `locked=False`. Without the wait, 0 of 200. The file alone passed under the one-core load (no natural reproduction).
- **Not firmware:** the one caller, `src/asy_uart_comm.py:1021`, is a single canceller, and False there is correct.
- **Fix:** park the holder inside `async with uart` on an Event until both requests have latched (`_cancel_req == 2`), then read, so one acknowledgement covers both on any host.

## 2. `only_the_api_writes_the_scd30` [wozi], `(4, 3, 2)`: (b) test assumption
- **Assumption:** the 4 is `idle_ticks < 8` (`tests/_sensortask_scenarios.py:3078`). `_scd30_cycles` starts the tasks (`:1407`), then drives the ten 500 ms ticks (`:1417-1424`) without waiting for the read task's `_init_scd()`. Wherever that init's `_frc_reset()` lands (`src/asy_scd30_driver.py:429`), it zeroes `_frc_idle_ticks`. The init waits on two real 100 ms probe settles (`src/asy_i2c_driver.py:379`, `:384`; the scenario patches only `asy_system_service` and `asy_scd30_driver`). After that it advances about one await per tick of the yield-driven loop.
- **Traced here:** the loop takes 30-42 ms. The init's reset lands 150-200 ms after the first tick, so idle is 10 and the test passes (10 runs, 6 of them under the one-core load).
- **Reproduced:** a busy wait per tick stands in for the slow Pi. At 30-50 ms per tick it passes; at 70 ms per tick it fails `(1, 3, 2)` in 2 of 2 runs, with the reset after tick 9. The Pi's 4 is a reset after tick 6.
- **Patching the I2C module too does not help:** with `asy_i2c_driver`'s asyncio patched as well, it still fails `(7, 3, 2)` at 70 ms per tick, with the reset after tick 3.
- **Not firmware:** on the board, the init (2.7 s or more, with the soft-reset wait) restarting the idle count is documented behaviour ("the soft reset restarted the measurement").
- **Fix:** in `_scd30_cycles`, wait until each reader's init has run (its three queued init frames consumed, then one yield) before the first tick.

## 3. `test_sensortask.py[dev]` passed on attempt 2/3: (c) other, pending one log
- **What the retry means:** `_run_with_retries` (`scripts/test.sh:573-613`) retries only on a timeout (exit 124, or 137 past the bound). A failing test is FAIL at once. So attempt 1 ran past the 240 s per-file bound (`scripts/test.sh:90-91`), as a hang or as plain slowness.
- **The log exists:** each attempt is appended to the job's log (`:582`), which is archived on the Pi under `build/archive/test_sh/20261105T131850Z`. It is not here.
- **Here:** the dev file took 81 s on the shared core (101/101) and wozi 60 s, so a Pi running 16 files at once can plausibly reach 240 s. Neither a hang nor slowness is excluded.
- **Fix:** read attempt 1 in that archived `[dev]` log. If it is the bound, the bench run sets `PER_FILE_TIMEOUT_S` for the Pi (an existing setting; the default is unchanged). If it is a hang, its ABORT line names the test.
nothing of mine is running
