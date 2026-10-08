"""The runtime import graph (SPECIFICATION.md F.1, L.2) over src/, ext/ and every device's generated modules:
acyclic, no sensor driver importing another, names imported where they are defined; no device image
holds a dynamic-import site, and outside the images only F.1's named host and test files load dynamically."""

import ast
import os
import shutil
import subprocess
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import pytest
from _devices import DEVICE_NAMES
from _repo_scan import REPO_ROOT, repo_files
from test_import_placement import _NAMED_EXCEPTIONS, f1_named_paths

from buildgen.generate import generate_device

# What a scan of the repository never reads: the reference-only legacy tree, the C peer, the audit set,
# and the two checks whose fixtures are the patterns themselves.
_NOT_SCANNED = ("legacy/", "arduino/", "audit/", "node_modules/")
_OWN_FIXTURES = frozenset({"tests_scripts/test_import_graph.py", "tests_scripts/test_import_placement.py"})
_WEBSITE_MODULE = "frozen_html"

Site = tuple[str, int, str]


@dataclass(frozen=True)
class Module:
    name: str
    path: str
    tree: ast.Module


@dataclass(frozen=True)
class Image:
    device: str
    modules: tuple[Module, ...]


def _parse(name: str, path: str, source: str) -> Module:
    return Module(name, path, ast.parse(source, filename=path))


def _is_type_checking(test: ast.expr) -> bool:
    return (isinstance(test, ast.Name) and test.id == "TYPE_CHECKING") or (isinstance(test, ast.Attribute) and test.attr == "TYPE_CHECKING")


def _runtime_nodes(node: ast.AST) -> Iterator[ast.AST]:
    # Every node that runs on the device: an `if TYPE_CHECKING:` body is stripped, its else branch kept.
    for child in ast.iter_child_nodes(node):
        if isinstance(child, ast.If) and _is_type_checking(child.test):
            for kept in child.orelse:
                yield kept
                yield from _runtime_nodes(kept)
            continue
        yield child
        yield from _runtime_nodes(child)


def static_imports(module: Module) -> list[tuple[str, str | None, int]]:
    # (imported module, imported name or None for a plain import, line) for every runtime import.
    found: list[tuple[str, str | None, int]] = []
    for node in _runtime_nodes(module.tree):
        if isinstance(node, ast.Import):
            found.extend((alias.name, None, node.lineno) for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            found.extend((node.module, alias.name, node.lineno) for alias in node.names)
    return found


def _bound_by_definition(module: Module) -> set[str]:
    # Names a module binds at runtime by def, class or assignment at module level (any if/try branch
    # that runs), never by an import: a name bound only by importing it is a re-export.
    bound: set[str] = set()
    pending: list[ast.stmt] = list(module.tree.body)
    while pending:
        node = pending.pop()
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            bound.add(node.name)
        elif isinstance(node, ast.Assign):
            bound.update(target.id for target in node.targets if isinstance(target, ast.Name))
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.value is not None:
            bound.add(node.target.id)
        elif isinstance(node, ast.If):
            pending.extend(node.orelse if _is_type_checking(node.test) else [*node.body, *node.orelse])
        elif isinstance(node, ast.Try):
            pending.extend([*node.body, *node.orelse, *node.finalbody, *(s for h in node.handlers for s in h.body)])
    return bound


def _sensor_drivers(modules: dict[str, Module]) -> set[str]:
    # A sensor driver is an asy_*_driver.py module defining a *_Reader class (SPECIFICATION.md C.1's layer 3).
    return {
        name for name, module in modules.items()
        if module.path.startswith("src/") and name.startswith("asy_") and name.endswith("_driver")
        and any(isinstance(node, ast.ClassDef) and node.name.endswith("_Reader") for node in module.tree.body)
    }


def graph_violations(modules: dict[str, Module]) -> list[str]:
    edges: dict[str, set[str]] = {name: set() for name in modules}
    drivers = _sensor_drivers(modules)
    found: list[str] = []
    for name, module in sorted(modules.items()):
        for target, imported, line in static_imports(module):
            top = target.split(".")[0]
            if top not in modules:
                continue
            edges[name].add(top)
            where = f"{module.path}:{line}"
            if name in drivers and top in drivers and top != name:
                found.append(f"{where}: sensor driver {name} imports sensor driver {top}")
            if name == "asy_print_log" and top == "asy_fram_manager":
                found.append(f"{where}: asy_print_log imports asy_fram_manager at runtime")
            if imported is not None and imported not in _bound_by_definition(modules[top]):
                found.append(f"{where}: {imported} is imported from {top}, which does not define it")
    found.extend(f"import cycle: {' -> '.join(cycle)}" for cycle in _cycles(edges))
    return found


def _cycles(edges: dict[str, set[str]]) -> list[list[str]]:
    cycles: list[list[str]] = []
    state: dict[str, int] = {}
    stack: list[str] = []

    def visit(node: str) -> None:
        state[node] = 1
        stack.append(node)
        for nxt in sorted(edges[node]):
            if state.get(nxt) == 1:
                cycles.append([*stack[stack.index(nxt) :], nxt])
            elif nxt not in state:
                visit(nxt)
        stack.pop()
        state[node] = 2

    for node in sorted(edges):
        if node not in state:
            visit(node)
    return cycles


def _src_and_ext(src_dir: Path, ext_dir: Path) -> dict[str, Module]:
    modules = {p.stem: _parse(p.stem, f"src/{p.name}", p.read_text(encoding="utf-8")) for p in sorted(src_dir.glob("*.py"))}
    modules.update({p.stem: _parse(p.stem, f"ext/{p.name}", p.read_text(encoding="utf-8")) for p in sorted(ext_dir.glob("*.py"))})
    return modules


def build_images(src_dir: Path, ext_dir: Path, website: Path, out_dir: Path) -> list[Image]:
    # Each device's frozen set as build_firmware.py stages it: its src/ and ext/ modules, the generated device
    # module and both boot entries written into out_dir (one is staged as main.py, the other is the no-autostart
    # image's), and the website module.
    images = []
    for device in DEVICE_NAMES:
        generated = generate_device(REPO_ROOT / "devices" / f"{device}.toml", src_dir, ext_dir)
        generated_names = (f"sensortask_{device}", f"sensortask_{device}_main", f"sensortask_{device}_main_noautostart")
        for name, source in zip(generated_names, (generated.module_source, generated.boot_entry_source, generated.boot_entry_noautostart_source), strict=True):
            (out_dir / f"{name}.py").write_text(source, encoding="utf-8")
        modules = []
        for name in sorted(generated.frozen_modules):
            path = src_dir / f"{name}.py" if (src_dir / f"{name}.py").is_file() else ext_dir / f"{name}.py"
            modules.append(_parse(name, f"{path.parent.name}/{path.name}", path.read_text(encoding="utf-8")))
        modules.extend(_parse(name, f"build/generated_src/{name}.py", (out_dir / f"{name}.py").read_text(encoding="utf-8")) for name in generated_names)
        modules.append(_parse(_WEBSITE_MODULE, f"build/{device}/{_WEBSITE_MODULE}.py", website.read_text(encoding="utf-8")))
        images.append(Image(device, tuple(modules)))
    return images


def image_sites(module: Module) -> list[Site]:
    # Inside an image nothing loads code dynamically: no __import__, no importlib, no exec/eval of source.
    sites: list[Site] = []
    for node in ast.walk(module.tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in {"__import__", "exec", "eval"}:
            sites.append((module.path, node.lineno, node.func.id))
        sites.extend(_importlib_sites(module.path, node))
    return sites


def _importlib_sites(path: str, node: ast.AST) -> list[Site]:
    if isinstance(node, ast.Import):
        return [(path, node.lineno, f"import {a.name}") for a in node.names if a.name.split(".")[0] == "importlib"]
    if isinstance(node, ast.ImportFrom) and (node.module or "").split(".")[0] == "importlib":
        return [(path, node.lineno, f"from {node.module} import")]
    if isinstance(node, ast.Name) and node.id == "importlib":
        return [(path, node.lineno, "importlib")]
    return []


def host_sites(path: str, source: str) -> list[Site]:
    # Outside an image: every __import__ call and importlib import or use, launcher source held in a
    # string literal included.
    sites: list[Site] = []
    for node in ast.walk(ast.parse(source, filename=path)):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "__import__":
            sites.append((path, node.lineno, "__import__"))
        elif isinstance(node, ast.Constant) and isinstance(node.value, str) and ("importlib" in node.value or "__import__(" in node.value):
            try:
                sites.extend((path, node.lineno, what) for _, _, what in host_sites(path, node.value))
            except SyntaxError:
                pass
        sites.extend(_importlib_sites(path, node))
    return sites


def unnamed_host_sites(files: list[str]) -> list[Site]:
    found: list[Site] = []
    for path in files:
        if path.endswith(".py") and not path.startswith(_NOT_SCANNED) and path not in _OWN_FIXTURES and path not in _NAMED_EXCEPTIONS:
            found.extend(host_sites(path, (REPO_ROOT / path).read_text(encoding="utf-8")))
    return found


@pytest.fixture(scope="module")
def website(tmp_path_factory: pytest.TempPathFactory) -> Path:
    # The website module's code is freezefs's mount wrapper, the same for every device; its pages are
    # bytes data, so one module frozen from a stub tree stands for each image's.
    root = tmp_path_factory.mktemp("website")
    (root / "site").mkdir()
    (root / "site" / "index.html").write_text("<p>stub</p>", encoding="utf-8")
    out = root / f"{_WEBSITE_MODULE}.py"
    env = {**os.environ, "HTML_SRC_DIRS": str(root / "site")}
    built = subprocess.run([str(REPO_ROOT / "scripts" / "build_frozen_html.sh"), str(out)], cwd=REPO_ROOT, env=env, capture_output=True, text=True, check=False)
    assert built.returncode == 0, f"build_frozen_html.sh failed:\n{built.stdout}{built.stderr}"
    return out


@pytest.fixture(scope="module")
def images(tmp_path_factory: pytest.TempPathFactory, website: Path) -> list[Image]:
    return build_images(REPO_ROOT / "src", REPO_ROOT / "ext", website, tmp_path_factory.mktemp("generated_src"))


def _graph(images: list[Image]) -> dict[str, Module]:
    modules = _src_and_ext(REPO_ROOT / "src", REPO_ROOT / "ext")
    for image in images:
        modules.update({m.name: m for m in image.modules if not m.path.startswith(("src/", "ext/"))})
    return modules


def test_the_runtime_import_graph_is_acyclic_and_imports_only_defined_names(images: list[Image]) -> None:
    found = graph_violations(_graph(images))
    assert not found, "runtime import graph (SPECIFICATION.md F.1):\n" + "\n".join(found)


def test_the_graph_sees_every_sensor_driver(images: list[Image]) -> None:
    drivers = _sensor_drivers(_graph(images))
    assert {"asy_bmp3xx_driver", "asy_isl29125_driver", "asy_scd30_driver", "asy_sgp40_driver"} <= drivers, drivers


def shared_names(src_dir: Path, ext_dir: Path) -> list[str]:
    src = {p.stem for p in src_dir.glob("*.py")}
    ext = {p.stem for p in ext_dir.glob("*.py")} | {p.parent.name for p in ext_dir.glob("*/*.py")}
    return sorted(src & ext)


def test_no_module_name_is_in_both_src_and_ext(tmp_path: Path) -> None:
    shared = shared_names(REPO_ROOT / "src", REPO_ROOT / "ext")
    assert not shared, f"a module name in both src/ and ext/ freezes one over the other: {shared}"
    for planted in ("src/microdot.py", "src/freezefs.py"):
        (tmp_path / planted).parent.mkdir(exist_ok=True)
        (tmp_path / planted).write_text("", encoding="utf-8")
    shutil.copytree(REPO_ROOT / "ext", tmp_path / "ext")
    assert shared_names(tmp_path / "src", tmp_path / "ext") == ["freezefs", "microdot"]


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_no_device_image_holds_a_dynamic_import_site(images: list[Image], device: str) -> None:
    image = next(i for i in images if i.device == device)
    sites = [site for module in image.modules for site in image_sites(module)]
    assert not sites, f"{device}'s image loads dynamically (SPECIFICATION.md F.1):\n" + "\n".join(f"  {p}:{line} {what}" for p, line, what in sites)


def test_every_image_holds_its_generated_modules_and_website(images: list[Image]) -> None:
    for image in images:
        names = {m.name for m in image.modules}
        assert {f"sensortask_{image.device}", f"sensortask_{image.device}_main", f"sensortask_{image.device}_main_noautostart", _WEBSITE_MODULE, "asy_system_service", "microdot"} <= names, image.device


def test_outside_the_images_only_the_named_files_load_dynamically() -> None:
    found = unnamed_host_sites(repo_files())
    assert not found, "a dynamic load outside SPECIFICATION.md F.1's named list - make it static, or name it there:\n" + "\n".join(f"  {p}:{line} {what}" for p, line, what in found)


def test_the_named_list_mirrors_specification_f1() -> None:
    assert set(_NAMED_EXCEPTIONS) == f1_named_paths()


def test_a_planted_import_in_a_frozen_module_fails_naming_every_device_and_the_site(tmp_path: Path, website: Path) -> None:
    src = tmp_path / "src"
    shutil.copytree(REPO_ROOT / "src", src)
    planted = src / "asy_crc_checks.py"
    planted.write_text(planted.read_text(encoding="utf-8") + "\n_late = __import__('time')\n", encoding="utf-8")
    line = planted.read_text(encoding="utf-8").count("\n")
    (tmp_path / "gen").mkdir()
    hits = {i.device: [s for m in i.modules for s in image_sites(m)] for i in build_images(src, REPO_ROOT / "ext", website, tmp_path / "gen")}
    assert hits == {device: [("src/asy_crc_checks.py", line, "__import__")] for device in DEVICE_NAMES}


@pytest.mark.parametrize(("source", "what"), [("import importlib\n", "import importlib"), ("from importlib import util\n", "from importlib import"), ("exec('x = 1')\n", "exec"), ("eval('1')\n", "eval")])
def test_each_image_site_kind_is_caught(source: str, what: str) -> None:
    assert [s[2] for s in image_sites(_parse("m", "src/m.py", source))][:1] == [what]


def test_an_unnamed_host_site_fails_and_a_named_file_passes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "tools").mkdir()
    (tmp_path / "tools" / "loader.py").write_text("import importlib.util\nmod = __import__('json')\nrun = 'import importlib'\n", encoding="utf-8")
    (tmp_path / "buildgen").mkdir()
    (tmp_path / "buildgen" / "validate.py").write_text("import importlib.util\n", encoding="utf-8")
    monkeypatch.setattr(sys.modules[__name__], "REPO_ROOT", tmp_path)
    assert sorted(unnamed_host_sites(["tools/loader.py", "buildgen/validate.py"])) == [
        ("tools/loader.py", 1, "import importlib.util"),
        ("tools/loader.py", 2, "__import__"),
        ("tools/loader.py", 3, "import importlib"),
    ]


def test_an_injected_cycle_driver_edge_reexport_and_fram_import_each_fail() -> None:
    sources = {
        "asy_a_driver": "from asy_b_driver import B_Reader\nclass A_Reader:\n    pass\n",
        "asy_b_driver": "import asy_a_driver\nclass B_Reader:\n    pass\n",
        "asy_print_log": "import asy_fram_manager\n",
        "asy_fram_manager": "from asy_reexporter import helper\n",
        "asy_reexporter": "from asy_origin import helper\n",
        "asy_origin": "def helper():\n    pass\n",
    }
    found = graph_violations({name: _parse(name, f"src/{name}.py", text) for name, text in sources.items()})
    assert sorted(found) == sorted([
        "src/asy_a_driver.py:1: sensor driver asy_a_driver imports sensor driver asy_b_driver",
        "src/asy_b_driver.py:1: sensor driver asy_b_driver imports sensor driver asy_a_driver",
        "src/asy_print_log.py:1: asy_print_log imports asy_fram_manager at runtime",
        "src/asy_fram_manager.py:1: helper is imported from asy_reexporter, which does not define it",
        "import cycle: asy_a_driver -> asy_b_driver -> asy_a_driver",
    ])


def test_type_checking_imports_are_no_edges() -> None:
    source = "from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n    import asy_b\nelse:\n    import asy_c\n"
    assert [t for t, _, _ in static_imports(_parse("asy_a", "src/asy_a.py", source))] == ["typing", "asy_c"]
