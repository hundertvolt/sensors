"""Canonical, zero-touch overrides for MicroPython's own build. Every override here generates
files/flags entirely OUTSIDE the fetched `$PICO_TOOLCHAIN_DIR/micropython` checkout - never a byte
written into it - referencing the pinned source by absolute path, and verifies a known anchor in
that source first so a future MicroPython release that restructures the target fails the build
loudly instead of silently shipping unpatched behavior. Full design rationale, the mechanism used
for each override, and the re-verification checklist for a MicroPython version bump:
SPECIFICATION.md Part B.14."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
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

# The exact line as pinned (ports/unix/variants/mpconfigvariant_common.h) - a plain, UNGUARDED
# #define (no #ifndef), which is exactly why a CFLAGS_EXTRA -D can't override it: verified
# directly (2026-09-15) that a later plain #define in the same translation unit always wins over
# an earlier command-line -D, regardless of order, and this build treats the resulting
# "macro redefined" warning as a hard failure anyway.
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
    """Redirects the Unix "standard" variant's own config directory (`make`'s `VARIANT_DIR`, which
    the port's Makefile only defaults via `?=` - a plain command-line override wins cleanly, no
    ordering tricks needed) to an external directory that `#include`s the real variant files by
    absolute path and then `#undef`/`#define`s `MICROPY_ASYNC_KBD_INTR` to 0 - MicroPython's own
    safe path (`mp_sched_keyboard_interrupt()`, checked at the next bytecode-dispatch safepoint)
    instead of the default's immediate `nlr_raise()` straight from the async SIGINT handler, which
    can land mid any non-reentrant operation (GC collection, exception/frame bookkeeping) and
    corrupt VM state. Verified empirically end-to-end (2026-09-15): the resulting binary's
    preprocessed `unix_mphal.c` selects the safe branch, and a build with `VARIANT=standard`
    explicitly still also passed keeps `BUILD ?= build-$(VARIANT)` at `build-standard` (every other
    script in this repo hardcodes that path) - `VARIANT_DIR` alone would otherwise derive `VARIANT`
    from the override directory's own name and rename the build output directory.
    Returns the extra `make` variables `build_unix_port()` must pass through unchanged."""
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
