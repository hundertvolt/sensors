F2r readiness follow-up hand-back, saved by the lead from the message it sent (2026-10-26). Commit d4c51d7b on audit/u35-f2r (on 2a46984a).

F2r follow-up. The readiness-gate red is fixed in commit d4c51d7b on audit/u35-f2r (on 2a46984a). Not pushed, nothing uncommitted.

**What the rule wants.** `tests_scripts/test_readiness_gates.py` lets a class read its `initialized` flag only through `self` (SPECIFICATION.md C.13). Every `X.initialized` with X other than `self` is a finding. Other modules don't read a sibling's flag; they go through the sibling's own interface. FRAMManager already does this: it reads FRAM_SPI's `lost` Event (asy_fram_manager.py:152, :210, :366 and others) and calls its methods, which answer sentinels. D.15 counts `is_*` as a getter.

**The fix:**
- FRAM_SPI gets a new sync getter, `is_ready()`, which returns `self.initialized`. It sits after `get_write_protected()`, in D.15 order.
- `erase_ready()` now calls `self.fram.is_ready()` where it read `self.fram.initialized` (asy_fram_manager.py:801). Its comment is reworded to match.
- The MicroPython readiness table in `tests/test_readiness_gates.py` now pins `is_ready()` as False before and after a failed setup.
- No behaviour change against the previous commit.

**Why not the other options:**
- Making `get_write_protected()` answer differently is out: tests/test_readiness_gates.py pins its False sentinel.
- Setting `lost` at the moment the loss is found would remove the window my test pins, so that's out too.

**Seen failing:** with the old line planted in a scratch copy (`self.initialized and not self.fram.lost.is_set() and ...`), `test_an_erase_asked_while_a_found_chip_loss_is_still_being_reported_is_refused` fails with `AssertionError: [True]`. The test itself is unchanged.

**Checks, all run directly with the binary, inside the namespace:**
- `tests/test_asy_fram_manager.py`: 149/149 at gc -1 (0.62 s) and 32768 (1.41 s).
- `tests/test_readiness_gates.py`: 14/14 at both stages.
- 30 importers of `asy_fram_manager`/`asy_fram_driver` (`test_sensortask` and the twin integration file once per device): 80 runs, all rc 0, zero memory markers.
- 22 tests_scripts readers of the changed files, including `test_readiness_gates.py`, `test_code_conventions.py` (D.15 order) and `test_api_reference.py`: 1324 passed.
- ruff clean; mypy main pass clean (267 files).
- `scripts/test.sh` and the twin CI were not run, as you asked.

**Effect:** none on any device or mode beyond the previous commit's.

**For D3:** C.13 (SPECIFICATION.md:4440-4441) says the erase gate reads FRAMManager's flag; it now also asks FRAM_SPI's `is_ready()`. That is optional wording, not stale.

Allow-lists: none touched. The `_EXEMPT` row at `tests_scripts/test_counter_steps.py:28` from my first hand-back is still yours.

Logs are in S/u35/laneR/f2r/ (fix2_*, imp2_*, batch2_summary.txt, readers3.log, bite_oldline.log). The planted copy is deleted. RUNS.md lines are closed.
nothing of mine is running
