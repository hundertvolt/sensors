# U23 lanes X and Y: gaps, conflicts and unplaced facts (draft for the lead, 2026-10-13)

Read against `wt-u23api` at `96ecee1` (`audit/u23-w1`) and D's final `3c23b1b` (`audit/u23-d`, see F), `lead_todo.md`,
the plan, the rulings, `pk/U23_steps.md` and `audit/review/{answers,decisions}.json`. Fact numbers are the draft
briefs' (X1-X46, Y1-Y10).

## A. Already present in the doc (only the named remainder is written)

- A1. The browser's doubles-only float gap: H.4 `:6633-6634` and A.8 `:1080-1081` already state it (no actor). New in X16:
  only the resolution clause and A.U23.49's actor "(agent, 2026-09-30)".
- A2. Step 73 (b)'s bootstrap tag "(agent, 2026-08-26: it is a thin bootstrap)" is at H.2 `:6578`; X12 keeps it.
- A3. The owner's bound rule is already present: B.14.4 `:2216-2217` ("... not a larger bound (owner, 2026-09-30)") and
  Part N `:10357` ("never a larger bound (owner, 2026-09-30)"); X2/X3 keep each word for word.
- A4. DEVICE_REFERENCE "## Clearing the error logs" `:148-154` (U19's text, the `HTTPDropped` clause included); only Y5's
  closing sentence is new.
- A5. G.2 `:6448-6456` already names the generator-bounds pin (`test_definitions_js_mirrors.py`, the shape corpus), the
  `buildgen/` source facts and the "one change" rule; X8 adds the new pairs only.
- A6. H.5.1 `:6720-6722`'s owner decision on the `decimals` hint (owner, 2026-09-12, `12a616a`) is step 32's Stage 1;
  X20 adds the fold sentence after it.
- A7. A.8 `:1011-1016` (the LED busy `descr`) and H.6 `:6790-6793` (the `LightCmdLED` retry wording) need nothing at U23.

## B. Facts not placed (no U23 target; the lead decides if any is wanted now)

- B1. `UnixTime` in A.8's `/status` paragraph (`:924-956`): A.U23.22 stages its doc row at U36 with A.U11.05's table; the
  paragraph lists fields "with meaning beyond their name", not every key, so nothing is false today.
- B2. H.6's clickable-code sentence (step 33, Stage 2 U36; the code is U23's, T).
- B3. CalLight's tones in M.1.5's table (`:9708-9713`) and H.5.1's `codes=<table>` paragraph (`:6754-6757`): A.U23.20
  stages the doc at U36; nothing false (the texts are unchanged; `tone` is a new optional key).
- B4. H.4 "PUT/GET error handling" (`:6624`) and the H.4 mock-paragraph rewrite beyond A-25's corrections: U36.
- B5. H.2's folder map (`:6534-6543`) lacks `build/generated_src/api/`: incomplete, not false.
- B6. Browser Back through the sections (owner, 2026-10-01: 'make the "back" function of the browser work ...', the
  `website-accessibility` answer; S's history): no step names a doc site; H.4's "Page model" row (`:6609`) stays true.
- B7. Not doc facts (the scan record and the register, the lead's): M's F1 (the mock accepts a PUT without
  `Content-Type`), M's F2 (`composeMockData()`'s healthy-zero fallback), B's `--color-neutral-bg` 4.16 and
  html-validate's unknown-attribute gap, `build_device_websites.sh --stage-only` never wiping `build/staged_html`;
  OF-136's closure records; OF-111 (A-11 as amended: nothing at U23 unless the owner answered (b) before D's final).

## C. Conflicts between sources (a recommendation each; the lead decides)

- C1. The website-confirmation date. Step 22's DEVICE_REFERENCE sentence and step 30's A.8 clause write "(owner,
  2026-10-02)"; the record (`answers.json` `dns-fallback-clear-confirm`, at 2026-10-01T21:41:25Z), D1's code comment
  (`buildgen/definitions.py:60-61`), D1's commit body and plan A-4 all use 2026-10-01. Recommend 2026-10-01 with the
  quote (X29, Y5).
- C2. "Codes clickable" in the divergence row (X36). A.U23.45 tags it "(owner, 2026-09-29)" — the errno/wrnno pills
  (A.U23.43 quotes "don't change the current look of the website, make the codes clickable", owner, 2026-09-29); the
  status codes, `ResetReason` first, are the owner's 2026-10-02 word ('Good, and make the numbers clickable in the
  website like the errno and wrnno numbers.', `reset-reason-codes`). Recommend both, each with its codes.
- C3. Doc parts the actions stage at U36 but `lead_todo.md` relays to X: H.1's AA statement (A.U23.44 "H.1 ... (U36)"),
  H.4's "Rendering safety" rule (A.U23.40 "(U36)"), H.3's hook list (A.U23.42 "(U36)", while plan A-25 lists H.3
  `:6595-6601` for U23). Recommend writing them at U23: the code U23 added cites these sections for exactly these facts
  (`eslint.config.js:121` → H.4, `html/style.css:378` → H.4, `:557` → H.3), and A-25 already reopens H.3 and H.4. A
  "no" drops X9 and X14; X13 stays (A-25). Settled since: the mock's stateless-command gap, which `lead_todo.md:63`
  relayed, stays U36's (A-10; the lead's close-prep ruling, `lead_todo.md:77`), so X16 leaves it out.
- C4. Agent decisions the owner approved on the review page. `lead_todo.md:49` and A.U23.45 write the favicon
  "(agent, 2026-09-30)", while `favicon-inline` is "ok" (2026-10-02); the failed-Apply marking is "(agent, 2026-08-22)"
  in `js/render.js:266`, `apply-failure-marks-fields` "ok" (2026-10-01); `ContMeas` with no state "(agent,
  2026-09-30)", `website-display-details` "Fine, ..." (2026-10-02). Recommend SPECIFICATION.md's existing form "(agent,
  <date>; owner-reviewed, <date>)" (`:6299`, `:9812`); X15, X19, X36 are drafted that way.
- C4a. The stripe text `html/style.css:314-316` removed by `e6a901e` carried no actor tag (the lead's close-prep
  ruling, `lead_todo.md:78`); X15 takes "(owner, 2026-08-21)" for the two-level stripe from A.U23.45 alone. If the
  lead finds no owner record for it, the clause is the agent's (date of the introducing commit, `git log -S`).
- C5. The DNS fallback Clear's actor "(owner, 2026-09-26)" (A.U23.45, from an OR record before the review page) cannot
  be checked in `answers.json`; `dns-fallback-setting` ("ok", 2026-10-02) covers the setting, not the button. Kept as
  A.U23.45 states it (X36).
- C6. Step 32 Stage 3b writes "carries `decimals` (2 or 3, a sensible number for the value)"; the tree emits SCD30 `CO2`
  0, `Temp`/`Hum`/`WetBulb`/`DewPoint` 1, `TempOffset` 2, the default 2, and ISL29125's tagged 3-4 (ruling A-17). X20
  writes the tree's derivation, not "2 or 3".
- C7. `web.default_decimals`: the owner wrote "e.g. limit to 2 or 3 digits"; 2 is the agent's pick (X4's Basis says so).
  `tests_scripts/test_buildgen_definitions.py:364` asserts the literal `2` with no `@tunable` tag, a mirror N.1 wants
  tagged and listed as a further Site; that file is D's: tag it (then X4's Sites gains it) or read `_DEFAULT_DECIMALS`.
- C8. `l1.lwip_host_spin_round_max_us`'s Basis (8,536 µs under load) and Margin ("2.3× the slowest round here") are
  single-round figures; `lead_todo.md:41-42` asks only the Dependants change, so X2 keeps them. Optional: add the window
  figures of `4f60381` (slowest windows 1,154-1,294 µs). B.14.4's "8.5 ms" stays true as the single round's worst.
- C9. D's final is not in `audit/u23-w1` (`96ecee1`): its `_put_status()`, the reference's `unavailableMarker`/
  `unknownCodeText` and the rule `api.wire-text-not-string` are staged, uncommitted, in `wt-u23d` (read via
  `git diff --cached`). X41-X43 and Y8 rest on that diff until the merge.
- C10. Step 30's clause says the website confirms "any system command (H.4; owner, 2026-10-02)"; the owner's words cover
  the system commands and the error reset, and the DNS Clear's own dialog is the agent's proposal the owner answered
  "Fine, ..." (`dns-fallback-clear-confirm`'s decision text). X29 names all three, each with its actor.
- C11. Plan rows' "U23 part" for steps 31, 33 and 73 is "none @U23 (U36)", yet each carries A-25 corrections U23 makes
  true or false (X17-X19, X33, X34): the briefs treat only the false sentences as U23's, the rest U36's.
- C12. H.8's complexity figures moved twice during wave 1 (`lead_todo.md:15`: 41 → 37 after M1; `:57-58`: tree maximum
  22 at `js/render.js:196`); X28 writes only the lead's final values.
- C13. Open at W1 (`lead_todo.md:74-75`): D's final adds `unavailableMarker`/`unknownCodeText` to the reference (staged
  in `wt-u23d`), while M's mirror test reads the marker and the unknown-code text from `src/` directly
  (`tests_scripts/test_js_api_mirrors.py:112-127`). X8 and X41 describe whatever the merged tree does; the lead's W1
  decision goes in the WAVE-2 FACTS.

## D. Tunables rows whose docs location is unclear

- T1. S's production JS tags (plan: `web.poll_backoff_max_ms` = 60000, `web.device_watch_interval_ms`): their Sites are
  in `js/` only, and N.3 has no website table (firmware, build, L0, L1, L2, L3/L4, CI, runners). Precedent:
  `web.outer_cap_s` (`src/` plus its `js/poll-manager.js` mirror) sits in Firmware (`:9979`). Recommend Firmware (the
  frozen website ships in the firmware image). Their Basis: A.U23.05 drafts `web.poll_backoff_max_ms`; the
  `website-unattended` decision ("The device check runs every 60 s; failed polls back off to at most 60 s.", "ok",
  2026-10-01) supports "(agent, 2026-09-30; owner-reviewed, 2026-10-01)" for both.
- T2. The plan's tag names for S are expectations; X writes the names S and S3 report.
- Clear: `web.default_decimals` → Build table beside `web.poll_interval_ms` (`:10100`, same file);
  `l1.lwip_host_spin_window_rounds` → L1 beside the `l1.lwip_host_*` rows (`:10352-10358`); `l0.live_*` → L0 beside
  `l0.live_twin_*` (`:10156-10165`).

## E. Docs outside both lanes' sets, and checks done

- E1. `digital_twin/README.md:799`: "`dev`'s own frozen website (7579 bytes, 168-483 bytes larger than the other five
  devices')" is a size U23's site growth (icon, new modules) will make stale; plan section 4 gives `digital_twin/` to no
  lane. The lead reads the rebuilt sizes and decides (Y could take the one line).
- E2. `CLAUDE.md:497` "`js/definitions.js`'s ~37-line `@typedef` run": 50 lines at `8fff76f`, 51 at `96ecee1`, so stale
  before U23. CLAUDE.md's working agreement says a stale fact is fixed in the session that finds it; Y owns CLAUDE.md.
  Recommend Y corrects the count with "No meaning change" (Y9).
- E3. `README.md:281` "All five CI-covered checks" stays true only if Y1 marks `lint:html:built` as local.
- E4. Checked with nothing false found: `tests_hardware/README.md` (its dispatch list `:1566-1571`),
  `digital_twin/README.md` `:188`, `:453` (`build_website.sh` still builds `frozen_html.py`), `README.md:305`, SPEC
  A.9 `:1109-1155`, E.1 `:4184`, `:4206` (the malformed-TOML case still exists), C.5.2.1, H.4's "Definitions file"
  and "Poll coordination" rows at `96ecee1` (X31 is wave 2's).

## F. After D's final (`audit/u23-d` at `3c23b1b` = `411bbb8` + `3c23b1b`) and the lead's rulings R1-R8

Outcome of each item above (the briefs carry the result):
- B1 → placed: X45 writes `UnixTime` in A.8's `/status` paragraph, the lead asking for D's API end states.
- C1 → R1 (2026-10-01; X29, Y5). C2 → R2 (both dates; X36). C3 → R3 (X9, X13, X14 written now). C4 → R6 (X15 names
  `apply-failure-marks-fields` and `favicon-inline`; X19 `website-display-details`). C6 → R4 (X20). C7 → R5, done by
  `3c23b1b` (`test_buildgen_definitions.py:377` tagged): X4 lists both Sites. C9 → resolved: X41-X46 and Y8 cite the
  committed `411bbb8`. T1 → R7 (X38: beside `web.outer_cap_s`, `:9979`). E1 → R8 (Y10; `digital_twin/README.md` joins
  Y's set, listed in no other `files_*.txt`). E2 → R8 (Y9 corrects the count to the one measured on its base).
- C13 still open: D's final adds `unavailableMarker`/`unknownCodeText` to the reference (`411bbb8`,
  `buildgen/api_reference.py:202-203`) while M's mirror test reads both from `src/` (`lead_todo.md:74-75`, the W1
  decision). X41 writes the reference keys; X8 describes the mirror test as merged.

New:
- B8. D's three status-row facts for Y (the Device Clock row, the notification `TS` row "Last Cycle Time",
  `ResetReason`'s "click it for its meaning") have no doc target: DEVICE_REFERENCE.md, README.md and SPECIFICATION.md
  describe no Status-page row label (checked: no "Last Trigger", "Device Clock" or "as a numeric code" in any of them).
- C14. A.8 `:921-923` "`sensors` keys are `<source>_<field>`" and `:954-955` "`SGP40_BackupTS`/`SGP40_RestoreTS`" are
  false on the wire, and were before U23: `GET /status`'s `sensors` holds one object per source
  (`src/asy_webserver_service.py:694-699`; the generated `_sgp_maintenance_status_*()` returns
  `{"BackupTS", "RestoreTS"}`).
  D's maintenance `path` (`[source, field]`) makes the page read it as sent; the definitions key stays
  `<source>_<field>`. X46 corrects both sentences (smallest true text); for the scan record, a doc fact wrong since
  before U23.
- C15. X44 (A.8: which definitions keys are field facts and which page-only) states a classification no sentence
  contradicts today; it is written because D's "Facts owed" lists it, not as an A-25 correction.
- B9. Not doc facts, from D's report (the lead's): the error-contract row for `api.wire-text-not-string` (paste into
  `tests_scripts/test_buildgen_error_contract.py`); scan finding 3 (`src/asy_webserver_service.py:642` detects the
  marker by `"error" in values`; inherently safe today, to park in the register).
- A8. Already present: the unavailable marker's shapes on the wire (per module on `/sensors`, per field on the flat
  routes), D's API end state, are in A.8's GET shapes (`:908-910`); nothing to write.
- Pending on wave 2 only: X27-X40, Y4-Y7, Y10 (the website sizes come from the lead's rebuild on `<W3>`).

## G. Wave 2 folded (API3 `9a8700f`: T final `f28431e`, C final `f6a7cae`, S2 `437e51f`; S3 and S final pending)

Placed now: X27, X29-X31, X33, X34 (shell), X35, X36, X39, X40 (READY-W2), X47-X56 (new: three `web.*` rows, the
`l0.section_render_wait_ms` row, the site-functions sites, H.1's check, H.3's end state and guard, H.4's Apply texts,
H.5's shape hints, R11's status rows in H.5.1), X57 (optional); Y4-Y7 (READY-W2; Y7: nothing to write). Every doc line
is unchanged from `96ecee1` to `9a8700f`. Earlier items: B4 partly placed (X54 adds the Apply texts to the
"PUT/GET error handling" row; the rest of that row stays a later unit's); B6 placed as X57 if the lead keeps it; B8
placed in Part H by R11 (X56).

Still pending:
- S3/S final: X34's `tests_js/_expected_display.js` and the `field-format.js` reason (the file is absent at `9a8700f`),
  X37 (the full ceiling), X38's `l0.live_*` rows and any tag S renames or withdraws, Y3's addendum (S's config files).
- The lead's edits (`wt-u23L`): X50's third site (the rename `l0.a11y_render_wait_ms` → `l0.section_render_wait_ms`;
  until it lands, `test_tunables_register.py` reads two IDs); X53's guard is red at `9a8700f` on `js/templates.js:620`
  (the lead's escaped-selector edit); X8's `DNS_LABEL_MAX`/`DNS_FALLBACK_MAX` pins; F4's shared plain-object check
  (if made, a G.2 entry nobody owns yet: X's, if the lead says so).
- The lead's final: X28 (the four ESLint ceilings), X35's count on `<W3>`, Y10 (the rebuilt sites' `GET /` sizes).

New gaps:
- G1. X48/X49 take "(agent, 2026-09-30; owner-reviewed, 2026-10-01)" from `website-unattended` ("ok"; its decision text
  names the 60 s watch and the 60 s back-off cap): R6 applied to a tunables Basis cell, which N.1's forms do not list;
  the lead confirms or X writes S's plain "estimated (agent, 2026-09-30)".
- G2. X47's Basis needs a commit (N.1: "estimated (agent, <commit that introduced the literal>)"); T wrote "the U23
  timestamp-age action": the brief names `10005b1` (T1, the literal's first commit).
- G3. X51: C measured the slowest whole site-functions case at 59 ms over 2 runs; the two rows stay "estimated" (their
  Basis is `render.test.js`'s), unless the lead wants a measured Basis naming both files.
- G4. X50's Basis is T's 59 ms (ruling I-12); C's 34 ms over 36 × 2 is the faster figure, not written.
- G5. X32 is already true at `9a8700f` (`collectGroupBody()` `js/render.js:272`, the compare sites `:423`, `:472`):
  nothing to write.
- G6. X57 (H.4's "Page model" gains the `#<key>` history, owner, 2026-10-01): no step or ruling names it; written under
  R3's "docs hold current state" only if the lead keeps it.
- G7. H.8.1's worked example (`field-format.js`'s `FormattableField`) still holds at `9a8700f` (`js/field-format.js:9`);
  step 58's resolved line is satisfied, nothing to write.
- G8. Not doc facts (the lead's records): S's scan #5 (a reflash before the first watch, open, a later build-chain
  unit), C's F3/F4, T's two findings (the mock's unpinned DNS constants, `generated-definitions-render.test.js`'s
  untagged bound, now tagged at `:14`), the legacy ledger's dev SHTC3/MPRLS (asked in session) and ISL29125 entries
  (decided).
- G9. Process: drafting this fold, I wrote one temporary file in `S/u23/` (`.xblock_w2.txt`) and deleted it at once;
  nothing else outside the five drafts was written.

## Lead rulings (agent, 2026-10-13; each conservative, listed for owner review)
- R1 Confirmation dialog date: 2026-10-01 (`audit/review/answers.json` `dns-fallback-clear-confirm`, at 2026-10-01T21:41Z).
  The step texts' 2026-10-02 is a plan slip: the scan record names it; X writes 2026-10-01.
- R2 Clickable codes: two decisions, each cited with its own date (09-29 errno/wrnno, 10-02 ResetReason).
- R3 H.1 AA, H.4 sink rule, H.3 hooks: X writes now what U23's code makes current (code cites them; docs hold current
  state); U36 keeps whatever goes beyond U23's code.
- R4 Decimals: X writes what the tree emits (0, 1, 2; ISL29125's tagged 3-4); step 32's "2 or 3" goes to the scan record.
- R5 `test_buildgen_definitions.py:364`: relayed to D (tag the literal, or D says it is not that tunable).
- R6 "(agent, D; owner-reviewed, D2)": the SPEC precedent (`:658`, `:1114`, `:6299`, `:9812`); only where an owner-review
  record exists, which X names in its report.
- R7 JS-only `web.*` tags: rows next to the existing `web.*` rows of N.3 (`web.outer_cap_s` already lists a JS site).
- R8 `CLAUDE.md:497` "~37-line": Y corrects it to the count measured on its base (the stale-fact rule).
  `digital_twin/README.md` joins Y's set for the website size (disjointness checked at launch).
- R9 X46 (C14): X corrects A.8's `<source>_<field>` text to the nested wire shape (stale fact, pre-U23; the scan record
  names it as a doc finding fixed at U23).
- R10 X44 (C15): kept, one or two sentences in A.8: the split is current state that D's code introduced.
- R11 B8: website-facing facts go to SPEC Part H (CLAUDE.md), so D's status-row facts move to X (Part H's status/system
  page text); Y writes them only where DEVICE_REFERENCE.md already describes that page.
- R12 B9: the lead's (row via the helper; `:642` in the close records). C13 waits for W1.
- R13 G1: Basis cells use only the forms N.1 lists; an owner review goes in that form only where the owner decided the
  value itself, otherwise the agent form stays (no new form invented in N.3).
- R14 G2: no Part N row or doc line cites a lane commit hash (the squash drops it; the U22 basis-hash slip): cite
  "(agent, 2026-10-13)" or the unit's final hash once known (the lead fills `<U23>` at the close).
- R15 G3: a new site keeps the row's Basis when that Basis already covers it; C's 59 ms whole-section maximum enters the
  Basis only if it does not.
- R16 G6: X57 is written (the page now keeps a hash history with Back; current state belongs in H.4).
