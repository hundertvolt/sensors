"""Boots every derived device's shipped form under the digital twin: its staged modules stripped and compiled by
mpy-cross, nothing of src/ or ext/ on the path, asserting what the source boot asserts (test_digital_twin_generated_boot.py,
which stays: the two runs over the same checks are the differential). SPECIFICATION.md B.11."""

import contextlib
import functools
import hashlib
import shutil
import socket
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING

import pytest
from _devices import DEVICE_NAMES, device_toml
from _script_loader import load_script_module
from test_digital_twin_generated_boot import _HOST, _STUB_FROZEN_HTML, _boot_generated_device

from buildgen.generate import generate_device

if TYPE_CHECKING:
    from buildgen.generate import GeneratedDevice

# Boots at a time: each a Unix-port twin on its own port, mostly waiting through a few seconds of boot and smoke (under
# half a core each, measured), so all six boot side by side at once.
_BOOTS_AT_ONCE = 6
_COMPILE_TIMEOUT_S = 60


def _compile(mpy_cross: Path, stage: Path, cache: "dict[tuple[str, str], bytes]", kept: str) -> None:
    # Every staged module but the boot entry and `kept` to .mpy, its .py removed; one compile per distinct module text
    # across the devices, run from the stage so the name each embeds is the bare file name, as the image's freeze has it.
    (stage / "main.py").unlink()
    for source in sorted(stage.glob("*.py")):
        if source.name == kept:
            continue
        key = (source.name, hashlib.sha256(source.read_bytes()).hexdigest())
        if key not in cache:
            done = subprocess.run([str(mpy_cross), source.name], cwd=stage, capture_output=True, text=True, check=False, timeout=_COMPILE_TIMEOUT_S)
            assert done.returncode == 0, f"mpy-cross refused {source.name}:\n{done.stdout}{done.stderr}"
            cache[key] = source.with_suffix(".mpy").read_bytes()
        source.with_suffix(".mpy").write_bytes(cache[key])
        source.unlink()
    (stage / "frozen_html.py").write_text(_STUB_FROZEN_HTML, encoding="utf-8")


def _distinct_free_ports(count: int) -> "list[int]":
    # Free ports for boots that run at once, distinct by construction: every probe stays bound until all are.
    with contextlib.ExitStack() as held:
        probes = [held.enter_context(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) for _ in range(count)]
        for probe in probes:
            probe.bind((_HOST, 0))
        return [int(probe.getsockname()[1]) for probe in probes]


@pytest.fixture(scope="module")
def build_firmware(repo_root: Path) -> ModuleType:
    return load_script_module(repo_root / "scripts" / "build_firmware.py", "build_firmware")


@pytest.fixture(scope="module")
def images(build_firmware: ModuleType, mpy_cross: Path, repo_root: Path, tmp_path_factory: pytest.TempPathFactory) -> "dict[str, tuple[GeneratedDevice, Path]]":
    # Each device's stage as build_firmware.py builds it, compiled: its generation and the stage holding only .mpy
    # files and the stub site. Each distinct module text is stripped once across the devices, as _compile() compiles
    # it once: the stripper's result depends on its text and path alone (scripts/_strip_type_checking.py).
    cache: dict[tuple[str, str], bytes] = {}
    found = {}
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(build_firmware, "strip_type_checking_blocks", functools.cache(build_firmware.strip_type_checking_blocks))
        for device in DEVICE_NAMES:
            generated = generate_device(device_toml(device), repo_root / "src", repo_root / "ext")
            stage = tmp_path_factory.mktemp(f"image_{device}")
            build_firmware.stage_python_modules(stage, generated)
            # The device module stays its stripped .py: the twin runner reads its construction lines from the module's
            # __file__ (digital_twin/run_generic_integration.py's _uart_links()), which a .mpy cannot give it.
            _compile(mpy_cross, stage, cache, kept=f"sensortask_{device}.py")
            found[device] = (generated, stage)
    return found


@pytest.fixture(scope="module")
def mpy_cross(micropython_dir: Path, tmp_path_factory: pytest.TempPathFactory) -> Path:
    # The toolchain's own mpy-cross, copied first: a concurrent build_firmware.py wipes mpy-cross/build/.
    built = micropython_dir / "mpy-cross" / "build" / "mpy-cross"
    if not built.is_file():
        pytest.fail(f"mpy-cross not built at {built} - run toolchain/setup_toolchain.py setup first")
    copy = tmp_path_factory.mktemp("mpy_cross") / "mpy-cross"
    shutil.copy2(built, copy)
    return copy


def test_each_image_holds_only_compiled_modules_and_the_stub_site(images: "dict[str, tuple[GeneratedDevice, Path]]") -> None:
    for device, (_generated, stage) in images.items():
        names = sorted(p.name for p in stage.iterdir())
        assert "microdot.mpy" in names and "asy_system_service.mpy" in names, names
        assert [n for n in names if not n.endswith(".mpy")] == sorted(["frozen_html.py", f"sensortask_{device}.py"]), names


def test_every_compiled_image_boots_and_serves_like_its_source(images: "dict[str, tuple[GeneratedDevice, Path]]", micropython_bin: Path, tmp_path: Path) -> None:
    # The boots run side by side, each on its own port with its own runner files, and report per device.
    ports = dict(zip(sorted(images), _distinct_free_ports(len(images)), strict=True))

    def boot(device: str) -> "tuple[str, list[str]]":
        generated, stage = images[device]
        run = tmp_path / device
        run.mkdir()
        return device, _boot_generated_device(stage, generated, micropython_bin, run, ports[device], image=True)

    with ThreadPoolExecutor(max_workers=_BOOTS_AT_ONCE) as pool:
        failures = {device: found for device, found in pool.map(boot, sorted(images)) if found}
    assert failures == {}, "\n\n".join(f"{device}:\n" + "\n".join(found) for device, found in failures.items())
