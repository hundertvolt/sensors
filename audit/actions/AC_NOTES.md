# A-C input notes (collected during A-L)

Items the per-unit files cannot settle alone; A-C resolves each when it merges by site (OR106.a, OR111.a).

1. A.U5.02 cites SPEC C.7.1 for the FRAM-logging rule, whose rows A.U2.22 deletes: the cite must follow wherever
   A.U2.22 moves the rule (sweep, `verify/SWEEP_permanent_text_U1-U7.md`).
2. The permanent-text sweep covered U1-U7 after verification; U0's rewrites come from V.U0.01; U8 was verified
   before the rule entered the verifier brief, so U8 gets the same sweep after its corrections are applied.
3. Register fixes collected in each unit file's "Register fixes" section are applied to the register at the end of
   each wave, by the lead.
4. Commit messages are permanent history, so they cite no temporary audit ID either (lead, 2026-09-29, reading
   G9/R12 "permanent text never cites a temporary plan … by section or number"): an action's IDs stay in its Why /
   Depends slots or a `[src: …]` note. U0's fifteen "The commit message carries …" notes become `[src: …]` notes in
   the U8 sweep; A-C checks every file for the same pattern.
5. A.U8.19: the `loop.sync_wait_max_us` row's checker was an audit review (the per-file lens), which ends with the
   audit; A-C decides whether a standing check is owed (the UART no-block rule is CLAUDE.md's, and a checker already
   enforces 1,533 µs per V.U8) — OR111.a (2) asks every rule to keep a guard.
6. Actor tags in non-standard form (A.U8.01 `estimated (agent, <commit>)`, A.U8.06 `agent 2026-09-11 (`7cf989d`)`,
   A.U8.07 "legacy value kept (agent)" without date): A-C normalises to "(actor, YYYY-MM-DD)".
7. U11 asks for catalog edits to A.U2.01: wrnno 24 retired, wrnno 22 text narrowed, no `_ERR_UNEXPECTED` in
   `api_response.py` (`audit/actions/U11.md` Register fixes) — A-C merges them into A.U2.01's table.
8. U12 Q1 self-resolved (lead): `abs_humidity()`/`rel_humidity()` are removed as unused product code; A.U12.09/10
   follow that in A-C.
9. U6 register fix 8 (SPEC L.6.4 lacks the `@web`/`@web-group` rows CLAUDE.md points to; the grammar lives in H.5.1)
   has no register block: U36 carries it (either the rows or CLAUDE.md's pointer moves to H.5.1).
10. U8C's six register fixes edit U8.md, not the register; they are applied after U8C (and its supplement U8C2) is
    verified. U8 register fix 6 (Appendix C NOT-DONE) is stale since U8C.
11. U13 Open point 1 (FRAM CS pull-up) withdrawn by the lead after the owner's challenge: the power-on hold time is
    met by boot timing; A.U13.04/05 and U13 register fix 5 are rewritten as a documented fact (see the note at the end
    of `U13.md`), no board change.
12. Asked the owner 2026-09-30 (pending): (Q-lwIP) the 10 s modlwip write stall — options per `verify/U14.md` V.U14.Q1,
    recommended TCP_SND_BUF 1600 + TCP_NODELAY + MEM_SIZE 24,900 (A.U14.30 waits); (Q-I2C) a boot-time I2C bus clear
    before the controller exists, from the owner's 2026-07-13 rule (`2421948`) against the lead's harmonization 38
    reading of OR64 (A.U14.17 waits; G4/R22 State "no boot-time bus clear (settled by the lead …)" follows the answer).
13. A.U15.12: `CFGMGR_SCD30` stays RAM-only (no FRAM chunk) per the owner's words in OR99 ("no extra FRAM chunk");
    the lead's note at the end of `U15.md` supersedes the Open-points reading.
