"""Every FRAM chunk in src/ is created with a real CRC (SPECIFICATION.md A.4): with the manager's
pass-through default any bytes behind an idle status byte read as valid, another owner's included,
since the owner seed has no CRC to act on. Checked by `ast` over every chunk-creating call."""

import ast
from pathlib import Path

import pytest

_CHUNK_CALLS = frozenset({"get_chunk", "get_timestamped_chunk"})
_REAL_CRCS = frozenset({"CRC8", "CRC16", "CRC32"})
_CRC_MODULE = "asy_crc_checks"
_BITE_HEAD = "from asy_crc_checks import CRC8, CRC16 as C16, CRCPass\nimport asy_crc_checks\n"


def _is_real_crc(value: ast.expr, imported: "set[str]") -> bool:
    if not (isinstance(value, ast.Call) and not value.args and not value.keywords):
        return False
    func = value.func
    if isinstance(func, ast.Name):
        return func.id in imported
    return isinstance(func, ast.Attribute) and func.attr in _REAL_CRCS and isinstance(func.value, ast.Name) and func.value.id == _CRC_MODULE


def _chunk_calls(tree: ast.Module) -> "list[ast.Call]":
    return [n for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr in _CHUNK_CALLS]


def _crc_names_imported(tree: ast.Module) -> "set[str]":
    # The local names this module binds to asy_crc_checks' real CRC classes (an alias counts as its class).
    return {alias.asname or alias.name for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module == _CRC_MODULE for alias in n.names if alias.name in _REAL_CRCS}


def _crc_problems(label: str, source: str) -> "list[str]":
    tree = ast.parse(source)
    imported = _crc_names_imported(tree)
    problems = []
    for call in _chunk_calls(tree):
        assert isinstance(call.func, ast.Attribute)
        crc = next((kw.value for kw in call.keywords if kw.arg == "crc"), None)
        if crc is None or not _is_real_crc(crc, imported):
            shown = "no crc=" if crc is None else f"crc={ast.unparse(crc)}"
            problems.append(f"{label}:{call.lineno}: {call.func.attr}() with {shown}, expected crc= one of {sorted(_REAL_CRCS)}() from {_CRC_MODULE}")
    return problems


def _src_sources(repo_root: Path) -> "list[tuple[str, str]]":
    return [(f"src/{p.name}", p.read_text()) for p in sorted((repo_root / "src").glob("*.py"))]


def test_every_fram_chunk_in_src_is_created_with_a_real_crc(repo_root: Path) -> None:
    sources = _src_sources(repo_root)
    calls = sum(len(_chunk_calls(ast.parse(text))) for _label, text in sources)
    assert calls >= 2, "found fewer chunk-creating calls in src/ than the logger store and the SGP40 backup make: the scan has gone blind"
    problems = [p for label, text in sources for p in _crc_problems(label, text)]
    assert not problems, "\n".join(problems)


@pytest.mark.parametrize(
    "call",
    [
        "fram.get_chunk(8, owner='X')",
        "fram.get_chunk(8, crc=None, owner='X')",
        "fram.get_chunk(8, crc=CRCPass(), owner='X')",
        "fram.get_chunk(8, CRC8(), owner='X')",
        "fram.get_timestamped_chunk(8, synced, owner='X')",
        "fram.get_timestamped_chunk(8, synced, crc=make_crc(), owner='X')",
    ],
)
def test_the_crc_check_bites(call: str) -> None:
    assert _crc_problems("src/asy_x.py", _BITE_HEAD + call + "\n")


@pytest.mark.parametrize(
    "call",
    [
        "fram.get_chunk(8, crc=CRC8(), owner='X')",
        "fram.get_chunk(8, crc=C16(), owner='X')",
        "fram.get_timestamped_chunk(8, synced, crc=asy_crc_checks.CRC32(), owner='X')",
    ],
)
def test_the_crc_check_passes_a_real_crc(call: str) -> None:
    assert not _crc_problems("src/asy_x.py", _BITE_HEAD + call + "\n")
