B2 hand-back (U33 lane B, block B2). Branch `audit/u33-b`, worktree `S/wt-u33b` (S = /tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad), created from c6b8a07 and rebuilt with `S/u23/rebuild.sh` (exit 0). Nothing pushed. About 67 tool calls.

**Commits:**
- `<CITE>` 939f78a was fast-forwarded in (`--ff-only`, since its parent is c6b8a07). That keeps it byte-identical to lane S's copy. Nothing later from lane S came in.
- 9dcd374, step 1b, applied. Four Deferred entries removed: buildspec, the loose end, the checkers and the segfault/soak entry (101 lines). Three allowlist rows left in the same commit.
- 695797a, steps 1a and 2, applied:
  - Items 32 and 44 are out.
  - T4 became its owed run in place, keeping its owner quote. F.3's `hold.fram_block` row also carries the quote.
  - The kick-then-reset bullet, the board-state sentence and the NTP-outage watch (R-8) are out.
  - Item (2) is now a row with its slots.
  - The 16 rows have their slots. `owed_slots.py` shows Expected, Wear and Twin row on every measurement row.
  - "Still owed elsewhere" became the budget, S4, G6 and F17 rows, in the bullet's order. Only H1 and "Excluded on purpose" remain.
  - L-1 applied: the command gains `--allow-persistence-write`.
  - L-2 applied: the row now names `tests_hardware/manual/manual_persistence.py`'s power-cycle step (it reads `AmbPres` around the cut, writes nothing, and reports whether the boot sends 0x0010). The `AmbPres` PUT stays owed, with its one SCD30 NVM write.
  - L-7 settled:
    - The `J.6` heading exists (SPEC:9369).
    - The codes are 9 for an incomplete command, 20 for C-stack exhaustion and 21 for a console interrupt (`src/asy_system_service.py`:88-91).
    - `run_bench_rollover_test.sh` passes `--allow-multi-day-rollover` and `--allow-flash-cycle` itself.
- e936618, step 3, applied:
  - B1's chroot paragraph is in (L-3). Its hosttools clause names the file as `hosttools_typecheck.ini` in `scripts/`, because a full path to a deleted file fails test_citations.
  - Entries added for `_cross_browser_probe.mjs`, `_twin_process.py` and `_port_lock.py` (the latter inside the 2026-10-15 list).
  - L-6: `scripts/test.sh` puts no Node on PATH. Three pytest files assert one (`test_cross_browser_smoke_probe.py`:24-25, `test_twin_process_js_spawn.py`:53-54, `test_live_twin_ceiling_parser.py` `_pinned_node()`), so I added one Node entry for the owner's run to settle.
  - The history query `c82149f..c6b8a07` now leaves 0 of 64 files unnamed.

**Seen failing first:**
- After the 1b deletions, `test_citations.py::test_the_allowlist_only_shrinks` named `('BACKLOG.md', 'Session 2')`, and `test_decision_vocabulary.py::test_the_allowlist_only_shrinks` named the "Deliberately does **not** use…" and "structurally incompatible.** It validates…" rows. Those rows were then removed.
- Item 32 on a tree without `<CITE>`: in a throwaway detached worktree at c6b8a07 (removed afterwards) with my BACKLOG.md, `test_every_citation_resolves_or_is_allow_listed` named `SPECIFICATION.md: BACKLOG item 32`. The same run also named `Session 2`, as expected since that tree still had the row.

**Checks:** test_citations, test_decision_vocabulary and test_legacy_paths on each head: 24 passed, exit 0. Times: 30.0 s on 939f78a (the first run, cold), then 23.7, 23.5 and 24.4 s. These are not B3's paired base/after times. Logs: `S/u33/laneB/b2_checks_{0..3}.log`, `b2_seen1.log`, `b2_seen2_nocite.log`.

**Decisions (agent, 2026-10-21):**
- T4 stays where its bullet stood. The four other rows replace the "Still owed elsewhere" bullet, in its order.
- The budget row keeps the owner's quoted words, sourced to BACKLOG at `569c6bb` (the commit that recorded them; `git show` confirms), rather than paraphrasing them.
- F17 keeps (3), the USB drop, and the archive §7R.5 source.
- The Expected slots with no value in their source carry "(agent, 2026-10-21)".
- The B1 bootloader claim "reset_cause() recorded" was not true of the test. The row says `ResetBits` is recorded instead.
- The M1 + S3b wear names the run's other persistence-gated flash tests, via the README budget table.

**State for B3:**
- Head e936618, nothing uncommitted.
- Allowlist rows removed: citation `BACKLOG.md	Session 2`; vocab `BACKLOG.md	Deliberately does **not** use the Unix-port twin's own…` and `BACKLOG.md	structurally incompatible.** It validates…`. Vocab :45 is untouched.
- Left for B3: CLAUDE.md (step 4 / E722, citation row :19, R-6 wozi), and lane B's complete checks: the 17 scans, the readers' paired times, the tier.
- On this branch alone, SPEC:10958 still points at BACKLOG's deleted buildspec "Deferred" account, and B.16 does not exist here. Lane S's e07098e (L.6.6) and 84dbb8a (B.16) fix both at the lead's merge. No check fails on either now.
- PROJECT_AUDIT_PLAN.md:2667 and :3293 quote removed BACKLOG lines. That file is not lane B's.

**Other:** Relay line written under `## B` in `S/u33/relay.md`. No real hardware was used. Silent-failure scan: documents only, nothing found. Effect by mode: none in any mode (STA/AP/Silent/Off/USB); no mode's behaviour is described differently. Nothing of mine is running.