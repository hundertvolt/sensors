"""A device that declares no FRAM boots: the first derived device's TOML copied without its FRAM, generated into
tmp_path and booted under the Unix-port binary with the unit fakes. Every log stays in RAM, no store is handed to
the system service, and "Erase FRAM" is refused with no reset armed. FRAM wiring is optional (its @wiring tag)."""

import json
import re
import subprocess
from pathlib import Path

import tomllib
from _devices import DEVICE_NAMES, device_toml

from buildgen.generate import generate_device

_DEVICE = "fixture_device"
# @tunable l0.fram_less_boot_timeout_s = 60
_BOOT_TIMEOUT_S = 60  # one construction and setup list on the Unix port, a few seconds; the bound ends a hang
_STUB_FROZEN_HTML = '"""Test-only stub: the boot serves no static page."""\n'
_FACTS = "FACTS "

# Runs under the Unix-port binary from the repository root: boots the generated module as the scenario libraries
# do, then sends "Erase FRAM" through the real route and prints what it found as one JSON line.
_BOOT = """
import asyncio, json, sys
sys.path.insert(0, "ext")
import machine
import sensortask_%(device)s as generated
from _async_harness import run
from _generated_module import boot_generated
from _strict_json import strict_loads
from microdot import Request

class _Holder:
    def hold(self, closable):
        pass

async def main():
    module, _wdt = await boot_generated(generated, "%(device)s", cfg_path="%(cfg)s", web_host="127.0.0.1", web_port=0)
    stored = []
    for name in dir(module):
        obj = getattr(module, name)
        if hasattr(obj, "get_loggers") and not isinstance(obj, type):
            stored += [logger.name for logger in obj.get_loggers() if getattr(logger, "fram", None) is not None]
    body = json.dumps({"SystemCmd": "erasefram"}).encode()
    headers = {"Content-Length": str(len(body)), "Content-Type": "application/json"}
    app = module.webserver._app
    req = Request(app, ("127.0.0.1", 1), "PUT", "/system", "1.1", headers, body=body, sock=(_Holder(), _Holder()))
    answer = strict_loads((await app.dispatch_request(req)).body)["result"]
    return {
        "fram": getattr(module, "fram", None) is not None,
        "storage": module.sysfunct._storage is not None,
        "stored": stored,
        "erasefram": answer,
        "armed": module.sysfunct._reset_armed,
        "resets": machine.reset_count,
    }

print("%(marker)s" + json.dumps(run(main())))
"""


def _without_fram(text: str) -> str:
    # The [[instance]] table of the FRAM, the SPI bus only it used and every fram_target wiring line, dropped.
    kept = []
    for table in re.split(r"(?m)^(?=\[)", text):
        if table.startswith("[[instance]]") and re.search(r'(?m)^driver = "fram"$', table):
            continue
        if table.startswith("[bus.spi"):
            continue
        kept.append(re.sub(r'(?m)^fram_target = "fram"\n', "", table))
    return "".join(kept)


def _boot(repo_root: Path, micropython_bin: Path, tmp_path: Path, toml_text: str) -> "dict[str, object]":
    (tmp_path / f"{_DEVICE}.toml").write_text(toml_text, encoding="utf-8")
    generated = generate_device(tmp_path / f"{_DEVICE}.toml", repo_root / "src", repo_root / "ext")
    (tmp_path / f"sensortask_{_DEVICE}.py").write_text(generated.module_source, encoding="utf-8")
    (tmp_path / f"sensortask_{_DEVICE}_main.py").write_text(generated.boot_entry_source, encoding="utf-8")
    (tmp_path / "frozen_html.py").write_text(_STUB_FROZEN_HTML, encoding="utf-8")
    (tmp_path / "cfg").mkdir()
    script = tmp_path / "boot.py"
    script.write_text(_BOOT % {"device": _DEVICE, "cfg": tmp_path / "cfg", "marker": _FACTS}, encoding="utf-8")
    env = {"MICROPYPATH": f"{tmp_path}:src:tests:.frozen", "TZ": "UTC", "PATH": "/usr/bin:/bin"}  # .frozen: the port's own asyncio
    result = subprocess.run([str(micropython_bin), "-X", "heapsize=16M", str(script)], cwd=repo_root, env=env, capture_output=True, text=True, timeout=_BOOT_TIMEOUT_S, check=False)
    lines = [line for line in result.stdout.splitlines() if line.startswith(_FACTS)]
    assert result.returncode == 0 and len(lines) == 1, f"rc={result.returncode}\n{result.stdout}\n{result.stderr}"
    facts: dict[str, object] = json.loads(lines[0][len(_FACTS) :])
    return facts


def test_the_fixture_declares_no_fram_at_all() -> None:
    doc = tomllib.loads(_without_fram(device_toml(DEVICE_NAMES[0]).read_text(encoding="utf-8")))
    assert [i["driver"] for i in doc["instance"] if i["driver"] == "fram"] == []
    assert "fram_target" not in json.dumps(doc), "a fram_target wiring survived"


def test_a_device_without_fram_boots_with_every_log_in_ram_and_refuses_erase_fram(repo_root: Path, micropython_bin: Path, tmp_path: Path) -> None:
    facts = _boot(repo_root, micropython_bin, tmp_path, _without_fram(device_toml(DEVICE_NAMES[0]).read_text(encoding="utf-8")))
    assert facts == {"fram": False, "storage": False, "stored": [], "erasefram": {"SystemCmd": "Failed"}, "armed": False, "resets": 0}, facts
