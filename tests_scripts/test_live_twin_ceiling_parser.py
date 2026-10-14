"""tests_js/_live_twin_command.js's configuredMaxConnections() sizes the browser tier's tab count, so
it must resolve every device's ceiling exactly as buildgen does - real TOMLs and the shapes a line
match got wrong (CRLF, a trailing comment, a key left to src/'s default) alike, on .nvmrc's Node only."""

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
_NVMRC = _REPO_ROOT / ".nvmrc"
# @tunable l0.live_twin_ceiling_parser_timeout_s = 120
_NODE_TIMEOUT_S = 120


def _pinned_node(nvmrc: Path = _NVMRC) -> str:
    # The Node the browser tier runs, .nvmrc's major, or a failure naming both: a module run on another major could
    # pass here and differ there.
    node = shutil.which("node")
    assert node is not None, "node is not on PATH - the browser tier this pins cannot run without it either"
    version = subprocess.run([node, "--version"], capture_output=True, text=True, check=True, timeout=_NODE_TIMEOUT_S).stdout.strip()
    pinned = nvmrc.read_text(encoding="utf-8").strip()
    message = f"node {version} on PATH, .nvmrc pins {pinned} - run toolchain/setup_toolchain.py env or put the pinned Node first"
    assert version.lstrip("v").split(".")[0] == pinned.lstrip("v").split(".")[0], message
    return node


def _js_ceiling(device: str, devices_dir: Path) -> int:
    node = _pinned_node()
    script = f"import {{ configuredMaxConnections }} from {json.dumps(_MODULE_URL)};\nconsole.log(JSON.stringify(configuredMaxConnections({json.dumps(device)}, {json.dumps(str(devices_dir))})));"
    done = subprocess.run([node, "--input-type=module", "-e", script], cwd=_REPO_ROOT, capture_output=True, text=True, check=False, timeout=_NODE_TIMEOUT_S)
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
    # None: the key is absent from [device], so the build falls back to ServingLimits' max_connections
    # default, src/'s _DEFAULT_MAX_CONNECTIONS.
    assert want == (webserver_init_default(_SRC_DIR, "max_connections") if expected is None else expected)
    assert _js_ceiling(label, tmp_path) == want


def test_a_node_of_another_major_fails(tmp_path: Path) -> None:
    # The pinned-Node check bites: a .nvmrc naming any other major than the Node on PATH fails with both values.
    node = shutil.which("node")
    assert node is not None, "node is not on PATH - the browser tier this pins cannot run without it either"
    major = subprocess.run([node, "--version"], capture_output=True, text=True, check=True, timeout=_NODE_TIMEOUT_S).stdout.strip().lstrip("v").split(".")[0]
    nvmrc = tmp_path / ".nvmrc"
    nvmrc.write_text(f"{int(major) + 1}\n", encoding="utf-8")
    with pytest.raises(AssertionError, match=rf"node v{major}\.\S+ on PATH, \.nvmrc pins {int(major) + 1} - run toolchain/setup_toolchain\.py env or put the pinned Node first"):
        _pinned_node(nvmrc)
