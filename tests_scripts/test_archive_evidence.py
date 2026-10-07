"""scripts/_archive_evidence.py moves a runner's evidence into build/archive/<runner>/<UTC timestamp>/
and keeps the newest three runs per runner: older runs go, nothing outside that runner's directory
is touched, and a missing path is skipped."""

import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest
from _script_loader import load_script_module

REPO_ROOT = Path(__file__).resolve().parent.parent
_SCRIPT = REPO_ROOT / "scripts" / "_archive_evidence.py"


@pytest.fixture(scope="module")
def archive() -> ModuleType:
    return load_script_module(_SCRIPT, "_archive_evidence")


def _snapshot(root: Path) -> set[str]:
    return {str(p.relative_to(root)) for p in root.rglob("*")}


def test_four_archivings_keep_the_newest_three(archive: ModuleType, tmp_path: Path) -> None:
    root = tmp_path / "archive"
    made = []
    for n in range(4):
        evidence = tmp_path / f"log{n}.txt"
        evidence.write_text(f"run {n}\n")
        made.append(archive.archive("x", [evidence], root=root))
    runs = sorted(p.name for p in (root / "x").iterdir())
    assert runs == sorted(p.name for p in made[1:])
    assert not made[0].exists()
    assert (made[3] / "log3.txt").read_text() == "run 3\n"
    assert not (tmp_path / "log3.txt").exists(), "evidence is moved, not copied"


def test_nothing_outside_the_runners_directory_is_touched(archive: ModuleType, tmp_path: Path) -> None:
    root = tmp_path / "archive"
    (root / "y").mkdir(parents=True)
    (root / "y" / "20200101T000000Z").mkdir()
    (root / "stray.txt").write_text("keep\n")
    (root / "x").mkdir()
    (root / "x" / "notes").mkdir()  # not a timestamp: never pruned
    outside = tmp_path / "unrelated"
    outside.mkdir()
    before_outside = _snapshot(outside)
    for n in range(5):
        evidence = tmp_path / f"e{n}"
        evidence.write_text("e\n")
        archive.archive("x", [evidence], root=root)
    assert (root / "y" / "20200101T000000Z").is_dir(), "runner y's runs are not pruned by runner x's keep"
    assert (root / "stray.txt").read_text() == "keep\n"
    assert (root / "x" / "notes").is_dir()
    assert _snapshot(outside) == before_outside
    assert len([p for p in (root / "x").iterdir() if p.name != "notes"]) == 3


def test_a_missing_path_is_skipped_and_nothing_is_created_for_none(archive: ModuleType, tmp_path: Path) -> None:
    root = tmp_path / "archive"
    assert archive.archive("x", [tmp_path / "absent"], root=root) is None
    assert not (root / "x").exists() or not any((root / "x").iterdir())
    present = tmp_path / "present"
    present.mkdir()
    (present / "f").write_text("f\n")
    run = archive.archive("x", [tmp_path / "absent", present], root=root)
    assert run is not None
    assert sorted(p.name for p in run.iterdir()) == ["present"]


def test_two_runs_in_one_second_get_distinct_directories(archive: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(archive, "_timestamp", lambda: "20261006T120000Z")
    first = archive.new_run_dir("x", root=tmp_path)
    second = archive.new_run_dir("x", root=tmp_path)
    assert (first.name, second.name) == ("20261006T120000Z", "20261006T120000Z-1")
    assert first.is_dir()
    assert second.is_dir()


def test_a_run_in_the_same_second_never_reuses_a_pruned_name(archive: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(archive, "_timestamp", lambda: "20261006T120000Z")
    runs = [archive.new_run_dir("x", root=tmp_path) for _ in range(5)]
    assert sorted(p.name for p in (tmp_path / "x").iterdir()) == ["20261006T120000Z-2", "20261006T120000Z-3", "20261006T120000Z-4"]
    assert runs[-1].is_dir()


def test_a_clock_stepped_backwards_never_prunes_the_new_run(archive: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    for stamp in ("20261006T120000Z", "20261006T120001Z", "20261006T120002Z", "20200101T000000Z"):
        monkeypatch.setattr(archive, "_timestamp", lambda stamp=stamp: stamp)
        newest = archive.new_run_dir("x", root=tmp_path)
    assert newest.is_dir()
    assert len(list((tmp_path / "x").iterdir())) == 3


@pytest.mark.parametrize(("runner", "keep"), [("Bad-Name", 3), ("../x", 3), ("", 3), ("x", 0)])
def test_a_bad_runner_name_or_keep_is_refused(archive: ModuleType, tmp_path: Path, runner: str, keep: int) -> None:
    with pytest.raises(ValueError, match=r"runner|keep"):
        archive.new_run_dir(runner, keep=keep, root=tmp_path)


def _cli(tmp_path: Path, *argv: str) -> subprocess.CompletedProcess[str]:
    # Runs a copy of the script whose repository root is tmp_path, so build/archive lands there.
    copy = tmp_path / "scripts" / _SCRIPT.name
    if not copy.exists():
        copy.parent.mkdir(parents=True)
        copy.write_text(_SCRIPT.read_text())
    return subprocess.run([sys.executable, str(copy), *argv], cwd=tmp_path, capture_output=True, text=True, check=False)


def test_the_new_dir_cli_prints_an_existing_empty_directory(tmp_path: Path) -> None:
    done = _cli(tmp_path, "--runner", "x", "--new-dir")
    assert done.returncode == 0, done.stderr
    created = Path(done.stdout.strip())
    assert created.is_dir()
    assert created.parent == tmp_path / "build" / "archive" / "x"
    assert not any(created.iterdir())


def test_the_cli_archives_paths_and_prints_the_directory(tmp_path: Path) -> None:
    evidence = tmp_path / "log.txt"
    evidence.write_text("x\n")
    done = _cli(tmp_path, "--runner", "x", str(evidence), str(tmp_path / "absent"))
    assert done.returncode == 0, done.stderr
    assert (Path(done.stdout.strip()) / "log.txt").read_text() == "x\n"
    nothing = _cli(tmp_path, "--runner", "x", str(tmp_path / "absent"))
    assert (nothing.returncode, nothing.stdout) == (0, "")


@pytest.mark.parametrize("argv", [["--runner", "Bad"], ["--runner", "x", "--keep", "0"], [], ["--bogus"]])
def test_the_cli_exits_2_on_a_usage_error(tmp_path: Path, argv: list[str]) -> None:
    done = _cli(tmp_path, *argv)
    assert done.returncode == 2, done.stdout + done.stderr
    assert not (tmp_path / "build").exists()


def test_import_has_no_side_effect(tmp_path: Path) -> None:
    done = subprocess.run([sys.executable, "-c", "import scripts._archive_evidence"], cwd=REPO_ROOT, capture_output=True, text=True, check=False)
    assert done.returncode == 0, done.stderr
    assert done.stdout == ""
