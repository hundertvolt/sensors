"""scripts/preview_server.py, `npm run preview`'s server: bound to 127.0.0.1 on a port of its own (0 here, the pytest
tier's ephemeral-port rule), it serves the page's four directories and nothing beside them - not the repo root, .git/,
a spilled config file or a path that climbs or links out - and a taken port is one line naming --port, exit 1."""

import http.client
import socket
import subprocess
import sys
import threading
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING

import pytest
from _script_loader import load_script_module

if TYPE_CHECKING:
    from collections.abc import Iterator

_SCRIPT = Path("scripts") / "preview_server.py"
# Every file a fixture root holds: the ones the preview serves, and the ones beside them it refuses.
_SERVED = ("html/index.html", "js/app.js", "mockdata/samples.json", "build/generated_src/definitions/index.json")
_REFUSED = (".git/HEAD", "config_WIFI.cfg", "pyproject.toml", "build/generated_src/sensortask_fixture-device.py")


@pytest.fixture(scope="module")
def preview_server(repo_root: Path) -> ModuleType:
    return load_script_module(repo_root / _SCRIPT, "preview_server")


@pytest.fixture(scope="module")
def site_root(tmp_path_factory: pytest.TempPathFactory) -> Path:
    tmp_path = tmp_path_factory.mktemp("site_root")
    for relative in (*_SERVED, *_REFUSED):
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"content of {relative}\n", encoding="utf-8")
    # A link inside a served directory that leads out of it, to a file outside the site.
    (tmp_path / "html" / "leak.cfg").symlink_to(tmp_path / "config_WIFI.cfg")
    return tmp_path


@pytest.fixture(scope="module")
def serving(preview_server: ModuleType, site_root: Path) -> "Iterator[tuple[str, int]]":
    # One server for the module, polled briefly: each shutdown waits out serve_forever()'s poll interval.
    server = preview_server.make_server(0, site_root)
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
    thread.start()
    try:
        yield server.server_address[0], server.server_address[1]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=10)


def _get(address: "tuple[str, int]", path: str) -> "tuple[int, bytes]":
    # http.client sends the path exactly as written, so a climbing path reaches the server unnormalized.
    connection = http.client.HTTPConnection(*address, timeout=10)
    try:
        connection.request("GET", path)
        response = connection.getresponse()
        return response.status, response.read()
    finally:
        connection.close()


def test_the_preview_binds_loopback_only(serving: "tuple[str, int]") -> None:
    assert serving[0] == "127.0.0.1"


@pytest.mark.parametrize("relative", _SERVED)
def test_the_pages_own_directories_are_served(serving: "tuple[str, int]", relative: str) -> None:
    assert _get(serving, f"/{relative}") == (200, f"content of {relative}\n".encode())


@pytest.mark.parametrize("relative", _REFUSED)
def test_a_file_beside_the_site_is_refused(serving: "tuple[str, int]", relative: str) -> None:
    status, _ = _get(serving, f"/{relative}")
    assert status == 404, f"/{relative} answered {status}: the preview served a file outside the site"


@pytest.mark.parametrize("path", ["/html/../pyproject.toml", "/js/../.git/HEAD", "/html/leak.cfg", "/", "/html/%2e%2e/config_WIFI.cfg"])
def test_a_path_that_climbs_or_links_out_of_the_site_is_refused(serving: "tuple[str, int]", path: str) -> None:
    status, body = _get(serving, path)
    assert status == 404, f"{path} answered {status} with {body[:80]!r}"


def test_a_taken_port_is_one_line_naming_the_option_and_exit_1(repo_root: Path) -> None:
    with socket.socket() as holder:
        holder.bind(("127.0.0.1", 0))
        holder.listen()
        port = holder.getsockname()[1]
        done = subprocess.run([sys.executable, str(repo_root / _SCRIPT), "--port", str(port)], capture_output=True, text=True, check=False, timeout=60)
    assert done.returncode == 1, done.stderr
    assert len(done.stderr.strip().splitlines()) == 1 and "--port" in done.stderr and str(port) in done.stderr, done.stderr
