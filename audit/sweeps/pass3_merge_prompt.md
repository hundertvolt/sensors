# Pass 3 merge — brief for the register-merge agents (2026-09-29)

You integrate pass 3's register lines into the audit register of the `sensors` repo (`/home/user/sensors`,
branch `claude/whole-project-audit-plan`). Read-only on everything except your two register files and your ledger.

## Inputs
- `audit/pass3/MERGE_INPUT.md`: the ten scans' register lines, numbered P001-P137 (a line may carry sub-lines).
- `audit/pass3/LEAD_MERGE.md`: the lead's overrides of scan lines (section 1) and the lines the owner's answers
  create, L01-L17 (section 2). An override wins over the scan line it names.
- Evidence behind a line: the scan file it came from (`audit/pass3/<scan>.md`, item IDs like D4.61 or H1.16).
- Owner rows: `PROJECT_AUDIT_PLAN.md` section 3.2 (`| ORnn |` quote rows and `| ORnn.a |` readings). The most
  recent owner decision wins; a missing owner trace never proves the owner did not decide.

## Register block form (`audit/pass2/*.md`)
`### <ID> <title>` then `- **Req**:`, `- **Sources**:`, `- **Rank**:`, `- **State**:`, `- **Home**:`,
`- **Pillar**:`, `- **Pass 2**:`. Keep this form. State lines read "work: <kind> in U<n> — <what> (<source>)".

## Your job
1. Apply every part of every P and L line that targets a block in YOUR files. A line naming several blocks:
   apply only the parts for your blocks. Lines for LEAD/* and REF/* blocks belong to the lead: skip them.
2. Accuracy before speed (owner, OR107.a). Before applying a line, read the whole target block. Apply it only
   if it fits: not already present, not contradicting the block's owner-ranked text or a newer owner row. When a
   line changes a Req or states a code fact, open the cited site at HEAD and check it (line numbers may have
   drifted; correct them). If a line conflicts or its fact does not hold, do not apply it: record why.
3. Write lean, plain English. Merge a line into the existing sentence where it belongs rather than bolting on
   duplicates. Keep "(owner, date)"/"(agent, date)" tags and source IDs (P/L numbers are not written into Req
   text; cite the scan item IDs, e.g. "(D4.61)").
4. On each block you change, append to its `- **Pass 2**:` line: " Pass 3: <P and L numbers>." (one list).
5. Write your ledger `audit/pass3/merge/<your letter>.md`: one line per (line, block) pair you own:
   `- P012 | G4/R26 | applied | <one clause>` or `already present` or `not applied | <reason>`.
   Every P/L part that targets your files must appear exactly once.
6. Do not run git (no add, commit, stash, checkout). Do not edit any other file. No hardware, no network
   commands, never read `arduino/`, never edit `ext/`.
7. Final reply: counts (applied / already present / not applied), every not-applied item with its reason,
   every conflict with an owner row, and any fact you corrected. No other narrative.
