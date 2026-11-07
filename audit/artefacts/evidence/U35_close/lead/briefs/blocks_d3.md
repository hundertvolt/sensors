# U35 lane D, block D3: the measured values in the documents, then D's scans (lead, 2026-10-22; D's last block)

- Base: `audit/u35-d2` fast-forwarded to the integration head the lead names (B2 and T4 merged), rebuilt, in
  `S/wt-u35d2`. Logs in `S/u35/laneD/d3/`. Commit subject `U35 lane D3: <summary>`; decision tags "(agent,
  2026-10-22)". Your files: SPECIFICATION.md, BACKLOG.md, tests_hardware/README.md, CLAUDE.md where a step names it.
- Read first: `S/CHECKLIST.md`, `S/u35/briefs/common_u35.md`, `S/u35/handbacks/D2e_final.md`, the B2 and T4
  hand-backs the lead names (their values and stale sentences, each with its source log), and each step's text
  (`python3 -I S/u35/tools/steps.py --standing <numbers>`) with its P1 row in `S/u35/lane_plan.md`. Check each against
  the tree first and write only what is missing.
1. Steps 146, 147 and 105: E.3.1's history from `audit/b3/timing.md`, and Part N's `l0`-`l2` Basis cells B2c measured,
   each cell citing its source as the neighbouring rows do; a row B2c could not measure keeps "estimated".
2. Steps 161 (E.1's clause that the heavy-file dispatch list is checked against the file set), 162 (E.9's calibration
   clause) and 163 (I.4(e)'s outcome over the sparser sampling interval), from B2c's figures.
3. Step 159 only if B2c found no sampling interval with Run 11's verdict: then hand back the facts the owner question
   needs (decision in at most 10 words, options each with its consequence per device); the lead asks it.
4. Step 158: BACKLOG.md's running list of build-environment changes since the chroot legs were last satisfied gains
   every U35 change to `pyproject.toml`, `scripts/`, `toolchain/` or the lock (`git diff --stat 49fde7b..HEAD` on those
   paths; 49fde7b is U34's pushed head).
5. E.5.1 against gate 2's coverage report (`S/u35/gate2/coverage.log` and its report files): whether
   `src/asy_wifi_service.py`'s `_push_wifi_led()` False arm and `src/asy_isl29125_driver.py`'s unreachable persist
   fallback are listed as they must be; add what is missing with its reason.
6. Every stale sentence B2 and T4 handed back, at its line. The FRAM loss rate's sentence (D3g's hand-back gives its line) takes B2c's re-measured value;
   the owner's acceptance around it keeps its actor, date and scope.
6b. tests_hardware/README.md states that a thread which dies fails the hardware test it ran under
   (`tests_hardware/conftest.py:110-112`, H4).
7. At the end, the 17 repo-wide scans once (`S/u32/briefs/common_u32.md`, "Before your lane's final"), on your head, in
   one process. Expected red: none.
Rules: owner decisions quote the owner's words and the question; a paraphrase is marked "paraphrase"; nothing cites an
audit ID, a lane or a temporary plan; doc lines about 100 characters. Checks after each commit: test_citations,
test_decision_vocabulary, test_legacy_paths, test_tunables_register and the readers of each section you changed. Never
run real hardware tools; never read arduino/; never edit ext/ or legacy/; no git stash; do not push. About 60-80 tool
calls; past 80, commit and hand back the rest. Hand-back at most 35 lines: commits; per step landed, found landed or
left with its reason; the scans' result; anything for the lead (an allow-list line your edit orphans); last line
"nothing of mine is running".
