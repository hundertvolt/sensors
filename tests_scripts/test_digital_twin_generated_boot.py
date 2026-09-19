"""Proves a Session-3-generated `sensortask_<device>.py` module actually boots under the digital twin's real MicroPython Unix-port environment and serves real REST requests - not just that it `ast.parse()`s (buildgen/'s own documented proof depth ceiling) or that buildgen.twin_wiring's plan looks right in isolation (test_buildgen_twin_wiring.py).
Spawns the real Unix-port binary as a subprocess and speaks plain HTTP to it, the same pattern scripts/_digital_twin_ci_suite.py already uses for the hand-written sensortask_wozi.py; wiring this into scripts/run_digital_twin_ci.sh stays Session 6's job (SPECIFICATION.md Part L.4).
See digital_twin/README.md's "Booting a generated device" section for the full mechanism this exercises."""

from __future__ import annotations

import http.client
import json
import os
import socket
import subprocess
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
from _devices import DEVICE_NAMES
from _devices import device_toml as device_toml_path

from buildgen.definitions import generate_definitions
from buildgen.generate import generate_device
from buildgen.twin_wiring import compute_twin_wiring

if TYPE_CHECKING:
    from buildgen.model import DeviceModel

_HOST = "127.0.0.1"
_HTTP_OK = 200
_BOOT_TIMEOUT_S = 30.0
_SHUTDOWN_TIMEOUT_S = 15.0
# Must outlast real boot-to-serving latency plus the smoke loop's sequential round trips. The
# old `3` passed only on unintentional slack in a slower shutdown sequence; removing that slack
# exposed the budget as always having been too tight, not a new regression.

# Raised to 15 once the implicit-FRAM-wiring rule gave conn/ntp/webserver real FRAM-backed
# loggers: each does a chunk read/write on its first task run, all sharing one process-wide lock
# inside the same ~1s task-start stagger window.

# Measured, not estimated: boot-to-first-200 lands between ~4.5s and ~6.3s across the six real
# devices, dev slowest. A boot-time-only, self-resolving cost that leaves steady-state serving
# untouched - and boot latency is not a thing to optimise for its own sake (CLAUDE.md).
_TWIN_DURATION_S = 15
# No real static content is needed - this suite never requests "/" (asy_webserver_service.py's own
# static route only touches frozen_html lazily, per request - see this file's own module docstring
# reasoning, confirmed directly by reading that route's implementation).
_STUB_FROZEN_HTML = '"""Test-only stub - digital_twin/machine.py has no static content of its own; this suite never requests \'/\'."""\n'
_SMOKE_ENDPOINTS = ("/measurements", "/sensors", "/networking", "/system", "/status")

# Discovered, never listed: a device TOML added to devices/ is covered by every test below with no
# edit here, which is the whole point of a generated build chain. Same for a new synthetic fixture,
# minus the deliberately malformed ones (they exist to be rejected, not booted).
#
# Through _devices.DEVICE_NAMES, not a local glob of devices/*.toml: that glob ran at collection
# time, before conftest.py reclaims a zz_test_*.toml leaked by a SIGKILLed run - and this is the
# one suite that would actually BOOT that deliberately malformed fixture.
_REPO_ROOT = Path(__file__).resolve().parent.parent
_FIXTURE_TOMLS = sorted(p.name for p in (_REPO_ROOT / "tests_scripts" / "buildgen_fixtures").glob("*.toml") if not p.name.startswith("malformed_"))


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


def _website_errcount_keys(model: DeviceModel, src_dir: Path) -> set[str]:
    """The errcount rows js/templates.js will render for this device, from the real generator."""
    groups = [g for section in generate_definitions(model, src_dir)["sections"] for g in section["groups"] if g.get("kind") == "errcount"]
    assert len(groups) == 1, f"expected exactly one errcount group for {model.device}, got {len(groups)}"
    return {row["key"] for row in groups[0]["modules"]}


def _errcount_parity_failures(model: DeviceModel, src_dir: Path, status_body: object) -> list[str]:
    """Compares the error sources GET /status really publishes against the website's own catalog.
    The API derives itself from the live object graph; buildgen/definitions.py's catalog is
    hand-kept. Both drift directions are silent in the product - SPECIFICATION.md Part H.6."""
    if not isinstance(status_body, dict) or not isinstance(status_body.get("errcount"), dict):
        return ["GET /status carried no usable errcount object, so no parity claim would mean anything"]
    published = set(status_body["errcount"])
    displayed = _website_errcount_keys(model, src_dir)
    # No exemptions: _errcount_group() derives its rows per logger instance now (BACKLOG item 31,
    # fixed 2026-09-18), so the two multi-instance fixtures agree exactly like the six real devices.
    missing = published - displayed
    extra = displayed - published
    failures = []
    if missing:
        failures.append(f"error sources published by GET /status with no website row (never displayed): {sorted(missing)}")
    if extra:
        failures.append(f"website errcount rows with no published source (each renders a permanent 0): {sorted(extra)}")
    return failures


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
    # every other import the generated module needs still falls through to `src/`/`ext/`, unaffected.
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
        "--duration", str(_TWIN_DURATION_S),
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
            elif path == "/status":
                # Rides the body this loop already fetched - the parity check costs no extra boot,
                # and inherits this test's own generic device/fixture coverage for free.
                failures.extend(_errcount_parity_failures(generated.model, src_dir, body))
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


@pytest.mark.parametrize("device_toml_name", _FIXTURE_TOMLS)
def test_synthetic_fixture_boots_and_serves_over_real_http(
    repo_root: Path, micropython_bin: Path, src_dir: Path, ext_dir: Path, fixtures_dir: Path, tmp_path: Path, device_toml_name: str,
) -> None:
    # The two mandatory synthetic fixtures (SPECIFICATION.md Part L.1's acceptance criterion #2) - proves
    # the generic wiring mechanism handles a hardware combination none of the 6 real devices use,
    # not just wozi/dev's own two already-hand-verified layouts.
    device_toml = fixtures_dir / device_toml_name
    port = _free_port()
    failures = _boot_generated_device(repo_root, micropython_bin, src_dir, ext_dir, device_toml, tmp_path, port)
    assert failures == []


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_real_device_boots_its_generated_module_and_serves_over_real_http(
    repo_root: Path, micropython_bin: Path, src_dir: Path, ext_dir: Path, tmp_path: Path, device: str,
) -> None:
    # Every real device's own TOML, generated fresh here - the actual proof that Session 3's
    # generator produces a module that runs, for every real device, not just ast.parse()s
    # (SPECIFICATION.md Part L.4: "ideally every" entry point).
    toml_path = device_toml_path(device)
    port = _free_port()
    failures = _boot_generated_device(repo_root, micropython_bin, src_dir, ext_dir, toml_path, tmp_path, port)
    assert failures == []
