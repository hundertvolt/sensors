"""The one test-side lookup of buildgen/error_catalog.json: code("E", "CALLBACK") is 14. Runs under the
MicroPython Unix port and host CPython (json only, the path relative to this file); an unknown or retired
name raises KeyError, so no expectation can pass on a stale literal after a renumbering."""

import json

_BY_NAME: "dict[str, dict[str, int]]" = {}


def _catalog_path() -> str:
    parts = __file__.rsplit("/", 1)
    return (parts[0] if len(parts) == 2 else ".") + "/../buildgen/error_catalog.json"


def _load() -> "dict[str, dict[str, int]]":
    with open(_catalog_path()) as f:
        catalog = json.load(f)
    by_name: dict[str, dict[str, int]] = {}
    for kind, rows in catalog["codes"].items():
        by_name[kind] = {row["name"]: int(num) for num, row in rows.items() if not row.get("retired")}
    return by_name


def code(kind: str, name: str) -> int:
    """The catalog number of `name` in `kind` ("E" or "W"); KeyError for an unknown or retired name."""
    if not _BY_NAME:
        _BY_NAME.update(_load())
    return _BY_NAME[kind][name]
