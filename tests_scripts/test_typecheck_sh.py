"""scripts/typecheck.sh: the exact stub pins of versions.toml [stubs] checked against [micropython] ref, an install that
must be exactly those releases, repairs that no-op on a fixed tree and fail on a moved one, and every pass and single-file
run named in the summary block. Driven on copies of the script, with mypy and uv stubbed, so nothing is installed."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import tomllib

REPO_ROOT = Path(__file__).resolve().parent.parent

# What a real install of the two pins leaves: one dist-info each (seen in an installed tree, 1.29.0.post1 / .post2).
_BOARD, _STDLIB = "1.29.0.post1", "1.29.0.post2"
_INSTALLED_DIST_INFOS = (f"micropython_rp2_rpi_pico_w_stubs-{_BOARD}.dist-info", f"micropython_stdlib_stubs-{_STDLIB}.dist-info")
_STUB_SPEC = f"micropython-rp2-rpi_pico_w-stubs=={_BOARD} micropython-stdlib-stubs=={_STDLIB}"
_VERSIONS = f'[micropython]\nref = "v1.29.0"\n\n[stubs]\nboard = "{_BOARD}"\nstdlib = "{_STDLIB}"\n'
_RUNS = ("main pass", "twin pass", "host pass", "bench conftest check", "network check", "conftest check")
_STAGES = ("stub pins", "stub install", "stub repairs", "module generation")


def _fake_uv(stub_bin: Path, *, install_fails: bool = False, dist_infos: "tuple[str, ...]" = _INSTALLED_DIST_INFOS) -> None:
    # `uv pip install --target <dir> ...` creates each dist-info and an unrepaired stdlib tree under <dir>; the lock
    # check and the generation exit 0.
    made = " ".join(dist_infos)
    tree = 'mkdir -p "$2/stdlib/asyncio"; echo "class _Future: ..." > "$2/stdlib/_asyncio.pyi"; echo "# NotImplemented: _NotImplementedType" > "$2/stdlib/builtins.pyi"'
    body = (
        "#!/usr/bin/env bash\n"
        'echo "uv $*" >> "$UV_CALLS"\n'
        f'if [ "$1" = "pip" ]; then\n    [ "{int(install_fails)}" = "0" ] || exit 1\n'
        '    while [ "$#" -gt 0 ] && [ "$1" != "--target" ]; do shift; done\n'
        f'    for d in {made}; do mkdir -p "$2/$d"; done\n    {tree}\nfi\nexit 0\n'
    )
    (stub_bin / "uv").write_text(body, encoding="utf-8")
    (stub_bin / "uv").chmod(0o755)


def _sandbox(tmp_path: Path, *, mypy_fails_on: str = "", uv_install_fails: bool = False, dist_infos: "tuple[str, ...]" = _INSTALLED_DIST_INFOS, versions: str = _VERSIONS) -> "tuple[Path, dict[str, str]]":
    # The script and its helpers in a stand-in repo with a .venv of a stub mypy (failing the run whose arguments hold
    # mypy_fails_on) and the real interpreter, a stub uv beside it, and a versions.toml of its own.
    root = tmp_path / "repo"
    (root / "scripts").mkdir(parents=True)
    (root / "toolchain").mkdir()
    for name in ("typecheck.sh", "_summary_block.sh", "_require_venv.sh", "_require_python.sh"):
        shutil.copy(REPO_ROOT / "scripts" / name, root / "scripts" / name)
    (root / "toolchain" / "versions.toml").write_text(versions, encoding="utf-8")
    venv_bin = root / ".venv" / "bin"
    venv_bin.mkdir(parents=True)
    mypy = f'#!/usr/bin/env bash\necho "mypy $*" >> "$UV_CALLS"\nif [ -n "{mypy_fails_on}" ] && [[ "$*" == *"{mypy_fails_on}"* ]]; then echo "error: planted"; exit 1; fi\nexit 0\n'
    (venv_bin / "mypy").write_text(mypy, encoding="utf-8")
    (venv_bin / "mypy").chmod(0o755)
    (venv_bin / "python3").symlink_to(sys.executable)
    uv_bin = tmp_path / "uv_bin"
    uv_bin.mkdir()
    _fake_uv(uv_bin, install_fails=uv_install_fails, dist_infos=dist_infos)
    env = {"PATH": f"{venv_bin}:{uv_bin}:/usr/bin:/bin", "VIRTUAL_ENV": str(root / ".venv"), "UV_CALLS": str(tmp_path / "calls"), "HOME": str(tmp_path), "GIT_CEILING_DIRECTORIES": str(tmp_path)}
    return root, env


def _run(tmp_path: Path, *args: str, **kwargs: object) -> subprocess.CompletedProcess[str]:
    root, env = _sandbox(tmp_path, **kwargs)  # type: ignore[arg-type]
    return subprocess.run(["/bin/bash", str(root / "scripts" / "typecheck.sh"), *args], cwd=root, env=env, capture_output=True, text=True, check=False, timeout=60)


def _block(out: str) -> str:
    return out[out.index("== Summary: scripts/typecheck.sh ==") :]


def test_a_clean_run_counts_every_stage_and_run_and_exits_0(tmp_path: Path) -> None:
    done = _run(tmp_path)
    assert done.returncode == 0, done.stdout + done.stderr
    block = _block(done.stdout)
    assert f"\nCounts (checks): passed {len(_STAGES) + len(_RUNS)} · failed 0 ·" in block
    assert block.endswith("Result: PASS\nExit code: 0\n")
    mypy = [line.rstrip() for line in (tmp_path / "calls").read_text(encoding="utf-8").splitlines() if line.startswith("mypy")]
    assert mypy == [
        "mypy",
        "mypy --config-file digital_twin/typecheck.ini",
        "mypy --config-file host_typecheck.ini",
        "mypy --config-file host_typecheck.ini tests_hardware/bench/conftest.py",
        "mypy tests/network.py",
        "mypy --config-file host_typecheck.ini tests_scripts/conftest.py",
    ], mypy


@pytest.mark.parametrize(("fails_on", "named"), [("digital_twin/typecheck.ini", "twin pass: digital_twin/typecheck.ini"), ("tests/network.py", "network check: pyproject.toml [tool.mypy]"), ("tests_scripts/conftest.py", "conftest check: host_typecheck.ini")])
def test_a_failing_run_is_named_and_fails_the_script_after_every_run(tmp_path: Path, fails_on: str, named: str) -> None:
    done = _run(tmp_path, mypy_fails_on=fails_on)
    assert done.returncode == 1
    block = _block(done.stdout)
    assert f"\nCounts (checks): passed {len(_STAGES) + len(_RUNS) - 1} · failed 1 ·" in block
    assert f"Failed:\n  - {named}\n" in block
    assert block.endswith("Result: FAIL\nExit code: 1\n")


def test_extra_paths_narrow_only_the_main_pass(tmp_path: Path) -> None:
    done = _run(tmp_path, "src", "tests")
    assert done.returncode == 0, done.stderr
    mypy = [line.rstrip() for line in (tmp_path / "calls").read_text(encoding="utf-8").splitlines() if line.startswith("mypy")]
    assert mypy[0] == "mypy src tests" and mypy[1] == "mypy --config-file digital_twin/typecheck.ini", mypy


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
    assert not (tmp_path / "calls").exists()


def test_an_unknown_option_is_refused_naming_it_before_anything_runs(tmp_path: Path) -> None:
    done = _run(tmp_path, "--strict")
    assert done.returncode == 2
    assert "error: unknown option --strict" in done.stderr
    assert not (tmp_path / "calls").exists()


def test_outside_the_project_venv_nothing_runs(tmp_path: Path) -> None:
    root, env = _sandbox(tmp_path)
    env["VIRTUAL_ENV"] = str(tmp_path)
    done = subprocess.run(["/bin/bash", str(root / "scripts" / "typecheck.sh")], cwd=root, env=env, capture_output=True, text=True, check=False, timeout=60)
    assert done.returncode == 1
    assert "error: activate the project venv first" in done.stderr
    assert not (tmp_path / "calls").exists()


# --- the stub pins: exact releases of the ref's X.Y.Z -----------------------------------------------


@pytest.mark.parametrize(
    ("versions", "named"),
    [
        (_VERSIONS.replace(f'board = "{_BOARD}"', 'board = "1.28.0.post1"'), "[stubs] board = '1.28.0.post1' does not belong to [micropython] ref v1.29.0"),
        (_VERSIONS.replace(f'stdlib = "{_STDLIB}"', 'stdlib = "1.29.1"'), "[stubs] stdlib = '1.29.1' does not belong to [micropython] ref v1.29.0"),
        (_VERSIONS.replace(f'stdlib = "{_STDLIB}"\n', ""), "[stubs] stdlib = None does not belong"),
        (_VERSIONS.partition("[stubs]")[0], "has no readable [micropython] ref and [stubs] table"),
    ],
    ids=["board-of-another-release", "stdlib-of-another-release", "stdlib-missing", "no-stubs-table"],
)
def test_a_stub_pin_of_another_release_is_refused_naming_the_key(tmp_path: Path, versions: str, named: str) -> None:
    done = _run(tmp_path, versions=versions)
    assert done.returncode == 1
    assert named in done.stderr, done.stderr
    assert "Failed:\n  - stub pins: exited 1\n" in _block(done.stdout)
    assert "uv pip" not in (tmp_path / "calls").read_text(encoding="utf-8"), "a refused pin was installed"


def test_the_shipped_pins_belong_to_the_shipped_ref() -> None:
    # A MicroPython bump without the stub move fails the unit tier as well as the typecheck.
    versions = tomllib.loads((REPO_ROOT / "toolchain" / "versions.toml").read_text(encoding="utf-8"))
    release = versions["micropython"]["ref"].lstrip("v")
    for key in ("board", "stdlib"):
        pin = versions["stubs"][key]
        assert pin == release or pin.startswith(f"{release}.post"), f"[stubs] {key} = {pin} is not a {release} stub release"


def test_the_exact_pins_are_installed_and_recorded(tmp_path: Path) -> None:
    done = _run(tmp_path)
    assert done.returncode == 0, done.stderr
    calls = (tmp_path / "calls").read_text(encoding="utf-8").splitlines()
    assert f"uv pip install --quiet --target typings micropython-rp2-rpi_pico_w-stubs=={_BOARD} micropython-stdlib-stubs=={_STDLIB}" in calls
    assert f"== MicroPython stubs: board {_BOARD}, stdlib {_STDLIB} (for firmware 1.29.0)\n" in done.stdout
    assert (tmp_path / "repo" / "typings" / ".stub-spec").read_text(encoding="utf-8") == f"{_STUB_SPEC}\n{_BOARD} {_STDLIB}\n"


@pytest.mark.parametrize(
    ("dist_infos", "named"),
    [
        ((*_INSTALLED_DIST_INFOS, "micropython_rp2_rpi_pico_w_stubs-1.29.0.post3.dist-info"), f"micropython_rp2_rpi_pico_w_stubs {_BOARD} 1.29.0.post3 where versions.toml pins {_BOARD}"),
        ((_INSTALLED_DIST_INFOS[0], "micropython_stdlib_stubs-1.29.0.post9.dist-info"), f"micropython_stdlib_stubs 1.29.0.post9 where versions.toml pins {_STDLIB}"),
        ((_INSTALLED_DIST_INFOS[1],), f"micropython_rp2_rpi_pico_w_stubs nothing where versions.toml pins {_BOARD}"),
    ],
    ids=["two-board-installs", "another-stdlib-release", "no-board-install"],
)
def test_an_install_that_is_not_exactly_the_pins_fails_and_records_nothing(tmp_path: Path, dist_infos: "tuple[str, ...]", named: str) -> None:
    done = _run(tmp_path, dist_infos=dist_infos)
    assert done.returncode == 1, done.stdout + done.stderr
    assert f"error: typings/ holds {named}" in done.stderr, done.stderr
    assert not (tmp_path / "repo" / "typings" / ".stub-spec").exists()


# --- the stub install block: the spec record and the wipe ----------------------------------------------


def _run_block(tmp_path: Path, name: str, prelude: str) -> subprocess.CompletedProcess[str]:
    # One of the script's marked blocks, cut between its two marker lines, run in tmp_path with uv faked.
    text = (REPO_ROOT / "scripts" / "typecheck.sh").read_text(encoding="utf-8")
    begin, end = f"# ---- {name} block ----\n", f"# ---- end of the {name} block ----\n"
    assert begin in text and end in text, f"scripts/typecheck.sh no longer marks its {name} block - update this test with it"
    block = text[text.index(begin) : text.index(end)]
    stub_bin = tmp_path / "stub_bin"
    stub_bin.mkdir(exist_ok=True)
    _fake_uv(stub_bin)
    script = tmp_path / "block.sh"
    script.write_text(f"#!/usr/bin/env bash\nset -euo pipefail\n_stage_passed() {{ :; }}\n{prelude}\n{block}", encoding="utf-8")
    env = {**os.environ, "PATH": f"{stub_bin}:{os.environ['PATH']}", "UV_CALLS": str(tmp_path / "calls")}
    return subprocess.run(["/bin/bash", str(script)], cwd=tmp_path, env=env, capture_output=True, text=True, check=False, timeout=60)


_PINS = f"firmware_version=1.29.0\nboard_pin={_BOARD}\nstdlib_pin={_STDLIB}"


@pytest.mark.parametrize("planted_spec", ["micropython-rp2-rpi_pico_w-stubs==1.28.0.post1 micropython-stdlib-stubs==1.28.0.post1", None])
def test_a_changed_or_missing_stub_spec_wipes_the_old_tree_first(tmp_path: Path, planted_spec: "str | None") -> None:
    (tmp_path / "typings").mkdir()
    (tmp_path / "typings" / "stale.pyi").write_text("# from an earlier install\n", encoding="utf-8")
    if planted_spec is not None:
        (tmp_path / "typings" / ".stub-spec").write_text(f"{planted_spec}\n1.28.0.post1 1.28.0.post1\n", encoding="utf-8")
    done = _run_block(tmp_path, "stub install", _PINS)
    assert done.returncode == 0, done.stdout + done.stderr
    assert not (tmp_path / "typings" / "stale.pyi").exists(), "the old stub tree survived a spec change"


def test_an_unchanged_stub_spec_keeps_the_tree(tmp_path: Path) -> None:
    (tmp_path / "typings").mkdir()
    (tmp_path / "typings" / "stale.pyi").write_text("# from an earlier install\n", encoding="utf-8")
    (tmp_path / "typings" / ".stub-spec").write_text(f"{_STUB_SPEC}\n{_BOARD} {_STDLIB}\n", encoding="utf-8")
    done = _run_block(tmp_path, "stub install", _PINS)
    assert done.returncode == 0, done.stdout + done.stderr
    assert (tmp_path / "typings" / "stale.pyi").is_file(), "an unchanged spec must not wipe the tree"


# --- the stub repairs: a fixed upstream is a no-op, a moved tree fails -----------------------------------


def _stub_tree(tmp_path: Path, *, futures: bool = False, future_class: bool = True, builtins: "str | None" = "# NotImplemented: _NotImplementedType\n") -> Path:
    stdlib = tmp_path / "typings" / "stdlib"
    (stdlib / "asyncio").mkdir(parents=True)
    (stdlib / "_asyncio.pyi").write_text("class _Future: ...\n" if future_class else "class Task: ...\n", encoding="utf-8")
    if futures:
        (stdlib / "asyncio" / "futures.pyi").write_text("from _asyncio import Future as Future\n", encoding="utf-8")
    if builtins is not None:
        (stdlib / "builtins.pyi").write_text(builtins, encoding="utf-8")
    return stdlib


def test_both_defects_present_are_repaired(tmp_path: Path) -> None:
    stdlib = _stub_tree(tmp_path)
    done = _run_block(tmp_path, "stub repairs", "")
    assert done.returncode == 0, done.stderr
    assert (stdlib / "asyncio" / "futures.pyi").read_text(encoding="utf-8") == "from _asyncio import _Future as Future\n"
    assert (stdlib / "builtins.pyi").read_text(encoding="utf-8") == "NotImplemented: _NotImplementedType\n"


def test_a_tree_upstream_fixed_is_left_untouched(tmp_path: Path) -> None:
    stdlib = _stub_tree(tmp_path, futures=True, builtins="NotImplemented: _NotImplementedType\n")
    done = _run_block(tmp_path, "stub repairs", "")
    assert done.returncode == 0, done.stderr
    assert (stdlib / "asyncio" / "futures.pyi").read_text(encoding="utf-8") == "from _asyncio import Future as Future\n"
    assert (stdlib / "builtins.pyi").read_text(encoding="utf-8") == "NotImplemented: _NotImplementedType\n"


@pytest.mark.parametrize(
    ("tree", "named"),
    [
        ({"builtins": None}, "typings/stdlib/builtins.pyi missing"),
        ({"builtins": "class object: ...\n"}, "NotImplemented in typings/stdlib/builtins.pyi missing"),
        ({"future_class": False}, "class _Future in typings/stdlib/_asyncio.pyi missing"),
    ],
    ids=["no-builtins", "no-notimplemented", "no-future-class"],
)
def test_a_moved_tree_fails_the_repair_naming_the_path(tmp_path: Path, tree: "dict[str, object]", named: str) -> None:
    _stub_tree(tmp_path, **tree)  # type: ignore[arg-type]
    done = _run_block(tmp_path, "stub repairs", "")
    assert done.returncode == 1
    assert f"error: the installed stub tree moved ({named}) - re-verify the" in done.stderr, done.stderr


def test_a_missing_asyncio_package_fails_the_repair(tmp_path: Path) -> None:
    (tmp_path / "typings" / "stdlib").mkdir(parents=True)
    done = _run_block(tmp_path, "stub repairs", "")
    assert done.returncode == 1
    assert "error: the installed stub tree moved (typings/stdlib/asyncio/ missing)" in done.stderr
