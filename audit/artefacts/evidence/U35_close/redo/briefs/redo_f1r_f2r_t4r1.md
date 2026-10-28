# Redo wave 1: F1r, F2r, T4r1 (lead, 2026-10-26)
Read `S/u35r/briefs/redo_common.md` first. Base for all three: `656fc82` (branch `audit/u35-int`), each in its own
worktree, already rebuilt. Logs in `S/u35/laneR/<block>/`.

## F1r (worktree S/wt-u35f1r, branch audit/u35-f1r)
Your brief is the "Both blocks" and "F1" sections of `S/u35r/recovered/briefs/blocks_f.md`, with these changes:
- The lost F1's results (`S/u35r/recovered/handbacks/F1_final.md`) are your map: redo each landed item test first on
  this base (its test seen failing first, its bite), and re-check each "cannot occur" and "kept" verdict yourself.
- Item 3's input differs: the e51 table (CE's) is lost and is rebuilt later by another block. Do now only what needs no
  e51 table: SensorReader `logger=` restored with its test (removed in 8d44fd1; the owner's library rule), the sgp40
  `_exchange()` reply bound (re-prove it dead, then remove it, proof in the commit), and the seven narrowing comments
  (scd30:280; uart_driver :183, :290, :357, :369, :810; webserver :212 at the lost head: re-locate them; comment only,
  mpy-cross output unchanged). The rest of item 3 waits for the e51 table.
- Add: `src/asy_webserver_service.py` near :949 says no arm "persisted" the entry where "traced" is exact (LEAD NOTES
  116): comment only. `tests_scripts/test_lint_ceilings.py:52` says the `logger=` reach-through stays "(C.7)", which C.7
  does not state: make the comment state what is true.
- For D3 (hand-back lines, not your edit): SPECIFICATION.md C.14.1's "before `make_logger()`, so … always agree"
  (about :4433-4434) once `logger=` is back.
- Not yours: the F2r and T4r1 files below; CF and CE work in tests you do not need.

## F2r (worktree S/wt-u35f2r, branch audit/u35-f2r)
Your brief is the "Both blocks" and "F2" sections of `S/u35r/recovered/briefs/blocks_f.md`, with these changes:
- Item 2 includes the exact-age survivor at `src/asy_notification_service.py` near :230
  (`test_a_stale_producer_sample_is_not_evaluated` skips the exact age; `S/u35r/recovered/handbacks/CF1b_final.md`):
  a sample at exactly the limit gets its test, red on a plant of the bound first.
- Item 7: OF-103's equality test is already in the tree (`tests/test_asy_neopixel_driver.py` about :1139-1145): say so,
  do not redo it. OF-245's six catalog codes stay yours.
- Item 4 (OF-246) is going to the owner as a question now: do not change it; hand back what C.7 says and the facts.
- `src/asy_uart_driver.py`: keep to the frame-copy lines of item 5; F1r adds comments elsewhere in the same file. Add
  tests as new functions at the files' ends; the lead merges.
- Not yours: the F1r and T4r1 files.

## T4r1 (worktree S/wt-u35t4r, branch audit/u35-t4r)
Your files are lane T's (the "Your files" line of `S/u35/briefs/blocks_t4.md`, plus `digital_twin/_fram_chip.py` and
`tests/test_digital_twin_fram.py`). Read `S/u35/briefs/blocks_t4.md` ("Both blocks", T4a, T4b),
`S/u35r/recovered/briefs/blocks_t4_amendments.md`, `S/u35r/recovered/handbacks/T4a2_final.md` and the facts at the end of
`S/u35r/recovered/lead_notes_119_148.md`. In this order:
1. Run 11's calibration: `_SOAK_CYCLES = 80`, `_MEM_TREND_TOLERANCE_SD_MULTIPLIER = 4.0`, `_MEM_SAMPLE_INTERVAL_MS = 100`,
   gc.collect() kept (the lost B2c's values; the owner accepted their cost, 2026-10-23: "Question 1: This is okay, go
   ahead."). B2c's measurement evidence is lost, so the values are proven here: a planted leak (in a scratch copy) turns
   Run 11 red on dev at both stages, and the unplanted tree stays green at both stages; the old values (20 at 3.0) are
   run against the same plant and the result recorded. If the new values do not bite, stop and hand back.
2. The `TimeStale` checks (null in Run 1, false after Run 8's first sync), if not in the suite, seen failing first.
3. The twin FRAM chip: `save_state()` writes only the used span (the lost T4a measured 66.1 MB -> 274 KB per dev run,
   the host-wear rule); `writes_at` sized for its 2048-key cap at construction, with a heap-locked test that counts 2048
   new addresses (T4a2_final.md), red first at both stages. Then reproduce T4a2's evidence cheaply: the Run 13 erasefram
   cell at -1 replayed until either the old tree shows the red and the new one does not, or a stated number of
   replays shows neither (state the numbers).
4. Run 5b (T4a amendment 2 item 8): deterministic, or its comment and message state what it proves and cite
   `tests/test_digital_twin_fram_crash_points.py`; the conservative option, logged.
5. T4a items 4 (steps 167, 169, 170, 171) and T4b item 1 (the README texts) as V4 lists them
   (`S/u35r/verify/V4_handback.md`, steps 167-171), and the twin's "no REST route" comments for gc.mem_free() (the
   runner near :412, the suite near :210): /status publishes MemFree (buildgen/codegen.py near :293).
Checks: the suite's readers in tests_scripts, test_citations, test_decision_vocabulary, test_tunables_register, each
changed twin file at both stages; one dev twin CI run per stage at the end (`scripts/run_digital_twin_ci.sh dev`, inside
the namespace, a disk check first), zero memory markers. Not yours: src/, the F1r and F2r files.
