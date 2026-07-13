#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""
Single-command installer/updater for the MicroPython RP2040/Pico W firmware build
environment (MicroPython + matching pico-sdk + matching picotool + ARM cross-toolchain).

Usage (from anywhere, via uv — no venv/pip setup needed):

    uv run toolchain/setup_toolchain.py
    uv run toolchain/setup_toolchain.py --latest          # bump to newest stable MicroPython
    uv run toolchain/setup_toolchain.py --micropython-ref v1.26.1
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

SAMPLE_PY = '''\
def add(a, b):
    return a + b


print(add(2, 3))
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
BUILD_ENV_ALLOWLIST = ("HOME", "USER", "LOGNAME", "LANG", "LC_ALL", "TERM", "TMPDIR")
BUILD_ENV_PATH = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

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


def build_firmware(micropython_dir: Path, board: str, jobs: int) -> Path:
    rp2_dir = micropython_dir / "ports" / "rp2"
    log(f"Building standard, unchanged firmware for BOARD={board}")
    build_dir = rp2_dir / f"build-{board}"
    if build_dir.exists():
        shutil.rmtree(build_dir)
    out = run(["make", f"BOARD={board}", f"-j{jobs}"], cwd=rp2_dir, env=build_env())
    if re.search(r"\berror:", out, re.IGNORECASE):
        raise SetupError("firmware build reported an error (see log above)")
    if re.search(r"\bwarning:", out, re.IGNORECASE):
        raise SetupError("firmware build produced warnings (see log above)")

    uf2 = build_dir / "firmware.uf2"
    if not uf2.exists():
        raise SetupError(f"firmware build did not produce {uf2}")
    return uf2


def cross_compile_sample(mpy_cross_binary: Path) -> None:
    log("Cross-compiling a sample .py file to verify mpy-cross works")
    with tempfile.TemporaryDirectory() as tmp:
        sample_py = Path(tmp) / "sample.py"
        sample_py.write_text(SAMPLE_PY)
        run([str(mpy_cross_binary), str(sample_py)], env=build_env())
        sample_mpy = Path(tmp) / "sample.mpy"
        if not sample_mpy.exists() or sample_mpy.stat().st_size == 0:
            raise SetupError("mpy-cross did not produce a non-empty sample.mpy")
        print(f"Produced {sample_mpy.name} ({sample_mpy.stat().st_size} bytes)")


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


def print_verification_summary(board: str, uf2: Path, mpy_cross_binary: Path) -> None:
    log("All verification checks passed")
    print(f"  1. Standard {board} firmware built with no errors/warnings: {uf2}")
    print(f"  2. Cross-compiler built: {mpy_cross_binary}")
    print("  3. Sample .py cross-compiled successfully")


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
    mpy_cross_binary = build_mpy_cross(micropython_dir, args.jobs)
    uf2 = build_firmware(micropython_dir, board, args.jobs)
    cross_compile_sample(mpy_cross_binary)

    print_verification_summary(board, uf2, mpy_cross_binary)
    return 0


def run_test(args: argparse.Namespace, versions: dict) -> int:
    """Just steps 5-6 of run_setup (build + verify), against whatever is already checked out —
    see the module docstring and toolchain/README.md's "How it works" for why that split exists."""
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
    # is the repeatable gate that checks it still builds cleanly.
    mpy_cross_binary = build_mpy_cross(micropython_dir, args.jobs)
    uf2 = build_firmware(micropython_dir, board, args.jobs)
    cross_compile_sample(mpy_cross_binary)

    print_verification_summary(board, uf2, mpy_cross_binary)
    return 0


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
