# Owner rulings and instructions after LEAD NOTES 118 (recovered by the lead, 2026-10-26)

Source: the lead's conversation context (the compaction summary of 2026-10-23 and the messages after it). Words in
double quotes are the owner's, verbatim. Everything before LEAD NOTES 118 is in `S/u35/lane_plan.md` (restored from
the 656fc82 evidence snapshot).

## Still in force from before (quoted in the summary)
- "Looking at the remaining percentages, I will start the hardware session once U35 is done and defer U36. So close U35
  cleanly, but don't put additional effort into the preparation of U36 unless I give you the go." (2026-10-22; the
  preparation part is superseded on 2026-10-26, below; the stop after U35 stands.)
- "Don't change too much, keep going." (2026-10-22)
- "Don't worry too much about the CI on Git for the moment. There are known large outages ... It's not Git and it's not
  the code." (2026-10-22 or 23)
- Earlier decisions in force: "Solutions you proposed agreed."; "Fine, keep it."; FRAM reads are destructive; "6: c";
  "1: a"; "2: a"; "4: a"; "5: b - system shall be proven stable unter max load allover"; Q3 "option a"; "Clock time:
  Option b, but with a flag in /status showing it might be stale..."; "use fresh agents in most cases."; "Prefer
  accuracy before speed"; "root cause any faults"; "keep an extra eye on all operating modes"; "I just want to make sure
  no evidence to a bug, be it in the firmware or the tests, is silently lost."; "increasing efficiency (significantly
  less effort for same quality, time is secondary) matters!"; "Test duration going up like this is anyhow something to
  fix - not cutting back strictness, but making it more efficient"; the least-wear rule is central; "no regressions,
  also no hidden ones"; defaulted parameters belong in one common place.

## 2026-10-23: how tests pick devices (LEAD NOTES 130, lost; facts in N5's brief)
- "Wait a second. If there was a "first device, whichever it is, tests repetitive stuff without additional
  information", I remember we decided that for speedups. Check that before changing anything!"
- Final description (the one that holds): "My words about not having tests arbitrarily fixed for specific
  configurations or devices still hold. They shall all be treated the same, only depending on their hardware
  configuration. But matrix deduplication is something different! If the pattern is like "the first device runs
  specific tests, which are always and guaranteed present and always identical for every device, fully independent from
  their configuration", and any device could be the first to be tested, then it is a good thing as it saves time and is
  not actually device specific."
- "Just to be sure. My reactions to your alarming imprecise wording are a misunderstanding. Make sure you remove any
  traces from that. What really holds is my final description of how to handle. So target minimal changes."

## 2026-10-23: answers to the lead's questions (LEAD NOTES 142, lost; questions paraphrased)
The lead asked: Q1, Run 11's calibrated leak check costs about 75-90 s more per run, keep it?; Q2, fault planting
scope; Q3, the size of the campaign before the hardware round. Then dead code, the FRAM reflash ruling (:861), and
single-device tests with different wiring.
- "Question 1: This is okay, go ahead."
- "Question 2: I never required to plant faults for every test. Planting faults is a good measure for complex
  measurement tests (e.g. memory exhaustion, leaks, long running accumulating processes, multi layered or external
  dependencies, and similar), but not required for the straightforward tests (which I would assume to be the majority
  by far). Planting errors for those straightforward tests would be complete overkill."
- "Question 3: The goal for the first hardware round after U35 was to have the firmware final. That's still in place."
- "Dead code: Double check it's really dead code. I don't want real features or sensible functionalities removed which
  could be worthwhile in future use. Always regard the modules as libraries, not every feature must be immediately
  used, as long as it is a real feature."
- "FRAM reflash: No behavioral difference at all should arise from a fresh flash or a first boot. If things happen at
  first boot, they must be triggered by evidence (e.g. no config available, FRAM image does no longer fit the layout).
  This should already be the case. But no special actions just triggered because it's the first boot."
- "Single device tests with different wiring should actually be avoided, so these tests should go for all devices."
- "For everything else, it looks ok."

## 2026-10-26: after the container reset
- On the recovery question: "Double check that it is really lost. I don't really believe that. Then come back at me."
- On backup pushes: "Just the way you always did, nothing ever was lost before, even with longer pauses, that is the
  reason why I don't believe it is really lost" (taken as: push exactly as before, no backup branch).
- "Collect everything you still find and double verify thoroughly that you really found everything important. Don't
  simply trust that the recordings are complete. In any case of doubt, rather redo the required steps."
- "And as we have a fresh weekly session now, there is no need to restrict on "firmware first" alone."
- "The three top priorities now: 1. Recover and redo what was lost, be really sure. 2. Firmware really complete, don't
  push fixes to future units 3. If it makes sense / works out, you can start preparing the next units in parallel"
- "Remember what we said about reasonable, technically sensible parallelism and using fresh agents most of the time."
- "Still wait after U35 is done, but as I said, preparing the next units is fine."

## 2026-10-26: answers to the recovery's owner questions (verbatim; the questions are in LEAD NOTES 177-190)
- Q4, the soft-reset record: "B is fine, very rare edge case"
- Datasheets: "You have access to the datasheets repo and may fetch whatever you need."
- Q5, OF-246: "Take option a as recommended"
- Q6, report_unretrieved silent at level 0: "Option a"
- Q7, OF-127: "Option a"
- Q8, OF-186: "These lines are not comments, they count as productive code. Option B." (re-stated by the owner after
  question 9 was put: "I already did answer: These lines are not comments, they count as productive code. Option B.")
- Q9, the boot-phase marker under a power-on cause: "Option b, should be in line with the prior similar decision"
- Q10, the NTP stale rule's up-to-10 s slack (checked on the 10 s tick): "Option a, the 10s don't matter at all
  relative to the interval, and on top, the interval as such is arbitrary. The system clock does not become imprecise
  suddenly, even after multiples of the interval it would be okay. It's rather thought as a signal that something in
  the NTP setup might be wrong." (owner, 2026-10-27)
- D.15 over the unchecked scopes (about 150 files out of order outside src/; options a-d put in prose, recommendation
  d): "Option d is fine" (owner, 2026-10-27). The sweep and the all-scope check go to U37 (B5 close of execution);
  until then lanes only order their own new code and leave pre-existing out-of-order code alone.
- Budget (2026-10-27, after 27 % of the weekly budget since the evening before): "Since our start yesterday evening,
  already 27% of the weekly budget was used until now. Be double sure to apply budget saving techniques without
  cutting back on quality and depth. But don't waste anything." (owner, 2026-10-27)
- Budget, refined: "And don't trade less churn against less parallelism. It's about efficiency - optimize the
  workflow into the direction of: same quality, same result, no major slowdown, but less budget usage. Remove
  unnecessary hogs and keep the good schemes." (owner, 2026-10-27)
- Typing-only guards (_checked_write_results): "As a general rule, future modules are required to fulfill the type
  checking as the current ones do. I once decided (that should be noted somewhere) that catching errors which can
  only happen for the reason of unfulfilled typing are overkill. So what about this?" then "if the check you remove
  really solely covers typing breakages and nothing else it can go (option b). Did you generally adhere to the rule
  I wrote, as it obviously was broken here and added unnecessary complexity to the code?" (owner, 2026-10-27)
- The test for an unnecessary check: "A strong hint for an unnecessary check is that it is proven to be fully
  covered by typing adherence alone, and that it is unreachable with today's code" (owner, 2026-10-27). Applied in
  the D2S brief: both conditions together mark a removal; the walk's typing-based unreachable verdicts and the e51
  uncovered guards are the sweep's starting list.
- PieceBuffer's UART callers and a MemoryError (options A/B/C put in prose, recommendation C): "Do option (c) as you
  recommended" (owner, 2026-10-27). Catch at asy_uart_comm.py's GET and SET sites with the protocol's own fault
  flow (one Class A changelog entry, receiver side, no byte emitted differently) and at asy_uart_driver.py's
  readline (None, Class B). It supersedes the "not caught" wording that came from the lead's OR143.a (2) text.

(owner, 2026-10-27, ~10:09 UTC) On the lead's offer of a lighter model for check-verified mechanical lanes:
"dont change anything for now, but keep it somewhat constrained"

(owner, 2026-10-27, ~10:29 UTC) On the lanes' tool-call seam: "is hard capping the tool usage sensible? so it should
be a goal, but not a hard limit, I'd say"

(owner, 2026-10-27, ~10:30 UTC) "central point: don't cut back the quality, as I told you"

(owner, 2026-10-27, ~10:33 UTC) On the seam: "handing back if it's not closed is extra effort, that's why I asked if
it makes any sense at all"

(owner, 2026-10-27, ~12:30 UTC) On HP2's question (report the stale asyncio child_last upstream / add an override):
"Actually reporting that many issues into a repo is hard. Surely we found a lot, but the maibtainers are currently
overwhelmed with AI findings. So we should report it later and bundled, if at all. So what would be the consequence
of just leaving it as is?"
(owner, 2026-10-27, ~12:41 UTC) On the lead's answer (leave it as is; a Part F paragraph with the bounds; a
BACKLOG.md entry of upstream findings to report later as one bundle, if at all): "Yes, let's do it like that"
- Intermediate pushes (2026-10-27): "Whenever there is a close good opportunity, commit and push intermediate results.
  I don't want to lose anything again." (owner, 2026-10-27). Applied as "U35 (preliminary N)" snapshots on the audit
  branch (the 2026-10-22 precedent): the integration head's tree plus the redo's records in the evidence folder, each
  on the last pushed commit, never while CI runs; the close commit then goes on the last snapshot.

## 2026-10-27, about 16:48 (CI)
"Don't care about proven external issues so far."

## 2026-10-28: the scan, the drift and the picture
- Pause: "Pause all tasks for now". Scan: "Now start a full scan what you find and report back to me once you
  finish." Push: "For now, document these findings in detail and push together with the current state." and "Push
  the analysis".
- Validity: "Decisions I really took are still valid. Verified bugs and gaps are still valid. Knowledge shall be
  preserved. But for the actual code, much might become obsolete when cleaning up."
- The picture: "Every decision and request I take is a puzzle piece of the big project picture and should fit. If it
  doesn't fit, we need to clarify."
- On the picture's questions (2026-10-28 08:53 UTC): "The OK in the review stay valid. WiFi stays valid." Recorded by the lead as:
  every "ok" on the review page stands as an owner decision; the Wi-Fi behaviour as built stays (a unit with no
  network configured returns to its hotspot after every window; OR151's silent mode applies to a configured unit
  whose network is absent). The FRAM question is open: the owner asked what it means.
- (2026-10-28 08:57 UTC) "We thoroughly discussed the WiFi issues and I decided everything already." and "The FRAM idea of yours is
  good, keep it!" The Wi-Fi decisions stand as recorded and are not re-asked; the per-owner CRC seed on FRAM chunks
  stays (owner, 2026-10-28).
- (2026-10-28 09:03 UTC) "document and push". Applied as the fifteenth preliminary snapshot: `scan/PICTURE.md` and the
  answers recorded in `scan/REPORT.md`.
- (2026-10-28 09:07 UTC, background for the cleanup) "now note as background: a verified finding or a taken decision
  stand for their own and are worth keeping at least documented. When cleaning the firmware and the buildgen, some of
  them may become obsolete, e.g. when removing cascades and issues these cascades themselves introduced and are
  overkill or runaway. They have no more direct meaning to the project anymore, but still are worth to know about in
  general. Others, which stay in scope, stay valid and effective as they are, but ideally are resolvable with way more
  minimal code. Rare but real conditions which drop out through the cleanup no longer matter. Rare but real conditions
  staying in scope still shall be addressed - no regressions, but more efficiency." Recorded as PICTURE.md section 8.
- (2026-10-28 09:10 UTC, go-ahead for a second, read-only pass) "Now with all that background and a sharpened vision,
  go through the changes since the audit start again and check if you found all such runaways, cascades, overkill
  places; there might be more hidden or overlaid / higher dimensional occurrences you did not see yet. And if you
  would remove those you already know, there might be side effects which make more overkill visible. Nevertheless,
  real features, real findings inside the minimal code, rare but real cases all keep effective."
- (2026-10-28 11:15 UTC, push, then a read-only check of the agents' decisions) "First, commit and push. Then, with
  the updated big picture about the project and its shape, revisit the decisions you took on my behalf, and check if
  you would answer differently with the new knowledge. Only check, and see them in a global context, also not
  contradicting each other, and document your findings." Pushed as snapshot 16 (11b66cd8); the check is
  S/u35r/decrev/.

## Record gap found 2026-10-28 (lead)
Owner words given during the redo (2026-10-26 to 2026-10-28) and during U35's first run (2026-10-22) were recorded in
S/u35/lane_plan.md's LEAD NOTES only, not here: among them the CI apt fix ("What about option 3 plus cache? Is there
something adversarial to using the cache?", then "Yes do it like you proposed", 2026-10-27, LN322), the listener-close
patch handling (OF-122, 2026-10-26, LN155), OF-107 ("There should be no uncaught exceptions. That's a hard pillar. ...",
"Event loop fallback: option b is fine.", LN156-166), the UART link module exception (2026-10-22), "Test duration is to
be fixed by efficiency, not by cutting strictness" (LN307). The complete extract, with each quote's LEAD NOTE and
context, is S/u35r/decrev/inputs/owner_words_lane_plan.md (56 entries; some are the lead's own questions, marked by
their context). From now on every owner word is appended here as it is given.

### The morning of 2026-10-28, added from LEAD NOTES 357-367 (verbatim, times UTC)
- 05:30 (LN357, the closing ledger): "I don't actually want to cut back or trade anything, I just want to make sure
  that you set up the process such that it can finished and is not designed self-sustaining / will never end"
- 05:58 (LN358, NeoPixel): "The Neopixel issue seems strange to me. Where do the hardcoded 5 minutes come from? And it
  seems such deep down into Micropython items that I doubt it's real. If it is and a closer look still holds, it's
  rather a structural issue and not something to patch over like that. Check this first, especially if it is real at
  all"
- 06:13 (LN360): "Pause all tasks for now"
- 06:37 (LN362): "I completely don't understand what lead you to implementing a pattern like that arbitrary 5 minutes
  check. That's high complexity on a limited device, undesirable as such. At least as far as I understand, it patches a
  rather hypothetical issue instead of cleanly and minimally implementing something clean. And anyhow, hardcoded delay
  checks like this are a very bad, very awkward pattern. Multiple issues we have in our pillars to strictly avoid.
  Looking at the immense effort you put into certain activities, including trying to debug the Micropython
  sources,which could not be more out of our scope , I wonder if the whole audit drifted into a wrong direction." and,
  on the lead's drift assessment: "Your findings and suggestions at least address my largest concerns, so you found
  that by your own. And I agree with wour conclusions about scope and effort. The verification machinery never was the
  goal of "perfection". The firmware shall be the main target, the buildgen as well. The unit tests shall have good
  quality, but don't need deep dives. The audit verification machinery is just a temporary tool. So we will have to
  find a distinction where to put the effort."
- 06:43 (LN363): "One of my biggest concerns is that much complexity was added to the firmware. Patching things was
  never an option, clean and minimal code always was the target. And building upon hypothetical findings is a clear
  no-go, especially if it leads to cascading effects like the one we stumbled upon."
- 06:59 (LN364): "Just to clarify what my expectations for the audit were from the very beginning: - A deep analysis
  of the big picture - Consolidation over the whole project - Agreed on new features being added - Docs to be
  consolidated - Repo cleanup - firmware quality already was high. So I expected some details changed due to findings,
  but in the dimension of a few lines per module, very minimal and clever. Not missing anything, but being smart and
  lean. Surely not by patching multiple loops over another. - The audit exceeded my expected time budget by a factor of
  4 and token usage by a factor of 15 and is not even done yet"
- 07:02 (LN365): "Stop, I didn't give ANY go ahead yet"
- 07:34 (LN366): "Just to clarify. Firmware state at the beginning was already quite solid. We gained substantial
  knowledge ever since. The mistake was how that went into the project. My expectation is that no real, verified gap is
  re-introduced. But the way it flows into the firmware and buildgen is *really* minimal change." and "Now start a full
  scan what you find and report back to me once you finish."
- 07:37 (LN367): "While,you scan, check for violations of our project scheme and pillars, much of the excessive
  additions do violate them"

## 2026-10-28: after the decision review
- (2026-10-28 12:55 UTC, push of the decision review) "push the findings" Pushed as snapshot 17 (on 11b66cd8); the
  evidence folder's `scan/decrev/`.
- (2026-10-28 13:05 UTC, plans for the rest of the audit) "Now, we have the following situation: * We encountered
  issues with the way the audit went * we discovered the reasons and analyzed remedies * we have detailed knowledge
  what needs to be fixed * we know how to change the way of work until the audit finishes * we have leftover work -
  U35 mid action, and the remaining units * The U35 und future planned work still suffer from the old way of working
  and may contain many of the identified flaws and runaway / overkill So it does not make sense to follow them for two
  reasons - they contain wrong decisions and plans, and they follow a known unstable way of work. Nevertheless, they
  do contain actions to be taken to finish the audit. What we need now: * a plan to do all the tidy and repair work in
  the existing status * a plan about which items remain open from current U35 until the end - revised with the new
  knowledge * a plan how to implement it, not drifting away but having a clear and defined end, not cutting back on
  quality" Answered by S/u35r/plan/PLAN.md (a plan only; nothing started).
- (2026-10-28 13:33 UTC, on PLAN.md's section 6) "lets go through the decisions one by one" Taken in order, one
  decision per message.
- (2026-10-28, on decision 1's effort figure) "40 to 60 hours? why?" Answered with the estimate's breakdown; PLAN.md
  section 5 corrected.
- (2026-10-28 13:38 UTC, PLAN.md decision 1, the plan's shape) "then take option a" Decided: the old plans retired as
  PLAN.md 3.1 says; the order R0, R1, R2, R3, round 1, R4, R5, the last round, D.
- (2026-10-28, on decision 2) "Why is the neopixel code to be completely rewritten?" Answered: it is not; the lead's
  wording was wrong. PLAN.md's B7 row corrected.
- (2026-10-28 13:43 UTC, PLAN.md decision 2, the repair method) "Option A, and keep TDD style" Decided: work from the
  current files with the hunk-ledger gate; every change test first (the test pinning the target behaviour is written
  or changed first and seen red, then the code), as CLAUDE.md's step-session workflow (3)-(5) has it.
- (2026-10-28 13:47 UTC, PLAN.md decision 3, item 1, a hardware fact) "1. line level with chip missing: high impedance
  and floating, the pull resistor is on the chip. the pin picks up any stray noise. But what for do you need to know
  that?" Recorded as the board fact for DECREV 9 item 1 (SCAN2's V10): with the FRAM chip absent its SO line floats
  and reads noise; there is no pull on the board.
- (2026-10-28 13:53 UTC, PLAN.md decision 3) "explain the other topics one by one" Items 2-4 explained one per
  message.
- (2026-10-28 13:57 UTC, PLAN.md decision 3, item 2, the mempause auto-unpause) "okay, as recommended" Decided: the
  deadline on the 1 s status pass stays (no one-shot timer; the pre-audit SPEC F.1/C.9 rule "every timer that must fire
  uses PERIODIC"); its two cascade parts are judged in B2's ledger; no measurement.
- (2026-10-28, on decision 3 item 3) "this is about firmware or about tests?" Answered: firmware
  (src/asy_webserver_service.py); the unit tests pinning it go with it; one gated bench test exercises the premise.
- (2026-10-28, on decision 3 item 3) "why were the extra request checks added?" Answered with A.U19.07's basis
  (OR52.a (3), register line G6/R52) and the pinned-source facts.
- (2026-10-28 14:08 UTC, PLAN.md decision 3, item 3, the request checks and the quiet print) "good, accepted" Decided:
  the Content-Length check (ASCII digits, once) stays on WS-1's refusal path; the rest of WS-2 and WS-9's quiet print
  with its merge list go; WS-1's head limits and the 3-4 line C-stack hook stay; no measurement.
- (2026-10-28 14:12 UTC, PLAN.md decision 3, item 4, the FRAM setup's identification retry) "keep it" Decided: the
  up-to-three RDID reads at setup with W29 stay (OR113's first rung, "retry the transaction"); round 1's FRAM log read
  records whether W29 ever appeared, as knowledge. Decision 3 is closed.
- (2026-10-28 14:15 UTC, PLAN.md decision 4, R3's effort) "Yes, take A" Decided: the lean form; each B3 row met on the
  final tree, verdicts and plant results carried over only where neither the test nor its target changed, matrices and
  maps as reading aids and working files, nothing new permanent.
- (2026-10-28 14:18 UTC, PLAN.md decision 5, the budgets) "A" Decided: each phase's budget at the top of its
  estimate (hours and agent runs, PLAN.md section 5), a stop with a report at 80 % of either; tokens on the owner's
  side.
- (2026-10-28, on decision 6) "there are links to the website which explain the errors, or am i wrong?" Answered:
  the device's own page explains each logged code by its number (buildgen/definitions.py _errcount_codes, frozen into
  the image; js/templates.js history buttons and describeCode); a reused number would explain an older entry wrongly.
- (2026-10-28 14:23 UTC, PLAN.md decision 6, retired error numbers) "third option accepted" Decided: no placeholder
  rows for numbers retired before the release (the 6 existing ones go, the codes the repair removes leave none); from
  the release on, a removed code keeps its number unused (the rule and its catalog check stay, applied from then).
- (2026-10-28 14:25 UTC, PLAN.md decision 7, where obsolete findings live) "C" Decided: folded into the facts as
  OR27.a has it; a finding a future reader might rebuild gets one line at its module's Part (the condition, why the
  code does not handle it, what covers it), platform facts in Part F, unverified ones as owed-hardware rows; trivial
  items only in the audit evidence, which stays reachable through the final merge commit. All seven decisions taken;
  R0 still needs its own go-ahead.
- (2026-10-28 14:29 UTC, after all seven PLAN.md decisions, the push) "do a push so we keep everything in any case"
  Go-ahead for a push of the plan with its decisions and the records as the next snapshot; not R0's go-ahead.
- (2026-10-28 14:33 UTC, on the plan's reliability) "What worries me much at the current stage: when going through the decisions,
  there was a pattern repeating: I only asked a question about a fact, and that alone was reason enough for you to
  revise your recommended actions, mostly refining them significantly. This is a clear sign that you papered over
  important details and had such many oversights that multiple appeared just in these seven questions. I wonder how
  many there are in the whole plan. What do you suggest how to handle this - will such issues be found while working
  on it? Before? After? How?"
- (2026-10-28 14:37 UTC, on the plan's reliability, after the lead's answer) "How about revising the current plans now?" A question,
  not a go-ahead; answered with what a revision now covers and costs.
- (2026-10-28 14:44 UTC, the plan check, go-ahead) "Revise our current plans, so they do not contain such glitches anymore. The claim
  falsification check agent scan seems reasonable, too. Add this as a final verification and adapt the run counts
  accordingly." Go-ahead for the check of every PLAN.md row (the five checks, evidence per row, a change list), with
  independent falsification agents as its final verification and their runs added to the budget table.
- (2026-10-28 15:59 UTC, the plan check's falsification agents) "Are these agents the last to go?" A question; answered:
  F3 and F4 are the last planned, the fifth budgeted run is unspent.
- (2026-10-28 16:06 UTC, after the plan check; push and hardware handover, go-ahead) "Once the falsification agent work and
  your follow up is done, save and push.
  Then, prepare a handover for real hardware tests and measurements which can be done without using any existing
  firmware - e.g. env setups, other script heavy work. Also, consider measurements and tests which run with minimal
  examples, not firmware. Prefer timing and script heavy work (but no hours long stuff, no soaks) so we can use the
  remaining 1...2% weekly budget for low token, longer duration measurements, which will yield you much knowledge for
  the upcoming work already." Go-ahead for the push (snapshot 19) after F3/F4 and their follow-up, then for writing a
  handover; the handover is prepared, not run (no real-hardware go-ahead for this session).
- (2026-10-28 16:35 UTC, the hardware handover; CI watching) "Using the current firmware in the tests is allowed, for
  sure.  As long as upcoming changes won't make another result, this is fine. As I said, for simpler parts, minimal
  test scripts are an option as well.
  By the way, with the remaining budget and the changes upcoming, pause watching Github CI for now" Recorded as: the
  handover may use the current firmware wherever R1 leaves the result unchanged, minimal scripts for the simpler
  parts; the PR's CI is no longer watched until the owner resumes it.
- (2026-10-28 16:38 UTC, the hardware handover) "We have several days (aka 12h stretches) we can use with the bench, so
  actually think of maximising the outcome of the few percent" Recorded as: the handover is redesigned for several
  unattended 12 h bench stretches, maximising the knowledge per token.
- (2026-10-28 16:46 UTC, the bench campaign; push go-ahead) "The sessions shall push regularly and dump all details into
  a single hand back file. When you are done with this, push.
  The sessions shall be interruptible anytime without losses (max 10 minutes wait time)" Recorded as: the bench
  sessions write one hand-back file with every detail and push it regularly; any step lasts at most 10 minutes, so a
  stop loses nothing beyond waiting for the current step; go-ahead to push the finished handover (snapshot 20).
- (2026-10-28 16:57 UTC, the session) "Now pause all activity in this session unless I tell you." Recorded as: nothing runs, is
  started or pushed in this session until the owner says so.
- (2026-11-02 15:02 UTC, the bench campaign's results; ends the pause for reading) "On a dedicated branch, the real
  hardware test recordings were stored. Many more interesting and decisive details than originally requested were
  investigated. Read this in and understand it." Recorded as: read the bench branch's recordings and understand them;
  no run, push or other work is started by this.
- (imported 2026-11-02 15:10 UTC from the bench branch's FINDINGS_20261029.md, ec97953d; given 2026-10-29 in the bench
  session, times as that file and its commits place them) Session scope: "measure as many values and situations as
  possible which might be valuable for the planned audit steps"; "There are many open hardware questions in the repo. I
  want to find as many answers as possible reasonably with the current state."; "Save all the details, push, and then
  do run what you held back."
  Radio power save (~17:26): "Power save mode is not an option"
  LAN/UDP storms (~17:51): "C changes are clearly out of scope." and "If there is no official Micropython way to handle
  it, we'll have to accept it as is. No patching or tinkering." Recorded there as: a storm stalling the loop is an
  accepted limitation, the watchdog its backstop; neither the CYW43 packet filter nor a C patch.
  GPIO interrupt storms (~18:28): "Interrupt storms are not really an issue. That only can happen on a board which is
  already defective." No mitigation planned.
  Real flash writes (~18:56): "Try that flash write test once"; under TCP (~19:05): "Try TCP with real flash once".
  Both run once each (three writes and one remove of one scratch file).
- (2026-11-02 15:21 UTC, the bench results; plan go-ahead) "The Mac and the IP addresses are no real hassle. The socket
  cap in Hotspot mode seems to be nothing new and no issues as long as everything stays like now from the global config
  point of view. The UDP  storm is not nice, but so far any research came up with "can't be fixed easily, especially
  needs a Micropython patch". If you have better ideas that would be nice, but would have to be a clean and lean Python
  only solution; otherwise we'll have to live with it. Fold into the plan now." Recorded as: the pushed LAN addresses
  and MAC stay; the hotspot's 2 UDP sockets are known and fine while the global config stays as it is; the storm stays
  accepted unless a clean, lean Python-only fix exists; go-ahead to fold the bench results into PLAN.md (no push named).
- (2026-11-02 15:33 UTC, after the plan fold-in) "So any open questions so far?" A question; answered with the open
  items that need the owner.
- (2026-11-02 15:39 UTC, the open items) "Falsification agent at the end: yes.
  Why not take 4 MHZ and we're on the safer side and still faster?
  I don't know anything about a uart guard, probably introduced by one of the excess excursions?" Recorded as: a
  falsification agent at the end of each R1 batch (the 2026-10-28 offer, 8 runs), run counts adapted; the FRAM's SPI
  clock goes to 4 MHz in B3 (the owner's choice over the offered 8 MHz); the UART guard is not in the code (a bench
  session suggestion after its own probe called `read()` without the lock; the lock-less early return is pre-audit),
  so it is dropped.
- (2026-11-02 15:42 UTC, the UART clock) "What is the MHz uart limit for the rp2?" A question; answered from the
  pinned source, the SDK and the RP2040 datasheet (3 Mbaud with MicroPython's 48 MHz peripheral clock).
- (2026-11-02 15:44 UTC, the SPI clock) "Sorry I meant the SPI" The question above was about SPI; answered from the
  pinned SDK, the datasheet and the bench (24 MHz with MicroPython's 48 MHz peripheral clock).
- (2026-11-02 15:51 UTC, the FRAM's SPI clock) "Then let's take the 8mhz as initially suggested" Recorded as: the FRAM's
  SPI clock goes to 8 MHz in B3 (24 MHz / 3, exact), replacing the 15:39 choice of 4 MHz.
- (2026-11-02 15:53 UTC, the bench's open technical questions) "Try to answer the other deep detail questions by proper
  research" Recorded as: research the open technical questions from the bench reading (source, datasheets, the
  recorded data, host-side reproduction); no hardware, no product code change, nothing pushed.
- (2026-11-02 16:25 UTC, the storm and the crc16 results) "Live with the udp storm and defer the CRC until the next
  hardware run" Recorded as: the LAN UDP storm stays an accepted limitation with the watchdog as backstop, the
  Python-only disconnect idea not adopted; the crc16 hazard results are deferred to the next hardware run (round 1).
- (2026-11-02 16:27 UTC, push go-ahead) "Push the plan" Recorded as: go-ahead to push the updated plan with the bench
  reading and research as snapshot 21.
- (2026-11-02 16:37 UTC, working practices) "Now, do you still remember our best practices about parallel work,
  efficiency and possibility?" Recorded as: a question, no go-ahead; answered from the rulings of 2026-10-23 and
  2026-10-27, LEAD NOTES 260-261, `redo_common.md` "Efficiency" and PLAN.md's batch order.
- (2026-11-02 16:42 UTC, working practices in the plan) "this also applies to our new plan, wherever it is
  appropriate, as soon as we go for it" Recorded as: the parallel-work and efficiency practices bind every phase of
  PLAN.md once it runs (section 4.5); not a go-ahead.
- (2026-11-02 16:42 UTC, working practices in the plan) "if the new plan has no more lanes, adapt the gist of the
  ideas to it" Recorded as: the plan still has lanes in R1-R5; for the phases without them (R0, the lead alone; round
  1, the bench session) section 4.5 carries the gist adapted.
- (2026-11-02 16:49 UTC, the plan against the owner's aims) "By now, we should have a plan which:
  * takes the audit ideas back to the roots
  * simplifies workflow drastically
  * keeps our high quality
  * avoids excursions and excessive / hypothetical excursions
  * will finish the audit well inside a week's budget
  * tries to minimize the changes in src and codegen
  * keeps all discussed features
  * closes all gaps we found which are still relevant
  can you confirm these ideas?" Recorded as: a question; answered criterion by criterion; not a go-ahead.
- (2026-11-02 16:57 UTC, the spirit of the first units) "the audit's machinery was, as I already mentioned, good at the
  first like 10 units, and then gradually, exponentially, increased into something way too large. The first 10 passes
  took one small "Max" plan. Unit 25 alone took 2 large "Max" plans and did not even finish. That is over 40x budget
  for ONE unit compared to the first TEN. We need to get back to the spirit of the first rounds, where the big picture
  of the audit was still clearer" Recorded as: direction for the plan (the shape of U1-U10); not a go-ahead.
- (2026-11-02 17:01 UTC, quality and effort) "Still, keep our valuable findings in mind, and keep the targeted quality.
  The ever-raising effort you invested did actually not lead to higher quality, only to bloated code. So keeping
  quality, closing gaps and saving on effort are not contradictory, but go into the same direction - agreed?"
  Recorded as: a principle for the plan's rewrite; answered "agreed"; not a go-ahead.
- (2026-11-02 17:03 UTC, go-ahead: the plan's rewrite) "rewrite the plan, and target that we are done with 50...60% of
  weekly budget (still a large Max plan)" Recorded as: go-ahead to rewrite PLAN.md in the first units' spirit, the
  whole remaining audit sized to finish within 50-60 % of one weekly budget of the large Max plan. Not a go-ahead for
  R0 or any run.
- (2026-11-02 17:31 UTC, the rewritten plan against the aims) "So by now it fulfills the criteria list I gave you
  recently?" Recorded as: a question; answered aim by aim; not a go-ahead.
- (2026-11-02 18:01 UTC, the goal) "The original goals from the audit and all discussed features all hold. No
  regressions, nothing bad reintroduced. Actually, the goal is how it was initially intended, only before the drift
  happened." Recorded as: the plan's goal is the audit's original goals (PROJECT_AUDIT_PLAN.md 1.1, OR1, OR12) as
  first meant; written into PLAN.md section 0 with the no-regression safeguards in section 2.
- (2026-11-02 18:03 UTC, what stays) "Also, nothing proven good shall be removed, but checked if it can be leaner"
  Recorded as: anything with proof that it is good stays and is checked for a leaner form; only what lacks that proof
  goes. Written into PLAN.md sections 0 and 2.
- (2026-11-02 18:04 UTC, knowledge) "In any case, no knowledge may be lost, and existing knowledge shall be smartly
  used wherever appropriate" Recorded as: every removed item keeps a knowledge line, nothing of knowledge value is
  left only in the session's scratch or lost with `audit/`, and established facts are used, never re-derived.
  Written into PLAN.md sections 0, 2, 3 (D) and 4.2.
- (2026-11-02 18:16 UTC, go-ahead: the plan's final check) "Now ensure the plan is complete, consistent, according to
  our discussions, coherent and correct. Target final quality of the plan itself." Recorded as: go-ahead for a check
  of PLAN.md (read-only on the repository; edits to the plan only), ending with independent falsification (rule 11).
- (2026-11-02 19:16 UTC, push go-ahead) "Push the plan" Recorded as: go-ahead to push the rewritten and checked plan
  with its change list, the check's hand-backs and the rulings as snapshot 22 (evidence only, `[skip ci]`).
- (2026-11-02 19:20 UTC, go-ahead: R0; CI watching) "Go ahead with R0, and resume watching CI" Recorded as: the
  go-ahead for R0 as PLAN.md section 3 states it (the lead alone, no product code), and CI watching resumed (the
  pause of 2026-10-28 ends).
- (2026-11-02 20:13 UTC, status question) "Everything still as expected?" Recorded as: a status question on R0's
  CI run; no go-ahead.
- (2026-11-02 20:27 UTC, question on R0's report) "What and where is the exception handler guard?" Recorded as: a
  question on item 6 of R0's report; no decision, no go-ahead.
- (2026-11-02 20:30 UTC, item 6 confirmed; go-ahead: the CI fix) "That's okay. And fix CI right now." Recorded as:
  the exception-handler guard stays, now on the owner's word (it was a decision taken on the owner's behalf); and the
  go-ahead to fix the red coverage test in R0, now, instead of R2: the byte check on `build-standard` only.
- (2026-11-02 20:42 UTC, standing go-ahead: run the plan) "You don't need to wait for my go for every step. We have a
  plan which seems sound, so keep rolling with our agreed scheme on parallelism." Recorded as: a standing go-ahead to
  run PLAN.md's phases in order without a go-ahead per phase or unit (R0's close, then R1 onward), with PLAN.md 4.3's
  parallelism. What still waits for the owner, by the plan and CLAUDE.md: a clarification (section 6), a user-visible
  removal with no record (section 2, step 1), a budget stop (section 5), and real hardware (round 1 and the last round
  need the owner's hardware go-ahead in this conversation).
- (2026-11-02 20:49 UTC, question on clarification (d)) "What is the \"RegionBuffer\", actually?" Recorded as: a
  question; (d) still open.
- (2026-11-02 20:53 UTC, clarification (d): level 0 silent; the questions' blast radius) "Actually, many of the
  questions you asked in the past were unclear about the real blast radius. There must be a mode which is really silent
  on the console, ever. That's level 0. Nevertheless, the outputs of the modules shall be visible with higher levels so
  it does not become invisible. Is there such thing possible as - adding a Logger without error codes, just console or
  nothing? - passing through the upstream module's Logger (done in many other places)? - Something else you would
  suggest?" Recorded as: decided, level 0 prints nothing on the console, ever; at level 1 and above every module's
  output is visible, the four logger-less layers included. Open: the mechanism (asked). Standing: every question states
  its real blast radius (files, sites, bytes, tests, behaviour on the device).
- (2026-11-02 20:58 UTC, clarification (d) decided; a COBS question) "Agreed with this. But why is nothing using COBS?
  I assumed it being run on the UART crossover test module!" Recorded as: (d) decided as proposed (loggers passed
  through to the UDP socket, RegionBuffer, the UART bus driver and the COBS codec; `console()` and the below-level
  MemoryError branch go; level 0 prints nothing, ever). Open: why no device runs COBS (asked).
- (2026-11-02 21:01 UTC, a COBS mode on the crossover jumper) "Option 1, add the cobs mode in B6" Recorded as: B6's
  action list gains a `cobs` mode in the flash-tier crossover script (`tests_hardware/device_scripts/
  uart_crossover_exchange.py` and the host test choosing its modes), test-side only, OR123's pattern; it first runs on
  silicon in round 1. No firmware, build-chain or wire change.
- (2026-11-02 21:11 UTC, B2: two /status keys) "(a), remove both" Recorded as: `ResetBits` and `ConfigUnpersisted` go
  from `/status`, with their emitter lines, website rows, getters and tests; `ResetReason` and the internal
  unpersisted flag (the shutdown flush) stay.
- (2026-11-02 21:17 UTC, question on clarification (k)) "If I decide to keep code 4, can it ever be read by anyone?"
  Recorded as: a question; (k) still open.
- (2026-11-02 21:22 UTC, clarification (k) decided: reset code 4) "That actually never happened and is overkill code
  bloating the firmware. Remove code 4." Recorded as: the bootloader command writes no reset record; code 4 and its
  catalog row go (decision 6: no placeholder before the release); the bench test expects what the silicon reads (2);
  B2 takes the smallest form (less code, not a new branch where avoidable).
- (2026-11-02 21:25 UTC, clarification (h) decided: the wet bulb's corner) "(a), remove the corner" Recorded as: the
  cold-dry corner exclusion in `wet_bulb_temperature()` goes (its 4 constants, the check and its tests); the
  pre-audit range check (-20..50 degC, 5..99 %RH) stays.
- (2026-11-03, time not taken, before 05:52 UTC, question on clarification (d2)) "What is the decision you ask about?"
  Recorded as: a question; (d2) re-asked in full with its blast radius; still open.
- (2026-11-03, time not taken, between 05:52 and 06:00 UTC, the allocation-free log call) "Is the err nomem really the
  best way? Sounds like overkill complexity to me. Is there a simple way?" Recorded as: a question; answered with the
  plain `err()` form and its blast radius.
- (2026-11-03 06:00 UTC, the allocation-free log call decided) "Yes keep it simple" Recorded as: `err_nomem()` goes;
  its 14 calls in 9 modules use plain `err()`, as before the audit; a log line that cannot get its argument tuple on a
  full heap raises, and the restart and watchdog backstops take it. One lead change after B2's merge, before B4 and B5.
- (2026-11-03, time not taken, between 06:07 and 06:12 UTC, clarification (d2)) "Concerning the debug level log lines:
  how about option b and letting them store errors in fram? No prints but never lost, isn't it?" Recorded as: a
  proposal; answered with its form (an E20 entry written at the logger's setup) and its limits.
- (2026-11-03 06:12 UTC, clarification (d2) decided) "Pre construction error storage is overkill complexity, it opens a
  tree of recombinations (multiple errors, own error, etc.). Leave that." Recorded as: (d2) is (b): nothing changes;
  lines logged during construction stay silent on the board, no reader of the stored level before the build, no
  pre-setup storage. B8 carries no (d2) item.
- (2026-11-03, time not taken, between 06:13 and 06:17 UTC, budget) "We are at 9% usage now, is that within
  expectation?" Recorded as: a meter reading, 9 % of the week, with B2's falsification, gate and push still to run;
  the plan's running total through B2 is 10 % (R0 2, B1 4, B2 4).
- (2026-11-03 06:18 UTC, budget and pace) "Okay, keep rolling" Recorded as: the standing go-ahead (2026-11-02 20:42)
  holds after the budget reading; B2's close, the plain-err change and B4/B5 continue.
- (2026-11-03 06:41 UTC, the error log's slot rule (OR35.b's reading)) "Option a is more complex and could mess up
  appearance order. Keep as is. Generally target low complexity" Recorded as: the newest-entry rule stays (a repeat
  is compared with the newest slot only; alternating codes each take a slot); and a standing direction for every unit:
  target low complexity.
- (2026-11-03 06:45 UTC, NTP's unsynced retry (legacy every 10 s against the doubling to 600 s)) "Option a, keep it
  simple, but the resync trial timeout may be longer, something between 1 and 10 minutes. What would you suggest?"
  Recorded as: the doubling, its cap and their two device settings go (B5); one fixed retry interval between 1 and 10
  minutes, its value asked back with a suggestion.
- (2026-11-03 06:54 UTC, NTP's unsynced retry interval decided) "Understood the suggestion. Then let's actually take 1
  minute, easier to understand and not significantly more noise than 2." Recorded as: while unsynced, the first attempt
  at the first check with the network up, then one attempt every 60 s after a failed one (one tunable constant, no
  device setting); the doubling, its 600 s cap, `ntp_retry_s`/`ntp_retry_max_s`, their build check and the generator's
  pair go; a skipped attempt (no network) does not count; a settings change or forced resync tries at once. B5 item 19.
- (2026-11-03, time not taken, between 08:25 and 08:29 UTC, budget) "Currently about 13.5% usage. Still within
  expectation?" Recorded as: a meter reading, 13.5 % of the week, with B2 pushed (CI pending) and B4 and B5 running,
  neither handed back; the plan's running total through B5 is 16 % (R0 2, B1 4, B2 4, B4 3, B5 3).
- (2026-11-03, time not taken, between 09:01 and 09:59 UTC, open decisions) "are there decisions which are really mine
  and which i could take already now?" Recorded as: the owner asks for the open clarifications now rather than at
  each unit's start; (e) B3, (c) B6, (i) R2 and (j) D are put one by one, (e) first.
- (2026-11-03, time not taken, between 10:00 and 10:16 UTC, (e) FRAM's E and W for one invalid block) "Option A.
  Both my statements hold. Either it's a warning or a fault applies to the same level / the same module, which should
  be clear about what it is. If there is a downstream fault, it's a fault on that level. If that propagates up, is
  handled and degraded to a warning, that's a valuable traceback. Therefore, both of my criteria are met with it."
  Recorded as: (e) decided, the pair stays as it is (no change in B3); the reading of "never both" is per level or
  module: a downstream fault is an error at its level, and the level above that handles it and degrades it logs a
  warning, which is the traceback the 2026-10-01 note asks for.
- (2026-11-03, time not taken, between 10:17 and 10:26 UTC, (c) a UART exchange during a flash write) "Option A, keep
  as is. Would a longer UART timeout, e.g. 3000ms, relieve things further?" Recorded as: (c) decided, no change in B6;
  the timeout question is answered with facts (the timeout is a fixed protocol parameter, owner 2026-09-11).
- (2026-11-03, time not taken, between 10:27 and 10:31 UTC, the UART timeout) "Keep the UART as is. Any module using
  the UART must be aware that errors like this can happen due to various reasons anyway and provide recovery mechanisms
  themselves. This is nothing new, only something to be aware of." Recorded as: the 1,000 ms timeout stays; a failed
  exchange is a normal event the link's users recover from themselves; no change and no new mechanism.
- (2026-11-03, time not taken, between 10:38 and 10:45 UTC, (i) the two decision-records checks) "Option A, this is
  valuable for future sessions as well" Recorded as: (i) decided, `test_decision_vocabulary.py` and
  `test_citations.py` stay as permanent repo rules with their shrinking allow-lists; R2 keeps them in full.
- (2026-11-03, time not taken, between 10:46 and 10:50 UTC, (j) the Stull paper) "Option A. I wonder where this was
  unclear, we decided that all docs are moved to the private repo." Recorded as: (j) was already decided (OR80.a:
  `datasheets/` is the private submodule for reference material, history kept); the plan wrongly made the push into a
  question. The paper moves to `hundertvolt/datasheets` and leaves this repo's tree before PR #107 merges.

- (2026-11-03, time not taken, between 11:47 and 11:49 UTC, budget) "A bit above 17% usage at this moment. Still within
  expectation?" Answered: yes, inside the 17-18 % given for B4 and B5; the whole job's 55 % estimate stands.
- (2026-11-03, time not taken, between 11:50 and 12:13 UTC, go-ahead) "Okay, keep rolling. Can you already prepare
  something while the background shell is running?" Recorded as: the next units' drafting starts beside the gate.

- 2026-11-03 15:17 UTC (time taken at reading), budget: "we are at 21% usage now. still inside expectation?" Answered: yes; the storage and UART pair, a bit past half done, should close near 23-24 %; the 55 % estimate for the whole job stands.
- 2026-11-03 19:01 UTC (time taken at reading), budget: "24% usage still within expectation?" Answered: a little over;
  the storage and UART pair closes near 25 % once its gate, snapshot and CI are done, about a point above the 23-24 %
  given at 15:17; the 55 % estimate for the whole job holds, with less slack.
- 2026-11-03 20:05 UTC (time taken at reading), B7/B8 owner questions: "Prepare these 5 questions and the one before
  that we can go through them one by one" Done: the B7 `State` question and B8's five queued questions prepared
  together, then asked one at a time.
- 2026-11-03 20:25 UTC (time taken at reading), B7 question 1 (`State`): "The entries in the status field could be
  anything as you describe them, what are they about?" Answered: what the notification service checks each cycle and
  what each code means in those terms; question 1 stays open.
- 2026-11-03 20:28 UTC (time taken at reading), B7 question 1 (`State`): "Now I understand why the whole notification
  status field was new to me - I never requested it. Did I actually ever request any status of the notification being
  added to the status field? Honestly I don't remember ever discussing this." Answered from the records (below).
- 2026-11-03 20:35 UTC (time taken at reading), B7 question 1 (the notification block in `/status`): "As you said that
  code functionality can be tested without all that, we do as recommended, only keep pause time" Decided: `Triggered`,
  `State` and `TS` leave `/status` with the Status page's "Notification Status" group, the NotifyState table and the
  mock data; `PauseTime` stays where it is; tests observe a flash through the LED fake's frames. Relayed to B7.
- 2026-11-03 20:40 UTC (time taken at reading), B8 question 2 (the boot entry at DebugLevel 0): "drop the traceback
  print and keep the start line, as you recommended" Decided: the generated main.py's `sys.print_exception(ended)` goes
  (reset reason 22 stays the record, with its pre-bind, comment and F811 exemption); the no-autostart start line stays.
- 2026-11-03 20:43 UTC (time taken at reading), B8 question 3 (the page's build-date stamp): "Remove it" Decided: the
  meta stamp, its read and compare in the page code and its build steps go; `BuildDate` stays in GET /system.
- 2026-11-03 20:45 UTC (time taken at reading), B8 question 4 (the "returned no JSON object" banner): "Yes, restore"
  Decided: the page's GET check goes back to the pre-audit form (an empty body refused, a typing cast otherwise).
- 2026-11-03 20:47 UTC (time taken at reading), B8 question 5 (a saturated counter shown as "65535+"): "Yes, that was a
  good addition, keep it" Decided: kept, now with the owner's agreement on record.
