# N9: the hardware tests' reads of the running firmware keep its interpreter (lead, 2026-10-26)
Read `S/u35r/briefs/redo_common.md` first. Worktree `S/wt-u35n9`, branch `audit/u35-n9`, base f3fb02c0 (the int head
with F4e merged, rebuilt). Logs in `S/u35/laneN/n9/`. Test and tool text only: no `src/`, no generated file, no wear.

## The finding (lane F4e's sweep, re-checked by the lead in the pinned v1.29.0 source; prove it again yourself)
`Board.exec()` (tests_hardware/harness.py, `mpremote connect <dev> exec <expr>`) enters the raw REPL with mpremote's
auto soft reset (tools/mpremote/mpremote/main.py `State.ensure_raw_repl`, `_auto_soft_reset = True`;
transport_serial.py `enter_raw_repl(soft_reset=True)`: Ctrl-C, Ctrl-A, Ctrl-D). The raw REPL's Ctrl-D goes to
ports/rp2/main.c's `soft_reset_exit` and `mp_deinit()`, then `mp_init()`: `sys.modules` is empty. Every snippet that
reads the running firmware through `sys.modules` (`sensortask_*` with a `sysfunct`) therefore reads nothing on silicon:
- tests_hardware/flash/test_system_commands.py `_READ_AFTER_BOOT` / `_after_boot()` (six callers): "AFTER null";
- tests_hardware/error_log_helpers.py `_READ_SYSTEM_LOG` / `read_live_system_log()`: its callers
  flash/test_bus_concurrency.py `_after_boot_band()` and flash/test_memory_stress.py's soak (before and after);
- tests_hardware/manual/manual_persistence.py `_READ_REASON` (`test_power_loss_during_the_shutdown_commands`).
Their comments assume the opposite ("an exec parks main.py"). The twin cannot see it: `TwinBoard.exec()` runs a fresh
process (right for silicon's default exec), and the twin skips those after-boot halves. Find by search, not this list,
every other site that reads live firmware state through `exec()`/`run_isolated()`; README.md's "Does mpremote's
implicit soft-reset re-execute ...main.py?" entry (around :1144) is the harness's own statement of the same fact.

## The fix (lead's decision under CHECKLIST 1d: test-only, no wear, restores coverage the hardware round needs)
1. `Board.exec_live(expr, timeout_s=None)`: `mpremote connect <dev> resume exec <expr>` (docs/reference/mpremote.rst's
   `resume`, :127-136: no auto soft reset). Its Ctrl-C ends main.py through the boot entry's KeyboardInterrupt
   clause (build/generated_src/sensortask_<device>_main.py: records 21, re-raises; its `finally` runs
   `asyncio.new_event_loop()`, so the dead loop's tasks cannot resume under the read's `asyncio.run()`), and the
   friendly REPL keeps every module. State in its comment, from the source, what the board does after it: nothing
   feeds the armed watchdog, so the board resets on its own, cause WDT, record 21, within one watchdog period of the
   firmware's last feed; the read must finish inside that window (bound it; check the existing harness timeout
   constants for one to reuse before adding a tagged `l4.harness_*` one with its Part N row).
   Check `_mpremote()`'s retry and recovery paths for what a retried `resume exec` meets, and say it.
2. `TwinBoard.exec_live()` refuses with `HardwareNotAvailableError` and the reason (the twin keeps no live interpreter
   across runs); never a silent fallback to `exec()`.
3. Every live read found moves to `exec_live()`; the comments state the real mechanism. Each caller's flow after the
   read checked: what resets the board next, and whether anything later asserts a reset reason the read's 21 changes.
4. A structural check in tests_scripts (the smallest home among the existing tests_hardware harness checks): every
   snippet in tests_hardware that reads `sys.modules` for the running firmware reaches the board only through
   `exec_live()`; seen red first on today's tree, and on a scratch copy with one site moved back.
5. Unit tests (tests_scripts, the existing harness tests' style, no device): `exec_live` builds `resume` before `exec`
   and plain `exec` does not; the twin refusal; each red first.
6. tests_hardware/README.md: the soft-reset entry states both paths (`exec()` soft-resets and reads a fresh
   interpreter; `exec_live()` keeps the parked firmware, then the watchdog resets it).

## Rules for this lane
Never run mpremote, picotool or any tests_hardware test except with `--collect-only` or `--twin`; never against a
board; if a safety classifier or permission check refuses a command, stop and hand back, never retry it another way.
Prove the mpremote and rp2 behaviour by reading the pinned source in `/root/pico-toolchain/micropython` (read-only).

## Proof and checks
`--collect-only` of the whole tests_hardware tier inside `unshare -n S/u24/ns_xdg.sh`, nice 19, RUNS.md lines; the
changed flash files with `--twin`; ruff, the host mypy pass and the main pass's device_scripts (stubs at
`S/shared/typings`), the comment cap, test_citations, test_decision_vocabulary, test_tunables_register,
test_exception_handler_contract (it lists `read_live_system_log` in `_LOG_READS`), and every tests_scripts reader of a
changed file. test_twin_record stays red for changed tests_hardware files (the lead re-records at the close): name any
other red. Your base has a changed `toolchain/`: no scripts/test.sh, no twin CI against the shared toolchain.

## Not yours
src/, toolchain/, digital_twin/, audit/ records, every allow-list (hand back the row you need). Commit subject
`U35 lane N9: <summary>`, the two trailers; do not push. Hand-back: commits; every site found (path:line, what it read,
its fix); the source lines proving both mpremote paths; each red and green with log paths; the silent-failure scan of
your diff (a fallback that hides a failure, a check that passes vacuously); last line "nothing of mine is running".
