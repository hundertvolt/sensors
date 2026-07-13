# Build environment installer

Single-command setup/update for the MicroPython RP2040/Pico W firmware build toolchain:
MicroPython itself, a matching `pico-sdk` (for building `picotool`), a version-matched
`picotool`, and the ARM cross-compiler.

## Usage

```sh
uv run toolchain/setup_toolchain.py                              # install/update per versions.toml
uv run toolchain/setup_toolchain.py --latest                      # pin + install newest stable MicroPython
uv run toolchain/setup_toolchain.py --micropython-ref v1.26.1     # build a specific ref instead
```

No `pip install`/venv setup needed by hand — `uv run` provisions an ephemeral, cached
interpreter for the script itself (see "Why not a full venv" below). Re-running the same
command is also how you update an existing install: it fetches, checks out whatever ref
is now pinned, and rebuilds only what changed.

Requires `sudo` (for `apt-get install` and `picotool`'s `make install`) and outbound network
access to GitHub and the distro package mirrors.

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
