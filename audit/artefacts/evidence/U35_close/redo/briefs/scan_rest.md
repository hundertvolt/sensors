# SCAN-REST: tests, tooling, docs, repo and the audit's course against the pre-audit state (lead, 2026-10-28)
Owner, verbatim (2026-10-28):
- "The verification machinery never was the goal of "perfection". The firmware shall be the main target, the
  buildgen as well. The unit tests shall have good quality, but don't need deep dives. The audit verification
  machinery is just a temporary tool."
- On the audit's expectations: "A deep analysis of the big picture - Consolidation over the whole project - Agreed on
  new features being added - Docs to be consolidated - Repo cleanup - firmware quality already was high. So I expected
  some details changed due to findings, but in the dimension of a few lines per module, very minimal and clever."
- "We will have to sort out the results up to now: real improvements, excessive growth, real findings, hypothetical
  findings, runaway situations, real investigations."

Read-only: no edit in the repo, no test run, no build. Range: the audit's start `25caf528` (2026-09-25) to the
integration head `497b3eda`, read in `S/wt-u35int`; never write to it. Never read `arduino/` (use `':!arduino'`).
Never open anything under `/root/.claude/` or any agent transcript. Your part (E, F or G) is in your launch message.
Coarser than the firmware scan: per area or file group, not per line, with examples that show each class.

## E: tests and tooling
- **Areas:** `tests/`, `digital_twin/`, `tests_scripts/`, `tests_hardware/`, `tests_js/`, `scripts/`, `toolchain/`,
  `.github/`, and the website, `js/` and `html/`. The website is product code, frozen into the firmware image, so
  flag any behaviour change it carries.
- **Per area:** its growth (`git diff --shortstat`), and what the growth is, split into:
  - tests that pin firmware or buildgen behaviour;
  - tests or tools of the audit's own machinery (review rows, scans, walks, sweeps, records);
  - harness infrastructure (fakes, driven clocks, runners);
  - CI.
- **The classes:** what is good-quality coverage worth keeping; what is excessive (deep dives, campaigns,
  duplicates); and the runaway areas, where tools test tools or harness work fed more harness work. Name examples
  with file and commit.

## F: docs and repo
- **Docs:** SPECIFICATION.md (by Part), README.md, CLAUDE.md, BACKLOG.md, every other root `*.md`,
  `digital_twin/README.md` and `tests_hardware/README.md`. For each, what grew, split into:
  - knowledge worth keeping;
  - history or narrative (the doc rules in CLAUDE.md say it must go);
  - duplication;
  - audit-process text.
  Give line counts per class, with examples.
- **Repo:** `audit/` by kind and size (records, scripts, evidence logs) and what of it needs to stay in the repo.
  Also any other clutter: generated, logged or stale material, for example `digital_twin_ci_logs/`.

## G: the audit's course
- **Units:** from the git history (`git log --format='%h %ad %s' --date=short 25caf528..497b3eda -- . ':!arduino'`),
  the audit plan `PROJECT_AUDIT_PLAN.md`, and the unit records in `audit/`. Per unit: what it delivered and its size
  (commits, and lines touched in firmware, tests, docs and audit).
- **The U35 redo:** the lane hand-backs in `S/u35r/handbacks_redo/` and the lead notes in `S/u35/lane_plan.md`.
  Read headlines and first sections, not whole files. Name:
  - the runaway chains: series of lanes on one topic, or investigations that fed the next;
  - the real investigations, each with what it delivered (a verified firmware fix, a test, knowledge, or nothing).

## Hand-back
- Write `S/u35r/scan/<part>.md`, first line "<part> scan, written by the lane (<date -u>)": the per-area findings
  and totals, then the list of runaway areas or chains.
- Final message: the path and three lines of headline totals. Last line: "nothing of mine is running".

## Addendum for E (lead, 2026-10-28): the project scheme and pillars
Owner, verbatim: "While,you scan, check for violations of our project scheme and pillars, much of the excessive
additions do violate them". For each area, name what violates a pillar or project rule, with the line that states
the rule. The pillars P1-P12 are the table in `audit/CONSOLIDATION.md` (around lines 19-36); the rules are CLAUDE.md
"Hard rules" and "Working agreements". Among them: P4 "nothing in the product for tests", P9 least wear, the host-I/O
wear rule, "hanging tests are never allowed", and the owner's "The unit tests shall have good quality, but don't need
deep dives". Read by anchor, not whole.
