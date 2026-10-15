"""tests_hardware/bench/conftest.py's board_image on a fake GET /system and a tmp image record: equal build dates pass;
a different date or device, an lwIP ensemble finding, a missing record and the tick-offset test image outside the
rollover run each stop the session naming the cause."""

import json
import sys
from pathlib import Path
from types import ModuleType

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests_hardware"))
import harness  # puts toolchain/ on sys.path, as at a bench run
import http_client
import micropython_overrides
import setup_toolchain
from _devices import bench_device
from _script_loader import load_script_module

_TESTS_HARDWARE = Path(__file__).resolve().parents[1] / "tests_hardware"
_DATE = "2026-10-14 12:00:00"
_DUT_IP = "192.0.2.10"


class _StoppedError(Exception):
    pass


class _Config:
    def __init__(self, record: Path, *, rollover: bool) -> None:
        self.options: dict[str, object] = {"--image-record": str(record), "--allow-multi-day-rollover": rollover}

    def getoption(self, name: str) -> object:
        return self.options[name]


class _Request:
    def __init__(self, config: _Config) -> None:
        self.config = config


def _bench_conftest() -> ModuleType:
    return load_script_module(_TESTS_HARDWARE / "bench" / "conftest.py", "bench_conftest_under_test")


def _record(**changes: object) -> "dict[str, object]":
    # What scripts/build_firmware.py writes for this tree's bench image, with the case's changes.
    record: dict[str, object] = {"device": bench_device(), "BuildDate": _DATE, "dirty": False, "uartCrc": "none"}
    record.update(lwip=setup_toolchain.load_lwip_macros(), maxConnections=harness.configured_max_connections(), overrides=[micropython_overrides.MODLWIP_OVERRIDE_DIR_NAME])
    record.update(changes)
    return record


def _serve(monkeypatch: pytest.MonkeyPatch, status: int = 200, body: object = None) -> None:
    payload = json.dumps({"build": {"BuildDate": _DATE}} if body is None else body).encode()
    monkeypatch.setattr(http_client, "fetch", lambda *_args, **_kwargs: http_client.HttpResponse(status, {}, payload))


def _board_image(tmp_path: Path, record: "dict[str, object] | None", *, rollover: bool = False) -> "tuple[list[tuple[str, str, str, str]], list[str]]":
    # The fixture function itself, its fixtures faked: the deviations it stopped on, and the session notes it wrote.
    path = tmp_path / "firmware-bench.json"
    if record is not None:
        path.write_text(json.dumps(record), encoding="utf-8")
    stopped: list[tuple[str, str, str, str]] = []
    notes: list[str] = []

    def _exit(deviations: "list[tuple[str, str, str, str]]") -> None:
        stopped.extend(deviations)
        raise _StoppedError

    def _note(text: str, *, recovery: bool = False, source: str) -> None:
        assert source == "board_image" and not recovery
        notes.append(text)

    try:
        _bench_conftest().board_image.__wrapped__(_DUT_IP, bench_device(), _Request(_Config(path, rollover=rollover)), _exit, _note)
    except _StoppedError:
        pass
    return stopped, notes


def test_the_image_this_round_built_passes_and_names_itself(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _serve(monkeypatch)
    stopped, notes = _board_image(tmp_path, _record())
    assert stopped == []
    assert len(notes) == 1 and _DATE in notes[0] and "uartCrc 'none'" in notes[0], notes


@pytest.mark.parametrize(
    ("case", "record", "cause"),
    [
        ("date", {"BuildDate": "2026-10-13 09:00:00"}, "image BuildDate"),
        ("device", {"device": "fixture-device"}, "image device"),
        ("ensemble", {"lwip": {**setup_toolchain.load_lwip_macros(), "MEMP_NUM_UDP_PCB": 0}}, "image lwIP ensemble"),
        ("ceiling", {"maxConnections": harness.configured_max_connections() + 1}, "image maxConnections"),
        ("tick-offset", {"overrides": [micropython_overrides.TICK_OFFSET_DIR_NAME]}, "tick-offset test image"),
    ],
)
def test_each_image_mismatch_stops_the_session_naming_its_cause(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, case: str, record: "dict[str, object]", cause: str) -> None:
    _serve(monkeypatch)
    stopped, _ = _board_image(tmp_path, _record(**record))
    assert cause in [name for name, *_ in stopped], (case, stopped)
    assert all("reflash" in remedy for *_, remedy in stopped), stopped


def test_the_tick_offset_image_passes_only_in_the_rollover_run(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _serve(monkeypatch)
    stopped, _ = _board_image(tmp_path, _record(overrides=[micropython_overrides.TICK_OFFSET_DIR_NAME]), rollover=True)
    assert stopped == []


def test_a_missing_record_stops_the_session_before_any_request(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(http_client, "fetch", lambda *_a, **_k: pytest.fail("no request before the record is read"))
    with pytest.raises(pytest.exit.Exception, match=r"no image record at .*build the bench image with scripts/build_firmware\.py"):
        _board_image(tmp_path, None)


def test_a_throwaway_worktree_image_is_noted_as_local_only(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _serve(monkeypatch)
    _, notes = _board_image(tmp_path, _record(dirty=True))
    assert notes and notes[0].startswith("local-only image: revert after this round"), notes


@pytest.mark.parametrize(("status", "body"), [(503, {"error": "busy"}), (200, {"uptime": 1}), (200, ["not", "an", "object"])], ids=["status", "no-build", "array"])
def test_a_system_answer_without_a_build_object_is_a_deviation(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, status: int, body: object) -> None:
    _serve(monkeypatch, status, body)
    stopped, _ = _board_image(tmp_path, _record())
    assert [name for name, *_ in stopped] == ["image BuildDate"], stopped
