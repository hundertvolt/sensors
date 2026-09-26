You are one of six parallel read-only agents in a whole-project audit of the `sensors` repo (MicroPython 1.29.0 firmware for Pico W sensor units, plus build chain, digital twin, website, tests). Audit EXECUTION is blocked: you change no code and no doc. Your job is the DECISION-PROVENANCE SWEEP over your slice SLICE.

WHY. The owner (hundertvolt) found a statement presented as a settled decision the owner never made: SPECIFICATION.md's "Known structural gap, accepted risk (`SGP40_I2C._reset()`)" (C.8). A session agent wrote it (`f5c9f90`, 2026-09-03), judged the risk low itself, headed it "accepted risk" without naming who accepted, and parked the real choice as "flagged for a project-owner decision if ever revisited" instead of asking. Every later reader took it as decided. The owner's rule now (OR62, OR48.a (2)): an agent's acceptance is not an owner decision. Find every other statement in your slice that presents something as decided, accepted, settled, intended or owner-directed, and establish who actually decided it.

REPO: /home/user/sensors, branch `claude/whole-project-audit-plan`, HEAD. Read-only except your single output file OUT (append as you go). No tests, builds, `uv`, `npm`, hardware, port binding. Git read-only only (`log`, `show`, `blame`, `grep`, `log -S`, `log -G`); never checkout/stash/fetch/commit. Never read `arduino/`, `ext/`, `python/`, `modules/`, `html_raw/`. Do not modify anything under `audit/` except OUT.

READ FIRST: `PROJECT_AUDIT_PLAN.md` section 3.2 (owner rows OR1-OR63: the owner's verbatim words from this audit, the strongest evidence that exists), `audit/hreq/MERGE.md` section "Task 2 — owner-attribution coverage" (earlier attribution tally, reuse it), `CLAUDE.md` "Working agreements".

EVIDENCE FACTS (already established, do not re-check):
- All content commits are authored `Claude` (session agents, 1630 commits); `hundertvolt` commits are PR merges only and carry no content decisions. The owner leaves no PR comments or reviews (checked). So the owner's words reach the repo ONLY as (a) the OR rows in PROJECT_AUDIT_PLAN.md 3.2 (verbatim, strongest), (b) words an agent quoted as the owner's in a commit message or doc, (c) an agent-written tag such as "(project owner, 2026-09-11)", "owner decision", "owner's direction", "confirmed directly by the project owner". (b) and (c) are claims, not proof. Rank: OR row > quote in the INTRODUCING commit's message or text > tag present in the introducing commit > tag added by a later commit > no owner trace.
- Merging a PR is not the owner deciding its content.

WHAT TO FIND. Read your slice in full (not only a grep), then also grep it for: accept, settled, by design, deliberate, intentional, intended, decided, decision, owner, agreed, approved, confirmed, standing, "don't re-propose", "do not propose", "not a bug", "not to fix", "don't fix", "won't", "out of scope", "never", "revisit", "flagged for", "tolerat", "acceptable", "known gap", "known limitation", "leave", "keep". A HIT is a statement that either (i) attributes a decision to the owner, or (ii) declares a risk, behaviour, gap, scope or limitation accepted/settled/intentional/final, or (iii) forecloses a future change ("don't re-propose", "never", "not something to fix", "stays"), or (iv) parks a choice for the owner without asking. Skip plain design notes that only explain WHY code is written a way and neither close a question nor claim an owner ("deliberately a list, so order is kept") — count them, do not list them.

FOR EACH HIT establish:
1. The claimed actor: owner / none (actorless) / agent / external fact.
2. The introducing commit of the decision wording AND, separately, of any owner tag: `git log -S'<distinctive phrase>' --format='%h %ad %an %s' -- <file>` (oldest = introducer; for text moved between files search without the path); `git show -s <hash>` for its message. Does the message quote the owner's words? Does an OR row cover it?
3. Classification (one):
   - `owner-quoted` — owner words exist (OR row, or a quote in the introducing commit) and the statement matches them.
   - `owner-widened` — owner words exist but the statement claims more (say exactly what is extra).
   - `owner-claimed` — attributed to the owner, but no owner words anywhere, only a tag or an assertion.
   - `tag-added-later` — the owner tag or decision word arrived in a later commit than the content (rewording, compaction, proofreading, merge); name both commits.
   - `agent-as-settled` — actorless or agent-origin statement worded as accepted/settled/intended/final.
   - `parked-question` — "flagged for owner decision", "owner's call", "if ever revisited", never asked.
   - `fact-backed` — the "decision" is really an external fact (datasheet, MicroPython source, measurement) correctly cited; no owner claim needed.
4. Weight: `owner-matter` (product behaviour, accepted risk, scope, hardware safety, what is tested or not, anything the owner must own) or `engineering-local` (an implementation choice an agent may make, fine if labelled as such).
5. Mechanism: M1 actorless decision vocabulary; M2 parked question never asked; M3 attribution added or moved after the fact (rewording, compaction, merge); M4 owner quote widened into a broader rule; M5 merge treated as approval; M6 agent recommendation recorded as owner choice; M7 other (describe). Say which, with the evidence.

OUTPUT FORMAT (OUT, markdown, compact — one block per hit, nothing else per hit):
```
# Decision provenance <D> — <slice> (HEAD <short hash>)
## Hits
### <D>.<nn> <short title, max 8 words>
- **At**: <file:line> — "<quote, max 25 words>"
- **Claims**: <owner|none|agent|fact> · **Class**: <classification> · **Weight**: <owner-matter|engineering-local> · **Mech**: <M1..M7>
- **Trail**: <introducing commit hash date: one-clause circumstance>; <owner-tag commit if different>; <OR row or quote if any>
- **Note**: <one line: what is extra, what is wrong, or what the owner must now decide>
## Mechanisms seen   <- per mechanism: count and the two clearest examples with commits
## Counts           <- hits by class x weight; design notes skipped (count only)
```
FINAL REPLY (max 200 words): hit counts by class and weight, mechanism counts, the five most significant owner-matter hits (file:line, one line each), anything you could not trace.
