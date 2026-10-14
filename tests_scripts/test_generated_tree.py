"""tests/_generated_tree.py's require_fresh(), run under the real Unix port over a stand-in repo the generator wrote:
a fresh tree passes; an input edited after the generation (a TOML, the generator itself, even within the same second),
a TOML added or a missing stamp is refused naming the generator, and regenerating clears it. A zz_test_ fixture is none."""

import ast
import json
import os
import shutil
import subprocess
from pathlib import Path
from types import ModuleType

import pytest
from _devices import DEVICE_NAMES
from _script_loader import load_script_module

REPO_ROOT = Path(__file__).resolve().parent.parent
_GENERATOR = Path("scripts") / "_generate_sensortask_modules.py"
_STALE = "STALE build/generated_src/ is missing or stale - run: uv run scripts/_generate_sensortask_modules.py"
_CHECK = "import _generated_tree\ntry:\n    _generated_tree.require_fresh()\nexcept RuntimeError as e:\n    print('STALE', e)\nelse:\n    print('FRESH')\n"


def _edit_keeping_mtime(path: Path) -> None:
    # A second write within the same second as the generation: the content changes, the whole-second mtime does not.
    stat = path.stat()
    with path.open("a") as f:
        f.write("# edited after the generation\n")
    os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns))


def _guard_constants() -> "dict[str, object]":
    # tests/_generated_tree.py's own module-level literals, read without running MicroPython.
    tree = ast.parse((REPO_ROOT / "tests" / "_generated_tree.py").read_text(encoding="utf-8"))
    return {node.targets[0].id: ast.literal_eval(node.value) for node in tree.body if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name) and isinstance(node.value, (ast.Constant, ast.Tuple))}


def _require_fresh(micropython_bin: Path, root: Path) -> str:
    env = {**os.environ, "MICROPYPATH": f"{REPO_ROOT / 'tests'}:.frozen"}
    done = subprocess.run([str(micropython_bin), "-c", _CHECK], cwd=root, env=env, capture_output=True, text=True, check=False, timeout=60)
    assert done.returncode == 0, done.stdout + done.stderr
    return done.stdout.strip()


def test_a_fresh_generation_passes(generator: ModuleType, micropython_bin: Path, tmp_path: Path) -> None:
    assert generator.main() == 0
    assert _require_fresh(micropython_bin, tmp_path) == "FRESH"


def test_a_toml_edited_after_the_generation_is_refused_until_regenerated(generator: ModuleType, micropython_bin: Path, tmp_path: Path) -> None:
    assert generator.main() == 0
    with (tmp_path / "devices" / f"{DEVICE_NAMES[0]}.toml").open("a") as f:
        f.write("# edited after the generation\n")
    assert _require_fresh(micropython_bin, tmp_path) == _STALE
    assert generator.main() == 0
    assert _require_fresh(micropython_bin, tmp_path) == "FRESH"


def test_an_edit_within_the_generations_own_second_is_refused(generator: ModuleType, micropython_bin: Path, tmp_path: Path) -> None:
    assert generator.main() == 0
    _edit_keeping_mtime(tmp_path / "devices" / f"{DEVICE_NAMES[0]}.toml")
    assert _require_fresh(micropython_bin, tmp_path) == _STALE


def test_an_edit_of_the_generator_itself_is_refused(generator: ModuleType, micropython_bin: Path, tmp_path: Path) -> None:
    assert generator.main() == 0
    _edit_keeping_mtime(tmp_path / _GENERATOR)
    assert _require_fresh(micropython_bin, tmp_path) == _STALE


def test_a_toml_added_after_the_generation_is_refused(generator: ModuleType, micropython_bin: Path, tmp_path: Path) -> None:
    assert generator.main() == 0
    shutil.copy(tmp_path / "devices" / f"{DEVICE_NAMES[0]}.toml", tmp_path / "devices" / "added.toml")
    os.utime(tmp_path / "devices" / "added.toml", (0, 0))  # older than the generation: only the input set differs
    assert _require_fresh(micropython_bin, tmp_path) == _STALE


def test_a_zz_test_fixture_in_devices_is_not_an_input(generator: ModuleType, micropython_bin: Path, tmp_path: Path) -> None:
    assert generator.main() == 0
    shutil.copy(tmp_path / "devices" / f"{DEVICE_NAMES[0]}.toml", tmp_path / "devices" / "zz_test_fixture.toml")
    assert _require_fresh(micropython_bin, tmp_path) == "FRESH"


def test_a_missing_stamp_is_refused(generator: ModuleType, micropython_bin: Path, tmp_path: Path) -> None:
    assert generator.main() == 0
    (tmp_path / "build" / "generated_src" / ".inputs_stamp.json").unlink()
    assert _require_fresh(micropython_bin, tmp_path) == _STALE


@pytest.mark.parametrize("orphan", ["sensortask_{d}_gone.py", "sensortask_{d}_gone_wiring_plan.json", "definitions/{d}_gone.json"])
def test_a_file_no_current_device_produces_is_refused_until_regenerated(generator: ModuleType, micropython_bin: Path, tmp_path: Path, orphan: str) -> None:
    # A file a removed device left behind: a consumer globbing the tree would take it for a device, so the tree is stale.
    assert generator.main() == 0
    planted = tmp_path / "build" / "generated_src" / orphan.format(d=DEVICE_NAMES[0])
    planted.write_text("# a removed device's output\n")
    assert _require_fresh(micropython_bin, tmp_path) == _STALE
    assert generator.main() == 0
    assert not planted.exists()
    assert _require_fresh(micropython_bin, tmp_path) == "FRESH"


def test_a_missing_output_is_refused(generator: ModuleType, micropython_bin: Path, tmp_path: Path) -> None:
    assert generator.main() == 0
    (tmp_path / "build" / "generated_src" / f"sensortask_{DEVICE_NAMES[0]}_wiring_plan.json").unlink()
    assert _require_fresh(micropython_bin, tmp_path) == _STALE


def test_a_stamp_listing_no_output_is_refused(generator: ModuleType, micropython_bin: Path, tmp_path: Path) -> None:
    # An empty list would compare against nothing: the tree's top level is always read.
    assert generator.main() == 0
    stamp = tmp_path / "build" / "generated_src" / ".inputs_stamp.json"
    stamp.write_text(json.dumps({**json.loads(stamp.read_text()), "outputs": []}))
    assert _require_fresh(micropython_bin, tmp_path) == _STALE


def test_a_file_mid_rename_is_no_output(generator: ModuleType, micropython_bin: Path, tmp_path: Path) -> None:
    # A .tmp beside its final name is another run's write in progress, never a module a test imports.
    assert generator.main() == 0
    (tmp_path / "build" / "generated_src" / f"sensortask_{DEVICE_NAMES[0]}.py.tmp").write_text("# mid-rename\n")
    assert _require_fresh(micropython_bin, tmp_path) == "FRESH"


@pytest.fixture
def generator(repo_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    # The generator over a stand-in root: one device's TOML and the generator as real copies (edited below), the rest shared.
    module = load_script_module(repo_root / _GENERATOR, "_generate_sensortask_modules")
    monkeypatch.setattr(module, "REPO_ROOT", tmp_path)
    (tmp_path / "devices").mkdir()
    shutil.copy(repo_root / "devices" / f"{DEVICE_NAMES[0]}.toml", tmp_path / "devices")
    (tmp_path / "scripts").mkdir()
    shutil.copy(repo_root / _GENERATOR, tmp_path / _GENERATOR)
    for shared in ("src", "buildgen", "ext", "toolchain"):
        (tmp_path / shared).symlink_to(repo_root / shared)
    return module


def test_the_guard_reads_the_stamp_and_the_inputs_the_generator_writes(generator: ModuleType, tmp_path: Path) -> None:
    # Two independent lists of one fact: the stamp path and the input set must agree, or a fresh tree reads as stale.
    guard = _guard_constants()
    assert generator.main() == 0
    assert (tmp_path / str(guard["_STAMP"])).is_file()
    named, pairs = guard["_NAMED"], guard["_LISTED"]
    assert isinstance(named, tuple) and isinstance(pairs, tuple)
    assert set(named) == set(generator._NAMED_INPUTS)
    listed = {f"{directory}/*{suffix}" for directory, suffix in pairs}
    assert listed == {"devices/*.toml", *generator._INPUT_GLOBS}
