Lane D hand-back (U25). Worktree S/wt-u25g. Nothing pushed, no hardware touched, nothing of mine still running.
Commits on top of a8dc1a1:
- 6c0efc7: SPECIFICATION.md (A.10, B.11, B.14.1, B.15, E.1-E.4, E.6.5/E.6.6, F.1/F.2/F.6/F.9, H.7, I.4(f.1), J.7, L.4, Part N)
- 4f8b451: CLAUDE.md, README.md, BACKLOG.md (incl. the chroot entry)
- 6417e17: digital_twin/README.md rewrite + SPEC E.8/E.9 wire_log
Steps by verdict:
- X (6, 15, 23-25, 42-49, 126-128, 133), Y (1, 33, 34, 125, chroot) and W (118, 119, 124, 96-98, 129, 130, 135-137, dropped-by-design, BACKLOG, subtleties, shim sites, cyw43) are all done.
- Already landed, verify-only: A.7 keywords (SPEC ~650), C.12 (~3788-3792), I.2 (nothing to do).
- Step 35 (grkizi owner question) is waiting: no A-15 message from you yet. Your run is still going; a15.txt shows gc=-1 rc=0, and 32768 is at repeat 05/50.
Deviations:
- Kept a stub "Known gaps" heading in the twin README, because 8 test files cite it.
- E.8/E.9 wire_log said "unbounded"; it now says bounded at 4096 B per direction (left stale by U24).
- Gave subtleties an `sgp40` account: `_digital_twin_ci_suite.py:134-135` cites one the README never had.
- Run 5b loss restored as "accepted (owner, 2026-09-11; confirmed 2026-09-26, paraphrase …)", matching SPEC A.4. My draft had quoted the paraphrase as the owner's words.
- Not applied: A.U25.61 flash check (U26), M.TWIN.064 Run 1 NTP sentence (U35). M.TWIN.072's pointer stays C.11.
Seen failing first:
- test_citations: 1 failed
- test_tunables_register: 1 failed (tags vs rows)
- test_level_containment: 2 failed (coverage/exception row; named scenario exists)
- test_import_placement: 1 failed
- test_decision_vocabulary: red after X+Y (stale allow-list)
After W, 11 of 13 are green:
- tunables 15, level_containment 22, import_placement 7, comment_block_cap 491, legacy_paths 3, code_conventions 25, error_catalog 40, host_annotations 12, lint_ceilings 19, mypy_any 7, mem_gate 13
- All runs under 20 s; after-times are pytest's own (no /usr/bin/time on this host).
Red, waiting on you (allow-list shrink only: no new hits, the entries just no longer occur):
- test_citations::test_the_allowlist_only_shrinks: `tests_scripts/_citation_allowlist.txt:79` (digital_twin/README.md WP1)
- test_decision_vocabulary::test_the_allowlist_only_shrinks: `tests_scripts/_decision_vocab_allowlist.txt` lines 51, 56, 118, 120-125, 127, 129, 133, 136
Scan: docs only, no silent-failure findings in my five files.
Facts owed / found outside my set:
- tests/_port_bands.py still lists the retired test_digital_twin_real_website_integration and _webserver_concurrency_scenarios (also in PER_DEVICE_OWNERS).
- tests/test_digital_twin_wifi_modes.py:236-238 comment is stale: the AP now reports STAT_GOT_IP.
- tests_hardware/flash/test_fram_storage.py's reset-race test could declare `fram_crash_points`.
- bench/test_uart_link_under_api_load.py partly covers uart_load.
Runs: no run of mine went over a minute, so no RUNS.md lines.
