# A-C3 Part O — owner rows and adherence (HEAD a937afa)

Read-only check of the planned end state (HEAD with every merged change of `audit/consolidation/M_*.md` applied).
Each finding names the M-ID to amend and the exact amendment text; the lead applies them after A-C2. No M file was
edited. Helper: `audit/sweeps/ac3_o.py` (parses all 1,865 merged changes and runs the text scans of section B-E).

Inputs read: `audit/sweeps/ac23_prompt.md`, `audit/sweeps/ac_prompt.md`, `audit/actions/AC_NOTES.md` (1-50),
`PROJECT_AUDIT_PLAN.md` 3.1-3.2 (OR1-OR135 with every .a/.b/.c, read in full), CLAUDE.md (session context), the whole
CLAUDE.md section of `M_DOCS.md` (M.DOCS.068-.108), M.WEB.050-.059 and the actions they cite where needed (A.U6.05,
A.U6.07, A.U6.15, A.U9.03, A.U10.37, A.U10.40, A.U19.02, A.U23.07, A.U23.16, A.U23.37, A.U24.14, A.U25.12, A.U30.16,
A.U36.548), and in full: `tests_js/mock-server.test.js`, `definitions.test.js`, `render.test.js`, `templates.test.js`,
`main.test.js`, `app.test.js`, `nav.test.js`, `definitions-mockdata-coverage.test.js` (AC_NOTES 40's six files plus the
two others M.WEB.052-.059 cover).

Finding weights: **H** = the end state breaks a test, a check or an owner row; **M** = a rule breach in permanent text
or a lost constituent detail; **L** = an imprecise line reference or form.

## A. The tests_js files against M.WEB.052-.059 (AC_NOTES 40)

**O-01 (H) M.WEB.052 — back-to-back LED commands turn "Failed" after the busy refusal.** A.U9.03's Blast states that
`mock-server.test.js:272-314`'s accepted submissions (`fractionalT` t 1.5 at `:293`, `lowerBoundary` `:302`,
`upperBoundary` `:304`, `again` `:312`) arrive back to back and each later one would read `"Failed"` once the mock
refuses a busy LED; M.WEB.052 kept only the new busy case and dropped that instruction, so the four existing
`toBe("Valid")` assertions fail at U9. Amend M.WEB.052's Change, after "and "Valid" again after `vi.setSystemTime`
passes `T`;", insert: "every other accepted `LightCmdLED` case in `:272-314` (`:293`, `:302`, `:304`, `:312`) advances the
mock clock past the previous accepted command's `T` (`vi.setSystemTime`) before it is sent, so each still reads
"Valid" (A.U9.03's Blast); the never-"Unchanged" repeat at `:312` keeps its point that an identical later command is
dispatched again;".

**O-02 (M) M.WEB.052 — the LightCmdLED comment block stays false.** `:273-275` says "'Invalid' only for a non-dict
payload, while a missing, non-numeric, fractional or out-of-range subfield reports 'Failed'"; `:287-288` ("superseding
the old raw int()/float() truncating casts") and `:296` ("is now rejected") are history. M.WEB.052 only swaps the
`coerce_numeric()` name at `:275`. Amend M.WEB.052's Change: replace "the `:249`, `:275` comments' `coerce_numeric()` →
"the server's per-kind validation"" with "the `:249` comment's `coerce_numeric()` → "the server's per-kind validation";
`:273-275` → "// Mirrors _dispatch_notification_led(): a malformed payload, a missing or extra member or a value outside
// its schema answers "Invalid"; a well-formed command while a signal still runs answers "Failed"."; `:287-288` →
"// A fractional R/G/B is rejected, never truncated."; `:296` → "// Out-of-range members are rejected (legacy
led_cmd()'s bounds)."".

**O-03 (M) M.WEB.052 — test titles name functions the end state removes or renames, and claims it reverses.**
`:336` "like the real backend's _set_dict_cfg() ContMeas branch" (SCD30's own `_set_dict_cfg()` goes, OR42.c (1),
M.SRC_SENS A.U4.04); `:372` "like the real backend's _mask_pw()" (→ `_cfg_overlay()`, M.SRC_NET A.U18 row at
M_SRC_NET.md:1302); `:316` "GET always reads back the fixed real-hardware constant 400 regardless of what was applied"
and its comment `:325-327` (A.U25.12 makes the readback the last applied value). Amend M.WEB.052's Change, append:
"Titles and comments follow the end state: `:316` → "dispatches PUT /sensors' ForceCalRef: range-validated, never
Unchanged, and GET reads back the last reference applied (400 on a fresh mock)", `:325-327` → "// The chip reports the
most recently used reference within one power-up and 400 after power-up (Interface Description 1.4.6).";
`:336` → "dispatches PUT /sensors' ContMeas as a command: bool-only, never persisted or reported by GET"; `:372` →
"masks PW (and HotspotPW) on every GET /networking, whatever was applied"; every other title naming a `src/` function
names one that exists at the end state (grep at landing)."

**O-04 (L) M.WEB.052 — line references.** The fixture is `:5-153` (DEFS `:5-135`, DATA `:137-153`), not "`:40-150`";
"Trailing restores (`:400-403`) go" covers only `:403` (`random.mockRestore()`; `:400` creates the spy). Amend
"Fixture definitions `:40-150`" → "Fixture definitions `:5-135` (data `:137-153`)" and "Trailing restores (`:400-403`)
go" → "The trailing restore `:403` goes (`restoreMocks`, A.U24.14); `:419-444`'s `finally` restore may stay".

**O-05 (H) M.WEB.053 — the removed-case line range deletes a case it keeps, and a variant name survives.**
(a) M.WEB.053 says "`:242-253` and the `defaultValue` half of `:254-258` go (the null pass-through case stays, without
`defaultValue`)"; at HEAD `:242-246` is the fallback case, `:248-252` the null pass-through case (inside `:242-253`), and
`:254-258` is `describe("loadDefinitions")`'s head. (b) A.U6.05's Site is `:1-6, :204-214` (rewritten); M.WEB.053 replaces
only `:209-210`, leaving the `:205-207` comment ("Nothing anywhere ran this validator against the shipped dev definitions
before … this suite only ever loaded wozi's …") — history (G9/R11) and a `wozi` substring that M.TSC.110's
variant-literal check fails on — and the `:2-3` comment describing the two JSON imports that go. Amend M.WEB.053's
Change: replace "`:242-253` and the `defaultValue` half of `:254-258` go (the null pass-through case stays, without
`defaultValue`)" with "`:242-246` (the `defaultValue` fallback case) goes; `:248-252` (null pass-through) stays with
`defaultValue: 5000` removed from its field and its comment → "// CCT is legitimately null in a dark room; the renderer
shows an em dash for it.""; replace "replaces `:209-210`" with "replaces `:205-213` (comment and `it.each`)"; add "the
`:2-3` comment → "// Every device's generated definitions come from tests_js/_generated_definitions.js (a real browser
run: no node:fs)."".

**O-06 (H) M.WEB.054 — `:323`'s new text keeps the old key the same change renames.** M.WEB.054 renames `MeasInt` →
`MeasInterval` throughout the fixture (A.U10.40, whose closing grep fails on any old key outside `legacy/`/`audit/`), then
writes "`:323` → "Command executed — MeasInt: Valid"". Amend to "`:323` → "Command executed — MeasInterval: Valid"".

**O-07 (H) M.WEB.054 — the PUT 500 case keeps the old injected text.** The "Found while merging" note moves `:647-666` to
"Internal server error" because an injected 500 answers with the catalog text (M.WEB.052, A.U23.26), but `:979-996`
("shows Failed with the server's own descr when a PUT hits a shaped HTTP error (500)") still expects
`/simulated failure/i` at `:995`. Amend the "Found while merging" note, append: "The same holds for `:995` (the PUT
500 case): it expects "Internal server error"."

**O-08 (M) M.WEB.054 — comments that the changed cases make false or that tell history.** `:702-704` ("'Failed', not
'Invalid': the dispatch layer only checks isinstance(payload, dict) …") is false once both cases expect "Invalid"
(only `:727` is rewritten); `:417` title and `:418-420` ("/status's PUT never returns a per-field result",
"_put_status() never builds a result dict") are false once the mock answers `{"ResetErrors": "Valid"}`; `:458-460`
claims the second submission reports Valid; `:403-405` (M.WEB.054 cites `:399-401`) describes the mock's randomized
latency the end state removes; `:409-410` ("Before the fix, …"), `:584-586` ("Before the templates.js fix … seen live
in Chromium") and `:679-680` ("used to arrive as null") are history; `:864` names `fetchOnce()` (A.U23.05 moves one-shot
sections onto the poll loop, AC_NOTES 28). Amend M.WEB.054's Change, append: "Comments and titles follow the end state:
`:702-704` → "// A non-numeric member is refused by the dispatcher's per-member validation (SPECIFICATION.md A.8).";
`:417` → "shows Valid after a successful Reset All Errors submission, read from /status's per-field result" and
`:418-420` deleted; `:458-460` → "// The toggle is Off after the first Apply, so a second click has nothing to submit.";
the latency comment at `:403-405` (not `:399-401`) → "// Fake timers from here on: the live poll tick is driven
deterministically."; `:409-410` → "// The poll update keeps the chosen filter."; `:584-586` → "// SystemCmd is never
returned by GET /system (A.8), so the select starts on its placeholder and an untouched Apply sends nothing.";
`:679-680` → "// JSON.stringify(NaN) is "null"; the raw text is sent instead so the server can refuse it."; `:864`
names the section's status sub-request as M.WEB.020 names it (no `fetchOnce()` if that function is gone)."

**O-09 (H) M.WEB.058 — the XSS case still calls `buildField()`, whose import the change drops.** M.WEB.058 drops
`buildField` from the imports (A.U23.37: its export goes) and says "XSS (`:502-570`) hold", but `:518` calls
`buildField(field, HOSTILE, false)`. Amend "XSS (`:502-570`) hold" → "XSS (`:502-570`) hold, `:512-523` building its
hostile field through a one-field `buildFieldGroupCard()` like the field-markup cases".

**O-10 (M) M.WEB.058 — a stale module path and a history title.** `:399` cites `src/print_log.py's get_log()` (renamed
`src/asy_print_log.py`, M.SRC_CORE.001 / A.U10.37 "every text mention"); `:328`'s title ends "(regression - … it had
drifted to being set externally by render.js instead)". Amend M.WEB.058's Change, append: "`:399` →
`src/asy_print_log.py's get_log()` (A.U10.37); `:328`'s title → "tags the card with data-group-key itself, like
buildFieldGroupCard() (SPECIFICATION.md Part H.3: js/templates.js owns the hook)"."

**O-11 (M) M.WEB.059 — `main.test.js:144` keeps the old inlining script.** M.WEB.059 repoints `:47-49` and `:127-128` to
`scripts/_stage_website.py` (A.U23.38) but `:144` still says "(scripts/build_website.sh always writes valid JSON)".
Amend M.WEB.059's Change, append: "`main.test.js:144` "scripts/build_website.sh" → "scripts/_stage_website.py"".

**O-12 (M) M.WEB.059 — `app.test.js` loses two cases without a recorded reason (OR12, OR33.a).** HEAD `:97-106`
(landing section marked current in the nav) and `:119-130` (mock data fetch fails with HTTP 500 → banner, no section)
are not in M.WEB.059's case list (only a torn `samples.json`). Amend M.WEB.059's `app.test.js` case list, append: "the
landing section is marked `aria-current` in the drawer; a `samples.json` answered with HTTP 500 shows its banner and
renders no section".

**O-13 (L) M.WEB.057 — line references and a history comment.** The file has 126 lines: its readonly-only comment is
`:73-74` (not `:223-224`) and the two self-checks are `:107-125` (not `:257-275`); `:96-98` ("The gap this catches happened
twice in one branch …") is history and describes the two per-device `it`s that go. Amend: "`:223-224`" → "`:73-74`",
"`:257-275`" → "`:107-125`", and append "`:96-98` → "// A blank row is not a defect the renderer reports, so an
unresolvable readonly field fails here."".

Confirmed against the files (no amendment): M.WEB.051's sites; M.WEB.052's `:178-195`, `:196-212`, `:224-244`,
`:372-383`, `:469-486`, `:498-519`, `:539-549`; M.WEB.053's `:81-95`, `:264-265`, `:295`, `:298`; M.WEB.054's `:5-6`,
`:11`, `:20`, `:84-87` (cited `:84-86`), `:129`, `:382-415`, `:468-535`, `:583-645`, `:647-676`, `:698-744`, `:783-812`,
`:845-860`, `:882-930`, `:958`, `:1015-1037`; M.WEB.055/.056 (new files, headers ≤ 3 lines); M.WEB.057's `groupValuesFrom`
mirror (the `:86` object check passes: `samples.json` gives `LastTaskEnd` `null`, M.WEB.045); M.WEB.058's `:40-48`,
`:89-279`, `:343-389`, `:398-428`, `:438-462`, `:478`, `:489`; M.WEB.059's `main.test.js` `:7`, `:11-12`, `:47-49`,
`:90`, `:127-128`, `:138`, `:166` and `nav.test.js` `:7`, `:38-92`. Every `wozi` literal in the eight files is removed by
the M.WEB changes except O-05 (b). `DATA.networkingConfig.PW: "hunter2hunter2"` and `templates.test.js:26` are fixture
strings, not credentials.

## B. Temporary audit IDs in permanent text (G9/R12, AC_NOTES 4)

Scan: every quoted after-text in a Change slot (`→ "…"`, `comment "…"`, `header "…"`, …) searched for OR/G/LEAD/REF
rows, A-/M-/V-IDs, unit and phase labels and "this audit". Catalog codes (`W54`), ruff codes (`T20`) and chip
coefficients (`T1`) are permanent and not findings. Eight breaches:

**O-14 (M) M.SCR.039** (`scripts/test.sh` comment): "… any derived device serves (OR78: no device named here)." → "…
any derived device serves; no device is named here."

**O-15 (M) M.TWIN.019** (`digital_twin/_wall_clock.py` comment): "# From outside, as the tests adapt every product seam:
no src/ change (OR36)" → "# Bound from outside, as every test adapts a product seam: src/ stays unchanged."

**O-16 (M) M.TEST_UNIT.279** (`tests/test_notification_scd30_integration.py` comment): "… the streak step prints only
(A.U3.03)." → "… the streak step prints only (SPECIFICATION.md C.7)."

**O-17 (M) M.TWIN.052** (`digital_twin/run_generic_integration.py` comment): "…, kept while B3 shows the sparser interval
gives Run 11 the same verdict." → "… (tests_scripts/test_gc_collect_sites.py)." at landing; when A.U35.25's measurement
keeps the collect, the clause "a sparser interval gives Run 11 the same verdict" is appended (otherwise the line goes,
as written).

**O-18 (M) M.TWIN.062** (`digital_twin/README.md`): "… the next launch consumes and deletes it (M.TWIN.032)" → "… the
next launch consumes and deletes it."

**O-19 (M) M.SPEC.070** (SPEC C.13): "… named exempt in the check (A.U10.22)." → "… named exempt in
`tests_scripts/test_readiness_gates.py`."

**O-20 (M) M.SPEC.116** (SPEC H table row): "… | the `/status` row A.8 states (A.U32.06)" → "… | the `/status` row A.8
states".

**O-21 (M) M.SPEC.129** (SPEC I.4): "Release proof: <image>, both stages, <date> (A.C.09)." → "Release proof: <image>,
both stages, <date>." (the source stays in the merged change's From).

**O-22 (M) M.SPEC.136 and M.DOCS.076 — "this audit" in permanent text.** M.SPEC.136 (SPEC J): "The wire format is not
touched in this audit (owner, 2026-09-25); …" → "The wire format stays as it is until the C side is reconciled (owner,
2026-09-25); …". M.DOCS.076 (CLAUDE.md UART bullet): "during this audit the wire format is not touched (owner,
2026-09-25: 'the UART wire format is not touched')" → "until the C reconciliation the wire format is not touched (owner,
2026-09-25: 'the UART wire format is not touched')". After phase D deletes `audit/` (M.DOCS line 832) "this audit"
names nothing (G9/R12; OR24.a (2) states the rule without a time limit inside the audit).

Placeholders that resolve at execution (M.DOCS.035 `<the Part B section M.TOOL.040's SPEC text names>`, M.SPEC.090/.095
`<A.U26.58's script>`, `<A.U25.59's test>`, M.SPEC.098, M.SPEC.111 `<A.U10.05's check>`/`<A.U10.08's check>`, M.SPEC.144
`<A.U6.15's check>`, M.SPEC.129 "(its Part N row, by the ID A.U8.14 lands)") are instructions, not text; they hold
provided the executor writes the resolved name. Two can be resolved now: M.SPEC.144 `<A.U6.15's check>` →
`test_no_variant_literals.py` (M.TSC.110); M.SPEC.111 `<A.U10.08's check>` → `test_watchdog_feed_sites.py` (M.TSC.155).
Commit messages: M.PROC.001 (6) already states the AC_NOTES 4 rule; the two Change texts mentioning commit messages
(M.DOCS.033, M.DOCS.107) carry no ID.

## C. Actor-tag form (AC_NOTES 6, OR27.a, OR87.a (d))

**O-23 (L) Tags not in "(actor, YYYY-MM-DD)" form in after-texts.** Amend each after-text:
- M.SPEC.054: "(owner-confirmed, 2026-07-15, `1ed1c9a`: …)" → "(owner, 2026-07-15, `1ed1c9a`: …)".
- M.SRC_CORE.013: "(owner-confirmed, 2026-07-18)" → "(owner, 2026-07-18)".
- M.SRC_CORE.091: "(owner-confirmed, 2026-07-18: reject generally at the top)" → "(owner, 2026-07-18: reject generally
  at the top)"; "(owner-confirmed, 2026-07-18)" → "(owner, 2026-07-18)" (OR87.a (d) names this form for this file).
- M.SRC_SENS.017: "(owner-confirmed, 2026-07-21)" → "(owner, 2026-07-21)".
- M.SPEC.064: the kept "(owner's decision, 2026-09-18)" → "(owner, 2026-09-18)".
- M.SPEC.075: "(owner decision, 2026-09-24)" → "(owner, 2026-09-24)".
- M.SPEC.082: the kept "(owner decision, 2026-09-22)" → "(owner, 2026-09-22)".
- M.TEST_UNIT.127: "(owner decision, SPECIFICATION.md C.8)" → "(owner, 2026-09-26; SPECIFICATION.md C.8)" (OR64.a (3)
  dates it; the HEAD text has no date).
- M.HW_BENCH.076: "(owner's audit question, 2026-09-01)" → "(owner, 2026-09-01)".
- M.HW_BENCH.080: "(owner's suggestion, 2026-09-02)" → "(owner, 2026-09-02)".
- M.TWIN.044: "(owner's choice over a probabilistic flaky mode, 2026-08-12)" → "(owner, 2026-08-12: chosen over a
  probabilistic flaky mode)".
- M.WEB.060: "(owner's request, 2026-08-24)" → "(owner, 2026-08-24)".
- M.SRC_SENS.071: "(agent classification, 2026-09-14)" → "(agent, 2026-09-14)".
- M.DOCS.008: "(agent reading, 2026-08-20; not a verified legal conclusion)" → "(agent, 2026-08-20; not a verified legal
  conclusion)".

## D. Owner rows contradicted or not carried

**O-24 (M) M.PROC.033 — the trace range stops at OR133.** OR134 (2026-10-01, LEAD/R34) and OR135 (2026-10-01, LEAD/R35)
exist. Amend M.PROC.033 (2) "Every owner row OR1-OR133" → "Every owner row OR1-OR135" and its Resolved "read as
OR1-OR133 (its own text)" → "read as OR1-OR135, the current last row".

**O-25 (M) M.PROC.035 — the A-C review is not in OR135.a's form.** M.PROC.035 (1) shows the review list "each in the
owner's format" only; OR135.a (LEAD/R35, the latest owner direction on that review) requires a self-contained,
layered package. Amend M.PROC.035 (1), after "every AC_NOTES lead decision marked for the owner is shown": "as one
self-contained, layered package (OR135.a, LEAD/R35): a short overview, then one plain-language page per topic with the
decision, why, what changes for the owner and the consequence of saying no; detail one link away; decisions grouped and
sorted by weight so routine ones can be approved as a batch". Add OR135 to its From.

**O-26 (H) M.HW_BENCH.075 (1) — a test that passes whatever it measured, kept as a permanent hardware control arm.**
`test_send_stall_on_the_unpatched_image` "passes when the steps ran" whatever the bounds show. That is a check that
cannot fail (OR19.a (1) red flag; OR21.a (3) wants such a test reported, not counted) and a permanent control arm
(OR21.a (2): the sensitivity proof is done once in the audit). It is opt-in (`flash_cycle` and `--lwip-control-image`),
so no CI job carries it; its biting form is also the OR114.a (4) removal signal. Amend M.HW_BENCH.075 (1): replace "The
verdicts are recorded; the test passes when the steps ran (the round plan expects the stall bound to fail there — a
control run passing every bound means the hammer never reached the `ERR_MEM` loop, which the round reports, A.C.06)."
with "The test passes only when the unpatched image shows the stall (a bound fails, or the board stops answering ≥ 5 s
or resets); every bound holding fails it with "the hammer did not reach the ERR_MEM loop on the unpatched image, or the
pin carries an upstream fix: re-check the modlwip_eagain override (SPECIFICATION.md B.14)" (OR19.a (1), OR114.a (4)).
The verdicts are recorded either way." Settled by OR19.a/OR21.a/OR114.a; not an owner question.

**O-27 (H) M.HW_DEV.122 / M.SCR.015 — the GC-site checker fails at U31.** `loop_stretch_timing.py` (U31) times five
`gc.collect()` calls (`gc_max_us`); A.U30.16's allowance table (U30) declares "everything else in the three scopes is a
violation", and no change adds a row for this file, so `scripts/lint.sh` fails from U31. The use is a measurement the
owner rows allow (OR39.a (2) "whichever needs to be measured"; OR91.a (9) sizes a test pause to "the measured worst-case
collection pause"). Amend M.SCR.015's Change, after the tests/twin/hardware rows clause: "plus, from U31, the
**measured collection pause** row `tests_hardware/device_scripts/loop_stretch_timing.py` (its timing function), reason
"times gc.collect() itself: the pause SPECIFICATION.md F.3 bounds (OR91.a (9))""; and M.HW_DEV.122's Blast: append
"its `gc.collect()` allowance row → M.SCR.015 (U31 stage)". Also amend M.SCR.015's "the tests/twin/hardware rows A.U30.16
lists, re-derived from the end-state tree at landing" → "the tests/twin/hardware rows A.U30.16 lists by category
(baseline, boot mirror, before a timed window, twin exception, measured collection pause), each function re-checked
against its category at landing" — re-deriving rows from whatever the tree holds would allow any new collect.

**O-28 (L) M.DOCS.078 and its mirrors — "exemplary/base device" reads as the golden-reference role OR78.a (2) withdrew.**
OR78.a (2)-(3) (2026-09-28, later than the 2026-09-03 rule): wozi loses its role as default and golden reference; docs
name a device as a current fact or an example, never as a rule. The register keeps the fact (G1/R36: wozi is never
flashed and rests on L1/L2). Amend M.DOCS.078's Change: "`:159` "**WoZi is the exemplary/base variant" → "**WoZi is the
exemplary/base device"" → "`:159-161` → "**`wozi` is never physically flashed or bench-tested; its correctness rests on
L1/L2, and only `dev` is flashed** (owner, 2026-09-03, `a19691c`)""; the same wording in M.GEN's `wozi.toml` header
("the exemplary/base device" → "never physically flashed; its correctness rests on L1/L2") and the README device table
row at M_DOCS.md:871 ("the exemplary device" dropped). Settled by OR78.a; not an owner question.

Rows checked with the end state honouring them and no change contradicting them: see the table in section F.

## E. Per-file adherence scans (result)

- **Credentials**: no literal password, token or key in any after-text (regex over all Change slots). The one accepted
  credential stays as OR70.a (1) says (M.DOCS.080, A.U29.03); the bench password moves to environment data (A.U26.49).
- **Vendored `ext/`**: one site, M.GEN.051 (re-vendor of an unmodified upstream tag, U0) plus M.GEN.050 (upstream stubs
  byte-identical, OR131.a) — both within OR24.a (2) as refined by OR131.a. No edit.
- **Legacy tree**: only M.PROC.014 (byte-identical move, OR32.a (2)), M.PROC.015 (`legacy/README.md`), M.PROC.021/.045
  (reads). No content edit.
- **No new permanent CI control arm (OR21.a (2))**: none in `ci.yml` (M_TOOL adherence, its line 1844, confirmed);
  M.TSC.020/.082/.093, M.TEST_UNIT.029/.205/.324, M.TWIN.158 keep plants one-time or call the existing arm existing;
  M.HW_DEV.118's suppressed arm continues HEAD's device-script arm. The one new permanent arm is O-26 (hardware, opt-in).
- **`gc.collect()` in product code (OR39.a, OR84.a)**: only `run_setups()`/`start_tasks()` (M.SRC_CORE.015, M.SCR.015);
  none emitted by buildgen (M.GEN.006); the one runtime `gc` use is the boot entry's `gc.threshold(32768)` (OR40.a).
- **`method-assign` in `src/`**: no change adds one.
- **English**: no non-English word in any after-text (`×`, `°C`, `µs` only).
- **3-line cap and headers**: every header or comment after-text the scan measured is ≤ 3 lines at the repo's line
  width; the eight long quoted spans flagged by length are Change prose, not comment texts. New files carry a ≤ 3-line
  header in their changes; G9/R16's presence check (AC_NOTES 42, U27) is the standing guard.
- **Current-state text**: beyond O-02, O-08, O-10, O-13 and O-22, the history-phrase hits in after-texts are
  `UART_C_PORT_CHANGELOG.md` rows (a change log by purpose) or before-texts being removed.
- **Residual history comments in files the plan touches but no change rewrites**: found in the eight tests_js files read
  in full (O-02, O-08, O-10, O-13, and `render.test.js:277-278`, `:300-302` "legacy … restored"; `templates.test.js:41-42`
  is rewritten by M.WEB.058). Files not read in full here rely on M.PROC.032's first pass (every in-scope file against
  every rule, U37); A.U36.548's own Site list does not reach them.

## F. Owner rows OR1-OR135 against the end state

P = audit process only (no repository end state; its carrier named). E = end-state row: carried by the M-IDs named,
none contradicting unless a finding is cited. Later rows overtake earlier ones as the plan records.

| Row | Kind | Carried by / verdict |
|---|---|---|
| OR1, OR1.a | P | scope of the whole audit — met by the plan as a whole |
| OR2, .a, .b | P | questions only at recording/consolidation — A-C owner questions; M.PROC.001 |
| OR2.c | P | on-behalf decisions logged and reviewed — every M file's "Agent decisions"; M.PROC.035 (O-25) |
| OR3 | P | contradictions → fine-tune questions — A-C owner questions |
| OR4, .a | P | sources; inaccessible-source handling — M.PROC.004, M.DOCS.068 (datasheet rule text) |
| OR5, .a | E | closure states: BACKLOG four kinds (M.DOCS.061-.067), phase-C close (M.PROC.043); `UART_C_PORT_CHANGELOG.md` kept (M.DOCS.015-.018); C port out (OR127) |
| OR6, .a | P | sync points, flake rule — M.PROC.001 (6) |
| OR7, .a | P | lead resolves agent conflicts — A-C itself |
| OR8, .a | P/E | no hardware in execution; hardware prepared and queued — M.PROC.029, M.PROC.036-.043, C.md |
| OR9, .a | P | passes until all green — M.PROC.032 |
| OR10, .a, .b | E/P | Part K one ordered checklist with "The brief" step (M.SPEC.140-.143), skill (M.DOCS.060, A.U36.543 (9)); baseline runs A.U36.543 (10) |
| OR11, .a | E | stray files: M.PROC.019, M.TSC.009/.010 (allow-lists deleted U37); `audit/` + plan deleted at phase D (M_DOCS.md:832) |
| OR12, .a | P/E | regressions fixed, tests keep goals — M.DOCS.093 (A.U36.017), SPEC E.2.2; O-12 is a case dropped without reason |
| OR13, .a | P | drift logged; factual docs fixed — throughout |
| OR14, .a | P | historical drift trace — done in passes |
| OR15, .a | E | README layout + CLI reference + `--help` check (M.DOCS.047/.052, M.TSC.113/.217); summary block every runner (M.SCR.001/.002, M.DOCS.053) |
| OR16, .a | E/P | twin boots every device; liveness inventory; fault planting B3 (M.PROC.022-.027) |
| OR17, .a | E | twin fidelity table (M.TWIN.001-.026, M.SPEC.023/.107); doubtful facts as hardware rows |
| OR18, .a | E | abnormal-harmless handled inside modules; hardware faults escalate — SRC merges; SPEC C.7.2 |
| OR19, .a | P/E | biting review in B3 (M.PROC.022); O-26 is a non-biting test |
| OR20, .a | E | driver/DUT separation (SPEC E.9), no test code in product — M.TWIN, M.SCR.016-.018 |
| OR21, .a | E | (1)(3) M.PROC.022, summary counts M.SCR.001; (2) no new CI control arm — holds, O-26 the one non-CI arm |
| OR22, .a | E | generated-code tests and coverage (M.SCR.044, M.DOCS.054, TEST_UNIT generated files) |
| OR23, .a | E | host coverage report-only (M.SCR.044/.045); error contract tests (M.SCR.029/.065, M.TOOL.045/.072) |
| OR24, .a | E | consistency changes direct (M.DOCS.073); interfaces with consumers (A.U10.40 map); ext/legacy untouched (section E) |
| OR25, .a | P | intent map audit-only (M.PROC.023) |
| OR26, .a | E | MemoryError criterion reworded (M.DOCS.083, SPEC I.4(a)); raising-call map (M.PROC.025) |
| OR27, .a | E | current-state docs and tags — M.DOCS/M.SPEC; breaches O-02, O-08, O-10, O-13, O-22, O-23 |
| OR28, .a | E | one global catalog `buildgen/error_catalog.json` (M.GEN.034), catalog test, generated code table (M.GEN.014) |
| OR29, .a | E | hardware knowledge base: SPEC F / `tests_hardware/README.md` (M.SPEC, M.HW_BENCH) |
| OR30, .a | E | Part N register + `@tunable` tags + check (M.SPEC.155-.157, M.DOCS.105) |
| OR31, .a | E | WDT first in boot entry (M.GEN.001); feed sites pinned (M.TSC.155) with OR120/OR130 refinements (M.SRC_CORE.009) |
| OR32, .a | E | `legacy/` move (M.PROC.014/.015), bench content to living docs (M.HW_BENCH.111-.113), `test_legacy_paths.py` |
| OR33, .a | P | necessity verdicts (B3; register) |
| OR34 | P | scope covers the whole tree — holds |
| OR35, .a, .b | E | newest-entry rule in `asy_print_log.py` (M.SRC_CORE.060/.063); module flags removed; C.7.1 text (M.SPEC.059) |
| OR36, .a | E | test seams removed: `_NTP_UDP_PORT` const (M.SRC_NET.042), ISL `address` (M.SRC_SENS.085), `self.uart` (M.SRC_NET.213); general-purpose API kept (BMP3XX `address`, FRAM API, UART set/get) |
| OR37, .a | E/P | harmful constructs and races — M.DOCS.086 wear sentence, B3; retries not fixes (M.PROC.001 (4)) |
| OR38, .a | E | archive last 3 (M.SCR.003), port locks (M.SCR.012/.013), board scratch removal (M.HW_DEV.035-.038) |
| OR39, .a | E | gc sites (M.SCR.015, M.DOCS.089); O-27 adds the measured-pause row |
| OR40, .a | E | one threshold call, two stages per tier, two-image hardware proof (M.PROC.042) |
| OR41, .a | P/E | matrices audit-only; tests per layer (B3, TEST merges) |
| OR42, .a, .b, .c | E | compare-before-write primitive and SCD30 per-field rules/order (M.SRC_SENS SCD30 changes, `compare_before_write(..., always=("AmbPres", …))`); no PUT retry (M_WEB.md:2006); third-party loop risk documented (A.U29, SPEC A.11) |
| OR43, .a | E | value inventory; Part H placement rule (M.SPEC.113); hand definitions retired (M.GEN `html/definitions`); device set derived |
| OR44, .a | E | SPEC Part 0 (M.SPEC.001-.006), CLAUDE.md pointers (M.DOCS.073/.108) |
| OR45, .a | E | L0-L4 in SPEC E.6 (M.SPEC.082), lower levels first (M.SCR.006/.030/.031), skip flag never clean (M.SCR.030, M.TSC.196) |
| OR46, .a, .b | E | dead-code tool audit-only; config objects (M.SRC_NET.119/.124), `LogConfig`; `max-args = 8` (M.TOOL.029), reasoned per-file entries (M.TOOL.030) |
| OR47, .a | E | phases sequential (M.GEN.006); lazy chunk setup removed; t0 + k·slot (M.SRC_CORE.014, M.SPEC.067); 1 s timers outside the stagger |
| OR48, .a | P | legacy-loss scan, no permanent record (M.PROC.021/.045) |
| OR49, .a | E/P | load tests; closing report (M.PROC.034) |
| OR50, .a | E | non-code staleness (M.PROC.019, M.TOOL); installer cleans its leftovers (M.TOOL.060/.063, M.TSC.125) |
| OR51, .a | E | quality bar in SPEC D/E, practice in CLAUDE.md (M.DOCS.091/.093) |
| OR52, .a | E | (2) golden stored config (M.TSC.018/.129); (3) SEC limitations (SPEC A.11); (6) unwedge retired (M.TWIN); (7) LIC |
| OR53 | E | `pico_gpio.py` every RP2040 function (M.GEN.042, M.TSC.050/.055) |
| OR54, .a | E | website tiers derived; twin sampler the one exception (M.TWIN.052; O-17 wording) |
| OR55, .a | E | collect complete on return — test rule text (M.DOCS.089, SPEC I.4(e)) |
| OR56, .a | E | one event one entry (M.TSC.111); `DNSFallback` default "8.8.8.8,1.1.1.1" (M.SRC_NET); FRAM layout within one build (M.SPEC.010, M.TEST_UNIT.040) |
| OR57, .a | P | legacy intent rule — applied in merges |
| OR58, .a | E | no legacy paths; one key scheme (A.U10.40 via every cluster) |
| OR59, .a | E | `.frozen` first (M.GEN.001), shadowing test (M.TSC.093), runbook erase |
| OR60, .a | E | reset record in `mem_backup()` region 0, `ResetReason` (M.SRC_CORE.002/.003), twin model |
| OR61, .a | E | 1.24.1 everywhere (M.DOCS.069/.074/.079, M.PROC.015) |
| OR62, .a | — | overtaken by OR64.a/OR65.a |
| OR63, .a | E | Codecov gone (M.TOOL.015/.021, M.DOCS.054/.097, M.SPEC.033/.081) |
| OR64, .a; OR65, .a | E | general call kept, owner-tagged C.8 (M.SPEC.065); hazard tests kept; O-23 dates the test comment |
| OR66, .a; OR67, .a | E | compensation rules, `required` tags kept (M.SRC_SENS.060, M.GEN.049) |
| OR68, .a | E | owner tags; prevention rules in CLAUDE.md (M.DOCS.091); checks (M.TSC.009/.010); getaddrinfo half gone (M.DOCS.070) |
| OR69, .a | E | midnight window (M.SRC_SENS.037), `res` meaning (M.SPEC.021), C12/C13 owner question (M.DOCS.067), pin by owner call (M.DOCS.070) |
| OR70, .a | E | hotspot password (M.DOCS.080); power-cycle recovery (M.DOCS.082); no-write rule (M.DOCS.082); UART error-32 (B26); `ResetErrors` Failed/global (M.TEST_UNIT); no negotiation (M.DOCS.076) |
| OR71, .a | E | workflow (M.DOCS.093), one repair write per boot, `MemFree` (M.GEN.008), consistent GET snapshot, "never will" gone (DEVICE_REFERENCE) |
| OR72, .a | E | F18 degradation; FRAM hold kept; concurrent `ResetErrors`; resize dropped; DNS history shown; dead-man's switch (M.DOCS.088); dev quirks rule gone (M.DOCS.077) |
| OR73, .a | E | Pico W only (M.SPEC.149) |
| OR74, .a | E | req 18 a wiring fact (M.SPEC.153 via A.U15.39) |
| OR75, .a | E | construction → setup → tasks → timers → NTP last (M.GEN.006) |
| OR76, .a | E | `CalLight` code and label (M.SRC_SENS.072-.081, M.GEN.062) |
| OR77, .a; OR79, .a | E | off-subnet spoof attempted, skip only with recorded reason (M.HW_BENCH.072) |
| OR78, .a | E | no variant literal (M.TSC.110); O-05 (b) and O-28 |
| OR80, .a; OR95, .a | E | datasheets submodule after the owner's push step (M.PROC.018, M.DOCS.068) |
| OR81, .a | E | `disallow_any_explicit` in three passes (M.TOOL.032/.079, M.DOCS.103) |
| OR82, .a; OR83, .a | E | owner/agent labels; L06 (M.SPEC.016), L44 (M.TOOL.030), L51 restored |
| OR84, .a | E | `run_setups()` (M.SRC_CORE.015, M.GEN.006) |
| OR85, .a | E | persistent staging under `build/`, clean at start (M.SCR.066, M.SCR.019) |
| OR86, .a | E | `--no-autostart` and its image name (M.SCR.065-.068, M.GEN.019) |
| OR87, .a; OR88, .a | E | tags and the CRC-16 wording (M.SRC_CORE.091; O-23 form) |
| OR89, .a | E | any client mix; frozen-port twins ad hoc; deferred blocking-call goal (M.DOCS.081, BACKLOG); `fram.setup()` result used (M.SRC_CORE.092); SCD30 readback fail refuses |
| OR90, .a; OR92, .a | E | SCD30 prerequisite fixture split, start sent at most once (M.HW_DEV.020, M.TSC.212) |
| OR91, .a | E | UART general API kept with contract tests; test collects baseline-only (M.SCR.015; O-27) |
| OR93, .a | E | `.gitignore` outside writers named (M.PROC.019) |
| OR94, .a | E | (11) inputs cleared (M.WEB.015/.054); (12) labels (M.SRC_NET @web groups); (13) staleness and ages; (14) clickable codes, look unchanged (M.WEB.016; nodata span on the D3 review list); (15) `UnixTime` (M.GEN.008) |
| OR96, .a | E | alphabetical order and its lint check (SRC/SPEC/WEB order changes, M.WEB.070) |
| OR97, .a | E | BackupTS/RestoreTS specials, VOC state code (M.SRC_SENS.064/.065), Wi-Fi terminal LED pattern (M.SRC_NET.077) |
| OR98, .a; OR99, .a | E | FRC readiness code, RAM only, saturating, config parameters (M.SRC_SENS.049/.051) |
| OR100, .a | E | Altitude help and warning (M.WEB.054 cases, SCD30 tag) |
| OR101, .a | E | twelve bugs; `SysUptime` from ticks (TickSeconds) |
| OR102, .a | E | (3) Synced cleared (M.SRC_NET.055); (5) LED busy Failed; (6) boot-failure code (M.SRC_CORE.006); (7) NODATA (M.SRC_NET.009); (8) Wi-Fi uptime with hotspot; (9) drop logging; (10) repro retired |
| OR103, .a; OR105, .a; OR110, .a | E | `COUNTER_CAP` ≤ 2**30 − 1, check-before-step; `LastSyncAge` 0xFFFFFFFF gone (M.SRC_NET line 898) |
| OR104, .a | E | password unrestricted; `TickSeconds` primitive in base classes |
| OR106-OR108 (.a) | P | A-L/A-C phase — this work |
| OR109, .a | E | SGP40 `_measure_command` in the session hold (M.SRC_SENS.067/.068); BMP3XX 1-3600 s |
| OR111, .a | P | this end-state check |
| OR112, .a | — | sizing and `TCP_NODELAY` overtaken by OR114.a; phase-C test kept (M.HW_BENCH.075) |
| OR113, .a | E | boot bus clear and recovery ladder (M.DOCS.081, SPEC F.2) |
| OR114, .a; OR115, .a | E | modlwip override (M.TOOL.039, M.SCR.067), no `TCP_NODELAY` (M.SRC_NET line 2295), hammer tests (M.TEST_UNIT.001); O-26 |
| OR116, .a; OR123, .a | E | `crc` key per `uart_link`, dev ships none, L3 CRC16 script, L4 per mode (GEN/HW merges) |
| OR117-OR122, OR124 (.a) | E | `resetconfig`/`erasefram`, controlled shutdown, watchdog ownership, same envelope, no dialog, near-misses Invalid (M.SRC_CORE.009-.011, M.SRC_NET.121, M.GEN.015, M.WEB.054) |
| OR125, .a | E | twin runner `--test-*` flags, off by default, checked (M.TWIN.051, M.TSC.220) |
| OR126, .a | E | `main()` keywords kept (M.GEN.006); debug-level note (A.U19.23); reboot/bootloader on the sequence; LED check kept; corrections (M.DOCS.099) |
| OR127, .a | E | secret scan excludes `arduino/` (M.PROC.020) |
| OR128, .a | E | `LastTaskEnd` (M.GEN.008, M.SRC_NET.170, M.WEB.012) |
| OR129, .a | E/P | dependency refresh in U0, re-check in U37 (M.PROC.008-.013, .031) |
| OR130, .a | E | one escalation feed (M.SRC_CORE, M.TSC.155) |
| OR131, .a | E | upstream stubs in `ext/typings/microdot/` (M.GEN.050) |
| OR132, .a | E | AA tokens (M.GEN.062) |
| OR133, .a | E | exit 2 for usage/setting errors (M.SCR, M.DOCS.052) |
| OR134, .a | P | test schedule — A-C2's work order; M.PROC.033 range (O-24) |
| OR135, .a | P | review package — M.PROC.035 (O-25) |

## G. Limits

- The OR table's E verdicts rest on the merged changes named (located by targeted search over all 1,865 Change texts
  and the cited merged changes read); a row is marked honoured when its stated end-state facts are written in a merged
  change and no merged change states the opposite. Exhaustive per-row re-derivation of every M file is Part R's trace.
- Per-file adherence was read in full for the eight tests_js files only; every other file's end state was checked through
  its merged-change texts (sections B-E). M.PROC.032's first U37 pass remains the file-by-file backstop.

## Summary

28 findings: 7 H (O-01, O-05, O-06, O-07, O-09, O-26, O-27), 17 M (O-02, O-03, O-08, O-10, O-11, O-12,
O-14 to O-22, O-24, O-25), 4 L (O-04, O-13, O-23, O-28). No owner question: every finding is settled by an owner row, the register or
AC_NOTES. M-IDs to amend: M.WEB.052, .053, .054, .057, .058, .059; M.SCR.039, M.SCR.015; M.TWIN.019, .044, .052,
.062; M.TEST_UNIT.127, .279; M.SPEC.054, .064, .070, .075, .082, .116, .129, .136 (and placeholders .111, .144);
M.DOCS.008, .076, .078; M.SRC_CORE.013, .091; M.SRC_SENS.017, .071; M.HW_BENCH.075, .076, .080; M.HW_DEV.122; M.WEB.060;
M.PROC.033, .035; M.GEN (`wozi.toml` header).
