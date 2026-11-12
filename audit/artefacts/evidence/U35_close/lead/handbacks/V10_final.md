V10 hand-back (lane V). Branch audit/u35-v10 in S/wt-u35v10, built on 1bb72a4. One commit: d1161ad, which changes only tests/_sensortask_scenarios.py. Nothing pushed, nothing uncommitted, no typings link. About 62 tool calls.

**Cost 1, the NAK storm's storm phase (applied).** I timed every method the storm reaches (scratch profiler `S/u35/laneV/v10/prof/prof_nak.py`). On dev at -1, 3.43 s of the scenario's 4.3 s sits in `IOQueue.wait_io_event()` (4156 calls). That is a real wait, not work. While any ThreadSafeFlag waits, the Unix port's poll() sleeps 1 ms on every scheduler round before it checks a non-fd pollable (extmod/modselect.c:353-370; POSIX_OPTIMISATIONS=1 in ports/unix/variants/mpconfigvariant_common.h:110). rp2 polls once with no sleep. V9's `_CountedFlag` was a ThreadSafeFlag, so all 7 passes paid that 1 ms per round.
- Fix: `_CountedFlag` keeps its state in an asyncio.Event. The semantics are unchanged: a wait consumes the set, and a set before the wait is kept. It is still a ThreadSafeFlag subclass, for the readers' annotation. A second waiter fails loudly, where the IO queue holds one waiter per stream (core.py:75-86). Every pass and assertion is kept.
- After: storm phase 3288 → 458 ms; poll time 3430 → 25 ms. NAK storm per device: dev 4121 → 732 ms (-1) and 4454 → 1012 ms (32768); wozi 2966 → 510 ms; arzi 1580 → 343 ms.
- What is left is real, irreducible work: the FRAM persistence of each storm entry (66 chunk writes = 660 `set_values_sync` writes, each with WREN, two status reads and WRDI; src/asy_fram_driver.py:356, :309).

**Cost 2, dev's extra growth at 32768 (root-caused; no cost beyond noise).**
- CPU time (user+sys), dev at 32768: base 28.86 and 30.70 s, head without the 3 new scenarios 30.69 and 30.84 s, head 32.22 and 32.80 s.
  - Two identical base runs differ by 1.84 s, so the skip-vs-base +0.99 s is within noise.
  - The new scenarios' CPU (head minus skip) is about 1.7 s.
  - Per-scenario wall-time deltas over the 102 common scenarios ranged from -0.5 s to +1.8 s across four pairs.
  - User CPU is only 29-32 s of 64-69 s wall time. The rest is waiting at nice 19 on the shared host, plus poll sleeps.
- Deterministic part: the live heap is 1.5-2 % larger, so each collection at 32768 marks that much more. It is real and comes from the file's own growth:
  - the module's own code adds 13.4 KB (698720 → 712096 B after import);
  - tests/_src_const.py's per-file constant cache (:8, :79) adds 8.3 KB once the new scenarios read their source files.

**Block K (applied).** The :477 block now measures TOTAL 0 at 120 (show.py) and keeps its 3 lines. One tightening was needed, since no 3-line rewrap fits: "or in a task it spawned" → "or a task it spawned", no meaning change.

**Paired times (s), vbase against the head, alternating:** every device is within +10 %.

| device | -1 | 32768 |
|---|---|---|
| arzi | 33.84→34.82 (+2.9 %) | 39.86→40.69 (+2.1 %) |
| dev | 53.63→55.28 (+3.1 %) | 65.84→67.13 (+2.0 %) |
| grkizi | 34.29→35.25 (+2.8 %) | 39.81→41.11 (+3.3 %) |
| klkizi | 34.38→34.97 (+1.7 %) | 39.90→41.19 (+3.2 %) |
| schlafzi | 34.32→34.94 (+1.8 %) | 39.58→41.67 (+5.3 %) |
| wozi | 38.78→39.55 (+2.0 %) | 45.14→46.94 (+4.0 %) |

- Base dev stops early at its known :3125 red.
- The final tree then ran all 12 files green, head only (fh_*.log). On dev, the three new scenarios now cost 1.79 s at 32768.

**Bites:**
- V8's p2 (`_rungs |= _RUNG_DEVICE` dropped) is red at :2511 on dev at -1 and at 32768.
- The new one-waiter check: with it planted off, a second waiter gets in and the probe never ends (rc 124). With the check on, the second waiter is refused.
- V9's b1-b4 were not re-run: the NTP scenario and its helpers are untouched (only line shifts).

**Checks on d1161ad:**
- ruff clean; all three mypy passes rc=0 (cold cache); D.15 shows only the known `@_register` line.
- The 12 checks, the 17 scans and the readers ran in one pytest process (c1): 1738 passed, 8 red, none naming my files. The reds are the known ones: tunables_register (asy_config_manager.py:74, twin uart_link:145), level_containment (4 twin scenarios), task_inventory ×4 (neopixel :144/:202, `UARTLinkDriver._two_initiations`), twin_record ×2 (expected).
- Zero MemoryError and zero "memory allocation failed" in every log.

**For the lead (not growth, not done):** the whole dev file spends 18.2 s of 56.3 s in the same 1 ms poll sleep (`S/u35/laneV/v10/pa_dev_-1.log`). The two biggest:
- `every_api_write_is_refused_from_a_system_commands_acceptance_to_its_reset`: 5.6 s of 8.9 s;
- `only_the_api_writes_the_scd30`: 4.4 s of 4.9 s.

**Decisions (agent, 2026-10-22):**
- The scenario's trigger stand-in is Event-backed, because the trigger mechanism is not what the storm checks.
- The one-waiter check is added, so the stand-in is no looser than the IO queue it replaces.

**Effect per mode:** tests only. STA, AP, Silent, Off and USB are unchanged on every device.

**Runs** (all with RUNS.md lines; logs in `S/u35/laneV/v10/`):
- profiles pn/pn2/pn3/f1p/fp;
- per-scenario pairs a1, ah2/ab2 and heap runs a2/hs/hq;
- CPU runs a3, p.sh (24 paired runs), a5 (lint, 12 head runs, bites, c1) and pa.
- I stopped a4.sh by its pid before its checks, because of a later edit. One probe that hung was killed by pid; it was a misdesigned ThreadSafeFlag case and is fixed.
- The scratch copies are deleted. Nothing of mine is running.