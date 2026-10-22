"""SPECIFICATION.md I.2 classifies every module's allocations; run-phase code allocates nothing long-lived except the
listed, reasoned cases: a method other than __init__/setup that stores a new object on self is named in
_RUN_PHASE_ALLOWED with its reason, over src/ and each device's generated modules, generated in memory."""

import ast
import re
from pathlib import Path

import pytest
from _devices import DEVICE_NAMES

from buildgen.generate import generate_device

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC = REPO_ROOT / "src"
_SPEC = REPO_ROOT / "SPECIFICATION.md"
_CONSTRUCTION = frozenset({"__init__", "setup"})
_ALLOCATING_CALLS = frozenset({"bytearray", "bytes", "memoryview", "list", "tuple", "dict", "set", "create_task"})
_GENERATED_ROWS = ("generated device modules", "generated boot entry")

# (module, "Class.method", attribute) -> why the run-phase allocation is not a long-lived object born amid churn.
_RUN_PHASE_ALLOWED: "dict[tuple[str, str, str], str]" = {
    ("asy_base_classes.py", "SensorReader._republish", "_datastruct"): "the changed sample, per republish, replacing the last",
    **{
        ("asy_bmp3xx_driver.py", "BMP3XX_I2C._read_coefficients", attr): "setup only: the calibration coefficients, replaced at each read-task start"
        for attr in ("_pressure_calib", "_temp_calib")
    },
    ("asy_fram_manager.py", "_FRAMBaseChunk._compare_with", "_compare_against"): "a view of the caller's buffer, cleared in finally",
    ("asy_i2c_driver.py", "I2C.init", "_args"): "per controller recovery: the stored arguments, replacing the last",
    ("asy_i2c_driver.py", "I2C.init", "_i2c"): "machine.I2C() returns a static object (ports/rp2/machine_i2c.c)",
    **{
        ("asy_isl29125_driver.py", f"ISL29125_Reader.{method}", "_cal_recent"): "calibration only, at most _CAL_CONVERGE_N ratios"
        for method in ("_end_calibration", "_measure_gain_ratio", "_note_candidate", "_read_on", "start_calibration")
    },
    ("asy_neopixel_driver.py", "NeopixelDriver._overlay_loop", "_overlay_rgb"): "the pixel tuple, replaced at every overlay wake",
    ("asy_scd30_driver.py", "SCD30_Reader._store_scd", "_datastruct"): "the latest reading, replaced at every read",
    ("asy_spi_driver.py", "SPI.init", "_spi"): "construction: init() runs from __init__ only, and machine.SPI() returns a static object (ports/rp2/machine_spi.c)",
    ("asy_system_service.py", "SystemService._reboot", "_reset_task"): "the one reset task of a reboot",
    ("asy_system_service.py", "SystemService._request_shutdown", "_shutdown_task"): "the one task of an accepted system command",
    ("asy_system_service.py", "SystemService.run_setups", "_config_faults"): "the boot list's end: once per boot",
    ("asy_system_service.py", "SystemService.start_tasks", "_tasks"): "the task-start list's slots: once per boot",
    ("asy_system_service.py", "SystemService.supervise_tasks", "_supervisor_task"): "the supervisor's own task, started once at boot",
    ("asy_uart_driver.py", "UART.init", "_uart"): "construction: init() runs from __init__ only",
    ("asy_uart_link_driver.py", "UARTLinkDriver._run_hazards", "_hazard_facts"): "the last hazard run's verdicts, replaced per run of dev's on-demand route",
    ("asy_webserver_service.py", "_PieceWriter.add", "_group"): "per response",
    ("asy_webserver_service.py", "_PieceWriter.flush", "_group"): "per response",
    ("asy_wifi_service.py", "WifiService._configure_hotspot_ap", "_dns_server_task"): "the hotspot's DNS task: the hotspot is a run-phase mode",
    ("asy_wifi_service.py", "WifiService._run_led_pattern", "_led_pattern"): "the LED pattern's (on, off) pair, one at a time",
    ("asy_wifi_service.py", "WifiService._run_led_pattern", "_ledflash"): "the LED pattern's task, one at a time",
    ("asy_wifi_service.py", "WifiService._switch_wlan_mode", "_wlan"): "network.WLAN() returns a static object (extmod/network_cyw43.c)",
}


def _allocates(value: ast.expr) -> bool:
    # A new object: a class instantiation (an upper-case name, private or not), a display (a tuple only when MicroPython
    # cannot fold it), a comprehension, an allocating call or a call through an expression (`type(x)(...)`); for a
    # conditional, a boolean or a binary operation, any operand that is one.
    if isinstance(value, ast.List | ast.Dict | ast.Set | ast.ListComp | ast.DictComp | ast.SetComp | ast.GeneratorExp):
        return True
    if isinstance(value, ast.Tuple):
        return not _folded(value)
    if isinstance(value, ast.IfExp):
        return _allocates(value.body) or _allocates(value.orelse)
    if isinstance(value, ast.BoolOp):
        return any(_allocates(operand) for operand in value.values)
    if isinstance(value, ast.BinOp):
        return _allocates(value.left) or _allocates(value.right)
    if not isinstance(value, ast.Call):
        return False
    func = value.func
    if not isinstance(func, ast.Name | ast.Attribute):
        return True
    name = (func.id if isinstance(func, ast.Name) else func.attr).lstrip("_")
    return name[:1].isupper() or name in _ALLOCATING_CALLS


def _catalog_text() -> str:
    text = _SPEC.read_text(encoding="utf-8")
    start = text.index("\n## I.2 ")
    return text[start : text.index("\n## ", start + 1)]


def _folded(value: ast.expr) -> bool:
    # A constant MicroPython's parser folds into one object (py/parse.c, build_tuple_from_stack()): a literal, a signed
    # number, or a tuple of them.
    if isinstance(value, ast.UnaryOp):
        return isinstance(value.operand, ast.Constant)
    if isinstance(value, ast.Tuple):
        return all(_folded(item) for item in value.elts)
    return isinstance(value, ast.Constant)


def _stored(node: ast.AST) -> "list[str]":
    # The self attributes an assignment stores a new object in.
    targets = node.targets if isinstance(node, ast.Assign) else [node.target] if isinstance(node, ast.AnnAssign) else []
    value = node.value if isinstance(node, ast.Assign | ast.AnnAssign) else None
    if value is None or not _allocates(value):
        return []
    return [t.attr for t in targets if isinstance(t, ast.Attribute) and isinstance(t.value, ast.Name) and t.value.id == "self"]


def _violations(path: str, source: str) -> "list[tuple[str, str, str]]":
    # (module, "Class.method", attribute) for every self.<attr> = <new object> in a method of the run phase.
    classes = [node for node in ast.parse(source).body if isinstance(node, ast.ClassDef)]
    methods = [(cls.name, n) for cls in classes for n in cls.body if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef) and n.name not in _CONSTRUCTION]
    return sorted({(path, f"{owner}.{method.name}", attr) for owner, method in methods for node in ast.walk(method) for attr in _stored(node)})


@pytest.fixture(scope="module")
def sources() -> "dict[str, str]":
    # src/ from disk, and each device's module and boot entries in memory, under the names their rows use.
    out = {p.name: p.read_text(encoding="utf-8") for p in sorted(SRC.glob("*.py"))}
    for device in DEVICE_NAMES:
        result = generate_device(REPO_ROOT / "devices" / f"{device}.toml", SRC, REPO_ROOT / "ext")
        out[f"sensortask_{device}.py"] = result.module_source
        out[f"sensortask_{device}_main.py"] = result.boot_entry_source
        out[f"sensortask_{device}_main_noautostart.py"] = result.boot_entry_noautostart_source
    return out


def test_every_src_module_has_a_catalog_section() -> None:
    catalog = _catalog_text()
    named = set(re.findall(r"`([a-z_0-9]+\.py)`", catalog))
    missing = sorted(p.name for p in SRC.glob("*.py") if p.name not in named)
    assert not missing, f"SPECIFICATION.md I.2 names no section for {missing}"
    for row in _GENERATED_ROWS:
        assert row in catalog, f"SPECIFICATION.md I.2 has no '{row}' row"


def test_no_unlisted_run_phase_long_lived_allocation(sources: "dict[str, str]") -> None:
    unlisted = [site for path, source in sorted(sources.items()) for site in _violations(path, source) if site not in _RUN_PHASE_ALLOWED]
    assert not unlisted, f"run-phase allocations not in _RUN_PHASE_ALLOWED (SPECIFICATION.md I.2): {unlisted}"


def test_every_allowed_entry_still_matches_a_site(sources: "dict[str, str]") -> None:
    live = {site for path, source in sources.items() for site in _violations(path, source)}
    stale = sorted(set(_RUN_PHASE_ALLOWED) - live)
    assert not stale, f"_RUN_PHASE_ALLOWED entries that no longer occur: {stale}"


def test_the_walk_covers_the_generated_modules(sources: "dict[str, str]") -> None:
    # The generated modules hold no class today, so no row of theirs is listed: a class they gained would be walked.
    generated = [path for path in sources if path.startswith("sensortask_")]
    assert len(generated) == 3 * len(DEVICE_NAMES)
    assert _violations("x.py", "class A:\n    def poll(self):\n        self.cache = {}\n") == [("x.py", "A.poll", "cache")]


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        ("    def poll(self):\n        self.buf = bytearray(4)\n", 1),
        ("    def poll(self):\n        self.task = asyncio.create_task(f())\n", 1),
        ("    def poll(self):\n        self.data = Reading(1, 2)\n", 1),
        ("    def poll(self):\n        self.items = [x for x in y]\n", 1),
        ("    def poll(self):\n        self.items = (x for x in y)\n", 1),
        ("    def poll(self):\n        self.pair = (a, b)\n", 1),
        ("    def poll(self):\n        self.pair = tuple(y)\n", 1),
        ("    def poll(self):\n        self.rgb = (b,) * 3 if on else (0, 0, 0)\n", 1),
        ("    def poll(self):\n        self.slots = [None] * n\n", 1),
        ("    def poll(self):\n        self.cache = self.cache or {}\n", 1),
        ("    def poll(self):\n        self.bus = _Bus(1)\n", 1),
        ("    def poll(self):\n        self.data = type(old)(*values)\n", 1),
        ("    def poll(self):\n        self.pair = (1, -2, 'x', (3.0, None))\n", 0),
        ("    def poll(self):\n        self.value = self._read() if ok else None\n", 0),
        ("    def poll(self):\n        self.count = self.count + 1\n", 0),
        ("    def poll(self):\n        self.view = None\n", 0),
        ("    def __init__(self):\n        self.cache = {}\n", 0),
        ("    async def setup(self):\n        self.cache = {}\n", 0),
    ],
)
def test_a_fabricated_method_is_judged_by_what_it_stores(body: str, expected: int) -> None:
    assert len(_violations("x.py", "class A:\n" + body)) == expected
