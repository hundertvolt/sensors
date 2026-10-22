U35 P2a hand-back. Lane P, branch audit/u35-p, worktree S/wt-u35p. Head is **a77baac** (on 0dd3148), and nothing is uncommitted.

**Commit a77baac.** Tests only: tests/_fram_chip_fake.py and tests/test_asy_system_service.py.
- **Step 35, applied.**
  - The fake gains `cut_after_bytes`: once that many more WRITE data bytes are on the wire, no write lands. It also gains `bytes_written` (WRITE data bytes the array took).
  - `readinto()` now passes the pending opcode as the `match=` key. The 32-byte DMA gate still applies.
  - ":100 '1.29'" now reads "v1.29.0", and `TEST_API` lists the chip's 22 knobs and counters.
  - test_asy_system_service.py's local `_CutChip` keeps only its erase-unit counters and `drop_wren_at_unit`. It now uses the fake's cut and raises `PowerCut` once the cut reads 0.
  - `_CutChip2MTA` takes `SIZE`/`RDID` from `FakeMB85RS2MTA`. The local `_WRITE_OPCODE` "keep in sync" copy is gone; the opcodes are imported from the fake (same pattern as test_bus_hazard_multi_device.py:28).
- **LEAD NOTES 15, applied.** The six `Task[object]` annotation lines (7 occurrences) now read `Task[None]`.
- **Proof for the TaskStarter form:** I ran scripts/typecheck.sh in a scratch copy with Y1's TaskStarter form in src/asy_system_service.py and `asy_system_service` removed from pyproject.toml:425.
  - With my change: rc=0, 10/10 passes.
  - Control with the six restored to `Task[object]`: the main pass fails with exactly Y1's 4 errors (:1232, :1975, :2174, :3090 at the head).
  - The copy has been deleted.
- **Steps 94, 95, 96 (check-only on the base f3fff0e):** all landed.
  - 94: :303, :318, :431, :467, :496, :545, :569, on `_driven()`'s DrivenTime at :121-123 (R-3).
  - 95: :604, :612, :620, :648, :672. Of A.U35.12's sleeps, no `sleep(0)  # let` remains in the file. The sequencer's 5-yield pumps are each checked by the start-order assert right after them.
  - 96: `_RUN_BOUND_S` :69 with its `@tunable` tag at :68; :2894, :2951, :3065, :3154, :3225.

**Seen failing first** (on the old fake, 183/187 passed):
- the power-cut case failed its memory assert;
- the `bytes_written` case raised AttributeError;
- the match-key case failed at :1760 (no raise);
- the `TEST_API` case failed at :1766 (`TEST_API` not in the class dict).

**Decisions (agent, 2026-10-21):**
- The cut counts bytes on the wire whether WEL is set or not, as the old local copy did.
- mypy rejects the chip's `TEST_API` override because tests/machine.py:598's SPI `TEST_API` is inferred as a fixed-length tuple. I added a coded, reasoned `# type: ignore[assignment]` at tests/_fram_chip_fake.py:29. **Defect for the owner of tests/machine.py:** annotating :598 as `tuple[str, ...]` would make that ignore unused, and `warn_unused_ignores` would then go red until it is removed.
- I ran the direct and non-twin transitive importers. I left out the twin files; they use digital_twin's own FRAM chip.

**Runs** (all rc=0, mem=0 at both stages unless noted):
- **test_asy_system_service paired, base→head, alternating:**
  - -1: 25.02/24.99 → 24.92/25.02 s.
  - 32768: 26.41/26.48/26.08 → 27.09/26.39/26.06 s. That is a mean of +0.19 s (+0.7 %), all of it from the first head run; the head ran at or below base in the next two pairs. Not grown.
- **At both stages on the head:** 10 direct importers plus 11 transitive ones, all green. uart_comm took 62.2/63.2 s; the rest are in S/u35/laneP/p2a_batch.tsv.
- **test_sensortask.py:** arzi and dev passed at -1 (91/91). The other 10 runs (four devices at -1, all six at 32768) did not run: the host had 15 heavy processes and my gate held them. I killed my batch, pid 28504, by pid. **Owed to P2b.**
- **Readers plus the 12 convention checks:** 2695 passed, 6 skipped (the opt-in RUN_SLOW firmware builds). Ruff and mypy (main pass with and without args, twin pass) are clean. comment_block_cap, decision_vocabulary and suppression_form were re-run after the last comment edit: 656 passed.
- One timing caveat: I made a comment-only edit to the fake around the time the first head system_service run started.

**Red checks:** none. **Orphaned allowlist rows:** none. **Silent-failure scan** of both files, all classes: nothing new.

**Relay:** `<TASKNONE> a77baac` written under `## Y`.

**Effect per mode:** none in STA, AP, Silent, Off or USB, on any device. No src/ file, wire byte, tag or catalog row changes.

**State for P2b:** start from a77baac. Owed: the 10 test_sensortask runs above. My files are unchanged since a77baac, and test_asy_fram_manager.py and test_digital_twin_fram.py are untouched.

Nothing of mine is running.
