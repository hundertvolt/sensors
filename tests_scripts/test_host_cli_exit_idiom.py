"""Every host CLI exits through one idiom, `raise SystemExit(main())`, its user-error classes derive from Exception, and
a malformed input reaches the user as one stderr line and exit 1, never a traceback - tracebacks are for internal bugs
(owner, 2026-09-25, paraphrase; SPECIFICATION.md L.5)."""

import ast
import subprocess
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parent.parent
# The host-CPython scopes; tests_hardware/device_scripts/ is MicroPython code pushed to the board.
_HOST_SCOPES = ("buildgen", "toolchain", "scripts", "tests_scripts", "tests_hardware")
_NOT_HOST = ("tests_hardware/device_scripts/",)
# The user-error class of each tool family, (file, class): the one a CLI's main() turns into its one line.
_USER_ERRORS = (
    ("buildgen/errors.py", "BuildError"),
    ("toolchain/setup_toolchain.py", "SetupError"),
    ("toolchain/micropython_overrides.py", "OverrideError"),
    ("scripts/_strip_type_checking.py", "StripError"),
    ("scripts/_stage_website.py", "StageError"),
)
_TIMEOUT_S = 60


def _is_main_guard(node: ast.If) -> bool:
    if not isinstance(node.test, ast.Compare) or len(node.test.comparators) != 1:
        return False
    left, right = node.test.left, node.test.comparators[0]
    return isinstance(left, ast.Name) and left.id == "__name__" and isinstance(right, ast.Constant) and right.value == "__main__"


def _is_main_call(node: ast.AST) -> bool:
    return isinstance(node, ast.Call) and ((isinstance(node.func, ast.Name) and node.func.id == "main") or (isinstance(node.func, ast.Attribute) and node.func.attr == "main"))


def _is_idiom(block: ast.If) -> bool:
    # Exactly `raise SystemExit(main(...))`, the arguments (an explicit argv) left to the CLI.
    if len(block.body) != 1 or block.orelse or not isinstance(block.body[0], ast.Raise):
        return False
    exc = block.body[0].exc
    return isinstance(exc, ast.Call) and isinstance(exc.func, ast.Name) and exc.func.id == "SystemExit" and len(exc.args) == 1 and _is_main_call(exc.args[0])


def idiom_violations(source: str, rel: str) -> "list[str]":
    # Each module-level __main__ block that runs a main() in any other form; a block running none (a test file's
    # --regenerate hook) is no CLI exit and is left alone.
    blocks = [node for node in ast.parse(source, rel).body if isinstance(node, ast.If) and _is_main_guard(node)]
    return [f"{rel}:{block.body[0].lineno}" for block in blocks if any(_is_main_call(sub) for sub in ast.walk(block)) and not _is_idiom(block)]


def _host_files() -> "list[str]":
    found = []
    for scope in _HOST_SCOPES:
        for path in sorted((_REPO / scope).rglob("*.py")):
            rel = path.relative_to(_REPO).as_posix()
            if "__pycache__" not in rel and not rel.startswith(_NOT_HOST):
                found.append(rel)
    return found


def test_every_host_cli_exits_through_raise_systemexit_main() -> None:
    violations = [site for rel in _host_files() for site in idiom_violations((_REPO / rel).read_text(encoding="utf-8"), rel)]
    assert not violations, f'end each host CLI with `if __name__ == "__main__": raise SystemExit(main())`: {violations}'


@pytest.mark.parametrize(
    ("block", "violates"),
    [
        ("raise SystemExit(main())", False),
        ("raise SystemExit(main(sys.argv[1:]))", False),
        ("raise SystemExit(runner.main())", False),
        ("sys.exit(main())", True),
        ("code = main()\n    raise SystemExit(code)", True),
        ("try:\n        raise SystemExit(main())\n    except KeyboardInterrupt:\n        pass", True),
        ("_regenerate()", False),
    ],
)
def test_the_idiom_check_bites(block: str, *, violates: bool) -> None:
    source = f'import sys\n\n\ndef main() -> int:\n    return 0\n\n\nif __name__ == "__main__":\n    {block}\n'
    assert bool(idiom_violations(source, "planted.py")) is violates, block


@pytest.mark.parametrize(("rel", "name"), _USER_ERRORS)
def test_each_user_error_class_derives_from_exception(rel: str, name: str) -> None:
    # Exception itself, as BuildError does: a RuntimeError base would let a broad `except RuntimeError` swallow it.
    classes = [node for node in ast.parse((_REPO / rel).read_text(encoding="utf-8"), rel).body if isinstance(node, ast.ClassDef) and node.name == name]
    assert len(classes) == 1, f"{rel} defines {name} {len(classes)} times"
    bases = [ast.unparse(base) for base in classes[0].bases]
    assert bases == ["Exception"], f"{rel}: {name}({', '.join(bases)}) - derive it from Exception"


def _malformed_runs(tmp_path: Path) -> "dict[str, list[str]]":
    # One malformed input per user-facing CLI, each refused before it touches a toolchain, a device or the repo tree.
    bad_toml = tmp_path / "bad.toml"
    bad_toml.write_text("[[[\n", encoding="utf-8")
    empty = tmp_path / "empty"
    empty.mkdir()
    return {
        "build_firmware": ["scripts/build_firmware.py", "zz_no_such_device", "--toolchain-dir", str(empty)],
        "setup_toolchain": ["toolchain/setup_toolchain.py", "test", "--toolchain-dir", str(empty)],
        "buildgen.generate": ["-m", "buildgen.generate", str(bad_toml)],
        "buildgen.definitions": ["-m", "buildgen.definitions", str(bad_toml)],
        "_generate_sensortask_modules": ["scripts/_generate_sensortask_modules.py", "--device-toml", str(bad_toml), "--out-dir", str(tmp_path / "out")],
        "_stage_website": ["scripts/_stage_website.py", "--build-date", "yesterday", str(tmp_path / "definitions.json"), str(tmp_path / "stage")],
        "_render_coverage": ["scripts/_render_coverage.py", "--raw-dir", str(empty)],
    }


_CLIS = ("build_firmware", "setup_toolchain", "buildgen.generate", "buildgen.definitions", "_generate_sensortask_modules", "_stage_website", "_render_coverage")


@pytest.mark.parametrize("cli", _CLIS)
def test_a_malformed_input_is_one_line_and_exit_1_without_a_traceback(cli: str, tmp_path: Path) -> None:
    argv = _malformed_runs(tmp_path)[cli]
    done = subprocess.run([sys.executable, *argv], cwd=_REPO, capture_output=True, text=True, check=False, timeout=_TIMEOUT_S)
    assert "Traceback" not in done.stdout + done.stderr, done.stderr
    assert done.returncode == 1, (done.returncode, done.stderr)
    lines = done.stderr.strip().splitlines()
    assert len(lines) == 1, f"{cli} printed {len(lines)} stderr lines: {done.stderr}"
    assert not (tmp_path / "stage").exists() and not (tmp_path / "out").exists(), "a refused run wrote its output"

