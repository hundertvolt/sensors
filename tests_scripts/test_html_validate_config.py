"""The repo's .htmlvalidate.json, run by the installed html-validate on pages of its own: an attribute the element
metadata does not know (a misspelling) fails the lint, while the site's data-* and aria-* attributes still pass -
the page html-validate lints in CI is every device's built page (SPECIFICATION.md H.8)."""

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

_CONFIG = ".htmlvalidate.json"
_CLI = Path("node_modules") / "html-validate" / "bin" / "html-validate.mjs"
_REQUIRED = "HTML_VALIDATE_REQUIRED"
_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Fixture page</title>
</head>
<body>
    <main>
        <p class="note" data-field-key="Interval" aria-live="polite"{attribute}>A paragraph.</p>
    </main>
</body>
</html>
"""
# The control page first: clean, so a finding on a planted page is that page's attribute.
_PLANTED = {"frobnicate.html": "frobnicate-attr", "calss.html": "calss"}


@pytest.fixture(scope="module")
def lint(repo_root: Path, tmp_path_factory: pytest.TempPathFactory) -> "tuple[int, dict[str, list[str]]]":
    # One html-validate run over every page: its exit code, and each page's findings as "rule: message".
    node = shutil.which("node")
    assert node is not None, "node is not on PATH - npm run lint:html cannot run without it either"
    pages = tmp_path_factory.mktemp("pages")
    (pages / "control.html").write_text(_PAGE.format(attribute=""), encoding="utf-8")
    for name, attribute in _PLANTED.items():
        (pages / name).write_text(_PAGE.format(attribute=f' {attribute}="1"'), encoding="utf-8")
    cli = repo_root / _CLI
    if not cli.is_file():
        # The unit-test jobs install no node_modules: CI's web-lint-and-typecheck job installs them and sets the flag.
        assert not os.environ.get(_REQUIRED), f"{_CLI} is not installed - npm ci installs it (npm run lint:html needs it too)"
        pytest.skip(f"html-validate is not installed ({_CLI}) - npm ci installs it; CI's web-lint-and-typecheck job runs this file with {_REQUIRED}=1")
    command = [node, str(cli), "--config", str(repo_root / _CONFIG), "--formatter", "json", *sorted(str(p) for p in pages.iterdir())]
    done = subprocess.run(command, cwd=repo_root, capture_output=True, text=True, check=False, timeout=120)
    # A clean run prints "[]": empty output is a run that never reported, never a pass.
    assert done.returncode in {0, 1} and done.stdout.strip(), done.stderr
    report = json.loads(done.stdout)
    return done.returncode, {Path(entry["filePath"]).name: [f"{m['ruleId']}: {m['message']}" for m in entry["messages"]] for entry in report}


def test_the_fixture_page_passes_with_the_sites_own_attribute_kinds(lint: "tuple[int, dict[str, list[str]]]") -> None:
    assert lint[1].get("control.html", []) == []


@pytest.mark.parametrize(("page", "attribute"), _PLANTED.items())
def test_an_attribute_the_element_does_not_know_fails_the_lint(lint: "tuple[int, dict[str, list[str]]]", page: str, attribute: str) -> None:
    code, findings = lint
    assert any(attribute in finding for finding in findings.get(page, [])), f"html-validate passed <p {attribute}>, an attribute no element metadata defines"
    assert code != 0
