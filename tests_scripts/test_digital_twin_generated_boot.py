"""Proves a Session-3-generated `sensortask_<device>.py` module actually boots under the digital twin's real MicroPython Unix-port environment and serves real REST requests - not just that it `ast.parse()`s (buildgen/'s own documented proof depth ceiling) or that buildgen.twin_wiring's plan looks right in isolation (test_buildgen_twin_wiring.py).
Spawns the real Unix-port binary as a subprocess and speaks plain HTTP to it, the same pattern scripts/_digital_twin_ci_suite.py already uses for the hand-written sensortask_wozi.py; wiring this into scripts/run_digital_twin_ci.sh stays Session 6's job (SPECIFICATION.md Part L.4).
See digital_twin/README.md's "Booting a generated device" section for the full mechanism this exercises."""

from __future__ import annotations

import http.client
import json
import os
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
from _devices import DEVICE_NAMES
from _devices import device_toml as device_toml_path
from _script_loader import load_script_module

from buildgen.definitions import generate_definitions
from buildgen.generate import generate_device
from buildgen.twin_wiring import compute_twin_wiring

if TYPE_CHECKING:
    from collections.abc import Callable

_HOST = "127.0.0.1"
_HTTP_OK = 200
# @tunable l0.generated_boot_boot_timeout_s = 30.0
_BOOT_TIMEOUT_S = 30.0
# @tunable l0.generated_boot_shutdown_timeout_s = 15.0
_SHUTDOWN_TIMEOUT_S = 15.0
# @tunable l0.generated_boot_poll_timeout_s = 1.0
_POLL_TIMEOUT_S = 1.0  # one readiness GET
# @tunable l0.generated_boot_poll_step_s = 0.25
_POLL_STEP_S = 0.25
# @tunable l0.generated_boot_exit_wait_s = 5
_EXIT_WAIT_S = 5  # a signalled twin's exit, before the next, harder signal
# Must outlast real boot-to-serving latency plus the smoke loop's sequential round trips. The
# old `3` passed only on unintentional slack in a slower shutdown sequence; removing that slack
# exposed the budget as always having been too tight, not a new regression.

# Raised to 15 once the implicit-FRAM-wiring rule gave conn/ntp/webserver real FRAM-backed
# loggers: each does a chunk read/write on its first task run, all sharing one process-wide lock
# inside the same ~1s task-start stagger window.

# Measured, not estimated: boot-to-first-200 lands between ~4.5s and ~6.3s across the six real
# devices, dev slowest. A boot-time-only, self-resolving cost that leaves steady-state serving
# untouched - and boot latency is not a thing to optimise for its own sake (CLAUDE.md).
# @tunable l0.generated_boot_twin_duration_s = 15
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

# The allocation-failure markers every gate shares, from the hardware tier's harness
# (tests_scripts/test_memory_error_gate_agreement.py keeps the gates agreeing).
_MEMORY_ERROR_MARKERS: tuple[str, ...] = tuple(load_script_module(_REPO_ROOT / "tests_hardware" / "harness.py", "harness").MEMORY_ERROR_MARKERS)


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
            raise RuntimeError(f"digital twin subprocess exited early with code {proc.returncode} before ever serving - see its output in the failures below")
        try:
            status, _ = _http_get(port, "/system", timeout=_POLL_TIMEOUT_S)
            if status == _HTTP_OK:
                return
        except OSError:
            pass
        time.sleep(_POLL_STEP_S)
    raise TimeoutError(f"generated device never started serving on {_HOST}:{port} within {timeout_s}s")


def _website_errcount_keys(definitions: dict[str, Any]) -> set[str]:
    """The errcount rows js/templates.js will render for this device: the union over every errcount
    group, wherever the definitions place one (the captive DNS history sits on Networking)."""
    groups = [g for section in definitions["sections"] for g in section["groups"] if g.get("kind") == "errcount"]
    assert groups, f"no errcount group in {definitions['device']['id']}'s definitions"
    return {row["key"] for g in groups for row in g["modules"]}


def _errcount_parity_failures(definitions: dict[str, Any], status_body: object) -> list[str]:
    """Compares the error sources GET /status really publishes against the website's own catalog.
    The API derives itself from the live object graph; buildgen/definitions.py's catalog is
    hand-kept. Both drift directions are silent in the product - SPECIFICATION.md Part H.6."""
    if not isinstance(status_body, dict) or not isinstance(status_body.get("errcount"), dict):
        return ["GET /status carried no usable errcount object, so no parity claim would mean anything"]
    published = set(status_body["errcount"])
    displayed = _website_errcount_keys(definitions)
    # No exemptions: _errcount_group() derives its rows per logger instance (fixed
    # 2026-09-18), so the two multi-instance fixtures agree exactly like the six real devices.
    missing = published - displayed
    extra = displayed - published
    failures = []
    if missing:
        failures.append(f"error sources published by GET /status with no website row (never displayed): {sorted(missing)}")
    if extra:
        failures.append(f"website errcount rows with no published source (each renders a permanent 0): {sorted(extra)}")
    return failures


def _resolves(body: object, path: list[str]) -> bool:
    """Whether a readonly field's `path` resolves in a GET body; a null leaf is a published value."""
    for step in path:
        if not isinstance(body, dict) or step not in body:
            return False
        body = body[step]
    return True


def _readonly_fields(definitions: dict[str, Any], section_key: str) -> list[tuple[str, dict[str, Any]]]:
    section = next(s for s in definitions["sections"] if s["key"] == section_key)
    return [(g["key"], f) for g in section["groups"] if g.get("kind") != "errcount" for f in g.get("fields", []) if f.get("kind") == "readonly"]


def _status_field_parity_failures(definitions: dict[str, Any], status_body: object) -> list[str]:
    """Every readonly field the Status page names must be in GET /status - the page's catalog of these
    rows is hand-kept, so a key it names but the device never publishes renders blank, silently."""
    if not isinstance(status_body, dict):
        return ["GET /status carried no object, so no field parity claim would mean anything"]
    missing = []
    for group_key, field in _readonly_fields(definitions, "status"):
        source = status_body.get(group_key)
        if group_key == "sensors" and isinstance(source, dict):
            # Maintenance data is per sensor; the page flattens it to <SENSOR>_<field> as js/render.js does.
            source = {f"{sensor}_{key}": value for sensor, values in source.items() if isinstance(values, dict) for key, value in values.items()}
        found = _resolves(source, field["path"]) if "path" in field else isinstance(source, dict) and field["key"] in source
        if not found:
            missing.append(f"{group_key}.{field['key']}")
    return [f"Status page fields GET /status does not publish (each renders blank): {missing}"] if missing else []


def _system_path_failures(definitions: dict[str, Any], system_body: object) -> list[str]:
    """Every readonly System field reads GET /system through its `path` (the build information)."""
    unresolved = [f"{group_key}.{field['key']}" for group_key, field in _readonly_fields(definitions, "system") if "path" in field and not _resolves(system_body, field["path"])]
    return [f"System page paths GET /system does not resolve: {unresolved}"] if unresolved else []


def _twin_output_failures(returncode: int | None, output: str) -> list[str]:
    """The finished twin's own verdict: its exit status, and every output line holding an
    allocation-failure marker (SPECIFICATION.md Part I.4(e)), quoted - a clean exit included."""
    failures = [f"subprocess exited with code {returncode}:\n{output}"] if returncode not in (0, None) else []
    marked = [line for line in output.splitlines() if any(marker in line for marker in _MEMORY_ERROR_MARKERS)]
    if marked:
        failures.append("allocation-failure marker in the twin's output:\n" + "\n".join(marked))
    return failures


def _run_twin(cmd: list[str], cwd: Path, env: dict[str, str], session: Callable[[subprocess.Popen[str]], list[str]], shutdown_timeout_s: float = _SHUTDOWN_TIMEOUT_S) -> tuple[list[str], str]:
    """Runs `session` against the spawned twin, then its exit and output verdicts; returns the
    failures and the twin's whole merged output."""
    proc = subprocess.Popen(cmd, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    # Drained while the twin runs: a pipe read only after exit blocks a child past 64 KiB of output.
    lines: list[str] = []
    reader = threading.Thread(target=lambda: lines.extend(proc.stdout or ()), daemon=True)
    reader.start()
    failures: list[str] = []
    try:
        failures.extend(session(proc))
    except (OSError, RuntimeError, ValueError, http.client.HTTPException) as exc:
        failures.append(f"twin session aborted: {type(exc).__name__}: {exc}")
    finally:
        try:
            proc.wait(timeout=shutdown_timeout_s)
        except subprocess.TimeoutExpired:
            proc.terminate()
            try:
                proc.wait(timeout=_EXIT_WAIT_S)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=_EXIT_WAIT_S)
            failures.append("subprocess did not exit cleanly within the duration + shutdown window - had to be terminated")
        reader.join(timeout=shutdown_timeout_s)
        if reader.is_alive():
            failures.append("the twin's output never reached end of file after its exit - the output below is incomplete")
        output = "".join(lines)
        failures.extend(_twin_output_failures(proc.returncode, output))
    return failures, output


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
    definitions = generate_definitions(generated.model, src_dir)

    def smoke(proc: subprocess.Popen[str]) -> list[str]:
        _wait_until_serving(proc, port, _BOOT_TIMEOUT_S)
        failures: list[str] = []
        for path in _SMOKE_ENDPOINTS:
            status, body = _http_get(port, path)
            if status != _HTTP_OK:
                failures.append(f"GET {path} -> {status}")
            elif not isinstance(body, dict):
                failures.append(f"GET {path} -> non-JSON-object body {body!r}")
            elif path == "/status":
                # Rides the body this loop already fetched - the parity checks cost no extra boot,
                # and inherit this test's own generic device/fixture coverage for free.
                failures.extend(_errcount_parity_failures(definitions, body))
                failures.extend(_status_field_parity_failures(definitions, body))
            elif path == "/system":
                failures.extend(_system_path_failures(definitions, body))
        return failures

    failures, _ = _run_twin(cmd, repo_root, env, smoke)
    return failures


def test_an_allocation_failure_in_a_clean_exiting_twin_is_a_failure() -> None:
    # The degrade-and-pass case: src/ logs str(e), so a caught allocation failure reads "memory
    # allocation failed" in a twin that still serves every request and exits 0.
    output = "serving\n[E] WEBSERVER: memory allocation failed, allocating 2048 bytes\nshutdown complete\n"
    failures = _twin_output_failures(0, output)
    assert len(failures) == 1, failures
    assert "memory allocation failed, allocating 2048 bytes" in failures[0]
    assert _twin_output_failures(0, "serving\nshutdown complete\n") == []
    assert _twin_output_failures(1, "Traceback\n")[0].startswith("subprocess exited with code 1")


def test_a_twin_printing_more_than_a_pipe_buffer_is_drained_while_it_runs(tmp_path: Path) -> None:
    # 128 KiB of boot chatter fills a 64 KiB pipe: read only after exit, the child blocks on its
    # write and is then reported as hung, its real output never scanned.
    child = "import sys\nfor i in range(2048):\n    sys.stdout.write(f'{i:05d} ' + 'x' * 57 + '\\n')\nprint('last line of a long boot')\n"
    failures, output = _run_twin([sys.executable, "-c", child], tmp_path, dict(os.environ), lambda _proc: [], shutdown_timeout_s=10)
    assert failures == []
    assert len(output) > 128 * 1024
    assert output.endswith("last line of a long boot\n")


def test_a_twin_that_dies_before_serving_keeps_its_output(tmp_path: Path) -> None:
    # The boot crash is the evidence: an aborted session must still report the child's own output.
    child = "print('boot banner'); print('Traceback: planted boot crash'); raise SystemExit(3)"

    def session(proc: subprocess.Popen[str]) -> list[str]:
        _wait_until_serving(proc, _free_port(), 10)
        return []

    failures, output = _run_twin([sys.executable, "-c", child], tmp_path, dict(os.environ), session)
    assert "planted boot crash" in output
    assert any(f.startswith("twin session aborted: RuntimeError: digital twin subprocess exited early with code 3") for f in failures), failures
    assert any(f.startswith("subprocess exited with code 3:") and "planted boot crash" in f for f in failures), failures


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
