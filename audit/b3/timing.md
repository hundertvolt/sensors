# Timing per level and GC stage (A.U35.23, A.U35.15, OR141.a (5), M.PROC.024)

Requirement: per level and GC stage the wall clock, peak RSS, host SSD writes and test counts, in B0, post-refresh (M.PROC.007/.012) and post-B3 columns (A.U35.23); the NTP loopback confirmation runs (A.U35.15); the UDP idle poll's twin measurement (OR141.a (5)); the 2**30 tick-wrap build's runs (M.PROC.024). Completion: every column filled from a gate log, every file more than 10 % slower made efficient. A defect any file records goes the OR12.a path (fixed with a regression test seen failing first, or an owner question), never a note alone, and passes A-C as a delta before it is applied (OR106.a). The file is complete when every row is terminal: biting, fixed, or justified with its reason. Opened by A.U35.01 / M.PROC.022 (agent, 2026-10-22); deleted with `audit/` at phase D.

| level | stage | wall clock | peak RSS | host SSD writes | tests | source log |
|---|---|---|---|---|---|---|

## The 2**30 tick-wrap build (M.PROC.024, A.U35.32)

`audit/sweeps/ticks30_build.sh build <scratch>` copies the pinned checkout (`/root/pico-toolchain/micropython`, v1.29.0,
read only) into the scratchpad, renames the Unix port's `mp_hal_ticks_ms()`/`mp_hal_ticks_us()` and wraps them with
one fixed offset each, read once from `TICKS30_WRAP_IN_MS`, and builds `build-ticks30` with the rig's own overrides
(`apply_unix_kbd_intr_override()`, both verified compiled in) plus `CFLAGS_EXTRA=-DMICROPY_PY_TIME_TICKS_PERIOD=1073741824`.
The literal is `(1<<30)`'s value, so make's shell needs no quoting (agent, 2026-10-22). The shared toolchain build is
never touched. Its self-check (`check`): `ticks_add(0, -1) + 1 == 2**30`, and with the wrap 1500 ms out both counters
cross it (`1073740324 -> 102 ms; 1072241825 -> 101775 us`).

**OF-32 (R-30), real clock.** `ticks30_build.sh probe <scratch> <tree> 600`: one twin `UARTLink` (dev's two UARTs),
the raw counters wrapping 300 s in, a byte every 100 s, then a 40-byte burst into a 5.2 ms flash stall, all through
the link's own wire time.

| tree | byte at 0-500 s | byte at 600 s (past 2**29 us) | stall burst at 0 s / 600 s | verdict |
|---|---|---|---|---|
| base `f3fff0e` | arrived | never arrived (`None`) | 32 kept, 8 lost / 0 kept, 0 lost | FAIL: OF-32 trips |
| lane Y final `5cf361c` | arrived | arrived | 32/8 / 32/8 | PASS |
| lane V `8edb5aa` (holds Y's fix and V's flash-stall fix) | arrived | arrived | 32/8 / 32/8 | PASS |

**The wrap tests on lane V's head (`8edb5aa`), on the 2**30 build**, the wrap at a quarter, half and three quarters
of each file's wall clock, both GC stages: `tests/test_ticks_rollover.py` (V's flash-stall wrap test) 23/23 at 950,
1900 and 2850 ms, 3.76-3.82 s each; `tests/test_digital_twin_machine.py` (Y's two link tests) 112/112 at 330, 660 and
1000 ms, 1.15-1.18 s each. Zero memory markers in any of the 12 logs. Both files' new tests drive `tests/_ticks30.py`'s
clock; the build adds a real counter wrap under the rest of each file.

Not exercised: a stall window straddling the 2**29 us alias (Y's finding at `digital_twin/_flash_stall.py:98`, fixed
by V's (start, length) windows) and a window exactly 2**30 us old (V's residual, `digital_twin/machine.py:937`).
Left to B2 (agent, 2026-10-22): M.PROC.024 (1), every L1 file using ticks, and (2), the twin suite per device with the
wrap inside Run 11's window; both need this file's measured wall clocks and Run 11's calibration.
