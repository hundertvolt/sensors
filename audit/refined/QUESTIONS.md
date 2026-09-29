# Refined harvest — owner questions

Audit working file (temporary). The 25 question candidates of the integration ledgers (`I1.md`-`I7.md`)
merged into 20 top-level decisions (lead, 2026-09-28); recommendation first. Each names its findings.

## A. Who decided (provenance)

1. **Five recorded decisions: were they yours?** (RF005, RF037, RF001, RF029, RF043)
   (a) tier-parity sweep "HIGH PRIORITY (project owner, 2026-09-15)" — no owner words in `ea32767`/`278cf60` → relabel agent;
   (b) chain-completeness rule (every module joins the twin) — tag "(owner, 2026-08-20)" in `00eb44d` → keep owner;
   (c) CRC-16 swap at UART promotion — deliberate per `7f4ebc3`, no owner words → agent, and "Not a deliberate change" goes;
   (d) FRAM differing copies are a hard failure — "(owner-confirmed)" in `69d85b7`, dropped later → restore owner;
   (e) `chunk_bytes` one parameter for both bounds — no owner source → agent.
   Answer per letter: yes (yours) / no (agent). Recommendation: a no, b yes, c no, d yes, e no.
   **Answered (OR87, 2026-09-29):** a owner (importance, not ordering), b owner, d owner; c and e: owner asked for an explanation. **Answered (OR88):** c result owner-confirmed, swap labelled agent; e owner.

## B. What your words cover

2. **OpenHAB load case: 2 + 2 = 4, or full ceiling?** (RF027) (a) your case only → 4 connections, below today's 6; (b) the widened "tabs fill any ceiling" → stronger, but not yours; (c) both, each labelled with its decider (recommended).
3. **"No twin32" — also the 64-bit frozen twin?** (RF028) (a) yes, both frozen twins are ad-hoc (recommended); (b) only 32-bit → the 64-bit twin reopens as a decision.
4. **Restore "adopt a non-blocking alternative once one exists"?** (RF012, `cc911be`, 2026-07-24, lost in a merge) (a) yes, one BACKLOG deferred goal for every blocking call (recommended); (b) no → blocking calls stay watchdog-backstopped, no forward goal.

## C. Device behaviour

5. **Dead declared FRAM chip: contain or escalate?** (RF153) (a) contain with a stated OR18.a exception, the manager stops touching the chip → runs forever without persisted logs; (b) escalate like any chip → a truly dead chip reboots the unit repeatedly; (c) escalate once per power-up, then contain (recommended).
6. **SCD30 PUT when its read-back fails?** (RF347) (a) refuse the whole PUT, as legacy did → no NVM write without a compare (recommended); (b) write every valid field (today) → spends NVM writes blind; (c) send only the always-sent commands.
7. **SCD30 bus-hazard fixture write: gated or prerequisite?** (RF306) (a) stays gated → seven flash bus-hazard tests never run by default; (b) prerequisite → one NVM write per session; (c) read first, write only if the mode is off (recommended).
8. **Unused UART protocol API: keep or remove?** (RF236) (a) keep as general-purpose API with contract tests (recommended); (b) remove → leaner image; (c) keep only what the C peer needs.
9. **`gc.collect()` inside tests as pause injector?** (RF196) (a) forbid, rebuild the three sites without it (recommended); (b) a named test-only exception in the site check.
10. **Ignore lines whose writer is outside the repo?** (RF321, RF322) (a) keep `config.json` and `.claude/worktrees/` with their writer named (recommended) → no credential or nested checkout can be staged; (b) remove both; (c) keep only `config.json`.

## D. What the operator sees

11. **Clear typed inputs after Apply, as legacy did?** (RF346) (a) clear all → nothing re-sent; (b) clear accepted ones, keep rejected ones for correction (recommended); (c) keep (today) → a second Apply re-sends `ForceCalRef`, `AmbPres`, `SystemCmd`.
12. **Restore "Apply & Reconnect" / "Apply & Resync" labels?** (RF348) (a) yes (recommended); (b) warning text instead; (c) as is → Apply drops Wi-Fi unannounced.
13. **Failed read: publish `None` or last sample?** (RF343, RF333) (a) `None` everywhere, as ISL29125 → one semantics, API change for three drivers; (b) last sample everywhere, page shows its age (recommended by I4); (c) keep both. The two ledgers recommend differently (I7: a, I4: b); lead: (b) with ages shown — no value lost, staleness visible.
14. **Readable text for codes on the website?** (RF151, RF340) (a) numbers only (today); (b) labels for published status codes (`reset_reason`, …) and error numbers from a table generated from the catalog at build time, `/status` unchanged (recommended); (c) `/status` itself carries text → RAM and size cost.
15. **Current Unix time back in `/status`?** (RF344) (a) add an epoch field → legacy value back (recommended); (b) render timestamps as dates only; (c) accept the loss.
16. **SGP40 backup/restore sentinels `-1`/`0`: how shown?** (RF345) (a) legacy meanings on the wire; (b) keep values, define them in SPEC and the `@web` tag, the page shows text (recommended); (c) as is.
17. **Publish the SGP40 VOC learning state?** (RF334) (a) yes, a numeric code in LEAD/R19's form with a page label (recommended); (b) docs only.
18. **SCD30 forced-calibration readiness in `/measurements`?** (RF335) (a) help text only; (b) a readiness code like ISL29125's (recommended); (c) refuse `ForceCalRef` until ready.
19. **Show terminal Wi-Fi deactivation on the status LED?** (RF336) (a) plain off (today) → looks like "connecting"; (b) a distinct pattern, honouring `LedWifiOn` (recommended); (c) NeoPixel only.
20. **SCD30 Altitude help: restore "turn off continuous measurement"?** (RF349) (a) restore; (b) drop; (c) measure in the hardware round, (b) until then (recommended).
