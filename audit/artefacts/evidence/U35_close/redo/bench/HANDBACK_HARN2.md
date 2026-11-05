harn2 hand-back, written by the agent (Thu Nov  5 18:14:04 UTC 2026)

Worktree `S/wt-harn2`, branch `audit/harn2`, 3 commits on `767f0d79`, one per item, not pushed. The runner copy was edited in place (pristine copy for the diff: `S/harn2_ds/round1.sh.orig`). None of items 1-3 can be pinned host-side: each depends on silicon (line levels, PWR_CTRL retention, erase time) that the twin does not model, so it passes or fails the same way before and after the change.
1. `eab1caf8` +4/-2. `_stuck_errno` repeats `_pick`'s one-byte pointer write, which goes through the controller. Confirmed in v1.29.0: `ports/rp2/machine_i2c.c:127-145` sends a zero-length write through soft I2C. Its `mp_hal_i2c_start` never reads SDA, and its ACK read (`extmod/machine_i2c.c:141`) takes SDA held low as an ACK, so the probe read None. With one byte it goes through `i2c_write_timeout_us`: lost arbitration, a NACK or a stuck STOP each give EIO or ETIMEDOUT (pico-sdk `i2c.c:218-235`, plus the wrapper's short-count EIO). Not a read: on dev the held chip is the BMP3xx (i2c0's only device). A read returns the byte at the chip's current pointer, and the hold's clocks can leave that pointer on ERR_REG, whose cmd_err/conf_err bits clear on read (BMP388 sec 4.3.2). The pointer write changes nothing `_pick` had not already done. Not tried on the board.
2. `dae3a601` +3/-0. One forced read now comes before `before`. Confirmed from the datasheet: when a forced conversion finishes, only the mode returns to sleep (BMP388 sec 3.3.2). PWR_CTRL's reset value is 0x00, and every read writes 0x13 (`asy_bmp3xx_driver.py:459`), so it reads 0, then 3, with no general call involved. The same run's chip conformance read 03.
3. `1cf37894` +4/-2. The wait first idles until `stop[0]` is set, which happens with the `reset` fact once the wrapped `_reboot()` has armed the reset, and only then counts its 16 s. Confirmed from the code: `_request_shutdown()` answers as soon as the shutdown task exists (`asy_system_service.py:379`). The erase runs inside that task, and `_reboot()` arms the 4 s one-shot after it. With the bench's 16,370-16,529 ms erases, a wait counted from the answer ends before the reset, which matches the order of the facts. `test_fram_erase_racing…` runs the same script (STATE loads), so it gets the same fix. I could only infer its `erase None`: I have no output from that run.
4. `round1.sh` +10/-4. After a successful `picotool load -x`, a new `kick()` makes `BenchBridge().kick_all_stations()`, the call `kick_after_reset()` makes. The board left USB at the bootloader step, so the old image cannot rejoin; a failed kick is printed and `flash()` still returns 0. `FLASHED_S=720` is the `/system` wait after a flash in `final_image()`, `gc_image()` and rollover's fallback. Item 12 measured 9 min 17 s (16:29:41 to 16:38:58). The test is a stubbed dry run of `flash()` (picotool, mpremote, uv and sleep stubbed). The original copy loads with no kick after it: red. The new copy kicks after the load and returns 0 also when the kick fails: green. The kick's snippet compiles and imports `BenchBridge`; nothing was called. shellcheck is clean (`harn2_round1sh.log`).
5. No change: the code does not show that the reset was ours and made the probe fail.
   - Before `is_reachable()`, a session start touches the board only passively. The runner does its uv sync and creates the evidence directory. `pytest_configure` exports BENCH_DEVICE, and collection imports nothing that touches a board. `Board()` resolves the by-id node. `is_device_present()` opens and closes the port at 115200 without writing a byte, so it is not the 1200-baud touch.
   - `is_reachable()` itself sends mpremote's Ctrl-C (`transport_serial.py:179`). That ends main.py through the boot entry's KeyboardInterrupt clause, which writes code 21 (`buildgen/codegen.py:857-861`). The raw-REPL soft reset keeps the armed watchdog and does not re-run main.py (`ports/rp2/main.c:246-247`), so the watchdog resets the board 6-8 s after the Ctrl-C: the supervisor feeds every 2 s (`_TASK_CHECK_TIME`) and the watchdog fires after 8 s. That reset is ours, and it happens at every real session start.
   - The probe's exchange normally takes 0.4 s, so that reset cannot fail it unless the exchange runs past 6 s.
   - The flash tier's board fixture needs only USB, so nothing waits for the network, and after a failed probe nothing acts at all.
   - The skip message is the same whether `is_device_present()` or `is_reachable()` failed, and `is_reachable()` discards mpremote's output, so the log cannot say which failed.
   - Reading the reset reason: 21 means our Ctrl-C landed and the probe failed for another reason; any other code means the product reset by itself and the probe met its USB re-enumeration.

Checks (6 runs, the twin run with the heavy slot taken and released):
- Rebuild, then `lint_direct` rc 0.
- mypy main, host and twin: clean (276, 312 and 59 files); the link was removed.
- `test_comment_block_cap.py`, `test_citations.py`, `test_device_script_watchdog.py` and `test_device_script_facts.py`: 676 passed.
- `tests_hardware --collect-only`: 234 collected, 203 selected, 31 deselected.
- One twin run of the 6 affected flash tests (`harn2_twin.log`): 5 passed, no `MemoryError` or "memory allocation failed". `test_a_held_sda_line…` failed at `held` False, an assertion that comes before `stuck_errno`: the twin models no line levels (BACKLOG). It is (c) other and fails the same way before the change.

Decisions (agent, 2026-11-05):
- The pointer write rather than a read (item 1).
- Rollover's after-flash read also gets `FLASHED_S` (item 12 names that fallback).
- 720 s.

Finding (c), read, not pursued: `session_start_evidence()` saves `/status` after the board fixture's probe has already ended main.py. Whatever it reads therefore comes from the reboot that probe causes, not from the state before the session, so the in-RAM ResetReason its comment protects is already gone.

nothing of mine is running
