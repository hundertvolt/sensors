"""scripts/_page_load_connections.mjs's classifyConnections(), run under Node: the cross-browser smoke counts a page
load's own connections (the document and its assets, SPECIFICATION.md H.7) apart from the data requests the page then
makes, and a connection that carried no request (a browser's speculative spare socket) is counted on its own."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
_MODULE_URL = (_REPO_ROOT / "scripts" / "_page_load_connections.mjs").as_uri()


def _classify(first_requests: "list[str | None]") -> "dict[str, int]":
    node = shutil.which("node")
    assert node is not None, "node is not on PATH - the cross-browser smoke this pins cannot run without it either"
    script = f"import {{ classifyConnections }} from {json.dumps(_MODULE_URL)};\nconsole.log(JSON.stringify(classifyConnections({json.dumps(first_requests)})));"
    done = subprocess.run([node, "--input-type=module", "-e", script], cwd=_REPO_ROOT, capture_output=True, text=True, check=False, timeout=120)
    assert done.returncode == 0, done.stderr
    result: dict[str, int] = json.loads(done.stdout)
    return result


@pytest.mark.parametrize(
    ("first_requests", "expected"),
    [
        (["GET / HTTP/1.1", "GET /js/app.js HTTP/1.1", "GET /measurements HTTP/1.1"], {"page": 2, "speculative": 0, "data": 1}),
        (["GET / HTTP/1.1", "GET /js/app.js HTTP/1.1"], {"page": 2, "speculative": 0, "data": 0}),
        (["GET / HTTP/1.1", "GET /favicon.ico HTTP/1.1", "GET /js/app.js HTTP/1.1"], {"page": 3, "speculative": 0, "data": 0}),
        (["GET / HTTP/1.1", "GET /js/app.js HTTP/1.1", None], {"page": 2, "speculative": 1, "data": 0}),
        (["GET /?x=1 HTTP/1.1", "GET /status HTTP/1.1", "PUT /sensors HTTP/1.1"], {"page": 1, "speculative": 0, "data": 2}),
        ([], {"page": 0, "speculative": 0, "data": 0}),
    ],
)
def test_a_page_loads_own_connections_are_counted_apart_from_its_data_requests(first_requests: "list[str | None]", expected: "dict[str, int]") -> None:
    assert _classify(first_requests) == expected
