"""Canonical, zero-touch overrides for MicroPython's own build: every one generates files and flags
entirely OUTSIDE the fetched checkout, and verifies a known anchor in the pinned source first so a
restructuring release fails loudly. Rationale and version-bump checklist: SPECIFICATION.md B.14."""

from __future__ import annotations

import ast
import re
import shlex
import subprocess
import tempfile
from pathlib import Path


class OverrideError(RuntimeError):
    """A pinned MicroPython source no longer matches what an override expects, so the override was
    NOT applied. Re-verify against the new source and update the override's anchor/generated
    content (SPECIFICATION.md Part B.14) - never silence this by removing the check."""


def _read_anchor_source(path: Path, override_name: str) -> str:
    if not path.exists():
        raise OverrideError(
            f"{override_name}: expected source file not found at {path} - MicroPython's own file "
            "layout has changed. Re-verify this override against the current pinned source and "
            "update it (SPECIFICATION.md Part B.14) before retrying.",
        )
    return path.read_text()


# ---------------------------------------------------------------------------------------------
# unix_kbd_intr: force the Unix port's "standard" variant to use MicroPython's own SAFE, deferred
# SIGINT-delivery path instead of its default immediate one. Full account: SPECIFICATION.md Part
# B.14.1, CLAUDE.md's Part F.6 entry.
# ---------------------------------------------------------------------------------------------

# The exact line as pinned (ports/unix/variants/mpconfigvariant_common.h): an UNGUARDED #define,
# which is why CFLAGS_EXTRA -D cannot override it - a later plain #define always wins over an
# earlier -D (verified 2026-09-15), and the redefinition warning is a hard failure here anyway.
_UNIX_KBD_INTR_ANCHOR = "#define MICROPY_ASYNC_KBD_INTR         (!MICROPY_PY_THREAD_GIL)"


def verify_unix_kbd_intr_anchor(micropython_dir: Path) -> Path:
    common_header = micropython_dir / "ports" / "unix" / "variants" / "mpconfigvariant_common.h"
    text = _read_anchor_source(common_header, "unix_kbd_intr")
    if _UNIX_KBD_INTR_ANCHOR not in text:
        raise OverrideError(
            f"unix_kbd_intr: expected anchor line not found in {common_header} - "
            "MICROPY_ASYNC_KBD_INTR's own definition has changed upstream (renamed, reguarded, or "
            "the async/immediate nlr_raise()-from-signal-handler mechanism itself was restructured "
            "in ports/unix/unix_mphal.c's sighandler()). Re-verify against the new pinned source "
            "and update this override's anchor and generated #undef/#define pair accordingly - "
            "SPECIFICATION.md Part B.14.1. Do NOT remove this check and build unpatched: the whole "
            "point is that an interrupt-mid-critical-section can corrupt VM state (reproduced "
            "directly as a garbled, impossible traceback - CLAUDE.md/SPECIFICATION.md Part F.6).",
        )
    return common_header


def apply_unix_kbd_intr_override(micropython_dir: Path, overrides_dir: Path) -> dict[str, str]:
    """Points the Unix standard variant's VARIANT_DIR at an external directory that #includes the
    real variant files and forces MICROPY_ASYNC_KBD_INTR to 0, selecting MicroPython's safe,
    deferred SIGINT path. Returns build_unix_port()'s extra `make` variables; see Part B.14.1."""
    verify_unix_kbd_intr_anchor(micropython_dir)
    real_variant_dir = micropython_dir / "ports" / "unix" / "variants" / "standard"
    override_dir = overrides_dir / "unix_kbd_intr_variant"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "mpconfigvariant.h").write_text(
        f'#include "{real_variant_dir / "mpconfigvariant.h"}"\n'
        "// SPECIFICATION.md Part B.14.1 / CLAUDE.md Part F.6: force MicroPython's own safe,\n"
        "// deferred SIGINT-delivery path - see toolchain/micropython_overrides.py.\n"
        "#undef MICROPY_ASYNC_KBD_INTR\n"
        "#define MICROPY_ASYNC_KBD_INTR (0)\n",
    )
    # mpconfigvariant.mk/manifest.py both relay to the real files rather than copying their
    # content, so neither can silently drift out of sync with a future pinned-version change -
    # `include()` is the freeze-manifest DSL's own primitive for exactly this (tools/manifestfile.py).
    (override_dir / "mpconfigvariant.mk").write_text(
        f'include {real_variant_dir / "mpconfigvariant.mk"}\n',
    )
    real_manifest = real_variant_dir / "manifest.py"
    if real_manifest.exists():
        (override_dir / "manifest.py").write_text(f'include("{real_manifest}")\n')
    return {"VARIANT": "standard", "VARIANT_DIR": str(override_dir)}


# ---------------------------------------------------------------------------------------------
# lwip_connection_counts: raise the rp2 firmware's simultaneous-TCP-connection ceiling and the
# buffering behind it. Full account, and why every macro goes through one generated header rather
# than a mix of -D and shim: SPECIFICATION.md Part B.14.2.
# ---------------------------------------------------------------------------------------------

LWIP_OVERRIDE_BOARD_DIR_NAME = "lwip_connection_counts_board"
LWIP_OVERRIDE_INCLUDE_DIR_NAME = "lwipopts_override"

# Split by how the PINNED source defines each macro, because that is what decides whether a plain
# -D could ever be trusted for it - guarded ones would take a -D, predefined ones silently would
# not (a later plain #define beats an earlier -D, B.14.1). Both go through the generated header.
LWIP_MACROS_GUARDED_IN_OPT_H = ("MEMP_NUM_TCP_PCB", "MEMP_NUM_TCP_PCB_LISTEN", "MEMP_NUM_PBUF", "PBUF_POOL_SIZE")
LWIP_MACROS_PREDEFINED_BY_MICROPYTHON = ("MEMP_NUM_UDP_PCB", "LWIP_STATS", "MEM_SIZE", "TCP_MSS", "TCP_WND", "TCP_SND_BUF", "MEMP_NUM_TCP_SEG")
LWIP_SETTABLE_MACROS = LWIP_MACROS_GUARDED_IN_OPT_H + LWIP_MACROS_PREDEFINED_BY_MICROPYTHON

# The five MEM_SIZE-group defines are ONE atomic `#ifndef MEM_SIZE` block upstream, so a partial
# set would silently revert TCP_MSS to lwIP's 536 and the segment count to 16. Every macro above is
# therefore required, always - restating an unchanged value costs nothing and closes that trap.
_LWIP_COMMON_ANCHORS = (
    "#ifndef MEM_SIZE",
    "#define MEM_SIZE (8000)",
    "#define TCP_MSS (800)",
    "#define TCP_WND (8 * TCP_MSS)",
    "#define TCP_SND_BUF (8 * TCP_MSS)",
    "#define MEMP_NUM_TCP_SEG (32)",
    "#define MEMP_NUM_UDP_PCB                (4 + LWIP_MDNS_RESPONDER)",
    "#define LWIP_STATS                      0",
    "#define LWIP_NETCONN                    0",
)
# lwip_inc must stay a PLAIN target-level include dir: a BEFORE form there would beat the
# directory-scope one this override prepends, and the real lwipopts.h would silently win again.
_RP2_CMAKE_ANCHORS = (
    "include(${MICROPY_BOARD_DIR}/mpconfigboard.cmake)",
    "target_include_directories(${MICROPY_TARGET} PRIVATE\n        lwip_inc\n    )",
    "if(NOT MICROPY_BOARD_PINS)",
)
_RP2_LWIPOPTS_ANCHOR = '#include "extmod/lwip-include/lwipopts_common.h"'
_BOARD_CMAKE_ANCHOR = "set(MICROPY_FROZEN_MANIFEST ${MICROPY_BOARD_DIR}/manifest.py)"

_LWIP_REVERIFY = (
    "Re-verify this override against the new pinned source and update its anchors "
    "(SPECIFICATION.md Part B.14.2). Do NOT remove the check and build anyway: an lwIP option that "
    "silently keeps its old value produces a firmware that accepts fewer connections than its own "
    "max_connections admits, which looks like an application bug and is not one."
)


def _require_anchor(text: str, anchor: str, where: Path, what: str) -> None:
    if anchor not in text:
        raise OverrideError(f"lwip_connection_counts: expected {what} not found in {where} - {anchor!r} is gone. {_LWIP_REVERIFY}")


def verify_lwip_connection_counts_anchor(micropython_dir: Path, board: str) -> None:
    """Checks every pinned-source fact this override depends on: lwIP's own `#if !defined` guards,
    MicroPython's atomic MEM_SIZE block and its plain #defines, the rp2 CMake include order, and
    the board directory's own shape. Raises OverrideError naming the drift; see Part B.14.2."""
    opt_h = micropython_dir / "lib" / "lwip" / "src" / "include" / "lwip" / "opt.h"
    opt_text = _read_anchor_source(opt_h, "lwip_connection_counts")
    for macro in LWIP_MACROS_GUARDED_IN_OPT_H:
        _require_anchor(opt_text, f"#if !defined {macro} || defined __DOXYGEN__", opt_h, f"lwIP's own guard for {macro}")

    common_h = micropython_dir / "extmod" / "lwip-include" / "lwipopts_common.h"
    common_text = _read_anchor_source(common_h, "lwip_connection_counts")
    for anchor in _LWIP_COMMON_ANCHORS:
        _require_anchor(common_text, anchor, common_h, "MicroPython's own pinned lwIP option")

    rp2_lwipopts = micropython_dir / "ports" / "rp2" / "lwip_inc" / "lwipopts.h"
    _require_anchor(_read_anchor_source(rp2_lwipopts, "lwip_connection_counts"), _RP2_LWIPOPTS_ANCHOR, rp2_lwipopts, "the rp2 port's include of the common options")

    rp2_cmake = micropython_dir / "ports" / "rp2" / "CMakeLists.txt"
    cmake_text = _read_anchor_source(rp2_cmake, "lwip_connection_counts")
    for anchor in _RP2_CMAKE_ANCHORS:
        _require_anchor(cmake_text, anchor, rp2_cmake, "the rp2 port's board/include wiring")

    board_cmake = micropython_dir / "ports" / "rp2" / "boards" / board / "mpconfigboard.cmake"
    _require_anchor(_read_anchor_source(board_cmake, "lwip_connection_counts"), _BOARD_CMAKE_ANCHOR, board_cmake, f"{board}'s own frozen-manifest line")
    for name in ("mpconfigboard.h", "manifest.py", "pins.csv"):
        if not (board_cmake.parent / name).is_file():
            raise OverrideError(f"lwip_connection_counts: {board}'s board directory no longer contains {name} ({board_cmake.parent}), so the generated board directory cannot relay it. {_LWIP_REVERIFY}")


def _validate_lwip_macros(macros: dict[str, int]) -> None:
    missing = [name for name in LWIP_SETTABLE_MACROS if name not in macros]
    unknown = sorted(set(macros) - set(LWIP_SETTABLE_MACROS))
    if missing or unknown:
        raise OverrideError(
            f"lwip_connection_counts: [lwip] in toolchain/versions.toml must set exactly "
            f"{list(LWIP_SETTABLE_MACROS)} - missing {missing}, unrecognized {unknown}. Every macro is "
            "required even when unchanged, because the five MEM_SIZE-group values are one atomic "
            "upstream block and a partial set silently reverts TCP_MSS to 536.",
        )
    for name, value in macros.items():
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise OverrideError(f"lwip_connection_counts: [lwip].{name} must be a non-negative int, got {value!r}")


def apply_lwip_connection_counts_override(micropython_dir: Path, overrides_dir: Path, board: str, macros: dict[str, int]) -> dict[str, str]:
    """Generates an out-of-tree board directory whose own lwipopts.h #includes the real one and then
    redefines every lwIP option, reached through MicroPython's documented BOARD_DIR redirect.
    Returns build_firmware()'s extra `make` variables; full mechanism in Part B.14.2."""
    verify_lwip_connection_counts_anchor(micropython_dir, board)
    _validate_lwip_macros(macros)
    rp2_dir = micropython_dir / "ports" / "rp2"
    real_board_dir = rp2_dir / "boards" / board
    override_dir = overrides_dir / LWIP_OVERRIDE_BOARD_DIR_NAME
    include_dir = override_dir / LWIP_OVERRIDE_INCLUDE_DIR_NAME
    include_dir.mkdir(parents=True, exist_ok=True)

    redefines = "".join(f"#undef {name}\n#define {name} ({macros[name]})\n" for name in LWIP_SETTABLE_MACROS)
    (include_dir / "lwipopts.h").write_text(
        "// Generated by toolchain/micropython_overrides.py - SPECIFICATION.md Part B.14.2.\n"
        "// Found ahead of ports/rp2/lwip_inc/lwipopts.h, so these win over both MicroPython's own\n"
        "// plain #defines and lwIP's opt.h defaults; every option is set, never a subset.\n"
        f'#include "{rp2_dir / "lwip_inc" / "lwipopts.h"}"\n'
        f"{redefines}",
    )
    # include_directories(BEFORE) at the port's own directory scope, which every target there
    # inherits ahead of its own target-level dirs - the only ordering that beats `lwip_inc`.
    # MICROPY_BOARD_PINS is set rather than the csv copied, so pins can never drift from the pin.
    (override_dir / "mpconfigboard.cmake").write_text(
        "# Generated by toolchain/micropython_overrides.py - SPECIFICATION.md Part B.14.2.\n"
        f'set(MICROPY_BOARD_PINS "{real_board_dir / "pins.csv"}")\n'
        f"include({real_board_dir / 'mpconfigboard.cmake'})\n"
        f'include_directories(BEFORE "{include_dir}")\n',
    )
    # Relays, never copies, for the same reason B.14.1's manifest is an include(): neither can
    # drift from a future pinned-version change. The real board cmake points the frozen manifest at
    # ${MICROPY_BOARD_DIR}, which is now this directory, so manifest.py has to be relayed too.
    (override_dir / "mpconfigboard.h").write_text(f'#include "{real_board_dir / "mpconfigboard.h"}"\n')
    (override_dir / "manifest.py").write_text(f'include("{real_board_dir / "manifest.py"}")\n')
    return {"BOARD": board, "BOARD_DIR": str(override_dir)}


# The flags CMake really compiled `firmware` with. Reading them back, rather than reconstructing an
# include path by hand, is what makes the check below a statement about the real translation unit.
_FLAGS_MAKE_KEYS = ("C_DEFINES", "C_INCLUDES", "C_FLAGS")
_LWIP_PROBE_MARK = "LWIPPROBE"


def _eval_macro_expression(text: str) -> int:
    """Evaluates a preprocessed integer constant expression (e.g. `(8 * (800))`) with no eval() -
    lwIP options are arithmetic over literals, and anything else must fail loudly, not guess."""

    def walk(node: ast.AST) -> int:
        if isinstance(node, ast.Expression):
            return walk(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, int) and not isinstance(node.value, bool):
            return node.value
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            return +walk(node.operand) if isinstance(node.op, ast.UAdd) else -walk(node.operand)
        if isinstance(node, ast.BinOp):
            left, right = walk(node.left), walk(node.right)
            if isinstance(node.op, ast.Add):
                return left + right
            if isinstance(node.op, ast.Sub):
                return left - right
            if isinstance(node.op, ast.Mult):
                return left * right
            if isinstance(node.op, ast.FloorDiv):
                return left // right
            if isinstance(node.op, ast.LShift):
                return left << right
            if isinstance(node.op, ast.RShift):
                return left >> right
        raise OverrideError(f"lwip_connection_counts: cannot evaluate preprocessed option value {text!r} - it is not an integer constant expression")

    try:
        return walk(ast.parse(text.replace("/", "//"), mode="eval"))
    except SyntaxError as exc:
        raise OverrideError(f"lwip_connection_counts: cannot parse preprocessed option value {text!r}") from exc


def read_lwip_macros_from_build(build_dir: Path, macros: dict[str, int], compiler: str = "arm-none-eabi-gcc") -> dict[str, int]:
    """Preprocesses lwIP's own opt.h with the exact flags CMake compiled the firmware with, and
    returns each option's resolved value. Proves the override landed instead of assuming the
    generated header was found - the check Part B.14.2's trap A exists for."""
    flags_make = build_dir / "CMakeFiles" / "firmware.dir" / "flags.make"
    if not flags_make.is_file():
        raise OverrideError(f"lwip_connection_counts: no compile flags at {flags_make} - the firmware build did not get as far as configuring, so nothing can be verified.")
    text = flags_make.read_text()
    args: list[str] = []
    for key in _FLAGS_MAKE_KEYS:
        match = re.search(rf"^{key} = (.*)$", text, re.MULTILINE)
        if match is None:
            raise OverrideError(f"lwip_connection_counts: {flags_make} has no {key} line - CMake's generated layout has changed. {_LWIP_REVERIFY}")
        args.extend(shlex.split(match.group(1)))
    # The option name goes inside a string literal: bare, the preprocessor expands it too and
    # the line comes back as `LWIPPROBE (16) = (16)`, with the option's identity gone.
    probe_body = '#include "lwip/opt.h"\n' + "".join(f'{_LWIP_PROBE_MARK} "{name}" = {name}\n' for name in macros)
    with tempfile.TemporaryDirectory() as tmp:
        probe = Path(tmp) / "lwip_option_probe.c"
        probe.write_text(probe_body)
        # -E only: this never links or runs anything, it just asks the preprocessor what the real
        # build's own macros resolved to. -P drops the line markers that would confuse the scan.
        result = subprocess.run([compiler, "-E", "-P", *args, str(probe)], capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise OverrideError(f"lwip_connection_counts: preprocessing lwIP's options with the real build flags failed:\n{result.stderr.strip()[:2000]}")
    found: dict[str, int] = {}
    for line in result.stdout.splitlines():
        stripped = line.strip()
        if stripped.startswith(_LWIP_PROBE_MARK):
            name, _, value = stripped[len(_LWIP_PROBE_MARK):].partition("=")
            found[name.strip().strip('"')] = _eval_macro_expression(value.strip())
    return found


def verify_lwip_macros_in_build(build_dir: Path, macros: dict[str, int], compiler: str = "arm-none-eabi-gcc") -> dict[str, int]:
    """read_lwip_macros_from_build() plus the assertion. Raises OverrideError naming every option
    whose resolved value differs from what was asked for."""
    found = read_lwip_macros_from_build(build_dir, macros, compiler)
    wrong = {name: (want, found.get(name)) for name, want in macros.items() if found.get(name) != want}
    if wrong:
        detail = ", ".join(f"{name}: asked {want}, built {got}" for name, (want, got) in sorted(wrong.items()))
        raise OverrideError(
            f"lwip_connection_counts: the generated lwipopts.h did not reach the firmware's own "
            f"translation unit - {detail}. The build is NOT configured as asked. {_LWIP_REVERIFY}",
        )
    return found
