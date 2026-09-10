"""Parses driver-declared bus requirements from the `# @requires bus.<field><op><value>` comment
tag (BUILD_CHAIN_PLAN.md's "Build/generator script quality bar") - a plain comment, deliberately
never a real Python value: nothing the running firmware itself reads should become a real
frozen-bytecode constant just to serve this generator. Grammar: `# @requires bus.<field><op><value>`
placed at module level near `_WIRING`/`_VAL_*`, e.g. `# @requires bus.timeout>=200000`.

A typo'd or misplaced attempt at this tag must never be silently invisible - buildgen/tag_comments.py's
standing rule, not specific to this tag. See that module's check_for_near_miss_tags() docstring for
the concrete incident this generalizes from."""

import operator
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from buildgen.errors import BuildError
from buildgen.tag_comments import check_for_near_miss_tags, iter_comment_tokens

# "#+" so a "## @requires ..." section-style comment is accepted rather than reported as
# malformed; the value may not start with an operator character, so a truncated
# "bus.timeout>=" fails as a malformed *tag* instead of silently re-splitting into op ">"
# and value "=".
_TAG_RE = re.compile(r"#+\s*@requires\s+bus\.(?P<field>\w+)\s*(?P<op>>=|<=|==|!=|>|<)\s*(?P<value>[^\s<>=!]\S*)")

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
                instance=instance_label,
            )
        try:
            value = _coerce(m.group("value"))
        except ValueError:
            raise BuildError(device, f"{path}:{tok.lineno}: malformed @requires value {m.group('value')!r}", instance=instance_label) from None
        tags.append(RequiresTag(m.group("field"), m.group("op"), value, m.group(0).strip()))
    check_for_near_miss_tags(tokens, path, device, instance_label, exact_matches)
    return tuple(tags)


def check_requires_tags(tags: "tuple[RequiresTag, ...]", bus_table: dict, device: str, instance_label: str, bus_name: str) -> None:
    for tag in tags:
        actual = bus_table.get(tag.field)
        if actual is None:
            raise BuildError(device, f"bus.{bus_name} is missing field {tag.field!r}, required by {instance_label} ({tag.raw!r})", instance=instance_label, field=tag.field)
        try:
            satisfied = _OPS[tag.op](actual, tag.value)
        except TypeError:
            # A malformed TOML value (e.g. a string where the tag expects a number) must fail
            # loud as a BuildError, not surface as a raw, uncaught TypeError from the comparison
            # itself - _check_bus_tables() only validates the handful of bus fields it knows about
            # by name (scl_pin/sda_pin/frequency/...), not every field an @requires tag might name.
            raise BuildError(
                device,
                f"bus.{bus_name}.{tag.field}={actual!r} is not comparable to {instance_label}'s requirement {tag.raw!r} (wrong type)",
                instance=instance_label,
                field=tag.field,
            ) from None
        if not satisfied:
            raise BuildError(
                device,
                f"bus.{bus_name}.{tag.field}={actual!r} does not satisfy {instance_label}'s requirement {tag.raw!r}",
                instance=instance_label,
                field=tag.field,
            )
