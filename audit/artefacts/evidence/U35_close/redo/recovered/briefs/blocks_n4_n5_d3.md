# Briefs N4 (W7), N5 and the D3 amendments (recovered verbatim from the lead's context, 2026-10-26)
[The snapshot copy S/u35/briefs/blocks_d3.md holds D3's original 34 lines; the amendments follow. Line numbers refer to
the lost heads.]

## blocks_n4.md: N4: the ResetErrors probe holds NTP still; test.sh's tier order; the tier's host writes (lead, 2026-10-22)
- Base: `ac0ad4c` (audit/u35-b2's head: 7851668 + B2a). Branch `audit/u35-n4`, worktree `S/wt-u35n4`, already rebuilt;
  its node_modules links to S/wt-u8's (lock hashes equal). Logs in `S/u35/laneN/n4/`. Commit subject
  `U35 lane N4: <summary>`; decision tags "(agent, 2026-10-22)". Text outside `audit/` cites no audit ID, lane or plan.
- Read first: `S/CHECKLIST.md` (binding), `S/u35/briefs/common_u35.md` (its Rules only), LEAD NOTES 122 and 123 in
  `S/u35/lane_plan.md` (the root cause and its evidence), and `S/u35/handbacks/B2a_final.md` ("For you").
- Your files: `tests_js/live-backend-put-matrix.test.js` and the tests_js helpers it imports, `scripts/test.sh`,
  `tests_scripts/test_test_sh.py`, and for item 3 only the tests_scripts files whose writes you measure. Not yours:
  `src/`, `digital_twin/`, SPECIFICATION.md (a sentence your change makes stale goes in the hand-back for D3).
- The host is shared with block B2b: one test run at a time in your worktree, every port-binding run (npm test,
  test.sh) inside `unshare -n S/u24/ns_xdg.sh`, under `nice -n 19`, each with its RUNS.md start and exit lines.
1. **The probe holds NTP still.** On arzi the string case leaves NTPHost at a name nothing in the twin's namespace
   resolves, so the unsynced client retries on its backoff and logs E73 by itself; the ResetErrors probe turns the
   backups off but not this. Test first: before the archive and the reset, the probe reads NTP as synced and fails
   with a message naming NTP if it is not; seen failing on the current probe (arzi's run reaches the probe unsynced).
   Then the fix: the probe points NTPHost back at the twin's local responder through the page, as a visitor would,
   and waits, bounded by a `@tunable` named like the file's others, until the status page shows it synced. Take the
   responder's address from one source: a JS value the twin harness already holds if there is one; else one named
   constant citing `digital_twin/unixport/_offline_ntp_config.py`'s `_RESPONDER_HOST`, kept equal by a check where
   the repo already pins such mirrors. No errcount row is filtered or excused. The helper's comment
   (`turnBackupsOff`, :221-222) states both counters that climb by themselves and drops "The twin has no NTP" (the
   twin boots synced to its responder). Bite: with the new step removed, the synced check fails deterministically;
   restored, the file passes. Then `npm test` once, whole, plus the JS lint and typecheck.
2. **The tier order.** `scripts/test.sh`'s comment says the backgrounded tests_scripts tier needs nothing from the
   frozen-module steps; 25 tests fail and 1 errors without frozen_modules (`S/u35/laneB/b2/runs/L0_pytest_nofrozen.log`),
   and it holds only because those tests start long after the build ends. Make the dependency structural (the tier
   starts once the frozen-module build has finished, or waits for it) if one measured `scripts/test.sh` run at -1
   shows no wall-clock cost beyond noise against B2a's 1350.2 s (state the noise you assume); otherwise keep the
   order and make the comment state the dependency and why it holds. `tests_scripts/test_test_sh.py` pins the result
   and a planted regression (the tier started before the build) fails it.
3. **The tier's host writes.** A full tests_scripts session leaves about 340 MB of tmp_path trees
   (`/tmp/pytest-of-root`; B0 measured 81.5 MB for the tier). Measure per test file the bytes its tmp_path trees hold
   (a session's retained basetemp, `du`; no SSD-churning re-run beyond one session), name the shape that writes most
   (a whole-tree copy where the test plants one file, say). If one shared helper or fixture is the source and the fix
   is local to it, fix it so each test copies only what its invariant needs, every assertion kept and its bite shown;
   otherwise record the table and the shape, with no change. CLAUDE.md's host-wear rule is the bar.
Checks: ruff and the host mypy pass on changed Python files; eslint and the JS typecheck on changed JS; test_test_sh,
test_citations, test_decision_vocabulary, test_comment_block_cap and every tests_scripts reader of a file you changed.
Hand-back (at most 30 lines): commits; item 1's test-first and bite results and the npm counts; item 2's measured
wall and the choice; item 3's table (top files, bytes) and what changed; anything for D3 with its line.
[Outcome known only in part (summary): N4 merged into int as 33d9ad8. Its hand-back named a guess about the hotspot-exit
window (lines 7-8), which F1 disproved. Item 1's root cause (LEAD NOTES 122-123, lost): arzi's string case leaves
NTPHost unresolvable, so E73 climbs by itself; the ResetErrors probe did not hold NTP still. Items 2 and 3's results lost.]

## blocks_n5.md: N5: no test picks its device by name (lead, 2026-10-23)
- The decision (owner, 2026-10-23): [the final device-selection description, verbatim in
  recovered/owner_rulings_after_LN118.md] And (owner, 2026-10-23): "So target minimal changes." LEAD NOTES 130 has the facts.
- Base: the head the lead names when starting you. Branch `audit/u35-n5`, worktree `S/wt-u35n5`, already rebuilt.
  Logs in `S/u35/laneN/n5/`. Commit subject `U35 lane N5: <summary>`; decision tags "(agent, <date -u>)".
- Your files: the test files named below, for their device choice only. Not yours: `src/`, `digital_twin/`,
  `scripts/`, `tests_js/` (the matrix dedupe fits the decision and stays), SPECIFICATION.md (stale lines to D3).
1. **Picks by name.** `tests/test_digital_twin_machine.py:376, 389, 626, 1228` ("dev"/"wozi" as fixtures) and
   `tests/_boot_contiguity_probe.py`: where a test takes a device by its name, it takes it by the hardware it needs
   instead (the first derived device wiring it, `tests/_twin_devices.py`'s helpers), every assertion kept. A name used
   only as a label or as data that no device choice depends on stays; say so per site. Grep `tests/`, `tests_scripts/`
   and `digital_twin/`'s test helpers once more for other name picks and treat them the same.
2. **Read, report, do not change.** For each other one-device pick (`generated_devices()[0]`, `device_with()`,
   `_driver_specific()`, `_first_device_only()`, `DEVICE_IDS[0]`, `test_digital_twin_fram_crash_points.py:221`,
   `scripts/test.sh:181`), one line: does what it exercises match on every device it stands for (the decision's
   pattern), or is there a device whose own wiring of that part differs (for example a shared bus where the picked
   device has its own)? Cite the plan facts. No edit.
Checks: ruff and mypy on changed files; each changed test file at both GC stages; test_citations,
test_decision_vocabulary, test_comment_block_cap and every tests_scripts reader of a changed file.
[Outcome known in part (summary): N5 (3640ff7) gave tests/test_digital_twin_machine.py `_BOARD`, `_ISL29125_BUS` and
`_board_plan(**buses)`, which returns the first generated device wiring exactly the given (driver, address/max_size) per
named bus and raises an AssertionError listing the devices searched; `_wire(**buses)` returns the plan. Its item 2
"Differs" list went to CM (CM_final.md lists the sites). Its `_board_plan` spi comprehension at :121 tripped
test_twin_wiring_contract's scanner (a false positive, CM2 item 1).]

## D3 amendment (lead, 2026-10-23): how tests pick devices
The owner's decision (LEAD NOTES 130) lands once, in SPECIFICATION.md E.2.1 where the one-device scenarios are
described, quoting the owner's words with the date (owner, 2026-10-23: "They shall all be treated the same, only
depending on their hardware configuration. But matrix deduplication is something different! ... then it is a good
thing as it saves time and is not actually device specific."); SPECIFICATION.md:8142-8143 (the live matrix's dedupe)
cites it as its actor. No CLAUDE.md change. Any line N5's hand-back lists as stale is brought in line with the tree.

## D3 amendment 2 (lead, 2026-10-23): E.5.1 from CE
Items 5 and step 111's register text come from `audit/b3/e51.md`'s "For D3" section on audit/u35-ce and
`S/u35/handbacks/CE_final.md`/`CE2_final.md`: the tracer classes checked at v1.29.0, the tracer death, the register's
kept lines, the lines that leave it, and E.5.3's sentence for the dead-tracer detection. Item 5's two sites:
`src/asy_wifi_service.py:652-653` executed at gate 2 (no line); `src/asy_isl29125_driver.py:1496` reached only by a
direct test (no keep line; its removal is routed).
From CE2 (`S/u35/handbacks/CE2_final.md`): E.5.3's code-3 row covers a report left incomplete by a dead tracer as well
as a failed rendering; E.10's result text "PASS (coverage report not rendered)" (`scripts/_summary_block.sh:139`,
`scripts/_summary_block.py:102`) is printed for that case too; E.5.1's tracer-death line and `tests/_untraced.py`.
[Later D3 inputs from the hand-backs: F1 (drop sgp40:697 from E.5.1; keep lines for scd30:735, uart's three
`if not want:`, isl 1217-1223, webserver :425 and :903; system:441 reachable by a cancel); CM (E.2.1: driver-specific
scenarios run on every device wiring them); CR4 (tests_hardware/README.md :1936 paragraph; SPECIFICATION.md:12234-12236
stale against the suite's tags 80/100/4.0); T4a2/T4b2 (none new); F3 (G.2, C.7/C.7.1, I.4(e), A.5 lines).]
