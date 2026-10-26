"""html/style.css's colour tokens meet WCAG 2.1 AA in both themes: text 4.5 on every background it sits on, each
status colour 4.5 on its own background and on the card surface, control borders 3.0 (WCAG 1.4.11); native
controls follow the theme through color-scheme, and the drawer honours reduced motion (SPECIFICATION.md H.1)."""

import re
from pathlib import Path

import pytest

_CSS = Path(__file__).resolve().parent.parent / "html" / "style.css"
_DARK = "@media (prefers-color-scheme: dark)"
_REDUCED_MOTION = "@media (prefers-reduced-motion: reduce)"
_TOKEN = re.compile(r"(--color-[\w-]+):\s*(#[0-9a-fA-F]{6}|#[0-9a-fA-F]{3})\s*;")
_TEXT, _STATUS, _COMPONENT = 4.5, 4.5, 3.0

# (foreground, background, minimum): where each colour token is drawn on which background in the stylesheet.
_PAIRS = (
    *((text, background, _TEXT) for text in ("text", "text-muted") for background in ("bg", "surface", "surface-alt")),
    ("accent-contrast", "accent", _TEXT),
    *((status, background, _STATUS) for status in ("success", "danger", "warn") for background in (f"{status}-bg", "surface")),
    *(("neutral", background, _STATUS) for background in ("neutral-bg", "surface")),
    *(("control-border", background, _COMPONENT) for background in ("surface", "surface-alt")),
)


def _block(css: str, opener: str) -> str:
    # The body of the first block opened by `opener`, braces balanced.
    open_at = css.index("{", css.index(opener))
    depth = 0
    for i in range(open_at, len(css)):
        depth += (css[i] == "{") - (css[i] == "}")
        if depth == 0:
            return css[open_at + 1 : i]
    raise AssertionError(f"{opener} block is not closed")


def _contrast(foreground: str, background: str) -> float:
    lighter, darker = sorted((_luminance(foreground), _luminance(background)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


def _luminance(colour: str) -> float:
    # WCAG 2.1 relative luminance of an sRGB hex colour.
    digits = colour.lstrip("#")
    digits = "".join(c * 2 for c in digits) if len(digits) == 3 else digits
    channels = [int(digits[k : k + 2], 16) / 255 for k in (0, 2, 4)]
    r, g, b = (c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _stylesheet() -> str:
    return re.sub(r"/\*.*?\*/", "", _CSS.read_text(encoding="utf-8"), flags=re.DOTALL)


def _themes() -> dict[str, dict[str, str]]:
    # The light tokens on :root, and the dark theme as the light ones overridden by its own :root block.
    css = _stylesheet()
    light = dict(_TOKEN.findall(_block(css, ":root {")))
    dark = {**light, **dict(_TOKEN.findall(_block(_block(css, _DARK), ":root {")))}
    return {"light": light, "dark": dark}


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_every_colour_pair_meets_its_contrast_minimum(theme: str) -> None:
    tokens = _themes()[theme]
    failures = []
    for foreground, background, minimum in _PAIRS:
        missing = [name for name in (f"--color-{foreground}", f"--color-{background}") if name not in tokens]
        if missing:
            failures.append(f"{missing} not defined")
            continue
        ratio = _contrast(tokens[f"--color-{foreground}"], tokens[f"--color-{background}"])
        if round(ratio, 2) < minimum:
            failures.append(f"--color-{foreground} on --color-{background}: {ratio:.2f} < {minimum}")
    assert not failures, failures


def test_the_dark_theme_redefines_every_colour_token() -> None:
    # Guard: a token the dark block leaves out would be checked, and drawn, with its light value.
    css = _stylesheet()
    light = {name for name, _ in _TOKEN.findall(_block(css, ":root {"))}
    dark = {name for name, _ in _TOKEN.findall(_block(_block(css, _DARK), ":root {"))}
    assert light
    assert dark == light


def test_native_controls_follow_the_theme() -> None:
    assert re.search(r":root\s*\{[^}]*\bcolor-scheme:\s*light dark\s*;", _stylesheet())


def test_inputs_selects_toggles_and_action_buttons_draw_the_control_border() -> None:
    css = _stylesheet()
    for selector in ('.field input[type="text"]', '.field input[type="password"]', ".field select", ".toggle-button", ".action-button"):
        rule = re.search(rf"(?:^|[}},])\s*{re.escape(selector)}\s*(?:,[^{{]*)?\{{([^}}]*)\}}", css, re.MULTILINE)
        assert rule is not None, selector
        assert re.search(r"border:\s*1px solid var\(--color-control-border\)", rule.group(1)), selector


def test_the_drawer_and_backdrop_do_not_animate_under_reduced_motion() -> None:
    body = _block(_stylesheet(), _REDUCED_MOTION)
    rule = re.search(r"\.nav-backdrop,\s*\.nav-drawer\s*\{([^}]*)\}", body)
    assert rule is not None, body
    assert re.search(r"transition:\s*none\s*;", rule.group(1))


def test_the_ratio_reader_bites() -> None:
    # The formula against WCAG's own anchors: black on white is 21, a colour on itself is 1.
    assert round(_contrast("#000", "#fff"), 2) == 21.0
    assert _contrast("#197f45", "#197f45") == 1.0
    assert round(_contrast("#1f9d55", "#e5f7ec"), 2) == 3.13
