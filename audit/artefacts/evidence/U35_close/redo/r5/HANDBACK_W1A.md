W1a hand-back, written by the agent (Tue Nov 10 17:47 UTC 2026)
Commit b5f2978c on audit/w1a (S/wt-w1a, from 651af010), not pushed: 66 files, +535/-795; src/, ext/, devices/, generated modules untouched.
1 B01: 17 explicit Any typed, all 3 baselines gone (main 12: tests/machine.py 7, _boot_contiguity_probe 2, _uart_link_contract,
  test_asy_uart_comm, _sensortask_scenarios; host 1: _hardware_verdict; twin 4: digital_twin/machine.py). The unit fake's _CallLog is
  generic, one entry union per bus fake (mypy 2.4 narrows it by entry[0] == op); mem_backup overloads; DMA typed; twin I2C.devices a
  union of its 4 chip fakes (one ignore where the bus calls them as _I2CDevice: each answers its own subset); fan-in a Protocol +
  TypeGuard; _make_comm explicit keywords (its never-passed message_callback dropped; 2 calls passing non-ints on purpose carry
  arg-type ignores); verdict imports scripts._summary_block; ~30 test sites narrowed (5 compare the whole entry now). Red: 17 mypy
  errors without the baselines, then green in all 3 passes. test_mypy_any_baseline: flag check, no exemption, a planted test.
2 U02/S04: _PENDING 68 -> 0: 67 to module level; the twin-machine fixture loads via the named script loader (path-scoped; no new F.1
  entry). Gone with the list: _regenerate and its 2 tests (pending_list_only_shrinks, regenerate_keeps_...). PLC0415 ignores for
  tests/** and tests_scripts/** gone (ruff --select PLC0415 clean, every scope). _NOT_YET_CLEANED 4 -> 1; 2 vocabulary entries gone.
3 H01: LISTENER_DRAIN_S 5 s and _STALL_DRAIN_S 1 s (agent, 2026-10-27) go: a declared stall is cancelled once the call returned (drain 0
  probe: 547 UART tests green). H02: hazard's 5 caught wait_for(5 s) + silent cancel -> await after clear(), which unsticks it (a
  planted raise on that timeout never fired, 123/123 at both stages); NTP's 9 -> 7 flag-level reads, 2 plain awaits (0.2/0.05 s gone).
  H03 NOT changed: _ESCALATION_WAIT_S 120 s has no src-only source: 4 task ends (_TASK_FAIL_MAX // _TASK_FAIL_INCREMENT + 1), the first
  after max_module_error + 1 failed cycles at the reader's period, each later one a read after its restart (the streak survives it),
  then _RESET_DELAY; per driver and device; dev ~15-20 s (feed_count 14). Other twin waits (30-90 s) unchanged. Lead: derive or name.
Removed, code at 651af010: the 3 Any baselines and residual/exists tests, ANN401 x2, _PENDING + _regenerate + 2 tests, PLC0415 x2, the
  4 bounds above, the twin's _ASYNCIO_CORE global (a per-call lookup), the helper copies; all superseded as stated, none a catcher.
4 H04/H05: _cycle x4 -> tests/_notification_cycle.py; crc8 x4 (3 named + _bus_hazard_catalog's) -> fakes/_crc8.py, moved from
  digital_twin/ so both tiers read one; _REPORT x6 -> _shared/unretrieved.py, test_exception_handler_contract resolving a _shared
  include (planted test added). 5 H12: one device per hardware_family: smoke booted arzi, dev, grkizi, wozi, 8/8. H27: plain form.
6 B37: twin SGP40 times every transfer out until 528 ms after an unknown command (bench, dev 2026-10-29); test red (no clock), green,
  red on a planted 527; fidelity row fixed; BACKLOG item gone; _sgp40_chip joins _KNOWN_TICKS_USERS.
7 F3 cause (twin, not src): its walk draws from `random`, which the Unix port seeds from the OS at import (variants/mpconfigvariant_
  common.h:66; 3 launches, 3 first draws), so every run draws its own walk and the GC stage never enters it; the frozen check fails
  when the walk leaves the integer index flat (R0 21/300). 20/20 green at -1 and at 32768 here: R3's 2/15 was chance. Fix: last round.
8 B27 twin half (host, 2 runs/stage): 10.0 idle rounds/s at both stages, 5-6 us per ipoll(0), loop share under +-4 % noise, first query
  after a silence median 65 ms, max 100.4 ms: in Part N's udp.poll_idle_ms Basis.
Gate (tc-c, heavy.lock as w1a): test.sh -1 PASS (120 files, 5252 tests, tests_scripts 6547) and 32768 PASS (120, 5252), clean
  reruns; dev twin suite 327+13 and harness PASS at both; npm lint/typecheck/test:unit PASS; touched files at -1/32768/cov: 84 runs
  green, 0 MemoryError; lint_direct rc 0; mypy 285/309/58 clean; tests_hardware --collect-only 210/250. Sizes: src/ and frozen
  inputs untouched, so bytecode and imageFreeBytes unchanged (not rebuilt); cost: the twin SGP40 tests one field per transfer.
For W2: CLAUDE.md:687-688 names the Any baseline as BACKLOG's open item; BACKLOG:111-118 (B27) owes the bench half only. Decisions
  (agent, 2026-11-10): entry unions over tuple[object, ...]; cancel at once over a sourced drain; crc8 into fakes/.
Findings: (c) dev scenario uart_ring_under_concurrent_load, 32768: "config PUTs under load answered []" 1 of 8 alone here, 0 of 5 on
  int 77a4e1e8, green in the clean gate (the flusher lost every slot to the hammer); not pursued. Off-list sibling: test_asy_uart_comm
  :2698's caught wait_for(10 s). Slips: my file batch and 3 twin VOC runs overlapped pin's lock (16:01-16:12); I ran ruff/mypy during
  my own gate's 32768 stage (checkout check red): both stages rerun clean.
