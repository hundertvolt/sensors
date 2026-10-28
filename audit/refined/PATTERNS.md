# Refined harvest — recurring-pattern catalog

Audit working file (temporary, deleted with `audit/`, OR11.a). Drafted by an agent, reviewed and extended
by the lead (RP38, partition) on 2026-09-28 for the owner's refined-harvest request; HEAD `5efc919`.
Purpose: harvest pass 1 recorded only what the repo **self-declares** (TODO, LIMIT, SETTLED, ...,
`audit/sweeps/harvest_prompt.md`). Everything learned since — OR1-OR83, harmonizations 1-45, the pass-2
register (518 live requirements), the verifiers' 68 defects, the provenance sweep (366 hits, mechanisms
M1-M7), CLAUDE.md's incident bullets — shows **which kinds of problem keep recurring here**. Each pattern
below is swept across the whole repo for **undeclared** instances: sites no comment or doc flags, which
pass 1 therefore could not see.

## 0 How to use this catalog

### 0.1 Why these recur — the owner's own recurrence markers

| Owner words | Row | Pattern(s) |
|---|---|---|
| "false decisions were written down or drifted away … and were lateron strictly obeyed"; "a long history of such oversights"; "code grew over time … incompletely retrofitted, or already existing ones forgotten in new code" | OR13 | RP01, RP02, RP24, RP27 |
| "topics may have been washed out or drifted into a wrong direction" | OR14 | RP02, RP03 |
| "a long history of accidentally stumbling upon such silent failures and losses" | OR16 | RP14, RP30, RP17 |
| "not always designed to be biting" | OR19 | RP28 |
| "several cases where the unit tests were completely integrated into the digital twin or the real hardware" | OR20 | RP31, RP25 |
| "silent test blindness by chance several times" | OR21 | RP29 |
| "the linter limit … was risen again and again" | OR46.a | RP34, RP12 |
| "several occasions where leftovers from previous operations … crosstalk" | OR38 | RP31 |
| "I never required that, I even objected several times against it!" (FRAM cross-version) | OR56 (3) | RP01, RP02 |
| "the recording as "my decision" is clearly wrong … catch more of such occurrences" | OR62 | RP01 |
| "This is a serious gap" (SCD30 compare-before-write lost from legacy); "treat this requirement as a concept" | OR42.b, OR48 | RP37, RP22 |
| "it seems to be lost regularly … I insisted several times on removing such traces" | OR78 | RP10 |
| "twin setup was always tracked along" — it was not | OR17 | RP09 |
| "either it's a fault or a warning, but never both … should be globally checked" | OR56 (1) | RP16 |
| "we once stumbled upon the NTP service just stalling its task … generalize" | OR18 | RP13 |

Numbers behind them: 49 of 214 owner-worded rules drifted or wrong, 79 only partly applied
(`audit/HARVEST_REQUIREMENTS.md` 2.1); 135 actorless decisions (M1), 51 agent recommendations recorded as
owner choices (M6), 31 qualifier/attribution moves (M3), 23 widenings (M4) (`audit/DECISION_PROVENANCE.md`
2.1); 19 wrong facts (HR 2.2); verifier defects C1 contradiction / C2 rank-date / C3 widening-narrowing /
C4 factual / C5 dropped owner content (`audit/pass2/verify/`), i.e. the **same drift classes reappear in
the audit's own register** — sweepers must not reproduce them in their output.

### 0.2 NEW vs KNOWN — the dedup procedure (every sweeper, every hit)

1. **Harvest pass 1**: grep `audit/harvest/*.md` (and `audit/harvest/raw/` for pre-merge text) for the
   file path and line. A hit whose site is already an item there is KNOWN unless the item's kind misses
   the defect (e.g. harvested as INVAR, but it is a test seam → `KNOWN+`).
2. **Register**: grep `audit/pass2/G*.md`, `LEAD.md` for the path (State lines cite `file:line`); the
   pattern's "known holders" below name the requirements. A site named in a State line is KNOWN.
3. **Provenance**: `audit/dprov/D1-D6.md` (366 hits with sites), `audit/DECISION_PROVENANCE.md` lists
   A-E, V, L and section 6 (32 factual errors); `audit/pass2/verify/L25.md` (25 owner-traced choices).
4. **Plan**: `PROJECT_AUDIT_PLAN.md` section 5 topics/seeds (`<AREA>.Tnn/Snn`) and the OR rows' named
   examples (OR rows often list sites "at recording time").
5. Classify: `NEW` (site in none of 1-4), `KNOWN+` (known item, but new sites or a defect the known
   item does not state), `KNOWN` (count only, do not list). Anchors at HEAD; harvest anchors are at
   `4dc80ef`, so match by quote when lines moved (`src/` is unchanged since `4dc80ef`, V2/V10).

### 0.3 Output line (one per NEW / KNOWN+ hit)

```
- RPnn.<sig> | NEW|KNOWN+ | <file:line@5efc919 or commit> | "<quote ≤20 words>" | <what is wrong, one line> | near: <known IDs> | home: <register req or "new req">, unit Uxx | owner-matter: y/n
```
Plus per pattern: a coverage table (what was searched: scope, signatures, counts of raw hits, NEW,
KNOWN+, KNOWN, rejected-as-false-positive with reason). No fixes, no severities (plan 4.5 assigns them).
Where OR2.c/OR12.a/OR13.a would route a finding to the owner, say so; never decide it.

### 0.4 Standing constraints for sweepers

Read-only; write only your output file. No tests, builds, `uv`, `npm`, `mpremote`, port binding,
network. Git read-only (`log`, `show`, `blame`, `log -S/-G`, `diff`). Never read `arduino/`. `ext/` is
never edited and only read for Microdot semantics. Legacy (`python/`, `modules/`, `build-*.sh`,
`dev_legacy/`'s old driver copies; `html_raw/` only for RP37's UI-function parity) is reference-only:
read for parity, never a finding target (CLAUDE.md "legacy tree is reference-only, forever"). Static
analysis with ad-hoc `python3 -c`/`ast` scripts in the scratchpad is allowed (it runs nothing of the
repo). MicroPython `v1.29.0` source: the scratchpad checkout `…/scratchpad/mp`; datasheet text:
`…/scratchpad/dstxt/`; Microdot: `…/scratchpad/microdot`.

---

## A. Records and provenance (docs, comments, git history)

### RP01 Actorless or misattributed decisions
- **Why it recurs**: owner answers reach the repo only through agents (DP 2.3). M1 actorless decision
  vocabulary 135 hits, M6 agent recommendation recorded as owner choice 51, M2 parked questions 7, M7
  blanket tags (`32b136f` over Part J, `999aada` over every UI choice). Trigger cases: SGP40 "accepted risk"
  (`f5c9f90`, OR62/OR64), FRAM "identical across firmware versions" (`69d85b7`, OR56 (3)), "Final project
  decision" over nine test sites (`ca7bffc`/`04e8f40`, C14), `3692a0a` filing its own "left as-is" under
  "confirmed intentional by the project owner" (C03). Harmonizations 34, 35; prevention rules 1, 2, 4, 5
  (OR68.a (4)).
- **Instance shapes**:
  - (a) decision word with no actor tag and no source citation in the same sentence: `accept(ed|able)`,
    `settled`, `decided`, `by design`, `deliberate(ly)?`, `intentional`, `final`, `standing`,
    `don't|do not re-propose`, `not a bug`, `don't fix`, `not to be reopened`, `stays`, `won't`,
    `out of scope`, `known (gap|limitation)`, `tolerat`, `project decision`;
  - (b) owner attribution without owner words: `owner('s)? (decision|direction|call|rule|choice)`,
    `(project owner|owner), 20\d\d-`, `confirmed (directly|by the (project )?owner)`, `per (project )?owner`;
    check the introducing commit (`git log -S`) for a quote;
  - (c) a heading or list preamble that attributes every item below it (`confirmed intentional by the
    project owner`, "the project owner's list") — check each item's introducing commit;
  - (d) parked question: `flagged for`, `owner's call`, `if ever revisited`, `revisit`, `TBD`,
    `to be decided` outside BACKLOG's owner-question list;
  - (e) batch commit messages "Act on/Record the owner's N decisions" paraphrasing without the question
    (`git log --grep='owner.s .* decisions'`) — each decision they introduced;
  - (f) decision text **emitted by generators** (strings in `buildgen/codegen.py` that land in generated
    modules), in assertion messages, error strings and JS/CSS/HTML comments, TOML comments.
- **Where**: every tracked text outside `audit/`, the plan, legacy, `arduino/`, `ext/`, `datasheets/`:
  all `*.md`, `src/`, `tests/`, `tests_scripts/`, `tests_hardware/`, `digital_twin/`, `buildgen/`,
  `scripts/`, `toolchain/`, `js/`, `tests_js/`, `html/`, `devices/`, `.github/`, `pyproject.toml`,
  `*.ini`, `eslint.config.js`, `package.json`. Git: all 1,718 commit messages (`git log --format=%H%n%B`).
  Calibration: ~222 decision-vocabulary lines and ~118 owner-tag lines in docs alone.
- **NEW vs known**: DP hit sites (`audit/dprov/D*.md`, placed in DP section 7) and lists A/A2/B/C/D/E/V/L;
  harvest SETTLED items; register G9/R27, G9/R35-R38, G2/R28, G7/R41. NEW = a decision statement at a
  site no D-hit cites (DP read current text at `a89a097`-`c76ae9b`; everything changed since, and shapes
  (e)/(f), are the likeliest gaps), or a D-hit whose classification the introducing commit contradicts.

### RP02 Scope drift of recorded rules (qualifiers dropped, words widened, foreclosures added, reasons swapped)
- **Why it recurs**: compaction, migration from temporary plans, proofreading and the three comment-cap
  passes (2026-09-18 `src/`, 2026-09-22 shell, 2026-09-24 config) rewrite rule text. Cases: L06 "leave
  as-is, no alternate read-back" → "confirmed intentional — don't fix" (`8784c66`, reason dropped
  `e5f31f2`); L44 "rather than scattered noqa" → "never" (`def319b`); L51 "`dev`'s real website" →
  "the real site" and tests built wozi's; L11 "disallowed" → "must never … standing rule"; B01 "for now …
  deferred to the refactor" → "accepted risk" (`50d86c3`/`75f2e11`); B02 owner "not worth it" → "intended
  recovery feature, don't propose" (`a04b483`, same day); V09 "overkill as a blanket policy" → "concrete,
  non-hypothetical threat" (`3ab1dae`, OR26.a); V06 "not yet decided" → "Decided"; A37 "not one of the
  original twenty" dropped (`5b97af3`); owner tags stripped by the `901e15d` fold; empty pointer
  "(owner decision, 2026-09-18, )" (`86fb067`); OR72.a (7)'s "until flash space is short" dropped twice
  inside the audit's own register (V3/V09, V4/V04). HR 2.1: owner rules drift most (49/214).
- **Instance shapes** (history diff, not text grep):
  - (a) a removed line holding a qualifier — `for now|until|not yet|on current code|deferred|at present|
    for the moment|temporar|unless|except|only (when|if)|rather than|prefer|if ever|as long as|while` —
    whose replacement line (same hunk or the text's new home) lacks it;
  - (b) an added foreclosure — `never|must not|don't|do not re-propose|not to be reopened|permanent(ly)?|
    stays|no plan to|and never will|must not gain` — in a commit whose message says compaction/fold/
    migrate/proofread/cap/"no content loss";
  - (c) an actor tag moved, added or removed by such a commit (`(owner|agent|project owner)` lines);
  - (d) a stated reason replaced or dropped while the rule stayed (harmonization 24: the rule keeps,
    the reason is corrected) — e.g. "deployed units" (A2-07), "fielded behaviour" (B06);
  - (e) an owner answer about one item generalised to a class ("a device's allow-list", "not to be
    modified" for all of `crc_checks.py` from an answer about the per-byte yield, LEAD 1 #8; V1/V14 "or
    algorithm").
- **Where**: `git log -p --follow` of CLAUDE.md, SPECIFICATION.md, BACKLOG.md, README.md,
  `tests_hardware/README.md`, `digital_twin/README.md`, DEVICE_REFERENCE.md, UART_C_PORT_CHANGELOG.md,
  and code comments of `src/`, `buildgen/`, `tests*/`, `digital_twin/`; prioritise the 181 commits whose
  message matches `compact|fold|cap|prune|migrat|proofread|trim|condense|3-line`, then deleted plans
  (`git log --diff-filter=D --name-only -- '*.md'`) versus where their text went.
- **NEW vs known**: DP list B (15), M3/M4 hits, L25 drift verdicts, DP section 6 rows 13-14 and 29-31,
  `audit/hreq/G*.md` candidates with "Truth: drifted/wrong", HARVEST DRIFT items (468). NEW = any other
  drifted rule or qualifier. This is the OR13.a/OR14.a history trace named in CONSOLIDATION section 9 —
  the output feeds pass 3 directly (do not run it twice).

### RP03 Merge-resolution loss
- **Why it recurs**: 121 merges; parallel sessions on long-lived branches. D.15's 2026-09-13 ruling
  dropped by merge `e5d2c43` (harmonization 27); owner-tested SCD30/SGP40 delays (`144873f`, `5ff8c0b`,
  G3/R30) restored in pass 2; a merge re-accumulated ~800 lines of history in BACKLOG (CLAUDE.md);
  `uv.lock` merged line-by-line into a self-contradictory lock that bypassed the tool pins (CLAUDE.md,
  2026-09-10); "a merge resolved by taking one side wholesale hides test/source mismatches" (CLAUDE.md).
- **Instance shapes**:
  - (a) owner-tagged or decision lines present in either parent but absent from the merge result and
    not moved elsewhere (`git diff M^1 M`, `git diff M^2 M`, filter removed lines with owner tags or
    RP01/RP02 vocabulary; then `git log -S` for where they went);
  - (b) a test pinning a feature whose source side was resolved `--ours` (test added on one parent,
    feature code absent at merge); a test file changed in the merge while its target was not;
  - (c) lock/pin files (`uv.lock`, `package-lock.json`, `toolchain/versions.toml`, `.nvmrc`) whose
    manifest and resolved parts disagree after a merge;
  - (d) duplicated sections or history re-added by a merge (same heading twice, pruned text back).
- **Where**: `git log --merges`, combined diffs (`git show --cc`), all file types.
- **NEW vs known**: harmonization 27's list, G3/R30, G5/R50, G8/R63, CLAUDE.md incidents. NEW = any
  other merge loss or re-accretion.

### RP04 Dangling citations and references to retired artifacts
- **Why it recurs**: temporary plans (FINAL_WIRING_PLAN, WP_RESTART_HANDOVER, WEBSITE_PLAN,
  BUILD_CHAIN_PLAN, UART_PROMOTION_REQUIREMENTS, HEAP_REMEDIATION_PLAN, PROJECT_NOTES, the queue and
  handover) were deleted while text kept citing them by section or number; runners and files were renamed.
  DP list E (9), section 6 rows 6-12, 20-21: "decision 3/6/7/8/10", "Topic 11", "§6.5", "WEBSITE_PLAN
  §7 'Coverage depth'", "(CLAUDE.md)" for rules CLAUDE.md never held, `.gitignore:75` citing the retired
  `run_wozi_integration.py`, `cfg_schema` kept "for the legacy REST layer" that was deleted. Prevention
  rule 5 (OR68.a (4)).
- **Instance shapes**:
  - (a) names of deleted files/dirs: `git log --diff-filter=D --name-only --format=` gives the list;
    grep the tree for each basename (calibration at HEAD: `sensortask_wozi` 30 files, `src/sensortask_wozi`
    15, `improved-quality` 6, `run_wozi_integration` 5, `get_long_block_lock` 5, `html_stub` 4, `codecov` 6);
  - (b) numbered labels with no living definition: `(decision|topic|step|item|question|criterion|
    stage|WP)\s*#?\d+`, `§\s*\d`, "this step's own finish criteria";
  - (c) `Part [A-Z](\.\d+)*` and `SPECIFICATION.md (Part|section)` references whose target heading does
    not exist or no longer says what is cited;
  - (d) `file:line` anchors in permanent docs and comments (`[\w/.-]+\.(py|js|sh|toml|md|yml):\d+`)
    that no longer point at the quoted construct;
  - (e) CLI flags, env vars, CI job names, markers, make/npm script names cited in docs that no longer
    exist (`--soak`, job names in `ci.yml`, `package.json` scripts);
  - (f) "see X" / "X explains" pointers where X exists but does not contain the claimed content.
- **Where**: all living text and code comments; `.gitignore`, `pyproject.toml`, `ci.yml` comments.
- **NEW vs known**: DP list E and section 6; harvest DRIFT "dangling" items; G9/R12's cited sites; OR50
  examples. NEW = every other unresolved citation.

### RP05 One fact, several homes; competing vocabularies
- **Why it recurs**: rules restated in CLAUDE.md, SPECIFICATION.md, README.md, `tests_hardware/README.md`
  and code headers drift apart (OR45: the tier concept "mentioned at several places" under two
  vocabularies, backends vs environment tiers; harmonization 20); CLAUDE.md duplicating SPEC facts it says
  it moved; the FRAM-backed logger list hand-kept in CLAUDE.md (G1/R12). OR51 "single point of truth, no
  duplicates"; G9/R13.
- **Instance shapes**: (a) the same rule/fact stated in two or more docs (near-duplicate sentences:
  normalise and compare 8-word shingles across all living `.md` and header comments); flag pairs whose
  numbers, names, scope or qualifiers differ; (b) terms used with two meanings or two terms for one thing:
  tiers/backends/levels/L0-L4, "field/fielded/deployed" (OR61.a (2)), "twin/mock/fake", "device/variant/
  board", "setup/init/initialize", result words; (c) a doc restating a list that is derived elsewhere
  (device lists, route lists, logger lists, errno tables, tunables).
- **Where**: all living `.md`; module headers in `src/`, `buildgen/`, `digital_twin/`, `scripts/`.
- **NEW vs known**: G9/R13-R15, harmonization 20, OR45.a (1), G1/R12. NEW = every other divergent pair.

### RP06 Stale current-state claims (snapshot numbers, void premises, history narrative)
- **Why it recurs**: docs grow by incident narrative; counts and measurements are copied as current;
  requirements rest on premises the owner has voided. Cases: "legacy units run 1.26" (really 1.24.1,
  OR61), "5 units are currently deployed" (README:10-13), "the deployed link runs CRC_Pass … in the
  field" (no UART device in the field), FiltCoeff kept for "deployed units" (A2-07), "legacy REST paths
  that external clients may use stay" (OR58 voids it), "86/86 on 2026-09-24", "Topic N", a ~800-line
  history re-accretion (CLAUDE.md), OR27.a's "no incident stories". OR27, G9/R11.
- **Instance shapes**: (a) void premises: `deployed|fielded|in the field|field units|backward|compat|
  existing units|external clients|migration` used as a reason (OR52.a (1), OR58.a, OR61.a); (b) counts
  and sizes stated as current (`\d+ (files|tests|devices|units|modules|lines|items|jobs)`, `\d+/\d+`),
  checked against the tree; (c) measured figures without image, date and method (G1/R39, OR27.a keeps
  only evidence behind a rule); (d) narrative markers `found the hard way|confirmed directly|used to|
  previously|originally|at the time|was once|no longer|now (fixed|gone)|this session`; (e) version
  strings (`1.26`, `1.28`, Microdot tags, Node, GCC) stated as current.
- **Where**: all living `.md`, code comments, `pyproject.toml`/`ci.yml` comments, test docstrings.
- **NEW vs known**: DP section 6 rows 1, 5, 27; OR61.a site list; HARVEST DOC DRIFT (226); G9/R11.
  NEW = the rest; (d) is inventory for B4 (count per file, list only owner-matter ones).

## B. Grounding (primary sources at the pinned versions)

### RP07 Platform and runtime claims not true at the pinned MicroPython
- **Why it recurs**: claims written from memory or general Python knowledge (CLAUDE.md standing
  practice). HR 2.2: `asyncio.run()` mechanism, `ENODEV` from zero-length I2C writes, timestamps to 2106
  not 2037, `const()` importability, no FPU, `bool` not an `int` subclass, `reset_cause()` reads
  `WDT_RESET` for every reset, filesystem file shadows a frozen module (OR59), `I2C.deinit()` "backwards"
  (F.5.1), FRAM SPI "timeout-wrappable" (LEAD 1 #2), OR55 `gc.collect()` completes on return,
  `getaddrinfo` status stale (C04). P11.
- **Instance shapes**: (a) any sentence asserting how a MicroPython/rp2/asyncio/lwIP/CYW43 call behaves
  (raises, blocks, returns, allocates, yields, is atomic, is safe in IRQ) — code comments, docstrings,
  docs, test names and assertion messages; (b) **undeclared** reliance in code: a construct whose
  correctness depends on such behaviour with no comment (e.g. catching `OSError` where the call raises
  `ValueError`/`MemoryError`; relying on `wait_for` cancelling a sync call; `struct.pack` truncation;
  `[x] * n` ranges; `Timer.init()` `ENOMEM`; soft-callback drop) — verify against `…/scratchpad/mp`;
  (c) CPython-isms that differ on MicroPython (`str.format` specs, `dict` ordering assumptions, `int`
  width, exception attributes, `json` leniency `b087dc7`).
- **Where**: `src/`, generated-code templates in `buildgen/codegen.py`, `digital_twin/`,
  `tests*/`, SPECIFICATION.md Part F/I, CLAUDE.md, READMEs.
- **NEW vs known**: harvest PLAT (400) and every PLATFORM item; HR 2.2's 19; G4/R01-R36; DP section 6.
  NEW = claims or reliances not among them, and harvested PLATFORM items now found false.

### RP08 Chip and datasheet claims and constants
- **Why it recurs**: SCD30 FRC readback is volatile (G3/R37) and NVM reachable over REST (DP 6 row 2,
  "zero REST-pushable fields" false); SCD30 per-field NVM semantics had to be re-derived (OR42.b); GPIO
  table narrower than RP2040 Table 279 (OR53); BMP3xx IIR tuple (`2bda920`); SGP40 feature-set removal
  given two reasons (DP 6 row 24); SGP40 general-call effect misstated as "resets the whole bus" (OR64);
  McCamy/Stull ranges (HR 3.4); owner-tested waits lost (G3/R30).
- **Instance shapes**: (a) every command code, register address, bit mask, CRC polynomial/init, timing
  (wait, power-up, conversion), range/limit, unit, scaling formula and default in `src/` drivers,
  `digital_twin/` chip fakes, `buildgen/pico_gpio.py`, `devices/*.toml` comments and `@limits` tags,
  checked against `datasheets/` (page/table cited or not); (b) behaviour statements about a chip
  ("persisted", "volatile", "self-clears", "general call", "idle after") without a page cite; (c) the
  same constant with different values in driver, fake, test and doc.
- **Where**: `src/asy_*_driver.py`, `src/asy_fram_*`, `digital_twin/_*chip*.py` and fakes, tests
  expected values, SPEC Parts C/M, DEVICE_REFERENCE.md, `devices/*.toml`. Datasheets: `datasheets/`
  (OR80 moves them to a submodule at the same path — cite paths unchanged).
- **NEW vs known**: harvest SENS/BUS/STOR PLATFORM items; G3/R29-R30, R37, R43, R45-R47, R58, G5/R28-R29,
  G4/R25; OR42.b field table. NEW = uncited or wrong constants and claims.

### RP09 Host-versus-target divergence (Unix port, fakes, twin)
- **Why it recurs**: the twin "was not always tracked along" (OR17); fakes richer than silicon or with a
  different signature (G2/R05, G2/R23); Unix-port behaviour unlike rp2: `mktime` and `$TZ`, `gmtime`
  tuple length (`cc911be`), float64 vs float32 (G5/R45), 63-bit vs 31-bit small ints, `select.poll` on
  non-fd objects hangs on GitHub runners (CLAUDE.md), async SIGINT (Part F.6/B.14), missing
  `getsockname()`; stub defects (`asyncio.Future`, `NotImplemented`, `Timer()` overloads); `I2C/SPI
  deinit()` fakes vs real no-ops; twin heap figures quoted as board figures (G4/R51).
- **Instance shapes**: (a) a fake/twin method whose signature, return, raise set or side effect differs
  from the real MicroPython object (`tests/machine.py`, `tests/network.py`, `digital_twin/machine.py`,
  `network.py`, `neopixel.py`, chip fakes) — compare against `typings/` stubs and `…/scratchpad/mp`
  port sources; (b) a fake that succeeds where silicon raises, or never produces a documented failure
  (EIO on 32+ byte SPI reads, ENOMEM, ETIMEDOUT, NAK); (c) code or tests correct only in float64/big-int
  semantics (`float(x) == int`, accumulations, `2**24` boundary — cf. `float_boundary_2pow24.py`);
  (d) tests passing only because of Unix-port specifics (TZ, heapsize, poll); (e) twin timing/electrical
  models tuned to an assumption rather than a measurement (OR17.a (3)); (f) unit fakes and twin fakes
  exposing the same test API with different conventions (harmonization 32).
- **Where**: `tests/` fakes and harnesses, `digital_twin/`, `typings/` (generated, read-only), `src/`
  arithmetic, `tests_hardware/device_scripts/` (target-side truths to compare with).
- **NEW vs known**: harvest TWIN LIMIT (150), TEST LIMIT/WORKAROUND; G2/R05-R07, G2/R23, G4/R21,
  G4/R30-R32, G5/R45, G6/R56, G7/R03-R17; OR17.a fidelity table seed (HR 3.3). NEW = undeclared
  divergences (no LIMIT comment at the site).

## C. One source of truth

### RP10 Hard-coded variants and device-set assumptions
- **Why it recurs**: wozi and dev were the templates for buildgen and "left traces allover" (OR78);
  OR43.a (3), OR54.a (1), OR71.a (4) (no per-driver allow-lists), OR74 (ISL29125 scope is a fact, not a
  rule), OR72.a (10) (dev meets every device's bar); the wozi-build-on-dev incident (CLAUDE.md).
  Calibration: 145 files outside `devices/` and `*.md` contain the word `wozi` or `dev`.
- **Instance shapes**: (a) variant names as literals (`wozi|dev|arzi|grkizi|klkizi|schlafzi|neu`) in
  code, CI, config, tests, twin, website, scripts — word-bounded, excluding prose uses of "dev" as
  "development" (classify each); (b) defaults: `device="wozi"`, `DEFAULT_DEVICE`, argparse defaults,
  `KNOWN_DEVICES`, `_DEVICES` tuples, `package.json` pretest args, CI matrix literals; (c) per-device
  test files or wrappers instead of generic bodies parametrised over `devices/*.toml`; (d) count
  assumptions (`== 6`, "six devices", `len(...) == N`); (e) "golden"/"reference" roles given to one
  device; (f) branches on device identity (`if device == …`, `name.startswith("dev")`); (g) driver-set
  assumptions: code or tests assuming every device has SCD30/FRAM/NeoPixel, allow-lists of which device
  may wire which driver (`test_isl29125_only_present_on_dev`); (h) docs stating a device fact as a rule
  ("never will", "must not gain one").
- **Where**: whole repo except `devices/`, `audit/`, legacy, `arduino/`, `ext/`, `datasheets/`;
  docs for (h) only.
- **NEW vs known**: OR78.a (5) is only a count and ten example files; G8/R01 State (`js/app.js:16`,
  `package.json:10`, `_DEVICES`, 18 wrappers, `["wozi","dev"]`, `tests_scripts/test_device_tomls.py:422-426`,
  `DEVICE_REFERENCE.md:100-101`); G1/R36, G7/R24, G2/R13. Output here is the **per-site inventory**
  (every site, classified by shape a-h, with its derivation source: TOML property, runner argument or
  derived set) — all sites beyond G8/R01's are NEW.

### RP11 Undeclared mirrors and two-sided contract drift
- **Why it recurs**: `src/`↔`js/` mirror obligations (Part G), hand-written `html/definitions/*.json`
  (OR43.a (3)), SPEC L.3 key list vs `buildspec.py`/`validate.py` (LEAD/R11), test copies of product
  values (G1/R41), errno tables vs website/`/status` text (OR28.a (3)), mock server "known gap" long
  fixed in the backend (DP 6 row 17), `tests_js` comment "matches none of dev's real groups" false (DP 6
  row 18), README CLI reference vs `--help` (OR15.a (1)), twin wiring vs buildgen's plan (G8/R15), twin
  vs hardware HTTP clients (G7/R26), "Unchanged" result that never fires (`b373034`), legacy-derived key
  spellings (OR58.a).
- **Instance shapes**: (a) the same literal set (keys, route paths, field names, units, ranges, error
  numbers, result words, timeouts, port numbers, pin names) defined in two or more files with no test
  pinning one to the other — mechanical: collect string/number literals and literal lists/dicts by AST
  (Python) and by parse (JS, TOML, YAML, JSON), cluster equal values across files; (b) both sides of an
  interface disagreeing: REST handler keys vs `@web` tags vs `js/` consumers vs `mockdata/`/mock server
  vs `tests_js` fixtures vs SPEC tables; result words and envelope shape (`res`/`result`, OR69.a (4));
  TOML keys in `devices/` vs `buildspec.py` vs `validate.py` vs SPEC L.3; UART constants vs Part J vs
  UART_C_PORT_CHANGELOG.md; (c) a MIRROR the harvest recorded whose two ends have since diverged.
- **Where**: `src/`, `js/`, `html/`, `mockdata/`, `tests_js/`, `buildgen/`, `devices/`, `tests*/`,
  `digital_twin/`, SPECIFICATION.md Parts A.8/C/H/J/L, README.
- **NEW vs known**: harvest MIRROR (~440 declared); G6/R41, G6/R48, G7/R26-R28, G7/R30, G8/R12-R15,
  G9/R07, G10/R12, LEAD/R08, R11; DP section 6. NEW = undeclared duplicates and new divergences.

### RP12 Unregistered tunables; limits moved without a measurement
- **Why it recurs**: OR30 (a register is owed); Run 7 budgets widened to 90 s on a disproven hypothesis
  and never narrowed (`6a91514`→`7079757`); `-X heapsize` 8M→32M→16M; `max-args` raised four times by
  agents (`2badee1`, `8e70914`, `9751814`, `740fab5`, DP 6 row 22); agent-added hard-coded DNS fallback
  (`a6abe13`, OR56 (2)); CI `timeout-minutes` cancelling a passed suite (CLAUDE.md, run `34755468619`).
- **Instance shapes**: (a) numeric literals that are tuned rather than derived (timeouts, retries,
  backoffs, intervals, sleeps, budgets, thresholds, sizes, heap sizes, soak durations, tolerances) in
  `src/`, generated-code templates, `digital_twin/`, `scripts/`, `tests*/`, `ci.yml`, `package.json`,
  `vitest.config.js` — each with: location, dependants, how determined, margin (none today → all NEW for
  the OR30 register); (b) history: every commit that raised/widened one (`git log -p -G '(timeout|
  _ms|_s|retries|heapsize|max-|minutes|budget|interval)'`) with or without a stated measurement;
  (c) values configured in two places (CI and runner) that disagree; (d) hard-coded values that should be
  config (hosts, servers, ports, intervals a user could reasonably change).
- **Where**: as (a); git history for (b).
- **NEW vs known**: OR30.a's named examples; G4/R54, G4/R64, G7/R34, G8/R37, G8/R36; harvest ASSUME
  "single dated measurement" items. The inventory is new work (the register does not exist yet); flag
  NEW only for (b) raises without measurement and for (d).

## D. Runtime behaviour (firmware: `src/` and the generated modules)

For all of D: read the generated `sensortask_<device>.py`/boot entry through their templates in
`buildgen/codegen.py` (do not build); treat generated code as `src/` (OR22).

### RP13 Harmless abnormal condition not handled in place (and hardware faults over-contained)
- **Why it recurs**: the NTP service stalled its task on an unreachable server and leaned on the
  supervisor's restart and decay counters, able to drive a reboot (OR18); OR31.a: a task either works or
  ends on what it cannot handle, never stalls silently; OR18.a: a missing/defective/stalled chip or a
  config/hardware mismatch **must escalate**, never be contained (the mirror-image error).
- **Instance shapes**: (a) inside a task coroutine: `raise`, `return` or an unhandled exception path
  triggered by a network/peer/client condition (timeout, DNS failure, refused, EOF, bad reply, WLAN
  down, NTP no reply); (b) an `await` with no deadline on an external event in a task that has other
  duties (`await ev.wait()`, `read()` with `timeout_ms=-1`, `wait_for` missing); (c) a retry loop without
  backoff/bound, or a backoff that interacts with the supervisor's counters; (d) the hint OR18 names:
  **tests of normal situations that accept or expect an `errno`/`wrnno`, a supervisor restart or a
  nonzero `ErrCount`** — grep `tests/`, `digital_twin/`, `tests_hardware/` for asserts on
  `errcount`/`ErrCount`/`wrnno=`/`errno=`/`restart` in happy-path tests; (e) the mirror: `except`
  around chip I/O that swallows a persistent chip failure and keeps the task alive forever, suppressing
  escalation (OR18.a).
- **Where**: `src/` tasks (25 `create_task` sites), `system_service.py`'s supervisor, generated
  `main()`, tests as in (d).
- **NEW vs known**: OR18 (NTP fixed), G6/R23, G5/R15, G5/R21, G3/R68, G6/R24, G6/R27, OR31.a. NEW = other
  tasks/paths and every test of type (d).

### RP14 Silent failure: swallowed errors, failure reading as success
- **Why it recurs**: OR16 "silent failures and losses"; a cut response must not read as success
  (G6/R45); an uninitialised bus must not look like success (G3/R20); a `ResetErrors` write failure
  answered as success (B08, OR70.a (6)); bare `except` kept visible on purpose (E722, L39); "A caught
  MemoryError that merely didn't crash anything is still a design defect" (CLAUDE.md).
- **Instance shapes**: (a) `except …:` whose body neither logs (`err_s`/`wrn_s`/print path), re-raises,
  nor returns a failure sentinel the caller checks (`pass`, `continue`, bare `return`, `return None`
  where `None` is also a success value); (b) a callee's failure sentinel ignored by its caller
  (`False`/`None`/`-1`/`b""` returns not checked — cross-reference each never-raise function's callers);
  (c) partial writes/reads treated as complete (`write()` count ignored, `readinto` length ignored);
  (d) `res: "OK"`/"Valid" returned after a store or chip write failed; (e) JS `catch {}`/`.catch(() =>
  {})`, promise rejections not surfaced on the page (G7/R38); (f) shell `|| true`, `2>/dev/null` on a
  step whose failure matters; (g) `finally` blocks that swallow via `return`.
- **Where**: `src/`, generated code, `js/`, `scripts/`, `toolchain/`, `buildgen/` (host side: OR23.a
  error contract — every error aborts nonzero), `digital_twin/` runners.
- **NEW vs known**: harvest SUPPRESS "exceptions swallowed with a comment" (declared); G5/R16-R17,
  G6/R44-R45, G3/R20, G3/R25, G8/R06, G7/R38. NEW = undeclared swallows and unchecked sentinels.

### RP15 Silent fallbacks and undecided substitutions
- **Why it recurs**: behaviour added by an agent with no decision, which later conflicted with the
  owner: public DNS servers hard-coded and appended on every lookup (`a6abe13`, OR56 (2)); a "silent
  uncompensated-VOC fallback" (`368fa83`, overtaken by OR66); a renamed stored-config key silently
  replaced by its default and the file rewritten (`config_manager.py:446-462`, OR52.a (2)); JSON
  leniency degrading to per-key defaults (`b087dc7`); SCD30 not-ready cycle reusing the last reading
  with a fresh timestamp (`110f3db`, kept as the named exception). P7: evidence must stay readable.
- **Instance shapes**: (a) `or DEFAULT`, `.get(key, default)`, `if x is None: x = …`, `except: value =
  default` where the substitution changes observable output (a reading, a setting, a stored value, a
  published field) without a log entry or a flag in the response; (b) "fallback", "default to",
  "silently", "best effort", "last known" in code or comments (calibration: `fallback` in 7 `src/`
  files); (c) stale data re-published as fresh (timestamps refreshed on reuse); (d) clamping instead of
  rejecting (G6/R16 "refused, never clamped", G3/R06 "gated, never clamped"); (e) type coercion that
  hides a bad value (int→float precision L21 accepted within bounds; bool as int, G5/R43).
- **Where**: `src/`, generated code, `js/` (rendering defaults), `buildgen/` (TOML defaults filled
  silently — G8/R09 wants explicit defaults).
- **NEW vs known**: OR56.a (2), OR66.a, OR52.a (2), HR 3.3 "stale as fresh", G3/R06, G3/R22, G5/R37,
  G6/R16, G8/R09. NEW = every other undecided substitution (owner-matter if it changes a published value).

### RP16 Log-evidence integrity (one event one entry, right class, one number, no flood)
- **Why it recurs**: UART fault logs an error and a warning (OR56 (1)); a failed sensor read logs the
  driver's `errno` 11 and `_error_check()`'s streak `errno` 1 (`base_classes.py:223`); SGP40 `W13` flood
  found only on the bench (`83c9920`, OR35); six modules each invented a repeat flag (OR35.a (4));
  numbers reused with different meanings (OR28); FRAM evidence erased by routine `ResetErrors`
  (CLAUDE.md incident); expected conditions must log nothing (G5/R21); saturation is a field, not a log
  entry (G3/R54).
- **Instance shapes**: (a) one occurrence reaching two `err_s`/`wrn_s` calls — callee logs and caller
  logs again, driver and base class both log, error then warning for the same event (trace every
  `err_s`/`wrn_s`, 219 sites in `src/`, through its callers); (b) a log call inside a loop or periodic
  path with no guard against repetition (flood candidates); (c) the same condition logged with different
  numbers in different modules, or one number with two meanings; `err_s` for a warning-class condition
  or vice versa; (d) log calls on expected/startup conditions (first boot without config, NTP not yet
  synced, WLAN connecting); (e) failure paths that log nothing persistent (L-DIAG: "knowingly silent"
  must be recorded); (f) `errno=`/`wrnno=` passed as positional or computed values (G10/R18).
- **Where**: `src/`, generated code, `print_log.py`, `base_classes.py`, `system_service.py`; the
  website/`/status` text mapping; tests asserting log content.
- **NEW vs known**: OR56.a (1) two cases, OR35's six modules, G3/R01-R02, G5/R19-R22, G6/R20, G3/R54.
  NEW = every other double entry, flood path, number clash, or expected-condition log. This is the
  seed inventory for B1's catalog (OR28.a) — list every site found, not a sample.

### RP17 Construction and boot completeness; lazy setup; boot order
- **Why it recurs**: loggers' store setup runs lazily inside tasks (`webserver._run()`,
  `SCD30_Reader._init_scd()`, and more found by V2/V08); generated `main()` starts timers before tasks
  against the owner's order (OR47.a (1), OR75); the webserver waits for the NTP sync (G1.091);
  `conn.setup()`/`ntp.setup()` never called in the old flow (CLAUDE.md); a half-built object after a
  failed setup (OR26.a); post-construction registration (OR46.b forbids); a Timer allocated but never
  referenced hung `start_timers()` (`3bb015b`).
- **Instance shapes**: (a) `.setup()`/`.initialize()`/`_init_*()` called from a task body or a request
  handler rather than the boot batch; (b) attributes set to `None` in `__init__` and filled later, with
  uses not guarded by a readiness gate (Part C.13); (c) `register_*`/`add_*`/`set_*_callback` methods
  called after construction to complete an object; (d) a module declared in a TOML but not constructed,
  set up, started, supervised, routed, rendered or FRAM-wired (OR16.a (1)) — cross-check `buildspec.py`,
  codegen templates and each driver's starter list; (e) boot steps fired off unawaited (`create_task`
  during boot without a join); (f) steps between two watchdog feeds whose worst case is unknown (OR31.a
  (2)); (g) `setup()` failure paths that leave the object reachable and used.
- **Where**: `src/` constructors, `setup()`s, `system_service.py`, `buildgen/codegen.py` templates,
  `buildgen/buildspec.py`, `devices/*.toml`.
- **NEW vs known**: G5/R05, G5/R06 (+ V2/V08 list), G3/R33, G5/R13-R14, G5/R01, harmonization 12, G1/R30.
  NEW = other sites.

### RP18 Timers, ticks, clocks and long-uptime arithmetic
- **Why it recurs**: unreferenced `Timer` garbage-collected (`3bb015b`); soft-callback drop and the
  8-deep soft-IRQ queue (F.1); one-shots armed from the previous callback accumulate latency (OR47 gap
  (a)); 1 s timers at arbitrary phases (OR47 gap (b)); stored tick ages beyond 2**29 ms; RTC steps
  (LEAD/R05); months of uptime (LEAD/R04); counters wrapping (G9/R09); P1.
- **Instance shapes**: (a) `Timer(` results not stored on a long-lived object; `Timer.init()` without
  `ENOMEM` handling (Part F); (b) callbacks doing more than set a flag (G5/R08); (c) tick arithmetic with
  `-`/`+`/`<` instead of `ticks_diff`/`ticks_add`; stored `ticks_ms()` values compared after unbounded
  time; `sleep_ms`/`wait_for`/`Timer(period=)` given values that can exceed limits or the 8,000 ms
  watchdog; (d) wall-clock (`time.time()`, `localtime`, `mktime`, RTC) used for intervals or ages;
  behaviour across an RTC step or before first NTP sync; (e) counters (`ErrCount`, uptime, restart
  counters, UIDs, sequence numbers) with no wrap analysis at service life; (f) schedules derived from
  "k·slot after the previous event" rather than one shared start.
- **Where**: `src/` (17 `Timer(`, 30 `ticks_ms(` sites), generated code, `js/` polling timers (LEAD/R09),
  `digital_twin/` clock models.
- **NEW vs known**: G4/R07, G4/R15-R16, G5/R07-R10, G6/R30, G6/R37, G9/R09, LEAD/R04-R05, harvest L-TIME
  items. NEW = other sites.

### RP19 Loop blocking and synchronous waits
- **Why it recurs**: UART reads waiting `timeout_char` per byte inside a non-yielding call (4.4 ms per
  frame, CLAUDE.md, F.5.8); the mirror (idling at transaction rate, F.5.9); "a write is fast enough not to
  matter" disproven on silicon — a flash write reset a live connection (A2-04, fixed by WP5's deferred
  flush); FRAM per-command hold accepted (OR72.a (2)); growing GET bodies must stream (I.4). F.3.
- **Instance shapes**: (a) `time.sleep*` in any `async def` or code reachable from one (2 sites in
  `src/`); (b) stream reads not clamped to `any()` or without a yield between rounds; (c) synchronous
  loops over client- or configuration-sized data in handlers/tasks (json encode/decode of growing
  dicts, list builds, CRC over large buffers without yield); (d) file I/O (`open`, `json.dump`,
  `os.rename`) on the request path; (e) bus transactions whose worst case exceeds the timing budget
  table (G4/R64); (f) `await` inside a lock held across slow I/O (overlaps RP21).
- **Where**: `src/`, generated code, `ext/microdot.py` call sites (not the file), `js/` (main-thread
  blocking loops).
- **NEW vs known**: G4/R40, G4/R43, G4/R55-R57, G4/R61, G5/R52-R53, G4/R22. NEW = other sites.

### RP20 Memory discipline (bounded, reused, collected only where allowed)
- **Why it recurs**: the whole Part I remediation; peer-sized UART allocations (`_accept_set()` up to
  ~64 kB, `readline_until_complete()` unbounded, C12/C13 deferred); gate text matching only the class
  name (see RP29); `gc.collect()` outside the boot placement (OR39/OR40; twin sampler exception OR54;
  `segfault_stress_repro.py:92` a tool use); coverage builds inflating allocations 4-5x (E.5.2).
- **Instance shapes**: (a) allocations sized by input (`bytearray(n)`, `bytes(n)`, `[x] * n`, `read(n)`,
  `.split()`, `.decode()` of client/peer data) without a clamp first (G4/R39); (b) per-call churn on hot
  paths: string concatenation in loops, f-strings/`%` in periodic paths, temporary lists/dicts/tuples
  per sample, closures/bound methods created per call, `json.dumps` of growing dicts (should stream);
  (c) `except MemoryError` that continues as normal (a design defect unless a real degradation
  alternative exists, OR26.a); (d) `gc.collect()`/`gc.threshold`/`gc.disable` anywhere outside the
  allowed sites (70 `gc.collect(` occurrences across `src/`, tests, twin, hardware, build — classify
  each as boot-placement / measurement-baseline / other); (e) long-lived buffers allocated late (after
  task start) rather than at construction (G4/R42); (f) unbounded growth: lists/dicts appended per event
  with no cap (test-side bookkeeping too, G7/R21).
- **Where**: `src/`, generated code, `digital_twin/`, `tests*/`, `tests_hardware/device_scripts/`.
- **NEW vs known**: G4/R38-R53, G6/R21 (C12/C13), G7/R21, OR39.a/OR40.a/OR54.a site lists, harvest MEM.
  NEW = other sites.

### RP21 Concurrency and cancellation safety
- **Why it recurs**: interleavings found by accident (OR37, OR41); `GET /sensors` could tear against a
  PUT (C15, OR71.a (8)); eight bare `asyncio.Lock()` outside `base_classes.py`, two of them bus locks
  (V2/V09); explicit `acquire()` sites (7 in `asy_wifi_service.py`, 5 in `asy_fram_driver.py`, V4/V16);
  shared-flag restart race (`3bb015b`); Unix-port task leaks across tests (CLAUDE.md); CLAUDE.md's
  four-tier bus-hazard rule extended to every shared resource (OR41.a (3)).
- **Instance shapes**: (a) read-modify-write of shared state (`self.x`, module globals, dicts shared
  between tasks) with an `await` between read and write and no lock; (b) `.acquire()` not paired with
  `release()` in `finally`/`async with`; locks held across `await asyncio.sleep`/network/bus I/O
  (L-CONC); nested lock acquisition in varying order; (c) state left inconsistent if `CancelledError`
  arrives at any `await` (flags set before and cleared after an await without `try/finally`);
  (d) per-sample state read after an await (G3/R50); (e) multi-field snapshots assembled across awaits
  (tearing); (f) `create_task` results not kept or never cancelled/awaited (leak, lost exception);
  (g) module-level singletons mutated from both tasks and callbacks.
- **Where**: `src/` (13 `asyncio.Lock()`, 16 `.acquire(` sites), generated code, `digital_twin/`
  runners, `js/` (overlapping fetches, G7/R33).
- **NEW vs known**: G5/R11-R12, G6/R26, G6/R51, G6/R54, G3/R50, G3/R67, G2/R10, G2/R14-R15. NEW = other
  sites.

### RP22 Limited-endurance writes and compare-before-write
- **Why it recurs**: the promoted SCD30 driver lost legacy's compare-before-write (OR42.a (2), "serious
  gap"); `force=True`/field-order semantics lost (OR42.b/c); owner rule: no limited-endurance write
  without a user/API action, one repair per boot (OR70.a (3), OR71.a (2), harmonization 37); a
  confirmed setting lost on power loss between response and flush (C01); tests and tools wearing flash
  (CLAUDE.md wear rule; `config_HWTEST_*.cfg` scratch, OR38.a (4)).
- **Instance shapes**: (a) every write path to the flash filesystem (`open(..., 'w'|'a'|'wb')`,
  `json.dump`, `os.rename`, `os.remove`, `os.mkdir`) and to SCD30 NVM (commands 0x0010, 0x4600, 0x5102,
  0x5204, 0x5306, 0x5403, 0x0104) in `src/`, generated code, device scripts, `tests_hardware/`,
  `scripts/`, `toolchain/` (mpremote `cp`/`rm`/`mkdir`), with its trigger and worst-case rate;
  (b) setters writing without comparing to the current value; (c) writes reachable from a timer, retry,
  supervisor restart or boot loop; (d) values whose form changes across save/reload (a config that never
  settles — type coercion, float formatting, key order), defaults that fail their own validation;
  (e) client-side repeats: website/tools re-sending unchanged values or retrying PUTs (OR42.a (3));
  (f) host-side churn in routine runs (twin state files, coverage data, archives) — CLAUDE.md's SSD rule.
- **Where**: as (a); `js/render.js` sparse PUT.
- **NEW vs known**: OR42.a's enumerated sites (`config_manager.py:375-376, 476-477`, `_set_dict_cfg()`),
  G1/R04-R09, G3/R35-R36, G5/R34-R35, G5/R40-R41, G4/R61, G7/R31, G8/R44. NEW = other write sites or
  triggers.

### RP23 Input robustness (malformed, oversized, non-finite)
- **Why it recurs**: trusted-LAN threat model keeps "a crash from bad input stays a defect" (OR52.a (3),
  OR49.a); non-finite values emitted as invalid JSON (G4/R28); `bool` accepted as `int` (G5/R43);
  identity strings bounded in characters not bytes (G6/R28); `NTP_Host` 1,024 bound re-decided (OR70.a
  (4)); captive DNS must stay silent on bad input (G6/R24).
- **Instance shapes**: (a) `float()`/`int()` on client input without finiteness/range checks; `isinstance(x,
  int)` that admits `bool`; (b) `len()` bounds in characters where bytes matter (UTF-8); (c) indexing,
  slicing or unpacking client/peer data without length checks; (d) JSON parse of unbounded bodies;
  nested structures accepted where scalars are expected; (e) validation performed after the value was
  used or stored (G4/R12); (f) JS rendering of device strings without escaping (G5/R58); (g) UDP/DNS/NTP
  reply parsing trusting lengths and offsets from the packet.
- **Where**: `src/` handlers, config validation, `captive_dns.py`, `asy_dns_client.py`,
  `asy_ntp_client.py`, `asy_udp_socket.py`, UART receive, `js/`.
- **NEW vs known**: G4/R10, G4/R12, G4/R28, G5/R43, G5/R57-R58, G6/R16, G6/R24, G6/R28, G6/R31, G6/R52,
  harvest SEC. NEW = other sites.

## E. Code material

### RP24 Not one material: incomplete retrofits and variant shapes for one job
- **Why it recurs**: "rules are written once and then not applied everywhere" (HR 2.1: D.15 member order,
  dynamic-import ban, "no warning for expected startup conditions", derived device set, `max-args`,
  generated code at the `src/` bar); OR13 "added features incompletely retrofitted, or already existing
  ones forgotten in new code"; OR24 "one material, change, don't flag"; OR46.b "adopt the solutions at
  any place they improve tidiness"; six per-module repeat flags vs one central rule (OR35); bare locks vs
  `LockedValue` (V2/V09); 8 async modules without the `asy_` marker (V4/V18); four byte-identical
  `*_DeviceSession` classes (V4/V13); Part G's grep-for-the-shape rule (G.3).
- **Instance shapes**: (a) for each Part G shared primitive (numeric validation/coercion, callback
  dispatch guarding, response envelopes, locked state, logging, streaming responses, config objects,
  starters, `readfrom_mem_into` reads, compare-before-write), every sibling site doing the same job by
  hand — AST shape search; (b) equivalent methods across drivers/services with different names, argument
  order, return conventions, raise behaviour or result words (`get_cfg`/`get_config`, `setup` returns
  `bool` vs raises); (c) classes violating D.15 member order or comment placement; (d) module shape
  divergences from the driver template (G10/R10); (e) identical or near-identical code blocks across
  files (clone detection by normalised AST hashes) in `src/`, tests, twin, `tests_hardware/`, scripts;
  (f) conventions machine-checkable but unchecked (LEAD/R17 list).
- **Where**: `src/`, generated code, `buildgen/`, `digital_twin/`, `tests*/`, `scripts/`, `toolchain/`,
  `js/`.
- **NEW vs known**: G10/R07-R37, G5/R12, G5/R43, G5/R50, G3/R01, G6/R40, LEAD/R17, SPEC Part G catalog.
  NEW = sites not named there. OR24.a: consistency changes are made directly in execution, so list all.

### RP25 Test seams in the product
- **Why it recurs**: OR20/OR36 (no test-only code in business logic, "testing must adapt to fit the code,
  never vice versa"); examples found while recording: `asy_isl29125_driver.py:1064-1066` address
  parameter "exists only for test injection", `asy_ntp_client.py:44-45` non-`const()` port "so tests can
  redirect it", `asy_uart_link_driver.py:57` public `self.uart` "the digital twin reaches"; the
  `asy_dns_client.py:20-21` non-const list (G2/R11 State); harmonization 10 (BMP3XX's address is hardware
  and stays); V3/V11 (no port redirect seams).
- **Instance shapes** — the **undeclared** ones (declared ones were harvested): (a) public attributes,
  parameters, methods or module globals of `src/` whose only readers/writers outside their module are in
  `tests/`, `digital_twin/`, `tests_hardware/` (cross-reference every name by grep/AST); (b) module
  constants left non-`const()` that tests reassign; (c) constructor parameters with defaults that no
  generated code or TOML ever passes; (d) hooks/callbacks, counters, `_debug`/`_test` attributes,
  `if __name__` blocks, env checks, extra return values used only by tests; (e) `@web`/`@wiring` tags or
  config fields present only to serve tests; (f) same in `js/` (exports only `tests_js/` imports) and
  in generated code (names only twin runners read). Keep OR36.a (3): general-purpose driver API that is
  a function of the hardware stays.
- **Where**: `src/`, generated code, `js/`, `html/`; reference search over `tests*/`, `digital_twin/`.
- **NEW vs known**: OR36 examples, G2/R11 State, G6/R34, G7/R01, G3/R26, harvest INVAR "shaped for a test
  hook" items. NEW = the rest.

### RP26 Dead code, leftovers and workarounds outliving their cause
- **Why it recurs**: "many changes were done over many iterations" (OR46); retired mechanisms still
  described (`get_long_block_lock` 5 files, `cfg_schema` kept for a deleted consumer, DP 6 row 20); the
  heap-unlock helper kept after the root fix (OR52.a (6)); budgets widened for a disproven cause
  (`6a91514`); stub repairs and poll-set prewarm with removal triggers (G4/R35, G7/R12); harmonization 30
  (unreachable defensive branches removed unless an extension-point or documented-runtime guard).
- **Instance shapes**: (a) functions, methods, classes, constants, parameters, config keys, `@web` fields,
  error numbers never referenced (reference search including buildgen's by-name resolution of drivers
  and tags, and JS/CSS consumers); (b) branches no input reaches (conditions fixed by construction,
  `isinstance` checks against types never passed); (c) workaround code whose trigger condition is gone
  (version checks against versions no longer pinned, comments naming a fixed upstream issue, retries
  for a fixed flake); (d) test helpers, fixtures, `mockdata/` files, scripts, CI steps, npm scripts
  nothing uses; (e) CSS rules and JS functions no page uses; (f) "kept for compatibility/legacy"
  justifications (with RP06 (a)).
- **Where**: all code scopes; host side included (`buildgen/`, `scripts/`, `toolchain/`, `tests_scripts/`).
  A dead-code tool may be run ad hoc in the scratchpad (OR46.a (2) allows it during the audit, never in
  `lint.sh`); every candidate confirmed by reference search.
- **NEW vs known**: G5/R54, G6/R55, G4/R34-R35, G7/R12, OR63.a (Codecov), harvest WORKAROUND (~150
  declared, removal triggers); DP 6 row 20. NEW = everything else (no prior dead-code pass exists).

### RP27 Under-exploited features and unwired values
- **Why it recurs**: OR13 "implemented features which are not or only partially exploited … missed
  opportunities"; OR43 (every module value to the API, every API value to its page); owner-added values
  found missing: free heap in `/status` (OR71.a (7)), DNS server error history (OR72.a (8)), ISL29125
  calibration suitability (OR76), `reset_reason` (OR60); `@limits` on every TOML numeric (G10/R34).
- **Instance shapes**: (a) values a module holds (readings, settings, status, counters, error logs,
  derived values) not reachable through any route, or reachable but not rendered on its page;
  (b) mechanisms built but used by only some consumers (twin fault vocabulary hooks no test drives,
  buildgen validation dimensions applied to some fields only, notification signals no path triggers,
  config fields no code reads); (c) legacy-exposed values and UI functions missing from the new API/site
  (with RP37); (d) datasheet features the driver implements half-way (a mode settable but not readable,
  a status bit read but not surfaced); (e) GET returns fields PUT does not accept or vice versa.
- **Where**: `src/` modules vs `asy_webserver_service.py` routes vs `@web` tags vs `js/`/`html/`;
  `digital_twin/` fault hooks vs tests; `buildgen/validate.py` vs `devices/*.toml`.
- **NEW vs known**: G6/R39, G7/R29, G9/R05, G6/R47, G7/R30, G10/R34, OR71.a (7), OR72.a (8), LEAD/R19.
  NEW = other unwired values and half-used mechanisms (this is the seed of OR43.a's value inventory).

## F. Tests

### RP28 Blank, weak or characterisation tests
- **Why it recurs**: OR19 (coverage-driven tests that do not bite); OR19.a red flags; expected values
  copied from current output (OR19.a (2), harmonization 29); a characterisation test pinning a tear
  (`test_asy_webserver_service.py:1108-1137`, C15); a tolerance for a result word that "never fires"
  (`b373034`); "a check that re-asserts a stand-in's canned return".
- **Instance shapes** (mechanical pre-scan to seed B3, which reviews every test): (a) test functions
  with no assertion (`assert`, `raise AssertionError`, `expect(`, microtest helpers), or only
  `is not None`/`isinstance`/"no exception"; (b) assertions on values the test itself configured into a
  fake (`fake.ret = X … assert f() == X` with nothing in between); (c) `except …: pass` in tests;
  (d) loops asserting nothing or asserting inside a loop that may run zero times; (e) tolerances wider
  than the quantity (`abs(a-b) < 1e6`, `>= 0`); (f) log assertions checking presence not content;
  (g) expected values without an independent source (magic numbers equal to current output — check
  `git log -S` whether the expected value was changed together with the code); (h) tests whose name
  promises a behaviour the body does not check.
- **Where**: `tests/` (104 files), `tests_scripts/`, `tests_js/`, `tests_hardware/`, twin scenarios
  (`tests/_*_scenarios.py`, `digital_twin/`).
- **NEW vs known**: G2/R11-R13, G3/R13, harvest TEST LIMIT items. Everything found is NEW input to B3's
  per-test classification; list shapes (a)-(e) exhaustively, (g)-(h) as candidates.

### RP29 Silent blindness in gates, checks, runners and the CI graph
- **Why it recurs**: OR21 "several times"; memory gates matching only the class name while `src/` logs
  `str(e)` ("memory allocation failed") (CLAUDE.md, I.4(e)); `needs:` success-gating silently skipped
  every test lane under a red lint (CLAUDE.md); `continue-on-error` hid `build-settrace`-only failures
  (E.5.3); a gate that DESELECTS is invisible to the skip check (CLAUDE.md wear rule); a pass after
  retry reads as a plain pass (LEAD/R03); soak trend retry (V3/V12); twin assertions failing open
  (G7/R18); `timeout-minutes` cancelling a passed suite.
- **Instance shapes**: (a) grep-based pass/fail checks (log scans, marker lists, `grep -q`) whose
  pattern cannot match the real failure text, or whose input may be empty/missing and then passes;
  (b) `continue-on-error`, `|| true`, `set +e`, `if: always()`/`success()`/`!cancelled()` choices, `needs:`
  edges, path filters (G8/R50) — each checked for whether a real failure can still turn the run red;
  (c) runner exit codes: pipelines losing status (`| tee` without `pipefail`), background jobs not
  waited for or their status ignored, retries converting fail to pass without reporting (LEAD/R03);
  (d) skip/deselect/xfail/opt-in markers and `pytest.skip()`/`return` early in tests when a condition is
  missing (a vacuous pass, G2/R27); (e) checks that compare against a baseline the same run produced;
  (f) timeouts where expiry counts as success; (g) summary/verdict lines computed from partial data
  (a "clean" verdict that does not name deselected counts, G8/R40).
- **Where**: `scripts/`, `.github/workflows/ci.yml` and the composite action, `tests_hardware/conftest.py`,
  `harness.py`, `scripts/_digital_twin_ci_suite.py`, `scripts/_require_clean_hardware_run.sh`,
  `tests/microtest.py`, `package.json`/`vitest.config.js`, `tests_scripts/conftest.py`.
- **NEW vs known**: G1/R38, G2/R02, G2/R27, G7/R18, G8/R38-R43, G8/R49-R50, G8/R52, G8/R55, LEAD/R03,
  CLAUDE.md incidents, harvest SUPPRESS (gates). NEW = other blind spots.

### RP30 Orphaned, unrun or shadowed tests; investigation residue
- **Why it recurs**: OR16.a (2) (every test collected by some runner and CI job); OR33 ("deep tests
  without any real benefit left from several investigations"); instruments only in the scratchpad
  (`twin_wrap.py`, `validate_bench.py`, LEAD/R01); a host-side mirror deleted as dead code
  (`tests_hardware/bus_topology.py`, CLAUDE.md); Appendix B's investigation-born list.
- **Instance shapes**: (a) test files not matched by any runner glob or CI step (`scripts/test.sh`'s
  discovery, pytest `testpaths`/`python_files`, vitest `include`, hardware runner paths);
  (b) test functions the runner never discovers (wrong prefix for `tests/microtest.py`, nested
  functions, methods in non-collected classes); (c) **shadowed tests**: two `def test_x` with the same
  name in one module (the first silently lost), duplicate `it()`/`test()` titles in JS; (d) device
  scripts in `tests_hardware/device_scripts/` referenced by no flash/bench test; helpers and fixtures
  nobody imports; (e) tests whose docstring or name cites a closed investigation, incident, BACKLOG item
  or deleted plan (necessity verdict input, OR33.a) — list each with its original intent;
  (f) tests guarding behaviour that no longer exists (asserting a retired API is absent forever, a
  removed file's behaviour).
- **Where**: `tests/`, `tests_scripts/`, `tests_js/`, `tests_hardware/`, `digital_twin/`, `scripts/`,
  `ci.yml`.
- **NEW vs known**: G2/R02, G2/R17, G7/R25, LEAD/R01, Appendix B (B.1-B.3), harvest HW/TEST. NEW = other
  orphans, every shadowed test, residue not in Appendix B.

### RP31 Crosstalk and hygiene; test logic inside the DUT
- **Why it recurs**: OR20 "several cases" of tests integrated into the twin or board causing memory
  contention and false positives; OR38 "several occasions" of leftovers; two suites binding the same real
  ports looked like merge defects (CLAUDE.md, 2026-09-13); nested `asyncio.run()` segfault (CLAUDE.md);
  process-wide task leaks hanging exit (`microtest.py` `sys.exit`); `-X heapsize` flakes; device scripts
  overwriting the real FRAM logs and fabricating evidence (CLAUDE.md FRAM caveat).
- **Instance shapes**: (a) fixed ports, file names, directories or state files in tests/runners that
  another test, tier or parallel job also uses (19 `port = <literal>` sites in test scopes; `/tmp/<fixed>`;
  repo-tree writes); (b) setup without teardown on every path (failure and cancellation included):
  sockets, servers, timers, tasks, files, temp dirs, monkeypatched module globals and fakes not restored
  (G2/R03); (c) module-level mutable state in test files or fakes shared across test functions;
  (d) `asyncio.run()` reachable from inside a coroutine (CLAUDE.md rule); fake streams backed by a real
  `select.poll()` (CLAUDE.md rule); (e) test logic (assertions, load generation, measurement) living
  inside the twin process or on the board instead of a host-side driver (OR20.a, E.9); (f) runners that
  do not clear their own scratch before starting, or that delete evidence instead of archiving it
  (OR38.a (2)); (g) tests depending on order or on another test's side effects.
- **Where**: `tests/`, `tests_scripts/`, `tests_js/`, `tests_hardware/`, `digital_twin/`, `scripts/`.
- **NEW vs known**: G2/R01, G2/R03-R04, G2/R08, G7/R02, G7/R10, G7/R19-R21, G8/R32-R35, G1/R08-R09,
  harvest TEST/TWIN INVAR. NEW = other sites.

### RP32 Harmful, wear-heavy, brute-force or nondeterministic tests and tools
- **Why it recurs**: `test_tmp_scratch.py`'s 400,000 directories per run, 396 MB of writes (CLAUDE.md,
  OR37); a consumed one-shot dead-man's switch cost the Pi4's SSH (Part B.13); `br0` MAC drift orphaned
  the DHCP reservation; retries or longer timeouts offered as race fixes (OR37.a (2)); sleeps as
  synchronisation (G7/R23); public-internet reach in tests (G2/R22).
- **Instance shapes**: (a) large loops, mass file creation, big allocations or long sleeps used to prove
  an invariant (scale instead of structure); (b) `sleep`/`asyncio.sleep` waiting for a condition instead
  of polling it with a deadline or a driven clock (401 sleep calls in test scopes — classify);
  (c) repeat-until-pass loops, `@retry`, rerun flags; (d) writes a test does not need (host disk churn,
  board flash, SCD30 NVM, FRAM wipes) outside the marker gates, or a gated write that is really a
  prerequisite (CLAUDE.md "owned vs prerequisite" rule); (e) destructive host operations (`nmcli`, `ip`,
  `iptables`, `iw`, bridge/slave changes, group changes, `rm -rf` of non-scratch paths) without an
  armed recovery; (f) hostnames/URLs of public services in tests (`pool.ntp.org`, `8.8.8.8`, GitHub);
  (g) unbounded waits/retries against third parties in scripts.
- **Where**: all test scopes, `scripts/`, `toolchain/`, `tests_hardware/bench_control.py`, `ci.yml`.
- **NEW vs known**: G2/R15, G2/R22, G7/R23, G8/R26-R27, G8/R44, G1/R05-R10, G1/R28, OR37.a,
  `tests_scripts/test_persistence_write_marker_completeness.py`'s pinned set. NEW = other sites.

### RP33 Hardware-instrument validity pitfalls
- **Why it recurs**: wozi's hardcoded build flashed onto the dev bench produced two false bugs
  (CLAUDE.md); isolated-driver device scripts overwrite the production FRAM chunk (CLAUDE.md caveat);
  `reset_cause()` reads `WDT_RESET` for every reset (HR 2.2, G1/R14); raw-REPL access stops `main.py`
  (G4/R59); device scripts must live within the 8 s watchdog (G4/R60); instruments never run in the twin
  before the queue (OR29.a (4), LEAD/R01); a clean verdict hiding deselected tests.
- **Instance shapes**: (a) hardware tests asserting beyond the verified limits (throughput, timing
  without datasheet/measurement tolerance, G1/R24, G3/R34); (b) instruments that construct their own
  production objects over shared stores (FRAM allocator, config files) without isolating or restoring;
  (c) oracles reading `reset_cause()`/log lines/DebugLevel without the checks G1/R14/R19 require;
  (d) scripts that can exceed the watchdog, or that feed it where production would not; (e) board or rig
  facts hard-coded in tests rather than read from `devices/dev.toml`/living docs (G1/R40, RP10);
  (f) instruments with no twin run path; (g) assumptions about board state at start (FRAM WP, SCD30
  NVM values, DebugLevel, scratch files — LEAD/R02).
- **Where**: `tests_hardware/` (100 files), `scripts/run_*_hardware_suite.sh`,
  `scripts/_require_clean_hardware_run.sh`, `tests_hardware/README.md`.
- **NEW vs known**: G1/R01-R41, LEAD/R01-R02, harvest HW (863 items, 190 ASSUME). NEW = undeclared cases.

## G. Build chain, CI and configuration

### RP34 Quality-gate erosion over history
- **Why it recurs**: "the linter limit … was risen again and again" (OR46.a); `max-args` raised by
  agents four times against a "ratchet DOWN only" comment (DP 6 row 22); L44's "rather than scattered
  noqa" hardened then loosened in the register (V2/V12); `self-repository` audit disabled (zizmor, justified);
  `select = ["ALL"]` making unpinned upgrades fail (pins); `unit-tests-coverage` made
  `continue-on-error` then reversed (E.5.3).
- **Instance shapes** (history-based): (a) every commit that raised a ruff complexity/argument ceiling,
  added a global or per-file ignore, added `# noqa`/`# type: ignore`/`eslint-disable`/
  `# shellcheck disable`/`@ts-expect-error`, disabled an audit, relaxed a mypy flag, narrowed a lint
  scope, raised a CI timeout, or turned a job advisory — with whether the commit states a reason and who
  decided (`git log -p -G` over `pyproject.toml`, `*.ini`, `eslint.config.js`, `tsconfig*.json`,
  `.github/`, `scripts/lint.sh`, `scripts/typecheck.sh`); (b) suppressions in the tree without a reason
  or with a reason that no longer holds; (c) global exemptions where a per-file one would do (LEAD/R17);
  (d) grep guards in `lint.sh` without a test (G8/R46).
- **Where**: as (a); git history.
- **NEW vs known**: harvest SUPPRESS (~500 declared sites — the current-tree inventory is complete);
  G5/R51, G8/R46-R48, G8/R57-R59, G8/R61, LEAD/R17, L44, DP 6 row 22. NEW = the history dimension (every
  loosening with its trail) and reasonless suppressions.

### RP35 Dead entries in non-code files; persisted throwaway secrets
- **Why it recurs**: OR50 (`.gitignore:75` justified by a retired runner; `pyproject.toml:59` RUF003
  exception for definitions OR43.a retires); CI steps for gone paths; OR63 (Codecov no-op); the bench
  password persisted in a file although generated (owner, 2026-09-25: a stylistic breach needing
  harmonization, `HW.T11`, `SEC.T07`).
- **Instance shapes**: (a) `.gitignore`/`.gitattributes` patterns matching nothing any tool writes;
  (b) ruff/mypy/eslint/vitest/tsconfig excludes, per-file ignores and overrides whose files no longer
  exist or no longer trigger the rule (candidate list; trial-removal is execution work); (c) `ci.yml`
  steps, caches, artifacts and path filters for gone paths; composite-action inputs nobody passes;
  (d) dependencies (`pyproject.toml` dev group, `package.json`, `toolchain/versions.toml` apt list)
  nothing imports or calls; (e) `devices/*.toml` keys no generator reads; fixtures/golden files no test
  loads; `mockdata/` entries; (f) comments in config files justifying a setting by something gone;
  (g) generated or throwaway credentials, tokens, MACs, IPs persisted in committed files.
- **Where**: all non-code files (OR50.a (1) list) and their comments.
- **NEW vs known**: OR50 examples, G8/R62, G5/R59, DP 6 row 21, harvest CI/SCR/TOOL DRIFT and SUPPRESS.
  NEW = other dead entries.

### RP36 Host-environment assumptions and reproducibility
- **Why it recurs**: gaps masked by a pre-provisioned sandbox (CLAUDE.md build-environment section):
  `requires-python >=3.10` without `tomllib`; `sudo` and `libcap2-bin` missing from minbase; GCC 14's
  `-Warray-bounds` invisible on noble; arm64 needing the ports mirror; `uv.lock` merge bypassing pins;
  `actionlint-py` downloading at build time (HTTP 500); Node from `.nvmrc`; `ast.unparse` depending on
  host CPython (LEAD/R13); a hard-coded `/home/nico/...` path in legacy build scripts (`b6cb852`).
- **Instance shapes**: (a) commands invoked by `scripts/`/`toolchain/` not provisioned by
  `versions.toml`'s apt list, the dev group or `.nvmrc` (collect every external command name); (b) stdlib
  modules or syntax newer than `requires-python`; (c) absolute or user-specific paths, `~`, `$HOME`
  assumptions, fixed `/tmp` names; (d) environment variables read without a default or a clear error;
  (e) unpinned downloads, unverified checksums, network access during tests; (f) output depending on
  hash seed, locale, TZ, filesystem order, host Python version, timestamps (reproducibility); (g) root vs
  non-root differences (`sudo` prepending, `setcap`); (h) GNU-only flags in shell.
- **Where**: `scripts/`, `toolchain/`, `buildgen/`, `pyproject.toml`, `package.json`, `.github/`,
  `tests_scripts/`.
- **NEW vs known**: G8/R05, G8/R19-R25, G8/R28, G8/R30, G8/R52, G8/R54, LEAD/R12-R13, BACKLOG's chroot
  list, harvest TOOL/SCR. NEW = other assumptions.

## H. Legacy parity

### RP37 Lost legacy function
- **Why it recurs**: OR48 ("functional discrepancies … may be hints to something lost … treat this
  requirement as a concept"); SCD30 compare-before-write, `AmbPres force=True`, fixed field order lost
  (OR42.a/b/c); NTP `Synced` staleness and force-resync clear lost (G6/R30); `WaitTimeNTP = 0` meaning
  "never wait" (HR 3.3); the overnight notification window (OR69.a (6)); legacy boot order checked
  (OR75.a); parity is with legacy's evident **intent**, legacy bugs excluded (OR57.a).
- **Instance shapes**: for each legacy function in `python/`, `modules/sensortask-*.py`,
  `python/CommonDrivers/api_helpers.py`, `async_connect.py`, `async_manager.py`, and legacy UI in
  `html_raw/` (UI functions only): (a) a behaviour with no counterpart in `src/`/generated code/`js/`
  (a check, a retry, a readback compare, a command order, a delay, a clamp, a state reset, an exposed
  value, a UI action); (b) a counterpart that drops a case (a value meaning, an edge such as 0, midnight,
  empty); (c) a divergence explained only by an agent (no owner decision, not an adaptation without
  functional loss — OR48.a (2)); (d) legacy code comments stating an intent the refactor lacks.
  Baseline: legacy HEAD (OR48.a (4)); note the post-import edits `2bda920`, `b6cb852`, `7a27ca1`,
  `a297b0f`.
- **Where**: legacy tree (read-only) vs `src/`, `buildgen/` templates, `js/`, `devices/*.toml`.
- **NEW vs known**: G9/R02-R05, G6/R25, G6/R30, G3/R36, G3/R62, OR42.a, HR 3.3, harvest PAR (259).
  Output: owner questions in the owner's format plus register lines only — OR48.a (3) wants no
  separate permanent list; this is the consolidation-pass legacy scan (CONSOLIDATION 9, OR52.a (5)).

### RP38 Operator guesswork: state the operator needs is not exposed or not explained
- **Why it recurs**: the owner met it in use — ISL29125 overlap calibration "is pure guessing if
  lighting conditions are fitting" (OR76: a numeric suitability code in the measurements API, shown in a
  user-friendly way); result words that do not say what happened (OR69.a (4)); a failed write answered
  as success (B08, OR70.a (6)); promise rejections not surfaced (G7/R38); `reset_reason` codes that must
  be provable and readable (OR60.a); `mem_free` added to `/status` (OR71.a (7)). P1/P7: an unattended
  device is judged through its website and API alone.
- **Instance shapes**: (a) a user action (PUT, command, calibration, reset, config change) whose
  preconditions the device knows but does not report (readiness, suitability, range, "not synced yet",
  "sensor warming up"); (b) a published value whose validity, staleness, unit or saturation is not
  visible (no timestamp, no flag, raw code without text); (c) error/warning numbers reaching the page
  without a readable meaning, or `/status` fields the website does not render; (d) website controls
  that give no feedback on success, refusal or no-change; (e) an operator procedure (reflash,
  calibration, recovery) the docs describe but the device gives no signal for; (f) config keys the API
  accepts that the website cannot show or edit, or vice versa.
- **Where**: `src/` REST handlers and `@web` tags, generated route tables, `js/`, `html/`, `mockdata/`,
  SPEC Parts A.8/H/M, README's operator sections.
- **NEW vs known**: OR76, OR69.a (4), OR70.a (6), G7/R38, OR60.a, OR71.a (7), G6/R44-R45. NEW = every
  other site; each is an owner-matter when it adds an API field or a page element (OR52.a (2) freezes
  keys before the release).

---

## 1 Sweep partition (13 agents; the lead split S1, S6 and S10 of the draft)

| Sweep | Patterns | Main scopes | Notes |
|---|---|---|---|
| S1 Provenance and merges | RP01, RP03 | all text + commit messages, merges | |
| S2 Rule drift over history | RP02 | full doc/comment history | this is the OR13.a/OR14.a history trace of CONSOLIDATION 9; not re-run in pass 3 |
| S3 Doc state | RP04, RP05, RP06 | living `.md`, code comments, config comments | text-similarity and link resolution tooling |
| S4 Grounding | RP07, RP08, RP09 | `src/`, `digital_twin/`, `tests/` fakes, SPEC F/I/C/M, datasheets, MicroPython checkout | |
| S5 One source and wiring | RP10, RP11, RP12, RP27 | whole repo; `src/`↔`js/`↔`buildgen/`↔`devices/`↔SPEC | RP10 per-site inventory is large |
| S6 Failure handling and evidence | RP13, RP14, RP15, RP16, RP17 | `src/`, generated-code templates, JS, test asserts on errno | traces callers of every `err_s`/`wrn_s` |
| S7 Time and memory | RP18, RP19, RP20 | `src/`, generated code, device scripts, `js/` | |
| S8 Concurrency, wear, input | RP21, RP22, RP23 | `src/`, generated code, `js/` | |
| S9 Code material | RP24, RP25, RP26 | all code scopes, AST clone and reference search | |
| S10 Test bodies and hygiene | RP28, RP30, RP31 | `tests/`, `tests_scripts/`, `tests_js/`, twin scenarios | |
| S11 Gates, harm and hardware | RP29, RP32, RP33 | `scripts/`, `ci.yml`, `tests_hardware/`, conftests | |
| S12 Build chain and operator view | RP34, RP35, RP36, RP38 | config files, `toolchain/`, `scripts/`, git history; REST/website | |
| S13 Legacy parity | RP37 | legacy tree vs `src/`, generated code, `js/` | this is the OR48 legacy scan of CONSOLIDATION 9; not re-run in pass 3 |

Overlaps are intentional at the edges; the lead dedups on `file:line`. Shared signatures (e.g. `except`
bodies for RP14/RP20, sleeps for RP19/RP32, ports for RP12/RP31) are recorded under the pattern whose
defect they show; a sweeper that meets another pattern's instance records it with that RP ID.

## 2 Knowledge sources a sweeper reads first

1. `CLAUDE.md` (hard rules and every "Known … cause, fixed" bullet).
2. `PROJECT_AUDIT_PLAN.md` 3.2: the OR rows its patterns cite, in full (later rows overtake earlier).
3. `audit/CONSOLIDATION.md` sections 1, 3 (harmonizations 1-45) and 5.
4. `audit/pass2/INDEX.md` plus the register files named in its patterns' "known holders"
   (`audit/pass2/G*.md`, `LEAD.md`), and `audit/pass2/verify/RULINGS.md`.
5. S1/S2 also: `audit/DECISION_PROVENANCE.md` sections 1-2, 6 and `audit/pass2/verify/L25.md`.
6. For dedup only: `audit/HARVEST.md` (how to read items) and the `audit/harvest/<AREA>.md` catalogs of
   the scanned areas.

## 3 Patterns considered and rejected

| Candidate | Why not a sweep pattern |
|---|---|
| Parallel-agent interference, verbose owner questions, convergence | Audit-process rules (OR7, OR51), not repo content; they govern how sweepers work (0.3-0.4) |
| Arduino C-side conformance | Out of scope, post-audit only (OR5.a (3)) |
| Network attackers, authentication, `bootloader` exposure | Trusted home LAN threat model (OR52.a (3)); only input robustness stays (RP23) |
| Boot latency | Not a metric (CLAUDE.md, G4/R58); only watchdog feed gaps matter (inside RP17 (f)) |
| Per-task heartbeats | Rejected by the owner (OR31.a (4)) |
| I2C/SPI/`getaddrinfo` timeout wrapping | Settled watchdog backstop (F.2, CLAUDE.md); only "one mechanism for wrappable calls" stays, inside RP19 |
| Log protection across reboots, alternating codes, layered limits | Owner: overkill (OR35.a (3)) |
| Firmware write-rate limiting; admission fairness | Owner chose no (OR42.a (3); OR72.a (1), OR83) |
| Legacy-tree code quality | Reference-only forever (CLAUDE.md); legacy is read only as RP37's oracle |
| Vendored Microdot edits | Never edited; its identity is one mechanical check (G6/R53), not a recurring pattern |
| Datasheet licensing, Codecov, Pico-W-only | Single decided actions (OR80, OR63, OR73), no hunt needed |
| Heap-layout research | Closed (G4/R53) |
| Comment-cap overflow | Machine-gated at zero for Python/shell; JS/CSS/config measured zero 2026-09-24; B4 re-measures |
| Separate "complexity" pattern | Covered by ruff ceilings and OR46.a (3); history side in RP34, shape side in RP24 |
| Separate "naming variance" pattern | Merged into RP24 (both are OR24 "one material") |
| Separate "fake fidelity" and "target semantics" patterns | Merged into RP09 (one question: does the host environment tell the truth about the target) |
| Separate "workarounds" pattern | Merged into RP26 (a workaround past its trigger is a leftover); declared ones were harvested |
| Separate "void fleet/compat premise" pattern | Merged into RP06 (a stale current-state claim) |
| Separate "tier containment" pattern | Planned as OR45.a's matrix in B3; its seeds sit in RP30 and RP33 |
| Separate "parked questions" pattern | Only 7 hits (M2); a sub-shape of RP01 (d) |
