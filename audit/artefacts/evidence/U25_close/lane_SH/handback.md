U25 lane SH final on audit/u25-sh (S/wt-u25sh): 1042ee1 (S1 shared twin helpers), f676468 (S: suite per device, runner, JS live commands, L0), fa31ee7 (H: host harness, in-DUT files removed, D.15 on every file). Nothing pushed; nothing of mine runs. Logs: S/u25/laneSH/.
Steps (16): applied 11: 74, 76, 79 (U25 stage), 80, 82, 83, 84 (U25 stage), 115, 132, 134 (U25 stage), 139 (U25 stage). Partly 2: 32 (only the U25 families (a)-(e), (l), (m) and (k); (f)-(j) and (1)-(3) belong to later units), 131 (the runner has no flag for the stall maxima, the over-cap trains or the free block: R/TWIN). Nothing at U25 3: 40 (stages U6/U8/U28/U36), 70 and 71 (U28, ci.yml is outside my set).
Deviations (agent, 2026-10-14):
- TwinRun landed early, in S1.
- The capability check reads only the file's xattr.
- Suite and harness each take a single `--gc-threshold` stage (for A-8 runs).
- `--only` refuses 5b or 4 when their producer run is missing.
- In the generated boot, "cause 3" is read as the mem-backup cause; ResetReason is asserted as _RR_TASK_BUDGET.
- Run 5 counts two events per failed read (READ + STREAK).
- Config writes PUT /system GMTOffset, because the product puts that field under section=system (the packet said /networking).
- Silent-chip erase: a refused erase may be followed by the dead chip's own escalation reset (ResetReason 5 asserted).
- The hang window is the reset deadline + 8.5 s, because the runner prints HANG when it arms, not when the step hangs.
- The refusal count uses slow healthy PUTs as holders (an unserved hang-up is itself a drop).
- The held-close burst fills the ceiling minus the probe's slot.
- The harness family banners are dropped for D.15, so scenarios run in alphabetical order.
Seen failing first:
- Frame: test_every_boot_ends_cleanly_or_by_a_claimed_exit failed 3 of 5 cases on the frame without its end checks (bites/frame/seen_failing.txt).
- Planted bites on dev, each failure naming its behaviour (harness_bite*_dev_neg1.out): negative Content-Length → "answered HTTP/1.0 200"; drop not counted → "HTTPDropped 0 -> 0"; ISL no-op PUT → "settings read … 16"; rx overrun → "56 ring laps"; both commands accepted → "['Valid','Valid']" ×2; reason forced to 3 → "relaunch reads ResetReason 3"; feed kept → "S6 watchdog never engaged"; refuse while paused → "did not answer Valid"; refusal stops the feed → "watchdog starved after a refused erase".
- Suite L0: seen_failing_suite_l0.txt.
Red checks:
- DNS scenario and suite Run 7: digital_twin/network.py:38 (AP 192.168.4.1/24) against src/asy_captive_dns.py:106-108, which drops 127.0.0.1 as off-subnet → MN/lead.
- Hung-step scenario: digital_twin/run_generic_integration.py:687 arms --test-shutdown-hang before setup (asy_system_service.py:677 replaces _tasks). S1 StopIteration at :460, S2 and S5reset IndexError at :462/:467, S3 blocks boot, S4 is inert. S5erase and S6 pass with it fixed → R/lead.
- Lead's stale rows:
  - _decision_vocab_allowlist.txt:154-156, :163 and the rows for deleted files
  - _citation_allowlist.txt:80-83
  - test_import_placement.py:36, :49, :65-66 and its F.1 list
  - digital_twin/typecheck.ini:60 (Any baseline)
  - test_no_variant_literals.py:38, :41, :46, :50-55
  - test_device_tomls.py:163, :171
  - tests/_port_bands.py:20, :26, :40
  - test_twin_entry_point_order (8 >= 10)
  - test_level_containment: E.6.6 rows for _run_12/_run_13, the per-device family, COVERS_TWIN_SCENARIOS
  - pyproject.toml:293, :385
  - tests/_sensortask_scenarios.py:362, :1582 cite deleted files
- Twin mypy pass: 88 errors in 5 tests/test_digital_twin_* files, none of them mine.
- Everything else in my scope is clean: ruff, the main/host mypy passes, shellcheck, npm lint/typecheck, lint-ceilings, comment cap.
Scan findings (all new; first five fixed and checked):
- Class 4, check matches nothing: Run 4's readings (_digital_twin_ci_suite.py:661); harness backlog `or True` let the stall end before the burst (_digital_twin_scenarios.py:373); ResetErrors precondition unchecked (:1065).
- Class 4, swallow: thread results lost (:997, :782, :1413).
- Aborted/incomplete twin: unclean SIGINT exit, missing shutdown line, unclaimed exit (:234-239, L0).
- Hook that raises: the runner's hang arming → R.
- Fake answers where silicon would not: AP ifconfig drops loopback → MN.
Facts owed to D: 33 tunables (new, moved and withdrawn, with value, site and basis) in S/u25/laneSH/tunables_SH.tsv. These include l0.live_smoke_timeout_ms=45000 at tests_js/live-backend.test.js:10 (measured 6.2-7.2 s on six devices); the SPEC :10757 and :10780-10783 sites; and :10842-10843 rows to retire.
Facts owed to the lead: R's responder writes CFGMGR_NTP W10×4 on every fresh boot. Library U24 parts are void (files deleted).
A-14 times:
- Suite, dev gc -1: 691 s (Run 11 184, Run 7 117 red, Run 9 93, Run 10 77, Run 13 74, 5c 62).
- Harness: wozi 435/445 s, dev 502/523 s (gc -1/32768).
- So about 38-42 min per device for both stages plus CRC16, over the line (U28).
- Family (a) on wozi: 120 s host-side against 40 s in-DUT (one boot per scenario).
Ported per family: (a) 20, (b) 8, (c) 9, (d) 1, (e) 2; new (l) 3, (m) 1, (k) 6; 50 in total.
Runs: 27 in RUNS.md, 10 rc=0 and 17 rc=1. Every rc=1 is either the DNS/hang reds above or a diagnosis or bite run, except one: wozi (a) failed held-close before its fix.
