"""Tests scripts/_digital_twin_ci_suite.py's Run 14 (the MQTT client against a real broker) without a live twin: which
devices run it, that a device without the client spawns nothing and is filed skipped, and that a missing broker fails
the run rather than skipping it, since a run that silently tested nothing would read as a pass."""

import json
import sys
from pathlib import Path
from types import ModuleType

import pytest
from _devices import DEVICE_NAMES, device_toml, devices_with

from buildgen.twin_wiring import compute_twin_wiring
from buildgen.validate import build_model


def _ctx(ci_suite: ModuleType, tmp_path: Path, *, mqtt: bool) -> object:
    # A pass over a wiring plan listing the client or not, its state and logs under tmp_path.
    plan = tmp_path / "plan.json"
    plan.write_text(json.dumps({"instances": ["fram", "mqtt"] if mqtt else ["fram"]}), encoding="utf-8")
    return ci_suite.RunContext(micropython_bin="/nonexistent", logs_dir=tmp_path, device="fixture-device", module="sensortask_fixture", wiring_plan_path=plan, instances=(), gc_threshold=-1, routes=("/status",))


@pytest.fixture
def spawned(ci_suite: ModuleType, monkeypatch: pytest.MonkeyPatch) -> list[str]:
    # Every launch stubbed, with a fresh _FAILURES and summary, so a test sees only its own run.
    log: list[str] = []
    monkeypatch.setattr(ci_suite, "_SUMMARY", ci_suite.Summary("scripts/_digital_twin_ci_suite.py", unit="checks"))
    monkeypatch.setattr(ci_suite, "_FAILURES", [])
    monkeypatch.setattr(ci_suite, "_CHECKS_PER_PASS", {})
    monkeypatch.setattr(ci_suite, "_spawn", lambda _ctx, _args, log_path: log.append(str(log_path)))
    return log


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_run_14_is_selected_by_the_devices_wiring_plan(ci_suite: ModuleType, repo_root: Path, device: str) -> None:
    # The plan buildgen writes for the device, read as the run reads it: the client listed exactly where the TOML wires it.
    plan = compute_twin_wiring(build_model(device_toml(device), repo_root / "src"))
    assert ci_suite._wires_mqtt(plan) is (device in devices_with("mqtt"))


def test_at_least_one_device_runs_it() -> None:
    # Otherwise CI's matrix would never reach Run 14 and the twin tier would hold the client to nothing.
    assert devices_with("mqtt")


def test_run_14_is_a_selection_of_its_own(ci_suite: ModuleType) -> None:
    # It reads no state an earlier run leaves, so --only 14 alone is honoured.
    assert ci_suite._run_selection("14") == frozenset({"14"})


def test_a_device_without_the_client_spawns_nothing(ci_suite: ModuleType, spawned: list[str], tmp_path: Path) -> None:
    ci_suite._run_14_mqtt_broker_faults(_ctx(ci_suite, tmp_path, mqtt=False))
    assert spawned == []
    assert ci_suite._FAILURES == []
    counts = ci_suite._SUMMARY.counts()
    assert (counts.skipped, counts.failed, counts.passed) == (1, 0, 0), counts


def test_a_missing_broker_fails_the_run_rather_than_skipping_it(ci_suite: ModuleType, spawned: list[str], monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(sys.modules[ci_suite.Mosquitto.__module__], "mosquitto_binary", lambda: None)
    ci_suite._run_14_mqtt_broker_faults(_ctx(ci_suite, tmp_path, mqtt=True))
    assert spawned == []
    assert len(ci_suite._FAILURES) == 1
    assert "no broker to test against" in ci_suite._FAILURES[0]
    assert ci_suite._SUMMARY.counts().skipped == 0
