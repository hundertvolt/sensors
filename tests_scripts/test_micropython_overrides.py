"""Tests toolchain/micropython_overrides.py's build overrides in isolation - anchors, generated files
and post-build readbacks, against synthetic trees and fake build outputs, never a real compile (that is
`toolchain/setup_toolchain.py test`'s own proof). SPECIFICATION.md Part B.14 has the mechanism."""

import difflib
import os
import re
import struct
import sys
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING

import pytest
from _script_loader import load_script_module

if TYPE_CHECKING:
    from typing import Protocol

    class _Run(Protocol):
        # setup_toolchain.run()'s shape as the fakes take it: an argv, a cwd, keyword-only extras.
        def __call__(self, cmd: list[str], cwd: Path | None = None, **kwargs: object) -> str: ...

_REAL_ANCHOR_LINE = "#define MICROPY_ASYNC_KBD_INTR         (!MICROPY_PY_THREAD_GIL)"


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

# extmod/modlwip.c as pinned, cut to what modlwip_eagain checks: the local include, and
# lwip_tcp_send()'s ERR_MEM retry loop with the insertion point inside it.
_FAKE_MODLWIP_INCLUDE = '#include "modnetwork.h"'

_FAKE_POLL_SOCKETS = "static inline void poll_sockets(void) {\n    MICROPY_PY_LWIP_POLL_HOOK\n    mp_event_wait_ms(1);\n}\n"

_FAKE_MODLWIP_INSERT_AFTER = "        err = tcp_output(socket->pcb.tcp);\n        if (err != ERR_OK) {\n            break;\n        }\n"

_FAKE_MODLWIP_LOOP = (
    "    for (int i = 0; i < 200; ++i) {\n"
    "        err = tcp_write(socket->pcb.tcp, buf, write_len, TCP_WRITE_FLAG_COPY);\n"
    "        if (err != ERR_MEM) {\n"
    "            break;\n"
    "        }\n"
    f"{_FAKE_MODLWIP_INSERT_AFTER}"
    "        MICROPY_PY_LWIP_EXIT\n"
    "        mp_hal_delay_ms(50);\n"
    "        MICROPY_PY_LWIP_REENTER\n"
    "    }\n"
)

# The rp2 wiring, file by file and in the order the build reads it.
_FAKE_MODLWIP_WIRING = (
    ("extmod/extmod.cmake", ("set(MICROPY_SOURCE_EXTMOD\n", "    ${MICROPY_EXTMOD_DIR}/modlwip.c\n")),
    ("ports/rp2/CMakeLists.txt", (
        "include(${MICROPY_DIR}/extmod/extmod.cmake)",
        "include(${MICROPY_DIR}/py/usermod.cmake)",
        "list(APPEND MICROPY_SOURCE_QSTR\n    ${MICROPY_SOURCE_EXTMOD}\n",
        "target_sources(${MICROPY_TARGET} PRIVATE\n    ${MICROPY_SOURCE_PY}\n    ${MICROPY_SOURCE_EXTMOD}\n",
    )),
    ("ports/rp2/Makefile", ("CMAKE_ARGS += -DUSER_C_MODULES=${USER_C_MODULES}",)),
    ("py/usermod.cmake", ('set(USER_C_MODULE_PATH "${USER_C_MODULE_PATH}/micropython.cmake")', "include(${USER_C_MODULE_PATH})")),
)

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

# The texts below mirror a real `make build-standard/unix_mphal.pp` (gcc -E -dD -C) at v1.29.0.
_DEFERRED_HANDLER = "        if ((mp_state_ctx.thread.mp_pending_exception) == ((mp_obj_t)(&(mp_state_ctx.vm.mp_kbd_exception)))) {\n            exit(1);\n        }\n        mp_sched_keyboard_interrupt();\n"

_IMMEDIATE_HANDLER = '        sigprocmask(\n# 63 "unix_mphal.c" 3 4\n                   2\n# 63 "unix_mphal.c"\n                              , &mask, \n        nlr_jump(((void *)(((mp_obj_t)(&(mp_state_ctx.vm.mp_kbd_exception))))));\n'

# One entry per anchor verify_modlwip_eagain_anchor() checks, each dropped on its own below.
_EVERY_MODLWIP_ANCHOR = (_FAKE_MODLWIP_LOOP, _FAKE_MODLWIP_INSERT_AFTER, _FAKE_MODLWIP_INCLUDE, *(anchor for _path, anchors in _FAKE_MODLWIP_WIRING for anchor in anchors))

# The host build's own anchors as the minimum text around them, file by file and in order.
_FAKE_RP2_LWIP_SETTINGS = (
    "#define LWIP_NETIF_EXT_STATUS_CALLBACK  1",
    "#define LWIP_NETIF_STATUS_CALLBACK      1",
    "#define LWIP_IPV4                       1",
    "#define LWIP_IPV6                       1",
    "#define LWIP_ND6_NUM_DESTINATIONS       4",
    "#define LWIP_ND6_QUEUEING               0",
)

_FAKE_LWIP_HOST_ANCHORS = (
    ("extmod/extmod.mk", ("\textmod/modlwip.c \\\n", "ifeq ($(MICROPY_PY_LWIP),1)\n", "ifeq ($(MICROPY_PY_LWIP_LOOPBACK),1)\nCFLAGS_EXTMOD += -DLWIP_NETIF_LOOPBACK=1\n")),
    ("ports/unix/Makefile", ("include $(VARIANT_DIR)/mpconfigvariant.mk\n", "include $(TOP)/extmod/extmod.mk\n", "ifeq ($(MICROPY_PY_SOCKET),1)\n", "\t$(wildcard $(VARIANT_DIR)/*.c)\n", "include $(TOP)/py/mkrules.mk\n")),
    ("py/mkrules.mk", ("vpath %.c . $(TOP)",)),
    ("py/mphal.h", ("#ifndef MICROPY_INTERNAL_EVENT_HOOK\n",)),
    ("py/scheduler.c", ("void mp_event_handle_nowait(void) {\n", "    MICROPY_INTERNAL_EVENT_HOOK;\n")),
    ("lib/lwip/src/include/lwip/opt.h", ("#define LWIP_HAVE_LOOPIF                (LWIP_NETIF_LOOPBACK && !LWIP_SINGLE_NETIF)\n", "#define LWIP_NETIF_LOOPBACK_MULTITHREADING    (!NO_SYS)\n")),
    ("ports/rp2/lwip_inc/lwipopts.h", _FAKE_RP2_LWIP_SETTINGS),
)

_FAKE_TCP_OUT = "lib/lwip/src/core/tcp_out.c"

_EVERY_LWIP_HOST_ANCHOR = (
    _REAL_ANCHOR_LINE, _FAKE_MODLWIP_LOOP, _FAKE_MODLWIP_INSERT_AFTER, _FAKE_MODLWIP_INCLUDE, _FAKE_POLL_SOCKETS,
    *(anchor for _path, anchors in _FAKE_LWIP_HOST_ANCHORS for anchor in anchors), _FAKE_TCP_OUT,
)

# What a healthy host binary answers the runtime probe with: modlwip is `socket`, and lwIP's own
# timers ran past their first 1 s reassembly tick without an assertion stopping the process.
_PROBE_OK = "True\nlwip timers ok"

_FAKE_TICKS_MS = "static inline mp_uint_t mp_hal_ticks_ms(void) {\n    return to_ms_since_boot(get_absolute_time());\n}\n"


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


def _fake_firmware_build(root: Path, compiled: "tuple[Path, ...]", *, empty: bool = False) -> Path:
    # A build dir whose firmware target compiled exactly `compiled`, each with its build.make rule and object.
    build_dir = root / "build-RPI_PICO_W"
    target_dir = build_dir / "CMakeFiles" / "firmware.dir"
    target_dir.mkdir(parents=True)
    rules = []
    for source in compiled:
        obj = target_dir / f"{str(source).lstrip('/')}.o"
        obj.parent.mkdir(parents=True, exist_ok=True)
        obj.write_bytes(b"" if empty else b"\x7fELF")
        (obj.parent / f"{obj.name}.d").write_text(f"{obj}: {source}\n")
        rules.append(f"CMakeFiles/firmware.dir{source}.o: CMakeFiles/firmware.dir/flags.make\nCMakeFiles/firmware.dir{source}.o: {source}\n")
    (target_dir / "build.make").write_text("".join(rules))
    return build_dir


def _fake_lwip_host_build(tmp_path: Path, *, source: str | None = None, block: str = "kept", stdout: str = _PROBE_OK, exit_code: int = 0, sleep_s: float = 0, stderr: str = "") -> "tuple[Path, Path, Path]":
    # (build_dir, micropython_dir, binary): a build-lwip whose modlwip.P names `source` first (the
    # real layout: the target, a continued line, the source), and a binary answering the socket probe.
    micropython_dir = tmp_path / "micropython"
    build_dir = micropython_dir / "ports" / "unix" / "build-lwip"
    (build_dir / "extmod").mkdir(parents=True)
    copy = tmp_path / "build_overrides" / "unix_lwip_host_variant" / "src" / "extmod" / "modlwip.c"
    copy.parent.mkdir(parents=True)
    copy.write_text("err_t err;\n" + ("        if (socket->timeout == 0) {\n            // Non-blocking: hand the wait back to the caller rather than sleeping inside this call.\n            MICROPY_PY_LWIP_EXIT\n            *_errno = MP_EAGAIN;\n            return MP_STREAM_ERROR;\n        }\n" if block == "kept" else ""))
    named = source if source is not None else str(copy)
    (build_dir / "extmod" / "modlwip.P").write_text(f"build-lwip/extmod/modlwip.o: \\\n {named} \\\n ../../py/mpconfig.h\n../../py/mpconfig.h:\n")
    binary = build_dir / "micropython"
    binary.write_text(
        f"#!{sys.executable}\nimport pathlib, sys, time\npathlib.Path({str(tmp_path / 'probe-argv.txt')!r}).write_text(chr(10).join(sys.argv[1:]))\n"
        f"time.sleep({sleep_s})\nprint({stdout!r})\nsys.stderr.write({stderr!r})\nsys.exit({exit_code})\n",
    )
    binary.chmod(0o755)
    return build_dir, micropython_dir, binary


def _fake_make(tmp_path: Path, *, pp: str | None = "", exit_code: int = 0, sleep_s: float = 0) -> "tuple[dict[str, str], Path]":
    # A `make` on a PATH of its own that logs its argv and writes `pp` to the last argument (cwd-relative);
    # with pp None it writes nothing, as a rule that stopped producing its target would.
    bindir = tmp_path / "fake-bin"
    bindir.mkdir()
    argv_log = tmp_path / "make-argv.txt"
    make = bindir / "make"
    make.write_text(
        f"#!{sys.executable}\nimport pathlib, sys, time\npathlib.Path({str(argv_log)!r}).write_text(chr(10).join(sys.argv[1:]))\n"
        f"time.sleep({sleep_s})\n" + ("" if pp is None else f"pathlib.Path(sys.argv[-1]).write_text({pp!r})\n") + f"print('PreProcess unix_mphal.c')\nsys.exit({exit_code})\n",
    )
    make.chmod(0o755)
    return {"PATH": str(bindir)}, argv_log


def _modlwip_paths(tmp_path: Path) -> "tuple[Path, Path, Path]":
    # (micropython_dir, the original modlwip.c, the patched copy), all absolute as the build sees them.
    micropython_dir = tmp_path.resolve() / "toolchain" / "micropython"
    copy_path = tmp_path.resolve() / "toolchain" / "build_overrides" / "modlwip_eagain" / "modlwip.c"
    return micropython_dir, micropython_dir / "extmod" / "modlwip.c", copy_path


def _pinned() -> "dict[str, int]":
    # MicroPython's own pinned block, which is itself a tuned set - see the test below.
    return {
        "MEMP_NUM_TCP_PCB": 5, "MEMP_NUM_TCP_PCB_LISTEN": 8, "MEMP_NUM_PBUF": 16,
        "PBUF_POOL_SIZE": 16, "MEMP_NUM_UDP_PCB": 5, "LWIP_STATS": 0, "MEM_SIZE": 8000,
        "TCP_MSS": 800, "TCP_WND": 6400, "TCP_SND_BUF": 6400, "MEMP_NUM_TCP_SEG": 32,
    }


def _pp_text(*, sentinel: bool = True, last_define: str = "(0)", handler: str = _DEFERRED_HANDLER, with_handler: bool = True) -> str:
    defines = "#define MICROPY_ASYNC_KBD_INTR (!MICROPY_PY_THREAD_GIL)\n#undef MICROPY_ASYNC_KBD_INTR\n" + f"#define MICROPY_ASYNC_KBD_INTR {last_define}\n"
    body = f'static void sighandler(int signum) {{\n    if (signum == \n# 50 "unix_mphal.c" 3 4\n                 2\n                       ) {{\n{handler}    }}\n}}\n\n\n' if with_handler else ""
    return (
        '# 1 "unix_mphal.c"\n#define nlr_raise(val) nlr_jump(MP_OBJ_TO_PTR(val))\n' + defines
        + ("#define MICROPY_SENSORS_KBD_INTR_OVERRIDE_APPLIED 1\n" if sentinel else "")
        + body + "void mp_hal_set_interrupt_char(char c) {\n}\n"
    )


def _probe_lines(values: "dict[str, str]") -> str:
    return "".join(f'LWIPPROBE "{name}" = {value}\n' for name, value in values.items())


def _stub_build_readbacks(setup_toolchain: ModuleType, monkeypatch: pytest.MonkeyPatch) -> "list[tuple[str, tuple[object, ...]]]":
    # The post-build proofs read a real build tree; the installer's structural tests record each
    # call instead (the proofs' own cases drive them over fake build outputs).
    calls: list[tuple[str, tuple[object, ...]]] = []
    for name in ("verify_unix_kbd_intr_in_build", "verify_modlwip_eagain_in_build", "verify_unix_lwip_host_in_build", "verify_tick_offset_in_build"):

        def record(*args: object, _name: str = name, **kwargs: object) -> None:
            calls.append((_name, (*args, *kwargs.values())))

        monkeypatch.setattr(setup_toolchain.micropython_overrides, name, record)
    return calls


def _tree_state(root: Path) -> "list[tuple[str, int, int]]":
    # Every path under root with its size and mtime: a write inside the tree changes this.
    return sorted((str(path.relative_to(root)), path.stat().st_size, path.stat().st_mtime_ns) for path in root.rglob("*"))


def _write_fake_lwip_host_tree(root: Path, *, drop: str | None = None) -> Path:
    # Everything the host build flavour checks - the SIGINT anchor, modlwip's, and its own - with
    # `drop` leaving exactly one out.
    _write_fake_micropython_tree(root, anchor_line=None if drop == _REAL_ANCHOR_LINE else _REAL_ANCHOR_LINE)
    _write_fake_modlwip_tree(root, drop=drop)
    for relative, anchors in _FAKE_LWIP_HOST_ANCHORS:
        (root / relative).parent.mkdir(parents=True, exist_ok=True)
        (root / relative).write_text("".join(f"{anchor}\n" for anchor in anchors if anchor != drop))
    if drop != _FAKE_TCP_OUT:
        (root / _FAKE_TCP_OUT).parent.mkdir(parents=True, exist_ok=True)
        (root / _FAKE_TCP_OUT).write_text("")
    return root


def _write_fake_lwip_tree(root: Path, *, drop: str | None = None, board: str = _REAL_BOARD) -> Path:
    # A synthetic tree carrying every anchor the override checks; `drop` removes exactly one, so a
    # test can prove that anchor is really load-bearing rather than decorative.
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


def _write_fake_modlwip_tree(root: Path, *, drop: str | None = None) -> Path:
    # The modlwip_eagain anchors as the minimum text around them, added to a tree that may already
    # hold the lwIP override's files; `drop` leaves exactly one anchor out.
    source = ['#include "py/mphal.h"', _FAKE_MODLWIP_INCLUDE, _FAKE_POLL_SOCKETS, "static mp_uint_t lwip_tcp_send(void) {", "    err_t err;", _FAKE_MODLWIP_LOOP, "    return 0;", "}"]
    (root / "extmod").mkdir(parents=True, exist_ok=True)
    (root / "extmod" / "modlwip.c").write_text("\n".join(line for line in source if line != drop and not (drop == _FAKE_MODLWIP_INSERT_AFTER and line == _FAKE_MODLWIP_LOOP)) + "\n")
    for relative, anchors in _FAKE_MODLWIP_WIRING:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a") as f:
            f.write("".join(f"{anchor}\n" for anchor in anchors if anchor != drop) + ")\n")
    (root / "py" / "mpconfig.h").write_text("#define MICROPY_VERSION_MAJOR 1\n#define MICROPY_VERSION_MINOR 29\n#define MICROPY_VERSION_MICRO 0\n")
    return root


def _write_fake_mphalport(root: Path, body: str = _FAKE_TICKS_MS) -> Path:
    # ports/rp2/mphalport.h as pinned, cut to mp_hal_ticks_ms() and its neighbours.
    header = root / "ports" / "rp2" / "mphalport.h"
    header.parent.mkdir(parents=True, exist_ok=True)
    header.write_text(f'#include "pico/time.h"\n\nstatic inline mp_uint_t mp_hal_ticks_us(void) {{\n    return time_us_32();\n}}\n\n{body}')
    return root


@pytest.fixture(scope="session")
def overrides(repo_root: Path) -> ModuleType:
    return load_script_module(repo_root / "toolchain" / "micropython_overrides.py", "micropython_overrides")


@pytest.fixture
def setup_toolchain(repo_root: Path) -> ModuleType:
    return load_script_module(repo_root / "toolchain" / "setup_toolchain.py", "setup_toolchain")


class TestVerifyUnixKbdIntrAnchor:
    def test_passes_against_the_real_pinned_source(self, overrides: ModuleType, micropython_dir: Path) -> None:
        common_header = micropython_dir / "ports" / "unix" / "variants" / "mpconfigvariant_common.h"
        if not common_header.is_file():
            pytest.fail(f"no real toolchain checkout at {micropython_dir} - build it with `uv run toolchain/setup_toolchain.py setup` (scripts/test.sh does)")
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
        assert result == {"VARIANT": "standard", "VARIANT_DIR": str(overrides_dir.resolve() / "unix_kbd_intr_variant")}

    def test_never_writes_inside_the_micropython_tree(self, overrides: ModuleType, tmp_path: Path) -> None:
        fake_mp_dir = _write_fake_micropython_tree(tmp_path / "micropython")
        before = sorted(p.relative_to(fake_mp_dir) for p in fake_mp_dir.rglob("*"))
        overrides.apply_unix_kbd_intr_override(fake_mp_dir, tmp_path / "build_overrides")
        after = sorted(p.relative_to(fake_mp_dir) for p in fake_mp_dir.rglob("*"))
        assert before == after, "the fetched checkout must never gain, lose, or have a file rewritten"

    def test_generated_mpconfigvariant_h_includes_the_real_file_and_forces_the_safe_path(self, overrides: ModuleType, tmp_path: Path) -> None:
        fake_mp_dir = _write_fake_micropython_tree(tmp_path / "micropython")
        real_header = fake_mp_dir.resolve() / "ports" / "unix" / "variants" / "standard" / "mpconfigvariant.h"
        override_dir = tmp_path / "build_overrides" / "unix_kbd_intr_variant"
        overrides.apply_unix_kbd_intr_override(fake_mp_dir, tmp_path / "build_overrides")
        generated = (override_dir / "mpconfigvariant.h").read_text()
        assert f'#include "{real_header}"' in generated
        assert "#undef MICROPY_ASYNC_KBD_INTR" in generated
        assert "#define MICROPY_ASYNC_KBD_INTR (0)" in generated
        # Ordering matters: the undef must follow the include (so it wins), the define follow the undef;
        # the sentinel the post-build readback looks for comes last.
        include_pos = generated.index(f'#include "{real_header}"')
        undef_pos = generated.index("#undef MICROPY_ASYNC_KBD_INTR")
        define_pos = generated.index("#define MICROPY_ASYNC_KBD_INTR (0)")
        sentinel_pos = generated.index(f"#define {overrides.UNIX_KBD_INTR_SENTINEL} 1\n")
        assert include_pos < undef_pos < define_pos < sentinel_pos

    def test_generated_mpconfigvariant_mk_relays_to_the_real_file(self, overrides: ModuleType, tmp_path: Path) -> None:
        fake_mp_dir = _write_fake_micropython_tree(tmp_path / "micropython")
        real_mk = fake_mp_dir.resolve() / "ports" / "unix" / "variants" / "standard" / "mpconfigvariant.mk"
        override_dir = tmp_path / "build_overrides" / "unix_kbd_intr_variant"
        overrides.apply_unix_kbd_intr_override(fake_mp_dir, tmp_path / "build_overrides")
        assert (override_dir / "mpconfigvariant.mk").read_text().startswith(f"include {real_mk}\n")

    def test_generated_manifest_relays_via_include_rather_than_copying(self, overrides: ModuleType, tmp_path: Path) -> None:
        # include() (not a raw copy) so the generated manifest can never drift out of sync with a
        # future pinned-version change to the real one.
        fake_mp_dir = _write_fake_micropython_tree(tmp_path / "micropython")
        real_manifest = fake_mp_dir.resolve() / "ports" / "unix" / "variants" / "standard" / "manifest.py"
        override_dir = tmp_path / "build_overrides" / "unix_kbd_intr_variant"
        overrides.apply_unix_kbd_intr_override(fake_mp_dir, tmp_path / "build_overrides")
        assert (override_dir / "manifest.py").read_text() == f"include({str(real_manifest)!r})\n"

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
    # Guards the wiring, not just the override function: an edit that drops build_unix_port()'s
    # call to apply_unix_kbd_intr_override(), or stops threading its make variables into the real
    # command, must fail a test rather than silently ship an unpatched binary again.

    def _recorded_make_cmd(
        self, setup_toolchain: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, settrace: bool,
    ) -> list[str]:
        # Builds one variant against a fake tree and returns the make command it constructed.
        fake_mp_dir = _write_fake_micropython_tree(tmp_path / "toolchain" / "micropython")
        toolchain_dir = tmp_path / "toolchain"
        expected_dir = setup_toolchain.UNIX_SETTRACE_BUILD_DIR if settrace else setup_toolchain.UNIX_BUILD_DIR
        build_dir = fake_mp_dir / "ports" / "unix" / expected_dir
        recorded: list[list[str]] = []

        def fake_run(cmd: list[str], cwd: Path | None = None, **_kwargs: object) -> str:
            recorded.append(cmd)
            if cmd[0] == "make":
                build_dir.mkdir(parents=True, exist_ok=True)
                (build_dir / "micropython").write_text("#!/bin/sh\necho fake\n")
                return f"LINK {expected_dir}/micropython\n"
            return "namespace(name='micropython')"

        monkeypatch.setattr(setup_toolchain, "run", fake_run)
        _stub_build_readbacks(setup_toolchain, monkeypatch)
        binary = setup_toolchain.build_unix_port(fake_mp_dir, toolchain_dir, jobs=4, settrace=settrace)
        assert binary == build_dir / "micropython", f"the {expected_dir} variant must be returned from its own build dir"
        return recorded[0]

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

        def fake_run(cmd: list[str], cwd: Path | None = None, **_kwargs: object) -> str:
            recorded.append(cmd)
            if cmd[0] == "make":
                # Stands in for what a real `make` invocation would produce - build_unix_port()'s
                # own binary.exists() check right after this needs something there.
                build_dir.mkdir(parents=True, exist_ok=True)
                (build_dir / "micropython").write_text("#!/bin/sh\necho fake\n")
                return "LINK build-standard/micropython\n"
            return "namespace(name='micropython')"  # stands in for the post-build sys.implementation probe

        monkeypatch.setattr(setup_toolchain, "run", fake_run)
        _stub_build_readbacks(setup_toolchain, monkeypatch)
        setup_toolchain.build_unix_port(fake_mp_dir, toolchain_dir, jobs=4)

        make_cmd = recorded[0]
        assert make_cmd[0] == "make"
        assert "VARIANT=standard" in make_cmd
        assert f"VARIANT_DIR={toolchain_dir.resolve() / 'build_overrides' / 'unix_kbd_intr_variant'}" in make_cmd

    def test_the_test_rig_variant_is_built_without_the_settrace_flag(
        self, setup_toolchain: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # The whole point of the 2026-09-21 split (Part E.5.2): compiled in, the flag allocates a
        # frame and a code object per call, inflating every figure the memory work measures 4-5x.
        # Re-adding it to the default path is silent until a binary is rebuilt - so assert it here.
        make_cmd = self._recorded_make_cmd(setup_toolchain, tmp_path, monkeypatch, settrace=False)
        flags = next((arg for arg in make_cmd if arg.startswith("CFLAGS_EXTRA=")), "")
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

    def test_the_shell_side_looks_for_every_build_flavour_where_it_is_built(self, repo_root: Path, setup_toolchain: ModuleType) -> None:
        # Both consumers spell the directory out, because they resolve a binary before anything can
        # ask it what it is. A renamed constant would leave scripts/test.sh rebuilding into a path
        # it never looks at, and tests_scripts/test_coverage_runner.py skipping itself in silence.
        shell = (repo_root / "scripts" / "test.sh").read_text()
        conftest = (repo_root / "tests_scripts" / "conftest.py").read_text()
        for variant in setup_toolchain.CURRENT_UNIX_BUILD_DIRS:
            assert f'"$unix_dir/{variant}/micropython"' in shell, f"scripts/test.sh no longer resolves the {variant} binary - the constant and the shell have drifted apart"
        assert f'"{setup_toolchain.UNIX_BUILD_DIR}"' in conftest, f"tests_scripts/conftest.py's micropython_bin fixture no longer points at {setup_toolchain.UNIX_BUILD_DIR}"

    def test_a_setup_run_builds_every_build_flavour(self, repo_root: Path) -> None:
        # Structural: the real call is a multi-minute compile. What has to hold is that the
        # verification sequence asks for the settrace and lwIP host flavours at all - without them,
        # --coverage and the lwIP host test files have no binary, and scripts/test.sh fails a run it cannot repair.
        source = (repo_root / "toolchain" / "setup_toolchain.py").read_text()
        assert "build_unix_port(micropython_dir, toolchain_dir, jobs, settrace=True)" in source, "setup must build the --coverage variant too, or scripts/test.sh --coverage has nothing to run"
        assert "build_unix_lwip_port(micropython_dir, toolchain_dir, jobs)" in source, "setup must build the lwIP host flavour too, or the lwIP host test files have nothing to run on"

    def test_raises_before_ever_invoking_make_when_the_override_cannot_be_verified(
        self, setup_toolchain: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # A stale/mismatched pinned source must fail loudly at the override's own verify step,
        # never fall through to a real (unpatched) build.
        fake_mp_dir = _write_fake_micropython_tree(tmp_path / "toolchain" / "micropython", anchor_line=None)
        toolchain_dir = tmp_path / "toolchain"
        recorded: list[list[str]] = []

        def fake_run(cmd: list[str], cwd: Path | None = None, **_kwargs: object) -> str:
            recorded.append(cmd)
            return ""

        monkeypatch.setattr(setup_toolchain, "run", fake_run)

        with pytest.raises(setup_toolchain.micropython_overrides.OverrideError):
            setup_toolchain.build_unix_port(fake_mp_dir, toolchain_dir, jobs=4)
        assert recorded == []


# ---------------------------------------------------------------------------
# lwip_connection_counts (SPECIFICATION.md Part B.14.2)
# ---------------------------------------------------------------------------


class TestVerifyLwipConnectionCountsAnchor:
    def test_passes_against_the_real_pinned_source(self, overrides: ModuleType, micropython_dir: Path) -> None:
        if not (micropython_dir / "lib" / "lwip" / "src" / "include" / "lwip" / "opt.h").is_file():
            pytest.fail(f"no real toolchain checkout with lwIP submodules at {micropython_dir} - build it with `uv run toolchain/setup_toolchain.py setup` (scripts/test.sh does)")
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
        assert result == {"BOARD": _REAL_BOARD, "BOARD_DIR": str(tmp_path.resolve() / "build_overrides" / overrides.LWIP_OVERRIDE_BOARD_DIR_NAME)}

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
        real = fake.resolve() / "ports" / "rp2" / "lwip_inc" / "lwipopts.h"
        assert f'#include "{real}"' in generated
        include_pos = generated.index(f'#include "{real}"')
        for name, value in _LWIP_MACROS.items():
            # Ordering is the whole mechanism: the #undef must follow the include, so it beats
            # MicroPython's own plain #define, and the #define must follow the #undef.
            assert include_pos < generated.index(f"#undef {name}") < generated.index(f"#define {name} ({value})"), name

    def test_the_board_cmake_prepends_the_override_include_dir_and_relays_the_real_board(self, overrides: ModuleType, tmp_path: Path) -> None:
        fake = _write_fake_lwip_tree(tmp_path / "micropython")
        overrides.apply_lwip_connection_counts_override(fake, tmp_path / "build_overrides", _REAL_BOARD, _LWIP_MACROS)
        override_dir = tmp_path.resolve() / "build_overrides" / overrides.LWIP_OVERRIDE_BOARD_DIR_NAME
        real_board = fake.resolve() / "ports" / "rp2" / "boards" / _REAL_BOARD
        cmake = (override_dir / "mpconfigboard.cmake").read_text()
        # BEFORE, not a plain include_directories(): a plain one lands after the port's own
        # target-level lwip_inc and the real lwipopts.h would silently win again.
        assert f'include_directories(BEFORE "{override_dir / overrides.LWIP_OVERRIDE_INCLUDE_DIR_NAME}")' in cmake
        assert f'include("{real_board / "mpconfigboard.cmake"}")' in cmake
        assert f'set(MICROPY_BOARD_PINS "{real_board / "pins.csv"}")' in cmake

    def test_the_board_header_and_manifest_relay_rather_than_copy(self, overrides: ModuleType, tmp_path: Path) -> None:
        # The real board cmake points MICROPY_FROZEN_MANIFEST at ${MICROPY_BOARD_DIR}, which is now
        # the generated directory - so both have to be relayed, and by reference so neither drifts.
        fake = _write_fake_lwip_tree(tmp_path / "micropython")
        overrides.apply_lwip_connection_counts_override(fake, tmp_path / "build_overrides", _REAL_BOARD, _LWIP_MACROS)
        override_dir = tmp_path / "build_overrides" / overrides.LWIP_OVERRIDE_BOARD_DIR_NAME
        real_board = fake.resolve() / "ports" / "rp2" / "boards" / _REAL_BOARD
        assert (override_dir / "mpconfigboard.h").read_text() == f'#include "{real_board / "mpconfigboard.h"}"\n'
        assert (override_dir / "manifest.py").read_text() == f"include({str(real_board / 'manifest.py')!r})\n"

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

    def test_the_mem_size_floor_is_the_earlier_configurations_share(self, overrides: ModuleType) -> None:
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
    # Guards build_firmware()'s wiring the way TestBuildUnixPortAppliesTheOverride guards the Unix
    # port's: the override's make variables reach `make`, and the readback runs on the real build.

    def _fake_runner(self, rp2_dir: Path, recorded: "list[list[str]]") -> "_Run":
        def fake_run(cmd: "list[str]", cwd: "Path | None" = None, **_kwargs: object) -> str:
            recorded.append(cmd)
            build_dir = rp2_dir / f"build-{_REAL_BOARD}"
            (build_dir / "CMakeFiles" / "firmware.dir").mkdir(parents=True, exist_ok=True)
            (build_dir / "CMakeFiles" / "firmware.dir" / "flags.make").write_text("C_DEFINES = \nC_INCLUDES = \nC_FLAGS = \n")
            (build_dir / "firmware.uf2").write_bytes(b"")
            return ""

        return fake_run

    @pytest.fixture
    def setup_toolchain(self, repo_root: Path) -> ModuleType:
        return load_script_module(repo_root / "toolchain" / "setup_toolchain.py", "setup_toolchain")

    def test_make_gets_the_redirect_and_the_build_is_verified_against_the_table(self, setup_toolchain: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        toolchain_dir = tmp_path / "toolchain"
        fake_mp_dir = _write_fake_modlwip_tree(_write_fake_lwip_tree(toolchain_dir / "micropython"))
        rp2_dir = fake_mp_dir / "ports" / "rp2"
        recorded: list[list[str]] = []
        verified: list[tuple[Path, dict[str, int]]] = []
        monkeypatch.setattr(setup_toolchain, "run", self._fake_runner(rp2_dir, recorded))
        _stub_build_readbacks(setup_toolchain, monkeypatch)

        def record_verify(build_dir: Path, macros: "dict[str, int]", compiler: "str | None" = None) -> "dict[str, int]":
            verified.append((build_dir, macros))
            return dict(macros)

        monkeypatch.setattr(setup_toolchain.micropython_overrides, "verify_lwip_macros_in_build", record_verify)

        uf2 = setup_toolchain.build_firmware(fake_mp_dir, _REAL_BOARD, 4, toolchain_dir=toolchain_dir, lwip_macros=_pinned())

        assert uf2 == rp2_dir / f"build-{_REAL_BOARD}" / "firmware.uf2"
        (make_cmd,) = recorded
        assert make_cmd[0] == "make"
        assert f"BOARD={_REAL_BOARD}" in make_cmd
        assert f"BOARD_DIR={toolchain_dir.resolve() / 'build_overrides' / setup_toolchain.micropython_overrides.LWIP_OVERRIDE_BOARD_DIR_NAME}" in make_cmd
        assert verified == [(rp2_dir / f"build-{_REAL_BOARD}", _pinned())], "the readback must run on the real build dir with the very table applied"

    def test_an_anchorless_tree_raises_before_make_ever_runs(self, setup_toolchain: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        toolchain_dir = tmp_path / "toolchain"
        fake_mp_dir = _write_fake_modlwip_tree(_write_fake_lwip_tree(toolchain_dir / "micropython", drop="#ifndef MEM_SIZE"))
        recorded: list[list[str]] = []
        monkeypatch.setattr(setup_toolchain, "run", self._fake_runner(fake_mp_dir / "ports" / "rp2", recorded))
        _stub_build_readbacks(setup_toolchain, monkeypatch)
        with pytest.raises(setup_toolchain.micropython_overrides.OverrideError):
            setup_toolchain.build_firmware(fake_mp_dir, _REAL_BOARD, 4, toolchain_dir=toolchain_dir, lwip_macros=_pinned())
        assert recorded == []

    def test_a_versions_file_without_an_lwip_table_is_named(self, setup_toolchain: ModuleType, repo_root: Path, tmp_path: Path) -> None:
        # The shipped file minus its [lwip] table, so [lwip] is the one thing missing.
        shipped = (repo_root / "toolchain" / "versions.toml").read_text()
        versions = tmp_path / "versions.toml"
        versions.write_text(re.sub(r"^\[lwip\]\n(?:(?!\[).*\n?)*", "", shipped, flags=re.MULTILINE))
        with pytest.raises(setup_toolchain.SetupError, match=r"\[lwip\]"):
            setup_toolchain.load_lwip_macros(versions)

    def test_without_an_explicit_table_the_build_applies_versions_tomls_own(self, setup_toolchain: ModuleType, repo_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        # The path every real `setup` run takes: no table passed, so the pinned one must be what
        # reaches both the generated header and the readback - never lwIP's or the port's defaults.
        import tomllib

        with (repo_root / "toolchain" / "versions.toml").open("rb") as f:
            pinned = tomllib.load(f)["lwip"]
        assert setup_toolchain.load_lwip_macros() == pinned
        toolchain_dir = tmp_path / "toolchain"
        fake_mp_dir = _write_fake_modlwip_tree(_write_fake_lwip_tree(toolchain_dir / "micropython"))
        verified: list[dict[str, int]] = []
        monkeypatch.setattr(setup_toolchain, "run", self._fake_runner(fake_mp_dir / "ports" / "rp2", []))
        _stub_build_readbacks(setup_toolchain, monkeypatch)

        def record_verify(_build_dir: Path, macros: "dict[str, int]", _compiler: "str | None" = None) -> "dict[str, int]":
            verified.append(macros)
            return dict(macros)

        monkeypatch.setattr(setup_toolchain.micropython_overrides, "verify_lwip_macros_in_build", record_verify)
        setup_toolchain.build_firmware(fake_mp_dir, _REAL_BOARD, 4, toolchain_dir=toolchain_dir)
        assert verified == [pinned]


# ---------------------------------------------------------------------------
# Every path written into a generated file is resolved first, and refused when the make, CMake, C or
# manifest text could not carry it (SPECIFICATION.md B.14).
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("char", [" ", "\t", '"', "'", "\\", "$", "#", ";", ":"])
def test_a_path_a_generated_file_cannot_carry_is_refused_by_its_character(overrides: ModuleType, tmp_path: Path, char: str) -> None:
    fake = _write_fake_micropython_tree(tmp_path / "micropython")
    overrides_dir = tmp_path / f"build{char}overrides"
    with pytest.raises(overrides.OverrideError, match=re.escape(f"contains {char!r}")):
        overrides.apply_unix_kbd_intr_override(fake, overrides_dir)
    assert not overrides_dir.exists(), "nothing may be written under a refused path"


@pytest.mark.parametrize("apply", ["apply_unix_kbd_intr_override", "apply_lwip_connection_counts_override", "apply_modlwip_eagain_override", "apply_unix_lwip_host_override", "apply_tick_offset_override"])
def test_every_override_refuses_an_unembeddable_toolchain_dir_before_reading_anything(overrides: ModuleType, tmp_path: Path, apply: str) -> None:
    # The checkout is refused too, before any anchor is read: an empty tree would fail later, by another name.
    bad = tmp_path / "pico toolchain"
    extra: dict[str, object] = {"board": _REAL_BOARD} if apply == "apply_tick_offset_override" else {}
    args: tuple[object, ...] = {"apply_lwip_connection_counts_override": (_REAL_BOARD, _pinned()), "apply_unix_lwip_host_override": (_pinned(),)}.get(apply, ())
    with pytest.raises(overrides.OverrideError, match=re.escape("contains ' '")):
        getattr(overrides, apply)(bad / "micropython", tmp_path / "build_overrides", *args, **extra)
    assert not (tmp_path / "build_overrides").exists()


def test_a_relative_overrides_dir_still_writes_absolute_paths(overrides: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write_fake_micropython_tree(tmp_path / "micropython")
    monkeypatch.chdir(tmp_path)
    result = overrides.apply_unix_kbd_intr_override(Path("micropython"), Path("build_overrides"))
    variant_dir = Path(result["VARIANT_DIR"])
    assert variant_dir == tmp_path.resolve() / "build_overrides" / overrides.UNIX_KBD_INTR_DIR_NAME
    real_variant = tmp_path.resolve() / "micropython" / "ports" / "unix" / "variants" / "standard"
    assert f'#include "{real_variant / "mpconfigvariant.h"}"' in (variant_dir / "mpconfigvariant.h").read_text()
    assert (variant_dir / "mpconfigvariant.mk").read_text().startswith(f"include {real_variant / 'mpconfigvariant.mk'}\n")
    assert (variant_dir / "manifest.py").read_text() == f"include({str(real_variant / 'manifest.py')!r})\n"


# ---------------------------------------------------------------------------
# The mbedtls array-bounds suppression lives in the two generated build files, scoped to ctr_drbg.c,
# and no make command carries a global flag for it.
# ---------------------------------------------------------------------------


def test_the_mbedtls_suppression_is_one_files_rule_in_each_generated_build_file(overrides: ModuleType, tmp_path: Path) -> None:
    kbd = overrides.apply_unix_kbd_intr_override(_write_fake_micropython_tree(tmp_path / "unix"), tmp_path / "build_overrides")
    board = overrides.apply_lwip_connection_counts_override(_write_fake_lwip_tree(tmp_path / "rp2"), tmp_path / "build_overrides", _REAL_BOARD, _pinned())
    mk = (Path(kbd["VARIANT_DIR"]) / "mpconfigvariant.mk").read_text().splitlines()
    cmake = (Path(board["BOARD_DIR"]) / "mpconfigboard.cmake").read_text().splitlines()
    unix_rule = "$(BUILD)/lib/mbedtls/library/ctr_drbg.o: CFLAGS += -Wno-array-bounds"
    rp2_rule = 'set_source_files_properties("${MICROPY_DIR}/lib/mbedtls/library/ctr_drbg.c" PROPERTIES COMPILE_OPTIONS "-Wno-array-bounds")'
    for lines, rule in ((mk, unix_rule), (cmake, rp2_rule)):
        assert [line for line in lines if "array-bounds" in line and not line.startswith("#")] == [rule]
        reason = lines[lines.index(rule) - 1]
        assert reason.startswith("# ") and "ctr_drbg.c" in reason and "(agent, 2026-10-08)" in reason, reason


def test_no_make_command_carries_the_mbedtls_flag_globally(setup_toolchain: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Unix: the rig carries no CFLAGS_EXTRA at all, settrace only its own define; rp2: no CFLAGS_EXTRA.
    toolchain_dir = tmp_path / "toolchain"
    fake_mp_dir = _write_fake_micropython_tree(toolchain_dir / "micropython")
    _write_fake_modlwip_tree(_write_fake_lwip_tree(fake_mp_dir))
    recorded: list[list[str]] = []

    def fake_run(cmd: list[str], cwd: Path | None = None, **_kwargs: object) -> str:
        recorded.append(cmd)
        if cmd[0] == "make" and cwd is not None and cwd.name == "unix":
            build = next((arg.partition("=")[2] for arg in cmd if arg.startswith("BUILD=")), "build-standard")
            (cwd / build).mkdir(parents=True, exist_ok=True)
            (cwd / build / "micropython").write_text("")
        elif cmd[0] == "make" and cwd is not None:
            target = cwd / f"build-{_REAL_BOARD}" / "CMakeFiles" / "firmware.dir"
            target.mkdir(parents=True, exist_ok=True)
            (target.parent.parent / "firmware.uf2").write_bytes(b"")
        return "namespace(name='micropython')"

    monkeypatch.setattr(setup_toolchain, "run", fake_run)
    _stub_build_readbacks(setup_toolchain, monkeypatch)
    monkeypatch.setattr(setup_toolchain.micropython_overrides, "verify_lwip_macros_in_build", lambda *_a, **_k: {})
    setup_toolchain.build_unix_port(fake_mp_dir, toolchain_dir, jobs=2)
    setup_toolchain.build_unix_port(fake_mp_dir, toolchain_dir, jobs=2, settrace=True)
    setup_toolchain.build_firmware(fake_mp_dir, _REAL_BOARD, 2, toolchain_dir=toolchain_dir, lwip_macros=_pinned())
    makes = [cmd for cmd in recorded if cmd[0] == "make"]
    assert len(makes) == 3
    assert not [arg for cmd in makes for arg in cmd if "array-bounds" in arg]
    assert [[arg for arg in cmd if arg.startswith("CFLAGS_EXTRA=")] for cmd in makes] == [[], ["CFLAGS_EXTRA=-DMICROPY_PY_SYS_SETTRACE=1"], []]
    assert not hasattr(setup_toolchain, "_MBEDTLS_GCC14_ARRAY_BOUNDS_WORKAROUND")


# ---------------------------------------------------------------------------
# unix_kbd_intr's post-build proof: the build's own preprocessed unix_mphal.c (SPECIFICATION.md B.14.1).
# ---------------------------------------------------------------------------


def test_the_kbd_readback_accepts_the_deferred_path(overrides: ModuleType) -> None:
    overrides._check_unix_kbd_intr_pp(_pp_text(), Path("unix_mphal.pp"))


@pytest.mark.parametrize(
    ("text", "message"),
    [
        (_pp_text(sentinel=False), "sentinel absent: the variant redirect was not used"),
        (_pp_text(last_define="(1)"), r"the immediate nlr_raise\(\) path was compiled - the last MICROPY_ASYNC_KBD_INTR definition .* is '\(1\)'"),
        (_pp_text(handler=_IMMEDIATE_HANDLER), r"the immediate nlr_raise\(\) path was compiled - sighandler\(\)"),
        (_pp_text(handler="        exit(1);\n"), r"never mp_sched_keyboard_interrupt\(\)"),
        (_pp_text(with_handler=False), r"has no sighandler\(\): the pinned source changed - re-verify SPECIFICATION.md B.14.1"),
    ],
)
def test_the_kbd_readback_names_each_miss(overrides: ModuleType, text: str, message: str) -> None:
    # Each one alone: the redirect not reached, the immediate define winning, nlr_jump() compiled in,
    # the deferred call missing, the handler gone from the source.
    with pytest.raises(overrides.OverrideError, match=message):
        overrides._check_unix_kbd_intr_pp(text, Path("unix_mphal.pp"))


def test_the_kbd_readback_preprocesses_with_the_builds_own_variables_and_removes_the_pp(overrides: ModuleType, tmp_path: Path) -> None:
    unix_dir = tmp_path / "ports" / "unix"
    (unix_dir / "build-settrace").mkdir(parents=True)
    env, argv_log = _fake_make(tmp_path, pp=_pp_text())
    make_vars = {"VARIANT": "standard", "VARIANT_DIR": "/over/unix_kbd_intr_variant", "CFLAGS_EXTRA": "-DMICROPY_PY_SYS_SETTRACE=1", "BUILD": "build-settrace"}
    overrides.verify_unix_kbd_intr_in_build(unix_dir, make_vars, "build-settrace", env=env)
    assert argv_log.read_text().splitlines() == [*(f"{key}={value}" for key, value in make_vars.items()), "build-settrace/unix_mphal.pp"]
    assert not (unix_dir / "build-settrace" / "unix_mphal.pp").exists(), "the .pp must not outlive the check"


def test_the_kbd_readback_names_the_default_build_dir_itself(overrides: ModuleType, tmp_path: Path) -> None:
    # The rig's make line carries no BUILD=; the readback must still hit build-standard's own rule.
    unix_dir = tmp_path / "ports" / "unix"
    (unix_dir / "build-standard").mkdir(parents=True)
    env, argv_log = _fake_make(tmp_path, pp=_pp_text())
    overrides.verify_unix_kbd_intr_in_build(unix_dir, {"VARIANT": "standard", "VARIANT_DIR": "/v"}, "build-standard", env=env)
    assert argv_log.read_text().splitlines()[-2:] == ["BUILD=build-standard", "build-standard/unix_mphal.pp"]


def test_the_kbd_readback_removes_the_pp_even_when_the_check_fails(overrides: ModuleType, tmp_path: Path) -> None:
    unix_dir = tmp_path / "ports" / "unix"
    (unix_dir / "build-standard").mkdir(parents=True)
    env, _argv = _fake_make(tmp_path, pp=_pp_text(sentinel=False))
    with pytest.raises(overrides.OverrideError, match="sentinel absent"):
        overrides.verify_unix_kbd_intr_in_build(unix_dir, {"VARIANT": "standard"}, "build-standard", env=env)
    assert not (unix_dir / "build-standard" / "unix_mphal.pp").exists()


def test_a_stale_pp_from_an_interrupted_run_is_never_read_as_this_builds(overrides: ModuleType, tmp_path: Path) -> None:
    # A readback killed before its cleanup leaves a passing .pp behind; a make that then produces
    # nothing must fail the proof, not let the old text vouch for the new build.
    unix_dir = tmp_path / "ports" / "unix"
    (unix_dir / "build-standard").mkdir(parents=True)
    (unix_dir / "build-standard" / "unix_mphal.pp").write_text(_pp_text())
    env, _argv = _fake_make(tmp_path, pp=None)
    with pytest.raises(overrides.OverrideError, match=r"did not produce .*unix_mphal\.pp \(exit 0\)"):
        overrides.verify_unix_kbd_intr_in_build(unix_dir, {"VARIANT": "standard"}, "build-standard", env=env)


def test_the_kbd_readback_refuses_variables_naming_another_build(overrides: ModuleType, tmp_path: Path) -> None:
    env, argv_log = _fake_make(tmp_path)
    with pytest.raises(overrides.OverrideError, match="BUILD=build-settrace, not the build being proven"):
        overrides.verify_unix_kbd_intr_in_build(tmp_path, {"BUILD": "build-settrace"}, "build-standard", env=env)
    assert not argv_log.exists()


def test_the_kbd_readback_names_a_failed_or_missing_make(overrides: ModuleType, tmp_path: Path) -> None:
    unix_dir = tmp_path / "ports" / "unix"
    (unix_dir / "build-standard").mkdir(parents=True)
    with pytest.raises(overrides.OverrideError, match="no `make` on the build's PATH"):
        overrides.verify_unix_kbd_intr_in_build(unix_dir, {}, "build-standard", env={"PATH": str(tmp_path / "empty")})
    env, _argv = _fake_make(tmp_path, exit_code=2)
    with pytest.raises(overrides.OverrideError, match=r"\(exit 2\):\nPreProcess unix_mphal.c"):
        overrides.verify_unix_kbd_intr_in_build(unix_dir, {}, "build-standard", env=env)


def test_the_kbd_readback_names_a_hung_make(overrides: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    unix_dir = tmp_path / "ports" / "unix"
    (unix_dir / "build-standard").mkdir(parents=True)
    env, _argv = _fake_make(tmp_path, pp=_pp_text(), sleep_s=30)
    monkeypatch.setattr(overrides, "_PREPROCESS_TIMEOUT_S", 0.2)
    with pytest.raises(overrides.OverrideError, match=r"did not finish within 0\.2 s"):
        overrides.verify_unix_kbd_intr_in_build(unix_dir, {}, "build-standard", env=env)


# ---------------------------------------------------------------------------
# modlwip_eagain (SPECIFICATION.md B.14): the anchors, the patched copy and its CMake swap.
# ---------------------------------------------------------------------------


def test_the_modlwip_anchors_hold_in_the_real_pinned_source(overrides: ModuleType, micropython_dir: Path) -> None:
    if not (micropython_dir / "extmod" / "modlwip.c").is_file():
        pytest.fail(f"no real toolchain checkout at {micropython_dir} - build it with `toolchain/setup_toolchain.py setup` (scripts/test.sh does)")
    overrides.verify_modlwip_eagain_anchor(micropython_dir)


@pytest.mark.parametrize("dropped", _EVERY_MODLWIP_ANCHOR)
def test_every_modlwip_anchor_is_load_bearing(overrides: ModuleType, tmp_path: Path, dropped: str) -> None:
    _write_fake_modlwip_tree(tmp_path, drop=dropped)
    with pytest.raises(overrides.OverrideError, match="micropython issue 19704"):
        overrides.verify_modlwip_eagain_anchor(tmp_path)


def test_the_modlwip_parametrization_covers_every_anchor_the_code_checks(overrides: ModuleType) -> None:
    in_code = {*overrides._MODLWIP_SOURCE_ANCHORS, *(anchor for _path, anchors in overrides._MODLWIP_RP2_WIRING for anchor in anchors)}
    assert set(_EVERY_MODLWIP_ANCHOR) == in_code
    assert len(_EVERY_MODLWIP_ANCHOR) == len(in_code)
    # The loop's own text holds the insertion point, so "exactly once" puts it inside the loop.
    assert overrides._MODLWIP_INSERT_AFTER in overrides._MODLWIP_ERR_MEM_LOOP


def test_a_repeated_retry_loop_is_refused(overrides: ModuleType, tmp_path: Path) -> None:
    source = _write_fake_modlwip_tree(tmp_path) / "extmod" / "modlwip.c"
    source.write_text(source.read_text() + _FAKE_MODLWIP_LOOP)
    with pytest.raises(overrides.OverrideError, match="found 2 times, not once"):
        overrides.verify_modlwip_eagain_anchor(tmp_path)


def test_the_cmake_wiring_out_of_order_is_refused(overrides: ModuleType, tmp_path: Path) -> None:
    # usermod.cmake included before extmod.cmake set the list: the swap would find nothing to swap.
    _write_fake_modlwip_tree(tmp_path)
    cmake = tmp_path / "ports" / "rp2" / "CMakeLists.txt"
    cmake.write_text("include(${MICROPY_DIR}/py/usermod.cmake)\n" + cmake.read_text().replace("include(${MICROPY_DIR}/py/usermod.cmake)", "", 1))
    with pytest.raises(overrides.OverrideError, match="is no longer after the anchor before it"):
        overrides.verify_modlwip_eagain_anchor(tmp_path)


def test_modlwip_c_outside_the_extmod_source_list_is_refused(overrides: ModuleType, tmp_path: Path) -> None:
    _write_fake_modlwip_tree(tmp_path)
    (tmp_path / "extmod" / "extmod.cmake").write_text("set(MICROPY_SOURCE_EXTMOD\n    ${MICROPY_EXTMOD_DIR}/modnetwork.c\n)\n    ${MICROPY_EXTMOD_DIR}/modlwip.c\n")
    with pytest.raises(overrides.OverrideError, match=r"no longer inside set\(MICROPY_SOURCE_EXTMOD"):
        overrides.verify_modlwip_eagain_anchor(tmp_path)


def test_apply_modlwip_returns_the_user_c_modules_directory(overrides: ModuleType, tmp_path: Path) -> None:
    fake = _write_fake_modlwip_tree(tmp_path / "micropython")
    result = overrides.apply_modlwip_eagain_override(fake, tmp_path / "build_overrides")
    assert result == {"USER_C_MODULES": str(tmp_path.resolve() / "build_overrides" / overrides.MODLWIP_OVERRIDE_DIR_NAME)}


def test_apply_modlwip_never_writes_inside_the_checkout(overrides: ModuleType, tmp_path: Path) -> None:
    fake = _write_fake_modlwip_tree(tmp_path / "micropython")
    before = _tree_state(fake)
    overrides.apply_modlwip_eagain_override(fake, tmp_path / "build_overrides")
    assert _tree_state(fake) == before


def test_the_copy_differs_from_the_pinned_source_by_exactly_the_include_and_the_eagain_block(overrides: ModuleType, tmp_path: Path) -> None:
    fake = _write_fake_modlwip_tree(tmp_path / "micropython")
    copy_dir = Path(overrides.apply_modlwip_eagain_override(fake, tmp_path / "build_overrides")["USER_C_MODULES"])
    lines = (copy_dir / "modlwip.c").read_text().split("\n", 2)
    header, copy = lines[:2], lines[2]
    assert header == ["// Generated by toolchain/micropython_overrides.py from extmod/modlwip.c of MicroPython 1.29.0 -", "// SPECIFICATION.md B.14. Do not edit."]
    diff = [line for line in difflib.ndiff((fake / "extmod" / "modlwip.c").read_text().splitlines(), copy.splitlines()) if line[:2] in {"- ", "+ "}]
    assert diff == [
        f"- {_FAKE_MODLWIP_INCLUDE}",
        '+ #include "extmod/modnetwork.h"',
        "+         if (socket->timeout == 0) {",
        "+             // Non-blocking: hand the wait back to the caller rather than sleeping inside this call.",
        "+             MICROPY_PY_LWIP_EXIT",
        "+             *_errno = MP_EAGAIN;",
        "+             return MP_STREAM_ERROR;",
        "+         }",
    ]


def test_the_eagain_block_sits_after_the_output_check_and_before_the_sleep(overrides: ModuleType, tmp_path: Path) -> None:
    # After tcp_output()'s ERR_OK check (so a failed output still breaks out as before), before the
    # loop releases the lock and sleeps 50 ms - the wait this override hands back to the caller.
    fake = _write_fake_modlwip_tree(tmp_path / "micropython")
    copy = (Path(overrides.apply_modlwip_eagain_override(fake, tmp_path / "build_overrides")["USER_C_MODULES"]) / "modlwip.c").read_text()
    block = copy.index("        if (socket->timeout == 0) {\n")
    assert copy.index(_FAKE_MODLWIP_INSERT_AFTER) + len(_FAKE_MODLWIP_INSERT_AFTER) == block
    assert block < copy.index("        MICROPY_PY_LWIP_EXIT\n        mp_hal_delay_ms(50);")


def test_the_generated_micropython_cmake_is_pinned_byte_for_byte(overrides: ModuleType, tmp_path: Path) -> None:
    fake = _write_fake_modlwip_tree(tmp_path / "micropython")
    copy_dir = Path(overrides.apply_modlwip_eagain_override(fake, tmp_path / "build_overrides")["USER_C_MODULES"])
    assert (copy_dir / "micropython.cmake").read_text() == (
        "# Generated by toolchain/micropython_overrides.py - SPECIFICATION.md B.14.\n"
        'list(FIND MICROPY_SOURCE_EXTMOD "${MICROPY_EXTMOD_DIR}/modlwip.c" _sensors_modlwip_index)\n'
        "if(_sensors_modlwip_index EQUAL -1)\n"
        '    message(FATAL_ERROR "modlwip_eagain: extmod/modlwip.c is not in MICROPY_SOURCE_EXTMOD - re-verify toolchain/micropython_overrides.py (SPECIFICATION.md B.14)")\n'
        "endif()\n"
        "list(REMOVE_AT MICROPY_SOURCE_EXTMOD ${_sensors_modlwip_index})\n"
        f'list(APPEND MICROPY_SOURCE_EXTMOD "{copy_dir / "modlwip.c"}")\n'
    )


def test_apply_modlwip_is_idempotent(overrides: ModuleType, tmp_path: Path) -> None:
    fake = _write_fake_modlwip_tree(tmp_path / "micropython")
    first = overrides.apply_modlwip_eagain_override(fake, tmp_path / "build_overrides")
    written = {path.name: path.read_bytes() for path in Path(first["USER_C_MODULES"]).iterdir()}
    assert overrides.apply_modlwip_eagain_override(fake, tmp_path / "build_overrides") == first
    assert {path.name: path.read_bytes() for path in Path(first["USER_C_MODULES"]).iterdir()} == written


@pytest.mark.parametrize("dropped", [_FAKE_MODLWIP_LOOP, "include(${USER_C_MODULE_PATH})", "#define MICROPY_VERSION_MINOR"])
def test_apply_modlwip_writes_nothing_when_an_anchor_or_the_version_is_missing(overrides: ModuleType, tmp_path: Path, dropped: str) -> None:
    fake = _write_fake_modlwip_tree(tmp_path / "micropython", drop=dropped)
    mpconfig = fake / "py" / "mpconfig.h"
    mpconfig.write_text("".join(line for line in mpconfig.read_text().splitlines(keepends=True) if not line.startswith(dropped)))
    with pytest.raises(overrides.OverrideError):
        overrides.apply_modlwip_eagain_override(fake, tmp_path / "build_overrides")
    assert not (tmp_path / "build_overrides").exists()


def test_build_firmware_applies_and_proves_both_rp2_overrides(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, setup_toolchain: ModuleType) -> None:
    # The make line carries the lwIP board redirect and modlwip's USER_C_MODULES; each readback runs
    # on the real build dir, modlwip's on the copy the override wrote.
    toolchain_dir = tmp_path / "toolchain"
    fake_mp_dir = _write_fake_modlwip_tree(_write_fake_lwip_tree(toolchain_dir / "micropython"))
    recorded: list[list[str]] = []

    def fake_run(cmd: list[str], cwd: Path | None = None, **_kwargs: object) -> str:
        recorded.append(cmd)
        build_dir = fake_mp_dir / "ports" / "rp2" / f"build-{_REAL_BOARD}"
        build_dir.mkdir(parents=True, exist_ok=True)
        (build_dir / "firmware.uf2").write_bytes(b"")
        return ""

    monkeypatch.setattr(setup_toolchain, "run", fake_run)
    calls = _stub_build_readbacks(setup_toolchain, monkeypatch)
    monkeypatch.setattr(setup_toolchain.micropython_overrides, "verify_lwip_macros_in_build", lambda *_a, **_k: {})
    setup_toolchain.build_firmware(fake_mp_dir, _REAL_BOARD, 2, toolchain_dir=toolchain_dir, lwip_macros=_pinned())
    modlwip_dir = toolchain_dir.resolve() / "build_overrides" / "modlwip_eagain"
    (make_cmd,) = recorded
    assert f"USER_C_MODULES={modlwip_dir}" in make_cmd
    build_dir = fake_mp_dir / "ports" / "rp2" / f"build-{_REAL_BOARD}"
    assert ("verify_modlwip_eagain_in_build", (build_dir, fake_mp_dir, modlwip_dir / "modlwip.c")) in calls
    assert ("verify_tick_offset_in_build", (build_dir, False)) in calls, "every release build proves it carries no tick offset"


# ---------------------------------------------------------------------------
# modlwip_eagain's post-build proof, over CMake's real firmware layout (pico-sdk 2.3.0 names objects
# `<source>.o`; an outside source's object mirrors its absolute path under the target dir).
# ---------------------------------------------------------------------------


def test_modlwip_readback_passes_on_cmakes_real_firmware_layout(overrides: ModuleType, tmp_path: Path) -> None:
    micropython_dir, _original, copy_path = _modlwip_paths(tmp_path)
    build_dir = _fake_firmware_build(tmp_path, (copy_path,))
    overrides.verify_modlwip_eagain_in_build(build_dir, micropython_dir, copy_path)


def test_modlwip_readback_refuses_a_build_that_compiled_the_original(overrides: ModuleType, tmp_path: Path) -> None:
    micropython_dir, original, copy_path = _modlwip_paths(tmp_path)
    build_dir = _fake_firmware_build(tmp_path, (original,))
    with pytest.raises(overrides.OverrideError, match="does not compile the patched copy"):
        overrides.verify_modlwip_eagain_in_build(build_dir, micropython_dir, copy_path)


def test_modlwip_readback_refuses_a_build_that_compiled_both(overrides: ModuleType, tmp_path: Path) -> None:
    micropython_dir, original, copy_path = _modlwip_paths(tmp_path)
    build_dir = _fake_firmware_build(tmp_path, (copy_path, original))
    with pytest.raises(overrides.OverrideError, match="still compiles the original"):
        overrides.verify_modlwip_eagain_in_build(build_dir, micropython_dir, copy_path)


def test_modlwip_readback_names_a_changed_cmake_layout(overrides: ModuleType, tmp_path: Path) -> None:
    micropython_dir, _original, copy_path = _modlwip_paths(tmp_path)
    with pytest.raises(overrides.OverrideError, match="layout changed"):
        overrides.verify_modlwip_eagain_in_build(tmp_path / "build-RPI_PICO_W", micropython_dir, copy_path)


def test_modlwip_readback_refuses_a_missing_or_empty_object(overrides: ModuleType, tmp_path: Path) -> None:
    micropython_dir, _original, copy_path = _modlwip_paths(tmp_path)
    empty = _fake_firmware_build(tmp_path / "empty", (copy_path,), empty=True)
    with pytest.raises(overrides.OverrideError, match="empty"):
        overrides.verify_modlwip_eagain_in_build(empty, micropython_dir, copy_path)
    missing = _fake_firmware_build(tmp_path / "missing", (copy_path,))
    next((missing / "CMakeFiles" / "firmware.dir").rglob("modlwip.c.o")).unlink()
    with pytest.raises(overrides.OverrideError, match=r"expected exactly one modlwip\.c\.o"):
        overrides.verify_modlwip_eagain_in_build(missing, micropython_dir, copy_path)


# ---------------------------------------------------------------------------
# unix_lwip_host (SPECIFICATION.md B.14): the third Unix build flavour, the patched modlwip.c over loopback lwIP.
# ---------------------------------------------------------------------------


def test_the_host_builds_own_flags_reach_modlwip_alone_and_never_the_test_rig(overrides: ModuleType, micropython_dir: Path, tmp_path: Path) -> None:
    # Each found by the first real build under -Werror: one object, one flag, `private` so the shared
    # headers that object's build triggers never inherit it - and the SIGINT-only rig carries none.
    if not (micropython_dir / "lib" / "lwip" / "src" / "core" / "tcp_out.c").is_file():
        pytest.fail(f"no real toolchain checkout with lwIP at {micropython_dir} - build it with `toolchain/setup_toolchain.py setup` (scripts/test.sh does)")
    host = overrides.apply_unix_lwip_host_override(micropython_dir, tmp_path / "build_overrides", _pinned())
    rig = overrides.apply_unix_kbd_intr_override(micropython_dir, tmp_path / "build_overrides")
    host_flags = [line for line in (Path(host["VARIANT_DIR"]) / "mpconfigvariant.mk").read_text().splitlines() if "CFLAGS +=" in line]
    rig_flags = [line for line in (Path(rig["VARIANT_DIR"]) / "mpconfigvariant.mk").read_text().splitlines() if "CFLAGS +=" in line]
    mbedtls = "$(BUILD)/lib/mbedtls/library/ctr_drbg.o: CFLAGS += -Wno-array-bounds"
    assert host_flags == [mbedtls, "$(BUILD)/extmod/modlwip.o: private CFLAGS += -Wno-sign-compare", "$(BUILD)/extmod/modlwip.o: private CFLAGS += -DSOMAXCONN=2"]
    assert rig_flags == [mbedtls]


def test_the_host_anchors_hold_in_the_real_pinned_source(overrides: ModuleType, micropython_dir: Path, tmp_path: Path) -> None:
    if not (micropython_dir / _FAKE_TCP_OUT).is_file():
        pytest.fail(f"no real toolchain checkout with lwIP at {micropython_dir} - build it with `toolchain/setup_toolchain.py setup` (scripts/test.sh does)")
    overrides.apply_unix_lwip_host_override(micropython_dir, tmp_path / "build_overrides", _pinned())


@pytest.mark.parametrize("dropped", _EVERY_LWIP_HOST_ANCHOR)
def test_every_host_anchor_is_load_bearing(overrides: ModuleType, tmp_path: Path, dropped: str) -> None:
    fake = _write_fake_lwip_host_tree(tmp_path / "micropython", drop=dropped)
    with pytest.raises(overrides.OverrideError):
        overrides.apply_unix_lwip_host_override(fake, tmp_path / "build_overrides", _pinned())
    assert not (tmp_path / "build_overrides").exists()


def test_the_host_parametrization_covers_every_anchor_the_code_checks(overrides: ModuleType) -> None:
    in_code = {
        overrides._UNIX_KBD_INTR_ANCHOR, *overrides._MODLWIP_SOURCE_ANCHORS, overrides._LWIP_HOST_TCP_OUT,
        *(anchor for _path, anchors in overrides._LWIP_HOST_ANCHORS for anchor in anchors),
    }
    assert set(_EVERY_LWIP_HOST_ANCHOR) == in_code
    assert len(_EVERY_LWIP_HOST_ANCHOR) == len(in_code)


def test_a_host_anchor_miss_names_its_file_and_a_missing_lwip_names_the_fetch(overrides: ModuleType, tmp_path: Path) -> None:
    fake = _write_fake_lwip_host_tree(tmp_path / "a", drop="#ifndef MICROPY_INTERNAL_EVENT_HOOK\n")
    with pytest.raises(overrides.OverrideError, match=r"py/mphal\.h is gone - the Unix port's lwIP wiring changed upstream"):
        overrides.apply_unix_lwip_host_override(fake, tmp_path / "build_overrides", _pinned())
    fake = _write_fake_lwip_host_tree(tmp_path / "b", drop=_FAKE_TCP_OUT)
    with pytest.raises(overrides.OverrideError, match=r"make submodules MICROPY_PY_LWIP=1"):
        overrides.apply_unix_lwip_host_override(fake, tmp_path / "build_overrides", _pinned())


def test_apply_host_returns_its_build_flavours_make_variables(overrides: ModuleType, tmp_path: Path) -> None:
    fake = _write_fake_lwip_host_tree(tmp_path / "micropython")
    assert overrides.apply_unix_lwip_host_override(fake, tmp_path / "build_overrides", _pinned()) == {
        "VARIANT": "standard",
        "VARIANT_DIR": str(tmp_path.resolve() / "build_overrides" / overrides.UNIX_LWIP_HOST_DIR_NAME),
        "BUILD": "build-lwip",
        "MICROPY_PY_LWIP": "1",
        "MICROPY_PY_LWIP_LOOPBACK": "1",
        "MICROPY_PY_SOCKET": "0",
    }


def test_apply_host_never_writes_inside_the_checkout(overrides: ModuleType, tmp_path: Path) -> None:
    fake = _write_fake_lwip_host_tree(tmp_path / "micropython")
    before = _tree_state(fake)
    overrides.apply_unix_lwip_host_override(fake, tmp_path / "build_overrides", _pinned())
    assert _tree_state(fake) == before


def test_apply_host_refuses_an_incoherent_lwip_table_before_writing(overrides: ModuleType, tmp_path: Path) -> None:
    fake = _write_fake_lwip_host_tree(tmp_path / "micropython")
    with pytest.raises(overrides.OverrideError, match="not a coherent set"):
        overrides.apply_unix_lwip_host_override(fake, tmp_path / "build_overrides", {**_pinned(), "MEMP_NUM_TCP_SEG": 8})
    assert not (tmp_path / "build_overrides").exists()


def test_the_host_variant_relays_the_standard_variant_and_swaps_in_the_patched_copy(overrides: ModuleType, tmp_path: Path) -> None:
    fake = _write_fake_lwip_host_tree(tmp_path / "micropython")
    variant = Path(overrides.apply_unix_lwip_host_override(fake, tmp_path / "build_overrides", _pinned())["VARIANT_DIR"])
    rp2_copy = Path(overrides.apply_modlwip_eagain_override(fake, tmp_path / "build_overrides")["USER_C_MODULES"]) / "modlwip.c"
    real = fake.resolve() / "ports" / "unix" / "variants" / "standard"
    assert sorted(str(path.relative_to(variant)) for path in variant.rglob("*") if path.is_file()) == [
        "lwip_host_port.c", "lwip_inc/arch/cc.h", "lwip_inc/arch/sys_arch.h", "lwip_inc/lwipopts.h", "manifest.py",
        "mpconfigvariant.h", "mpconfigvariant.mk", "src/extmod/modlwip.c",
    ]
    assert (variant / "src" / "extmod" / "modlwip.c").read_bytes() == rp2_copy.read_bytes(), "the host build compiles the firmware's own patched copy"
    header = (variant / "mpconfigvariant.h").read_text()
    assert header == overrides._unix_kbd_intr_header(real) + "void mp_lwip_host_poll(void);\n#define MICROPY_INTERNAL_EVENT_HOOK mp_lwip_host_poll()\n"
    mk = (variant / "mpconfigvariant.mk").read_text().splitlines()
    # vpath before py/mkrules.mk's own `vpath %.c . $(TOP)`: make searches the copy's directory first.
    assert mk[:3] == [f"include {real / 'mpconfigvariant.mk'}", f"INC += -I{variant / 'lwip_inc'}", f"vpath extmod/modlwip.c {variant / 'src'}"]
    assert (variant / "manifest.py").read_text() == f"include({str(real / 'manifest.py')!r})\n"


def test_the_host_lwipopts_are_rp2s_with_the_hosts_alignment_and_the_pinned_table(overrides: ModuleType, tmp_path: Path) -> None:
    fake = _write_fake_lwip_host_tree(tmp_path / "micropython")
    variant = Path(overrides.apply_unix_lwip_host_override(fake, tmp_path / "build_overrides", _pinned())["VARIANT_DIR"])
    text = (variant / "lwip_inc" / "lwipopts.h").read_text()
    common = text.index('#include "extmod/lwip-include/lwipopts_common.h"')
    assert all(text.index(setting) < common for setting in _FAKE_RP2_LWIP_SETTINGS)
    assert "#define LWIP_RAND() ((u32_t)rand())" in text and "#include <stdlib.h>" in text
    # A literal, since lwIP may test MEM_ALIGNMENT in #if; the common block's 4 is undone first.
    assert common < text.index(f"#undef MEM_ALIGNMENT\n#define MEM_ALIGNMENT {struct.calcsize('P')}\n")
    assert common < text.index(overrides._lwip_redefines(_pinned()))


def test_ipv6_fragment_headers_are_copied_on_the_host_and_never_in_the_firmware(overrides: ModuleType, tmp_path: Path) -> None:
    # struct ip6_reass_helper outgrows IP6_FRAG_HLEN where pointers are 8 bytes, and ip6_reass_tmr()
    # asserts on it each second (lib/lwip/src/core/ipv6/ip6_frag.c:117-120); rp2 is 32-bit.
    fake = _write_fake_lwip_host_tree(tmp_path / "micropython")
    host = Path(overrides.apply_unix_lwip_host_override(fake, tmp_path / "build_overrides", _pinned())["VARIANT_DIR"]) / "lwip_inc" / "lwipopts.h"
    board = Path(overrides.apply_lwip_connection_counts_override(_write_fake_lwip_tree(tmp_path / "rp2"), tmp_path / "rp2_overrides", _REAL_BOARD, _pinned())["BOARD_DIR"])
    lines = host.read_text().splitlines()
    define = lines.index("#define IPV6_FRAG_COPYHEADER 1")
    assert lines[define - 1].startswith("// ") and "ip6_frag.c" in lines[define - 1], "the define carries its reason"
    assert not [path for path in board.rglob("*") if path.is_file() and "IPV6_FRAG_COPYHEADER" in path.read_text()]


def test_the_host_port_layer_runs_lwip_from_the_event_hook_and_asserts_loudly(overrides: ModuleType, tmp_path: Path) -> None:
    fake = _write_fake_lwip_host_tree(tmp_path / "micropython")
    variant = Path(overrides.apply_unix_lwip_host_override(fake, tmp_path / "build_overrides", _pinned())["VARIANT_DIR"])
    port = (variant / "lwip_host_port.c").read_text()
    for needed in ("u32_t sys_now(void) {\n    return (u32_t)mp_hal_ticks_ms();\n}", "int mp_mod_network_prefer_dns_use_ip_version = 4;", "    if (polling) {\n        return;\n    }\n    polling = 1;\n    netif_poll_all();\n    sys_check_timeouts();\n    polling = 0;"):
        assert needed in port, needed
    assert port.index("#if MICROPY_PY_LWIP") < port.index("u32_t sys_now(void)") < port.rindex("#endif")
    cc = (variant / "lwip_inc" / "arch" / "cc.h").read_text()
    assert "abort();" in cc.split("#define LWIP_PLATFORM_ASSERT(x)")[1].split("\n")[0], "rp2's assert is a no-op; the host instrument must stop"


def test_the_host_readback_accepts_the_patched_copy_and_modlwip_as_socket(overrides: ModuleType, tmp_path: Path) -> None:
    build_dir, micropython_dir, binary = _fake_lwip_host_build(tmp_path)
    overrides.verify_unix_lwip_host_in_build(build_dir, micropython_dir, binary, env={"PATH": os.environ["PATH"]})
    # lwip.reset() starts lwIP's cyclic timers; sleeping 2.5 s runs them through the event hook, past
    # two 1 s IPv6 reassembly ticks, and lwip.callback() runs them once more directly.
    assert (tmp_path / "probe-argv.txt").read_text().splitlines() == [
        "-c", "import lwip, socket, time; print(socket is lwip); lwip.reset(); time.sleep_ms(2500); lwip.callback(); print('lwip timers ok')",
    ]


@pytest.mark.parametrize(
    ("source", "block", "stdout", "exit_code", "message"),
    [
        ("../../extmod/modlwip.c", "kept", _PROBE_OK, 0, "names the original"),
        ("/elsewhere/src/extmod/modlwip.c", "kept", _PROBE_OK, 0, "not the patched copy"),
        (None, "dropped", _PROBE_OK, 0, "not the patched copy"),
        (None, "kept", "False\nlwip timers ok", 0, r"socket module is not modlwip - the probe printed 'False\\nlwip timers ok' \(exit 0\)"),
        (None, "kept", "True", 0, r"did not survive lwIP's own timers - the probe printed 'True' \(exit 0\)"),
        (None, "kept", _PROBE_OK, 1, r"did not survive lwIP's own timers - .*\(exit 1\)"),
    ],
)
def test_the_host_readback_names_each_miss(overrides: ModuleType, tmp_path: Path, source: str | None, block: str, stdout: str, exit_code: int, message: str) -> None:
    # The original compiled, some other file compiled, the copy without its block, `socket` not
    # modlwip, the timers never reaching their end, a non-zero exit after it.
    build_dir, micropython_dir, binary = _fake_lwip_host_build(tmp_path, source=source, block=block, stdout=stdout, exit_code=exit_code)
    with pytest.raises(overrides.OverrideError, match=message):
        overrides.verify_unix_lwip_host_in_build(build_dir, micropython_dir, binary, env={"PATH": os.environ["PATH"]})


def test_the_host_readback_shows_an_lwip_assertion_that_stopped_the_binary(overrides: ModuleType, tmp_path: Path) -> None:
    # The 64-bit failure as the first real build met it: one 1 s timer tick after lwip.reset(),
    # ip6_reass_tmr() asserts and the loud host LWIP_PLATFORM_ASSERT aborts the process.
    assertion = "lwIP assertion failed: sizeof(struct ip6_reass_helper) <= IP6_FRAG_HLEN, set IPV6_FRAG_COPYHEADER to 1 (../../lib/lwip/src/core/ipv6/ip6_frag.c:118)\n"
    build_dir, micropython_dir, binary = _fake_lwip_host_build(tmp_path, stdout="True", exit_code=134, stderr=assertion)
    with pytest.raises(overrides.OverrideError, match=r"did not survive lwIP's own timers - the probe printed 'True' \(exit 134\): lwIP assertion failed: sizeof\(struct ip6_reass_helper\)"):
        overrides.verify_unix_lwip_host_in_build(build_dir, micropython_dir, binary, env={"PATH": os.environ["PATH"]})


def test_the_host_readback_names_an_uncompiled_modlwip_a_missing_binary_and_a_hung_one(overrides: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    build_dir, micropython_dir, binary = _fake_lwip_host_build(tmp_path / "hung", sleep_s=30)
    monkeypatch.setattr(overrides, "_PREPROCESS_TIMEOUT_S", 0.2)
    with pytest.raises(overrides.OverrideError, match=r"did not answer the runtime probe within 0\.2 s"):
        overrides.verify_unix_lwip_host_in_build(build_dir, micropython_dir, binary, env={"PATH": os.environ["PATH"]})
    binary.unlink()
    with pytest.raises(overrides.OverrideError, match="cannot run"):
        overrides.verify_unix_lwip_host_in_build(build_dir, micropython_dir, binary, env={"PATH": os.environ["PATH"]})
    (build_dir / "extmod" / "modlwip.P").unlink()
    with pytest.raises(overrides.OverrideError, match="was not compiled into this build"):
        overrides.verify_unix_lwip_host_in_build(build_dir, micropython_dir, binary, env={"PATH": os.environ["PATH"]})


def test_build_unix_lwip_port_builds_the_host_flavour_and_proves_it(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, setup_toolchain: ModuleType) -> None:
    toolchain_dir = tmp_path / "toolchain"
    fake_mp_dir = _write_fake_lwip_host_tree(toolchain_dir / "micropython")
    unix_dir = fake_mp_dir / "ports" / "unix"
    recorded: list[list[str]] = []

    def fake_run(cmd: list[str], cwd: Path | None = None, **_kwargs: object) -> str:
        recorded.append(cmd)
        if cmd[0] == "make":
            (unix_dir / "build-lwip").mkdir(parents=True, exist_ok=True)
            (unix_dir / "build-lwip" / "micropython").write_text("")
        return "namespace(name='micropython')"

    monkeypatch.setattr(setup_toolchain, "run", fake_run)
    calls = _stub_build_readbacks(setup_toolchain, monkeypatch)
    binary = setup_toolchain.build_unix_lwip_port(fake_mp_dir, toolchain_dir, 2)
    assert binary == unix_dir / "build-lwip" / "micropython"
    make_vars = [arg for arg in recorded[0] if "=" in arg]
    assert make_vars == ["VARIANT=standard", f"VARIANT_DIR={toolchain_dir.resolve() / 'build_overrides' / 'unix_lwip_host_variant'}", "BUILD=build-lwip", "MICROPY_PY_LWIP=1", "MICROPY_PY_LWIP_LOOPBACK=1", "MICROPY_PY_SOCKET=0"]
    assert [name for name, _args in calls] == ["verify_unix_kbd_intr_in_build", "verify_unix_lwip_host_in_build"], "the SIGINT proof, then the host proof"
    assert calls[1][1][:3] == (unix_dir / "build-lwip", fake_mp_dir, binary)


# ---------------------------------------------------------------------------
# tick_offset_test (SPECIFICATION.md B.14): the test-only image whose ticks_ms() wraps 15 minutes after boot.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("board", ["RPI_PICO_W", "RPI_PICO"])
def test_tick_offset_builds_in_its_own_per_board_directory(overrides: ModuleType, tmp_path: Path, board: str) -> None:
    # Never a release build's directory, and never another board's: each keeps its own CMake cache.
    fake = _write_fake_mphalport(tmp_path / "micropython")
    assert overrides.apply_tick_offset_override(fake, tmp_path / "build_overrides", board=board) == {"BUILD": f"build-{board}-tickoffset"}


def test_the_tick_anchor_holds_in_the_real_pinned_source(overrides: ModuleType, micropython_dir: Path) -> None:
    if not (micropython_dir / "ports" / "rp2" / "mphalport.h").is_file():
        pytest.fail(f"no real toolchain checkout at {micropython_dir} - build it with `toolchain/setup_toolchain.py setup` (scripts/test.sh does)")
    assert overrides.verify_tick_offset_anchor(micropython_dir) == micropython_dir / "ports" / "rp2" / "mphalport.h"


def test_the_offset_wraps_both_counts_fifteen_minutes_after_boot(overrides: ModuleType) -> None:
    # ticks_ms() wraps at 2**30, the raw millisecond count at 2**32: one offset reaches both at once.
    assert overrides.TICK_OFFSET_MS == 2**32 - 900_000
    assert overrides.TICK_OFFSET_MS % 2**30 == 2**30 - 900_000


def test_the_tick_copy_differs_from_the_pinned_header_by_exactly_the_return_line(overrides: ModuleType, tmp_path: Path) -> None:
    fake = _write_fake_mphalport(tmp_path / "micropython")
    overrides.apply_tick_offset_override(fake, tmp_path / "build_overrides", board=_REAL_BOARD)
    lines = (tmp_path / "build_overrides" / overrides.TICK_OFFSET_DIR_NAME / "mphalport.h").read_text().split("\n", 4)
    prefix, body = lines[:4], lines[4]
    assert prefix[2:] == [f"#define MICROPY_SENSORS_TICK_OFFSET_MS ({2**32 - 900_000}u)", f"#define {overrides.TICK_OFFSET_SENTINEL} 1"]
    diff = [line for line in difflib.ndiff((fake / "ports" / "rp2" / "mphalport.h").read_text().splitlines(), body.splitlines()) if line[:2] in {"- ", "+ "}]
    # 32-bit unsigned: the sum wraps where the hardware count would, and the timer is never written.
    assert diff == ["-     return to_ms_since_boot(get_absolute_time());", "+     return (mp_uint_t)(to_ms_since_boot(get_absolute_time()) + MICROPY_SENSORS_TICK_OFFSET_MS);"]


def test_apply_tick_offset_never_writes_inside_the_checkout(overrides: ModuleType, tmp_path: Path) -> None:
    fake = _write_fake_mphalport(tmp_path / "micropython")
    before = _tree_state(fake)
    overrides.apply_tick_offset_override(fake, tmp_path / "build_overrides", board=_REAL_BOARD)
    assert _tree_state(fake) == before


@pytest.mark.parametrize("body", ["static inline mp_uint_t mp_hal_ticks_ms(void) {\n    return time_us_32() / 1000;\n}\n", _FAKE_TICKS_MS + _FAKE_TICKS_MS])
def test_a_moved_or_repeated_tick_anchor_is_refused_before_writing(overrides: ModuleType, tmp_path: Path, body: str) -> None:
    fake = _write_fake_mphalport(tmp_path / "micropython", body)
    with pytest.raises(overrides.OverrideError, match=r"ports/rp2/mphalport\.h - re-derive this override's anchor and its replacement \(SPECIFICATION\.md B\.14\)"):
        overrides.apply_tick_offset_override(fake, tmp_path / "build_overrides", board=_REAL_BOARD)
    assert not (tmp_path / "build_overrides").exists()


def test_the_tick_readback_reads_the_sentinel_through_the_builds_own_mphal(overrides: ModuleType, tmp_path: Path) -> None:
    applied, compiler, argv_log = _fake_build(tmp_path / "applied", stdout="TICKPROBE = 1\n")
    absent, compiler_2, _argv = _fake_build(tmp_path / "absent", stdout=f"TICKPROBE = {overrides.TICK_OFFSET_SENTINEL}\n")
    for build_dir, cc in ((applied, compiler), (absent, compiler_2)):
        (build_dir / "CMakeFiles" / "firmware.dir" / "flags.make").write_text(f"# compile C with {cc}\nC_DEFINES = -DPICO_BOARD=pico_w\nC_INCLUDES = -I/tick -I/real\nC_FLAGS = -O2\n")
    assert overrides.tick_offset_in_build(applied) is True
    assert overrides.tick_offset_in_build(absent) is False
    assert "-I/tick -I/real" in argv_log.read_text(), "the build's own include order decides which mphalport.h is found"


def test_the_tick_readback_refuses_an_answer_it_cannot_read(overrides: ModuleType, tmp_path: Path) -> None:
    build_dir, compiler, _argv = _fake_build(tmp_path, stdout="TICKPROBE = 2\n")
    (build_dir / "CMakeFiles" / "firmware.dir" / "flags.make").write_text(f"# compile C with {compiler}\nC_DEFINES = \nC_INCLUDES = \nC_FLAGS = \n")
    with pytest.raises(overrides.OverrideError, match=r"gave \['2'\], neither 1 nor absent"):
        overrides.tick_offset_in_build(build_dir)


@pytest.mark.parametrize(("carries", "expected", "message"), [("1", "release", "a release build carries the tick-offset test override"), ("absent", "test", "never reached the generated mphalport.h")])
def test_a_build_that_is_not_what_it_was_asked_to_be_is_refused(overrides: ModuleType, tmp_path: Path, carries: str, expected: str, message: str) -> None:
    value = "1" if carries == "1" else overrides.TICK_OFFSET_SENTINEL
    build_dir, compiler, _argv = _fake_build(tmp_path, stdout=f"TICKPROBE = {value}\n")
    (build_dir / "CMakeFiles" / "firmware.dir" / "flags.make").write_text(f"# compile C with {compiler}\nC_DEFINES = \nC_INCLUDES = \nC_FLAGS = \n")
    with pytest.raises(overrides.OverrideError, match=message):
        overrides.verify_tick_offset_in_build(build_dir, expected=expected == "test")
    overrides.verify_tick_offset_in_build(build_dir, expected=expected != "test")


@pytest.mark.parametrize("tick_offset_test", ["release", "test"])
def test_build_firmware_applies_the_tick_override_only_for_the_test_image_and_proves_every_build(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, setup_toolchain: ModuleType, tick_offset_test: str) -> None:
    # The test image: the override applied for its board, its directory ahead on the include path, its
    # own build dir, the readback asking for it. A release build: none of that, and the readback refusing it.
    toolchain_dir = tmp_path / "toolchain"
    fake_mp_dir = _write_fake_mphalport(_write_fake_modlwip_tree(_write_fake_lwip_tree(toolchain_dir / "micropython")))
    wanted = tick_offset_test == "test"
    build_dir = fake_mp_dir / "ports" / "rp2" / (f"build-{_REAL_BOARD}-tickoffset" if wanted else f"build-{_REAL_BOARD}")
    recorded: list[list[str]] = []

    def fake_run(cmd: list[str], cwd: Path | None = None, **_kwargs: object) -> str:
        recorded.append(cmd)
        build_dir.mkdir(parents=True, exist_ok=True)
        (build_dir / "firmware.uf2").write_bytes(b"")
        return ""

    applied: list[tuple[tuple[object, ...], dict[str, object]]] = []
    real_apply = setup_toolchain.micropython_overrides.apply_tick_offset_override

    def record_apply(*args: object, **kwargs: object) -> "dict[str, str]":
        applied.append((args, kwargs))
        result: dict[str, str] = real_apply(*args, **kwargs)
        return result

    monkeypatch.setattr(setup_toolchain, "run", fake_run)
    monkeypatch.setattr(setup_toolchain.micropython_overrides, "apply_tick_offset_override", record_apply)
    calls = _stub_build_readbacks(setup_toolchain, monkeypatch)
    monkeypatch.setattr(setup_toolchain.micropython_overrides, "verify_lwip_macros_in_build", lambda *_a, **_k: {})
    assert setup_toolchain.build_firmware(fake_mp_dir, _REAL_BOARD, 2, toolchain_dir=toolchain_dir, lwip_macros=_pinned(), tick_offset_test=wanted) == build_dir / "firmware.uf2"
    board_cmake = (toolchain_dir / "build_overrides" / "lwip_connection_counts_board" / "mpconfigboard.cmake").read_text()
    tick_dir = toolchain_dir.resolve() / "build_overrides" / "tick_offset_test"
    assert (f'include_directories(BEFORE "{tick_dir}")' in board_cmake) is wanted
    assert [kwargs for _args, kwargs in applied] == ([{"board": _REAL_BOARD}] if wanted else [])
    assert ("verify_tick_offset_in_build", (build_dir, wanted)) in calls
    assert (f"BUILD=build-{_REAL_BOARD}-tickoffset" in recorded[0]) is wanted


@pytest.mark.parametrize("override", ["unix_kbd_intr", "lwip_connection_counts", "modlwip_eagain", "unix_lwip_host", "tick_offset_test"])
def test_a_rerun_leaves_nothing_an_earlier_run_wrote_in_the_override_dir(overrides: ModuleType, tmp_path: Path, override: str) -> None:
    # Re-run over a dirty toolchain: a file an older generator version wrote would still be compiled
    # (the variant dirs' *.c), or found first on an include path (the BEFORE dirs). Each dir starts empty.
    out = tmp_path / "build_overrides"
    unix, rp2 = _write_fake_micropython_tree(tmp_path / "unix"), _write_fake_lwip_tree(tmp_path / "rp2")
    modlwip, host, tick = _write_fake_modlwip_tree(tmp_path / "modlwip"), _write_fake_lwip_host_tree(tmp_path / "host"), _write_fake_mphalport(tmp_path / "tick")
    applies = {
        "unix_kbd_intr": lambda: overrides.apply_unix_kbd_intr_override(unix, out),
        "lwip_connection_counts": lambda: overrides.apply_lwip_connection_counts_override(rp2, out, _REAL_BOARD, _pinned()),
        "modlwip_eagain": lambda: overrides.apply_modlwip_eagain_override(modlwip, out),
        "unix_lwip_host": lambda: overrides.apply_unix_lwip_host_override(host, out, _pinned()),
        "tick_offset_test": lambda: overrides.apply_tick_offset_override(tick, out, board=_REAL_BOARD),
    }
    applies[override]()
    (written,) = list(out.iterdir())
    stale = [written / "old_port.c", written / "lwip_inc" / "lwip" / "stale.h"]
    for path in stale:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("int left_by_an_older_generator;\n")
    applies[override]()
    assert not [path for path in stale if path.exists()], f"{written.name} kept files the current generator did not write"


def test_the_current_override_dirs_are_exactly_what_the_overrides_write(overrides: ModuleType, micropython_dir: Path, tmp_path: Path) -> None:
    # Read from a real run of every apply_*(), independent of the tuple the leftover remover trusts.
    if not (micropython_dir / _FAKE_TCP_OUT).is_file():
        pytest.fail(f"no real toolchain checkout with lwIP at {micropython_dir} - build it with `toolchain/setup_toolchain.py setup` (scripts/test.sh does)")
    out = tmp_path / "build_overrides"
    overrides.apply_unix_kbd_intr_override(micropython_dir, out)
    overrides.apply_lwip_connection_counts_override(micropython_dir, out, _REAL_BOARD, _pinned())
    overrides.apply_modlwip_eagain_override(micropython_dir, out)
    overrides.apply_unix_lwip_host_override(micropython_dir, out, _pinned())
    overrides.apply_tick_offset_override(micropython_dir, out, board=_REAL_BOARD)
    assert sorted(path.name for path in out.iterdir()) == sorted(overrides.CURRENT_OVERRIDE_DIRS)
    assert len(overrides.CURRENT_OVERRIDE_DIRS) == len(set(overrides.CURRENT_OVERRIDE_DIRS))
