"""The twin runner's --test-* instrumentation stays test-only: every flag is off by default, every instrumentation call
and private rebind sits under its own flag, and nothing the firmware freezes (src/, ext/, a generated device module, the
frozen website) names a --test- flag, the runner or a twin-only module."""

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RUNNER = REPO_ROOT / "digital_twin" / "run_generic_integration.py"
_PREFIX = "--test-"
_INSTRUMENT = "_test_"  # every instrumentation function's prefix
_STARTER = "_test_start"  # the one dispatcher main() calls, every flag checked inside it
_SHARED_NAMES = {"machine", "network", "neopixel", "rp2"}  # twin fakes standing in for the firmware's own modules
# Every test-only flag the runner may have: one it gains or loses is a reviewed change to this table, never silent.
_FLAG_TABLE = (
    "--test-hold-closing-slot", "--test-stall-loop-ms", "--test-conn-status-interval-ms", "--test-fault-status-interval-ms",
    "--test-shutdown-hang", "--test-flash-stall-max", "--test-uart-over-cap", "--test-hold-system-entry", "--test-kbd-traceback",
    "--test-loop-lag-ms", "--test-drop-timer-fire", "--test-watchdog-fault", "--test-defer-faults", "--test-pin-send-buffer",
)


def _functions(tree: ast.Module) -> "dict[str, ast.FunctionDef | ast.AsyncFunctionDef]":
    return {node.name: node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}


def _guarded(node: ast.AST, parents: "dict[ast.AST, ast.AST]") -> bool:
    # Under an `if` whose test reads only flags.<field>.
    while node in parents:
        node = parents[node]
        if isinstance(node, ast.If):
            reads = [n for n in ast.walk(node.test) if isinstance(n, ast.Attribute)]
            names = [n for n in ast.walk(node.test) if isinstance(n, ast.Name)]
            if reads and all(ast.unparse(r.value) == "flags" for r in reads) and all(n.id == "flags" for n in names):
                return True
    return False


def _product_files() -> "list[Path]":
    roots = (REPO_ROOT / "src", REPO_ROOT / "ext", REPO_ROOT / "frozen_modules")
    found = [path for root in roots for path in sorted(root.glob("*.py"))]
    return found + sorted((REPO_ROOT / "build" / "generated_src").glob("sensortask_*.py"))


def default_problems(source: str) -> "list[str]":
    # _NO_TEST_FLAGS holds only False/None, parse_args() starts from it, and each --test- flag is parsed and documented.
    tree = ast.parse(source)
    problems = []
    (default,) = [n.value for n in tree.body if isinstance(n, ast.Assign) and ast.unparse(n.targets[0]) == "_NO_TEST_FLAGS"]
    if not (isinstance(default, ast.Call) and default.args and all(isinstance(a, ast.Constant) and a.value in (False, None) for a in default.args)):
        problems.append(f"_NO_TEST_FLAGS = {ast.unparse(default)} turns a flag on by default")
    if "flags = _NO_TEST_FLAGS" not in ast.unparse(_functions(tree)["parse_args"]):
        problems.append("parse_args() does not start from _NO_TEST_FLAGS")
    named = {n.value.split()[0] for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str) and n.value.startswith(_PREFIX)}
    parsed = {n.value for n in ast.walk(_functions(tree)["_parse_test_flag"]) if isinstance(n, ast.Constant) and isinstance(n.value, str)}
    usage = next(ast.unparse(n.value) for n in tree.body if isinstance(n, ast.Assign) and ast.unparse(n.targets[0]) == "_USAGE")
    problems += [f"{flag} is not parsed by _parse_test_flag()" for flag in sorted(named - parsed)]
    problems += [f"{flag} is not in the --help text" for flag in sorted(named) if flag not in usage]
    problems += [f"{flag} is in the flag table but not in the runner" for flag in _FLAG_TABLE if flag not in named]
    problems += [f"{flag} is in the runner but not in the flag table" for flag in sorted(named - set(_FLAG_TABLE))]
    fields = len(default.args) if isinstance(default, ast.Call) else 0
    if len(named) != fields:
        problems.append(f"{len(named)} --test- flags for the {fields} TestFlags fields")
    return problems


def guard_problems(source: str) -> "list[str]":
    # main() reaches the instrumentation only through _test_start(config.instrumentation, ...); inside it each call sits
    # under its flag's if; and outside the _test_ functions nothing rebinds a private attribute of another object.
    tree = ast.parse(source)
    functions = _functions(tree)
    problems = []
    for name, func in functions.items():
        calls = [n for n in ast.walk(func) if isinstance(n, ast.Call) and ast.unparse(n.func).startswith(_INSTRUMENT)]
        if name == "main":
            problems += [f"main() calls {ast.unparse(c)}" for c in calls if not (ast.unparse(c.func) == _STARTER and ast.unparse(c.args[0]) == "config.instrumentation")]
        elif name == _STARTER:
            parents = {child: parent for parent in ast.walk(func) for child in ast.iter_child_nodes(parent)}
            problems += [f"{_STARTER}() calls {ast.unparse(c)} outside its flag's if" for c in calls if not _guarded(c, parents)]
        elif not name.startswith(_INSTRUMENT) and calls:
            problems += [f"{name}() calls {ast.unparse(c)}" for c in calls]
        if not name.startswith(_INSTRUMENT):
            for node in ast.walk(func):
                targets = node.targets if isinstance(node, ast.Assign) else []
                problems += [f"{name}() rebinds {ast.unparse(t)}" for t in targets if isinstance(t, ast.Attribute) and t.attr.startswith("_") and ast.unparse(t.value) != "self"]
    return problems


def test_every_test_only_flag_is_off_by_default_parsed_and_documented() -> None:
    assert default_problems(RUNNER.read_text(encoding="utf-8")) == []


def test_every_instrumentation_call_and_private_rebind_sits_under_its_flag() -> None:
    source = RUNNER.read_text(encoding="utf-8")
    assert _STARTER in _functions(ast.parse(source)), "the dispatcher is gone - the check would pass vacuously"
    assert guard_problems(source) == []


def test_nothing_the_firmware_freezes_names_a_test_flag_the_runner_or_a_twin_module() -> None:
    twin_only = {path.stem for path in (REPO_ROOT / "digital_twin").rglob("*.py")} - _SHARED_NAMES
    files = _product_files()
    assert len(files) > 40 and any(p.parent.name == "generated_src" for p in files), len(files)  # the whole set, generated included
    problems = []
    for path in files:
        source = path.read_text(encoding="utf-8")
        if _PREFIX in source:
            problems.append(f"{path.relative_to(REPO_ROOT)} names a {_PREFIX} flag")
        for node in ast.walk(ast.parse(source)):
            modules = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module or ""] if isinstance(node, ast.ImportFrom) else []
            problems += [f"{path.relative_to(REPO_ROOT)} imports {m}" for m in modules if m.split(".")[0] in twin_only]
    assert problems == [], problems


def test_a_flag_defaulting_on_or_an_unguarded_call_is_caught() -> None:
    source = RUNNER.read_text(encoding="utf-8")
    on = source.replace("_NO_TEST_FLAGS = TestFlags(False,", "_NO_TEST_FLAGS = TestFlags(True,", 1)
    assert on != source and any("by default" in p for p in default_problems(on))
    unguarded = source.replace("    if flags.conn_status_interval_ms:\n        tasks.append(", "    if True:\n        tasks.append(")
    assert unguarded != source and any("outside its flag's if" in p for p in guard_problems(unguarded))
    leaked = source.replace("def load_module(", "def _leak(m):\n    m.webserver._close_writer = None\n\n\ndef load_module(")
    assert leaked != source and any("rebinds m.webserver._close_writer" in p for p in guard_problems(leaked))
    dropped = source.replace('elif arg == "--test-loop-lag-ms":', 'elif arg == "--test-loop-lag":')
    assert dropped != source and any("--test-loop-lag-ms is in the flag table but not in the runner" in p for p in default_problems(dropped))
