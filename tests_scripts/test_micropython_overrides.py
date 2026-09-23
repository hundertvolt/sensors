"""Tests toolchain/micropython_overrides.py's unix_kbd_intr override in isolation - the anchor
verification and the generated files, against synthetic fixture trees, never a real compile (that
is what the real Unix-port build already proves). SPECIFICATION.md Part B.14 has the mechanism."""

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


class TestVerifyLwipConnectionCountsAnchor:
    def test_passes_against_the_real_pinned_source(self, overrides: ModuleType, micropython_dir: Path) -> None:
        if not (micropython_dir / "lib" / "lwip" / "src" / "include" / "lwip" / "opt.h").is_file():
            pytest.skip(f"no real toolchain checkout with lwIP submodules at {micropython_dir} - build it first (scripts/test.sh does)")
        overrides.verify_lwip_connection_counts_anchor(micropython_dir, _REAL_BOARD)

    def test_raises_when_the_tree_is_missing_entirely(self, overrides: ModuleType, tmp_path: Path) -> None:
        with pytest.raises(overrides.OverrideError, match="not found"):
            overrides.verify_lwip_connection_counts_anchor(tmp_path, _REAL_BOARD)

    @pytest.mark.parametrize(
        "dropped",
        [
            "MEMP_NUM_TCP_PCB",  # lwIP's own guard - without it a value could not be injected at all
            "PBUF_POOL_SIZE",
            "#ifndef MEM_SIZE",  # trap A: the atomic block
            "#define TCP_MSS (800)",
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
        ],
    )
    def test_every_anchor_is_load_bearing(self, overrides: ModuleType, tmp_path: Path, dropped: str) -> None:
        # One parametrization per anchor: each must fail the verify step on its own, or it is
        # decorative and would let a restructuring release build silently unpatched.
        _write_fake_lwip_tree(tmp_path, drop=dropped)
        with pytest.raises(overrides.OverrideError):
            overrides.verify_lwip_connection_counts_anchor(tmp_path, _REAL_BOARD)


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

    @pytest.mark.parametrize("macros", [{"MEMP_NUM_TCP_PCB": 8}, {**_LWIP_MACROS, "NOT_A_REAL_OPTION": 1}, {**_LWIP_MACROS, "TCP_MSS": -1}, {**_LWIP_MACROS, "LWIP_STATS": True}])
    def test_rejects_a_partial_unknown_or_ill_typed_option_set(self, overrides: ModuleType, tmp_path: Path, macros: "dict[str, object]") -> None:
        # A partial set is the one that matters: MEM_SIZE alone disables the whole upstream block,
        # silently reverting TCP_MSS to lwIP's 536 and the segment count to 16 (trap A).
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
        ],
    )
    def test_one_value_moved_alone_is_refused_by_name(self, overrides: ModuleType, change: "dict[str, int]", expect: str) -> None:
        problems = overrides.check_lwip_ensemble({**_pinned(), **change})
        assert problems, f"{change} left the set incoherent but was accepted"
        assert any(expect in p for p in problems), problems

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
