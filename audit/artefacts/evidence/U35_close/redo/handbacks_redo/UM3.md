UM3 hand-back, written by the lane (2026-10-27)

**Commits** on audit/u35-um1 in S/wt-u35um1, oldest first. Not pushed. Nothing uncommitted except the linked node_modules (and UM2's gitignored typings/, identical to S/shared/typings, left as found).
- 52906bb8: item 1, merge of 158058ed.
- 2f8122c1: item 2, read_at()'s verdicts, the merged tree's verdict lines, U17's cells, review.md.
- 8c506e95: the lead's settle() input, red first (twin fix).
- c570ba76: review.md row for that test.

Item 3 (the CRC16 red): root cause established with evidence, **fix not made: it needs your decision** (below). Logs: S/u35/laneB/um3/ (crc/ holds every probe run's JSON line and twin output; runs.txt).

## 1. The merge (52906bb8)
Conflicts, each resolved by its tool:
- **audit/b3/e51.md**: the integration's side taken, then re-rendered by raising_walk.py (its block) and e51_sweep.py --render.
- **audit/sweeps/e51_hits.json**: per file, the side that changed it. For asy_base_classes.py (both sides) and the three UART modules, a fresh dump: all 128 tests/test_*.py jobs under build-settrace + _coverage_runner.py, PER_DEVICE on all six devices, all rc 0, zero memory markers, no tracer cut short.
  - Against each side's hits mapped over equal blocks, no line is lost.
  - Added: read_at()'s lines, BR4's edited try line (:517), and 40 UART lines UM2's carried-over hits had missed.
- **e51_verdicts.json**: the 23 "covered" verdicts whose sites the fresh dump covers were removed (BR4's convention). One of them carried UM2's broken ranges (":669-666, :673-670, :684-681").
- Auto-merged with no overlapping hunks: src/asy_base_classes.py, tests/test_asy_base_classes.py, SPECIFICATION.md. raising.md re-rendered.
- Green at the commit: walk, e51 (--check, --self-test), review_rows; lint_direct.

## 2. Verdicts (2f8122c1)
- **read_at()'s seven open rows were the only open rows.**
  - len (:206, :210, :212 ×2) and min (:212): unreachable.
  - divmod (:208) and memoryview (:213): handled, small fixed allocations in the responder listen loop, whose except Exception at asy_uart_comm.py:569 catches them.
  - The walk now reads handled 594, unreachable 543, defect 3, nothing open.
- **"Any other" rows:**
  - PieceBuffer.__init__::bytearray still said no caller catches. It is restated for the owner's catch.
  - conformance_walk.py's U17 R1/R5/R6 cells stood "pending owner" on the PieceBuffer catch. Now R1 is the failed frame, with UM2's two ALLOC tests in L1, and R5/R6 no longer list it as a task end. conformance.md and queue_c.md were re-rendered.
- **Line citations the merge moved** (mapped over equal blocks, then read on the tree):
  - 85 refs in asy_base_classes.json: +15 past :203.
  - asy_config_manager.json :803/:809 → :818/:824; asy_print_log.json :411 → :426.
  - UART :974/:1111 → :988/:1125.
  - The walk's debug keys → :519/:700.
- **Two refs BR4's own re-location missed**, read where they were written:
  - the conventions' eight except clauses, now :464, :479, :510, :520, :548, :574, :686, :701;
  - _rearm_timer's _trigger_loop call, now :737.
- **review.md** re-rendered: UM2's six tests (and later my settle test) are rows, biting with no flag.

## 3. The CRC16 red
**Reproduced, with the exact signature.** Probe: the test's own flow N times, plus a /status errcount read after its two reads (probe file planted, never committed, removed). Load = the twin and K busy loops pinned to one CPU, all nice 19.

| tree | stage | idle host | loaded (K=3) |
|---|---|---|---|
| head | 32768 | 0/32 red | 8/75 red |
| head | -1 | 0/22 | 0/20 |
| ad624cca (base) | 32768 | 0/20 | 0/30 (2 runs with E22 after the window) |
| ad624cca (base) | -1 | 0/20 | 2/20 (host load1 up to 6.3) |

Every red reads "Transfers (0, 0), Failures (0, 1)", with E81 (NO_ACK) logged at both ends.

**Not brought by UM2.** The base reproduces it. UM2's diff touches the banner GET path only with a try and isinstance checks.

**Root cause (timing).**
- The CRC engine yields once per byte (`await asyncio.sleep(0)` in asy_crc_checks.py _crc(); kept by owner ruling 2026-09-18, "pure wall clock time is not such an issue, don't touch", SPECIFICATION.md I.2/G.2).
- A CRC16 frame-with-ACK round trip runs four CRC passes over a 55-byte frame: about 220 event-loop rounds. On the booted dev twin each round waits behind every device task (about 2.7 ms).
- **Idle host, planted trace:** a round trip takes median 606 ms, max 843 ms at 32768 (567/786 at -1), against the protocol's fixed 1000 ms ACK timeout.
- **Under host contention**, the round trip passes 1 s:
  - the initiator logs "no ACK for frame 1";
  - the responder's unacknowledged answer header then logs "no ACK for frame 1";
  - the fault's resync (1.5 s quiet) + hold-off (1.5 s) + period (1 s) keep the next transfer outside the test's 3 s window.
  - The UART errors cluster at the test's own /status reads.
- Loop-lag reporter: no single loop stall above 0.28 s, so this is the accumulation of rounds, not one blocker.

**Bite.** A tmp_path copy of asy_crc_checks.py without the per-byte yield, same load: 0/23 red, round trip median 180 ms, max 257 ms, 4 transfers by the second read (about 1 with the yield). Control: the shipped no-CRC link under the same load: 0/20, 4 transfers. The CRC16 test passed in item 4's tier run.

**Fix: your decision.** The product fix contradicts an owner ruling, and the test fix narrows a check (CHECKLIST 4).
- (a) Product, owner question: the CRC yields per N bytes instead of per byte. Evidence: 220 rounds per round trip eat 60-85 % of the ACK budget on an idle twin. The same arithmetic applies on silicon. This is the root fix.
- (b) Test, lead: keep the static CRC16 wiring check. Require transfers to rise, which proves CRC16 frames validated both ways. Fail only on framing failures (read from the twin's printed UART error texts), not on load timeouts.
- (c) Hardware round: measure a CRC16 round trip on the dev bench under API load (silicon-only).
- My recommendation: (a) to the owner, with (c) to size N.

**The lead's settle() input (8c506e95).** Confirmed and fixed red-first. A planted stall after the first advance failed `assert not link.a_to_b.in_flight` (tests/test_digital_twin_machine_uart.py:199); with the fix the file is 26/26 at both stages. It does not explain the CRC16 red: settle() refuses a running loop, so no booted twin calls it.

## 4. Checks on the head (8c506e95; c570ba76 only re-rendered review.md)
- **Test files:** 47 files (direct importers of the four modules, the UART harness users, the twin UART files, test_sensortask), at -1 then 32768 one after the other. PER_DEVICE files (sensortask_integration, timer_pool, sensortask) on all six devices. **124/124 jobs rc 0, zero memory markers** (i4_both.log). The grown file test_digital_twin_machine_uart takes 4.3/4.6 s (+1 test, ~10 ms of sleep).
- **lint_direct** rc 0.
- **The six mypy passes** on a cold cache: rc 0.
- **The walk, e51 (--check, --self-test) and review_rows --check:** green (8570 rows).
- **The whole tests_scripts tier:** 6997 passed, **5 failed, the same five as the lead's own tier run on 158058ed** (mc_tier158). None is in my files or UM2's:
  - test_code_conventions member_order: src/asy_fram_manager.py _FRAMBaseChunk, `_handle_status_bytes` before `_copy_out`.
  - test_level_containment: twin scenarios held_i2c_line and setup_resets have neither an L3/L4 counterpart nor an E.6.6 row.
  - test_suppression_form: tests/test_digital_twin_sgp40.py:314 has `assignment,method-assign` without the space.
  - test_twin_record (×2): expected on src/runner changes; plus three F4 instruments with no record.

## For the lead
- **audit/trace/UART_PART_J.md:20** still says PieceBuffer "lets its MemoryError through (OR143.a, owner, 2026-10-05)". That is superseded by the owner's 2026-10-27 catch. Not my file; not edited.
- The five tier reds above wait on their owners.
- **Runs:** cov_merge rc 0 (2467 s); the CRC16 probe batches (crc_*), with burners killed by trap, none left; i4_both rc 0; i4_tier rc 1 (the five above); i4_lint, i4_mypy, i4_audit rc 0. My base worktree wt-u35um3base and its branch are removed.

nothing of mine is running
