"""Parses the `# @web <Field> key=value ...` / `# @web-group key=value ...` website-definitions
comment-tag family, built on `buildgen.tag_comments`'s shared scanning/near-miss mechanism (never a
second, separately-tested detector). Grammar and design rationale: SPECIFICATION.md Part H.5.1."""

import re
from dataclasses import dataclass
from pathlib import Path

from buildgen.errors import BuildError
from buildgen.tag_comments import KNOWN_TAGS, check_for_near_miss_tags, iter_comment_tokens

_SPECS_WEB = tuple(spec for spec in KNOWN_TAGS if spec.name == "web")
_SPECS_WEB_GROUP = tuple(spec for spec in KNOWN_TAGS if spec.name == "web-group")

# "#+" so a "## @web ..." section-style comment is accepted, matching every other tag family.
_WEB_RE = re.compile(r"#+\s*@web\s+(?P<field>[A-Za-z_]\w*)(?P<rest>.*)$")
_WEB_GROUP_RE = re.compile(r"#+\s*@web-group(?P<rest>.*)$")

# A key is a plain identifier, or the "special:<value>" shape (repeatable, one per enum/sentinel
# option) - the value is either a double-quoted string or a bare, space-free token. Escaping a
# literal '"' inside a quoted value is deliberately unsupported (see module docstring).
_KV_RE = re.compile(r'(?P<key>special:[^\s="]+|[A-Za-z][A-Za-z0-9]*)=(?:"(?P<qval>[^"]*)"|(?P<bval>[^\s"]+))')

_FIELD_KNOWN_KEYS = frozenset({
    "section", "submitGroup", "label", "unit", "description", "kind",
    "onLabel", "offLabel", "mask", "dispatch", "defaultValue",
})
_GROUP_KNOWN_KEYS = frozenset({"section", "submitGroup", "label", "submit", "submitLabel"})
_VALID_KINDS = frozenset({"readonly", "number", "string", "enum", "toggle"})
_BOOL_VALUES = {"true": True, "false": False}
SELF_GROUP = "self"


class _WebGrammarError(Exception):
    """Internal: a malformed key=value payload. Always caught and re-raised as a BuildError with
    the tag's own file/line/field context, never allowed to escape this module."""


@dataclass(frozen=True)
class WebFieldTag:
    field_name: str
    section: str
    submit_group: str
    label: str
    raw: str
    unit: "str | None" = None
    description: "str | None" = None
    kind: "str | None" = None
    on_label: "str | None" = None
    off_label: "str | None" = None
    mask: bool = False
    dispatch: bool = False
    default_value: "bool | int | float | str | None" = None
    special: "tuple[tuple[str, str], ...]" = ()


@dataclass(frozen=True)
class WebGroupTag:
    section: str
    submit_group: str
    label: str
    raw: str
    submit: bool = False
    submit_label: "str | None" = None


def _parse_kv_pairs(rest: str) -> "dict[str, str]":
    pairs: dict[str, str] = {}
    pos = 0
    n = len(rest)
    while pos < n:
        while pos < n and rest[pos].isspace():
            pos += 1
        if pos >= n:
            break
        m = _KV_RE.match(rest, pos)
        if m is None:
            raise _WebGrammarError(f"unparseable content starting at {rest[pos:]!r}")
        key = m.group("key")
        if key in pairs:
            raise _WebGrammarError(f"duplicate key {key!r}")
        pairs[key] = m.group("qval") if m.group("qval") is not None else m.group("bval")
        pos = m.end()
    return pairs


def _coerce_bool(raw: str, *, device: str, path: Path, lineno: int, instance_label: str, key: str) -> bool:
    if raw not in _BOOL_VALUES:
        raise BuildError(device, f"{path}:{lineno}: @web {key}= must be true or false, got {raw!r}", instance=instance_label)
    return _BOOL_VALUES[raw]


def _coerce_default_value(raw: str) -> "bool | int | float | str":
    if raw in _BOOL_VALUES:
        return _BOOL_VALUES[raw]
    try:
        return int(raw)
    except ValueError:
        pass
    try:
        return float(raw)
    except ValueError:
        pass
    return raw


def _split_special(pairs: "dict[str, str]") -> "tuple[dict[str, str], tuple[tuple[str, str], ...]]":
    plain: dict[str, str] = {}
    special: list[tuple[str, str]] = []
    for key, value in pairs.items():
        if key.startswith("special:"):
            special.append((key[len("special:"):], value))
        else:
            plain[key] = value
    return plain, tuple(special)


def _check_known_and_required(
    plain: "dict[str, str]", known_keys: "frozenset[str]", required: "frozenset[str]",
    *, device: str, path: Path, lineno: int, instance_label: str, field: "str | None", raw: str, tag_name: str,
) -> None:
    unknown = set(plain) - known_keys
    if unknown:
        raise BuildError(device, f"{path}:{lineno}: @{tag_name} tag has unknown key(s) {sorted(unknown)}: {raw!r}", instance=instance_label, field=field)
    missing = required - set(plain)
    if missing:
        raise BuildError(device, f"{path}:{lineno}: @{tag_name} tag is missing required key(s) {sorted(missing)}: {raw!r}", instance=instance_label, field=field)


def parse_web_tags(path: Path, device: str, instance_label: str) -> "tuple[WebFieldTag, ...]":
    tokens = iter_comment_tokens(path, device, instance_label)
    tags: list[WebFieldTag] = []
    exact_matches: set[tuple[int, int]] = set()
    for tok in tokens:
        text = tok.text.strip()
        m = _WEB_RE.fullmatch(text)
        if m is None:
            continue
        exact_matches.add((tok.lineno, tok.col))
        field_name = m.group("field")
        if tok.inside_block:
            raise BuildError(device, f"{path}:{tok.lineno}: @web tag for {field_name!r} must be at module level: {text!r}", instance=instance_label, field=field_name)
        try:
            pairs = _parse_kv_pairs(m.group("rest"))
        except _WebGrammarError as e:
            raise BuildError(device, f"{path}:{tok.lineno}: malformed @web tag for {field_name!r} ({e}): {text!r}", instance=instance_label, field=field_name) from None
        plain, special = _split_special(pairs)
        _check_known_and_required(
            plain, _FIELD_KNOWN_KEYS, frozenset({"section", "submitGroup", "label"}),
            device=device, path=path, lineno=tok.lineno, instance_label=instance_label, field=field_name, raw=text, tag_name="web",
        )
        kind = plain.get("kind")
        if kind is not None and kind not in _VALID_KINDS:
            raise BuildError(device, f"{path}:{tok.lineno}: @web tag for {field_name!r} has unknown kind {kind!r}: {text!r}", instance=instance_label, field=field_name)
        tags.append(WebFieldTag(
            field_name=field_name,
            section=plain["section"],
            submit_group=plain["submitGroup"],
            label=plain["label"],
            raw=text,
            unit=plain.get("unit"),
            description=plain.get("description"),
            kind=kind,
            on_label=plain.get("onLabel"),
            off_label=plain.get("offLabel"),
            mask=_coerce_bool(plain["mask"], device=device, path=path, lineno=tok.lineno, instance_label=instance_label, key="mask") if "mask" in plain else False,
            dispatch=_coerce_bool(plain["dispatch"], device=device, path=path, lineno=tok.lineno, instance_label=instance_label, key="dispatch") if "dispatch" in plain else False,
            default_value=_coerce_default_value(plain["defaultValue"]) if "defaultValue" in plain else None,
            special=special,
        ))
    check_for_near_miss_tags(tokens, path, device, instance_label, exact_matches, _SPECS_WEB)
    _check_no_duplicate_fields(tags, path, device, instance_label)
    return tuple(tags)


def parse_web_group_tags(path: Path, device: str, instance_label: str) -> "tuple[WebGroupTag, ...]":
    tokens = iter_comment_tokens(path, device, instance_label)
    tags: list[WebGroupTag] = []
    exact_matches: set[tuple[int, int]] = set()
    for tok in tokens:
        text = tok.text.strip()
        m = _WEB_GROUP_RE.fullmatch(text)
        if m is None:
            continue
        exact_matches.add((tok.lineno, tok.col))
        if tok.inside_block:
            raise BuildError(device, f"{path}:{tok.lineno}: @web-group tag must be at module level: {text!r}", instance=instance_label)
        try:
            pairs = _parse_kv_pairs(m.group("rest"))
        except _WebGrammarError as e:
            raise BuildError(device, f"{path}:{tok.lineno}: malformed @web-group tag ({e}): {text!r}", instance=instance_label) from None
        _check_known_and_required(
            pairs, _GROUP_KNOWN_KEYS, frozenset({"section", "submitGroup", "label"}),
            device=device, path=path, lineno=tok.lineno, instance_label=instance_label, field=None, raw=text, tag_name="web-group",
        )
        tags.append(WebGroupTag(
            section=pairs["section"],
            submit_group=pairs["submitGroup"],
            label=pairs["label"],
            raw=text,
            submit=_coerce_bool(pairs["submit"], device=device, path=path, lineno=tok.lineno, instance_label=instance_label, key="submit") if "submit" in pairs else False,
            submit_label=pairs.get("submitLabel"),
        ))
    check_for_near_miss_tags(tokens, path, device, instance_label, exact_matches, _SPECS_WEB_GROUP)
    _check_no_duplicate_groups(tags, path, device, instance_label)
    return tuple(tags)


def _check_no_duplicate_fields(tags: "tuple[WebFieldTag, ...] | list[WebFieldTag]", path: Path, device: str, instance_label: str) -> None:
    seen: dict[tuple[str, str, str], WebFieldTag] = {}
    for tag in tags:
        key = (tag.section, tag.submit_group, tag.field_name)
        if key in seen:
            raise BuildError(device, f"{path}: duplicate @web tag for field {tag.field_name!r} in section {tag.section!r}/group {tag.submit_group!r}", instance=instance_label, field=tag.field_name)
        seen[key] = tag


def _check_no_duplicate_groups(tags: "tuple[WebGroupTag, ...] | list[WebGroupTag]", path: Path, device: str, instance_label: str) -> None:
    seen: dict[tuple[str, str], WebGroupTag] = {}
    for tag in tags:
        key = (tag.section, tag.submit_group)
        if key in seen:
            raise BuildError(device, f"{path}: duplicate @web-group tag for section {tag.section!r}/group {tag.submit_group!r}", instance=instance_label)
        seen[key] = tag
