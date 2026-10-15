"""The NTP store the twin plants before a boot holds every key of the product's NTP store, each one the twin does not set
at the product's own default, so a fresh boot warns about none (the config manager warns once per missing key). Both
sides are read by AST, never imported."""

import ast

from _repo_scan import REPO_ROOT

_CLIENT = REPO_ROOT / "src" / "asy_ntp_client.py"
_WRITER = REPO_ROOT / "digital_twin" / "unixport" / "_offline_ntp_config.py"
_SET_BY_THE_TWIN = {"NTPHost", "DNSFallback"}


def _assigned(tree: ast.Module) -> "dict[str, ast.expr]":
    # Module-level `NAME = value` and `NAME: type = value`.
    found = {node.targets[0].id: node.value for node in tree.body if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name)}
    found.update({node.target.id: node.value for node in tree.body if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.value is not None})
    return found


def _const_arg(value: ast.expr) -> object:
    assert isinstance(value, ast.Call) and ast.unparse(value.func) == "const", ast.unparse(value)
    literal: object = ast.literal_eval(value.args[0])
    return literal


def _rows(value: ast.expr) -> "list[tuple[object, ...]]":
    literal = _const_arg(value)
    assert isinstance(literal, tuple) and all(isinstance(row, tuple) and len(row) > 2 for row in literal), literal
    return list(literal)


def product_store() -> "tuple[str, dict[str, object]]":
    # NTPClient's store name and the schema it hands its config manager (super().__init__'s third argument): name -> default.
    tree = ast.parse(_CLIENT.read_text(encoding="utf-8"))
    consts = _assigned(tree)
    init = next(n for n in ast.walk(tree) if isinstance(n, ast.Call) and ast.unparse(n.func) == "super().__init__")
    rows = [row for name in ast.walk(init.args[2]) if isinstance(name, ast.Name) for row in _rows(consts[name.id])]
    return str(_const_arg(consts["_NAME"])), {str(row[0]): row[2] for row in rows}


def planted_store() -> "tuple[str, dict[str, object]]":
    # The writer's store name and the defaults it plants beside the two keys it sets.
    consts = _assigned(ast.parse(_WRITER.read_text(encoding="utf-8")))
    name: object = ast.literal_eval(consts["_NTP_STORE_NAME"])
    defaults: object = ast.literal_eval(consts["_STORE_DEFAULTS"])
    assert isinstance(name, str) and isinstance(defaults, dict), (name, defaults)
    return name, {str(key): value for key, value in defaults.items()}


def test_the_planted_store_has_every_key_of_the_product_store() -> None:
    (_, product), (_, planted) = product_store(), planted_store()
    assert len(product) == 6, f"the NTP store's schema reads {sorted(product)} - the parse found the wrong call"
    assert set(planted) | _SET_BY_THE_TWIN == set(product), f"planted {sorted(set(planted) | _SET_BY_THE_TWIN)}, the store reads {sorted(product)}"


def test_each_planted_default_is_the_products_and_the_store_name_matches() -> None:
    (product_name, product), (planted_name, planted) = product_store(), planted_store()
    assert planted_name == product_name
    assert {key: value for key, value in planted.items() if product.get(key) != value} == {}, f"the product's defaults: {product}"
