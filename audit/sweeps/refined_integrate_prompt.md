You are integration agent AGENT of the REFINED HARVEST in the whole-project audit of the `sensors` repo at /home/user/sensors (branch `claude/whole-project-audit-plan`). Audit execution is BLOCKED: no code, test, doc or config outside `audit/` changes. You edit ONLY: FILES, plus your ledger OUT = /home/user/sensors/audit/refined/AGENT.md (create it). Other agents edit the other register files in parallel — never touch them.

Context. The requirement register is `audit/pass2/G1.md`-`G10.md`, `LEAD.md` (blocks `### Gx/Rnn Title` with fields Req / Sources / Rank / State / Home / Pillar / Pass 2; read a few blocks first and keep the exact format). The refined harvest swept the repo for 38 recurring patterns (`audit/refined/PATTERNS.md`); its 354 findings are in `audit/refined/FINDINGS.md` (IDs RF001-RF354, grouped by the register file their home names; ⚑ = owner-matter). Each line came from a sweep file `audit/refined/Snn.md` ([Snn] tag) which holds its context and coverage. Your findings: the sections GROUPS of FINDINGS.md.

Read first: CLAUDE.md; audit/CONSOLIDATION.md sections 1, 3 (harmonizations 1-45), 5; PROJECT_AUDIT_PLAN.md section 3.2 rows cited by your findings and your register blocks (OR1-OR86; a later owner row overtakes an earlier one); audit/pass2/INDEX.md (units U0-U37 and phase C are listed there).

For EVERY RF line in your groups, in order:
1. Re-check it at its site (open the file/commit; one look — the sweeper verified it already). If it is false, a duplicate of another RF line, or already fully stated by the register, it is REJECTED (say why).
2. Otherwise integrate it into the requirement its home names, or into a better-fitting requirement in YOUR files:
   - add the site/fact to State as work with its unit (code/doc/test/rule/hardware in Uxx), and `RFnnn` to Sources;
   - if it shows the requirement's own Req, Rank, State or a claim in it is WRONG (a factual error, a drifted or dropped owner qualifier, a "holds" that does not hold, a rule contradicting a later OR row), correct the field in place per harmonizations 24, 27, 34, 35 and note it in the Pass 2 field as "Refined: RFnnn — <what changed>";
   - append "Refined: RFnnn[, …]" to the Pass 2 field of every requirement you touch.
3. If no requirement in your files fits, write a NEW requirement block at the end of the right file among yours (next free number), all fields filled, Pass 2: "new (refined harvest, RFnnn)". FOR THE NEW GROUP: write new blocks into /home/user/sensors/audit/pass2/REF.md as `### REF/Rnn Title` (create the file with a one-line header `# Refined harvest — new requirements`); a finding that belongs to an existing requirement in another file is NOT edited there — record it in your ledger as "→ Gx/Rnn: <the exact State/Sources text to add>" and the lead applies it.
4. Lost owner decisions (a merge or rewrite dropped owner words): restore them into the requirement text ONLY if you verify the owner words (quote + commit) AND no later OR row or recorded owner answer overtakes them (the most recent owner decision wins, OR68.a (2)); rank "owner" with the quote, date and commit. If a later owner row conflicts or you cannot verify, make it a question instead.
5. Owner-matter (⚑, or anything where OR2.c / OR12.a / OR13.a / OR48.a (2) route the decision to the owner): never decide. Write a question candidate in the owner's format: a numbered top-level decision of at most 10 words, then options (a, b, …) each with its consequence, and your recommendation. Put the finding in the register as work with "State: open — owner question (RFnnn)".

Rank discipline (the audit's own recurring drift, verifiers found 68 such defects last pass): quote owner words exactly with their qualifiers; "owner" only with owner words or an OR row; agent choices are "(agent, 2026-09-28)"; every decision statement names actor and date; never widen or narrow what a source says.

LEDGER (OUT):
```
# Refined integration AGENT — GROUPS
| RF | action | where | note |
|---|---|---|---|
| RF001 | placed / corrected / new / restored / question / rejected / → other | Gx/Rnn or REF/Rnn or Qn | one line |
## Questions
1. <≤10 words> — (a) … → consequence; (b) … → consequence. Recommendation: … (RFnnn)
## Summary
counts per action; the requirements you created or corrected
```
Every RF id of your groups must appear exactly once in the table (a script checks this). No model identifiers anywhere. Keep entries lean. FINAL REPLY (max 120 words): counts per action, new requirement IDs, corrected requirement IDs, number of questions and the top 3 questions.
