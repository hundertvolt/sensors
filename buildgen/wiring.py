"""Parses a driver module's `# @wiring <toml_field> <ProducerClass> <target> <required|optional>
<kwarg|attr|setter>` comment tags (SPECIFICATION.md Part C.14.2 documents the shape and all three
modes) - a comment, never a real Python value, per BUILD_CHAIN_PLAN.md's quality bar."""

import re
from dataclasses import dataclass
from pathlib import Path

from buildgen.errors import BuildError
from buildgen.tag_comments import KNOWN_TAGS, check_for_near_miss_tags, iter_comment_tokens

_MODES = ("kwarg", "attr", "setter")
_SPECS = tuple(spec for spec in KNOWN_TAGS if spec.name == "wiring")

# Every element is its own capture group with its own alternation, so dropping any one of the five
# leaves the line matching no tag at all - which check_for_near_miss_tags() then reports as a
# malformed @wiring tag rather than letting it pass as "no tag here".
_TAG_RE = re.compile(
    r"#+\s*@wiring\s+(?P<toml_field>\w+)\s+(?P<producer_class>\w+)\s+(?P<target>\w+)\s+(?P<required>required|optional)\s+(?P<mode>kwarg|attr|setter)\s*$"
)


@dataclass(frozen=True)
class WiringField:
    toml_field: str
    producer_class: str  # a plain class-name string (e.g. "SCD30_Reader") - never imported/resolved to a real type object
    target: str
    required: bool
    mode: str  # "kwarg" | "attr" | "setter"
    # mode decides how the resolved producer reaches its consumer (SPECIFICATION.md Part C.14.2):
    # "kwarg" passes the instance as a constructor kwarg named `target`; "attr" passes the
    # instance's `target` attribute/bound method instead (signal_sink wants `pixel.request_signal`,
    # not `pixel`); "setter" calls `<consumer>.<target>(<producer>)` once, after both exist, so it
    # gates nothing in construction order. Per-value measurement wiring is _VALUE_WIRING's
    # (value_wiring.py), not this tag's.


def parse_wiring(path: Path, device: str, driver: str) -> "tuple[WiringField, ...]":
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
                f"{path}:{tok.lineno}: @wiring tag must be at module level, not inside a class/function body: {tok.text.strip()!r}",
                instance=driver,
            )
        fields.append(WiringField(m.group("toml_field"), m.group("producer_class"), m.group("target"), m.group("required") == "required", m.group("mode")))
    duplicate = _first_duplicate([f.toml_field for f in fields])
    if duplicate is not None:
        raise BuildError(device, f"{path}: declares two @wiring tags for {duplicate!r} - each TOML field is wired exactly once", instance=driver, field=duplicate)
    check_for_near_miss_tags(tokens, path, device, driver, exact_matches, _SPECS)
    return tuple(fields)


def _first_duplicate(names: "list[str]") -> "str | None":
    seen: set[str] = set()
    for name in names:
        if name in seen:
            return name
        seen.add(name)
    return None
