"""One occurrence is persisted as a fault or as a warning, never both (SPECIFICATION.md C.7): a persisted err_s()
and wrn_s() reachable one after the other on one path of one function, with no return between, fail unless
_ALLOWED names both events and why they are two occurrences. Same-kind pairs and other functions' entries pass."""

import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from _devices import DEVICE_NAMES

from buildgen.generate import generate_device

if TYPE_CHECKING:
    from collections.abc import Iterator

_REPO = Path(__file__).resolve().parent.parent
_METHOD_KIND = {"err_s": "E", "wrn_s": "W"}
_KEYWORD = {"E": "errno", "W": "wrnno"}
_PREFIX = {"E": "_ERR_", "W": "_WRN_"}

Event = tuple[str, str]  # (kind, catalog name - or the code expression's text when it is not a named constant)
Pair = tuple[str, str, Event, Event]  # (module path, function, first, second)

_FILE_THEN_WRITE = "the config file was unusable, then writing its repair failed: two occurrences"
_TWO_SOURCES = "the config manager and the read callback are two sources: two occurrences"
_FILE_THEN_SCHEMA = "the config file was unusable, then the schema itself proved invalid: two occurrences"
_CHIP_RESET = "a chip reset, then a failed re-apply or a rejected reading: separate occurrences"

# The mixed pairs the tree holds on purpose, each with why its two entries are two occurrences. A listed
# pair the scan no longer finds fails, so the list follows every change that renames or removes one.
_ALLOWED: "dict[Pair, str]" = {
    ("src/asy_bmp3xx_driver.py", "_read_bmp", ("E", "CFG_READ"), ("W", "BMP_CHIP_RESET")): "the cycle's config read fell back, then the chip reset was read: separate occurrences",
    ("src/asy_bmp3xx_driver.py", "_read_bmp", ("W", "BMP_CHIP_RESET"), ("E", "READ")): _CHIP_RESET,
    ("src/asy_bmp3xx_driver.py", "_read_bmp", ("W", "BMP_CHIP_RESET"), ("E", "READ_RANGE")): _CHIP_RESET,
    ("src/asy_isl29125_driver.py", "_check_divergence", ("W", "ISL_DIVERGED"), ("E", "CHIP_SET")): "the chip diverged from the shadow, then its re-apply failed: separate occurrences",
    ("src/asy_uart_comm.py", "_resync", ("W", "UART_DRAIN_BOUND"), ("E", "UART_LINK_UNINTELLIGIBLE")): "a drain that hit its bound and a link no frame ever validated on are separate conditions",
    ("src/asy_fram_driver.py", "setup", ("W", "FRAM_ID_RETRIED"), ("E", "FRAM_WP_PARTIAL")): "the chip answered its identification only on a retry, then its status register read partly protected: two conditions",
    ("src/asy_fram_manager.py", "_read", ("W", "FRAM_BLOCK_INVALID"), ("E", "FRAM_BLOCK_WRITE")): "an invalid block, then a failed repair write",
    ("src/asy_base_classes.py", "_get_dict_cfg", ("W", "CFG_KEYS"), ("E", "CFG_CALLBACK_RAISED")): _TWO_SOURCES,
    ("src/asy_base_classes.py", "_get_dict_cfg", ("E", "CFG_GET_RAISED"), ("W", "CALLBACK_KEYS")): _TWO_SOURCES,
    ("src/asy_base_classes.py", "_get_dict_cfg", ("W", "CALLBACK_KEYS"), ("E", "CFG_CALLBACK_RAISED")): "the callback's unknown keys, then merging its result raised: two occurrences",
    ("src/asy_captive_dns.py", "run", ("E", "UNEXPECTED"), ("W", "SOCKET_TEARDOWN")): "never in one run: the raising disconnect sets disconnect_ok, which the teardown warning tests",
    ("src/asy_ntp_client.py", "_fetch_ntp_reply", ("W", "SOCKET_TEARDOWN"), ("E", "NTP_NO_REPLY")): "the socket's teardown and the exchange's outcome (a silent server) are two occurrences",
    ("src/asy_wifi_service.py", "_deactivate_wlan_permanently", ("W", "WLAN_DEACTIVATED"), ("E", "WLAN_OFF")): "the permanent switch-off is persisted first, then a raise in its teardown (disconnect/active/deinit) is a second occurrence",
    ("src/asy_config_manager.py", "setup", ("W", "CFG_FILE_NOT_OBJECT"), ("E", "CFG_FILE_WRITE")): _FILE_THEN_WRITE,
    ("src/asy_config_manager.py", "setup", ("W", "CFG_FILE_JSON"), ("E", "CFG_FILE_WRITE")): _FILE_THEN_WRITE,
    ("src/asy_config_manager.py", "setup", ("W", "CFG_FILE_UNREADABLE"), ("E", "CFG_FILE_WRITE")): _FILE_THEN_WRITE,
    ("src/asy_config_manager.py", "setup", ("W", "STORED_DEFAULT"), ("E", "CFG_FILE_WRITE")): _FILE_THEN_WRITE,
    ("src/asy_config_manager.py", "setup", ("W", "CFG_KEYS_REMOVED"), ("E", "CFG_FILE_WRITE")): _FILE_THEN_WRITE,
    ("src/asy_config_manager.py", "setup", ("W", "CFG_FILE_NOT_OBJECT"), ("E", "CFG_NO_DEFAULTS")): _FILE_THEN_SCHEMA,
    ("src/asy_config_manager.py", "setup", ("W", "CFG_FILE_JSON"), ("E", "CFG_NO_DEFAULTS")): _FILE_THEN_SCHEMA,
    ("src/asy_config_manager.py", "setup", ("W", "CFG_FILE_UNREADABLE"), ("E", "CFG_NO_DEFAULTS")): _FILE_THEN_SCHEMA,
    ("src/asy_config_manager.py", "setup", ("W", "CFG_FILE_NOT_OBJECT"), ("E", "CFG_BAD_DEFAULT")): _FILE_THEN_SCHEMA,
    ("src/asy_config_manager.py", "setup", ("W", "CFG_FILE_JSON"), ("E", "CFG_BAD_DEFAULT")): _FILE_THEN_SCHEMA,
    ("src/asy_config_manager.py", "setup", ("W", "CFG_FILE_UNREADABLE"), ("E", "CFG_BAD_DEFAULT")): _FILE_THEN_SCHEMA,
}


def _code_name(kind: str, node: "ast.expr | None") -> str:
    if isinstance(node, ast.Name) and node.id.startswith(_PREFIX[kind]):
        return node.id[len(_PREFIX[kind]):]
    return ast.unparse(node) if node is not None else "?"


def _callee(call: ast.Call) -> str:
    return call.func.attr if isinstance(call.func, ast.Attribute) else getattr(call.func, "id", "")


def _bound(call: ast.Call, fn: "ast.FunctionDef | ast.AsyncFunctionDef", param: str) -> "ast.expr | None":
    # The argument this call binds to `fn`'s parameter `param`, or None when it is left at its default.
    keyword = next((k.value for k in call.keywords if k.arg == param), None)
    if keyword is not None:
        return keyword
    params = [a.arg for a in (*fn.args.posonlyargs, *fn.args.args)]
    position = params.index(param) if param in params else -1
    if params[:1] == ["self"] and isinstance(call.func, ast.Attribute):
        position -= 1
    if 0 <= position < len(call.args) and not isinstance(call.args[position], ast.Starred):
        return call.args[position]
    return None


@dataclass
class _Module:
    # One parsed module and its persisting wrappers: function name -> {code parameter: kind}.

    path: str
    tree: ast.Module
    defs: "dict[str, ast.FunctionDef | ast.AsyncFunctionDef]" = field(default_factory=dict)
    wrappers: "dict[str, dict[str, str]]" = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.defs = {n.name: n for n in ast.walk(self.tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
        changed = True
        while changed:  # a wrapper forwarding to a wrapper is one too, so resolve to a fixed point
            changed = False
            for name, fn in self.defs.items():
                forwarded = self._forwarded(fn)
                if forwarded != self.wrappers.get(name, {}):
                    self.wrappers[name] = forwarded
                    changed = True
        self.wrappers = {name: params for name, params in self.wrappers.items() if params}

    def _forwarded(self, fn: "ast.FunctionDef | ast.AsyncFunctionDef") -> "dict[str, str]":
        # The parameters `fn` persists a caller's code through: passed as the code of err_s()/wrn_s() or a wrapper.
        params = {a.arg for a in (*fn.args.posonlyargs, *fn.args.args, *fn.args.kwonlyargs)}
        forwarded = {}
        for node in ast.walk(fn):
            for kind, code in self.events(node) if isinstance(node, ast.Call) else ():
                if isinstance(code, ast.Name) and code.id in params:
                    forwarded[code.id] = kind
        return forwarded

    def events(self, call: ast.Call) -> "list[tuple[str, ast.expr | None]]":
        # The persisted entries this one call writes: (kind, code expression).
        if isinstance(call.func, ast.Attribute) and call.func.attr in _METHOD_KIND:
            kind = _METHOD_KIND[call.func.attr]
            return [(kind, next((k.value for k in call.keywords if k.arg == _KEYWORD[kind]), None))]
        name = _callee(call)
        return [(kind, _bound(call, self.defs[name], param)) for param, kind in self.wrappers.get(name, {}).items() if name in self.defs]


@dataclass
class _Walk:
    # The straight-line path walk of one function: `pending` holds the entries the last persisted call left.

    module: _Module
    function: str
    pairs: "set[Pair]" = field(default_factory=set)
    breaks: "list[set[Event]]" = field(default_factory=list)
    continues: "list[set[Event]]" = field(default_factory=list)

    def calls(self, node: ast.AST, pending: "set[Event]") -> "set[Event]":
        found = []
        stack = [node]
        while stack:
            sub = stack.pop()
            if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)) and sub is not node:
                continue
            if isinstance(sub, ast.Call):
                found.append(sub)
            stack.extend(ast.iter_child_nodes(sub))
        for call in sorted(found, key=lambda c: (c.end_lineno or 0, c.end_col_offset or 0)):  # inner calls run first
            for kind, code in self.module.events(call):
                event = (kind, _code_name(kind, code))
                self.pairs.update((self.module.path, self.function, before, event) for before in pending if before[0] != kind)
                pending = {event}
        return pending

    def block(self, stmts: "list[ast.stmt]", pending: "set[Event]") -> "set[Event]":
        for stmt in stmts:
            pending = self.stmt(stmt, pending)
        return pending

    def stmt(self, stmt: ast.stmt, pending: "set[Event]") -> "set[Event]":
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            return pending
        if isinstance(stmt, (ast.Return, ast.Raise)):
            self.calls(stmt, pending)
            return set()  # the path ends here
        if isinstance(stmt, (ast.Break, ast.Continue)):
            targets = self.breaks if isinstance(stmt, ast.Break) else self.continues
            if targets:
                targets[-1] |= pending
            return set()
        return self.compound(stmt, pending)

    def compound(self, stmt: ast.stmt, pending: "set[Event]") -> "set[Event]":
        if isinstance(stmt, ast.If):
            pending = self.calls(stmt.test, pending)
            return self.block(stmt.body, pending) | self.block(stmt.orelse, pending)
        if isinstance(stmt, (ast.For, ast.AsyncFor, ast.While)):
            return self.loop(stmt, pending)
        if isinstance(stmt, (ast.Try, ast.TryStar)):
            return self.try_(stmt, pending)
        if isinstance(stmt, (ast.With, ast.AsyncWith)):
            for item in stmt.items:
                pending = self.calls(item.context_expr, pending)
            return self.block(stmt.body, pending)
        if isinstance(stmt, ast.Match):
            pending = self.calls(stmt.subject, pending)
            return set().union(pending, *(self.block(case.body, pending) for case in stmt.cases))
        return self.calls(stmt, pending)

    def loop(self, stmt: "ast.For | ast.AsyncFor | ast.While", pending: "set[Event]") -> "set[Event]":
        # One pass through the body: a later pass handles a later item, another occurrence.
        pending = self.calls(stmt.test if isinstance(stmt, ast.While) else stmt.iter, pending)
        self.breaks.append(set())
        self.continues.append(set())
        body = self.block(stmt.body, pending)
        broken, continued = self.breaks.pop(), self.continues.pop()
        if isinstance(stmt, ast.While) and isinstance(stmt.test, ast.Constant) and stmt.test.value:
            return broken  # `while True` leaves only through a break
        return self.block(stmt.orelse, pending | body | continued) | broken

    def try_(self, stmt: "ast.Try | ast.TryStar", pending: "set[Event]") -> "set[Event]":
        # A handler is entered from the start of any statement of the try body.
        entry = set(pending)
        body = pending
        for inner in stmt.body:
            entry |= body
            body = self.stmt(inner, body)
        out = self.block(stmt.orelse, body)
        for handler in stmt.handlers:
            out |= self.block(handler.body, entry)
        return self.block(stmt.finalbody, out) if stmt.finalbody else out


def _pairs(modules: "list[_Module]") -> "set[Pair]":
    found: set[Pair] = set()
    for m in modules:
        for fn in m.defs.values():
            walk = _Walk(m, fn.name)
            walk.block(fn.body, set())
            found |= walk.pairs
    return found


def _parse(path: str, source: str) -> _Module:
    return _Module(path, ast.parse(source, filename=path))


def _src_modules() -> "list[_Module]":
    return [_parse(f"src/{p.name}", p.read_text()) for p in sorted((_REPO / "src").glob("*.py"))]


@pytest.fixture(scope="module")
def tree_pairs(tmp_path_factory: pytest.TempPathFactory) -> "set[Pair]":
    generated = tmp_path_factory.mktemp("generated_src")
    modules = _src_modules()
    for device in DEVICE_NAMES:
        result = generate_device(_REPO / "devices" / f"{device}.toml", _REPO / "src", _REPO / "ext")
        target = generated / f"sensortask_{device}.py"
        target.write_text(result.module_source)
        modules.append(_parse(f"build/generated_src/{target.name}", target.read_text()))
    return _pairs(modules)


def _describe(pairs: "set[Pair] | Iterator[Pair]") -> str:
    return "\n".join(f"{path} {fn}(): {a[0]} {a[1]} then {b[0]} {b[1]}" for path, fn, a, b in sorted(pairs))


def test_no_occurrence_is_persisted_as_both_a_fault_and_a_warning(tree_pairs: "set[Pair]") -> None:
    unlisted = tree_pairs - set(_ALLOWED)
    assert not unlisted, "a persisted fault and warning on one path, not in _ALLOWED - one occurrence is one or the other:\n" + _describe(unlisted)


def test_every_allowed_pair_still_occurs(tree_pairs: "set[Pair]") -> None:
    stale = set(_ALLOWED) - tree_pairs
    assert not stale, "these _ALLOWED pairs no longer occur - drop or rename them:\n" + _describe(stale)


def test_the_scan_sees_the_trees_logging() -> None:
    # Guards the scan itself: a shape change in the logging calls must not quietly empty it.
    modules = _src_modules()
    persisted = sum(len(m.events(c)) for m in modules for c in ast.walk(m.tree) if isinstance(c, ast.Call))
    assert persisted >= 100, f"only {persisted} persisted log calls found in src/"


# ---- planted pairs -----------------------------------------------------------------------------------


_PLANT = """
class Mod:
    async def _err(self, errno, *args):
        await self.pr.err_s("x", *args, errno=errno)

    async def f(self, ok):
        await self.pr.wrn_s("w", wrnno=_WRN_A)
        {second}
"""


_PLANTED_PAIR = {("src/plant.py", "f", ("W", "A"), ("E", "B"))}


@pytest.mark.parametrize(
    ("second", "expected"),
    [
        ('await self.pr.err_s("e", errno=_ERR_B)', _PLANTED_PAIR),  # a warning then a fault for one occurrence
        ("await self._err(_ERR_B)", _PLANTED_PAIR),  # the same pair, the fault written through a wrapper
        ('await self.pr.wrn_s("w2", wrnno=_WRN_C)', set()),  # same kind
        ('if ok:\n            return\n        await self.pr.err_s("e", errno=_ERR_B)', _PLANTED_PAIR),  # one path still reaches it
        ('return\n        await self.pr.err_s("e", errno=_ERR_B)', set()),  # a return between ends the path
        ("await self.g()", set()),  # another function's entries are never paired
    ],
)
def test_the_scan_bites_a_planted_pair(second: str, expected: "set[Pair]") -> None:
    source = _PLANT.format(second=second) + "\n    async def g(self):\n        await self.pr.err_s('g', errno=_ERR_D)\n"
    pairs = _pairs([_parse("src/plant.py", source)])
    assert pairs == expected, _describe(pairs)


def test_the_scan_sees_a_handler_entered_after_a_warning() -> None:
    source = "async def f(pr):\n    try:\n        await pr.wrn_s('w', wrnno=_WRN_A)\n        step()\n    except OSError:\n        await pr.err_s('e', errno=_ERR_B)\n"
    assert _pairs([_parse("src/plant.py", source)]) == {("src/plant.py", "f", ("W", "A"), ("E", "B"))}


def test_a_second_fault_after_a_fault_passes() -> None:
    source = "async def f(pr):\n    await pr.err_s('a', errno=_ERR_A)\n    await pr.err_s('b', errno=_ERR_B)\n"
    assert not _pairs([_parse("src/plant.py", source)])
