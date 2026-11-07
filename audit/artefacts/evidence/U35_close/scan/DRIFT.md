# How the audit drifted

Written by the lead, 2026-10-28 08:27 UTC. It is built on the full scan (`scan/REPORT.md` and its parts) and on
targeted reads:
- the audit plan's goals, method and owner rows;
- the register's unit table and owner-review list;
- the open-findings list and the work order;
- each unit's evidence index and the U0 baseline;
- the redo's lead notes.

No log dumps were read. The owner asked (2026-10-28): "learn and understand how the drift evolved. The first about 10
units of the audit felt well scoped. The drift came in gradually, but exponentially growing. ... get an understanding
of what happened, which effects it caused, and how it could have been prevented."

## The short answer

- **The drift has a date: 2026-10-06, the first day of execution.**
  - The owner asked for a silent-failure scan after every implementation, and for special operating situations.
  - The agent answered with a 381-entry inventory of hypothetical situations, run in every later unit.
  - Each scan finding was folded into the work order as about five parts: code, tests on four tiers, spec text,
    bench checks and docs.
  - The owner's same-day restraint ("the fixes required for such reliability (if required at all, if not already
    safe inherently) are minimal, low complexity") was turned into "the smallest change that closes it", never into
    "does it really happen?".
- **The first units stayed lean because they were the owner's own rows.**
  - U1-U8 delivered one owner-defined consolidation each, together +46 `src/` lines. They closed on 10-06, before the
    new scan shaped any unit.
  - From U11 on the content was defined by findings, and the findings came from reading.
- **The plan made it possible.**
  - The plan turned complete checking into complete changing. "Every register work line becomes concrete changes."
  - 548 requirements (125 written by the agent) became binding rules at the go-ahead.
  - The expanding requirements became machine-checked gates; the restraining ones stayed prose and were applied to
    their one item only.
- **Nothing pushed back during execution.**
  - By design there were no owner stop-points. 708 decisions were taken on the owner's behalf, for a review that
    was planned only at the very end.
  - "Conservative" was read as "most protective" rather than "smallest change".
  - No budget existed: no change budget, no flash budget, no time or token budget.
- **The growth was a loop, so it was exponential.**
  - More code meant more to scan, and every finding added code plus tests on four tiers.
  - The tests and tools were in scope too, so they were scanned and grew the same way.
  - A bigger suite made the gates slower and flakier. The rule "no flake without a root cause" then pulled the
    harness itself into investigations.

## 1. The course in numbers

Per unit, from the git history, the register and the evidence folders:
- **src:** the change in non-comment `src/` lines.
- **lanes:** parallel lanes inside the unit.
- **evid.:** the files in the unit's evidence folder.
- **on-behalf:** decisions taken on the owner's behalf.
- **findings:** open-findings rows the unit's close scan produced.

| units | dates | src | lanes | evid. | on-behalf | findings | what defined the content |
|---|---|---|---|---|---|---|---|
| Phase A (planning) | 09-25 .. 10-05 | 0 | — | — | — | — | the plan |
| U0-U8C2 (baseline, foundations) | 10-06 .. 10-07 | +46 in all | 0 | 0-16 | 1-20 | 0-12 | the owner's own rows |
| U9 LED pilot, U10 contracts | 10-07 | +19, +7 | 0-1 | 3, 15 | 16, 32 | 2, 5 | owner rows plus shared primitives |
| U11-U12 core, algorithms | 10-07 | +172, +54 | 0 | 88, 11 | 35, 13 | 9, 3 | findings |
| U13-U21 bus, drivers, FRAM, UART, network, REST, buildgen, toolchain | 10-07 .. 10-08 | +459 ... +150 (+1,723) | 0 → 12 | 53 → 939 | 13-55 | 5-16 | findings |
| U22-U28 LED re-check, web, tests, twin, hardware tiers, scripts, CI | 10-12 .. 10-19 | +44 ... +2 (+51) | 5-14 | 383-1,601 | 11-41 | 7-16 | the machinery audited itself |
| U29-U34 security, memory, timing, legacy parity, docs, licences | 10-20 .. 10-21 | +376 (U30 +346) | 2-15 | 126-1,969 | 6-26 | 2-6 | synthesis lenses |
| U35 first round | 10-21 .. 10-22 | +174 | 96 hand-backs | | 20 | 21 | the planned test campaign |
| U35 redo | 10-26 .. 10-28 | +23 | 94 hand-backs | | | | the campaign and its own findings |

What the numbers say:
- **The planned scope did not grow.** Each unit had 20-50 planned actions throughout, and B1 units had as many
  planned steps as B2 units (U2 218, U5 212; U11 195, U18 194).
- **The execution inside each unit grew.**
  - Lanes went from 0 to 15 per unit, evidence files from 3 to 1,969, and close-scan findings from 2 to 16.
  - The machinery units (U22-U28) added 51 `src/` lines and about 40 k test and tool lines.
- **The speed hid it.** U9-U21, thirteen units, closed in about 38 hours (10-07 06:04 to 10-08 20:34), one squashed
  commit each. Nobody could read the growth while it happened.

## 2. The mechanisms

### 2.1 The goals said "every", and checking became changing

**What the plan's goals say:**
- **Deep:** "every in-scope file is read in full at four levels".
- **Proven:** "every property the audit claims is shown by a biting test or a run".
- **Converged:** "re-verification passes repeat until one ends all green".
- **Closed:** "every item ends in one of OR5.a's states".

**How the plan applied them:**
- 18 lenses applied to each of 25 areas.
- Exhaustive techniques, for example:
  - "inject `CancelledError` at the k-th await for every k";
  - "power loss after every SPI transaction k";
  - "every period combination in the allowed ranges".
- The whole-audit definition of done lists 14 permanent machine checks. None of them measures size, minimality or
  cost.

The owner's requirements did ask for complete *checking*: "check EVERYTHING file by file", "100% of all error paths",
"all the way through rare corner cases tested". The owner's later words make clear that this was about analysis and
testing: "firmware quality already was high. So I expected some details changed due to findings, but in the
dimension of a few lines per module". The plan carried completeness from the checking over into the changing.

### 2.2 The rules that expand got gates, the rules that restrain stayed prose

The owner gave restraining signals before and during execution. Each was applied to its own item and never became a
rule for the whole audit:
- **"yes, but the control arms are overkill" (OR21.a, 09-25):** the arms were dropped. The sensitivity campaign they
  belonged to stayed.
- **OR72.a (09-26):** "four zero-think-time readers are a hypothetical client". That one decision was withdrawn; the
  pattern behind it was not named.
- **OR36 (09-26), "lean, clean, efficient, minimal ... zero artifacts specifically added for testing":** this was
  read narrowly as "no test-only code in the image".
- **OR149 (10-06), "if required at all, if not already safe inherently ... minimal, low complexity":** this was
  integrated as "first ask whether a site is safe by construction, then for the smallest inherent change". The
  finding was still to be closed; whether its trigger occurs was never asked.

**Pillar P6, "Efficient and compact"**, got only an "image-size report". The U0 baseline recorded every image size
(dev 2,238,464 B UF2 after the dependency refresh). No later unit compared against it. Meanwhile the requirements
behind "handles everything" (P2, 66) and "proven to corner cases" (P5, 94) outnumbered those behind P6 (36), and the
pillars had no priority order to settle a conflict.

### 2.3 Every observation was planned as a change, and agent text became binding

**The planning chain:**
- Phase A's harvest, passes and scans recorded 324 seed observations, mostly found by reading.
- They fed a register of 548 requirements. 125 of those are ranked "agent", and 471 carry work (338 of them code).
- The action lists then made "every register work line" a concrete change. The work order holds 1,914 changes in
  6,599 steps.
- At the go-ahead (OR145, 10-06) "the pillars and rules and specifications we wrote and refined are no longer
  subject to change, but become effective". From then on the agent's own requirements bound execution like the
  owner's.

**The owner's review covered decisions, not changes.**
- The owner answered all 15 significant and 53 moderate decisions on the review page (45 "ok"). The 296 routine ones
  went in unanswered, as the page's design allowed.
- The 1,914 changes themselves were never put to the owner.
- The scan shows where the hypothetical hardening came from. In the network and UART files, 29 of the 43 hypothetical
  rows trace to the plan, 12 to execution scans, and 2 have no named origin.

The register's closing states also gave a confirmed-but-hypothetical finding no natural end: it could be fixed,
settled by decision, out of scope, moved to hardware, deferred, or rejected. "Recorded as knowledge, no change" was
not an outcome a lane would choose.

### 2.4 10-06: the special-situation inventory (where the well-scoped part ended)

**What the owner asked on 10-06:**
- "always keep an eye open for such tiny oversights - all places ... Do a scan if you found all such cases after
  each implementation" (OR147);
- "keep an extra eye on all operating modes" (OR148);
- twice whether the list was complete: "Is this really the complete list of situations?" and "Are you sure to have
  found really all special situations now".

**What the agent built in answer:**
- A procedure (`silent_failure_scan.md`) with a derivation that "every unit re-runs".
- A "blind" 381-entry inventory, whose categories include the scheduler queue, the alarm pool, non-`OSError`
  exceptions and `json`/`struct` edge cases. These overlap with what the scan now classes as hypothetical: the alarm
  pool, the scheduler queue, exceptions outside `OSError`.
- A fold of 61 parked scan rows into 328 parts of the work order (OR150.b), "source fixes first, then tests (four
  tiers), SPEC sentences, bench checks and docs".

**The inventory had real value.** The same day it found two real pre-audit bugs, confirmed in the code by the lead: the
ISL29125 settle deadline (now also reproduced by the scan) and the SGP40 compensation masking instead of clamping. The mistake was not the inventory. It was treating 381
hypotheses as work, each closed with code and tests on four tiers.

### 2.5 No owner filter during execution

**The plan removed the owner from the loop:**
- No owner stop-points during execution (PQ8).
- Unforeseen decisions were taken on the owner's behalf with "the more conservative, more easily reversible option"
  (OR2.c), and reviewed only at the end (B5), which was never reached. The owner-review list holds 708 such
  decisions, up to 55 per unit (U14, U15).

**"Conservative" was read the wrong way.** The agent read it as "the safer behaviour", which in code meant another
guard, fallback or timed check. For a codebase that was already solid, the most conservative and most reversible
option is usually no change at all.

### 2.6 The loop that made it exponential

1. **More code meant more findings.** Every unit's close scan read the changed code under 18 lenses and every
   operating mode. Findings grow with code surface × lenses × modes.
2. **Each finding added roughly five parts:** code, tests on four tiers, a spec sentence, docs. The surface grew
   again.
3. **The tests and tools were scanned too.** The goal "Broad" covered every tracked file, "code, tests, tooling, CI".
   So the tests the audit added were themselves audited with the same depth. The machinery units (U22-U28) added
   about 40 k lines to the tests and tools and almost nothing to the product. Examples:
   - 7 of U23's 9 commits fix or probe live-check cleanup;
   - U25 had 6 fixes for port 53, the bind capability and the tracer.
4. **Bigger suites made slower and flakier gates.** Every unit closed with the full suite at both GC stages plus CI.
   Overruns and flakes then went through "no flake without a root cause", which pulled the harness into
   investigations already in U11 and U13 (the settrace frame allocation, the coverage tracer's heap). CI timeouts
   went from 45 to 175 minutes.
5. **Parallel lanes added integration work.** Lanes went from 0 to 15 per unit, and each merge needed a gate, a fix
   and a gate again.

### 2.7 One level of rigor for everything

Firmware, buildgen, unit tests, the twin, the runners and the audit's own records all got the same depth. The test
campaign (B3) was planned as "every test reviewed; one fault-planting campaign per module; intent map; combination
and interaction matrices". U35 executed exactly that:
- 8,467 review rows;
- intent and levels walks keyed on line numbers, so every merge needed a re-render (20 commits);
- interaction matrices, and harness growth to reach edge cases.

The owner's later line states the missing tier: "The unit tests shall have good quality, but don't need deep dives.
The audit verification machinery is just a temporary tool."

### 2.8 No cost feedback

- **No budget was set.** The token budget question (PQ9) was answered only for agent count.
- **The calibration was never run.** The LED pilot was planned as "the calibration pilot: cost, convergence rule,
  register format", but no cost figure was recorded and no unit was compared against it.
- **Nothing tracked the cost per unit:** no change in `src/` lines, bytecode, image size, CI time or tokens per unit.
- **The flash use went unseen.** The dev image's payload grew from about 1,093 KB to about 1,158 KB. The audit used
  about 65 KB of the 107 KB that were free (61 %), and nobody looked. This corrects the report's "about half", which
  was estimated from bytecode only.

### 2.9 Cascades were not read as a signal

An addition protecting another addition was treated as normal work, never as a sign that the root was wrong:

| root | led to |
|---|---|
| the NeoPixel 300 s rewrite | a lost shutdown cancel |
| `ready()` moved onto `wait_for_ms()` | the same lost cancel, then a move back |
| the NTP resync on elapsed time | a resync one tick late, then a rounding rule |
| the recovery ladder's no-controller state | a bool contract and 26 raise sites in four drivers |
| the C-stack escalation | about 120 report calls and a bounded escalation wait |

No rule asked: "would removing the root be smaller than protecting it?"

### 2.10 The U35 redo repeated the pattern at lane level (the lead's own part)

As lead of the redo I repeated the mechanisms in small:
- 94 hand-backs in 34.5 hours;
- findings outside a brief became the next lane;
- every lane got exhaustive verification (combined tiers, bite runs);
- a closing ledger only after the owner had to say "not designed self-sustaining / will never end".

The owner had to intervene repeatedly:
- "You are way too fast" (10-26);
- "You papered over the event loop fallback as well" (10-26);
- "The CI failures are there for several days" (10-27);
- the 5-minute check, and the pause (10-28).

The investigation into MicroPython's C sources for a rare lost cancel (the NeoPixel case) is the clearest example of
effort without proportion.

## 3. Why the first ten units felt well scoped

- **One owner-defined deliverable each.** U1-U8 were the legacy move, the error catalog, the log-repeat rule,
  compare-before-write, config objects, one-source website definitions, the level ladder and the `@tunable` scheme.
  Their scope was the owner's words, and the result was small or negative: U5 −115 `src/` lines, U6 −1,341 website
  lines.
- **They closed before the new scan shaped any unit.** They closed on 10-06, the same day OR147/OR148 arrived, so
  the special-situation inventory and the 328 fold parts never shaped their content.
- **U9 and U10 were small too.** U9 (the LED pilot) added +19 lines. U10 (system-wide contracts) added +7 net, mostly
  renames and shared primitives. U10 did plant the seeds of later cascades, `utc_now()` and `TickSeconds` among them,
  which every later unit then adopted.
- **The jump came at U11.** The core modules were the first to meet all three at once: the plan's lenses, the new
  scan and the mode inventory. U11 added +172 lines, U13 +459.

## 4. What it caused

| effect | size |
|---|---|
| firmware | +27 % `src/` lines, +29 % bytecode, about 65 KB of image used out of 107 KB free |
| code in doubt | about 1,640 of about 3,900 changed lines (hypothetical, excessive or cascade) |
| real defects created by the cascades | the NeoPixel lost cancel, the UDP lost cancel, the NTP resync regression, the I2C double recovery step |
| unreviewed decisions | 708 taken on the owner's behalf |
| tests and tooling | 2.2×, 233 k lines; about 30 k lines test the tools |
| CI | unit-tier timeouts 45 → 175 minutes; the twin matrix 6 → 24 jobs |
| docs | SPECIFICATION.md 3× in bytes; one register of mostly test values is 47 % of all doc growth |
| repo | `audit/` 14,052 files, 127 MB |
| cost | the owner's figures: time ×4, tokens ×15, and not done |
| the owner's attention | spent on interventions instead of decisions |

**On the other side, the knowledge is real:**
- 17 confirmed gaps in the pre-audit code;
- platform facts verified against the pinned source;
- the hardware-round list;
- the owner's own features, delivered.

## 5. Where it could have been caught

| date | signal | what it called for |
|---|---|---|
| 09-25 / 09-26 | the owner's "overkill" and "hypothetical client" | a general rule against building on hypotheses |
| 10-06 | 381 situations derived; 61 rows folded into 328 parts | stop: are these real, and is this work? |
| 10-06 | OR149's "if required at all" | an admission test on the trigger, not only on the size of the fix |
| 10-07 | U11 +172 and U13 +459 `src/` lines, against the owner's "a few lines per module" | a change budget per module |
| 10-08 | U18-U20 with 11-12 lanes and up to 939 evidence files each | a volume alarm to the owner |
| 10-13 | U23's 7 of 9 commits on harness cleanup | tiered rigor: the machinery is not the product |
| 10-20 | U30 +346 lines for an unmeasured C-stack trigger | the trigger measured, or the code not added |
| 10-26 .. 10-28 | 94 hand-backs, the owner's repeated interventions | the closing ledger from the start, and an owner checkpoint |

## 6. How it could have been prevented

Each rule answers one mechanism above. All of them also apply to the cleanup ahead.

1. **Code only on evidence.**
   - Product code changes only for an owner decision, an observed failure, or a reproduction against the real code.
   - Anything else is recorded as knowledge: a fact in the spec, a hardware-round item, or at most one cheap test.
   - A hypothesis never becomes code on its own (2.3, 2.4).
2. **Restraint as a gate, not as prose.**
   - A change budget per module ("a few lines per module").
   - A bytecode and image delta per unit against the U0 baseline, and a flash headroom floor.
   - Exceeding any of them stops the unit and goes to the owner with the diff (2.2, 2.8).
3. **"Conservative" means the smallest change.** For solid code, that is often no change (2.5).
4. **Tiered rigor.**
   - Firmware and buildgen: deep.
   - Unit tests: good quality, no campaigns.
   - The audit machinery: minimal and throwaway. No tests of tools, no records keyed on line numbers, no raw logs in
     the repo (2.7).
5. **Inventories are reading aids, not work lists.**
   - No "for every k" technique and no exhaustive matrix as a source of work.
   - One pass per area. Lenses that always find something cannot be the end condition (2.1, 2.6).
6. **The cascade rule.**
   - Code that exists because of another addition first questions its root.
   - A chain two deep goes to the owner (2.9).
7. **Owner checkpoints with numbers.**
   - At every sync point, five lines: `src/` lines, image size, test lines, CI time, tokens, and the decisions taken
     on the owner's behalf.
   - Those decisions reviewed every few units, not at the end (2.5, 2.8).
8. **The agent's requirements stay proposals.** An agent-written requirement binds only once the owner adopts it, and
   the owner sees the change list, not only the decisions (2.3).
9. **Lanes from the plan only.**
   - A finding outside a brief goes to a list, never to a new lane.
   - The lane count is capped by what the lead can review line by line (2.6, 2.10).
10. **A budget agreed with the owner.** Time and tokens per phase, with a stop and a report at 80 % (2.8).

## 7. Sources

- **The audit plan** (`PROJECT_AUDIT_PLAN.md` at `497b3eda`):
  - 1.1-1.2, the goals and definition of done;
  - 3, the owner decisions (PQ8, PQ9);
  - 3.2, the owner rows OR2.c, OR5.a, OR21.a, OR36, OR72.a, OR140, OR145, OR147-OR150;
  - 4.1-4.3, the method, lenses and techniques.
- **The consolidation** (`audit/CONSOLIDATION.md`): section 1, the pillars; section 2, the phases.
- **The requirement index** (`audit/pass2/INDEX.md`): the requirement counts.
- **The work order** (`audit/order/work_order.json`): steps and changes per unit.
- **The register** (`audit/REGISTER.md`): the unit table and the owner-review list.
- **The open findings** (`audit/sweeps/open_findings.md`): rows by originating unit.
- **The review page** (`audit/review/decisions.json`, `answers.json`).
- **The evidence folders** (`audit/artefacts/evidence/U*_close/`): file and lane counts; U18's index.
- **The U0 baseline** (`audit/artefacts/ENV/baseline.md`): the image sizes.
- **Lane F4c2's dev image of 2026-10-26** (`S/u35/laneR/f4c2/fw/firmware-dev.uf2`): 2,371,072 B.
- **The redo's lead notes** (`S/u35/lane_plan.md`): notes 163, 165, 320, 357, 358 and 362.
- **The scan parts** (`scan/A.md`-`G.md`): the H-row origins and the cascades.
