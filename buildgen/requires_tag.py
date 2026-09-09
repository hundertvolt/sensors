"""Parses driver-declared bus requirements from the `# @requires bus.<field><op><value>` comment
tag (BUILD_CHAIN_PLAN.md's "Build/generator script quality bar") - a plain comment, deliberately
never a real Python value: nothing the running firmware itself reads should become a real
frozen-bytecode constant just to serve this generator. Grammar: `# @requires bus.<field><op><value>`
placed at module level near `_WIRING`/`_VAL_*`, e.g. `# @requires bus.timeout>=200000`."""

import operator
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from buildgen.errors import BuildError

_TAG_RE = re.compile(r"#\s*@requires\s+bus\.(?P<field>\w+)\s*(?P<op>>=|<=|==|!=|>|<)\s*(?P<value>\S+)")

_OPS: dict[str, Callable[[Any, Any], bool]] = {
    ">=": operator.ge,
    "<=": operator.le,
    "==": operator.eq,
    "!=": operator.ne,
    ">": operator.gt,
    "<": operator.lt,
}


@dataclass(frozen=True)
class RequiresTag:
    field: str
    op: str
    value: "int | float"
    raw: str


def _coerce(raw: str) -> "int | float":
    try:
        return int(raw)
    except ValueError:
        return float(raw)


def parse_requires_tags(path: Path, device: str, instance_label: str) -> tuple[RequiresTag, ...]:
    tags = []
    for lineno, line in enumerate(path.read_text().splitlines(), start=1):
        m = _TAG_RE.search(line)
        if m is None:
            continue
        try:
            value = _coerce(m.group("value"))
        except ValueError:
            raise BuildError(device, f"{path}:{lineno}: malformed @requires value {m.group('value')!r}", instance=instance_label) from None
        tags.append(RequiresTag(m.group("field"), m.group("op"), value, m.group(0).strip()))
    return tuple(tags)


def check_requires_tags(tags: "tuple[RequiresTag, ...]", bus_table: dict, device: str, instance_label: str, bus_name: str) -> None:
    for tag in tags:
        actual = bus_table.get(tag.field)
        if actual is None:
            raise BuildError(device, f"bus.{bus_name} is missing field {tag.field!r}, required by {instance_label} ({tag.raw!r})", instance=instance_label, field=tag.field)
        if not _OPS[tag.op](actual, tag.value):
            raise BuildError(
                device,
                f"bus.{bus_name}.{tag.field}={actual!r} does not satisfy {instance_label}'s requirement {tag.raw!r}",
                instance=instance_label,
                field=tag.field,
            )
