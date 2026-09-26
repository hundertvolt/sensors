# Requirement merge — clusters and owner-attribution coverage (HEAD, 2026-09-26)

Read with OR54-OR58 (recorded after this merge ran): a test may measure in the statement after
`gc.collect()` (OR55.a); one event logs one entry (OR56.a (1)); FRAM layout is fixed per build only
(OR56.a (3)); legacy parity is with intent (OR57.a); no legacy REST path stays (OR58.a).

Inputs: `audit/hreq/G1.md` … `G10.md` (965 candidates), their brief `audit/sweeps/hreq_prompt.md`, the owner rows OR1-OR55 (`PROJECT_AUDIT_PLAN.md` 3.2) and the 206 owner-attribution lines supplied with this task. Read-only pass: nothing in the tree was changed; three facts were re-checked at HEAD where members disagreed (`asy_webserver_service.py:463-469` with `api_response.py:81-105`, `src/voc_algorithm.py:1-5`, `py/parse.c:369-392` in the v1.29.0 checkout).

Method: every candidate's full text (Req, Provenance, Truth, Fit) was read and grouped by the rule it states, across groups and within a group. A cluster holds candidates stating the same rule, or one rule and its direct refinements; each merged **Req** keeps every member's specific content. **Provenance** is the strongest member (O > O-confirmed > F > A > C) with that member's evidence; **Truth** is the worst member (wrong > drifted/stale > partly > unverifiable > not checked > holds) with what diverges, the other members' levels listed after it. **Note** lines record contradictions between members and their resolution.

## Task 1 — cross-group clusters

213 clusters covering 596 candidates (194 span two or more groups); singletons listed after the last cluster.

### HR001 Tick arithmetic is wrap-safe on rp2
- **Req**: Every elapsed-time and deadline computation on `ticks_ms()` values uses `ticks_diff()`/`ticks_add()`, never raw subtraction, and holds across rp2's 2**30 ms wrap (~12.4 days). A stored tick or deadline is compared only within `ticks_diff()`'s 2**29 ms (~6.2 day) horizon or cleared before it ages past it, a flag that keeps a deadline alive until a later event also expires by elapsed time, and each stored-tick site states why it cannot outlive a wrap. Because the Unix port's period is 2**62, wrap safety is proven by a source scan over every tick user (`src/` and generated code) plus period-parametric code, and a test that names a rollover uses the target's period and actually crosses one.
- **Members**: G2.049, G4.037, G5.086, G6.018
- **Provenance**: F — G2.049: v1.29.0 `py/mpconfig.h:1925` period = `MP_SMALL_INT_POSITIVE_MASK + 1`, `extmod/modtime.c:152`
- **Truth**: partly — G2.049: `_KNOWN_TICKS_USERS` enforced both ways; the subtraction scan is per-line over `src/` only (not generated modules or `digital_twin/`); `test_asy_uart_comm.py:748-756` names the 2**30 rollover but only sets a deadline 1 ms in the past (others: G4.037 partly, G5.086 partly, G6.018 partly)
- **Fit / pillar**: refines P1 (OR44.a counter wrap); refines OR44.a P1 (counter wrap); extends P1 (counter wrap) · pillar P1 (all members)

### HR002 Every MicroPython pin move triggers the re-check
- **Req**: `toolchain/versions.toml`'s `[micropython] ref` is the refactor's only MicroPython pin. Any path that builds or pins another version (`--latest`, `--micropython-ref`, a hand edit) triggers the platform re-check: every Part F fact, upstream file:line citation, override anchor (Part B.14) and the stub version are re-verified against the new tag's source, each construct is asked whether a newer or better way exists, ruled-out items (e.g. `getaddrinfo()` timeout support) are re-checked rather than carried, and the built ref is recorded where a build can be traced to it.
- **Members**: G4.001, G8.047
- **Provenance**: O — G8.047: CLAUDE.md "Platform target" standing practice ("repeat it every time `toolchain/versions.toml`'s MicroPython `ref` moves"); the gap is C
- **Truth**: partly — G4.001: pin is `v1.29.0` (versions.toml:10; CONSOLIDATION 6: still latest); nothing enforces the re-check: `setup_toolchain.py --latest`/`write_micropython_ref()` move the pin without prompting it (TOOL.T12); citations such as `modlwip.c:802`, `runtime.c:1692/1696`, `gc.c:891` hold at v1.29.0 (checked) (others: G8.047 partly)
- **Fit / pillar**: refines OR29.a (2); refines CLAUDE.md platform practice · pillars differ: G4.001 P1, G8.047 process

### HR003 Verify tool versions after a uv.lock merge
- **Req**: After any merge that touches `uv.lock`, `uv sync` is run and the installed ruff and mypy versions are compared with `pyproject.toml`'s pins, and `uv lock` is re-run if they differ; `uv lock --check` alone is never trusted as proof.
- **Members**: G8.116, G9.043
- **Provenance**: F — G8.116: measured 2026-09-10 (lock read `specifier ==0.15.21` next to `version 0.16.6`, `uv lock --check` passed); rule A `dd38176`
- **Truth**: unverifiable — G8.116: review-only; CI's `uv sync` without `--locked` would not catch it either (others: G9.043 holds)
- **Fit / pillar**: extends OR7 (coherent merges); extends OR6 · pillar process (all members)

### HR004 Clean-chroot check: periodic, owner-run, two compilers
- **Req**: Every change to the build environment (`pyproject.toml`, `scripts/`, `toolchain/`, CI config) is recorded in BACKLOG.md's running chroot list. The owner runs the clean-chroot verification periodically on Ubuntu 24.04 (GCC 13) and Debian trixie (GCC 14), plus a separate full-installer leg for `toolchain/` changes; a session whose sandbox can build a chroot runs it too, and no document calls it a pre-push gate. The ARM cross-compiler and apt packages stay unpinned from the distro because the two legs cover compiler drift; the recipe enables `universe`, installs `sudo` and `libcap2-bin`, and uses the ports mirror on arm64.
- **Members**: G8.059, G8.070, G9.035
- **Provenance**: O — G8.059: CLAUDE.md:861 "Owner decision, 2026-09-18: this is a periodic check the project owner runs manually"; BACKLOG:515 "settled (owner decision, 2026-09-18)"
- **Truth**: drifted — G8.059: the list omits changed files (TOOL.N155: `_generate_sensortask_modules.py`, `cross_browser_smoke.mjs`, `_render_coverage.py`, `build_website.sh`, hardware runners, `zizmor.yml`, `action.yml` since 2026-09-13); legs last satisfied 2026-09-12; `libcap2-bin` is in both `versions.toml:26-28` and the … (others: G8.070 partly, G9.035 drifted)
- **Fit / pillar**: extends OR50.a (2) (chroot list), P9; extends G8.059; extends OR50.a (2) (BACKLOG chroot entry) · pillar process (all members)

### HR005 Pull requests: proactive, described, watched
- **Req**: A session may open a pull request at any time without asking, and finishing work on a branch always opens one with a description of what changed and why; the session subscribes to its activity right after opening it. During the audit there is one branch and one PR (#107), and PR/CI watching uses event hooks only, no timed checks.
- **Members**: G8.131, G9.036
- **Provenance**: O — G8.131: CLAUDE.md:1043 "explicitly authorized … Confirmed directly by the project owner"; plan 3.1 owner record (2026-09-26)
- **Truth**: holds — G8.131: practice; one recorded owner instruction to stop watching a branch (`27e97e1`) (others: G9.036 holds)
- **Fit / pillar**: restates OR6.a; restates PQ2 answer · pillar process (all members)

### HR006 UART C-port changelog: every change, until reconciliation
- **Req**: Every change to `asy_uart_comm.py`'s wire constants, accept/reject rules or recovery timings is recorded in `UART_C_PORT_CHANGELOG.md` as Class A (mirror in C) or Class B (no C impact), both logged, with a status from the file's own closed vocabulary; a change to any `const()` wire constant or recovery timing is Class A by definition. The file stays in the repo past the audit and is deleted only once the C side is reconciled.
- **Members**: G6.002, G6.006, G9.033
- **Provenance**: O — G6.006: OR5.a (1) "`UART_C_PORT_CHANGELOG.md` stays until the C side is reconciled"; OR11.a (1)
- **Truth**: drifted — G6.002: `UART_C_PORT_CHANGELOG.md:27` scopes it to "every change to the module during its `src/` promotion", CLAUDE.md to every change; no test or hook checks that a `const()` change has an entry (only three files name the changelog) (others: G6.006 holds, G9.033 partly)
- **Fit / pillar**: extends OR24.a (2) (UART wire format untouched in the audit); restates OR5.a (1), OR11.a · process; restates OR11.a · pillars differ: G6.002 P8, G6.006 ?, G9.033 process

### HR007 arduino/ is out of scope and documented so
- **Req**: The Arduino C implementation is out of scope: no audit work reads, verifies or reconciles `arduino/`, which stays at the root as the post-audit reconciliation reference outside every lint, test and licence review, and README.md and THIRD_PARTY_LICENSES.md state that exclusion. C-side conformance is never assumed; each Class A changelog entry states what the reconciliation must check; with no C device in the field an entry is an obligation to record, not a deployment risk; hardware tests prove Python-to-Python interoperation only.
- **Members**: G6.005, G9.051
- **Provenance**: O — G6.005: "outside this project's scope (owner, 2026-09-24)"; "prototypical ... (owner, 2026-09-11)"; OR5.a (3)
- **Truth**: partly — G9.051: SPEC A.1 states it; README's licence paragraph and THIRD_PARTY_LICENSES.md do not. (others: G6.005 holds)
- **Fit / pillar**: restates OR5.a (3) · process; restates OR5.a (3) · pillars differ: G6.005 ?, G9.051 process

### HR008 The legacy tree is reference-only
- **Req**: `python/`, `modules/`, `html_raw/`, the four `build-*.sh`, `update_and_install.txt` (the legacy build's own manual recipe) and `dev_legacy/`'s old driver copies are read, never worked on: no lint, type, test, CI, cleanup or completion scope, and no document frames covering them as open work; a finding about them is recorded only when it explains current behaviour. They move unchanged into `legacy/` (OR32.a) and stay listed in the doc map.
- **Members**: G9.050, G9.054
- **Provenance**: O — G9.054: "(project owner, 2026-09-11)"; OR32/OR32.a.
- **Truth**: drifted — G9.050: BACKLOG.md:878-882 still lists completing it as open work; OR32.a (1)'s legacy list does not name the file (resolved by its content: it is the legacy build's own recipe). (others: G9.054 drifted)
- **Fit / pillar**: refines OR32.a (1); restates OR32.a · pillars differ: G9.050 P8, G9.054 process

### HR009 Legacy _boot.py import stays untouched
- **Req**: `modules/_boot.py`'s literal `import sensortask.py` is never changed without real-hardware testing on the deployed MicroPython version, and the legacy boot path is never exercised on silicon (the bench flashes only the refactored build); the move into `legacy/` keeps the file byte-identical.
- **Members**: G1.023, G9.056
- **Provenance**: O — G1.023: CLAUDE.md "The legacy tree is reference-only, forever" (project owner, 2026-09-11)
- **Truth**: holds — G1.023: holds (others: G9.056 holds)
- **Fit / pillar**: restates CLAUDE.md; restates CLAUDE.md hard rule, OR32.a (2) · pillars differ: G1.023 process, G9.056 P9

### HR010 Behaviour and features change only with proof
- **Req**: The refactored firmware keeps the deployed units' top-level features: it is more consistent and stable, not a feature change, and any removed feature is an owner decision. A general improvement keeps observable behaviour identical for every valid input with the full suite passing unchanged; a formula or behaviour discrepancy found in verification is never changed silently but follows OR12.a (proof from datasheet or specification, a regression test, logged for the owner).
- **Members**: G5.081, G9.052
- **Provenance**: O — G5.081: OR12/OR12.a (owner, 2026-09-25); D.1's "flag and ask" is CLAUDE.md's owner rule
- **Truth**: partly — G9.052: the parity checks below hold for bounds, wiring, WiFi, supervisor and NTP; losses found: G9.068 (SGP40 NTP wait 0), G9.063 (SCD30 compare, in intent). (others: G5.081 holds)
- **Fit / pillar**: restates OR12.a · pillars differ: G5.081 process, G9.052 P4

### HR011 Consistency changes directly; behaviour changes flagged
- **Req**: Every member of a related set takes the same shape (names, order, optionality, signatures, return convention, uniform behaviour of equivalent code). Before writing something new the Part G catalog and the wider tree are searched for an existing primitive, a new primitive joins G.2 in the same change, and the G.3 grep-for-the-shape scan runs whenever a file enters `src/`, generated modules included. A cross-file consistency discrepancy is changed directly and logged (OR24.a), while a formula or behaviour discrepancy or an architecturally significant decision is flagged to the owner before anything changes.
- **Members**: G5.082, G9.018
- **Provenance**: O — G5.082: OR24/OR24.a (owner, 2026-09-25: "Change, don't flag"); the scan rule in CLAUDE.md is an owner hard rule
- **Truth**: drifted — G5.082: D.10 ("flag a questionable existing convention rather than silently diverging") and CLAUDE.md ("do not silently fix it. Report it and discuss") still state flag-and-discuss, which OR24.a overrides for consistency changes; no tool runs the scan; generated `sensortask_<device>.py` never "moves into … (others: G9.018 drifted)
- **Fit / pillar**: restates OR24.a, OR44.a (3); conflicts CLAUDE.md:88-91 with OR24.a (1) (resolved: OR24.a is the later owner ruling) · pillars differ: G5.082 P4, G9.018 process
- **Note**: Both members say the same; both record that CLAUDE.md/D.10 still say flag-first for every discrepancy — resolved by OR24.a (later owner ruling).

### HR012 One central repeat rule protects every error ring
- **Req**: A code identical to the newest entry of a logger's history spends no new ring slot; it is still counted, printed and written through, for every logger (RAM- or FRAM-backed) whatever the fault's origin. This central `print_log.py` rule, not per-module caps or episode flags, protects the ten-slot ring: a module that fails every cycle keeps logging every failure (no escalation cap, `max_module_error = 0`, the notification monitor never gives up), and the per-module episode mechanisms (`repeat=` in FRAM manager, UART, WIFI, NTP, NOTIFY, SGP40; UART's one-errno-one-warning episode budget with W11 over W10, W12 only on repeat, W13 on a cancel-counter rise; SGP40's one W13 per NTP outage) go once the central rule covers them. Sites that today persist per occurrence (NTP 16/17/18, captive DNS W1/W2, webserver reclaim warnings, WiFi byte-bound refusal) come under it.
- **Members**: G3.065, G3.066, G5.025, G6.022, G6.045
- **Provenance**: O — G5.025: OR35.a/OR35.b (owner, 2026-09-26: "just don't repeat the same error in the slots. Pure and simple")
- **Truth**: drifted — G5.025: not implemented: `_store_err()` dedupes only on a caller's `repeat=True` (`print_log.py:167`); `repeat=` is set by 6 modules (grep); C.7.1 text says "Three modules therefore dedupe" while its own table rows add NTP, NOTIFY and SGP40; C.7.1 says a chunk "logs into its OWNER's FRAM-backed history", … (others: G3.065 holds, G3.066 holds, G6.022 drifted, G6.045 partly)
- **Fit / pillar**: restates OR35.b; superseded by OR35.a (4)/OR35.b; conflicts OR35.b (one central rule in `print_log.py`, no per-module episode cases; see Conflicts) · pillars differ: G3.065 P7, G3.066 P7, G5.025 P1, P7, G6.022 P7, G6.045 P7
- **Note**: G6.022 states UART's own per-episode budget (partly owner-decided W11-over-W10, 2026-09-18) as a requirement and conflicts with OR35.b's single central rule; G3.066 is explicitly interim. Resolved by provenance: OR35.a/OR35.b (owner, 2026-09-26) is later and supersedes the per-module episode rules.

### HR013 Expected conditions log nothing; tolerated codes justified
- **Req**: No error or warning is logged for an expected, routine condition on any boot or in normal operation (startup jitter, a first boot's missing config file, a command-only schema with no stored values), and a test of a normal situation never accepts or expects a logged `errno`/`wrnno`. Where a hardware test does tolerate a specific code, or deliberately asserts nothing about a log, it states in place why that code cannot indicate a real fault in this scenario or why no groundable entry exists.
- **Members**: G1.053, G5.029
- **Provenance**: O-confirmed — G1.053: OR18 ("tests for normal situations [that] accept or even expect log entries for wrnno or errno" are a hint of a bad pattern)
- **Truth**: partly — G5.029: never written as a standing rule in CLAUDE.md/SPECIFICATION.md (only SGP40's fix at C.14.2); `ConfigManager.setup()` persists `wrnno` 3 "Config file … not found" on every first boot and `wrnno` 6 for a command-only schema (`config_manager.py:426,472`), and … (others: G1.053 holds)
- **Fit / pillar**: refines OR18; restates OR18 (hint) and extends P1 · pillars differ: G1.053 P2/P5, G5.029 P1, P7

### HR014 dev is the flashed rig; wozi never flashed
- **Req**: Only a `dev` build of the tree under test, always from `devices/dev.toml`, is ever flashed or bench-tested; `wozi` is the exemplary base variant, never flashed, proven by the unit and twin tiers, and a dev-bench pass counts for wozi only for code under test in its dev-native configuration. Quirks of the legacy dev build are out of scope as bugs, while the refactored `dev` device meets the same bar as every other device. The ISL29125 and the UART link are dev-only: dev wires exactly one initiator and one responder `uart_link` (UART0 GP0/GP1, UART1 GP8/GP9) across its permanent crossover jumper (GP0-GP9, GP1-GP8), each with its own FRAM-backed history, only the initiator reports transfer/failure counts, command ids are bench application semantics, GPIO16/17 stay free for a future BSEC UART0, and wozi gets no UART instance. `uart_link` is the one non-singleton service driver; every other service driver is a singleton resolved through `driver_registry._OVERRIDES`.
- **Members**: G1.022, G1.098, G6.037, G8.030, G9.047
- **Provenance**: O — G6.037: CLAUDE.md hard rules (wozi never flashed); changelog B31 reverses an earlier agent "never"
- **Truth**: partly — G9.047: the example describes legacy `modules/sensortask-dev.py:89-104, 428`; the refactored `devices/dev.toml:122` instantiates `neopixel`, so the example no longer applies to `src/`. (others: G1.022 holds, G1.098 holds, G6.037 holds, G8.030 holds)
- **Fit / pillar**: restates CLAUDE.md hard rule; restates CLAUDE.md; restates CLAUDE.md wozi/dev rules; restates CLAUDE.md; refines OR36.a (2); refines OR36.a (2) · pillars differ: G1.022 P9, G1.098 P8, G6.037 P10, G8.030 process, G9.047 P4

### HR015 Radio identity strings bounded in bytes everywhere
- **Req**: SSID, PW, Country, Hostname and HotspotPW are bounded in UTF-8 bytes, never characters or UTF-16 units: SSID at most 32, PW 8-63 (or "" for an open network), country exactly 2, hostname at most 32. The limits are checked before any `network` call, at PUT (`"Invalid"`, errno 20), at use (a stored over-bound value runs on its default, wrnno 8; an over-long SSID never reaches `connect()`), at build time for the TOML-injected `hostname`/`hotspot_password` defaults, and identically in fakes, the website hint, client check and mock. A TOML hostname or hotspot password is only the default of a ConfigManager-persisted field, so a value stored through the web UI survives a reflash whose TOML says otherwise, and runtime keeps a default rather than failing to boot.
- **Members**: G4.042, G6.055, G6.068, G7.086, G8.025
- **Provenance**: O — G8.025: BACKLOG.md "`[device].name`/`hostname`/`hotspot_password` are wired into the boot path now - done (owner decision, 2026-09-18)"; bounds F: `extmod/modnetwork.h:60` `MICROPY_PY_NETWORK_HOSTNAME_MAX_LEN (32)` at v1.29.0, `modnetwork.c:157`
- **Truth**: wrong — G7.086: `mock-server.js:59-61` compares `value.length` (UTF-16 units) and `templates.js:27-28` says "characters", while `asy_wifi_service.py:82` checks `len(value.encode())`; C.7.4 itself says "the web UI mirrors" the character bound. (others: G4.042 partly, G6.055 holds, G6.068 holds, G8.025 holds)
- **Fit / pillar**: refines OR43.a (1) (ranges from datasheets); refines OR18 (a config value never treated as a hardware fault); refines OR52.a (2) (stored config is a public interface); restates G.1 applied to C.7.4; extends P1 (no silent identity loss), OR52.a (2) · pillars differ: G4.042 P2, G6.055 P2, G6.068 P1, G7.086 P8, G8.025 P1
- **Note**: G4.042 gives the WPA2 passphrase as 8-64 bytes; G6.055/G8.025 give 8-63. 64 is the hex-PSK form; the code bounds 8..63 (`validate.py:116`, `asy_wifi_service.py:48,53`). Resolved to 8-63 by code and the higher-provenance members.

### HR016 SGP40 VOC backup keeps legacy semantics
- **Req**: SGP40 backs up the VOC state to FRAM once per `BackupPeriod` minutes (0 = off) and verifies it about once an hour of backups; on boot it waits up to `WaitTimeNTP` seconds (capped at 600) for NTP before restoring, where `WaitTimeNTP = 0` means restore once immediately (never 'no restore'); a backup older than `BackupMaxAge` is rejected (0 = no age limit), the age check is skipped when NTP never syncs, an untimestamped backup is written once the wait expires, and the 45-sample VOC blackout is skipped after a restore. The '0 means' semantics live in the schema and docs, not only in `@web` text.
- **Members**: G3.081, G9.067, G9.068
- **Provenance**: O — G9.067: the legacy UI text is the owner's own deployed wording (initial commit by the owner); OR48 (functional losses).
- **Truth**: wrong — G9.067: `_init_sgp()` sets `voc_init = 0` (`asy_sgp40_driver.py:334`) and raises it only for `WaitTimeNTP >= 1` (:355-358), so 0 never restores; legacy started with `voc_init = 1` (`asy_sgp40_driver/__init__.py:71`) and kept it for 0. (others: G3.081 partly, G9.068 partly)
- **Fit / pillar**: extends OR52.a (2) (persisted keys' meaning); restates OR48 (a functional loss, PAR.S01); refines OR48.a · pillar P1 (all members)

### HR017 Uniform module interface for supervision and aggregation
- **Req**: Every task-owning module exposes `get_task_starters()`/`get_timer_starters()` (possibly empty), every logging module `get_error_counter()`, and every top-level module `get_error_sources() -> list[Any]` and `get_loggers() -> list[PrintLogHistory]` (itself plus nested logger owners such as its `cfgmgr`); every error-log result is annotated `"ErrorLog"`, and supervision and aggregation walk these lists, never a hand-enumerated one.
- **Members**: G5.019, G10.043
- **Provenance**: A — G5.019: `6aed3c9`
- **Truth**: holds — G5.019: holds for `SensorReader`, `SensorReaderConfig`, `SystemService`, `AsyFramManager` (read); duck-typed, checked only by mypy/tests, no wiring-time Protocol check (others: G10.043 holds)
- **Fit / pillar**: restates OR16.a (1) chain completeness; restates C.9/G.2; P10 · pillar P10 (all members)

### HR018 The addition checklist is literal and accurate
- **Req**: Every addition walks the one ordered checklist (Part K) step by step, stating each step that does not apply with its reason. Every file, function and dispatch it names exists under that name, and Part L.1's association points equal Part K.3's. A new bus-facing driver lands together with its chip fake (`digital_twin/_<name>_chip.py`), its `machine.py` bus-map dispatch and `tests/test_digital_twin_<name>.py` (other modules join the twin through `build_system()`), with the chip-fake catalog tied to buildgen's `BUS_ATTACHED_DRIVERS` by a test; the documentation step records datasheet findings (Part M), the errno/wrnno row, user-facing notes (`DEVICE_REFERENCE.md`) and only genuinely open questions (BACKLOG).
- **Members**: G7.004, G9.024, G9.025
- **Provenance**: O — G9.025: OR44.a (3) ("produce fully fitting code on the first try").
- **Truth**: drifted — G7.004: C.11 item 9 still says "Also update `html/definitions/<device>.json` ... Same session", contradicting OR43.a (3)'s retirement of hand-written definitions (@web tags the only source); catalog sync is hand-kept (`test_buildgen_twin_wiring.py` pins wozi/dev only, TWIN.N281); a missing fake fails only … (others: G9.024 holds, G9.025 drifted)
- **Fit / pillar**: refines OR10.a (Part K step), OR16.a (1); restates OR44.a (3), harmonization 4; restates OR44.a (3) · pillar P10 (all members)

### HR019 Device set derived from devices/*.toml everywhere
- **Req**: Every check, test, script, build step, website tier and CI job derives the device set and per-device facts (drivers present, FRAM size, bus sharers) from `devices/*.toml` and the generated source at run time; tests are generic bodies driven by each TOML, never hand-written per-device files or a hard-coded device count, and no scenario assumes a driver every current device happens to have. Where a literal is unavoidable (a CI matrix, per-device MicroPython wrapper, JS constant) a test fails when it differs from the derived set; a deliberately narrower set is named and derived from its own criterion; docs may state the current count as a fact but never copy per-device TOML facts.
- **Members**: G2.042, G7.056, G8.033, G9.027, G10.062
- **Provenance**: O — G2.042: OR43.a (3) "Every check, test and build step derives the device set from devices/*.toml at run time ... never a hard-coded list or count"
- **Truth**: wrong — G7.056: `js/app.js:16` `KNOWN_DEVICES = ["wozi", "dev"]` with a silent fallback to wozi; `package.json:10` builds wozi only; the live tier boots `sensortask_wozi` only; README.md:430-431 claims "every real device is fully supported end-to-end via `--device`" though four devices' definitions never pass the … (others: G2.042 partly, G8.033 drifted, G9.027 partly, G10.062 partly)
- **Fit / pillar**: restates OR43.a (3); restates OR43.a; restates OR43.a (3); refines P10 · pillar P10 (all members)

### HR020 Every Timer arm handles ENOMEM and degrades
- **Req**: Every `Timer.init()`/`Timer(period=...)` arm site sits in a `try` catching `(OSError, MemoryError)`, because the rp2 alarm pool behind `machine.Timer` holds 16 alarms and an exhausted pool raises `OSError(ENOMEM)`; a bare `Timer()` is the allocate-now, arm-later form and never reaches the pool, and a re-arm after `deinit()` may succeed or raise. A failed arm degrades locally (skip the cycle, stop sequencing and release `start_timers()`, abort a pause, run without uptime, fall back to watchdog starvation on the reboot path), logs at the level its context allows, never ends its task and never triggers a reboot; a read-trigger failure lets the starter sequence continue with any data-ready IRQ wired after the guarded arm, its consequence stated accurately (starters run once per boot), and periodic timers are preferred where a dropped callback must self-heal.
- **Members**: G1.032, G3.063, G4.012, G5.056, G6.057, G10.021
- **Provenance**: O-confirmed — G5.056: `1df8bc4` (2026-07-18): "Owner-confirmed recovery: log and keep running"; F (`Timer.init()` fails only with `OSError(ENOMEM)`, per C.9)
- **Truth**: drifted — G3.063: the comment "this sensor just never gets triggered this cycle" understates it: `start_timers()` runs once at boot (`system_service.py:209-213`), so a timer-only sensor (BMP3xx, SGP40) stays untriggered until reboot, logged via non-persisting `pr.err()` only (others: G1.032 holds, G4.012 holds, G5.056 holds, G6.057 partly, G10.021 holds)
- **Fit / pillar**: refines OR29.a (2)-(3), OR49.a (1) (timer alarm pool as a finite resource); tension with OR18/OR31.a ("never stalls silently"); refines OR26.a (raising calls mapped from source); restates OR26.a (Timer callbacks); refines OR26.a; restates C.9 · pillars differ: G1.032 P3/P6, G3.063 P3, G4.012 P2, G5.056 P3, G6.057 P3, G10.021 P2

### HR021 Validate before packing, storing or slicing bytes
- **Req**: Before `int()`, `struct.pack()`/`pack_into()`, `to_bytes()`, a `bytearray` item store or a slice copy into a buffer, code range- and NaN-checks the value and bound-checks the span, because MicroPython truncates silently (0x101 stores as 0x01, missing pack arguments become zeros, NaN packs as a float, `int()` truncates toward zero) and a `bytearray` resizes on a length-mismatched slice assignment where a `memoryview` raises; it also handles `pack_into()`'s `ValueError` on a negative offset and the empty tuple from a zero-field format, probes `memoryview` writability with a zero-length slice assignment, and states any remaining truncation (SCD30 TempOffs 0.01 ticks) as the driver's, not the chip's.
- **Members**: G3.020, G4.026, G4.027, G6.028
- **Provenance**: F — G3.020: SPEC F.1 (pack truncation at 1.29, `py/binary.c` checks preview-gated; not re-read here); the rule is A (regression tests for `set_ambient_pressure(-0.5)`)
- **Truth**: drifted — G3.020: SCD30 validates before `int()`; SPEC:243-245 says TempOffs is "silently truncated by the chip", but the truncation is the driver's `int(offset * 100)` (`asy_scd30_driver.py:568-570`); legacy raised OverflowError where src now truncates (BUS.N137) (others: G4.026 holds, G4.027 holds, G6.028 holds)
- **Fit / pillar**: refines OR26; refines OR26.a; new; restates CLAUDE.md Part F pointer · pillar P2 (all members)

### HR022 No nested asyncio.run, no async generators
- **Req**: Code never defines an `async def ... yield` generator (streaming bodies are synchronous iterators over prepared pieces) and never calls `asyncio.run()` while other tasks are parked; every test helper that calls `asyncio.run()` (file-local `run()`, `hazard_pair()`, `build_pair()`, frame builders using `crc8_byte()`) is called only from synchronous test-function scope, because nesting it crashes the Unix port instead of raising.
- **Members**: G2.020, G4.034, G9.041
- **Provenance**: F — G9.041: session reduction to a 12-line reproducer (recorded in CLAUDE.md); not re-run here.
- **Truth**: partly — G2.020: rule followed at the cited sites, review-only (item N717); CLAUDE.md's mechanism is wrong at v1.29.0: `extmod/asyncio/core.py:247-248` `run()` is `run_until_complete(create_task(coro))` on the SAME `_task_queue`, it installs no fresh loop (`new_event_loop()` runs only at import, :324), so the crash … (others: G4.034 holds, G9.041 unverifiable)
- **Fit / pillar**: new (test standard); refines OR26.a; extends OR38 · pillars differ: G2.020 P5, G4.034 P2, G9.041 P5
- **Note**: G2.020 records that CLAUDE.md's stated mechanism (a fresh event loop replacing the queue) does not match v1.29.0 `extmod/asyncio/core.py:247-248`; the rule itself is undisputed. The mechanism wording is unresolved until re-traced.

### HR023 I2C bus parameters cover the slowest chip
- **Req**: A bus's I2C timeout covers the longest clock stretch any chip on it may do (SCD30: up to 30 ms per frame, 150 ms about once a day), so a bus carrying an SCD30 runs `timeout >= 200000` µs and at most 100 kHz (50 kHz recommended), otherwise rp2's 50 ms default stays; drivers declare these datasheet limits as `@requires` tags that buildgen enforces, a shared bus taking the strictest, and no bound is invented (SGP40 `<= 400 kHz`, BMP3xx and the FRAM's SPI none). Because each rp2 bus id is one static object whose re-construction resets frequency and timeout for all users, every script and module that constructs a bus passes the TOML's full parameter set, and a wrapper omits `addrsize`/`timeout` it does not set; soak checks for the long stretch state they observe only its absence of failure.
- **Members**: G1.033, G1.034, G3.037, G4.016, G8.044
- **Provenance**: F — G1.033: ports/rp2/machine_i2c.c:50, 72, 87, 110 (static `machine_i2c_obj[]`, default timeout 50,000 µs applied on every make_new); SCD30 Interface Description p.2 (150 ms stretch)
- **Truth**: partly — G1.033: sgp40_fram_backup_restore.py:54 and sgp40_voc_algorithm_quality.py:46 omit the timeout on i2c1, silently lowering it to 50 ms for the SCD30 on the same bus (others: G1.034 holds, G3.037 holds, G4.016 holds, G8.044 holds)
- **Fit / pillar**: extends SPECIFICATION.md F.5.1 (static bus singletons); restates a datasheet fact; refines OR29.a (2); extends OR30 (bus timeout is a tunable); new (datasheet-derived bus rule); extends OR29.a (verified limits) · pillars differ: G1.033 P2, G1.034 P2, G3.037 P5, G4.016 P2, G8.044 P2

### HR024 SPI 32+ byte reads may raise EIO
- **Req**: Since 1.29, every rp2 SPI read of 32 bytes or more (the DMA path) is treated as able to raise `OSError(EIO)` on an RX overrun, while writes and shorter transfers never raise. The FRAM layer handles it without retrying (owner, 2026-09-24): the dual copy absorbs a single overrun and only an overrun hitting both copies degrades the read to `None`. Both bus fakes model the overrun at the bus level, the twin's chip-level fault injector never raises it for reads the port cannot fail, test comments describe SPI's fault surface accordingly, and since no Python knob induces it on target the hardware tier pins its consequence (a busy/locked-out status read).
- **Members**: G1.035, G4.017, G5.068, G7.033
- **Provenance**: O — G5.068: "So no retry is added (owner decision, 2026-09-24)"; "SETTLED, owner, 2026-09-24" (BACKLOG); F (MicroPython v1.29.0 `ports/rp2/machine_spi.c`, per F.5.2 — not re-read here)
- **Truth**: drifted — G5.068: policy holds; `tests/test_fram_integration.py:3-5` still says "Real RP2040 SPI write()/readinto() cannot raise or report a fault at all", contradicting F.5.2; recovery shown by mock/twin only; a transient read fault at logger `setup()` is not absorbed (G5.065) (others: G1.035 holds, G4.017 holds, G7.033 partly)
- **Fit / pillar**: restates SPECIFICATION.md F.5.2; refines OR26.a; restates owner decision; refines OR17.a (match vs mismatch row) · pillars differ: G1.035 P2, G4.017 P2, G5.068 P3, G7.033 P5

### HR025 I2C/SPI deinit releases nothing on rp2
- **Req**: No code relies on `machine.I2C.deinit()`/`machine.SPI.deinit()` to stop or release a bus: on rp2 both are silent no-ops (I2C's exists only from 1.29) and each bus id is a static singleton that re-construction reconfigures, so no code depends on bus identity; only `UART.deinit()`, `Timer.deinit()` and `WLAN.deinit()` release hardware, and a wrapper makes a bus unavailable by dropping its own reference. `asy_i2c_driver.py`, `asy_spi_driver.py`, `tests/machine.py` and `digital_twin/machine.py` state the same semantics.
- **Members**: G3.035, G4.014
- **Provenance**: F — G3.035: CLAUDE.md "audited against upstream source at both tags, 2026-09-10"
- **Truth**: holds — G3.035: SPEC F.5.1 present; per-bus singleton reconfigured by a later construction stays a plan item (HW.S18); the four files not re-read here (others: G4.014 holds)
- **Fit / pillar**: refines OR29.a; refines OR29.a (2) · pillars differ: G3.035 P5, G4.014 P2

### HR026 Soft timer callbacks only set a flag
- **Req**: Every `machine.Timer` is soft and its callback (and every `Pin.irq` callback) does nothing but `.set()` an `asyncio.ThreadSafeFlag` or event; re-arming, resets and storage state run in the task it wakes. No code relies on every callback being delivered, since rp2's depth-8 scheduler queue drops one silently when full and a flag set twice coalesces: a timer that must not lose a fire is `PERIODIC`, and each remaining `ONE_SHOT` states why a dropped fire is acceptable or backstopped.
- **Members**: G4.010, G5.057, G10.039
- **Provenance**: F — G4.010: `ports/rp2/mpconfigport.h:131` (`MICROPY_SCHEDULER_DEPTH 8`), `shared/runtime/mpirq.c:103-105` (return of `mp_sched_schedule()` ignored), `py/scheduler.c:163-176`, `extmod/asyncio/event.py:45-63`
- **Truth**: drifted — G5.057: C.9 scopes PERIODIC to "anything that must keep firing", F.1 says "every timer that must fire uses `PERIODIC`"; four `ONE_SHOT` timers remain (`system_service.py:126` reset, `:166` stagger sequencer, `:367` storage unpause; `asy_ntp_client.py:283` retry), and the reset, sequencer and unpause … (others: G4.010 holds, G10.039 partly)
- **Fit / pillar**: refines OR49.a (1) (8-deep soft-IRQ queue); refines OR26.a, OR31.a; restates C.9; refines OR47.a (3) (sequencer) · pillars differ: G4.010 P2, G5.057 P3, G10.039 P3

### HR027 A swallowing except always leaves a trace
- **Req**: A broad `except Exception` in `src/` appears only around caller-supplied callbacks, an unsupervised task's top, or a platform call with an undocumented raise surface. Every `except` that swallows an exception logs it through `err_s()`/`wrn_s()` (persisted for attempts and callbacks) or returns a documented sentinel its caller logs; a print-only swallow is allowed only with a stated reason (sync context, the logging layer itself, a deliberately uncounted routine observation), and none is a silent `pass`.
- **Members**: G5.012, G6.041
- **Provenance**: A — G5.012: C.7 agent text; CORE.N245's open question (`6f12d22`) is the origin
- **Truth**: partly — G5.012: `asy_fram_manager.py:594-597` (timestamp unpack → `_TS_UNINIT`, no log), `config_manager.py:79-83,93-97,113-118` (malformed schema → empty, no log) and `print_log.py:247-269` (FRAM I/O → `False`, `_diag` only, silent at level 0) swallow without a persisted trace; the schema ones are authoring-time … (others: G6.041 partly)
- **Fit / pillar**: refines OR26.a ("swallowing excepts"); refines OR26.a (swallowing excepts) · pillars differ: G5.012 P2, P7, G6.041 P2

### HR028 Construction and setup follow one contract
- **Req**: A module's `__init__` only allocates and validates (caller arguments first: non-integer or negative size, out-of-byte id, non-buffer), stopping at the first finding and printing a refusal at once; `async def setup()` calls the logger's own `setup()` first, persists any construction refusal, and has one return contract and signature shape project-wide. A class with async setup gates on `self.initialized: bool = False -> True` (the named exception is `ConfigManager.valid`), and a call before `setup()` answers exactly as that class's declared raise/never-raise contract says; a driver `init()` with a remaining controlled raise path documents that its callers handle it.
- **Members**: G5.017, G6.027, G10.044
- **Provenance**: A — G5.017: C.13 agent text
- **Truth**: partly — G10.044: partly (others: G5.017 not checked, G6.027 holds)
- **Fit / pillar**: restates OR26.a (C.13 gates honoured); restates C.13; refines OR26.a (construction completeness); refines OR24, OR26.a (construction completeness), OR47.a (1) · pillar P2 (all members)

### HR029 UART re-init only by fresh construction
- **Req**: A UART is re-initialised only by constructing a new `machine.UART(...)` (as `asy_uart_driver.UART.init()` does), never `deinit()` followed by `init()`, because on rp2 `deinit()` unroots the RX/TX ring buffers and a same-size `init()` reuses them unrooted, so IRQ writes land in collectable memory; moving a UART to other pins needs a hard reset, since `deinit()` leaves the GPIO function select in place.
- **Members**: G4.021, G6.034
- **Provenance**: F — G4.021: `ports/rp2/machine_uart.c:436-443` (alloc only when `buf == NULL`), `:483-497` (roots cleared, `buf` kept, no `gpio_set_function` reset)
- **Truth**: holds — G4.021: holds (others: G6.034 holds)
- **Fit / pillar**: refines OR29.a (2); restates Part F · pillar P2 (all members)

### HR030 SGP40 general-call reset: setup only, recorded
- **Req**: The SGP40's datasheet I2C general-call reset (0x06 to address 0x00, Table 17) resets every general-call listener on its bus, SCD30 included; it fires only from `initialize()` at setup or task restart, tolerates the NAK and is never reachable from a REST field (`SGPResetVOC` is a software-only algorithm reset). A reset that reaches every device on a shared bus is a deliberate, recorded owner decision with a hazard test at every tier, including real-hardware tests that check SCD30 measurement keeps advancing; no device address may be 0x00 or in the reserved ranges. The behaviour is new relative to the field firmware, whose reset never ran.
- **Members**: G1.046, G3.038, G9.070
- **Provenance**: F — G1.046: SGP40 datasheet Table 17 (cited at asy_sgp40_driver.py:586); call chain read at HEAD
- **Truth**: partly — G9.070: `asy_sgp40_driver.py:585-593` broadcasts on every task restart; legacy never ran its reset (un-awaited coroutine, wrong address), so field units never broadcast. No owner decision recorded. (others: G1.046 holds, G3.038 holds)
- **Fit / pillar**: refines SPEC C.8 structural exception 2; extends OR41.a/OR45.a (listed exception); extends OR48.a (2) (an agent-only divergence goes to the owner) · pillars differ: G1.046 P2, G3.038 P2, G9.070 P9
- **Note**: G3.038 calls it an accepted low risk (agent acceptance, f5c9f90); G9.070 finds no owner decision and a new-vs-field divergence. Resolved by OR48.a (2): an agent acceptance is not an owner decision, so the divergence goes to the owner (unresolved until then).

### HR031 Never emit non-finite values or JSON
- **Req**: No NaN or ±inf value is ever published or passed to `json.dumps()`, which never raises and emits bare `nan`/`inf` that browsers and MicroPython's own `json.load()` reject; every float that can become non-finite is gated before serialisation (shaping values is the caller's obligation on every route), never poisons filter state, and every comparison that gates on a value handles NaN explicitly. A config read survives a leniently mangled parse through per-key validation with default fallback.
- **Members**: G3.021, G4.030, G6.086
- **Provenance**: F — G6.086: pinned against the interpreter by `test_strict_json.py`
- **Truth**: partly — G4.030: SCD30 gates per word (`test_asy_scd30_driver.py:415`); a repo-wide non-finite gate is XCUT.T23's open topic; the omitted-value leniency is fixed upstream after 1.29 (commit `9ef16b466` per `test_config_manager.py:929`), so the loader must keep working either way (others: G3.021 holds, G6.086 partly)
- **Fit / pillar**: refines OR26/OR49.a; refines OR26.a, OR52.a (2); new · pillar P2 (all members)

### HR032 Device and bus locks: caller-held, fixed order
- **Req**: Locking is the caller's job: every I2CDevice operation runs inside `async with device:`, a multi-transaction sequence (RMW, snapshot, burst) holds the session lock for its whole length, helpers documented as 'caller holds the lock' take none, and nested sessions on one device are forbidden (non-reentrant `asyncio.Lock`). Locks are always acquired in SPECIFICATION.md C.8's fixed order (level 2 before level 1, driver before bus: `async with self.i2c_<chip> as <chip>:` then `async with <chip>.i2c_device as i2c:`) across every driver, and a new lock takes its place in that order.
- **Members**: G3.026, G5.096, G10.036
- **Provenance**: A — G3.026: SPEC C.3/C.8
- **Truth**: not checked — G5.096: no mechanical guard exists (others: G3.026 holds, G10.036 holds)
- **Fit / pillar**: refines OR41.a; refines OR41.a (2); restates C.8 · pillar P2 (all members)

### HR033 Routine faults are handled in place
- **Req**: An abnormal but harmless situation (unreachable NTP/DNS server, garbage reply, network loss, a retry loop that keeps failing without raising) is handled inside its module, logged, counted and retried on its own capped exponential backoff (NTP unsynced: 10 s doubling to 600 s on the 10 s tick, checked as a pair by buildgen, plus a short resync loop when synced; captive DNS 0.5 s to 5 s; UART listen timeout/2 to 5 x timeout), never a zero-delay retry, reset on the first success. A task ends and is restarted only when a restart re-initialises something real (a sensor re-probe, a fresh WLAN object) or on an unexpected exception it cannot handle; each restart costs 100 of a 300 budget decaying 1 per clean 2 s pass, so the fourth death inside the window reboots. Every bench test that injects a network fault asserts afterwards, via the FRAM-kept SYSTEM log, that no task ended and no budget reboot happened, and a host guard keeps that assertion present.
- **Members**: G1.054, G5.053, G6.044, G6.066
- **Provenance**: O — G5.053: C.7.2 "(owner, 2026-09-24)"; OR18/OR31.a (owner, 2026-09-25); budget constants C (`system_service.py:44-46`)
- **Truth**: holds — G1.054: `assert_no_task_ended()` asserts SYSTEM counter 0 (error_log_helpers.py:29-36); completeness guard with vacuity floor ≥ 15 (test_bench_no_task_ended_completeness.py:17, 46); the guard misses class methods, helper-injected faults, call order and the flash tier (:15-46); side finding: the … (others: G5.053 holds, G6.044 holds, G6.066 holds)
- **Fit / pillar**: restates OR18.a, OR31.a (4-not-adopted replacement) at L4; restates OR18, OR31.a; restates OR18 · pillars differ: G1.054 P2, G5.053 P2, P3, G6.044 P2, G6.066 P2

### HR034 Inoperational hardware escalates to a reboot
- **Req**: A missing, dead or stalled chip, or a device config that does not match the board, is not contained: construction and `setup()` still complete on a bus where the chip never answers, the reader's failed init logs errno 10/12/13 and its read loop returns False without entering the wait, and the supervisor's legacy escalation (+100 per restart, decay 1 per check, reboot above 300) restarts it up to a reboot, which is intended.
- **Members**: G3.061, G5.054, G9.075
- **Provenance**: O — G3.061: M.1.1 req 20; OR18.a ("escalation … up to a reboot is acceptable and even intended")
- **Truth**: holds — G3.061: BMP/ISL/SCD30/SGP40 init paths return False on failure (others: G5.054 holds, G9.075 holds)
- **Fit / pillar**: restates OR18.a, OR26.a; restates OR18.a · pillar P3 (all members)

### HR035 Flash writes staged off the request path
- **Req**: A write to the RP2040 flash filesystem never runs inline in a request: `ConfigManager.write_config()` validates and stages synchronously and its own task flushes after the response, because a flash program/erase disables interrupts port-wide and inline it reset the triggering HTTP connection. Any code that must see the write land (every device script and restore phase) awaits `flush_pending()` on each manager it staged on before returning.
- **Members**: G1.094, G4.050
- **Provenance**: F — G4.050: `ports/rp2/rp2_flash.c:171-197` (`save_and_disable_interrupts()` around program/erase); A (`81d6a36`, WP5)
- **Truth**: holds — G1.094: staging and `create_task(self._flush_staged(...))` at config_manager.py:350-356; guard enforces flush per manager in device_scripts/ (flush order not asserted by design, :69-71; one allowlisted script whose re-derivation only checks for any `.sleep*()` call, :26-28, 81-87) (others: G4.050 holds)
- **Fit / pillar**: refines OR26.a (construction/handling completeness); refines OR42.a (write sites) · pillars differ: G1.094 P2, G4.050 P9

### HR036 A sample never claims freshness it lacks
- **Req**: A driver never re-stamps a sample it cannot prove current. The ISL29125 is self-healing and reports such a sample as None; a reader that cannot read its own config during a cycle logs the errno, and its fallback publication with fixed values (BMP3xx offsets 0 and mean temperature 15 °C; ISL29125 filter off) and the ISL29125's past-bound settle publication (a bounded number of rounds under a stream of concurrent config writes) stand only where they do not violate that rule.
- **Members**: G3.044, G3.058, G3.060
- **Provenance**: O — G3.060: SPEC M.1.1 "the project owner's list", requirement 16
- **Truth**: partly — G3.060: the config-read-failure path publishes a freshly stamped sample with the filter off (`asy_isl29125_driver.py:503-506`) and the bounded settle publishes a possibly-stale one (G3.044, G3.058) (others: G3.044 holds, G3.058 holds)
- **Fit / pillar**: conflicts G3.060; tension with M.1.1 req 16; conflicts G3.044, G3.058; whether it generalises beyond ISL29125 is open (G3.072) · pillars differ: G3.044 P3, G3.058 P3, G3.060 P1
- **Note**: Contradiction: G3.060 (owner, SPEC M.1.1 req 16) forbids publishing an unprovable sample as fresh; G3.044 and G3.058 (agent design, tests) publish a freshly stamped filter-off sample and a possibly-stale post-settle sample. Resolved by provenance for the ISL29125: the owner requirement wins and the two agent behaviours are defects; whether the rule generalises beyond ISL29125 (BMP3xx fallback) is unresolved.

### HR037 Memory safety designed in; degradation only backstop
- **Req**: Every `src/` module that can exhaust memory is designed never to raise `MemoryError` under worst-case load; a caught `MemoryError` is a design defect to fix at its source, not a handled case. Where a function has a real alternative flow it catches `(OSError, MemoryError)` and returns a defined unavailable/`None`/`False` result, never an unguarded re-raise; where it is doomed without memory the supervisor's task restart and then the watchdog are the remedy, and `asyncio` primitives are not blanket-wrapped.
- **Members**: G4.062, G9.046
- **Provenance**: O — G9.046: OR26.a (owner's sharpened wording, 2026-09-25).
- **Truth**: drifted — G4.062: SPEC F.2 (:3609-3610) and CLAUDE.md keep the "concrete, non-hypothetical threat" wording that OR26.a replaced; the listed suppression sites each degrade to a defined result (checked at `asy_uart_comm.py:290,873`, `base_classes.py:71`, `config_manager.py:356`, `print_log.py:140-144`, … (others: G9.046 drifted)
- **Fit / pillar**: restates OR26.a, OR40; restates OR26.a · pillars differ: G4.062 P2, G9.046 P3
- **Note**: Both members record that CLAUDE.md/SPEC F.2 still carry the replaced 'concrete, non-hypothetical threat' wording; resolved by OR26.a (owner, 2026-09-25).

### HR038 Lock exits tolerate a double release
- **Req**: `Lockable.__aexit__()` and every lock-releasing exit path swallow the `RuntimeError` of an already-released lock and never propagate it, and a two-lock entry releases the outer lock when acquiring the inner one fails. On the synchronous SPI path `session_begin()`/`session_end()` never take the bus lock: the caller holds it (enforced by `configure()`'s guard) and deasserts CS in its own `try/finally`, and `__aenter__` releases the lock itself if `configure()` raises.
- **Members**: G3.028, G5.015
- **Provenance**: A — G3.028: tests and code comments
- **Truth**: drifted — G3.028: `asy_spi_driver.py:61-67` says the guard is "only ever called from SPIDevice.__aenter__", but `session_begin()` (FRAM's sync path) calls it too (BUS.S03) (others: G5.015 holds)
- **Fit / pillar**: OR13 (comment vs code); refines OR38.a (1) (no leaked locks) · pillar P2 (all members)

### HR039 Unlocked shared-state access has no await
- **Req**: Shared state is read or read-modify-written without a lock only where no `await` can run between the operations that must agree, with the justification written at the site; a function requiring a caller-held lock says so where it is defined; every `ConfigManager` serialises its own writes and flush on `config_lock`, and nothing relies on serialisation across two managers.
- **Members**: G5.046, G6.047
- **Provenance**: A — G5.046: code comments and PR #40 comment (agent)
- **Truth**: holds — G5.046: holds for `_get_values()`'s success path (no await, `config_manager.py:240-251`) and `monitor_loop()`'s three reads (per harvest; not re-traced at HEAD); the PR #40 justification lives only in the PR comment (others: G6.047 holds)
- **Fit / pillar**: refines OR37.a (2) (races proven by analysis); refines OR41.a (2) · pillar P2 (all members)

### HR040 Read triggers staggered from one shared start
- **Req**: Sensor read-trigger timers start staggered evenly across exactly one second, each at `t0 + k*slot` against one shared start so callback latency cannot accumulate, guaranteeing a minimum separation of one measured worst-case read for every combination of whole-second periods with bus-sharing sensors placed furthest apart; the uptime, WiFi and NTP 1 s timers are outside the stagger. Timing designs may rely on `Timer.PERIODIC` being drift-free (it re-arms from its own schedule), never on a chain of one-shots armed from callbacks.
- **Members**: G4.013, G5.058
- **Provenance**: O — G5.058: C.9.1 "Design intent (owner-established)"; OR47/OR47.a (3) (owner, 2026-09-26) sharpens it to shared-start scheduling with a minimum separation
- **Truth**: partly — G5.058: each one-shot is armed from the previous callback with `delay = 1000 // (N+1)` (`system_service.py:158-168`), so offsets accumulate latency; the proof test replicates the arithmetic instead of running the real sequencer and assumes whole-second periods from one common start (others: G4.013 holds)
- **Fit / pillar**: refines OR47.a (3); restates OR47.a (3) · pillars differ: G4.013 P1, G5.058 P2, P6

### HR041 CRC and codec instances: per sequence, guarded
- **Req**: Every public CRC and framing-codec method returns None/False on invalid input or failed allocation and never raises, except CRC `add()`/`check()`, whose `MemoryError` is a documented controlled raise that every caller guards; pass-through mode (poly None) returns the caller's object unchanged. Incremental CRC state and a delimited codec's scratch belong to one instance and one sequence: each construction site makes its own instance, every incremental sequence is finalised with `check_inc()` before the next starts, and a caller finishes with a returned scratch view before the next `encode_into()`. `crc_checks.py` itself is not modified.
- **Members**: G3.002, G3.003, G5.080
- **Provenance**: O-confirmed — G5.080: `23e5443`: "crc_checks.py is not to be modified" (owner decision per harvest); caller discipline A
- **Truth**: partly — G5.080: guarded call sites tested in `tests/test_asy_uart_driver.py` only (per harvest, not re-traced); the empty-payload asymmetry (CORE.N156) is still open (others: G3.002 holds, G3.003 holds)
- **Fit / pillar**: refines OR26 (handled at the right layer); extends OR41.a (shared-resource matrix); conflicts OR24/OR46.a if the empty-payload fix needs a `crc_checks.py` change — see Conflicts · pillar P2 (all members)

### HR042 The UART stack never raises
- **Req**: Neither `UART_Comm` nor the UART driver ever raises: every `UART_Comm` entry point returns its documented sentinel for a link fault, failed allocation or misbehaving callback (its listen-loop and dispatcher catches are the backstop, not the mechanism), the driver collapses poll, `any()`, unregister and caller type errors to False/None/0 and re-checks `_uart`/`poller` every `ready()` iteration against a concurrent `deinit()`, and the one upstream owner (`asy_uart_comm.py`) logs. A caller's buffer belongs to the call until it returns.
- **Members**: G3.033, G6.001
- **Provenance**: O-confirmed — G6.001: Part J "confirmed by the project owner (2026-09-11)" (SPEC:5169); UART requirements file: "same never-raise/never-wedge contracts"
- **Truth**: holds — G3.033: catches present; accumulation loops are MemoryError-wrapped and one is documented unbounded-and-accepted (`:415`) (others: G6.001 holds)
- **Fit / pillar**: refines OR26 · pillar P2 (all members)

### HR043 Captive DNS answers on-subnet, drops the rest
- **Req**: The hotspot's captive DNS answers every well-formed on-subnet A query with exactly one A record for the AP's own address (TTL 60 s) and silently drops malformed, truncated, off-subnet or root queries, silence being the correct outcome hardware tests assert. Because no supervisor restarts it, it catches everything at its task top, backs off receive failures up to a 5 s cap and persists a code; one instance is reused across hotspot activations (relying on `disconnect()` fully resetting the socket) and each request's `DNSQuery` shares the `DNSSRV` logger.
- **Members**: G1.088, G6.058
- **Provenance**: A — G1.088: captive_dns.py comments; tests read behaviour from source
- **Truth**: holds — G1.088: `_RECV_FAIL_BACKOFF_MAX_S = const(5.0)` (captive_dns.py:34), `response()` returns None for rejected queries (:194); the flood test does not exercise the backoff curve its name claims (test_hotspot_role_reversal.py:244-257, commit f862b1e) (others: G6.058 holds)
- **Fit / pillar**: refines OR49.a (1) (malformed input) and OR52.a (3); refines OR52.a (3) · pillar P2 (all members)

### HR044 System commands, reboot path and storage pause
- **Req**: `SystemCmd` accepts exactly `reboot`, `bootloader` and `mempause`. `machine.reset()`/`bootloader()` are called only from `SystemService._reboot()`, which pauses FRAM storage before arming the one-shot reset a few seconds later (and before the starve fallback), and every new reset path goes through it. `mempause` pauses FRAM storage for a fixed 300 s window that no client can supply or end early; storage pause is bounded at 3,600 s, lives in RAM only (a reset clears it) and ends by itself on a one-shot timer, and a paused chunk drops rather than defers its writes, reads and clears. `PauseTime` is range-checked 0-3600 and rejected, not clamped. The boot signature is the NTP time of boot, or a random 32-bit value after 120 s without NTP.
- **Members**: G1.093, G5.052, G5.079, G6.082, G9.074
- **Provenance**: A — G1.093: webserver comment; test pins it
- **Truth**: partly — G1.093: client can't supply the duration (asy_webserver_service.py:96); the 300 s value in `system_cmd()` was not traced here; `_MAX_STORAGE_PAUSE = 3600` caps the internal API (system_service.py:41) (others: G5.052 holds, G5.079 holds, G6.082 holds, G9.074 holds)
- **Fit / pillar**: refines OR43.a (1) (read-only vs writable); extends P7; extends P3; refines OR52.a (3) (unauthenticated `bootloader` accepted); restates OR52.a (3) for `bootloader` · pillars differ: G1.093 P2, G5.052 P7, P3, G5.079 P3, P7, G6.082 P2, G9.074 P3

### HR045 PUT results: four words, envelope stays OK
- **Req**: PUT bodies are sparse JSON with no `cmd` envelope. Each field reports one of `"Valid"`, `"Unchanged"`, `"Invalid"` (bad or unknown key) or `"Failed"`, typed once as `WriteValidity` and used identically by the JS mock; a per-field failure never demotes the envelope below `res: OK, code: 0` (the only OK outcome), and callers read the per-field results. A push fires only on `"Valid"`, dispatch-only and command-only fields report `"Valid"` on every well-formed repeat (SCD30 `ContMeas=True` too), setters return a uniform `True`, and toggling the WiFi LED never reconnects. A post-write hook fires at most once per call and only when a field was `"Valid"`; if it raises, `api_response.handle_set_cmd()` persists errno 99 and answers `ERR`/100, and the webserver reports every field of that group `"Failed"`; an invalid manager or internal error reports every requested key `"Failed"`; malformed JSON answers HTTP 200 with code 1. The website marks a submitted-but-unanswered field Failed only as a defensive fallback.
- **Members**: G3.069, G5.040, G5.042, G6.079, G7.068, G10.047
- **Provenance**: A — G3.069: SPEC C.5.2.1
- **Truth**: drifted — G6.079: the `_put_sensors` comment cites a per-key "Invalid" but emits nothing for an unknown sensor key (`asy_webserver_service.py:427-430`); `lightCmdLED` reports "Failed" for a malformed payload where H.6 says "Invalid" (REST.N122 mechanisms differ) (others: G3.069 holds, G5.040 partly, G5.042 partly, G7.068 drifted, G10.047 holds)
- **Fit / pillar**: restates OR42.c (1) result words; extends OR43.a (1) ("GET returns exactly what PUT accepts"); refines OR26.a (Microdot handlers); refines OR43.a (1) (GET returns what PUT accepts); refines OR26 (no silent drop); restates C.5.2, OR42.a (2) · pillars differ: G3.069 P4, G5.040 P2, G5.042 P2, G6.079 P4, G7.068 P2, G10.047 P8
- **Note**: G5.042 (ERR/100 with empty result) and G6.079/G7.068 (every field Failed, envelope OK) describe two layers, checked at HEAD: `handle_set_cmd()` returns `make_response(100)` and `_put_sensors` maps that to `"Failed"` per key (`asy_webserver_service.py:463-469`). No contradiction.

### HR046 SCD30 not-ready cycle reuses the last reading
- **Req**: `read_measurement()` runs exactly once per cycle before the three pure cache getters, which never re-check data-ready (the flag clears on read); when the SCD30 reports no new data the reader keeps its cached values untouched and counts no error, matching legacy, accepting that a previous cycle's values are published under a fresh timestamp.
- **Members**: G3.072, G9.063
- **Provenance**: O-confirmed — G3.072: "Reverted from an earlier \"clear to None\" version per project-owner direction" (`110f3db`)
- **Truth**: holds — G3.072: confirmed in code; the IRQ fallback counter accumulates across cycles rather than consecutive ones (SENS.S08) (others: G9.063 holds)
- **Fit / pillar**: tension with G3.060 / OR44 P1 (see Conflicts); refines OR48.a (2) (recorded owner decision) · pillar P2 (all members)
- **Note**: Tension with the ISL29125 no-stale-sample rule (HR036) and P1; resolved for SCD30 by the owner direction in `110f3db` (legacy behaviour prioritised).

### HR047 Chip identity checked at setup per datasheet
- **Req**: Every driver's layer-2 `setup()` verifies the chip's identity from documented content and raises if it does not answer, with SPI devices (no ACK) verified by content only and each check exactly as strong as the datasheet supports: the FRAM requires manufacturer ID, continuation code and product ID together and supports only the parts in `_KNOWN_PRODUCT_IDS` (MB85RS64V, 8 KB, RDID `04 7F 03 02`, 2-byte addresses; MB85RS2MTA, 256 KB, `04 7F 48 03`, 3-byte addresses), refusing a chip whose RDID does not match the part implied by `max_size`, a new size needing its own table entry and each device TOML naming its part next to `max_size`; the SGP40 checks the self-test result's high byte (0xD4) and has no feature-set check; BMP3xx accepts the documented chip IDs.
- **Members**: G3.039, G5.071, G9.069
- **Provenance**: F — G5.071: RDID tables MB85RS64V p.10 (`04H 7FH 03H 02H`, density 64 kbit) and MB85RS2MTA p.10 (`04H 7FH 48H 03H`, 2 Mbit), confirmed in `dstxt`; dev's MB85RS2MTA confirmed on silicon (`tests/test_asy_fram_driver.py:104-105`)
- **Truth**: partly — G3.039: SGP40 self-test compares the 0xD4 high byte (datasheet Table 13: "0xD4 0xXX … ignore 0xXX"); the serial read fetches 1 of the 3 words the datasheet specifies (§3.4) and checks an undocumented `word[0] == 0` inherited from Adafruit; SCD30 accepts any CRC-valid firmware version (others: G5.071 partly, G9.069 holds)
- **Fit / pillar**: refines OR48.a (feature-set check dropped vs legacy, recorded); extends P2; refines OR48.a (datasheet-grounded adaptation) · pillar P2 (all members)

### HR048 Owner-confirmed legacy behaviours stay
- **Req**: The behaviours SPECIFICATION.md A.4 lists as confirmed intentional by the owner stay: LED sequencing; SGP40 backup 0 = disabled; permanent WiFi deactivation after a second failure streak; no STA-to-hotspot fallback after one success; raw numbers in the UI; SGP40 skips its VOC read (no fallback values) while compensation data is unavailable, a None compensation field at boot logging nothing, only a raising source logging errno 18 and a non-numeric value counting as a read failure; no UART RTS/CTS flow control, with no plan to revisit; a notification window that must have On before Off on the same day, never wrapping midnight (an overnight window is a future feature, not a fix); SCD30 `AmbPres` readback via 0x0010.
- **Members**: G3.078, G3.095, G6.036, G9.071
- **Provenance**: O-confirmed — G3.078: SPEC A.4 "Functional behaviors confirmed intentional by the project owner"
- **Truth**: holds — G3.078: code and tests; compensation values are not clamped before conversion (G3.079) (others: G3.095 holds, G6.036 holds, G9.071 holds)
- **Fit / pillar**: restates owner decision; restates OR48.a (legacy-identical, no loss); new; restates OR48.a (2) (recorded owner decisions) · pillars differ: G3.078 P2, G3.095 P4, G6.036 P4, G9.071 P2

### HR049 CYW43 behaviours the WiFi code and bench respect
- **Req**: The WiFi service treats an RSSI query outside station mode as an expected `ValueError("STA required")`, accounts for `STAT_GOT_IP` being reported by an AP interface and for status 2 ('obtaining IP') having no named constant, and never re-applies `essid/password/active(True)` to a running access point (the CYW43 can drop its beacon). The bench AP is tuned to the CYW43439: fixed 2.4 GHz (band bg) channel 6 because auto channel 13 did not associate, WPA2-PSK (RSN/CCMP) only with PMF disabled, and `ensure_bench_bridge()` converges an existing AP back to channel 6 on every run.
- **Members**: G1.084, G4.044, G6.063, G8.062
- **Provenance**: F — G4.044: `extmod/network_cyw43.c:365`; the beacon and PMF facts are silicon findings (unverifiable here)
- **Truth**: partly — G6.063: `_run_hotspot_mode()`'s `status != STAT_GOT_IP` branch is live only on the first tick; `rssi` error prints on every `/status` in AP mode (N106) (others: G1.084 holds, G4.044 holds, G8.062 holds)
- **Fit / pillar**: refines OR29.a (1); refines OR29.a; restates Part F; extends OR29.a (hardware facts stored) · pillars differ: G1.084 P3, G4.044 P2, G6.063 P2, G8.062 P3

### HR050 Boot entry frozen as main.py; nothing shadows it
- **Req**: Each device's generated boot entry is frozen under the literal name `main.py` with the board's stock manifest reused unchanged; a custom frozen `_boot.py` is never used (it skips the board manifest and broke USB, which comes up only after `_boot.py` and `boot.py` return). Because a VFS `boot.py` runs before the frozen `main.py` and the filesystem root precedes `.frozen` on `sys.path`, a unit's littlefs holds no `boot.py` and no `.py`/`.mpy` named like a frozen module before a refactored image runs, and device scripts never leave `.py` files there.
- **Members**: G4.008, G8.073, G9.090
- **Provenance**: F — G4.008: `ports/rp2/main.c:229-247` (`_boot.py` → `boot.py` → `mp_usbd_init()` → `main.py`), `shared/runtime/pyexec.c:743-752` (a frozen `main.py` wins over a VFS one), `py/runtime.c:147-150` (`sys.path = ['', '.frozen']`); design A (`e554073`)
- **Truth**: wrong — G9.090: a filesystem `print_log.py`, `config_manager.py`, `system_service.py` etc. shadows the frozen module on import; the generated boot entry adds no `sys.path` guard (`buildgen/codegen.py:696-709`). The dev unit's 2026-08 snapshot held exactly such files plus `config_BMP3XX.cfg`/`config_SGP40.cfg` … (others: G4.008 holds, G8.073 holds)
- **Fit / pillar**: refines OR52.a (1) (reflash runbook, `PAR.T08`); extends OR31.a (1) (pre-`main.py` code minimal); new (answers harmonization 23 / PAR.T08) · pillars differ: G4.008 P3, G8.073 P3, G9.090 P9

### HR051 Uninterruptible calls fall to the watchdog
- **Req**: A call MicroPython cannot interrupt (any `machine.I2C`/`machine.SPI` transfer, which has no await point or partial-read API; `socket.getaddrinfo()`, also inside `asyncio.start_server()`) is not wrapped in an asyncio timeout. A wedged bus, sensor or resolver is recovered by task restart escalating to reboot and the hardware watchdog, not by an I2C-level timeout mechanism; the UART clamp-and-yield technique is not generalised to I2C/SPI, a task respawn does not rebuild the bus peripheral, and the upstream status is re-checked at every pin move.
- **Members**: G3.031, G4.048
- **Provenance**: O — G3.031: CLAUDE.md "settled, don't re-propose"; OR18.a ("a stalled chip may recover by a reboot")
- **Truth**: holds — G3.031: no I2C timeout wrapper in `src/`; SPEC F.2:3620 "only a full reboot does that"; hot-reconnect completeness never confirmed on hardware (BUS.N134) (others: G4.048 holds)
- **Fit / pillar**: restates OR18.a · pillar P3 (all members)

### HR052 Pin legality follows RP2040 Table 279
- **Req**: `buildgen/pico_gpio.py` accepts every pin function RP2040 datasheet Table 279 offers on the Pico W's user GPIOs, with a test per newly legal pin and comments that state the silicon facts, and never accepts GPIO23/24/25/29 for any bus, UART or IRQ wiring, because the Pico W hands them to the CYW43 even where the mux would allow it. A device wires at most one UART crossover pair, since RP2040 has two UART, two I2C and two SPI peripheral indices.
- **Members**: G3.036, G4.051, G8.026
- **Provenance**: O — G8.026: OR53 (1) (owner, 2026-09-26): "`buildgen/pico_gpio.py` accepts every pin function the RP2040 offers (datasheet Table 279)"; F — RP2040 datasheet Table 279 (printed pp.237-238); `ports/rp2/machine_uart.c:71-77`, `machine_i2c.h:65-66` at v1.29.0
- **Truth**: wrong — G8.026: Table 279 gives GP22 I2C1 SDA, GP28 I2C0 SDA, SPI on GP20-22/26-28, UART1 on GP20/21; `pico_gpio.py:9-10,26-27` say "GP22/GP28 have no I2C function at all" / "GP20-22/GP26-28 have no SPI function", and `_UART_PAIRS` omits (20,21). SPEC A.6's `pin % 4`/`((pin+4)&8)>>3` mux matches … (others: G3.036 holds, G4.051 holds)
- **Fit / pillar**: restates OR53 (1) ("wireless-reserved GPIOs stay excluded"); restates OR53 (1) · pillars differ: G3.036 P9, G4.051 P2, G8.026 P10

### HR053 One hardcoded 8000 ms watchdog, fed centrally
- **Req**: Each generated boot entry constructs exactly one `WDT(timeout=8000)`, identical on every device, hardcoded with no injection point, as its first statement before the device-module import (and so before the frozen-HTML `/html` mount); 8000 ms stays under the RP2040's 8,388 ms cap (24-bit counter decremented twice per µs tick, erratum RP2040-E1; a larger value raises `ValueError`) and is not raised, and code that runs before it stays minimal. Every feed goes through `SystemService.feed_watchdog()`: at boot after every one-time `await X.setup()` in the batch, never inside a loop; at runtime only from the supervisor loop, never a Timer/IRQ callback, so no caller can keep feeding a hung system. Every inter-feed stretch (boot steps, device scripts, the twin WDT model) is budgeted against 8,000 ms.
- **Members**: G4.005, G5.047, G5.048, G8.029
- **Provenance**: O — G5.047: "must be hardcoded so no error ever can circumvent it" (owner, quoted from FINAL_WIRING_PLAN.md in `eaafc2f`); OR31.a (1) (owner, 2026-09-25) for "first statement … before the device-module import"
- **Truth**: partly — G5.047: exactly one `WDT(` per generated device (`tests_scripts/test_buildgen_generate.py:48-53`); but it is the first line of `build_system()`, after `from sensortask_<device> import main` (`buildgen/codegen.py:381,703`); `tests/test_reset_call_site_invariant.py:30-45`'s WDT half is vacuous (skips … (others: G4.005 holds, G5.048 partly, G8.029 partly)
- **Fit / pillar**: refines OR31.a (2); restates OR31.a (1); restates OR31.a · pillar P3 (all members)

### HR054 Power-cycle backstop and deferred-flush window accepted
- **Req**: A WiFi link stuck in a CYW43 `isconnected()` false positive is recovered by a power cycle or `hard_reset()`, a deliberate recovery feature; no independent reachability probe is added. Its accepted residual risk is stated in the same words in CLAUDE.md and SPECIFICATION.md F.2: a power loss between an accepted PUT's response and its deferred flash write may lose that one change, never corrupt it, the next boot's `setup()` repairs what an interrupted write left, and the port-wide IRQ disable of the flash write stays off the request's path.
- **Members**: G5.035, G6.053, G9.031
- **Provenance**: O — G6.053: CLAUDE.md; commit 655e4f9 "the project owner judged a new reachability-probe mechanism's complexity not worth it"
- **Truth**: drifted — G6.053: `tests_hardware/README.md:635-641` still calls it "a real architectural question for the project owner, not decided here" (others: G5.035 unverifiable, G9.031 drifted)
- **Fit / pillar**: extends P3; restates CLAUDE.md; refines OR18.a; restates CLAUDE.md hard rule; rule drift under OR13.a · pillars differ: G5.035 P3, P9, G6.053 P3, G9.031 P3

### HR055 No module insists on FRAM
- **Req**: FRAM is optional hardware: anything a constructor calls that could fail (FRAM chunk allocation) is caught and degrades to None because no supervisor exists yet, every FRAM-backed logger and store then works RAM-only (allocation failure never raises), SGP40 runs without backup/restore, and `AsyFramManager`'s own log is the one deliberately RAM-only error source.
- **Members**: G3.084, G5.063
- **Provenance**: O-confirmed — G5.063: `ec2e803` (2026-08-11): "per the owner's explicit requirement that no module insist on FRAM"; WP Topic 11 (`9ac59cf`, per harvest): "every module shall have optional FRAM logging … FRAM module itself is the sole exception"
- **Truth**: holds — G3.084: the allocation failure is print-only, so SGP40 silently runs without backup (STOR.S08) (others: G5.063 holds)
- **Fit / pillar**: refines OR26.a (construction completeness); extends P3 · pillar P3 (all members)

### HR056 WiFi state machine keeps legacy field behaviour
- **Req**: An empty SSID or 5 failed connection attempts lead to hotspot mode; a link that was established once never escalates to the hotspot: a disconnect after an established STA connection retries silently every 60 s without incrementing `connection_failures`. The hotspot stays up while a client is associated and otherwise retries STA after its window; a second failed STA streak after a hotspot phase deactivates WLAN permanently, a terminal state task restarts keep and only a power cycle clears; power saving is off, a connect attempt polls for 5 s, a mode switch disconnects, deactivates and waits before the new mode, and repeated hardware failure hands the task to the supervisor.
- **Members**: G1.090, G6.052, G9.078
- **Provenance**: O-confirmed — G6.052: "Functional behaviors confirmed intentional by the project owner" (SPEC:269-275); commit 8696c1d
- **Truth**: holds — G1.090: `_on_sta_disconnected()` sleeps 60 s when `_conn_phase == _PHASE_STA_ESTABLISHED` and only otherwise calls `_register_sta_connection_failure()` (asy_wifi_service.py:469-478) (others: G6.052 holds, G9.078 holds)
- **Fit / pillar**: refines OR18.a (harmless situation handled inside); tension P1 (a terminal no-network state needs a person) — resolved by owner's words; refines OR48.a · pillars differ: G1.090 P1/P3, G6.052 P3, G9.078 P3

### HR057 SCD30 read on data-ready with 500 ms fallback
- **Req**: The SCD30 is read on its data-ready IRQ edge; a 500 ms periodic tick, started with the other timer starters, counts a pin stuck high and forces a read when the edge is missed. The read moment is IRQ-modulated and outside the timer no-coincidence proof, setup does not restart continuous measurement, the published tuple is CO2, temperature, humidity, derived values and timestamp, and the temperature offset is applied only in the sensor's NVM.
- **Members**: G3.073, G9.065
- **Provenance**: O-confirmed — G9.065: OR47.a (3) (500 ms tick stays).
- **Truth**: not checked — G9.065: src tick period and publication tuple not re-read here. (others: G3.073 holds)
- **Fit / pillar**: restates OR47.a (3) · pillars differ: G3.073 P3, G9.065 P2

### HR058 method-assign suppressions: inline in tests, never src
- **Req**: Test, twin and device-script code that reassigns a method carries an inline `# type: ignore[method-assign]` at each site, and every such type suppression names its bracketed code (`method-assign`, `assignment`, `arg-type` for deliberate wrong-type inputs, `misc` for module swaps), never a scope-wide override; `src/` never suppresses `method-assign`, which `scripts/lint.sh` enforces with grep guards that are themselves tested against fabricated and live trees.
- **Members**: G1.108, G2.070, G8.085
- **Provenance**: O — G1.108: CLAUDE.md "(project owner's direction)"
- **Truth**: holds — G1.108: six inline sites in device scripts; `scripts/lint.sh` guards src/ (others: G2.070 holds, G8.085 holds)
- **Fit / pillar**: restates CLAUDE.md; restates OR36 (no test artifacts in product) · pillar P4 (all members)

### HR059 E402 suppression only after a real statement
- **Req**: `# noqa: E402` appears only in files where a statement other than a `sys.path` change precedes the imports; a `sys.path`-only preamble carries none, since ruff exempts it and RUF100 fails an unused suppression.
- **Members**: G1.106, G2.071
- **Provenance**: A — G1.106: CLAUDE.md ("verified directly, 2026-09-10")
- **Truth**: holds — G1.106: website_identity.py has a `REPO_ROOT =` statement before the suppressed imports (others: G2.071 holds)
- **Fit / pillar**: restates CLAUDE.md · pillar P4 (all members)

### HR060 Async-ness is marked one way
- **Req**: Async-ness is marked one way in identifiers: a `src/` module whose public API is async carries the `asy_` prefix and a sync-only module does not (sensor drivers are `asy_<chip>_driver.py`), the same `asy_` marker is used on starters and other identifiers (never `async_`), and sync twins of async methods carry `_sync`; harmonised under OR24 (8 async modules and several identifiers deviate today).
- **Members**: G10.001, G10.076
- **Provenance**: C — G10.001: driver form written (agent, spec consolidation `59f1614`); the general prefix rule is unwritten
- **Truth**: partly — G10.001: driver form holds 6/6 and is enforced by `buildgen/driver_registry.py:85` (`f"asy_{driver}_driver"`); general form 19 of 27 async modules (others: G10.076 partly)
- **Fit / pillar**: refines OR24 · pillar P4 (all members)

### HR061 Sensor driver module shape is uniform
- **Req**: Every module that logs under a fixed name declares `_NAME = const("<NAME>")`, and a module with a measurement namedtuple names the type with the identical string, defined next to it; a sensor driver's REST keys use `self.name`, never `_NAME`, and its `*_Reader` constructor keeps the documented parameter order. The device-session lock wrapper (`<Sensor>_DeviceSession(Lockable)`) has one shape across drivers and exists once as a shared `Lockable` subclass taking the bus device, not as a verbatim copy per driver.
- **Members**: G3.087, G10.006, G10.007
- **Provenance**: A — G3.087: `e5f31f2`, `6aed3c9`
- **Truth**: partly — G3.087: `_NAME == "BMP3XX"` and namedtuple "BMP3XX" checked; no test for the name rule; constructor divergences seeded (SENS.S18); C.14.1's "three promoted drivers" count is stale (four) (others: G10.006 holds, G10.007 holds)
- **Fit / pillar**: restates OR24; conflicts G10 C.2 text vs Part G.1 · refines OR24/OR46.b ("adopt the solutions at any place"); restates C.2 · pillar P4 (all members)
- **Note**: Contradiction: G3.087 (agent, C.2) requires the DeviceSession as 'verbatim boilerplate' per driver; G10.006 requires one shared class. Resolved toward one shared class by OR24 'one material' and Part G.1 'never reimplement' (owner-level basis over agent text).

### HR062 No runtime cast shim; one narrowing idiom
- **Req**: Narrowing a base or `struct.unpack()` return type uses one project-wide idiom with no runtime cost: a reader's `get_data()` narrows by an identity return with a scoped `# type: ignore[return-value]`, `typing.cast()` appears only under `TYPE_CHECKING`-safe imports, no module defines a runtime `cast()` shim, and the written rule (C.4.2) is self-consistent.
- **Members**: G3.088, G10.024
- **Provenance**: A — G3.088: `e5f31f2`
- **Truth**: drifted — G10.024: C.4.2 rejects a local shim and in the next sentence keeps `typing.cast()` for `SCD30_I2C._read_dev_register()`; `asy_scd30_driver.py:26-32` defines exactly such a runtime shim and calls it on every read (`:487`, `:621-623`); no other file has one (others: G3.088 partly)
- **Fit / pillar**: restates OR24; refines OR24; P6 (a function call per reading) · pillar P4 (all members)

### HR063 Guard real-world faults, not type violations
- **Req**: Code does not re-check at runtime what static typing already guarantees for the project's own callers (types, address format); it does guard NaN, ±inf and out-of-domain values of correctly typed inputs, which real sensors produce, and validates every input that arrives untyped (REST JSON, TOML, restored FRAM/flash state) at its entry point.
- **Members**: G3.018, G5.009
- **Provenance**: O-confirmed — G5.009: `b5502c8` (2026-08-06): "Per project owner feedback: don't guard against inputs violating their already-declared types"
- **Truth**: partly — G5.009: D.2 states the typed half; the "untyped entry points validated" half is only implied (F.1's driver-gating audit dated 2026-09-24, not re-checked here) (others: G3.018 holds)
- **Fit / pillar**: restates SPEC D.2; refines OR26 (handling at the right layer) · pillars differ: G3.018 P4, G5.009 P2

### HR064 bool never passes as an int
- **Req**: Integer validation and narrowing exclude `bool` by exact type (`type(x) is int` / `is not int`), never plain `isinstance`, with no redundant CPython-only guard on top; tests and comments state the platform fact the same way: on MicroPython `bool` is not an `int` subclass (`py/objbool.c`), unlike CPython.
- **Members**: G4.028, G5.008
- **Provenance**: F — G4.028: `py/objbool.c:87-96` (`mp_type_bool` has no `parent` slot); A (`839c31e`)
- **Truth**: drifted — G4.028: `tests/test_asy_isl29125_driver.py:2835` ("bool is an int subclass in MicroPython as in CPython") and `tests/test_asy_neopixel_driver.py:541` contradict SPEC and source (others: G5.008 holds)
- **Fit / pillar**: new; refines OR24 · pillar P4 (all members)
- **Note**: G5.008's provenance line says Python's `bool` subclasses `int`; G4.028 (F, `py/objbool.c:87-96`) shows MicroPython's does not. Rule unaffected; the fact resolves to G4.028's source reading, and two test comments stating the CPython fact are drift.

### HR065 Code uses only the pinned MicroPython subset
- **Req**: All MicroPython-target code (product, unit-tier tests and device scripts) avoids syntax the pinned parser rejects or mishandles (iterable unpacking in a display, `await` in a comprehension, a `{`-containing literal implicitly concatenated with an f-string) and builtins and modules the rp2 build lacks (`zip(strict=)`, `bytearray` slice deletion, `deque.clear()` and keyword arguments, `file.writelines()`, `itertools`, `str.removeprefix()`, `random.Random`, `inspect`, `namedtuple._asdict()/_fields`, `dataclasses`, user-class `__del__`, `weakref`), never relies on dict or `globals()` order, and relies on annotations never being evaluated. Each gap is enforced by a named lint rule where one exists (RUF005, PERF401, B905 suppressed only in MicroPython-target code while host code passes `strict=`), each such suppression names the platform fact and is re-checked on a version bump, and code the unit tier does not run is proven on the target interpreter.
- **Members**: G1.107, G2.050, G4.031, G4.032
- **Provenance**: F — G1.107: MicroPython v1.29.0 py/objzip.c:39-40 (`mp_arg_check_num(n_args, n_kw, 0, MP_OBJ_FUN_ARGS_MAX, false)` rejects keywords)
- **Truth**: holds — G1.107: five sites, all device scripts (others: G2.050 holds, G4.031 holds, G4.032 holds)
- **Fit / pillar**: refines CLAUDE.md suppression practice; extends CLAUDE.md version-bump practice to tests; new (P4 + OR16.a chain liveness for device scripts); new · pillars differ: G1.107 P4, G2.050 P5, G4.031 P4, G4.032 P4

### HR066 TYPE_CHECKING guard, PEP 604 unions, full annotations
- **Req**: Every module that needs `typing` imports it as `try: from typing import TYPE_CHECKING` / `except ImportError: TYPE_CHECKING = False` (typing has no runtime presence on MicroPython), never unconditionally, and puts every typing-only import under `if TYPE_CHECKING:`; unions are PEP 604 `X | Y`, never `typing.Union`, and every parameter and return is annotated.
- **Members**: G5.001, G6.039, G10.023, G10.026
- **Provenance**: O-confirmed — G10.026: CLAUDE.md "confirmed directly" (the runtime test on the pinned interpreter); enforced by ruff `UP007`/`ANN` and mypy `--strict`
- **Truth**: holds — G5.001: all 22 `src/` files that import `typing` use the identical guard (grep), the 6 without it (`asy_dns_client`, `asy_i2c_driver`, `crc_checks`, `framing_codecs`, `math_helpers`, `voc_algorithm`) import no `typing`; `_strip_type_checking.py` matches this exact shape (others: G6.039 holds, G10.023 holds, G10.026 holds)
- **Fit / pillar**: refines OR24 (one material); restates OR24 (one material); restates C.10; restates CLAUDE.md · pillar P4 (all members)

### HR067 Quote annotations only for TYPE_CHECKING names
- **Req**: An annotation is quoted only when it names something imported or defined under `TYPE_CHECKING`; every other annotation is bare, and the tree is harmonised to that rule under OR24 (today 150 quoted annotations in 21 `src/` files name nothing TYPE_CHECKING-only, and the same starter signature is quoted in some drivers and bare in others).
- **Members**: G5.002, G10.025
- **Provenance**: O — G5.002: "Quoting annotations (owner decision, 2026-09-24)"; applied in `58abf8f` ("SPECIFICATION.md D.6 states the annotation-quoting rule; no mass edit")
- **Truth**: partly — G10.025: D.6 itself says existing files "are not mass-edited"; OR24/OR24.a (1) authorise the consistency change (others: G5.002 holds)
- **Fit / pillar**: conflicts OR24 (one material) — the "not mass-edited" clause leaves two styles; OR24.a authorises harmonising; conflicts D.6 "not mass-edited" vs OR24 "change, don't flag" — resolved by OR24.a (later, owner) · pillar P4 (all members)
- **Note**: Contradiction: G5.002 carries the owner's D.6 decision (2026-09-24) 'existing files are not mass-edited'; G10.025 harmonises all. Resolved by OR24/OR24.a (owner, 2026-09-25, 'change, don't flag'), the later ruling.

### HR068 Class members follow D.15; comments move along
- **Req**: Inside every `src/` class, dunders come first, then private methods, then public ones, each group ordered starters, getters, setters, others (SPECIFICATION.md D.15). A reorder is a pure AST-verified move in which a method's own comments and a section heading travel with their code while their text does not change.
- **Members**: G5.005, G9.048, G10.045
- **Provenance**: O-confirmed — G5.005: `41762dc` (2026-09-13): "Owner's rulings, 2026-09-13, on the D.15 open question. The order as written stands … comments move with the code they annotate … The reorder itself is a decided task now"
- **Truth**: drifted — G5.005: D.15 at HEAD still reads "no change to any body/decorator/comment" (the owner's amendment and the high-priority BACKLOG task were dropped by merge `e5d2c43`, BACKLOG has no entry); a crude AST role check at HEAD finds 18 of 51 method-bearing `src/` classes out of order (the project's own … (others: G9.048 drifted, G10.045 partly)
- **Fit / pillar**: restates OR24 (naming, ordering: "change, don't flag"); restates OR24 (ordering); lost decision under OR13/OR14; restates OR24 · pillar P4 (all members)
- **Note**: G5.005/G9.048 record that the owner's 2026-09-13 amendment ('comments move with the code') was lost by merge `e5d2c43`; D.15 still says 'no change to any body/decorator/comment'. Resolved by the owner ruling (41762dc), which the merged statement carries.

### HR069 Every suppression names its code and reason
- **Req**: Every `# type: ignore` and `# noqa` names its error codes, a multi-code list in one order and spacing, and in shipped code carries a one-line reason (a verified stub defect, an unannotated vendored import, a MicroPython builtin limit); a typing workaround names the external defect and its removal trigger (e.g. `ANN401` on `**kwargs` until the stubs declare `TypedDict`/`Unpack`), a stub defect that can be repaired at install is repaired rather than suppressed, and a suppression that no longer fires is removed.
- **Members**: G5.003, G6.040, G10.072
- **Provenance**: C — G5.003: 2 coded `type: ignore[...]` in `src/system_service.py` (:232 `union-attr`, :234 `arg-type`) and 0 uncoded in `src/` (grep); `warn_unused_ignores` in mypy config; removal-trigger wording is agent-authored (`pyproject.toml`)
- **Truth**: drifted — G6.040: SPEC F.5.5 (3833) calls `asy_udp_socket.py`'s `recvfrom()` "the one place a `type: ignore` *is* right", while 20 others exist, two in the same file (`:48`, `:136`); vendored `ext/microdot.py`'s own suppressions stay untouched (G6.060) (others: G5.003 holds, G10.072 partly)
- **Fit / pillar**: restates OR50.a (1) for suppressions; extends OR50.a (1) (suppressions re-checked on trial); refines OR24, OR50.a (suppression review) · pillar P4 (all members)

### HR070 Workarounds name their defect and removal trigger
- **Req**: Every workaround of an external defect, in product code (stub gaps, a cyw43 quirk, a modlwip freed-pcb write, Microdot's 1,024 B `send_file` default), the test tiers (stub gap, mypy narrowing limit, Vitest API gap, filename length) or the hardware harness (USB raw-REPL wedge rebind, picotool BOOTSEL retry, nmcli escaping, error text and rescan lag, NM teardown settle), states the defect, its scope and bound, and the event that removes it, and is re-checked when the tool or upstream version changes; `type: ignore` is preferred over mistyping an annotation to match a wrong stub.
- **Members**: G1.081, G2.052, G6.080
- **Provenance**: A — G1.081: harvest WORKAROUND kind; no owner wording
- **Truth**: partly — G1.081: each has cause and bound (≤2 rebinds, 5 retries, ≤2 s); none states a removal trigger or tool version (others: G2.052 partly, G6.080 partly)
- **Fit / pillar**: extends OR50.a (1) (every setting has a live reason) to harness code; new (closes untracked workarounds) · process; extends OR50.a (1) (every entry has a live reason) · pillars differ: G1.081 P4, G2.052 ?, G6.080 P4

### HR071 Lint exemptions central, scoped by reason
- **Req**: A lint exemption is scoped the same way for the same reason: a structural or whole-file reason lives once in `pyproject.toml`'s per-file-ignores (or one per-category block) with its reason, e.g. `tests_hardware/`'s subprocess rules S603/S607, S310 for the fixed bench URL, S112 for loss-injection loops, S105/S106 for the accepted hotspot-password copies, and the test tiers' S101, SLF001, PLC0415, PLR2004, ARG00x, A002/FBT/ANN401 and the Microdot `disallow_untyped_decorators` override with its revisit trigger; an inline `# noqa` is used only for a line-scoped need, carries its reason on that line, and moves to the central table when the same reason recurs; the docs describe exactly which scopes carry each block.
- **Members**: G1.109, G2.072, G5.085, G8.124, G10.081
- **Provenance**: O-confirmed — G8.124: `2badee1` "project owner's explicit direction: enable the strict rule" (pyproject.toml:214); the line-scoped exception A (`c225b04`)
- **Truth**: drifted — G2.072: CLAUDE.md says `tests_scripts/`, `scripts/` and `toolchain/` carry the same block `tests/` does; `pyproject.toml` has it for `tests_scripts/**` and `tests_hardware/**` only, `scripts/`/`toolchain/` get per-file `S603` only (others: G1.109 partly, G5.085 holds, G8.124 drifted, G10.081 partly)
- **Fit / pillar**: refines OR46.b (central, reasoned per-file exemption); refines OR46.b (3) (central exemptions); refines OR24; extends OR24 (one material), OR50.a (stale suppressions); refines OR50.a (every suppression reviewed on trial) · pillar P4 (all members)

### HR072 Shared state lives in the Locked primitives
- **Req**: State shared across coroutines is held in `Lockable`/`LockedCounter`/`LockedFlag`/`LockedValue`, never a bare module-level variable plus an ad hoc lock; `LockedCounter` clamps to `[0, max_val]` (negative `max_val` clamps to 0) and `LockedValue` stores any value unclamped; a bare `asyncio.Lock()` outside `base_classes.py` exists only where it guards an external resource, with the reason stated.
- **Members**: G5.016, G10.035
- **Provenance**: A — G5.016: G.2 catalog (agent)
- **Truth**: partly — G10.035: 8 bare `asyncio.Lock()` outside `base_classes.py`: bus locks `asy_i2c_driver.py:32`, `asy_spi_driver.py:36` (external resource); `asy_fram_manager.py:68`, `asy_neopixel_driver.py:61-62`, `asy_udp_socket.py:59`, `asy_wifi_service.py:174`, `config_manager.py:223` unexplained against G.2 (others: G5.016 holds)
- **Fit / pillar**: restates Part G, OR24; restates Part G.2 · pillar P4 (all members)

### HR073 Nothing in the product exists for tests
- **Req**: No parameter, non-`const()` value, public attribute, getter, branch or hook exists in `src/`, generated code or the frozen website bundle only so a test, the twin or a hardware script can reach it; the swap to the twin is pure module-path ordering and twin code uses the product's normal interfaces. Tests adapt from outside, reaching private attributes (SLF001 exempt), replacing module names (`json`, `deque`, `bytearray`, `asyncio.sleep`), rebinding across `sys.modules`, or arming a one-shot `_StarvedAlloc`, and restoring each in `__exit__`/`finally`; a test that would need a `src/` change alone is dropped or redesigned and any existing hook is removed.
- **Members**: G2.038, G5.076, G6.033, G7.003, G7.084
- **Provenance**: O — G2.038: OR36 "Testing must adapt to fit the code, never vice versa"; OR36.a (1)
- **Truth**: wrong — G7.084: `pollManager.isBusy` (`poll-manager.js:44`) is used only by `tests_js/poll-manager.test.js:126-142`. (others: G2.038 holds, G5.076 partly, G6.033 drifted, G7.003 partly)
- **Fit / pillar**: restates OR36.a (1); restates OR36.a (1) — tension with OR36.a (3) over whether a pause bypass is "a function of the hardware" …; restates OR36/OR36.a; conflicts none; extends OR36 (to the frozen website) · pillar P4 (all members)
- **Note**: G5.076 notes a tension with OR36.a (3) over whether FRAM's `override_pause` is 'a function of the hardware'; unresolved at cluster level.

### HR074 One per-function explanation form per scope
- **Req**: Each scope uses one form for per-function explanations: in `src/` a module has one header docstring and every function or method carries its explanation as `#` comments, never its own docstring (D.11); JS uses JSDoc blocks; each host scope chooses one form and is harmonised to it under OR24.
- **Members**: G9.022, G10.029
- **Provenance**: A — G9.022: wording from `e5f31f2` (2026-09-09); C: 0 of 936 `src/` functions carry a docstring (AST count at HEAD).
- **Truth**: partly — G10.029: `src/` holds with 3 exceptions; the host scopes mix both forms; CLAUDE.md's wording names function docstrings as allowed, D.11 forbids them in `src/` (others: G9.022 holds)
- **Fit / pillar**: refines OR24 (one material); refines OR24, OR27.a · pillar P4 (all members)
- **Note**: G10.029 notes CLAUDE.md's wording allows function docstrings while D.11 forbids them in `src/`; drift, resolved toward D.11 as the more specific rule (unresolved for host scopes until one form is chosen).

### HR075 Vendored Microdot is never edited
- **Req**: `ext/microdot.py` stays byte-identical to upstream tag `v2.6.2` and the legacy `python/CommonDrivers/microdot.py` stays an unmodified old snapshot; neither is restyled or edited, every behaviour change and Microdot gap (the write-phase exception gap included) is handled by wrapping or calling it from `asy_webserver_service.py`, and a version move is a deliberate decision with its provenance recorded in THIRD_PARTY_LICENSES.md.
- **Members**: G6.070, G9.057
- **Provenance**: O — G6.070: OR24.a (2) "vendored `ext/` ... never touched"
- **Truth**: holds — G6.070: `git -C microdot show v2.6.2:src/microdot/microdot.py | diff - ext/microdot.py` identical (2026-09-26); no test, script or CI step re-verifies it (others: G9.057 holds)
- **Fit / pillar**: restates OR24.a (2) · pillar P4 (all members)

### HR076 Permanent text never cites temporary labels
- **Req**: Permanent code, tests and docs never cite row or entry IDs of working or temporary files (hardware-queue rows, handovers, `UART_C_PORT_CHANGELOG.md` entries, `audit/` items, 'Item N'), an unnamed section of another file, a retired file, or session/step/work-package/plan/decision labels no living document defines; a fact worth citing is stated in place or linked to its permanent home, a rule needing provenance carries '(owner, YYYY-MM-DD)', and a temporary file's content is migrated before it is deleted.
- **Members**: G1.104, G9.002, G9.005
- **Provenance**: O-confirmed — G1.104: OR27.a (history out of docs) and OR11 (no broken crosslinks); plan seed DOC.S06
- **Truth**: drifted — G1.104: "queue row G9" (website_identity.py:1-2), "queue F10" (test_network_resilience.py:876-877), "Item 23/19/20" (test_toolchain_flash_boot.py:14-47) and more remain after the queue file's deletion (03f8bcf) (others: G9.002 drifted, G9.005 drifted)
- **Fit / pillar**: refines OR27.a, OR11; refines OR27.a (provenance tag replaces labels); refines OR11.a · pillars differ: G1.104 P4, G9.002 P4, G9.005 P8

### HR077 One header block, three-line comment cap everywhere
- **Req**: Every file in the repo, of any language (Python, shell, JS, `.d.ts`, CSS, HTML, TOML/YAML/INI/JSON-with-comments including `tsconfig*.json`), opens with exactly one header block and keeps it and every inline comment block to at most three prose lines; machine-read tag lines, JSDoc type annotations and PEP 723 blocks are exempt but their introducing prose is not. `tests_scripts/test_comment_block_cap.py` enforces the cap as defined (tag exemption for the tag line only, PEP 723 exemption only inside a `# /// script` block, a paragraph packed onto one long line counted by its length, a non-empty scope floor), checks header presence too, and names the files it cannot parse as review-enforced.
- **Members**: G9.020, G9.021, G10.028
- **Provenance**: O — G9.020: "(project owner, 2026-09-14, re-confirmed 2026-09-18)"; "comment rule applies to every file" is the PQ6 answer (2026-09-26).
- **Truth**: drifted — G9.020: `tsconfig.json:11-15` (5 lines), `:29-35` (7), `tsconfig.node.json`, `tests_js/vitest-commands.d.ts:1-22` (6, 10, 5 lines) exceed the cap; CLAUDE.md says "every scope measures zero". (others: G9.021 partly, G10.028 partly)
- **Fit / pillar**: restates PQ6 answer; refines OR27.a / PQ6; restates CLAUDE.md, refines OR27.a · pillar P4 (all members)

### HR078 Hardware claims cite the repo's datasheets
- **Req**: Every hardware-interaction claim in code, tests, comments and docs is checked against and cites (page, section or table) the datasheet in `datasheets/<chip>/`; datasheet text wins over reference implementations (RIOT, SparkFun, Adafruit); a missing datasheet is named explicitly, never replaced by memory or web search, and statements that a datasheet is absent are corrected once it is present (WS2812, BMP390, RP2040, W25Q16JV, CYW43439 now are).
- **Members**: G1.103, G3.107, G9.034
- **Provenance**: O — G3.107: CLAUDE.md "read them first … say so explicitly if one you need isn't there"; OR4
- **Truth**: drifted — G1.103: manual_bus_electrical.py:54, 60 says no WS2812 datasheet is present, but datasheets/ws2812/ exists; accuracy tolerances cite only the BMP388 sheet for a BMP384/BMP390 heading (manual_sensor_accuracy.py:11-15) (others: G3.107 drifted, G9.034 holds)
- **Fit / pillar**: restates OR4, OR29.a (2); restates OR4/OR51.a (2); restates OR4 · pillars differ: G1.103 P7, G3.107 P4, G9.034 process

### HR079 Docs state current facts, not history
- **Req**: Every markdown file, code comment and config comment states current facts, rules, agreements and technical reasons only; incident stories, 'used to', 'an earlier draft said', withdrawn figures and pass-by-pass narratives are removed with anything worth keeping folded into the fact, and a measured value stays only where it is the evidence behind a rule or limit, with its date and source.
- **Members**: G9.001, G9.023
- **Provenance**: O-confirmed — G9.023: OR27.a ("measured numbers stay only where they are the evidence behind a rule or a limit").
- **Truth**: drifted — G9.001: 25 drift-only items (group H below) show narrative in SPEC (e.g. F.5.2 :3744 "an earlier draft", H.5 :4405, I.5 :5148), `tests_hardware/README.md` "Third pass" sections, CLAUDE.md "Known … fixed" bullets, README :26-29, code comments (`system_service.py:191`, `asy_webserver_service.py:749`). (others: G9.023 stale)
- **Fit / pillar**: restates OR27/OR27.a; restates OR27.a · pillar P4 (all members)

### HR080 Divergence from legacy field behaviour is explained
- **Req**: A change to a driver's or service's behaviour is checked against the legacy code's field-proven behaviour; a divergence counts as explained only as an adaptation with no functional loss or as a recorded owner decision, otherwise it goes to the owner. Not parity targets: the ISL29125's legacy driver (smoke-tested only, evidence of intent at most for naming, defaults and API shape), the legacy dev entry point with its dev-only SHTC3/MPRLS drivers and the `dev_legacy/` snapshot (dev's refactored firmware is `devices/dev.toml`), and the legacy Python UART modules (the UART contract is Part J and the C peer; their blocking-read pattern stays forbidden).
- **Members**: G3.101, G9.053, G9.086, G9.087
- **Provenance**: O — G3.101: SPEC M.1 "(owner)"; `2ad5d9e` "the owner's standing ruling"
- **Truth**: drifted — G3.101: the exception lives in SPEC M.1 only; CLAUDE.md's rule states no exception (others: G9.053 holds, G9.086 holds, G9.087 holds)
- **Fit / pillar**: bounds OR48.a (legacy losses); restates OR48.a (2); restates OR32.a (1); restates CLAUDE.md UART rules · pillars differ: G3.101 process, G9.053 P4, G9.086 process, G9.087 P6
- **Note**: G3.101 records that the ISL29125 exemption lives only in SPEC M.1 while CLAUDE.md's rule states none (drift, not a contradiction).

### HR081 Address field only for selectable chips
- **Req**: Whether a driver is `ADDRESS_CAPABLE` or `FIXED_ADDRESS` follows its datasheet's address-select pin: only then does it get a TOML `address` field and parameter (BMP3xx 0x76/0x77 by SDO, a `@limits` set); hard-wired chips (ISL29125 0x44, SGP40, SCD30) get none, not even for test injection, and a second instance needs another bus.
- **Members**: G3.045, G8.036
- **Provenance**: O — G8.036: harmonization 10 / OR36.a (1) (owner, 2026-09-26): BMP3XX's address stays (SDO), ISL29125's goes; rule text A (`6db3199`)
- **Truth**: drifted — G3.045: `asy_isl29125_driver.py:1065-1066` says the parameter "exists only for test injection, exactly as BMP3XX_I2C's does", but BMP's is a real hardware choice; dev and wozi both wire BMP at 0x77 (`dev.toml:91`, `wozi.toml:70`) (others: G8.036 partly)
- **Fit / pillar**: restates OR36.a (1) + harmonization 10; restates harmonization 10 · pillar P4 (all members)

### HR082 Command-only fields are never persisted
- **Req**: A command-only field (special-alone: `def=None`, `special` set; e.g. `SGPResetVOC`, `ISLCalibrate`, `ContMeas`) runs only on demand, is validated and always reported `"Valid"` so a repeated value re-triggers its action, is never written to the config store, is kept out of `get_dict_cfg()`'s field list and the bool batch (ConfigManager's `get_dict()` is all-or-nothing), and is skipped by the failed-push recovery chain, which for other fields falls back to the chip's readback, then the stored config, then the default.
- **Members**: G3.068, G5.045, G9.061
- **Provenance**: A — G3.068: `9b83336` (rule: command-only fields carry the prefix), after `7890e2b` flagged it "the project owner's call"
- **Truth**: partly — G5.045: holds (`base_classes.py:380-383` skips it); a command-only schema still creates an empty `{}` config file on flash (`tests/test_config_manager.py:1119-1121`) and logs wrnno 6 (G5.029) (others: G3.068 holds, G9.061 holds)
- **Fit / pillar**: extends OR43.a (settings vs commands); refines OR42.c (2); refines OR42.c (1) · pillars differ: G3.068 P4, G5.045 P9, G9.061 P2
- **Note**: G3.068 says a command-only field carries its device prefix, while G10.009 (key spelling, outside this cluster) says keys carry no per-driver prefix; unresolved naming question for the OR24 key-scheme harmonisation.

### HR083 Schema getters sync; Neopixel has none
- **Req**: A module's schema is exposed as a plain sync `get_cfg_schema()` (no I/O) plus the public `cfg_schema` attribute; `NeopixelDriver` is the one module without a config schema.
- **Members**: G3.090, G5.095
- **Provenance**: O-confirmed — G3.090: "No config schema (confirmed by the project owner)" (since `da9b4ab`)
- **Truth**: holds — G3.090: no `_VAL_*` in the module (others: G5.095 holds)
- **Fit / pillar**: restates owner decision; restates OR24 · pillar P4 (all members)

### HR084 General-purpose driver API stays without callers
- **Req**: API that completes a module as a general-purpose driver for its hardware or algorithm stays even with zero station callers (BMP `get_altitude()`, standalone getters, optional `setup()` parameters, SCD30 reader getters, CRC16/CRC32, COBS, the VOC tuning setter, the async SPI transfers, `writeto_then_readfrom()`, FRAM `verify_present()`/`set_write_protected()`/`get_write_protected()`/`get_size()`), with its caller discipline stated: FRAM's `verify_present()`/`set_write_protected()` are never called while holding the FRAM lock and are wrapped in a broad `try/except`; `writeto_then_readfrom()` is two transactions with no rollback, and a caller needing a repeated start passes `out_stop=False`.
- **Members**: G3.017, G3.108, G5.075
- **Provenance**: O — G3.017: OR36.a (3) ("These are functions of the hardware items … They remain as they are.")
- **Truth**: holds — G3.017: CRC16 has no production user (grep: only `CRC_Pass`, `CRC8`, `CRC32` are imported), COBS unused, `get_altitude()` has no `src/` caller (others: G3.108 holds, G5.075 holds)
- **Fit / pillar**: restates OR36.a (3); bounds OR46.a (2) dead-code removal; extends OR36.a (3) (general-purpose API); restates OR36.a (3) · pillar P4 (all members)

### HR085 Local time uses legacy EU DST rule
- **Req**: `cettime()` applies `DSTOffset` between the last Sundays of March and October (01:00 UTC) to the configured GMT/DST offsets, copied verbatim from deployed legacy, and `NTP_Offset_S` shifts the RTC and every stored timestamp; the EU-only switch rule is an accepted limitation documented in SPECIFICATION.md/DEVICE_REFERENCE.md.
- **Members**: G6.061, G9.080
- **Provenance**: A — G9.080: legacy parity; not recorded as a decision anywhere.
- **Truth**: holds — G6.061: not independently verified against a calendar (N137) (others: G9.080 holds)
- **Fit / pillar**: restates CLAUDE.md "verify against legacy field behaviour"; new (undocumented limitation, OR5.a closure) · pillars differ: G6.061 P4, G9.080 P1

### HR086 Drivers never round; renderer rounds once
- **Req**: No firmware driver rounds an emitted value; a field's display precision is its `decimals` hint, applied in `formatFieldValue()` as the one rounding point in the stack.
- **Members**: G3.109, G7.079
- **Provenance**: O — G3.109: SPEC M.1.1 owner list, requirement 19
- **Truth**: holds — G3.109: `round(` appears in `src/` only for a threshold count (`asy_isl29125_driver.py:1235`) and a sleep (`asy_sgp40_driver.py:574`) (others: G7.079 holds)
- **Fit / pillar**: extends OR43.a (units and ranges); new (owner decision) · pillar P4 (all members)

### HR087 Website XSS-safe by construction under LAN model
- **Req**: Under the trusted home-LAN threat model the page needs no CSP, same-origin SRI or security headers; it stays XSS-safe by construction: every server- or user-supplied string is inserted with `textContent`, never `innerHTML`, the build escapes every `<` in inlined JSON so `</script` cannot close the tag, both are enforced by a check rather than review alone, and any future cross-origin resource requires SRI.
- **Members**: G5.091, G7.075
- **Provenance**: O — G7.075: OR52.a (3) "Threat model: trusted home LAN"; `textContent`-only is A (`15ed282`).
- **Truth**: partly — G5.091: 0 `innerHTML` in `js/` (grep) and the escape exists; no eslint rule enforces it (`eslint.config.js` has no `no-restricted-*`), and `tests_js/templates.test.js:502-570` covers hostile labels/values but not keys that reach selectors/ids (others: G7.075 holds)
- **Fit / pillar**: extends OR52.a (3); restates OR52.a (3) · pillars differ: G5.091 P2, G7.075 P4

### HR088 Envelope code keeps legacy 0-5, one catalog
- **Req**: Every REST reply keeps the legacy envelope `{res, code, descr, result}`; `code` draws from one documented catalog in which 0-5 mean what they meant in legacy and legacy special codes 6-10 are replaced by per-field result words; every catalogued code has a live producer, HTTP status codes are not reused as envelope codes unless the catalog says so, and `descr` text is not a contract.
- **Members**: G9.059, G10.078
- **Provenance**: A — G9.059: code comment "generalizes the legacy special_err closed Literal enum into an open set, same envelope shape".
- **Truth**: partly — G10.078: two code spaces in one field; two dead catalog entries (OR46.a leftover candidates) (others: G9.059 holds)
- **Fit / pillar**: refines OR24.a (2); refines OR24.a (2) (public interface: change with `js/`), OR46.a · pillar P4 (all members)

### HR089 Formulas keep source-validated domains
- **Req**: Derived values (wet bulb, dew point, absolute/relative humidity, barometric sea-level pressure, EMA with a coefficient outside (0, 1] meaning off, McCamy CCT) keep the legacy formulas and are gated to the domain their published source validates, cited where it differs from legacy: Stull wet bulb -20..50 °C and 5..99 %RH, McCamy CCT 2000..12500 K, barometric reduction 300..1250 hPa and -40..85 °C from the BMP3xx datasheet.
- **Members**: G3.008, G9.072
- **Provenance**: F — G3.008: BMP390 datasheet "Operating range -40 ‒ +85 °C, 300‒1250 hPa" (dstxt bmp390 line 86); Stull (2011) and McCamy (1992) papers not in the repo
- **Truth**: partly — G3.008: code bounds equal the stated domains; the BMP bound is confirmed; the Stull and McCamy domains are unverifiable here (papers not reachable) (others: G9.072 holds)
- **Fit / pillar**: refines OR4/OR51.a (2) (primary-source recheck); refines OR48.a · pillar P4 (all members)

### HR090 Shared test helpers live once
- **Req**: A test double or helper used by several files (the coroutine driver `run()`, fast-sleep and fake-time doubles, `_RaiseOnArm`, `_wlan()`, raising FRAM fakes, bus/FRAM builders, frame builders, live-twin harness code) exists once in a shared `tests/_*.py` or `tests_js/_*.js` module and is imported, Part G's 'reuse before writing' applied to tests; no rule requires test files to be self-contained.
- **Members**: G2.041, G10.060
- **Provenance**: O — G2.041: OR24 "one material", OR46.b "adopt the solutions at any place they improve code tidyness"
- **Truth**: drifted — G2.041: `_RaiseOnArm` exists in 7 files and `_FastAsyncSleep` in 10; `test_ntp_fram_system_integration.py:57-58` and `test_setter_microdot_integration.py:5-10` cite a self-containment convention SPEC Part E does not contain (grep), while 13 shared `tests/_*.py` modules exist (others: G10.060 partly)
- **Fit / pillar**: restates OR24 for tests; extends Part G to tests; OR39.a (3) (test-suite tidiness), OR24 · pillar P4 (all members)

### HR091 SIGINT override proven, then heap unwedge retired
- **Req**: Every Unix-port binary the project builds or runs has `MICROPY_ASYNC_KBD_INTR=0` forced by the `unix_kbd_intr` override through `setup_toolchain.py` (no other build path), proven by a post-build check of the binary; once that proof exists, `digital_twin/unix_port_gc_unwedge.py`, its test and its call sites are retired, and SPECIFICATION.md F.6 keeps the mechanism and the correct recovery (`gc.collect()`, not `micropython.heap_unlock()`) so it can be restored. `src/` needs no SIGINT path (rp2 has no signals).
- **Members**: G4.059, G7.023, G8.050, G9.042
- **Provenance**: O — G4.059: OR52.a (6) ("retire if it's no longer needed but document how it was done")
- **Truth**: drifted — G7.023: at HEAD the helper is wired at `run_generic_integration.py:395, 435` and `launch.py:432`, and F.6's amendment (`SPECIFICATION.md:4119-4133`) and CLAUDE.md say the calls are "kept, deliberately, as defense in depth" — both superseded by OR52.a (6); the retirement's precondition (a test proving the … (others: G4.059 holds, G8.050 partly, G9.042 partly)
- **Fit / pillar**: restates OR52.a (6); restates OR52.a (6); conflicts SPEC F.6 amendment/CLAUDE.md bullet (later owner row wins) · pillars differ: G4.059 P4, G7.023 P4, G8.050 P5, G9.042 P4
- **Note**: G7.023 records SPEC F.6's amendment and CLAUDE.md calling the calls 'kept, deliberate'; resolved by OR52.a (6) (owner, 2026-09-26), the later row.

### HR092 Every dev tool pinned exactly and enforced
- **Req**: Every dev-group tool (ruff, mypy, shellcheck, actionlint, zizmor, pytest, mpremote ...) and stub package is pinned to an exact version in `pyproject.toml` and bumped deliberately with `lint.sh`/`typecheck.sh` re-run, since `select = ["ALL"]` and zero-finding gates turn an unchosen upgrade into red CI; CI's `uv sync` uses the lock (`--locked`), uv itself and the npm dev tools are held to a lock or pin, and `lint.sh`/`typecheck.sh` fail when run from an inactive or stale venv or a bare `python3` instead of using whatever is on PATH.
- **Members**: G5.084, G8.086, G8.115
- **Provenance**: A — G5.084: CLAUDE.md text (agent), after an unpinned mypy 2.3.0 broke CI (PR #23)
- **Truth**: drifted — G8.115: `pytest` and `mpremote` are unpinned (`pyproject.toml:23-24`) against the "every tool pinned" comment and CLAUDE.md; `pip install uv` is unpinned in every lane; `uv sync` runs without `--locked`; npm tools are caret ranges held only by `package-lock.json` + `npm ci` (others: G5.084 not checked, G8.086 partly)
- **Fit / pillar**: restates CLAUDE.md; extends G8.115 (pins); extends P8, OR50.a (1) · pillars differ: G5.084 P5, G8.086 P4, G8.115 P4

### HR093 Three strict mypy passes, always run
- **Req**: Three mypy passes run `strict = true` plus `no_implicit_optional` and `warn_unreachable`: the main MicroPython-stub pass (`src tests`, where `tests/machine.py` stands in for `machine`), the twin pass and the host CPython pass, separated because mypy resolves each bare module name to one file per run (name collisions such as a bare `conftest` are split into named modules and a stub gap masked this way is recorded). Only the main pass exempts `no_implicit_reexport`, and `disallow_untyped_decorators` is off only for `tests/test_setter_microdot_integration.py`; exclusions are named directories with a reason; the three configs' strictness is kept identical by a check; `typecheck.sh` regenerates `build/generated_src/` first and always runs and fails on the twin and host passes whatever arguments narrow the main pass.
- **Members**: G2.069, G8.088, G8.089
- **Provenance**: A — G2.069: agent sessions (`confirmed directly` in CLAUDE.md)
- **Truth**: partly — G8.089: strictness holds; the three configs are "synced by hand (INI has no include)" with no check (SCR.N160); CLAUDE.md's exclusion list omits `tests/_webserver_concurrency_scenarios.py` and `_digital_twin_construction_scenarios.py` (drift, SCR.N182); `tests_scripts/conftest.py` stays unchecked (accepted … (others: G2.069 unverifiable, G8.088 holds)
- **Fit / pillar**: extends OR46.a (imports); restates CLAUDE.md scope; extends P4 · pillars differ: G2.069 P5, G8.088 P4, G8.089 P4

### HR094 CI supply chain: least privilege, pinned, audited
- **Req**: The workflow sets `permissions: {}` and each job grants itself only what it needs (`contents: read`), every job has a kebab-case id and `timeout-minutes`, and every checkout sets `persist-credentials: false`; first-party `actions/*` are tag-pinned and every third-party action SHA-pinned and bumped by hand (no Dependabot). zizmor enforces this, always runs `--offline` (identical in CI, dev box and chroot), keeps every other audit at its default so a new release surfaces new checks, and disables `self-repository` only until actionlint accepts `uses: $/.github/...`.
- **Members**: G8.109, G8.110, G8.111, G10.075
- **Provenance**: A — G8.109: `bfaf4c6` (2026-09-10)
- **Truth**: drifted — G8.111: CLAUDE.md:493-494 and `zizmor.yml:1-2` say "Only `unpinned-uses` is configured" while `self-repository` is configured too (CI.N161) (others: G8.109 holds, G8.110 holds, G10.075 holds)
- **Fit / pillar**: new (supply-chain floor); new; restates CLAUDE.md, OR30.a (timeouts are tunables) · pillar P4 (all members)

### HR095 Eight lint scopes, zero findings, day one
- **Req**: `ruff`, `shellcheck`, `actionlint`, `zizmor` and all three mypy passes report zero findings over the eight scopes; a new generator, validator or other host module joins the ruff/mypy scope from its first commit and CI's explicit path arguments follow the lint scope; `ruff format` is never run; the legacy tree (`python/`, `modules/`, the four `build-*.sh`) is never in any lint, type or CI scope.
- **Members**: G8.084, G8.133
- **Provenance**: O — G8.084: CLAUDE.md:170 "The legacy tree is reference-only, forever … (project owner, 2026-09-11)"; zero-findings bar A (`c0dfd20`, 2026-07-13)
- **Truth**: holds — G8.084: `lint.sh:13` covers the eight scopes, shellcheck `scripts/*.sh` only; "28 findings" in legacy scripts is a dated count (others: G8.133 holds)
- **Fit / pillar**: restates CLAUDE.md; P4; extends OR23.a (1) · pillar P4 (all members)

### HR096 Unix-port divergences shimmed in tests, proven on target
- **Req**: Where the Unix-port rig differs from rp2 (socket `bind`/`sendto`/`connect` rejecting a `(host, port)` tuple, micropython#6924; raw `recvfrom()` sockaddrs; 9-element `gmtime()`; missing `settimeout`; leaked poll registrations; 64-bit words and allocation boundaries; double floats; the tick period; `select.poll()`/`ipoll()` readiness on Python streams and UDP sockets; `getsockname()`/packed `getaddrinfo()` gaps; bound-method identity; private `asyncio.core` internals), the difference is worked around only in test code, recorded in SPEC Part F with its source and a removal trigger, and the rp2 behaviour is proven on the twin or silicon or the test states the divergence. Twin entry points apply `_unix_port_udp_addr_shim` before any socket exists, passing only numeric addresses; the port-53 DNS test runs only with `CAP_NET_BIND_SERVICE` and a failed bind fails the run loudly.
- **Members**: G2.051, G4.056, G7.022
- **Provenance**: F — G2.051: v1.29.0 `ports/unix/modsocket.c:231,376` take the address as a raw buffer; `ports/unix/modtime.c:138` builds a 9-tuple vs `extmod/modtime.c:65` 8; github.com/micropython/micropython/issues/6924 closed with the port unchanged
- **Truth**: partly — G2.051: shims are test-side only; none names a removal trigger; SPEC Part F records neither #6924 nor the gmtime length (grep), so the rp2 tuple path is unexercised below the bench (others: G4.056 holds, G7.022 partly)
- **Fit / pillar**: refines OR29.a (3); refines OR45.a (2)(b); extends OR38.a (3) (port 53 fixed-port use) · pillar P5 (all members)

### HR097 Code and fakes model rp2's real raise surface
- **Req**: Bus wrappers and fakes model exactly the rp2 raise surface of the pinned MicroPython: hardware I2C raises `OSError(EIO)` for a NAK or non-timeout failure and `OSError(ETIMEDOUT)` for a stalled or stretched bus, while a zero-length I2C write (presence probe, `scan()`) goes through the soft-I2C path and raises `ENODEV` on NAK; SPI `write()` never raises and a 32+ byte DMA read can raise EIO; UART faults arrive as sentinels, never exceptions: framing, parity and overrun errors deliver or lose the byte, break bytes are dropped, `read()` answers `None` on an empty ring (even after `any()` said otherwise), `write()` may short-write or return `None`, `any()` has no raise site, every loop ends on those sentinels, and the driver caches its construction values because `machine.UART` has no getters.
- **Members**: G3.024, G4.015, G4.020
- **Provenance**: F — G3.024: `ports/rp2/machine_i2c.c:127-154`; `extmod/machine_i2c.c:203` (`return -MP_ENODEV` on NAK); `ports/rp2/machine_spi.c:267, 341`; `ports/rp2/machine_uart.c:640-660`
- **Truth**: wrong — G3.024: SPEC C.12 "real hardware only raises `OSError(EIO)` or `OSError(ETIMEDOUT)` — never `ENODEV`" does not hold for zero-length writes, which the presence probe (`asy_i2c_driver.py:266`) uses; behaviour is safe (the probe catches every OSError), the spec and the fakes' model are not. SPI and UART … (others: G4.015 holds, G4.020 holds)
- **Fit / pillar**: refines OR29.a (2) (corrected fact); refines OR26.a · pillars differ: G3.024 P5, G4.015 P2, G4.020 P2
- **Note**: Contradiction: G4.015 says I2C never raises `ENODEV` (SoftI2C's); G3.024 shows the zero-length-write probe path does (`extmod/machine_i2c.c:203`). Resolved by that source (F) in G3.024's favour; SPEC C.12's 'never ENODEV' is wrong for probes.

### HR098 Unix-port poll-set prewarm; rp2 unaffected
- **Req**: Every entry point that boots a device with real sockets under the Unix port calls `prewarm_poll_set()` as its first statement, because `extmod/modselect.c` rebases non-fd poll entries' NULL `pollfd` into a dangling pointer when `pollfds` grows; the workaround stays until upstream fixes the growth path, an upstream issue is filed for the residual case, and the 512-slot margin is re-checked against the highest concurrency any tier drives. The defect is compiled out of rp2 firmware, so the bench burst test is standing robustness validation, not a regression test for it.
- **Members**: G1.036, G7.021
- **Provenance**: F — G1.036: MicroPython v1.29.0 py/mpconfig.h:1892-1893 (`MICROPY_PY_SELECT_POSIX_OPTIMISATIONS` defaults to 0; rp2 defines no override)
- **Truth**: partly — G7.021: mechanism confirmed at v1.29.0; the first-statement rule is convention only: `tests/test_digital_twin_run_generic_integration.py` boots a device through `main()` without importing the prewarm; no upstream issue filed (TWIN.N365); port 0 is unusable because the Unix port has no `getsockname()` … (others: G1.036 holds)
- **Fit / pillar**: restates digital_twin/README.md; extends OR4 (upstream sources), OR5 (removal trigger) · pillar P5 (all members)

### HR099 Unix-port runs pin TZ=UTC and rp2 time shapes
- **Req**: Every runner that starts the Unix-port interpreter (unit, twin and every other) exports `TZ=UTC`, because the Unix port's `time.mktime()` calls host libc local-time `mktime()` while rp2's is TZ-agnostic, so a result under any other TZ is not meaningful; unit and twin code normalise `gmtime()` to rp2's 8-element tuple, a path reachable only on one shape is tested on that shape, and `sleep(0)` never advances wall-clock time in tests.
- **Members**: G2.007, G4.039, G8.094
- **Provenance**: F — G2.007: MicroPython v1.29.0 `ports/unix/modtime.c:191` calls libc `mktime(&time)`; rule text A (`f936c84` doc prune moved it)
- **Truth**: holds — G2.007: `scripts/test.sh:23`; `tests_scripts/test_coverage_runner.py:35` mirrors it (others: G4.039 holds, G8.094 holds)
- **Fit / pillar**: new (platform fact the unit tier depends on); refines OR45.a (4) (tier scope); extends OR20.a (host environment faithful to target) · pillar P5 (all members)

### HR100 Every MicroPython run gated on both allocation markers
- **Req**: Every gate that judges a MicroPython run (unit, twin CI, flash, bench, and the JS/cross-browser live twins) matches `MemoryError` or `memory allocation failed` (the second being what a caught-and-logged failure prints, since `src/` logs `str(e)`) and fails on either, a passing file included; all gates read one marker set (`harness.MEMORY_ERROR_MARKERS` for the hardware pair) kept in agreement by `test_memory_error_gate_agreement.py`, and the suite's deliberate injections are worded clear of both. `test.sh` judges each file's deciding attempt (a timed-out earlier attempt's partial output does not count) and names the files in its summary; a bench crash oracle watches the device log throughout the fault and recovery window, not a tail taken afterwards, matches traceback and allocation markers, and checks every logger the fault can reach (WEBSERVER and SYSTEM included); a device stability verdict needs zero true failures and zero marker lines.
- **Members**: G1.049, G1.050, G2.012, G4.071, G8.079
- **Provenance**: O — G8.079: CLAUDE.md memory-safety rule ("Both halves are machine-checked … a degrade-and-pass is the silent case the bar is about"), OR40.a (2); F — v1.29.0 `py/runtime.c:1692,1696` wording
- **Truth**: partly — G1.049: crash checks grep only "Traceback" in a 5 s tail after the fault (test_network_resilience.py:156-158); the first bus test checks five loggers and no task-ended/WEBSERVER state (:134-138) (others: G1.050 partly, G2.012 partly, G4.071 partly, G8.079 holds)
- **Fit / pillar**: refines OR21.a (1); restates CLAUDE.md four-gate rule; refines OR40.a (2); extends OR40.a (2); refines OR40.a (2), OR21.a (1); restates OR40.a (2) · pillar P5 (all members)

### HR101 Hardware results count only on verified images
- **Req**: A hardware sitting first reads and saves `errcount`, then builds and flashes a `dev` image of the tree under test; a result counts only once the image is proven to be that tree (`/system`'s `build.buildDate` and the lwIP ensemble checked), and oracles computed from the tree (ceiling, served website, allocation needs) run only after that check, with a local-only image reverted at once. It runs flash then bench tiers, spends flash/NVM writes only in a gated run after a clean default run, reads every verdict's deselected count, stops and reports any red step its plan did not anticipate rather than working around it, and caps every ad-hoc retry and runs ad-hoc scripts under `timeout`.
- **Members**: G1.002, G1.056
- **Provenance**: O — G1.002: BACKLOG.md:353 "the owner's standing answers (2026-09-22)" (D1-D3); retry cap A (0154aec)
- **Truth**: partly — G1.056: the sitting order and README rule state it; no test or fixture compares `buildDate` or the image hash with the tree before tree-derived oracles run (e.g. `configured_max_connections()` "describes the TREE, not necessarily the image", harness.py:39-41) (others: G1.002 holds)
- **Fit / pillar**: refines OR5.a (2), OR17.a (5), OR28.a (1); refines OR29.a (4), OR45.a (2)(a) · pillars differ: G1.002 process, G1.056 P5

### HR102 A heap figure states how it was taken
- **Req**: A heap figure is valid only with its scope written down: the GC threshold in force (every measuring script or harness sets its own `gc.threshold()` and prints `GC_THRESHOLD=`, since a raw-REPL soft reset keeps the firmware's; a figure without it is void), the image, the position in the boot/serving sequence or suite, production boot versus isolated build, the instrument's own cost, and whether it is a sampled minimum. Samples follow a settling collect, offered load never scales with the setting under test, ballast guards use the largest free run, instrumentation goes into a staged build (never committed, never `exec()`'d into a live system), allocating instrumentation never yields a headline, a control-flow-changing substitution is not an isolation, quarantined figures from a defective instrument are never reused, the bisecting probe runs after the last map dump, and a derived threshold's first silicon failure is a finding, not automatically a regression.
- **Members**: G1.061, G1.062, G4.079
- **Provenance**: A — G1.061: HEAP_FRAGMENTATION_MEASUREMENTS.md (condensed by 17b4354, 2026-09-24)
- **Truth**: holds — G1.061: stated as rules in the file; enforced only by review except the threshold half (G1.062) (others: G1.062 holds, G4.079 holds)
- **Fit / pillar**: refines OR39.a (2), OR40.a (3); refines OR40.a (2)-(3); refines OR29.a (4), OR49.a (3) · pillars differ: G1.061 P5/P7, G1.062 P5, G4.079 P7

### HR103 Instruments run in the twin before silicon
- **Req**: Every new or changed device script or instrument runs once against the digital twin (`twin_wrap`) before it is queued for silicon. When a hardware test goes red, the first check is whether it asks the right question of the right endpoint and field and whether its instrument has ever executed correctly; a first-run silicon failure of a never-executed instrument is treated as a harness bug until proven otherwise.
- **Members**: G1.003, G1.076
- **Provenance**: O-confirmed — G1.076: OR29.a (4) "is run once against the digital twin before entering the queue"
- **Truth**: not checked — G1.076: not checked (no record per script) (others: G1.003 holds)
- **Fit / pillar**: refines OR6 (investigate every failure); restates OR29.a (4), OR21.a (1) · pillars differ: G1.003 process, G1.076 P5

### HR104 Test processes exit explicitly; one boot each
- **Req**: A test runner that shares one process-wide asyncio task queue ends with an explicit process exit: `microtest.run()` always ends with `sys.exit()` (0 all-pass, 1 on any failure) after scratch teardown in `finally`, because MicroPython's asyncio has no parent/child task tracking and cancelling one task never reaches its siblings; a `tests/` file boots the real supervised task graph at most once per process.
- **Members**: G2.004, G7.045, G9.040
- **Provenance**: F — G9.040: `mp/extmod/asyncio/task.py` has no child-task registry (its `ph_child` is the pairing heap); `tests/microtest.py:42` calls `sys.exit()`.
- **Truth**: holds — G2.004: `tests/microtest.py:42`; `tests/_boot_contiguity_probe.py:161` does the same (others: G7.045 holds, G9.040 holds)
- **Fit / pillar**: restates CLAUDE.md; refines OR38.a (1); extends OR38.a (1) (no leftovers across tests) · pillar P5 (all members)

### HR105 Tests restore state and leave nothing running
- **Req**: A test that mutates process-wide state (class registries such as `Timer.all_timers`, `raise_on_arm`, RTC/pin/wiring-plan state, module globals, `gc.threshold`, `sys.modules`) restores it in `finally`, and no test depends on the run order of its file (MicroPython's `globals()` does not preserve it). A test that starts a background task keeps a reference and cancels and awaits it in its own `finally`; every host-side load or holder thread is stopped and joined on every path and reports transport and HTTP-protocol failures instead of dying silently; JS harnesses clear their own timers and child processes.
- **Members**: G1.079, G2.018, G2.019
- **Provenance**: O — G2.018: OR38.a (1) "Each test cleans up after itself on every path ... never relying on a later test"; order rule A (`c5478f0`); F: globals map is not ordered (v1.29.0 `py/objdict.c` sets `is_ordered` only for ordered dicts)
- **Truth**: partly — G1.079: in-test teardown asserts hold; the HTTP_ERROR guard misses workers with no `try`, positional Thread targets, helper-routed fetches and flash/device_scripts (test_bench_harness_helpers.py:98-125) (others: G2.018 partly, G2.019 partly)
- **Fit / pillar**: refines OR38.a (1); restates OR38.a (1) · pillar P5 (all members)

### HR106 Every tuned value is a registered tunable
- **Req**: Every tuned (not derived) value, in the product (UART GC-pause, jitter, gate-step and diagnostic-streak constants, NTP retry/timeouts, WiFi settle and poll delays, UDP backoff, webserver timeouts and body cap) and in every test tier (sleeps, bounds, loopback budgets, per-file/suite timeouts, Vitest backstop, speed-probe thresholds, hardware waits, retries, soak durations, settle sleeps, tolerances, allocation and heap-rate budgets, twin durations and warm-ups, CI `timeout-minutes`), has an entry in the OR30 tunables register stating its basis (measurement with date, image or binary and run count; datasheet; or the named product constant it derives from), its margin and its re-check trigger, moves with any value it derives from, is sized so host load cannot fail a healthy test, marks a single dated observation as such, and states any accepted blind spot with the value; a budget is never widened on an unproven hypothesis and a job near its ceiling is recorded with its numbers.
- **Members**: G1.068, G2.048, G4.080, G6.062, G7.038, G8.113
- **Provenance**: O — G2.048: OR30/OR30.a (1) "per-file timeouts and retries ... twin run and soak durations"
- **Truth**: partly — G1.068: most values carry a one-line basis, many rest on one observation (e.g. slot release 0.71-0.84 s, harness.py:60; 45 s settle, scd30_plausibility_read.py:15; `_MIN_RATIO = 5` from one 20.6x reading, uart_idle_poll_rate.py:17-20); no `@tunable` tag exists yet (OR30 not executed); … (others: G2.048 partly, G4.080 partly, G6.062 partly, G7.038 partly, G8.113 partly)
- **Fit / pillar**: restates OR30.a (1)-(3) for L3/L4; restates OR30.a; restates OR30.a (1)-(3) · pillars differ: G1.068 P5/P8, G2.048 P5, G4.080 P5, G6.062 P8, G7.038 P8, G8.113 P5

### HR107 Skips visible; a vacuous check never passes
- **Req**: Every skip, deselect and opt-in gate is listed with a still-valid reason and counted in the run's summary; a skip caused by a missing build (Unix port, settrace variant, generated tree, toolchain) is never reported as a pass, and a hard prerequisite (e.g. `node`) fails rather than skips consistently across tiers. A scenario or check that finds nothing to exercise reports skipped or fails, never PASS; a test that tolerates failures, a ceiling or a no-op outcome also asserts a minimum engagement (answered requests, interleaved reads, range switches, dropped callbacks, link transfers), and a fault injection proves it took effect.
- **Members**: G1.047, G2.054, G2.055
- **Provenance**: O — G2.054: OR21.a (3) "a test that passes with nothing actually checked is reported as such"
- **Truth**: partly — G1.047: floors exist in the ISL, SCD30/SGP40 and ceiling tests; no floor in test_bus_concurrency_under_api_load.py:172-341 (a run with zero successes passes), test_memory_stress_bench.py:53-55 (non-200s never asserted), scheduler_saturation_drop.py:43-55 (passes with 0 dropped), … (others: G2.054 partly, G2.055 partly)
- **Fit / pillar**: restates OR21.a (1); refines OR19.a red flags; restates OR21.a (3); restates OR16.a (2) · pillar P5 (all members)

### HR108 Every twin scenario has a hardware counterpart
- **Req**: A behaviour tested on several backends lives once in a backend-agnostic helper (importable under MicroPython and CPython) whose docstring states the backends it applies to, without forcing genuinely backend-specific coverage into sharing. Every mock/twin test of hardware-facing behaviour has a real-hardware counterpart wherever technically possible, every flash-tier bus hazard has a bench-tier counterpart through the REST stack (bench contains flash), and each asymmetry that cannot close is a named structural exception with its reason (only `dev` benched; no FRAM write-protect route; SCD30 IRQ edge; SGP40 general call at setup only; UART fault catalog, GPIO fault harness and CYW43-firmware faults need hardware the bench lacks; `lightCmdLED`/WS2812 timing).
- **Members**: G1.044, G2.061
- **Provenance**: O — G1.044: SPECIFICATION.md:3197 "Standing rule (project owner's direction)"; C.8 flash⊂bench rule; UART catalog exception "answered 2026-09-22"
- **Truth**: partly — G1.044: bench ⊇ flash holds by execution (run_bench_hardware_suite.sh runs flash + bench); exception 1 is wrong for SCD30 (G1.045); scenario containment of the 31 twin files is unmeasured (OR45.a) (others: G2.061 partly)
- **Fit / pillar**: restates OR45.a (2)(b), (3); CLAUDE.md four-tier bus-hazard rule; restates OR45.a (2)(b) · pillar P5 (all members)
- **Note**: G1.044's truth notes its exception list is wrong for SCD30's same-device write (see singleton G1.045: SCD30 NVM is REST-reachable).

### HR109 Test logic and load live outside the DUT
- **Req**: Twin and hardware tests drive and assert from a host process outside the DUT: request driving, history, verdicts, soak loops and load generation live host-side, host clients drain response bodies rather than buffer them, and the DUT emits only values that exist nowhere else (`gc.mem_free()`) through the narrowest channel, a fixed-timer log line; a fix under this rule must catch the real case strictly better, never merely lighten the DUT.
- **Members**: G1.075, G2.062, G7.040
- **Provenance**: O — G2.062: OR20.a
- **Truth**: partly — G2.062: `_webserver_concurrency_scenarios.py` still runs its client in the DUT's heap (in-process twin tier) (others: G1.075 holds, G7.040 holds)
- **Fit / pillar**: restates OR20.a · pillar P5 (all members)

### HR110 Browser floor current Chromium, Firefox, Safari
- **Req**: The website runs on current Chromium, Firefox and Safari, desktop and mobile; shipped JS/CSS uses only features within that floor, stated once, with lint/type settings bounding `js/` to it. The full browser matrix runs on Chromium through Vitest, and a deliberately narrow cross-browser smoke drives each engine (Chromium, Edge, Firefox, WebKit) in its own single session against a real booted twin at desktop and mobile widths, with a unique probe value per check, waiting on the rendered result and stating engine limits; in CI all engines are installed and a skipped engine fails, locally it warns. Firefox, geckodriver and micromamba come deliberately unpinned from conda-forge.
- **Members**: G2.065, G7.071, G7.072, G8.102
- **Provenance**: O — G2.065: PQ10 answer "browser floor current Chromium, Firefox, Safari"; narrow scope A
- **Truth**: partly — G7.071: features used (private fields, `replaceChildren`, `toFixed` to 100, range media queries, `min()`) are within current engines; `ecmaVersion: "latest"` bounds nothing; the floor is stated nowhere in SPECIFICATION.md; no real Safari/mobile pass exists (BACKLOG.md:833-837 "needs the project owner … (others: G2.065 holds, G7.072 holds, G8.102 partly)
- **Fit / pillar**: restates PQ10; refines OR45.a (L0 website tier); refines PQ10 browser floor · pillars differ: G2.065 P5, G7.071 P4, G7.072 P5, G8.102 P5

### HR111 Twin fakes independent, held to shared contracts
- **Req**: The digital twin's fakes (`machine`, `network`, `neopixel`, chip fakes, CRC8, fault injector) are independent reimplementations: they never import `tests/` fakes or `src/` helpers and are never imported by them, so a bug shared between oracle and code under test cannot hide. Where the unit tier and the twin model the same peripheral or expose the same test-facing API (UART link, stall counting, `readfrom_mem_into()` delegation, machine constants, fault queue `inject_fault()`/`maybe_raise()`), both follow one convention and one shared contract suite: they may differ in fidelity, never in semantics, and a new `machine` constant or method goes into both together.
- **Members**: G2.035, G2.036, G7.001
- **Provenance**: O-confirmed — G7.001: `b8791e6` (2026-08-12): "Kept fully independent from tests/machine.py per the owner's explicit instruction - a separate module, never imported by or importing it"; the CRC/FRAM "deliberately not shared" wording is A (`3795d93`).
- **Truth**: partly — G2.035: UART link held by `_uart_link_contract.ALL_CHECKS` run against both; the two fault-injection APIs (`tests/machine.py` `inject_fault()` vs `digital_twin/_fault_injection.py`) are equal by convention only (others: G2.036 holds, G7.001 holds)
- **Fit / pillar**: extends P8; conflicts P8/OR24 one material (duplicated fakes) — see Conflicts; refines OR17 (twin as an independent oracle) · pillar P5 (all members)
- **Note**: G2.036 flags a tension with P8 'one material' (duplicated fakes); resolved by the owner's explicit instruction to keep them independent (`b8791e6`).

### HR112 Emitted JSON checked by the strict oracle
- **Req**: Every test that asserts output is valid JSON (streamed routes included) parses it with the strict RFC 8259 recogniser `tests/_strict_json.py`, never MicroPython's `json.loads()`, which treats `,` and `:` as whitespace and accepts separators `JSON.parse()` rejects; the recogniser rejects duplicate keys, and code relying on MicroPython's last-wins duplicates or non-`str` key emission states it.
- **Members**: G2.028, G4.029
- **Provenance**: F — G4.029: `extmod/modjson.c:170-177`; A (`cca4fd3`, closing coverage-audit gaps)
- **Truth**: partly — G2.028: used by streamed-body tests; no check that every emitted-JSON test uses it; duplicate keys pass (`_strict_json.py:83-98`) (others: G4.029 holds)
- **Fit / pillar**: new (closes a parser-oracle gap); refines OR19.a (checks that can fail) · pillar P5 (all members)
- **Note**: G2.028 requires the recogniser to reject duplicate keys and records that it does not today (`_strict_json.py:83-98`).

### HR113 Fakes model what src relies on, with sources
- **Req**: A fake models the real peripheral's semantics wherever `src/` depends on them (internal consistency with `src/`, not bit-for-bit silicon). Every semantic or port constant it models on purpose (pin constants, `DMA_MIN_SIZE_THRESHOLD`, UART id/buffer bounds and check order, `deinit()` no-ops, `write()` returning None on TX timeout, Timer init-helper rule, WDT cap, `WDT.feed()` allocating nothing, FRAM WEL, stream poll code, NeoPixel busy-wait) cites the datasheet page or pinned source line, is pinned by the fake's own tests and re-checked at every pin move; a knob modelling non-datasheet behaviour says so; every known gap is stated in the fake and in the twin fidelity table, and a gap that can hide a real defect is closed or covered at a higher tier.
- **Members**: G2.031, G2.032, G4.057
- **Provenance**: A — G2.031: `tests/network.py:8-9` SETTLED by an agent; O-backed by OR17 ("models the real hardware as close and as correct as possible") for the twin
- **Truth**: partly — G2.031: most gaps are stated inline; `tests/machine.py:51-54` implies `pull` is honoured (it is not); dev's 256 KB FRAM fake keeps the 8 KB, 2-byte address model (`tests/_sensortask_scenarios.py:65-72`) (others: G2.032 partly, G4.057 partly)
- **Fit / pillar**: extends OR17 to the unit tier; refines OR29.a (2); restates OR17.a (2) · pillar P5 (all members)

### HR114 Two full GC stages on every tier
- **Req**: Every tier that runs MicroPython runs its whole suite first at `gc.threshold(-1)` and then at the shipped 32768, each stage verified on its own with zero allocation failures (the twin CI suite: its whole run sequence twice per device). The shipped value appears once, in the generated boot entry, and every test copy (twin default included) is derived from it or pinned to it; `GC_THRESHOLD` is validated to the RP2040's 32-bit range; no test overrides its file's stage except one whose subject is the threshold, which restores the value it found. The hardware tier covers the `-1` stage only partially until the final hardware phase, whose release proof runs a `dev` image without the threshold through the default flash and bench tiers, then the normal image.
- **Members**: G1.064, G2.010, G4.070, G7.034, G8.083
- **Provenance**: O — G1.064: OR40.a (3)
- **Truth**: partly — G2.010: unit tier (`ci.yml:454-469`) and twin CI suite (`_digital_twin_ci_suite.py:1310` both values) hold; `tests/test_asy_webserver_service.py` sets `gc.threshold` 58 times inside test bodies (item N307), so its hammer tests run their own stage, not the file's (others: G1.064 holds, G4.070 partly, G7.034 partly, G8.083 partly)
- **Fit / pillar**: restates OR40.a (3); restates OR40.a (2); restates OR40.a · pillars differ: G1.064 P5, G2.010 P6, G4.070 P5, G7.034 P5, P6, G8.083 P5

### HR115 gc.collect only at boot placement or baselines
- **Req**: Business logic calls `gc.collect()` only between the units of the two one-time boot setup lists (`system_service.start_and_check_tasks` and the generated boot batch: one before, one after each unit), never in the run phase or supervisor loop, enforced by site (lint and an AST test) and by effect (twin boot contiguity); the stretch between the two lists stays uncovered unless a measurement finds survivors born there. Test, twin, device-script and tool code calls `gc.collect()` only to settle a clean baseline for a memory measurement, lets it complete before measuring (never in the next statement), never inside a timed window, never as a recovery step or to keep a test from failing, and never inside a DUT whose verdict it judges; the rule is machine-checked over `tests/` and `digital_twin/` too, and a threshold change is never accepted as a memory fix.
- **Members**: G1.063, G2.011, G4.072, G4.073, G7.041
- **Provenance**: O — G1.063: OR39.a (1) "in tests only to set a clean baseline for a memory measurement, never followed by the measurement in the very next statement"
- **Truth**: drifted — G2.011: two props remain (`tests/test_fram_integration.py:177`, `tests/_webserver_concurrency_scenarios.py:861`, each justified in its comment as a Unix-port artifact/backstop); `scripts/lint.sh:42-49` and `tests_scripts/test_gc_collect_sites.py` guard only `src/`/`buildgen/`, and `lint.sh`'s comment calls … (others: G1.063 partly, G4.072 holds, G4.073 partly, G7.041 partly)
- **Fit / pillar**: restates OR39.a (1); gap: the timing-window use is not named in OR39.a; restates OR39.a (1); restates OR39.a (1), OR40.a (1); restates OR39.a (1), OR54.a (2); restates OR39.a (1); conflicts SPEC I.4 "don't re-flag" (later owner row wins) · pillars differ: G1.063 P4, G2.011 P6, G4.072 P6, G4.073 P5, G7.041 P5
- **Note**: G7.041 conflicts SPEC I.4's 'don't re-flag it without new evidence' for the twin sampler; resolved by OR39.a (1) (owner), the later row.

### HR116 Twin heap figures are twin tripwires only
- **Req**: Heap, fragmentation, contiguity, placement and throughput figures from the 64-bit Unix-port twin are harness baselines and regression tripwires only, never quoted as board figures; board memory claims come from L3/L4, a single-campaign twin figure carries its margin and date and is re-derived after a binary, manifest or object-graph change. `test_digital_twin_boot_contiguity.py` keeps its suppressed control arm, which must violate every bound, and bounds mirrored from the hardware script are pinned.
- **Members**: G2.060, G4.077, G7.014
- **Provenance**: O-confirmed — G2.060: CLAUDE.md "added 2026-09-18 with the owner's approval"; OR21.a (2) "existing control arms ... are left as they are"
- **Truth**: holds — G2.060: control arm present (`test_digital_twin_boot_contiguity.py:37-47`); probe constants equal the hardware script's (`heap_layout_after_full_boot_sequence.py:32-35`) but are unpinned (others: G4.077 holds, G7.014 holds)
- **Fit / pillar**: restates OR21.a (2); refines OR17.a (fidelity table); refines OR39.a (2), OR40.a (3) · pillars differ: G2.060 P6, G4.077 P5, G7.014 P5, P6

### HR117 Every bus chip gets a silicon conformance probe
- **Req**: Chip behaviour measured on real silicon overrides both datasheet and fake. Each bus-facing chip gets a conformance probe that talks only raw `machine.I2C`, runs identically on silicon and on the fake (the twin side under the same Unix-port binary and flags as `scripts/test.sh`; a missing Unix port is a skip with its cause), is diffed host-side with light- or environment-dependent keys compared only in an independent form, and has a pytest gate; a disagreement is decided from the datasheet plus a fresh measurement, never from the fake, and deliberately non-nominal fake parameters exist only where a test needs something to converge on.
- **Members**: G1.073, G2.064, G7.007
- **Provenance**: A — G1.073: SPECIFICATION.md C.11.1
- **Truth**: partly — G1.073: probe and diff hold; the twin run uses `-X heapsize=8M` and no GC-threshold stage while scripts/test.sh:369 uses 16M (isl29125_conformance.py:66); a missing build raises FileNotFoundError; the only conformance check sits behind the gated flash test (others: G2.064 partly, G7.007 partly)
- **Fit / pillar**: refines OR17.a (2)-(3) fidelity table; refines OR17.a (3), OR29.a (4); refines OR17.a (3)-(5), OR29.a (2) · pillar P5 (all members)

### HR118 One twin fidelity table names every gap
- **Req**: Every hardware fact the twin does not or cannot model (timers/IRQs, bus timing and electrical behaviour, chip functional gaps, network and lwIP, RTC advance, UART baud mismatch, TX backpressure, the `timeout_char` stall, repeated flapping) is listed once in a twin fidelity table with its evidence and the tier that proves it instead (L3/L4 test or hardware-queue row); the twin's UART and network fakes model the rp2/CYW43 behaviour the code relies on (crossover topology, `any()` draining the FIFO, overrun counted not raised, re-construction superseding an instance, radio byte bounds), and a property proven only at L2 is named as such.
- **Members**: G6.032, G7.008
- **Provenance**: O — G6.032: OR17/OR17.a
- **Truth**: wrong — G7.008: no fidelity table exists; `digital_twin/README.md` records gaps in prose at scattered places (grep "fidelity" finds only :114); BMP3xx compensation is validated only by a manual script; the default AutoRangeDwell is never run at L2. (others: G6.032 unverifiable)
- **Fit / pillar**: restates OR17.a; restates OR17.a (2); extends CONSOLIDATION §4 home ("`digital_twin/README.md` fidelity table") · pillars differ: G6.032 P5, G7.008 P5, P7

### HR119 No fault-injection hardware; catalog stays mock-only
- **Req**: No bench hardware is bought for fault injection: the ~20-scenario UART fault catalog is a structural exception that stays mock-only and is not improvised with a second raw UART, the GPIO fault harness and a second WiFi client stay permanently manual, and a babbling-UART-peer test waits for hardware that does not exist; no software stand-in claims their coverage.
- **Members**: G1.101, G6.035
- **Provenance**: O — G1.101: BACKLOG.md:193 "SETTLED 2026-09-22 (owner): no hardware will be bought"; BACKLOG.md:375 "(owner, 2026-09-25)"
- **Truth**: holds — G1.101: holds (others: G6.035 holds)
- **Fit / pillar**: bounds OR45.a (3) (listed exceptions); refines OR45.a (3) (listed exception, reviewed at audit close) · pillar P5 (all members)

### HR120 Expected values come from an independent source
- **Req**: A test's expected value comes from a source independent of the code under test (datasheet formula or worked example, second CRC implementation, independently written formula such as BMP3xx compensation or Newton inversion, hand calculation), hard-coded where it is wire bytes, never from the function under test or its current output; an exact reference is preferred where one exists, a sanity bound only where none can be derived, and a tolerance states the error budget it covers.
- **Members**: G2.026, G3.099, G7.047
- **Provenance**: O — G2.026: OR19.a (2) "Expected values come from an independent source ... never copied from current output"
- **Truth**: partly — G2.026: BMP3xx and SGP40 oracles are independent; `tests_js/_live_matrix_command.js:9-12` computes expected captions with the `formatFieldValue()` under test; SPEC D.12 asks for a sanity bound instead of an exact value (A, `2a558f5`) (others: G3.099 holds, G7.047 holds)
- **Fit / pillar**: conflicts SPEC D.12 wording (resolved by OR19.a, see Conflicts); restates OR19.a (2) (independent source); restates OR19.a (2) · pillar P5 (all members)
- **Note**: G2.026 notes SPEC D.12 asks for a sanity bound instead; resolved by OR19.a (2) (owner).

### HR121 Unreachable defensive branches: labelled, tested, registered
- **Req**: A defensive branch that no real input or normal flow can reach keeps its handler only as labelled defence in depth, in a module contracted never to raise, where SPECIFICATION.md E.5.1's register names its class (e.g. `Timer.init()`'s `MemoryError` arm, `ConfigManager`'s three type-mismatch catches, `get_log()`'s `_NO_WRN` arm); it is exercised through a double (a raising Protocol fake, a substituted name) or, if untestable, named in E.5.1 with its reason, is never left silently uncovered, and is not counted as dead code.
- **Members**: G2.057, G3.019, G5.013
- **Provenance**: O-confirmed — G2.057: `500851c`: "the general 'leave the catch, skip an untestable test, note why' convention ... confirmed directly by the project owner"; E.5.1 print_log sentinel "confirmed intentional by the project owner"
- **Truth**: partly — G2.057: E.5.1 register exists; the convention's own home (BACKLOG) is gone and not restated in Part D/E (item N744); `voc_algorithm.py`'s `_FIX16_OVERFLOW` unreachability is disputed (ALGO.S01) (others: G3.019 holds, G5.013 holds)
- **Fit / pillar**: refines OR25.a (3), OR26.a; refines OR16.a (3) ("justified" line); conflicts OR46.a (2) (confirmed leftovers incl. "unreachable branches" are removed) — see Conflicts · pillars differ: G2.057 P2, G3.019 P5, G5.013 P4
- **Note**: G5.013 flags a conflict with OR46.a (2) (confirmed leftovers, 'unreachable branches' included, are removed) against the owner-confirmed keep-and-note convention (`500851c`, G2.057). Unresolved: whether registered defence-in-depth branches count as OR46.a leftovers needs the owner.

### HR122 Test-side bookkeeping is bounded
- **Req**: A fake's or twin's own bookkeeping (call logs, recorders, `I2C.log`/`SPI.log`/WDT log/NeoPixel `writes`) is capped (keep-last-N) with a visible `dropped` count, or cleared by its owner (`UARTLink.wire_log`: each unit test, and the runner's clearer every 5 s), so harness growth never surfaces as a `MemoryError` in the code under test or reads as a product leak; recorders are muted while a test measures `src/`'s allocation, and a log-window assertion stays inside the bound.
- **Members**: G2.034, G7.042
- **Provenance**: A — G2.034: `8cf7b81` (2026-08-13) introduced `_LOG_MAXLEN`
- **Truth**: partly — G7.042: bounds present (`_LOG_MAXLEN`); `tests/test_digital_twin_bus_hazard_concurrency.py:364-370` asserts on a shared bus log during a ~75 s run and only assumes it never wraps; the 200-entry `I2C.log` is described as read by nothing. (others: G2.034 holds)
- **Fit / pillar**: refines OR38.a (1); refines OR38.a (1) (no leaks), OR20 (instrumentation distortion) · pillar P5 (all members)

### HR123 Soak trend retries once, noise-calibrated
- **Req**: The twin soak's memory-trend verdict derives its tolerance from each attempt's own observed noise and may retry once with a fully independent fresh boot, for the trend check only; HTTP, watchdog and shutdown failures are never retried, and the trend check's failure diagnostics are printed to the log permanently.
- **Members**: G7.036, G8.103
- **Provenance**: A — G7.036: `846c78b` (2026-09-14).
- **Truth**: holds — G7.036: E.9 text and `_run_11_soak()`. (others: G8.103 holds)
- **Fit / pillar**: refines OR37.a (2) ("a retry never counts as a race fix") — this retry is a measurement repeat, not a race …; tension OR37.a (2) · pillar P5 (all members)
- **Note**: Both members note tension with OR37.a (2) ('a retry never counts as a race fix'); resolved: this retry repeats a noisy measurement, it is not a race fix.

### HR124 Leak bounds are rates; soak time is liveness
- **Req**: A memory-leak assertion bounds retention per operation, a rate calibrated against a real and an injected leak, never an absolute heap delta. A soak's wall-clock budget is a liveness backstop set above the whole observed range, never a performance assertion and never bisected to a code change (the twin soak's runtime is GC-timing-driven); the suite counts operations instead of timing them.
- **Members**: G2.013, G7.039
- **Provenance**: A — G2.013: `fd333ce` (2026-09-12, fixing red CI)
- **Truth**: partly — G2.013: `test_uart_comm_hazard.py` uses per-transaction rates; `tests/test_asy_webserver_service.py:1833` still asserts an absolute 4096 B `mem_free()` drop (others: G7.039 holds)
- **Fit / pillar**: refines OR19.a (1) (tolerances); refines OR30.a (3) · pillar P5 (all members)

### HR125 Waits poll for the condition, deterministically
- **Req**: A test waits for readiness by polling for the exact expected state with a deadline instead of sleeping or racing on host speed (the bench Pi4 is about 4x slower than an x86 runner); a fixed sleep is used only where a probe would disturb the property under test (e.g. a probe occupying a `max_connections` slot), and then as a measured tunable with its margin; each fault environment is deterministic (e.g. NTP unreachability via RFC 5737 TEST-NET-1 `192.0.2.1`).
- **Members**: G2.047, G7.037
- **Provenance**: A — G2.047: JS rule `7ae2f27` (2026-08-26); fixed-sleep choice `a335923` (polling probes broke the max_connections exactness tests)
- **Truth**: partly — G2.047: JS tier polls; Python twin tests use 0.5-2.5 s fixed readiness sleeps sized from single ~400 ms measurements (item N104, N498, N505, N512) (others: G7.037 holds)
- **Fit / pillar**: refines OR30.a (1); refines OR37.a (3), OR38 · pillar P5 (all members)

### HR126 No test may hang; backstops stay
- **Req**: Every test is bounded: async test bodies run under `asyncio.wait_for` so a wedge is a fast FAIL, every MicroPython test file runs under a per-file timeout (default 240 s) with two retries and `stdbuf` line buffering, CI keeps its `needs:` sequencing edge, and the backgrounded pytest tier has one whole-suite timeout (default 1200 s) that is never retried. These backstops stay after any specific hang is fixed, and a retry or longer timeout never counts as the fix for a race.
- **Members**: G2.003, G8.078
- **Provenance**: O — G8.078: OR37.a (2) (owner, 2026-09-26): "the two settled mechanisms stay: `test.sh`'s per-file timeout-and-retry (hang backstop) and the three-attempt `uv sync` retry"
- **Truth**: drifted — G8.078: SPEC B.10.1 (HEAD :916) sizes CI's 45 min on "180 s x 3" while `test.sh:314` defaults to 240 s (SCR.N149); `scripts/test.sh:27` says "85 files" against 87 (SCR.N013); per-file override table is deliberately empty (`:315-318`) (others: G2.003 holds)
- **Fit / pillar**: restates OR37.a (2); restates OR37.a (2); feeds OR30 · pillar P5 (all members)

### HR127 One fixed MICROPYPATH layout per tier
- **Req**: `scripts/test.sh` runs every `tests/test_*.py` from the repo root under the pinned Unix port with `MICROPYPATH=build/generated_src:src:tests:frozen_modules:.frozen`, and the twin with `...:src:digital_twin:ext:frozen_modules:.frozen`: generated modules first, fakes ahead of real modules, `.frozen` explicit because `MICROPYPATH` replaces the default path. `ext/` and `digital_twin/` stay off the unit path and a file needing them inserts them into `sys.path` itself (twin files put `digital_twin/` ahead of `tests/`); `_`-prefixed helper modules are never collected; any tool that re-runs a file uses the same layout or states why not.
- **Members**: G2.001, G8.080
- **Provenance**: F — G8.080: `.frozen` is `MP_FROZEN_PATH_PREFIX` (SPEC E.3); order convention A (`35ba8ac`)
- **Truth**: partly — G8.080: `test.sh:369` holds; the unit path lacks `ext`, so one test hand-inserts it (SCR.N068); the twin path is duplicated in two scripts; SPEC E.3's one-file example omits `build/generated_src` (the paragraph after it explains the extra step) (others: G2.001 holds)
- **Fit / pillar**: extends P8 (one layout, mirrors pinned); extends OR20.a (fakes outside the product) · pillar P5 (all members)

### HR128 Coverage reports never gate; its test result does
- **Req**: No line-coverage threshold is enforced anywhere: Python and JS coverage numbers are advisory reports, while the instrumented run's test result gates like any other: `test.sh --coverage` exits 0 (pass), 1 (test failure, outranking a renderer failure) or 3 (tests passed, rendering failed); CI goes red on 1, tolerates 3, and runs report/upload steps `always()` as advisory; every document says it this way. The traced set covers `src/`, `digital_twin/` and the generated device modules; the report knows the tracer's false-negative classes (folded `_` constants, decorator lines, `while True:` headers, pass-through `finally`), and `--coverage` ignores `GC_THRESHOLD` and says so.
- **Members**: G2.058, G8.082, G9.037
- **Provenance**: O — G2.058: OR23.a (2) "report-only and never gating, like src/"; E.5.3 test-result gating "owner decision, 2026-09-22" (CLAUDE.md)
- **Truth**: drifted — G9.037: README.md:177 says "test result gating", :192 says "non-gating, never fails the build". (others: G2.058 partly, G8.082 partly)
- **Fit / pillar**: refines OR22.a (2); extends OR25.a (3) (coverage report-only); conflicts with web-coverage practice; refines OR16.a (3)/OR25.a (3) (coverage report-only) · pillar P5 (all members)

### HR129 A clean hardware verdict proves every test ran
- **Req**: A flash or bench run is reported clean only if nothing failed, at least one test passed and nothing skipped beyond named, documented permanent skips and the opt-in gates whose flag is absent; a gate whose flag was passed and still skipped fails, whitelist names are pinned to real tests and flags, a build lacking a wired module fails rather than skips, an unconditional permanent skip is re-justified at every audit, and the verdict is parsed from pytest's own output and names every test an opt-in gate deselected as not covered.
- **Members**: G1.041, G8.090
- **Provenance**: O — G8.090: CLAUDE.md wear rule (project owner, 2026-09-17); OR21.a (3) (owner, 2026-09-25) on reporting skipped/deselected counts
- **Truth**: partly — G1.041: verdict script holds; `test_spoofed_off_subnet_source_address_is_ignored` is an unconditional `@pytest.mark.skip` "pending" a mechanism yet whitelisted as permanent; a firmware missing UARTLINK or `asy_uart_comm` turns into skips (test_uart_link_under_api_load.py:39-57, … (others: G8.090 partly)
- **Fit / pillar**: restates OR16.a (2); restates OR21.a (3), refines OR15.a (2) · pillar P5 (all members)

### HR130 Test ports OS-chosen or one tier only
- **Req**: A test that picks its own port asks the OS for a free one (port 0); a fixed test port base lies below the ephemeral range (32768-60999), inside SPEC E.1's documented bands and disjoint from every other file's; product-fixed ports (DNS 53, NTP 123, the twin's 18080) are redirected in tests or used by one tier at a time, a taken port fails at once naming it, two suites that bind real ports never run concurrently, CI isolates the fixed port by one runner per PUT-matrix shard, and every twin run shuts its twin down even when the run crashes.
- **Members**: G2.017, G8.092
- **Provenance**: O — G2.017: OR38.a (3) "a test that chooses its own port asks the OS for a free one ... product-fixed ports ... used by one tier at a time under a lock"; E.1 band text A (`35ba8ac`)
- **Truth**: partly — G2.017: Linux default range confirmed (`/proc/sys/net/ipv4/ip_local_port_range` = 32768 60999); bands are review-only and E.1 says TCP bases sit in 17400-19999 while `_webserver_concurrency_scenarios.py:77` assigns 19700+200·i up to 20700; no lock exists for the concurrent-suites rule; `_free_port()` … (others: G8.092 partly)
- **Fit / pillar**: restates OR38.a (3) · pillar P5 (all members)

### HR131 Host tests write only the zz_test_ namespace
- **Req**: The host tier works in `tmp_path`; the only live-tree write allowed is a `devices/zz_test_*.toml` fixture in a reserved namespace no real device may use, removed in `finally`, reclaimed at pytest session start and swept by `test.sh` first, before it generates every device module and only then backgrounds the pytest tier; nothing in the foreground globs `devices/` after that, device discovery always filters the prefix, and no test deletes a repo-level state directory another concurrent test may use.
- **Members**: G2.016, G8.075
- **Provenance**: A — G2.016: `09c77e2` (2026-09-17, closing test.sh leak/orphan hazards)
- **Truth**: partly — G2.016: sweep order pinned by `tests_scripts/test_test_sh.py:512-524`; the reserved-prefix guard inspects only `test_build_website_sh.py` (item N583); `test_bench_harness_helpers.py:138-143` globs `devices/` without the filter; both JS live harnesses `rmSync` the shared `digital_twin/config` (item N597, … (others: G8.075 holds)
- **Fit / pillar**: refines OR38.a (1)(3); restates OR38.a (1)/(3) · pillar P5 (all members)

### HR132 Website build stages production files only
- **Req**: `scripts/build_website.sh` stages only production files: `js/mock-server.js` and every other prototype-only file are never staged, checked against the real `html/`/`js/` contents by a drift test rather than a hand list; the generated `definitions.json` is written to scratch and inlined, never staged, with every `<` escaped; the exact-string contracts with `html/index.html` (stylesheet `<link>`, `</head>`, `id="inlined-definitions"`, the literal `../js/app.js` import) fail the build loudly when they drift, and the buildgen fallback for devices without hand-written definitions has an error-path test.
- **Members**: G7.058, G8.101
- **Provenance**: A — G7.058: `15ed282`/`35ba8ac` (2026-08-26/09-22).
- **Truth**: partly — G7.058: build checks present (`build_website.sh:59-67`); the staging guard is a substring match of each file name anywhere in the script (a comment mention passes; `html/` subdirectories and non-`.js` files under `js/` unchecked, WEB.N029); the prototype-only negative list is four hand-named paths (N031); … (others: G8.101 holds)
- **Fit / pillar**: refines OR36 (nothing test-only in the image); extends OR16 · pillars differ: G7.058 P4, G8.101 P5

### HR133 Unit tests: Unix port, one process each
- **Req**: `src/` unit tests run under the real MicroPython Unix-port interpreter, never CPython/pytest, one process per `tests/test_*.py`; process-wide swaps (`asy_spi_driver._SPI`, `asyncio.sleep`, `AsyUDPSocket`, `_FALLBACK_DNS_SERVERS`) are allowed only because of that, and no runner batches several test files into one process. Host-only build tooling is tested under CPython pytest.
- **Members**: G2.002, G9.039
- **Provenance**: O-confirmed — G9.039: OR20.a ("the unit tier stays on the MicroPython Unix port").
- **Truth**: holds — G2.002: `scripts/test.sh:335-390` launches one process per file; SPEC E.2.1 derives the per-device split from it (others: G9.039 holds)
- **Fit / pillar**: new (makes a load-bearing runner property explicit); restates OR20.a · pillar P5 (all members)

### HR134 Settrace only in the coverage binary
- **Req**: The installer builds two Unix-port binaries: `build-standard`, without `MICROPY_PY_SYS_SETTRACE`, is the rig for every plain run, and `build-settrace` is used only by `--coverage`; the rp2 firmware never gets the flag, because it allocates a frame and code object per call and inflates allocation 4-5x non-uniformly. Memory and allocation figures are taken only on `build-standard`, and constants calibrated on one binary are re-derived on the other. Every runner that starts the interpreter (test.sh, both twin runners, the cross-browser smoke, the live JS commands, CI's build-if-missing steps) verifies variant and freshness by asking the binary itself (`hasattr(sys, "settrace")`), never by path or existence, and rebuilds or fails on a mismatch.
- **Members**: G2.008, G4.060, G8.052, G8.053, G9.038
- **Provenance**: O — G8.052: "owner decision, 2026-09-21" (SPEC:730, :3060; CLAUDE.md:566); 4-5x inflation is a single measurement (`1e2f5b2`)
- **Truth**: partly — G2.008: `scripts/test.sh:97` probes the variant; `tests_scripts/conftest.py:55-60` and `tests_js/_live_twin_command.js:12-13` take `build-standard` by path without probing (item N546, N588); `tests/test_asy_fram_allocation_budget.py:3-5` still says the test interpreter is a settrace build (drift) (others: G4.060 holds, G8.052 holds, G8.053 partly, G9.038 holds)
- **Fit / pillar**: extends OR39.a (3); refines OR39.a (2); extends P5/P6 (measurements not inflated); extends OR16 (tier liveness) · pillars differ: G2.008 P5, G4.060 P5, G8.052 P5, G8.053 P5, G9.038 P6

### HR135 Every build error names what, where, fix
- **Req**: Every error in the host build chain aborts with a nonzero exit and a message naming the broken rule, where (device, instance or bus, field, or file and line) and the fix; user errors print no traceback, only internal bugs do; this covers write errors (`OSError`) and raw `KeyError`/`ValueError`/`AttributeError` escapes as well as `BuildError`; and every abort path has its own test, driven by a deliberately malformed fixture definition, asserting exit code and message.
- **Members**: G2.067, G8.005
- **Provenance**: O — G2.067: OR23.a (3) "every error path has a test asserting the exit code and that the message carries what, where and the fix"
- **Truth**: partly — G2.067: malformed fixtures exist; the fixture writer cannot emit inline tables, so the dict-valued `led_target` case always skips (`test_buildgen_validate.py:1203-1208`) (others: G8.005 partly)
- **Fit / pillar**: restates OR23.a (3) · pillar P5 (all members)

### HR136 Port-53 capability granted narrowly per run
- **Req**: Every runner that starts the Unix-port interpreter on a privileged port (the port-53 DNS test) grants `cap_net_bind_service` to that binary by `setcap` on each invocation (via `sudo` when not root), because a cached toolchain archive does not carry xattrs; this needs `libcap2-bin` and `sudo`, and nothing grants it more broadly.
- **Members**: G5.092, G8.095
- **Provenance**: A — G5.092: script comments (agent)
- **Truth**: holds — G5.092: three identical grant sites (per harvest; not re-read line by line) (others: G8.095 holds)
- **Fit / pillar**: refines OR38.a (3) (fixed product ports); new · pillar P5 (all members)

### HR137 const() rules as the pinned compiler applies them
- **Req**: Every module-level constant whose value `const()` can fold (small int, str, bytes, float, `None`/`True`/`False`, and tuples of these) is `_`-prefixed and `const()`-wrapped, which inlines it at compile time and removes it as a module attribute (so it is never imported or read by `getattr`); a public `const()` exists only for names other modules import and stays an importable global; a `const()` referenced inside another `const()` tuple is itself `const()`; float constants freeze as single precision; harmonised under OR24 (about nine eligible plain constants remain).
- **Members**: G4.035, G10.014
- **Provenance**: F — G4.035: `py/parse.c:832-869` (underscore names become `pass`, others stored), `py/parse.c:369-392` (str/token/const-object/tuple accepted), `py/mpconfig.h:582-605` (`COMP_CONST_TUPLE/FLOAT` on); A (`6f430c7`, `e5f31f2`)
- **Truth**: wrong — G4.035: SPEC F.1 (:3521-3524) "a `const()`-wrapped value does not survive as an importable module attribute in a frozen build" holds only for `_`-prefixed names; `parse.c:864-869` keeps a non-underscore `const()` as a module global. Float `const()` precision at freeze time not checked (ALGO.T06) (others: G10.014 partly)
- **Fit / pillar**: new; refines OR24; P6 (no global dict entry, inlined) · pillar P6 (all members)
- **Note**: G4.035 records SPEC F.1's claim that any `const()` value is absent from a frozen build as wrong for non-underscore names (`py/parse.c:864-869`). The two members' type lists differ (bytes vs float); both are folded per `py/parse.c:369-392` (const_object), merged here.

### HR138 Transfer methods in pairs, one naming rule
- **Req**: Every transfer method comes as a pair (`write(data)`/`write_into(buf)`, `read()`/`read_into(buf)`), named `read_into`/`write_into` for project APIs or the platform's `readinto` where it mirrors a `machine`/stream API (stated as a rule), with synchronous variants carrying `_sync`; a failed buffer allocation degrades to a `None` buffer that every consumer checks first, and long-lived buffers are allocated once, not per operation.
- **Members**: G4.066, G10.046
- **Provenance**: A — G4.066: `6a2d43e` (2026-09-11)
- **Truth**: partly — G4.066: `AsyFramChunk` pairs hold; FRAM chunk buffers and each persisted log entry allocate a fresh `AsyFramChunkBuffer` (with an unused lock) per call (`asy_fram_manager.py:434-572`, `print_log.py:249`; CORE.S07) against the long-lived-buffer rule (others: G10.046 partly)
- **Fit / pillar**: refines OR46.b (one shape per job); refines OR24, Part G.2 · pillar P6 (all members)

### HR139 Numeric code is correct in float32
- **Req**: Every numeric threshold, constant and formula in firmware is valid in the rp2 port's single-precision float (24-bit mantissa, software float from the boot ROM, no FPU), not only the Unix port's double: comments and test expectations state which precision they assume, integer arithmetic is used where precision or speed matters, and float edge cases proven on the Unix port are re-proven on the target before they are relied on. A numeric config value above 2^24 is stored rounded without error, so no float field's bounds exceed 2^24 and a field needing exact large integers is an int type; a JSON integer is accepted and converted for a float field, and docs describe that acceptance correctly.
- **Members**: G1.037, G3.011, G4.036, G5.038
- **Provenance**: F — G1.037: MicroPython v1.29.0 ports/rp2/mpconfigport.h:128-129 (`MICROPY_FLOAT_IMPL_FLOAT`)
- **Truth**: drifted — G4.036: SPEC F.5.3 (:3792-3793) says `-fno-math-errno` makes `math.sqrt` "compile to the hardware instruction"; the Cortex-M0+ has no FPU or sqrt instruction (the flag is in `ports/rp2/CMakeLists.txt:547`, but the effect claimed is wrong) (others: G1.037 holds, G3.011 partly, G5.038 drifted)
- **Fit / pillar**: new (accepted boundary for OR43.a (1) ranges); new (gap: the unit and twin tiers cannot observe float32 effects) · OR17/OR29.a; refines OR29.a (2); new (a bound check in buildgen/tests closes the unpinned premise) · pillars differ: G1.037 P6, G3.011 P6, G4.036 P6, G5.038 P2

### HR140 Budgets start from the built image's GC heap
- **Req**: Design budgets assume the RP2040 on a Pico W: two Cortex-M0+ cores up to 133 MHz with MicroPython on one, 264 KB SRAM and 2 MB QSPI flash with the littlefs partition behind the firmware image; the heap the SRAM-resident interpreter and the CYW43 driver take is an accepted, unavoidable cost of the board, so budgets start from the measured GC heap of the built image, never from 264 KB.
- **Members**: G4.052, G4.083
- **Provenance**: F — G4.052: RP2040 datasheet p.9 ("Dual ARM Cortex-M0+ @ 133MHz", "264kB on-chip SRAM"); partition size depends on the build (not checked)
- **Truth**: partly — G4.083: "roughly half the 264KB SRAM" does not match the build's ~192 KB GC heap (SPEC B.14.2: 192,488 B); it matches the ~130 KB free after boot (F.5.3) (others: G4.052 holds)
- **Fit / pillar**: restates OR44 (low-end hardware) · pillar P6 (all members)

### HR141 FRAM capacity is a per-build mpremote check
- **Req**: Whether every FRAM chunk of the fully built system fits the part is decided once per build by a `None` chunk from `get_chunk()`, checked per generated device at the mock tier and on the board by an mpremote device script only; no runtime `/status` field reports it.
- **Members**: G1.028, G5.064
- **Provenance**: O — G1.028: README.md:1411 "mpremote-only by design (owner's own decision)"
- **Truth**: partly — G1.028: the script probes a hand-kept attribute list and silently skips a new FRAM-wired name (fram_capacity_after_full_system_build.py:11-17, G1.027) (others: G5.064 holds)
- **Fit / pillar**: refines OR47.a (2); refines OR16.a (1) · pillars differ: G1.028 P6, G5.064 P5

### HR142 Chip command waits follow datasheet maxima
- **Req**: Delays between a chip command and its result follow the datasheet's stated maxima with a stated margin and a correctly cited source, not legacy's empirical values: the SGP40 measurement wait covers the 30 ms maximum raw-measurement duration (self-test maximum 320 ms); SCD30 transfers use no repeated start and wait more than 3 ms (50 ms used) between write and read; each SCD30 read-task (re)start sends a soft reset and waits the full <2 s boot bound (2.5 s) before the next command, also on supervisor restarts, and sends no start-continuous command at boot (the sensor's NVM state is used).
- **Members**: G3.074, G3.080, G9.064, G9.066
- **Provenance**: F — G3.074: SCD30 Interface Description lines 52-54 ("does not support repeated start", "boot-up time is < 2 s"), line 570 ("delay of > 3ms")
- **Truth**: partly — G9.066: src waits 100 ms per SGP40 measurement (`asy_sgp40_driver.py:615`, 3x the datasheet max) and 500 ms for the self-test (:687, datasheet max 320 ms); margins are not stated. (others: G3.074 holds, G3.080 holds, G9.064 holds)
- **Fit / pillar**: extends OR30; OR30 tunable; refines OR48.a (adaptation grounded in datasheet); refines OR48.a (2) · pillars differ: G3.074 P6, G3.080 P6, G9.064 P3, G9.066 P6

### HR143 UART code never blocks the asyncio loop
- **Req**: `asy_uart_driver.py` and `asy_uart_comm.py` never hold the asyncio loop, not even in a wait state, because rp2 `UART.read()/readinto()` wait out `timeout_char` per missing byte inside `mp_event_handle_nowait()`, which never yields, while `POLLIN` fires on one byte: every counted read is clamped to `uart.any()`, `ready()` yields before returning True (the one place the invariant lives), delimited reads yield every 16 bytes and a zero-length round sleeps. A task waiting for traffic that may never come (the responder's idle listen) polls at a slower tuned `poll_idle_ms`, never at the transaction rate and never with a 0 default, kept well under the peer's reply timeout. UART fakes serve `min(nbytes, queued)`, never block, and count the real stall in `would_have_blocked_bytes` identically in both fakes; the invariant is proven by recorded request sizes at the mock tier and by timing only on the bench.
- **Members**: G2.022, G3.030, G4.019, G4.022, G6.024
- **Provenance**: O — G2.022: CLAUDE.md "may never block the asyncio loop ... (project owner, 2026-09-11)"; the counting stand-in is A (`fd333ce`/`2b9c997`)
- **Truth**: partly — G3.030: `ready()` yields at `asy_uart_driver.py:294`, `_read_delimited` at `:168-169`, `_buffered()` clamps counted reads; `readline()`/`readline_until_complete()` gate on one buffered byte, then call `uart.readline()` unclamped (`:395, :410`), holding for the buffered line plus one `timeout_char` (rp2 … (others: G2.022 holds, G4.019 holds, G4.022 partly, G6.024 holds)
- **Fit / pillar**: refines CLAUDE.md UART rule; restates CLAUDE.md; OR30 (`poll_idle_ms`, 16-byte yield are tunables); refines OR31.a (tasks never stall), P6; extends OR49.a (CPU time); refines F.3 / P6 · pillars differ: G2.022 P2, G3.030 P6, G4.019 P6, G4.022 P6, G6.024 P6
- **Note**: G4.022 extends the idle-rate rule beyond UART and records that `asy_udp_socket.ready()` polls every 20 ms forever for captive DNS; that extension is agent-level (A) over the owner's UART-specific rule.

### HR144 CRC keeps its per-byte yield
- **Req**: `crc_checks._crc()` keeps its `await asyncio.sleep(0)` after every byte, accepting the ~5.8x wall-clock cost so a large CRC never stalls other tasks; a table-driven CRC is not introduced, its RAM cost not being justified by the small buffers.
- **Members**: G3.016, G4.085
- **Provenance**: O — G3.016: SPEC I.2: "2026-09-18: \"pure wall clock time is not such an issue, don't touch\"" (commit `23e5443`, "Record the owner's three decisions"); the table decline is A (`b1059bd`), not restated in SPEC
- **Truth**: holds — G3.016: `crc_checks.py:49`; the silicon wall-time factor stays unmeasured (informational) (others: G4.085 holds)
- **Fit / pillar**: restates owner decision; relevant to OR39; restates owner decision · pillar P6 (all members)

### HR145 Growing GET bodies stream in bounded pieces
- **Req**: Every GET route whose response grows with device configuration streams its JSON through `_stream_dict_response()`/`_PieceWriter` in pieces of at most `chunk_bytes` (default 256, the same parameter that sizes static reads, clamped to at least 1) through a writer holding at most 16 pieces, with an exact `Content-Length` and output byte-identical to MicroPython's `json.dumps()`, never built as one string or dict; the largest allocation is the largest fragment, the one over-cap fragment (a 1,024-character `NTP_Host`) is bounded by the schema, and tests assert the bounded stream shape itself because a Unix-port heap cannot reproduce the contiguity failure.
- **Members**: G2.029, G4.067, G6.085
- **Provenance**: O-confirmed — G2.029: CLAUDE.md memory-safety bullet "the canonical example of this 'relieve the pressure' fix" under the owner-established discipline
- **Truth**: partly — G4.067: holds for every route; the `NTP_Host` piece is ~1,026 B (I.3 states it) (others: G2.029 holds, G6.085 partly)
- **Fit / pillar**: extends OR39/OR40 (design first); refines OR49.a (1) (heap); restates CLAUDE.md memory rule; refines OR40/P6 · pillar P6 (all members)

### HR146 Connection ceiling is one checked, derived number
- **Req**: Every shipped device TOML states `[device].max_connections` (6, the recommended setting); `backlog` defaults to `max_connections + 1` and buildgen refuses one outside `[max, max + 1]`; `toolchain/versions.toml`'s `[lwip]` table is one coherent ensemble sized for the admitted connections plus three spare TCP PCBs (`MEMP_NUM_TCP_PCB >= max_connections + 3`), at least 2,000 B `MEM_SIZE` per connection with `TCP_MSS` kept, no ignored settings, read back from the built image, and buildgen refuses any device the pools cannot serve, passing exactly the checked values to `WebserverService`. `Request.max_content_length` and `max_body_length` are both set from one parameter (2,048 B, process-global) so no oversized body is buffered and the simultaneous contiguous demand is `max_connections x max_content_length` (about 2,324 B GC heap per connection); a change to either value re-derives the heap and lwIP budget. A connection over the ceiling is accepted and closed with no response, a slot counts until its close completes and is released even if the close's warning raises `MemoryError`, no open connection is evicted and keep-alive is not implemented. Every host instrument sizes its load with `device_max_connections()`, never a literal; load tests treat only reset or EOF as a clean refusal, retry only a ceiling close, wait out the slot-release lag, assert per-answer correctness plus a floor on answered requests, assert a refusal only where the burst exceeds the ceiling by a full ceiling, and require `max_connections >= 4`; per-source-IP behaviour is out of scope, and only silicon confirms a raised PCB count.
- **Members**: G1.058, G2.063, G4.045, G4.068, G6.074, G6.075, G8.023, G8.024
- **Provenance**: O — G8.024: "The owner's decision (2026-09-22) is that the recommended setting ships on every device"; SPEC:4557 "(owner decision, evidence below)"
- **Truth**: partly — G2.063: any `OSError`, not only a reset, counts as a clean rejection (item N108); `:311-313` calls rejection timing-dependent while `:503-506` asserts it (others: G1.058 holds, G4.045 holds, G4.068 holds, G6.074 partly, G6.075 holds, G8.023 holds, G8.024 holds)
- **Fit / pillar**: refines OR43.a (derived, never hard-coded), OR49.a (1) (graceful degradation at the connection limit); refines OR49.a (1); refines OR49.a (1) (sockets/connections); refines OR52.a (3); refines OR49.a (graceful degradation under load); extends P6; new (per-device knob rule) · pillars differ: G1.058 P6/P8, G2.063 P5, G4.045 P6, G4.068 P6, G6.074 P6, G6.075 P6, G8.023 P6, G8.024 P6

### HR147 Memory pressure is fixed by design, never settings
- **Req**: A memory-pressure problem is fixed by a design-level technique that relieves the pressure (chunking, reusing preallocated buffers, streaming), never by a `gc.threshold()` value, an added `gc.collect()`, a larger heap or a ruled-out remedy. `gc.threshold(32768)` is defence in depth set once for the final build. The unit tier's `-X heapsize` (16M) is a Unix-port harness setting unrelated to the board's RAM, sized to the suite's measured floor and never raised to make a failing test pass; per-file heap pressure is relieved at the root (split heavy files per device, smaller object graphs), not by a per-file override or a `gc.collect()` prop.
- **Members**: G2.009, G4.074, G8.106
- **Provenance**: O — G4.074: OR40 ("the threshold is finally applied to move it even further into the stable region"); threshold choice per "explicit project owner direction" (`887da0e`)
- **Truth**: holds — G2.009: `scripts/test.sh:369` `-X heapsize=16M`; one real-time test is the reason for the floor (SPEC E.3.1, commit `5cd7e30`): the heap value is load-bearing for a timing budget, not only memory (others: G4.074 holds, G8.106 holds)
- **Fit / pillar**: refines OR39.a (2), OR30.a (1) (heapsize is a tunable); restates OR40; refines OR30.a (1) (tunable), OR39.a · pillar P6 (all members)

### HR148 Post-build heap bounds are fixed requirements
- **Req**: After a full `build_system()` on the board the largest free block is at least 32,768 B (twice the worst reachable allocation as derived), the built graph's survivors hold at most 100,000 B, and the boot places nothing in the top 16,384 B of the heap; these bounds are requirements, never raised or re-derived to fit a reading, and every threshold names the image and measurement it was fitted to. `WORST_CASE_ALLOCATION = 16,384` stays above the measured worst case as a regression tripwire, serving memory is proven as placeability of the ceiling's worst concurrent demand rather than an absolute free-byte floor, and no free-heap percentage target or REST-exposed `mem_free` exists.
- **Members**: G1.060, G4.075
- **Provenance**: O — G1.060: SPECIFICATION.md:3777 "the owner retired its 100,000 B free / 80,000 B contiguous floors" (2026-09-19, commit 3fe0fb2 "The owner's decision")
- **Truth**: partly — G1.060: the three checks and the tripwire hold (test_memory_stress.py:22-66); `_MAX_USED = 100_000` in heap_headroom_after_full_system_build.py:36-39 is fitted to readings of an unnamed image; `_MAX_ROUTE_NEED = 480` rests on one measurement set (others: G4.075 holds)
- **Fit / pillar**: refines OR49.a (1), OR30.a (3); refines OR49.a (1) · pillar P6 (all members)

### HR149 Nothing blocks the loop; no global long-block lock
- **Req**: No `src/` code blocks the event loop with blocking I/O, `time.sleep()` or an unbounded loop while timing-sensitive work (LED animation, UART, the watchdog feed) must run; the documented exceptions are sub-millisecond (the `sleep_us(2)` CS settle) or unavoidable C calls, and load models exclude artefacts such as a synchronous `I2C.scan()`. The legacy global `get_long_block_lock()` stays retired: long-blocking calls are isolated per F.3, a call that cannot be timeout-wrapped (`getaddrinfo`) is not wrapped in a lock, and a new genuinely long-blocking call gets a freshly designed coordination mechanism.
- **Members**: G4.084, G5.061, G9.081
- **Provenance**: O — G9.081: CLAUDE.md hard rule (F.3); BACKLOG item 4 ("Decided by the project owner").
- **Truth**: holds — G4.084: only `time.sleep_us(_CS_SETTLE_US)` found (`asy_spi_driver.py:141,150`); "noticeable" is undefined (no mechanical check) (others: G5.061 holds, G9.081 holds)
- **Fit / pillar**: refines OR31.a; restates CLAUDE.md "Long-blocking operations" rule; restates CLAUDE.md F.3 rule · pillar P6 (all members)

### HR150 UART frame path allocates nothing
- **Req**: After construction the UART protocol and its frame codec allocate nothing per frame or transaction: two long-lived frame buffers, a preallocated ACK, zero and command scratch per instance and codec scratch sized once from the frame bound are reused, drains use `readinto` into the RX scratch, there is one allocation per logical message, construction is refused unless every buffer allocated, and an allocation failure degrades to the failure sentinel plus resync. A responder whose `set_callback` answers 'don't care' lets the peer size one allocation (up to ~64 kB at `payload_size` 255), accepted because it is caught and degraded; new responders declare their size. Tests pin zero retained bytes per transaction and a bounded heap rate per failure.
- **Members**: G4.065, G6.019
- **Provenance**: O-confirmed — G6.019: requirements §3 item 8 (owner, 2026-09-11); N227 A ("deliberately left", audit pass 2026-09-11)
- **Truth**: holds — G4.065: `framing_codecs.allocations` counter asserted; `test_uart_comm_hazard.py` pins retention (others: G6.019 holds)
- **Fit / pillar**: refines OR44.a P1 (heap over months); refines OR26.a (MemoryError with a real alternative flow) · pillar P6 (all members)

### HR151 Boot latency is not a metric
- **Req**: Boot time is not optimised for its own sake: the one-time `setup()` batch is never trimmed or reordered for speed, and the only boot-time target is that no inter-feed stretch approaches the watchdog timeout. Cold-boot latency is measured and reported with a sanity ceiling, never asserted against a tight bound, and measured boot figures are evidence for the watchdog margin only.
- **Members**: G1.092, G4.086
- **Provenance**: O — G1.092: CLAUDE.md "(WP6, owner-established requirement)"
- **Truth**: holds — G1.092: 120 s ceiling, printed; the in-test comment calls the missing threshold a TODO ("no measured baseline exists yet"), which the rule makes unnecessary (others: G4.086 holds)
- **Fit / pillar**: restates CLAUDE.md boot-latency rule; refines OR31.a (2); restates OR31.a (2) · pillars differ: G1.092 P6, G4.086 P3

### HR152 TYPE_CHECKING blocks stripped from the staged image
- **Req**: Every `from typing import ...` in MicroPython-target code sits under a guarded `TYPE_CHECKING` import, and because `mpy-cross` does not dead-code-eliminate those blocks, the firmware build strips them and their import guard from the staged copy of each module, never from `src/` or `ext/`; the stripped output is compiled by `mpy-cross` and executed by at least one tier, and field tracebacks are mapped back knowing that stripping drops comments and shifts line numbers.
- **Members**: G4.054, G8.098
- **Provenance**: A — G4.054: Unix-port and mpy-cross facts (not re-checked here)
- **Truth**: partly — G8.098: staged-copy-only holds (`test_build_firmware.py:151-157`, config_manager only); compound tests and `if/else` forms are left while the guard is removed unconditionally (SCR.N085); validated by CPython `ast.parse` only (SCR.N087); output depends on host `ast.unparse` version (others: G4.054 holds)
- **Fit / pillar**: refines OR36 (lean image); extends OR36 (image purity), P6 · pillar P6 (all members)

### HR153 Frozen website: vendored freezefs, never compressed
- **Req**: `build_frozen_html.sh` runs the vendored, unmodified freezefs with an explicit `HTML_SRC_DIRS` (no default), writing to `frozen_modules/`, and never uses `--compress` (a compressed file opened in text mode, or with `--on-import=mount`, is buffered whole in RAM); a missing source dir fails the build and website paths stay under freezefs's 255-character limit.
- **Members**: G4.069, G7.078, G8.096
- **Provenance**: F — G4.069: vendored `ext/freezefs/ffsmount.py:93-102`; A for the rule
- **Truth**: partly — G8.096: `gzip -9` without `-n` embeds mtimes, so the image is not reproducible (`:25`); the `for src_dir in $src_dirs` loop is unquoted (`:22`); `build_frozen_html.sh:10-11` says freezefs dropped `-s` while the vendored CLI still has it (`ext/freezefs/archive.py:235-239`, drift) (others: G4.069 holds, G7.078 holds)
- **Fit / pillar**: refines OR36 (lean image); refines P6; extends P8 · pillars differ: G4.069 P6, G7.078 P6, G8.096 P4
- **Note**: Contradiction on reproducibility: G8.096 requires a byte-reproducible archive (and finds `gzip -9` without `-n` embeds mtimes); G7.078 accepts the embedded local build time. Both agent-level (A); unresolved, needs the owner. G8.096's 'freezefs 2.4' naming is itself drift (see singleton G9.099).

### HR154 Read and save FRAM evidence before clearing
- **Req**: `PUT /status {"ResetErrors": true}` resets every registered module and erases FRAM evidence, so before it, a reflash, a reboot or any other clearing the FRAM-persisted error logs (and, after an unexpected reset, `reset_cause()`) are read and saved verbatim; the harness does this automatically before its first clear in a session, a test clears only after capturing what it asserts on, and the same holds inside the twin, whose `_fram_chip.py` models the production layout and whose CI suite issues `ResetErrors` from one helper only. A FRAM log counts as evidence only after checking what has run against that board, because isolated-driver device scripts (deterministic allocator, production's first chunks) and bootloader entry can overwrite or tear production chunks; such a script clears its chunk at its start and leaves no seeded history on any path. History survives a reflash, and the sweep's time under load is fixed at the source, never by raising a client timeout.
- **Members**: G1.024, G1.025, G5.030, G6.087, G7.028, G8.104
- **Provenance**: O-confirmed — G5.030: `6cf82a1` records owner rulings incl. the FRAM-residue trap; OR28.a (1) and OR38.a (4) (owner, 2026-09-25/26) restate "read before clearing"
- **Truth**: partly — G1.024: `reset_all_error_logs()` clears with no snapshot (error_log_helpers.py:17-19) and nearly every network-fault test calls it at start and end (test_network_resilience.py:169-994); only test_memory_stress_bench.py:129-131 captures first; SPECIFICATION.md:1819-1822 says "clear it first" with no read … (others: G1.025 partly, G5.030 holds, G6.087 partly, G7.028 partly, G8.104 partly)
- **Fit / pillar**: restates CLAUDE.md FRAM rule; refines OR38.a (2), (4); refines OR38.a (4) and OR28.a (1); restates CLAUDE.md FRAM rule, OR38.a (4); refines CLAUDE.md FRAM rule; OR49.a; restates CLAUDE.md FRAM rule; refined by OR38.a (2); refines CLAUDE.md FRAM-evidence rule · pillars differ: G1.024 P7, G1.025 P7, G5.030 P7, P9, G6.087 P7, G7.028 P7, G8.104 P7

### HR155 One errno/wrnno catalog, checked by a test
- **Req**: Every `errno`/`wrnno` has one meaning project-wide, recorded once in SPECIFICATION.md C.7.1: 1-9 / 1-2 are the base-class meanings, reusable elsewhere only for the identical condition; common conditions share one number; module-specific codes sit in non-overlapping ranges; within a module each condition (read vs config vs calibration leg, each getter vs its setter, each registration rejection) has its own number, since `/status` and bench reads tell conditions apart only by number; a retired number is never reused; the numbers readers rely on for diagnosis are part of the contract. The catalog, every `err_s`/`wrn_s` call in `src/` and generated code, and the code-to-text mappings change together in one change, enforced by a test that checks every call site.
- **Members**: G3.067, G5.024, G6.064, G9.032
- **Provenance**: O — G5.024: OR28/OR28.a (owner, 2026-09-25: "This audit IS the next substantial change … yes to all"); the C.7.1 deferral "(owner decision, 2026-09-24)" is superseded
- **Truth**: drifted — G5.024: C.7.1 says "No clash is live, since none shares a logger with a `SensorReader`", but `AsyNtpClient`, `AsyConnTime` and `NotificationCoordinator` are `SensorReaderConfig`s and log `wrnno` 1-3/1-5 on the same logger that `base_classes.py` uses for `wrnno` 1/2 (`asy_ntp_client.py:95,157,217`, … (others: G3.067 holds, G6.064 drifted, G9.032 partly)
- **Fit / pillar**: restates OR28.a (2) (one meaning per number); restates OR28.a; restates OR28.a (3) · pillars differ: G3.067 P7, G5.024 P7, P8, G6.064 P7, G9.032 P7

### HR156 FRAM layout fixed within a build, not across
- **Req**: FRAM chunks are allocated synchronously at construction by a bump allocator, so the generated construction order is the on-chip layout: every chunk-owning object is constructed unconditionally at top level, exactly once per boot, never in a branch or loop a restart can re-enter; the number and order of notification signals (whose combined chunk `finalize()` builds, and whose order decides arbitration) and the SGP40's 32-field VOC state (field order, 256-byte size, explicit `"<"` packing, a pack/unpack failure returning False) are fixed within a build. The layout is deterministic and asserted per generated device, carries no fingerprint and need not survive a reflash or match legacy; after a reflash foreign bytes are handled as empty and re-initialised without a crash or error flood.
- **Members**: G3.014, G3.094, G5.062, G9.088
- **Provenance**: O — G5.062: OR47.a (2) (owner, 2026-09-26): "there is no requirement for the fram to stay consistent through firmware re-flashes. it only must be rock solid within one individual firmware build"; the determinism rule itself is A
- **Truth**: drifted — G5.062: SPECIFICATION.md:216-218, :379 and `tests/test_asy_fram_manager.py:88-90` still say the order "must stay identical across firmware versions"; A.7's hand-numbered chunk list is not machine-checked against the generator; per-device layout assertion not found; `devices/dev.toml:97` names an undefined … (others: G3.014 partly, G3.094 holds, G9.088 unverifiable)
- **Fit / pillar**: refines OR47.a (2) (fixed within one build, no fingerprint); restates OR47.a (2) (fixed within one build); restates OR47.a (2) · pillars differ: G3.014 P7, G3.094 P7, G5.062 P8, P2, G9.088 P1

### HR157 Construction and setup order generated and fixed
- **Req**: Construction order is a deterministic topological sort: mandatory infrastructure first (with `fram` ahead of `conn`/`ntp`/`sysfunct` when `fram_target` is set), then TOML declaration order, the webserver last; FRAM chunk allocation follows it. The boot `setup()` batch runs in a generated, fixed order in which FRAM precedes `sysfunct` (its `cfgmgr` logger needs FRAM) and `notification.setup()` follows `finalize()`; each ordering constraint is stated where the generator emits it, and both orders are asserted per generated device.
- **Members**: G5.059, G8.022
- **Provenance**: O — G8.022: OR47.a (2) (owner, 2026-09-26: "fixed and deterministic" within one build); tie-break text A `4dbd4bb`
- **Truth**: holds — G5.059: `setup_order` puts `fram` first, then `sysfunct`, `conn`, `ntp` (`codegen.py:444-452`); per-device assertion of the order not found beyond the feed test (others: G8.022 holds)
- **Fit / pillar**: restates OR47.a (1); restates OR47.a (1)-(2) · pillars differ: G5.059 P2, G8.022 P7

### HR158 The FRAM-backed logger set is derived
- **Req**: Every module except the FRAM module itself gets FRAM-backed logging when its instance is wired to FRAM, stated once as a rule; the set of FRAM-backed loggers (`fram_target` wiring, the implicit service wiring and every `CFGMGR_<name>`) is one fact derived from the device TOML, and every list of it (CLAUDE.md's FRAM rule, SPEC A.4/A.7, hardware tests) is derived from there or complete, never a stale hand list.
- **Members**: G1.027, G9.030
- **Provenance**: O — G9.030: CLAUDE.md's FRAM rule (hard rule; its evidence-first half is the owner's); "implicit-FRAM-wiring rule" is A (WP1).
- **Truth**: drifted — G1.027: `_FRAM_BACKED_MODULES = (SYSTEM, SGP40, BMP3XX, SCD30, ISL29125, NEOPIXEL, NOTIFY)` (test_memory_stress_bench.py:22) omits WIFI, NTP, WEBSERVER, DNSSRV, every CFGMGR_* and UART_*, which CLAUDE.md lists as FRAM-backed and devices/dev.toml:19, 150-172 wires; test_network_resilience.py:929-930 calls … (others: G9.030 drifted)
- **Fit / pillar**: refines OR43.a (derive); refines CLAUDE.md FRAM rule · pillars differ: G1.027 P7/P8, G9.030 P7

### HR159 Heap-map tooling derived and bound to gc.c
- **Req**: Heap tooling derives the GC block size from the binary it measures (16 B on the RP2040 and the 32-bit twin, 32 B on the 64-bit Unix port) and parses `micropython.mem_info(1)`/`gc_dump_alloc_table()` output host-side (on the board it goes to the platform print, not `sys.stdout`): 64 blocks per line, runs of free lines abbreviated, one heap area on rp2. The parser pins the upstream text format, fails closed on a truncated or foreign capture, treats `HeapDelta` as a lower bound, and is re-checked against `py/gc.c` at every pin move.
- **Members**: G1.038, G4.061
- **Provenance**: F — G1.038: MicroPython v1.29.0 py/gc.c:1323-1342 (`DUMP_BYTES_PER_LINE = 64`, "(%u lines all free)"), py/gc.c:1317 ("No. of 1-blocks ... max free sz"), py/modmicropython.c:84-87 (`mp_plat_print`)
- **Truth**: holds — G1.038: format anchors match v1.29.0; fail-closed pinned by test_heap_map_parser.py; the probe's pinning artefact is handled by re-reads with a ±2-block tolerance (test_memory_stress.py:49-57); CLAUDE.md's version-bump re-check list does not name heap_map.py (others: G4.061 holds)
- **Fit / pillar**: extends CLAUDE.md version-bump re-check practice; refines OR29.a (2); refines OR39.a (2) · pillar P7 (all members)

### HR160 Website policy mirrors src/ exactly
- **Req**: Any policy the website encodes on behalf of the device (validation, coercion, bounds, result words, dispatch semantics, masking, envelopes) is identical to `src/`'s and changes in the same change on both sides, with no backend-only or frontend-only policy. The client's hard-coded wire knowledge matches the server and moves with it (the generated `_gmtimestruct_to_dict()` keys; errcount history shape `num`/`type` with no timestamp; shaped-error `descr` for 400/404/405/413/500; `/sensors` PUT nesting; envelope failure detection; `/status` PUT without per-field result; `PauseTime` read from `GET /status`; `${sensor}_${field}` flattening; `SystemCmd` never returned by GET; `mempause`'s fixed 300 s). A JS constant mirroring a `src/` value is named like the Python constant without the leading underscore and cites the live `src/` file and constant.
- **Members**: G7.049, G7.051, G10.049
- **Provenance**: A — G7.049: `0e94354` (2026-08-25, "Add SPECIFICATION.md Part G").
- **Truth**: drifted — G10.049: `SYSTEM_CMDS`/`PAUSE_TIME_MAX` (`js/mock-server.js:16-17`) follow; `LIGHT_CMD_LED_*` (`:178-184`) cite `src/sensortask_wozi.py`'s `_notification_led_callback()`, a file that is now generated and never committed (5 references to it across `js/`, `html/`, `tests_js/`) (others: G7.049 partly, G7.051 partly)
- **Fit / pillar**: refines OR24.a (2) (public interfaces change with every consumer); refines OR24.a (2), OR43.a (1) ("GET returns exactly what PUT accepts"); restates G.2; P8 · pillar P8 (all members)

### HR161 Mock backend and fixtures match the real API
- **Req**: `js/mock-server.js` answers exactly as the real server does, bound for bound and quirk for quirk, with every mirrored value read from its source or pinned by a test (route set, `SYSTEM_CMDS`, `PAUSE_TIME_MAX`, `PauseTime` dispatch, `lightCmdLED` bounds and Invalid/Failed split, numeric/string/enum strictness, special-value bypass, malformed body 200 `res:"ERR"`, 405 code 4, envelope, settings GET shape, `ResetErrors` refill, `PW`/`HotspotPW` masking, `ForceCalRef` 400 and omitted command-only fields, `/status` PUT shape, unknown-field handling); each `mockdata/<device>.json` carries exactly the measurements, settings and errcount keys the real device publishes, checked for every field kind by a test.
- **Members**: G7.050, G7.057
- **Provenance**: O — G7.057: OR43.a (2) "the mock server and mock data match the real API field for field"; supersedes the owner's 2026-09-12 q5 "leave mockdata's SHTC3/MPRLS placeholders alone" (`12a616a`).
- **Truth**: wrong — G7.057: `mockdata/dev.json:5-6, :13-14, :65-75` carry SHTC3/MPRLS that `devices/dev.toml` does not wire; no BMP3XX `sensorsConfig` nor `BMP3XX`/`CFGMGR_BMP3XX`/`UART_init`/`UART_resp` errcount rows though dev wires them; the coverage test checks readonly fields only; `mock-server-put-matrix.test.js:18-21` … (others: G7.050 partly)
- **Fit / pillar**: restates G.2; refines OR43.a (2) ("the mock server and mock data match the real API field for field"); restates OR43.a (2); conflicts owner q5 (2026-09-12) — later row wins · pillar P8 (all members)
- **Note**: G7.057 notes it supersedes the owner's 2026-09-12 q5 ('leave mockdata's SHTC3/MPRLS placeholders') by OR43.a (2) (owner, later row).

### HR162 One role per document; one home per rule
- **Req**: CLAUDE.md holds session rules and working agreements with one short reason each (it loads into every session), SPECIFICATION.md facts and specifications, BACKLOG.md only open items (at the audit's end: owed real-hardware work, C-port items and owner-deferred goals with their reason), `DEVICE_REFERENCE.md` user-facing operating notes, `HEAP_FRAGMENTATION_MEASUREMENTS.md` measuring method only. A fact or standing rule is written in exactly one document whose role fits it and referenced from the others, never stated twice; incident accounts, measurements and long recipes (the chroot recipe) live in SPECIFICATION.md or a README; a resolved BACKLOG item leaves and its permanent content migrates (facts to SPECIFICATION.md, rules to CLAUDE.md), as BACKLOG's header says.
- **Members**: G9.006, G9.008, G9.009, G9.014
- **Provenance**: O — G9.008: OR51 ("single point of truth, no duplicates").
- **Truth**: drifted — G9.008: the check-current-docs and re-check-on-version-bump practice is stated in full in both places. (others: G9.006 partly, G9.009 drifted, G9.014 drifted)
- **Fit / pillar**: restates OR51.a (4); restates OR51; restates PQ6 answer / OR27.a; restates harmonization 3 · pillars differ: G9.006 P8, G9.008 P8, G9.009 P4, G9.014 P8

### HR163 Bench facts live in living docs and dev.toml
- **Req**: Current bench facts (wiring, chip identities, bench state, the manual `br0` recipe) live in `tests_hardware/README.md` and the documents owning each fact; device scripts and manual instructions take bus pins, bus parameters, UART pairs and peripheral GPIOs from `devices/dev.toml` or are pinned to it by a host test; `dev_legacy/README.md` describes only the legacy snapshot and is not a source for the bench.
- **Members**: G1.071, G9.049
- **Provenance**: O-confirmed — G9.049: OR32.a (3).
- **Truth**: drifted — G9.049: `dev_legacy/README.md:5` still calls itself "the current, maintained single source of truth" for the bench unit. (others: G1.071 partly)
- **Fit / pillar**: refines OR43.a (derive) and OR32.a (3); restates OR32.a (3) · pillar P8 (all members)

### HR164 Third-party attribution agrees everywhere
- **Req**: Every file derived from third-party code opens with `# SPDX-FileCopyrightText:`, `# SPDX-License-Identifier:` and one line pointing to THIRD_PARTY_LICENSES.md, in that order, before the module docstring; THIRD_PARTY_LICENSES.md has exactly one accurate entry per file, and header, entry and any sibling licence file state the same holder, year, scope and changes. The Apache-2.0 portion of `src/captive_dns.py` (p-doyle's `DNSQuery`) is scoped identically in its SPDX header, `src/LICENSE-captive_dns` and THIRD_PARTY_LICENSES.md with the §4(b) change notice kept; the licence-less karfas `AsyUDPClient` reuse rests on the author's public forum offer, and both derived files carry the attribution, discussion link and change list.
- **Members**: G9.094, G9.096, G9.097, G10.030
- **Provenance**: O-confirmed — G9.097: "the project owner located and provided the actual context" (`micropython/discussions#12967`), commit `383d17b`.
- **Truth**: drifted — G9.094: `src/asy_isl29125_driver.py` has two entries (:32-36 and :44-53); ":28-29 the one non-Adafruit file" while three are listed; :52-53 says "FRAM-persisted gain-ratio self-calibration" while the driver only reads `GainRatio` from its config store and its FRAM wiring is for logging … (others: G9.096 drifted, G9.097 drifted, G10.030 partly)
- **Fit / pillar**: refines OR52.a (7); refines OR52.a (7) (public redistribution); extends LIC (OR52.a (7)) · pillars differ: G9.094 P8, G9.096 P8, G9.097 P8, G10.030 P4

### HR165 VOC algorithm stays a literal, traceable port
- **Req**: `src/voc_algorithm.py` stays a literal port, diffable against its reference, of DFRobot's MIT Python translation of Sensirion's archived C Gas Index Algorithm: constants, field names, operation order and casing traced 1:1, no stylistic rewrite, unused reference API (tuning setters) kept; THIRD_PARTY_LICENSES.md records the full chain to Sensirion's BSD-3-Clause C reference.
- **Members**: G3.012, G9.098
- **Provenance**: A — G3.012: SPEC F.4 text, no owner attribution found
- **Truth**: partly — G3.012: constants checked against `gia` fixpoint `sensirion_gas_index_algorithm.c`/`.h` (INITIAL_BLACKOUT 45 `.h:73`, SAMPLING_INTERVAL 1 `.h:72`, guards 10.3972/−11.7835 `.c:259-261`, FIX16_MINIMUM/OVERFLOW 0x80000000 `.c:37,40`) and match; the docstring names the archived `embedded-sgp` via DFRobot, … (others: G9.098 holds)
- **Fit / pillar**: restates OR4.a (source now reachable); refines OR52.a (7) · pillars differ: G3.012 P4, G9.098 P8
- **Note**: Apparent contradiction: G3.012 says it traces Sensirion's reference, G9.098 DFRobot's translation. The file header (`src/voc_algorithm.py:3-5`) says it is ported from DFRobot's translation of Sensirion's C and verified constant-for-constant against the C; both hold, merged.

### HR166 ISL29125 INT is open-drain; dev pulls externally
- **Req**: The ISL29125 INT line is open-drain and needs a pull-up, internal via `irq_pull_up = true` or external; on the dev board GPIO6 has its own external pull-up, so `devices/dev.toml` sets `irq_pull_up = false`. SYNC and CONVEN stay 0 and RGBCF/CONVENF stay unused.
- **Members**: G1.097, G3.103
- **Provenance**: O — G1.097: dev_legacy/README.md:49 "confirmed by the project owner directly"
- **Truth**: holds — G1.097: dev.toml:107 (others: G3.103 holds)
- **Fit / pillar**: restates a rig fact; extends OR53 (pin configuration follows the chip) · pillars differ: G1.097 P8, G3.103 P4

### HR167 Generated device modules are never committed
- **Req**: Each device's `sensortask_<device>.py` and boot entry are generated by buildgen at build time only, live under the gitignored `build/`, and are never committed to `src/`; code, tests and docs refer to the generator or the generated module, never to a hand-written one.
- **Members**: G8.018, G9.029
- **Provenance**: A — G8.018: build-chain plan `3847c71`, folded `901e15d`
- **Truth**: partly — G9.029: no hand-written module exists; 9 comments still name `sensortask_wozi.py`/`sensortask-wozi.py` or retired runners (drift-only group G). (others: G8.018 holds)
- **Fit / pillar**: restates P8; extends P8 · pillar P8 (all members)

### HR168 PUT enveloped via make_response; GET bare
- **Req**: Every PUT and every shaped error answers with the `api_response.make_response()` envelope and every GET with the bare data dict (streamed where it scales); no route, in `src/` or in `js/mock-server.js`, builds a `{res, code, descr, result}` dict by hand.
- **Members**: G6.083, G10.077
- **Provenance**: A — G6.083: Part G catalog
- **Truth**: holds — G6.083: the only literal `"res":` in `src/` is inside `make_response()` (`api_response.py:56`); `js/` and generated code not checked (others: G10.077 holds)
- **Fit / pillar**: restates OR24; restates G.2 · pillars differ: G6.083 P4, G10.077 P8

### HR169 @web tags are the only website definitions source
- **Req**: Every device's `definitions.json` is generated at build time by `generate_definitions()` from the `@web`/`@web-group` tags, which are the only source: the hand-written `html/definitions/wozi.json`/`dev.json` are retired, `tests_js/` loads generated definitions, and adding a driver field needs only its tag.
- **Members**: G7.055, G8.045, G9.026
- **Provenance**: O — G7.055: OR43.a (3) "the hand-written `html/definitions/wozi.json`/`dev.json` are retired, the `@web` tags become the only source, and `tests_js/` loads generated definitions".
- **Truth**: drifted — G7.055: the two files still exist and are shipped for wozi/dev; their provenance is stated three ways: "hand-written" (`build_website.sh:26`, H.5), "never hand-maintained" (K.4:5804), "generated *and committed*" (BACKLOG.md:507); C.11 item 9 and `digital_twin/README.md:838-842` still instruct a hand … (others: G8.045 partly, G9.026 drifted)
- **Fit / pillar**: restates OR43.a (3) · pillar P8 (all members)

### HR170 Every REST value reachable in the GUI
- **Req**: Every value a REST endpoint returns or accepts is reachable in the ordinary GUI on its right page (no API-browser page), with the six sections mirroring the six endpoints; a value a route exposes but no page shows is placed per OR43.a's placement rule or listed as a deliberate exception with its reason in Part H.
- **Members**: G7.076, G9.028
- **Provenance**: O — G7.076: `WEBSITE_PLAN.md` §1 "goals, unchanged from the project owner's brief": "Every REST endpoint's functionality must be reachable somewhere in the GUI — not necessarily as a dedicated API-browser page".
- **Truth**: drifted — G9.028: GET `/system` returns a `build` entry (`asy_webserver_service.py:490-491`) that L.7 says is never rendered. (others: G7.076 partly)
- **Fit / pillar**: restates OR43.a (2); conflicts L.7 vs H.1/OR43.a (2) (listed under Conflicts) · pillars differ: G7.076 P2, G9.028 P8

### HR171 Test copies of product values derived or pinned
- **Req**: A test, harness, device script, twin table or build check that needs a product value (caps, timeouts, schema bounds and defaults, driver option tables, log strings, errnos and logger names, epoch deltas, the GC threshold, timing windows, fixed addresses, reserved address ranges, calibration datasets, special-field lists, UI strings, binary paths, `@limits` and `_VAL_*` mirrors, DEVICE_REFERENCE bounds and colours, a literal `submitGroup`) reads or derives it from its source (`src/` by AST or import, `devices/*.toml`, buildgen, the driver's schema) or takes it from one shared helper; where a copy is unavoidable (a `const()` compiled away, MicroPython-side code that cannot import host code, the on-target `KNOWN_ADDRESSES` table) the copy cites its source and a source-reading test fails on drift. A `_`-prefixed `const()` stays compiled away even when a test must restate it; a test of production wiring drives the real generated wiring; every bus-attached driver kind is covered by the per-driver tables, and a missing driver fails a test instead of dropping out. Plausibility bounds come from one place per quantity with their source (datasheet range, or an owner decision such as the 200 ppm CO2 floor), and a torn-read oracle states it only catches out-of-range values.
- **Members**: G1.069, G1.070, G1.072, G2.039, G2.040, G3.086, G6.081, G7.032, G8.012
- **Provenance**: O — G2.040: OR43.a (3) "one source", P8 (OR10.a, OR51.a (4) single source of truth)
- **Truth**: drifted — G1.070: test_rest_endpoints_over_sta.py:18 uses 400 ppm while scd30_plausibility_read.py:12 and test_bus_concurrency_under_api_load.py:19 use 200; bounds copied across three files (others: G1.069 partly, G1.072 partly, G2.039 partly, G2.040 partly, G3.086 partly, G6.081 partly, G7.032 partly, G8.012 partly)
- **Fit / pillar**: extends OR43.a (derive, never hard-code) to L3/L4; refines OR43.a (1) (ranges against datasheets); refines OR43.a (derive), OR44.a checklist; extends OR36.a (1), P8; restates P8; refines OR30.a (2)/OR43.a (3) (one source); extends OR16/OR22.a (silently broken chains), P8; refines P8 (generated not copied), OR28.a (3) (errno … · pillars differ: G1.069 P8, G1.070 P8, G1.072 P8/P10, G2.039 P5, G2.040 P8, G3.086 P8, G6.081 P8, G7.032 P8, G8.012 P5

### HR172 Twin wiring comes from buildgen's plan
- **Req**: The twin's bus, address and IRQ-pin layout is read from buildgen's per-device wiring plan (`compute_twin_wiring()`), never hand-typed; a caller that constructs a bus without configuring wiring fails loudly rather than silently getting wozi's layout; chip-intrinsic facts (fixed I2C addresses, FRAM RDID per size) live in one table each; and the wiring-plan JSON (`configure_wiring()`, `uart` and `instances` keys, generated variable names, `main()` signature) has one producer and one stated shape, tied to its consumers by a test.
- **Members**: G7.018, G8.039
- **Provenance**: A — G7.018: `fcc5339` (2026-09-11, "generalize wiring past the wozi/dev 2-profile enum").
- **Truth**: drifted — G7.018: L.4:6305 "No hand-typed wiring literal exists anywhere" vs `launch.py:369-375` (`I2C(0, scl=Pin(13), ...)`, `WDT(timeout=8000)`, addresses — they match `devices/wozi.toml` today, unchecked), `buildgen/twin_wiring.py:12` `FIXED_ADDRESSES`, `machine.py:323` RDID by size with silent MB85RS64V … (others: G8.039 partly)
- **Fit / pillar**: refines OR43.a (device set derived), P8; extends P8 · pillar P8 (all members)

### HR173 Python/website duplicates derived or pinned both ways
- **Req**: Every value or rule duplicated between buildgen/Python and the website (the six-endpoint section skeleton and `pollIntervalMs`, dispatch-group bounds and `SystemCmd` options, `SUPPORTED_SCHEMA_MAJOR` vs `SCHEMA_VERSION`, the `decimals` 0-100 bound, flat writable paths and `path` only on readonly fields as enforced by `buildgen/web_tag.py` and `js/definitions.js`, the definitions shape check, the TOML `max_connections` reader, errcount keys vs live `/status`, `websiteVersion` vs `WEBSITE_VERSION`) is derived from one source or pinned by a test that fails on drift in either direction.
- **Members**: G7.052, G8.042
- **Provenance**: A — G7.052: buildgen website commits.
- **Truth**: partly — G7.052: enforced: errcount keys at twin boot, TOML ceiling reader, `path` rule on both sides, decimals bound (`buildgen/web_tag.py:33` and `definitions.test.js`); not enforced: `_shape_problems` vs `validateDefinitions()` (no Node round trip), `SUPPORTED_SCHEMA_MAJOR = 1` vs `SCHEMA_VERSION = "1.0.0"` (no … (others: G8.042 partly)
- **Fit / pillar**: refines P8, OR43.a (3); extends Part G mirror obligation, OR43.a · pillar P8 (all members)

### HR174 buildgen copies of src facts tied to source
- **Req**: A module's TOML driver key, `_NAME`, logger/errcount key and config-store label derive from one source; every value buildgen restates from `src/` (hostname and WPA2 bounds, the NTP check tick, UART role literals and defaults, poll-floor formulas, FieldSchema tuple width) is read by AST or pinned equal by a test; and every hand-kept generator catalog that feeds the website (`_SENSOR_DRIVERS`, `_WARN_SIGNAL_WEB_CATALOG`, `_ERRCOUNT_CATALOG`/`_ERRCOUNT_NAME`/`_CFGMGR_LABEL`/`_NAME_EXT_LABEL`) covers every driver and logger and agrees with its code-side twin (`codegen._KNOWN_SIGNALS`, the 300 s mempause text), a missing row failing a test rather than silently dropping a driver from the website.
- **Members**: G8.010, G8.011, G10.068
- **Provenance**: C — G8.010: 9 mirror sites carry "mirrors"/"kept in step" comments; `_check_uart_link_buses()` reads `asy_uart_comm.py` thresholds by AST (1 site derived)
- **Truth**: partly — G8.010: no `tests_scripts/` test names `_HOSTNAME_MAX_LEN`, `_NTP_CHECK_TICK_S` or `_WPA2_*` (grep); `validate.py:246-247` "mirrored here rather than read" (others: G8.011 partly, G10.068 partly)
- **Fit / pillar**: extends P8 (one source, generated not copied); extends OR43.a (1)-(3), OR16; refines P8 (OR30/OR43.a one source), OR24 · pillar P8 (all members)
- **Note**: Tension with singleton G8.009 (owner, 2026-09-18/24: `buildspec.py` and `definitions.py`'s `status`/`errcount` catalog stay hand-maintained); compatible if the hand tables are pinned by tests rather than generated.

### HR175 Generator-only facts are one-line comment tags
- **Req**: Every driver-declared fact the running firmware never reads (cross-instance wiring, per-value wiring, field limits, bus requirements, website hints) is a machine-read `# @web`, `@web-group`, `@wiring`, `@value-wiring`, `@limits` or `@requires` comment, one line per field at module level next to the schema it describes, never a Python value frozen into the image, and is the only source buildgen reads for it; the one exception is a `_Default<Field>` class, live code the generated module constructs.
- **Members**: G8.001, G10.069
- **Provenance**: O — G8.001: "Project owner's ruling" quoted in `415438e` (2026-09-10); SPEC:6366 "(project owner's ruling, 2026-09-10)"
- **Truth**: holds — G8.001: no `_WIRING`/`_LIMITS`/`_VALUE_WIRING`/`_REQUIRES` assignment left in `src/`; 12 `src/` files carry tags; the only `_Default*` classes are `asy_sgp40_driver.py:102,118`, `asy_notification_service.py:58`. The 3,576 B saving is one measurement (`415438e`) (others: G10.069 holds)
- **Fit / pillar**: extends P6 (frozen size) and P4; restates L.6.4; P8 · pillars differ: G8.001 P6, G10.069 P8

### HR176 Node comes from .nvmrc only, verified
- **Req**: The Node major comes only from `.nvmrc`: a matching-major Node already on `PATH` is used as is and never overridden; otherwise the installer downloads it from nodejs.org verified against the release SHASUMS, never from apt (trixie ships Node 20); npm install is skipped only when there is neither `.nvmrc` nor npm.
- **Members**: G8.068, G9.045
- **Provenance**: A — G8.068: `setup_toolchain.py:929-931` "so there is exactly one pin rather than a second one living here"
- **Truth**: partly — G8.068: the patch version floats (`latest-v22.x`); the checksum comes from the same origin with no signature, and `next(...)` without a default raises a raw `StopIteration` (`:996-1003`); `@types/node ^26` disagrees with `.nvmrc` 22; `package.json` has no `engines` (others: G9.045 holds)
- **Fit / pillar**: extends P8 (one pin); extends OR15.a · pillars differ: G8.068 P8, G9.045 process

### HR177 Tests restore the board and rig state
- **Req**: A test, device script or manual step that changes persisted board state (flash config values, SCD30 NVM settings, FRAM write-protect bits, DebugLevel, the SSID, a notification threshold) states the write it spends, restores the prior value on every path with the restore in `finally`, verifies the restore's result word, and starts by detecting and repairing a leftover from an aborted earlier run rather than refusing to run; tests that depend on SCD30 NVM settings (interval 2 s, ambient pressure, temperature offset) assert them as a precondition and leave the SCD30 at the board's configured values. A device script sets and parks any shared rig state it depends on (NeoPixel light, a latched LED) on every exit path, and a bench test that runs a device script returns the board to serving through `restore_board_to_serving()` in a `finally` or fixture teardown, kept true by a host guard.
- **Members**: G1.014, G1.015, G1.016, G1.078, G1.096
- **Provenance**: O-confirmed — G1.014: OR38.a (1) "Each test cleans up after itself on every path, failure and cancellation included"
- **Truth**: partly — G1.014: `WarnCO2=1700` never restored (test_hotspot_role_reversal.py:274-281); garbage-SSID PUT plus two asserts before any `try` (test_network_resilience.py:520-533); restore checks only HTTP 200 (test_end_to_end_timing.py:181-205); sensor-push test refuses on a leftover instead of repairing (:41-45); … (others: G1.015 partly, G1.016 partly, G1.078 holds, G1.096 partly)
- **Fit / pillar**: refines OR38.a (1), (4); refines OR38.a (1), OR42.a (1); refines OR38.a (1) · pillars differ: G1.014 P9, G1.015 P9, G1.016 P9, G1.078 P5, G1.096 P5

### HR178 Persistent stores compare before write
- **Req**: A setter that writes persistent memory (config file, SCD30 NVM) goes through the shared compare-before-write primitive against a fresh snapshot at the store's resolution and writes only what differs, answering `"Unchanged"` otherwise: SCD30's TempOffs, MeasInt, Altitude and SelfCal are written only if different at chip resolution, `AmbPres` is always sent (it resumes measurement; 0 = compensation off), `ForceCalRef` is always carried out and `ContMeas` is a command, in the fixed legacy order TempOffs, MeasInt, AmbPres, Altitude, ForceCalRef, SelfCal, ContMeas; no periodic caller ever writes NVM.
- **Members**: G3.070, G9.062
- **Provenance**: O — G3.070: OR42.b/OR42.c; AmbPres static value and readback "confirmed intentional by the project owner" (SPEC A.4)
- **Truth**: drifted — G3.070: code writes every validated field unconditionally in client order (`asy_scd30_driver.py:257-297`); SPEC:237-240 describes a `force=True` the code no longer has; ContMeas has no schema by design; ForceCalRef recalibration stays manual (no automation) (others: G9.062 partly)
- **Fit / pillar**: restates OR42.c; restates OR42.c; corrects OR42.a/OR42.c's factual premise (Conflicts) · pillar P9 (all members)

### HR179 Bench bridge always presents eth0's real MAC
- **Req**: Every creation of the bench `br0` bridge, in `ensure_bench_bridge()` and the manual recipe alike, pins `bridge.mac-address` to `eth0`'s real hardware MAC before the uplink is brought up, so the router's static DHCP reservation stays valid; on an existing bridge a drifted MAC is only reported with the manual remedy, never repaired live (cycling a live bridge's MAC can cut the session's own connection); the comparison reads `nmcli` with `--escape no`; re-keying the router is the owner's out-of-repo follow-up.
- **Members**: G1.019, G8.060, G9.044
- **Provenance**: O — G9.044: CLAUDE.md hard rule on `br0`'s MAC; the flag-only part is A.
- **Truth**: holds — G1.019: `ensure_bench_bridge()` re-enforces MAC and channel (setup_toolchain.py:845-857) (others: G8.060 holds, G9.044 holds)
- **Fit / pillar**: restates CLAUDE.md hard rule; extends P9 (setup never damages the bench); restates CLAUDE.md B.13 rules · pillar P9 (all members)

### HR180 Dead-man's switch armed through host network risk
- **Req**: Any operation that can cut the connection to the bench host (creating or modifying the bridge, enslaving the uplink, cycling the AP, the manual `nmcli connection delete` recipe), whether started by a test, the installer or a documented manual recipe, runs with a recovery dead-man's switch armed for the whole risk window, re-armed per step or once for a measured atomic sequence; the recovery script is recreated fresh in the session scratchpad, not committed, and manual recipes that enslave `eth0` carry the arming step themselves.
- **Members**: G1.018, G8.061
- **Provenance**: A — G1.018: commit f35f021 (2026-09-04 SSH-lockout incident); no owner wording
- **Truth**: partly — G1.018: rule stated; `ensure_bench_bridge()` arms none itself (SPEC:1022-1025); dev_legacy/README.md's manual recipe only points to B.13; B.13 hardcodes the "Wired connection 1" profile name (others: G8.061 partly)
- **Fit / pillar**: restates CLAUDE.md hard rule; refines OR37.a (1) · pillar P9 (all members)

### HR181 No real credential committed; bench secrets generated
- **Req**: No real credential is committed: per-device config and host-spilled `config_*.cfg` files stay git-ignored; a new bench AP gets a freshly generated SSID and password (`secrets`), shown once at creation, never persisted in a tracked file and never echoed into logs or argv; the harness reads the bench PSK at run time (`bench.ap_password()` via `nmcli --show-secrets`, `$BENCH_AP_PASSWORD` override) and generates test-only SSIDs/passwords per session; the accepted hotspot fallback password appears in tests only as copies pinned to `_VAL_HOTSPOT_PW`'s default and `devices/*.toml`, each naming that source; credential rotation is not a bench capability.
- **Members**: G1.020, G5.089, G8.064
- **Provenance**: O — G1.020: owner 2026-09-25: "a pure throwaway board-bench-password ... The only topic to note and to check here throughout the audit is consistency ... persisting one in a file rather is a stylistic ... breach which will need harmonization"; SPECIFICATION.md:3136 …
- **Truth**: partly — G1.020: run-time read holds (bench_control.py:64-68); conftest copy pinned by test_tests_hardware_conftest_constants.py; the bench PSK is still committed in device_scripts/wifi_reconnect_after_failed_attempts_repro.py:10 (value not repeated here); hotspot copies in test_hotspot_role_reversal.py:43 and … (others: G5.089 partly, G8.064 partly)
- **Fit / pillar**: refines OR52.a (3) threat model; restates owner record (HW.T11); extends OR52.a (7) (public repo); refines plan 3.1 owner record · pillars differ: G1.020 P4, G5.089 process, P9, G8.064 P9

### HR182 Shared hotspot fallback password is an accepted risk
- **Req**: The hotspot fallback password (`"12345678"`, now a per-device TOML `hotspot_password`/`HotspotPW` default, falling back to the shared default at boot if out of bounds) is an accepted risk, exploitable only in radio range of a unit that already lost its WiFi, and is not rotated or removed without the owner's direction; every file carrying it is listed in `pyproject.toml`'s per-file S105/S106 exemptions so a new credential elsewhere still fails lint, and the docs (CLAUDE.md included) list its real locations.
- **Members**: G5.088, G9.091
- **Provenance**: O — G5.088: CLAUDE.md "accepted risk … not something to 'fix' by rotating/removing without the project owner's direction" (from `75f2e11`); OR52.a (3) radio-range out of scope
- **Truth**: drifted — G5.088: CLAUDE.md names two sites (legacy `async_connect.py`, `src/asy_wifi_service.py`) and pyproject.toml:168-169 "three known, accepted sites", while the literal is in all six `devices/*.toml` (grep) and exempted in eight Python files (`pyproject.toml:252,304-305,340-347`) (others: G9.091 drifted)
- **Fit / pillar**: restates owner risk acceptance; tension with the owner's 2026-09-25 "persisting one in a file … stylistic breach" (bench PSK; different … · pillars differ: G5.088 P2, G9.091 P3

### HR183 Wear-spending and long runs are default-off gates
- **Req**: Every hardware test that spends a limited-endurance write, a re-provisioning flash, a soak duration, the 12.4-day rollover wait or the physical light rig runs only behind its own default-off opt-in flag: persistence writes are deselected centrally in `pytest_collection_modifyitems()`, the others skip in-test, the flash and bench runners always exclude `long_soak` and `multi_day_rollover` so soaks start only through `run_bench_soak_tests.sh --tier`; a gate's help text states exactly which writes it spends, and a clean verdict means 'everything that ran passed', reported with its deselected count.
- **Members**: G1.004, G8.091
- **Provenance**: O — G1.004: CLAUDE.md "(project owner's explicit, standing direction, 2026-09-17)"; README:1309 "Standing design, project owner's own choice"; run_bench_soak_tests.sh "owner's direction, 2026-09-04"; OR49.a (2)
- **Truth**: partly — G1.004: gates exist and deselect/skip as stated (conftest.py:26-133, test_tests_hardware_persistence_write_gating.py runs real collect-only); `--allow-neopixel-sweep` help says "Spends no write of any kind" (conftest.py:57-69) while isl29125_mechanism_envelope.py:102-193 makes ~9 `_set_dict_cfg` flash … (others: G8.091 partly)
- **Fit / pillar**: restates CLAUDE.md wear rule; refines OR37.a (1), OR49.a (2); restates CLAUDE.md wear rule; tension with OR45.a (2) · pillar P9 (all members)

### HR184 Only SCD30 NVM and flash count as wear
- **Req**: Only SCD30 NVM and the RP2040 flash filesystem count as limited-endurance stores: writes to BMP3xx and ISL29125 configuration registers go to volatile memory (reset at power-on) and may be written freely by hazard and concurrency tests, and FRAM writes (10^12 cycles/byte MB85RS64V on wozi, 10^13 MB85RS2MTA on dev) sit outside every wear gate and budget, though not outside the evidence rules. SCD30 NVM values persist across power cycles on the bench, so tests never assume factory defaults and any NVM write a test owns stays behind `persistence_write`/`scd30_extra_write`.
- **Members**: G1.008, G1.009, G3.076
- **Provenance**: O — G1.008: OR49.a "FRAM writes do not count as wear" (2026-09-26); CLAUDE.md wear rule
- **Truth**: unverifiable — G3.076: bench NVM state (TempOffs 1.5 °C, 2026-09-02) needs the board; volatility of BMP/ISL config registers not re-read (others: G1.008 holds, G1.009 holds)
- **Fit / pillar**: restates OR49.a (2); refines OR49.a (2); restates CLAUDE.md wear rule, OR49.a (2) · pillar P9 (all members)

### HR185 Gate markers registered; a typo fails loudly
- **Req**: Every opt-in hardware marker is registered in `tests_hardware/conftest.py` with its reason and enabled by a flag named `--allow-<marker-in-kebab>` (harmonised under OR24); pytest treats unknown markers as errors (`--strict-markers`), so a misspelled or renamed wear or soak gate marker (`persistence_write`, `scd30_extra_write`, `flash_cycle`, `long_soak`, `multi_day_rollover`) fails collection instead of silently running a gated test ungated.
- **Members**: G1.042, G8.134, G10.064
- **Provenance**: O — G8.134: CLAUDE.md wear rule ("every operation that spends a limited-endurance write cycle is a default-off, explicitly-opted-into marker", owner 2026-09-17); the gap is C
- **Truth**: wrong — G8.134: markers are registered (`conftest.py:106-113`) but no `--strict-markers`/`addopts` exists in `pyproject.toml` or the conftests, so an unknown marker is only a `PytestUnknownMarkWarning`; `test_persistence_write_marker_completeness.py` guards omission, not misspelling (others: G1.042 partly, G10.064 partly)
- **Fit / pillar**: refines OR16.a (2); refines OR37.a (1), OR42.a (1); refines OR37/OR42, OR15.a (1) (CLI reference) · pillar P9 (all members)

### HR186 Routine runs spend no avoidable host wear
- **Req**: No test inflicts avoidable wear on the host: no test generates mass filesystem churn (an invariant is proven structurally, e.g. no `TmpScratch` operation reads `tests/_tmp`'s shared root, never by reproducing a symptom at scale), a full `test.sh` run stays sleep-bound with a small measured host write volume (about 46 MB today) re-measured when test structure changes, and a routine flash or bench run needs no third-party network and no full toolchain re-verification, which sits behind an opt-in gate or in the setup tier.
- **Members**: G1.010, G2.014, G8.107
- **Provenance**: O — G1.010: CLAUDE.md "(project owner's explicit, standing direction, 2026-09-17)"; OR37.a (1)
- **Truth**: partly — G1.010: `test_env_tier_flash_recurring_run_is_idempotent` runs `setup_toolchain.py env --tier flash` unmarked in every flash pass (test_toolchain_flash_boot.py:30-42) (others: G2.014 holds, G8.107 unverifiable)
- **Fit / pillar**: restates CLAUDE.md wear rule; refines OR37.a (1); restates OR37.a (1) · pillar P9 (all members)

### HR187 Device TOML wiring comes from real hardware
- **Req**: Every wiring fact in a device TOML (buses, pins, frequencies, chip selects, IRQ pins) comes from real, bench-validated hardware or the field unit's legacy `sensortask-*.py` source, cites its origin in a TOML comment and is never invented; a field device's TOML reproduces its legacy wiring, and a deliberate difference (e.g. the SCD30 bus's `timeout = 200000`) is recorded with its reason.
- **Members**: G8.032, G9.085
- **Provenance**: A — G8.032: `6db3199` (2026-09-14), "Add SPECIFICATION.md Part K"
- **Truth**: unverifiable — G8.032: review-only rule; the three neu units' wiring is from one legacy file, never checked against the physical units (GEN.N273) (others: G9.085 holds)
- **Fit / pillar**: refines OR10.a (procedure); refines OR48.a · pillars differ: G8.032 P10, G9.085 P9

### HR188 Raw-REPL access stops main.py; observe passively
- **Req**: Hardware tooling accounts for mpremote's raw REPL: `mpremote exec`/`run`/`is_reachable()` Ctrl-C `main.py`, and the raw-REPL soft reset never re-runs `main.py` (only a hard reset resumes the live system) while the watchdog, GC threshold, `ticks_ms()` counter and GPIO muxing survive it, so the board stays unfed until the armed 8 s watchdog resets it, and an attach within about 1 s of boot parks it at the REPL with no watchdog. Live-system observation therefore uses only passive means (`is_device_present()`, `tail_log()`, REST), every raw-REPL entry is followed by `hard_reset()`, a flash/bench test never ends on a parked board, and every heap figure names the threshold in force.
- **Members**: G1.030, G4.007
- **Provenance**: F — G1.030: mpremote transport_serial.py:178-179 writes Ctrl-C on raw-REPL entry; ports/rp2/main.c:246-247 runs main.py only in friendly-REPL mode; `mpremote reset` = `machine.reset()` via exec (tools/mpremote/mpremote/main.py:407-411)
- **Truth**: partly — G1.030: rule and fixtures honour it (conftest.py:253-254 kick+hard_reset, test_watchdog_starvation.py:44-47 ends on hard_reset); harness.hard_reset() docstring and test_reboot_persistence.py:1-3 call `mpremote reset` a "DTR-line hardware reset", but it is `machine.reset()` through a raw-REPL exec … (others: G4.007 holds)
- **Fit / pillar**: extends OR29.a (knowledge base); refines OR29.a (1) · pillars differ: G1.030 P9/P5, G4.007 P7

### HR189 Flash written only at two ConfigManager sites
- **Req**: The firmware writes its flash filesystem only through `ConfigManager`, at exactly two sites: `setup()` at most once per boot when a file is missing or needs repair, and `_flush_staged()` once per accepted PUT that changed a value; nothing re-runs either on its own (no timer, sleep, loop or retry, and no cross-boot 'repair failed' guard, since only an unrelated reboot loop could repeat a repair), at most one flush per instance is in flight and `flush_pending()` awaits the latest; docs state both paths wherever they argue safety from 'no write in flight'.
- **Members**: G5.031, G5.033, G5.034
- **Provenance**: O — G5.031: C.7.3 "(owner, 2026-09-24)"
- **Truth**: drifted — G5.034: CLAUDE.md:199-201 says "every real flash write is reachable only through the REST PUT path" and BACKLOG.md:168-170 "it never happens on its own", but `ConfigManager.setup()` rewrites files at boot on its own (`config_manager.py:474-481`); SPECIFICATION.md F.2 (:3639) narrows it to "triggered … … (others: G5.031 holds, G5.033 holds)
- **Fit / pillar**: restates OR42.a (1); refines OR42.a (1) ("at most once per boot, then stable") · pillar P9 (all members)

### HR190 A failed config write costs persistence only
- **Req**: A PUT answers on validated values: the client's `"Valid"` means validated and staged. A config write that fails (setup's create/repair, errno 4, or a deferred flush, errno 14) keeps the validated values live, is logged, is never reported back to the client, is never retried, and never ends a task or causes a reboot.
- **Members**: G5.032, G6.088
- **Provenance**: O — G5.032: C.7.3 "a reboot loop that also wrote the flash on each pass (owner, 2026-09-24)"
- **Truth**: holds — G5.032: `_cache` committed in `finally` (`config_manager.py:382-384`), setup failure runs unpersisted (`:476-485`); consequence noted: a flush failing mid-`json.dump()` leaves an unparseable file (open "w" truncates first) that the next boot rebuilds from defaults, losing that change … (others: G6.088 holds)
- **Fit / pillar**: extends P3 (degrade, never reboot); refines OR42.a (bounded writes) · pillars differ: G5.032 P3, P9, G6.088 P9

### HR191 Device scripts live within the 8 s watchdog
- **Req**: Every device script runs under the `machine.WDT(timeout=8000)` that `run_isolated()` arms before it, against the frozen image rather than the tree; because an mpremote soft reset never disarms an rp2 watchdog and a re-`WDT(timeout=...)` takes the new timeout, any script or hardware test that can outlast the window feeds or deliberately re-arms it, chunking any longer wait or busy loop (at most 2 s) with a `wdt.feed()` between, and a link or rig fault inside a wait ends in a FAIL line, never a silent watchdog reset.
- **Members**: G1.031, G4.006
- **Provenance**: F — G1.031: rp2 WDT is re-armable, not stoppable, max 8,388 ms (ports/rp2/machine_wdt.c:38 `WDT_TIMEOUT_MAX 8388`); rule A (dc3ee33, 441de83)
- **Truth**: partly — G1.031: harness arms it (harness.py:444, 458); feeding is review-only; uart_read_never_blocks_the_loop.py:42-58 busy-waits unbounded with no feed; wifi_reconnect_after_failed_attempts_repro.py and wifi_service_reconnect_repro.py wait up to 10-13 min with no feed; the documented feeding wrapper … (others: G4.006 holds)
- **Fit / pillar**: refines OR29.a (4) (watchdog budget); refines OR29.a (4) · pillars differ: G1.031 P5, G4.006 P9

### HR192 DHCP behaviour is outside the test scope
- **Req**: DHCP-client flakiness on the bench network and the AP-side DHCP server (CYW43 firmware, no project code) are out of the project's test scope: network-robustness tests treat 'WiFi up, no internet' as NTP/DNS unreachable and deliberately never inject DHCP faults (they could strand the DUT), and tests only use DHCP results (a lease, a gateway), never assert DHCP behaviour itself.
- **Members**: G1.089, G6.069
- **Provenance**: A — G1.089: test docstring "deliberately out of scope (see BACKLOG.md)"
- **Truth**: holds — G1.089: no DHCP assertions in tests_hardware/ (others: G6.069 holds)
- **Fit / pillar**: refines OR18.a (not project-fixable); refines OR49.a (no destructive or uncontrollable tests) · pillars differ: G1.089 P5, G6.069 P9

### HR193 Twin runs own their state and archive evidence
- **Req**: A twin run's config directory and state files are owned by that run (per-run scratch, or one tier at a time under a lock), never a fixed repo-relative path shared with other suites; each twin runner clears exactly its own known scratch before starting, never wipes state another concurrently usable tier owns, and archives evidence (twin FRAM/SCD30 state, logs) rather than deleting it.
- **Members**: G7.048, G8.093
- **Provenance**: O — G7.048: OR38.a (1) "anything shared between tests or parallel processes (... file names, directories, state files ...)".
- **Truth**: drifted — G8.093: `run_digital_twin_ci.sh:10-11` and `_digital_twin_ci_suite.py:6` claim the shell script cleans, but it has no clean step; `_clean_state()` removes two JSON files and `config/`; `cross_browser_smoke.mjs:451` `rmSync`s the shared `digital_twin/config` (others: G7.048 partly)
- **Fit / pillar**: restates OR38.a (1); restates OR38.a (1)-(2) · pillars differ: G7.048 P9, G8.093 P7

### HR194 Board resolved by USB identity, exactly one
- **Req**: The board is resolved by the RP2040/MicroPython USB vendor ID `2e8a` and its stable `/dev/serial/by-id` name, never by a bare ttyACM scan (the bench's Arduino peer, 2341, is on the same host); zero or several matches is a hard error naming `--device`/`MPREMOTE_DEVICE`, never a guess, and every entry point (the installer, the harness, `scripts/mpremote_connect.sh`) uses the same resolution.
- **Members**: G1.021, G8.065
- **Provenance**: A — G1.021: harness docstrings; discovery consolidated in 9cfb3b3
- **Truth**: partly — G1.021: harness resolution pinned by test_resolve_board_device.py; mpremote_connect.sh:8 still defaults to `/dev/ttyACM0`; setup_toolchain.py:629-632 accepts any 2e8a device (a debug probe counts) (others: G8.065 holds)
- **Fit / pillar**: new (bench safety); extends P9 (never flash the wrong board) · pillar P9 (all members)

### HR195 API claims rest on pinned source, rechecked
- **Req**: A session asserts how a MicroPython or Microdot API behaves only after reading the pinned source or current upstream docs (GitHub `docs/` when the docs hosts are blocked), never from memory, and cites what it read; every Microdot behaviour the REST layer relies on (dispatch semantics and handler return shapes, the body read before the 413 check, hook order, error-handler lookup keys, header writes ending in a separate blank line, the `send_file` short-read loop, muted socket errnos, HTTP/1.0 without keep-alive) is stated with its source line and rechecked whenever `ext/microdot.py` moves.
- **Members**: G4.002, G6.071
- **Provenance**: O — G6.071: CLAUDE.md "Always check current MicroPython and Microdot documentation before asserting how an API behaves"
- **Truth**: holds — G4.002: holds as practice (convention only); BACKLOG's `readfrom_mem_into()` verification is one honoured instance (others: G6.071 holds)
- **Fit / pillar**: restates OR4 · process; restates CLAUDE.md standing practice · pillars differ: G4.002 ?, G6.071 P4

### HR196 Stored config survives key changes; full schema
- **Req**: Loading a config file with a missing, renamed, invalid or unknown key replaces only that key by its default (logging a warning) and keeps every other stored value, never resetting the whole file; because `setup()` drops and rewrites any on-disk key not in its schema, every `ConfigManager` on a real file (firmware, script or test) is constructed with that file's complete production schema; from the release on, persisted keys and file names change only with a migration, pinned by a golden stored-config fixture.
- **Members**: G5.037, G9.077
- **Provenance**: O — G5.037: OR52.a (2) (owner, 2026-09-26) for the release-stability half; hazard text is A (`6f430c7`)
- **Truth**: partly — G5.037: the hazard holds (`config_manager.py:446-463` removes unknown keys, wrnno 5); no golden fixture test exists yet; enforcement for scripts is caller discipline only (others: G9.077 holds)
- **Fit / pillar**: restates OR52.a (2); refines OR52.a (2) (golden stored-config test) · pillars differ: G5.037 P8, P9, G9.077 P1

### HR197 UDP and DNS: IPv4-only, never raise
- **Req**: The project is IPv4-only end to end (resolver A records, `AF_INET`/`SOCK_DGRAM` sockets, address tuples), and an IPv6-shaped resolver result degrades to 'no reply', never a crash. `AsyUDPSocket` I/O, `resolve_ipv4()` and the captive DNS return their sentinels and never raise (`AsyUDPSocket.__init__` excepted). `AsyUDPSocket` is content-agnostic, validates `mode` eagerly, silently truncates an over-long datagram (documented), keeps `(b"", addr)` distinct from `(None, None)`, serialises `connect`/`disconnect` with a per-instance lock, never widens an except to `CancelledError`, is used from one coroutine at a time and owns no logger, so every caller checks `disconnect()`'s bool and logs a failure. `resolve_ipv4()` returns a literal IPv4 host unchanged, otherwise resolves one A record over UDP (512-byte replies, bare-pointer answer names, query refused when a label exceeds 63 octets, placeholder or malformed servers skipped, DHCP server first then public fallbacks), any unparseable reply being `None`; callers pass their real timeout.
- **Members**: G6.043, G6.048, G6.049, G6.050
- **Provenance**: A — G6.043: `a6abe13` (resolver) and the UDP exception audit; C.7 bool rule
- **Truth**: partly — G6.043: only `captive_dns.py:139-153` checks and logs; `asy_ntp_client.py:188` and `asy_dns_client.py:120` discard the result, and NTP's fetch has no `finally` around `disconnect()` (N030, a cancel mid-fetch skips it); C.7.1 row "every failure surfaces to exactly one upstream owner" does not hold for … (others: G6.048 holds, G6.049 holds, G6.050 partly)
- **Fit / pillar**: refines OR38.a (1) (no leaked sockets); new; refines OR52.a (3) (robust to malformed input) · pillars differ: G6.043 P1, G6.048 P2, G6.049 P6, G6.050 P2

### HR198 Named modules never raise; they return sentinels
- **Req**: `base_classes.py`, `config_manager.py`, `print_log.py`, `system_service.py`, `asy_fram_manager.py`, `asy_fram_driver.py` (outside its one-time `__init__`/`setup()` errors) and `math_helpers` return a documented sentinel on every path and never raise; `math_helpers` returns None for a None, out-of-domain or NaN input and for any residual `ValueError`/`ArithmeticError`, relying on a domain gate before computation and not defending against wrong types; raw bus drivers are the one allowed exception, and their only callers catch what they raise.
- **Members**: G3.006, G5.010
- **Provenance**: A — G3.006: rule text since `b85a056`
- **Truth**: holds — G3.006: gates of the form `not (lo <= x <= hi)` reject NaN; `ZeroDivisionError` is an `ArithmeticError` subclass (`py/objexcept.c:317`), so the catches are complete (and ALGO.N075's reverted explicit catch was redundant) (others: G5.010 holds)
- **Fit / pillar**: restates SPEC D.2; refines OR26; restates OR26 · pillar P2 (all members)

### HR199 A third-party outage never reads as red
- **Req**: A third party's momentary outage never reads as a red test result: every CI job that syncs, and the installer's `env`, run `uv sync` with three attempts (10 s/20 s pauses) before the tests, because `actionlint-py` downloads its binary inside its build backend, and the retry is never simplified away; `apt-get update` failures from unrelated sources are tolerated and logged while every `apt-get install` stays fatal, in the toolchain installer and `setup_cross_browser_toolchain.sh` alike.
- **Members**: G8.058, G8.132
- **Provenance**: O — G8.132: OR37.a (2) (owner, 2026-09-26): "the three-attempt `uv sync` retry (third-party outages)" stays; F — HTTP 500 on 2026-09-13, 504 on 2026-09-14
- **Truth**: partly — G8.132: six hand copies in `ci.yml` plus the composite action and `setup_toolchain.py:121` (`UV_SYNC_ATTEMPTS = 3 # mirrors ci.yml`), no single source; `unit-tests-gc-threshold` relies on the action's copy only (others: G8.058 holds)
- **Fit / pillar**: restates OR6.a (third-party outage ≠ red); restates OR37.a (2), OR6.a · pillar P3 (all members)

### HR200 Static imports only; frozen set is the closure
- **Req**: Every import is a plain static `import`/`from ... import` statement, never `__import__` or `importlib`, so a device's frozen-module set can be derived as the seed (declared drivers plus the fixed core) closed over real static imports after `TYPE_CHECKING` stripping; default providers stay import-free, and no module name exists in both `src/` and `ext/`, which are frozen flat into one directory.
- **Members**: G5.006, G8.017
- **Provenance**: O — G5.006: "project owner's explicit, standing rule, not just a style preference" (F.1); added in `6aed3c9` (2026-09-09)
- **Truth**: drifted — G5.006: `src/` holds (0 sites); but `digital_twin/run_generic_integration.py:356`, `tests/_sensortask_scenarios.py:127,365,505,834`, `tests/_webserver_concurrency_scenarios.py:100`, `tests/_digital_twin_construction_scenarios.py:98`, `tests/_boot_contiguity_probe.py:125`, … (others: G8.017 partly)
- **Fit / pillar**: extends P8 (static derivability); extends P6, OR46.a (imports level) · pillars differ: G5.006 P4, G8.017 P6
- **Note**: G5.006 records dynamic imports in `digital_twin/` and `tests/` scenario helpers; whether 'project-wide' (G8.017) covers test code is unresolved.

### HR201 MicroPython stubs derived, isolated, repaired
- **Req**: The board stubs install into `typings/`, never a dependency group (they replace mypy's typeshed), at the version derived from the pinned `ref` (`==X.Y.Z.*`); a missing upstream release blocks typechecking with an actionable error and no fallback. A verified stub defect is handled where it lives: repaired in the installed stub tree, conditionally so the repair no-ops once upstream ships the fix, or modelled by the test fake, with its removal trigger named, never answered by `type: ignore` in `src/` or `digital_twin/`.
- **Members**: G4.053, G8.087
- **Provenance**: A — G4.053: CLAUDE.md "(added with the 1.29 bump)"; stub gaps F against source (`machine_timer.c:118-127` bare `Timer()` valid)
- **Truth**: partly — G4.053: `typecheck.sh` repairs are conditional; `Timer()`, `const()`-as-`Any`, private `_mpy_shed` import and `DeflateIO` workarounds state no removal trigger; `tests/test_asy_fram_manager.py:1599-1602` uses `type: ignore[return-value]` for `gather()` (tests, allowed) (others: G8.087 partly)
- **Fit / pillar**: new; extends P8 (one pin) · pillar P4 (all members)

### HR202 Fake and twin modules named after the real
- **Req**: Platform fakes carry the real module name (`machine.py`, `network.py`, `neopixel.py`) in `tests/` and `digital_twin/` alike, digital-twin chip models live in `_<chip>_chip.py` as `<Chip>Chip` classes, every other non-test file under `tests/` is an `_`-prefixed helper, and scenario libraries are `_<tier>_scenarios.py` with a `register_for_device()` factory and one-call per-device wrappers.
- **Members**: G10.058, G10.080
- **Provenance**: A — G10.058: E.2.1 (2026-09-17 split)
- **Truth**: holds — G10.058: 17/17 non-test files; 18/18 wrappers are `globals().update(register_for_device("<device>"))` (others: G10.080 holds)
- **Fit / pillar**: restates E.2.1; restates E.6.5 · pillar P5 (all members)

### HR203 Twin and hardware HTTP clients share one contract
- **Req**: `tests_hardware/http_client.py` keeps the same `HttpResponse`/`fetch()` shape as `digital_twin/_http_client.py`, so host-side test logic runs unchanged against the twin and the board; the client relies on the server always answering `Connection: close`, treats an empty response as a connection-ceiling refusal (`CeilingRefusedError`, an `OSError`), decodes only JSON objects, and never calls `.json()` on a drained (`read_body=False`) response.
- **Members**: G1.074, G7.046
- **Provenance**: A — G1.074: module docstring
- **Truth**: partly — G7.046: every empty response, not only a refusal, is classed as a ceiling refusal by callers' `except OSError` (TWIN.N031, a blindness risk under OR21); `type: ignore[type-var]` at `:35` is a stub gap with no removal trigger. (others: G1.074 not checked)
- **Fit / pillar**: refines OR45.a (2)(b) and OR21.a (1) (hardware logic pointed at the twin); refines OR21 · pillar P5 (all members)

### HR204 A tag field or group is declared once
- **Req**: Each `@web-group` is declared by exactly one source file (other modules only add fields to it) and each field carries at most one tag per family (`@limits` domain, `@wiring` field, `@value-wiring` field); buildgen fails the build on a missing or duplicate declaration, since the second would silently win.
- **Members**: G6.065, G8.043
- **Provenance**: A — G8.043: `415438e` (2026-09-10)
- **Truth**: holds — G6.065: holds (others: G8.043 holds)
- **Fit / pillar**: refines OR43.a (3); extends G8.002 · pillars differ: G6.065 P8, G8.043 P5

### HR205 Every pointer and citation resolves
- **Req**: Every pointer in code, tests and docs (to CLAUDE.md, BACKLOG.md, a SPECIFICATION.md Part, a docstring, another file) names a target that exists and says what the pointer claims, and a pointer into a rule document is checked when that document changes; evidence cited as 'archive §...' of `HEAP_FRAGMENTATION_MEASUREMENTS.md` stays reachable because commit `12640c2` stays an ancestor of `main` (merge, never squash), and each citation names the commit once where the reader meets it.
- **Members**: G9.003, G9.004
- **Provenance**: A — G9.003: implied; the owner's own words are OR11 ("no crosslinks are broken") and OR51 ("placed, cited and crosslinked correctly").
- **Truth**: drifted — G9.003: both hard-rule pointers dangle at HEAD; 47 more dangling or misdirected pointers are drift-only (group R). (others: G9.004 holds)
- **Fit / pillar**: restates OR11/OR51 for pointers; refines PQ2 answer (merge commit) · pillars differ: G9.003 P8, G9.004 P7

### HR206 Instance, file and logger names built once
- **Req**: Every per-instance REST key, config filename and logger name is built by `config_manager.instance_name(base, ext)` (an empty extension reproducing the single-instance name byte for byte), and a module's config file name `config_<name>.cfg` and config logger name `CFGMGR_<name>` are built only by `SensorReaderConfig` from `self.name`; no module rebuilds them by hand.
- **Members**: G5.018, G10.079
- **Provenance**: A — G5.018: `6aed3c9` (2026-09-09, build-chain session 1)
- **Truth**: partly — G10.079: 1 duplicate construction; `config_manager.py` is the only flash writer (`:375,:476`), which holds (others: G5.018 holds)
- **Fit / pillar**: restates OR24; restates C.14.1; P8 · pillars differ: G5.018 P4, P10, G10.079 P8

### HR207 Dispatch-only set derived from @web tags
- **Req**: Which PUT fields are dispatch-only (re-dispatched on every submit, never persisted, never `"Unchanged"`) is derived from the `@web` `dispatch=true` tags plus the webserver's own action fields, never a hand or prose list, and every consumer (renderer, mock, test matrices, persistence-write gate, docs) reads the derived set, a command-only toggle GET cannot report (`ContMeas`) classified the same way everywhere. A REST write persists only when a field validates and changes its stored value, so a hardware test sending only rejected, unknown, unchanged or dispatch-only fields carries no `persistence_write` marker; this does not hold for SCD30 until OR42.c's compare-before-write lands.
- **Members**: G1.006, G7.054
- **Provenance**: O-confirmed — G1.006: OR49.a (2) "reads, rejected writes and unchanged writes only"; harmonization 11
- **Truth**: drifted — G7.054: at least five disagreeing hand lists: H.4 (4 + tagged `SGPResetVOC`, `ISLCalibrate`), H.6 (adds `ContMeas`, omits `ISLCalibrate`), `mock-server.js:22` `SENSOR_QUIRK_FIELDS` {ForceCalRef, ContMeas, SGPResetVOC, ISLCalibrate} plus `:244`'s own list, `_put_field_cases.js:14` {SystemCmd, PauseTime, … (others: G1.006 partly)
- **Fit / pillar**: restates OR49.a (2); depends on OR42.c; refines P8; relates OR42.c (2) (ContMeas stays a command) · pillars differ: G1.006 P9, G7.054 P8

### HR208 Host-side setup effects listed and provisioned
- **Req**: Everything the bench tier needs on the host (passwordless sudo for `nmcli`, `iw`, `iptables`, `tc`, `tcpdump`, `tee` and `picotool`, `br_netfilter`, packages Raspberry Pi OS lacks) is provisioned by `setup_toolchain.py env --tier bench` or listed in one place with its reason; the installer's host-wide changes (sudo apt installs, picotool in `/usr/local`, `dialout` membership, the bench bridge, persistent `br_netfilter`/sysctl files) are listed in the docs, happen only in the tiers that need them and are the only host-wide changes it makes, and a sandbox-built picotool without USB support or a stale system picotool is detected and reported.
- **Members**: G1.082, G8.066
- **Provenance**: A — G1.082: harvest ASSUME items
- **Truth**: partly — G8.066: every `env` tier runs a full `setup` (sudo apt, `sudo make install` of picotool), and `test.sh` auto-runs `setup` when the binary is missing or the wrong variant; `sysctl` temp file leaks if `sudo cp` fails (`:815-840`) (others: G1.082 not checked)
- **Fit / pillar**: refines OR15.a (1) (install from scratch); extends OR37.a (1), OR50.a (3) · pillars differ: G1.082 P4, G8.066 P9

### HR209 Field units stay 1.26 until runbook reflash
- **Req**: Fielded units keep MicroPython 1.26 and the legacy firmware until a deliberate reflash campaign; only the refactor targets the pinned version, and no claim verified at 1.28/1.29 is extrapolated to 1.26 behaviour. Legacy units get fresh setup after reflash, following a reflash runbook covering littlefs residue and region size (1.26 to 1.29), hostname and DHCP reservation, SCD30 NVM survival and the first-boot hotspot/permanent-deactivation hazard; no config migration code is written.
- **Members**: G4.004, G9.089
- **Provenance**: O — G9.089: OR52.a (1).
- **Truth**: partly — G9.089: no runbook exists yet; SPEC F.5:3681 still says "BACKLOG open question 3". (others: G4.004 holds)
- **Fit / pillar**: refines OR52.a (1); restates OR52.a (1) · pillars differ: G4.004 P3, G9.089 process

### HR210 Undocumented ISL29125 behaviour is measured on silicon
- **Req**: Where the ISL29125 datasheet is silent or contradicted by silicon (BOUTF cleared by status read and reset, 0x08 reading 0x00 after reset, reserved bits reading zero, 16-byte reads not rolling over, PRST counter restarting on flag clear, whether a CONFIG1 write restarts an in-flight conversion, whether PRST counts RGB cycles or single integrations), the behaviour is measured on silicon and recorded in SPEC M.1.2 with date and specimen count, the twin models every row, the PRST unit that `persist_for_interval()` depends on is asserted while the restart question is reported only, and a second specimen or a changed rig or cover triggers re-measurement of these and of the hysteresis band and PRST windows.
- **Members**: G3.047, G3.100
- **Provenance**: A — G3.047: measurements 2026-09-12/13 on one board
- **Truth**: unverifiable — G3.047: needs hardware; the twin comments cite each measured row (checked presence only) (others: G3.100 unverifiable)
- **Fit / pillar**: restates OR17.a (fidelity table) and OR29.a (3); restates OR17.a (4)/OR29.a (2) · pillar P5 (all members)

### HR211 Every test is collected and every script driven
- **Req**: Every test function a file defines actually runs: a `tests/test_*.py` file holds only synchronous `def test_*` functions and ends with the `microtest.run(globals())` trailer, and a file missing the trailer, a file collecting zero tests, an `async def test_*` never awaited or a check missing from a hand-kept registry (e.g. `_uart_link_contract.ALL_CHECKS`) fails the run instead of reporting `0/0 passed` or PASS. Every device script is driven by a host test that asserts its result or is retired per OR33.a with its intent moved elsewhere; a report-only or always-PASS script is not a test.
- **Members**: G1.077, G2.005, G10.059
- **Provenance**: O — G2.005: OR16.a (2) "every test file is collected by some runner and CI job, none is orphaned"; OR15.a (2) summary counts
- **Truth**: partly — G1.077: four scripts have no host runner at HEAD (grep over tests_hardware/*.py outside device_scripts/): heap_layout_after_full_boot_sequence, wifi_country_hostname_edge_values, and the two WiFi repros; the first two always print PASS (others: G2.005 partly, G10.059 holds)
- **Fit / pillar**: restates OR16.a (2), OR33.a; refines OR16.a (2); restates E.2 · pillar P5 (all members)

### HR212 test.sh reports to CI through annotations
- **Req**: `scripts/test.sh` never writes its verdict to `$GITHUB_STEP_SUMMARY` (summaries are in no API and a nested run would append to its parent's); under GitHub Actions every red outcome is an `::error` annotation, the pytest tier first, then up to eight failing files with their last 40 log lines, then one 'and N more', inside GitHub's ten-per-step limit, and a missing log never aborts the summary.
- **Members**: G8.105, G8.122
- **Provenance**: A — G8.105: `5ca5d4a` (2026-09-24)
- **Truth**: holds — G8.105: `test.sh` has no `GITHUB_STEP_SUMMARY` (grep); no test pins the absence (the SPEC's "pins it" refers to the annotations) (others: G8.122 holds)
- **Fit / pillar**: refines OR15.a (2) · pillar P5 (all members)

### HR213 Emitted-byte changes are owner flag days
- **Req**: A UART protocol change should only tighten receiver validation; a change to emitted bytes (enabling a CRC, a delimited codec, a shorter ACK) is a coordinated flag day needing an explicit owner decision, which the Python side may lead once recorded. The pass-through codec stays the default so the fixed frame size is the framing, and the deployed `dev` link runs `CRC_Pass` as the supported interim with payload corruption undetected and accepted; the CRC algorithm and byte order are specified, never inherited (`crc_checks.py`'s MSB-first big-endian CRC16 is not wire-compatible with the legacy/C native-order variant, so selecting it is changelog A7's flag day), and a CRC instance is never shared between link ends.
- **Members**: G6.004, G6.031
- **Provenance**: O-confirmed — G6.004: changelog "the project owner has decided (2026-09-11) that the Python side may lead it"
- **Truth**: holds — G6.004: `dev.toml` wires no `crc=`/codec; `Framing_Pass` default; buildgen emits neither (`validate.py:256-258`) (others: G6.031 holds)
- **Fit / pillar**: restates OR24.a (2) (UART wire format not touched during the audit); new (accepted boundary) · pillars differ: G6.004 P8, G6.031 P2

Singletons: 369

G1.001, G1.005, G1.007, G1.011, G1.012, G1.013, G1.017, G1.026, G1.029, G1.039, G1.040, G1.043, G1.045, G1.048, G1.051, G1.052, G1.055, G1.057, G1.059, G1.065, G1.066, G1.067, G1.080, G1.083, G1.085, G1.086, G1.087, G1.091, G1.095, G1.099, G1.100, G1.102, G1.105, G2.006, G2.015, G2.021, G2.023, G2.024, G2.025, G2.027, G2.030, G2.033, G2.037, G2.043, G2.044, G2.045, G2.046, G2.053, G2.056, G2.059, G2.066, G2.068, G2.073, G2.074, G3.001, G3.004, G3.005, G3.007, G3.009, G3.010, G3.013, G3.015, G3.022, G3.023, G3.025, G3.027, G3.029, G3.032, G3.034, G3.040, G3.041, G3.042, G3.043, G3.046, G3.048, G3.049, G3.050, G3.051, G3.052, G3.053, G3.054, G3.055, G3.056, G3.057, G3.059, G3.062, G3.064, G3.071, G3.075, G3.077, G3.079, G3.082, G3.083, G3.085, G3.089, G3.091, G3.092, G3.093, G3.096, G3.097, G3.098, G3.102, G3.104, G3.105, G3.106, G4.003, G4.009, G4.011, G4.018, G4.023, G4.024, G4.025, G4.033, G4.038, G4.040, G4.041, G4.043, G4.046, G4.047, G4.049, G4.055, G4.058, G4.063, G4.064, G4.076, G4.078, G4.081, G4.082, G4.087, G5.004, G5.007, G5.011, G5.014, G5.020, G5.021, G5.022, G5.023, G5.026, G5.027, G5.028, G5.036, G5.039, G5.041, G5.043, G5.044, G5.049, G5.050, G5.051, G5.055, G5.060, G5.065, G5.066, G5.067, G5.069, G5.070, G5.072, G5.073, G5.074, G5.077, G5.078, G5.083, G5.087, G5.090, G5.093, G5.094, G6.003, G6.007, G6.008, G6.009, G6.010, G6.011, G6.012, G6.013, G6.014, G6.015, G6.016, G6.017, G6.020, G6.021, G6.023, G6.025, G6.026, G6.029, G6.030, G6.038, G6.042, G6.046, G6.051, G6.054, G6.056, G6.059, G6.060, G6.067, G6.072, G6.073, G6.076, G6.077, G6.078, G6.084, G7.002, G7.005, G7.006, G7.009, G7.010, G7.011, G7.012, G7.013, G7.015, G7.016, G7.017, G7.019, G7.020, G7.024, G7.025, G7.026, G7.027, G7.029, G7.030, G7.031, G7.035, G7.043, G7.044, G7.053, G7.059, G7.060, G7.061, G7.062, G7.063, G7.064, G7.065, G7.066, G7.067, G7.069, G7.070, G7.073, G7.074, G7.077, G7.080, G7.081, G7.082, G7.083, G7.085, G8.002, G8.003, G8.004, G8.006, G8.007, G8.008, G8.009, G8.013, G8.014, G8.015, G8.016, G8.019, G8.020, G8.021, G8.027, G8.028, G8.031, G8.034, G8.035, G8.037, G8.038, G8.040, G8.041, G8.046, G8.048, G8.049, G8.051, G8.054, G8.055, G8.056, G8.057, G8.063, G8.067, G8.069, G8.071, G8.072, G8.074, G8.076, G8.077, G8.081, G8.097, G8.099, G8.100, G8.108, G8.112, G8.114, G8.117, G8.118, G8.119, G8.120, G8.121, G8.123, G8.125, G8.126, G8.127, G8.128, G8.129, G8.130, G9.007, G9.010, G9.011, G9.012, G9.013, G9.015, G9.016, G9.017, G9.019, G9.055, G9.058, G9.060, G9.073, G9.076, G9.079, G9.082, G9.083, G9.084, G9.092, G9.093, G9.095, G9.099, G9.100, G9.101, G10.002, G10.003, G10.004, G10.005, G10.008, G10.009, G10.010, G10.011, G10.012, G10.013, G10.015, G10.016, G10.017, G10.018, G10.019, G10.020, G10.022, G10.027, G10.031, G10.032, G10.033, G10.034, G10.037, G10.038, G10.040, G10.041, G10.042, G10.048, G10.050, G10.051, G10.052, G10.053, G10.054, G10.055, G10.056, G10.057, G10.061, G10.063, G10.065, G10.066, G10.067, G10.070, G10.071, G10.073, G10.074

### ID check

Script check (`scratchpad/mrg/gen.py`): 965 candidate headings parsed from G1-G10 (G1 109, G2 74, G3 109, G4 87, G5 96, G6 88, G7 86, G8 134, G9 101, G10 81); 965 placements = 596 in clusters + 369 singletons; duplicates 0, missing 0, unknown 0. Every ID appears exactly once.

### Contradictions inside clusters

- HR012 (One central repeat rule protects every error ring): G6.022 states UART's own per-episode budget (partly owner-decided W11-over-W10, 2026-09-18) as a requirement and conflicts with OR35.b's single central rule; G3.066 is explicitly interim. Resolved by provenance: OR35.a/OR35.b (owner, 2026-09-26) is later and …
- HR022 (No nested asyncio.run, no async generators): G2.020 records that CLAUDE.md's stated mechanism (a fresh event loop replacing the queue) does not match v1.29.0 `extmod/asyncio/core.py:247-248`; the rule itself is undisputed. The mechanism wording is unresolved until re-traced.
- HR030 (SGP40 general-call reset: setup only, recorded): G3.038 calls it an accepted low risk (agent acceptance, f5c9f90); G9.070 finds no owner decision and a new-vs-field divergence. Resolved by OR48.a (2): an agent acceptance is not an owner decision, so the divergence goes to the owner (unresolved until then).
- HR036 (A sample never claims freshness it lacks): Contradiction: G3.060 (owner, SPEC M.1.1 req 16) forbids publishing an unprovable sample as fresh; G3.044 and G3.058 (agent design, tests) publish a freshly stamped filter-off sample and a possibly-stale post-settle sample. Resolved by provenance for the …
- HR045 (PUT results: four words, envelope stays OK): G5.042 (ERR/100 with empty result) and G6.079/G7.068 (every field Failed, envelope OK) describe two layers, checked at HEAD: `handle_set_cmd()` returns `make_response(100)` and `_put_sensors` maps that to `"Failed"` per key …
- HR046 (SCD30 not-ready cycle reuses the last reading): Tension with the ISL29125 no-stale-sample rule (HR036) and P1; resolved for SCD30 by the owner direction in `110f3db` (legacy behaviour prioritised).
- HR061 (Sensor driver module shape is uniform): Contradiction: G3.087 (agent, C.2) requires the DeviceSession as 'verbatim boilerplate' per driver; G10.006 requires one shared class. Resolved toward one shared class by OR24 'one material' and Part G.1 'never reimplement' (owner-level basis over agent text).
- HR067 (Quote annotations only for TYPE_CHECKING names): Contradiction: G5.002 carries the owner's D.6 decision (2026-09-24) 'existing files are not mass-edited'; G10.025 harmonises all. Resolved by OR24/OR24.a (owner, 2026-09-25, 'change, don't flag'), the later ruling.
- HR073 (Nothing in the product exists for tests): G5.076 notes a tension with OR36.a (3) over whether FRAM's `override_pause` is 'a function of the hardware'; unresolved at cluster level.
- HR074 (One per-function explanation form per scope): G10.029 notes CLAUDE.md's wording allows function docstrings while D.11 forbids them in `src/`; drift, resolved toward D.11 as the more specific rule (unresolved for host scopes until one form is chosen).
- HR080 (Divergence from legacy field behaviour is explained): G3.101 records that the ISL29125 exemption lives only in SPEC M.1 while CLAUDE.md's rule states none (drift, not a contradiction).
- HR082 (Command-only fields are never persisted): G3.068 says a command-only field carries its device prefix, while G10.009 (key spelling, outside this cluster) says keys carry no per-driver prefix; unresolved naming question for the OR24 key-scheme harmonisation.
- HR097 (Code and fakes model rp2's real raise surface): Contradiction: G4.015 says I2C never raises `ENODEV` (SoftI2C's); G3.024 shows the zero-length-write probe path does (`extmod/machine_i2c.c:203`). Resolved by that source (F) in G3.024's favour; SPEC C.12's 'never ENODEV' is wrong for probes.
- HR111 (Twin fakes independent, held to shared contracts): G2.036 flags a tension with P8 'one material' (duplicated fakes); resolved by the owner's explicit instruction to keep them independent (`b8791e6`).
- HR115 (gc.collect only at boot placement or baselines): G7.041 conflicts SPEC I.4's 'don't re-flag it without new evidence' for the twin sampler; resolved by OR39.a (1) (owner), the later row.
- HR121 (Unreachable defensive branches: labelled, tested, registered): G5.013 flags a conflict with OR46.a (2) (confirmed leftovers, 'unreachable branches' included, are removed) against the owner-confirmed keep-and-note convention (`500851c`, G2.057). Unresolved: whether registered defence-in-depth branches count as OR46.a …
- HR123 (Soak trend retries once, noise-calibrated): Both members note tension with OR37.a (2) ('a retry never counts as a race fix'); resolved: this retry repeats a noisy measurement, it is not a race fix.
- HR143 (UART code never blocks the asyncio loop): G4.022 extends the idle-rate rule beyond UART and records that `asy_udp_socket.ready()` polls every 20 ms forever for captive DNS; that extension is agent-level (A) over the owner's UART-specific rule.
- HR153 (Frozen website: vendored freezefs, never compressed): Contradiction on reproducibility: G8.096 requires a byte-reproducible archive (and finds `gzip -9` without `-n` embeds mtimes); G7.078 accepts the embedded local build time. Both agent-level (A); unresolved, needs the owner. G8.096's 'freezefs 2.4' naming is …
- HR165 (VOC algorithm stays a literal, traceable port): Apparent contradiction: G3.012 says it traces Sensirion's reference, G9.098 DFRobot's translation. The file header (`src/voc_algorithm.py:3-5`) says it is ported from DFRobot's translation of Sensirion's C and verified constant-for-constant against the C; …
- HR174 (buildgen copies of src facts tied to source): Tension with singleton G8.009 (owner, 2026-09-18/24: `buildspec.py` and `definitions.py`'s `status`/`errcount` catalog stay hand-maintained); compatible if the hand tables are pinned by tests rather than generated.
- HR200 (Static imports only; frozen set is the closure): G5.006 records dynamic imports in `digital_twin/` and `tests/` scenario helpers; whether 'project-wide' (G8.017) covers test code is unresolved.

## Task 2 — owner-attribution coverage

`file:line | candidate IDs (cluster) | note` — "agent verification" marks a `confirmed directly` line with no owner attribution; "not a rule" marks history, motivation or incidental mentions.

| file:line | candidate IDs | note |
|---|---|---|
| .gitignore:38 | G4.009 | fact carried; agent verification ("confirmed directly"), not an owner attribution |
| BACKLOG.md:23 | G5.024 (HR155) | renumber-to-10+ on next substantial change; superseded by OR28.a (renumber in the audit) |
| BACKLOG.md:39 | G8.129 |  |
| BACKLOG.md:55 | G5.075 (HR084) | general-purpose FRAM API stays; also G3.017 |
| BACKLOG.md:59 | G5.060 |  |
| BACKLOG.md:82 | — | history/open item: one-off sweep (owner-requested 2026-09-15), not a standing rule |
| BACKLOG.md:94 | G5.076 G6.033 (HR073) | scratched tests needing a src/ change for the test alone |
| BACKLOG.md:100 | G3.048 | defect record; the resulting rule is the shadow rule |
| BACKLOG.md:129 | G3.056 |  |
| BACKLOG.md:168 | G5.034 G5.061 (HR149, HR189) | BACKLOG #4: no long-block coordination for write_config |
| BACKLOG.md:231 | — | agent verification ("confirmed directly"), not an owner attribution; not a rule |
| BACKLOG.md:326 | G4.087 | open owner decision (item 24 design fix), not a settled rule |
| BACKLOG.md:375 | G1.101 (HR119) |  |
| BACKLOG.md:381 | G4.087 | F18 is an open owner decision, not a settled rule |
| BACKLOG.md:389 | G5.069 | T4 is an open owner decision on the per-command hold; G5.069 carries the settled whole-block scope |
| BACKLOG.md:474 | G5.068 G4.017 (HR024) |  |
| BACKLOG.md:478 | G3.102 |  |
| BACKLOG.md:481 | G6.005 G9.051 (HR007) |  |
| BACKLOG.md:484 | G6.051 |  |
| BACKLOG.md:516 | G8.059 G9.035 (HR004) |  |
| BACKLOG.md:632 | — | agent verification ("confirmed directly"), not an owner attribution; not a rule |
| BACKLOG.md:805 | G1.001 | instance of the go-ahead rule (history), not a separate rule |
| BACKLOG.md:834 | — | open item: manual cross-device check owed to the owner; not a rule |
| BACKLOG.md:891 | G3.025 | partial: G3.025 carries the shared-scratch design; the decision to route get_bits/set_bits/get_register_struct through readfrom_mem_into is not stated by any candidate |
| CLAUDE.md:125 | G6.002 G9.033 G6.005 (HR006, HR007) |  |
| CLAUDE.md:129 | G6.004 (HR213) |  |
| CLAUDE.md:133 | G6.005 (HR007) |  |
| CLAUDE.md:170 | G9.054 G8.084 (HR008, HR095) |  |
| CLAUDE.md:190 | G5.088 G9.091 (HR182) |  |
| CLAUDE.md:222 | G3.030 G4.019 G6.024 G2.022 (HR143) |  |
| CLAUDE.md:238 | G2.044 |  |
| CLAUDE.md:250 | G1.004 G1.010 G2.014 G8.107 (HR183, HR186) |  |
| CLAUDE.md:284 | G1.001 |  |
| CLAUDE.md:417 | G9.020 G10.028 (HR077) |  |
| CLAUDE.md:433 | G9.020 (HR077) |  |
| CLAUDE.md:444 | G9.018 (HR011) |  |
| CLAUDE.md:461 | G9.019 |  |
| CLAUDE.md:488 | G8.082 G9.037 (HR128) |  |
| CLAUDE.md:524 | G8.089 (HR093) | agent verification ("confirmed directly"), not an owner attribution |
| CLAUDE.md:528 | G8.089 (HR093) | agent verification ("confirmed directly"), not an owner attribution |
| CLAUDE.md:550 | G8.133 (HR095) |  |
| CLAUDE.md:559 | G9.037 G2.058 (HR128) | "confirmed directly" here read as owner-confirmed by G9.037 |
| CLAUDE.md:566 | G8.052 G2.008 G4.060 (HR134) |  |
| CLAUDE.md:740 | G8.123 |  |
| CLAUDE.md:741 | G8.123 | continuation of :740 |
| CLAUDE.md:771 | G8.085 G1.108 G2.070 (HR058) |  |
| CLAUDE.md:823 | G2.069 (HR093) | agent verification ("confirmed directly"), not an owner attribution |
| CLAUDE.md:861 | G9.035 G8.059 (HR004) |  |
| CLAUDE.md:915 | — | not a rule (incidental mention of the owner's dev box) |
| CLAUDE.md:1042 | G9.035 (HR004) |  |
| CLAUDE.md:1043 | G8.131 G9.036 (HR005) |  |
| CLAUDE.md:1046 | G8.131 G9.036 (HR005) |  |
| HEAP_FRAGMENTATION_MEASUREMENTS.md:389 | G4.078 |  |
| README.md:364 | G1.001 |  |
| README.md:568 | G5.027 | agent verification ("confirmed directly"), not an owner attribution |
| README.md:698 | G6.006 G6.005 (HR006, HR007) |  |
| README.md:701 | — | uncovered: audit-plan lifecycle (see list below) |
| README.md:767 | G1.001 |  |
| SPECIFICATION.md:39 | G9.051 G6.005 (HR007) |  |
| SPECIFICATION.md:165 | G3.090 G5.095 (HR083) |  |
| SPECIFICATION.md:189 | G5.065 |  |
| SPECIFICATION.md:201 | G5.067 |  |
| SPECIFICATION.md:240 | G3.070 G9.062 (HR178) | AmbPres always sent; G3.070 records SPEC's `force=True` wording as drifted |
| SPECIFICATION.md:269 | G9.071 G6.052 G3.095 G3.078 G6.036 (HR048, HR056) |  |
| SPECIFICATION.md:355 | G3.040 |  |
| SPECIFICATION.md:361 | — | uncovered: WS2812 supply/level-shifter fact (see list below) |
| SPECIFICATION.md:730 | G8.052 (HR134) |  |
| SPECIFICATION.md:1095 | — | agent verification ("confirmed directly"), not an owner attribution; override mechanism fact (SPEC B.14), not an owner rule |
| SPECIFICATION.md:1841 | G5.028 G5.074 |  |
| SPECIFICATION.md:1914 | G5.024 (HR155) | same decision as BACKLOG.md:23; superseded by OR28.a |
| SPECIFICATION.md:1949 | G6.022 (HR012) | W11 outranks W10 (owner, 2026-09-18) inside the UART episode budget |
| SPECIFICATION.md:1976 | G5.054 (HR034) |  |
| SPECIFICATION.md:1994 | G5.032 (HR190) |  |
| SPECIFICATION.md:2006 | G5.033 (HR189) |  |
| SPECIFICATION.md:2042 | G5.069 |  |
| SPECIFICATION.md:2068 | G3.038 (HR030) | not a settled rule: quiesce mechanism flagged for a future owner decision |
| SPECIFICATION.md:2071 | G2.044 |  |
| SPECIFICATION.md:2075 | G2.044 |  |
| SPECIFICATION.md:2118 | G2.044 | iterate every real bus (TOML-driven per-bus coverage) |
| SPECIFICATION.md:2176 | G2.044 |  |
| SPECIFICATION.md:2658 | G5.002 G10.025 (HR067) | superseded in part by OR24.a (harmonise, not "no mass edit") |
| SPECIFICATION.md:3002 | G5.013 (HR121) | defensive-symmetry sentinel kept |
| SPECIFICATION.md:3060 | G8.052 G4.060 (HR134) |  |
| SPECIFICATION.md:3100 | G8.082 (HR128) |  |
| SPECIFICATION.md:3136 | G1.020 G8.064 (HR181) |  |
| SPECIFICATION.md:3197 | G1.044 G2.061 (HR108) |  |
| SPECIFICATION.md:3453 | G5.006 G8.017 (HR200) |  |
| SPECIFICATION.md:3755 | G5.068 (HR024) |  |
| SPECIFICATION.md:3808 | G4.082 |  |
| SPECIFICATION.md:4557 | G4.068 G6.075 G8.024 (HR146) |  |
| SPECIFICATION.md:4893 | G3.016 G4.085 G5.021 (HR144) | settled list: CRC per-byte yield and logger store setup first |
| SPECIFICATION.md:5069 | G7.041 (HR115) | agent verification ("confirmed directly"), not an owner attribution; carried as the twin sampler baseline rule |
| SPECIFICATION.md:5171 | G6.003 |  |
| SPECIFICATION.md:5301 | G1.058 (HR146) | bounded wait_until() for slot-release lag |
| SPECIFICATION.md:5355 | G6.004 (HR213) |  |
| SPECIFICATION.md:5502 | G6.007 |  |
| SPECIFICATION.md:5507 | G6.008 |  |
| SPECIFICATION.md:6366 | G8.001 (HR175) |  |
| SPECIFICATION.md:6606 | G3.054 G3.060 G3.051 G3.109 (HR036, HR086) | M.1.1 owner list (req 16, 17, 19, 20 carried individually) |
| SPECIFICATION.md:6737 | G3.052 |  |
| THIRD_PARTY_LICENSES.md:74 | — | not a rule (licence provenance research the owner prompted) |
| THIRD_PARTY_LICENSES.md:100 | G9.098 (HR165) | agent verification ("confirmed directly"), not an owner attribution |
| THIRD_PARTY_LICENSES.md:150 | — | not a rule (licence candidates the owner asked to check) |
| THIRD_PARTY_LICENSES.md:168 | — | not a rule (owner recollection, ruled out) |
| THIRD_PARTY_LICENSES.md:178 | — | not a rule (owner-flagged origin, checked) |
| THIRD_PARTY_LICENSES.md:195 | G9.097 (HR164) |  |
| THIRD_PARTY_LICENSES.md:197 | G9.097 (HR164) |  |
| UART_C_PORT_CHANGELOG.md:9 | G6.005 (HR007) |  |
| UART_C_PORT_CHANGELOG.md:15 | G6.005 (HR007) |  |
| UART_C_PORT_CHANGELOG.md:39 | G6.004 (HR213) |  |
| UART_C_PORT_CHANGELOG.md:64 | G3.005 G6.038 | framing-codec concept (owner decision, 2026-09-11) |
| dev_legacy/README.md:25 | — | agent verification ("confirmed directly"), not an owner attribution; not a rule |
| dev_legacy/README.md:33 | G9.049 G1.071 (HR163) | superseded: dev_legacy README as "authoritative source" is retired by OR32.a (3); the owner-verified wiring facts live on in G1.097/G1.098 |
| dev_legacy/README.md:49 | G1.097 G3.103 (HR166) |  |
| dev_legacy/README.md:57 | G1.098 G6.037 (HR014) |  |
| dev_legacy/README.md:660 | G1.019 (HR179) |  |
| digital_twin/README.md:479 | G5.065 |  |
| digital_twin/README.md:551 | G7.038 (HR106) | agent verification ("confirmed directly"), not an owner attribution |
| digital_twin/README.md:654 | G5.065 | agent verification ("confirmed directly"), not an owner attribution |
| digital_twin/README.md:786 | G7.022 (HR096) | agent verification ("confirmed directly"), not an owner attribution |
| js/templates.js:293 | G7.070 |  |
| js/templates.js:304 | G7.070 |  |
| pyproject.toml:165 | G5.087 | S104 bind-all accepted under the trusted-LAN threat model |
| scripts/_digital_twin_ci_suite.py:728 | G5.065 |  |
| scripts/_digital_twin_ci_suite.py:802 | G5.065 |  |
| scripts/build_frozen_html.sh:31 | G8.096 (HR153) | agent verification ("confirmed directly"), not an owner attribution |
| scripts/cross_browser_smoke.mjs:355 | — | agent verification ("confirmed directly"), not an owner attribution; not a rule |
| scripts/run_bench_soak_tests.sh:3 | G1.004 G8.091 (HR183) |  |
| src/asy_fram_driver.py:130 | G5.069 |  |
| src/asy_neopixel_driver.py:5 | G3.090 G5.095 (HR083) |  |
| tests/_coverage_runner.py:60 | G4.055 | agent verification ("confirmed directly"), not an owner attribution |
| tests/_digital_twin_construction_scenarios.py:165 | — | not a rule (motivation for a twin fault scenario, "owner decision 10" undefined in living docs) |
| tests/_webserver_concurrency_scenarios.py:217 | — | not a rule (test motivation: OpenHAB-style concurrent polling example) |
| tests/_webserver_concurrency_scenarios.py:482 | G6.075 (HR146) | exceeding the ceiling rejects only the new arrival; open connections never evicted |
| tests/_webserver_concurrency_scenarios.py:569 | G6.075 G2.063 (HR146) | partial: "OpenHAB plus open browser tabs filling the whole ceiling all succeed" is carried only as per-answer correctness at the ceiling |
| tests/neopixel.py:2 | G10.058 G10.080 (HR202) | agent verification ("confirmed directly"), not an owner attribution |
| tests/network.py:2 | G10.058 G2.032 (HR113, HR202) | agent verification ("confirmed directly"), not an owner attribution |
| tests/test_asy_fram_manager.py:886 | G5.067 |  |
| tests/test_asy_i2c_driver.py:803 | G4.023 | agent verification ("confirmed directly"), not an owner attribution |
| tests/test_asy_neopixel_driver.py:543 | G4.024 | agent verification ("confirmed directly"), not an owner attribution |
| tests/test_asy_notification_service.py:839 | G3.065 (HR012) |  |
| tests/test_asy_ntp_client.py:928 | G4.056 (HR096) | agent verification ("confirmed directly"), not an owner attribution |
| tests/test_asy_ntp_client.py:948 | G2.045 | agent verification ("confirmed directly"), not an owner attribution |
| tests/test_asy_ntp_client.py:2105 | G4.056 (HR096) | agent verification ("confirmed directly"), not an owner attribution |
| tests/test_asy_uart_driver.py:92 | G2.032 (HR113) | agent verification ("confirmed directly"), not an owner attribution |
| tests/test_asy_uart_driver.py:102 | G2.032 (HR113) | agent verification ("confirmed directly"), not an owner attribution |
| tests/test_asy_udp_socket.py:97 | G6.048 (HR197) | agent verification ("confirmed directly"), not an owner attribution |
| tests/test_asy_udp_socket.py:534 | G4.023 | agent verification ("confirmed directly"), not an owner attribution |
| tests/test_asy_udp_socket.py:1286 | G6.048 (HR197) | agent verification ("confirmed directly"), not an owner attribution |
| tests/test_asy_udp_socket.py:1451 | — | agent verification ("confirmed directly"), not an owner attribution; not a rule |
| tests/test_asy_udp_socket.py:1475 | G6.048 (HR197) | agent verification ("confirmed directly"), not an owner attribution |
| tests/test_asy_udp_socket.py:1564 | G6.048 (HR197) | agent verification ("confirmed directly"), not an owner attribution |
| tests/test_asy_udp_socket.py:1642 | G6.048 (HR197) | agent verification ("confirmed directly"), not an owner attribution |
| tests/test_asy_webserver_service.py:890 | G4.029 (HR112) | agent verification ("confirmed directly"), not an owner attribution |
| tests/test_asy_webserver_service.py:2296 | G6.071 (HR195) | agent verification ("confirmed directly"), not an owner attribution |
| tests/test_asy_webserver_service.py:2592 | G4.070 G4.074 (HR114, HR147) | owner-chosen gc.threshold(32768) |
| tests/test_asy_webserver_service.py:2627 | G4.070 (HR114) | agent verification ("confirmed directly"), not an owner attribution |
| tests/test_asy_webserver_service.py:2637 | G4.070 G4.074 (HR114, HR147) |  |
| tests/test_asy_webserver_service.py:2733 | G2.029 G4.067 (HR145) | test motivation; /measurements and /sensors as the owner-named streaming candidates |
| tests/test_asy_webserver_service.py:2758 | G4.070 (HR114) | agent verification ("confirmed directly"), not an owner attribution |
| tests/test_asy_webserver_service.py:2768 | G4.070 G4.074 (HR114, HR147) |  |
| tests/test_asy_wifi_service.py:16 | G2.039 G4.035 (HR137, HR171) | agent verification ("confirmed directly"), not an owner attribution |
| tests/test_asy_wifi_service.py:528 | G6.056 | agent verification ("confirmed directly"), not an owner attribution |
| tests/test_asy_wifi_service.py:539 | G6.056 | agent verification ("confirmed directly"), not an owner attribution |
| tests/test_asy_wifi_service.py:1902 | G4.033 | agent verification ("confirmed directly"), not an owner attribution |
| tests/test_asy_wifi_service.py:2299 | G2.017 (HR130) | agent verification ("confirmed directly"), not an owner attribution |
| tests/test_asy_wifi_service.py:2361 | G7.022 (HR096) | agent verification ("confirmed directly"), not an owner attribution |
| tests/test_base_classes.py:231 | G4.063 | agent verification ("confirmed directly"), not an owner attribution |
| tests/test_base_classes.py:239 | G4.063 | agent verification ("confirmed directly"), not an owner attribution |
| tests/test_digital_twin_sensortask_integration.py:421 | — | uncovered: owner decision 7 (see list below) |
| tests/test_fram_integration.py:300 | G5.065 |  |
| tests/test_print_log.py:307 | G4.063 | agent verification ("confirmed directly"), not an owner attribution |
| tests/test_print_log.py:541 | G4.025 | agent verification ("confirmed directly"), not an owner attribution |
| tests/test_uart_comm_hazard.py:48 | G6.030 |  |
| tests_hardware/README.md:11 | G1.001 |  |
| tests_hardware/README.md:32 | G8.066 (HR208) | agent verification ("confirmed directly"), not an owner attribution |
| tests_hardware/README.md:526 | — | agent verification ("confirmed directly"), not an owner attribution; not a rule |
| tests_hardware/README.md:575 | G1.052 | agent verification ("confirmed directly"), not an owner attribution |
| tests_hardware/README.md:626 | G6.053 (HR054) | superseded: the reachability question was settled by the owner (655e4f9); README text drifted |
| tests_hardware/README.md:630 | G6.053 (HR054) | agent verification ("confirmed directly"), not an owner attribution |
| tests_hardware/README.md:637 | G6.053 (HR054) | superseded: still framed as open; settled in CLAUDE.md |
| tests_hardware/README.md:757 | G1.045 | agent verification ("confirmed directly"), not an owner attribution; G1.045 shows the claim is wrong (SCD30 writes NVM from `_set_dict_cfg`) |
| tests_hardware/README.md:853 | — | agent verification ("confirmed directly"), not an owner attribution; not a rule |
| tests_hardware/README.md:862 | — | agent verification ("confirmed directly"), not an owner attribution; not a rule |
| tests_hardware/README.md:868 | G1.053 G5.029 (HR013) | agent verification ("confirmed directly"), not an owner attribution |
| tests_hardware/README.md:1085 | G1.044 G2.044 (HR108) |  |
| tests_hardware/README.md:1188 | — | history: heading of a one-off owner-requested sweep, not a standing rule |
| tests_hardware/README.md:1252 | — | not a rule (disclosure note) |
| tests_hardware/README.md:1268 | G6.033 G5.076 (HR073) |  |
| tests_hardware/README.md:1291 | G6.033 G5.076 (HR073) |  |
| tests_hardware/README.md:1311 | G1.004 G1.007 (HR183) |  |
| tests_hardware/README.md:1325 | G1.005 |  |
| tests_hardware/bench/test_end_to_end_timing.py:121 | G1.100 |  |
| tests_hardware/bench/test_network_resilience.py:632 | G6.075 (HR146) | agent verification ("confirmed directly"), not an owner attribution |
| tests_hardware/bench/test_network_resilience.py:690 | G6.075 G5.029 (HR013, HR146) | agent verification ("confirmed directly"), not an owner attribution |
| tests_hardware/bench/test_network_resilience.py:710 | G5.029 (HR013) | agent verification ("confirmed directly"), not an owner attribution |
| tests_hardware/bench/test_network_resilience.py:742 | G5.029 (HR013) | agent verification ("confirmed directly"), not an owner attribution |
| tests_hardware/device_scripts/fram_error_log_reset_race_verify.py:18 | G5.065 |  |
| tests_hardware/flash/test_fram_storage.py:59 | G5.065 |  |
| tests_hardware/manual/manual_wifi.py:47 | — | not a rule (manual step records an observation for the owner) |
| tests_hardware/soak_tiers.py:3 | — | agent verification ("confirmed directly"), not an owner attribution; not a rule |
| tests_js/mock-server-put-matrix.test.js:20 | G7.057 (HR161) | superseded: OR43.a (2) requires mock fixtures to carry exactly the real device's fields |
| tests_js/templates.test.js:400 | G7.070 |  |
| tests_js/vitest-commands.d.ts:21 | — | agent verification ("confirmed directly"), not an owner attribution; not a rule |
| tests_scripts/test_buildgen_validate.py:1729 | G8.024 (HR146) |  |
| tests_scripts/test_digital_twin_generated_boot.py:45 | G7.043 | agent verification ("confirmed directly"), not an owner attribution |

Tally: 129 owner-attributed lines carried by candidates (some superseded or open, as noted); 62 agent-verification lines (51 of them still map to a candidate carrying the fact); 12 not a rule or open item; 3 uncovered; 2 more are carried only partly.

### Owner-attributed statements no candidate carries

- **README.md:701 — audit-plan lifecycle.** `PROJECT_AUDIT_PLAN.md` is planning only; its execution is blocked until the owner's explicit go-ahead, and the file is deleted once the audit closes and its outcomes are migrated. In force at HEAD: the audit is in consolidation with execution still blocked (this task's own brief).
- **SPECIFICATION.md:361 — WS2812 supply and data level.** The boards carry one RGB NeoPixel supplied from USB 5 V behind a level shifter, so the data-line voltage levels are settled (owner, 2026-09-25); WS2812 vs WS2812B stays unconfirmed. In force (hardware fact, no candidate or cluster records it).
- **tests/test_digital_twin_sensortask_integration.py:421 — "owner decision 7".** Watchdog escalation is proven both as an automated assertion (this test) and as a manually observable run (`digital_twin/run_generic_integration.py`). In force at HEAD (the test exists); the label "decision 7" is defined in no living document, a G9.002 (HR076) drift.

Carried only partly:
- **BACKLOG.md:891** — `asy_i2c_driver.py`'s `get_bits`/`set_bits`/`get_register_struct` read through `readfrom_mem_into()` (owner decision, 2026-09-18, done). G3.025 carries the shared-scratch safety rule, not the routing decision itself. In force.
- **tests/_webserver_concurrency_scenarios.py:569** — the owner's named case (an OpenHAB instance polling two endpoints plus open website tabs, filling the whole ceiling, all succeeding cleanly) appears only as per-answer correctness at the ceiling (G6.075, G2.063, HR146). In force (the scenario runs).

Owner-attributed but open, not rules: BACKLOG.md:326 and :381 (F18, item 24 `ResetErrors` design fix; see G4.087), BACKLOG.md:389 (T4, FRAM per-command hold), BACKLOG.md:834 (manual cross-device spot check), SPECIFICATION.md:2068 (bus-wide quiesce mechanism).

Superseded owner statements still in the tree (carried by candidates that record the newer rule): SPECIFICATION.md:1914/BACKLOG.md:23 (renumber on next change → OR28.a), SPECIFICATION.md:2658 ("not mass-edited" → OR24.a), dev_legacy/README.md:33 ("authoritative source" → OR32.a (3)), tests_hardware/README.md:626-637 (reachability probe "open" → settled, 655e4f9), tests_js/mock-server-put-matrix.test.js:20 (dev-unique placeholder groups → OR43.a (2)).
