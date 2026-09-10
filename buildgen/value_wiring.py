"""Parses a driver module's `# @value-wiring <toml_field> <source_kwarg> <field_kwarg>
<required|optional>` comment tags - the per-value measurement wiring that generalizes `warn_*`'s
`{source, field}` shape to any module consuming one scalar out of another's `get_data()`."""

import re
from dataclasses import dataclass
from pathlib import Path

from buildgen.errors import BuildError
from buildgen.tag_comments import KNOWN_TAGS, check_for_near_miss_tags, iter_comment_tokens

_SPECS = tuple(spec for spec in KNOWN_TAGS if spec.name == "value-wiring")

_TAG_RE = re.compile(r"#+\s*@value-wiring\s+(?P<toml_field>\w+)\s+(?P<source_kwarg>\w+)\s+(?P<field_kwarg>\w+)\s+(?P<required>required|optional)\s*$")


@dataclass(frozen=True)
class ValueWiringField:
    toml_field: str
    source_kwarg: str
    field_kwarg: str
    required: bool


def parse_value_wiring(path: Path, device: str, driver: str) -> "tuple[ValueWiringField, ...]":
    tokens = iter_comment_tokens(path, device, driver)
    fields = []
    exact_matches: set[tuple[int, int]] = set()
    for tok in tokens:
        m = _TAG_RE.fullmatch(tok.text.strip())
        if m is None:
            continue
        exact_matches.add((tok.lineno, tok.col))
        if tok.inside_block:
            raise BuildError(
                device,
                f"{path}:{tok.lineno}: @value-wiring tag must be at module level, not inside a class/function body: {tok.text.strip()!r}",
                instance=driver,
            )
        fields.append(ValueWiringField(m.group("toml_field"), m.group("source_kwarg"), m.group("field_kwarg"), m.group("required") == "required"))
    seen: set[str] = set()
    for f in fields:
        if f.toml_field in seen:
            raise BuildError(device, f"{path}: declares two @value-wiring tags for {f.toml_field!r} - each TOML field is wired exactly once", instance=driver, field=f.toml_field)
        seen.add(f.toml_field)
    check_for_near_miss_tags(tokens, path, device, driver, exact_matches, _SPECS)
    return tuple(fields)
