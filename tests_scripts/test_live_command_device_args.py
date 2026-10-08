"""The live website commands boot the device they are given: every exported command that starts a twin
takes a `device` argument and hands it to its module's spawnTwin(), which builds the module, wiring plan
and MICROPYPATH from it alone (SPECIFICATION.md Part H.7). Read as text: the modules run under Node."""

import re
from pathlib import Path

import pytest
from _devices import DEVICE_NAMES

_REPO_ROOT = Path(__file__).resolve().parent.parent
_MODULES = ("tests_js/_live_twin_command.js", "tests_js/_live_matrix_command.js")

_EXPORTED = re.compile(r"^export (?:async )?function (\w+)\(([^)]*)\)", re.MULTILINE)
_SPAWN_DEF = re.compile(r"^function spawnTwin\(([^)]*)\)", re.MULTILINE)
_SITE_ENTRY = "build/generated_html/${device}"


def _bodies(text: str) -> "dict[str, tuple[str, str]]":
    # Exported function name -> (parameter text, body text up to the next top-level definition).
    starts = [(m.start(), m.group(1), m.group(2)) for m in _EXPORTED.finditer(text)]
    out: dict[str, tuple[str, str]] = {}
    for index, (start, name, params) in enumerate(starts):
        end = starts[index + 1][0] if index + 1 < len(starts) else len(text)
        out[name] = (params, text[start:end])
    return out


def _problems(path: str, text: str) -> "list[str]":
    problems: list[str] = []
    spawn_def = _SPAWN_DEF.search(text)
    if spawn_def is None:
        return [f"{path}: no spawnTwin() definition - the twin launch moved, re-point this check"]
    if spawn_def.group(1).strip() != "device":
        problems.append(f"{path}: spawnTwin({spawn_def.group(1)}) must take exactly `device`, with no default")
    spawn_body = text[spawn_def.start():text.find("\n}\n", spawn_def.start())]
    needles = ("`sensortask_${device}`", "`sensortask_${device}_wiring_plan.json`", _SITE_ENTRY)
    problems += [f"{path}: spawnTwin() does not build {needle} from its device argument" for needle in needles if needle not in spawn_body]
    if not re.search(r'"--device",\s*device,', spawn_body):
        problems.append(f"{path}: spawnTwin() does not pass `--device device`")
    booting = {name: entry for name, entry in _bodies(text).items() if "spawnTwin(" in entry[1]}
    if not booting:
        problems.append(f"{path}: no exported command boots a twin - the check found nothing to hold")
    for name, (params, body) in booting.items():
        names = [p.split("=")[0].strip() for p in params.split(",")]
        if "device" not in names or "=" in params.split("device", 1)[1].split(",")[0]:
            problems.append(f"{path}: {name}({params}) must take a required `device` argument")
        if "spawnTwin(device)" not in body:
            problems.append(f"{path}: {name}() does not pass its device to spawnTwin()")
    if "frozen_modules" in text:
        problems.append(f"{path}: still names frozen_modules - a twin must serve its own device's site")
    literals = [literal for device in DEVICE_NAMES for literal in (f'"{device}"', f"'{device}'", f"`{device}`", f"sensortask_{device}")]
    problems += [f"{path}: names the device {literal} - the device must come from the argument" for literal in literals if literal in text]
    return problems


@pytest.mark.parametrize("module", _MODULES)
def test_every_booting_command_takes_and_passes_its_device(module: str) -> None:
    problems = _problems(module, (_REPO_ROOT / module).read_text(encoding="utf-8"))
    assert not problems, "\n".join(problems)


def test_the_ceiling_reader_has_no_default_device() -> None:
    text = (_REPO_ROOT / "tests_js" / "_live_twin_command.js").read_text(encoding="utf-8")
    match = re.search(r"^export function configuredMaxConnections\(([^)]*)\)", text, re.MULTILINE)
    assert match is not None, "configuredMaxConnections() is gone from _live_twin_command.js - re-point this check"
    first = match.group(1).split(",")[0]
    assert first.strip() == "device", f"configuredMaxConnections({match.group(1)}) must take a required device first"


_PLANTED = """function spawnTwin() {
    const proc = spawn(BIN, ["--module", "sensortask_<D>", "--device", "<D>"], { env: { MICROPYPATH: "build/generated_src:frozen_modules" } });
}

export async function runLiveBackendSmoke({ context }) {
    const proc = spawnTwin();
}
"""


def test_a_hard_coded_device_is_caught() -> None:
    # The check must bite, not just agree with today's modules: the pre-device form fails on every rule.
    problems = "\n".join(_problems("planted.js", _PLANTED.replace("<D>", DEVICE_NAMES[0])))
    for expected in ("must take exactly `device`", "does not build", "required `device` argument", "frozen_modules", f'"{DEVICE_NAMES[0]}"'):
        assert expected in problems, f"{expected!r} not reported:\n{problems}"
