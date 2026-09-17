"""Cross-tier parity for the error-log catalog: every logger GET /status publishes must have a row
in the generated definitions.json, and vice versa. The API side derives itself from the real object
graph; the website side is a hand-kept catalog - nothing compared the two, and both drifts are silent."""

from __future__ import annotations

import json
import os
import subprocess
from typing import TYPE_CHECKING

import pytest

from buildgen.definitions import generate_definitions
from buildgen.generate import generate_device
from buildgen.validate import build_model

if TYPE_CHECKING:
    from pathlib import Path

_DEVICES = ("arzi", "dev", "grkizi", "klkizi", "schlafzi", "wozi")
# One device per process, at the same -X heapsize scripts/test.sh passes the unit-test tier: the
# Unix port's own 2MB default cannot hold `dev`'s full object graph (it fails with a MemoryError
# while draining the /status body). A host-side harness setting, unrelated to the rp2040's own RAM.
_HEAPSIZE = "16M"
_PROBE_TIMEOUT_S = 120.0
# Reuses tests/_sensortask_scenarios.py's own build()/_dispatch() rather than reconstructing a
# device by hand: it already owns the per-device FRAM fake selection and the TmpScratch config dir,
# and a second copy of that setup here would be the thing most likely to drift out from under this
# check. register_for_device() is its public entry point; the side effect this needs is the scratch
# dir it installs.
_PROBE = """import json
import sys
sys.path.insert(0, "tests")
import _sensortask_scenarios as s

device = sys.argv[1]
s.register_for_device(device)  # sets up this device's own TmpScratch config dir
module = s.build(device)
res = s._dispatch(module, "GET", "/status")
print("ERRCOUNT_KEYS=" + json.dumps(sorted(json.loads(s.status_body(res))["errcount"].keys())))
"""


def _website_keys(repo_root: Path, device: str) -> set[str]:
    """The errcount rows js/templates.js will render, straight from the real generator."""
    model = build_model(repo_root / "devices" / f"{device}.toml", repo_root / "src")
    groups = [g for section in generate_definitions(model, repo_root / "src")["sections"] for g in section["groups"] if g.get("kind") == "errcount"]
    assert len(groups) == 1, f"expected exactly one errcount group for {device}, got {len(groups)}"
    return {module_info["key"] for module_info in groups[0]["modules"]}


def _api_keys(repo_root: Path, micropython_bin: Path, tmp_path: Path, device: str) -> set[str]:
    """GET /status's real errcount keys, from a genuinely built object graph under the Unix port.

    Generated into tmp_path rather than read from build/generated_src: a bare `pytest tests_scripts`
    run has no guarantee that tree exists or is current, and a stale module would silently answer
    for a device TOML that no longer looks like this.
    """
    generated = generate_device(repo_root / "devices" / f"{device}.toml", repo_root / "src")
    (tmp_path / f"sensortask_{device}.py").write_text(generated.module_source)
    probe = tmp_path / "probe_errcount.py"
    probe.write_text(_PROBE)
    env = dict(os.environ)
    # tmp_path first, so `import sensortask_<device>` resolves to the module just generated.
    env["MICROPYPATH"] = f"{tmp_path}:src:tests:frozen_modules:.frozen"
    env["TZ"] = "UTC"  # CLAUDE.md: the Unix port's mktime() reads the host's $TZ
    result = subprocess.run(
        [str(micropython_bin), "-X", f"heapsize={_HEAPSIZE}", str(probe), device],
        capture_output=True, text=True, check=False, cwd=repo_root, env=env, timeout=_PROBE_TIMEOUT_S,
    )
    assert result.returncode == 0, f"the {device} probe failed:\n{result.stdout}\n{result.stderr}"
    line = next((ln for ln in result.stdout.splitlines() if ln.startswith("ERRCOUNT_KEYS=")), None)
    assert line is not None, f"the {device} probe printed no key line:\n{result.stdout}"
    return set(json.loads(line[len("ERRCOUNT_KEYS=") :]))


@pytest.mark.parametrize("device", _DEVICES)
def test_every_published_error_source_has_a_website_row_and_vice_versa(repo_root: Path, micropython_bin: Path, tmp_path: Path, device: str) -> None:
    # Both directions matter, and both fail silently today. A source missing from the catalog is
    # simply never rendered; a catalog row with no source renders a permanent, reassuring "0",
    # because js/templates.js falls back to `errcount[key] ?? {counter: 0}`.
    api = _api_keys(repo_root, micropython_bin, tmp_path, device)
    website = _website_keys(repo_root, device)
    assert api == website, (
        f"{device}: the published error sources and the website's errcount rows have drifted.\n"
        f"  published but never displayed: {sorted(api - website)}\n"
        f"  displayed but never published (renders a permanent 0): {sorted(website - api)}"
    )
