# The big picture, refined from the owner's decisions

Written by the lead, 2026-10-28 08:46 UTC; the owner's answers added 09:05 UTC (section 7).

The owner asked (2026-10-28): "Every decision and request I take is a puzzle piece of the big project picture and
should fit. If it doesn't fit, we need to clarify. This is part of the audit pillars, you can check that. So refine
your general picture from what we learned and decided together throughout the audit."

**Sources.** Every owner row in the plan (308 rows, OR1-OR150, the owner's words extracted), the owner rulings after
LEAD NOTES 118, the 24 notes on the review page, the owner's statements in this conversation, and the scan and drift
analysis (`scan/REPORT.md`, `scan/DRIFT.md`).

## 0. The rule this follows, and how the audit missed it

The rule is written down, from the planning phase on:
- **OR44 (2026-09-26):** "Every requirement, every decision, every coding pattern can be seen as samples of a larger
  concept, each has a specific value, but also a general one. The general concept must be coherent and sound seen
  from all perspectives."
- **OR3 (2026-09-25):** "In case you find topics I mentioned or findings of you might potentially be contradictory,
  they surely are not. Such cases always mean that there is a topic to be fine tuned - a reason to ask and clarify".
- **OR7 (2026-09-25):** "keep the big picture in mind and check how it all fits together ... It is of major importance
  that the final result is 100% coherent and clean."
- **The process requirements** (`audit/CONSOLIDATION.md` section 1): "an audit that runs uninterrupted, decides
  conservatively, proves instead of assuming, and leaves nothing open."

**How the audit missed it.**
- Each piece was applied by its *specific* value only.
- The expanding pieces (check everything, 100 % of error paths, biting tests everywhere) became gates.
- The restraining pieces were each applied to their one item, and their *general* value was never drawn:
  - "overkill", "a hypothetical client", "Very hypothetical test", "lean, clean, efficient, minimal";
  - "if required at all";
  - "Pure and simple", "no need for such complexity here", "Don't change too much".
- The two groups looked contradictory, and OR3 says that means a topic to fine-tune and ask about. That question was
  never asked.

## 1. The concept (owner, OR44, unchanged)

"a device which can run indefinitely long without any user interaction once configured, handles all issues inside, and
although barely reachable has multiple fallback layers, has premium quality code, has all its main cases all the way
through rare corner cases tested, and runs efficiently and compact on a low end hardware device"

The pillars P1-P12 stand as they are. What follows is how the owner's pieces fill them in, and the general value each
group of pieces carries.

## 2. The lines the pieces draw

### L1. Look at everything; change only what is needed, minimally

**What the owner asked for:**
- **The analysis is complete.** "check EVERYTHING file by file" (OR46); "Trace all execution paths" (OR16); "a scan ...
  all places" (OR147).
- **The change is small.**
  - OR1: "consolidation, harmonization, and perfection as far as possible", of a prototype already "complete, stable,
    working".
  - OR12: refactors "fine in general if really required".
  - OR36: "lean, clean, efficient, minimal".
  - OR149: "the fixes required for such reliability (if required at all, if not already safe inherently) are minimal,
    low complexity. It's more about having such situation in mind and giving the code a simple inherent way of
    handling it."
  - 2026-10-22: "Don't change too much, keep going." 2026-10-23: "So target minimal changes."
  - 2026-10-28: "really minimal change", "in the dimension of a few lines per module".

**General value:** completeness belongs to the looking, understanding and recording; minimality belongs to the
change. Both hold at once, and they never compete.

### L2. Real, not hypothetical; but cheap bounds by principle are wanted

**Against building on hypotheses:**
- The pre-audit SPECIFICATION.md F.2: a theoretical MemoryError is "only worth closing for a concrete,
  non-hypothetical threat".
- OR26.a: graceful degradation "on expectable memory errors".
- OR72: "Very hypothetical test", "It seems to be unreachable by definition".
- OR33.a: a test that "can only fail / can never fail ... If it remains unreasonable or unrealistic, drop."
- 2026-10-26, on a rare case: "B is fine, very rare edge case".
- 2026-10-27, on unnecessary checks: "fully covered by typing adherence alone, and ... unreachable with today's code".
- 2026-10-28: "building upon hypothetical findings is a clear no-go", and "Hypothetical findings which are suspicious
  to be real need to be verified".

**For cheap structural bounds, even for improbable cases:**
- OR103, the counters: "Extremely improbable to ever be reached, but anyhow safely confined - ... nothing bad except a
  wrong number happens".
- OR99: "A counter which counts up ... and then stops is okay (probably even the best ... bounded by principle)".
- OR110, the memory rule: forbidden are objects that "reside in the heap forever ... and which can grow"; "If a timer
  allocates, never reaches any critical value and frees some seconds later, it's less critical".

**General value:** a bound that costs nothing and is part of the design (a capped counter, no growing long-lived
allocation) is wanted even for improbable cases. A *mechanism* for a trigger nobody observed is not wanted:
- a task, a timer, a flag, a fallback or a retry;
- a timed check ("hardcoded delay checks like this are a very bad, very awkward pattern", 2026-10-28).

A suspicious hypothesis is verified first. If it is confirmed, the fix is the minimal one from L1.

### L3. Handle it inside, simply and at the right layer; escalate rather than contain

**The owner's pieces:**
- **P2/P3.**
- **OR18:** NTP stalling its task "instead of handling it internally" was the bad pattern.
- **OR18.a:** "a stalled chip may recover by a reboot, keeping it contained going so far may miss that opportunity".
- **OR31.a:** tasks "either really work or return / end in any other case which cannot be handled internally (internal
  handling is absolutely preferred, anyhow)".
- **OR113:** "recover mildly, but escalating up to a full bus reset is absolutely allowed ... Apply this idea
  throughout!"
- **OR119:** "shut all down controlled, erase, reboot - probably this is the most elegant solution anyway".
- **CLAUDE.md:** the watchdog is the accepted backstop for a wedged I2C bus and for the Wi-Fi false positive.
- **OR35.a, the log rule:** "rather simple and lean"; "Protection against alternating codes and layered limits are
  overkill on such limited device".
- **OR35.b:** "No distinction ... just don't repeat the same error in the slots. Pure and simple."
- **The review note on one-entry-per-fault:** "It should rather stay as is, upstream layers reacting to a downstream
  fault may encounter following errors ... getting a notion of a traceback and blast radius of an error is actually
  desirable."

**General value:** one simple mechanism, at the layer that owns the fault.
- Beyond that layer, the existing ladder carries it: the task ends, the supervisor restarts it, the unit reboots, and
  the watchdog is the last step.
- The ladder itself is part of the design. Containment code beyond it is not.
- Smallest blast radius applies to the code as well: one mechanism in the shared base, not a copy per driver.

### L4. Prove what matters, efficiently

**The owner's pieces:**
- **Tests must bite:** P5; OR19/OR21 "biting tests".
- **But the control arms are "overkill"** (OR21.a).
- **Fault planting only where it adds something** (2026-10-23): "Planting faults is a good measure for complex
  measurement tests ... but not required for the straightforward tests (which I would assume to be the majority by
  far). Planting errors for those straightforward tests would be complete overkill."
- **The suite should get faster.** OR39: "Look for opportunities for speeding up the test suite". Also: "Test duration
  going up like this is anyhow something to fix - not cutting back strictness, but making it more efficient", and
  "significantly less effort for same quality".
- **Effort must pay off.** OR77: only "if the effort of this is reasonable and if we can cover test cases we cannot
  cover under any of the other tests".
- **Test code stays out of the twin and the rigs.** OR20: "Only if there is no alternative, and keep tiny anyway".
- **Tiered effort** (2026-10-28): "The unit tests shall have good quality, but don't need deep dives. The audit
  verification machinery is just a temporary tool."

**General value:** test real behaviour, at the tier that can reach it, with the least machinery. Effort is tiered:
- the firmware and buildgen get depth;
- the tests get good quality;
- the machinery stays small and temporary.

### L5. One material, one source, extensible, modules as libraries

**The owner's pieces:**
- **One material and one shape.** OR24: "one material"; OR46.b: "one shape for one job"; OR84: setups through one
  `sysfunct` list, "the same way as the task starters and the timer starters".
- **No board-specific code outside its TOML.** OR78: "nothing about the WoZi and Dev build shall remain hardcoded at any
  place". OR43.a: "it may become more than six devices in the future".
- **A pattern that produces fitting code on the first try.** OR10: "a full integration of a new sensor starting with
  just a datasheet". OR44.a: a pattern and checklist that "will produce 100% fitting code on the first try".
- **Modules are libraries.** 2026-10-23: "Always regard the modules as libraries, not every feature must be
  immediately used, as long as it is a real feature". On the review page, the humidity helpers stay: "useful, complete
  the functional suite, small, lightweight".

**General value:** every module follows one small, repeatable pattern, so that a new sensor fits on the first try.
Extra machinery in a module is a cost carried by every future module. Unused but real features are fine; unused
protective machinery is not.

### L6. The device's own resources: least wear, compact, no growth, no special first boot

**The owner's pieces:**
- **Least wear and write rules.** P6, P9. OR42: write only on change. OR70.3: "never write without user / api
  interaction as a standing rule". OR49.a: "FRAM writes do not count as wear".
- **FRAM consistency within one build only.** OR47.a: "fingerprinting on the fram is a waste of space. there is no
  requirement for the fram to stay consistent through firmware re-flashes. it only must be rock solid within one
  individual firmware build."
- **No special first boot.** 2026-10-23: "No behavioral difference at all should arise from a fresh flash or a first
  boot. If things happen at first boot, they must be triggered by evidence (e.g. no config available, FRAM image does
  no longer fit the layout)."
- **Nothing for tests in the product.** OR36: "zero artifacts specifically added for testing".

**General value:** the image, the heap and the stores are budgets, and every addition is paid from them.
- Flash is measured against the baseline.
- Nothing in the product exists for the tests.
- Behaviour follows from evidence, never from "this is the first boot".

### L7. Decisions are the owner's, recorded truthfully, asked briefly

**The owner's pieces:**
- **When questions are asked.** OR2/OR2.a/OR2.b: questions go to the recording and the consolidation run, so that
  execution can run uninterrupted. OR2.c: unforeseen decisions take the conservative, reversible option and are
  logged.
- **Contradictions are questions.** OR3.
- **The owner's decisions, not the agent's.** OR48.a: "recorded decisions I took (not the session agent)". OR56: "I
  never required that, I even objected several times against it!" OR62: "I never decided that. Check if you can
  identify the mechanism how that sneaked into the docs". OR13: "false decisions were written down ... and were
  lateron strictly obeyed".
- **How questions are asked.** OR51: "many questions are asked way too verbose". 2026-10-26: no multiple choice for
  complex topics, one at a time. "You are way too fast": wait for the answer.

**General value:**
- Only the owner's own words are decisions.
- Text written by the agent stays a labelled proposal until the owner adopts it, however it is formatted (a rule, a
  register row, a review item).
- "Conservative" means the smallest and most reversible change, which for solid code is usually none.
- An apparent conflict between pieces goes to the owner as one short question.

### L8. The way of working

**The owner's pieces:**
- **Accuracy first, without overdoing parallelism.** OR107: "prefer accuracy before speed. Parallelization is
  generally allowed, but don't overdo it it, the resulting syncing effort should stay reasonable".
- **Test scheduling.** OR134: savvy test scheduling to save wall clock "without touching quality or raising token
  usage".
- **Budget.** 2026-10-27: "same quality, same result, no major slowdown, but less budget usage. Remove unnecessary
  hogs".
- **Root causes, and no lost evidence.** "root cause any faults", and "I just want to make sure no evidence to a bug,
  be it in the firmware or the tests, is silently lost".
- **External issues.** "Don't care about proven external issues so far."
- **Upstream findings.** Report them "later and bundled, if at all".
- **Push intermediate results.** "I don't want to lose anything again."

**General value:** effort goes where it changes the product's quality.
- Proven external noise is noted and left alone.
- Parallel work is limited by what can be reviewed.

## 3. The picture in one paragraph

Look at everything, trace every path and record what is known. Then change the product only where a verified gap
exists or the owner decided, in the smallest form that fits the existing design and its one shared pattern.
- **What can grow:** bound it by construction, at no cost.
- **Everything else:** leave it to the existing ladder (local handling, task end, supervisor, reboot, watchdog), not
  to new machinery.
- **Tests:** test real behaviour where a test has power, efficiently. Keep the verification machinery small and
  temporary.
- **The device's budgets:** keep flash, heap and the stores within them.
- **Decisions:** treat only the owner's words as decisions, and ask one short question whenever two pieces seem to
  collide.

## 4. Where the audit's results do not fit the picture

These are facts for the cleanup, not new work. Each names the pieces it collides with.

**M1. The F.2 rule against hypothetical MemoryError handling was deleted.**
- What happened: SPECIFICATION.md F.2's "only worth closing for a concrete, non-hypothetical threat" was removed in
  the U0 doc pass (`195f3ed3`, 2026-10-06). The agent's reading was that OR26.a replaced it ("the criterion is whether a
  real graceful-degradation alternative exists, not whether the threat is 'concrete, non-hypothetical'").
- Why it does not fit: the owner's words say "expectable memory errors", which fits the old rule (L2). The deletion
  was never asked (OR3, OR13).
- Consequence: a project safeguard against hypotheticals was gone from day one of execution. It fits every later
  ruling, so it belongs back.

**M2. Hardcoded timed checks.** The NeoPixel 300 s rewrite, the LED queue's 120 s deadline, the two 10,800 s sample-age
checks, the 1,200 ms escalation wait, and the webserver's three retries 5 s apart (L1, L2, L3).

**M3. Per-episode log flags.** They stop the console line on repeats (OR35.a "Console logs actually should keep
printing all"; OR35.b "No distinction ... Pure and simple").

**M4. Typing-only guards and exact-type getters.** They break the owner's earlier rule on checks that typing alone
already covers (2026-10-27: "I once decided ... catching errors which can only happen for the reason of unfulfilled
typing are overkill").

**M5. The recovery ladder's cascade.**
- What fits: the ladder itself (OR113).
- What does not: the "bus not initialized" contract copied into four drivers (26 raise sites), against L3 (one
  mechanism, in the base) and L5 (one shape).

**M6. Product console lines for the test tiers' memory gates.** They put test needs into the product (OR36 "zero
artifacts specifically added for testing"; P4).

**M7. Allocation cuts for short-lived temporaries.** OR110 named such temporaries "less critical".

**M8. Test-machinery scale.**
- Fault planting campaigns go beyond the 2026-10-23 ruling ("I never required to plant faults for every test").
- The twin's harness growth goes beyond OR20's "keep tiny anyway".
- CI went from 45 to 175 minutes, against OR39's "speeding up".
- The audit records go beyond OR48.a's "make sure everything is found, but no list or permanent record" (for the
  legacy-parity scan).

**M9. Parallelism.** Up to 15 lanes per unit, and 94 hand-backs in the redo, against OR107's "don't overdo it".

**M10. Agent text treated as decisions.**
- 125 agent-written requirements bound execution.
- 708 decisions were taken on the owner's behalf, with no review yet.
- Review-page ticks: answered, they stand as the owner's decisions (section 7).

**M11. The factory-state Wi-Fi unit. Withdrawn.** I had read OR151 ("If the SSID stored in the config never appears,
everything stays silent"; "Entering the hotspot mode only through a reboot, as is.") against the code, which returns an
unconfigured unit to the hotspot after every window, and taken that for an agent decision. The owner decided the
Wi-Fi behaviour in full during the audit (section 7); it fits, and it is not re-asked.

**M12. FRAM chunks seeded per owner. Withdrawn:** the owner keeps the seed (section 7). The question was:
- What it does: it makes a chunk written by another module read as blank after a reflash shifted the layout. It
  costs no bytes, but `owner=` is now on every chunk request.
- Why it may not fit: it sits between OR47.a ("no requirement for the fram to stay consistent through firmware
  re-flashes", "fingerprinting ... waste of space") and the 2026-10-23 ruling, which names "FRAM image does no longer
  fit the layout" as evidence that may trigger first-boot action.

**M13. Website look changes beyond what the owner asked for. Withdrawn (second pass, 2026-10-28).** I had listed
the code tones, the drawer and the section-switch wait as changes nobody asked for (OR94: "don't change the current
look of the website"). All three trace to the owner:
- the tones are the CalLight "fixed tone table" of review item `website-display-details` ("Fine, and ...");
- the inert closed drawer is in review item `website-accessibility` ("Fine, and ...");
- the section-switch wait keeps the owner-decided dropped-connection trace (OR102.a (9), OR137) free of navigation
  noise (commit 9bf22747); it stays, possibly in a smaller form.
The owner also asked for the contrast fix (OR132 "2a"), the Back history, the decimals and the confirmation dialogs.

## 5. Corrections to my earlier reports from this pass

- **The website features I listed as unagreed are mostly the owner's own requests.**
  - The Back history: review note, "make the "back" function of the browser work".
  - The per-value decimals: review note.
  - `UnixTime`: OR94's answer "15 a".
  - The auto-reload: the review page's "ok".

  Only small items remain unrequested (M13).
- **The FRAM layout-shift fix stays a real gap.** The scan report counted it among the 17 confirmed gaps; the owner
  kept the fix (section 7).
- **The contrast fix fits.** It is OR132's "2a".

## 6. What needed clarifying (all three answered, section 7)

These were the pieces that did not fit together, or whose fit I could not settle from the record.

1. **The review page.** Do the 45 "ok" ticks on the agent-written review page count as decisions the owner "really
   took", or only the pieces in the owner's own words? The C-stack reboot (about 120 call sites) is the largest one
   that hangs on this.
2. **The factory-state Wi-Fi unit (M11):** OR151's silent mode with hotspot only through a reboot, or back to the
   hotspot after every window?
3. **FRAM chunks seeded per owner (M12):** does it fit OR47.a, or is it the fingerprinting OR47.a calls a waste?

Not questions, because they follow from the pieces directly and are marked for the cleanup:
- restoring F.2's sentence (M1);
- removing timed checks, per-episode log flags, typing guards, test-only console lines and cascade copies (M2-M7),
  unless a verified gap needs part of one.

## 7. Answers (owner, 2026-10-28)

- 1, the review page: "The OK in the review stay valid." Every "ok" on the review page stands as an owner decision,
  the C-stack reboot included. How the cleanup treats them: section 8.
- 2, Wi-Fi: "WiFi stays valid." Read by the lead as: the behaviour as built stays; a unit with no network configured
  returns to its hotspot after every window, and OR151's silent mode applies to a configured unit whose network is
  absent. So M11 fits and is withdrawn.
- Wi-Fi, added: "We thoroughly discussed the WiFi issues and I decided everything already." Settled; not to be
  re-asked.
- 3, the FRAM owner seed: "The FRAM idea of yours is good, keep it!" It stays (owner, 2026-10-28); M12 is withdrawn,
  and the layout-shift fix stays on the list of real gaps.

## 8. How the cleanup treats findings and decisions (owner, 2026-10-28)

"now note as background: a verified finding or a taken decision stand for their own and are worth keeping at least
documented. When cleaning the firmware and the buildgen, some of them may become obsolete, e.g. when removing cascades
and issues these cascades themselves introduced and are overkill or runaway. They have no more direct meaning to the
project anymore, but still are worth to know about in general. Others, which stay in scope, stay valid and effective
as they are, but ideally are resolvable with way more minimal code. Rare but real conditions which drop out through
the cleanup no longer matter. Rare but real conditions staying in scope still shall be addressed - no regressions, but
more efficiency."

Read by the lead as three rules:
- **Everything is kept documented.** Every verified finding and every decision the owner took stands for its own and
  stays in the records, whatever the cleanup does to the code.
- **Obsolete with what it was about.** A finding or decision tied to a cascade or runaway mechanism the cleanup
  removes, including the issues such a mechanism itself introduced, loses its direct meaning for the project. It stays
  documented as general knowledge. A rare but real condition that drops out with the cleanup no longer matters.
- **In scope: valid and effective, in far less code.** A finding or decision that stays in scope keeps its full effect,
  ideally in much more minimal code. A rare but real condition that stays in scope is still addressed: no regression,
  more efficiency.
