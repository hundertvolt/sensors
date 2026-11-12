BR3 hand-back, written by the lane (2026-10-27)

Lane BR3 (raising.md, part 3: asy_fram_manager.py and asy_fram_driver.py). Worktree S/wt-u35braise3, branch audit/u35-braise3, based on 651d3e79. Not pushed. Nothing uncommitted (node_modules was already untracked). Logs are in S/u35/laneB/br3/, and every run went through S/u35/laneB/br3/run.sh, with RUNS.md lines named `U35 lane BR3`.

## Commits
- **7ceb50b2**: the defect fix (below). It also re-renders raising.md and e51.md and moves the e51 coverage hits for the shifted lines.
- **396ab96d**: verdicts for asy_fram_driver.py (`audit/b3/raising_verdicts/asy_fram_driver.json`).
- **acebee6d**: verdicts for asy_fram_manager.py (`audit/b3/raising_verdicts/asy_fram_manager.json`).

Every commit passed these checks:
- `raising_walk.py --check`
- `e51_sweep.py --check`
- `review_rows.py --check` (8534 rows, unchanged)
- test_citations, test_decision_vocabulary and test_comment_block_cap (666 passed)

Each verdict commit's raising.md diff touches only that module's rows. Its e51.md diff touches only the generated block. On this base, the 396ab96d diff also creates the block's heading, because BR1's print_log and math_helpers commits are not under it. The lead's re-walk over the merged JSON files settles that.

## Rows by verdict
**Before (651d3e79, module-wide groups):**
- driver: 4 raise rows (3 "exempt (setup)", 1 "inherently safe") and 51 call groups (open 24, transitive 26, unreachable 1).
- manager: 75 call groups (open 29, transitive 45, unreachable 1).

**After (per-function groups):**
- driver: 4 raise rows, all handled. 81 call groups: handled 23, unreachable 58.
- manager: 109 call groups: handled 67, unreachable 42.

**Left as transitive, as the brief asks** (calls into asy_base_classes and asy_print_log that keep those modules' own rows):
- driver, 5 groups: `report_if_fatal`, `self.pr.err_s`/`wrn_s`/`evt`/`one`.
- manager, 14 groups: `console`, `report_if_fatal`, `utc_now`, `buf.get_buf`, `buf.get_data_buf`, `self.pr.*`.

**Two of the walk's "transitive" groups were name matches, not real calls into own code.** I classified both by hand:
- `self._spidev.setup` is SPIDevice.setup in asy_spi_driver.
- `self.lost.clear` is asyncio's Event.clear.

**The lead's BR1b note is addressed.** The driver's two setup raise proofs used to cite asy_fram_manager.py:795/:796. I checked them on the base, where they are :817/:818. On this branch, after the fix moved lines, they are :828 (the `self.fram.setup()` call) and :829 (`except Exception`). The new proofs cite those. The `_check_device_id` raise proof now also covers its run-time callers: they are unreachable behind the `initialized` guard.

**CO1's call at asy_fram_manager.py:152** (`verify_present` on the chip-loss path) is classified like any other call: `_FRAMBaseChunk._blank_verdict::self.fram.verify_present` is handled, and `::self.fram.lost.is_set` is unreachable.

**Shared facts are stated once, in each file's "conventions" key.** The walk does not render that key. They cover:
- C-stack overflow.
- No allocation for a call frame or for `super().m()`.
- Exception objects, which fall back to the emergency object.
- Small fixed allocations: F.2 → I.4(a), handled by `_log_dead_task()` :326 or the boot entry's `except BaseException`.
- CancelledError is a BaseException (extmod/asyncio/core.py:18).
- The driver's "byte-level chain": no transfer can raise, except a 32+ byte read's OSError(EIO), ports/rp2/machine_spi.c:267-270/341.

**Special attention:**
- Task tops: `_watch_chip_loop` reaches `_log_dead_task`; its starter `create_task` reaches `_start_task`'s except at asy_system_service.py:502.
- Erase and quiesce run inside the shutdown sequence's try (asy_system_service.py:441, except :494).
- No Timer or IRQ callbacks, no Microdot handler and no response-writing path exist in these two modules.
- Widened excepts: the driver's `except BaseException` at :160 re-raises. The manager's `except Exception` at :168/:328/:423/:593/:628/:829 cannot catch a CancelledError. So there is no swallowed cancel to name for A.U35.48.

## Defect: a chunk read's copy-out raised MemoryError
- **Site:** `FRAMChunk.read()` (`return bytearray(dbuf)`, base :488) and `FRAMTimestampedChunk.read()` (`return ts, age, bytearray(dbuf)`, base :558).
  - The copy is chunk-sized, so its size grows with configuration, and nothing caught it. On an exhausted heap the MemoryError left a module whose header says it never raises.
  - The buffer it copies from already degrades: RegionBuffer catches its allocation at asy_base_classes.py:160.
  - No firmware caller uses `read()`: the firmware uses `read_into()`. The hardware device scripts and tests do call it.
- **Test:** `tests/test_asy_fram_manager.py::test_a_failed_read_copy_returns_the_sentinel_on_both_chunk_classes`. It substitutes `asy_fram_manager.bytearray` with a function that raises only for a memoryview argument (the copy), then asserts:
  - `None` and `(None, None, None)` as the return values;
  - the console line with the failure's own text;
  - one ALLOC entry per read (ErrCount 2);
  - a later read still returns the data.
- **Red first:** on the base, `MemoryError: injected for the read copy` was raised from src/asy_fram_manager.py:488 (153/154 passed; log `red_first.log`).
- **Fix:** both `read()`s go through a new `_FRAMBaseChunk._copy_out()` (:463-471). It does `try: bytearray(data)`, and on `except MemoryError` it:
  - prints the failure's own text with `console` (the memory gates read it);
  - persists one ALLOC entry (`err_s`, the same message `read_into()` uses for a missing buffer);
  - returns None.
  
  The return contract is unchanged, and the "never raises" header is true again.
- **Runs:**
  - All 24 importer test files at both GC stages: rc 0, zero memory markers (`fix_importers_both.log`). The one file that needs TEST_DEVICE was run on all six devices at both stages, all rc 0 with zero markers (`fix_twin_integration_both.log`).
  - lint_direct (ruff over the eight scopes and build/generated_src, shellcheck, actionlint, zizmor, method-assign, gc sites): clean.
  - The main mypy pass, with a temporary copy of S/shared/typings (deleted afterwards): clean.
  - 12 tests_scripts readers of the FRAM modules: 461 passed.
- **How I kept `e51_sweep.py --check` green after the line move (please check this):**
  - The hits are line numbers from one coverage run (CEr1), so any src edit that shifts lines breaks the check.
  - `S/u35/laneB/br3/remap_hits.py` moved src/asy_fram_manager.py's hits from the base text to the new text: lines difflib calls equal keep their hit.
  - The 13 inserted or changed lines take their hit from a real build-settrace run of tests/test_asy_fram_manager.py (`cov_mgr.json`, 154/154 passed). All code lines were hit; the three comment and blank lines were not.
  - I then re-rendered e51.md: four FRAM sites moved by +10 or +11 lines. Three e51_verdicts.json proofs that cross-referenced "as :487" now say ":497".
  - If you would rather have a fresh coverage run at the merge, it replaces this remap.

## e51.md rows added
100 rows in the generated "Unreachable raises" block: 58 for asy_fram_driver.py and 42 for asy_fram_manager.py. Each row carries its proof and the narrow except around it, if any. No hand edits: the walk renders them from the JSON files.

## Question for the owner
**Does the FRAM driver's "never raises" contract cover `get_values()`?**
- `asy_fram_driver.py`'s module comment (:12-14) and G5/R17 both say the driver never raises outside its one-time `__init__()`/`setup()` errors.
- SPECIFICATION.md C.3.1 (:3100-3101) and F.5.2 say otherwise: `get_values()` into a buffer of 32 bytes or more can raise OSError(EIO) on an RX overrun. Both say it propagates, like asy_i2c_driver.py's, and that its caller handles it.
- In the firmware this raise is handled. The only read that long is the chunk layer's payload read, inside `_read_chunk()`'s `except Exception` at asy_fram_manager.py:328. No firmware code calls `get_values()` directly.
- I recorded the row as handled with these facts, and left the code and comment alone because two owner-level texts disagree.
- Options:
  - (a) Name the exception in the module comment. That is one clause; the spec already says it.
  - (b) Catch OSError in `get_values()` and return False with an errno. That contradicts F.5.2's recorded "propagates" and adds a catalog code.
- **I recommend (a).**

## Process note
I applied the src edit in 7ceb50b2 with a short Python string replace in Bash, not the Edit tool (BR1's notes ask for Edit or Write). The result is the same three hunks you can see in the diff. Every later edit used Edit or Write.

nothing of mine is running
