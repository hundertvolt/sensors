"""Stand-ins offer only their real class's surface (SPECIFICATION.md E.4): each fake's public names, less its declared
TEST_API, are names the real type has - for the machine fakes, the locals-dict entries of the pinned MicroPython
checkout's C sources; for the webserver test's module doubles, the product's own classes. A missing checkout fails."""

import ast
import re
from pathlib import Path

import pytest
from _repo_scan import REPO_ROOT

# Each machine fake class and the locals-dict tables (file, table name) its rp2 type answers from at the pinned tag.
_REAL_TABLES: dict[str, tuple[tuple[str, str], ...]] = {
    "Pin": (("ports/rp2/machine_pin.c", "machine_pin_locals_dict_table"),),
    "I2C": (("extmod/machine_i2c.c", "machine_i2c_locals_dict_table"),),
    "SPI": (("extmod/machine_spi.c", "machine_spi_locals_dict_table"),),
    "UART": (("extmod/machine_uart.c", "machine_uart_locals_dict_table"),),
    "Timer": (("ports/rp2/machine_timer.c", "machine_timer_locals_dict_table"),),
    "RTC": (("ports/rp2/machine_rtc.c", "machine_rtc_locals_dict_table"),),
    "WDT": (("extmod/machine_wdt.c", "machine_wdt_locals_dict_table"),),
}
# A table entry that is a port macro expands to the port's own entries, defined in this file.
_PORT_MACROS = {"MICROPY_PY_MACHINE_UART_CLASS_CONSTANTS": "ports/rp2/machine_uart.c"}
_UNIT_FAKE = "tests/machine.py"
_TWIN_FAKE = "digital_twin/machine.py"
# Twin classes that declare no TEST_API yet, so their surface cannot be compared; the list only shrinks.
_TWIN_PENDING: "tuple[str, ...]" = ()
_MODULE_DOUBLES_FILE = "tests/test_asy_webserver_service.py"
# Each webserver module double and the product classes whose surface it stands in for.
_MODULE_DOUBLES = {"_FakeModule": ("src/asy_base_classes.py", "SensorReaderConfig"), "_FakeLogger": ("src/asy_print_log.py", "PrintLogHistory")}


def _class(tree: ast.Module, name: str) -> ast.ClassDef:
    found = [node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == name]
    assert len(found) == 1, f"{name}: expected one class definition, found {len(found)}"
    return found[0]


def _declared_test_api(cls: ast.ClassDef) -> "set[str] | None":
    for node in cls.body:
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "TEST_API" for target in node.targets):
            names = ast.literal_eval(node.value)
            assert isinstance(names, tuple), f"{cls.name}.TEST_API is not a tuple literal"
            return {str(name) for name in names}
    return None


def _fake_surface(path: str, name: str) -> "tuple[set[str], set[str] | None, set[str]]":
    # Public methods, class attributes and every public self.<name> its __init__ assigns; its TEST_API; and every
    # public name any of its methods assigns (what a TEST_API entry may name).
    cls = _class(ast.parse((REPO_ROOT / path).read_text(encoding="utf-8")), name)
    return _public_names(cls), _declared_test_api(cls), _public_names(cls, every_method=True)


def _locals_dict_names(checkout: Path, path: str, table: str) -> set[str]:
    source = (checkout / path).read_text(encoding="utf-8")
    start = source.index(f"{table}[] = {{")
    body = source[start : source.index("};", start)]
    names = set(re.findall(r"MP_QSTR_(\w+)", body))
    for macro, macro_file in _PORT_MACROS.items():
        if macro in body:
            definition = (checkout / macro_file).read_text(encoding="utf-8")
            match = re.search(rf"#define {macro} \\\n((?:.*\\\n)+)", definition)
            assert match is not None, f"{macro} not defined in {macro_file}"
            names |= set(re.findall(r"MP_QSTR_(\w+)", match.group(1)))
    return names


def _product_surface(path: str, name: str) -> set[str]:
    # The class, its bases in the same module, and the methods every subclass in src/ shares (the interface a caller
    # dispatches on), so a double of the abstract base may answer what each concrete one does.
    tree = ast.parse((REPO_ROOT / path).read_text(encoding="utf-8"))
    names: set[str] = set()
    pending = [name]
    while pending:
        cls = _class(tree, pending.pop())
        names |= _public_names(cls)
        pending += [base.id for base in cls.bases if isinstance(base, ast.Name) and any(isinstance(node, ast.ClassDef) and node.name == base.id for node in tree.body)]
    shared: set[str] | None = None
    for source in sorted((REPO_ROOT / "src").glob("*.py")):
        for node in ast.parse(source.read_text(encoding="utf-8")).body:
            if isinstance(node, ast.ClassDef) and any(ast.unparse(base).rsplit(".", 1)[-1] == name for base in node.bases):
                own = _public_names(node)
                shared = own if shared is None else shared & own
    return names | (shared or set())


def _public_names(cls: ast.ClassDef, *, every_method: bool = False) -> set[str]:
    names: set[str] = set()
    for node in cls.body:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            names.add(node.name)
            if every_method or node.name == "__init__":
                names |= {target.attr for target in ast.walk(node) if isinstance(target, ast.Attribute) and isinstance(target.ctx, ast.Store) and isinstance(target.value, ast.Name) and target.value.id == "self"}
        elif isinstance(node, ast.Assign):
            names |= {target.id for target in node.targets if isinstance(target, ast.Name)}
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
    return {name for name in names if not name.startswith("_") and name != "TEST_API"}


@pytest.fixture(scope="module")
def checkout(micropython_dir: Path) -> Path:
    # The surface is read from the pinned checkout, never assumed: a missing one fails every case, never skips.
    if not (micropython_dir / "ports" / "rp2" / "machine_pin.c").is_file():
        pytest.fail(f"pinned MicroPython checkout not found at {micropython_dir} - run toolchain/setup_toolchain.py setup first")
    return micropython_dir


@pytest.mark.parametrize("name", sorted(_REAL_TABLES))
def test_a_unit_machine_fake_offers_only_its_real_class_surface(checkout: Path, name: str) -> None:
    public, test_api, defined = _fake_surface(_UNIT_FAKE, name)
    assert test_api is not None, f"{_UNIT_FAKE} {name} declares no TEST_API"
    real = set().union(*(_locals_dict_names(checkout, path, table) for path, table in _REAL_TABLES[name]))
    assert sorted(public - test_api - real) == [], f"{name}: public names neither rp2's nor declared test-only"
    assert sorted(test_api - defined) == [], f"{name}: TEST_API names that the class does not define"


@pytest.mark.parametrize("name", sorted(_REAL_TABLES))
def test_a_twin_machine_fake_offers_only_its_real_class_surface_or_is_pending(checkout: Path, name: str) -> None:
    public, test_api, _defined = _fake_surface(_TWIN_FAKE, name)
    if name in _TWIN_PENDING:
        assert test_api is None, f"{_TWIN_FAKE} {name} declares its TEST_API now - remove it from _TWIN_PENDING"
        return
    assert test_api is not None, f"{_TWIN_FAKE} {name} declares no TEST_API"
    real = set().union(*(_locals_dict_names(checkout, path, table) for path, table in _REAL_TABLES[name]))
    assert sorted(public - test_api - real) == [], f"{name}: public names neither rp2's nor declared test-only"


@pytest.mark.parametrize("name", sorted(_MODULE_DOUBLES))
def test_a_webserver_module_double_offers_only_its_product_surface(name: str) -> None:
    public, test_api, _defined = _fake_surface(_MODULE_DOUBLES_FILE, name)
    real = _product_surface(*_MODULE_DOUBLES[name])
    assert sorted(public - (test_api or set()) - real) == [], f"{name}: public names the product class lacks, undeclared"


def test_the_locals_dict_reader_finds_every_rp2_table(checkout: Path) -> None:
    # The reader must not pass by finding nothing: each table answers names the fakes are known to share.
    expected = {"Pin": "value", "I2C": "writeto", "SPI": "readinto", "UART": "INV_TX", "Timer": "PERIODIC", "RTC": "datetime", "WDT": "feed"}
    for name, entry in expected.items():
        assert entry in set().union(*(_locals_dict_names(checkout, path, table) for path, table in _REAL_TABLES[name])), name
