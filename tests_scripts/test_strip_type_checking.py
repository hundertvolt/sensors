"""Tests scripts/_strip_type_checking.py's `if TYPE_CHECKING:` stripping transform in isolation,
independent of build_firmware.py's own wiring (see test_build_firmware.py for that)."""

import ast
import importlib.util

import pytest


@pytest.fixture(scope="session")
def strip_module(repo_root):
    module_path = repo_root / "scripts" / "_strip_type_checking.py"
    spec = importlib.util.spec_from_file_location("_strip_type_checking", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_no_type_checking_pattern_returns_source_byte_for_byte_unchanged(strip_module):
    source = "import os\n\n\ndef f(x: int) -> int:\n    return x + 1\n"
    assert strip_module.strip_type_checking_blocks(source) is source


def test_strips_bare_type_checking_block_and_its_import_guard(strip_module):
    source = (
        "import asyncio\n\n"
        "try:\n"
        "    from typing import TYPE_CHECKING\n"
        "except ImportError:\n"
        "    TYPE_CHECKING = False\n\n"
        "if TYPE_CHECKING:\n"
        "    from typing import Any\n\n"
        "    Alias = dict[str, Any]\n\n\n"
        "def f() -> None:\n"
        "    pass\n"
    )
    output = strip_module.strip_type_checking_blocks(source)
    assert "TYPE_CHECKING" not in output
    assert "Alias" not in output
    assert "import asyncio" in output
    assert "def f() -> None" in output
    ast.parse(output)  # stays syntactically valid


def test_strips_module_attribute_type_checking_test(strip_module):
    source = "import typing\n\nif typing.TYPE_CHECKING:\n    X = 1\n\nY = 2\n"
    output = strip_module.strip_type_checking_blocks(source)
    assert "X = 1" not in output
    assert "Y = 2" in output


def test_leaves_compound_condition_untouched(strip_module):
    # "if TYPE_CHECKING and something():" is not a bare test - BACKLOG.md's prototype note says
    # leave any compound condition untouched rather than guess.
    source = "if TYPE_CHECKING and extra_check():\n    Z = 1\n"
    output = strip_module.strip_type_checking_blocks(source)
    assert "Z = 1" in output


def test_leaves_if_else_untouched(strip_module):
    source = "if TYPE_CHECKING:\n    W = 1\nelse:\n    W = 2\n"
    output = strip_module.strip_type_checking_blocks(source)
    assert "W = 1" in output
    assert "W = 2" in output


def test_leaves_unrelated_try_except_importerror_untouched(strip_module):
    source = "try:\n    import ujson as json\nexcept ImportError:\n    import json\n"
    output = strip_module.strip_type_checking_blocks(source)
    assert "import ujson as json" in output
    assert output is source  # nothing matched, so this is the unchanged-passthrough path


def test_strips_multiple_type_checking_blocks_in_one_file(strip_module):
    source = (
        "try:\n"
        "    from typing import TYPE_CHECKING\n"
        "except ImportError:\n"
        "    TYPE_CHECKING = False\n\n"
        "if TYPE_CHECKING:\n"
        "    A = 1\n\n"
        "def f():\n"
        "    pass\n\n"
        "if TYPE_CHECKING:\n"
        "    B = 2\n"
    )
    output = strip_module.strip_type_checking_blocks(source)
    assert "A = 1" not in output
    assert "B = 2" not in output
    assert "def f" in output


def test_real_src_files_round_trip_to_syntactically_valid_type_checking_free_output(strip_module, repo_root):
    # End-to-end proof against the actual promoted driver files that use this pattern (not just
    # synthetic snippets above) - confirms the transform handles real, full-size module content.
    # Every bare `if TYPE_CHECKING:` block must be gone; the import-guard header itself is only
    # required to disappear where it's the plain two-line D.6 form - some files (e.g.
    # asy_scd30_driver.py) extend the except handler with a real runtime `cast()` no-op fallback
    # that's called outside any TYPE_CHECKING block, so that handler body has more than the one
    # matched statement and this transform correctly leaves it in place rather than guessing.
    src_files_with_guard = [p for p in (repo_root / "src").glob("*.py") if "TYPE_CHECKING" in p.read_text()]
    assert src_files_with_guard, "sanity: at least one real src/ file should use this pattern"
    for src_file in src_files_with_guard:
        output = strip_module.strip_type_checking_blocks(src_file.read_text())
        assert "if TYPE_CHECKING:" not in output
        ast.parse(output)
