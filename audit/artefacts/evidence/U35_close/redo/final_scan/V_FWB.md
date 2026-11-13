# V_FWB: verification of FWB-1 to FWB-6 (plus FWB's Notes)

Release `S/wt-final` at `590cffcf`, baseline `25caf528`. Read-only; every repo view filtered.

## Summary table

| id | verdict | one-line reason | fix size (lines) | touches device behaviour? |
|---|---|---|---|---|
| FWB-1 | CONFIRMED-OWNER | True. Apply re-reads the section, then sends every untouched toggle or dropdown another client changed, which reverts that client's change. A web test pins this as deliberate WYSIWYG ("the visitor wants exactly those"), with no owner decider. FWB's fix is incomplete: the post-write GET re-baselines the same way. | ~15-20 in `js/render.js`, plus 2 web tests and the H.4 row (or 1 doc line if kept) | n (firmware unchanged; it changes which PUTs the page sends) |
| FWB-2 | CONFIRMED | True. The residue of the removed 1,200 ms wait. Owner 2026-11-03 "Yes keep it simple" was recorded as "a log line that cannot get its argument tuple on a full heap raises, and the restart and watchdog backstops take it". | ~4 code + 1 SPEC clause (F.2, SPECIFICATION.md:6660) | y, edge only (heap exhausted while the escalation line is formatted: a watchdog reset with the same recorded code, no config flush) |
| FWB-3 | CONFIRMED (smaller fix) | True, and every producer is a build-checked int. Drop only the three audit-added clauses (`:924`, `:933`, `:935`). The pre-audit ones (`:234-235`, `:431`, `:443`, `:916`, `:922`) are MINOR. | ~3, plus one Class B entry in `UART_C_PORT_CHANGELOG.md` | n |
| FWB-4 | CONFIRMED | True. `_Holder` and `_RequestLike.sock` are typing-only, with no reader in `src/` since the `.hold()` mechanism was removed on 11-03 (`41da2a61`). | 4 | n |
| FWB-5 | MINOR | True and unreachable. But this is pre-audit code in 4 modules: removing it grows the diff against main for a few bytes. | ~12 (not worth it) | n |
| FWB-6 | CONFIRMED-OWNER (colour only); rest REFUTED | Errcount count colour: no decider, and Q10 does not cover it. "Resolution:" hint: owner "Fine" (review item `website-display-details`, 2026-10-02). `console.error`: the pre-audit poll diagnostic, relocated, and not on the page. | ~6 (CSS `:469-481` plus a counter>0 row attribute) | n |

## Per finding

### FWB-1: CONFIRMED-OWNER
- **Checked.** I traced the click handler end to end:
  - `js/render.js:202-207`: `refreshAfterApply()` → `fetchOnce()` (`:626-637`) → `paint()` → `:699-702`. For an existing card, `baselines.set(card, values)` and `updateFieldGroupValues()`.
  - `js/templates.js:930-948` repaints readonly values and number/string captions/placeholders only. Its own doc (`:922-923`) says "a toggle or select changes only by the user or by resetControl()".
  - Then `collectGroupBody(card, group, baseline())` (`:261-274`) reads the controls:
    - a plain toggle is sent when its shown state differs from the fresh baseline (`:422`);
    - a plain enum is sent when its selected value differs (`:471`);
    - number/string inputs are sent only when typed into (`:467-469`), so they are unaffected.
- **Precisely what happens to an untouched control.** Take a toggle or preselected dropdown that another client changed after this card was built (`templates.js:85-107` and `:353-359` paint it from the build-time value).
  1. The re-read makes the other client's value the baseline.
  2. The control still shows the build-time value.
  3. The two differ, so the control goes into the PUT body with the page's stale value. This happens even if the user changed nothing at all and pressed Apply.
  4. The device stores it (a real change for the config store, so a flash write).
  5. After the PUT, `resetToBaseline()` (`:519-527`) repaints that control from the post-write GET, which now reports the page's value. So the page shows the revert as success.
- **Pre-audit (`25caf528` `js/render.js:188-201` and `:247-254`).** The baseline was the build-time `currentValues`, updated only for submitted keys answered Valid/Unchanged. GETs never touched it (`:320-334`), so an untouched control was never sent.
- **Deliberate, but agent-chosen.** `tests_js/render.test.js:2044-2061`: "sends one GET of the section before the PUT, and a toggle and dropdown another client changed". Its comment reads "The page still shows On and x1; the visitor wants exactly those", and it expects `PUT {MeasEnabled: true, Oversampling: 1}` with no user input.
- **Origin.** U23 `9bf22747` (2026-10-13), action A.U23.15 citing G7/R43 / WEB.S10: "the baseline is refreshed from the server's post-write GET instead of being frozen at first render". WEB.S10 is an agent "Latent" seed (archive `PROJECT_AUDIT_PLAN.md`, WEB seeds).
- **Owner record.** I found none:
  - the only owner row on these Apply items is OR94.a (11), which covers clearing inputs and resetting commands;
  - the review page's `FOLD_ANSWERS.md` has no item on it;
  - it is not among U14's Q10 choices;
  - SPECIFICATION.md H.4's "PUT/GET error handling" row states it with no decider, and the "Divergences from the legacy site" row omits it.
- **Correction to FWB.**
  - **What the page shows.** The page does not show toggles and selects "as they were at the last GET". No GET ever repaints them. They show the card's build-time value, or for a submitted field, the value it was reset to after its own Apply.
  - **The smallest fix is incomplete.**
    - Deleting `:204-207` only narrows the window. The post-write GET of any Apply (`:146` → `:701`) still re-baselines every card of the section, including sibling cards (for example `/sensors`, where "each card applies independently") and the unsubmitted fields of the same card, without repainting them. The next Apply there reverts in the same way.
    - The live `status` section re-baselines on every poll too, though its writable fields are dispatch-only today.
    - A fix that restores the pre-audit rule would:
      1. delete `:204-207`;
      2. stop re-baselining existing cards at `:701`;
      3. put back the pre-audit "stored keys become the baseline" update in place of `resetToBaseline()`.

      That is about 15-20 lines, plus the two tests at `render.test.js:2044-2075`.
  - Website only, firmware unchanged.
- **Owner question:** Should Apply send only the toggles and dropdowns the user changed (pre-audit), or set every toggle and dropdown the card shows, even ones another client changed since the page loaded (current, agent-chosen)?

### FWB-2: CONFIRMED
- **Fact.** `src/asy_system_service.py:544-550` is a `try` around the two `err_s()` calls, with `except MemoryError` → `self.pr.err("Reboot entry not written:", e)`.
  - `:538` (command gate) and `:539` (`write_reset_record`) precede it.
  - The loop's own `except Exception` is at `:564-566`.
- **History verified.** At `72b12815`, `:554-558`, the arm wrapped `await asyncio.wait_for_ms(entry, _ESCALATION_ENTRY_WAIT_MS)` with a `TimeoutError` arm, and its comment read "building the entry, its wait or its write". `22477130` (2026-11-03) removed the wait and kept the arm.
- **What the arm still catches.** `err_s()` already catches its own FRAM write's `MemoryError` (`src/asy_print_log.py:281-290`). What is left is the call's `*args` tuple and `print` in `_line()` (`:86-92`), so the arm guards a log line on a full heap.
- **Decisive citation.** Owner, 2026-11-03 06:00: "Yes keep it simple". The rulings file records this as "a log line that cannot get its argument tuple on a full heap raises, and the restart and watchdog backstops take it".
- **What removing it changes.** In that edge case, the reset comes from the watchdog, with the reset code already written at `:539` (P7 holds). `_reboot()`'s config flush and storage pause are skipped. No test pins the arm (`git grep "entry not written"` finds only the source line).
- **Smallest fix.** Drop the `try`/`except` (keep both `err_s()` calls) and the F.2 clause "a `MemoryError` building it still arms the reset" (`SPECIFICATION.md:6660`).

### FWB-3: CONFIRMED, smaller fix
- **Fact.** All sites verified in `src/asy_uart_comm.py`:
  - `:234-235`, `:431`, `:443`, `:916`, `:922` are pre-audit (`25caf528` `:215-216`, `:239`, `:243`, `:374`, `:386`);
  - `:924`, `:933`, `:935` came from `c11ca0aa` (U17, 2026-10-08).
- **Producers.** Every producer is an int:
  - `TransferLimits` is generated from int constants plus `_checked_int` (`buildgen/codegen.py:553-561`, `buildgen/validate.py:914`);
  - the UART bus ints are build-refused otherwise (`validate.py:810-815`);
  - the command ids are constants (`asy_uart_link_driver.py:133-182`).
- **Ruling.** Owner, 2026-10-27: "if the check you remove really solely covers typing breakages and nothing else it can go"; PICTURE M4.
- **Worth it.** Dropping the three audit-era clauses shrinks the change against main. Reworking the pre-audit ones grows it for no runtime gain (MINOR). Any change to this module needs a Class B line in `UART_C_PORT_CHANGELOG.md` (the file exists; CLAUDE.md requires it). No wire change.

### FWB-4: CONFIRMED
- **Fact.** `src/asy_api_response.py:24-25` and `:33-34`, inside `if TYPE_CHECKING:`.
- **No users.** `git grep` over `src`, `tests`, `digital_twin`, `buildgen`, `tests_hardware`, `tests_scripts` and `ext` finds no `.sock` read and no `.hold(` call in `src/`.
- **History.** `git log -S ".hold("` shows `f5c82557` (U19) added the mechanism and `41da2a61` (2026-11-03) removed it; the Protocol member was left behind.
- **Smallest fix.** Delete `_Holder` and the `sock` property.
- **Related, same root, in tests only.** These are noted here, not as findings (do not drift into tests):
  - `tests_hardware/device_scripts/allocation_need_per_source.py:52-58` keeps `_NoopHolder`/`_ProbeRequest.sock`, with a stale comment "the static route hands its opened file to hold()";
  - `tests_scripts/test_fram_less_boot.py:33-35` keeps `_Holder`.

### FWB-5: MINOR
- **Fact.** `ConfigManager._get_values()` returns `[current[key] for key in schema_names(keys)]` or `None` (`src/asy_config_manager.py:357-367`), so the `len()` clauses are unreachable.
- **Sites, all present at baseline.**
  - `asy_notification_service.py:217-219`;
  - `asy_ntp_client.py:183`, `:283`, `:412` and `:428`;
  - the constants `:88-89`. Only `_NTP_STR_COUNT` (`:87`) is audit-added, with the DNSFallback read.
- **Why not worth it.** This is a 4-module sweep of pre-audit code that grows the diff against main, for a few bytes of bytecode.

### FWB-6: CONFIRMED-OWNER for the errcount count colour; the other two items REFUTED
- **Q10 (owner, 2026-11-06 13:17: "Question 10: Keep all of it").**
  - It covered exactly the ten agent "choice" lines of the web realm (`S/u35r/r5/U14_QUESTIONS.md` Q10; `S/u35r/r5/U14_TAGS.tsv`):
    - PBUF_POOL_SIZE at default;
    - the 2,000 B lwIP floor;
    - the in-flight GET finishing on a section switch;
    - the per-request catch;
    - two default decimals;
    - status-code tables beside the description;
    - a dimensionless value omits its unit;
    - the inline bootstrap is not type-checked;
    - ResetVOC as a live-push field;
    - "one catalog table coloured".
  - "One catalog table coloured" is CalLight (`f509c906:tests_scripts/test_error_catalog.py:727-728`, `_TONED_TABLES = {"CalLight"}`), not the errcount count.
  - Q10 covers none of FWB-6's items, and not FWB-1's re-read either.
- **"Resolution:" hint (`js/templates.js:448-450`): REFUTED.**
  - Review item `website-display-details` (archive `audit/actions/FOLD_ANSWERS.md`) reads: "The SCD30 temperature offset's hint names its 0.01 °C resolution". The owner answered "Fine, and ..." (2026-10-02).
  - `resolution` has one user (`src/asy_scd30_driver.py:128`).
- **`console.error` once per failing episode (`js/render.js:646-650`): REFUTED.**
  - The pre-audit site already had `console.error("Poll failed:")` (`25caf528:js/poll-manager.js:117`), and pre-audit SPECIFICATION.md (`:4681`) called it "the poll loop's only failure diagnostic".
  - The release moves it to where it is reachable. It is the browser console, not the page look. Its `failing` flag also drives `onRecovered`.
- **Errcount count colour (`html/style.css:469-481`): CONFIRMED-OWNER.**
  - Pre-audit: red for `counter > 0` (`25caf528:html/style.css:407-409`, `templates.js:283`).
  - Now: coloured by the worst history type (`js/templates.js:711-719`).
  - It was added by U23 A.U23.12 (agent, from audit seed WEB.S08 "rollup and row colour can disagree").
  - The owner answered on that same catalog row (G7/R39, OR94.a (14)) with "the website's look stays exactly as it is", meaning the codes only become clickable.
  - Smallest fix: a counter>0 row attribute and one CSS rule, in place of the two `data-worst` colour rules. `data-worst` stays: the flagged filter and the no-data style use it. About 6 lines.
  - **Owner question:** Keep the error count coloured by its worst history entry (red errors, amber warnings-only, muted otherwise), or restore the pre-audit red for any non-zero count, per your 2026-09-29 "don't change the current look of the website"?

## Duplicates and notes

- **No duplicates across FWA/BUILD/DOCS/TESTS.**
  - FWB-3 shares only the class (M4 typing guards) with FWA-1 (`compare_before_write`) and BUILD-6 (buildgen); the sites differ, so they are not duplicates.
  - FWB-5's out-of-scope SGP40/BMP3XX sites are reported nowhere else.
- **FWB-1's root.** Every GET re-baselines existing cards (`render.js:701`) while their toggles/selects are never repainted. The pre-Apply re-read is one of three paths onto it: the re-read, the post-write GET and the live poll. Report it as one item.
- **FWB's Notes, checked:**
  - **The 60 s `/status` device watch** (`js/shell.js:96-103`) is owner-approved: review `website-unattended`, status ok: "The device check runs every 60 s". Not a candidate.
  - **The `buildgen/validate.py:871-905` J.6 formula mirror** is real (the floors are recomputed from AST-read constants). It is not a duplicate of BUILD-10, which covers hand-copied values, not formulas. It stays an owner call (P8 against build-time errors).
  - **The `asy_uart_comm.py:342` "for the memory gates" wording** is verified. It is a test-facing comment in product code (M6 wording); doc-scope only.
  - **The other notes** (hazard mode, library readers, `get_error_sources()`, the `_body_as_dict` import, M1) read as stated.
- **Minor citation slips in FWB, none affecting a verdict:**
  - `js/templates.js:924-951` is `:922-948` (the file ends at 948);
  - `fetchOnce()` starts at `:626`.
