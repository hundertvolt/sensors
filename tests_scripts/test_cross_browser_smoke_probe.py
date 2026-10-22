"""scripts/_cross_browser_probe.mjs run under Node without a browser: pickProbe() yields every device's field the
cross-browser smoke edits (SPECIFICATION.md H.7) or fails naming the device, and engineVerdict() fails a missing
engine under --require-all-engines and skips it, counted, without; the smoke reads that flag and nothing else."""

import json
import math
import shutil
import subprocess
from pathlib import Path
from typing import TypedDict

import pytest
from _devices import DEVICE_NAMES, device_toml

from buildgen.definitions import definitions_for_toml

_REPO_ROOT = Path(__file__).resolve().parent.parent
_MODULE_URL = (_REPO_ROOT / "scripts" / "_cross_browser_probe.mjs").as_uri()
# The span pickProbe() needs, so a probe value never repeats within one device's run.
_MIN_SPAN = 64


class _Field(TypedDict, total=False):
    # The definitions keys pickProbe() reads; JSON gives no static type, so these name the shape the rule walks.
    key: str
    kind: str
    min: object
    max: object
    float: bool


class _Group(TypedDict, total=False):
    key: str
    submit: bool
    fields: list[_Field]


class _Section(TypedDict):
    key: str
    groups: list[_Group]


class _Definitions(TypedDict):
    sections: list[_Section]


class _Outcome(TypedDict, total=False):
    # engineVerdict()'s answer, an entry of its results or skips.
    label: str
    ok: bool
    detail: str


class _Verdict(TypedDict):
    results: list[_Outcome]
    skips: list[_Outcome]
    passed: int
    ran: int
    skipped: int


def _pick(definitions_path: Path) -> "subprocess.CompletedProcess[str]":
    node = shutil.which("node")
    assert node is not None, "node is not on PATH - the cross-browser smoke this pins cannot run without it either"
    script = (
        f"import {{ readFileSync }} from 'node:fs';\nimport {{ pickProbe }} from {json.dumps(_MODULE_URL)};\n"
        f"console.log(JSON.stringify(pickProbe(JSON.parse(readFileSync({json.dumps(str(definitions_path))}, 'utf8')))));"
    )
    return subprocess.run([node, "--input-type=module", "-e", script], cwd=_REPO_ROOT, capture_output=True, text=True, check=False, timeout=120)


def _expected_probe(definitions: _Definitions) -> "dict[str, object] | None":
    # The rule restated independently: the first number field, not float, with finite bounds at least
    # _MIN_SPAN apart, in a submitting group, in definitions order.
    for section in definitions["sections"]:
        for group in section["groups"]:
            if group.get("submit") is not True:
                continue
            for field in group.get("fields", []):
                low, high = field.get("min"), field.get("max")
                if field.get("kind") != "number" or field.get("float") is True or not isinstance(low, int | float) or not isinstance(high, int | float):
                    continue
                if math.isfinite(low) and math.isfinite(high) and high - low >= _MIN_SPAN:
                    return {"sectionKey": section["key"], "groupKey": group["key"], "fieldKey": field["key"], "min": low, "max": high}
    return None


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_every_device_yields_an_in_range_integer_probe(tmp_path: Path, device: str) -> None:
    definitions = definitions_for_toml(device_toml(device), _REPO_ROOT / "src")
    path = tmp_path / f"{device}.json"
    path.write_text(json.dumps(definitions), encoding="utf-8")
    done = _pick(path)
    assert done.returncode == 0, done.stderr
    probe = json.loads(done.stdout.strip().splitlines()[-1])
    expected = _expected_probe(json.loads(path.read_text(encoding="utf-8")))
    assert expected is not None, f"{device}'s definitions carry no editable integer field the smoke could probe"
    assert probe == expected


def test_a_device_with_no_candidate_fails_naming_itself(tmp_path: Path) -> None:
    definitions = {
        "device": {"id": "fixture-device", "displayName": "Fixture Device"},
        "sections": [{"key": "sensors", "groups": [{"key": "G", "submit": True, "fields": [
            {"key": "Ratio", "kind": "number", "float": True, "min": 0, "max": 1000},
            {"key": "Narrow", "kind": "number", "min": 0, "max": 10},
        ]}]}],
    }
    path = tmp_path / "fixture.json"
    path.write_text(json.dumps(definitions), encoding="utf-8")
    done = _pick(path)
    assert done.returncode != 0, f"pickProbe() returned {done.stdout!r} for definitions with no candidate"
    assert "fixture-device" in done.stderr


def _webdriver_failure(status: int, body: object) -> "str | None":
    node = shutil.which("node")
    assert node is not None, "node is not on PATH"
    script = (
        f"import {{ webDriverFailure }} from {json.dumps(_MODULE_URL)};\n"
        f"console.log(JSON.stringify(webDriverFailure({status}, {json.dumps(body)})));"
    )
    done = subprocess.run([node, "--input-type=module", "-e", script], cwd=_REPO_ROOT, capture_output=True, text=True, check=False, timeout=120)
    assert done.returncode == 0, done.stderr
    result: str | None = json.loads(done.stdout.strip().splitlines()[-1])
    return result


@pytest.mark.parametrize(("status", "body"), [(200, {"value": None}), (200, {"value": {"x": 1, "y": 0, "width": 1280, "height": 800}})])
def test_a_webdriver_success_is_no_failure(status: int, body: object) -> None:
    assert _webdriver_failure(status, body) is None


@pytest.mark.parametrize(("status", "body"), [
    (404, {"value": {"error": "no such window", "message": "gone"}}),
    (500, {"value": {"error": "unknown error", "message": "resize refused"}}),
    (200, {"value": {"error": "unsupported operation", "message": "x"}}),
    (500, {}),
])
def test_a_webdriver_error_status_or_error_value_is_a_failure_naming_it(status: int, body: object) -> None:
    failure = _webdriver_failure(status, body)
    assert failure is not None
    assert str(status) in failure
    if isinstance(body, dict) and isinstance(body.get("value"), dict):
        assert body["value"]["error"] in failure


def test_every_webdriver_command_in_the_smoke_checks_its_reply() -> None:
    # Navigation and window size were fire-and-forget: a failed resize went unnoticed (only the mobile width is asserted).
    text = (_REPO_ROOT / "scripts" / "cross_browser_smoke.mjs").read_text(encoding="utf-8")

    def body(name: str) -> str:
        return text.split(f"async function {name}(", 1)[1].split("\n}\n", 1)[0]

    assert "webDriverFailure(res.status, body)" in body("wdCommand")
    for name in ("wdNavigate", "wdSetWindowRect", "wdExecute"):
        assert "wdCommand(" in body(name) and "fetch(" not in body(name), f"{name}() does not check the WebDriver reply"


_WEBKIT_BIN = "/usr/bin/WebKitWebDriver"
_FIREFOX_BINS = ["/fixture/ff/bin/firefox", "/fixture/ff/bin/geckodriver"]
_PRESENT = [{"name": "WebKit", "missing": []}, {"name": "Chromium", "missing": []}]
_WEBKIT_MISSING = [{"name": "WebKit", "missing": [_WEBKIT_BIN]}, {"name": "Chromium", "missing": []}]
_CHROMIUM_PASSED = [{"label": "fixture-device Chromium (desktop)", "ok": True}, {"label": "fixture-device Chromium (mobile)", "ok": True}]
_ONE_FAILED = [*_CHROMIUM_PASSED, {"label": "fixture-device WebKit (desktop)", "ok": False, "detail": "x"}]
# Every engineVerdict() case as (available, results, requireAllEngines), all answered by one Node process.
_VERDICT_CASES = {
    "missing, required": (_WEBKIT_MISSING, _CHROMIUM_PASSED, True),
    "missing, not required": (_WEBKIT_MISSING, _CHROMIUM_PASSED, False),
    "two binaries missing": ([{"name": "Firefox", "missing": _FIREFOX_BINS}], [], True),
    "present, required": (_PRESENT, _ONE_FAILED, True),
    "present, not required": (_PRESENT, _ONE_FAILED, False),
}


@pytest.fixture(scope="module")
def verdicts() -> "dict[str, _Verdict]":
    node = shutil.which("node")
    assert node is not None, "node is not on PATH"
    cases = {name: [available, results, {"requireAllEngines": required}] for name, (available, results, required) in _VERDICT_CASES.items()}
    script = (
        f"import {{ engineVerdict }} from {json.dumps(_MODULE_URL)};\n"
        f"const cases = {json.dumps(cases)};\n"
        "console.log(JSON.stringify(Object.fromEntries(Object.entries(cases).map(([name, args]) => [name, engineVerdict(...args)]))));"
    )
    done = subprocess.run([node, "--input-type=module", "-e", script], cwd=_REPO_ROOT, capture_output=True, text=True, check=False, timeout=120)
    assert done.returncode == 0, done.stderr
    answered: dict[str, _Verdict] = json.loads(done.stdout.strip().splitlines()[-1])
    return answered


def test_with_the_flag_a_missing_engine_fails_naming_its_binary_and_the_installer(verdicts: "dict[str, _Verdict]") -> None:
    verdict = verdicts["missing, required"]
    failed = [result for result in verdict["results"] if not result["ok"]]
    assert [result["label"] for result in failed] == ["WebKit"], verdict
    assert _WEBKIT_BIN in failed[0]["detail"]
    assert "CI requires every engine" in failed[0]["detail"]
    assert "scripts/setup_cross_browser_toolchain.sh" in failed[0]["detail"]
    assert (verdict["passed"], verdict["ran"], verdict["skipped"], verdict["skips"]) == (2, 3, 0, [])


def test_without_the_flag_a_missing_engine_is_skipped_and_counted(verdicts: "dict[str, _Verdict]") -> None:
    verdict = verdicts["missing, not required"]
    assert verdict["results"] == _CHROMIUM_PASSED
    assert [skip["label"] for skip in verdict["skips"]] == ["WebKit"]
    assert _WEBKIT_BIN in verdict["skips"][0]["detail"]
    assert "scripts/setup_cross_browser_toolchain.sh" in verdict["skips"][0]["detail"]
    assert (verdict["passed"], verdict["ran"], verdict["skipped"]) == (2, 2, 1)


def test_an_engine_missing_two_binaries_names_both(verdicts: "dict[str, _Verdict]") -> None:
    verdict = verdicts["two binaries missing"]
    assert all(path in verdict["results"][0]["detail"] for path in _FIREFOX_BINS), verdict


@pytest.mark.parametrize("case", ["present, required", "present, not required"])
def test_with_every_engine_present_only_the_checks_decide(verdicts: "dict[str, _Verdict]", case: str) -> None:
    verdict = verdicts[case]
    assert verdict["results"] == _ONE_FAILED
    assert (verdict["passed"], verdict["ran"], verdict["skipped"], verdict["skips"]) == (2, 3, 0, [])


def test_the_smoke_takes_the_engine_flag_and_rejects_any_other_argument() -> None:
    # Only argument handling runs: a usage error exits before Playwright loads or a twin boots; its usage names the flag.
    node = shutil.which("node")
    assert node is not None, "node is not on PATH"
    done = subprocess.run([node, "scripts/cross_browser_smoke.mjs", "--require-all-engines", "--frobnicate"], cwd=_REPO_ROOT, capture_output=True, text=True, check=False, timeout=120)
    assert done.returncode == 2, done.stderr
    assert 'unknown argument "--frobnicate"' in done.stderr and 'unknown argument "--require-all-engines"' not in done.stderr
    assert "[--require-all-engines]" in done.stderr, "the usage block does not name --require-all-engines"
