"""tests_hardware/run_scopes.py, checked by a real --collect-only: every listed node exists in its tier and
survives the bench runner's own marker floor, and a scope's writes are exactly the groups its tests' markers
name, so --allow-persistence-writes-to with them selects the whole scope and permits nothing beyond it."""

import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tests_hardware"))

from persistence_groups import persistence_groups
from run_scopes import SCOPES, Scope

_FLOOR = "not long_soak and not multi_day_rollover"  # scripts/run_bench_hardware_suite.sh's own -m


def _collect(repo_root: Path, nodes: "list[str]", *extra: str) -> str:
    result = subprocess.run([sys.executable, "-m", "pytest", *nodes, "--collect-only", "-q", "-m", _FLOOR, *extra], cwd=repo_root, capture_output=True, text=True, check=False)
    assert result.returncode == 0, f"collection failed:\n{result.stdout}\n{result.stderr}"
    return result.stdout


def _nodes(scope: Scope, part: str) -> "list[str]":
    return [node for node, _reason in (scope.flash if part == "flash" else scope.bench)]


@pytest.mark.parametrize("name", sorted(SCOPES))
@pytest.mark.parametrize("part", ["flash", "bench"])
def test_every_listed_node_collects_in_its_tier_and_nothing_is_deselected(repo_root: Path, name: str, part: str) -> None:
    scope = SCOPES[name]
    nodes = _nodes(scope, part)
    assert nodes, f"scope {name} lists no {part} test - the runner hands each step its list"
    assert all(node.startswith(f"tests_hardware/{part}/") for node in nodes), nodes
    assert len(set(nodes)) == len(nodes), f"scope {name} lists a {part} node twice"
    assert all(reason.strip() for _node, reason in (scope.flash if part == "flash" else scope.bench)), "every entry says why the change reaches it"
    output = _collect(repo_root, nodes, *(f"--allow-persistence-writes-to={g}" for g in scope.writes))
    assert "deselected" not in output, f"scope {name}'s {part} list loses a test to the floor or its own write permission:\n{output}"
    for node in nodes:
        assert node in output, f"{node} collected nothing:\n{output}"


@pytest.mark.parametrize("name", sorted(SCOPES))
def test_a_scopes_writes_are_exactly_what_its_marked_tests_name(repo_root: Path, name: str) -> None:
    # Fewer would deselect a scoped test; more would permit a write the scope never owns.
    scope = SCOPES[name]
    assert set(scope.writes) <= persistence_groups(), scope.writes
    nodes = _nodes(scope, "flash") + _nodes(scope, "bench")
    for group in scope.writes:
        others = [f"--allow-persistence-writes-to={g}" for g in scope.writes if g != group]
        output = _collect(repo_root, nodes, *others) if others else _collect(repo_root, nodes)
        assert "deselected" in output, f"scope {name} lists {group}, but no test of it needs that group"


def test_the_mqtt_scope_runs_the_whole_client_module_and_writes_only_its_settings(repo_root: Path) -> None:
    # Owner, 2026-10-08: "include the ntp tests too, allow networking/ntp" - and nothing beyond the two groups.
    scope = SCOPES["mqtt"]
    assert "tests_hardware/bench/test_mqtt_broker_faults.py" in _nodes(scope, "bench")
    assert scope.writes == ("networking/mqtt", "networking/ntp"), "the MQTT scope permits a write to no other group, the SCD30's least of all"
    gated = _collect(repo_root, _nodes(scope, "bench"))
    assert "test_the_broker_is_found_by_the_bench_hosts_local_name" not in gated, "without the scoped permission its own write stays deselected"
