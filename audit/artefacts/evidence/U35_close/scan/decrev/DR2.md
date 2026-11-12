DR2 decision review, written by the part (Wed Oct 28 11:47:48 UTC 2026)

Set: the register's owner-review list, units U0-U10 (U0, U1, U2, U3, U4, U5, U6, U7, U8, U8C, U8C2, U9, U10), 173 rows
from `inputs/DR2_register_rows.txt`. Pushed head `11b66cd8`, product tree `497b3eda`. Read-only; nothing ran. Every
claim below rests on git, grep at `497b3eda`, the pinned MicroPython v1.29.0 source, a datasheet, a scan row, or the
owner's own words; where a row needed more than a scan row, the check is named in the row.

Sources used for "the owner's words": `PROJECT_AUDIT_PLAN.md` OR rows at `11b66cd8` (only the quoted owner text, and
an owner's "yes"/"ok" to an explicit agent proposal), `recovered/owner_rulings_after_LN118.md`, `inputs/answers.json`
(the review page), `picture/PICTURE.md` sections 7-8.

## 1. Counts

**Decisions 171, facts 2** (REG:225, REG:330: a doc states a fact or a measurement).

| verdict | rows |
|---|---|
| DIFF | 3 |
| FORM | 3 |
| OBS | 7 |
| OWN | 6 |
| SUP | 23 |
| CHECK | 0 |
| SAME | 129 |
| fact | 2 |

Per unit (DIFF / FORM / OBS / OWN / SUP / SAME / fact):

| unit | rows | DIFF | FORM | OBS | OWN | SUP | SAME | fact |
|---|---|---|---|---|---|---|---|---|
| U0 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 0 |
| U1 | 3 | 0 | 0 | 0 | 0 | 0 | 3 | 0 |
| U2 | 7 | 0 | 1 | 0 | 0 | 3 | 3 | 0 |
| U3 | 10 | 0 | 0 | 0 | 2 | 4 | 4 | 0 |
| U4 | 7 | 0 | 0 | 0 | 0 | 0 | 7 | 0 |
| U5 | 18 | 0 | 0 | 0 | 1 | 1 | 16 | 0 |
| U6 | 20 | 0 | 0 | 1 | 1 | 2 | 16 | 0 |
| U7 | 20 | 0 | 1 | 0 | 0 | 0 | 19 | 0 |
| U8 | 16 | 0 | 0 | 0 | 0 | 1 | 14 | 1 |
| U8C | 11 | 0 | 0 | 0 | 0 | 1 | 10 | 0 |
| U8C2 | 12 | 1 | 0 | 0 | 0 | 0 | 10 | 1 |
| U9 | 16 | 1 | 0 | 4 | 1 | 7 | 3 | 0 |
| U10 | 32 | 1 | 1 | 2 | 1 | 4 | 23 | 0 |

Per topic:

| topic | rows | DIFF | FORM | OBS | OWN | SUP | SAME | fact |
|---|---|---|---|---|---|---|---|---|
| ci-tooling | 31 | 0 | 1 | 0 | 1 | 0 | 28 | 1 |
| timing-waits (the `@tunable` rows) | 27 | 0 | 0 | 0 | 1 | 1 | 25 | 0 |
| docs-records | 19 | 0 | 0 | 0 | 0 | 1 | 18 | 0 |
| website | 15 | 0 | 0 | 1 | 0 | 3 | 10 | 1 |
| led-notification | 11 | 1 | 0 | 4 | 0 | 2 | 4 | 0 |
| tests-hardware | 8 | 0 | 0 | 0 | 0 | 2 | 6 | 0 |
| tests-unit | 8 | 0 | 0 | 0 | 0 | 2 | 6 | 0 |
| core-logging | 6 | 0 | 0 | 0 | 1 | 2 | 3 | 0 |
| wifi | 6 | 0 | 0 | 0 | 3 | 1 | 2 | 0 |
| error-catalog | 5 | 0 | 1 | 1 | 0 | 2 | 1 | 0 |
| buildgen-toml | 5 | 0 | 0 | 0 | 0 | 1 | 4 | 0 |
| uart | 4 | 0 | 0 | 1 | 0 | 0 | 3 | 0 |
| twin | 4 | 0 | 0 | 0 | 0 | 2 | 2 | 0 |
| ntp-dns | 4 | 1 | 0 | 0 | 0 | 2 | 1 | 0 |
| generated-code | 4 | 0 | 0 | 0 | 0 | 0 | 4 | 0 |
| process | 4 | 1 | 0 | 0 | 0 | 0 | 3 | 0 |
| webserver-rest | 3 | 0 | 0 | 0 | 0 | 1 | 2 | 0 |
| driver-scd30 | 2 | 0 | 0 | 0 | 0 | 0 | 2 | 0 |
| driver-isl29125 | 2 | 0 | 1 | 0 | 0 | 0 | 1 | 0 |
| memory-gc | 2 | 0 | 0 | 0 | 0 | 0 | 2 | 0 |
| storage-fram | 2 | 0 | 0 | 0 | 0 | 1 | 1 | 0 |
| driver-sgp40 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 0 |

Picture lines touched: L1 58, L4 50, L5 25, L8 13, L3 7, L6 7, L7 6, L2 5 (facts: none). Misfits: REG:121 (L2),
REG:232 (L2), REG:244 (L6), REG:268 (L6), REG:270 (L6), REG:329 (L7).

How to read the set as a whole. U0-U8 were owner-defined deliverables (OR28 catalog, OR35 log rule, OR42 write rule,
OR46.a config objects, OR54.a/OR78 one-source website, OR45.a/OR15.a tier ladder and summary, OR30/OR30.a tunables);
their register rows are mostly staging, wording and test-machinery choices inside an owner scheme, and most stand
(SAME) or were finished by a later unit (SUP). The rows that change are in U9 (the LED pilot), U10 (the contracts) and
the U8C2 process rule: each rests on a hypothesis, a test need in the product, or agent text made binding.

## 2. DIFF rows

### REG:121 (registered as U9; landed at U22, `01032838`, 2026-10-13)
- **Decision as taken:** SF-M3-09: the Wi-Fi LED overlay is rewritten by its own task every 300,000 ms with no change
  pending ("a blanked pixel heals without a new call path"); at head `asy_neopixel_driver.py:36-39, 82`
  (`wait_for_ms(self._overlay_start.wait(), _OVERLAY_REFRESH_MS)`, tag `led.overlay_refresh_ms`).
- **New answer:** no periodic rewrite. The overlay task waits on its flag with no timeout, as before the audit
  (`await self.led_overl_start.wait()`). The premise (a WS2812 loses its state under Wi-Fi bursts) stays a
  hardware-round item; only if the board shows it does a fix follow, in its smallest form.
- **Basis:**
  - owner, 2026-10-28: "hardcoded delay checks like this are a very bad, very awkward pattern" (`scan_pub/C.md` NP-5:
    "the owner's words were about this row"); owner, 2026-10-28: "building upon hypothetical findings is a clear
    no-go";
  - `C.md` NP-5: class H, origin OF-75 (an agent scan), value "an agent choice (2026-10-06), never the owner's"; its
    premise is hardware-only (`REPORT.md` section 7 item 9);
  - the cascade defect, confirmed by the lead: a shutdown cancel landing in the timeout's cleanup window is lost, 8/8 on
    the pinned Unix port; the window is the timeout path of `extmod/asyncio/funcs.py:47-50` (v1.29.0:
    `runner_task.cancel()`, `await runner_task`, `raise core.TimeoutError`);
  - `REPORT.md` section 3 ("the reverse case ... revert it to the pre-audit `await ...wait()`, which removes 5
    lines"), section 6 point 3; `SCAN2.md` section 5 keep list ("with NP-5 reverted"); `PICTURE.md` M2.
- **Topic / line:** led-notification; L2 misfit (also L3).
- **What changes:** `src/asy_neopixel_driver.py` about −5 lines (`C.md` minimal-change list, NP-5); the constant, its
  `@tunable` line and its Part N row go; the tests that pin the 300 s rewrite go; one SPEC sentence; the register row's
  unit label reads U22, not U9 (records fix).

### REG:244 (U10)
- **Decision as taken:** `set_utc_valid(*, valid: bool = True)`: the lane brief's parameter, keyword-only, "and every
  test resets the clock through it"; reason: private-flag writes from tests would spread a module internal across 12
  files.
- **New answer:** the product function takes no parameter: it only ever marks the clock valid. Tests reset the module
  flag through one test-side helper, by reassigning the module attribute, which is the project's own mocking mechanism
  (MicroPython has no `unittest.mock`; CLAUDE.md's `no_implicit_reexport` note).
- **Basis:**
  - OR36 (owner, 2026-09-26): "contains zero artifacts specifically added for testing, neither functions, nor specific
    variables. Testing must adapt to fit the code, never vice versa.";
  - review `timestamps-before-ntp`, "ok": "Once set, the clock counts as valid for the rest of the boot" — so
    `valid=False` is a product state change the owner-approved behaviour never makes;
  - grep at `497b3eda`: one `src/` caller, `set_utc_valid()` with no argument (`src/asy_ntp_client.py:305`); 51
    call sites pass `valid=`, all outside `src/` (50 in `tests/`, 1 in `tests_hardware/`, 10 files); the definition
    is `src/asy_base_classes.py:384`;
  - `scan2/G2.md` overlay map, row "is the clock usable": "`set_utc_valid(valid=)` has no src caller, 51 test lines
    use it (G1, P4)".
- **Topic / line:** ntp-dns; L6 misfit (nothing in the product exists for the tests).
- **What changes:** product: one parameter and its assignment (about 2 lines); tests: one helper and 51 mechanical
  call-site edits in 10 files.

### REG:329 (U8C2)
- **Decision as taken:** scan findings no step closes are held in `audit/sweeps/open_findings.md`, "each with the unit
  whose step touches its file"; earlier scans' open rows move there (reason: a finding left only in a scan record has
  no unit to act on it). The file's header at `11b66cd8` makes it binding: "A unit's lead reads the rows naming that
  unit before building its packets, puts each into a step".
- **New answer:** keep the list, every finding documented, but a finding becomes a unit's work only once it is verified
  (observed, reproduced, or proven from the pinned source) or the owner decided it. An unverified finding stays
  knowledge or goes to the hardware-round list; a suspicious one is verified first, then fixed minimally.
- **Basis:**
  - owner, 2026-10-28: "building upon hypothetical findings is a clear no-go"; "Hypothetical findings which are
    suspicious to be real need to be verified";
  - `REPORT.md` "What went wrong" item 2, which the owner agreed to ("I agree with wour conclusions about scope and
    effort."): "Every finding became code ... It should have gone in as knowledge, a test, or a question to the owner";
  - `DRIFT.md` 2.6 (each finding added roughly five parts) and rule 9 ("A finding outside a brief goes to a list,
    never to a new lane").
- **Topic / line:** process; L7 misfit (agent text made binding), L2.
- **What changes:** records only: the file's header, and a class column (verified / by reading / hardware) in place of
  the automatic target unit. No code. Closed rows stay documented as they are. The rule the row cites ("the owner's
  evidence rule": "I just want to make sure no evidence to a bug ... is silently lost") is kept: nothing is dropped.

## 3. OBS rows

| id | root it depends on (scan row) | topic |
|---|---|---|
| REG:106 | W67 and the drop branch (`C.md` NT-5, class C of NP-2's deadline). The deadline's only trigger is "a signal task that never restarts" (`asy_neopixel_driver.py:33`); a supervised task that ends is restarted within one 2 s pass, so the case is the supervisor gone and the watchdog next: containment beyond the ladder. `scan2/G1.md` S2-G1-17 (NT-5 C, OV), `G4.md` S2-G4-9; `SCAN2.md` section 3 "only W67 and the identity test go". The deadline itself stays (owner, review `led-request-internal-queue`). | led-notification |
| REG:230 | the same root (S2-G1-17). W67's catalog row goes (`G4b.md` S2-G4X-6 lists W67). The second notify band 67-68 has no other code (W68 is unassigned at head); the row's reason "46, 47 retired, never reused" leans on the never-reuse rule, agent text (`SCAN2.md` section 8 item 5). | error-catalog |
| REG:235 | the same root: the dropped-signal warning's own test (S2-G4-9: "2/3 (W67)"). | led-notification |
| REG:181 | the browser definitions validator's growth per hint (`scan2/G3.md` S2-G3-13, X + OV, about 135 JS lines frozen into every image): the definitions are generated, checked by buildgen and parsed back by the stager, all frozen together. The Python mirror's coverage of the U6 rejections goes with those rejections; the pre-audit scope (schema major, shape, pollGroup, intervals) stays. | website |
| REG:232 | the type half of NT-4 (`C.md` NT-4: H, TYPING, "every wired producer field is a float, int or None"); `G1.md` S2-G1-19 (typing-only guards); owner, 2026-10-27: "if the check you remove really solely covers typing breakages and nothing else it can go (option b)". The guard is still at `asy_notification_service.py:238`. The NaN half is not typing; it is NT-4's own H (implausible), judged there. | led-notification |
| REG:268 | `setup()` widened to bool with no product reader (`G1.md` S2-G1-10, H, P4): the boot list discards it (`asy_system_service.py:743`, `codegen.py:443`), every in-driver call discards it. With the bool gone, "True when only the logger fell back" has nothing to mean. | led-notification |
| REG:270 | the same root (S2-G1-10). The one bool that stays is `UARTComm.setup()`, read by the link driver (`asy_uart_link_driver.py:291`); the link driver's own `setup()` answer, and so its `initialized`, has no product reader. The readiness check that "reads it so" is test machinery. | uart |

## 4. FORM rows

| id | the smaller form | scan row | topic |
|---|---|---|---|
| REG:132 | Keeping every fixed number stands. The per-module band table it extends (`range`, `owners` with bands) is read by one test only; the product reads `text`, `retired`, the status tables and `tone`. Smaller: the catalog keyed by number, uniqueness from the keys, no band table (~20 host JSON lines and the band checks go; device cost 0). | `scan2/G4.md` S2-G4-19 (X, "bands are optional") | error-catalog |
| REG:197 | The owner asked for "the same final block" for every runner (OR15.a (2), "yes to both"). The block is three emitters (sh, Python, JS) held byte-identical by a test, so each layout addition (here `Notes:` and the per-test `Skipped:` list) is written three times and pinned. Smaller: one renderer every runner calls. | `scan_pub/E.md` tests_scripts "Violations" (P8: "`test_summary_block.py` (three emitters, byte-identical)"); runaway 4 (runner-reporting chain, about 2,300 lines with tests) | ci-tooling |
| REG:256 | The narrowing `if period is None or ...` (`asy_isl29125_driver.py:1153-1154` at head; the comment says "set at construction, never None") is a run-time branch for the type checker. Smaller: a typing-side form (the value typed as `int` after construction, or a cast/assert), no branch. This site is not among the twenty S2-G4-22 lists. | `scan2/G4.md` S2-G4-22 (X); `SCAN2.md` section 9 ("need a typing-side form") | driver-isl29125 |

## 5. OWN rows

| id | the owner's words and source | built follows? gap |
|---|---|---|
| REG:139 | review `one-entry-per-fault`, status "change" (2026-10-02): "It should rather stay as is, upstream layers reacting to a downstream fault may encounter following errors going above the original fault, so getting a notion of a traceback and blast radius of an error is actually desirable."; OR35.a (2026-09-26): "Protection against alternating codes and layered limits are overkill on such limited device." | Yes: each layer persists (E49, then W63), the alternation is outside the newest-entry rule, the tests pin the real result. The base reader still persists its streak entry at head (`asy_base_classes.py:596`, `_ERR_STREAK`). Gap: none in the code; the U3 action file's preamble still states the overturned detecting-layer rule (section 7, item 11). |
| REG:142 | the same review note; and the Wi-Fi behaviour, owner, 2026-10-28: "We thoroughly discussed the WiFi issues and I decided everything already." | Yes: base `GIVE_UP` and `WLAN_GIVE_UP` (E66, live in the catalog at head) both persist. Gap: none. |
| REG:156 | owner, 2026-10-28 (Wi-Fi settled, as above). | Yes (`WifiConfig` four fields, `_WIFI_REFRESH_S = const(5)`). Form only; no smaller form to note. |
| REG:178 | owner, 2026-10-28 (Wi-Fi settled). | Yes (the Hostname label check, characters compared, no `re`). Form only. |
| REG:242 | OR30 (2026-09-25): "for example, runtime and timeout parameters for test suites ... make a list and document at an appropriate place ... Then check all of these parameters you found to be in an accuracy state"; OR30.a: "yes to all three" to the proposal "(1) scope: ... test-suite values ... (3) Accuracy: each value is checked against the current project (timeouts vs measured run times from CI logs and local runs with a stated margin ...); board-dependent values go to the hardware queue". | Registered: yes. Gap: "measurement owed" defers OR30.a (3)'s accuracy check; at head 951 of the 1,127 test/CI/runner rows carry it (`scan_pub/F.md` section 2, Part N table). How much of that check the tests are owed is where OR30.a meets the owner's 2026-10-28 line on tiered effort (section 7, item 12: facts only). |
| REG:247 | OR142 (2026-10-05): "Option 1, record the MicroPython sites in F.1. But the places you named so far are all harmless." | Yes: no `load_generated()`; the named sites stay, recorded in F.1. Gap: none. |

## 6. SUP rows; CHECK rows

**SUP** (a later decision replaced the row; whether the later one stands):

| id | superseded by | the later one stands? |
|---|---|---|
| REG:136 | U3 `65a0df3b` renumbered BMP3XX and SGP40 onto the catalog | yes (OR28) |
| REG:137 | U3 moved NTP onto the catalog; Run 9 followed | yes |
| REG:138 | U3's central newest-entry rule in the logger (A.U3.01) | yes: OR35.a/OR35.b; `A.md` A-P1 R; `SCAN2.md` section 5 |
| REG:141 | U6's one sample table (`samples.json`) replaced the mock histories | yes |
| REG:143 | U16's reorder; the pair is gone from `tests_scripts/test_fault_or_warning_never_both.py`'s allow-list at head | yes |
| REG:146 | U5 (construction-time signals) and U15 (W34 renamed `SGP_BACKUP_AGE`); W46/W47 are `"retired": true` at head | yes; their tombstones follow the never-reuse rule (agent text, `SCAN2.md` 8.5) |
| REG:147 | U18 removed `cettime()`'s handler; E16 `CLOCK` is retired at head | yes |
| REG:171 | U26 reworked the DebugLevel device scripts (one remains, `system_debug_level_set_standard.py`) | yes |
| REG:175 | `BuildInternalError` (later unit) | yes (`D.md` H1 R, OR23.a) |
| REG:184 | U23 deleted the comment's site (no legacy-bounds text in `js/mock-server.js` at head) | yes |
| REG:228 | the end-state IDs of later units | yes |
| REG:231 | `32c4266d` (U35 redo) removed the NeoPixel numeric-type gates, under the owner's typing rule (2026-10-27) | yes (`C.md` NP-R2, R). The bool fact the row rests on holds: `py/objbool.c` gives `mp_type_bool` no parent, so `isinstance(True, int)` is False |
| REG:233 | U24/U35's shared helpers (driven clock, print recorder) | yes, though those helpers sit inside a runaway (`E.md` runaway 1, driven-clock chain; runaway 9, `tests/test_shared_helpers.py`) |
| REG:234 | U22 removed `last_value`/`triggered` (absent from `asy_notification_service.py` at head) | yes |
| REG:237 | the later "Valid" envelope | yes |
| REG:238 | the later "LED busy - retry later" answer | yes (owner, review `led-request-internal-queue`: "The refusal and error message lets the external caller knows to try again later.") |
| REG:239 | U25's twin wall clock (OF-19 closed at U25) | yes |
| REG:241 | the later retry message | yes (same owner note) |
| REG:246 | U11's SF-A11 (REG:113, another part's set): the auto-unpause became a `ticks_ms()` deadline on the status pass | in doubt: `A.md` A-S21, class H, triage suspicious (mechanism confirmed in source, `shared/runtime/mpirq.c:105`, `py/scheduler.c:163-180`; frequency unverified, hardware item HW5) |
| REG:253 | U18 put `shape=hostName` on `NTPHost` (`asy_ntp_client.py:122` at head) | yes (the PUT check is `G2.md` S2-G2-6's keep, "NTP-1/NTP-2's PUT refusal (O)") |
| REG:254 | U18 removed `_flash_led_off()` (`f1f800e7`) | yes (Wi-Fi settled) |
| REG:266 | U19's typed route object; no `assert` in `asy_webserver_service.py` at head | yes |
| REG:315 | U26 renamed the file (`tests_hardware/soak_durations.py`) | yes |

**CHECK:** none. No row in this set is suspicious in a way a static check could not settle: every DIFF and OBS above
rests on a scan row with its proof, git, grep at `497b3eda`, the pinned source or the owner's words. The one premise
left open (the WS2812 state loss behind REG:121) does not decide the DIFF: the new answer is "not without the board's
evidence", whichever way the hardware round goes.

## 7. Contradictions, seeds, and counterparts

### Contradictions

1. **REG:243 against commit `87c14760` (U35 redo, 2026-10-26).** REG:243 (U9) keeps OF-16 open: "closing it needs a
   per-file count in Part N's Sites format ... an extension is the owner's to accept". `87c14760` made that extension
   as an agent decision: SPECIFICATION.md N.2 at `11b66cd8` reads "the check compares the counts, so a deleted second
   tag fails (agent, 2026-10-26)"; the redo brief ordered it with the tag "(agent, <date -u>)"
   (`S/u35r/briefs/n67_test_items.md` item 7). Yet `audit/sweeps/open_findings.md` at `11b66cd8` still lists OF-16 as
   "open ... the extension waits for the owner (U9 review row)". No owner words were found for the extension.
   **Stands: REG:243** (L7: only the owner's words decide a change to a format in force). The new knowledge adds
   that per-file pinning is part of the register's runaway: "needs every Sites cell to list exactly its files and tag
   counts, so every test edit reopens the register" (`F.md` section 5 item 1). The records contradict each other
   (OF-16 "open" while implemented).
2. **REG:244 against OR36** (owner, quoted in section 2) and the owner's "ok" on `timestamps-before-ntp` (one-way
   clock). **The owner's words stand.**
3. **REG:121 against the owner's 2026-10-28 words** on hardcoded delay checks and on hypothetical findings, and
   against L2/L3 (`PICTURE.md` M2). **The owner's words stand.** Records: the register files the row under U9, but git
   shows it landed at U22 (`01032838`).
4. **REG:329 against the owner's 2026-10-28 words** on hypothetical findings and the owner-agreed `REPORT.md` "What
   went wrong" item 2. **The owner's words stand.**
5. **REG:231 against REG:232: one guard, removed in one module, kept in its sibling.** The same numeric-type gate on
   the same signal path was removed from the NeoPixel driver (`32c4266d`, under the owner's typing rule) and is still
   at `asy_notification_service.py:238`. **The owner's typing rule (2026-10-27) stands**, so REG:232's type half goes
   too (S2-G1-19).
6. **REG:256 against the owner's typing rule** (2026-10-27: "fully covered by typing adherence alone, and ...
   unreachable with today's code"). **The owner's words stand** (FORM above). S2-G4-22's list misses this site.
7. **REG:268 and REG:270 against L6** (OR36, "zero artifacts specifically added for testing"), through S2-G1-10.
   **The owner's rule stands.** Their counterparts on the review page, `setup-returns-bool` and `initialized-flags`,
   are unanswered.
8. **REG:106, REG:230 and REG:235 against L3** ("the ladder itself is part of the design. Containment code beyond it
   is not."), through S2-G1-17. **The owner-approved deadline stands, and W67's machinery goes.**
9. **REG:144's "the list only shrinks" against the later units (agent against agent).** The fault-or-warning
   allow-list grew from 21 entries at U3 (`65a0df3b`) to 29 at `497b3eda`
   (`tests_scripts/test_fault_or_warning_never_both.py`, counted from its `_ALLOWED` dict). Each added entry carries a
   "two occurrences" reason. **The measure is OR56** (owner: "Either it's a fault or a warning, but never both at a
   time. That is common sense and should be globally checked and applied."); the claim in REG:144's reasoning did not
   hold. Fact for the lead. (REG:128's like claim did hold: the citation list went from 169 to 89 lines, the
   vocabulary list from 733 to 393.)
10. **U3's central rule against U30's per-episode flags.** U3 removed every per-module episode mechanism (A.U3.02;
    REG:134, REG:138 are its U2 half), as OR35.a/OR35.b ask. U30 (`06a8ae5d`, "A config store's or a reader's failed
    reads log once per episode") brought seven flags back (`G4.md` S2-G4-8, `G1.md` S2-G1-8). They also stop the
    console line, which OR35.a rejects: "Console logs actually should keep printing all." **The U3 side stands (the
    owner's words).**
11. **U3's action-file preamble against the owner's change on `one-entry-per-fault`.** The preamble's rule, "the
    layer that detects a fault persists it; a layer that only learns of it from a callee's failure return prints it"
    (agent, 2026-09-29), went to the review page and the owner answered "change" (quoted in section 5). The code
    follows the owner (REG:139, REG:142; `asy_base_classes.py:596`), and SPEC no longer states the rule. But
    `audit/actions/U3.md` still carries it, with "Open points: none". Records only. **The owner's words stand.**
12. **Two owner statements on test tunables (facts, no question).**
    - OR30/OR30.a ("for example, runtime and timeout parameters for test suites"; "yes to all three", the accuracy
      check against measured runs included) against 2026-10-28 ("The unit tests shall have good quality, but don't
      need deep dives. The audit verification machinery is just a temporary tool.").
    - Facts: OR30.a (1)'s own examples are suite-level ("CI `timeout-minutes` ...; per-file timeouts and retries;
      Unix-port `-X heapsize`; twin run and soak durations; hardware-tier budgets"). U8C/U8C2 extended the tagging to
      single literals inside test files: 1,249 `@tunable` lines in the test and tool areas (`E.md` runaway 5), of
      which 450 are in `tests/`.
    - The register holds 1,127 test/CI/runner rows; 951 of them read "estimated ... measurement owed" (`F.md` section
      2).

Within my set and against the picture lines, no other pair conflicts. Every SUP row's later decision agrees with the
row's own stated end state (each checked at head, section 6).

### Seeds: whether each stands, and what grew from it

- **U2, the error catalog.**
  - The seed stands: OR28 (owner): "Globally harmonize errno and wrnno numbers ... this non-overlap and consistent
    scheme shall be applied to every project member."
  - Beyond the owner's words:
    - the per-module bands and owners (`G4.md` S2-G4-19, X, optional; REG:132 FORM);
    - the "Retired numbers are never reused" rule. It is agent text (`65a0df3b`, SPECIFICATION.md:3653; `SCAN2.md`
      8.5), and it turns every removed code into a tombstone (`G4b.md` S2-G4X-6 lists about 20; REG:146, REG:230
      lean on it);
    - the test band E125-E127. Its texts are inlined into every device's frozen website (S2-G4-19: "a P4 tension the
      owner may want to see"; REG:140 uses it).
  - What grew from it: every later mechanism brought its own codes. 15 codes exist only for doubted mechanisms
    (`SCAN2.md` section 2 item 7).
- **U3, the central log-repeat rule.**
  - The seed stands: OR35.a/OR35.b; `A.md` A-P1 R.
  - The pair scan stands too: OR56, "should be globally checked and applied".
  - Undone later: U3's detecting-layer rule was reversed by the owner (item 11). U30 re-grew the per-episode flags
    U3 removed (item 10). The pair allow-list grew (item 9).
- **U4, compare-before-write.**
  - The seed stands: `A.md` A-C21 R, OR42; `C.md` SCD-3 R, OR42.b and OR42.c "Perfect match".
  - The deferred flush that came later is U11's, under the "ok" on `failed-push-no-flash-write`. It has a smaller form
    (`G4.md` S2-G4-16), and it is not in this set.
- **U5, config objects.**
  - The seed stands: OR46.a, "think of something better and lower the linter limit again"; −115 `src/` lines
    (`DRIFT.md` section 3).
  - One cascade: `_urgency` (`G3.md` S2-G3-17, C, "keep: as is (net small)"; REG:158 SAME).
- **U6, one-source website definitions.**
  - The seed stands: OR54.a (1), OR43.a, OR78; −1,341 website lines.
  - What grew later: the browser validator, one validator per hint (S2-G3-13, X, mostly U23's A.U23.10). U6's own
    share of it is REG:181 (OBS).
- **U7, the tier ladder and the summary block.**
  - The seed stands: OR45.a ("1. yes 2. yes 3. yes 4. yes"), with the L0-L4 ladder, containment by execution and by
    scenario, and listed exceptions; OR15.a (2), "the same final block" for every runner.
  - What grew from it: the runner-reporting chain. The block exists in three languages, held byte-identical, then the
    run record and the verdict came at U26 (`E.md` runaway 4). REG:197 FORM.
  - The CI growth (45 to 175 minutes) has other roots in `E.md`. It is not this seed's.
- **U8, U8C and U8C2, the `@tunable` scheme.**
  - The seed stands: OR30 and OR30.a, "yes to all three". The owner approved the tag, the permanent register, a check
    that fails on an unlisted, untagged or differing value, and the accuracy check.
  - What grew from it is the largest record growth of the audit: Part N is 562 KB, 47 % of all doc growth (`F.md`
    section 5 item 1).
  - The reach into single test literals and the per-file counts (item 1) are the agent's. How much accuracy the test
    rows are owed is item 12.
- **U9, the LED pilot.**
  - Its owner parts stand:
    - NP-1, the REST refusal (OR102 "5. a");
    - NP-2's deadline (review "Fine, and ...");
    - NT-1, midnight spanning (OR69 "6. a");
    - NT-6, the measured pause (OR104).
  - Its agent parts do not:
    - NP-3, NP-4 and NT-4 are H (`C.md`);
    - NT-5 is C (REG:106, REG:230, REG:235 OBS);
    - the 300 s rewrite registered under it is H, with a confirmed defect (REG:121 DIFF).
  - Its planned role as "the calibration pilot: cost, convergence rule, register format" never recorded a cost figure
    (`DRIFT.md` 2.8).
- **U10, the system-wide contracts.**
  - These stand:
    - the counter cap (`A.md` A-B1 R, OR103);
    - `TickSeconds` (A-B4 R, OR101/OR104; two of its six instances go with the NTP cadence chain, `G4.md` S2-G4-13);
    - `utc_now()` (A-B5 R, review `timestamps-before-ntp` "ok"; one flag instead of two is a form note, S2-G4-15);
    - the boot-batch logger setup (A-B16 R, OR47.a (2));
    - the collected read triggers (`D.md` G5 R, WP7);
    - the lock-order and watchdog-feed checks (`E.md` keep list).
  - These do not:
    - `setup()` → bool (S2-G1-10, H; REG:268, REG:270 OBS);
    - the `valid=` test parameter (REG:244 DIFF);
    - the shared-start stagger mechanism (`A.md` A-S26, H: the pre-audit chain already met OR47);
    - the refused tick-arm answer (`A.md` A-B6, H; `G4.md` S2-G4-7).
  - What later depends on it, per `DRIFT.md` section 3: "U10 did plant the seeds of later cascades, `utc_now()` and
    `TickSeconds` among them". These are the "TS None before the first sync" exceptions in every reader (BMP-10,
    SCD-10, SGP-22, ISL-18, all C, `G4.md` platform table) and the NTP cadence chain (S2-G4-13).
- **A U0 decision missing from the list.** The U0 doc pass deleted F.2's "only worth closing for a concrete,
  non-hypothetical threat" (`195f3ed3`, 2026-10-06; `PICTURE.md` M1). The decision was taken on the owner's behalf,
  but it is not a register row. The picture puts it back.

### Likely counterparts in other sets

- REG:106, REG:230, REG:235 ↔ review `led-request-internal-queue` (the deadline); register REG:123 ("all | New
  catalog codes ... `_WRN_NOTIFY_SIGNAL_DROPPED` ...", found in no part's input file).
- REG:121 ↔ parked delta REG:878 ("U15, U22 | SF-M3-09 (agent) ... a blanked pixel leaves the WiFi overlay wrong",
  in the parked set) and U22's own rows; the same SF-M3 family as REG:117 (U15, SF-M3-01, the 10,800 s bound).
- REG:244 ↔ review `timestamps-before-ntp`.
- REG:246 ↔ REG:113 (U11, SF-A11) and parked REG:853.
- REG:252 ↔ REG:517 (U18 keeps the once-per-tick read) and REG:389 (U14, the `TickSeconds` horizon test).
- REG:268, REG:270 ↔ review `setup-returns-bool`, `initialized-flags` (unanswered).
- REG:245 ↔ review `trigger-starters` (unanswered).
- REG:231, REG:232 ↔ review `validator-api` (unanswered: "runtime type checks that can never fire are not written").
- REG:327, REG:329 ↔ the open-findings close rows REG:656, REG:666, REG:681, REG:703, REG:718, REG:727 and REG:794,
  which run the mechanism REG:329 set up.
- REG:139, REG:142 ↔ review `one-entry-per-fault`.
- REG:142, REG:156, REG:178, REG:254 ↔ the Wi-Fi rows of U18 (owner-settled).
- REG:149, REG:155 ↔ reviews `api-unknown-key-invalid`, `scd30-write-path` ("ok").
- REG:166 ↔ review `typecheck-stripper-text-edit` ("ok").
- REG:194-REG:213 ↔ review `retry-pass-flagged` ("ok").
- REG:214, REG:242, REG:308-REG:328 ↔ every later unit's `@tunable` rows.

## 8. SAME rows

- REG:128 docs-records: allow-lists grow once, text untouched; they did shrink later (169→89, 733→393). The gates
  they serve are the audit-born docs policing of `E.md` (b), which the owner calls temporary: if the gates retire,
  this row goes with them.
- REG:129 docs-records: the stale BACKLOG bullet is removed whole.
- REG:130 docs-records: names the owner's legacy rule as the reason; true and smaller.
- REG:131 docs-records: minimal repath of three comments.
- REG:133 error-catalog: next free numbers; no fixed number moves.
- REG:134 core-logging: one W25 for a paused read and write; the episode base goes (OR35.b direction).
- REG:135 uart: a test goes with the constants it reads.
- REG:140 tests-hardware: the seed scripts use the test band, so a test-written entry is recognisable (the FRAM
  evidence rule); the band's P4 tension is S2-G4-19's.
- REG:144 core-logging: real pairs allow-listed with reasons (OR56); see item 9 on "only shrinks".
- REG:145 core-logging: the narrowest reading of the pair scan.
- REG:148 twin: the twin counts events under the central rule.
- REG:149 driver-scd30: a body that writes nothing reads no chip snapshot (`C.md` SCD-3: one snapshot per PUT with a
  chip key).
- REG:150 driver-scd30: a reasoned typing-side ignore (still at `asy_scd30_driver.py:278, 297`).
- REG:151 buildgen-toml: one predicate for an observed build break.
- REG:152 docs-records: minimal current-state SPEC edits.
- REG:153 docs-records: avoids a self-contradicting SPEC.
- REG:154 tests-unit: the write, not the snapshot, fails in that test.
- REG:155 website: the comment matches what reaches the backend.
- REG:157 webserver-rest: avoids shadowing `tuple.index`.
- REG:158 buildgen-toml: `_urgency` keeps mandatory services early (S2-G3-17, keep). The FRAM chunk order changing
  between builds is allowed (OR47.a: "no requirement for the fram to stay consistent through firmware re-flashes").
- REG:159 buildgen-toml: codegen reads src defaults (one source).
- REG:160 generated-code: MicroPython's namedtuple takes no defaults (`py/objnamedtuple.c:97`, arg count must equal
  field count).
- REG:161 led-notification: a refused signal is printed by the level-gated logger and persisted once.
- REG:162 driver-isl29125: the address is hard-wired, "internally hard-wired as 1000100"
  (`datasheets/isl29125/REN_isl29125_DST_20151201_1.pdf`), so no feature is lost.
- REG:163 tests-unit: keeps the test's real behaviour.
- REG:164 uart: keeps a callback the tests pass.
- REG:165 tests-unit: unused ignores removed.
- REG:166 ci-tooling: fixes an observed import-time NameError in frozen firmware.
- REG:167 tests-hardware: a crashed task or absorbed bus error is no longer swallowed (the owner's evidence rule).
- REG:168 ci-tooling: minimal registration.
- REG:169 ci-tooling: ESLint's floor is 1.
- REG:170 docs-records: a measured figure; a missing sentence added.
- REG:172 docs-records: minimal current-state edits.
- REG:173 ci-tooling: ruff's positional twin of an existing exemption.
- REG:174 website: a row lands with its key (parity).
- REG:176 website: keeps a moved errcount group showing real history.
- REG:177 website: no new hint text.
- REG:179 website: the mock fails closed.
- REG:180 website: probes see real current values.
- REG:182 ci-tooling: the check must spell the names it bans (OR78).
- REG:183 generated-code: a published `null` is published.
- REG:185 generated-code: same generated text, within the lint ceiling.
- REG:186 website: one device's failure no longer hides the others'.
- REG:187 website: a failed WebDriver command is no longer ignored.
- REG:188 wifi: test scope matches the schema's order and U4's "Unchanged".
- REG:189 docs-records: docs stop citing deleted files.
- REG:190 docs-records: true at U6.
- REG:191 driver-sgp40: fixes a real two-SGP40 misread found by the parity check.
- REG:192 memory-gc: the live check only gets stricter. The test and its suppressed arm predate the audit (in the
  tree at `25caf528`). OR21.a's "the control arms are overkill" (2026-09-25) is noted for the cleanup, not
  applied here.
- REG:193 website: a visible skip.
- REG:194 ci-tooling: a failure can no longer exit 0.
- REG:195 ci-tooling: SPEC E.3's stated behaviour.
- REG:196 ci-tooling: no failure vanishes behind a passing retry or a missing log.
- REG:198 ci-tooling: per-test detail stays visible.
- REG:199 ci-tooling: listed exceptions with reasons, as OR45.a (3) prescribes.
- REG:200 docs-records: the later owner wording wins; actor tags truthful.
- REG:201 docs-records: the doc states what the code does.
- REG:202 tests-hardware: one run no longer prunes another's evidence.
- REG:203 tests-hardware: a retried refusal reaches the record.
- REG:204 ci-tooling: no marker escapes the scan.
- REG:205 ci-tooling: tolerate argparse's case without editing the tool.
- REG:206 ci-tooling: pytest's own exit is not mislabelled.
- REG:207 ci-tooling: a guard form that works when sourced.
- REG:208 ci-tooling: no double count of a retried file.
- REG:209 ci-tooling: no note dropped.
- REG:210 ci-tooling: the files line matches E.10.
- REG:211 docs-records: an interim row names its gap.
- REG:212 ci-tooling: an option no longer becomes a directory name.
- REG:213 ci-tooling: a spawn failure is named, not waited out.
- REG:214 timing-waits: early tags keep their rows (OR30.a (2)'s check).
- REG:215 timing-waits: one row, one value; leaves composite poll steps untagged (less tagging).
- REG:216 timing-waits: follows the Resolved line.
- REG:217 timing-waits: the step's unit.
- REG:218 timing-waits: a mirror that is about to go is not a site.
- REG:219 timing-waits: names where the texts gave none.
- REG:220 timing-waits: the merged text lists it.
- REG:221 timing-waits: one grammar.
- REG:222 timing-waits: the work order's placement.
- REG:223 ci-tooling: `/proc/uptime` resolution.
- REG:224 ci-tooling: ignores with reasons; the vendored stub is never edited.
- REG:226 uart: contract constants are excluded (OR30.a (1)).
- REG:227 timing-waits: the code's own cited measurement as Basis.
- REG:229 website: the page footprint counted correctly (the device's socket budget).
- REG:236 ntp-dns: the Unix port's `gmtime()` is a 9-tuple (`ports/unix/modtime.c:138`), rp2's an 8-tuple
  (`extmod/modtime.c:75`).
- REG:240 tests-unit: a regression fails instead of hanging the file (the hang backstop).
- REG:243 ci-tooling: the blind spot left to the owner; see item 1.
- REG:245 timing-waits: a test bound for the owner's even stagger (WP7, OR47.a (3)).
- REG:248 ci-tooling: typing follows today's return type.
- REG:249 ci-tooling: the tests need a coroutine.
- REG:250 generated-code: the interim annotation form.
- REG:251 buildgen-toml: `class_has_read_triggers()` serves G5 (R, S2-G4-20); `get_error_counter()` the protocol.
- REG:252 wifi: a cheap bound by construction (L2) against `ticks_diff()`'s 2**29 ms horizon. `WifiUptime` on
  `TickSeconds` is kept (S2-G4-13, OR101/OR104).
- REG:255 docs-records: a reorder cannot keep a topical heading true.
- REG:257 storage-fram: the bounded lock wait is pre-audit (`25caf528:src/asy_fram_driver.py:408`); the test
  technique is sound.
- REG:258 led-notification: the refusal tests need the pre-setup state.
- REG:259 led-notification: a test budget for the owner's measured pause (NT-6).
- REG:260 ci-tooling: the siblings' existing reason.
- REG:261 docs-records: one rule for every reordered file.
- REG:262 docs-records: the tree does not contradict itself.
- REG:263 docs-records: docs state current behaviour.
- REG:264 memory-gc: the figure is linear; computing it is exact.
- REG:265 webserver-rest: a nameless error source fixed.
- REG:267 led-notification: the REST setter contract (Valid/Failed per key).
- REG:269 ci-tooling: one shared alias.
- REG:271 ci-tooling: the narrowest readings, written in each check.
- REG:272 ci-tooling: no pending entry outlives its unit. Its teardown-answer entries (`I2C.deinit`, `SPI.deinit`)
  are the check side of S2-G1-10 and go with it.
- REG:273 ci-tooling: the check's own fixtures are not launchers.
- REG:274 tests-hardware: the scripts wait on the reading, not on time.
- REG:275 docs-records: the D.15 rule.
- REG:308 timing-waits: a tag needs its row (OR30.a (2)).
- REG:309 timing-waits: a row waits for its tag.
- REG:310 timing-waits: real tagged literals get rows.
- REG:311 timing-waits: the register compares as written.
- REG:312 tests-unit: one source for two tests.
- REG:313 tests-unit: a stalled listener can no longer pass silently.
- REG:314 timing-waits: the merged text carries it.
- REG:316 timing-waits: those literals were deleted or moved.
- REG:317 process: content shared, not ancestry.
- REG:318 twin: relieves a large allocation by design; ends a silent growth bug.
- REG:319 timing-waits: the step's constituents moved to U25.
- REG:320 timing-waits: withdrawn with its code.
- REG:321 timing-waits: the fake servers left with their classes.
- REG:322 timing-waits: the Resolved line over the older text.
- REG:323 timing-waits: the raw script's rows withdrawn.
- REG:324 timing-waits: a requirement, not an estimate.
- REG:325 timing-waits: a Dependant names an existing row.
- REG:326 process: no double application.
- REG:327 process: the SF-U8C2 findings are statically true silent failures (a swallowed exception, an ignored
  result). They would pass REG:329's new verification gate, so recording them for later units stands.
- REG:328 timing-waits: one more truthful reason.
