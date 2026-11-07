# Fix unit: the new-module procedure's gaps the two proof runs found (lead, 2026-11-05; docs only)

## Read first
`S/u35r/r1/common_r1.md` (binding; labels `pk_`). S =
`/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad`. Then the two comparisons, which
are your work list: `S/p10_lead/isl29125/COMPARE.md` (proof run 1: sentences K1-K6, section 2's L25 and L26, section
3) and `S/p10_lead/bmp3xx/COMPARE.md` (proof run 2: sentences N1-N3). The procedure logs they cite are
`S/p10/isl29125/PROCEDURE_LOG.md` and `S/p10/bmp3xx/proclog.md`; read an entry where a sentence's place is unclear.

## Why it matters
Two agents built a module from the datasheet by SPECIFICATION.md Part K and `.claude/skills/integrate-module/SKILL.md`
alone. Every place they had to guess or look beyond the procedure is listed in those files with the sentence that
would have prevented it. Putting those sentences in is how the procedure gets proven, not merely written.

## Your work (worktree `S/wt-pk`, branch `audit/pk`, at `4e05f80e`; commit locally, never push)
1. **Part K and the skill:** K1, K3, K4, K5, K6 (run 1), N1 in place of K2 (it widens K2), N2 and N3 (run 2), each at
   the item its line names. Fit each sentence to the text around it rather than pasting it, and check every name it
   cites exists in this tree (a file, a table, `_KNOWN_TICKS_USERS`, a Part or item number). K3 replaces K.9's
   dangling "C.8 ... note" with the C.9.1 reference; N3 goes in the skill's step 1.
2. **Part F.1:** the `math.inf` fact (run 1's section 3): a frozen `math.inf` or `math.nan` folds to a float constant
   that the freezer writes as a bare `inf`/`nan`, failing the firmware build; `float("inf")` is not folded. Put it
   next to F.1's sentence on host-folded float constants, with the source citations section 3 gives (check them in
   `S/tc-int/micropython/`, read only).
3. **CLAUDE.md, "How a block is counted":** one clause saying a line over 120 characters counts as ceil(len/120) lines,
   as `tests_scripts/test_comment_block_cap.py` already counts it (check the lines run 1 cites, and the decision tag
   its comment gives).
4. **C.9, one Timer per starter (L26):** the comparison marks it plausible, not reproduced. Write the sentence only if
   this tree's code and Part F confirm the rule (cite where); otherwise write nothing and say why in your hand-back.

## Not yours
Run 1's and run 2's codebase findings (class C, other than items 3-4 above), the strip artefacts (class S), and
anything under `src/`, `tests/`, `digital_twin/`, `buildgen/` or `tests_hardware/`.

## Rules for the text
- The smallest form: one sentence per gap where one does; no new section, list or table unless the gap is a missing
  table row. Net growth of Part K plus the skill under 40 lines.
- Text outside `audit/` cites no audit IDs (no K1, N2, PL12, L26, RF numbers, unit names): state the rule itself.
- A sentence that records a choice carries the repository's decision tag form, "(agent, 2026-11-05)"; a fact gets its
  source citation instead.
- SPECIFICATION.md keeps its wrap width; comment-block and line rules as CLAUDE.md states them.

## Checks (light runs only; the heavy slot is the lead's until about 20:45 UTC)
`S/u35/lead/lint_direct.sh`; `tests_scripts/test_comment_block_cap.py`, `test_citations.py` and every other
tests_scripts file that reads SPECIFICATION.md, CLAUDE.md or the skill (grep for them). Then, once
`S/u35/lead/heavy.lock` is absent, take it as common_r1 says and run the tests_scripts tier whole (lesson: a change
to SPECIFICATION.md runs it whole), and release it.

## Limits
Write only SPECIFICATION.md, CLAUDE.md and `.claude/skills/integrate-module/SKILL.md` (plus `digital_twin/README.md`
only if a sentence's place is there). One commit. Budget about 1 % of the week; hand back by 22:30 UTC.

## Hand-back
`S/u35r/r4/HANDBACK_PK.md`, at most 30 lines, and return its path: per item where the sentence went (file:line), lines
in and out, and anything not written with the reason; the checks. Last line: "nothing of mine is running".
