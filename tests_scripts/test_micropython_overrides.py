"""Tests toolchain/micropython_overrides.py's unix_kbd_intr override in isolation: the anchor
verification (loud failure on upstream drift) and the generated override files, against synthetic
fixture trees - never a real compile (that's what scripts/run_digital_twin_ci.sh's own real Unix
port build already proves). See SPECIFICATION.md Part B.14 for the full mechanism."""

from pathlib import Path
from types import ModuleType

import pytest
from _script_loader import load_script_module

_REAL_ANCHOR_LINE = "#define MICROPY_ASYNC_KBD_INTR         (!MICROPY_PY_THREAD_GIL)"


@pytest.fixture(scope="session")
def overrides(repo_root: Path) -> ModuleType:
    return load_script_module(repo_root / "toolchain" / "micropython_overrides.py", "micropython_overrides")


def _write_fake_micropython_tree(root: Path, *, anchor_line: str | None = _REAL_ANCHOR_LINE, with_manifest: bool = True) -> Path:
    variants_dir = root / "ports" / "unix" / "variants"
    variants_dir.mkdir(parents=True)
    common_header = variants_dir / "mpconfigvariant_common.h"
    lines = ["// fake mpconfigvariant_common.h for testing", "#define MICROPY_DEBUG_PRINTERS (1)"]
    if anchor_line is not None:
        lines.insert(1, anchor_line)
    common_header.write_text("\n".join(lines) + "\n")

    standard_dir = variants_dir / "standard"
    standard_dir.mkdir()
    (standard_dir / "mpconfigvariant.h").write_text(
        '#define MICROPY_CONFIG_ROM_LEVEL (MICROPY_CONFIG_ROM_LEVEL_EXTRA_FEATURES)\n#include "../mpconfigvariant_common.h"\n',
    )
    (standard_dir / "mpconfigvariant.mk").write_text("FROZEN_MANIFEST ?= $(VARIANT_DIR)/manifest.py\n")
    if with_manifest:
        (standard_dir / "manifest.py").write_text('include("$(PORT_DIR)/variants/manifest.py")\n')
    return root


class TestVerifyUnixKbdIntrAnchor:
    def test_passes_against_the_real_pinned_source(self, overrides: ModuleType, micropython_dir: Path) -> None:
        common_header = micropython_dir / "ports" / "unix" / "variants" / "mpconfigvariant_common.h"
        if not common_header.is_file():
            pytest.skip(f"no real toolchain checkout at {micropython_dir} - build it first (scripts/test.sh does)")
        result = overrides.verify_unix_kbd_intr_anchor(micropython_dir)
        assert result == common_header

    def test_raises_when_the_common_header_is_missing(self, overrides: ModuleType, tmp_path: Path) -> None:
        with pytest.raises(overrides.OverrideError, match="not found"):
            overrides.verify_unix_kbd_intr_anchor(tmp_path)

    def test_raises_when_the_anchor_line_is_gone(self, overrides: ModuleType, tmp_path: Path) -> None:
        _write_fake_micropython_tree(tmp_path, anchor_line=None)
        with pytest.raises(overrides.OverrideError, match="anchor line not found"):
            overrides.verify_unix_kbd_intr_anchor(tmp_path)

    def test_raises_when_the_anchor_line_changed_shape(self, overrides: ModuleType, tmp_path: Path) -> None:
        # Simulates a future MicroPython release reguarding/renaming the macro - any textual
        # drift from the exact pinned line must be treated as "unverified", not fuzzy-matched.
        _write_fake_micropython_tree(tmp_path, anchor_line="#ifndef MICROPY_ASYNC_KBD_INTR\n#define MICROPY_ASYNC_KBD_INTR (!MICROPY_PY_THREAD_GIL)\n#endif")
        with pytest.raises(overrides.OverrideError, match="anchor line not found"):
            overrides.verify_unix_kbd_intr_anchor(tmp_path)


class TestApplyUnixKbdIntrOverride:
    def test_returns_the_expected_make_variables(self, overrides: ModuleType, tmp_path: Path) -> None:
        fake_mp_dir = _write_fake_micropython_tree(tmp_path / "micropython")
        overrides_dir = tmp_path / "build_overrides"
        result = overrides.apply_unix_kbd_intr_override(fake_mp_dir, overrides_dir)
        assert result == {"VARIANT": "standard", "VARIANT_DIR": str(overrides_dir / "unix_kbd_intr_variant")}

    def test_never_writes_inside_the_micropython_tree(self, overrides: ModuleType, tmp_path: Path) -> None:
        fake_mp_dir = _write_fake_micropython_tree(tmp_path / "micropython")
        before = sorted(p.relative_to(fake_mp_dir) for p in fake_mp_dir.rglob("*"))
        overrides.apply_unix_kbd_intr_override(fake_mp_dir, tmp_path / "build_overrides")
        after = sorted(p.relative_to(fake_mp_dir) for p in fake_mp_dir.rglob("*"))
        assert before == after, "the fetched checkout must never gain, lose, or have a file rewritten"

    def test_generated_mpconfigvariant_h_includes_the_real_file_and_forces_the_safe_path(self, overrides: ModuleType, tmp_path: Path) -> None:
        fake_mp_dir = _write_fake_micropython_tree(tmp_path / "micropython")
        real_header = fake_mp_dir / "ports" / "unix" / "variants" / "standard" / "mpconfigvariant.h"
        override_dir = tmp_path / "build_overrides" / "unix_kbd_intr_variant"
        overrides.apply_unix_kbd_intr_override(fake_mp_dir, tmp_path / "build_overrides")
        generated = (override_dir / "mpconfigvariant.h").read_text()
        assert f'#include "{real_header}"' in generated
        assert "#undef MICROPY_ASYNC_KBD_INTR" in generated
        assert "#define MICROPY_ASYNC_KBD_INTR (0)" in generated
        # Ordering matters: the undef must follow the include (so it wins), the define follow the undef.
        include_pos = generated.index(f'#include "{real_header}"')
        undef_pos = generated.index("#undef MICROPY_ASYNC_KBD_INTR")
        define_pos = generated.index("#define MICROPY_ASYNC_KBD_INTR (0)")
        assert include_pos < undef_pos < define_pos

    def test_generated_mpconfigvariant_mk_relays_to_the_real_file(self, overrides: ModuleType, tmp_path: Path) -> None:
        fake_mp_dir = _write_fake_micropython_tree(tmp_path / "micropython")
        real_mk = fake_mp_dir / "ports" / "unix" / "variants" / "standard" / "mpconfigvariant.mk"
        override_dir = tmp_path / "build_overrides" / "unix_kbd_intr_variant"
        overrides.apply_unix_kbd_intr_override(fake_mp_dir, tmp_path / "build_overrides")
        assert (override_dir / "mpconfigvariant.mk").read_text() == f"include {real_mk}\n"

    def test_generated_manifest_relays_via_include_rather_than_copying(self, overrides: ModuleType, tmp_path: Path) -> None:
        # include() (not a raw copy) so the generated manifest can never drift out of sync with a
        # future pinned-version change to the real one.
        fake_mp_dir = _write_fake_micropython_tree(tmp_path / "micropython")
        real_manifest = fake_mp_dir / "ports" / "unix" / "variants" / "standard" / "manifest.py"
        override_dir = tmp_path / "build_overrides" / "unix_kbd_intr_variant"
        overrides.apply_unix_kbd_intr_override(fake_mp_dir, tmp_path / "build_overrides")
        assert (override_dir / "manifest.py").read_text() == f'include("{real_manifest}")\n'

    def test_missing_real_manifest_is_tolerated(self, overrides: ModuleType, tmp_path: Path) -> None:
        fake_mp_dir = _write_fake_micropython_tree(tmp_path / "micropython", with_manifest=False)
        override_dir = tmp_path / "build_overrides" / "unix_kbd_intr_variant"
        overrides.apply_unix_kbd_intr_override(fake_mp_dir, tmp_path / "build_overrides")
        assert not (override_dir / "manifest.py").exists()

    def test_is_idempotent(self, overrides: ModuleType, tmp_path: Path) -> None:
        fake_mp_dir = _write_fake_micropython_tree(tmp_path / "micropython")
        overrides_dir = tmp_path / "build_overrides"
        first = overrides.apply_unix_kbd_intr_override(fake_mp_dir, overrides_dir)
        second = overrides.apply_unix_kbd_intr_override(fake_mp_dir, overrides_dir)
        assert first == second

    def test_raises_without_applying_anything_when_the_anchor_is_gone(self, overrides: ModuleType, tmp_path: Path) -> None:
        fake_mp_dir = _write_fake_micropython_tree(tmp_path / "micropython", anchor_line=None)
        overrides_dir = tmp_path / "build_overrides"
        with pytest.raises(overrides.OverrideError):
            overrides.apply_unix_kbd_intr_override(fake_mp_dir, overrides_dir)
        assert not overrides_dir.exists()


class TestBuildUnixPortAppliesTheOverride:
    """Guards the wiring itself, not just the override function in isolation - a future edit that
    drops build_unix_port()'s own call to apply_unix_kbd_intr_override() (or stops threading its
    returned make variables into the real command) must fail a test, not silently ship an
    unpatched binary again."""

    @pytest.fixture
    def setup_toolchain(self, repo_root: Path) -> ModuleType:
        return load_script_module(repo_root / "toolchain" / "setup_toolchain.py", "setup_toolchain")

    def test_the_constructed_make_command_carries_variant_and_variant_dir(
        self, setup_toolchain: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        fake_mp_dir = _write_fake_micropython_tree(tmp_path / "toolchain" / "micropython")
        toolchain_dir = tmp_path / "toolchain"
        build_dir = fake_mp_dir / "ports" / "unix" / "build-standard"

        recorded: list[list[str]] = []

        def fake_run(cmd: list[str], cwd: Path | None = None, *, check: bool = True, env: dict[str, str] | None = None) -> str:
            recorded.append(cmd)
            if cmd[0] == "make":
                # Stands in for what a real `make` invocation would produce - build_unix_port()'s
                # own binary.exists() check right after this needs something there.
                build_dir.mkdir(parents=True, exist_ok=True)
                (build_dir / "micropython").write_text("#!/bin/sh\necho fake\n")
                return "LINK build-standard/micropython\n"
            return "namespace(name='micropython')"  # stands in for the post-build sys.implementation probe

        monkeypatch.setattr(setup_toolchain, "run", fake_run)
        setup_toolchain.build_unix_port(fake_mp_dir, toolchain_dir, jobs=4)

        make_cmd = recorded[0]
        assert make_cmd[0] == "make"
        assert "VARIANT=standard" in make_cmd
        assert f"VARIANT_DIR={toolchain_dir / 'build_overrides' / 'unix_kbd_intr_variant'}" in make_cmd

    def test_raises_before_ever_invoking_make_when_the_override_cannot_be_verified(
        self, setup_toolchain: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # A stale/mismatched pinned source must fail loudly at the override's own verify step,
        # never fall through to a real (unpatched) build.
        fake_mp_dir = _write_fake_micropython_tree(tmp_path / "toolchain" / "micropython", anchor_line=None)
        toolchain_dir = tmp_path / "toolchain"
        recorded: list[list[str]] = []

        def fake_run(cmd: list[str], cwd: Path | None = None, *, check: bool = True, env: dict[str, str] | None = None) -> str:
            recorded.append(cmd)
            return ""

        monkeypatch.setattr(setup_toolchain, "run", fake_run)

        with pytest.raises(setup_toolchain.micropython_overrides.OverrideError):
            setup_toolchain.build_unix_port(fake_mp_dir, toolchain_dir, jobs=4)
        assert recorded == []
