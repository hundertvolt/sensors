"""A device script's ConfigManager over a production config file passes that module's full production
schema (SPECIFICATION.md C.5): a narrower one makes setup() drop every sibling field on its repair
write. Reads the scripts and src/ by AST; config_HWTEST_* scratch is exempt, any other unread site is named."""

import ast
import re
import shutil
from functools import cache
from pathlib import Path

import pytest

from buildgen.schema_ast import _eval_literal, extract_field_schemas
from buildgen.signals import WARN_SIGNALS

REPO_ROOT = Path(__file__).resolve().parent.parent
DEVICE_SCRIPTS = REPO_ROOT / "tests_hardware" / "device_scripts"
# A production config file's base name and the src/ module that owns its schema.
_OWNERS = {
    "SYSTEM": "asy_system_service.py",
    "WIFI": "asy_wifi_service.py",
    "NTP": "asy_ntp_client.py",
    "NOTIFY": "asy_notification_service.py",
    "SGP40": "asy_sgp40_driver.py",
    "BMP3XX": "asy_bmp3xx_driver.py",
    "ISL29125": "asy_isl29125_driver.py",
}
_PRODUCTION_RE = re.compile(r"^config_(" + "|".join(_OWNERS) + r")(?:_\w+)?\.cfg$")
_SCRATCH_RE = re.compile(r"^config_HWTEST_\w+\.cfg$")
# (script, its file-name expression): the reason a site this check cannot read is not checked. Empty: none today.
_UNREAD: "dict[tuple[str, str], str]" = {}
_RENDERED_SCHEMA = ("BENCH", "system_schema")  # rendered from schema_ast by the harness: production by construction

Schema = frozenset[tuple[object, ...]]


def _is_bench_schema(node: ast.expr) -> bool:
    return (
        isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name) and node.value.id == _RENDERED_SCHEMA[0]
        and isinstance(node.slice, ast.Constant) and node.slice.value == _RENDERED_SCHEMA[1]
    )


def _is_field_tuples(node: ast.expr) -> bool:
    # tuple((name,) + tuple(spec) for name, spec in BENCH["system_schema"].items()): the dict as ConfigManager's tuples.
    if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "tuple" and len(node.args) == 1 and isinstance(node.args[0], ast.GeneratorExp)):
        return False
    gen = node.args[0]
    comp = gen.generators[0] if len(gen.generators) == 1 else None
    elt = gen.elt
    if comp is None or comp.ifs or not (isinstance(comp.target, ast.Tuple) and len(comp.target.elts) == 2 and all(isinstance(e, ast.Name) for e in comp.target.elts)):
        return False
    name, spec = (e.id for e in comp.target.elts if isinstance(e, ast.Name))
    items = comp.iter
    return (
        isinstance(items, ast.Call) and isinstance(items.func, ast.Attribute) and items.func.attr == "items" and _is_bench_schema(items.func.value)
        and isinstance(elt, ast.BinOp) and isinstance(elt.op, ast.Add)
        and ast.dump(elt.left) == ast.dump(ast.Tuple([ast.Name(name, ast.Load())], ast.Load()))
        and isinstance(elt.right, ast.Call) and getattr(elt.right.func, "id", "") == "tuple" and len(elt.right.args) == 1 and getattr(elt.right.args[0], "id", "") == spec
    )


def _is_rendered(node: ast.expr, assigned: "dict[str, list[ast.expr]]") -> bool:
    # BENCH["system_schema"], its field-tuple form, either through cast(...) or a name bound to it (every binding).
    if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "cast" and len(node.args) == 2:
        return _is_rendered(node.args[1], assigned)
    if isinstance(node, ast.Name) and assigned.get(node.id):
        return all(_is_rendered(value, {}) for value in assigned[node.id])
    return _is_bench_schema(node) or _is_field_tuples(node)


def _argument(call: ast.Call, index: int, keyword: str) -> "ast.expr | None":
    if len(call.args) > index:
        return call.args[index]
    return next((k.value for k in call.keywords if k.arg == keyword), None)


def _assignments(tree: ast.Module) -> "dict[str, list[ast.expr]]":
    found: dict[str, list[ast.expr]] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            found.setdefault(node.targets[0].id, []).append(node.value)
        elif isinstance(node, ast.AnnAssign) and node.value is not None and isinstance(node.target, ast.Name):
            found.setdefault(node.target.id, []).append(node.value)
    return found


def _called_name(call: ast.Call) -> "str | None":
    func = call.func
    return func.attr if isinstance(func, ast.Attribute) else func.id if isinstance(func, ast.Name) else None


def _file_name(node: "ast.expr | None", consts: "dict[str, ast.expr]") -> "str | None":
    # The config file's base name from a literal path or one built as production builds it - cfg_path plus a literal
    # tail, or config_filename(<dir>, <name>) (src/asy_config_manager.py) - so neither form escapes the check.
    if node is None:
        return None
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return _file_name(node.right, consts)
    if isinstance(node, ast.Call) and _called_name(node) == "config_filename" and len(node.args) == 2:
        name = _literal(node.args[1], consts)
        return f"config_{name}.cfg" if isinstance(name, str) else None
    value = _literal(node, consts)
    return value.rsplit("/", 1)[-1] if isinstance(value, str) else None


def _literal(node: ast.expr, consts: "dict[str, ast.expr]") -> object:
    try:
        return _eval_literal(node, consts)
    except (TypeError, ValueError):
        return None  # computed at run time: nothing this check can name


def _module_consts(tree: ast.Module) -> "dict[str, ast.expr]":
    consts: dict[str, ast.expr] = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            consts[node.targets[0].id] = node.value
        elif isinstance(node, ast.AnnAssign) and node.value is not None and isinstance(node.target, ast.Name):
            consts[node.target.id] = node.value
    return consts


@cache
def _parse(source: str) -> ast.Module:
    # One parse per distinct script text: several checks read the same scripts, a bite's rewritten copy parses afresh.
    return ast.parse(source)


def _write(scripts: Path, name: str, body: str) -> None:
    (scripts / name).write_text(body, encoding="utf-8")


def findings(scripts: Path, repo_root: Path = REPO_ROOT, unread: "dict[tuple[str, str], str] | None" = None) -> "list[str]":
    listed = _UNREAD if unread is None else unread
    found: list[str] = []
    reached: set[tuple[str, str]] = set()
    for path in sorted(scripts.rglob("*.py")):
        tree = _parse(path.read_text(encoding="utf-8"))
        consts, assigned = _module_consts(tree), _assignments(tree)
        for call in (n for n in ast.walk(tree) if isinstance(n, ast.Call)):
            if _called_name(call) != "ConfigManager":
                continue
            where = f"{path.relative_to(scripts)}:{call.lineno}"
            path_node, schema_node = _argument(call, 0, "filename"), _argument(call, 1, "cfg_vals")
            filename = _file_name(path_node, consts)
            match = _PRODUCTION_RE.match(filename) if filename is not None else None
            if match is None:
                site = (path.relative_to(scripts).as_posix(), ast.unparse(path_node) if path_node is not None else "<no file name>")
                reached.add(site)
                if (filename is not None and _SCRATCH_RE.match(filename)) or site in listed:
                    continue
                problem = f"{site[1]}: its config file name is computed at run time" if filename is None else f"{filename} has no schema owner in _OWNERS"
                found.append(f"{where}: {problem}, so this check cannot read it - add it, or list it in _UNREAD with its reason")
                continue
            if schema_node is not None and _is_rendered(schema_node, assigned):
                continue
            try:
                schema = _eval_literal(schema_node, consts) if schema_node is not None else None
            except (TypeError, ValueError):
                schema = None
            if not isinstance(schema, tuple):
                found.append(f"{where}: {filename}'s schema cannot be resolved to a literal, so it cannot be checked against the production one")
                continue
            given = frozenset(tuple(field) if isinstance(field, tuple) else (field,) for field in schema)
            expected = production_schema(match.group(1), repo_root)
            if given != expected:
                missing = sorted(str(f[0]) for f in expected - given)
                found.append(f"{where}: {filename} is built with a schema that is not {match.group(1)}'s full production one (missing or different: {missing})")
    found.extend(f"{script}: {expr} is listed as unread but no ConfigManager builds it any more" for script, expr in sorted(set(listed) - reached))
    return found


def production_schema(name: str, repo_root: Path = REPO_ROOT) -> Schema:
    fields = {(field, *spec) for field, spec in extract_field_schemas(repo_root / "src" / _OWNERS[name]).items()}
    if name == "NOTIFY":
        # The notification signals' thresholds join its schema at construction (buildgen/signals.py's WARN_SIGNALS).
        fields |= {(s.name, s.field_type, s.default, s.min, s.max, None) for s in WARN_SIGNALS.values()}
    return frozenset(fields)


@pytest.fixture
def scripts_copy(tmp_path: Path) -> Path:
    return Path(shutil.copytree(DEVICE_SCRIPTS, tmp_path / "device_scripts"))


def test_every_script_manager_over_a_production_file_takes_the_full_schema() -> None:
    assert findings(DEVICE_SCRIPTS) == []


def test_the_check_reaches_a_live_production_site() -> None:
    # Not vacuous: at least one script builds a manager over a production file today.
    hits = 0
    for path in sorted(DEVICE_SCRIPTS.rglob("*.py")):
        tree = _parse(path.read_text(encoding="utf-8"))
        consts = _module_consts(tree)
        for call in (n for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "ConfigManager"):
            node = _argument(call, 0, "filename")
            try:
                value = _eval_literal(node, consts) if node is not None else None
            except (TypeError, ValueError):
                continue
            hits += isinstance(value, str) and _PRODUCTION_RE.match(value) is not None
    assert hits >= 1


def test_the_system_schema_matches_its_owner() -> None:
    assert production_schema("SYSTEM") == frozenset({("DebugLevel", "int", 0, 0, 5, None)})


def test_a_dropped_field_fails_naming_the_site(scripts_copy: Path) -> None:
    _write(scripts_copy, "zz_probe.py", 'import asy_config_manager as cm\n_S = (("SSID", "str", "", 0, 32, None),)\ncm.ConfigManager("config_WIFI.cfg", _S, "WIFI")\n')
    result = findings(scripts_copy)
    assert len(result) == 1 and result[0].startswith("zz_probe.py:3: config_WIFI.cfg") and "'Hostname'" in result[0], result


def test_an_extension_form_names_the_same_owner(scripts_copy: Path) -> None:
    _write(scripts_copy, "zz_probe.py", 'import asy_config_manager as cm\ncm.ConfigManager("config_SYSTEM_2.cfg", (), "SYSTEM_2")\n')
    assert [f.split(":", 2)[2].strip().split(" ")[0] for f in findings(scripts_copy)] == ["config_SYSTEM_2.cfg"]


def test_an_unresolvable_schema_over_a_production_file_fails(scripts_copy: Path) -> None:
    _write(scripts_copy, "zz_probe.py", 'import asy_config_manager as cm\ncm.ConfigManager("config_NTP.cfg", make_schema(), "NTP")\n')
    assert any("cannot be resolved" in f for f in findings(scripts_copy))


def test_a_scratch_file_and_a_rendered_schema_are_exempt(scripts_copy: Path) -> None:
    _write(scripts_copy, "zz_probe.py", 'import asy_config_manager as cm\ncm.ConfigManager("config_HWTEST_X.cfg", (), "HWTEST")\ncm.ConfigManager("config_SYSTEM.cfg", BENCH["system_schema"], "SYSTEM")\n')
    assert findings(scripts_copy) == []


def test_the_rendered_schema_as_field_tuples_counts_but_a_filtered_one_does_not(tmp_path: Path) -> None:
    whole = 'S = cast("ConfigSchema", tuple((n,) + tuple(v) for n, v in BENCH["system_schema"].items()))\n'
    filtered = 'S = tuple((n,) + tuple(v) for n, v in BENCH["system_schema"].items() if n != "DebugLevel")\n'
    for body, flagged in ((whole, False), (filtered, True)):
        _write(tmp_path, "zz_probe.py", f'import asy_config_manager as cm\n{body}cm.ConfigManager("config_SYSTEM.cfg", S, "SYSTEM")\n')
        assert any(f.startswith("zz_probe.py") for f in findings(tmp_path)) is flagged, body


@pytest.mark.parametrize(
    "path_expr",
    ['cfg_path + "config_WIFI.cfg"', 'cm.config_filename(cfg_path, "WIFI")', 'config_filename("", _NAME)', '"/flash/config_WIFI.cfg"'],
)
def test_a_computed_production_path_is_checked_too(tmp_path: Path, path_expr: str) -> None:
    # A path built the way production builds it names the same file, so it must not escape the check.
    _write(tmp_path, "zz_probe.py", f'import asy_config_manager as cm\n_NAME = "WIFI"\n_S = (("SSID", "str", "", 0, 32, None),)\ncm.ConfigManager({path_expr}, _S, "WIFI")\n')
    result = findings(tmp_path)
    assert len(result) == 1 and result[0].startswith("zz_probe.py:4: config_WIFI.cfg") and "'Hostname'" in result[0], result


def test_a_computed_file_name_is_named_until_listed_with_its_reason(tmp_path: Path) -> None:
    # A name this check cannot evaluate is a site it cannot check: named, unless listed with why; a stale listing fails.
    _write(tmp_path, "zz_probe.py", 'import asy_config_manager as cm\n_S = (("SSID", "str", "", 0, 32, None),)\ncm.ConfigManager(make_path(), _S, "WIFI")\n')
    result = findings(tmp_path)
    assert len(result) == 1 and result[0].startswith("zz_probe.py:3: make_path()") and "computed at run time" in result[0], result
    assert findings(tmp_path, unread={("zz_probe.py", "make_path()"): "a planted site"}) == []
    (tmp_path / "zz_probe.py").unlink()
    assert findings(tmp_path, unread={("zz_probe.py", "make_path()"): "a planted site"}) == ["zz_probe.py: make_path() is listed as unread but no ConfigManager builds it any more"]


def test_a_config_name_with_no_schema_owner_is_named(tmp_path: Path) -> None:
    # Only config_HWTEST_* scratch is exempt by name: any other file this check has no owner for is named.
    _write(tmp_path, "zz_probe.py", 'import asy_config_manager as cm\ncm.ConfigManager("config_PLANTED.cfg", (), "PLANTED")\n')
    result = findings(tmp_path)
    assert len(result) == 1 and result[0].startswith("zz_probe.py:2: config_PLANTED.cfg") and "no schema owner" in result[0], result
