# Project audit — plan and topic catalog

**Status: PLANNING. Audit execution is BLOCKED until the project owner gives an explicit go-ahead in
the conversation that starts it.** Nothing in this file authorizes any audit work: every topic, seed
observation and question below is a *recorded item to cover later*, never an implicit start. Until
the owner declares the planning phase finished, the only permitted work on this file is extending,
correcting and validating the list itself.

**Temporary.** Like every other plan/queue doc here, this file is deleted once the audit closes. Its
permanent outcomes (fixed code, settled decisions, new rules) migrate into `SPECIFICATION.md`,
`CLAUDE.md`, `BACKLOG.md` or `REAL_HARDWARE_TEST_QUEUE.md` first. The retired `src/` audit's
`AUDIT_PLAN.md` (closed 2026-08-10, see README "Further reading") is the precedent for this file's
shape; this one is broader (whole project, not only `src/`) and deeper (down to function internals,
across every tier). The ID prefixes below are chosen not to collide with `SPECIFICATION.md` Part IDs
(`A.1`…`M.1.6`), `REAL_HARDWARE_TEST_QUEUE.md` row IDs (`R1`, `F17`, …) or the undefined `WP1`-`WP8`
labels already in the tree.

---

## 0. How to read this file

- **Areas** (section 5) partition the whole repository into audit units, each with a mnemonic code
  (`CORE`, `NET`, `WEB`, …). Every git-tracked file belongs to exactly one area or to the explicit
  out-of-scope list (section 2.2); section 5.0 is that mapping.
- **Topics** (`<AREA>.T<nn>`) are the checklist: questions a deep audit of that area must answer.
- **Seed observations** (`<AREA>.S<nn>`) are concrete, file:line-anchored things the planning survey
  noticed. **Every seed is UNVERIFIED** — recorded by a read-only survey agent, not reproduced, not
  confirmed, not triaged. Some will turn out wrong. Verifying them *is* audit work and is blocked like
  the rest. A seed tagged `[x2]`/`[x3]` was reported independently by two/three survey agents
  (a convergence signal, not a verification).
- **Cross-cutting lenses** (section 4.2) apply to every area on top of its own topics.
- Line numbers are as of commit `0615eba` (planning baseline) and will drift.

---

## 1. Goals and definition of done

### 1.1 Goals

1. **Broad**: every tracked file outside the out-of-scope list is looked at by an auditor with a
   stated lens — code, tests, tooling, CI, website, docs, config.
2. **Deep**: `src/`, `buildgen/`, `toolchain/`, `scripts/`, `js/` and the test infrastructure are read
   line by line, down to function internals, not grepped; formulas and protocol facts are checked
   against datasheets and the pinned MicroPython 1.29.0 source, never memory (CLAUDE.md, Part D.1/D.9).
3. **Converged**: each area's findings stabilise under independent re-audit (section 4.4), and
   cross-area contradictions are arbitrated rather than left as two reports.
4. **Actionable**: every finding ends as exactly one of: fixed-and-verified, owner decision recorded,
   moved to `BACKLOG.md`/`REAL_HARDWARE_TEST_QUEUE.md` with enough context to act on, or rejected
   with the reason.
5. **Feature parity preserved**: the refactor keeps the deployed units' top-level features (CLAUDE.md
   working agreement); every behaviour change found is either documented-as-deliberate or raised.

### 1.2 Definition of done (whole audit)

- [ ] Every area in section 5 has its topics answered, its seeds triaged, and its quality measure met.
- [ ] Every finding in the register (section 4.5) has a terminal status.
- [ ] Every cross-cutting lens (section 4.2) has been applied to every in-scope area, recorded per
      area, not assumed.
- [ ] `scripts/lint.sh`, `scripts/typecheck.sh`, `scripts/test.sh` (both `gc.threshold(-1)` and
      `GC_THRESHOLD=32768`), `scripts/test.sh --coverage`, `scripts/run_digital_twin_ci.sh` for all 6
      devices, the npm tier and `scripts/build_firmware.py` for all 6 devices are green with zero
      `MemoryError`/`memory allocation failed`, and no test was deleted or weakened to get there.
- [ ] Coverage recorded before and after; any drop explained.
- [ ] Every real-hardware item the audit produced is in `REAL_HARDWARE_TEST_QUEUE.md` (or run, if the
      owner granted a bench go-ahead inside the audit).
- [ ] Every permanent fact this file holds has migrated; the owner agrees the audit is finished; this
      file is deleted.

---

## 2. Scope

### 2.1 In scope

All of: `src/`, `ext/` (behaviour relied upon only — see 2.2), `buildgen/`, `devices/`, `toolchain/`,
`scripts/`, `.github/`, root config (`pyproject.toml`, `uv.lock`, `package.json`, `package-lock.json`,
`eslint.config.js`, `tsconfig*.json`, `vitest.config.js`, `.htmlvalidate.json`, `.stylelintrc.json`,
`host_typecheck.ini`, `.gitignore`, `.nvmrc`), `js/`, `html/`, `mockdata/`, `tests/`, `tests_js/`,
`tests_scripts/`, `tests_hardware/` (desk review; execution only with a go-ahead), `digital_twin/`,
and every markdown doc (`*.md` at the root, `digital_twin/README.md`, `tests_hardware/README.md`,
`dev_legacy/README.md`), plus `update_and_install.txt`, `LICENSE`, `THIRD_PARTY_LICENSES.md`.

### 2.2 Out of scope, or in scope only as a reference

| Path | Treatment | Authority |
|---|---|---|
| `arduino/` | Out of scope entirely: no audit, no reconciliation | BACKLOG (owner, 2026-09-24) |
| `python/`, `modules/`, `build-*.sh`, `html_raw/` | **Read-only reference** for the parity area (`PAR`): read to establish deployed behaviour, never a to-do | CLAUDE.md legacy rule |
| `ext/microdot.py`, `ext/freezefs/` | Never edited or restyled. Audited only for *what this project relies on* from it, and for whether our wrappers cover its gaps | CLAUDE.md vendoring rule |
| `datasheets/` | Reference material. Gaps (missing datasheets) are recorded, not "fixed" by web memory | CLAUDE.md / Part A.6 |
| `dev_legacy/` session logs and snapshot | Reference only; its `README.md` is in scope as a doc | Part A.1 |
| `modules/_boot.py`'s `import sensortask.py` | Never changed without real-hardware testing | CLAUDE.md hard rule |

### 2.3 Standing constraints the audit must respect (from CLAUDE.md, restated only as pointers)

- Flag, don't silently fix, any behaviour/formula discrepancy (Part D.1) and any cross-file
  consistency discrepancy found by a `src/` scan (CLAUDE.md "bird's-eye-view scan").
- Real hardware: owner go-ahead in that session's conversation; wear gates; FRAM-forensics-first;
  dead-man's switch for host network changes; `br0` MAC pinning (CLAUDE.md hard rules).
- Settled decisions are not re-opened (BACKLOG "SETTLED" entries, Part A.4 "confirmed intentional"
  list, the wedged-I2C/WiFi backstop rules). A seed that touches one is triaged as "settled — no
  action" unless it shows the settled premise itself is factually wrong, in which case it is raised,
  not acted on.
- Memory-safety discipline (design for zero `MemoryError`, no `gc.collect()` propping, both GC stages).
- Comment cap (3 lines) and docs-hold-current-state for anything the audit writes.
- Step-session workflow (CLAUDE.md) for any fix unit of work: scope → questions → tests first →
  implementation → coverage → stop and report.

---

## 3. Open decisions for the owner (needed before or at go-ahead)

These shape *how* the audit runs. None blocks further planning; all block execution.

| ID | Question | Options | Planner's recommendation |
|---|---|---|---|
| PQ1 | Output mode: findings-only first, or fix as we go? | (a) Two phases: complete register first, then owner-prioritised fix units; (b) fix-per-area immediately after that area converges; (c) findings only, fixes as separate future work | (a) — convergence across areas first avoids fixing one area against a contract another area's audit later overturns |
| PQ2 | Branch/PR shape for fixes | (a) all on this branch (it merges to `main`); (b) one branch + PR per fix unit, based on this branch | (b) for fixes, keeping the register on this branch |
| PQ3 | Severity scale and sign-off threshold | e.g. S1 safety/data-loss/bricking, S2 functional defect, S3 robustness/latent, S4 consistency/doc/style | Owner sign-off before any fix that changes observable behaviour or a wire/storage format, regardless of severity |
| PQ4 | Real hardware inside the audit? | (a) none — every silicon item goes to the queue; (b) one or more gated bench sittings within the audit | (a) by default; (b) only for S1 items needing silicon evidence |
| PQ5 | Threat model for the security area (`SEC`) | (a) trusted home LAN, LAN peers are benign; (b) LAN peers untrusted (guest Wi-Fi, IoT neighbours, DNS rebinding via a browser); (c) hotspot-mode attacker in radio range | Needs an explicit answer: it decides whether e.g. unauthenticated `bootloader` is a defect or an accepted property |
| PQ6 | Documentation restructuring scope (`DOC`) | (a) correctness only (stale/contradictory/dangling); (b) also placement (e.g. `I.6` inside Part J, CLAUDE.md size/auto-load budget, history pruning in `tests_hardware/README.md`) | (b), but as its own late unit so it doesn't churn line refs mid-audit |
| PQ7 | Merge strategy for this branch into `main` | merge commit vs squash | Merge commit: ~77 "archive §" citations point at commit `12640c2`, which today is reachable only from this branch (seed `DOC.S04`); a squash + branch delete would orphan them. Alternatively tag it |
| PQ8 | Comment-cap scope extension | Does the 3-line cap apply to `tsconfig*.json`, `.gitignore`, `html/index.html` inline script, and to 400-700-character one-line docstrings? | Owner call (seeds `WEB.S19`, `CI.S10`, `TEST.S22`) |
| PQ9 | Parallelism budget | How many concurrent agents per wave; token budget | Owner granted "as many as useful, with care" (2026-09-25); planner proposes waves of ≤ 8 auditors + verifiers |
| PQ10 | Baseline environment | May the planning phase already build the toolchain/Unix port in the sandbox (no audit, just the environment), so execution starts on a measured baseline? | Yes — it's prep, not audit, but it's the owner's call since "blocked" was stated broadly |
| PQ11 | Legacy→refactor reflash campaign | Is a field reflash planned within the horizon, making the migration topics (`PAR.T06`, `PAR.T07`) S1 rather than S3? | Owner input |

---

## 4. Method

### 4.1 Execution order (proposed, after go-ahead)

0. **ENV** — build the toolchain, run every tier once, record the baseline (counts, timings, coverage,
   warnings). Nothing is audited against an unmeasured tree.
1. **Wave 1 — foundations, in parallel**: `XCUT` (system contracts), `CORE`, `ALGO`, `BUS`, `PLAT`.
   Their outputs (error-code catalogue, lock map, timer map, FRAM layout, MicroPython facts) are inputs
   for everything else.
2. **Wave 2 — subsystems, in parallel**: `SENS`, `STOR`, `UART`, `NET`, `REST`, `LED`, `GEN`, `TOOL`.
3. **Wave 3 — consumers and verification tiers**: `WEB`, `TEST`, `TWIN`, `HW`, `SCR`, `CI`.
4. **Wave 4 — cross-cutting synthesis**: `SEC`, `MEM`, `PERF`, `PAR`, then `DOC` and `LIC` last
   (they absorb every other area's doc findings).
5. **Global convergence pass** over the register (section 4.4), then owner review.

### 4.2 Cross-cutting lenses (apply to every in-scope area)

| Lens | Question every area answers |
|---|---|
| L-CORR | Correct against the authoritative source (datasheet, RFC, MicroPython 1.29.0 source, Microdot v2.6.2 source, browser spec) — verified, cited, not recalled |
| L-EXC | Exception net complete: nothing raises out of a never-raise contract; every raise has a catching caller (Part D.2) |
| L-CONC | Every lock, shared state, await point and interleaving; lock-hold spans containing sleeps or I/O; lock order |
| L-BLOCK | Nothing blocks the loop beyond its budget (Part D.5, F.3, F.5.8) |
| L-TIME | Timers (soft-callback drop, ONE_SHOT vs PERIODIC, alarm pool), ticks wraparound, timeouts vs the 8388 ms watchdog |
| L-MEM | Allocation bounded and not client-controllable; churn on hot paths; long-lived placement (Part I) |
| L-LIFE | Every resource (socket, timer, task, file, lock, buffer, FRAM chunk) released on every path incl. cancel/restart |
| L-STATE | State machines complete: every state × event, including task restart, reboot, power loss, and cancellation at every `await` |
| L-DIAG | Every failure mode leaves persisted, attributable evidence (errcount/FRAM entry, reset cause) — or is recorded as knowingly silent |
| L-TGT | The property holds in target semantics, not only on the 64-bit double-precision Unix port or the twin (float32, 31-bit small ints, soft-callback drop, IRQ-off windows, blocking UART reads) |
| L-WEAR | Flash/NVM/FRAM write frequency and who can trigger it (REST, loops, tests) |
| L-SEC | Input from the network/LAN/radio/user treated as hostile per the PQ5 threat model |
| L-API | D.10 consistency within and across files; naming; return conventions; Part G reuse |
| L-DEAD | Dead code, unused parameters, test-only production API, unreachable branches |
| L-TEST | Tests bite (fail when the property breaks), not vacuous, not tautological; tiered per CLAUDE.md |
| L-DOC | Code, comments and docs agree; comment cap; no dangling citations |
| L-PAR | Behaviour equals legacy or the change is documented as deliberate |

### 4.3 Techniques catalogue

- **Line-by-line reading** of every in-scope source file (full reads, never grep-only), with the
  callers and callees of each function read alongside (Part D.0).
- **Source verification**: clone MicroPython `v1.29.0` (and Microdot `v2.6.2` for comparison) into the
  scratchpad; every runtime claim cites a file and line there.
- **Datasheet verification** from `datasheets/` (text already extracted during planning to the session
  scratchpad; re-extract in a new session).
- **Differential testing**: mock tier vs twin tier; Python VOC port vs Sensirion's C reference (if the
  owner can supply it); float32 vs double arithmetic for every formula that runs on rp2.
- **Mutation / clamp-removal sweeps** (the technique already used for UART, BACKLOG): remove or invert
  a guard, shadow the mutated copy ahead of `src/` on `MICROPYPATH`, require a named test to fail.
- **Fake-mutation sweeps**: remove one fidelity rule from a chip fake and check some test notices.
- **Fuzzing**: `buildgen.build_model()` with mis-shaped TOML (expect only `BuildError`); REST request
  lines/headers/bodies; DNS/NTP reply parsers; UART frames; stored config JSON; FRAM chunk images.
- **Interleaving exploration**: scripted asyncio schedules for every lock-protected sequence found by
  `L-CONC`.
- **Budget arithmetic**: worst-case watchdog-feed gap, lock-hold per bus, request ceiling, FRAM layout
  vs chip size, UDP PCB count, alarm-pool count — computed from code, cross-checked by measurement.
- **Static sweeps** (grep/AST scripts kept in the scratchpad): error-code catalogue, timer inventory,
  lock inventory, `create_task` inventory, `repeat=` usage, cross-reference resolver for docs.
- **Representation-faithful scratch Unix port**: a third, scratch-only build with 32-bit objects and
  single-precision floats (if buildable) for ALGO/SENS arithmetic parity and allocation counts — not a
  toolchain change.
- **Cancel-at-each-await sweep**: for each multi-step coroutine, inject `CancelledError` at the k-th
  await for every k and assert the post-state invariants (`XCUT.T19`).
- **Loop-lag sentinel**: a task measuring how late `sleep_ms()` wakes, under combined worst-case load
  (`PERF.T09`).
- **Crash-point enumeration** on a twin FRAM image: power loss after every SPI transaction k
  (`STOR.T12`).
- **Clock-jump injection** in the twin: RTC forwards/backwards, `NTP_Offset_S` changes (`NET.T11`).
- **Third-party HTTP client matrix**: curl with `Expect: 100-continue`, chunked bodies, browser
  keep-alive (`REST.T12`).
- **Rogue DNS/NTP responder at the twin tier**, not only on the bench (`SEC.T11`).
- **Datasheet golden vectors**: e.g. SGP40 Table 10 ticks (25 °C → 0x6666, 50 % → 0x8000), SCD30's CRC
  example, default command CRCs.
- **IRQ-line fault simulation**: floating, stuck-low and bouncing SCD30 RDY / ISL29125 INT lines.
- **Execution** only in isolated git worktrees or scratch directories (section 4.6).

### 4.4 Multi-agent orchestration and convergence (owner's go, 2026-09-25)

- **Roles**: *auditor* agents (read-only on the repo; one area or sub-unit each, one lens set);
  *verifier* agents (adversarial: try to disprove one finding, by execution where possible);
  the *arbiter* (the main session: dedups, resolves contradictions between agents, assigns
  severity/status, is the **only writer** of this file and of the findings register).
- **Per-unit pipeline**: auditor A (full deep read) → independent auditor B with a different lens
  emphasis, not shown A's output → arbiter merges → each candidate finding goes to a verifier →
  confirmed/plausible/rejected.
- **Convergence criterion** for an area: a fresh auditor pass with the full current register in hand
  produces no new finding of severity S1-S2 and no new S3 in more than one topic. Two consecutive
  passes that only restate known findings close the area.
- **Contradiction handling**: when two agents disagree on a fact, the arbiter checks the source
  directly (planning example: one survey said the hotspot timeout is 5 min, another 8 min — the class
  default is 5 but every `devices/*.toml` sets `hotspot_time_min = 8`; both were right about different
  things).
- **Non-interference rules**:
  - Auditors and verifiers never write inside the checkout. They use the scratchpad or their own
    `isolation: "worktree"`.
  - Two agents that execute tests never share a worktree: `scripts/test.sh`, `npm test`,
    `build_website.sh` and the twin CI suite all write shared outputs (`frozen_modules/`,
    `build/generated_src/`, `digital_twin/*_state.json`, `tests/_tmp`, rp2/mpy-cross build dirs) and
    bind real ports (CLAUDE.md: two port-binding suites must never run at once).
  - The toolchain directory (`$PICO_TOOLCHAIN_DIR`) is shared read-only after ENV builds it; any agent
    that needs a rebuild gets its own toolchain dir.
  - Fix work (if PQ1 allows): one writer per file at a time, one fix unit per branch/worktree.

### 4.5 Findings register

Created at execution start (not now) as a section of this file or a sibling file (owner's choice).
One row per finding:

`ID` (`F-<AREA>-<nnn>`) · title · file:line · lens · severity (PQ3) · class (defect / latent /
doc-drift / test-gap / decision-needed / settled-no-action) · evidence (repro, source citation) ·
verifier verdict · status (open / confirmed / rejected / decided / fixed / moved-to-backlog /
moved-to-queue) · link to fix commit or decision.

Seeds (`<AREA>.S<nn>`) become findings only after verification; a seed rejected by a verifier is
recorded as rejected with the reason, so it is not rediscovered.

### 4.6 Execution environment (area `ENV`)

- [ ] **ENV.T01** Build the toolchain (`uv run toolchain/setup_toolchain.py`), Unix port both
      variants; note sandbox egress limits (CLAUDE.md chroot notes: `astral.sh`, `deb.debian.org`
      were blocked in earlier sessions).
- [ ] **ENV.T02** Baseline run of every tier listed in 1.2; record counts (files, tests, pass/fail),
      wall clock, coverage per `src/` file, lint/typecheck finding counts (expected 0), npm results.
- [ ] **ENV.T03** Clone MicroPython `v1.29.0` source (and `extmod/asyncio`, `ports/rp2`, `lib/lwip`,
      `lib/cyw43-driver`) plus Microdot `v2.6.2` into the scratchpad as the reference corpus.
- [ ] **ENV.T04** Re-extract datasheet text; list missing datasheets (seed `SENS.S20`).
- [ ] **ENV.T05** Decide the worktree/port/toolchain-dir allocation per parallel agent (4.4).
- [ ] **ENV.T06** Measure `disallow_any_explicit` counts per pass (BACKLOG's figures are dated
      2026-09-11) as a baseline only — enabling it stays a separate owner-deferred session.

---

## 5. Areas, topics and seed observations

### 5.0 Area index and file mapping

| Code | Area | Files (tracked) |
|---|---|---|
| XCUT | System-wide contracts (boot, supervision, watchdog, timers, concurrency, errors, persistence layout) | cross-file; anchored in `src/system_service.py`, generated `sensortask_<device>.py`, Part A.7/C.7-C.9/C.13-C.14 |
| CORE | Core runtime modules | `src/system_service.py`, `base_classes.py`, `config_manager.py`, `print_log.py`, `api_response.py` |
| ALGO | Pure algorithms and codecs | `src/math_helpers.py`, `voc_algorithm.py`, `crc_checks.py`, `framing_codecs.py` |
| BUS | Bus layer | `src/asy_i2c_driver.py`, `asy_spi_driver.py`, `asy_uart_driver.py` |
| SENS | Sensor drivers | `src/asy_scd30_driver.py`, `asy_sgp40_driver.py`, `asy_bmp3xx_driver.py`, `asy_isl29125_driver.py` |
| STOR | FRAM storage | `src/asy_fram_driver.py`, `asy_fram_manager.py` |
| UART | UART protocol | `src/asy_uart_comm.py`, `asy_uart_link_driver.py`, `UART_C_PORT_CHANGELOG.md`, Part J |
| NET | Networking | `src/asy_wifi_service.py`, `asy_ntp_client.py`, `asy_dns_client.py`, `asy_udp_socket.py`, `captive_dns.py`, `LICENSE-captive_dns` |
| REST | Web server and HTTP surface | `src/asy_webserver_service.py`, relied-upon behaviour of `ext/microdot.py` |
| LED | Notification and LED | `src/asy_neopixel_driver.py`, `asy_notification_service.py` |
| GEN | Build generator and device definitions | `buildgen/*`, `devices/*.toml` |
| TOOL | Toolchain installer and build overrides | `toolchain/*` |
| SCR | Scripts and test orchestration | `scripts/*`, `host_typecheck.ini`, `digital_twin/typecheck.ini` |
| CI | CI, dependency pins, supply chain | `.github/**`, `pyproject.toml`, `uv.lock`, `package.json`, `package-lock.json`, `.nvmrc`, `.gitignore`, `eslint.config.js`, `tsconfig*.json`, `vitest.config.js`, `.htmlvalidate.json`, `.stylelintrc.json` |
| WEB | Website | `js/*`, `html/*`, `mockdata/*`, `ext/freezefs/` (reliance only) |
| TEST | Software test tiers | `tests/*`, `tests_scripts/*`, `tests_js/*` |
| TWIN | Digital twin | `digital_twin/*` |
| HW | Real-hardware tier (desk review; execution gated) | `tests_hardware/**`, `REAL_HARDWARE_TEST_QUEUE.md`, `HARDWARE_TEST_HANDOVER.md`, `HEAP_FRAGMENTATION_MEASUREMENTS.md`, `dev_legacy/README.md` |
| SEC | Security threat model | cross-cutting |
| MEM | Memory safety | cross-cutting, Part I |
| PERF | Timing and capacity budgets | cross-cutting |
| PLAT | MicroPython/RP2040 platform facts | Part F, `toolchain/versions.toml` pin |
| PAR | Legacy parity and field migration | refactor vs `python/`, `modules/`, `html_raw/` |
| DOC | Documentation set | every `*.md`, `update_and_install.txt` |
| LIC | Licensing and attribution | `LICENSE`, `THIRD_PARTY_LICENSES.md`, `src/LICENSE-captive_dns`, `ext/LICENSE-microdot`, attribution headers |
| ENV | Audit execution environment | section 4.6 |

Out of scope/reference only: see 2.2. Every tracked file not listed above must be mapped here before
the plan is declared complete (validation step V1, section 6).

---

### 5.1 XCUT — System-wide contracts

**Goal**: establish, from code, the device's real runtime contracts — boot order, supervision,
watchdog budget, timers, tasks, locks, error codes, persistence layout — as the reference every other
area audits against.
**References**: Parts A.4, A.7, C.7-C.9, C.13, C.14, G, I.4; generated `build/generated_src/
sensortask_<device>.py` for all 6 devices.

Topics:
- [ ] **XCUT.T01** Boot sequence per device, from `WDT(timeout=8000)` creation through the setup batch
      (`fram → sysfunct → conn → ntp → needs_setup…`) to the first supervisor feed: every feed point,
      the worst-case gap between feeds, and what happens when any `setup()` fails (legacy reboot-looped;
      the generated `build_system()` ignores the result — seed `PAR.S12`).
- [ ] **XCUT.T02** Task supervisor semantics: is restarting via the same captured starter safe for
      *every* task (state reset, double registration, leaked timers)? Undetected hung-but-alive tasks
      (flag never set, lock never released)? Decay/score arithmetic; wrnno `n+1` stability across
      devices and firmware versions; restart backoff.
- [ ] **XCUT.T03** Watchdog budget end to end: all feed sites, worst-case scan with *k* simultaneous
      task deaths each persisting to FRAM (~305 ms of *yielding* time per chunk,
      SPECIFICATION.md ~1854 — distinct from the ~21 ms *non-yielding* bus hold in `PERF.T04`), commanded reset vs WDT reset
      (FRAM paused vs not), and the absence of any recorded `machine.reset_cause()`.
- [ ] **XCUT.T04** Timer inventory per device: every `machine.Timer`, ONE_SHOT vs PERIODIC, what a
      dropped soft callback costs (F.1), the rp2 alarm-pool limit vs simultaneous timers, every ENOMEM
      fallback and whether its failure is persisted or print-only.
- [ ] **XCUT.T05** Task inventory: every `create_task`, supervised or not (config flush, captive DNS,
      hotspot LED flash, per-connection HTTP tasks), lifetime, cancel path, exception visibility.
- [ ] **XCUT.T06** Lock map: every `asyncio.Lock`/`ThreadSafeFlag`/`Lockable`, holders, hold spans
      containing `sleep`/network/bus I/O, lock ordering (deadlock freedom), non-reentrancy hazards
      (seed `STOR.S02`).
- [ ] **XCUT.T07** Error-code catalogue: every `errno`/`wrnno` per module vs Part C.7.1; reserved
      ranges; dynamic codes; `repeat=` usage vs the per-episode rule; persisted vs print-only;
      whether client-input errors belong in the fault history.
- [ ] **XCUT.T08** Logger lifecycle: every FRAM-backed logger's `setup()` site; entries logged before
      `setup()`; `reset()` racing `setup()`; `set_level_setters` coverage; debug-level precedence.
- [ ] **XCUT.T09** FRAM layout per device: deterministic chunk order, total bytes vs chip size (8 KB
      on field devices, 256 KB on `dev`), what a firmware change that adds/reorders a chunk does to
      existing data, first boot on a chip written by another layout (legacy, other firmware).
- [ ] **XCUT.T10** Config persistence end to end: per-module files, `setup()` repair, littlefs
      atomicity under power loss, flush before each reset path, concurrent writers, unsupervised flush
      task failure visibility.
- [ ] **XCUT.T11** Setter dispatch: `PUT /sensors` direct `_set_dict_cfg` vs settings-group
      `handle_set_cmd`; per-module serialization; failed-push recovery chain under concurrency;
      post-hook failure reporting; "Unchanged" semantics vs a diverged chip.
- [ ] **XCUT.T12** Readiness gates (C.13) for every module, including behaviour when `setup()` fails
      or is never reached.
- [ ] **XCUT.T13** Every reset/reboot path (REST reboot/bootloader, supervisor, WDT, alarm-pool
      fallback): FRAM pause, config flush, repeated requests, interaction with an in-flight PUT.
- [ ] **XCUT.T14** The generated `sensortask_<device>.py` modules as frozen firmware code in their own
      right: reviewed like `src/`, yet outside `src/` review, outside coverage (seed `TEST.S13`), and
      outside `test_reset_call_site_invariant.py`'s scan.
- [ ] **XCUT.T15** Part G.3 re-validation: grep-for-the-shape sweep for duplicated primitives across
      `src/`, `buildgen/`-generated code and `js/`.
- [ ] **XCUT.T16** Import graph: no cycles across `src/` + `ext/` + generated code; import-time side
      effects per module (allocations, hardware access); frozen set = transitive import closure (with
      `GEN.T05`).
- [ ] **XCUT.T17** Data freshness contract: what `TS` means per driver; can any cycle publish old
      values with a new timestamp (seed `SENS.S08`)?
- [ ] **XCUT.T18** Time base: RTC set by NTP, `time.time()` vs `ticks_ms()`, `mktime` epoch/TZ,
      timestamps stored in FRAM, boot signature semantics.
- [ ] **XCUT.T19** Cancellation-safety map: every `await` reachable from a cancelling context (webserver
      `wait_for`s `src/asy_webserver_service.py:246, 708`, `src/asy_fram_driver.py:408`, supervisor
      restarts). For each multi-step sequence cut mid-way (`_set_dict_cfg` persist→push→recover, SCD30
      command+wait, FRAM dual-copy write and BUSY marker, `write_config` staging, `_flush_pending_configs`
      before a reboot) state what the cut leaves behind.
- [ ] **XCUT.T20** Boot failure beyond `setup()`: a constructor in `build_system()` raising, an exception
      or return out of `main()`, frozen `main.py` ending in the REPL with `WDT(8000)` armed and no FRAM
      logger yet — is the resulting reset loop diagnosable at all? Leftover filesystem `boot.py`/`main.py`
      from the legacy tree (`PLAT.T10`).
- [ ] **XCUT.T21** Tick counting and `ThreadSafeFlag` semantics: counters that advance once per `wait()`
      (SysUptime, WiFi/NTP counters, hotspot timeout, sensor base triggers) lose ticks when the flag is set
      twice before the waiter runs, a soft callback is dropped, or the loop stalls > 1 period. Which must be
      wall-clock accurate? Exactly one waiter per flag, across supervisor restarts too.
- [ ] **XCUT.T22** Soft-callback pile-up budget: callbacks that can fall due inside the longest no-yield or
      IRQ-off window (flash write, I2C `timeout`, GC pause, VOC step) vs the scheduler depth (8, F.1).
      Analysis only — F.1 settles the software-timeout mitigation as rejected.
- [ ] **XCUT.T23** Non-finite values on every output path: which floats can reach `json.dumps` (REST
      responses, config files) as NaN/±inf (MicroPython emits bare `nan`/`inf`, invalid JSON — verify at
      1.29.0)? Only SCD30 checks `isfinite` (`src/asy_scd30_driver.py:626`). One finiteness contract per
      layer (see `REST.T11`).
- [ ] **XCUT.T24** Post-mortem diagnosability (L-DIAG end to end): per failure class — WDT reset,
      supervisor reboot, boot crash, unsupervised-task death, FRAM write failure inside the logging layer
      (`_diag()` silent at level 0, `src/print_log.py:177-178`) — what persisted evidence survives?

Seeds:
- **XCUT.S01** A watchdog feed happens only after the supervisor's full scan; several task deaths,
  each costing two persisted FRAM writes, plus the 2 s sleep could approach the 8 s WDT and turn a
  commanded, FRAM-paused reboot into an unpaused WDT reset (`src/system_service.py:229-255`).
- **XCUT.S02** ONE_SHOT soft timers on critical paths contradict C.9's own "PERIODIC for anything
  that must fire" rule: `_reboot` (`system_service.py:126`), storage auto-unpause (`:365`),
  `_timer_sequencer` (`:164`); the arm-failure paths only cover ENOMEM.
- **XCUT.S03** Every `_reboot()` call deinits and re-arms the 4 s reset timer, so repeated reboot
  requests can postpone the reset indefinitely while FRAM stays paused (`system_service.py:118-126`).
- **XCUT.S04** A supervisor-triggered reboot does not flush pending configs, unlike the REST path
  (`src/system_service.py:251-253`; REST path `buildgen/codegen.py:501-514, 524-531`).
- **XCUT.S05** If `_timer_sequencer` cannot arm its next step, the remaining timer starters are
  skipped with only a print-level error; those drivers' tasks then wait forever and the supervisor,
  which only checks `done()`, cannot see it (`system_service.py:169-175, 209-214`).
- **XCUT.S06** C.9.1's stagger proof: the first starter fires at offset 0; offsets are relative to each
  callback's actual run time, so latency accumulates; with SCD30's 500 ms base tick,
  `int(1000/(N+1))*j == 500` for N = 3, 7, 9 (`system_service.py:158-159`). The proof's own test
  re-implements the formula instead of reading it (seed `TEST.S06`).
- **XCUT.S07** Dynamic `wrnno = n+1` means a persisted W-code names different tasks on different
  devices/firmware versions and must stay ≤ 127 (`system_service.py:238-239`).
- **XCUT.S08** `[x2]` The FRAM chunk layer logs into the manager's RAM-only logger, not the owner's
  FRAM-backed history as C.7.1 states (`src/asy_fram_manager.py:622, 665-674, 716`).
- **XCUT.S09** A.4's "8 KB ample headroom over SGP40's ~250 B" predates WP1-WP3; ~17 logger/cfgmgr
  chunks on wozi and ~21 on dev now share the chip — never re-summed against 8 KB.
- **XCUT.S10** No `machine.reset_cause()` is recorded anywhere in `src/`, so post-mortems cannot tell
  a WDT reset from a commanded one.
- **XCUT.S11** The supervisor's reboot branch `return`s (`src/system_service.py:251-253`), so `main()`
  and `asyncio.run(main())` finish ~4 s before the reset fires (`buildgen/codegen.py:478, 705-708`):
  webserver, readers and any staged flush stop at once and `main.py` drops to the REPL. The REST reboot
  path keeps the loop running until the reset.
- **XCUT.S12** No `set_exception_handler()` anywhere in `src/` or codegen: an unretrieved exception
  from an unsupervised task (`src/config_manager.py:354`; `src/asy_wifi_service.py:394, 425`) only
  reaches MicroPython's default console print.
- **XCUT.S13** `WDT(timeout=8000)` is `build_system()`'s first statement (`buildgen/codegen.py:381`); the
  constructors after it run unguarded, so a construction-time exception becomes an 8 s WDT reset loop
  before any FRAM logger exists — nothing persisted, `reset_cause()` never read (`XCUT.S10`).

Quality measure: a written timer/task/lock/error-code/FRAM-layout inventory per device, derived from
code, with every discrepancy against Parts A.7/C.7-C.9 registered; worst-case watchdog gap computed.

---

### 5.2 CORE — Core runtime modules

**Goal**: Part D in full (D.0-D.16) for `system_service.py`, `base_classes.py`, `config_manager.py`,
`print_log.py`, `api_response.py`, function by function.
**References**: Parts C.4-C.7, C.13, G.2, I.4; legacy `python/CommonDrivers/async_manager.py`,
`api_helpers.py`, `system_service.py`.

Topics:
- [ ] **CORE.T01** `ConfigManager.setup()`: every read-failure class (ENOENT vs EIO vs `MemoryError`
      vs corrupt JSON vs wrong type) and whether each may overwrite user config with defaults.
- [ ] **CORE.T02** `write_config()`/`_flush_staged()`/`flush_pending()`: staging identity checks,
      superseded flushes, exceptions from an unsupervised flush task, `_cache` commit in `finally`
      after a failed write (C.7.3 "costs persistence, never the config").
- [ ] **CORE.T03** Validation primitives (`type_or_range_error`, `coerce_numeric`,
      `check_cfg_get_default`, `special` handling) on single-precision rp2 floats, bigints, ±inf/NaN,
      `bool`-is-`int`, enum sets; static rejection of malformed schemas (int bounds on float fields,
      tuple `special` on special-alone fields).
- [ ] **CORE.T04** `_set_dict_cfg` orchestration: snapshot → persist → push → recover under
      concurrent PUTs to the same module; interaction with `Unchanged`.
- [ ] **CORE.T05** (module-level half of `XCUT.T08`) `PrintLogHistory`/`PrintLogHistoryStore`: ring semantics, count saturation, code
      encoding (0x80 split), pre-setup entries, reset-vs-setup race, `errno=0`, allocation per entry.
- [ ] **CORE.T06** `SystemService`: uptime/boot-signature across task restart, debug-level
      application, `pause_permanent_storage` clamp and unpause, reboot timer re-arm.
- [ ] **CORE.T07** `api_response`: envelope catalogue vs what the webserver actually emits; code 100
      after a post-hook exception; unused catalogue codes.
- [ ] **CORE.T08** `Lockable`/`LockableBuffer`/`Locked*`: does any `Locked*` critical section contain an
      `await`? If none, each lock is pure cost under cooperative scheduling — justify, document or drop;
      swallowed `RuntimeError`; unused per-buffer locks; clamping.
- [ ] **CORE.T09** D.15 method ordering, D.6 typing, D.11 comments, D.10 shapes across the five files.
- [ ] **CORE.T10** Dead/test-only API (seed `CORE.S14`): keep, trim or document — each is frozen
      bytecode on the device.
- [ ] **CORE.T11** `PrintLogHistoryStore` evidence preservation: which `_read()` failures (blank chunk, CRC
      mismatch, transient SPI EIO, paused storage) make `setup()` write the RAM ring over the persisted
      one; does the chunk API distinguish "never written" from "unreadable"? (CLAUDE.md FRAM-forensics
      rule; with `STOR.T01`).
- [ ] **CORE.T12** `ConfigManager` repair fixpoint and file lifecycle: every `setup()` repair converges
      within one boot (int↔float coercion, float32 JSON repr, special-alone fields — C.7.3's boots-bound
      covers a failing write, not a successful one that never converges); orphaned `config_*.cfg` after
      an instance is renamed/removed; filename length with `name_ext`.

Seeds:
- **CORE.S01** A supervisor restart of the uptime task resets uptime to 0 and leaves the boot
  signature `None` for the rest of the boot (`start_time_set` stays True), silently faking "a reboot
  happened"; untested (`src/system_service.py:375-394`).
- **CORE.S02** Any read failure in `ConfigManager.setup()` — `MemoryError` on a valid file, EIO,
  `TypeError` — is logged as wrnno 3 "not found" and the file is rewritten with defaults, destroying
  user config on a transient boot failure (`src/config_manager.py:407-426, 459`).
- **CORE.S03** Errors logged before a logger's `setup()` are overwritten when `_read()` restores the
  FRAM ring (e.g. SYSTEM's `_apply_level` errno 7 during `sysfunct.setup()`, before SYSTEM's
  `pr.setup()` runs in `start_and_check_tasks`) — but survive on first boot, so behaviour is
  inconsistent (`src/print_log.py:173-176, 273-277`).
- **CORE.S04** `reset()` during an in-flight `setup()` read restores the old ring into RAM while FRAM
  is cleared (`print_log.py:213-223` vs `:273-277`).
- **CORE.S05** No per-module serialization of `_set_dict_cfg`'s sequence; a failed push in one PUT can
  make `_recover_failed_push` persist its pre-write snapshot over another PUT's accepted value
  (`src/base_classes.py:302-358`).
- **CORE.S06** A post-hook that raises after fields were persisted and pushed yields code 100 with an
  empty result, and the webserver then marks every field "Failed" (`src/api_response.py:92-105`;
  `src/asy_webserver_service.py:463-470`).
- **CORE.S07** Every persisted log entry allocates a fresh `AsyFramChunkBuffer` with an unused
  `asyncio.Lock`, against G.2's one-long-lived-buffer rule; `LockableBuffer`'s lock is never used
  anywhere (`print_log.py:249, 262`; `base_classes.py:54-56`).
- **CORE.S08** Debug-level precedence: the persisted `DebugLevel` overrides the constructor `debug=`;
  CFGMGR loggers never receive `debug`; with an invalid cfgmgr `get_debug_level()` reports 0 while
  loggers keep their constructor level (`system_service.py:105, 287-296, 317, 340-341`; `config_manager.py:220`).
- **CORE.S09** `flush_pending()` is unguarded: a flush task that died with an unexpected exception
  re-raises through `_system_cmd_callback` and the reboot is never issued; re-await semantics of a
  finished task need checking against pinned `extmod/asyncio` (`config_manager.py:390-400`; also
  `system_service.py:184-196`).
- **CORE.S10** `write_config` validates against the caller's `cfg_vals` while `setup()`/`_cache` use
  `self.cfg_vals` — two sources of truth (`config_manager.py:299-347`).
- **CORE.S11** Each invalid key in a PUT is a persisted *error* (errno 10/12) and a FRAM write under
  `config_lock`; client input can evict real fault evidence from the 10-slot ring
  (`config_manager.py:319, 330`).
- **CORE.S12** `get_int_values()` uses `int()`, silently truncating a float field or converting a
  bool, unlike `get_bool_values()`'s strict check (`config_manager.py:282-289`).
- **CORE.S13** Small: `Lockable.__aexit__` swallows `RuntimeError` on double release
  (`base_classes.py:47-50`); comment claims `pr.name == name` in the `logger=` branch without enforcing
  it (`:163-171`); `get_log()` reports ErrNum 128 for a raw 0x80 entry (`print_log.py:189-191`);
  `errno=0` counts but never persists (`:161-166`).
- **CORE.S14** Production API with no `src/` caller: `api_response.parse_cmd_request` (webserver
  re-implements it as `_body_as_dict`, a Part G duplicate), catalogue codes 2-5, `ok_descr`,
  `SystemService.get_debug_level`/`set_debug_level`/`stop_uptime_timer`, `LockedFlag`,
  `type_or_range_error(check_special=)`, `SensorReader(logger=)`.
- **CORE.S15** Comment drift: `config_manager.py:126-127` says the generated `lightCmdLED` dispatch
  calls `coerce_numeric()`; it calls `type_or_range_error()` with synthetic schemas
  (`buildgen/codegen.py:538-556`).
- **CORE.S16** `PrintLogHistoryStore.setup()` calls `_write()` whenever `_read()` returns False, and
  `_read()` returns False on any failure, so a transient read fault at boot — not only a blank chunk —
  overwrites the persisted ring and count (`src/print_log.py:257-271, 276`).
- **CORE.S17** `write_config()` sets `self._staged` before `asyncio.create_task()`; a `MemoryError` there
  returns `(False, {})` (every field "Failed") while `_current()` keeps serving the staged value and no
  flush is ever scheduled (`src/config_manager.py:353-360`).
- **CORE.S18** SysUptime counts `uptime_event` wake-ups, not elapsed time: every loop stall > 1 s or
  dropped soft callback is a permanent undercount (`src/system_service.py:204, 379-380`; same mechanism
  as `NET.S02`).

Quality measure: each file passes Part D with every finding registered; each seed confirmed or
rejected by a verifier with a repro or a source citation.

---

### 5.3 ALGO — Pure algorithms and codecs

**Goal**: every formula and codec correct against its primary source, over its full domain, in the
target's arithmetic (float32 on rp2, arbitrary-precision ints in Python vs int32 in C references).
**References**: Part D.1/D.12, F.1 (float32), F.4; `math_helpers.py`'s cited literature; Sensirion
VOC Index algorithm (reference C source **not in the repo** — owner to supply or accept a gap).

Topics:
- [ ] **ALGO.T01** `math_helpers`: each formula vs its cited source, validity range vs the source's
      real domain vs the caller's hardware range (D.1), NaN/±inf, float32 behaviour.
- [ ] **ALGO.T02** `voc_algorithm`: port fidelity vs Sensirion's C reference, including every place C
      `int32` wraps and Python ints don't; state (de)serialization; blackout semantics after restore.
- [ ] **ALGO.T03** `crc_checks`: test vectors per polynomial/width, pass-mode parity with real mode,
      incremental API contract, per-byte `sleep(0)` cost and where it runs under a bus lock.
- [ ] **ALGO.T04** `framing_codecs`: COBS round-trip property over all lengths/zero patterns,
      in-place decode safety, scratch-aliasing contract with the UART write path; COBS is unused in
      production (UART defaults to `Framing_Pass`) — keep, test-only, or document.
- [ ] **ALGO.T05** Restored-state robustness: `unpack_from()` accepts any 32 int64 values; per field, does
      an out-of-int32 / out-of-domain value give a bounded wrong result, an exception, or a hang (→ WDT
      reset restoring the same state = boot loop)? (with `PAR.S09`, `STOR`).
- [ ] **ALGO.T06** Runtime float32 vs compile-time double: C folds `F16(x)` in double at compile time,
      the port evaluates `_f16(x)` at run time in rp2 float32; enumerate every `_f16` argument and every
      frozen float literal/`const()` in `math_helpers`, prove equality — or precompute as integer `const()`s.
- [ ] **ALGO.T07** Oracle provenance for every ALGO test: literature/datasheet vectors, an independent
      implementation, or values the port generated itself (tautological).

Seeds:
- **ALGO.S01** `_FIX16_OVERFLOW`/`_FIX16_MINIMUM` are positive `0x80000000` in Python but `INT32_MIN`
  in C; `_fix16_div`'s `if not bit` overflow check cannot trigger; `F16(1)+FIX16_MAXIMUM` wraps
  negative in C but not here (`src/voc_algorithm.py:41-43, 248, 628, 675, 688`).
- **ALGO.S02** VOC state is packed as `"32q"` without a byte-order prefix, while F.1 says on-chip
  layouts pin `"<"` (`voc_algorithm.py:98, 141`).
- **ALGO.S03** `altitude_baro` returns a pressure, not an altitude (naming); the `abs_humidity` comment
  calls 7.6/240.7 "ice-phase" constants, which in the literature are the supercooled-water pair (ice
  is 9.5/265.5) — legacy-identical, unused in `src/` (`src/math_helpers.py:86-98, 101-112`).
- **ALGO.S04** Pass-mode `add_into`/`check_from` skip the bounds validation real mode does, and pass-mode
  `add()`/`check()` return the caller's object where real mode returns a copy
  (`src/crc_checks.py:58-59, 73-74, 111-112, 131-132`).
- **ALGO.S05** `CRC16`, `rel_humidity`/`abs_humidity`, `Framing_COBS` have no production caller
  (`src/crc_checks.py:155-157`; `src/math_helpers.py:101, 119`; `src/framing_codecs.py:75`).
- **ALGO.S06** `_fix16_div()` masks a negative divisor to 32 bits; if `b` is a negative multiple of 2**32,
  `divider` becomes 0 and `while divider < remainder` never ends while `bit` grows as a bigint — C's int32
  can't produce such a `b`, Python's non-wrapping arithmetic or an unvalidated restore could
  (`src/voc_algorithm.py:139-178, 242, 245-247`).
- **ALGO.S07** `_f16()` runs in float32 on every sample and boxes floats each call; equality with C's
  compile-time double constants is unverified (`src/voc_algorithm.py:199-202`; uses e.g. `:417, 505, 510,
  657, 761`).
- **ALGO.S08** rp2 small ints stop at 31 bits; the CRC32 register exceeds that on every shift, so each bit
  step allocates a bigint (`src/crc_checks.py:41-47`) — CRC32 guards SGP40's VOC chunk
  (`src/asy_sgp40_driver.py:181`), re-read every second during the NTP wait (`SENS.S05`). The 64-bit Unix
  port never shows this.

Quality measure: every formula has a cited source check and a float32 emulation check; VOC port has a
differential result or a recorded owner-accepted gap.

---

### 5.4 BUS — Bus layer

**Goal**: the I2C/SPI/UART wrappers' contracts (raise surface, never-block, locking, readiness) hold
exactly as Parts C.3, C.8, F.5.1/F.5.2/F.5.7-F.5.9 state, against the pinned rp2 port source.
**References**: `ports/rp2/machine_i2c.c`, `machine_spi.c`, `machine_uart.c`, `extmod/machine_i2c.c`
at `v1.29.0`.

Topics:
- [ ] **BUS.T01** Every public method's raise/sentinel contract vs Part D.2's per-bus `OSError`
      surface; every upstream caller catches what can propagate.
- [ ] **BUS.T02** Shared per-bus 32-byte I2C scratch: no await between fill and decode anywhere; no
      IRQ/Timer path touches I2C; copy-out on every return.
- [ ] **BUS.T03** Lock-hold spans that include sleeps (probe, SCD30 command waits) and their effect on
      sibling devices' timing on a shared bus.
- [ ] **BUS.T04** SPI session primitives: `configure()`/`machine.SPI.init()` per CS assertion — cost
      and whether it resets the peripheral each time; blocking `sleep_us(2)`.
- [ ] **BUS.T05** UART never-block invariant (CLAUDE.md hard rule): every read path clamped and
      yielding; write path waits; cancel handshake; `readinto(nbytes > len(buf))`.
- [ ] **BUS.T06** Uninitialised-bus behaviour (silent no-ops) and whether any caller can reach it.
- [ ] **BUS.T07** The deliberate I2C/SPI asymmetry (BACKLOG: SPI sync session, I2C none) stays
      deliberate; the D.10 note is current.
- [ ] **BUS.T08** Unused public API (frozen bytecode that must still meet its bus contract): UART beyond
      `readinto_until_complete`/`writefrom`; I2C `scan`, `writeto_then_readfrom`, `write_then_readinto`;
      SPI `write_readinto` and the async transfers — keep, trim or test.
- [ ] **BUS.T09** I2C bus recovery across an MCU-only reset: a WDT/`machine.reset()` mid-read resets the
      RP2040 but not the powered sensors; a slave holding SDA low survives into the next boot unless a bus
      clear is issued (check `ports/rp2/machine_i2c.c` init). Tests F.2's settled premise that a reboot
      reconstructs a wedged bus — raise, don't act (2.3).
- [ ] **BUS.T10** Worst-case synchronous block per I2C transaction (bus `timeout` from the TOML,
      `buildgen/codegen.py:386-387`, × transactions per locked section); per-port `machine.I2C` singleton
      silently reconfigured by a later construction with different freq/timeout (`HW.S18`).
- [ ] **BUS.T11** Pin states before `setup()` and across resets: FRAM CS pad default vs the FRAM
      power-up CS rule and any board pull-up; UART TX idle level before `init()` (with `STOR.T11`, `HW.T07`).
- [ ] **BUS.T12** IRQ-off windows vs peripheral buffering: littlefs program/erase (config flush, boot
      repair) vs the 32-byte UART RX FIFO (~2.8 ms at 115200, overrun absorbed silently, C.3.2), SPI DMA
      (F.5.2), CYW43. Window lengths need the Pico W QSPI flash datasheet — missing from `datasheets/`.

Seeds:
- **BUS.S01** `I2C.readfrom_into`/`writeto` are silent no-ops when `_i2c is None`; SCD30/SGP40 would
  then CRC-check stale buffer contents that pass — latent, unreachable today
  (`src/asy_i2c_driver.py:204-205, 222-223`).
- **BUS.S02** `I2CDevice._probe_for_device` sleeps 2×100 ms while holding the bus lock during every
  driver's `setup()` (`asy_i2c_driver.py:261-271`).
- **BUS.S03** `SPIDevice.session_begin` calls `machine.SPI.init(...)` on every chip-select (~25 per
  FRAM block); if rp2's `init` resets the peripheral this is real per-CS overhead (inferred; check
  `ports/rp2/machine_spi.c`) (`src/asy_spi_driver.py:67, 133-139`).
- **BUS.S04** `SPI.write_readinto()` returns `None` both on success and on a swallowed `ValueError`
  (`asy_spi_driver.py:83-97`).
- **BUS.S05** UART: `_read_delimited`'s delimiter/skip branches consume buffered bytes without
  yielding (bounded by `rxbuf`) (`src/asy_uart_driver.py:171-176`); `_write_all` waits on
  `ready(POLLOUT)` with no deadline at the *idle* poll rate (`:135, :267`); `readinto(buf, nbytes)` with
  `nbytes > len(buf)` relies on `machine.UART.readinto` clamping (`:353-354`).
- **BUS.S06** `readline()`/`readline_until_complete()` call `machine.UART.readline()` without the `any()`
  clamp, and `:415` has no length bound — a steady newline-free stream would hold the loop for its wire
  time; neither has a production caller (`src/asy_uart_driver.py:395, 410, 415`).
- **BUS.S07** Every I2C transaction allocates new memoryview objects around the long-lived scratch
  (`src/asy_i2c_driver.py:63, 208, 231`).
- **BUS.S08** `Pin(cs_pin)` is bound without a mode and first driven in `setup()`; until then the
  active-low FRAM CS sits at the pad reset default while `machine.SPI()` muxes SCK/MOSI
  (`src/asy_spi_driver.py:43, 117, 181-184`).

Quality measure: every seed confirmed/rejected against rp2 source; never-block invariant re-proven by a
clamp-removal sweep over the current driver.

---

### 5.5 SENS — Sensor drivers

**Goal**: SCD30, SGP40, BMP3xx, ISL29125 correct against their datasheets, robust in every recovery
path, consistent with Part C, and faithful to legacy field behaviour where legacy had one.
**References**: `datasheets/{scd30,sgp40,bmp3xx,isl29125}/`, Parts C, M; legacy
`python/IndividualDrivers/`; missing: BMP390 datasheet, Sensirion VOC reference, RP2040 silicon
datasheet (A.6).

Topics:
- [ ] **SENS.T01** Every register/command, CRC, delay, unit conversion and scaling vs the datasheet;
      float32 vs double for every formula that runs on rp2 (BMP compensation, SCD30 offset).
- [ ] **SENS.T02** Config bounds vs helper domains vs datasheet ranges (e.g. `MeanAtmTemp` vs
      `altitude_baro`, `PressOffset` vs the plausibility gate, `BackupPeriod` vs verify period).
- [ ] **SENS.T03** Recovery paths per driver: failed read, CRC error, brownout, divergence re-apply,
      supervisor restart (is every piece of per-instance state re-initialised?).
- [ ] **SENS.T04** Stale-as-fresh, per driver (system-wide contract in `XCUT.T17`): can a cycle publish
      cached values with a new `TS`?
- [ ] **SENS.T05** Interrupt semantics: SCD30 RDY fallback counter, ISL29125 INT thresholds vs the
      decision rule, soft-IRQ allocation, IRQ storms.
- [ ] **SENS.T06** Bus-time budget on `dev`'s shared i2c1 (SCD30 50 ms sleeps under the bus lock vs
      SGP40's 1 Hz cadence vs ISL29125 cycles); VOC processing time on target.
- [ ] **SENS.T07** NVM wear: every SCD30 persistent setter and who can trigger it (REST, loops, tests),
      incl. whether "Unchanged" writes are skipped as legacy did (seed `PAR.S02`).
- [ ] **SENS.T08** Part C conformance and D.10 across the four: constructor shape, snapshot-read
      failure logging, errno allocation, operating-range gates, `@web`/`@limits`/`@requires` tags.
- [ ] **SENS.T09** Unverified protocol assumptions: SCD30 reading back 0x0010 (`SENS.S10` area), SGP40
      serial word[0] `== 0x0000` (`SENS.S06`, `SENS.S21`).
- [ ] **SENS.T10** Four-tier bus-hazard coverage per driver (CLAUDE.md hard rule), checked against the
      real tier files rather than assumed.
- [ ] **SENS.T11** VOC 1 Hz sampling: Sensirion's algorithm expects one `measure_raw` per second; SGP40 is
      driven by a soft PERIODIC timer + `ThreadSafeFlag` that merges ticks missed during loop stalls
      (`NET.S01`/`NET.S02`, FRAM writes, SCD30 bus holds). Measure lost samples and the effect on time
      constants, the 45-sample blackout and `backup_counter` (counts cycles, not seconds) (`XCUT.T21`).
- [ ] **SENS.T12** SGP40 compensation input: age of the wired T/RH (SCD30 `MeasInt` up to 1800 s, value
      cached through its error streak), plausibility/clamping before tick conversion (`SENS.S03`), SCD30
      `TempOffs`/self-heating interplay, `_Default*` sources, mismatched cadences.
- [ ] **SENS.T13** Datasheet operating procedures: SCD30 FRC needs continuous mode at 2 s for ≥ 2 min
      (Interface Description 1.4.5), ASC needs ≥ 7 days uninterrupted power with daily fresh air (1.4.6) —
      vs user-settable `MeasInt`, REST `ForceCalRef` with no precondition/warning, and the soft reset on
      every `setup()`; SGP40 heater-off/idle, self-test in measurement mode (3.3), serial read length
      (3.4); BMP3xx IIR in forced mode (time constant in samples × `SampleInterv` up to 3600 s; CONFIG
      write resets it, 3.4.3) and the recommended osr pairing (Table 5).
- [ ] **SENS.T14** A sensor missing or permanently failed, end to end: `setup()` retry rate, persisted-log
      volume per hour, whether the supervisor score ends in a device reboot, knock-on on SGP40
      compensation and notifications, legacy parity.
- [ ] **SENS.T15** Persisted logs outside the `_error_check` streak: can a steady fault persist one entry
      per cycle forever, against C.7.1's once-per-episode rule (SGP40 errno 12-18 — 13 from
      `_check_storage` fires every second —, BMP errno 14/22, ISL errno 14/28/31-35, SCD30 forwards)?
      (with `XCUT.T07`).
- [ ] **SENS.T16** Hardware I/O triggered by a REST GET: every `_read_sensor_dict` callback (SCD30
      six-register snapshot, BMP bit-field snapshot, ISL snapshot + divergence re-apply + wrnno 11) — cost
      under the bus lock, side effects, GET safety/idempotency (with `REST.T10`).
- [ ] **SENS.T17** `@requires` tags vs each datasheet's bus limits: ISL29125 (400 kHz max) and BMP3xx
      carry none (with `GEN.T03`).

Seeds:
- **SENS.S01** SGP40 `get_raw()` points `self._command_buffer` at `_measure_command` and restores it
  without `try/finally`; after any failed read the alias persists across supervisor restarts, and
  `initialize()` then writes the serial/self-test commands into the 8-byte measure buffer and sends
  all 8 bytes; untested (`src/asy_sgp40_driver.py:608-612, 669-683`).
- **SENS.S02** SGP40 FRAM verify period `int(math.ceil((10*60)/p)*0.1)` is 0 for `BackupPeriod`
  67-1440 (verification disabled) and off by one elsewhere (p=7 → 8, intended 9)
  (`asy_sgp40_driver.py:352, 409`).
- **SENS.S03** SGP40 compensation ticks are masked `& 0xFFFF` instead of clamped: RH −1 % → ~99 %,
  RH 101 % → ~1 %, T 131 °C → ~−44 °C; inputs are not clamped upstream (`asy_sgp40_driver.py:595, 602`).
- **SENS.S04** VOC = 0 is stored as a valid reading during the 45-sample blackout after every
  init/reset; the datasheet index range is 1-500 (`voc_algorithm.py:761-762, 780`;
  `asy_sgp40_driver.py:444-447`).
- **SENS.S05** `_run_restore` re-reads the 260-byte FRAM chunk every second while waiting up to 600 s
  for NTP (`asy_sgp40_driver.py:212-215, 383-385`).
- **SENS.S06** SGP40 serial-number check `word[0] == 0x0000` is an undocumented Adafruit assumption
  (`asy_sgp40_driver.py:674-678`).
- **SENS.S07** SGP40 measure wait is 100 ms against a 30 ms datasheet maximum (inferred cost only)
  (`asy_sgp40_driver.py:610-611`).
- **SENS.S08** SCD30 `scd_timer_triggers` accumulates across cycles (comment says "consecutive") and
  forces a read even when RDY is low; the not-ready read leaves the cache untouched and `_read_scd`
  re-stamps cached values as fresh — legacy-identical (`src/asy_scd30_driver.py:174-187, 412-420,
  610-611`).
- **SENS.S09** SCD30 `int(offset*100)` truncates 0.01 K low for ~6.5 % of 0.01-step values in float32
  (0.53 → 52, 1.05 → 104) (`asy_scd30_driver.py:570`) — A.4 documents truncation as deliberate; the
  float32 representation effect is the new part.
- **SENS.S10** SCD30 has no CO2/RH/T plausibility gate (datasheet 0-40000 ppm), only finiteness, though
  C.3 says operating-range checks live in layer 2 (`asy_scd30_driver.py:621-630`).
- **SENS.S11** SCD30 sleeps 50 ms inside the bus lock per command/register read;
  `get_config_snapshot` holds i2c1 ≥ 6×50 ms (`asy_scd30_driver.py:471, 483, 514-520`).
- **SENS.S12** BMP3xx `MeanAtmTemp` accepts −50..50 but `altitude_baro` requires −40..85, so
  [−50, −40) silently yields `SLPres = None` (`src/asy_bmp3xx_driver.py:84`; `math_helpers.py:25-26, 92`).
- **SENS.S13** BMP3xx plausibility gate runs before `PressOffset` (±500 hPa) is applied, so a published
  `Pres` can leave the datasheet range and `SLPres` becomes `None` with no log (`asy_bmp3xx_driver.py:237`).
- **SENS.S14** BMP3xx `get_altitude()`/`get_pressure()`/`get_temperature()` have no production caller
  (`asy_bmp3xx_driver.py:555-577`).
- **SENS.S15** ISL29125: in high range INT is armed on green ≤ down-threshold, but `_evaluate_range`
  decides on the peak of all three channels, so a colour-dominant scene (or `AutoRangeDwell`, or
  darkness on the low range's 0 threshold) can fire INT every PRST window and force a read cycle
  indefinitely (`src/asy_isl29125_driver.py:359-364, 577-583, 598-599`).
- **SENS.S16** ISL29125 `set_autorange_thresh()` does not rewrite the chip's threshold registers,
  unlike `set_resolution()` (`asy_isl29125_driver.py:981-988` vs `:941-945`).
- **SENS.S17** ISL29125 small: the 1-count dark offset is subtracted after `<<4`, so at 12 bit it is
  1/16 count (`:1262-1263`); `_filtered` survives a restart (`:270`); calibration legs stall the read
  loop.
- **SENS.S18** Part C divergences: ISL29125 constructor order/kw-only (`asy_isl29125_driver.py:197-212`);
  SGP40's `fram_storage`/`fram_ntp_callback` names (`asy_sgp40_driver.py:140-141`); snapshot-read
  failure logging differs (BMP errno 22 `asy_bmp3xx_driver.py:177`, ISL errno 28
  `asy_isl29125_driver.py:723`, SCD30 base errno 4 `src/base_classes.py:210`).
- **SENS.S19** C.3 text is stale: BMP3xx "has no scratch buffer" (the I2C layer now has one)
  (SPECIFICATION.md ~1541-1543).
- **SENS.S20** Missing references: BMP390 datasheet (driver accepts chip ID 0x60), RP2040 silicon
  datasheet, WS2812 datasheet, Sensirion VOC algorithm reference.
- **SENS.S21** The SGP40 serial-number read fetches 3 of the 9 bytes the datasheet specifies
  (`readlen=1`), so only word 0 is CRC-checked and compared (`asy_sgp40_driver.py:669-678`; datasheet
  3.4, Tables 8/16).
- **SENS.S22** `SCD30_I2C.setup()` sends a soft reset on every read-loop (re)start
  (`asy_scd30_driver.py:577-589`); 1.4.10 says it restores the power-up state, and 1.4.6 says ASC's first
  7-day search aborts on power interruption — whether a soft reset aborts it is undocumented.
- **SENS.S23** BMP3xx polls STATUS every 2 ms (~60 bus transactions per ×32/×32 conversion on a possibly
  shared bus) although the conversion time is computable (3.9.2) (`asy_bmp3xx_driver.py:408, 541-553,
  623`).
- **SENS.S24** An ISL29125 `GET /sensors` can write both the chip and the FRAM ring:
  `_read_sensor_dict()` → `_check_divergence()` → `configure(force=True)` + `wrn_s` 11
  (`asy_isl29125_driver.py:716-728, 745-755`) — possibly intended (comment `:717-719`); record either way.
- **SENS.S25** When a config read fails, BMP3xx and ISL29125 still publish a freshly stamped sample with
  hard-coded fallbacks, silently dropping the user's offsets/filter (`asy_bmp3xx_driver.py:231-234`;
  `asy_isl29125_driver.py:503-507`) (with `XCUT.T17`).
- **SENS.S26** No driver's `stop_timer()` has a production caller (`asy_scd30_driver.py:233`,
  `asy_sgp40_driver.py:480`, `asy_bmp3xx_driver.py:305`, `asy_isl29125_driver.py:871`; NET's
  `asy_ntp_client.py:357, 360`, `asy_wifi_service.py:677`).

Quality measure: a datasheet-citation per register/formula; every seed resolved; a float32 emulation
run for each formula; restart-state table per driver.

---

### 5.6 STOR — FRAM storage

**Goal**: the dual-copy chunk store's integrity guarantees (all-or-nothing loss, busy markers, write
protection as an access gate, pause gating, determinism) hold under every fault and interleaving.
**References**: A.4 FRAM bullets, C.7.1 FRAM row, I.4(f.1); `datasheets/fram/` (MB85RS64V field,
MB85RS2MTA dev).

Topics:
- [ ] **STOR.T01** Block/chunk state machine: UNINIT/IDLE/BUSY transitions for read, write, clear,
      repair; torn states at each step; blank-chunk reads.
- [ ] **STOR.T02** Dual-copy repair decisions (block 0 invalid, block 1 invalid, both valid-different)
      and their CRC coverage.
- [ ] **STOR.T03** Write-enable/WEL/WRDI handling, write verification cadence, status-register
      protection bits (volatile vs non-volatile), partial protection.
- [ ] **STOR.T04** (module half of `XCUT.T06`) Locking: driver lock + bus lock held together per block; chunk `_op_lock`; logging
      while holding the driver lock (deadlock invariant).
- [ ] **STOR.T05** Pause gating: who sets pause (`mempause` 300 s, reboot paths); writes during a pause
      are dropped, not deferred (a log entry is lost); `override_pause` has no production caller
      (`STOR.S07`); interplay with `XCUT.T13`/`CORE.T06`.
- [ ] **STOR.T06** Timestamped chunks: NTP gating, `(ntp_synced, utc, success)` ordering.
- [ ] **STOR.T07** Address width / product-ID mapping for both chip sizes; wraparound; out-of-range.
- [ ] **STOR.T08** errno/wrnno ranges vs C.7.1 (drift noted; catalogue owned by `XCUT.T07`); the chunk
      layer's logger ownership (`XCUT.S08`) and the layout/8 KB budget (`XCUT.T09`, `XCUT.S09`) are this
      module's too.
- [ ] **STOR.T09** Timestamped chunks across clock changes: `age = now - ts` negative or jumping when the
      RTC is set backwards, `NTP_Offset_S` changes (±12 h, shifts the RTC itself) or a pre-NTP clock runs;
      `BackupMaxAge` accepts any negative age (`asy_fram_manager.py:609-614`; `asy_sgp40_driver.py:389`);
      `_TS_UNINIT = 0` as sentinel (with `XCUT.T18`, `NET.T11`).
- [ ] **STOR.T10** Reads are writes: every `_read_chunk` writes BUSY then IDLE to both status bytes
      (`:299, :343`) — refused under write protection/pause, power loss during a *read* leaves BUSY, and the
      status bytes are the most-written cells: compute per-byte endurance for the busiest ring vs 10^12
      (MB85RS64V) / 10^13 (MB85RS2MTA).
- [ ] **STOR.T11** SPI electrical contract vs both FRAM datasheets: mode 0 at the 1 MHz default
      (`asy_spi_driver.py:55-57`; no baudrate from codegen) vs 20/40 MHz maxima, CS setup/hold, HOLD/WP
      tie-offs per board, power-up time before the first RDID; the FRAM driver has no `@requires` tag.
- [ ] **STOR.T12** Crash-consistency enumeration on a twin FRAM image: power loss after every SPI
      transaction k of write/read/clear/repair; classify the next boot per owner (log ring, SGP40 backup)
      (with `TWIN.T04`/`TWIN.S04`).

Seeds:
- **STOR.S01** `_set_check_sb` writes BUSY even when it found UNINIT and `_read_chunk` returns early
  without restoring, so a second read of a never-written/cleared chunk reports errno 31/33 "invalid"
  instead of "uninitialised"; untested (`src/asy_fram_manager.py:235-250, 306-308`).
- **STOR.S02** `_write_chunk`/`_read_chunk` call `self.pr.err_s` while holding the FRAM driver lock —
  safe only because the chunk logger is RAM-only; a FRAM-backed logger (what C.7.1 says happens)
  would deadlock on the non-reentrant lock; nothing enforces it (`asy_fram_manager.py:278-289, 320-355`).
- **STOR.S03** `setup()` sets `_wp` only when the status register equals 0x8C exactly; a chip with BP
  bits partly set is treated as writable (`src/asy_fram_driver.py:388`).
- **STOR.S04** C.7.1's FRAM row: "manager errno 17-88" vs code using 10/11/19/20; C.3's "fresh buffer
  per call" for FRAM_SPI vs preallocated buffers and no `_send_opcode` (`asy_fram_driver.py:118-121`;
  SPECIFICATION.md ~1544-1545, ~1926).
- **STOR.S05** `verify_present()`/`set_write_protected()` have no production caller and are SETTLED as
  kept (`src/asy_fram_driver.py:357, 400`; BACKLOG.md:72) — record as settled-no-action.
- **STOR.S06** `FRAM_SPI`'s `wp_pin` path is unreachable in production (`AsyFramManager` never forwards it,
  `asy_fram_manager.py:628`; codegen emits only `max_size`/`debug`, `buildgen/codegen.py:203`) and treats
  the pin as whole-array protection (`asy_fram_driver.py:217-220`), while the MB85RS64V WP pin only
  guards the status register when WPEN=1.
- **STOR.S07** No `src/`/`buildgen/` code passes `override_pause=True`; the parameter on every chunk
  method is test-only API (`asy_fram_manager.py:96, 128, 389`).
- **STOR.S08** An out-of-memory FRAM allocation is reported only through print-only `pr.err`
  (`asy_fram_manager.py:649, 662, 691, 704`; `asy_sgp40_driver.py:186`): a layout overflowing 8 KB
  (`XCUT.S09`) silently drops owners to RAM-only with nothing persisted.

Quality measure: every state transition covered by a named test at mock and twin tier; seeds resolved.

---

### 5.7 UART — UART protocol

**Goal**: `UART_Comm` conforms to Part J exactly; Part J is complete and unambiguous as the
two-implementation contract; every change is logged in `UART_C_PORT_CHANGELOG.md` with its class.
**References**: Part J, F.5.7-F.5.9, `UART_C_PORT_CHANGELOG.md`; the C side is out of scope (owner),
so no reconciliation — but Part J must remain sufficient for someone who does one.

Topics:
- [ ] **UART.T01** Frame/transaction rules vs Part J line by line (UID, CMD, SIZE, CHUNKS, CUR_CHUNK,
      ACK withholding, GET as one-chunk train).
- [ ] **UART.T02** Recovery: resync drain window/bound, write hold-off, blind-resync diagnostic,
      cancel handshake, listen backoff.
- [ ] **UART.T03** Allocation: preallocated buffers, peer-declared `CHUNKS` allocation (BACKLOG
      accepted-with-caveat), rejection bitmap.
- [ ] **UART.T04** (with `XCUT.T07`, `CORE.T05`) Logging: per-episode dedupe keyed on last errno only, `_ready()` flooding,
      repeat-counting vs C.7.1.
- [ ] **UART.T05** Construction validation (timeout floor, rxbuf floor) vs buildgen's own checks
      (`GEN.T01`, L.6.6).
- [ ] **UART.T06** `UartLinkExerciser` (bench-only): counters, supervision, FRAM wiring, whether its
      failure modes can pollute the persisted log at 1 Hz.
- [ ] **UART.T07** `UART_C_PORT_CHANGELOG.md` completeness vs git history of `asy_uart_comm.py`, and
      whether a "temporary" file with no reachable deletion trigger should be reclassified (seed
      `DOC.S14`).
- [ ] **UART.T08** End-to-end delivery semantics: a lost final ACK makes the initiator report failure
      after the responder already delivered the SET / ran `get_callback` — at-least-once with caller
      retries, at-most-once without. What does Part J promise; must commands be idempotent?
- [ ] **UART.T09** Cancellation/restart mid-transaction (supervisor restart, reboot, `clear()`): `_busy`/
      `_in_resync`/hold-off state, a half-sent frame on the wire, peer recovery, a listen-task restart
      while the peer is mid-train (with `XCUT.T19`).
- [ ] **UART.T10** Measured constants the contract rests on: `_GC_PAUSE_WORST_MS = 21` (under what heap,
      threshold, firmware?) and J.6's floors re-derived from `devices/dev.toml`'s baudrate/rxbuf/poll_*;
      what would invalidate them (with `PLAT`, `MEM`).

Seeds:
- **UART.S01** `[x2]` `UART_Comm._err` sends repeats to the sync `pr.err()`, which neither persists nor
  counts, while C.7.1 says `repeat=True` "still counts it" — UART repeats never reach `ErrCount`
  (`src/asy_uart_comm.py:319-322`; sync `err()` `src/print_log.py:112-114` vs persisting `_store_err()`
  `:158-175`, which does count repeats).
- **UART.S02** A GET frame's `CHUNKS=1` is not enforced (`asy_uart_comm.py:484-488`) though J.4 defines
  a GET as a one-chunk train.
- **UART.S03** Dedupe keyed only on the last errno, cleared by every valid frame: a link alternating
  good/bad or between two errnos persists on every fault (`:319, :658-661`); `_ready()` calls `err_s`
  on every call, so a failed `setup()` plus the exerciser's 1 Hz `uart_get` persists an entry per
  second (`:351-355`; `src/asy_uart_link_driver.py:110-120`).
- **UART.S04** The `dev` link runs with `CRC_Pass`: codegen never passes `crc=`
  (`buildgen/codegen.py:396-397`) — a corrupted payload byte is caught only structurally.
- **UART.S05** A declined command returns `cmd_id=None`, sending `_listen_loop` into backoff up to
  5×timeout while the initiator may already be retrying (`asy_uart_comm.py:1116-1126`).
- **UART.S06** `UartLinkExerciser.reset_error_counter()` also zeroes `transfers`/`failures`, so
  `ResetErrors` wipes measurement data, not only error history (D.10 vs other modules)
  (`src/asy_uart_link_driver.py:157-160`).

Quality measure: Part J ↔ code traceability table; every seed resolved; changelog complete.

---

### 5.8 NET — Networking

**Goal**: the WiFi/NTP/DNS/UDP/captive-DNS state machines are complete, bounded, non-blocking and
match legacy field behaviour or document the change.
**References**: A.4 "confirmed intentional" WiFi rules, C.8 (WiFi locking), F.2 (backstops), H.7
(connection ceiling), B.14.2 (lwIP), legacy `python/CommonDrivers/async_connect.py`; RFC 1035/5905.

Topics:
- [ ] **NET.T01** WiFi state machine: every phase × event, incl. task restart in each phase, PUT during
      a mode switch, PUT while `DEACTIVATED`, a client joining as the hotspot timer fires, a router
      outage at boot longer than the fail-to-hotspot + hotspot window, mid-handshake interruption by
      the 5 s poll (security/parity sides: `SEC.T04`, `PAR.S08`).
- [ ] **NET.T02** (with `XCUT.T06`; budget in `PERF.T05`) `wifi_mode_lock` hold spans (connect poll, 60 s sleep, NTP attempt) and what stalls
      meanwhile (uptime counters, `/status` getters, reconnect, NTP).
- [ ] **NET.T03** (threat side in `SEC.T05`/`SEC.T11`) NTP: sync/backoff/retry schedule, stale-sync reachability, ONE_SHOT retry timer vs
      C.9, reply validation (mode, version, origin timestamp, LI, stratum, KoD), RTC set semantics,
      EU-only DST rule vs configurable offsets, socket cleanup on cancel.
- [ ] **NET.T04** DNS client: query building (labels, trailing dot, 255-octet limit), response parsing
      (TC bit, uncompressed names, CNAME chains), server order incl. the public fallback.
- [ ] **NET.T05** (with `PLAT.T04`, B.14.2) UDP socket: poll strategy and idle cost, sentinel contract, `disconnect()` on every
      exit path, PCB budget (`MEMP_NUM_UDP_PCB = 5`) across DHCP/DNS/mDNS/captive DNS/NTP and STA↔AP
      transitions.
- [ ] **NET.T06** Captive DNS: QTYPE handling, QR bit, TTL after leaving hotspot, allocation per
      query, unsupervised task lifetime across mode switches, subnet filter.
- [ ] **NET.T07** Radio-string bounds (C.7.4 bytes) at write and at use; hostname cap vs legacy.
- [ ] **NET.T08** CYW43 synchronous calls per request (`status("rssi")`, `ifconfig()`), their cost and
      behaviour in AP mode.
- [ ] **NET.T09** Hotspot/captive portal end to end: AP security mode actually set (no explicit
      `security=`, `asy_wifi_service.py:384`), channel/country, AP subnet and DHCP pool vs the captive
      subnet filter, station limit, OS probe URLs (`/generate_204`, `/hotspot-detect.html`,
      `/connecttest.txt`) → 302 → index, HTTPS/DoH/"Private DNS" bypassing the portal, the 60 s TTL after
      leaving hotspot mode (with `REST.T07`).
- [ ] **NET.T10** Sockets across WLAN mode switches and `wlan.deinit()`: listening HTTP socket, in-flight
      TCP connections, captive-DNS/NTP/DNS UDP PCBs when the netif is torn down (STA↔AP, deactivation)
      (with `NET.T05`, `PLAT.T04`).
- [ ] **NET.T11** Clock jumps: first RTC set from the boot default, `NTP_Offset_S` shifting the RTC, DST
      boundaries, and every wall-clock consumer (`TS`, FRAM backup age, notification window, `cettime`)
      (with `XCUT.T18`, `STOR.T09`, `SEC.T11`).
- [ ] **NET.T12** D.9 sweep of the network API on 1.29: magic `pm=0xA11140` vs `WLAN.PM_*` (`:386, :452`),
      `_STAT_OBTAINING_IP = 2` (`:128`), `status("stations")` shape, explicit `security=` for STA/AP,
      `network.hostname()` semantics (DHCP option, mDNS).
- [ ] **NET.T13** DHCP/IP lifecycle while connected: lease renewal, address/DNS-server change, gateway loss
      while `isconnected()` stays true (F.2 backstop — not re-opening it), hostname collisions.

Seeds:
- **NET.S01** `wifi_mode_lock` is held across `asyncio.sleep(60)` in `_on_sta_disconnected`, stalling
  NTP, uptime updates and PUT-triggered reconnects for 60 s (`src/asy_wifi_service.py:473` inside
  `:583-590`).
- **NET.S02** NTP holds `wifi_mode_lock` for its whole attempt (up to 3 DNS servers × 500 ms + 5000 ms
  fetch); meanwhile WiFi's 1 s `ThreadSafeFlag` ticks collapse, so `WifiUptime` undercounts and
  `/status` shows `IPv4`/`Rssi` as null (`src/asy_ntp_client.py:433-440`).
- **NET.S03** `[x2]` NTP "stale after 3× interval" can never trigger: `ntp_sec_count` resets at every due
  resync, failed ones included, so `Synced` stays True forever after the first success — legacy-
  identical and pinned by `tests/test_asy_ntp_client.py:1388-1410` (`asy_ntp_client.py:456-471`).
- **NET.S04** `[x2]` The DNS client falls back to `8.8.8.8` and `1.1.1.1` after the DHCP server —
  undocumented in SPECIFICATION/BACKLOG, a network/privacy behaviour change vs legacy's system
  resolver (`src/asy_dns_client.py:20, 110`).
- **NET.S05** `get_dns_server_ip()` returns `None` whenever the lock is held when NTP samples it, so
  NTP silently uses only the public resolvers — fails on networks that block external DNS
  (`asy_ntp_client.py:431`).
- **NET.S06** `ntp_force_sync()` no longer clears `Synced` (legacy did): after an NTP-settings PUT with
  a bad host, local time and notifications keep running on the old sync (`asy_ntp_client.py:416-422`
  vs legacy `async_connect.py:129-135`).
- **NET.S07** `_poll_sta_connect_status` does not break on `STAT_GOT_IP`; every successful connect
  costs the full 5 s under the lock (`asy_wifi_service.py:616-621`).
- **NET.S08** `_run_hotspot_mode` repeats the full mode switch (deinit + new `WLAN`) on any tick where
  AP status ≠ `STAT_GOT_IP`, re-setting `hotspot_started_once` (`asy_wifi_service.py:570`).
- **NET.S09** A task restart during HOTSPOT forces `reconn_wifi` and resets `hotspot_started_once`,
  which differs from the comment at `:305` and A.4's "left as-is" (`asy_wifi_service.py:311`).
- **NET.S10** `captive_dns` receives with `recvfrom(4096)` per datagram (16× I.3's 256 B design bound,
  contradicting I.2's "small, fixed" claim); NTP allocates 1024 B for a 48 B reply
  (`src/captive_dns.py:98`; `asy_ntp_client.py:185`).
- **NET.S11** Captive DNS polls at 50 Hz forever while the hotspot is up (`timeout_ms=-1` over a 20 ms
  `ipoll(0)` loop) — the idle-poll cost F.5.9 fixed for UART (`src/asy_udp_socket.py:126`).
- **NET.S12** Captive DNS answers every QTYPE (AAAA, HTTPS) with an A record while echoing the QTYPE,
  doesn't check QR, and builds f-strings for `pr.evt` on every query regardless of level
  (`captive_dns.py:109-121` f-strings, `:170-171` QR/opcode parsing, `:203-210` A answer).
- **NET.S13** `_fetch_ntp_reply` has no `disconnect()` in `finally`, unlike `resolve_ipv4`; a cancel
  mid-fetch leaks a UDP PCB until GC (`asy_ntp_client.py:183-188` vs `asy_dns_client.py:117-120`).
- **NET.S14** DNS query building: trailing dot/empty label → malformed query; no 255-octet QNAME check
  (`NTP_Host` allows 1024); TC bit unchecked; only answers starting with a compression pointer parsed
  (`asy_dns_client.py:44-62` query building, `:71-85` response parsing).
- **NET.S15** `get_wlan_rssi()` prints an error on every `/status` in hotspot mode; `WifiUptime`/
  `Connected` count up in AP mode (`asy_wifi_service.py:760`; AP counting `:503-512, 851-858`).
- **NET.S16** `PW` accepts 8-63 characters (excludes a raw 64-hex PSK); the masked `"********"` from a
  GET, if PUT back, would be stored as the password — check the JS client (`WEB.T02`)
  (`asy_wifi_service.py:46, 197-201`).
- **NET.S17** Bounds vs legacy: Hostname 1-63 → 1-32, SSID min 2 → 0, `PW` `""` = open network (legacy
  `""` meant "unchanged"), `HotspotPW` build-time only (not in any `SettingsGroup`,
  `buildgen/codegen.py:607`).
- **NET.S18** Comment drift: `asy_udp_socket.py:176` names a nonexistent `_open()`;
  `asy_wifi_service.py:168-169` mentions a future "combined Networking endpoint".
- **NET.S19** NTP discards the reply's source address and sends an all-zero transmit timestamp, so an
  origin-timestamp check is impossible; whether lwIP's connected-PCB filter already enforces the source
  is unverified (`asy_ntp_client.py:183-184`) (feeds `SEC.T05`).
- **NET.S20** The hotspot AP is configured with `essid`/`password` only, so its auth mode is the cyw43
  default — verify on 1.29 that it is WPA2-AES, not mixed/open (`asy_wifi_service.py:384`).

Quality measure: complete phase × event table for WiFi; lock-hold table; every seed resolved.

---

### 5.9 REST — Web server and HTTP surface

**Goal**: every byte a client sends is bounded before it is allocated; every route validates and
answers with the documented envelope; the server survives hostile and pathological clients; our
wrappers cover every gap in vendored Microdot (A.5).
**References**: A.5, A.8, H.6, H.7, I.3, I.6; `ext/microdot.py` v2.6.2; MicroPython
`extmod/asyncio/stream.py`, `py/stream.c` at `v1.29.0`.

Topics:
- [ ] **REST.T01** (with `MEM.T03`, `SEC.T05`) Allocation-before-check sweep: Content-Length (negative, huge, non-numeric,
      duplicate), request line and header line length, header count, query string, JSON depth/size,
      path length — each against Microdot's actual order of operations.
- [ ] **REST.T02** Route table: every GET/PUT, validation, envelope, status codes, HEAD/OPTIONS
      behaviour, unknown keys, non-object bodies, wrong Content-Type.
- [ ] **REST.T03** `PUT /sensors` vs settings-group routes: guarding, post hooks, result shape (D.10) —
      owned by `XCUT.T11` (with `CORE.T04`, `CORE.S06`).
- [ ] **REST.T04** (with `SEC.T02`, `PERF.T03`, `HW.T02`) Command fields: `SystemCmd`, `lightCmdLED`, `PauseTime`, `ResetErrors` — validation,
      Invalid vs Failed semantics, blocking duration, idempotency, confirmation for irreversible ones.
- [ ] **REST.T05** Streaming (`_PieceWriter`): piece bound in bytes (not characters), exact
      Content-Length, per-source guarding in `/status`.
- [ ] **REST.T06** (budget in `PERF.T02`) Connection lifecycle: `_TimeoutStreamProxy`, `outer_cap_s`, `max_connections`,
      backlog, slot release lag (H.7.1), stream closing on HEAD/abort/error.
- [ ] **REST.T07** Static serving: `..` handling, `.gz` lookup, 302-in-hotspot, caching headers,
      Content-Type/charset.
- [ ] **REST.T08** (with `XCUT.T07`, `CORE.S11`) Logging from the webserver: `wrn_s` without `repeat=` on routine idle/aborted
      connections vs FRAM ring churn.
- [ ] **REST.T09** Verify A.5's gap list against v2.6.2 source and note what v2.7.0 changes; confirm
      every fix stays outside `ext/`.
- [ ] **REST.T10** GET routes with hardware side effects and latency: `/sensors` (live register
      snapshots, ISL re-apply), `/status` (`rssi`, `ifconfig`, every logger's `get_log()`) — worst-case
      duration vs `per_call_timeout_s`/`outer_cap_s`, bus-lock contention under 6 clients (with
      `SENS.T16`, `PERF.T02`/`T04`).
- [ ] **REST.T11** JSON-safety sweep: every float that can reach a body must be finite (bare `nan`/`inf`
      from MicroPython `json`, F.1) — BMP compensation, ISL HSB/CCT, `math_helpers`, NTP/notification
      values, stored config; non-ASCII SSID/hostname (with `XCUT.T23`).
- [ ] **REST.T12** HTTP framing interop: `Expect: 100-continue` (curl, bodies > 1 KB), `Transfer-Encoding:
      chunked` without Content-Length (→ `body=b''`, `ext/microdot.py:423-430`), keep-alive/pipelining vs
      HTTP/1.0, absolute-form targets, percent-encoded paths (routes match undecoded), query strings on
      API routes, gzip regardless of `Accept-Encoding`.
- [ ] **REST.T13** Client-triggerable stdout: Microdot `print_exception()` for every unparsable request
      (`ext/microdot.py:1407-1408`) plus every `pr.*` print; on rp2 1.29 `mp_usbd_cdc_tx_strn` may wait up
      to `MICROPY_HW_USB_CDC_TX_TIMEOUT` per print when a CDC host is attached but not reading — a
      LAN-triggerable loop stall on the bench (with `PERF.T11`, `PLAT.T03`).

Seeds:
- **REST.S01** `Content-Length: -1` appears to bypass the 2048 B body cap: `Request.create` does
  `int(value)` and reads the body when `content_length <= max_body_length`; `readexactly(-1)` becomes
  `read(-1)` = read-all (up to ~`TCP_WND` 6400 B), and a follow-up negative read hits `py/stream.c`'s
  `MemoryError` path — i.e. a client-triggered `MemoryError`, contradicting I.6 and the zero-
  `MemoryError` bar (`ext/microdot.py:417-426`; upstream `extmod/asyncio/stream.py:41-52`). Not executed. Any fix
  must live outside `ext/`.
- **REST.S02** Header lines and header count are unbounded before Microdot's `max_readline` check,
  because asyncio `readline()` grows with O(n²) copies until `\n`; bounded only by the 5 s per-call and
  15 s outer timeouts; untested (`ext/microdot.py:412-421, 533-537`).
- **REST.S03** `[x2]` (owned by `XCUT.T11`) `_put_sensors` calls `module._set_dict_cfg()` directly, bypassing
  `ar.handle_set_cmd` (no errno-99 guard, no post hooks), unlike the flat routes
  (`src/asy_webserver_service.py:420-432`).
- **REST.S04** `[x2]` `_put_status` resets every error source sequentially with no guard: an exception
  leaves a partial reset and a 500; no confirmation for an irreversible evidence wipe (`:631-637`).
- **REST.S05** WEBSERVER `wrn_s` calls never pass `repeat=`, so every idle/reclaimed connection (browser
  speculative preconnects) spends a FRAM ring slot; same for DNSSRV (`:254, :715-724`;
  `src/captive_dns.py:119, 123`).
- **REST.S06** `_PieceWriter` counts characters, not bytes: non-ASCII SSID/hostname values make pieces
  larger than `chunk_bytes` (`:145-148`).
- **REST.S07** HEAD requests and aborted static responses never `aclose()` the opened stream (relies on
  GC) (`asy_webserver_service.py:655-667`; `ext/microdot.py:684-699`).
- **REST.S08** `[x2]` No `Cache-Control`/ETag on static files: every visit re-downloads index and
  `app.js` on a CPU-bound server with a ceiling of 6 connections (`asy_webserver_service.py:649-667`).
- **REST.S09** `[x3]` REST `lightCmdLED` goes through `request_signal()`, which spins until any running
  ramp ends; with `t` up to 60 s a request can exceed `outer_cap_s` = 15 s, where legacy answered
  "LED is busy" (error 8) at once; `led_signal()`/`start_asy_ext_cmd_watcher` look dead
  (`buildgen/codegen.py:555`; `src/asy_neopixel_driver.py:104, 137-153`).
- **REST.S10** `lightCmdLED` out-of-range/missing keys yield per-field `"Failed"` while `PauseTime`
  yields `"Invalid"`; H.6 reserves Invalid for structurally wrong payloads (`asy_webserver_service.py:
  533-566`).
- **REST.S11** Comment drift: `asy_webserver_service.py:725` "see module docstring" (which says
  nothing about it); I.6 still says `max_connections` is 4 and 4 × 2048 = 8192 B (now 6 → 12288 B).
- **REST.S12** `_put_status` returns code 0 with no `result` map, silently ignoring unknown keys and any
  `ResetErrors` value other than `True`, unlike every other PUT's per-field verdicts (D.10)
  (`asy_webserver_service.py:631-639`).
- **REST.S13** `_put_sensors` drops unknown sensor names and non-dict sub-objects with no result entry;
  the comment cites the per-key "Invalid" convention but nothing is emitted, so a typo returns
  `{"res":"OK","result":{}}` (`:425-430`).

Quality measure: an adversarial-client test matrix (mock + twin) with the `MemoryError` gates active;
every seed resolved.

---

### 5.10 LED — Notification and LED

**Goal**: LED arbitration and threshold signalling are bounded, non-blocking, and legacy-faithful.
**References**: A.4 (split, sequencing, midnight-window decision), `DEVICE_REFERENCE.md`, legacy
`neopixel_signal.py`.

Topics:
- [ ] **LED.T01** (owns `REST.S09`/`LED.S01`) Signal arbitration (internal vs external), queued vs running semantics, busy
      behaviour, ramp timing, overlay.
- [ ] **LED.T02** Input sanitisation: `t`, colours, brightness, frequency — floors and ceilings.
- [ ] **LED.T03** `NotificationCoordinator` staged construction (`register`/`finalize`), buffered
      rejections, per-signal schema injection, check order and sleeps.
- [ ] **LED.T04** Failure isolation: can a bad source value kill `monitor_loop`?
- [ ] **LED.T05** Signal machinery lifecycle: `neopixel_signal` cancelled mid-ramp leaves the pixel lit and
      `start_signal_event` set, so the restarted task replays the old `rgbt`; `request_signal()` callers
      spin with no deadline whenever that task isn't running (`asy_neopixel_driver.py:145-153, 155-187`).
- [ ] **LED.T06** Notification inputs: freshness (old `TS` can still trigger, `XCUT.T17`), `None` vs 0,
      `>=`/`<=` at exactly the threshold, ordering and total duration with several signals in one window.
- [ ] **LED.T07** WS2812 contract: `bitstream` timing and IRQ-off window per `write()` during 20 Hz ramps,
      GRB ordering (`bpp=3`), 3.3 V data vs VIH at 5 V supply per board; missing datasheet (`SENS.S20`).

Seeds:
- **LED.S01** `request_signal()` and `_led_ext_signal_starter` busy-wait with `sleep(0)` for the whole
  length of a running signal; `t` has a floor but no ceiling; `neopixel_freq=0` raises
  `ZeroDivisionError` in `__init__` (`src/asy_neopixel_driver.py:68, 84-85, 148-149, 162-169`).
- **LED.S02** `float(value)` sits outside the `try` in `_check_one`; a non-numeric field would end
  `monitor_loop` (`src/asy_notification_service.py:218`).
- **LED.S03** An extra `2×FlashDur` sleep follows the *last* warning too (legacy slept only between);
  minor parity delta (`asy_notification_service.py:369-374`).
- **LED.S04** `DEVICE_REFERENCE.md` describes the WiFi LED as a static preference, but the code still
  toggles/flashes it with connection state, as legacy did (`DEVICE_REFERENCE.md:11` vs
  `asy_wifi_service.py:344, 527-536, 594`; doc half owned by `DOC.T10`).

Quality measure: every seed resolved; busy/queue semantics written down and tested.

---

### 5.11 GEN — Build generator and device definitions

**Goal**: `buildgen` fails loudly (only `BuildError`) on every malformed input, never emits code it has
not validated, and generates what Part L says for all 6 devices.
**References**: Parts L (all), K.3-K.8, C.14, H.5.1; `tests_scripts/test_buildgen_*.py`.

Topics:
- [ ] **GEN.T01** L.5 contract fuzz: every table/field of the TOML with wrong types/shapes → only
      `BuildError`, never a raw exception.
- [ ] **GEN.T02** Every TOML value that reaches generated source via `str()`/`repr()` is type-checked;
      the generated module is `ast.parse`/`compile`d before being returned.
- [ ] **GEN.T03** Tag grammars (`@wiring`, `@value-wiring`, `@limits`, `@requires`, `@web`,
      `@web-group`): scope detection, near-miss detection, NaN/inf, false positives on prose.
- [ ] **GEN.T04** Multi-instance correctness (`name_ext`): no generated reference to a bare
      driver-named global; definitions and codegen agree.
- [ ] **GEN.T05** Frozen-module set: `CORE_MODULES` vs codegen's imports, `TYPE_CHECKING` handling,
      `else:` branches, generated module included.
- [ ] **GEN.T06** Hand-maintained catalogs vs "one new file" (L.1 criterion 2): `buildspec.py`,
      `_SENSOR_DRIVERS`, `_ERRCOUNT_CATALOG`, `_CFGMGR_LABEL`, `twin_wiring.FIXED_ADDRESSES`, the twin CI
      suite's `_DRIVER_ERRCOUNT_NAME`/`_BUS_FAULT_OPS`, hand-mirrored constants
      (`_NTP_CHECK_TICK_S`, `_SERVER_OUTER_CAP_S`, `_WARN_SIGNAL_WEB_CATALOG`) — which are
      cross-tested, which silently drift (buildspec itself is SETTLED as hand-maintained).
- [ ] **GEN.T07** `pico_gpio.py` legality table vs RP2040 silicon (e.g. GP22/GP28 functions) — is the
      conservatism intended?
- [ ] **GEN.T08** `devices/*.toml`: values vs legacy pinning per unit, `SensorStation<Name>` rule,
      shared hotspot password, `timeout`/`frequency` vs `@requires`.
- [ ] **GEN.T09** `definitions.py`: ordering vs codegen, string `specialValues`, UTF-8 byte bounds,
      NaN/inf defaults, `defaultValue` kind check, display identity (file stem vs `SensorStation`).

Seeds:
- **GEN.S01** `_sgp_maintenance_status()` uses the bare global `sgp40` whenever any sgp40 instance
  exists; the `multi_instance.toml` fixture (`sgp40_a`/`sgp40_b`) generates `assert sgp40 is not None`
  with no such global — a runtime `NameError` swallowed by `_write_guarded`, invisible to the smoke
  test (`buildgen/codegen.py:563-567`; `definitions.py:430`).
- **GEN.S02** `irq_pull_up` is never validated and is emitted with `str()`; `"no way"` produced invalid
  generated source that was returned without complaint — a crafted value injects code
  (`codegen.py:194-195`; `validate.py:386`).
- **GEN.S03** A TOML with no `[bus]` table crashes with a raw `KeyError`, though `validate.py:280-282`
  declares that shape legal (`codegen.py:382, 489`).
- **GEN.S04** A non-table `wiring` (device or instance level) raises a raw `AttributeError`
  (`validate.py:645, 693-694`; `graph.py:146`; `codegen.py:111`; `model.py:213`).
- **GEN.S05** Stray `warn_*` keys are accepted on any instance and add dependency edges, but only the
  notification instance's reach codegen (`validate.py:646, 669-672`; `graph.py:170`).
- **GEN.S06** `{source, field}` value-wiring never checks `field` exists on the source's data, though
  L.6.3 says the build checks it (`validate.py:579-591`).
- **GEN.S07** The generated module's own `TYPE_CHECKING` block is frozen unstripped; the comment at
  `scripts/build_firmware.py:95-99` says there is nothing to strip (`codegen.py:336-343`).
- **GEN.S08** The `definitions.py` CLI path (used by `build_website.sh`) never builds
  `construction_order`, so sensor ordering can differ from codegen's (`definitions.py:522-524`).
- **GEN.S09** Codegen hardcodes `fram=` for device-level consumers and `conn.set_ext_led` instead of each
  tag's `target`; an instance-level setter-mode tag would validate and be silently dropped
  (`codegen.py:112, 429`).
- **GEN.S10** Fragility: `tag_comments.py:200` treats a column-0 comment inside a function body as
  module level; `requires_tag._coerce` and `web_tag._coerce_default_value` accept `nan`/`inf` (the
  latter would emit JSON `NaN` and break the inlined page, `web_tag.py:120-131`);
  `defaults.default_init_params` ignores keyword-only args (`defaults.py:346`); `schema_ast._eval_literal`
  can recurse unboundedly; `twin_wiring.py:219` and `definitions._coerce_special_value` raise raw
  `ValueError`.
- **GEN.S11** `frozen_modules.py:41` skips a whole `If` including its `orelse`; `:57` has no
  `SyntaxError → BuildError`; `CORE_MODULES` is a hand mirror of codegen's imports with no test.
- **GEN.S12** `scripts/_strip_type_checking.py:59-63` removes the `try: from typing import
  TYPE_CHECKING` guard unconditionally but keeps `if TYPE_CHECKING: … else:` and compound tests
  (not present in `src/` today).
- **GEN.S13** Dead generated global: `timers_running = ThreadSafeFlag()` is created in every generated
  module and never used (`codegen.py:367, 431`).
- **GEN.S14** Stale comments: `tag_comments.py:121-129, 142-143` ("`@web` planned"),
  `requires_tag.py:2, 323` (`_VAL_*`), `web_tag.py:21` ("see module docstring").

Quality measure: fuzz harness result (only `BuildError`); generated output compiles for fixtures;
every seed resolved.

---

### 5.12 TOOL — Toolchain installer and build overrides

**Goal**: the installer and overrides are correct, idempotent, safe for the host, reproducible, and
fail loudly.
**References**: Parts B.1-B.14, CLAUDE.md "Build-environment verification", dead-man's-switch rule.

Topics:
- [ ] **TOOL.T01** Every subprocess: argument quoting, secrets in argv/logs, `sudo` environment
      (proxy/CA variables dropped by `env_reset`?), error propagation.
- [ ] **TOOL.T02** Downloads: pinning, checksum/signature verification, version floating (Node,
      picotool tag selection, MicroPython tag vs SHA), `git fetch --tags --force`.
- [ ] **TOOL.T03** Bench tier: bridge creation/modification with no in-code dead-man's switch, MAC
      pinning, `br_netfilter` persistence, temp files, idempotency, `--skip-apt` interactions.
- [ ] **TOOL.T04** Overrides framework: anchor checks, generated board/variant dirs, lwIP ensemble
      checks vs `lib/lwip` `init.c`/`opt.h`, post-build verification, path quoting.
- [ ] **TOOL.T05** Two Unix-port variants: detection, rebuild on mismatch, cache interactions.
- [ ] **TOOL.T06** B.14.3 (`littlefs_flash_storage_size`, documented not implemented) — relevance to a
      1.26 → 1.29 reflash (seed `PAR.S10`).

Seeds:
- **TOOL.S01** The bench AP password is echoed in the full argv by `run()` and printed again, and sits
  on the process command line (`toolchain/setup_toolchain.py:111, 916-921, 924`).
- **TOOL.S02** `ensure_node` uses `next(...)` without a default (raw `StopIteration` if SHASUMS changes
  between two fetches); checksum from the same origin, no signature; version floats within v22
  (`setup_toolchain.py:998-1003`).
- **TOOL.S03** `ensure_bench_bridge()`'s creation path enslaves `eth0` (`nmcli connection up br0-eth0`)
  with no dead-man's switch armed — the exact operation behind the 2026-09-04 lockout; B.13's manual
  recovery script hardcodes the profile name "Wired connection 1" (unverified on trixie)
  (`setup_toolchain.py:896-925`).
- **TOOL.S04** `ensure_apt_packages` uses `sudo env DEBIAN_FRONTEND=…`, which likely drops proxy
  variables; `ensure_dialout_group` is skipped by `--skip-apt`; `ensure_br_netfilter` passes no `env=`
  and leaks its temp file if `sudo` fails (`setup_toolchain.py:689`).
- **TOOL.S05** `build_firmware.py` does not `.resolve()` `--toolchain-dir`; generated make/CMake
  `include` paths are unquoted, so relative paths or paths with spaces would break
  (`toolchain/micropython_overrides.py:78-83, 332-336`).

Quality measure: every subprocess call reviewed; the two chroot legs' owed-list in BACKLOG kept current.

---

### 5.13 SCR — Scripts and test orchestration

**Goal**: the orchestration scripts are the gates everything else trusts; they must fail closed,
never report green on a run that did less than it claims, and be safe to run on a dev box.
**References**: CLAUDE.md "Code quality tooling", Parts E.1-E.5, B.10-B.11, L.5.

Topics:
- [ ] **SCR.T01** `test.sh`: argument/env validation, parallelism probe, per-file timeout/retry,
      `MemoryError` gate, exit codes 0/1/3, annotation emission, backgrounded pytest tier, a file that
      runs zero tests, a file that `sys.exit(0)`s early.
- [ ] **SCR.T02** `lint.sh`/`typecheck.sh`: scope lists vs CLAUDE.md's eight directories; the
      `method-assign` and `gc.collect()` grep guards; stub repair conditions.
- [ ] **SCR.T03** `build_firmware.py`, `build_website.sh`, `build_frozen_html.sh`,
      `_strip_type_checking.py`, `_generate_sensortask_modules.py`: correctness, determinism
      (`gzip -n`), fail-loud, shared outputs.
- [ ] **SCR.T04** Twin CI suite and runners: fixed ports (18080, 53), run list, gates, log handling;
      Unix-port variant probe present only in `test.sh`.
- [ ] **SCR.T05** Hardware runners and `_require_clean_hardware_run.sh`: flag parsing, `-m` last-wins,
      skip whitelist, messages.
- [ ] **SCR.T06** Concurrency safety of local runs: shared mutable outputs (`frozen_modules/`,
      `build/generated_src/`, twin state files, `tests/_tmp`, rp2/mpy-cross build dirs).
- [ ] **SCR.T07** `setcap cap_net_bind_service` on a general-purpose interpreter binary (three
      scripts) — host-security side effect.
- [ ] **SCR.T08** Shell quality beyond shellcheck: `set -euo pipefail`, traps, temp-file cleanup,
      quoting.

Seeds:
- **SCR.S01** `_require_clean_hardware_run.sh:106` prints a truncated sentence ("…flags) to."); the
  `--soak-tier=x` form is not recognised (`:20-23`); a caller's `-m` replaces the runner's soak
  exclusion (pytest `-m` is last-wins).
- **SCR.S02** No zero-tests-ran guard: `microtest` prints `0/0 passed` and exits 0, which `test.sh`
  records as PASS (`scripts/test.sh:373-376`).
- **SCR.S03** Stale comment `test.sh:296` (pytest "right after the toolchain check"); B.10.1 says
  "180 s × 3" where the default is 240 (`test.sh:314`).
- **SCR.S04** `build_frozen_html.sh:110` runs `gzip -9` without `-n` (mtime embedded → non-deterministic
  firmware images).
- **SCR.S05** The Unix-port variant probe exists only in `test.sh`; `run_digital_twin_ci.sh`,
  `run_unix_port_integration.sh` and `cross_browser_smoke.mjs` only check `-x`.
- **SCR.S06** `setcap cap_net_bind_service` is applied to the Unix-port interpreter (`test.sh:284-288`
  and two other scripts), letting any local user bind privileged ports with it.

Quality measure: each gate script has a test proving it fails on each failure class it claims to
catch (many already exist in `tests_scripts/` — audit their bite).

---

### 5.14 CI — CI, dependency pins and supply chain

**Goal**: CI runs what the docs say, on the paths that can break it, reproducibly, with least
privilege, and a third party's outage never reads as a red test (CLAUDE.md).
**References**: `.github/workflows/ci.yml`, composite action, `zizmor.yml`, Parts B.10, H.8.

Topics:
- [ ] **CI.T01** Job graph: `needs`/`if` edges vs CLAUDE.md's sequencing-not-gating rule; timeouts;
      matrices; `continue-on-error` semantics; concurrency groups.
- [ ] **CI.T02** Path filters: the web tier's filter vs every input of the website build and the live
      twin tests.
- [ ] **CI.T03** Caching: keys vs every input that feeds compiled binaries; save-on-failure
      behaviour; misleading downstream errors on a cold cache.
- [ ] **CI.T04** Pins: uv itself, `uv sync --locked/--frozen`, `pytest`/`mpremote` unpinned vs the
      "every tool pinned" comment, stub post-release floating, `coverage` in a PEP 723 script,
      `@types/node` vs `.nvmrc`, sdist-only `actionlint-py` fetching a binary, micromamba/Firefox
      unpinned, hardcoded `amd64`.
- [ ] **CI.T05** mypy scope in CI vs `typecheck.sh` defaults vs B.15.
- [ ] **CI.T06** Permissions, credentials persistence, SHA vs tag pinning policy, no Dependabot
      (manual SHA bumps).
- [ ] **CI.T07** Hardcoded 6-device matrices vs L.1 criterion 2 (a new device = one new file).
- [ ] **CI.T08** Config-file comment cap: which config files are in the swept set (PQ8).

Seeds:
- **CI.S01** The toolchain cache key hashes `versions.toml` and `setup_toolchain.py` but not
  `toolchain/micropython_overrides.py`, whose `unix_kbd_intr` override is compiled into the cached
  binary (`.github/actions/setup-micropython-toolchain/action.yml:38`).
- **CI.S02** `[x2]` The `web-changes` filter omits `src/**`, `buildgen/**`, `devices/**`,
  `digital_twin/**`, `toolchain/**`, yet the live-backend twin tests and generated definitions depend
  on them (`ci.yml:42-58`).
- **CI.S03** `lint-and-typecheck` narrows the main mypy pass to `src tests tests_hardware/device_scripts`
  (`ci.yml:339`), while `typecheck.sh:105-107`'s comment says CI passes `src tests`.
- **CI.S04** `pip install uv` is unpinned in every lane, and `uv sync` runs without `--locked`, so a
  drifted lock re-resolves silently (`ci.yml:323`; `action.yml:18`).
- **CI.S05** `[x2]` `pytest` and `mpremote` are unpinned in `pyproject.toml` despite its "PINNED like every
  tool" comment; the hardware harness depends on mpremote's exact raw-REPL/soft-reset behaviour.
- **CI.S06** `setup_cross_browser_toolchain.sh:159` fetches micromamba `latest` with no checksum;
  Firefox/geckodriver unpinned (`:162`); `arch=amd64` hardcoded (`:139`); the Firefox cache key is a
  fixed string (`ci.yml:301-305`).
- **CI.S07** `package.json` pins `@types/node ^26` while `.nvmrc` pins Node 22.
- **CI.S08** The composite action's description lists six callers; there are nine. `pyproject.toml:233`
  says "three known credential sites", but S105/S106 are exempted in more files.
- **CI.S09** `actions/cache` saves only on job success: a cold-cache `unit-tests` failure makes
  `firmware-build-verify` (`!cancelled()`) fail with a misleading "no toolchain found" (inferred).
- **CI.S10** Comment blocks over 3 lines in files outside CLAUDE.md's swept config list: `.gitignore`
  (from lines 27, 33, 75, 84), `tsconfig.json` (11, 29), `tsconfig.node.json` (2, 17); `.gitignore:75`
  still names the retired `run_wozi_integration.py`.

Quality measure: every job's actual behaviour matches B.10/B.10.1; every pin decision recorded.

---

### 5.15 WEB — Website

**Goal**: the UI is correct, robust against a slow/failing device, mirrors `src/` validation exactly
(Part G.2 mirror obligation), is accessible, and its build is deterministic and fail-loud.
**References**: Parts H (all), A.9, G.2, L.4 (definitions generation).

Topics:
- [ ] **WEB.T01** Apply/PUT semantics: sparse bodies, dispatch toggles, baselines, result
      reconciliation and colouring, repeated Applies.
- [ ] **WEB.T02** Input parsing: whitespace, hex/exponent, locale decimal comma, empty vs zero, byte
      vs character length for strings.
- [ ] **WEB.T03** Request lifecycle: timeouts (headers vs body), single-flight queue, section switch
      cancellation, hidden-tab polling, client/server timeout race.
- [ ] **WEB.T04** Mock server ↔ `src/` parity (G.2): every validation rule, envelope, unknown key,
      malformed body, Content-Type gate, failure injections that model fixed server gaps.
- [ ] **WEB.T05** Definitions: hand-written wozi/dev vs generated (order-sensitive), `validateDefinitions`
      strictness vs H.4's claim, degraded `/status` sources.
- [ ] **WEB.T06** Build: bundle order, import stripping, duplicate exports, inlining/escaping, the
      staging test's bite.
- [ ] **WEB.T07** Accessibility: ids, labels, drawer focus/inert, contrast (light and dark), colour-only
      information, password inputs, `color-scheme`, reduced motion.
- [ ] **WEB.T08** Security: no-`innerHTML` rule enforcement, selector injection, CSRF/DNS rebinding/
      clickjacking posture (PQ5), password `autocomplete`.
- [ ] **WEB.T09** Browser support floor vs features used (media-range syntax, `replaceChildren`,
      private fields, `??=`).
- [ ] **WEB.T10** Test coverage: live PUT matrix per device (dev/ISL29125), live tests that skip-and-
      pass without the toolchain, runtime DOM validation.

Seeds:
- **WEB.S01** After Apply a settings card is not rebuilt, so a dispatch toggle (`SGPResetVOC`,
  `ISLCalibrate`) stays On and its baseline moves to true; the next Apply on that card resends it and
  resets the VOC algorithm/backup again (`js/render.js:81, 252, 321-335`).
- **WEB.S02** Dispatch toggles in the Off position are always sent, so an Apply can never report
  "Nothing to submit" (`render.js:81`).
- **WEB.S03** A whitespace-only number field submits 0 (`Number(" ") === 0`); hex and `1e3` pass
  client-side; a decimal comma is sent as a string (`render.js:23-30, 101-102`).
- **WEB.S04** Per-field status colours go stale: fields not in the latest result keep the previous
  Apply's colour (`render.js:164-169`).
- **WEB.S05** `fetchWithTimeout` clears its timer once headers arrive; `response.text()` is unbounded,
  so a mid-body stall blocks the global single-flight queue for every section
  (`js/poll-manager.js:32-34, 63`).
- **WEB.S06** Client 15000 ms starts before connect, server `outer_cap_s` 15.0 at accept, so the client
  nearly always aborts first — undercutting H.4's stated rationale.
- **WEB.S07** Section switches never abort in-flight or queued requests; polling continues in hidden
  tabs on a server that saturates around ~2.2 requests/s (`poll-manager.js:126-131`).
- **WEB.S08** The errcount group is rebuilt every tick, losing keyboard focus; its rollup (history type)
  and row colour (`counter > 0`) can disagree (`render.js:296-312`; `js/templates.js:243-249` vs `:283`).
- **WEB.S09** A degraded `/status` source (`{"error":"unavailable"}`) renders as "—" with no signal.
- **WEB.S10** Latent: in-place caption refresh bypasses `resolveFieldValue` (`render.js:327, 331`);
  the baseline snapshot is frozen at first render (`:336`); an Apply with no `rest.put` silently does
  nothing and `validateDefinitions` doesn't require it (`:197-199`).
- **WEB.S11** `console.error("Poll failed:")`, cited by H.8 as the loop's only diagnostic, is dead:
  `fetchOnce` catches everything (`render.js:350-375`).
- **WEB.S12** Mock divergences: WiFi UTF-8 byte bounds not mirrored (`js/mock-server.js:59-61` counts
  UTF-16); unknown `/sensors` sub-key silently ignored vs the server's Invalid + errno 10, with a
  comment claiming parity (`:130-131`); `partial-result` injection models a server gap that is fixed
  (`render.js:133-135`, `mock-server.js:252-254`); malformed/non-object bodies behave differently
  (`:375, 383`); recursive jitter corrupts time structs and random-walks `BootSignature`/`NtpLastSync`
  (`:289-291`, stale comment `:481`).
- **WEB.S13** `[x3]` wozi/dev `html/definitions/*.json` are hand-written; the generator's output equals
  them only order-insensitively — field order differs (e.g. wozi SCD30), so generated devices show
  fields in a different order; the golden test is order-insensitive
  (`tests_scripts/test_buildgen_definitions.py:40-69`).
- **WEB.S14** H.2 claims `build_website.sh` mechanically re-checks bundle order; no such check exists,
  and the order is violated (`templates.js` before `definitions.js`, `scripts/build_website.sh:78`),
  harmless only via hoisting; single-line `grep -v` import stripping; the staging test passes on a
  comment mention (`tests_scripts/test_build_website_sh.py:117-133`, stale comment `:26-29`).
- **WEB.S15** Duplicate DOM ids (`field-${key}` not namespaced by group: dev's `SampleInterv`/`FiltCoeff`
  twice); dangling `label htmlFor` targets (`templates.js:61, 71-78, 135-138`).
- **WEB.S16** Drawer not `inert` when closed, no focus management, static `aria-label`; colour-only
  errcount history; light-mode contrast below 4.5:1 (success 3.13, danger 3.74, warn 4.01; borders
  1.39); `input[type=password]` unstyled (`html/style.css:261-263`); no `color-scheme`.
- **WEB.S17** No ESLint rule enforces the no-`innerHTML` rule; selectors interpolate keys without
  `CSS.escape`; masked password inputs lack `autocomplete` (`templates.js:160`).
- **WEB.S18** Duplication/dead: `selectSection` and the startup banner duplicated in `js/app.js` and
  `js/main.js` (BACKLOG); `PollManager.isBusy` test-only; `"settings"`/`"none"` pollGroups identical;
  stale spec pointers (`templates.js:8, 340`; `render.js:127`); `validateDefinitions` shallow — an
  unknown kind renders as a text input (`templates.js:158`).
- **WEB.S19** `html/index.html:40-43` has a 4-line `//` block (comment cap).
- **WEB.S20** `/system`'s `build` entry is rendered nowhere, while H.1 says every REST function is
  reachable in the GUI (L.7 may say otherwise — reconcile).

Quality measure: every seed resolved; mock ↔ src parity table; axe-style runtime check result.

---

### 5.16 TEST — Software test tiers

**Goal**: the suites prove what their names claim; failures are loud; no test is vacuous,
tautological, or propped up by `gc.collect()`; tier obligations (CLAUDE.md bus-hazard rule, E.6.6
parity) are met or recorded.
**References**: Parts E (all), K.6, C.11.1, C.12; CLAUDE.md hang/segfault/memory rules.

Topics:
- [ ] **TEST.T01** Vacuity sweep: tautologies, swallowed exceptions, negative-only assertions,
      early-return skips counted as PASS, overclaiming names.
- [ ] **TEST.T02** Mutation/clamp-removal sweeps over the guards named in the seeds, then broadly.
- [ ] **TEST.T03** `gc.collect()` and absolute heap bounds in tests/twin vs CLAUDE.md and E.8; root-
      cause any `MemoryError` a manual collect is hiding.
- [ ] **TEST.T04** Timing sensitivity: wall-clock bounds under parallelism, fixed sleeps, unbounded
      `asyncio.run()` helpers.
- [ ] **TEST.T05** Mock ↔ twin semantic divergences (reset returns vs raises, WDT validation,
      `Pin.init` pull, IRQ edges, `scan()`, RTC set return).
- [ ] **TEST.T06** Meta-tests: which CLAUDE.md rules are machine-enforced vs review-only; propose
      guards for review-only ones (four-tier bus-hazard rule, nested `asyncio.run`, port/scratch-key
      disjointness, `ALL_CHECKS` completeness, `gc.collect()` in tests/twin).
- [ ] **TEST.T07** Shared mutable class-level state across tests in one process + dict-order execution.
- [ ] **TEST.T08** Duplication of helpers (raise-on-arm context managers, `run()`, `_wait_until`).
- [ ] **TEST.T09** Coverage: generated modules untraced; E.5.1's false-negative categories re-checked.
- [ ] **TEST.T10** `tests_js/`: live tests' skip behaviour, fixture reliance on hand-written
      definitions, mock-only coverage for dev fields.
- [ ] **TEST.T11** Private-attribute coupling in tests (refactor fragility) — accepted cost or not.

Seeds:
- **TEST.S01** Tautology: `test_*_bus_membership_matches_the_real_toml_group` is registered only when
  `len(attachments) >= 2` and then asserts exactly that (`tests/test_bus_hazard_generated.py:108-113`).
- **TEST.S02** `scenario_each_occupant_never_touches_an_unexpected_address` swallows exceptions and
  asserts only `touched <= allowed`; an early raise leaves the empty set, which passes
  (`tests/_bus_hazard_catalog.py`).
- **TEST.S03** Step-bound override tests cannot fail: their scripted deltas lie inside both the
  overridden and the default bounds; comments say otherwise (`tests/test_digital_twin_scd30.py:202`;
  `tests/test_digital_twin_bmp3xx.py:151`).
- **TEST.S04** `_scenario_bus_fault_degrades` injects SGP40 faults, starts only the webserver, and GETs
  `/measurements`, which doesn't touch the bus — the fault is probably never consumed; its comment
  about `tests/machine.py` lacking a fault surface is stale (`tests/_digital_twin_construction_scenarios.py`).
- **TEST.S05** The reserved-address check runs on constants defined in the test file itself, with its
  own copy of the range logic (`tests/test_bus_hazard_multi_device.py:63-66, 385`).
- **TEST.S06** The stagger no-coincidence proof re-implements `1000 // (n+1)`; no test reads the real
  `sequencer_timer.period` (`tests_scripts/test_timer_stagger_no_coincidence.py`;
  `src/system_service.py:159`).
- **TEST.S07** `_uart_comm_harness.build_pair()` discards `Pair.setup()`'s result (~60 call sites);
  negative-only tests would pass on a failed setup (`tests/test_asy_uart_comm.py:686-691`).
- **TEST.S08** Overclaiming names in `_sensortask_scenarios.py` (`…light_cmd_led_dispatches_to_the_real_
  pixel_driver`, `…round_trips_a_real_scd30_field_through_the_real_driver` assert only "Valid").
- **TEST.S09** Early `return` when a device lacks a module counts as PASS
  (`tests/_sensortask_scenarios.py:289, 890`); catalog no-op branches likewise.
- **TEST.S10** The cross-occupant write scenario uses `writers[0]` only; dev ISL29125's
  write-vs-siblings is never generated.
- **TEST.S11** `gc.collect()` added as a `MemoryError` workaround in tests
  (`tests/test_digital_twin_sensortask_integration.py:543-546, 627, 705, 779`;
  `tests/_webserver_concurrency_scenarios.py:861`; `tests/test_fram_integration.py:157-177`) —
  MicroPython collects on allocation failure anyway, so a collect that prevents a `MemoryError` points
  at retention or fragmentation.
- **TEST.S12** Absolute heap bounds against E.8's "a leak is a rate" (`tests/test_asy_webserver_service.py:
  1833`; `tests/test_digital_twin_uart_link.py` `_hammer_with_the_graph_running`).
- **TEST.S13** Coverage traces `src/` and `digital_twin/` only; generated `sensortask_*.py` gets none.
- **TEST.S14** Tight wall-clock bounds under 1-4× core parallelism (`test_asy_dns_client.py:332`,
  `test_captive_dns.py:482`, `test_asy_notification_service.py:1268`, `test_asy_udp_socket.py:926,
  994, 1350`); fixed `sleep(1.0)` for bind; 43 of 47 local `run()` helpers unbounded.
- **TEST.S15** Mock/twin divergences: `reset()` returns in `tests/machine.py:700` but raises in the twin;
  mock WDT accepts any timeout/id; mock `Pin.init()` drops `pull` (`:51-54`); mock `trigger_irq()` ignores
  edge direction; mock `scan()` lists only seeded addresses.
- **TEST.S16** Helper bug suspicion: `AdversarialPeer.recv()` tests `poller.ipoll(0)` for truthiness,
  which this build reports as ready every tick (`tests/test_asy_udp_socket.py:290` vs
  `tests/test_asy_dns_client.py:350-353`).
- **TEST.S17** `test_reset_call_site_invariant.py` scans `src/` only; `WDT()` now lives in generated code;
  aliased imports (`from machine import reset`) escape the substring match.
- **TEST.S18** Duplication: 7 copies of the Timer raise-on-arm context manager; 47 local `run()`s; 20
  files with their own `run_timed`/`_wait_until`/`_cancel`.
- **TEST.S19** Live PUT matrix covers wozi only (`tests_js/live-backend-put-matrix.test.js:58`); live
  tests skip-and-pass without the toolchain (`tests_js/live-backend.test.js:13-16`).
- **TEST.S20** Only ISL29125 has a C.11.1 conformance probe; SCD30, SGP40, BMP3xx and FRAM fakes have
  none and nothing requires one.
- **TEST.S21** E.1 says TCP port bases lie in 17400-19999, but `_webserver_concurrency_scenarios.py:77`
  allocates `19700+200*i`, reaching 20700+.
- **TEST.S22** The comment-cap gate counts physical lines, and E501 is ignored, so a docstring can pack
  a paragraph onto one 400-700-character line and pass (`digital_twin/_fault_injection.py:3`,
  `digital_twin/run_generic_integration.py:1-2`, `tests/test_digital_twin_run_generic_integration.py:1-2`,
  `buildgen/twin_wiring.py:1-2, 195-196`, `scripts/_digital_twin_ci_suite.py:5-7`,
  `scripts/_render_coverage.py:6-7`) — owner decision on a character bound (PQ8).

Quality measure: every seed resolved; a mutation-sweep report per `src/` module; a list of CLAUDE.md
rules with their enforcing test (or "review-only, accepted").

---

### 5.17 TWIN — Digital twin

**Goal**: each fake models the real chip/port faithfully where tests depend on it, and every
known infidelity is documented where a test author will see it.
**References**: `digital_twin/README.md`, Parts A.10, C.11.1, E.6.5, E.7-E.9.

Topics:
- [ ] **TWIN.T01** Per chip fake: behaviours modelled vs datasheet (command gating, CRC on written
      arguments, execution-time NAKs, general call, soft reset, measurement interval 0).
- [ ] **TWIN.T02** Fake `machine`: Timer as asyncio task (no soft-callback drop), WDT enforcement,
      reset/bootloader exceptions, RTC return value, I2C bus-level faults (no busy knob).
- [ ] **TWIN.T03** Fake `network`: connect phase timing, AP-mode config validation.
- [ ] **TWIN.T04** FRAM fake: framing inferred from `write()` pairing instead of CS; wraparound;
      out-of-range writes growing the buffer.
- [ ] **TWIN.T05** Fault-injection catalogue completeness vs what tests need (e.g. no BMP `writeto` hang).
- [ ] **TWIN.T06** 64-bit, non-frozen heap caveat applied to every twin-tier allocation assertion (E.8).
- [ ] **TWIN.T07** Unix-port helper modules (`unix_port_gc_unwedge.py`, `unix_port_poll_prewarm.py`,
      `_unix_port_udp_addr_shim.py`) — still needed after the root-cause fixes?

Seeds:
- **TWIN.S01** SCD30 fake produces readings regardless of start/stop continuous measurement, never checks
  argument CRCs, accepts interval 0 (a 0 ms periodic timer), treats soft reset as a no-op
  (`digital_twin/_scd30_chip.py`).
- **TWIN.S02** SGP40 fake models no command execution time and doesn't validate compensation-word CRCs;
  the twin's general call reaches no chip, so the SGP40 self-reset is unmodelled
  (`digital_twin/_sgp40_chip.py`; `digital_twin/machine.py`).
- **TWIN.S03** BMP3xx fake: chip ID 0x60 only; no `writeto` hang knob.
- **TWIN.S04** FRAM fakes (mock and twin) infer transaction framing from `write()` pairing, not CS, so a
  single write carrying opcode+address+data would lose the data; no wraparound.
- **TWIN.S05** Twin `RTC.datetime(set)` returns the tuple where the real call returns `None`; twin
  `network.py` validates no AP-mode config.
- **TWIN.S06** `digital_twin/README.md:107-108` says `WLAN.connect()` connects "immediately", but
  `digital_twin/network.py` uses a 0.7 s async phase.

Quality measure: an infidelity table in `digital_twin/README.md`, each row either fixed or accepted.

---

### 5.18 HW — Real-hardware tier (desk review; execution gated)

**Goal**: the hardware tier is safe for the board, the host and the evidence; its tests assert what
they claim; its docs are current. Desk review needs no go-ahead; anything touching the board or bench
network does (CLAUDE.md), and is otherwise queued in `REAL_HARDWARE_TEST_QUEUE.md`.
**References**: `tests_hardware/README.md`, Parts E.6, E.8, E.9, B.12, B.13; `REAL_HARDWARE_TEST_QUEUE.md`,
`HARDWARE_TEST_HANDOVER.md`, `HEAP_FRAGMENTATION_MEASUREMENTS.md`, `dev_legacy/README.md`.

Topics:
- [ ] **HW.T01** Wear: every flash/NVM/FRAM write reachable from each test and device script vs its
      markers (`persistence_write`, `scd30_extra_write`), including `device_scripts/`.
- [ ] **HW.T02** Evidence safety: automatic `errcount` snapshot before the first `ResetErrors`; which
      scripts overwrite production FRAM chunks; `_FRAM_BACKED_MODULES` completeness.
- [ ] **HW.T03** Board safety: scripts leaving non-volatile state behind (FRAM WPEN/BP, SCD30 NVM
      settings), watchdog-armed boards running long scripts, credentials files left on the board.
- [ ] **HW.T04** Host safety: bridge operations with/without a dead-man's switch; routine tests that
      rebuild the host environment (SSD wear, third-party dependency).
- [ ] **HW.T05** Oracle bite: every test's assertion vs its name; engagement floors for passive
      tail tests; `reset_cause()` checks.
- [ ] **HW.T06** Harness facts: what `hard_reset()` really does (mpremote source), out-of-band reset
      availability, raw-REPL side effects (stops `main.py` → WDT reset ~8 s later).
- [ ] **HW.T07** Bench-rig facts vs docs (MPRLS on i2c0? FRAM part number on dev).
- [ ] **HW.T08** Hardcoded pins/timeouts/addresses in device scripts vs `devices/dev.toml`.
- [ ] **HW.T09** Structural-exception claims (E.6.6, C.8, `tests_hardware/README.md` tenth pass)
      re-derived from source.
- [ ] **HW.T10** Queue and handover hygiene: rows that duplicate BACKLOG, row IDs cited from permanent
      code after deletion, state duplicated between queue and handover.
- [ ] **HW.T11** Bench credentials consistency (owner, 2026-09-25: low risk, **consistency not
      security**): throwaway bench credentials are generated or read at run time
      (`bench.ap_password()`) and never persisted in files; harmonise every script to that convention.

Seeds:
- **HW.S01** `tests_hardware/flash/test_toolchain_flash_boot.py:30-42` is unmarked and runs
  `setup_toolchain.py env --tier flash` (~481 s): git fetch, toolchain rebuild, `uv sync` into the venv
  pytest runs from, `npm ci`, Playwright — host SSD wear, a third-party dependency inside a hardware run.
- **HW.S02** `[x2]` SCD30 NVM *is* reachable over REST (`asy_scd30_driver.py:257-275` dispatch;
  `asy_webserver_service.py:431`), contradicting E.6.6 exception 2 (SPECIFICATION ~3203), C.8 (~2153),
  `tests_hardware/README.md:748, 1130, 1173, 1196, 1240` and
  `bench/test_sensor_config_push_over_real_hardware.py:22`; the manual tier even instructs it.
- **HW.S03** `manual/manual_persistence.py:37-47` sets SCD30 `MeasInt=7` with no restore; later
  SCD30 tests assume ~2 s (`device_scripts/scd30_real_irq_edge.py:11`).
- **HW.S04** The manual "FRAM" power-cycle test PUTs `WarnCO2=424242` (range 0..3000 → Invalid), the
  value lives in the flash config not FRAM, and it names the wrong chip (`manual_persistence.py:3,
  14, 18-19`).
- **HW.S05** `device_scripts/isl29125_mechanism_envelope.py:100-108, 150-162` makes ~5 flash writes
  under `neopixel_sweep` only; the marker-completeness guard excludes `device_scripts/`
  (`tests_scripts/test_persistence_write_marker_completeness.py:55`).
- **HW.S06** 80 `ResetErrors`/`reset_all_error_logs` sites, no automatic `errcount` snapshot;
  `bench/test_memory_stress_bench.py:120` resets at start; its `_FRAM_BACKED_MODULES` (`:22`) omits
  WIFI, NTP, WEBSERVER, DNSSRV, `CFGMGR_*`, `UART_*`.
- **HW.S07** `fram_write_protect_roundtrip.py` sets non-volatile WPEN|BP0|BP1 and restores only in
  `finally`; a WDT reset or killed mpremote would leave production FRAM silently write-protected.
- **HW.S08** `device_scripts/wifi_reconnect_after_failed_attempts_repro.py:9-10` persists a throwaway
  bench SSID/PSK in the file — owner: low risk, a consistency breach (see HW.T11), not a safety one;
  `dev_legacy/README.md:661` records the Pi's `eth0` MAC (minor, same topic).
- **HW.S09** `wifi_service_reconnect_repro.py` (queue F1) runs up to 13 min without feeding the
  watchdog that production arms (`codegen.py:381`), so it is likely reset ~8 s in, leaving
  `config_HWTEST_WIFI.cfg` (with the real WiFi password) behind.
- **HW.S10** `bench/test_hotspot_role_reversal.py:58-89` persists `SSID=""` and calls `ap_down()` before
  `yield`; a stage 1-2 failure skips the teardown and strands board and bench AP.
- **HW.S11** Four role-reversal tests assert nothing of their own (`pass`, a constant equal to itself,
  non-empty) (`test_hotspot_role_reversal.py:~124-150`).
- **HW.S12** `bus_topology_autodetect_and_hazard_sweep.py:33-44`: `_probe()` returns `None` for both NAK
  and ACK, so the address sweeps can't fail on either; self-hazard overlap unproven; `dev_legacy`
  lists an MPRLS on i2c0 while docs say "BMP3xx alone".
- **HW.S13** `bench/test_network_resilience.py:328-362` can't distinguish DNS garbage from silence;
  `tests_hardware/README.md` says DNAT-to-loopback does not deliver locally (671-679) yet calls the
  `RogueUdpResponder` tests unaffected (~990-1000).
- **HW.S14** Soak tests assert less than their names: no memory trend, no timing, "never observed"
  clock stretch; no engagement floor; `DebugLevel`-dependent; `is_reachable()` stops `main.py` and the
  WDT reboots ~8 s later (`bench/test_memory_stress_bench.py:136-174`,
  `flash/test_memory_stress.py:87-105`, `flash/test_bus_electrical_timing.py:83-93`).
- **HW.S15** Loose oracles: `"CFGMGR_" in log or "FRAM" in log` (`flash/test_reboot_persistence.py:66`,
  reused `test_network_resilience.py:312, 341`); watchdog-starvation doesn't check `reset_cause()`.
- **HW.S16** Orphan device scripts with no wrapper (`wifi_country_hostname_edge_values.py` whose both
  branches print PASS, the two WiFi repros, `heap_layout_after_full_boot_sequence.py`).
- **HW.S17** Doc drift: README:1354 "73" bench tests (85 now); MB85RS64V named for dev
  (MB85RS2MTA) at README:710, `flash/test_fram_storage.py:1`, `manual_persistence.py:3, 14`;
  `hard_reset()` described as DTR vs `machine.reset()`; stale `DebugLevel` comments
  (`test_reboot_persistence.py:52, 68, 77, 79`); README:503 rollover guidance; README:87 and
  `run_bench_soak_tests.sh:4` point at `conftest.py` for `SOAK_TIER_SECONDS` (it's `soak_tiers.py`);
  README:587 datasheet list omits isl29125; `bench_control.py:103-104` says OUTPUT/FORWARD.
- **HW.S18** Pins hardcoded in ~20 device scripts with no guard vs `devices/dev.toml`; two SGP40 scripts
  omit `timeout=200000` on i2c1 (`sgp40_voc_algorithm_quality.py:46`, `sgp40_fram_backup_restore.py:54`),
  possibly resetting SCD30's bus timeout on the per-bus singleton.
- **HW.S19** Silent assumptions: stable DUT DHCP address across resets, passwordless `sudo`,
  `mpremote_connect.sh` default `/dev/ttyACM0` may be the Arduino, fixed 2 s link-local sleep, the
  "> 45 s between reset and attach" trap unenforced.
- **HW.S20** `dev_legacy/README.md` stale: "MicroPython 1.28.0" (line 19), "Current bench state (as of
  2026-09-02)" (595-665), the superseded bench-frozen-firmware recipe.

Quality measure: desk findings resolved or queued; every silicon-needing check is a queue row with
flags and wear stated.

---

### 5.19 SEC — Security threat model (cross-cutting)

**Goal**: an explicit threat model (PQ5) and every exposure classified against it — defect, accepted
property (with the owner's decision recorded), or out of model.

Topics:
- [ ] **SEC.T01** Write the threat model: actors (LAN peer, browser page on the LAN via DNS rebinding,
      radio-range attacker in hotspot mode, local user on the dev/bench host, supply chain), assets
      (availability, config, FRAM evidence, flash/NVM endurance, credentials).
- [ ] **SEC.T02** Unauthenticated write surface: `SystemCmd` (`bootloader` = offline until physical
      intervention; `reboot`; `mempause`), `ResetErrors` (irreversible evidence wipe), SSID/PW changes, every config write
      (flash/NVM wear by alternation).
- [ ] **SEC.T03** Browser-borne attacks: CSRF (blocked by JSON content-type + no CORS?), DNS rebinding
      (no Host check), clickjacking (no X-Frame-Options/CSP).
- [ ] **SEC.T04** Radio-range: shared default hotspot password in all 6 TOMLs (accepted-risk rule in
      CLAUDE.md), captive DNS spoofing, bogus-SSID → hotspot → second streak → permanent WLAN
      deactivation (A.4 intentional; a remote DoS needing a power cycle).
- [ ] **SEC.T05** Protocol-level: HTTP body/header bounds (`REST.S01`, `REST.S02`), NTP reply spoofing
      (no origin check), DNS response validation, captive-DNS subnet filter by source address.
- [ ] **SEC.T06** Host-side: `setcap` on the interpreter (owned by `SCR.T07`), secrets in argv/logs and
      `sudo` usage (owned by `TOOL.T01`), downloaded binaries without signatures (owned by `TOOL.T02`/
      `CI.T04`) — SEC only records the disposition.
- [ ] **SEC.T07** Credential hygiene consistency (owner, 2026-09-25: consistency, not safety) — see
      `HW.T11`; plus the known accepted hotspot fallback password in `src/asy_wifi_service.py`.
- [ ] **SEC.T08** Attack-surface inventory per mode (STA, AP, deactivated): HTTP 80 on all interfaces,
      captive DNS 53 (AP), cyw43 DHCP server (AP), mDNS 5353 if compiled into rp2 1.29 (unverified), ICMP;
      physical: USB-CDC/raw REPL (plaintext `PW` in `config_WIFI.cfg`), BOOTSEL/UF2, the dev UART jumper.
- [ ] **SEC.T09** Availability and evidence integrity vs a LAN peer: slot exhaustion (6 × 15 s, no
      per-peer limit), ring eviction via client-provoked entries (`CORE.S11`, `REST.S05`), repeated
      `mempause`/`reboot` (`XCUT.S03`), flash wear by alternating PUTs, stdout stalls (`REST.T13`).
- [ ] **SEC.T10** Information exposure and outbound traffic: what unauthenticated GETs reveal (SSID,
      hostname, versions + build date, full error histories) and every outbound destination (DHCP DNS,
      8.8.8.8/1.1.1.1 `NET.S04`, NTP host) — disposition each under PQ5.
- [ ] **SEC.T11** Trust in time and names: spoofed NTP → RTC, `TS`, FRAM backup age, notification
      window; spoofed DNS → NTP at an attacker's host; DNS id entropy (`os.urandom(2)`) and source-port
      predictability (`LWIP_RAND`) (with `NET.T03`/`T04`, `STOR.T09`).

Seeds: `REST.S01`, `REST.S02`, `REST.S04`, `REST.S05`, `NET.S04`, `NET.S12`, `NET.S16`, `NET.S17`,
`NET.S19`, `CORE.S11`, `XCUT.S03`, `HW.S02`, `TOOL.S01`, `SCR.S06`, `WEB.S17`, `HW.S08`, `CI.S04`, `CI.S06`
(cross-referenced, not repeated).

Quality measure: a threat-model table with a disposition per exposure, signed off by the owner.

---

### 5.20 MEM — Memory safety (cross-cutting)

**Goal**: the Part I discipline holds everywhere: no client-controllable or unbounded allocation, no
churn of same-shaped objects on hot paths, long-lived objects placed at boot, zero `MemoryError` at
both GC stages without `gc.collect()` props.
**References**: Part I (esp. I.2, I.3, I.4, I.6), `HEAP_FRAGMENTATION_MEASUREMENTS.md`, E.8.

Topics:
- [ ] **MEM.T01** Re-walk I.2's hotspot catalogue against current code (it predates several modules).
- [ ] **MEM.T02** The placement-lens re-walk BACKLOG already names: which run-phase code allocates
      something long-lived while bus/network churn is in flight?
- [ ] **MEM.T03** Client-controllable allocation (HTTP, DNS/NTP replies, UART peer-declared sizes,
      captive DNS datagrams) — each bounded before allocation.
- [ ] **MEM.T04** Per-cycle churn: log entries (fresh chunk buffer + lock), `pr.all()` argument tuples
      built at level 0, `write_config` dict copies, CRC `add()`/`check()` copies, f-strings in hot paths.
- [ ] **MEM.T05** Tests: `gc.collect()` props and absolute heap bounds — owned by `TEST.T03`
      (`TEST.S11`, `TEST.S12`).
- [ ] **MEM.T06** Does anything in `src/` still need one big contiguous allocation (I.4's forbidden-fix
      rule)?
- [ ] **MEM.T07** Target representation gap: rp2 small ints stop at ±2**30 and every float is a heap
      object (Unix port: ±2**62) — bigint/float churn in VOC, CRC32, `math_helpers` and driver formulas
      never reaches either tier's `MemoryError` gate; quantify per cycle (`ALGO.S07`, `ALGO.S08`).
- [ ] **MEM.T08** Per-call wrapper allocations on hot paths: `asyncio.wait_for()` (task + closure per
      call), memoryview slices (`BUS.S07`), `schema_dict()` rebuilt per field in `_set_dict_cfg`
      (`src/base_classes.py:346`), `*args` tuples.
- [ ] **MEM.T09** C-stack budget: rp2 main stack vs the deepest await chain; a `MICROPY_STACK_CHECK`
      `RuntimeError` would be swallowed by broad `except Exception` nets.

Seeds: `REST.S01`, `REST.S02`, `NET.S10`, `CORE.S07`, `TEST.S11`, `TEST.S12` (cross-referenced).

Quality measure: updated hotspot catalogue; every allocation site classified bounded/fixed/client-
controlled.

---

### 5.21 PERF — Timing and capacity budgets (cross-cutting)

**Goal**: every budget the system relies on is computed from code, checked against measurements, and
has a test that fails before the budget is crossed.
**References**: F.1, F.2, F.3, F.5.8/F.5.9, I.1 (GC pause), SPECIFICATION.md ~1854 (~305 ms yielding
per FRAM chunk), ~3985-3992 (~21 ms non-yielding block hold), BACKLOG 24/32.

Topics:
- [ ] **PERF.T01** Watchdog: worst-case feed gap (XCUT.T03).
- [ ] **PERF.T02** HTTP capacity: ~2.2 requests/s saturation, `max_connections` 6, slot release lag,
      UI polling rates, hidden tabs, no caching of static assets.
- [ ] **PERF.T03** `ResetErrors` sweep cost vs `outer_cap_s` and the UI timeout (BACKLOG 24/32 — the
      reader-count curve is queued as R2).
- [ ] **PERF.T04** Bus budgets: SCD30 50 ms sleeps under the bus lock, probe sleeps, FRAM block hold
      (~21 ms), SPI re-init per CS, VOC processing cost, CRC per-byte yield.
- [ ] **PERF.T05** Lock-hold stalls in networking (60 s sleep, 5 s connect poll, ~6.5 s NTP attempt) —
      owned by `NET.T02`; PERF records only the budget.
- [ ] **PERF.T06** Boot is not a metric to optimise (CLAUDE.md WP6): verify only that the setup batch
      never starves the WDT on the device with the most setup units (`dev`, ~21 FRAM loggers × ~170 ms).
- [ ] **PERF.T07** Idle CPU: polling loops (captive DNS 50 Hz, UART idle rate, neopixel busy-waits).
- [ ] **PERF.T08** Inventory of no-yield stretches with durations (littlefs flush with IRQs off, I2C up to
      its `timeout`, GC pause ~15-21 ms, `vocalgorithm_process()` on target, CRC32 with bigints, `print()`),
      each against every timing-sensitive consumer's tolerance.
- [ ] **PERF.T09** Measured event-loop lag under combined worst-case load, twin and bench (queue row).
- [ ] **PERF.T10** Persisted-log rate budget: every `err_s`/`wrn_s` costs a ~305 ms yielding FRAM chunk
      write queued on the FRAM lock (`src/print_log.py:167-178`); worst-case entries/s per module in a
      fault storm and what that queue delays (`XCUT.S01`).
- [ ] **PERF.T11** Console cost: at `DebugLevel` > 0 (REST-settable) every log line is a synchronous
      `print()`; with a USB-CDC host attached but not reading, each may wait up to the CDC TX timeout
      (`REST.T13`; verify at 1.29.0).

Seeds: cross-referenced from `XCUT.S01`, `SENS.S11`, `BUS.S02`, `BUS.S03`, `NET.S01`, `NET.S02`,
`NET.S07`, `NET.S11`, `LED.S01`, `REST.S08`, `WEB.S07`.

Quality measure: a budget table (value, derivation, measurement, guarding test).

---

### 5.22 PLAT — MicroPython/RP2040 platform facts

**Goal**: CLAUDE.md's standing practice run in full against 1.29.0 — every MicroPython-facing
construct checked for correctness *and* for a newer/better way (D.9), and every Part F fact re-verified
from source.

Topics:
- [ ] **PLAT.T01** asyncio semantics relied on: re-awaiting a finished/failed task, `Lock` FIFO order,
      `ThreadSafeFlag` from soft IRQs, `wait_for` cost, `Task.data`, cancellation delivery.
- [ ] **PLAT.T02** `const()` accepted types, `deque` features, `struct` truncation, `time.mktime`
      range/epoch, `random` seeding at boot, float32 behaviour.
- [ ] **PLAT.T03** rp2 port: soft-timer drop conditions, alarm-pool size, `machine.SPI.init()` cost,
      `UART.readinto` clamping, I2C/SPI `deinit()` no-ops, RX-overrun `EIO`, `mem_backup()` adoption
      (F.5.4), `reset_cause()`.
- [ ] **PLAT.T04** lwIP/modlwip: socket finalisers (PCB leak on GC), `tcp_write` retry blocking,
      `getaddrinfo` inside `asyncio.start_server`, UDP PCB pool.
- [ ] **PLAT.T05** Stub-package defects repaired by `typecheck.sh` — still present upstream?
- [ ] **PLAT.T06** Everything Part F.5 lists as "ruled out" — still ruled out.
- [ ] **PLAT.T07** Newer upstream (post-1.29.0) changes worth knowing before the next pin move (note
      only; the pin moves in its own session).
- [ ] **PLAT.T08** rp2 vs Unix-port number representation: small-int width, float boxing, mpz, float32
      libm accuracy (pico_float `pow`/`exp`/`log`/`atan`).
- [ ] **PLAT.T09** How mpy-cross freezes float literals and float `const()`s for a float32 target; does it
      fold float expressions in host double (`py/parse.c`, `MICROPY_COMP_CONST_FLOAT`)?
- [ ] **PLAT.T10** Boot chain: frozen `main.py` vs filesystem `boot.py`/`main.py` precedence
      (`shared/runtime/pyexec.c`); what runs after `main.py` returns or raises (REPL, soft timers); WDT
      across a soft reset and across `machine.bootloader()`.
- [ ] **PLAT.T11** `json`: `dumps()` of NaN/±inf, float32 round-trip through `dump`/`load`, how `dump()`
      writes to a littlefs stream.
- [ ] **PLAT.T12** `MICROPY_SCHEDULER_DEPTH` on rp2 and which sources share it; whether rp2 flash writes
      still disable IRQs / lock out core 1 at 1.29.0 and for how long; `ThreadSafeFlag` single-waiter rule.

Seeds: `CORE.S09` (task re-await), `BUS.S03` (SPI init), `BUS.S05` (UART readinto), `NET.S13` (socket
finaliser), `ALGO.S01` (int32 vs Python int).

Quality measure: each fact cited to a file:line in the pinned source; F.5 updated where it drifted.

---

### 5.23 PAR — Legacy parity and field migration

**Goal**: every deployed feature exists in the refactor or its removal/change is documented as
deliberate; the legacy → refactor reflash is understood and safe.
**References**: `python/`, `modules/sensortask-*.py`, `html_raw/`, `build-*.sh` (read-only); Parts A.4,
A.8, H.1, L.1; CLAUDE.md "same top-level features" agreement.

Topics:
- [ ] **PAR.T01** Full parity table: every legacy REST route/field/bound/default/behaviour → refactor
      location, "same" / "changed-documented" / "changed-undocumented" / "missing".
- [ ] **PAR.T02** Device mapping: legacy `arzi`/`neu`×3/`wozi`/`dev` → `devices/*.toml` pins and
      options.
- [ ] **PAR.T03** A.4 "confirmed intentional" behaviours still hold, one by one.
- [ ] **PAR.T04** Timing parity: supervisor period/reset delay, UI poll interval, LED sleeps, NTP retry.
- [ ] **PAR.T05** External REST consumers (scrapers, home automation) of the legacy routes — owner input.
- [ ] **PAR.T06** Migration on reflash: stored `config.json` → per-module `.cfg` (never read), legacy
      FRAM contents under the new layout, littlefs region size across 1.26 → 1.29, hostname change and
      DHCP reservations, SCD30 NVM survival, first-boot hotspot → permanent-deactivation hazard.
- [ ] **PAR.T07** Whether a reflash runbook (or a first-boot migration/format step) is wanted (PQ11).

Seeds:
- **PAR.S01** `WaitTimeNTP=0` disables the VOC restore entirely; legacy restored once, immediately; the
  web label "Never wait for NTP sync" implies the legacy meaning (`src/asy_sgp40_driver.py:53, 64,
  355-358`).
- **PAR.S02** `[x2]` SCD30 PUT calls every setter unconditionally; legacy wrote only when the value
  differed from the readback (or forced `AmbPres`) — NVM wear and repeated `ForceCalRef` recalibration
  (`src/asy_scd30_driver.py:257-298` vs legacy `api_helpers.py:192`).
- **PAR.S03** SGP40 resets `voc_write = WaitTimeNTP` after every stamped write, so each later backup waits
  for NTP again; legacy set it to 0 for good (`asy_sgp40_driver.py:430-438`).
- **PAR.S04** `[x2]` Supervisor: check period 3 s → 2 s (decay 1.5× faster), reset delay 5 s → 4 s,
  explicit `reboot_system()` instead of watchdog starvation; A.2 still says "stops feeding the
  watchdog"; BACKLOG asks for the supervisor change "without changing observed behaviour".
- **PAR.S05** `/system`'s build info exists but no UI renders it (see `WEB.S20`).
- **PAR.S06** Wire changes are documented as deliberate (six routes, sparse PUT, native bool/null,
  `BMP388` → `BMP3XX`, oversampling as values not indices, `Led` prefix dropped) — but old bookmarks
  (`/sensorconfig.html` etc.) now 404; confirm acceptable.
- **PAR.S07** UI measurement poll 2 s → 3 s (definitions `landingSection` poll 3000 ms).
- **PAR.S08** Config migration: nothing in `src/`/`buildgen/` reads `config.json`; after reflash every
  unit boots with SSID `""` → hotspot; if nobody joins within the hotspot window, the second streak
  permanently deactivates WLAN until a power cycle. BACKLOG #2's "avoids this structurally" covers
  key-adding updates, not this transition.
- **PAR.S09** Legacy FRAM chunk 0 (SGP40 VOC state, no CRC, 248 B) sits where the refactor's first
  chunk now lives; expect CRC/status errors on first boot that seed misleading errcount entries (see
  CLAUDE.md's FRAM-evidence rule); VOC baseline lost (45-sample relearn).
- **PAR.S10** The littlefs region must survive a 1.26 → 1.29 swap (`MICROPY_HW_FLASH_STORAGE_BYTES`
  equal on both; B.14.3) — unverified.
- **PAR.S11** Hostname changes from `"SensorNode"`/user-set to `SensorStation<Name>` (DHCP reservations,
  DNS names, hotspot SSID).
- **PAR.S12** Legacy reboot-looped forever on a failed `fram.setup()` (WDT starved); the generated
  `build_system()` ignores `setup()` results — an undocumented, probably-better change.
- **PAR.S13** CLAUDE.md says the refactored wozi is "never physically flashed"; if the fielded wozi unit
  is ever reflashed, its first real flash is a production one — owner confirmation.

Quality measure: complete parity table; each "changed-undocumented" row decided by the owner.

---

### 5.24 DOC — Documentation set

**Goal**: the docs hold current state, rules and targets only; every fact has one home; every
cross-reference resolves; the auto-loaded CLAUDE.md stays a rule set, not a reference manual.
**References**: CLAUDE.md "Working agreements"; README "Further reading".

Topics:
- [ ] **DOC.T01** Structural hygiene of `SPECIFICATION.md`: misplaced sections, heading levels,
      unnumbered subsections, a section-level table of contents.
- [ ] **DOC.T02** Cross-reference integrity: `Part X.Y` (all resolve today), BACKLOG numbers, queue row
      IDs, archive `§`, named sections — and whether a CI lint should keep it that way.
- [ ] **DOC.T03** Reference policy: permanent code citing temporary docs' row IDs (they dangle once
      rows are deleted); ID namespaces that collide visually (`F1` row vs `F.1` Part).
- [ ] **DOC.T04** Archive durability: `12640c2` reachability after merge (PQ7).
- [ ] **DOC.T05** History/narrative vs the current-state rule (tests_hardware README pass sections,
      README provenance paragraphs, CLAUDE.md incident bullets, BACKLOG item narratives, dated stamps).
- [ ] **DOC.T06** One home per fact: duplicated facts across CLAUDE.md/SPEC/BACKLOG/queue/handover;
      open work scattered over 6+ places.
- [ ] **DOC.T07** CLAUDE.md budget (~92 KB auto-loaded): rules vs facts vs narrative; relocation of the
      chroot recipe and "Known … fixed" bullets to SPEC with pointers (PQ6).
- [ ] **DOC.T08** Every dated count/number claim (86/86, ~157, 21 chunks, suite counts) — keep, make
      generated, or make tested.
- [ ] **DOC.T09** Glossary for undefined labels (WP1-WP8, measure A/B, image E6′, S3, sittings).
- [ ] **DOC.T10** Contradiction sweep (seeds below) and terminology drift.

Seeds:
- **DOC.S01** `## I.6` sits inside Part J (SPECIFICATION.md:5161); `## E.2.1` (:2796) and `## H.5.1`
  (:4406) should be `###`; H.7 has two unnumbered subsections (:4526 connection ceiling — cited as
  "H.7" for lwIP facts — and :4660 cross-browser).
- **DOC.S02** F.5 is titled "MicroPython 1.29 delta" but F.5.7-F.5.9 are standing UART runtime facts
  CLAUDE.md's hard rules depend on; a future version audit replacing F.5 would orphan them.
- **DOC.S03** Contradiction on website definitions: H.5 (:4401) and `build_website.sh` say wozi/dev are
  hand-written; K.4 (:5781) says "never hand-maintained"; K.8 (:5895) "regenerates automatically";
  C.11 point 9 (:2331) says hand-update.
- **DOC.S04** ~77 "archive §" citations resolve only against commit `12640c2`, reachable today only from
  this branch (PQ7).
- **DOC.S05** Dangling named citations in code: `tests/machine.py:2`, `tests/test_captive_dns.py:230`,
  `src/asy_notification_service.py:3, 69`, `src/asy_neopixel_driver.py:3`,
  `tests/test_asy_wifi_service.py:1791`, `scripts/_strip_type_checking.py:13`,
  `tests_scripts/test_strip_type_checking.py:51`, `scripts/lint.sh:17`,
  `tests_hardware/bench/test_network_resilience.py:3`, `tests_hardware/flash/test_toolchain_flash_boot.py:
  14, 25, 46`, `tests_hardware/bench/test_heap_under_connection_ceiling.py:161`,
  `tests/test_asy_webserver_service.py:194` (F.6/F.7 from a retired audit, colliding with Part F),
  `tests_hardware/flash/test_bus_concurrency.py:122` (quotes item 8 as unsettled).
- **DOC.S06** Deleted queue rows still cited: C7 (BACKLOG:249), R10 (BACKLOG:661), F11
  (SPECIFICATION.md:5279, `tests_hardware/http_client.py:48`), F7, F10, F13, G9 (in tests_hardware).
- **DOC.S07** Dangling doc pointers: README.md:652-653 and 783-784 point at SPECIFICATION front matter
  that has no such text; CLAUDE.md:647 ("`_timer_sequencer()` fix above") and :893-894 ("Platform
  target" above) point at nothing; BACKLOG.md:817 names a nonexistent README section.
- **DOC.S08** Stale: "86/86" (CLAUDE.md:350, HARDWARE_TEST_HANDOVER.md:20) and "85" (SPECIFICATION.md:
  2917) vs 87 test files; CLAUDE.md:773 "~157" method-assign sites vs 209; CLAUDE.md:725 names a split
  test file; A.6 datasheet list omits isl29125; B.9 (821-826) says `build-*.sh` still hardcode paths and
  firmware build is uncovered; C.11 "only"/"three" (2319, 2325) and C.4.1 "three drivers" (1630);
  L.6.4 "only `_LIMITS` driver" (isl29125:194 has one too); README.md:774-776 item 8 status; "pre-push
  verification" wording (SPECIFICATION.md:6-7, README.md:650).
- **DOC.S09** `[x3]` A.7 states setup order `sysfunct → fram → …`; the generator emits `fram → sysfunct →
  …` (`buildgen/codegen.py:441-449`); A.2 supervisor text stale (`PAR.S04`); C.6 (:1802, :5666)
  describes a `repr()`-parsing `make_dict()` "landmine" the code no longer has; C.5.3 cites a
  nonexistent `_cfg_subset()` and `/net/cmd`/`/led/cmd`.
- **DOC.S10** Conflicting migration targets for resolved BACKLOG items (BACKLOG.md:5-7, README.md:656-
  657, CLAUDE.md:406-410 say CLAUDE/README; practice is mostly SPECIFICATION).
- **DOC.S11** Coverage gating stated both ways in README (189 vs 183-185); CLAUDE.md chroot recipe
  contradicts itself (1026-1028 vs 968-971) and duplicates the libcap2-bin paragraph (936-953).
- **DOC.S12** CLAUDE.md:367-376's FRAM-log list omits ISL29125 (dev wires it to FRAM); SPEC cites
  "CLAUDE.md's implicit-FRAM-wiring rule" (376, 396) that CLAUDE.md never states as a rule.
- **DOC.S13** BACKLOG hygiene: stub list (15-18) omits item 29; items 2 and 4 are decided and uncited;
  a SETTLED entry filed under "not yet done" (58); several items carry "earlier version said" narrative.
- **DOC.S14** `UART_C_PORT_CHANGELOG.md` is "temporary until reconciled", but reconciliation is out of
  scope (owner) — no reachable deletion trigger; reclassify?
- **DOC.S15** `update_and_install.txt` is missing from README's "single complete map"; the queue and the
  handover duplicate board state and running order; `dev_legacy/README.md`'s "single source of truth"
  status vs the queue/handover.
- **DOC.S16** Undefined labels used across 39 files: WP1-WP8; "measure A/B", "image E6′", "S3" defined
  only in the git archive.
- **DOC.S17** Dated counts likely drifted: CLAUDE.md:821-840's per-file `call-overload` counts; BACKLOG's
  explicit-`Any` counts (2026-09-11); SPECIFICATION.md:3668-3671 and queue:73 suite counts.

Quality measure: cross-reference resolver clean for every ID family; contradiction list empty or
decided; CLAUDE.md size target agreed (PQ6) and met.

---

### 5.25 LIC — Licensing and attribution

**Goal**: every vendored or derived file carries correct attribution and `THIRD_PARTY_LICENSES.md` is
complete and accurate for what ships and what is stored in the repo.

Topics:
- [ ] **LIC.T01** Every Adafruit/DFRobot/Sensirion-derived file's header attribution vs
      `THIRD_PARTY_LICENSES.md` (F.4 allows rewriting, keeping attribution).
- [ ] **LIC.T02** Vendored `ext/` licences present and matching upstream tags.
- [ ] **LIC.T03** The unknown-provenance area (`captive_dns.py`/`asy_ntp_client.py`/`asy_udp_socket.py`,
      `src/LICENSE-captive_dns`) — still accurately described?
- [ ] **LIC.T04** Scope statement vs `arduino/`'s vendored third-party libraries (BSEC, Adafruit,
      BME68x) — out of project scope (owner) but stored in the repo.
- [ ] **LIC.T05** What actually ships in the firmware image (frozen set) vs what the licence doc lists.

Seeds:
- **LIC.S01** Two separate `src/asy_isl29125_driver.py` entries (THIRD_PARTY_LICENSES.md:34-39, 46-53);
  l.37 says the legacy copy is listed "below" while l.118-120 says the entry "moved up".
- **LIC.S02** THIRD_PARTY_LICENSES.md:52-53 credits "FRAM-persisted gain-ratio self-calibration";
  M.1.5 and the driver say calibration is RAM-only and user-applied.
- **LIC.S03** README.md:726-731 calls the doc "every piece of vendored … third-party code in one
  place", but `arduino/`'s vendored libraries are not mentioned.

Quality measure: per-file attribution table; doc accurate for the shipped image.

---

## 6. Plan validation (planning phase — this is the only work allowed before go-ahead)

Each step is its own dedicated pass; none is marked done by another's side effects (lesson from the
retired `AUDIT_PLAN.md`).

- [ ] **V1 Inventory coverage**: script-check that every git-tracked file maps to exactly one area in
      5.0 or to the 2.2 list; add missing areas/topics.
- [ ] **V2 Completeness review by fresh eyes**: independent agents per area group read this plan plus
      the area's files and answer only "what topic or lens is missing?"; merge by arbitration.
- [ ] **V3 Reference reality check**: every file path, line anchor, SPEC Part and seed citation in this
      file resolves at the planning baseline (this checks the *plan*, it does not verify seeds).
- [ ] **V4 Internal consistency**: every ID referenced in this file exists; no two topics overlap
      without a cross-reference; section 4.1's waves cover every area.
- [ ] **V5 Backward read**: read bottom-to-top for contradictions between stated facts (order-
      independent claims only).
- [ ] **V6 Owner review**: PQ1-PQ11 answered; the owner declares the list complete (or keeps
      extending it) and gives the execution go-ahead explicitly.

---

## Appendix A — System snapshot (planning baseline `0615eba`, for orientation)

- **Product**: MicroPython 1.29.0 firmware (frozen bytecode) for Raspberry Pi Pico W (RP2040) room
  air-quality units. 6 device variants from `devices/*.toml` (`wozi`, `dev`, `arzi`, `klkizi`,
  `grkizi`, `schlafzi`); field units still run the legacy 1.26 tree (`arzi`, `wozi`, 3× `neu`).
  Only `dev` is ever flashed/bench-tested; `wozi` is the exemplar validated by mock/twin tiers.
- **Runtime**: one asyncio loop; soft `machine.Timer`s set flags; a supervisor restarts dead tasks with
  a decaying score and reboots past a threshold; `WDT(8000)` fed by setup batch and supervisor.
- **Layers**: bus wrappers (`asy_i2c/spi/uart_driver`) → protocol classes → `*_Reader`
  (`SensorReader`/`SensorReaderConfig`) with per-module `ConfigManager` JSON files on littlefs and
  `PrintLogHistory(Store)` error rings, FRAM-backed via a dual-copy chunk allocator.
- **Sensors**: SCD30 (CO2/T/RH, NVM settings), SGP40 (VOC index, FRAM-backed algorithm state),
  BMP3xx (pressure), ISL29125 (RGB/lux, dev only); NeoPixel notifications; UART protocol pair (dev only).
- **Network**: STA with hotspot/captive-portal fallback and permanent deactivation after a second
  failure streak; NTP with EU DST; own non-blocking DNS; Microdot v2.6.2 REST (6 GET routes, PUTs,
  static gzip site), `max_connections` 6, 2048 B body cap, 15 s outer cap; lwIP options pinned via a
  build override.
- **Build**: `buildgen` turns a device TOML + AST-read `src/` tags into `sensortask_<device>.py`, a boot
  entry and `definitions.json`; `build_firmware.py` stages, strips `TYPE_CHECKING`, freezes the website
  (`build_website.sh` → freezefs) and builds the UF2 with a from-source toolchain (`toolchain/`).
- **Verification tiers**: mock (87 files, ~3,770 tests under the real Unix-port interpreter), digital
  twin (chip fakes + fake `machine`/`network`, CI suite of 14+ runs per device), host pytest
  (`tests_scripts/`, 60 files), web (Vitest browser mode, cross-browser smoke), real hardware (flash 51,
  bench 85, soak 4, manual; owner go-ahead only).
- **Docs**: ~1.1 MB; SPECIFICATION.md (Parts A-M) is the central spec; CLAUDE.md the auto-loaded rule set;
  BACKLOG.md working memory; queue/handover temporary.
