"""buildgen.gc_policy + the boot entry it drives: a build's GC policy and whether it carries the
memory-pressure instrument are build properties, not something a test mutates at runtime
(SPECIFICATION.md Part I.6)."""

import ast
from pathlib import Path

import pytest
from _toml_fixtures import base_doc, write_doc

from buildgen.codegen import generate_boot_entry_source
from buildgen.errors import BuildError
from buildgen.gc_policy import DEFAULT_GC_POLICY, GC_POLICIES, GC_POLICY_THRESHOLDS, PRESSURE_MODULE, check_pressure_policy, threshold_for
from buildgen.generate import generate_device


def test_the_shipped_default_is_the_threshold_policy() -> None:
    assert DEFAULT_GC_POLICY == "threshold"
    assert GC_POLICY_THRESHOLDS["threshold"] == 32768
    # Negative disables the threshold outright in py/modgc.c - MicroPython's own real default.
    assert GC_POLICY_THRESHOLDS["reactive"] == -1


def test_default_boot_entry_is_unchanged_by_the_new_option() -> None:
    # The shipped artifact must be byte-identical to what this generator emitted before GC policy
    # became selectable - a regression here changes every deployed device's boot.
    source = generate_boot_entry_source("wozi")
    assert "gc.threshold(32768)" in source
    assert PRESSURE_MODULE not in source
    assert "asyncio.run(main())" in source


@pytest.mark.parametrize("policy", GC_POLICIES)
def test_every_policy_emits_its_own_threshold_and_parses(policy: str) -> None:
    source = generate_boot_entry_source("dev", policy)
    assert f"gc.threshold({GC_POLICY_THRESHOLDS[policy]})" in source
    ast.parse(source)


def test_a_pressure_build_imports_and_starts_the_instrument() -> None:
    source = generate_boot_entry_source("dev", "reactive", memory_pressure=True)
    ast.parse(source)
    assert f"import {PRESSURE_MODULE}" in source
    assert f"{PRESSURE_MODULE}.start()" in source
    # Started inside the loop main() blocks on, before main() itself, so boot is under pressure too.
    assert source.index(f"{PRESSURE_MODULE}.start()") < source.index("await main()")
    assert "asyncio.run(_main_under_pressure())" in source


def test_pressure_is_refused_on_the_shipped_policy() -> None:
    with pytest.raises(BuildError) as excinfo:
        generate_boot_entry_source("dev", "threshold", memory_pressure=True)
    assert "reactive" in str(excinfo.value)


def test_an_unknown_policy_fails_loudly_and_names_the_valid_ones() -> None:
    with pytest.raises(BuildError) as excinfo:
        threshold_for("proactive", "dev")
    assert "reactive" in str(excinfo.value)
    assert "threshold" in str(excinfo.value)


def test_check_pressure_policy_allows_the_reactive_combination() -> None:
    check_pressure_policy("reactive", "dev", memory_pressure=True)  # must not raise
    check_pressure_policy("threshold", "dev", memory_pressure=False)


def test_generate_device_threads_the_policy_through(tmp_path: Path, repo_root: Path) -> None:
    toml_path = write_doc(tmp_path, "gcdev", base_doc())
    generated = generate_device(toml_path, repo_root / "src", repo_root / "ext", gc_policy="reactive", memory_pressure=True)
    assert generated.gc_policy == "reactive"
    assert generated.memory_pressure is True
    assert "gc.threshold(-1)" in generated.boot_entry_source
    # The device module itself is policy-independent - only the boot entry changes.
    assert "gc.threshold" not in generated.module_source


def test_generate_device_defaults_to_the_shipped_policy(tmp_path: Path, repo_root: Path) -> None:
    toml_path = write_doc(tmp_path, "gcdev", base_doc())
    generated = generate_device(toml_path, repo_root / "src", repo_root / "ext")
    assert generated.gc_policy == DEFAULT_GC_POLICY
    assert generated.memory_pressure is False
    assert "gc.threshold(32768)" in generated.boot_entry_source


def test_the_instrument_module_exists_where_the_build_script_stages_it_from(repo_root: Path) -> None:
    # scripts/build_firmware.py stages this exact path into a --memory-pressure build; a rename
    # that misses one side would otherwise only surface as a failed firmware build.
    assert (repo_root / "tests_hardware" / "device_modules" / f"{PRESSURE_MODULE}.py").is_file()


def test_the_device_module_declares_its_build_gc_policy(tmp_path: Path, repo_root: Path) -> None:
    # Read off the frozen image by tests_hardware/conftest.py's flashed_build fixture. A live
    # gc.threshold() read cannot serve this purpose: entering the raw REPL can land before main.py
    # has run, and a fresh interpreter reports -1 regardless of what the boot entry would set.
    toml_path = write_doc(tmp_path, "gcdev", base_doc())
    for policy in GC_POLICIES:
        generated = generate_device(toml_path, repo_root / "src", repo_root / "ext", gc_policy=policy, memory_pressure=(policy == "reactive"))
        assert f"BUILD_GC_POLICY = {policy!r}" in generated.module_source


def test_build_gc_policy_is_public_and_readable_without_running_main(tmp_path: Path, repo_root: Path) -> None:
    # Not underscore-private and not a const(): const() folds at compile time and leaves no module
    # attribute to read, and a private name is not part of what the hardware tier may rely on.
    toml_path = write_doc(tmp_path, "gcdev", base_doc())
    generated = generate_device(toml_path, repo_root / "src", repo_root / "ext", gc_policy="reactive")
    tree = ast.parse(generated.module_source)
    assigned = [
        node
        for node in tree.body
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "BUILD_GC_POLICY" for t in node.targets)
    ]
    assert len(assigned) == 1, "BUILD_GC_POLICY must be exactly one module-level assignment"
    assert isinstance(assigned[0].value, ast.Constant), "must be a plain literal, not a const() call - const() leaves no readable attribute"
    assert assigned[0].value.value == "reactive"
