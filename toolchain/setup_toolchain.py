#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""
Single-command installer/updater for the MicroPython RP2040/Pico W firmware build
environment (MicroPython + matching pico-sdk + matching picotool + ARM cross-toolchain), plus
a host-side MicroPython Unix port build used for running tests under the real interpreter
later (see BACKLOG.md's "Self-contained venv via uv" — this is the "setup script that builds/
installs the MicroPython Unix port interpreter" it describes).

Usage (from anywhere, via uv — no venv/pip setup needed):

    uv run toolchain/setup_toolchain.py
    uv run toolchain/setup_toolchain.py --latest          # bump to newest stable MicroPython
    uv run toolchain/setup_toolchain.py --micropython-ref v1.26.1
    uv run toolchain/setup_toolchain.py --clean           # wipe build dirs, then rebuild from scratch
    uv run toolchain/setup_toolchain.py test              # re-verify an existing install, offline

Re-running this same command against an existing toolchain directory is how updates work:
it fetches, checks out whatever ref is now pinned, re-derives the matching pico-sdk/picotool
versions, and rebuilds only what's needed.

Two design decisions shape most of the code below, both explained at length in
toolchain/README.md's "How it works":
  - Only the MicroPython ref is a hand-picked version (see versions.toml). The pico-sdk and
    picotool versions are *derived* from it (derive_pico_sdk_commit / derive_picotool_ref)
    instead of being tracked as separate pins that could quietly drift out of sync.
  - Every build subprocess runs in an explicitly constructed environment (build_env /
    network_env), never the caller's raw shell — so a leftover CFLAGS, a shadowing ~/bin/cmake,
    or some other locally-installed thing can't silently change what gets built.

Verification (run_verification_sequence()) proves the toolchain actually works, rather than just
asserting the pieces are probably fine: it freezes one small test module as bytecode into both
the Unix port and the RP2 firmware, then imports it inside the Unix port and checks the result —
proof that the whole freeze pipeline (mpy-cross -> FROZEN_MANIFEST -> firmware) works end to end,
not just that mpy-cross alone compiles something. See its docstring for the exact step order and
toolchain/README.md's "Verification" section for the rationale.

See toolchain/README.md for the full picture (what this does and does not cover).
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

MICROPYTHON_URL = "https://github.com/micropython/micropython.git"
PICO_SDK_URL = "https://github.com/raspberrypi/pico-sdk.git"
PICOTOOL_URL = "https://github.com/raspberrypi/picotool.git"

# The single module used throughout the frozen-bytecode verification chain (see
# run_verification_sequence()): one source of truth compiled/frozen/imported everywhere, rather
# than separate throwaway samples for "does mpy-cross work" vs. "does freezing work". Runs real
# checks on import (arithmetic, a comprehension, exception handling, a stdlib module) and exposes
# RESULT so callers can prove the import produced an actual value, not just that it didn't crash.
FROZEN_VERIFY_MODULE = "frozen_verify_test"
FROZEN_VERIFY_PY = '''\
import sys
import json

assert 2 + 3 == 5
assert "-".join(str(x) for x in range(3)) == "0-1-2"
assert json.dumps({"a": 1}) == '{"a": 1}'

try:
    1 / 0
except ZeroDivisionError:
    pass
else:
    raise SystemExit("expected ZeroDivisionError")

RESULT = "FROZEN_VERIFY_OK: " + sys.implementation.name
'''


class SetupError(RuntimeError):
    pass


def log(msg: str) -> None:
    print(f"\n== {msg}", flush=True)


# Every subprocess this script runs gets this fixed, deterministic PATH and a small
# allowlist of ambient variables — never the caller's raw environment. Deliberately an
# allowlist, not a blocklist: CC/CXX/CFLAGS/LDFLAGS/MAKEFLAGS, CMAKE_*, PICO_SDK_PATH/
# PICO_BOARD, PYTHONPATH, and anything else not listed here are all dropped, and a fixed
# PATH means a shadowing binary earlier in the caller's PATH (a stray ~/bin/cmake, a
# different gcc-arm-none-eabi build, an old picotool) can never be picked up instead of
# the one this script itself just installed. Nothing here is trusted from the caller's
# shell/profile to silently change what gets built, with what flags, or using what tools.
BUILD_ENV_ALLOWLIST = ("HOME", "USER", "LOGNAME", "TERM", "TMPDIR")
BUILD_ENV_PATH = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

# LANG/LC_ALL are deliberately *not* in the allowlist above and forced to C.UTF-8 instead of
# passed through: build_firmware()/build_mpy_cross() detect failures by grepping build output
# for the literal English "error:"/"warning:" (gcc/make don't offer a machine-readable
# success/failure signal beyond exit code + freeform text). GCC and binutils *can* emit
# translated diagnostics via gettext catalogs on a system where the caller's locale has one
# installed — inheriting the caller's LANG/LC_ALL would risk a real warning silently not
# matching those English-only patterns. C.UTF-8 keeps UTF-8 text handling (unlike plain "C")
# while guaranteeing English tool output every time, regardless of the caller's own locale.
BUILD_ENV_LOCALE = "C.UTF-8"

# On top of the base allowlist, git/apt calls (and the rp2 "submodules" Makefile target,
# which does both a git fetch *and* an internal cmake configure pass) also need whatever
# proxy/CA configuration this machine's network actually requires — explicitly named
# here rather than inherited wholesale, so it's still only ever these specific variables.
NETWORK_ENV_EXTRA = (
    "HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy",
    "NO_PROXY", "no_proxy", "ALL_PROXY", "all_proxy",
    "SSL_CERT_FILE", "GIT_SSL_CAINFO", "CURL_CA_BUNDLE", "REQUESTS_CA_BUNDLE",
)


def build_env() -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if k in BUILD_ENV_ALLOWLIST}
    env["PATH"] = BUILD_ENV_PATH
    env["LANG"] = BUILD_ENV_LOCALE
    env["LC_ALL"] = BUILD_ENV_LOCALE
    return env


def network_env() -> dict[str, str]:
    env = build_env()
    for key in NETWORK_ENV_EXTRA:
        if key in os.environ:
            env[key] = os.environ[key]
    return env


def run(cmd: list[str], cwd: Path | None = None, check: bool = True, env: dict[str, str] | None = None) -> str:
    print(f"$ {' '.join(cmd)}" + (f"   (cwd={cwd})" if cwd else ""), flush=True)
    result = subprocess.run(
        cmd, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
    )
    print(result.stdout)
    if check and result.returncode != 0:
        raise SetupError(f"command failed (exit {result.returncode}): {' '.join(cmd)}")
    return result.stdout


def load_versions(path: Path) -> dict:
    with path.open("rb") as f:
        return tomllib.load(f)


def write_micropython_ref(path: Path, ref: str) -> None:
    text = path.read_text()
    new_text = re.sub(r'(?m)^ref = ".*"$', f'ref = "{ref}"', text, count=1)
    path.write_text(new_text)


def ensure_apt_packages(packages: list[str], skip: bool) -> None:
    if skip:
        log("Skipping apt package install (--skip-apt)")
        return
    log("Installing/checking system packages")
    env = network_env()
    # Non-fatal: unrelated third-party sources some environments have configured (PPAs etc.)
    # may be blocked or broken without affecting the main archive packages we actually need.
    run(["sudo", "apt-get", "update"], check=False, env=env)
    run(
        ["sudo", "env", "DEBIAN_FRONTEND=noninteractive", "apt-get", "install", "-y",
         "--no-install-recommends", *packages],
        env=env,
    )


def is_sha(ref: str) -> bool:
    """True for a raw commit hash (e.g. a pico-sdk pin read out of a git tree) as opposed to
    a tag/branch name (e.g. "v1.28.0"). The two need different checkout handling below: tags
    are always fetched by `git fetch --tags`, but an arbitrary commit might not be reachable
    that way and needs fetching directly by its hash instead."""
    return bool(re.fullmatch(r"[0-9a-f]{7,40}", ref))


def clone_full(url: str, dest: Path) -> None:
    # Deliberately a full clone, not `--depth 1`: a shallow clone only has one ref's history,
    # which breaks the *update* path (fetch + checkout some other arbitrary ref later) — and
    # updating in place, not just installing once, is a first-class requirement here.
    dest.parent.mkdir(parents=True, exist_ok=True)
    run(["git", "clone", "--quiet", url, str(dest)], env=network_env())


def checkout_ref(repo: Path, ref: str) -> None:
    env = network_env()
    run(["git", "fetch", "--quiet", "--tags", "--force", "origin"], cwd=repo, env=env)
    if is_sha(ref):
        try:
            run(["git", "checkout", "--quiet", ref], cwd=repo, env=env)
            return
        except SetupError:
            # The commit wasn't already present locally (e.g. a pico-sdk pin from a
            # MicroPython ref we haven't built before) — fetch it directly by hash.
            pass
        run(["git", "fetch", "--quiet", "origin", ref], cwd=repo, env=env)
        run(["git", "checkout", "--quiet", "FETCH_HEAD"], cwd=repo, env=env)
    else:
        run(["git", "checkout", "--quiet", ref], cwd=repo, env=env)


def ensure_repo_at_ref(url: str, dest: Path, ref: str) -> None:
    """Clone-or-update: the same call handles both "doesn't exist yet" (setup) and "already
    exists, may be pinned to something else" (update) — there's no separate update codepath."""
    if not dest.exists():
        log(f"Cloning {url} -> {dest}")
        clone_full(url, dest)
    else:
        log(f"Updating existing clone at {dest}")
    checkout_ref(dest, ref)


def derive_pico_sdk_commit(micropython_dir: Path, mpy_ref: str) -> str:
    """The pico-sdk version to use is never chosen independently — it's read straight out of
    MicroPython's own git submodule pin at lib/pico-sdk, which is exactly the pico-sdk commit
    the firmware actually compiles against. This is the mechanism that makes "only pin
    MicroPython" (see versions.toml) possible instead of tracking two version numbers by hand."""
    out = run(["git", "ls-tree", mpy_ref, "lib/pico-sdk"], cwd=micropython_dir, env=network_env())
    # format: "160000 commit <sha>\tlib/pico-sdk"
    fields = out.split()
    if len(fields) < 3:
        raise SetupError(f"could not find lib/pico-sdk submodule pin for {mpy_ref}")
    return fields[2]


def derive_picotool_ref(pico_sdk_dir: Path, pico_sdk_commit: str) -> str:
    """picotool only needs to match pico-sdk's major.minor (not its exact commit) — but that
    match is enforced at build time (a mismatch fails with "Incompatible picotool installation
    found" since pico-sdk 2.0.0), so getting it wrong isn't a style nitpick, it's a build
    failure. Resolve the derived pico-sdk commit to its nearest tag, then pick the newest
    picotool tag sharing that major.minor."""
    described = run(["git", "describe", "--tags", pico_sdk_commit], cwd=pico_sdk_dir, env=network_env()).strip()
    match = re.match(r"^(\d+)\.(\d+)\.", described)
    if not match:
        raise SetupError(f"could not parse major.minor from pico-sdk tag {described!r}")
    major, minor = match.group(1), match.group(2)

    out = run(["git", "ls-remote", "--tags", PICOTOOL_URL], env=network_env())
    candidates = []
    for line in out.splitlines():
        m = re.search(rf"refs/tags/({major}\.{minor}\.\d+)$", line)
        if m:
            candidates.append(m.group(1))
    if not candidates:
        raise SetupError(f"no picotool tag found matching pico-sdk major.minor {major}.{minor}")
    candidates.sort(key=lambda v: tuple(int(x) for x in v.split(".")))
    return candidates[-1]


PICOTOOL_INSTALL_PREFIX = "/usr/local"


def build_and_install_picotool(picotool_dir: Path, pico_sdk_dir: Path, jobs: int) -> Path:
    log(f"Building and installing picotool (against pico-sdk at {pico_sdk_dir})")
    build_dir = picotool_dir / "build"
    if build_dir.exists():
        shutil.rmtree(build_dir)
    build_dir.mkdir()
    env = build_env()
    # Pinned explicitly (not left to whatever cmake's own default resolves to) so the
    # install location is deterministic regardless of ambient cmake config/env state.
    run(
        ["cmake", "..", f"-DPICO_SDK_PATH={pico_sdk_dir}", f"-DCMAKE_INSTALL_PREFIX={PICOTOOL_INSTALL_PREFIX}"],
        cwd=build_dir,
        env=env,
    )
    run(["make", f"-j{jobs}"], cwd=build_dir, env=env)
    run(["sudo", "make", "install"], cwd=build_dir, env=env)
    picotool_binary = Path(PICOTOOL_INSTALL_PREFIX) / "bin" / "picotool"
    if not picotool_binary.exists():
        raise SetupError(f"picotool install did not produce {picotool_binary}")
    # Invoked by absolute path, not a bare "picotool" PATH lookup — a stray picotool
    # installed elsewhere on PATH (a different version, an unrelated package) must not
    # be able to shadow the one just built for this pico-sdk.
    version_out = run([str(picotool_binary), "version"], env=env)
    print(f"Installed: {version_out.strip()}")
    return picotool_binary


def build_mpy_cross(micropython_dir: Path, jobs: int) -> Path:
    log("Building mpy-cross")
    mpy_cross_dir = micropython_dir / "mpy-cross"
    env = build_env()
    out = run(["make", f"-j{jobs}"], cwd=mpy_cross_dir, env=env)
    if re.search(r"\bwarning:", out, re.IGNORECASE):
        raise SetupError("mpy-cross build produced warnings (see log above)")
    binary = mpy_cross_dir / "build" / "mpy-cross"
    if not binary.exists():
        raise SetupError("mpy-cross build did not produce build/mpy-cross")
    version_out = run([str(binary), "--version"], env=env)
    print(f"Built: {version_out.strip()}")
    return binary


def fetch_rp2_submodules(micropython_dir: Path, board: str) -> None:
    log(f"Fetching submodules needed for BOARD={board}")
    rp2_dir = micropython_dir / "ports" / "rp2"
    # Needs network_env(), not build_env(): this Makefile target both fetches submodules
    # over git and runs a preliminary cmake configure pass, so it needs the deterministic
    # PATH *and* real network/proxy access at the same time.
    run(["make", f"BOARD={board}", "submodules"], cwd=rp2_dir, env=network_env())


def fetch_unix_submodules(micropython_dir: Path) -> None:
    log("Fetching submodules needed for the Unix port")
    unix_dir = micropython_dir / "ports" / "unix"
    # Unlike ports/rp2's "submodules" target, this one is pure git (axtls/berkeley-db/libffi
    # submodule checkouts) with no internal cmake configure pass - network_env() is still the
    # right choice (it fetches over git), just for a simpler reason than rp2's.
    run(["make", "submodules"], cwd=unix_dir, env=network_env())


def build_firmware(micropython_dir: Path, board: str, jobs: int, frozen_manifest: Path | None = None) -> Path:
    """Builds the RP2 firmware. Pass frozen_manifest (an absolute path to a manifest.py written
    by write_freeze_manifest()) to freeze an extra module in via FROZEN_MANIFEST=, which takes
    precedence over the board's own default manifest; omit it for a vanilla build."""
    rp2_dir = micropython_dir / "ports" / "rp2"
    label = "with the frozen verification module (build-only check)" if frozen_manifest else "standard, unchanged"
    log(f"Building firmware for BOARD={board} ({label})")
    build_dir = rp2_dir / f"build-{board}"
    if build_dir.exists():
        shutil.rmtree(build_dir)
    make_cmd = ["make", f"BOARD={board}", f"-j{jobs}"]
    if frozen_manifest is not None:
        make_cmd.append(f"FROZEN_MANIFEST={frozen_manifest}")
    out = run(make_cmd, cwd=rp2_dir, env=build_env())
    if re.search(r"\berror:", out, re.IGNORECASE):
        raise SetupError("firmware build reported an error (see log above)")
    if re.search(r"\bwarning:", out, re.IGNORECASE):
        raise SetupError("firmware build produced warnings (see log above)")

    uf2 = build_dir / "firmware.uf2"
    if not uf2.exists():
        raise SetupError(f"firmware build did not produce {uf2}")
    return uf2


def build_unix_port(micropython_dir: Path, jobs: int, frozen_manifest: Path | None = None) -> Path:
    """Builds the "standard" variant (the default, and the one with the most complete feature
    set) - see ports/unix/README.md. Requires mpy-cross to already be built (build_mpy_cross()
    must run first); the Makefile also depends on it directly, but re-checking a build that's
    already current is a no-op, not wasted work. Pass frozen_manifest the same way as
    build_firmware() above; omit it for a vanilla build."""
    label = "with the frozen verification module" if frozen_manifest else "standard, unchanged"
    log(f"Building the MicroPython Unix port ({label})")
    unix_dir = micropython_dir / "ports" / "unix"
    build_dir = unix_dir / "build-standard"
    if build_dir.exists():
        shutil.rmtree(build_dir)
    make_cmd = ["make", f"-j{jobs}"]
    if frozen_manifest is not None:
        make_cmd.append(f"FROZEN_MANIFEST={frozen_manifest}")
    out = run(make_cmd, cwd=unix_dir, env=build_env())
    if re.search(r"\berror:", out, re.IGNORECASE):
        raise SetupError("Unix port build reported an error (see log above)")
    if re.search(r"\bwarning:", out, re.IGNORECASE):
        raise SetupError("Unix port build produced warnings (see log above)")

    binary = build_dir / "micropython"
    if not binary.exists():
        raise SetupError(f"Unix port build did not produce {binary}")
    version_out = run([str(binary), "-c", "import sys; print(sys.implementation)"], env=build_env())
    print(f"Built: {version_out.strip()}")
    return binary


def clean_build_dirs(toolchain_dir: Path, board: str) -> None:
    """Wipe every build-artifact directory without touching the git clones themselves, so the
    setup that follows rebuilds everything from scratch -- as if freshly installed -- without
    re-cloning multi-gigabyte source trees that haven't actually changed. build_firmware(),
    build_unix_port(), and build_and_install_picotool() already do this for their own build dirs
    on every run (that's why the firmware/Unix-port steps always fully recompile while
    mpy-cross's build/ is normally left alone and rebuilds incrementally); this is the same
    action made available on demand and extended to mpy-cross's build/ too, the one directory
    nothing else ever clears."""
    log("Cleaning all build-artifact directories")
    targets = [
        toolchain_dir / "picotool" / "build",
        toolchain_dir / "micropython" / "mpy-cross" / "build",
        toolchain_dir / "micropython" / "ports" / "rp2" / f"build-{board}",
        toolchain_dir / "micropython" / "ports" / "unix" / "build-standard",
    ]
    for target in targets:
        if target.exists():
            print(f"Removing {target}")
            shutil.rmtree(target)
        else:
            print(f"(nothing to clean at {target})")


# The frozen test module lives in its own subdirectory of the tempdir created by
# run_verification_sequence(), never directly alongside the generated manifest.py files - see
# write_freeze_manifest() for why that separation matters.
FROZEN_MODULE_SUBDIR = "frozen_module"


def write_frozen_verify_test(test_dir: Path) -> Path:
    """Step 1 of run_verification_sequence(): the one .py file cross-compiled/frozen/imported at
    every later step - see FROZEN_VERIFY_PY."""
    module_dir = test_dir / FROZEN_MODULE_SUBDIR
    module_dir.mkdir()
    test_file = module_dir / f"{FROZEN_VERIFY_MODULE}.py"
    test_file.write_text(FROZEN_VERIFY_PY)
    return test_file


def cross_compile_frozen_verify_test(mpy_cross_binary: Path, test_file: Path) -> Path:
    """Step 3: cross-compiles the test file standalone (invoking mpy-cross directly, not via a
    manifest's freeze()) to prove mpy-cross itself works, independently of the freeze/build
    pipeline exercised by steps 4 and 6."""
    log("Cross-compiling the verification test file to prove mpy-cross works standalone")
    run([str(mpy_cross_binary), str(test_file)], env=build_env())
    compiled = test_file.with_suffix(".mpy")
    if not compiled.exists() or compiled.stat().st_size == 0:
        raise SetupError(f"mpy-cross did not produce a non-empty {compiled.name}")
    print(f"Produced {compiled.name} ({compiled.stat().st_size} bytes)")
    return compiled


def write_freeze_manifest(manifest_path: Path, port_manifest_relpath: str) -> None:
    """Mirrors this repo's own manifest convention (python/Manifest/manifest.py): include the
    port's normal manifest, then freeze FROZEN_MODULE_SUBDIR. freeze() resolves its argument
    relative to *this* manifest file's own directory - manifest_path is always written as a
    sibling of FROZEN_MODULE_SUBDIR (never inside it), so freeze() only ever picks up the one
    intended test module, never the manifest.py files generated alongside it (both this one and
    the other port's, which also lives in the same tempdir - see run_verification_sequence())."""
    manifest_path.write_text(
        f'include("$(PORT_DIR)/{port_manifest_relpath}")\nfreeze("{FROZEN_MODULE_SUBDIR}")\n'
    )


def run_frozen_verify_on_unix(unix_binary: Path) -> None:
    """Step 5: imports the frozen module *by name*, with no source .py file anywhere on disk for
    the interpreter to find - the only way this can succeed is if the module was actually baked
    into the binary as frozen bytecode, not merely compiled and left on disk somewhere."""
    log("Importing the frozen verification module inside the Unix port and checking its result")
    out = run(
        [str(unix_binary), "-c", f"import {FROZEN_VERIFY_MODULE}; print({FROZEN_VERIFY_MODULE}.RESULT)"],
        env=build_env(),
    )
    if "FROZEN_VERIFY_OK" not in out:
        raise SetupError("frozen verification module did not produce the expected result (see log above)")
    print(out.strip())


def clean_frozen_verification_build_dirs(toolchain_dir: Path, board: str) -> None:
    """Step 7: removes exactly the two build outputs the frozen-bytecode verification chain
    (steps 4-6) leaves behind - the Unix port and RP2 firmware built with the frozen test module.
    Neither is kept: the RP2 build is never repeated afterward (see run_verification_sequence()'s
    docstring for why a build-only check is sufficient), and the Unix port gets rebuilt vanilla
    in step 8. Deliberately does not touch mpy-cross/build or picotool - both are real toolchain
    deliverables needed for actual project work later, not verification-only artifacts."""
    log("Cleaning up the frozen-bytecode verification build artifacts")
    targets = [
        toolchain_dir / "micropython" / "ports" / "rp2" / f"build-{board}",
        toolchain_dir / "micropython" / "ports" / "unix" / "build-standard",
    ]
    for target in targets:
        if target.exists():
            print(f"Removing {target}")
            shutil.rmtree(target)
        else:
            print(f"(nothing to clean at {target})")


def run_verification_sequence(micropython_dir: Path, toolchain_dir: Path, board: str, jobs: int) -> tuple[Path, Path]:
    """The frozen-bytecode verification chain described in toolchain/README.md's "Verification" -
    each step must succeed before the next starts (a SetupError from any run()/build_*() call
    aborts the whole sequence, so this is enforced by the exception propagating, not by checking
    a return code by hand):

      1. create a test .py file
      2. build mpy-cross
      3. cross-compile the test file standalone (proves mpy-cross itself works)
      4. build the Unix port with the test file frozen in
      5. import the frozen module inside the Unix port and check its result
         -> mpy-cross and the Unix port build are now both verified
      6. build the RP2 port with the same test file frozen in (build-only: there's no RP2
         hardware here to run it on, so a clean build is the whole check)
      7. clean up everything steps 4-6 left behind
      8. build a vanilla (non-frozen) Unix port - this becomes the standing test rig for
         everything that follows (see BACKLOG.md's "Self-contained venv via uv")

    Deliberately does not rebuild a vanilla RP2 firmware.uf2 afterward: nothing in this project
    is ever actually flashed from a "vanilla, no project code" image, so step 6's from-scratch,
    zero-errors/zero-warnings build with the frozen module already *is* the real proof that the
    ARM toolchain/pico-sdk/picotool combination works - freezing extra bytecode only adds to a
    build, it can't make an otherwise-broken one succeed, so this result is a strict superset of
    what a vanilla build would have proven anyway.
    """
    with tempfile.TemporaryDirectory() as tmp:
        test_dir = Path(tmp)

        test_file = write_frozen_verify_test(test_dir)
        mpy_cross_binary = build_mpy_cross(micropython_dir, jobs)
        cross_compile_frozen_verify_test(mpy_cross_binary, test_file)

        unix_manifest = test_dir / "manifest_unix.py"
        write_freeze_manifest(unix_manifest, "variants/manifest.py")
        unix_binary = build_unix_port(micropython_dir, jobs, frozen_manifest=unix_manifest)
        run_frozen_verify_on_unix(unix_binary)

        rp2_manifest = test_dir / "manifest_rp2.py"
        write_freeze_manifest(rp2_manifest, f"boards/{board}/manifest.py")
        build_firmware(micropython_dir, board, jobs, frozen_manifest=rp2_manifest)
        # test_dir (the test module + both manifests) is removed automatically once this
        # "with" block exits - nothing further to clean up for those.

    clean_frozen_verification_build_dirs(toolchain_dir, board)

    unix_binary = build_unix_port(micropython_dir, jobs)  # vanilla rebuild: the real test rig

    return mpy_cross_binary, unix_binary


def latest_stable_micropython_ref() -> str:
    """Backs --latest: the only version this whole script tracks by hand is the MicroPython
    ref (versions.toml), so "upgrade everything" reduces to "find the newest MicroPython tag,
    write it back to versions.toml, and let derive_pico_sdk_commit/derive_picotool_ref do the
    rest on the next run"."""
    out = run(["git", "ls-remote", "--tags", MICROPYTHON_URL], env=network_env())
    candidates = []
    for line in out.splitlines():
        m = re.search(r"refs/tags/(v\d+\.\d+(?:\.\d+)?)$", line)
        if m:
            tag = m.group(1)
            parts = tuple(int(x) for x in tag[1:].split("."))
            candidates.append((parts, tag))
    if not candidates:
        raise SetupError("could not find any stable MicroPython release tags")
    candidates.sort()
    return candidates[-1][1]


def print_verification_summary(board: str, mpy_cross_binary: Path, unix_binary: Path) -> int:
    log("All verification checks passed")
    print(f"  1-3. mpy-cross built and cross-compiled the verification test file standalone: {mpy_cross_binary}")
    print("  4-5. Unix port built with the test file frozen in, and the frozen module ran with the expected result")
    print(f"  6. {board} firmware built with the same test file frozen in (build-only, zero errors/warnings)")
    print("  7. Frozen-bytecode verification build artifacts cleaned up")
    print(f"  8. Vanilla Unix port rebuilt as the standing test rig: {unix_binary}")
    return 0


def run_setup(args: argparse.Namespace, versions_path: Path, versions: dict) -> int:
    """Install or update. The steps below are exactly "How it works" in toolchain/README.md:
    pin MicroPython -> derive pico-sdk -> derive picotool -> install the ARM toolchain -> build
    everything in an isolated environment -> verify. ensure_repo_at_ref() doubles as the update
    mechanism (clone if missing, fetch+checkout if not), so there's no separate "update" branch
    of this function — re-running it against an existing --toolchain-dir *is* the update."""
    mpy_ref = args.micropython_ref
    if args.latest:
        mpy_ref = latest_stable_micropython_ref()
        log(f"--latest resolved to MicroPython {mpy_ref}; updating {versions_path}")
        write_micropython_ref(versions_path, mpy_ref)
    if mpy_ref is None:
        mpy_ref = versions["micropython"]["ref"]

    board = versions["toolchain"]["board"]
    apt_packages = versions["toolchain"]["apt_packages"]

    toolchain_dir = args.toolchain_dir.expanduser().resolve()
    toolchain_dir.mkdir(parents=True, exist_ok=True)
    micropython_dir = toolchain_dir / "micropython"
    pico_sdk_dir = toolchain_dir / "pico-sdk"
    picotool_dir = toolchain_dir / "picotool"

    print(f"Toolchain directory: {toolchain_dir}")
    print(f"MicroPython ref: {mpy_ref}")
    print(f"Board: {board}")

    if args.clean:
        clean_build_dirs(toolchain_dir, board)

    ensure_apt_packages(apt_packages, args.skip_apt)

    log(f"Preparing MicroPython at {mpy_ref}")
    ensure_repo_at_ref(MICROPYTHON_URL, micropython_dir, mpy_ref)

    pico_sdk_commit = derive_pico_sdk_commit(micropython_dir, mpy_ref)
    log(f"MicroPython {mpy_ref} pins pico-sdk commit {pico_sdk_commit}")
    ensure_repo_at_ref(PICO_SDK_URL, pico_sdk_dir, pico_sdk_commit)
    run(["git", "submodule", "update", "--init", "lib/mbedtls"], cwd=pico_sdk_dir, env=network_env())

    picotool_ref = derive_picotool_ref(pico_sdk_dir, pico_sdk_commit)
    log(f"Matching picotool tag: {picotool_ref}")
    ensure_repo_at_ref(PICOTOOL_URL, picotool_dir, picotool_ref)

    build_and_install_picotool(picotool_dir, pico_sdk_dir, args.jobs)
    fetch_rp2_submodules(micropython_dir, board)
    fetch_unix_submodules(micropython_dir)

    mpy_cross_binary, unix_binary = run_verification_sequence(micropython_dir, toolchain_dir, board, args.jobs)

    return print_verification_summary(board, mpy_cross_binary, unix_binary)


def run_test(args: argparse.Namespace, versions: dict) -> int:
    """Re-verify an existing install, offline: just run_verification_sequence() again against
    whatever is already checked out — see the module docstring and toolchain/README.md's "How it
    works" for why apt/git network access is never needed here."""
    board = versions["toolchain"]["board"]
    toolchain_dir = args.toolchain_dir.expanduser().resolve()
    micropython_dir = toolchain_dir / "micropython"
    rp2_dir = micropython_dir / "ports" / "rp2"

    if not (micropython_dir / "mpy-cross").is_dir() or not rp2_dir.is_dir():
        raise SetupError(
            f"no toolchain found at {toolchain_dir} — run `setup` first "
            f"(e.g. `uv run toolchain/setup_toolchain.py setup`)"
        )

    log(f"Testing existing toolchain at {toolchain_dir} (offline: no apt/git network access)")
    print(f"Board: {board}")

    # Deliberately does not touch apt, git remotes, or the pico-sdk/picotool derivation —
    # this re-verifies whatever is already checked out, so it's fast, reproducible, and
    # runnable offline. That's what makes it suitable as a standalone CI step later: `setup`
    # (or a restored cache of its --toolchain-dir) provisions the toolchain once, and `test`
    # is the repeatable gate that checks it still builds cleanly. Submodules are assumed
    # already fetched by a prior `setup` run.
    mpy_cross_binary, unix_binary = run_verification_sequence(micropython_dir, toolchain_dir, board, args.jobs)

    return print_verification_summary(board, mpy_cross_binary, unix_binary)


def main() -> int:
    toolchain_dir_default = Path(os.environ.get("PICO_TOOLCHAIN_DIR", Path.home() / "pico-toolchain"))

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--toolchain-dir",
        type=Path,
        default=toolchain_dir_default,
        help="Directory holding the micropython/pico-sdk/picotool source trees (default: $PICO_TOOLCHAIN_DIR or ~/pico-toolchain)",
    )
    common.add_argument("--jobs", type=int, default=os.cpu_count() or 4, help="Parallel make jobs")

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    subparsers = parser.add_subparsers(dest="command")

    setup_parser = subparsers.add_parser(
        "setup", parents=[common], help="Install or update the toolchain (default if no subcommand given)"
    )
    setup_parser.add_argument("--micropython-ref", help="Override the MicroPython tag/ref to build (default: from versions.toml)")
    setup_parser.add_argument("--latest", action="store_true", help="Detect the newest stable MicroPython release and pin versions.toml to it")
    setup_parser.add_argument("--skip-apt", action="store_true", help="Skip installing system/apt packages")
    setup_parser.add_argument(
        "--clean",
        action="store_true",
        help="Wipe all build-artifact directories (picotool/build, mpy-cross/build, ports/rp2/build-<board>, "
        "ports/unix/build-standard) before building, without re-cloning the git sources -- brings the "
        "toolchain back to a from-scratch build state",
    )

    subparsers.add_parser(
        "test",
        parents=[common],
        help="Re-verify an already-installed toolchain with no network/apt access — the CI-friendly check",
    )

    # Backward/convenience compat: `setup_toolchain.py [--some-setup-flag ...]` (no subcommand)
    # still means "setup", so existing invocations and muscle memory keep working.
    argv = sys.argv[1:]
    if argv and argv[0] not in ("setup", "test", "-h", "--help"):
        argv = ["setup", *argv]
    elif not argv:
        argv = ["setup"]
    args = parser.parse_args(argv)

    versions_path = Path(__file__).parent / "versions.toml"
    versions = load_versions(versions_path)

    if args.command == "test":
        return run_test(args, versions)
    return run_setup(args, versions_path, versions)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SetupError as exc:
        print(f"\nFAILED: {exc}", file=sys.stderr)
        sys.exit(1)
