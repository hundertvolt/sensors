"""scripts/_cross_browser_probe.mjs's pickProbe(), run under Node without a browser: every device's
generated definitions yield the first in-range integer field of a submitting group, the field the
cross-browser smoke edits (SPECIFICATION.md H.7), and a device with none fails naming itself."""

import json
import math
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest
from _devices import DEVICE_NAMES, device_toml

from buildgen.definitions import definitions_for_toml

_REPO_ROOT = Path(__file__).resolve().parent.parent
_MODULE_URL = (_REPO_ROOT / "scripts" / "_cross_browser_probe.mjs").as_uri()
# The span pickProbe() needs, so a probe value never repeats within one device's run.
_MIN_SPAN = 64


def _pick(definitions_path: Path) -> "subprocess.CompletedProcess[str]":
    node = shutil.which("node")
    assert node is not None, "node is not on PATH - the cross-browser smoke this pins cannot run without it either"
    script = (
        f"import {{ readFileSync }} from 'node:fs';\nimport {{ pickProbe }} from {json.dumps(_MODULE_URL)};\n"
        f"console.log(JSON.stringify(pickProbe(JSON.parse(readFileSync({json.dumps(str(definitions_path))}, 'utf8')))));"
    )
    return subprocess.run([node, "--input-type=module", "-e", script], cwd=_REPO_ROOT, capture_output=True, text=True, check=False, timeout=120)


def _expected_probe(definitions: "dict[str, Any]") -> "dict[str, Any] | None":
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
    path.write_text(json.dumps(definitions))
    done = _pick(path)
    assert done.returncode == 0, done.stderr
    probe = json.loads(done.stdout.strip().splitlines()[-1])
    expected = _expected_probe(definitions)
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
    path.write_text(json.dumps(definitions))
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
    text = (_REPO_ROOT / "scripts" / "cross_browser_smoke.mjs").read_text()

    def body(name: str) -> str:
        return text.split(f"async function {name}(", 1)[1].split("\n}\n", 1)[0]

    assert "webDriverFailure(res.status, body)" in body("wdCommand")
    for name in ("wdNavigate", "wdSetWindowRect", "wdExecute"):
        assert "wdCommand(" in body(name) and "fetch(" not in body(name), f"{name}() does not check the WebDriver reply"
