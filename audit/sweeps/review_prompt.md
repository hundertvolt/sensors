# Owner review package: content brief

The plan is complete: 1,883 merged changes (`audit/consolidation/M_*.md`), a step-level work order
(`audit/order/WORK_ORDER.md`), and the register (`audit/pass2/`). Before execution starts, the owner reviews the whole plan
**alone** and gives the go-ahead. This pass gathers the content for that review. The lead builds the page from it.

## The owner's own words (OR135, LEAD/R35)

"When you are in the stage of preparing my review, be aware that I will do that review alone. So keep it at a level where I
won't need to ask for details for every topic, but at the same time not overwhelming, not exhausting, human-oriented and
friendly, so it will be a rewarding task for me."

So:
- Plain language. Name things by what the owner knows: the sensor, the website, the dev bench, the test suite. No audit
  IDs, change IDs or file:line references in the readable text. Put those in a separate `refs` field.
- Each item says what it is, why, what it means for the owner, and what happens if they say no.
- The owner knows the project well. Don't explain basics, but don't assume they have read any audit file.
- Be accurate. Every statement must trace to a merged change, an AC_NOTES item, a register requirement or an OR row. Read
  the source before writing about it. Accuracy before speed.
- Use they/them for the owner. Write in English.

Never read `arduino/`, never edit any file outside `audit/review/`, no git commits, never run anything against real
hardware.

## Part T: topics and overview (one agent) → `audit/review/topics.json`

```json
{
  "overview": {
    "one_line": "…",
    "numbers": [{"label": "…", "value": "…", "note": "…"}],
    "what_you_are_asked": ["…"],
    "timeline": "…"
  },
  "topics": [{
    "id": "short-slug",
    "title": "…",
    "summary": "2-3 sentences: what changes in this area and why",
    "highlights": [{"title": "…", "text": "1-2 sentences", "user_visible": true, "refs": ["M.X.nnn", "…"]}],
    "unchanged": "1 sentence on what deliberately stays as it is (optional)",
    "size": {"changes": 0, "units": "U…-U…"},
    "refs": ["audit/consolidation/M_….md"]
  }]
}
```

- Aim for 8-12 topics a person thinks in: for example the sensors and drivers, the network and REST API, the website,
  system and memory safety, the device configuration and the build generator, the tests, the digital twin, the hardware
  tests and the bench, the build chain and CI, and the documentation. Choose the split from the material.
- 4-8 highlights per topic: the changes the owner would most want to know about (behaviour they will notice, a new
  command, something removed, a risk closed). Not a change list.
- The overview: the scale (changes, units, steps), the work order's shape (the unit sequence in a sentence or two), the
  execution estimate (about 5-8 working days with the OR134 test scheduling; it is an estimate, say so), and the three
  hardware sessions.

## Part D: decisions and owner steps (one agent) → `audit/review/decisions.json`

```json
{
  "owner_steps": [{"id": "…", "title": "…", "what": "…", "why": "…", "when": "before unit … / phase C", "refs": ["…"]}],
  "hardware_sessions": [{"id": "…", "title": "…", "rounds": "…", "what_happens": "…", "owner_present": "…",
                          "duration": "…", "wear_or_risk": "…", "refs": ["…"]}],
  "decisions": [{
    "id": "short-slug",
    "weight": "significant | moderate | routine",
    "topic": "a Part T topic slug",
    "title": "…",
    "decision": "what was decided on the owner's behalf, 1-2 sentences",
    "why": "1-2 sentences, grounded",
    "if_no": "what the owner's no would change, 1 sentence",
    "alternative": "the realistic other option (optional)",
    "refs": ["…"]
  }],
  "parked": [{"id": "…", "title": "…", "why_parked": "…", "refs": ["…"]}]
}
```

- **Decisions**: every decision the planning took on the owner's behalf under OR2.c that the owner has not yet seen.
  Sources: items marked as agent proposals or "for the OR2.c review" in `audit/actions/AC_NOTES.md`,
  `PROJECT_AUDIT_PLAN.md` 3.2 (e.g. OR119.a (5), OR121.a's confirmation-step proposal) and the register; the D-T1-D-T34,
  TOOL D1-D16, AD-nn and G3-n decision lists (search `audit/consolidation/`, `audit/actions/`); the release version 2.0;
  and "Resolved" slots in M files that choose between options without an owner row. Owner decisions already recorded as OR
  rows are not decisions to review. The roughly 75 engineering-local "(agent, date)" labels OR71.a (0) already accepted are
  not reviewed again, unless a merged change alters one.
- **Weight**: "significant" changes something the owner or a user would notice (behaviour, API, the website, the release,
  wear, scope). "moderate" is a design choice inside the code with a plausible alternative. "routine" is a mechanical or
  conventional choice that the owner can approve in one batch. Expect few significant items, more moderate ones and many
  routine ones. Merge duplicates.
- **Owner steps**: what only the owner can do (e.g. push access to `hundertvolt/datasheets` before U28, AC_NOTES 37), from
  AC_NOTES, WORK_ORDER.md "owner items" and the M files.
- **Hardware sessions**: the three sessions in WORK_ORDER.md.
- **Parked**: anything OR2.c parks for the owner (it needs real hardware, or it lies beyond the agreed scope).

A register applier is still editing `audit/pass2/`, `M_SPEC.md` and `M_SCR.md` while you start. Read those last, and
re-check any item you take from them at the end.

Hand back the counts (per weight, steps, sessions, parked) and anything you could not ground.
