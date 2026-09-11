"""Parses a driver module's `# @limits <field> <min>..<max>` / `# @limits <field> in {a, b}` comment
tags - a field's own unconditional domain, either a range (`*` on either side means that side is
unchecked, and `min == max` an exact value) or an enumerated set of legal ints."""

import re
from dataclasses import dataclass
from pathlib import Path

from buildgen.errors import BuildError
from buildgen.tag_comments import KNOWN_TAGS, check_for_near_miss_tags, iter_comment_tokens

_SPECS = tuple(spec for spec in KNOWN_TAGS if spec.name == "limits")

# Past the field name the payload is interpreted by hand below, so a broken bound reports which
# half is wrong rather than the whole line just failing to match. It must still carry range or
# choice-set punctuation to match at all, or an ordinary sentence that happens to start with
# "@limits" would be read as a tag with an unintelligible domain instead of as the prose it is.
_TAG_RE = re.compile(r"#+\s*@limits\s+(?P<field>\w+)\s+(?=.*(?:\.\.|[{}]))(?P<payload>\S.*?)\s*$")
_SET_RE = re.compile(r"^in\s*\{(?P<values>[^{}]*)\}$")
_RANGE_PARTS = 2  # a range payload is always exactly <min>..<max>


@dataclass(frozen=True)
class LimitField:
    toml_field: str
    choices: "frozenset[int] | None"  # enumerated legal values, if that shape was used - min/max are both None when this is set
    min: "int | float | None" = None
    max: "int | float | None" = None


def _number(raw: str, path: Path, lineno: int, device: str, driver: str, what: str) -> "int | float":
    try:
        return int(raw, 0)  # base 0 so a hex address literal (0x76) reads as itself
    except ValueError:
        pass
    try:
        return float(raw)
    except ValueError:
        raise BuildError(device, f"{path}:{lineno}: @limits {what} {raw!r} is not a number", instance=driver) from None


def _parse_payload(payload: str, path: Path, lineno: int, device: str, driver: str, field: str) -> "LimitField":
    set_match = _SET_RE.match(payload)
    if set_match is not None:
        raw_values = [v.strip() for v in set_match.group("values").split(",") if v.strip()]
        if not raw_values:
            raise BuildError(device, f"{path}:{lineno}: @limits {field} declares an empty choice set - no value could ever be legal", instance=driver, field=field)
        choices = set()
        for raw in raw_values:
            value = _number(raw, path, lineno, device, driver, "choice")
            if not isinstance(value, int):
                raise BuildError(device, f"{path}:{lineno}: @limits {field} choice {raw!r} must be an int, not a float", instance=driver, field=field)
            choices.add(value)
        return LimitField(field, frozenset(choices))

    parts = payload.split("..")
    if len(parts) != _RANGE_PARTS:
        raise BuildError(
            device,
            f"{path}:{lineno}: @limits {field} payload {payload!r} is neither a range (<min>..<max>, '*' for unbounded) nor a choice set (in {{a, b}})",
            instance=driver,
            field=field,
        )
    low_raw, high_raw = (p.strip() for p in parts)
    if not low_raw or not high_raw:
        raise BuildError(device, f"{path}:{lineno}: @limits {field} range {payload!r} is missing one of its bounds - use '*' for an unbounded side", instance=driver, field=field)
    low = None if low_raw == "*" else _number(low_raw, path, lineno, device, driver, "min")
    high = None if high_raw == "*" else _number(high_raw, path, lineno, device, driver, "max")
    if low is None and high is None:
        raise BuildError(device, f"{path}:{lineno}: @limits {field} declares '*..*', which checks nothing - drop the tag instead", instance=driver, field=field)
    if low is not None and high is not None and low > high:
        raise BuildError(device, f"{path}:{lineno}: @limits {field} range {low}..{high} is inverted - no value could ever be legal", instance=driver, field=field)
    return LimitField(field, None, low, high)


def parse_limits(path: Path, device: str, driver: str) -> "tuple[LimitField, ...]":
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
                f"{path}:{tok.lineno}: @limits tag must be at module level, not inside a class/function body: {tok.text.strip()!r}",
                instance=driver,
            )
        fields.append(_parse_payload(m.group("payload"), path, tok.lineno, device, driver, m.group("field")))
    seen: set[str] = set()
    for f in fields:
        if f.toml_field in seen:
            raise BuildError(device, f"{path}: declares two @limits tags for {f.toml_field!r} - one domain per field", instance=driver, field=f.toml_field)
        seen.add(f.toml_field)
    check_for_near_miss_tags(tokens, path, device, driver, exact_matches, _SPECS)
    return tuple(fields)
