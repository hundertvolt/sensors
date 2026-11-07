# R5 unit apr: the owner's decision-review answers in the records, the twin and the estimates table (lead, 2026-11-06)

## Read first
`S/u35r/r1/common_r1.md` (binding; labels `apr_`). S =
`/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad`. Then `S/u35r/r5/U14_ANSWERS.md`
(the owner's answers), `S/u35r/r5/U14_QUESTIONS.md` and `S/u35r/r5/U14_TAGS.tsv` (one row per "(agent, date)" line:
file:line as of int f509c906, kind, realm, and for a record its replacing citation; lines have moved since, so find
each row by its content, never by its line number alone).

## Owner ruling behind this unit (2026-11-06 13:27:49 UTC, verbatim)
"Q11: All accepted. Last message: A, all now" (A: the firmware unit and this unit in parallel).

## Your work (worktree `S/wt-apr`, branch `audit/apr`, at int `964ee399`; create it; commit locally, never push)
1. **The 466 tagged lines** (a tag added after f509c906 is not in the table: leave it). Each `record` row: its "(agent, date)" tag is replaced by the citation the row names
   (datasheet table, source line, owner ruling), or dropped where the row says wording only. Each `choice` row the
   owner accepted as built: the tag becomes "(agent, date; owner-reviewed, 2026-11-06)", the tree's existing form. A
   choice an answer changes is changed as that answer says (items 2-6). Skip every row inside the spans the parallel
   firmware unit rewrites: the webserver's status-command hook and its SPECIFICATION.md text, `_log_dead_task()`, the
   WLAN state lines in `src/asy_wifi_service.py`, everything about `TimeStale`, and the four "harness hard reset reads
   2" places; list the skipped rows in the hand-back.
2. **Q1:** SPECIFICATION.md 0.2's "proven good" sentence becomes the owner's definition (U14_ANSWERS Q1 entry).
3. **Q5 (Option C):** the five fake-chip differences corrected in `digital_twin/` as the Q5 entry lists; each README row
   becomes "fixed:" with a small self-test of the twin; the two runtime differences stay accepted.
4. **Q6:** each SPECIFICATION.md Part N row named in the Q6 entry gets one word in its Margin column: "bound" (9),
   "attention" (19) or "choice" (4), and the two non-number records are corrected. The bound rows name the bench step or
   script that measures them. Two new zero-wear measurement scripts: the supervisor scan (a device script) and a bench
   capture of real client request heads (the 32-line / 2,048 B limits), each in its tier's README. Leave the attention
   rows' numbers as they are: a read-only unit sets them, and the lead folds them in.
5. **Q8:** SPECIFICATION.md's ISL29125 "Divergence detection" paragraph (near :11543) is rewritten to the code: the
   chip's config is compared after a failed write and on a REST config read, not every cycle.
6. **Q10:** the post-write hook catch's recorded reason (`tests/test_asy_api_response.py` near :181-183, and wherever
   else it is repeated) becomes the real one: a raising reconnect or resync hook answers its fields "Failed" and logs
   the error, instead of the server's bare 500 after the values were already saved.

## Never
CLAUDE.md and common_r1 in full. No hardware. Never edit `ext/`; never read `arduino/`; never open `/root/.claude/`.
Never weaken a check. No `src/` behaviour change: in `src/` only tag wording. The firmware unit (apf) edits `src/`,
`buildgen/`, tests and SPECIFICATION.md at the same time: change only your rows' lines, restructure nothing.

## Checks
Lint_direct, the three mypy passes, the comment cap and `tests_scripts/test_decision_vocabulary.py` while working; the
twin's changed tests under the Unix port. Then once, under `S/u35/lead/heavy.lock` (wait while it exists; write "apr
gate <time>" into it; `rm` it as its own command when done; the other unit uses it too): `tests_scripts` whole, and the
twin CI suite for dev at both GC settings (`scripts/run_digital_twin_ci.sh dev --gc-threshold -1 --part suite`, the
same with 32768). `--collect-only` on both hardware tiers for the new scripts' tests.

## Limits
SPECIFICATION.md, `digital_twin/`, `tests/` (twin self-tests, item 6's comment), `tests_hardware/` (item 4's scripts
and READMEs), and tag wording in any file a row names. One or two commits. Budget about 1.5 % of the week. Hand back by
16:45 UTC.

## Hand-back
`S/u35r/r5/HANDBACK_APR.md`, at most 30 lines (common_r1's hand-back items): rows done per kind, rows skipped and
why, each item's outcome and test, the bench's `PYTEST_K` for the two new scripts. Last line: "nothing of mine is
running".
