# A-C fold of the silent-failure scan rows into the work order (phase 1: source side)

Work ONLY in the worktree <scratchpad>/wt-fold
(branch audit/sf-fold). Edit ONLY the M files assigned to you. Do not commit. Do not run tests, builds, npm or uv (a
quiet measurement runs on this host). Never read `arduino/`. No hardware.

Input: <scratchpad>/scan/sf_rows.md (the register's
parked rows; each names its units, the finding, and the minimal fix; full texts in
`audit/sweeps/scan_runs/20261006_*.md`). Rules you apply, read them first: `audit/sweeps/silent_failure_scan.md`
(minimal-first), CLAUDE.md (decision tags "(owner, YYYY-MM-DD)"/"(agent, YYYY-MM-DD)"; permanent text outside `audit/`
never cites audit IDs; comment blocks at most 3 prose lines; `ext/` never edited; the UART wire format untouched).

For each row whose fix lands in a file covered by your M files (by the row's site, not only its unit label):
1. Find the existing M entry for that site (`audit/consolidation/site_index.json` maps files to M-IDs; read the
   entry's Change in full). Fold the fix into that entry: append to its `- **Change**:` slot a numbered part
   `(N) (A-C fold, silent-failure scan SF-xx, 2026-10-06) ...` stating the end state precisely (function, condition,
   return value, log call with its catalog code if one is needed, the 3-line comment if one is warranted), at the
   smallest form the row proposes, consistent with the rest of the entry's text. Continuation lines indent two
   spaces like the existing ones. If the row corrects the entry's own text (SF-M1-02), edit that text in place and say
   so in the fold part.
2. Respect owner decisions: where the row says "owner-review list" or "flag-first", the fold states the conservative
   option the row names and nothing more; where a row says "owner question", fold only the visibility part.
3. Keep the entry's unit: if the row's unit label differs from the entry's `- **Unit**:`, keep the entry's and report
   it. Prefer an entry of the same unit when several cover the site.
4. Only if no M entry covers the site at all: report it; do not invent an entry.
5. Do not touch the `From`, `Depends` or `Blast` slots' structure; you may append to `Blast carried by` a short
   "(SF-xx: test in M_TEST_UNIT/M_TWIN per phase 2)" note.

Output: write <scratchpad>/scan/fold_<yourname>.md
with one line per row you handled: `SF-xx | M-ID (part N) | file | unit kept | test/SPEC/bench carriers needed (one
phrase each)`, and a list of rows in your scope you could not fold, with the reason. Final message: counts and anything
unresolved.
