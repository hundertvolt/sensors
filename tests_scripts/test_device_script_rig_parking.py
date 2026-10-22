"""Every NeoPixel a device script constructs is parked dark on every path: the construction sits at a `try` whose
`finally` turns it off (`.off()`, or an all-zero colour then `write()`), so a failing script never leaves the
NeoPixel-to-ISL29125 rig lit for the next test. Read on the rendered scripts."""

import ast
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests_hardware"))
import bench_facts
import harness

_SCRIPTS = Path(__file__).resolve().parents[1] / "tests_hardware" / "device_scripts"
_CONSTRUCTORS = frozenset({"NeopixelDriver", "NeoPixel"})


def _call_name(node: ast.AST) -> str:
    if not isinstance(node, ast.Call):
        return ""
    return node.func.attr if isinstance(node.func, ast.Attribute) else getattr(node.func, "id", "")


def _parks(final: "list[ast.stmt]", name: str) -> bool:
    # The finally turns `name` off: name.off(), or an all-zero colour followed by name.write().
    calls = [n for stmt in final for n in ast.walk(stmt) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and isinstance(n.func.value, ast.Name) and n.func.value.id == name]
    zero = any(isinstance(n, ast.Tuple) and n.elts and all(isinstance(e, ast.Constant) and e.value == 0 for e in n.elts) for stmt in final for n in ast.walk(stmt))
    return any(c.func.attr == "off" for c in calls if isinstance(c.func, ast.Attribute)) or (zero and any(c.func.attr == "write" for c in calls if isinstance(c.func, ast.Attribute)))


def _unparked(source: str) -> "list[int]":
    # Lines of each construction that is neither the first statement of a parking try nor the statement right before one
    # (agent, 2026-10-14: the second form keeps a failed construction from reaching the finally unbound).
    found: list[int] = []
    for node in ast.walk(ast.parse(source)):
        for field in ("body", "orelse", "finalbody"):
            block = getattr(node, field, None)
            if not isinstance(block, list):
                continue
            for i, stmt in enumerate(block):
                if not (isinstance(stmt, ast.Assign) and _call_name(stmt.value) in _CONSTRUCTORS and isinstance(stmt.targets[0], ast.Name)):
                    continue
                name = stmt.targets[0].id
                parent_try = node if isinstance(node, ast.Try) and field == "body" and i == 0 else None
                next_try = block[i + 1] if i + 1 < len(block) and isinstance(block[i + 1], ast.Try) else None
                if not any(t is not None and _parks(t.finalbody, name) for t in (parent_try, next_try)):
                    found.append(stmt.lineno)
    return found


def test_every_neopixel_a_script_constructs_is_parked_on_every_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(harness, "RENDERED_SCRIPTS_DIR", tmp_path)
    # A static check reads the includes a render inlines; no fact value enters it, so the render takes the device
    # module's name alone instead of a cold build of every fact.
    module = f"sensortask_{harness.bench_device()}"
    monkeypatch.setattr(bench_facts, "build", lambda _device: {"device_module": module})
    rendered = {path.name: harness.render_device_script(path).read_text(encoding="utf-8") for path in sorted(_SCRIPTS.glob("*.py"))}
    assert any(_call_name(n) in _CONSTRUCTORS for source in rendered.values() for n in ast.walk(ast.parse(source))), "no script constructs a NeoPixel - the scan reads nothing"
    found = {name: lines for name, source in rendered.items() if (lines := _unparked(source))}
    assert not found, f"a NeoPixel constructed outside a try that parks it dark (script: lines): {found}"


_BITES = {
    "np = NeoPixel(Pin(p, Pin.OUT), 1)\nnp.write()\n": [1],
    "try:\n    np = NeoPixel(Pin(p, Pin.OUT), 1)\n    run(np)\nfinally:\n    np.off()\n": [],
    "pixel = NeopixelDriver(p)\ntry:\n    run(pixel)\nfinally:\n    pixel[0] = (0, 0, 0)\n    pixel.write()\n": [],
    "try:\n    np = NeoPixel(Pin(p, Pin.OUT), 1)\nfinally:\n    np.write()\n": [2],
    "try:\n    x = 1\n    np = NeoPixel(Pin(p, Pin.OUT), 1)\nfinally:\n    np.off()\n": [3],
}


@pytest.mark.parametrize(("source", "lines"), list(_BITES.items()), ids=["no-try", "first-in-try", "right-before-try", "lit-write", "not-first"])
def test_the_parking_check_bites(source: str, lines: "list[int]") -> None:
    assert _unparked(source) == lines
