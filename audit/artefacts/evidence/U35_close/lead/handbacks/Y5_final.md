Y5 hand-back (lane Y, last block). Branch audit/u35-y in S/wt-u35y, head **5cf361c** (on e1fc497). Nothing is uncommitted, nothing is pushed, and nothing of mine is running. I made about 72 tool calls.

**Commits and verdicts**
- d6f34ab, asy_system_service: **cleared**. The starters and slots use TaskStarter/Task[None] (LEAD NOTES 15), and the module leaves pyproject's list and `_RESIDUAL`. The stale :228 comment is replaced by a correct one-line comment, so the line count is unchanged. mpy-cross: 11289 → 11263 bytes. The only change is the dropped `Any` in the `if TYPE_CHECKING:` import, which never runs on the device: a probe that restores that import is byte-identical to the base (S/u35/laneY/y5/mpy/). So it is not fully byte-identical. Dropping an unused import was the clean form (agent, 2026-10-21). Two annotations are unquoted because code_conventions refuses quoted runtime names. Annotations have no effect on the bytes.
- 69135de, test_asy_uart_driver: **cleared**, 23 lines. It uses Unpack TypedDicts (UART, the reads, DMA.config), `**int`, rp2.DMA, CoroutineOf, and the TYPE_CHECKING overload form for `__getitem__`. It also adds two narrowing asserts before a wrapper that already failed on None. Its baseline line, ANN401 entry and `_RESIDUAL` row are gone.
- 1e4df91, test_asy_uart_comm: **25 of 26 lines cleared; the module stays listed with 1 site** at :177, `params: dict[str, Any]` in `_make_comm()`. mypy does not follow a TypedDict pop, so the rest forwarded into UARTComm needs Any, a cast, or a copy of UARTComm's and transfer_limits' defaults (agent, 2026-10-21).
  - `_make_comm` now takes `Unpack[_CommKw]`, so every caller is checked. payload_size and timeout are typed `object`, because the validation tests pass bad values on purpose.
  - fail_write_after's fake is now machine.UART. Its `no-any-return` ignore is gone and the write swap takes the standard `method-assign` ignore (net zero; agent, 2026-10-21).
  - The last ANN401 entry and its stale comment ("Unpack[TypedDict] is unavailable") are removed.
- 5cf361c: blank lines only (`git diff --ignore-blank-lines` is empty), 36 sites in both UART files. This covers LEAD NOTES 25's two sites. The others were the same consistency defect: ruff preview E30x showed single blank lines and runs of 3-4.

**Baseline now**
- main pass, 5: _boot_contiguity_probe, _sensortask_scenarios, _uart_link_contract, machine, test_asy_uart_comm.
- twin pass: machine. host pass: scripts._hardware_verdict.
- ANN401 left: tests/machine.py and digital_twin/machine.py.

**LEAD NOTES 30 residual: handed to the lead (both files needed).**
- Neither stall file can match a time across the wrap, so digital_twin/machine.py:937 (`_stall_offset_us = ticks_diff(us, EPOCH_US) - _wire_us`) cannot fix it alone:
  - V's fb9c0e1 `irqs_were_off` uses `ticks_diff(at_us, start)`, which masks its arguments to the period. Any time, bounded or not, then aliases one period later.
  - The current tree compares `start <= at_us < end` with start and end from ticks_diff. An unbounded time from machine.py would then miss every window recorded after 2**29 µs.
- The fix needs windows stored in unbounded µs with a plain comparison (V's file), plus :937 passing unbounded time. I wrote no test, because no fix landed.

**Seen failing:** none. These are pure migrations; the proof is the three mypy passes, mypy_any_baseline and ruff_exemptions_live.

**Checks (final, on the head)**
- lint.sh rc=0 (5.1 s). typecheck.sh cold rc=0, 6 Success (22.7 s).
- 17 scans: 876 passed, 1 failed.
- Readers: 34 files plus the 12 commit checks, all green.
- The only red, in the 12 checks and the scans: `tests/test_bus_hazard_multi_device.py:71: l1.bus_fault_isolation_bound_s is tagged but has no SPECIFICATION.md Part N row`. It waits on D.
- Zero MemoryError and zero "memory allocation failed" in every log.
- Silent-failure scan: nothing new (no new handler or fallback).
- Effect per mode: none in STA, AP, Silent, Off or USB, on any device.

**Times (head, -1/32768)**
- driver: 5.63/9.34, 166/166. U1 had 5.67/9.30 (later 5.59/9.09).
- comm: 62.16/63.22, 201/201. U32 had 61.39/62.22, U1 62.34/63.67.
- Neither is over 10 %. I did not re-run after the blank-line commit (whitespace only).

**Runs**
- run2.sh drv pid 2519 rc=0; run2.sh comm pid 9061 rc=0; final.sh pid 11324 rc=0. All have RUNS.md lines.
- Deviation: three foreground readers.sh runs of about 63-75 s got no RUNS.md lines.
- Logs: S/u35/laneY/y5/ (t_drv, t_comm, final, r_*, mpy).

**Relay:** none written. The worktree still holds the gitignored .venv and typings/. I left them for the lead's W6 edit to tests/machine.py:598 (agent, 2026-10-21); remove them with literal paths afterwards.