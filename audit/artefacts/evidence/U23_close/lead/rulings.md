# U23 rulings (lead, 2026-10-13; amend lane_plan.md section 5)

Every ruling takes the plan's default (A-1..A-36), each conservative and reversible, decided on the owner's behalf and
listed for their review at the close (agent, 2026-10-13). Checked by the lead against the tree before accepting:
A-4 (`buildgen/api_reference.py:33-40` refuses an unclassified key, `api.field-key-unclassified`), A-5
(`src/asy_api_response.py:41-51`: 2 and 3 still in `_STANDARD_CODES`), A-2 (the five Part N rows at
`SPECIFICATION.md:10183`, `:10474-10476`, `:10577` cite `45f5c23`/`7b548af`/`85c82b9`).

One amendment:
- A-11 (OF-111): asked in session in the U22 owner report (question 3). On the owner's "(b)" before D's final, D
  carries it (one line in `_put_status()`, the scenario back to "Failed" at every step, seen failing first); otherwise
  the finding stays open with the question's date and U23 writes nothing for it.

Operational rulings:
1. Waves as the plan's section 2: D, M, B (wave 1, three agents); T, C, S (wave 2); X, Y (wave 3, after every code final,
   the facts relayed). Each lane's file set is written to RUNS.md and checked disjoint (`comm -12`) before launch.
2. WIP order as the plan's section 3: the lead's start commit (OF-135) first; then D1, M1, B1 merged into
   `audit/u23-api1`, the device modules regenerated and the site rebuilt in each worktree, ruff, the three mypy passes,
   `npm run lint`, `npm run typecheck` and the touched files run; lanes resume on it.
3. No toolchain rebuild: `/root/pico-toolchain` is read-only for everyone. A lane that finds it needs one stops and
   reports. No `npm install`/`npm ci`/`playwright install`: the lead copies a verified `node_modules/` (lock hash checked).
4. The frozen website, `build/` and `frozen_modules/` are the lead's (A-35): B runs its scripts only into temp outputs; D,
   M and B report every input change; the lead rebuilds before any full-graph or browser run.
5. Runs: single files only, at `nice -n 19`; at most two heavy runs per lane at once, one while a wall-time-bound file runs (owner, 2026-10-13: "4 to 6 agents
   and 4 to 6 scripts is fine."); every port-binding run (browser
   files, MicroPython files that serve, twins) in its own `unshare -n`, never two in one namespace; never `npm test` or
   `npm run test:*` (their `pretest` rebuilds the site). CONCURRENCY.md (u21 copy) is binding.
6. The live tier's time (A-32): S measures `live-backend.test.js` and each put-matrix shard; above 15 of
   `web-unit-tests`' 20 minutes, S stops and reports, and the lead decides.
7. The pre-gate check is the whole `tests_scripts/` tier, never a subset (U22's slip).
