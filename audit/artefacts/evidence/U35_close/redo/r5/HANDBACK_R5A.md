r5A hand-back, written by the agent (2026-11-05 11:03 UTC)

Commit `843eb19d` on `audit/r5a` (parent `932510fc`), not pushed. In/out: BACKLOG.md +3/-208, SPECIFICATION.md +26/-7, CLAUDE.md +8/-9, digital_twin/README.md +2/-3, tests_hardware/README.md +2/-2, scripts/run_digital_twin_ci.sh +2/-1, tests_scripts/test_comment_block_cap.py +1/-9, tests_scripts/test_counter_steps.py +3/-7, and +1/-1 in each of tests/test_asy_udp_socket.py, tests/test_ntp_wifi_dns_integration.py, tests_hardware/bench_control.py and tests_hardware/bench/test_network_resilience.py. Total +51/-250 (net -199). Every removed BACKLOG text is still in `932510fc`.

Findings rows:
- F1: D, already stated at `run_digital_twin_ci.sh:18`.
- F2: D, a comment at `:101-103` (agent, 2026-11-05).
- F4: listed. The fix is not at the head: `tests/test_asy_fram_allocation_budget.py:3` still says "any comparable per-call allocation".
- F5, F6, F7, F8: R, checked. F5 at `devices/dev.toml:66` (8192). F6 at `tests_hardware/README.md:1029-1034` (module runs whole). F7 at README `:308`. F8 at `buildgen/validate.py:536-544`; L.6.6 has no such line.

BACKLOG rows:
- B05: D. The trace is in SPEC F.1 (after the `.frozen`/built-in paragraph), checked against `S/tc-int/micropython` v1.29.0 (`py/frozenmod.c:85-87`, `py/builtinimport.c:368`). CLAUDE.md:95 now points to F.1.
- B06: listed. The golden fixture is not at the head (no `tests_scripts/golden/`; C.5 `:3408` says "from the release on"). Item 2 stays.
- B07: R. Placed at F.1, F.5 and README.md:231. Its 1.27→1.28 commit list went as history of the old pin.
- B08: D, F.3 "needs none (owner, 2026-08-11)".
- B09: D. The facts are at tests_hardware/README.md:1287-1295 (now dated 2026-09-08) and A.11 row 9. Three citers were repointed; the inventory's other two no longer exist.
- B10: D, at F.2 (`:6629`). CLAUDE.md:219 and `test_ntp_wifi_dns_integration.py:526` were repointed.
- B11: D, at the E.6.6 rows `bus-fault-injection` and `hotspot-multi-client` (owner, 2026-09-22). BACKLOG's "(item 8)" now points to E.6.6.
- B12: R. The facts are at tests_hardware/README.md:315, :658-662 and :698. The citer at `test_network_resilience.py:1040` now points to README's "Workarounds".
- B13: R, at tests_hardware/README.md:248. G6's "item 12" was repointed.
- B14: R, at C.7.1 (`:3786`).
- B15: R, a duplicate of README's "How a round runs" (`:435-452`).
- B50: D, F.5.2 (owner, 2026-09-24).
- B53, B61: R, removed.
- B54: R, at L.2 (`:10466-10478`). A.11 row 8 lost its pointer to the removed note.
- B55: D. F.5.8's no-wait sentence now carries "(agent, 2026-09-11)".
- B56: D, at the end of J.9 (agent, 2026-09-11). Checked against `src/asy_uart_driver.py:430-454`, `asy_framing_codecs.py:82-95` and the supervisor's one-time setup batch.
- B57: D. CLAUDE.md:961-964 now names standalone `device_scripts` runs.
- B59: O, already at J.1 (`:9446-9447`) and CLAUDE.md:144. Removed.
- B67: D. The uutils facts moved into B.10.1, under its existing (agent, 2026-10-20).
- B51 and B62-B66: O, unchanged. Their doc sites and cites were checked: README licences paragraph, `asy_system_service.py:110,115`, F.2, B.14.3 and B.14.4.
- B60: kept. Its own text says it comes out when the audit closes, so its terminal state comes at D.

Marker rows:
- X1: listed (W = Y).
- X2: R, already stated. The changelog's B33 (`:157`) says "The numbers in B10-B32 read through this table", and B34 (`:158`) shows the resync no longer persists. No edit, so the changelog test was not run.
- X3: F. Both empty sets were removed, along with their stale-entry halves.

Three more dangling pointers were fixed. One was already dead at `932510fc`: A.10:1398 now points to digital_twin/README.md. The other two died with this change: digital_twin/README.md:1146 and tests_hardware/README.md:1098.

Not fixed, outside my rows: five comments in `tests/` point to BACKLOG entries that no longer exist: `test_asy_captive_dns.py:241`, `test_asy_print_log.py:516`, `test_asy_sgp40_driver.py:222,587` and `test_asy_udp_socket.py:1744`.

Drifted rules: none found. BACKLOG's stub rule was kept and its example list now reads "(none today)". Item 2 is the only numbered item left, so whether the numbering paragraph should stay is a question for the owner.

Build-environment list: no entry added. The scripts/ change is a comment only, and the tests_scripts change is test-only.

Checks, 2 of 6 runs, all light:
- `r5A_checks`, covering the comment cap, counter steps, citations, decision vocabulary and the threat-model (THR) facts: 684 passed, 2 failed, both expected.
  - Citation allow-list: 1 stale entry, `BACKLOG.md HARDWARE_TEST_PLAN.md`, from item 8.
  - Vocabulary allow-list: 4 stale entries, from items 4 and 6, the UART-fakes entry and the UART-sensor entry.
- `r5A_lint`: lint_direct passed (rc 0) and the host mypy pass found 0 issues in 312 files.
- Tool help was not run because README.md is unchanged.

nothing of mine is running
