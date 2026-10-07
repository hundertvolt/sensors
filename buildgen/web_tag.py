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
    "onLabel", "offLabel", "mask", "dispatch", "defaultValue", "path", "decimals",
    "alwaysExecuted", "format", "codes", "bytes", "shape",
})
_GROUP_KNOWN_KEYS = frozenset({"section", "submitGroup", "label", "submit", "submitLabel"})
_VALID_KINDS = frozenset({"readonly", "number", "string", "enum", "toggle"})
# The values each enumerated key takes; format and codes describe a readonly value, bytes and shape a
# string one (a string's kind is inferred from its schema, so the generator checks that half).
_FORMATS = frozenset({"epoch", "gmtimestruct"})
_SHAPES = frozenset({"hostLabel", "countryCode", "hostName"})
_READONLY_ONLY_KEYS = ("format", "codes")
_STRING_ONLY_KEYS = ("bytes", "shape")
# js/definitions.js's own validateFieldHints() ceiling (Number#toFixed()'s real RangeError
# boundary) - pinned by `tests_scripts/test_definitions_js_mirrors.py`.
_MAX_DECIMALS = 100
_BOOL_VALUES = {"true": True, "false": False}
SELF_GROUP = "self"


class _WebGrammarError(Exception):
    # Internal: a malformed key=value payload. Always caught and re-raised as a BuildError with
    # the tag's own file/line/field context, never allowed to escape this module.
    pass


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
    path: "tuple[str, ...] | None" = None
    decimals: "int | None" = None
    always_executed: bool = False
    format: "str | None" = None
    codes: "str | None" = None  # a status table's name in buildgen/error_catalog.json, inlined by the generator
    byte_length: bool = False
    shape: "str | None" = None


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


def _coerce_path(raw: str, *, device: str, path: Path, lineno: int, instance_label: str, field_name: str) -> "tuple[str, ...]":
    # Dot-joined rather than a JSON array (Part H.5.1): _KV_RE captures one scalar per key=value
    # pair, so an array literal has no home in this grammar. Splitting a plain string at
    # consumption time fits the existing shape instead of growing a second value grammar.
    parts = tuple(raw.split("."))
    if not parts or any(not p for p in parts):
        raise BuildError(
            device,
            f'{path}:{lineno}: @web tag for {field_name!r} has malformed path={raw!r} - expected dot-joined non-empty segments, e.g. path="RGB.R"',
            instance=instance_label, field=field_name,
        )
    return parts


def _coerce_decimals(raw: str, *, device: str, path: Path, lineno: int, instance_label: str, field_name: str) -> int:
    try:
        value = int(raw)
    except ValueError:
        raise BuildError(device, f"{path}:{lineno}: @web tag for {field_name!r} has non-integer decimals={raw!r}", instance=instance_label, field=field_name) from None
    if not (0 <= value <= _MAX_DECIMALS):
        raise BuildError(device, f"{path}:{lineno}: @web tag for {field_name!r} has decimals={value} outside 0..{_MAX_DECIMALS}", instance=instance_label, field=field_name)
    return value


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


@dataclass(frozen=True)
class TagSite:
    # Where one tag sits, built once per tag: what every error raised about it names.
    device: str
    path: Path
    lineno: int
    instance_label: str
    field: "str | None"
    raw: str
    tag_name: str


def _check_value_keys(plain: "dict[str, str]", kind: "str | None", site: TagSite) -> None:
    # Each key's allowed kind and value set; a bool key's value is checked where it is coerced.
    where = f"{site.path}:{site.lineno}: @web tag for {site.field!r}"
    for key in _READONLY_ONLY_KEYS:
        if key in plain and kind != "readonly":
            raise BuildError(site.device, f"{where} has {key}= but is not kind=readonly: {site.raw!r}", instance=site.instance_label, field=site.field)
    for key in _STRING_ONLY_KEYS:
        if key in plain and kind not in (None, "string"):
            raise BuildError(site.device, f"{where} has {key}= but is not a string field: {site.raw!r}", instance=site.instance_label, field=site.field)
    if "format" in plain and plain["format"] not in _FORMATS:
        raise BuildError(site.device, f"{where} has format={plain['format']!r}, expected one of {sorted(_FORMATS)}: {site.raw!r}", instance=site.instance_label, field=site.field)
    if "shape" in plain and plain["shape"] not in _SHAPES:
        raise BuildError(site.device, f"{where} has shape={plain['shape']!r}, expected one of {sorted(_SHAPES)}: {site.raw!r}", instance=site.instance_label, field=site.field)
    if plain.get("alwaysExecuted") == "true" and plain.get("dispatch") == "true":
        # A dispatch field persists nothing; an always-executed one writes the chip's own store.
        raise BuildError(site.device, f"{where} has both alwaysExecuted=true and dispatch=true, which exclude each other: {site.raw!r}", instance=site.instance_label, field=site.field)


def _check_known_and_required(plain: "dict[str, str]", known_keys: "frozenset[str]", required: "frozenset[str]", site: TagSite) -> None:
    unknown = set(plain) - known_keys
    if unknown:
        raise BuildError(site.device, f"{site.path}:{site.lineno}: @{site.tag_name} tag has unknown key(s) {sorted(unknown)}: {site.raw!r}", instance=site.instance_label, field=site.field)
    missing = required - set(plain)
    if missing:
        raise BuildError(site.device, f"{site.path}:{site.lineno}: @{site.tag_name} tag is missing required key(s) {sorted(missing)}: {site.raw!r}", instance=site.instance_label, field=site.field)


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
        site = TagSite(device, path, tok.lineno, instance_label, field_name, text, "web")
        _check_known_and_required(plain, _FIELD_KNOWN_KEYS, frozenset({"section", "submitGroup", "label"}), site)
        kind = plain.get("kind")
        if kind is not None and kind not in _VALID_KINDS:
            raise BuildError(device, f"{path}:{tok.lineno}: @web tag for {field_name!r} has unknown kind {kind!r}: {text!r}", instance=instance_label, field=field_name)
        if "path" in plain and kind != "readonly":
            # Mirrors js/definitions.js's own validateFieldHints() rule: a PUT body is always flat,
            # so a path on a writable field would render one value and submit a different one.
            raise BuildError(device, f"{path}:{tok.lineno}: @web tag for {field_name!r} has path= but is not kind=readonly: {text!r}", instance=instance_label, field=field_name)
        _check_value_keys(plain, kind, site)
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
            path=_coerce_path(plain["path"], device=device, path=path, lineno=tok.lineno, instance_label=instance_label, field_name=field_name) if "path" in plain else None,
            decimals=_coerce_decimals(plain["decimals"], device=device, path=path, lineno=tok.lineno, instance_label=instance_label, field_name=field_name) if "decimals" in plain else None,
            always_executed=_coerce_bool(plain["alwaysExecuted"], device=device, path=path, lineno=tok.lineno, instance_label=instance_label, key="alwaysExecuted") if "alwaysExecuted" in plain else False,
            format=plain.get("format"),
            codes=plain.get("codes"),
            byte_length=_coerce_bool(plain["bytes"], device=device, path=path, lineno=tok.lineno, instance_label=instance_label, key="bytes") if "bytes" in plain else False,
            shape=plain.get("shape"),
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
        site = TagSite(device, path, tok.lineno, instance_label, None, text, "web-group")
        _check_known_and_required(pairs, _GROUP_KNOWN_KEYS, frozenset({"section", "submitGroup", "label"}), site)
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
