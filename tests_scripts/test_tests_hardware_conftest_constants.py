"""tests_hardware/conftest.py's own definitions held to the files that decide them - the DUT hostname candidates and
hotspot password the harness derives from the bench TOML and src/'s schema, the standard DebugLevel against its schema
bound - plus the session start's evidence order and the standard-state report, on fakes."""

import ast
import json
import os
import re
import sys
from pathlib import Path
from types import ModuleType

import pytest
import tomllib
from _devices import DEVICE_NAMES, bench_device, device_toml
from _script_loader import load_script_module

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests_hardware"))
import error_log_helpers
import harness

_TESTS_HARDWARE = Path(__file__).resolve().parents[1] / "tests_hardware"
_DUT_IP = "192.0.2.10"


def _load(name: str, path: Path) -> ModuleType:
    return load_script_module(path, name)


@pytest.fixture(scope="module")
def conftest() -> ModuleType:
    return _load("hardware_conftest_under_test", _TESTS_HARDWARE / "conftest.py")


def _schema(repo_root: Path, module: str, const_name: str) -> "tuple[object, ...]":
    # One field of a one-field _VAL_* schema tuple in src/, read as text (micropython.const() folds the name out).
    source = (repo_root / "src" / module).read_text(encoding="utf-8")
    match = re.search(rf"^{const_name} = const\((\(\(.*?\),\))\)", source, re.MULTILINE)
    assert match is not None, f"src/{module} no longer declares {const_name} in the expected shape"
    field: tuple[object, ...] = ast.literal_eval(match.group(1))[0]
    return field


def _bench_table() -> "dict[str, object]":
    table: dict[str, object] = tomllib.loads(device_toml(bench_device()).read_text(encoding="utf-8"))["device"]
    return table


def test_the_first_hostname_candidate_is_the_bench_devices_own_toml_hostname() -> None:
    # Ordered newest-first, so a freshly flashed board is found on the first scan.
    assert harness.dut_hostname_candidates()[0] == _bench_table()["hostname"], "the bench would scan for an SSID the bench board no longer broadcasts"


def test_the_last_hostname_candidate_is_the_shared_schema_default(repo_root: Path) -> None:
    # The fallback for a board whose config file predates per-device hostname injection.
    assert harness.dut_hostname_candidates()[-1] == _schema(repo_root, "asy_wifi_service.py", "_VAL_HOSTNAME")[2]


def test_every_hostname_candidate_fits_the_schema_bound(repo_root: Path) -> None:
    _, _, _, low, high, _ = _schema(repo_root, "asy_wifi_service.py", "_VAL_HOSTNAME")
    assert isinstance(low, int) and isinstance(high, int)
    for candidate in harness.dut_hostname_candidates():
        assert low <= len(candidate) <= high, f"{candidate!r} cannot be a live Hostname value"


def test_the_hotspot_password_is_the_bench_tomls_and_the_schema_default(repo_root: Path) -> None:
    # The one pinned copy pair: the bench TOML's password and _VAL_HOTSPOT_PW's default, within its bounds.
    password = harness.hotspot_password()
    _, _, default, low, high, _ = _schema(repo_root, "asy_wifi_service.py", "_VAL_HOTSPOT_PW")
    assert password == _bench_table()["hotspot_password"] == default
    assert isinstance(low, int) and isinstance(high, int) and low <= len(password) <= high, password


def test_the_stale_credential_recovery_joins_with_the_harness_password(repo_root: Path) -> None:
    # The join's password is the helper's, never a literal copy of it in the conftest.
    tree = ast.parse((repo_root / "tests_hardware" / "conftest.py").read_text(encoding="utf-8"))
    joins = [node for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "join_dut_hotspot"]
    assert len(joins) == 1 and ast.unparse(joins[0].args[1]) == "harness.hotspot_password()", [ast.unparse(j) for j in joins]


def test_the_standard_debug_level_is_the_schemas_most_verbose(conftest: ModuleType, repo_root: Path) -> None:
    # Every log-based boot oracle needs >= 3 (harness.wait_for_boot()); the standard state holds the schema's maximum.
    high = _schema(repo_root, "asy_system_service.py", "_VAL_DEBUG_LEVEL")[4]
    assert high == conftest._STANDARD_DEBUG_LEVEL
    assert conftest._STANDARD_DEBUG_LEVEL >= 3


class _Reporter:
    def __init__(self) -> None:
        self.lines: list[str] = []

    def write_line(self, line: str) -> None:
        self.lines.append(line)


class _RunRecord:
    def __init__(self) -> None:
        self.notes: list[tuple[str, str]] = []

    def add_session_note(self, _config: object, text: str, *, recovery: bool, source: str) -> None:
        del recovery
        self.notes.append((source, text))


class _Plugins:
    def __init__(self) -> None:
        self.plugins: dict[str, object] = {"terminalreporter": _Reporter(), "_pytest_run_record": _RunRecord()}

    def get_plugin(self, name: str) -> object:
        return self.plugins.get(name)


class _Config:
    def __init__(self, **options: object) -> None:
        self.options = options
        self.stash = pytest.Stash()
        self.pluginmanager = _Plugins()
        self.ini_lines: list[str] = []

    def getoption(self, name: str) -> object:
        return self.options.get(name)

    def addinivalue_line(self, name: str, line: str) -> None:
        self.ini_lines.append(f"{name}: {line}")

    @property
    def console(self) -> "list[str]":
        reporter = self.plugins("terminalreporter")
        assert isinstance(reporter, _Reporter)
        return reporter.lines

    @property
    def notes(self) -> "list[tuple[str, str]]":
        record = self.plugins("_pytest_run_record")
        assert isinstance(record, _RunRecord)
        return record.notes

    def plugins(self, name: str) -> object:
        return self.pluginmanager.get_plugin(name)


class _Board:
    def __init__(self, exec_output: str = "", log: "list[str] | None" = None) -> None:
        self.exec_output = exec_output
        self.log = [] if log is None else log

    def exec(self, expr: str, timeout_s: "float | None" = None) -> str:
        del expr, timeout_s
        self.log.append("raw-REPL exec")
        return self.exec_output

    def hard_reset(self) -> None:
        self.log.append("hard_reset")


@pytest.mark.parametrize(("output", "level"), [("LEVEL=5\nFILES=[]\n", 5), ("LEVEL=3\nFILES=[]\n", 3), ("LEVEL=absent\nFILES=[]\n", None)])
def test_the_debug_level_read_is_parsed_strictly(conftest: ModuleType, output: str, level: "int | None") -> None:
    board = _Board(output)
    assert conftest._board_state(board, None, None) == (level, [])
    assert board.log == ["raw-REPL exec", "hard_reset"], "the read-only exec stops main.py, so a reset follows it"
    deviations = conftest.board_state_deviations(level, [], False)
    if level == 5:
        assert deviations == []
    else:
        assert [(d.name, d.read, d.standard) for d in deviations] == [("DebugLevel", str(level) if level else "absent", "5")]
        assert "--repair-standard-state" in deviations[0].remedy


@pytest.mark.parametrize("output", ["", "LEVEL=5\n", "LEVEL=5\nLEVEL=5\nFILES=[]\n", "LEVEL=5\nFILES={}\n"])
def test_a_board_state_read_without_one_level_and_one_name_list_raises(conftest: ModuleType, output: str) -> None:
    with pytest.raises(harness.HardwareTestFailureError):
        conftest.parse_board_state(output)


def test_the_standard_state_report_names_each_deviation_and_its_repair(conftest: ModuleType) -> None:
    # DebugLevel 3 and the write-protect set (both repaired on request) and another round's image (a reflash), one message.
    deviations = conftest.board_state_deviations(3, ["config_SYSTEM.cfg"], True)
    bench = _load("bench_conftest_for_report", _TESTS_HARDWARE / "bench" / "conftest.py")
    record = {"device": bench_device(), "BuildDate": "2026-10-13 09:00:00"}
    deviations += [d for d in bench.image_deviations(record, {"BuildDate": "2026-10-14 12:00:00"}, bench_device(), allow_rollover=False) if d[0] == "image BuildDate"]
    config = _Config()
    with pytest.raises(pytest.exit.Exception) as stopped:
        conftest.exit_on_deviations(config, deviations)
    assert config.console[0] == "board not in the standard state:", config.console
    assert config.console == str(stopped.value.msg).splitlines(), "the console message precedes the stop and equals it"
    by_name = {line.split(":", 1)[0].strip(" -"): line for line in config.console[1:]}
    assert sorted(by_name) == ["DebugLevel", "FRAM write-protect", "image BuildDate"], by_name
    assert "read 3" in by_name["DebugLevel"] and "holds 5" in by_name["DebugLevel"]
    assert "read set" in by_name["FRAM write-protect"] and "holds clear" in by_name["FRAM write-protect"]
    assert all("--repair-standard-state" in by_name[name] for name in ("DebugLevel", "FRAM write-protect"))
    assert "reflash" in by_name["image BuildDate"] and "--repair-standard-state" not in by_name["image BuildDate"]
    assert "2026-10-13 09:00:00" in by_name["image BuildDate"] and "2026-10-14 12:00:00" in by_name["image BuildDate"]


@pytest.mark.parametrize("answer", ["answers", "refuses", "absent"])
def test_the_session_start_saves_status_over_rest_before_any_raw_repl_call(conftest: ModuleType, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, answer: str) -> None:
    log: list[str] = []

    def save_errcount(dut_ip: str, reason: str) -> None:
        if answer == "refuses":
            raise ConnectionRefusedError(dut_ip)
        log.append(f"GET /status saved ({reason})")

    def save_fram_raw(board: object, reason: str) -> object:
        del board
        log.append(f"raw-REPL FRAM dump ({reason})")
        return harness.FramDump(tmp_path / "dump.txt", {"write_protected": False})

    monkeypatch.setattr(error_log_helpers, "save_errcount", save_errcount)
    monkeypatch.setattr(harness, "save_fram_raw", save_fram_raw)
    config = _Config()
    conftest.session_start_evidence(config, _Board(log=log), None if answer == "absent" else _DUT_IP)
    rest = ["GET /status saved (session-start)"] if answer == "answers" else []
    assert log == [*rest, "raw-REPL FRAM dump (session-start)", "hard_reset"]
    assert config.stash[conftest._REST_SAVED] is (answer == "answers")
    assert [source for source, _ in config.notes] == ([] if answer == "answers" else ["fram_evidence_saved"]), config.notes


def test_bench_device_names_a_toml_and_is_exported_for_the_session(conftest: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("BENCH_DEVICE", raising=False)
    with pytest.raises(pytest.UsageError, match=r"no devices/no-such-board\.toml"):
        conftest.pytest_configure(_Config(**{"--bench-device": "no-such-board"}))
    config = _Config(**{"--bench-device": DEVICE_NAMES[-1]})
    conftest.pytest_configure(config)
    assert os.environ.get("BENCH_DEVICE") == DEVICE_NAMES[-1]
    assert harness.bench_device() == DEVICE_NAMES[-1]
    conftest.pytest_unconfigure(config)
    assert "BENCH_DEVICE" not in os.environ, "the session's export outlived it"
    assert any(line.startswith("markers: ") for line in config.ini_lines), "the marker table registers with the options"


class _RepairableBoard(_Board):
    # A board at DebugLevel 3 with the write-protect set until the repairs run; `stuck` keeps the level unrepaired.
    def __init__(self, *, stuck: bool = False) -> None:
        super().__init__()
        self.level, self.protected, self.stuck = 3, True, stuck

    def exec(self, expr: str, timeout_s: "float | None" = None) -> str:
        del timeout_s
        self.log.append("exec")
        if "WP_CLEARED" in expr:
            self.protected = False
            return "WP_CLEARED=True\n"
        return f"LEVEL={self.level}\nFILES=[]\n"

    def run_isolated(self, script_path: "str | Path", **_kwargs: object) -> str:
        self.log.append(f"run {Path(script_path).name}")
        before, self.level = self.level, self.level if self.stuck else 5
        return f"FACT before={before}\nFACT written={json.dumps(not self.stuck)}\nDONE\n"


class _Request:
    def __init__(self, config: _Config, board: _Board) -> None:
        self.config, self.board = config, board

    def getfixturevalue(self, name: str) -> object:
        assert name == "board", name
        return self.board


def _start_state(conftest: ModuleType, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, board: _RepairableBoard, **options: object) -> _Config:
    # Drives standard_state's start on a bench-less fake board, its snapshot and evidence dumps faked.
    monkeypatch.setattr(conftest.BenchBridge, "is_configured", lambda _self: False)
    monkeypatch.setattr(conftest, "_scd30_snapshot", lambda _board, _ip: {})
    monkeypatch.setattr(conftest, "_clear_write_protect_exec", lambda: "WP_CLEARED exec")  # its pins are another case's
    monkeypatch.setattr(harness, "save_fram_raw", lambda b, _reason: harness.FramDump(tmp_path / "dump.txt", {"write_protected": b.protected}))
    config = _Config(**options)
    state = conftest.standard_state.__wrapped__(_Request(config, board), harness.FramDump(tmp_path / "dump.txt", {"write_protected": True}))
    next(state)
    return config


def test_a_deviation_without_the_repair_flag_stops_the_session_unrepaired(conftest: ModuleType, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    board = _RepairableBoard()
    with pytest.raises(pytest.exit.Exception, match="board not in the standard state"):
        _start_state(conftest, monkeypatch, tmp_path, board)
    assert not any(entry.startswith("run ") for entry in board.log), "nothing is repaired without --repair-standard-state"


def test_the_repair_flag_repairs_each_deviation_once_and_reads_it_back(conftest: ModuleType, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    board = _RepairableBoard()
    config = _start_state(conftest, monkeypatch, tmp_path, board, **{"--repair-standard-state": True})
    assert [entry for entry in board.log if entry.startswith("run ")] == ["run system_debug_level_set_standard.py"]
    assert (board.level, board.protected) == (5, False)
    assert [text for _source, text in config.notes if text.startswith("repaired")] == ["repaired DebugLevel to 5 (one flash write)", "repaired the FRAM write-protect (status register write)"]


def test_a_repair_that_did_not_take_still_stops_the_session(conftest: ModuleType, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # The script reports a write, the read-back still finds DebugLevel 3: the start fails naming it.
    board = _RepairableBoard(stuck=True)
    monkeypatch.setattr(conftest, "_repair", lambda *_args: None)
    with pytest.raises(pytest.exit.Exception, match="DebugLevel: read 3"):
        _start_state(conftest, monkeypatch, tmp_path, board, **{"--repair-standard-state": True})
