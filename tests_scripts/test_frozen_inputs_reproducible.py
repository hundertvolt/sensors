"""Every derived device's staged firmware inputs are reproducible: two stagings under one build date and two hash seeds
are byte-identical, another date changes only the generated module's date line, and the manifest names every frozen
file in sorted order whatever order the host's directory walk yields (SPECIFICATION.md B.11)."""

import ast
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from _devices import DEVICE_NAMES

_REPO = Path(__file__).resolve().parent.parent
_DATE = "2026-09-12T10:00:00Z"
_OTHER_DATE = "2026-09-13T11:22:33Z"
_BOARD = "RPI_PICO_W"
_STAGE_PLACEHOLDER = "<stage>"
# One process stages every device into <out>/<device>/ with the given date and writes its rendered manifest beside it.
_STAGE_ALL = """
import sys
from pathlib import Path
repo, out, date, board = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3], sys.argv[4]
sys.path.insert(0, str(repo / "scripts"))
import build_firmware
for device in sys.argv[5:]:
    stage = out / device
    stage.mkdir(parents=True)
    generated = build_firmware.generate_device(repo / "devices" / f"{device}.toml", repo / "src", repo / "ext", build_date=date)
    build_firmware.stage_python_modules(stage, generated)
    (out / f"{device}.manifest").write_text(build_firmware.render_manifest(board, stage).replace(str(stage), "<stage>"), encoding="utf-8")
"""
# Executes a manifest with the pinned checkout's own tools/manifestfile.py under a directory walk that lists every
# directory in ascending or descending order, as two hosts may; prints the frozen files, -B keeping bytecode out.
_FROZEN_ORDER = """
import os, sys
mp, manifest, descending = sys.argv[1], sys.argv[2], sys.argv[3] == "descending"
sys.path.insert(0, mp + "/tools")
import manifestfile
walk = os.walk
def host_order(top, *args, **kwargs):
    for dirpath, dirnames, filenames in walk(top, *args, **kwargs):
        dirnames.sort(reverse=descending)
        filenames.sort(reverse=descending)
        yield dirpath, dirnames, filenames
os.walk = host_order
lib = mp + "/lib/micropython-lib"
m = manifestfile.ManifestFile(manifestfile.MODE_FREEZE, {"MPY_DIR": mp, "MPY_LIB_DIR": lib, "PORT_DIR": mp + "/ports/rp2", "BOARD_DIR": mp + "/ports/rp2/boards/RPI_PICO_W"})
m.add_library("micropython-lib", lib)
m.execute(manifest)
print("\\n".join(f.target_path for f in m.files()))
"""


def _stage_all(out: Path, date: str, seed: str) -> None:
    env = {**os.environ, "PYTHONHASHSEED": seed}
    done = subprocess.run([sys.executable, "-c", _STAGE_ALL, str(_REPO), str(out), date, _BOARD, *DEVICE_NAMES], env=env, capture_output=True, text=True, check=False)
    assert done.returncode == 0, done.stderr


@pytest.fixture(scope="module")
def stagings(tmp_path_factory: pytest.TempPathFactory) -> "tuple[Path, Path, Path]":
    # (date, seed 0), (date, seed 4242), (another date, seed 0), staged by three processes side by side.
    runs = [tmp_path_factory.mktemp(name) for name in ("seed0", "seed4242", "other_date")]
    with ThreadPoolExecutor(max_workers=len(runs)) as pool:
        list(pool.map(_stage_all, runs, (_DATE, _DATE, _OTHER_DATE), ("0", "4242", "0")))
    return runs[0], runs[1], runs[2]


def _files(root: Path) -> "dict[str, bytes]":
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()}


def test_two_hash_seeds_stage_byte_identical_inputs(stagings: "tuple[Path, Path, Path]") -> None:
    first, second, _other = stagings
    a, b = _files(first), _files(second)
    assert sorted(a) == sorted(b)
    assert [name for name in a if a[name] != b[name]] == []
    assert {f"{d}.manifest" for d in DEVICE_NAMES} <= set(a)


def test_the_build_date_is_the_one_input_that_differs(stagings: "tuple[Path, Path, Path]") -> None:
    # The date is the build's one time input (owner, 2026-10-05: 'They must differ for being genuine. Apart from that,
    # everything shall be byte-identical.'): another date changes exactly the generated module's date line.
    first, _second, other = stagings
    a, c = _files(first), _files(other)
    assert sorted(a) == sorted(c)
    differing = sorted(name for name in a if a[name] != c[name])
    assert differing == sorted(f"{d}/sensortask_{d}.py" for d in DEVICE_NAMES), differing
    for name in differing:
        lines = [(old, new) for old, new in zip(a[name].decode().splitlines(), c[name].decode().splitlines(), strict=True) if old != new]
        assert lines == [(f'_BUILD_DATE = const("{_DATE}")', f'_BUILD_DATE = const("{_OTHER_DATE}")')], (name, lines)


def test_every_manifest_names_its_files_and_freezes_no_bare_directory(stagings: "tuple[Path, Path, Path]") -> None:
    first, _second, _other = stagings
    for device in DEVICE_NAMES:
        tree = ast.parse((first / f"{device}.manifest").read_text(encoding="utf-8"))
        freezes = [node for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "freeze"]
        assert len(freezes) == 1 and len(freezes[0].args) == 2, f"{device}: a bare directory freeze() walks in the host's order"
        named = ast.literal_eval(freezes[0].args[1])
        assert list(named) == sorted(p.name for p in (first / device).glob("*.py")), device


def test_the_frozen_order_does_not_follow_the_host_s_directory_walk(stagings: "tuple[Path, Path, Path]", micropython_dir: Path, tmp_path: Path) -> None:
    # The board's own manifests walk directories too (ports/rp2/modules, micropython-lib packages); the rendered manifest
    # sorts every walk, so two hosts walking in different orders freeze the same order. The bare board manifest under
    # the same two walks shows the shuffle bites.
    first, _second, _other = stagings
    device = DEVICE_NAMES[0]
    manifest = tmp_path / "manifest.py"
    manifest.write_text((first / f"{device}.manifest").read_text(encoding="utf-8").replace(_STAGE_PLACEHOLDER, str(first / device)), encoding="utf-8")
    board = micropython_dir / "ports" / "rp2" / "boards" / _BOARD / "manifest.py"

    def frozen(path: Path, order: str) -> "list[str]":
        done = subprocess.run([sys.executable, "-B", "-c", _FROZEN_ORDER, str(micropython_dir), str(path), order], cwd=tmp_path, capture_output=True, text=True, check=False)
        assert done.returncode == 0, done.stderr
        return done.stdout.splitlines()

    assert frozen(board, "ascending") != frozen(board, "descending"), "the two walks froze one order - the check below would hold vacuously"
    ordered = frozen(manifest, "descending")
    assert ordered == frozen(manifest, "ascending")
    staged = sorted(p.name for p in (first / device).glob("*.py"))
    assert [name for name in ordered if name in staged] == staged
