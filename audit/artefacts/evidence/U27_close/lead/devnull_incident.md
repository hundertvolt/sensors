# /dev/null replaced by a regular file (found 07:05, 2026-10-15)

- State: `/dev/null` a regular file, mode 0644, inode 122, birth 04:13:31.61 (= /dev's mtime, the last entry change there).
- Cause: the U27 planning agent (file-only, lead-launched) ran at 04:13:31.022
  `mv ../pk/packet_laneLEAD.md /dev/null 2>/dev/null` as a discard idiom (its transcript line 424). mv across filesystems
  unlinks the target and copies: the character device was replaced by a regular file holding the packet; later `>/dev/null`
  redirects truncated it, `>>` appended, and readers (`</dev/null`, `GIT_CONFIG_GLOBAL=/dev/null`) got the content.
- Seen: lane T 06:56, test_hardware_runners.py 37 errors "fatal: bad config line 1 in file /dev/null" (git init under
  GIT_CONFIG_GLOBAL=/dev/null), passed at 06:52; lane T's attempts to restore (mknod) and rerun were refused by its
  permission check.
- Window: 04:13:31 to the restore. Runs in it: the U27 base sweep (04:30-04:55, all rc 0), lane T T1 and Part 2, lane U
  (82/82 both stages), the API checks, the private toolchain test, lanes B and S so far.
- Prevention: never mv/cp/redirect-replace onto a device path; discard with `rm` of literal paths. Every gate and merge
  check starts with `[ -c /dev/null ]`.
- Restored: a container restart at 07:00:39 recreated /dev (character device 1,3, mode 666); the owner's go-ahead to restore
  ("Restore now (Recommended)", 2026-10-15) arrived after it, so no device command was run.
- Lane reports: B's stub `uv` in test_typecheck_sh appended to /dev/null (fixed in f4f6a49); S's shell writes into it were
  ordinary `>/dev/null` redirects. Reruns owed at <W1>: lane T's test_hardware_runners.py and its six reordered files.
