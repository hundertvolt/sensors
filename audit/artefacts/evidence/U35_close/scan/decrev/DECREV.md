# The decisions taken on the owner's behalf, re-checked against the refined picture

Written by the lead, 2026-10-28 12:50 UTC. Read-only: nothing in the repo changed, and nothing ran on the Unix port,
the twin, the tests or a board. Checked at the pushed head `11b66cd8` (product tree `497b3eda`), against the pre-audit
`25caf528`, legacy and the pinned MicroPython v1.29.0 source.

The owner's request (2026-10-28): "First, commit and push. Then, with the updated big picture about the project and
its shape, revisit the decisions you took on my behalf, and check if you would answer differently with the new
knowledge. Only check, and see them in a global context, also not contradicting each other, and document your
findings."

The new knowledge applied: the picture's lines L1-L8 and section 8 (`scan/PICTURE.md`), the second pass
(`scan/scan2/SCAN2.md`), the first scan (`scan/REPORT.md` and its row files), the drift analysis (`scan/DRIFT.md`), and
the owner's words across the audit. Settled and not re-opened: every "ok" on the review page, the Wi-Fi behaviour, the
FRAM per-owner seed. For those this file notes at most a smaller form.

## 1. In short

- **What was checked.** Every decision an agent took without the owner's words:
  - the review page's 364 planning decisions;
  - the register's 704 rows of decisions taken during execution, and its 68 parked changes;
  - the redo's own lead decisions;
  - about 1,270 values and rules in SPECIFICATION.md Part N;
  - about 450 agent-tagged lines elsewhere in the repo.

  After joining the decisions that appear in several sets (a review item, executed in a unit, written into the spec,
  with a value in Part N), that is **2,784 decisions**:

  | same answer today | the owner's | smaller form | different answer | obsolete | replaced later | needs a check |
  |---|---|---|---|---|---|---|
  | 2,278 | 201 | 75 | 82 | 71 | 66 | 11 |

- **Most decisions stand.** About 82 % would be taken the same way today. Most of them are routine:
  - names and wording;
  - placements that follow an existing pattern;
  - test-side mechanics the owner's rules already cover;
  - values whose mechanism stays.
- **82 would be answered differently.** Almost all fall into six kinds (section 3):
  - a hypothetical finding made into code;
  - a timed check or bound;
  - a test need built into the product;
  - an agent rule that widened an owner rule;
  - the scale of the records and the parallelism;
  - a working pre-audit or legacy behaviour changed without the owner asking.

  Each different answer rests on the owner's words or on a verified fact (a source line, git, the pinned MicroPython
  source, a datasheet), never on a hypothesis.
- **71 become obsolete with the cleanup.** They answer questions that exist only because of a mechanism the cleanup
  removes. They stay documented as knowledge.
- **In eight places what was built differs from the owner's words** (section 4; a ninth is resolved). In seven
  more, agent text is credited to the owner (section 5).
- **Taken together, the different answers are consistent.**
  - They contradict neither each other nor an owner decision, under three conditions (section 7).
  - They remove nothing from SCAN2's keep list.
  - Every confirmed gap and every rare but real case stays covered. One behaviour visible to users changes back to
    legacy: the wet bulb in its cold-dry corner.
- **One error in my second pass.** Its G3 part (S2-G3-7) listed W12 among the codes to remove; the crosswalk (G4b)
  already kept it, and it must stay: the captive DNS teardown, which predates the audit, uses it. One record gap also
  turned up, and is fixed (section 2).

## 2. How it was checked, and the record gap it found

- **Sets.** Eight read-only parts each judged one set, giving every decision one verdict, a topic and the picture line
  it touches. A crosswalk then:
  - joined the 84 decisions that appear in several sets;
  - settled 26 cases where parts gave the same decision different verdicts;
  - checked 19 contradictions across sets;
  - checked the different answers as one set.
- **Verdicts.**
  - "Different" needs the owner's words or a verified fact.
  - Anything suspicious and not settled statically is a check, not a verdict.
  - Only the owner's words count as the owner's decisions, whatever agent text says.
- **The record gap.**
  - The parts read the owner's words from `PROJECT_AUDIT_PLAN.md`, the rulings file, `CHECKLIST.md` and the review
    answers. 56 further entries existed only in the lead's lane plan, about 30 of them real owner quotes.
  - Example: one part rated the CI mirror check and package cache as an agent decision against the owner's "Don't care
    about proven external issues so far." (2026-10-27 16:48). The same evening the owner asked for an investigation
    ("The CI failures are there for several days as far as I remember - ... Maybe it actually would be good to
    investigate."), then approved the fix ("What about option 3 plus cache? Is there something adversarial to using the
    cache?", then "Yes do it like you proposed").
  - The crosswalk re-settled every row these words touch (the CI cache, the third lwIP patch and its retirement rule,
    the loop-end record, the NeoPixel check, the closing ledger).
  - The rulings file now carries the missing words, including the whole morning of 2026-10-28, and `CHECKLIST.md` has
    a rule: every owner word goes into the rulings file as it is given.

## 3. The different answers, by kind

### 3.1 Hypothetical findings made into code (about 30)

Most come from the first silent-failure scans (2026-10-06), folded into units as "parked changes". Each is rated
hypothetical in the first scan with its reason. Each new answer is the pre-audit behaviour, and the finding stays
documented.

| decision as taken | new answer | basis |
|---|---|---|
| two 10,800 s sample-age checks at the consumers (notification, SGP40) | none | `_store_scd()` stamps `utc_now()` every cycle, so they never fire; the owner on hardcoded delay checks |
| W73 stuck-RDY counter (SCD30) | none | SCD-6 hypothetical; the re-store is the owner's named exception |
| BMP3XX power-on detector, EVENT/ERR_REG read each cycle, W71 | none | BMP-1 hypothetical |
| BMP3XX out-of-range code E27 at the BMP3XX site | a plain read failure | BMP-5 hypothetical; E27 stays for the SCD30 range gate |
| ISL29125 shadow compared every read cycle | after a failed write or on a GET, as before | the datasheet allows a silent change only by reset or brownout, which BOUTF handles |
| ISL29125 calibration timeout W75 | console line, as before | ISL-9 hypothetical |
| SGP40 restart keeps the live VOC state | the restore, as before | SGP-12 hypothetical; the backup is at most one BackupPeriod old |
| `ResetBits` in `/status` | the decoded reset reason only | A-S4 hypothetical; the owner's reset-reason table (OR60) |
| W69 CONFIG_LOST after a reformat | the console line | hypothetical, and it raises its own false alarm after every scratch build |
| E28 for a RAM-only logger | the console line | A-P3 hypothetical; the confirmed unreadable-store branch stays |
| `ConfigUnpersisted` key in `/status` | none; the flag stays for the shutdown flush | errno 14 in CFGMGR's error count already shows it |
| notification `State` field | none | a new API field with no owner decision and no other reader |
| uptime tick re-armed on a bounded sleep | the catch at the arm, as before | the refused-arm trigger was refuted |
| supervisor fault entry E115 | the watchdog reset carries it | the watchdog resets either way |
| NTP 44-47-byte replies refused; resync cadence from elapsed time | as before | NTP-9 and NTP-12 hypothetical; the owner's Q10: "the interval as such is arbitrary" |
| DNS reply filling the buffer taken as truncated (W16) | as before | no EDNS is sent, so servers truncate at 512 B themselves; the 512 B receive (a confirmed gap) stays |
| captive DNS re-raising a MemoryError (E23, 3 s pause) | the pre-audit catch-all: an unparsable query gets no answer | the keep was the lead's, not the owner's |
| stored NTPHost/DNSFallback re-checked; HTTP version refused; a page build-date stamp for a reflash mid-request | none | each hypothetical (S2-G2-6, WS-2, S2-G3-14) |
| a chunk read's MemoryError degraded with an entry (BR3) | no catch | a 268 B copy once per boot; the deleted F.2 rule "only worth closing for a concrete, non-hypothetical threat" |
| WR1, each bus's own settings in the twin's device picks | one line of knowledge, the SGP40 twin bus default fixed | the lead's own probe: 0 of 14 picks change |

The seed behind this kind is a rule taken early: every open finding gets a unit (REG:329). The new answer:
`open_findings.md` stays as the record, but a finding becomes work only once it is verified or the owner decided it
("building upon hypothetical findings is a clear no-go").

### 3.2 Timed checks and bounds (about 15)

The owner's words: "hardcoded delay checks like this are a very bad, very awkward pattern", and the NeoPixel words
("it patches a rather hypothetical issue instead of cleanly and minimally implementing something clean").

| decision as taken | new answer |
|---|---|
| the NeoPixel overlay rewritten at least every 300 s | the pre-audit wait on its flag, with no timeout (−5 lines); it also removes the confirmed lost shutdown cancel |
| one shared timed-wait primitive and a sweep of every `wait_for` site (the lost-cancel answer) | none; one Part F sentence on `wait_for`'s cancel property |
| "bound every wait that can be bounded" | a bound only where a verified condition needs one |
| a 1,200 ms bound on the escalation's log write | none; the reset record is written before it, the watchdog still resets with code 20 |
| web server start: 3 attempts, 5 s apart | one start, then the supervisor's restart: server sockets set `SO_REUSEADDR` and lwIP builds with `SO_REUSE 1`, so a restart rebinds at once |
| whole-millisecond waits extended to one-off sleeps | the rule only where it matters (waits in loops) |
| the BMP3XX conversion wait and the I2C scratch view rewritten | the pre-audit STATUS poll and per-read view |
| a build rule: the I2C timeout under half the smallest hard consumer | none for the field devices; the boot bus-clear budget stays the one I2C timing check |
| a shared twin retired by wall-clock age (89 s) | idle detected by its event: the SGP40 warning on a boot that never syncs |
| seven tests that sleep a fixed time, then assert | wait for the condition with a bounded poll or an event (OR37.a (3): "yes, all exactly like this") |
| CI job budgets of 175 min and a 5× harness timeout | near the measured run plus a margin, with the owner's two retries kept inside |

### 3.3 Test needs in the product (about 10)

Against OR36 ("zero artifacts specifically added for testing") and the owner's test-side "Option 1":

| decision as taken | new answer |
|---|---|
| `setup()` returns a bool everywhere | the pre-audit `None`; a bool only on dev's `UARTComm.setup()`, whose caller reads it; `deinit()`'s and `set_level()`'s bools go with it |
| `set_utc_valid(*, valid=...)` | no parameter; the review's own routine item says so, and the tests reset the flag through their own helper |
| the exception-handler guard "only where no handler is set" | a check: whether the owner's 2026-10-07 approval covered the guard |
| `_shutdown_task` kept because four test files read it | goes; the pinned asyncio keeps the task referenced |
| console lines in the UART driver, UDP and RegionBuffer so the memory gates see their failures | the driver catches keep their sentinels and the owning module's logger reports at its level |
| a launcher stop file for a twin hang reproduced 0 times in about 1,900 tries | none after the diagnostic |
| a rig override where a test-level fix exists | the test-level fix (OR20) |
| four planted-mismatch tests | the two mirror pins stay, the plants go (the owner's 2026-10-23 planting ruling) |

### 3.4 Agent rules that widened an owner rule (about 10)

- **The tunables register's scope.**
  - SPEC:11921 credits "every test tier's sleeps, bounds, timeouts, retries ..." to the owner as a paraphrase. The
    owner's words are narrower: OR30, runtime and timeout parameters of the test suites; OR30.a (1), "every tuned (not
    derived) value that must be retuned as the project changes".
  - New answer: about 860 test-internal rows leave the register, and their constants stay in the tests.
  - The cut follows the owner's criterion, so the hardware-tier budgets OR30.a (1) names stay, with the accuracy check
    of OR30.a (3) visible.
  - The tag-count rule per file goes with it.
- **"Silence on a routine batch counts as approval."**
  - This is agent text in the review page's owner step. The owner's words: "recorded decisions I took (not the session
    agent)" (OR48.a), "Decisions I really took are still valid.", "The OK in the review stay valid.".
  - The 295 unanswered items stay agent proposals; this file judged them as such.
- **The resolver logging through a passed-in logger, written beside the "No logging in these layers" rule.** The rule
  constrains the code, not the reverse: the resolver returns its result, and its one caller logs (about 45 device lines,
  3 catalog codes).
- **"A new check is not growth of existing work"** and **"records lanes fix any defect they find in-lane, src
  included"**.
  - A new check's cost counts like any other growth.
  - Product code changes only on an observed failure or a reproduction ("in the dimension of a few lines per module,
    very minimal and clever ... Surely not by patching multiple loops over another.").
- **Run-time narrowing kept as a standing rule.** Same decision, smaller form: a typing-side narrowing (a cast) instead
  of a branch that can never run (the owner, 2026-10-27, on errors that exist only for typing).
- **The catalog's "Retired numbers are never reused".**
  - Agent text with no owner words, and no part's set holds it.
  - Each code the cleanup removes then leaves a tombstone, about 20 in all.
  - Its stated reason, FRAM history across reflashes, is not required (OR47.a: "no requirement for the fram to stay
    consistent through firmware re-flashes").
  - A point for the cleanup plan.

### 3.5 Scale of records and parallelism (about 15)

- **The lanes.**
  - U35 was cut into ten lanes, then 13-15. New answer: a few lanes the lead reviews line by line.
  - The owner's words: OR107 "don't overdo it"; OR145 "use parallelization carefully"; 2026-10-21 "Don't overdo it".
- **The records lanes.** Different answers on their content:
  - per-test verdict ledgers;
  - reverse maps;
  - matrix records;
  - record checks at every merge;
  - re-location passes;
  - a coverage campaign over every uncovered line;
  - scanner reader extensions;
  - new twin chip knobs.

  The basis: OR48.a ("make sure everything is found, but no list or permanent record") and the owner's 06:37 words
  ("The audit verification machinery is just a temporary tool.").
- **Whether the paused lanes resume is not settled by this check.** The crosswalk read the owner's words in order:
  - 05:30: the owner kept all nine ledger items ("I don't actually want to cut back or trade anything, I just want to
    make sure that you set up the process such that it can finished and is not designed self-sustaining / will never
    end").
  - 06:37: the owner reopened where the effort goes ("So we will have to find a distinction where to put the effort.").
  - 07:02: the lead's mapping of the paused work was stopped.

  So the ledger stands as the owner's, and the distinction is an open owner topic. The different answers above say how
  I would weigh the content if that distinction is made; they do not decide it.

### 3.6 Working behaviour changed without the owner asking (about 8)

| decision as taken | new answer | basis |
|---|---|---|
| `rel_humidity()` refuses instead of clamping; the wet bulb refuses a cold-dry corner | the pre-audit and legacy clamp to 0-100 %; the wet bulb's pre-audit domain | the owner's note "Keep them ... Adapt the tests to be in line with the others"; the no-clamp rule is agent text (OR140.a) |
| SGP40's own persisted "no backup" warning folded away | kept, as before | the owner's note on one entry per fault: "It should rather stay as is ... a notion of a traceback and blast radius of an error is actually desirable" |
| 35 VOC constants pre-converted once | upstream's per-sample conversion, the literal port | OR109, OR109.a (1) "No rework of the fix16 helpers"; the literal-port rule |
| a chip-setup failure goes straight to the controller rebuild | the normal ladder, mild rung first, keeping `_rungs = 0` and I2C-5's report | OR113's order |
| a zero-length guard in the UART driver | none; no caller passes zero | the unit's own record |
| a `None` branch for a raw SGP40 reading | none, or a typing-side form | the owner's typing rule of 2026-10-27 |
| a per-episode log flag in the notification service and in three other modules | the central newest-entry rule only | U3's rule is the owner's (OR35.a, OR35.b "Pure and simple.") |

## 4. Where what was built differs from the owner's words

These are not new decisions: the owner decided, and the tree does not match.

1. **WoZi wording.** The owner on `wozi-move-owner-operation`: such specialties "shall be removed from the docs". The
   "exemplary/base, never flashed" wording is still in CLAUDE.md (:168, :191-205), README.md:410, SPECIFICATION.md:10575
   and `devices/wozi.toml:1`. The docs pass only narrowed it to sessions.
2. **VOC state 2.** The approved `state-code-values` text says "settled"; the catalog says "learned", forced by the
   decision-vocabulary check.
3. **`rel_humidity()`'s clamp** (section 3.6). The owner's "change" note asked to keep the helpers and adapt the tests.
   Removing the clamp went past that note.
4. **The internal LED request.** The approved text: an internal request "waits for the running signal up to a
   deadline and then queues, as legacy queued it, but bounded". The code drops it after 120 s and logs W67.
   - The deadline is the owner's; the drop at expiry and W67 are the agent's.
   - The text reads as queueing when the deadline passes, and the owner's note supports that ("internal LED commands
     are guaranteed to be bounded by number and frequency, they won't flood the device").
   - The form that follows the words: queue, not drop, at the deadline. W67 then goes.
5. **E28** reaches further than the owner's 2026-09-16 words, which cover the FRAM_FULL refusal only (section 3.1).
6. **The heap floor row** (SPEC:13099) reads "measurement owed". The owner's `heap-floors-kept` "ok" says the floors
   change "only through a new derivation of the need, never to fit a reading".
7. **"Option 1"** (2026-10-20) covered the unit tests' log level. SPEC I.4(e) credits it for the product console lines
   as well (section 3.3).
8. **The comment width, now resolved.** An agent decision (R-4, "no comment-cap length rule") went against the
   review's "ok" (a 110-character wrap). The owner's later Q6 "c" (120 characters) settles it, and the code follows,
   so no gap is left.
9. **OF-16's per-file tag count.** It was changed under the owner's delegation for test-only changes ("That's actually
   a combination you don't need to ask me for."), but the record still reads "open, waits for the owner". That is a
   records error only.

## 5. Agent text credited to the owner (seven sites)

- **OR21.a (2):** "existing control arms ... are left as they are". The owner wrote "yes, but the control arms are
  overkill". Two guards were added to an arm after it.
- **OR140.a (4):** "and the helpers with the no-clamp rule".
- **SPEC:11921:** the register's scope, "(owner, 2026-09-25, paraphrase)".
- **SPEC:3666-3668:** "An expected condition prints only", generalised from a paraphrase about startup jitter.
- **OR143.a:** "catches go", which is the lead's integrated text.
- **REG:637:** "(owner, 2026-10-08)" for "at most three agents"; the owner's words name no number.
- **SPEC I.4(e):** "Option 1" on product console lines.

The same mechanism appears in REPORT.md's "What went wrong", tagged "the owner agreed". The agreement ("I agree with
wour conclusions about scope and effort.") answered the lead's drift assessment in the conversation, before REPORT.md
was written. The different answers that cite it also rest on other owner words of that day.

## 6. Owner statements that pull apart (facts; no question is framed)

- **(a) Test values.** OR30.a ("yes to all three": scope, form, accuracy for the tunables) against the 2026-10-28
  tiering ("The unit tests shall have good quality, but don't need deep dives.").
- **(b) Where the effort goes.** 05:30 ("I don't actually want to cut back or trade anything") against 06:37 ("So we
  will have to find a distinction where to put the effort.").
- **(c) A lost UART frame.** The review "change" note on `uart-flash-erase-overrun` against the 2026-10-22 accepted
  degradation of a flash stall.
- **(d) The console at DebugLevel 0.** OR35.a ("Console logs actually should keep printing all") against the 2026-10-07
  handler design, Q6 "Option a" and "Keep as is, no added complexity.".
- **(e) FRAM's own log for one invalid block.** OR56 ("never both at a time") against the "stay as is" note on one entry
  per fault. FRAM's own log gets an E and a W, as before the audit.
- **(f) The refused hotspot timer arm.** Wi-Fi's option (b) against Q2, that a timer shortage cannot come as a surprise.
- **(g) The threat model.** A hazard row was added to A.11 after the owner signed the table off.
- **(h) The wet bulb.** "Adapt the humidity to the verified range" against the wet bulb's cold-dry corner, which the
  pre-audit domain returns to.

## 7. The different answers as one set

- **Against each other.** No two contradict. The crosswalk checked the pairs that touch, for example:
  - the escalation's unbounded write with the general bound rule;
  - the I2C budget check with the per-bus ceiling;
  - the codes that retire with the codes that must stay (W12);
  - the unpersisted flag with the owner's staged write.
- **Against owner decisions.** Three conditions:
  1. the CI and harness budgets keep the owner's two retries for tests that run into a timeout;
  2. the register cut keeps the hardware-tier budgets of OR30.a (1), and their pending accuracy check stays visible;
  3. every change passes the owner's 2026-10-22 test: "double check where it came from what it affects, what its
     intended function is ... no regressions, also no hidden ones".

  The cleanup still owes the per-change table that test asks for.
- **Against SCAN2's keep list.** Everything on it stays effective:
  - the owner's decisions in their smallest form: the C-stack reboot, the NeoPixel queueing, the staged write, the FRAM
    seed, the DMA ring, the hazard mode, the head limits, a trace per dropped connection, the Q6 handler, Wi-Fi;
  - the confirmed gaps: the unreadable log store, captive DNS's 512 B receive, the zero NTP timestamp, I2C-6/7, the
    SGP40 restore cycle, the loop-end labels, the emergency buffer, the listener close, the cut config write;
  - the rare but real cases: a wedged bus at boot, a chip failing in operation, a declared FRAM that never sets up, an
    unreadable store at boot, an unpersisted store at shutdown, a C-stack overflow.
- **What taking them all would regress, unless handled:**
  - **The memory gates' sight.** The UART driver's, UDP's and RegionBuffer's caught failures go silent unless their
    text is routed through the owning module's logger. That is not a product regression, but CLAUDE.md's standing
    rule.
  - **The VOC test time.** VOC-5's revert takes away one of the two causes of `test_voc_algorithm.py`'s 20.0 → 6.3 s,
    to be measured ("not cutting back strictness, but making it more efficient").
  - **A visible output.** SCD30's published `WetBulb` returns to legacy in Stull's cold-dry corner.
  - **The bench proof.** A UART cap on dev near the echo's need shortens the bench's largest-train proof; the wire format
    is untouched.

## 8. Corrections to my earlier reports

- **W12** (G3's S2-G3-7; G4b already keeps it) stays. The captive DNS teardown warning uses it at head
  (`asy_captive_dns.py:145`). That event predates the audit (`captive_dns.py@25caf528:153`, wrnno 3), and NTP uses W12
  too.
- **The UART link's `initialized`** stays. The exercise loop reads it (`asy_uart_link_driver.py:133`), and so does the
  hazard dispatch guard (`:282`). Only the `setup()` bool is in doubt.
- **The refusal path.** Close, then trace, is no contradiction of the owner-agreed bound. It is a smaller form of the
  owner's drop trace, and the bound stays on the other arms. The pre-audit "reject cheaply" design has no owner words.
- **The CI mirror check and cache** are the owner's (section 2), not an agent mechanism.
- **The closing ledger** is the owner's (section 3.5).

## 9. What needs verification (merged; nothing was run)

1. **The FRAM SPI SO level with the chip absent**, on dev at the pre-audit image.
   - It decides the lost-FRAM chain (about 60 lines), the RDID probe, OF-250 and E54.
   - At 0x00 the chain goes. At 0xFF the parts differ on what stays; read that case against SCAN2's keep list first.
2. **Whether eight or more soft callbacks queue at once** under the shipped load, across a config flush.
   - It decides the FRAM mempause deadline against the pre-audit one-shot.
3. **The logger-side C-stack check at a near-exhausted C stack**, on the Unix port and against the board's peak.
   - The owner's C-stack reboot in about 118 fewer lines depends on it.
4. **A USB host that never reads**, against the pre-audit image.
   - It decides WS-2's 38 lines, the Microdot print's level gate and the console-starvation test's premise.
5. **The three BR2 fixes.**
   - Read each raising call at the parent of `7008730e` against v1.29.0.
   - A MemoryError only at call entry: revert. Anything else: keep.
6. **The exception-handler guard.**
   - Find the 2026-10-07 proposal the owner answered "Yes, build it that way.".
   - The guard in it: the owner's. Not in it: one line goes.
7. **W29 entries in dev's FRAM log** over the hardware round's boots, read before any `ResetErrors`.
   - None: the retry goes. Any: it stays.
8. **The refused connection's effect on the 9-socket pool.** It changes a label, not the action.
9. **Owed measurements that decide no verdict:**
   - the 100 ms UDP idle rate;
   - the SCD30 readiness defaults;
   - dev's heap after boot;
   - the VOC test time after the revert.
10. **The WS2812 state loss under Wi-Fi bursts**, only if a fix is ever wanted back.

Items 1, 2, 4 and 7 need the hardware round. Items 3, 5 and 6 are static or Unix-port checks for the cleanup's own
start.

## 10. Files

All in `S/u35r/decrev/`; in the evidence folder, `scan/decrev/`:

| file | contents |
|---|---|
| `DR1.md` | the review page, 364 decisions |
| `DR2.md` | register U0-U10, 171 |
| `DR3.md` | U11-U16, 205 |
| `DR4.md` | U17-U23, 159 |
| `DR5.md` | U24-U30, 129 |
| `DR6.md` | U31-U35, the parked changes, the review page's parked items and steps, and the redo's lead decisions, 311 |
| `DR7.md` | SPECIFICATION.md Part N, 1,273 |
| `DR8.md` | agent-tagged lines elsewhere, 409 |
| `DRX.md` | the crosswalk: 84 chains, 26 settled conflicts, 19 contradictions, the different answers as one set, the merged checks, the totals |

- **The part totals.** They sum to 3,021 decisions:
  - 81 were tracked in another set and are counted there;
  - joining the chains gives the 2,784 above.
- **The inputs.** `inputs/` holds copies of `audit/REGISTER.md`, `SPECIFICATION.md`, `PROJECT_AUDIT_PLAN.md` and
  `audit/review/` at `11b66cd8`, the rows extracted from them, and the 56-entry extract of owner words that were in the
  lane plan only. Only that extract, `inputs/owner_words_lane_plan.md`, is in the evidence folder.
- **The briefs.** `briefs/decrev.md` and `briefs/decrev_x.md` (in the evidence folder, `redo/briefs/`).
