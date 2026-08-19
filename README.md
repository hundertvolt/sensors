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

## Digital twin (hardware simulator)

`digital_twin/` is a fake `machine`/`network`/`neopixel` implementation (Step 3 of
`FINAL_WIRING_PLAN.md`'s five-step effort) that mirrors the real `wozi` bus wiring — real-time-firing
`Timer`s, randomized-but-plausible sensor values, and a scripted `WLAN` connect sequence — so driver
code can run under the real MicroPython Unix-port interpreter with no physical hardware attached.

Start its standalone CLI demo directly with the same Unix-port binary `scripts/test.sh` builds:

```sh
$HOME/pico-toolchain/micropython/ports/unix/build-standard/micropython digital_twin/launch.py \
    --seed 42 --duration 3 --no-wdt-feed --wifi-outcome success --fault scd30:writeto:1
```

(use `$PICO_TOOLCHAIN_DIR` instead of `$HOME/pico-toolchain` if you've overridden it — see
`scripts/test.sh`'s own `toolchain_dir` resolution for the exact path; run
`uv run toolchain/setup_toolchain.py` first if the binary doesn't exist yet). All flags are optional
and repeatable where noted:

- `--seed N` — seed every chip's random value walk for a reproducible run.
- `--duration SECONDS` — exit after a fixed run instead of looping forever (Ctrl-C also works).
- `--no-wdt-feed` — stop feeding the watchdog, to watch it actually trip.
- `--fault DEVICE:OP[:TIMES]` (repeatable) — script a one-shot/N-shot bus fault, e.g.
  `--fault scd30:writeto:2`. See `digital_twin/launch.py`'s own `_FAULT_DEVICE_OPS` for every valid
  `DEVICE:OP` pair.
- `--wifi-outcome OUTCOME` (repeatable) — queue a `WLAN.connect()` outcome:
  `success`/`no_ap`/`wrong_password`/`connect_fail`.
- `--fram-state-path PATH` — persist the FRAM twin's contents to a JSON file across runs, instead of
  in-memory only.

This standalone launcher is twin-only (no `src/` import). To instead run the real
`src/sensortask_wozi.py` prototype against the twin, see `digital_twin/README.md`'s own
"Swapping the twin in for a Unix-port run" section — that's a separate `MICROPYPATH`-based
invocation, not this launcher.

Full reference — what's simulated and how, FRAM persistence, running the twin's own unit tests, and
adding a new chip fake when a new sensor driver lands: **`digital_twin/README.md`**.

### Manual baseline verification walkthrough

A copy-paste sequence for manually checking the real assembled system (`src/sensortask_wozi.py`,
unchanged) against the digital twin, end to end, over real HTTP — the same walkthrough used to
establish this project's own known-working baseline (build → boot → set log level → reboot with
that level persisted → boot again with bus faults injected). Run each block from the repo root;
`curl` and a browser both work against `http://127.0.0.1:8080` while a run is up.

**1. Fresh build and boot** (also runs a built-in 20-cycle soak across every endpoint before it
starts serving — watch for a `PASS` line):

```sh
rm -rf digital_twin/config digital_twin/fram_state.json   # start from a clean, unconfigured device
scripts/run_unix_port_integration.sh --host 127.0.0.1 --port 8080
```

Leave this running in its own terminal. In a second terminal, walk every GET endpoint plus the
stub website:

```sh
curl -s http://127.0.0.1:8080/measurements | python3 -m json.tool
curl -s http://127.0.0.1:8080/sensors | python3 -m json.tool
curl -s http://127.0.0.1:8080/networking | python3 -m json.tool
curl -s http://127.0.0.1:8080/system | python3 -m json.tool
curl -s http://127.0.0.1:8080/notification | python3 -m json.tool
curl -s http://127.0.0.1:8080/status | python3 -m json.tool
open http://127.0.0.1:8080/   # or just curl -s http://127.0.0.1:8080/ - the stub site's index
```

**2. Set the log level to `all` (5) via the real API, then reboot to see a full startup log.**
`DebugLevel` is a persisted `/system` setting (0-5, see `print_log.py`'s `PrintLog.level_*()`
methods) — like every config write, it's saved to disk immediately, but only takes effect for
*future* logger construction, so its own verbose logging only shows up starting with the next
boot:

```sh
curl -s -X PUT -H "Content-Type: application/json" -d '{"DebugLevel": 5}' http://127.0.0.1:8080/system
curl -s http://127.0.0.1:8080/system   # confirm it reads back as 5
```

Now stop the running twin with **Ctrl-C in its own terminal** (a real `SIGINT` — this is what
`run_wozi_integration.py`'s own `except KeyboardInterrupt:` catches, letting its `finally` block
flush the FRAM twin's state to disk before exiting; a hard `kill`/`pkill` skips that cleanup, same
as it would skip any unsaved state on real hardware). Then boot again the same way as step 1, but
**without** wiping `digital_twin/config/` this time (that's the whole point — the persisted
`DebugLevel` survives):

```sh
scripts/run_unix_port_integration.sh --host 127.0.0.1 --port 8080
```

This boot's own console output is now the full verbose trace — every `PrintLog.evt()`/`.one()`/
`.all()` call, not just warnings/errors, across every module (FRAM chunk allocation, WiFi hotspot
fallback, NTP sync attempts, task/timer startup sequencing, ...).

**3. Exercise every PUT endpoint and check persistence.** Ctrl-C first if the level-5 instance from
step 2 is still up (same log-verbosity note applies to whatever ships next), then repeat step 1's
boot, and try:

```sh
curl -s -X PUT -H "Content-Type: application/json" \
  -d '{"SSID": "MyNetwork", "PW": "hunter2", "Country": "DE", "Hostname": "wozi-test"}' \
  http://127.0.0.1:8080/networking
curl -s -X PUT -H "Content-Type: application/json" -d '{"GMTOffset": 3600, "DSTOffset": 3600}' \
  http://127.0.0.1:8080/system
curl -s -X PUT -H "Content-Type: application/json" \
  -d '{"WarnCO2": 1500, "WarnVOC": 300, "WarnHum": 60.0}' http://127.0.0.1:8080/notification
curl -s -X PUT -H "Content-Type: application/json" \
  -d '{"SCD30": {"MeasInt": 4}, "SGP40": {"BackupPeriod": 2}, "BMP3XX": {"SampleInterv": 3}}' \
  http://127.0.0.1:8080/sensors
```

Every field type is checked strictly against its schema — a JSON integer where a `"float"` field is
declared (e.g. `60` instead of `60.0`) is correctly rejected as `"Invalid"`, not a bug; send a real
decimal point for float-typed fields (`WarnHum`/`TempOffs`/`Interv`/`FlashDur`, ...). Read each
endpoint back (`curl -s http://127.0.0.1:8080/<endpoint>`) to confirm the write took, then Ctrl-C
and boot once more without wiping `digital_twin/config/` to confirm it survived the restart. One
known, accepted exception: SCD30's own fields (`MeasInt`, `TempOffs`, ...) don't survive a twin
restart — real hardware's SCD30 chip has its own onboard NVM that a real MCU-only reboot doesn't
touch, but the twin doesn't currently model that (see `BACKLOG.md`).

**4. Repeat with bus fault injection, and confirm recovery.** `--fault DEVICE:OP[:TIMES]` (see the
"Digital twin" section above for the full flag reference) queues a bounded, self-clearing failure
on a specific bus operation - the affected sensor's reader task should fail, log it, and recover on
its own once the fault count is exhausted:

```sh
rm -rf digital_twin/config digital_twin/fram_state.json
scripts/run_unix_port_integration.sh --host 127.0.0.1 --port 8080 \
    --fault scd30:writeto:2 --fault sgp40:readfrom_into:2 --fault bmp3xx:readfrom_mem:2 --fault fram:write:2
```

Watch `/status`'s `errcount` section for each affected module's counter to tick up, then confirm
`/measurements` still returns plausible readings from every sensor once the run has been up for a
few seconds — that's the fault having fired, been logged, and recovered from. A device-wide
task-failure streak beyond `system_service.py`'s own threshold triggers a real reboot request too
(logged as `SYSTEM ... reboot triggered!` at `DebugLevel >= 4`) - on real hardware this actually
restarts the unit; the twin can't do that (`machine.reset()` raises `SimulatedReset` instead, which
is expected and harmless - see that exception's own docstring), so the same process keeps serving
afterward instead of restarting, which is fine for continuing this walkthrough.

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

**Temporary planning doc** (kept live — not a periodic-cleanup artifact):

- **WIRING_CONTRACT.md** — the standing reference for `src/sensortask_wozi.py`'s construction
  sequence (Step 1 of `FINAL_WIRING_PLAN.md`'s five-step effort landed and merged): real FRAM-chunk
  construction order, the constructor-injection dependency graph between modules, already-found
  mechanical gaps, and forward REST-API notes. Its own facts have no other permanent home, so it
  stays up to date as `src/sensortask_wozi.py` changes, not just at some periodic pass's own close —
  deliberately kept alive past Step 1 landing (deviating from its own original "deleted once Stage 1
  lands" framing) since Steps 2-5 and Step 6 (`BACKLOG.md`'s open question #6, its own
  dedicated session/branch alongside the original five) all build on the exact construction
  order/dependency graph it documents; deleted only once the whole effort — five steps, Step 6, and
  the large post-merge audit — merges back and supersedes it.
- **FINAL_WIRING_PLAN.md** — the global list for Stage 1's actual rewrite: the five-branch/session
  plan that builds `src/sensortask_wozi.py` (construction restructure, generic webserver/API
  service, digital-twin simulator, website placeholder scaffold, full Unix-port integration), plus
  Step 6 (the self-healing-system failure-mode audit, added after the original five-step plan was
  scoped), each step's goals/doc-links/criteria, and the cross-step interface contracts that make
  them combine into one working prototype. Deleted once all five steps, Step 6, and the closing
  large post-merge audit have merged back — same lifecycle as `AUDIT_PLAN.md`'s below.
- **`digital_twin/README.md`** — the standing reference for Step 3's hardware simulator: what's
  there, how to swap it in for a Unix-port run, FRAM persistence, running its own tests, and how to
  add a new chip fake when a new sensor driver lands (required per `SPECIFICATION.md` C.11).
  Its own lifecycle isn't yet settled the way `WIRING_CONTRACT.md`'s is above (still genuinely
  useful to Step 5 and likely beyond, but a later session may decide to fold it into
  `SPECIFICATION.md` the way `src/README.md`/`tests/README.md` were) — listed here for now so it
  isn't only locatable by cross-reference in the meantime.

`AUDIT_PLAN.md`, the master action list for the now-completed full `src/` audit, was deleted once
the audit closed — everything permanent it settled was migrated into `SPECIFICATION.md` (the
style-guideline harmonization it drove lives in Parts C/D) first.
