# SGP40 config tests failing intermittently at the U16 merge: root cause

Seen: `test_set_dict_cfg_works_out_of_the_box_with_zero_driver_changes` (and, in repeats, other config-writing
tests) failed on the merged U16 tree, the lane S tree and the U15 tree (first_seen_merge_t.log, sgp_rc/, sgp_base/).

Cause: the lead's own run procedure. The default and 32768 runs of `tests/test_asy_sgp40_driver.py` (and later six
repeats) ran at the same time in one worktree. `tests/_tmp_scratch.py`'s `TmpScratch("sgp40")` owns
`tests/_tmp/sgp40/`, wipes it at construction and numbers its subdirectories per process, so two processes of the
same file delete and reuse each other's config directories. `scripts/test.sh` runs each file once per tree, so the
supported path never does this. (The u16base column fails 35 tests for a different, expected reason: that tree is the
WIP API base, its SGP40 tests predate lanes M/S.)

Proof: serial runs, one process of the file per worktree at a time (sgp_serial/): merged tree 155/155 three times at
each stage, U15 tree 144/144 three times at 32768, readiness gates 14/14 at both stages; no MemoryError or
"memory allocation failed" in any log. Not a firmware or test defect; the rule "no two runs in one worktree at the
same time" covers it.
