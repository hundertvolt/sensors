"""Tests for buildgen.source_ast: one parsed tree per source text, shared by every pass and device.
Sharing is only sound while nothing edits a node, so a whole build of every device is checked
against fresh parses, tree by tree, with every cached tree accounted for."""

import ast
from pathlib import Path

import pytest
from _devices import DEVICE_NAMES

from buildgen.definitions import definitions_for_toml
from buildgen.generate import generate_device
from buildgen.source_ast import _parse, parse_source


def test_one_text_is_parsed_once() -> None:
    _parse.cache_clear()
    first = parse_source("X = 1\n", "a.py")
    assert parse_source("X = 1\n", "a.py") is first
    assert parse_source("X = 1\n", "b.py") is not first  # the filename is part of the key: tracebacks name it
    info = _parse.cache_info()
    assert (info.misses, info.hits) == (2, 1)


def test_the_default_filename_and_its_spelled_out_form_share_one_tree() -> None:
    # The cache keys on the call as made; parse_source() passes both arguments so these stay one entry.
    _parse.cache_clear()
    assert parse_source("X = 1\n") is parse_source("X = 1\n", "<unknown>")
    assert _parse.cache_info().currsize == 1


def test_a_syntax_error_is_raised_for_each_caller_and_never_cached() -> None:
    _parse.cache_clear()
    for _ in range(2):
        with pytest.raises(SyntaxError) as raised:
            parse_source("x = (1,\n", "broken.py")
        assert raised.value.filename == "broken.py"
    assert _parse.cache_info().currsize == 0


def test_a_whole_build_of_every_device_leaves_every_shared_tree_as_parsed(repo_root: Path) -> None:
    # Every tree the build cached is looked up again (a hit hands back the very object the build
    # shared) and must dump exactly as a fresh parse, positions included; the hit count proves none was missed.
    src_dir, ext_dir = repo_root / "src", repo_root / "ext"
    _parse.cache_clear()
    for device in DEVICE_NAMES:
        toml = repo_root / "devices" / f"{device}.toml"
        generate_device(toml, src_dir, ext_dir)
        definitions_for_toml(toml, src_dir)
    cached = _parse.cache_info().currsize
    assert cached > 0
    checked = 0
    for path in sorted([*src_dir.glob("*.py"), *ext_dir.glob("*.py")]):
        for source, filename in ((path.read_text(), str(path)), (path.read_text(encoding="utf-8"), "<unknown>")):
            hits = _parse.cache_info().hits
            shared = parse_source(source, filename)
            if _parse.cache_info().hits == hits:
                continue  # not one the build parsed: this lookup just parsed it
            checked += 1
            assert ast.dump(shared, include_attributes=True) == ast.dump(ast.parse(source, filename=filename), include_attributes=True), f"{filename}: a shared tree was edited"
    assert checked == cached, f"{cached - checked} cached tree(s) came from a file outside src/ and ext/ - extend the lookup"
