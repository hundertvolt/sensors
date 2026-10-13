"""Tests for buildgen.frozen_modules: dependency-driven frozen-module selection via AST-scanned
transitive import closure (SPECIFICATION.md Part L.2), seeded from the generated module's own imports,
TYPE_CHECKING blocks stripped (their else: branch kept), never a dynamic import."""

import ast
from pathlib import Path

import pytest
from _devices import DEVICE_NAMES

from buildgen.errors import BuildError
from buildgen.frozen_modules import compute_frozen_modules
from buildgen.generate import GeneratedDevice, generate_device


def _module_files(src_dir: Path, ext_dir: Path) -> "dict[str, Path]":
    # Every importable module name of the two roots; src/ wins a name both carry, as the closure resolves it.
    return {p.stem: p for root in (ext_dir, src_dir) for p in sorted(root.glob("*.py"))}


def _runtime_imports(source: str) -> "set[str]":
    # This test's own reading of what a module imports when it runs: an `if TYPE_CHECKING:` body
    # never runs and its else: does. Kept apart from the module under test, so the two can disagree.
    found: set[str] = set()
    pending: list[ast.AST] = [ast.parse(source)]
    while pending:
        node = pending.pop()
        if isinstance(node, ast.If) and isinstance(node.test, ast.Name) and node.test.id == "TYPE_CHECKING":
            pending.extend(node.orelse)
            continue
        if isinstance(node, ast.Import):
            found.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            found.add(node.module.split(".")[0])
        pending.extend(ast.iter_child_nodes(node))
    return found


@pytest.fixture
def ext_dir(repo_root: Path) -> Path:
    return repo_root / "ext"


@pytest.fixture(scope="module")
def generated(repo_root: Path) -> "dict[str, GeneratedDevice]":
    # One generation per device for the whole module: every per-device test below reads the same result.
    return {device: generate_device(repo_root / "devices" / f"{device}.toml", repo_root / "src", repo_root / "ext") for device in DEVICE_NAMES}


@pytest.fixture
def src_dir(repo_root: Path) -> Path:
    return repo_root / "src"


def test_wozi_frozen_modules_include_every_declared_driver(repo_root: Path, src_dir: Path, ext_dir: Path) -> None:
    result = generate_device(repo_root / "devices" / "wozi.toml", src_dir, ext_dir)
    for driver_module in ("asy_scd30_driver", "asy_sgp40_driver", "asy_bmp3xx_driver", "asy_fram_manager", "asy_neopixel_driver", "asy_notification_service"):
        assert driver_module in result.frozen_modules


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_the_frozen_set_is_the_closure_of_the_generated_modules_imports(generated: "dict[str, GeneratedDevice]", src_dir: Path, ext_dir: Path, device: str) -> None:
    files = _module_files(src_dir, ext_dir)
    expected = {name for name in _runtime_imports(generated[device].module_source) if name in files}
    assert expected, "sanity: a generated module imports at least one src/ or ext/ module"
    frontier = sorted(expected)
    while frontier:
        for dep in _runtime_imports(files[frontier.pop()].read_text()):
            if dep in files and dep not in expected:
                expected.add(dep)
                frontier.append(dep)
    assert generated[device].frozen_modules == expected


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_every_frozen_module_is_imported_by_the_generated_module_or_another_member(generated: "dict[str, GeneratedDevice]", src_dir: Path, ext_dir: Path, device: str) -> None:
    # No stray name: a member nothing in the image imports would be frozen for nothing.
    files = _module_files(src_dir, ext_dir)
    frozen = generated[device].frozen_modules
    imported = _runtime_imports(generated[device].module_source).union(*(_runtime_imports(files[m].read_text()) for m in frozen))
    assert sorted(frozen - imported) == []


def test_frozen_modules_include_transitive_dependency(repo_root: Path, src_dir: Path, ext_dir: Path) -> None:
    # asy_sgp40_driver.py imports voc_algorithm.py and asy_crc_checks.py directly - the generated
    # module imports neither, so this only passes if the transitive closure actually walks imports,
    # not just the seed set.
    result = generate_device(repo_root / "devices" / "wozi.toml", src_dir, ext_dir)
    assert "voc_algorithm" not in _runtime_imports(result.module_source)
    assert "voc_algorithm" in result.frozen_modules
    assert "asy_crc_checks" in result.frozen_modules


def test_frozen_modules_include_ext_microdot(repo_root: Path, src_dir: Path, ext_dir: Path) -> None:
    result = generate_device(repo_root / "devices" / "wozi.toml", src_dir, ext_dir)
    assert "microdot" in result.frozen_modules


def test_the_seed_keeps_only_imported_names_with_a_file(tmp_path: Path) -> None:
    # Built-ins and the build-time frozen_html have no .py in either root, so they drop out of the seed.
    (tmp_path / "src").mkdir()
    (tmp_path / "ext").mkdir()
    (tmp_path / "src" / "asy_real_driver.py").write_text("")
    source = "import asyncio\nimport frozen_html\nfrom machine import Pin\nfrom asy_real_driver import X\n"
    assert compute_frozen_modules(source, tmp_path / "src", tmp_path / "ext") == {"asy_real_driver"}


def test_frozen_modules_exclude_type_checking_only_import(tmp_path: Path) -> None:
    # A module only reachable through an `if TYPE_CHECKING:` block never executes on-device
    # (MicroPython has no runtime typing module) - it must not be pulled into the closure.
    (tmp_path / "type_only_dep.py").write_text("")
    (tmp_path / "asy_typechecked_driver.py").write_text(
        "try:\n    from typing import TYPE_CHECKING\nexcept ImportError:\n    TYPE_CHECKING = False\n\nif TYPE_CHECKING:\n    import type_only_dep\n",
    )

    frozen = compute_frozen_modules("from asy_typechecked_driver import X\n", tmp_path, tmp_path)
    assert "asy_typechecked_driver" in frozen
    assert "type_only_dep" not in frozen


def test_the_else_branch_of_a_type_checking_block_is_a_runtime_import(tmp_path: Path) -> None:
    # Only the `if TYPE_CHECKING:` body is skipped: its else: runs on the device, so what it imports is frozen.
    (tmp_path / "type_only_dep.py").write_text("")
    (tmp_path / "runtime_dep.py").write_text("")
    (tmp_path / "asy_branching_driver.py").write_text("TYPE_CHECKING = False\nif TYPE_CHECKING:\n    import type_only_dep\nelse:\n    import runtime_dep\n")

    frozen = compute_frozen_modules("import asy_branching_driver\n", tmp_path, tmp_path)
    assert frozen == {"asy_branching_driver", "runtime_dep"}


def test_a_module_in_the_closure_that_does_not_parse_fails_the_build(tmp_path: Path) -> None:
    # A src/ file the closure reaches but cannot parse is one BuildError naming the file, never a raw traceback.
    (tmp_path / "broken_dep.py").write_text("def broken(:\n")
    (tmp_path / "asy_realdep_driver.py").write_text("import broken_dep\n")
    with pytest.raises(BuildError, match=r"^\[dev/broken_dep\] .*broken_dep\.py has a syntax error.* - fix: ") as caught:
        compute_frozen_modules("import asy_realdep_driver\n", tmp_path, tmp_path, device="dev")
    assert caught.value.rule == "source.syntax-error"


def test_frozen_modules_real_import_is_included(tmp_path: Path) -> None:
    (tmp_path / "real_dep.py").write_text("")
    (tmp_path / "asy_realdep_driver.py").write_text("import real_dep\n")

    frozen = compute_frozen_modules("import asy_realdep_driver\n", tmp_path, tmp_path)
    assert "real_dep" in frozen


def test_a_seed_module_with_no_file_on_disk_contributes_no_imports(tmp_path: Path) -> None:
    # The closure walk asks each module for its own imports; one with no .py file anywhere in the
    # roots contributes nothing rather than raising, so a stale seed name can't break a build.
    from buildgen.frozen_modules import _local_imports_of

    assert _local_imports_of("no_such_module", (tmp_path,)) == set()


def test_an_import_cycle_between_two_modules_terminates(tmp_path: Path) -> None:
    # The frontier skips anything already in the closure - without that, two modules importing each
    # other would loop forever rather than resolving.
    (tmp_path / "mod_a.py").write_text("import mod_b\n")
    (tmp_path / "mod_b.py").write_text("import mod_a\n")
    from buildgen.frozen_modules import _local_imports_of

    assert _local_imports_of("mod_a", (tmp_path,)) == {"mod_b"}
    assert _local_imports_of("mod_b", (tmp_path,)) == {"mod_a"}
    assert compute_frozen_modules("import mod_a\n", tmp_path, tmp_path) == {"mod_a", "mod_b"}
