# U35 lane H, block H4: a dying reader thread fails its test; the twin record re-recorded (lead, 2026-10-22)

- Base: the integration head the lead names when starting you (G2 and G3 merged). Branch `audit/u35-h4`, worktree
  `S/wt-u35h4`, already rebuilt. Logs in `S/u35/laneH/h4/`. Commit subject `U35 lane H4: <summary>`; decision tags
  "(agent, 2026-10-22)". Commit messages and every file outside `audit/` cite no audit ID, lane or temporary plan.
- Read first: `S/CHECKLIST.md` (binding), `S/u35/briefs/common_u35.md` (its Rules), `S/u35/handbacks/H3_final.md`
  (its class-4 list), LEAD NOTES 58 and 112 in `S/u35/lane_plan.md`, the OF-260 row
  (`S/wt-u35rec/audit/sweeps/open_findings.md:268`), and `tests_hardware/README.md`'s twin section.
- Your files: `tests_hardware/conftest.py`, `tests_hardware/twin_record.json`, the hardware suite's tests_scripts
  readers, and a thread target in `tests_hardware/` only if a death you unmask is that test's own bug. Not yours:
  `src/`, SPECIFICATION.md (a sentence your change makes stale goes in the hand-back for D3).

1. **The warning is an error.** `tests_hardware/conftest.py` turns pytest's `PytestUnhandledThreadExceptionWarning`
   into an error for the whole hardware suite, in one place (its `pytest_configure`), so a reader thread that dies
   fails the test it ran under instead of leaving a warning. The pinned pytest 9.1.1 raises the warning when it is
   filtered as an error (`_pytest/threadexception.py:58-67`). The comment there stays within the 3-line cap.
   Seen biting first, through the twin and never on hardware: a scratch test in a throwaway copy whose thread target
   raises passes with only the warning on your base and fails with the change. Then a planted death in one real
   class-4 reader (H3's list) in that scratch copy fails its test.
2. **The re-record.** G2 and G3 change `src/asy_fram_manager.py`, `asy_system_service.py` and `asy_webserver_service.py`, which 27 device
   scripts import, so the record's hashes are stale (`tests_scripts/test_twin_record.py:69`). Re-record at both GC
   stages with H3's script shape (`S/u35/lead/record/record.sh` is the lead's copy: point it at your worktree and
   your log folder), with `S/u35/laneH/h3/reasons.json`. About 35 minutes; one run, in its namespace, at nice 19.
   Compare with the base record: every changed result is traced to its cause. A result that turns red because a
   thread death is now an error gets no reason until root-caused: a cause in the test's own code is yours to fix,
   test first; a cause in `src/` or the twin goes in the hand-back with its evidence, never retried and never
   reasoned away. Count `PytestUnraisableExceptionWarning` in the record's logs and report the count with each test
   it names (no change for it).
3. **Checks.** ruff and the host mypy pass on the changed files; the hardware suite's tests_scripts readers
   (test_twin_record, the runner and marker tests) and `tests_hardware` with `--collect-only`.

Rules: never run real hardware tools (mpremote, picotool, nmcli, iw, iptables) and `tests_hardware` only through the
twin or `--collect-only`; never read arduino/; never edit ext/ or legacy/; no git stash; kill only by a pid you
checked; one test run at a time in your worktree; port-binding runs inside `unshare -n S/u24/ns_xdg.sh`; every run's
start and exit line in `S/u21/RUNS.md`; CHECKLIST 22's disk check before the re-record. Do not push. About 60-80 tool
calls; past 80, commit what is green and hand back the rest at a seam.

Hand-back (at most 35 lines): commits; item 1's bite results; the re-record's wall, results per stage and every
changed result with its cause; the unraisable count; anything for D3 with its line; last line "nothing of mine is
running".
