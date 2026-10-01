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
22. Wave-3 register fixes to apply at wave end: G6/R49 "rate-limited trace" → one trace per event (OR35.a (2),
    OR35.b; `verify/U19.md` V.U19.08/23). U14 follow-ups from OR114: A.U14.30 drops the OR112 sizing and keeps the
    B.14.2 text/ensemble parts that still hold; A.U14.28's F.7 row 15 (missing Unix-port `TCP_NODELAY`) goes.
23. Wave 2 register fixes applied (`REGISTER_FIXES_wave2.md`); G3/R16's phase-C "scope CS / schematic pull-up" item
    dropped by the lead (the CS state is a documented datasheet fact, item 11). Left for the wave-3 pass: U8C2's own
    register fixes on U8.md (A.U8.04/09/13 and U8C.md items, listed at the end of `REGISTER_FIXES_wave2.md`).
24. `verify/U21.md` / `verify/U22.md` (lead accepted all): the OR115 hammer tests prove they reached the patched
    branch (`EAGAIN` while a zero-timeout poll still reports writable), else they pass on unpatched firmware too; the
    one-time unpatched control run covers every bound-asserting test; A.U21.14 sets a phase-C bound, a failed bound
    goes to the owner per item 21. A.U22.03 (event-driven LED pause) is an agent proposal, shown in the OR2.c review.
25. U25 Q1 (A.U25.69, the generated `main()`'s four keywords) is collected for the A-C owner review, reworded by
    V.U25.52 as unsettled (OR36 test-origin vs OR86 REPL start; options keep / remove / keep `cfg_path` only). U25's six named conflicts (A.U8.20, A.U15.R02, A.U20.02,
    A.U3.01, A.U11.03, A.U13.R01) are merged in A-C.
26. `verify/U23.md` accepted; lead decision: the history-pill border cue (A.U23.43 (6)) is dropped, since the owner's
    words for those pills are OR94 "don't change the current look of the website" and A28 "only colours its number";
    shown to the owner in the A-C list. A.U23.20/21's special-value text and colour are narrowed to the owner-backed
    fields (OR97.a (16) SGP40 timestamps; OR76.a CalLight colour).
27. OR116-OR118 (owner, 2026-09-30): UART link in both CRC modes at every tier; `SystemCmd` gains "Reset to defaults"
    and "Erase FRAM"; full tests at every tier, the config reset behind `persistence_write`. Register LEAD/R31-R32; the
    actions go in `SUPP_owner_0930.md` (one supplement over the already-verified units U11/U16/U17/U19/U20/U23 and
    the in-flight U24-U26), verified like any unit. Lead readings shown to the owner: CRC mode by TOML key, not a
    runtime switch (OR36); "the whole config" includes Wi-Fi & Identity.
28. U23 applied: `js/render.js:382` is a third direct `fetchOnce()` caller (the first fetch) that V.U23.01 did not
    count; A-C confirms A.U23.05's "one-shot sections run through the poll loop" covers it, else adds the site.
29. `verify/U24.md` accepted (V.U24 proved from v1.29.0 `extmod/modselect.c:252-266, 302-306`, `py/modio.c:84-96`):
    CLAUDE.md's "Known hang cause" bullet, SPEC J.7 and A.U14.28 row 12 state the wrong mechanism — the UART fakes
    answer `GET_FILENO` with 0, so a real poll watches stdin. A-C merges the replacement text across those sites and
    shows the CLAUDE.md fact change to the owner. Twin/unit fake conflicts (A.U24.16/17/20/80-82 against A.U25.02,
    .04, .07) are merged in A-C.
30. U26 written (86 actions, verifier running): N.27 and the `:271` flash-tier move are G2/R17's (U35), which no unit
    file claims yet — U35's author takes them; A-C checks they landed. Five agent design decisions go to the OR2.c review.
31. `verify/U25.md` accepted: U25 Q2 (V.U25.35, how the twin scenarios needing DUT-internal control move host-side:
    runner instrumentation / named in-process exceptions / drop to L1) joins the A-C owner questions. V.U25 finds
    SUPP_recovery's A.U15.R02 wrong on twin Run 5 (setup probes use up the faults, the heater-off rung is never
    reached): A-C corrects A.U15.R02. OR116-OR122 twin duties are SUPP_owner_0930's.
32. U24 applied (V.U24.01-54, A.U24.80-82). N.33's three `tests/` citers (`test_asy_udp_socket.py:399`,
    `test_ntp_wifi_dns_integration.py:365`, `test_asy_wifi_service.py:1527`) are U36's under G9/R12's State; A-C checks.
33. Owner answered 2026-09-30: OR123 (CRC mode by TOML key, L3 device script runs CRC16 over the jumper; the
    lead reading of AC_NOTES 27 confirmed), OR124 (the reset includes Wi-Fi & Identity; confirmed), OR125 (U25 Q2 →
    (a): every scenario host-side, the twin runner carries named instrumentation flags; A.U25.46 follows, pending Q2
    lifted). U25 Q1 (the `main()` keywords) is still open.
34. SUPP_owner_0930 written (30 actions, OR116-OR125). A-C resolves its 9 cross-unit conflicts (A.U11.03/.04,
    A.U20.06, A.U16.19, A.U23.17, A.U17.32, A.U26.71, A.U10.08 — OR120 overrides OR31.a (3) — and OR125.a's owner
    between U25 and this file) and its 5 LEAD/R31-R32 register fixes, after its verifier and applier. Its agent
    proposal (reboot/bootloader on the same shutdown sequence, OR119.a (5)) goes to the owner review.
35. U26 applied (V.U26.01-30, A.U26.87 new for N.27's G2/R09 half). A-C: A.U26.09/.32/.72 land together; OR90.a (1)'s
    "seven" is a stale count (five tests lose the marker) — flag to the owner, substance unchanged; co-lands with
    A.S0930.01/.05/.06, A.U13.R02, A.U17.05.
36. SUPP_owner_0930 applied (V.01-24); A.U25.74 added to U25 (OR125.a, twin-runner flags), U25's Q2 references
    settled by the lead. A-C: A.S0930.13's park point keys on `_feed_owned` (a refused command keeps feeding); co-lands
    A.U11.03 (`_flush_config_stores` returns bool), A.U24.17 (twin WDT `feed_times`), Depends added to A.U24.42/.53/.55,
    A.U26.26/.32/.68/.79/.87, A.U11.07.
37. Owner answered 2026-09-30 (OR126/OR126.a): U25 Q1 (a) — A.U25.69 firm; U19 Q2 (a) — accepted, DTR-only stall
    confirmed from source; OR119.a (5) accepted — reboot/bootloader run the controlled sequence (new SUPP actions);
    A.U22.03 withdrawn; corrections accepted (OR90.a (1) five, CLAUDE.md hang-cause text per item 29, border cue
    dropped per item 26, U17 Q1 (a)). U27 applied (V.U27.01-21, A.U27.39): A-C drops A.U11.26/A.U19.15's U35
    dependency (met by A.U27.07); co-lands with A.U26.66, A.U28.33 and three more `ci.yml` build-if-missing steps.
38. U28 applied (V.U28.01-22, A.U28.43 wires the built-HTML lint). A-C: A.U28.02's uv pin value is `<v>` (no recorded
    source) — execution pins the uv version current at B0 and records it in A.U0.06's environment line; A.U28.24's bare
    `python3` preview script meets G8/R05's version check (decide at merge); co-lands A.U27.15/A.U28.33 (`.gitignore`
    MICROPYPATH sentence, keep one), A.U27.39/A.U28.17 (port-53 lock), A.U28.41/A.U20.14 (template constant).
34. Owner answered 2026-09-30: OR127 (secret scan excludes `arduino/`; U29 open point closed), OR128 (`LastTaskEnd` in
    `/status`; U32 Q1 closed, A.U32.06 firm). OR129: dependency refresh (LEAD/R33) in U0 after the baseline and a
    second check in U37 — A-C adds the U0 step and orders it before every B1 action; every action citing a pinned
    upstream line carries "re-check against the refreshed pin".
35. `verify/U31.md` accepted: A.U31.07 (the supervisor scan can pass 8000 ms under load: four task ends × 627-700 ms
    per FRAM write with three `/status` readers, plus the 2 s sleep and the 4 s reset delay) is an owner question, U31 Q1,
    asked 2026-09-30. U32 Q1 closed by OR128.
36. Owner answered U31 Q1 2026-09-30 (OR130): option (a), one feed before the budget reboot; A.U31.07 firm; the G5/R02
    Req rewrite and OR31.a (3)'s two-call-site test follow (register fixes at wave end).
37. `verify/U36b.md` accepted: moving `datasheets/` into the owner's private `hundertvolt/datasheets` submodule
    (A.U36.545, A.U28.35; OR80, OR95) needs push access nobody has verified (OR95.a verified a clone only). A-C lists it
    as an explicit owner step before the move, shown at the A-C review.
38. A-C lead rulings from `M_SRC_SENS.md`'s gaps (2026-10-01): GAP-14 — A.U11.S01's never-true runtime type checks are
    not written anywhere (the lead's L1 answer: the fix is at the type level); GAP-15 — `_error_check()` unchanged, each
    reader passes `condition=results[0] is None`; GAP-17 (G5/R14, agent rank) — protocol classes and `I2CDevice` are
    named exempt in A.U10.22's check, `NotificationService`'s `_finalized` guard counts as its gate, `NeopixelDriver`
    gets an `initialized` gate. Every later A-C cluster applies these.
39. Lead ruling (2026-10-01): `CRC_Base` with an out-of-range polynomial degrades fully to pass-through (length 0), as
    its documented contract already states — M.SRC_CORE.131; TEST_UNIT carries the L1 cases.
40. `M_WEB.md` read six `tests_js/` files at the action sites plus a grep, not in full (its header names them): the
    end-state check reads those six in full and confirms M.WEB.052-.059 against them.
41. Owner, 2026-10-01: GEN Q1 → (a) (OR131: Microdot stubs byte-identical in `ext/typings/microdot/`, U0 re-vendor) and
    GEN Q2 → (a) (OR132: light-theme AA tokens applied, M.GEN.062). Every cluster writes both as firm, no "pending".
42. Lead rulings on `M_TEST_UNIT.md`'s two questions (2026-10-01). (1) Header block: settled by G9/R16 (every file "opens
    with exactly one header block", every-file scope owner PQ6, 2026-09-26; the gate "checks header presence") — the 23
    L1 files without one each get a ≤ 3-line docstring, landing in U27 with the presence check; not an owner question.
    (2) `NotificationService`: AC_NOTES 38's "`_finalized` counts as its gate" is void, since M.SRC_SENS.033 removes
    `_finalized`. G5/R14 settles it: the class has an async `setup()`, so it carries `self.initialized` (False in
    `__init__`, True in `setup()`) and stays in A.U10.22's check, not exempt. No method guards on it; a call before
    `setup()` answers the construction defaults through its members' own gates (M.SRC_SENS.033).
43. Owner, 2026-10-01: SCR Q1 → (a) (OR133: every runner, `test.sh` included, exits 2 on a usage or setting error;
    E.10 names no exception; `test_test_sh.py`'s rejection tests expect 2). Written firm everywhere.
44. Lead (2026-10-01), TEST_UNIT GAP-U3 and the TSC gap: `NeopixelDriver` gets `self.initialized` (False last in
    `__init__`, True in `setup()`, which returns the logger's result) — M.SRC_SENS.023/.024 amended. As for
    `NotificationService` (42), no method guards on it; a call before `setup()` answers as after it.
45. Cross-cluster gaps left after their owning merge closed, for the A-C gap pass before ordering: PROC gap 5 — no runner
    selects `multi_day_rollover` (SCR M.SCR.030-.032, HW_BENCH M.HW_BENCH.126); TSC's `NeopixelDriver` gap is already
    carried by M.SRC_SENS.023/.024 (AC_NOTES 44). Every other "Gaps for other clusters" item is checked in the same pass.
46. Owner, 2026-10-01 (OR134 → LEAD/R34): execution schedules test runs for wall clock without weakening any gate —
    scoped runs first, the full gate per unit unchanged, background runs on worktree snapshots, port-binding suites
    isolated by network namespace (proven in U0) or serialised, GitHub CI as a parallel lane, hardware rounds batched.
    A-C2 writes the schedule into the work order.
