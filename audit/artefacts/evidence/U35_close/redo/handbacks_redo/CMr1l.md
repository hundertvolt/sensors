CMr1l hand-back, written by the lane (2026-10-27 17:40 UTC)

Worktree S/wt-u35cm3, branch audit/u35-cm3, base 562cf582. Logs, probes, bites in S/u35/laneC/cmr1l/ (times.txt,
load.txt; probe/, light/, bites/, bites2/, dbg/, final/). Every run went through one.sh / many.sh / files.sh /
round.sh / pyt.sh (namespace, nice 19, RUNS.md lines; 210 starts, 210 dones). One file changed:
tests/test_digital_twin_sensortask_integration.py. No src/, digital_twin/, SPEC or wait-value change. Not pushed.

## Commits
- `571fa38e` the supervised-death drift check runs on one driven clock, so every death reads the same heap.
- `bca66069` the widened Wi-Fi scenarios read the entries they persist back from WIFI's FRAM chunk.

## Item 1: the transients' cause (evidence)
Instrument (probe/_cmprobe.py, never committed): right after each of the floor's three reads, no await between, a walk
of the GC allocation table (HP2's layout, py/gc.c gc_setup_area, 32 B blocks on the 64-bit twin): every head typed by
its first word, generators by code_state.fun_bc, Tasks by coro; every stale child_last edge (child NULL, child_last
set, py/pairheap.h: pop() and init_node() never clear child_last) with its target's state; for a target, a scan of
every heap word, then of [stack] and the binary's static data, for a word pointing at it.
- **+416 B at CMr1j's death 7 (0-based 6) = (B)**: one cancelled twin-WDT countdown Task (64 B) with its coroutine
  (160), CancelledError (64), StopIteration (32), a BaseException-typed block (32) and two raw blocks (64): 416 B
  exactly, at u2_arzi_m1 death 6 r0, the only edge to a finished task at that read Timer._run's stale child_last ->
  that Task; gone the next death. The twin's WDT._arm() cancels and creates a countdown task per feed (110 a death).
  Across every real-clock probe run the only finished tasks seen pinned were WDT._countdown (74 reads).
- **+192 B at CMr1j's deaths 9-10 (0-based 8-9) = (A)**: the last `_wait_until` coroutine of the floor loop with its
  predicate closure and that closure's function: 128 + 32 + 32 = 192 B on 5a8c6e35's file (its coroutine is 160 B on
  562cf582, which added `clock=`: 224 B there). Kept by one stale C-stack word 176 B below the depth gc.collect() is
  called from (inside the collect's own frames, left by the await of `_wait_until` just before; 135 reads, depth
  5728 vs 5552 or 4848 vs 4672; 23 more found no such word left at the census's own depth); no heap word refers to it
  (u6: 17 of 17 reads); zeroing that one word and collecting frees its block (z1: 19 of 19 reads, block kind 0). Reproduced on CMr1j's int_base.py at 32768 (gbase_arzi_t_1-4:
  +192 B at reads of several deaths, gen[_wait_until] +128 B).
- (C) objects the real-clock tasks hold mid-cycle: a float +32 B at deaths 4, 5, 9, 10 (du_arzi_t_1); +96..+160 B in
  full-file runs; a +32 B step from death 7 on (du_arzi_m1_1) reads Theil-Sen 6.4 B.
- Neither the death record (fixed-size ring and two attributes) nor where a 32768 collection lands showed in any
  reading: (A), (B) and (C) occur at both stages.

## Item 1: the check's new form (571fa38e), measured basis, bites
The test's boot runs on one DrivenTime (`_driven`), the station link is awaited on it before the supervisor starts
(the supervisor's passes are a yield each, so the clock never settles under them: `_settle()` raises, dbg1), and the
deaths then pass no virtual time: every other task stays parked and each death runs the same instructions, so (A) and
(B) repeat identically and (C) is gone. Bound (32 B), window (deaths 4-10), Theil-Sen and _FLOOR_READS unchanged: no
lead decision needed. Comment of _DRIFT_SLOPE_BYTES restated with the new basis.
| form | healthy runs (six devices x both stages) | settled floors | Theil-Sen | +32 B/death | +64 B/death |
|---|---|---|---|---|---|
| real clock (562cf582), light copy | 24 | offsets up to 448 B; 416 B in 14 runs, 224 B in 4 | max 19.2 B | offline: min 21.3 B (missed); real plant 12/12 red (one at 43 B) | offline min 53.3 |
| driven (571fa38e), light copy + controls | 36 (load 1.0-14.9) | identical at every death (death 4 alone still settling in 4 runs: dev m1 +32, wozi m1 +224) | 0.0 in all | real plant 12/12 "32 B retained" | real plant 12/12 "64 B retained" |
Plants (test copies in bites/D_p32, D_p64, list sized up front): `(death,)` per death, one 32 B block, the least a
leak can hold; `bytearray(16)` per death, 64 B. Control bites/D_none 12/12 green, slope 0.0. Failed-link bite
(bites/D_nolink): fails cleanly in 1.2 s, no hang in the cleanup.
Time: the death test 7.0-7.9 s per run against 7.8-8.8 s before, on every device and stage.

## Item 2: FRAM assertions (bca66069), per scenario, bites
`_ring_in_fram(clock, conn)`: WIFI's chunk read back through the store's own `_read()` (FRAM manager, SPI driver, the
twin chip digital_twin/_fram_chip.py, CRC-checked; the logger-state read of test_digital_twin_fram_crash_points.py),
driven; requires a stored ring equal to the RAM ring.
- DHCP trace: after its (1, 1) RAM slots. Radio re-select: after its DEVICE_RECOVERY slot. Hotspot fallback and DNS
  idle rate: in `_hotspot_boot`, a new RAM assertion of the one to-hotspot slot, then the FRAM read.
- Bites, arzi/dev/grkizi at -1, the four scenarios each (bites2/): write plant (scratch asy_print_log.py: WIFI's store
  reports its write landed, writes nothing): new file 12/12 red "WIFI's FRAM copy False is not its RAM ring (...)",
  the 571fa38e file 12/12 green (the gap). RAM-only wiring plant (scratch generated modules, WifiService log=log_ram):
  new 12/12 red "WIFI's FRAM copy True ...", old 12/12 green. Control 12/12 green.

## Checks on bca66069
- The file on all six devices at both stages (f2): 24 green, zero memory markers; sum 162.45 s (-1) / 171.89 s
  (32768) against CMr1j's final 169.71 / 177.92 (arzi 30.77/32.69, dev 34.07/36.73, grkizi 27.77/29.85, klkizi
  21.43/22.11, schlafzi 21.45/21.86, wozi 26.96/28.65). Item 1 alone (f1): 24 green, zero markers.
- lint_direct rc=0; six mypy passes clean (272/57/312/1/1/1); walk, e51, review_rows --check rc=0.
- Whole tests_scripts tier (PICO_TOOLCHAIN_DIR=S/tc-int, whose record matches this tree's toolchain inputs; the
  shared /root/pico-toolchain's does not): 7040 passed, 6 skipped, 6 failed, the base's six (member_order
  asy_fram_manager, host_text_encoding, level_containment held_i2c_line/setup_resets, suppression_form
  test_digital_twin_sgp40.py:314, twin_record x2); none names my file.
- Silent-failure scan: class 3 (detection left to chance) in the drift check, fixed by item 1; class 7 (a FRAM-side
  fault invisible to the RAM-side assertion) in the four scenarios, fixed by item 2; mode: supervision, FRAM writes.

## Findings for the lead
1. (B)'s source is the twin's per-feed countdown task (digital_twin/machine.py WDT._arm). Under driven sleeps each
   death's 110 cancelled ones form one stale-child_last chain from the status loop (110 edges per read on arzi and
   dev, about 45 KB), replaced whole at the next death: identical each death, so no drift, but heap the device lacks.
   Twin-only (rp2's feed allocates nothing); one long-lived countdown re-reading its deadline would remove the churn.
   Not changed: not my file.
2. The drift window now measures the death path with every other task parked: a retention that needs a death to meet
   another task's cycle is outside it (the real-clock form saw such interplay only as noise it could not separate).
3. audit/b3/review.md's line numbers are stale since CMr1j's commits (and mine); --check is green; render left to the
   merge to avoid conflicts.
4. For D3's E.2.1 text (CMr1j's): the supervised-death test now also runs on the driven clock.
5. A first driven variant (supervisor started before the link wait) hung: `_settle()` raised under the supervisor's
   yield-per-pass loop, then the cleanup's cancel() of a sensor `_read_loop` cancelled at virtual t=0 never returned
   (dbg2); the exact await inside the loop was not pinned. Abandoned; the committed order fails cleanly (D_nolink).

## Process notes
- The first probe batch's threshold-stage runs failed at import (the runner's own directory is first on the path), and
  that batch (many.sh, pid 1588) was killed by pid, its RUNS.md done line written by hand; re-run fixed.
- All probe, plant and debug copies are outside the worktree; nothing uncommitted.

nothing of mine is running
