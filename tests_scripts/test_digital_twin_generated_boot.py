"""Proves a Session-3-generated `sensortask_<device>.py` module actually boots under the digital twin's real MicroPython Unix-port environment and serves real REST requests - not just that it `ast.parse()`s (buildgen/'s own documented proof depth ceiling) or that buildgen.twin_wiring's plan looks right in isolation (test_buildgen_twin_wiring.py).
Spawns the real Unix-port binary as a subprocess and speaks plain HTTP to it, the same pattern scripts/_digital_twin_ci_suite.py already uses for the hand-written sensortask_wozi.py; wiring this into scripts/run_digital_twin_ci.sh stays Session 6's job (BUILD_CHAIN_PLAN.md's Session 5 write-up).
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

from buildgen.definitions import generate_definitions
from buildgen.generate import generate_device
from buildgen.twin_wiring import compute_twin_wiring

if TYPE_CHECKING:
    from buildgen.model import DeviceModel

_HOST = "127.0.0.1"
_HTTP_OK = 200
_BOOT_TIMEOUT_S = 30.0
_SHUTDOWN_TIMEOUT_S = 15.0
# Must comfortably outlast real boot-to-serving latency plus the 5-endpoint smoke loop's own
# sequential HTTP round trips - `3` used to pass only because an older, slower
# `run_generic_integration.py` shutdown sequence added a few seconds of unintentional slack after
# the sleep expired; a cleaner/faster shutdown (2026-09-14) removed that slack and exposed this
# budget as always having been too tight, not a new regression to chase in the twin itself
# (confirmed directly: the pre-refactor file reproduces the identical ~1.9s boot latency it had
# before this margin was raised the first time). Raised again, deliberately, from 6 to 15 once WP1
# (WiFi/NTP/webserver inheriting the device's FRAM chip when one is wired, CLAUDE.md's implicit-
# FRAM-wiring rule) wired a real FRAM-backed logger into `conn`/`ntp`/`webserver` (plus `conn`'s own
# `DNSServer`): each now performs a real chunk read/write the first time its own task runs, sharing
# one process-wide `asyncio.Lock` (`FRAM_SPI`'s own, `src/asy_fram_driver.py`) with every other
# already-FRAM-wired module whose own task is starting in the very same ~1s task-start stagger
# window (`system_service.py`'s `start_and_check_tasks()`) - measured directly, not estimated:
# boot-to-first-200 across all 6 real devices lands between ~4.5s and ~6.3s (`dev` slowest, the
# device with the most FRAM-wired instances), for a real, expected reason - not a new hang, and not
# something to chase down as a code defect. It is a boot-time-only, self-resolving cost (steady-
# state serving is unaffected - the lock is only ever this contended during the one-time startup
# window), matching CLAUDE.md's own already-accepted position that boot latency is not a thing to
# optimise for its own sake; see BACKLOG.md for the finding, in case FRAM-chunk-lock contention at
# boot ever needs its own fix once WP2 adds another chunk per FRAM-wired sensor's own ConfigManager.
_TWIN_DURATION_S = 15
# No real static content is needed - this suite never requests "/" (asy_webserver_service.py's own
# static route only touches frozen_html lazily, per request - see this file's own module docstring
# reasoning, confirmed directly by reading that route's implementation).
_STUB_FROZEN_HTML = '"""Test-only stub - digital_twin/machine.py has no static content of its own; this suite never requests \'/\'."""\n'
_SMOKE_ENDPOINTS = ("/measurements", "/sensors", "/networking", "/system", "/status")

# Discovered, never listed: a device TOML added to devices/ is covered by every test below with no
# edit here, which is the whole point of a generated build chain. Same for a new synthetic fixture,
# minus the deliberately malformed ones (they exist to be rejected, not booted).
_REPO_ROOT = Path(__file__).resolve().parent.parent
_REAL_DEVICE_TOMLS = sorted(p.name for p in (_REPO_ROOT / "devices").glob("*.toml"))
_FIXTURE_TOMLS = sorted(p.name for p in (_REPO_ROOT / "tests_scripts" / "buildgen_fixtures").glob("*.toml") if not p.name.startswith("malformed_"))

# Reported, not fixed (BACKLOG item 31, and CLAUDE.md's "flag, don't silently change" rule for a
# cross-file discrepancy a scan turns up). buildgen/definitions.py's _errcount_group() is keyed by
# DRIVER KIND - it receives only a set of have-keys and has no instance information at all - while
# the API publishes one key per LOGGER INSTANCE. No real device is affected (none declares two
# instances of one driver, and dev's uart_link pair happens to use exactly the name_ext values the
# catalog hardcodes), so this is latent, not live. Both synthetic fixtures are affected, which is
# precisely what a fixture is for. Pinned exactly rather than waved through: closing the gap makes
# this fail and prompts the exemption's removal, and any OTHER drift still fails immediately.
# Each value is (published-but-never-displayed, displayed-but-never-published).
_KNOWN_CATALOG_DRIFT: dict[str, tuple[frozenset[str], frozenset[str]]] = {
    "novel_combo": (
        frozenset({"SCD30_primary", "SCD30_secondary", "UART_a", "UART_b"}),
        frozenset({"SCD30", "UART_init", "UART_resp"}),
    ),
    "multi_instance": (
        frozenset({"BMP3XX_only", "CFGMGR_BMP3XX_only", "CFGMGR_SGP40_a", "CFGMGR_SGP40_b", "SCD30_a", "SCD30_b", "SGP40_a", "SGP40_b"}),
        frozenset({"BMP3XX", "CFGMGR_BMP3XX", "CFGMGR_SGP40", "SCD30", "SGP40"}),
    ),
}


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

    The two sides are built by unrelated mechanisms: the API derives itself from the live object
    graph (SensorReaderConfig.get_error_sources() returns [self, self.cfgmgr], and the generated
    _collect_error_sources() is a plain loop over every constructed module), while the catalog in
    buildgen/definitions.py is hand-kept. Both drift directions are silent in the product - a source
    with no row is never rendered, and a row with no source renders a permanent, reassuring "0",
    because js/templates.js falls back to `errcount[key] ?? {counter: 0}`.
    """
    if not isinstance(status_body, dict) or not isinstance(status_body.get("errcount"), dict):
        return ["GET /status carried no usable errcount object, so no parity claim would mean anything"]
    published = set(status_body["errcount"])
    displayed = _website_errcount_keys(model, src_dir)
    expected_missing, expected_extra = _KNOWN_CATALOG_DRIFT.get(model.device, (frozenset(), frozenset()))
    missing = (published - displayed) - expected_missing
    extra = (displayed - published) - expected_extra
    failures = []
    if missing:
        failures.append(f"error sources published by GET /status with no website row (never displayed): {sorted(missing)}")
    if extra:
        failures.append(f"website errcount rows with no published source (each renders a permanent 0): {sorted(extra)}")
    # The exemption is a record of a REPORTED gap, not a licence. Once the catalog derives per
    # instance, these stop being drift and the stale entry has to go - loudly, not quietly.
    if expected_missing and not (expected_missing & published):
        failures.append(f"{model.device}'s _KNOWN_CATALOG_DRIFT entry is stale - the gap appears to be fixed, so delete it (and BACKLOG item 31) rather than carrying it")
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
    # The two mandatory synthetic fixtures (BUILD_CHAIN_PLAN.md's acceptance criteria #2) - proves
    # the generic wiring mechanism handles a hardware combination none of the 6 real devices use,
    # not just wozi/dev's own two already-hand-verified layouts.
    device_toml = fixtures_dir / device_toml_name
    port = _free_port()
    failures = _boot_generated_device(repo_root, micropython_bin, src_dir, ext_dir, device_toml, tmp_path, port)
    assert failures == []


@pytest.mark.parametrize("device_toml_name", _REAL_DEVICE_TOMLS)
def test_real_device_boots_its_generated_module_and_serves_over_real_http(
    repo_root: Path, micropython_bin: Path, src_dir: Path, ext_dir: Path, tmp_path: Path, device_toml_name: str,
) -> None:
    # Every real device's own TOML, generated fresh here - the actual proof that Session 3's
    # generator produces a module that runs, for every real device, not just ast.parse()s
    # (BUILD_CHAIN_PLAN.md's Session 5 write-up: "ideally every" entry point).
    device_toml = repo_root / "devices" / device_toml_name
    port = _free_port()
    failures = _boot_generated_device(repo_root, micropython_bin, src_dir, ext_dir, device_toml, tmp_path, port)
    assert failures == []
