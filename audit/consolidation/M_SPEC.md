# A-C merge SPEC (HEAD 546cdd8)

One file: `SPECIFICATION.md` (6,805 lines at HEAD; unchanged since the audit's starting merge `1dea035`, so every
action's line cite resolves against HEAD). Inputs: the 221 index pairs, 41 further actions whose Site names SPEC, every
Change/Blast clause of any action that writes SPEC text (grep of `audit/actions/*.md`), AC_NOTES 1-43, the finished
merges' gaps (GEN, SRC_SENS, SRC_CORE, SRC_NET, TEST_HELP, WEB, TWIN, HW_BENCH, HW_DEV, TEST_UNIT, SCR, TOOL; TSC has no
gap section yet). Owner answers written firm: OR131 (Microdot stubs, `ext/typings/microdot/`), OR132 (light-theme AA
tokens), OR133 (SCR Q1 (a): every runner, `test.sh` included, exits 2 on a usage or setting error, no exception).

Conventions every merged change below applies (stated once, not repeated per change):
- **C1 Permanent text cites no temporary audit ID** (G9/R12, AC_NOTES 4): no `OR`/`G`/`R`/`A.U`/`M.` ID, no
  `audit/` path, no wave/unit/work-package label in SPEC; actor tags read "(owner, YYYY-MM-DD)" / "(agent, YYYY-MM-DD)"
  (AC_NOTES 6); a constituent's quoted text that carries an ID loses it on landing.
- **C2 Current state, targets and rules, not history** (CLAUDE.md working agreement): where a constituent says
  "X was Y, now Z", SPEC states Z; measured dates stay as the date of a fact.
- **C3 Version facts** (OR129, LEAD/R33): A.SDEP.08 (U0) may move the MicroPython pin and A.U37's second check may move
  it again. Every Part F/B/I/J sentence naming `v1.29.0`, an upstream `file:line` or a stub version is written against
  the pin in force when it lands, re-checked against the refreshed pin (A.SDEP.17/.21); the texts below quote HEAD's
  `v1.29.0` citations as the constituents state them and the executor replaces the version token and re-verifies each
  line cite when the pin moved. A fact that no longer holds at the refreshed pin is rewritten, not kept.
- **C4 Part N row form** is A.U8.01's (ID, Value+unit, Sites, Dependants, Basis, Margin, Re-check trigger; rule rows
  name their check); "estimated (agent, <commit>) — measurement owed: <how, level>" where no measurement exists.
- **C5 Section numbers**: the end state's numbering is A.U36.532's (every section numbered, in its Part, listed under
  its Part); a merged change below names the HEAD number and, where it moves, the end-state number.

- **C6 A cited section exists before its first citer lands.** A.U0.08's citation check (U0) fails on a SPEC citation
  whose heading does not exist, so a merged change that creates a section is staged into the unit of the earliest
  action whose landed text cites that section (named per change as "Stage 1"), and the rest of its text lands in the
  latest constituent's unit. Renumbering (A.U36.532) repoints its citers in the same change.
- **C7 Product names are the merged ones.** SPEC text names symbols as the finished merges leave them (e.g. `src/`
  modules `asy_*` per A.U10.37/M.SRC_CORE; `SystemService`, `WifiService`, `NotificationService`, `NeopixelDriver`,
  `UARTLinkDriver`, `UARTComm`, `CRCPass`, `TickSeconds`, `utc_now()`; `_cfg_overlay()` for HEAD's `_mask_pw()`;
  no `register()`/`finalize()` on the notification service; the boot entry `sensortask_<device>_main.py` and
  `…_main_noautostart.py`, M.GEN.019). Where a constituent's quoted text names a HEAD or superseded name, the merged
  change below gives the end-state name; the executor greps each quoted symbol against the landed tree and uses the
  landed spelling.

## SPECIFICATION.md — front matter (`:1-28`)

### M.SPEC.001 Front matter: intro, Terms table, table of contents
- **From**: A.U36.541 (intro, TOC "Part 0"), A.U36.524 (6) (`:6-7` "pre-push verification" goes), A.U36.512 (1)
  (Terms table), A.U8.01 Blast (TOC "Part N"), A.U36.543 (8) (TOC Parts D and K renamed).
- **Site**: `SPECIFICATION.md:3-4` (intro), `:6-9` ("Not here, by design"), new `## Terms` before `## Table of
  contents`, `:11-25` (TOC).
- **Change**: (1) `:3-4` → "Central specification: design principles, architecture, build/toolchain mechanics,
  sensor-driver architecture, the `src/` quality bar, testing/coverage, platform facts, the website, the build chain,
  chip reference and the tunable-parameter register." (2) `:6-7` parenthesis → "(AI-session operating constraints —
  hard rules, working agreements, PR workflow, code-quality tooling)"; the rest of the paragraph unchanged. (3) After
  that paragraph, A.U36.512 (1)'s block verbatim except the device row's file names: "| device | The unit one
  `devices/<name>.toml` defines (the owner's "board variant"): its TOML, its generated `sensortask_<device>.py` and boot
  entry `sensortask_<device>_main.py`, its website; the CLI's `--device`, the TOML's `[device]` table. |" and the build
  flavour row listing all three flavours "`standard` (the test rig), `settrace` (`--coverage`), `lwip` (the patched
  modlwip over loopback lwIP)" (A.U21.12 lands in U21, before this U36 text). (4) TOC: first entry "- **Part 0** —
  Design principles (the concept, the pillars, the conventions catalog)"; "Part D — `src/` quality bar"; "Part K —
  Adding a module: the one ordered checklist"; last entry "- **Part N** — Tunable Parameters"; the other entries
  unchanged.
- **Resolved**: A.U36.512's term table named the HEAD boot-entry file `<device>_boot.py`; M.GEN.019 (U20) settles
  `sensortask_<device>_main.py` (C7). The TOC entry for Part N is added in U8 (Stage 1) because Part N exists from U8.
- **Unit**: Stage 1 U8 (TOC "Part N" line, with M.SPEC[N]); Stage 2 U36 (everything else).
- **Depends**: M.SPEC.002 (Part 0 exists), M.SPEC[N] (Part N).
- **Blast carried by**: README "Further reading" (Part 0, Part N named) → A.U36.547/A.U36.541 (5) (DOCS); CLAUDE.md
  `:6-7`-equivalent wording → A.U36.524 (2)-(4) (DOCS); the "variant" renames in the body → M.SPEC.004.
- **Kind**: doc

## SPECIFICATION.md — Part 0 (new, between the front matter and Part A)

### M.SPEC.002 Create Part 0, Design principles, sections 0.1-0.5
- **From**: A.U36.541 (1) (Part 0 text), A.U36.542 (1) (0.4 body), A.U36.031 (the P4 workaround principle).
- **Site**: new `# Part 0 — Design principles` after the front matter's `---` (`:28`), before `# Part A` (`:29`).
- **Change**: A.U36.541 (1)'s text verbatim (Sections line; 0.1 concept in the owner's words with "(owner,
  2026-09-26)"; 0.2 pillar table P1-P12 with "P1-P6 (owner, 2026-09-26); P7-P12 (agent, 2026-09-26)"; 0.3 structural
  patterns "(owner, 2026-07-13)" plus the extracted pattern "(agent, 2026-07-13)"; 0.5 "From principles to the
  checklist"), with these merged amendments: (a) 0.2 gains, directly after the "A new pillar is added …" sentence, one
  paragraph carrying A.U36.031's entry verbatim, introduced "Under P4:" — "**A workaround names its defect and its
  end** (agent, 2026-09-26). Code that works around a defect outside this repo — a stub gap, a CYW43 quirk, a
  MicroPython or Microdot limitation, a test-runner or hardware-harness quirk — says in its comment which defect, how far
  it reaches and what bounds it, and which event removes it (an upstream fix seen at a pin re-check, a tool bump); every
  pin or tool move re-checks it (Part F's opening checklist). A defect in a type stub is repaired at install time,
  guarded so the repair no-ops once upstream re-ships (B.15); where our own code narrows a type the checker cannot see, a
  narrow `type: ignore[<code>]` is preferred to an annotation that lies." (the stub-repair pointer names B.15, where
  A.U27.02/A.U27.03 move the repair account; F.5.5 keeps only the 1.29 delta fact, M.SPEC[F.5.5]). (b) 0.4's body is
  A.U36.542 (1)'s text, with: the `voc_algorithm.py` tag written "(agent, 2026-08-11)" (A.U0.40's L01 label,
  `f27b33b`); the "Comment tags" row → "| Comment tags (`@web`, `@web-group`, `@wiring`, `@value-wiring`, `@limits`,
  `@requires`, `@tunable`) | L.6.4 | `src/` (`@tunable`: every scope `tests_scripts/test_tunables_register.py` scans,
  N.2) | `tests_scripts/test_buildgen_*` grammar tests; `test_tunables_register.py` |"; the "Error and logging contract"
  row's enforcement also names `tests_scripts/test_error_catalog.py`; the "Config schema" row → "Config schema and each
  value's scope rule | C.5 | `src/`, generated | unit tests; `tests_scripts/test_config_schemas.py`"; and A.U36.542's
  landing check (each row's "Written in"/"Enforced by" read against the landed sections and checks; a check that did
  not land reads "review"). (c) 0.2's P12 row cites "H.6.1 (the website's wire contract)" — created by M.SPEC[H.6.1]
  (A.U36.044) in the same unit. (d) 0.5 as written ("walks Part K's ordered checklist … CLAUDE.md's bird's-eye scan
  checks new code against this Part").
- **Resolved**: A.U36.541 leaves A.U36.031's placement to A-C ("under P4 in 0.3's style, or a list after the table"):
  placed as one "Under P4:" paragraph in 0.2, since 0.3 holds only the owner's patterns and an unnumbered `###` would
  break A.U36.532's structure rule — agent decision, OR2.c review. A.U36.031 cites F.5.5 for the repair pattern;
  A.U27.03/A.U36.546 move that account to B.15, so the pointer names B.15. A.U36.542's catalog omitted the `@tunable`
  family A.U8.03 adds to L.6.4 (U8, earlier) and the scope rule A.U36.538 adds to C.5 (same unit): both rows follow.
- **Unit**: U36.
- **Depends**: M.SPEC.003 (structure rule), M.SPEC[C.*] (Part C sections the catalog cites), M.SPEC[D] (D.11,
  D.15), M.SPEC[L.6.4] (L.6.4 rows), A.U10.47/A.U36.038/A.U5.17 (the checks named, other clusters).
- **Blast carried by**: CLAUDE.md "Architecture reference" pointer, `:214` "indefinitely", `:68-91` (the `src/` and
  scan bullets) → A.U36.541 (3)-(4), A.U36.542 (2)-(3) (DOCS); README map → A.U36.541 (5)/A.U36.547 (DOCS); SPEC D.3
  `:2631` → M.SPEC[D]; Part K's opening points to 0.5 → M.SPEC[K]; A.U0.08/A.U0.09 checks resolve "Part 0"/"0.x"
  and read the tags → TSC (A.U0.08, A.U0.09); A.U36.532's test treats `0` as a Part letter → M.SPEC.003.
- **Kind**: doc, rule

## SPECIFICATION.md — whole-file structure

### M.SPEC.003 Every section numbered, nested, in its Part; Sections lines
- **From**: A.U36.532 (1)-(6), A.U36.541 (Part 0 is a Part), A.U8.01 (Part N is a Part), A.U36.524 (B.17), A.U33.05
  (B.16), A.U36.543 (K.5.1; D.0/D.13/D.14/D.16 leave D), A.U14.28 (F.7), A.U36.022/A.U15.05/A.U36.546 (M.2-M.6),
  A.U29.01 (A.11), A.U7.02 (E.10), A.U36.017 (E.2.2), A.U36.044 (H.6.1), A.SDEP.22 (F.5.10).
- **Site**: every `# Part` heading; `:2809` (E.2.1), `:4427` (H.5.1), `:4547`, `:4648`, `:4681` (H.7 subsections),
  `:5183-5313` (I.6), `:3866-4066` (F.5.7-F.5.9).
- **Change**: A.U36.532 (1)-(5) as written: `## E.2.1` → `### E.2.1`; `## H.5.1` → `### H.5.1`; I.6 moves verbatim (as
  M.SPEC[I.6] leaves its text) to the end of Part I after I.5; H.7's subsections become `### H.7.1 The connection ceiling
  (`max_connections`, `backlog`, lwIP pcbs)`, `#### H.7.1.1 A connection's real lifetime, …`, `### H.7.2 Cross-browser
  coverage`; F.5.7-F.5.9 move to `## F.8 `machine.UART` on rp2: standing facts` as F.8.1-F.8.3 placed after F.7 with
  their own cross-references renumbered and every citer A.U36.532 (4) lists repointed in the same change, plus every
  citer another action adds before U36 that names F.5.7/F.5.8/F.5.9 (A.U13.12, A.U13.13, A.U13.19, A.U17.*, A.U26.59,
  A.U8C2.39/.42, A.U31.05, A.U16.07, A.U33.07 and the merged texts M.SRC_NET/M.HW_DEV/M.TEST_UNIT cite — grep "F.5.7",
  "F.5.8", "F.5.9" over the tree at landing, `audit/` aside); each `# Part` heading is followed by one "Sections: X.1
  <title> · …" line listing its `##` sections in order (Part 0 keeps the line A.U36.541 writes). The heading's version
  qualifier "(verified at v1.29.0)" is written with the pin in force at landing (C3). The structure test (A.U36.532 (6),
  TSC's file) takes the Part letters `0`, `A` … `N` (not `A` … `M`): Part N exists from U8.
- **Resolved**: A.U36.532's Part-letter list stops at M, written before Part N's creation was counted; A.U8.01 (U8)
  creates Part N, so the letters are `0, A … N`. New sections created by other actions (A.11, B.16, B.17, E.2.2, E.10,
  F.5.10, F.7, F.8, H.6.1, K.5.1, M.2-M.6, N.1-N.4) appear in their Part's Sections line; D's line lists D.1-D.12, D.15
  (numbers ascend with gaps, as A.U36.532 allows). F.5.10 (A.SDEP.22) is a standing re-check list, not a 1.29 delta
  item: placed as F.9 — see M.SPEC[F.9].
- **Unit**: U36 (the move of F.5.7-F.5.9 and every Sections line); the heading-level fixes land with it.
- **Depends**: every section-creating change below (M.SPEC[A.11] A.11, M.SPEC[B.16-17] B.16/B.17, M.SPEC[E.10] E.10,
  M.SPEC[E.2.1-2] E.2.2, M.SPEC[F.7] F.7, M.SPEC[F.9] F.9, M.SPEC[H.6.1] H.6.1, M.SPEC[K] K.5.1, M.SPEC[M.2-6] M.2-M.6,
  M.SPEC[N] N).
- **Blast carried by**: the F.8 citers outside SPEC (`src/asy_uart_driver.py`, `tests/…`, `digital_twin/machine.py`,
  `tests_hardware/…`, CLAUDE.md, BACKLOG, `UART_C_PORT_CHANGELOG.md:95`) → A.U36.532 (4) itself, executed in U36 across
  files (its SRC/TEST/TWIN/HW/DOCS sites are carried by that action; no other cluster merges them); new L0
  `tests_scripts/test_spec_structure.py` → TSC (A.U36.532 (6), letters per the resolution above).
- **Kind**: doc, test

### M.SPEC.004 "variant" names one concept only, across SPEC
- **From**: A.U36.512 (2)-(3) (SPEC sites).
- **Site**: `SPECIFICATION.md:85`, `:451`, `:740`, `:2898`, `:3059`, `:3066`, `:3213`, `:3253`, `:4010`, `:4106`,
  `:6008`, `:6012`.
- **Change**: A.U36.512 (2)-(3)'s SPEC replacements verbatim ("device" for the TOML-unit sense, "build flavour" for the
  Unix-port sense; `:6012` → "## L.1 Devices and the two standing acceptance criteria"). Each replacement lands inside
  the section text that another merged change rewrites where one does: `:2898` with M.SPEC[E.2.1-2] (E.2.1, A.U36.016),
  `:3059`/`:3066` with M.SPEC[E.5.2] (E.5.2, three flavours after A.U21.12/A.U27.12), `:451` with M.SPEC[A.7] (A.7),
  `:3213`/`:3253` with M.SPEC[E.6.6] (E.6.6), `:6008`/`:6012` with M.SPEC[L.1] (L.1); a sentence another change deletes
  needs no rename.
- **Resolved**: — (pure word replacement; where a rewrite removes the sentence, the rename is void).
- **Unit**: U36.
- **Depends**: M.SPEC[A.7], M.SPEC[E.2.1-2], M.SPEC[E.5.2], M.SPEC[E.6.6], M.SPEC[L.1].
- **Blast carried by**: CLAUDE.md/README/code/test renames → A.U36.512 (4)-(6) (DOCS, TOOL M.TOOL.056, SCR, TSC).
- **Kind**: doc

- **C8 U0's tag and decision wording folds into the section's merged text.** A.U0.12/.16/.17/.19/.21/.25/.29/.30/.33/
  .37-.44/.56/.60 write actor tags and answered decisions across SPEC in U0. Where a later action rewrites the same
  sentence, the U0 wording is carried inside that section's merged change (its tag survives in the end-state text) and
  lands with it; where no later action touches the sentence, the U0 edit is its own merged change landing in U0. The
  decision-vocabulary allow-list (M.TSC.010) is generated at U0's landing and shrinks when each tag lands, so the
  deferral needs no extra work.

## SPECIFICATION.md — Part A

### M.SPEC.005 A.1: one `legacy/` block, current vendored pins, no history
- **From**: A.U1.14 (legacy block), A.U1.08 (`dev_legacy/` entry; covered by A.U1.14), A.U0.38 V01 (`:38-39`),
  A.U34.01 Blast (one `arduino/` wording), A.U36.548 (4) (`:59-60`), A.U36.511 (2) (`:64`), A.U36.512 (3) (`:85`),
  A.U36.543 (8) (`:54`), A.SDEP.06 (`:62` tag), A.U34.12 Blast and A.U8.23 Blast with OR131 (`ext/typings/microdot/`
  line), A.U34.08 (2) and A.SDEP.07 (`:63`), A.U36.545/A.U28.35 (gap: `:34-35` datasheets line).
- **Site**: `SPECIFICATION.md:33-92` (A.1 code block).
- **Change**: in the code block — (1) `datasheets/` (`:34-35`) → "datasheets/              Private submodule
  `hundertvolt/datasheets`: the chips' datasheet PDFs (A.6)" with its folder line unchanged. (2) `arduino/` (`:36-39`)
  → its first three lines unchanged, the fourth → "Post-audit only (owner, 2026-09-25: 'the C port stays out of scope,
  anything there is post-audit only'): no lint, type check, test, licence or secret review here (secret scan: owner,
  2026-09-30)". (3) `dev_legacy/` (`:40-41`), `html_raw/` (`:42-44`), `modules/` (`:47-49`), `python/` (`:50-53`),
  `build-{arzi,dev,neu,wozi}.sh` (`:87`) and `update_and_install.txt` (`:88`) go; after the `html/, js/, …` entry one
  entry "legacy/                  Reference-only legacy tree (CLAUDE.md; legacy/README.md)" with the children
  "  firmware/                the legacy units' firmware (MicroPython 1.24.1), the old root layout unchanged: python/,
  modules/, html_raw/, the four build-*.sh, update_and_install.txt" and "  dev_drivers/             the dev unit's
  2026-08-27 on-device snapshot" (A.U1.14). (4) `src/` (`:54-60`): "(Part D)" → "(Parts K, D)"; the sentence
  "improved-quality/ (former WIP staging) has been fully retired and deleted." goes; the rest unchanged. (5) `ext/`
  (`:61-63`): "microdot.py               Microdot <tag>, unmodified (A.5)", a new line "  typings/microdot/        its
  upstream type stubs of the same tag, unmodified, never frozen (B.15)", and "freezefs/                 freezefs `main`
  at `<commit>`, unmodified - the website's gzip+freeze pipeline (A.9)" — `<tag>` is the Microdot tag and `<commit>` the
  freezefs commit (short SHA) that U0's dependency refresh leaves (A.SDEP.06/.07; `v2.6.2` and `26be9e3` if nothing
  moved). (6) `devices/` (`:64`) "One TOML file per device variant" → "One TOML file per device". (7) `toolchain/`
  (`:85`) "builds RP2040 firmware and both Unix-port variants" → "builds RP2040 firmware and every Unix-port build
  flavour". (8) `tests_hardware/` (`:81-82`) gains "and the dev bench's wiring and state" (A.U1.14).
- **Resolved**: A.U0.38 (V01) and A.U34.01 word the `arduino/` exclusion differently; A.U34.01 asks A-C to keep one
  wording — the owner's quote (V01) plus A.U34.01's review list and its 2026-09-30 secret-scan clause (OR127). The A.1
  `datasheets/` line becomes false after A.U28.35 moves the PDFs; no action edits it (gap, my site) — rewritten here.
  OR131 (firm): the stub line names `ext/typings/microdot/`.
- **Unit**: Stage 1 U0: (2) (A.U0.38) and (5) with A.SDEP.06/.07 and OR131's re-vendor; Stage 2 U1: (3), (8) with
  A.U1.14; Stage 3 U34: (5)'s freezefs commit form only if U0 did not move it (A.U34.08); Stage 4 U36: (1), (4), (6), (7). Each stage is a
  disjoint line set; no stage is a prerequisite of another unit's work except Stage 1, which keeps A.1 true when the
  vendored files change in U0.
- **Depends**: A.U1.01-A.U1.04 (the move), A.SDEP.06/.07, A.U28.35 (datasheets move; owner step first, AC_NOTES 37).
- **Blast carried by**: A.U1.09's old-path check (TSC) reads A.1 → A.U1.09; README/CLAUDE.md/THIRD_PARTY wording of
  the same exclusion → A.U34.01/A.U34.02 (DOCS).
- **Kind**: doc

### M.SPEC.006 A.2: the architecture summary states the merged product
- **From**: A.U36.535 (1)-(3), A.U1.15 (`:102-104`), A.U10.09 (supervisor text), A.U31.07 Blast (escalation at the
  first task end past the budget), A.S0930.41 (A.2's escalation text holds: direct reset), A.U27.07 Blast (`:110` drops
  `parse_cmd_request()`), A.U10.37/A.U10.38 (names, C7).
- **Site**: `SPECIFICATION.md:94-127` (A.2).
- **Change**: (1) `:96-99` → "… with a `*_Reader` wrapper giving the common async-task surface (`start_asy_read`/
  `start_asy_trigger`/`start_timer`, its last sample under a lock, an error counter, config callbacks). Full spec: Part
  C." — the starter names as A.U10.44 leaves them (C7). (2) `:102-106` → "**Config management** — the legacy firmware
  (`legacy/firmware/`) uses `async_manager.ConfigManager`: one ad hoc instance per device, flat JSON, self-healing
  corruption by overwriting the whole file with hardcoded defaults (a legacy unit is never upgraded in place: it is
  reflashed with fresh setup, owner 2026-09-26). `src/asy_config_manager.py`'s `ConfigManager` replaces it: every module
  owns its schema (`ConfigSchema` tuple) and config file via a public `cfg_schema` attribute (C.5)." (3) `:107-111` →
  "**REST API pipeline** — the legacy `api_helpers.py` chains `cmd_pre_check → init_json_from_cfg → update_valid_json →
  set_sensor_value → cmd_post_check` per PUT. `src/asy_api_response.py` replaces it: `SensorReader._set_dict_cfg()`
  (`asy_base_classes.py`) is every module's generic schema-driven setter and `make_response()`/`handle_set_cmd()` give
  every endpoint one response envelope (C.5.3)." (4) `:112-115` → "**FRAM storage** (on every device whose TOML
  declares a `fram` instance — today all of them) — a bump allocator handing out chunks as two redundant copies, so a
  power loss or watchdog reset mid-write leaves one valid copy. Used for the per-module error logs and SGP40's VOC
  baseline backup." (5) `:118` `NotificationCoordinator` → `NotificationService`. (6) `:120-122` "Deployed code still
  uses the monolithic `async_connect.py`." → "The legacy firmware uses the monolithic `async_connect.py`." (7) `:123-125`
  → "**Task supervisor** (`asy_system_service.py`'s `supervise_tasks()`, started by every generated
  `sensortask_<device>.py`'s `main()`) — two-tier self-healing: a dead task restarts, each end logged once as a persisted
  SYSTEM entry (decaying error score); at the first task end past the budget the supervisor feeds the watchdog once,
  then stops feeding one-way and reboots directly through `SystemService._reboot()` (reset reason recorded, staged config
  flushed, FRAM paused, reset `_RESET_DELAY` later) (owner, 2026-09-30); a reset timer that cannot be armed leaves the
  watchdog to reset the device. A unit runs indefinitely without anyone once configured (owner, 2026-09-26; Part 0)."
- **Resolved**: A.U36.535 (3) names `start_and_check_tasks()`; A.U20.06 (U20) splits it into `start_tasks()`/
  `supervise_tasks()` (C7). A.U10.09's text predates OR130 (U31's one feed before the stop, A.U31.07 firm, AC_NOTES 36)
  and A.S0930.41's statement that the escalation resets directly without the controlled sequence; both are folded in.
  `:122`'s "Deployed" framing of the legacy firmware is rewritten by the same rule A.U1.15 applies (`:102`; no action
  names `:122` — adherence fix).
- **Unit**: U36 (the summary describes the U10/U11/U20/U31 end state; nothing cites a new A.2 sentence earlier).
- **Depends**: A.U11.03, A.U20.06, A.U31.07, A.U10.44 (names), M.SPEC[renames].
- **Blast carried by**: `tests_hardware/README.md:1280-1286` and `BACKLOG.md:89-90` → A.U10.09 (HW_BENCH/DOCS);
  `src/asy_system_service.py:1` header → A.U36.535 (5) (SRC_CORE carries the file).
- **Kind**: doc

### M.SPEC.007 A.3: refactor status as today's fact
- **From**: A.U28.12, A.U1.15 (`:131-134` legacy clause), A.U36.543 (8) (`:135`), A.U36.511 (1) (`:137-146`, with
  A.U0.25's A06 tag), A.U36.548 (G9/R11: "not yet `arzi`/`neu`" dropped), A.U0.23 Blast (A06 at `:143-145`).
- **Site**: `SPECIFICATION.md:129-146` (A.3).
- **Change**: first paragraph → "Targets the latest stable MicroPython/pico-sdk/picotool/Microdot at the pin the
  owner moves (F.1), expands error handling and fault recovery, and adds unit tests, mypy, ruff and CI (every tool its
  own CI job; the job list and why each is shaped as it is: B.10). Code lands in `src/` by Part K's checklist." Second
  paragraph → A.U36.511 (1)'s text verbatim, with the generated files named `sensortask_<device>.py` and boot entry
  `sensortask_<device>_main.py` (C7).
- **Resolved**: A.U28.12 and A.U1.15 edit the same sentence (job list vs legacy clause): one sentence carries both
  (A.U28.12's Depends names A.U1.15). "latest *stable*" vs the owner's pin rule (A.U0.33 C05 at F.1 `:3441-3442`, owner,
  2026-09-26): A.3 states the pin rule by pointer, so the two Parts agree.
- **Unit**: U36.
- **Depends**: M.SPEC[F.1] (the pin sentence it points to), M.SPEC[renames].
- **Blast carried by**: —
- **Kind**: doc

### M.SPEC.008 Module and class renames reach every SPEC mention
- **From**: A.U10.37 (module renames: "SPEC/CLAUDE.md/… every text mention updated"), A.U10.38 (class renames, "docs
  SPEC (many)"), A.U10.35 (privatised attributes SPEC names), A.U10.44 (starter/coroutine names, Blast "SPEC C.4.1,
  C.9, A.7"), A.U10.18 (lock names, Blast "SPEC C.8, G.2, A.7"), A.U10.39 (`_VAL_` names), A.U10.40 (REST/config key
  scheme, Blast "SPEC A.8, H, C.5.3"), A.U10.43 (unit suffixes, Blast "SPEC C.9.1, L.3"), A.U10.41 (`NTPHost`), A.U2.23
  (renumbered codes).
- **Site**: every SPEC mention of a renamed module, class, attribute, starter, lock, key, TOML key or code (grep each
  old name over `SPECIFICATION.md` at landing).
- **Change**: in U10's commits, each old name → its new name wherever SPEC names it (module `asy_*` names; classes
  `WifiService`, `NotificationService`, `UARTLinkDriver`, `NTPClient`, `UDPSocket`, `FRAMManager`, `FRAMChunk`,
  `FRAMChunkBuffer`, `FRAMTimestampedChunk`, `FRAMChunkTimestampedBuffer`, `CaptiveDNS`, `CRCBase`, `CRCPass`,
  `FramingBase`, `FramingPass`, `FramingCOBS`, `UARTComm`, `BMP3XX_Reader`; locks `<purpose>_lock`; REST/config keys per
  A.U10.40's table; TOML keys per A.U10.43); in U2, every cited error number → its catalog number and name (A.U2.23).
  A sentence another merged change below rewrites in a later unit takes the new name directly (C7); a sentence it
  deletes needs no rename. Quoted owner words keep their spelling. Logger names (`"SYSTEM"`, `"CFGMGR_*"`) and FRAM
  layout names do not change.
- **Resolved**: — (mechanical; the later section merges use the renamed spellings).
- **Unit**: Stage 1 U2 (codes, A.U2.23); Stage 2 U10 (names, A.U10.18/.35/.37-.44). A.U0.08's citation check reads
  `SPECIFICATION.md` Part citations, not symbol names, so neither stage gates a check.
- **Depends**: A.U2.01 (catalog), A.U10.37-A.U10.44.
- **Blast carried by**: CLAUDE.md/README/other docs → the same actions (DOCS); code/tests → SRC/TEST clusters.
- **Kind**: doc

### M.SPEC.009 A.4 legacy-module bullets: legacy paths, actor tags, current names
- **From**: A.U1.15 (`:150, :152, :156`), A.U0.42 (`:162-163`), A.U0.39 L04 (`:164-165`), A.U10.37/A.U10.38 (names).
- **Site**: `SPECIFICATION.md:150-167`.
- **Change**: `python/CommonDrivers/…` → `legacy/firmware/python/CommonDrivers/…` (three bullets); `:157-158`
  "`src/config_manager.py`/`src/base_classes.py`'s" → "`src/asy_config_manager.py`/`src/asy_base_classes.py`'s";
  `:159-161` "always import by name from `config_manager`/`base_classes`, never `async_manager`" → "… from
  `asy_config_manager`/`asy_base_classes` …"; `:162-163` "(accepted: this device is the file's only writer)" →
  "(agent, 2026-07-16, `83c08ae`: this device is the file's only writer)"; `:164-165` "(no schema at all, confirmed by
  the project owner)" → "(no schema at all; owner, 2026-08-05)"; `:166-167` "(`asy_wifi_service.py`/
  `asy_ntp_client.py`)" unchanged (module names already `asy_`).
- **Resolved**: —
- **Unit**: U10 (the U0/U1 halves fold into one edit with the renames, C8; no earlier unit cites these sentences).
- **Depends**: A.U1.01 (legacy move), A.U10.37.
- **Blast carried by**: `src/asy_config_manager.py:7` pointer to A.4 → A.U0.42 (SRC_CORE).
- **Kind**: doc

### M.SPEC.010 A.4 FRAM bullet: one current account of the chunk store
- **From**: A.U16.12 (protocol elements), A.U0.41 (`:178`, `:196` tags), A.U16.09 (`:178`, `:201-202`), A.U16.11
  (status-byte endurance), A.U36.546 (2) (MB85RS64V fact → M.6), A.U0.25 A10 (`:188`), A.U0.33 A2-01 (`:189`), A.U11.03
  (`:195-198`, `:226-231`), A.S0930.30 (erase, `:226-231`), A.S0930.41 (`:195-198`), A.S0930.17 Blast (0x00 proof),
  A.S0930.25 Blast (power-loss proof cited), A.S0930.14 Blast ("every deliberate reset pauses FRAM first" holds),
  A.U16.06 (unreadable chunk, `:205-206`), A.U16.19 (`:207-208`), A.U16.08 (`:214`), A.U16.18 (`:214-215`), A.U0.38 V12
  (`:215-217`), A.U16.03 (first boot after a reflash), A.U16.02 (determinism rule's checks), A.U16.17 (declared chip
  failing setup), A.U16.R02 (three identification attempts), A.U16.R03 (chip lost mid-operation), A.U2.09, A.U3.04,
  A.U2.23 (codes and the one-entry flow), A.U20.02/A.U24.54 (the `WDT()`-site half), A.U10.38 (class names).
- **Site**: `SPECIFICATION.md:168-236` (the `asy_fram_driver.py`/`asy_fram_manager.py` bullet).
- **Change**: the bullet, in this order (each paragraph's facts as the constituent states them; C7 names):
  1. Head: "`asy_fram_driver.py`/`asy_fram_manager.py` — raw SPI FRAM driver and chunk allocator with dual-copy
     redundancy (every device whose TOML declares a `fram` instance)." The 2026-09-18 restructure sentence keeps its
     facts (synchronous byte-level path under a caller-held lock, `session_begin()`/`session_end()`, the 2 µs CS settle,
     `get_values_sync()`/`set_values_sync()` plus `report_get_values()`/`report_set_values()`, the async forms kept for
     other bus users) and loses "Every `errno`/`wrnno` keeps its number and meaning; only the logging site moved up"
     (false after U2/U3): "a chunk failure persists one entry, the driver's (C.7)".
  2. A.U16.12's paragraph verbatim ("What each protocol element is for (owner, 2026-09-18): … pinned by
     `tests/test_asy_fram_wire_trace.py`."), whose status-byte clause already carries A.U16.09's "a blank copy is not
     read, so it takes no marker".
  3. The busy/idle consequence (`:177-188`): "Each chunk stores two copies plus a busy/idle status byte guarding reads
     and writes (reads too: owner-confirmed, 2026-07-18, `c9dde56`; a blank block is left blank: it is never read). The
     chip reads destructively — every read is a read-then-restore (M.6) — so a power loss mid-read is as real a risk as
     mid-write: `_read_chunk()` marks a block busy before reading and restores idle on the way out, an interruption on
     both copies makes every later read fail the status check until a write clears it, and refusing those bytes is
     correct (owner, 2026-09-10, `2e523d2`: the owner confirmed the design intent; don't 'fix' it). Pinned by
     `tests/test_asy_fram_manager.py`'s `test_an_overrun_mid_read_leaves_the_chunk_unreadable_until_it_is_rewritten`.
     Its busiest cells are a chunk's status bytes — 3 operations per read, 2 per write; even one block taking every
     block operation the bus allows would wear them past 10^12 only after ~140 years (pinned in
     `tests/test_asy_fram_wire_trace.py`)." The MB85RS64V datasheet quote (endurance and "destructive readout") moves
     to M.6 (M.SPEC[M.2-6]).
  4. Error-log cost (`:189-200`): "**What this costs at the error-log layer** (owner, 2026-09-11; confirmed
     2026-09-26): an abrupt reset that catches both copies marked loses that module's whole persisted history, at
     roughly 1 abrupt restart in 8 in the twin — accepted; the loss is all-or-nothing, never a partial or garbled
     restore. A commanded reset loses nothing: it runs the controlled shutdown (A.8) — FRAM is paused and every chunk
     operation drained before any task is stopped, and the reset path pauses FRAM again before arming (the pause
     finishes ongoing operations and rejects new ones: owner-confirmed, 2026-07-18, `c9dde56`), which gates every
     `_write()`/`_read()`/`clear()` so nothing can be in flight; the supervisor's own budget reboot writes the
     reset-reason record, flushes every staged config write and pauses FRAM before arming its one-shot reset (A.2).
     Covered at every tier — `tests/test_fram_integration.py` (both blocks torn), the twin's Run 5c (a real commanded
     reboot), `tests_hardware/flash/test_fram_storage.py`'s reset-race pair on silicon." The twin figure for the
     commanded case is the one A.U25.36 re-measures (no "20/20" figure, A.S0930.41).
  5. Unreadable vs invalid (A.U16.06): "A chunk that cannot be read is left untouched and its owner logs in RAM until
     the next boot; only a chunk proven blank or invalid is re-initialised. A read that faulted after marking its block
     leaves the busy marker set: the next boot reads that block as invalid, like any interrupted operation, so a fault on
     both copies keeps the stored history for the current boot only — the next boot re-initialises the chunk." Plus
     A.U16.03: "The first boot after a reflash re-initialises every chunk the new build no longer recognises, pinned per
     device."
  6. Write protection (`:201-213`): A.U16.09's "… must WRITE the transient busy marker before it may read a written
     block (a blank block is not read and takes no marker, so it reports uninitialised even when protected) …"; "it
     fails *at* the chip (the status byte is clocked off the bus first, then the marker write is refused on each block,
     a read fault)"; "One property separates it from the pause gate"; the `override_pause` clause goes (A.U16.19); the
     silicon-only claim and `fram_write_protect_roundtrip.py` sentence stay.
  7. `:214-217` → "'Both copies valid but different' is a hard failure (no generation counter), never guessed (owner,
     2026-07-18). `FRAMTimestampedChunk.write()`/`write_into()` return `(success, ntp_synced, utc)`, bool first like
     every other chunk method; `read_into()`'s age is signed, and a negative age is expired under a nonzero
     `BackupMaxAge`. `FRAMManager` is a bump-pointer allocator: construction order is the on-chip layout, fixed and
     deterministic within one firmware build; FRAM content need not survive a reflash (owner, 2026-09-26: 'there is no
     requirement for the fram to stay consistent through firmware re-flashes')."
  8. Determinism rule (`:218-225`): kept, with "a full reboot replays `build_system()`'s construction from scratch" and
     the owner list rewritten generically — "every FRAM-chunk-owning construction is an unconditional top-level
     statement of the generated module" — and A.U16.02's clause: "pinned per device by the layout scenario and by
     `tests_scripts/test_fram_chunk_owner_sites.py`".
  9. Chip faults (A.U16.17 + A.U16.R02 + A.U16.R03): "A FRAM chip declared in the device TOML that fails `setup()` —
     after up to three identification attempts — escalates like any declared chip (owner, 2026-09-29: 'the same as all
     other chips'): one supervised task that ends at once, so the supervisor reboots past its budget; modules log in
     RAM until then. A chip that stops answering its identification after boot stops all FRAM access, ends the
     manager's task and is set up again by its restart; a chip that stays lost reboots the device through the
     supervisor. Where no chip is declared, every module runs RAM-only (owner, 2026-08-11)."
  10. Erase (A.S0930.30/.17): "**Erase FRAM** (`SystemCmd` `erasefram`, owner, 2026-09-30) marks every chunk's blocks
      blank first, then zeroes the whole chip in 256-byte units; a blank block reads as a new chip's, and no
      interrupted later write can leave a block that validates (the two gates: the blanking pass runs before any byte
      is zeroed, and a chunk whose blanking failed stops the erase before pass 2). A power loss at any step leaves a
      bootable state (L1-proven per step)."
  11. Reset paragraph (`:226-236`) → "Every deliberate reset pauses FRAM first: the system commands close FRAM before
      stopping tasks (A.8), and `_reboot()` pauses it before arming the reset and before the watchdog-starve fallback.
      Margin: a two-block write with its CRC read-back takes a few milliseconds at 1 MHz (2.8-3.4 ms per one-byte write
      measured on silicon, F.8.2), three orders of magnitude under the 4 s reset delay and the ~8 s watchdog. The
      `machine.reset()`/`bootloader()` call sites are confined to `asy_system_service.py` by
      `tests/test_reset_call_site_invariant.py`, and the one `WDT()` construction — the generated boot entry's first
      statement (A.7) — by the same test over the generated boot entries."
- **Resolved**: A.U16.11 (A.4) and A.U36.546 (2) (move the MB85RS64V fact to M.6): the datasheet fact moves, the
  project consequence (status-byte endurance, busy marker) stays in A.4 with a pointer — both constituents' intents
  kept. A.U11.03's and A.S0930.41's rewrites of `:195-198` merge: A.S0930.41 (later, SUPP) supersedes the "20/20"
  figure; A.U11.03's order describes the supervisor's own reboot. A.U0.38 V12, A.U16.01 and A.U16.18 word the layout
  rule; one sentence (owner quote from V12). `:175-176`'s "keeps its number" is false after A.U2.09/A.U3.04 (no action
  names it — adherence fix). The 8 KB chip size (`:228`) is a TOML fact (G8/R01, OR78): replaced by the measured
  per-write time. The `WDT()`-site sentence follows A.U20.02 (WDT in the boot entry) and A.U24.54 (the invariant test
  globs boot entries) — "permanently vacuous" goes.
- **Unit**: U36 (latest constituents A.U36.546 and the U36 doc pass; every earlier unit's behaviour is described as its
  end state). No earlier unit cites a new A.4 sentence by section text.
- **Depends**: M.SPEC[M.2-6] (M.6 exists in the same unit), A.U16.*, A.S0930.17, A.U11.03, A.U20.02, A.U24.54.
- **Blast carried by**: `tests/test_asy_fram_wire_trace.py:2, :499` → A.U16.12 (TEST_UNIT); `src/asy_fram_manager.py:3`
  → A.U16.01 (SRC_CORE); `tests_hardware/README.md:430-432` stays true (A.U16.01).
- **Kind**: doc

### M.SPEC.011 A.4 SCD30 bullets: chip-store behaviour, first start, not-ready cycle, participant rung
- **From**: A.U15.04 (new read-timing bullet), A.U15.06 (`:237-245` rewrite and the not-ready bullet), A.U0.25 A14
  (`:242` tag), A.U4.04 Blast (`:237-240` `force=True`; superseded by A.U15.06's text, which states the chip-store
  behaviour), A.U4.05 Blast (rounding; in A.U15.06's text), A.U15.R01 (soft reset rung).
- **Site**: `SPECIFICATION.md:237-245`.
- **Change**: four bullets in this order: (1) A.U15.04's "**SCD30 read timing and first start.** …" verbatim, gaining
  at its end "A second consecutive failed read soft-resets the chip (no NVM write), the participant rung of the
  recovery ladder (C.7)." (2) A.U15.06's `AmbPres` bullet verbatim. (3) `ForceCalRef`: the HEAD text "recalibration is
  manual: ventilate until indoor CO2 matches outdoor ambient, then set `ForceCalRef` to that value via REST. No
  automation planned (owner, 2026-08-11, `acc4993`)." plus A.U15.06's sentence "Every `ForceCalRef` PUT is carried out,
  never "Unchanged" — its read-back is volatile (400 ppm after power-up, Interface Description p14, 'Set Forced
  Recalibration value') (owner, 2026-09-26)." and one pointer "Whether the light conditions suit a recalibration is
  published as `FRCState` (M.2)." (4) A.U15.06's `TempOffs` bullet verbatim, then its "**SCD30 not-ready cycle.**"
  bullet verbatim.
- **Resolved**: A.U4.04's "`force=True` … genuine truncation" wording (Blast) is the HEAD text A.U15.06 replaces (U15
  after U4); A.U15.06 states the rounding A.U4.05 implements. The `FRCState` pointer joins the M.2 code table
  (A.U15.12/A.U36.537) to the operator bullet (agent decision, OR2.c).
- **Unit**: U15.
- **Depends**: A.U4.04, A.U4.05, A.U15.R01, A.U15.12, M.SPEC[M.2-6] (Stage of M.2 in U15).
- **Blast carried by**: `src/asy_scd30_driver.py:162-163` comment → A.U15.04 (SRC_SENS); BACKLOG `:910-913` →
  A.U15.06 (DOCS); `tests_js/live-backend-put-matrix.test.js:185-187` → A.U4.05 (WEB).
- **Kind**: doc

### M.SPEC.012 A.4 SGP40 VOC-index bullet: the blackout code and the participant rung
- **From**: A.U15.19 Blast (`:246-251` gains the blackout sentence), A.U15.R02 Blast ("SPEC A.4 SGP40 bullet", no text
  given — gap filled from its Change).
- **Site**: `SPECIFICATION.md:246-251`.
- **Change**: the bullet keeps its three numbered facts and gains after (1): "— published as 0 during the blackout,
  with `VOCState` 0 (M.3)"; and at its end: "A second consecutive failed cycle sends the device-addressed heater-off
  (SGP40 datasheet Table 14), which reaches only the SGP40 — the participant rung of the recovery ladder (C.7); the
  general-call reset stays at setup (C.8)."
- **Resolved**: A.U15.19 asks this bullet to "co-land with U36's move of that bullet", but no U36 action moves the SGP40
  bullet (A.U36.546 (2) moves only the BMP390 and FRAM facts): the bullet stays in A.4. A.U15.R02's A.4 clause carries
  no text: written from its Change (heater-off to idle, device-addressed).
- **Unit**: U15.
- **Depends**: A.U15.19, A.U15.R02, M.SPEC[M.2-6] (M.3's `VOCState` table, U36 — the pointer resolves at U36; A.U0.08
  checks Part citations, and "M.3" exists from U15 when A.U15.05 creates it).
- **Blast carried by**: —
- **Kind**: doc

### M.SPEC.013 A.4 gains the BMP3XX recovery bullet
- **From**: A.U15.R03 Blast ("SPEC A.4 BMP3XX bullet", no text given — gap filled from its Change).
- **Site**: `SPECIFICATION.md` A.4, new bullet after the SGP40 bullet.
- **Change**: "- **BMP3XX recovery.** A second consecutive failed read soft-resets the chip (0xB6 to CMD) and writes
  the stored oversampling and filter configuration back, since the reset returns every user setting to its default
  (BMP388 DS001 §4.3.22) — the participant rung of the recovery ladder (C.7); a reset the chip rejects (`ERR_REG`
  `cmd_err`) is logged once and writes no configuration."
- **Resolved**: — (no constituent gave the text; this is the action's own behaviour, stated as A.U15.R01/R02 state
  theirs).
- **Unit**: U15.
- **Depends**: A.U15.R03.
- **Blast carried by**: —
- **Kind**: doc

### M.SPEC.014 A.4 NeoPixel and notification bullet: the merged LED and notification behaviour
- **From**: A.U9.02 (`:252-254`), A.U9.05, A.U9.06, A.U22.01 (NeoPixel paragraph), A.U9.09, A.U9.01 (midnight window),
  A.U9.11 (`:264-265`), A.U0.38 V17 (`:265`), A.U1.15 (`:265` path), A.U5.06 Blast (`:259-262` deferred construction
  rewritten), A.U22.03 (WITHDRAWN, OR126.a (4): its "pause task sleeps until a pause is set" sentence is not written),
  A.U10.38 (`NotificationService`), A.S0930.13 Blast (A.4 watchdog paragraph — none here).
- **Site**: `SPECIFICATION.md:252-265`.
- **Change**: the bullet → "Legacy `neopixel_signal.py` (LED hardware plus hardcoded threshold monitoring) was split:
  `asy_neopixel_driver.py`'s `NeopixelDriver` (pure LED hardware; also serves `asy_wifi_service.py`'s `LEDControl`
  Protocol) and `asy_notification_service.py`'s `NotificationService` (generic threshold signalling — owns the
  sleep window, interval, `AutoOn` and the global `FlashBri`/`FlashDur`, one combined `ConfigManager` and logger).
  `led_signal()` (the REST command) is refused at once while a signal is queued or running (owner, 2026-09-29);
  `request_signal()` (internal) waits for a running signal up to a deadline, then queues and returns — never when its
  own ramp ends (agent, 2026-09-29: legacy queued internal requests without a bound). Values are sanitised when the
  request enters: colour bytes clamped to 0-255 (non-finite → 0), the duration floored at 0.1 s and capped at 60 s, a
  non-numeric value refused; a cancelled or failed ramp ends dark with the slot free. The pixel reports no faults
  (`NeoPixel.write()` hands `machine.bitstream()` only arguments the class builds itself, and the driver clamps every
  frame value before storing it), so its recovery is the task's: the supervisor restarts an ended overlay or signal
  task, and each (re)start writes a defined state — the signal task black, then the overlay restored; the overlay task
  the current overlay (agent, 2026-09-30). The notification signals are passed at construction (C.14.3); the active
  window runs from On to Off, and an On time later than Off spans midnight (owner, 2026-09-26); the LED pause counts
  down measured monotonic time (`ticks_ms()`), never wake-ups or the clock. `NotificationSignal.color` is a per-channel
  weight (0/1) scaled by the shared `FlashBri` at trigger time. Config field names carry no "Led" prefix (`WarnCO2`,
  not `LedWarnCO2`); the new API is the only reference and no legacy spelling or
  `legacy/firmware/html_raw/` compatibility is kept (owner, 2026-09-26)."
- **Resolved**: A.U9.11 and A.U0.38 (V17) reword `:264-265` differently; A.U9.11's Blast settles it ("A-C merges onto
  this action's wording, which follows G3/R69's 'accepted debt goes'"); A.U1.15's path joins it. The staged
  `register()`/`finalize()` text goes (A.U5.06: signals at construction; C7). A.U22.03 is withdrawn (OR126.a (4),
  AC_NOTES 37): its sentence is not written; the one-second check stays as HEAD's code has it.
- **Unit**: U22 (A.U22.01 is the latest; U9's and U5's halves describe behaviour that lands by U9/U5 and U22 restates
  the paragraph whole).
- **Depends**: A.U5.06, A.U9.01-A.U9.09, A.U9.11, A.U22.01, M.SPEC[renames].
- **Blast carried by**: DEVICE_REFERENCE "Neopixel LED" bullets → A.U9.01/A.U9.03 (DOCS); `src/asy_notification_
  service.py:68-70` → A.U9.11 (SRC_SENS); `src/asy_webserver_service.py:550, :100` comments → A.U9.09 (SRC_NET).
- **Kind**: doc

### M.SPEC.015 A.4 supervisor bullet names the split supervisor
- **From**: A.U20.06 Blast (A.4 callers `start_and_check_tasks()` → `start_tasks()`/`supervise_tasks()`), A.U8.12 Blast
  ("SPEC A.4 supervisor … cites Part N"), A.U31.07 Blast (escalation text).
- **Site**: `SPECIFICATION.md:266-268`.
- **Change**: → "- The legacy task supervisor is a hand-rolled loop duplicated per device file; every generated
  `sensortask_<device>.py`'s `main()` instead calls `SystemService.start_tasks()`, `start_timers()` and runs
  `supervise_tasks()` as its own task (A.2 for the escalation; its timings are Part N's `system.*` rows)."
- **Resolved**: —
- **Unit**: U20.
- **Depends**: A.U20.06, M.SPEC[N].
- **Blast carried by**: —
- **Kind**: doc

### M.SPEC.016 A.4 owner-confirmed list: the owner's bullets only, each tagged
- **From**: A.U0.25 (A13 restructure, A49, L05, L06, C03), A.U10.24 (FRAM headroom → summed layout), A.U18.29
  (`:271-273`), A.U36.530 (static `AmbPres` item), A.U9.01 (the midnight clause leaves the list), A.U26.07 Change
  (cites the L06 read-back note, read-only).
- **Site**: `SPECIFICATION.md:269-285`.
- **Change**: heading "**Functional behaviours confirmed intentional by the project owner** (owner, 2026-07-13,
  `368fa83`) — don't "fix" these:" over the owner's bullets: air-quality LED sequencing (one colour per condition,
  paused between flashes); `BackupPeriod`/`BackupMaxAge` "0 = disabled" (`DEVICE_REFERENCE.md`); permanent Wi-Fi
  deactivation after a second STA failure streak — `_PHASE_DEACTIVATED` survives task restarts, only a physical power
  cycle clears it (owner, 2026-08-11, `acc4993`); a restart in hotspot mode leaves the hotspot and starts a fresh STA
  failure streak, as legacy's restart did (agent, 2026-09-30); STA never falls back to the hotspot once connected
  successfully in a task's lifetime — only a human resubmitting credentials or a task restart resets this; the web UI
  shows raw numbers, no colour-coding of measured values (the LED is the at-a-glance indicator), the one coloured cue
  being the ISL29125 calibration-light code's tone (owner, 2026-09-28); SCD30 pressure compensation comes from a
  manually set, static `AmbPres` on every device, a device with a barometric sensor included; a device without one has
  no live compensation at all — an accepted limitation (owner, 2026-07-13, `b64857d`: 'intentionally rely on a
  manually-set static `AmbPres` config value instead, and that's fine as-is'); and A.U10.24's FRAM bullet verbatim
  ("every FRAM chunk of a fully built device fits its part: the summed layout … (owner, 2026-09-16: 'we do not even add
  errno/wrnno for the out of FRAM memory … Handle via mpremote.')", its byte sums taken from the per-device test U20
  adds). Then three separate bullets, each with its own tag: A.U0.25's SGP40 compensation text verbatim (owner,
  2026-09-26 quote); "`asy_uart_driver.py` exposes no hardware flow control (owner, 2026-07-23, `c9006dc`)"; "SCD30's
  `get_ambient_pressure()` reuses the set command word — leave as is, no alternate documented read-back exists to switch
  to (owner, 2026-07-22, `75f2e11`)". The midnight-window sentence goes from the list (the window spans midnight since
  U9; A.4's notification bullet states it, M.SPEC.014).
- **Resolved**: A.U0.25 moves the midnight sentence out as an interim "must" text; A.U9.01 (U9) implements it, and its
  Blast routes "U22 rewrites the C03 sentence" to A.U9.01 — merged end state: no midnight sentence in the list.
  A.U10.24 and A.U0.25 both touch the FRAM-headroom item; A.U10.24's Blast says "A-C merges onto this text". The
  "no colour-coding" item is false after A.U23.20's owner-backed CalLight tone (OR76.a, AC_NOTES 26) — narrowed
  (adherence fix, no action names it). A.U18.29's restart sentence is an agent statement inside the owner list: kept
  with its agent tag beside the owner's item it refines.
- **Unit**: U36 (A.U36.530 is the latest; the U0/U9/U10/U18 wording folds in, C8).
- **Depends**: A.U9.01, A.U10.24 (U20's byte sums), A.U18.29, A.U23.20.
- **Blast carried by**: DEVICE_REFERENCE commissioning section → A.U36.531 (DOCS).
- **Kind**: doc

### M.SPEC.017 A.4 gains the Wi-Fi state-machine bullet
- **From**: gap — G6/R25's Home is "SPEC A.4 WiFi, F.2" and A.U18.28 ("A.4 WiFi phase table … gains the row"),
  A.U18.R01 ("SPEC A.4 WiFi bullet: …"), A.U18.30 ("SPEC A.4 WiFi"), A.U8.10 ("SPEC A.4 WiFi section cites Part N") and
  A.U36.531 ("SPECIFICATION.md A.4") all write into an A.4 Wi-Fi text that does not exist at HEAD and no action creates.
- **Site**: `SPECIFICATION.md` A.4, new bullet before the owner-confirmed list.
- **Change**: "- **Wi-Fi state machine** (`asy_wifi_service.py`; owner, 2026-07-13, and as amended below). An empty
  SSID or five failed attempts lead to hotspot mode; a link established once never escalates — a later disconnect
  retries silently every 60 s without counting a failure. The hotspot stays up while a client is associated, otherwise
  STA is retried after its window; a selected AP not reporting `STAT_GOT_IP` is re-activated only if inactive and
  counts as having no client (cyw43 `cyw43_lwip.c:300-323`). A second failed STA streak after a hotspot phase
  deactivates Wi-Fi permanently, a terminal state that task restarts keep and only a power cycle clears (owner,
  2026-08-11, `acc4993`); it shows its own LED pattern, as "Missing WLAN configuration" does (owner, 2026-09-29).
  Power saving is off, a connect attempt polls up to 5 s, a mode switch disconnects, deactivates and waits; repeated
  WLAN hardware errors first re-initialise the radio (power-cycled by the driver) before the task gives up — the
  participant rung (C.7) — and the supervisor takes over after that. A CYW43 `isconnected()` false positive is
  recovered by a power cycle or `hard_reset()` (F.2). Every delay named here is a Part N `wifi.*` row."
- **Resolved**: the bullet is written from G6/R25's Req (the register's statement of the current machine) and the
  constituents' clauses; A.U18.28's "phase table" becomes this bullet's hotspot sentence (no table exists to gain a
  row). Agent decision for the OR2.c review.
- **Unit**: U18 (every constituent's code lands in U18; A.U36.531 cites A.4 in U36).
- **Depends**: A.U18.28, A.U18.30, A.U18.R01, A.U8.10 (Part N rows).
- **Blast carried by**: F.2 `:3635-3636` → M.SPEC[F.2]; DEVICE_REFERENCE LED table → A.U18.30 (DOCS).
- **Kind**: doc

### M.SPEC.018 A.5: Microdot facts at the vendored tag, the pin-move checklist, the connection ladder
- **From**: A.SDEP.06 (`:289-294` tag; the v2.7.0 note restated; `:334`), A.SDEP.18 Blast (A.5 facts re-checked at the
  tag), A.U19.19 (pin-move checklist), A.U19.07 (head bound), A.U19.08 (connection-fault ladder), A.U19.09 (start
  retry rung), A.U19.24 (EAGAIN spin), A.U19.23 (console at `DebugLevel` 0), A.S0930.41 (the stall figure per line),
  A.U36.544 (4) (read-phase sentence), A.U18.01 (`:331`), A.U19.05 (`:326`), A.U1.15 (`:300`, `:332`), A.U5.04 Blast
  (constructor mentions), A.U20.06 (`start_and_check_tasks()` → supervised task list), A.U10.38 (`WifiService`),
  A.U11.26 Blast (A.5 names no code 100 — grep: nothing to change), A.U27.07 Blast (A.5 names no `parse_cmd_request` —
  nothing), A.U31.18 Blast (per-call/outer-cap text unchanged), A.U18.43 Blast (A.5 states the 1,024 B default),
  A.U35.36 (cites the response-writing gap, read-only).
- **Site**: `SPECIFICATION.md:287-335` (A.5).
- **Change**: (1) Opening paragraph: "`ext/microdot.py` is vendored, unmodified upstream Microdot (pinned `<tag>` — no
  edits/cleanup; CLAUDE.md's hard rules are authoritative; MIT text at `ext/LICENSE-microdot`; its type stubs in
  `ext/typings/microdot/`). Facts below are confirmed against that source, not docs or memory." followed by one
  sentence stating what the pinned tag changed for this repo against `v2.6.2` (A.SDEP.06: the v2.7.0 note becomes that
  statement; if the pin stayed at `v2.6.2`, the HEAD note on upstream v2.7.0 stays, re-dated at the refresh), and that
  a move shifts none of H.7's serving walls (re-verified for the actual tag). (2) New paragraph after it: A.U19.19's
  "**When the Microdot pin moves** …" verbatim, each item cited to its `ext/microdot.py` line at the pin. (3) The
  blanket-catch bullet: "Deployed `python/CommonDrivers/microdot.py`" → "The legacy `legacy/firmware/python/
  CommonDrivers/microdot.py`"; the rest unchanged. (4) The response-writing-gap bullet stays (re-verified at the tag,
  A.SDEP.18 W30). (5) After the `print_exception` bullet, new bullet (A.U36.544): "Microdot's request read phase passes
  a muted socket `OSError`, re-raises any other `OSError` and only prints any other exception before dispatching with
  no request (`ext/microdot.py` at the pinned tag), so a read timeout (`asyncio.TimeoutError`, not an `OSError`) is
  observable only in this project's stream proxy." (6) The request-size bullet: "`max_content_length` (16 KB default,
  413 if exceeded) → tightened to 2048 bytes (Part N `web.max_content_length`), with `max_body_length` bound to the
  same value so an oversized body is never buffered (I.6); `max_readline` (2 KB default) — and the request head is
  bounded before Microdot parses it: each line at `max_readline`, at most 32 headers, `Content-Length` digits only and
  once, no `Transfer-Encoding`; a refused head is answered 400 without Microdot's console traceback (errno 32 is in its
  muted list)." (7) The server-task bullet: "The Microdot server task is one of the supervised tasks (`start_tasks()`/
  `supervise_tasks()`) — …" (rest unchanged). (8) New bullet, the connection ladder (A.U19.08 + A.U19.09 + A.U19.24):
  "**Recovery for the webserver's own connection faults**: a client fault — refusal, bad head, reset, per-call or
  outer-cap timeout, stream error — ends that one connection and releases its slot (the smallest rung); it never
  restarts the server task. A send the lwIP stack cannot queue spins cooperatively — full CPU, other tasks still served
  each round — until the connection's per-call timeout ends it (B.14's modlwip `EAGAIN` override while the pin carries
  upstream issue 19704). A failed `start_server()` is retried three times five seconds apart, spanning one full lwIP
  close linger, before the task ends (a `socket()` failure holds nothing; a `bind()`/`listen()` failure holds its pcb
  until a collection, up to two across the retries); the task supervisor, reboot and watchdog stay above it unchanged.
  `_serve()` never raises out of its task." (9) New bullet (A.U19.23 + A.S0930.41): "Client traffic prints nothing at
  the shipped `DebugLevel` 0. At a raised level every console write waits up to 500 ms while a USB host program holds
  the port open without reading (`MICROPY_HW_USB_CDC_TX_TIMEOUT`; never when the host merely enumerated the device or no
  host is attached), so one printed line of several writes can stall the loop about 2 s — an accepted debug-mode
  limitation (owner, 2026-09-30)." (10) Captive-portal bullet: "`_serve_static()`'s `except OSError` branch" →
  "`_StaticRoutes.serve()`'s `except OSError` branch"; "whenever `is_hotspot_active: Callable[[], bool] | None` is
  provided" → "whenever `StaticSite.is_hotspot_active` is provided"; "The generated `sensortask_wozi.py` wires this to
  `AsyConnTime.is_hotspot_active()`" → "Every generated `sensortask_<device>.py` wires it to
  `WifiService.is_hotspot_active()`"; "while `captive_dns.py` answers every domain with the AP's IP" → "while
  `asy_captive_dns.py` answers every A/ANY query with the AP's IP and every other type with an empty NOERROR reply
  (C.7.5)". (11) Last bullet: "Deployed `python/CommonDrivers/microdot.py`" → "The legacy
  `legacy/firmware/python/CommonDrivers/microdot.py`"; "v2.6.2's async-safe `invoke_handler()`" → "the pinned tag's
  async-safe `invoke_handler()`" if that function still exists at the tag, else the sentence states the tag's
  equivalent.
- **Resolved**: A.U19.23 states "500 ms per line", A.S0930.41 "about 2 s per line": both are right at different units
  (500 ms per `mp_hal_stdout_tx_strn()` call; a `print(a, b)` issues one call per argument, separator and line end,
  V.SUPP_owner_0930.B2.02) — the merged sentence states both units (OR126.a (2)). A.U19.08's B.14 pointer is
  conditional on A.SDEP.13 keeping the override (OR114); if the refreshed pin carries upstream's fix, the clause names
  the fix's return behaviour instead (A.SDEP.13). `<tag>` = the tag A.SDEP.06 vendors (C3).
- **Unit**: Stage 1 U0: (1) and (11)'s tag (A.SDEP.06, so A.1/A.5 never name a tag `ext/` no longer holds); Stage 2
  U19: everything else (A.U19.* latest), with (10)'s C.7.5 pointer resolving because C.7.5 lands in U18
  (M.SPEC[C.7.5]).
- **Depends**: A.SDEP.06, A.SDEP.18, A.U19.05/.07/.08/.09/.19/.23/.24, A.U5.04, A.U20.06 (name, U20 — Stage 2 writes
  `start_and_check_tasks()` if U20 has not landed; the U20 rename pass M.SPEC.008-style replaces it, C7), M.SPEC[C.7.5].
- **Blast carried by**: `src/asy_webserver_service.py:237, :725` comments → A.U19.07/A.U19.08 (SRC_NET); CLAUDE.md
  standing-practice pointer to A.5's list → A.U19.19 Blast (DOCS); `tests_hardware/README.md` bench note → A.U19.23
  (HW_BENCH).
- **Kind**: doc, rule

### M.SPEC.019 A.6: where the datasheets live, how a claim cites them, what is not obtainable
- **From**: A.U36.545 (1) (submodule), A.U36.019 (1) (citation and next-best-source rule), A.U15.39 (ISL29125
  paragraph), A.U36.022 (2) (WS2812 → M.5), A.U36.546 (2) (BMP390 paragraph → M.4), A.U0.40 L49 (the BMP390 text's
  datasheet facts), A.U15.25 Blast (A.6's BMP text is A.U0.40's), A.U20.09 Blast (`:347-352` holds), A.U28.35/A.U34.09
  Blasts (location text is U36's).
- **Site**: `SPECIFICATION.md:337-361` (A.6).
- **Change**: (1) First paragraph → A.U36.545 (1)'s sentences (submodule `hundertvolt/datasheets`, the folder list
  unchanged, owner 2026-09-28; access by the owner's grant; nothing in build/lint/test/CI needs a datasheet;
  `git submodule update --init datasheets`), followed by A.U36.019 (1)'s rule sentences verbatim (cite page/section/
  table; datasheet text wins over RIOT, SparkFun, Adafruit, DFRobot; training memory is never a source; a missing
  document is named in this section's list, work continues from the next-best primary source, marked 'open until the
  owner provides <document>', re-checked when it arrives (owner, 2026-09-25)). (2) The Pico W paragraph unchanged
  (A.U20.09: holds). (3) The BMP390 paragraph (`:355-357`) leaves A.6: its text, as A.U0.40 rewrites it (CHIP_ID `0x60`
  BMP390 / `0x50` BMP384/388 with the §4.2 citations, the family fact first confirmed by the owner, 2026-08-11), becomes
  M.4's first paragraph (M.SPEC[M.2-6]). (4) The WS2812 paragraph → "**WS2812**: `datasheets/ws2812/` holds the plain
  WS2812 datasheet; the LED's hardware facts are Part M.5." (5) New last paragraph, the list of documents not
  obtainable here: "**Not obtainable here** (the owner may supply them; each re-checked when it arrives): the Renesas
  application notes the ISL29125 datasheet FN8424 Rev 3.00 refers to (agent, 2026-09-25)." — A.U15.39's ISL29125
  sentence in list form, its folder fact ("`datasheets/isl29125/` holds FN8424 Rev 3.00") kept in the folder list
  sentence.
- **Resolved**: A.U0.40 (U0) rewrites the BMP390 paragraph in A.6; A.U36.546 (U36) moves the paragraph to M.4 —
  merged: A.U0.40's corrected text lands in M.4 (the move carries the correction; no intermediate A.6 edit is needed,
  C8). A.U36.019 and A.U36.545 rewrite the same first paragraph; A.U36.545 says "A.U36.019's rule sentences follow
  unchanged" — one paragraph, both. A.U15.39's separate ISL29125 paragraph and A.U36.019's "list" are one list (A.U36.019:
  "A.U15.39's ISL29125 paragraph … is that list's first entry").
- **Unit**: U36 (after A.U28.35's move and its owner step: the Claude GitHub App's push access to
  `hundertvolt/datasheets` confirmed first, AC_NOTES 37).
- **Depends**: A.U28.35 (and its owner step), M.SPEC[M.2-6] (M.4, M.5 exist in the same unit).
- **Blast carried by**: CLAUDE.md "Datasheets" → A.U36.019 (2)/A.U36.545 (2) (DOCS); README → A.U36.545 (3)/A.U36.547
  (DOCS); A.U0.08's check skipping `datasheets/` while uninitialised → A.U0.08 (TSC).
- **Kind**: doc, rule

### M.SPEC.020 A.7: the generated construction order, boot sequence and FRAM-wiring rule, rewritten whole
- **From**: A.U11.11 (boot order sentence), A.U20.02 (watchdog in the boot entry, `main(watchdog=…)`), A.U20.03
  (`.frozen` first), A.U20.04 (emergency buffer), A.U20.05 (no-autostart variant), A.U25.69 (the four keywords),
  A.U20.06 (setup list, `start_tasks()`/`supervise_tasks()`), A.U11.10 (step 16 → `run_setups()`), A.U11.06 (boot
  phase marker), A.U11.05 (`begin_boot()`), A.U20.07 + A.U25.47 (the proof names both levels), A.S0930.13 Blast and
  A.S0930.30 (supervisor its own task, parks for a shutdown), A.U10.07 (unfed-stretch table), A.U31.03 (setup-unit
  margin clause), A.U8.08 Blast (cite `wdt.timeout_ms`), A.U10.10 (every logger store set up in the batch; `:471` and
  the boot-latency note rewritten), A.U10.12 (collector list, `:374`), A.U10.44 (starter names), A.U10.18
  (`network_available_locked`), A.U20.08 (bus step), A.U5.02 (steps 5-7 tail), A.U5.06 (step 12, step 16), A.U5.07
  (step 13 goes; neopixel before `conn`), A.U5.08 (step 15 goes), A.U5.04 (step 14), A.U5.11 (SGP40 references),
  A.U36.003 (FRAM-wiring rule), A.U36.002/.004 (citers), A.U0.29 E01 + RF049 (`:392-394`, `:485-486`), A.U0.38 V12
  (`:379`), A.U16.01 (`:418-420`, `:485-487`), A.U16.17/A.U16.R03 Blasts (manager's task), A.U11.12 (registry
  paragraph), A.U11.14 (`:563-564`), A.U14.01 Blast (`:532`), A.U36.544 (2)/(4) (WP labels; `:440`, `:458`, `:502`),
  A.U36.512 (2) (`:451`), A.U36.511/G8/R01 (no copied TOML fact), GAP-G7/GAP-10 (no `CFGMGR_SCD30` chunk, AC_NOTES 13),
  A.U15.12 Blast (superseded on the chunk by AC_NOTES 13), A.U24.65 (`:578` wrapper files gone), A.U12.14 Blast (holds),
  A.U3.06 Blast (holds), A.U20.15 (names the generator), A.U10.08 Blast (A.7 names the scan row), A.U31.07 Blast
  (the scan formula).
- **Site**: `SPECIFICATION.md:363-579` (A.7).
- **Change**: A.7 becomes, in order:
  1. Heading `## A.7 The generated construction order, boot sequence and dependency graph`.
  2. Intro: "`buildgen.generate.generate_device()` emits each device's `sensortask_<device>.py` and its boot entry
     from the device's TOML (Part L). This section states the order rules and why they hold; the step list below is
     wozi's generated order as a worked example. Each device's own construction and boot sequence is recorded by
     buildgen beside the generated module (`build/generated_src/sensortask_<device>_expected.json`: `boot_sequence`,
     `fram_wired`, `fram_backed_loggers`) and asserted for every device at L1 (`tests/_sensortask_scenarios.py`) and
     in the twin (L2)."
  3. Boot entry: "The boot entry `sensortask_<device>_main.py` (frozen as `main.py`) arms the watchdog as its first
     statement — `watchdog = WDT(timeout=8000)`, hardcoded, uniform, never per device (owner, 2026-08-11: 'must be
     hardcoded so no error ever can circumvent it'; Part N `wdt.timeout_ms`) — then puts `.frozen` first on
     `sys.path` (F.1), reserves the emergency exception buffer (I.4(e)), imports the device module, sets
     `gc.threshold(32768)` (I.4(f)) and runs `asyncio.run(main(watchdog=watchdog))`. The no-autostart entry
     `sensortask_<device>_main_noautostart.py` arms nothing and prints the manual start line (B.11).
     `main(*, watchdog, cfg_path="", debug=None, web_host="0.0.0.0", web_port=80)`: the four keywords after
     `watchdog` are the documented manual-start options (owner, 2026-09-30: 'they are worth for more than just
     testing') — `cfg_path` the config directory, `debug` every logger's level until the boot batch applies the
     persisted `DebugLevel`, `web_host`/`web_port` the server bind. Importing the device module runs nothing."
  4. Boot order: A.U11.11's paragraph with the merged names — "`main()` runs the boot phases strictly one after
     another: construction (`build_system()`, whose first statement is `reset_reason = begin_boot()`, A.8), the
     one-time setup batch (`SystemService.run_setups()`), task starts (`start_tasks()`), timer starts
     (`start_timers()`), then the first NTP force sync — last, so the webserver already answers during it (owner,
     2026-09-28: 'Boot order is tasks before timers'; legacy started the timers first; NTP last: agent, 2026-09-28) —
     and finally `supervise_tasks()`, which runs the supervisor as its own task; the supervisor parks when a shutdown
     command takes the watchdog over (A.8); one supervisor pass, its escalation included, stays inside Part N's
     `system.scan_budget`. Each transition is recorded in `machine.mem_backup()` region 1 (`boot_phase()`), so a boot
     that dies mid-phase reads back as that phase's boot-failure code (A.8)."
  5. "**Why order matters**: `FRAMManager` is a bump-pointer allocator — construction order is the on-chip layout,
     fixed within one build (A.4)."
  6. "**Construction order** (wozi, generated): `fram` comes before `conn`/`ntp`/`sysfunct`, which — with `conn`'s
     `CaptiveDNS` and the webserver — inherit it whenever `[device.wiring].fram_target` is set, as every device's TOML
     does today (the implicit FRAM-wiring rule below the list); with `[device.wiring].led_target` set the order is
     fram → neopixel → conn → ntp → sysfunct → sensors (the LED is a construction argument of `conn`)." Steps,
     renumbered: (1) `reset_reason = begin_boot()`; (2) every `[bus.*]` in TOML order before any instance —
     `asy_i2c_driver.I2C(...)` per I2C bus, the wrapper clearing a held bus first (F.2), each bus's `timeout` its
     TOML's (wozi's SCD30 bus sets 200 ms against the SCD30's documented 150 ms clock stretching, past rp2's 50 ms
     default; L.6.6 bounds it), then `asy_spi_driver.SPI(...)`; (3) `fram = FRAMManager(spi0, …)` — no chunk of its
     own (owner, 2026-09-16: 'The ONLY module which NEVER has own FRAM logging is the FRAM module itself … Every other
     module shall have FRAM logging optional.'), built first so each mandatory-infra module receives a real chunk
     (`buildgen.graph.build_construction_order()`'s explicit edges); (4) `neopixel = NeopixelDriver(…, log=…)` — chunk;
     (5) `conn = WifiService(WifiConfig(…), ext_led=neopixel, log=…)` — chunk, then its `CFGMGR_WIFI` chunk (the
     implicit FRAM-wiring rule: every `SensorReaderConfig`'s own `cfgmgr` inherits its owner's FRAM, its own
     `CFGMGR_<name>` logger), then its `CaptiveDNS` — chunk, its own `"DNSSRV"` logger; (6) `ntp =
     NTPClient(conn.get_wifi_mode_lock(), conn.network_available_locked, conn.get_dns_server_ip, NtpTiming(…), log=…)`
     — chunk, then `CFGMGR_NTP`; (7) `sysfunct = SystemService(ntp.ntp_issynced, watchdog=watchdog, storage=fram,
     cfg_path=…, log=…, level_setters=_collect_level_setters, config_stores=_collect_config_stores,
     reset_reason=reset_reason)` — chunk, then `CFGMGR_SYSTEM`; (8) `scd30 = SCD30_Reader(…)` — chunk; its
     `ConfigManager` (the three FRC settings) logs RAM-only (owner, 2026-09-30: no extra FRAM chunk); constructed
     before `sgp40`, which holds it as a value reference (ordering hazard #1, C.14) — a name-resolution requirement,
     not a FRAM one; any order is valid for the chunks, since the layout is fixed within one build and need not
     survive a reflash (owner, 2026-09-26); (9) `sgp40 = SGP40_Reader(…, value references to `scd30`'s `Temp`/`Hum`
     (C.14.3), backup=…, log=…)` — chunk, `CFGMGR_SGP40`, then the VOC backup (a timestamped chunk); (10) `bmp3xx =
     BMP3XX_Reader(…)` — chunk, `CFGMGR_BMP3XX` (a device that declares `isl29125` places it here, chunk then
     `CFGMGR_ISL29125`); (11) `notification = NotificationService(neopixel.request_signal, ntp.cettime, signals=(…),
     log=…)` — chunk, `CFGMGR_NOTIFY`; signals passed at construction (C.14.3); (12) on a device with `uart_link`
     instances (`dev` today) the UART buses' wrappers and one `UARTLinkDriver` per instance, each with its own chunk
     when its `[instance.wiring]` sets `fram_target` — never shared, so a fault stays attributable; no `cfgmgr`;
     placed before the webserver, whose error sources include them; `dev` also runs a link exerciser on the initiator
     side (`asy_uart_link_driver.py`), so every claim about the link coexisting with the webserver is about a busy
     link; its counts surface through `/status`; (13) `app = Microdot(); webserver = WebserverService(app,
     routes=RouteSources(…), serving=ServingLimits(…), static=StaticSite("/html", …, conn.is_hotspot_active),
     log=…)` — chunk (implicit FRAM wiring); the static routes register last, so an exact-match API route always wins.
  7. "**The one-time setup batch**: `run_setups(_collect_setups())` awaits, in order, `fram` (first: `sysfunct`'s
     config store logs to it), `sysfunct`, `conn`, `ntp`, every instance with a `setup()` in construction order, and
     the webserver last; every logger store is set up here, first in its module's `setup()`, so no logger is set up
     lazily by a task. `run_setups()` feeds the watchdog after every unit and runs the I.4(f.1) placement collects —
     a one-time, boot-only, non-looping feed site, safe however many modules a device wires; each unit's feed margin
     is Part N's `boot.setup_unit_stretch_ms`."
  8. A.U10.07's table "Unfed stretches at boot" (stretch 1: boot-entry `WDT()` → construction → the first
     `run_setups()` feed; stretch 2: the last setup feed → `start_tasks()` (N starts with `sleep(1/N)` and their
     collects) → `start_timers()` (unstaggered starters, then the trigger plan, last start below 1000 ms) → the force
     sync → the supervisor's first feed), each row naming its bound's source, against Part N's
     `boot.unfed_stretch_1_ms`/`boot.unfed_stretch_2_ms` and `wdt.timeout_ms`; the stretch order follows A.U11.11 (tasks
     before timers), not A.U10.07's HEAD order.
  9. "**Real FRAM chunk order** (wozi): neopixel → `WifiService` → `CFGMGR_WIFI` → `CaptiveDNS` (`DNSSRV`) →
     `NTPClient` → `CFGMGR_NTP` → `SystemService` → `CFGMGR_SYSTEM` → SCD30 → SGP40 → `CFGMGR_SGP40` → SGP40 VOC backup
     (timestamped) → BMP3XX → `CFGMGR_BMP3XX` → `NotificationService` → `CFGMGR_NOTIFY` → `WebserverService`
     (dev adds ISL29125 → `CFGMGR_ISL29125` after BMP3XX and `UART_init` → `UART_resp` before the webserver). This
     order is the on-chip layout of the build that generates it; it is fixed within that build and free to change in
     the next one (owner, 2026-09-26). Which modules may have a chunk is the owner's rule at step 3. A device with no
     `[device.wiring].fram_target` keeps `conn`/`ntp`/`sysfunct`/the webserver RAM-only; a `uart_link` instance with
     no `fram_target` of its own stays RAM-only the same way."
  10. A.U36.003 (3)'s paragraph "**The implicit FRAM-wiring rule.** …" verbatim, with "every `SensorReaderConfig`'s
      own `CFGMGR_<name>` logger with its owner" gaining "— the SCD30's settings store excepted: it logs RAM-only
      (owner, 2026-09-30)".
  11. Boot latency: A.U10.10's rewrite of the note — the lazy webserver setup and the contended-window hypothesis go
      (every logger is set up in the batch, step 7); the measured silicon facts stay as the evidence behind CLAUDE.md's
      "boot latency is not a metric" rule: boot-to-first-`/status` 7.74 s pre-change baseline to ~9.8 s with every
      module FRAM-wired (`dev` bench, 2026-09-16, medians of five timed resets); 23 consecutive reboots across the
      four images with no second, unrequested reset (the executor reads the introducing commit, `git log -S"23
      consecutive reboots"`, for what was checked; a `reset_cause()` reading cannot show it, F.5.4); the setup-order
      A/B of 2026-09-25 (8.94 s against 8.91 s; `sysfunct.setup()` 79 ms against 26 ms); the setup costs on silicon
      (`fram.setup()` 6 ms, every other unit 79-91 ms, the batch 0.93 s, construction ~0.14 s, module import ~1.1 s,
      the 8-timer stagger 0.79 s), gaining A.U31.03's clause "each unit's feed margin is Part N's
      `boot.setup_unit_stretch_ms`". No WP labels; the twin's absolute figures are stated as not a baseline (it
      models no Wi-Fi).
  12. Task/timer starter collection (`:552-553`) → "**Task, trigger and timer starters** (`_collect_task_starters()`,
      `_collect_trigger_starters()`, `_collect_timer_starters()`, `_collect_task_names()`): every module's
      `get_task_starters()`/`get_trigger_starters()`/`get_timer_starters()` is called uniformly; the trigger starters
      are ordered so instances sharing a bus are furthest apart (C.9.1). The FRAM manager always contributes one task:
      it ends at once when the declared chip failed setup and when a chip that was up stops answering, so the
      supervisor escalates (A.4)."
  13. Error-source/debug-level fan-in (`:555-564`): kept, with `conn.dns_server` → `conn`'s `CaptiveDNS`,
      "`SystemService.set_level_setters()`/`_apply_level()`'s registry" → "the `level_setters` provider `SystemService`
      resolves once in `setup()`" (A.U5.08), A.U11.12's "the store's value overrides the constructor `debug=`; an
      unreadable store keeps the constructed level", and A.U11.14's sentence "calling `set_level()` at any time is safe:
      no hard IRQ handler logs, and the soft Timer callbacks that do run between bytecodes on the scheduler, where the
      store of `self.level` — one small `int` — is atomic" (the `_timer_sequencer()` example goes with A.U10.12; the
      arm-failure prints remain the example).
  14. Dependency graph (`:566-576`): kept with the merged shape — `ntp` holds `conn`'s bound methods; `conn` holds
      `neopixel` (constructor argument); `notification` holds its signals' value references and
      `neopixel.request_signal`/`ntp.cettime`; `sgp40` holds `ntp.ntp_issynced` and value references to `scd30`
      (C.14.3) — `asy_sgp40_driver.py` imports nothing from `asy_scd30_driver`; every instance-level dependency is
      constructor-injected, so the object graph is a clean DAG. The "real change from the earlier `comp_source`
      shape" sentence goes (history).
  15. `:578` → "Full coverage: `tests/_sensortask_scenarios.py`, run once per derived device by
      `tests/test_sensortask.py` (one process per device, E.2.1)."
  Removed with this rewrite: "Historically documented against a hand-written `src/sensortask_wozi.py` …" (`:365-370`),
  the `build_system(...)`/`main()` sentence `:372-376` (replaced by 3-4), step 13 `conn.set_ext_led(neopixel)`, step 15
  `set_level_setters`, step 16's batch list (replaced by 7), every WP label, `:418-420`'s "never physically flashed …
  deployed-data-loss risk", `:548-550` ("This order, and `i2c0`'s … are wozi's own", folded into 2/6), `:440`
  "(§Part J)" and `:458` "See Part J for the wrapper module's exact shape" (→ `asy_uart_link_driver.py`), `:502`
  "Part C.9's" → "C.9.1's" where the stagger is meant.
- **Resolved**: (a) AC_NOTES 13 and GAP-G7/GAP-10: A.U15.12's Blast ("SCD30 → its own `CFGMGR_SCD30`, wozi 17
  chunks") is superseded — the SCD30 store logs RAM-only, so the chunk order gains none. (b) A.U5.07 moves neopixel
  ahead of `conn` when `led_target` is set: the chunk order and step list follow (no action rewrote the A.7 list for
  it; its Blast names `:478-485`). (c) A.U10.07's stretch 2 was written in HEAD order (timers before tasks); A.U11.11
  (OR75.a) orders tasks before timers — the table follows the merged order. (d) G8/R01 (OR78): A.7 copies per-device
  TOML facts; the section now states rules and labels the list a worked example whose authority is the generated
  `expected` file (agent decision, OR2.c review). (e) A.U14.01 Blast: `:532` "produced no `WDT_RESET`" → "no second,
  unrequested reset", the executor reading the introducing commit. (f) A.U16.R03 extends A.U16.17: the manager's task
  is permanent whenever a chip is declared (not conditional).
- **Unit**: Stage 1 U20: items 3, 4, 7 (the boot entry, order and batch the U20 code introduces; A.U20.02/.06 Docs and
  A.U11.10/.11 co-land "in one commit" with U20's LEAD/R20 codegen action); Stage 2 U36: the whole section as above
  (A.U36.003/.004 latest; later units' facts — U31's clause, U32's task names — folded in).
- **Depends**: A.U11.05/.06/.10/.11, A.U20.02-.07, A.U5.02-.11, A.U10.07/.10/.12, A.U16.17/.R03, A.U31.03, A.U36.003,
  M.SPEC[N] (the rows cited), M.SPEC.008.
- **Blast carried by**: CLAUDE.md FRAM rule pointer → A.U36.002 (DOCS); code/test comments citing A.7 → A.U36.004
  (SRC/TEST clusters); `buildgen/codegen.py` docstrings naming A.7 → A.U20.15 (GEN); `tests_hardware/README.md:1395`
  → A.U36.004 (8) (HW_BENCH).
- **Kind**: doc

### M.SPEC.021 A.8: the REST reference summary, the `/status` fields and codes, the controlled shutdown
- **From**: A.U19.20 (normative generated reference), A.U10.40 (key scheme), A.U19.01 (unknown key → "Invalid"),
  A.U19.02/A.U9.03 (`LightCmdLED`), A.U4.04 Blast (`:608-609` SCD30), A.U19.12 + A.U36.544 RF063 (`:627-631`), A.U0.29
  E05/E06 (`:632-634`), A.U0.39 L21 (`:619-622`), A.U11.18 (coercion test named), A.U11.29 (exact type), A.U23.49
  Change (float32), A.U11.31 (`ResetErrors`), A.U19.15/A.U27.07 (envelope line), A.U11.01, A.U11.02, A.U11.05 (code
  table), A.U11.06 (10 + p), A.U11.08 (`MemFree`), A.U19.10 (`HTTPDropped`, `WifiTS`), A.U32.06 (`LastTaskEnd`),
  A.U23.22 (`UnixTime`), A.U6.21 (`UTCTime` null), A.U6.20 + A.U15.18 (backup timestamps), A.U18.33 (one networking
  snapshot), A.U30.19 (code 20), A.S0930.09 (exact-word rationale), A.S0930.15 (codes 7-9), A.S0930.30 + A.S0930.41
  (controlled shutdown), A.S0930.31 (behaviour that changes), A.S0930.32/.33/.11/.12/.18 Blasts, A.U6.23/A.U6.27/
  A.U36.537 (code tables' one source: the catalog), A.U20.38 (build refuses a collision), A.U5.04 (constructor),
  A.U18.10/A.U18.38 (`DNSFallback`, `HotspotPW`), A.U0.36 Blast (coercion policy holds), A.U36.544 (2) (`section B`).
- **Site**: `SPECIFICATION.md:580-634` (A.8).
- **Change**: A.8 becomes, in order:
  1. Opening: "The normative REST reference is generated per device: `buildgen/api_reference.py` writes
     `build/generated_src/api/<device>.json` from the one route table (`ROUTES` in `asy_webserver_service.py`), the
     device's generated definitions, the result words and the envelope code catalog; `tests_scripts/test_api_reference.py`
     pins it. This section is its prose summary. `WebserverService` is registration-based: the generated module hands
     it one `RouteSources` object (`sensors`, `settings`, `build_info`, `system_cmd`, `notification_led`,
     `notification_pause`, `status_sources`, `maintenance_sensors`, `error_sources`), a `ServingLimits` and a
     `StaticSite`, and it registers the REST surface from them. Six endpoints: `/measurements`, `/sensors`,
     `/networking`, `/system`, `/status`, `/notification`; `/measurements` and `/status` are the live-data endpoints,
     the rest settings. Keys follow one scheme: value and setting keys PascalCase, acronyms upper-case, no unit suffix;
     envelope, section and container keys lowercase (agent, 2026-09-29; the new API is the only reference, owner,
     2026-09-26). The build refuses a GET key or logger-name collision."
  2. GET shapes: HEAD's bullet with the keys of the scheme (`/networking` → `SSID, PW` (masked), `Country`,
     `Hostname`, `HotspotPW` (masked), `LEDWifiOn`, `NTPHost`, `NTPOffset`, `NTPInterval`, `DNSFallback`; `/system` →
     `DebugLevel`, `GMTOffset`, `DSTOffset` and the nested `build` entry `{FirmwareVersion, WebsiteVersion,
     BuildDate}` (L.7), verbatim from the build info the generator records once per generation; `/notification` →
     `OnH, OnM, OffH, OffM, FlashBri, FlashInterval, FlashDur, AutoOn, WarnCO2, WarnVOC, WarnHum`; `/status` → live
     only, sub-structured `networking`/`system`/`sensors`/`notification`/`errcount`). The "Real production bug, fixed"
     bullet (`:604-606`) goes (history; the `.update()` rule stays as one clause: "results are merged with
     `.update()`: every driver's own return is already `{name: {...}}`").
  3. `/status` fields with meaning beyond their name (each owner/agent tag as its constituent states):
     "`SysUptime`: measured seconds since boot from `ticks_ms()` deltas, never counted wake-ups or the clock (owner,
     2026-09-29). `BootSignature`: resolved once per boot, unchanged by a restart of the uptime task. `ResetReason`:
     the reason for the last reset (codes below). `LastTaskEnd`: the supervised task that ended last and the
     `SysUptime` second it ended, `null` until one does — the legacy `Task_LastErr` successor (owner, 2026-09-30).
     `MemFree`: `gc.mem_free()` when the poll was answered, in bytes (owner, 2026-09-26); no collection runs before it
     (I.4(f.1)). `UTCTime` and `UnixTime`: `null` until the first NTP sync; `UnixTime` is the device's Unix seconds
     every age on the website is computed against. `networking`: one snapshot of the Wi-Fi state, refreshed each second
     — no field reads the radio on a poll; `WifiTS` is that snapshot's time, so a stale value shows the Wi-Fi task
     stalled, judged against `UTCTime` (owner, 2026-09-29); `HTTPDropped` counts the connections dropped before a
     response — a refusal at the ceiling, a refused head or an early peer reset — each also traced once per event (A.5).
     `SGP40_BackupTS`/`SGP40_RestoreTS`: `null` = none since boot, `0` = no timestamp (owner, 2026-09-29). `errcount`:
     one entry per module plus one per `ConfigManager` (`CFGMGR_<name>`)."
  4. Code tables: "Every `/status` code table — `ResetReason` here, `FRCState` (M.2), `VOCState` (M.3), `CalLight`
     (M.1.5) — has one source, the `status` section of `buildgen/error_catalog.json`, from which the website's labels
     are generated; each SPEC table carries a `<!-- catalog: status.<name> -->` marker and
     `tests_scripts/test_error_catalog.py` keeps it equal to the catalog." Then the marked `ResetReason` table:
     0 unknown (the record's magic or check word is wrong) · 1 power-on (also the RUN pin, RP2040 datasheet §4.7.4) ·
     2 watchdog without a record (a starvation, `machine.reset()` from outside the firmware, `mpremote reset`) ·
     3 reboot command · 4 bootloader command · 5 supervisor escalation (task-error budget) · 6 watchdog starve after
     the reset timer could not be armed · 7 reboot after "Reset to defaults" · 8 reboot after "Erase FRAM" · 9 reboot
     after either command whose purpose did not complete · 10 + p boot failure in phase p (11 construction, 12 setup
     batch, 13 task starts, 14 timer starts, 15 first NTP sync) · 20 C stack exhausted (F.1); then "The record lives in
     `machine.mem_backup()` region 0 and the boot phase in region 1 — RAM that survives a reset, never flash or FRAM
     (owner, 2026-09-26); `machine.reset_cause()` alone cannot tell these apart (F.5.4)."
  5. PUT shapes (`:607-615`): "sparse JSON, no `cmd` envelope, on a product route: present fields apply, omitted stay
     untouched, an unknown field (or unknown sensor) answers "Invalid"; the server answers every submitted key."
     `/sensors` → "per-sensor field subsets; SCD30 compares against a fresh chip snapshot and writes only what changed
     (compare-before-write, G.2)". `/networking` → Wi-Fi fields fire `reconnect_wifi()`, NTP fields fire
     `ntp_force_sync()`, `LEDWifiOn` fires nothing — one `SettingsGroup` per subset. `/system` → settings plus
     `"SystemCmd": "reboot"|"bootloader"|"mempause"|"resetconfig"|"erasefram"` — "a command runs only on its exact
     word, matched as a whole string: no alias, prefix or case variant does (owner, 2026-09-30); `mempause`'s fixed
     300 s lives in the command callback". `/status` → "`{"ResetErrors": true}` only: every registered error source
     resets concurrently and `result.ResetErrors` answers "Valid", or "Failed" when a store's write failed; any other
     value answers "Invalid"". `/notification` → settings plus `LightCmdLED` (`R`/`G`/`B`/`T`, validated in the
     webserver through a synthetic schema like every schema-backed field; answered "Failed" while a signal is queued or
     running, owner, 2026-09-29) and `PauseTime` (range-checked 0-3600, refused not clamped, validated the same way).
     Envelope: "`res`/`code`/`descr`/`result` per C.5.3: `res` is `"OK"` when the request was processed; a per-field
     outcome is detail in `result`."
  6. "**The controlled shutdown**" — A.S0930.41's paragraph verbatim (owner, 2026-09-30; the debug-level stall
     sentence with "(agent, 2026-09-30)"; "Reset codes 3, 4, 7, 8, 9."; the escalation sentence "The supervisor's
     task-budget reboot resets directly, without the sequence."), followed by A.S0930.30's two-command purposes
     ("`resetconfig` ("Reset to defaults") deletes every config file — the unit comes back on the schema defaults, as
     the hotspot with its TOML hostname and hotspot password; FRAM logs and the SCD30's NVM are untouched (Wi-Fi and
     identity included, owner, 2026-09-30). `erasefram` ("Erase FRAM") zeroes the whole chip — every FRAM log and the
     SGP40 backup start fresh. No confirmation step (owner, 2026-09-30).") and A.S0930.31's behaviour clauses in
     compact form: a commanded reset whose sequence hangs before its last step reads `ResetReason` 2 at the next boot,
     or 10 + the boot phase when accepted before the boot was marked done; a power cut reads 1; a command that cannot
     start (its task cannot be created) answers "Failed" with nothing changed; the design order's rationale and the
     power-loss table in compact form (A.S0930.30).
  7. "**Numeric coercion policy**" (`:617-624`): kept, with the per-kind validators named (`asy_config_manager.py`'s
     `checked_int()`/`checked_float()`/`checked_numeric()`, M.SRC_CORE.047) in place of `coerce_numeric()`, "an int is
     accepted for a float field; a float for an int field only with no fractional part (`5.0`→`5`, `5.7` refused as
     "Invalid", never truncated); a `bool` never for int/float (exact `type()`); NaN/±inf refused", "int→float has a
     known gap (every int representable only up to the float32 mantissa, F.1) — accepted (owner, 2026-08-24,
     `3986be9`) since no registered float field's bounds go near it; every schema's float bounds are checked against
     2**24 statically (`tests_scripts/test_config_schemas.py`)"; "a float is stored, cached and compared in the
     single-precision form the file reloads as"; "`js/mock-server.js` mirrors the policy; the browser has doubles only
     — the mock's one accepted gap (H.4)".
  8. GET consistency (`:626-631`) → "**GET copy-safety**: `get_dict_data()`/`ConfigManager.get_dict()`/
     `PrintLogHistory.get_log()` build a fresh dict or list per call with no `await` mid-construction; a config GET
     and a PUT on one module are serialised by the module's write lock, and `SCD30_Reader`/`BMP3XX_Reader` read their
     live hardware fields through one locked `get_config_snapshot()` call, so a GET never mixes pre- and post-write
     values (owner, 2026-09-26)."
  9. `:632-634` → A.U0.29's "Connection hardening" paragraph verbatim (owner tags 2026-08-12, `ed48887`, `ee5310c`).
- **Resolved**: (a) A.U19.12 and A.U36.544 RF063 rewrite the same "One open exception" sentence; both mechanisms exist
  in the merged product (M.SRC_CORE.038 lock; `get_config_snapshot()` at HEAD) — one sentence states both. (b)
  A.S0930.41 supersedes A.S0930.30's A.8 paragraph ("becomes"); A.S0930.30's purposes and A.S0930.31's behaviour stay.
  (c) A.U11.05 asks A-C to choose one owner for the code table (A.U11.05, A.U6.23, G5/R03): the catalog's `status`
  section is the source (A.U6.27/A.U36.537), A.8 carries the marked table. (d) A.U19.15 keeps envelope codes 2/3
  while `parse_cmd_request()` exists; A.U27.07 deletes it (M.SRC_CORE.073) — no 2/3. (e) The `UtcTime` spelling of
  A.U6.21 follows A.U10.40 (`UTCTime`). (f) GAP-G13 (M_SRC_CORE): `coerce_numeric()` becomes private and typed callers
  use the per-kind validators; the policy text names them. (g) `/status` code 20 (A.U30.19) joins the table though
  A.U30.19 placed it "(11-15 are A.U11.05's)" — consistent.
- **Unit**: Stage 1 U11: item 4's table with codes 0-6 and 10 + p (A.U11.05 lands the field; A.U14.01's F.5.4
  paragraph cites "A.8"); Stage 2 U36: the whole section as above.
- **Depends**: A.U19.20, A.U10.40, A.U11.01-.08, A.U19.10, A.U32.06, A.U23.22, A.S0930.* , A.U30.19, A.U6.27,
  M.SPEC[C.5.3], M.SPEC[F.5.4].
- **Blast carried by**: `buildgen/error_catalog.json` `status` section → A.U6.27/A.U2.01 (GEN); the marker test →
  A.U36.537 (TSC); `js/render.js:132-135` comment → A.U23.13 (WEB); DEVICE_REFERENCE key names → A.U10.40 (DOCS).
- **Kind**: doc

### M.SPEC.022 A.9: the frozen-website pipeline as it stands
- **From**: A.U36.036 (2) (`:643-646`), A.U36.516 (1) (`:648`), A.U6.04 Blast (`:648`), A.U19.05 (`:642`), A.U19.06
  (no-cache, streams closed), A.U27.06 (`gzip -n`, reproducible), A.U0.39 L51 (`:657-658`), A.U6.03/A.U23.38 (every
  device's site, derived bundle), A.U24.69 (ports held by one runner at a time; `:661-662`), A.U36.548/G9/R11
  (history out), M.SCR.012/.017 (which site each runner builds).
- **Site**: `SPECIFICATION.md:636-662` (A.9).
- **Change**: (1) First paragraph: "`scripts/build_frozen_html.sh` gzips (`gzip -n`, so the output is reproducible) a
  temp copy of the source dirs `HTML_SRC_DIRS` names (required; `scripts/build_website.sh` stages a device's website
  and sets it), then runs `python -m freezefs <tmp> frozen_modules/frozen_html.py --on-import mount --target /html
  --overwrite always` (never `--compress`: this project pre-gzips by hand, served via Microdot's `send_file(…,
  compressed=True)` over a stream `_StaticRoutes.serve()` opens itself, in 256 B reads and with `Content-Length` — I.3,
  "Static files"; every response carries `Cache-Control: no-cache` (agent, 2026-09-30) and every opened file is closed
  when the connection ends). Output goes to `frozen_modules/` (gitignored), not `.frozen/`: `.frozen/` is
  MicroPython's import sentinel (F.1)." The recursive-merge paragraph keeps its facts with the example
  "`<staged>/index.html`, `<staged>/definitions.json`, `<staged>/js/render.js`". (2) Second paragraph → "There is no
  placeholder site (owner, 2026-09-23: '`dev`'s real website is the most biting test' — today every device's real
  site): `scripts/test.sh` builds every device's site and freezes the first derived device's into
  `frozen_modules/frozen_html.py`; `npm test`'s `pretest` hook builds the generated definitions; each twin runner serves
  its booted device's own site (`build/generated_html/<device>`). The binary `application/octet-stream` fallback, which
  no real site has a file for, is pinned on a synthetic fixture in `tests/test_asy_webserver_service.py` beside the
  generic route wiring; `tests/test_website_build_integration.py` is the real-pipeline proof. Product-fixed ports are
  held by one runner at a time (E.1, 'Fixed ports')." The "removed 2026-09-24" history and "not for this file any
  more" go.
- **Resolved**: A.U0.39's L51 tag survives inside the reworded sentence (C8). "wozi's for the unit and web tiers"
  is false after A.U6.03/A.U23.38/M.SCR (every device's site; first derived device frozen) — rewritten (adherence).
  The "two suites must not run concurrently" clause becomes the port-lock pointer (A.U24.69, M.SCR.012).
- **Unit**: U36.
- **Depends**: A.U19.05, A.U19.06, A.U27.06, A.U6.03, A.U23.38, A.U24.69, M.SPEC[E.1].
- **Blast carried by**: `.gitignore:33-41` → A.U28.33/A.U36.036 (4) (TOOL/LEAD); `scripts/build_frozen_html.sh` →
  A.U27.06 (SCR).
- **Kind**: doc

### M.SPEC.023 A.10: the twin's rule, its suite and where its quirks live
- **From**: A.U37.06 (4) (generated-module rule), A.U0.38 V28 (`:672` tag), A.U36.511 (3) (`:679`), A.U36.544 (1)
  (`:691`), A.U25.43 Blast (A.10 → F), A.U25.01 Blast (A.10 points to the fidelity table), A.U10.38 (`WifiService`
  is not named; nothing), A.U36.016/M.TWIN (the suite's runs as the twin README states them).
- **Site**: `SPECIFICATION.md:664-693` (A.10).
- **Change**: (1) First paragraph: "`digital_twin/` fakes `machine`/`network`/`neopixel` at the same raw
  bus-transaction boundary `tests/machine.py` uses, with real-time-firing `Timer`s and plausible sensor values, so a
  generated device module runs under the Unix-port interpreter and behaves like real hardware. Every generated device
  module has this Unix-port equivalent, mocked only at the raw bus-transaction boundary (owner, 2026-08-08,
  paraphrase). Independent of `tests/`; the swap is `MICROPYPATH` ordering. How faithful each fake is, and where it is
  not: `digital_twin/README.md`'s fidelity table." (2) "**Chain-completeness requirement** (owner, 2026-08-20,
  `00eb44d`): any new module joins the digital twin provided it can form a complete chain …" — "A new sensor driver
  needs the C.11 point 9 checklist" → "A new driver needs Part K's twin step (K.5)". (3) The CI-suite paragraph:
  "a `strategy.matrix` over every device of `devices/*.toml`"; the run list stays a pointer to `digital_twin/README.md`
  (which has the runs and the per-device subprocess counts) with the two GC stages in order (I.4(e)); the last sentence
  → "The Unix-port `socket` quirks the twin works around from twin-side code are Part F's Unix-port facts (F.7)".
- **Resolved**: A.U36.544 (1) offers "`digital_twin/README.md` … or F.7 where A.U14.28 moved it"; A.U25.43 makes
  Part F's Unix-port facts the one home ("U36 moves it, G7/R12 doc") — F.7 it is. A.U37.06 (4) adds its rule sentence
  "after '…and behaves like real hardware.'" — placed there.
- **Unit**: U37 (A.U37.06 is the latest; its sentence lands when BACKLOG's bullet is deleted); the U0/U36 edits fold
  in (C8).
- **Depends**: M.SPEC[F.7], M.SPEC[K], A.U25.01 (the fidelity table exists).
- **Blast carried by**: BACKLOG `:848-859` deletion → A.U37.06 (DOCS).
- **Kind**: doc

### M.SPEC.024 New A.11: threat model for a trusted home LAN
- **From**: A.U29.01 (the section), A.U29.03 (every place of the hotspot default; A.11 as the decision's home),
  A.U29.04 (row 15's history-scan sentence), A.U29.02 (the L0 check reads A.11), A.S0930.09/.30/.41 (command words and
  the controlled shutdown, row 2), A.U10.40 (key names), A.U18.37 (`_cfg_overlay()`, C7), A.U10.37 (`asy_captive_dns.py`).
- **Site**: new `## A.11 Threat model: trusted home LAN` after A.10 (`:664-694`), before the `---` at `:695`.
- **Change**: A.U29.01's text as planned (opening paragraph; the 16-row "Exposures" table; closing paragraph), with:
  row 3's source → "A.8; `src/asy_wifi_service.py` `_cfg_overlay()`"; row 6's source → "`src/asy_captive_dns.py`
  (`run()`'s subnet filter, `DNSQuery`)"; row 2's keys in the scheme (`ResetVOC`, `Calibrate`, `LightCmdLED`,
  `PauseTime`) and its shutdown sentence pointing at A.8's "controlled shutdown" paragraph; row 8 listing every place of
  the default as A.U29.03 (a) enumerates them (`src/asy_wifi_service.py`'s `HotspotPW` default, each
  `devices/*.toml` `hotspot_password`, L.3's example TOML, the legacy tree, the tests pinned to that default), "accepted
  permanently as a known limitation (owner, 2026-09-26; first accepted 'for now', owner, 2026-07-13, `b64857d`)"; row 15
  completed by A.U29.04's sentence written to the scan's actual result (or ending after "row 8's default" if the scan
  has not run); every upstream citation re-checked against the refreshed pin (C3). The closing paragraph names the
  check `tests_scripts/test_threat_model_statement.py`.
- **Resolved**: A.U29.01's row 3 names `_mask_pw()`; A.U18.37 (U18, earlier) renames it `_cfg_overlay()` and A.U29.01's
  Depends asks for the landed name (C7). A.U29.03 (2) moves the pointer of A.U0.33's L.2/L.3 replacements from
  "CLAUDE.md" to "A.11" — carried in M.SPEC[L.2]/M.SPEC[L.3].
- **Unit**: U29.
- **Depends**: A.S0930.09, A.U11.05, A.U18.10, A.U18.19, A.U18.37, A.U18.38, A.U10.40, M.SPEC[A.8] (Stage 1 table).
- **Blast carried by**: README intro sentence → A.U29.01 Blast (DOCS); CLAUDE.md credentials bullet → A.U29.03 (1)
  (DOCS); `pyproject.toml` S104/S105 comments → A.U28.27/A.U28.29/A.U29.03 (TOOL); the L0 check → A.U29.02 (TSC).
- **Kind**: doc
