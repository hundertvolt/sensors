"""Topological construction ordering (SPECIFICATION.md Part L.2's ordering hazard #1, SPECIFICATION.md
Part C.14.2): a consumer references its producer's already-built object, so the producer is
constructed first. Rejects a cycle as a build-time error."""

from typing import TypeAlias

from buildgen.errors import BuildError
from buildgen.model import DeviceModel, instance_label, resolve_instance_key

Node: TypeAlias = "str | tuple[str, str]"

_FIXED_INFRA_ORDER = ("conn", "ntp", "sysfunct")


def _node_label(node: object) -> str:
    return node if isinstance(node, str) else instance_label(node)  # type: ignore[arg-type]


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

    device_wiring = model.doc.get("device", {}).get("wiring", {})
    fram_target = device_wiring.get("fram_target")
    if fram_target is not None:
        fram_key = resolve_instance_key(model, fram_target)
        # sysfunct/conn/ntp are mandatory infra that inherit the device's FRAM chip implicitly
        # (Part C.14), so each must be constructed after fram and depends on it here. webserver
        # needs no entry: it has no node in this graph, codegen always emitting it last.
        deps["sysfunct"].add(fram_key)
        deps["conn"].add(fram_key)
        deps["ntp"].add(fram_key)
    led_target = device_wiring.get("led_target")
    if led_target is not None:
        deps["conn"].add(resolve_instance_key(model, led_target))  # passed to conn as ext_led

    for spec in model.instances.values():
        if spec.driver in ("sgp40", "notification"):
            deps[spec.key].add("ntp")  # built with ntp.ntp_issynced / ntp.cettime
        for wf in spec.wiring_schema:
            value = spec.wiring.get(wf.toml_field)
            if value is None:
                continue  # optional and absent - validate.py already confirmed required ones are present
            if isinstance(value, dict) and value.get("default") is True:
                continue  # SPECIFICATION.md Part L.6.2's wiring defaults - no producer to depend on
            deps[spec.key].add(resolve_instance_key(model, value))
        # {source, field} references - warn_* (SPECIFICATION.md Part C.14.3) and Part L.6.3's generalized
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
        raise BuildError(model.device, f"wiring dependency cycle detected among: {remaining}")

    model.construction_order = order
    return order
