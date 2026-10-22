"""Parses driver-declared bus requirements from the `# @requires bus.<field><op><value>` comment
tag placed at module level near `_WIRING`/`_VAL_*` (SPECIFICATION.md Part L.5) - a plain
comment, never a real Python value, and never silently invisible (see tag_comments.py)."""

import math
import operator
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from buildgen.errors import BuildError
from buildgen.tag_comments import check_for_near_miss_tags, iter_comment_tokens, specs_for

if TYPE_CHECKING:
    from buildgen.model import TomlDoc

_SPECS = specs_for("requires")

# "#+" so a "## @requires ..." section-style comment is accepted rather than reported malformed.
# The value may not begin with an operator character, so a truncated "bus.timeout>=" fails as a
# malformed tag instead of silently re-splitting into op ">" and value "=".
_TAG_RE = re.compile(r"#+\s*@requires\s+bus\.(?P<field>\w+)\s*(?P<op>>=|<=|==|!=|>|<)\s*(?P<value>[^\s<>=!]\S*)")

_OPS: dict[str, Callable[[float, float], bool]] = {
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
    tokens = iter_comment_tokens(path, device, instance_label)
    tags = []
    exact_matches: set[tuple[int, int]] = set()
    for tok in tokens:
        m = _TAG_RE.fullmatch(tok.text.strip())
        if m is None:
            continue
        exact_matches.add((tok.lineno, tok.col))
        if tok.inside_block:
            raise BuildError(
                device,
                f"{path}:{tok.lineno}: @requires tag must be at module level (see _WIRING/_VAL_*'s own placement), not inside a class/function body: {tok.text.strip()!r}",
                rule="tag.not-module-level",
                fix="move the tag to module level, beside the driver's schema",
                instance=instance_label,
            )
        try:
            value = _coerce(m.group("value"))
        except ValueError:
            raise BuildError(
                device,
                f"{path}:{tok.lineno}: malformed @requires value {m.group('value')!r}",
                rule="tag.not-a-number",
                fix="write the value as an int or a float",
                instance=instance_label,
            ) from None
        if not math.isfinite(value):
            # float() reads nan/inf, and every comparison with one is silently false or true.
            raise BuildError(
                device,
                f"{path}:{tok.lineno}: @requires value {m.group('value')!r} is not a finite number",
                rule="tag.non-finite-number",
                fix="write a finite number",
                instance=instance_label,
            )
        tags.append(RequiresTag(m.group("field"), m.group("op"), value, m.group(0).strip()))
    check_for_near_miss_tags(tokens, path, device, instance_label, exact_matches, _SPECS)
    return tuple(tags)


def check_requires_tags(tags: "tuple[RequiresTag, ...]", bus_table: "TomlDoc", device: str, instance_label: str, bus_name: str) -> None:
    for tag in tags:
        actual = bus_table.get(tag.field)
        if actual is None:
            raise BuildError(
                device,
                f"bus.{bus_name} is missing field {tag.field!r}, required by {instance_label} ({tag.raw!r})",
                rule="requires.missing-bus-field",
                fix=f"declare {tag.field} on [bus.{bus_name}] so that {tag.field} {tag.op} {tag.value}",
                instance=instance_label,
                field=tag.field,
            )
        # Compared only as a number: _check_bus_tables() validates only the bus fields it knows by
        # name, and Python would compare a bool as 0/1.
        if not isinstance(actual, (int, float)) or isinstance(actual, bool):
            raise BuildError(
                device,
                f"bus.{bus_name}.{tag.field}={actual!r} is not comparable to {instance_label}'s requirement {tag.raw!r} (wrong type)",
                rule="requires.not-comparable",
                fix=f"write bus.{bus_name}.{tag.field} as a number",
                instance=instance_label,
                field=tag.field,
            )
        if not _OPS[tag.op](actual, tag.value):
            raise BuildError(
                device,
                f"bus.{bus_name}.{tag.field}={actual!r} does not satisfy {instance_label}'s requirement {tag.raw!r}",
                rule="requires.unsatisfied",
                fix=f"set bus.{bus_name}.{tag.field} so that {tag.field} {tag.op} {tag.value}, or move {instance_label} to a bus that meets it",
                instance=instance_label,
                field=tag.field,
            )
