"""Seeded mutation fuzz of the build (SPECIFICATION.md Part L.5): mutated device documents run through
validation, ordering and code generation, and the only outcomes allowed are a generated module or a
BuildError - any other exception is a generator bug, reported with the seed and the case that hit it."""

import copy
import random
from pathlib import Path
from typing import TYPE_CHECKING

import tomllib
from _devices import DEVICE_NAMES, device_toml
from _toml_fixtures import base_doc, write_doc

from buildgen.codegen import generate_module_source
from buildgen.errors import BuildError
from buildgen.graph import build_construction_order
from buildgen.validate import build_model

if TYPE_CHECKING:
    from _toml_fixtures import TomlDoc

_SEED = 20261008
_CASES = 2000
# One value of each TOML type a retyped leaf takes; _dump_scalar() writes the list and the table as real TOML.
_RETYPED: "tuple[object, ...]" = (7, -1, "x", True, [1, "a"], {"k": 1}, {})
_PIN_KEYS = frozenset({"scl_pin", "sda_pin", "sck_pin", "mosi_pin", "miso_pin", "tx_pin", "rx_pin", "cs_pin", "irq_pin", "pin"})

_Path = tuple["str | int", ...]


def _paths(value: object, prefix: "_Path" = ()) -> "list[_Path]":
    # Every key or element path below the document root, containers and leaves alike, in document order.
    found: list[_Path] = []
    children = value.items() if isinstance(value, dict) else enumerate(value) if isinstance(value, list) else ()
    for key, child in children:
        found.append((*prefix, key))
        found.extend(_paths(child, (*prefix, key)))
    return found


def _step(node: object, key: "str | int") -> object:
    # One step down a path: a table by key, an array by index.
    if isinstance(node, dict) and isinstance(key, str):
        return node[key]
    if isinstance(node, list) and isinstance(key, int):
        return node[key]
    return None


def _parent(doc: "TomlDoc", path: "_Path") -> object:
    node: object = doc
    for key in path[:-1]:
        node = _step(node, key)
    return node


def _get(doc: "TomlDoc", path: "_Path") -> object:
    return _step(_parent(doc, path), path[-1])


def _set(doc: "TomlDoc", path: "_Path", value: object) -> None:
    parent, key = _parent(doc, path), path[-1]
    if isinstance(parent, dict) and isinstance(key, str):
        parent[key] = value
    if isinstance(parent, list) and isinstance(key, int):
        parent[key] = value


def _delete(doc: "TomlDoc", path: "_Path") -> None:
    parent, key = _parent(doc, path), path[-1]
    if isinstance(parent, dict) and isinstance(key, str):
        del parent[key]
    if isinstance(parent, list) and isinstance(key, int):
        del parent[key]


def _labels(doc: "TomlDoc") -> "list[str]":
    # Every wiring-style reference the document's instances answer to, plus one that answers to nothing.
    labels = ["nothing_here"]
    instances = doc.get("instance", [])
    for inst in instances if isinstance(instances, list) else []:
        if isinstance(inst, dict) and isinstance(inst.get("driver"), str):
            ext = inst.get("name_ext", "")
            labels.append(f"{inst['driver']}_{ext}" if isinstance(ext, str) and ext else str(inst["driver"]))
    return labels


def _mutate(rng: random.Random, doc: "TomlDoc") -> str:
    # One mutation of `doc` in place; returns what it did, for the failure report.
    paths = _paths(doc)
    kind = rng.choice(("delete", "retype", "swap-pins", "duplicate", "rewire"))
    if kind == "delete" and paths:
        path = rng.choice(paths)
        _delete(doc, path)
        return f"delete {path}"
    if kind == "retype":
        leaves = [p for p in paths if not isinstance(_get(doc, p), (dict, list))]
        if leaves:
            path, value = rng.choice(leaves), copy.deepcopy(rng.choice(_RETYPED))
            _set(doc, path, value)
            return f"retype {path} = {value!r}"
    pins = [p for p in paths if p[-1] in _PIN_KEYS]
    if kind == "swap-pins" and len(pins) > 1:
        a, b = rng.sample(pins, 2)
        first, second = _get(doc, a), _get(doc, b)
        _set(doc, a, second)
        _set(doc, b, first)
        return f"swap {a} {b}"
    instances = doc.get("instance")
    if kind == "duplicate" and isinstance(instances, list) and instances:
        twin = copy.deepcopy(rng.choice(instances))
        if isinstance(twin, dict) and rng.random() < 0.5:
            twin["name_ext"] = f"x{rng.randrange(100)}"
        instances.append(twin)
        return f"duplicate {twin!r}"
    wiring = [p for p in paths if "wiring" in p and isinstance(_get(doc, p), str)]
    if wiring:
        path, label = rng.choice(wiring), rng.choice(_labels(doc))
        _set(doc, path, label)
        return f"rewire {path} = {label!r}"
    return "none"


def test_a_mutated_device_builds_or_fails_with_a_build_error(tmp_path: Path, repo_root: Path) -> None:
    # Every case rewrites the one fixture file (no per-case file or directory): about 2,000 small rewrites of one inode.
    src_dir = repo_root / "src"
    bases: list[TomlDoc] = [base_doc(), *(tomllib.loads(device_toml(d).read_text()) for d in DEVICE_NAMES)]
    rng = random.Random(_SEED)  # noqa: S311 - a seeded case generator, no secret
    built = refused = 0
    for case in range(_CASES):
        doc = copy.deepcopy(rng.choice(bases))
        did = [_mutate(rng, doc) for _ in range(rng.randint(1, 3))]
        path = write_doc(tmp_path, "fixture", doc)
        try:
            model = build_model(path, src_dir)
            generate_module_source(model, build_construction_order(model), "2026-01-01T00:00:00Z", src_dir)
        except BuildError:
            refused += 1
            continue
        except Exception as e:
            e.add_note(f"seed {_SEED} case {case}: {did} raised something other than a BuildError")
            raise
        built += 1
    assert built and refused, f"the corpus never reached one of the two outcomes: {built} built, {refused} refused"
