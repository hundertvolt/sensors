# Gate harness race: the typecheck regenerated build/generated_src while test.sh imported from it

Seen: U13 gate0 (gate_v3.sh on fe24d3d), test.sh at -1: all 68 tests of test_sensortask_klkizi failed with
"AttributeError: module 'sensortask_klkizi' has no attribute 'build_system'" (the first file run, log line 33); the
same file passed at 32768 and the klkizi twin passed.
Cause: gate_v3.sh ran lint + typecheck in wt-u8 concurrently with test.sh -1 in the same worktree. scripts/typecheck.sh
(:133-134) regenerates build/generated_src via scripts/_generate_sensortask_modules.py, which rewrites each module with
Path.write_text (truncate, then write). An import landing in that window loads an empty module.
Reproduced (repro_counts.txt): 30 regenerations, a reader polling sensortask_klkizi.py saw 537 empty reads among
9,193,868 (no partial non-empty read). Not a product or test defect: a harness isolation breach (one worktree per
concurrent run, gate_isolation.md), present in gate_v3 and gate_v4; the pilots did not hit the window.
Fix: gate_v5.sh runs lint + typecheck in their own worktree (wt-lint).
