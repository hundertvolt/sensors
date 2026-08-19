# CLAUDE.md

Operating constraints and architecture reference for AI sessions working in this repo. See
README.md for human-facing orientation, and README.md's "Further reading" section for the
complete map of every other supporting doc in the repo (BACKLOG.md's open-questions/deferred-work
list included) — that section is the single place the list is kept, not duplicated here.

## Datasheets

Full detail (folder contents, the "read the PDF first" rule, what to do when one's missing): see
SPECIFICATION.md Part A.6. Short version: `datasheets/` holds real datasheet PDFs for the chips
this codebase drives — read them first for any hardware-interaction claim, and say so explicitly
if one you need isn't there rather than falling back to web search/training memory.

## Platform target

**The concrete facts** — MicroPython 1.26/RP2040 specifics, the WDT 8388ms cap, RP2040 hardware
specs, the soft-Timer-callback-drop gotcha, the `[x] * n` segfault range, `Timer.init()`'s
`OSError(ENOMEM)` case, the `MemoryError`-isn't-an-`OSError`-subclass rule, `struct.pack()`'s
silent truncation — **live in `SPECIFICATION.md`'s Part F (Platform Target & MicroPython Runtime
Facts).** Read Part F before any platform-facing code work; don't rely on memory of it, and don't
re-derive these from training memory or general Python knowledge — they were confirmed against
real MicroPython source, not assumed.

Two standing AI-session practices (not facts, kept here since they're instructions, not
information):

- **Always check current MicroPython and Microdot documentation before asserting how an API
  behaves** — do not rely on training-data memory for either. This has already caught real
  discrepancies once; treat it as a standing requirement for every session, not a one-time step.
- **Whenever the pinned MicroPython version changes (and periodically otherwise), re-check every
  MicroPython-facing code construct against the current pinned version's own source, the current
  rp2 port documentation, and MicroPython developer-forum/issue-tracker findings** — not just "is
  this still correct," but specifically "is there now a newer/better/more-complete way to do this
  that a stale construct is missing out on." Examples of the kind of thing this is meant to catch:
  a newly widened set of types accepted by `micropython.const()`, or real `asyncio`-level
  timeout/cancellation support being added to something that previously had none (e.g.
  `socket.getaddrinfo()` — see SPECIFICATION.md Part F.2 for its current
  can't-be-timeout-wrapped status, which is exactly the kind of fact a version bump could change
  and silently invalidate). This is a standing practice, not a one-time pass — repeat it every time
  `toolchain/versions.toml`'s MicroPython `ref` moves.

## Hard rules

- **Don't edit `improved-quality/`'s *source* files (drivers, managers, etc.) — they're the WIP
  refactor target, out of scope for routine editing.** This does **not** cover its dev-tooling
  config: `mypy.ini`/`pycheck.sh` were an ad hoc, trial-and-error setup the project owner
  explicitly asked to have questioned and replaced (confirmed directly, not inferred) — they've
  been retired in favor of root-level `pyproject.toml` + `scripts/lint.sh`/`scripts/typecheck.sh`
  (see "Code quality tooling" below). Source files elsewhere in `improved-quality/` remain
  read-only context until the refactor itself starts. **The project owner can authorize a scoped
  exception for a severity-justified fix** (precedent: the `ConfigManager`/`LockedValue`
  wrong-module-import bug that would have crash-looped every deployed unit's boot) — this is a
  standing, repeatable exception path, not a one-off; it still requires the owner's explicit
  authorization each time, scoped narrowly to the specific fix, not a general license to edit
  `improved-quality/` more broadly.
- **`src/` is where files land once they're fully reviewed and tested** — formula/logic
  correctness checked, input validation and exception-safety audited, unit tests written and
  passing (see "Code quality tooling" below and SPECIFICATION.md Part E), unlike `improved-quality/`'s
  WIP files above. **SPECIFICATION.md Part D is the full checklist** for what "fully reviewed and tested"
  actually requires — apply it to every file that makes this move, not just whichever ones already
  have. **For a new sensor driver specifically, SPECIFICATION.md Part C is the shared
  architecture/interface spec** extracted from the three drivers already in `src/` — what shape
  the code should take (layering, naming, error handling, config schema, ...), separate from
  Part D's "is it good enough to move" checklist. Files in `src/` aren't automatically
  re-wired into any driver's actual import path for a
  real firmware build just by moving there — `improved-quality/` files keep importing them by
  their old unqualified name unchanged (e.g. `import math_helpers`, `from crc_checks import ...`),
  which still resolves correctly both because MicroPython's frozen-module namespace is flat (it
  doesn't matter which directory the source lives in once it's actually frozen into firmware) and,
  for local dev-tooling checks today, because `pyproject.toml`'s `mypy_path` includes `src`. Treat
  `src/` files as normal, freely-editable code, not as read-only WIP context the way
  `improved-quality/` is.
- **Whenever a new file is promoted into `src/`, run a bird's-eye-view scan over the whole
  content of `src/`** — not just the new file in isolation — to check that the coding guidelines
  and `src/README.md`'s checklist (including its "API consistency, within a file and across the
  project" and "Check against current MicroPython" items) actually hold consistently across every
  file there, not just that the new file individually passes review on its own. **If the scan
  surfaces a discrepancy — one file diverging from another, or from a guideline — do not silently
  fix it.** Report it and discuss how to resolve it before changing anything, the same "flag, don't
  silently change" treatment section 1 of `src/README.md` already gives formula/behavior
  discrepancies, applied here to cross-file consistency instead.
- **Do not "fix" `modules/_boot.py`'s `import sensortask.py`** (literal `.py` in the import
  statement) without testing on real hardware first. It works reliably today; MicroPython's
  documented freeze/import behavior says the module should be named `sensortask` with the
  extension stripped, so this *looks* like it should raise `ModuleNotFoundError` — the mechanism
  is genuinely unresolved (see BACKLOG.md #1). Changing it blind risks breaking every deployed
  unit's autostart.
- **`python/CommonDrivers/microdot.py` is vendored third-party code** — verified to match current
  upstream Microdot exactly (`send_file()` signature, `Request.json` behavior). Don't restyle or
  "clean up" it; if you need to change its behavior, treat that as a deliberate fork decision, not
  routine editing. **`ext/microdot.py` is the same policy applied to the refactor target**: a plain,
  unmodified vendored copy of upstream Microdot (pinned to tag `v2.6.2`), replacing the
  `improved-quality/microdot.py` copy that had drifted into an unintentional fork (removed). No
  edits, no restyling, ever — any behavior change needed is handled by wrapping/calling it from our
  own code (see "Microdot / REST layer" below), never by touching this file. `src/` and `ext/` are
  copied flat into one directory and frozen together for the refactored firmware build, which is why
  they live at the same directory depth in the repo.
- **`dev` config is a bench rig only** — its quirks (e.g. LED/Neopixel REST routes referencing an
  object that's never instantiated) are explicitly out of scope. Don't fix them as if they were
  bugs.
- **No unit tests against the current (deployed, pre-refactor) codebase — `python/`, `modules/`.**
  The agreed plan is: fully understand the current system first, confirm what's already
  transferred into `improved-quality/`, and write tests as part of that refactor — not before, and
  not against the current code. This does **not** contradict `tests/README.md`'s testing
  requirements (tests under a real MicroPython Unix-port interpreter, `uv`-managed venv, mocking
  boundary, etc.) — those describe what the *refactored* code must eventually have. **First
  concrete instance**: `src/math_helpers.py` has a full `tests/test_math_helpers.py` suite,
  running under a real MicroPython Unix-port interpreter per that plan (see "Code quality tooling"
  below) — this rule is about not testing the old `python/`/`modules/` code, not about deferring
  all tests indefinitely.
- **Don't touch `sensors/config.json`-equivalent files or commit any real credentials.** A
  `.gitignore` covers per-device config/build artifacts, but still be deliberate about what you
  stage. **The one known real credential already in this repo**: a hardcoded hotspot fallback
  password, present in both `python/CommonDrivers/async_connect.py` (deployed, pre-refactor) and
  `src/asy_wifi_service.py` (promoted) — accepted risk (only exploitable by someone in physical
  WiFi range of a unit that's already lost its real WiFi), not something to "fix" by
  rotating/removing without the project owner's direction. `improved-quality/async_connect.py`
  itself was removed once its functionality was fully promoted to `src/asy_wifi_service.py`/
  `asy_ntp_client.py`/`asy_dns_client.py` — no import in the repo referenced it anymore.
- **For a genuinely wedged I2C bus/sensor, the hardware watchdog is the accepted backstop, not a
  software fix to chase** — settled, don't re-propose an I2C-level timeout mechanism; full
  reasoning (including why `socket.getaddrinfo()` belongs in this same bucket, and which calls
  genuinely *can* be timeout-wrapped) is in SPECIFICATION.md Part F.2.
- **Don't wrap every `asyncio` primitive call in `try`/`except` against a theoretical internal
  `MemoryError` as a blanket policy** — see SPECIFICATION.md Part F.2 for the full rule and its
  narrow exception.
- **Adafruit-derived driver code is fair game to restructure/rewrite** (keeping attribution) —
  unlike `python/CommonDrivers/microdot.py`/`ext/microdot.py`, which stay hands-off/vendored (see
  above). Full note: SPECIFICATION.md Part F.4.
- **Long-blocking operations must not stall timing-sensitive work** — standing design principle
  for all new code; full reasoning (including the retired `get_long_block_lock()` mechanism) is in
  SPECIFICATION.md Part F.3.

## Working agreements

- Long-term goal: fully understand the current (production) system in detail, then check what's
  already been addressed/transferred well into `improved-quality/`. The refactor should end up
  with the *same top-level features*, just more consistent/stable — not a feature change.
- When a fact in this file or BACKLOG.md turns out to be stale (version drift, changed upstream
  API, etc.), update the doc in the same session rather than silently working around the
  discrepancy.
- **Documentation contains current state, future targets, and rules/agreements — not the historic
  path that got there.** BACKLOG.md is active working memory (open questions, deferred work,
  in-flux decisions), not an append-only log of bugs found and fixed in already-shipped, tested
  code; once an item is resolved, it comes out, migrated to CLAUDE.md/README.md if it's a
  permanent fact worth keeping, or simply dropped if it was process narrative with no forward
  value. This already had to be corrected once (a merge re-accumulated ~800 lines of per-file
  "bug found, fixed" narrative in BACKLOG.md) — treat pruning history back out as routine
  maintenance whenever an item resolves, not a one-off cleanup.
- Prefer flagging genuinely ambiguous/architecturally significant decisions to the project owner
  over guessing — several open questions in BACKLOG.md exist precisely because the code's actual
  intent wasn't obvious from reading it alone.
- When changing a sensor driver's behavior, verify against the legacy driver's own actually-proven
  field behavior, not just judged correct against internal code-review logic in isolation.
- **Step-session workflow, standing practice for any substantial unit of refactor/audit work**
  (originated during the `improved-quality/` → `src/` wiring effort's five-plus-one step sessions,
  still the expected shape for a comparable future unit of work — a new driver promotion, a new
  audit pass, etc.): (1) refine the task's own scope into a detailed list — goals, doc links, and
  the criteria that make the branch/session done — doing real research first (datasheets, current
  MicroPython/Microdot docs, legacy driver code) rather than restating a one-line ask; (2) ask up to
  10 top-level clarifying questions (what needs deciding, the realistic options, the consequences of
  each), resolving as much as possible from project context/internal docs/legacy code first, but
  raising a genuinely blocking or architecturally significant decision at any point, not only in
  this round; (3) write the full set of unit tests first (TDD) against the criteria the refined
  scope settled on; (4) write the implementation against those tests, refining until every test
  passes and the result is lean, not just "technically satisfies the tests"; (5) add unit tests for
  the resulting functional code, maximizing coverage; (6) stop and report back to the project owner
  before doing anything more — merging, starting the next unit of work, or any scope beyond what was
  just built is not the session's own call. A session can come back with a blocking question at any
  point in this sequence, not only at the end.

## Code quality tooling

- **Config lives in root `pyproject.toml`** (ruff/mypy/pytest/uv, dev-tooling only — the shipped
  code stays frozen-bytecode-only, not restructured into an installable package). Run manually via
  `scripts/lint.sh` (ruff), `scripts/typecheck.sh` (mypy), and `scripts/test.sh` (unit tests, under
  a real MicroPython Unix-port interpreter — see below and `tests/README.md`); `lint.sh`/
  `typecheck.sh` assume `ruff`/`mypy` are already on `PATH` (e.g. an activated `uv sync`-created
  venv). **Wired into CI** via `.github/workflows/ci.yml` (GitHub Actions), running all three on
  every push/PR. The CI pipeline does not yet include a real firmware-build stage (see
  BACKLOG.md).
- **Scope is `improved-quality/`, `src/`, `tests/`, and `digital_twin/`.** The pre-refactor deployed
  codebase (`python/`, `modules/`) has no lint/type config yet; extending scope there is a separate
  future decision, not assumed by this setup. Unlike `improved-quality/`'s tracked, allowed-to-be-
  nonzero debt, `digital_twin/` is expected to stay fully clean, same as `src/`/`tests/` — it's a
  fully-reviewed, freely-editable scope (see "Hard rules" above), not WIP. `digital_twin/`'s own
  type-check is a **separate** mypy invocation (`digital_twin/typecheck.ini`, run unconditionally by
  `scripts/typecheck.sh` regardless of its own args) rather than folded into the main
  `[tool.mypy]` pass — mypy resolves each bare `machine`/`network`/`neopixel` module name to exactly
  one file per run, so this package's own hardware fakes and the real `typings/` board stubs can
  never both be checked correctly in one invocation. `digital_twin/machine.py`/`network.py`/
  `neopixel.py` (a straight `Duplicate module named "machine"` collision with `tests/machine.py`
  otherwise — confirmed directly, not the softer resolution-priority hijack `tests/network.py`'s own
  exclude guards against) and `digital_twin/launch.py`/every `tests/test_digital_twin_*.py` (attr-
  defined noise on every twin-only API the real board stub doesn't declare, e.g.
  `WDT.would_have_triggered_count`, `WLAN.script_connect_outcomes()` — confirmed directly, including
  one real `mypy src tests`-only finding this design caught that a from-scratch `mypy` run missed)
  are therefore excluded from the main `[tool.mypy]` pass and checked correctly by the dedicated
  pass instead — see `pyproject.toml`'s own `[tool.mypy]` exclude comment and
  `digital_twin/typecheck.ini`'s own docstring for the full account.
- **Unit tests run under a real MicroPython Unix-port interpreter, not pytest/CPython** — "as close
  to the real environment as possible" means the actual runtime, not CPython plus MicroPython-
  flavored stubs (see `tests/README.md`'s "Why not pytest"). `scripts/test.sh` builds that
  interpreter on first run (`toolchain/setup_toolchain.py`'s `setup` — building/verifying the
  Unix port is just part of what `setup`/`test` already do, there's no separate `unix`
  subcommand — cached under `$PICO_TOOLCHAIN_DIR`) and shells out to it once per `tests/test_*.py`
  file; see `tests/README.md` for the full rationale and the minimal `test_*`-function runner
  (`tests/microtest.py`) used in place of CPython's `unittest`.
- **`scripts/test.sh --coverage` reports `src/` line coverage; it never gates anything** — no
  threshold is enforced anywhere, by design (confirmed directly, not a placeholder for a future
  gate). Since `coverage.py` only runs under CPython while `src/` only ever runs
  under the real MicroPython Unix-port interpreter, collection (`tests/_coverage_runner.py`,
  `sys.settrace` inside MicroPython) and rendering (`scripts/_render_coverage.py`, a second
  self-contained `uv run` script, under CPython) are two separate stages glued together through
  `coverage.py`'s own `CoverageData` API — see `tests/README.md`'s "Coverage" section for the full
  pipeline. The Unix port binary is always built with `MICROPY_PY_SYS_SETTRACE=1`
  (`build_unix_port()` in `toolchain/setup_toolchain.py`) — an inert hook check when unused, not a
  behavior change, confirmed directly — so plain `scripts/test.sh` and `--coverage` share one
  binary; `ports/rp2`'s firmware build never gets this flag. CI
  (`.github/workflows/ci.yml`) runs it as a non-gating step: a markdown summary goes to that run's
  GitHub Actions Job Summary (not the repo's main page), the HTML report is a downloadable build
  artifact (GitHub doesn't render it inline), and the Cobertura XML uploads to Codecov — which
  needs this repo registered at codecov.io plus a token/OIDC setup that hasn't happened yet, so
  that upload currently no-ops. Locally, `--coverage` only prints the output paths; nothing opens
  automatically. See README.md's "Test coverage" section for the full user-facing rundown.
- **CI hang investigation (resolved)**: `unit-tests` hung intermittently and repeatedly, always the
  same symptom — `test_asy_uart_driver.py`'s MicroPython process going completely silent for the
  rest of the job (first seen as a full 6-hour stall before `timeout-minutes` existed; see PR
  #24/#25's history). An early round of isolation (bisect-matrix runs, solo vs. concurrent-job-burst
  comparisons) pointed at GitHub Actions runner-level contention and produced three successive
  mitigations in `scripts/test.sh`/`ci.yml` (per-file `timeout`+retry, `stdbuf -oL -eL` line
  buffering, `needs: lint-and-typecheck` job sequencing) — **none of which actually stopped the
  hang**; they only turned a silent multi-hour stall into a fast, attributable ~12-13 minute
  failure. The real root cause, found by adding a diagnostic `asyncio.wait_for(5)` bound around
  the test file's own `run()` helper: ~17 tests in `test_asy_uart_driver.py` feed data via
  `feed_rx()` then call `uart.read()`/`write()` with no explicit `timeout_ms`, hitting
  `asy_uart_driver.py`'s `ready()`'s `timeout_ms=-1` (wait forever) branch — the only place in the
  whole file relying on the *real* `select.poll()` to detect readiness via `tests/machine.py`'s
  pure-Python `io.IOBase` fake UART's `ioctl()`, instead of the bounded `_StepPoller` test double
  every other test in the file already used. On GitHub Actions specifically (never locally, including
  under simulated single-core CPU contention), that real-poll/ioctl-on-a-non-fd-Python-object path
  never detects readiness at all — confirmed deterministic, not intermittent, once the diagnostic
  bound made the failure visible as `TimeoutError` instead of a silent stall. **Fix**: switched all
  17 tests to the same `_StepPoller` double, removing the dependency entirely — verified with 21/21
  clean CI jobs across three separate branches/configurations before landing on the real branch.
  The three earlier mitigations (per-file timeout/retry, stdbuf, job sequencing) are kept as a
  standing "hanging is never allowed" backstop against any *future* hang, not because they fixed
  this one — an isolation test with all three reverted, running only the `_StepPoller` fix, passed
  8/8 clean CI jobs on its own. Don't re-diagnose this specific symptom as a new code bug if it
  recurs elsewhere; do treat any *new* file/test that leaves `uart.poller` (or an equivalent
  fake-stream object) wired to a real `select.poll()` as a like-for-like risk.
- **Non-UTC-host test failures (resolved)**: on a developer machine whose system timezone isn't
  UTC, `tests/test_ntp_fram_system_integration.py`'s
  `test_fram_write_into_gets_a_real_valid_timestamp_once_the_real_ntp_chain_is_synced` and
  `test_system_service_boot_signature_resolves_via_the_real_ntp_chain_once_synced` failed every
  run (deterministic, not flaky) with a bare `AssertionError` at their final `abs(... -
  int(time.time())) < 5` line, while CI (GitHub-hosted `ubuntu-latest`, always UTC) stayed green.
  Root cause, confirmed directly against both the real MicroPython v1.28.0 Unix-port source and a
  live reproduction: the Unix port's `time.mktime()` (`ports/unix/modtime.c`) calls straight
  through to the host's real libc `mktime()`, which — per POSIX, and unlike the deployed rp2
  firmware — interprets its input `struct tm` as **local time** and converts using the process's
  `$TZ`. `src/asy_fram_manager.py`'s and `src/system_service.py`'s (and every other driver's)
  `time.mktime(time.gmtime())` idiom for "current UTC timestamp" is therefore only a true no-op
  round trip under `TZ=UTC`; under e.g. `TZ=Europe/Berlin` it silently comes back ~1 hour off
  (`tm_isdst` is forced to `0` by `gmtime()`'s 9-tuple, so it's standard-time offset, not the
  actual current DST offset), reproduced identically both with a hand-rolled snippet and by
  literally re-running the two failing tests with only `$TZ` changed (12/12 pass under `TZ=UTC`,
  the same 2/12 fail under `TZ=Europe/Berlin`, same line numbers, same "10/12 passed"). **Not a
  production bug**: confirmed directly from `ports/rp2/datetime_patch.c` that the deployed
  firmware overrides libc's `mktime()`/`localtime_r()` with `shared/timeutils`' pure, TZ-agnostic
  epoch arithmetic — real hardware has no `$TZ` concept and this idiom round-trips exactly there
  regardless. **Fix**: `scripts/test.sh` now does `export TZ=UTC` before invoking the Unix-port
  binary (for both the plain and `--coverage` passes, and every test file), pinning every local
  test run to the same UTC behavior GitHub's runners already gave for free — verified with a full
  99/99-passing `scripts/test.sh` run under `TZ=Europe/Berlin` in the calling shell after the fix.
  Don't re-diagnose a consistent (not intermittent) failure isolated to this file's two live-clock
  assertions as a new code bug — check the runner's `$TZ` first.
- **`ruff format` is deliberately not used anywhere** — line breaks are hand-chosen throughout this
  codebase; `line-length = 320` (ruff's own ceiling) plus an `E501` ignore keep this a non-issue even
  if `format` is ever run by accident. Lint rule selection (`E`/`F`/`W`/`I`/`UP`/`B`) is stricter
  than ruff's default but well short of enabling everything.
- **Bare `except:` (E722) is intentionally left enabled**, unlike the old `improved-quality/pycheck.sh`
  — the project owner wants ruff to flag existing bare excepts as a tracked to-do, not silence them
  before they're fixed (test-driven-development framing, confirmed directly).
- **Union type annotations: always PEP 604 `X | Y` (and `X | None`), never `typing.Union[...]`.**
  Confirmed safe at runtime on both the deployed 1.26 pin and the refactor's 1.28.0 target by
  testing directly against the pinned Unix-port interpreter (`int | None` in an unquoted, executed
  annotation works with no import needed) — MicroPython parses but never evaluates annotation
  expressions at all, so this isn't even a runtime-support question, just a style one. `typing.Union`
  needs `from typing import Union`, which isn't guarded by `TYPE_CHECKING` in every file that still
  uses it and would raise `ImportError` on-device if actually reached at runtime — one more reason
  `|` is strictly better here, not just newer. This is already machine-enforced: ruff's `UP007` rule
  (part of the enabled `UP` selection) flags every `Union[...]` as a finding. `src/` and `tests/`
  are already 100% `|`-style with zero `Union[...]` occurrences. `improved-quality/`'s one WIP file
  (`sensortask-wozi.py`, in ruff's checked scope) is likewise already 100% `|`-style today — its
  remaining tracked lint findings are elsewhere (`UP006`/`UP035`/`UP037`/`I001`/`F401`/`E722`). The
  `Union[...]` usages that do exist today are confined to `python/` (deployed, frozen, no lint
  config at all) — leave those alone under the usual out-of-scope-editing hard rule; don't drive-by
  "fix" `Union` → `|` in a file you're not otherwise promoting/refactoring.
- **mypy is stricter than default, short of `--strict`** (`disallow_untyped_defs`,
  `check_untyped_defs`, `warn_return_any`, `warn_unreachable`, `strict_equality`, etc., but not
  `disallow_any_generics`/`disallow_untyped_calls`/`disallow_subclassing_any`). Does **not** disable
  the `assignment` error code — the old `improved-quality/mypy.ini` did, though that was never a
  deliberate choice.
- **MicroPython stubs**: `micropython-rp2-rpi_pico_w-stubs` (PyPI, board/version-specific, pulls in
  `micropython-stdlib-stubs`). Published by the same project as
  [`josverl/micropython-stubs`](https://github.com/josverl/micropython-stubs) — PyPI is just its
  distribution channel, not a separate/alternative stub source. **Version is auto-derived, not a
  separate hand-kept pin**: `scripts/typecheck.sh` reads `toolchain/versions.toml`'s
  `[micropython] ref` (the single source of truth for the firmware version target) and installs
  the matching `<major>.<minor>.<patch>.*` stub release, failing with a clear, actionable error
  (not a silent fallback) if `ref` isn't a plain `vX.Y.Z` tag or no matching stub release exists
  upstream yet (stub releases can lag a new MicroPython release). Installed into `typings/`
  (gitignored) — **deliberately not** a
  `pyproject.toml` `[dependency-groups]` entry, because these stubs must fully replace mypy's
  typeshed for MicroPython/CPython stdlib-name collisions (`time`, `math`, `select`, `errno`, ...
  — see `[tool.mypy]`'s `custom_typeshed_dir`), and doing that against the same venv that also
  holds mypy/ruff/pytest's own dependencies breaks type-checking of those. Keep this isolation if
  you touch the stub setup — it's load-bearing, not incidental, confirmed by testing the collision
  directly in-session.
- **`scripts/typecheck.sh`'s combined `mypy src tests` run resolves every `from machine import X`
  project-wide to `tests/machine.py`'s fake module, not the real `typings/machine.pyi` board stub**
  — confirmed directly by running `mypy src` alone (no `tests` in scope): the real stub's `Timer`
  class has no zero-argument constructor overload (every overload requires a positional `id: int`
  first argument) and doesn't declare `I2C.deinit()` at all, so an `src`-only run raises 13 errors
  across `asy_ntp_client.py`/`asy_sgp40_driver.py`/`asy_scd30_driver.py`/`asy_bmp3xx_driver.py`
  (bare `Timer()` construction) and `asy_i2c_driver.py` (`self._i2c.deinit()`) that never surface in
  the actual, documented `mypy src tests` invocation. Both are real, working MicroPython patterns
  (bare `Timer()` allocate-now/`init()`-later is valid runtime usage; `I2C.deinit()` releases the
  peripheral's pins) — this is a **gap in the third-party `micropython-rp2-rpi_pico_w-stubs`
  package**, not a bug in any promoted driver, and `tests/machine.py`'s fake happens to model both
  correctly. Net effect: harmless today, but worth knowing that the real board stub's coverage is
  incomplete for these two APIs specifically if a future `src`-only or `--strict`-adjacent
  type-check run is ever added.
- **`improved-quality/microdot.py` no longer exists** — it was a confirmed *unintentional* fork of
  vendored Microdot, removed and replaced with a fresh, unmodified sync at `ext/microdot.py`
  (pinned to tag `v2.6.2`; see "Hard rules" above and "Microdot / REST layer" below). See
  BACKLOG.md's "Deferred" list for the resulting dead `pyproject.toml` exclude entry.

## Pre-push verification (clean Ubuntu 24.04)

**Before pushing any change to `pyproject.toml`, `scripts/`, `toolchain/versions.toml`, or
anything else touching the dev-tooling/build-environment setup**, verify it end-to-end inside a
genuinely clean Ubuntu 24.04 environment — not just in whatever sandbox this session happens to
be running in. A session sandbox typically already has Python 3.11+, `uv`, build tools, etc.
pre-installed, which can mask real gaps. **This already caught a real bug once**: a
`requires-python = ">=3.10"` that let `uv sync` build a venv without `tomllib` (stdlib only since
3.11), invisible in a sandbox whose default Python happened to already be 3.11+, and only found by
actually testing under a 3.10 interpreter. Treat this as a standing QA step, not a one-off — don't
skip it just because "it worked in this session's sandbox."

**Recipe** (needs root; mirrors how `toolchain/setup_toolchain.py`'s own "verified from scratch"
claims were checked — see `toolchain/README.md`'s "Evidence this actually works"):

```bash
# One-time: build a clean Ubuntu 24.04 (noble) chroot with nothing preinstalled beyond the
# minimal base - matching the OS the project's docs actually target, not this session's sandbox.
apt-get install -y debootstrap
CHROOT=/tmp/noble-chroot   # anywhere with a few hundred MB free; not part of this repo
debootstrap --variant=minbase noble "$CHROOT" http://archive.ubuntu.com/ubuntu

# Enable universe (off by default under debootstrap, on by default on every real Ubuntu ISO - see
# "Platform target" above) and wire up DNS + the usual chroot bind mounts.
cat > "$CHROOT/etc/apt/sources.list" <<'EOF'
deb http://archive.ubuntu.com/ubuntu noble main universe
deb http://archive.ubuntu.com/ubuntu noble-updates main universe
deb http://security.ubuntu.com/ubuntu noble-security main universe
EOF
cp /etc/resolv.conf "$CHROOT/etc/resolv.conf"
mount --bind /proc "$CHROOT/proc"; mount --bind /sys "$CHROOT/sys"
mount --bind /dev "$CHROOT/dev"; mount --bind /dev/pts "$CHROOT/dev/pts"

# This session's outbound HTTPS goes through a local policy proxy (see /root/.ccr/README.md if
# present) - the chroot shares the host's network namespace, so it just needs the same env
# vars/CA bundle passed through. Skip this block entirely on a plain machine with direct internet
# access (e.g. the project owner's own dev box).
if [ -f /root/.ccr/ca-bundle.crt ]; then
    mkdir -p "$CHROOT/root/.ccr"
    cp /root/.ccr/ca-bundle.crt "$CHROOT/root/.ccr/ca-bundle.crt"
    cat > "$CHROOT/root/proxy-env.sh" <<EOF
export HTTPS_PROXY="$HTTPS_PROXY" https_proxy="$HTTPS_PROXY"
export NO_PROXY="$NO_PROXY" no_proxy="$NO_PROXY"
export SSL_CERT_FILE=/root/.ccr/ca-bundle.crt CURL_CA_BUNDLE=/root/.ccr/ca-bundle.crt
export GIT_SSL_CAINFO=/root/.ccr/ca-bundle.crt REQUESTS_CA_BUNDLE=/root/.ccr/ca-bundle.crt
export PIP_CERT=/root/.ccr/ca-bundle.crt
export LANG=C.UTF-8 LC_ALL=C.UTF-8 DEBIAN_FRONTEND=noninteractive
EOF
    # astral.sh (the official `uv` installer's domain) is blocked by this session's egress
    # policy - use `pip install uv` (README's documented alternative) instead of the curl
    # installer when testing inside this specific sandbox.
else
    echo 'export LANG=C.UTF-8 LC_ALL=C.UTF-8 DEBIAN_FRONTEND=noninteractive' > "$CHROOT/root/proxy-env.sh"
fi

chroot "$CHROOT" /bin/bash -c "source /root/proxy-env.sh && apt-get update && apt-get install -y --no-install-recommends git curl ca-certificates python3 python3-venv python3-pip sudo"
chroot "$CHROOT" /bin/bash -c "source /root/proxy-env.sh && pip install --break-system-packages uv"
# sudo is not part of debootstrap --variant=minbase, but toolchain/setup_toolchain.py's
# ensure_apt_packages() unconditionally shells out to it (see toolchain/versions.toml's
# apt_packages, used by both its `setup`/`test` subcommands) - without it, `scripts/test.sh`
# fails with "sudo: command not found" even though a real dev machine (where the calling user has
# sudo rights but isn't already root) never hits this. A plain chroot session runs as root, where
# apt-get wouldn't need sudo at all, but the script always prepends it regardless - so installing
# the package is the correct fix here, not stripping sudo from the script for a root-only case.

# Per-verification: copy the CURRENT working tree (uncommitted changes included - this is a
# pre-push gate, not a post-push audit) into the chroot, then run the exact documented workflow
# from README.md's "Code quality tooling" section.
rm -rf "$CHROOT/root/sensors"
cp -r /path/to/this/repo/checkout "$CHROOT/root/sensors"   # adjust to wherever it's actually checked out
chroot "$CHROOT" /bin/bash -c "
  source /root/proxy-env.sh
  cd /root/sensors
  rm -rf .venv typings   # don't carry over host-built artifacts
  uv sync
  source .venv/bin/activate
  scripts/lint.sh
  scripts/typecheck.sh
  scripts/test.sh   # builds the MicroPython Unix port from scratch inside the chroot (no cached
                     # ~/pico-toolchain carried over) - this is what actually exercises
                     # toolchain/versions.toml's apt_packages list end-to-end, same spirit as the
                     # rest of this recipe
"

# Cleanup when done
umount "$CHROOT"/dev/pts "$CHROOT"/dev "$CHROOT"/sys "$CHROOT"/proc
rm -rf "$CHROOT"
```

**What counts as passing**: `lint.sh`/`typecheck.sh` run to completion with no config/crash errors
— a nonzero exit from real lint/type findings is expected and fine, since `improved-quality/` isn't
clean yet (see BACKLOG.md); the number of findings will drift as the code changes, so match against
what the same scripts produce in the ordinary session sandbox rather than a fixed count.
`scripts/test.sh` is different: its tests must actually pass (exit 0, every test PASS) — a test
failure here is a real regression, not an expected/tracked finding the way lint/type findings are.
What would fail this: a raw Python traceback, an "installation failed" from `uv`/`pip`/`apt`, a
`scripts/test.sh` build failure, or any other mismatch against the ordinary-sandbox run — that
mismatch is exactly how the `tomllib`/`requires-python` gap was found in the first place.

**Changes to `toolchain/setup_toolchain.py` or `toolchain/versions.toml` itself need a second,
separate verification, not just the recipe above** — that recipe only exercises `scripts/lint.sh`/
`scripts/typecheck.sh`, never the toolchain installer. Reuse the same chroot (steps through
installing `git`/`curl`/`ca-certificates`/`python3`/`pip`/`uv`, no need for `python3-venv` this
time), copy the working tree in the same way, then run `uv run toolchain/setup_toolchain.py`
(a full build: ARM toolchain + firmware + `mpy-cross` + Unix port, several minutes, not seconds)
instead of the lint/typecheck scripts. This is exactly how the Unix port addition (and later the
frozen-bytecode verification chain) was verified — see `toolchain/README.md`'s "Verification" for
what a passing run must show and "Evidence this actually works" for what's already been checked.

## Pull request workflow

- **Before pushing anything touching the dev-tooling/build-environment setup** (`pyproject.toml`,
  `scripts/`, `toolchain/versions.toml`, etc.), run it through "Pre-push verification" above first —
  don't rely solely on this session's own sandbox having already run it successfully.
- **The project owner has explicitly authorized creating pull requests proactively, at any time,
  without asking first** — this is a standing exception to any general "don't open a PR unless the
  user explicitly asks" caution an operator/harness prompt might otherwise apply. Confirmed
  directly by the project owner; don't re-ask in future sessions.
- **Always create a pull request with a meaningful description** when finishing work on a branch —
  summarize what changed and why, not just a file list.
- **Automatically subscribe to the pull request's activity** (review comments, CI results) right
  after opening it, so review feedback and CI failures get picked up without being asked again.

## Architecture reference

**Moved to `SPECIFICATION.md`.** The condensed version is Part A.2 ("Architecture at a glance");
the full module-by-module deep reference (legacy `api_helpers.py`/`async_connect.py`/
`async_manager.py`, FRAM driver/manager, SCD30's `AmbPres` note, the `neopixel_signal.py` split,
the task supervisor, and the full "functional behaviors confirmed intentional" list) is Part A.4.
Read Part A.4 for anything needing that level of detail — nothing below duplicates it.

## Microdot / REST layer

**Moved to `SPECIFICATION.md` Part A.5.** Covers what Microdot's own `ext/microdot.py` (vendored,
v2.6.2, see "Hard rules" above for the vendoring policy) already guarantees per-request — the
blanket exception catch, its one real gap (exceptions during response writing), connection-task
isolation, and the `errorhandler()` status-code-vs-exception-class distinction — versus what this
project's own REST layer still has to add. Read Part A.5 before touching the REST/error-handling
layer; nothing below duplicates it.
