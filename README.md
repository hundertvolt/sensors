# Sensor Framework

A generic asyncio-based sensor framework for **Raspberry Pi Pico W (1st gen, RP2040)** boards
running **MicroPython**, currently applied to room air-quality monitoring. Each physical unit
reads sensors over I2C/SPI, exposes a REST API plus a small web UI, persists frequently-changing
data to an external FRAM chip, and persists configuration to a JSON file on the onboard flash
filesystem. Code ships as frozen bytecode compiled into the MicroPython firmware, not loaded from
the device filesystem at runtime.

**5 units are currently deployed**: `arzi`, `wozi`, and three physically-identical-to-arzi units
sharing the `neu` build (same sensors, different GPIO wiring). `dev` is a bench/test rig only.

| Config | Sensors | FRAM | Watchdog | HTML source |
|---|---|---|---|---|
| arzi | SCD30 (CO2/temp/hum), SGP40 (VOC) | yes | active (8000ms) | `html_raw/arzi` |
| neu ×3 | same as arzi, different pin assignments | yes | active | `html_raw/arzi` (reused) |
| wozi | SCD30, SGP40, BMP388 (pressure/temp) | yes | active | `html_raw/wozi` |
| dev | SCD30, SGP40, SHTC3, MPRLS, ISL29125 | no | disabled | `html_raw/dev` (bench rig) |

## Repository layout, architecture, refactor status, and the build process

**Moved to [`SPECIFICATION.md`](SPECIFICATION.md)**, the project's central specification document
— Part A (repository layout, architecture at a glance, refactor status) and Part B (toolchain
internals + building this project's firmware). This section used to hold all of that content
directly; it's now a pointer, as part of a first-pass doc-scatter cleanup that consolidated
`DRIVER_SPEC.md`, `src/README.md`, `tests/README.md`, `toolchain/README.md`, and these sections
into one place. See "Further reading" below for the complete doc map.

Everyday build commands, unchanged:

```sh
uv run toolchain/setup_toolchain.py              # first-time setup / everyday re-run (see SPECIFICATION.md Part B)
uv run toolchain/setup_toolchain.py --latest      # detect + pin + install newest stable MicroPython
uv run toolchain/setup_toolchain.py test          # offline re-verify an existing install (~30s)
```

## Code quality tooling

Ruff and mypy checks, scoped to `improved-quality/`, `src/`, and `tests/` (the pre-refactor
codebase — `python/`, `modules/` — isn't covered yet), plus unit tests for `src/`, can be run
manually. Needs Python 3.11+ (`tomllib`, stdlib only since 3.11 — `uv sync` enforces this
automatically via `pyproject.toml`'s `requires-python`, so this only matters if `uv` has to fall
back to whatever `python3` it finds):

```sh
uv sync                    # one-time, and after pulling changes - installs ruff/mypy/pytest into .venv
source .venv/bin/activate  # scripts/lint.sh and scripts/typecheck.sh assume ruff/mypy are already on PATH

scripts/lint.sh            # ruff check
scripts/typecheck.sh       # mypy, using MicroPython stubs matching toolchain/versions.toml (see above)
scripts/test.sh            # runs every test in tests/, under a real MicroPython Unix-port interpreter -
                            # builds that interpreter automatically on first run (see tests/README.md)
scripts/test.sh --coverage # same, plus a src/-only line coverage report (HTML/XML/markdown) - see below
```

All three (`lint.sh`/`typecheck.sh`/`test.sh`) run in GitHub Actions CI
(`.github/workflows/ci.yml`) on every push/PR, plus `test.sh --coverage` as a non-gating extra
step. Config lives in the root `pyproject.toml`; see CLAUDE.md's "Code quality tooling" section
for the full rationale (why `ruff format` isn't used, why the MicroPython stubs install into a
separate `typings/` directory instead of the main dev venv, why tests don't run under
pytest/CPython, etc.).

### Test coverage

```sh
scripts/test.sh --coverage
```

Reports `src/`-only line coverage; non-gating, never fails the build. Full pipeline, output paths,
and CI behavior (Job Summary, build artifact, Codecov status): **moved to
[`SPECIFICATION.md`](SPECIFICATION.md) Part E.5, "Coverage"**.

## Further reading

Every supporting doc in the repo, in one place — added to as a first pass at pulling scattered
specs/guidelines into a single map rather than leaving them locatable only by cross-reference.
When a new doc is added, add it here too instead of letting the map go stale again.

**Standing operating docs** (permanent, kept current):

- **CLAUDE.md** — AI-session operating constraints: hard rules, working agreements, PR workflow,
  pre-push verification. Start here for how AI sessions should operate in this repo. Its former
  Platform-target/Architecture-reference/Microdot content now lives solely in `SPECIFICATION.md`
  (Parts F/A.4/A.5) — CLAUDE.md carries short pointers to those spots instead of restating them,
  so read `SPECIFICATION.md` directly for that material (see its front matter for the tradeoff
  this creates: that content is no longer auto-loaded into every session for free).
- **BACKLOG.md** — active open questions, not-yet-done refactor targets, and deferred/out-of-scope
  work; see its own opening paragraph for the full scope. Resolved items move into this file or
  CLAUDE.md instead of staying there — it's working memory, not a changelog.

**The central specification** (permanent, code-facing):

- **[`SPECIFICATION.md`](SPECIFICATION.md)** — the single central specification document:
  repository/architecture overview, the toolchain/build-environment installer, the sensor driver
  architecture spec, the `src/` production-quality checklist, testing & coverage, and
  MicroPython/RP2040 platform-target facts — all in one place, organized into lettered Parts
  (A-F) for different needs. Produced by a first-pass doc-scatter cleanup that merged
  `DRIVER_SPEC.md`, `src/README.md`, `tests/README.md`, `toolchain/README.md`, most of this
  file's former "Repository layout"/"Architecture at a glance"/"Refactor in progress"/"Build
  process" content, and the spec-shaped parts of `CLAUDE.md`/`BACKLOG.md` into one document. Start
  here for "how does this codebase actually work" or "what shape should a new driver's code take."
- **DRIVER_SPEC.md**, **`src/README.md`**, **`tests/README.md`**, **`toolchain/README.md`** — now
  short stub files pointing into `SPECIFICATION.md`'s Parts C, D, E, and B respectively, kept so
  existing links/references throughout the repo still resolve to a real file. Read
  `SPECIFICATION.md` directly rather than these.

**Temporary planning docs** (deleted once their purpose is served — not meant to accumulate):

- **AUDIT_PLAN.md** — the master action list for the planned full `src/` audit (see BACKLOG.md's
  "Planned: full `src/` audit"): Definition of Done, per-cluster goals/quality measures, and the
  standing conventions settled during pre-audit planning. Deleted once the audit is agreed done;
  anything permanent it settles migrates into CLAUDE.md/README.md/`SPECIFICATION.md` first.
  **Its own Cluster 10 goal is a style-guideline *harmonization* pass — applying the audit's real
  per-file findings to actually resolve cross-file inconsistencies — not creating a new merged
  file.** `SPECIFICATION.md` (above) already did the *location* consolidation (moving scattered
  content into one place, unaudited); Cluster 10's job once it runs is to edit `SPECIFICATION.md`'s
  Parts C/D in place against real audit findings, not to produce a second, separate document.
- **WIRING_CONTRACT.md** — seed document for the eventual real rewrite of
  `improved-quality/sensortask-wozi.py`'s construction sequence (the audit's "Stage 1," out of the
  audit's own scope): real FRAM-chunk construction order, the constructor-injection dependency
  graph between modules, and mechanical gaps already found. Deleted once that rewrite lands.

**Known gap**: BACKLOG.md's "Refactor targets not yet done" section references a "Recipe list" as
existing style-bearing source material to fold into the eventual consolidated guideline alongside
`DRIVER_SPEC.md` — no file by that name (or close to it) exists anywhere in the repo's history.
Flagged, not resolved; needs the project owner to say what it's meant to point to.
