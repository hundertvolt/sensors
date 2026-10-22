"""One shell convention over scripts/*.sh: `#!/usr/bin/env bash`, `set -euo pipefail` first (or a set line saying why),
a sourced helper setting no option of its caller's, one EXIT trap armed before any mktemp, no loop over an unquoted
expansion, `-h|--help` exit 0, an unknown argument refused with exit 2 naming it before any tool runs (sandboxed)."""

import re
import shutil
import subprocess
from pathlib import Path

import pytest
from _devices import DEVICE_NAMES

REPO_ROOT = Path(__file__).resolve().parent.parent
_SCRIPTS = sorted(p.relative_to(REPO_ROOT).as_posix() for p in (REPO_ROOT / "scripts").glob("*.sh"))
_SHEBANG = "#!/usr/bin/env bash"
_STRICT = "set -euo pipefail"
_UNKNOWN = "--not-an-option"
_TIMEOUT_S = 30
_SET_OPTIONS = re.compile(r"^\s*set\s+[-+]")
_EXIT_TRAP = re.compile(r"^\s*trap\s+(?!-\s)\S.*\bEXIT\b")
_MKTEMP = re.compile(r"\bmktemp\b")
_FOR_IN = re.compile(r"^\s*for\s+\w+\s+in\s+(?P<words>.*?)\s*(?:;\s*do\b.*)?$")
_HEREDOC = re.compile(r"(?<!<)<<-?\s*['\"]?(\w+)['\"]?")
_COMMAND_PATH = re.compile(r"^if\s.*BASH_SOURCE\[0\].*\$0")
# A usage line whose tail goes to another tool (pytest, mpremote, the twin) declares that tool's arguments its own.
_FORWARDED_TAIL = re.compile(r"\[[^\]]*\b(?:args|arguments|forwarded)\b[^\]]*\]")
# The only real commands a sandboxed run finds; everything that builds, installs, syncs or reaches a board is a stub
# that records its call and fails, so a script that gets past its argument check is seen.
_REAL_COMMANDS = ("bash", "sh", "env", "dirname", "basename", "cat", "sed", "grep", "awk", "head", "tail", "tr", "cut", "sort", "uniq", "comm", "wc", "printf", "realpath", "readlink", "uname", "id", "date", "ls", "mkdir", "rm", "rmdir", "mktemp", "sleep", "seq", "nproc", "tee", "touch", "cp", "mv", "chmod", "ln", "stat", "find", "xargs", "true", "false", "sha256sum")
_STUB_COMMANDS = ("uv", "python", "python3", "node", "npm", "npx", "mpremote", "picotool", "pytest", "sudo", "nmcli", "iw", "iptables", "setcap", "apt-get", "git", "make", "curl", "wget", "gzip", "flock", "timeout", "stdbuf", "mypy", "ruff", "shellcheck", "actionlint", "zizmor", "systemctl", "xvfb-run")


def _is_callable(lines: list[str]) -> bool:
    return any(_COMMAND_PATH.match(line) for line in lines)


def _is_sourced(lines: list[str]) -> bool:
    # A helper says so in its header's first line; the convention reads that, not the file name.
    header = _header(lines)
    return bool(header) and header[0].startswith("# Sourced")


def _code_lines(lines: list[str]) -> list[tuple[int, str]]:
    # (line, text) of every line that starts as shell code: comments, heredoc bodies and lines that begin inside a
    # quoted string spanning lines (a `-c` program, say) left out.
    found, terminator, quote = [], "", ""
    for number, line in enumerate(lines, 1):
        if terminator:
            terminator = "" if line.strip() == terminator else terminator
            continue
        starts_inside, quote = bool(quote), _quote_after(line, quote)
        if starts_inside or line.lstrip().startswith("#"):
            continue
        found.append((number, line))
        heredoc = _HEREDOC.search(line)
        if heredoc:
            terminator = heredoc.group(1)
    return found


def _header(lines: list[str]) -> list[str]:
    header = []
    for line in lines[1:]:
        if not line.startswith("#"):
            break
        header.append(line)
    return header


def _quote_after(line: str, quote: str) -> str:
    # The quote still open at the end of the line, given the one open at its start; a comment ends the scan.
    index = 0
    while index < len(line):
        char = line[index]
        if quote == "'":
            quote = "" if char == "'" else quote
        elif char == "\\":
            index += 1
        elif quote:
            quote = "" if char == '"' else quote
        elif char in "\"'":
            quote = char
        elif char == "#" and (index == 0 or line[index - 1] in " \t;"):
            break
        index += 1
    return quote


def _run(sandbox: Path, tmp_path: Path, script: str, *args: str) -> tuple[subprocess.CompletedProcess[str], list[str]]:
    calls = tmp_path / "stub.calls"
    env = {"PATH": str(sandbox / ".stub_bin"), "HOME": str(tmp_path / "home"), "STUB_CALLS": str(calls), "XDG_RUNTIME_DIR": str(tmp_path)}
    done = subprocess.run([str(sandbox / ".stub_bin" / "bash"), str(sandbox / script), *args], cwd=sandbox, env=env, stdin=subprocess.DEVNULL, capture_output=True, text=True, check=False, timeout=_TIMEOUT_S)
    return done, calls.read_text(encoding="utf-8").splitlines() if calls.exists() else []


def _runnable(scripts: list[str]) -> list[str]:
    # Every script a user runs: all but the sourced helpers that refuse to run as a command.
    found = []
    for script in scripts:
        lines = (REPO_ROOT / script).read_text(encoding="utf-8").splitlines()
        if not _is_sourced(lines) or _is_callable(lines):
            found.append(script)
    return found


def _unquoted_expansion(words: str) -> str | None:
    # The word list from its first `$` outside quotes on: a word-split, glob-expanded expansion.
    quote = ""
    for index, char in enumerate(words):
        if quote:
            quote = "" if char == quote and words[index - 1] != "\\" else quote
        elif char in "\"'":
            quote = char
        elif char == "$":
            return words[index:]
    return None


def _usage_line(text: str) -> str:
    found = re.search(r"Usage: (.*)", text)
    return found.group(1) if found else ""


def convention_problems(path: Path, name: str) -> list[str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    code = _code_lines(lines)
    problems = [] if lines and lines[0] == _SHEBANG else [f"{name}:1: line 1 is not {_SHEBANG}"]
    sourced = _is_sourced(lines)
    if not sourced:
        first = next(((n, text) for n, text in code if n > 1), (0, ""))
        stated = first[1].startswith("set ") and " # " in first[1]
        if first[1].split(" #", 1)[0].rstrip() != _STRICT and not stated:
            problems.append(f"{name}:{first[0]}: the first command is {first[1].strip()!r}, not `set -euo pipefail` or a set line stating why on that line")
    else:
        guard = next((n for n, text in code if _COMMAND_PATH.match(text)), None)
        problems += [
            f"{name}:{n}: a sourced script sets shell options outside its command path - they would change its caller's"
            for n, text in code
            if _SET_OPTIONS.match(text) and (guard is None or n < guard or not text.startswith((" ", "\t")))
        ]
    traps = [n for n, text in code if _EXIT_TRAP.match(text)]
    if sourced:
        problems += [f"{name}:{n}: a sourced script arms an EXIT trap - it would replace its caller's" for n in traps]
    elif len(traps) > 1:
        problems.append(f"{name}: {len(traps)} EXIT traps (lines {', '.join(map(str, traps))}) - one trap removes every temporary file")
    for n, text in code:
        if _MKTEMP.search(text) and not sourced and (not traps or n < traps[0]):
            problems.append(f"{name}:{n}: mktemp before the EXIT trap that removes it (line {traps[0]})" if traps else f"{name}:{n}: mktemp with no EXIT trap to remove it")
    for n, text in code:
        loop = _FOR_IN.match(text)
        word = _unquoted_expansion(loop.group("words")) if loop and not text.lstrip().startswith("for ((") else None
        if word is not None:
            problems.append(f"{name}:{n}: a loop over an unquoted expansion ({word})")
    return problems
@pytest.fixture(scope="module")
def sandbox(tmp_path_factory: pytest.TempPathFactory) -> Path:
    # A copy of scripts/ and devices/ with a PATH of real basics and recording stubs: no run reaches this checkout.
    root = tmp_path_factory.mktemp("conventions")
    shutil.copytree(REPO_ROOT / "scripts", root / "scripts", ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(REPO_ROOT / "devices", root / "devices")
    stub_bin = root / ".stub_bin"
    stub_bin.mkdir()
    for name in _REAL_COMMANDS:
        target = shutil.which(name)
        if target is not None:
            (stub_bin / name).write_text(f'#!/bin/sh\nexec "{target}" "$@"\n', encoding="utf-8")
    for name in _STUB_COMMANDS:
        (stub_bin / name).write_text(f'#!/bin/sh\necho "{name} $*" >> "$STUB_CALLS"\nexit 97\n', encoding="utf-8")
    for stub in stub_bin.iterdir():
        stub.chmod(0o755)
    return root


@pytest.mark.parametrize("script", _SCRIPTS)
def test_every_script_follows_the_static_convention(script: str) -> None:
    assert convention_problems(REPO_ROOT / script, script) == []


@pytest.mark.parametrize("script", _runnable(_SCRIPTS))
@pytest.mark.parametrize("flag", ["-h", "--help"])
def test_help_exits_0_with_the_usage_before_running_anything(sandbox: Path, tmp_path: Path, script: str, flag: str) -> None:
    done, calls = _run(sandbox, tmp_path, script, flag)
    assert done.returncode == 0, f"{script} {flag} exited {done.returncode}:\n{done.stdout}\n{done.stderr}"
    assert re.search(r"(?im)^usage:", done.stdout), f"{script} {flag} printed no usage block on stdout:\n{done.stdout}"
    assert calls == [], f"{script} {flag} ran {calls}"


@pytest.mark.parametrize("script", [s for s in _runnable(_SCRIPTS) if not _FORWARDED_TAIL.search(_usage_line((REPO_ROOT / s).read_text(encoding="utf-8")))])
def test_an_unknown_argument_exits_2_naming_it_before_running_anything(sandbox: Path, tmp_path: Path, script: str) -> None:
    done, calls = _run(sandbox, tmp_path, script, _UNKNOWN)
    assert calls == [], f"{script} {_UNKNOWN} got past its argument check and ran {calls}"
    assert done.returncode == 2, f"{script} {_UNKNOWN} exited {done.returncode}, not 2:\n{done.stderr}"
    assert _UNKNOWN in done.stderr, f"{script} refused {_UNKNOWN} without naming it:\n{done.stderr}"


@pytest.mark.parametrize(
    ("args", "named"),
    [((), "--device"), (("--device",), "--device"), (("--device", "no_such_device"), "no_such_device"), (("--device", "zz_test_x"), "zz_test_x")],
    ids=["no-argument", "no-value", "unknown-device", "fixture-device"],
)
def test_the_twin_runner_refuses_a_missing_or_unknown_device_naming_it_and_the_valid_ones(sandbox: Path, tmp_path: Path, args: tuple[str, ...], named: str) -> None:
    done, calls = _run(sandbox, tmp_path, "scripts/run_unix_port_integration.sh", *args)
    assert (done.returncode, calls) == (2, []), done
    assert named in done.stderr, done.stderr
    assert f"valid devices: {' '.join(DEVICE_NAMES)}" in done.stderr, done.stderr


def test_each_rule_bites_on_a_planted_script(tmp_path: Path) -> None:
    planted = tmp_path / "planted.sh"
    planted.write_text(
        "#!/bin/bash\n# Runs a thing.\nset -eu\nscratch=\"$(mktemp -d)\"\ntrap 'rm -rf \"$scratch\"' EXIT\ntrap 'echo bye' EXIT\n"
        'for f in $(ls); do :; done\nfor g in ${files[@]+"${files[@]}"}; do :; done\nfor h in "${files[@]}" devices/*.toml; do :; done\n',
        encoding="utf-8",
    )
    sourced = tmp_path / "sourced.sh"
    sourced.write_text("#!/usr/bin/env bash\n# Sourced helper.\nset -euo pipefail\ntrap 'rm -f x' EXIT\nf() {\n    set -x\n}\n", encoding="utf-8")
    callable_lib = tmp_path / "callable.sh"
    callable_lib.write_text('#!/usr/bin/env bash\n# Sourced, and callable as a command.\nf() { :; }\nif [ "${BASH_SOURCE[0]}" = "$0" ]; then\n    set -euo pipefail\n    f "$@"\nfi\n', encoding="utf-8")
    reasoned = tmp_path / "reasoned.sh"
    reasoned.write_text("#!/usr/bin/env bash\n# Runs a thing.\nset -uo pipefail  # not -e: the exit code is judged\n", encoding="utf-8")
    assert convention_problems(planted, "planted.sh") == [
        "planted.sh:1: line 1 is not #!/usr/bin/env bash",
        "planted.sh:3: the first command is 'set -eu', not `set -euo pipefail` or a set line stating why on that line",
        "planted.sh: 2 EXIT traps (lines 5, 6) - one trap removes every temporary file",
        "planted.sh:4: mktemp before the EXIT trap that removes it (line 5)",
        "planted.sh:7: a loop over an unquoted expansion ($(ls))",
        'planted.sh:8: a loop over an unquoted expansion (${files[@]+"${files[@]}"})',
    ]
    assert convention_problems(sourced, "sourced.sh") == [
        "sourced.sh:3: a sourced script sets shell options outside its command path - they would change its caller's",
        "sourced.sh:6: a sourced script sets shell options outside its command path - they would change its caller's",
        "sourced.sh:4: a sourced script arms an EXIT trap - it would replace its caller's",
    ]
    assert convention_problems(callable_lib, "callable.sh") == []
    assert convention_problems(reasoned, "reasoned.sh") == []


