"""SPECIFICATION.md A.11 names every unauthenticated write the firmware accepts: each PUT route, each SystemCmd word,
each dispatch field of every device."""

import ast
import functools
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from _devices import DEVICE_NAMES, device_toml

from buildgen.definitions import definitions_for_toml

if TYPE_CHECKING:
    from collections.abc import Iterable

    from buildgen.jsontypes import JsonValue

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SPEC = _REPO_ROOT / "SPECIFICATION.md"
_SRC = _REPO_ROOT / "src"
_WEBSERVER = _SRC / "asy_webserver_service.py"
_HEADING = "## A.11 "
# The floors: a derivation that broke and found nothing fails here instead of passing every check vacuously.
_MIN_PUT_ROUTES = 5
_SYSTEM_CMD_FLOOR = ("bootloader", "erasefram", "mempause", "reboot", "resetconfig")
_DISPATCH_FLOOR = ("ResetErrors", "SystemCmd")


def _a11_text() -> str:
    # A.11 from its heading to the next `## ` or `---` line; a section with no such end would read the whole rest of SPEC.
    lines = _SPEC.read_text(encoding="utf-8").splitlines()
    start = next((i for i, line in enumerate(lines) if line.startswith(_HEADING)), None)
    if start is None:
        pytest.fail(f"{_SPEC.name} has no '{_HEADING.strip()}' heading: the threat model's section is missing")
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("## ") or lines[i].rstrip() == "---"), None)
    if end is None:
        pytest.fail(f"{_SPEC.name}'s '{_HEADING.strip()}' runs to the end of the file: no `## ` or `---` line ends it")
    return "\n".join(lines[start:end])


@functools.cache
def _dispatch_fields() -> "tuple[str, ...]":
    # Every field key carrying "dispatch": true in any device's generated definitions, sub-fields included, union over devices.
    found: set[str] = set()
    for device in DEVICE_NAMES:
        stack: list[JsonValue] = [definitions_for_toml(device_toml(device), _SRC)]
        while stack:
            node = stack.pop()
            if isinstance(node, dict):
                key = node.get("key")
                if node.get("dispatch") is True and isinstance(key, str):
                    found.add(key)
                stack.extend(node.values())
            elif isinstance(node, list):
                stack.extend(node)
    return tuple(sorted(found))


def _missing(text: str, names: "Iterable[str]") -> "list[str]":
    # The names text does not carry as a code span, sorted.
    return sorted(name for name in set(names) if f"`{name}`" not in text)


def _module_literal(name: str) -> object:
    # A module-level `name = ...` or `name = const(...)` of the webserver, read from source as buildgen reads ROUTES.
    for node in ast.parse(_WEBSERVER.read_text(encoding="utf-8")).body:
        if isinstance(node, ast.Assign) and [ast.unparse(t) for t in node.targets] == [name]:
            value = node.value
            if isinstance(value, ast.Call) and ast.unparse(value.func) == "const" and len(value.args) == 1:
                value = value.args[0]
            return ast.literal_eval(value)
    pytest.fail(f"{_WEBSERVER.name} assigns no module-level {name}")


def _put_paths() -> "list[str]":
    # The paths of ROUTES' PUT rows, each row (method, path, handler name).
    rows = _module_literal("ROUTES")
    assert isinstance(rows, tuple), f"ROUTES in {_WEBSERVER.name} is a {type(rows).__name__}, not a tuple of rows"
    paths: list[str] = []
    for row in rows:
        match row:
            case (str() as method, str() as path, str()):
                if method == "PUT":
                    paths.append(path)
            case _:
                pytest.fail(f"ROUTES row {row!r} in {_WEBSERVER.name} is not (method, path, handler name)")
    return paths


def _system_cmd_words() -> "list[str]":
    # The string elements of _SYSTEM_CMDS, the only words system_cmd() is ever handed.
    words = _module_literal("_SYSTEM_CMDS")
    assert isinstance(words, tuple), f"_SYSTEM_CMDS in {_WEBSERVER.name} is a {type(words).__name__}, not a tuple"
    return [word for word in words if isinstance(word, str)]


def test_a11_names_every_put_route() -> None:
    paths = _put_paths()
    assert len(paths) >= _MIN_PUT_ROUTES and "/system" in paths, f"ROUTES yielded the PUT paths {paths}: the derivation broke"
    missing = _missing(_a11_text(), paths)
    assert not missing, f"SPECIFICATION.md A.11 does not name the PUT route(s) {missing} - add each to its unauthenticated-writes row"


def test_a11_names_every_system_command_word() -> None:
    words = _system_cmd_words()
    assert sorted(words) == list(_SYSTEM_CMD_FLOOR), f"_SYSTEM_CMDS yielded {words}: a new word joins this floor and A.11 in one change"
    missing = _missing(_a11_text(), words)
    assert not missing, f"SPECIFICATION.md A.11 does not name the SystemCmd word(s) {missing} - add each to its unauthenticated-writes row"


def test_a11_names_every_dispatch_field() -> None:
    fields = _dispatch_fields()
    assert set(_DISPATCH_FLOOR) <= set(fields), f"the generated definitions yielded the dispatch fields {list(fields)}: the derivation broke"
    missing = _missing(_a11_text(), fields)
    assert not missing, f"SPECIFICATION.md A.11 does not name the dispatch field(s) {missing} - add each to its unauthenticated-writes row"


def test_the_check_bites() -> None:
    assert _missing("... `reboot` ... `mempause` ...", ["reboot", "erasefram", "mempause"]) == ["erasefram"]
