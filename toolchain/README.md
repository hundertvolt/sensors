# Build environment installer

One command sets up (or updates) everything needed to build MicroPython firmware for the
Raspberry Pi Pico W: MicroPython itself, a matching `pico-sdk`, a version-matched `picotool`,
and the ARM cross-compiler — plus a host-side MicroPython Unix port build, used for running
tests under the real interpreter later instead of just CPython with MicroPython-flavored stubs
on top (see BACKLOG.md's "Self-contained venv via uv").

## Why this isn't just "apt install the toolchain"

Two problems make a naive install unreliable, and this script exists specifically to solve
both:

1. **The four pieces have to agree with each other exactly, or the build silently breaks.**
   `picotool` has enforced a matching major.minor version against the `pico-sdk` it's built with
   since pico-sdk 2.0.0 (a mismatch fails outright with "Incompatible picotool installation
   found"), and the `pico-sdk` version has to be whatever MicroPython's own build actually
   compiles against — not just "some recent pico-sdk". Getting this right by hand means cross-
   referencing three separate repos' tags/submodule pins every time you change versions. See
   "How the versions fit together" below for how the script avoids this by construction instead
   of by careful bookkeeping.
2. **Every dev machine has its own installed tools and environment variables, and any of them
   could silently change what gets built.** A leftover `CFLAGS` from an unrelated project, a
   personal `~/bin/cmake` earlier in `PATH`, a different `picotool` already installed — none of
   these should be able to change the output of a build that's supposed to be reproducible. See
   "Environment isolation" below.

## Quick start

```sh
uv run toolchain/setup_toolchain.py                              # install/update per versions.toml
uv run toolchain/setup_toolchain.py --latest                      # pin + install newest stable MicroPython
uv run toolchain/setup_toolchain.py --micropython-ref v1.26.1     # build a specific ref instead
uv run toolchain/setup_toolchain.py --clean                       # wipe build dirs, then rebuild from scratch

uv run toolchain/setup_toolchain.py test                          # re-verify an existing install, offline
```

No `pip install`/venv setup needed by hand for the script itself — `uv run` provisions an
ephemeral, cached interpreter (see "Why not a full venv" below). There are two subcommands,
`setup` and `test`; `setup` is the default if you omit it, so all of the invocations above except
the last one are really `setup` in disguise. Both also build and verify a MicroPython Unix-port
interpreter at the same pinned ref (sharing the same `--toolchain-dir` checkout, just a different
`ports/` subdirectory) alongside the RP2040 firmware — see "How it works" below, `../tests/README.md`
for why the test suite runs under that instead of CPython/pytest, and `scripts/test.sh`, which
runs `setup` automatically the first time it needs the interpreter. That Unix-port binary is
always built with `MICROPY_PY_SYS_SETTRACE=1` (an inert, behavior-neutral hook check when unused —
see `build_unix_port()`), so the same binary backs both plain `scripts/test.sh` and
`scripts/test.sh --coverage` (see `../tests/README.md`'s "Coverage" section) — no second Unix port
build. The RP2040 firmware build never gets this flag; it's dev/test tooling only.

**Prerequisites:**

- `sudo` access (used for `apt-get install` and `picotool`'s `make install`).
- Outbound network access to GitHub and your distro's package mirrors.
- [`uv`](https://docs.astral.sh/uv/) itself already installed (`pip install uv`, or the official
  `curl -LsSf https://astral.sh/uv/install.sh | sh` installer).
- Ubuntu's `universe` apt component enabled — the default on every official Ubuntu image, so
  this only matters on a deliberately minimal base (e.g. a bare `debootstrap` rootfs, which
  enables only `main` unless told otherwise); `gcc-arm-none-eabi` and its newlib packages live
  in `universe`.

## How it works

The whole design follows from the two problems above. Walking through what `setup` actually
does, in order:

1. **Check out MicroPython at the pinned ref.** `versions.toml` records exactly one hand-picked
   version — the MicroPython tag — because everything downstream can be *derived* from it rather
   than tracked separately (see step 2). This is also the only version a human ever needs to
   decide on; bumping it (by hand, or via `--latest`) is the entire "what do I upgrade to" question.
2. **Derive the matching `pico-sdk` version, instead of pinning it separately.** MicroPython's own
   git repo already records which `pico-sdk` commit it builds against, as an ordinary git
   submodule pin at `lib/pico-sdk`. The script reads that pin directly
   (`derive_pico_sdk_commit()`) rather than maintaining a second, independent version number that
   could drift out of sync with the first one.
3. **Derive the matching `picotool` version the same way.** Since `picotool` only requires a
   major.minor match against `pico-sdk` (not an exact commit), the script resolves the derived
   pico-sdk commit to its nearest tag, takes the major.minor, and picks the newest `picotool` tag
   sharing it (`derive_picotool_ref()`). Two derivations, zero independently-tracked version
   numbers beyond the one in step 1.
4. **Install the ARM cross-compiler from the distro's `gcc-arm-none-eabi` package.** Unlike the
   other three, this one genuinely doesn't need a hand-tracked pin — it's a known-working,
   reproducibly-installable toolchain for pico-sdk 2.x straight from `apt`.
5. **Build everything inside an explicitly constructed, isolated environment**, not whatever the
   caller's shell happens to have set — see "Environment isolation" below. This is what makes
   the versions derived in steps 1–4 the actual versions used, instead of being second-guessed
   by a stray environment variable or a shadowing binary.
6. **Verify the result before declaring success**, every single run, via a frozen-bytecode chain
   rather than separate throwaway checks: freeze one small test module into both the Unix port
   and the RP2 firmware, import it *by name* inside the Unix port binary and check its result,
   clean up, then rebuild a vanilla Unix port as the standing test rig (see "Verification" below,
   and `run_verification_sequence()`'s docstring in `setup_toolchain.py` for the exact step
   order). A `setup` that finished without running this chain would just be an assertion that the
   pieces are probably fine; running it is what makes it a proof.

Step 6 is intentionally a mix of from-scratch and incremental: the firmware and Unix-port builds
always wipe their build directories first, so "builds with zero errors/warnings" is a genuine
proof every run rather than a cached one, but `mpy-cross`'s build directory is otherwise left
alone — if nothing in its source changed, it just relinks instead of recompiling. That's a
deliberate, useful property (a `setup`/update re-run doesn't waste time re-verifying unchanged
output), not an oversight — but it means there's normally no single command that forces
*everything* back to a truly from-scratch build state without also re-cloning gigabytes of
unchanged git history. `--clean` is that command: it wipes every build-artifact directory
(`picotool/build`, `mpy-cross/build`, `ports/rp2/build-<board>`, `ports/unix/build-standard`, via
`clean_build_dirs()`) before the steps above run, without touching the git clones themselves,
then proceeds through the normal build+verify flow — so it ends in the same state a genuinely
fresh install would.

`test` is `setup` with steps 1–4 skipped: it assumes an install already exists at
`--toolchain-dir` and just re-runs step 6's verification chain against whatever is already
checked out there. That split exists because steps 1–4 need network/apt access and can change
what's installed, while the verification chain doesn't need either and is what you actually want
to re-run repeatedly (locally, or eventually in CI — see "CI perspective" below) to confirm the
toolchain still builds cleanly.

## Environment isolation

Every subprocess this script runs — `git`, `apt-get`, `cmake`, `make`, `picotool`, the built
`mpy-cross` binary — gets an explicit, constructed environment instead of inheriting the
caller's shell wholesale. Two flavors, both defined right at the top of `setup_toolchain.py`:

- **`build_env()`** — for the actual compile steps (picotool's build, `mpy-cross`, the firmware
  build, running the cross-compiled sample): a fixed, deterministic `PATH`
  (`/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin`) plus a small allowlist
  (`HOME`, `USER`, `LOGNAME`, `TERM`, `TMPDIR`). Everything else — `CC`/`CXX`/`CFLAGS`/
  `CXXFLAGS`/`LDFLAGS`/`MAKEFLAGS`, any `CMAKE_*` variable, `PICO_SDK_PATH`/`PICO_BOARD`,
  `PYTHONPATH`, a leftover `http_proxy` meant for some unrelated tool — is dropped. The fixed
  `PATH` also means a shadowing binary earlier in the caller's `PATH` (a personal `~/bin/cmake`,
  a different `gcc-arm-none-eabi` build, an old `picotool`) can never be picked up instead of
  the toolchain this script itself just built/installed. `LANG`/`LC_ALL` are also *not* passed
  through — they're forced to `C.UTF-8` instead (see "Verified adversarially" below for why
  this matters more than it looks).
- **`network_env()`** — the same base, plus whatever proxy/CA configuration is actually present
  (`HTTPS_PROXY`/`https_proxy`/`HTTP_PROXY`/`http_proxy`/`NO_PROXY`/`no_proxy`/`ALL_PROXY`/
  `all_proxy`/`SSL_CERT_FILE`/`GIT_SSL_CAINFO`/`CURL_CA_BUNDLE`/`REQUESTS_CA_BUNDLE`), explicitly
  named rather than inherited wholesale. Used for `git`/`apt-get` calls, and for the rp2 port's
  `make submodules` target specifically because that one Makefile target both fetches submodules
  over git *and* runs a preliminary `cmake` configure pass — it needs the deterministic `PATH`
  and real network access at the same time (the concrete bug this exact split was built to fix —
  see "Verified adversarially" below).

`picotool`'s own install location is also pinned explicitly
(`-DCMAKE_INSTALL_PREFIX=/usr/local`, matching where it's later invoked from by absolute path)
rather than left to whatever a stray `CMAKE_INSTALL_PREFIX` or local `cmake` cache would
otherwise resolve to.

## Directory layout

```
<toolchain-dir>/          default: $PICO_TOOLCHAIN_DIR or ~/pico-toolchain
  micropython/             full clone, checked out at the pinned ref
    ports/rp2/build-<board>/    transient - built once with the frozen test module (step 6 of
                                 "Verification"), then removed in step 7; does not exist after a
                                 completed setup/test run
    ports/unix/build-standard/  host-side interpreter build output (micropython) - the one build
                                 artifact kept as a standing deliverable (step 8)
    mpy-cross/build/            cross-compiler build output (mpy-cross)
  pico-sdk/                full clone, checked out at the ref MicroPython pins
  picotool/                full clone, checked out at the derived matching tag; built + `sudo make install`ed
```

Full (non-shallow) clones are used deliberately, not just for the initial install — shallow
clones make the *update* path (fetch + checkout an arbitrary new ref) unreliable, and update
is a first-class requirement here, not an afterthought.

## Verification

Every `setup` or `test` run re-verifies the environment end-to-end via a single frozen-bytecode
chain (`run_verification_sequence()` in `setup_toolchain.py`), each step gating the next — a
`SetupError` from any step aborts the whole chain, so later steps never run against a broken
earlier one:

1. Write a small test module (`frozen_verify_test.py`: arithmetic, a comprehension, exception
   handling, a stdlib import, and a `RESULT` value to check).
2. Build `mpy-cross` (the cross-compiler).
3. Cross-compile the test module with `mpy-cross` directly — proves the cross-compiler itself
   works, independently of the freeze/build pipeline exercised next.
4. Build the Unix port (`ports/unix`, "standard" variant) with the test module frozen in via
   `FROZEN_MANIFEST=`, with no compiler errors or warnings.
5. Import the frozen module *by name* inside that Unix port binary — with no source `.py` file
   anywhere on disk for the interpreter to find — and check its result. The only way this can
   succeed is if the module was actually baked into the binary as frozen bytecode, not merely
   compiled and left on disk. `mpy-cross` and the Unix port build are now both verified. This is
   the host-side MicroPython build that tests will eventually run under (see BACKLOG.md's
   "Self-contained venv via uv").
6. Build the RP2 firmware for the target board (default `RPI_PICO_W`) with the same test module
   frozen in, with no compiler errors or warnings. Build-only: there's no RP2 hardware here to
   run it on, so a clean build is the whole check. Freezing extra bytecode is strictly additive
   to a build — it can't make an otherwise-broken toolchain succeed — so this is a strict
   superset of what a vanilla (no frozen module) RP2 build would have proven anyway; see
   `run_verification_sequence()`'s docstring for why a separate vanilla RP2 build isn't also kept.
7. Clean up the RP2 firmware and Unix port build directories from steps 4–6. `mpy-cross`'s and
   `picotool`'s build output are *not* touched — both are real toolchain deliverables needed for
   actual project work later, not verification-only artifacts.
8. Rebuild a vanilla (non-frozen) Unix port. This becomes the standing test rig used for running
   tests under the real interpreter later (see BACKLOG.md's "Self-contained venv via uv").

Any failure aborts with a non-zero exit and the build log leading up to it. Note this means a
completed `setup`/`test` run does **not** leave a vanilla RP2 `firmware.uf2` anywhere — only the
(also cleaned-up) frozen-module build from step 6, which existed purely to prove the toolchain
works. The Unix port from step 8 is the only build artifact kept as a standing deliverable.

## Evidence this actually works

Claims above that are checkable were checked, not just written down. The bullets mentioning a
specific "three checks"/"four checks" count below predate the 8-step frozen-bytecode chain
described in "Verification" above and refer to the simpler build-and-run-a-sample-script design
that chain replaced — they're kept as evidence for the still-true claims in each bullet
(clean-chroot install, the update path, environment isolation, the locale bug fix), not as a
description of the current step count.

- **Restructured into the 8-step frozen-bytecode chain**: re-ran `test` against an existing
  `v1.28.0` toolchain twice while building the new `run_verification_sequence()`. The first pass
  caught a real bug: `freeze(".")` in the generated manifests froze every `.py` file sitting next
  to the test module, including the manifest files themselves (`MPY manifest_unix.py` showed up
  in the build log where only `MPY frozen_verify_test.py` was expected) — harmless in practice but
  sloppy, so the test module was moved into its own dedicated subdirectory
  (`FROZEN_MODULE_SUBDIR`) that only ever contains that one file. Second pass confirmed the fix:
  `frozen_verify_test.py` is the only extra frozen module in both the Unix port and RP2 builds,
  the frozen import prints `FROZEN_VERIFY_OK: micropython` with no source file on disk, step 7
  removes both `ports/rp2/build-RPI_PICO_W` and `ports/unix/build-standard`, and the final vanilla
  Unix port rebuild's frozen-module list no longer includes `frozen_verify_test.py` anywhere.
- **A genuinely clean Ubuntu 24.04 system, from scratch**: a `debootstrap`-built `noble` chroot
  with nothing preinstalled beyond the minimal base (no build tools, no `git`/`curl`/`sudo`, no
  `uv`, no apt cache beyond `main`) — the script installed every system dependency itself (after
  enabling `universe`, see "Quick start" above) and passed all three checks in ~3 minutes, for
  both the latest stable MicroPython release and the currently-deployed `v1.26.1` pin. **Re-run
  after the Unix port build was added** (same from-scratch chroot recipe, `python3`/`pip`/`uv`
  only — everything else, including `libffi-dev` for the Unix port's `ffi` module, installed by
  the script itself): all four checks passed, including the Unix port build and its sample
  script.
- **The in-place update path**: existing `v1.26.1` install → re-run targeting the latest
  release. Existing clones are fetched and re-checked-out rather than re-cloned, the derived
  pico-sdk/picotool versions bump automatically, and only the affected pieces rebuild. **Verified
  with the Unix port specifically**: built and ran the sample script against `v1.26.1` first
  (`sys.implementation` correctly reported `(1, 26, 1, '')`), then re-ran targeting `v1.28.0`
  against the same `--toolchain-dir` — the Unix port rebuilt and the sample script re-ran
  correctly against the new version (`(1, 28, 0, '')`), with no leftover state from the old
  build.
- **`test` in isolation**: run against a `setup`-provisioned install, it completed in ~30s
  (vs. minutes for `setup`), touched no network or apt state, and passed all three (now four)
  checks. **`--clean` re-verified after the Unix port build was added**: confirmed it wipes
  `ports/unix/build-standard` along with the other build-artifact directories, and a full
  from-scratch rebuild afterward still passes all four checks.
- **Environment isolation, adversarially**: ran both `setup` and `test` with a deliberately
  hostile ambient environment — `CC`/`CXX` pointed at `/bin/false`, garbage `CFLAGS`/`CXXFLAGS`/
  `LDFLAGS`/`MAKEFLAGS`, a bogus `PICO_SDK_PATH`/`PICO_BOARD`/`PYTHONPATH`/`CMAKE_INSTALL_PREFIX`/
  `CMAKE_TOOLCHAIN_FILE`, and fake `cmake`/`arm-none-eabi-gcc`/`picotool` shell scripts (each just
  printing a marker and exiting 1) placed earlier in `PATH` than the real toolchain. Before the
  `network_env()`/`build_env()` split existed, `make submodules`'s internal `cmake` configure
  pass picked up the fake `cmake` and failed outright — the concrete bug that motivated the split
  in the first place, not a hypothetical one. After the fix, both `setup` and `test` completed
  successfully with zero trace of any of the injected poison in the build logs.
- **A real run on someone else's machine surfaced a second, subtler gap**: a full log from an
  actual Ubuntu 24.04 dev machine (German locale) showed `git`/`apt` output in German
  (`Klone nach`, `Submodul-Pfad ... ausgecheckt`) — meaning `LANG`/`LC_ALL` were still being
  passed through from the caller's shell at the time. That's a real problem, not just cosmetic:
  `build_firmware()`/`build_mpy_cross()`/`build_unix_port()` detect failure by grepping build
  output for the literal English `error:`/`warning:` (there's no other machine-readable signal
  from `make`/`gcc`), and
  GCC/binutils diagnostics *can* be translated via gettext catalogs on a system where the
  caller's locale has one installed — silently defeating that detection. Fixed by forcing
  `LANG=C.UTF-8`/`LC_ALL=C.UTF-8` in `build_env()` instead of allowlisting them through.
  Re-verified by re-running the full `setup` flow with `LANG=de_DE.UTF-8` set in the calling
  shell (reproducing the exact locale from that log): `git` output was confirmed back to English
  (`Cloning into ...` instead of `Klone nach ...`), and all three checks still passed.

## Why not a full venv

This mostly isn't Python-package territory: apt packages, multi-gigabyte git source trees,
and `cmake`/`make` builds of C/C++ toolchains can't live inside a `.venv`. The one thing that
*can* be venv-managed — the installer script's own interpreter — is handled by `uv run`'s
per-script ephemeral environment (see the `# /// script` block at the top of
`setup_toolchain.py`), which is why there's no `pyproject.toml`/`uv sync` step here at all:
the script has zero extra dependencies, so `uv run` alone is the complete, single-command
setup path. The source trees and build artifacts live in `--toolchain-dir` instead
(`~/pico-toolchain` by default) — deliberately outside this git repo, matching how
`build-*.sh` already expects a sibling MicroPython tree today (see the root README).

## Not yet covered

This installs the generic MicroPython/pico-sdk/picotool/cross-compiler toolchain (plus the Unix
port) and proves it builds, cross-compiles, and runs real Python. It does **not** yet wire up
`build-*.sh`'s hardcoded `/home/nico/rpi_pico/...` paths or the `py-include` symlink this
project's own firmware builds expect — that's the next step (see BACKLOG.md). The Unix port build
itself **is** wired into the actual test suite now (`scripts/test.sh` runs `setup` automatically
the first time it needs the interpreter, see "Code quality tooling" in the root README and
BACKLOG.md's "Self-contained venv via uv") — the remaining gap is the RP2040 firmware build, not
the Unix port.

## CI perspective

A CI pipeline now exists (`.github/workflows/ci.yml`, GitHub Actions — this repo is GitHub-hosted,
despite some older BACKLOG.md text still saying "GitLab"), with two jobs: `lint-and-typecheck`
(ruff/mypy) and `unit-tests`, which runs `scripts/test.sh` — building the toolchain (including the
Unix port) via plain `setup` on a cache miss (keyed on `toolchain/versions.toml` in `ci.yml`) and
reusing the cached `--toolchain-dir` on a hit. It does **not** yet include a real RP2040
firmware-build stage. `test` (the offline re-verification subcommand) is still written with that
eventual stage in mind (see BACKLOG.md's "Final-goal requirements for the refactor"): a `setup`
job would provision (or restore a cache of) `--toolchain-dir` once, and a `test` job would run
against it as the actual gate — offline, fast, and not dependent on GitHub/apt reachability at
gate time. The `unit-tests` job actually running today already follows this same
provision-then-cache shape, just using `setup` directly rather than a separate `setup`/`test`
split (there's nothing to re-verify offline yet beyond what the test suite itself already
exercises). Nothing about `setup`/`test` assumes a specific CI system; they're plain script
invocations with a clean exit code, so either would drop into a different pipeline without
changes if this repo ever moved off GitHub Actions.
