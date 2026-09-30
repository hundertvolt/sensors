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
14. Test-tier `@tunable` classification convergence (lead, 2026-09-30): after C.0.1, G1-G18 and G19, each further
    family found by a verifier was smaller than the last (seven families, then three, then one of 18 sites). The
    search stops at family level here; residual literals of a tuned purpose are the B2 per-file pass's to catch, which
    reads every test file in full (plan 4.1). A-C records this as the stated limit of the A-L inventory, not a gap.
15. Owner answered item 12 on 2026-09-30: OR112 (lwIP option (b), thorough hardware test in phase C) and OR113 (boot
    bus clear (a); standing principle "recover with the smallest possible blast radius … escalating up to a full bus
    reset … also in mid operation … Apply this idea throughout!"). A.U14.30 and A.U14.17 option (a) are no longer
    pending; U19 writes the `TCP_NODELAY` action as firm. OR113.a (2) needs a recovery-ladder pass over every
    bus-facing unit already written (U10, U13, U15, U16, U17; U18 for the network side) — `SUPP_recovery.md` — and
    every later author and verifier applies it (brief rule 8). Harmonization 38 and G4/R22 are rewritten.
16. U17 Q1 (UART controller re-init as a recovery rung) self-resolved by the lead to (a), not a rung, documented in
    SPEC J.5 (A.U17.33): rp2 flags UART errors per byte and latches none (v1.29.0 `ports/rp2/machine_uart.c:162-190`),
    so a re-init has nothing to clear. The A-C list shows it to the owner as a lead decision under OR113.
17. V.U17.01: `(x + 1) & CAP` steps allocate at the wrap (2**30 is a heap int on rp2); A.U15.31 takes the same
    conditional wrap as A.U17.28/A.U17.13. A-C checks every sequence/counter action for the add-then-mask form.
18. U19 Open point 1 put to the owner 2026-09-30 (pending): modlwip's `setsockopt(TCP_NODELAY)` writes
    `socket->pcb.tcp->flags` with no NULL check and no lwIP lock (v1.29.0 `extmod/modlwip.c:1527-1535`), while a peer
    reset sets `pcb.tcp = NULL` from PendSV (`:498-507`) — confirmed by the lead. Alternative: `TCP_OVERSIZE 0` in
    `[lwip]` compiles out the oversize path (`lwip/src/core/tcp_out.c:226-278`; rp2 sets neither `TCP_OVERSIZE` nor
    `LWIP_NETIF_TX_SINGLE_PBUF`, default `TCP_MSS`), the one property OR112's `TCP_NODELAY` was chosen for
    (`verify/U14.md` V.U14.Q1). A.U19.22 and A.U14.30 follow the answer; the U19 verifier writes both variants.
19. Item 18 answered 2026-09-30 by OR114 (owner: "Do it this way"): the modlwip `ERR_MEM` stall is fixed by a
    zero-touch build override (patched copy of `modlwip.c`, non-blocking send returns `EAGAIN`, swapped in through a
    generated `USER_C_MODULES` CMake file), watched upstream (issue 19704) and removed once the pin carries a fix.
    `TCP_NODELAY` (A.U19.22) is withdrawn; A.U14.30 loses the OR112 sizing (`[lwip]` keeps HEAD values) and keeps the
    doc/ensemble parts that still hold; the override itself is U21's (tooling). Phase C reproduces the stall on HEAD
    firmware first. `audit/actions/SUPP_lwip.md` holds the analysis.
20. Owner questions collected for the A-C review (not asked yet): U19 Q2 — debug-level console stall with a
    non-reading USB host (recommended (a), accept as a documented debug-mode limit).
21. OR114 override behaviour (lead, 2026-09-30): the U19 verifier confirmed from source that a full per-pcb queue with
    room left is frequent (`verify/U19.md` V.U19.Q0), so with `EAGAIN` a stuck connection spins cooperatively until an
    ACK or the 5 s per-call timeout. Kept as decided (upstream PR 19708's change, smallest patch); OR115's hammer tests
    bound other tasks' latency and CPU share in that state. If they fail the bound, the patch adds a short POLLOUT
    back-off after `EAGAIN` instead — that is then put to the owner as a change to OR114.
