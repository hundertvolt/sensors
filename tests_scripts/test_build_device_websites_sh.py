"""scripts/build_device_websites.sh builds every derived device's site from its generated definitions:
one frozen module per device under the given root, each serving an index.html whose inlined
definitions name that device, and a reserved zz_test_ fixture TOML never built (SPECIFICATION.md H.2)."""

import ast
import gzip
import json
import re
import subprocess
from pathlib import Path

import pytest
from _devices import DEVICE_NAMES

_INLINED = re.compile(r'<script type="application/json" id="inlined-definitions">(.*?)</script>', re.DOTALL)


def _frozen_file(module_text: str, served_path: str) -> bytes:
    """One file's gzipped bytes out of a freezefs module, read with ast (the module mounts on import)."""
    table = re.search(rf"\(\s*'{re.escape(served_path)}',\s*\(\s*(_f\d+),", module_text)
    assert table is not None, f"{served_path} is not served by this frozen module"
    for node in ast.parse(module_text).body:
        if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name) and node.targets[0].id == table.group(1):
            assert isinstance(node.value, ast.Call) and isinstance(node.value.args[0], ast.Constant)
            data = node.value.args[0].value
            assert isinstance(data, bytes)
            return data
    raise AssertionError(f"{table.group(1)} ({served_path}) has no bytes assignment in the frozen module")


def _inlined_device_id(frozen_module: Path) -> str:
    html = gzip.decompress(_frozen_file(frozen_module.read_text(), "/index.html.gz")).decode()
    match = _INLINED.search(html)
    assert match is not None, f"{frozen_module}: index.html carries no inlined definitions"
    device_id = json.loads(match.group(1))["device"]["id"]
    assert isinstance(device_id, str)
    return device_id


@pytest.fixture(scope="module")
def built_root(repo_root: Path, tmp_path_factory: pytest.TempPathFactory) -> Path:
    # One build of every device for the whole module, with a reserved zz_test_ TOML present: it is
    # malformed, so building it would fail the run, and it is removed again whatever happens.
    out_root = tmp_path_factory.mktemp("device_websites")
    skipped_toml = repo_root / "devices" / "zz_test_device_websites_skip.toml"
    assert not skipped_toml.exists(), "sanity: this test-only device name must not collide with a real device"
    skipped_toml.write_text((repo_root / "tests_scripts" / "buildgen_fixtures" / "malformed_missing_device_table.toml").read_text())
    try:
        result = subprocess.run([str(repo_root / "scripts" / "build_device_websites.sh"), str(out_root)], cwd=repo_root, capture_output=True, text=True, check=False)
    finally:
        skipped_toml.unlink()
    assert result.returncode == 0, f"build_device_websites.sh failed:\n{result.stdout}\n{result.stderr}"
    return out_root


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_every_device_gets_its_own_site_from_its_generated_definitions(built_root: Path, device: str) -> None:
    frozen = built_root / device / "frozen_html.py"
    assert frozen.is_file(), f"no site built for {device} at {frozen}"
    assert _inlined_device_id(frozen) == device


def test_only_derived_devices_are_built(built_root: Path) -> None:
    assert sorted(p.name for p in built_root.iterdir()) == sorted(DEVICE_NAMES)


def test_the_inlined_reader_bites(tmp_path: Path) -> None:
    # The id check must read the served page, not agree with anything: a page naming another id fails.
    page = gzip.compress(b'<head><script type="application/json" id="inlined-definitions">{"device": {"id": "other"}}</script></head>')
    module = tmp_path / "frozen_html.py"
    module.write_text(f"_f0 = const({page!r})\n_files = (\n ( '/index.html.gz',  ( _f0, False, {len(page)} ) ),\n)\n")
    assert _inlined_device_id(module) == "other"
