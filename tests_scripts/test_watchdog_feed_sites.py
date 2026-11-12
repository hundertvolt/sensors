"""The watchdog is fed only by the system service: every `.feed()` or `feed_watchdog()` call in src/ sits in
asy_system_service.py's SystemService, and no generated module or boot entry makes either. A stray feed elsewhere
would keep a wedged loop alive past the hardware watchdog, the owner's backstop (CLAUDE.md)."""

import ast
from pathlib import Path

from _devices import DEVICE_NAMES

from buildgen.generate import generate_device

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC = REPO_ROOT / "src"
_SERVICE = ("asy_system_service.py", "SystemService")
_FEEDS = frozenset({"feed", "feed_watchdog"})


def _feeds(tree: ast.Module) -> "list[tuple[str, int]]":
    # (the enclosing top-level class or "", line) for every call named feed() or feed_watchdog().
    found: list[tuple[str, int]] = []
    for top in tree.body:
        owner = top.name if isinstance(top, ast.ClassDef) else ""
        for node in ast.walk(top):
            if isinstance(node, ast.Call):
                func = node.func
                name = func.attr if isinstance(func, ast.Attribute) else func.id if isinstance(func, ast.Name) else None
                if name in _FEEDS:
                    found.append((owner, node.lineno))
    return found


def test_only_the_system_service_feeds_the_watchdog() -> None:
    sites = {path.name: _feeds(ast.parse(path.read_text(encoding="utf-8"))) for path in sorted(SRC.glob("*.py"))}
    stray = [f"{name}:{line}" for name, found in sites.items() for owner, line in found if (name, owner) != _SERVICE]
    assert stray == []
    assert sites[_SERVICE[0]], "the system service no longer feeds: the check would pass on nothing"


def test_no_generated_module_or_boot_entry_feeds() -> None:
    for device in DEVICE_NAMES:
        generated = generate_device(REPO_ROOT / "devices" / f"{device}.toml", SRC, REPO_ROOT / "ext")
        for source in (generated.module_source, generated.boot_entry_source, generated.boot_entry_noautostart_source):
            assert _feeds(ast.parse(source)) == [], device
