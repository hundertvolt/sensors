"""No file outside devices/ names a device variant: the device set comes from data (devices/*.toml), a
runner argument or a TOML property, never a literal. Files still carrying one sit in _NOT_YET_CLEANED,
which only shrinks; `python tests_scripts/test_no_variant_literals.py` lists the current findings."""

import re
import sys

import pytest
import tomllib
from _devices import DEVICE_NAMES
from _repo_scan import REPO_ROOT, is_shared_excluded, read_text, repo_files

# The check's own patterns and homonym list spell the forms it looks for.
_SELF = "tests_scripts/test_no_variant_literals.py"
# Data read from the devices, not code that names one.
_FIXTURE_PREFIXES = ("devices/", "tests_scripts/golden/", "tests_scripts/fixtures/api_reference/")
# A device name that is also an ordinary word is matched only in variant-shaped forms.
_ENGLISH_HOMONYMS = frozenset({"dev"})
_TC_VERBS = ("replace", "del", "add", "change")

# The content change that removes each kind of literal, named by what it does.
_REASON_UNIT_TEST = "the unit test takes its device from the generated build, selecting by TOML property"
_REASON_ALLOWLIST = "shrinks as the quoted sentences naming a device are rewritten"
_REASON_FIXTURE_COMMENT = "the fixture's comments name the property each block copies, not a device TOML"

# File -> the content change that removes its literal. Only shrinks: an entry whose file is clean fails.
_NOT_YET_CLEANED: "dict[str, str]" = {
    "tests/test_digital_twin_bus_hazard_concurrency.py": _REASON_UNIT_TEST,
    "tests/test_digital_twin_machine.py": _REASON_UNIT_TEST,
    "tests/test_digital_twin_run_generic_integration.py": _REASON_UNIT_TEST,
    "tests_scripts/_citation_allowlist.txt": _REASON_ALLOWLIST,
    "tests_scripts/_decision_vocab_allowlist.txt": _REASON_ALLOWLIST,
    "tests_scripts/buildgen_fixtures/novel_combo.toml": _REASON_FIXTURE_COMMENT,
}


def _homonyms(names: "list[str]", pyproject_text: str) -> "frozenset[str]":
    groups = tomllib.loads(pyproject_text).get("dependency-groups", {})
    return frozenset(n for n in names if n in groups or n in _ENGLISH_HOMONYMS)


def _homonym_patterns(name: str) -> "list[re.Pattern[str]]":
    n = re.escape(name)
    return [
        re.compile(rf"sensortask_{n}\b", re.IGNORECASE),
        re.compile(rf"{n}\.(?:toml|json|uf2)\b", re.IGNORECASE),
        re.compile(rf"firmware-{n}\b", re.IGNORECASE),
        re.compile(rf"SensorStation{n}\b", re.IGNORECASE),
        re.compile(rf"device[= ]{n}\b", re.IGNORECASE),
    ]


def _quoted_is_exempt(line: str, start: int) -> bool:
    # A quoted homonym that is a path join's right operand or a device argv element of `iw`/`tc`.
    before = line[:start].rstrip()
    if before.endswith("/"):
        return True
    previous = re.search(r"""["'](\w+)["']\s*,$""", before)
    return previous is not None and previous.group(1) in ("iw", *_TC_VERBS)


def _homonym_hits(name: str, line: str, others: "list[str]") -> "list[str]":
    hits = [m.group(0) for p in _homonym_patterns(name) for m in p.finditer(line)]
    quoted = re.finditer(rf"""(["']){re.escape(name)}\1""", line, re.IGNORECASE)
    hits += [m.group(0) for m in quoted if not _quoted_is_exempt(line, m.start())]
    for m in re.finditer(r"\[[^\[\]]*\]", line):
        listed = m.group(0)
        if re.search(rf"\b{re.escape(name)}\b", listed, re.IGNORECASE) and any(re.search(rf"\b{re.escape(o)}\b", listed, re.IGNORECASE) for o in others):
            hits.append(listed)
    return hits


def line_hits(line: str, names: "list[str]", homonyms: "frozenset[str]") -> "list[str]":
    # Every variant literal on one line: a plain name anywhere, a homonym only in variant-shaped forms.
    hits: list[str] = []
    for name in names:
        if name in homonyms:
            hits += _homonym_hits(name, line, [o for o in names if o != name])
        else:
            hits += [m.group(0) for m in re.finditer(re.escape(name), line, re.IGNORECASE)]
    return hits


def _in_scope(path: str) -> bool:
    return not (is_shared_excluded(path) or path == _SELF or path.endswith(".md") or path.startswith(_FIXTURE_PREFIXES))


def file_findings(text: str, names: "list[str]", homonyms: "frozenset[str]") -> "list[tuple[int, str]]":
    return [(number, hit) for number, line in enumerate(text.splitlines(), 1) for hit in line_hits(line, names, homonyms)]


def collect_findings() -> "dict[str, list[tuple[int, str]]]":
    homonyms = _homonyms(DEVICE_NAMES, (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    found: dict[str, list[tuple[int, str]]] = {}
    for path in repo_files():
        if _in_scope(path) and (text := read_text(path)) is not None:
            hits = file_findings(text, DEVICE_NAMES, homonyms)
            if hits:
                found[path] = hits
    return found


def test_no_file_outside_the_device_tomls_names_a_variant() -> None:
    found = collect_findings()
    new = {path: hits[:3] for path, hits in found.items() if path not in _NOT_YET_CLEANED}
    assert not new, "variant literals outside devices/ - take the device from data, an argument or a TOML property:\n" + "\n".join(f"  {p}: {h}" for p, h in sorted(new.items()))


def test_every_not_yet_cleaned_entry_still_carries_a_literal() -> None:
    found = collect_findings()
    stale = sorted(path for path in _NOT_YET_CLEANED if path not in found)
    assert not stale, f"these files are clean now - remove their _NOT_YET_CLEANED entries: {stale}"


def test_every_not_yet_cleaned_reason_names_a_change() -> None:
    blank = sorted(path for path, reason in _NOT_YET_CLEANED.items() if not reason.strip())
    assert not blank, f"each entry names the change that removes its literal: {blank}"


def _named(text: str) -> str:
    # A self-test line with `{V}` as a plain device name and `{H}` as a homonym, both from the data.
    plain = next(n for n in DEVICE_NAMES if n not in _homonyms(DEVICE_NAMES, ""))
    homonym = next(iter(_homonyms(DEVICE_NAMES, "") or _ENGLISH_HOMONYMS))
    return text.replace("{V}", plain).replace("{Vc}", plain.capitalize()).replace("{H}", homonym).replace("{Hc}", homonym.capitalize())


@pytest.mark.parametrize(
    "line",
    [
        "# the {V} board",  # a comment
        'device = "{V}"',  # a string
        "import sensortask_{V}",  # an identifier
        'name = "SensorStation{Vc}"',
        "const {V}Data = 1;",
        'title = "SensorStation{Hc}"',
        'args = ["--device", "{H}"]',
        "path = 'devices/{H}.toml'",
        "matrix: [{V}, {H}]",
    ],
)
def test_a_variant_literal_is_caught(line: str) -> None:
    names = [*DEVICE_NAMES, *_ENGLISH_HOMONYMS]
    assert line_hits(_named(line), names, _homonyms(names, "")), _named(line)


@pytest.mark.parametrize(
    "line",
    [
        'port = "/{H}/ttyACM0"',
        'apt = "libffi-{H}"',
        "# {H}-tooling only",
        'subprocess.run(["iw", "{H}", iface])',
        'subprocess.run(["tc", "qdisc", "del", "{H}", iface])',
        'root = tmp_path / "{H}"',
    ],
)
def test_a_homonym_in_ordinary_use_passes(line: str) -> None:
    names = [*DEVICE_NAMES, *_ENGLISH_HOMONYMS]
    assert not line_hits(_named(line), names, _homonyms(names, "")), _named(line)


def test_a_dependency_group_name_counts_as_a_homonym() -> None:
    assert _homonyms(["zz", "tools"], '[dependency-groups]\ntools = ["x"]\n') == frozenset({"tools"})


if __name__ == "__main__":
    for found_path, found_hits in sorted(collect_findings().items()):
        marker = " " if found_path in _NOT_YET_CLEANED else "+"
        print(f"{marker} {found_path}: {found_hits[:3]}")
    sys.exit(0)
