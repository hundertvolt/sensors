"""A filesystem module never shadows a frozen one: the boot entry's own path lines, read from its generator, put the
frozen modules ahead of a planted asyncio.py on the Unix port; without them the planted copy wins (the premise)."""

import ast
import os
import subprocess
from pathlib import Path

from buildgen.codegen import generate_boot_entry_source

_PLANTED = 'print("SHADOWED")\n'
_PROBE = 'import asyncio\nprint("FILE", asyncio.__file__)\n'
# A frozen module's __file__ is its manifest path, the .frozen/ prefix stripped (py/builtinimport.c:228, v1.29.0).
_FROZEN_FILE = "FILE asyncio/__init__.py"


def _path_lines() -> str:
    # The boot entry's `import sys` and its `sys.path.insert(0, ".frozen")`, as the generator writes them.
    tree = ast.parse(generate_boot_entry_source("fixture_device"))
    found = [
        node for node in tree.body
        if (isinstance(node, ast.Import) and [a.name for a in node.names] == ["sys"])
        or (isinstance(node, ast.Expr) and ast.unparse(node).startswith("sys.path.insert("))
    ]
    assert [ast.unparse(node) for node in found] == ["import sys", "sys.path.insert(0, '.frozen')"], [ast.unparse(n) for n in found]
    return "".join(ast.unparse(node) + "\n" for node in found)


def _run(micropython_bin: Path, cwd: Path, source: str) -> str:
    (cwd / "asyncio.py").write_text(_PLANTED, encoding="utf-8")
    (cwd / "probe.py").write_text(source, encoding="utf-8")
    env = {key: value for key, value in os.environ.items() if key != "MICROPYPATH"}  # the port's own default path
    done = subprocess.run([str(micropython_bin), "probe.py"], cwd=cwd, env=env, capture_output=True, text=True, timeout=60, check=False)
    assert done.returncode == 0, done.stdout + done.stderr
    return done.stdout


def test_without_the_path_lines_a_planted_asyncio_shadows_the_frozen_one(micropython_bin: Path, tmp_path: Path) -> None:
    # The premise: the script's directory comes first on the port's default path.
    out = _run(micropython_bin, tmp_path, _PROBE)
    assert "SHADOWED" in out and _FROZEN_FILE not in out, out


def test_the_boot_entrys_path_lines_load_the_frozen_asyncio(micropython_bin: Path, tmp_path: Path) -> None:
    out = _run(micropython_bin, tmp_path, _path_lines() + _PROBE)
    assert "SHADOWED" not in out and _FROZEN_FILE in out, out
