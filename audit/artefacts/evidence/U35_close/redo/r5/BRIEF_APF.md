# R5 unit apf: the owner's decision-review answers that change the firmware (lead, 2026-11-06)

## Read first
`S/u35r/r1/common_r1.md` (binding; labels `apf_`). S =
`/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad`. Then `S/u35r/r5/U14_ANSWERS.md`
(the owner's answers, verbatim times; your items are named below by their entry) and CLAUDE.md in full.

## Owner ruling behind this unit (2026-11-06 13:27:49 UTC, verbatim)
"Q11: All accepted. Last message: A, all now" (A: the firmware unit and the records-and-twin unit in parallel).

## Your work (worktree `S/wt-apf`, branch `audit/apf`, at int `964ee399`; create it; commit locally, never push)
1. **The UART hazard code into the link module** (U14_ANSWERS Q3 entry, the owner's 09:08:46 words). Remove
   `add_status_command()`, `_status_commands` and its lookup from `src/asy_webserver_service.py`; the link module
   brings its own route, registered by dev-only generated lines on the app `buildgen/codegen.py` creates (for example
   `PUT /uart`); its form is a dev-only website section posting there. If the shared page code cannot post a new
   section unchanged, stop that part and say so in the hand-back (it goes back to the owner); do the rest.
   `tests_scripts/test_uart_link_bench_only.py` fails on any trace (hook, key, route, form, generated line) in a
   non-dev build. The bench hazard test and the doc lines follow the new path. UART wire format untouched.
2. **The C-stack overflow record** ("Also for the apply unit", overflow record A): `_log_dead_task()` writes
   `_RR_STACK_EXHAUSTED` (20) before its awaited entry when the ended task's exception is the C-stack overflow; a unit
   test with the logger blocked; one sentence in SPECIFICATION.md Part F.1; the stack device script gains an escape
   mode (an overflow no handler records) expecting 20 on silicon.
3. **WLAN console lines** (same section, 12:09:55): one line per change of connection state, never per pass; entering
   a connection prints "WLAN connection established" with its diagnostics, leaving it "No WLAN connection" (and any
   other state line the loop repeats prints only on its change); `_conn_phase` tracks the state. A unit test asserts one
   line per change across several passes in each state. Console only; no FRAM entry changes.
4. **`TimeStale` removed** (Q9 entries, 13:01:01 ruling B): every place the Q9 entry lists (generator, definitions,
   tests, twin CI suite checks moved to `NTPSynced`, scenario test, mock data, twin README, SPECIFICATION.md's
   paragraphs). The "NTP Synced" row takes the drifted-times description; the October wish is served by `NTPSynced`
   (owner, 2026-11-06).
5. **"A harness hard reset reads 2"** in four places (`tests_hardware/harness.py` near :924, SPECIFICATION.md near :1124
   and :7015, `buildgen/error_catalog.json` near :173): it reads 21 (`RR_INTERRUPTED`) since the reset-reason rename.
Each changed line that carries an "(agent, date)" tag inside your spans: you own its wording (the parallel unit skips
these spans).

## Never
CLAUDE.md and common_r1 in full. No hardware. Never edit `ext/`; never read `arduino/`; never open `/root/.claude/`.
Never weaken a check. Another unit (apr) edits SPECIFICATION.md tags, `digital_twin/` and tests at the same time: change
only your items' lines, restructure nothing.

## Checks
Test first per common_r1. Rebuild, lint_direct, the three mypy passes; the changed test files while working. Then the
gate once, under `S/u35/lead/heavy.lock` (wait while it exists; write "apf gate <time>" into it; `rm` it as its own
command when done; the other unit uses it too): common_r1's gate (both `scripts/test.sh` stages, the four twin CI runs)
plus `npm run lint`, `npm run typecheck`, `npm run test:unit`, since the website changes; `tests_scripts` whole once,
also under the lock. Sizes per common_r1 (module_sizes and `imageFreeBytes`).

## Limits
`src/`, `buildgen/`, `js/`/`html/` only as item 1 needs, `tests/`, `tests_scripts/`, `tests_hardware/` (items 1, 2, 5),
`digital_twin/` (item 4 only), `mockdata/`, SPECIFICATION.md (your items' lines). One or two commits. Budget about
1.5 % of the week. Hand back by 16:30 UTC.

## Hand-back
`S/u35r/r5/HANDBACK_APF.md`, at most 30 lines (common_r1's hand-back items), and the bench's reruns for the new image
as `PYTEST_K` per tier. Last line: "nothing of mine is running".
