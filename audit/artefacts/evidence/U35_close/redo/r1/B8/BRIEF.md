# B8 brief: build chain and generated code (lead, 2026-11-04)

Read first, in order: `S/u35r/r1/common_r1.md` (binding; its standing direction: target low complexity),
`S/u35r/r1/B8/ACTION_LIST.md` (your work list: the re-base note at its top maps its line numbers to your base, the
lead's decisions are at its end), PLAN.md sections 2 and 4 and its B8 row (`S/u35r/plan/PLAN.md`, R1).

- Worktree `S/wt-b8`, branch `audit/r1-b8`, at the integration head d5c90b71 (B1-B7 merged). Run labels start with
  `b8_`. Hand-back: `S/u35r/r1/B8/HANDBACK.md`. You run alone; every file in the list is yours.
- The owner, 2026-11-04 06:11 UTC: "take extra care that we are not currently creating a runaway, self-inflicted
  complexity increase." So each row gets the smallest change that does what it says: no new mechanism, helper, test
  or doc paragraph a row does not need. A row whose change would grow the code against `25caf528` goes to the lead
  before you write it (say so in the hand-back and do the rest). The hand-back gives the net lines per directory
  against d5c90b71 (`git diff --shortstat d5c90b71 HEAD -- <dir>`) beside the sizes.
- Budget: this unit's share is 4 % of the week: one gate and at most one fix round. If a second round looks needed,
  stop and hand back with what is open.
- The host is not yours yet: the lead's coverage run holds it until about 07:30 UTC. Read and write first (the pinning
  tests before each change); start no run until the lead's message that the host is free.
- Nothing needs the owner (the list is final). Anything that would: do every other row, hand back with it open and
  say so; do not ask the owner yourself.
- The website reads `definitions.py` and the catalog: the gate adds `npm run lint`, `npm run typecheck` and
  `npm run test:unit` (`node_modules` is linked in the worktree). `tests_hardware` only with `--collect-only` or
  `--twin`; nothing is skipped, disabled or deselected. The gate runs once, after the lead's message.

Sources for each row are its basis column; read the part you need, not whole files. Before you remove, check each
"remove" row for proof that it is good (PLAN.md 0): one with such proof becomes a shrink row, said so in the hand-back.
A pre-audit or legacy function found lost or changed without a recorded reason goes to the lead.
