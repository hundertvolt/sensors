# Phase A-L — brief for the verifier agents (2026-09-29)

You are the adversarial verifier of one A-L action file of the whole-project audit of the `sensors` repo at
/home/user/sensors (branch `claude/whole-project-audit-plan`). Your UNIT and HEAD follow in the prompt that
launched you. Audit execution is BLOCKED: you change nothing except your output file
`/home/user/sensors/audit/actions/verify/<UNIT>.md`. Append as you go.

The author followed `audit/sweeps/al_prompt.md` (read it first: purpose, constraints, format — its constraints
bind you too). Your job is to try to prove the file wrong, action by action, the way plan 4.4's verifiers do.
Accuracy before speed (OR107.a): check every action; never sample.

Inputs: `audit/actions/<UNIT>.md`; its input
`/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/al/input_<UNIT>.md`; the owner
rows of `PROJECT_AUDIT_PLAN.md` 3.2 the actions cite; earlier units' files in `audit/actions/`.

Per action, check:
1. **Sites**: every cited path and line range exists at HEAD and shows what the action says.
2. **Faithful**: the change does what the register clause asks — no less, no more. Flag overreach (work no clause
   asks for), a missed part of the clause, a choice the register or an owner row already settles differently, and
   any owner attribution without an owner source (quote the row). The most recent owner row wins.
3. **Blast radius**: repeat the searches yourself for the changed symbols, constants, messages, error numbers,
   field names, keys, routes and paths across the scopes the brief lists. Report every caller, generated site, js
   mirror, existing test that pins today's behaviour, twin fake, doc passage, TOML key or UART changelog duty that
   is missing or wrong. A "—" slot that should hold something is a finding.
4. **Implementable**: can it be done without a further question? If not, what is missing.
5. **Dependencies and conflicts**: a missing Depends; an action that conflicts with another action in this file
   or an earlier unit's file.

Also check the file as a whole: every input block has a ledger row and every clause naming the unit is covered;
each DONE-AT-HEAD is really done (open it); each register fix is right; each open point was not self-resolvable
from owner rows, the register or the sources (if it was, say how).

OUTPUT (`audit/actions/verify/<UNIT>.md`):
```
# A-L verify <UNIT> (HEAD <sha>)
Counts: <n> actions checked · OK <n> · FIX <n> · REJECT <n>; ledger <complete / gaps>
## Findings
- V.<UNIT>.nn | <action ID or "ledger"/"register fix k"/"open point k"> | FIX / REJECT / ADD | <evidence: path:line, owner row> | <the exact correction: replacement text for the slot or line, or the new action in the author's format>
## Checked OK
<action IDs, comma-separated>
```
List only non-OK items under Findings; each carries the exact correction so the lead can apply it after checking
it. FINAL REPLY (max 120 words): the counts and the three most serious findings.
