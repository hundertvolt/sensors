# Final bird's-eye scan: verification brief

S = /tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad

First read `S/u35r/final_scan/BRIEF_COMMON.md` in full: the context, the owner's rulings, the safety rules (binding for
you too) and the release worktree `S/wt-final` (590cffcf) against the baseline `25caf528`. One correction to its
"already decided" list: the boot-confined `gc.collect()` placement reset is NOT settled. The release records it as
removed (by an agent), and whether the owner agreed to that removal is itself a question to check.

A first set of fresh reviewers scanned the release and wrote reports. You are a different, independent reviewer. Your
job is to try to DISPROVE each finding in the report(s) you are given. Reviewers' mistakes come back as confidently as
their real findings; a finding that survives your attempt to refute it is worth the owner's time, one that does not is
noise. Do not take a report's reasoning, citations or "decision record: none found" on trust: check them yourself.

For each finding:
1. **Fact.** Is what it cites true at that `file:line` in `S/wt-final`? Read the code or text (filtered).
2. **Is it really a leftover / gap / conflict?** Look for an owner decision that covers it: grep (filtered) the rulings
   file `S/u35r/recovered/owner_rulings_after_LN118.md`, `S/u35r/decrev/inputs/owner_words_lane_plan.md`,
   `S/u35r/picture/PICTURE.md`, and, for the earlier owner rows, the archive copy of the audit plan
   (`git -C S/wt-final show origin/claude/u35-audit-archive:PROJECT_AUDIT_PLAN.md | grep -v -i -E "<filter>" | grep ...`).
   Is the thing "proven good" (it fixes an observed or reproduced failure, measurably improves the device or build, or
   the owner approved it)? Then it stays, at most in a leaner form.
3. **The fix.** Would the proposed fix drop a real feature, open a gap, or start a chain of follow-on changes? Is there
   a smaller fix? Would it change firmware behaviour on the device (then say so)? Roughly how many lines does it touch?
4. **Worth it?** The goal is "all gaps closed, agreed features implemented, and from there minimal, efficient and lean
   changes", with the change against main (= the pre-audit code) as small as reasonable. Removing an audit-era addition
   shrinks that change; reworking pre-audit code grows it. A true but marginal finding is not worth a change.

Verdicts, one per finding:
- **CONFIRMED** - true, a real leftover/gap/conflict, and the fix (or your smaller one) is safe and worth it.
- **CONFIRMED-OWNER** - true, but the fix removes something that could be a real feature, or reverses something the
  owner said yes to: the owner must decide. Give the question in one plain sentence.
- **MINOR** - true but not worth a change now (say why in one line).
- **REFUTED** - the fact is wrong, or an owner decision / proof covers it (cite it).

Also flag duplicates across the findings you see (same root, two reports) and keep the root one.

## Output

Write `S/u35r/final_scan/V_<YOUR_ID>.md`:

```
# V_<YOUR_ID>: verification of <report ids>
## Summary table: id | verdict | one-line reason | fix size (lines) | touches device behaviour? (y/n)
## Per finding (short): what you checked, what you found, the decisive citation, the smallest fix
## Duplicates and notes
```

Your final message: the summary table only (at most 20 lines).
