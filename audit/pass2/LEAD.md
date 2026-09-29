# Allover pass 2 — lead (arbiter) resolutions and adopted gaps

Audit working file (temporary, deleted with `audit/`, OR11.a). The lead's part of the pass-2 register:
cross-group resolutions (OR7.a: checked against sources, never by majority), merges, the gaps the groups
proposed and the lead adopted, and the one provenance decision no group placed. Group files:
`audit/pass2/G1.md`-`G10.md`; brief `audit/sweeps/pass2_prompt.md`; index `audit/pass2/INDEX.md`.

## 1 Resolutions of cross-group points

Every group's section 3 was read (about 150 entries). Most name complementary rules at two layers and
need only the cross-reference they already carry. The points below needed a decision.

| # | Point | Resolution | Basis |
|---|---|---|---|
| 1 | Contradictions flagged against HR054, HR150/HR042, HR048, HR014, HR209 and SPEC M.1.1 item 18 | Already resolved in the owning requirement (G5/R35-R36, G4/R40, G3/R19, G3/R61-R62, G1/R36, G4/R04, G3/R44): each follows the later owner row | OR69.a (3)(6)(7), OR70.a (2), OR72.a (10), OR61.a, OR71.a (4) |
| 2 | G5/R53 lists "FRAM SPI transactions" as timeout-wrappable (G4/R22) | Scope corrected: only the awaitable parts (bus-lock acquisition, status-poll sequences, UDP waits); a `machine.SPI` transfer is synchronous and stays under the watchdog backstop; BACKLOG's wording corrected with it. The owner's priority on one mechanism stands | fact (`ports/rp2/machine_spi.c`), OR72.a (2), harmonization 24 |
| 3 | OR47.a (1) lists "construction, setup batch, task starts, timer starts"; the generated `main()` runs timer starts, `ntp_force_sync()`, task starts (`buildgen/codegen.py:470-478`) (G1/R30) | Not decided by the lead (withdrawn after verification, V4/V01): the owner confirmed OR47.a (1)'s order, so the conflict goes to the owner as question 3; G5/R05 states OR47.a (1)'s order and records the code's order as a finding | OR47.a (1) (owner "1. yes"), OR7.a, OR3 |
| 4 | Twin state: G8/R35 "never a fixed repo path" vs G7/R14 persistent default (E09) | The manual twin entry point keeps its persistent default file in `digital_twin/` (owner-specified, E09); automated runs own per-run paths and archive before wiping | E09, OR38.a (2) |
| 5 | `voc_algorithm.py:141` `"32q"` (G4/R11) vs the literal-port rule (G3/R10) | A persisted `struct` format takes `"<"` — size-neutral, no arithmetic change — as the one exception to the literal port; names and casing stay; G10/R09's scheme applies only to the facade other modules import | G4/R11 (fact: native vs standard formats), L01 (agent) |
| 6 | ISL29125/UART per-driver device allow-lists (G8/R01, G3/R44) | Gone: a device's TOML decides its sensors; SPEC M.1.1 item 18 keeps today's scope (`dev` carries it) without "must not gain one" | OR71.a (4) is later than item 18 (2026-09-12, list A36), OR68.a (2) |
| 7 | A06's "untestable peripheral" reason and the wozi prohibition (G8/R01, G1/R36) | The owner's item names `dev` as the UART target; the reason and the prohibition are the agent's and are labelled so | A06 note, OR71.a (0) |
| 8 | `crc_checks.py` "not to be modified" (G3/R03) | The owner's words (`23e5443`) cover only the per-byte yield; the wider ban is an agent widening. HARVEST_REQUIREMENTS 3.3's empty-payload decision stands, basis corrected | M4, harmonization 24 |
| 9 | Unreadable config file (G5/R34) | Never overwritten: an I/O error or `MemoryError` while reading is not a bad file; the one-repair-per-boot exception covers a readable file with a bad, missing or unknown key | OR70.a (3), OR71.a (2), conservative (OR2.c) |
| 10 | SENS.S11, TEST.S11 carry two statuses | The owning area's status applies (answered) | plan 0 (owning area) |
| 11 | L51 (retired `html_stub/`, owner-tagged) placed by no group | LEAD/R18 | DECISION_PROVENANCE L51 |
| 12 | Verification (`audit/pass2/verify/V1.md`-`V4.md`, 68 defects in 523 requirements) | Applied as `verify/RULINGS.md` says; list-L owner trails left to owner question 4 | OR7.a |
| 15 | OR83: L06, L44, L51 restored to the owner's original wording (owner label); F18 reading confirmed | Applied in G3, G5, LEAD/R18, G9/R38, G1/G2/G4/G6 (veto qualifiers removed) | OR83 |
| 14 | OR79 (attempt the bench spoofing test), OR80 (datasheets private submodule), OR81 (stricter typing in this audit), OR82 (owner-traced L labels) | Applied in G1/R29, G9/R23, G8/R61, G9/R38 and every rank citing an L item | OR79-OR82 |
| 13 | Owner answers after pass 2 (OR74-OR78, 2026-09-28) | Applied: OR74 in G3/R44; OR75 in G5/R05 and G1/R30 (legacy checked: timers first there too); OR76 as LEAD/R19; OR77 in G1/R29; OR78 in G8/R01 and G1/R36 (the fixed-`dev` exception withdrawn) | OR74-OR78 |

## 2 Merges (one rule, one owning requirement)

The merged requirement keeps a "Lead: merged into …" line; its State lines are carried out under the owner.

| Merged | Into | What stays with the merged one |
|---|---|---|
| G6/R50 | G5/R23 | the REST face of `ResetErrors` |
| G3/R33 | G5/R06 | the per-driver logger-setup sites |
| G3/R31 | G6/R51 | the driver-side atomic snapshot |
| G5/R55 | G9/R28 | the code and scan side of the change classes |
| G9/R06 | G6/R38 | its doc corrections |
| G4/R63 | G5/R03 | the platform facts of `mem_backup()` |

Rules stated in several groups at different layers, each with one owner: `res` and the four result words
G5/R39, the envelope and its JS mirror G6/R41, the code catalog G9/R07; F18 as a degradation check
G6/R49, the ceiling fit G4/R62; the central repeat rule G3/R01, its applications G6/R20 and G5/R20;
necessity verdicts G9/R34, their test side G2/R17; `reset_reason` G5/R03, its twin model G7/R07, its
website field G7/R29, its hardware oracle G1/R14.

## 3 Requirements (adopted gaps and the unplaced decision)

The groups proposed 20 gaps. OR44.a (1) invites filling pillar gaps; each below follows from an owner
row or a pillar and is adopted at agent rank. All are on the owner-review list (OR2.c). Two pairs were
merged (G6 gap 1 with G9 gap 4; G2 gap 2 kept apart from G6 gap 2).

### LEAD/R01 Hardware instruments run in the twin first
- **Req**: A committed host runner (a stock Unix-port twin, not a frozen 32-bit build) runs every device script and flash/bench test module once against the digital twin before it enters the hardware queue, and again after any change to the runner or to the `src/` API the script calls; a script that cannot run there is a listed exception with its reason.
- **Sources**: G1 gap 1 · OR29.a (4), OR21.a (1), OR16 · HW.T02, HW.T13
- **Rank**: owner — run once in the twin before the queue, OR29.a (4) "(owner, 2026-09-25)"; the committed runner, the re-run trigger and the exception list "(agent, 2026-09-27)"
- **State**: work: code in U26 — commit the runner (today `twin_wrap.py`/`validate_bench.py` are scratchpad tools, `HEAP_FRAGMENTATION_MEASUREMENTS.md:310`); test in U35 — every instrument run through it after B1
- **Home**: `tests_hardware/README.md`; SPEC E.6
- **Pillar**: P5
- **Pass 2**: new. Verified: V4/V19 applied.

### LEAD/R02 A hardware round starts and ends in a standard board state
- **Req**: Every hardware round ends on the release `dev` image with `errcount` saved, `DebugLevel` 5, the SCD30 at its configured NVM values, FRAM write-protect clear and no scratch files, checked by harness fixtures at its end and at the next round's start, replacing a hand-kept board-state line.
- **Sources**: G1 gap 2 · OR38.a (4), OR17.a (5) · BACKLOG.md:359-361, Appendix B.1 D1-D3 · RF312
- **Rank**: agent — "(agent, 2026-09-27)"
- **State**: work: test in U26 (fixtures); hardware in C; code in U26 — a timed-out `mpremote` call kills only the host process (`tests_hardware/harness.py:373-384`): the device script keeps running (several feed their own watchdog) until the next test's raw-REPL entry interrupts it mid-operation, config writes included; the harness interrupts and resets the board to the standard state before the next test (RF312)
- **Home**: `tests_hardware/README.md`
- **Pillar**: P9
- **Pass 2**: new Refined: RF312.

### LEAD/R03 A pass after a retry is never a plain pass
- **Req**: A test file that passed only on its per-file retry is named and counted in the runner's summary block and entered as an item to root-cause; the retry backstop itself stays.
- **Sources**: G2 gap 1 · OR6.a, OR15.a (2), OR21.a (3), OR37.a (2) · `scripts/test.sh:362-387`
- **Rank**: agent — "(agent, 2026-09-27)"
- **State**: work: code in U7
- **Home**: SPEC E (runner summary block)
- **Pillar**: P5
- **Pass 2**: new

### LEAD/R04 Months of uptime are proven under driven time
- **Req**: Behaviour over months of uptime — tick wraps and stored-tick ages at rp2's 2**30 ms period, NTP resync cadence, supervisor counter decay, log-ring saturation — is proven at L1/L2 under a driven clock for every generated device, not by real-time soaks alone.
- **Sources**: G2 gap 2 · OR44.a (1) P1, HR001 · TEST.S25, Appendix B.1 G6
- **Rank**: agent — "(agent, 2026-09-27)"
- **State**: work: test in U35 (with HR001's tick scan)
- **Home**: SPEC E
- **Pillar**: P1
- **Pass 2**: new

### LEAD/R05 Wall-clock consumers survive an RTC step
- **Req**: Every wall-clock consumer (`TS`, FRAM backup age, the notification window, `cettime`, the NTP stale counter) behaves correctly when the RTC steps forward or backward — the first set from the boot default, an `NTP_Offset_S` change, a DST boundary — proven by clock-jump injection at L1/L2.
- **Sources**: G6 gap 2 · OR44.a (1) P1 · NET.T11, XCUT.T18, STOR.T09, plan 4.3
- **Rank**: agent — "(agent, 2026-09-27)"
- **State**: work: test in U18, U10
- **Home**: SPEC C.9/F
- **Pillar**: P1
- **Pass 2**: new

### LEAD/R06 The C stack has a budget
- **Req**: The deepest call and await chain (each nested `await` resume recurses in C) is budgeted against rp2's 8 KB C stack with a measured margin, and a `RuntimeError` from the stack check is never swallowed as a routine failure: it escalates through the supervisor.
- **Sources**: G4 gap 1 · OR26.a, OR18.a · `ports/rp2/CMakeLists.txt:661`, `py/mpconfig.h:813`, `py/runtime.c:1785-1786` (v1.29.0) · MEM.T09
- **Rank**: fact + agent — the stack size and check are v1.29.0 facts; the budget rule "(agent, 2026-09-27)"
- **State**: work: code in U30 (analysis); hardware in C (measurement)
- **Home**: SPEC F, I
- **Pillar**: P2
- **Pass 2**: new

### LEAD/R07 Every device build reports its image size
- **Req**: Each device build reports its firmware image size against the littlefs partition boundary and B0 records it, so OR72.a (7)'s "until flash space is actually short" has an observable trigger.
- **Sources**: G4 gap 2 · OR72.a (7) (D04)
- **Rank**: agent — "(agent, 2026-09-27)"
- **State**: work: code in U27/U20
- **Home**: SPEC B (build)
- **Pillar**: P6
- **Pass 2**: new

### LEAD/R08 One REST API reference, frozen at the release
- **Req**: The REST API (routes, keys, value types, units, ranges, result words) has one normative reference generated from the schemas and `@web` tags; the mock server, website tests and the live-twin PUT matrix are checked against it; from the release on a golden fixture of it, loaded by a `tests_scripts` check, fails on any unrecorded change (as OR52.a (2)'s stored-config fixture).
- **Sources**: G6 gap 1, G9 gap 4 · OR58.a, OR52.a (2), OR43.a (2)(3), A23 · P12 · RF067
- **Rank**: agent — "(agent, 2026-09-27)", on the owner's "the new API is the reference" (OR58.a)
- **State**: work: code in U19, U23; test in U19; work: code in U24/U26/U27/U23 — the route set (`asy_webserver_service.py:370-383`) is hand-copied in eight test/tool sites (`scripts/_digital_twin_ci_suite.py:1074`, `tests/_webserver_concurrency_scenarios.py:659`, `tests_hardware/bench/test_network_resilience.py:1034`, `tests_scripts/test_digital_twin_generated_boot.py:47`, `tests/test_digital_twin_bus_hazard_concurrency.py:107`, `tests_hardware/bench/test_memory_stress_bench.py:145`, `tests_hardware/bench/test_serving_heap_at_default_gc.py:27`, `tests_js/live-backend-put-matrix.test.js:15`), seven omit `GET /notification`; each derives its set, filtered by property, from the registration table or this reference (harmonization 31) (RF067)
- **Home**: SPEC A.8/H; `tests_scripts/`
- **Pillar**: P12
- **Pass 2**: new Refined: RF067.

### LEAD/R09 The website runs unattended indefinitely
- **Req**: A page left open for days keeps bounded resources (no growth of listeners, timers or DOM nodes; `startApp()` has a stop handle; every read-only field group, the errcount group included, is updated in place, not rebuilt; the poll interval is bounded above as well as below) and, after a device reboot or reflash, detects a changed build or `schemaVersion` on its next poll and reloads instead of polling with a stale bundle.
- **Sources**: G7 gap 1 · OR44 · WEB.T13, R42 (G7) · WEB.N225, N226, N272 · RF193, RF201
- **Rank**: agent — "(agent, 2026-09-27)"
- **State**: work: code and test in U23; `js/render.js:334-339` rebuilds every read-only field group of a live section (the whole Measurements page) on every 3 s poll — fresh subtree, listeners and closures, `replaceWith` (RF193); `js/definitions.js:124-127` rejects a non-positive poll interval but not one above 2**31-1 ms, which `setTimeout` turns into an immediate fire (latent: buildgen emits 3000, `buildgen/definitions.py:510`) (RF201)
- **Home**: SPEC H
- **Pillar**: P1
- **Pass 2**: new Refined: RF193 — Req widened from the errcount group to every read-only group; RF201 — upper poll bound added (agent, 2026-09-28).

### LEAD/R10 The website meets an accessibility baseline
- **Req**: Unique DOM ids (field ids namespaced by group), every label targeting its control, a closed drawer `inert` with focus handled, WCAG 2.1 AA contrast in both themes, a non-colour cue beside colour where A28 allows, `autocomplete` on password inputs, reduced motion honoured; proven by an automated accessibility check in `tests_js`.
- **Sources**: G7 gap 2 · OR44.a P4, OR43.a (2) · WEB.T07, WEB.S15-S17
- **Rank**: agent — "(agent, 2026-09-27)"
- **State**: work: code and test in U23
- **Home**: SPEC H
- **Pillar**: P4
- **Pass 2**: new

### LEAD/R11 The device TOML schema is one checked contract
- **Req**: SPEC L.3's key list is generated from, or checked against, `buildspec.py` (hand-kept by the owner's decision) and `validate.py` by a `tests_scripts` test; a key change updates every consumer in one commit.
- **Sources**: G8 gap 1 · OR24.a (2), OR68.a (2) (A2-02/03), P12
- **Rank**: agent — "(agent, 2026-09-27)"
- **State**: work: test in U20
- **Home**: SPEC L.3; `tests_scripts/`
- **Pillar**: P12
- **Pass 2**: new

### LEAD/R12 Shell scripts share one safety convention
- **Req**: Every script under `scripts/` runs `set -euo pipefail` or states why not, quotes every expansion and removes its temporary files in one `EXIT` trap.
- **Sources**: G8 gap 2 · OR24, OR38.a (1) · SCR.T08, SCR.S08, TOOL.S04, G8.077
- **Rank**: agent — "(agent, 2026-09-27)"
- **State**: work: code in U27
- **Home**: SPEC B (scripts)
- **Pillar**: P4
- **Pass 2**: new

### LEAD/R13 The frozen image is reproducible from its inputs
- **Req**: The same commit, the pinned toolchain and the pinned host CPython give byte-identical frozen inputs (generated modules, stripped copies, wiring plans, website; build date excepted) across hash seeds, and the same frozen-module order inside the image (`freeze()` of a directory follows an unsorted `os.walk`); the host Python behind `ast.unparse` is pinned or its output proven invariant.
- **Sources**: G8 gap 3 · HARVEST_REQUIREMENTS 3.3 (HR153), P11 · GEN.T11, SCR.T09, SCR.T11 · RF332 · MicroPython `v1.29.0` `tools/manifestfile.py:317`, `tools/makemanifest.py:198-254`
- **Rank**: agent — "(agent, 2026-09-27)"
- **State**: work: test in U27/U20; code in U27 — `scripts/build_firmware.py:42-45` freezes the staging directory, so mpy-tool receives the `.mpy` files in the host filesystem's directory order and identical inputs can give differently laid-out UF2s; the manifest lists the files sorted (RF332)
- **Home**: SPEC B/L
- **Pillar**: P11
- **Pass 2**: new Refined: RF332 — Req extended from the frozen inputs to the module order in the image (agent, 2026-09-28).

### LEAD/R14 Operator actions in one place
- **Req**: DEVICE_REFERENCE.md carries one commissioning and operating section listing every action that needs a person, with its trigger: Wi-Fi setup through the hotspot, the first `AmbPres` PUT that starts SCD30 measurement (OR71.a (2)), the manual `ForceCalRef` procedure (A14), ISL29125 calibration (A38), reading `reset_reason` (OR60.a), the reflash runbook (OR52.a (1), OR59.a); the runbook links to it.
- **Sources**: G9 gap 1 · OR44 ("without any user interaction once configured")
- **Rank**: agent — "(agent, 2026-09-27)"
- **State**: work: doc in U36
- **Home**: DEVICE_REFERENCE.md
- **Pillar**: P3
- **Pass 2**: new

### LEAD/R15 The release is a defined point
- **Req**: The audit's merge into `main` is the release: it carries the `buildgen/version.py` version as a git tag and a short release note of the user-visible changes against legacy (renamed keys, `reset_reason`, the overnight window, compare-before-write, the new API); the golden stored-config and REST fixtures are taken from it. The tag is pushed only at close, with the owner's agreement that the audit is finished.
- **Sources**: G9 gap 2 · OR5 ("a true release version"), OR52.a (2), OR58.a, OR11.a
- **Rank**: agent — "(agent, 2026-09-27)"
- **State**: work: rule in U37 (B5); tag in phase D
- **Home**: README.md (release); SPEC L (version)
- **Pillar**: P12
- **Pass 2**: new

### LEAD/R16 Tag form of a reviewed agent decision
- **Req**: A decision taken on the owner's behalf (OR2.c) keeps the agent as its actor after review: "(agent, date; owner-reviewed, date)"; where the owner rules differently, the owner's words and "(owner, date)" replace it.
- **Sources**: G9 gap 3 · OR2.c, OR68.a (4), OR71.a (0)
- **Rank**: agent — "(agent, 2026-09-27)"
- **State**: work: rule in U36 (CLAUDE.md working agreement with the prevention rules, B0)
- **Home**: CLAUDE.md working agreements
- **Pillar**: process
- **Pass 2**: new

### LEAD/R17 Conventions are machine-checked where cheap
- **Req**: A `tests_scripts` AST check over `src/` and generated code fails on the machine-checkable conventions — the `asy_` module marker, `_NAME` equal to the namedtuple name, starter names, the `errno=`/`wrnno=` keyword, no `print()`, `assert` or function-level import — ruff's global N801/T20 ignores narrow to the files that need them, and the `src/` per-file S101 exemption (`pyproject.toml:309`) goes with G10/R21.
- **Sources**: G10 gap 1 · OR24, harmonization 5 · G10.007, G10.016, `pyproject.toml:85,174,309` · RF272
- **Rank**: agent — "(agent, 2026-09-27)"
- **State**: work: test in U10; code in U28 (`pyproject.toml`); the D.15 member order (G5/R50, owner-confirmed 2026-09-13; alphabetical within role and all scopes except test functions, OR96.a) joins the checked list, so it does not re-drift after U10's reorder (RF272)
- **Home**: `tests_scripts/`; `pyproject.toml`
- **Pillar**: P4
- **Pass 2**: new. Verified: V4/V20 applied. Refined: RF272.

### LEAD/R18 Tests serve the real website
- **Req**: Every tier that serves a website (`scripts/test.sh`, `npm test`'s `pretest`, the twin runners) builds and serves a device's real website, never a placeholder, because the real website is the most biting test. The owner's rule named `dev`'s real website (2026-09-23), the richest site then; under OR54.a (1) and OR78.a the tiers serve the real site of every device the TOMLs define, `dev`'s included, never a hard-coded one. The binary fallback the real site has no file for is covered by its own test.
- **Sources**: L51 · SPEC:655-659
- **Rank**: owner — retirement of `html_stub/` "(owner, 2026-09-24)" (`12640c2`, paraphrase); the rule restored to its first record "the owner's rule (2026-09-23) is that `dev`'s real website is the most biting test" (`c349559`, OR83), its device scope carried by OR54.a (1)/OR78.a; L-list labels per OR82 (`verify/L25.md`)
- **State**: holds — `html_stub/` retired; doc: the tag gets its date form in U36
- **Home**: SPEC E/H
- **Pillar**: P5
- **Pass 2**: new (placed by the lead). Verified: V4/V21 applied.

### LEAD/R19 ISL29125 reports whether the light suits calibration
- **Req**: The ISL29125 driver publishes in `/measurements`, on every read, a numeric code for whether the current light suits the gain-ratio calibration: suitable (green counts inside the auto-range overlap band — the same test the calibration run applies), too dark, too bright, and "not applicable now" (fixed range, or the range still settling). The code table is defined once (SPEC M.1 and the field's `@web` tag); the Measurements page shows a plain-language label and colour cue next to the calibration fields. Tests at L1 (each code at its band edges), L2 (the twin's light model) and the website.
- **Sources**: OR76/OR76.a · `asy_isl29125_driver.py:638-641` · SENS.T (ISL29125), WEB
- **Rank**: owner — "we should add a field to the measurements API, a numerical code which tells if the current brightness is suitable, too high or too low for determining the calibration factor and show this on the measurements webpage in a user friendly way" (owner, 2026-09-28, OR76); the fourth code and its name "(agent, 2026-09-28)"
- **State**: work: code in U15 (driver, `@web` tag), U23 (website); test in U15, U25, U23; doc in U15 (SPEC M.1)
- **Home**: SPEC M.1; the field's `@web` tag
- **Pillar**: P3
- **Pass 2**: new (owner request after pass 2)

### LEAD/R20 One setup runner, like the starters
- **Req**: The generated `main()` passes the ordered setup list (OR75.a's order) to one `SystemService` method that loops over it, feeds the watchdog after each setup and does the placement collects of SPEC I.4(f.1); generated code carries no unrolled setup block and no `gc.collect()`. The collect allowance moves to that method (lint, `test_gc_collect_sites.py`, SPEC I.4(f.1), CLAUDE.md); the boot-contiguity test passes unchanged.
- **Sources**: OR84/OR84.a · `buildgen/codegen.py:455-467` · `src/system_service.py:209-216`
- **Rank**: owner — "a sysfunct function which gets the list of the setup functions to be called, and all of the looping, collecting and feeding is done automatically" (owner, 2026-09-28, OR84)
- **State**: work: code in U28 (codegen), U06 (system_service); test in U28, U06; doc in U06 (SPEC I.4(f.1), A.7), CLAUDE.md
- **Home**: SPEC A.7, I.4(f.1); CLAUDE.md memory rule
- **Pillar**: P4
- **Pass 2**: new (owner request after pass 2)

### LEAD/R21 Build intermediates kept for inspection
- **Req**: The firmware build stages its frozen `.py` modules and `manifest.py` in a persistent per-device directory under the gitignored `build/`, wiped at the start of that device's next build and kept after it (failed builds included), its path printed. Every other intermediate of the firmware chain (`build_website.sh`, `build_frozen_html.sh`) follows the same rule: clean at the start, never at the end.
- **Sources**: OR85/OR85.a · `scripts/build_firmware.py:139` · `scripts/build_website.sh:19-24` · `scripts/build_frozen_html.sh:19-20`
- **Rank**: owner — "Deletion / cleaning happens at the beginning of a build process, not at its end" (owner, 2026-09-28, OR85; an earlier demand stated by the owner, no trace found, OR64); extension to the website scripts "(agent, 2026-09-28)", on the owner-review list
- **State**: work: code in U30; test in U30 (L0: directory kept, wiped on the next build); doc in U30 (README build section)
- **Home**: README build section; SPEC B (build chain)
- **Pillar**: P7
- **Pass 2**: new (owner request after pass 2; lost owner decision, harmonization 27)

### LEAD/R22 Build option without autostart
- **Req**: `scripts/build_firmware.py <device>` has a device-agnostic option that builds the same image whose frozen boot entry keeps its settings (`.frozen` first, `gc.threshold`), prints the manual start line and returns to the REPL instead of running `main()`; default output `build/firmware-<device>-noautostart.uf2`. Its docs name the empty-VFS precondition (a returning frozen entry lets a filesystem `main.py` run).
- **Sources**: OR86/OR86.a · `scripts/build_firmware.py:95-99` · `buildgen/codegen.py:696-708` · `dev_legacy/README.md:602-611`
- **Rank**: owner — "a command line option for building a firmware which builds a version without autostart" (owner, 2026-09-28, OR86); the output name and the banner "(agent, 2026-09-28)"
- **State**: work: code in U30, U28; test in U30 (L0); doc in U30 (README, `--help`, OR15.a (1))
- **Home**: README build section; `--help`
- **Pillar**: P3
- **Pass 2**: new (owner request after pass 2)

### LEAD/R23 SGP40 reports its VOC-algorithm state
- **Req**: The SGP40 driver publishes the VOC algorithm's state it already holds — within the 45-sample blackout, inside the 24 h learning window (uptime), restored from a backup or started fresh — so an operator can tell a learning VOC index from a settled one after `SGPResetVOC`, a boot without a usable backup or a restore, while `WarnVOC` notifications already act on it: one field in the owner's LEAD/R19 form (numeric code, table in SPEC, label on the Measurements page via OR94.a (14)) (owner, 2026-09-29, OR97.a (17)).
- **Sources**: RF334 · OR76/OR76.a (analogous field), OR43.a (1) ("what a user needs to operate and diagnose the device"), OR44 · `src/voc_algorithm.py:15, :38`; `src/asy_sgp40_driver.py:61-77` (`@web` tags) · Sensirion Info Note VOC Index (`datasheets/sgp40/Info_Note_VOC_Index.pdf`, 24 h learning time) · SENS.S04
- **Rank**: owner — OR97.a (17) "(owner, 2026-09-29)"; code values "(agent, 2026-09-28)"
- **State**: work: code in U15 (driver field, `@web` tag), U23 (label); doc in U36 (SPEC M code table) (RF334)
- **Home**: SPEC Part M (SGP40); the field's `@web` tag; DEVICE_REFERENCE.md
- **Pillar**: P3
- **Pass 2**: new (refined harvest, RF334)

## 4 Questions for the owner (after self-resolution)

All four are answered: OR80, OR81, OR75, OR82. Questions 1-2 came from the groups (facts re-checked by the lead); questions 3-4 from the
verification, where an owner answer and the repo disagree.

1. **Answered 2026-09-28 (OR80): private repo as a submodule at `datasheets/`, history kept.** Was: "Vendor datasheet PDFs in the public repo: keep them?" Raspberry Pi's two carry CC BY-ND; Fujitsu,
   Renesas and Sensirion say "All rights reserved"; Bosch, Winbond, Worldsemi and Infineon grant nothing.
   (a) Keep all, with a note naming each copyright — no change; accepted legal risk.
   (b) Keep Raspberry Pi's; replace the rest by a list (title, revision, official URL, SHA-256) and
   gitignored local copies — history still holds them; sessions need a fetch step, some vendor hosts are
   blocked here.
   (c) As (b), plus a history rewrite — force-push to `main`, every cited commit hash breaks.
2. **Answered 2026-09-28 (OR81): in this audit.** Was: "Stricter typing (`disallow_any_explicit`): this audit or stay deferred?"
   (a) Stay deferred (your 2026-09-11 decision): counts re-measured in B0, one BACKLOG item with its
   reason.
   (b) In this audit: about 384 findings resolved in B2, with a typing scheme for test wrappers.
3. **Answered 2026-09-28 (OR75): tasks before timers.** Was: "Boot order: timers before tasks, or tasks before timers?" You confirmed OR47.a (1)'s order
   (setup batch, task starts, timer starts); the generated code starts the timers, then forces an NTP
   sync, then starts the tasks (`buildgen/codegen.py:476-478`).
   (a) Tasks first, as confirmed — the generated order changes; a timer never fires before its task
   exists; the NTP force sync moves before or after, tested at L2.
   (b) Timers first, as coded — OR47.a (1) is reworded; the first trigger may fire before its task runs
   (the flag waits for it); the reason is written into A.7.
4. **Answered 2026-09-28 (OR82): owner label where the source is verified and nothing drifted (18), agent otherwise (7), `verify/L25.md`.** Was: "Implementation choices with an owner tag in their history: label agent or owner?" You answered
   "keep them, labelled as agent design" for all 75; about 25 of them carry an owner tag or quote in
   their introducing commit (e.g. L12, L17, L30, L51; list in `audit/pass2/G9.md` R38).
   (a) All 75 "(agent, date)", as answered — the owner words stay cited as the reason where quoted.
   (b) Those ~25 keep "(owner, date)", the other ~50 "(agent, date)" — attribution follows the trail.

Also answered: the F18 reading is confirmed (OR83, option a). Still open from before: C12/C13 (UART chunking)
is deferred to BACKLOG's owner-question list (OR69.a (7)).
