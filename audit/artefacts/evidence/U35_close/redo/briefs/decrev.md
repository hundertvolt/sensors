# DECREV: the agents' decisions on the owner's behalf, re-checked against the refined picture (lead, 2026-10-28)

S = `/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad`. Read-only: you change nothing
in the repo, the worktrees or any earlier scan file. Your part (DR1-DR8), its input and its scope are in your launch
message. Inputs are in `S/u35r/decrev/inputs/`; the repo is `/home/user/sensors`, pushed head `11b66cd8` (product tree
= the integration head `497b3eda`; use `git show 11b66cd8:<path>`).

## The owner, verbatim (2026-10-28)
- The request: "with the updated big picture about the project and its shape, revisit the decisions you took on my
  behalf, and check if you would answer differently with the new knowledge. Only check, and see them in a global
  context, also not contradicting each other, and document your findings."
- The background for the cleanup: "a verified finding or a taken decision stand for their own and are worth keeping
  at least documented. When cleaning the firmware and the buildgen, some of them may become obsolete, e.g. when
  removing cascades and issues these cascades themselves introduced and are overkill or runaway. They have no more
  direct meaning to the project anymore, but still are worth to know about in general. Others, which stay in scope,
  stay valid and effective as they are, but ideally are resolvable with way more minimal code. Rare but real
  conditions which drop out through the cleanup no longer matter. Rare but real conditions staying in scope still
  shall be addressed - no regressions, but more efficiency."
- Earlier the same day: "Firmware state at the beginning was already quite solid. ... My expectation is that no real,
  verified gap is re-introduced. But the way it flows into the firmware and buildgen is *really* minimal change.";
  "building upon hypothetical findings is a clear no-go"; "Hypothetical findings which are suspicious to be real need
  to be verified"; "hardcoded delay checks like this are a very bad, very awkward pattern"; "The unit tests shall have
  good quality, but don't need deep dives. The audit verification machinery is just a temporary tool."
- Settled, never questioned again: every "ok" on the review page stands ("The OK in the review stay valid."); the
  Wi-Fi behaviour as built is the owner's ("We thoroughly discussed the WiFi issues and I decided everything
  already."); the FRAM per-owner CRC seed stays ("The FRAM idea of yours is good, keep it!"). For these you may only
  note a smaller form of the same behaviour ("form only"). A topic the owner decided is never put to the owner again.

## The new knowledge (read by section, not whole)
- `S/u35r/picture/PICTURE.md`: sections 2 (the lines L1-L8 the owner's decisions draw), 4 (where the audit's results
  misfit them, M1-M13), 7 (the owner's answers) and 8 (how the cleanup treats findings and decisions).
- `S/u35r/scan2/SCAN2.md` (the second pass, whole, 22 KB): the eight patterns, the finds, the removal closure, the
  keep list (section 5), the corrections (6) and the resolved disagreements (7). Its rows are in `S/u35r/scan2/G1.md`
  (core, storage, drivers, LED), `G2.md` (network, UART), `G3.md` (buildgen, generated code, website), `G4.md`
  (families, closure), `G4b.md` (crosswalk); grep `^### S2-` or the anchor.
- The first scan: `S/u35r/scan_pub/REPORT.md` sections 2-6 (classes R/K/H/X/C, the 17 real gaps, the code in doubt,
  smaller forms) and the row files `A.md` (core, storage), `B.md` (network, UART), `C.md` (drivers, LED), `D.md`
  (buildgen, generated), `E.md` (tests, tooling), `F.md` (docs, repo); grep `^### `.
- `S/u35r/scan_pub/DRIFT.md`: the mechanisms of the drift and its ten rules.
- The owner's record: `PROJECT_AUDIT_PLAN.md` at `11b66cd8` (the OR rows; only the owner's words there are owner
  decisions), `S/u35r/recovered/owner_rulings_after_LN118.md`, the review answers (`inputs/answers.json`; in
  `inputs/DR1_review_decisions.tsv` the columns owner_status and owner_note), `S/CHECKLIST.md`.

## What counts as a decision taken on the owner's behalf
Every row of your input: a choice an agent made (behaviour, rule, scope, value, form, placement, what to test, what
to leave out) without the owner's words. A tagged line that only states a fact or a measurement is not a decision:
count it as "fact" and give no verdict. If the owner's words cover a row (an "ok" or "Fine, and ..." tick, an OR row,
a ruling), it is the owner's now: verdict OWN, with the source.

## The verdict, one per decision
- **SAME**: with today's knowledge you would take the same decision.
- **FORM**: the same decision, but the form built for it is larger than it needs; name the smaller form and the
  scan row that shows it.
- **DIFF**: you would decide differently now. Give the new answer and the new knowledge it rests on: the owner's
  words (verbatim, with the source), or a verified fact (a scan row with its proof: source line, git, the pinned
  MicroPython source `/root/pico-toolchain/micropython` v1.29.0, a datasheet). Never a hypothesis.
- **OBS**: obsolete: it answers a question that exists only because of a mechanism the cleanup removes (a cascade, a
  hypothetical, a runaway); name that root and its scan row. It stays documented as general knowledge.
- **OWN**: covered by the owner's words; cite them. If the owner's note changed or conditioned the agent's decision
  ("change", "Fine, and ..."), say whether what was built follows the owner's words, and flag any gap.
- **SUP**: superseded by a later decision (agent or owner); cite it, and say whether the later one stands.
- **CHECK**: suspicious either way and not settled by a static check: put it under "needs verification" with the
  one minimal check that would settle it (what, against which commit, and what each outcome means). Do not decide it.

Also give each decision:
- **line**: the picture line it touches (L1-L8), and "misfit" if it contradicts that line;
- **topic**, from this list, so the crosswalk can group across parts: core-logging, error-catalog, storage-fram,
  config, supervisor-reset-watchdog, memory-gc, timing-waits, bus-i2c-spi, driver-scd30, driver-sgp40, driver-bmp3xx,
  driver-isl29125, driver-other, led-notification, wifi, ntp-dns, webserver-rest, website, uart, buildgen-toml,
  generated-code, tests-unit, twin, tests-hardware, ci-tooling, docs-records, release, security, licensing, process.

## Global context: contradictions
- Within your set and against the owner's record, list every pair that contradicts: two decisions that cannot both
  hold, a decision against an owner decision or ruling, a decision against a picture line. Name both sides with IDs
  and sources, and say which side stands (the owner's words always do; between agents, the one the new knowledge
  supports). If two owner statements seem to pull apart, record the facts for the lead; never frame a question.
- Note any decision that another part's set obviously also decides (for example a review-page decision executed in a
  unit): name the likely counterpart by its words, so the crosswalk can pair them.

## Rules
- No runs: no Unix port, no twin, no tests, no builds. Static checks only (git, grep, the pinned MicroPython source,
  `datasheets/`, `legacy/` read-only). Never read `arduino/` (`':!arduino'` on git grep/log). `ext/` is vendored and
  out of scope. Never open anything under `/root/.claude/`, nor any agent transcript or task output file.
- No source copied into your file beyond identifiers and one-line anchors. Never write a credential's value; the
  hotspot fallback password is named only as "the hotspot default".
- Never build on a hypothesis: "only X uses Y" or "Y exists because of X" is backed by grep or by the introducing
  commit (`git log -S`), cited. A DIFF or OBS without such a basis is a CHECK.
- Records say "the owner" (no pronoun). Owner quotes verbatim, with their source. Only the owner's words count as
  owner decisions; agent text in SPECIFICATION.md, BACKLOG.md or the audit records does not, whatever its wording.
- Efficiency: read your input and the cited sections, not whole files; don't re-derive what a scan row establishes,
  cite it. Target size of your file: about 30-60 KB.

## Hand-back
Write `S/u35r/decrev/<part>.md`, first line "<part> decision review, written by the part (<date -u>)". It holds:
1. Counts: decisions, facts, and per verdict; per topic.
2. DIFF rows in full: id; the decision as taken (one line); the new answer; the basis; topic; line; what changes in
   the code or records if the new answer is taken (an estimate, no implementation).
3. OBS rows: id; the root it depends on (scan row); topic.
4. FORM rows: id; the smaller form; the scan row; topic.
5. OWN rows: id; the owner's words and source; whether what was built follows them, any gap.
6. SUP rows; CHECK rows (with the one minimal check each).
7. Contradictions (both sides, sources, which stands) and the likely counterparts in other sets.
8. SAME rows: one line each (id, topic, a few words).
Row ids: `REG:<line>` for register rows (the line in `inputs/REGISTER_11b66cd8.md`), the review id for review items,
`SPEC:<line>` (in `inputs/SPEC_11b66cd8.md`) or `<path>:<line>` at `11b66cd8` for tagged text.
Final message: the path, one line of counts per verdict, the three most significant DIFFs in one line each, the
number of contradictions. Last line: "nothing of mine is running".
