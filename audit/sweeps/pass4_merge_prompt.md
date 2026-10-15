# Pass 4 merge — brief for the register-merge agents (2026-09-29)

Same brief as `audit/sweeps/pass3_merge_prompt.md`, read it in full and follow it, with these substitutions:
- Input lines: `audit/pass4/MERGE_INPUT.md` (Q01-Q45) instead of pass 3's P lines.
- Overrides and answer lines: `audit/pass4/LEAD_MERGE.md` (M01-M04) instead of pass 3's L lines.
- Evidence: `audit/pass4/<scan>.md` (item IDs like K.29, H.10, F.18, R.26).
- Owner rows now run to OR109.
- Ledger: `audit/pass4/merge/<your letter>.md`, one line per (Q or M part, block) you own.
- On each changed block append " Pass 4: <Q and M numbers>." to its `- **Pass 2**:` line.
- Run no git commands at all, not even read-only ones; the lead checks commit hashes.
