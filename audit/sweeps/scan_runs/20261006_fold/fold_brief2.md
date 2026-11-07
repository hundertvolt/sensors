# A-C fold of the silent-failure scan rows, phase 2 (carriers: tests, SPEC, bench, docs)

Work ONLY in the worktree <scratchpad>/wt-fold
(branch audit/sf-fold). Edit ONLY the M files assigned to you. Do not commit. Do not run tests, builds, npm or uv (a quiet
measurement runs on this host). Never read `arduino/`. No hardware commands of any kind.

Phase 1 is done: every source-side fix is folded into the M_SRC_CORE/M_SRC_SENS/M_SRC_NET/M_WEB/M_GEN/M_SCR/M_TWIN
entries as parts "(N) (A-C fold, silent-failure scan SF-xx, 2026-10-06)". Each such entry's `Blast carried by` slot ends
with a note naming the tests/SPEC/bench text owed in phase 2. Inputs, read all of them first:
- scratchpad/scan/sf_rows.md (the 67 register rows; 61 parked; each names finding, units, minimal fix);
- scratchpad/scan/fold_F1.md, fold_F2.md, fold_F3.md, fold_lead.md (one line per row: M-ID part, file, unit, and the
  carriers needed - your work list);
- `grep -n "A-C fold, silent-failure scan" audit/consolidation/M_*.md` and each hit's `Blast carried by` note (the
  carrier notes there are authoritative where they are more specific than the fold_*.md lines);
- `audit/sweeps/silent_failure_scan.md` (classes, operating modes, minimal-first) and CLAUDE.md (decision tags
  "(owner, YYYY-MM-DD)"/"(agent, YYYY-MM-DD)"; permanent text outside `audit/` never cites audit IDs - so SPEC/README
  sentences you specify cite no SF/M/A IDs; comment blocks at most 3 prose lines; four test tiers for shared
  resources; no avoidable wear: FRAM writes are not wear, a flash/NVM write in a hardware test sits behind its marker).

For every carrier a fold names in your files:
1. Find the existing M entry for that test file / SPEC Part / hardware script / doc (`audit/consolidation/site_index.json`
   maps files to M-IDs; read the entry in full). Fold the carrier into that entry's `- **Change**:` slot as a numbered
   part `(N) (A-C fold, silent-failure scan SF-xx, 2026-10-06) ...`, continuing the entry's numbering (start at (1) if it
   has none), indented like the existing lines. State the end state precisely: test name(s) and tier (L1 unit under
   the Unix port, L2 twin, L3 flash, L4 bench), the setup, the assertion (exact log code / marker / return), and for
   SPEC the sentence itself (or its content in full, at most 3 lines per point). Tests come first in each unit
   (tests-first), so a test part says which source part it pins ("pins M.SRC_CORE.091 (1)").
2. Keep that entry's unit. If the test entry's unit is earlier than the source part it pins, say "staged with <unit>".
3. Only if no M entry covers the file at all: list it as "needs a new entry" in your report with the proposed file,
   unit and content; do not invent an entry.
4. Hardware: a Phase C row becomes a bench/flash check part only (it runs in Phase C, never now); name its marker gate
   if it writes flash or SCD30 NVM.
5. Do not change `From`, `Depends` or `Blast` slot structure.
Also check each source fold part has at least one test carrier somewhere; list any that has none and add it if the test
file is in your scope.

Output: scratchpad/scan/fold_<yourname>.md, one line per carrier part: `SF-xx | M-ID (part N) | file | unit | pins
<source M-ID part>`, then "needs a new entry", then "source parts with no test carrier". Final message: counts and
anything unresolved.
