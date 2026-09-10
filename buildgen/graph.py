"""Topological construction ordering (BUILD_CHAIN_PLAN.md's "ordering hazard #1"/SPECIFICATION.md
Part C.14.2): a consumer's constructor call references its producer's already-built Python object
directly, so the producer must be constructed first. Sorts by `_WIRING` dependency (kwarg/attr
modes only - "setter" wiring, e.g. `conn.set_ext_led(pixel)`, is a post-construction call emitted
once everything already exists, so it never gates construction order - see codegen.py) plus two
fixed mandatory-infra edges (`ntp` needs `conn`, `sysfunct` needs `ntp`) and one conditional one
(`sysfunct` needs its `device.wiring.fram_target` instance, if set). Rejects a cycle as a
build-time error, per BUILD_CHAIN_PLAN.md's own explicit requirement."""

from typing import TypeAlias

from buildgen.errors import BuildError
from buildgen.model import DeviceModel, instance_label, resolve_instance_key

Node: TypeAlias = "str | tuple[str, str]"

_FIXED_INFRA_ORDER = ("conn", "ntp", "sysfunct")


def _node_label(node: object) -> str:
    return node if isinstance(node, str) else instance_label(node)  # type: ignore[arg-type]


def build_construction_order(model: DeviceModel) -> "list[Node]":
    nodes: list[Node] = list(_FIXED_INFRA_ORDER) + list(model.instances.keys())
    deps: dict[Node, set[Node]] = {n: set() for n in nodes}

    deps["ntp"].add("conn")
    deps["sysfunct"].add("ntp")

    device_wiring = model.doc.get("device", {}).get("wiring", {})
    fram_target = device_wiring.get("fram_target")
    if fram_target is not None:
        deps["sysfunct"].add(resolve_instance_key(model, fram_target))

    for spec in model.instances.values():
        for wf in spec.wiring_schema:
            if wf.mode == "setter":
                continue  # post-construction call, not a construction-order dependency
            value = spec.wiring.get(wf.toml_field)
            if value is None:
                continue  # optional and absent - validate.py already confirmed required ones are present
            if isinstance(value, dict) and value.get("default") is True:
                continue  # §2's wiring-defaults mechanism - no producer instance to depend on
            deps[spec.key].add(resolve_instance_key(model, value))
        # {source, field} references - warn_* (SPECIFICATION.md Part C.14.3) and §2.9's generalized
        # per-value measurement wiring share this exact shape, so one loop covers both; a
        # {default: true, ...} selection has no "source" key at all, naturally excluded here too.
        for value in spec.wiring.values():
            if isinstance(value, dict) and "source" in value:
                deps[spec.key].add(resolve_instance_key(model, value["source"]))

    # Stable priority tie-break: mandatory infra first (in its own fixed order), then original TOML
    # declaration order - so a device with no cross-instance dependencies at all still reproduces a
    # deterministic, human-predictable order.
    priority: dict[Node, int] = {n: i for i, n in enumerate(_FIXED_INFRA_ORDER)}
    priority.update({spec.key: len(_FIXED_INFRA_ORDER) + spec.order_index for spec in model.instances.values()})

    in_degree = {n: len(d) for n, d in deps.items()}
    dependents: dict[Node, list[Node]] = {n: [] for n in nodes}
    for n, ds in deps.items():
        for d in ds:
            dependents[d].append(n)

    ready = sorted((n for n in nodes if in_degree[n] == 0), key=lambda n: priority[n])
    order: list[Node] = []
    while ready:
        ready.sort(key=lambda n: priority[n])
        n = ready.pop(0)
        order.append(n)
        for dep in dependents[n]:
            in_degree[dep] -= 1
            if in_degree[dep] == 0:
                ready.append(dep)

    if len(order) != len(nodes):
        remaining = sorted(_node_label(n) for n in nodes if n not in order)
        raise BuildError(model.device, f"wiring dependency cycle detected among: {remaining}")

    model.construction_order = order
    return order
