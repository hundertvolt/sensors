"""Every bare python3 a script runs is version-checked first (scripts/_require_python.sh): require_python311 passes
3.11 and newer silently and fails a 3.10 or a missing python3 naming the calling script, the version found and the fix;
each scripts/*.sh runs it before its first bare python3; build_frozen_html.sh stops on it before writing anything."""

import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
_LIB = REPO_ROOT / "scripts" / "_require_python.sh"
_TIMEOUT_S = 30
# A python3 reporting itself as 3.10: any -c probe runs under this suite's interpreter with version_info replaced;
# anything else it is asked to run is recorded and fails, so a script that got past its check is seen.
_STUB_PYTHON = """#!{python} -I
import sys
class _Version(tuple):
    major, minor, micro = 3, 10, 0
if sys.argv[1:2] == ["-c"] and len(sys.argv) > 2:
    code = sys.argv[2]
    sys.argv = ["-c", *sys.argv[3:]]
    sys.version_info = _Version((3, 10, 0, "final", 0))
    exec(compile(code, "<probe>", "exec"), {{"__name__": "__main__"}})
    sys.exit(0)
with open({calls!r}, "a", encoding="utf-8") as calls:
    calls.write("python3 " + " ".join(sys.argv[1:]) + "\\n")
sys.exit(97)
"""
_STUB_COMMANDS = ("bash", "cat", "cp", "dirname", "basename", "mkdir", "mktemp", "rm", "head", "sed", "grep", "tr", "cut", "ls", "env", "gzip", "mv", "touch", "date")
_CALL = re.compile(r"(?<![\w./-])python3(?![\w.-])")
_HEREDOC = re.compile(r"(?<!<)<<-?\s*['\"]?(\w+)['\"]?")
_QUOTED = re.compile(r"\"(?:[^\"\\]|\\.)*\"|'[^']*'")


def _bare_python3_lines(text: str) -> list[int]:
    # The lines that run a bare python3: outside comments, heredoc bodies and quoted text, and not through uv run.
    found, terminator = [], ""
    for number, line in enumerate(text.splitlines(), 1):
        if terminator:
            terminator = "" if line.strip() == terminator else terminator
            continue
        raw = line.split(" #", 1)[0]
        code = _QUOTED.sub("''", raw)
        if code.lstrip().startswith("#"):
            continue
        if _CALL.search(code) and not re.search(r"\buv run\b[^|;&]*python3", code):
            found.append(number)
        heredoc = _HEREDOC.search(raw)
        if heredoc:
            terminator = heredoc.group(1)
    return found


def _check_lines(text: str) -> list[int]:
    return [n for n, line in enumerate(text.splitlines(), 1) if re.match(r"\s*require_python311\b", line)]


def _require(env_path: str) -> subprocess.CompletedProcess[str]:
    # A caller script sourcing the library, as the runners do, under the PATH given.
    body = "\n".join(["set -euo pipefail", f"source {shlex.quote(str(_LIB))}", "require_python311", "echo checked"])
    return subprocess.run(["/bin/bash", "-c", body, "scripts/caller.sh"], env={"PATH": env_path}, capture_output=True, text=True, check=False, timeout=_TIMEOUT_S)


def _stub_bin(tmp_path: Path) -> tuple[Path, Path]:
    # A PATH directory whose python3 reports 3.10, beside wrappers for the commands a build script needs.
    bin_dir, calls = tmp_path / "stub_bin", tmp_path / "python3.calls"
    bin_dir.mkdir()
    for name in _STUB_COMMANDS:
        target = shutil.which(name)
        if target is not None:
            (bin_dir / name).write_text(f'#!/bin/sh\nexec "{target}" "$@"\n', encoding="utf-8")
            (bin_dir / name).chmod(0o755)
    (bin_dir / "python3").write_text(_STUB_PYTHON.format(python=sys.executable, calls=str(calls)), encoding="utf-8")
    (bin_dir / "python3").chmod(0o755)
    return bin_dir, calls


def test_a_new_enough_python3_passes_silently() -> None:
    done = _require(f"{Path(sys.executable).parent}:/usr/bin:/bin")
    assert (done.returncode, done.stdout, done.stderr) == (0, "checked\n", "")


def test_a_3_10_python3_fails_naming_the_caller_the_version_and_the_fix(tmp_path: Path) -> None:
    bin_dir, calls = _stub_bin(tmp_path)
    done = _require(str(bin_dir))
    assert (done.returncode, done.stdout) == (1, ""), done
    assert done.stderr.strip() == "error: scripts/caller.sh needs python3 >= 3.11 (tomllib, datetime.UTC) - the python3 on PATH is 3.10; fix: activate the uv venv (uv sync) or put a newer python3 first on PATH"
    assert not calls.exists(), calls.read_text(encoding="utf-8")


def test_no_python3_on_path_fails_naming_that(tmp_path: Path) -> None:
    empty = tmp_path / "empty_bin"
    empty.mkdir()
    done = _require(str(empty))
    assert (done.returncode, done.stdout) == (1, ""), done
    assert done.stderr.strip() == "error: scripts/caller.sh needs python3 >= 3.11 (tomllib, datetime.UTC) - no python3 is on PATH; fix: activate the uv venv (uv sync) or put a newer python3 first on PATH"


def test_the_library_refuses_to_run_as_a_script() -> None:
    done = subprocess.run(["/bin/bash", str(_LIB)], capture_output=True, text=True, check=False, timeout=_TIMEOUT_S)
    assert (done.returncode, done.stderr.strip()) == (2, "error: source scripts/_require_python.sh, do not run it")


def test_the_scan_sees_each_bare_python3_and_nothing_else() -> None:
    text = (
        "# python3 in a comment\n"
        'echo "needs python3 >= 3.11"\n'
        'PYTHONPATH="ext" python3 -m freezefs a b\n'
        "uv run python3 -c pass\n"
        "python3 <<'PYEOF'\n"
        "python3 -m inside_the_heredoc\n"
        "PYEOF\n"
        "x=$(python3 -c pass)\n"
    )
    assert _bare_python3_lines(text) == [3, 5, 8]


@pytest.mark.parametrize("script", sorted(p.relative_to(REPO_ROOT).as_posix() for p in (REPO_ROOT / "scripts").glob("*.sh") if p != _LIB))
def test_every_bare_python3_comes_after_the_version_check(script: str) -> None:
    text = (REPO_ROOT / script).read_text(encoding="utf-8")
    checks = _check_lines(text)
    unchecked = [line for line in _bare_python3_lines(text) if not any(check < line for check in checks)]
    assert not unchecked, f"{script} runs a bare python3 at line(s) {unchecked} before any require_python311 (source scripts/_require_python.sh)"


def test_build_frozen_html_stops_on_a_3_10_python3_before_writing_anything(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    shutil.copytree(REPO_ROOT / "scripts", root / "scripts", ignore=shutil.ignore_patterns("__pycache__"))
    source = tmp_path / "site"
    source.mkdir()
    (source / "index.html").write_text("<!doctype html>\n", encoding="utf-8")
    out = tmp_path / "out" / "frozen_html.py"
    bin_dir, calls = _stub_bin(tmp_path)
    env = {"PATH": str(bin_dir), "HOME": str(tmp_path), "HTML_SRC_DIRS": str(source)}
    done = subprocess.run([str(bin_dir / "bash"), str(root / "scripts" / "build_frozen_html.sh"), str(out)], cwd=root, env=env, capture_output=True, text=True, check=False, timeout=_TIMEOUT_S)
    assert done.returncode == 1, done
    assert "needs python3 >= 3.11 (tomllib, datetime.UTC) - the python3 on PATH is 3.10" in done.stderr, done.stderr
    assert not calls.exists(), f"build_frozen_html.sh ran python3 past its check: {calls.read_text(encoding='utf-8')}"
    assert not out.parent.exists(), "build_frozen_html.sh touched its output before the check"
