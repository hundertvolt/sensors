"""Tests scripts/_digital_twin_ci_suite.py's Run 12 (the MQTT client against a real broker) without a live twin: which
devices run it, that a device without the client spawns nothing, and that a missing broker fails the run rather than
skipping it, since a run that silently tested nothing would read as a pass."""

import sys
from pathlib import Path
from types import ModuleType

import pytest
import tomllib
from _devices import DEVICE_NAMES, device_toml


def _carries_mqtt(device: str) -> bool:
    doc = tomllib.loads(device_toml(device).read_text())
    return any(instance.get("driver") == "mqtt" for instance in doc.get("instance", []))


def _ctx(ci_suite: ModuleType, tmp_path: Path, *, mqtt: bool) -> object:
    return ci_suite.RunContext(
        micropython_bin="/nonexistent",
        logs_dir=tmp_path,
        device="fixture",
        module="sensortask_fixture",
        wiring_plan_path=tmp_path / "plan.json",
        drivers=frozenset(),
        gc_threshold=-1,
        mqtt=mqtt,
    )


@pytest.fixture
def spawned(ci_suite: ModuleType, monkeypatch: pytest.MonkeyPatch) -> list[str]:
    # Every subprocess and state side effect stubbed, with a fresh _FAILURES, so a test sees only its own run.
    log: list[str] = []
    monkeypatch.setattr(ci_suite, "_FAILURES", [])
    monkeypatch.setattr(ci_suite, "_clean_state", lambda: None)  # never touches the real digital_twin/ state
    monkeypatch.setattr(ci_suite, "_spawn", lambda _ctx, _args, log_path: log.append(str(log_path)))
    return log


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_run_12_is_selected_by_the_device_toml(ci_suite: ModuleType, device: str) -> None:
    assert ci_suite._device_has_mqtt(device) is _carries_mqtt(device)


def test_at_least_one_device_runs_it() -> None:
    # Otherwise CI's matrix would never reach Run 12 and the twin tier would hold the client to nothing.
    assert any(_carries_mqtt(device) for device in DEVICE_NAMES)


def test_a_device_without_the_client_spawns_nothing(ci_suite: ModuleType, spawned: list[str], tmp_path: Path) -> None:
    ci_suite._run_12_mqtt_broker_faults(_ctx(ci_suite, tmp_path, mqtt=False))
    assert spawned == []
    assert ci_suite._FAILURES == []


def test_a_missing_broker_fails_the_run_rather_than_skipping_it(ci_suite: ModuleType, spawned: list[str], monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(sys.modules[ci_suite.Mosquitto.__module__], "mosquitto_binary", lambda: None)
    ci_suite._run_12_mqtt_broker_faults(_ctx(ci_suite, tmp_path, mqtt=True))
    assert spawned == []
    assert len(ci_suite._FAILURES) == 1
    assert "no broker to test against" in ci_suite._FAILURES[0]
