"""Proves a Session-3-generated `sensortask_<device>.py` module actually boots under the digital
twin's real MicroPython Unix-port environment and serves real REST requests - not just that it
`ast.parse()`s (buildgen/'s own documented proof depth) or that the wiring plan
buildgen.twin_wiring computes looks right in isolation (test_buildgen_twin_wiring.py).

Spawns the real Unix-port binary as a subprocess and speaks plain HTTP to it, the same pattern
scripts/_digital_twin_ci_suite.py already uses for the hand-written sensortask_wozi.py - this file
is the equivalent proof for GENERATED modules, run here (not wired into scripts/run_digital_twin_ci.sh)
because building the real per-device CI matrix is explicitly Session 6's job
(BUILD_CHAIN_PLAN.md's Session 5 write-up), not this session's. See digital_twin/README.md's
"Booting a generated device" section for the full mechanism this exercises."""

from __future__ import annotations

import http.client
import json
import os
import socket
import subprocess
import time
from typing import TYPE_CHECKING, Any

import pytest

from buildgen.generate import generate_device
from buildgen.twin_wiring import compute_twin_wiring

if TYPE_CHECKING:
    from pathlib import Path

_HOST = "127.0.0.1"
_HTTP_OK = 200
_BOOT_TIMEOUT_S = 30.0
_SHUTDOWN_TIMEOUT_S = 15.0
# No real static content is needed - this suite never requests "/" (asy_webserver_service.py's own
# static route only touches frozen_html lazily, per request - see this file's own module docstring
# reasoning, confirmed directly by reading that route's implementation).
_STUB_FROZEN_HTML = '"""Test-only stub - digital_twin/machine.py has no static content of its own; this suite never requests \'/\'."""\n'
_SMOKE_ENDPOINTS = ("/measurements", "/sensors", "/networking", "/system", "/status")


@pytest.fixture
def src_dir(repo_root: Path) -> Path:
    return repo_root / "src"


@pytest.fixture
def ext_dir(repo_root: Path) -> Path:
    return repo_root / "ext"


@pytest.fixture
def fixtures_dir(repo_root: Path) -> Path:
    return repo_root / "tests_scripts" / "buildgen_fixtures"


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((_HOST, 0))
        return int(s.getsockname()[1])


def _http_get(port: int, path: str, timeout: float = 5.0) -> tuple[int, Any]:
    conn = http.client.HTTPConnection(_HOST, port, timeout=timeout)
    try:
        conn.request("GET", path)
        res = conn.getresponse()
        raw = res.read()
        content_type = res.getheader("Content-Type", "")
        parsed = json.loads(raw) if raw and "json" in content_type else None
        return res.status, parsed
    finally:
        conn.close()


def _wait_until_serving(proc: subprocess.Popen[str], port: int, timeout_s: float) -> None:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"digital twin subprocess exited early with code {proc.returncode} before ever serving - see its own captured output")
        try:
            status, _ = _http_get(port, "/system", timeout=1.0)
            if status == _HTTP_OK:
                return
        except OSError:
            pass
        time.sleep(0.25)
    raise TimeoutError(f"generated device never started serving on {_HOST}:{port} within {timeout_s}s")


def _boot_generated_device(repo_root: Path, micropython_bin: Path, src_dir: Path, ext_dir: Path, device_toml: Path, tmp_path: Path, port: int) -> list[str]:
    """Generates `device_toml` via buildgen, boots the result under run_generic_integration.py in a
    real MicroPython Unix-port subprocess, hits a handful of real REST endpoints, and returns any
    failures (empty list = clean boot, clean REST responses, clean shutdown)."""
    generated = generate_device(device_toml, src_dir, ext_dir)
    module_name = f"sensortask_{generated.model.device}"
    (tmp_path / f"{module_name}.py").write_text(generated.module_source)
    (tmp_path / "frozen_html.py").write_text(_STUB_FROZEN_HTML)

    wiring_plan = compute_twin_wiring(generated.model)
    wiring_plan_path = tmp_path / "wiring_plan.json"
    wiring_plan_path.write_text(json.dumps(wiring_plan))

    env = dict(os.environ)
    # tmp_path first: makes `import sensortask_<device>` (inside run_generic_integration.py) resolve
    # to THIS generated module rather than any same-named hand-written one under src/ (wozi/dev) -
    # every other import the generated module itself needs (asy_i2c_driver, microdot, ...) still
    # falls through to src/ent, since tmp_path holds nothing else.
    env["MICROPYPATH"] = f"{tmp_path}:src:digital_twin:ext:.frozen"
    env["TZ"] = "UTC"
    cmd = [
        str(micropython_bin),
        "digital_twin/run_generic_integration.py",
        "--module", module_name,
        "--wiring-plan", str(wiring_plan_path),
        "--device", generated.model.device,
        "--host", _HOST,
        "--port", str(port),
        "--duration", "3",
    ]
    proc = subprocess.Popen(cmd, cwd=repo_root, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    failures: list[str] = []
    try:
        _wait_until_serving(proc, port, _BOOT_TIMEOUT_S)
        for path in _SMOKE_ENDPOINTS:
            status, body = _http_get(port, path)
            if status != _HTTP_OK:
                failures.append(f"GET {path} -> {status}")
            elif not isinstance(body, dict):
                failures.append(f"GET {path} -> non-JSON-object body {body!r}")
    finally:
        try:
            proc.wait(timeout=_SHUTDOWN_TIMEOUT_S)
        except subprocess.TimeoutExpired:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=5)
            failures.append("subprocess did not exit cleanly within the duration + shutdown window - had to be terminated")
        output = proc.stdout.read() if proc.stdout else ""
        if proc.returncode not in (0, None):
            failures.append(f"subprocess exited with code {proc.returncode}:\n{output}")
    return failures


@pytest.mark.parametrize("device_toml_name", ["novel_combo.toml", "multi_instance.toml"])
def test_synthetic_fixture_boots_and_serves_over_real_http(
    repo_root: Path, micropython_bin: Path, src_dir: Path, ext_dir: Path, fixtures_dir: Path, tmp_path: Path, device_toml_name: str,
) -> None:
    # The two mandatory synthetic fixtures (BUILD_CHAIN_PLAN.md's acceptance criteria #2) - proves
    # the generic digital-twin wiring mechanism handles a hardware combination none of the 6 real
    # devices use (two SCD30 instances, a shared-bus multi-device layout, ...), not just wozi/dev's
    # own two already-hand-verified layouts.
    device_toml = fixtures_dir / device_toml_name
    port = _free_port()
    failures = _boot_generated_device(repo_root, micropython_bin, src_dir, ext_dir, device_toml, tmp_path, port)
    assert failures == []


@pytest.mark.parametrize("device", ["wozi", "dev"])
def test_real_device_boots_its_generated_module_and_serves_over_real_http(
    repo_root: Path, micropython_bin: Path, src_dir: Path, ext_dir: Path, tmp_path: Path, device: str,
) -> None:
    # The two real devices' own TOML, generated fresh here rather than imported as the hand-written
    # src/sensortask_wozi.py/sensortask_dev.py digital_twin/run_wozi_integration.py/
    # run_dev_integration.py boot - this is the actual proof that Session 3's generator produces a
    # module that runs, not just one that ast.parse()s.
    device_toml = repo_root / "devices" / f"{device}.toml"
    port = _free_port()
    failures = _boot_generated_device(repo_root, micropython_bin, src_dir, ext_dir, device_toml, tmp_path, port)
    assert failures == []
