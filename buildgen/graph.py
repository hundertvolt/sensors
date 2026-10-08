"""Topological construction ordering (SPECIFICATION.md Part L.2's ordering hazard #1, SPECIFICATION.md
Part C.14.2): a consumer references its producer's already-built object, so the producer is
constructed first. Rejects a cycle as a build-time error."""

from typing import TypeAlias

from buildgen.errors import BuildError
from buildgen.model import DeviceModel, instance_label, resolve_instance_key

Node: TypeAlias = "str | tuple[str, str]"

_FIXED_INFRA_ORDER = ("conn", "ntp", "sysfunct")


def _node_label(node: Node) -> str:
    return node if isinstance(node, str) else instance_label(node)


def _urgency(nodes: "list[Node]", dependents: "dict[Node, list[Node]]", priority: "dict[Node, int]") -> "dict[Node, int]":
    # The lowest priority among a node and everything that transitively waits on it. A cycle stops
    # the walk at the repeated node; build_construction_order() reports it afterwards.
    urgency: dict[Node, int] = {}

    def visit(n: Node, path: "set[Node]") -> int:
        if n in urgency:
            return urgency[n]
        best = priority[n]
        for d in dependents[n]:
            if d not in path:
                best = min(best, visit(d, path | {n}))
        urgency[n] = best
        return best

    for n in nodes:
        visit(n, set())
    return urgency


def build_construction_order(model: DeviceModel) -> "list[Node]":
    nodes: list[Node] = list(_FIXED_INFRA_ORDER) + list(model.instances.keys())
    deps: dict[Node, set[Node]] = {n: set() for n in nodes}

    deps["ntp"].add("conn")
    deps["sysfunct"].add("ntp")

    device = model.doc.get("device")
    device_wiring = device.get("wiring") if isinstance(device, dict) else None
    if not isinstance(device_wiring, dict):
        device_wiring = {}  # absent; validate.py refuses a [device] or [device].wiring that is not a table
    fram_target = device_wiring.get("fram_target")
    if isinstance(fram_target, str):
        fram_key = resolve_instance_key(model, fram_target)
        # sysfunct/conn/ntp are mandatory infra that inherit the device's FRAM chip implicitly
        # (Part C.14), so each must be constructed after fram and depends on it here. webserver
        # needs no entry: it has no node in this graph, codegen always emitting it last.
        deps["sysfunct"].add(fram_key)
        deps["conn"].add(fram_key)
        deps["ntp"].add(fram_key)
    led_target = device_wiring.get("led_target")
    if isinstance(led_target, str):
        deps["conn"].add(resolve_instance_key(model, led_target))  # passed to conn as ext_led

    for spec in model.instances.values():
        if spec.driver in ("sgp40", "notification"):
            deps[spec.key].add("ntp")  # built with ntp.ntp_issynced / ntp.cettime
        for wf in spec.wiring_schema:
            value = spec.wiring.get(wf.toml_field)
            # An instance reference is a string; an absent optional field or Part L.6.2's
            # {default = true, ...} table has no producer to depend on (validate.py refused the rest).
            if isinstance(value, str):
                deps[spec.key].add(resolve_instance_key(model, value))
        # {source, field} references come from Part L.6.3's value-wiring fields and, on the
        # notification, its warn_* signals (Part C.14.3): no other sub-table makes an edge. A
        # {default = true, ...} selection has no "source" key, so it makes none either.
        source_fields = [vwf.toml_field for vwf in spec.value_wiring_schema]
        if spec.driver == "notification":
            source_fields += [toml_field for toml_field in spec.wiring if toml_field.startswith("warn_")]
        for toml_field in source_fields:
            value = spec.wiring.get(toml_field)
            source = value.get("source") if isinstance(value, dict) else None
            if isinstance(source, str):
                deps[spec.key].add(resolve_instance_key(model, source))

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
    # A node something earlier waits on inherits that urgency (the NeoPixel conn is built with goes
    # right after fram, ahead of the sensors), then its own priority breaks the tie.
    urgency = _urgency(nodes, dependents, priority)

    def sort_key(n: Node) -> "tuple[int, int]":
        return urgency[n], priority[n]

    ready = sorted((n for n in nodes if in_degree[n] == 0), key=sort_key)
    order: list[Node] = []
    while ready:
        ready.sort(key=sort_key)
        n = ready.pop(0)
        order.append(n)
        for dep in dependents[n]:
            in_degree[dep] -= 1
            if in_degree[dep] == 0:
                ready.append(dep)

    if len(order) != len(nodes):
        remaining = sorted(_node_label(n) for n in nodes if n not in order)
        raise BuildError(
            model.device,
            f"wiring dependency cycle detected among: {remaining}",
            rule="wiring.cycle",
            fix="remove one of the wiring references that make these instances wait on each other",
        )

    model.construction_order = order
    return order
