"""Every key of the radio shape corpus (tests/_radio_shape_cases.json) has a product judge: the judge files' module-level
_JUDGED_SHAPES tuples, read by ast, together name exactly the corpus keys, and each file's own test iterates its tuple,
so a key no product check reads fails here (SPECIFICATION.md G.2)."""

import ast
import json
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent
_CORPUS = _ROOT / "tests" / "_radio_shape_cases.json"
_JUDGES = ("tests/test_asy_ntp_client.py", "tests/test_asy_wifi_service.py")
_TUPLE = "_JUDGED_SHAPES"


def _judged(source: str) -> "list[str]":
    # The corpus keys a judge file's _JUDGED_SHAPES names, after checking one test_* function iterates that tuple.
    tree = ast.parse(source)
    values = [n.value for n in tree.body if isinstance(n, ast.Assign) and [ast.unparse(t) for t in n.targets] == [_TUPLE]]
    assert len(values) == 1, f"{_TUPLE} assigned {len(values)} times at module level, not once"
    tests = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name.startswith("test_")]
    assert any(isinstance(n, ast.Name) and n.id == _TUPLE for t in tests for n in ast.walk(t)), f"no test iterates {_TUPLE}"
    return [shape for shape, _field in ast.literal_eval(values[0])]


def _problems(sources: "dict[str, str]", corpus: "dict[str, object]") -> "list[str]":
    judged = {path: _judged(source) for path, source in sources.items()}
    named = [key for keys in judged.values() for key in keys]
    problems = [f"{key}: judged by no product test" for key in sorted(set(corpus) - set(named))]
    problems += [f"{key}: judged but not in the corpus" for key in sorted(set(named) - set(corpus))]
    return problems + [f"{key}: judged twice" for key in sorted({key for key in named if named.count(key) > 1})]


def test_the_judge_files_together_judge_exactly_the_corpus_keys() -> None:
    sources = {path: (_ROOT / path).read_text(encoding="utf-8") for path in _JUDGES}
    assert _problems(sources, json.loads(_CORPUS.read_text(encoding="utf-8"))) == []


@pytest.mark.parametrize(
    ("planted", "expected"),
    [
        ('_JUDGED_SHAPES = (("a", "A"),)\n\n\ndef test_x():\n    for s, f in _JUDGED_SHAPES:\n        pass\n', ["b: judged by no product test"]),
        ('_JUDGED_SHAPES = (("a", "A"), ("b", "B"), ("c", "C"))\n\n\ndef test_x():\n    _JUDGED_SHAPES\n', ["c: judged but not in the corpus"]),
        ('_JUDGED_SHAPES = (("a", "A"), ("b", "B"), ("a", "A"))\n\n\ndef test_x():\n    _JUDGED_SHAPES\n', ["a: judged twice"]),
    ],
)
def test_a_planted_gap_fails_the_check(planted: str, expected: "list[str]") -> None:
    assert _problems({"tests/test_planted.py": planted}, {"a": {}, "b": {}}) == expected


@pytest.mark.parametrize(
    ("planted", "expected"),
    [
        ('_JUDGED_SHAPES = (("a", "A"),)\n\n\ndef test_x():\n    pass\n', "no test iterates"),
        ("def test_x():\n    pass\n", "assigned 0 times"),
    ],
)
def test_a_judge_file_without_an_iterated_tuple_fails_the_check(planted: str, expected: str) -> None:
    with pytest.raises(AssertionError, match=expected):
        _judged(planted)
