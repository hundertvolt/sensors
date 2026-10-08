"""End-to-end: buildgen.generate.generate_device() over every devices/*.toml plus the novel and
multi-instance fixtures (SPECIFICATION.md Part L.1) - the validate -> sort -> generate pipeline from one TOML."""

# Correctness-proof scope: generated output is proven valid Python of the documented construction-order/wiring
# shape (ast.parse() + structural inspection); booting it is test_digital_twin_generated_boot.py's.

import ast
import builtins
import functools
import json
import re
import shutil
from datetime import datetime
from itertools import pairwise
from pathlib import Path
from typing import cast

import pytest
from _devices import DEVICE_NAMES
from _script_loader import load_script_module
from _toml_fixtures import base_doc, write_doc

import buildgen.generate as generate_module
from buildgen.codegen import _Ctx, _sgp40_status_vars, generate_boot_entry_source, generate_module_source, trigger_spread
from buildgen.definitions import definitions_for_toml
from buildgen.errors import BuildError, BuildInternalError
from buildgen.generate import GeneratedDevice, generate_device
from buildgen.graph import build_construction_order
from buildgen.model import DeviceModel, TomlDoc, instance_label
from buildgen.validate import _WDT_TIMEOUT_MS, SETTINGS_GROUPS, build_model, module_int_const
from buildgen.version import FIRMWARE_VERSION, WEBSITE_VERSION

_REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def src_dir(repo_root: Path) -> Path:
    return repo_root / "src"


@pytest.fixture
def ext_dir(repo_root: Path) -> Path:
    return repo_root / "ext"


@pytest.fixture
def fixtures_dir(repo_root: Path) -> Path:
    return repo_root / "tests_scripts" / "buildgen_fixtures"


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_real_device_generates_syntactically_valid_module(repo_root: Path, src_dir: Path, ext_dir: Path, device: str) -> None:
    result = generate_device(repo_root / "devices" / f"{device}.toml", src_dir, ext_dir)
    tree = ast.parse(result.module_source, filename=f"sensortask_{device}.py")
    assert any(isinstance(n, ast.AsyncFunctionDef) and n.name == "build_system" for n in tree.body)
    assert any(isinstance(n, ast.AsyncFunctionDef) and n.name == "main" for n in tree.body)
    ast.parse(result.boot_entry_source, filename=f"{device}_boot.py")


@functools.cache
def _real(device: str) -> GeneratedDevice:
    # One generation per real device for the read-only pins below; a test that mutates builds its own.
    return generate_device(_REPO_ROOT / "devices" / f"{device}.toml", _REPO_ROOT / "src", _REPO_ROOT / "ext")


def _body(source: str) -> "list[ast.stmt]":
    # A generated file's statements after its docstring.
    tree = ast.parse(source)
    first = tree.body[0]
    assert isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str)
    return tree.body[1:]


def _calls(nodes: "list[ast.stmt]", name: str) -> "list[ast.Call]":
    return [n for stmt in nodes for n in ast.walk(stmt) if isinstance(n, ast.Call) and ast.unparse(n.func) == name]


def _index(stmts: "list[ast.stmt]", text: str) -> int:
    (found,) = [i for i, stmt in enumerate(stmts) if ast.unparse(stmt) == text]
    return found


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_real_device_module_constructs_no_watchdog_and_its_boot_entry_exactly_one(device: str) -> None:
    # The boot entry arms the one WDT before any product import and hands it to main(); the module only takes it.
    result = _real(device)
    assert result.module_source.count("WDT(") == 0
    assert result.boot_entry_source.count("WDT(") == 1


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_real_device_boot_entry_arms_the_watchdog_as_its_first_statement(device: str) -> None:
    stmts = _body(_real(device).boot_entry_source)
    assert ast.unparse(stmts[0]) == "from machine import WDT"
    assert ast.unparse(stmts[1]) == f"watchdog = WDT(timeout={_WDT_TIMEOUT_MS})"


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_real_device_boot_entry_puts_frozen_code_first_before_any_product_import(device: str) -> None:
    # rp2 starts with sys.path ['', '.frozen', '/lib'] (ports/rp2/main.c:208, py/runtime.c:147-150, v1.29.0).
    stmts = _body(_real(device).boot_entry_source)
    assert len(_calls(stmts, "sys.path.insert")) == 1
    at = _index(stmts, "sys.path.insert(0, '.frozen')")
    assert at > _index(stmts, f"watchdog = WDT(timeout={_WDT_TIMEOUT_MS})")
    before = [stmt for stmt in stmts[:at] if isinstance(stmt, (ast.Import, ast.ImportFrom))]
    names = {alias.name for stmt in before if isinstance(stmt, ast.Import) for alias in stmt.names}
    names |= {stmt.module for stmt in before if isinstance(stmt, ast.ImportFrom) and stmt.module is not None}
    assert names <= {"machine", "sys"}, names


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_real_device_boot_entry_reserves_the_emergency_exception_buffer_before_the_device_import(device: str) -> None:
    # 77 B keeps a heap-exhaustion MemoryError's 24-character message whole (py/objexcept.c:485-523, v1.29.0).
    stmts = _body(_real(device).boot_entry_source)
    (call,) = _calls(stmts, "micropython.alloc_emergency_exception_buf")
    (size,) = call.args
    assert isinstance(size, ast.Constant) and isinstance(size.value, int) and size.value >= 77
    at = next(i for i, stmt in enumerate(stmts) if call in ast.walk(stmt))
    assert at < _index(stmts, f"from sensortask_{device} import main")


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_real_device_boot_entry_records_an_interrupt_before_the_watchdog_resets(device: str) -> None:
    # asyncio's loop catches only CancelledError and Exception (extmod/asyncio/core.py:153, 194, v1.29.0),
    # so a console Ctrl-C leaves asyncio.run(); the tail records it and re-raises, nothing else.
    stmts = _body(_real(device).boot_entry_source)
    assert _index(stmts, "from asy_system_service import RR_INTERRUPTED, write_reset_record") > _index(stmts, f"from sensortask_{device} import main")
    tail = stmts[-1]
    assert isinstance(tail, ast.Try)
    assert [ast.unparse(s) for s in tail.body] == ["asyncio.run(main(watchdog=watchdog))"]
    (handler,) = tail.handlers
    assert handler.type is not None and ast.unparse(handler.type) == "KeyboardInterrupt"
    assert handler.name is None
    assert [ast.unparse(s) for s in handler.body] == ["write_reset_record(RR_INTERRUPTED)", "raise"]
    assert not tail.orelse
    assert [ast.unparse(s) for s in tail.finalbody] == ["asyncio.new_event_loop()"]


def _shared_head(stmts: "list[ast.stmt]") -> "list[str]":
    # Up to gc.threshold(), without the watchdog lines and the interrupt record's import.
    own = {"from machine import WDT", f"watchdog = WDT(timeout={_WDT_TIMEOUT_MS})", "from asy_system_service import RR_INTERRUPTED, write_reset_record"}
    texts = [ast.unparse(stmt) for stmt in stmts]
    return [t for t in texts[: texts.index("gc.threshold(32768)") + 1] if t not in own]


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_real_device_boot_entry_variants_share_one_head_and_differ_only_in_the_watchdog_and_the_tail(device: str) -> None:
    autostart = generate_boot_entry_source(device)
    manual = generate_boot_entry_source(device, autostart=False)
    for name, source in (("main", autostart), ("main_noautostart", manual)):
        compile(source, f"sensortask_{device}_{name}.py", "exec")
        stmts = _body(source)
        assert _index(stmts, "gc.threshold(32768)") > _index(stmts, f"from sensortask_{device} import main")
    assert _shared_head(_body(autostart)) == _shared_head(_body(manual))
    stmts = _body(manual)
    assert not _calls(stmts, "WDT")
    assert not _calls(stmts, "asyncio.run")
    assert "RR_INTERRUPTED" not in manual
    # The printed manual start runs the identical main() under the identical watchdog.
    assert ast.unparse(stmts[-1]) == f"print({'from machine import WDT; asyncio.run(main(watchdog=WDT(timeout=' + str(_WDT_TIMEOUT_MS) + ')))'!r})"


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_real_device_manual_start_line_names_every_keyword_main_takes(device: str) -> None:
    manual = generate_boot_entry_source(device, autostart=False)
    match = re.search(r"^# main\(\) also takes (.+) \(keyword-only\)$", manual, re.MULTILINE)
    assert match is not None
    main = _function(_real(device).module_source, "main")
    assert match.group(1).split(", ") == [a.arg for a in main.args.kwonlyargs if a.arg != "watchdog"]


def _setup_names(source: str) -> "list[str]":
    # The bound setup methods _collect_setups() returns, in order.
    returned = next(n.value for n in ast.walk(_function(source, "_collect_setups")) if isinstance(n, ast.Return))
    assert isinstance(returned, ast.List)
    out = []
    for elt in returned.elts:
        assert isinstance(elt, ast.Attribute) and elt.attr == "setup" and isinstance(elt.value, ast.Name), ast.unparse(elt)
        out.append(elt.value.id)
    return out


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_real_device_hands_every_setup_to_one_list_in_the_fixed_order(device: str) -> None:
    # fram first (sysfunct's store logs to it), the three services, every other set-up module in
    # construction order, the webserver last (Part A.7); run_setups() feeds and collects between them.
    result = _real(device)
    model = result.model
    expected = [instance_label(k) for k in model.instances if k[0] == "fram"] + ["sysfunct", "conn", "ntp"]
    for node in model.construction_order:
        if isinstance(node, tuple) and node[0] != "fram":
            info = model.instances[node].driver_info
            assert info is not None
            if info.needs_setup:
                expected.append(instance_label(node))
    expected.append("webserver")
    setups = _setup_names(result.module_source)
    assert setups == expected
    sensors = [instance_label(spec.key) for spec in model.instances.values() if spec.driver_info is not None and spec.driver_info.kind == "sensor"]
    assert sensors
    assert set(sensors) <= set(setups)


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_real_device_module_neither_feeds_nor_collects_and_constructs_without_awaiting(device: str) -> None:
    # Every feed and every boot placement collect sits in SystemService (run_setups(), start_tasks());
    # the module keeps gc for MemFree's gc.mem_free().
    source = _real(device).module_source
    assert "gc.collect(" not in source
    assert "feed_watchdog(" not in source
    assert re.search(r"^import gc$", source, re.MULTILINE)
    assert not [n for n in ast.walk(_function(source, "build_system")) if isinstance(n, ast.Await)]


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_real_device_main_runs_the_boot_sequence_with_its_phase_marks(device: str) -> None:
    main = _function(_real(device).module_source, "main")
    assert [a.arg for a in main.args.kwonlyargs] == ["watchdog", "cfg_path", "debug", "web_host", "web_port"]
    assert main.args.kw_defaults[0] is None  # watchdog is required: no caller runs the device unguarded
    assert not main.args.args
    assert [ast.unparse(s) for s in main.body] == [
        "await build_system(watchdog=watchdog, cfg_path=cfg_path, debug=debug, web_host=web_host, web_port=web_port)",
        "sysfunct.boot_phase(BOOT_SETUP)",
        "await sysfunct.run_setups(_collect_setups())",
        "sysfunct.boot_phase(BOOT_TASKS)",
        "await sysfunct.start_tasks(_collect_task_starters())",
        "sysfunct.boot_phase(BOOT_TIMERS)",
        "await sysfunct.start_timers(_collect_trigger_starters(), _collect_timer_starters())",
        "sysfunct.boot_phase(BOOT_NTP)",
        "await ntp.ntp_force_sync()",
        "sysfunct.boot_phase(BOOT_DONE)",
        "await sysfunct.supervise_tasks()",
    ]


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_real_device_build_system_only_constructs_with_the_reset_reason_read_first(device: str) -> None:
    result = _real(device)
    fn = _function(result.module_source, "build_system")
    assert [a.arg for a in fn.args.kwonlyargs] == ["watchdog", "cfg_path", "debug", "web_host", "web_port"]
    assert fn.args.kw_defaults[0] is None
    assert ast.get_docstring(fn) == "Construct every module in the generated order (SPECIFICATION.md Part A.7)."
    stmts = [s for s in fn.body[1:] if not isinstance(s, ast.Global)]
    assert ast.unparse(stmts[0]) == "reset_reason = begin_boot()"
    assigned = [s.targets[0].id for s in stmts if isinstance(s, ast.Assign) and isinstance(s.targets[0], ast.Name)]
    assert assigned[-1] == "webserver"
    # Every bus precedes the first instance, so each I2C bus clears a held SDA before anything uses it.
    buses = list(_toml_tables(result.model.doc, "bus"))
    assert assigned[1 : 1 + len(buses)] == buses
    assert len(_calls(fn.body, "asy_i2c_driver.I2C")) == len([b for b in buses if b.startswith("i2c")])


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_real_device_system_service_takes_the_watchdog_the_stores_and_the_reset_reason(device: str) -> None:
    (call,) = _calls(_function(_real(device).module_source, "build_system").body, "SystemService")
    keywords = {str(k.arg): ast.unparse(k.value) for k in call.keywords}
    assert keywords["watchdog"] == "watchdog"
    assert keywords["level_setters"] == "_collect_level_setters"
    assert keywords["config_stores"] == "_collect_config_stores"
    assert keywords["reset_reason"] == "reset_reason"


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_real_device_collects_every_config_store_for_the_service_to_flush(device: str) -> None:
    # SystemService flushes the stores in its shutdown sequence; the module only lists them.
    source = _real(device).module_source
    assert "_flush_pending_configs" not in source
    fn = _function(source, "_collect_config_stores")
    assert fn.returns is not None and ast.unparse(fn.returns) == "list[cm.ConfigManager]"
    (loop,) = [n for n in ast.walk(fn) if isinstance(n, ast.For)]
    assert isinstance(loop.iter, ast.Tuple)
    assert [ast.unparse(e) for e in loop.iter.elts] == [*_collected_modules(source, "_collect_level_setters")]
    assert "# the accepted residual risk is power loss between a PUT and its flush (owner, 2026-09-26)" in str(ast.get_source_segment(source, fn))


def test_every_config_store_a_module_builds_sits_on_the_attribute_the_collector_reads(src_dir: Path) -> None:
    # Guard: _collect_config_stores() finds a store by getattr(module, "cfgmgr"), so a store kept under any
    # other name would silently miss the shutdown flush and the ConfigFaults list.
    calls, stored = 0, []
    for path in sorted(src_dir.glob("*.py")):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Call) and ast.unparse(node.func) == "ConfigManager":
                calls += 1
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call) and ast.unparse(node.value.func) == "ConfigManager":
                stored += [ast.unparse(target) for target in node.targets]
    assert calls > 0
    assert stored == ["self.cfgmgr"] * calls


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_real_device_system_command_callback_answers_the_service_for_every_command_word(src_dir: Path, device: str) -> None:
    fn = _function(_real(device).module_source, "_system_cmd_callback")
    answers = {}
    for stmt in fn.body[:-1]:
        assert isinstance(stmt, ast.If) and not stmt.orelse, ast.unparse(stmt)
        test = stmt.test
        assert isinstance(test, ast.Compare) and ast.unparse(test.left) == "cmd" and isinstance(test.comparators[0], ast.Constant)
        (ret,) = stmt.body
        assert isinstance(ret, ast.Return) and ret.value is not None
        answers[test.comparators[0].value] = ast.unparse(ret.value)
    assert ast.unparse(fn.body[-1]) == "return False"
    assert set(answers) == set(_src_tuple_const(src_dir / "asy_webserver_service.py", "_SYSTEM_CMDS"))
    assert answers == {
        "reboot": "await sysfunct.reboot_system()",
        "bootloader": "await sysfunct.reboot_bootloader()",
        "mempause": "sysfunct.pause_permanent_storage(300)",
        "resetconfig": "await sysfunct.reset_to_defaults()",
        "erasefram": "await sysfunct.erase_fram()",
    }


def _src_tuple_const(path: Path, name: str) -> "tuple[str, ...]":
    # A module-level `name = const((...))` read from source: an underscore const() is no attribute on MicroPython.
    for node in ast.parse(path.read_text(encoding="utf-8")).body:
        if isinstance(node, ast.Assign) and [ast.unparse(t) for t in node.targets] == [name]:
            assert isinstance(node.value, ast.Call) and ast.unparse(node.value.func) == "const"
            value = ast.literal_eval(node.value.args[0])
            assert isinstance(value, tuple)
            return value
    raise AssertionError(f"{path.name} has no {name}")


def _status_entries(source: str, name: str) -> "dict[str, str]":
    returned = next(n.value for n in ast.walk(_function(source, name)) if isinstance(n, ast.Return))
    assert isinstance(returned, ast.Dict)
    return {str(k.value): ast.unparse(v) for k, v in zip(returned.keys, returned.values, strict=True) if isinstance(k, ast.Constant)}


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_real_device_system_status_reports_every_system_key_in_order(device: str) -> None:
    result = _real(device)
    entries = _status_entries(result.module_source, "_system_status")
    has_fram = any(k[0] == "fram" for k in result.model.instances)
    expected = ["SysUptime", "BootSignature", "ResetReason", "ResetBits", "MemFree", *(["MemPaused"] if has_fram else []), "ConfigFaults", "ConfigUnpersisted", "LocalTime", "UTCTime"]
    assert list(entries) == expected
    assert entries["ResetReason"] == "sysfunct.get_reset_reason()"
    assert entries["ResetBits"] == "sysfunct.get_reset_bits()"
    assert entries["MemFree"] == "gc.mem_free()"
    assert entries["ConfigFaults"] == "list(sysfunct.get_config_faults())"
    assert entries["ConfigUnpersisted"] == "list(sysfunct.get_config_unpersisted())"


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_real_device_module_carries_no_assert_and_no_explicit_any(device: str) -> None:
    # Annotation-only globals give mypy the constructed type, so no narrowing check is left to emit.
    source = _real(device).module_source
    assert not [ast.unparse(n) for n in ast.walk(ast.parse(source)) if isinstance(n, ast.Assert)]
    assert not re.search(r"\bAny\b", source)


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_real_device_header_imports_the_boot_marks_and_the_watchdog_type_only(device: str) -> None:
    source = _real(device).module_source
    tree = ast.parse(source)
    runtime = [ast.unparse(n) for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))]
    assert "from asy_system_service import SystemService, begin_boot, BOOT_SETUP, BOOT_TASKS, BOOT_TIMERS, BOOT_NTP, BOOT_DONE" in runtime
    assert "import frozen_html" in runtime
    assert "from machine import WDT" not in runtime
    assert re.search(r"^import frozen_html$", source, re.MULTILINE), "the website mount import carries no suppression"
    (guarded,) = [n for n in tree.body if isinstance(n, ast.If) and ast.unparse(n.test) == "TYPE_CHECKING"]
    assert "from machine import WDT" in [ast.unparse(n) for n in guarded.body]
    assert "import asyncio" not in runtime


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_real_device_types_the_collectors_by_what_the_service_takes(device: str) -> None:
    source = _real(device).module_source
    returns = {}
    for name in ("_collect_setups", "_collect_task_starters", "_collect_timer_starters", "_collect_trigger_starters", "_collect_error_sources", "_collect_level_setters", "_collect_config_stores"):
        fn = _function(source, name)
        assert fn.returns is not None
        returns[name] = ast.unparse(fn.returns)
    assert returns == {
        "_collect_setups": "'list[SetupFct]'",
        "_collect_task_starters": "'list[TaskStarter]'",
        "_collect_timer_starters": "'list[TimerStarter]'",
        "_collect_trigger_starters": "'list[TimerStarter]'",
        "_collect_error_sources": "'list[ErrorSource]'",
        "_collect_level_setters": "'list[Callable[[int], bool]]'",
        "_collect_config_stores": "list[cm.ConfigManager]",
    }


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_real_device_expected_facts_name_the_setups_construction_and_phases_the_module_runs(device: str) -> None:
    # The boot-sequence oracle and the generated module agree, each derived on its own.
    result = _real(device)
    sequence = result.expected_facts["boot_sequence"]
    assert isinstance(sequence, dict)
    assert sequence["setups"] == _setup_names(result.module_source)
    assert sequence["construction"] == [node if isinstance(node, str) else instance_label(node) for node in build_construction_order(result.model)]
    main = _function(result.module_source, "main")
    named = []
    for stmt in main.body:
        assert isinstance(stmt, ast.Expr)
        call = stmt.value.value if isinstance(stmt.value, ast.Await) else stmt.value
        assert isinstance(call, ast.Call)
        named.append(ast.unparse(call.args[0]) if ast.unparse(call.func) == "sysfunct.boot_phase" else ast.unparse(call.func).rpartition(".")[2])
    assert sequence["phases"] == named


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_real_device_serves_the_settings_groups_of_the_one_table(device: str) -> None:
    # Guard: the build checks key collisions on the same SETTINGS_GROUPS rows codegen renders.
    source = _real(device).module_source
    for page in ("networking", "system"):
        expected = [(module, fields, dict([hook.split("=", 1)]) if hook else {}) for section, module, fields, hook in SETTINGS_GROUPS if section == page]
        assert _settings_groups(source, page) == expected


# The functions SPECIFICATION.md L.2 lets a generated module define, each with its reason there.
_EMITTED_FUNCTIONS = frozenset({"build_system", "main", "_gmtimestruct_to_dict", "_system_cmd_callback", "_notification_led_callback", "_notification_pause_callback", "_networking_status", "_system_status", "_notification_status"})


@functools.cache
def _all_sources(name: str) -> "tuple[str, str, str]":
    # The module and both boot entries of a real device or a buildgen fixture.
    toml = _REPO_ROOT / "devices" / f"{name}.toml" if name in DEVICE_NAMES else _REPO_ROOT / "tests_scripts" / "buildgen_fixtures" / f"{name}.toml"
    result = generate_device(toml, _REPO_ROOT / "src", _REPO_ROOT / "ext")
    return result.module_source, result.boot_entry_source, result.boot_entry_noautostart_source


_GENERATED = [*DEVICE_NAMES, "novel_combo", "multi_instance"]


@pytest.mark.parametrize("name", _GENERATED)
def test_generated_text_carries_no_noqa_and_no_type_ignore(name: str) -> None:
    for source in _all_sources(name):
        assert "# noqa" not in source
        assert "# type: ignore" not in source


@pytest.mark.parametrize("name", _GENERATED)
def test_generated_module_strips_to_valid_python_with_no_type_checking_name_left(name: str) -> None:
    strip = load_script_module(_REPO_ROOT / "scripts" / "_strip_type_checking.py", "_strip_type_checking")
    stripped = strip.strip_type_checking_blocks(_all_sources(name)[0])
    assert "TYPE_CHECKING" not in stripped
    compile(stripped, f"sensortask_{name}.py", "exec")


@pytest.mark.parametrize("name", _GENERATED)
def test_generated_module_defines_only_the_functions_l2_lists(name: str) -> None:
    tree = ast.parse(_all_sources(name)[0])
    defined = [n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    assert [d for d in defined if d not in _EMITTED_FUNCTIONS and not d.startswith(("_sgp_maintenance_status_", "_collect_"))] == []


def _runtime_module_names(tree: ast.Module) -> "set[str]":
    # Every name the module binds at runtime: imports, assignments, annotation-only globals and defs,
    # never one imported under TYPE_CHECKING (it does not exist on the device).
    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            names |= {(a.asname or a.name).split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom):
            names |= {a.asname or a.name for a in node.names}
        elif isinstance(node, ast.Assign):
            names |= {t.id for t in node.targets if isinstance(t, ast.Name)}
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            names.add(node.name)
        elif isinstance(node, ast.Try):
            names |= {t.id for sub in ast.walk(node) if isinstance(sub, ast.Assign) for t in sub.targets if isinstance(t, ast.Name)}
            names |= {a.asname or a.name for sub in ast.walk(node) if isinstance(sub, ast.ImportFrom) for a in sub.names}
    return names


def _loads_outside_annotations(fn: "ast.FunctionDef | ast.AsyncFunctionDef") -> "list[ast.Name]":
    skip = {id(sub) for stmt in ast.walk(fn) if isinstance(stmt, ast.AnnAssign) for sub in ast.walk(stmt.annotation)}
    return [n for stmt in fn.body for n in ast.walk(stmt) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load) and id(n) not in skip]


@pytest.mark.parametrize("name", _GENERATED)
def test_every_name_a_generated_function_reads_is_bound(name: str) -> None:
    # The class of the unassigned bare-driver global: every load is a parameter, a local, a module name or a builtin.
    tree = ast.parse(_all_sources(name)[0])
    module_names = _runtime_module_names(tree) | set(dir(builtins))
    unresolved = []
    for fn in (n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))):
        local = {a.arg for a in [*fn.args.posonlyargs, *fn.args.args, *fn.args.kwonlyargs]}
        local |= {n.id for n in ast.walk(fn) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store)}
        unresolved += [f"{fn.name}: {n.id}" for n in _loads_outside_annotations(fn) if n.id not in local | module_names]
    assert unresolved == []


def test_an_optional_value_wiring_field_left_out_renders_no_keyword(tmp_path: Path, src_dir: Path, ext_dir: Path) -> None:
    # The tag's own path for absence: no keyword, so the constructor default applies. No driver in src/
    # declares an optional one today, so sgp40's humidity tag is staged as optional in a src/ copy.
    src = tmp_path / "src"
    shutil.copytree(src_dir, src)
    path = src / "asy_sgp40_driver.py"
    text = path.read_text(encoding="utf-8")
    assert text.count("# @value-wiring humidity_source humidity required") == 1
    path.write_text(text.replace("# @value-wiring humidity_source humidity required", "# @value-wiring humidity_source humidity optional"), encoding="utf-8")
    doc = base_doc()
    sgp40 = next(i for i in doc["instance"] if i["driver"] == "sgp40")
    del sgp40["wiring"]["humidity_source"]
    source = generate_device(write_doc(tmp_path, "optional_value_wiring", doc), src, ext_dir).module_source
    compile(source, "sensortask_optional_value_wiring.py", "exec")
    (call,) = _calls(_function(source, "build_system").body, "SGP40_Reader")
    assert [k.arg for k in call.keywords if k.arg in ("temperature", "humidity")] == ["temperature"]


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_real_device_passes_each_wired_value_in_its_tag_order(device: str) -> None:
    # Guard: every value-wiring field the TOML wires reaches the constructor, in the driver's tag order.
    result = _real(device)
    built = {s.targets[0].id: s.value for s in _function(result.module_source, "build_system").body if isinstance(s, ast.Assign) and isinstance(s.targets[0], ast.Name) and isinstance(s.value, ast.Call)}
    wired = [spec for spec in result.model.instances.values() if spec.value_wiring_schema]
    assert wired, device
    for spec in wired:
        kwargs = {f.kwarg for f in spec.value_wiring_schema}
        passed = [k.arg for k in built[spec.label].keywords if k.arg in kwargs]
        assert passed == [f.kwarg for f in spec.value_wiring_schema if f.toml_field in spec.wiring], spec.label


def test_a_wiring_tag_naming_another_target_renders_that_keyword(tmp_path: Path, src_dir: Path, ext_dir: Path) -> None:
    # Device-level wiring renders each consumer's own tag target, never a literal keyword.
    src = tmp_path / "src"
    shutil.copytree(src_dir, src)
    path = src / "asy_system_service.py"
    text = path.read_text(encoding="utf-8")
    assert text.count("# @wiring fram_target FRAMManager log optional kwarg") == 1
    path.write_text(text.replace("# @wiring fram_target FRAMManager log optional kwarg", "# @wiring fram_target FRAMManager store optional kwarg"), encoding="utf-8")
    source = generate_device(write_doc(tmp_path, "store_target", base_doc()), src, ext_dir).module_source
    (call,) = _calls(_function(source, "build_system").body, "SystemService")
    keywords = {str(k.arg): ast.unparse(k.value) for k in call.keywords}
    assert keywords.get("store") == "log_fram"
    assert "log" not in keywords


def test_a_device_without_any_bus_generates(tmp_path: Path, src_dir: Path, ext_dir: Path) -> None:
    # validate.py accepts a device with no [bus.*] table; codegen reads the same default.
    doc = base_doc()
    del doc["bus"]
    doc["instance"] = [{"driver": "neopixel", "pin": 15}]
    del doc["device"]["wiring"]["fram_target"]
    result = generate_device(write_doc(tmp_path, "busless", doc), src_dir, ext_dir)
    compile(result.module_source, "sensortask_busless.py", "exec")
    assert not [n for n in ast.walk(ast.parse(result.module_source)) if isinstance(n, ast.Call) and ast.unparse(n.func).startswith("asy_") and ast.unparse(n.func).endswith(("I2C", "SPI", "UART"))]


def _uart_bus_calls(source: str) -> "dict[str, str]":
    fn = _function(source, "build_system")
    return {s.targets[0].id: ast.unparse(s.value) for s in fn.body if isinstance(s, ast.Assign) and isinstance(s.targets[0], ast.Name) and isinstance(s.value, ast.Call) and ast.unparse(s.value.func) == "asy_uart_driver.UART"}


def _uart_link_model(src_dir: Path) -> DeviceModel:
    # The device carrying a uart_link pair, chosen by that property, never by name.
    (device,) = [d for d in DEVICE_NAMES if any(k[0] == "uart_link" for k in _real(d).model.instances)]
    model = build_model(_REPO_ROOT / "devices" / f"{device}.toml", src_dir)
    build_construction_order(model)
    return model


def test_a_link_naming_a_crc_mode_gets_that_check_on_its_uart_bus_and_its_import(src_dir: Path) -> None:
    # The CRC is the bus's (A.7): a link's crc key reaches the UART constructor, "none" stays absent.
    model = _uart_link_model(src_dir)
    links = [s for s in model.instances.values() if s.driver == "uart_link"]
    links[0].fields["crc"] = "crc16"
    links[1].fields["crc"] = "none"
    source = generate_module_source(model, model.construction_order, "2026-01-01T00:00:00Z", src_dir)
    calls = _uart_bus_calls(source)
    assert calls[str(links[0].fields["bus"])].endswith(", crc=CRC16())")
    assert "crc=" not in calls[str(links[1].fields["bus"])]
    assert [ast.unparse(n) for n in ast.parse(source).body if isinstance(n, ast.ImportFrom) and n.module == "asy_crc_checks"] == ["from asy_crc_checks import CRC16"]


def test_a_crc_mode_the_validator_never_checked_is_an_internal_error(src_dir: Path) -> None:
    model = _uart_link_model(src_dir)
    next(s for s in model.instances.values() if s.driver == "uart_link").fields["crc"] = "crc32"
    with pytest.raises(BuildInternalError, match="crc mode 'crc32' reached codegen unchecked"):
        generate_module_source(model, model.construction_order, "2026-01-01T00:00:00Z", src_dir)


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_real_device_without_a_crc_key_imports_no_crc_and_passes_none(device: str) -> None:
    # Guard: no shipped link names a CRC (the UART wire format is untouched), so no bus gets one.
    source = _real(device).module_source
    assert "crc=" not in source
    assert "asy_crc_checks" not in source


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_real_device_passes_each_uart_bus_its_stated_rx_ring(device: str) -> None:
    result = _real(device)
    calls = _uart_bus_calls(result.module_source)
    for bus, table in _toml_tables(result.model.doc, "bus").items():
        if bus.startswith("uart"):
            stated = table.get("rx_ring")
            assert (f"rx_ring={stated}" in calls[bus]) if stated is not None else ("rx_ring=" not in calls[bus]), calls[bus]


def test_an_unstated_rx_ring_is_left_to_the_uart_constructor_default(src_dir: Path) -> None:
    model = _uart_link_model(src_dir)
    buses = [str(s.fields["bus"]) for s in model.instances.values() if s.driver == "uart_link"]
    _toml_tables(model.doc, "bus")[buses[0]]["rx_ring"] = 4096
    _toml_tables(model.doc, "bus")[buses[1]].pop("rx_ring", None)
    calls = _uart_bus_calls(generate_module_source(model, model.construction_order, "2026-01-01T00:00:00Z", src_dir))
    assert "rx_ring=4096" in calls[buses[0]]
    assert "rx_ring=" not in calls[buses[1]]


def _toml_tables(doc: TomlDoc, key: str) -> "dict[str, TomlDoc]":
    tables = doc.get(key, {})
    assert isinstance(tables, dict) and all(isinstance(table, dict) for table in tables.values())
    return cast("dict[str, TomlDoc]", tables)


def _uart_link_lines(source: str) -> "dict[str, ast.Call]":
    fn = _function(source, "build_system")
    return {s.targets[0].id: s.value for s in fn.body if isinstance(s, ast.Assign) and isinstance(s.targets[0], ast.Name) and isinstance(s.value, ast.Call) and ast.unparse(s.value.func) == "UARTLinkDriver"}


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_real_device_hands_each_link_its_transfer_limits_as_one_object(src_dir: Path, device: str) -> None:
    # payload_size, timeout and chunk_bytes are the protocol's defaults (no TOML key); the receive cap is the TOML's.
    result = _real(device)
    links = {instance_label(k): s for k, s in result.model.instances.items() if k[0] == "uart_link"}
    calls = _uart_link_lines(result.module_source)
    assert set(calls) == set(links)
    defaults = [module_int_const(src_dir, "asy_uart_comm.py", name) for name in ("_DEFAULT_PAYLOAD_SIZE", "_DEFAULT_TIMEOUT_MS", "_DEFAULT_CHUNK_BYTES")]
    for var, call in calls.items():
        (limits,) = [ast.unparse(k.value) for k in call.keywords if k.arg == "limits"]
        cap = links[var].fields.get("max_transfer_bytes", module_int_const(src_dir, "asy_uart_comm.py", "_DEFAULT_MAX_TRANSFER_BYTES"))
        assert limits == f"TransferLimits({', '.join(str(v) for v in defaults)}, {cap})"
    if calls:
        assert "from asy_uart_comm import TransferLimits" in result.module_source


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_real_device_links_keep_the_protocol_default_limits(src_dir: Path, device: str) -> None:
    # Guard: the UART wire format is untouched, so every shipped link's cap is the protocol default.
    for spec in _real(device).model.instances.values():
        if spec.driver == "uart_link":
            assert spec.fields.get("max_transfer_bytes") in (None, module_int_const(src_dir, "asy_uart_comm.py", "_DEFAULT_MAX_TRANSFER_BYTES"))


def test_a_crc_mode_named_on_both_ends_of_the_bench_link_reaches_both_uart_buses(tmp_path: Path, src_dir: Path, ext_dir: Path) -> None:
    # The device carrying the uart_link pair, its TOML copied with crc = "crc16" on both links.
    (device,) = [d for d in DEVICE_NAMES if any(k[0] == "uart_link" for k in _real(d).model.instances)]
    text = (_REPO_ROOT / "devices" / f"{device}.toml").read_text(encoding="utf-8")
    edited = re.sub(r'^(driver = "uart_link"\n)', r'\1crc = "crc16"\n', text, flags=re.MULTILINE)
    assert edited.count('crc = "crc16"') == 2
    path = tmp_path / f"{device}.toml"
    path.write_text(edited, encoding="utf-8")
    source = generate_device(path, src_dir, ext_dir).module_source
    calls = _uart_bus_calls(source)
    assert len(calls) == 2
    assert all(call.endswith(", crc=CRC16())") for call in calls.values()), calls
    assert "from asy_crc_checks import CRC16" in source


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_real_device_boot_entry_imports_the_right_module(repo_root: Path, src_dir: Path, ext_dir: Path, device: str) -> None:
    result = generate_device(repo_root / "devices" / f"{device}.toml", src_dir, ext_dir)
    assert f"from sensortask_{device} import main" in result.boot_entry_source


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_real_device_embeds_and_reports_version_and_build_date_exactly_once(repo_root: Path, src_dir: Path, ext_dir: Path, device: str) -> None:
    # Part L.7: buildgen.version is the one source of truth for the two version constants, and
    # the build date is explicitly injected rather than computed on-device - which is what lets
    # this assert an exact match instead of a moving "now".
    result = generate_device(repo_root / "devices" / f"{device}.toml", src_dir, ext_dir, build_date="2026-09-12T10:00:00Z")
    assert result.module_source.count("_FIRMWARE_VERSION = const(") == 1
    assert result.module_source.count("_WEBSITE_VERSION = const(") == 1
    assert result.module_source.count("_BUILD_DATE = const(") == 1
    assert f"_FIRMWARE_VERSION = const({FIRMWARE_VERSION!r})" in result.module_source
    assert f"_WEBSITE_VERSION = const({WEBSITE_VERSION!r})" in result.module_source
    assert "_BUILD_DATE = const('2026-09-12T10:00:00Z')" in result.module_source
    assert 'build_info={"FirmwareVersion": _FIRMWARE_VERSION, "WebsiteVersion": _WEBSITE_VERSION, "BuildDate": _BUILD_DATE}' in result.module_source
    # Regression guard against an earlier, corrected design: the version no longer
    # lives on GET /status's "system" section, so build_info above is its only key.
    assert result.module_source.count('"FirmwareVersion": _FIRMWARE_VERSION') == 1


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_real_device_defaults_to_a_real_current_build_date_when_none_is_given(repo_root: Path, src_dir: Path, ext_dir: Path, device: str) -> None:
    result = generate_device(repo_root / "devices" / f"{device}.toml", src_dir, ext_dir)
    match = re.search(r"_BUILD_DATE = const\('([^']+)'\)", result.module_source)
    assert match is not None
    datetime.fromisoformat(match.group(1))  # raises ValueError if malformed; "Z" is UTC, not naive


def _function(source: str, name: str) -> "ast.FunctionDef | ast.AsyncFunctionDef":
    tree = ast.parse(source)
    return next(n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name)


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_real_device_main_starts_read_triggers_apart_from_the_timer_starters(repo_root: Path, src_dir: Path, ext_dir: Path, device: str) -> None:
    result = generate_device(repo_root / "devices" / f"{device}.toml", src_dir, ext_dir)
    main = ast.unparse(_function(result.module_source, "main"))
    assert "await sysfunct.start_timers(_collect_trigger_starters(), _collect_timer_starters())" in main
    # start_timers() awaits its own stagger inline, so the old completion flag has no reader left.
    assert "timers_running" not in result.module_source
    assert "ThreadSafeFlag" not in result.module_source


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_real_device_declares_every_global_by_the_class_build_system_constructs(device: str) -> None:
    # Annotation only: the name is unbound until build_system() runs (py/compile.c:2029-2039, v1.29.0),
    # so a reader before the build gets an error rather than a None it might mistake for a module.
    tree = ast.parse(_real(device).module_source)
    annotated = [(n.target.id, n) for n in tree.body if isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name)]
    declared = {name: n for name, n in annotated if n.value is None}
    assert all(name.startswith("_FIELD_WARN_") for name, n in annotated if n.value is not None)
    built = _function(_real(device).module_source, "build_system")
    (global_stmt,) = [n for n in built.body if isinstance(n, ast.Global)]
    constructed = {
        n.targets[0].id: ast.unparse(n.value.func)
        for n in ast.walk(built)
        if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name) and isinstance(n.value, ast.Call) and n.targets[0].id in global_stmt.names
    }
    assert constructed, device
    assert list(declared) == global_stmt.names
    assert {var: ast.unparse(n.annotation) for var, n in declared.items()} == constructed
    assert "watchdog" not in declared


# Each warn signal's schema line as the generator rendered it before its catalog moved out of codegen.
_WARN_SCHEMA_LINES = {
    "warn_co2": '_FIELD_WARN_CO2: cm.ConfigSchema = (("WarnCO2", "int", 1600, 0, 3000, None),)',
    "warn_voc": '_FIELD_WARN_VOC: cm.ConfigSchema = (("WarnVOC", "int", 350, 0, 500, None),)',
    "warn_hum": '_FIELD_WARN_HUM: cm.ConfigSchema = (("WarnHum", "float", 65.0, 0.0, 100.0, None),)',
}


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_real_device_renders_each_wired_warn_schema_unchanged_and_bare_annotated(device: str) -> None:
    # cm is a runtime import, so its ConfigSchema needs no quotes; the values are the one catalog's.
    result = _real(device)
    wired = [k for s in result.model.instances.values() if s.driver == "notification" for k in s.wiring if k.startswith("warn_")]
    lines = [line for line in result.module_source.splitlines() if line.startswith("_FIELD_WARN_")]
    assert lines == [_WARN_SCHEMA_LINES[k] for k in wired]


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_real_device_networking_status_reads_one_wifi_snapshot_and_no_radio(repo_root: Path, src_dir: Path, ext_dir: Path, device: str) -> None:
    # One response, one consistent snapshot: every address and the RSSI come from conn.get_data()'s tuple.
    fn = _function(generate_device(repo_root / "devices" / f"{device}.toml", src_dir, ext_dir).module_source, "_networking_status")
    calls = [ast.unparse(n.func) for n in ast.walk(fn) if isinstance(n, ast.Call)]
    assert calls.count("conn.get_data") == 1
    assert not [c for c in calls if c.startswith("conn.") and c not in ("conn.get_data", "conn.get_wifi_uptime")], calls
    snapshot = next(n.targets[0].id for n in ast.walk(fn) if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name) and "conn.get_data()" in ast.unparse(n.value))
    returned = next(n.value for n in ast.walk(fn) if isinstance(n, ast.Return))
    assert isinstance(returned, ast.Dict)
    entries = {k.value: ast.unparse(v) for k, v in zip(returned.keys, returned.values, strict=True) if isinstance(k, ast.Constant)}
    assert "IP" not in entries
    fields = {"IPv4": "IP", "Subnet": "Subnet", "Gateway": "Gateway", "DNS": "DNS", "RSSI": "RSSI", "Mode": "Mode", "Connected": "Connected", "WifiTS": "TS"}
    assert {key: entries[key] for key in fields} == {key: f"{snapshot}.{field}" for key, field in fields.items()}


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_real_device_networking_status_reads_the_webservers_drop_window(repo_root: Path, src_dir: Path, ext_dir: Path, device: str) -> None:
    fn = _function(generate_device(repo_root / "devices" / f"{device}.toml", src_dir, ext_dir).module_source, "_networking_status")
    returned = next(n.value for n in ast.walk(fn) if isinstance(n, ast.Return))
    assert isinstance(returned, ast.Dict)
    entries = {k.value: ast.unparse(v) for k, v in zip(returned.keys, returned.values, strict=True) if isinstance(k, ast.Constant)}
    assert entries["HTTPDropped"] == "await webserver.get_dropped_count()"


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_real_device_led_callback_takes_the_validated_values_and_only_signals(repo_root: Path, src_dir: Path, ext_dir: Path, device: str) -> None:
    # The webserver validates R/G/B/T against its own schemas, so the callback is a plain hand-over.
    source = generate_device(repo_root / "devices" / f"{device}.toml", src_dir, ext_dir).module_source
    fn = _function(source, "_notification_led_callback")
    assert ast.unparse(fn.args) == "r: int, g: int, b: int, t: float"
    assert fn.returns is not None and ast.unparse(fn.returns) == "bool"
    assert [ast.unparse(n) for n in fn.body] == ["return neopixel.led_signal(r, g, b, t)"]
    assert "_FIELD_LED_" not in source


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_real_device_webserver_reads_the_system_uptime_for_its_drop_window(repo_root: Path, src_dir: Path, ext_dir: Path, device: str) -> None:
    source = generate_device(repo_root / "devices" / f"{device}.toml", src_dir, ext_dir).module_source
    call = next(n for n in ast.walk(ast.parse(source)) if isinstance(n, ast.Call) and ast.unparse(n.func) == "WebserverService")
    assert [k.arg for k in call.keywords] == ["routes", "serving", "uptime_s", "static", "log"]
    assert next(ast.unparse(k.value) for k in call.keywords if k.arg == "uptime_s") == "sysfunct.get_uptime"


def _settings_groups(source: str, page: str) -> "list[tuple[str, tuple[str, ...], dict[str, str]]]":
    # (module, field names, hook keywords) of each SettingsGroup the generated RouteSources lists for `page`.
    routes = next(n for n in ast.walk(ast.parse(source)) if isinstance(n, ast.Call) and ast.unparse(n.func) == "RouteSources")
    settings = next(k.value for k in routes.keywords if k.arg == "settings")
    assert isinstance(settings, ast.Dict)
    groups = next(v for k, v in zip(settings.keys, settings.values, strict=True) if isinstance(k, ast.Constant) and k.value == page)
    assert isinstance(groups, ast.List)
    out = []
    for call in groups.elts:
        assert isinstance(call, ast.Call) and ast.unparse(call.func) == "SettingsGroup"
        out.append((ast.unparse(call.args[0]), ast.literal_eval(call.args[1]), {str(k.arg): ast.unparse(k.value) for k in call.keywords}))
    return out


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_real_device_networking_settings_publish_the_hotspot_password_and_the_dns_fallback(repo_root: Path, src_dir: Path, ext_dir: Path, device: str) -> None:
    # HotspotPW reconnects with the identity group; DNSFallback needs no hook, the next NTP attempt reads it.
    source = generate_device(repo_root / "devices" / f"{device}.toml", src_dir, ext_dir).module_source
    assert _settings_groups(source, "networking") == [
        ("conn", ("SSID", "PW", "Country", "Hostname", "HotspotPW"), {"post_fct": "conn.reconnect_wifi"}),
        ("conn", ("LEDWifiOn",), {}),
        ("ntp", ("NTPHost", "NTPOffset", "NTPInterval"), {"post_asy_fct": "ntp.ntp_force_sync"}),
        ("ntp", ("DNSFallback",), {}),
    ]


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_real_device_settings_groups_accept_exactly_what_their_page_shows_as_writable(repo_root: Path, src_dir: Path, ext_dir: Path, device: str) -> None:
    # One source: the page's writable fields are what its PUT route's settings groups accept, group by
    # group on Networking (HotspotPW in identity, DNSFallback alone) and as one set on System.
    toml = repo_root / "devices" / f"{device}.toml"
    source = generate_device(toml, src_dir, ext_dir).module_source
    sections = {s["key"]: s for s in json.loads(json.dumps(definitions_for_toml(toml, src_dir)))["sections"]}
    shown = {page: [tuple(f["key"] for f in g["fields"] if f.get("kind") != "readonly" and not f.get("dispatch")) for g in sections[page]["groups"] if "fields" in g] for page in ("networking", "system")}
    accepted = {page: [fields for _module, fields, _hooks in _settings_groups(source, page)] for page in ("networking", "system")}
    assert shown["networking"] == accepted["networking"]
    assert sorted(k for group in shown["system"] for k in group) == sorted(k for group in accepted["system"] for k in group)


def _src_with_read_triggers(src_dir: Path, tmp_path: Path, drivers: "tuple[str, ...]") -> Path:
    # A src/ copy in which exactly the named drivers' reader classes declare their own read triggers.
    copy = tmp_path / "src"
    shutil.copytree(src_dir, copy)
    for path in copy.glob("asy_*_driver.py"):
        text = path.read_text()
        path.write_text(re.sub(r"^    def get_trigger_starters\(self\)[^\n]*:\n        return \[[^\n]*\]\n\n", "", text, flags=re.MULTILINE))
    for driver in drivers:
        path = copy / f"asy_{driver}_driver.py"
        text = path.read_text()
        match = re.search(r"^class \w+_Reader\(SensorReader(?:Config)?\):\n", text, re.MULTILINE)
        assert match is not None, driver
        method = "    def get_trigger_starters(self):\n        return [self.start_timer]\n\n"
        path.write_text(text[: match.end()] + method + text[match.end() :])
    return copy


def _trigger_modules(source: str) -> "list[str]":
    func = _function(source, "_collect_trigger_starters")
    loops = [n for n in ast.walk(func) if isinstance(n, ast.For)]
    if not loops:
        return []
    assert isinstance(loops[0].iter, ast.Tuple)
    return [elt.id for elt in loops[0].iter.elts if isinstance(elt, ast.Name)]


@pytest.mark.parametrize(
    ("device", "expected"),
    # dev: sgp40 and isl29125 share i2c1, bmp3xx sits alone on i2c0 - slots 0, 250, 500 ms;
    # wozi: sgp40 and bmp3xx share i2c1 (scd30 keeps its own tick) - slots 0, 333 ms.
    [("dev", ["sgp40", "bmp3xx", "isl29125"]), ("wozi", ["sgp40", "bmp3xx"])],
)
def test_read_triggers_are_collected_with_bus_sharing_readers_furthest_apart(repo_root: Path, src_dir: Path, ext_dir: Path, tmp_path: Path, device: str, expected: "list[str]") -> None:
    src = _src_with_read_triggers(src_dir, tmp_path, ("bmp3xx", "isl29125", "sgp40"))
    result = generate_device(repo_root / "devices" / f"{device}.toml", src, ext_dir)
    assert _trigger_modules(result.module_source) == expected
    assert "scd30" not in _trigger_modules(result.module_source)


def _collected_modules(source: str, collector: str) -> "list[str]":
    (loop,) = [n for n in ast.walk(_function(source, collector)) if isinstance(n, ast.For)]
    assert isinstance(loop.iter, ast.Tuple)
    return [elt.id for elt in loop.iter.elts if isinstance(elt, ast.Name)]


def _fram_var(result: GeneratedDevice) -> str:
    (key,) = [key for key in result.model.instances if key[0] == "fram"]
    return instance_label(key)


@pytest.mark.parametrize("device", DEVICE_NAMES)
@pytest.mark.parametrize("collector", ["_collect_task_starters", "_collect_timer_starters"])
def test_real_device_collects_the_fram_managers_starters(repo_root: Path, src_dir: Path, ext_dir: Path, device: str, collector: str) -> None:
    # A declared chip that fails setup escalates through its supervised task like any other chip.
    result = generate_device(repo_root / "devices" / f"{device}.toml", src_dir, ext_dir)
    assert _fram_var(result) in _collected_modules(result.module_source, collector)


@pytest.mark.parametrize("collector", ["_collect_task_starters", "_collect_timer_starters"])
def test_a_fixture_without_fram_target_still_collects_its_declared_fram(fixtures_dir: Path, src_dir: Path, ext_dir: Path, collector: str) -> None:
    result = generate_device(fixtures_dir / "multi_instance.toml", src_dir, ext_dir)
    assert "storage=None" in result.module_source  # [device.wiring].fram_target unwired
    assert _fram_var(result) in _collected_modules(result.module_source, collector)


def test_bus_spread_takes_the_largest_group_first_and_keeps_construction_order_on_ties() -> None:
    order = trigger_spread([("a", "i2c0"), ("b", "i2c1"), ("c", "i2c1"), ("d", "i2c0"), ("e", "i2c1"), ("f", "spi0")])
    assert order == ["b", "a", "f", "c", "d", "e"]
    assert trigger_spread([]) == []


def test_a_device_whose_readers_declare_no_read_triggers_collects_none(repo_root: Path, src_dir: Path, ext_dir: Path, tmp_path: Path) -> None:
    src = _src_with_read_triggers(src_dir, tmp_path, ())
    for path in src.glob("asy_*_driver.py"):
        assert "def get_trigger_starters" not in path.read_text(), path.name
    result = generate_device(repo_root / "devices" / "dev.toml", src, ext_dir)
    assert _trigger_modules(result.module_source) == []
    assert ast.unparse(_function(result.module_source, "_collect_trigger_starters")).rstrip().endswith("return []")


def test_novel_combo_fixture_generates_successfully(fixtures_dir: Path, src_dir: Path, ext_dir: Path) -> None:
    # The mandatory synthetic novel-combination fixture (Part L.1's criterion 2): existing
    # drivers in a layout no real device uses - two SCD30s, an SGP40 compensated from each,
    # BMP3xx at its alternate address - proving generality beyond the six hand-verified files.
    result = generate_device(fixtures_dir / "novel_combo.toml", src_dir, ext_dir)
    ast.parse(result.module_source)
    ast.parse(result.boot_entry_source)
    assert "scd30_primary" in result.module_source
    assert "scd30_secondary" in result.module_source
    assert "SGP40_Reader(i2c1, temperature=ValueRef(scd30_secondary, 'Temp')" in result.module_source
    assert "humidity=ValueRef(scd30_primary, 'Hum')" in result.module_source
    # Only warn_co2 is wired - warn_voc/warn_hum must not appear at all.
    assert "WarnCO2" in result.module_source
    assert "WarnVOC" not in result.module_source
    assert "WarnHum" not in result.module_source
    # ISL29125 on i2c0 with no fram_target - proves the driver generalizes beyond dev.toml's own
    # i2c1/GPIO6/fram-wired instance.
    isl_call = next(line for line in result.module_source.splitlines() if "ISL29125_Reader(" in line)
    assert "ISL29125_Reader(i2c0, 3, trigger_s=5" in isl_call
    assert "log=log_ram" in isl_call


def test_novel_combo_construction_order_is_topologically_valid(fixtures_dir: Path, src_dir: Path, ext_dir: Path) -> None:
    result = generate_device(fixtures_dir / "novel_combo.toml", src_dir, ext_dir)
    order = result.model.construction_order
    assert order.index(("scd30", "secondary")) < order.index(("sgp40", ""))
    assert order.index(("fram", "")) < order.index(("scd30", "primary"))
    assert order.index(("neopixel", "")) < order.index(("notification", ""))


def test_multi_instance_fixture_generates_successfully(fixtures_dir: Path, src_dir: Path, ext_dir: Path) -> None:
    # The dedicated multi-instance fixture: two SCD30s and two SGP40s on separate buses, one
    # SGP40 wired to a real SCD30 and the other mixing a cross-driver reference with an explicit
    # default - proving the "any producer exposing a matching attribute name" claim directly.
    result = generate_device(fixtures_dir / "multi_instance.toml", src_dir, ext_dir)
    ast.parse(result.module_source)
    ast.parse(result.boot_entry_source)
    assert "scd30_a" in result.module_source
    assert "scd30_b" in result.module_source
    assert "sgp40_a" in result.module_source
    assert "sgp40_b" in result.module_source
    assert "temperature=ValueRef(scd30_b, 'Temp')" in result.module_source
    assert "humidity=ValueRef(scd30_b, 'Hum')" in result.module_source
    assert "temperature=ValueRef(bmp3xx_only, 'Temp')" in result.module_source
    assert "humidity=ValueRef(_DefaultHumiditySource(relative_humidity=35), 'value')" in result.module_source
    assert "_DefaultSignalSink().request_signal" in result.module_source
    # led_target/fram_target both left unwired - conn gets no LED, sysfunct no storage, both RAM logs.
    assert "ext_led=None" in result.module_source
    assert "SystemService(ntp.ntp_issynced, watchdog=watchdog, storage=None, cfg_path=cfg_path, log=log_ram, level_setters=_collect_level_setters, config_stores=_collect_config_stores, reset_reason=reset_reason)" in result.module_source
    # Only sgp40_a is monitored via warn_voc - exactly one NotificationSignal is passed
    # (warn_co2/warn_hum are absent from this fixture entirely, and sgp40_b is never a warn_* source).
    assert result.module_source.count("NotificationSignal(") == 1
    assert "signals=(NotificationSignal('WarnVOC', ValueRef(sgp40_a, 'VOC'), _FIELD_WARN_VOC, (0, 1, 0)),)" in result.module_source
    # Two scd30 instances and two sgp40 instances share one module each - one import line per
    # module, not one per instance, merging whichever _Default* extras either instance needs.
    assert result.module_source.count("from asy_scd30_driver import") == 1
    assert result.module_source.count("from asy_sgp40_driver import") == 1
    assert "from asy_sgp40_driver import SGP40_Reader, _DefaultHumiditySource" in result.module_source


def test_multi_instance_same_module_merges_distinct_default_extras(tmp_path: Path, src_dir: Path, ext_dir: Path) -> None:
    # codegen's per-module import dedup unions whichever _Default* extras any instance needs.
    # Here the two sgp40 instances default DIFFERENT fields, so the merged import line must
    # carry both even though neither instance alone needs both.
    doc = base_doc()
    doc["bus"]["i2c1"] = {"scl_pin": 19, "sda_pin": 18, "frequency": 50000, "timeout": 200000}
    sgp40 = next(i for i in doc["instance"] if i["driver"] == "sgp40")
    sgp40["name_ext"] = "a"
    sgp40["wiring"]["humidity_source"] = {"default": True, "relative_humidity": 35}
    doc["instance"].append(
        {
            "driver": "sgp40",
            "name_ext": "b",
            "bus": "i2c1",
            "wiring": {
                "temperature_source": {"default": True, "temperature": 20},
                "humidity_source": {"source": "scd30", "field": "Hum"},
            },
        },
    )
    result = generate_device(write_doc(tmp_path, "merge_extras", doc), src_dir, ext_dir)
    ast.parse(result.module_source)
    assert result.module_source.count("from asy_sgp40_driver import") == 1
    import_line = next(line for line in result.module_source.splitlines() if line.startswith("from asy_sgp40_driver import"))
    assert "_DefaultHumiditySource" in import_line
    assert "_DefaultTemperatureSource" in import_line


def test_device_level_fram_target_wires_fram_into_conn_ntp_sysfunct_and_webserver(tmp_path: Path, src_dir: Path, ext_dir: Path) -> None:
    # The implicit FRAM-wiring rule (SPECIFICATION.md A.7): every mandatory-infra module inherits the
    # device's own FRAM chip, exactly like every FRAM-wirable [[instance]] - base_doc() already
    # declares [device.wiring].fram_target = "fram", so this is the happy path.
    doc = base_doc()
    result = generate_device(write_doc(tmp_path, "device_fram_present", doc), src_dir, ext_dir)
    ast.parse(result.module_source)
    conn_line = next(line for line in result.module_source.splitlines() if line.strip().startswith("conn = WifiService("))
    ntp_line = next(line for line in result.module_source.splitlines() if line.strip().startswith("ntp = NTPClient("))
    sysfunct_line = next(line for line in result.module_source.splitlines() if line.strip().startswith("sysfunct = SystemService("))
    assert "log=log_fram" in conn_line
    assert "log=log_fram" in ntp_line
    assert "log=log_fram" in sysfunct_line
    assert "storage=fram" in sysfunct_line
    assert "log=log_fram," in result.module_source.split("webserver = WebserverService(")[1].split("\n    )\n")[0]
    # fram must actually be constructed before all three consume it - a real NameError on device,
    # not just a codegen-shape check.
    fram_pos = result.module_source.index("fram = FRAMManager(")
    assert fram_pos < result.module_source.index(conn_line)
    assert fram_pos < result.module_source.index(ntp_line)
    assert fram_pos < result.module_source.index(sysfunct_line)


def test_neither_ntp_nor_notification_is_handed_a_give_up_streak(tmp_path: Path, src_dir: Path, ext_dir: Path) -> None:
    # Regression (C.7.2): both constructors dropped max_module_error, so emitting it again would be a
    # TypeError at boot on every device - caught here rather than by a bench flash.
    source = generate_device(write_doc(tmp_path, "no_streak", base_doc()), src_dir, ext_dir).module_source
    calls = [line for line in source.splitlines() if "NTPClient(" in line or "NotificationService(" in line]
    assert len(calls) == 2, calls
    assert all("max_module_error" not in line for line in calls), calls


def test_ntp_timing_carries_the_effective_backoff_pair(tmp_path: Path, src_dir: Path, ext_dir: Path) -> None:
    def ntp_line(doc: "dict[str, object]", name: str) -> str:
        source = generate_device(write_doc(tmp_path, name, doc), src_dir, ext_dir).module_source
        ast.parse(source)
        return next(line for line in source.splitlines() if line.strip().startswith("ntp = NTPClient("))

    doc = base_doc()
    unstated = ntp_line(doc, "ntp_backoff_unstated")
    # Unstated, the src/ defaults (_DEFAULT_RETRY_S/_DEFAULT_RETRY_MAX_S) are passed as literals.
    assert "NtpTiming(_DNS_TIMEOUT_MS, _DNS_TRIES, _NTP_FETCH_TIMEOUT_MS, 10, 600)" in unstated
    assert "max_module_error" not in unstated  # NTP keeps no give-up streak (Part C.7.2)
    doc["device"]["ntp_retry_s"] = 30
    doc["device"]["ntp_retry_max_s"] = 900
    assert "NtpTiming(_DNS_TIMEOUT_MS, _DNS_TRIES, _NTP_FETCH_TIMEOUT_MS, 30, 900)" in ntp_line(doc, "ntp_backoff_stated")


def test_device_with_no_fram_target_leaves_conn_ntp_sysfunct_and_webserver_ram_only(tmp_path: Path, src_dir: Path, ext_dir: Path) -> None:
    # Regression/fallback path: a device that never wires [device.wiring].fram_target at all (or
    # has no fram instance) must build byte-for-byte as it always has - no fram= kwarg anywhere on
    # the mandatory-infra constructors, and no forced construction-order dependency on fram either.
    doc = base_doc()
    del doc["device"]["wiring"]["fram_target"]
    del doc["device"]["wiring"]["led_target"]  # its FRAM-logged NeoPixel would rightly precede conn
    result = generate_device(write_doc(tmp_path, "device_fram_absent", doc), src_dir, ext_dir)
    ast.parse(result.module_source)
    conn_line = next(line for line in result.module_source.splitlines() if line.strip().startswith("conn = WifiService("))
    ntp_line = next(line for line in result.module_source.splitlines() if line.strip().startswith("ntp = NTPClient("))
    sysfunct_line = next(line for line in result.module_source.splitlines() if line.strip().startswith("sysfunct = SystemService("))
    assert "log=log_ram" in conn_line
    assert "log=log_ram" in ntp_line
    assert "log=log_ram" in sysfunct_line
    assert "storage=None" in sysfunct_line
    webserver_call = result.module_source.split("webserver = WebserverService(")[1].split("\n    )\n")[0]
    assert "log=log_ram," in webserver_call
    # conn is still built first among mandatory infra - nothing forces fram ahead of it when there's
    # no device-level fram_target to justify that dependency.
    order = [n if isinstance(n, str) else f"{n[0]}_{n[1]}" if n[1] else n[0] for n in result.model.construction_order]
    assert order.index("conn") < order.index("fram")


def test_multi_instance_same_module_dedupes_identical_default_extra(tmp_path: Path, src_dir: Path, ext_dir: Path) -> None:
    # The same mechanism's opposite corner: both sgp40 instances default the SAME field, with
    # different constants. default_class_name() maps the field name alone, so the import line
    # must list the class once rather than twice.
    doc = base_doc()
    doc["bus"]["i2c1"] = {"scl_pin": 19, "sda_pin": 18, "frequency": 50000, "timeout": 200000}
    sgp40 = next(i for i in doc["instance"] if i["driver"] == "sgp40")
    sgp40["name_ext"] = "a"
    sgp40["wiring"]["humidity_source"] = {"default": True, "relative_humidity": 35}
    doc["instance"].append(
        {
            "driver": "sgp40",
            "name_ext": "b",
            "bus": "i2c1",
            "wiring": {
                "temperature_source": {"source": "scd30", "field": "Temp"},
                "humidity_source": {"default": True, "relative_humidity": 45},
            },
        },
    )
    result = generate_device(write_doc(tmp_path, "dedupe_extras", doc), src_dir, ext_dir)
    ast.parse(result.module_source)
    assert result.module_source.count("from asy_sgp40_driver import") == 1
    import_line = next(line for line in result.module_source.splitlines() if line.startswith("from asy_sgp40_driver import"))
    assert import_line.count("_DefaultHumiditySource") == 1


def test_device_without_notification_or_neopixel_omits_their_wiring(tmp_path: Path, src_dir: Path, ext_dir: Path) -> None:
    doc = base_doc()
    doc["instance"] = [i for i in doc["instance"] if i["driver"] not in ("neopixel", "notification")]
    del doc["device"]["wiring"]["led_target"]
    result = generate_device(write_doc(tmp_path, "minimal", doc), src_dir, ext_dir)
    ast.parse(result.module_source)
    assert "notification_led=None" in result.module_source
    assert "notification_pause=None" in result.module_source
    assert '"notification":' not in result.module_source.split("status_sources=")[1].split("\n")[0] if "status_sources=" in result.module_source else True


def test_wiring_defaults_generate_inline_provider_construction(tmp_path: Path, src_dir: Path, ext_dir: Path) -> None:
    # SPECIFICATION.md Part L.6.2's generated-code shape: the provider is constructed inline, at the exact
    # call-site the real wiring expression would occupy, with no separate named global.
    doc = base_doc()
    doc["instance"][4]["wiring"]["signal_sink"] = {"default": True}
    doc["instance"][1]["wiring"]["temperature_source"] = {"default": True, "temperature": 20}
    result = generate_device(write_doc(tmp_path, "with_defaults", doc), src_dir, ext_dir)
    ast.parse(result.module_source)
    assert "_DefaultSignalSink().request_signal" in result.module_source
    # Every defaulted per-value field always resolves to (provider, "value") - the fixed contract
    # every _Default<Field> class's get_data() follows - not the real field name.
    assert "temperature=ValueRef(_DefaultTemperatureSource(temperature=20), 'value')" in result.module_source
    # humidity_source stays a real reference - not defaulted in this fixture.
    assert "humidity=ValueRef(scd30, 'Hum')" in result.module_source


def test_device_level_led_target_unwired_passes_no_led(tmp_path: Path, src_dir: Path, ext_dir: Path) -> None:
    # test_device_wiring_optional_field_absent_is_fine (test_buildgen_validate.py) already
    # confirms validate.py accepts neopixel-present-but-led_target-unwired; the generated conn
    # line then passes ext_led=None.
    doc = base_doc()
    del doc["device"]["wiring"]["led_target"]
    result = generate_device(write_doc(tmp_path, "no_led_target", doc), src_dir, ext_dir)
    ast.parse(result.module_source)
    conn_line = next(line for line in result.module_source.splitlines() if line.strip().startswith("conn = WifiService("))
    assert "ext_led=None" in conn_line


def test_a_device_with_led_target_builds_the_neopixel_first_and_passes_it_to_conn(tmp_path: Path, src_dir: Path, ext_dir: Path) -> None:
    result = generate_device(write_doc(tmp_path, "led_target", base_doc()), src_dir, ext_dir)
    source = result.module_source
    conn_line = next(line for line in source.splitlines() if line.strip().startswith("conn = WifiService("))
    assert "ext_led=neopixel" in conn_line
    assert source.index("neopixel = NeopixelDriver(") < source.index(conn_line)
    assert "set_ext_led" not in source


def test_every_constructor_logs_through_its_fram_targets_log_config(tmp_path: Path, src_dir: Path, ext_dir: Path) -> None:
    # One LogConfig per FRAM store, built right after it; the FRAM manager itself gets the FRAM-less
    # one, and so does any module with no fram_target (here: the notification).
    doc = base_doc()
    del doc["instance"][4]["wiring"]["fram_target"]
    source = generate_device(write_doc(tmp_path, "log_configs", doc), src_dir, ext_dir).module_source
    lines = [line.strip() for line in source.splitlines()]
    assert "log_ram = LogConfig(None, DEFAULT_LOG.history_length, debug)" in lines
    fram_line, after = next((line, nxt) for line, nxt in pairwise(lines) if line.startswith("fram = FRAMManager("))
    assert fram_line == "fram = FRAMManager(spi0, 1, max_size=0x2000, log=log_ram)"
    assert after == "log_fram = LogConfig(fram, DEFAULT_LOG.history_length, debug)"
    calls = {line.split(" = ")[0]: line for line in lines if re.match(r"\w+ = [A-Z]\w*\(", line) and not line.startswith(("log_", "watchdog", "app"))}
    for var in ("scd30", "sgp40", "neopixel", "conn", "ntp", "sysfunct"):
        assert "log=log_fram" in calls[var], calls[var]
    assert "log=log_ram" in calls["notification"]
    assert "debug=debug" not in source.split("async def build_system(")[1].split("async def main(")[0].split(") -> None:")[1]
    assert "fram=" not in source


def test_device_without_sgp40_omits_maintenance_sensors(tmp_path: Path, src_dir: Path, ext_dir: Path) -> None:
    doc = base_doc()
    doc["instance"] = [i for i in doc["instance"] if i["driver"] != "sgp40"]
    del doc["instance"][0]["wiring"]  # scd30's own optional fram_target - unrelated to sgp40's removal
    result = generate_device(write_doc(tmp_path, "nosgp40", doc), src_dir, ext_dir)
    ast.parse(result.module_source)
    assert "maintenance_sensors=()," in result.module_source


def test_build_error_reports_device_and_field(tmp_path: Path, src_dir: Path) -> None:
    doc = base_doc()
    del doc["device"]["hotspot_time_min"]
    path = write_doc(tmp_path, "broken_device", doc)
    with pytest.raises(BuildError) as exc_info:
        generate_device(path, src_dir)
    assert "broken_device" in str(exc_info.value)
    assert "hotspot_time_min" in str(exc_info.value)


def test_cli_writes_module_and_boot_entry_to_out_dir(repo_root: Path, tmp_path: Path) -> None:
    from buildgen.generate import main

    out_dir = tmp_path / "out"
    exit_code = main([str(repo_root / "devices" / "wozi.toml"), "--out-dir", str(out_dir)])
    assert exit_code == 0
    assert sorted(p.name for p in out_dir.iterdir()) == ["sensortask_wozi.py", "sensortask_wozi_main.py", "sensortask_wozi_main_noautostart.py"]
    ast.parse((out_dir / "sensortask_wozi.py").read_text())


def test_cli_prints_module_source_without_out_dir(repo_root: Path, capsys: pytest.CaptureFixture[str]) -> None:
    from buildgen.generate import main

    exit_code = main([str(repo_root / "devices" / "wozi.toml")])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "async def build_system(" in captured.out


def test_cli_reports_build_error_on_stderr_and_exits_nonzero(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    from buildgen.generate import main

    doc = base_doc()
    del doc["device"]["hotspot_time_min"]
    path = write_doc(tmp_path, "broken_device", doc)
    exit_code = main([str(path), "--src-dir", str(Path(__file__).resolve().parent.parent / "src")])
    assert exit_code == 1
    captured = capsys.readouterr()
    assert "hotspot_time_min" in captured.err
    # One line naming what, where and the fix, never a traceback (SPECIFICATION.md Part L.5).
    assert captured.err.count("\n") == 1
    assert captured.err.startswith("buildgen: [broken_device")
    assert " - fix: " in captured.err
    assert "Traceback" not in captured.err


def test_hostname_and_hotspot_password_are_wired_into_generated_code(repo_root: Path, src_dir: Path, ext_dir: Path) -> None:
    # The inverse of the tripwire this replaces: hostname and hotspot_password were validated
    # and then reached nothing, so every device booted as the shared "SensorNode". They are
    # passed to WifiService now, as the two persisted fields' per-device defaults.
    result = generate_device(repo_root / "devices" / "wozi.toml", src_dir, ext_dir)
    assert "WifiConfig('SensorStationWozi', '12345678', " in result.module_source
    ast.parse(result.module_source)


def test_bmp3xx_trigger_s_is_rendered_into_the_constructor_call(tmp_path: Path, src_dir: Path, ext_dir: Path) -> None:
    # trigger_s is declared only on scd30 in every real device and fixture; this pins bmp3xx's own
    # trigger_s rendering, which its @limits domain depends on.
    doc = base_doc()
    doc["instance"].append({"driver": "bmp3xx", "name_ext": "", "bus": "i2c0", "address": 0x77, "trigger_s": 42, "wiring": {"fram_target": "fram"}})
    result = generate_device(write_doc(tmp_path, "dev", doc), src_dir, ext_dir)
    assert "trigger_s=42" in result.module_source
    ast.parse(result.module_source)


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_real_device_constructs_scd30_with_the_boot_config_path(repo_root: Path, src_dir: Path, ext_dir: Path, device: str) -> None:
    # SCD30 keeps its three FRC readiness settings in a config file, so it is built like the other config readers.
    result = generate_device(repo_root / "devices" / f"{device}.toml", src_dir, ext_dir)
    calls = [line for line in result.module_source.splitlines() if "SCD30_Reader(" in line]
    assert calls, f"{device} constructs no SCD30_Reader - the check holds nothing"
    for call in calls:
        assert ", cfg_path=cfg_path, log=" in call, call


def test_isl29125_irq_pin_and_trigger_s_are_rendered_into_the_constructor_call(tmp_path: Path, src_dir: Path, ext_dir: Path) -> None:
    # irq_pin is a required positional arg (like scd30's own shape); trigger_s is optional (like
    # bmp3xx's own shape) - ISL29125_Reader is the one driver combining both.
    doc = base_doc()
    doc["instance"].append({"driver": "isl29125", "name_ext": "", "bus": "i2c0", "irq_pin": 6, "trigger_s": 5, "wiring": {"fram_target": "fram"}})
    result = generate_device(write_doc(tmp_path, "dev", doc), src_dir, ext_dir)
    assert "ISL29125_Reader(i2c0, 6, trigger_s=5" in result.module_source
    call = next(line for line in result.module_source.splitlines() if "ISL29125_Reader(" in line)
    assert "log=log_fram" in call
    ast.parse(result.module_source)


def test_isl29125_without_trigger_s_or_fram_target_omits_both(tmp_path: Path, src_dir: Path, ext_dir: Path) -> None:
    # Both are optional - a device wiring neither must still generate a valid, minimal call.
    doc = base_doc()
    doc["instance"].append({"driver": "isl29125", "name_ext": "", "bus": "i2c0", "irq_pin": 6})
    result = generate_device(write_doc(tmp_path, "dev", doc), src_dir, ext_dir)
    call = next(line for line in result.module_source.splitlines() if "ISL29125_Reader(" in line)
    assert "trigger_s" not in call
    assert "log=log_ram" in call
    assert "irq_pull_up" not in call
    ast.parse(result.module_source)


def test_isl29125_irq_pull_up_false_is_rendered_into_the_constructor_call(tmp_path: Path, src_dir: Path, ext_dir: Path) -> None:
    # A board with its own external pull-up resistor (the real dev bench) sets this - the driver's
    # own default (omitted here) is True, the internal pull-up, for a board with no resistor of
    # its own.
    doc = base_doc()
    doc["instance"].append({"driver": "isl29125", "name_ext": "", "bus": "i2c0", "irq_pin": 6, "irq_pull_up": False})
    result = generate_device(write_doc(tmp_path, "dev", doc), src_dir, ext_dir)
    assert "irq_pull_up=False" in result.module_source
    ast.parse(result.module_source)


def test_a_warn_signal_outside_the_catalog_reaching_codegen_is_an_internal_error(tmp_path: Path, src_dir: Path) -> None:
    # The build refuses an unknown warn_* key before generation starts (validate.py); one that got past
    # it is a generator bug, never rendered and never silently dropped.
    model = build_model(write_doc(tmp_path, "warn_bogus", base_doc()), src_dir)
    build_construction_order(model)
    model.instances[("notification", "")].wiring["warn_bogus"] = {"source": "scd30", "field": "CO2"}
    with pytest.raises(BuildInternalError, match="warn_bogus"):
        generate_module_source(model, model.construction_order, "2026-01-01T00:00:00Z", src_dir)


def test_identifier_rejects_a_name_python_could_not_use(src_dir: Path) -> None:
    # A name_ext such as "a-b" reaches it through a TOML; driven directly for every kind of bad name -
    # it is the one guard standing between a bad name and generated source that would not parse.
    from buildgen.codegen import _identifier

    for bad in ("class", "not-an-identifier", "9leading_digit", ""):
        with pytest.raises(BuildError, match="not usable as a generated Python identifier - fix: ") as exc_info:
            _identifier(bad, "dev")
        assert exc_info.value.rule == "names.not-an-identifier"
    assert _identifier("i2c0", "dev") == "i2c0"


def test_codegen_has_no_build_recipe_for_an_unknown_driver(tmp_path: Path, src_dir: Path, ext_dir: Path) -> None:
    # driver_registry can resolve a driver that codegen has no constructor recipe for - the build
    # must say exactly that, and name where to add one.
    from buildgen.codegen import _build_call, _Ctx
    from buildgen.validate import build_model

    # Driven at the _build_call() level: an instance of such a driver can't be carried through a
    # whole build, because _check_required_fields() rejects a driver with no buildspec.py entry
    # long before codegen sees it.
    model = build_model(write_doc(tmp_path, "dev", base_doc()), src_dir)
    spec = model.instances[("scd30", "")]
    spec.driver = "not_a_real_driver"
    assert spec.driver_info is not None
    with pytest.raises(BuildError, match=re.escape("no build recipe for driver 'not_a_real_driver' - fix: add one to buildgen.codegen._BUILD_ARGS_HANDLERS")) as exc_info:
        _build_call(spec, spec.driver_info, _Ctx(model))
    assert exc_info.value.rule == "driver.no-build-recipe"


def test_notification_with_no_signal_sink_wiring_field_fails_loud(tmp_path: Path, src_dir: Path) -> None:
    # _build_args_notification()'s internal invariant: signal_sink is always resolved by
    # validate.py before codegen runs, so no real TOML reaches this. Driven by mutating an
    # already-validated spec, the same way the unknown-driver test above reaches its branch.
    from buildgen.codegen import _build_args_notification, _Ctx
    from buildgen.validate import build_model

    model = build_model(write_doc(tmp_path, "dev", base_doc()), src_dir)
    spec = model.instances[("notification", "")]
    spec.wiring_schema = tuple(wf for wf in spec.wiring_schema if wf.toml_field != "signal_sink")
    with pytest.raises(BuildInternalError, match="no signal_sink wiring field by codegen time"):
        _build_args_notification(spec, _Ctx(model))


def test_instance_with_no_driver_info_fails_loud_at_codegen_time(tmp_path: Path, src_dir: Path) -> None:
    # _emit_header_and_imports()'s internal invariant: driver_info is always resolved before
    # codegen runs. Driven through generate_module_source(), the same seam generate_device()
    # uses, on a valid model with one instance's driver_info cleared afterwards.
    from buildgen.codegen import generate_module_source
    from buildgen.graph import build_construction_order
    from buildgen.validate import build_model

    model = build_model(write_doc(tmp_path, "dev", base_doc()), src_dir)
    build_construction_order(model)
    model.instances[("scd30", "")].driver_info = None
    with pytest.raises(BuildInternalError, match="driver_info unresolved by codegen time"):
        generate_module_source(model, model.construction_order, "2026-01-01T00:00:00Z", src_dir)


def test_construction_order_entry_that_is_neither_a_bare_node_nor_an_instance_key_fails_loud(tmp_path: Path, src_dir: Path) -> None:
    # _emit_build_system()'s internal invariant: build_construction_order() only emits the three
    # infra names or a real instance key, so no TOML reaches this. Driven by inserting a bogus
    # bare string into an already-computed construction order.
    from buildgen.codegen import generate_module_source
    from buildgen.graph import build_construction_order
    from buildgen.validate import build_model

    model = build_model(write_doc(tmp_path, "dev", base_doc()), src_dir)
    build_construction_order(model)
    mutated_order = [*model.construction_order, "bogus_node"]
    with pytest.raises(BuildInternalError, match="is not a known bare node or an instance key"):
        generate_module_source(model, mutated_order, "2026-01-01T00:00:00Z", src_dir)


def test_a_codegen_step_reached_without_its_src_dir_is_an_internal_error(tmp_path: Path, src_dir: Path) -> None:
    model = build_model(write_doc(tmp_path, "no_src_dir", base_doc()), src_dir)
    with pytest.raises(BuildInternalError, match="no src_dir"):
        _ = _Ctx(model).src_dir


def test_an_sgp40_without_its_resolved_name_is_an_internal_error(tmp_path: Path, src_dir: Path) -> None:
    model = build_model(write_doc(tmp_path, "no_resolved_name", base_doc()), src_dir)
    build_construction_order(model)
    model.instances[("sgp40", "")].resolved_name = None
    with pytest.raises(BuildInternalError, match="resolved_name unresolved"):
        _sgp40_status_vars(model.construction_order, _Ctx(model))


def test_a_generator_bug_emitting_invalid_python_is_an_internal_error(tmp_path: Path, src_dir: Path, ext_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # generate_device() compiles what it emits before returning it, so a template bug never reaches a file.
    monkeypatch.setattr(generate_module, "generate_module_source", lambda *_args, **_kwargs: "def broken(:\n")
    with pytest.raises(BuildInternalError, match="broken_template"):
        generate_device(write_doc(tmp_path, "broken_template", base_doc()), src_dir, ext_dir)


def test_cli_entry_point_writes_both_files_and_exits_zero(tmp_path: Path, repo_root: Path) -> None:
    # The one real entry point a person invokes by hand. Run as a subprocess so the __main__ guard
    # and the process exit code are both genuinely exercised, not just main()'s return value.
    import subprocess
    import sys

    out = tmp_path / "out"
    result = subprocess.run(
        [sys.executable, "-m", "buildgen.generate", str(repo_root / "devices" / "wozi.toml"), "--out-dir", str(out)],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert sorted(p.name for p in out.iterdir()) == ["sensortask_wozi.py", "sensortask_wozi_main.py", "sensortask_wozi_main_noautostart.py"]
    ast.parse((out / "sensortask_wozi.py").read_text())


def test_cli_entry_point_reports_a_build_error_and_exits_nonzero(tmp_path: Path, repo_root: Path) -> None:
    import subprocess
    import sys

    bad = write_doc(tmp_path, "dev", {"device": {"name": "Test"}})
    result = subprocess.run(
        [sys.executable, "-m", "buildgen.generate", str(bad)],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1
    assert "buildgen:" in result.stderr  # a human-readable reason, never a raw traceback
    assert "Traceback" not in result.stderr
    assert result.stderr.count("\n") == 1
    assert " - fix: " in result.stderr


def _webserver_keywords(source: str) -> dict[str, object]:
    calls = [node for node in ast.walk(ast.parse(source)) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "ServingLimits"]
    assert len(calls) == 1, len(calls)
    return {kw.arg: ast.literal_eval(kw.value) for kw in calls[0].keywords if kw.arg in ("max_connections", "backlog")}


@pytest.mark.parametrize(
    ("stated", "expected"),
    [
        ({"max_connections": 3, "backlog": 4}, {"max_connections": 3, "backlog": 4}),
        ({"max_connections": 5}, {"max_connections": 5, "backlog": None}),
        ({}, {"max_connections": 6, "backlog": None}),  # asy_webserver_service._DEFAULT_MAX_CONNECTIONS
    ],
)
def test_the_stated_connection_ceiling_reaches_the_webserver_and_an_absent_one_is_its_src_default(tmp_path: Path, src_dir: Path, ext_dir: Path, stated: dict[str, int], expected: dict[str, int]) -> None:
    # validate.py checks the stated values against the firmware's lwIP pools; that check is only
    # worth anything if the same values are the ones the device is then built with.
    doc = base_doc()
    for key in ("max_connections", "backlog"):
        doc["device"].pop(key, None)
    doc["device"].update(stated)
    result = generate_device(write_doc(tmp_path, "ceiling", doc), src_dir, ext_dir)
    assert _webserver_keywords(result.module_source) == expected
