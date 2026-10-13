"""scripts/_page_load_connections.mjs under Node: the cross-browser smoke counts a page load's own connections (the
document and its assets, SPECIFICATION.md H.7) apart from its data requests, and a connection still empty once the page's
first data request went out (a browser's spare socket) on its own; the counting proxy is driven over real sockets."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
_MODULE_URL = (_REPO_ROOT / "scripts" / "_page_load_connections.mjs").as_uri()

# A server behind the proxy that holds every connection open, and a client socket helper: open() resolves once the
# proxy has recorded the connection, send() writes one request line.
_HARNESS = """
import net from "node:net";
import { classifyConnections, settledPageLoadConnections, startCountingProxy } from %s;
const upstream = net.createServer((s) => s.on("error", () => {}));
await new Promise((r) => upstream.listen(0, "127.0.0.1", r));
const proxy = await startCountingProxy("127.0.0.1", 0, upstream.address().port);
const clients = [];
const pause = (ms) => new Promise((r) => setTimeout(r, ms));
async function open() {
    const before = proxy.firstRequests().length;
    const socket = net.connect(proxy.port(), "127.0.0.1");
    socket.on("error", () => {});
    clients.push(socket);
    while (proxy.firstRequests().length === before) await pause(5);
    return socket;
}
async function send(socket, path) {
    socket.write(`GET ${path} HTTP/1.1\\r\\nHost: x\\r\\n\\r\\n`);
    while (!proxy.firstRequests().some((l) => l !== null && l.startsWith(`GET ${path} `))) await pause(5);
}
let out;
%s
for (const c of clients) c.destroy();
await proxy.close();
upstream.close();
console.log(JSON.stringify(out));
"""


def _node(body: str) -> "dict[str, object]":
    node = shutil.which("node")
    assert node is not None, "node is not on PATH - the cross-browser smoke this pins cannot run without it either"
    script = _HARNESS % (json.dumps(_MODULE_URL), body)
    done = subprocess.run([node, "--input-type=module", "-e", script], cwd=_REPO_ROOT, capture_output=True, text=True, check=False, timeout=120)
    assert done.returncode == 0, done.stderr
    result: dict[str, object] = json.loads(done.stdout)
    return result


def _classify(first_requests: "list[str | None]") -> "dict[str, int]":
    result = _node(f"out = classifyConnections({json.dumps(first_requests)});")
    return {k: int(str(v)) for k, v in result.items()}


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


def test_the_socket_opened_for_the_first_data_request_counts_as_data_once_it_is_written() -> None:
    # The pattern a CI run failed on: a spare socket, the document, its script, then the socket the page opened for
    # its first data request, not yet written when the navigation finished.
    result = _node("""
const spare = await open(); await send(await open(), "/"); await send(await open(), "/js/app.js");
const pending = await open();
const atNavigationEnd = classifyConnections(proxy.firstRequests());
setTimeout(() => pending.write("GET /measurements HTTP/1.1\\r\\n\\r\\n"), 50);
const started = Date.now();
const settled = classifyConnections(await settledPageLoadConnections(proxy, 5000));
out = { atNavigationEnd, settled, waitedMs: Date.now() - started };
""")
    assert result["atNavigationEnd"] == {"page": 2, "speculative": 2, "data": 0}
    assert result["settled"] == {"page": 2, "speculative": 1, "data": 1}
    assert int(str(result["waitedMs"])) < 2000


def test_a_load_already_past_its_first_data_request_is_counted_at_once() -> None:
    result = _node("""
await open(); await send(await open(), "/"); await send(await open(), "/measurements");
const started = Date.now();
const settled = classifyConnections(await settledPageLoadConnections(proxy, 5000));
out = { settled, waitedMs: Date.now() - started };
""")
    assert result["settled"] == {"page": 1, "speculative": 1, "data": 1}
    assert int(str(result["waitedMs"])) < 1000


def test_a_page_that_never_sends_a_data_request_is_counted_after_the_wait() -> None:
    result = _node("""
await send(await open(), "/"); await open();
const started = Date.now();
const settled = classifyConnections(await settledPageLoadConnections(proxy, 200));
out = { settled, waitedMs: Date.now() - started };
""")
    assert result["settled"] == {"page": 1, "speculative": 1, "data": 0}
    assert 150 <= int(str(result["waitedMs"])) < 5000


def test_a_previous_loads_socket_writing_late_is_not_the_next_loads() -> None:
    # A socket opened before reset() that writes afterwards neither takes one of the new load's slots nor counts as
    # its first data request.
    result = _node("""
const old = await open();
proxy.reset();
await send(await open(), "/");
old.write("GET /measurements HTTP/1.1\\r\\n\\r\\n");
await pause(100);
out = { firstRequests: proxy.firstRequests(), dataSeen: await proxy.firstDataRequest(50) };
""")
    assert result == {"firstRequests": ["GET / HTTP/1.1"], "dataSeen": False}


def test_the_previous_loads_data_request_does_not_end_the_next_loads_wait() -> None:
    result = _node("""
await send(await open(), "/measurements");
proxy.reset();
await send(await open(), "/");
const pending = await open();
setTimeout(() => pending.write("GET /status HTTP/1.1\\r\\n\\r\\n"), 50);
out = classifyConnections(await settledPageLoadConnections(proxy, 5000));
""")
    assert result == {"page": 1, "speculative": 0, "data": 1}
