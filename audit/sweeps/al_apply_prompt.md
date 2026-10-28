# Phase A-L — brief for the apply agents (2026-09-29)

You apply an A-L verifier's accepted corrections to one action file of the `sensors` audit
(/home/user/sensors, branch `claude/whole-project-audit-plan`). Your UNIT follows in the prompt that launched you.
Audit execution is BLOCKED: you edit only `/home/user/sensors/audit/actions/<UNIT>.md`; no other file, no git
writes.

1. Read `audit/actions/verify/<UNIT>.md`, section "## Findings". Every item V.<UNIT>.nn is accepted by the lead
   unless the prompt says otherwise.
2. FIX: make exactly the edit the item's last field ("the exact correction") describes, in the named action's
   named slot (Site, Change, Blast, Depends, Kind), or in the Ledger / Register fixes / Open points section it
   names. ADD: add the new action (numbered after the last existing one) or the rows exactly as given. Where an
   item offers alternatives, apply the first unless it says otherwise.
3. A correction that concerns another unit's file is never applied there: write it as a cross-unit note in this
   file's Depends or Blast slot ("co-lands with A.<unit>.nn — A-C merges").
4. Then clear what the corrections left stale in this file — line ranges, counts, numbers, cross-references,
   ledger rows, Depends lists, "none" lines that are no longer true. Check each against the source at HEAD and the
   verify file before changing it; never guess.
5. Append at the end: "Verified 2026-09-29 (`audit/actions/verify/<UNIT>.md`): V.<UNIT>.01-V.<UNIT>.nn applied."
6. Re-read every edited action to check each edit landed in the right action and reads correctly.

Final reply (max 100 words): items applied; stale spots fixed; anything not applied or left, and why.
