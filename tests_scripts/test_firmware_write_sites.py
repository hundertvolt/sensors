"""Every limited-endurance write the firmware can make, pinned in _SITES by file, function and construct: each flash
filesystem write in src/ and in every device's generated modules, and each SCD30 command the chip keeps in its NVM.
A new, moved or vanished site fails; any change to the table is the owner's to decide (_OWNER_RULE)."""

import ast
from collections import Counter
from pathlib import Path

import pytest
from _devices import DEVICE_NAMES, device_toml

from buildgen.generate import generate_device

REPO_ROOT = Path(__file__).resolve().parent.parent
_OWNER_RULE = 'a write to the flash or the SCD30 NVM is added, moved or removed only by the owner (owner, 2026-10-22: "a condition strictly to be avoided by rule and nothing you were allowed to decide without even asking")'

# (file, function, construct) -> (what triggers the write, why it is needed). One entry per site; a second site of the
# same construct in the same function fails as new.
_SITES: "dict[tuple[str, str, str], tuple[str, str]]" = {
    ("src/asy_config_manager.py", "ConfigManager._write_file", "open w"): (
        "a PUT's deferred flush when the staged document differs from the file, and setup() over a missing, damaged or drifted file",
        "the config file is each store's only copy that survives a reboot",
    ),
    ("src/asy_config_manager.py", "ConfigManager.delete_file", "os.remove"): (
        "Reset to defaults (SystemCmd resetconfig): one remove per store, retried once on an error other than ENOENT",
        "the next boot writes each store's defaults over a missing file",
    ),
    ("src/asy_scd30_driver.py", "SCD30_I2C.set_temperature_offset", "_send_command 0x5403"): (
        "a PUT whose TempOffset differs from the chip's at tick resolution",
        "the chip keeps its temperature offset in NVM (Interface Description 1.4.7)",
    ),
    ("src/asy_scd30_driver.py", "SCD30_I2C.set_measurement_interval", "_send_command 0x4600"): (
        "a PUT whose MeasInterval differs from the chip's",
        "the chip keeps its measurement interval in NVM (1.4.3)",
    ),
    ("src/asy_scd30_driver.py", "SCD30_I2C.set_ambient_pressure", "_send_command 0x0010"): (
        "every PUT carrying AmbPres, equal or not: a command, never compared",
        "starts continuous measurement with that pressure compensation; the chip keeps the measuring status in NVM (1.4.1)",
    ),
    ("src/asy_scd30_driver.py", "SCD30_I2C.set_altitude", "_send_command 0x5102"): (
        "a PUT whose Altitude differs from the chip's",
        "the chip keeps its altitude compensation in NVM (1.4.8)",
    ),
    ("src/asy_scd30_driver.py", "SCD30_I2C.set_forced_recalibration_reference", "_send_command 0x5204"): (
        "every PUT carrying ForceCalRef, equal or not: a command, never compared",
        "a forced recalibration rewrites the calibration curve the chip keeps in NVM (1.4.6)",
    ),
    ("src/asy_scd30_driver.py", "SCD30_I2C.set_self_calibration_enabled", "_send_command 0x5306"): (
        "a PUT whose SelfCal differs from the chip's",
        "the chip keeps its automatic self-calibration setting in NVM (1.4.6)",
    ),
    ("src/asy_scd30_driver.py", "SCD30_I2C.stop_continuous_measurement", "_send_command 0x0104"): (
        "every PUT carrying ContMeas false",
        "stops continuous measurement, whose status the chip keeps in NVM (1.4.2)",
    ),
}

# The SCD30 commands whose effect the chip saves in non-volatile memory (Interface Description 1.4.1-1.4.3, 1.4.6-1.4.8);
# 0x0104 stops measurement, changing the saved measuring status.
_NVM_COMMANDS = frozenset({0x0010, 0x0104, 0x4600, 0x5306, 0x5204, 0x5403, 0x5102})
_FS_MODULES = frozenset({"os", "uos", "vfs"})
_FS_CALLS = frozenset({"remove", "rename", "mkdir", "rmdir", "unlink", "mount", "umount"})
_WRITE_MODE_CHARS = frozenset("wax+")
_BUILD_DATE = "2026-01-01T00:00:00Z"  # fixed, so generation is deterministic; the scan never reads it


class _Scan:
    def __init__(self, label: str, tree: ast.Module) -> None:
        self.label = label
        self.stack: list[str] = []
        self.sites: list[tuple[str, str, str, int]] = []
        self.consts: dict[str, int] = {}
        self.fs_modules: dict[str, str] = {}  # local name -> os / uos / vfs
        self.fs_names: dict[str, str] = {}  # local name -> the function it was imported as
        self.rp2_modules: set[str] = set()
        self.flash_names: set[str] = set()
        for statement in tree.body:
            if isinstance(statement, ast.Assign) and len(statement.targets) == 1 and isinstance(statement.targets[0], ast.Name):
                value = _int_value(statement.value)
                if value is not None:
                    self.consts[statement.targets[0].id] = value
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in _FS_MODULES:
                        self.fs_modules[alias.asname or alias.name] = alias.name
                    elif alias.name == "rp2":
                        self.rp2_modules.add(alias.asname or alias.name)
            elif isinstance(node, ast.ImportFrom) and node.module in _FS_MODULES:
                self.fs_names.update({alias.asname or alias.name: alias.name for alias in node.names})
            elif isinstance(node, ast.ImportFrom) and node.module == "rp2":
                self.flash_names.update(alias.asname or alias.name for alias in node.names if alias.name == "Flash")

    def _add(self, node: ast.expr, construct: str) -> None:
        self.sites.append((self.label, ".".join(self.stack) or "<module>", construct, node.lineno))

    def _attribute(self, node: ast.Attribute) -> None:
        if node.attr == "mkfs" or node.attr.startswith("Vfs") or node.attr == "writeblocks":
            self._add(node, node.attr)
        elif node.attr == "Flash" and isinstance(node.value, ast.Name) and node.value.id in self.rp2_modules:
            self._add(node, "rp2.Flash")

    def _call(self, node: ast.Call) -> None:
        func = node.func
        name = func.id if isinstance(func, ast.Name) else func.attr if isinstance(func, ast.Attribute) else ""
        base = func.value.id if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name) else ""
        if name == "open" and (isinstance(func, ast.Name) or base in ("io", "builtins")):
            construct = self._open_mode(node)
            if construct is not None:
                self._add(node, construct)
        elif isinstance(func, ast.Attribute) and name in _FS_CALLS and base in self.fs_modules:
            self._add(node, f"{self.fs_modules[base]}.{name}")
        elif isinstance(func, ast.Name) and self.fs_names.get(name) in _FS_CALLS:
            self._add(node, f"os.{self.fs_names[name]}")
        if "send" in name.lower() or "write" in name.lower():
            for value in self._nvm_commands(node):
                self._add(node, f"{name} {value:#06x}")

    def _name(self, node: ast.Name) -> None:
        if node.id == "mkfs" or node.id.startswith("Vfs") or node.id == "writeblocks" or (self.fs_names.get(node.id, "").startswith("Vfs")):
            self._add(node, node.id)
        elif node.id in self.flash_names:
            self._add(node, "rp2.Flash")

    def _nvm_commands(self, node: ast.Call) -> "list[int]":
        found = []
        for arg in [*node.args, *(k.value for k in node.keywords)]:
            value = self.consts.get(arg.id) if isinstance(arg, ast.Name) else _int_value(arg)
            if value in _NVM_COMMANDS and value not in found:
                found.append(value)
        return found

    def _open_mode(self, node: ast.Call) -> "str | None":
        # The construct for an open() that may write, or None for a read-only one.
        mode = node.args[1] if len(node.args) > 1 else next((k.value for k in node.keywords if k.arg == "mode"), None)
        if mode is None:
            return None
        if isinstance(mode, ast.Constant) and isinstance(mode.value, str):
            return f"open {mode.value}" if _WRITE_MODE_CHARS & set(mode.value) else None
        return "open <non-literal mode>"

    def walk(self, node: ast.AST) -> None:
        # Every node once, under the qualified name of the functions and classes enclosing it.
        scope = node.name if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) else None
        if scope is not None:
            self.stack.append(scope)
        if isinstance(node, ast.Call):
            self._call(node)
        elif isinstance(node, ast.Attribute):
            self._attribute(node)
        elif isinstance(node, ast.Name):
            self._name(node)
        for child in ast.iter_child_nodes(node):
            self.walk(child)
        if scope is not None:
            self.stack.pop()


def _firmware_sources() -> "list[tuple[str, str]]":
    # (label, source): every src/ module, and each device's three generated modules, generated in process.
    sources = [(f"src/{path.name}", path.read_text(encoding="utf-8")) for path in sorted((REPO_ROOT / "src").glob("*.py"))]
    for device in DEVICE_NAMES:
        generated = generate_device(device_toml(device), REPO_ROOT / "src", REPO_ROOT / "ext", build_date=_BUILD_DATE)
        sources += [
            (f"generated/sensortask_{device}.py", generated.module_source),
            (f"generated/sensortask_{device}_main.py", generated.boot_entry_source),
            (f"generated/sensortask_{device}_main_noautostart.py", generated.boot_entry_noautostart_source),
        ]
    return sources


def _int_value(node: ast.expr) -> "int | None":
    # A module constant's value: `NAME = const(<int>)` or `NAME = <int>`.
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "const" and len(node.args) == 1:
        node = node.args[0]
    if isinstance(node, ast.Constant) and type(node.value) is int:
        return node.value
    return None


@pytest.fixture(scope="module")
def firmware_sites() -> "list[tuple[str, str, str, int]]":
    sources = _firmware_sources()
    assert len(sources) > 3 * len(DEVICE_NAMES), "no src/ module was scanned"
    return [site for label, source in sources for site in scan_source(label, source)]


def scan_source(label: str, source: str) -> "list[tuple[str, str, str, int]]":
    # (file, function, construct, line) of every limited-endurance write in one module's source.
    tree = ast.parse(source, label)
    scan = _Scan(label, tree)
    scan.walk(tree)
    return scan.sites


def test_every_limited_endurance_write_site_is_pinned(firmware_sites: "list[tuple[str, str, str, int]]") -> None:
    found = Counter(site[:3] for site in firmware_sites)
    pinned = Counter(_SITES.keys())
    lines = [f"  new: {f}:{line} in {func}: {construct}" for f, func, construct, line in firmware_sites if found[(f, func, construct)] > pinned[(f, func, construct)]]
    lines += [f"  vanished or moved: {f} {func}: {construct}" for (f, func, construct) in _SITES if found[(f, func, construct)] < pinned[(f, func, construct)]]
    assert not lines, f"the firmware's write sites differ from _SITES - {_OWNER_RULE}:\n" + "\n".join(lines)


def test_every_pinned_site_names_its_trigger_and_reason() -> None:
    blank = [key for key, (trigger, why) in _SITES.items() if not trigger.strip() or not why.strip()]
    assert not blank, f"each pinned site names what triggers it and why it is needed: {blank}"


_FLAGGED = [
    ('def f(p):\n    open(p, "w")\n', ["open w"]),
    ('def f(p):\n    open(p, mode="ab")\n', ["open ab"]),
    ('def f(p):\n    open(p, "r+")\n', ["open r+"]),
    ("def f(p, m):\n    open(p, m)\n", ["open <non-literal mode>"]),
    ('import os\ndef f(p):\n    os.rename(p, p + ".old")\n', ["os.rename"]),
    ("import uos as u\ndef f(p):\n    u.mkdir(p)\n", ["uos.mkdir"]),
    ("from os import remove as rm\ndef f(p):\n    rm(p)\n", ["os.remove"]),
    ("import vfs\ndef f(b):\n    vfs.mount(b, '/')\n", ["vfs.mount"]),
    ("import os\ndef f(b):\n    os.VfsLfs2.mkfs(b)\n", ["mkfs", "VfsLfs2"]),
    ("def f(b, buf):\n    b.writeblocks(0, buf)\n", ["writeblocks"]),
    ("import rp2\nbdev = rp2.Flash()\n", ["rp2.Flash"]),
    ("_CMD_SET_ALTITUDE_COMPENSATION = const(0x5102)\nasync def f(s):\n    await s._send_command(_CMD_SET_ALTITUDE_COMPENSATION, 5)\n", ["_send_command 0x5102"]),
    ("async def f(s, i2c):\n    await s._send_dev_command(i2c, 0x0104)\n", ["_send_dev_command 0x0104"]),
]
_UNFLAGGED = [
    "def f(p):\n    open(p)\n",
    'def f(p):\n    open(p, "rb")\n',
    "_CMD_SET_ALTITUDE_COMPENSATION = const(0x5102)\nasync def f(s):\n    return await s._read_register(_CMD_SET_ALTITUDE_COMPENSATION)\n",
    "_CMD_SOFT_RESET = const(0xD304)\nasync def f(s):\n    await s._send_command(_CMD_SOFT_RESET)\n",
    "import os\ndef f(p):\n    return os.stat(p)\n",
]


@pytest.mark.parametrize(("source", "constructs"), _FLAGGED)
def test_the_scan_flags_a_write(source: str, constructs: "list[str]") -> None:
    assert [site[2] for site in scan_source("planted.py", source)] == constructs


@pytest.mark.parametrize("source", _UNFLAGGED)
def test_the_scan_leaves_a_read_unflagged(source: str) -> None:
    assert scan_source("planted.py", source) == []
