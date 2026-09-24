"""Tests toolchain/micropython_overrides.py's unix_kbd_intr override in isolation - the anchor
verification and the generated files, against synthetic fixture trees, never a real compile (that
is what the real Unix-port build already proves). SPECIFICATION.md Part B.14 has the mechanism."""

import sys
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING

import pytest
from _script_loader import load_script_module

if TYPE_CHECKING:
    from collections.abc import Callable

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
    """Guards the wiring, not just the override function: an edit that drops build_unix_port()'s
    call to apply_unix_kbd_intr_override(), or stops threading its make variables into the real
    command, must fail a test rather than silently ship an unpatched binary again."""

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

    def _recorded_make_cmd(
        self, setup_toolchain: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, settrace: bool,
    ) -> list[str]:
        """Builds one variant against a fake tree and returns the make command it constructed."""
        fake_mp_dir = _write_fake_micropython_tree(tmp_path / "toolchain" / "micropython")
        toolchain_dir = tmp_path / "toolchain"
        expected_dir = setup_toolchain.UNIX_SETTRACE_BUILD_DIR if settrace else setup_toolchain.UNIX_BUILD_DIR
        build_dir = fake_mp_dir / "ports" / "unix" / expected_dir
        recorded: list[list[str]] = []

        def fake_run(cmd: list[str], cwd: Path | None = None, *, check: bool = True, env: dict[str, str] | None = None) -> str:
            recorded.append(cmd)
            if cmd[0] == "make":
                build_dir.mkdir(parents=True, exist_ok=True)
                (build_dir / "micropython").write_text("#!/bin/sh\necho fake\n")
                return f"LINK {expected_dir}/micropython\n"
            return "namespace(name='micropython')"

        monkeypatch.setattr(setup_toolchain, "run", fake_run)
        binary = setup_toolchain.build_unix_port(fake_mp_dir, toolchain_dir, jobs=4, settrace=settrace)
        assert binary == build_dir / "micropython", f"the {expected_dir} variant must be returned from its own build dir"
        return recorded[0]

    def test_the_test_rig_variant_is_built_without_the_settrace_flag(
        self, setup_toolchain: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # The whole point of the 2026-09-21 split (Part E.5.2): compiled in, the flag allocates a
        # frame and a code object per call, inflating every figure the memory work measures 4-5x.
        # Re-adding it to the default path is silent until a binary is rebuilt - so assert it here.
        make_cmd = self._recorded_make_cmd(setup_toolchain, tmp_path, monkeypatch, settrace=False)
        flags = next(arg for arg in make_cmd if arg.startswith("CFLAGS_EXTRA="))
        assert "MICROPY_PY_SYS_SETTRACE" not in flags, f"the test rig must be settrace-FREE, got {flags!r}"
        assert not [arg for arg in make_cmd if arg.startswith("BUILD=")], "the rig takes the Makefile's own default build dir, never an explicit BUILD="

    def test_the_coverage_variant_gets_the_flag_and_its_own_build_dir(
        self, setup_toolchain: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # --coverage genuinely needs sys.settrace, so the second binary must both carry the flag and
        # land somewhere else - sharing one build dir is what made the path stop identifying the
        # variant, which scripts/test.sh now has to probe the binary to recover.
        make_cmd = self._recorded_make_cmd(setup_toolchain, tmp_path, monkeypatch, settrace=True)
        flags = next(arg for arg in make_cmd if arg.startswith("CFLAGS_EXTRA="))
        assert "-DMICROPY_PY_SYS_SETTRACE=1" in flags, f"--coverage's own binary must carry the flag, got {flags!r}"
        assert f"BUILD={setup_toolchain.UNIX_SETTRACE_BUILD_DIR}" in make_cmd
        assert setup_toolchain.UNIX_SETTRACE_BUILD_DIR != setup_toolchain.UNIX_BUILD_DIR, "the two variants must not share a build directory"

    def test_the_shell_side_looks_for_both_variants_where_they_are_built(self, repo_root: Path, setup_toolchain: ModuleType) -> None:
        # Both consumers spell the directory out, because they resolve a binary before anything can
        # ask it what it is. A renamed constant would leave scripts/test.sh rebuilding into a path
        # it never looks at, and tests_scripts/test_coverage_runner.py skipping itself in silence.
        shell = (repo_root / "scripts" / "test.sh").read_text()
        conftest = (repo_root / "tests_scripts" / "conftest.py").read_text()
        for variant in (setup_toolchain.UNIX_BUILD_DIR, setup_toolchain.UNIX_SETTRACE_BUILD_DIR):
            assert f'"$unix_dir/{variant}/micropython"' in shell, f"scripts/test.sh no longer resolves the {variant} binary - the constant and the shell have drifted apart"
        assert f'"{setup_toolchain.UNIX_BUILD_DIR}"' in conftest, f"tests_scripts/conftest.py's micropython_bin fixture no longer points at {setup_toolchain.UNIX_BUILD_DIR}"

    def test_a_setup_run_builds_both_variants(self, repo_root: Path) -> None:
        # Structural: the real call is a multi-minute compile. What has to hold is that the
        # verification sequence asks for the settrace variant at all - without it, --coverage has
        # no binary and scripts/test.sh's own variant check fails a run it cannot repair.
        source = (repo_root / "toolchain" / "setup_toolchain.py").read_text()
        assert "build_unix_port(micropython_dir, toolchain_dir, jobs, settrace=True)" in source, "setup must build the --coverage variant too, or scripts/test.sh --coverage has nothing to run"

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


# ---------------------------------------------------------------------------
# lwip_connection_counts (SPECIFICATION.md Part B.14.2)
# ---------------------------------------------------------------------------

_REAL_BOARD = "RPI_PICO_W"
_LWIP_MACROS = {
    "MEMP_NUM_TCP_PCB": 12,
    "MEMP_NUM_TCP_PCB_LISTEN": 8,
    "MEMP_NUM_PBUF": 16,
    "PBUF_POOL_SIZE": 16,
    "MEMP_NUM_UDP_PCB": 5,
    "LWIP_STATS": 0,
    "MEM_SIZE": 8000,
    "TCP_MSS": 800,
    "TCP_WND": 6400,
    "TCP_SND_BUF": 6400,
    "MEMP_NUM_TCP_SEG": 32,
}


def _write_fake_lwip_tree(root: Path, *, drop: str | None = None, board: str = _REAL_BOARD) -> Path:
    """A synthetic tree carrying every anchor the override checks; `drop` removes exactly one, so a
    test can prove that anchor is really load-bearing rather than decorative."""
    opt_h = root / "lib" / "lwip" / "src" / "include" / "lwip"
    opt_h.mkdir(parents=True)
    guards = "\n".join(f"#if !defined {m} || defined __DOXYGEN__\n#define {m} 1\n#endif" for m in ("MEMP_NUM_TCP_PCB", "MEMP_NUM_TCP_PCB_LISTEN", "MEMP_NUM_PBUF", "PBUF_POOL_SIZE") if m != drop)
    (opt_h / "opt.h").write_text(guards + "\n")

    common = root / "extmod" / "lwip-include"
    common.mkdir(parents=True)
    common_lines = [
        "#define LWIP_NETCONN                    0",
        "#define LWIP_STATS                      0",
        "#define MEMP_NUM_UDP_PCB                (4 + LWIP_MDNS_RESPONDER)",
        "#ifndef MEM_SIZE",
        "#define MEM_SIZE (8000)",
        "#define TCP_MSS (800)",
        "#define TCP_WND (8 * TCP_MSS)",
        "#define TCP_SND_BUF (8 * TCP_MSS)",
        "#define MEMP_NUM_TCP_SEG (32)",
        "#endif",
    ]
    (common / "lwipopts_common.h").write_text("\n".join(line for line in common_lines if line != drop) + "\n")

    lwip_inc = root / "ports" / "rp2" / "lwip_inc"
    lwip_inc.mkdir(parents=True)
    inc_line = '#include "extmod/lwip-include/lwipopts_common.h"'
    (lwip_inc / "lwipopts.h").write_text("" if inc_line == drop else inc_line + "\n")

    cmake_lines = [
        "include(${MICROPY_BOARD_DIR}/mpconfigboard.cmake)",
        "target_include_directories(${MICROPY_TARGET} PRIVATE\n        lwip_inc\n    )",
        "if(NOT MICROPY_BOARD_PINS)",
    ]
    (root / "ports" / "rp2" / "CMakeLists.txt").write_text("\n".join(line for line in cmake_lines if line != drop) + "\n")

    board_dir = root / "ports" / "rp2" / "boards" / board
    board_dir.mkdir(parents=True)
    board_cmake_line = "set(MICROPY_FROZEN_MANIFEST ${MICROPY_BOARD_DIR}/manifest.py)"
    (board_dir / "mpconfigboard.cmake").write_text('set(PICO_BOARD "pico_w")\n' if board_cmake_line == drop else f'set(PICO_BOARD "pico_w")\n{board_cmake_line}\n')
    for name in ("mpconfigboard.h", "manifest.py", "pins.csv"):
        if name != drop:
            (board_dir / name).write_text("")
    return root


# One entry per anchor verify_lwip_connection_counts_anchor() checks - 18 text anchors plus the
# three relayed board files. Each is dropped on its own below to prove it is load-bearing.
_EVERY_LWIP_ANCHOR = (
    "MEMP_NUM_TCP_PCB",  # lwIP's own guards - without one a value could not be injected at all
    "MEMP_NUM_TCP_PCB_LISTEN",
    "MEMP_NUM_PBUF",
    "PBUF_POOL_SIZE",
    "#ifndef MEM_SIZE",  # the atomic block
    "#define MEM_SIZE (8000)",
    "#define TCP_MSS (800)",
    "#define TCP_WND (8 * TCP_MSS)",
    "#define TCP_SND_BUF (8 * TCP_MSS)",
    "#define MEMP_NUM_TCP_SEG (32)",
    "#define MEMP_NUM_UDP_PCB                (4 + LWIP_MDNS_RESPONDER)",  # trap B: a plain #define
    "#define LWIP_STATS                      0",
    "#define LWIP_NETCONN                    0",  # the fact that makes MEMP_NUM_NETCONN a no-op
    '#include "extmod/lwip-include/lwipopts_common.h"',
    "include(${MICROPY_BOARD_DIR}/mpconfigboard.cmake)",  # the BOARD_DIR redirect itself
    "target_include_directories(${MICROPY_TARGET} PRIVATE\n        lwip_inc\n    )",
    "if(NOT MICROPY_BOARD_PINS)",
    "set(MICROPY_FROZEN_MANIFEST ${MICROPY_BOARD_DIR}/manifest.py)",
    "pins.csv",
    "manifest.py",
    "mpconfigboard.h",
)


class TestVerifyLwipConnectionCountsAnchor:
    def test_passes_against_the_real_pinned_source(self, overrides: ModuleType, micropython_dir: Path) -> None:
        if not (micropython_dir / "lib" / "lwip" / "src" / "include" / "lwip" / "opt.h").is_file():
            pytest.skip(f"no real toolchain checkout with lwIP submodules at {micropython_dir} - build it first (scripts/test.sh does)")
        overrides.verify_lwip_connection_counts_anchor(micropython_dir, _REAL_BOARD)

    def test_raises_when_the_tree_is_missing_entirely(self, overrides: ModuleType, tmp_path: Path) -> None:
        with pytest.raises(overrides.OverrideError, match="not found"):
            overrides.verify_lwip_connection_counts_anchor(tmp_path, _REAL_BOARD)

    @pytest.mark.parametrize("dropped", _EVERY_LWIP_ANCHOR)
    def test_every_anchor_is_load_bearing(self, overrides: ModuleType, tmp_path: Path, dropped: str) -> None:
        # One parametrization per anchor: each must fail the verify step on its own, or it is
        # decorative and would let a restructuring release build silently unpatched.
        _write_fake_lwip_tree(tmp_path, drop=dropped)
        with pytest.raises(overrides.OverrideError):
            overrides.verify_lwip_connection_counts_anchor(tmp_path, _REAL_BOARD)

    def test_the_parametrization_covers_every_anchor_the_code_checks(self, overrides: ModuleType) -> None:
        # A new anchor added to the code without its own drop case would be unproven - so the two
        # lists must agree exactly, not merely overlap.
        in_code = {*overrides.LWIP_MACROS_GUARDED_IN_OPT_H, *overrides._LWIP_COMMON_ANCHORS, overrides._RP2_LWIPOPTS_ANCHOR, *overrides._RP2_CMAKE_ANCHORS, overrides._BOARD_CMAKE_ANCHOR, "mpconfigboard.h", "manifest.py", "pins.csv"}
        assert set(_EVERY_LWIP_ANCHOR) == in_code
        assert len(_EVERY_LWIP_ANCHOR) == len(set(_EVERY_LWIP_ANCHOR)) == 21


class TestApplyLwipConnectionCountsOverride:
    def test_returns_board_and_board_dir(self, overrides: ModuleType, tmp_path: Path) -> None:
        fake = _write_fake_lwip_tree(tmp_path / "micropython")
        result = overrides.apply_lwip_connection_counts_override(fake, tmp_path / "build_overrides", _REAL_BOARD, _LWIP_MACROS)
        assert result == {"BOARD": _REAL_BOARD, "BOARD_DIR": str(tmp_path / "build_overrides" / overrides.LWIP_OVERRIDE_BOARD_DIR_NAME)}

    def test_never_writes_inside_the_micropython_tree(self, overrides: ModuleType, tmp_path: Path) -> None:
        fake = _write_fake_lwip_tree(tmp_path / "micropython")
        before = sorted(p.relative_to(fake) for p in fake.rglob("*"))
        overrides.apply_lwip_connection_counts_override(fake, tmp_path / "build_overrides", _REAL_BOARD, _LWIP_MACROS)
        after = sorted(p.relative_to(fake) for p in fake.rglob("*"))
        assert before == after, "the fetched checkout must never gain, lose, or have a file rewritten"

    def test_generated_lwipopts_includes_the_real_one_then_redefines_every_option(self, overrides: ModuleType, tmp_path: Path) -> None:
        fake = _write_fake_lwip_tree(tmp_path / "micropython")
        overrides.apply_lwip_connection_counts_override(fake, tmp_path / "build_overrides", _REAL_BOARD, _LWIP_MACROS)
        generated = (tmp_path / "build_overrides" / overrides.LWIP_OVERRIDE_BOARD_DIR_NAME / overrides.LWIP_OVERRIDE_INCLUDE_DIR_NAME / "lwipopts.h").read_text()
        real = fake / "ports" / "rp2" / "lwip_inc" / "lwipopts.h"
        assert f'#include "{real}"' in generated
        include_pos = generated.index(f'#include "{real}"')
        for name, value in _LWIP_MACROS.items():
            # Ordering is the whole mechanism: the #undef must follow the include, so it beats
            # MicroPython's own plain #define, and the #define must follow the #undef.
            assert include_pos < generated.index(f"#undef {name}") < generated.index(f"#define {name} ({value})"), name

    def test_the_board_cmake_prepends_the_override_include_dir_and_relays_the_real_board(self, overrides: ModuleType, tmp_path: Path) -> None:
        fake = _write_fake_lwip_tree(tmp_path / "micropython")
        overrides.apply_lwip_connection_counts_override(fake, tmp_path / "build_overrides", _REAL_BOARD, _LWIP_MACROS)
        override_dir = tmp_path / "build_overrides" / overrides.LWIP_OVERRIDE_BOARD_DIR_NAME
        real_board = fake / "ports" / "rp2" / "boards" / _REAL_BOARD
        cmake = (override_dir / "mpconfigboard.cmake").read_text()
        # BEFORE, not a plain include_directories(): a plain one lands after the port's own
        # target-level lwip_inc and the real lwipopts.h would silently win again.
        assert f'include_directories(BEFORE "{override_dir / overrides.LWIP_OVERRIDE_INCLUDE_DIR_NAME}")' in cmake
        assert f"include({real_board / 'mpconfigboard.cmake'})" in cmake
        assert f'set(MICROPY_BOARD_PINS "{real_board / "pins.csv"}")' in cmake

    def test_the_board_header_and_manifest_relay_rather_than_copy(self, overrides: ModuleType, tmp_path: Path) -> None:
        # The real board cmake points MICROPY_FROZEN_MANIFEST at ${MICROPY_BOARD_DIR}, which is now
        # the generated directory - so both have to be relayed, and by reference so neither drifts.
        fake = _write_fake_lwip_tree(tmp_path / "micropython")
        overrides.apply_lwip_connection_counts_override(fake, tmp_path / "build_overrides", _REAL_BOARD, _LWIP_MACROS)
        override_dir = tmp_path / "build_overrides" / overrides.LWIP_OVERRIDE_BOARD_DIR_NAME
        real_board = fake / "ports" / "rp2" / "boards" / _REAL_BOARD
        assert (override_dir / "mpconfigboard.h").read_text() == f'#include "{real_board / "mpconfigboard.h"}"\n'
        assert (override_dir / "manifest.py").read_text() == f'include("{real_board / "manifest.py"}")\n'

    def test_is_idempotent(self, overrides: ModuleType, tmp_path: Path) -> None:
        fake = _write_fake_lwip_tree(tmp_path / "micropython")
        overrides_dir = tmp_path / "build_overrides"
        first = overrides.apply_lwip_connection_counts_override(fake, overrides_dir, _REAL_BOARD, _LWIP_MACROS)
        second = overrides.apply_lwip_connection_counts_override(fake, overrides_dir, _REAL_BOARD, _LWIP_MACROS)
        assert first == second

    def test_raises_without_applying_anything_when_the_anchor_is_gone(self, overrides: ModuleType, tmp_path: Path) -> None:
        fake = _write_fake_lwip_tree(tmp_path / "micropython", drop="#ifndef MEM_SIZE")
        overrides_dir = tmp_path / "build_overrides"
        with pytest.raises(overrides.OverrideError):
            overrides.apply_lwip_connection_counts_override(fake, overrides_dir, _REAL_BOARD, _LWIP_MACROS)
        assert not overrides_dir.exists()

    @pytest.mark.parametrize("macros", [{"MEMP_NUM_TCP_PCB": 8}, {**_LWIP_MACROS, "NOT_A_REAL_OPTION": 1}, {**_LWIP_MACROS, "TCP_MSS": -1}, {**_LWIP_MACROS, "TCP_MSS": 0}, {**_LWIP_MACROS, "LWIP_STATS": True}])
    def test_rejects_a_partial_unknown_or_ill_typed_option_set(self, overrides: ModuleType, tmp_path: Path, macros: "dict[str, object]") -> None:
        # Every option is required so the build is fully pinned by one reviewable table; a partial
        # set could not revert the atomic block here (#include first, then #undef), but -D could.
        fake = _write_fake_lwip_tree(tmp_path / "micropython")
        with pytest.raises(overrides.OverrideError):
            overrides.apply_lwip_connection_counts_override(fake, tmp_path / "build_overrides", _REAL_BOARD, macros)

    def test_every_settable_macro_is_one_the_pinned_source_actually_defines(self, overrides: ModuleType) -> None:
        assert set(overrides.LWIP_SETTABLE_MACROS) == set(overrides.LWIP_MACROS_GUARDED_IN_OPT_H) | set(overrides.LWIP_MACROS_PREDEFINED_BY_MICROPYTHON)
        assert not set(overrides.LWIP_MACROS_GUARDED_IN_OPT_H) & set(overrides.LWIP_MACROS_PREDEFINED_BY_MICROPYTHON)


# ---------------------------------------------------------------------------
# The ensemble. lwIP's options are not independent: lib/lwip/src/core/init.c turns each of these
# into a compile-time #error, and opt.h derives four more values from them.
# ---------------------------------------------------------------------------


def _pinned() -> "dict[str, int]":
    """MicroPython's own pinned block, which is itself a tuned set - see the test below."""
    return {
        "MEMP_NUM_TCP_PCB": 5, "MEMP_NUM_TCP_PCB_LISTEN": 8, "MEMP_NUM_PBUF": 16,
        "PBUF_POOL_SIZE": 16, "MEMP_NUM_UDP_PCB": 5, "LWIP_STATS": 0, "MEM_SIZE": 8000,
        "TCP_MSS": 800, "TCP_WND": 6400, "TCP_SND_BUF": 6400, "MEMP_NUM_TCP_SEG": 32,
    }


class TestLwipEnsemble:
    def test_the_derived_values_match_lwips_own_formulas(self, overrides: ModuleType) -> None:
        # opt.h computes these from TCP_MSS/TCP_SND_BUF; none is settable here, and most of
        # init.c's sanity checks are really about them rather than the values actually set.
        # 876, not 856: pbuf.h's PBUF_IP_HLEN is 40 under LWIP_IPV6, which the rp2 port enables.
        assert overrides.derive_lwip_dependents(_pinned()) == {
            "TCP_SND_QUEUELEN": 32, "TCP_SNDLOWAT": 3200, "TCP_SNDQUEUELOWAT": 16, "PBUF_POOL_BUFSIZE": 876,
        }

    def test_the_pbuf_header_allowance_matches_the_ipv6_enabled_port(self, overrides: ModuleType) -> None:
        # The constant that was wrong: the rp2 port sets LWIP_IPV6 = 1, so pbuf.h takes IP_HLEN 40.
        # It cancels out of the TCP_WND-vs-pool check (both sides shift by 20) but not out of
        # PBUF_POOL_BUFSIZE itself, which is what the pool's real RAM cost is computed from.
        assert overrides._PBUF_PROTOCOL_HEADER_BYTES == 14 + 40 + 20  # LINK + IP(v6) + TRANSPORT
        usable = overrides.derive_lwip_dependents(_pinned())["PBUF_POOL_BUFSIZE"] - overrides._PBUF_PROTOCOL_HEADER_BYTES
        assert usable == _pinned()["TCP_MSS"] + 2  # TCP_MSS plus the 4-byte alignment pad

    def test_micropythons_own_pinned_block_is_coherent(self, overrides: ModuleType) -> None:
        # The evidence that these are a tuned SET, not independent knobs: the pinned block sits
        # exactly on lwIP's own MEMP_NUM_TCP_SEG >= TCP_SND_QUEUELEN boundary, 32 against 32.
        assert overrides.check_lwip_ensemble(_pinned()) == []
        assert overrides.derive_lwip_dependents(_pinned())["TCP_SND_QUEUELEN"] == _pinned()["MEMP_NUM_TCP_SEG"]

    def test_the_shipped_table_is_coherent_at_every_devices_own_ceiling(self, overrides: ModuleType, repo_root: Path) -> None:
        import tomllib

        with (repo_root / "toolchain" / "versions.toml").open("rb") as f:
            macros = tomllib.load(f)["lwip"]
        for toml_path in sorted((repo_root / "devices").glob("*.toml")):
            if toml_path.name.startswith("zz_test_"):
                continue
            with toml_path.open("rb") as f:
                ceiling = tomllib.load(f)["device"].get("max_connections")
            assert overrides.check_lwip_ensemble(macros, ceiling) == [], f"{toml_path.name} admits {ceiling} connections the shipped [lwip] table cannot serve"

    @pytest.mark.parametrize(
        ("change", "expect"),
        [
            # Trap A's exact shape: TCP_MSS left at lwIP's own 536 fallback while the rest stands.
            ({"TCP_MSS": 536}, "MEMP_NUM_TCP_SEG"),
            ({"MEMP_NUM_TCP_SEG": 16}, "MEMP_NUM_TCP_SEG"),
            ({"TCP_SND_BUF": 1000}, "TCP_SND_BUF"),
            ({"PBUF_POOL_SIZE": 4}, "TCP_WND"),
            ({"TCP_WND": 400}, "TCP_WND"),
            # The init.c checks on the u16_t ranges and the per-protocol pcb floors.
            ({"TCP_MSS": 8300, "TCP_WND": 8300, "TCP_SND_BUF": 65000}, "TCP_SNDLOWAT (32500, derived from TCP_SND_BUF/TCP_MSS) >= 0xFFFF - 4 * TCP_MSS"),
            ({"PBUF_POOL_SIZE": 0, "TCP_WND": 70000}, "TCP_WND (70000) > 0xFFFF"),
            ({"MEMP_NUM_TCP_PCB": 0}, "MEMP_NUM_TCP_PCB (0) <= 0"),
            ({"MEMP_NUM_UDP_PCB": 0}, "MEMP_NUM_UDP_PCB (0) <= 0"),
        ],
    )
    def test_one_value_moved_alone_is_refused_by_name(self, overrides: ModuleType, change: "dict[str, int]", expect: str) -> None:
        problems = overrides.check_lwip_ensemble({**_pinned(), **change})
        assert problems, f"{change} left the set incoherent but was accepted"
        assert any(expect in p for p in problems), problems

    @pytest.mark.parametrize(
        ("change", "expect"),
        [
            ({"TCP_MSS": 1, "TCP_SND_BUF": 16384}, "TCP_SND_QUEUELEN (65536, derived from TCP_SND_BUF/TCP_MSS) > 0xFFFF"),
            ({"TCP_SND_BUF": 0}, "TCP_SND_QUEUELEN (0, derived from TCP_SND_BUF/TCP_MSS) < 2"),
        ],
    )
    def test_the_derived_queue_length_must_fit_lwips_own_bounds(self, overrides: ModuleType, change: "dict[str, int]", expect: str) -> None:
        problems = overrides.check_lwip_ensemble({**_pinned(), **change})
        assert any(expect in p for p in problems), problems

    def test_the_pbuf_size_checks_are_restated_even_though_the_formula_keeps_them_clear(self, overrides: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
        # TCP_MSS >= 1 keeps PBUF_POOL_BUFSIZE above both floors, so only a forced value reaches
        # the two checks - which still have to be there for the restatement to be complete.
        real = overrides.derive_lwip_dependents
        monkeypatch.setattr(overrides, "derive_lwip_dependents", lambda m: {**real(m), "PBUF_POOL_BUFSIZE": 4})
        problems = overrides.check_lwip_ensemble(_pinned())
        assert any("PBUF_POOL_BUFSIZE (4) <= MEM_ALIGNMENT (4)" in p for p in problems), problems
        assert any("PBUF_POOL_BUFSIZE (4) leaves no room" in p for p in problems), problems

    @pytest.mark.parametrize(
        ("forced", "expect"),
        [
            # opt.h's ceil(4 * SND_BUF / MSS) is never below 2 * floor(SND_BUF / MSS) ...
            ({"TCP_SND_QUEUELEN": 15}, "TCP_SND_QUEUELEN (15) < 2 * (TCP_SND_BUF / TCP_MSS) (16)"),
            # ... and its min(..., SND_BUF - 1) never reaches SND_BUF, so only a forced value gets here.
            ({"TCP_SNDLOWAT": 6400}, "TCP_SNDLOWAT (6400) >= TCP_SND_BUF (6400)"),
        ],
    )
    def test_the_send_queue_checks_are_restated_even_though_the_formula_keeps_them_clear(self, overrides: ModuleType, monkeypatch: pytest.MonkeyPatch, forced: "dict[str, int]", expect: str) -> None:
        real = overrides.derive_lwip_dependents
        monkeypatch.setattr(overrides, "derive_lwip_dependents", lambda m: {**real(m), **forced})
        problems = overrides.check_lwip_ensemble(_pinned())
        assert any(expect in p for p in problems), problems

    def test_an_mss_that_underflows_lwips_own_sndlowat_is_refused_by_name(self, overrides: ModuleType) -> None:
        # init.c's (16 * 1024) - 1 bound, one below and at: 16382 passes this check, 16383 does not.
        below = overrides.check_lwip_ensemble({**_pinned(), "TCP_MSS": 16382})
        at = overrides.check_lwip_ensemble({**_pinned(), "TCP_MSS": 16383})
        assert not any("underflows" in p for p in below), below
        assert any("TCP_MSS (16383) >= 16383, which underflows" in p for p in at), at

    @pytest.mark.parametrize(
        ("change", "derived"),
        [
            # Each where opt.h's rounding or its floor decides the value, not the common case.
            ({"TCP_SND_BUF": 6401}, {"TCP_SND_QUEUELEN": 33}),  # ceil(4 * 6401 / 800), not floor
            ({"TCP_SND_BUF": 3200}, {"TCP_SNDLOWAT": 1601}),  # 2 * MSS + 1 outweighs SND_BUF / 2
            ({"TCP_SND_BUF": 1600}, {"TCP_SND_QUEUELEN": 8, "TCP_SNDQUEUELOWAT": 5}),  # the floor of 5
            ({"TCP_SND_BUF": 1601}, {"TCP_SNDLOWAT": 1600}),  # capped at SND_BUF - 1
            ({"TCP_MSS": 801}, {"PBUF_POOL_BUFSIZE": 876}),  # 801 + 74 rounded up to MEM_ALIGNMENT
        ],
    )
    def test_the_derived_values_follow_opt_hs_rounding_at_its_edges(self, overrides: ModuleType, change: "dict[str, int]", derived: "dict[str, int]") -> None:
        got = overrides.derive_lwip_dependents({**_pinned(), **change})
        assert {key: got[key] for key in derived} == derived, got

    @pytest.mark.parametrize(
        ("at", "past", "problem"),
        [
            # init.c's own comparison operators, each pinned on both sides of its boundary: the value
            # that still passes and the first one refused (lib/lwip/src/core/init.c).
            ({"TCP_WND": 800}, {"TCP_WND": 799}, "< TCP_MSS"),
            ({"TCP_SND_BUF": 1600, "TCP_WND": 1600}, {"TCP_SND_BUF": 1599, "TCP_WND": 1599}, "< 2 * TCP_MSS"),
            ({"TCP_WND": 16 * 802}, {"TCP_WND": 16 * 802 + 1}, "> PBUF_POOL_SIZE * (PBUF_POOL_BUFSIZE - headers)"),
            ({"TCP_WND": 0xFFFF, "PBUF_POOL_SIZE": 0}, {"TCP_WND": 0x10000, "PBUF_POOL_SIZE": 0}, "> 0xFFFF - it must fit"),
        ],
    )
    def test_each_init_c_check_holds_exactly_at_its_own_boundary(self, overrides: ModuleType, at: "dict[str, int]", past: "dict[str, int]", problem: str) -> None:
        assert not any(problem in p for p in overrides.check_lwip_ensemble({**_pinned(), **at})), at
        assert any(problem in p for p in overrides.check_lwip_ensemble({**_pinned(), **past})), past

    @pytest.mark.parametrize(
        ("at", "past", "problem"),
        [
            ({"TCP_SND_QUEUELEN": 2}, {"TCP_SND_QUEUELEN": 1}, "< 2 - lwIP needs"),
            ({"TCP_SND_QUEUELEN": 0xFFFF}, {"TCP_SND_QUEUELEN": 0x10000}, "> 0xFFFF - it must fit"),
            ({"TCP_SNDQUEUELOWAT": 31}, {"TCP_SNDQUEUELOWAT": 32}, "TCP_SNDQUEUELOWAT"),
            ({"TCP_SNDLOWAT": 0xFFFF - 4 * 800 - 1}, {"TCP_SNDLOWAT": 0xFFFF - 4 * 800}, "4 * TCP_MSS below"),
        ],
    )
    def test_each_check_on_a_derived_value_holds_exactly_at_its_own_boundary(
        self, overrides: ModuleType, monkeypatch: pytest.MonkeyPatch, at: "dict[str, int]", past: "dict[str, int]", problem: str,
    ) -> None:
        # opt.h's formulas never reach these edges from a sane table, so the derived value is forced.
        real = overrides.derive_lwip_dependents
        forced: dict[str, int] = {}
        monkeypatch.setattr(overrides, "derive_lwip_dependents", lambda m: {**real(m), **forced})
        forced.update(at)
        assert not any(problem in p for p in overrides.check_lwip_ensemble(_pinned())), at
        forced.update(past)
        assert any(problem in p for p in overrides.check_lwip_ensemble(_pinned())), past

    @pytest.mark.parametrize("ceiling", [0, -1])
    def test_a_ceiling_admitting_no_connection_is_refused_by_name(self, overrides: ModuleType, ceiling: int) -> None:
        # A problem entry, like every other relationship here - never a ZeroDivisionError from the
        # per-connection share, and never a silent pass.
        problems = overrides.check_lwip_ensemble(_pinned(), ceiling)
        assert problems == [f"max_connections ({ceiling}) < 1 - the per-connection relationships are undefined for a ceiling admitting no connection"]

    def test_apply_refuses_an_incoherent_set_before_writing_anything(self, overrides: ModuleType, tmp_path: Path) -> None:
        fake = _write_fake_lwip_tree(tmp_path / "micropython")
        overrides_dir = tmp_path / "build_overrides"
        with pytest.raises(overrides.OverrideError, match="not a coherent set"):
            overrides.apply_lwip_connection_counts_override(fake, overrides_dir, _REAL_BOARD, {**_pinned(), "MEMP_NUM_TCP_SEG": 8})
        assert not overrides_dir.exists()

    @pytest.mark.parametrize("ceiling", [5, 8, 12])
    def test_the_shared_pools_must_serve_every_admitted_connection_not_just_one(self, overrides: ModuleType, ceiling: int) -> None:
        # lwIP's own checks size MEMP_NUM_TCP_SEG and MEM_SIZE for a single connection. Both are
        # global while TCP_SND_QUEUELEN is per-connection, so a ceiling above what they can serve
        # accepts work the stack cannot push - admission without service.
        problems = overrides.check_lwip_ensemble(_pinned(), ceiling)
        assert any("cannot each hold a full send window" in p for p in problems), problems
        assert any("per admitted connection" in p for p in problems), problems

    def test_every_admitted_connection_leaves_three_pcbs_spare(self, overrides: ModuleType) -> None:
        # The shipped pattern at 6 (PCB 9, SEG 48, MEM_SIZE 12000) is clean; one PCB fewer is
        # refused by name and alone, so the rule is the PCB one and not a pool check tripping.
        at_six = {**_pinned(), "MEMP_NUM_TCP_PCB": 9, "MEMP_NUM_TCP_SEG": 48, "MEM_SIZE": 12000}
        assert overrides.check_lwip_ensemble(at_six, 6) == []
        problems = overrides.check_lwip_ensemble({**at_six, "MEMP_NUM_TCP_PCB": 8}, 6)
        assert len(problems) == 1, problems
        assert problems[0].startswith("MEMP_NUM_TCP_PCB (8) < max_connections + 3 (9)"), problems

    def test_the_mem_size_floor_is_the_fielded_designs_own_share(self, overrides: ModuleType) -> None:
        # 8000 / 4 = 2000. A relationship, not a tuning target: raising the ceiling may not quietly
        # give each connection a smaller share of the arena every outbound byte is copied into.
        assert _pinned()["MEM_SIZE"] // 4 == overrides.MEM_SIZE_BYTES_PER_CONNECTION_FLOOR

    def test_the_generated_header_carries_a_sentinel_the_build_check_demands(self, overrides: ModuleType, tmp_path: Path) -> None:
        # Values alone cannot prove the shim was REACHED: a run asking for the defaults would
        # verify clean against a build the override never touched.
        fake = _write_fake_lwip_tree(tmp_path / "micropython")
        overrides.apply_lwip_connection_counts_override(fake, tmp_path / "build_overrides", _REAL_BOARD, _pinned())
        generated = (tmp_path / "build_overrides" / overrides.LWIP_OVERRIDE_BOARD_DIR_NAME / overrides.LWIP_OVERRIDE_INCLUDE_DIR_NAME / "lwipopts.h").read_text()
        assert f"#define {overrides.LWIP_OVERRIDE_SENTINEL} 1" in generated


# ---------------------------------------------------------------------------
# The readback: what the firmware's own translation unit resolved each option to. Driven through a
# stub compiler, so every outcome of the real `-E` run is reachable without an ARM toolchain.
# ---------------------------------------------------------------------------


def _fake_build(tmp_path: Path, *, stdout: str, returncode: int = 0, drop_key: str | None = None) -> "tuple[Path, str, Path]":
    build_dir = tmp_path / "build-RPI_PICO_W"
    flags = build_dir / "CMakeFiles" / "firmware.dir"
    flags.mkdir(parents=True)
    lines = {"C_DEFINES": "-DPICO_BOARD=pico_w", "C_INCLUDES": "-I/over/ride -I/real/lwip_inc", "C_FLAGS": "-O2"}
    (flags / "flags.make").write_text("".join(f"{key} = {value}\n" for key, value in lines.items() if key != drop_key))
    argv_log = tmp_path / "argv.txt"
    compiler = tmp_path / "fake-gcc"
    compiler.write_text(f"#!{sys.executable}\nimport sys, pathlib\npathlib.Path({str(argv_log)!r}).write_text(' '.join(sys.argv[1:]))\nsys.stdout.write({stdout!r})\nsys.stderr.write('boom')\nsys.exit({returncode})\n")
    compiler.chmod(0o755)
    return build_dir, str(compiler), argv_log


def _probe_lines(values: "dict[str, str]") -> str:
    return "".join(f'LWIPPROBE "{name}" = {value}\n' for name, value in values.items())


class TestLwipBuildReadback:
    def test_a_build_that_resolved_every_option_as_asked_verifies_clean(self, overrides: ModuleType, tmp_path: Path) -> None:
        asked = _pinned()
        resolved = {name: f"({value})" for name, value in asked.items()} | {overrides.LWIP_OVERRIDE_SENTINEL: "1"}
        build_dir, compiler, argv_log = _fake_build(tmp_path, stdout=_probe_lines(resolved))
        found = overrides.verify_lwip_macros_in_build(build_dir, asked, compiler)
        assert {name: found[name] for name in asked} == asked
        assert "-I/over/ride -I/real/lwip_inc" in argv_log.read_text(), "the real build's own flags must reach the preprocessor"

    def test_an_expression_value_is_evaluated_not_compared_as_text(self, overrides: ModuleType, tmp_path: Path) -> None:
        asked = _pinned()
        resolved = {name: f"({value})" for name, value in asked.items()} | {"TCP_WND": "(8 * (800))", overrides.LWIP_OVERRIDE_SENTINEL: "1"}
        build_dir, compiler, _argv = _fake_build(tmp_path, stdout=_probe_lines(resolved))
        assert overrides.verify_lwip_macros_in_build(build_dir, asked, compiler)["TCP_WND"] == 6400

    def test_a_value_that_did_not_land_is_named_with_both_numbers(self, overrides: ModuleType, tmp_path: Path) -> None:
        asked = _pinned()
        resolved = {name: str(value) for name, value in asked.items()} | {"MEMP_NUM_TCP_PCB": "4", overrides.LWIP_OVERRIDE_SENTINEL: "1"}
        build_dir, compiler, _argv = _fake_build(tmp_path, stdout=_probe_lines(resolved))
        with pytest.raises(overrides.OverrideError, match="MEMP_NUM_TCP_PCB: asked 5, built 4"):
            overrides.verify_lwip_macros_in_build(build_dir, asked, compiler)

    def test_a_header_never_reached_is_named_as_such_not_as_an_unparseable_value(self, overrides: ModuleType, tmp_path: Path) -> None:
        # Unreached, the preprocessor leaves the sentinel as its own bare name - which must read as
        # absent, so the message says what went wrong (the redirect) rather than failing to parse.
        asked = _pinned()
        resolved = {name: str(value) for name, value in asked.items()} | {overrides.LWIP_OVERRIDE_SENTINEL: overrides.LWIP_OVERRIDE_SENTINEL}
        build_dir, compiler, _argv = _fake_build(tmp_path, stdout=_probe_lines(resolved))
        with pytest.raises(overrides.OverrideError, match=r"sentinel .* is absent"):
            overrides.verify_lwip_macros_in_build(build_dir, asked, compiler)

    def test_a_non_constant_value_fails_loudly_rather_than_guessing(self, overrides: ModuleType, tmp_path: Path) -> None:
        asked = _pinned()
        resolved = {name: str(value) for name, value in asked.items()} | {"MEM_SIZE": "sizeof(struct x)", overrides.LWIP_OVERRIDE_SENTINEL: "1"}
        build_dir, compiler, _argv = _fake_build(tmp_path, stdout=_probe_lines(resolved))
        with pytest.raises(overrides.OverrideError, match="cannot"):
            overrides.read_lwip_macros_from_build(build_dir, asked, compiler)

    def test_a_failed_preprocessor_run_reports_its_own_stderr(self, overrides: ModuleType, tmp_path: Path) -> None:
        build_dir, compiler, _argv = _fake_build(tmp_path, stdout="", returncode=1)
        with pytest.raises(overrides.OverrideError, match="failed:\nboom"):
            overrides.read_lwip_macros_from_build(build_dir, _pinned(), compiler)

    def test_a_build_that_never_configured_is_refused_before_preprocessing(self, overrides: ModuleType, tmp_path: Path) -> None:
        with pytest.raises(overrides.OverrideError, match="no compile flags"):
            overrides.read_lwip_macros_from_build(tmp_path / "build-RPI_PICO_W", _pinned(), "never-run")

    def test_a_changed_flags_layout_is_refused_by_name(self, overrides: ModuleType, tmp_path: Path) -> None:
        build_dir, compiler, _argv = _fake_build(tmp_path, stdout="", drop_key="C_INCLUDES")
        with pytest.raises(overrides.OverrideError, match="no C_INCLUDES line"):
            overrides.read_lwip_macros_from_build(build_dir, _pinned(), compiler)

    def test_a_missing_compiler_is_named_not_a_bare_traceback(self, overrides: ModuleType, tmp_path: Path) -> None:
        build_dir, _compiler, _argv = _fake_build(tmp_path, stdout="")
        missing = str(tmp_path / "no-such-gcc")
        with pytest.raises(overrides.OverrideError, match=r"cannot run the C compiler .*no-such-gcc"):
            overrides.read_lwip_macros_from_build(build_dir, _pinned(), missing)

    def test_a_hung_compiler_is_named_after_the_timeout(self, overrides: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        build_dir, _compiler, _argv = _fake_build(tmp_path, stdout="")
        sleeper = tmp_path / "slow-gcc"
        sleeper.write_text(f"#!{sys.executable}\nimport time\ntime.sleep(30)\n")
        sleeper.chmod(0o755)
        monkeypatch.setattr(overrides, "_PREPROCESS_TIMEOUT_S", 0.2)
        with pytest.raises(overrides.OverrideError, match=r"compiler .*slow-gcc.* did not finish"):
            overrides.read_lwip_macros_from_build(build_dir, _pinned(), str(sleeper))

    def test_the_compiler_cmake_recorded_is_used_when_none_is_passed(self, overrides: ModuleType, tmp_path: Path) -> None:
        # The build's own compiler, not whichever arm-none-eabi-gcc PATH happens to find first.
        asked = _pinned()
        resolved = {name: str(value) for name, value in asked.items()} | {overrides.LWIP_OVERRIDE_SENTINEL: "1"}
        build_dir, compiler, argv_log = _fake_build(tmp_path, stdout=_probe_lines(resolved))
        flags_make = build_dir / "CMakeFiles" / "firmware.dir" / "flags.make"
        flags_make.write_text(f"# compile ASM with /nowhere/asm-gcc\n# compile C with {compiler}\n" + flags_make.read_text())
        assert overrides.verify_lwip_macros_in_build(build_dir, asked)["TCP_MSS"] == 800
        assert argv_log.is_file(), "the recorded compiler was not the one run"

    def test_the_cmake_cache_compiler_is_the_fallback_when_flags_make_names_none(self, overrides: ModuleType, tmp_path: Path) -> None:
        build_dir, compiler, _argv = _fake_build(tmp_path, stdout="")
        (build_dir / "CMakeCache.txt").write_text(f"CMAKE_C_FLAGS:STRING=\nCMAKE_C_COMPILER:FILEPATH={compiler}\n")
        assert overrides._recorded_c_compiler(build_dir, "") == compiler
        assert overrides._recorded_c_compiler(tmp_path / "unconfigured", "") == overrides._DEFAULT_COMPILER

    def test_an_explicit_compiler_wins_over_the_recorded_one(self, overrides: ModuleType, tmp_path: Path) -> None:
        build_dir, compiler, argv_log = _fake_build(tmp_path, stdout="")
        flags_make = build_dir / "CMakeFiles" / "firmware.dir" / "flags.make"
        flags_make.write_text(f"# compile C with {tmp_path / 'no-such-gcc'}\n" + flags_make.read_text())
        overrides.read_lwip_macros_from_build(build_dir, _pinned(), compiler)
        assert argv_log.is_file()

    def test_an_undefined_option_reads_as_absent_and_is_named(self, overrides: ModuleType, tmp_path: Path) -> None:
        # Any undefined macro comes back as its own bare name, not only the sentinel.
        asked = _pinned()
        resolved = {name: str(value) for name, value in asked.items()} | {"TCP_MSS": "TCP_MSS", overrides.LWIP_OVERRIDE_SENTINEL: "1"}
        build_dir, compiler, _argv = _fake_build(tmp_path, stdout=_probe_lines(resolved))
        assert "TCP_MSS" not in overrides.read_lwip_macros_from_build(build_dir, asked, compiler)
        with pytest.raises(overrides.OverrideError, match="TCP_MSS: asked 800, built None"):
            overrides.verify_lwip_macros_in_build(build_dir, asked, compiler)


class TestEvalMacroExpression:
    @pytest.mark.parametrize(
        ("text", "value"),
        [("(8 * (800))", 6400), ("(-7/2)", -3), ("(7/-2)", -3), ("(-8/2)", -4), ("-(3)", -3), ("(1<<4)", 16), ("(256>>2)", 64), ("((4 * 6400 + (800 - 1)) / 800)", 32)],
    )
    def test_evaluates_c_integer_arithmetic(self, overrides: ModuleType, text: str, value: int) -> None:
        # C's `/` truncates toward zero; Python's `//` floors, which differs for a negative operand.
        assert overrides._eval_macro_expression(text) == value

    @pytest.mark.parametrize(
        ("text", "message"),
        [
            ("(u16_t)(800)", "cannot evaluate"),  # a cast is not arithmetic over literals
            ("800U", "cannot parse"),  # the options set here never carry a suffix - refuse, not guess
            ("(1/0)", "divides by zero"),
            ("(1<<-1)", "shift count"),
            ("(1<<64)", "shift count"),
        ],
    )
    def test_refuses_what_it_cannot_evaluate_exactly(self, overrides: ModuleType, text: str, message: str) -> None:
        with pytest.raises(overrides.OverrideError, match=message):
            overrides._eval_macro_expression(text)


class TestBuildFirmwareAppliesTheLwipOverride:
    """Guards build_firmware()'s wiring the way TestBuildUnixPortAppliesTheOverride guards the Unix
    port's: the override's make variables reach `make`, and the readback runs on the real build."""

    @pytest.fixture
    def setup_toolchain(self, repo_root: Path) -> ModuleType:
        return load_script_module(repo_root / "toolchain" / "setup_toolchain.py", "setup_toolchain")

    def _fake_runner(self, rp2_dir: Path, recorded: "list[list[str]]") -> "Callable[..., str]":
        def fake_run(cmd: "list[str]", cwd: "Path | None" = None, *, check: bool = True, env: "dict[str, str] | None" = None) -> str:
            recorded.append(cmd)
            build_dir = rp2_dir / f"build-{_REAL_BOARD}"
            (build_dir / "CMakeFiles" / "firmware.dir").mkdir(parents=True, exist_ok=True)
            (build_dir / "CMakeFiles" / "firmware.dir" / "flags.make").write_text("C_DEFINES = \nC_INCLUDES = \nC_FLAGS = \n")
            (build_dir / "firmware.uf2").write_bytes(b"")
            return ""

        return fake_run

    def test_make_gets_the_redirect_and_the_build_is_verified_against_the_table(self, setup_toolchain: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        toolchain_dir = tmp_path / "toolchain"
        fake_mp_dir = _write_fake_lwip_tree(toolchain_dir / "micropython")
        rp2_dir = fake_mp_dir / "ports" / "rp2"
        recorded: list[list[str]] = []
        verified: list[tuple[Path, dict[str, int]]] = []
        monkeypatch.setattr(setup_toolchain, "run", self._fake_runner(rp2_dir, recorded))

        def record_verify(build_dir: Path, macros: "dict[str, int]", compiler: "str | None" = None) -> "dict[str, int]":
            verified.append((build_dir, macros))
            return dict(macros)

        monkeypatch.setattr(setup_toolchain.micropython_overrides, "verify_lwip_macros_in_build", record_verify)

        uf2 = setup_toolchain.build_firmware(fake_mp_dir, _REAL_BOARD, 4, toolchain_dir=toolchain_dir, lwip_macros=_pinned())

        assert uf2 == rp2_dir / f"build-{_REAL_BOARD}" / "firmware.uf2"
        (make_cmd,) = recorded
        assert make_cmd[0] == "make"
        assert f"BOARD={_REAL_BOARD}" in make_cmd
        assert f"BOARD_DIR={toolchain_dir / 'build_overrides' / setup_toolchain.micropython_overrides.LWIP_OVERRIDE_BOARD_DIR_NAME}" in make_cmd
        assert verified == [(rp2_dir / f"build-{_REAL_BOARD}", _pinned())], "the readback must run on the real build dir with the very table applied"

    def test_an_anchorless_tree_raises_before_make_ever_runs(self, setup_toolchain: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        toolchain_dir = tmp_path / "toolchain"
        fake_mp_dir = _write_fake_lwip_tree(toolchain_dir / "micropython", drop="#ifndef MEM_SIZE")
        recorded: list[list[str]] = []
        monkeypatch.setattr(setup_toolchain, "run", self._fake_runner(fake_mp_dir / "ports" / "rp2", recorded))
        with pytest.raises(setup_toolchain.micropython_overrides.OverrideError):
            setup_toolchain.build_firmware(fake_mp_dir, _REAL_BOARD, 4, toolchain_dir=toolchain_dir, lwip_macros=_pinned())
        assert recorded == []

    def test_a_versions_file_without_an_lwip_table_is_named(self, setup_toolchain: ModuleType, tmp_path: Path) -> None:
        versions = tmp_path / "versions.toml"
        versions.write_text('[micropython]\nref = "v1.29.0"\n')
        with pytest.raises(setup_toolchain.SetupError, match=r"no \[lwip\] table"):
            setup_toolchain.load_lwip_macros(versions)

    def test_without_an_explicit_table_the_build_applies_versions_tomls_own(self, setup_toolchain: ModuleType, repo_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        # The path every real `setup` run takes: no table passed, so the pinned one must be what
        # reaches both the generated header and the readback - never lwIP's or the port's defaults.
        import tomllib

        with (repo_root / "toolchain" / "versions.toml").open("rb") as f:
            pinned = tomllib.load(f)["lwip"]
        assert setup_toolchain.load_lwip_macros() == pinned
        toolchain_dir = tmp_path / "toolchain"
        fake_mp_dir = _write_fake_lwip_tree(toolchain_dir / "micropython")
        verified: list[dict[str, int]] = []
        monkeypatch.setattr(setup_toolchain, "run", self._fake_runner(fake_mp_dir / "ports" / "rp2", []))

        def record_verify(_build_dir: Path, macros: "dict[str, int]", _compiler: "str | None" = None) -> "dict[str, int]":
            verified.append(macros)
            return dict(macros)

        monkeypatch.setattr(setup_toolchain.micropython_overrides, "verify_lwip_macros_in_build", record_verify)
        setup_toolchain.build_firmware(fake_mp_dir, _REAL_BOARD, 4, toolchain_dir=toolchain_dir)
        assert verified == [pinned]
