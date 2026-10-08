"""Canonical, zero-touch overrides for MicroPython's own build: every one generates files and flags
entirely OUTSIDE the fetched checkout, and verifies a known anchor in the pinned source first so a
restructuring release fails loudly. Rationale and version-bump checklist: SPECIFICATION.md B.14."""

import ast
import re
import shlex
import shutil
import struct
import subprocess
import tempfile
from pathlib import Path


class OverrideError(RuntimeError):
    # A pinned MicroPython source no longer matches what an override expects, so the override was
    # NOT applied. Re-verify against the new source and update the override's anchor/generated
    # content (SPECIFICATION.md Part B.14) - never silence this by removing the check.
    pass


def _read_anchor_source(path: Path, override_name: str) -> str:
    if not path.exists():
        raise OverrideError(
            f"{override_name}: expected source file not found at {path} - MicroPython's own file "
            "layout has changed. Re-verify this override against the current pinned source and "
            "update it (SPECIFICATION.md Part B.14) before retrying.",
        )
    return path.read_text()


# What a generated make, CMake, C or manifest line cannot carry unquoted: whitespace and these.
_UNEMBEDDABLE_CHARS = "\"'\\$#;:"


def _embeddable(path: Path, what: str) -> Path:
    # paths are resolved, and refused when a generated file cannot carry them
    path = path.resolve()
    for char in str(path):
        if char.isspace() or char in _UNEMBEDDABLE_CHARS:
            raise OverrideError(f"{what}: the path {path} contains {char!r}, which the generated make/CMake/C/manifest text cannot carry - use a --toolchain-dir (or $PICO_TOOLCHAIN_DIR) without whitespace, quotes, backslashes, '$', '#', ';' or ':'")
    return path


def _fresh_dir(path: Path) -> Path:
    # An override's directory, emptied first: a file an older generator wrote would otherwise still be
    # compiled (a variant's *.c) or found first on an include path, after a re-run over a dirty toolchain.
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)
    return path


def _count_once(text: str, anchor: str, where: Path, name: str, tail: str) -> int:
    # The anchor's one position in text; absent or repeated is an OverrideError naming both.
    count = text.count(anchor)
    if count != 1:
        state = "not found" if count == 0 else f"found {count} times, not once"
        raise OverrideError(f"{name}: expected {anchor!r} {state} in {where} - {tail}")
    return text.index(anchor)


def _require_in_order(micropython_dir: Path, name: str, relative: str, anchors: tuple[str, ...], tail: str) -> None:
    # Each anchor present in micropython_dir/relative, each after the one before it.
    path = micropython_dir / relative
    text = _read_anchor_source(path, name)
    position = 0
    for anchor in anchors:
        found = text.find(anchor, position)
        if found < 0:
            state = "is no longer after the anchor before it" if anchor in text else "is gone"
            raise OverrideError(f"{name}: expected {anchor!r} in {path} {state} - {tail}")
        position = found + len(anchor)


# A GCC >= 14 -Warray-bounds false positive in mbedtls_xor() (SPECIFICATION.md B.7.1), suppressed in
# ctr_drbg.c alone by both generated build files, since every build fails on any warning.
_MBEDTLS_ARRAY_BOUNDS_REASON = (
    "mbedtls_xor() in ctr_drbg.c trips GCC >= 14's -Warray-bounds; not yet re-checked on a GCC >= 14 host with the "
    "pin's mbedtls 3.6.6; scoped to ctr_drbg.c; goes when a GCC >= 14 build of both targets is clean without it, "
    "checked at every ref move (agent, 2026-10-08)"
)
_UNIX_MBEDTLS_ARRAY_BOUNDS = f"# {_MBEDTLS_ARRAY_BOUNDS_REASON}\n$(BUILD)/lib/mbedtls/library/ctr_drbg.o: CFLAGS += -Wno-array-bounds\n"
_RP2_MBEDTLS_ARRAY_BOUNDS = f'# {_MBEDTLS_ARRAY_BOUNDS_REASON}\nset_source_files_properties("${{MICROPY_DIR}}/lib/mbedtls/library/ctr_drbg.c" PROPERTIES COMPILE_OPTIONS "-Wno-array-bounds")\n'


# ---------------------------------------------------------------------------------------------
# unix_kbd_intr: force the Unix port's "standard" variant to use MicroPython's own SAFE, deferred
# SIGINT-delivery path instead of its default immediate one. Full account: SPECIFICATION.md Part
# B.14.1.
# ---------------------------------------------------------------------------------------------

UNIX_KBD_INTR_DIR_NAME = "unix_kbd_intr_variant"
# Proves the generated header was REACHED by a build's own translation unit, as the lwIP one does.
UNIX_KBD_INTR_SENTINEL = "MICROPY_SENSORS_KBD_INTR_OVERRIDE_APPLIED"

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
            "SPECIFICATION.md Part B.14.1. Do NOT remove this check and build unpatched: an "
            "interrupt mid critical section can corrupt VM state (reproduced as a garbled, "
            "impossible traceback - SPECIFICATION.md B.14.1).",
        )
    return common_header


def _unix_kbd_intr_header(real_variant_dir: Path) -> str:
    # The generated mpconfigvariant.h text: the real one first, then the safe SIGINT path and the
    # sentinel the post-build readback looks for. The host lwIP build starts from the same text.
    return (
        f'#include "{real_variant_dir / "mpconfigvariant.h"}"\n'
        "// SPECIFICATION.md Part B.14.1: force MicroPython's own safe,\n"
        "// deferred SIGINT-delivery path - see toolchain/micropython_overrides.py.\n"
        "#undef MICROPY_ASYNC_KBD_INTR\n"
        "#define MICROPY_ASYNC_KBD_INTR (0)\n"
        f"#define {UNIX_KBD_INTR_SENTINEL} 1\n"
    )


def apply_unix_kbd_intr_override(micropython_dir: Path, overrides_dir: Path) -> dict[str, str]:
    # Points the Unix standard variant's VARIANT_DIR at an external directory that #includes the
    # real variant files and forces MICROPY_ASYNC_KBD_INTR to 0; paths are resolved and refused
    # when unembeddable. Returns build_unix_port()'s extra `make` variables; see Part B.14.1.
    micropython_dir = _embeddable(micropython_dir, "unix_kbd_intr")
    overrides_dir = _embeddable(overrides_dir, "unix_kbd_intr")
    verify_unix_kbd_intr_anchor(micropython_dir)
    real_variant_dir = micropython_dir / "ports" / "unix" / "variants" / "standard"
    override_dir = _fresh_dir(overrides_dir / UNIX_KBD_INTR_DIR_NAME)
    (override_dir / "mpconfigvariant.h").write_text(_unix_kbd_intr_header(real_variant_dir))
    # mpconfigvariant.mk/manifest.py both relay to the real files rather than copying their
    # content, so neither can silently drift out of sync with a future pinned-version change -
    # `include()` is the freeze-manifest DSL's own primitive for exactly this (tools/manifestfile.py).
    (override_dir / "mpconfigvariant.mk").write_text(  # GNU make's include takes no quotes; _embeddable() guards it
        f'include {real_variant_dir / "mpconfigvariant.mk"}\n{_UNIX_MBEDTLS_ARRAY_BOUNDS}',
    )
    real_manifest = real_variant_dir / "manifest.py"
    if real_manifest.exists():
        (override_dir / "manifest.py").write_text(f"include({str(real_manifest)!r})\n")
    return {"VARIANT": "standard", "VARIANT_DIR": str(override_dir)}


# ---------------------------------------------------------------------------------------------
# lwip_connection_counts: raise the rp2 firmware's simultaneous-TCP-connection ceiling and the
# buffering behind it. Full account, and why every macro goes through one generated header rather
# than a mix of -D and shim: SPECIFICATION.md Part B.14.2.
# ---------------------------------------------------------------------------------------------

LWIP_OVERRIDE_BOARD_DIR_NAME = "lwip_connection_counts_board"
LWIP_OVERRIDE_INCLUDE_DIR_NAME = "lwipopts_override"
# Proves the generated header was REACHED, not merely written - see apply_...() below.
LWIP_OVERRIDE_SENTINEL = "MICROPY_SENSORS_LWIP_OVERRIDE_APPLIED"

# Split by how the PINNED source defines each macro, because that is what decides whether a plain
# -D could ever be trusted for it - guarded ones would take a -D, predefined ones silently would
# not (a later plain #define beats an earlier -D, B.14.1). Both go through the generated header.
LWIP_MACROS_GUARDED_IN_OPT_H = ("MEMP_NUM_TCP_PCB", "MEMP_NUM_TCP_PCB_LISTEN", "MEMP_NUM_PBUF", "PBUF_POOL_SIZE")
LWIP_MACROS_PREDEFINED_BY_MICROPYTHON = ("MEMP_NUM_UDP_PCB", "LWIP_STATS", "MEM_SIZE", "TCP_MSS", "TCP_WND", "TCP_SND_BUF", "MEMP_NUM_TCP_SEG")
LWIP_SETTABLE_MACROS = LWIP_MACROS_GUARDED_IN_OPT_H + LWIP_MACROS_PREDEFINED_BY_MICROPYTHON

# The MEM_SIZE group is ONE atomic `#ifndef MEM_SIZE` block upstream, so a -D of any of it would drop
# TCP_MSS to lwIP's 536; the generated header (#include first, then #undef) cannot. Every macro is
# still required, so the build is fully pinned and reviewable, and a regression to -D stays safe.
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
    # Checks every pinned-source fact this override depends on: lwIP's own `#if !defined` guards,
    # MicroPython's atomic MEM_SIZE block and its plain #defines, the rp2 CMake include order, and
    # the board directory's own shape. Raises OverrideError naming the drift; see Part B.14.2.
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


# lwIP's options are NOT independent: lib/lwip/src/core/init.c turns each relationship below into a
# compile-time #error, and opt.h DERIVES four more values from the ones set here. Mirrored here to
# fail before the build, naming the relationship, rather than in a wall of preprocessor output.

# 2,000 B = MicroPython's own MEM_SIZE 8000 (lwipopts_common.h) over the refactor's earlier
# max_connections 4 (agent, 2026-09-22). A relationship, not a tuning target: raising the ceiling
# may not shrink a connection's share of the arena every outbound byte is copied into.
# @tunable lwip.mem_size_per_connection_floor = 2000
MEM_SIZE_BYTES_PER_CONNECTION_FLOOR = 2000
# PCBs past the ceiling: a closed connection's FIN_WAIT pcb outlives its slot (tcp_alloc() never
# reclaims one at equal priority; modlwip aborts it after 10 s), as do arrivals not yet accepted or
# refused. The pattern every limit ever measured on silicon ran at (Part H.7).
# @tunable lwip.spare_tcp_pcbs = 3
SPARE_TCP_PCBS = 3
# PBUF_LINK_HLEN 14 + PBUF_IP_HLEN 40 + PBUF_TRANSPORT_HLEN 20 + PBUF_LINK_ENCAPSULATION_HLEN 0.
# IP_HLEN is 40, not 20: pbuf.h picks it on LWIP_IPV6, which ports/rp2/lwip_inc/lwipopts.h enables.
_PBUF_PROTOCOL_HEADER_BYTES = 74
_MEM_ALIGNMENT = 4  # extmod/lwip-include/lwipopts_common.h
_U16_MAX = 0xFFFF


def derive_lwip_dependents(macros: dict[str, int]) -> dict[str, int]:
    # The four values lwIP's own opt.h computes from the ones this override sets, by the same
    # formulas (TCP_SND_QUEUELEN / TCP_SNDLOWAT / TCP_SNDQUEUELOWAT / PBUF_POOL_BUFSIZE). They are
    # what most of init.c's sanity checks are really about, and none of them is settable here.
    mss, snd_buf = macros["TCP_MSS"], macros["TCP_SND_BUF"]
    snd_queuelen = (4 * snd_buf + (mss - 1)) // mss
    return {
        "TCP_SND_QUEUELEN": snd_queuelen,
        "TCP_SNDLOWAT": min(max(snd_buf // 2, 2 * mss + 1), snd_buf - 1),
        "TCP_SNDQUEUELOWAT": max(snd_queuelen // 2, 5),
        # LWIP_MEM_ALIGN_SIZE at MEM_ALIGNMENT 4 (lwipopts_common.h) over TCP_MSS plus the headers.
        "PBUF_POOL_BUFSIZE": ((mss + _PBUF_PROTOCOL_HEADER_BYTES) + 3) & ~3,
    }


def check_lwip_ensemble(macros: dict[str, int], max_connections: int | None = None) -> list[str]:
    # Every init.c relationship over the options set or derived here, plus the three it does NOT
    # check: it sizes the shared pools for ONE connection, while this firmware admits max_connections.
    # Returns the violated relationships; empty means the set is coherent.
    d = derive_lwip_dependents(macros)
    mss, snd_buf, wnd = macros["TCP_MSS"], macros["TCP_SND_BUF"], macros["TCP_WND"]
    seg, pool, pool_buf = macros["MEMP_NUM_TCP_SEG"], macros["PBUF_POOL_SIZE"], d["PBUF_POOL_BUFSIZE"]
    queuelen = d["TCP_SND_QUEUELEN"]
    problems: list[str] = []
    # --- lwIP's own, from lib/lwip/src/core/init.c. The port leaves MEMP_MEM_MALLOC, LWIP_WND_SCALE
    # and LWIP_DISABLE_*_SANITY_CHECKS at 0 and LWIP_TCP/LWIP_UDP at 1, so every one is live. ---
    if macros["MEMP_NUM_UDP_PCB"] <= 0:
        problems.append(f"MEMP_NUM_UDP_PCB ({macros['MEMP_NUM_UDP_PCB']}) <= 0 - lwIP requires at least one UDP pcb with LWIP_UDP enabled")
    if macros["MEMP_NUM_TCP_PCB"] <= 0:
        problems.append(f"MEMP_NUM_TCP_PCB ({macros['MEMP_NUM_TCP_PCB']}) <= 0 - lwIP requires at least one TCP pcb with LWIP_TCP enabled")
    if wnd > _U16_MAX:
        problems.append(f"TCP_WND ({wnd}) > 0xFFFF - it must fit in a u16_t without LWIP_WND_SCALE, which this port does not enable")
    if queuelen > _U16_MAX:
        problems.append(f"TCP_SND_QUEUELEN ({queuelen}, derived from TCP_SND_BUF/TCP_MSS) > 0xFFFF - it must fit in a u16_t")
    if queuelen < 2:  # noqa: PLR2004 - init.c's own literal
        problems.append(f"TCP_SND_QUEUELEN ({queuelen}, derived from TCP_SND_BUF/TCP_MSS) < 2 - lwIP needs at least 2 for no-copy writes")
    if pool_buf <= _MEM_ALIGNMENT:
        problems.append(f"PBUF_POOL_BUFSIZE ({pool_buf}) <= MEM_ALIGNMENT ({_MEM_ALIGNMENT})")
    if seg < queuelen:
        problems.append(f"MEMP_NUM_TCP_SEG ({seg}) < TCP_SND_QUEUELEN ({queuelen}, derived from TCP_SND_BUF/TCP_MSS)")
    if snd_buf < 2 * mss:
        problems.append(f"TCP_SND_BUF ({snd_buf}) < 2 * TCP_MSS ({2 * mss})")
    if queuelen < 2 * (snd_buf // mss):
        problems.append(f"TCP_SND_QUEUELEN ({queuelen}) < 2 * (TCP_SND_BUF / TCP_MSS) ({2 * (snd_buf // mss)})")
    if d["TCP_SNDLOWAT"] >= snd_buf:
        problems.append(f"TCP_SNDLOWAT ({d['TCP_SNDLOWAT']}) >= TCP_SND_BUF ({snd_buf})")
    if mss >= (16 * 1024) - 1:
        problems.append(f"TCP_MSS ({mss}) >= 16383, which underflows lwIP's own TCP_SNDLOWAT calculation")
    if d["TCP_SNDLOWAT"] >= _U16_MAX - 4 * mss:
        problems.append(f"TCP_SNDLOWAT ({d['TCP_SNDLOWAT']}, derived from TCP_SND_BUF/TCP_MSS) >= 0xFFFF - 4 * TCP_MSS ({_U16_MAX - 4 * mss}) - it must stay 4 * TCP_MSS below u16_t overflow")
    if d["TCP_SNDQUEUELOWAT"] >= queuelen:
        problems.append(f"TCP_SNDQUEUELOWAT ({d['TCP_SNDQUEUELOWAT']}) >= TCP_SND_QUEUELEN ({queuelen})")
    if pool and pool_buf <= _PBUF_PROTOCOL_HEADER_BYTES:
        problems.append(f"PBUF_POOL_BUFSIZE ({pool_buf}) leaves no room past the {_PBUF_PROTOCOL_HEADER_BYTES}-byte protocol headers")
    if pool and wnd > pool * (pool_buf - _PBUF_PROTOCOL_HEADER_BYTES):
        problems.append(f"TCP_WND ({wnd}) > PBUF_POOL_SIZE * (PBUF_POOL_BUFSIZE - headers) ({pool * (pool_buf - _PBUF_PROTOCOL_HEADER_BYTES)})")
    if wnd < mss:
        problems.append(f"TCP_WND ({wnd}) < TCP_MSS ({mss})")
    if max_connections is None:
        return problems
    if max_connections < 1:  # every share below divides by it, and admitting nothing serves nothing
        problems.append(f"max_connections ({max_connections}) < 1 - the per-connection relationships are undefined for a ceiling admitting no connection")
        return problems
    return problems + _per_connection_problems(macros, max_connections)


def _per_connection_problems(macros: dict[str, int], max_connections: int) -> list[str]:
    # The three relationships lwIP does not check, because it sizes for one connection and we admit N.
    mss, snd_buf, seg = macros["TCP_MSS"], macros["TCP_SND_BUF"], macros["MEMP_NUM_TCP_SEG"]
    problems: list[str] = []
    want_pcb = max_connections + SPARE_TCP_PCBS
    if macros["MEMP_NUM_TCP_PCB"] < want_pcb:
        problems.append(f"MEMP_NUM_TCP_PCB ({macros['MEMP_NUM_TCP_PCB']}) < max_connections + {SPARE_TCP_PCBS} ({want_pcb}) - connections still closing and the one queued over-ceiling arrival hold PCBs from the same pool")
    # Segments are a GLOBAL pool while TCP_SND_QUEUELEN is PER connection, so one connection can
    # drain the pool. Every admitted connection gets a full window of full-MSS segments; short writes and
    # closing pcbs can still drain it (SPECIFICATION.md Part B.14.2.1).
    want_seg = max_connections * (snd_buf // mss)
    if seg < want_seg:
        problems.append(f"MEMP_NUM_TCP_SEG ({seg}) < max_connections * (TCP_SND_BUF / TCP_MSS) ({want_seg}) - {max_connections} connections cannot each hold a full send window")
    # MEM_SIZE is the arena every outbound byte passes through: modlwip.c's tcp_write() always sets
    # TCP_WRITE_FLAG_COPY, so the payload is copied into a PBUF_RAM pbuf, which is mem_malloc()'d
    # from it. Its per-connection share may not fall below the floor above.
    per_connection = macros["MEM_SIZE"] // max_connections
    if per_connection < MEM_SIZE_BYTES_PER_CONNECTION_FLOOR:
        problems.append(f"MEM_SIZE ({macros['MEM_SIZE']}) leaves {per_connection} B per admitted connection, below the {MEM_SIZE_BYTES_PER_CONNECTION_FLOOR} B floor - every outbound byte is copied into this arena (modlwip.c's tcp_write TCP_WRITE_FLAG_COPY)")
    return problems


def validate_lwip_macros(macros: dict[str, int]) -> None:
    missing = [name for name in LWIP_SETTABLE_MACROS if name not in macros]
    unknown = sorted(set(macros) - set(LWIP_SETTABLE_MACROS))
    if missing or unknown:
        raise OverrideError(
            f"lwip_connection_counts: [lwip] in toolchain/versions.toml must set exactly "
            f"{list(LWIP_SETTABLE_MACROS)} - missing {missing}, unrecognized {unknown}. Every macro is "
            "required even when unchanged, so the firmware's lwIP options are fully pinned and "
            "reviewable in that one table (SPECIFICATION.md Part B.14.2).",
        )
    for name, value in macros.items():
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise OverrideError(f"lwip_connection_counts: [lwip].{name} must be a non-negative int, got {value!r}")
    if macros["TCP_MSS"] < 1:  # every segment and window derivation divides by it
        raise OverrideError(f"lwip_connection_counts: [lwip].TCP_MSS must be at least 1, got {macros['TCP_MSS']}")
    # lwIP's own relationships, always - an incoherent set is a compile-time #error deep inside
    # lib/lwip/src/core/init.c, and this says the same thing before the build with the relationship
    # named. The N-connection ones are checked per device by buildgen, which knows N.
    problems = check_lwip_ensemble(macros)
    if problems:
        raise OverrideError(
            "lwip_connection_counts: [lwip] in toolchain/versions.toml is not a coherent set - lwIP's "
            "options are NOT independent (lib/lwip/src/core/init.c turns each of these into a "
            "compile-time #error, and opt.h derives TCP_SND_QUEUELEN/TCP_SNDLOWAT/TCP_SNDQUEUELOWAT/"
            "PBUF_POOL_BUFSIZE from them):\n  - " + "\n  - ".join(problems),
        )


def _lwip_redefines(macros: dict[str, int]) -> str:
    # The sentinel closes the one hole a value comparison cannot: if this header is never found,
    # every option resolves to MicroPython's own default, and a run that happens to ASK for the
    # defaults would verify clean against a build the override never touched.
    return f"#define {LWIP_OVERRIDE_SENTINEL} 1\n" + "".join(f"#undef {name}\n#define {name} ({macros[name]})\n" for name in LWIP_SETTABLE_MACROS)


def apply_lwip_connection_counts_override(micropython_dir: Path, overrides_dir: Path, board: str, macros: dict[str, int], *, extra_include_dirs: tuple[Path, ...] = ()) -> dict[str, str]:
    # Generates an out-of-tree board directory whose own lwipopts.h #includes the real one and then
    # redefines every lwIP option, reached through MicroPython's documented BOARD_DIR redirect; paths
    # are resolved and refused when unembeddable. Returns build_firmware()'s `make` variables; Part B.14.2.
    micropython_dir = _embeddable(micropython_dir, "lwip_connection_counts")
    overrides_dir = _embeddable(overrides_dir, "lwip_connection_counts")
    extra_include_dirs = tuple(_embeddable(path, "lwip_connection_counts") for path in extra_include_dirs)
    verify_lwip_connection_counts_anchor(micropython_dir, board)
    validate_lwip_macros(macros)
    rp2_dir = micropython_dir / "ports" / "rp2"
    real_board_dir = rp2_dir / "boards" / board
    override_dir = _fresh_dir(overrides_dir / LWIP_OVERRIDE_BOARD_DIR_NAME)
    include_dir = override_dir / LWIP_OVERRIDE_INCLUDE_DIR_NAME
    include_dir.mkdir()
    (include_dir / "lwipopts.h").write_text(
        "// Generated by toolchain/micropython_overrides.py - SPECIFICATION.md Part B.14.2.\n"
        "// Found ahead of ports/rp2/lwip_inc/lwipopts.h, so these win over both MicroPython's own\n"
        "// plain #defines and lwIP's opt.h defaults; every option is set, never a subset.\n"
        f'#include "{rp2_dir / "lwip_inc" / "lwipopts.h"}"\n'
        f"{_lwip_redefines(macros)}",
    )
    # include_directories(BEFORE) at the port's own directory scope, which every target there
    # inherits ahead of its own target-level dirs - the only ordering that beats `lwip_inc`.
    # MICROPY_BOARD_PINS is set rather than the csv copied, so pins can never drift from the pin.
    extra_lines = "".join(f'include_directories(BEFORE "{path}")\n' for path in extra_include_dirs)
    (override_dir / "mpconfigboard.cmake").write_text(
        "# Generated by toolchain/micropython_overrides.py - SPECIFICATION.md Part B.14.2.\n"
        f'set(MICROPY_BOARD_PINS "{real_board_dir / "pins.csv"}")\n'
        f'include("{real_board_dir / "mpconfigboard.cmake"}")\n'
        f'include_directories(BEFORE "{include_dir}")\n'
        f"{extra_lines}{_RP2_MBEDTLS_ARRAY_BOUNDS}",
    )
    # Relays, never copies, for the same reason B.14.1's manifest is an include(): neither can
    # drift from a future pinned-version change. The real board cmake points the frozen manifest at
    # ${MICROPY_BOARD_DIR}, which is now this directory, so manifest.py has to be relayed too.
    (override_dir / "mpconfigboard.h").write_text(f'#include "{real_board_dir / "mpconfigboard.h"}"\n')
    (override_dir / "manifest.py").write_text(f"include({str(real_board_dir / 'manifest.py')!r})\n")
    return {"BOARD": board, "BOARD_DIR": str(override_dir)}


# ---------------------------------------------------------------------------------------------
# modlwip_eagain: a non-blocking modlwip send returns EAGAIN on ERR_MEM instead of retrying for up to
# 10 s inside one call (micropython issue 19704). Removed, not re-anchored, once the pin carries a
# real fix (owner, 2026-09-30). Full account: SPECIFICATION.md B.14.
# ---------------------------------------------------------------------------------------------

MODLWIP_OVERRIDE_DIR_NAME = "modlwip_eagain"
MODLWIP_COPY_NAME = "modlwip.c"
# lwip_tcp_send()'s ERR_MEM retry loop, verbatim as pinned in extmod/modlwip.c: 200 rounds of
# mp_hal_delay_ms(50), even for a non-blocking socket.
_MODLWIP_ERR_MEM_LOOP = (
    "    for (int i = 0; i < 200; ++i) {\n"
    "        err = tcp_write(socket->pcb.tcp, buf, write_len, TCP_WRITE_FLAG_COPY);\n"
    "        if (err != ERR_MEM) {\n"
    "            break;\n"
    "        }\n"
    "        err = tcp_output(socket->pcb.tcp);\n"
    "        if (err != ERR_OK) {\n"
    "            break;\n"
    "        }\n"
    "        MICROPY_PY_LWIP_EXIT\n"
    "        mp_hal_delay_ms(50);\n"
    "        MICROPY_PY_LWIP_REENTER\n"
    "    }\n"
)
_MODLWIP_INSERT_AFTER = "        err = tcp_output(socket->pcb.tcp);\n        if (err != ERR_OK) {\n            break;\n        }\n"
# Upstream PR 19708's change: hand the wait back to the caller instead of sleeping in the loop.
_MODLWIP_EAGAIN_BLOCK = (
    "        if (socket->timeout == 0) {\n"
    "            // Non-blocking: hand the wait back to the caller rather than sleeping inside this call.\n"
    "            MICROPY_PY_LWIP_EXIT\n"
    "            *_errno = MP_EAGAIN;\n"
    "            return MP_STREAM_ERROR;\n"
    "        }\n"
)
# The copy no longer sits beside modnetwork.h; ${MICROPY_DIR} is on every include path (py/py.cmake).
_MODLWIP_LOCAL_INCLUDE = '#include "modnetwork.h"'
_MODLWIP_COPY_INCLUDE = '#include "extmod/modnetwork.h"'
_MODLWIP_SOURCE_ANCHORS = (_MODLWIP_ERR_MEM_LOOP, _MODLWIP_INSERT_AFTER, _MODLWIP_LOCAL_INCLUDE)
# How the rp2 build reaches the copy: extmod.cmake lists modlwip.c, usermod.cmake includes the
# generated micropython.cmake after it and before the sources and the QSTR list are read.
_EXTMOD_SOURCE_SET = "set(MICROPY_SOURCE_EXTMOD\n"
_EXTMOD_MODLWIP_LINE = "    ${MICROPY_EXTMOD_DIR}/modlwip.c\n"
_MODLWIP_RP2_WIRING = (
    ("extmod/extmod.cmake", (_EXTMOD_SOURCE_SET, _EXTMOD_MODLWIP_LINE)),
    ("ports/rp2/CMakeLists.txt", (
        "include(${MICROPY_DIR}/extmod/extmod.cmake)",
        "include(${MICROPY_DIR}/py/usermod.cmake)",
        "list(APPEND MICROPY_SOURCE_QSTR\n    ${MICROPY_SOURCE_EXTMOD}\n",
        "target_sources(${MICROPY_TARGET} PRIVATE\n    ${MICROPY_SOURCE_PY}\n    ${MICROPY_SOURCE_EXTMOD}\n",
    )),
    ("ports/rp2/Makefile", ("CMAKE_ARGS += -DUSER_C_MODULES=${USER_C_MODULES}",)),
    ("py/usermod.cmake", ('set(USER_C_MODULE_PATH "${USER_C_MODULE_PATH}/micropython.cmake")', "include(${USER_C_MODULE_PATH})")),
)
_MODLWIP_VERSION_DEFINES = ("MICROPY_VERSION_MAJOR", "MICROPY_VERSION_MINOR", "MICROPY_VERSION_MICRO")
_MODLWIP_REVERIFY = (
    "the ERR_MEM retry loop or its wiring changed upstream - check whether the pin now carries a real "
    "fix for micropython issue 19704 (then retire this override) or re-derive the patch (SPECIFICATION.md B.14)"
)


def _micropython_version(micropython_dir: Path, name: str) -> str:
    # X.Y.Z from the checkout's own py/mpconfig.h, so a generated file names the source it came from.
    mpconfig = micropython_dir / "py" / "mpconfig.h"
    text = _read_anchor_source(mpconfig, name)
    parts = []
    for define in _MODLWIP_VERSION_DEFINES:
        match = re.search(rf"^#define {define} (\d+)$", text, re.MULTILINE)
        if match is None:
            raise OverrideError(f"{name}: {mpconfig} has no `#define {define} <n>` line - {_MODLWIP_REVERIFY}")
        parts.append(match.group(1))
    return ".".join(parts)


def _verify_modlwip_source(micropython_dir: Path, name: str) -> str:
    # The pinned extmod/modlwip.c, once its loop, the insertion point and the local include each occur
    # exactly once - the loop's text holds the insertion point, so its one occurrence is inside the
    # loop. Shared by the rp2 build and the host lwIP build.
    source = micropython_dir / "extmod" / "modlwip.c"
    text = _read_anchor_source(source, name)
    for anchor in _MODLWIP_SOURCE_ANCHORS:
        _count_once(text, anchor, source, name, _MODLWIP_REVERIFY)
    return text


def _modlwip_eagain_source(micropython_dir: Path, name: str) -> str:
    # The patched copy's text: the pinned file with the EAGAIN block inserted and the include
    # rewritten, no #line, so a compiler diagnostic names the copy. Same bytes for every build.
    text = _verify_modlwip_source(micropython_dir, name)
    version = _micropython_version(micropython_dir, name)
    patched = text.replace(_MODLWIP_INSERT_AFTER, _MODLWIP_INSERT_AFTER + _MODLWIP_EAGAIN_BLOCK, 1).replace(_MODLWIP_LOCAL_INCLUDE, _MODLWIP_COPY_INCLUDE, 1)
    return (
        f"// Generated by toolchain/micropython_overrides.py from extmod/modlwip.c of MicroPython {version} -\n"
        "// SPECIFICATION.md B.14. Do not edit.\n"
        f"{patched}"
    )


def verify_modlwip_eagain_anchor(micropython_dir: Path) -> None:
    # Every pinned-source fact the override relies on: the loop and its insertion point, the local
    # include, and the CMake/Makefile wiring that swaps the copy in. Raises OverrideError naming it.
    _verify_modlwip_source(micropython_dir, MODLWIP_OVERRIDE_DIR_NAME)
    for relative, anchors in _MODLWIP_RP2_WIRING:
        _require_in_order(micropython_dir, MODLWIP_OVERRIDE_DIR_NAME, relative, anchors, _MODLWIP_REVERIFY)
    extmod_cmake = micropython_dir / "extmod" / "extmod.cmake"
    text = extmod_cmake.read_text()
    block_start = text.index(_EXTMOD_SOURCE_SET)
    block_end = text.find("\n)", block_start)
    if text.find(_EXTMOD_MODLWIP_LINE, block_start) > block_end >= 0:
        raise OverrideError(f"{MODLWIP_OVERRIDE_DIR_NAME}: extmod/modlwip.c is no longer inside set(MICROPY_SOURCE_EXTMOD ...) in {extmod_cmake} - {_MODLWIP_REVERIFY}")


def apply_modlwip_eagain_override(micropython_dir: Path, overrides_dir: Path) -> dict[str, str]:
    # Writes the patched copy and a micropython.cmake that swaps it for the original in
    # MICROPY_SOURCE_EXTMOD; paths are resolved and refused when unembeddable. Returns
    # build_firmware()'s USER_C_MODULES (a directory: usermod.cmake appends micropython.cmake).
    micropython_dir = _embeddable(micropython_dir, MODLWIP_OVERRIDE_DIR_NAME)
    overrides_dir = _embeddable(overrides_dir, MODLWIP_OVERRIDE_DIR_NAME)
    verify_modlwip_eagain_anchor(micropython_dir)
    copy_text = _modlwip_eagain_source(micropython_dir, MODLWIP_OVERRIDE_DIR_NAME)
    override_dir = _fresh_dir(overrides_dir / MODLWIP_OVERRIDE_DIR_NAME)
    copy_path = override_dir / MODLWIP_COPY_NAME
    copy_path.write_text(copy_text)
    (override_dir / "micropython.cmake").write_text(
        "# Generated by toolchain/micropython_overrides.py - SPECIFICATION.md B.14.\n"
        'list(FIND MICROPY_SOURCE_EXTMOD "${MICROPY_EXTMOD_DIR}/modlwip.c" _sensors_modlwip_index)\n'
        "if(_sensors_modlwip_index EQUAL -1)\n"
        '    message(FATAL_ERROR "modlwip_eagain: extmod/modlwip.c is not in MICROPY_SOURCE_EXTMOD - re-verify toolchain/micropython_overrides.py (SPECIFICATION.md B.14)")\n'
        "endif()\n"
        "list(REMOVE_AT MICROPY_SOURCE_EXTMOD ${_sensors_modlwip_index})\n"
        f'list(APPEND MICROPY_SOURCE_EXTMOD "{copy_path}")\n',
    )
    return {"USER_C_MODULES": str(override_dir)}


# ---------------------------------------------------------------------------------------------
# unix_lwip_host: a third Unix-port build flavour that compiles the patched modlwip.c above over
# lwIP on a loopback netif, so the send path runs on the host (owner, 2026-09-30). Full account:
# SPECIFICATION.md B.14.
# ---------------------------------------------------------------------------------------------

UNIX_LWIP_HOST_DIR_NAME = "unix_lwip_host_variant"
# setup_toolchain.py's UNIX_LWIP_BUILD_DIR; this module never imports the installer, a test pins both.
_UNIX_LWIP_BUILD = "build-lwip"
# The rp2 port's own lwIP settings, each line as pinned in ports/rp2/lwip_inc/lwipopts.h; its LWIP_RAND()
# and pico/rand.h are rp2-only, so the host header restates these rather than including that file.
_RP2_LWIP_HOST_SETTINGS = (
    "#define LWIP_NETIF_EXT_STATUS_CALLBACK  1",
    "#define LWIP_NETIF_STATUS_CALLBACK      1",
    "#define LWIP_IPV4                       1",
    "#define LWIP_IPV6                       1",
    "#define LWIP_ND6_NUM_DESTINATIONS       4",
    "#define LWIP_ND6_QUEUEING               0",
)
# What the host build relies on, file by file, each after the one before it: lwIP compiled in with
# the loopback netif, the variant makefile read before extmod.mk and before mkrules.mk's vpath, the
# variant's .c files compiled, the event hook MicroPython runs while it waits, and NO_SYS polling.
_LWIP_HOST_ANCHORS = (
    ("extmod/extmod.mk", ("\textmod/modlwip.c \\\n", "ifeq ($(MICROPY_PY_LWIP),1)\n", "ifeq ($(MICROPY_PY_LWIP_LOOPBACK),1)\nCFLAGS_EXTMOD += -DLWIP_NETIF_LOOPBACK=1\n")),
    ("ports/unix/Makefile", ("include $(VARIANT_DIR)/mpconfigvariant.mk\n", "include $(TOP)/extmod/extmod.mk\n", "ifeq ($(MICROPY_PY_SOCKET),1)\n", "\t$(wildcard $(VARIANT_DIR)/*.c)\n", "include $(TOP)/py/mkrules.mk\n")),
    ("py/mkrules.mk", ("vpath %.c . $(TOP)",)),
    ("py/mphal.h", ("#ifndef MICROPY_INTERNAL_EVENT_HOOK\n",)),
    ("py/scheduler.c", ("void mp_event_handle_nowait(void) {\n", "    MICROPY_INTERNAL_EVENT_HOOK;\n")),
    ("extmod/modlwip.c", ("static inline void poll_sockets(void) {\n    MICROPY_PY_LWIP_POLL_HOOK\n    mp_event_wait_ms(1);\n}\n",)),
    ("lib/lwip/src/include/lwip/opt.h", ("#define LWIP_HAVE_LOOPIF                (LWIP_NETIF_LOOPBACK && !LWIP_SINGLE_NETIF)\n", "#define LWIP_NETIF_LOOPBACK_MULTITHREADING    (!NO_SYS)\n")),
    ("ports/rp2/lwip_inc/lwipopts.h", _RP2_LWIP_HOST_SETTINGS),
)
_LWIP_HOST_TCP_OUT = "lib/lwip/src/core/tcp_out.c"
# The host build's own per-object flags, (object, flag, reason): the Unix port compiles with -Wextra
# (ports/unix/Makefile:55), rp2 does not. `private` keeps each off what that object's build triggers.
_LWIP_HOST_OBJECT_FLAGS = (
    ("extmod/modlwip.o", "-Wno-sign-compare", "modlwip.c compares its mp_uint_t timeout and send/recv results with -1; rp2 compiles it without -Wextra, so upstream never meets -Wsign-compare there"),
    ("extmod/modlwip.o", "-DSOMAXCONN=2", "ports/unix/mpconfigport.h:176 takes the default listen() backlog from <sys/socket.h>'s SOMAXCONN, which modlwip.c never includes; 2 is rp2's own default (py/mpconfig.h:2148)"),
)
_LWIP_HOST_REVERIFY = "the Unix port's lwIP wiring changed upstream - re-derive the host lwIP build (SPECIFICATION.md B.14)"


def _lwip_host_files(micropython_dir: Path, variant_dir: Path, lwip_macros: dict[str, int]) -> dict[str, str]:
    # Every generated file of the host build flavour, by path under its variant directory.
    real_variant_dir = micropython_dir / "ports" / "unix" / "variants" / "standard"
    alignment = struct.calcsize("P")  # the host's own pointer alignment, a literal lwIP may test in #if
    settings = "\n".join(_RP2_LWIP_HOST_SETTINGS)
    files = {
        "mpconfigvariant.h": _unix_kbd_intr_header(real_variant_dir) + "void mp_lwip_host_poll(void);\n#define MICROPY_INTERNAL_EVENT_HOOK mp_lwip_host_poll()\n",
        "mpconfigvariant.mk": (
            f"include {real_variant_dir / 'mpconfigvariant.mk'}\n"
            f"INC += -I{variant_dir / 'lwip_inc'}\n"
            f"vpath extmod/modlwip.c {variant_dir / 'src'}\n"
            f"{_UNIX_MBEDTLS_ARRAY_BOUNDS}"
            + "".join(f"# {reason}\n$(BUILD)/{obj}: private CFLAGS += {flag}\n" for obj, flag, reason in _LWIP_HOST_OBJECT_FLAGS)
        ),
        "src/extmod/modlwip.c": _modlwip_eagain_source(micropython_dir, "unix_lwip_host"),
        "lwip_inc/lwipopts.h": (
            "// Generated by toolchain/micropython_overrides.py - SPECIFICATION.md B.14.\n"
            "// The host lwIP build's options: the rp2 port's own settings, MicroPython's common block, the\n"
            "// host's pointer alignment and versions.toml's [lwip] table, as in every rp2 image.\n"
            "#ifndef MICROPY_INCLUDED_SENSORS_LWIP_HOST_LWIPOPTS_H\n#define MICROPY_INCLUDED_SENSORS_LWIP_HOST_LWIPOPTS_H\n\n"
            f"#include <stdlib.h>\n\n{settings}\n\n#define LWIP_RAND() ((u32_t)rand())\n\n"
            '#include "extmod/lwip-include/lwipopts_common.h"\n\n'
            f"#undef MEM_ALIGNMENT\n#define MEM_ALIGNMENT {alignment}\n"
            "// Pointers wider than 4 bytes: struct ip6_reass_helper outgrows IP6_FRAG_HLEN, which ip6_reass_tmr() asserts each second (lib/lwip/src/core/ipv6/ip6_frag.c:117-120).\n"
            f"#define IPV6_FRAG_COPYHEADER 1\n{_lwip_redefines(lwip_macros)}\n#endif\n"
        ),
        "lwip_inc/arch/cc.h": (
            "// Generated by toolchain/micropython_overrides.py - SPECIFICATION.md B.14.\n"
            "// As ports/rp2/lwip_inc/arch/cc.h, except that a failed lwIP assertion stops the host build loudly.\n"
            "#ifndef MICROPY_INCLUDED_SENSORS_LWIP_HOST_ARCH_CC_H\n#define MICROPY_INCLUDED_SENSORS_LWIP_HOST_ARCH_CC_H\n\n"
            "#include <stdio.h>\n#include <stdlib.h>\n"
            "#define LWIP_PLATFORM_DIAG(x)\n"
            '#define LWIP_PLATFORM_ASSERT(x) do { fprintf(stderr, "lwIP assertion failed: %s (%s:%d)\\n", (x), __FILE__, __LINE__); abort(); } while (0)\n'
            "#define LWIP_NO_CTYPE_H 1\n\n#endif\n"
        ),
        "lwip_inc/arch/sys_arch.h": "// Generated by toolchain/micropython_overrides.py - SPECIFICATION.md B.14.\n// Empty, as ports/rp2/lwip_inc/arch/sys_arch.h: NO_SYS needs no OS layer.\n",
        "lwip_host_port.c": (
            "// Generated by toolchain/micropython_overrides.py - SPECIFICATION.md B.14.\n"
            "// The host lwIP build's port layer: lwIP's clock, modlwip's DNS preference, and the event hook\n"
            "// that runs lwIP wherever MicroPython waits, as PendSV does on rp2.\n"
            '#include "py/mphal.h"\n\n#if MICROPY_PY_LWIP\n\n'
            '#include "lwip/netif.h"\n#include "lwip/sys.h"\n#include "lwip/timeouts.h"\n\n'
            "u32_t sys_now(void) {\n    return (u32_t)mp_hal_ticks_ms();\n}\n\n"
            "int mp_mod_network_prefer_dns_use_ip_version = 4;\n\n"
            "void mp_lwip_host_poll(void) {\n    static int polling = 0;\n    if (polling) {\n        return;\n    }\n"
            "    polling = 1;\n    netif_poll_all();\n    sys_check_timeouts();\n    polling = 0;\n}\n\n#endif\n"
        ),
    }
    real_manifest = real_variant_dir / "manifest.py"
    if real_manifest.exists():
        files["manifest.py"] = f"include({str(real_manifest)!r})\n"
    return files


def _verify_unix_lwip_host_anchors(micropython_dir: Path) -> None:
    # The SIGINT override's anchor, modlwip's, and every fact the host build relies on (above).
    verify_unix_kbd_intr_anchor(micropython_dir)
    _verify_modlwip_source(micropython_dir, "unix_lwip_host")
    for relative, anchors in _LWIP_HOST_ANCHORS:
        _require_in_order(micropython_dir, "unix_lwip_host", relative, anchors, _LWIP_HOST_REVERIFY)
    if not (micropython_dir / _LWIP_HOST_TCP_OUT).is_file():
        raise OverrideError(f"unix_lwip_host: {micropython_dir / _LWIP_HOST_TCP_OUT} is missing - lib/lwip is not fetched for the Unix port (make submodules MICROPY_PY_LWIP=1), or {_LWIP_HOST_REVERIFY}")


def apply_unix_lwip_host_override(micropython_dir: Path, overrides_dir: Path, lwip_macros: dict[str, int]) -> dict[str, str]:
    # Generates the host build flavour's variant directory: the SIGINT header plus the lwIP event
    # hook, lwIP's options and port layer, and the patched modlwip.c found by vpath ahead of the
    # original; paths are resolved and refused when unembeddable. Returns its `make` variables.
    micropython_dir = _embeddable(micropython_dir, "unix_lwip_host")
    overrides_dir = _embeddable(overrides_dir, "unix_lwip_host")
    _verify_unix_lwip_host_anchors(micropython_dir)
    validate_lwip_macros(lwip_macros)
    variant_dir = overrides_dir / UNIX_LWIP_HOST_DIR_NAME
    files = _lwip_host_files(micropython_dir, variant_dir, lwip_macros)
    _fresh_dir(variant_dir)
    for relative, text in files.items():
        (variant_dir / relative).parent.mkdir(parents=True, exist_ok=True)
        (variant_dir / relative).write_text(text)
    return {
        "VARIANT": "standard",
        "VARIANT_DIR": str(variant_dir),
        "BUILD": _UNIX_LWIP_BUILD,
        "MICROPY_PY_LWIP": "1",
        "MICROPY_PY_LWIP_LOOPBACK": "1",
        "MICROPY_PY_SOCKET": "0",
    }


# ---------------------------------------------------------------------------------------------
# tick_offset_test: a TEST-ONLY build in which mp_hal_ticks_ms() returns the time since boot plus 2**32
# ms minus 15 minutes, so ticks_ms() and the 32-bit millisecond count wrap about 15 minutes after boot
# (owner, 2026-10-01). Never in a release image. Full account: SPECIFICATION.md B.14.
# ---------------------------------------------------------------------------------------------

TICK_OFFSET_DIR_NAME = "tick_offset_test"
TICK_OFFSET_SENTINEL = "MICROPY_SENSORS_TICK_OFFSET_TEST_APPLIED"
# The test image's own build directory per board, so a later release build never reuses its
# objects and two boards never share one CMake cache: build-<board>-tickoffset.
TICK_OFFSET_BUILD_SUFFIX = "-tickoffset"
# 15 minutes before the 32-bit wrap; 2**32 is also a multiple of ticks_ms()'s 2**30 period, so both wrap together
TICK_OFFSET_MS = 2**32 - 15 * 60 * 1000
# mp_hal_ticks_ms() as pinned in ports/rp2/mphalport.h; py/mphal.h reaches it as <mphalport.h>,
# which no rp2, extmod or shared file includes with quotes, so a copy found first replaces it.
_TICK_OFFSET_ANCHOR = "static inline mp_uint_t mp_hal_ticks_ms(void) {\n    return to_ms_since_boot(get_absolute_time());\n}\n"
_TICK_OFFSET_REPLACEMENT = "static inline mp_uint_t mp_hal_ticks_ms(void) {\n    return (mp_uint_t)(to_ms_since_boot(get_absolute_time()) + MICROPY_SENSORS_TICK_OFFSET_MS);\n}\n"
_TICK_OFFSET_REVERIFY = "re-derive this override's anchor and its replacement (SPECIFICATION.md B.14); do not build the test image unpatched"


def verify_tick_offset_anchor(micropython_dir: Path) -> Path:
    # The pinned mp_hal_ticks_ms() body, exactly once; returns the header that holds it.
    header = micropython_dir / "ports" / "rp2" / "mphalport.h"
    _count_once(_read_anchor_source(header, TICK_OFFSET_DIR_NAME), _TICK_OFFSET_ANCHOR, header, TICK_OFFSET_DIR_NAME, _TICK_OFFSET_REVERIFY)
    return header


def apply_tick_offset_override(micropython_dir: Path, overrides_dir: Path, *, board: str) -> dict[str, str]:
    # Writes a copy of the pinned mphalport.h whose mp_hal_ticks_ms() adds TICK_OFFSET_MS in 32-bit
    # unsigned arithmetic; the hardware timer is never written. build_firmware() puts the directory
    # ahead on the include path; returns the test image's own build directory as `make` variables.
    micropython_dir = _embeddable(micropython_dir, TICK_OFFSET_DIR_NAME)
    overrides_dir = _embeddable(overrides_dir, TICK_OFFSET_DIR_NAME)
    header = verify_tick_offset_anchor(micropython_dir)
    override_dir = _fresh_dir(overrides_dir / TICK_OFFSET_DIR_NAME)
    (override_dir / "mphalport.h").write_text(
        "// Generated by toolchain/micropython_overrides.py from ports/rp2/mphalport.h - SPECIFICATION.md B.14.\n"
        "// TEST-ONLY: ticks_ms() wraps about 15 minutes after boot. Never in a release image.\n"
        f"#define MICROPY_SENSORS_TICK_OFFSET_MS ({TICK_OFFSET_MS}u)\n"
        f"#define {TICK_OFFSET_SENTINEL} 1\n"
        + header.read_text().replace(_TICK_OFFSET_ANCHOR, _TICK_OFFSET_REPLACEMENT, 1),
    )
    return {"BUILD": f"build-{board}{TICK_OFFSET_BUILD_SUFFIX}"}


# The flags CMake really compiled `firmware` with. Reading them back, rather than reconstructing an
# include path by hand, is what makes the check below a statement about the real translation unit.
_FLAGS_MAKE_KEYS = ("C_DEFINES", "C_INCLUDES", "C_FLAGS")
# The probe puts each option name inside a string literal: bare, the preprocessor expands it too
# and the line comes back as `LWIPPROBE (16) = (16)`, with the option's identity gone.
_LWIP_PROBE_MARK = "LWIPPROBE"
_MAX_SHIFT = 64
_DEFAULT_COMPILER = "arm-none-eabi-gcc"
# @tunable tool.preprocess_timeout_s = 120
_PREPROCESS_TIMEOUT_S = 120
# pico-sdk 2.3.0 names every object <source>.o (cmake/preload/toolchains/util/pico_gcc_common.cmake:45),
# and CMake writes an outside source's object at its absolute path under the target dir.
_FIRMWARE_OBJECT_SUFFIX = ".o"
_TICK_PROBE_MARK = "TICKPROBE"
# The host binary's runtime probe: modlwip is `socket`, and lwIP's cyclic timers, started by reset()
# and run by the event hook while it sleeps, outlive two 1 s IPv6 reassembly ticks.
_LWIP_HOST_TIMERS_OK = "lwip timers ok"
_LWIP_HOST_PROBE = f"import lwip, socket, time; print(socket is lwip); lwip.reset(); time.sleep_ms(2500); lwip.callback(); print({_LWIP_HOST_TIMERS_OK!r})"
# ports/unix/unix_mphal.c, whose sighandler() takes SIGINT; the body runs to the next function.
_KBD_INTR_PP_SOURCE = "unix_mphal"
_SIGHANDLER_START = "static void sighandler(int signum)"
_SIGHANDLER_END = "void mp_hal_set_interrupt_char"

# Every directory the apply_*() functions write under build_overrides/; setup removes any other it finds there.
CURRENT_OVERRIDE_DIRS = (UNIX_KBD_INTR_DIR_NAME, LWIP_OVERRIDE_BOARD_DIR_NAME, MODLWIP_OVERRIDE_DIR_NAME, UNIX_LWIP_HOST_DIR_NAME, TICK_OFFSET_DIR_NAME)


def _eval_macro_expression(text: str) -> int:
    # Evaluates a preprocessed integer constant expression (e.g. `(8 * (800))`) with no eval() -
    # lwIP options are arithmetic over literals, and anything else must fail loudly, not guess.

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
            if isinstance(node.op, ast.FloorDiv):  # C's `/`, rewritten below: truncates toward zero
                if right == 0:
                    raise OverrideError(f"lwip_connection_counts: cannot evaluate preprocessed option value {text!r} - it divides by zero")
                quotient = abs(left) // abs(right)
                return -quotient if (left < 0) != (right < 0) else quotient
            if isinstance(node.op, (ast.LShift, ast.RShift)):
                if not 0 <= right < _MAX_SHIFT:  # C leaves these undefined; never guess a value
                    raise OverrideError(f"lwip_connection_counts: cannot evaluate preprocessed option value {text!r} - shift count {right} is outside 0..{_MAX_SHIFT - 1}")
                return left << right if isinstance(node.op, ast.LShift) else left >> right
        raise OverrideError(f"lwip_connection_counts: cannot evaluate preprocessed option value {text!r} - it is not an integer constant expression")

    try:
        return walk(ast.parse(text.replace("/", "//"), mode="eval"))
    except SyntaxError as exc:
        raise OverrideError(f"lwip_connection_counts: cannot parse preprocessed option value {text!r}") from exc


def _recorded_c_compiler(build_dir: Path, flags_text: str) -> str:
    # The C compiler CMake itself chose for this build: flags.make's own header line, else
    # CMakeCache.txt's CMAKE_C_COMPILER, else the toolchain's usual name on PATH.
    match = re.search(r"^# compile C with (\S.*)$", flags_text, re.MULTILINE)
    if match is not None:
        return match.group(1).strip()
    cache = build_dir / "CMakeCache.txt"
    if cache.is_file():
        match = re.search(r"^CMAKE_C_COMPILER:[A-Z]+=(\S.*)$", cache.read_text(), re.MULTILINE)
        if match is not None:
            return match.group(1).strip()
    return _DEFAULT_COMPILER


def _preprocess_with_build_flags(build_dir: Path, probe_body: str, name: str, what: str, reverify: str, compiler: str | None) -> str:
    # Preprocesses probe_body with the exact flags (and, unless `compiler` is given, the compiler)
    # CMake built the firmware with, returning the output; each failure names `what` was read.
    flags_make = build_dir / "CMakeFiles" / "firmware.dir" / "flags.make"
    if not flags_make.is_file():
        raise OverrideError(f"{name}: no compile flags at {flags_make} - the firmware build did not get as far as configuring, so nothing can be verified.")
    text = flags_make.read_text()
    if compiler is None:
        compiler = _recorded_c_compiler(build_dir, text)
    args: list[str] = []
    for key in _FLAGS_MAKE_KEYS:
        match = re.search(rf"^{key} = (.*)$", text, re.MULTILINE)
        if match is None:
            raise OverrideError(f"{name}: {flags_make} has no {key} line - CMake's generated layout has changed. {reverify}")
        args.extend(shlex.split(match.group(1)))
    with tempfile.TemporaryDirectory() as tmp:
        probe = Path(tmp) / "build_flags_probe.c"
        probe.write_text(probe_body)
        # -E only: this never links or runs anything, it just asks the preprocessor what the real
        # build's own macros resolved to. -P drops the line markers that would confuse the scan.
        try:
            result = subprocess.run([compiler, "-E", "-P", *args, str(probe)], capture_output=True, text=True, check=False, timeout=_PREPROCESS_TIMEOUT_S)
        except subprocess.TimeoutExpired as exc:
            raise OverrideError(f"{name}: preprocessing {what} with compiler {compiler!r} did not finish within {_PREPROCESS_TIMEOUT_S} s") from exc
        except OSError as exc:
            raise OverrideError(f"{name}: cannot run the C compiler {compiler!r} to read back {what} ({exc}) - is the ARM toolchain installed and on PATH?") from exc
    if result.returncode != 0:
        raise OverrideError(f"{name}: preprocessing {what} with the real build flags failed:\n{result.stderr.strip()[:2000]}")
    return result.stdout


def read_lwip_macros_from_build(build_dir: Path, macros: dict[str, int], compiler: str | None = None) -> dict[str, int]:
    # Preprocesses lwIP's own opt.h with the exact flags (and, unless `compiler` is given, the
    # compiler) CMake built the firmware with, returning each option's resolved value - proof the
    # override landed rather than an assumption the generated header was found (Part B.14.2).
    probe_body = '#include "lwip/opt.h"\n' + "".join(f'{_LWIP_PROBE_MARK} "{name}" = {name}\n' for name in (*macros, LWIP_OVERRIDE_SENTINEL))
    output = _preprocess_with_build_flags(build_dir, probe_body, "lwip_connection_counts", "lwIP's options", _LWIP_REVERIFY, compiler)
    found: dict[str, int] = {}
    for line in output.splitlines():
        stripped = line.strip()
        if stripped.startswith(_LWIP_PROBE_MARK):
            name, _, value = stripped[len(_LWIP_PROBE_MARK):].partition("=")
            name, value = name.strip().strip('"'), value.strip()
            if value != name:  # an undefined macro comes back as its own name: absent, not a value
                found[name] = _eval_macro_expression(value)
    return found


def verify_lwip_macros_in_build(build_dir: Path, macros: dict[str, int], compiler: str | None = None) -> dict[str, int]:
    # read_lwip_macros_from_build() plus the assertion. Raises OverrideError naming every option
    # whose resolved value differs from what was asked for.
    found = read_lwip_macros_from_build(build_dir, macros, compiler)
    if found.get(LWIP_OVERRIDE_SENTINEL) != 1:
        raise OverrideError(
            f"lwip_connection_counts: the generated lwipopts.h was never reached by the firmware's own "
            f"translation unit - its sentinel {LWIP_OVERRIDE_SENTINEL} is absent, so every option came "
            f"from MicroPython's defaults however the values below compare. The BOARD_DIR redirect or "
            f"the include ordering it depends on has changed. {_LWIP_REVERIFY}",
        )
    wrong = {name: (want, found.get(name)) for name, want in macros.items() if found.get(name) != want}
    if wrong:
        detail = ", ".join(f"{name}: asked {want}, built {got}" for name, (want, got) in sorted(wrong.items()))
        raise OverrideError(
            f"lwip_connection_counts: the generated lwipopts.h did not reach the firmware's own "
            f"translation unit - {detail}. The build is NOT configured as asked. {_LWIP_REVERIFY}",
        )
    return found


def _check_unix_kbd_intr_pp(pp_text: str, pp_path: Path) -> None:
    # One build's preprocessed unix_mphal.c: the sentinel reached, the last MICROPY_ASYNC_KBD_INTR
    # definition (0), sighandler() calling mp_sched_keyboard_interrupt() and never nlr_jump().
    if not re.search(rf"^#define {UNIX_KBD_INTR_SENTINEL} 1\s*$", pp_text, re.MULTILINE):
        raise OverrideError(f"unix_kbd_intr: sentinel absent: the variant redirect was not used - {pp_path} never reached the generated mpconfigvariant.h (SPECIFICATION.md B.14.1)")
    defines = re.findall(r"^#define MICROPY_ASYNC_KBD_INTR\s+(.*?)\s*$", pp_text, re.MULTILINE)
    last = defines[-1] if defines else None
    if last != "(0)":
        raise OverrideError(f"unix_kbd_intr: the immediate nlr_raise() path was compiled - the last MICROPY_ASYNC_KBD_INTR definition in {pp_path} is {last!r}, not '(0)' (SPECIFICATION.md B.14.1)")
    start = pp_text.find(_SIGHANDLER_START)
    end = pp_text.find(f"\n{_SIGHANDLER_END}", start) if start >= 0 else -1
    if end < 0:
        raise OverrideError(f"unix_kbd_intr: unix_mphal.pp has no sighandler(): the pinned source changed - re-verify SPECIFICATION.md B.14.1 ({pp_path})")
    body = pp_text[start:end]
    if "nlr_jump(" in body or "mp_sched_keyboard_interrupt()" not in body:
        raise OverrideError(f"unix_kbd_intr: the immediate nlr_raise() path was compiled - sighandler() in {pp_path} calls nlr_jump() or never mp_sched_keyboard_interrupt() (SPECIFICATION.md B.14.1)")


def verify_unix_kbd_intr_in_build(unix_dir: Path, make_vars: dict[str, str], build_dir_name: str, *, env: dict[str, str]) -> None:
    # Re-preprocesses unix_mphal.c with this build's own make variables, so with the very flags it
    # was compiled with (py/mkrules.mk's $(BUILD)/%.pp rule), checks it, and removes the .pp.
    variables = dict(make_vars)
    if variables.setdefault("BUILD", build_dir_name) != build_dir_name:
        raise OverrideError(f"unix_kbd_intr: the make variables name BUILD={variables['BUILD']}, not the build being proven ({build_dir_name})")
    search_path = env.get("PATH")
    make = shutil.which("make", path=search_path) if search_path else None
    if make is None:
        raise OverrideError(f"unix_kbd_intr: no `make` on the build's PATH ({search_path!r}) to preprocess unix_mphal.c with")
    pp_path = unix_dir / build_dir_name / f"{_KBD_INTR_PP_SOURCE}.pp"
    argv = [make, *(f"{key}={value}" for key, value in variables.items()), f"{build_dir_name}/{_KBD_INTR_PP_SOURCE}.pp"]
    pp_path.unlink(missing_ok=True)  # else a .pp an interrupted run left behind could vouch for this build
    try:
        try:
            result = subprocess.run(argv, cwd=unix_dir, env=env, capture_output=True, text=True, check=False, timeout=_PREPROCESS_TIMEOUT_S)
        except subprocess.TimeoutExpired as exc:
            raise OverrideError(f"unix_kbd_intr: preprocessing unix_mphal.c for {build_dir_name} did not finish within {_PREPROCESS_TIMEOUT_S} s") from exc
        except OSError as exc:
            raise OverrideError(f"unix_kbd_intr: cannot run {make!r} to preprocess unix_mphal.c ({exc})") from exc
        if result.returncode != 0 or not pp_path.is_file():
            raise OverrideError(f"unix_kbd_intr: `{' '.join(argv)}` did not produce {pp_path} (exit {result.returncode}):\n{(result.stdout + result.stderr).strip()[-2000:]}")
        _check_unix_kbd_intr_pp(pp_path.read_text(errors="replace"), pp_path)
    finally:
        pp_path.unlink(missing_ok=True)


def verify_modlwip_eagain_in_build(build_dir: Path, micropython_dir: Path, copy_path: Path) -> None:
    # The firmware target's own CMake rules compile the patched copy, never extmod/modlwip.c, into
    # exactly one non-empty object at the copy's mirrored path. Raises OverrideError naming the miss.
    target_dir = build_dir / "CMakeFiles" / "firmware.dir"
    build_make = target_dir / "build.make"
    if not build_make.is_file():
        raise OverrideError(f"modlwip_eagain: no {build_make} - CMake's generated layout changed - re-verify the post-build proof (SPECIFICATION.md B.14)")
    text = build_make.read_text()
    copy_object = f"CMakeFiles/firmware.dir{copy_path}{_FIRMWARE_OBJECT_SUFFIX}"
    if f"{copy_object}: {copy_path}\n" not in text:
        raise OverrideError(f"modlwip_eagain: {build_make} has no rule `{copy_object}: {copy_path}` - it does not compile the patched copy, or CMake's generated layout changed. {_MODLWIP_REVERIFY}")
    original = micropython_dir / "extmod" / "modlwip.c"
    named = sorted({str(path) for path in (original, original.resolve()) if str(path) in text})
    if named:
        raise OverrideError(f"modlwip_eagain: {build_make} still compiles the original {named[0]} - the image would carry the 10 s ERR_MEM retry loop. {_MODLWIP_REVERIFY}")
    expected = build_dir / copy_object
    objects = sorted(target_dir.rglob(f"*{MODLWIP_COPY_NAME}{_FIRMWARE_OBJECT_SUFFIX}"))
    if objects != [expected]:
        raise OverrideError(f"modlwip_eagain: expected exactly one {MODLWIP_COPY_NAME}{_FIRMWARE_OBJECT_SUFFIX} under {target_dir}, at {expected}; found {[str(path) for path in objects]}. {_MODLWIP_REVERIFY}")
    if expected.stat().st_size == 0:
        raise OverrideError(f"modlwip_eagain: {expected} is empty - the patched copy did not compile into the image. {_MODLWIP_REVERIFY}")


def verify_unix_lwip_host_in_build(build_dir: Path, micropython_dir: Path, binary: Path, *, env: dict[str, str]) -> None:
    # The host build compiled the patched copy, never extmod/modlwip.c (its dependency file names
    # the source first), and the built binary's `socket` is modlwip. Raises OverrideError naming it.
    dep_file = build_dir / "extmod" / "modlwip.P"
    if not dep_file.is_file():
        raise OverrideError(f"unix_lwip_host: no {dep_file} - extmod/modlwip.c was not compiled into this build, or py/mkrules.mk's dependency files moved; {_LWIP_HOST_REVERIFY}")
    unix_dir = build_dir.parent
    entries = [entry for entry in dep_file.read_text().partition(":")[2].split() if entry != "\\"]
    sources = [(unix_dir / entry.rstrip(":")).resolve() for entry in entries]
    original = (micropython_dir / "extmod" / "modlwip.c").resolve()
    if not sources or original in sources:
        raise OverrideError(f"unix_lwip_host: {dep_file} names the original {original} or no source at all - the vpath swap did not happen; {_LWIP_HOST_REVERIFY}")
    if sources[0].parts[-4:] != (UNIX_LWIP_HOST_DIR_NAME, "src", "extmod", MODLWIP_COPY_NAME) or _MODLWIP_EAGAIN_BLOCK not in sources[0].read_text():
        raise OverrideError(f"unix_lwip_host: {dep_file} compiles {sources[0]}, not the patched copy; {_LWIP_HOST_REVERIFY}")
    try:
        result = subprocess.run([str(binary), "-c", _LWIP_HOST_PROBE], env=env, capture_output=True, text=True, check=False, timeout=_PREPROCESS_TIMEOUT_S)
    except subprocess.TimeoutExpired as exc:
        raise OverrideError(f"unix_lwip_host: {binary} did not answer the runtime probe within {_PREPROCESS_TIMEOUT_S} s") from exc
    except OSError as exc:
        raise OverrideError(f"unix_lwip_host: cannot run {binary} ({exc})") from exc
    printed = result.stdout.strip()
    lines = printed.splitlines()
    detail = f"the probe printed {printed!r} (exit {result.returncode}): {result.stderr.strip()[:2000]}"
    if lines[:1] != ["True"]:
        raise OverrideError(f"unix_lwip_host: {binary}'s socket module is not modlwip - {detail}")
    if result.returncode != 0 or lines[1:] != [_LWIP_HOST_TIMERS_OK]:
        raise OverrideError(f"unix_lwip_host: {binary} did not survive lwIP's own timers - {detail}")


def tick_offset_in_build(build_dir: Path) -> bool:
    # Whether the firmware's own translation units reach the tick-offset copy: py/mphal.h with the
    # build's recorded flags, its sentinel read back the way the lwIP readback reads its options.
    probe_body = f'#include "py/mphal.h"\n{_TICK_PROBE_MARK} = {TICK_OFFSET_SENTINEL}\n'
    output = _preprocess_with_build_flags(build_dir, probe_body, TICK_OFFSET_DIR_NAME, "the tick-offset sentinel", _TICK_OFFSET_REVERIFY, None)
    values = [line.strip()[len(_TICK_PROBE_MARK):].partition("=")[2].strip() for line in output.splitlines() if line.strip().startswith(_TICK_PROBE_MARK)]
    if values == ["1"]:
        return True
    if values == [TICK_OFFSET_SENTINEL]:  # an undefined macro comes back as its own name
        return False
    raise OverrideError(f"tick_offset_test: reading {TICK_OFFSET_SENTINEL} back from {build_dir} gave {values!r}, neither 1 nor absent - {_TICK_OFFSET_REVERIFY}")


def verify_tick_offset_in_build(build_dir: Path, *, expected: bool) -> None:
    # Run after every rp2 build: a release build (expected False) carrying the override is refused,
    # and so is a test build (expected True) that never reached it.
    found = tick_offset_in_build(build_dir)
    if found and not expected:
        raise OverrideError(f"tick_offset_test: a release build carries the tick-offset test override - {build_dir} reaches the generated mphalport.h, so ticks_ms() would wrap 15 minutes after boot. Build the release image without tick_offset_test (SPECIFICATION.md B.14).")
    if expected and not found:
        raise OverrideError(f"tick_offset_test: the test build at {build_dir} never reached the generated mphalport.h - its sentinel {TICK_OFFSET_SENTINEL} is absent, so the image wraps at the usual time. {_TICK_OFFSET_REVERIFY}")
