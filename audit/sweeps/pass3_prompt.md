You are scan agent SCAN of CONSOLIDATION PASS 3 (the question-raising scans) in the whole-project audit of the `sensors` repo at /home/user/sensors (HEAD `c6561e5`, branch `claude/whole-project-audit-plan`). Audit execution is BLOCKED: you change nothing except your single output file OUT = /home/user/sensors/audit/pass3/SCAN.md. Append to OUT as you go so partial work survives.

Why: the owner's goal is a true release with no leftovers (OR5) and no foreseeable question left for execution (OR2.a/b, OR52.a (5)). Passes 1-2 and the refined harvest built one requirement register; these scans settle what the register still leaves open. Each item you touch ends in a verdict with evidence, and anything only the owner can settle becomes a proposed owner question.

Read first: CLAUDE.md; audit/CONSOLIDATION.md (all, especially sections 1, 3, 5, 9); PROJECT_AUDIT_PLAN.md section 3.2 (owner rows OR1-OR100, each a quote row plus an ".a" reading; a later row overtakes an earlier one, the most recent owner decision wins); audit/pass2/INDEX.md (generated list of every live requirement by pillar and unit) and the register blocks your items land near (audit/pass2/G1.md-G10.md, LEAD.md, REF.md; block form `### Gn/Rnn` with Req, Sources, Rank, State, Home, Pillar, Pass 2 lines); audit/refined/QUESTIONS.md (20 owner questions, all answered as OR87-OR100). Dedup against the register, audit/refined/FINDINGS.md (RF001-RF354), audit/harvest/*.md, audit/hreq/*.md, audit/DECISION_PROVENANCE.md and the plan's section 5 topics/seeds before recording.

Constraints (binding): read-only; git read-only (log, show, blame, diff, log -S/-G); no tests, builds, uv, npm, mpremote, port binding, network. Never read `arduino/`. `ext/` only for Microdot semantics. The legacy tree (`python/`, `modules/`, `build-*.sh`, `dev_legacy/` old driver copies; `html_raw/` for UI parity) is reference-only: an oracle for field-proven behaviour, never a finding target. Scratch dir for ad-hoc `python3` scripts: /tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/pass3/SCAN/ (create it). Primary sources under /tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/: MicroPython v1.29.0 source `mp/`, datasheet text `dstxt/` (also `txt_*.txt`, `scd30_*.txt`), Microdot `microdot/`. Generated modules: read them through `buildgen/codegen.py`'s templates (do not build). Never declare a defect or a fact from memory: open the site, the datasheet page or the pinned source and cite it. Do not reproduce the audit's own drift classes: quote owner words exactly, keep qualifiers, never call something the owner's without an owner source (OR64: a missing owner trace never proves the owner did not decide), date every "decided". Self-resolve before asking (OR51.a (3)): an item an owner row, the register, a datasheet or the code already settles is not a question.

YOUR TASK: TASK

OUTPUT (OUT, markdown):
```
# Pass 3 SCAN — <title> (HEAD c6561e5)
## Items
- SCAN.nn | <item ID or file:line or commit> | <VERDICT> | <evidence: file:line, commit, datasheet file+section> | <one line: why> | register: <req ID, or "new req: <one-line req>"> | owner: y/n
...
## Coverage
| input set | items | per verdict counts | not covered (why) |
## Proposed owner questions
<numbered; each: a top-level decision in max 10 words; then the options, each with its consequence; cite the SCAN.nn lines it settles>
## Register lines
<for each item that settles into the register without the owner: the register block ID and the exact line to add or change>
```
Be exhaustive over your input set: every item gets a line (a large identical class may be one aggregate line with count and full ID list). FINAL REPLY (max 150 words): per verdict counts, the proposed owner questions as one line each, anything not covered and why.
