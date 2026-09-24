"""tests_js/_live_twin_command.js's configuredMaxConnections() sizes the browser tier's tab count, so
it must resolve every device's ceiling exactly as buildgen does - real TOMLs and the shapes a line
match got wrong (CRLF, a trailing comment, a key left to src/'s default) alike."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest
from _devices import DEVICE_NAMES, device_toml

from buildgen.validate import device_max_connections, webserver_init_default

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SRC_DIR = _REPO_ROOT / "src"
_MODULE_URL = (_REPO_ROOT / "tests_js" / "_live_twin_command.js").as_uri()


def _js_ceiling(device: str, devices_dir: Path) -> int:
    node = shutil.which("node")
    assert node is not None, "node is not on PATH - the browser tier this pins cannot run without it either"
    script = f"import {{ configuredMaxConnections }} from {json.dumps(_MODULE_URL)};\nconsole.log(JSON.stringify(configuredMaxConnections({json.dumps(device)}, {json.dumps(str(devices_dir))})));"
    done = subprocess.run([node, "--input-type=module", "-e", script], cwd=_REPO_ROOT, capture_output=True, text=True, check=False, timeout=120)
    assert done.returncode == 0, done.stderr
    value = json.loads(done.stdout.strip().splitlines()[-1])
    assert isinstance(value, int), value
    return value


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_every_real_device_resolves_to_buildgen_s_own_ceiling(device: str) -> None:
    assert _js_ceiling(device, device_toml(device).parent) == device_max_connections(device_toml(device), _SRC_DIR)


@pytest.mark.parametrize(
    ("label", "text", "expected"),
    [
        ("crlf", '[device]\r\nname = "x"\r\nmax_connections = 4\r\n\r\n[bus.i2c0]\r\nsda = 0\r\n', 4),
        ("trailing_comment", '[device]\nname = "x"\nmax_connections = 5  # raised for the bench\n', 5),
        ("other_table_only", '[device]\nname = "x"\n\n[webserver]\nmax_connections = 9\n', None),
        ("missing_key", '[device]\nname = "x"\n', None),
    ],
)
def test_synthetic_tomls_resolve_as_buildgen_resolves_them(tmp_path: Path, label: str, text: str, expected: "int | None") -> None:
    toml = tmp_path / f"{label}.toml"
    toml.write_bytes(text.encode())
    want = device_max_connections(toml, _SRC_DIR)
    # None: the key is absent from [device], so the build falls back to WebserverService's default.
    assert want == (webserver_init_default(_SRC_DIR, "max_connections") if expected is None else expected)
    assert _js_ceiling(label, tmp_path) == want
