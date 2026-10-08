"""scripts/typecheck.sh ends every run with the summary block (SPECIFICATION.md E.10), and its stub install
records the version it resolved and wipes an install of another spec. Driven on copies of the script, with
mypy, uv and python3 stubbed, so nothing is installed or generated."""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

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
