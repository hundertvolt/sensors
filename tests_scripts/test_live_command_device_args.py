"""The live website commands boot the device they are given, in a config directory of their own: every exported
command that starts a twin takes a `device` argument and hands it, with its makeConfigDir() directory, to
tests_js/_twin_process.js's spawnTwin() (SPECIFICATION.md Part H.7). Read as text: the modules run under Node."""

import re
from pathlib import Path

import pytest
from _devices import DEVICE_NAMES

_REPO_ROOT = Path(__file__).resolve().parent.parent
_LAUNCH = "tests_js/_twin_process.js"
_MODULES = ("tests_js/_live_twin_command.js", "tests_js/_live_matrix_command.js")
_SMOKE = "scripts/cross_browser_smoke.mjs"
_IN_MEMORY_STATE = ("--fram-state-path", "--scd30-state-path", "--mem-backup-state-path")

_EXPORTED = re.compile(r"^export (?:async )?function (\w+)\(([^)]*)\)", re.MULTILINE)
_SPAWN_DEF = re.compile(r"^export function spawnTwin\(\{([^}]*)\}\)", re.MULTILINE)
_SITE_ENTRY = "build/generated_html/${device}"


def _bodies(text: str) -> "dict[str, tuple[str, str]]":
    # Exported function name -> (parameter text, body text up to the next top-level definition).
    starts = [(m.start(), m.group(1), m.group(2)) for m in _EXPORTED.finditer(text)]
    out: dict[str, tuple[str, str]] = {}
    for index, (start, name, params) in enumerate(starts):
        end = starts[index + 1][0] if index + 1 < len(starts) else len(text)
        out[name] = (params, text[start:end])
    return out


def _command_problems(path: str, text: str) -> "list[str]":
    # Every exported command that boots a twin takes a required device and hands it to the launch.
    problems: list[str] = []
    booting = {name: entry for name, entry in _bodies(text).items() if "spawnTwin(" in entry[1]}
    if not booting:
        problems.append(f"{path}: no exported command boots a twin - the check found nothing to hold")
    for name, (params, body) in booting.items():
        names = [p.split("=")[0].strip() for p in params.split(",")]
        if "device" not in names or "=" in params.split("device", 1)[1].split(",")[0]:
            problems.append(f"{path}: {name}({params}) must take a required `device` argument")
        if not re.search(r"spawnTwin\(\{\s*device\b", body):
            problems.append(f"{path}: {name}() does not pass its device to spawnTwin()")
        if "configDir" not in body:
            problems.append(f"{path}: {name}() boots a twin without its own config directory")
    if re.search(r"^(?:export )?(?:async )?function spawnTwin\(", text, re.MULTILINE):
        problems.append(f"{path}: defines its own spawnTwin() - the launch lives in {_LAUNCH} alone")
    return problems + _config_dir_problems(path, text) + _device_literals(path, text)


def _config_dir_problems(path: str, text: str) -> "list[str]":
    # No command clears a shared directory: each boots in its own makeConfigDir() directory and removes only that.
    problems = [f"{path}: calls rmSync() - a command removes only its own config directory, through removeConfigDir()" for _ in re.finditer(r"\brmSync\(", text)]
    if "digital_twin/config" in text or '"digital_twin", "config"' in text:
        problems.append(f"{path}: names digital_twin/config, the manual run's directory no command touches")
    if "spawnTwin(" in text and "makeConfigDir()" not in text:
        problems.append(f"{path}: boots a twin without a makeConfigDir() directory of its own")
    return problems


def _device_literals(path: str, text: str) -> "list[str]":
    literals = [literal for device in DEVICE_NAMES for literal in (f'"{device}"', f"'{device}'", f"`{device}`", f"sensortask_{device}")]
    problems = [f"{path}: names the device {literal} - the device must come from the argument" for literal in literals if literal in text]
    if "frozen_modules" in text:
        problems.append(f"{path}: still names frozen_modules - a twin must serve its own device's site")
    return problems


def _launch_problems(path: str, text: str) -> "list[str]":
    # The one twin launch: spawnTwin({device, port}) with no default device, everything per device built from it.
    spawn_def = _SPAWN_DEF.search(text)
    if spawn_def is None:
        return [f"{path}: no exported spawnTwin({{...}}) definition - the twin launch moved, re-point this check"]
    params = [p.split("=")[0].strip() for p in spawn_def.group(1).split(",")]
    problems: list[str] = []
    if "device" not in params or re.search(r"\bdevice\s*=", spawn_def.group(1)):
        problems.append(f"{path}: spawnTwin({{{spawn_def.group(1)}}}) must take a required `device`, with no default")
    spawn_body = text[spawn_def.start() : text.find("\n}\n", spawn_def.start())]
    needles = ("`sensortask_${device}`", "`sensortask_${device}_wiring_plan.json`", _SITE_ENTRY)
    problems += [f"{path}: spawnTwin() does not build {needle} from its device argument" for needle in needles if needle not in spawn_body]
    if not re.search(r'"--device",\s*device,', spawn_body):
        problems.append(f"{path}: spawnTwin() does not pass `--device device`")
    return problems + _state_problems(path, spawn_def.group(1), spawn_body) + _device_literals(path, text)


def _state_problems(path: str, params_text: str, spawn_body: str) -> "list[str]":
    # The launch's state: the caller's config directory, required, and every other state path in memory.
    params = [p.split("=")[0].strip() for p in params_text.split(",")]
    problems: list[str] = []
    if "configDir" not in params or re.search(r"\bconfigDir\s*=", params_text):
        problems.append(f"{path}: spawnTwin({{{params_text}}}) must take a required `configDir`, with no default")
    if not re.search(r'"--config-dir",\s*configDir,', spawn_body):
        problems.append(f"{path}: spawnTwin() does not pass `--config-dir configDir`")
    problems += [f'{path}: spawnTwin() does not pass `{flag} ""` (in memory)' for flag in _IN_MEMORY_STATE if not re.search(rf'"{flag}",\s*"",', spawn_body)]
    return problems


def test_the_one_launch_builds_everything_from_its_device() -> None:
    problems = _launch_problems(_LAUNCH, (_REPO_ROOT / _LAUNCH).read_text(encoding="utf-8"))
    assert not problems, "\n".join(problems)


@pytest.mark.parametrize("module", _MODULES)
def test_every_booting_command_takes_and_passes_its_device(module: str) -> None:
    problems = _command_problems(module, (_REPO_ROOT / module).read_text(encoding="utf-8"))
    assert not problems, "\n".join(problems)


def test_the_smoke_boots_in_its_own_config_directory_with_in_memory_state() -> None:
    text = (_REPO_ROOT / _SMOKE).read_text(encoding="utf-8")
    problems = _config_dir_problems(_SMOKE, text)
    problems += [f'{_SMOKE}: its twin launch does not pass `{flag} ""`' for flag in _IN_MEMORY_STATE if not re.search(rf'"{flag}",\s*"",', text)]
    if not re.search(r'"--config-dir",\s*configDir,', text):
        problems.append(f"{_SMOKE}: its twin launch does not pass `--config-dir configDir`")
    assert not problems, "\n".join(problems)


def test_the_ceiling_reader_has_no_default_device() -> None:
    text = (_REPO_ROOT / "tests_js" / "_live_twin_command.js").read_text(encoding="utf-8")
    match = re.search(r"^export function configuredMaxConnections\(([^)]*)\)", text, re.MULTILINE)
    assert match is not None, "configuredMaxConnections() is gone from _live_twin_command.js - re-point this check"
    first = match.group(1).split(",")[0]
    assert first.strip() == "device", f"configuredMaxConnections({match.group(1)}) must take a required device first"


_PLANTED_LAUNCH = """export function spawnTwin({ port }) {
    const proc = spawn(BIN, ["--module", "sensortask_<D>", "--device", "<D>"], { env: { MICROPYPATH: "build/generated_src:frozen_modules" } });
}
"""
_PLANTED_COMMAND = """function spawnTwin(device) {
    return device;
}

export async function runLiveBackendSmoke({ context }) {
    rmSync(path.join(REPO_ROOT, "digital_twin", "config"), { recursive: true, force: true });
    const proc = spawnTwin({ port: PORT });
}
"""


def test_a_hard_coded_device_is_caught() -> None:
    # The checks must bite, not just agree with today's modules: the pre-device forms fail on every rule.
    launch = "\n".join(_launch_problems("planted.js", _PLANTED_LAUNCH.replace("<D>", DEVICE_NAMES[0])))
    for expected in ("required `device`", "does not build", "`--device device`", "frozen_modules", f'"{DEVICE_NAMES[0]}"'):
        assert expected in launch, f"{expected!r} not reported:\n{launch}"
    for expected in ("required `configDir`", "`--config-dir configDir`", '`--mem-backup-state-path ""`'):
        assert expected in launch, f"{expected!r} not reported:\n{launch}"
    command = "\n".join(_command_problems("planted.js", _PLANTED_COMMAND))
    for expected in ("required `device` argument", "does not pass its device", "defines its own spawnTwin()", "calls rmSync()", "names digital_twin/config", "without a makeConfigDir()", "without its own config directory"):
        assert expected in command, f"{expected!r} not reported:\n{command}"
