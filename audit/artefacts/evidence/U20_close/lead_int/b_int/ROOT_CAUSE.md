# B's three files on audit/u20-int 35ed863: concurrent-run failures, root-caused

First run (logs in this directory): the three stages of each file ran at the same time in one worktree.
- test_asy_config_manager: gc 32768 45 failed, settrace 47 failed; test_asy_base_classes: 5 failed at each; all `OSError: ENOENT`.
- test_asy_webserver_service: 1 failed at all three stages, `('erasefram', [False, False])`.

Cause: tests/_tmp_scratch.py gives each test FILE one fixed directory, tests/_tmp/<key>/, wiped at construction and at
teardown_all(). Two processes of the same file share it: one wipes the other's files (the ENOENTs), and in the webserver
file one process's `resetconfig` case deletes both config files at the paths another process's `erasefram` case expects
to find. scripts/test.sh runs each file once, one process per file, so CI and the gate never do this; the session rule
"no two runs in one worktree at once" covers it. Lead's run, not a product or test defect.

Sequential re-run (seq/): every stage of every file green - config_manager 232, base_classes 187, webserver 217, at
gc -1, gc 32768 and settrace; zero memory markers. Webserver wall 28 / 28 / 66 s at nice 19 under lane load.
Parallel stage runs go to separate worktrees (as the gate's wt-u8 / wt-u7g / wt-cov do).
