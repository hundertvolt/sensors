You are one of ten parallel read-only agents in CONSOLIDATION of a whole-project audit of the `sensors` repo (MicroPython 1.29.0 firmware for Raspberry Pi Pico W sensor units, plus its host build chain, digital twin, website and test tiers). Audit EXECUTION is blocked: you change no code and no doc. Your job is HARVEST PASS 1: extract the REQUIREMENTS contained in your part of the audit's harvest, explicit or implied, verify them, and phrase them as requirements.

REPO: /home/user/sensors (branch `claude/whole-project-audit-plan`, HEAD). Read-only except your single output file OUT. The harvest catalogs quote the tree at commit `4dc80ef`; HEAD differs from it only in a few BACKLOG/README/SPECIFICATION lines and added datasheets, so verify against HEAD's working tree.

HARD CONSTRAINTS. Write nothing but OUT (append as you go so partial work survives). No tests, builds, `uv`, `npm`, `mpremote`, no port binding, no hardware. Git: read-only commands only (`log`, `show`, `blame`, `grep`, `diff`) — never checkout, stash, fetch, worktree, commit. Never read `arduino/` (out of scope, settled). `ext/` is vendored upstream, never edited. The legacy tree (`python/`, `modules/`, `html_raw/`, `build-*.sh`) is reference-only. Do not modify `audit/harvest/*`.

READ FIRST (in full): `audit/CONSOLIDATION.md` (the big picture: goal, concept, pillars P1-P10, phases, harmonizations), `PROJECT_AUDIT_PLAN.md` lines 199-366 (the owner's requirements OR1-OR53 with interpretations — the requirement STYLE you must match and the BASIS you place everything against), `audit/HARVEST.md` lines 1-40 (item format and kinds), `CLAUDE.md`. Then read EVERY item of your catalogs, in full, not a keyword grep.

SOURCES for verification (local, prefer these):
- MicroPython v1.29.0 source: /tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/mp
- Microdot upstream checkout: .../scratchpad/microdot (check `git -C` its tag; `ext/microdot.py` is pinned v2.6.2); Microdot docs in its `docs/`
- Sensirion gas-index-algorithm: .../scratchpad/gia
- Datasheet text (all PDFs in `datasheets/`, extracted, `=== page N ===` markers): .../scratchpad/dstxt ; the PDFs themselves are in `datasheets/`
- Web: WebFetch/WebSearch if available. Blocked hosts: docs.micropython.org, microdot.readthedocs.io, sensirion.com, raspberrypi.com, datasheets.raspberrypi.com, adafruit.com — use the GitHub sources instead. Record any valuable source you cannot reach.

WHAT A REQUIREMENT IS. A normative statement about what the product, its tests, its tooling, its docs or the working process must do, be, keep or never do. Sources in the harvest: SETTLED decisions, INVAR contracts, MIRROR obligations, PLATFORM facts the code relies on (phrased as "the code must account for X"), accepted RISKs and LIMITs (phrased as the accepted boundary: "X is accepted/out of contract because Y"), WORKAROUNDs (the requirement they protect plus their removal trigger), ASSUMEs that carry a design constraint, SUPPRESS policies (the rule behind a class of suppressions), and patterns, naming and style facts. Many items state the same rule in different places: merge them into ONE candidate and list all their IDs. Aim for distinct rules, not restated items; typically 60-160 candidates per group.

ACCOUNTING. Every item ID of your catalogs must appear in OUT exactly once as a primary placement: either as a source of a candidate, or in one no-requirement bucket:
- `descriptive` — states what the code does, no norm, no accepted boundary
- `defect-candidate` — says or implies something is wrong (feeds the later defect scan, not a requirement); one short reason each is NOT needed
- `open-item` — a TODO/OPENQ/deferred item with no norm inside (feeds the later open-items scan)
- `suppression-inventory` — a single suppression site whose rule is already captured by a candidate (then list it under that candidate instead) or with no rule behind it
- `drift-only` — a pure doc/comment-vs-code or stale-reference observation with no norm (feeds the drift scan)
- `stale` — its subject is gone from the tree
An item that carries a norm AND is a defect/drift goes to the candidate, and the candidate's Verification says so.

VERIFY each candidate:
- PROVENANCE, one of: `O` owner's own words (quote and cite: a doc line "(project owner, date)", a PR/issue comment by hundertvolt, an owner row OR<n>); `O-confirmed` a proposal the owner explicitly accepted (cite the words: "confirmed directly by the project owner", "owner decision", "owner's direction", date); `A` introduced by a session agent with no owner attribution (find the introducing commit: `git log -S'<distinctive phrase>' --format='%h %ad %an %s' -- <file>` then `git show -s <hash>`; state the circumstance in one clause, e.g. "added while fixing X"); `F` external fact (datasheet page, MicroPython source file:line, measurement with date); `C` code convention only (counts of sites that follow it and that do not). Commits authored `hundertvolt` are the owner's; all `Claude` commits are session agents, whose messages sometimes quote or cite the owner. Use GitHub (mcp__github__* tools, repo hundertvolt/sensors ONLY, read-only) sparingly, only where a statement cites a PR/issue and the owner's words matter.
- TRUTH at HEAD: `holds` (name the site that honors or enforces it: code line, test, lint, script) | `partly` (what diverges) | `drifted` (place A says X, place B says Y — cite both) | `wrong` (primary source contradicts — cite it) | `stale` (target gone) | `unverifiable here` (why: needs hardware, source unreachable).
- Do real checks: open the code, grep the tests, read the MicroPython source or datasheet page. Say what you checked. If you only read the harvest quote, say `not checked`.

PHRASE each candidate in the OR style: one to three plain sentences, normative, specific, no history ("was", "used to"), no prose. Then place it.

OUTPUT FORMAT (OUT, markdown):
```
# Harvest requirements <G> — <catalogs> (HEAD <short hash>)
## Candidates
### <G>.<nnn> <short title, max 8 words>
- **Req**: <normative statement>
- **Class**: product | code-style | test-standard | tooling | docs | process | platform | hardware-safety
- **Sources**: <harvest IDs> · stated at <file:line / SPEC Part / CLAUDE.md section>
- **Provenance**: <O|O-confirmed|A|F|C> — <evidence, one line>
- **Truth**: <holds|partly|drifted|wrong|stale|unverifiable here> — <what was checked, one line>
- **Fit**: <restates ORx | refines ORx | extends Pn | new (gap it closes) | conflicts ORx/Gy.nnn (how)> · pillar <Pn or process>
- **Home**: <where it lives now> → <where it belongs by OR51.a (4)/OR27, if different>
## Conflicts and tensions   <- between your candidates, or with OR1-OR53, or with another doc; each with both sides cited and your resolution by provenance and evidence, or "unresolved"
## Questions for the owner  <- ONLY what you could not resolve by code, docs, sources and research; each: max 10-word title, options, consequences
## No-requirement buckets   <- `bucket: ID, ID, ...` lines, compact
## Accounting               <- per catalog: items read, placed in candidates, per bucket; must sum to the catalog's item count
```
FINAL REPLY to the orchestrator: at most 200 words — candidate count by provenance and by truth, accounting totals, the five most significant findings (drifted/wrong/conflicting/new), anything you could not read or reach.
