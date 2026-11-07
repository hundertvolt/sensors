# DECREV crosswalk: the eight parts in one global view (lead, 2026-10-28)

S = `/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad`. Read the shared brief first:
`S/u35r/briefs/decrev.md` (the owner's request, the verdicts, the rules; they all apply to you). Read-only.

The eight parts are `S/u35r/decrev/DR1.md` (review page, planning) ... `DR8.md` (untracked agent text):
DR1 review page; DR2-DR6 the register's owner-review list by unit range, DR6 also the parked deltas and the redo's
lead decisions; DR7 the tunable values (SPECIFICATION.md Part N); DR8 the agent-tagged text elsewhere.

## A record gap the parts did not have (lead, 2026-10-28)
The parts read the owner's words from `PROJECT_AUDIT_PLAN.md`, the rulings file, `CHECKLIST.md` and the review
answers. 56 further owner quotes were recorded only in the lead's lane plan; they are extracted, each with its LEAD
NOTE and context, in `S/u35r/decrev/inputs/owner_words_lane_plan.md` (some entries are the lead's own questions; the
context says which). One example the lead checked: DR8 rates the CI apt mirror check and package cache DIFF against
the owner's 2026-10-27 16:48 "Don't care about proven external issues so far.", but at 20:23 the owner asked for the
CI failures to be investigated and at 20:53 approved the fix ("What about option 3 plus cache? Is there something
adversarial to using the cache?", then "Yes do it like you proposed"; LEAD NOTES 320 and 322): that row is OWN.
Read the extract first, and re-settle every verdict in DR1-DR8 that these words touch (an agent decision the owner in
fact took or adopted becomes OWN; a DIFF or OBS against the owner's words falls; a SAME the words contradict becomes
DIFF). List every re-settled row with the quote and its LEAD NOTE.

## Your job
1. **Pair the counterparts.** One decision often appears in several sets: a review-page item, executed in a unit
   (a register row), written into SPECIFICATION.md (a tagged line), with a value in Part N. Join each such chain by
   its words (the parts named likely counterparts; verify by reading both rows). One line per chain: the ids, the
   topic, the verdicts each part gave.
2. **Verdict conflicts.** Where the same decision got different verdicts in different parts (SAME in one, DIFF or
   OBS in another; OWN in one, agent in another), settle it against the record and the source, as the brief
   requires (owner's words win; otherwise the verified fact; a hypothesis never). Say which verdict stands and why.
3. **Contradictions across parts.** Two decisions from different sets that cannot both hold, or a decision against
   an owner decision, ruling or picture line that a part did not see because the other side was in another set.
   Check every pair the parts listed, and look for more within each topic (group all rows by the topic key). Both
   sides, sources, which stands.
4. **Seeds and chains.** Decisions that seeded others (a rule, a scheme, a contract adopted early that later rows
   applied): name the seed, its dependants across the sets, and what a DIFF or OBS on the seed takes along. Check
   that a seed's verdict and its dependants' verdicts agree (a SAME dependant of an OBS seed is a conflict).
5. **The DIFFs as one set.** Do the DIFFs, taken together, contradict each other or an owner decision, or the keep
   list of `S/u35r/scan2/SCAN2.md` section 5 (what must stay effective)? Would taking them all regress a confirmed gap
   or a rare but real case? Name any such.
6. **CHECKs.** Merge the parts' "needs verification" lists, drop duplicates, and order them by how much depends on
   them.

## Hand-back
Write `S/u35r/decrev/DRX.md`, first line "DRX crosswalk, written by the part (<date -u>)": the chains table; the
verdict conflicts settled; the cross-part contradictions; the seeds with their dependants; the DIFF set check; the
merged CHECK list; and totals per verdict across all eight parts after your settlements (counting each chain once).
Target 30-50 KB. Final message: the path, the totals, the number of chains, conflicts and contradictions, and the
three most significant findings in one line each. Last line: "nothing of mine is running".
