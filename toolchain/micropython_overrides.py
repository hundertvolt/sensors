"""Canonical, zero-touch overrides for MicroPython's own build: every one generates files and flags
entirely OUTSIDE the fetched checkout, and verifies a known anchor in the pinned source first so a
restructuring release fails loudly. Rationale and version-bump checklist: SPECIFICATION.md B.14."""

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
