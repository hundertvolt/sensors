# Build environment installer

Single-command setup/update for the MicroPython RP2040/Pico W firmware build toolchain:
MicroPython itself, a matching `pico-sdk` (for building `picotool`), a version-matched
`picotool`, and the ARM cross-compiler.

## Usage

There are two subcommands, `setup` and `test`. `setup` is the default if you omit it (so
existing invocations without a subcommand keep working):

```sh
uv run toolchain/setup_toolchain.py                              # = setup: install/update per versions.toml
uv run toolchain/setup_toolchain.py --latest                      # pin + install newest stable MicroPython
uv run toolchain/setup_toolchain.py --micropython-ref v1.26.1     # build a specific ref instead

uv run toolchain/setup_toolchain.py test                          # re-verify an existing install, offline
```

No `pip install`/venv setup needed by hand — `uv run` provisions an ephemeral, cached
interpreter for the script itself (see "Why not a full venv" below). Re-running `setup`
against an existing install is also how updates work: it fetches, checks out whatever ref
is now pinned, and rebuilds only what changed.

`test` is deliberately separate from `setup`: it never touches apt or git remotes, it just
rebuilds the standard firmware image and `mpy-cross` from whatever is already checked out at
`--toolchain-dir` and re-runs the same three checks. That makes it fast (~30s vs. minutes for a
full `setup`), fully offline/reproducible, and the natural shape for a CI step later: a `setup`
run (or a restored cache of its `--toolchain-dir`) provisions the toolchain once, and `test` is
the repeatable gate that checks it still builds cleanly — see "Not yet covered" below. Run it
against a `--toolchain-dir` with no toolchain installed yet and it fails immediately with a clear
message telling you to run `setup` first, rather than a confusing build error.

Requires `sudo` (for `apt-get install` and `picotool`'s `make install`), outbound network access
to GitHub and the distro package mirrors, and `uv` itself already installed (`pip install uv`, or
the official `curl -LsSf https://astral.sh/uv/install.sh | sh` installer).

The `apt-get install` step needs Ubuntu's `universe` component enabled — the default on every
official Ubuntu image, so this only matters if you're starting from a deliberately minimal base
(e.g. a bare `debootstrap`-built rootfs, which enables only `main` unless told otherwise);
`gcc-arm-none-eabi`, `libnewlib-arm-none-eabi`, and `libstdc++-arm-none-eabi-newlib` all live in
`universe`.

## What gets pinned, and how

Only the MicroPython ref is pinned by hand, in `versions.toml`. Everything else is derived
automatically each run:

- **pico-sdk**: read directly from MicroPython's own `lib/pico-sdk` git submodule pin at the
  chosen ref — this is exactly the pico-sdk version the firmware actually compiles against,
  so it can never drift out of sync with the MicroPython ref.
- **picotool**: picotool enforces a matching major.minor version against the pico-sdk it's
  built with (a hard requirement since pico-sdk 2.0.0 — a mismatch fails with "Incompatible
  picotool installation found"). The script resolves the derived pico-sdk commit to its
  nearest tag, takes the major.minor, and picks the newest picotool tag sharing it.
- **ARM cross-compiler**: installed from the distro's `gcc-arm-none-eabi` package (currently
  13.2.rel1 on Ubuntu noble) rather than a separately-pinned version — this is the "fitting"
  version in the sense of being a known-working, reproducibly-installable toolchain for
  pico-sdk 2.x, not a hand-tracked pin like the other three.

To move to a new MicroPython release: edit `versions.toml`'s `ref` (or pass `--latest`) and
re-run. Everything downstream re-derives and rebuilds as needed.

## Directory layout

```
<toolchain-dir>/          default: $PICO_TOOLCHAIN_DIR or ~/pico-toolchain
  micropython/             full clone, checked out at the pinned ref
  pico-sdk/                full clone, checked out at the ref MicroPython pins
  picotool/                full clone, checked out at the derived matching tag; built + `sudo make install`ed
```

Full (non-shallow) clones are used deliberately, not just for the initial install — shallow
clones make the *update* path (fetch + checkout an arbitrary new ref) unreliable, and update
is a first-class requirement here, not an afterthought.

## Verification

Every run re-verifies the environment end-to-end before reporting success:

1. A standard, unchanged firmware image builds for the target board (default `RPI_PICO_W`)
   with no compiler errors or warnings.
2. `mpy-cross` (the cross-compiler) builds cleanly.
3. `mpy-cross` successfully cross-compiles a throwaway sample `.py` file.

Any failure aborts with a non-zero exit and the build log leading up to it.

**Verified end-to-end on a genuinely clean Ubuntu 24.04 system**: a `debootstrap`-built `noble`
chroot with nothing preinstalled beyond the minimal base (no build tools, no `git`/`curl`/`sudo`,
no `uv`, no apt cache beyond `main`) — the script installed every system dependency itself
(after enabling `universe`, see "Usage" above) and passed all three checks in ~3 minutes, for
both the latest stable MicroPython release and the currently-deployed `v1.26.1` pin. The
in-place update path (existing `v1.26.1` install → re-run targeting the latest release) was also
verified: existing clones are fetched and re-checked-out rather than re-cloned, the derived
pico-sdk/picotool versions bump automatically, and only the affected pieces rebuild. `test` was
verified separately against a `setup`-provisioned install: it completed in ~30s (vs. minutes for
`setup`), touched no network or apt state, and passed all three checks.

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

This installs the generic MicroPython/pico-sdk/picotool/cross-compiler toolchain and proves
it builds and cross-compiles. It does **not** yet wire up `build-*.sh`'s hardcoded
`/home/nico/rpi_pico/...` paths or the `py-include` symlink this project's own firmware
builds expect — that's the next step (see BACKLOG.md).

## CI perspective

`test` is written with an eventual CI stage in mind (see BACKLOG.md's "Final-goal requirements
for the refactor" — a real firmware build as a CI pipeline stage), even though no CI pipeline
exists yet for this repo. The intended shape once that's built: a `setup` job provisions (or
restores a cache of) `--toolchain-dir`, and a `test` job runs against it as the actual gate —
offline, fast, and not dependent on GitHub/apt reachability at gate time. Nothing about `test`
today assumes a specific CI system; it's just a plain script invocation with a clean exit code,
so it should drop into whatever pipeline (GitHub Actions, GitLab CI, etc.) is set up later
without changes.
