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

## SPECIFICATION.md — Part B (`:697-1483`)

### M.SPEC.025 B.1 and B.3 step 3: picotool's real compatibility rule
- **From**: A.U21.05 (B.1 item 1, B.3 step 3); A.U14.24 (the F.1 sentence it co-lands with, carried in M.SPEC[F.1]).
- **Site**: `SPECIFICATION.md:705-707` (B.1 item 1), `:751-752` (B.3 step 3).
- **Change**: B.1 item 1 → "**The four pieces must agree, or the build breaks** — `picotool` must be of `pico-sdk`'s
  major version and at least the version `pico-sdk` requires, or the build fails ("Incompatible picotool installation
  found"), and `pico-sdk` must match whatever MicroPython's build compiles against (B.3 derives this instead of
  hand-tracking it)." B.3 step 3 appends "(narrower than pico-sdk's own rule, B.1)". The pico-sdk/picotool file:line
  cites live in F.1 only; they are re-read in the refreshed pin's clones (C3).
- **Resolved**: A.U14.24's "must match that major.minor or the build fails" is replaced by A.U21.05's clause (A.U21.05
  Depends) — one rule in B.1 and F.1.
- **Unit**: U21.
- **Depends**: A.SDEP.08 (pin, C3); M.SPEC[F.1].
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
  therefore". (3) "Because a build directory's name no longer tells you which variant is in it, `scripts/test.sh`
  verifies the binary rather than the path (E.5.2's first consequence)." → "A build directory's name does not tell you
  which build flavour it holds, so every runner asks the binary through `scripts/_unix_port.sh` (E.5.2)."
- **Resolved**: A.U36.512's U36 word change (`:740`) is overtaken by A.U27.12's U27 sentence (same clause, flavour
  word already in it) — one text. A.U21.02 asks for "the help-text wording"; the comments carry it shortened to a
  comment column (agent decision, listed below).
- **Unit**: Stage 1 U21 ((1), (2)); Stage 2 U27 ((3)).
- **Depends**: A.U21.02, A.U21.08, A.U21.12, A.U27.12; M.SPEC[E.5.2].
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
- **Unit**: U21.
- **Depends**: A.U21.17, A.U21.18; M.SPEC[N] rows (A.U21.17, M_TOOL gap 8).
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
- **Depends**: A.U28.01-A.U28.43, A.U27.14, A.U27.25, A.U8.15, M.SPEC[N].
- **Blast carried by**: `ci.yml` comments → A.U28.42 (TOOL); CLAUDE.md carriers → A.U28.11 (DOCS).
- **Kind**: doc

### M.SPEC.035 B.11: building this project's firmware
- **From**: A.U1.16 (`:946-950`, `:983-985`), A.U1.03 (the legacy text moves to `legacy/README.md`), A.U21.02 Blast
  (bump sentence), A.U27.02 Blast (stub sentence), A.U20.15 Blast (`:956` names the generator), M.GEN.019 (boot-entry
  names), A.U36.544 (2) (no "Session N" label), A.U36.011 (`:967-968`), A.U27.04 Blast (strip paragraph), A.U27.05 Blast
  (the shipped form boots under the twin), A.U27.06 Blast (build date the only varying value), A.U27.31 Blast (image
  report), A.U27.34 Blast (sorted freeze), A.U27.35 Blast (intermediates kept), A.U27.36 Blast (`--no-autostart`),
  A.U26.02 Blast (image record), A.U21.22 Blast (one build per toolchain directory).
- **Site**: `SPECIFICATION.md:937-993` (B.11).
- **Change**: (1) `:939-942` → "**Bumping the MicroPython version**: change `versions.toml`'s `[micropython] ref` — the
  only place — then run the platform re-check (CLAUDE.md "Platform target"; Part F's opening checklist). Everything else
  derives: matching pico-sdk/picotool (B.3) and the Unix ports; the stub X.Y.Z is checked against the ref and the
  post-releases are pinned in `[stubs]` (B.15)." (2) `:944-948` → "The legacy build (`legacy/firmware/build-<device>.sh`)
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
  `"main.py"`, reusing the stock `manifest.py` unchanged."; `:967-968` → A.U36.011's sentence. (5) `:970-977` (strip
  paragraph) → A.U27.04's mechanism: every `TYPE_CHECKING` form is blanked line for line in the staged copy, without
  `ast.unparse()`, so comments elsewhere survive and an on-device traceback's line numbers match `src/`; the ~3.6 KB
  figure stays as the reason. (6) `:979-984` → "`tests_scripts/` (CPython/pytest) covers the build tooling fast and
  offline; `test_real_firmware_build_produces_a_valid_uf2` does the real end-to-end build, parametrized over every
  device, gated behind `RUN_SLOW_FIRMWARE_BUILD=1` and run per device in CI's `firmware-build-verify` — this pipeline's
  CI firmware-build stage. `freeze()` receives this project's modules as a sorted list, and the frozen inputs are
  proven reproducible; the build date is the only varying value. The stock `ports/rp2/modules` freeze still follows
  the checkout's directory order (upstream's manifest, not staged here)." (7) `:986-993` (production-readiness) →
  "…proves the build assembles, that the stripped, compiled image set boots under the twin (the shipped form), and (via
  `tests/test_digital_twin_real_website_integration.py`, H.7) that the booted twin serves the real website …";
  "and on first run caught a real bug (an early manifest omitted `ports/rp2/modules/rp2.py`, since fixed by reusing the
  stock manifest)" → "(it proved the stock manifest must be reused: an own manifest omitted `ports/rp2/modules/rp2.py`)".
- **Resolved**: (a) "parametrized over `wozi`/`dev`" is false at HEAD (`tests_scripts/test_build_firmware.py:196`
  parametrizes over `DEVICE_NAMES`) — corrected (adherence finding). (b) A.U20.15's "`<device>_boot.py`" naming is
  superseded by M.GEN.019 (C7). (c) "(retired, Session 6's finish criterion)" goes under A.U36.544 (2) (G9/R12). (d) The
  legacy paragraph's "path not yet genericized (BACKLOG.md)" goes with A.U1.16 (legacy work is never a to-do).
- **Unit**: Stage 1 U1 ((2), (6)'s legacy clause); Stage 2 U20 ((3)'s generator/boot-entry names); Stage 3 U21 ((1)
  re-check, (3) lock); Stage 4 U26/U27 ((1) stubs, (3) record/report/intermediates/`--no-autostart`, (5), (6), (7));
  Stage 5 U36 ((4), A.U36.011).
- **Depends**: A.U1.03, A.U20.05, A.U20.15, A.U21.22, A.U26.02, A.U27.02, A.U27.04-.06, A.U27.31, A.U27.34-.36,
  M.GEN.019.
- **Blast carried by**: README build section → A.U27.35/A.U27.36 (DOCS); `legacy/README.md` → A.U1.03 (DOCS).
- **Kind**: doc

### M.SPEC.036 B.12: tiered environment setup
- **From**: A.U1.16 (`:999` recipe pointer), A.U21.19 Blast (`$BENCH_AP_PASSWORD`), A.U21.24 Blast (the command table),
  A.U21.28 Blast (USB detection rule), A.U36.548 (G9/R11: incident pointer), A.U1.05 Blast (same pointer).
- **Site**: `SPECIFICATION.md:995-1023` (B.12).
- **Change**: (1) `:999` "automating `dev_legacy/README.md`'s manual `nmcli` recipe" → "automating
  `tests_hardware/README.md`'s manual `nmcli` recipe". (2) "**USB device detection**" paragraph → A.U21.28's rule: one
  board resolver — USB vendor `2e8a` plus MicroPython's by-id name, across every `ttyACM*`/`ttyUSB*` entry; exactly one
  match required, zero or several a hard error naming `--device`. (3) "unless overridden" → "unless `$BENCH_AP_PASSWORD`
  is set". (4) `:1017-1018` "`ip`/`nmcli` … missing ones auto-install via `apt`" → "every command a tier runs is checked
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
  mbedtls mention follows the branch), A.U21.02 (the pin-move message cites B.14), A.SDEP.11 ((c): no SIGINT override).
- **Site**: `SPECIFICATION.md:1072-1120` (B.14 up to B.14.1).
- **Change**: (1) `:1074` "(so far: two implemented, one identified and planned)" → "(each subsection below is
  implemented and proven in the built artefact)". (2) `:1093-1094` "the way the mbedtls GCC-14 workaround and
  `MICROPY_PY_SYS_SETTRACE=1` already do it" → "the way `MICROPY_PY_SYS_SETTRACE=1` does it" under A.U21.16's 2a, or
  "the way `MICROPY_PY_SYS_SETTRACE=1` and the one-file mbedtls flag do it" under 2b; "(`build_unix_port()`/
  `build_firmware()` grep their own output for `warning:`)" → "(every build's output passes one diagnostics check, B.7)".
  (3) The general-shape paragraph gains, after "or both;": "paths written into generated files are resolved and refused
  when they hold a character the target syntax cannot carry;" and, after "every build", "and each override is then
  proven in the built artefact — a readback of the preprocessed source or the build's own flags, never only the
  generated input". (4) The "first real test" paragraph's runner list holds (`scripts/run_unix_port_integration.sh`
  stays, M.SCR). (5) Under A.SDEP.11 outcome (c) only: the list gains "the Unix port delivers SIGINT through
  `mp_sched_keyboard_interrupt()` by default (`<file:line>` at <tag>); no override is needed" and B.14.1 goes
  (M.SPEC.039).
- **Resolved**: A.U21.09 writes "three implemented" (U21); A.U36.521 replaces the count with a count-free form (U36),
  which also survives A.SDEP.11 (c) — Stage 1 U21 "(so far: three implemented, one documented and not built)" keeps the
  HEAD text true while B.14.3 still exists; Stage 2 U36 the count-free form.
- **Unit**: Stage 1 U21 ((1) interim, (2), (3)); Stage 2 U36 ((1) final). (5) at U0 if A.SDEP.11 (c).
- **Depends**: A.U21.06, A.U21.08, A.U21.09, A.U21.15, A.U21.16, A.SDEP.11.
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
- **Unit**: Stage 1 U0 ((4), A.SDEP.11); Stage 2 U21 ((3)); Stage 3 U36 ((1), (2)).
- **Depends**: A.SDEP.11, A.U21.06, A.U21.12, A.U25.39, M.SPEC[F.6].
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
- **Unit**: Stage 1 U0 ((3)); Stage 2 U8 ((2)); Stage 3 U18 ((1)).
- **Depends**: A.SDEP.08, A.SDEP.14, A.U8.14, A.U18.02/.09/.15/.16 (the bounds A.U18.18 states).
- **Blast carried by**: `versions.toml` tags → A.U8.14 (TOOL).
- **Kind**: doc

### M.SPEC.041 B.14.2.1: the send stall, the segment pool and what fixes it
- **From**: A.U14.30 (1)-(2) (and its H.7 change, carried in M.SPEC[H.7]), A.U21.09 Blast (the stall sentence names the
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
- **Depends**: A.U14.30, A.U21.09, A.U21.14, A.SDEP.08, A.SDEP.13, A.SDEP.14, M.SPEC.042, M.SPEC[H.7].
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
  M.SPEC[F.7], M.SPEC[H.7]; code comments cite "SPECIFICATION.md B.14" only). (3) Phase C (A.C.10 delta): the proof
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

### M.SPEC.043 B.15: the three passes, what each checks, the stub workarounds
- **From**: A.U27.25 (main-pass/CI paths), A.U27.09 (generated output; `:1440-1442`), A.U20.14 Blast, A.U28.41 Blast,
  A.U27.23 (exclusions checked by another run), A.U0.60 (conftest label), A.U36.043 and A.U25.40 Blast
  (`segfault_stress_repro.py`), A.U27.22 (`ignore-without-code`), A.U27.24 (scope test), A.U27.02 (stub pins; moved
  tree fails), A.U27.03 (workaround list), A.U21.04 (`typings/.stub-spec`), A.U8.23 (Microdot stubs, OR131), A.U28.27
  Blast (two ignore groups), A.U28.39 (path check), A.U33.06 Blast (E722 text may move here), A.U36.527 (B.15 lists the
  passes; `disallow_any_explicit` is C.10's), A.U36.546 (CLAUDE.md's stub-gap and stub-repair narrative moves here),
  A.SDEP.03/A.SDEP.15 (re-read at the refreshed tool and stub versions), M_DOCS gap 1 (c) (BACKLOG `:730-739`'s
  standalone-mypy `Timer()` note, M.DOCS.065).
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
  must equal the ref's, prints and records them in `typings/.stub-spec`, and repairs the package's verified defects
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
  M.SPEC[F.5.5], M.SPEC[D.6].
- **Blast carried by**: CLAUDE.md mypy/stub/scope bullets → A.U36.546/A.U27.22/A.U27.23 (DOCS); `pyproject.toml`,
  `host_typecheck.ini`, `typecheck.ini` comments → A.U27.23/A.U27.25/A.U0.60 (TOOL).
- **Kind**: doc

### M.SPEC.044 New B.16: checkers measured and declined
- **From**: A.U33.05 (1) (section), A.U0.37 (tag on `BACKLOG.md:740`, moves with the text), A.U15.02 (vulture `cast()`
  clause already absent).
- **Site**: new `## B.16 Checkers measured and declined` after B.15 (`:1482`), before Part C.
- **Change**: A.U33.05 (1)'s text verbatim, tagged "(agent, 2026-09-10)" with the vulture sentence's "(owner,
  2026-09-26)". H.8's `npm audit` sentence is M.SPEC[H.8].
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
- **Depends**: M.SPEC.008, M.SPEC[K].
- **Blast carried by**: `src/system_service.py:1` header → A.U36.535 (5) (SRC_CORE).
- **Kind**: doc

### M.SPEC.047 C.2: naming, the shared session class, the constructor tail
- **From**: A.U0.40 L01 (`:1510-1511`), A.U10.38 (derivation rule and exception table), A.U10.35 (private by default),
  A.U10.39 (`_VAL_` names; `_cfg_schema` private), A.U10.21 (one `setup()` contract named), A.U15.40 (4) (`DeviceSession`),
  A.U5.02 Blast (constructor-order rule → the tail), A.U5.09/A.U18.40 Blasts (WiFi's constructor), A.U36.542 (0.4 cites C.2
  for naming and "private by default").
- **Site**: `SPECIFICATION.md:1505-1544` (C.2).
- **Change**: (1) First paragraph: after the CapWords sentence add A.U10.38's rule: "A module's primary class name derives
  from its file name (`asy_<x>_service.py` → `<X>Service`, `asy_<x>_driver.py` → `<X>Driver` unless C.2's compound
  applies); no class carries an `Asy` prefix; acronyms are upper-case (`UARTComm`, `CRCPass`, `NTPClient`,
  `FRAMManager`). Exceptions: the peripheral wrappers `I2C`/`SPI`/`UART` keep the `machine` names (the originals are
  imported under private aliases), and a chip class is the `<CHIP>_<Role>` compound with the chip spelled as its
  `_NAME` (`BMP3XX_Reader`, `SCD30_I2C`, `FRAM_SPI`)." "Name-mangled …" holds. `:1510-1511` → A.U0.40 L01's "One named
  exception to the casing rule (agent, 2026-08-11, `f27b33b`): `voc_algorithm.py`'s internals trace their
  DFRobot/Sensirion source 1:1 (F.4)." (2) New sentence (A.U10.35): "Attributes and methods are private by default; one
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
- **Depends**: A.U13.01, A.U13.07-.10, A.U13.R01, A.U16.16, M.SPEC[F.1], M.SPEC[F.5.2].
- **Blast carried by**: bus driver code/tests → U13 actions (SRC_CORE/TEST_UNIT); Part N `i2c.clear_half_period_us` →
  M.SPEC[N].
- **Kind**: doc

### M.SPEC.049 C.3.1: the SPI variant and FRAM's general-purpose API
- **From**: A.U13.05 (per-CS init cost; CS pad state), A.U16.04 (FRAM API and caller rule), A.U16.20 + A.U20.10 (`max_size`
  legal set; the TOML names its part), A.U16.15 (partly protected status register), A.U16.R01 (WREN retried once),
  A.U16.R02 (three identification attempts), A.S0930.17/.30 (`quiesce()`, `erase_ready()`, `erase_chip()`), A.U36.546 (2)
  (`:1603-1604` chip facts move to M.6), A.U1.04 (dev bench facts live in `tests_hardware/README.md`; no SPEC edit).
- **Site**: `SPECIFICATION.md:1576-1605` (C.3.1).
- **Change**: (1) The synchronous-session bullet (`:1591-1598`) gains A.U13.05's two sentences, the bracketed measurement
  replaced by phase C's result when it exists (A.C.10), else the sentence ends "… only a board-level CS pull-up can meet
  it; `setup()` sets the level before it drives the pad". (2) The `_setup_addr_buffer()` bullet (`:1599-1605`):
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
  A.U36.546 moves the chip facts to M.6 in U36; until then the text stays in C.3.1.
- **Unit**: Stage 1 U13 ((1)); Stage 2 U16 ((2) attempts/legal set, (3)); Stage 3 U20 ((2) "names its part"); Stage 4
  S0930 per its unit ((3) erase API); Stage 5 U36 ((2) M.6 pointer).
- **Depends**: A.U13.05, A.U16.04, A.U16.15, A.U16.20, A.U16.R01, A.U16.R02, A.U20.10, A.S0930.17, M.SPEC[M.2-6].
- **Blast carried by**: BACKLOG `:52-57` deletion → A.U16.04 (DOCS); Part N rows for the attempts → A.U16.R02 (M.SPEC[N]).
- **Kind**: doc

### M.SPEC.050 C.3.2: the UART driver contract
- **From**: A.U0.40 L52 (`:1613`), A.U12.03 (zero-length payload), A.U13.18 (concurrent `deinit()` seen at the next
  `ready()` exit), A.U17.13 (`discarded_bytes`), A.U17.28 (masked sequences), A.U36.544 (3) (changelog label B15 goes,
  `:1622`), A.U14.14 Blast (points to F.1), A.SDEP.08 (C3), M_DOCS gap 1 (c) (two of BACKLOG's four UART findings).
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
  finding goes to J.9 and the shared-codec finding to G.2, M.SPEC[J], M.SPEC[G.2]).
- **Resolved**: A.U36.544 (3) drops changelog labels from permanent text; A.U17.28's rewrite of the same sentence makes
  the history parenthesis go with it (C2).
- **Unit**: Stage 1 U0 ((1)); Stage 2 U12/U13/U17 ((3), (2)); U36 (label, if still present; (5), before BACKLOG's entry
  leaves at U37).
- **Depends**: A.U12.03, A.U13.18, A.U17.13, A.U17.28, M.DOCS.065.
- **Blast carried by**: UART changelog entries → A.U17.* (SCR/DOCS per UCL rule).
- **Kind**: doc

### M.SPEC.051 C.4 and C.4.1: the reader contract, the loop skeleton, the ladder hooks
- **From**: A.U11.37 (logging form, `:1635-1637`), A.U18.39 (mask-string PUT rule, "U36 places it" in C.4), A.U15.43
  (reader tasks return `None`), A.U15.40 (4) (heading), A.U10.44 (starter/coroutine names), A.U10.R01 (driver skeleton:
  recovery hooks), A.U3.03 (failed read persists only the driver's entry), A.U3.06 (one entry per supervised task end),
  A.U2.22 Blast (`:1656` "`errno=10`"), A.U5.06 Blast (C.4 has no `:259-262`; nothing).
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
  sentence "One bounded bus fault is one restart" gains "and one SYSTEM entry (one entry per supervised task end)".
- **Resolved**: A.U11.37's form and A.U2.04's `_ERR_<NAME>` idiom are one sentence (A.U11.37 Depends A.U2.04). A.U18.39
  says "U36 places it": C.4 is the Home its register names; placed in U18 with the code (the rule is current at U18),
  since nothing in U36 moves C.4 (agent decision).
- **Unit**: Stage 1 U2 (codes); Stage 2 U3 ((4) entry); Stage 3 U10 ((2) names, (3) ladder hooks — A.U10.R01); Stage 4
  U11 ((1) form); Stage 5 U15 ((2) `None`, heading); U18 ((1) PUT rule).
- **Depends**: A.U2.04, A.U3.03, A.U3.06, A.U10.44, A.U10.R01, A.U11.37, A.U15.40, A.U15.43, A.U18.39, M.SPEC[N].
- **Blast carried by**: driver code → U15/U10 (SRC_SENS); G.2 ladder hooks → M.SPEC[G.2].
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
  (script guard; golden stored-config fixture), A.U20.12 (generated schemas linted), A.U3.05 (a failed config read is
  persisted by `ConfigManager` only), A.U11.21 (floats in stored form), A.U10.39 (`_cfg_schema` private), A.U10.29
  Blast (C.5 const pointer is U14's: the `const()`-wrapped-tuple sentence stays).
- **Site**: `SPECIFICATION.md:1708-1740` (C.5, C.5.1).
- **Change**: (1) `:1710-1711` → "`special` is a single sentinel value (an "unset" value outside the normal range, e.g.
  SCD30's `AmbPres=0` — deliberately outside it; the validation, not the schema, is what yields (owner-confirmed,
  2026-07-15, `1ed1c9a`: 'Confirmed with the project owner which side was wrong (the validation, not the schema …)'))
  or an in-range value with a documented meaning (SGP40's `BackupPeriod`/`BackupMaxAge`/`WaitTimeNTP` 0); a field with
  `default=None` and a single-value `special` is "special-alone" …" (rest of the sentence as at HEAD). (2) After the
  schema paragraph (`:1717`), two paragraphs: A.U15.42's "**`FiltCoeff` keeps two meanings** (owner, 2026-09-26): …"
  verbatim, then A.U36.538's "**Every config value has one explicit scope** (owner, 2026-07-13, as recorded in
  `144873f`: …)" verbatim. (3) `:1722-1725` (three defensive catches, "don't remove them") → A.U35.43 (3): "Type
  mismatches are rejected statically: `ConfigManager` catches only the runtime failures of its file and heap operations
  (the REST layer rejects a non-object body before it reaches a module)." followed by: "A float is validated, cached,
  staged and compared in the form the file reloads as, so an identical PUT after a reboot answers "Unchanged". A failed
  config read is persisted once, by `ConfigManager`; a caller prints its fallback line and runs on its documented
  fallback." (4) The hazard paragraph (`:1727-1730`) gains: "A device script constructing a `ConfigManager` over a
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
- **Unit**: Stage 1 U0 ((1) owner insertion); Stage 2 U3 ((3) caller rule); Stage 3 U10 ((7)); Stage 4 U11 ((3) float,
  (4), (5)); Stage 5 U15 ((1) in-range meanings, (2) `FiltCoeff`); Stage 6 U20 ((6)); Stage 7 U35 ((3) first sentence);
  Stage 8 U36 ((2) scope rule).
- **Depends**: A.U0.17, A.U3.05, A.U10.39, A.U11.21, A.U11.29, A.U11.33, A.U15.17, A.U15.42, A.U20.12, A.U35.43,
  A.U36.538, M.SRC_CORE.047.
- **Blast carried by**: BACKLOG `:478-480` → A.U15.42 (DOCS); H.5 special-value note → A.U15.17 (M.SPEC[H.5]).
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
- **Depends**: A.U4.01-.04, A.U10.25, A.U11.19, A.U11.24-.28, A.S0930.16, M.SPEC.008, M.SPEC[G.2].
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
  `handle_set_cmd(reader, data, cfg_vals, post_fct=None, post_asy_fct=None, ok_descr=None)` orchestrates
  `_set_dict_cfg()` plus one optional post-write hook (fires once per call, only if a field actually changed — one hook
  per endpoint, not one per field, as legacy's `post_fct`/`post_asy_fct` (agent, 2026-08-03)); a hook's failure reports
  its group's fields "Failed" inside the OK envelope. Build `data` from only the keys the client sent. A per-field
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
  "persist first, then push, and every setter returns `bool`" is not carried here (M.SPEC.055 (a)).
- **Unit**: Stage 1 U0 ((1) `res` rule); Stage 2 U10 ((2), (3)); Stage 3 U11/U19 ((1) catalog without 4/5/100, hook
  sentence, with 2/3 while `parse_cmd_request()` exists); Stage 4 U27 ((1) without 2/3); U32 ((1) hook reason).
- **Depends**: A.U10.42, A.U11.26, A.U19.15, A.U27.07, A.U32.03, M.SRC_CORE.073.
- **Blast carried by**: `api_response.py` comments → A.U32.03/A.U19.15 (SRC_CORE); A.8 envelope line → M.SPEC.021.
- **Kind**: doc

### M.SPEC.057 C.6: `make_dict()` reads fields by `getattr()`, one nested shape
- **From**: A.U11.35 (C.6 and `:5687-5688`), A.U10.36 (one config-dict shape), A.U0.40 (L55 label; folded).
- **Site**: `SPECIFICATION.md:1808-1814` (C.6); `:5687-5688` (J, carried in M.SPEC[J]).
- **Change**: C.6 → A.U11.35's paragraph verbatim, plus "Every module's config dict has the same nested shape `{<name>:
  {field: value}}`; no module returns a flat one."
- **Unit**: Stage 1 U10 (shape sentence); Stage 2 U11 (paragraph).
- **Depends**: A.U10.36, A.U11.34, A.U11.35.
- **Blast carried by**: `:5687-5688` → M.SPEC[J].
- **Kind**: doc

### M.SPEC.058 C.7: the error-handling and logging contract
- **From**: A.U5.01 (`LogConfig`, `make_logger(log, name)`), A.U16.01 (`:1818-1821` reflash pitfall), A.U26.22 (save,
  then clear; "SPEC C.7 is U36's"), A.U10.10 (every logger store set up in the boot batch), A.U10.11 (pre-setup entries
  survive setup), A.U16.17 (a declared FRAM chip that fails setup escalates), A.U16.06 (unreadable vs invalid chunk),
  A.U11.16 (allocation failure degrades to RAM-only), A.U11.31 + A.U19.14 (`ResetErrors` measurements dated; BACKLOG item
  32; its U33 repoint, M_DOCS gap 1 (b)), A.U2.14 (`W5, W4, W4` numbers, M.SPEC.008), A.U11.13 (an invalid level is refused), A.U11.15 (no level accessors;
  the `pr.level` attribute), A.U2.22 (numbering rules), A.U3.10 (one event, one entry; detecting layer), A.U2.04 + A.U11.37
  (idiom), A.U2.06 + A.U2.08 (`_error_check()` bullet; no dynamic numbering), A.U3.03 (a failed read persists only the
  driver's entry), A.U10.R01 (the recovery ladder), M_SRC_SENS GAP-15 (pre-sync `TS` excluded), A.U0.19 H1.02
  (`:1894-1897` DNSSRV), A.U18.36 (WIFI observation sites), A.U18.15 (UDP users check `disconnect()`), A.U18.09
  (resolver bounds), A.U13.16 + A.U10.22 (teardown returns `bool`), A.U30.19 + M_SRC_CORE GAP-G8 (`report_if_fatal()`
  in `asy_print_log`), A.U3.11 (pair scan), A.U35.37 (normal situations log nothing), A.U6.26 (no C.7 text), A.U14.19
  (nothing).
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
  after it — A.U3.10's: "**One occurrence persists one entry, error or warning, never both** (owner, 2026-09-26: 'Either
  it's a fault or a warning, but never both at a time'): the layer that detects a condition persists it; a caller above
  prints, unless it has its own later event (the give-up). An expected condition prints only: a normal situation never
  logs a code, and a test of one asserts no entry (owner, 2026-09-12, `8a45060`: 'no error/warning should ever be logged
  for expected startup jitter on any boot, on any module'). Every same-path pair of persisted calls in `src/` and
  generated code is checked by a scan, with an allow-list naming each pair's two events. A failed config read is
  persisted by `ConfigManager` only (C.5)." (8) `_error_check()` paragraph (`:1885-1890`) → "`_error_check(results,
  condition=True) -> bool` is the shared consecutive-failure counter every `read_loop()` calls once per cycle — `False`
  (give up, restart) once the streak exceeds `max_module_error`; it decrements on a good read and the count shows in the
  driver's `ErrCount`; a failed cycle prints, and only the give-up persists. Between the retry and the give-up it climbs
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
  same family — one paragraph (agent decision). (c) A.U2.22 removes the per-module dynamic `wrnno` text that A.U2.08 also
  removes — one deletion. (d) The boot-window history (`:1840-1846`) contradicts A.U10.10's end state (every store set up
  before the server answers) — replaced by A.U25.65's statement of the end-state behaviour (agent decision).
- **Unit**: Stage 1 U0 ((9)); Stage 2 U2 ((6), numbers); Stage 3 U3 ((7) first half, (8) failed read prints); Stage 4 U5
  ((1) `LogConfig`); Stage 5 U10 ((1) boot batch/pre-setup, (8) ladder, (10)); Stage 6 U11 ((1) degrade, (3), (4), (5));
  Stage 7 U16 ((1) pitfall, FRAM escalation, unreadable chunk); Stage 8 U18 ((10) UDP, (11) WIFI/resolver); Stage 9 U30
  ((11) `report_if_fatal()`); Stage 10 U35/U36 ((7) normal situations, (1) save primitive).
- **Depends**: A.U2.22, A.U3.03, A.U3.10, A.U3.11, A.U5.01, A.U10.10, A.U10.11, A.U10.R01, A.U11.13, A.U11.16,
  A.U11.31, A.U13.16, A.U16.01, A.U16.06, A.U16.17, A.U18.09, A.U18.15, A.U18.36, A.U19.14, A.U26.22, A.U30.19,
  A.U35.37, M.SRC_CORE.034, M.SRC_SENS.083.
- **Blast carried by**: CLAUDE.md FRAM rule → A.U26.22/A.U2.08 (DOCS); `digital_twin/README.md:503-507` → A.U25.65 (TWIN).
- **Kind**: doc

### M.SPEC.059 C.7.1: the band table and the catalog
- **From**: A.U2.22 (C.7.1 → band table + catalog pointer), A.U3.10 (repeat rule → the central rule), A.U2.01/A.U2.02
  Blasts (catalog file, catalog test), A.U0.40 L56 (`:1948`), A.U0.38 V48 (`:1949`), A.U3.08 (UART W10 console, W11 drain
  bound), A.U16.R03 (errno 54 row), A.U15.24 (W11 shared row), A.U18.06/A.U18.14/A.U2.09/A.U2.15/A.U2.19/A.U2.20/A.U3.09/
  A.U9.08/A.U16.15 (row texts — generated from the catalog, nothing hand-written), A.U36.544 item 29 (WIFI reason
  sentence), A.U18.36 (wrnno 36 text).
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
  the FRAM module never has FRAM logging of its own (owner)."; the UART decision "**`wrnno` W11 outranks W10** (owner,
  2026-09-18): a resync prints; the drain bound persists W11, so 'the peer never stopped sending' is what a field log
  carries"; the WIFI authentication code reads "authentication or handshake failed": cyw43 reports any failed AUTH event
  or key exchange as BADAUTH (`lib/cyw43-driver/src/cyw43_ctrl.c`), not proof of a wrong password; the no-logging layers
  "(owner, 2026-08-20, `c80d293`: no logging in these layers)" — the bus drivers, `asy_udp_socket.py`,
  `asy_dns_client.py`, `asy_uart_driver.py` (whose `cancel_unacknowledged` its owner reads and logs).
- **Resolved**: A.U0.40 L56 and A.U0.38 V48 tag rows that A.U2.22 deletes (U2, later): their tags survive in the kept
  statements (C8). A.U3.08's W10/W11 restatement replaces A.U2.22's quoted "W11 outranks W10 … persisted when the drain
  bound is hit". Catalog numbers in the statements are the catalog's (M.SPEC.008).
- **Unit**: Stage 1 U0 (tags on HEAD rows); Stage 2 U2 ((2)); Stage 3 U3 ((1), UART statement).
- **Depends**: A.U2.01, A.U2.02, A.U2.22, A.U3.08, A.U3.10.
- **Blast carried by**: per-row codes → the catalog file (GEN/A.U2.01); C.11 item 8, K.1, K.9 → M.SPEC[C.11], M.SPEC[K].
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
- **Depends**: A.U17.07, A.U17.21, A.U17.32, A.S0930.01, A.U18.10, A.U18.14, A.U18.19-.21, A.U18.47, A.U5.10, M.SPEC[A.11].
- **Blast carried by**: DEVICE_REFERENCE `NtpSynced` → A.U18.20/.21 (DOCS); L.3/L.4 lists → M.SPEC[L.3]/[L.4].
- **Kind**: doc

### M.SPEC.061 C.7.3: a failed config write costs persistence, never the config
- **From**: A.U11.20 (an unreadable file is never written that boot), A.U11.19 (a missing file is served from defaults
  and written by the first accepted change), A.U11.28 (write-count sentence), A.U11.21 (stored form, C.5), A.S0930.16
  (closed store), A.U2.07 (numbers), A.U0.37 V52 (`:1994` tag), A.U36.034 (CLAUDE.md points here), A.C.17 (power-loss
  result, phase C), A.U36.548 (G9/R11).
- **Site**: `SPECIFICATION.md:1986-2011` (C.7.3).
- **Change**: (1) First paragraph: "`setup()` runs on the file's good keys and the defaults for the rest when its
  create-or-repair write fails (errno 4)" → by catalog name; new sentences: "A missing file is served from defaults and
  written by the first accepted change; an unreadable one is served from defaults and never written this boot." "Before
  this, a failed setup write left the manager invalid: … (owner, 2026-09-24)." → "Were a failed setup write to leave the
  manager invalid, every reader's init would fail, the supervisor would reboot and every boot would repeat the write —
  a reboot loop writing the flash each pass (owner, 2026-09-24)." (2) Write-site list: "`setup()` writes at most once,
  only when the file is missing or needs repair" → "only when the file exists and needs repair"; "`_flush_staged()` writes
  once per accepted PUT that changes a value" → "once per accepted PUT that changes a value, after its pushes; a flush
  equal to the file writes nothing". (3) "**Bounded by boots …**" paragraph: "(owner, 2026-09-24)" → A.U0.37 V52's
  "(owner, 2026-09-24; the bound — each write once per explicit change or once per boot — confirmed by the owner,
  2026-09-26)" at `:1994`. (4) Phase C (A.C.17): the power-loss result is recorded in F.2's sentence, which this section
  cites ("A power cut during a write leaves a loadable file: F.2.").
- **Resolved**: A.U11.19 and A.U11.20 contradict HEAD's "missing" case of `setup()` — the end state (no write for a
  missing file) is theirs (M.SRC_CORE).
- **Unit**: Stage 1 U0 ((3)); Stage 2 U2 (codes); Stage 3 U11 ((1), (2)); phase C ((4) pointer once F.2 has the result).
- **Depends**: A.U11.19, A.U11.20, A.U11.28, A.C.17, M.SPEC[F.2].
- **Blast carried by**: CLAUDE.md flash-write rule → A.U36.034 (DOCS).
- **Kind**: doc

### M.SPEC.062 C.7.4: the radio's string bounds and shapes
- **From**: A.U14.37 (first sentence: raise types, cyw43 citations), A.U6.29 (host-label rule), A.U6.30 (country shape),
  A.U18.37 (GET shows the radio value in use), A.U18.38 (no change), A.U3.07 (`errno 17` number), A.U2.14 (codes),
  A.U26.20 (test only), A.U6.28 Blast (H.5 cross-reference, M.SPEC[H.5]), A.C.14 (unknown country code on silicon,
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
- **Unit**: Stage 1 U2 (codes); Stage 2 U6 ((2) shapes); Stage 3 U14 ((1)); Stage 4 U18 ((3)); U36 ((4)); phase C ((5)).
- **Depends**: A.U6.29, A.U6.30, A.U14.37, A.U18.37, A.C.14.
- **Blast carried by**: H.5 FieldDef `shape`/`bytes` → M.SPEC[H.5].
- **Kind**: doc

### M.SPEC.063 New C.7.5: the captive DNS answers
- **From**: A.U18.01 (creates the section; QTYPE rule, owner 2026-09-29), A.U18.02 (drop rule).
- **Site**: new `### C.7.5 Captive DNS` after C.7.4 (`:2027`), before C.8.
- **Change**: "`asy_captive_dns.py` answers every on-subnet A/ANY query with the AP's IP and every other type with an
  empty NOERROR reply (owner, 2026-09-29). A datagram that is a response (QR), declares other than one question, uses a
  compressed or reserved label or a name over 255 octets is dropped (agent, 2026-09-28); a reply is at most 287 B."
- **Unit**: U18.
- **Depends**: A.U18.01, A.U18.02.
- **Blast carried by**: A.5 `:331` → M.SPEC.018; `THIRD_PARTY_LICENSES.md:145-148` → A.U18.01/.02 (DOCS); I.4 → M.SPEC[I.4].
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
  scope paragraph (`:2041-2050`, "(owner's decision, 2026-09-18)") gains: "`setup()` and `set_write_protected()` take both
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
  A.U26.08, A.U26.09, A.U35.21, A.U36.015, M.SPEC[E.6].
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
  check); exactly one waiter per flag"), F.1 keeping only the platform fact. "A driver needing more than one rate
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
- **Depends**: A.U10.02, A.U10.03, A.U10.12, A.U10.14, A.U10.19, A.U10.28, A.U10.44, A.U15.41, A.U18.22-.24,
  M.SPEC[F.1], M.SPEC[G.2].
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
- **Depends**: A.U10.12, A.U10.13, A.U10.14, A.U11.39, A.U15.03, A.U31.17, A.C.07, M.SPEC[N].
- **Blast carried by**: A.7 boot-latency note → M.SPEC.020; `tests_hardware` spacing test → A.U26.41 (HW_BENCH).
- **Kind**: doc

### M.SPEC.068 C.10: typing conventions, stated once
- **From**: A.U36.534 (1) (C.10 rewrite), A.U15.02 (`cast()` sentence), A.U36.527 (the typing scheme lives here), A.U10.46 +
  A.U11.S02 + A.U15.43 (alias lists), A.U11.S01 → M_SRC_CORE GAP-G13 (per-kind validator sentence), A.U11.S03 / A.U19.17
  (no change).
- **Site**: `SPECIFICATION.md:2313-2321` (C.10).
- **Change**: A.U36.534 (1)'s text verbatim (its `print_log.py` example spelled `asy_print_log.py`, C7), followed by the
  aliases A.U10.46/A.U11.S02/A.U15.43 add as they land, and the sentence from GAP-G13: "A consumer that needs an `int`
  or a `float` calls the per-kind validator, which returns that type or `None`; it never narrows a validated value at
  runtime."
- **Resolved**: A.U11.S01's "narrows it with `type()`/`isinstance()`" is replaced by GAP-G13's sentence (lead's ruling).
- **Unit**: Stage 1 U10/U11/U15 (alias lines as each lands, appended to HEAD's C.10); Stage 2 U36 (rewrite carrying them).
- **Depends**: A.U10.46, A.U11.S02, A.U15.02, A.U15.43, A.U36.527, A.U36.534, M.SRC_CORE.047.
- **Blast carried by**: D.6 and CLAUDE.md → A.U36.534 (2)-(3) (M.SPEC[D], DOCS).
- **Kind**: doc

### M.SPEC.069 C.11 and C.11.1: design decisions; the conformance probe moves to K.5.1
- **From**: A.U36.039 (item 9; SPI clause to K.5), A.U36.516 (2) (dropped in favour of A.U36.039), A.U6.04 Blast (C.11
  `:2344-2346`), A.U2.22 Blast (item 8), A.U36.543 (4) (C.11.1 → K.5.1; its closing paragraph stays as C.11's), A.U26.66
  (conformance probes for every bus chip; the probe file name).
- **Site**: `SPECIFICATION.md:2323-2366`.
- **Change**: item 8 → "**Errno/wrnno numbering**: take numbers from the catalog's bands (C.7, C.7.1)."; item 9 → A.U36.039's
  text verbatim; C.11.1 (`:2348-2366`) moves to K.5.1 (M.SPEC[K]) with A.U26.66's body; C.11 closes with the kept
  paragraph "**Chip-specific facts go to Part M, not here.** …".
- **Resolved**: A.U36.039 and A.U36.516 (2) rewrite the same sentences ("not both") — A.U36.039's item 9 carries the V28
  clause; A.U36.516 (2) itself says "carried by part A's A.U36.039 … not re-planned here".
- **Unit**: Stage 1 U2 (item 8); Stage 2 U36 (item 9, the move).
- **Depends**: A.U2.22, A.U36.039, A.U36.543, M.SPEC[K].
- **Blast carried by**: K.5 SPI sentence → A.U36.039 (M.SPEC[K]); `tests_hardware/README.md:404-415` → A.U26.66 (HW).
- **Kind**: doc

### M.SPEC.070 C.12 and C.13: fault injection; one readiness and teardown contract
- **From**: A.U14.14 (C.12 sentence), A.U24.21/A.U25.17 (C.12 is U14's), A.U10.21 (one `setup()` contract), A.U10.22 (checks
  named), A.U13.16 (I2C/SPI `deinit()` return bool), A.U5.06 (no staged variant), A.U10.38 (names).
- **Site**: `SPECIFICATION.md:2368-2391`.
- **Change**: (1) C.12 last sentence → A.U14.14's ("For fault injection, the fakes raise exactly what rp2 raises (F.1):
  `EIO`/`ETIMEDOUT` from an I2C transfer, `ENODEV` only from a NAKed zero-length probe, nothing from `scan()`, and UART
  faults as sentinels, never exceptions."). (2) C.13: "(proven first by `FRAM_SPI`/`SPIDevice`; standard for
  `ConfigManager`, `NotificationCoordinator`'s staged variant)" → "(proven first by `FRAM_SPI`/`SPIDevice`; standard for
  `ConfigManager`)"; after the gate sentence: "**One contract**: `async def setup(self) -> bool`, no parameters — `True` =
  ready, `False` = degraded (already logged by the object); a protocol-layer setup keeps its documented raise for a chip
  that fails identification, which its reader's init catches. A class whose constructor refused persists that code in
  `setup()` and returns `False`."; closing: "Every class's gate (a call before `setup()` or after a failed one answers as
  its contract says) and every teardown result is checked by a test (`tests/`)."
- **Unit**: Stage 1 U10 ((2)); Stage 2 U13 (teardown list in C.7, M.SPEC.058); Stage 3 U14 ((1)); U5 (staged variant goes).
- **Depends**: A.U5.06, A.U10.21, A.U10.22, A.U13.16, A.U14.14, M.SPEC[F.1].
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
  its tag live in L.6.4 (M.SPEC[L.6.4]) — C8.
- **Unit**: Stage 1 U0 ((4), L12 on HEAD text); Stage 2 U5 ((3), (5) edges, (7) signals); Stage 3 U10 (names); Stage 4
  U16 ((5) layout clause, A.U16.01); Stage 5 U36 ((1), (2), (6), (7) count and labels).
- **Depends**: A.U5.03, A.U5.06, A.U5.07, A.U5.11, A.U16.01, A.U36.511, A.U36.514, M.SPEC[L.6.4], M.SPEC.020.
- **Blast carried by**: test comments citing C.14.3 → A.U36.513 (TEST_UNIT); L.2/L.3/L.6.4 → M.SPEC[L.*].
- **Kind**: doc

## SPECIFICATION.md — Part D (`:2589-2743`)

### M.SPEC.073 Part D: heading, intro; D.0, D.13, D.14, D.16 move to Part K
- **From**: A.U36.543 (7) (heading, intro, removals; D.8 sentence), A.U36.540 (3) (D.0's new sentence, landing in K.1),
  A.U36.532 (numbering: Part D numbers ascend with gaps).
- **Site**: `SPECIFICATION.md:2589-2600`, `:2720-2728`, `:2739-2741`.
- **Change**: A.U36.543 (7) verbatim: heading "# Part D — `src/` quality bar"; intro "The bar every file in `src/` and
  every generated module meets: … Part K's step K.2 applies it; Part C gives a driver's shape."; D.0 (with A.U36.540
  (3)'s rewrite), D.13, D.14 and D.16 removed (their content lands in K.1, K.10, K.11, M.SPEC[K]); D.1-D.12 and D.15 keep
  their numbers.
- **Resolved**: A.U36.540 (3) rewrites D.0's sentence in place, and A.U36.543 (2) moves D.0 to K.1 "followed by A.U36.540
  (3)'s D.0 sentence" — the rewritten sentence lands in K.1 only (A.U36.540 itself says so).
- **Unit**: U36.
- **Depends**: A.U36.540, A.U36.543, M.SPEC[K], M.SPEC.003.
- **Blast carried by**: the `.claude/skills/integrate-module/SKILL.md` → A.U36.543 (9) (DOCS); TOC → M.SPEC.001.
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
  A.U10.32 (D.15 rewrite), A.SDEP.08 (D.9 pin token).
- **Site**: `SPECIFICATION.md:2647-2737`.
- **Change**: (1) D.6 → A.U36.534 (2)'s text ("Type-hint every parameter and return, not over- or under-typed; the idiom
  and its reasons are C.10. **`mpy-cross` does not dead-code-eliminate …** (B.11).") followed by the quoting paragraph:
  "**Quoting annotations** (owner decision, 2026-09-24): quote an annotation only when it names something imported under
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
  is Part E's (M.SPEC[E]). (7) D.15 → A.U10.32's rewrite (roles, alphabetical within a role, dunders, the restored
  "**'Starter' is a role, not a name** (owner, 2026-09-14)" paragraph with `Calibrate`, scope, the import-time exception).
- **Resolved**: A.U10.31's own D.6 sentence ("existing files are not mass-edited" → "every file follows it") lands in U10
  on HEAD's D.6, and A.U36.534 (2) (U36) rewrites the paragraph above it — the quoting paragraph keeps A.U10.31's
  wording (A.U36.534 says "the quoting paragraph `:2658-2661` is A.U10.31's"). A.U28.30 and A.U28.27 both say "U36" for
  their D.6 sentences — placed in U28 with the check (the rule is current then; agent decision).
- **Unit**: Stage 1 U5 ((4) config objects, ceilings); Stage 2 U10 ((1) quoting, (4) raise form, (7)); Stage 3 U28 ((1)
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
- **Unit**: Stage 1 U7 ((2) missing build, (3) run record, (7)); Stage 2 U8 ((3) probe); Stage 3 U21 ((3) lock, (6));
  Stage 4 U24 ((4), (5)); Stage 5 U27 ((2) shipped form, (7) twin runner, M.SCR.017's port-53 sentence); U35 ((3)
  dispatch check); U0 ((8) if A.SDEP.16 (c)); U2 ((2) catalog).
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
  / "test standard" each names — no action creates it: gap fill), M_TEST_HELP GAP-H5 (the deleted library's citers).
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
  logic."; `:2836-2839` → A.U36.016's paragraph verbatim. New closing paragraph (A.U24.75): "Every `buildgen/` module has
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
  sleep to one yield."
- **Resolved**: (a) A.U24.65 (generic `PER_DEVICE` file for the concurrency library) vs A.U25.46 (library retired
  host-side) — A.U25.46 kept (M.TEST_HELP.033, M.SCR.017). (b) Several actions name "SPEC E hygiene section"/"test
  standard" written by "U36", yet no U36 action writes it — created here from their texts (agent decision, OR2.c).
- **Unit**: Stage 1 U7 ((1) skip/empty); Stage 2 U24 ((1) rest, (2) per-device runs, buildgen homes, (4) hygiene
  sentences); Stage 3 U25 ((2) concurrency row); Stage 4 U35 ((4) bite list, driven time); Stage 5 U36 ((2) A.U36.016,
  labels; (3)).
- **Depends**: A.U7.07, A.U24.03, A.U24.04, A.U24.07, A.U24.08, A.U24.65, A.U24.75, A.U24.76, A.U25.46, A.U26.15,
  A.U35.03, A.U35.10, A.U36.016, A.U36.017, M.TEST_HELP.033.
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
- **Depends**: A.U7.04, A.U7.06, A.U8.15, A.U8C2.08, A.U24.65, A.U27.14, A.U35.23, M.SPEC[N].
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
  (`RegionBuffer.buf`, `FRAMManager`); entries the table removes leave the text, and "That pass left **31 genuinely
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
  A.U0.44 L61 (`:3108-3109`, `:3190-3191`), A.U36.548 (G9/R11).
- **Site**: `SPECIFICATION.md:3103-3193`.
- **Change**: (1) E.6 intro: `:3108-3109` "— don't force further sharing onto genuinely backend-specific coverage." →
  "— further sharing is not forced onto genuinely backend-specific coverage (agent, 2026-09-04, `8080538`)."; the
  `tests_hardware/` paragraph uses the level names (L3 flash, L4 bench); "Both tiers run clean end to end on real
  hardware; the earlier WiFi-reconnection flakiness this section used to flag is root-caused and mitigated" → "L3 and L4
  run end to end on the bench (`tests_hardware/README.md`'s 'Known assumptions and open findings')"; new sentence: "Every
  L3/L4 module is collectible with nothing attached under every option, checked at L0." (2) E.6.1 → A.U7.01's level
  table and its containment paragraph verbatim, followed by A.U36.007's slot text; the "**Credential rotation is
  deliberately not a bench capability** (owner decision, 2026-09-22)" paragraph keeps its decision and reason without
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
  script takes every board fact from `BENCH`, one rendered dict (`tests_hardware/`)."
- **Unit**: Stage 1 U0 ((1), (6) tags); Stage 2 U7 ((2) table, (3), (4) run record); Stage 3 U25/U26 ((6) pointers, (1)
  collectible); Stage 4 U27 ((4) `-m`); Stage 5 U36 ((2) slot, (4) A.U36.009, history).
- **Depends**: A.U7.01, A.U7.14, A.U7.18, A.U7.24, A.U7.25, A.U25.01, A.U26.31, A.U26.44, A.U27.19, A.U36.007, A.U36.009.
- **Blast carried by**: README hardware table → A.U7.01/A.U36.008 (DOCS); `tests_hardware/README.md` → A.U7.18/A.U26.* (HW).
- **Kind**: doc

### M.SPEC.083 E.6.6: the one level-containment exception list
- **From**: A.U7.25 (E.6.6 → the table, rows 1-10), A.U4.07 (the SCD30 text correction runs first; no row), A.U0.38 V03/V31
  /V33 (carried by A.U7.25's rows 1 and 3), A.U36.028 (`uart-fault-catalog` wording), A.U36.045 (`bmp3xx-general-call`),
  A.U26.28 (boot-failure code row), A.C.12 (replaces it with the silicon attempt's result), A.U26.39 (`hotspot-multi-client`),
  A.U26.34 (recovery rungs without L3/L4), A.U26.56 (off-subnet spoof attempt result), A.U26.51 + M_PROC gap 2 (rows for
  twin scenarios without a counterpart; `COVERS_TWIN_SCENARIOS`), A.U35.21 (lone BMP3XX row is L4 only — A.U36.045),
  A.U26.86 (THR wording; no SPEC edit beyond A.U36.028), A.U36.512 (3) (`:3213` "variant"), M_HW_DEV (`sgp40-general-call`
  no L4, A.U7.25 row 2).
- **Site**: `SPECIFICATION.md:3195-3237` (E.6.6).
- **Change**: heading "### E.6.6 Level-containment exceptions"; the opening rule paragraph keeps the owner's standing rule
  with "(owner, 2026-09-26)" and A.U7.01's containment wording, "C.8 is an instance of this rule"; the four numbered
  exceptions become one table `| ID | Scenario/behaviour | Missing level(s) | Reason | Decided | Reviewed at close |`
  read by `tests_scripts/test_level_containment.py`, with rows: `dev-only-bench` (owner, 2026-09-03); `sgp40-general-call`
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
  M.SPEC[H.8].
- **Kind**: doc
