U35 P2b hand-back. Lane P, branch audit/u35-p, worktree S/wt-u35p. Head **83e8633** (on a77baac). Nothing is uncommitted and nothing of mine is running.

**What changed (commit 83e8633):** five files, src/asy_fram_manager.py, digital_twin/_fram_chip.py, tests/test_asy_fram_manager.py, tests/test_digital_twin_fram.py and tests/test_asy_fram_wire_trace.py.

**Steps by verdict**
- **R-8 applied.** A new private method `_FRAMBaseChunk._blank_verdict()` (src/asy_fram_manager.py:145-150) runs when `_read()` is about to return its blank verdict (no copy usable, a blank status byte read, no fault).
  - It calls `verify_present()` (RDID) after `_read_chunk` has released the bus lock. The driver reads into its preallocated `_id_buf`.
  - A chip that answers: the read returns False, as today.
  - A chip that does not answer: the read returns None, the driver logs FRAM_CHIP_LOST once, and the chip watch takes over.
  - No non-zero blank marker, so the FRAM layout is unchanged.
  - The probe sits in a helper because a probe inline in `_read()` failed ruff (PLR0911 12>10, PLR0912 21>20); I did not add a suppression.
  - The blank-setup wire-trace golden gains `w:9f r:047f0302` (54 to 55 CS cycles), and its header records the change.
- **LEAD NOTES 24 applied.** The twin chip has a new `silent_write_count`, listed in its `TEST_API`. It counts payload WRITEs issued while the chip is silent, using write_count's filter (a data phase over one byte), with or without a WREN.
- **P2a's ten test_sensortask runs: done, and I ran all twelve**, because my `src/` change reaches every device. All 91/91 at both stages.

**When a blank status byte is read in steady state (from the code; the same on all six devices, which all wire both fram and sgp40)**
- **Boot:** each FRAM-backed logger's `setup()` reads its chunk once (asy_print_log.py:383 to `_read` :298). The SGP40 backup restore reads its chunk once per attempt (asy_sgp40_driver.py:556); a blank result ends restoring (:558).
- **Chunk allocation:** `get_chunk()` and `get_timestamped_chunk()` are synchronous and read nothing.
- **errcount behind /status:** `get_log()` reads RAM only; no FRAM read.
- **Other:** a supervisor restart re-reads a chunk only if that logger's setup never finished, or if the SGP40 restore was still pending.
- **Conclusion: nothing recurs per request**, so there is no bound and no twin cost measurement (the brief's condition is not met). The cost is one CS cycle of 1 + 4 bytes per blank read.

**Seen failing first, on a77baac's src** (L1 143/146, twin 48/50):
- L1 silent chip read: test_asy_fram_manager.py:3000 got False where None was expected.
- L1 one probe per blank read: :3018, the RDID count.
- L1 busy lock: :3047, no probe was made.
- Twin silent chip: test_digital_twin_fram.py:626 got False.
- Twin counter: :823 raised AttributeError `silent_write_count`.

**Bites (scratch copies, deleted):**
- Removing the `lost.is_set()` condition fails only :3046.
- A probe-once-per-chunk bound fails only :3018. This is the test that shows no bound may hide a chip that stops answering.

**mpy-cross compare (armv6m, base f3fff0e against head; S/u35/laneP/p2b/mpy/compare.txt):**
- Code changes only in `_read` (372 to 381 instructions), the new `_blank_verdict`, and its definition in the class body.
- The other 53 functions differ only in line tables and qstr indices.

**Runs** (all rc=0 with mem=0 unless noted; times are base runs → head runs in seconds; tables in S/u35/laneP/p2b/batch.tsv and batch2.tsv):
- fram_manager, paired:
  - -1: 5.11/5.18 → 4.92/4.94.
  - 32768: 5.76/5.77 → 5.70/5.98 (+1.3 %).
- twin_fram, paired:
  - -1: 0.64/0.52 → 0.59/0.57.
  - 32768: 0.84/0.76 → 0.80/0.65.
- Head only, at -1/32768:
  - wire_trace 0.43/0.48;
  - ntp_fram_system 7.56/7.66 (U32 7.63/7.68);
  - twin integration dev 23.06/23.47 (U32 22.95/23.65), 4 passed and 8 skipped (arzi-only); its 10 tracebacks are the file's deliberate "injected status fault";
  - 14 importers green at both stages;
  - test_sensortask -1/32768: arzi 27.8/32.0, dev 45.2/54.2, grkizi 27.8/32.8, klkizi 27.7/32.0, schlafzi 28.3/32.1, wozi 32.6/36.0.
- Readers in one pytest process (48 files: P2.2's list, lock_order, twin_fake_catalog found by grep, and the 12 checks): 2711 passed, 6 skipped (the opt-in RUN_SLOW builds).
- ruff and the main (both forms) and twin mypy passes are clean.
- Sequencing slip, mine: an edit after the rebuild left build/generated_src stale, so 17 runs refused to start. I rebuilt with S/u23/rebuild.sh and re-ran all 17 green. That was not a code failure.

**Red checks:** none. test_twin_record was not run and is expected red. **Orphaned allow-list rows:** none.

**Silent-failure scan, all classes, my files:** nothing new. Class 3 (blank versus undriven) is now closed. A busy lock keeps the blank verdict and the driver logs it, so class 1 is not ignored.

**Effect per mode:** all six devices, on the FRAM's SPI bus. STA, AP, Silent, Off and USB take the same path. A chip that is silent at a blank read is reported lost at that read, not at the next write. On USB the lost-chip line prints at the first blank read.

**Decisions (agent, 2026-10-21):**
- No bound on the probe.
- At most one probe per `_read()` call, and only where its blank verdict is returned. Write-verify and the block-1 check after a valid block 0 do not probe: the chip just answered in that same operation, and the next write's WEL check finds a lost chip.
- A probe that cannot take the lock keeps False.
- The silent counter ignores WEL.

**Relay lines written:**
- `## P`: `<SILENTW> 83e8633`.
- `## D`: the facts for R-8's FRAM sentence (P2b 83e8633).

**Facts owed:**
- T3: the field name is `silent_write_count`. A correct product issues 0 to a chip that is silent from boot, because the driver's WEL check stops each write before its data phase.
- T4/D2: digital_twin/README.md has no text on the new counter yet; I did not check its test-surface table.

**Datasheet:** the worktree's datasheets/ is empty. /home/user/sensors/datasheets/fram/*.pdf exist but are AES-encrypted, and the host has no AES provider. I used the scratchpad's earlier text extraction of the same documents (S/MB85RS64V-DS501-00015-4v0-E.txt and the MB85RS2MTA one): RDID op-code 1001 1111B on p7, ID 04H 7FH 03H 02H on p10-11, SO High-Z while CS is high on p2.

**Start state for P3:** head 83e8633. The config_manager and print_log files are untouched by P2b. Logs are in S/u35/laneP/p2b/. RUNS.md has start and exit lines for every run.
