# D: close-out steps (lead draft, 2026-11-12; nothing here runs without the owner's agreement)

## Preconditions
1. The bench round is read: 10g, k (noble + trixie legs), the wear steps (7b, 8f, 8b CRC-16, 10b, 15; 7f if run).
   A firmware red from them reopens work before D; a test-side red is recorded.
2. CI green on the final snapshot (snapshot 66 = 503c9c83 or its successor); P01 green on the final int head
   (gate66 green on 67e47fa6; 7c142edd changes one test line only: covered by its own 5+5 runs and snapshot 66's CI).
3. The owner agrees to close (and decides what happens with the later-window items: j, 7f if not run today,
   16b's power-cycle half, 13).

## Records (inside audit/, in the archive commit)
4. Final report: S/u35r/r5/W3A/REPORT_DRAFT.md with the <BENCH>/<D> placeholders filled, committed under
   audit/ in the last commit that holds audit/.
5. Record corrections owed before the archive commit: OF-16's two record lines (report section 2); the
   load.md captive-DNS flood cell (justified or a gap, report section 5); the 11 DNR rows not located by search.

## Branches (never deleted)
6. `claude/u35-audit-archive` = the last commit holding audit/ and PROJECT_AUDIT_PLAN.md, pushed.
   Kept beside it: `claude/u35-bench-campaign` (bench evidence) and `claude/u35-int-backup` (integration history).

## The delete commit (on top of the archive commit)
7. Delete `audit/` and `PROJECT_AUDIT_PLAN.md`.
8. Outside audit/, the only references (git grep at 7c142edd):
   - README.md:1281-1283 "Further reading" entry for PROJECT_AUDIT_PLAN.md and audit/: removed.
   - tests_scripts/_repo_scan.py:27-28 and tests_scripts/test_import_graph.py:24 exclude "audit/" and
     "PROJECT_AUDIT_PLAN.md": left as they are (excluding a path that no longer exists is harmless and keeps a
     restored archive out of the scans) - or removed, owner's call; recommendation: leave.
9. Checks on the delete commit: lint, three mypy passes, tests_scripts readers, the twin CI on dev; CI on the push.
   Dry run done 2026-11-12 09:44 on e763e46e (49cdd0e3 minus audit/, PROJECT_AUDIT_PLAN.md, README:1281-1283):
   the full gate (unit at both GC stages, twins at both, web tier) plus lint, three mypy passes and readers, green.

## Release
10. One merge into `main` (pull request hundertvolt/sensors#107, retitled and described as release 2.0); the owner
    merges. Version 2.0 is already in buildgen/version.py; README's "Release" section is the release note against
    the legacy firmware.
11. Tag `v2.0` on the merge commit: the owner (tag pushes from this session are refused, 403).
12. After the merge: CI on main green; the later-window bench items stay in BACKLOG.md's "Real-hardware work
    still owed".
