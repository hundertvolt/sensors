# U35 gate 1, blocks G1a and G1b: root-cause the two twin scenario failures (lead, 2026-10-22)

## Both blocks
- The W6 gate (`S/gate_v17.sh` on `069b9fe`, outdir `S/u35/gate1`) ran up to four twins in parallel plus the npm leg.
  Every leg passed except one scenario on each of two devices; each passed on every other device and stage, and in
  every earlier gate since it was added. The owner's rules: "root cause any faults"; no failure is called a flake
  without a root cause; "system shall be proven stable unter max load allover"; "I just want to make sure no evidence to
  a bug, be it in the firmware or the tests, is silently lost."
- Your branch `audit/u35-g1<x>` and worktree `S/wt-u35g1<x>`, both at `069b9fe`, already rebuilt. Logs in
  `S/u35/laneG/g1<x>/`. Commit subject `U35 gate fix: <summary>`; decision tags "(agent, 2026-10-22)".
- Read first: `S/CHECKLIST.md`, `S/u35/briefs/common_u35.md` (its Rules and Runs parts; its lane file lists do not
  apply: your files are named below), and the evidence copied from the gate (below). Never edit the gate's worktrees
  (`S/wt-tw*`, `S/wt-cov`, `S/wt-lint`, `S/wt-u8`, `S/wt-u7g`): the coverage leg still runs in `S/wt-cov`.
- Method: read the failed and a passed run side by side; state the mechanism with file:line at `069b9fe`; reproduce it
  on demand in a scratch copy (a planted delay or load at the point the mechanism names), and show it failing the same
  way, then passing with the fix. A reproduction is never a retry: "it passed again" proves nothing.
- The fix goes where the defect is. A test or harness defect is fixed in the test or harness; the check's strength
  stays (checks are never weakened, a bound is never widened to fit a slow host). A firmware defect: stop and hand
  back the mechanism and a proposed patch; `src/` is not edited in this block. Nothing may add or change a flash or
  SCD30-NVM write (CHECKLIST 24), and the UART wire format is untouched.
- Proof after the fix: the scenario on every device that runs it at both stages; the same scenario under the gate's
  load shape (the other device twins of the gate running beside it, or an equivalent CPU load you start and stop by
  pid) at least three times per stage; the scenario module's readers in `tests_scripts` (`grep -l` the module name);
  ruff and the host mypy pass on the changed files. Port-binding runs inside `unshare -n S/u24/ns_xdg.sh`; one run at a
  time in your worktree; RUNS.md lines; CHECKLIST 22's disk check. The other G1 block runs beside you: at most two
  twin processes of yours at once.
- Never run real hardware tools (mpremote, picotool, nmcli, iw, iptables); never read arduino/; never edit ext/ or
  legacy/; no git stash; kill only by a pid you checked; do not push. About 60-80 tool calls; past 80, commit what is
  green and hand back the rest.
- Hand-back (at most 35 lines): the mechanism with file:line; the reproduction (planted, how it failed); the fix and
  its commit; the proof runs (counts per device and stage, under load); anything for the lead (a firmware question, a
  doc sentence the fix makes stale with its line); last line "nothing of mine is running".

## G1a: klkizi, GC -1, `reset_errors_while_the_escalation_logs_is_refused_and_clears_nothing`
- Failure: `AssertionError: SYSTEM's history holds no stack-exhaustion entry` (all ten entries 'N', counter 0).
- Evidence: `S/u35/gate1/evidence/klkizi_reset_errors/gc_neg1_failed/` and `.../gc_32768_passed/` (twin_01 is the
  escalation boot, twin_02 the relaunch); the leg's log `S/u35/gate1/twin_klkizi.log`; host load `S/u35/gate1/vmstat.log`.
- What the lead saw (verify, do not trust): the failed boot logs `SYSTEM Reboot: C stack exhausted - its entry not
  persisted within 1200 ms, its write is held up` and SYSTEM:3 FRAM writes; the passed boot logs `SYSTEM C stack
  exhausted - reboot triggered` and SYSTEM:4. The scenario (`scripts/_digital_twin_scenarios.py`, its `@scenario` line)
  holds the entry write with `--test-hold-system-entry` (`digital_twin/run_generic_integration.py`,
  `_test_hold_system_entry`), reads the error table, sends a refused ResetErrors, then releases; the escalation's write
  is bounded by `_ESCALATION_ENTRY_WAIT_MS` in `src/asy_system_service.py`. The lead's hypothesis is that the host's
  steps between ENTRY_HELD and ENTRY_RELEASE took past that bound under load, so the firmware took its designed
  timeout path. Find when the bound and the scenario each came in (`git log -S`), whether the scenario's design ever
  guaranteed its window, and fix the scenario so its outcome does not depend on host speed, keeping what it proves:
  a ResetErrors arriving while the escalation writes its entry is refused and clears nothing, and the reboot keeps
  every entry with ResetReason 20. If the timeout path itself (entry not persisted, reboot anyway) has no scenario of
  its own, say so; whether to add one is the lead's call.
- Your files: `scripts/_digital_twin_scenarios.py`, `digital_twin/run_generic_integration.py` (its test knobs only),
  their tests_scripts readers, `digital_twin/README.md` where a knob's text changes.

## G1b: dev, GC 32768, `uart_ring_under_concurrent_load`
- Failure: `AssertionError: a load thread raised or never ran: [3, 3, 3, 2, "TimeoutError('timed out')", 4, 3, 6]`
  (61.4 s); the GC -1 run of the same leg passed (61.6 s).
- Evidence: `S/u35/gate1/evidence/dev_uart_ring/gc_32768_failed/` and `.../gc_neg1_passed/` (two boots each, with
  state dirs); the leg's log `S/u35/gate1/twin_dev.log`; host load `S/u35/gate1/vmstat.log`.
- Find which load thread raised, on which request, against what timeout, and why the device answered late or not at
  all: the device's own log in that window (loop lag, flash stall, refusals, the UART links' counters), against the
  scenario's `_uart_load_round` and its constants. Decide from evidence whether the device missed a bound it owes (a
  firmware finding: hand it back) or the host-side thread's timeout or start does not match what the device is
  specified to answer under that load (fix the scenario, keeping the check's strength). The scenario's own claims
  (no overrun, a train past the cap refused once, the heap unfragmented) stay as strong as now.
- Your files: `scripts/_digital_twin_scenarios.py` (this scenario and its helpers only), its tests_scripts readers.
  G1a edits the same module elsewhere: keep your diff to your scenario's functions so the lead merges both cleanly.

## G1c: the coverage leg, `tests/test_sensortask.py[dev]` under `build-settrace`
- Failure: `test_every_logger_count_stops_at_its_top_and_its_ring_keeps_the_newest_codes_through_a_reboot`:
  `MemoryError: memory allocation failed, allocating 262145 bytes` at `tests/_sensortask_scenarios.py:2195` (the
  `rebooted = build(device, chip=_chip_holding(..., bytes(_fram_chip(module).memory)))` line). The leg's log is
  `S/u35/gate1/coverage.log` (the failure near its line 1688; the summary at its end); the dev file's lines and its test
  order are saved in `S/u35/gate1/evidence/coverage_dev/`. The same file passed both plain stages in this gate with no
  memory marker. The scenario came in today (`ed649bd`, lane V), as did two others with the same copy (:2003, :2046).
- What the lead saw (verify, do not trust): the rebuild copies the device's whole FRAM image into one 256 KiB `bytes`
  while the first device graph and its chip are still alive, and `_chip_holding()` (:896) copies it again into the new
  chip; under the settrace binary's allocation inflation (SPECIFICATION.md Part E.5.2) the heap has no free contiguous
  run that size. Establish the mechanism: which allocations are live at that line, why plain passes and settrace does
  not, and whether the test order matters (the runner's order is the module's). Reproduce it on demand under
  `build-settrace` the way `scripts/test.sh --coverage` runs one file (read the script for the runner and flags), then
  fix it in the tests without the big contiguous copy (the project's memory rule: relieve the pressure, never raise the
  heap; CLAUDE.md's `-X heapsize` bullet), at all three sites if they share the defect, keeping what each scenario
  proves (the rebuild reads the chip image the first graph wrote, every logger restored).
- Proof: the dev file and every device's `tests/test_sensortask.py` under `build-settrace` and at both plain stages;
  the three scenarios' assertions bitten in a scratch copy (a rebuild that does not carry the image must fail); the
  file's paired plain wall times before and after (LEAD NOTES 4: no growth).
- Your files: `tests/_sensortask_scenarios.py`, `tests/test_sensortask.py` if needed.

## G2: the webserver's refusal path gets a bound; FRAM chunk writes proven safe to cancel (after G1a/G1b)
- Start: `S/u35/handbacks/G1b_final.md` (the refusal path's unbounded hold, the evidence, both scratch patches and
  `S/u35/laneG/g1b/proposed_p1.diff`) and `S/u35/handbacks/G1a_final.md` (the escalation bound's cancel cut a chunk
  write in two and the relaunch read a BUSY block). Branch `audit/u35-g1b`, worktree `S/wt-u35g1b`, clean at `069b9fe`
  (rebuilt). Logs in `S/u35/laneG/g2/`. Here `src/` is yours, within the files named below.
- Decided on the owner's behalf (lead, 2026-10-22, logged for the owner's review; conservative and reversible): p1's
  shape. The refused connection is counted at once, its trace held at most one per-call timeout, then closed. A trace
  cut short keeps its entry in RAM for the logger's next write, as `PrintLog._write()` already intends for a cancelled
  write (src/asy_print_log.py, the comment above `self._write_gen`). The trace-before-close order stays, because it is
  what paces a refused client (G1b's close-before-trace run piled tasks up and exhausted the heap). Every drop still
  leaves its count and its entry (SPECIFICATION.md's "Every drop leaves evidence", owner, 2026-09-29).
1. Premises first, each with file:line: `wrn_s()` puts the entry in RAM before its first await, so a cancel at any
   await keeps it; the next write by any caller persists it; nothing else in `_serve()` relies on the trace having
   landed before the close.
2. FRAM chunk-write cancellation safety. A cancel already reaches a chunk write in production through the escalation's
   bound (src/asy_system_service.py:578), `_serve()`'s outer cap and every other `wait_for_ms` over a logging call, and
   p1 adds one more. At every await between `PrintLog._write()` and the SPI transfer (FRAM manager, FRAM driver, SPI
   driver, their locks), a cancel must leave chip select deasserted, every lock released and the chunk's last good
   block intact and readable. The relaunch must restore it, and log a BUSY block as the store's self-healing path does.
   Pin this with unit tests that cancel at each await point, seen biting on a planted unsafe variant. A defect found
   here: stop and hand it back with a proposed patch; do not fix it in this block.
3. Test first, in `tests/test_asy_webserver_connections.py`: a refusal whose trace blocks past the per-call timeout
   closes at that timeout, keeps its count and its RAM entry, and the next write persists the entry. Seen failing on
   `069b9fe`. Then p1 in `src/asy_webserver_service.py`, with the A.8 comment above it stating what the code does (at
   most 3 lines). The cut arm is not a silent `pass`: the entry's survival is its evidence, and a comment says so.
4. The escalation's message at src/asy_system_service.py:580 says "its entry not persisted within" where the write may
   have landed half or whole (G1a's control run): make it state only what the code knows, and fix every test that
   matches the old text.
5. The scenario's `_REQUEST_TIMEOUT_S` (scripts/_digital_twin_scenarios.py:80) against what the device owes after p1: an
   admitted connection is bounded by the outer cap, a refused one by one per-call timeout plus a flash hold. If the
   client timeout sits below a bound the device owes, derive it from the src constants, never from measured latency,
   and change it only for the load threads that need it. Otherwise leave it and say why.
6. Proof: the changed unit files at both stages and under `build-settrace` (one at a time, as test.sh runs one file);
   `tests/test_asy_webserver_*`, `tests/test_digital_twin_webserver_concurrency.py` and every device's
   `tests/test_sensortask.py` at both stages; `uart_ring_under_concurrent_load` on dev under the gate's load shape
   (four CPU burners you start and kill by pid) 3 times per stage, plus G1b's planted 4x trace once with p1; the
   readers; ruff, the main and twin mypy passes; LEAD NOTES 7's mpy-cross byte compare for each src file; LEAD NOTES 4
   for each changed test file's time.
- Your files: `src/asy_webserver_service.py`, `src/asy_system_service.py` (the message only),
  `tests/test_asy_webserver_connections.py`, the FRAM and SPI unit test files your step 2 needs (tests only),
  `scripts/_digital_twin_scenarios.py` (step 5 only). Not yours: SPECIFICATION.md. G1b's stale SPEC lines (12216, 9785,
  6588) and any your change adds go in the hand-back for D3, each with its line.
- Same rules as "Both blocks". About 60-80 tool calls; if step 2 alone fills the block, commit what is green and hand
  back step 3 onward at a seam.

## G3: the FRAM chunk's write order, every pre-close trace bounded, G2's open proofs (after G2)
- Start: `S/u35/handbacks/G2_final.md` and G2's logs and tools in `S/u35/laneG/g2/b/` (`tools/two_cut.py`, the patched
  file `plant_FIX/asy_fram_manager.py`, `tools/twin_batch.sh`, `tools/plant4x.py`). Branch `audit/u35-g1b`, worktree
  `S/wt-u35g1b`, at G2's `43d1a6b`. Logs in `S/u35/laneG/g3/`. Decided on the owner's behalf (lead, 2026-10-22, for the
  owner's review): the write-order fix lands in U35 with the refusal bound, because the bound adds a cancel source to a
  path where two cut writes in a row lose a chunk's stored history; and the bound's shape applies to every trace
  `_serve()` awaits before its close, not only the refusal's. CHECKLIST 24: FRAM is not wear; list every FRAM write and
  read site your diff adds or changes in the hand-back.
1. `src/asy_fram_manager.py` `_write()` (:373-382 at `069b9fe`) writes block 0 then block 1 whatever their state, so
   one cut leaving block 1 BUSY and the next cut inside block 0 leave both BUSY, and `setup()` overwrites the history.
   Test first, structurally, never by brute scale. For each start state (both blocks IDLE, block 0 BUSY, block 1 BUSY)
   and each cut point of one write, after the cut at most one block is BUSY and a relaunch restores the old or the new
   state. Seen failing on `069b9fe` for the block-1-BUSY start. G2's 784-pair sweep stays a scratch proof: run it once
   on the fix (0 lost) and log it.
   Then the fix: the block that is not IDLE is written first. G2's patch reads block 1's two status bytes, which are
   FRAM reads only. A failed status read gets an order you state with its reason, and a test. The relaunch's BUSY
   log and repair stay as they are.
2. Every trace `_serve()` awaits before the writer closes (the refusal's, `_note_drop()`'s bad-head and peer-reset
   arms, and the three reclaim arms at :944-952) is held at most `self._per_call_timeout_ms` through one helper, then
   the close proceeds. A cut trace's entry stays in RAM for the logger's next write, as G2's refusal arm says. No
   second copy of the drop count line: G2 inlined `_note_drop()`'s first line at the refusal; fold it back. Test first:
   one reclaim arm and one drop arm whose trace blocks past the timeout close at it, seen failing on `43d1a6b`.
3. LEAD NOTES 4: `tests/test_asy_fram_manager.py` grew +12 % / +15 % (G2's fresh 8 KB fake chip per fixture). Make
   it efficient without weakening it, for example one chip per sweep reset in place; paired times before and after.
4. G2's owed proofs, on your final head:
   - every device's `tests/test_sensortask.py` at both stages (rebuild first with `S/u23/rebuild.sh`);
   - the changed unit files under `build-settrace`;
   - `tools/twin_batch.sh` as G2 wrote it, inside the namespace: uart_ring 3x per stage beside four burners you
     kill by pid, the webserver concurrency scenario family at both stages, and the 4x plant once with the bound;
   - the whole tests_scripts tier once at the end, alone on the host, instead of picking readers;
   - ruff, all four mypy passes, LEAD NOTES 7's mpy-cross compare for each changed src file.
- Your files: `src/asy_fram_manager.py`, `src/asy_webserver_service.py`, `tests/test_asy_fram_manager.py`,
  `tests/test_asy_webserver_connections.py`, the FRAM unit test files step 1 needs. SPECIFICATION.md is not yours:
  put G2's D3 lines in your hand-back, together with any stale sentence your fix makes (the FRAM dual-block write
  order is described in SPEC; find it with grep).
- Same rules as "Both blocks". About 60-80 tool calls; if steps 1-2 fill the block, commit what is green and hand back
  the rest at a seam.
