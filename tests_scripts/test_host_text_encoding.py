"""Every host text read or write (host_typecheck.ini's trees) names its encoding as a literal - open() and Path.open()
in text mode, Path.read_text() and Path.write_text() - so a non-UTF-8 locale cannot fail or misdecode this repo's own
UTF-8 text (agent, 2026-10-15); subprocess text streams stay out of scope, as in ruff's PLW1514."""

import ast
import configparser
from functools import cache

import pytest
from _repo_scan import REPO_ROOT, repo_files, statement_nodes

SCOPES = ("buildgen/", "scripts/", "toolchain/", "tests_scripts/", "tests_hardware/")
# Inputs a test reads, and the device scripts the board runs: not host code.
_NOT_HOST = ("tests_scripts/buildgen_fixtures/", "tests_hardware/device_scripts/")
_PATH_TEXT_METHODS = frozenset({"read_text", "write_text"})


def _is_text_mode(call: ast.Call, mode_index: int) -> bool:
    # No mode reads text; a mode that is not a literal cannot be shown binary, so it counts as text.
    mode = call.args[mode_index] if len(call.args) > mode_index else next((kw.value for kw in call.keywords if kw.arg == "mode"), None)
    return mode is None or not (isinstance(mode, ast.Constant) and isinstance(mode.value, str) and "b" in mode.value)


def _module_names(tree: ast.Module) -> set[str]:
    # Names an `import` binds: `os.open()` or a helper module's own `read_text()` is a module function, not a Path method.
    return {(alias.asname or alias.name).split(".")[0] for node in statement_nodes(tree) if isinstance(node, ast.Import) for alias in node.names}


def _opens_text(call: ast.Call, modules: set[str]) -> bool:
    func = call.func
    if isinstance(func, ast.Name):
        return func.id == "open" and _is_text_mode(call, 1)
    if not isinstance(func, ast.Attribute):
        return False
    module = func.value.id if isinstance(func.value, ast.Name) and func.value.id in modules else None
    if func.attr in _PATH_TEXT_METHODS:
        return module is None
    if func.attr != "open":
        return False
    # Path.open(mode, ...) takes the mode first; io.open() is the builtin; any other module's open() is no text stream.
    return _is_text_mode(call, 0) if module is None else module == "io" and _is_text_mode(call, 1)


@cache
def scoped_files() -> tuple[str, ...]:
    return tuple(p for p in repo_files() if p.endswith(".py") and p.startswith(SCOPES) and not p.startswith(_NOT_HOST))


def text_io_calls(source: str, rel: str) -> list[tuple[str, bool]]:
    # (file:line and the call, whether it names a literal encoding=) for every text-mode open, read_text and write_text;
    # None or a name passed through decodes by whatever its caller chose, the locale included.
    if source.isascii() and not any(name in source for name in ("open", *_PATH_TEXT_METHODS)):
        return []  # an ASCII name is spelled out where it is called, so there is no call to find
    tree = ast.parse(source, rel)
    modules = _module_names(tree)
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and _opens_text(node, modules):
            call = ast.unparse(node)
            site = f"{rel}:{node.lineno}: {call if len(call) <= 100 else call[:97] + '...'}"
            encoding = next((kw.value for kw in node.keywords if kw.arg == "encoding"), None)
            found.append((node.lineno, node.col_offset, site, isinstance(encoding, ast.Constant) and isinstance(encoding.value, str)))
    return [(site, encoded) for _, _, site, encoded in sorted(found)]


def test_every_host_text_read_and_write_names_its_encoding() -> None:
    sites = [site for rel in scoped_files() for site, encoded in text_io_calls((REPO_ROOT / rel).read_text(encoding="utf-8"), rel) if not encoded]
    assert not sites, 'give each host text read or write a literal encoding="utf-8":\n' + "\n".join(sites)


def test_the_scan_is_not_empty() -> None:
    # A scope that lists no file, or a tree with no matched call, is a scan that silently stopped looking.
    files = scoped_files()
    assert not [scope for scope in SCOPES if not any(p.startswith(scope) for p in files)], f"no Python file under one of {SCOPES}"
    assert all((REPO_ROOT / prefix).is_dir() for prefix in _NOT_HOST), f"an exclusion names no directory: {_NOT_HOST}"
    assert any(text_io_calls((REPO_ROOT / rel).read_text(encoding="utf-8"), rel) for rel in files), "no text read or write matched"


def test_the_scopes_are_the_host_type_check_pass_files() -> None:
    # Every host Python tree host_typecheck.ini checks is host code here too; the device scripts run on the board.
    parser = configparser.ConfigParser()
    parser.read(REPO_ROOT / "host_typecheck.ini", encoding="utf-8")
    assert sorted(SCOPES) == sorted(f"{name.strip()}/" for name in parser["mypy"]["files"].split(","))
    assert any(p.startswith("tests_hardware/") for p in scoped_files())
    assert not [p for p in scoped_files() if p.startswith("tests_hardware/device_scripts/")]


def test_a_non_ascii_source_is_always_parsed() -> None:
    # Python folds a name to NFKC, so a fullwidth open is open although the text never spells it.
    assert text_io_calls("def f(p):\n    return \uff4f\uff50\uff45\uff4e(p)\n", "planted.py") == [("planted.py:2: open(p)", False)]


@pytest.mark.parametrize(
    ("call", "flagged"),
    [
        ("open(p)", True),
        ("open(p, 'w')", True),
        ("open(p, mode='a')", True),
        ("open(p, mode)", True),
        ("open(p, 'rb')", False),
        ("open(p, 'w', encoding='utf-8')", False),
        ("p.open()", True),
        ("(root / 'x.toml').open('a+')", True),
        ("p.open('rb')", False),
        ("p.open(mode='w', encoding='utf-8')", False),
        ("p.read_text()", True),
        ("p.read_text(**options)", True),
        ("p.read_text(encoding='utf-8')", False),
        ("p.write_text(text)", True),
        ("p.write_text(text, encoding='utf-8')", False),
        ("open(p, 'w', encoding=None)", True),
        ("p.read_text(encoding=mode)", True),
        ("p.open('w', encoding=options['encoding'])", True),
        ("io.open(p, 'w')", True),
        ("os.open(p, os.O_RDONLY)", False),
        ("helpers.read_text(p)", False),
        ("read_text(p)", False),
        ("subprocess.run(['true'], text=True)", False),
    ],
)
def test_the_check_bites(call: str, *, flagged: bool) -> None:
    source = f"import io\nimport os\nimport subprocess\n\nimport helpers\n\n\ndef f(p, root, text, mode, options):\n    return {call}\n"
    assert [site for site, encoded in text_io_calls(source, "planted.py") if not encoded] == ([f"planted.py:9: {call}"] if flagged else []), call
