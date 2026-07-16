# CLAUDE.md

Operating constraints and architecture reference for AI sessions working in this repo. See
README.md for human-facing orientation and BACKLOG.md for the open-questions/deferred-work list.

## Platform target

- Deployed units run **MicroPython 1.26** on **Raspberry Pi Pico W (1st gen / RP2040)**. Code
  ships as **frozen bytecode** compiled into the firmware — it is not loaded from the device
  filesystem at runtime, and CPython-only stdlib features/behavior cannot be assumed.
  - Upstream MicroPython has moved past 1.26 (1.28.0 was the latest stable as of the last
    doc-verification pass) — don't assume "current docs" and "1.26 behavior" are the same thing.
    When in doubt about whether an API changed between 1.26 and latest, say so explicitly rather
    than silently documenting latest-only behavior as if it applies to deployed devices.
  - **1.26 is the pin for the current, deployed codebase only.** The `improved-quality/` refactor
    is explicitly meant to move the version target forward to whatever is the most recent *stable*
    release at that time (MicroPython, pico-sdk, picotool, Microdot) and to actively use relevant
    improvements/new features those releases introduced — not just reproduce 1.26-era behavior
    under a newer version number. See BACKLOG.md's "Decided for the refactor" section.
  - **MicroPython 1.26 already bundles pico-sdk 2.1.1 as its internal `ports/rp2` submodule** —
    confirmed via web search, not training-data memory. Since pico-sdk 2.0.0, a standalone
    `picotool` build must match the pico-sdk major.minor version it's used against (enforced via
    marker files from `sudo make install`/`cmake --install`, not just having the binary on `PATH`)
    or the build fails with "Incompatible picotool installation found." This means
    `update_and_install.txt`'s standalone `pico-sdk`/`picotool` clones need to be checked out at a
    matching `2.1.x` tag *today*, not just "whatever's current" — see BACKLOG.md's "Dev/build
    environment setup" item for the full finding.
  - `machine.WDT` hard-caps at **8388ms** on RP2040. Current code uses `WDT(timeout=8000)` — only
    388ms of margin. Don't casually increase this without checking the cap still holds against
    current docs.
  - `RP2040`: dual-core Cortex-M0+ @ up to 133MHz, 264KB SRAM (6 banks), 2×I2C, 2×SPI, 2×UART,
    8×PIO state machines.
  - Pico W's littlefs partition (~848KB) is smaller than plain Pico's (~1.37MB) because Pico W's
    firmware image is larger (CYW43 driver + WiFi/BT firmware blobs baked in) — the filesystem
    occupies whatever flash remains after the firmware image, not a fixed per-board reservation.
- **Always check current MicroPython and Microdot documentation before asserting how an API
  behaves** — do not rely on training-data memory for either. This has already caught real
  discrepancies once; treat it as a standing requirement for every session, not a one-time step.

## Hard rules

- **Don't edit `improved-quality/`'s *source* files (drivers, managers, etc.) — they're the WIP
  refactor target, out of scope for routine editing.** This does **not** cover its dev-tooling
  config: `mypy.ini`/`pycheck.sh` were an ad hoc, trial-and-error setup the project owner
  explicitly asked to have questioned and replaced (confirmed directly, not inferred) — they've
  been retired in favor of root-level `pyproject.toml` + `scripts/lint.sh`/`scripts/typecheck.sh`
  (see "Code quality tooling" below). Source files elsewhere in `improved-quality/` remain
  read-only context until the refactor itself starts.
- **`src/` is where files land once they're fully reviewed and tested** — formula/logic
  correctness checked, input validation and exception-safety audited, unit tests written and
  passing (see "Code quality tooling" below and `tests/README.md`), unlike `improved-quality/`'s
  WIP files above. **`src/README.md` is the full checklist** for what "fully reviewed and tested"
  actually requires — apply it to every file that makes this move, not just whichever ones already
  have. Files in `src/` aren't automatically re-wired into any driver's actual import path for a
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
  routine editing.
- **`dev` config is a bench rig only** — its quirks (e.g. LED/Neopixel REST routes referencing an
  object that's never instantiated) are explicitly out of scope. Don't fix them as if they were
  bugs.
- **No unit tests against the current (deployed, pre-refactor) codebase — `python/`, `modules/`.**
  The agreed plan is: fully understand the current system first, confirm what's already
  transferred into `improved-quality/`, and write tests as part of that refactor — not before, and
  not against the current code. This does **not** contradict BACKLOG.md's detailed testing
  requirements (tests under a real MicroPython Unix-port interpreter, `uv`-managed venv, mocking
  boundary, etc.) — those describe what the *refactored* code must eventually have. **First
  concrete instance**: `src/math_helpers.py` has a full `tests/test_math_helpers.py` suite,
  running under a real MicroPython Unix-port interpreter per that plan (see "Code quality tooling"
  below) — this rule is about not testing the old `python/`/`modules/` code, not about deferring
  all tests indefinitely.
- **Don't touch `sensors/config.json`-equivalent files or commit any real credentials.** A real
  WiFi SSID/password was previously committed and had to be scrubbed from history — see
  BACKLOG.md's security notes. A `.gitignore` now covers per-device config/build artifacts, but
  still be deliberate about what you stage.
- **Long-blocking operations must not stall timing-sensitive work.** Any new code that blocks the
  event loop for a noticeable time (e.g. `socket.getaddrinfo()`) must not do so while
  timing-sensitive work like the Neopixel animation needs to run — either avoid the block, or
  coordinate via `async_connect.py`'s `get_long_block_lock()` pattern so timing-sensitive code runs
  before/around it. This is a standing convention for all new code, not just the original
  NTP-vs-Neopixel case it was written for.

## Working agreements

- Long-term goal: fully understand the current (production) system in detail, then check what's
  already been addressed/transferred well into `improved-quality/`. The refactor should end up
  with the *same top-level features*, just more consistent/stable — not a feature change.
- When a fact in this file or BACKLOG.md turns out to be stale (version drift, changed upstream
  API, etc.), update the doc in the same session rather than silently working around the
  discrepancy.
- Prefer flagging genuinely ambiguous/architecturally significant decisions to the project owner
  over guessing — several open questions in BACKLOG.md exist precisely because the code's actual
  intent wasn't obvious from reading it alone.

## Code quality tooling

- **Config lives in root `pyproject.toml`** (ruff/mypy/pytest/uv, dev-tooling only — the shipped
  code stays frozen-bytecode-only, not restructured into an installable package). Run manually via
  `scripts/lint.sh` (ruff), `scripts/typecheck.sh` (mypy), and `scripts/test.sh` (unit tests, under
  a real MicroPython Unix-port interpreter — see below and `tests/README.md`); `lint.sh`/
  `typecheck.sh` assume `ruff`/`mypy` are already on `PATH` (e.g. an activated `uv sync`-created
  venv). **Wired into CI** via `.github/workflows/ci.yml` (GitHub Actions — this repo is
  GitHub-hosted; older BACKLOG.md text said "GitLab", which was never actually checked against
  where the repo lives and has since been corrected), running all three on every push/PR. The CI
  pipeline does not yet include a real firmware-build stage (see BACKLOG.md).
- **Scope is `improved-quality/`, `src/`, and `tests/`, for now.** The pre-refactor deployed
  codebase (`python/`, `modules/`) has no lint/type config yet; extending scope there is a separate
  future decision, not assumed by this setup.
- **Unit tests run under a real MicroPython Unix-port interpreter, not pytest/CPython** — per
  BACKLOG.md's "Self-contained venv via `uv`" requirement. `scripts/test.sh` builds that
  interpreter on first run (`toolchain/setup_toolchain.py`'s `setup` — building/verifying the
  Unix port is just part of what `setup`/`test` already do, there's no separate `unix`
  subcommand — cached under `$PICO_TOOLCHAIN_DIR`) and shells out to it once per `tests/test_*.py`
  file; see `tests/README.md` for the full rationale and the minimal `test_*`-function runner
  (`tests/microtest.py`) used in place of CPython's `unittest`.
- **`scripts/test.sh --coverage` reports `src/` line coverage; it never gates anything** — no
  threshold is enforced anywhere, by design (confirmed directly, not a placeholder for a future
  gate — see BACKLOG.md). Since `coverage.py` only runs under CPython while `src/` only ever runs
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
  expressions at all (also documented in BACKLOG.md's PEP 604 entry, verified against current
  MicroPython docs), so this isn't even a runtime-support question, just a style one. `typing.Union`
  needs `from typing import Union`, which isn't guarded by `TYPE_CHECKING` in every file that still
  uses it and would raise `ImportError` on-device if actually reached at runtime — one more reason
  `|` is strictly better here, not just newer. This is already machine-enforced: ruff's `UP007` rule
  (part of the enabled `UP` selection) flags every `Union[...]` as a finding. `src/` and `tests/`
  are already 100% `|`-style with zero `Union[...]` occurrences. The `Union[...]` usages that do
  exist today are confined to `python/` (deployed, frozen, no lint config at all) and pre-existing
  `improved-quality/` WIP files (in ruff's checked scope, already showing up as tracked `UP007`
  findings in the lint baseline) — leave those alone under the usual out-of-scope-editing hard rule;
  don't drive-by "fix" `Union` → `|` in a file you're not otherwise promoting/refactoring.
- **mypy is stricter than default, short of `--strict`** (`disallow_untyped_defs`,
  `check_untyped_defs`, `warn_return_any`, `warn_unreachable`, `strict_equality`, etc., but not
  `disallow_any_generics`/`disallow_untyped_calls`/`disallow_subclassing_any`). Does **not** disable
  the `assignment` error code — the old `improved-quality/mypy.ini` did, but BACKLOG.md records that
  as never a deliberate choice.
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
- **`microdot.py` is excluded from both tools' direct checks** (vendored, not ours to restyle —
  see the hard rule above), but code that *imports* it is still fully checked; mypy's
  `follow_imports`/`follow_imports_for_stubs` settings make this work for both regular Python files
  and the `.pyi` stub files in `typings/` (stub files are otherwise exempt from `follow_imports` by
  default — a real, tested distinction, not a guess).

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
what a passing run must show and "Evidence this actually works" for what's already been checked,
plus BACKLOG.md's "Self-contained venv via uv" for that specific verification's results.

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

See README.md's "Architecture at a glance" section for the condensed version. Key modules if you
need to go deeper:

- `python/CommonDrivers/api_helpers.py` — generic REST validate → apply-to-sensor → persist
  pipeline, repeated by hand for every endpoint (no shared schema/route generation — see
  BACKLOG.md's config-duplication item).
- `python/CommonDrivers/async_connect.py` — WiFi STA + AP/hotspot fallback + NTP client with
  manual CET/CEST DST math (`cettime()`); exposes `get_long_block_lock()`, a shared lock
  serializing `socket.getaddrinfo()` against Neopixel animation — this pattern is now the general
  convention for long-blocking operations, see "Hard rules" above.
- `python/CommonDrivers/async_manager.py` — `ConfigManager`, `DataManager`,
  `TimeCounterManager`, `LockedValue`/`Flag`.
- `python/IndividualDrivers/asy_fram_driver.py` / `asy_fram_manager.py` — raw SPI FRAM driver +
  chunk allocator with dual-copy redundancy (arzi/neu/wozi only, not dev).
- **SCD30's `AmbPres` (ambient-pressure compensation) is stored in the sensor's own internal
  non-volatile memory as a one-time-set value, not a continuously-updated live input.** This is why
  it's a static config value on every unit — including wozi, which has a live BMP388 — and why
  `set_ambient_pressure` is called with `force=True` in the REST handler: resending the same value
  is also the SCD30's documented command to resume continuous measurement after it's been stopped.
  Don't "fix" this into a live BMP388→SCD30 feed; it's intentional, confirmed by the project owner.
- Task supervisor lives in `main()` inside each `sensortask-*.py`, not in a shared module — it's
  duplicated per device file today.
