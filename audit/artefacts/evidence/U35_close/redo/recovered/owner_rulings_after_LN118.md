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
