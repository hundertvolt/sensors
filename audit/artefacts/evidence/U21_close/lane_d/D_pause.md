# U21 lane D: pause status (2026-10-08)

Worktree `scratchpad/wt-u21d`, branch `audit/u21-d`.
- HEAD is 20c85cb, the merge of `audit/u21-api` at 1b43482, which brings T's final.
- Checkpoint commit: e9c4fd7 "U21 lane D WIP D1".
- Uncommitted edits: `SPECIFICATION.md` only, left as they are. Nothing is stashed.

No process of mine is running. The MicroPython runs visible in `ps` have their cwd in `wt-u8` and are not mine. Lane D started no MicroPython, toolchain or background run at any time.

## Done

**Committed in e9c4fd7 (phase 1):**
- B.1, B.3 step 3 and F.1: the picotool rule.
- Part F's opening checklist, and F.1's closing practice paragraph deleted.
- B.7: the warning-free sentence and the host lwIP build's two flags.
- B.7.1: branch 2b corrections.
- B.10: the cache key.
- B.11: the re-check clause, the lock, the record, and rename.
- B.14: intro, why-not and general shape.
- B.14.1: the per-build readback. B.14.2: the generated-file facts.
- B.14.2.1 and A.5: the send stall.
- New B.14.4 (`modlwip_eagain` plus the host build) and B.14.5 (`tick_offset_test`).
- H.7: the send path.
- F.7: row 14, and rows 23-30 (the host lwIP build).
- F.9: rows for SIGINT, mbedtls, modlwip and the host flags, and the settrace row reworded.
- E.1, E.3, E.5.2, E.6.1 (the L1 row) and E.10.
- B.15: the stub record.
- Part N: the 7 `l1.lwip_host_*` rows and the `tool.preprocess_timeout_s` dependants.

**Uncommitted (phase 2, after T's merge):**
- B.2: quick-start comments, the `board` line, three flavours.
- B.3: the pin writer, the typed table, the record, the lock, notices, clones.
- B.4: budgets, streaming, sessions, signals and the SIGKILL limit, retries, secrets, apt.
- B.5: tree lines, the lock, picotool, Node, leftovers.
- B.6: three Unix ports and the readbacks.
- B.12: resolver, `board`, `$BENCH_AP_PASSWORD`, the command table, the sudo probe.
- B.13: the installer arms the switch.
- A.1: the tree line.
- Part N: 8 new `tool.*` rows, plus updates to `tool.uv_sync_attempts`, `tool.uv_sync_backoff_step_s` and `tool.apt_acquire_timeout_s`.
- `test_tunables_register.py` was green (15 passed) right after these edits.

## Still to do on resume

- Rewrap a few over-wide lines, including B.4 near "SIGTERM and SIGHUP".
- Re-read every new section against the code once more.
- Run the brief's pre-commit checks:
  - `test_decision_vocabulary`, `test_citations`, `test_comment_block_cap`, `test_tunables_register`, `test_legacy_paths`, `test_import_placement`, `test_code_conventions`;
  - `test_host_annotations`, `test_tool_help`, `test_lint_ceilings`, `test_mypy_any_baseline`.
- Commit the phase 2 work, then write the final report to `scratchpad/u21/reports/D.md`.
- Known differences between T's report and the code, to report: T lists the tar unpack under the remote-query budget, but the code uses the build budget. T lists the frozen-verify run under the build budget, but the code uses the remote-query budget. The SPEC follows the code.
