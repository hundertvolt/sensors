# Routine decisions: settle, combine, or keep (owner method, 2026-10-02)

The owner answered every significant and moderate decision on the review page (`audit/review/answers.json`; read their
notes, several set new rules). The 296 "routine" decisions in `audit/review/decisions.json` are too many, too low-level
and too hard to understand out of context. The owner will not approve them in a batch: that would record them as
deliberate owner decisions they never saw. Their words:

> "Carefully boil it down to the barely necessary ones. Check if they can be already answered by: our rules and pillars;
> our project style at other, similar occasions; documentation and datasheets; best practice; similarities (same issue at
> different places); web search (repos, forums, etc); net effects - if none of the above ways holds, what actually does it
> change? If it's nothing, then it simply does not matter. ... For what is still left then, there is quite some
> probability of being similar or linked issues which can be combined to a higher level decision or a missing rule to be
> set up. ... I would expect at max 30 questions remaining, probably even way less."

## Method, applied to every item in your share, in this order

1. **Rules and pillars.** An owner row (`PROJECT_AUDIT_PLAN.md` 3.2, OR1-OR139 with their .a readings; the most recent
   wins), a CLAUDE.md rule, an owner-ranked register requirement (`audit/pass2/`), the pillars (OR44.a) or an owner answer
   in `answers.json` decides it.
2. **Project style.** The project already made the same kind of choice elsewhere; name where.
3. **Documentation and datasheets.** SPECIFICATION.md, the MicroPython/Microdot docs or source (a v1.29.0 checkout is at
   `/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/mp`), `datasheets/`.
4. **Best practice**, including a web search of repos, docs and forums where it settles the point.
5. **Similarity.** The same issue appears at several places; one answer covers all.
6. **Net effect.** If nothing above decides it, state what it actually changes for the device, a user, the owner or the
   project's quality. If the answer is "nothing that matters", it is settled as "no net effect".

Read the source of every citation before using it. A rule must actually decide the item, not merely relate to it.
Bookkeeping about the audit itself (which merge file carries a change, where a note sits) is settled by the plan's own
process rules.

Whatever survives all six steps goes to the owner. Before you keep one, look across your share for items that share the
underlying choice: combine them into one higher-level decision, or propose the missing rule that would settle them all.

## Output: `audit/review/routine_<share>.json`

```json
{
  "settled": [{"id": "...", "step": "rule | style | docs | best-practice | similar | net-effect",
               "why": "one plain sentence a reader can check", "cite": "OR.. / CLAUDE.md rule / G../R.. / doc ref / URL / id of the item it follows"}],
  "for_owner": [{"id": "...", "kind": "decision | missing-rule", "topic": "<slug from audit/review/topics.json>",
                 "title": "...", "question": "the decision in max 10 words", "context": "2-4 plain sentences",
                 "options": [{"label": "...", "consequence": "..."}], "recommended": "label",
                 "members": ["routine ids this answers"], "refs": ["..."]}]
}
```

Every routine id of your share appears exactly once: in `settled`, or as a member of exactly one `for_owner` entry
(verify with a script and report the check). Readable text has no audit IDs or file:line references; those go in
`cite`/`refs`. Plain, friendly English; they/them for the owner. Never read `arduino/`, never edit any file outside
`audit/review/`, no git commits, nothing against hardware. Accuracy before speed.

Hand back: counts per step, the `for_owner` titles with member counts, and anything you were unsure about.
