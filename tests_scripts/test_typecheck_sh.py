"""scripts/typecheck.sh ends every run with the summary block (SPECIFICATION.md E.10), and its stub install
records the version it resolved and wipes an install of another spec. Driven on copies of the script, with
mypy, uv and python3 stubbed, so nothing is installed or generated."""

import configparser
import glob
import os
import re
import shlex
import shutil
import subprocess
from pathlib import Path

import pytest
import tomllib

REPO_ROOT = Path(__file__).resolve().parent.parent


# What a real `uv pip install --target typings` of the board stubs leaves: its own dist-info beside
# the stdlib package it pulls in (seen in an installed tree, 1.29.0.post1 with 1.29.0.post2).
_BOARD_DIST_INFO = "micropython_rp2_rpi_pico_w_stubs-1.29.0.post1.dist-info"
_INSTALLED_DIST_INFOS = (_BOARD_DIST_INFO, "micropython_stdlib_stubs-1.29.0.post2.dist-info")
_STUB_SPEC = "micropython-rp2-rpi_pico_w-stubs==1.29.0.*"


def _fake_uv(stub_bin: Path, *, install_fails: bool = False, dist_infos: "tuple[str, ...]" = _INSTALLED_DIST_INFOS) -> None:
    # `uv pip install --target <dir> ...` creates each dist-info directory under <dir>; anything else exits 0.
    made = " ".join(dist_infos)
    body = (
        "#!/usr/bin/env bash\n"
        f'if [ "$1" = "pip" ]; then\n    [ "{int(install_fails)}" = "0" ] || exit 1\n'
        '    while [ "$#" -gt 0 ] && [ "$1" != "--target" ]; do shift; done\n'
        f'    for d in {made}; do mkdir -p "$2/$d"; done\nfi\nexit 0\n'
    )
    (stub_bin / "uv").write_text(body)
    (stub_bin / "uv").chmod(0o755)


def _run(tmp_path: Path, *args: str, mypy_fails_on: str = "", uv_install_fails: bool = False, dist_infos: "tuple[str, ...]" = _INSTALLED_DIST_INFOS) -> subprocess.CompletedProcess[str]:
    root = tmp_path / "repo"
    (root / "scripts").mkdir(parents=True)
    for name in ("typecheck.sh", "_summary_block.sh"):
        shutil.copy(REPO_ROOT / "scripts" / name, root / "scripts" / name)
    stub_bin = tmp_path / "stub_bin"
    stub_bin.mkdir()
    stubs = {
        # Fails only the pass whose arguments contain mypy_fails_on (empty: none fails).
        "mypy": f'#!/usr/bin/env bash\nif [ -n "{mypy_fails_on}" ] && [[ "$*" == *"{mypy_fails_on}"* ]]; then echo "error: planted"; exit 1; fi\nexit 0\n',
        "python3": "#!/usr/bin/env bash\ncat >/dev/null\necho 1.29.0\n",
    }
    for name, body in stubs.items():
        (stub_bin / name).write_text(body)
        (stub_bin / name).chmod(0o755)
    _fake_uv(stub_bin, install_fails=uv_install_fails, dist_infos=dist_infos)
    env = {**os.environ, "PATH": f"{stub_bin}:{os.environ['PATH']}", "GIT_CEILING_DIRECTORIES": str(tmp_path)}
    return subprocess.run(["/bin/bash", str(root / "scripts" / "typecheck.sh"), *args], env=env, capture_output=True, text=True, check=False, timeout=60)


def _block(out: str) -> str:
    return out[out.index("== Summary: scripts/typecheck.sh ==") :]


def test_a_clean_run_counts_every_step_and_exits_0(tmp_path: Path) -> None:
    done = _run(tmp_path)
    assert done.returncode == 0, done.stdout + done.stderr
    block = _block(done.stdout)
    assert "\nCounts (checks): passed 7 · failed 0 ·" in block
    assert block.endswith("Result: PASS\nExit code: 0\n")


def test_a_failing_twin_pass_is_named_and_fails_the_run(tmp_path: Path) -> None:
    done = _run(tmp_path, mypy_fails_on="digital_twin/typecheck.ini")
    assert done.returncode == 1
    block = _block(done.stdout)
    assert "\nCounts (checks): passed 6 · failed 1 ·" in block
    assert "Failed:\n  - twin pass: digital_twin/typecheck.ini\n" in block
    assert block.endswith("Result: FAIL\nExit code: 1\n")


def test_every_pass_runs_even_after_one_fails(tmp_path: Path) -> None:
    done = _run(tmp_path, mypy_fails_on="host_typecheck.ini")
    assert done.returncode == 1
    assert "Failed:\n  - host pass: host_typecheck.ini\n" in _block(done.stdout)


def test_a_failing_stub_install_aborts_naming_its_stage(tmp_path: Path) -> None:
    done = _run(tmp_path, uv_install_fails=True)
    assert done.returncode == 1
    block = _block(done.stdout)
    assert "Failed:\n  - stub install: exited 1\n" in block
    assert "\nCounts (checks): passed 1 · failed 1 ·" in block


@pytest.mark.parametrize("flag", ["-h", "--help"])
def test_help_prints_the_usage_and_runs_nothing(tmp_path: Path, flag: str) -> None:
    done = _run(tmp_path, flag, uv_install_fails=True)
    assert done.returncode == 0, done.stderr
    assert done.stdout.startswith("Usage: scripts/typecheck.sh [PATH ...]")
    assert "== Summary" not in done.stdout


# --- the stub install block: the spec record, the wipe and the resolved version ----------------------


def _run_stub_block(tmp_path: Path, *, planted_spec: "str | None", stale: bool = True, dist_infos: "tuple[str, ...]" = _INSTALLED_DIST_INFOS, install_fails: bool = False) -> subprocess.CompletedProcess[str]:
    # Runs the script's own stub block, cut between its two marker lines, in tmp_path with uv faked;
    # plants an earlier install (a stale file, and a .stub-spec unless planted_spec is None) first.
    text = (REPO_ROOT / "scripts" / "typecheck.sh").read_text()
    begin, end = "# ---- stub install block ----\n", "# ---- end of the stub install block ----\n"
    assert begin in text and end in text, "scripts/typecheck.sh no longer marks its stub install block - update this test with it"
    block = text[text.index(begin) : text.index(end)]
    stub_bin = tmp_path / "stub_bin"
    stub_bin.mkdir()
    _fake_uv(stub_bin, dist_infos=dist_infos, install_fails=install_fails)
    if stale:
        (tmp_path / "typings").mkdir()
        (tmp_path / "typings" / "stale.pyi").write_text("# from an earlier install\n")
        if planted_spec is not None:
            (tmp_path / "typings" / ".stub-spec").write_text(f"{planted_spec}\n1.29.0.post1\n")
    script = tmp_path / "block.sh"
    script.write_text(f'#!/usr/bin/env bash\nset -euo pipefail\nfirmware_version=1.29.0\nstub_package="{_STUB_SPEC}"\n_stage_passed() {{ :; }}\n{block}')
    env = {**os.environ, "PATH": f"{stub_bin}:{os.environ['PATH']}"}
    return subprocess.run(["/bin/bash", str(script)], cwd=tmp_path, env=env, capture_output=True, text=True, check=False, timeout=60)


@pytest.mark.parametrize("planted_spec", ["micropython-rp2-rpi_pico_w-stubs==1.28.0.*", None])
def test_a_changed_or_missing_stub_spec_wipes_the_old_tree_first(tmp_path: Path, planted_spec: "str | None") -> None:
    # A version change never overlays an older install: the recorded spec decides, and no record at all
    # is an install this script cannot vouch for.
    done = _run_stub_block(tmp_path, planted_spec=planted_spec)
    assert done.returncode == 0, done.stdout + done.stderr
    assert not (tmp_path / "typings" / "stale.pyi").exists(), "the old stub tree survived a spec change"
    assert (tmp_path / "typings" / _BOARD_DIST_INFO).is_dir()


def test_an_unchanged_stub_spec_keeps_the_tree(tmp_path: Path) -> None:
    done = _run_stub_block(tmp_path, planted_spec=_STUB_SPEC)
    assert done.returncode == 0, done.stdout + done.stderr
    assert (tmp_path / "typings" / "stale.pyi").is_file(), "an unchanged spec must not wipe the tree"


def test_an_install_that_fails_leaves_no_record_so_the_next_run_starts_clean(tmp_path: Path) -> None:
    # The record means a complete install of its spec: one cut short (a failed or killed install over
    # an unchanged spec) leaves none, and the next run wipes whatever it half wrote.
    done = _run_stub_block(tmp_path, planted_spec=_STUB_SPEC, install_fails=True)
    assert done.returncode == 1, done.stdout + done.stderr
    assert not (tmp_path / "typings" / ".stub-spec").exists(), "a failed install left the record of a complete one"


def test_the_resolved_stub_version_is_printed_and_recorded(tmp_path: Path) -> None:
    done = _run_stub_block(tmp_path, planted_spec=None, stale=False)
    assert done.returncode == 0, done.stdout + done.stderr
    assert "== MicroPython stubs: 1.29.0.post1 (for firmware 1.29.0)\n" in done.stdout
    assert (tmp_path / "typings" / ".stub-spec").read_text() == f"{_STUB_SPEC}\n1.29.0.post1\n"


@pytest.mark.parametrize(
    ("dist_infos", "found"),
    [((_BOARD_DIST_INFO, "micropython_rp2_rpi_pico_w_stubs-1.29.0.post2.dist-info"), 2), (("micropython_stdlib_stubs-1.29.0.post2.dist-info",), 0)],
)
def test_not_exactly_one_board_stub_dist_info_fails_and_records_nothing(tmp_path: Path, dist_infos: "tuple[str, ...]", found: int) -> None:
    # Two installs side by side (or none) leave the installed version unknown, so the block fails rather
    # than record one; the stdlib package's own dist-info is not the board's and never counts.
    done = _run_stub_block(tmp_path, planted_spec=None, stale=False, dist_infos=dist_infos)
    assert done.returncode == 1, done.stdout + done.stderr
    assert f"error: found {found} stub dist-info directories" in done.stderr
    assert not (tmp_path / "typings" / ".stub-spec").exists()


def test_a_failing_board_stub_check_is_named_as_the_stub_install_stage(tmp_path: Path) -> None:
    # The whole script: the block's own exit reaches the summary block under its stage name.
    done = _run(tmp_path, dist_infos=())
    assert done.returncode == 1, done.stdout + done.stderr
    assert "Failed:\n  - stub install: exited 1\n" in _block(done.stdout)


# --- every file the main pass leaves out is checked by the twin pass ----------------------------

# The one file the main pass excludes that no pass may check: a bare `network.py` in a scanned root
# wins resolution over the real stub project-wide, silently turning WLAN types into Any (SPECIFICATION.md B.15).
_IN_NO_PASS = {"tests/network.py": "a bare network.py wins resolution over the real stub project-wide (SPECIFICATION.md B.15)"}
_TWIN_INI = "digital_twin/typecheck.ini"


def _python_files(root: Path, target: str) -> "set[str]":
    # The .py/.pyi files a mypy target names, repo-relative: a directory walked, a glob expanded.
    found: set[str] = set()
    for match in sorted(glob.glob(target, root_dir=root)) or [target]:
        path = root / match
        files = sorted(path.rglob("*.py*")) if path.is_dir() else [path]
        found |= {f.relative_to(root).as_posix() for f in files if f.suffix in {".py", ".pyi"} and f.is_file()}
    return found


def _main_pass_exclusions(root: Path) -> "set[str]":
    # The files pyproject's [tool.mypy] `files` would check but its `exclude` removes.
    cfg = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["tool"]["mypy"]
    seen = {rel for target in cfg["files"] for rel in _python_files(root, target)}
    return {rel for rel in seen if any(re.search(pattern, rel) for pattern in cfg["exclude"])}


def _twin_pass_targets(root: Path) -> "set[str]":
    # The files the twin pass checks as scripts/typecheck.sh invokes it, minus the ini's own exclude.
    lines = [line.strip() for line in (root / "scripts" / "typecheck.sh").read_text(encoding="utf-8").splitlines() if line.strip().startswith(f"mypy --config-file {_TWIN_INI} ")]
    assert len(lines) == 1, f"scripts/typecheck.sh no longer invokes the twin pass on one line: {lines}"
    targets = shlex.split(lines[0].split("||")[0])[3:]
    assert targets, "the twin pass names no target"
    ini = configparser.ConfigParser()
    ini.read(root / _TWIN_INI)
    excluded = ini.get("mypy", "exclude", fallback="").strip()
    return {rel for target in targets for rel in _python_files(root, target) if not (excluded and re.search(excluded, rel))}


def test_every_file_the_main_pass_excludes_is_a_twin_pass_target() -> None:
    # pyproject's comment says the twin pass checks what the main pass excludes; this proves it, so a
    # file excluded there is never in no pass at all.
    excluded = _main_pass_exclusions(REPO_ROOT)
    assert set(_IN_NO_PASS) <= excluded, f"stale entries in _IN_NO_PASS: {sorted(set(_IN_NO_PASS) - excluded)}"
    unchecked = sorted(excluded - _twin_pass_targets(REPO_ROOT) - set(_IN_NO_PASS))
    assert not unchecked, f"excluded from the main pass yet in no twin pass target, so no mypy pass checks them: {unchecked}"


def test_the_exclusion_guard_sees_a_planted_unchecked_file(tmp_path: Path) -> None:
    # A file the main pass excludes and the twin pass never names is reported.
    for rel in ("pyproject.toml", "scripts/typecheck.sh", _TWIN_INI):
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(REPO_ROOT / rel, tmp_path / rel)
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "_planted_twin_library.py").write_text("", encoding="utf-8")
    text = (tmp_path / "pyproject.toml").read_text(encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text(text.replace("exclude = [\n", 'exclude = [\n    "tests/_planted_twin_library\\\\.py$",\n', 1), encoding="utf-8")
    assert "tests/_planted_twin_library.py" in _main_pass_exclusions(tmp_path) - _twin_pass_targets(tmp_path)


# The one file the host pass excludes that no pass checks (two trivial fixtures, SPECIFICATION.md B.15).
_HOST_IN_NO_PASS = {"tests_scripts/conftest.py": "with both test tiers on mypy_path both conftests are a bare `conftest`"}
_HOST_INI = "host_typecheck.ini"


def _host_pass_exclusions(root: Path) -> "set[str]":
    ini = configparser.ConfigParser()
    ini.read(root / _HOST_INI)
    excluded = ini.get("mypy", "exclude").strip()
    seen = {rel for target in ini.get("mypy", "files").split(",") for rel in _python_files(root, target.strip())}
    return {rel for rel in seen if re.search(excluded, rel)}


def _checked_elsewhere(root: Path) -> "set[str]":
    # The main pass's files, the twin pass's, and every file typecheck.sh names on a host line (named, it ignores exclude).
    cfg = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["tool"]["mypy"]
    main = {rel for target in cfg["files"] for rel in _python_files(root, target)} - _main_pass_exclusions(root)
    lines = [line.strip() for line in (root / "scripts" / "typecheck.sh").read_text(encoding="utf-8").splitlines() if line.strip().startswith(f"mypy --config-file {_HOST_INI}")]
    named = {rel for line in lines for target in shlex.split(line.split("||")[0])[3:] for rel in _python_files(root, target)}
    return main | _twin_pass_targets(root) | named


def test_every_file_the_host_pass_excludes_is_checked_by_another_run() -> None:
    excluded = _host_pass_exclusions(REPO_ROOT)
    assert set(_HOST_IN_NO_PASS) <= excluded, f"stale entries in _HOST_IN_NO_PASS: {sorted(set(_HOST_IN_NO_PASS) - excluded)}"
    unchecked = sorted(excluded - _checked_elsewhere(REPO_ROOT) - set(_HOST_IN_NO_PASS))
    assert not unchecked, f"excluded from the host pass yet named by no other mypy run, so none checks them: {unchecked}"


def test_the_host_exclusion_guard_sees_a_planted_unchecked_file(tmp_path: Path) -> None:
    for rel in ("pyproject.toml", "scripts/typecheck.sh", _TWIN_INI, _HOST_INI):
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(REPO_ROOT / rel, tmp_path / rel)
    (tmp_path / "tests_hardware").mkdir()
    (tmp_path / "tests_hardware" / "planted_host_module.py").write_text("", encoding="utf-8")
    text = (tmp_path / _HOST_INI).read_text(encoding="utf-8")
    (tmp_path / _HOST_INI).write_text(text.replace("exclude = (?x)(", "exclude = (?x)(^tests_hardware/planted_host_module\\.py$|", 1), encoding="utf-8")
    assert "tests_hardware/planted_host_module.py" in _host_pass_exclusions(tmp_path) - _checked_elsewhere(tmp_path)
