# Lane E: pause status (2026-10-08)

Worktree `scratchpad/wt-u21e`, branch `audit/u21-e`. HEAD is dd8202a, the merge of `audit/u21-api` at 1b43482, so T's final work is in. Nothing is committed past that merge, and no WIP E1 commit was made: the phase-2 instruction arrived before any edit. All edits below sit **uncommitted** in the worktree. Nothing was stashed.

**Nothing is running.** I started no background process, and `ps` shows no lane-E process. My only runs were the three foreground baseline pytests (decision_vocabulary 6 passed, citations 15 passed, legacy_paths 3 passed), all before any edit. I sent the A-21 freeze ack, and I have started no run since "A-21 done".

## Done (uncommitted)

**CLAUDE.md**
- Row 19: the anchor-check sentence gains the modlwip_eagain / issue 19704 clause, tagged (owner, 2026-09-30).
- B1: the dead-man's-switch rule now says the installer arms the switch itself.
- B1: "Two Unix-port binaries" becomes three. The 2026-09-21 owner tag stays on the settrace split; `build-lwip` is tagged (owner, 2026-09-30) and cited as SPEC B.14.4. The rebuild clause also covers a missing record or a missing `build-lwip`.
- B1: the stub bullet gains the printed version and `typings/.stub-spec`.
- Row 20: the trixie paragraph no longer names `_MBEDTLS_GCC14_ARRAY_BOUNDS_WORKAROUND`. It now says "suppressed for ctr_drbg.c alone by the build files micropython_overrides.py generates".

**BACKLOG.md**
- Row 1: the modlwip watch item is added at the end of "Deferred". Commit `6e79dcf9c` was verified in the pinned checkout: it swaps the sleep for poll_sockets() and keeps the 10 s limit.
- Row 18: two rows are added before "Still owed elsewhere": the modlwip stall (reproduce, then the override) and the `env --tier bench` bridge creation under its own timer. The stall row carries no `l4.` tag (A-19).
- Row 21: the 2026-10-08 chroot paragraph is added before "Kept here as the running list…", with the FBT outcome, the three host_typecheck.ini sections, the installer leg owed, and the man-page and `sudo -k` readings owed.

**README.md**
- Row 17 / B3: the `board` command line and help-text rows for `--micropython-ref`, `--latest` and `--clean` (three builds).
- The `test` paragraph now says "a few minutes", not "~30s". That figure was already stale before U21 (70-78 s); I will report it.
- New: the record and picotool lines, the flash and bench tier rows, and the command-check sentence.
- The `--device` row now gives the resolver order. The `--password` row is removed and a `BENCH_AP_PASSWORD` line added.
- The detection and credentials paragraph is rewritten (owner, 2026-10-02), and its example uses `BENCH_AP_PASSWORD=<psk>`.
- The bridge paragraph now says every bridge change runs under the timer.
- Node: SHASUMS fetched once, plus the node record.
- build_firmware: the lock, the record refusal and the record print.
- The serial-access paragraph now describes the resolver and `board`.

**tests_hardware/README.md**
- Row 23: item 1 points to `_TIER_COMMANDS`, and the resolver is added.
- New item 2: passwordless sudo (the `sudo -k -n` probe, a sample sudoers line with placeholders, each command's reason).
- Old items 2-4 are renumbered 3-5, and the "Prerequisites item 2" citation becomes "item 3".
- Item 4 (picotool): USB-less is refused in flash/bench and only warned about in setup/generic; skipped when the tag is current; shadow warning. The sandbox narrative is gone.
- Row 76: in "Host network", the installer arms its own timer, plus the PSK lines (owner, 2026-10-02).
- Row 24: the `BENCH_AP_PASSWORD` bullet gains "env --tier bench reads the same variable".
- MPREMOTE_DEVICE bullet: the now-false "so the two cannot disagree" is removed, and a note on the installer's narrower resolver is added.

**HEAP_FRAGMENTATION_MEASUREMENTS.md**
- Row 16: the three builds, citing SPEC B.14.4.
- New fact: every setup or test run removes the ad-hoc `build-nosettrace`/`build-heapprobe32` dirs as leftovers.

## In progress / still to do

- **Proofread the last edit.** `tests_hardware/README.md`, "Environment variables": the `BENCH_AP_PASSWORD` bullet's lines need a rewrap.
- **Remaining greps** for U21-renamed names: only the dated BACKLOG history line ~399 remains, which is kept on purpose.
- **Pre-commit checks**, none run yet on the edited tree:
  - test_decision_vocabulary, test_citations, test_comment_block_cap, test_tunables_register, test_legacy_paths, test_import_placement, test_code_conventions, test_host_annotations, test_tool_help, test_lint_ceilings, test_mypy_any_baseline.
  - Expected red: test_citations on "SPECIFICATION.md B.14.4" (CLAUDE.md, BACKLOG.md, HEAP), until lane D's B.14.4 heading merges. test_tunables_register is red on D's Part N rows.
- **Commit**, then the silent-failure scan section, then the final report to `scratchpad/u21/reports/E.md`.
- **Findings to report:**
  - CLAUDE.md recipe comment "apt_packages, used by both its setup/test subcommands": `test` runs no apt. This was already false before U21.
  - The HEAP twin recipes' global `-Wno-array-bounds` is now redundant (not false).
  - The sudoers rule for `timeout`/`tee`/`systemd-run` grants root for anything (a security note).
