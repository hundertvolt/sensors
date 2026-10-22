T2b hand-back (lane T, branch audit/u35-t, worktree S/wt-u35t). One commit: f9569b9, on ecac120. Nothing uncommitted.

**Steps**
- **157 (1), applied.** Run 11's window is now the twin log's byte size before and after the measured cycles. Its samples are the MEM_SAMPLE lines that start in [start, end). `_parse_mem_samples(log: bytes, base=0)` returns (byte offset, free); a malformed line and an unterminated last line are skipped. New `_mem_samples_from()`. The warm-up reads from byte offsets too, and the `log_from` import is gone from the suite (`_twin_process`/scenarios still use it).
- **157 (2), applied.** The runner prints `MEM_SAMPLE {time.ticks_ms()} ...`. 157 (3) was not touched (the collect, its comment and checker row stay for B2, R-22). 157 (4) is T4's.
- **164, applied.** Six offset cases: byte offsets past a non-ASCII line, a base, a backwards stamp, never armed, malformed or old float stamp, unterminated tail. Plus a soak whose host clock and stamps step back an hour mid-cycles; it must select exactly the measured cycles' samples. The stub stamps are now ticks-like ints.
- **160, applied.** Run 3 checks the shutdown line's `fram_writes` <= window / 627 ms x 2. The window is spawn to exit on the host's monotonic clock. `_PERSISTED_LOG_CHUNK_WRITE_MS = 627` has no tag (rate.persisted_log is a C/F row, not Part N). The bound is stated beside the assertion.

**Seen failing and bites** (logs in S/u35/laneT/)
- On ecac120's suite, 9 cases failed (t2b_seen_failing.log). The backwards-clock soak gave "enough MEM_SAMPLE lines ... (0 samples)". The parse cases raised TypeError (bytes into the old str parser).
- Bite A, newline rule removed: `[(0, 1355680), (24, 13)] == [(0, 1355680)]`. Bite C, character offsets: `(99,…)/(100,…)`. Both are in t2b_bites.log; the suite was restored and checked with cmp.
- 160 plant, Run 3 over stubs (scratch S/u35/laneT/t2b_plant/run3_plant.py, not committed), 1300 ms window, ceiling 4: fram_writes=4 passes; fram_writes=5 gives "FAIL: Run 3: the FRAM chip's 5 writes stay within the persisted-log rate, 4 over the 1300 ms run".

**Finding (new, for the lead; class 3, twin/tooling mode, every device)**
- Run 3's rate check passes whatever the product writes during the storm. Run 3 faults `fram:silent` on every device, and `digital_twin/_fram_chip.py:287` returns before `_count_write` while the chip is silent.
- Real dev Run 3 read `fram_writes=0` at both stages ("0 writes ... 24 over the 7563 ms run").
- Proposed fix: the chip counts writes issued while silent and the runner prints that count. `_fram_chip.py` is P's file (LEAD NOTES 2a), so this needs routing. The relay line states the caveat.

**Relay lines written:** one under `## B`: the load.md entry (gap, load, limit, degradation, recovery, plus the silent caveat).

**Runs** (all rc=0, mem=0)
- t2b_readers.sh (pid 32456): ruff, host and twin mypy (0 errors), and the 12 checks plus gc_collect_sites (861 passed). Then 22 readers paired base (S/wt-u35base) / head, all flat; soak 0.78/0.65 s (24 cases); rgi 1.43/1.46 s at -1 and 1.51/1.47 s at 32768. run_digital_twin_ci_sh read 5.32/6.75 once; re-paired back to back it read 4.82/4.88 and 5.19/5.49, so that was host noise.
- t2b_twin.sh (pid 5034), dev `--only 3,11`, base = ecac120's suite and runner swapped in (T2a's precedent): -1 139.7/155.0 s, 32768 105.7/197.2 s; 0 FAIL lines. Tree rebuilt after (rebuild.sh f9569b9, all six devices).
  - Per soak request the time is flat (0.238/0.236 s and 0.248/0.235 s). The gap is Run 11's adaptive warm-up: 64/74 and 41/100 cycles.
  - The floor analysis shows base and head alike: about 90 new floors per run, the last at 35-92 % of the run, so one deep dip resets the plateau. That is for B2's calibration, not a change of mine.
  - Added time from this block: none. Run 3's check adds no boot (one monotonic read and one log parse).
- RUNS.md has start and done lines for both. The raw Run 11 logs were deleted after the summary; the Run 3 logs and .out files are kept (192K).

**Decisions (agent, 2026-10-21)**
- (1) An unterminated last line and a non-integer stamp are no sample. A partial line's digits would read as a smaller free count.
- (2) The warm-up uses byte offsets too, so only one offset unit is left.
- (3) Run 3's window is spawn to exit on the host's monotonic clock.

**Owed**
- T4: README :332 and :780 `MEM_SAMPLE <time.time()>` → `<time.ticks_ms()>`; a Run 11 sentence that the window is a byte span of the log; Run 3's FRAM ceiling.
- D: SPEC E.9's window sentence; rate.persisted_log (SPEC:6438) now has Run 3 as a reader.

**Not done:** no allow-list row orphaned, no red checks. Run 3's rate check has no committed L0 case, because the matrix and errcount files are outside this block's set; it could go to T3 or T4.

**T3 starts** from f9569b9 in S/wt-u35t: rebuilt, clean, branch audit/u35-t.

Nothing of mine is running.
