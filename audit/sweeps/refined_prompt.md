You are sweep agent SWEEP of the REFINED HARVEST in the whole-project audit of the `sensors` repo at /home/user/sensors (HEAD `5efc919`, branch `claude/whole-project-audit-plan`). Audit execution is BLOCKED: you change nothing except your single output file OUT = /home/user/sensors/audit/refined/SWEEP.md. Append to OUT as you go so partial work survives.

Why this harvest: harvest pass 1 was deliberately unbiased — file by file, it recorded only what comments and docs self-declare. Since then the audit learned which kinds of problem keep recurring in this project. The owner: "we have gathered a huge amount of knowledge and may focus sharper on certain patterns … update our knowledge base on that refined view for not missing anything important for the project." Your job is to hunt your patterns EXHAUSTIVELY across their scope and record every UNDECLARED instance, i.e. every site the knowledge base does not already hold.

Your patterns: PATTERNS (defined in /home/user/sensors/audit/refined/PATTERNS.md — read section 0 fully and your patterns' sections fully; read the other patterns' headings so you can tag what you meet in passing).

Read first (PATTERNS.md section 2): CLAUDE.md; PROJECT_AUDIT_PLAN.md section 3.2 rows your patterns cite (in full; later rows overtake earlier ones); audit/CONSOLIDATION.md sections 1, 3, 5; audit/pass2/INDEX.md and the register blocks your patterns name as known holders (audit/pass2/G*.md, LEAD.md). Dedup per PATTERNS.md 0.2 against audit/harvest/*.md, the register, audit/dprov/, audit/DECISION_PROVENANCE.md, the plan's section 5 topics/seeds.

Constraints (PATTERNS.md 0.4, binding): read-only; git read-only (log, show, blame, diff, log -S/-G); no tests, builds, uv, npm, mpremote, port binding, network. Never read `arduino/`. `ext/` is read only for Microdot semantics. The legacy tree (`python/`, `modules/`, `build-*.sh`, `dev_legacy/` old driver copies; `html_raw/` for UI-function parity only) is reference-only: an oracle for parity, never a finding target. Ad-hoc `python3` analysis scripts (ast, re, difflib) are allowed in your own scratch dir /tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/refined/SWEEP/ (create it). Primary sources: MicroPython v1.29.0 at …/scratchpad/mp, datasheet text at …/scratchpad/dstxt/, Microdot at …/scratchpad/microdot (all under /tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/). Generated modules: read them through `buildgen/codegen.py`'s templates (do not build). No fixes, no severities, no decisions: where the owner would decide (OR2.c, OR12.a, OR13.a, OR48.a (2)), mark owner-matter: y. Do not reproduce the audit's own drift classes in your text: quote owner words exactly, keep qualifiers, never call something the owner's without an owner source, date every claim of "decided".

Verify before recording: every NEW or KNOWN+ line must have been checked at its site (open the file/commit); a signature hit that turns out not to be an instance goes to the coverage table as a rejected false positive with its reason.

OUTPUT (OUT, markdown):
```
# Refined harvest SWEEP — PATTERNS (HEAD 5efc919)
## RPnn <name>
- RPnn.<shape letter> | NEW|KNOWN+ | <file:line or commit> | "<quote ≤20 words>" | <what is wrong, one line> | near: <known IDs or -> | home: <register req ID or "new req">, unit <Uxx or ?> | owner-matter: y/n
...
### Coverage RPnn
| shape | scope searched | signature / method | raw hits | NEW | KNOWN+ | KNOWN | rejected (reason) |
## Cross-pattern notes    <- instances of other RP IDs met in passing, same line format
## Top 10                 <- your most important NEW/KNOWN+ lines, by anchor
```
Be exhaustive: list every instance, not samples (a high-volume identical class may be one aggregate line with count and full site list). FINAL REPLY (max 120 words): per pattern NEW/KNOWN+/KNOWN counts, anything you could not cover and why, your top 5 anchors.
