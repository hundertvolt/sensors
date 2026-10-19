"""Shared pytest options, markers and fixtures for tests_hardware/: every fixture skips when its
hardware is absent, so the tier collects with nothing attached under every option
(tests_hardware/README.md)."""

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING, NamedTuple, NoReturn

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))  # tests_hardware/ itself, for `import harness`/`import bench_control`

import bench_facts
import error_log_helpers
import harness
import http_client
import markers
import scd30_prerequisite
from bench_control import BenchBridge
from harness import Board, HardwareNotAvailableError, HardwareTestFailureError, wait_for_boot, wait_until
from soak_durations import SOAK_DURATION_SECONDS
from twin_board import TwinBoard

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator, Sequence

# The standard board state's log level: the most verbose, what every log-based oracle reads at (>= 3).
_STANDARD_DEBUG_LEVEL = 5  # source: src/asy_system_service.py _VAL_DEBUG_LEVEL maximum, pinned by a tests_scripts check
# Whether the session start saved /status over REST, so dut_ip saves it once the address is known otherwise.
_REST_SAVED = pytest.StashKey[bool]()
_BENCH_DEVICE_BEFORE = pytest.StashKey["str | None"]()

# @tunable l4.hotspot_role_reversal_hotspot_scan_timeout_s = 30.0
_HOTSPOT_SCAN_TIMEOUT_S = 30.0
# @tunable l4.hotspot_role_reversal_hotspot_scan_poll_s = 2.0
_HOTSPOT_SCAN_POLL_S = 2.0
# @tunable l4.hotspot_role_reversal_join_hotspot_timeout_s = 45.0
_JOIN_HOTSPOT_TIMEOUT_S = 45.0
# @tunable l4.conftest_provision_put_timeout_s = 10.0
_PROVISION_PUT_TIMEOUT_S = 10.0
# @tunable l4.conftest_dut_ip_exec_timeout_s = 15.0
_DUT_IP_EXEC_TIMEOUT_S = 15.0
# @tunable l4.conftest_http_ready_probe_timeout_s = 5.0
_HTTP_READY_PROBE_TIMEOUT_S = 5.0
# @tunable l4.conftest_http_ready_poll_s = 2.0
_HTTP_READY_POLL_S = 2.0
# @tunable l4.conftest_ip_and_http_timeout_s = 60.0
_IP_AND_HTTP_TIMEOUT_S = 60.0
# @tunable l4.dut_serving_after_sta_s = 30.0
_DUT_SERVING_AFTER_STA_S = 30.0
# @tunable l4.conftest_sta_tail_step_s = 2.0
_STA_TAIL_STEP_S = 2.0
# @tunable l4.conftest_vl805_read_timeout_s = 20.0
_VL805_READ_TIMEOUT_S = 20.0
# @tunable l4.conftest_end_present_timeout_s = 15.0
_END_PRESENT_TIMEOUT_S = 15.0
# @tunable l4.conftest_end_boot_timeout_s = 30.0
_END_BOOT_TIMEOUT_S = 30.0

# The VL805 USB-controller firmware from which the bench Pi 4 no longer hangs the RP2040's USB device (RP2040-E15).
_VL805_E15_FIXED = 0x000138C1
_SCD30_SNAPSHOT = ("MeasInterval", "AmbPres", "TempOffset", "Altitude", "SelfCal")
_SCRATCH_PREFIX, _SCRATCH_DIR = "config_HWTEST_", "hwtest-scratch"
_REPAIRED = "--repair-standard-state repairs it (a listed prerequisite write)"
_REFLASH = "manual step: reflash the round's standard image (built by scripts/build_firmware.py)"
_RESTORE_SCD30 = "manual step: the PUT /sensors that restores it (spends SCD30 NVM writes)"
_DEBUG_LEVEL_SCRIPT = harness.DEVICE_SCRIPTS_DIR / "system_debug_level_set_standard.py"
# Read-only: the log level the production config holds and the root's names (a scratch file or directory).
_BOARD_STATE_EXEC = (
    "import json, os\ntry:\n  print('LEVEL=' + str(json.load(open('config_SYSTEM.cfg')).get('DebugLevel')))\n"
    "except OSError:\n  print('LEVEL=absent')\nprint('FILES=' + json.dumps(os.listdir()))"
)


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption("--device", default=None, help="Serial device path for the flash-tier board (default: $MPREMOTE_DEVICE, else the board's stable /dev/serial/by-id symlink - see harness.resolve_board_device())")
    parser.addoption("--bench-device", default=None, metavar="NAME", help="the board on the bench; default $BENCH_DEVICE, else the one devices/*.toml with [device].bench = true")
    parser.addoption("--image-record", default=None, metavar="PATH", help="the image record of the build on the board (default build/firmware-<bench device>.json, beside its .uf2)")
    parser.addoption("--dut-ip", default=None, metavar="ADDR", help="the DUT's last known address on the bench network; lets the session save /status before anything resets the board")
    parser.addoption("--lwip-control-image", default=None, metavar="PATH", help="the unpatched control image a phase-C round built in a throwaway worktree; required by the unpatched lwIP test, never defaulted")
    parser.addoption("--rollover-image", default=None, metavar="PATH", help="the tick-offset test image the rollover round built; required by the rollover test, never defaulted")
    parser.addoption("--twin", action="store_true", default=False, help="run flash-tier tests and device scripts against the Unix-port twin instead of a board")
    durations = ", ".join(f"{name}={seconds:.0f} s" for name, seconds in SOAK_DURATION_SECONDS.items())
    parser.addoption("--soak-duration", choices=sorted(SOAK_DURATION_SECONDS), default=None, help=f"run the soak_duration tests for one named duration ({durations}); scripts/run_bench_soak_tests.sh passes it")
    parser.addoption("--allow-flash-cycle", action="store_true", default=False, help="one or more reflashes owned by the test (flash wear)")
    parser.addoption("--allow-multi-day-rollover", action="store_true", default=False, help="the tick-rollover observation on the tick-offset test image, about 2 h; no write of its own")
    parser.addoption("--allow-neopixel-sweep", action="store_true", default=False, help="~10 minutes of light programs on the NeoPixel-to-ISL29125 rig recorded by the manual tier; no write of its own, its config pushes need --allow-persistence-write")
    parser.addoption("--allow-persistence-write", action="store_true", default=False, help="the owned flash-filesystem and SCD30 NVM writes listed in tests_hardware/README.md's budget table; shared prerequisite writes run without it")
    parser.addoption("--allow-scd30-extra-write", action="store_true", default=False, help="on top of --allow-persistence-write: the further SCD30 NVM writes the budget table lists under scd30_extra_write")
    parser.addoption("--allow-toolchain-reverify", action="store_true", default=False, help="a full toolchain re-verification: network fetches and ~8 min of builds; no board write")
    parser.addoption("--repair-standard-state", action="store_true", default=False, help="repair a board found outside the standard state; each repair is a listed prerequisite write")


def pytest_configure(config: pytest.Config) -> None:
    markers.register(config)
    # The bench board by name: every default-taking harness helper reads $BENCH_DEVICE, so the option is exported for
    # this session and the previous value restored at its end (an in-process pytest.main() loop must not inherit it).
    chosen = config.getoption("--bench-device") or os.environ.get("BENCH_DEVICE")
    if chosen and not (harness.DEVICES_DIR / f"{chosen}.toml").is_file():
        raise pytest.UsageError(f"--bench-device/$BENCH_DEVICE names {chosen!r}, but there is no devices/{chosen}.toml")
    config.stash[_BENCH_DEVICE_BEFORE] = os.environ.get("BENCH_DEVICE")
    if chosen:
        os.environ["BENCH_DEVICE"] = chosen


def pytest_unconfigure(config: pytest.Config) -> None:
    if _BENCH_DEVICE_BEFORE not in config.stash:  # configure refused the option before exporting anything
        return
    before = config.stash[_BENCH_DEVICE_BEFORE]
    if before is None:
        os.environ.pop("BENCH_DEVICE", None)
    else:
        os.environ["BENCH_DEVICE"] = before


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    # The wear gates deselect rather than skip, so a run reports its deselected count; each item is
    # tagged with the flag that would select it, which tells it apart from a runner's -m exclusion.
    # Only these two options are read at collection: everything else a fixture reads at run time.
    allow_writes = config.getoption("--allow-persistence-write")
    allow_extra_write = config.getoption("--allow-scd30-extra-write")
    kept: list[pytest.Item] = []
    deselected: list[pytest.Item] = []
    for item in items:
        lacks_write_permission = item.get_closest_marker("persistence_write") is not None and not allow_writes
        lacks_extra_write_permission = item.get_closest_marker("scd30_extra_write") is not None and not allow_extra_write
        if lacks_write_permission:
            item.user_properties.append(("deselected_by", "--allow-persistence-write"))
            deselected.append(item)
        elif lacks_extra_write_permission:
            item.user_properties.append(("deselected_by", "--allow-scd30-extra-write"))
            deselected.append(item)
        else:
            kept.append(item)
    if deselected:
        config.hook.pytest_deselected(items=deselected)
    # destructive_last: within its module a marked test runs after the others, the order otherwise kept.
    module_order: dict[str, int] = {}
    for item in kept:
        module_order.setdefault(item.nodeid.split("::", 1)[0], len(module_order))
    items[:] = sorted(kept, key=lambda item: (module_order[item.nodeid.split("::", 1)[0]], item.get_closest_marker("destructive_last") is not None))


@pytest.fixture
def result_note(request: pytest.FixtureRequest) -> "Callable[..., None]":
    # A note on the test's own report, which the run record keeps for a passing test too (a print
    # is dropped by capture). recovery=True marks a pass that needed a recovery step.
    def _note(text: str, *, recovery: bool = False) -> None:
        request.node.user_properties.append(("recovery" if recovery else "result_note", text))

    return _note


def record_session_note(config: pytest.Config, text: str, *, recovery: bool = False, source: str) -> None:
    # For session-scoped fixtures, which have no test report: the run-record plugin keeps the note
    # under session_notes. Without it the note is printed past output capture, never dropped.
    plugin = config.pluginmanager.get_plugin("_pytest_run_record")
    if plugin is not None:
        plugin.add_session_note(config, text, recovery=recovery, source=source)
        return
    line = f"{'RECOVERY' if recovery else 'NOTE'} ({source}): {text}"
    capture = config.pluginmanager.get_plugin("capturemanager")
    if capture is None:
        print(line)
        return
    with capture.global_and_fixture_disabled():
        print(line)


def report_to_console(config: pytest.Config, message: str) -> None:
    # Through the terminal reporter, so neither output capture nor -q can hide it.
    reporter = config.pluginmanager.get_plugin("terminalreporter")
    if reporter is None:
        print(message)
        return
    for line in message.splitlines():
        reporter.write_line(line)


@pytest.fixture(scope="session")
def session_note(request: pytest.FixtureRequest) -> "Callable[..., None]":
    # record_session_note() bound to this session, for a subdirectory's conftest (it cannot import this module).
    def _note(text: str, *, recovery: bool = False, source: str) -> None:
        record_session_note(request.config, text, recovery=recovery, source=source)

    return _note


@pytest.fixture(scope="session")
def bench_device_name() -> str:
    # pytest_configure() exported --bench-device as $BENCH_DEVICE, so the harness's own resolution is the one answer.
    return harness.bench_device()


@pytest.fixture(scope="session")
def board(request: pytest.FixtureRequest) -> "Iterator[Board | TwinBoard]":
    if request.config.getoption("--twin"):
        # A missing Unix-port build fails the twin's first run, never skips it - the run asked for the twin.
        yield TwinBoard()
        return
    b = Board(device=request.config.getoption("--device"))
    # The passive presence check first: with no serial node there is nothing to start mpremote against.
    if not (b.is_device_present() and b.is_reachable()):
        pytest.skip(
            f"no real board reachable at {b.device} - this fixture only runs against real hardware "
            "(see tests_hardware/README.md for provisioning). Not a failure: this tier is meant to "
            "be collectible with nothing attached.",
        )
    yield b


@pytest.fixture(scope="session")
def bench(board: Board, request: pytest.FixtureRequest) -> BenchBridge:
    # Depends on `board` - a bench test needs both the real board over USB and the real WiFi bridge.
    if request.config.getoption("--twin"):
        pytest.skip("the twin has no bench bridge")
    bridge = BenchBridge()
    if not bridge.is_configured():
        pytest.skip(
            "no bench WiFi bridge configured (br0-wifi-ap missing) - run "
            "`uv run toolchain/setup_toolchain.py env --tier bench` first (see tests_hardware/README.md).",
        )
    for removed in bridge.clear_leftovers():  # a killed earlier run's network state, each removal reported
        record_session_note(request.config, f"removed a leftover: {removed}", source="bench.clear_leftovers")
    return bridge


class Deviation(NamedTuple):
    # One way the board differs from the standard state: what was read, what the state holds, how it is restored.
    name: str
    read: str
    standard: str
    remedy: str


def standard_state_message(deviations: "Sequence[tuple[str, str, str, str]]") -> str:
    lines = ["board not in the standard state:"]
    lines += [f"  - {d.name}: read {d.read}, the standard state holds {d.standard} - {d.remedy}" for d in map(Deviation._make, deviations)]
    return "\n".join(lines)


def exit_on_deviations(config: pytest.Config, deviations: "Sequence[tuple[str, str, str, str]]") -> NoReturn:
    # One console message through the terminal reporter (output capture and -q cannot hide it), then the failed start.
    message = standard_state_message(deviations)
    report_to_console(config, message)
    pytest.exit(message, returncode=1)


@pytest.fixture(scope="session")
def standard_state_exit(request: pytest.FixtureRequest) -> "Callable[[Sequence[tuple[str, str, str, str]]], NoReturn]":
    # exit_on_deviations() bound to this session, for a subdirectory's conftest (bench/conftest.py's image check).
    def _exit(deviations: "Sequence[tuple[str, str, str, str]]") -> NoReturn:
        exit_on_deviations(request.config, deviations)

    return _exit


def parse_board_state(output: str) -> "tuple[int | None, list[str]]":
    # The read-only exec's two lines: the production DebugLevel (None when the file or the key is absent) and the
    # root's names. Anything else is a changed exec or a board that did not run it, never a guess.
    level_lines = [line[len("LEVEL=") :].strip() for line in output.splitlines() if line.startswith("LEVEL=")]
    file_lines = [line[len("FILES=") :].strip() for line in output.splitlines() if line.startswith("FILES=")]
    if len(level_lines) != 1 or len(file_lines) != 1:
        raise HardwareTestFailureError(f"the board-state exec printed no single LEVEL= and FILES= line:\n{output}")
    files = json.loads(file_lines[0])
    if not isinstance(files, list) or not all(isinstance(name, str) for name in files):
        raise HardwareTestFailureError(f"the board-state exec's FILES= is no list of names: {file_lines[0]!r}")
    level = int(level_lines[0]) if re.fullmatch(r"-?\d+", level_lines[0]) else None
    return level, files


def board_state_deviations(level: "int | None", files: "list[str]", write_protected: object) -> "list[Deviation]":
    found: list[Deviation] = []
    if level != _STANDARD_DEBUG_LEVEL:
        found.append(Deviation("DebugLevel", "absent" if level is None else str(level), str(_STANDARD_DEBUG_LEVEL), _REPAIRED))
    if write_protected is not False:
        found.append(Deviation("FRAM write-protect", "set" if write_protected is True else f"unread ({write_protected!r})", "clear", _REPAIRED))
    scratch = sorted(name for name in files if name.startswith(_SCRATCH_PREFIX) or name == _SCRATCH_DIR)
    if scratch:
        found.append(Deviation("scratch files", ", ".join(scratch), "none", _REPAIRED))
    return found


def scd30_deviations(start: "dict[str, object]", end: "dict[str, object]") -> "list[Deviation]":
    # A test that changed an SCD30 value and did not restore it: the end differs from the session start.
    return [Deviation(f"SCD30 {key}", repr(end.get(key)), repr(start.get(key)), _RESTORE_SCD30) for key in sorted(set(start) | set(end)) if start.get(key) != end.get(key)]


def session_start_evidence(config: pytest.Config, board: "Board", dut_ip: "str | None") -> "harness.FramDump":
    # Evidence before anything clears it: /status over REST first when the DUT answers at --dut-ip (the in-RAM
    # ResetReason a raw-REPL entry would end), then the read-only raw FRAM dump, then the reset the dump needs.
    saved = False
    if dut_ip:
        try:
            error_log_helpers.save_errcount(dut_ip, "session-start")
            saved = True
        except (OSError, AssertionError, http_client.HTTP_ERROR) as exc:
            record_session_note(config, f"pre-session /status not saved: --dut-ip {dut_ip} did not answer ({exc})", source="fram_evidence_saved")
    else:
        record_session_note(config, "pre-session /status not saved: no reachable --dut-ip", source="fram_evidence_saved")
    config.stash[_REST_SAVED] = saved
    dump = harness.save_fram_raw(board, "session-start")
    board.hard_reset()
    return dump


def _board_if_present(request: pytest.FixtureRequest) -> "Board | None":
    # The autouse session fixtures act only on a real board: without one, each test's own `board` request skips it.
    if request.config.getoption("--twin"):
        return None
    try:
        board: Board = request.getfixturevalue("board")
    except pytest.skip.Exception:
        return None
    return board


@pytest.fixture(scope="session", autouse=True)
def fram_evidence_saved(request: pytest.FixtureRequest) -> "harness.FramDump | None":
    board = _board_if_present(request)
    if board is None:
        return None
    return session_start_evidence(request.config, board, request.config.getoption("--dut-ip"))


def _get_json(dut_ip: str, path: str) -> "dict[str, object]":
    # One strict GET: a 200 whose body is a JSON object.
    res = http_client.fetch(dut_ip, 80, "GET", path, timeout_s=_HTTP_READY_PROBE_TIMEOUT_S)
    try:
        body = res.json() if res.status_code == 200 else None
    except (ValueError, TypeError):  # no JSON, or a JSON value other than an object
        body = None
    if not isinstance(body, dict):
        raise HardwareTestFailureError(f"GET {path} gave no JSON object: {res.status_code} {res.body!r}")
    return dict(body)


def _result_words(res: "http_client.HttpResponse") -> "dict[str, object]":
    # A PUT's per-field result words ({"result": {...}}), empty when the answer carries none.
    try:
        result = res.json().get("result") if res.status_code == 200 else None
    except (ValueError, TypeError):
        result = None
    return dict(result) if isinstance(result, dict) else {}


def _board_state(board: "Board", bench: "BenchBridge | None", dut_ip: "str | None") -> "tuple[int | None, list[str]]":
    # The read-only exec stops main.py, so the board is reset (with a bench: back to serving) after it.
    output = board.exec(_BOARD_STATE_EXEC, timeout_s=_DUT_IP_EXEC_TIMEOUT_S)
    if bench is not None and dut_ip is not None:
        harness.restore_board_to_serving(board, bench, dut_ip)
    else:
        board.hard_reset()
    level, files = parse_board_state(output)
    if dut_ip is not None:  # with a bench the running system's own answer is the reading
        rest_level = _get_json(dut_ip, "/system").get("DebugLevel")
        level = rest_level if isinstance(rest_level, int) and not isinstance(rest_level, bool) else None
    return level, files


def _bench_instances(driver: str) -> "dict[str, dict[str, bench_facts.Fact]]":
    # The bench board's instances of one driver by label, from its device TOML through bench_facts, never a literal.
    instances = bench_facts.build(harness.bench_device())["instances"]
    if not isinstance(instances, dict):
        raise HardwareNotAvailableError(f"the bench facts of {harness.device_toml()} carry no instance table")
    return {label: spec for label, spec in instances.items() if isinstance(spec, dict) and spec.get("driver") == driver}


def _scd30_snapshot(board: "Board", dut_ip: "str | None") -> "dict[str, object]":
    # Over REST the configured values of every SCD30 instance; without a bench what the read-only interval script yields.
    if dut_ip is not None:
        body = _get_json(dut_ip, "/sensors")
        snapshot: dict[str, object] = {}
        for label in sorted(_bench_instances("scd30")):
            values = body.get(label)
            if not isinstance(values, dict):
                raise HardwareTestFailureError(f"GET /sensors carries no {label} object: {values!r}")
            snapshot.update({f"{label}.{key}": values.get(key) for key in _SCD30_SNAPSHOT})
        return snapshot
    facts = scd30_prerequisite.interval_facts(board)
    board.hard_reset()
    return {f"interval read {key}": value for key, value in facts.items()}


def _repair(config: pytest.Config, board: "Board", bench: "BenchBridge | None", dut_ip: "str | None", deviations: "list[Deviation]") -> None:
    # Each repair a pinned prerequisite write, reported as a session note; the board is serving again afterwards.
    names = {d.name for d in deviations}
    if "DebugLevel" in names:
        if dut_ip is not None:
            res = http_client.fetch(dut_ip, 80, "PUT", "/system", {"DebugLevel": _STANDARD_DEBUG_LEVEL}, timeout_s=_PROVISION_PUT_TIMEOUT_S)
            if _result_words(res).get("DebugLevel") not in ("Valid", "Unchanged"):
                raise HardwareTestFailureError(f"PUT /system DebugLevel {_STANDARD_DEBUG_LEVEL} was refused: {res.status_code} {res.body!r}")
        else:
            facts = harness.parse_facts(board.run_isolated(_DEBUG_LEVEL_SCRIPT, standard_debug_level=_STANDARD_DEBUG_LEVEL))
            board.hard_reset()
            if facts.get("written") is not True and facts.get("before") != _STANDARD_DEBUG_LEVEL:
                raise HardwareTestFailureError(f"{_DEBUG_LEVEL_SCRIPT.name} did not set DebugLevel {_STANDARD_DEBUG_LEVEL}: {facts}")
        record_session_note(config, f"repaired DebugLevel to {_STANDARD_DEBUG_LEVEL} (one flash write)", recovery=True, source="standard_state")
    if "FRAM write-protect" in names:
        output = board.exec(_clear_write_protect_exec(), timeout_s=_DUT_IP_EXEC_TIMEOUT_S)
        if "WP_CLEARED=True" not in output:
            raise HardwareTestFailureError(f"clearing the FRAM write-protect failed:\n{output}")
        record_session_note(config, "repaired the FRAM write-protect (status register write)", recovery=True, source="standard_state")
    if "scratch files" in names:
        output = board.exec(_REMOVE_SCRATCH_EXEC, timeout_s=_DUT_IP_EXEC_TIMEOUT_S)
        if "SCRATCH_REMOVED" not in output:
            raise HardwareTestFailureError(f"removing the scratch files failed:\n{output}")
        record_session_note(config, "removed the scratch config files (flash writes)", recovery=True, source="standard_state")
    if bench is not None and dut_ip is not None:
        harness.restore_board_to_serving(board, bench, dut_ip)
    else:
        board.hard_reset()


# The scratch the hardware tests may leave: config_HWTEST_* files and the hwtest-scratch directory, removed whole.
_REMOVE_SCRATCH_EXEC = (
    "import os\ndef rm(p):\n  try:\n    names = os.listdir(p)\n  except OSError:\n    os.remove(p)\n    return\n"
    "  for n in names:\n    rm(p + '/' + n)\n  os.rmdir(p)\n"
    f"for n in os.listdir():\n  if n.startswith('{_SCRATCH_PREFIX}') or n == '{_SCRATCH_DIR}':\n    rm(n)\nprint('SCRATCH_REMOVED')"
)


def _clear_write_protect_exec() -> str:
    # The bench board's FRAM through the product driver, its pins from the device TOML; one status-register write.
    facts = bench_facts.build(harness.bench_device())
    chips, buses = list(_bench_instances("fram").values()), facts["bus"]
    bus = buses.get(str(chips[0].get("bus"))) if chips and isinstance(buses, dict) else None
    if not isinstance(bus, dict):
        raise HardwareNotAvailableError(f"{harness.device_toml()} wires no FRAM on a declared bus, so no write-protect to clear")
    chip = chips[0]
    return (
        "import asyncio, asy_spi_driver\nfrom asy_fram_driver import FRAM_SPI\nfrom asy_print_log import PrintLogHistory\n"
        f"spi = asy_spi_driver.SPI({bus['id']}, sck_pin={bus['sck_pin']}, mosi_pin={bus['mosi_pin']}, miso_pin={bus['miso_pin']})\n"
        f"fram = FRAM_SPI(spi, {chip['cs_pin']}, logger=PrintLogHistory(name='FRAMWP'), max_size={facts['fram_max_size']})\n"
        "async def main():\n  await fram.setup()\n  print('WP_CLEARED=' + str(await fram.set_write_protected(value=False)))\n"
        "asyncio.run(main())"
    )


def _vl805_note(config: pytest.Config) -> None:
    # The bench Pi 4's VL805 firmware, read-only; an old one gets a console warning, never a failed session
    # (the firmware carries TinyUSB's RP2040-E15 workaround).
    try:
        done = subprocess.run(["rpi-eeprom-update"], capture_output=True, text=True, timeout=_VL805_READ_TIMEOUT_S, check=False)  # the bench host's own tool, on PATH
    except (OSError, subprocess.TimeoutExpired) as exc:
        record_session_note(config, f"vl805_firmware: not read ({exc})", source="standard_state")
        return
    match = re.search(r"VL805_FW:.*?CURRENT:\s*([0-9a-fA-F]+)", done.stdout, re.DOTALL)
    if match is None:
        record_session_note(config, f"vl805_firmware: not read (no VL805 CURRENT line, exit {done.returncode})", source="standard_state")
        return
    version = int(match.group(1), 16)
    record_session_note(config, f"vl805_firmware: {match.group(1)}", source="standard_state")
    if version < _VL805_E15_FIXED:
        report_to_console(config, f"warning: the bench host's VL805 firmware {match.group(1)} predates {_VL805_E15_FIXED:08x}, which can hang the RP2040's USB device (RP2040-E15) - update it: sudo rpi-eeprom-update -a")


@pytest.fixture(scope="session", autouse=True)
def standard_state(request: pytest.FixtureRequest, fram_evidence_saved: "harness.FramDump | None") -> "Iterator[None]":
    # DebugLevel 5, FRAM write-protect clear, no scratch files and the SCD30 snapshot - at the session start and end,
    # over REST when a bench is configured. A deviation is reported, then repaired on request or fails the start.
    config = request.config
    if config.getoption("--twin"):
        record_session_note(config, "twin run: the twin's board starts fresh, nothing to check", source="standard_state")
    board = _board_if_present(request)
    if board is None:
        yield
        return
    bench = request.getfixturevalue("bench") if BenchBridge().is_configured() else None
    dut_ip: str | None = request.getfixturevalue("dut_ip") if bench is not None else None
    if bench is not None:
        _vl805_note(config)
    level, files = _board_state(board, bench, dut_ip)
    deviations = board_state_deviations(level, files, fram_evidence_saved.facts.get("write_protected") if fram_evidence_saved else None)
    if deviations and not config.getoption("--repair-standard-state"):
        exit_on_deviations(config, deviations)
    if deviations:
        report_to_console(config, standard_state_message(deviations))
        _repair(config, board, bench, dut_ip, deviations)
        # A repair that reported success is read back like the start was, so a write that did not take still fails.
        dump = harness.save_fram_raw(board, "after-repair")
        level, files = _board_state(board, bench, dut_ip)
        remaining = board_state_deviations(level, files, dump.facts.get("write_protected"))
        if remaining:
            exit_on_deviations(config, remaining)
    start = _scd30_snapshot(board, dut_ip)
    yield
    if dut_ip is not None:
        error_log_helpers.save_errcount(dut_ip, "session-end")
    end = _scd30_snapshot(board, dut_ip)
    level, files = _board_state(board, bench, dut_ip)
    dump = harness.save_fram_raw(board, "session-end")
    if bench is not None and dut_ip is not None:
        harness.restore_board_to_serving(board, bench, dut_ip)
    else:  # the last step on the board, after the flash tier's own serving check: it proves the boot again
        board.hard_reset()
        wait_until(board.is_device_present, timeout_s=_END_PRESENT_TIMEOUT_S, description="board back on USB after the session-end reset")
        wait_for_boot(board, _END_BOOT_TIMEOUT_S)
    deviations = board_state_deviations(level, files, dump.facts.get("write_protected")) + scd30_deviations(start, end)
    if deviations:
        report_to_console(config, standard_state_message(deviations))
        raise HardwareTestFailureError(standard_state_message(deviations))


@pytest.fixture(scope="session", autouse=True)
def report_recovery_events(request: pytest.FixtureRequest) -> "Iterator[None]":
    # Every mpremote recovery the harness made this session reaches the run record as a recovery note.
    board = _board_if_present(request)
    yield
    for event in board.recovery_events if board is not None else []:
        record_session_note(request.config, event, recovery=True, source="mpremote")


def _recover_stale_dut_credentials(bench: BenchBridge, note: "Callable[..., None]") -> None:
    # Last-resort recovery for dut_ip(): the DUT's own hotspot is joined and the bench AP's current credentials PUT to
    # it. The single radio scans only with the AP down, so the AP goes down first; every path restores the bridge.
    ssid, password = bench.ap_ssid(), bench.ap_password()
    candidates = harness.dut_hostname_candidates()  # the hotspot SSID is the Hostname: the TOML's, or the schema default
    note("stale-credential recovery: one PUT /networking (flash write, pinned prerequisite)", recovery=True)
    bench.ap_down()
    try:
        found: list[str] = []

        def _any_candidate_visible() -> bool:
            found[:] = [name for name in candidates if bench.is_ssid_visible(name)][:1]
            return bool(found)

        wait_until(_any_candidate_visible, timeout_s=_HOTSPOT_SCAN_TIMEOUT_S, poll_interval_s=_HOTSPOT_SCAN_POLL_S, description=f"the DUT's own hotspot (one of {list(candidates)}) scannable with the bench AP down")
        bench.join_dut_hotspot(found[0], harness.hotspot_password(), timeout_s=_JOIN_HOTSPOT_TIMEOUT_S)
        res = http_client.fetch(bench.gateway_ip(), 80, "PUT", "/networking", {"SSID": ssid, "PW": password}, timeout_s=_PROVISION_PUT_TIMEOUT_S)
        if res.status_code != 200:
            raise HardwareTestFailureError(f"PUT /networking during stale-credential recovery failed: {res.status_code} {res.body!r}")
        result = _result_words(res)
        accepted = {"Valid", "Unchanged"}
        if result.get("SSID") not in accepted or result.get("PW") not in accepted:
            raise HardwareTestFailureError(f"PUT /networking during stale-credential recovery was rejected: {result!r}")
    finally:
        bench.leave_dut_hotspot_and_restore_bridge()


@pytest.fixture(scope="session")
def dut_ip(board: Board, bench: BenchBridge, request: pytest.FixtureRequest) -> str:
    # The DUT's STA address on the bench bridge network. An exec stops main.py and hard_reset() restarts it, so the
    # address is read once the log shows the STA connect, then the board is reset and serving is awaited.
    config = request.config
    seen: list[str] = []

    def note(text: str, *, recovery: bool = False) -> None:
        record_session_note(config, text, recovery=recovery, source="dut_ip")

    def sta_connected() -> bool:
        seen.extend(board.tail_log(duration_s=_STA_TAIL_STEP_S))
        return "WLAN connection established" in "\n".join(seen)

    harness.kick_then_reset(board, bench)
    try:
        harness.recover_by_reset(board, bench, sta_connected, first_wait_s=_IP_AND_HTTP_TIMEOUT_S, retry_wait_s=_IP_AND_HTTP_TIMEOUT_S, skipped="the first STA connect after the session's reset", note=note, description="DUT STA connect")
    except TimeoutError:
        # Neither reset helps when the DUT holds stale stored credentials (a bridge recreated with a new SSID/password).
        _recover_stale_dut_credentials(bench, note)
        seen.clear()
        harness.kick_then_reset(board, bench)
        wait_until(sta_connected, timeout_s=_IP_AND_HTTP_TIMEOUT_S, description="DUT STA connect after stale-credential recovery")
    try:
        output = board.exec("import network\nw = network.WLAN(network.STA_IF)\nprint('DUT_IP=' + (w.ifconfig()[0] if w.isconnected() else ''))", timeout_s=_DUT_IP_EXEC_TIMEOUT_S)
    finally:
        harness.kick_then_reset(board, bench)
    ips = [line[len("DUT_IP=") :].strip() for line in output.splitlines() if line.startswith("DUT_IP=")]
    if not ips or not ips[0]:
        raise HardwareTestFailureError(f"the log showed 'WLAN connection established' but the board reported no STA address:\n{output}")
    ip = ips[0]
    wait_until(
        lambda: http_client.fetch(ip, 80, "GET", "/status", timeout_s=_HTTP_READY_PROBE_TIMEOUT_S).status_code == 200,
        timeout_s=_DUT_SERVING_AFTER_STA_S + _IP_AND_HTTP_TIMEOUT_S,
        poll_interval_s=_HTTP_READY_POLL_S,
        description=f"DUT serves real HTTP at {ip} (the reset after the address read, the STA reconnect, then {_DUT_SERVING_AFTER_STA_S} s for the webserver: main() starts it before the first NTP sync)",
    )
    if not config.stash.get(_REST_SAVED, False):
        error_log_helpers.save_errcount(ip, "session-start")
        config.stash[_REST_SAVED] = True
    return ip
