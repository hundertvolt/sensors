"""tests_hardware/http_client.py and digital_twin/_http_client.py keep one shape, read by ast (the twin's is MicroPython
code, never imported here): the response's attributes, json() returning a JSON object alias and refusing a drained
body, fetch()'s parameters in order (the twin's being async the one difference) and CeilingRefusedError in both."""

import ast
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
CLIENTS = {"hardware": REPO_ROOT / "tests_hardware" / "http_client.py", "twin": REPO_ROOT / "digital_twin" / "_http_client.py"}
# The agreed shape: every attribute a response carries, and fetch()'s parameters in order.
RESPONSE_ATTRIBUTES = ("status_code", "headers", "body", "drained")
FETCH_PARAMETERS = ("host", "port", "method", "path", "json_body", "timeout_s", "read_body")
AGREED: "dict[str, object]" = {"refusal class": True, "response attributes": tuple(sorted(RESPONSE_ATTRIBUTES)), "json() return": "object alias", "json() refuses drained": True, "fetch parameters": FETCH_PARAMETERS}


def _alias_value(tree: ast.Module, name: str) -> "ast.expr | None":
    # What `name` is bound to: an assignment in the module (a TYPE_CHECKING block included), else in the src/ module it
    # is imported from.
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in node.targets):
            return node.value
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == name and node.value is not None:
            return node.value
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and any(alias.name == name for alias in node.names):
            source = REPO_ROOT / "src" / f"{node.module}.py"
            return _alias_value(ast.parse(source.read_text(encoding="utf-8")), name) if source.is_file() else None
    return None


def _drift(trees: "dict[str, ast.Module]") -> "list[str]":
    # Every member where the clients part from the agreed shape or from each other, each named with what every side has.
    shapes = {side: _shape(tree) for side, tree in trees.items()}
    found = []
    for member in ("refusal class", "response attributes", "json() return", "json() refuses drained", "fetch parameters", "fetch keyword-only"):
        values = {side: shape[member] for side, shape in shapes.items()}
        if len(set(values.values())) > 1 or (member in AGREED and set(values.values()) != {AGREED[member]}):
            found.append(f"{member}: {values}")
    kinds = (shapes["hardware"]["fetch kind"], shapes["twin"]["fetch kind"])
    if kinds != ("sync", "async"):
        found.append(f"fetch kind: hardware {kinds[0]}, twin {kinds[1]}")
    return found


def _json_return(tree: ast.Module, method: "ast.FunctionDef | None") -> str:
    # "object alias" when json() is annotated with a name bound to dict[str, <JSON value>]; what it is otherwise.
    if method is None or method.returns is None:
        return "unannotated"
    returns = method.returns
    name = returns.value if isinstance(returns, ast.Constant) and isinstance(returns.value, str) else ast.unparse(returns)
    value = _alias_value(tree, name)
    if isinstance(value, ast.Subscript) and ast.unparse(value.value) == "dict" and isinstance(value.slice, ast.Tuple) and ast.unparse(value.slice.elts[0]) == "str":
        return "object alias"
    return f"{name} = {ast.unparse(value) if value is not None else '<unbound>'}"


def _shape(tree: ast.Module) -> "dict[str, object]":
    classes = {node.name: node for node in tree.body if isinstance(node, ast.ClassDef)}
    response = classes.get("HttpResponse")
    attributes: set[str] = set()
    json_method = None
    if response is not None:
        attributes |= {node.target.id for node in response.body if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name)}
        attributes |= {t.attr for node in ast.walk(response) if isinstance(node, ast.Assign) for t in node.targets if isinstance(t, ast.Attribute) and ast.unparse(t.value) == "self"}
        json_method = next((node for node in response.body if isinstance(node, ast.FunctionDef) and node.name == "json"), None)
    refuses = json_method is not None and any(
        isinstance(node, ast.If) and ast.unparse(node.test) == "self.drained" and any(isinstance(stmt, ast.Raise) and stmt.exc is not None and ast.unparse(stmt.exc).startswith("ValueError(") for stmt in node.body)
        for node in ast.walk(json_method)
    )
    fetch = next((node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "fetch"), None)
    arguments = fetch.args if fetch is not None else ast.arguments(posonlyargs=[], args=[], kwonlyargs=[], kw_defaults=[], defaults=[])
    return {
        "refusal class": "CeilingRefusedError" in classes,
        "response attributes": tuple(sorted(attributes)),
        "json() return": _json_return(tree, json_method),
        "json() refuses drained": refuses,
        "fetch parameters": tuple(a.arg for a in [*arguments.posonlyargs, *arguments.args, *arguments.kwonlyargs]),
        "fetch keyword-only": tuple(a.arg for a in arguments.kwonlyargs),
        "fetch kind": None if fetch is None else "async" if isinstance(fetch, ast.AsyncFunctionDef) else "sync",
    }


def test_the_two_clients_keep_one_shape() -> None:
    assert _drift({side: ast.parse(path.read_text(encoding="utf-8")) for side, path in CLIENTS.items()}) == []


@pytest.mark.parametrize(
    ("edit", "member"),
    [
        (("self.drained = drained", "self.kept = drained"), "response attributes"),
        (('    json_body: "dict[str, object] | None" = None,\n    timeout_s: "float | None" = None,\n', '    timeout_s: "float | None" = None,\n    json_body: "dict[str, object] | None" = None,\n'), "fetch parameters"),
        (("class CeilingRefusedError(OSError):", "class RefusedError(OSError):"), "refusal class"),
        (("        if self.drained:\n            raise ValueError", "        if self.drained:\n            raise RuntimeError"), "json() refuses drained"),
        (('def json(self) -> "JsonDict":', 'def json(self) -> "object":'), "json() return"),
        (("async def fetch(", "def fetch("), "fetch kind"),
    ],
    ids=["attribute", "parameter-order", "refusal-class", "drained-refusal", "json-return", "fetch-kind"],
)
def test_a_drift_in_the_twin_client_fails_naming_the_member(edit: "tuple[str, str]", member: str) -> None:
    twin = CLIENTS["twin"].read_text(encoding="utf-8")
    assert twin.count(edit[0]) == 1, f"the bite's anchor {edit[0]!r} moved"
    trees = {"hardware": ast.parse(CLIENTS["hardware"].read_text(encoding="utf-8")), "twin": ast.parse(twin.replace(edit[0], edit[1]))}
    assert [line.split(":")[0] for line in _drift(trees)] == [member]
