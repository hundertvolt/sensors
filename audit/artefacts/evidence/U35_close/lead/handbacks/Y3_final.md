Y3 hand-back (lane Y, block 3). Branch audit/u35-y in S/wt-u35y, head 949a68a (on the lead's 1089164). Nothing uncommitted, nothing pushed. I made 61 tool calls and stopped before R-15 because I could not finish it inside the 70-call valve.

**Steps**
- OF-32 (R-30): applied in 949a68a.
  - Change: UARTLink._now_us() re-anchors at every read. It adds the gap since its previous read: from ticks_us() up to `_US_GAP_MAX_MS` = 2**28 us, from ticks_ms() beyond that. So neither a long run nor an idle gap needs one ticks_diff() across 2**29 us.
  - `_stall_offset_us` (the attribute tests/test_digital_twin_machine_uart.py:119 reads) is recomputed at each anchor, in _flash_stall's own EPOCH_US coordinates.
  - The 2**30 build's confirmation is B1's <T30>.
- R-15 for test_asy_uart_comm (26 Any lines) and test_asy_uart_driver (23): not started; both stay listed. Sites: `grep -n '\bAny\b'` in each file (comm :149, :334, :696, ... :3287; driver :85, :148, :390, ... :2940).

**Seen failing first** (tests/test_digital_twin_machine.py, on tests/_ticks30.py's clock)
- Old code: "a byte sent 600000 ms into the link's life never arrived", and the stall test got (kept, dropped, OE) (0, 0, 0): 109/111.
- Bite 1, no ms guard: fails at 1400000 ms (the 700 s idle gap) and (0, 0, 0).
- Bite 2, stall offset frozen at construction: (40, 0, 0), "the burst missed the stall's window".
- Logs: S/u35/laneY/y3/{seen_failing,bite1,bite2}.log. The bite copies are deleted; nothing planted was committed.

**Checks:** ruff clean. Cold `scripts/typecheck.sh` rc=0 (21.4 s).
- The 12 commit checks: all green except test_tunables_register, red only on Y2's known `tests/test_bus_hazard_multi_device.py:71: l1.bus_fault_isolation_bound_s ... no Part N row` (it waits on D).
- Nine readers green (ticks_wrap_scan, fake_surface_conformance, twin_fake_catalog, counter_steps, twin_never_needs_tests_on_its_path, twin_wiring_contract, exception_handler_contract, gc_collect_sites, ruff_exemptions_live); suppression_form green after sorting my ignore codes.
- No allow-list row orphaned. No relay lines. Zero MemoryError and zero "memory allocation failed" in every log.

**Times (s, -1 / 32768)**
- twin machine, base/head paired: 1.17/1.22 and 1.19/1.21 (the head has 2 more tests).
- Head only: machine_uart 4.12/4.34 (25/25); integration[dev] 23.46/23.48 (4/12, 8 skipped, against U32's 22.95/23.65); uart_link 56.13/59.18 (20/20, against 55.35/59.39).
- Nothing over 10 %.

**Effect per mode:** twin fake only. No firmware, device module or wire byte changes; STA, AP, Silent, Off and USB are unchanged on every device. It only matters on a 2**30-period twin build running dev's link past about 9 min.

**Silent-failure scan:** one new finding, outside my set. Class 5, twin on a 2**30 build: digital_twin/_flash_stall.py:98 stores its windows as ticks_diff() from EPOCH_US. A stall straddling the 2**29 us wrap gets end < start, so it reads as empty. No lane holds that file, so this is for the lead to route.

**Decision (agent, 2026-10-21):** the ticks_ms() fallback above 2**28 us, rather than per-read accumulation alone, because bite 1 shows an idle link misreading without it.

**Facts for Y4**
- The ANN401 reason for both UART files (pyproject.toml:267-269, "Unpack[TypedDict] is unavailable") is stale for mypy. A scratch probe under the main pass, `**kwargs: "Unpack[_Kw]"` with typing_extensions.Unpack and a `total=False` TypedDict under TYPE_CHECKING, forwarded into a keyword-only callee and into print(), reported only the planted error.
- MicroPython rejects `{**kwargs}` in a dict display (SyntaxError), so the helper bodies keep `dict(kwargs)`.

**Baseline now:** main pass 7 (_boot_contiguity_probe, _sensortask_scenarios, _uart_link_contract, asy_system_service, machine, test_asy_uart_comm, test_asy_uart_driver); twin pass machine; host pass scripts._hardware_verdict.

**Y4's start:** head 949a68a; the R-15 UART files as above; step 114 per the plan. The worktree keeps its gitignored .venv and typings/.

Runs: batch1 (pid 24619, rc=0, logged in RUNS.md; its typecheck leg failed with rc=1 because no venv was activated, and was re-run by hand with rc=0). Nothing of mine is running.
