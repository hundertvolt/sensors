# A-C merge SPEC (HEAD 546cdd8)

One file: `SPECIFICATION.md` (6,805 lines at HEAD; unchanged since the audit's starting merge `1dea035`, so every
action's line cite resolves against HEAD). Inputs: the 221 index pairs, 41 further actions whose Site names SPEC, every
Change/Blast clause of any action that writes SPEC text (grep of `audit/actions/*.md`), AC_NOTES 1-43, the finished
merges' gaps (GEN, SRC_SENS, SRC_CORE, SRC_NET, TEST_HELP, WEB, TWIN, HW_BENCH, HW_DEV, TEST_UNIT, SCR, TOOL, PROC, DOCS
gap 1 (a)-(i); TSC names no SPEC gap); every Part A-N is merged (none NOT-DONE). Owner answers written firm: OR131 (Microdot stubs, `ext/typings/microdot/`), OR132 (light-theme AA
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
- **Unit**: Stage 1 U8 (TOC "Part N" line, with M.SPEC.155); Stage 2 U36 (everything else).
- **Depends**: M.SPEC.002 (Part 0 exists), M.SPEC.155 (Part N).
- **Blast carried by**: README "Further reading" (Part 0, Part N named) → A.U36.547/A.U36.541 (5) (DOCS); CLAUDE.md
  `:6-7`-equivalent wording → A.U36.524 (2)-(4) (DOCS); the "variant" renames in the body → M.SPEC.004.
- **Kind**: doc

## SPECIFICATION.md — Part 0 (new, between the front matter and Part A)

### M.SPEC.002 Create Part 0, Design principles, sections 0.1-0.5
- **From**: A.U36.541 (1) (Part 0 text), A.U36.542 (1) (0.4 body), A.U36.031 (the P4 workaround principle), A.U10.47
  Blast (the catalog names the conventions check); OR141.a (3) (the `voc_algorithm.py` exception's owner tag) (A-C review
  fold).
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
  A.U27.02/A.U27.03 move the repair account; F.5.5 keeps only the 1.29 delta fact, M.SPEC.104). (b) 0.4's body is
  A.U36.542 (1)'s text, with: the `voc_algorithm.py` tag written "(agent, 2026-08-11; owner, 2026-10-05: the one
  exception to the naming and member-ordering rules)" (A.U0.40's L01 label, `f27b33b`; OR141.a (3), A-C review fold); the "Comment tags" row → "| Comment tags (`@web`, `@web-group`, `@wiring`, `@value-wiring`, `@limits`,
  `@requires`, `@tunable`) | L.6.4 | `src/` (`@tunable`: every scope `tests_scripts/test_tunables_register.py` scans,
  N.2) | `tests_scripts/test_buildgen_*` grammar tests; `test_tunables_register.py` |"; the "Error and logging contract"
  row's enforcement also names `tests_scripts/test_error_catalog.py`; the "Config schema" row → "Config schema and each
  value's scope rule | C.5 | `src/`, generated | unit tests; `tests_scripts/test_config_schemas.py`"; the naming rows (`asy_` marker, `_NAME`, starter names, `errno=`/`wrnno=`) and the D.15
  member-order row name `tests_scripts/test_code_conventions.py` in "Enforced by"; and A.U36.542's
  landing check (each row's "Written in"/"Enforced by" read against the landed sections and checks; a check that did
  not land reads "review"). (c) 0.2's P12 row cites "H.6.1 (the website's wire contract)" — created by M.SPEC.120
  (A.U36.044) in the same unit. (d) 0.5 as written ("walks Part K's ordered checklist … CLAUDE.md's bird's-eye scan
  checks new code against this Part").
- **Resolved**: A.U36.541 leaves A.U36.031's placement to A-C ("under P4 in 0.3's style, or a list after the table"):
  placed as one "Under P4:" paragraph in 0.2, since 0.3 holds only the owner's patterns and an unnumbered `###` would
  break A.U36.532's structure rule — agent decision, OR2.c review. A.U36.031 cites F.5.5 for the repair pattern;
  A.U27.03/A.U36.546 move that account to B.15, so the pointer names B.15. A.U36.542's catalog omitted the `@tunable`
  family A.U8.03 adds to L.6.4 (U8, earlier) and the scope rule A.U36.538 adds to C.5 (same unit): both rows follow.
- **Unit**: U36.
- **Depends**: M.SPEC.003 (structure rule), M.SPEC.046-.072 (Part C sections the catalog cites), M.SPEC.075 (D.11,
  D.15), M.SPEC.149 (L.6.4 rows), A.U10.47/A.U36.038/A.U5.17 (the checks named, other clusters).
- **Blast carried by**: CLAUDE.md "Architecture reference" pointer, `:214` "indefinitely", `:68-91` (the `src/` and
  scan bullets) → A.U36.541 (3)-(4), A.U36.542 (2)-(3) (DOCS); README map → A.U36.541 (5)/A.U36.547 (DOCS); SPEC D.3
  `:2631` → M.SPEC.074; Part K's opening points to 0.5 → M.SPEC.140; A.U0.08/A.U0.09 checks resolve "Part 0"/"0.x"
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
  M.SPEC.132 leaves its text) to the end of Part I after I.5; H.7's subsections become `### H.7.1 The connection ceiling
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
  item: placed as F.9 — see M.SPEC.109.
- **Unit**: U36 (the move of F.5.7-F.5.9 and every Sections line); the heading-level fixes land with it.
- **Depends**: every section-creating change below (M.SPEC.024 A.11, M.SPEC.044/.045 B.16/B.17, M.SPEC.086 E.10,
  M.SPEC.077 E.2.2, M.SPEC.107 F.7, M.SPEC.109 F.9, M.SPEC.120 H.6.1, M.SPEC.142 K.5.1, M.SPEC.151/.152 M.2-M.6,
  M.SPEC.155 N).
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
  the section text that another merged change rewrites where one does: `:2898` with M.SPEC.077 (E.2.1, A.U36.016),
  `:3059`/`:3066` with M.SPEC.081 (E.5.2, three flavours after A.U21.12/A.U27.12), `:451` with M.SPEC.020 (A.7),
  `:3213`/`:3253` with M.SPEC.083 (E.6.6), `:6008`/`:6012` with M.SPEC.144 (L.1); a sentence another change deletes
  needs no rename.
- **Resolved**: — (pure word replacement; where a rewrite removes the sentence, the rename is void).
- **Unit**: U36.
- **Depends**: M.SPEC.020, M.SPEC.077, M.SPEC.081, M.SPEC.083, M.SPEC.144.
- **Blast carried by**: CLAUDE.md/README/code/test renames → A.U36.512 (4)-(6) (DOCS, TOOL M.TOOL.056, SCR, TSC).
- **Kind**: doc

- **C8 U0's tag and decision wording folds into the section's merged text.** A.U0.12/.16/.17/.19/.21/.25/.29/.30/.33/
  .37-.44/.56/.60 write actor tags and answered decisions across SPEC in U0. Where a later action rewrites the same
  sentence, the U0 wording is carried inside that section's merged change (its tag survives in the end-state text) and
  lands with it; where no later action touches the sentence, the U0 edit is its own merged change landing in U0. The
  decision-vocabulary allow-list (M.TSC.010) is generated at U0's landing and shrinks when each tag lands, so the
  deferral needs no extra work.
- **C9 Review-answer tags (A-C review fold, 2026-10-05).** Where a change below writes the permanent tag of one of the
  68 decisions the owner answered on 2026-10-02 (`audit/actions/FOLD_ANSWERS.md`), a decision answered "fine" reads
  "(agent, <its date>; owner-reviewed, 2026-10-02)" (an existing owner tag stays as it is); one answered with a change
  or a question carries the owner's ruling in place of the proposed text, tagged "(owner, 2026-10-02)"; the rulings of
  2026-10-05 (OR141-OR143) are "(owner, 2026-10-05)". This holds also where the tag sits inside an action's text quoted
  "verbatim". Which change carries which decision's tag: the F21 table in "A-C review fold (2026-10-05)" at the end.

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
- **Depends**: A.U1.01-A.U1.04 (the move), A.SDEP.06/.07, A.U28.35 (datasheets move; owner step first, AC_NOTES 37 —
  satisfied: standing push permission, owner, 2026-10-05, OR144.a; A-C review fold).
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
  A-C2 step order: A.U10.09's part lands in U11, not U10 (it needs A.U11.03, which lands in U11).
- **Depends**: A.U11.03, A.U20.06, A.U31.07, A.U10.44 (names), M.SPEC.008.
- **Blast carried by**: `tests_hardware/README.md:1280-1286` and `BACKLOG.md:89-90` → A.U10.09 (HW_BENCH/DOCS);
  `src/asy_system_service.py:1` header → A.U36.535 (5) (SRC_CORE carries the file).
- **Kind**: doc

### M.SPEC.007 A.3: refactor status as today's fact
- **From**: A.U28.12, A.U1.15 (`:131-134` legacy clause), A.U36.543 (8) (`:135`), A.U36.511 (1) (`:137-146`, with
  A.U0.25's A06 tag), A.U36.548 (G9/R11: "not yet `arzi`/`neu`" dropped), A.U0.23 Blast (A06 at `:143-145`); OR140.a (18)
  (no device but `dev` is special) (A-C review fold).
- **Site**: `SPECIFICATION.md:129-146` (A.3).
- **Change**: first paragraph → "Targets the latest stable MicroPython/pico-sdk/picotool/Microdot at the pin the
  owner moves (F.1), expands error handling and fault recovery, and adds unit tests, mypy, ruff and CI (every tool its
  own CI job; the job list and why each is shaped as it is: B.10). Code lands in `src/` by Part K's checklist." Second
  paragraph → A.U36.511 (1)'s text, with the generated files named `sensortask_<device>.py` and boot entry
  `sensortask_<device>_main.py` (C7), and its UART sentence without the WoZi clause (A-C review fold): "`dev`
  additionally carries the UART message protocol (Part J) as two instances across its permanent crossover jumper (owner,
  2026-09-11) — the bench rig's, so the one device-specific role here is `dev`'s; every other device is built and tested
  alike (owner, 2026-10-02)." ("`wozi` does not (… wozi's none, for want of a flashable board: agent, 2026-09-11)"
  goes.)
- **Resolved**: A.U28.12 and A.U1.15 edit the same sentence (job list vs legacy clause): one sentence carries both
  (A.U28.12's Depends names A.U1.15). "latest *stable*" vs the owner's pin rule (A.U0.33 C05 at F.1 `:3441-3442`, owner,
  2026-09-26): A.3 states the pin rule by pointer, so the two Parts agree.
- **Unit**: U36.
  A-C2: stage U28 — A.U28.12's A.3 pointer to B.10's job list lands with that list (M.SPEC.033, U28).
- **Depends**: M.SPEC.088 (the pin sentence it points to), M.SPEC.008.
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
  failing setup), A.U16.R02 (three identification attempts), A.U16.R03 (chip lost mid-operation), A.U2.09,
  A.U2.23 (codes), A.U3.04 dropped (OR140.a (7)), A.U20.02/A.U24.54 (the `WDT()`-site half), A.U10.38 (class names);
  OR140.a (7) (every layer keeps its own persisted entry) (A-C review fold).
- **Site**: `SPECIFICATION.md:168-236` (the `asy_fram_driver.py`/`asy_fram_manager.py` bullet).
- **Change**: the bullet, in this order (each paragraph's facts as the constituent states them; C7 names):
  1. Head: "`asy_fram_driver.py`/`asy_fram_manager.py` — raw SPI FRAM driver and chunk allocator with dual-copy
     redundancy (every device whose TOML declares a `fram` instance)." The 2026-09-18 restructure sentence keeps its
     facts (synchronous byte-level path under a caller-held lock, `session_begin()`/`session_end()`, the 2 µs CS settle,
     `get_values_sync()`/`set_values_sync()` plus `report_get_values()`/`report_set_values()`, the async forms kept for
     other bus users) and loses "Every `errno`/`wrnno` keeps its number and meaning; only the logging site moved up"
     (false after U2's renumbering): "its codes are the error catalog's, and every layer that meets a chunk failure —
     the driver's guard, the chunk's status or payload check, the block write or read — persists its own entry, so the
     history shows how far the fault reached (C.7; owner, 2026-10-02)".
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
     to M.6 (M.SPEC.152).
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
  rule; one sentence (owner quote from V12). `:175-176`'s "keeps its number" is false after A.U2.09 (no action
  names it — adherence fix). A.U3.04's one-entry flow is dropped by the owner (OR140.a (7)): the clause states the
  per-layer rule instead (A-C review fold). The 8 KB chip size (`:228`) is a TOML fact (G8/R01, OR78): replaced by the measured
  per-write time. The `WDT()`-site sentence follows A.U20.02 (WDT in the boot entry) and A.U24.54 (the invariant test
  globs boot entries) — "permanently vacuous" goes.
- **Unit**: U36 (latest constituents A.U36.546 and the U36 doc pass; every earlier unit's behaviour is described as its
  end state). No earlier unit cites a new A.4 sentence by section text.
  A-C2 step order: A.S0930.14's part lands in U20, not U16 (it follows A.S0930.14's own change, which lands in U20).
- **Depends**: M.SPEC.152 (M.6 exists in the same unit), A.U16.*, A.S0930.17, A.U11.03, A.U20.02, A.U24.54.
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
- **Depends**: A.U4.04, A.U4.05, A.U15.R01, A.U15.12, M.SPEC.151 (Stage of M.2 in U15).
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
- **Depends**: A.U15.19, A.U15.R02, M.SPEC.151 (M.3's `VOCState` table, U36 — the pointer resolves at U36; A.U0.08
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
  A.U10.38 (`NotificationService`), A.S0930.13 Blast (A.4 watchdog paragraph — none here); OR140.a (5) (internal requests
  queue because they are bounded; an external refusal tells the caller to retry) (A-C review fold).
- **Site**: `SPECIFICATION.md:252-265`.
- **Change**: the bullet → "Legacy `neopixel_signal.py` (LED hardware plus hardcoded threshold monitoring) was split:
  `asy_neopixel_driver.py`'s `NeopixelDriver` (pure LED hardware; also serves `asy_wifi_service.py`'s `LEDControl`
  Protocol) and `asy_notification_service.py`'s `NotificationService` (generic threshold signalling — owns the
  sleep window, interval, `AutoOn` and the global `FlashBri`/`FlashDur`, one combined `ConfigManager` and logger).
  `led_signal()` (the REST command) is refused at once while a signal is queued or running (owner, 2026-09-29), and
  the refusal tells the caller to try again later: an external caller could flood the device into exhaustion (owner,
  2026-10-02); `request_signal()` (internal) waits for a running signal up to a deadline, then queues and returns —
  never when its own ramp ends — because internal requests are bounded in number and rate (owner, 2026-10-02: 'internal
  LED commands are guaranteed to be bounded by number and frequency, they won't flood the device'; legacy queued them
  without a bound). Values are sanitised when the
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
  A-C2 step order: A.U9.09's part lands in U10, not U9 (it follows A.U9.09's own change, which lands in U10).
- **Depends**: A.U5.06, A.U9.01-A.U9.09, A.U9.11, A.U22.01, M.SPEC.008; the refusal's retry wording as the LED
  command handler lands it M.SRC_NET.122 [follows].
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
- **Depends**: A.U20.06, M.SPEC.156.
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
  A.U36.531 ("SPECIFICATION.md A.4") all write into an A.4 Wi-Fi text that does not exist at HEAD and no action creates;
  OR140.a (17) (the Wi-Fi-off pattern respects the Wi-Fi LED setting) (A-C review fold).
- **Site**: `SPECIFICATION.md` A.4, new bullet before the owner-confirmed list.
- **Change**: "- **Wi-Fi state machine** (`asy_wifi_service.py`; owner, 2026-07-13, and as amended below). An empty
  SSID or five failed attempts lead to hotspot mode; a link established once never escalates — a later disconnect
  retries silently every 60 s without counting a failure. The hotspot stays up while a client is associated, otherwise
  STA is retried after its window; a selected AP not reporting `STAT_GOT_IP` is re-activated only if inactive and
  counts as having no client (cyw43 `cyw43_lwip.c:300-323`). A second failed STA streak after a hotspot phase
  deactivates Wi-Fi permanently, a terminal state that task restarts keep and only a power cycle clears (owner,
  2026-08-11, `acc4993`); it shows its own LED pattern, as "Missing WLAN configuration" does (owner, 2026-09-29) —
  0.1 s on, 2.9 s off — and like every Wi-Fi pattern it follows the Wi-Fi LED setting: dark while `LEDWifiOn` is off,
  shown as soon as it is switched on (owner, 2026-10-02).
  Power saving is off, a connect attempt polls up to 5 s, a mode switch disconnects, deactivates and waits; repeated
  WLAN hardware errors first re-initialise the radio (power-cycled by the driver) before the task gives up — the
  participant rung (C.7) — and the supervisor takes over after that. A CYW43 `isconnected()` false positive is
  recovered by a power cycle or `hard_reset()` (F.2). Every delay named here is a Part N `wifi.*` row."
- **Resolved**: the bullet is written from G6/R25's Req (the register's statement of the current machine) and the
  constituents' clauses; A.U18.28's "phase table" becomes this bullet's hotspot sentence (no table exists to gain a
  row). Agent decision for the OR2.c review.
- **Unit**: U18 (every constituent's code lands in U18; A.U36.531 cites A.4 in U36).
- **Depends**: A.U18.28, A.U18.30, A.U18.R01, A.U8.10 (Part N rows); M.SRC_NET.077/.100 (the deactivated pattern gated
  by `LEDWifiOn`, as the fold amends them).
- **Blast carried by**: F.2 `:3635-3636` → M.SPEC.096; DEVICE_REFERENCE LED table → A.U18.30 (DOCS, M.DOCS.027).
- **Kind**: doc

### M.SPEC.018 A.5: Microdot facts at the vendored tag, the pin-move checklist, the connection ladder
- **From**: A.SDEP.06 (`:289-294` tag; the v2.7.0 note restated; `:334`), A.SDEP.18 Blast (A.5 facts re-checked at the
  tag), A.U19.19 (pin-move checklist), A.U19.07 (head bound), A.U19.08 (connection-fault ladder), A.U19.09 (start
  retry rung), A.U19.24 (EAGAIN spin), A.U19.23 (console at `DebugLevel` 0), A.S0930.41 (the stall figure per line),
  A.U36.544 (4) (read-phase sentence), A.U18.01 (`:331`), A.U19.05 (`:326`), A.U1.15 (`:300`, `:332`), A.U5.04 Blast
  (constructor mentions), A.U20.06 (`start_and_check_tasks()` → supervised task list), A.U10.38 (`WifiService`),
  A.U11.26 Blast (A.5 names no code 100 — grep: nothing to change), A.U27.07 Blast (A.5 names no `parse_cmd_request` —
  nothing), A.U31.18 Blast (per-call/outer-cap text unchanged), A.U18.43 Blast (A.5 states the 1,024 B default),
  A.U35.36 (cites the response-writing gap, read-only); OR140.a (2) (the console-starvation bench test is
  gated by the persistence-write flag), F21 tag form (http-head-limits) (A-C review fold).
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
  limitation (owner, 2026-09-30). The bench test that holds the port open runs only behind the persistence-write flag,
  since it spends two flash writes, the debug level set to 0 and back (owner, 2026-10-02)." (A-C review fold, OR140.a
  (2); lands with the bullet, after U26's gate on the test) (10) Captive-portal bullet: "`_serve_static()`'s `except OSError` branch" →
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
  (M.SPEC.063).
- **Depends**: A.SDEP.06, A.SDEP.18, A.U19.05/.07/.08/.09/.19/.23/.24, A.U5.04, A.U20.06 (name, U20 — Stage 2 writes
  `start_and_check_tasks()` if U20 has not landed; the U20 rename pass M.SPEC.008-style replaces it, C7), M.SPEC.063.
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
  M.4's first paragraph (M.SPEC.151). (4) The WS2812 paragraph → "**WS2812**: `datasheets/ws2812/` holds the plain
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
  `hundertvolt/datasheets` confirmed first, AC_NOTES 37 — satisfied: the owner gave standing push permission, owner,
  2026-10-05, OR144.a; A-C review fold).
- **Depends**: A.U28.35 (and its owner step), M.SPEC.151/.152 (M.4, M.5 exist in the same unit).
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
  (the scan formula); OR136.a (1) (an absent config file written once at boot), OR138.a (1) (`ConfigFaults` fixed at the
  end of the batch), OR141.a (4) (d) + OR143.a (5) (the UART receive ring allocated in the link's `setup()`) (A-C review
  fold).
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
     2026-09-28: 'Boot order is tasks before timers'; legacy started the timers first; NTP last: agent, 2026-09-28;
     owner-reviewed, 2026-10-02) —
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
     is Part N's `boot.setup_unit_stretch_ms`." Then (A-C review fold): "A config store whose file is absent writes it
     here, once, with its schema defaults (C.7.3; owner, 2026-10-01); the set of modules whose file existed but was
     unreadable or damaged is fixed when the batch ends and published as `/status` `ConfigFaults` (A.8; owner,
     2026-10-01). A `uart_link` instance's `setup()` allocates its receive DMA ring, held for the program's life, so the
     placement collects put it with the long-lived survivors (I.4(f.1); owner, 2026-10-05)."
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
  A.U11.10/.11 co-land "in one commit" with U20's LEAD/R20 codegen action; item 7's fold sentence with them — the
  absent-file write lands in U11, the receive ring in U13 and `ConfigFaults` in U20, all before this stage); Stage 2
  U36: the whole section as above (A.U36.003/.004 latest; later units' facts — U31's clause, U32's task names — folded
  in).
- **Depends**: A.U11.05/.06/.10/.11, A.U20.02-.07, A.U5.02-.11, A.U10.07/.10/.12, A.U16.17/.R03, A.U31.03, A.U36.003,
  M.SPEC.156 (the rows cited), M.SPEC.008; M.SRC_CORE.043 (absent-file write, as the fold amends it);
  M.GEN.008, M.GEN.014 (`ConfigFaults` in the generated `/status` block); M.SRC_NET.222 (the ring in the link's `setup()`).
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
  A.U18.10/A.U18.38 (`DNSFallback`, `HotspotPW`), A.U0.36 Blast (coercion policy holds), A.U36.544 (2) (`section B`),
  G3/R31 (merged into G6/R51: the GET's chip I/O, item 8; AC3_R R-09); OR136.a (1)-(2) (absent file written once with
  defaults), OR137.a (1)-(5) (`HTTPDropped` as a 24-hour window), OR138.a (1)-(2) (`ConfigFaults`; the reset deletes
  every file unread), OR140.a (3) (website confirmation, API one command per request), OR140.a (5) (the LED refusal
  tells the caller to retry), OR140.a (12) (no SCD30 write during a sequence), F21 tag form (A-C review fold).
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
     envelope, section and container keys lowercase (agent, 2026-09-29; owner-reviewed, 2026-10-02; the new API is the
     only reference, owner, 2026-09-26). The build refuses a GET key or logger-name collision."
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
     stalled, judged against `UTCTime` (owner, 2026-09-29); `HTTPDropped` counts the web connections dropped before a
     response in the last 24 hours, at hourly resolution — a refusal at the ceiling, a refused head or an early peer
     reset — held in 24 hourly bins allocated once and advanced from the uptime seconds (the hourly window counter,
     G.2), each bin and the sum capped at `COUNTER_CAP`, so a drop leaves the count 23-24 hours after it happened; no
     drop, read or hour change allocates; `ResetErrors` clears it; each drop is also traced once (A.5; owner,
     2026-10-01). `ConfigFaults`: the names of the modules whose config file existed at this boot but could not be read
     or was damaged (unparseable or invalid), an empty list when there are none — fixed when the boot setup batch ends
     (A.7), bounded by the build's config stores, and a module stays listed for the rest of the boot even when the boot
     repair rewrote its file; the module's persisted warning stays, once per boot (owner, 2026-10-01).
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
     resets concurrently, `HTTPDropped`'s window included, and `result.ResetErrors` answers "Valid", or "Failed" when a
     store's write failed; any other value answers "Invalid"". `/notification` → settings plus `LightCmdLED`
     (`R`/`G`/`B`/`T`, validated in the webserver through a synthetic schema like every schema-backed field; answered
     "Failed" while a signal is queued or running, owner, 2026-09-29, and the refusal tells the caller to try again
     later, owner, 2026-10-02) and `PauseTime` (range-checked 0-3600, refused not clamped, validated the same way).
     Envelope: "`res`/`code`/`descr`/`result` per C.5.3: `res` is `"OK"` when the request was processed; a per-field
     outcome is detail in `result`."
  6. "**The controlled shutdown**" — A.S0930.41's paragraph verbatim (owner, 2026-09-30; the debug-level stall
     sentence with "(agent, 2026-09-30)"; "Reset codes 3, 4, 7, 8, 9."; the escalation sentence "The supervisor's
     task-budget reboot resets directly, without the sequence."), followed by A.S0930.30's two-command purposes
     ("`resetconfig` ("Reset to defaults") deletes every schema-backed config file without reading it, readable or
     not (owner, 2026-10-01): the command is answered when it is accepted, the deletes run in the shutdown sequence,
     and a delete that fails is logged and shows as reset reason 9 (a command whose purpose did not complete) at the
     next boot — never as an HTTP "Failed" (agent, 2026-10-05). After the reboot each file
     is written once with its defaults (C.7.3), so the unit comes back on the schema defaults, as the hotspot with its
     TOML hostname and hotspot password; FRAM logs and the SCD30's NVM are untouched (Wi-Fi and identity included,
     owner, 2026-09-30). `erasefram` ("Erase FRAM") zeroes the whole chip — every FRAM log and the SGP40 backup start
     fresh. The API takes one command per request and asks no confirmation (owner, 2026-09-30); the website asks the
     browser's confirmation before it sends any system command (H.4; owner, 2026-10-02).") then (OR140.a (12)): "No
     SCD30 write can happen while a sequence runs: the SCD30 is written only by an API command, and every API command,
     the SCD30 setters included, is refused from the moment a sequence is accepted (owner, 2026-10-02); unit and twin
     tests prove it." and A.S0930.31's behaviour clauses in
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
     values (owner, 2026-09-26). A config GET on a chip-backed module costs one chip snapshot per request (SCD30: the
     six-register read; BMP3XX: the configuration bit fields; ISL29125: the register snapshot, plus one re-apply write
     and wrnno 11 when the chip diverged from its shadow), taken under the device session like any read." The executor
     checks each figure against the landed drivers.
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
  paragraph cites "A.8"); Stage 2 U36: the whole section as above. Fold stages, each with the code it states: U19
  (item 3's `HTTPDropped` window and item 5's "`HTTPDropped`'s window included", with the window counter and its
  webserver use); U20 (item 3's `ConfigFaults`; item 6's delete-unread, failed-delete and SCD30 sentences, with the
  `/status` generated block, the delete path and the system-command tests); U23 (item 6's website-confirmation clause,
  with the website's confirm dialogs); item 6's "written once with its defaults" with the U20 stage (the absent-file
  write lands in U11, earlier).
  A-C2 step order: A.S0930.12's part lands in U20, not U11 (it follows A.S0930.12's own change, which lands in U20); A.S0930.31's part lands in U20, not U11 (it follows A.S0930.31's own change, which lands in U20); A.S0930.32's part lands in U20, not U11 (it needs A.S0930.13, which lands in U20); A.S0930.33's part lands in U20, not U11 (it follows A.S0930.33's own change, which lands in U20).
- **Depends**: A.U19.20, A.U10.40, A.U11.01-.08, A.U19.10, A.U32.06, A.U23.22, A.S0930.* , A.U30.19, A.U6.27,
  M.SPEC.056, M.SPEC.103; M.SPEC.111 (the window counter's G.2 entry); M.SRC_CORE.043/.047 (absent-file write, fault
  state, as the fold amends them); M.SRC_CORE.133 (the window counter), M.SRC_NET.127, M.SRC_NET.129 (the webserver's
  drop path and `get_dropped_count()`), M.GEN.008, M.GEN.014 (`ConfigFaults` in the generated `/status` block and its
  catalog description), M.SRC_CORE.042 (the delete that never reads), M.WEB.021 (the confirm dialogs),
  M.TEST_UNIT.306 and M.TWIN.104 (the watertight proof).
- **Blast carried by**: `buildgen/error_catalog.json` `status` section → A.U6.27/A.U2.01 (GEN); the marker test →
  A.U36.537 (TSC); `js/render.js:132-135` comment → A.U23.13 (WEB); DEVICE_REFERENCE key names → A.U10.40 (DOCS).
- **Kind**: doc

### M.SPEC.022 A.9: the frozen-website pipeline as it stands
- **From**: A.U36.036 (2) (`:643-646`), A.U36.516 (1) (`:648`), A.U6.04 Blast (`:648`), A.U19.05 (`:642`), A.U19.06
  (no-cache, streams closed), A.U27.06 (`gzip -n`, reproducible), A.U0.39 L51 (`:657-658`), A.U6.03/A.U23.38 (every
  device's site, derived bundle), A.U24.69 (ports held by one runner at a time; `:661-662`), A.U36.548/G9/R11
  (history out), M.SCR.012/.017 (which site each runner builds); F21 tag form (A-C review fold).
- **Site**: `SPECIFICATION.md:636-662` (A.9).
- **Change**: (1) First paragraph: "`scripts/build_frozen_html.sh` gzips (`gzip -n`, so the output is reproducible) a
  temp copy of the source dirs `HTML_SRC_DIRS` names (required; `scripts/build_website.sh` stages a device's website
  and sets it), then runs `python -m freezefs <tmp> frozen_modules/frozen_html.py --on-import mount --target /html
  --overwrite always` (never `--compress`: this project pre-gzips by hand, served via Microdot's `send_file(…,
  compressed=True)` over a stream `_StaticRoutes.serve()` opens itself, in 256 B reads and with `Content-Length` — I.3,
  "Static files"; every response carries `Cache-Control: no-cache` (agent, 2026-09-30; owner-reviewed, 2026-10-02) and every opened file is closed
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
- **Depends**: A.U19.05, A.U19.06, A.U27.06, A.U6.03, A.U23.38, A.U24.69, M.SPEC.076.
- **Blast carried by**: `.gitignore:33-41` → A.U28.33/A.U36.036 (4) (TOOL/LEAD); `scripts/build_frozen_html.sh` →
  A.U27.06 (SCR).
- **Kind**: doc

### M.SPEC.023 A.10: the twin's rule, its suite and where its quirks live
- **From**: A.U37.06 (4) (generated-module rule), A.U0.38 V28 (`:672` tag), A.U36.511 (3) (`:679`), A.U36.544 (1)
  (`:691`), A.U25.43 Blast (A.10 → F), A.U25.01 Blast (A.10 points to the fidelity table), A.U10.38 (`WifiService`
  is not named; nothing), A.U36.016/M.TWIN (the suite's runs as the twin README states them); OR140.a (13) (the twin's
  local NTP responder replaces the planned log tolerance, A.U35.38/.39 dropped), routine settlement twin-choice-17 (the
  sync-dependent clock-jump cases also run in the twin) (A-C review fold).
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
  → "The Unix-port `socket` quirks the twin works around from twin-side code are Part F's Unix-port facts (F.7)". (4)
  New sentence after (1) (A-C review fold): "The twin answers NTP from a local responder, so a twin boot syncs its
  clock like a unit on its network: the normal-boot log check expects NTP synced and tolerates no NTP code, the NTP
  client's tests (function, error handling, the cases that must bite, regressions) run against the same responder, and
  the clock-jump cases that need a sync run in the twin as well as under the driven clock (owner, 2026-10-02; the
  clock-jump file, agent, 2026-10-05)."
- **Resolved**: A.U36.544 (1) offers "`digital_twin/README.md` … or F.7 where A.U14.28 moved it"; A.U25.43 makes
  Part F's Unix-port facts the one home ("U36 moves it, G7/R12 doc") — F.7 it is. A.U37.06 (4) adds its rule sentence
  "after '…and behaves like real hardware.'" — placed there.
- **Unit**: U37 (A.U37.06 is the latest; its sentence lands when BACKLOG's bullet is deleted); the U0/U36 edits fold
  in (C8). Fold stage U25: (4), after the responder, the client tests on it and the clock-jump twin file land (all U25).
- **Depends**: M.SPEC.107, M.SPEC.142, A.U25.01 (the fidelity table exists); M.TWIN.167 (the responder and the
  log check's NTP-synced expectation), M.TEST_UNIT.342 (the NTP-client tests on it), M.TWIN.146 (the
  clock-jump twin file).
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
  "CLAUDE.md" to "A.11" — carried in M.SPEC.145/M.SPEC.146.
- **Unit**: U29.
- **Depends**: A.S0930.09, A.U11.05, A.U18.10, A.U18.19, A.U18.37, A.U18.38, A.U10.40, M.SPEC.021 (Stage 1 table).
- **Blast carried by**: README intro sentence → A.U29.01 Blast (DOCS); CLAUDE.md credentials bullet → A.U29.03 (1)
  (DOCS); `pyproject.toml` S104/S105 comments → A.U28.27/A.U28.29/A.U29.03 (TOOL); the L0 check → A.U29.02 (TSC).
- **Kind**: doc

## SPECIFICATION.md — Part B (`:697-1483`)

### M.SPEC.025 B.1 and B.3 step 3: picotool's real compatibility rule
- **From**: A.U21.05 (B.1 item 1, B.3 step 3); A.U14.24 (the F.1 sentence it co-lands with, carried in M.SPEC.088).
- **Site**: `SPECIFICATION.md:705-707` (B.1 item 1), `:751-752` (B.3 step 3).
- **Change**: B.1 item 1 → "**The four pieces must agree, or the build breaks** — `picotool` must be of `pico-sdk`'s
  major version and at least the version `pico-sdk` requires, or the build fails ("Incompatible picotool installation
  found"), and `pico-sdk` must match whatever MicroPython's build compiles against (B.3 derives this instead of
  hand-tracking it)." B.3 step 3 appends "(narrower than pico-sdk's own rule, B.1)". The pico-sdk/picotool file:line
  cites live in F.1 only; they are re-read in the refreshed pin's clones (C3).
- **Resolved**: A.U14.24's "must match that major.minor or the build fails" is replaced by A.U21.05's clause (A.U21.05
  Depends) — one rule in B.1 and F.1.
- **Unit**: U21.
- **Depends**: A.SDEP.08 (pin, C3); M.SPEC.088.
- **Blast carried by**: `derive_picotool_ref()` docstring and `versions.toml:3-5` comment → A.U21.05 (TOOL).
- **Kind**: doc

### M.SPEC.026 B.2: quick start names three build flavours and the shared probe
- **From**: A.U21.02 Blast (quick-start comments take the help-text wording), A.U21.08 Blast (`--toolchain-dir` row notes
  the character limit), A.U21.12 Blast (three binaries), A.U27.12 Blast (one probe, flavours named), A.U36.512 (2)-(3)
  (`:740` "which variant is in it"), A.U36.546 (CLAUDE.md's coverage bullet drops the 24.6 s → 9.3 s figure because
  `:739` keeps it).
- **Site**: `SPECIFICATION.md:712-743` (B.2 code block and the paragraph after it).
- **Change**: (1) Code-block comments: `--latest` → "# pin versions.toml to the newest stable tag (a pin move: the
  owner's call; the platform re-check follows)"; `--micropython-ref v1.26.1` → "# build this ref without changing
  versions.toml (off-pin: re-check before trusting it)"; `--toolchain-dir /path` → "# default ~/pico-toolchain; the
  path may not hold whitespace, quotes, \ $ # ; :". (2) "Both subcommands also build/verify **two** Unix-port
  interpreters (owner decision, 2026-09-21): …" → "Both subcommands also build/verify **three** Unix-port interpreters,
  one per build flavour: `build-standard` **without** `MICROPY_PY_SYS_SETTRACE` — the test rig, what plain
  `scripts/test.sh` runs — and `build-settrace` with it, which only `scripts/test.sh --coverage` uses (E.5) (owner,
  2026-09-21); and `build-lwip`, the real patched `extmod/modlwip.c` over loopback lwIP, which only the lwIP host files
  run (E.1, E.3; owner, 2026-09-30)." The flag paragraph ("**The flag is not inert when unused** (measured 2026-09-18)
  … 24.6s → 9.3s)") keeps its facts with "Since the split, the plain suite's figures" → "The plain suite's figures are
  therefore", and its timing names the file as it was when measured: "(measured at the split of the two builds: `test_sensortask_wozi.py`,
  today `tests/test_sensortask.py` run for `wozi`, 24.6 s → 9.3 s)" — A.U24.65 deletes the per-device wrappers (GAPS_G3
  hand-off 5; gap pass G1). (3) "Because a build directory's name no longer tells you which variant is in it, `scripts/test.sh`
  verifies the binary rather than the path (E.5.2's first consequence)." → "A build directory's name does not tell you
  which build flavour it holds, so every runner asks the binary through `scripts/_unix_port.sh` (E.5.2)."
- **Resolved**: A.U36.512's U36 word change (`:740`) is overtaken by A.U27.12's U27 sentence (same clause, flavour
  word already in it) — one text. A.U21.02 asks for "the help-text wording"; the comments carry it shortened to a
  comment column (agent decision, listed below).
- **Unit**: Stage 1 U21 ((1), (2)); Stage 2 U27 ((3)).
- **Depends**: A.U21.02, A.U21.08, A.U21.12, A.U27.12; M.SPEC.081; M.TEST_UNIT.337 (A.U24.65's per-device file).
- **Blast carried by**: README flag table → A.U21.02 (DOCS); CLAUDE.md "Two Unix-port binaries" → A.U21.12/A.U36.546
  (DOCS).
- **Kind**: doc

### M.SPEC.027 B.3: the pin line, the typed table, the build record
- **From**: A.U21.01 (refusals cite B.3), A.U21.29 (typed table; errors cite B.3), A.U21.03 Blast (step 8 "record what
  was built"), A.U27.02 (the `[stubs]` table the typed check also reads), A.U21.02 (pin moves on the owner's call).
- **Site**: `SPECIFICATION.md:745-761` (B.3).
- **Change**: (1) Step 1 → "Check out MicroPython at the pinned ref — `versions.toml`'s `[micropython] ref`, exactly
  one `ref = "…"` line in that table (`--latest` rewrites that one line and re-reads the file; a missing or duplicate
  line is refused). The pin moves only on the owner's call (owner, 2026-09-26)." (2) New sentence after the list:
  "`versions.toml` is read as a typed table — `[micropython] ref` (a non-empty string), `[toolchain] board` (a string)
  and `apt_packages` (a list of strings), `[lwip]` (B.14.2's options), `[stubs] board`/`stdlib` (B.15) — and a missing or
  mistyped key fails naming its table and key, before anything is built." (3) New step 7: "Record what was built:
  `toolchain-record.json` in the toolchain directory names every ref and commit, the picotool and compiler versions and
  the hashes of the inputs (B.5)." (4) The closing paragraph's "`test` is `setup` with steps 1-4 skipped" holds.
- **Resolved**: A.U21.03 calls it "step 8"; B.3 has six steps at HEAD — it becomes step 7 (agent decision).
- **Unit**: U21 ((1)-(3)); the `[stubs]` key lands with A.U27.02 (U27) — Stage 2 U27 adds it to (2).
- **Depends**: A.U21.01, A.U21.03, A.U21.29, A.U27.02.
- **Blast carried by**: the `SetupError` texts → A.U21.01/A.U21.29 (TOOL).
- **Kind**: doc

### M.SPEC.028 B.4: bounded, streamed, retried, redacted subprocesses
- **From**: A.U21.17 Blast, A.U21.18 Blast, M_TOOL gap 8 (D2: one retry pair for every retried network step).
- **Site**: `SPECIFICATION.md:763-775` (B.4).
- **Change**: (1) After the two env bullets, a new paragraph: "Every subprocess is bounded by one of three budgets —
  `tool.remote_query_timeout_s`, `tool.network_step_timeout_s`, `tool.build_step_timeout_s` (Part N) — and streams its
  output as it runs; a timeout kills the process group and names the limit. Network steps (clones, fetches,
  `ls-remote`, submodule updates, the Node downloads, `uv sync`) are retried three times with growing pauses
  (`tool.uv_sync_attempts`, `tool.uv_sync_backoff_step_s`). A secret passed to a step never appears in the echoed
  command or its output." (2) The `network_env()` bullet gains "privileged apt calls keep them through `sudo
  --preserve-env=<names>` (sudo's `env_reset` would drop them)."
- **Resolved**: — (no conflict among the constituents)
- **Unit**: U21.
- **Depends**: A.U21.17, A.U21.18; M.SPEC.156 rows (A.U21.17, M_TOOL gap 8).
- **Blast carried by**: `setup_toolchain.py` `run()` → A.U21.17 (TOOL).
- **Kind**: doc

### M.SPEC.029 B.5: directory layout
- **From**: A.U21.03 Blast (record file), A.U21.22 Blast (lock), A.U21.27 Blast (picotool installed only when its tag
  changed), A.U21.30 Blast (outdated leftovers removed), A.U21.12 Blast (`build-lwip`).
- **Site**: `SPECIFICATION.md:777-792` (B.5).
- **Change**: the tree gains `    ports/unix/build-lwip/      the same interpreter with the patched modlwip over
  loopback lwIP - the lwIP host files only` after `build-settrace/`; `  toolchain-record.json  what was built from what
  (refs, commits, picotool, compilers, input hashes)` and `  .toolchain.lock          held by the one setup run allowed
  per directory` at the top level; the `picotool/` line → "full clone at the derived matching tag; built and
  `sudo make install`ed only when its tag changed". After the tree: "Setup removes directories its own earlier versions
  left (old Unix build names, retired overrides, superseded Node trees). One run at a time per toolchain directory: a
  second run fails at once naming the first, and an interrupted one is detected at the next start."
- **Resolved**: — (no conflict among the constituents)
- **Unit**: U21.
- **Depends**: A.U21.03, A.U21.12, A.U21.22, A.U21.27, A.U21.30.
- **Blast carried by**: README toolchain section → A.U21.27 (DOCS).
- **Kind**: doc

### M.SPEC.030 B.6: verification steps
- **From**: A.U21.15 Blast (step 2 zero errors and warnings), A.U21.12 Blast (step 8c), A.U21.06 (every Unix binary
  re-proves the SIGINT override), A.U21.09 (the firmware build's post-build proof).
- **Site**: `SPECIFICATION.md:794-805` (B.6).
- **Change**: step 2 → "Build `mpy-cross`, zero errors and warnings."; step 8 → "8. Rebuild the vanilla Unix ports —
  (a) `build-standard`, the standing test rig, (b) `build-settrace`, (c) `build-lwip`, the lwIP host build (B.14.3) —
  each followed by its override readbacks (B.14)." The closing line → "A completed run leaves no vanilla RP2
  `firmware.uf2`; step 8's three Unix ports are the kept artefacts."
- **Resolved**: A.U21.12 names "step 8c"; B.6 at HEAD has one step 8 — it becomes (a)-(c). The cross-reference "B.14.3"
  is the end-state number of the `modlwip_eagain` subsection (M.SPEC.042); in U21 it reads "B.14.4" (C6).
- **Unit**: U21.
- **Depends**: A.U21.06, A.U21.12, A.U21.15, M.SPEC.042.
- **Blast carried by**: —
- **Kind**: doc

### M.SPEC.031 B.7 and B.7.1: evidence, warning-free builds, the mbedtls flag
- **From**: A.U1.17 (`:808` "deployed" goes), A.U36.524 (6) (`:812` pointer), A.U21.15 (its error text cites "B.7"
  for "every build is warning-free"), A.U21.16 (B.7.1 rewritten per branch), A.SDEP.12 (the mbedtls version at the
  refreshed pin), A.U14.23 (BACKLOG's text cites B.7.1; no SPEC edit).
- **Site**: `SPECIFICATION.md:807-822` (B.7, B.7.1).
- **Change**: (1) `:808` "for both the deployed `v1.26.1` and latest stable" → "for both `v1.26.1` and latest stable".
  (2) Gap fill: after B.7's first sentence, "Every build is warning-free: a `warning:` or `error:` in any build's output
  fails the run (one helper checks every build; B.7.1 names the one suppression, if any)." — A.U21.15's message points
  here and B.7 had no such sentence. (3) `:812` "See CLAUDE.md's "Build-environment verification" for the re-check
  recipe." → "B.17 is the re-check recipe." (4) B.7.1 per A.U21.16's branch: 2a (clean on both targets) → "GCC ≥ 14
  flagged `mbedtls_xor()` in `ctr_drbg.c` as `-Warray-bounds` with mbedtls 3.6.2; mbedtls 3.6.6 (vendored since the
  v1.29.0 pin, `lib/mbedtls` `0bebf8b`) carries the fix (mbedtls `292b96c0a`), and a GCC <version> build of both targets
  is clean without a suppression (agent, <date>)" with the heading → "### B.7.1 GCC ≥ 14 hosts: the mbedtls array-bounds
  check"; 2b (a warning remains, or the GCC ≥ 14 build cannot run before B5) → "persists on GCC <version> despite mbedtls
  3.6.6; scoped to `ctr_drbg.c` (the generated variant makefiles and board cmake, B.14); goes when a GCC ≥ 14 build is
  clean without it, checked at every ref move (agent, <date>)". Both: "this project's pinned MicroPython vendors an
  mbedtls commit predating that fix" goes; "Not yet fixed upstream (GCC bug #121044 still UNCONFIRMED)" goes (2a) or
  becomes "GCC bug #121044's status is unread here (gcc.gnu.org unreachable)" (2b). Where A.SDEP.08 moved the pin, the
  vendored mbedtls version and commit are A.SDEP.12's record, not "`0bebf8b` / v3.6.6" (C3).
- **Resolved**: A.U1.17 lands in U1 on HEAD text; A.U36.524 (6) in U36; A.U21.16 in U21 or phase C (its step 1 needs a
  GCC ≥ 14 build). Independent sentences.
- **Unit**: Stage 1 U1 ((1)); Stage 2 U21 ((2), and (4) when step 1 ran in U21 — else (4) lands in phase C's delta,
  A.C.10); Stage 3 U36 ((3), after M.SPEC.045 creates B.17).
- **Depends**: A.U1.17, A.U21.15, A.U21.16, A.SDEP.12, M.SPEC.045.
- **Blast carried by**: CLAUDE.md `:979-983` → A.U21.16 (DOCS); `setup_toolchain.py` constant → A.U21.16 (TOOL).
- **Kind**: doc

### M.SPEC.032 B.9 Coverage
- **From**: A.U1.16 (B.9).
- **Site**: `SPECIFICATION.md:830-835`.
- **Change**: A.U1.16's text verbatim: title "## B.9 Coverage"; body "The RP2040 firmware build is covered for every
  device (B.11, CI `firmware-build-verify`) and the Unix port by the test suite (E.3). The legacy build
  (`legacy/firmware/build-*.sh`) is reference-only and never wired (CLAUDE.md)."
- **Resolved**: — (no conflict among the constituents)
- **Unit**: U1.
- **Depends**: A.U1.03 (the `legacy/` layout).
- **Blast carried by**: —
- **Kind**: doc

### M.SPEC.033 B.10: the CI job set, the cache key, the retried sync
- **From**: A.U28.37 (B.10 text), A.U21.07 (cache key gains `micropython_overrides.py`), A.U28.04 (runner, GCC, glibc
  in the key), A.U28.01 (one retried `uv sync --locked`), A.U28.06 (every device), A.U28.10 (outage dates stay as
  facts), A.U28.42 (the composite actions' headers point to B.10), A.U7.03 Blast (`:867` "ALL PASSED" quote), A.SDEP.19
  (the `actionlint-py` reason re-checked), A.SDEP.05 (no action version named; nothing to edit), A.U28.15 (Codecov
  goes), M_TOOL gap 8 (D1: the two composite actions, the `devices` job, `env` for matrix values; `ci.devices_timeout_min`).
- **Site**: `SPECIFICATION.md:837-870` (B.10).
- **Change**: (1) `:839-848` A.U28.37's text: "**sixteen jobs** (fourteen of real work plus two that derive inputs:
  `web-changes`, the path filter the web jobs gate on, and `devices`, the device list both per-device matrices read)";
  "for each of the six devices" → "for every device". (2) Gap fill (M_TOOL gap 8 D1), new paragraph after the job list:
  "Two composite actions carry the shared steps: `.github/actions/uv-sync` (the retried sync, the lint jobs) and
  `.github/actions/setup-micropython-toolchain` (sync, then the cached Unix-port toolchain, built on a miss when a job
  asks for it). A matrix value reaches a script through `env`, never through the script text." (3) `:850-853` → A.U28.37's
  cache-key sentence (A.U21.07's third file and A.U28.04's runner identity in one): "The cache key hashes every input
  compiled into the cached binaries — `versions.toml`, `setup_toolchain.py`, `micropython_overrides.py` — and the
  runner image, host GCC and glibc: keying on `versions.toml` alone once let a stale binary survive (`--coverage`
  failed in CI while passing locally). Every caller of the composite action shares that one key, so the first job in a
  run builds and the rest hit." (4) `:855-862` → A.U28.37's sync paragraph verbatim ("Every job that syncs runs
  `scripts/uv_sync_retried.sh` (`uv sync --locked`, three attempts, 10 s and 20 s pauses) … `pyproject.toml`'s
  `required-version` pins uv itself."), with the named example (`actionlint-py` fetching its binary in its build
  backend) kept only if A.SDEP.19 found it still true at the refreshed lock, else replaced by "a dependency's build-time
  download". (5) `:864-870` (coverage rerun paragraph): "the plain suite reported `60/60 files passed / ALL PASSED`" →
  "the plain suite had passed" (the quoted summary text no longer exists after A.U7.03's summary block); the run ID,
  date and 13m24s stay as the evidence behind the rule (G9/R11).
- **Resolved**: A.U21.07 (U21) and A.U28.04 (U28) edit the same sentence (A.U28.04: "one edit") — Stage 1 U21 writes
  the three-file form, Stage 2 U28 adds the runner identity. A.U7.03 asks to "reword to the new text"; the quote goes
  rather than quoting the new block (a quoted summary drifts, OR43.a).
- **Unit**: Stage 1 U21 ((3) files part); Stage 2 U28 (rest).
- **Depends**: A.U28.01-A.U28.36 (A.U28.37's Depends), A.U21.07, A.U7.03, A.SDEP.19.
- **Blast carried by**: CLAUDE.md retry bullet → A.U28.10 (DOCS); `action.yml` comments → A.U28.04/A.U28.42 (TOOL).
- **Kind**: doc

### M.SPEC.034 B.10.1: why each job is shaped as it is
- **From**: A.U28.37 (B.10.1 bullets), A.U1.16 (`:911-912` legacy clause), A.U27.14 (`unit-tests` retry budget),
  A.U8.15 Blast (budgets cite Part N), A.U27.25 (`lint-and-typecheck` mypy paths), A.U28.05 (picotool from the cached
  build; the `Findpicotool.cmake` record; `:933-934` cache-miss sentence), A.U28.07, A.U28.08, A.U28.09, A.U28.11,
  A.U28.13, A.U28.15, A.U28.16, A.U28.17, A.U28.19, A.U28.43 (each "docs SPEC B.10.1 (A.U28.37)"), A.U28.42 (ci.yml
  header points here), A.U21.18 (callers only), A.SDEP.19 Blast, M_TOOL gap 8.
- **Site**: `SPECIFICATION.md:872-935` (B.10.1).
- **Change**: every bullet as A.U28.37 states it, with these merged sentences: (a) permissions: "…nothing pushes,
  comments or calls the API; `web-changes` alone adds `actions: read` to find its filter base. zizmor enforces it."
  (b) `web-changes`: A.U28.07's rule — "a push compares against the last commit CI passed on that branch, a
  `pull_request` against its base" — and the full input list (the paths of H.8). (c) `lint-and-typecheck`: "names every
  ruff scope explicitly, `build/generated_src` included after a generation step, and lints the generated modules with
  `src/`'s rules; for mypy it names exactly the main pass's `files`, checked by a test (B.15)"; the shellcheck sentence →
  "shellcheck covers `scripts/` only: the legacy `legacy/firmware/build-*.sh` are never in scope (CLAUDE.md)" — no count.
  (d) `unit-tests`: "…`timeout-minutes` is for many files hanging at once: a warm run plus one file's full 12-minute
  retry budget (240 s x 3, `PER_FILE_TIMEOUT_S`), after a tighter cap cancelled a healthy run (`34755468619`). The
  minutes are `ci.unit_tests_timeout_min` (Part N). The retried sync is the toolchain action's first step, ahead of
  `scripts/test.sh`." — "~17-minute" and the cold-cache 16m58s/16m42s figures move to the Part N row's Basis (A.U8.15).
  (e) `unit-tests-coverage`: the Codecov clause goes; "four summaries and four HTML artifacts"; its minutes → Part N.
  (f) `digital-twin-e2e`: "One job per device from `devices`". (g) `firmware-build-verify`: "installs the cached
  picotool build before building (picotool lives in `/usr/local`, outside the cache)"; the executor's one-line record of
  what pico-sdk's `Findpicotool.cmake` does without an installed picotool (A.U28.05); `:933-934` "A cache miss fails on
  `build_firmware.py`'s own "no toolchain found" rather than skipping the build." → "A cache miss fails the picotool step
  by name (no cached build tree), never skipping the build." (h) web bullets: `web-unit-tests` "`needs:
  web-lint-and-typecheck` for order only, `!cancelled()`"; `web-coverage` "its test step gates, its report steps
  (`always()`) do not; success-gated on `web-unit-tests`"; smoke "`--require-all-engines`: a missing engine fails in CI;
  Firefox's cache key rolls monthly and with the installer; each Xvfb reports its own display"; `web-lint-and-typecheck`
  "syncs the Python environment and validates every device's built page (`npm run lint:html:built`)"; `dorny/paths-filter`
  pinned to a v4 commit (A.U28.13). (i) Closing sentence: "`tests_scripts/test_ci_workflow.py` pins these rules."
- **Resolved**: A.U1.16 and A.U1.21 disagree on the legacy shellcheck count ("28 findings"): A.U1.16 removes it from
  B.10.1, A.U1.21 calls B.10 its "one home, U36", and no U36 action keeps it. A count of legacy findings explains no
  current behaviour (CLAUDE.md legacy rule) — it goes. A.U27.14 (U27) and A.U8.15 (U8) touch the same sentence:
  Stage 1 U8 tags the minutes in place, Stage 2 U27 writes the 240 s budget, Stage 3 U28 the rest.
- **Unit**: Stage 1 U1 ((c)'s legacy clause); Stage 2 U8 (Part N pointer, A.U8.15); Stage 3 U27 ((c) mypy, (d));
  Stage 4 U28 (rest).
  A-C2 step order: A.U28.13's part lands in U0 (A.SDEP.05: "A.U28.13 (pulled forward)" into the GitHub Actions pin refresh).
- **Depends**: A.U28.01-A.U28.43, A.U27.14, A.U27.25, A.U8.15, M.SPEC.156.
- **Blast carried by**: `ci.yml` comments → A.U28.42 (TOOL); CLAUDE.md carriers → A.U28.11 (DOCS).
- **Kind**: doc

### M.SPEC.035 B.11: building this project's firmware
- **From**: A.U1.16 (`:946-950`, `:983-985`), A.U1.03 (the legacy text moves to `legacy/README.md`), A.U21.02 Blast
  (bump sentence), A.U27.02 Blast (stub sentence), A.U20.15 Blast (`:956` names the generator), M.GEN.019 (boot-entry
  names), A.U36.544 (2) (no "Session N" label), A.U36.011 (`:967-968`), A.U27.04 Blast (strip paragraph), A.U27.05 Blast
  (the shipped form boots under the twin), A.U27.06 Blast (build date the only varying value), A.U27.31 Blast (image
  report), A.U27.34 Blast (sorted freeze), A.U27.35 Blast (intermediates kept), A.U27.36 Blast (`--no-autostart`),
  A.U26.02 Blast (image record), A.U21.22 Blast (one build per toolchain directory); OR140.a (11) (the stub version moves
  with every MicroPython bump, checked), OR140.a (18) (no WoZi-specific wording), OR141.a (5) (the build date is a build
  input; two builds with one fixed date compare byte for byte), F21 tag form (A-C review fold).
- **Site**: `SPECIFICATION.md:937-993` (B.11).
- **Change**: (1) `:939-942` → "**Bumping the MicroPython version**: change `versions.toml`'s `[micropython] ref` — the
  only place — then run the platform re-check (CLAUDE.md "Platform target"; Part F's opening checklist). Everything else
  derives: matching pico-sdk/picotool (B.3) and the Unix ports; the stub post-releases pinned in `[stubs]` move with
  it — a check fails while their X.Y.Z differs from the ref (B.15; owner, 2026-10-02)." (2) `:944-948` → "The legacy build (`legacy/firmware/build-<device>.sh`)
  is described in `legacy/README.md`; reference-only." (3) `:950-956` → "**The `src/`-based build**:
  `scripts/build_firmware.py <device> [--output PATH] [--no-autostart]` assembles a real `firmware.uf2` from the
  generated device module, its boot entry, `src/` + `ext/microdot.py` + the device's website (H) — build-only. Every
  device needs its own `devices/<device>.toml` (Part L); `buildgen.codegen.generate_boot_entry_source()` emits the boot
  entry `sensortask_<device>_main.py`, frozen as `main.py`; `--no-autostart` freezes
  `sensortask_<device>_main_noautostart.py` instead, an image that starts at the REPL. One build at a time per toolchain
  directory, enforced by a lock; a second run fails at once naming the first. Each build writes an image record beside
  its `.uf2` and reports the image size against the filesystem boundary (the link refuses an overlap; the report gives
  the headroom). Build intermediates stay under `build/` for inspection and are wiped at the next start." (4) `:958-968`
  ("That entry point is frozen …"): "re-confirmed against pinned v1.29.0" → against the pin in force (C3); "A custom
  `_boot.py` whose `asyncio.run(main())` never returns (this script's earlier approach) means USB never initializes" →
  "A frozen `_boot.py` whose `asyncio.run(main())` never returns would keep USB from initializing"; "Fixed: freeze the
  real entry point as `"main.py"`, reusing the stock `manifest.py` unchanged." → "So the entry point is frozen as
  `"main.py"`, reusing the stock `manifest.py` unchanged."; `:967-968` → A.U36.011's sentence without its WoZi clause:
  "Confirmed working on real hardware on `dev`'s own image; a dev-native bench proof holds for every device (CLAUDE.md's
  `dev` rule)." (no build but `dev` has a role of its own, owner, 2026-10-02). (5) `:970-977` (strip
  paragraph) → A.U27.04's mechanism: every `TYPE_CHECKING` form is blanked line for line in the staged copy, without
  `ast.unparse()`, so comments elsewhere survive and an on-device traceback's line numbers match `src/` (its decision tag
  "(agent, 2026-09-30; owner-reviewed, 2026-10-02)"); the ~3.6 KB figure stays as the reason. (6) `:979-984` → "`tests_scripts/` (CPython/pytest) covers the build tooling fast and
  offline; `test_real_firmware_build_produces_a_valid_uf2` does the real end-to-end build, parametrized over every
  device, gated behind `RUN_SLOW_FIRMWARE_BUILD=1` and run per device in CI's `firmware-build-verify` — this pipeline's
  CI firmware-build stage. `freeze()` receives this project's modules as a sorted list. The build date is a build
  input: a real build stamps its UTC build time into the build information (L.7), and the reproducibility check builds
  twice with one fixed date and compares every other byte, while a second check proves that changing only the date
  changes only that line (owner, 2026-10-05). The stock `ports/rp2/modules` freeze still follows the checkout's
  directory order (upstream's manifest, not staged here)." (7) `:986-993` (production-readiness) →
  "…proves the build assembles, that the stripped, compiled image set boots under the twin (the shipped form), and (via
  the real-website scenarios of `scripts/_digital_twin_scenarios.py`, H.7) that the booted twin serves the real website …";
  "and on first run caught a real bug (an early manifest omitted `ports/rp2/modules/rp2.py`, since fixed by reusing the
  stock manifest)" → "(it proved the stock manifest must be reused: an own manifest omitted `ports/rp2/modules/rp2.py`)".
- **Resolved**: (a) "parametrized over `wozi`/`dev`" is false at HEAD (`tests_scripts/test_build_firmware.py:196`
  parametrizes over `DEVICE_NAMES`) — corrected (adherence finding). (b) A.U20.15's "`<device>_boot.py`" naming is
  superseded by M.GEN.019 (C7). (c) "(retired, Session 6's finish criterion)" goes under A.U36.544 (2) (G9/R12). (d) The
  legacy paragraph's "path not yet genericized (BACKLOG.md)" goes with A.U1.16 (legacy work is never a to-do). (e) (7)
  lands after U25 deletes `tests/test_digital_twin_real_website_integration.py` (M.TWIN.136, A.U25.46): it names the
  harness scenarios that replace the file (M_TWIN gap, ledger pass).
- **Unit**: Stage 1 U1 ((2), (6)'s legacy clause); Stage 2 U20 ((3)'s generator/boot-entry names); Stage 3 U21 ((1)
  re-check, (3) lock); Stage 4 U26/U27 ((1) stubs and their bump check, (3) record/report/intermediates/`--no-autostart`,
  (5), (6) with the build-date input and the two-build check, (7)); Stage 5 U36 ((4), A.U36.011 without its WoZi
  clause).
- **Depends**: A.U1.03, A.U20.05, A.U20.15, A.U21.22, A.U26.02, A.U27.02, A.U27.04-.06, A.U27.31, A.U27.34-.36,
  M.GEN.019; M.SCR.066 and its tests (the build-date input and the two-build check, as the fold amends them); M.SCR.027
  (the stub pins checked against the ref's X.Y.Z).
- **Blast carried by**: README build section → A.U27.35/A.U27.36 (DOCS); `legacy/README.md` → A.U1.03 (DOCS); CLAUDE.md
  `dev` rule (M.DOCS.078).
- **Kind**: doc

### M.SPEC.036 B.12: tiered environment setup
- **From**: A.U1.16 (`:999` recipe pointer), A.U21.19 Blast (`$BENCH_AP_PASSWORD`), A.U21.24 Blast (the command table),
  A.U21.28 Blast (USB detection rule), A.U36.548 (G9/R11: incident pointer), A.U1.05 Blast (same pointer); OR140.a (1)
  (the bench AP password is a throwaway, passed plainly) (A-C review fold).
- **Site**: `SPECIFICATION.md:995-1023` (B.12).
- **Change**: (1) `:999` "automating `dev_legacy/README.md`'s manual `nmcli` recipe" → "automating
  `tests_hardware/README.md`'s manual `nmcli` recipe". (2) "**USB device detection**" paragraph → A.U21.28's rule: one
  board resolver — USB vendor `2e8a` plus MicroPython's by-id name, across every `ttyACM*`/`ttyUSB*` entry; exactly one
  match required, zero or several a hard error naming `--device`. (3) "unless overridden" → "unless `$BENCH_AP_PASSWORD`
  is set — a throwaway password used once, passed to `nmcli` on its command line and never committed (owner,
  2026-10-02)". (4) `:1017-1018` "`ip`/`nmcli` … missing ones auto-install via `apt`" → "every command a tier runs is checked
  and, unless `--skip-apt`, installed (the `_TIER_COMMANDS` table)". (5) `:1020-1023` "**Full `flash`/`bench`
  real-hardware verification is DONE** — both tiers run clean end to end on the real bench Rpi4 (2026-09-04); see B.13
  for the incident that interrupted the first attempt." → "`flash` and `bench` ran clean end to end on the bench Pi4
  (2026-09-04)."
- **Resolved**: (5) is G9/R11 (incident narrative out, measured fact with date stays); no action names the sentence —
  agent decision under A.U36.548's rule.
- **Unit**: Stage 1 U1 ((1)); Stage 2 U21 ((2)-(4)); Stage 3 U36 ((5)).
- **Depends**: A.U1.05, A.U21.19, A.U21.24, A.U21.28.
- **Blast carried by**: README tier table → A.U21.24 (DOCS); `tests_hardware/README.md` → A.U21.19/A.U21.28 (DOCS).
- **Kind**: doc

### M.SPEC.037 B.13: the dead-man's switch, the bridge MAC, the recovery script
- **From**: A.U36.523 (main), A.U0.33 C18 (`:1027` tag), A.U0.44 L36 (`:1037` tag), A.U0.19 H1.03 (`:1046-1047` tag),
  A.U1.16 (`:1042-1043` pointer), A.U21.23 (the installer arms the switch itself; the remedy text), A.U1.05 (the moved
  recipe points here), A.C.01 (reads B.13; no edit), A.U36.546 (CLAUDE.md keeps only the rule and pointer).
- **Site**: `SPECIFICATION.md:1025-1070` (B.13).
- **Change**: (1) `:1027` "**Standing rule**:" → "**Standing rule** (owner, 2026-09-26):"; the rest of the first
  paragraph to "not guessed." holds; `:1031-1035` → A.U36.523 (1). (2) `:1037-1044` → A.U36.523 (2), whose "(observed
  2026-09-04, `28c5d8e`)" reads "(agent, 2026-09-04, `28c5d8e`)" (A.U0.44 L36's tag folded), and its last clause "the
  manual recipe (`tests_hardware/README.md`) pins it the same way" (A.U1.16's pointer). (3) New paragraph after it
  (A.U21.23): "`ensure_bench_bridge()` arms the same switch itself for a bridge creation and for the channel re-pin: the
  restore profile is read at run time, never hard-coded, the timer is verified armed before the first change and
  disarmed only once the bridge has an address and the default route; the MAC-mismatch remedy it prints starts with
  arming it." (4) `:1046-1047` "Recreate this script fresh in a session's own scratchpad each time (deliberately not a
  committed file):" → "Recreate this script fresh in a session's own scratchpad each time (not a committed file: the
  pattern, not the file, is what's durable — owner, 2026-09-04, `1096b31`):". (5) Script block and step 1 → A.U36.523
  (3) (`RESTORE` read from `nmcli -g GENERAL.CONNECTION device show eth0`).
- **Resolved**: five actions edit B.13 (A.U36.523 lists them); each owns distinct sentences except `:1037-1044`, where
  A.U36.523's rewrite absorbs A.U0.44's tag and A.U1.16's pointer.
- **Unit**: Stage 1 U0 ((1) tag, (4)); Stage 2 U1 (pointer, on HEAD text); Stage 3 U21 ((3)); Stage 4 U36 ((1) rest,
  (2), (5)).
- **Depends**: A.U0.19, A.U0.33, A.U0.44, A.U1.16, A.U21.23.
- **Blast carried by**: CLAUDE.md dead-man's-switch/bridge-MAC rules → A.U36.546/A.U21.23 (DOCS); README `:104-108` →
  A.U36.522 (DOCS); `tests_hardware/README.md` → A.U1.05 (DOCS).
- **Kind**: doc

### M.SPEC.038 B.14 intro and general shape: every override proven in the built artefact
- **From**: A.U36.521 (2) (count-free intro), A.U21.09 Blast (intro count), A.U21.06 Blast (general shape: proven in the
  artefact), A.U21.08 Blast (paths resolved and refused), A.U21.15 (one diagnostics helper), A.U21.16 Blast (`:1093-1094`
  mbedtls mention follows the branch), A.U21.02 (the pin-move message cites B.14), A.SDEP.11 ((c): no SIGINT override);
  OR139.a (2) (a test-only override, refused in a release build; the count) (A-C review fold).
- **Site**: `SPECIFICATION.md:1072-1120` (B.14 up to B.14.1).
- **Change**: (1) `:1074` "(so far: two implemented, one identified and planned)" → "(each subsection below is
  implemented and proven in the built artefact)". (2) `:1093-1094` "the way the mbedtls GCC-14 workaround and
  `MICROPY_PY_SYS_SETTRACE=1` already do it" → "the way `MICROPY_PY_SYS_SETTRACE=1` does it" under A.U21.16's 2a, or
  "the way `MICROPY_PY_SYS_SETTRACE=1` and the one-file mbedtls flag do it" under 2b; "(`build_unix_port()`/
  `build_firmware()` grep their own output for `warning:`)" → "(every build's output passes one diagnostics check, B.7)".
  (3) The general-shape paragraph gains, after "or both;": "paths written into generated files are resolved and refused
  when they hold a character the target syntax cannot carry;" and, after "every build", "and each override is then
  proven in the built artefact — a readback of the preprocessed source or the build's own flags, never only the
  generated input", and (A-C review fold) "an override marked test-only is applied only to a build that asks for it by
  name, the build information names it, and a release build that carries it is refused (B.14.5)". (4) The "first real
  test" paragraph's runner list holds (`scripts/run_unix_port_integration.sh`
  stays, M.SCR). (5) Under A.SDEP.11 outcome (c) only: the list gains "the Unix port delivers SIGINT through
  `mp_sched_keyboard_interrupt()` by default (`<file:line>` at <tag>); no override is needed" and B.14.1 goes
  (M.SPEC.039).
- **Resolved**: A.U21.09 writes "three implemented" (U21); A.U36.521 replaces the count with a count-free form (U36),
  which also survives A.SDEP.11 (c) — Stage 1 U21 "(so far: four implemented, one of them a test-only override, and one
  documented and not built)" keeps the HEAD text true while B.14.3 still exists (the tick-offset override, M.SPEC.162,
  lands in the same unit; A-C review fold, OR139.a); Stage 2 U36 the count-free form.
- **Unit**: Stage 1 U21 ((1) interim, (2), (3) with its test-only clause, after M.SPEC.162's subsection in the same
  unit); Stage 2 U36 ((1) final; "B.14.5" → "B.14.4" with M.SPEC.162's renumbering). (5) at U0 if A.SDEP.11 (c).
- **Depends**: A.U21.06, A.U21.08, A.U21.09, A.U21.15, A.U21.16, A.SDEP.11, M.SPEC.162.
- **Blast carried by**: `micropython_overrides.py` docstrings → A.U21.08 (TOOL).
- **Kind**: doc

### M.SPEC.039 B.14.1 `unix_kbd_intr`: proven per binary, the problem stated as evidence
- **From**: A.U21.06 (Change error text cites B.14.1; Blast "Verified" paragraph), A.U36.037 (2) (`:1154-1157`), A.U36.548
  (10) (`:1126`, "Root-caused by reproducing"), A.U36.511 (4) (`:1132` device count), A.U36.512 (MicroPython's `VARIANT`
  word stays here), A.U25.39 Blast (hands `:1156` to U36), A.SDEP.11 (re-check outcomes).
- **Site**: `SPECIFICATION.md:1122-1222` (B.14.1).
- **Change**: (1) `:1126` "**The problem, found root-causing a real, intermittent `digital-twin-e2e` CI failure**
  (2026-09-14/15):" → "**The problem** (reproduced 2026-09-14/15):"; "Root-caused by reproducing it directly" →
  "Reproduced by"; `:1132` "across all 6 real devices" → "across every device"; mechanism, reproducer and traceback stay
  as the evidence. (2) `:1154-1157` → A.U36.037 (2): "- a `gc.collect()` recovery (F.6) would patch that one downstream
  symptom, but nothing for" (the bullet keeps its tail). (3) "Verified" paragraph (`:1202-1208`) gains: "Every build
  re-proves it: `build_unix_port()` preprocesses `unix_mphal.c` with the build's own flags (`make
  <build>/unix_mphal.pp`) and fails unless the sentinel `MICROPY_SENSORS_KBD_INTR_OVERRIDE_APPLIED` and the deferred
  branch are present and `nlr_jump(` is absent — for `build-standard`, `build-settrace` and `build-lwip` alike."; "`build_unix_port()`
  (both call sites - the frozen-verification build and the vanilla test-rig rebuild) applies this unconditionally" →
  "every Unix-port build applies this unconditionally"; "across all 6 real devices" (`:1204`) → "across all six devices
  then defined". (4) "confirmed against the pinned `v1.29.0` source", `mpconfigvariant_common.h`'s anchor and the
  re-verification checklist re-read at the refreshed pin (A.SDEP.11): under (a) unchanged but the tag; (b) the anchor
  text, the generated pair and the hammer-loop record rewritten; (c) B.14.1 removed (M.SPEC.038 (5)).
- **Resolved**: A.U36.548 (10) ties (1) to "only while A.SDEP.11 keeps the override" — under (c) the section goes and
  (1)-(3) are void. The measured 700+ iterations were across the six devices of 2026-09-15; "every device" would restate
  the evidence, so the Verified paragraph names the six of that day (agent decision); `:1132` follows A.U36.511 (4) as
  written.
- **Unit**: Stage 1 U0 ((4), A.SDEP.11); Stage 2 U21 ((3)); Stage 3 U25 ((2), with M.SPEC.106 and A.U25.39's
  retirement); Stage 4 U36 ((1)).
- **Depends**: A.SDEP.11, A.U21.06, A.U21.12, A.U25.39, M.SPEC.106.
- **Blast carried by**: CLAUDE.md `:665-695` → A.U36.037 (3)/A.SDEP.11 (DOCS).
- **Kind**: doc

### M.SPEC.040 B.14.2: the UDP pcb budget, the tunables, the anchors at the refreshed pin
- **From**: A.U18.18 (UDP pcb budget), A.U8.14 Blast (B.14.2 cites Part N), A.SDEP.14 (anchors and ensemble re-verified;
  `:1375` 2,324 B), A.SDEP.08 (C3 on every `v1.29.0` citation).
- **Site**: `SPECIFICATION.md:1224-1306` (B.14.2).
- **Change**: (1) After "`MEMP_NUM_UDP_PCB` is a **bare `#define`** (`4 + LWIP_MDNS_RESPONDER`)" A.U18.18's text verbatim
  ("Its 5 pcbs cover every UDP user at once: … frees its pcb (`cyw43_ctrl.c:118-127`, `cyw43_lwip.c:251-257`, lwIP
  `dhcp.c:1386-1389`)"), with its file:line cites re-read at the refreshed pin and lwIP commit (C3), and the module names
  as landed (`asy_captive_dns`, NTP/resolver per M.SRC_NET). (2) The `[lwip]` paragraph ("`toolchain/versions.toml`'s
  `[lwip]` table is that file") gains "each option a Part N row (`lwip.*`)". (3) "verified against `v1.29.0` as fetched"
  and every upstream file:line in the section re-stamped at the refreshed pin, the twenty-one-anchor count restated if
  A.SDEP.14 changed it.
- **Resolved**: — (no conflict among the constituents)
- **Unit**: Stage 1 U0 ((3)); Stage 2 U8 ((2)); Stage 3 U18 ((1)).
- **Depends**: A.SDEP.08, A.SDEP.14, A.U8.14, A.U18.02/.09/.15/.16 (the bounds A.U18.18 states).
- **Blast carried by**: `versions.toml` tags → A.U8.14 (TOOL).
- **Kind**: doc

### M.SPEC.041 B.14.2.1: the send stall, the segment pool and what fixes it
- **From**: A.U14.30 (1)-(2) (and its H.7 change, carried in M.SPEC.121), A.U21.09 Blast (the stall sentence names the
  override, owner 2026-09-30), A.SDEP.13 (upstream fix at the refreshed pin), A.SDEP.08 (5) (baseline and table header
  re-measured), A.SDEP.14, A.U0.44 L28 (`:1330` tag), A.U8.14 Blast (Part N), A.U21.14/A.C.06/A.C.10 (phase-C result
  replaces the "Not yet reproduced" sentence), A.U36.548 (G9/R11: archive pointers stay as evidence).
- **Site**: `SPECIFICATION.md:1308-1388` (B.14.2.1).
- **Change**: (1) `:1315-1317` → A.U14.30 change 2 verbatim ("— a full window of full-MSS segments per admitted
  connection. It does not stop the pool running out: … one of the three `ERR_MEM` sources below."). (2) `:1322-1325` →
  A.U14.30 change 1 verbatim, its pointer reading "(B.14.3, the `modlwip_eagain` override)" and its stall-fix sentence
  carrying A.U21.09's tag: "The firmware build replaces that loop (B.14.3, the `modlwip_eagain` override; owner,
  2026-09-30): a non-blocking write that meets `ERR_MEM` returns `EAGAIN`, and the webserver's per-call write timeout
  bounds the wait cooperatively." Under A.SDEP.13 (a) that sentence is instead "The pinned MicroPython carries the fix
  (`<tag>`, `<file:line>`): …" with no override pointer. The last sentence "Not yet reproduced on silicon … (agent,
  2026-09-30)." becomes phase C's recorded result (A.U21.14) when it has run: "Reproduced on `dev` on the pre-override
  image and absent on the override image (agent, <date>, <image build dates>)". (3) `:1330` "**`PBUF_POOL_SIZE` is
  deliberately left alone.**" → "**`PBUF_POOL_SIZE` stays at the port default (agent, 2026-09-22, `31da2b3`).**". (4)
  "**Measured cost, from real builds** (`RPI_PICO_W`, v1.29.0, …)": under a moved pin, the baseline line, the table
  header and the "shipped image's own linker heap" are re-measured (A.SDEP.08 (5)); the deltas stand unless the
  measurement moves them; the 2,324 B figure re-checked (A.SDEP.14). (5) The ensemble values cite Part N's `lwip.*` rows.
- **Resolved**: A.U14.30 (U14) and A.U21.09 (U21) rewrite the same sentence; A.U21.09's Blast routes its text onto
  A.U14.30's revised one (A-C) — one sentence with A.U21.09's name and tag; the pointer is B.14.3's end-state number
  (U21 writes "B.14.4", C6). A.U14.30 says the static `MEM_SIZE` proof and sizing are withdrawn (OR114.a) — nothing
  else in the section moves.
- **Unit**: Stage 1 U0 ((3) tag; (4) if the pin moved); Stage 2 U14 ((1)); Stage 3 U21 ((2) less its last sentence's
  result); Stage 4 phase C delta (A.C.10, (2)'s result); U36 repoints "B.14.4" → "B.14.3" (M.SPEC.042).
  A-C2 step order: A.U14.30's part lands in U19, not U14 (it needs A.U19.24, which lands in U19).
- **Depends**: A.U14.30, A.U21.09, A.U21.14, A.SDEP.08, A.SDEP.13, A.SDEP.14, M.SPEC.042, M.SPEC.121.
- **Blast carried by**: `micropython_overrides.py:263-265` comment → A.U14.30 (TOOL).
- **Kind**: doc

### M.SPEC.042 B.14.3: the littlefs subsection goes; `modlwip_eagain` takes its number
- **From**: A.U36.521 (B.14.3 deleted, deferral to BACKLOG), A.U21.09 (new subsection), A.U21.12 (the host build
  belongs in it), A.U21.13 (the spin-round test bounds the busy wait), A.U21.14/A.C.06 (phase-C proof recorded),
  A.SDEP.13 (outcome (a): no override), A.SDEP.08 (B.14.3's mechanism re-verified at the new tag while it exists),
  A.U0.33 D04 (`:1390-1393` lead rewrite), A.U0.34 (BACKLOG item's pointer), A.U27.31 (the trigger).
- **Site**: `SPECIFICATION.md:1390-1418` (HEAD B.14.3); new subsection after it.
- **Change**: (1) U21: new "### B.14.4 `modlwip_eagain` (implemented) - a non-blocking modlwip send returns `EAGAIN` on
  `ERR_MEM`" after HEAD's B.14.3, as A.U21.09's Blast lists it: the mechanism (the patched copy of `extmod/modlwip.c`
  with the `socket->timeout == 0` early return inside the `ERR_MEM` retry loop, generated outside the checkout; the
  CMake swap of `MICROPY_SOURCE_EXTMOD`'s entry; the include rewrite), the anchors (loop, insertion point, include and
  the build files' lines), the post-build proof, the host build `build-lwip` (A.U21.12: the same copy over loopback lwIP,
  `MEM_ALIGNMENT` at host pointer size, lwIP driven from the event hook, asserts that abort — its divergences are F.7's),
  the removal trigger "the pin carries an upstream fix for micropython issue 19704 (PRs 19705/19708)", and the cost:
  "POLLOUT reports writable while `tcp_sndbuf() > 0`, so with the arena full the retry is a cooperative busy wait until
  the peer ACKs or the per-call timeout fires — its duration bounded by that timeout, its per-round cost by the lwIP
  host build's spin-round test and on the dev bench (`l4.lwip_spin_concurrent_request_max_s`); a failed bound goes to the
  owner as a change to the override (a short POLLOUT back-off after `EAGAIN`) (owner, 2026-09-30)." Under A.SDEP.13 (a)
  the subsection is not written; B.14.2.1 states the upstream fix (M.SPEC.041). (2) U36: HEAD's B.14.3 (`:1390-1418`)
  deleted (A.U36.521 (1)); "### B.14.4" renumbered "### B.14.3" and every citer repointed (M.SPEC.030, M.SPEC.041,
  M.SPEC.107, M.SPEC.121; code comments cite "SPECIFICATION.md B.14" only). (3) Phase C (A.C.10 delta): the proof
  sentence records the A.U21.14 result.
- **Resolved**: (a) A.U0.33 D04 rewrites B.14.3's lead in U0 and keeps "The mechanism below stays documented for that
  day"; A.U36.521 (U36, the register's later clause) removes the text — A.U0.33's `:1390-1393` edit is dropped (void
  at U36; landing it in U0 and deleting it in U36 would only churn). (b) A.U21.09 numbered its subsection after B.14.3
  "goes with U36"; until U36 the old B.14.3 exists, so U21 lands B.14.4 and U36 renumbers it (C5/C6). (c) A.U0.34's
  BACKLOG pointer "mechanism SPEC B.14.3" is replaced by A.U36.521 (3)'s self-contained item (DOCS).
- **Unit**: Stage 1 U21 ((1)); Stage 2 phase C ((3)); Stage 3 U36 ((2)).
- **Depends**: A.U21.09-A.U21.14, A.SDEP.13, A.U27.31, A.U0.34, A.U36.521.
- **Blast carried by**: BACKLOG Deferred item → A.U36.521 (3)/A.U0.34 (DOCS); BACKLOG watch entry and CLAUDE.md
  "Platform target" sentence → A.U21.09 (DOCS).
- **Kind**: doc

### M.SPEC.162 New B.14.5: the test-only tick-offset override for the rollover round
- **From**: OR139/OR139.a (1)-(5) (owner, 2026-10-01: a test build with a starting offset); AC_NOTES 52 (OR139 owed:
  the override with its anchor check and release-build refusal, the build-info marker, SPEC B.14) (A-C review fold, F04).
- **Site**: new subsection `### B.14.5`, titled with the override's name as landed in `micropython_overrides.py` and
  "(test-only) - the tick counts wrap about 15 minutes after boot", after the `modlwip_eagain` subsection (HEAD B.14.3 and the U21 B.14.4 still exist at U21); renumbered B.14.4 at U36 with
  M.SPEC.042 (2)'s renumbering.
- **Change**: one subsection, in B.14's per-override shape: "**What it does.** A test build of the `dev` image that
  differs from it by one build define: `mp_hal_ticks_ms()` (`ports/rp2/mphalport.h:96-98`, v1.29.0, which also feeds
  the soft-timer queue, `ports/rp2/mphalport.c:236-241`, and lwIP's `sys_now()`, `ports/rp2/mpnetworkport.c:122-125`)
  returns the time since boot plus 2**32 ms minus 15 minutes, so `time.ticks_ms()` (period 2**30) and the 32-bit
  millisecond count both wrap about 15 minutes after boot. The hardware timer is never written: the SDK expects it to
  increase monotonically (RP2040 datasheet 4.6.2). **Why.** The rollover round then crosses both wraps in about two
  hours on silicon instead of a 12.4-day run (owner, 2026-10-01); the driven-clock proofs in the unit and twin tiers stay
  the per-commit proof (E.6). **Mechanism and anchor.** Applied by `toolchain/micropython_overrides.py` as a test-only
  override, generated outside the checkout like every other (B.14), with its anchor check on the `mp_hal_ticks_ms()`
  definition; it is applied only to a build that names it, the build information names it, and a check fails any
  release build that carries it. **Cost.** One flash cycle per round, counted in the round's flash budget. **Removal
  trigger.** None while the rollover round exists; its anchor is re-verified with every MicroPython version bump (Part
  F's opening checklist)." Where the anchor or the build-info field is spelled in code, the text names it as landed
  (C7); how the test build is requested on the build's command line is decided at execution, with its reason recorded.
- **Resolved**: — (new subsection; B.14.3/B.14.4 numbering per M.SPEC.042 (b): this one is B.14.5 until U36 deletes
  HEAD's B.14.3, then B.14.4).
- **Unit**: Stage 1 U21 (the subsection, with the override, its anchor check and the release-build refusal; without
  the clause "the build information names it" unless the code writing that name lands in U21 too); Stage 2 U27 (that
  clause, with the build information that names the override, where M.SCR produces it); Stage 3 U36 (renumbered B.14.4
  with M.SPEC.042 (2), every citer repointed).
- **Depends**: M.TOOL.080 (the override, anchor check and release-build refusal in
  `toolchain/micropython_overrides.py`), M.SCR.067, M.SCR.074 (the build information names the override; the rollover
  runner, M.SCR.074), M.SPEC.042 (subsection numbering).
- **Blast carried by**: E.6's rollover sentence → M.SPEC.082; F.1's tick paragraph pointer → M.SPEC.092;
  `tests_hardware/README.md` rollover round → M.HW_BENCH.126; BACKLOG chroot list (an override
  change touches the toolchain leg) → M.DOCS.066; README test recipe and command-line reference → M.DOCS.049/.052.
- **Kind**: doc

### M.SPEC.043 B.15: the three passes, what each checks, the stub workarounds
- **From**: A.U27.25 (main-pass/CI paths), A.U27.09 (generated output; `:1440-1442`), A.U20.14 Blast, A.U28.41 Blast,
  A.U27.23 (exclusions checked by another run), A.U0.60 (conftest label), A.U36.043 and A.U25.40 Blast
  (`segfault_stress_repro.py`), A.U27.22 (`ignore-without-code`), A.U27.24 (scope test), A.U27.02 (stub pins; moved
  tree fails), A.U27.03 (workaround list), A.U21.04 (`typings/.stub-spec`), A.U8.23 (Microdot stubs, OR131), A.U28.27
  Blast (two ignore groups), A.U28.39 (path check), A.U33.06 Blast (E722 text may move here), A.U36.527 (B.15 lists the
  passes; `disallow_any_explicit` is C.10's), A.U36.546 (CLAUDE.md's stub-gap and stub-repair narrative moves here),
  A.SDEP.03/A.SDEP.15 (re-read at the refreshed tool and stub versions), M_DOCS gap 1 (c) (BACKLOG `:730-739`'s
  standalone-mypy `Timer()` note, M.DOCS.065); OR140.a (11) (the stub version moves with every MicroPython bump,
  enforced by the check) (A-C review fold).
- **Site**: `SPECIFICATION.md:1422-1482` (B.15).
- **Change**: (1) Main pass heading paths → "(`src`, `tests`, `digital_twin`, `tests_hardware/device_scripts`,
  `build/generated_src`)"; the `build/generated_src` bullet (`:1440-1442`) → "`build/generated_src` is both a `files`
  entry — the generated device modules and boot entries are checked as sources, with `src/`'s lint rules and no emitted
  suppression — and on `mypy_path` for the twin pass's imports; `typecheck.sh` generates it first." (2) `mypy_path`
  bullet gains "`ext/typings` holds Microdot's upstream stub, vendored unmodified at `ext/typings/microdot/` (same policy
  as `ext/microdot.py`)". (3) Excluded list: `segfault_stress_repro.py` goes; "Their apparent cleanliness in this pass was
  accidental: …" → "The twin pass checks them (`digital_twin/typecheck.ini` `files` names `digital_twin`, every
  `tests/test_digital_twin_*.py` and the two scenario libraries)."; `tests/network.py` gains "checked alone by
  `typecheck.sh`". (4) Strictness line gains `ignore-without-code`; the `test_setter_microdot_integration`
  decorator override is restated as "upstream's stub leaves `route`/`get`/`put` unannotated (v2.6.2)". (5) Twin pass:
  "its strictness is kept in sync with the main pass by hand (INI has no include directive)" → "…, checked by
  `tests_scripts/test_lint_type_scopes.py` (INI has no include directive)". (6) Host pass: the `tests_scripts/conftest.py`
  bullet → "`tests_scripts/conftest.py` is checked alone by `typecheck.sh` (with both test roots on `mypy_path` it would
  be a second bare `conftest`); `tests_hardware/conftest.py` keeps the slot." — or, if A.U27.23's single-file run still
  reports a duplicate module, "excluded: <the true reason> (agent, 2026-09-24)" (A.U0.60). (7) New closing paragraphs:
  "**CI and local runs agree**: CI passes exactly the main pass's `files`; a local run may narrow it with arguments.
  `tests_scripts/test_lint_type_scopes.py` pins the three configs and every lint scope; an L0 check resolves every path
  the config files name. Ruff's global ignores are two groups, each narrowed to the scopes its reason covers (D.6)."
  and "**Stubs**: `typecheck.sh` installs the exact post-releases `toolchain/versions.toml` `[stubs]` pins, whose X.Y.Z
  must equal the ref's — so the stubs move with every MicroPython bump, and the check fails until they do (owner,
  2026-10-02) — prints and records them in `typings/.stub-spec`, and repairs the package's verified defects
  after installing it, each guarded on the defect still being present and failing when the file it targets moved
  (F.5.5)." followed by A.U27.03's "Stub workarounds and their removal triggers" list (the two F.5.5 repairs first,
  then `Timer()`, `const()` of a tuple, `_mpy_shed.time_mp._TicksMs`, `DeflateIO`), each line's stub version re-read at
  the refreshed pin (A.SDEP.15); the `Timer()` line adds (M_DOCS gap 1 (c), BACKLOG's standalone-mypy entry, which leaves
  at U37): "a `mypy` run over `src/` or `tests_hardware/device_scripts/` alone resolves `machine` to the board stub and
  reports every bare `Timer()` (`timer_alarm_pool_exhaustion.py`, `scheduler_saturation_drop.py` among them); every run
  this project makes includes `tests/`, whose `tests/machine.py` models `Timer()` and wins resolution, so such a finding
  is the stub gap, not a regression". (8) If U36's CLAUDE.md pass moves the E722 bullet here (A.U33.06), it lands as is.
- **Resolved**: (a) A.U0.60 is conditional on A.U27.23: (6) takes whichever outcome A.U27.23 records. (b) A.U36.043
  (U36) and A.U25.40 (U25) remove the same token — lands with A.U25.40's retirement (U25) so the list never names a
  deleted file; A.U36.043's SPEC half is then done. (c) A.U36.546 sends CLAUDE.md's stub narrative here "per
  A.U27.02/A.U27.03" — the defect facts live in F.5.5; B.15 carries the list and pointer, not a second copy.
- **Unit**: Stage 1 U8 ((2), (4) override text — A.U8.23); Stage 2 U25 ((3) token); Stage 3 U27 (rest); U36 (8) only.
- **Depends**: A.U8.23, A.U21.04, A.U25.40, A.U27.02, A.U27.03, A.U27.09, A.U27.22-.25, A.U28.27, A.U28.39, A.U28.41,
  M.SPEC.104, M.SPEC.075, M.SCR.027 (the X.Y.Z check).
- **Blast carried by**: CLAUDE.md mypy/stub/scope bullets → A.U36.546/A.U27.22/A.U27.23 (DOCS); `pyproject.toml`,
  `host_typecheck.ini`, `typecheck.ini` comments → A.U27.23/A.U27.25/A.U0.60 (TOOL).
- **Kind**: doc

### M.SPEC.044 New B.16: checkers measured and declined
- **From**: A.U33.05 (1) (section), A.U0.37 (tag on `BACKLOG.md:740`, moves with the text), A.U15.02 (vulture `cast()`
  clause already absent).
- **Site**: new `## B.16 Checkers measured and declined` after B.15 (`:1482`), before Part C.
- **Change**: A.U33.05 (1)'s text verbatim, tagged "(agent, 2026-09-10)" with the vulture sentence's "(owner,
  2026-09-26)". H.8's `npm audit` sentence is M.SPEC.124.
- **Resolved**: — (no conflict among the constituents)
- **Unit**: U33.
- **Depends**: M.SPEC.043 (B.15 above it).
- **Blast carried by**: `BACKLOG.md:739-776` deletion → A.U33.05 (3) (DOCS).
- **Kind**: doc

### M.SPEC.045 New B.17: build-environment verification (clean chroot)
- **From**: A.U36.524 (1) (section), A.U28.02 (the pinned `pip install "uv==<v>"` line), A.U36.546 (CLAUDE.md sheds the
  recipe), A.U36.548 (G9/R11 history out), A.U0.39 L37 (owner tag on "Two targets"), A.U21.16 (trixie wording), M_DOCS
  gap 1 (f).
- **Site**: new `## B.17 Build-environment verification (clean chroot: Ubuntu 24.04 and Debian trixie)` after B.16.
- **Change**: A.U36.524 (1) (a)-(f) verbatim: CLAUDE.md `:870-1033` moved with the opening rewritten, each comment
  block ≤ 3 lines, the trixie reason kept, the "last satisfied" paragraph and dated confirmations out, the installer
  leg's B.6/B.7 pointers kept; the pip line in A.U28.02's pinned form. Two merged amendments (M_DOCS gap 1 (f),
  M.DOCS.106): "Two targets, both required" carries A.U0.39 L37's "(owner, 2026-09-11)"; the trixie paragraph's mbedtls
  sentence takes A.U21.16's wording — "the mbedtls `mbedtls_xor()` `-Warray-bounds` false positive (B.7.1) is the kind of
  GCC ≥ 14-only diagnostic noble cannot see, and the build treats any `warning:` as fatal" — in the tense B.7.1's branch
  leaves (M.SPEC.031).
- **Resolved**: — (no conflict among the constituents)
- **Unit**: U36.
- **Depends**: A.U28.02, A.U33.04, M.SPEC.044.
- **Blast carried by**: CLAUDE.md section, PR-workflow bullet, `:496` → A.U36.524 (2)-(4) (DOCS); BACKLOG chroot head →
  A.U36.524 (5) (DOCS); SPEC `:6-7` → M.SPEC.001; SPEC `:812` → M.SPEC.031.
- **Kind**: doc

## SPECIFICATION.md — Part C (`:1484-2588`)

### M.SPEC.046 Part C intro and C.1: the generated device module replaces the hand-written one
- **From**: A.U36.543 (8) (`:1489-1491`), A.U36.535 (4) (C.1 `:1495`, `:1503-1504`), A.U15.40 (four drivers), A.U10.37
  (module names, M.SPEC.008), A.U10.29 Blast (C.1 const pointer is U14's — nothing names it in C.1 at HEAD).
- **Site**: `SPECIFICATION.md:1486-1504`.
- **Change**: (1) `:1486-1489` "Extracted from the three drivers first promoted to `src/` (`asy_scd30_driver.py`,
  `asy_bmp3xx_driver.py`, `asy_sgp40_driver.py`) plus shared infrastructure (…)" → "Extracted from the sensor drivers in
  `src/` (four today: `asy_scd30_driver.py`, `asy_bmp3xx_driver.py`, `asy_sgp40_driver.py`, `asy_isl29125_driver.py`)
  plus the shared infrastructure (`asy_base_classes.py`, `asy_i2c_driver.py`/`asy_spi_driver.py`, `asy_config_manager.py`,
  `asy_print_log.py`, `asy_system_service.py`)" — module spellings as landed (C7). (2) `:1489-1491` → A.U36.543 (8)'s
  sentence "Part D is the quality bar; Part K the ordered checklist that applies both." (3) C.1 code block and the
  closing sentence → A.U36.535 (4) verbatim.
- **Resolved**: "the three drivers" is false at HEAD (ISL29125 promoted) — corrected with A.U15.40's "four today"
  (adherence finding: a stale count, stated as today's fact per OR43.a (3)).
- **Unit**: U36 (with the Part K rewrite); module spellings from U10 (M.SPEC.008).
- **Depends**: M.SPEC.008, M.SPEC.140.
- **Blast carried by**: `src/system_service.py:1` header → A.U36.535 (5) (SRC_CORE).
- **Kind**: doc

### M.SPEC.047 C.2: naming, the shared session class, the constructor tail
- **From**: A.U0.40 L01 (`:1510-1511`), OR141.a (3) (`voc_algorithm.py` the one exception to the naming and
  member-ordering rules; A.U10.33's reorder and the naming harmonisation inside it dropped) (A-C review fold), A.U10.38
  (derivation rule and exception table), A.U10.35 (private by default),
  A.U10.39 (`_VAL_` names; `_cfg_schema` private), A.U10.21 (one `setup()` contract named), A.U15.40 (4) (`DeviceSession`),
  A.U5.02 Blast (constructor-order rule → the tail), A.U5.09/A.U18.40 Blasts (WiFi's constructor), A.U36.542 (0.4 cites C.2
  for naming and "private by default").
- **Site**: `SPECIFICATION.md:1505-1544` (C.2).
- **Change**: (1) First paragraph: after the CapWords sentence add A.U10.38's rule: "A module's primary class name derives
  from its file name (`asy_<x>_service.py` → `<X>Service`, `asy_<x>_driver.py` → `<X>Driver` unless C.2's compound
  applies); no class carries an `Asy` prefix; acronyms are upper-case (`UARTComm`, `CRCPass`, `NTPClient`,
  `FRAMManager`). Exceptions: the peripheral wrappers `I2C`/`SPI`/`UART` keep the `machine` names (the originals are
  imported under private aliases), and a chip class is the `<CHIP>_<Role>` compound with the chip spelled as its
  `_NAME` (`BMP3XX_Reader`, `SCD30_I2C`, `FRAM_SPI`)." "Name-mangled …" holds. `:1510-1511` → A.U0.40 L01's sentence
  widened by the owner's ruling (A-C review fold): "The one named exception to the naming rules and to D.15's member
  order (agent, 2026-08-11, `f27b33b`; owner, 2026-10-05): `src/voc_algorithm.py` stays a literal port — its names,
  casing and order are upstream's, tracing the DFRobot/Sensirion source 1:1 (F.4); only the class other modules import
  follows the scheme." (2) New sentence (A.U10.35): "Attributes and methods are private by default; one
  is public only when another module needs it or it is general-purpose driver API (the FRAM and bus APIs, C.3.1)." (3)
  `_VAL_` bullet: "`_VAL_<KEY_IN_UPPER_SNAKE> = const(((\"<Field>\", \"<type>\", default, min, max, special),))` — one
  schema tuple per config field, named after its key (C.5)"; the `_WIRING` clause → "cross-instance dependencies are
  `# @wiring …` comment tags beside the schema (C.14.2, L.6.4) — none when the driver has none" (gap fill: C.2 still
  describes the pre-2026-09-10 Python `_WIRING` tuple that C.14.2 says no longer exists). (4) The session bullet and its
  code block → A.U15.40 (4): "- `DeviceSession` (`asy_base_classes.py`, G.2): one device's session lock plus its bus
  device; every driver builds its own `DeviceSession(I2CDevice(bus, addr))`, no per-driver subclass." (5) Constructor
  order (`:1537-1544`) → "`<Chip>_I2C`/`_SPI` (layer 2), `<Chip>_Reader` (layer 3). A module constructor takes its own
  parameters (bus handle, addressing/pins, `@wiring`-resolved references, `trigger_sec` where configurable — SGP40's is
  not, C.11 item 6), then the fixed tail `max_module_error=5`, `name_ext=""`, `cfg_path=""` (those it has) and one
  `log: LogConfig = DEFAULT_LOG` (C.7) (agent, 2026-08-07; checked by a test). `setup()` is `async def setup(self) ->
  bool` with no parameters (C.13). **`max_module_error` is a generic failure-streak threshold, not I2C-specific** —
  `asy_wifi_service.py` uses it too through `_error_check()` (C.7)." (`asy_ntp_client.py` leaves the sentence: NTP has no
  streak, C.7.2.)
- **Resolved**: A.U10.38 renames `BMP3xx_DeviceSession` → `BMP3XX_DeviceSession`, then A.U15.40 removes every per-driver
  session class (M.SRC_SENS) — C.2 names only `DeviceSession`. "`trigger_sec: int = <n>` … `history_length: int = 10`,
  `debug: int | None = None`" is replaced by the tail (A.U5.02); A.U5.02's Blast names "the constructor-order rule,
  rewritten to the tail" without the text, written here (agent decision). The NTP mention of `max_module_error` goes:
  C.7.2 already says NTP's constructor lost it (fact at HEAD; adherence finding).
- **Unit**: Stage 1 U0 ((1) L01 tag); Stage 2 U5 ((5) tail); Stage 3 U10 ((1) rule, (2), (3) `_VAL_` names, (5) setup
  contract); Stage 4 U15 ((4)); (3)'s `@wiring` gap fill lands in U10 with the names.
- **Depends**: A.U5.01, A.U5.02, A.U10.21, A.U10.35, A.U10.38, A.U10.39, A.U15.40, M.SPEC.008.
- **Blast carried by**: `pyproject.toml` N801 per-file entries → A.U10.38 (TOOL); the name/order checks → A.U15.40/A.U5.18
  (TSC).
- **Kind**: doc

### M.SPEC.048 C.3: the protocol layer's raise surface and buffers
- **From**: A.U13.01 (`:1550-1552`), A.U16.16 (`:1552-1555`), A.U13.07 (I2C transfers report bool on an uninitialised
  bus), A.U13.08 (SPI availability as `False`), A.U13.09 (drivers treat it as a failed transfer), A.U13.10 (burst read),
  A.U13.R01 (`clear()`/`recover()`), A.U10.45 (raise-message form), A.U0.19 H2.16 (`:1566` tag), A.U15.01 (no change: C.3
  already requires the range gate), A.U14.14 Blast (C.3 points to F.1), A.C.15 (SCD30 facts belong to Part M; no C.3
  edit).
- **Site**: `SPECIFICATION.md:1546-1574` (C.3).
- **Change**: (1) `:1550-1552` → A.U13.01's sentence (BMP3XX_I2C "needs no scratch of its own — those helpers read into
  the bus's shared scratch (G.2)", `get_register_bytes()` listed). (2) `:1552-1555` → A.U16.16's sentence ("A class
  that builds its own buffers allocates them once as well: `FRAM_SPI` keeps its ID, status, address and WRSR buffers
  from `__init__` and sends its one-byte commands as module constants."). (3) The carve-out bullets: "**This carve-out's
  fault surface is bus-specific.**" bullet → "`asy_i2c_driver.py` raises `OSError` from a transfer; `asy_spi_driver.py`'s
  `write()` cannot raise on rp2, while `readinto()`/`write_readinto()` can raise `OSError(EIO)` on a 32+ byte RX overrun
  (F.5.2). An uninitialised bus is never a raise: every I2C and SPI transfer, `configure()` and `session_begin()` answer
  `False`/`None`, and a driver treats that as a failed transfer. `write_readinto()` returns `False` for a caller-input
  length mismatch. What rp2's buses raise and answer: F.1." (4) New bullet after it (A.U13.R01): "**Bus recovery**:
  `I2C.clear()` clocks a held bus free (at most nine pulses, then a STOP, bounded by the bus timeout) and `I2C.recover()` rebuilds the controller —
  re-construction being the only controller re-init rp2 offers; both report their outcome as status bits, never a
  raise. They are the bus rungs of the recovery ladder (C.7)." (5) `:1566` identity bullet gains "(SCD30's: owner,
  2026-07-21, `e960d44`: 'Owner decision: add it.')". (6) A new closing sentence (A.U10.45): "A raise carries one message
  form — a fixed string naming the condition, the values as separate arguments — and an `except` tuple lists its classes
  alphabetically (`(MemoryError, OSError)`)."
- **Resolved**: A.U13.01 and A.U16.16 edit adjacent sentences (A.U16.16 Depends) — one paragraph, both texts.
- **Unit**: Stage 1 U0 ((5)); Stage 2 U10 ((6)); Stage 3 U13 ((1), (3), (4)); Stage 4 U16 ((2)).
- **Depends**: A.U13.01, A.U13.07-.10, A.U13.R01, A.U16.16, M.SPEC.090, M.SPEC.101.
- **Blast carried by**: bus driver code/tests → U13 actions (SRC_CORE/TEST_UNIT); Part N `i2c.clear_half_period_us` →
  M.SPEC.156.
- **Kind**: doc

### M.SPEC.049 C.3.1: the SPI variant and FRAM's general-purpose API
- **From**: A.U13.05 (per-CS init cost; CS pad state), A.U16.04 (FRAM API and caller rule), A.U16.20 + A.U20.10 (`max_size`
  legal set; the TOML names its part), A.U16.15 (partly protected status register), A.U16.R01 (WREN retried once),
  A.U16.R02 (three identification attempts), A.S0930.17/.30 (`quiesce()`, `erase_ready()`, `erase_chip()`), A.U36.546 (2)
  (`:1603-1604` chip facts move to M.6), A.U1.04 (dev bench facts live in `tests_hardware/README.md`; no SPEC edit).
- **Site**: `SPECIFICATION.md:1576-1605` (C.3.1).
- **Change**: (1) The synchronous-session bullet (`:1591-1598`) gains A.U13.05's first sentence (the per-CS `SPI.init()`
  cost) and, as its second, the lead's rewrite (AC_NOTES 11): "During reset and until `setup()` configures the pin, the
  FRAM CS pad sits at an intermediate level (0.22-0.74 × VDD on the MB85RS64V) between the RP2040 pad's default pull-down
  (50-80 kΩ, RP2040 datasheet 2.19) and the chip's internal CS pull-up (MB85RS64V 28-180 kΩ, MB85RS2MTA 18-80 kΩ); SCK
  and SI are pulled down with it, so no op-code can be clocked in. The datasheets' power-on hold time (CS high for tpu
  after VDD reaches its minimum: 0.6 ms MB85RS64V p.17, 250 µs MB85RS2MTA p.18) is met by construction: the first CS low
  comes after the crystal start and the whole MicroPython boot (agent, 2026-09-29)." The executor re-reads the cited
  datasheet pages before writing the figures. (2) The `_setup_addr_buffer()` bullet (`:1599-1605`):
  "Two real chips: `MB85RS64V` (8KB, `0x2000`) and `MB85RS2MTA` (256KB, `0x40000`, `datasheets/fram/…` p.10)." → "The
  supported parts and their sizes: M.6."; "`setup()` raises `OSError` on a size/chip mismatch, `ValueError` on an
  unrecognized `max_size`. A genuinely new size needs its own table entry." → "`setup()` makes up to three identification
  attempts, then raises `OSError` on a size/chip mismatch, `ValueError` on an unrecognized `max_size`. Every device TOML
  names its FRAM part; a genuinely new size needs its own `_KNOWN_PRODUCT_IDS` entry and the `@limits max_size` set
  (checked equal by a test)." (3) New bullet after it: A.U16.04's text verbatim ("**`FRAM_SPI`'s general-purpose API** …
  as the chunk layer's `_read_chunk()` does."), extended: "A WREN whose latch did not set is repeated once, like WRDI; a
  status register with only some protection bits set is reported and treated as protected. The manager's
  `quiesce()`, `erase_ready()` and `erase_chip()` serve the two shutdown commands (A.8): the erase holds both FRAM locks
  per 256-byte unit and never across an await of another lock (C.8)."
- **Resolved**: A.U16.20 and A.U20.10 rewrite the same sentence (A.U20.10: "joins the same sentence") — one sentence.
  A.U36.546 moves the chip facts to M.6 in U36; until then the text stays in C.3.1. A.U13.05's second sentence as first
  written (pull-up needed, phase-C measurement) is superseded by the lead's withdrawal (AC_NOTES 11, 23; the lead's note
  at the end of `U13.md`, 2026-09-29).
- **Unit**: Stage 1 U13 ((1)); Stage 2 U16 ((2) attempts/legal set, (3)); Stage 3 U20 ((2) "names its part"); Stage 4
  S0930 per its unit ((3) erase API); Stage 5 U36 ((2) M.6 pointer).
  A-C2: "S0930" is not a unit; its parts land in the units SUPP_owner_0930 states: A.S0930.17 in U16, A.S0930.30 in U36.
- **Depends**: A.U13.05, A.U16.04, A.U16.15, A.U16.20, A.U16.R01, A.U16.R02, A.U20.10, A.S0930.17, M.SPEC.152.
- **Blast carried by**: BACKLOG `:52-57` deletion → A.U16.04 (DOCS); Part N rows for the attempts → A.U16.R02 (M.SPEC.156).
- **Kind**: doc

### M.SPEC.050 C.3.2: the UART driver contract
- **From**: A.U0.40 L52 (`:1613`), A.U12.03 (zero-length payload), A.U13.18 (concurrent `deinit()` seen at the next
  `ready()` exit), A.U17.13 (`discarded_bytes`), A.U17.28 (masked sequences), A.U36.544 (3) (changelog label B15 goes,
  `:1622`), A.U14.14 Blast (points to F.1), A.SDEP.08 (C3), M_DOCS gap 1 (c) (two of BACKLOG's four UART findings);
  OR141.a (4) (b), (c) (the receive side reads a DMA ring, never `machine.UART`'s receive calls), OR143.a (2) (the
  `readline_until_complete()` cap) (A-C review fold).
- **Site**: `SPECIFICATION.md:1607-1631` (C.3.2).
- **Change**: (1) `:1613` "Settled precedent: **one merged class**" → "Precedent (agent, 2026-08-08, `59d6b7b`): **one
  merged class**". (2) The cancel clause: "published through monotonic request/ack counters and bounded so the call is
  provably terminating. (It was an `asyncio.Event` handshake, which could both drop a request and hang the canceller
  forever; see `UART_C_PORT_CHANGELOG.md` B15.)" → "published through request/ack sequences masked to 2**30 − 1 and
  compared by distance, bounded so the call is provably terminating." (3) After the raise-contract clause: "A
  zero-length payload is transferred as nothing, in every CRC and codec mode; a concurrent `deinit()` is seen at the
  next `ready()` exit; `discarded_bytes` counts the bytes a failed `*_until_complete()` read consumed and dropped (masked
  to 2**30 − 1)." (4) "re-verified against `ports/rp2/machine_uart.c` at v1.29.0" and "(re-traced 2026-09-13 …)" stand as
  the dated facts at the pin in force (C3); the clause list points to F.1 for the raise surface. (5) M_DOCS gap 1 (c)
  (BACKLOG `:698-720`'s "four UART findings", which leave at U37): a closing paragraph "**Two out-of-contract calls**
  (agent, 2026-09-11): `UART.deinit()`/`init()` do not take the session lock — calling either while a read is in flight
  is out of contract, and no caller does (`init()` calls `deinit()` itself, so a lock check would change construction);
  `UARTComm.setup()` runs once per boot before any task starts — a second call while its listen loop runs would deadlock
  on the bus lock the loop holds, and the supervisor re-runs starters, never `setup()`." (the peer-sized allocation
  finding goes to J.8 and the shared-codec finding to G.2, M.SPEC.138, M.SPEC.111). (6) (A-C review fold) The HEAD
  sentences "**`any()` cannot raise either** (re-traced 2026-09-13, since every read in the driver now funnels through
  it): … a reachable rp2 case — worth its two lines precisely because it is the single choke point" → "**The receive side
  never calls `machine.UART`'s `any()`, `read()`, `readinto()` or poll** (owner, 2026-10-05): each link receives through
  a DMA channel paced by the UART's RX DREQ into a power-of-two ring held for the program's life, and every read copies
  its bytes from that ring by index (F.8.2); transmit stays on `machine.UART`, whose receive buffer is held at its
  minimum. The ring's fill level is the one choke point every read passes; reading `DMA.count` raises only on a
  closed channel (`ValueError`, `ports/rp2/rp2_dma.c:372-376, 390-392`, v1.29.0), so the choke point's catch guards
  that case and a future port." The raise-contract clause about framing, parity and overrun errors stands; a lap of the ring is the receive
  overrun J.7 names. (7) After (3)'s zero-length sentence (A-C review fold): "`readline_until_complete()` takes the same
  receive cap as a transfer and never grows by concatenation: a line over the cap is discarded, the call returns
  `None` and the case is logged (J.8)." — the cap's parameter named as landed (C7); since this layer keeps no logger of
  its own (C.7.1), which layer writes that entry is decided at execution, with its reason recorded.
- **Resolved**: A.U36.544 (3) drops changelog labels from permanent text; A.U17.28's rewrite of the same sentence makes
  the history parenthesis go with it (C2).
- **Unit**: Stage 1 U0 ((1)); Stage 2 U12/U13/U17 ((3), (2)); Stage 2b U13 ((6), (7), with the DMA receive path and
  the readline cap, their unit and twin fakes and tests); U36 (label, if still present; (5), before BACKLOG's entry
  leaves at U37).
- **Depends**: A.U12.03, A.U13.18, A.U17.13, A.U17.28, M.DOCS.065; M.SRC_NET.221 (the DMA receive path in
  `asy_uart_driver.py`), M.SRC_NET.202 (the `readline_until_complete()` cap).
- **Blast carried by**: UART changelog entries → A.U17.* (SCR/DOCS per UCL rule).
- **Kind**: doc

### M.SPEC.051 C.4 and C.4.1: the reader contract, the loop skeleton, the ladder hooks
- **From**: A.U11.37 (logging form, `:1635-1637`), A.U18.39 (mask-string PUT rule, "U36 places it" in C.4), A.U15.43
  (reader tasks return `None`), A.U15.40 (4) (heading), A.U10.44 (starter/coroutine names), A.U10.R01 (driver skeleton:
  recovery hooks), A.U3.03 dropped (OR140.a (7)), A.U3.06 (one entry per supervised task end — one event at one
  layer, kept), A.U3.11 narrowed (the mixed-kind scan C.7 names), A.U2.22 Blast (`:1656` "`errno=10`"), A.U5.06 Blast
  (C.4 has no `:259-262`; nothing) (A-C review fold: A.U3.03 stated no text here; (5) states the per-layer and
  mixed-kind rules, lead ruling).
- **Site**: `SPECIFICATION.md:1633-1667` (C.4, C.4.1).
- **Change**: (1) C.4 `:1635-1637` → "**Contract: never raises.** Every public method returns a sentinel on failure.
  Every layer-2 call is wrapped in its own `try/except Exception`, logged via `await self.pr.err_s("Message:", e,
  errno=_ERR_<NAME>)` — the logger prefixes its own name; a fixed message string, then the exception or values as
  separate arguments, never a pre-built or f-string, so a suppressed level allocates nothing." plus A.U18.39's rule as a
  second paragraph: "A PUT stores any value its schema accepts — a password equal to the mask string `********`
  included; a client that echoes the mask stores it, which is accepted (owner, 2026-09-29: 'I don't want to restrict it
  in any way')." (2) C.4.1 heading → "`read_loop()` skeleton (identical across the sensor drivers)"; skeleton `-> bool` →
  `-> None`, `return False` → `return`, with the loop's names as A.U10.44 lands them; "Returning `False` is the task
  supervisor's restart signal." → "Returning ends the task; the supervisor restarts it." (3) `_init_<sensor>()` sentence:
  "`try: await protocol.setup() except Exception: err_s(..., errno=10); return False`" → "a chip-setup failure persists
  the driver's init code (C.7's catalog), calls `await self._init_failed()` and returns `False`; success calls `await
  self._init_done()`"; new sentence (A.U10.R01): "An I2C driver sets `self._recovery_bus = i2c` and may override
  `_recover_device() -> bool` (never raises; persists its own failure) — the participant rung of the recovery ladder
  (C.7); only a chip failure calls `_init_failed()`." (4) "**A restart is not free.**" paragraph: "`system_service.py`'s
  `_TASK_FAIL_INCREMENT` (100) against a `_TASK_FAIL_MAX` of 300" → the landed constant names with their Part N IDs; the
  sentence "One bounded bus fault is one restart" gains "and one SYSTEM entry (one entry per supervised task end)". (5)
  (A-C review fold, lead ruling) After the skeleton: "A failed read persists the driver's read code and
  `_error_check()`'s streak entry — each layer that meets the fault keeps its own entry (owner, 2026-10-02) — and
  neither persists one occurrence as both an error and a warning (C.7, checked by its scan)."
- **Resolved**: A.U11.37's form and A.U2.04's `_ERR_<NAME>` idiom are one sentence (A.U11.37 Depends A.U2.04). A.U18.39
  says "U36 places it": C.4 is the Home its register names; placed in U18 with the code (the rule is current at U18),
  since nothing in U36 moves C.4 (agent decision).
- **Unit**: Stage 1 U2 (codes); Stage 2 U3 ((4) entry; (5), with C.7's paragraph and the narrowed scan); Stage 3 U10 ((2) names, (3) ladder hooks — A.U10.R01); Stage 4
  U11 ((1) form); Stage 5 U15 ((2) `None`, heading); U18 ((1) PUT rule).
  A-C2 step order: A.U2.22's part lands in U3, not U2 (it needs A.U2.02, which lands in U3); A.U10.R01's part lands in U13, not U10 (it follows A.U10.R01's own change, which lands in U13).
- **Depends**: A.U2.04, A.U3.06, A.U10.44, A.U10.R01, A.U11.37, A.U15.40, A.U15.43, A.U18.39, M.SPEC.156.
- **Blast carried by**: driver code → U15/U10 (SRC_SENS); G.2 ladder hooks → M.SPEC.111.
- **Kind**: doc

### M.SPEC.052 C.4.2: data access, narrowing, the one staleness rule
- **From**: A.U0.39 L53 (`:1679`), A.U15.02 (`:1681-1682`), A.U15.22 (5) (staleness rule), A.U11.S01 (superseded by
  M_SRC_CORE GAP-G13's per-kind validators), A.U10.06 (the `TS` capture; M_SRC_SENS GAP-15).
- **Site**: `SPECIFICATION.md:1669-1682` (C.4.2).
- **Change**: (1) `:1679` "the settled convention" → "the convention (owner, 2026-07-23, `eff19bf`)". (2) `:1681-1682` →
  A.U15.02's sentence ("A `struct.unpack()` result is narrowed by assigning it to an annotated local … no `src/` module
  calls `typing.cast()` or defines a `cast()` shim (owner, 2026-07-23)."). (3) After it, A.U15.22 (5)'s "**One staleness
  rule** (owner, 2026-09-12; owner, 2026-09-29): …" verbatim, with one clause added from M_SRC_SENS GAP-15: "a reading
  taken before the first NTP sync carries `TS` `None` and is a good reading: the reader's failure test looks only at the
  measurement fields (`condition=results[0] is None`, C.7)".
- **Resolved**: A.U11.S01's C.10 sentence ("a consumer … narrows it with `type()`/`isinstance()`") is replaced by GAP-G13's
  per-kind validators (M.SPEC.061).
- **Unit**: Stage 1 U0 ((1)); Stage 2 U15 ((2), (3)).
- **Depends**: A.U15.02, A.U15.22, A.U10.06, M.SRC_SENS.083/.089-.091.
- **Blast carried by**: `tests/test_asy_scd30_driver.py:454-457` comment → A.U15.22 (TEST_UNIT).
- **Kind**: doc

### M.SPEC.053 C.4.3 and C.4.4: the write path on `SensorReader`; no deferred construction
- **From**: A.U4.03 (write orchestration on `SensorReader`), A.U4.04 (SCD30 answers PUTs through the chip store), A.U15.12
  (SCD30 a `SensorReaderConfig` with a composite store), A.U5.06 (signals at construction; the deferred variant goes),
  A.U18.37 (`_cfg_overlay()`), A.U10.38 (names).
- **Site**: `SPECIFICATION.md:1684-1706` (C.4.3, C.4.4).
- **Change**: (1) C.4.3 first paragraph → "Pick by where config values live. The write orchestration (validate, stage,
  push, recover) lives on `SensorReader`, with the store behind two extension points (`_get_mgr_cfg()`/`_set_mgr_cfg()`);
  **`SensorReaderConfig`** adds the file-backed `ConfigManager` store. A driver whose values live partly in the chip uses a
  composite store: the SCD30 keeps six keys in its NVM, read back from the chip and written only when changed, and three
  in its file (`SensorReaderConfig`, A.4). A field with a live chip readback is read through `get_dict_cfg()`'s
  `callback`." (2) "**A `SensorReaderConfig` subclass whose field set isn't fixed at class-definition time …**" paragraph
  (`:1693-1698`) → "Every module's schema is fixed at construction: `NotificationService` takes its signals as
  constructor arguments, so no module completes itself after construction (no `register()`/`finalize()`)." (3) C.4.4:
  "(BMP3xx: 3 of 8 fields; SGP40: none; SCD30: all fields)" → "(BMP3XX: 3 of 8 fields; SGP40: none; SCD30: its six chip
  keys)"; "`asy_wifi_service.py`'s `callback= self._mask_pw` unconditionally overwrites the persisted `PW` with a fixed
  mask" → "`WifiService`'s `callback=self._cfg_overlay` shows what the radio uses: passwords masked, and a stored value
  the radio would refuse as the default it runs on (C.7.4)".
- **Resolved**: A.U4.03 (U4) states SCD30 cannot be a `SensorReaderConfig`; A.U15.12 (U15, later) makes it one with a
  composite store (M.SRC_SENS) — the end state is A.U15.12's; Stage 1 U4 writes the write-path move, Stage 2 U15 the
  SCD30 composite.
- **Unit**: Stage 1 U4 ((1) write path); Stage 2 U5 ((2)); Stage 3 U15 ((1) SCD30 composite, (3) SCD30 keys); U18 ((3)
  overlay).
- **Depends**: A.U4.03, A.U4.04, A.U5.06, A.U15.12, A.U18.37.
- **Blast carried by**: A.4 SCD30 bullets → M.SPEC.011; A.7 step 12 → M.SPEC.020.
- **Kind**: doc

### M.SPEC.054 C.5 and C.5.1: the schema, its special slot, scopes, validators and guards
- **From**: A.U0.17 (`:1711-1712` owner ruling), A.U15.17 Blast (special slot gains in-range meanings), A.U15.42
  (`FiltCoeff` two meanings), A.U36.538 (scope rule), A.U35.43 (3) (`:1722-1725`), A.U11.17 (no change), A.U11.29 +
  M_SRC_CORE GAP-G13 (typed getters; `checked_int()`/`checked_float()`/`checked_numeric()`, private coercion), A.U11.33
  (script guard; golden stored-config fixture), A.U20.12 (generated schemas linted), A.U3.05's caller half dropped
  (OR140.a (7): the caller keeps its own persisted entry; its `ConfigManager` half — the converter failure and the
  non-bool stored value persisted — stays), A.U11.21 (floats in stored form), A.U10.39 (`_cfg_schema` private), A.U10.29
  Blast (C.5 const pointer is U14's: the `const()`-wrapped-tuple sentence stays) (A-C review fold).
- **Site**: `SPECIFICATION.md:1708-1740` (C.5, C.5.1).
- **Change**: (1) `:1710-1711` → "`special` is a single sentinel value (an "unset" value outside the normal range, e.g.
  SCD30's `AmbPres=0` — deliberately outside it; the validation, not the schema, is what yields (owner,
  2026-07-15, `1ed1c9a`: 'Confirmed with the project owner which side was wrong (the validation, not the schema …)'))
  or an in-range value with a documented meaning (SGP40's `BackupPeriod`/`BackupMaxAge`/`WaitTimeNTP` 0); a field with
  `default=None` and a single-value `special` is "special-alone" …" (rest of the sentence as at HEAD). (2) After the
  schema paragraph (`:1717`), two paragraphs: A.U15.42's "**`FiltCoeff` keeps two meanings** (owner, 2026-09-26): …"
  verbatim, then A.U36.538's "**Every config value has one explicit scope** (owner, 2026-07-13, as recorded in
  `144873f`: …)" verbatim. (3) `:1722-1725` (three defensive catches, "don't remove them") → A.U35.43 (3): "Type
  mismatches are rejected statically: `ConfigManager` catches only the runtime failures of its file and heap operations
  (the REST layer rejects a non-object body before it reaches a module)." followed by: "A float is validated, cached,
  staged and compared in the form the file reloads as, so an identical PUT after a reboot answers "Unchanged". A failed
  config read is persisted by `ConfigManager` and by the caller that meets it, each in its own log, and the caller runs
  on its documented fallback (C.7; owner, 2026-10-02)." (4) The hazard paragraph (`:1727-1730`) gains: "A device script constructing a `ConfigManager` over a
  production file is checked to pass that module's full schema (`tests_scripts/`), and every device's stored config —
  each file and its keys' types — is pinned by a golden fixture from the release on: a change to it ships with a
  migration (owner, 2026-09-26)." (5) Typed accessors (`:1731-1734`) → "Four typed accessors — `get_int_values()`/
  `get_float_values()`/`get_str_values()`/`get_bool_values()` — return cache values checked by exact type (an `int` field
  read as `float` is accepted), all or nothing; a consumer that needs an `int` or a `float` from a free value calls the
  per-kind validator (`checked_int()`, `checked_float()`, `checked_numeric()`; `None` = refused), never a runtime cast."
  (6) New closing sentence: "Every `src/` and generated schema is linted: its annotation form, and unique field names
  across the schemas one `ConfigManager` or settings group serves." (7) C.5.1: "exposed via a plain sync
  `get_cfg_schema()` (no I/O, deliberately not `async`) and as a public attribute directly" → "exposed only through the
  plain sync `get_cfg_schema()` (no I/O, deliberately not `async`); the attribute is private (`_cfg_schema`)".
- **Resolved**: A.U15.17's Blast sentence and A.U0.17's insertion edit the same clause — one sentence carrying both
  (A.U15.17 "co-lands with A.U10.40/A.U10.42's C.5 edits"); A.U10.40/A.U10.42 touch C.5.3 only. A.U11.29's
  `coerce_numeric()` naming is superseded by GAP-G13 (C7).
- **Unit**: Stage 1 U0 ((1) owner insertion); Stage 2 U3 ((3) caller rule, stating the per-layer behaviour HEAD
  already has, with C.7's paragraph); Stage 3 U10 ((7)); Stage 4 U11 ((3) float,
  (4), (5)); Stage 5 U15 ((1) in-range meanings, (2) `FiltCoeff`); Stage 6 U20 ((6)); Stage 7 U35 ((3) first sentence);
  Stage 8 U36 ((2) scope rule).
- **Depends**: A.U0.17, A.U10.39, A.U11.21, A.U11.29, A.U11.33, A.U15.17, A.U15.42, A.U20.12, A.U35.43,
  A.U36.538, M.SRC_CORE.047.
- **Blast carried by**: BACKLOG `:478-480` → A.U15.42 (DOCS); H.5 special-value note → A.U15.17 (M.SPEC.117).
- **Kind**: doc

### M.SPEC.055 C.5.2, C.5.2.1, C.5.2.2: setter dispatch on `SensorReader`
- **From**: A.U4.03/A.U4.04 Blasts (`SensorReaderConfig`-only extension point; SCD30 hand-rolled setters; ContMeas
  instance), A.U4.01/A.U4.02 (compare-before-write named), A.U10.25 (setter-result and registration check), A.U11.24
  (holds), A.U11.25 (whole-operation failure narrows), A.U11.27 (PUTs per module serialised), A.U11.28 (stage first, then
  push; flush follows), A.S0930.16 (closed store; `delete_file()`), A.U2.07 (`:1753` numbers, M.SPEC.008), A.U11.19
  (command-only field creates no file), A.U10.40 (`SGPResetVOC` → `ResetVOC`, M.SPEC.008), A.U36.548 (G9/R11: "Since WP5"
  label).
- **Site**: `SPECIFICATION.md:1742-1786`.
- **Change**: (1) C.5.2 first sentence → "`_set_mgr_cfg(data, cfg_vals) -> (bool, WriteValidity)` is `SensorReader`'s
  store extension point (a file through `ConfigManager.write_config(...)`, or a chip, A.4's SCD30); every store write
  goes through `compare_before_write()` (G.2), so an unchanged value is "Unchanged" and spends no write.
  `_set_dict_cfg(data, cfg_vals) -> WriteValidity` validates and stages first, then pushes live only fields that both
  changed (`"Valid"`) and have a registered push callback, and the flash write follows the pushes; PUTs to one module run
  one at a time." "a whole-operation validation failure (an invalid `ConfigManager`, or an internal error raised out of
  `write_config()`/`_set_mgr_cfg()` itself, never a later flash-write failure - see below)" → "a whole-operation failure
  (an invalid manager or an internal error)". "**Since WP5** (SPECIFICATION.md Part F.2), the actual flash write is
  deferred to an independent task" → "The flash write is deferred to an independent task (F.2)". New sentence: "A closed
  store refuses writes; `delete_file()` removes the store's file for the config reset (A.8)." "Every setter's return
  contract is uniformly `bool`" gains "— every method registered in `_push_callbacks` (assigned only in `__init__`) and
  every `set_*` a settings group or dispatcher reaches, checked by a test". (2) C.5.2.1: `SGPResetVOC` → `ResetVOC`
  throughout (M.SPEC.008); "and a special-alone write always reports `"Valid"` … re-fires every request" gains "; it
  creates no file"; the closing "(SCD30's `ContMeas`, inverted, is the other instance)" goes (A.U4.04: SCD30's
  `ContMeas` is a chip key now). (3) C.5.2.2 unchanged except "`_set_mgr_cfg`" now reads as the store extension point
  above (the "Failed" sentence holds, A.U11.27).
- **Resolved**: (a) A.U0.33 C14 tags "persist first, then push, and every setter returns `bool`" as owner text of
  2026-09-26, but the owner's answer (OR69.a (4)) holds only the `res` semantics; the ordering is A.U11.28's mechanism
  (stage, push, then the flash write) — C.5.2 states A.U11.28's order and C.5.3 keeps only the owner's `res` sentence
  (adherence finding; agent decision). (b) A.U4.03's "SCD30 cannot become a `SensorReaderConfig`" is overtaken by A.U15.12
  (M.SPEC.053).
- **Unit**: Stage 1 U4 ((1) extension point, compare-before-write); Stage 2 U11 ((1) failure narrowing, serialised PUTs,
  order, (2) no file); Stage 3 S0930 ((1) closed store); U10/U2 renames (M.SPEC.008); U36 ("Since WP5" if not already
  gone).
  A-C2: "S0930" is not a unit; its parts land in the units SUPP_owner_0930 states: A.S0930.16 in U11.
- **Depends**: A.U4.01-.04, A.U10.25, A.U11.19, A.U11.24-.28, A.S0930.16, M.SPEC.008, M.SPEC.111.
- **Blast carried by**: `tests/test_base_classes.py` section comment → A.U4.03 (TEST_UNIT).
- **Kind**: doc

### M.SPEC.056 C.5.3: the one envelope catalog and the `res` rule
- **From**: A.U19.15 (catalog table and rule), A.U11.26 (codes 4/5/100 go; hook failure is per field), A.U27.07 (2/3 go
  with `parse_cmd_request()`), M.SRC_CORE.073 (end-state catalog), A.U32.03 (one hook per endpoint, its reason), A.U0.33
  C14 (`res` rule), A.U10.42 (`:1801-1805`), A.U1.18 (`:1801` repath — void, sentence deleted), A.U0.38 V17 (`:1801`
  nothing further), A.U2.18 (errno 99 row goes), A.U10.40 (keys), A.U36.542 (no edit).
- **Site**: `SPECIFICATION.md:1788-1806` (C.5.3).
- **Change**: (1) First paragraph → "Wire shape: `{"res": "OK"|"ERR", "code": int, "descr": str, "result": ...}`.
  `make_response(code, descr=None, result=None)` draws from **one envelope code catalog**, every code with a producer:
  [a Markdown table: `0` Command executed, `1` Invalid JSON request, `400` Bad request, `404` Not found, `405` Method not
  allowed, `413` Payload too large, `500` Internal server error]; a shaped HTTP error uses its status as its code.
  `handle_set_cmd(reader, data, cfg_vals, post_fct=None, post_asy_fct=None)` orchestrates
  `_set_dict_cfg()` plus one optional post-write hook (fires once per call, only if a field actually changed — one hook
  per endpoint, not one per field, as legacy's `post_fct`/`post_asy_fct` (agent, 2026-08-03)) and returns the per-field
  result (`WriteValidity`), not an envelope; a hook's failure reports its group's fields "Failed", and the endpoint's OK
  envelope carries the result. Build `data` from only the keys the client sent. A per-field
  failure never demotes the overall response below `"OK"`/`0` — detail lives in `"result"`: `res` is `"OK"` when the
  request itself was processed; a non-`OK` `res` means the request was broken (unparseable, wrong shape, unknown
  endpoint), never invalid or failed content (owner, 2026-09-26: 'res not "OK" means that the request itself was broken,
  not invalid content')." (2)
  `:1799-1801`: "Only legacy `html_raw/` isn't updated (H.1)." goes (A.U10.42). (3) `:1802-1805` → A.U10.42's sentence
  ("`WifiService` owns one schema, but `/networking`'s settings groups each carry only their own subset
  (`SettingsGroup(conn, (…))`, generated), so a LED-only change never fires `reconnect_wifi()`").
- **Resolved**: (a) A.U19.15 and A.U11.26 edit the same catalog sentence ("one edit"), A.U27.07 removes 2/3 —
  end state is M.SRC_CORE.073's seven codes. (b) A.U1.18 repaths `:1801` in U1 and A.U10.42 deletes it in U10: A.U1.18's
  `:1801` edit is dropped (one landing that a later unit deletes; the legacy-path fact lives in H.1). (c) A.U0.33 C14's
  "persist first, then push, and every setter returns `bool`" is not carried here (M.SPEC.055 (a)). (d) Gap pass G2
  (M.SRC_CORE.070/.072, GAPS_G2 H-5 (a)): `handle_set_cmd()` loses `ok_descr` and returns the per-field result, so its
  one caller needs no runtime narrowing; the sentence follows (gap pass G1).
- **Unit**: Stage 1 U0 ((1) `res` rule); Stage 2 U10 ((2), (3)); Stage 3 U11/U19 ((1) catalog without 4/5/100, hook
  sentence, with 2/3 while `parse_cmd_request()` exists); Stage 4 U27 ((1) without 2/3); U32 ((1) hook reason).
- **Depends**: A.U10.42, A.U11.26, A.U19.15, A.U27.07, A.U32.03, M.SRC_CORE.072, M.SRC_CORE.073.
- **Blast carried by**: `api_response.py` comments → A.U32.03/A.U19.15 (SRC_CORE); A.8 envelope line → M.SPEC.021.
- **Kind**: doc

### M.SPEC.057 C.6: `make_dict()` reads fields by `getattr()`, one nested shape
- **From**: A.U11.35 (C.6 and `:5687-5688`), A.U10.36 (one config-dict shape), A.U0.40 (L55 label; folded).
- **Site**: `SPECIFICATION.md:1808-1814` (C.6); `:5687-5688` (J, carried in M.SPEC.139).
- **Change**: C.6 → A.U11.35's paragraph verbatim, plus "Every module's config dict has the same nested shape `{<name>:
  {field: value}}`; no module returns a flat one."
- **Resolved**: — (no conflict among the constituents)
- **Unit**: Stage 1 U10 (shape sentence); Stage 2 U11 (paragraph).
- **Depends**: A.U10.36, A.U11.34, A.U11.35.
- **Blast carried by**: `:5687-5688` → M.SPEC.139.
- **Kind**: doc

### M.SPEC.058 C.7: the error-handling and logging contract
- **From**: A.U5.01 (`LogConfig`, `make_logger(log, name)`), A.U16.01 (`:1818-1821` reflash pitfall), A.U26.22 (save,
  then clear; "SPEC C.7 is U36's"), A.U10.10 (every logger store set up in the boot batch), A.U10.11 (pre-setup entries
  survive setup), A.U16.17 (a declared FRAM chip that fails setup escalates), A.U16.06 (unreadable vs invalid chunk),
  A.U11.16 (allocation failure degrades to RAM-only), A.U11.31 + A.U19.14 (`ResetErrors` measurements dated; BACKLOG item
  32; its U33 repoint, M_DOCS gap 1 (b)), A.U2.14 (`W5, W4, W4` numbers, M.SPEC.008), A.U11.13 (an invalid level is refused), A.U11.15 (no level accessors;
  the `pr.level` attribute), A.U2.22 (numbering rules), A.U3.10 (one occurrence, error or warning; its detecting-layer
  clause dropped, OR140.a (7)), A.U2.04 + A.U11.37
  (idiom), A.U2.06 + A.U2.08 (`_error_check()` bullet; no dynamic numbering), A.U3.03 dropped (OR140.a (7)), A.U10.R01
  (the recovery ladder), M_SRC_SENS GAP-15 (pre-sync `TS` excluded), A.U0.19 H1.02
  (`:1894-1897` DNSSRV), A.U18.36 (WIFI observation sites), A.U18.15 (UDP users check `disconnect()`), A.U18.09
  (resolver bounds), A.U13.16 + A.U10.22 (teardown returns `bool`), A.U30.19 + M_SRC_CORE GAP-G8 (`report_if_fatal()`
  in `asy_print_log`), A.U3.11 narrowed (lead ruling on OR140.a (7): the scan checks only the mixed-kind rule — an error
  and a warning for one occurrence in one log — its allow-list keeping only reasons that still hold),
  A.U35.37 (normal situations log nothing), A.U6.26 (no C.7 text), A.U14.19 (nothing); OR140.a (7) (every layer that
  meets a fault keeps its own persisted entry, as today) (A-C review fold).
- **Site**: `SPECIFICATION.md:1816-1900` (C.7).
- **Change**: (1) First paragraph → "`self.pr` is `PrintLogHistory` (in-memory) or `PrintLogHistoryStore` (FRAM-backed),
  chosen from the module's `log: LogConfig` (`fram`, `history_length`, `debug`); `make_logger(log, name)` is the same
  branch for a module that is not a `SensorReader` (`SystemService`). **Known pitfall**: a FRAM-backed history survives
  every reboot; after a reflash it survives only where the new build happens to keep the same chunk, and otherwise reads
  as invalid and restarts empty (A.4). A persisted entry is therefore no proof that it came from *this* run: read and
  save the log first (the one save primitive, `tests_hardware/`; CLAUDE.md's FRAM rule), then clear it (`PUT /status
  {"ResetErrors": true}`). Every logger store is set up in the boot batch, first in its module's setup (A.7); entries
  logged before `setup()` are kept and merged after the stored ones. A FRAM chip declared in the device TOML that fails
  `setup()` escalates like any declared chip (owner, 2026-09-29: 'the same as all other chips'): one supervised task that
  ends at once, so the supervisor reboots past its budget; modules log in RAM until then. Where no chip is declared,
  every module runs RAM-only (owner, 2026-08-11). A chunk that cannot be read is left untouched and its owner logs in RAM
  until the next boot; only a chunk proven blank or invalid is re-initialised. A FRAM chunk operation fails only by
  allocation, which degrades that logger to RAM-only logging." (2) The `reset()` paragraph keeps its rule ("**`reset()`
  writes unconditionally; `_store_err()` does not.** … `setup()` still runs normally.") and "Without this, a
  `ResetErrors` landing in the boot window was silently undone: … Fixed 2026-09-11; covered at the mock, twin and flash
  tiers." → "A reset issued before a logger's `setup()` clears the chip too, and that `setup()` then restores the cleared
  ring, so a clear is all-or-nothing across modules (covered at the mock, twin and flash tiers)." (3) "**A `ResetErrors`
  answering `OK` …**" paragraph unchanged (owner, 2026-09-17), except "answering `OK`" → "answering `Valid`" where
  A.U11.31 makes the reply per field. (4) "**Confirmed on real hardware (dev bench board, 2026-09-17).**" keeps its three
  measured bullets, dated as taken before the concurrent reset (A.U11.31); "`W5, W4, W4`" → the catalog codes
  (M.SPEC.008); "Timings and the remaining load-case concern: BACKLOG.md item 24." → "…: BACKLOG.md item 32" at U19
  (A.U19.14), and at U33, when A.U33.09 dissolves item 32 into an owed row, → "…: BACKLOG.md's owed row 'bench
  `ResetErrors` budget'" (M_DOCS gap 1 (b), M.DOCS.063); "All 21 of `dev`'s chunks" stays a dated measurement. (5) Log-level paragraph gains "an invalid level is refused, never clamped;
  the print methods read the logger's `level` attribute". (6) Numbering paragraph (`:1875-1883`) → A.U2.22's rules
  ("codes are integers 1-127 (warnings stored with a `0x80` offset, 0 = nothing to record); one global catalog
  (`buildgen/error_catalog.json`); … the catalog test (`tests_scripts/test_error_catalog.py`) enforces all of it") and,
  as its last sentence, the idiom "codes are `_ERR_<NAME>`/`_WRN_<NAME>` `const()`s passed by keyword". (7) New paragraph
  after it (A.U3.10's, its detecting-layer clause replaced by the owner's ruling, A-C review fold): "**Every layer that
  meets a fault keeps its own persisted entry** (owner, 2026-10-02: a layer reacting to a fault below it may meet
  following errors beyond the original one, so the history shows how far the fault reached — a trace of it); entries of
  one kind from several layers, and a layer's reaction to a fault (a give-up, a task end, a drain bound), are allowed.
  **In one log, one occurrence is never persisted as both an error and a warning** (owner, 2026-09-26: 'Either it's a
  fault or a warning, but never both at a time. That is common sense and should be globally checked and applied.'): an
  L0 scan over `src/` and the generated modules flags an `err_s` and a `wrn_s` persisted for the same occurrence in one
  function, its allow-list naming each remaining pair with a reason that still holds (`tests_scripts/`, the file as
  landed). An expected condition prints only: a normal situation never logs a code, and a
  test of one asserts no entry (owner, 2026-09-12, `8a45060`: 'no error/warning should ever be logged for expected
  startup jitter on any boot, on any module'). A failed config read is persisted by `ConfigManager` and by the caller
  that meets it (C.5)." (8) `_error_check()` paragraph (`:1885-1890`) → "`_error_check(results,
  condition=True) -> bool` is the shared consecutive-failure counter every `read_loop()` calls once per cycle — `False`
  (give up, restart) once the streak exceeds `max_module_error`; it decrements on a good read and the count shows in the
  driver's `ErrCount`; a failed cycle persists the streak's entry beside the driver's own read code, and the give-up
  persists its own. Between the retry and the give-up it climbs
  the recovery ladder once per episode: [A.U10.R01's sentence verbatim, "(owner, 2026-09-30: smallest blast radius
  first; thresholds agent, 2026-09-30; F.2)"]. `condition` lets a driver exclude a cycle that is not a sensor failure
  (SGP40's `condition=compensated`; every reader passes `condition=results[0] is None`, so a pre-sync `TS` of `None`
  counts as a good read). **A call site with just one pass/fail flag** passes a fixed one-element sentinel …" (rest
  holds); the "dynamically" sentence (`:1882-1883`) goes (A.U2.08). (9) `:1891-1897` → A.U0.19 H1.02's sentence
  ("**An owned helper with no registered task/timer starter of its own may still own an independent, uniquely-named
  logger** (agent, 2026-08-07, generalising the one case the owner decided): `asy_captive_dns.py`'s `CaptiveDNS` (owned by
  `WifiService`) gets its own `"DNSSRV"` logger (owner, 2026-08-07, `74cfa7f`) so its history can be shown with the
  networking data (owner, 2026-09-26)"). (10) The teardown sentence → "**A teardown/cleanup method on a class with no
  logger of its own returns `bool`**, so its caller can log the failure — `UDPSocket.disconnect()` (every user checks it
  and persists a failure), `WebserverService._close_writer()`, `UART.deinit()`, `I2C.deinit()`, `SPI.deinit()` (C.13)."
  (11) New closing paragraphs: "**Every broad handler first calls `report_if_fatal()`** (`asy_print_log.py`): a C-stack
  overflow is recorded by the handler that catches it and the supervisor reboots (reset code 20, F.1)." and the WIFI
  observation rule (A.U18.36, agent, 2026-09-30): "`WifiService`'s radio observations (`status()`, `isconnected()`,
  `ifconfig()`, the stations query, the LED helpers) stay print-only as routine observations; the persisted ones are the
  connect-attempt tier and the timer arms. The resolver resolves only names RFC 1035 can encode (no empty label, at most
  255 octets); anything else resolves to `None`."
- **Resolved**: (a) A.U26.22 says "SPEC C.7 is U36's" and A.U16.01 (U16) rewrites the same sentence: Stage U16 lands
  A.U16.01's "read and save the log first … then clear" and U36 adds "the one save primitive" pointer once A.U26.22's
  primitive exists — one sentence. (b) A.U3.10 places "one event, one entry" in C.7 and A.U35.37's rule (G5/R21) is the
  same family — one paragraph (agent decision). (b.1) OR140.a (7) (owner, 2026-10-02) drops the detecting-layer rule
  ("one entry per fault"): the paragraph states the per-layer rule; the owner's literal 2026-09-26 rule (one occurrence
  never both an error and a warning in one log, globally checked) stays with A.U3.11's scan narrowed to it, and with
  A.U3.06/A.U3.08; A.U3.03/.04/.05 (caller half)/.07/.09 are dropped (lead ruling, A-C review fold). (c) A.U2.22 removes the per-module dynamic `wrnno` text that A.U2.08 also
  removes — one deletion. (d) The boot-window history (`:1840-1846`) contradicts A.U10.10's end state (every store set up
  before the server answers) — replaced by A.U25.65's statement of the end-state behaviour (agent decision).
- **Unit**: Stage 1 U0 ((9)); Stage 2 U2 ((6), numbers); Stage 3 U3 ((7) first half; (8)'s failed-cycle clause states
  HEAD's per-layer behaviour); Stage 4 U5
  ((1) `LogConfig`); Stage 5 U10 ((1) boot batch/pre-setup, (8) ladder, (10)); Stage 6 U11 ((1) degrade, (3), (4), (5));
  Stage 7 U16 ((1) pitfall, FRAM escalation, unreadable chunk); Stage 8 U18 ((10) UDP, (11) WIFI/resolver); Stage 9 U30
  ((11) `report_if_fatal()`); Stage 10 U35/U36 ((7) normal situations, (1) save primitive).
  A-C2 step order: A.U2.14's part lands in U3, not U2 (it follows A.U2.14's own change, which lands in U3); A.U2.22's part lands in U3, not U2 (it needs A.U2.02, which lands in U3); A.U10.R01's part lands in U13, not U10 (it follows A.U10.R01's own change, which lands in U13).
- **Depends**: A.U2.22, A.U3.10 (its kept half), A.U3.11 (narrowed), A.U5.01, A.U10.10, A.U10.11, A.U10.R01, A.U11.13, A.U11.16,
  A.U11.31, A.U13.16, A.U16.01, A.U16.06, A.U16.17, A.U18.09, A.U18.15, A.U18.36, A.U19.14, A.U26.22, A.U30.19,
  A.U35.37, M.SRC_CORE.034, M.SRC_SENS.083; the narrowed mixed-kind scan (M_TSC, as the fold amends A.U3.11's carrier).
- **Blast carried by**: CLAUDE.md FRAM rule → A.U26.22/A.U2.08 (DOCS); `digital_twin/README.md:503-507` → A.U25.65 (TWIN).
- **Kind**: doc

### M.SPEC.059 C.7.1: the band table and the catalog
- **From**: A.U2.22 (C.7.1 → band table + catalog pointer), A.U3.10 (repeat rule → the central rule), A.U2.01/A.U2.02
  Blasts (catalog file, catalog test), A.U0.40 L56 (`:1948`), A.U0.38 V48 (`:1949`), A.U3.08 (UART W10 console, W11 drain
  bound), A.U16.R03 (errno 54 row), A.U15.24 (W11 shared row), A.U18.06/A.U18.14/A.U2.09/A.U2.15/A.U2.19/A.U2.20/
  A.U9.08/A.U16.15 (row texts — generated from the catalog, nothing hand-written), A.U36.544 item 29 (WIFI reason
  sentence), A.U18.36 (wrnno 36 text); A.U3.09 dropped (OR140.a (7); its row texts are the catalog's either way) (A-C
  review fold).
- **Site**: `SPECIFICATION.md:1902-1950` (C.7.1).
- **Change**: (1) Intro and repeat paragraph → A.U3.10's central rule: "**Repeats.** A history is a ring of ten slots
  per logger with one shared saturating counter, codes only (errors and warnings share it; the `0x80` offset makes the
  two kinds different codes); a code identical to the newest entry is counted and written through but spends no slot —
  'just don't repeat the same error in the slots. Pure and simple' (owner, 2026-09-26). The console is unfiltered; RAM and
  FRAM histories follow the same rule; there is no per-module episode state; alternating codes and reboots are outside
  the rule." (2) The table → A.U2.22's band table (base 1-9/1-2; the shared band;
  each owner's band) with "(owner, 2026-09-25)" and a pointer: "every code, its owner, name and meaning:
  `buildgen/error_catalog.json`; `tests_scripts/test_error_catalog.py` checks every logging call against it". The
  per-module rows, "Seven modules still number inside the reserved range" and "renumbered to 10+ on its next substantial
  change" go. Kept as statements beside the table: "The FRAM manager's chunks log into the manager's RAM-only history:
  the FRAM module never has FRAM logging of its own: a FRAM fault logged into that same FRAM is
  lost with it."; the UART decision "**`wrnno` W11 outranks W10** (owner,
  2026-09-18): a resync prints; the drain bound persists W11, so 'the peer never stopped sending' is what a field log
  carries"; the WIFI authentication code reads "authentication or handshake failed": cyw43 reports any failed AUTH event
  or key exchange as BADAUTH (`lib/cyw43-driver/src/cyw43_ctrl.c`), not proof of a wrong password; the no-logging layers
  "(owner, 2026-08-20, `c80d293`: no logging in these layers)" — the bus drivers, `asy_udp_socket.py`,
  `asy_dns_client.py`, `asy_uart_driver.py` (whose `cancel_unacknowledged` its owner reads and logs).
- **Resolved**: A.U0.40 L56 and A.U0.38 V48 tag rows that A.U2.22 deletes (U2, later): their tags survive in the kept
  statements (C8). A.U3.08's W10/W11 restatement replaces A.U2.22's quoted "W11 outranks W10 … persisted when the drain
  bound is hit". Catalog numbers in the statements are the catalog's (M.SPEC.008).
- **Unit**: Stage 1 U0 (tags on HEAD rows); Stage 2 U2 ((2)); Stage 3 U3 ((1), UART statement).
  A-C2 step order: A.U2.02's part lands in U3, not U2 (it follows A.U2.02's own change, which lands in U3); A.U2.15's part lands in U3, not U2 (it follows A.U2.15's own change, which lands in U3); A.U2.22's part lands in U3, not U2 (it needs A.U2.02, which lands in U3).
- **Depends**: A.U2.01, A.U2.02, A.U2.22, A.U3.08, A.U3.10.
- **Blast carried by**: per-row codes → the catalog file (GEN/A.U2.01); C.11 item 8, K.1, K.9 → M.SPEC.069, M.SPEC.140/.142.
- **Kind**: doc

### M.SPEC.060 C.7.2: which failures end a task; the network recovery ladder
- **From**: A.U18.47 (NET ladder paragraph), A.U18.19 (NTP source/origin decision), A.U18.20 (`Synced` goes stale), A.U18.21
  (a settings change clears `Synced`), A.U18.10 (`DNSFallback`, resolver order), A.U18.14 (both local codes), A.U5.10
  (`retry_s`/`retry_max_s` wording after grouping), A.U8.09 (Part N), A.U2.15 (`E21` → catalog), A.U0.38 V51 (`:1976`),
  A.U17.07 (UART link that never came up ends its task), A.U17.21 + A.U17.32 + A.S0930.01 (build refusals), A.U2.20
  (UART numbers), A.U36.548 (G9/R11 history).
- **Site**: `SPECIFICATION.md:1952-1984` (C.7.2).
- **Change**: (1) First paragraph keeps the rule; "the NTP task used to end after six failed syncs, so an unreachable
  server restarted it about once a minute and rebooted the device about every four minutes (owner, 2026-09-24). The
  legacy client never gave up." → "(owner, 2026-09-24: an NTP task that gave up after six failed syncs rebooted a device
  every few minutes; the legacy client never gave up)". (2) NTP bullet: "`retry_s` (default 10 s) doubling … `retry_max_s`
  (default 600 s)" with the parameter names as A.U5.10 groups them and their Part N IDs; "**Confirmed on silicon
  (2026-09-25)**: with UDP 123 blocked, one `E21` slot (count 3) …" → the catalog code; new sentences: "The resolver asks
  the DHCP-provided DNS server first, then the `DNSFallback` servers (an NTP config value, at most three, emptiable at
  the API). `Synced` is true only while the last success is less than three intervals old; a failed resync does not
  extend it, and a PUT of an NTP setting clears it until the next successful sync (owner, 2026-09-29). A request that
  could not be sent and a reply that never came are two local codes (`NTP_NOT_SENT`, `NTP_NO_REPLY`)." and A.U18.19's
  paragraph: "**No origin check** (agent, 2026-09-30): a reply is accepted only from the resolved server's address and
  port, because the fetch socket is connected and lwIP's `udp_input()` gives a connected pcb only that remote's datagrams;
  each attempt uses a fresh socket, so a late reply to an earlier attempt reaches none; an on-path host forging the
  server's address is outside the trusted-LAN model (A.11)." with its file:line sources re-read at the refreshed pin
  (C3). (3) After the bullets, A.U18.47's paragraph verbatim ("Network faults recover with the smallest step first. …
  (owner, 2026-09-26) (owner, 2026-09-30)."). (4) "**Out of scope (owner, 2026-09-24): hardware that is inoperational from
  the start.**" → "… hardware that is inoperational from the start, or a chip that stalls (owner, 2026-09-25: 'a stalled
  chip may recover by a reboot').**"; "and neither is a UART link whose `setup()` refused its construction" → "and
  neither is a UART link whose `setup()` failed: it ends its task on both roles, and the supervisor's restart escalation
  is its path to a reboot". (5) The build-refusal sentence → "The refusals a device TOML can cause are build errors
  instead (`buildgen/validate.py`, reading the thresholds out of `asy_uart_comm.py`): a reply timeout below 2 ×
  `poll_wait_ms` + `poll_idle_ms` + the GC pause, or above the ticks horizon its drain bound needs; a `poll_wait_ms`
  outside 1 … 9 ms; an `rxbuf` below one frame or one poll's arrivals; a crossover pair whose baud rates or CRC modes
  differ; every other refusal needs code the generator never emits." (codes by catalog name, not number).
- **Resolved**: A.U17.07 asks U10's C.7.2 edit to merge "a UART link whose `setup()` failed ends its task on both roles"
  beside the stalled chip — one sentence with A.U0.38 V51. A.U18.47's double tag is the constituent's own.
- **Unit**: Stage 1 U0 ((4) V51); Stage 2 U2 (codes); Stage 3 U5/U8 ((2) names, Part N); Stage 4 U17 ((4) UART, (5)
  poll/timeout/baud); Stage 5 U18 ((2) resolver/`Synced`/codes/origin, (3)); S0930 ((5) CRC mode); U36 ((1)).
  A-C2 step order: A.U2.15's part lands in U3, not U2 (it follows A.U2.15's own change, which lands in U3).
  A-C2: "S0930" is not a unit; its parts land in the units SUPP_owner_0930 states: A.S0930.01 in U20.
- **Depends**: A.U17.07, A.U17.21, A.U17.32, A.S0930.01, A.U18.10, A.U18.14, A.U18.19-.21, A.U18.47, A.U5.10, M.SPEC.024.
- **Blast carried by**: DEVICE_REFERENCE `NtpSynced` → A.U18.20/.21 (DOCS); L.3/L.4 lists → M.SPEC.146/[L.4].
- **Kind**: doc

### M.SPEC.061 C.7.3: a failed config write costs persistence, never the config
- **From**: A.U11.20 (an unreadable file is never written that boot), A.U11.19 (a missing file is served from defaults
  and written by the first accepted change — superseded on that point by OR136.a (1)), A.U11.28 (write-count sentence),
  A.U11.21 (stored form, C.5), A.S0930.16 (closed store), A.U2.07 (numbers), A.U0.37 V52 (`:1994` tag), A.U36.034
  (CLAUDE.md points here), A.C.17 (power-loss result, phase C), A.U36.548 (G9/R11); OR136.a (1)-(4) (an absent file is
  written once with its defaults), OR138.a (1)-(2) (`ConfigFaults`; the reset deletes every file unread) (A-C review
  fold).
- **Site**: `SPECIFICATION.md:1986-2011` (C.7.3).
- **Change**: (1) First paragraph: "`setup()` runs on the file's good keys and the defaults for the rest when its
  create-or-repair write fails (errno 4)" → by catalog name; new sentences: "A config file that is genuinely absent (its
  open fails with ENOENT: after a fresh flash, a filesystem erase or "Reset to defaults") is written once, at that
  boot, with the schema defaults, through the same compare-before-write path as every other write, so every module's
  file exists after the first boot (owner, 2026-10-01). A command-only schema persists no field and has no file to
  write; its absence stays a printed note. A file that exists but cannot be read (an I/O error, `MemoryError`) or is
  corrupt is served from defaults and never overwritten (owner, 2026-09-26); a readable file with a bad, missing or
  unknown key gets at most one repair write per boot (owner, 2026-09-26). A module whose file existed at this boot but
  could not be read or was damaged (unparseable or invalid) is listed in `/status` `ConfigFaults` for the rest of the
  boot, even after the boot repair rewrote its file, and keeps its persisted warning, once per boot (A.8; owner,
  2026-10-01)." "Before this, a failed setup write left the manager
  invalid: … (owner, 2026-09-24)." → "Were a failed setup write to leave the manager invalid, every reader's init would
  fail, the supervisor would reboot and every boot would repeat the write — a reboot loop writing the flash each pass
  (owner, 2026-09-24)." (2) Write-site list: "`setup()` writes at most once, only when the file is missing or needs
  repair" → "`setup()` writes at most once per boot: the defaults when the file is absent, or the one repair of an
  existing, readable file"; "`_flush_staged()` writes once per accepted PUT that changes a value" → "once per accepted
  PUT that changes a value, after its pushes; a flush equal to the file writes nothing"; new third item: "the store's
  delete for "Reset to defaults" removes the file without reading it, whatever its readable state (owner, 2026-10-01);
  it runs in the shutdown sequence after the command was answered, so a delete that fails is logged and reads as reset
  reason 9 at the next boot (A.8)". (3) "**Bounded by boots …**" paragraph:
  "(owner, 2026-09-24)" → A.U0.37 V52's "(owner, 2026-09-24; the bound — each write once per explicit change or once per
  boot — confirmed by the owner, 2026-09-26)" at `:1994`. (4) Phase C (A.C.17): the power-loss result is recorded in
  F.2's sentence, which this section cites ("A power cut during a write leaves a loadable file: F.2.").
- **Resolved**: A.U11.19 and A.U11.20 contradict HEAD's "missing" case of `setup()`; A.U11.19's end state (no write for
  a missing file) is itself superseded by OR136.a (1) (owner, 2026-10-01: "if the file is genuinely missing, it shall be
  written once with defaults"), which narrows HEAD's case to ENOENT — an unreadable file is never treated as missing
  (A.U11.20). OR138.a adds the fault list and the unread delete (A-C review fold).
- **Unit**: Stage 1 U0 ((3)); Stage 2 U2 (codes); Stage 3 U11 ((1) without its `ConfigFaults` clause, (2) without its
  third item — the absent-file write, the unreadable-file rule and the fault state land in U11, M.SRC_CORE.043/.047);
  Stage 4 U20 ((1)'s `ConfigFaults` clause and (2)'s delete item, with the generated `/status` block and the
  system-command delete path); phase C ((4) pointer once F.2 has the result).
- **Depends**: A.U11.19, A.U11.20, A.U11.28, A.C.17, M.SPEC.096; M.SRC_CORE.043/.047 (as the fold amends them);
  M.GEN.008, M.GEN.014 (`ConfigFaults` in `/status`), M.SRC_CORE.042, M.SRC_CORE.011 (the unread delete; a failed one logged, reset reason 9).
- **Blast carried by**: CLAUDE.md flash-write rule → A.U36.034 (DOCS, M.DOCS.082, as the fold amends it); CLAUDE.md
  wear rule's fresh-filesystem prerequisite → M.DOCS.086; A.8's `ConfigFaults` and reset text → M.SPEC.021; A.7's
  setup-batch sentence → M.SPEC.020.
- **Kind**: doc

### M.SPEC.062 C.7.4: the radio's string bounds and shapes
- **From**: A.U14.37 (first sentence: raise types, cyw43 citations), A.U6.29 (host-label rule), A.U6.30 (country shape),
  A.U18.37 (GET shows the radio value in use), A.U18.38 (no change), A.U3.07 dropped (lead ruling on OR140.a (7); its
  `errno 17` clause is gone from (4) anyway, A-C review fold), A.U2.14 (codes),
  A.U26.20 (test only), A.U6.28 Blast (H.5 cross-reference, M.SPEC.117), A.C.14 (unknown country code on silicon,
  phase C).
- **Site**: `SPECIFICATION.md:2013-2027` (C.7.4).
- **Change**: (1) First sentence → A.U14.37's text verbatim (re-read at the refreshed pin and cyw43 commit, C3). (2)
  "`asy_wifi_service.py` now bounds SSID, PW, Country, Hostname and HotspotPW in bytes at both ends" → "`WifiService`
  bounds SSID, PW, Country, Hostname and HotspotPW in bytes at both ends, and checks two shapes: `Hostname` is a host
  label — ASCII letters, digits and `-`, not starting or ending with `-` (RFC 1123), at PUT, use and build; `Country` is
  two uppercase letters (ISO 3166-1 alpha-2) at PUT and use (agent, 2026-09-28)"; codes by catalog name. (3) New
  sentence: "`GET /networking` shows the value the radio uses: passwords masked, and a stored value the radio would refuse
  as the default it runs on." (4) "So a schema-valid `"ÄT"` … used to raise on every connect, set `hw_op_failed` and end
  the task after `max_module_error` cycles (errno 17) — a config value treated as a hardware fault (C.7.2)." → "Unchecked,
  a schema-valid `"ÄT"` or a 32-character SSID with umlauts would raise on every connect and end the task as a hardware
  fault (C.7.2)." (5) Phase C (A.C.14): one dated sentence on what the radio does with a well-shaped but unknown country
  code.
- **Resolved**: — (no conflict among the constituents)
- **Unit**: Stage 1 U2 (codes); Stage 2 U6 ((2) shapes); Stage 3 U14 ((1)); Stage 4 U18 ((3)); U36 ((4)); phase C ((5)).
- **Depends**: A.U6.29, A.U6.30, A.U14.37, A.U18.37, A.C.14.
- **Blast carried by**: H.5 FieldDef `shape`/`bytes` → M.SPEC.117.
- **Kind**: doc

### M.SPEC.063 New C.7.5: the captive DNS answers
- **From**: A.U18.01 (creates the section; QTYPE rule, owner 2026-09-29), A.U18.02 (drop rule).
- **Site**: new `### C.7.5 Captive DNS` after C.7.4 (`:2027`), before C.8.
- **Change**: "`asy_captive_dns.py` answers every on-subnet A/ANY query with the AP's IP and every other type with an
  empty NOERROR reply (owner, 2026-09-29). A datagram that is a response (QR), declares other than one question, uses a
  compressed or reserved label or a name over 255 octets is dropped (agent, 2026-09-28); a reply is at most 287 B."
- **Resolved**: — (no conflict among the constituents)
- **Unit**: U18.
- **Depends**: A.U18.01, A.U18.02.
- **Blast carried by**: A.5 `:331` → M.SPEC.018; `THIRD_PARTY_LICENSES.md:145-148` → A.U18.01/.02 (DOCS); I.4 → M.SPEC.126.
- **Kind**: doc

### M.SPEC.064 C.8: locks, the lock table, the hold table, cancellation
- **From**: A.U10.16 (lock table between `<!-- locks:begin -->`/`<!-- locks:end -->`; "a new lock takes its place"),
  A.U10.17 (bare-lock reasons; `Locked*` hold no lock; NOTIFY no-lock sentence), A.U10.18 (lock names; `_locked` suffix
  rule), A.U12.18 (per-call input staged inside the hold, owner 2026-09-29), A.U15.S01 (derived value inside the same
  hold), A.U16.10 (`setup()`/`set_write_protected()` take both FRAM locks), A.U16.13 (chunk layer logs only into RAM),
  A.S0930.17/.30 (erase holds both FRAM locks per unit), A.U18.33 (the "Known inconsistency" paragraph → one contract),
  A.U18.32 (the STA-retry sentence goes), A.U18.34 (the `wifi_mode_lock` hold table), A.U18.10 (≤ 3 fallback servers bound
  the NTP hold), A.U36.544 (`_config_lock` sentence), A.U11.27 (`_set_lock`), M_SRC_SENS GAP-13 (`_threshold_lock`;
  resolver form), A.U18.07 + A.U18.31 + A.U35.48 (cancellation line — no action creates it: gap fill).
- **Site**: `SPECIFICATION.md:2029-2058` (C.8 lock layers, FRAM scope, known-inconsistency paragraph).
- **Change**: (1) Opening paragraph: lock names as A.U10.18 lands them (`I2C.bus_lock`/`SPI.bus_lock`, a device session's
  `session_lock`); after "reversing risks a real deadlock" A.U12.18's sentence ("Every per-call input a multi-step operation
  keeps in a shared buffer is written inside the device-session hold, never before it: an await before the hold (a CRC's
  per-byte yield included) lets another caller overwrite it (owner, 2026-09-29: 'No races allowed').") with A.U15.S01's ",
  and a value derived from shared driver state is derived inside the same hold (the ISL29125's resolution shadow)". (2)
  New paragraph with the table (A.U10.16): "**Every lock, its level and what it may be held while taking** — a new lock
  takes its place in this table in the same change; `tests_scripts/test_lock_order.py` resolves every `async with`/
  `.acquire()` in `src/` against it." Rows: `Lockable.session_lock` (level 2, device session; a bus device's session lock
  is its bus lock), `I2C.bus_lock`/`SPI.bus_lock` (level 1), `FRAM_SPI`'s bus-lock alias (level 1), `_FRAMBaseChunk._op_lock`
  (level 3, taken before the FRAM driver's session), `ConfigManager._config_lock` (serialises the config file and its
  staged snapshot: every config read and write), `SensorReader._set_lock` (one module's config GET and PUT),
  `ISL29125_Reader._threshold_lock` (taken inside `_set_lock`, before the device session), `WifiService.wifi_mode_lock`,
  `UDPSocket._connect_lock`, `NeopixelDriver._overlay_lock`, `SensorReader._data_lock` (leaf: nothing is acquired inside
  it) — each with the external resource it serialises (A.U10.17's reasons); the check resolves `self._i2c_<chip>`/
  `self._spi_<chip>` to the session level. Below it: "`LockedCounter`/`LockedFlag`/`LockedValue` hold no lock: no method
  awaits. `NotificationService.monitor_loop()` reads its three config groups without a lock: `ConfigManager`'s value read
  never suspends on its success path, so the three reads run as one uninterrupted unit (agent, 2026-08-19)." (3) The FRAM
  scope paragraph (`:2041-2050`; its tag "(owner's decision, 2026-09-18)" → "(owner, 2026-09-18)") gains: "`setup()` and `set_write_protected()` take both
  too, and the whole-chip erase holds both per 256-byte unit, never across an await of another lock. Nothing logged under
  the FRAM driver lock reaches FRAM: the chunk layer and `FRAM_SPI` log only into the manager's RAM history (a FRAM-backed
  one would re-enter the lock), pinned in `tests/test_asy_fram_manager.py`." (4) `:2052-2058` ("**Known inconsistency
  (`asy_wifi_service.py`)** … not a bug.") → "**One getter contract (`WifiService`)** (agent, 2026-09-30): every public
  getter reads state the service holds — the 1 Hz snapshot and the phase — and never touches the radio; the one radio
  read a caller may make, `network_available_locked()`, requires `wifi_mode_lock`." followed by A.U18.34's hold table
  (connect attempt, STA disconnect wait, mode switch, hotspot bring-up, permanent deactivation, stations query, status
  read and snapshot, the NTP attempt with up to three `DNSFallback` servers ≈ 7.1 s, ≤ 9.1 s) and its waiter analysis
  verbatim, tagged "(agent, 2026-09-30)" with the DNS-inside-the-lock row "(owner, 2026-07-28)"; "the 60 s STA-retry wait
  is outside the lock". (5) Gap fill — new paragraph: "**Cancellation leaves shared state consistent**: every task path
  in UART, NET and REST restores its locks, busy flags and indicators in `finally` and re-raises `CancelledError`, never
  swallowing it in a widened `except`: the captive DNS re-raises after its cleanup, and the LED flash task leaves the LED
  to its canceller. A test sweep cancels every such path at each of its awaits (agent)."
- **Resolved**: (a) A.U10.16 lists "the `Locked*` `_value_lock`s (leaf)" and A.U10.17 (same unit) drops those locks —
  the table has no `Locked*` rows (M.SRC_CORE). (b) A.U10.16's resolver names `self.i2c_<chip>`; A.U10.35 makes them
  private — the table states `self._i2c_<chip>` (GAP-13). (c) A.U18.07/A.U18.31/A.U35.48 each say "C.8's cancellation
  line/paragraph names …", yet no action writes that paragraph and HEAD has none — written here from their shared
  requirement (G6/R54; agent decision, OR2.c).
- **Unit**: Stage 1 U10 ((1) names, (2)); Stage 2 U11 (`_set_lock` row); Stage 3 U12 ((1) per-call input); Stage 4 U15
  ((1) derived value, `_threshold_lock` row); Stage 5 U16 ((3)); Stage 6 U18 ((4), (5) first two instances); S0930 ((3)
  erase); U35 ((5) sweep sentence); U36 (`_config_lock` read/write wording, A.U36.544).
  A-C2: "S0930" is not a unit; its parts land in the units SUPP_owner_0930 states: A.S0930.17 in U16, A.S0930.30 in U36.
- **Depends**: A.U10.16-.18, A.U11.27, A.U12.18, A.U15.S01, A.U16.10, A.U16.13, A.U18.07, A.U18.31-.34, A.U35.48,
  A.S0930.17, M.SRC_SENS.080.
- **Blast carried by**: `tests_scripts/test_lock_order.py` → A.U10.16 (TSC); `src/` lock-reason comments → A.U10.17
  (SRC_*).
- **Kind**: doc

### M.SPEC.065 C.8: the general-call reset, the hazard standing rule, the SCD30 budget, the device set
- **From**: A.U15.15 (general-call paragraph → owner decision), A.U15.R02 (heater-off participant rung), A.U35.21 (lone
  BMP3XX flash-tier check), A.U0.37 V22 (`:2070-2073` standing-rule head), A.U0.33 B04/B05 (`:2107`, `:2075-2076`,
  `:2176-2178`), A.U0.25 A16/A17 (`:2118`, `:2141-2142`), A.U13.R02 (recovery scenario), A.U24.27 (generated scheme
  drives every writer), A.U4.08 (REST half of the SCD30 budget), A.U26.08 + A.U26.09 (flash-tier budget after the fixture
  split), A.U4.07 + A.U7.25 (the two exception shapes → pointer to E.6.6), A.U36.015 (per-device paragraph derived),
  A.U24.66 (per-device statements go — carried by A.U36.015), A.U36.014 (C.8 stays the one list), A.U1.06 (C.8 (a)-(b) is
  G1/R07's other home: nothing beyond A.U26.08/.09), A.U36.544 (2) ("Session 6.2" label).
- **Site**: `SPECIFICATION.md:2059-2201` (C.8 from "Known structural gap" to the end).
- **Change**: (1) `:2059-2068` → A.U15.15's "**Owner decision — the SGP40 general-call reset (`SGP40_I2C._reset()`)**: …"
  paragraph verbatim, gaining (A.U15.R02) "A failing SGP40 is first recovered by the device-addressed heater-off (Table
  14), which reaches only the SGP40; the general call stays at setup" and (A.U35.21) "a flash-tier script checks that a
  BMP3XX alone on its bus keeps its configuration and readings across the broadcast"; "the bench tier lists it as an
  exception (E.6)" names the E.6.6 row. (2) `:2070-2073` → A.U0.37 V22's head ("**Standing rule — hazard test coverage,
  read before adding a new device on a shared resource or rewiring a bus** (owner, 2026-09-03, `da3a5b5`: 'note down to
  never forget this'; every shared resource, owner, 2026-09-26): every promoted I2C/SPI device, and every other shared
  resource (locks, FRAM, the config file, sockets, the heap), gets same-device read-vs-write concurrency coverage,
  cross-device interleaving coverage (if it shares a bus with another device on any device's wiring), and an
  address/command sweep confirming it never touches a foreign or reserved address, across as many of four tiers as apply
  (cheapest first)") and gains "and the recovery ladder's bus rungs (a held-SDA bus) at every tier that can reach them".
  (3) Item 1's "(project owner's own reframing, 2026-09-15)" → "(owner, 2026-09-15, `24d74a5`)"; the generated-scheme
  bullet gains "the generated scheme drives every writer on every shared bus". (4) `:2107` "**Real-hardware write-safety
  constraints, project-owner-mandated**:" gains "(owner, 2026-09-03, `7c8dbbc`, paraphrase; (a) generalised by the
  owner's wear rule of 2026-09-17)"; `:2118` "(project owner's explicit direction)" → "(owner, 2026-09-15, `f9df9a2`)".
  (5) The SCD30 exception bullet (`:2135-2152`): "**SCD30's own on-chip NVM write is opt-in, off by default, and capped
  at one real write per test session**" gains "(owner, 2026-09-16, `98dc1b2`)"; the budget text → A.U26.09's flash-tier
  table pointer (`tests_hardware/README.md`) plus A.U4.08's REST half: "a `PUT /sensors` to SCD30 spends one NVM write
  per field whose value changed, one per `AmbPres`/`ForceCalRef` sent and one per `ContMeas=false`, none for an identical
  TempOffs/MeasInt/Altitude/SelfCal"; the routine-write fixture wording follows A.U26.08 (the read-while-write test owns
  its write; the five other dependents run by default). (6) `:2153-2175` (the flash-subset-of-bench bullet's two
  exception shapes) → "**Flash-tier bus-hazard coverage is always a subset of bench-tier coverage** — whatever gets added
  to `tests_hardware/flash/test_bus_concurrency.py` gets a bench-tier counterpart driven through the HTTP stack; every
  exception is a row of E.6.6's one list." (the false "SCD30 registers zero `_push_callbacks` … no `PUT /sensors` field
  can ever reach" goes with it). (7) `:2176-2184` → A.U0.33 B05: "**`test_bus_hazard_multi_device.py` is the permanent
  home** for generic hazard shapes (owner, 2026-09-15, `24d74a5`) — each test in it takes its own necessity verdict; …"
  (the rest of the bullet without "never retired … superseding an earlier plan"). (8) `:2185-2200` → A.U36.015's
  paragraph verbatim ("**Which devices a cross-device check applies to is derived, never listed.** …").
- **Resolved**: (a) A.U4.07 corrects the false SCD30 sentence and A.U7.25 replaces the whole exception text with a
  pointer — A.U4.07 runs first (B1 order), so its correction lands in E.6.6's row, and C.8 keeps only the pointer (both
  actions say so). (b) A.U4.08 (U4) and A.U26.09 (U26) rewrite the same SCD30 budget paragraph: U4 adds the REST half,
  U26 the flash half; A.U0.25 A16's tag stays on the head sentence. (c) A.U15.15 (U15) supersedes A.U0.33's nearby tags
  only for its own paragraph; `:2075-2076`/`:2107` tags are untouched by it.
- **Unit**: Stage 1 U0 ((2), (3) tag, (4), (5) tag, (7)); Stage 2 U4 ((5) REST half); Stage 3 U7 ((6)); Stage 4 U13 ((2)
  recovery rung); Stage 5 U15 ((1)); Stage 6 U24/U26 ((3) every writer, (5) flash half); Stage 7 U35 ((1) BMP3XX
  sentence); Stage 8 U36 ((8)).
- **Depends**: A.U0.25, A.U0.33, A.U0.37, A.U4.07, A.U4.08, A.U7.25, A.U13.R02, A.U15.15, A.U15.R02, A.U24.27, A.U25.48,
  A.U26.08, A.U26.09, A.U35.21, A.U36.015, M.SPEC.082.
- **Blast carried by**: CLAUDE.md hazard rule → A.U36.014/A.U0.37 (DOCS); `tests_hardware/conftest.py:109` marker text →
  A.U4.08 (HW); test comments → A.U15.15 (TEST_UNIT).
- **Kind**: doc

### M.SPEC.066 C.9: timers, tasks and the task inventory
- **From**: A.U10.14 (C.9 callback/one-shot wording; widening tag), A.U10.19 (task inventory table; opt-out relabelled),
  A.U10.02 (`TickSeconds` pointer), A.U10.03 (the 1 s ticks share `arm_tick_timer()`), A.U10.44 (names), A.U15.41 (a
  failed read-trigger arm ends its task), A.U18.22 (NTP retry `ONE_SHOT` and its backstop), A.U18.23/A.U18.24 (re-arm
  points), A.U10.28 + A.U18.26 (wall-clock consumers survive an RTC step: tests cited), A.U10.45 (except-tuple order),
  M.SPEC.008 (`asy_captive_dns.py`, `CaptiveDNS`).
- **Site**: `SPECIFICATION.md:2203-2222` (C.9), `:2303-2311` (the cascading-recovery-storm paragraph after C.9.1).
- **Change**: (1) First paragraph: "`get_task_starters()`/`get_timer_starters()`" → the three starter lists as A.U10.12/
  A.U10.44 name them (task, timer and trigger starters); "a task tied to a runtime mode transition
  (`asy_wifi_service.py`'s hotspot-mode DNS server task) is deliberately outside this generic supervision, a legitimate
  opt-out" → "… is outside this generic supervision (agent, 2026-08-07)", followed by A.U10.19's inventory table between
  `<!-- tasks:begin -->`/`<!-- tasks:end -->` (config flush, captive DNS, hotspot LED flash, per-connection HTTP — each
  with its reason, lifetime, cancel path and the top that persists its failure) and "every `create_task(`/
  `start_server(` in `src/` is a starter or a row of this table, checked by `tests_scripts/test_task_inventory.py`". (2)
  Second paragraph → A.U10.14's C.9 sentence ("a callback only `.set()`s a `ThreadSafeFlag` or event; re-arming, resets
  and storage state run in the task it wakes; a timer whose fire must not be lost is `PERIODIC`; each remaining
  `ONE_SHOT` states why a dropped fire is acceptable or backstopped (the stagger wait: the watchdog; the reset timer:
  `ONE_SHOT` by the owner's choice, 'brittle wrt. wdt timeout settings' (owner, 2026-07-18); the NTP retry: the next due
  check); exactly one waiter per flag"), F.1 keeping only the platform fact; the `PERIODIC` sentence gains F.1's
  silicon example, moved here (M.SPEC.090): "— the WiFi hotspot shutoff included, stopped by `reconnect_wifi()` (its
  landed name, C7) on its first delivered fire (confirmed on silicon 2026-09-25: back in STA after the 8-minute window with no reboot)". "A driver needing more than one rate
  (BMP3xx: 1Hz base tick divided down) runs a small counting sub-task" → "… runs `SensorReader`'s shared trigger divider
  (`_trigger_loop()`, G.2)". New sentences: "The 1 s tick timers (system uptime, WiFi uptime, NTP sync age) share
  `arm_tick_timer()`; they start with the timer starters and never take a stagger slot. Every elapsed time is measured
  in ticks (`TickSeconds`, G.2). A failed arm is re-armed at the task's next opportunity and persisted on a second
  failure, then the task ends for the supervisor; a read-trigger arm failure wakes the task waiting on it, which persists
  the failure and ends, and its restart re-arms. Wall-clock consumers survive an RTC step (the tests in
  `tests/test_system_service.py` and the NTP/notification files pin it)." (3) The widening paragraph: "catches `except
  (OSError, MemoryError) as e:`" → "`except (MemoryError, OSError) as e:`" and gains "(owner, 2026-08-07: every
  `Timer.init()` catch widened to `(MemoryError, OSError)` however hard the failure is to provoke)". (4) Cascading
  paragraph: "`captive_dns.py`'s `DNSServer.run()`" → "`CaptiveDNS.run()`"; "before this fix, a persistent failure produced
  ~5 log lines/sec continuously" → "without it, a persistent failure printed ~5 lines per second"; the rest holds.
- **Resolved**: A.U18.22's comment-only action also names C.9 (A.U10.14's text) — its backstop joins the `ONE_SHOT` list.
  A.U10.12 moves read triggers out of `get_timer_starters()`; C.9's starter wording follows it (M.SPEC.067).
- **Unit**: Stage 1 U10 ((1)-(3), (4)); Stage 2 U15 (read-trigger arm sentence); Stage 3 U18 (re-arm points, NTP retry).
  A-C2 step order: A.U10.28's part lands in U16, not U10 (it follows A.U10.28's own change, which lands in U16).
- **Depends**: A.U10.02, A.U10.03, A.U10.12, A.U10.14, A.U10.19, A.U10.28, A.U10.44, A.U15.41, A.U18.22-.24,
  M.SPEC.090, M.SPEC.111.
- **Blast carried by**: comments at the sites → A.U18.22-.24 (SRC_NET).
- **Kind**: doc

### M.SPEC.067 C.9.1: one shared start and a minimum separation
- **From**: A.U10.14 (rewrite: mechanism, minimum-separation guarantee, SCD30 owner decision, labels out), A.U10.12
  (mechanism), A.U10.13 + A.U11.39 (regression coverage: the per-device fake-clock scenario), A.U0.37 V10 (`:2249-2250`),
  A.U0.33 C02 (`:2286-2298`), A.U15.03 (`:2288` SCD30 tick counts), A.U31.17 (task-start spread in whole milliseconds),
  A.U26.41 (silicon spacing test reads the value), A.C.07 (measured separation, phase C), A.U10.43 (suffix names).
- **Site**: `SPECIFICATION.md:2224-2302` (C.9.1).
- **Change**: heading → "### C.9.1 Read-trigger stagger: one shared start, a minimum separation"; body as A.U10.14
  states it: the design-intent paragraph in the owner's words, tagged "(owner, 2026-09-16)"; "The mechanism" → A.U10.12:
  trigger starters only, run in task context by `start_timers(triggers, timers)`, trigger k at `t0 + k·slot` with `slot =
  1000 // (len(triggers) + 1)`, each wait a flag-woken `ONE_SHOT` (the watchdog its backstop) with a plain sleep if the arm
  fails, bus-sharing instances furthest apart; unstaggered: the three 1 s ticks and SCD30's 500 ms tick; the task-start
  spread is a separate coarse one (`asyncio.sleep_ms(1000 // len(task_starters))`, no coincidence claim; owner, 2026-09-26)
  and the boot `setup()` batch "is not staggered at all (owner, 2026-09-25)"; "The no-coincidence proof" → "the
  minimum-separation guarantee": two whole-second periods bring two reads closest at the circular distance of their
  offset difference modulo `1000·gcd`, kept ≥ `stagger.min_read_separation_ms` (Part N); the rp2 `alarm_callback()`
  drift-free reschedule bullet keeps its facts at the pin in force (C3); the SCD30 bullet: "its base tick counts ticks
  with the pin high since the last read …; SCD30's read may coincide with other reads on its bus: that is the chip's own
  timing, outside the spacing rule (owner, 2026-09-26)"; "Regression coverage" → "the per-device scenario
  (`tests/_sensortask_scenarios.py`) runs the real `start_timers()` under a fake clock and checks every pair's distance
  for every period combination; on silicon, `tests_hardware/` measures the trigger spacing per bus against this
  value". "WP7"/"WP6" leave the heading and text; dates stay. Phase C (A.C.07): the measured separation is recorded with
  its date.
- **Resolved**: A.U0.33 C02 and A.U0.37 V10 edit sentences A.U10.14 rewrites (U10, later) — their owner tags land in
  A.U10.14's text (C8). A.U15.03 co-lands with A.U10.14's SCD30 bullet (its Blast says so).
- **Unit**: Stage 1 U0 (tags on HEAD text); Stage 2 U10 (rewrite); Stage 3 U15 (SCD30 tick wording); U31 (spread form);
  phase C (measurement).
- **Depends**: A.U10.12, A.U10.13, A.U10.14, A.U11.39, A.U15.03, A.U31.17, A.C.07, M.SPEC.156.
- **Blast carried by**: A.7 boot-latency note → M.SPEC.020; `tests_hardware` spacing test → A.U26.41 (HW_BENCH).
- **Kind**: doc

### M.SPEC.068 C.10: typing conventions, stated once
- **From**: A.U36.534 (1) (C.10 rewrite), A.U15.02 (`cast()` sentence), A.U36.527 (the typing scheme lives here), A.U10.46 +
  A.U11.S02 + A.U15.43 (alias lists), A.U11.S01 → M_SRC_CORE GAP-G13 (per-kind validator sentence), A.U11.S03 / A.U19.17
  (no change).
- **Site**: `SPECIFICATION.md:2313-2321` (C.10).
- **Change**: A.U36.534 (1)'s text verbatim (its `print_log.py` example spelled `asy_print_log.py`, C7), followed by the
  aliases A.U10.46/A.U11.S02/A.U15.43 add as they land, and the sentence from GAP-G13, completed by gap pass G2: "A
  validator takes the REST value as `object`. `type_or_range_error()` refuses with `(True, None)`. A consumer that needs an
  `int` or a `float` calls the per-kind validator (`checked_int()`, `checked_float()`, `checked_numeric()`), which
  returns that type or `None` — the webserver's notification fields, the ISL29125, SGP40 and BMP3XX settings, the SGP40
  compensation read and BMP3XX `set_trigger_s()` among them; it never narrows a validated value at runtime."
- **Resolved**: A.U11.S01's "narrows it with `type()`/`isinstance()`" is replaced by GAP-G13's sentence (lead's ruling).
  Gap pass G2 (M.SRC_CORE.047, GAPS_G2 H-5 (b)) adds the `object` parameter, the `(True, None)` refusal and the
  consumer list (gap pass G1).
- **Unit**: Stage 1 U10/U11/U15 (alias lines as each lands, appended to HEAD's C.10); Stage 2 U36 (rewrite carrying them).
- **Depends**: A.U10.46, A.U11.S02, A.U15.02, A.U15.43, A.U36.527, A.U36.534, M.SRC_CORE.047.
- **Blast carried by**: D.6 and CLAUDE.md → A.U36.534 (2)-(3) (M.SPEC.075, DOCS).
- **Kind**: doc

### M.SPEC.069 C.11 and C.11.1: design decisions; the conformance probe moves to K.5.1
- **From**: A.U36.039 (item 9; SPI clause to K.5), A.U36.516 (2) (dropped in favour of A.U36.039), A.U6.04 Blast (C.11
  `:2344-2346`), A.U2.22 Blast (item 8), A.U36.543 (4) (C.11.1 → K.5.1; its closing paragraph stays as C.11's), A.U26.66
  (conformance probes for every bus chip; the probe file name).
- **Site**: `SPECIFICATION.md:2323-2366`.
- **Change**: item 8 → "**Errno/wrnno numbering**: take numbers from the catalog's bands (C.7, C.7.1)."; item 9 → A.U36.039's
  text verbatim; C.11.1 (`:2348-2366`) moves to K.5.1 (M.SPEC.142) with A.U26.66's body; C.11 closes with the kept
  paragraph "**Chip-specific facts go to Part M, not here.** …".
- **Resolved**: A.U36.039 and A.U36.516 (2) rewrite the same sentences ("not both") — A.U36.039's item 9 carries the V28
  clause; A.U36.516 (2) itself says "carried by part A's A.U36.039 … not re-planned here".
- **Unit**: Stage 1 U2 (item 8); Stage 2 U36 (item 9, the move).
  A-C2 step order: A.U2.22's part lands in U3, not U2 (it needs A.U2.02, which lands in U3).
- **Depends**: A.U2.22, A.U36.039, A.U36.543, M.SPEC.142.
- **Blast carried by**: K.5 SPI sentence → A.U36.039 (M.SPEC.142); `tests_hardware/README.md:404-415` → A.U26.66 (HW).
- **Kind**: doc

### M.SPEC.070 C.12 and C.13: fault injection; one readiness and teardown contract
- **From**: A.U14.14 (C.12 sentence), A.U24.21/A.U25.17 (C.12 is U14's), A.U10.21 (one `setup()` contract), A.U10.22 (checks
  named; its check scope narrowed to the flag's readers), A.U13.16 (I2C/SPI `deinit()` return bool), A.U5.06 (no staged
  variant), A.U10.38 (names); routine settlement initialized-flags (the flag only where product code reads it) (A-C
  review fold).
- **Site**: `SPECIFICATION.md:2368-2391`.
- **Change**: (1) C.12 last sentence → A.U14.14's ("For fault injection, the fakes raise exactly what rp2 raises (F.1):
  `EIO`/`ETIMEDOUT` from an I2C transfer, `ENODEV` only from a NAKed zero-length probe, nothing from `scan()`, and UART
  faults as sentinels, never exceptions."). (2) C.13: "(proven first by `FRAM_SPI`/`SPIDevice`; standard for
  `ConfigManager`, `NotificationCoordinator`'s staged variant)" → "(proven first by `FRAM_SPI`/`SPIDevice`; standard for
  `ConfigManager`)"; after the gate sentence: "**One contract**: `async def setup(self) -> bool`, no parameters — `True` =
  ready, `False` = degraded (already logged by the object); a protocol-layer setup keeps its documented raise for a chip
  that fails identification, which its reader's init catches. A class whose constructor refused persists that code in
  `setup()` and returns `False`." and "**Which classes carry the `initialized` flag**: only those whose product code
  reads it — the FRAM driver, the SPI driver, the UART protocol module (`UARTComm`) and the logging classes
  (`asy_print_log.py`) — each setting `self.initialized = False` last in `__init__` and `True` in `setup()`; a class
  where only a test would read it carries none (`SystemService`, `SensorReader`, `WebserverService`, `NeopixelDriver`,
  `NotificationService` among them) (agent, 2026-10-05). Every async `setup()`
  returns `bool` — `WifiService` and `WebserverService` override it like the rest. The protocol classes and
  `I2CDevice` build everything in `__init__` and are named exempt in `tests_scripts/test_readiness_gates.py`."; the
  exact class list is the set the landed `src/` reads, checked by that test; closing: "Every class's gate (a call before `setup()` or after a failed one answers as
  its contract says) and every teardown result is checked by a test (`tests/`)."
- **Resolved**: Gap pass G2 (GAPS_G2 H-5 (d); M.SRC_CORE.008/.039/.092, M.SRC_NET.079/.119): `SystemService`,
  `SensorReader` and `FRAMManager` gain the flag (`FRAMManager`'s replaces `_was_up`, D.10: one flag, one meaning), and
  `WifiService`/`WebserverService`'s `setup()` return `bool`; AC_NOTES 38/42/44 settle the exempt protocol classes and
  the `NeopixelDriver`/`NotificationService` flags. C.13 names them (gap pass G1). The routine settlement
  initialized-flags (2026-10-05) narrows this: no flag on `SensorReader`, `WebserverService`, `NeopixelDriver`,
  `NotificationService` (M.SRC_CORE.036/.039, M.SRC_NET.119, M.SRC_SENS.023/.033 as the fold amends them), and none on
  `SystemService` either: product code reads the flag only in the FRAM driver, the SPI driver, `UARTComm` and
  `asy_print_log.py` (lead ruling, A-C review fold).
- **Unit**: Stage 1 U10 ((2)); Stage 2 U13 (teardown list in C.7, M.SPEC.058); Stage 3 U14 ((1)); U5 (staged variant goes);
  the class list lands at U16 with the FRAM classes' readiness changes (M.SRC_CORE.092).
- **Depends**: A.U5.06, A.U10.21, A.U10.22, A.U13.16, A.U14.14, M.SPEC.090, M.SRC_CORE.036, M.SRC_CORE.039,
  M.SRC_CORE.092, M.SRC_NET.119, M.SRC_SENS.023, M.SRC_SENS.033.
- **Blast carried by**: the fakes → A.U24.21/A.U25.17 (TEST_HELP/TWIN).
- **Kind**: doc

### M.SPEC.071 C.14 and C.14.1: instance naming, scope, seams
- **From**: A.U0.21 (`:2399-2403` singleton scope), A.U36.544 (2) ("Session 1/3/6" labels), A.U9.10 (seam proofs named),
  A.U35.45 (no `logger=` reach-through), A.U5.08 (level setters a construction-time provider; nothing in C.14 names
  them — no edit), A.U11.32 (one helper for config and logger names), A.U15.40 (4) (`:2419-2420` "three promoted drivers"),
  A.U10.38 (names), A.U6.06 (no change), A.U22.02 (nothing named).
- **Site**: `SPECIFICATION.md:2393-2441` (C.14, C.14.1).
- **Change**: (1) C.14 first paragraph: "Session 1 of the device-genericization initiative (`SPECIFICATION.md Part L`) —
  the mechanism `buildgen/` (Session 3 on) now drives from each device's TOML, wired into the real build chain as of
  Session 6." → "The mechanism `buildgen/` drives from each device's TOML (Part L)."; the singleton clause → A.U0.21's
  text (with `NotificationService`, M.SPEC.008). (2) C.14.1: "`config_manager.py`'s `instance_name(base, ext) -> str` is
  the one place the rule is implemented" holds and gains "and the config file and `CFGMGR_<name>` logger names are
  built only by `SensorReaderConfig`, through one helper"; "before either the `logger=`-reuse or fresh-`make_logger()`
  branch, so `self.pr.name`/`self.name` always agree" → "before `make_logger()`, so `self.pr.name` and `self.name` agree";
  the REST-key paragraph: "This was a real, confirmed gap found by audit: … would have silently collided … Fixed by
  threading `self.name` through both:" → "So both keys thread `self.name`:" and "every `get_dict_cfg()` across the three
  promoted drivers" → "across the promoted sensor drivers (four today)". (3) A one-line seam sentence in C.14.3's fan-in
  paragraph (A.U9.10): "Each LED and notification seam has an end-to-end test (`tests/test_notification_neopixel_
  integration.py` and siblings)."
- **Resolved**: A.U35.45 removes the `logger=` reach-through that C.14.1 describes as a branch — the sentence names only
  `make_logger()` (grep at execution confirms no other mention).
- **Unit**: Stage 1 U0 ((1) singleton clause); Stage 2 U9 ((3)); Stage 3 U11 ((2) helper); Stage 4 U15 ((2) four drivers);
  Stage 5 U35 ((2) branch); U36 ((1) labels, (2) history).
- **Depends**: A.U0.21, A.U9.10, A.U11.32, A.U15.40, A.U35.45, A.U36.544.
- **Blast carried by**: BACKLOG `:81-82` → A.U0.21 (DOCS).
- **Kind**: doc

### M.SPEC.072 C.14.2 and C.14.3: wiring tags, construction order, fan-in
- **From**: A.U36.514 (4) (`:2456-2462` → the L.6.4 pointer), A.U0.39 L12 (`:2456` tag — folds into L.6.4's owner quote),
  A.U0.44 L58 (`:2506`), A.U5.03 (one `LogConfig` per FRAM store), A.U5.07 (WiFi LED at construction; construction order
  with `led_target`), A.U5.11 (SGP40 value references, one backup group), A.U5.06 (signals at construction), A.U36.544 (2)
  (Session labels), A.U36.511 (5) (`:2578-2579`), A.U36.513 (C.14.3 owns the `(source, field)` signal reference), A.U10.19
  (C.14.3 cites the inventory), A.U10.38 (names), M.GEN.010 (setup order).
- **Site**: `SPECIFICATION.md:2443-2587` (C.14.2, C.14.3).
- **Change**: (1) C.14.2 opening: "**Extended by Session 3 of SPECIFICATION.md Part L** (the `buildgen/` generator) from
  this Part's original 2-element shape to a 5-element one, resolving that plan's own two open `_WIRING`-coverage questions
  (full rationale: that session's PR description) — purely additive, no existing driver's constructor signature changed
  to make this possible:" → "Its five fields:". (2) `:2456-2462` → A.U36.514 (4): "**A comment, never a real Python value**
  (L.6.4), read only by `buildgen/wiring.py`." — the "Every element is a bare word …" sentence stays. (3) `mode="setter"`
  bullet: the WiFi LED is passed at construction now (A.U5.07) — the bullet keeps the mode's definition and its example
  becomes whatever setter-mode tag remains at landing, or the bullet states "no driver uses it today" if none does
  (grep at execution). (4) `:2506` "is a deliberate, narrow exception to" → "is a narrow exception (agent, 2026-09-10,
  `e2bcf6f`) to". (5) "**Ordering hazard #1**": "The generated `sensortask_wozi.py` constructs `scd30` before `sgp40` for
  exactly this reason (A.7's construction order) — a real, deliberate reordering of wozi's FRAM chunk allocation order,
  safe only because wozi is never physically flashed (CLAUDE.md)." → "A producer is constructed before its consumer
  (A.7's construction order); any order is valid for the FRAM layout, which is fixed within one build only (A.4)."; "plus
  two fixed mandatory-infra edges and one conditional one" → the edges as A.U5.07 lands them ("every `sgp40` and every
  `notification` instance depends on `ntp`; with `led_target` set, fram → neopixel → conn → ntp → sysfunct → sensors");
  "`buildgen/graph.py` (Session 3)" → "`buildgen/graph.py`". (6) "**Ordering hazard #2**": "(fixed 2026-09-12; a full
  audit … found no other occurrence in `src/`)" → "(agent, 2026-09-12: no other cross-module read in `src/` conflates the
  two)"; "`NotificationCoordinator._check_one()`" → "`NotificationService._check_one()`". (7) C.14.3: the
  `NotificationCoordinator` fan-in sentence → "`NotificationService`'s signals (`source`/`field` direct references) are
  constructor arguments, resolved after every producer exists, so they need no `@wiring` declaration"; "(the common case —
  every real `devices/*.toml` compensates both off one `SCD30_Reader`)" → "(the common case: one `SCD30_Reader` feeding
  both)"; "SGP40_Reader.__init__ uses the same shape twice" gains "passed as value references, with its backup settings
  one group"; "**Generalized per-value measurement wiring (SPECIFICATION.md Part L.6.3, 2026-09-10)**" → "**Per-value
  measurement wiring (L.6.3)**"; the inventory pointer "Tasks created outside the starters: C.9's table."
- **Resolved**: A.U0.39 L12 tags the owner sentence that A.U36.514 (4) removes from C.14.2 (U36, later); the quote and
  its tag live in L.6.4 (M.SPEC.149) — C8.
- **Unit**: Stage 1 U0 ((4), L12 on HEAD text); Stage 2 U5 ((3), (5) edges, (7) signals); Stage 3 U10 (names); Stage 4
  U16 ((5) layout clause, A.U16.01); Stage 5 U36 ((1), (2), (6), (7) count and labels).
- **Depends**: A.U5.03, A.U5.06, A.U5.07, A.U5.11, A.U16.01, A.U36.511, A.U36.514, M.SPEC.149, M.SPEC.020.
- **Blast carried by**: test comments citing C.14.3 → A.U36.513 (TEST_UNIT); L.2/L.3/L.6.4 → M.SPEC.145/.146/.149.
- **Kind**: doc

## SPECIFICATION.md — Part D (`:2589-2743`)

### M.SPEC.073 Part D: heading, intro; D.0, D.13, D.14, D.16 move to Part K
- **From**: A.U36.543 (7) (heading, intro, removals; D.8 sentence), A.U36.540 (3) (D.0's new sentence, landing in K.1),
  A.U36.532 (numbering: Part D numbers ascend with gaps).
- **Site**: `SPECIFICATION.md:2589-2600`, `:2720-2728`, `:2739-2741`.
- **Change**: A.U36.543 (7) verbatim: heading "# Part D — `src/` quality bar"; intro "The bar every file in `src/` and
  every generated module meets: … Part K's step K.2 applies it; Part C gives a driver's shape."; D.0 (with A.U36.540
  (3)'s rewrite), D.13, D.14 and D.16 removed (their content lands in K.1, K.10, K.11, M.SPEC.140-.143); D.1-D.12 and D.15 keep
  their numbers.
- **Resolved**: A.U36.540 (3) rewrites D.0's sentence in place, and A.U36.543 (2) moves D.0 to K.1 "followed by A.U36.540
  (3)'s D.0 sentence" — the rewritten sentence lands in K.1 only (A.U36.540 itself says so).
- **Unit**: U36.
- **Depends**: A.U36.540, A.U36.543, M.SPEC.140-.143, M.SPEC.003.
- **Blast carried by**: the `.claude/skills/integrate-module/SKILL.md` → M.DOCS.109 (A.U36.543 (9)); TOC → M.SPEC.001.
- **Kind**: doc

### M.SPEC.074 D.1-D.5: correctness, raises, stability, resources, blocking
- **From**: A.U36.540 (4) (D.1 discrepancy rule), A.U12.08 (`altitude_baro` → `pressure_at_height()`), A.U12.06 (no change),
  A.U36.032 (D.2 typed-call-site qualifier; untyped entry points), A.U14.06 (D.2 controlled-raise schema; per-bus
  surface), A.U13.07 Blast (uninitialised bus), A.U11.12/A.U11.17/A.U35.36 (cite D.2, no edit), A.U36.541 (2) (D.3
  "indefinitely"), A.U31.19 (2) (D.4 sleep rule), A.U28.27 (TRY003/EM10x keep the SRAM reason, D.4 — no SPEC edit).
- **Site**: `SPECIFICATION.md:2602-2645`.
- **Change**: (1) D.1: `:2606-2607` → A.U36.540 (4)'s sentence ("**A discrepancy proven by the datasheet or the
  specification is fixed with a regression test for the correct behaviour** (E.2.2); one short of that proof is entered
  in BACKLOG.md's owner-question list and not changed (owner, 2026-09-25)."); `:2611` "`altitude_baro`'s range" →
  "`pressure_at_height()`'s range". (2) D.2: `:2617-2622` → A.U36.032's text verbatim; `:2623-2628` → A.U14.06's two
  rewrites verbatim (controlled-raise schema; per-bus surface, its C.12 pointer). (3) D.3: "Units run years without a
  reboot:" → "Units run indefinitely without a reboot (0.1):". (4) D.4 gains A.U31.19 (2)'s sentence ("A sleep takes
  whole milliseconds (`asyncio.sleep_ms(<int>)`, `asyncio.wait_for_ms()`) or a whole number of seconds: … checked by
  `tests_scripts/test_src_sleep_forms.py`."), extended by M_SRC_SENS GAP-1: "A blocking `time.sleep*` appears in `src/`
  only at the two named sites — the SPI chip-select settle and the boot bus clear — and the same check fails any other."
  (D.5's "No blocking I/O, `time.sleep`" gains "(except those two, D.4)".)
- **Resolved**: A.U36.032 Depends A.U14.06 (same section, later sentences) — U14 lands A.U14.06, U36 A.U36.032 on the text
  above it. GAP-1's exceptions contradict D.5's flat "no `time.sleep`" — D.5 names them (gap fill).
- **Unit**: Stage 1 U12 ((1) rename); Stage 2 U14 ((2) A.U14.06); Stage 3 U31 ((4)); Stage 4 U36 ((1) rule, (2)
  A.U36.032, (3)).
- **Depends**: A.U12.08, A.U13.07, A.U13.08, A.U14.06, A.U14.14, A.U31.19, A.U36.032, A.U36.540, A.U36.541,
  M.SRC_SENS.002/.008.
- **Blast carried by**: `tests_scripts/test_src_sleep_forms.py` → A.U31.19 + GAP-1 (TSC).
- **Kind**: doc

### M.SPEC.075 D.6-D.15: typing, improvement, platform check, API shape, readability, tests, order
- **From**: A.U36.534 (2) (D.6), A.U10.31 (quoting rule), A.U28.30 (D.6 suppression form rule), A.U28.27 (D.6/B.15 name the
  two ruff groups), A.U18.43 (no edit), A.U36.543 (7) (D.8 sentence), A.U36.540 (5) (D.9), A.U10.45 (D.10 raise form),
  A.U5.17 + A.U5.04 (D.10 config objects; `max-args`), A.U5.18 (ceilings), A.U11.09 (pattern is U14's G/F; none here),
  A.U17.19 (none), A.U36.533 (2) (D.11), A.U10.34 (every Python scope), A.U35.03 (D.12's red-flag list is Part E's),
  A.U10.32 (D.15 rewrite), A.SDEP.08 (D.9 pin token); OR141.a (3) (D.15 names `voc_algorithm.py` as its one
  exception) (A-C review fold).
- **Site**: `SPECIFICATION.md:2647-2737`.
- **Change**: (1) D.6 → A.U36.534 (2)'s text ("Type-hint every parameter and return, not over- or under-typed; the idiom
  and its reasons are C.10. **`mpy-cross` does not dead-code-eliminate …** (B.11).") followed by the quoting paragraph:
  "**Quoting annotations** (owner, 2026-09-24): quote an annotation only when it names something imported under
  `TYPE_CHECKING`, or a class defined later in the module that ruff (F821) or mypy would otherwise reject; leave every
  other annotation bare. MicroPython never evaluates annotations, so both forms are runtime-safe; every file follows it
  (owner, 2026-09-25)." and "Every `# type: ignore` and `# noqa` names its codes in ascending order; in `src/` a `type:
  ignore` carries a one-line reason and no `# noqa` exists; a typing workaround names its external defect and removal
  trigger (0.2, P4; B.15) — checked by a test. Ruff's per-file ignores name two scope groups, MicroPython-run code and
  host code (B.15)." (2) D.8 gains A.U36.543 (7)'s ": an improvement significant enough to want its own regression test
  gets one, never a manual spot-check (agent, 2026-07-14, `1682601`)". (3) D.9: "(currently v1.29.0 — the last pass's
  findings are catalogued in Part F.5)" → the pin in force (C3); "is a D.1-style behavior change — flag and ask." → "is a
  behaviour change and follows D.1." (4) D.10: "`crc_checks.py`'s `CRC_Pass`/`CRC8`/`CRC16`/`CRC32`" → "`CRCPass`/`CRC8`/
  `CRC16`/`CRC32`"; gains "Parameters that travel together are one config object (a namedtuple built by generated code,
  G.2) rather than a long list; ruff's ceilings (`max-args` 8 and the others) sit at the measured maximum and only go
  down, a signature mirroring an external API exempted per file, never by raising a limit (owner, 2026-09-26); checked
  by `tests_scripts/test_lint_ceilings.py`. A raise carries one message form and an `except` tuple lists its classes
  alphabetically (C.3)." (5) D.11 → A.U36.533 (2)'s text verbatim. (6) D.12 unchanged; the test standard's red-flag list
  is Part E's (M.SPEC.077). (7) D.15 → A.U10.32's rewrite (roles, alphabetical within a role, dunders, the restored
  "**'Starter' is a role, not a name** (owner, 2026-09-14)" paragraph with `Calibrate`, scope, the import-time exception),
  plus (A-C review fold) "One named exception: `src/voc_algorithm.py` keeps upstream's member order, as it keeps its
  names (C.2; owner, 2026-10-05)."
- **Resolved**: A.U10.31's own D.6 sentence ("existing files are not mass-edited" → "every file follows it") lands in U10
  on HEAD's D.6, and A.U36.534 (2) (U36) rewrites the paragraph above it — the quoting paragraph keeps A.U10.31's
  wording (A.U36.534 says "the quoting paragraph `:2658-2661` is A.U10.31's"). A.U28.30 and A.U28.27 both say "U36" for
  their D.6 sentences — placed in U28 with the check (the rule is current then; agent decision).
- **Unit**: Stage 1 U5 ((4) config objects, ceilings); Stage 2 U10 ((1) quoting, (4) raise form, (7) with its
  `voc_algorithm.py` sentence, with the order check that exempts it); Stage 3 U28 ((1)
  suppression form, scope groups); Stage 4 U36 ((1) A.U36.534, (2), (3), (5)); pin token U0 (C3).
- **Depends**: A.U5.17, A.U5.18, A.U10.31, A.U10.32, A.U10.34, A.U10.45, A.U28.27, A.U28.30, A.U36.533, A.U36.534,
  A.U36.540, A.U36.543.
- **Blast carried by**: CLAUDE.md comment rule → A.U36.533 (1) (DOCS); `pyproject.toml` comments → A.U5.17/A.U28.27
  (TOOL); the order and convention checks → A.U10.47 (TSC).
- **Kind**: doc

## SPECIFICATION.md — Part E (`:2745-3433`)

### M.SPEC.076 Part E intro and E.1: the host tier, ports, scratch, lwIP host files, evidence, parallelism
- **From**: A.U24.70 (port bands; `:2780-2793` points to the table), A.U24.69 + M.SCR.012 (one lock per product-fixed port,
  inherited by children), A.U24.10 + A.U24.11 (scratch failures raised; keys unique, checked), A.U21.12 + A.U21.13 (the
  second L1 file set `tests/lwip_host/` on `build-lwip`), A.U21.22 (`test.sh` and the toolchain lock), A.U27.05 (the L0
  list: the stripped, compiled image set boots under the twin; the pytest tier runs `mpy-cross` from the toolchain),
  A.U7.20 + A.U27.16 (evidence archive), A.U35.24 (heavy-file dispatch list checked), A.U7.08 (pytest tier reports through
  a run record), A.U7.26 (a missing build fails the host tier), A.U8.16 (speed probe), A.U28.27 (no edit: PT rules cite
  E.1), A.U6.10 (no edit), A.SDEP.16 (the prewarm scan band, only if A.SDEP.16 retires it), A.U2.02 (catalog test in the
  inventory), M.SCR.017 (port 53 and the scenario harness).
- **Site**: `SPECIFICATION.md:2745-2801`.
- **Change**: (1) Intro unchanged. (2) First E.1 paragraph's host list gains "the boot of the stripped, compiled image
  set under the twin (the shipped form, B.11; `mpy-cross` from the toolchain directory)" and "the error catalog against
  every logging call"; new sentence: "A host test whose build or toolchain input is missing fails, never skips." (3) The
  pytest-tier paragraph gains "and reports its counts through a run record that `scripts/test.sh` reads into its summary
  block (E.10)"; "`TEST_PARALLELISM` budget" gains "(a monotonic speed probe picks it, falling back to the slow-host
  value when the probe cannot run; the heavy-file dispatch list is checked against the file set)". New sentence: "One
  toolchain build at a time per toolchain directory: a `test.sh` that must build waits on no one — it fails at once
  naming the run holding the lock (B.5)." (4) The ports paragraph (`:2780-2793`) → "**Ports**: every test socket binds
  inside its owner's band of `tests/_port_bands.py` — disjoint, below the OS ephemeral range (32768-60999), the
  per-device libraries splitting their band over the derived devices; an allocator past its band end fails naming it,
  and `tests_scripts/test_port_bands.py` checks the table and every binding site. For UDP an overlap is silent rather
  than `EADDRINUSE`, which is why the bands exist. **Fixed ports** the product itself binds (53 for the captive DNS,
  18080 for the CI suite's twin) are held by one runner at a time: a lock directory per port under
  `${XDG_RUNTIME_DIR:-/tmp}`, taken by `scripts/test.sh`, `scripts/run_digital_twin_ci.sh`,
  `scripts/run_unix_port_integration.sh` and the scenario harness; a runner started by one holding the lock inherits it,
  an unrelated second suite fails at once naming the holder (CLAUDE.md's two-suites rule)." (5) Scratch paragraph gains
  "keys are unique across files and processes (checked); a cleanup failure other than absence is raised". (6) New
  paragraph: "**The lwIP host files** (`tests/lwip_host/test_*.py`) run after the `tests/test_*.py` loop on the
  `build-lwip` binary (B.2, B.14.3), through the same per-file function; they bind no host port (loopback lwIP is
  in-process) and `--coverage` excludes them." (7) New paragraph: "**Evidence archive**: every runner — `scripts/test.sh`,
  `scripts/run_digital_twin_ci.sh` (per device), the hardware runners — moves its logs and reports under
  `build/archive/<runner>/<UTC>/` and keeps the last three; a failed run's logs are copied, never only moved." (8) If
  A.SDEP.16 retires `unix_port_poll_prewarm.py`, the band list drops its scan band.
- **Resolved**: — (no conflict among the constituents)
- **Unit**: Stage 1 U7 ((2) missing build, (3) run record, (7)); Stage 2 U8 ((3) probe); Stage 3 U21 ((3) lock, (6));
  Stage 4 U24 ((4), (5)); Stage 5 U27 ((2) shipped form, (7) twin runner, M.SCR.017's port-53 sentence); U35 ((3)
  dispatch check); U0 ((8) if A.SDEP.16 (c)); U2 ((2) catalog).
  A-C2 step order: A.U2.02's part lands in U3, not U2 (it follows A.U2.02's own change, which lands in U3); A.U24.70's part lands in U25, not U24 (it needs A.U24.65, which lands in U25).
- **Depends**: A.U7.08, A.U7.20, A.U7.26, A.U8.16, A.U21.12, A.U21.13, A.U21.22, A.U24.10, A.U24.11, A.U24.69, A.U24.70,
  A.U27.05, A.U27.16, A.U35.24, M.SCR.012, M.SCR.017.
- **Blast carried by**: CLAUDE.md two-suites bullet → A.U24.69 (DOCS); README env-var list → A.U8.16 (DOCS).
- **Kind**: doc

### M.SPEC.077 E.2, E.2.1, new E.2.2 and new E.2.3: microtest, per-device runs, test changes, the test standard
- **From**: A.U7.07 (skips; empty file fails), A.U24.03 (async tests and aborted files fail), A.U24.04 (canonical trailer,
  checked), A.U24.65 + A.U25.46 + M.TEST_HELP.033 (per-device files: `PER_DEVICE = True`, one job per derived
  device; the concurrency library moves host-side), A.U36.016 (heavy twin tests follow the per-device bar), A.U24.75
  (named homes of each `buildgen/` module's tests), A.U24.76 (doubles and builders named by role), A.U35.07 (E.2.1's "stay
  wozi-only" is U36's), A.U36.544 (2) ("Part L's Session 6.2"), A.U36.532 (numbering), A.U36.017 (E.2.2), A.U36.542 (0.4
  cites E.2/E.3 for test conventions), A.U24.07 + A.U24.08 + A.U26.15 + A.U35.10 + A.U35.03 (the "Part E hygiene section"
  / "test standard" each names — no action creates it: gap fill), M_TEST_HELP GAP-H5 (the deleted library's citers),
  M_TWIN gap (E.2.1's text names files that exist; gap pass G1); routine settlement device-script-sleeps (G7/R23: a
  fixed wait becomes a bounded poll where the state is readable) (A-C review fold).
- **Site**: `SPECIFICATION.md:2803-2839`; new E.2.2 and E.2.3 after E.2.1.
- **Change**: (1) E.2 → "`microtest.py` is a minimal collector/runner — not CPython's `unittest`, unavailable on the Unix
  port's standard build. It calls every synchronous `def test_*` and reports PASS, FAIL or SKIP (`microtest.Skip(reason)`,
  counted and listed); a file that collects nothing fails, an `async def test_*` or a test returning a value fails, and a
  `BaseException` aborting the file reports the rest as not run, never as passed. Every test file ends with the canonical
  `microtest.run(globals())` trailer (checked by `tests_scripts/test_microtest.py`); `run()` always ends with
  `sys.exit()` (E.3). Plain `assert`." (2) E.2.1 (heading "### E.2.1 Per-device scenario libraries: one process per
  device" — numbered as a subsection under A.U36.532): "parametrized across all 6 real devices" → "run for every device
  of `devices/*.toml`"; the wrapper description → "a file marked `PER_DEVICE = True` is run by `scripts/test.sh` once per
  derived device (`TEST_DEVICE`), each its own Unix-port process — no per-device wrapper files"; the table keeps
  `tests/_sensortask_scenarios.py` (`tests/test_sensortask.py`) and `tests/_digital_twin_construction_scenarios.py`
  (`tests/test_digital_twin_construction.py`); the concurrency row → "real concurrent TCP against `WebserverService`:
  the host-side scenario harness `scripts/_digital_twin_scenarios.py`, one twin process per scenario (E.9)". The memory
  paragraph keeps its dated measurement; "It is **not** a reversion to the old per-device test-body duplication that Part
  L's Session 6.2 collapsed: …" → "Every scenario body lives once and stays device-generic; the per-device run adds no
  logic."; `:2836-2839` → A.U36.016's paragraph verbatim except its "one device per process like the wrapper files above", which reads "one device per process, the file marked `PER_DEVICE = True` (above)" (gap pass G1: the M_TWIN gap's "E.2.1 names files that exist" — no wrapper file exists after (2); `tests/test_digital_twin_sensortask_integration.py` and `tests/_twin_devices.py` exist, M.TWIN.144). New closing paragraph (A.U24.75): "Every `buildgen/` module has
  `tests_scripts/test_buildgen_<module>.py` or a named home (`buildspec` → `test_buildgen_driver_registry.py`/
  `test_buildgen_validate.py`, `codegen` → `test_buildgen_generate.py`, `errors` → every reject test, `model` →
  `test_buildgen_validate.py`); pytest suites use module-level `def test_*`, never `Test*` classes (checked). Test
  doubles and builders are named by role." (3) New "### E.2.2 A test changes only mechanically" — A.U36.017 (1) verbatim.
  (4) New "### E.2.3 The test standard and hygiene" (gap fill, each sentence from its action): "**A test bites**: it
  asserts (an `assert`, `AssertionError` or `pytest.raises` in the test or a helper it calls — never a `raise` in the code
  under test), and none of these red flags holds: no assertion; only "no exception", `is not None`, `isinstance` or
  `callable`; a check that cannot fail or re-asserts a stand-in's canned return; `except: pass`; a log assertion on
  existence only (a log check names the number and `ErrType` of exactly one persisted entry per event); a loop that checks
  nothing or runs zero times; a tolerance or scripted value that cannot fail its bound; a name claiming more than it
  asserts; a helper whose failed setup does not fail the test; an expected value copied from the code under test (owner,
  2026-09-25). **Hygiene**: a test restores every process-wide state it changes on every path — the fakes reset their
  class and module state after every test through `microtest.after_each`, which also restores `sys.path` and
  `gc.threshold()`; a test that starts a task keeps it and cancels and awaits it, and the shared `tests/_async_harness.run()`
  refuses a nested call (F.1) and fails a test that leaves a task parked (owner, 2026-09-26: 'Each test cleans up after
  itself on every path'); a bench test that writes config restores the prior value in `finally`, checks the restore's
  result word, and first repairs a leftover of an aborted run. **Time at L1 is driven**: unit tests move time through the
  fakes and `DrivenTime` (virtual sleeps and 2**30-period ticks); a real wall-clock wait is used only where a `const()` or
  the platform leaves no alternative, stated and a Part N row; `tests/_fast_sleep.py` keeps its one use, collapsing every
  sleep to one yield." (5) E.2.3 gains, after the driven-time sentence (A-C review fold): "**Waits poll.** A test, a
  twin runner or a device script waits for a state by polling for exactly that state with a deadline wherever the
  state can be read (agent, 2026-08-26, `7ae2f27`; device scripts included, agent, 2026-10-05); a fixed delay stays only
  where there is nothing to read or a probe would disturb the property under test, named, measured and a Part N row
  (agent, 2026-09-16, `a335923`)."
- **Resolved**: (a) A.U24.65 (generic `PER_DEVICE` file for the concurrency library) vs A.U25.46 (library retired
  host-side) — A.U25.46 kept (M.TEST_HELP.033, M.SCR.017). (b) Several actions name "SPEC E hygiene section"/"test
  standard" written by "U36", yet no U36 action writes it — created here from their texts (agent decision, OR2.c). (c) A.U36.016's
  "like the wrapper files above" predates A.U24.65 (3)'s `PER_DEVICE` dispatch, which (2) states — the clause names the
  marker (M.TWIN.144 (d): the file meets the bar through `PER_DEVICE`; gap pass G1).
- **Unit**: Stage 1 U7 ((1) skip/empty); Stage 2 U24 ((1) rest, (2) per-device runs, buildgen homes, (4) hygiene
  sentences); Stage 3 U25 ((2) concurrency row); Stage 3b U26 ((5), with the device scripts' fixed waits turned into
  polls, M.HW_DEV; the twin runners' polls land in U25 before it); Stage 4 U35 ((4) bite list, driven time); Stage 5
  U36 ((2) A.U36.016, labels; (3)).
- **Depends**: A.U7.07, A.U24.03, A.U24.04, A.U24.07, A.U24.08, A.U24.65, A.U24.75, A.U24.76, A.U25.46, A.U26.15,
  A.U35.03, A.U35.10, A.U36.016, A.U36.017, M.TEST_HELP.033; M.HW_DEV.048, M.HW_DEV.050, M.HW_DEV.081, M.HW_DEV.089, M.HW_DEV.139, M.HW_DEV.141 (the device scripts' bounded polls).
- **Blast carried by**: CLAUDE.md working-agreement bullet → A.U36.017 (2) (DOCS); README test recipes → A.U24.65 (DOCS).
- **Kind**: doc

### M.SPEC.078 E.3: running, the generated tree, the forced exit, the summary
- **From**: A.U27.15 (`MICROPYPATH` from `scripts/micropypath.toml`; `:2851` example), A.U36.036 (3) (`.frozen` pointer),
  A.U24.46 (a direct run refuses a stale tree), A.U27.11 (generator all-or-nothing, atomic, pruned), A.U6.02 (every
  device's definitions generated into the build tree), A.U6.05 (tests_js load generated definitions; H.8 holds it),
  A.U24.05 (the GC-stage and coverage runners fail an incomplete file), A.U24.59 (harness facts: `asyncio` attributes
  assignable, C builtins not), A.U36.546 (1) (E.3 gains the structural-invariant paragraph and the forced-exit mechanism),
  A.U14.28 (Part E rig-limit text points to F.7), A.U7.03 (summary block per level), A.U27.18 (no change), A.U36.544 (2)
  (Session labels), M_SCR gap 5 / OR133 (exit 2 on a usage or setting error).
- **Site**: `SPECIFICATION.md:2841-2879`.
- **Change**: (1) The direct-run example → "`MICROPYPATH="$(scripts/_unix_port.sh micropypath unit)"
  ~/pico-toolchain/micropython/ports/unix/build-standard/micropython tests/test_math_helpers.py` — the unit and twin
  layouts are defined once, in `scripts/micropypath.toml`"; the `.frozen` paragraph → "`.frozen` is MicroPython's import
  sentinel, not a directory (F.1); `frozen_modules` is an ordinary, gitignored directory (A.9's output)". (2) The
  generated-module paragraph: "(SPECIFICATION.md Part L's Session 6)" goes; gains "`scripts/_generate_sensortask_modules.py`
  writes every device's modules and definitions into `build/generated_src/` all or nothing, atomically, pruning stale
  device outputs; a direct run refuses a stale or missing generated tree". (3) New paragraph (A.U36.546): "**The forced
  exit.** MicroPython's asyncio has no parent/child task tracking: a test that drives the generated task graph leaves
  every task `create_task()` spawned parked after its own coroutine returns, and `Task.cancel()` on the awaited task does
  not cascade. One process runs every test of a file, so `microtest.run()` always ends with `sys.exit()` (0 all-pass, 1
  any failure) rather than waiting for the interpreter's idle detection; `digital_twin/launch.py`'s tracked-task list is
  the alternative for a graph small enough to enumerate." (4) New paragraph (A.U36.546): "A host test proves its
  invariant structurally and generates no mass filesystem churn: `tests/test_tmp_scratch.py` records the `os` calls of a
  full `TmpScratch` lifecycle and asserts none reads the shared root, instead of building 400,000 directories (396 MB of
  disk writes per run before, 392 KB after, `/proc/diskstats`, 2026-09-17)." (5) New sentence (A.U24.59, A.U14.28):
  "Where the Unix-port rig differs from rp2 is F.7; on it, `asyncio` attributes are assignable and the C builtin modules
  (`time`, `socket`) are not." (6) The annotations paragraph keeps "never write the verdict to `$GITHUB_STEP_SUMMARY`" and
  gains "the run ends with the summary block of E.10, per level". (7) (OR133, M_SCR gap 5): "A usage or setting error —
  an unknown option, an invalid `GC_THRESHOLD`, `PER_FILE_TIMEOUT_S`, `TESTS_SCRIPTS_TIMEOUT_S` or
  `TEST_PARALLELISM` — exits 2 before the run
  touches the live tree (E.10)."
- **Resolved**: — (no conflict among the constituents)
- **Unit**: Stage 1 U6 ((2) definitions); Stage 2 U7 ((6), (7)); Stage 3 U24 ((2) refusal, (5) harness fact); Stage 4
  U27 ((1), (2) atomic); Stage 5 U36 ((1) `.frozen`, (2) label, (3), (4)); U14 ((5) F.7 pointer).
- **Depends**: A.U6.02, A.U7.03, A.U14.28, A.U24.05, A.U24.46, A.U24.59, A.U27.11, A.U27.15, A.U36.036, A.U36.546,
  M.SCR.035 (exit 2), M.SPEC.086.
- **Blast carried by**: CLAUDE.md hang/segfault bullets → A.U36.546 (DOCS); `digital_twin/README.md` path literals →
  A.U27.15 (TWIN).
- **Kind**: doc

### M.SPEC.079 E.3.1: the test heap and the per-file timeout
- **From**: A.U8.15 (Part N rows `l1.unix_heapsize`, `runner.per_file_timeout_s`; values point to Part N), A.U8C2.08
  (`l2.bus_hazard_concurrency_run_seconds`), A.U27.14 (`:2931` "85 times"), A.U7.04 (`RETRIED-PASS`), A.U7.06 (both
  timeout variables validated), A.U24.65 (heap split per device job), A.U35.23 (heap-flag history row), A.U0.40 L10
  (`:2884-2886` tag), A.U0.37 (none in E.3.1 beyond `:2905` "standing backstop" tag), A.U36.512 (3) (`:2898` "dev-variant"
  → "dev device"), A.U30.12 (`gc.threshold_bytes` sites).
- **Site**: `SPECIFICATION.md:2881-2934`.
- **Change**: (1) `-X heapsize=16M` sentence names `l1.unix_heapsize` (Part N) and "never *raised*" keeps A.U0.40's L10
  tag "(agent, 2026-09-17; no per-file override: owner, 2026-09-17)"; the history list keeps its measured facts with "WP1+
  WP2 made the then-monolithic …" → "Building all six devices' graphs in one process pushed 8M → 32M …" (G9/R12 label
  out) and gains A.U35.23's row when B3 records it ("the heaviest file's measured peak at both stages plus the margin");
  "`test_digital_twin_bus_hazard_concurrency.py`'s dev-variant scenario … own 9-second real-clock budget" → "dev
  scenario … budget (`l2.bus_hazard_concurrency_run_seconds`)". (2) `PER_FILE_TIMEOUT_S` paragraph: "(default 240)" →
  "(`runner.per_file_timeout_s`, Part N)"; "is a standing backstop" gains "(owner, 2026-09-26)"; "Two retries absorb
  transient contention" gains "; a pass after a retry is reported as `RETRIED-PASS`, a root-cause item, never as a plain
  pass"; new: "`PER_FILE_TIMEOUT_S` and `TESTS_SCRIPTS_TIMEOUT_S` are validated as positive integers before any sweep (exit 2
  otherwise, E.10)." (3) Overrides paragraph: "the per-device splits" → "the per-device jobs (one process per device)".
  (4) GC stage paragraph: "validated once in `scripts/test.sh` rather than 85 times inside the runner" → "validated once
  in `scripts/test.sh` rather than once per test file"; "is rejected before the run touches the live tree" gains "(exit
  2)"; the `--coverage` sentence → "`--coverage` runs at the reactive default and ignores `GC_THRESHOLD`, and says so
  (E.5)".
- **Resolved**: A.U7.06 exits 1 on an invalid timeout; the owner's answer OR133 (AC_NOTES 43) makes every runner,
  `test.sh` included, exit 2 on a usage or setting error, with no exception — exit 2 (M.SCR.035).
- **Unit**: Stage 1 U0 ((1) tag, (2) tag); Stage 2 U7 ((2) retry, validation); Stage 3 U8 (Part N pointers); Stage 4 U24
  ((3)); Stage 5 U27 ((4) count); U35 (history row); U36 ((1) label, A.U36.512).
  A-C2 step order: A.U24.65's part lands in U25, not U24 (it follows A.U24.65's own change, which lands in U25).
- **Depends**: A.U7.04, A.U7.06, A.U8.15, A.U8C2.08, A.U24.65, A.U27.14, A.U35.23, M.SPEC.156.
- **Blast carried by**: CLAUDE.md heapsize bullet → A.U36.546/A.U8.15 (DOCS).
- **Kind**: doc

### M.SPEC.080 E.4: the fakes' boundary, their contract and counters
- **From**: A.U4.06 (filesystem and SCD30 NVM write counters), A.U24.17 (one contract suite for both tiers' fakes),
  A.U24.18 (stand-ins offer only their real class's surface, checked), A.U24.26 (fakes cite their port facts and state
  gaps), A.U24.78 (fault queue follows the twin's convention), A.U0.44 L60 (`:2952`, `:2954`), A.U10.38/A.U16.05 (names:
  `FRAMManager`, `RegionBuffer`).
- **Site**: `SPECIFICATION.md:2936-2962`.
- **Change**: (1) "real `AsyFramManager`" → "real `FRAMManager`"; the `print_log.py` history sentence ("This caught a real
  gap during `print_log.py`'s review: `_write()`/`_read()` called buffer methods *before* their `try:` block started —
  fixed by widening both to cover the whole body.") goes (G9/R11). New paragraph: "Both tiers' fakes (`tests/machine.py`,
  `digital_twin/machine.py`) pass one shared contract suite; each cites the rp2 port fact it models and states its gaps;
  a stand-in offers only its real class's surface (checked), and fault injection takes the twin's queue convention. The
  fakes count every filesystem write and every SCD30 NVM write, so a test asserts the writes it spends." (2) `:2952`
  "**The allocator is the one other sanctioned mocking surface**" → "**The allocator is the one other mocking surface
  (agent, 2026-09-13, `a1bf976`)**"; `:2954` "a deliberately generous multiple" → "a generous multiple".
- **Resolved**: — (no conflict among the constituents)
- **Unit**: Stage 1 U0 ((2)); Stage 2 U4 (counters); Stage 3 U24 (contract, surface, port facts, fault queue); U36 ((1)
  history).
- **Depends**: A.U4.06, A.U24.17, A.U24.18, A.U24.26, A.U24.78.
- **Blast carried by**: `digital_twin/README.md` fidelity notes → A.U24.17/A.U25.01 (TWIN).
- **Kind**: doc

### M.SPEC.081 E.5, E.5.1, E.5.2, E.5.3: coverage
- **From**: A.U36.526 (1) (E.5 body), A.U24.72 (traced sets; host-chain report; the tracer's false-negative classes),
  A.U28.15 (Codecov and the Cobertura XML go), A.U7.20 (coverage outputs archived), A.U24.05 (an incomplete file fails),
  A.U35.41 (E.5.1 rewritten to what stays; the unreachable-branch convention), A.U16.05 (`LockableBuffer` → `RegionBuffer`
  in E.5.1), A.U18.17 (the UDP `POLLERR` arm needs no E.5.1 entry), A.U15.21/A.U15.38/A.U16.23/A.U18.41/A.U35.42 (verdicts
  carried in A.U35.41's table), A.U1.06/A.U17.04 (cite E.5.1; no edit), A.U27.12 (E.5.2 probe and callers), A.U36.512 (3)
  (`:3059`, `:3066` "variant"), A.U21.12 (a third binary), A.U24.42 (cites E.5.2), A.U7.03 (`:3100` Result text), A.SDEP.02
  (cites E.5.3), A.U36.548 (G9/R11).
- **Site**: `SPECIFICATION.md:2964-3101`.
- **Change**: (1) E.5 body (`:2970-2983`) → A.U36.526 (1)'s text verbatim, plus "the coverage outputs move into the
  evidence archive (E.1)" and A.U24.05's "a file that does not reach microtest's exit fails the run". (2) E.5.1: first
  paragraph (tracer artifacts) stays and gains A.U24.72 (3)'s classes as facts ("lines the `sys.settrace` line event
  never reports — a multi-line statement's continuation lines, `else:`/`finally:` headers, a `const()`-folded line,
  `pass` in some shapes — each listed with its example as confirmed on `build-settrace`"); then A.U35.41's convention
  paragraph verbatim ("A branch no input can reach is removed. It stays only as a guard of an overridable extension
  point or of a documented runtime failure; such a guard is exercised through a double …, or, when no test can provoke
  it, listed in E.5.1 with its reason. (owner, 2026-09-26) A re-check that only narrows an `Optional` for the type checker
  stays, with a comment saying so (agent, 2026-09-30)."); the dead-code register (`:2994-3029`) → one line per entry A.U35.41's
  table keeps (keep / keep registered untestable / keep as type narrowing), each with its reason and the current names
  (`RegionBuffer.buf`, `FRAMManager`) — no narrowing entry for the webserver's `_apply_settings_groups()`, whose
  `isinstance()` unwrap goes once `handle_set_cmd()` returns the per-field result (M.SRC_NET.120, M.SRC_CORE.072; GAPS_G2
  H-5 (c), gap pass G1); entries the table removes leave the text, and "That pass left **31 genuinely
  uncovered lines across 8 files**, all of which now have tests — the register above is what remains, not a backlog."
  goes (dated count, G9/R11); the `finally:` paragraph stays, its "Two more were found exactly that way in the 2026-09-22
  pass" → "`WifiService`'s `_locked_wlan_status()` and `_get_hotspot_stations()` release `wifi_mode_lock` in a `finally`;
  both have cancellation tests". (3) E.5.2: "measured false on 2026-09-18, after an earlier note in this repo claimed it
  was" → "(measured 2026-09-18)"; "builds **two** Unix-port variants rather than one (owner decision, 2026-09-21)" →
  "builds `build-standard` without the flag and `build-settrace` with it (owner, 2026-09-21), plus `build-lwip` (B.2)";
  "**The build directory's path no longer identifies its variant.**" bullet → "**A build directory's name does not
  identify its build flavour**: an older toolchain directory may hold a `build-standard` that carries the flag, so every
  runner asks the binary itself through `scripts/_unix_port.sh` (`hasattr(sys, "settrace")`, `import lwip`, `import
  asyncio`) and rebuilds or fails on a mismatch; CI's cache key covers the same inputs (B.10)"; the second bullet holds.
  (4) E.5.3: the quoted `Result: TESTS PASSED, COVERAGE RENDERING FAILED` → "the summary block's `Result: PASS (coverage
  report not rendered)` (E.10)"; the incident sentence "It happened — `scripts/test.sh --coverage` exited 1 on 2026-09-22
  … and CI would never have said so." keeps its dated fact as the evidence behind the split.
- **Resolved**: A.U24.72 writes E.5's classes "itself" and A.U36.526 rewrites E.5 in U36 — the classes are placed in
  E.5.1 with the other tracer artifacts (U24), and A.U36.526's body (U36) does not repeat them.
- **Unit**: Stage 1 U7 ((1) archive, (4)); Stage 2 U24 ((1) incomplete file, (2) classes); Stage 3 U27 ((3) probe); Stage
  4 U35 ((2) register and convention); Stage 5 U36 ((1) body, (3) wording).
- **Depends**: A.U7.03, A.U7.20, A.U24.05, A.U24.72, A.U27.12, A.U28.15, A.U35.41, A.U36.526.
- **Blast carried by**: README "Test coverage" and CLAUDE.md coverage bullet → A.U36.526 (2)-(4) (DOCS).
- **Kind**: doc

### M.SPEC.082 E.6 to E.6.5: the level ladder, adapters, the harness, role reversal, overlap
- **From**: A.U7.01 (E.6.1 → "The level ladder (L0-L4)"; vocabulary), A.U36.007 (the not-levels sentence), A.U36.009
  (E.6.3: no GC-instrumented image), A.U7.24 (E.6.2's "not an automated check" goes; the containment test), A.U7.25 (E.6.2's
  persistence/IRQ/random-walk exclusion removed), A.U7.18 (runners run every lower level first), A.U7.14 + A.U27.19 (E.6.3:
  the verdict reads the run record; a caller's `-m` narrows), A.U26.31 (hardware levels collectible with nothing
  attached), A.U25.01 (E.6.5 points to the fidelity table), A.U26.44 (device-script convention: board facts from `BENCH`),
  A.U0.44 L61 (`:3108-3109`, `:3190-3191`), A.U36.548 (G9/R11); OR139.a (1)-(5) (the rollover round on the tick-offset
  test image) (A-C review fold).
- **Site**: `SPECIFICATION.md:3103-3193`.
- **Change**: (1) E.6 intro: `:3108-3109` "— don't force further sharing onto genuinely backend-specific coverage." →
  "— further sharing is not forced onto genuinely backend-specific coverage (agent, 2026-09-04, `8080538`)."; the
  `tests_hardware/` paragraph uses the level names (L3 flash, L4 bench); "Both tiers run clean end to end on real
  hardware; the earlier WiFi-reconnection flakiness this section used to flag is root-caused and mitigated" → "L3 and L4
  run end to end on the bench (`tests_hardware/README.md`'s 'Known assumptions and open findings')"; new sentence: "Every
  L3/L4 module is collectible with nothing attached under every option, checked at L0." (2) E.6.1 → A.U7.01's level
  table and its containment paragraph verbatim, followed by A.U36.007's slot text; the "**Credential rotation is
  deliberately not a bench capability** (owner decision, 2026-09-22)" paragraph keeps its decision and reason, its tag
  as "(owner, 2026-09-22)", without
  "The harness carried … zero call sites, so the table above claimed a fault nothing ever injected" (G9/R11). (3) E.6.2:
  "flash/bench" → "L3/L4"; "What stays out: mock's raw byte/frame assertions, twin's persistence/IRQ/random-walk
  behavior, real-hardware-only electrical/timing checks." → "What stays out: L1's raw byte/frame assertions and
  real-hardware-only electrical/timing checks; a twin scenario without an L3/L4 counterpart is a row of E.6.6.";
  "Documentation discipline (…), not an automated check." → "Each L3/L4 module names the twin scenarios it covers
  (`COVERS_TWIN_SCENARIOS`), checked by `tests_scripts/test_level_containment.py`." (4) E.6.3: appended A.U36.009's
  sentence; new: "A hardware run's verdict reads its run record, never a grep of its output; a `-m` the caller passes
  narrows the runner's own selection, never replaces it." (5) E.6.4: "bench" → "L4" where it names the level. (6) E.6.5:
  "Six subsystem pairs scanned in full: … (166 mock vs. 18 twin tests) …" keeps its finding with level names; `:3190-3191`
  gains "(agent, 2026-09-04)"; new: "How faithful each twin fake is: `digital_twin/README.md`'s fidelity table. A device
  script takes every board fact from `BENCH`, one rendered dict (`tests_hardware/`)." (7) E.6.3 gains (A-C review
  fold): "**The tick rollover on silicon** is one round on the tick-offset test image (B.14.5), whose tick and 32-bit
  millisecond counts wrap about 15 minutes after boot: the rollover runner flashes it — one flash cycle, counted in the
  round's budget — polls for about two hours with the standard health verdicts, and the next round flashes its own
  image; the driven-clock proofs at L1 and L2 stay the per-commit proof (owner, 2026-10-01)."
- **Resolved**: — (no conflict among the constituents)
- **Unit**: Stage 1 U0 ((1), (6) tags); Stage 2 U7 ((2) table, (3), (4) run record); Stage 3 U25/U26 ((6) pointers, (1)
  collectible); Stage 4 U27 ((4) `-m`; (7) with the rollover runner M.SCR.074, after M.SPEC.162's U21 subsection);
  Stage 5 U36 ((2) slot, (4) A.U36.009, history; "B.14.5" → "B.14.4" with M.SPEC.162).
- **Depends**: A.U7.01, A.U7.14, A.U7.18, A.U7.24, A.U7.25, A.U25.01, A.U26.31, A.U26.44, A.U27.19, A.U36.007, A.U36.009,
  M.SPEC.162, M.SCR.074 (the runner, as the fold amends it).
- **Blast carried by**: README hardware table → A.U7.01/A.U36.008 (DOCS); `tests_hardware/README.md` → A.U7.18/A.U26.* (HW);
  the rollover round in `tests_hardware/README.md` → M.HW_BENCH.126.
- **Kind**: doc

### M.SPEC.083 E.6.6: the one level-containment exception list
- **From**: A.U7.25 (E.6.6 → the table, rows 1-10), A.U4.07 (the SCD30 text correction runs first; no row), A.U0.38 V03/V31
  /V33 (carried by A.U7.25's rows 1 and 3), A.U36.028 (`uart-fault-catalog` wording), A.U36.045 (`bmp3xx-general-call`),
  A.U26.28 (boot-failure code row), A.C.12 (replaces it with the silicon attempt's result), A.U26.39 (`hotspot-multi-client`),
  A.U26.34 (recovery rungs without L3/L4), A.U26.56 (off-subnet spoof attempt result), A.U26.51 + M_PROC gap 2 (rows for
  twin scenarios without a counterpart; `COVERS_TWIN_SCENARIOS`), A.U35.21 (lone BMP3XX row is L4 only — A.U36.045),
  A.U26.86 (THR wording; no SPEC edit beyond A.U36.028), A.U36.512 (3) (`:3213` "variant"), M_HW_DEV (`sgp40-general-call`
  no L4, A.U7.25 row 2); OR140.a (18) (no device but `dev` is special; WoZi-specific wording goes) (A-C review fold).
- **Site**: `SPECIFICATION.md:3195-3237` (E.6.6).
- **Change**: heading "### E.6.6 Level-containment exceptions"; the opening rule paragraph keeps the owner's standing rule
  with "(owner, 2026-09-26)" and A.U7.01's containment wording, "C.8 is an instance of this rule"; the four numbered
  exceptions become one table `| ID | Scenario/behaviour | Missing level(s) | Reason | Decided | Reviewed at close |`
  read by `tests_scripts/test_level_containment.py`, with rows: `dev-only-bench` (owner, 2026-09-03), its Reason the
  general rule — "only `dev` has a bench board; every other device is built and tested alike and proven at L0-L2" (no
  device but `dev` has a role of its own, owner, 2026-10-02) — citing CLAUDE.md's `dev` rule, never the HEAD text's
  "WoZi is the exemplary/base variant" entry; `sgp40-general-call`
  (owner, 2026-09-26); `uart-fault-catalog` in A.U36.028's wording ("no injection hardware will be bought, and a second raw
  `machine.UART` is never used as a stand-in; on silicon the flash level covers silence and a baud mismatch", owner,
  2026-09-22); `ws2812-no-readback`; `human-only`; `twin-instrument` (one row per twin-only file, A.U7.24's first run;
  `unix_port_gc_unwedge` leaves with the helper's retirement, A.U25.39); `off-subnet-spoof` (owner, 2026-09-28; its
  Reason states phase C's attempt result, A.U26.56); `scd30-rdy-irq-vs-fallback` and `scd30-non-finite-words` (owner,
  2026-09-25); `fram-write-protect-no-rest` (agent, 2026-09-15); `bmp3xx-general-call` (A.U36.045, agent, 2026-09-30);
  `hotspot-multi-client` ("multi-client load in hotspot mode: one bench radio", owner, 2026-09-22 — no purchase);
  `boot-failure-code` (A.U26.28's row until A.C.12's attempt: a reset code the attempt reached leaves the table, one it
  could not returns with the recorded result); one row per recovery rung without an L3/L4 entry (A.U26.34); one row per
  twin scenario A.U26.51's search left without a counterpart, each with its reason. "**Out of scope entirely**" paragraph
  stays.
- **Resolved**: (a) A.U7.25 row 3's "until injection hardware exists" is overtaken by A.U36.028's "no injection hardware
  will be bought" (owner, 2026-09-22, A40). (b) "SCD30 has zero REST-pushable fields" (HEAD exception 2) is false
  (A.U4.07) — no row. (c) A.U26.28's boot-failure row and A.C.12's silicon attempt: A.C.12 replaces the row with its
  result (A.C.12 says so).
- **Unit**: Stage 1 U7 (table, rows 1-10); Stage 2 U26 (rows A.U26.28/.34/.39/.51); Stage 3 phase C (A.C.12, A.U26.56
  results); Stage 4 U35/U36 (A.U36.045, A.U36.028 wording, close review).
- **Depends**: A.U4.07, A.U7.24, A.U7.25, A.U26.28, A.U26.34, A.U26.39, A.U26.51, A.U26.56, A.U36.028, A.U36.045, A.C.12.
- **Blast carried by**: references to E.6.6's numbered items (BACKLOG, `tests_hardware/README.md`, two test files) →
  A.U7.25 repoint (DOCS/HW); C.8's exception text → M.SPEC.065.
- **Kind**: doc

### M.SPEC.084 E.7 and E.8: soak timing; measurement traps
- **From**: A.U36.512 (3) (`:3253` "dev variant"), A.U24.64 (E.7/E.8 already state the rate rule), A.U36.012 (E.8 heap-figure
  scope bullet), A.U3.08 + A.U2.20 (E.8 `:3348-3350`), A.U0.40 L16 (`:3372-3375`), M_TEST_UNIT GAP-U10 (E.8 "48 checks, 96
  tests … Two are single-mode"), M_TEST_HELP GAP-H5 + A.U36.544 (E.8 gains the platform-print sentence), A.U0.37 V38 (E.8? no:
  `:3379` is E.9's rule sentence), A.U36.548 (G9/R11).
- **Site**: `SPECIFICATION.md:3242-3375`.
- **Change**: (1) E.7: "Measured on the dev variant (2026-09-11)" → "Measured on the `dev` device (2026-09-11)"; the
  soak history (`run_dev_integration.py` "since retired") keeps only the dated measurement and its two consequences. (2)
  E.8: after the first bullet, A.U36.012's bullet verbatim ("**A heap figure counts only with its scope written beside
  it** …"). (3) The `ErrNum` bullet → "**A fault persists its errno; a resync prints**, and only a drain-bound resync
  persists `wrnno` 54 — so the newest UART entry is the fault's own code (C.7.1)." (4) New bullet (A.U36.544): "`micropython.
  mem_info(1)` prints through the platform print, not `sys.stdout`, so a heap map cannot be captured in-process." (5)
  `:3372-3375` → "**Every hazard check runs in both CRC modes (agent, 2026-09-12, `dc970fb`).**
  `tests/test_uart_comm_hazard.py` registers each `_check_*` twice (`_nocrc`, `_crc16`) — <N> checks, <2N> tests, with
  <k> single-mode by construction (`_MODE_SPECIFIC`), because their subject is one configuration. The dev wiring selects
  `CRCPass`; no UART device is in the field." — N and k as `tests/test_uart_comm_hazard.py` registers them at landing
  (GAP-U10: four single-mode checks after M.TEST_UNIT.319/.325, plus the new checks of M.TEST_UNIT.319-.322).
- **Resolved**: GAP-U10 — a count in text drifts; the executor writes the landed counts (or the sentence names the
  mechanism without counts, agent's preference per OR43.a (3)). A.U0.40 L16 and GAP-U10 edit the same sentences — one
  text.
- **Unit**: Stage 1 U0 ((5) tag and CRC sentence); Stage 2 U3 ((3)); Stage 3 U17/U24 ((5) counts at the landing that
  changes them); Stage 4 U36 ((1), (2), (4)).
- **Depends**: A.U3.08, A.U36.012, A.U36.544, M.TEST_UNIT.319-.325.
- **Blast carried by**: `HEAP_FRAGMENTATION_MEASUREMENTS.md` header → unchanged (DOCS).
- **Kind**: doc

### M.SPEC.085 E.9: driver/DUT separation; the host-side scenario harness
- **From**: A.U25.46 (E.9 names the harness), A.U27.38 (both runners drive it), A.U25.74 (the twin runner's named,
  off-by-default `--test-…` flags), A.U31.06 (`--test-loop-lag-ms` among them), A.U26.68 (device scripts emit facts; the
  host test gives the verdict), A.U27.17 + A.U35.27 (Run 11's verdict on one attempt; window and tolerance calibrated
  against a planted leak), A.U30.17 (4) (`:3400`), A.U0.37 V38 (`:3379` rule tag), A.U17.18 (no change), A.U36.548 (G9/R11),
  M.SCR.017 (port-53 scenarios), M_SCR gap 5.
- **Site**: `SPECIFICATION.md:3377-3433`.
- **Change**: (1) `:3379` rule sentence gains "(owner, 2026-09-25)". (2) The first-findings list: "**The Run 11
  memory-trend soak itself** used to drive … Moved entirely host-side (2026-09-14)" → "**The Run 11 memory-trend soak**
  drives every request over real HTTP from the CPython suite (`scripts/_digital_twin_ci_suite.py`'s `_run_11_soak()`)";
  "(I.4(e)'s own narrow, separately-litigated exception)" → "(I.4(e)'s one twin exception)". New paragraph: "**The
  host-side L2 scenario harness** (`scripts/_digital_twin_scenarios.py`) is this rule's general form: each scenario boots
  the device's generated graph in a fresh twin and drives it over HTTP, reading only the runner's stdout and its named
  `--test-…` flags — off by default, the runner's one instrumentation exception (owner, 2026-09-30), e.g.
  `--test-loop-lag-ms`. `scripts/test.sh` runs it per derived device with the scenarios that need an exclusive port 53
  deselected and listed; `scripts/run_digital_twin_ci.sh` runs every scenario, one twin at a time, holding port 53. A
  device script emits facts; its host test gives the verdict." (3) The trend-tolerance paragraph (`:3412-3433`): its
  mechanism (autocorrelated samples; tolerance from each attempt's own quarter spread) stays; "`_run_11_soak()` also
  retries once — a second fully independent clean boot — before failing on the trend check specifically, …" → "The verdict
  is decided on one attempt, with the window and tolerance calibrated against a planted leak (Part N rows); if that
  calibration cannot bound one attempt's noise, the verdict fails and the retry question goes to the owner." The
  "Real GitHub-runner CI kept tripping … (2026-09-14) … 3298/2854 and 4361/2847 bytes" history keeps only its dated
  measurement as the reason.
- **Resolved**: — (no conflict among the constituents)
- **Unit**: Stage 1 U0 ((1)); Stage 2 U25 ((2) harness); Stage 3 U26 (device-script sentence); Stage 4 U27 ((2) both
  runners, (3)); U30 ((2) exception wording); U31 (flag); U35 ((3) calibration).
- **Depends**: A.U25.46, A.U25.74, A.U26.68, A.U27.17, A.U27.38, A.U30.17, A.U31.06, A.U35.27, M.SCR.017.
- **Blast carried by**: `digital_twin/README.md` flag table and CI-suite text → A.U25.74/A.U27.17 (TWIN).
- **Kind**: doc

### M.SPEC.086 New E.10: the runner summary block and exit codes
- **From**: A.U7.02 (the block and its rules), OR133 / AC_NOTES 43 (owner: every runner, `test.sh` included, exits 2 on a
  usage or setting error, no exception), M.SCR.035 (`test.sh`'s exit 2), A.U7.03 (per level; codes 0/1/3), A.U7.08
  (pytest tier through a run record), A.U7.10 (`npm test` ends with the block), A.U7.13 (hardware runs write a run
  record), A.U36.525 (CLAUDE.md's verdict rule points here), M_SCR gap 5.
- **Site**: new `## E.10 The runner summary block` after E.9 (`:3433`), before Part F.
- **Change**: A.U7.02's E.10 text — the block (`== Summary: <runner> ==` … `Exit code: <n>`) and its rules (counted unit
  named; retried and recovered passes apart from `passed`; a missing or empty per-item verdict counts as failed;
  `vacuous` > 0 forces FAIL; `Exit code:` equals the real exit status) — with the exit codes stated firm: "**Exit codes**:
  0 — every item passed; 1 — an item failed or an allocation-failure marker was seen; 2 — a usage or setting error (an
  unknown option, a missing or invalid argument, environment value or heavy-file list), in every runner, `scripts/test.sh` included, with
  no exception (owner, 2026-10-01); 3 — `scripts/test.sh --coverage` only: every test passed and only the coverage
  rendering failed (`Result: PASS (coverage report not rendered)`, E.5.3); 4 — NOT CLEAN, a run that cannot be read as
  clean. A usage error prints the usage line on stderr." and the emitters: "`scripts/_summary_block.sh` and
  `scripts/_summary_block.py` print byte-identical layouts (checked); `tests_js/_summary_reporter.js` prints the same for
  `npm test`; the backgrounded pytest tier and every hardware run write a run record the summary reads. A gate's verdict
  is its exit status or this block, never a truncated view of its output (`| tail`, `| head`)." A.U7.02's sentence
  listing "today's divergent sites: `test.sh:34, :47, :53` exit 1" is not written — OR133 settled them (M.SCR.035).
- **Resolved**: A.U7.02 flagged `test.sh`'s exit 1 sites to the lead; the owner answered SCR Q1 with (a) (OR133): firm,
  no "pending" marker (owner, 2026-10-01; M.SCR.035/.045 apply it to `test.sh`, a bad heavy-file list included).
- **Unit**: U7 (the block and codes; `test.sh` adopts exit 2 in the same unit, M.SCR.035).
- **Depends**: A.U7.02, A.U7.03, A.U7.08, A.U7.10, A.U7.13, M.SCR.035.
- **Blast carried by**: CLAUDE.md verdict bullet → A.U36.525 (DOCS); README sample block → A.U7.03 (DOCS); H.8 JS tier →
  M.SPEC.124.
- **Kind**: doc

## SPECIFICATION.md — Part F (`:3435-4146`)

Every Part F text below names upstream sources at HEAD's `v1.29.0` as its constituents state them; per C3 the executor
re-stamps each version token and re-verifies each `file:line` at the pin in force when the text lands (A.SDEP.08 (4)
runs that re-check in full at U0; M.PROC.031 repeats it at U37 if a release appeared). A runtime fact that A.SDEP.17's
re-read (W18-W28, W37-W40, W42; M.PROC.011) finds flipped at the new tag is rewritten in the change below that carries
it; an unflipped fact keeps the text given here.

### M.SPEC.087 Part F opens with the platform re-check; the one statement of the practice
- **From**: A.U36.023 (1) (the opening checklist), A.SDEP.21 (2) (item (9), the standing-workaround list), A.U26.65 +
  M_DOCS gap 1 (d) (the checklist names `tests_hardware/README.md`'s Workarounds table; M.DOCS.070), A.U14.23 + A.U1.19 +
  M_DOCS gap 1 (c) (BACKLOG item 3's surviving fact; M.DOCS.063), A.SDEP.08 (4) (runs the list in full), A.U37.04 (1)
  (Part F is the one home of platform facts — a check, no text), A.U36.031 (Part 0's P4 cites "Part F's opening
  checklist"); OR142.a (2) (MicroPython's two bundled sites re-read at every bump) (A-C review fold).
- **Site**: `SPECIFICATION.md:3435-3437` (new paragraphs between `# Part F` and `## F.1`); `:3597-3602` (F.1's closing
  paragraph, the same practice restated).
- **Change**: (1) A.U36.023 (1)'s paragraph verbatim, with two amendments: its first sentence reads "Every MicroPython
  fact in this Part is a fact of the pinned tag (`toolchain/versions.toml`'s `[micropython] ref`; its owner rule, F.1)."
  and it opens with the sentence moved from `:3597-3598`: "Current MicroPython and Microdot documentation and source are
  checked before asserting how an API behaves — never training-data memory."; item (9) reads "(9) every standing
  workaround listed in F.9 and every row of `tests_hardware/README.md`'s Workarounds table, at each pin move and at every
  dependency refresh" (F.9 is M.SPEC.003's number for A.SDEP.21's "F.5.10"); and (A-C review fold) the list gains "the
  two dynamic-import sites in MicroPython's bundled modules that F.1 records (the `asyncio` lazy loader and
  micropython-lib's `dht.py`), re-read for any new one in what the image freezes (owner, 2026-10-05)". (2) A second paragraph (M_DOCS gap 1 (c),
  A.U14.23's corrected fact re-stamped to the pin): "The toolchain builds the `RPI_PICO_W` firmware at the pin from
  scratch without editing the MicroPython tree; its out-of-tree changes are the build overrides of
  `toolchain/micropython_overrides.py` (B.14) and the GCC ≥ 14 array-bounds workaround (B.7.1)." (3) `:3597-3602`
  deleted: both its practices are now (1); its `getaddrinfo()` example goes with it (A.U36.023 (2): nothing in `src/`
  calls it, F.2).
- **Resolved**: (a) A.U36.023 and A.U0.33 C05 both tag the pin's owner-only move "(owner, 2026-09-26)"; one tag, in
  F.1's version sentence, which lands at U0 (M.SPEC.088); the intro points there. (b) BACKLOG item 3 leaves at U37
  (M.DOCS.063): its legacy-version decision is F.1's sentence (A.U1.17, M.SPEC.088), its "no tree edits" fact is (2);
  A.U14.23 names "F.5's intro", but F.5 is rewritten per pin move (A.SDEP.21 (2)) and the intro is the standing home —
  agent decision, OR2.c review. A.U14.23's sentence on the 1.27→1.28 rp2-port commits is not carried: a fact about two
  superseded tags (C2) that F.5's record of the pin no longer needs — agent decision, OR2.c review. (c) The practice
  stated twice in Part F (intro and `:3597-3602`) → once.
- **Unit**: Stage 1 U21 ((1) items 1-9 without the Workarounds-table clause, (2), (3); A.U21.02's notice text is the
  first to cite "Part F's checklist", C6; the dynamic-import item with them, F.1 listing the two sites since U10);
  Stage 2 U26 (item (9)'s Workarounds-table clause, once A.U26.65 creates the table).
- **Depends**: A.SDEP.21 (F.9 exists, U0), A.U0.33 (F.1 tag), A.U21.02, A.U26.65, M.SPEC.088, M.SPEC.089, M.SPEC.109.
- **Blast carried by**: CLAUDE.md "Platform target" pointer and "Last run" line → M.DOCS.070 (DOCS); BACKLOG item 3's
  removal → M.DOCS.063 (DOCS); A.U21.02's notice wording → TOOL; Part 0 P4's pointer → M.SPEC.002.
- **Kind**: rule, doc

### M.SPEC.088 F.1 opening paragraph: the legacy units, the pin, pico-sdk/picotool, the watchdog cap, the hardware; which stores wear
- **From**: A.U1.17 (`:3439`, `:3442`), A.U0.33 C05 (`:3441-3442`), A.U14.24 + A.U21.05 (`:3443-3444`), A.U14.09
  (`:3447-3450`), A.U36.006 (new paragraph), A.U32.01 (the runbook's place), M_DOCS gap 1 (c) (item 3's decision),
  A.U8.08/A.U8.02 (the cap's source and the `wdt.timeout_ms` row).
- **Site**: `SPECIFICATION.md:3439-3450`; new paragraph after `:3450`.
- **Change**: (1) `:3439-3443` → "The owner's legacy units run **MicroPython 1.24.1** with the legacy firmware
  (`legacy/firmware/`) and stay on it until the owner reflashes one (README.md, "Moving a legacy unit to this
  firmware"); no fact verified at the pin is extrapolated to 1.24.1. The refactor runs on **Pico W (RP2040)** from
  **frozen bytecode**, not loaded from a filesystem at runtime — CPython-only stdlib behaviour cannot be assumed. It
  pins **<pin>** (`toolchain/versions.toml`), which stays pinned to a chosen version that moves only on the owner's call
  (owner, 2026-09-26), and uses that version's features rather than reproducing legacy behaviour. F.5 records what the
  pin changed for this codebase." (2) `:3443-3444` → A.U14.24's sentence with A.U21.05's picotool clause in place of its
  "must match that major.minor or the build fails": "The pin bundles pico-sdk as its `lib/pico-sdk` submodule at
  <commit> (version <X.Y.Z>, `lib/pico-sdk/pico_sdk_version.cmake`); pico-sdk accepts a standalone `picotool` of its own
  major version and at least its `picotool_VERSION_REQUIRED` (<v> at the pin), so <v> or a later same-major release
  builds and an older same-major one or another major fails (pico-sdk `tools/CMakeLists.txt:<lines>`; picotool
  `CMakeLists.txt:<line>`); `toolchain/versions.toml` pins only the MicroPython ref and derives both (B.3)." — the
  executor reads every bracketed value from the pinned clones (A.U0.03's corpus at U14, the refreshed pin's at U21). (3)
  `:3445-3446` → "`machine.WDT` hard-caps at **8388 ms** (`ports/rp2/machine_wdt.c:32-38`); the boot entry arms 8000 ms
  (Part N `wdt.timeout_ms`, a 388 ms margin) — not raised without re-checking the cap." (4) USB sentence unchanged; A.U14.09's
  hardware text replaces "RP2040: dual-core … 8×PIO." verbatim; the littlefs sentence stays. (5) A.U36.006's "**Which
  stores wear.**" paragraph verbatim after `:3450`.
- **Resolved**: (a) A.U1.17's legacy sentence ends "(the reflash runbook)"; A.U32.01 (U32) names its place — U32's text
  wins. (b) A.U14.24 vs A.U21.05 on the picotool clause: A.U21.05's rule (same major, at least the required version)
  replaces A.U14.24's "match major.minor", as A.U21.05 states; A.U14.24's version facts stay. (c) A.U0.33 C05 and A.U1.17
  both rewrite `:3441-3442`: one sentence carrying C05's owner tag and A.U1.17's "legacy behaviour". (d) The WDT sentence's
  source and Part N pointer are a gap fill from A.U8.02/A.U8.08's cited cap (agent decision, OR2.c review).
- **Unit**: Stage 1 U0 (C05 tag); Stage 2 U1 ((1) legacy wording); Stage 3 U8 ((3) Part N pointer, once the row exists);
  Stage 4 U14 ((2) version facts, (4)); Stage 5 U21 ((2) picotool clause); Stage 6 U32 (runbook name); Stage 7 U36 ((5)).
- **Depends**: A.U1.02 (legacy paths), A.U0.03, A.U8.08, A.U32.01, A.U16.11 (cites the same endurance figures).
- **Blast carried by**: SPEC B.1/B.3 picotool text → M.SPEC.025, M.SPEC.027; `toolchain/versions.toml:3-5` comment and
  `derive_picotool_ref()` docstring → A.U21.05 (TOOL); README hardware summary pointing to F.1 → A.U14.09 (DOCS);
  CLAUDE.md wear rule → A.U0.37 (DOCS); C.8's "volatile per their datasheets" source → M.SPEC.065.
- **Kind**: doc

### M.SPEC.089 F.1 imports: the static-import rule and its named exceptions; `.frozen`; extensible built-ins; `const()`
- **From**: A.U0.40 L11 (`:3452-3453` tag), A.U0.07 (the rule, the named exceptions, the shrinking pending list, the
  check), A.U10.30 (the named dynamic loads), A.U25.42 (b) (the twin HTTP client's lazy import), M_HW_BENCH GAP-B4 (the
  by-path `exec()` moves to `digital_twin/run_device_script.py`), A.U37.02 (the pending list goes; per-import `# noqa:
  PLC0415`), A.U36.036 (`.frozen` paragraph), A.U14.10 (4) (the `.gitignore` restamp, folded into A.U36.036 (4)),
  A.U20.03 + A.U25.58 + A.U32.02 (extensible built-ins and their proof), A.U14.27 (`const()`), A.U10.29 (blast);
  OR141.a (2) and OR142.a (1)-(3) (the ban's scope is the code in an image; the named host and test exceptions and
  MicroPython's two bundled sites; no loader is rewritten), A.U10.30's loader rewrite (`tests/_generated_module.py`,
  the ISL29125 test's `import time`) dropped (OR141.a (2)) (A-C review fold).
- **Site**: `SPECIFICATION.md:3452-3457`, new paragraph after it, `:3526-3529`.
- **Change**: (1) `:3452-3457` → "**Every import is a static `import`/`from … import` statement at module top**
  (agent, 2026-09-09, `3847c71`), AST-scannable without executing code — what lets a build derive a device's module set
  from the closure of real imports. **No code this project writes, generates or vendors into an image imports
  dynamically**: `src/`, `ext/` and the generated boot, device and website modules have no `__import__` or `importlib`
  — no site in any of the six devices' images at the pin — and the import check enforces it per image
  (owner, 2026-10-05). Outside the image, these host and test sites load by path or by name and are the only
  exceptions, each with its reason, kept in `tests_scripts/test_import_placement.py`'s `_NAMED_EXCEPTIONS`; the check
  fails on any site not listed, and the owner judges every listed one harmless (owner, 2026-10-05):
  `tests_scripts/_script_loader.py` (a `scripts/` file by path); `tests_scripts/conftest.py` (sets the path that loader
  relies on; names `importlib` in a comment); `tests_scripts/test_buildgen_validate.py` (a test of the named loader in `buildgen/validate.py`);
  `tests_scripts/test_js_coverage_report_dir.py` (names `importlib` in a docstring; reads import statements by AST);
  `buildgen/validate.py` (loads `toolchain/micropython_overrides.py` by path: it is no package);
  `digital_twin/run_generic_integration.py` (the module its device config names); `tests/_boot_contiguity_probe.py`,
  `tests/_digital_twin_construction_scenarios.py`, `tests/_sensortask_scenarios.py` and
  `tests/_webserver_concurrency_scenarios.py` (a device module by its derived name); `tests/test_asy_isl29125_driver.py`
  (`__import__("time")` inside two test statements); `ext/freezefs/ffsextract.py` (vendored, build-time only; its
  extract mode is never used). Executing a file by path (`exec`) is not an import: ruff's S102 and its per-file
  ignores govern it, not this list.
  **MicroPython's own bundled modules are platform code, never edited**, and carry two sites recorded here as platform
  facts: `extmod/asyncio/__init__.py:29` (v1.29.0), the lazy loader that imports a submodule on first use of `Lock`,
  `Event`, `wait_for`, `gather` or `start_server`, and micropython-lib's `dht.py:14`, frozen by the board manifest and
  never imported by this project; both are re-read at every MicroPython version bump (Part F's opening checklist;
  owner, 2026-10-05). `digital_twin/_http_client.py`'s function-level `_strict_json` import (`tests/` is absent from a
  twin process's path) is the one named function-level import there. Each remaining function-level import carries an
  inline `# noqa: PLC0415` with its reason. `importlib` is not frozen into this project's manifest; the rule holds
  regardless." — every listed path and line is re-grepped at landing (the list is the set `test_import_placement.py`
  holds then; the owner's list of 2026-10-05 is its content). (2) A.U36.036 (1)'s "**`.frozen` is MicroPython's import
  sentinel, never a directory.**" paragraph verbatim, followed by A.U20.03's sentence: "An extensible built-in
  (`MP_REGISTER_EXTENSIBLE_MODULE`: `machine`, `time`, `os`, `json`, `socket`, `select`, `struct`, `errno`,
  `collections`, …) is looked up on `sys.path` before the built-in (`py/builtinimport.c:404-416`), so a filesystem file
  of that name shadows it on any path entry; the boot entry's `.frozen`-first line protects the frozen product modules
  only (proved on the Unix port by `tests_scripts/test_frozen_first_shadowing.py`), and the reflash runbook's filesystem
  erase covers the built-ins." (3) `:3526-3529` → A.U14.27's "**An `_`-prefixed `micropython.const()` name is not a
  module attribute** …" text verbatim (its float sentence goes to M.SPEC.091).
- **Resolved**: (a) A.U0.07's Stage-1 text says "the named exceptions and a pending list that only shrinks"; A.U37.02
  deletes "pending list" at U37 — the text above is the end state. (a.1) OR141.a (2)/OR142.a supersede A.U10.30's
  rewrite of the device-module loaders through `tests/_generated_module.py` and of the ISL29125 test's `__import__`:
  no loader is rewritten, the HEAD sites are the list, and the ban's scope is the code in an image (A-C review fold).
  (b) A.U10.30 named `tests_hardware/isl29125_conformance.py:35`; M.HW_BENCH.038/.091 move that by-path `exec()` into `digital_twin/run_device_script.py` (GAP-B4) —
  an `exec` is not an import, so neither it nor the two `tests/` exec runners is on the list: S102 governs them (lead
  ruling, A-C review fold). (c) A.U25.42 (c) repeats A.U10.30's twin dynamic load — one entry. (d) A.U36.036's
  "a same-named `.py` earlier on the path wins over a frozen module" (the default path) and A.U20.03's boot entry putting
  `.frozen` first are both true: the first is the interpreter's default, the second the product's boot entry — kept
  adjacent so neither reads as contradicting the other.
- **Unit**: Stage 1 U0 (A.U0.40 tag; A.U0.07's rule and pending list); Stage 2 U10 (the scope sentence, the named
  list and the two platform sites, with the import check that enforces them, OR142.a); Stage 3 U14
  ((3)); Stage 4 U20 (A.U20.03 sentence); Stage 5 U25 (A.U25.42 (b); A.U25.58's proof name); Stage 6 U26 (none
  left: GAP-B4's exec is S102's, not the list's); Stage 7 U36 (A.U36.036 paragraph); Stage 8 U37 ("pending list" goes).
- **Depends**: A.U0.07, A.U10.30 (its check only, narrowed to `__import__`/`importlib`; the rewrite dropped), A.U14.10, A.U20.03, A.U25.42, A.U25.58
  (M.TSC.093), A.U28.33, A.U36.036, A.U37.02, M.HW_BENCH.038, M.HW_BENCH.091; M.TSC.098 (the per-image check
  failing on an unlisted `__import__`/`importlib` site).
- **Blast carried by**: A.9/E.3 `.frozen` pointers → M.SPEC.022/M.SPEC.078; `.gitignore` parenthesis → A.U36.036 (4)
  (M.PROC.019 (6), PROC — `.gitignore` is PROC's, gap pass G1); `pyproject.toml` PLC0415 entries → A.U37.02 (TOOL); the check's exception set → GAP-B4 (TSC); README
  frozen-code sentence → A.U32.02 (DOCS).
- **Kind**: rule, doc

### M.SPEC.090 F.1 timers and the bus raise surface
- **From**: A.U10.14 (F.1 keeps the drop fact and points to C.9), A.U0.25 A48 (`:3465-3467` owner tag), A.U26.58 (the
  probe the drop fact cites), A.U14.12 (1) (alarm pool, finaliser), A.U10.45 (`(MemoryError, OSError)`), A.U14.14 (new
  paragraph: what rp2's buses raise), A.U25.19 (the twin pool takes F.1's value; blast), A.C.03 (4)/A.C.10 (the silicon
  count beside F.1).
- **Site**: `SPECIFICATION.md:3459-3467`, `:3494-3497`, new paragraph after `:3497`.
- **Change**: (1) `:3459-3467` → "**A soft `machine.Timer` callback (the default — no `hard=True` anywhere) can be
  silently dropped, not just delayed** — `mp_sched_schedule()` drops it when the scheduler queue (depth 8 on rp2, shared
  by every soft timer and IRQ) is full, with no exception and no way to tell a dropped callback from one not yet run
  (`py/scheduler.c`, at the pin); proven on silicon by the scheduler-drop probe (`tests_hardware/device_scripts/<A.U26.58's
  script>`). What follows from it — a callback only sets a flag, every timer that must fire is `PERIODIC` — is C.9's. A
  software-timeout mitigation was considered and rejected by the owner (owner, 2026-07-18, `f3924e1`/`af24a01`: 'brittle
  wrt. wdt timeout settings')." The hotspot-shutoff example (`:3463-3465`, silicon 2026-09-25) moves to C.9 with the
  `PERIODIC` rule (M.SPEC.066 amended). (2) `:3494-3497` → A.U14.12 (1)'s paragraph verbatim (`<N>` and the pico-sdk
  `file:line` read at execution), its closing sentences written "catch `(MemoryError, OSError)` wherever both are
  plausible" (A.U10.45's order), plus, once phase C has run, "(silicon: <n> free alarms constructed with the image's other
  default-pool users, <date>)" (A.C.03 (4), A.C.10). (3) A.U14.14's "**What rp2's buses raise, and what they answer
  instead**" paragraph verbatim after it.
- **Resolved**: (a) A.U10.14 strips F.1's soft-callback text to the platform fact; A.U0.25's owner tag on the rejected
  mitigation stays in F.1 (the rejection concerns the drop, a platform fact). (b) A.U14.12 leaves the pool size unasserted
  until the corpus is read; A.U25.19's twin pool uses this value (16 until then) — the F.1 number is the source both read.
- **Unit**: Stage 1 U0 (A48 tag); Stage 2 U10 ((1) strip, (2) tuple order); Stage 3 U14 ((2), (3)); Stage 4 U26 (probe
  name); Stage 5 phase C (silicon count).
- **Depends**: A.U0.03, A.U10.14, A.U10.45, A.U14.12, A.U14.14, A.U26.58, A.C.03, M.SPEC.066.
- **Blast carried by**: C.9 `PERIODIC` rule and widening tag → M.SPEC.066; C.12's fault-injection sentence → M.SPEC.070;
  C.3/D.2 per-bus pointers → M.SPEC.048/M.SPEC.074; Timer and I2C fakes → A.U24/A.U25 (TEST_HELP, TWIN); CLAUDE.md
  `:647` Timer-GC wording → M.DOCS.099 (sentence deleted).
- **Kind**: doc

### M.SPEC.091 F.1 numbers, bytes and JSON
- **From**: A.U0.39 L21 (`:3502` tag), A.U14.27 (float freezing sentence), A.U1.17 (`:3507` legacy path), A.U24.58 +
  G4/R12 State (the bytearray store truncation fact, no owning SPEC text — gap fill), A.U31.19 (3) (floats are heap
  objects; `sleep()` multiplies), A.U14.11 (json's omitted value), A.U14.10 (3) (`int()` of inf/NaN), A.U10.27 (the
  `json.dumps()` fact stays; its rule lands in C/G), A.U11.09/A.U12.14 (the byte-order rule covers persisted formats — no
  edit).
- **Site**: `SPECIFICATION.md:3499-3524`, `:3574-3595`.
- **Change**: (1) `:3502` "— accepted, since no real schema field's bounds go near it" → "— accepted (owner, 2026-08-24,
  `3986be9`), since no real schema field's bounds go near it"; the paragraph gains A.U14.27's float sentence ("Float
  constants are folded in double on the host by `mpy-cross` and rounded to single precision once …") and A.U31.19 (3)'s
  sentence ("rp2 uses the default object representation, so every float result is heap-allocated; `asyncio.sleep(t)` and
  `asyncio.wait_for(aw, t)` both multiply `t` by 1000 (`extmod/asyncio/core.py:61-63`, `funcs.py:24-34`)"). (2) `:3507`
  `dev_legacy/asy_bsec_driver.py` → `legacy/dev_drivers/asy_bsec_driver.py`. (3) After the `struct.pack()` paragraph, one
  sentence: "**A `bytearray` item store keeps the low byte**: `b[i] = n` stores `n & 0xFF` without raising
  (`py/binary.c:512-521`), where CPython raises `ValueError`; a float raises `TypeError`." (4) The `json.loads()`
  paragraph gains A.U14.11's text after its example. (5) The `json.dumps()` paragraph gains, after "`math.log(0)`)",
  A.U14.10 (3)'s "; `int()` of an infinite float raises `OverflowError` and of NaN `ValueError` (`py/objint.c:143-152`)".
- **Resolved**: (a) the truncation fact is cited by three code comments (A.U24.25, A.U24.58, A.U25.21, A.U9.06) as SPEC
  F.1's, but no action writes it — gap fill (agent decision, OR2.c review). (b) A.U31.19's fact sits with the float
  facts, where the "heap float" premise is stated; D.4's rule cites it (M.SPEC.074).
- **Unit**: Stage 1 U0 ((1) tag); Stage 2 U1 ((2)); Stage 3 U14 ((1) float sentence, (3)-(5)); Stage 4 U31 ((1) sleep
  sentence).
- **Depends**: A.U1.02, A.U14.10, A.U14.11, A.U14.27, A.U31.19.
- **Blast carried by**: `tests/test_config_manager.py`/`tests/_strict_json.py` comments → A.U14.11 (TEST_HELP/TEST_UNIT);
  the response writer's non-finite rule → A.U10.27 (M.SPEC.111); comments citing the truncation fact → A.U24.58/A.U25.21
  (TEST_UNIT, TWIN).
- **Kind**: doc

### M.SPEC.092 F.1 time and stack: the tick horizon, the wall clock, the C stack
- **From**: A.U14.32 (tick paragraph), A.U35.32 + M_PROC gap (M.PROC.024: the wrap run's sentence), A.U36.544 item 12
  (`soft_reset()`/`mpremote exec` sentence), A.U14.33/A.U14.34/A.U15.35/A.U17 `_holdoff_active` (the fixes that make the
  sentence true; blast), A.U14.25 (new wall-clock paragraph), A.U14.26 (the seven comments that point to it; blast),
  A.U10.06 + A.U6.21 (`utc_now()` and the pre-sync `UtcTime`; blast), A.U30.18 (4) (new C-stack paragraph), A.U30.19
  (its closing sentence, reset code 20); OR139.a (the silicon rollover on the tick-offset image), F21 tag form
  (c-stack-reboot) (A-C review fold).
- **Site**: `SPECIFICATION.md:3531-3537`; two new paragraphs after it.
- **Change**: (1) `:3531-3537` → A.U14.32's text: its replacement of the "`ticks_diff()` is correct …" sentence and of the
  closing "cannot empirically exercise …" sentence verbatim, the latter followed by M.PROC.024's "Wrap safety was run once
  on a 2**30-period Unix build started just before the wrap (agent, <date>)." then (A-C review fold) "On silicon the
  rollover round's tick-offset test image crosses the tick wrap and the 32-bit millisecond wrap about 15 minutes after
  boot (B.14.5, E.6.3)." and A.U36.544 item 12's "`machine.soft_reset()`
  does not zero the counter (free-running hardware time); an `mpremote exec` stops `main.py`, so nothing feeds the
  watchdog and the hard reset about 8 s later does (bench, 2026-09-11)." (2) A.U14.25's "**The wall clock runs as unsigned
  32-bit seconds since 1970, valid to 2106, and only after an NTP sync.**" paragraph verbatim, its last sentence's "(the
  divergence list below)" written "(F.7)" and its "a wall-clock value is used or published only once `ntp_issynced()` is
  true" naming the primitive: "… only through `utc_now()` (`None` until the first sync, G.2)". (3) A.U30.18 (4)'s
  "**C stack.**" paragraph with the facts its Why records: "**C stack.** 8 KB (`PICO_STACK_SIZE=0x2000`,
  `ports/rp2/CMakeLists.txt:661`), with the check on (`MICROPY_STACK_CHECK` follows the ROM level, `py/mpconfig.h:812-814`;
  rp2 builds the extra-features level, `ports/rp2/mpconfigport.h:80-81`): the limit is the linker's stack extent minus
  the 256 B margin (`ports/rp2/main.c:78, 148`, `ports/rp2/mpconfigport.h:125`, `py/cstack.h:38-43`) = 7,936 B, and
  crossing it raises `RuntimeError("maximum recursion depth exceeded")` (`py/cstack.c:50-55`, `py/runtime.c:1784-1787`).
  Every resumed task re-enters its whole await chain in C, so the budget is the longest await chain times the per-level
  cost: the longest chain is <n> levels (<path>), pinned by `tests_scripts/test_await_depth.py`; measured on the `dev`
  board at <bytes> peak (<date>, image <sha>), within half the limit (agent, <date>; owner-reviewed, 2026-10-02). A
  stack-check error is recorded by
  the handler that catches it (`report_if_fatal()`, G.2) and the supervisor reboots (reset code 20, A.8)."
- **Resolved**: (a) A.U14.32 lands at U14 but states a property U15/U17's tick fixes make true — the sentence lands with
  or after them (A.U14.32 Depends); A.U35.32's run sentence lands at U35 with its date (M.PROC.024). (b) A.U14.25 says
  "published only once `ntp_issynced()`"; A.U10.06 (U10) makes `utc_now()` the one primitive — the landed text names it
  (C7). (c) A.U30.18 (4) wrote "[facts above]"; its Why's v1.29.0 facts are the text.
- **Unit**: Stage 1 U14 ((1) A.U14.32 text, after A.U14.33/.34; (2)); Stage 2 U30 ((3); its measured clause in phase C);
  Stage 3 U35 (M.PROC.024 sentence and the fold's silicon-rollover sentence, both after U27's runner and M.SPEC.082
  (7)); Stage 4 U36 (A.U36.544 item 12 sentence; "B.14.5" → "B.14.4").
- **Depends**: A.U10.06, A.U14.33, A.U14.34, A.U15.35, A.U17 tick fix (`_holdoff_active`), A.U30.18, A.U30.19, A.U35.32,
  M.PROC.024, M.SPEC.107, M.SPEC.111, M.SPEC.128 ((d.1) cites this paragraph).
- **Blast carried by**: `tests/test_ticks_rollover.py` docstring/comment → A.U14.32 (TEST_UNIT); the seven wall-clock
  comments → A.U14.26 (SRC_*); `tests_hardware/flash/test_bus_electrical_timing.py` pointers → A.U36.544 (HW_DEV); the
  `/status` `UtcTime` row → M.SPEC.021; I.4 (d.1) → M.SPEC.128; `report_if_fatal()` entry → M.SPEC.111.
- **Kind**: doc

### M.SPEC.093 F.1 asyncio and network facts
- **From**: A.U14.18 (nested `asyncio.run()` mechanism), A.U14.15 (new list "asyncio as this code relies on it"),
  A.U19.07 (the list gains `readexactly(n < 0)`), A.U14.19 (the list names its guard), A.S0930.18 + A.S0930.30 (the
  forwarded-cancel fact, "cited once"), A.U31.18 + A.U31.19 (no `asyncio.wait_for()` left in `src/`), A.U25.39 (the twin
  comment cites F.1 for what `asyncio.run()` catches — gap fill), A.U36.544 item 5 (UDP on rp2/lwIP) and its
  `digital_twin/network.py:137` item (`WLAN.status()`), A.SDEP.17 W18-W20/W27/W39/W40 (conditional).
- **Site**: `SPECIFICATION.md:3539-3555`, `:3569-3572`; new paragraphs after `:3548` and before F.2.
- **Change**: (1) `:3541-3542` → A.U14.18's F.1 sentence verbatim. (2) After `:3548`, A.U14.15's paragraph verbatim with
  two further items: "`readexactly(n)` with `n < 0` reads everything, then raises `MemoryError`" (A.U19.07) and
  "cancelling a task that awaits another task forwards the cancel to the awaited one (`extmod/asyncio/task.py:164-166`),
  so cancelling a server's task closes its listening socket (`stream.py:141-142, 149-159`)" (A.S0930.18). (3) `:3550-3553`
  "every stream write wraps in its own `asyncio.wait_for()`" → "every stream write wraps in its own
  `asyncio.wait_for_ms()`"; the rest of the paragraph stays. (4) `:3569-3572` gains, after its first sentence, "(`run()`
  catches only `CancelledError` and `Exception`, `extmod/asyncio/core.py:<lines>`)". (5) Before F.2, A.U36.544 item 5's
  "**UDP on rp2/lwIP** (bench, 2026-09-08): …" paragraph verbatim, then its `WLAN.status()` sentence: "`WLAN.status()`
  returns the link status as an int; `status('rssi')` (STA only) an int; `status('stations')` (AP only) the list of
  connected stations; any other query raises `ValueError` (`extmod/network_cyw43.c:357-392`)."
- **Resolved**: (a) A.S0930.30 places the forwarded-cancel fact in "F.5"; it is no 1.29 delta (`task.py`'s forwarding is
  older) and A.U36.532 files standing facts by topic — the asyncio list is its home, cited once by A.8's sequence text
  (agent decision, OR2.c review). (b) A.U25.39's twin comment cites "SPECIFICATION.md F.1, asyncio.run() catches only
  CancelledError and Exception", a clause F.1 does not hold — (4) adds it, the executor verifying the `core.py` lines
  (agent decision, OR2.c review). (c) A.SDEP.17's W18 (nested run may raise at the new tag), W19 (async generators),
  W20 (starred displays, `await` in comprehensions), W39 (`json.loads()` separators) and W40 (`readexactly()`
  re-concatenation): each changes its F.1 sentence only when the re-read finds it flipped (M.PROC.011).
- **Unit**: Stage 1 U14 ((1), (2) without the two added items); Stage 2 U19 (`readexactly`); Stage 3 U25 ((4), with
  A.U25.39's comment); Stage 4 U31 ((3)); Stage 5 U36 ((5); the forwarded-cancel item with A.S0930.30's docs pass).
- **Depends**: A.U14.15, A.U14.18, A.U14.19, A.U19.07, A.U25.39, A.U31.18, A.S0930.18, A.U36.544.
- **Blast carried by**: CLAUDE.md segfault bullet → M.DOCS.099 (DOCS); `asy_ntp_client.py`/`system_service.py` comments →
  A.U14.15 (SRC_NET/SRC_CORE); the bench and test comments pointing to the UDP fact → A.U36.544 (HW_BENCH, TEST_UNIT);
  `digital_twin/network.py:137` pointer → A.U36.544 (TWIN); A.8's sequence text citing the fact → M.SPEC.021.
- **Kind**: doc

### M.SPEC.094 F.2 heading, the ladder rule, what can be timeout-wrapped, the `MemoryError` pointer
- **From**: A.U14.R01 (1)-(2), A.U0.37 V08 (`:3606-3608` owner tag), A.U0.22 (the "Settled." wording; BACKLOG goal),
  A.U14.16 (`getaddrinfo()` traced), A.U10.26 + M_DOCS gap 1 (a) (the one timeout mechanism, built; M.DOCS.062), A.U31.18
  (the webserver's three waits use it), A.U30.01 (2) (`:3614-3615` → I.4(a) pointer), A.U0.38 V09 (`:3614-3615`,
  superseded), A.SDEP.17 W27 (conditional), A.U36.023 (2) (the `getaddrinfo()` example leaves CLAUDE.md).
- **Site**: `SPECIFICATION.md:3604-3615`.
- **Change**: (1) Heading → "## F.2 Blocking calls and the recovery ladder". (2) `:3606-3608` → A.U14.R01 (2)'s paragraph
  verbatim (its closing "(a stalled chip may still reach a reboot, owner, 2026-09-25)" is A.U0.37 V08's owner quote). (3)
  `:3608-3612` → A.U14.16's text up to "is fixed since v1.28.0." (the executor names the fix commit only after opening the
  upstream PR), then, in place of its last sentence: "**One timeout mechanism**: a wait that genuinely can be bounded is
  wrapped in `asyncio.wait_for_ms(<awaitable>, <timeout_ms>)` around the single awaitable that can wait
  (`extmod/asyncio/funcs.py:24-55`), the timeout a caller parameter in milliseconds and a timeout mapped to the owning
  function's documented sentinel (agent, 2026-09-29) — `asy_udp_socket.py`'s `select.poll`-driven `ready()` (and so
  `write_and_recvfrom()`), the FRAM presence check's bus-lock wait and the webserver's per-call waits. The FRAM's other
  bus-lock waits and its status-byte sequences carry none: they wait only on other coroutines of this program. A single
  `machine.I2C` or `machine.SPI` transfer is synchronous and cannot be wrapped: the ladder acts once it returns, and one
  that never returns is the watchdog's." (4) `:3614-3615` → A.U30.01 (2)'s "**Which calls catch `MemoryError`**:
  I.4(a)."
- **Resolved**: (a) A.U14.16 (U14) writes "are to share one mechanism, not yet built (BACKLOG)" and lists "bus-lock
  acquisition, the FRAM status-poll sequence" as wrappable; A.U10.26 (U10, earlier) built the mechanism and closed the
  FRAM sequences as needing none — A.U10.26's design is the text, A.U14.16's stale clause and its BACKLOG pointer are not
  written (M_DOCS gap 1 (a)). (b) A.U0.37's "Settled." → owner-tag rewrite (U0) is superseded at U14 by A.U14.R01's
  paragraph, which keeps the same owner quote. (c) A.U0.38 V09 and A.U30.01 rewrite `:3614-3615`: A.U30.01's pointer is
  the end state (its criterion lands once, in I.4(a)); V09's U0 wording stands until U30. (d) W27: if the new tag adds an
  asyncio-level timeout to `getaddrinfo()`, (3)'s first sentence records it; no code change (M.PROC.011).
- **Unit**: Stage 1 U0 (V08 tag, V09 wording); Stage 2 U10 ((3)'s mechanism sentence in place of "should standardize on
  one mechanism"); Stage 3 U14 ((1), (2), (3) A.U14.16 text around the U10 sentence); Stage 4 U30 ((4)); Stage 5 U31 (the
  webserver clause, once A.U31.18 lands).
  A-C2 step order: A.U14.R01's part lands in U18, not U14 (it needs A.U18.R01, which lands in U18).
- **Depends**: A.U0.22, A.U0.37, A.U10.26, A.U14.16, A.U14.R01, A.U30.01, A.U31.18.
- **Blast carried by**: CLAUDE.md wedged-bus rule → M.DOCS (A.U14.R01 (4), A.U0.22); BACKLOG non-blocking goal and the
  removed "share one mechanism" item → M.DOCS.062/.065; `tests_hardware/README.md:633` issue list → A.U14.16 (HW_BENCH);
  I.4(a) criterion → M.SPEC.128.
- **Kind**: rule, doc

### M.SPEC.095 F.2 the I2C recovery ladder per sensor, the boot clear, live reconnect, each rung's tests
- **From**: A.U14.R01 (3), A.U14.17 option (a) (OR113, AC_NOTES 15: the boot clear), A.U14.38 (owner rule and proof),
  A.U25.59 (the L2 proof), U26's LEAD/R29 manual step (the L4 proof), A.U36.046 + A.U35.52 (each rung's tests), A.U13.R01,
  A.U10.R01, A.U15.R01-R05, A.U16.R01-R03, A.U18.R01 (the rungs; blast), A.U20.08 (every bus constructed before any
  instance; the clear its first act), A.U36.531 (the operator's power-cycle line; DOCS).
- **Site**: `SPECIFICATION.md:3617-3623`.
- **Change**: `:3617-3623` → A.U14.R01 (3)'s paragraph verbatim, with: (a) after "every I2C bus is cleared once at boot
  before its controller is constructed" the clause "(constructing `machine.I2C` drives no SCL pulses of its own,
  `ports/rp2/machine_i2c.c:110-118`, so a watchdog reset or `machine.reset()` frees a held SDA through this clear)"; (b) after
  "recovered by these rungs without a reboot when it is back before the restart budget runs out, as for every declared
  chip" the proof clause "(proven at L2 by `<A.U25.59's test>` and by the manual L4 step `<U26's step>`; the FRAM
  likewise)"; (c) after each rung, A.U36.046's one line "(tested: <L1 file::test>, <L2 …>, <L3 …>, <L4 …> or "not
  reachable at <level>: <reason>")" from A.U35.52's table — test names, never line numbers.
- **Resolved**: (a) A.U14.17 waited on Q-I2C; the owner chose the boot clear (a) (OR113, 2026-09-30) and set the standing
  principle "recover with the smallest possible blast radius … also in mid operation", so A.U14.17 (a)'s "once per bus at
  boot, never at runtime (OR64.a (2))" is overtaken by A.U14.R01's runtime clear rung; A.U14.17 (a)'s separate F.2
  paragraph is not written — its one surviving fact is clause (a), and its power-cycle sentence is already R01's. Option
  (b)'s text is dropped. (b) A.U14.38's owner-rule head is already R01's ("Hot-unplug/replug is a kept feature: 'Live bus
  reconnect must be preserved' (owner, 2026-07-13)") — one statement; its proof sentence is (b).
- **Unit**: Stage 1 U14 (R01 text, (a)); Stage 2 U25/U26 ((b) names, once both tests exist; until then the sentence
  carries only the owner rule, as A.U14.38 says); Stage 3 U36 ((c), after A.U35.52).
- **Depends**: A.U10.R01, A.U13.R01, A.U14.17, A.U14.38, A.U14.R01, A.U15.R01-R05, A.U16.R01-R03, A.U18.R01, A.U20.08,
  A.U25.59, A.U35.52, A.U36.046.
- **Blast carried by**: DEVICE_REFERENCE.md power-cycle line → A.U36.531 (M.DOCS); BACKLOG held-SDA hardware row →
  A.U14.17 (M.DOCS owed list); `digital_twin/README.md:543-544` and `BACKLOG.md:199` wording → A.U14.R01 blast (TWIN, DOCS);
  C.3/C.7/C.8 rung texts → M.SPEC.048, M.SPEC.058, M.SPEC.065; F.8.2's backstop sentence → M.SPEC.108; Part N
  `i2c.clear_half_period_us` → M.SPEC.156.
- **Kind**: rule, doc

### M.SPEC.096 F.2 the WiFi false positive, flash writes and the power-loss window
- **From**: A.U14.R01 blast (d) (`:3625` head), A.U0.33 B02 (`:3628-3631`), A.U18.28 (`:3635-3636`), A.U26.30 (the
  power-cycle backstop as a judged trade-off; CLAUDE.md/README), A.U36.033 (`:3638-3658`), A.U0.33 C01 (`:3653-3658`,
  absorbed), A.U11.04 + A.S0930.14 + A.S0930.30 + A.S0930.33 + A.S0930.41 (the commanded-reset sentence), A.C.17 (the
  silicon power-cut result), A.U36.034 (CLAUDE.md flash-write rule cites this), A.U0.34 (BACKLOG item 4 cites F.2),
  A.SDEP.17 W28 (conditional: upstream state of the false positive); OR136.a (1) (an absent config file is written once
  with its defaults) (A-C review fold).
- **Site**: `SPECIFICATION.md:3625-3658`.
- **Change**: (1) `:3625` "**The same backstop applies to a WiFi link …**" → "**The watchdog/power-cycle backstop also
  covers a WiFi link stuck in a CYW43-firmware-level false positive**"; `:3628-3631` per A.U0.33 B02 ("**Investigated, no
  `src/` change**: the owner judged a reachability probe not worth its complexity (owner, 2026-09-04, `655e4f9`,
  paraphrase; confirmed 2026-09-26) — …"); `:3635-3636` per A.U18.28 ("a selected AP not reporting it is re-activated
  only if inactive and counts as having no client (cyw43 `cyw43_lwip.c:300-323`)"). (2) `:3638-3658` → A.U36.033's
  "**Flash writes and this backstop.**" paragraph verbatim except its write-path clause and its commanded-reset
  sentence. The write-path clause reads (A-C review fold): "and only on an accepted PUT that changed a value, in at most
  one repair per boot of an existing, readable config file (C.7.3; owner, 2026-09-26), once with the schema defaults
  when a config file is genuinely absent — a fresh flash, a filesystem erase or "Reset to defaults" (owner,
  2026-10-01) — or when the `SystemCmd` `"resetconfig"` deletes every config file before its reboot (owner,
  2026-09-30)"; "Neither the PUT write nor the repair runs inline in a request" → "Neither the PUT write nor a boot write
  runs inline in a request". The commanded-reset sentence ("A write accepted before
  a commanded reset or a shutdown command is on flash when the reset fires — … a write arriving in the reset's last
  milliseconds is refused (A.4).") → A.S0930.41's: "A write accepted before a system command closes the config stores is on
  flash when the reset fires; one arriving after is refused; after the supervisor's own reboot decision, a write accepted
  inside the 4 s window is flushed at the reset; a hung shutdown step ends in a watchdog reset (A.8)." Once phase C has
  run, the residual-window sentence gains A.C.17's result: "(silicon, <date>: <n> power cuts during a config write, each
  boot loading a valid file)".
- **Resolved**: (a) A.U0.33 C01's two edits (`:3653`, `:3656-3658`) are absorbed by A.U36.033's text, keeping its owner
  tag (A.U36.033 says so). (b) Four constituents write the commanded-reset sentence: A.U11.04 (U11, "one arriving in its
  last milliseconds is refused"), A.S0930.30 (the two shutdown commands), A.U36.033 (both), A.S0930.41 (all four commands
  run the sequence, the supervisor's own reboot flushes inside its 4 s window) — A.S0930.41's is the end state (OR126).
  (c) A.C.17 replaces no text: it adds the dated silicon result to the sentence it tests.
- **Unit**: Stage 1 U0 (B02, C01 edits); Stage 2 U11 (A.U11.04's sentence); Stage 3 U14 ((1) head, R01 blast (d));
  Stage 4 U18 (A.U18.28); Stage 5 U36 ((2) A.U36.033 with A.S0930.41's sentence); Stage 6 phase C (A.C.17 result).
  A-C2 step order: A.U14.R01's part lands in U18, not U14 (it needs A.U18.R01, which lands in U18); A.S0930.14's part lands in U20, not U11 (it follows A.S0930.14's own change, which lands in U20); A.S0930.33's part lands in U20, not U11 (it follows A.S0930.33's own change, which lands in U20).
- **Depends**: A.U0.33, A.U11.04, A.U11.19, A.U11.28, A.U14.R01, A.U18.28, A.U36.033, A.S0930.09-.17, A.S0930.30,
  A.S0930.41, A.C.17; M.SRC_CORE.043 (the absent-file write, as the fold amends it).
- **Blast carried by**: CLAUDE.md CYW43 and flash-write bullets → A.U36.034, A.U26.30 (M.DOCS); BACKLOG item 4 → A.U0.34/
  A.U36.035 (M.DOCS); C.7.3's repair text → M.SPEC.061; A.8's shutdown text → M.SPEC.021; `tests_hardware/README.md`
  CYW43 issue list (W28) → HW_BENCH.
- **Kind**: rule, doc

### M.SPEC.097 F.3 the timing budget table
- **From**: A.U31.01 (the consumer and budget tables, the Part N row), A.U31.02 (the lead names the recomputing test),
  A.U31.03, A.U31.05, A.U31.06, A.U31.07, A.U31.08 (row values and guards), A.U8.19 (the pointer sentence to
  `loop.sync_wait_max_us` and `loop.uart_call_span_max_us`), A.U0.40 L62 (`:3664-3667` tag), A.U16.07 (the hold-timing
  script cites `hold.fram_block`), A.U13.R01 (the runtime clear yields: `hold.recovery_rung`), A.S0930.24/.28
  (`feed.shutdown_step`), A.U33.07 (the owed row cites F.3), A.U9.04 (`:3663` unaffected), M_SRC_CORE GAP-1 (D.4's sleep
  exceptions read the `stall.sync_wait` row); OR141.a (4) (the UART receive ring absorbs a flash write's
  interrupts-off stretch: A.U31.01's `con.uart_fifo` crossing and A.U31 open point 2's accepted degradation are
  superseded), OR136.a (1) (the boot write of an absent file is a flash program), OR140.a (2) (the L4 console-starvation
  test runs only behind the persistence-write flag) (A-C review fold).
- **Site**: `SPECIFICATION.md:3660-3667`; the table between `<!-- timing-budget:begin -->`/`<!-- timing-budget:end -->`.
- **Change**: the principle paragraph stays; the retired-lock sentence gains "(agent, 2026-07-28)" (A.U0.40 L62); then
  A.U31.01 (1)-(3) verbatim — the lead paragraph, with A.U31.02's clause "the code-derived rows are recomputed by
  `tests_scripts/test_timing_budget.py`", the consumer table and the budget rows — followed by A.U8.19's sentence: "The
  deliberate synchronous waits in `src/` and the UART call span are rule rows of their own: Part N
  `loop.sync_wait_max_us` and `loop.uart_call_span_max_us` (the `stall.sync_wait` and `stall.uart_call` rows)." Each
  row's guard names the test file (and function where one exists) at execution; the Part N column names only IDs the
  register carries (A.U31.01's own rule). Three rows of A.U31.01's text change (A-C review fold): (i) the consumer row
  `con.uart_fifo` → "| `con.uart_rx_ring` (a device with a `uart_link`) | the receive ring's capacity at the line rate,
  sized to hold what the peer sends during the longest synchronous flash write under stop-and-wait (J.6) | the ring
  floor (J.6), `devices/dev.toml` | hard past the bound only: a lap is detected and handled as the receive overrun
  (J.7) |"; (ii) `stall.flash_program`: "only on an accepted PUT's deferred flush and the one boot repair" → "on an
  accepted PUT's deferred flush, the one boot repair and the one boot write of an absent file's defaults (C.7.3)";
  "consumers `con.uart_fifo` (crossed: a peer frame arriving meanwhile loses bytes and the link resyncs — accepted
  degradation, the receive-overrun fault class of J.7)" → "consumers `con.uart_rx_ring` (not crossed: the DMA ring
  receives with interrupts off, so no frame is lost, owner, 2026-10-05; proved on silicon without a flash write by the
  interrupts-off sweep device script)"; (iii) `stall.console`'s guard gains "and the L4 starvation test, run only
  behind the persistence-write flag (it spends 2 flash writes, debug level 0 and back to 5; owner, 2026-10-02)".
- **Resolved**: (a) A.U8.19's "F.3 gains one sentence pointing to both rows" and A.U31.01's rows `stall.sync_wait`/
  `stall.uart_call` name the same rows — one sentence after the table. (b) `hold.recovery_rung` ("each SCL wait bounded by
  the bus timeout and yielding every millisecond") matches A.U13.R01's runtime path; the boot clear runs synchronously
  inside the fed boot batch (`feed.boot_first`). (c) Values measured in phase C (`stall.flash_program`, `stall.voc_process`,
  `lag.loop`) carry "owed" until A.C.10's delta writes them. (d) A.U31 open point 2 (an erase overrunning the 32-byte
  FIFO accepted as one lost frame) is superseded by the owner's ruling (OR140 note, OR141.a (4), owner, 2026-10-05):
  the receive DMA ring takes the UART consumer off the crossing (A-C review fold).
- **Unit**: Stage 1 U0 (L62 tag); Stage 2 U8 (A.U8.19 sentence, rows' Part N IDs); Stage 3 U31 (the table, with the
  fold's three rows — the ring lands in U13, the absent-file write in U11, the gated console test's gate in U26, all
  earlier); Stage 4 phase C (measured cells; the interrupts-off sweep's result, C).
- **Depends**: A.U8.01, A.U8.19, A.U13.R01, A.U16.07, A.U17.27, A.U18.34, A.U31.01-A.U31.08, A.S0930.24, A.S0930.28,
  A.C.10, M.SPEC.156, M.SPEC.136 (J.6's ring floor); M.SRC_NET.221 (the ring), M.HW_DEV.159 (the
  interrupts-off sweep device script), M.HW_BENCH.082 (the gated console test, as the fold amends it).
- **Blast carried by**: Part N `fram.block_hold_budget_us` → M.SPEC.156; A.7/C.8/C.9.1/F.8.2/I.2/J.6 one-clause pointers to
  their rows → M.SPEC.020, M.SPEC.064, M.SPEC.067, M.SPEC.108, M.SPEC.126, M.SPEC.136; `tests_hardware/README.md` owed-row
  line → A.U31.01 (HW_BENCH); `tests_scripts/test_timing_budget.py` → A.U31.02 (TSC).
- **Kind**: rule, doc

### M.SPEC.098 F.4 the VOC reference, its successor and the one deliberate deviation
- **From**: A.U12.15 (F.4's Sensirion sentence), A.U12.11 (the helpers wrap to int32), A.U12.12 (the vector source),
  A.U12.13 (the uptime-limit deviation), A.U34.04 (successor and name map consistent), A.SDEP.10 (the upstreams read;
  no text), A.U0.40 L01 (C.2's tag on the literal-port rule; M.SPEC.047); OR141.a (3) (A-C review fold).
- **Site**: `SPECIFICATION.md:3669-3676`.
- **Change**: the Sensirion sentence gains A.U12.15's text verbatim; its "are pinned against it" names A.U12.12's vector
  source ("pinned against vectors from `<A.U12.12's source>`, `tests/<file>`"); its last sentence reads (A-C review
  fold): "The literal-port rule is agent design (agent, 2026-07-21), the named exception to the Adafruit rule; the port
  keeps upstream's names, casing and order, the one exception to the naming and member-ordering rules (C.2, D.15; owner,
  2026-10-05)."
- **Resolved**: A.U12.15's "the literal-port rule is agent design (agent, 2026-07-21)" and A.U0.40 L01's C.2 tag
  "(agent, 2026-08-11, `f27b33b`)" name two acts (the rule; C.2's casing exception) — both kept, each on its own text.
- **Unit**: U12.
- **Depends**: A.U12.11, A.U12.12, A.U12.13, A.U12.15.
- **Blast carried by**: `src/voc_algorithm.py` docstring → A.U12.15 (SRC_SENS); THIRD_PARTY chain → A.U34.04 (DOCS).
- **Kind**: doc

### M.SPEC.099 F.5 heading and intro: the record of the pin
- **From**: A.SDEP.21 (2) (heading, present-tense facts, new subsections), A.SDEP.08 (6) (the field-proven paragraph
  while silicon proof is owed), A.U1.17 (`:3686`), A.U1.19 (no item-3 pointer), A.U36.008 (`:3685` "mid soak duration"),
  A.U14.23 (if item 3 goes, its fact moves here — carried by M.SPEC.087 instead), A.C.10 (phase C restates the silicon
  proof), M.PROC.031 + M_PROC gap (the U37 second record), A.U36.548 (headings in present tense), M.PROC.011 (W-items).
- **Site**: `SPECIFICATION.md:3678-3690`.
- **Change**: (1) Heading → "## F.5 MicroPython at the pin (`<pin>`, audited <date>)". (2) The method sentence
  (`:3680-3681`) stays. (3) `:3683-3690` → while the pin moved at U0 and phase C has not run: "**Built and verified at
  L0-L2 at the pin; silicon proof owed (BACKLOG).**" (A.SDEP.08 (6)); after phase C: "**The pin is field-proven on the dev
  bench (<date>).** Real `dev` firmware built from `src/` and flashed; `sys.implementation` reports `(<x, y, z>)` /
  `_mpy=<n>` / `RPI_PICO_W`, with the flash level (<n> passed), the bench level (<n> passed) and the mid soak duration
  (<n> passed) clean against it." (A.U36.008's wording; A.C.10's delta writes the figures); "Deployed units stay on 1.26
  regardless (BACKLOG open question 3)." → "The legacy units stay on 1.24.1 until the owner reflashes one (F.1)."; the
  closing sentence on the three findings that wanted on-target confirmation keeps its F.5.1/F.5.2/F.5.3 references and
  its `device_scripts/fram_busy_status_lockout.py` pointer, re-checked against the new run. If the pin did not move at
  U0, (1) keeps HEAD's delta wording re-stamped to "audited <date>" and (3)'s HEAD paragraph stays with A.U36.008's and
  A.U1.17's wording edits only. (4) U37: if M.PROC.031 finds a newer release and the pin moves again, (1)-(3) are written
  once more against that pin (the second record replaces the first; C2).
- **Resolved**: A.U1.17 and A.U36.008 edit adjacent sentences of one paragraph that A.SDEP.08 (6) may replace — the
  wording edits apply to whichever text stands.
- **Unit**: Stage 1 U0 ((1), (3) owed form, if the pin moved); Stage 2 U1 (legacy sentence); Stage 3 U36 (A.U36.008
  wording); Stage 4 phase C (field-proven form); Stage 5 U37 (M.PROC.031, conditional).
- **Depends**: A.SDEP.08, A.SDEP.21, A.U1.17, A.U36.008, A.C.10, M.PROC.031.
- **Blast carried by**: CLAUDE.md `:17` and "Last run" → M.DOCS.070; BACKLOG owed row for the pin → A.SDEP.08 (6)/A.SDEP.21
  (4) (M.DOCS owed list).
- **Kind**: doc

### M.SPEC.100 F.5.1 bus `deinit()` no-ops and the re-construction rule
- **From**: A.U14.04 (the re-construction bullet), A.U13.R01 blast (controller re-init sentence), A.U13.16 (`deinit()`
  returns bool, cannot raise — consistent), A.U24.26 (fakes cite F.5.1), A.SDEP.17 W26 (conditional).
- **Site**: `SPECIFICATION.md:3702-3708` (the "no way to release" bullet).
- **Change**: the bullet gains A.U14.04's text verbatim, then A.U13.R01's sentence: "Re-construction is also the only
  controller re-init rp2 offers — `machine.I2C.init()` raises `OSError` (`extmod/machine_i2c.c:320-326`) — and a real
  one: pico-sdk's `i2c_init()` resets the whole I2C block first (F.2's controller rung)." The `I2C.deinit()` 1.29 floor
  bullet keeps its version wording (the floor is the fact, A.SDEP.21 (2)). If W26 finds rp2 now sets the `.deinit` slot or
  stops returning static singletons, the section is rewritten to the new fact as a U13/U14 delta with its phase-C check
  (M.PROC.011).
- **Resolved**: — (no conflict among the constituents)
- **Unit**: Stage 1 U13 (A.U13.R01 sentence); Stage 2 U14 (A.U14.04).
- **Depends**: A.U13.R01, A.U14.04, M.SPEC.095.
- **Blast carried by**: wrapper construction and device scripts passing the TOML's `timeout` → A.U14.04/A.U26 (HW_DEV);
  `@requires` tags → M.SPEC.149; fakes' citations → A.U24.26 (TEST_HELP).
- **Kind**: rule, doc

### M.SPEC.101 F.5.2 the SPI RX overrun: mechanism, reach, the no-retry decision
- **From**: A.U14.21 (mechanism), A.U36.548 (1) (history wording; heading), A.U2.09 + A.U2.23 (the errno), A.U3.04
  dropped (OR140.a (7): "the one entry" goes), A.U16.14 (comment cites F.5.2), M_DOCS gap 1 (c) (BACKLOG's "SPI RX
  overrun is not retried" entry leaves at U37; M.DOCS.065) (A-C review fold).
- **Site**: `SPECIFICATION.md:3724-3760`.
- **Change**: heading → "### F.5.2 rp2 SPI reads can raise `OSError(EIO)`" (A.U36.548 (1), unless A.SDEP.21 (2) has
  restated F.5's headings — then its form); `:3726-3728` → A.U14.21's mechanism text; `:3749-3750` → "**It does not
  reach the reader task.** Driving the fault through" (the rest of the sentence stays); "logging errno 47" → "logging
  it at each layer that meets it (the catalog's codes, C.7, C.7.1)"; "So no retry is added (owner decision, 2026-09-24): the
  dual-copy layer already covers the read path." → "So no retry is added (owner, 2026-09-24): the dual copy absorbs a
  transient overrun — `_read_chunk()` logs it and `_read()` falls back to block 1 and repairs block 0 — so a retry inside
  the chunk loop would buy little."
- **Resolved**: M_DOCS gap 1 (c): BACKLOG's deferred entry restates F.5.2's decision with its reason; the reason joins
  F.5.2's owner-tagged sentence, so the entry can leave with nothing lost. Its "Don't re-propose it" is not the owner's
  words (OR71.a (0)) and is not carried.
- **Unit**: Stage 1 U2 (errno renumber); Stage 2 U3 (the per-layer wording, with C.7's paragraph); Stage 3 U14
  (mechanism); Stage 4 U36 (wording, heading, BACKLOG reason).
- **Depends**: A.U2.09, A.U14.21, A.U36.548, M.SPEC.058.
- **Blast carried by**: BACKLOG `:474-477` removal → M.DOCS.065; `tests/test_fram_integration…` comment → A.U16.14
  (TEST_UNIT); BACKLOG `:476` errno → A.U2.09 (DOCS).
- **Kind**: doc

### M.SPEC.102 F.5.3 the SRAM placement cost, the heap headroom, `-fno-math-errno`
- **From**: A.U0.25 A18 (`:3783-3785` tags), A.U0.33 T1 (`:3780-3790` placement sentence), A.U30.09 (`:3788-3791` loaded
  floor from `MemFree`), A.U11.08 + A.U6.22 (blast: `MemFree` exists), A.U14.35 (`:3792-3794`), A.C.03 (4) (the flash-tier
  heap figures on the named image), A.U36.548 (history wording).
- **Site**: `SPECIFICATION.md:3762-3794`.
- **Change**: (1) `:3783-3785` "the owner retired its 100,000 B free / 80,000 B contiguous floors" gains "(owner,
  2026-09-19, `3fe0fb2`)" and "it now asserts survivor volume … survivor *placement* and contiguity" gains "(these
  replacements: agent, 2026-09-19)"; "**That test's thresholds changed on 2026-09-19**:" → "**The test's assertions**:"
  (C2). (2) The paragraph gains A.U0.33 T1's sentence ("The in-suite heap placement figure is closed on the flash-tier
  figure: `largest_block` 122,016 B at baseline → 84,112 B after `build_system()`, control and production arms identical
  (owner, 2026-09-26).") (3) `:3788-3791` → A.U30.09's text. (4) `:3792-3794` → A.U14.35's text. (5) After phase C, the
  figures re-measured on the release image (A.C.03 (4)) replace the 2026-09-11 ones with their date and image.
- **Resolved**: — (no conflict among the constituents)
- **Unit**: Stage 1 U0 ((1) tags, (2)); Stage 2 U14 ((4)); Stage 3 U30 ((3)); Stage 4 U36 ((1) heading wording); Stage 5
  phase C ((5)).
- **Depends**: A.U0.03 (`pico_float` wrap), A.U11.08, A.U14.35, A.U30.09, A.C.03.
- **Blast carried by**: README `:611-613` → U33 (DOCS); `digital_twin/README.md:591-592` → A.U11.08 (TWIN); A.8's `MemFree`
  row → M.SPEC.021.
- **Kind**: doc

### M.SPEC.103 F.5.4 `mem_backup()` adopted for the reset reason; what `reset_cause()` can tell
- **From**: A.U14.20 (heading, both paragraphs), A.U14.01 (second paragraph), A.U11.05 + A.U11.06 (the mechanism and A.8's
  code table; blast), A.U33.09 (the owed row cites F.5.4).
- **Site**: `SPECIFICATION.md:3796-3810`.
- **Change**: A.U14.20's heading and two paragraphs verbatim, then A.U14.01's "**`machine.reset_cause()` separates
  power-on from everything else, nothing more.**" paragraph verbatim.
- **Resolved**: A.U14.20 and A.U14.01 are one commit (both say so); the code table stays A.8's (A.U11.05 owns it,
  M.SPEC.021).
- **Unit**: U14 (after A.U11.05/A.U11.06 at U11).
- **Depends**: A.U11.05, A.U11.06, A.U14.01, A.U14.20.
- **Blast carried by**: `tests_hardware/harness.py` `hard_reset()` docstring and the starvation oracle → A.U14.01/U26
  (HW_BENCH); SPEC `:532` "produced no `WDT_RESET`" → M.SPEC.020; BACKLOG `:331-338` → U33/U36 (DOCS); twin `mem_backup()`
  row → U25 (TWIN).
- **Kind**: doc

### M.SPEC.104 F.5.5 the stub package's defects, the repair guard, the suppression rule
- **From**: A.U0.44 L64 (`:3830` tag), A.U14.36 (`:3835-3839`), A.U27.02 (the repairs fail when their file moved; stub
  post-releases pinned), A.SDEP.09 (the stub versions named), A.SDEP.15 (re-check), A.U28.30 + A.U18.43 (D.6 carries the
  form rule; no F.5.5 edit), M.SPEC.043 (B.15 holds the mechanism).
- **Site**: `SPECIFICATION.md:3813-3838`.
- **Change**: (1) `:3815-3816` names the stub releases installed at the pin (`[stubs]` in `toolchain/versions.toml`,
  A.U27.02/A.SDEP.09); if the refreshed stubs no longer carry a defect, its bullet leaves and the count sentence follows
  (A.SDEP.15). (2) `:3818-3819` "each guarded on the defect still being present so it no-ops once upstream re-ships" gains
  "and failing when the file it targets moved". (3) `:3832` "Repairing the stubs is deliberate, and preferred over" →
  "Repairing the stubs is preferred (agent, 2026-09-10, `90e8c17`) over". (4) `:3835-3838` → A.U14.36's text verbatim.
- **Resolved**: M.SPEC.043 (B.15) and this section both describe the repairs: B.15 the install mechanism and its typing
  passes, F.5.5 the defects at the pin and the suppression rule — each points to the other, no fact stated twice.
- **Unit**: Stage 1 U0 ((3) tag; (1) at the refreshed stubs); Stage 2 U14 ((4)); Stage 3 U27 ((1) `[stubs]`, (2)).
- **Depends**: A.U0.44, A.U14.36, A.U27.02, A.SDEP.09, A.SDEP.15, M.SPEC.043.
- **Blast carried by**: CLAUDE.md stub bullets → A.U27.02/A.SDEP.09 (DOCS); `src/` suppression inventory → U28 (SRC_*,
  TOOL); D.6 form rule → M.SPEC.075.
- **Kind**: doc

### M.SPEC.105 F.5.6 smaller facts at the pin and the non-events
- **From**: A.U14.27 (`:3846`), A.U0.56 L65 (`:3851`), A.U14.16 (`:3852-3855` getaddrinfo bullet), A.U14.22 (`:3858-3860`
  DHCP), A.SDEP.08 (4) (every ruled-out item re-checked, not carried), A.U14.28 (the hang cause and `TZ` fact now F.7's).
- **Site**: `SPECIFICATION.md:3840-3864`.
- **Change**: (1) `:3846` "This project's 21 `const()`-using files are all unannotated." → "This project's `const()` names
  are all unannotated." (2) `:3851` "Not worth it at current flash headroom." → "Not adopted at current flash headroom
  (agent, 2026-09-10)." (3) `:3852-3855` → A.U14.16's form ("`extmod/asyncio/` is byte-identical between the two tags …
  no new primitives; `socket.getaddrinfo()` stays synchronous, and this project calls it only on a numeric host (F.2)").
  (4) `:3856-3857` "the E.3 `select.poll()` GH-Actions hang cause and the `TZ=UTC` Unix-port fact both stand" → "… the
  `select.poll()` hang cause and the `TZ=UTC` Unix-port fact (F.7 rows 12 and 6) both stand". (5) `:3858-3860` → A.U14.22's
  DHCP text. (6) At a pin move, each bullet is re-checked against the new tag: a non-event that changed becomes a
  finding, the version pair in the bullets follows the record (A.SDEP.08 (4), A.SDEP.21 (2)).
- **Resolved**: — (no conflict among the constituents)
- **Unit**: Stage 1 U0 ((6), (2)); Stage 2 U14 ((1), (3), (4), (5)).
- **Depends**: A.U0.56, A.U14.16, A.U14.22, A.U14.27, A.U14.28, A.SDEP.08.
- **Blast carried by**: `THIRD_PARTY_LICENSES.md:162-165` → unchanged (DOCS).
- **Kind**: doc

### M.SPEC.106 F.6 the SIGINT heap wedge: mechanism kept, workaround retired
- **From**: A.U36.037 (1)-(2), A.U25.39 (the helper retired), A.U21.06 (each built binary proves the override), A.U36.512
  (`:4106` "build variant"; inside the replaced text), A.SDEP.16 (`:4091` prewarm mention; conditional), A.U36.548 (history).
- **Site**: `SPECIFICATION.md:4067-4143`.
- **Change**: A.U36.037 (1) verbatim: `:4091-4143` → its "**Closed at the root, and the workaround retired.**" paragraph
  (the Mechanism and Recovery paragraphs `:4067-4090` stay; the `unix_port_poll_prewarm.py` mention at `:4091` goes with
  the replaced text). B.14.1 `:1154-1157` is M.SPEC.039 (2), staged with this change.
- **Resolved**: A.U36.512's `:4106` rewording and A.SDEP.16's `:4091` edit fall inside the replaced span — void.
- **Unit**: U25 (with the retirement, after A.U21.06 at U21); A.U36.037 names U36 for the wording — it lands with
  A.U25.39, together with M.SPEC.039 (2), so neither F.6 nor B.14.1 describes a deleted helper as live (agent decision,
  OR2.c review).
- **Depends**: A.U21.06, A.U25.39.
- **Blast carried by**: CLAUDE.md heap-lock bullet → M.DOCS.100; `digital_twin/README.md:89-101` → A.U25.39 (TWIN); B.14.1
  line → M.SPEC.039 (2).
- **Kind**: doc

### M.SPEC.107 New F.7: the Unix-port rig, where it differs from rp2
- **From**: A.U14.28 (section, rule sentence, table rows 1-14), M.PROC.016 + M_PROC gap (rows from the effective-settings
  diff and the "differ, used by nothing here" sentence), A.U36.040 (the `poll()` growth-path paragraph), AC_NOTES 29 +
  A.U24.15 (row 12's mechanism corrected), M_DOCS gap 1 (i) (row 12 cites CLAUDE.md's "Known hang cause"; M.DOCS.099),
  A.U21.12 (host-lwIP build divergences), A.U21.13 (the host admits about half rp2's connections), A.U19.22 (a "row 15"
  for the withdrawn `TCP_NODELAY` constant goes), A.U14.05 (row 11), A.U14.32/A.U14.34/A.U35.32 (row 8's proof),
  A.U36.544 (`:691`'s source-level account lives here), A.U25.01 (the twin fidelity table points here), A.SDEP.16
  (re-check of the Unix-rig workarounds; conditional removals), A.U25.43 (the prewarm entry order).
- **Site**: new `## F.7 The Unix-port rig: where it differs from rp2` after F.6 (`:4143`), before the `---` (`:4145`);
  `:691` (A.6's pointer).
- **Change**: (1) A.U14.28's rule sentence and table verbatim, columns as it names them, with: row 12 → "`select.poll()`
  over a Python stream object: a real poll asks each registered object for a file descriptor (`MP_STREAM_GET_FILENO`) and,
  on any non-error answer, polls that descriptor instead of the object's own `ioctl()` (`extmod/modselect.c:252-266,
  302-306`, `py/modio.c:84-96`); a fake answering 0 makes the poll watch fd 0, stdin, which never turns ready on GitHub
  runners (CLAUDE.md, the known hang cause) · rp2 has no POSIX path (`MICROPY_PY_SELECT_POSIX_OPTIMISATIONS` 0,
  `py/mpconfig.h:1891-1893`) · both machine fakes answer `EINVAL` as rp2 does; `tests/machine.py` `_StepPoller`; every
  `uart.poller` double is bounded · L2/L3 · a pin re-check that finds the POSIX path changed (owner, 2026-09-29,
  paraphrase: a known limitation, not filed upstream)". (2) Directly after row 12, A.U36.040 (1)'s "**`poll()`'s growth
  path dangles non-fd entries (Unix port only).**" paragraph verbatim (the segfault half of HEAD's row 12, with the
  prewarm workaround and its trigger). (3) One row per divergence A.U21.12 names for the host lwIP build ("loopback netif
  instead of CYW43; 64-bit struct sizes, so arena thresholds differ from rp2's; `MEM_ALIGNMENT` set to the host's
  pointer size; lwIP driven from the event hook rather than PendSV; loud lwIP asserts"), plus A.U21.13's "each loopback
  connection takes two pcbs, so the host admits about half rp2's connections" — each with its workaround site, rp2 proof
  (L4) and trigger. (4) Rows from M.PROC.016's diff: every differing `MICROPY_*`/`MP_*` setting that changes a construct
  used in `src/`, `ext/microdot.py` or the generated modules, one row each; the rest in one sentence "These further
  settings differ and are used by nothing here: <list>." (5) Row 14 keeps its pointers (F.6, E.3.1); rows 3 and 13 keep
  A.U14.28's "not a divergence" wording. (6) A.6's `:691` pointer → "F.7" (A.U36.544). (7) A.SDEP.16: a row whose upstream
  condition the refreshed pin meets loses its workaround (and the row states the port now agrees, or goes) in the commit
  that removes the workaround.
- **Resolved**: (a) AC_NOTES 29 (owner-accepted, AC_NOTES 37): A.U14.28's row-12 mechanism ("never re-evaluates a non-fd
  object's `ioctl()`") is wrong; the corrected mechanism replaces it here, in CLAUDE.md (M.DOCS.099) and in J.7
  (M.SPEC.137). (b) A.U14.28's row 12 also carried the pollfds growth segfault; A.U36.040 gives it its own paragraph —
  one statement. (c) A.U19.22 withdraws `TCP_NODELAY`, so no row for a missing Unix-port constant is written (A.U14.28's
  text at HEAD has no row 15; nothing to delete). (d) M_DOCS gap 1 (i): the row cites "CLAUDE.md, the known hang cause",
  the phrase M.DOCS.099 keeps.
- **Unit**: Stage 1 U14 (rule sentence, rows 1-14, after M.PROC.016's diff; (4)); Stage 2 U21 ((3)); Stage 3 U24 (row 12
  mechanism, with A.U24.15); Stage 4 U36 ((2), (6)); A.SDEP.16 removals in the unit that removes each workaround.
- **Depends**: A.U14.05, A.U14.28, A.U14.29/M.PROC.016, A.U21.12, A.U21.13, A.U24.15, A.U25.43, A.U36.040, A.U36.544,
  A.SDEP.16.
- **Blast carried by**: the "(Part F.7 row N)" comment pointers at the shim sites → A.U14.28 (TEST_HELP, TWIN); the twin
  README shim and prewarm sections → A.U14.28/A.U36.040 (TWIN); E.3/E.5.2 rig-limit pointers → M.SPEC.078/M.SPEC.081;
  CLAUDE.md hang and `TZ` bullets → M.DOCS.099/.100; J.7's pointer → M.SPEC.137; the twin fidelity table → A.U25.01 (TWIN).
- **Kind**: rule, doc

### M.SPEC.108 F.8 `machine.UART` on rp2: the standing facts (HEAD F.5.7-F.5.9)
- **From**: A.U36.532 (4) (the move; M.SPEC.003), A.U36.512 (`:4010` "in any variant"), A.U36.544 (`:4062`), A.U0.25 A20
  (`:4026` tag), A.U0.44 L15 (`:3993`, `:3998-3999`), A.U14.R01 blast (a) (`:3998-3999`), A.U0.33 T4 (`:4016-4017`),
  A.U16.07 (`:4001-4017` hold-timing script), A.U26.59 + A.U8C2.39 (the driver script and its Part N row; the raw script
  and A.U8C2.42's row withdrawn, M.HW_DEV.049), A.U13.12 (readline paths clamped), A.U13.13 + A.U14.31 (the write side),
  A.U13.17 (the poll defaults), A.U13.19 (the out-of-range degrade), A.U18.05 (UDP follows the same shape), A.U8.06 +
  A.U8.11 (Part N IDs), A.U20.18 (`poll_idle_ms` bounded by the tick horizon), A.U13.18 (F.8.1's citer), A.U31.01 (rows the
  section feeds), A.SDEP.17 W24/W25 (conditional), A.U33.07 (owed row cites F.8.2); OR141.a (4) (a)-(f) (each link
  receives through a DMA ring; the clamp reads the ring's fill level), OR141.a (5) (the 100 ms UDP idle rate stays, its
  measurement owed) (A-C review fold).
- **Site**: `SPECIFICATION.md:3866-4066`, moved to `## F.8` after F.7 (M.SPEC.003).
- **Change**: (1) F.8.1 (was F.5.7) body unchanged; if W24 finds `deinit()` now keeps the ring rooted, its closing
  paragraph says the fresh construction stays correct but is no longer load-bearing (M.PROC.011). (2) F.8.2 (was F.5.8):
  (a) `:3927-3928` "`readline()` has no count to clamp and gates on `any()` instead" → "`readline()` and
  `readline_until_complete()` pass the clamp as `readline()`'s size, which stops the read at the bytes already buffered
  (`py/stream.c:368-380`)"; `:3984-3990` the sweep paragraph's "the three that carry no count to clamp — `readline()`,
  `readline_until_complete()` and `_read_delimited()`'s one-byte read — gate on one buffered byte instead" → "the two
  readline paths clamp through `readline()`'s size and `_read_delimited()`'s one-byte read gates on one buffered byte";
  (b) the measurements cite only the driver script (`device_scripts/uart_driver_read_never_blocks_the_loop.py`, Part N
  `l3.uart_read_never_blocks_the_loop_span_fraction`); the raw-script figures (`:3953-3957`, 2026-09-12) stay as dated
  measurements of the peripheral, their script named as folded into the driver script; (c) `:3993` gains "(agent,
  2026-09-11, `441de83`)"; `:3998-3999` → "That is Part F.2's case: a transfer in flight cannot be interrupted, so the
  ladder acts once it returns and one that never returns is the watchdog's — until a genuine non-blocking alternative
  reliably exists (owner, 2026-07-24; BACKLOG deferred goal)."; (d) `:4010` "in any variant" → "on any device";
  `:4012-4017` "whether to yield between the envelopes of one write is open (BACKLOG.md, T4)" → A.U0.33 T4's "the
  per-block hold stays (owner, 2026-09-26: 'Probably better to keep'): yielding per command would bring back the
  coroutine churn the 2026-09-18 remediation removed", plus "pinned on the bench by
  `device_scripts/fram_command_hold_timing.py` (F.3 `stall.fram_command`, `hold.fram_block`)"; (e) `:4018-4022` → A.U14.31's
  "**The write side blocks too once a write outgrows the free TX ring.**" paragraph verbatim; (f) (A-C review fold) after
  the two halves of the fix: "**The receive side now bypasses `machine.UART` entirely** (owner, 2026-10-05), so no frame
  is lost while a flash write holds interrupts off (`ports/rp2/rp2_flash.c:170-174`; W25Q16JV tSE 45/400 ms, tPP
  0.4/3 ms). `machine.UART` enables the RX and RX-timeout interrupts at init (`ports/rp2/machine_uart.c:454`), and its
  IRQ handler, `any()` and `read()` all drain the FIFO (`:162-188, 506, 604`); so after every init the driver clears
  RXIM/RTIM in UARTIMSC and sets RXDMAE in UARTDMACR (RP2040 datasheet 4.2.5), and a DMA channel paced by the UART's RX
  DREQ (2.5.3.1: UART0_RX 21, UART1_RX 23) writes a naturally aligned power-of-two ring (CTRL.RING_SIZE on the write
  address, 2.5.1.3). Progress is read from TRANS_COUNT only, never WRITE_ADDR, which reads wrong during ring transfers
  (RP2040-E12); a second, chained channel reloads the count when it runs out, at most 2**30 − 1 so that reading
  `DMA.count` (`ports/rp2/rp2_dma.c:390-392`) never allocates a big int; the fill level is the modular difference of
  the totals, and a lap — more unread bytes than the ring holds — is detected, counted and handled as J.7's receive
  overrun, never read as data. The clamp of half 1 is therefore to the ring's fill level, never `uart.any()`; a read
  copies by index into the frame buffer, never through a slice, so no byte, read or frame allocates; half 2's yield in
  `ready()` and its wait/idle rates stay. Soft reset is safe: `rp2.DMA` has a finaliser that aborts the channel and soft
  reset runs `gc_sweep_all()` (`rp2_dma.c:365, 637-673`; `ports/rp2/main.c:303`), proven on the bench. The per-byte
  wait measured above stays a fact of `machine.UART`'s receive calls, which this driver no longer makes." (all cites
  at v1.29.0, re-checked at the pin in force, C3). (3) F.8.3 (was F.5.9): (a)
  `:4026` "Same layer as F.5.8 and the same owner rule behind it" → "Same layer as F.8.2 and an agent extension of its
  owner rule (agent, 2026-09-11)"; `:4047` "F.5.8" → "F.8.2"; (b) `:4062` "`_UART_TIMEOUT_MS = 1000`" → "`UARTLinkDriver`'s
  `timeout` default of 1000 ms"; (c) `:4063-4065` → A.U13.17's "The driver defaults to 50 ms idle and 2 ms
  in-transaction, the dev bench's measured pair; a wiring states either only to depart from it." (d) after it, A.U13.19's
  sentence: "An out-of-range `poll_wait_ms`, `poll_idle_ms` or `timeout_ms` — beyond the ticks range, where
  `asyncio.sleep_ms()` raises `OverflowError` — degrades `ready()` to `False`, as a malformed mask (`TypeError`) does; the
  build bounds `poll_idle_ms` between `poll_wait_ms` and the tick horizon (`buildgen/validate.py`)." (A.U20.18); (e) A.U18.05's
  paragraph: "`asy_udp_socket.ready()` follows the same shape: 20 ms inside an exchange, 100 ms for the captive DNS's
  deadline-free listen (agent, 2026-09-30; kept with its measurement owed, owner, 2026-10-05): the idle rate trades the
  first-query latency of an idle listener against the event-loop share its polling takes, specified as Part N
  `udp.poll_idle_ms`, bounded by the build, and measured on the twin and on the bench"; (f) the rates cite Part N (`uart.poll_wait_ms`, `uart.poll_idle_ms`,
  `udp.poll_wait_ms`, `udp.poll_idle_ms`, by the IDs A.U8.06/A.U8.11 land); (g) (A-C review fold, U13) the section's
  description of the UART `ready()`'s check: it reads the receive ring's fill level instead of polling the receive side
  (`ipoll()`/`uart.any()`), and sleeps `poll_wait_ms` inside a transaction and `poll_idle_ms` with no deadline — the
  cost argument and the rule stay as written (owner, 2026-10-05; F.8.2). (4) If W25 finds the per-byte wait gone, F.8.2's
  mechanism text follows the source; the clamp and the yield stay (the owner's no-blocking rule).
- **Resolved**: (a) A.U0.44 L15 and A.U14.R01 blast (a) rewrite `:3998-3999` — one sentence carrying R01's ladder and
  L15's owner tag. (b) A.U26.59 folds `uart_read_never_blocks_the_loop.py` into the driver script; A.U8C2.42's citation of
  the raw script is withdrawn with it (M.HW_DEV.049). (c) `UartLinkExerciser` → `UARTLinkDriver` (C7). (d) A.U13.12's
  clamp makes HEAD's "gate on `any()`" readline wording false — rewritten in (2)(a).
- **Unit**: Stage 1 U0 (A20, L15 tags, T4); Stage 2 U13 ((2)(a), (3)(c), (3)(d) degrade half; (2)(f) and (3)(g) with
  the DMA receive path, its fakes and tests — the "proven on the bench" clause added in phase C with the soft-reset run);
  Stage 3 U14 ((2)(e), the backstop sentence); Stage 4 U16 (hold-timing script); Stage 5 U18 ((3)(e) with the idle-rate
  change and its owed measurement, A.U18.05); Stage 6 U20 ((3)(d) build half); Stage 7 U26 ((2)(b)); Stage 8 U36 (the
  move with every citer, M.SPEC.003; (2)(d), (3)(a)-(b)).
  A-C2 step order: A.U14.R01's part lands in U18, not U14 (it needs A.U18.R01, which lands in U18).
- **Depends**: M.SPEC.003, A.U0.25, A.U0.33, A.U0.44, A.U8.06, A.U8.11, A.U13.12, A.U13.13, A.U13.17, A.U13.19, A.U14.31,
  A.U14.R01, A.U16.07, A.U18.05, A.U20.18, A.U26.59, A.U36.512, A.U36.544; M.SRC_NET.221 (the DMA receive path),
  M.TEST_HELP.069 and M.TWIN.169 (the time-driven DMA and UART register fakes), M.HW_DEV.160 (the
  soft reset during traffic on the bench); M.SPEC.156 (`udp.poll_idle_ms`'s owed measurement).
- **Blast carried by**: every F.5.7-F.5.9 citer outside SPEC → A.U36.532 (4) (M.SPEC.003); `devices/dev.toml:39-40`
  comment and J.6 sentences → A.U13.17 (GEN, M.SPEC.136); the raw script's README lines → A.U26.59 (HW_DEV).
- **Kind**: doc

### M.SPEC.109 New F.9: standing workarounds for upstream defects, and what retires each
- **From**: A.SDEP.21 (2) (the closing subsection "F.5.10"), A.SDEP.22 (CLAUDE.md's refresh practice cites it),
  A.U36.023 (1) item (9), A.U36.031 (P4: a workaround names its defect and its end), A.U21.09 (the issue-19704 entry),
  M.PROC.031 (U37 re-reads every entry), A.U26.65 (harness workarounds live in `tests_hardware/README.md`'s table, not
  here).
- **Site**: new `## F.9 Standing workarounds for upstream defects, and what retires each` after F.8 (end state; created
  after F.6 at U0, so F.7 and F.8 are inserted before it as they land).
- **Change**: A.SDEP.21 (2)'s subsection under this number: "(agent, <date>)", one line per workaround still standing
  after the refresh — name, where it lives, the upstream condition that retires it, the section holding the detail
  (B.7.1, B.14.x, F.5.5/B.15, F.6, F.7, A.5, H.7, H.8) — and a closing sentence: "Harness and bench workarounds are listed
  in `tests_hardware/README.md`'s Workarounds table; both lists are re-checked at each pin move and dependency refresh
  (this Part's opening paragraph)." Every entry retired at U37 (M.PROC.031) leaves in the commit that removes its
  workaround.
- **Resolved**: A.SDEP.21/.22 and A.U36.023 name the section "F.5.10"; A.U36.532's rule files standing facts by topic, not
  under F.5's per-pin record, so it is F.9 (M.SPEC.003's resolution, agent decision, OR2.c review); every citer writes
  "F.9" — CLAUDE.md's A.SDEP.22 sentence included (gap for DOCS).
- **Unit**: Stage 1 U0 (with A.SDEP.21); Stage 2 U21 (the issue-19704 line, A.U21.09); Stage 3 U26 (closing sentence's
  table pointer); Stage 4 U37 (M.PROC.031 re-read).
- **Depends**: A.SDEP.21, A.U21.09, A.U26.65, M.PROC.031.
- **Blast carried by**: CLAUDE.md refresh bullet "Part F.5.10" → "Part F.9" (gap for DOCS: M.DOCS's A.SDEP.22 text);
  BACKLOG upstream-watch items → A.SDEP.21 (5) (DOCS).
- **Kind**: rule, doc

## SPECIFICATION.md — Part G (`:4147-4276`)

### M.SPEC.110 G intro, G.0, G.1: the rule covers test code
- **From**: A.U24.49 (G.1 gains the test-code scope), A.U18.08 ("reuse before writing": the dotted-quad helper — its
  entry is M.SPEC.111), A.U4.01/A.U11.31/A.U18.38/A.U19.01/A.U19.16 (mirror rule applied, blast only — G.1's sentence
  stands).
- **Site**: `SPECIFICATION.md:4161-4172`.
- **Change**: G.1's first sentence "Before writing new code, identify the *kind* of problem it solves" → "Before writing
  new code — test code under `tests/`, `tests_scripts/` and `tests_js/` included — identify the *kind* of problem it
  solves"; the rest of G.0/G.1 unchanged.
- **Resolved**: — (no conflict among the constituents)
- **Unit**: U36 (A.U24.49 names U36 for the text; the helpers land at U24).
- **Depends**: A.U24.49.
- **Blast carried by**: E.2.1 names the shared helper modules → M.SPEC.077; the clone consolidation → A.U24.49 (TEST_HELP).
- **Kind**: rule, doc

### M.SPEC.111 G.2: the catalog at the end state
- **From**: GAP-G13 (M_SRC_CORE; per-kind validators), A.U15.09 (`ContMeas` synthetic schema), A.U24.62 (bool/int
  fact), A.U10.01 + A.U10.05 (`COUNTER_CAP`, the counter check), A.U10.02 (`TickSeconds`), A.U10.06 (`utc_now()`),
  A.U5.01 + A.U5.03 (`LogConfig`, `DEFAULT_LOG`), A.U30.19 + GAP-G8 (`report_if_fatal()` in `asy_print_log`), A.U15.40 +
  GAP-8 (`DeviceSession`, `SensorReader._trigger_loop()`), A.U10.R01 (the ladder hooks beside `_error_check()`), A.U13.R01
  (`I2C.clear()`/`recover()`), A.U13.11 (pair rule), A.U13.01 + A.U12.18 + A.U13.10 + A.U30.07 (the I2C scratch and
  burst entries), A.U1.18 (`:4205` legacy path), A.U19.11 + A.U10.27 (streaming pieces in bytes; non-finite as `null`),
  A.U13.06 (bus asymmetries), A.U12.17 + A.U17.22 + M_DOCS gap 1 (c) (frame-codec aliasing, `max_frame`, one codec per
  driver; M.DOCS.065), A.U12.10 (derived quantities, CRCs), A.U12.01 + A.U12.06 (their facts), A.U19.16 (result words),
  A.U4.01 (compare-before-write), A.U5.04 + A.U5.09 + A.U18.40 (config objects), A.U18.08 (`ipv4_to_int()`), A.U18.13 +
  A.U18.05 + A.U8.11 (the UDP client and the one poller pattern), A.U23.25 + A.U6.16 + A.U20.27 (mirror pairs),
  A.S0930.13 + A.S0930.30 + A.U10.08 + A.U8.08 + A.U35.30 + A.U24.79 (watchdog entry), A.U25.23 (the twin's own
  `COUNTER_CAP` copy cites G.2; blast), A.U16.23 (accessor rule unchanged), A.U5.14 (region = `memoryview` slice; no edit);
  OR137.a (4) (the hourly window counter), OR143.a (1) (the shared piece primitive, checked against this catalog first),
  OR140.a (4) (the humidity helpers stay; their domain joins the derived-quantities entry), F21 tag form
  (timestamps-before-ntp) (A-C review fold).
- **Site**: `SPECIFICATION.md:4174-4264`.
- **Change**: entries in HEAD's order, module and class names as landed (C7: `asy_config_manager.py`,
  `asy_base_classes.py`, `asy_print_log.py`, `asy_api_response.py`, `asy_crc_checks.py`, `asy_framing_codecs.py`,
  `asy_system_service.py`; `RegionBuffer`, `FRAMChunk`, `FRAMChunkBuffer`, `FramingBase`/`FramingPass`/`FramingCOBS`,
  `CRCBase`/`CRCPass`, `UDPSocket`), each edit below, new entries where named:
  1. Numeric validation → "`asy_config_manager.py`'s `type_or_range_error()` for a schema-backed or dispatch-only
     (synthetic `FieldSchema`: `ContMeas`, the system and notification commands) field, and the per-kind validators
     `checked_int()`, `checked_float()`, `checked_numeric()` (`None` = refused) for a typed caller, which never narrows a
     validated value at runtime. `bool` is not an `int` here (F.1). Never hand-roll a cast or range comparison."
  2. Callback dispatch guarding, envelope: names only.
  3. Locked state gains A.U10.01's sentence ("`LockedCounter` saturates at `COUNTER_CAP` (2**30 − 1), checked before the
     step; a value never stepped (an identifier) is a `LockedValue`") and "kept allocation-free by
     `tests_scripts/<A.U10.05's check>`".
  4. New, after it: A.U10.02's "**Elapsed seconds**" entry and A.U10.06's "**Current UTC timestamp**" entry verbatim
     (its decision tag "(agent, 2026-09-29; owner-reviewed, 2026-10-02)", C9). Then (A-C review fold) "**Hourly window
     counter** — `asy_base_classes.py`'s hourly window counter (its class name as landed): a count of events in the last
     24 hours at hourly resolution, in 24 integer bins allocated once at construction; the bins advance lazily on the
     next event or read from the uptime seconds (`SysUptime`, monotonic, untouched by NTP steps), zeroing every hour
     passed — all 24 after a gap of a day or more; each bin and the sum are capped at `COUNTER_CAP`; `reset()` clears
     every bin; no event, read or hour change allocates. Its first user is `HTTPDropped` (A.8; owner, 2026-10-01)."
  5. Logging → "`asy_print_log.py`'s `make_logger()` with one `LogConfig` (`DEFAULT_LOG` for a module with no store of its
     own; one per FRAM store) …"; new, after the error-log type: "**Fatal-error report** — `asy_print_log.py`'s
     `report_if_fatal()`/`fatal_reported()`: the first statement of every broad handler in `src/` and the generated
     modules; a C-stack exhaustion is recorded and the supervisor reboots (F.1)."
  6. Driver shape → Part C, plus new: "**Device session** — `asy_base_classes.py`'s `DeviceSession`: one device's session
     lock plus its bus device, built by every driver, never subclassed per driver (C.2)"; "**Trigger divider** —
     `SensorReader._trigger_loop()`: a reader needing a slower rate than its base tick divides it here (C.9)";
     "**Read-error escalation** — `SensorReader._error_check()` and its ladder hooks `_recover_device()`,
     `_init_failed()`/`_init_done()`, with `I2C.clear()`/`I2C.recover()` as the bus rungs (C.7, F.2)."
  7. Buffer ownership: `LockableBuffer` → `RegionBuffer`; "their `python/` ancestors" → "their
     `legacy/firmware/python/` ancestors"; `AsyFramChunk` → `FRAMChunk`, `AsyFramChunkBuffer` → `FRAMChunkBuffer`; the pair
     bullet gains A.U13.11's sentence; the scratch sentence gains A.U13.01's text, then A.U12.18's SGP40
     `_measure_command` sentence, and A.U30.07's "`get_register_into()` for a burst the caller decodes at once into a
     buffer of its own".
  8. Streaming: "pieces of at most `chunk_bytes`" → "… `chunk_bytes` bytes, already encoded" (A.U19.11); gains "The
     writer writes a non-finite float as `null`; producers still gate their own values (F.1)." (A.U10.27).
  9. SPI session: last sentence → A.U13.06's text.
  10. Frame codecs: names as landed; gains A.U12.17's "a returned view aliases the codec's scratch until its next
      `encode_into()`", A.U17.22's "a delimited codec's `max_frame` is the raw frame (header, payload and CRC);
      `UARTComm` refuses one smaller than that", and BACKLOG's finding: "Each driver constructs its own codec: one
      instance shared by two drivers would corrupt both, its long-lived scratch being per instance (agent,
      2026-09-11)."
  11. New, after the codecs: A.U12.10's "**Derived quantities**" and "**CRCs**" entries verbatim, the domain list of the
      first gaining (A-C review fold) "Magnus absolute and relative humidity −30..40 °C" — `abs_humidity()` and
      `rel_humidity()` stay in `math_helpers.py`, small and complete the functional suite (owner, 2026-10-02), and follow
      the entry's no-clamp rule like the rest.
  12. Mirror: the bullet becomes the catalog of mirrored pairs, each with its check — the mock against the product
      endpoints (field for field, bound for bound); `js/api-contract.js` (wire facts, the result words, the mock's
      `COUNTER_CAP`) against `src/`, read by its source-reading test (A.U23.25, A.U19.16); the website's copies of
      generator bounds against `buildgen/`, pinned by `test_definitions_js_mirrors.py` and the shape corpus (A.U6.16);
      the two owner-kept catalogs pinned by A.U20.27's check — "a `src/` policy change and its `js/` mirror are one
      change".
  13. Naming → `asy_config_manager.py`'s `instance_name()`.
  14. Wiring declaration (gap fill): "a `_WIRING: "WiringSchema"` tuple next to a driver's `_VAL_*` schema tuples" → "a
      `# @wiring` comment tag next to a driver's `_VAL_*` schema tuples (L.6.4), read by `buildgen/wiring.py`".
  15. Fan-in: names only.
  16. Watchdog feed: "`system_service.py`'s `SystemService.feed_watchdog()`" → "`asy_system_service.py`'s …"; "(the
      task-supervisor loop, and buildgen's own one-time boot setup batch, WP6)" → "(the supervisor and the generated
      one-time setup batch)"; gains "the one reusable feed access point until a shutdown command takes ownership; then
      only the sequence's own feed (A.8)" (A.S0930.30), "the feed sites and the supervisor scan budget are pinned by
      `tests_scripts/test_watchdog_feed_sites.py`; the timeout is Part N `wdt.timeout_ms`" and A.U35.30's sentence naming the planted-failure
      tests as the failure-class proof.
  17. New: A.U19.16's "**Result words** — `asy_config_manager.py`'s `VALID`/`UNCHANGED`/`INVALID`/`FAILED`: every
      per-field result"; A.U4.01's "**Compare-before-write** — `asy_config_manager.py`'s `compare_before_write()`: every
      setter that writes persistent memory"; A.U5.04's "**Config objects** — parameters that travel together are one
      namedtuple built by generated code"; "**Dotted-quad parsing** — `asy_dns_client.py`'s `ipv4_to_int()`, never a
      second parser" (A.U18.08); "**UDP client and the one poller pattern** — `asy_udp_socket.py`'s `UDPSocket` makes one
      connect attempt per construction; every wait goes through its `ready()`, which, like the UART driver's, checks
      readiness without blocking — `ipoll(0)` for the socket, the receive ring's fill level for a UART (F.8.2) — and
      sleeps `poll_wait_ms` inside an exchange and `poll_idle_ms` when waiting with no deadline (F.8.3; Part N `udp.*`,
      `uart.*`)" (A.U18.13, A.U18.05, A.U8.11; the UART clause as the fold's DMA receive path leaves it, U13).
  18. New, after the streaming entry (A-C review fold): "**Bounded piece assembly** — the shared piece primitive (its
      module and class name as landed; the webserver's streaming `_PieceWriter` is its model): a payload whose size
      the caller did not fix is held as pieces of at most `chunk_bytes`, with its length, iteration and a copy-out, so
      no single allocation exceeds `chunk_bytes`; `UARTComm` assembles every train without a caller destination in it
      (J.8; owner, 2026-10-05)."
- **Resolved**: (a) A.U15.40 named the divider `_divide_trigger()`; M.SRC_SENS.045 lands `_trigger_loop()` (GAP-8). (b)
  A.U30.19 placed `report_if_fatal()` in `base_classes.py`; M.SRC_CORE.034 lands it in `asy_print_log` (GAP-G8). (c) GAP-G13
  replaces A.U11.S01's runtime narrowing with the per-kind validators; `coerce_numeric()` becomes private and leaves the
  entry. (d) A.U13.01 and A.U12.18 edit the same scratch paragraph — A.U13.01's sentence first, A.U12.18's after it, as
  A.U13.01 states. (e) the `_WIRING` tuple entry is false at HEAD (C.14.2 already reads a comment tag; M.SPEC.072) — gap
  fill (agent decision, OR2.c review). (f) A.U18.13 and A.U8.11 name a G.2 `AsyUDPSocket` entry and a "one poller
  pattern" entry that no constituent writes — one entry, gap fill (agent decision, OR2.c review). (g) A.U10.27's rule
  is homed here (the streaming writer is where it applies); F.1 keeps the fact (M.SPEC.091).
- **Unit**: Stage 1 U4 (compare-before-write); Stage 2 U5 (logging, config objects); Stage 3 U10 (names, counter, elapsed,
  UTC, ladder, watchdog check, A.U10.27); Stage 4 U11 (validation entry, GAP-G13); Stage 5 U12 (derived quantities, CRCs,
  codec aliasing); Stage 6 U13 (pair rule, scratch, bus asymmetry, I2C rungs); Stage 7 U15 (session, divider); Stage 8 U17
  (`max_frame`); Stage 9 U18 (UDP, dotted quad); Stage 10 U19 (result words, streaming bytes); Stage 11 U23/U20/U6
  (mirror pairs); Stage 12 U30 (fatal report, `get_register_into()`); Stage 13 U35/U36 (watchdog proof, shutdown
  ownership, the shared-codec sentence, legacy path at U1). Fold stages: U12 (item 11's humidity domain, with the
  helpers' aligned tests); U17 (item 18, with the piece primitive and `UARTComm`'s chunked assembly — checked against
  this catalog first, so its entry lands in the same commit); U19 (item 4's hourly window counter, with its first user,
  the webserver's drop path).
  A-C2 step order: A.S0930.13's part lands in U20, not U11 (it follows A.S0930.13's own change, which lands in U20).
- **Depends**: A.U4.01, A.U5.01, A.U5.04, A.U10.01, A.U10.02, A.U10.05, A.U10.06, A.U10.08, A.U10.R01, A.U12.10,
  A.U12.17, A.U12.18, A.U13.01, A.U13.06, A.U13.11, A.U13.R01, A.U15.40, A.U17.22, A.U18.05, A.U18.08, A.U18.13, A.U19.11,
  A.U19.16, A.U23.25, A.U30.07, A.U30.19, A.U35.30, A.S0930.30, M.SRC_CORE.034, M.SRC_CORE.047, M.SRC_SENS.045;
  M.SRC_CORE.133 (the window counter), M.SRC_CORE.134, M.SRC_NET.220 (the piece primitive and its use), M.SRC_CORE.125/.128
  (their removal of the humidity helpers dropped by the fold).
- **Blast carried by**: I.2's scratch paragraph → M.SPEC.126; C.2/C.3/C.7/C.9 pointers → M.SPEC.047, .048, .058, .066;
  BACKLOG's I2C-scratch and bus-asymmetry entries → A.U13.01/A.U13.06 (DOCS); the twin `COUNTER_CAP` comment → A.U25.23
  (TWIN); JS mirror checks → A.U23.25/A.U6.16 (WEB, TSC).
- **Kind**: rule, doc

### M.SPEC.112 G.3: a shape-grep finding is migrated, not flagged
- **From**: A.U36.540 (6), A.U37.07 (the closing sweep runs G.3; no text).
- **Site**: `SPECIFICATION.md:4269-4271`.
- **Change**: "Each finding is a candidate migration, not a known quirk to leave alone — flag and discuss before changing
  (D.1's "flag, don't silently change" applies here too)." → A.U36.540 (6)'s "Each finding is migrated to the primitive
  directly as a consistency change (owner, 2026-09-25); a migration that would change behaviour follows D.1."
- **Resolved**: — (no conflict among the constituents)
- **Unit**: U36.
- **Depends**: A.U36.540.
- **Blast carried by**: CLAUDE.md scan rule → A.U36.540/A.U36.542 (DOCS); D.1 → M.SPEC.074.
- **Kind**: rule, doc

## SPECIFICATION.md — Part H (`:4277-4780`)

Part H's key names follow A.U10.40's one key scheme as landed (C7: e.g. `SGPResetVOC` → `ResetVOC`); module names
follow C7 (`asy_api_response.py`, `asy_config_manager.py`). Every "(U36)" docs clause of U6/U23/U28 lands through the
U36 change that owns its paragraph below.

### M.SPEC.113 H.1: the owner's brief, placement, the browser floor, themes and accessibility
- **From**: A.U0.29 E03 (`:4283-4286` owner tags), A.U36.500 (1)-(2) (constraints met per device; the placement rule and
  the unshown values), A.U19.10 (2) (the four values not added, recorded here), A.U32.06 (`LastTaskEnd` on Status),
  A.U36.501 (1) (the browser floor), A.U36.510 (1) (themes, AA contrast, accessibility), OR132 + A.U23.44 (light-theme AA
  tokens), A.U23.43 (accessibility baseline), A.C.04 (6) + A.C.10 (the browser-floor evidence note), A.U1.18 (`:4290`
  predecessor path), A.U10.42 (no legacy compatibility); OR140.a (15) (Back walks the sensor subpages), the review
  answers' tag form for website-accessibility and status-fields-added-and-left-out (C9) (A-C review fold).
- **Site**: `SPECIFICATION.md:4281-4293`.
- **Change**: (1) `:4281-4288` keeps its first two sentences, then "Standing constraints, all met:" → A.U36.500 (1)'s
  "Standing constraints (the owner's brief, 2026-08-21, `c28ab93`), met on every device the TOMLs define:" with A.U0.29's
  "full coverage of the REST API (owner, 2026-09-26: 'The reference for us is the new API.')" in place of "full REST
  coverage retained versus legacy"; "stable on major browsers," → A.U36.501 (1)'s browser-floor text; "light/dark
  (automatic-only via `prefers-color-scheme`);" → A.U36.510 (1)'s text verbatim (both themes at AA, OR132 firm), its
  accessibility clause tagged "(owner, 2026-10-02)" and followed by (A-C review fold) "browser history that follows the
  pages: each sensor subpage opened from the menu is a history entry of its own, so Back and Forward walk the subpages
  and a deep link opens its subpage (owner, 2026-10-02);". Once
  phase C has run, the floor sentence gains its evidence note: "(checked on the bench, <date>: <engines and widths>)"
  (A.C.04 (6)). (2) After `:4288`, A.U36.500 (2)'s "**Placement.**" paragraph verbatim (its Status list already names
  `LastTaskEnd`, A.U32.06) and its "**Values deliberately not shown**" sentence (A.U19.10 (2)'s four values), its tag
  "(owner, 2026-10-02)" (C9: the owner answered it, adding the 24-hour `HTTPDropped`, A.8). The Placement paragraph's
  Status list gains `ConfigFaults` (A-C review fold; the website row lands in U23, OR138.a). (3) `:4290-4293` "**Predecessor**: `html_raw/{general,arzi,dev,wozi}` is the legacy, still-deployed site …" →
  "**Predecessor**: `legacy/firmware/html_raw/{general,arzi,dev,wozi}` is the legacy site the owner's legacy units serve,
  targeting the legacy REST shape (PUT-with-`cmd`-envelope, `Led`-prefixed fields); this Part's website targets the refactored REST
  shape from the start and keeps no legacy compatibility (owner, 2026-09-26) — not a reskin."
- **Resolved**: (a) A.U0.29 (U0) and A.U36.500 (U36) rewrite the same sentence — A.U36.500 keeps A.U0.29's owner tags,
  as it says. (b) A constraint not met at landing is named with the action that closes it, not written as met
  (A.U36.500's own rule). (c) OR132 answered the light-theme question firm: "every text and status colour meets WCAG 2.1
  AA … in both themes" is written without a pending marker.
- **Unit**: Stage 1 U0 (A.U0.29 tags); Stage 2 U1 ((3) path); Stage 3 U36 ((1)-(3) rest; the history clause after U23
  lands it); Stage 4 phase C (evidence note).
- **Depends**: A.U0.29, A.U1.02, A.U6.18-A.U6.26, A.U19.10, A.U23.22, A.U23.43, A.U23.44, A.U23.48, A.U32.06, A.U36.500,
  A.U36.501, A.U36.510, A.C.04; M.WEB.025, M.WEB.030 (history entries per subpage, deep links), M.WEB.012 (the
  `ConfigFaults` row).
- **Blast carried by**: `eslint.config.js` `ecmaVersion: 2022` → A.U36.501 (2) (WEB); H.5.1's generator-owned paragraph
  pointer → M.SPEC.118.
- **Kind**: rule, doc

### M.SPEC.114 H.2: folder map, preview, module list, the stager, the splitting rule
- **From**: A.U36.517 (1)-(5), A.U28.24 (`:4307`, `:4323` preview on 127.0.0.1), A.U0.44 L23 (`:4335-4336` tag), A.U23.07
  (`shell.js`), A.U23.25 (`api-contract.js`), A.U23.37 (kept exports), A.U23.38 (bundle derived from imports), A.U6.02-A.U6.07
  (generated definitions, mock samples, device list), A.U6.16 (the splitting rule's unique top-level names), M_WEB gap 4 (d)
  (`field-format.js` is pure formatting; `tests_js/_expected_display.js` is the Node- and browser-safe module).
- **Site**: `SPECIFICATION.md:4296-4335`.
- **Change**: A.U36.517 (1)-(5) verbatim, with: (a) the module list's `field-format.js` entry → "`field-format.js` (pure
  formatting, no DOM dependency)", and a new line "`tests_js/_expected_display.js` (the expected-display helper the
  Node-context and browser tests share, H.8.1)"; (b) the inline-bootstrap sentence `:4332-4336` stays with "(accepted —
  it's a thin bootstrap)" → "(agent, 2026-08-26: it is a thin bootstrap)" and gains A.U36.517 (5)'s id-check sentence.
- **Resolved**: M_WEB gap 4 (d): HEAD's "`field-format.js` (… split so Node-context tests can reuse it without DOM types,
  H.8.1)" is false after M.WEB.012/.069 — the Node-and-browser module is `tests_js/_expected_display.js`.
- **Unit**: Stage 1 U0 (L23 tag); Stage 2 U36 (the rest; U6/U23/U28 behaviours land first).
- **Depends**: A.U0.44, A.U6.02-A.U6.07, A.U23.07, A.U23.25, A.U23.37, A.U23.38, A.U28.24, A.U36.517, M.WEB.012, M.WEB.069.
- **Blast carried by**: README web section → A.U36.516 (7)/A.U36.547 (DOCS); `tests_scripts/test_build_website_sh.py`
  comments → TSC.
- **Kind**: doc

### M.SPEC.115 H.3: the API-stability rule and the layering contract
- **From**: A.U0.25 A23 + A.U10.42 (`:4339`), A.U36.509 (1)-(2), A.U23.08 (in-place refresh), A.U23.15 (`resetControl()`),
  A.U23.41 (the layering guard), A.U23.42 (the data-attribute hooks), A.U23.40 (`CSS.escape()`).
- **Site**: `SPECIFICATION.md:4339-4359`.
- **Change**: (1) `:4339` "The REST API is expected to stay stable long-term" → "The REST API's keys are harmonised
  before the release; after it they are frozen, or changed only with a migration (owner, 2026-08-21, `c28ab93`; owner,
  2026-09-26)". (2) `:4343-4359` → A.U36.509 (1)-(2) verbatim, naming the layering check's file as A.U23.41 lands it.
- **Resolved**: A.U0.25 A23 (U0: "expected to stay stable long-term (owner, 2026-08-21, `c28ab93`); it is harmonised
  before the release and frozen from it (owner, 2026-09-26)") and A.U10.42 (U10: harmonised, then frozen or migrated) —
  A.U10.42's wording, keeping A.U0.25's commit.
- **Unit**: Stage 1 U0 (A23 tags); Stage 2 U10 ((1)); Stage 3 U36 ((2)).
- **Depends**: A.U0.25, A.U10.42, A.U23.08, A.U23.15, A.U23.40-A.U23.42, A.U36.509.
- **Blast carried by**: C.5.3's legacy-route sentence → M.SPEC.056.
- **Kind**: rule, doc

### M.SPEC.116 H.4: the decision table and the mock paragraph
- **From**: A.U36.503 (1)-(3) (poll rows), A.U11.31 + A.U19.14 (`ResetErrors` concurrent; item 24 leaves), A.U8.04 +
  A.U8.18 (Part N citations), A.U36.507 (3) (history depth), A.U36.504 (1) (never-"Unchanged" row), A.S0930.30
  (`resetconfig` exception; folded by A.U36.504), A.U6.17 (derived classes), A.U36.505 (sparse PUT, after Apply, accepted
  gap), A.U0.25 A24 (`:4382` tag), A.U23.14/A.U23.15/A.U23.17, A.U36.506 (1) (staleness row), A.U23.21, A.U36.510 (2)-(5)
  (validation, rendering safety, stale bundle, mock paragraph), A.U23.06/.10/.26/.28/.29/.40/.49, A.U11.21 (float32 mock
  gap), A.U25.12 + M_WEB gap 4 (c) (`ForceCalRef` read-back; dispatch fields never reported by GET), A.U18.38 (`HotspotPW`
  masked), A.U19.01 (unknown key "Invalid"), A.U23.45 + A.U6.18 (the legacy-divergence row), A.U36.500 (3)-(4) (nav and
  reachability rows), M_WEB gap 4 (e) (`LastTaskEnd`'s display), A.U32.06 (the `LastTaskEnd` row's field),
  A.U23.01-A.U23.05; OR140.a (3) (confirmation before every system command, the error-history clear and the DNS
  fallback Clear; the API stays one command per request), OR140.a (15) (history per subpage), OR140.a (16) (displayed
  precision per value), F21 tag form (website-unattended) (A-C review fold).
- **Site**: `SPECIFICATION.md:4361-4387`.
- **Change**: rows in HEAD's order with: "Nav grouping" and "API reachability" → A.U36.500 (3)-(4); "History depth" →
  A.U36.507 (3); "Poll coordination", "Per-request timeout value" → A.U36.503 (1)-(2) (the latter's "(15 s, Part N
  `web.outer_cap_s`)" and "concurrently" as written there; "(BACKLOG item 24)" gone); "Definitions validation" → A.U36.510
  (2); "Rendering safety" → A.U36.510 (3); "Numeric coercion/validation" → "`type_or_range_error()` and the per-kind
  validators (`asy_config_manager.py`), mirrored in `mock-server.js` | Canonical for every numeric field (A.8, Part G)";
  "Dispatch-only PUT fields" → A.U36.504 (1)'s "Never-"Unchanged" fields" row; after "PUT-result coloring", A.U36.505
  (1)'s "Sparse PUT" and "After Apply" rows and A.U36.506 (1)'s "Stale readings and timestamps" row; "PUT/GET error
  handling" → A.U36.503 (3)'s sentence; "Known accepted gap" → A.U36.505 (2); new rows A.U36.510 (4) ("Stale bundle") and
  A.U23.45's "Divergences from the legacy site" (its list, plus A.U6.18's "the identity and NTP submit buttons keep
  legacy's labels (owner, 2026-09-29)"); new row "Last task end | `LastTaskEnd` shows "<Task> at uptime <n> s" on the
  Status page | the `/status` row A.8 states". New rows (A-C review fold): "Confirmations | the browser's own
  `confirm()` before every system command, before the error-history reset and before the DNS fallback Clear; the API
  takes one command per request and asks nothing (A.8) | owner, 2026-10-02"; "Navigation history | each sensor subpage
  opened from the menu is a history entry: Back and Forward walk the subpages, a deep link opens its subpage (H.1) |
  owner, 2026-10-02"; "Displayed precision | each numeric value shows a sensible number of decimals (2-3), from the
  `decimals` hint its source declares (H.5.1); the API keeps full resolution | owner, 2026-10-02". The poll rows carry
  the website-unattended decision's tag "(agent, 2026-09-30; owner-reviewed, 2026-10-02)" (C9). The mock paragraph `:4384-4387` → A.U36.510 (5) verbatim except
  its SCD30 clause → "SCD30's `ForceCalRef` reads back the last reference applied since power-up, 400 after power-up
  (Interface Description 1.4.6), and the mock answers the same — the last value applied, 400 on a fresh mock" and its
  GET clause → "the dispatch fields and `ContMeas` are never reported by GET (command-only triggers, C.5.2.1)".
- **Resolved**: (a) A.U36.510 (5) predates A.U25.12's volatile FRC read-back and A.U10.40's key rename — M_WEB gap 4 (c)
  takes the landed facts. (b) A.U36.504 merges A.S0930.30's two H sentences, as it states. (c) A.U11.31's "concurrently"
  and A.U8.04's Part N citation are merged into A.U36.503 (2), as it states. (d) M_WEB gap 4 (e): HEAD names no
  `LastTaskEnd` display; the row is a gap fill from A.U32.06's `/status` field (agent decision, OR2.c review).
- **Unit**: Stage 1 U0 (A24 tag); Stage 2 U11 ("concurrently"); Stage 3 U36 (the table and the paragraph; the three fold
  rows after U23 lands their behaviour).
- **Depends**: A.U0.25, A.U6.17, A.U6.18, A.U8.04, A.U8.18, A.U11.31, A.U19.14, A.U23.01-A.U23.06, A.U23.10, A.U23.14-
  A.U23.17, A.U23.21, A.U23.26, A.U23.28, A.U23.29, A.U23.40, A.U23.45, A.U23.49, A.U25.12, A.U32.06, A.U36.503-A.U36.507,
  A.U36.510, A.S0930.30, M.WEB.041; M.WEB.021, M.WEB.025, M.WEB.012 (the three behaviours the
  fold rows state).
- **Blast carried by**: `js/poll-manager.js` header pointer → A.U36.503 (4) (WEB); `js/render.js`/`html/style.css` comments
  → A.U23.45 (WEB); `js/templates.js`/`html/style.css` history comments → A.U36.507 (1)-(2) (WEB); Part N
  `web.poll_backoff_max_ms`/`web.device_watch_interval_ms` → M.SPEC.156; M.1.1 item 16 → A.U36.506 (2) (M.SPEC.153).
- **Kind**: rule, doc

### M.SPEC.117 H.5: generated-only definitions and every hint key
- **From**: A.U36.515 (1), A.U36.502 (2) (carried by A.U36.515 (1)), A.U23.09 (poll interval bound), A.U23.16
  (`defaultValue` goes), A.U23.18 (`statusPath`; errcount on any page), A.U6.19 (`format`), A.U6.27 + A.U2.21 (`codes`),
  A.U6.28 (`byteLength`), A.U6.29 (`shape`), A.U6.04 (hand-written files retired), A.U10.40 (key names).
- **Site**: `SPECIFICATION.md:4389-4426`.
- **Change**: `:4391-4426` → A.U36.515 (1) verbatim.
- **Resolved**: — (no conflict among the constituents)
- **Unit**: U36 (after U6/U23).
- **Depends**: A.U6.01-A.U6.05, A.U6.17, A.U6.19, A.U6.27-A.U6.29, A.U23.09, A.U23.16-A.U23.18, A.U23.20, A.U23.49,
  A.U36.504, A.U36.515.
- **Blast carried by**: L.7's build-information sentence → A.U36.502 (1) (M.SPEC.150); K.4/K.8/K.11 and C.11 hand-written
  definition mentions → A.U6.04 (M.SPEC.142/.143, M.SPEC.069).
- **Kind**: doc

### M.SPEC.118 H.5.1: the one entry point, the tags' meaning, the build rules, the proof
- **From**: A.U36.515 (2)-(3), A.U6.01 (`definitions_for_toml()`), A.U36.514 (5) (grammar floor → L.6.4), A.U0.16
  (`:4463` owner decisions), A.U20.25 (an untagged schema field or unreadable schema fails; `hidden`), A.U20.30 (the one
  warn-signal catalog), A.U15.17 (`WaitTimeNTP` 0 meaning), A.U36.500 blast (generator-owned paragraph cites H.1),
  M_DOCS gap 1 (g) (tag-line pointer; M.DOCS.092), A.U36.532 (`##` → `###`; M.SPEC.003); OR140.a (16) (a sensible
  number of decimals per value, from its source; the API keeps full resolution) (A-C review fold).
- **Site**: `SPECIFICATION.md:4427-4510`.
- **Change**: (1) `:4429-4431` → A.U36.515 (2). (2) `:4447-4450` → A.U36.514 (5)'s "The grammar floor — one line per
  tag, no `"` inside a quoted value — is L.6.4's." (3) After the tag description, A.U20.25's rule: "Every schema field
  of a tagged driver needs a `@web` tag, or `@web <Field> hidden="<reason>"` to leave it off the website on purpose; an
  untagged field or a schema constant that cannot be read at build time fails the build." (4) `:4463` head gains A.U0.16's
  sentence ("The nested body is kept and precision is a renderer-side `decimals` hint (owner, 2026-09-12, `12a616a`: …)"),
  then (A-C review fold): "The hint is every numeric value's, not one sensor's: each value the website shows carries
  `decimals` (2 or 3, a sensible number for the value) from its source — the `@web` tag's `decimals` field, or the
  build's default derived from the schema field where the tag gives none — carried by buildgen into the generated
  definitions; only the website rounds, the API keeps full resolution (owner, 2026-10-02)." How the build derives the
  default for an untagged numeric field is decided at execution, with its reason recorded (M_GEN).
  (5) `:4486-4490`: the SGP40 "0 means X" list keeps its fields (landed key names), `WaitTimeNTP`'s meaning per A.U15.17
  ("0 = never wait: one restore attempt on the first cycle"). (6) "What stays generator-owned": "H.4's 'mirrors the 6 REST
  endpoints 1:1'" → "H.1's placement rule"; the warn-signal sentence ("`_WARN_SIGNAL_WEB_CATALOG`, the same precedent …
  kept in sync by cross-reference/comment, not import, …") → "the `warn_co2`/`warn_voc`/`warn_hum` UI metadata, read
  with the schema by codegen and definitions alike from `buildgen/signals.py`'s one catalog". (7) `:4501-4510` →
  A.U36.515 (3).
- **Resolved**: M_DOCS gap 1 (g): A.U36.514 (2) puts the `@web`/`@web-group` rows and key sets into L.6.4's table (pinned
  by a test), so L.6.4 is the grammar's one home and H.5.1 states what the tags feed; no row is duplicated here. CLAUDE.md's
  pointer needs only L.6.4 — DOCS drops M.DOCS.092's "the `@web`/`@web-group` grammar H.5.1" half (gap for DOCS).
- **Unit**: Stage 1 U0 ((4)); Stage 2 U15 ((5)); Stage 3 U20 ((3), (6) catalog); Stage 3b U23 ((4)'s fold sentence, with
  the tag field, the generator's default and the renderer); Stage 4 U36 ((1), (2), (6) pointer, (7)).
- **Depends**: A.U0.16, A.U6.01, A.U15.17, A.U20.25, A.U20.30, A.U36.500, A.U36.514, A.U36.515, M.SPEC.003;
  M.GEN.017, M.GEN.018 (the tag field and the generated `decimals`), M.WEB.012, M.WEB.020 (the renderer).
- **Blast carried by**: L.4 bullet → A.U36.515 (4) (M.SPEC.147); L.6.4 rows → A.U36.514 (M.SPEC.149); `web_tag.py`
  comments → A.U36.514 (6) (GEN).
- **Kind**: doc

### M.SPEC.119 H.6: errcount and never-"Unchanged" field conventions
- **From**: A.U36.508 (heading, body), A.U36.504 (2) (never-"Unchanged" semantics), A.U19.02 + A.U9.03 (`lightCmdLED`
  "Failed" while a signal runs), A.S0930.30 (a refused system command answers "Failed"), A.U2.05 (an empty history slot),
  A.U20.38 (the build refuses a name collision), A.U23.11-A.U23.13, A.U23.19, A.U23.20, A.U6.25 (DNS history placed on
  Networking), A.U2.21 + A.U6.27 (the `codes` block), A.U15.12 (SCD30's config-store row), A.U20.16 (no H.6 text names
  per-instance maintenance keys; nothing to edit), A.U36.044 (the history-entry pointer to H.6.1); OR140.a (8)
  (reset-reason codes clickable like errno/wrnno), OR140.a (5) (the LED refusal tells the caller to retry) (A-C review
  fold).
- **Site**: `SPECIFICATION.md:4512-4532`.
- **Change**: A.U36.508's heading and body verbatim, with A.U36.504 (2)'s paragraph placed after "Errcount UX" and its
  "`"Failed"` when a system command is refused (a reset armed or a shutdown under way)" extended: "… or, for
  `LightCmdLED`, while a signal is still queued or running (owner, 2026-09-29) — a refusal that tells the caller to try
  again later (owner, 2026-10-02)"; the module-list paragraph gains "the build refuses two loggers, or two GET keys, of
  one name" (A.U20.38); after A.U36.508's "Each number is a button …" sentence (A-C review fold): "A readonly status
  code — `ResetReason`, `VOCState`, `FRCState` — is shown the same way: its number is a button that shows the code's
  description from the catalog on click (`ResetReason`: owner, 2026-10-02)."
- **Resolved**: A.U19.02 and A.U9.03 write the same `lightCmdLED` exception into `:4524-4528`, which A.U36.504 (2)
  replaces — the exception joins A.U36.504's sentence. A.U2.05's empty-slot fact lands in H.6.1 row 2 (M.SPEC.120), where
  the entry shape now lives.
- **Unit**: Stage 1 U9/U19 (the `lightCmdLED` clause on HEAD text); Stage 2 U36 (the section, with the fold's two
  clauses — the clickable codes land in U23, the retry wording with the LED handler before it).
- **Depends**: A.U9.03, A.U19.02, A.U20.38, A.U23.11-A.U23.13, A.U23.18-A.U23.20, A.U6.25, A.U6.27, A.U11.26, A.U15.12,
  A.U36.504, A.U36.508, A.S0930.30; A.U23.20 (2) (already makes `ResetReason` clickable, M.WEB);
  M.SRC_NET.122.
- **Blast carried by**: `asy_wifi_service.py:168-169` comment → A.U6.25 (SRC_NET); A.8's `lightCmdLED` row → M.SPEC.021;
  `DEVICE_REFERENCE.md` → A.U9.03 (DOCS).
- **Kind**: rule, doc

### M.SPEC.120 New H.6.1: the wire contract the client relies on
- **From**: A.U36.044, M_WEB gap 4 (a)-(b) (time-struct members; rows 7-9 after A.U23.19/M.WEB.041), A.U2.05 (the empty
  slot), A.U10.40 (key names), A.U19.01/A.U19.16/A.U23.13/A.U23.24/A.U23.25/A.U23.28/A.U11.31 (row contents).
- **Site**: new `### H.6.1 The wire contract the client relies on` after H.6.
- **Change**: A.U36.044's rule sentence and table, rows as its text gives them, with: row 1 → "time values are objects
  `{Year, Month, MDay, Hour, Minute, Second, Weekday, Yearday}`, never strings"; row 2 gains "a `num` of 0 marks an empty
  slot"; row 7 client cell → "`js/render.js`'s `statusPath` read"; row 8 → "maintenance fields are read by their `path`
  in the nested body; nothing is flattened | the driver's `get_dict_data()` keys | `js/definitions.js`
  `resolveFieldValue()`"; row 9 client cell → "the definitions' `options` (the mock derives them)"; row 5's server cell
  `api_response.py` → `asy_api_response.py`. H.6's history-entry sentence is A.U36.508's ("its shape is H.6.1 row 2").
- **Resolved**: M_WEB gap 4 (a)-(b): A.U36.044 predates A.U10.40's capitalised members (M.WEB.001) and A.U23.19's path
  reads (M.WEB.020); the landed facts are the rows.
- **Unit**: U36 (after U19/U23).
- **Depends**: A.U2.05, A.U10.40, A.U11.31, A.U19.01, A.U19.16, A.U23.13, A.U23.19, A.U23.24, A.U23.25, A.U23.28, A.U36.044,
  A.U36.508, M.WEB.001, M.WEB.020, M.WEB.041.
- **Blast carried by**: G.2's mirror entry points here → M.SPEC.111.
- **Kind**: rule, doc

### M.SPEC.121 H.7 intro and H.7.1 the connection ceiling
- **From**: A.U36.517 (6)-(7), A.U6.03 + A.U6.10 (every device), A.U23.32-A.U23.35 (live tier), A.U24.52 (a missing
  interpreter fails), M_SCR gap 5 (the smoke and live twins launch through `tests_js/_twin_process.js`), A.U14.12 (2)
  (`tcp_alloc()` source), A.U14.30 ("on admission"), A.U30.20 (placeability, not a percentage), A.U19.13 (1) (serving
  demand derivation), A.U19.08 (dropped connections traced; accept failures invisible), A.U24.34 (a clean refusal is a
  reset or EOF), A.U0.25 A29 (`:4557`) and A33 (`:4620-4622`), A.U0.33 C17/F18 (`:4608-4610`), A.U0.44 L26 (`:4642-4643`),
  A.U0.46 (same research topic as `:4622`), A.U5.04/A.U5.05 (`ServingLimits`), A.U8.18 (Part N citations), A.SDEP.14
  (2,324 B re-verified), A.U23.06 (2.2 requests/s cited), A.U36.532 (`### The connection ceiling` → `### H.7.1`),
  M.SPEC.042 (2) (H.7 repoint); OR137.a (1) (`HTTPDropped` is a 24-hour window) (A-C review fold: (8)'s sentence
  names the window; it lands with A.U19.08's sentence in its unit or, if that unit precedes U19's window counter, the
  phrase "in `HTTPDropped`'s 24-hour window (A.8)" lands with the counter in U19).
- **Site**: `SPECIFICATION.md:4534-4646`.
- **Change**: (1) `:4536-4545` → A.U36.517 (6) verbatim, its live-tier sentence gaining "each twin launched through
  `tests_js/_twin_process.js`", and its second proof layer written for the harness that replaces the deleted file (M_TWIN
  gap, M.TWIN.136): "`scripts/_digital_twin_scenarios.py`'s real-website scenarios boot, in a runner subprocess, the
  device `scripts/test.sh` built the site for, with `frozen_html` its real build, and drive real HTTP." (2) Heading → "### H.7.1 The connection ceiling (`max_connections`, `backlog`, lwIP pcbs)";
  `:4549-4554` → A.U36.517 (7). (3) `:4557` "(owner decision, evidence below)" → "(owner, 2026-09-24, `db3bf52`; evidence
  below)". (4) `:4563-4565` gains A.U14.12 (2)'s source parenthesis. (5) `:4601-4602` → A.U30.20's text; after the
  mechanism bullet, A.U19.13 (1)'s derivation paragraph with the per-device figures the L1 scenario writes (its build
  named). (6) `:4603` "**lwIP is never the constraint.**" → "**lwIP is never the constraint on admission.**". (7)
  `:4608-4613` → "**Refusals are expected, not failures** (owner, 2026-09-23, `84f3d57`): a connection counts until it has
  closed (H.7.1.1), so back-to-back clients see ~70 % refused at every limit; the device's own rejection count matches the
  host's exactly. It stays that way (owner, 2026-09-26: a connection counts until it has closed): …" (the reasoning
  sentence stays), then A.U0.33's "Four zero-think-time readers are a degradation check, not a contract — no crash, reboot,
  task end or `MemoryError` marker, full recovery once the load stops; a writer starved meanwhile is accepted (owner,
  2026-09-26: 'Very hypothetical test.'; confirmed 2026-09-28)." and A.U24.34's "A clean refusal is a reset or an EOF,
  nothing else; every load test also holds a floor on answered requests." (8) After the refusal bullet, A.U19.08's
  sentence: "A refusal, a refused head and a peer reset before the response are counted in `HTTPDropped`'s 24-hour
  window (A.8) and traced once per event (one history slot per run of identical codes); a failed `accept()` and an arrival past the backlog are
  invisible to the product — asyncio's server loop discards them (`extmod/asyncio/stream.py:160-164`)." (9)
  `:4620-4622` → A.U0.25 A33's "… an ad-hoc instrument, never a committed build or gate (owner, 2026-09-23, `bbb2306`: 'no
  twin32 to be kept at all'; both frozen twins, owner, 2026-09-29)". (10) `:4642-4643` → A.U0.44 L26's text. (11)
  `WebserverService` constructor mentions name its config objects (`ServingLimits`, `StaticSite`; A.U5.04/A.U5.05); the
  ceiling, timeouts and per-connection cost cite Part N (`web.max_connections`, `web.outer_cap_s`, `lwip.*`; A.U8.18).
- **Resolved**: (a) M.SPEC.042 (2) lists H.7 among B.14.4's citers; no landed H.7 sentence cites the `modlwip_eagain`
  subsection (the send path is B.14.2.1's, A.U14.30) — that repoint is void unless a landed sentence names it. (b) A.U0.33
  F18 and A.U19.14 both point at the "It stays that way" sentence; A.U19.14 defers to A.U0.33 — one text. (c) A.U36.532's
  numbering puts HEAD's H.7.1 under this section as H.7.1.1; the cross-reference in (7) reads "H.7.1.1". (d) A.U36.517 (6)
  describes the L2 proof as `tests/test_digital_twin_real_website_integration.py`, which U25 deletes (A.U25.46,
  M.TWIN.136): the landed text names the harness scenarios (M_TWIN gap; agent decision, OR2.c review).
- **Unit**: Stage 1 U0 ((3), (7) tags and reader sentence, (9), (10)); Stage 2 U14 ((4), (6)); Stage 3 U19 ((5) derivation,
  (8)); Stage 4 U24 ((7) refusal rule); Stage 5 U30 ((5) placeability); Stage 6 U36 ((1), (2), (11), numbering).
  A-C2 step order: A.U14.30's part lands in U19, not U14 (it needs A.U19.24, which lands in U19).
- **Depends**: A.U0.25, A.U0.33, A.U0.44, A.U5.04, A.U5.05, A.U6.03, A.U6.10, A.U8.18, A.U14.12, A.U14.30, A.U19.08,
  A.U19.13, A.U23.32-A.U23.35, A.U24.34, A.U24.52, A.U30.20, A.U36.517, A.U36.532, M.SCR (gap 5), M.TWIN.136.
- **Blast carried by**: `HEAP_FRAGMENTATION_MEASUREMENTS.md` archive references → unchanged (DOCS); I.1's free-heap sentence →
  A.U30.20 (M.SPEC.125); I.6's per-connection figures → A.U19.13 (2) (M.SPEC.132); Part N rows → M.SPEC.156.
- **Kind**: rule, doc

### M.SPEC.122 H.7.1.1 (HEAD H.7.1): a connection's real lifetime
- **From**: A.U36.532 (heading level), A.U14.03 (the reset-then-write mechanism), A.U2.19 (wrnno 49/50 named), A.U5.05
  (`ServingLimits` knob names), A.U8.05 + A.U8C.04 (Part N citations), A.SDEP.13 + A.SDEP.18 (re-checked at the pin).
- **Site**: `SPECIFICATION.md:4648-4679`.
- **Change**: heading → "#### H.7.1.1 A connection's real lifetime, and what it does to every instrument that holds one";
  the first bullet names wrnno 49 (the per-call close) and the second wrnno 50 (the outer cap) as the codes each logs
  (A.U2.19, at their landed numbers); `per_call_timeout_s`/`outer_cap_s` cite Part N (`web.per_call_timeout_s`,
  `web.outer_cap_s`) and `ServingLimits`; the fourth bullet's second sentence → A.U14.03's text verbatim (if the B0 build
  compiles `assert()` into rp2, it gains "(a debug build asserts instead)"). Under A.SDEP.13 (a) or a moved Microdot gap
  (A.SDEP.18), the bullet follows the re-checked source.
- **Resolved**: — (no conflict among the constituents)
- **Unit**: Stage 1 U2 (codes); Stage 2 U5 (knob names); Stage 3 U8 (Part N); Stage 4 U14 (mechanism); Stage 5 U36 (heading).
- **Depends**: A.U2.19, A.U5.05, A.U8.05, A.U14.03, A.U36.532.
- **Blast carried by**: `asy_webserver_service.py`/test/harness comments → A.U14.03 (SRC_NET, TEST_UNIT, HW_BENCH).
- **Kind**: doc

### M.SPEC.123 H.7.2 cross-browser coverage
- **From**: A.U36.517 (8), A.U36.532 (heading), A.U28.37 (install paragraph: xvfb, Edge key fingerprint, pinned micromamba),
  A.U28.17 (CI fails on a skipped engine), A.U28.18/A.U28.21/A.U28.22 (Xvfb and installer facts), A.U0.29 E04 (`:4709` tag),
  A.U6.11 (every device), A.U23.34 (full-ceiling tabs), A.SDEP.19 W36 (`:4543-4545`) and W-items (conditional), M_SCR gap 5
  (the smoke launches the twin through `tests_js/_twin_process.js`).
- **Site**: `SPECIFICATION.md:4681-4711`.
- **Change**: heading → "### H.7.2 Cross-browser coverage"; `:4681-4697` → A.U36.517 (8) verbatim, its first sentence's
  "boots the real twin" gaining "(through `tests_js/_twin_process.js`)"; the channel paragraph per A.U28.37: "(plus `xvfb`,
  since headless WebKitGTK still wants a display)" → "plus `xvfb`, which WebKitGTK and Firefox both need"; the Edge key is
  checked against its published fingerprint and micromamba is a pinned release checked by SHA-256; "That install is
  deliberately **unpinned**" → "That install is **unpinned** (agent, 2026-08-26, `7ff3c3c`)".
- **Resolved**: A.U0.29 tags "unpinned" for the conda-forge Firefox while A.U28.37 pins micromamba itself — both true (the
  binary is pinned, the packages it pulls are not); kept as two clauses.
- **Unit**: Stage 1 U0 (E04 tag); Stage 2 U28 (install facts); Stage 3 U36 (the rest).
- **Depends**: A.U0.29, A.U6.11, A.U23.34, A.U28.17, A.U28.18, A.U28.21, A.U28.22, A.U28.37, A.U36.517, A.U36.532.
- **Blast carried by**: `scripts/setup_cross_browser_toolchain.sh:39` comment → A.U0.29 (SCR); B.10.1 smoke bullet →
  M.SPEC.034.
- **Kind**: doc

### M.SPEC.124 H.8 and H.8.1: the web tooling, the test tier, CI
- **From**: A.U36.517 (9), A.U33.05 (2) (`npm audit`), A.U28.37 (CI mechanism, `tsconfig.base.json`, html-validate's built
  pages), A.U28.07/A.U28.16/A.U28.25/A.U28.26/A.U28.43, A.U6.05/A.U6.08/A.U6.09/A.U6.12, A.U23.05 (the poll-failure
  diagnostic), A.U23.10 + A.U23.26 + A.U5.18 (complexity ceilings at the measured maximum), A.U36.549 ("only ever ratchet
  down" gains its actor), A.U24.14 (fakes restored), A.U24.48 (every disable carries a reason), A.U23.31 (the mock against
  the REST reference), A.U7.10 (`npm test` ends with the summary block, E.10), A.U7.21 (live twins gate on both markers),
  A.U8.21 (JS harness budgets in Part N), A.SDEP.04 (no package version named), A.SDEP.19 W34 (coverage `exclude`,
  conditional), M_WEB gap 4 (d) (H.8.1 names `tests_js/_expected_display.js`).
- **Site**: `SPECIFICATION.md:4713-4777`.
- **Change**: (1) First paragraph gains A.U36.517 (9)'s text after "Vitest in real-browser mode (…)", A.U7.10's "`npm test`
  ends with the runner summary block (E.10)", and A.U33.05 (2)'s `npm audit` sentence; the TypeScript clause names
  `tsconfig.base.json` (A.U28.25); html-validate's role names the built-page run (A.U28.43); the coverage clause keeps its
  `exclude` sentence unless W34 finds the re-parse fixed (then it goes with its test, A.SDEP.19). (2) ESLint paragraph:
  `:4735-4737` "`js/poll-manager.js`'s "Poll failed:" is the poll loop's only failure diagnostic and is asserted by a test" →
  A.U23.05's "a failed GET shows the section's banner (logged once per failure episode) and is retried with a capped
  back-off; a PUT is never retried"; gains "every disable comment names its rule and a reason (enforced)" (A.U24.48);
  `:4739-4741` the ceilings and their figures as A.U5.18's pin leaves them after A.U23.10/A.U23.26's splits, and "and only
  ever ratchet down" → "and only ever ratchet down (agent, <date of the introducing commit>)" (A.U36.549). (3) "CI
  mechanism" `:4746-4753` → A.U28.37's text (the full input list; "a push compares against the last commit CI passed");
  the web coverage run's test result gates, its reports do not (A.U28.16). (4) H.8.1 gains: "The browser- and Node-safe
  expected-display helper is `tests_js/_expected_display.js`; `field-format.js` is pure formatting with no DOM
  dependency." and A.U24.14's "every JS fake timer and spy is restored on every path".
- **Resolved**: M_WEB gap 4 (d) — H.8.1's worked example (`field-format.js`'s `FormattableField`) stays only if that typedef
  survives M.WEB.012/.069 (grep at landing); otherwise the example names the landed typedef.
- **Unit**: Stage 1 U5 (ceilings); Stage 2 U7 (summary block); Stage 3 U23 (poll diagnostic, ceilings re-measured); Stage 4
  U24 (disable reasons, fakes); Stage 5 U28 (CI); Stage 6 U33 (`npm audit`); Stage 7 U36 ((1) A.U36.517 (9), the actor
  tag).
- **Depends**: A.U5.18, A.U6.05, A.U6.08, A.U6.09, A.U6.12, A.U7.10, A.U7.21, A.U8.21, A.U23.05, A.U23.10, A.U23.26,
  A.U23.31, A.U24.14, A.U24.48, A.U28.07, A.U28.16, A.U28.25, A.U28.26, A.U28.37, A.U28.43, A.U33.05, A.U36.517,
  A.U36.549, M.SPEC.086.
- **Blast carried by**: B.10/B.10.1 → M.SPEC.033/.034; B.16 → M.SPEC.044; I.4(e) gate list → M.SPEC.129; Part N JS rows →
  M.SPEC.156.
- **Kind**: doc

## SPECIFICATION.md — Part I (`:4781-5163`, plus I.6 from `:5183-5313`)

### M.SPEC.125 Part I intro and I.1: research findings, sourced and current
- **From**: A.U30.02 (7) (intro scope sentence) and Blast (`:4800-4802` accumulation-loop sentence), A.U14.07 (two
  prior-art claims), A.U14.08 (1)-(2) (two uncited claims), A.U14.13 + A.U0.56 L29 (`:4816-4818` measured heap, one
  sentence), A.U30.20 (`:4855-4857` no free-heap target), A.U8.06 (the GC pause figure is a Part N basis; no edit),
  A.C.03 (4) + A.C.10 (post-build free heap on the named image), A.U10.45 (no tuple here), C7 names.
- **Site**: `SPECIFICATION.md:4783-4857`.
- **Change**: (1) `:4785-4787` → A.U30.02 (7)'s scope sentence. (2) `:4796-4802`: `LockableBuffer`/`AsyFramChunk` →
  `RegionBuffer`/`FRAMChunk` (C7); "every accumulation loop in `src/` either bounds total size or already guards the one
  failure that matters, `asy_uart_driver.py`" → "every accumulation loop is classified in I.2". (3) `:4805-4806`
  "`system_service.py`'s task-supervisor loop" → "`asy_system_service.py`'s supervisor". (4) `:4814-4816` → A.U14.08 (1)
  (the issue link, written only after the page is read; else the sentence goes). (5) `:4816-4818` → A.U14.13's text (its
  last clause "the RAM cost is a fact of this board (agent, 2026-09-07)" is A.U0.56's relabel); the GC-heap figure is
  re-read from the build in force at landing and, after phase C, from the release image (A.C.03 (4)). (6) `:4831-4833`
  and `:4841-4844` → A.U14.07's two texts. (7) `:4855-4857` → "**No free-heap target is published.** No MicroPython
  maintainer, doc or web framework states one; the documented point is contiguity: an allocation fails when no contiguous
  run is large enough, however much RAM is free (`docs/reference/constrained.rst:354-357`). This project sets none
  either: serving memory is proven as placeability of the connection ceiling's worst concurrent demand (H.7.1), and free
  heap is recorded, never required (agent, 2026-09-19; the owner retired the old floors the same day)." (A.U14.08 (2) +
  A.U30.20).
- **Resolved**: A.U14.13 and A.U0.56 edit one sentence — A.U14.13's text carries A.U0.56's tag (both say so); A.U14.08 (2)
  and A.U30.20 rewrite `:4855-4857`'s two halves — joined in (7).
- **Unit**: Stage 1 U14 ((4)-(6), (7) first half; A.U0.56 is U14's per its Unit); Stage 2 U30 ((1), (2), (7) second half);
  Stage 3 U10/U36 (C7 names); Stage 4 phase C (figure).
- **Depends**: A.U0.56, A.U14.07, A.U14.08, A.U14.13, A.U30.02, A.U30.20, A.C.03.
- **Blast carried by**: `tests_hardware/README.md:633-634` field account → A.U14.08 (3) (HW_BENCH); H.7's percentage →
  M.SPEC.121.
- **Kind**: doc

### M.SPEC.126 I.2: the allocation-site catalog
- **From**: A.U30.02 (2)-(6), (8), (9) (the catalog, its rows and verdicts, the placement lens, the UART row, the two dated
  paragraphs as rows), A.U30.03 (the catalog's L0 checks; I.2's opening names the file), A.U0.12 (`:4870` UART wording,
  superseded), A.U0.39 L30 (`:4893` owner decisions head), A.U13.01 (`:4877-4891` shrinks; design in G.2), A.U13.02 +
  A.U30.21 (per-read memoryview allocation), A.U30.11 (the CRC row), A.U12.01 (CRC32 in small ints), A.U18.02 + A.U18.03 +
  A.U18.16 (DNS/NTP receive bounds), A.U30.07 (bursts into the caller's buffer), M_SRC_CORE GAP-G9 (`FRAMManager._chunks`),
  A.U36.013 (§M7/§M8 cited by the owner's closure; no edit), M.SRC_CORE.091; OR143.a (1)-(2), (5) (the UART receive
  allocations chunked and capped; the deferred owner question answered), OR141.a (4) (d) (the receive DMA ring: one
  allocation in `setup()`, measured), OR137.a (1) (the hourly window counter's fixed bins) (A-C review fold).
- **Site**: `SPECIFICATION.md:4859-4903`.
- **Change**: I.2 → A.U30.02 (2)'s "Allocation-site catalog — every `src/` and generated module" with its opening rule
  block, which names `tests_scripts/test_memory_catalog.py` (A.U30.03: every `src/` module has a section, every run-phase
  long-lived allocation is listed); rows per A.U30.02 (3)-(6), (8), with: (a) the UART rows in the owner's end state (A-C
  review fold; A.U30.02 (6)'s "the owner's deferred question" wording is superseded by OR143.a): "client-controlled by
  the UART peer and bounded before allocation: a train with no caller destination is assembled in pieces of at most
  `chunk_bytes` (G.2's piece primitive), a declared size above `max_transfer_bytes` is refused through the withheld ACK
  before anything is allocated, and `readline_until_complete()` is capped by the same value and never grows by
  concatenation; no caught `MemoryError` stands at these sites (owner, 2026-10-05; J.8)" and "the receive DMA ring —
  construction phase (the link's `setup()` in the one-time setup list), long-lived, fixed by the device TOML's ring size,
  allocated once and never reallocated by a task restart; its alignment padding fixed; net heap cost and largest free
  block before and after: <the twin's figure> on the twin, <the board's figure> on `dev` (owner,
  2026-10-05)" — the twin figure written when the catalog lands (measured in U25), the `dev` figure after phase C — A.U0.12's interim "bounded, or
  unbounded pending owner question 1 (BACKLOG.md)" is the U0 text they replace (A.U0.12's U0 wording itself
  changes: "bounded, or — the UART receive allocations — to be chunked and capped (owner, 2026-10-05; J.8)", since the
  chunking became work before B0 and no owner question is entered, M.DOCS.067); (b) the I2C scratch row carries A.U13.02's sentence as A.U30.21 corrects it ("a held view of the scratch
  halves it: one slice per read"), A.U30.07's burst rows, and A.U30.02 (8)'s fallback verdict; (c) the `crc_checks`
  row is A.U30.11's text with the owner quote and date; (d) the captive-DNS and UDP rows state "one question of at most
  255 octets, a reply of at most 287 B" and "512 B for DNS (RFC 1035 §4.2.1), 48 B for NTP (RFC 5905 §7.3)" (A.U18.02,
  A.U18.03, A.U18.16); (e) the FRAM manager row gains "`FRAMManager._chunks` grows once per allocation at construction,
  never at run time" (GAP-G9); (f) the owner-decisions block head (`:4893`) → "**Owner decisions from the heap-fragmentation
  work** (owner, 2026-09-18 and 2026-09-24; …)" with each bullet keeping its quote, as catalog rows of their modules;
  (g) (A-C review fold) the `asy_base_classes.py` section gains the hourly window counter's row — construction phase,
  long-lived, fixed (24 small-int bins), no allocation per event, read or hour change (G.2, A.8).
- **Resolved**: (a) A.U0.12 (U0) rewords `:4870`; A.U30.02 (U30) replaces the paragraph by the catalog with a UART row
  stating the deferred question — A.U30.02 is the end state, its UART row text replaced by the chunked and capped
  allocations of OR143.a and the ring row of OR141.a (4) (A-C review fold). (b) A.U13.01 (U13) shrinks `:4877-4891` to its measurement
  role; A.U30.02 (8) turns it into a row (U30) — the row keeps A.U13.01's measurement line. (c) A.U13.02's "a held
  `memoryview` … would halve the first figure" becomes fact after A.U30.21 — A.U30.21's wording.
- **Unit**: Stage 1 U0 (A.U0.12, L30 tag); Stage 2 U13 (A.U13.01, A.U13.02); Stage 3 U18 (DNS/UDP bounds); Stage 4 U30 (the
  catalog, after U10-U28 and A.U30.04-.08, A.U30.21; the UART rows after the ring (U13), the cap and chunking (U13/U17)
  and the twin's measurement (U25), and the window counter's row (U19)); Stage 5 phase C (the dev figure of the ring row).
- **Depends**: A.U0.12, A.U0.39, A.U12.01, A.U13.01, A.U13.02, A.U16.05, A.U17.03, A.U18.02, A.U18.03, A.U18.16, A.U30.02,
  A.U30.03, A.U30.07, A.U30.11, A.U30.21, M.SRC_CORE.091; M.SRC_NET.221, M.SRC_NET.220, M.SRC_NET.202 (the ring, the cap
  and the chunking), M.SRC_CORE.133 (the window counter's row), M.TSC.230, M.TEST_HELP.028 (the twin's before/after heap measurement), M.HW_DEV.159, M.HW_DEV.160 (the dev
  measurement).
- **Blast carried by**: BACKLOG `:925-935` placement item and the owner-question list → A.U30.02 (9)/A.U0.12 (DOCS); G.2 rows
  citing I.2 → M.SPEC.111; `tests_scripts/test_memory_catalog.py` → A.U30.03 (TSC).
- **Kind**: rule, doc

### M.SPEC.127 I.3: bounded response assembly
- **From**: A.U19.11 (pieces in bytes, one copy), A.U5.04 + A.U5.05 (`chunk_bytes` from `ServingLimits`/`StaticSite`),
  A.U31.18 (per-write `wait_for_ms()`), A.U10.41 (`NTPHost` bounded at 253), A.U0.33 W3 (`:4926` tag) and `:4950`
  (superseded), A.U19.05 (`_StaticRoutes.serve()`), A.SDEP.18 (the mid-headers text states the upstream behaviour at the
  pin), A.U36.548 (G9/R11: dated measurements stay as evidence).
- **Site**: `SPECIFICATION.md:4905-4991`.
- **Change**: (1) `:4910-4912` "pieces of at most `chunk_bytes`" → "pieces of at most `chunk_bytes` bytes" and "hands
  Microdot `Response(iter(pieces), ...)`" gains "(already encoded, one copy)"; "one `WebserverService` constructor
  parameter" → "one `ServingLimits` field". (2) `:4923` "a per-write `asyncio.wait_for()`" → "a per-write
  `asyncio.wait_for_ms()`". (3) `:4926` "(+17 %, 2026-09-25; BACKLOG.md W3)" → "(+17 %, 2026-09-25) — accepted as the price
  of this bound (owner, 2026-09-26)". (4) `:4939-4951` → the same paragraph at `NTPHost`'s RFC 1035 bound: "the longest
  string any schema permits is `NTPHost`'s 253 characters (RFC 1035, `asy_ntp_client.py`'s `_VAL_NTP_HOST`), giving a
  ~255 B piece on `/networking`, inside the cap"; the 2026-09-25 silicon measurement at 1,024 characters stays as a dated
  measurement of the bound it superseded ("a fourfold longer value still fitted"), and "Nothing to change here — a shorter
  `NTP_Host` bound is the lever, and the owner settled it — but do not read …" goes (the bound is now the lever applied).
  (5) `:4958` static paragraph names `_StaticRoutes.serve()`; the mid-headers sentence follows A.SDEP.18's re-check.
- **Resolved**: A.U0.33 (U0) re-dates the `NTP_Host` lever "re-decided when the REST API's key names are harmonised"; A.U10.41
  (U10, after A.U10.40's harmonisation) applies it — the 253 bound is the end state and A.U0.33's `:4950` sentence lives
  only between U0 and U10.
- **Unit**: Stage 1 U0 ((3), A.U0.33 `:4950`); Stage 2 U5 ((1) names); Stage 3 U10 ((4)); Stage 4 U19 ((1), (5)); Stage 5
  U31 ((2)).
- **Depends**: A.U0.33, A.U5.04, A.U5.05, A.U10.40, A.U10.41, A.U19.05, A.U19.11, A.U31.18, A.SDEP.18.
- **Blast carried by**: the I.3 hammer test names and `test_g3_…` piece test → A.U10.41 (TEST_UNIT); BACKLOG `:484-513` →
  A.U10.41 (DOCS).
- **Kind**: doc

### M.SPEC.128 I.4 (a)-(d): the criterion, degrade, restart, watchdog; the C stack
- **From**: A.U30.01 (1) (one criterion text), A.U0.38 V09 (`:5006-5007`, superseded), A.U10.45 (`(MemoryError, OSError)`),
  A.U11.03 + A.S0930.41 (`:5014-5016` reset path), A.U20.06 (supervisor split names), A.U30.18 (5) (new (d.1)),
  A.S0930.14 + A.S0930.30 (the shutdown sequence's allocation is fixed).
- **Site**: `SPECIFICATION.md:4995-5016`.
- **Change**: (1) (a)'s "Not a blanket policy on every `asyncio` primitive (F.2) — only where …" sentence → A.U30.01 (1)'s
  "**Which call sites catch.**" text verbatim; "catches `(OSError, MemoryError)`" → "catches `(MemoryError, OSError)`".
  (2) (c) "`start_and_check_tasks()` already restarts any task" → "the supervisor (`supervise_tasks()`) restarts any task".
  (3) (d) "escalates past repeated restarts to `reboot_system()`" → "escalates past repeated restarts to the reset path
  (`_reboot()`)". (4) New "(d.1) **The C stack is a budget too** (F.1): a stack-check error is never a routine failure —
  the handler that catches it records it (`report_if_fatal()`) and the supervisor reboots." (A.U30.18 (5), with A.U30.19's
  primitive named). (5) After (d): "The controlled shutdown sequence allocates a fixed amount (one task, one 256-byte FRAM
  erase unit) and needs no threshold (A.8)." (A.S0930.30).
- **Resolved**: A.U0.38 V09 (U0) rewrites `:5006-5007`'s middle; A.U30.01 (U30) replaces the sentence with the one criterion
  (it says V09's three rewrites are superseded, the owner quote landing once, here).
- **Unit**: Stage 1 U0 (V09); Stage 2 U10 (tuple order); Stage 3 U11/U20 ((2), (3)); Stage 4 U30 ((1), (4)); Stage 5 U36
  ((5), with A.S0930.30's docs pass).
- **Depends**: A.U0.38, A.U10.45, A.U11.03, A.U20.06, A.U30.01, A.U30.18, A.U30.19, A.S0930.14, A.S0930.30, A.S0930.41.
- **Blast carried by**: F.2's pointer → M.SPEC.094; CLAUDE.md memory criterion bullet → A.U30.01 (3) (DOCS).
- **Kind**: rule, doc

### M.SPEC.129 I.4 (e)-(f): zero `MemoryError`s at the reactive default; the gates; the threshold
- **From**: A.U0.43 (`:5018-5020` head tag), A.U7.05 + A.U27.01 (both gates fail closed on a missing log), A.U14.05 (the
  two wordings need room for the message), A.U20.04 (the boot entry reserves the emergency buffer), A.U7.21 + A.U7.23 (the
  gates named, JS live twins and the cross-browser smoke among them), A.U30.17 (2) + A.U35.25 (the twin sampler is the one
  twin exception, kept while a sparser interval agrees), A.U30.14 (`gc.threshold()` confined), A.U8.14 (Part N), A.C.09
  (the release-proof record), A.U30.12/A.U30.13 (hammers run at the file's stage; no SPEC edit).
- **Site**: `SPECIFICATION.md:5018-5089`.
- **Change**: (1) (e) head gains "(owner, 2026-09-26)". (2) `:5028-5032` gains "a missing, unreadable or empty log fails the
  gate, in the unit and the twin tier alike". (3) `:5034-5050` "All four gates match two spellings" → "Every memory gate
  matches two spellings", and the gate list names each gate instead of a count — the unit tier (`scripts/test.sh`), the twin
  tier (`scripts/_digital_twin_ci_suite.py`), the two real-hardware soak/hammer gates, the JS live twins and the cross-browser
  smoke (`tests_js/_memory_markers.js`) — all kept in agreement by `tests_scripts/test_memory_error_gate_agreement.py`; after
  "there is no third wording in the pinned source)", A.U14.05's inserted text verbatim (the reservation is A.U20.04's
  `micropython.alloc_emergency_exception_buf(100)`). (4) `:5062-5076` keeps the sampler's mechanism and its 2026-09-14
  measurement; its last sentence → A.U30.17 (2)'s "It is the twin's one exception (owner, 2026-09-26), kept while a sparser
  sampling interval gives Run 11 the same verdict; every other twin run collects nothing." — rewritten to A.U35.25's
  outcome when it lands (kept, or removed with its paragraph). (5) (f) `:5079-5081` "Every generated boot entry
  (`buildgen.codegen.generate_boot_entry_source()`, formerly the hand-written `boot_entry/*_boot.py`) sets
  `gc.threshold(32768)`" → "The generated boot entry sets `gc.threshold(32768)` (its Part N row, by the ID A.U8.14 lands) — the one
  `gc.threshold()` call outside the test runners, checked by `tests_scripts/test_gc_collect_sites.py`"; "the twin CI was the
  only place the shipped value was exercised at all until 2026-09-21" goes (history). After phase C: "Release proof:
  <image>, both stages, <date>."
- **Resolved**: A.U7.21 removes the count ("FOUR") so it cannot drift; the SPEC list names the gates the landed tree has.
- **Unit**: Stage 1 U0 ((1)); Stage 2 U7 ((2) unit, (3) gate list); Stage 3 U8 (Part N); Stage 4 U14/U20 ((3) A.U14.05
  with A.U20.04 in the same commit); Stage 5 U27 ((2) twin); Stage 6 U30 ((4), (5)); Stage 7 U35 ((4) outcome); Stage 8
  phase C (release proof).
- **Depends**: A.U0.43, A.U7.05, A.U7.21, A.U7.23, A.U8.14, A.U14.05, A.U20.04, A.U27.01, A.U30.14, A.U30.17, A.U35.25,
  A.C.09.
- **Blast carried by**: CLAUDE.md memory rule gate wording → A.U7.21/A.U36.546 (DOCS); `test_memory_error_gate_agreement.py`
  comment → A.U14.05 (TSC); `digital_twin/README.md` sampler paragraph → A.U0.43/A.U30.17 (TWIN).
- **Kind**: rule, doc

### M.SPEC.130 I.4 (f.1), (g) and the standing rule: the boot-confined collects
- **From**: A.U11.10 (both lists run by `SystemService`), A.U20.06 (`start_tasks()`), A.U27.21 (the AST checker, aliases
  included), A.U30.17 (3) (the checker covers tests, twin and device scripts), A.U25.61 (the flash-tier layout check reads
  the twin's bound), A.U36.546 + A.U30.10 + M_DOCS gap 1 (e) (the run-phase figure; M.DOCS.089), A.U0.43 (`:5145` tag),
  A.U20.05 (threshold set after the device-module import; no SPEC edit); OR141.a (4) (d) and OR143.a (5) (the UART
  receive ring is a setup-list survivor; the boot contiguity test asserts where it lands) (A-C review fold).
- **Site**: `SPECIFICATION.md:5091-5146`.
- **Change**: (1) `:5091-5101` "the generated setup batch (`buildgen.codegen`'s `_emit_build_system()`, one before the batch
  and one after each module's `feed_watchdog()`) and `SystemService.start_and_check_tasks()`'s task-starter loop (one before
  the loop, one after each starter)" → "both run by `SystemService`: `run_setups()` (one before the batch and one after each
  setup's feed) and `start_tasks()`'s starter loop (one before the loop, one after each starter)". (2) `:5114-5121` →
  "Confined mechanically: `scripts/_check_gc_collect_sites.py`, one AST checker run by `scripts/lint.sh` and
  `tests_scripts/test_gc_collect_sites.py`, allows a `gc.collect()` in `src/` only in `asy_system_service.py`'s
  `run_setups()` and `start_tasks()` — aliases included — and none under `buildgen/`; both were verified to bite on an
  injected call." followed by A.U30.17 (3)'s sentence (tests, twin, device scripts). (3) The effect paragraph names the
  flash-tier layout check that reads the twin's bound (A.U25.61). The same paragraph gains (A-C review fold): "A
  `uart_link` instance's receive DMA ring is one of these survivors: allocated once in the link's `setup()`, a unit of
  the setup list, so the placement collect after it puts the ring with the long-lived objects; the boot contiguity test
  asserts where it lands on `dev`, and the net heap cost and largest free block before and after it are I.2's (owner,
  2026-10-05)." (4) After the measured-effect paragraph, the run-phase
  figure in A.U30.10's description: "At `gc.threshold(32768)` the run phase keeps the boot placement gain: the largest
  free block is 80 % of free four seconds after the task-starter list, against 12 % at the reactive default (`dev` board,
  MicroPython v1.29.0, 2026-09-19; `HEAP_FRAGMENTATION_MEASUREMENTS.md` archive §7H.3)." (5) `:5145` "This is a standing
  rule, not a one-time audit finding" → "A standing rule (owner, 2026-09-26), not a one-time audit finding".
- **Resolved**: M_DOCS gap 1 (e): A.U36.546 writes the figure "recorded 2026-09-21" from `12640c2`; A.U30.10 (U30) traced it
  to `dev`, v1.29.0, 2026-09-19, archive §7H.3 — A.U30.10's description is the text (the executor confirms the § at landing).
- **Unit**: Stage 1 U0 ((5)); Stage 2 U11/U20 ((1), with the codegen change, one commit); Stage 3 U25 ((3) and its fold
  sentence, with the contiguity assertion on the ring — the ring lands in U13, earlier); Stage 4 U27 ((2) checker);
  Stage 5 U30 ((2) scopes, (4)).
- **Depends**: A.U0.43, A.U11.10, A.U20.06, A.U25.61, A.U27.21, A.U30.10, A.U30.17, A.U36.546; M.SRC_NET.222 (the
  ring in `setup()`), M.TSC.230 (the boot contiguity test's assertion on the ring).
- **Blast carried by**: CLAUDE.md memory rule's (f.1) sentence and the 80/12 figure → M.DOCS.089 (DOCS); A.7 step 16 →
  M.SPEC.020; `scripts/lint.sh` messages → A.U11.10/A.U27.21 (SCR).
- **Kind**: rule, doc

### M.SPEC.131 I.5: the board's confirmation, current state
- **From**: A.U36.548 (2).
- **Site**: `SPECIFICATION.md:5150-5162`.
- **Change**: A.U36.548 (2)'s two rewrites verbatim ("Confirmed on the board (2026-09-08): …"; "nothing from this audit
  remains open pending hardware" deleted); "(Part F.5.3 for the 1.29 figures)" → "(F.5.3 for the figures at the pin)".
- **Resolved**: — (no conflict among the constituents)
- **Unit**: U36.
- **Depends**: A.U36.548.
- **Blast carried by**: —.
- **Kind**: doc

### M.SPEC.132 I.6 back in Part I: the request-body cap at the end state
- **From**: A.U36.026 (the move), M.SPEC.003 (the same move, A.U36.532 (2)), A.U19.07 (the negative-length hole), A.U19.13
  (2) (`max_connections` 6), A.U10.41 (`NTPHost` 253; margins re-derived), A.SDEP.06 (`:5197` Microdot tag at the re-vendored
  version), A.U0.44 L32 (`:5243` tag) and A.C.13 (the silicon result), A.U0.25 A35 (`:5301` tag; "F11" goes), A.U0.33 B06
  (`:5307-5311` deleted), A.U1.18 (`:5309` path; void with B06).
- **Site**: `SPECIFICATION.md:5183-5313`, moved after I.5.
- **Change**: (1) Move first (A.U36.026; M.SPEC.003 executes it at U36 — the content edits below land on the block where it
  stands at their unit). (2) `:5197` "Verified against the vendored v2.6.2" → the re-vendored tag (A.SDEP.06). (3)
  `:5202-5206` and `:5211-5213` → A.U19.13 (2)'s text at 6 (6 × 16,384 = 98,304 B before the fix; 6 × 2,048 = 12,288 B now),
  with the pointer to H.7.1's derivation. (4) After the ordering paragraph, A.U19.07's sentence: "A negative
  `Content-Length` is refused with the head, before Microdot reads anything (`readexactly(n)` with `n < 0` reads everything,
  F.1)." (5) `:5208-5222` re-derived at `NTPHost`'s 253 bound: the largest legitimate body and the per-route figures are
  written as `tests_scripts/test_request_body_cap_headroom.py` computes them at landing; "dominated by `NTP_Host`'s
  1024-character bound (1,038 B of it)" follows. (6) `:5243` "never a hardware-confirmed one" → "not hardware-confirmed
  (agent, 2026-09-19, `1ce5d84`)", replaced after phase C by A.C.13's result: "On silicon (<date>): an oversized body is
  refused with no body read." (7) `:5301` "(owner's decision; F11, …)" → "(owner, 2026-09-19, `ac8d404`; …)". (8)
  `:5307-5311` ("Related, deliberately not changed: …") deleted.
- **Resolved**: (a) A.U36.026 and A.U36.532 (2) both move I.6 — one move (M.SPEC.003). (b) A.U1.18's `:5309` repath falls
  inside B06's deletion — void. (c) The W5 paragraphs measure `max_connections = 4` on 2026-09-19 — dated measurements of
  that image, kept (C2).
- **Unit**: Stage 1 U0 ((6) tag, (7), (8), (2) if Microdot moved); Stage 2 U10 ((5)); Stage 3 U19 ((3), (4)); Stage 4 U36
  (move); Stage 5 phase C ((6) result).
- **Depends**: A.U0.25, A.U0.33, A.U0.44, A.U10.41, A.U19.07, A.U19.13, A.U36.026, A.SDEP.06, A.C.13, M.SPEC.003.
- **Blast carried by**: `test_request_body_cap_headroom.py`'s pinned maxima → A.U10.41 (TSC); Part N body-cap row →
  M.SPEC.156.
- **Kind**: doc

## SPECIFICATION.md — Part J (`:5166-5182`, `:5314-5699`)

Part J's class and module names follow C7 (`UARTComm` for `UART_Comm`, `UARTLinkDriver` for `UartLinkExerciser`,
`CRCPass` for `CRC_Pass`, `asy_crc_checks.py`, `asy_framing_codecs.py`, `FramingPass`, `RegionBuffer`); every `errno`/
`wrnno` number follows the catalog (A.U2.20, A.U2.23) at the unit that renumbers it. No Part J edit below changes the
protocol: each is spec text (the Class A/B entries are their code actions').

### M.SPEC.133 Part J intro and J.1: scope, provenance, the changelog
- **From**: A.U1.18 (`:5170`, `:5322-5323` legacy paths), A.U36.027 (`:5318-5319` BSEC scope; `:5331` errno tag), A.U2.20 +
  A.U2.23 (`:5331` errno), A.U0.30 (`:5338` owner tag), A.U0.38 V01 + A.U36.025 + A.U34.01 (`:5343-5344` post-audit only, one
  wording), A.U17.08 (`:5346-5347` the changelog's lifecycle), A.U17.11 (the constants-table check).
- **Site**: `SPECIFICATION.md:5166-5182`, `:5314-5355`.
- **Change**: (1) `:5170` → `legacy/firmware/python/IndividualDrivers/asy_uart_comm.py`. (2) `:5318-5319` → A.U36.027's text.
  (3) `:5322-5323` → `legacy/dev_drivers/asy_bsec_driver.py`, `legacy/dev_drivers/sensortask-dev.py`. (4) `:5331` "is refused
  (`errno` 15)" → "is refused (`errno` <n>; agent, 2026-09-13)". (5) `:5338` "and is owner-validated over many real
  transmissions" gains "(owner, 2026-09-11)". (6) `:5343-5344` "reconciling it is outside this project's scope (owner,
  2026-09-24)" → "reconciling it is post-audit only (owner, 2026-09-25)". (7) `:5346-5347` "— a temporary file, deleted once
  the C side is reconciled." → "— kept until the post-audit C reconciliation deletes it."; the bullet gains
  "`tests_scripts/test_uart_changelog.py` fails when a module constant changes without the changelog's constants table
  following it."
- **Resolved**: A.U0.38, A.U36.025 and A.U34.01 word the `arduino/` exclusion — one wording ("post-audit only (owner,
  2026-09-25)"), as A.U34.01 asks.
- **Unit**: Stage 1 U0 ((5), (6)); Stage 2 U1 ((1), (3)); Stage 3 U2 ((4) number); Stage 4 U17 ((7)); Stage 5 U36 ((2), (4) tag).
- **Depends**: A.U0.30, A.U0.38, A.U1.18, A.U2.20, A.U2.23, A.U17.08, A.U17.11, A.U34.01, A.U36.025, A.U36.027.
- **Blast carried by**: BACKLOG `:839-847` → A.U36.027 (DOCS); CLAUDE.md `:123-125` → A.U17.08/A.U0.38 (DOCS); README temporary-docs
  note → A.U17.08 (DOCS).
- **Kind**: doc

### M.SPEC.134 J.2-J.4: role model, frame format, transactions
- **From**: A.U12.05 (COBS delimiter fact into J.3), A.U17.22 (`max_frame`), A.U12.03 (no J.3 change), A.U1.18 (`:5394`
  path), A.U0.25 A19 (`:5416` owner tag), A.U17.16 (J.4 GET `CHUNKS`), A.U0.28/A.U0.49 (comments only; J text unchanged),
  A.U24.01 (tests keep J.3's layout as an independent copy; no edit).
- **Site**: `SPECIFICATION.md:5357-5455`.
- **Change**: (1) J.3 `:5384-5391`: names as landed (C7); after "…a coordinated flag day (changelog A11), not a local
  decision." A.U12.05's inserted text verbatim, then A.U17.22's "A delimited codec's `max_frame` is the raw frame
  (header, payload and CRC); `UARTComm` refuses one smaller than that." (2) `:5394` → `legacy/firmware/python/
  IndividualDrivers/asy_uart.py`; `:5398` `src/crc_checks.py` → `src/asy_crc_checks.py`. (3) `:5416` "(author-confirmed
  rationale, 2026-09-11)" → "(owner, 2026-09-11, `7e8cf44`)". (4) J.4 GET paragraph gains A.U17.16's "A GET frame
  declaring any other `CHUNKS` is rejected like any invalid frame (no ACK)."
- **Resolved**: A.U12.05 notes J.3's "(changelog A11)"/"(… A7)" pointers cite a temporary file; they stay while
  `UART_C_PORT_CHANGELOG.md` exists (kept until the post-audit reconciliation, M.SPEC.133) and resolve at A.U0.08's check.
- **Unit**: Stage 1 U0 ((3)); Stage 2 U1 ((2) path); Stage 3 U10 (C7 names); Stage 4 U12 ((1) COBS); Stage 5 U17 ((1)
  `max_frame`, (4)).
- **Depends**: A.U0.25, A.U1.18, A.U10.37, A.U12.05, A.U17.16, A.U17.22.
- **Blast carried by**: G.2 frame-codec entry → M.SPEC.111; C.3.2 zero-length line → A.U12.03 (M.SPEC.050).
- **Kind**: doc

### M.SPEC.135 J.5: timing, recovery and the UART recovery ladder
- **From**: A.U17.33 (the ladder paragraph), A.U17.06 (a stale hold-off expires), A.U17.17 (a validated command resets
  the listen backoff), A.U17.23 (a cancelled transaction frees the instance), A.U3.02 + A.U3.08 (`:5491-5497`: a resync
  prints, the drain bound persists one warning), A.U2.20/A.U2.23 (`:5497` codes), A.U8.06 (Part N IDs), A.U14.R01 (F.2's
  ladder names "UART: J.5").
- **Site**: `SPECIFICATION.md:5457-5497`.
- **Change**: (1) After the hold-off paragraph `:5477-5478`, A.U17.06's sentence, then A.U17.17's. (2) "Unsticking from
  outside" gains A.U17.23's sentence. (3) `:5491-5497` "a resync persists the more specific of its two warnings, once the
  drain has decided which case this is (C.7.1's `wrnno` 10/11 note)" → "a resync prints; only a drain that hits its bound
  persists its warning (`wrnno` <n>, C.7.1)". (4) After "**The drain is bounded** …", A.U17.33's "**Recovery ladder**"
  paragraph verbatim. (5) `1.5 × timeout` and the drain bound cite their Part N rows (`uart.*`, A.U8.06).
- **Resolved**: A.U3.02 and A.U3.08 both rewrite `:5491-5497`'s persistence clause — A.U3.08's wording (the later, more
  specific one; A.U3.02 removes the episode mechanism it describes).
- **Unit**: Stage 1 U2/U3 ((3)); Stage 2 U8 ((5)); Stage 3 U17 ((1), (2), (4)).
  A-C2 step order: A.U14.R01's part lands in U18, not U17 (it needs A.U18.R01, which lands in U18).
- **Depends**: A.U2.23, A.U3.02, A.U3.08, A.U8.06, A.U17.06, A.U17.07, A.U17.17, A.U17.23, A.U17.33.
- **Blast carried by**: C.7.1/C.7.2 UART texts → M.SPEC.059/M.SPEC.060; changelog entries → the code actions (UART).
- **Kind**: doc

### M.SPEC.136 J.6: deployment parameters at the end state
- **From**: A.S0930.08 (the CRC mode agreed out of band; wire-cost defaults), A.S0930.01 + A.U17.32 + A.U17.21 (the build's
  pair checks cite J.6; no edit beyond the CRC sentence), A.U17.15 (the closed blind spot), A.U3.08 (`:5514-5516`,
  superseded), A.U2.20/A.U2.23 (codes 32, 22, 15), A.U0.37 V44 (`:5530-5531`), A.U13.17 (poll defaults 2/50 ms), A.U17.20
  (ceilings), A.U8.06 (Part N IDs), A.U36.532 (`:5546` F.5.9 → F.8.3), A.U16.07/A.U33.07 (cite the 80 B floor; no edit);
  OR141.a (4) (e) (the receive ring's size floor), OR143.a (2) (`max_transfer_bytes`, declared and checked with the
  ring size) (A-C review fold).
- **Site**: `SPECIFICATION.md:5499-5566`.
- **Change**: (1) `:5501-5505` → A.S0930.08's "`payload_size`, `timeout` and the CRC mode are **agreed out of band …**" and
  its build sentence. (2) `:5507-5521` → A.U17.15's "**Bytes a failed frame read drops count toward it** (owner,
  2026-09-26)" paragraph verbatim, codes as landed; the "`payload_size` must be in `1 … 255`" sentence starts a new
  paragraph. (3) Wire cost: "At the defaults (`payload_size=48`, CRC16)" → A.S0930.08's "(`payload_size=48` with CRC16;
  `dev` runs without, 53 bytes)"; `:5530-5532` "This is accepted for the intended traffic … and is not on its own a reason
  to change the wire format" → "The wire format stays as it is until the C side is reconciled (owner, 2026-09-25); the ratio fits the
  intended traffic (short bursts between two participants); the two candidates that would change it, a bare 5-byte ACK
  header and COBS-delimited variable-length frames through the framing codec, wait for that reconciliation". (4) `:5534-5542` per A.U13.17: "defaulting to **20 ms**" → "defaulting to 2 ms with a 50 ms idle
  rate, the dev bench's measured pair"; "Measured against the defaults" → "Measured at the former 20 ms default"; "must
  therefore be constructed with a single-digit `poll_wait_ms`" gains ", which the driver default (2 ms) is". (5) `:5546`
  "(Part F.5.9)" → "(F.8.3)". (6) `:5554-5566`: the poll-interval floor recomputed at the 2 ms default (≈ 80 bytes,
  A.U13.17), then A.U17.20's ceiling sentence ("Both also have a ceiling: …"), each value citing its Part N row. (7)
  (A-C review fold) The `rxbuf` paragraph's subject becomes the receive ring: "**The receive ring is sized at
  construction against its floors** — the larger of one whole framed frame, one poll interval's arrivals (both as
  above) and what the peer can send during the longest synchronous flash write under stop-and-wait (one frame plus every
  retransmission its `timeout` and backoff fit), rounded up to a power of two; too small is a readiness-gate refusal
  with its own errno, never a silent degradation, and the size is derived, never a bare number (owner, 2026-10-05).
  `machine.UART`'s own receive buffer is held at its minimum, since nothing reads it (F.8.2)." — the driver-default
  example (260 against 256) restated for the ring as landed; the `timeout` floor sentences stay. (8) After "Maximum
  transferable payload is `(0xFF - 1) × payload_size`." (A-C review fold): "An instance accepts at most its
  `max_transfer_bytes`: a train declaring more is refused before anything is allocated (J.8). The cap and the ring size
  are declared together in the link's device TOML and checked together by the build; they stay two values, since
  stop-and-wait means the ring never holds a whole transfer (owner, 2026-10-05)."
- **Resolved**: A.U3.08 (U3) rewrites the old blind-spot paragraph's signature sentence; A.U17.15 (U17) replaces the
  paragraph — A.U17.15 is the end state.
- **Unit**: Stage 1 U0 ((3) V44 tag); Stage 2 U2/U3 (codes, A.U3.08 interim); Stage 3 U8 (Part N); Stage 4 U13 ((4), (6)
  floor; (7)'s ring and the minimum receive buffer, with the DMA receive path); Stage 5 U17 ((2), (6) ceiling; (7)'s
  flash-write floor and refusal, (8)'s first sentence, with `UARTComm`'s ring floor and receive cap); Stage 5b U20 ((8)'s
  TOML sentence, with the keys and the build check); Stage 6 U36 ((1), (3) defaults, (5)) — A.S0930.08 is part of the
  2026-09-30 set landing with the CRC-mode wiring.
- **Depends**: A.U0.37, A.U2.23, A.U3.08, A.U8.06, A.U13.17, A.U17.13, A.U17.15, A.U17.20, A.S0930.01, A.S0930.08, M.SPEC.003;
  M.SRC_NET.221, M.SRC_NET.222 (the ring in `asy_uart_driver.py`, its floor and refusal in `asy_uart_comm.py`),
  M.SRC_NET.220 (`max_transfer_bytes`), M.GEN.066 (the TOML keys and their joint build check).
- **Blast carried by**: changelog B26 → A.U17.15 (UART); `devices/dev.toml:39-40` comment → A.U13.17 (GEN); C.7.2 build
  refusals → M.SPEC.060.
- **Kind**: rule, doc

### M.SPEC.137 J.7: the loopback model, both CRC modes, the tier map, the poll constraint
- **From**: A.S0930.08 ("Both CRC modes at every level"), A.S0930.03/.04 (mode marks), A.U36.539 (2)-(3) (tier map; jumper
  path), A.U17.25 + A.U26.33 + A.U26.82 + A.U26.87 (cells), M_TWIN gap + M_DOCS gap 1 (h) (the L2 files: `tests/test_digital_twin_
  uart_comm_hazard.py`, `tests/test_digital_twin_uart_link.py`, `tests/test_digital_twin_uart_field_sweep.py`; M.DOCS.085),
  A.U1.18 + A.U1.04 + A.U1.08 (`:5572` path), A.U35.06 (`:5613-5617` latency), A.U24.15 + AC_NOTES 29 + M_DOCS gap 1 (i)
  (`:5619-5625` mechanism; CLAUDE.md's "known hang cause"; M.DOCS.099), A.U36.040 (the growth path is F.7's), A.SDEP.16
  (`:5622` prewarm, conditional), A.U8C.43 + A.U8C2.15 (Part N IDs), M_DOCS gap 1 (c) (BACKLOG's UART-fakes entry; M.DOCS.065);
  OR141.a (4) (c), (g) (a lap is the receive overrun; the fakes model the DMA ring; hammering, concurrent load and the
  interrupts-off sweep), OR143.a (4) (the chunking and cap tests) (A-C review fold).
- **Site**: `SPECIFICATION.md:5568-5625`.
- **Change**: (1) `:5571-5574`: "(the permanent UART0↔UART1 crossover jumper, `dev_legacy/README.md`)" → "(… jumper,
  `tests_hardware/README.md` 'The dev bench')"; "`digital_twin/machine.py` (twin tier, which has no `UART` at all today)" →
  "`digital_twin/machine.py` (twin tier)" (gap fill: the twin has had its `UART` since the promotion). (2) After the
  two-models paragraph: "Both fakes serve what they hold and return; they never wait as the peripheral does. Each counts the
  bytes a read asked for that had not arrived (`UART.would_have_blocked_bytes`, held identical by
  `tests/_uart_link_contract.py`), which catches a clamp regression as a number; the milliseconds an over-ask would cost
  are measured only at L3 (F.8.2)." (BACKLOG's UART-fakes entry, current-state facts only.) (3) A.S0930.08's "**Both CRC
  modes at every level** (owner, 2026-09-30) …" paragraph, then A.U36.539 (2)'s "**Comm-hazard tier map**" with its table
  and injector paragraph, every cell filled from the landed tests (an unfilled cell "—" with its reason) and each row
  marked with its CRC modes. (4) `:5600-5602` the margin table's budgets cite their Part N rows. (5) `:5613-5617` "The
  accepted trade-off is that neither test would now catch a *latency* regression below 240 ms — …" → A.U35.06's outcome:
  "a latency regression is caught by <test>" (the planted proof), "accepted trade-off" gone. (6) `:5619-5625` → "**Constraint
  — a loopback harness never registers a fake UART with a real `select.poll()`** (CLAUDE.md, the known hang cause): a real
  poll asks each registered object for a file descriptor and polls that descriptor instead of the object's own `ioctl()`
  (F.7 row 12); the machine fakes answer `EINVAL` as rp2 does, and the mock layer supplies a bounded paired poller
  re-querying each fake per call, installed by reassigning `uart.poller` after construction — the project's mocking
  mechanism, keeping `src/` free of a testability seam. The Unix port's poll growth-path defect is F.7's." — the
  `unix_port_poll_prewarm.py` mention goes with A.SDEP.16 if the prewarm is retired, else it is F.7's pointer. (7) (A-C
  review fold) The two-models paragraph gains: "Both fakes model the receive side as rp2 runs it: a time-driven DMA and
  UART register model fills the receive ring independently of the event loop (F.8.2), so the count reload and modular
  wrap, a frame split across the ring end and a lap are exercised; a lap is the receive-buffer overrun of the fault list
  above — detected, counted and resynced, never read as data (owner, 2026-10-05)." The tier map gains the rows the fold
  adds, each with its CRC modes: L1 — zero allocation per read at `gc.threshold(-1)`, no receive allocation above
  `chunk_bytes`, a refusal before any allocation, the readline cap; hammering — thousands of back-to-back transactions at
  the line rate with the ring at its fill boundary and random consumer stalls within and beyond the bound (no loss
  within it, a detected overrun beyond it), and repeated maximum-size and over-cap trains; L2 concurrent load — both
  `dev` link instances under traffic beside the webserver hammer, FRAM log writes and config PUTs, the twin's config
  flush stalling the loop for the datasheet erase time, both GC stages, zero `MemoryError`; L3 — the interrupts-off sweep
  without a flash write (`machine.disable_irq()` and a busy wait on `time.ticks_us()` for 3 ms, 45 ms, 400 ms and one
  window past the ring's bound, while the other UART streams frames from its own DREQ-paced transmit DMA over the
  crossover jumper: every frame within the bound intact with UARTRSR's overrun bit clear, the over-bound window read as
  an overrun), a soft reset during traffic and a maximum-size transfer; a real config write during traffic only behind
  the persistence-write flag (owner, 2026-10-05). Cells are filled from the landed tests like the rest.
- **Resolved**: (a) AC_NOTES 29 corrects `:5619-5622`'s mechanism ("does not re-evaluate a Python object's `ioctl()`") — one
  mechanism, stated in F.7 row 12 (M.SPEC.107) and pointed to here. (b) M_DOCS gap 1 (c) routes the UART-fakes entry to J.9;
  its facts are about the test models, J.7's subject, so they land in J.7 (agent decision, OR2.c review); J.9 gains
  nothing from it. (c) M_DOCS gap 1 (h): the map names the L2 files M_TWIN lands (three, the two DOCS names among them).
- **Unit**: Stage 1 U1 ((1) path); Stage 2 U8C (Part N); Stage 2b U13 ((7)'s fake-model sentence and its L1 rows, with
  the DMA receive path and both fakes); Stage 3 U24 ((6), with A.U24.15); Stage 3b U25 ((7)'s L2 row, with the twin's
  flash-write stall and the concurrent-load test); Stage 3c U26 ((7)'s L3 row, the device script written; its cells
  "owed" until phase C runs it); Stage 4 U35 ((5)); Stage 5 U36 ((1) twin clause, (2), (3)). The U17 chunking and cap
  rows land with U17's tests.
  A-C2 step order: A.U17.25's part lands in U25, not U24 (it follows A.U17.25's own change, which lands in U25).
- **Depends**: A.U1.18, A.U8C.43, A.U8C2.15, A.U17.25, A.U24.15, A.U26.33, A.U26.82, A.U26.87, A.U35.06, A.U36.040, A.U36.539,
  A.S0930.03, A.S0930.04, A.S0930.08, A.SDEP.16, M.SPEC.107, M.TWIN.156; M.TEST_HELP.069, M.TWIN.169 (the
  DMA/UART register fakes), M.TEST_UNIT.344, M.TEST_UNIT.345 (L1 and hammering), M.TWIN.170, M.TWIN.171 (the flash-write stall and the
  concurrent-load test), M.HW_DEV.159, M.HW_DEV.160 (the interrupts-off sweep), M.TEST_UNIT.344, M.TEST_UNIT.345 (the chunking and cap
  tests), M.HW_DEV.045, M.HW_DEV.046 (the bench maximum-size transfer).
- **Blast carried by**: CLAUDE.md hazard rule's UART clause → M.DOCS.085; CLAUDE.md hang bullet → M.DOCS.099; BACKLOG's
  UART-fakes entry → M.DOCS.065; E.6.6 exception rows for the L4 "—" cells → M.SPEC.083.
- **Kind**: rule, doc

### M.SPEC.138 J.8: the memory model at the end state
- **From**: A.U17.03 (`(CHUNKS − 1) × payload_size`; its pending owner question answered by OR143.a), A.U36.548
  (`:5633-5635`), M_DOCS gap 1 (c) (BACKLOG's peer-sized-allocation finding; M.DOCS.065), A.U30.02 (6) (I.2's UART row
  points here), C7 (`RegionBuffer`); OR143.a (1)-(5) (chunked receive assembly, the receive cap, the ring allocated in
  `setup()`), OR141.a (4) (d) (the ring held for life, copied from by index) (A-C review fold).
- **Site**: `SPECIFICATION.md:5627-5664`.
- **Change**: (1) `:5633-5635` → A.U36.548's "This module chunks the memory for SET in both directions (J.8); a responder's
  GET answer is still returned as one buffer." (2) `:5640` `LockableBuffer(…)` → `RegionBuffer(…)`. (3) `:5650-5652` →
  A.U17.03's first sentence, then the owner's end state in place of its open question (A-C review fold): "The total
  upper bound `(CHUNKS − 1) × payload_size` (chunk 1 carries only the command id) is known the moment the first frame
  of a train arrives, and the exact size is known whenever the caller passed `exp_size` — neither case justifies an
  incrementally grown accumulator. **No receive allocation is larger than `chunk_bytes`, and none exceeds
  `max_transfer_bytes`** (owner, 2026-10-05): a train whose declared size (its `CHUNKS`, or `exp_size`) exceeds the
  instance's `max_transfer_bytes` is refused before anything is allocated, through the rejection J.4 already has (the
  withheld ACK), and logged once; a train the caller gave no destination for (`uart_get()` with `exp_size=None`, or a
  `set_callback` answering *don't care*) is assembled in pieces of at most `chunk_bytes`, held in G.2's piece primitive;
  a caller-supplied destination is filled in place as before. Both are constructor arguments with reasoned defaults, as
  `WebserverService`'s `chunk_bytes` is, and `max_transfer_bytes` is declared in the link's device TOML beside the
  receive ring's size (J.6). `readline_until_complete()` takes the same cap (C.3.2). A caller that declares its size
  caps it — the form to prefer in a new responder (agent, 2026-09-11)." (4) The "**A failed allocation degrades …**"
  bullet keeps its rule for the module's other allocations and gains: "The receive allocations above are bounded before
  they happen, so no caught `MemoryError` stands at them (I.2, I.4(a))." (5) New bullet after the frame-buffer bullet:
  "**The receive DMA ring**, in the bus driver: allocated once in the link's `setup()` (a unit of the one-time setup
  list, I.4(f.1)), held for the program's life and never reallocated by a task restart; a read copies from it by index
  into the RX frame buffer, never through a slice, so steady-state reception allocates nothing (F.8.2; owner,
  2026-10-05)."
- **Resolved**: A.U17.03's "an open owner question (BACKLOG.md, owner questions). Until it is answered a failed
  allocation degrades as the next bullet says" is superseded by OR143.a (owner, 2026-10-05: the parked chunking item
  becomes work; its BACKLOG question is removed, M.DOCS.067) — (3) states the end state (A-C review fold).
- **Unit**: Stage 1 U17 ((3) with `chunk_bytes`, `max_transfer_bytes` and the piece primitive; (4)); Stage 1b U13 ((5),
  with the ring; the readline cap's clause of (3) lands in U17 after U13's cap); Stage 1c U20 ((3)'s TOML clause, with the
  keys and the build check); Stage 2 U30/U10 ((2) name); Stage 3 U36 ((1), the advice clause).
- **Depends**: A.U17.03, A.U36.548; M.SRC_NET.220, M.SRC_NET.202 (`chunk_bytes`, `max_transfer_bytes`, the piece primitive's
  use, the readline cap), M.SRC_NET.221 (the ring), M.GEN.066 (the TOML key and its check), M.SPEC.111
  (item 18), M.SPEC.136 ((7)-(8)).
- **Blast carried by**: BACKLOG owner question naming both allocation sites → removed (M.DOCS.067, as the fold amends
  it); the streaming-GET BACKLOG item → A.U36.548 (DOCS); `UART_C_PORT_CHANGELOG.md` rows for the refusal (Class A) and
  the chunked assembly, the ring and the readline cap (Class B) → M.DOCS.022/.024 (as the fold amends them).
- **Kind**: doc

### M.SPEC.139 J.9: the module contract
- **From**: A.U0.44 L14 (`:5668`), A.U0.48 (comment; J.9 unchanged beyond L14), A.U17.01 (entry-point check order), A.U5.12
  (one responder-callbacks object), A.U11.35 (`:5687-5688`), A.U2.20/A.U2.23 (`:5675` code alignment), A.U10.R01 (the
  ladder lives in `_error_check()`, which this module does not use).
- **Site**: `SPECIFICATION.md:5666-5697`.
- **Change**: (1) `:5668` "(owner-delegated decision, 2026-09-11, resolved against precedent)" → "(agent, 2026-09-11: a
  choice the owner delegated to the promotion, 'delegated to this scope, resolved against precedent')". (2) `:5675-5676`
  "`errno`/`wrnno` still align to `base_classes.py`'s reservation regardless of the base class (C.7.1)" → "its codes are
  the error catalog's, like every module's (C.7.1)". (3) After "`None` means failure …", A.U17.01's sentence. (4) A
  constructor sentence: "A responder takes its callbacks as one `ResponderCallbacks(get, set, message)` object; an
  initiator passes none." (A.U5.12). (5) `:5687-5688` "C.6's `make_dict()` repr-parsing landmine does not apply: this
  namedtuple is never serialized." → "this namedtuple is never serialized.".
- **Resolved**: — (no conflict among the constituents)
- **Unit**: Stage 1 U0 ((1)); Stage 2 U2 ((2)); Stage 3 U5 ((4)); Stage 4 U11 ((5)); Stage 5 U17 ((3)).
  A-C2 step order: A.U10.R01's part lands in U13, not U11 (it follows A.U10.R01's own change, which lands in U13).
- **Depends**: A.U0.44, A.U2.23, A.U5.12, A.U11.35, A.U17.01.
- **Blast carried by**: the exerciser's plain-class comment → A.U0.48 (SRC_NET); C.6 → M.SPEC.057.
- **Kind**: doc

## SPECIFICATION.md — Part K (`:5701-6002`)

### M.SPEC.140 Part K heading, intro, K.1 and K.2: the one ordered checklist begins
- **From**: A.U36.543 (1)-(3), (8) (`:5738`), (11) (names grepped before landing), A.U36.540 (3) (D.0's sentence lands in
  K.1; M.SPEC.073), A.U36.542 (0.4's conventions catalog is K.2's code-style step), A.U24.16 (K.2 pull sentence), A.U36.541
  (Part 0).
- **Site**: `SPECIFICATION.md:5701-5758`.
- **Change**: A.U36.543 (1)-(3) verbatim (heading "# Part K — Adding a module: the one ordered checklist"; the intro; K.1
  item 0 "The brief" then D.0's text and A.U36.540 (3)'s sentence; K.2's heading and first paragraph); `:5738` "(Part D,
  all of D.0–D.15)" → "(Part D in full)"; K.2's `irq_pull_up=False` example → A.U24.16's "`pull=None` and an omitted pull
  are the same on rp2 (no pull, set unconditionally); both fakes accept both". Every file, function, table and test name
  Part K states is grepped at landing and fixed if absent (A.U36.543 (11)).
- **Resolved**: D.0's text moves here with A.U36.540's rewrite (M.SPEC.073's resolution) — not written twice.
- **Unit**: Stage 1 U24 (pull sentence on HEAD text); Stage 2 U36 (the rest).
- **Depends**: A.U24.16, A.U36.540, A.U36.541, A.U36.542, A.U36.543, M.SPEC.073.
- **Blast carried by**: `.claude/skills/integrate-module/SKILL.md` → M.DOCS.109 (A.U36.543 (9)); the baseline runs →
  M.PROC.048 (A.U36.543 (10)); README map → A.U36.547 (DOCS); TOC → M.SPEC.001.
- **Kind**: rule, doc

### M.SPEC.141 K.3: the two owner-kept tables
- **From**: A.U33.01 (1), (2), (5), A.U15.28 (a hard-wired chip's protocol class takes no address), A.U20.27 (the
  completeness test; every restated value AST-read or pinned), A.U20.18 (`:5779-5782` holds).
- **Site**: `SPECIFICATION.md:5759-5790`.
- **Change**: A.U33.01 (1), (2), (5) verbatim; `:5769-5773` (hard-wired chips get no TOML `address`) gains A.U15.28's "and
  its protocol class takes no `address` parameter at all, not even for tests; a second part needs another bus (owner,
  2026-09-26)".
- **Resolved**: — (no conflict among the constituents)
- **Unit**: Stage 1 U15 (A.U15.28); Stage 2 U20 (after A.U20.27); Stage 3 U33 (A.U33.01).
- **Depends**: A.U15.28, A.U20.27, A.U33.01.
- **Blast carried by**: `buildgen/buildspec.py:5-7` comment and `validate.py:352` message → A.U33.01 (4) (GEN); L.6.6/L.1 →
  M.SPEC.149, M.SPEC.144.
- **Kind**: doc

### M.SPEC.142 K.4-K.9: generated definitions, the twin step and K.5.1, FRAM placement, attribution
- **From**: A.U36.516 (3)-(4) (K.4, K.8), A.U6.04 + A.U6.06 (blast: hand-written definitions and mock fixtures retired),
  A.U36.543 (4) (K.5 dispatch names; `test_twin_fake_catalog.py`; C.11.1 → K.5.1), A.U25.67 (the twin catalog check),
  A.U26.66 (K.5.1's body: conformance probes for every bus chip), A.U36.039 (K.5's SPI-sharing sentence), A.U16.01
  (`:5904-5906` K.7), A.U34.07 (3) (K.9 attribution line).
- **Site**: `SPECIFICATION.md:5802-5940`; new `### K.5.1` from C.11.1 (`:2348-2366`).
- **Change**: (1) K.4 `:5802-5804` → A.U36.516 (3). (2) K.5 `:5819-5820` → A.U36.543 (4)'s dispatch text and its
  `tests_scripts/test_twin_fake_catalog.py` sentence; K.5 appended: A.U36.039's SPI sentence "(agent, 2026-09-10)". (3) New
  "### K.5.1 Keeping a chip fake honest — the conformance probe": C.11.1's body as A.U26.66 leaves it (its paragraph naming
  `flash/test_chip_conformance.py`; one probe per bus chip, twin and silicon alike); C.11.1's citers repoint to K.5.1. (4)
  K.7 `:5904-5906` → A.U16.01's text. (5) K.8 `:5915-5920` → A.U36.516 (4). (6) K.9 `:5937-5938` → A.U34.07 (3)'s text.
- **Resolved**: C.11.1's move is one change across C and K: M.SPEC.069 removes it from C, this change creates K.5.1, in the
  same U36 commit (C6: K.5.1 exists before any citer repoints to it).
- **Unit**: Stage 1 U16 ((4)); Stage 2 U34 ((6)); Stage 3 U36 ((1)-(3), (5), with M.SPEC.069).
- **Depends**: A.U6.04, A.U6.06, A.U16.01, A.U25.67, A.U26.66, A.U34.07, A.U36.039, A.U36.516, A.U36.543, M.SPEC.069.
- **Blast carried by**: `digital_twin/README.md` step 5 → A.U36.516 (6) (TWIN); README preview recipe → A.U36.516 (7)
  (DOCS); `tests_hardware/README.md` C.11.1 citers → A.U26.66 (HW_BENCH); `asy_fram_manager.py:3`/`dev.toml` comments →
  A.U16.01 (SRC_CORE, GEN).
- **Kind**: doc

### M.SPEC.143 K.10-K.11: verification, the gate, the checklist
- **From**: A.U36.543 (5)-(6) (K.10 heading, scope sentence, the gate; K.11 hedge, twin line, last item, documentation
  line), A.U36.516 (5) (K.11 definitions line), A.U33.01 (3) (K.11 `_ERRCOUNT_CATALOG` line), A.U36.511 (6) (`:5995-5996`
  device set), A.U2.22 (the error-catalog entry), A.U25.67 (`test_twin_fake_catalog.py` green).
- **Site**: `SPECIFICATION.md:5943-6001`.
- **Change**: A.U36.543 (5)-(6) verbatim; K.11 `:5972` → A.U33.01 (3); `:5990-5991` → A.U36.516 (5); `:5995-5996` "all six
  device TOMLs actually generated and inspected" → "every device TOML generated and inspected"; the documentation line as
  A.U36.543 (6) gives it (with the error-catalog entry).
- **Resolved**: — (no conflict among the constituents)
- **Unit**: Stage 1 U33 (A.U33.01 (3)); Stage 2 U36 (the rest).
- **Depends**: A.U2.22, A.U25.67, A.U33.01, A.U36.511, A.U36.516, A.U36.543.
- **Blast carried by**: CLAUDE.md `:68-77` → A.U36.542 (DOCS).
- **Kind**: rule, doc

## SPECIFICATION.md — Part L (`:6003-6591`)

Part L's class names follow C7 (`WifiService` for `AsyConnTime`, `NotificationService` for `NotificationCoordinator`);
"variant" is harmonised by M.SPEC.004 (A.U36.512).

### M.SPEC.144 Part L intro and L.1: devices and the two acceptance criteria
- **From**: A.U36.512 (`:6008` "per device variant"; `:6012` heading), A.U36.511 (7) (`:6014-6019` device set as today's fact),
  A.U24.66 (L.1 loses per-device statements), A.U0.33 A2-02 (`:6024` criterion tag) + A.U33.02 (criterion 1 body and
  heading), A.U20.27 (the completeness test named), A.U6.15 (criterion 2 names the variant-literal check), A.U0.33 C07
  (`:6039-6040`); OR140.a (18) (no device but `dev` is special) (A-C review fold).
- **Site**: `SPECIFICATION.md:6003-6040`.
- **Change**: (1) `:6008` "file per device variant" → "file per device"; heading → "## L.1 Devices and the two standing
  acceptance criteria". (2) `:6014-6019` → A.U36.511 (7)'s text (the `bmp3xx`/`timeout = 200000` sentence goes), its
  device list without the WoZi wording (A-C review fold): "`dev` (the bench rig, the one device with a role of its own —
  CLAUDE.md's `dev` rule), `wozi`, `arzi`, and `klkizi`/`grkizi`/`schlafzi` (…)" — "the exemplary/base device, never
  physically flashed" goes: every device but `dev` is built and tested alike (owner, 2026-10-02).
  (3) Criterion 1 → A.U33.02's heading "**A new driver needs exactly one association plus one row in each owner-kept
  table**" with A.U0.33's tags "(the criterion: owner, 2026-09-09, `0755e37`; the table stays hand-maintained: owner,
  2026-09-18, `b0f755c`)" and A.U33.02's body; the named exception stays. (4) Criterion 2 gains "No device name appears
  outside `devices/` — `tests_scripts/test_no_variant_literals.py` enforces it." (5) `:6039-6040` → A.U0.33 C07's text.
- **Resolved**: A.U0.33 A2-02 (U0) names "one `buildgen/buildspec.py` table entry"; A.U33.02 (U33) widens it to both owner-kept
  tables after A.U20.27 — A.U33.02's heading carries A.U0.33's tags.
- **Unit**: Stage 1 U0 ((3) tags, (5)); Stage 2 U6 ((4)); Stage 3 U33 ((3) body); Stage 4 U36 ((1), (2)).
- **Depends**: A.U0.33, A.U6.15, A.U20.27, A.U24.66, A.U33.02, A.U36.511, A.U36.512.
- **Blast carried by**: A.3 device paragraph → M.SPEC.007; README devices table → A.U36.547 (DOCS).
- **Kind**: rule, doc

### M.SPEC.145 L.2: core design decisions at the end state
- **From**: A.U36.511 (8) (`:6047`, `:6105-6106`), A.U0.33 + A.U29.03 (`:6053-6054` accepted-permanently tag, A.11
  pointer), A.U2.07 + A.U2.23 (`:6058` `CFGMGR_WIFI` code), A.U20.23 (owner's wiring decisions), A.U5.07 + A.U20.22 (`:6074`
  the WiFi LED at construction), A.U20.16 (the emitted adapters listed), A.U20.42 (generated globals declared), A.U20.13
  (frozen set seeded from the generated module's imports), A.U0.40 L11 + A.U10.30 (`:6101-6102` tag; the F.1 list),
  A.U0.19 H1.07 (`:6107-6109` fail-loud tag), M_TEST_HELP GAP-H5 + A.U36.544 (equal-rank order); OR142.a (1) (the ban
  covers the code in an image) (A-C review fold).
- **Site**: `SPECIFICATION.md:6042-6109`.
- **Change**: (1) `:6047` "every variant" → "every device"; `:6048-6050` "generates all six devices' modules" → "generates
  every device's modules". (2) `:6051-6063`: "`AsyConnTime(hostname=..., hotspot_password=...)`" → "`WifiService(...)`'s
  device settings"; "(accepted risk, CLAUDE.md)" → "(accepted permanently as a known limitation, owner, 2026-09-26; A.11)";
  "(`CFGMGR_WIFI` `W4`)" → the landed code; "Until 2026-09-18 nothing passed them at all and every device booted as the shared
  `"SensorNode"` whatever its TOML said." goes (C2: history). (3) The cross-instance bullet gains A.U20.23's two insertions;
  "`device.wiring.led_target` for WiFi's `conn.set_ext_led(pixel)`" → "`device.wiring.led_target` for the WiFi status LED,
  passed at construction". (4) The no-getters bullet gains A.U20.16's list of emitted functions and why each exists, and
  A.U20.42's "generated globals are declared, assigned once by `build_system()`". (5) The ordering bullet gains GAP-H5's
  "Instances of equal rank keep their TOML declaration order (`buildgen/graph.py:54-57`)." (6) Frozen-module bullet: "seeds
  from each device's declared driver list plus a fixed always-included core set" → "seeds from the generated module's own
  imports (which name every declared driver and the mandatory services)"; "Dynamic imports are disallowed project-wide"
  → "No code this project writes, generates or vendors into an image imports dynamically (agent, 2026-09-09; its
  scope, owner, 2026-10-05; the named host and test exceptions and MicroPython's two bundled sites: F.1)" (A-C review
  fold). (7) `:6105-6106` "per-variant test files" →
  "per-device test files". (8) The build-time-tooling bullet gains "(owner, 2026-09-09, `b2625e9`: …)" as A.U0.19 H1.07 quotes it.
- **Resolved**: — (no conflict among the constituents)
- **Unit**: Stage 1 U0 ((2) tag, (6) tag, (8)); Stage 2 U2 (code); Stage 3 U5 ((3) LED); Stage 4 U20 ((3) owner tags, (4),
  (6) seed); Stage 5 U29 ((2) A.11 pointer); Stage 6 U36 ((1), (2) history, (5), (7)).
- **Depends**: A.U0.19, A.U0.33, A.U0.40, A.U2.07, A.U5.07, A.U10.30, A.U20.13, A.U20.16, A.U20.22, A.U20.23, A.U20.42,
  A.U29.03, A.U36.511, A.U36.544, M.SPEC.024 (A.11 exists, U29).
- **Blast carried by**: `devices/*.toml` `[device.wiring]`/per-signal comments → A.U20.23 (GEN); H.6 maintenance keys →
  A.U20.16 (nothing to edit, M.SPEC.119).
- **Kind**: rule, doc

### M.SPEC.146 L.3: the device TOML schema and its checked key table
- **From**: A.U20.35 (the key table between markers; its test), A.U20.29 (banners, order), A.U20.19 (`hardware_family`;
  `name_ext` rule; fuzz), A.U20.34 (ranges), A.U26.01 (`bench`), A.U31.08 (I2C `timeout` upper bound), A.S0930.01 (`crc`),
  A.U10.43 (unit suffixes), A.U29.03 + A.U0.33 (`:6136` comment), A.U36.511 (9) (`:6131`), A.U5.07 + A.U9.04 (`:6245-6248`
  LED wiring), C7 names (`:6116`, `:6120`); OR141.a (1) (`bench` and `hardware_family` stay in `[device]`, checked,
  never emitted), OR143.a (2) (the cap and the ring size declared and checked together) (A-C review fold).
- **Site**: `SPECIFICATION.md:6111-6259`.
- **Change**: (1) `:6116` "NotificationCoordinator" → "the notification service"; `:6120` WiFi knob names as A.U10.43 lands
  them. (2) The example: `:6131` "the 6 real files are devices/*.toml." → "the real files are devices/*.toml."; `:6136`
  "# accepted-risk default (CLAUDE.md)" → "# default, accepted permanently (owner, 2026-09-26; A.11)"; banners `:6160`,
  `:6207` → A.U20.29's three titles and form; the LED wiring lines `:6245-6248` as A.U5.07 leaves the TOML. (3) After the
  example, A.U20.35's table `<!-- toml-schema-table -->` … `<!-- /toml-schema-table -->`, rows as A.U20.35 lists them plus:
  `hardware_family` (A.U20.19: "a label only the test suite reads; hardware divergence removes it from one file"), `bench`
  (A.U26.01: "the board `tests_hardware/` flashes and tests; at most one device") — both rows stating "kept in
  `[device]`, checked by the build, never emitted into the image (owner, 2026-10-05)" (A-C review fold), `uart_link`
  `crc` ("none" | "crc16", default "none", both ends equal; A.S0930.01), the link's receive-ring size and
  `max_transfer_bytes` (declared together, checked together by the build, two values; owner, 2026-10-05; J.6) (A-C review
  fold), the I2C bus `timeout` upper bound (A.U31.08), each numeric `[device]` and bus field's range (A.U20.34). (4) One sentence for the banner order and form (A.U20.29) and one for the `name_ext` rule (every
  non-singleton instance states it); the closing sentence names `tests_scripts/test_toml_schema_contract.py`.
- **Resolved**: — (no conflict among the constituents)
- **Unit**: Stage 1 U0 ((2) `:6136` tag); Stage 2 U5/U9 (LED lines); Stage 3 U10 (key names); Stage 4 U20 ((3) table, (4);
  the ring-size and `max_transfer_bytes` rows with their keys and joint check); Stage 5 U26/U29/U31 (rows `bench`, A.11
  pointer, `timeout` bound); Stage 6 U36 ((1), `:6131`; `crc` row with A.S0930.01).
- **Depends**: A.U5.07, A.U10.43, A.U20.19, A.U20.29, A.U20.34, A.U20.35, A.U26.01, A.U29.03, A.U31.08, A.S0930.01;
  M.GEN.066 (the two TOML keys and their joint check).
- **Blast carried by**: `devices/*.toml` banners → A.U20.29 (GEN); the table's test → A.U20.35 (TSC).
- **Kind**: rule, doc

### M.SPEC.147 L.4: the generator pipeline
- **From**: A.U2.24 + A.U2.01 (the error catalog as a buildgen input), A.U19.20 (`buildgen/api_reference.py`), A.U20.30
  (`buildgen/signals.py`), A.U20.02 + A.U20.05 (`:6267-6271` the boot entry and its no-autostart variant), A.U5.08
  (`set_level_setters()` → a construction-time provider), A.U5.03 (one `LogConfig` per FRAM store), A.S0930.02 (a link
  end's CRC reaches its bus), A.S0930.11 (the command callback by reference to A.8), A.U36.515 (4) (`definitions_for_toml()`),
  A.U6.01, A.U20.28 (one producer and a contract test for the twin plan; chip addresses read from drivers), A.U36.518
  (twin-wiring bullet; device-set wording), A.U36.041 + A.U0.59 (`:6308-6314` the persistence-limit pointer), A.U17.21 +
  A.U17.32 (checks list: UART ceilings, baud agreement), A.U20.36 (deterministic generation), A.U27.10 (Python-version
  check), A.U20.32 (mypy sentence holds); OR141.a (5) (the build date is a build input) (A-C review fold).
- **Site**: `SPECIFICATION.md:6261-6319`.
- **Change**: (1) The inputs list gains `buildgen/error_catalog.json` (consumer `definitions.py`; never frozen into the
  firmware), `buildgen/signals.py` (the warn-signal catalog) and the generated `buildgen/api_reference.py` reference (A.8).
  (2) `:6267-6271` names the boot entry `sensortask_<device>_main.py` and its `…_main_noautostart.py` variant, the watchdog
  armed as the entry's first statement and passed to `main()`. (3) The construction sentence: one `LogConfig` per FRAM
  store; `level_setters=` passed as a provider (no `set_level_setters()` line); a `uart_link` end's CRC passed to its bus;
  the command callback's branches by reference to A.8. (4) `:6285-6297` → A.U36.515 (4) (`definitions_for_toml()`; "Tag
  grammar: L.6.4; what the definitions carry: H.5/H.5.1."). (5) `:6302-6306`, `:6310-6311`, `:6318-6319` → A.U36.518 (1)-(3);
  `:6283-6296`'s chip-address sentence per A.U20.28 ("declared as a module-level const in each driver"). (6) `:6308-6314` →
  A.U36.041's bullet (A.U0.59's label merged into it). (7) The checks list gains the UART poll and timeout ceilings and the
  pair's baud and CRC agreement; the host-tooling sentence names the Python-version check (A.U27.10); and "Generation is
  deterministic across hash seeds (tested); the build date is the one deliberate input that varies — a fixed date makes
  two generations byte-identical, and changing only the date changes only that line (L.7; owner, 2026-10-05)." (A.U20.36;
  amended by OR141.a (5), A-C review fold).
- **Resolved**: — (no conflict among the constituents)
- **Unit**: Stage 1 U2 (catalog); Stage 2 U5 ((3) LogConfig, provider); Stage 3 U17 ((7) UART); Stage 4 U19 (api reference);
  Stage 5 U20 ((2), (5) addresses, (7) deterministic, signals); Stage 6 U27 ((7) python check); Stage 7 U36 ((4), (5), (6),
  CRC and command clauses with the 2026-09-30 set).
  A-C2 step order: A.U2.24's part lands in U6, not U2 (it needs A.U2.21, which lands in U6); A.U0.59's part lands in U25, not U2 (it follows A.U0.59's own change, which lands in U25).
- **Depends**: A.U0.59, A.U2.01, A.U2.24, A.U5.03, A.U5.08, A.U6.01, A.U17.21, A.U17.32, A.U19.20, A.U20.02, A.U20.05,
  A.U20.28, A.U20.30, A.U20.36, A.U27.10, A.U36.041, A.U36.515, A.U36.518, A.S0930.02, A.S0930.11, M.GEN.019.
- **Blast carried by**: `digital_twin/README.md` plan-shape and address text → A.U20.28 (TWIN); C.7.2 refusal list →
  M.SPEC.060.
- **Kind**: doc

### M.SPEC.148 L.5: the build-script quality bar
- **From**: A.U0.19 (`:6322-6325` owner tag), A.U20.19 (`:6332` collision class tag; the fuzz test), A.U20.17 (message form,
  rule-id completeness), A.U27.29 (three user-error classes, one exit idiom), A.U20.33 (native annotations), A.U20.14 +
  A.U27.09 + A.U28.41 (generated output joins the ruff/mypy scope), A.U24.55 (every boot entry executed at L1), A.U20.01 (a
  UART bus claimed twice), A.U20.24 (scan dimension: column-0 rule, `nan`/`inf` refused), A.U20.37 (`@value-wiring`/`@limits`
  dimensions), A.U36.514 (3) (`:6357-6369` → L.6.4 pointers), A.U0.39 L12 (`:6366`, carried to L.6.4) and L13 (`:6370` tag),
  A.U20.39 (names no function; nothing).
- **Site**: `SPECIFICATION.md:6320-6437`.
- **Change**: (1) `:6322-6325` first paragraph gains "(owner, 2026-09-09)". (2) `:6332` "Global-resource-collision checks
  are their own error class …" gains "(owner, 2026-09-09)"; `:6346-6348` "Any other single-owner resource claimed twice" gains
  "a UART bus claimed by two instances". (3) `:6357-6369` → A.U36.514 (3)'s two texts. (4) `:6370` "**Standing rule for every
  tag in this comment-tag family:" gains "(owner, 2026-09-10, `12d62b6`)"; the rule's dimension list gains A.U20.37's `@value-wiring` and `@limits` dimensions and A.U20.24's
  column-0 rule and "`nan`/`inf` rejected" in each value dimension. (5) "Newly-built generator/validator modules join …
  ruff/mypy scope" gains "and so does their generated output (`build/generated_src/`), every boot entry executed at L1". (6)
  The "Fail loudly" bullet `:6420-6436` gains A.U20.17's message form (rule, place and fix) and its rule-id completeness
  test, A.U27.29's three user-error classes and one exit idiom, and A.U20.19's fuzz test; one line: "Host code evaluates
  annotations natively (no `from __future__ import annotations`); a `TYPE_CHECKING` name or a later class is quoted."
- **Resolved**: A.U0.39 L12's quote at `:6366` leaves L.5 with A.U36.514 (3) — the quote and tag live in L.6.4 (A.U36.514 (1),
  M.SPEC.149); C8 folds the U0 tag into that text.
- **Unit**: Stage 1 U0 ((1), (4) tag, L12 on HEAD text); Stage 2 U20 ((2), (4) dimensions, (6) message form, fuzz); Stage 3
  U24/U27/U28 ((5), (6) classes and annotations); Stage 4 U36 ((3)).
- **Depends**: A.U0.19, A.U0.39, A.U20.01, A.U20.14, A.U20.17, A.U20.19, A.U20.24, A.U20.33, A.U20.37, A.U24.55, A.U27.09,
  A.U27.29, A.U28.41, A.U36.514.
- **Blast carried by**: CLAUDE.md scope sentence → A.U27.09 (DOCS); B.15 scope → M.SPEC.043.
- **Kind**: rule, doc

### M.SPEC.149 L.6.1-L.6.6: wiring defaults, per-value wiring, the comment-tag family, pin legality, validation
- **From**: A.U20.21 (L.6.2 keyword-only parameters), A.U15.16 + A.U20.20 + A.U5.11 (L.6.3), A.U36.514 (1)-(2) (L.6.4 opening
  and the `@web`/`@web-group` rows), A.U0.39 L12 (the owner quote, in L.6.4), A.U8.03 (`# @tunable` row), A.U20.25 (`hidden`),
  A.U20.24 (`specs_for()`), A.U5.03 + A.U5.07 (L.6.4 `:6499`, `:6513`), A.U15.10 (no per-driver rows), A.U6.19 + M_DOCS gap
  1 (g) (CLAUDE.md cites L.6.4 for the web rows), A.U20.09 + A.U0.29 E02 (L.6.5), A.U33.03 + A.U0.33 A2-03 (L.6.6 last
  paragraph), A.U20.18 + A.U20.01 + A.S0930.01 + A.U20.34 + A.U20.17 (L.6.6 coverage list), A.U16.20 (C.3.1, not here);
  OR143.a (2) (the receive cap and the ring size checked together), OR141.a (1) (`bench`, `hardware_family` checked,
  never emitted), OR140.a (16) (the `@web` `decimals` field for every numeric value) (A-C review fold).
- **Site**: `SPECIFICATION.md:6439-6566`.
- **Change**: (1) L.6.2 `:6461-6464` "param names and which have a Python default" gains "positional and keyword-only alike".
  (2) L.6.3 gains A.U20.20's "the field set is read from the producer's `get_data()` namedtuple", A.U5.11's value references
  and one backup group, and after `:6485` A.U15.16's behaviour sentence verbatim. (3) L.6.4: opening → A.U36.514 (1)
  verbatim (its owner quote is A.U0.39 L12's, "(owner, 2026-09-10: …)"); the table gains A.U36.514 (2)'s `# @web` row (keys
  as `_FIELD_KNOWN_KEYS` lists them at landing, `hidden` among them, A.U20.25) and `# @web-group` row, and A.U8.03's
  "`# @tunable` / `<area>.<name> = <literal>` / `tests_scripts/test_tunables_register.py`" row (an L0 test, not the build);
  `:6499`/`:6513` per A.U5.07 (no setter-mode LED tag) and A.U5.03; `:6505-6507` names `specs_for()` (A.U20.24). (4) L.6.5
  `:6520-6542` → A.U20.09's per-GPIO text transcribed from RP2040 Table 279; `:6522-6523` "this project targets the Pico W
  alone" gains "(owner, 2026-09-26: 'Only the Pico W.')". (5) L.6.6: the coverage list gains `irq_pull_up`'s type,
  `poll_idle_ms`'s range, the compile step (A.U20.18), a UART bus claimed twice (A.U20.01), the `crc` legal set and pair
  agreement (A.S0930.01), every numeric field's range (A.U20.34), and (A-C review fold) a `uart_link`'s receive-ring
  size against its floors together with its `max_transfer_bytes` (J.6), and `bench`/`hardware_family` checked and never
  emitted (L.3), and points to L.5 for the message form (A.U20.17); the `# @web` row's key set includes `decimals`, the
  display precision every numeric field may declare (H.5.1); the last
  paragraph → A.U0.33's "**Hand-maintained by owner decision** (owner, 2026-09-18, `b0f755c`): … two independent naming
  spaces." with A.U33.03's inserted sentences, the "BACKLOG.md's 'Deferred' section has the full account …" sentence gone.
- **Resolved**: M_DOCS gap 1 (g): L.6.4 holds the `@web`/`@web-group` rows (A.U36.514 (2), test-pinned); H.5.1 points here
  for the grammar (M.SPEC.118); CLAUDE.md's tag-line pointer needs only L.6.4 — gap for DOCS (M.DOCS.092 drops its H.5.1
  half).
- **Unit**: Stage 1 U0 ((4) E02 tag; L12 on HEAD's L.5 text); Stage 2 U5 ((2) references, (3) `:6499`/`:6513`); Stage 3 U8
  ((3) `@tunable` row); Stage 4 U15 ((2) behaviour); Stage 5 U20 ((1), (2) field set, (3) `hidden`/`specs_for()`, (4) Table
  279, (5) checks, with the fold's ring/cap and `bench`/`hardware_family` checks); Stage 6 U33 ((5) last paragraph);
  Stage 7 U36 ((3) opening and web rows, `decimals` among the keys as U23 leaves them, `crc` with the 2026-09-30 set).
- **Depends**: A.U0.29, A.U0.33, A.U0.39, A.U5.03, A.U5.07, A.U5.11, A.U8.03, A.U15.16, A.U20.01, A.U20.09, A.U20.17,
  A.U20.18, A.U20.20, A.U20.21, A.U20.24, A.U20.25, A.U20.34, A.U33.03, A.U36.514, A.S0930.01, M.DOCS.092;
  M.GEN.066 (the ring/cap check), M.GEN.017, M.GEN.018 (`decimals` for every numeric field).
- **Blast carried by**: the tag-family comments in `buildgen/` and `src/` → A.U36.514 (6) (GEN, SRC_*); BACKLOG `:638-658` →
  A.U33.03 (DOCS); `test_buildgen_web_tag.py` table check → A.U36.514 (TSC).
- **Kind**: rule, doc

### M.SPEC.150 L.7: product versioning, the build information, the release
- **From**: A.U36.519 (1)-(2), A.U20.31 ("both starting at `2.0b0`" goes), A.U36.502 (1) (the build information rendered on
  the System page), A.U6.24 (the same), A.U37.11 (2) (the release is the merge into `main`), A.U20.36 + A.U27.06 (the build
  date is the only varying value — amended by OR141.a (5)), M_DOCS gap 1 (c) (BACKLOG item 2's fact; M.DOCS.063);
  OR141.a (5) (the build date is a build input; the two-build check), OR139.a (2) (the build information names a
  test-only override), F21 tag form (A-C review fold).
- **Site**: `SPECIFICATION.md:6568-6590`.
- **Change**: (1) `:6570-6571` → A.U36.519 (1). (2) `:6580-6581` → A.U36.502 (1). (3) `:6587-6589` → A.U36.519 (2). (4) After
  the single-source paragraph, A.U37.11 (2)'s release paragraph (its decision tags in the C9 form: release-version-2-0
  and release-defined-point "(agent, <date>; owner-reviewed, 2026-10-02)"). (4.1) (A-C review fold) The build-information
  paragraph gains: "**The build date is a build input** (owner, 2026-10-05): a real build stamps its UTC build time into
  the build information, so two genuine builds differ there; the reproducibility check builds twice with one fixed date
  and compares everything else byte for byte, and a second check proves that changing only the date changes only that
  line (B.11). A test build that carries a test-only override names it here (B.14.5)." — wherever A.U20.36's "the build
  date is the only varying value" stood, this text replaces it. (5) After it, BACKLOG item 2's surviving fact as a
  migration-rule reason: "The legacy firmware rewrote its whole config file with defaults when one key was missing; this
  firmware keeps one config file per module and repairs only an invalid or missing value at boot (C.7.3), so an update that
  adds a key keeps every stored value, and a legacy unit moves to it by a fresh setup (README.md, the reflash runbook)."
- **Resolved**: M_DOCS gap 1 (c) routes item 2 here; its "**Decided: not patched on the current codebase**" half concerns the
  legacy tree (reference-only, no work) and is not carried (agent decision, OR2.c review).
- **Unit**: Stage 1 U6/U36 ((2)); Stage 1b U27 ((4.1), with the build-date input and the two checks, M.SCR.066, and the
  override's build-info name, M.SPEC.162 Stage 2); Stage 2 U36 ((1), (3), (5)); Stage 3 U37 ((4)).
- **Depends**: A.U6.24, A.U20.31, A.U36.502, A.U36.519, A.U37.11, M.SPEC.061 (C.7.3 repair text); M.SCR.066 and its tests
  (as the fold amends them), M.SPEC.162.
- **Blast carried by**: `buildgen/version.py` docstring → A.U36.519 (3) (GEN); README `## Release` → A.U37.11 (3) (DOCS);
  BACKLOG item 2 removal → M.DOCS.063.
- **Kind**: doc

## SPECIFICATION.md — Part M (`:6592-6805`)

### M.SPEC.151 Part M preamble and new M.2 SCD30, M.3 SGP40, M.4 BMP3XX
- **From**: A.U15.05 (preamble list; the three sections and their "Command waits" tables), A.U8.07 + A.U31.09 + A.U31.11 (the
  waits are Part N tunables, stated in ms), A.U15.01 (M.2 lists the range gate), A.U15.06 (M.2 NVM-write sentence), A.U15.08
  (M.2 0x0010 sentence), A.U15.12 (M.2 `FRCState` code table and four criteria), A.U36.537 (1), (3) (M.3 `VOCState` table; M.2
  marker), A.U15.13 + A.U15.14 + A.U15.19 + A.U15.20 (M.3 identity, compensation clamp, blackout, lost samples), A.U36.546 (2)
  (A.6's BMP390 paragraph becomes M.4's first line), A.U15.23 + A.U15.24 + A.U15.25 + A.U15.26 + A.U32.04 (M.4 contents),
  A.U36.006 (wear facts live in F.1; M.2 points there), A.U36.022 (3) and A.U36.546 (2) (the preamble also names M.5, M.6),
  A.U26.72 (M.2: the Altitude answer once measured).
- **Site**: `SPECIFICATION.md:6592-6597`; new sections after `:6805`.
- **Change**: (1) Preamble `:6597` "Only the ISL29125 has needed one so far." → "M.1 ISL29125, M.2 SCD30, M.3 SGP40, M.4 BMP3XX,
  M.5 WS2812, M.6 FRAM." (2) M.2/M.3/M.4 as A.U15.05 writes them — headings, "Command waits" tables, the sentences below each
  table — every wait in milliseconds and its value cell citing its Part N row (A.U8.07's IDs as A.U31.09/A.U31.11 rename them).
  (3) M.2 gains, in this order: the range gate (A.U15.01: readings outside the datasheet measurement ranges are rejected as
  failed reads); A.U15.06's NVM sentence (owner, 2026-09-26), pointing to F.1's "Which stores wear"; A.U15.08's 0x0010
  sentence (owner, 2026-07-22, `75f2e11`); A.U15.12's `FRCState` code table and four criteria with their sources and tags,
  preceded by `<!-- catalog: status.FRCState -->` (A.U36.537 (3)). (4) M.3 gains A.U15.13's identity sentence (owner,
  2026-07-21), A.U15.14's "Compensation inputs are clamped to Table 10's range and must be finite", A.U36.537 (1)'s
  `VOCState` table with its marker (the blackout row A.U15.19 pins), and, after phase C, A.U15.20's measured lost-sample figures
  with its statement. (5) M.4 opens with A.6's BMP390 paragraph (`:355-357`, the family shares one register map, with A.U0.40
  L49's datasheet citation), then A.U15.05's table with A.U15.25's computed-wait row and AN006 sentence, A.U15.23's
  `MeanAtmTemp` bound, A.U15.24's `PressOffset` warning sentence (code as landed), A.U15.26's `SampleInterv` sentence.
  (6) After phase C, M.2 gains A.U26.72's measured answer — whether a changed Altitude applies at once while `AmbPres` is 0 —
  with its date (the Altitude help text follows it, U15/U23).
- **Resolved**: the sections exist from U15 (C6: A.U36.537's catalog markers and A.U15.12's table cite them).
- **Unit**: Stage 1 U15 ((1) partial list, (2), (3), (4) without VOCState, (5)); Stage 2 U36 ((1) M.5/M.6 names, A.6's BMP390
  move, `VOCState` table, marker); Stage 3 phase C (A.U15.20 figures).
- **Depends**: A.U0.40, A.U8.07, A.U15.01, A.U15.05, A.U15.06, A.U15.08, A.U15.12-A.U15.14, A.U15.19, A.U15.20, A.U15.23-A.U15.26,
  A.U31.09, A.U31.11, A.U36.537, A.U36.546.
- **Blast carried by**: A.6 BMP390 paragraph removal → M.SPEC.019; DEVICE_REFERENCE FRC procedure → A.U36.531 (DOCS);
  `tests_scripts/test_error_catalog.py` marker check → A.U36.537 (4) (TSC); BACKLOG `:910-913` → A.U15.06 (DOCS).
- **Kind**: doc

### M.SPEC.152 New M.5 WS2812 and M.6 FRAM
- **From**: A.U36.022 (1)-(3), A.U36.546 (2) (FRAM chip facts from A.4 `:178` and C.3.1 `:1603-1604` move to M.6; endurance points
  to F.1), A.U36.006 (the wear figures).
- **Site**: new `## M.5` and `## M.6` after M.4.
- **Change**: M.5 = A.U36.022 (1) verbatim. M.6 "## M.6 FRAM (MB85RS64V, MB85RS2MTA; `asy_fram_driver.py`)": the two parts, their
  sizes and the RDID source (C.3.1 `:1603-1604`), "MB85RS64V reads are destructive internally" (A.4 `:178`), each re-checked
  against `datasheets/fram/` with its page; the endurance line points to F.1's "Which stores wear".
- **Resolved**: — (no conflict among the constituents)
- **Unit**: U36.
- **Depends**: A.U36.006, A.U36.022, A.U36.546.
- **Blast carried by**: A.6 WS2812 paragraph → A.U36.022 (2) (M.SPEC.019); A.4/C.3.1 pointers → M.SPEC.010/M.SPEC.049.
- **Kind**: doc

### M.SPEC.153 M.1 preamble and M.1.1 the owner's list
- **From**: A.U15.39 (preamble; req 18; A.6 line), A.U0.38 V62 (`:6601-6604`, superseded), A.U36.021 + A.U36.529 (CLAUDE.md
  parity points here; no SPEC edit), A.U0.25 A36 (`:6606` heading tag) and A37 (`:6654`), A.U0.33 B12 (`:6612`) and B10
  (`:6625-6626`), A.U36.506 (2) (item 16), A.U36.020 (req 18 consistent), A.U8.13 (Part N IDs).
- **Site**: `SPECIFICATION.md:6599-6658`.
- **Change**: (1) Preamble `:6601-6604` → A.U15.39's text. (2) `:6606` heading gains "(owner, 2026-09-12, `a2ea347`/`7890e2b`;
  later items tagged individually)". (3) `:6612` "Device and maths constants are not settings (M.1.3's classification note)."
  gains "(agent, 2026-09-14, `2ad5d9e`; open to change, owner 2026-09-26)". (4) `:6625-6626` "Do not re-propose either."
  deleted, "(owner, 2026-09-12, `a2ea347`)" added. (5) Item 16's sentence → A.U36.506 (2). (6) Req 18 → A.U15.39's text. (7)
  `:6654` "21." gains "Added later (owner, 2026-09-15, `5872365`), not one of the original twenty".
- **Resolved**: A.U0.38 V62 (U0) rewrites the preamble's legacy sentence; A.U15.39 (U15) replaces the preamble — its text keeps
  the same fact with the owner's 2026-09-26 tag.
- **Unit**: Stage 1 U0 ((2)-(4), (7), V62); Stage 2 U15 ((1), (6)); Stage 3 U36 ((5)).
- **Depends**: A.U0.25, A.U0.33, A.U0.38, A.U15.39, A.U36.506.
- **Blast carried by**: DEVICE_REFERENCE calibration paragraph → A.U15.39 (DOCS); twin test comments → A.U36.020 (TWIN, M.TWIN.122/.126).
- **Kind**: doc

### M.SPEC.154 M.1.2-M.1.6: measured behaviour, register ownership, auto-range, calibration, range ratio
- **From**: A.U15.34 (M.1.2 "State across a task restart" table), A.U15.R04 (the participant-rung row), M_SRC_SENS GAP-16 (the
  INT re-arm flag row), A.U3.10 + A.U3.14 (`:6675-6678` the brownout latch → the central repeat rule), A.C.19 + A.C.10 (rows
  confirmed or re-measured, dated), A.U12.07 (M.1.3 McCamy error), A.U15.31 (the write-failure sequence form), A.U0.44 L34
  (`:6702`, `:6722`), A.U0.38 V63 + A.U15.39 (`:6731-6733` application notes), A.U0.33 B11 (`:6737-6739`, `:6748`), A.U15.32 +
  A.U15.33 + A.U15.35 (M.1.4 bullets), A.U15.30 (`:6752-6755` settle bullet), A.U0.25 A38 (`:6764`), A.U0.16 (`:6781`),
  A.U15.36 + A.U36.537 (2) (M.1.5 `CalLight` table with tones), A.U0.39 L33 (`:6804-6805`), A.U8.13 (Part N IDs).
- **Site**: `SPECIFICATION.md:6660-6805`.
- **Change**: (1) M.1.2 gains A.U15.34's restart-state table, with A.U15.R04's row ("a second consecutive failed cycle re-applies
  the whole configuration, as a brownout does") and GAP-16's row (the INT re-arm flag: reset at restart); `:6675-6678` "what
  `_recover_brownout()`'s `_brownout_seen` latch assumes" → the central repeat rule (C.7.1); after phase C each row confirmed
  gains "confirmed <date>, one specimen (the dev breakout)" or its re-measured value (A.C.19). (2) M.1.3: the colour-chain block
  gains A.U12.07's McCamy sentence; the divergence-detection text names the masked sequence (A.U15.31); `:6702` "Deliberately
  unused, so nobody adds them later:" → "Unused (agent, 2026-09-24, from FN8424 p6/p10/p13), each for the reason given:";
  `:6722` gains "Neither is a correction of the other"; `:6731-6733` → A.U15.39's application-notes text (it carries V63's
  "re-checked if the owner supplies them"). (3) M.1.4: `:6737-6739` → A.U0.33 B11's "The rule behind these items, generalised by
  the agent from two owner rulings (agent, 2026-09-24, `5b97af3`; open to change, owner 2026-09-26): …"; `:6748` "The
  switch-down point is derived" gains "(owner, 2026-09-14)"; the derived-down-point bullet gains A.U15.33's sentence; the INT
  bullet gains A.U15.32's sentence; the settle bullet → A.U15.30's text plus A.U15.35's "a passed deadline is moved up to now";
  constants cite their Part N IDs (A.U8.13). (4) M.1.5: `:6764` "Owner's design" gains "(owner, 2026-09-13, `f05f82d`: …; band
  windows and hold times: agent)"; A.U15.36's `CalLight` code table with A.U36.537 (2)'s tone column, marker and sentence;
  `:6781` gains A.U0.16's "(the peak-of-three rule: proposed by the agent, confirmed by the owner, 2026-09-12, `12a616a`)". (5)
  M.1.6 `:6804-6805` "do not re-raise it as actionable" → "not actionable on one board (owner, 2026-09-13, `05f4746`: 'Do not
  re-raise it as actionable')".
- **Resolved**: A.U3.10 and A.U3.14 rewrite `:6675-6678` the same way (the central rule) — one edit. A.U0.38 V63 and A.U15.39 both
  rewrite `:6731`; A.U15.39's text is the end state and keeps V63's clause.
- **Unit**: Stage 1 U0 (tags); Stage 2 U3 ((1) latch); Stage 3 U8 (Part N); Stage 4 U12 (McCamy); Stage 5 U15 ((1) table, (2)-(4)
  ISL rows); Stage 6 U36 (`CalLight` tones); Stage 7 phase C (A.C.19).
- **Depends**: A.U0.16, A.U0.25, A.U0.33, A.U0.38, A.U0.39, A.U0.44, A.U3.10, A.U3.14, A.U8.13, A.U12.07, A.U15.30-A.U15.36,
  A.U15.39, A.U15.R04, A.U36.537, A.C.19, M.SRC_SENS.074.
- **Blast carried by**: `flash/test_bus_concurrency.py` comment → A.C.19 (HW_DEV); driver comments → A.U15.30/A.U15.34 (SRC_SENS);
  twin fidelity rows → A.C.19 (TWIN).
- **Kind**: doc

## SPECIFICATION.md — Part N (new, after Part M)

### M.SPEC.155 Create Part N, the tunable-parameter register: N.1 rules, N.2 tag grammar and check, N.3 tables, N.4 rule rows
- **From**: A.U8.01 (the Part, its rules, row form, definitions), A.U8.02 (N.2 tag grammar and the register check), A.U8.03
  (the `@tunable` comment-cap exemption; L.6.4 row), M.SPEC.001 (TOC line), M.SPEC.003 (numbering N.1-N.4; Part letter `N`).
- **Site**: new `# Part N — Tunable Parameters` after Part M (end of file), with `## N.1 Rules`, `## N.2 Tag grammar and check`,
  `## N.3 Register tables`, `## N.4 Rule rows`.
- **Change**: A.U8.01's text verbatim for N.1 (the classes, the per-service timeout rule with "(owner, 2026-07-28)", the
  widening and host-load rules, the single-observation and blind-spot forms, the *config*/*test input*/*mirror* definitions, the
  "estimated (agent, <commit>) — measurement owed: <how, level>" form) and N.3/N.4's row form (C4); N.2 = A.U8.02's grammar and
  its `tests_scripts/test_tunables_register.py` check (tags and rows agree; relation checks such as `wdt.timeout_ms` ≤ 8388,
  `system.reset_delay_s` × 1000 < `wdt.timeout_ms`). N.3's table order: firmware, build, L0, L1, L2, L3/L4, CI, runners. A
  Sections line lists N.1-N.4 (M.SPEC.003).
- **Resolved**: — (no conflict among the constituents)
- **Unit**: U8 (Stage 1 for every later row; C6: the Part exists before the first `@tunable` tag cites it).
- **Depends**: A.U8.01, A.U8.02, A.U8.03.
- **Blast carried by**: the tags in every tier → the tagging actions (each cluster); `test_tunables_register.py` → A.U8.02 (TSC);
  CLAUDE.md comment-cap exemption list → A.U8.03 (DOCS); L.6.4 `@tunable` row → M.SPEC.149.
- **Kind**: rule, doc

### M.SPEC.156 Part N rows: every tagging action's rows, at the end state
- **From**: every action whose Blast or Change writes "Part N row(s)" (the 242 fragment clauses under Part N: A.U8.04-A.U8.24,
  A.U8C.*, A.U8C2.*, and the later units' new tunables — e.g. A.U9.04, A.U10.08, A.U10.26 `fram.verify_lock_timeout_ms`, A.U13.R01
  `i2c.clear_half_period_us`, A.U10.R01 `module.recover_*_at`, A.U17.*, A.U19.13 `web.serving_demand_budget_b`, A.U23.05/.06,
  A.U26.*, A.U31.*), OR141.a (4)-(5), OR143.a (1)-(2), OR137.a (1), OR139.a (1) (the fold's new tunables and the idle
  rate's owed measurement; A-C review fold), the Dependants lists (A.U8C.120, A.U8C.121, A.U8C2.51) as M_PROC gap 1 states their end state, A.U8.19 (rule
  rows `loop.sync_wait_max_us`, `loop.uart_call_span_max_us`; `spi.cs_settle_us`), A.U10.07 (rule rows `boot.unfed_stretch_1_ms`,
  `boot.unfed_stretch_2_ms`), A.U31.03 (rule row `boot.setup_unit_stretch_ms`), A.U31.01 (5) (`fram.block_hold_budget_us = 30000`),
  A.U28.36 (CI budgets), and the cluster gaps: M_HW_BENCH GAP-B7, M_HW_DEV GAP-D2 and GAP-D4, M_SRC_SENS GAP-1 and GAP-4, M_TEST_UNIT
  GAP-U9, M_TWIN gap (renames, withdrawals, one new row), M_TOOL gap 8, M_SCR gap 5, M_WEB gap 7; GAPS_G4 hand-off 4
  (reflash-row sites per M.HW_BENCH.014; starter grace and poll rows withdrawn per M.TEST_HELP.028/M.HW_DEV.117; gap pass G1).
- **Site**: N.3/N.4 (M.SPEC.155).
- **Change**: each tagging action writes its rows in the unit that lands its tags (row form C4; no audit ID in a cell), with these
  end-state amendments: (1) **Dependants** — A.U8C.120/.121/A.U8C2.51's lists as written, minus `l1.asy_notification_service_
  override_tick_s` (withdrawn with its literal, M.TEST_UNIT.090) and `l2.network_neopixel_never_connects_wait_s` (the wait is gone,
  M.TWIN.132); under `wdt.timeout_ms` the per-script feed rows (`l3.*_wdt_feed_every`, `l3.sgp40_fram_backup_restore_wdt_feed_
  interval_s`, `l3.fram_pause_unpause_and_gating_feed_step_s`) are replaced by one `l3.device_script_feed_step_ms = 2000` (the
  shared `tests_hardware/device_scripts/_shared/watchdog.py`, GAP-D2); entries "deferred U26 — listed if U26 keeps it" follow the
  HW_DEV/HW_BENCH end state; each entry states the relation in words. (2) **Rows no tagging action writes**, each "estimated
  (agent, <commit>) — measurement owed: <how, level>" unless stated: `l4.end_to_end_timing_reboot_loss_margin_s`, the two lwIP
  send-stall bounds (M.HW_BENCH.075), `l4.console_starvation_load_s` (GAP-B7); `runner.scenarios_timeout_s`,
  `l2.commanded_reset_margin_s`, `l0.cross_browser_smoke_poll_ms` (M_SCR gap 5); `ci.devices_timeout_min` (M.TOOL.016);
  `l2.clock_jump_wait_timeout_s` (M.TWIN.146); the `tests_js` rows `l0.poll_manager_poll_ms`, `l0.render_*`, `l0.live_twin_*`,
  `l0.live_matrix_poll_ms`, `l0.put_matrix_*`, `l0.live_concurrent_tabs_timeout_ms`, `l0.live_restart_recovery_timeout_ms`,
  `web.poll_backoff_max_ms`, `web.device_watch_interval_ms` (M_WEB gap 7; the last two with A.U23.05/.06's Basis and Margin);
  `l1.asy_notification_service_next_sleep_min_ms = 59000` (GAP-U9: A.U8C2.02's `_s` row in ms after A.U31.14). (3) **Renames**:
  `led.refresh_hz_default` → `led.refresh_hz`, `led.overlay_brightness_default` → `led.overlay_brightness`, with every Dependant
  naming them (GAP-4); `l2.uart_link_collect_*` → `l2.uart_link_pause_*` (A.U17.04); `l2.uart_link_leak_budget_bytes` →
  `l2.uart_link_leak_rate_bytes_per_transfer` (M.TWIN.158); `udp.ready_poll_ms` → `udp.poll_wait_ms = 20` and `udp.poll_idle_ms =
  100` (A.U18.05); the Sites of `l3.toolchain_flash_boot_picotool_load_attempts`, `l3.toolchain_flash_boot_load_timeout_s`
  and `l3.toolchain_flash_boot_load_retry_backoff_s` → `tests_hardware/harness.py` (`reflash()`, the loop it absorbs,
  M.HW_BENCH.014), the load timeout also `tests_hardware/manual/manual_toolchain.py`; the chip-wait rows' `…_s` → `…_ms` (A.U31.09, A.U31.11); `l3.conformance_twin_probe_timeout_s` follows the
  module rename (M.HW_BENCH). (4) **Withdrawn rows**: `l2.sensortask_integration_dns_query_*`/`…_override_poll_*` (M.TWIN.144),
  the per-script feed rows of (1), A.U8.15's 8M heapsize tag on the conformance launcher (M.HW_BENCH), A.U8C.96/A.U8C2.42's rows on
  the folded raw UART script (M.HW_DEV.049), `udp.conn_tries_default` (A.U18.13 removes the parameter),
  `l3.heap_layout_after_full_boot_sequence_starter_loop_grace_ms` and `l3.heap_layout_after_full_boot_sequence_starter_poll_ms`
  (A.U8C.01/A.U8C.72's rows; the grace sleep and the poll loop go with M.TEST_HELP.028 and M.HW_DEV.117). (5) **Rule rows'
  checks**: `loop.uart_call_span_max_us` "Checked by" → `tests_hardware/flash/test_uart_crossover.py`'s driver test (the verdict
  moved host-side, GAP-D4); `loop.sync_wait_max_us` "Checked by" → `tests_scripts/test_src_sleep_forms.py`, Dependants gain the
  boot bus clear with its bound (≤ 9 SCL pulses of 10 µs and a STOP per bus, GAP-1). (6) **Tool rows** (M_TOOL gap 8):
  `tool.uv_sync_attempts`/`tool.uv_sync_backoff_step_s` name both sites and "every retried network step, uv sync included";
  `tool.preprocess_timeout_s` also bounds the kbd and lwIP-host readbacks; `tool.remote_query_timeout_s` covers the `sudo -n`
  probes, `tee`, `systemd-run`/`systemctl`. (7) CI job budgets carry A.U28.36's measured basis with its run id. (8) (A-C
  review fold) `udp.poll_idle_ms = 100` keeps its value with "estimated (agent, <commit>) — measurement owed: the
  event-loop share an idle captive-DNS listener's polling takes and its first-query latency, L2 (twin) and L4 (bench)"
  (owner, 2026-10-05: kept, its measurement owed). New rows for the tunables the fold adds, by the IDs their `@tunable`
  tags land: `UARTComm`'s `chunk_bytes` and `max_transfer_bytes` defaults and `dev`'s declared receive-ring size and cap
  (Basis: J.6's floor derivation — one frame, one poll interval, the stop-and-wait bytes during the longest synchronous
  flash write, rounded up to a power of two; Re-check trigger: a `payload_size`, `timeout`, baud or flash-part change);
  the hourly window's 24 bins of 3600 s (Basis: owner, 2026-10-01); the tick-offset override's 2**32 ms − 15 min
  (Basis: the wrap about 15 minutes after boot, owner, 2026-10-01); the interrupts-off sweep's windows (3 ms, 45 ms,
  400 ms and one past the ring bound: the W25Q16JV tPP/tSE figures, J.6). Each row is written in the unit that lands
  its tag (U13/U17/U20 for the UART values, U19 for the window, U21 for the override, U26 for the sweep).
- **Resolved**: M_PROC gap 1's end-state rule over the U8C lists (drops above); the GAP rows are carried here because no tagging
  action writes them (each cluster's gap names SPEC).
- **Unit**: each row with its tagging action (U8, U8C, U8C2, then the unit introducing the tunable); (1) and (3)-(5) at the unit
  whose action changes the row (U17, U18, U24-U26, U31, U35); (2) with the action that creates the literal; (7) at U28's CI run.
- **Depends**: A.U8.01-A.U8.24, A.U8C.*, A.U8C2.*, A.U10.07, A.U28.36, A.U31.01, A.U31.03, M.HW_BENCH.067/.075/.082,
  M.HW_BENCH.014, M.HW_DEV.004/.048/.049/.068/.117/.140, M.TEST_HELP.028, M.SCR.040/.054/.063, M.TEST_UNIT.090/.091, M.TOOL.016/.041/.046, M.TWIN.132/.144/.146/.158,
  M.WEB (gap 7), M.SRC_SENS.002/.008/.021; M.SRC_NET.221, M.SRC_NET.220, M.GEN.066,
  M.SRC_CORE.133, M.TOOL.080, M.HW_DEV.160 (the tags of the fold's new tunables).
- **Blast carried by**: the tags themselves → their tagging actions (each tier's cluster); the register check → M.SPEC.155.
- **Kind**: doc

### M.SPEC.157 Part N bases: the B3 measurements and the phase-C deltas
- **From**: A.U35.56 + M.PROC.028 + M_PROC gap 2 (test-tier rows measured), A.C.10 (phase-C deltas into Part N), A.C.02 (6) (the
  speed-probe bands), A.C.03 (4) (silicon figures behind firmware rows), A.U19.13 (`web.serving_demand_budget_b` re-derived).
- **Site**: Part N rows whose Basis reads "estimated".
- **Change**: per A.U35.56/M.PROC.028: a hang bound or `wait_for` limit → "measured (agent, <date>): max <x> over 20 runs at 32×
  parallelism", value at the stated margin; a poll step or retry count → "design choice" with its reason; a wait the driven clock
  replaced → the row goes with its literal; an `l3.`/`l4.` row keeps "estimated" until phase C, whose A.C.10 delta writes its
  measured basis (date, image, run count); A.C.02 (6)'s speed-probe bands and A.C.03 (4)'s silicon figures land on their rows the
  same way. Each value change lands tag and row together.
- **Resolved**: — (no conflict among the constituents)
- **Unit**: Stage 1 U35 (B3); Stage 2 phase C (A.C.10 deltas).
- **Depends**: A.U35.56, A.C.02, A.C.03, A.C.10, M.PROC.028, M.PROC.029.
- **Blast carried by**: the tagged literals → their tiers' clusters (B3/C deltas); the release note's "estimated" list → A.U37.12
  (DOCS).
- **Kind**: doc

## Merged changes found by the ledger pass (each placed in its Part; numbered after the rest)

### M.SPEC.158 F.1 gains the CYW43 values this code names
- **From**: A.U18.27 (the list: `_STAT_JOINED_NO_IP`, `_PM_NO_POWERSAVE` with their sources), A.U18.36 (the `status("stations")`
  defect beside it), A.U36.023 (the pin-move re-check re-reads the list).
- **Site**: `SPECIFICATION.md` F.1, a new paragraph after the UDP-on-rp2/lwIP and `WLAN.status()` facts (M.SPEC.093 (5)).
- **Change**: "**CYW43 values this code names** (re-read at every pin move, this Part's opening paragraph): link status 2,
  `CYW43_LINK_NOIP` — joined, no IP yet; `network` exports no name for it (`cyw43.h:100`; `extmod/modnetwork.c:197-202`),
  named `_STAT_JOINED_NO_IP` in `asy_wifi_service.py`; the power-management word `0xA11140`,
  `CYW43_PM_VALUE(NO_POWERSAVE, 200, 1, 1, 10)` — power save off with `PM_PERFORMANCE`'s listen fields
  (`extmod/network_cyw43.c:43-51`), legacy's word, named `_PM_NO_POWERSAVE`. One defect: a `status("stations")` whose ioctl
  fails returns an empty list (`cyw43_ctrl.c:725-727`), but if the chip cannot be brought up (`:719-722`) it returns 32
  entries of uninitialised data (`network_cyw43.c:377-388`), read as a client present — the hotspot then stays up and the
  failing chip surfaces through the connect-attempt tier (agent, 2026-09-30)." — every upstream cite at the pin (C3).
- **Resolved**: A.U18.27/A.U18.36 name an F.1 home that no Part F change carried — gap fill from their texts (agent decision,
  OR2.c review).
- **Unit**: U18 (with A.U18.27/A.U18.36's code).
- **Depends**: A.U18.27, A.U18.36, M.SPEC.093.
- **Blast carried by**: `asy_wifi_service.py` constants and comments → A.U18.27 (SRC_NET); `digital_twin/network.py` status
  constants → U25 (TWIN); C.7's WIFI review paragraph → A.U18.36 (M.SPEC.058).
- **Kind**: doc

### M.SPEC.159 B.4 gains the shell-script conventions
- **From**: A.U27.33 (Blast: "SPEC B (scripts) gains a short 'Shell script conventions' paragraph (the four rules)").
- **Site**: `SPECIFICATION.md` B.4 (as M.SPEC.028 leaves it), a closing paragraph.
- **Change**: "**Shell script conventions** (agent, 2026-09-30), checked over every `scripts/*.sh` by an L0 test: the first
  command after the header is `set -euo pipefail`, or a `set` line carrying its reason on the same line; at most one
  `trap … EXIT`, armed before any `mktemp`; no loop over an unquoted expansion; every runner taking a device validates it
  through `scripts/_devices.sh`'s `require_device` before any work, and a flag without its value is a usage error (exit 2,
  E.10)."
- **Resolved**: A.U27.33's Blast names the paragraph but no merged change carried it — gap fill from its four rules
  (agent decision, OR2.c review).
- **Unit**: U27.
- **Depends**: A.U27.08, A.U27.33, M.SPEC.028, M.SPEC.086.
- **Blast carried by**: the scripts and the L0 test → A.U27.33 (SCR, TSC); BACKLOG chroot entry → A.U27.33 (DOCS).
- **Kind**: rule, doc

### M.SPEC.160 E.2.3, E.6.6 and K.10 gain the test-standard items no Part E change carried
- **From**: A.U24.60 (the strict JSON oracle serves every test), A.U35.33 (months of uptime under a driven clock is the
  long-uptime proof), A.U35.28 (every finite resource loaded; the fault-storm log rate cites F.3's `rate.persisted_log`),
  A.S0930.20 (the L0 guards of the command set among the test catalog), A.U35.04 (one targeted fault-planting pass per new
  module), A.U26.63 (DHCP-client faults are out of scope, stated once), A.U24.02 Blast (the test standard names the
  const-mirror check).
- **Site**: E.2.3 (M.SPEC.077 (4)); E.6.6's "Out of scope entirely" paragraph (`:3234`, M.SPEC.083); K.10's gate (M.SPEC.143).
- **Change**: (1) E.2.3 gains: "Every test that reads emitted JSON parses it with `tests/_strict_json.py`'s oracle, which
  rejects duplicate keys (escaped spellings included) as well as JSON MicroPython's parser would accept (F.1)." and "Months
  of uptime are proven per device by a driven-clock scenario, never by a wall-clock soak (E.9)." and "**Load**: every finite
  resource — connections, pcbs, the heap, FRAM chunk operations, the persisted-log rate — is loaded to its bound at the
  level that has it; the fault-storm log test measures each module's rate against F.3's `rate.persisted_log` row." and "The
  system-command set (its definitions, callback, mirror, mock, website and feed sites) is held together by L0 guards." and
  "A test-side copy of a `src/` constant reads it through `src_const(...)`, or is a literal citing its external source on
  its line or the line above and equal to the `src/` value; a copy under another name carries `# pins src/<file>.py
  <NAME>`; `tests_scripts/test_const_mirrors.py` fails on any other." (2)
  E.6.6's "Out of scope entirely" paragraph gains "DHCP-client faults: the unit uses DHCP results only (a known limitation,
  owner, 2026-09-26; `tests_hardware/README.md`)". (3) K.10's gate gains "one targeted fault-planting pass over the new module
  in a throwaway worktree — each planted fault caught by a test, nothing from the worktree kept".
- **Resolved**: each constituent names a Part E home "U36 writes it" that no Part E action carried — gap fill, the sentences
  taken from the constituents (agent decision, OR2.c review).
- **Unit**: U36 (after U24, U35, the 2026-09-30 set, U26).
- **Depends**: A.S0930.20, A.U24.02, A.U24.60, A.U26.63, A.U35.04, A.U35.28, A.U35.33, M.SPEC.077, M.SPEC.083, M.SPEC.097, M.SPEC.143.
- **Blast carried by**: the tests themselves → their actions (TEST_UNIT, TEST_HELP, TSC, HW_BENCH).
- **Kind**: rule, doc

### M.SPEC.161 The renamed hardware gates in SPEC text
- **From**: A.U26.74 (2) (`--allow-persistence-writes` → `--allow-persistence-write`; `long_soak` → `soak_duration` with its
  valued `--soak-duration`; its Site lists `SPECIFICATION.md` among every user of the old names), A.U26.35 (the soak duration).
- **Site**: `SPECIFICATION.md:2144` (C.8's SCD30 budget text, M.SPEC.065), `:5157` (I.5, M.SPEC.131); every further SPEC hit of
  the old names at landing (grep).
- **Change**: `:2144` "`--allow-persistence-writes`" → "`--allow-persistence-write`"; `:5157` "a `long_soak`-gated 600s
  variant" → "a 600 s variant run under `--soak-duration` (marker `soak_duration`)"; `:990` `--allow-flash-cycle` stays.
- **Resolved**: A.U26.74's Site names SPEC among the old names' users; no Part C/I change carried the rename — written
  here (agent decision, OR2.c review).
- **Unit**: U26 (with the rename); M.SPEC.131's U36 rewrite of I.5 keeps the new name.
- **Depends**: A.U26.35, A.U26.74, M.SPEC.065, M.SPEC.131.
- **Blast carried by**: CLAUDE.md wear rule and `tests_hardware/README.md` → A.U26.74 (DOCS, HW_BENCH).
- **Kind**: doc

## Gaps for other clusters

1. **DOCS — the refresh bullet's section number.** M.DOCS's A.SDEP.22 text has CLAUDE.md's MicroPython-refresh bullet cite
   "Part F.5.10"; the section lands as F.9 (M.SPEC.109, numbering by M.SPEC.003), so that bullet reads "Part F.9".
2. **DOCS — the tag-line pointer.** M.DOCS.092 has CLAUDE.md's machine-read tag-line exemption point at "L.6.4" and at "the
   `@web`/`@web-group` grammar H.5.1"; the grammar moves into L.6.4 (M.SPEC.118, M.SPEC.149), so the pointer names L.6.4
   only and the H.5.1 half goes.
3. **TEST_UNIT — the idle-wait degrade test cannot fail on the test rig.** `test_an_idle_wait_beyond_the_ticks_range_returns_false`
   (M_TEST_UNIT `:3682`, from A.U13.19) sets `poll_idle_ms = 2**29`. That is outside rp2's range (ticks period 2**30) but
   well inside the Unix test rig's (2**62 on the 64-bit port, SPEC F.1 `:3536`), so on the rig `asyncio.sleep_ms()` raises
   nothing. The never-ready `_StepPoller` returns `False` anyway, so the test passes without reaching the degrade path it
   is named for. The test needs a value beyond the rig's half-period (above 2**61), or the 2**30 tick fake that the wrap tests
   already use (M.TEST_UNIT.313). F.8.2's sentence (M.SPEC.108) states the rp2 behaviour and needs no change.

No other cluster receives a SPEC-side gap. TWIN's gap came the other way (into SPEC: the L2 real-website proof text) and is
carried by M.SPEC.035 (e) and M.SPEC.121 (1)/(d).

## Adherence findings

Rule breaches found in HEAD's SPEC or in the input actions. Each one is fixed by the merged change named. None needs the
owner.

- **Stale facts stated as current** (CLAUDE.md: docs hold current state; OR43.a (3)). No action fixed these, so the merge
  did: A.1's `datasheets/` line after A.U28.35 moves the PDFs (M.SPEC.005); A.2 `:122` calls the legacy firmware
  "Deployed" (M.SPEC.006); A.4 `:175-176` "keeps its number" after A.U2.09/A.U3.04 (M.SPEC.010); the A.4 owner list's "no
  colour-coding" after A.U23.20's CalLight tone (M.SPEC.016); A.9's "wozi's for the unit and web tiers" (M.SPEC.022); B.11's
  "parametrized over `wozi`/`dev`", already false at HEAD (M.SPEC.035); the Part C intro's "three drivers" (M.SPEC.046);
  C.2's NTP `max_module_error` mention and its pre-2026-09-10 Python `_WIRING` tuple (M.SPEC.047); J.7's "twin has no
  `UART` at all today" (M.SPEC.137); F.5's "Deployed units stay on 1.26", where the legacy units run 1.24.1 (M.SPEC.099).
  CLAUDE.md's matching "1.26" is A.U1.12's, carried by DOCS.
- **An owner tag on agent text** (CLAUDE.md: owner decisions are quoted, not paraphrased). A.U0.33 C14 credits C.5.3's
  "persist first, then push" order to the owner, but the owner's answer (OR69.a (4)) holds only the `res` semantics. C.5.2
  states A.U11.28's order as the mechanism, and C.5.3 keeps only the owner's sentence (M.SPEC.055).
- **A superseded-label input.** A.U15.12's Blast "wozi 17 chunks, `CFGMGR_SCD30`" is stale after GAP-G7/GAP-10 (the SCD30
  store logs to RAM only). A.7 gains no chunk (M.SPEC.020).
- **Inputs naming a home that no action writes.** Several actions say "U36 writes it" for text that no U36 action carries:
  the E.2.3 test standard (M.SPEC.077, M.SPEC.160), C.8's cancellation line (M.SPEC.064), the G.2 UDP and poller entries
  (M.SPEC.111), F.1's CYW43 values (M.SPEC.158), B.4's shell conventions (M.SPEC.159), the renamed hardware gates
  (M.SPEC.161), and the 0.4 catalog's conventions check (M.SPEC.002). Each is a gap fill taken from its constituent's own
  words.
- **History and numbering against the standing rules.** A.U14.23's sentence on the 1.27→1.28 rp2 commits describes
  superseded tags (C2) and is not carried (M.SPEC.087). A.SDEP.21/.22/A.U36.023 file a standing list under F.5's per-pin
  record as "F.5.10", which A.U36.532's by-topic rule forbids, so it lands as F.9 (M.SPEC.109). A.U36.517 (6) describes,
  as the U36 end state, a file that U25 deletes; the landed text names the harness instead (M.SPEC.121).
- **Audit IDs in quoted text** (C1). Several constituent quotes carry IDs, for example A.U1.18's H.1 wording. They are
  stripped on landing (C1, every change).

## Owner questions

None. Every conflict was settled by a firm owner answer (OR113-OR133 as quoted, OR131-OR133 written firm), by a
standing rule (C1-C8, A.U36.532's structure, CLAUDE.md), or by an agent decision listed below. There are 128 Resolved
entries; 38 of them have no conflict.

## Agent decisions for the OR2.c review

Placement and gap-fill choices that no owner answer settles, each recorded in its change's Resolved line:

- M.SPEC.002: A.U36.031's P4 entry is placed as one "Under P4:" paragraph in 0.2, with its pointer at B.15. The 0.4
  catalog names `tests_scripts/test_code_conventions.py` (A.U10.47 Blast; added by the ledger pass).
- M.SPEC.003 / M.SPEC.109: "F.5.10" is numbered F.9. The HEAD sections F.5.7-F.5.9 become F.8.x.
- M.SPEC.011: the `FRCState` pointer joins the operator bullet.
- M.SPEC.012 / M.SPEC.013: A.4 bullets are filled from the constituents' Change text, because the Blast gave none.
- M.SPEC.020 (d): A.7 states rules and labels its list a worked example, with the generated `expected` file as the authority.
- M.SPEC.026: A.U21.02's help-text wording is shortened to a comment column.
- M.SPEC.027: A.U21.03's "step 8" lands as B.3 step 7 (B.3 has six steps at HEAD).
- M.SPEC.035 (e): B.11's proof parenthesis names the harness scenarios (M_TWIN gap).
- M.SPEC.036: the incident narrative of (5) goes under A.U36.548's rule.
- M.SPEC.039: B.14.1's Verified paragraph names the six devices defined that day.
- M.SPEC.047: the C.2 `@wiring` sentence and the constructor-tail text are written here, because no action gives the text.
- M.SPEC.051: A.U18.39's C.4 sentence lands in U18, not U36.
- M.SPEC.055: the C.5.2/C.5.3 split between the mechanism and the owner's `res` sentence.
- M.SPEC.058: one paragraph per family; A.U25.65's end-state statement replaces C.7's pre-answer sentence.
- M.SPEC.064 (c): the C.8 cancellation paragraph is a gap fill from A.U18.07/A.U18.31/A.U35.48.
- M.SPEC.074: D.5 names GAP-1's two `sleep` exceptions.
- M.SPEC.075: A.U28.30/A.U28.27's D.6 sentences land in U28 with their check.
- M.SPEC.077 / M.SPEC.160: E.2.3 is created from the constituents' sentences, including the const-mirror rule (A.U24.02,
  added by the ledger pass).
- M.SPEC.087: BACKLOG item 3's standing home is the Part F intro. A.U14.23's history sentence is not carried.
- M.SPEC.088: the watchdog cap's source and its Part N pointer are a gap fill from A.U8.02/A.U8.08.
- M.SPEC.091: the bytearray-truncation fact is a gap fill, and A.U31.19's float fact sits with the float paragraph.
- M.SPEC.093: the forwarded-cancel fact lives in F.1's asyncio list, cited once. The `asyncio.run()` catch clause is a gap
  fill. A.SDEP.17's W-items are conditional.
- M.SPEC.106: neither F.6 nor B.14.1 describes a deleted helper as live.
- M.SPEC.111: G.2's wiring-declaration entry and the single UDP/poller entry are gap fills. `_trigger_loop()` is used
  (GAP-8), and `report_if_fatal()` is placed in `asy_print_log` (GAP-G8).
- M.SPEC.116: the `LastTaskEnd` row comes from A.U32.06's `/status` field.
- M.SPEC.121 (d): H.7's L2 proof names the harness scenarios (M_TWIN gap).
- M.SPEC.137 (b): the UART-fakes facts land in J.7, not J.9 (M_DOCS gap 1 (c) routing).
- M.SPEC.150: the legacy "not patched" half of item 2 is not carried.
- M.SPEC.156: Part N rows that no tagging action writes are carried here with an "estimated" basis.
- M.SPEC.158 / M.SPEC.159 / M.SPEC.161: ledger-pass gap fills (F.1 CYW43 values, B.4 shell conventions, the renamed
  hardware gates).

## Ledger

Every action in the universe: 221 index pairs (I), 41 extras whose Site names SPEC (E), and every action whose
Change or Blast clause names SPEC (B). The union is 1,138 actions. 1,112 are carried: 1,088 through a merged change's From
line, and 24 by the M-ID their row names (each a Blast-only SPEC clause, or a Part N row edit carried by M.SPEC.156/.157). 26
are dropped, each with its reason. Every index pair is carried. Three of the dropped actions are extras, flagged "[extra]":
A.U17.12, A.U20.40 and A.U36.522. Each edits an audit working file, a code comment or the README, and only cites a SPEC
section that stays.

**Cluster gaps carried** (incoming → M-ID):
- M_DOCS gap 1: (a) M.SPEC.094; (b) M.SPEC.058; (c) item 3 → M.SPEC.087/.088, item 2 → M.SPEC.150, SPI RX overrun →
  M.SPEC.101, UART fakes → M.SPEC.137, peer allocation → M.SPEC.138, shared COBS → M.SPEC.111, the two UART findings →
  M.SPEC.050, mypy `Timer` → M.SPEC.043; (d) M.SPEC.087; (e) M.SPEC.130; (f) M.SPEC.045; (g) M.SPEC.118/.149 (the DOCS half
  is gap 2 above); (h) M.SPEC.137; (i) M.SPEC.107 and M.SPEC.137.
- M_PROC: gap 1 (Part N Dependants, with its drops) → M.SPEC.156; M.PROC.016 (F.7 rows) → M.SPEC.107; M.PROC.024 (F.1
  wrap sentence) → M.SPEC.092; M.PROC.028 / A.C.10 (Part N bases) → M.SPEC.157; E.6 rows (A.U26.51 with A.U7.25) →
  M.SPEC.083; M.PROC.011 (conditional F texts) → M.SPEC.086 note, .093, .094, .100, .108; M.PROC.031 (U37 second F.5
  record) → M.SPEC.099, .109.
- M_HW_BENCH GAP-B4 → M.SPEC.089; GAP-B7 → M.SPEC.156. M_HW_DEV GAP-D2, GAP-D4 → M.SPEC.156.
- M_SCR gap 5: Part N rows → M.SPEC.156; exit 2 (OR133) → M.SPEC.078/.079/.086 (E.10); lock directory (M.SCR.012) →
  M.SPEC.076, .022; port-53 scenarios (M.SCR.017) → M.SPEC.076/.077/.085; `tests_js/_twin_process.js` → M.SPEC.121/.123.
- M_SRC_CORE GAP-G7 → M.SPEC.020; GAP-G8 → M.SPEC.058/.111; GAP-G9 → M.SPEC.126; GAP-G13 → M.SPEC.021/.052/.054/.068/.111.
- M_SRC_SENS GAP-1 → M.SPEC.074/.097/.156; GAP-4 → M.SPEC.156; GAP-8 → M.SPEC.111; GAP-10 → M.SPEC.020; GAP-13 →
  M.SPEC.064; GAP-15 → M.SPEC.052/.058; GAP-16 → M.SPEC.154.
- M_TEST_HELP GAP-H5 → M.SPEC.077/.084/.145. M_TEST_UNIT GAP-U9 → M.SPEC.156; GAP-U10 → M.SPEC.084.
- M_TOOL gap 8 → M.SPEC.028/.033/.034/.156. M_TWIN gap → M.SPEC.156 (rows), M.SPEC.137 (J.7 files), M.SPEC.035/.121 (the L2
  proof). M_WEB gap 4 (a)-(b) → M.SPEC.120; (c), (e) → M.SPEC.116; (d) → M.SPEC.114/.124; gap 7 → M.SPEC.156. M_GEN gap 10
  is mention-only (nothing to carry). M_SRC_NET and M_TSC name no SPEC gap.
- Gap pass G1 (2026-10-01, `GAPS_G1.md`): every item above re-read in its carrying change's body; two amended —
  M.SPEC.077 (A.U36.016's "wrapper files" clause names the `PER_DEVICE` marker; M_TWIN gap) and M.SPEC.089's Blast
  (`.gitignore` is M.PROC.019's). M_TEST_HELP GAP-H5's H.7.1 citer list needs no edit: A.U36.532 (3) changes no H.7.1
  citer. GAPS_G4 hand-off 4: M.SPEC.156 amended (the reflash rows' site is `harness.py`; the starter grace and poll rows
  are withdrawn). GAPS_G2 H-5: M.SPEC.056 (C.5.3), M.SPEC.068 (C.10), M.SPEC.081 (E.5.1) and M.SPEC.070 (C.13)
  amended. GAPS_G3 hand-off 5: M.SPEC.026's timing names the file as it was when measured.

| Action | Src | Merged change(s), or dropped with reason |
|---|---|---|
| A.C.01 | B | M.SPEC.037 |
| A.C.02 | EB | M.SPEC.157 |
| A.C.03 | B | M.SPEC.090, M.SPEC.102, M.SPEC.125, M.SPEC.157 |
| A.C.04 | B | M.SPEC.113 |
| A.C.06 | B | M.SPEC.041, M.SPEC.042 |
| A.C.07 | B | M.SPEC.067 |
| A.C.09 | B | M.SPEC.129 |
| A.C.10 | IB | M.SPEC.041, M.SPEC.090, M.SPEC.099, M.SPEC.113, M.SPEC.125, M.SPEC.154, M.SPEC.157 |
| A.C.13 | B | M.SPEC.132 |
| A.C.14 | B | M.SPEC.062 |
| A.C.15 | B | M.SPEC.048 |
| A.C.17 | B | M.SPEC.061, M.SPEC.096 |
| A.C.19 | IB | M.SPEC.154 |
| A.S0930.01 | B | M.SPEC.060, M.SPEC.136, M.SPEC.146, M.SPEC.149 |
| A.S0930.02 | B | M.SPEC.147 |
| A.S0930.03 | B | M.SPEC.137 |
| A.S0930.04 | B | M.SPEC.137 |
| A.S0930.07 | B | dropped: a `UART_C_PORT_CHANGELOG.md` Class B row; no SPEC text (UART cluster) |
| A.S0930.08 | IB | M.SPEC.136, M.SPEC.137 |
| A.S0930.09 | B | M.SPEC.021, M.SPEC.024 |
| A.S0930.10 | B | M.SPEC.119 (Blast: the refused-command text is A.S0930.30's, carried there) |
| A.S0930.11 | B | M.SPEC.021, M.SPEC.147 |
| A.S0930.12 | B | M.SPEC.021 |
| A.S0930.13 | B | M.SPEC.014, M.SPEC.020, M.SPEC.111 |
| A.S0930.14 | B | M.SPEC.010, M.SPEC.096, M.SPEC.128 |
| A.S0930.15 | EB | M.SPEC.021 |
| A.S0930.16 | B | M.SPEC.055, M.SPEC.061 |
| A.S0930.17 | B | M.SPEC.010, M.SPEC.049, M.SPEC.064 |
| A.S0930.18 | B | M.SPEC.021, M.SPEC.093 |
| A.S0930.20 | B | M.SPEC.160 |
| A.S0930.25 | B | M.SPEC.010 |
| A.S0930.30 | IB | M.SPEC.010, M.SPEC.020, M.SPEC.021, M.SPEC.024, M.SPEC.049, M.SPEC.064, M.SPEC.093, M.SPEC.096, M.SPEC.111, M.SPEC.116, M.SPEC.119, M.SPEC.128 |
| A.S0930.31 | B | M.SPEC.021 |
| A.S0930.32 | B | M.SPEC.021 |
| A.S0930.33 | B | M.SPEC.021, M.SPEC.096 |
| A.S0930.41 | IB | M.SPEC.006, M.SPEC.010, M.SPEC.018, M.SPEC.021, M.SPEC.024, M.SPEC.096, M.SPEC.128 |
| A.SDEP.02 | B | M.SPEC.081 |
| A.SDEP.03 | B | M.SPEC.043 |
| A.SDEP.04 | B | M.SPEC.124 |
| A.SDEP.05 | B | M.SPEC.033 |
| A.SDEP.06 | EB | M.SPEC.005, M.SPEC.018, M.SPEC.132 |
| A.SDEP.07 | EB | M.SPEC.005 |
| A.SDEP.08 | EB | M.SPEC.040, M.SPEC.041, M.SPEC.042, M.SPEC.050, M.SPEC.075, M.SPEC.087, M.SPEC.099, M.SPEC.105 |
| A.SDEP.09 | B | M.SPEC.104 |
| A.SDEP.10 | B | M.SPEC.098 |
| A.SDEP.12 | B | M.SPEC.031 |
| A.SDEP.13 | B | M.SPEC.041, M.SPEC.042, M.SPEC.122 |
| A.SDEP.14 | B | M.SPEC.040, M.SPEC.041, M.SPEC.121 |
| A.SDEP.15 | B | M.SPEC.043, M.SPEC.104 |
| A.SDEP.16 | B | M.SPEC.076, M.SPEC.106, M.SPEC.107, M.SPEC.137 |
| A.SDEP.17 | EB | M.SPEC.093, M.SPEC.094, M.SPEC.096, M.SPEC.100, M.SPEC.108 |
| A.SDEP.18 | B | M.SPEC.018, M.SPEC.122, M.SPEC.127 |
| A.SDEP.19 | B | M.SPEC.033, M.SPEC.034, M.SPEC.123, M.SPEC.124 |
| A.SDEP.21 | EB | M.SPEC.087, M.SPEC.099, M.SPEC.109 |
| A.SDEP.22 | B | M.SPEC.003, M.SPEC.109 |
| A.U0.05 | B | dropped: audit tooling (packet "References" list); no SPEC text |
| A.U0.07 | B | M.SPEC.089 |
| A.U0.08 | B | dropped: the TSC citation check; SPEC side is convention C6 (header), no SPEC text |
| A.U0.12 | IB | M.SPEC.126 |
| A.U0.16 | IB | M.SPEC.118, M.SPEC.154 |
| A.U0.17 | IB | M.SPEC.054 |
| A.U0.19 | IB | M.SPEC.037, M.SPEC.048, M.SPEC.058, M.SPEC.145, M.SPEC.148 |
| A.U0.21 | IB | M.SPEC.071 |
| A.U0.22 | B | M.SPEC.094 |
| A.U0.23 | B | M.SPEC.007 |
| A.U0.25 | IB | M.SPEC.007, M.SPEC.010, M.SPEC.011, M.SPEC.016, M.SPEC.065, M.SPEC.090, M.SPEC.102, M.SPEC.108, M.SPEC.115, M.SPEC.116, M.SPEC.121, M.SPEC.132, M.SPEC.134, M.SPEC.153, M.SPEC.154 |
| A.U0.27 | B | dropped: `tests_hardware/README.md` tags; the cited A.4 stays (C6 holds) |
| A.U0.28 | B | M.SPEC.134 |
| A.U0.29 | IB | M.SPEC.020, M.SPEC.021, M.SPEC.113, M.SPEC.123, M.SPEC.149 |
| A.U0.30 | IB | M.SPEC.133 |
| A.U0.33 | IB | M.SPEC.010, M.SPEC.037, M.SPEC.042, M.SPEC.056, M.SPEC.065, M.SPEC.067, M.SPEC.088, M.SPEC.096, M.SPEC.102, M.SPEC.108, M.SPEC.121, M.SPEC.127, M.SPEC.132, M.SPEC.144, M.SPEC.145, M.SPEC.146, M.SPEC.149, M.SPEC.153, M.SPEC.154 |
| A.U0.34 | B | M.SPEC.042, M.SPEC.096 |
| A.U0.35 | B | dropped: code comments citing A.4; A.4 stays (C6 holds) |
| A.U0.36 | B | M.SPEC.021 |
| A.U0.37 | IB | M.SPEC.044, M.SPEC.061, M.SPEC.065, M.SPEC.067, M.SPEC.079, M.SPEC.084, M.SPEC.085, M.SPEC.094, M.SPEC.136 |
| A.U0.38 | EB | M.SPEC.005, M.SPEC.010, M.SPEC.014, M.SPEC.020, M.SPEC.023, M.SPEC.056, M.SPEC.059, M.SPEC.060, M.SPEC.083, M.SPEC.094, M.SPEC.128, M.SPEC.133, M.SPEC.153, M.SPEC.154 |
| A.U0.39 | IB | M.SPEC.009, M.SPEC.021, M.SPEC.022, M.SPEC.045, M.SPEC.052, M.SPEC.072, M.SPEC.091, M.SPEC.126, M.SPEC.148, M.SPEC.149, M.SPEC.154 |
| A.U0.40 | IB | M.SPEC.019, M.SPEC.047, M.SPEC.050, M.SPEC.057, M.SPEC.059, M.SPEC.079, M.SPEC.084, M.SPEC.089, M.SPEC.097, M.SPEC.098, M.SPEC.145 |
| A.U0.41 | IB | M.SPEC.010 |
| A.U0.42 | IB | M.SPEC.009 |
| A.U0.43 | IB | M.SPEC.129, M.SPEC.130 |
| A.U0.44 | IB | M.SPEC.037, M.SPEC.041, M.SPEC.072, M.SPEC.080, M.SPEC.082, M.SPEC.104, M.SPEC.108, M.SPEC.114, M.SPEC.121, M.SPEC.132, M.SPEC.139, M.SPEC.154 |
| A.U0.45 | B | M.SPEC.037 (Blast: the SPEC twin copy is A.U0.44 L36 at `:1037`, carried there); the CLAUDE.md edit is DOCS |
| A.U0.46 | B | M.SPEC.121 |
| A.U0.48 | B | M.SPEC.139 |
| A.U0.49 | B | M.SPEC.134 |
| A.U0.51 | B | M.SPEC.154 (Blast: SPEC `:6717-6722` is A.U0.44 L34, carried there); the comment edit is SRC |
| A.U0.52 | B | dropped: a `buildgen/validate.py` docstring; no SPEC text |
| A.U0.56 | IB | M.SPEC.105, M.SPEC.125 |
| A.U0.59 | B | M.SPEC.147 |
| A.U0.60 | IB | M.SPEC.043 |
| A.U1.02 | B | M.SPEC.088, M.SPEC.091, M.SPEC.133 (Blast: SPEC legacy paths via A.U1.17 and A.U1.18, carried there) |
| A.U1.03 | B | M.SPEC.035 |
| A.U1.04 | B | M.SPEC.049, M.SPEC.137 |
| A.U1.05 | B | M.SPEC.036, M.SPEC.037 |
| A.U1.06 | B | M.SPEC.065, M.SPEC.081 |
| A.U1.08 | B | M.SPEC.005, M.SPEC.137 |
| A.U1.09 | B | dropped: the L0 old-path test reads A.1, which M.SPEC.005 keeps; no SPEC text |
| A.U1.12 | B | dropped: CLAUDE.md only (DOCS) |
| A.U1.14 | IB | M.SPEC.005 |
| A.U1.15 | IB | M.SPEC.006, M.SPEC.007, M.SPEC.009, M.SPEC.014, M.SPEC.018 |
| A.U1.16 | IB | M.SPEC.032, M.SPEC.034, M.SPEC.035, M.SPEC.036, M.SPEC.037 |
| A.U1.17 | IB | M.SPEC.031, M.SPEC.088, M.SPEC.091, M.SPEC.099 |
| A.U1.18 | IB | M.SPEC.056, M.SPEC.111, M.SPEC.113, M.SPEC.132, M.SPEC.133, M.SPEC.134, M.SPEC.137 |
| A.U1.19 | B | M.SPEC.087, M.SPEC.099 |
| A.U1.21 | B | M.SPEC.034 (the legacy "28 findings" count; Resolved there: it goes) |
| A.U2.01 | B | M.SPEC.059, M.SPEC.147 |
| A.U2.02 | B | M.SPEC.059, M.SPEC.076 |
| A.U2.04 | B | M.SPEC.058 |
| A.U2.05 | B | M.SPEC.119, M.SPEC.120 |
| A.U2.06 | B | M.SPEC.058 |
| A.U2.07 | B | M.SPEC.055, M.SPEC.061, M.SPEC.145 |
| A.U2.08 | B | M.SPEC.058 |
| A.U2.09 | B | M.SPEC.010, M.SPEC.059, M.SPEC.101 |
| A.U2.14 | B | M.SPEC.058, M.SPEC.062 |
| A.U2.15 | B | M.SPEC.059, M.SPEC.060 |
| A.U2.18 | B | M.SPEC.056 |
| A.U2.19 | B | M.SPEC.059, M.SPEC.122 |
| A.U2.20 | B | M.SPEC.059, M.SPEC.060, M.SPEC.084, M.SPEC.133, M.SPEC.135, M.SPEC.136, M.SPEC.139 |
| A.U2.21 | B | M.SPEC.117, M.SPEC.119 |
| A.U2.22 | IB | M.SPEC.051, M.SPEC.058, M.SPEC.059, M.SPEC.069, M.SPEC.143 |
| A.U2.23 | EB | M.SPEC.008, M.SPEC.010, M.SPEC.101, M.SPEC.133, M.SPEC.135, M.SPEC.136, M.SPEC.139, M.SPEC.145 |
| A.U2.24 | IB | M.SPEC.147 |
| A.U3.02 | B | M.SPEC.135 |
| A.U3.03 | B | M.SPEC.051, M.SPEC.058 |
| A.U3.04 | B | M.SPEC.010, M.SPEC.101 |
| A.U3.05 | B | M.SPEC.054 |
| A.U3.06 | B | M.SPEC.020, M.SPEC.051 |
| A.U3.07 | B | M.SPEC.062 |
| A.U3.08 | B | M.SPEC.059, M.SPEC.084, M.SPEC.135, M.SPEC.136 |
| A.U3.09 | B | M.SPEC.059 |
| A.U3.10 | IB | M.SPEC.058, M.SPEC.059, M.SPEC.154 |
| A.U3.11 | B | M.SPEC.058 |
| A.U3.14 | B | M.SPEC.154 |
| A.U4.01 | B | M.SPEC.055, M.SPEC.110, M.SPEC.111 |
| A.U4.02 | B | M.SPEC.055 |
| A.U4.03 | B | M.SPEC.053, M.SPEC.055 |
| A.U4.04 | B | M.SPEC.011, M.SPEC.021, M.SPEC.053, M.SPEC.055 |
| A.U4.05 | B | M.SPEC.011 |
| A.U4.06 | B | M.SPEC.080 |
| A.U4.07 | B | M.SPEC.065, M.SPEC.083 |
| A.U4.08 | IB | M.SPEC.065 |
| A.U5.01 | B | M.SPEC.058, M.SPEC.111 |
| A.U5.02 | B | M.SPEC.020, M.SPEC.047 |
| A.U5.03 | B | M.SPEC.072, M.SPEC.111, M.SPEC.147, M.SPEC.149 |
| A.U5.04 | B | M.SPEC.018, M.SPEC.020, M.SPEC.021, M.SPEC.075, M.SPEC.111, M.SPEC.121, M.SPEC.127 |
| A.U5.05 | B | M.SPEC.121, M.SPEC.122, M.SPEC.127 |
| A.U5.06 | B | M.SPEC.014, M.SPEC.020, M.SPEC.051, M.SPEC.053, M.SPEC.070, M.SPEC.072 |
| A.U5.07 | B | M.SPEC.020, M.SPEC.072, M.SPEC.145, M.SPEC.146, M.SPEC.149 |
| A.U5.08 | EB | M.SPEC.020, M.SPEC.071, M.SPEC.147 |
| A.U5.09 | B | M.SPEC.047, M.SPEC.111 |
| A.U5.10 | B | M.SPEC.060 |
| A.U5.11 | B | M.SPEC.020, M.SPEC.072, M.SPEC.149 |
| A.U5.12 | B | M.SPEC.139 |
| A.U5.14 | B | M.SPEC.111 |
| A.U5.17 | B | M.SPEC.075 |
| A.U5.18 | B | M.SPEC.075, M.SPEC.124 |
| A.U6.01 | B | M.SPEC.118, M.SPEC.147 |
| A.U6.02 | B | M.SPEC.078, M.SPEC.114 |
| A.U6.03 | B | M.SPEC.022, M.SPEC.114, M.SPEC.121 |
| A.U6.04 | B | M.SPEC.022, M.SPEC.069, M.SPEC.114, M.SPEC.117, M.SPEC.142 |
| A.U6.05 | B | M.SPEC.078, M.SPEC.114, M.SPEC.124 |
| A.U6.06 | B | M.SPEC.071, M.SPEC.114, M.SPEC.142 |
| A.U6.07 | B | M.SPEC.114 |
| A.U6.08 | B | M.SPEC.124 |
| A.U6.09 | B | M.SPEC.124 |
| A.U6.10 | B | M.SPEC.076, M.SPEC.121 |
| A.U6.11 | B | M.SPEC.123 |
| A.U6.12 | B | M.SPEC.124 |
| A.U6.13 | B | dropped: `tests_js` fixtures; no SPEC text |
| A.U6.15 | B | M.SPEC.144 |
| A.U6.16 | B | M.SPEC.111, M.SPEC.114 |
| A.U6.17 | B | M.SPEC.116 |
| A.U6.18 | B | M.SPEC.116 |
| A.U6.19 | B | M.SPEC.117, M.SPEC.149 |
| A.U6.20 | B | M.SPEC.021 |
| A.U6.21 | B | M.SPEC.021, M.SPEC.092 |
| A.U6.22 | B | M.SPEC.102 |
| A.U6.23 | B | M.SPEC.021 |
| A.U6.24 | B | M.SPEC.150 |
| A.U6.25 | B | M.SPEC.119 |
| A.U6.26 | B | M.SPEC.058 |
| A.U6.27 | B | M.SPEC.021, M.SPEC.117, M.SPEC.119 |
| A.U6.28 | B | M.SPEC.062, M.SPEC.117 |
| A.U6.29 | B | M.SPEC.062, M.SPEC.117 |
| A.U6.30 | B | M.SPEC.062 |
| A.U7.01 | IB | M.SPEC.082 |
| A.U7.02 | IB | M.SPEC.003, M.SPEC.086 |
| A.U7.03 | B | M.SPEC.033, M.SPEC.078, M.SPEC.081, M.SPEC.086 |
| A.U7.04 | B | M.SPEC.079 |
| A.U7.05 | B | M.SPEC.129 |
| A.U7.06 | B | M.SPEC.079 |
| A.U7.07 | B | M.SPEC.077 |
| A.U7.08 | B | M.SPEC.076, M.SPEC.086 |
| A.U7.10 | B | M.SPEC.086, M.SPEC.124 |
| A.U7.13 | B | M.SPEC.086 |
| A.U7.14 | B | M.SPEC.082 |
| A.U7.18 | B | M.SPEC.082 |
| A.U7.20 | B | M.SPEC.076, M.SPEC.081 |
| A.U7.21 | B | M.SPEC.124, M.SPEC.129 |
| A.U7.23 | B | M.SPEC.129 |
| A.U7.24 | B | M.SPEC.082 |
| A.U7.25 | IB | M.SPEC.065, M.SPEC.082, M.SPEC.083 |
| A.U7.26 | B | M.SPEC.076 |
| A.U8.01 | IB | M.SPEC.001, M.SPEC.003, M.SPEC.155 |
| A.U8.02 | B | M.SPEC.088, M.SPEC.155 |
| A.U8.03 | B | M.SPEC.149, M.SPEC.155 |
| A.U8.04 | B | M.SPEC.116, M.SPEC.156 |
| A.U8.05 | B | M.SPEC.122, M.SPEC.156 |
| A.U8.06 | B | M.SPEC.108, M.SPEC.125, M.SPEC.135, M.SPEC.136, M.SPEC.156 |
| A.U8.07 | B | M.SPEC.151, M.SPEC.156 |
| A.U8.08 | B | M.SPEC.020, M.SPEC.088, M.SPEC.111, M.SPEC.156 |
| A.U8.09 | B | M.SPEC.060, M.SPEC.156 |
| A.U8.10 | B | M.SPEC.017, M.SPEC.156 |
| A.U8.11 | B | M.SPEC.108, M.SPEC.111, M.SPEC.156 |
| A.U8.12 | B | M.SPEC.015, M.SPEC.156 |
| A.U8.13 | B | M.SPEC.153, M.SPEC.154, M.SPEC.156 |
| A.U8.14 | B | M.SPEC.040, M.SPEC.041, M.SPEC.129, M.SPEC.156 |
| A.U8.15 | B | M.SPEC.034, M.SPEC.079, M.SPEC.156 |
| A.U8.16 | B | M.SPEC.076, M.SPEC.156 |
| A.U8.17 | B | M.SPEC.156 |
| A.U8.18 | B | M.SPEC.116, M.SPEC.121, M.SPEC.156 |
| A.U8.19 | EB | M.SPEC.097, M.SPEC.156 |
| A.U8.20 | B | M.SPEC.156 |
| A.U8.21 | B | M.SPEC.124, M.SPEC.156 |
| A.U8.22 | B | M.SPEC.156 |
| A.U8.23 | B | M.SPEC.005, M.SPEC.043, M.SPEC.156 |
| A.U8C.01 | B | M.SPEC.156 |
| A.U8C.02 | B | M.SPEC.156 |
| A.U8C.03 | B | M.SPEC.156 |
| A.U8C.04 | B | M.SPEC.122, M.SPEC.156 |
| A.U8C.05 | B | M.SPEC.156 |
| A.U8C.06 | B | M.SPEC.156 |
| A.U8C.07 | B | M.SPEC.156 |
| A.U8C.08 | B | M.SPEC.156 |
| A.U8C.09 | B | M.SPEC.156 |
| A.U8C.10 | B | M.SPEC.156 |
| A.U8C.11 | B | M.SPEC.156 |
| A.U8C.12 | B | M.SPEC.156 |
| A.U8C.13 | B | M.SPEC.156 |
| A.U8C.14 | B | M.SPEC.156 |
| A.U8C.15 | B | M.SPEC.156 |
| A.U8C.16 | B | M.SPEC.156 |
| A.U8C.17 | B | M.SPEC.156 |
| A.U8C.18 | B | M.SPEC.156 |
| A.U8C.19 | B | M.SPEC.156 |
| A.U8C.20 | B | M.SPEC.156 |
| A.U8C.21 | B | M.SPEC.156 |
| A.U8C.22 | B | M.SPEC.156 |
| A.U8C.23 | B | M.SPEC.156 |
| A.U8C.24 | B | M.SPEC.156 |
| A.U8C.25 | B | M.SPEC.156 |
| A.U8C.26 | B | M.SPEC.156 |
| A.U8C.27 | B | M.SPEC.156 |
| A.U8C.28 | B | M.SPEC.156 |
| A.U8C.29 | B | M.SPEC.156 |
| A.U8C.30 | B | M.SPEC.156 |
| A.U8C.31 | B | M.SPEC.156 |
| A.U8C.32 | B | M.SPEC.156 |
| A.U8C.33 | B | M.SPEC.156 |
| A.U8C.34 | B | M.SPEC.156 |
| A.U8C.35 | B | M.SPEC.156 |
| A.U8C.36 | B | M.SPEC.156 |
| A.U8C.37 | B | M.SPEC.156 |
| A.U8C.38 | B | M.SPEC.156 |
| A.U8C.39 | B | M.SPEC.156 |
| A.U8C.40 | B | M.SPEC.156 |
| A.U8C.41 | B | M.SPEC.156 |
| A.U8C.42 | B | M.SPEC.156 |
| A.U8C.43 | B | M.SPEC.137, M.SPEC.156 |
| A.U8C.44 | B | M.SPEC.156 |
| A.U8C.45 | B | M.SPEC.156 |
| A.U8C.46 | B | M.SPEC.156 |
| A.U8C.47 | B | M.SPEC.156 |
| A.U8C.48 | B | M.SPEC.156 |
| A.U8C.49 | B | M.SPEC.156 |
| A.U8C.50 | B | M.SPEC.156 |
| A.U8C.51 | B | M.SPEC.156 |
| A.U8C.52 | B | M.SPEC.156 |
| A.U8C.53 | B | M.SPEC.156 |
| A.U8C.54 | B | M.SPEC.156 |
| A.U8C.55 | B | M.SPEC.156 |
| A.U8C.56 | B | M.SPEC.156 |
| A.U8C.57 | B | M.SPEC.156 |
| A.U8C.58 | B | M.SPEC.156 |
| A.U8C.59 | B | M.SPEC.156 |
| A.U8C.60 | B | M.SPEC.156 |
| A.U8C.61 | B | M.SPEC.156 |
| A.U8C.62 | B | M.SPEC.156 |
| A.U8C.63 | B | M.SPEC.156 |
| A.U8C.64 | B | M.SPEC.156 |
| A.U8C.65 | B | M.SPEC.156 |
| A.U8C.66 | B | M.SPEC.156 |
| A.U8C.67 | B | M.SPEC.156 |
| A.U8C.68 | B | M.SPEC.156 |
| A.U8C.69 | B | M.SPEC.156 |
| A.U8C.70 | B | M.SPEC.156 |
| A.U8C.71 | B | M.SPEC.156 |
| A.U8C.72 | B | M.SPEC.156 |
| A.U8C.73 | B | M.SPEC.156 |
| A.U8C.74 | B | M.SPEC.156 |
| A.U8C.75 | B | M.SPEC.156 |
| A.U8C.76 | B | M.SPEC.156 |
| A.U8C.77 | B | M.SPEC.156 |
| A.U8C.78 | B | M.SPEC.156 |
| A.U8C.79 | B | M.SPEC.156 |
| A.U8C.80 | B | M.SPEC.156 |
| A.U8C.81 | B | M.SPEC.156 |
| A.U8C.82 | B | M.SPEC.156 |
| A.U8C.83 | B | M.SPEC.156 |
| A.U8C.84 | B | M.SPEC.156 |
| A.U8C.85 | B | M.SPEC.156 |
| A.U8C.86 | B | M.SPEC.156 |
| A.U8C.87 | B | M.SPEC.156 |
| A.U8C.88 | B | M.SPEC.156 |
| A.U8C.89 | B | M.SPEC.156 |
| A.U8C.90 | B | M.SPEC.156 |
| A.U8C.91 | B | M.SPEC.156 |
| A.U8C.92 | B | M.SPEC.156 |
| A.U8C.93 | B | M.SPEC.156 |
| A.U8C.94 | B | M.SPEC.156 |
| A.U8C.95 | B | M.SPEC.156 |
| A.U8C.96 | B | M.SPEC.156 |
| A.U8C.97 | B | M.SPEC.156 |
| A.U8C.98 | B | M.SPEC.156 |
| A.U8C.99 | B | M.SPEC.156 |
| A.U8C.100 | B | M.SPEC.156 |
| A.U8C.101 | B | M.SPEC.156 |
| A.U8C.102 | B | M.SPEC.156 |
| A.U8C.103 | B | M.SPEC.156 |
| A.U8C.104 | B | M.SPEC.156 |
| A.U8C.105 | B | M.SPEC.156 |
| A.U8C.106 | B | M.SPEC.156 |
| A.U8C.107 | B | M.SPEC.156 |
| A.U8C.108 | B | M.SPEC.156 |
| A.U8C.109 | B | M.SPEC.156 |
| A.U8C.110 | B | M.SPEC.156 |
| A.U8C.111 | B | M.SPEC.156 |
| A.U8C.112 | B | M.SPEC.156 |
| A.U8C.113 | B | M.SPEC.156 |
| A.U8C.114 | B | M.SPEC.156 |
| A.U8C.115 | B | M.SPEC.156 |
| A.U8C.116 | B | M.SPEC.156 |
| A.U8C.117 | B | M.SPEC.156 |
| A.U8C.118 | B | M.SPEC.156 |
| A.U8C.120 | EB | M.SPEC.156 |
| A.U8C.121 | EB | M.SPEC.156 |
| A.U8C2.01 | B | M.SPEC.156 |
| A.U8C2.02 | B | M.SPEC.156 |
| A.U8C2.03 | B | M.SPEC.156 |
| A.U8C2.04 | B | M.SPEC.156 |
| A.U8C2.05 | B | M.SPEC.156 |
| A.U8C2.06 | B | M.SPEC.156 |
| A.U8C2.07 | B | M.SPEC.156 |
| A.U8C2.08 | B | M.SPEC.079, M.SPEC.156 |
| A.U8C2.09 | B | M.SPEC.156 |
| A.U8C2.10 | B | M.SPEC.156 |
| A.U8C2.11 | B | M.SPEC.156 |
| A.U8C2.12 | B | M.SPEC.156 |
| A.U8C2.13 | B | M.SPEC.156 |
| A.U8C2.14 | B | M.SPEC.156 |
| A.U8C2.15 | B | M.SPEC.137, M.SPEC.156 |
| A.U8C2.16 | B | M.SPEC.156 |
| A.U8C2.17 | B | M.SPEC.156 |
| A.U8C2.18 | B | M.SPEC.156 |
| A.U8C2.19 | B | M.SPEC.156 |
| A.U8C2.20 | B | M.SPEC.156 |
| A.U8C2.21 | B | M.SPEC.156 |
| A.U8C2.22 | B | M.SPEC.156 |
| A.U8C2.23 | B | M.SPEC.156 |
| A.U8C2.24 | B | M.SPEC.156 |
| A.U8C2.25 | B | M.SPEC.156 |
| A.U8C2.26 | B | M.SPEC.156 |
| A.U8C2.27 | B | M.SPEC.156 |
| A.U8C2.28 | B | M.SPEC.156 |
| A.U8C2.29 | B | M.SPEC.156 |
| A.U8C2.30 | B | M.SPEC.156 |
| A.U8C2.31 | B | M.SPEC.156 |
| A.U8C2.32 | B | M.SPEC.156 |
| A.U8C2.33 | B | M.SPEC.156 |
| A.U8C2.34 | B | M.SPEC.156 |
| A.U8C2.35 | B | M.SPEC.156 |
| A.U8C2.36 | B | M.SPEC.156 |
| A.U8C2.37 | B | M.SPEC.156 |
| A.U8C2.38 | B | M.SPEC.156 |
| A.U8C2.39 | B | M.SPEC.108, M.SPEC.156 |
| A.U8C2.40 | B | M.SPEC.156 |
| A.U8C2.41 | B | M.SPEC.156 |
| A.U8C2.42 | B | M.SPEC.108, M.SPEC.156 |
| A.U8C2.43 | B | M.SPEC.156 |
| A.U8C2.44 | B | M.SPEC.156 |
| A.U8C2.45 | B | M.SPEC.156 |
| A.U8C2.46 | B | M.SPEC.156 |
| A.U8C2.47 | B | M.SPEC.156 |
| A.U8C2.48 | B | M.SPEC.156 |
| A.U8C2.49 | B | M.SPEC.156 |
| A.U8C2.51 | EB | M.SPEC.156 |
| A.U9.01 | B | M.SPEC.014, M.SPEC.016 |
| A.U9.02 | B | M.SPEC.014 |
| A.U9.03 | B | M.SPEC.021, M.SPEC.119 |
| A.U9.04 | B | M.SPEC.097, M.SPEC.146, M.SPEC.156 |
| A.U9.05 | B | M.SPEC.014 |
| A.U9.06 | B | M.SPEC.014 |
| A.U9.08 | B | M.SPEC.059 |
| A.U9.09 | B | M.SPEC.014 |
| A.U9.10 | B | M.SPEC.071 |
| A.U9.11 | IB | M.SPEC.014 |
| A.U10.01 | B | M.SPEC.111 |
| A.U10.02 | B | M.SPEC.066, M.SPEC.111 |
| A.U10.03 | B | M.SPEC.066 |
| A.U10.05 | B | M.SPEC.111 |
| A.U10.06 | B | M.SPEC.052, M.SPEC.092, M.SPEC.111 |
| A.U10.07 | EB | M.SPEC.020, M.SPEC.156 |
| A.U10.08 | B | M.SPEC.020, M.SPEC.111, M.SPEC.156 |
| A.U10.09 | IB | M.SPEC.006 |
| A.U10.10 | B | M.SPEC.020, M.SPEC.058 |
| A.U10.11 | B | M.SPEC.058 |
| A.U10.12 | B | M.SPEC.020, M.SPEC.067 |
| A.U10.13 | B | M.SPEC.067 |
| A.U10.14 | IB | M.SPEC.066, M.SPEC.067, M.SPEC.090 |
| A.U10.16 | EB | M.SPEC.064 |
| A.U10.17 | EB | M.SPEC.064 |
| A.U10.18 | B | M.SPEC.008, M.SPEC.020, M.SPEC.064 |
| A.U10.19 | EB | M.SPEC.066, M.SPEC.072 |
| A.U10.21 | B | M.SPEC.047, M.SPEC.070 |
| A.U10.22 | B | M.SPEC.058, M.SPEC.070 |
| A.U10.24 | IB | M.SPEC.016 |
| A.U10.25 | B | M.SPEC.055 |
| A.U10.26 | EB | M.SPEC.094, M.SPEC.156 |
| A.U10.27 | B | M.SPEC.091, M.SPEC.111 |
| A.U10.28 | B | M.SPEC.066 |
| A.U10.29 | B | M.SPEC.046, M.SPEC.054, M.SPEC.089 |
| A.U10.30 | B | M.SPEC.089, M.SPEC.145 |
| A.U10.31 | IB | M.SPEC.075 |
| A.U10.32 | IB | M.SPEC.075 |
| A.U10.34 | B | M.SPEC.075 |
| A.U10.35 | B | M.SPEC.008, M.SPEC.047 |
| A.U10.36 | B | M.SPEC.057 |
| A.U10.37 | B | M.SPEC.006, M.SPEC.008, M.SPEC.009, M.SPEC.024, M.SPEC.046 |
| A.U10.38 | B | M.SPEC.006, M.SPEC.008, M.SPEC.009, M.SPEC.010, M.SPEC.014, M.SPEC.018, M.SPEC.023, M.SPEC.047, M.SPEC.053, M.SPEC.070, M.SPEC.071, M.SPEC.072, M.SPEC.080 |
| A.U10.39 | B | M.SPEC.008, M.SPEC.047, M.SPEC.054 |
| A.U10.40 | B | M.SPEC.008, M.SPEC.021, M.SPEC.024, M.SPEC.055, M.SPEC.056, M.SPEC.117, M.SPEC.120 |
| A.U10.41 | IB | M.SPEC.008, M.SPEC.127, M.SPEC.132 |
| A.U10.42 | IB | M.SPEC.056, M.SPEC.113, M.SPEC.115 |
| A.U10.43 | B | M.SPEC.008, M.SPEC.067, M.SPEC.146 |
| A.U10.44 | B | M.SPEC.008, M.SPEC.020, M.SPEC.051, M.SPEC.066 |
| A.U10.45 | B | M.SPEC.048, M.SPEC.066, M.SPEC.075, M.SPEC.090, M.SPEC.125, M.SPEC.128 |
| A.U10.46 | B | M.SPEC.068 |
| A.U10.47 | B | M.SPEC.002 |
| A.U10.R01 | B | M.SPEC.051, M.SPEC.058, M.SPEC.095, M.SPEC.111, M.SPEC.139, M.SPEC.156 |
| A.U11.01 | B | M.SPEC.021 |
| A.U11.02 | B | M.SPEC.021 |
| A.U11.03 | B | M.SPEC.010, M.SPEC.128 |
| A.U11.04 | B | M.SPEC.096 |
| A.U11.05 | B | M.SPEC.020, M.SPEC.021, M.SPEC.103 |
| A.U11.06 | B | M.SPEC.020, M.SPEC.021, M.SPEC.103 |
| A.U11.08 | B | M.SPEC.021, M.SPEC.102 |
| A.U11.09 | B | M.SPEC.075, M.SPEC.091 |
| A.U11.10 | IB | M.SPEC.020, M.SPEC.130 |
| A.U11.11 | IB | M.SPEC.020 |
| A.U11.12 | B | M.SPEC.020, M.SPEC.074 |
| A.U11.13 | B | M.SPEC.058 |
| A.U11.14 | IB | M.SPEC.020 |
| A.U11.15 | B | M.SPEC.058 |
| A.U11.16 | B | M.SPEC.058 |
| A.U11.17 | B | M.SPEC.054, M.SPEC.074 |
| A.U11.18 | B | M.SPEC.021 |
| A.U11.19 | B | M.SPEC.055, M.SPEC.061 |
| A.U11.20 | B | M.SPEC.061 |
| A.U11.21 | B | M.SPEC.054, M.SPEC.061, M.SPEC.116 |
| A.U11.24 | B | M.SPEC.055 |
| A.U11.25 | B | M.SPEC.055 |
| A.U11.26 | B | M.SPEC.018, M.SPEC.056 |
| A.U11.27 | B | M.SPEC.055, M.SPEC.064 |
| A.U11.28 | B | M.SPEC.055, M.SPEC.061 |
| A.U11.29 | B | M.SPEC.021, M.SPEC.054 |
| A.U11.31 | B | M.SPEC.021, M.SPEC.058, M.SPEC.110, M.SPEC.116, M.SPEC.120 |
| A.U11.32 | B | M.SPEC.071 |
| A.U11.33 | B | M.SPEC.054 |
| A.U11.35 | IB | M.SPEC.057, M.SPEC.139 |
| A.U11.37 | IB | M.SPEC.051, M.SPEC.058 |
| A.U11.39 | B | M.SPEC.067 |
| A.U11.S01 | B | M.SPEC.052, M.SPEC.068 |
| A.U11.S02 | B | M.SPEC.068 |
| A.U11.S03 | B | M.SPEC.068 |
| A.U12.01 | B | M.SPEC.111, M.SPEC.126 |
| A.U12.03 | B | M.SPEC.050, M.SPEC.134 |
| A.U12.05 | IB | M.SPEC.134 |
| A.U12.06 | B | M.SPEC.074, M.SPEC.111 |
| A.U12.07 | B | M.SPEC.154 |
| A.U12.08 | B | M.SPEC.074 |
| A.U12.10 | IB | M.SPEC.111 |
| A.U12.11 | B | M.SPEC.098 |
| A.U12.12 | B | M.SPEC.098 |
| A.U12.13 | B | M.SPEC.098 |
| A.U12.14 | B | M.SPEC.020, M.SPEC.091 |
| A.U12.15 | IB | M.SPEC.098 |
| A.U12.17 | B | M.SPEC.111 |
| A.U12.18 | B | M.SPEC.064, M.SPEC.111 |
| A.U13.01 | IB | M.SPEC.048, M.SPEC.111, M.SPEC.126 |
| A.U13.02 | EB | M.SPEC.126 |
| A.U13.05 | IB | M.SPEC.049 |
| A.U13.06 | IB | M.SPEC.111 |
| A.U13.07 | B | M.SPEC.048, M.SPEC.074 |
| A.U13.08 | B | M.SPEC.048 |
| A.U13.09 | B | M.SPEC.048 |
| A.U13.10 | B | M.SPEC.048, M.SPEC.111 |
| A.U13.11 | IB | M.SPEC.111 |
| A.U13.12 | B | M.SPEC.108 |
| A.U13.13 | B | M.SPEC.108 |
| A.U13.16 | B | M.SPEC.058, M.SPEC.070, M.SPEC.100 |
| A.U13.17 | B | M.SPEC.108, M.SPEC.136 |
| A.U13.18 | B | M.SPEC.050, M.SPEC.108 |
| A.U13.19 | B | M.SPEC.108 |
| A.U13.R01 | B | M.SPEC.048, M.SPEC.095, M.SPEC.097, M.SPEC.100, M.SPEC.111, M.SPEC.156 |
| A.U13.R02 | B | M.SPEC.065 |
| A.U14.01 | IB | M.SPEC.020, M.SPEC.103 |
| A.U14.02 | B | dropped: `tests_hardware/README.md` cites F.5.4, which stays (C6 holds) |
| A.U14.03 | IB | M.SPEC.122 |
| A.U14.04 | IB | M.SPEC.100 |
| A.U14.05 | IB | M.SPEC.107, M.SPEC.129 |
| A.U14.06 | IB | M.SPEC.074 |
| A.U14.07 | IB | M.SPEC.125 |
| A.U14.08 | IB | M.SPEC.125 |
| A.U14.09 | IB | M.SPEC.088 |
| A.U14.10 | IB | M.SPEC.089, M.SPEC.091 |
| A.U14.11 | IB | M.SPEC.091 |
| A.U14.12 | IB | M.SPEC.090, M.SPEC.121 |
| A.U14.13 | IB | M.SPEC.125 |
| A.U14.14 | IB | M.SPEC.048, M.SPEC.050, M.SPEC.070, M.SPEC.090 |
| A.U14.15 | IB | M.SPEC.093 |
| A.U14.16 | IB | M.SPEC.094, M.SPEC.105 |
| A.U14.17 | IB | M.SPEC.095 |
| A.U14.18 | IB | M.SPEC.093 |
| A.U14.19 | B | M.SPEC.058, M.SPEC.093 |
| A.U14.20 | IB | M.SPEC.103 |
| A.U14.21 | IB | M.SPEC.101 |
| A.U14.22 | IB | M.SPEC.105 |
| A.U14.23 | B | M.SPEC.031, M.SPEC.087, M.SPEC.099 |
| A.U14.24 | IB | M.SPEC.025, M.SPEC.088 |
| A.U14.25 | IB | M.SPEC.092 |
| A.U14.26 | B | M.SPEC.092 |
| A.U14.27 | IB | M.SPEC.089, M.SPEC.091, M.SPEC.105 |
| A.U14.28 | IB | M.SPEC.003, M.SPEC.078, M.SPEC.105, M.SPEC.107 |
| A.U14.30 | IB | M.SPEC.041, M.SPEC.121 |
| A.U14.31 | IB | M.SPEC.108 |
| A.U14.32 | IB | M.SPEC.092, M.SPEC.107 |
| A.U14.33 | B | M.SPEC.092 |
| A.U14.35 | IB | M.SPEC.102 |
| A.U14.36 | IB | M.SPEC.104 |
| A.U14.37 | IB | M.SPEC.062 |
| A.U14.38 | IB | M.SPEC.095 |
| A.U14.R01 | IB | M.SPEC.094, M.SPEC.095, M.SPEC.096, M.SPEC.108, M.SPEC.135 |
| A.U15.01 | B | M.SPEC.048, M.SPEC.151 |
| A.U15.02 | IB | M.SPEC.044, M.SPEC.052, M.SPEC.068 |
| A.U15.03 | B | M.SPEC.067 |
| A.U15.04 | IB | M.SPEC.011 |
| A.U15.05 | IB | M.SPEC.003, M.SPEC.151 |
| A.U15.06 | IB | M.SPEC.011, M.SPEC.151 |
| A.U15.09 | B | M.SPEC.111 |
| A.U15.10 | B | M.SPEC.149 |
| A.U15.12 | B | M.SPEC.020, M.SPEC.053, M.SPEC.119, M.SPEC.151 |
| A.U15.13 | B | M.SPEC.151 |
| A.U15.14 | B | M.SPEC.151 |
| A.U15.15 | IB | M.SPEC.065 |
| A.U15.16 | IB | M.SPEC.149 |
| A.U15.17 | IB | M.SPEC.054, M.SPEC.118 |
| A.U15.18 | B | M.SPEC.021 |
| A.U15.19 | B | M.SPEC.012, M.SPEC.151 |
| A.U15.20 | B | M.SPEC.151 |
| A.U15.21 | B | M.SPEC.081 |
| A.U15.22 | IB | M.SPEC.052 |
| A.U15.23 | B | M.SPEC.151 |
| A.U15.24 | B | M.SPEC.059, M.SPEC.151 |
| A.U15.25 | B | M.SPEC.019, M.SPEC.151 |
| A.U15.26 | B | M.SPEC.151 |
| A.U15.27 | B | dropped: its Blast states no SPEC mention (grep `get_altitude`) |
| A.U15.28 | B | M.SPEC.141 |
| A.U15.30 | IB | M.SPEC.154 |
| A.U15.31 | B | M.SPEC.154 |
| A.U15.32 | B | M.SPEC.154 |
| A.U15.33 | B | M.SPEC.154 |
| A.U15.34 | IB | M.SPEC.154 |
| A.U15.35 | B | M.SPEC.092, M.SPEC.154 |
| A.U15.36 | B | M.SPEC.154 |
| A.U15.38 | B | M.SPEC.081 |
| A.U15.39 | IB | M.SPEC.019, M.SPEC.153, M.SPEC.154 |
| A.U15.40 | IB | M.SPEC.046, M.SPEC.047, M.SPEC.051, M.SPEC.071, M.SPEC.111 |
| A.U15.41 | B | M.SPEC.066 |
| A.U15.42 | IB | M.SPEC.054 |
| A.U15.43 | B | M.SPEC.051, M.SPEC.068 |
| A.U15.R01 | B | M.SPEC.011, M.SPEC.095 |
| A.U15.R02 | B | M.SPEC.012, M.SPEC.065, M.SPEC.095 |
| A.U15.R03 | B | M.SPEC.013, M.SPEC.095 |
| A.U15.R04 | B | M.SPEC.095, M.SPEC.154 |
| A.U15.S01 | B | M.SPEC.064 |
| A.U16.01 | IB | M.SPEC.020, M.SPEC.058, M.SPEC.142 |
| A.U16.02 | B | M.SPEC.010 |
| A.U16.03 | B | M.SPEC.010 |
| A.U16.04 | IB | M.SPEC.049 |
| A.U16.05 | IB | M.SPEC.080, M.SPEC.081 |
| A.U16.06 | B | M.SPEC.010, M.SPEC.058 |
| A.U16.07 | B | M.SPEC.097, M.SPEC.108, M.SPEC.136 |
| A.U16.08 | IB | M.SPEC.010 |
| A.U16.09 | B | M.SPEC.010 |
| A.U16.10 | B | M.SPEC.064 |
| A.U16.11 | EB | M.SPEC.010 |
| A.U16.12 | IB | M.SPEC.010 |
| A.U16.13 | B | M.SPEC.064 |
| A.U16.14 | B | M.SPEC.101 |
| A.U16.15 | B | M.SPEC.049, M.SPEC.059 |
| A.U16.16 | IB | M.SPEC.048 |
| A.U16.17 | B | M.SPEC.010, M.SPEC.020, M.SPEC.058 |
| A.U16.18 | IB | M.SPEC.010 |
| A.U16.19 | IB | M.SPEC.010 |
| A.U16.20 | B | M.SPEC.049, M.SPEC.149 |
| A.U16.23 | B | M.SPEC.081, M.SPEC.111 |
| A.U16.R01 | B | M.SPEC.049, M.SPEC.095 |
| A.U16.R02 | B | M.SPEC.010, M.SPEC.049, M.SPEC.095 |
| A.U16.R03 | B | M.SPEC.010, M.SPEC.020, M.SPEC.059, M.SPEC.095 |
| A.U17.01 | B | M.SPEC.139 |
| A.U17.03 | IB | M.SPEC.138 |
| A.U17.04 | B | M.SPEC.081 |
| A.U17.06 | B | M.SPEC.135 |
| A.U17.07 | B | M.SPEC.060 |
| A.U17.08 | B | M.SPEC.133 |
| A.U17.11 | B | M.SPEC.133 |
| A.U17.12 | EB | dropped [extra]: an audit working file (traceability table); no SPEC text |
| A.U17.13 | B | M.SPEC.050 |
| A.U17.14 | B | M.SPEC.156 (the threshold literal's Part N row) |
| A.U17.15 | IB | M.SPEC.136 |
| A.U17.16 | B | M.SPEC.134 |
| A.U17.17 | B | M.SPEC.135 |
| A.U17.18 | B | M.SPEC.085 |
| A.U17.19 | B | M.SPEC.075 |
| A.U17.20 | B | M.SPEC.136 |
| A.U17.21 | B | M.SPEC.060, M.SPEC.136, M.SPEC.147 |
| A.U17.22 | B | M.SPEC.111, M.SPEC.134 |
| A.U17.23 | B | M.SPEC.135 |
| A.U17.25 | B | M.SPEC.137 |
| A.U17.28 | B | M.SPEC.050 |
| A.U17.32 | B | M.SPEC.060, M.SPEC.136, M.SPEC.147 |
| A.U17.33 | IB | M.SPEC.135 |
| A.U18.01 | B | M.SPEC.018, M.SPEC.063 |
| A.U18.02 | B | M.SPEC.063, M.SPEC.126 |
| A.U18.03 | B | M.SPEC.126 |
| A.U18.05 | B | M.SPEC.108, M.SPEC.111 |
| A.U18.06 | B | M.SPEC.059 |
| A.U18.07 | B | M.SPEC.064 |
| A.U18.08 | B | M.SPEC.110, M.SPEC.111 |
| A.U18.09 | B | M.SPEC.058 |
| A.U18.10 | B | M.SPEC.021, M.SPEC.060, M.SPEC.064 |
| A.U18.13 | B | M.SPEC.111 |
| A.U18.14 | B | M.SPEC.059, M.SPEC.060 |
| A.U18.15 | B | M.SPEC.058 |
| A.U18.16 | B | M.SPEC.126 |
| A.U18.17 | EB | M.SPEC.081 |
| A.U18.18 | IB | M.SPEC.040 |
| A.U18.19 | EB | M.SPEC.060 |
| A.U18.20 | B | M.SPEC.060 |
| A.U18.21 | B | M.SPEC.060 |
| A.U18.22 | B | M.SPEC.066 |
| A.U18.23 | B | M.SPEC.066 |
| A.U18.24 | B | M.SPEC.066 |
| A.U18.26 | B | M.SPEC.066 |
| A.U18.27 | B | M.SPEC.158 |
| A.U18.28 | B | M.SPEC.017, M.SPEC.096 |
| A.U18.29 | EB | M.SPEC.016 |
| A.U18.30 | B | M.SPEC.017 |
| A.U18.31 | B | M.SPEC.064 |
| A.U18.32 | B | M.SPEC.064 |
| A.U18.33 | B | M.SPEC.021, M.SPEC.064 |
| A.U18.34 | IB | M.SPEC.064 |
| A.U18.36 | EB | M.SPEC.058, M.SPEC.059, M.SPEC.158 |
| A.U18.37 | B | M.SPEC.024, M.SPEC.053, M.SPEC.062 |
| A.U18.38 | B | M.SPEC.021, M.SPEC.062, M.SPEC.110, M.SPEC.116 |
| A.U18.39 | B | M.SPEC.051 |
| A.U18.40 | B | M.SPEC.047, M.SPEC.111 |
| A.U18.41 | B | M.SPEC.081 |
| A.U18.43 | B | M.SPEC.018, M.SPEC.075, M.SPEC.104 |
| A.U18.47 | IB | M.SPEC.060 |
| A.U18.R01 | B | M.SPEC.017, M.SPEC.095 |
| A.U19.01 | B | M.SPEC.021, M.SPEC.110, M.SPEC.116, M.SPEC.120 |
| A.U19.02 | B | M.SPEC.021, M.SPEC.119 |
| A.U19.05 | B | M.SPEC.018, M.SPEC.022, M.SPEC.127 |
| A.U19.06 | B | M.SPEC.022 |
| A.U19.07 | B | M.SPEC.018, M.SPEC.093, M.SPEC.132 |
| A.U19.08 | B | M.SPEC.018, M.SPEC.121 |
| A.U19.09 | B | M.SPEC.018 |
| A.U19.10 | B | M.SPEC.021, M.SPEC.113 |
| A.U19.11 | B | M.SPEC.111, M.SPEC.127 |
| A.U19.12 | B | M.SPEC.021 |
| A.U19.13 | EB | M.SPEC.121, M.SPEC.132, M.SPEC.156, M.SPEC.157 |
| A.U19.14 | B | M.SPEC.058, M.SPEC.116 |
| A.U19.15 | B | M.SPEC.021, M.SPEC.056 |
| A.U19.16 | B | M.SPEC.110, M.SPEC.111, M.SPEC.120 |
| A.U19.17 | B | M.SPEC.068 |
| A.U19.19 | EB | M.SPEC.018 |
| A.U19.20 | B | M.SPEC.021, M.SPEC.147 |
| A.U19.21 | B | dropped: a test docstring tag citing past SPEC text; no SPEC text |
| A.U19.22 | B | M.SPEC.107 |
| A.U19.23 | B | M.SPEC.018 |
| A.U19.24 | B | M.SPEC.018 |
| A.U20.01 | B | M.SPEC.148, M.SPEC.149 |
| A.U20.02 | B | M.SPEC.010, M.SPEC.020, M.SPEC.147 |
| A.U20.03 | B | M.SPEC.020, M.SPEC.089 |
| A.U20.04 | B | M.SPEC.020, M.SPEC.129 |
| A.U20.05 | B | M.SPEC.020, M.SPEC.130, M.SPEC.147 |
| A.U20.06 | B | M.SPEC.015, M.SPEC.018, M.SPEC.020, M.SPEC.128, M.SPEC.130 |
| A.U20.07 | B | M.SPEC.020 |
| A.U20.08 | B | M.SPEC.020, M.SPEC.095 |
| A.U20.09 | B | M.SPEC.019, M.SPEC.149 |
| A.U20.10 | B | M.SPEC.049 |
| A.U20.12 | B | M.SPEC.054 |
| A.U20.13 | B | M.SPEC.145 |
| A.U20.14 | B | M.SPEC.043, M.SPEC.148 |
| A.U20.15 | B | M.SPEC.020, M.SPEC.035 |
| A.U20.16 | B | M.SPEC.119, M.SPEC.145 |
| A.U20.17 | B | M.SPEC.148, M.SPEC.149 |
| A.U20.18 | B | M.SPEC.108, M.SPEC.141, M.SPEC.149 |
| A.U20.19 | B | M.SPEC.146, M.SPEC.148 |
| A.U20.20 | B | M.SPEC.149 |
| A.U20.21 | B | M.SPEC.149 |
| A.U20.22 | B | M.SPEC.145 |
| A.U20.23 | IB | M.SPEC.145 |
| A.U20.24 | B | M.SPEC.148, M.SPEC.149 |
| A.U20.25 | B | M.SPEC.118, M.SPEC.149 |
| A.U20.27 | B | M.SPEC.111, M.SPEC.141, M.SPEC.144 |
| A.U20.28 | B | M.SPEC.147 |
| A.U20.29 | EB | M.SPEC.146 |
| A.U20.30 | B | M.SPEC.118, M.SPEC.147 |
| A.U20.31 | B | M.SPEC.150 |
| A.U20.32 | B | M.SPEC.147 |
| A.U20.33 | B | M.SPEC.148 |
| A.U20.34 | B | M.SPEC.146, M.SPEC.149 |
| A.U20.35 | IB | M.SPEC.146 |
| A.U20.36 | B | M.SPEC.147, M.SPEC.150 |
| A.U20.37 | IB | M.SPEC.148 |
| A.U20.38 | B | M.SPEC.021, M.SPEC.119 |
| A.U20.39 | B | M.SPEC.148 |
| A.U20.40 | EB | dropped [extra]: a `buildgen/twin_wiring.py` comment citing L.4, which stays (C6 holds) |
| A.U20.41 | B | dropped: its SPEC text is A.U10.37/A.U10.38's, carried by M.SPEC.006/.008/.009 and the rest of their list |
| A.U20.42 | B | M.SPEC.145 |
| A.U21.01 | B | M.SPEC.027 |
| A.U21.02 | B | M.SPEC.026, M.SPEC.027, M.SPEC.035, M.SPEC.038 |
| A.U21.03 | B | M.SPEC.027, M.SPEC.029 |
| A.U21.04 | B | M.SPEC.043 |
| A.U21.05 | IB | M.SPEC.025, M.SPEC.088 |
| A.U21.06 | B | M.SPEC.030, M.SPEC.038, M.SPEC.039, M.SPEC.106 |
| A.U21.07 | B | M.SPEC.033 |
| A.U21.08 | B | M.SPEC.026, M.SPEC.038 |
| A.U21.09 | B | M.SPEC.030, M.SPEC.038, M.SPEC.041, M.SPEC.042, M.SPEC.109 |
| A.U21.12 | B | M.SPEC.026, M.SPEC.029, M.SPEC.030, M.SPEC.042, M.SPEC.076, M.SPEC.081, M.SPEC.107 |
| A.U21.13 | B | M.SPEC.042, M.SPEC.076, M.SPEC.107 |
| A.U21.14 | B | M.SPEC.041, M.SPEC.042 |
| A.U21.15 | B | M.SPEC.030, M.SPEC.031, M.SPEC.038 |
| A.U21.16 | IB | M.SPEC.031, M.SPEC.038, M.SPEC.045 |
| A.U21.17 | B | M.SPEC.028 |
| A.U21.18 | B | M.SPEC.028, M.SPEC.034 |
| A.U21.19 | B | M.SPEC.036 |
| A.U21.22 | B | M.SPEC.029, M.SPEC.035, M.SPEC.076 |
| A.U21.23 | B | M.SPEC.037 |
| A.U21.24 | B | M.SPEC.036 |
| A.U21.27 | B | M.SPEC.029 |
| A.U21.28 | B | M.SPEC.036 |
| A.U21.29 | B | M.SPEC.027 |
| A.U21.30 | B | M.SPEC.029 |
| A.U21.31 | B | dropped: its Blast finds no SPEC change (`fielded` only at the NTP_Host bound, A.U10.41 → M.SPEC.127) |
| A.U22.01 | EB | M.SPEC.014 |
| A.U22.02 | B | M.SPEC.071 |
| A.U22.03 | B | M.SPEC.014 |
| A.U23.01 | B | M.SPEC.116 |
| A.U23.02 | B | M.SPEC.116 |
| A.U23.03 | B | M.SPEC.116 |
| A.U23.04 | B | M.SPEC.116 |
| A.U23.05 | B | M.SPEC.116, M.SPEC.124, M.SPEC.156 |
| A.U23.06 | B | M.SPEC.116, M.SPEC.121, M.SPEC.156 |
| A.U23.07 | B | M.SPEC.114 |
| A.U23.08 | B | M.SPEC.115 |
| A.U23.09 | B | M.SPEC.117 |
| A.U23.10 | B | M.SPEC.116, M.SPEC.124 |
| A.U23.11 | B | M.SPEC.119 |
| A.U23.12 | B | M.SPEC.119 |
| A.U23.13 | B | M.SPEC.119, M.SPEC.120 |
| A.U23.14 | B | M.SPEC.116 |
| A.U23.15 | B | M.SPEC.115, M.SPEC.116 |
| A.U23.16 | B | M.SPEC.117 |
| A.U23.17 | B | M.SPEC.116 |
| A.U23.18 | B | M.SPEC.117 |
| A.U23.19 | B | M.SPEC.119, M.SPEC.120 |
| A.U23.20 | B | M.SPEC.119 |
| A.U23.21 | B | M.SPEC.116 |
| A.U23.22 | B | M.SPEC.021 |
| A.U23.23 | B | M.SPEC.116 (Blast: the H.4 legacy-divergence record is A.U23.45's, carried there) |
| A.U23.25 | B | M.SPEC.111, M.SPEC.114, M.SPEC.120 |
| A.U23.26 | B | M.SPEC.116, M.SPEC.124 |
| A.U23.28 | B | M.SPEC.116, M.SPEC.120 |
| A.U23.29 | B | M.SPEC.116 |
| A.U23.31 | B | M.SPEC.124 |
| A.U23.32 | B | M.SPEC.121 |
| A.U23.33 | B | M.SPEC.121 |
| A.U23.34 | B | M.SPEC.121, M.SPEC.123 |
| A.U23.35 | B | M.SPEC.121 |
| A.U23.37 | B | M.SPEC.114 |
| A.U23.38 | B | M.SPEC.022, M.SPEC.114 |
| A.U23.39 | B | M.SPEC.116 (Blast: the H.4 legacy-divergence record is A.U23.45's, carried there) |
| A.U23.40 | B | M.SPEC.115, M.SPEC.116 |
| A.U23.41 | B | M.SPEC.115 |
| A.U23.42 | B | M.SPEC.115 |
| A.U23.43 | B | M.SPEC.113 |
| A.U23.44 | B | M.SPEC.113 |
| A.U23.45 | IB | M.SPEC.116 |
| A.U23.49 | B | M.SPEC.021, M.SPEC.116 |
| A.U24.01 | B | M.SPEC.134 |
| A.U24.02 | B | M.SPEC.160 |
| A.U24.03 | B | M.SPEC.077 |
| A.U24.04 | B | M.SPEC.077 |
| A.U24.05 | B | M.SPEC.078, M.SPEC.081 |
| A.U24.07 | B | M.SPEC.077 |
| A.U24.08 | B | M.SPEC.077 |
| A.U24.10 | B | M.SPEC.076 |
| A.U24.11 | B | M.SPEC.076 |
| A.U24.14 | B | M.SPEC.124 |
| A.U24.15 | B | M.SPEC.107, M.SPEC.137 |
| A.U24.16 | B | M.SPEC.140 |
| A.U24.17 | B | M.SPEC.080 |
| A.U24.18 | B | M.SPEC.080 |
| A.U24.21 | B | M.SPEC.070 |
| A.U24.26 | B | M.SPEC.080, M.SPEC.100 |
| A.U24.27 | B | M.SPEC.065 |
| A.U24.34 | B | M.SPEC.121 |
| A.U24.37 | B | dropped: a test scenario change; no SPEC text |
| A.U24.42 | B | M.SPEC.081 |
| A.U24.46 | B | M.SPEC.078 |
| A.U24.48 | B | M.SPEC.124 |
| A.U24.49 | IB | M.SPEC.110 |
| A.U24.52 | B | M.SPEC.121 |
| A.U24.55 | B | M.SPEC.148 |
| A.U24.58 | B | M.SPEC.091 |
| A.U24.59 | B | M.SPEC.078 |
| A.U24.60 | B | M.SPEC.160 |
| A.U24.62 | B | M.SPEC.111 |
| A.U24.64 | B | M.SPEC.084 |
| A.U24.65 | B | M.SPEC.020, M.SPEC.077, M.SPEC.079 |
| A.U24.66 | B | M.SPEC.065, M.SPEC.144 |
| A.U24.67 | B | dropped: SPEC J quotes no banner (grep `dev-uart-crossover`, `banner`: none in J); no SPEC text |
| A.U24.69 | B | M.SPEC.022, M.SPEC.076 |
| A.U24.70 | IB | M.SPEC.076 |
| A.U24.72 | IB | M.SPEC.081 |
| A.U24.75 | EB | M.SPEC.077 |
| A.U24.76 | B | M.SPEC.077 |
| A.U24.78 | B | M.SPEC.080 |
| A.U24.79 | B | M.SPEC.111 |
| A.U25.01 | B | M.SPEC.023, M.SPEC.082, M.SPEC.107 |
| A.U25.12 | B | M.SPEC.116 |
| A.U25.17 | B | M.SPEC.070 |
| A.U25.19 | B | M.SPEC.090 |
| A.U25.23 | B | M.SPEC.111 |
| A.U25.38 | B | M.SPEC.156 (the A.U8.20 rows for the polled waits go) |
| A.U25.39 | B | M.SPEC.039, M.SPEC.093, M.SPEC.106 |
| A.U25.40 | B | M.SPEC.043 |
| A.U25.42 | B | M.SPEC.089 |
| A.U25.43 | B | M.SPEC.023, M.SPEC.107 |
| A.U25.45 | B | M.SPEC.156 (the deferred-U25 rows close "polled"; each remaining wait's deadline row) |
| A.U25.46 | B | M.SPEC.077, M.SPEC.085 |
| A.U25.47 | B | M.SPEC.020 |
| A.U25.58 | B | M.SPEC.089 |
| A.U25.59 | B | M.SPEC.095 |
| A.U25.61 | B | M.SPEC.130 |
| A.U25.65 | B | M.SPEC.058 (its end-state statement replaces the C.7 sentence; its README edit is TWIN) |
| A.U25.67 | B | M.SPEC.142, M.SPEC.143 |
| A.U25.69 | EB | M.SPEC.020 |
| A.U25.74 | B | M.SPEC.085 |
| A.U26.01 | B | M.SPEC.146 |
| A.U26.02 | B | M.SPEC.035 |
| A.U26.07 | B | M.SPEC.016 |
| A.U26.08 | B | M.SPEC.065 |
| A.U26.09 | B | M.SPEC.065 |
| A.U26.15 | B | M.SPEC.077 |
| A.U26.20 | B | M.SPEC.062 |
| A.U26.22 | B | M.SPEC.058 |
| A.U26.30 | B | M.SPEC.096 |
| A.U26.31 | B | M.SPEC.082 |
| A.U26.33 | B | M.SPEC.137 |
| A.U26.34 | B | M.SPEC.083 |
| A.U26.39 | B | M.SPEC.083 |
| A.U26.41 | B | M.SPEC.067 |
| A.U26.44 | B | M.SPEC.082 |
| A.U26.51 | EB | M.SPEC.083 |
| A.U26.54 | B | M.SPEC.156 (the `l4.<test>_min_answered` rows) |
| A.U26.56 | B | M.SPEC.083 |
| A.U26.58 | B | M.SPEC.090 |
| A.U26.59 | B | M.SPEC.108 |
| A.U26.63 | B | M.SPEC.160 |
| A.U26.64 | B | M.SPEC.156 (`l4.openhab_poll_interval_s`) |
| A.U26.66 | B | M.SPEC.069, M.SPEC.142 |
| A.U26.68 | B | M.SPEC.085 |
| A.U26.72 | B | M.SPEC.151 |
| A.U26.74 | IB | M.SPEC.161 |
| A.U26.82 | B | M.SPEC.137 |
| A.U26.84 | B | M.SPEC.156, M.SPEC.157 (the FRC readiness rows' measured basis) |
| A.U26.85 | B | M.SPEC.156 (`l4.lwip_spin_concurrent_request_max_s`) |
| A.U26.86 | B | M.SPEC.083 |
| A.U26.87 | B | M.SPEC.137 |
| A.U27.01 | B | M.SPEC.129 |
| A.U27.02 | B | M.SPEC.027, M.SPEC.035, M.SPEC.043, M.SPEC.104 |
| A.U27.03 | IB | M.SPEC.043 |
| A.U27.04 | B | M.SPEC.035 |
| A.U27.05 | B | M.SPEC.035, M.SPEC.076 |
| A.U27.06 | B | M.SPEC.022, M.SPEC.035, M.SPEC.150 |
| A.U27.07 | B | M.SPEC.006, M.SPEC.018, M.SPEC.021, M.SPEC.056 |
| A.U27.09 | B | M.SPEC.043, M.SPEC.148 |
| A.U27.10 | B | M.SPEC.147 |
| A.U27.11 | B | M.SPEC.078 |
| A.U27.12 | B | M.SPEC.026, M.SPEC.081 |
| A.U27.14 | IB | M.SPEC.034, M.SPEC.079 |
| A.U27.15 | IB | M.SPEC.078 |
| A.U27.16 | B | M.SPEC.076 |
| A.U27.17 | B | M.SPEC.085 |
| A.U27.18 | B | M.SPEC.078 |
| A.U27.19 | B | M.SPEC.082 |
| A.U27.21 | B | M.SPEC.130 |
| A.U27.22 | B | M.SPEC.043 |
| A.U27.23 | B | M.SPEC.043 |
| A.U27.24 | B | M.SPEC.043 |
| A.U27.25 | IB | M.SPEC.034, M.SPEC.043 |
| A.U27.28 | B | dropped: comment-cap rewraps; detail moved by the executor per CLAUDE.md lands with its owning action, no named SPEC text |
| A.U27.29 | B | M.SPEC.148 |
| A.U27.31 | B | M.SPEC.035, M.SPEC.042 |
| A.U27.33 | B | M.SPEC.159 |
| A.U27.34 | B | M.SPEC.035 |
| A.U27.35 | B | M.SPEC.035 |
| A.U27.36 | B | M.SPEC.035 |
| A.U27.38 | B | M.SPEC.085 |
| A.U28.01 | B | M.SPEC.033 |
| A.U28.04 | B | M.SPEC.033 |
| A.U28.05 | B | M.SPEC.034 |
| A.U28.06 | B | M.SPEC.033 |
| A.U28.07 | B | M.SPEC.034, M.SPEC.124 |
| A.U28.08 | B | M.SPEC.034 |
| A.U28.09 | B | M.SPEC.034 |
| A.U28.10 | B | M.SPEC.033 |
| A.U28.11 | B | M.SPEC.034 |
| A.U28.12 | IB | M.SPEC.007 |
| A.U28.13 | B | M.SPEC.034 |
| A.U28.15 | B | M.SPEC.033, M.SPEC.034, M.SPEC.081 |
| A.U28.16 | B | M.SPEC.034, M.SPEC.124 |
| A.U28.17 | B | M.SPEC.034, M.SPEC.123 |
| A.U28.18 | B | M.SPEC.123 |
| A.U28.19 | B | M.SPEC.034 |
| A.U28.20 | B | dropped: a code comment citing Part H, which stays (C6 holds) |
| A.U28.21 | B | M.SPEC.123 |
| A.U28.22 | B | M.SPEC.123 |
| A.U28.24 | B | M.SPEC.114 |
| A.U28.25 | B | M.SPEC.124 |
| A.U28.26 | B | M.SPEC.124 |
| A.U28.27 | B | M.SPEC.043, M.SPEC.074, M.SPEC.075, M.SPEC.076 |
| A.U28.30 | B | M.SPEC.075, M.SPEC.104 |
| A.U28.33 | B | dropped: `.gitignore` comments citing A.9 (M.SPEC.022) and L, both kept (C6 holds) |
| A.U28.35 | B | M.SPEC.005, M.SPEC.019 |
| A.U28.36 | EB | M.SPEC.156 |
| A.U28.37 | IB | M.SPEC.033, M.SPEC.034, M.SPEC.123, M.SPEC.124 |
| A.U28.39 | B | M.SPEC.043 |
| A.U28.41 | B | M.SPEC.043, M.SPEC.148 |
| A.U28.42 | B | M.SPEC.033, M.SPEC.034 |
| A.U28.43 | B | M.SPEC.034, M.SPEC.124 |
| A.U29.01 | IB | M.SPEC.003, M.SPEC.024 |
| A.U29.02 | B | M.SPEC.024 |
| A.U29.03 | IB | M.SPEC.024, M.SPEC.145, M.SPEC.146 |
| A.U29.04 | EB | M.SPEC.024 |
| A.U30.01 | IB | M.SPEC.094, M.SPEC.128 |
| A.U30.02 | IB | M.SPEC.125, M.SPEC.126, M.SPEC.138 |
| A.U30.03 | B | M.SPEC.126 |
| A.U30.07 | B | M.SPEC.111, M.SPEC.126 |
| A.U30.09 | IB | M.SPEC.102 |
| A.U30.10 | B | M.SPEC.130 |
| A.U30.11 | IB | M.SPEC.126 |
| A.U30.12 | B | M.SPEC.079, M.SPEC.129 |
| A.U30.13 | B | M.SPEC.129 |
| A.U30.14 | B | M.SPEC.129 |
| A.U30.17 | IB | M.SPEC.085, M.SPEC.129, M.SPEC.130 |
| A.U30.18 | IB | M.SPEC.092, M.SPEC.128 |
| A.U30.19 | B | M.SPEC.021, M.SPEC.058, M.SPEC.092, M.SPEC.111 |
| A.U30.20 | IB | M.SPEC.121, M.SPEC.125 |
| A.U30.21 | B | M.SPEC.126 |
| A.U31.01 | IB | M.SPEC.097, M.SPEC.108, M.SPEC.156 |
| A.U31.02 | B | M.SPEC.097 |
| A.U31.03 | IB | M.SPEC.020, M.SPEC.097, M.SPEC.156 |
| A.U31.04 | B | dropped: a code comment citing F.3, which stays (M.SPEC.097; C6 holds) |
| A.U31.05 | B | M.SPEC.097 |
| A.U31.06 | B | M.SPEC.085, M.SPEC.097 |
| A.U31.07 | B | M.SPEC.006, M.SPEC.015, M.SPEC.020, M.SPEC.097 |
| A.U31.08 | B | M.SPEC.097, M.SPEC.146 |
| A.U31.09 | B | M.SPEC.151 |
| A.U31.11 | B | M.SPEC.151 |
| A.U31.13 | B | M.SPEC.156 (rows renamed to ms, (3)) |
| A.U31.14 | B | M.SPEC.156 (rows renamed to ms; GAP-U9's `next_sleep_min_ms`) |
| A.U31.15 | B | M.SPEC.156 (rows renamed to ms, (3)) |
| A.U31.16 | B | M.SPEC.156 (rows renamed to ms, (3)) |
| A.U31.17 | B | M.SPEC.067 |
| A.U31.18 | B | M.SPEC.018, M.SPEC.093, M.SPEC.094, M.SPEC.127 |
| A.U31.19 | IB | M.SPEC.074, M.SPEC.091, M.SPEC.093 |
| A.U32.01 | B | M.SPEC.088 |
| A.U32.02 | B | M.SPEC.089 |
| A.U32.03 | IB | M.SPEC.056 |
| A.U32.04 | B | M.SPEC.151 |
| A.U32.06 | B | M.SPEC.021, M.SPEC.113 |
| A.U33.01 | IB | M.SPEC.141, M.SPEC.143 |
| A.U33.02 | IB | M.SPEC.144 |
| A.U33.03 | IB | M.SPEC.149 |
| A.U33.05 | IB | M.SPEC.003, M.SPEC.044, M.SPEC.124 |
| A.U33.06 | B | M.SPEC.043 |
| A.U33.07 | B | M.SPEC.097, M.SPEC.108, M.SPEC.136 |
| A.U33.09 | B | M.SPEC.103 |
| A.U34.01 | B | M.SPEC.005, M.SPEC.133 |
| A.U34.04 | B | M.SPEC.098 |
| A.U34.07 | IB | M.SPEC.142 |
| A.U34.08 | IB | M.SPEC.005 |
| A.U34.09 | B | M.SPEC.019 |
| A.U34.12 | B | M.SPEC.005 |
| A.U35.03 | B | M.SPEC.075, M.SPEC.077 |
| A.U35.04 | B | M.SPEC.160 |
| A.U35.06 | IB | M.SPEC.137 |
| A.U35.07 | B | M.SPEC.077 |
| A.U35.10 | B | M.SPEC.077 |
| A.U35.13 | B | M.SPEC.156, M.SPEC.157 (rows withdrawn with their literals) |
| A.U35.14 | B | M.SPEC.156, M.SPEC.157 (rows withdrawn with their literals) |
| A.U35.15 | B | M.SPEC.156, M.SPEC.157 (rows withdrawn, or the cap's row) |
| A.U35.18 | B | M.SPEC.156 (`l1.bus_fault_isolation_bound_s`) |
| A.U35.21 | B | M.SPEC.065, M.SPEC.083 |
| A.U35.23 | EB | M.SPEC.079 |
| A.U35.24 | B | M.SPEC.076 |
| A.U35.25 | B | M.SPEC.129 |
| A.U35.27 | B | M.SPEC.085 |
| A.U35.28 | B | M.SPEC.160 |
| A.U35.29 | B | M.SPEC.156 (the L2 floor row) |
| A.U35.30 | B | M.SPEC.111 |
| A.U35.32 | B | M.SPEC.092, M.SPEC.107 |
| A.U35.33 | B | M.SPEC.160 |
| A.U35.36 | B | M.SPEC.018, M.SPEC.074 |
| A.U35.37 | B | M.SPEC.058 |
| A.U35.41 | IB | M.SPEC.081 |
| A.U35.42 | B | M.SPEC.081 |
| A.U35.43 | IB | M.SPEC.054 |
| A.U35.45 | B | M.SPEC.071 |
| A.U35.48 | B | M.SPEC.064 |
| A.U35.52 | B | M.SPEC.095 |
| A.U35.56 | EB | M.SPEC.157 |
| A.U36.002 | B | M.SPEC.020 |
| A.U36.003 | IB | M.SPEC.020 |
| A.U36.004 | B | M.SPEC.020 |
| A.U36.006 | IB | M.SPEC.088, M.SPEC.151, M.SPEC.152 |
| A.U36.007 | IB | M.SPEC.082 |
| A.U36.008 | IB | M.SPEC.099 |
| A.U36.009 | IB | M.SPEC.082 |
| A.U36.011 | IB | M.SPEC.035 |
| A.U36.012 | IB | M.SPEC.084 |
| A.U36.013 | B | M.SPEC.126 |
| A.U36.014 | B | M.SPEC.065 |
| A.U36.015 | IB | M.SPEC.065 |
| A.U36.016 | IB | M.SPEC.023, M.SPEC.077 |
| A.U36.017 | IB | M.SPEC.003, M.SPEC.077 |
| A.U36.019 | IB | M.SPEC.019 |
| A.U36.020 | B | M.SPEC.153 |
| A.U36.021 | B | M.SPEC.153 |
| A.U36.022 | IB | M.SPEC.003, M.SPEC.019, M.SPEC.151, M.SPEC.152 |
| A.U36.023 | IB | M.SPEC.087, M.SPEC.094, M.SPEC.109, M.SPEC.158 |
| A.U36.025 | B | M.SPEC.133 |
| A.U36.026 | IB | M.SPEC.132 |
| A.U36.027 | IB | M.SPEC.133 |
| A.U36.028 | IB | M.SPEC.083 |
| A.U36.029 | B | dropped: its Blast finds no SPEC change at HEAD (C.7.2 unchanged; `DSTOffset` not in SPEC) |
| A.U36.031 | IB | M.SPEC.002, M.SPEC.087, M.SPEC.109 |
| A.U36.032 | IB | M.SPEC.074 |
| A.U36.033 | IB | M.SPEC.096 |
| A.U36.034 | B | M.SPEC.061, M.SPEC.096 |
| A.U36.036 | IB | M.SPEC.022, M.SPEC.078, M.SPEC.089 |
| A.U36.037 | IB | M.SPEC.039, M.SPEC.106 |
| A.U36.039 | IB | M.SPEC.069, M.SPEC.142 |
| A.U36.040 | IB | M.SPEC.107, M.SPEC.137 |
| A.U36.041 | IB | M.SPEC.147 |
| A.U36.043 | IB | M.SPEC.043 |
| A.U36.044 | IB | M.SPEC.003, M.SPEC.119, M.SPEC.120 |
| A.U36.045 | IB | M.SPEC.083 |
| A.U36.046 | IB | M.SPEC.095 |
| A.U36.500 | IB | M.SPEC.113, M.SPEC.116, M.SPEC.118 |
| A.U36.501 | IB | M.SPEC.113 |
| A.U36.502 | IB | M.SPEC.117, M.SPEC.150 |
| A.U36.503 | IB | M.SPEC.116 |
| A.U36.504 | IB | M.SPEC.116, M.SPEC.119 |
| A.U36.505 | IB | M.SPEC.116 |
| A.U36.506 | IB | M.SPEC.116, M.SPEC.153 |
| A.U36.507 | IB | M.SPEC.116 |
| A.U36.508 | IB | M.SPEC.119 |
| A.U36.509 | IB | M.SPEC.115 |
| A.U36.510 | IB | M.SPEC.113, M.SPEC.116 |
| A.U36.511 | IB | M.SPEC.005, M.SPEC.007, M.SPEC.020, M.SPEC.023, M.SPEC.039, M.SPEC.072, M.SPEC.143, M.SPEC.144, M.SPEC.145, M.SPEC.146 |
| A.U36.512 | IB | M.SPEC.001, M.SPEC.004, M.SPEC.005, M.SPEC.020, M.SPEC.026, M.SPEC.039, M.SPEC.079, M.SPEC.081, M.SPEC.083, M.SPEC.084, M.SPEC.106, M.SPEC.108, M.SPEC.144 |
| A.U36.513 | B | M.SPEC.072 |
| A.U36.514 | IB | M.SPEC.072, M.SPEC.118, M.SPEC.148, M.SPEC.149 |
| A.U36.515 | IB | M.SPEC.117, M.SPEC.118, M.SPEC.147 |
| A.U36.516 | IB | M.SPEC.022, M.SPEC.069, M.SPEC.142, M.SPEC.143 |
| A.U36.517 | IB | M.SPEC.114, M.SPEC.121, M.SPEC.123, M.SPEC.124 |
| A.U36.518 | IB | M.SPEC.147 |
| A.U36.519 | IB | M.SPEC.150 |
| A.U36.520 | B | dropped: a `devices/wozi.toml` comment citing Part L, which stays (C6 holds) |
| A.U36.521 | IB | M.SPEC.038, M.SPEC.042 |
| A.U36.522 | EB | dropped [extra]: README text citing B.13 (M.SPEC.037 names it as DOCS blast) |
| A.U36.523 | IB | M.SPEC.037 |
| A.U36.524 | IB | M.SPEC.001, M.SPEC.003, M.SPEC.031, M.SPEC.045 |
| A.U36.525 | B | M.SPEC.086 |
| A.U36.526 | IB | M.SPEC.081 |
| A.U36.527 | B | M.SPEC.043, M.SPEC.068 |
| A.U36.529 | B | M.SPEC.153 |
| A.U36.530 | IB | M.SPEC.016 |
| A.U36.531 | B | M.SPEC.017, M.SPEC.095 |
| A.U36.532 | IB | M.SPEC.003, M.SPEC.073, M.SPEC.077, M.SPEC.108, M.SPEC.118, M.SPEC.121, M.SPEC.122, M.SPEC.123, M.SPEC.132, M.SPEC.136 |
| A.U36.533 | IB | M.SPEC.075 |
| A.U36.534 | IB | M.SPEC.068, M.SPEC.075 |
| A.U36.535 | IB | M.SPEC.006, M.SPEC.046 |
| A.U36.537 | EB | M.SPEC.021, M.SPEC.151, M.SPEC.154 |
| A.U36.538 | IB | M.SPEC.054 |
| A.U36.539 | IB | M.SPEC.137 |
| A.U36.540 | IB | M.SPEC.073, M.SPEC.074, M.SPEC.075, M.SPEC.112, M.SPEC.140 |
| A.U36.541 | IB | M.SPEC.001, M.SPEC.002, M.SPEC.003, M.SPEC.074, M.SPEC.140 |
| A.U36.542 | IB | M.SPEC.002, M.SPEC.047, M.SPEC.056, M.SPEC.077, M.SPEC.140 |
| A.U36.543 | IB | M.SPEC.001, M.SPEC.003, M.SPEC.005, M.SPEC.007, M.SPEC.046, M.SPEC.069, M.SPEC.073, M.SPEC.075, M.SPEC.140, M.SPEC.142, M.SPEC.143 |
| A.U36.544 | EB | M.SPEC.018, M.SPEC.020, M.SPEC.021, M.SPEC.023, M.SPEC.035, M.SPEC.050, M.SPEC.059, M.SPEC.064, M.SPEC.065, M.SPEC.071, M.SPEC.072, M.SPEC.077, M.SPEC.078, M.SPEC.084, M.SPEC.092, M.SPEC.093, M.SPEC.107, M.SPEC.108, M.SPEC.145 |
| A.U36.545 | IB | M.SPEC.005, M.SPEC.019 |
| A.U36.546 | IB | M.SPEC.003, M.SPEC.010, M.SPEC.019, M.SPEC.026, M.SPEC.037, M.SPEC.043, M.SPEC.045, M.SPEC.049, M.SPEC.078, M.SPEC.130, M.SPEC.151, M.SPEC.152 |
| A.U36.547 | B | dropped: the README map (DOCS); the Parts it cites exist (C6 holds) |
| A.U36.548 | IB | M.SPEC.005, M.SPEC.007, M.SPEC.022, M.SPEC.036, M.SPEC.039, M.SPEC.041, M.SPEC.045, M.SPEC.055, M.SPEC.060, M.SPEC.061, M.SPEC.081, M.SPEC.082, M.SPEC.084, M.SPEC.085, M.SPEC.099, M.SPEC.101, M.SPEC.102, M.SPEC.106, M.SPEC.127, M.SPEC.131, M.SPEC.138 |
| A.U36.549 | B | M.SPEC.124 |
| A.U37.02 | B | M.SPEC.089 |
| A.U37.04 | IB | M.SPEC.087 |
| A.U37.06 | IB | M.SPEC.023 |
| A.U37.07 | B | M.SPEC.112 |
| A.U37.11 | IB | M.SPEC.150 |
| AC3_R R-03 | A-C3 | M.SPEC.049 (1): A.U13.05's first sentence plus the lead's withdrawal text (no pull-up claim, no phase-C measurement); Resolved records the supersession; tag written "(agent, 2026-09-29)" (adapted from "(lead, 2026-09-30)": the lead's note at the end of `U13.md` is dated 2026-09-29, and a permanent actor tag is "(owner, …)" or "(agent, …)", G9/R11) |
| AC3_R R-09 | A-C3 | M.SPEC.021 item 8 gains the GET's chip I/O sentence; From gains G3/R31 |
| AC3_R R-04 | A-C3 | M.SPEC.073 and M.SPEC.140 Blast pointers name M.DOCS.109 and M.PROC.048 (R-04 cited them as .046/.142; adapted to the two changes that hold the pointers) |
| AC3_S S-13 | A-C3 | as AC3_R R-04 (one change, M.DOCS.109) |
| AC3_S §5 | A-C3 | M.SPEC.153 Blast: twin test comments → A.U36.020 (TWIN, M.TWIN.122/.126) |
| AC3_O O-19 | A-C3 | M.SPEC.070: "(A.U10.22)" → `tests_scripts/test_readiness_gates.py` |
| AC3_O O-20 | A-C3 | M.SPEC.116: "(A.U32.06)" out of the row text; A.U32.06 added to From |
| AC3_O O-21 | A-C3 | M.SPEC.129: "(A.C.09)" out of the release-proof line (A.C.09 stays in From) |
| AC3_O O-22 | A-C3 | M.SPEC.136: "not touched in this audit" → "stays as it is until the C side is reconciled" (the M.DOCS.076 half is DOCS's) |
| AC3_O O-23 | A-C3 | M.SPEC.054, M.SPEC.064, M.SPEC.075, M.SPEC.082: tags in "(owner, YYYY-MM-DD)" form |
| AC3_O B (placeholders) | A-C3 | M.SPEC.111 `<A.U10.08's check>` → `tests_scripts/test_watchdog_feed_sites.py` (M.TSC.155); M.SPEC.144 `<A.U6.15's check>` → `test_no_variant_literals.py` (M.TSC.110) |
| G9/R12 (lead, applier 2 hand-off H-3) | A-C3 | M.SPEC.136 (3): the changelog-entry citation `UART_C_PORT_CHANGELOG.md` A10/A11 → the two candidates stated in place (G9/R12 lists `SPECIFICATION.md:5532` (A10/A11) itself) |

## A-C2 order notes (2026-10-01)

Unit and Depends edits made by the A-C2 work order (`audit/order/WORK_ORDER.md`); one row per edit.

| M-ID | slot | edit | reason |
|---|---|---|---|
| M.SPEC.006 | Unit | appended: A-C2 step order: A.U10.09's part lands in U11, not U10 (it needs A.U11.03, which lands in U11). | dependency deferral (an edge ran from a later step) |
| M.SPEC.007 | Unit | appended: A-C2: stage U28 — A.U28.12's A.3 pointer to B.10's job list lands with that list (M.SPEC.033, U28). | Depends edge ran from a later step: M.SPEC.033/.034 depend on A.U28.12 in U28 |
| M.SPEC.010 | Unit | appended: A-C2 step order: A.S0930.14's part lands in U20, not U16 (it follows A.S0930.14's own change, which lands in U20). | dependency deferral (an edge ran from a later step) |
| M.SPEC.014 | Unit | appended: A-C2 step order: A.U9.09's part lands in U10, not U9 (it follows A.U9.09's own change, which lands in U10). | dependency deferral (an edge ran from a later step) |
| M.SPEC.021 | Unit | appended: A-C2 step order: A.S0930.12's part lands in U20, not U11 (it follows A.S0930.12's own change, which lands in U20); A.S0930.31's part lands in U20, not U11 (it follows A.S0930.31's own change, which lands in U20); A.S0930.32's part lands in U20, not U11 (it needs A.S0930.13, which lands in U20); A.S0930.33's part lands in U20, not U11 (it follows A.S0930.33's own change, which lands in U20). | dependency deferral (an edge ran from a later step) |
| M.SPEC.034 | Unit | appended: A-C2 step order: A.U28.13's part lands in U0 (A.SDEP.05: "A.U28.13 (pulled forward)" into the GitHub Actions pin refresh). | a part lands outside the Unit slot's units by an action's own text |
| M.SPEC.041 | Unit | appended: A-C2 step order: A.U14.30's part lands in U19, not U14 (it needs A.U19.24, which lands in U19). | dependency deferral (an edge ran from a later step) |
| M.SPEC.049 | Unit | appended: A-C2: "S0930" is not a unit; its parts land in the units SUPP_owner_0930 states: A.S0930.17 in U16, A.S0930.30 in U36. | AC3_R R-08 (h) |
| M.SPEC.051 | Unit | appended: A-C2 step order: A.U2.22's part lands in U3, not U2 (it needs A.U2.02, which lands in U3); A.U10.R01's part lands in U13, not U10 (it follows A.U10.R01's own change, which lands in U13). | dependency deferral (an edge ran from a later step) |
| M.SPEC.055 | Unit | appended: A-C2: "S0930" is not a unit; its parts land in the units SUPP_owner_0930 states: A.S0930.16 in U11. | AC3_R R-08 (h) |
| M.SPEC.058 | Unit | appended: A-C2 step order: A.U2.14's part lands in U3, not U2 (it follows A.U2.14's own change, which lands in U3); A.U2.22's part lands in U3, not U2 (it needs A.U2.02, which lands in U3); A.U10.R01's part lands in U13, not U10 (it follows A.U10.R01's own change, which lands in U13). | dependency deferral (an edge ran from a later step) |
| M.SPEC.059 | Unit | appended: A-C2 step order: A.U2.02's part lands in U3, not U2 (it follows A.U2.02's own change, which lands in U3); A.U2.15's part lands in U3, not U2 (it follows A.U2.15's own change, which lands in U3); A.U2.22's part lands in U3, not U2 (it needs A.U2.02, which lands in U3). | dependency deferral (an edge ran from a later step) |
| M.SPEC.060 | Unit | appended: A-C2 step order: A.U2.15's part lands in U3, not U2 (it follows A.U2.15's own change, which lands in U3). | dependency deferral (an edge ran from a later step) |
| M.SPEC.060 | Unit | appended: A-C2: "S0930" is not a unit; its parts land in the units SUPP_owner_0930 states: A.S0930.01 in U20. | AC3_R R-08 (h) |
| M.SPEC.064 | Unit | appended: A-C2: "S0930" is not a unit; its parts land in the units SUPP_owner_0930 states: A.S0930.17 in U16, A.S0930.30 in U36. | AC3_R R-08 (h) |
| M.SPEC.066 | Unit | appended: A-C2 step order: A.U10.28's part lands in U16, not U10 (it follows A.U10.28's own change, which lands in U16). | dependency deferral (an edge ran from a later step) |
| M.SPEC.069 | Unit | appended: A-C2 step order: A.U2.22's part lands in U3, not U2 (it needs A.U2.02, which lands in U3). | dependency deferral (an edge ran from a later step) |
| M.SPEC.076 | Unit | appended: A-C2 step order: A.U2.02's part lands in U3, not U2 (it follows A.U2.02's own change, which lands in U3); A.U24.70's part lands in U25, not U24 (it needs A.U24.65, which lands in U25). | dependency deferral (an edge ran from a later step) |
| M.SPEC.079 | Unit | appended: A-C2 step order: A.U24.65's part lands in U25, not U24 (it follows A.U24.65's own change, which lands in U25). | dependency deferral (an edge ran from a later step) |
| M.SPEC.094 | Unit | appended: A-C2 step order: A.U14.R01's part lands in U18, not U14 (it needs A.U18.R01, which lands in U18). | dependency deferral (an edge ran from a later step) |
| M.SPEC.096 | Unit | appended: A-C2 step order: A.U14.R01's part lands in U18, not U14 (it needs A.U18.R01, which lands in U18); A.S0930.14's part lands in U20, not U11 (it follows A.S0930.14's own change, which lands in U20); A.S0930.33's part lands in U20, not U11 (it follows A.S0930.33's own change, which lands in U20). | dependency deferral (an edge ran from a later step) |
| M.SPEC.108 | Unit | appended: A-C2 step order: A.U14.R01's part lands in U18, not U14 (it needs A.U18.R01, which lands in U18). | dependency deferral (an edge ran from a later step) |
| M.SPEC.111 | Unit | appended: A-C2 step order: A.S0930.13's part lands in U20, not U11 (it follows A.S0930.13's own change, which lands in U20). | dependency deferral (an edge ran from a later step) |
| M.SPEC.121 | Unit | appended: A-C2 step order: A.U14.30's part lands in U19, not U14 (it needs A.U19.24, which lands in U19). | dependency deferral (an edge ran from a later step) |
| M.SPEC.135 | Unit | appended: A-C2 step order: A.U14.R01's part lands in U18, not U17 (it needs A.U18.R01, which lands in U18). | dependency deferral (an edge ran from a later step) |
| M.SPEC.137 | Unit | appended: A-C2 step order: A.U17.25's part lands in U25, not U24 (it follows A.U17.25's own change, which lands in U25). | dependency deferral (an edge ran from a later step) |
| M.SPEC.139 | Unit | appended: A-C2 step order: A.U10.R01's part lands in U13, not U11 (it follows A.U10.R01's own change, which lands in U13). | dependency deferral (an edge ran from a later step) |
| M.SPEC.147 | Unit | appended: A-C2 step order: A.U2.24's part lands in U6, not U2 (it needs A.U2.21, which lands in U6); A.U0.59's part lands in U25, not U2 (it follows A.U0.59's own change, which lands in U25). | dependency deferral (an edge ran from a later step) |

## A-C review fold (2026-10-05)

Folds the owner's review answers (OR136-OR143, `audit/actions/FOLD_ANSWERS.md`, the routine settlements of
`audit/review/routine_merge.json`, AC_NOTES 52) into the changes above, per `audit/actions/FOLD_BRIEF.md`. Every amended
change names its source in From with "(A-C review fold)"; one change is added (M.SPEC.162, placed in Part B). Convention
C9 (above Part A) fixes the review-answer tag form.

| Fnn | M-ID(s) | action |
|---|---|---|
| F01 | M.SPEC.061 (C.7.3: absent file written once; write list), M.SPEC.096 (F.2 write-path clause), M.SPEC.021 (A.8 reset purpose: each file written once after the reboot), M.SPEC.020 (A.7 setup-batch sentence), M.SPEC.097 (`stall.flash_program` write list) | amended |
| F02 | M.SPEC.021 (A.8 `HTTPDropped` 24-hour window, `ResetErrors` clears it), M.SPEC.111 (G.2 hourly window counter entry), M.SPEC.121 (H.7 counted in the window), M.SPEC.126 (I.2 row), M.SPEC.113 (values-not-shown tag) | amended |
| F03 | M.SPEC.061 (C.7.3 `ConfigFaults`; delete unread, a failed delete reads as reset reason 9), M.SPEC.021 (A.8 field; delete unread in the shutdown sequence, a failed delete reset reason 9, never an HTTP "Failed"), M.SPEC.020 (fixed at the batch end), M.SPEC.113 (Status placement gains the row) | amended |
| F04 | M.SPEC.162 (new B.14.5 tick-offset override), M.SPEC.038 (B.14 count and test-only clause), M.SPEC.082 (E.6.3 rollover round), M.SPEC.092 (F.1 silicon rollover sentence), M.SPEC.150 (build info names the override), M.SPEC.156 (the offset's row) | added (M.SPEC.162), amended |
| F05 | M.SPEC.036 (B.12: throwaway password, passed plainly, never committed) | amended |
| F06 | M.SPEC.018 (A.5 console bullet), M.SPEC.097 (`stall.console` guard) | amended |
| F07 | M.SPEC.021 (A.8: API one command, website confirms), M.SPEC.116 (H.4 "Confirmations" row) | amended |
| F08 | M.SPEC.111 (G.2 derived quantities: the Magnus humidity domain; helpers stay) | amended |
| F09 | M.SPEC.014 (A.4: internal queue bounded, external refusal says retry), M.SPEC.021 (A.8 `LightCmdLED`), M.SPEC.119 (H.6) | amended |
| F10 | — | none in this file |
| F11 | M.SPEC.058 (C.7: per-layer rule plus the mixed-kind rule and its narrowed scan), M.SPEC.051 (C.4.1 (5): the same two rules; A.U3.03 dropped), M.SPEC.010 (A.4 FRAM), M.SPEC.054 (A.U3.05's caller half dropped), M.SPEC.059 (A.U3.09 dropped), M.SPEC.062 (A.U3.07 dropped), M.SPEC.101 (F.5.2) | amended |
| F12 | M.SPEC.119 (H.6: readonly status codes clickable) | amended |
| F13 | — | none in this file |
| F14 | M.SPEC.035 (B.11 bump sentence), M.SPEC.043 (B.15 stubs move with the bump) | amended |
| F15 | M.SPEC.021 (A.8: no SCD30 write during a sequence) | amended |
| F16 | M.SPEC.023 (A.10: the twin's NTP responder) | amended |
| F17 | M.SPEC.113 (H.1 history clause), M.SPEC.116 (H.4 "Navigation history" row) | amended |
| F18 | M.SPEC.116 (H.4 "Displayed precision" row), M.SPEC.118 (H.5.1 `decimals` for every value), M.SPEC.149 (L.6.4 key set) | amended |
| F19 | M.SPEC.017 (A.4 Wi-Fi: the off pattern follows `LEDWifiOn`) | amended |
| F20 | M.SPEC.007 (A.3), M.SPEC.035 (B.11 A.U36.011 sentence), M.SPEC.083 (E.6.6 `dev-only-bench` reason), M.SPEC.144 (L.1) | amended |
| F21 | C9 (the form); explicit in M.SPEC.014, .017, .018, .020, .021, .022, .023, .035, .036, .043, .058, .061, .092, .108, .111, .113, .116, .118, .119, .146, .150; the full map is the table below | tag |
| F22 | M.SPEC.146 (L.3 rows: kept in `[device]`, checked, never emitted), M.SPEC.149 (L.6.6 check) | amended |
| F23 | M.SPEC.089 (F.1: scope per image, the owner's 12 named sites and the two platform sites; `exec` is S102's, not the list's; A.U10.30's loader rewrite dropped), M.SPEC.145 (L.2), M.SPEC.087 (Part F checklist re-reads the two sites) | amended |
| F24 | M.SPEC.047 (C.2), M.SPEC.075 (D.15), M.SPEC.098 (F.4), M.SPEC.002 (0.4 tag) | amended |
| F25 | M.SPEC.050 (C.3.2 receive side), M.SPEC.108 (F.8.2 DMA ring), M.SPEC.136 (J.6 ring floor), M.SPEC.137 (J.7 lap, fakes, tier rows), M.SPEC.138 (J.8 ring bullet), M.SPEC.126 (I.2 ring row), M.SPEC.130 (I.4(f.1) survivor), M.SPEC.097 (F.3: `con.uart_rx_ring`, not crossed; open point 2 superseded), M.SPEC.020 (A.7), M.SPEC.156 (rows) | amended |
| F26 | M.SPEC.035 (B.11 build date), M.SPEC.147 (L.4), M.SPEC.150 (L.7 build-date paragraph), M.SPEC.108 (F.8.3 idle rate kept, measurement owed), M.SPEC.156 (`udp.poll_idle_ms` owed) | amended |
| F27 | M.SPEC.138 (J.8 end state), M.SPEC.136 (J.6 cap), M.SPEC.050 (C.3.2 readline cap), M.SPEC.111 (G.2 piece primitive), M.SPEC.126 (I.2 UART row), M.SPEC.137 (J.7 tests), M.SPEC.146 (L.3 keys), M.SPEC.149 (L.6.6 check), M.SPEC.156 (rows) | amended |
| F28 | M.SPEC.070 (C.13: the flag only where product code reads it) | amended |
| F29 | — | none in this file |
| F30 | — | none in this file (no SPEC change names the `IP` key; A.8 lists no networking key by name) |
| F31 | M.SPEC.023 (A.10 clock-jump sentence) | amended |
| F32 | M.SPEC.077 (E.2.3 "Waits poll") | amended |
| F33 | — | none in this file |

**F21 map** — where this file writes each answered decision's tag (C9). "explicit": the tag is written in the change;
"C9": the tag sits in an action's text the change quotes and takes the C9 form at landing; "—": this file writes no tag
for it.

| Decision (FOLD_ANSWERS) | status | M-ID | form |
|---|---|---|---|
| release-version-2-0 | ok | M.SPEC.150 (4) | C9 |
| rest-key-scheme | ok | M.SPEC.021 (1) | explicit |
| rest-api-frozen-at-release | ok | M.SPEC.115, M.SPEC.021 (1) | — (owner tags stand) |
| website-unattended | ok | M.SPEC.116 (poll rows) | explicit |
| website-accessibility | ask | M.SPEC.113 | explicit (owner, 2026-10-02) |
| dns-fallback-clear-confirm | ask | M.SPEC.116, M.SPEC.021 (6) | explicit (owner, 2026-10-02) |
| sgp40-wait-zero | ok | M.SPEC.118 (5) | — |
| apply-failure-marks-fields | ok | M.SPEC.119 | — |
| c-stack-reboot | ok | M.SPEC.092 (3) | explicit |
| unreadable-config-file | ask | M.SPEC.061, M.SPEC.021 | explicit (owner, 2026-10-01: the ruling is OR138) |
| timestamps-before-ntp | ok | M.SPEC.111 item 4 | explicit |
| reflash-runbook-erase | ok | — (README, M_DOCS) | — |
| wifi-off-led-pattern | ask | M.SPEC.017 | explicit (owner, 2026-10-02) |
| scd30-calibration-readiness | ok | M.SPEC.151 (M.2) | C9 |
| api-unknown-key-invalid | ok | M.SPEC.021 (5) | — |
| release-defined-point | ok | M.SPEC.150 (4) | C9 |
| lwip-retry-on-full-queue | ok | M.SPEC.042 (owner tag stands), M.SPEC.097 | — |
| humidity-helpers-removed | change | M.SPEC.111 item 11 | explicit (owner, 2026-10-02) |
| http-head-limits | ok | M.SPEC.018 | C9 |
| static-no-cache | ok | M.SPEC.022 | explicit |
| status-fields-added-and-left-out | ask | M.SPEC.021 (3), M.SPEC.113 | explicit (owner, 2026-10-01 for `HTTPDropped`, OR137; owner, 2026-10-02 for the values left out) |
| deactivated-snapshot | ok | M.SPEC.021 (3) | — |
| ntp-synced-goes-stale | ok | M.SPEC.060 | C9 |
| ntp-no-origin-check | ok | M.SPEC.060 | C9 |
| dns-fallback-setting | ok | M.SPEC.060 | C9 |
| hotspot-redirect | ok | M.SPEC.018 (10) | C9 if its text carries a tag |
| envelope-codes-equal-http | ok | M.SPEC.056 | C9 |
| system-command-words | ok | M.SPEC.021 (5) | — (owner tag stands) |
| system-command-sequence-details | ask | M.SPEC.021 (6) | explicit (owner, 2026-10-02) |
| reset-reason-codes | ask | M.SPEC.119, M.SPEC.021 (4) | explicit (owner, 2026-10-02) |
| failed-push-no-flash-write | ok | M.SPEC.055 | — |
| one-entry-per-fault | change | M.SPEC.058 | explicit (owner, 2026-10-02) |
| led-request-internal-queue | ask | M.SPEC.014, M.SPEC.021, M.SPEC.119 | explicit (owner, 2026-10-02) throughout (lead ruling) |
| threshold-rewrite-failure | ok | M.SPEC.154 | C9 |
| pres-offset-warning | ok | M.SPEC.151 (M.4), M.SPEC.059 | C9 |
| state-code-values | ok | M.SPEC.012, M.SPEC.151, M.SPEC.154 | C9 |
| scd30-write-path | ok | M.SPEC.053 | C9 |
| idle-poll-rate | ask | M.SPEC.108 (3)(e), M.SPEC.156 | explicit (owner, 2026-10-05) |
| ntp-sync-last | ok | M.SPEC.020 item 4 | explicit |
| uart-flash-erase-overrun | change | M.SPEC.097, M.SPEC.108 | explicit (owner, 2026-10-05) |
| heap-floors-kept | ok | M.SPEC.156 (heap rows' Basis) | C9 |
| legacy-wip-as-intent | ask | — (CLAUDE.md, M_DOCS) | — |
| stale-as-fresh-every-driver | ok | M.SPEC.052 | C9 |
| sgp40-chip-identity | ok | M.SPEC.151 (M.3) | C9 |
| standard-state-repair-optin | ask | — | — |
| standard-board-state | ok | — | — |
| console-starvation-bench-test | ask | M.SPEC.018, M.SPEC.097 | explicit (owner, 2026-10-02) |
| hand-run-hardware-rows | ask | — (BACKLOG, M_DOCS) | — |
| twin-tolerates-ntp-offline | change | M.SPEC.023 | explicit (owner, 2026-10-02) |
| typecheck-stripper-text-edit | ok | M.SPEC.035 (5) | explicit |
| stub-versions-pinned | ask | M.SPEC.035, M.SPEC.043 | explicit (owner, 2026-10-02) |
| comment-cap-long-lines | ok | M.SPEC.075 (D.11) | C9 |
| ci-web-filter-base | ok | M.SPEC.034, M.SPEC.124 | C9 |
| bench-sudo-checked | ok | — | — |
| bench-psk-fallback | change | M.SPEC.036 | explicit (owner, 2026-10-02) |
| threat-model-table | ok | M.SPEC.024 | C9 |
| licence-notices | ok | — (THIRD_PARTY, M_DOCS) | — |
| wozi-move-owner-operation | ask | M.SPEC.007, M.SPEC.035, M.SPEC.083, M.SPEC.144 | explicit (owner, 2026-10-02) |
| operator-actions-one-place | ok | — (DEVICE_REFERENCE, M_DOCS) | — |
| favicon-inline | ok | M.SPEC.116 (if a row names it) | C9 |
| website-display-details | ask | M.SPEC.118, M.SPEC.116 | explicit (owner, 2026-10-02) |
| negative-backup-age | ok | M.SPEC.010 item 7 | — |
| no-gcc14-ci-leg | ok | M.SPEC.031, M.SPEC.045 | C9 |
| reproducible-image | ask | M.SPEC.035, M.SPEC.147, M.SPEC.150 | explicit (owner, 2026-10-05) |
| driven-time-and-rtc-steps | ok | M.SPEC.077 | C9 |
| retry-pass-flagged | ok | M.SPEC.078, M.SPEC.086 | C9 |
| twin-first-for-instruments | ok | M.SPEC.082, M.SPEC.085 | C9 |
| toml-build-metadata | ask | M.SPEC.146 | explicit (owner, 2026-10-05) |

**Fold readings, as settled by the lead's rulings (2026-10-05)** (each also in its change's slots):
- F11 scope: dropped A.U3.03, A.U3.04, A.U3.05's caller half, A.U3.07, A.U3.09 (cross-layer and reaction entries stay
  persisted, owner, 2026-10-02). Kept: A.U3.06, A.U3.08, the newest-entry rule parts (A.U3.01/.02/.10, A.U3.12-.15),
  A.U3.05's `ConfigManager` half. A.U3.11 is narrowed to the owner's literal 2026-09-26 rule: one occurrence is never
  persisted as both an error and a warning in one log; the L0 scan flags an `err_s` and a `wrn_s` for one occurrence in
  one function, its allow-list keeping only reasons that still hold. C.7 (M.SPEC.058) and C.4.1 (M.SPEC.051 (5)) state
  the per-layer rule and the mixed-kind rule with its scan.
- F23: the import check covers `__import__` and `importlib`; F.1's list is the owner's 12 sites plus MicroPython's two
  bundled sites; executing a file by path is S102's (ruff), not the list's.
- F09: the LED queue decision is tagged "(owner, 2026-10-02)" everywhere.
- F03: "Reset to defaults" is answered at acceptance; the deletes run unread in the shutdown sequence; a failed delete is
  logged and reads as reset reason 9 at the next boot, never an HTTP "Failed" (M.SPEC.021, M.SPEC.061).
- F28: `SystemService` carries no `initialized`; product code reads the flag only in the FRAM driver, the SPI driver,
  `UARTComm` and `asy_print_log.py` (M.SPEC.070).
- F03/F01: "corrupt" (unparseable) files are never overwritten; a readable file with a bad, missing or unknown key gets
  its one repair; both kinds are listed in `ConfigFaults` (OR136.a (2), OR138.a (1)).
- F27: `readline_until_complete()` lives in a layer without its own logger (C.7.1); which layer writes the over-cap entry
  is decided at execution.
- OR144: the datasheet push precondition of M.SPEC.005 (Depends) and M.SPEC.019 (Unit) is stated as satisfied.
