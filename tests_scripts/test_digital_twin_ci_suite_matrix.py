"""Tests scripts/_digital_twin_ci_suite.py's fault matrix and command line without a live twin: every fault and hang op
a chip fake hooks is driven by a run or left out with a reason, every op named exists in the twin's vocabulary, Run 12's
stack subject is the plan's first bus device, and the diagnosis options refuse what they cannot honour (exit 2)."""

import ast
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest
from _devices import DEVICE_NAMES, device_toml

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SUITE = _REPO_ROOT / "scripts" / "_digital_twin_ci_suite.py"
_HOOKS = {"maybe_raise": "fault", "maybe_hang": "hang"}


def _chip_hook_ops() -> "set[tuple[str, str, str]]":
    # (driver, kind, op) of every maybe_raise/maybe_hang call with a literal op in digital_twin/_<driver>_chip.py.
    found: set[tuple[str, str, str]] = set()
    for path in sorted((_REPO_ROOT / "digital_twin").glob("_*_chip.py")):
        driver = path.stem[1 : -len("_chip")]
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in _HOOKS and node.args and isinstance(node.args[0], ast.Constant):
                found.add((driver, _HOOKS[node.func.attr], str(node.args[0].value)))
    return found


def _driven(ci_suite: ModuleType) -> "set[tuple[str, str, str]]":
    # What the runs drive: Run 3's sustained faults, Run 5c's bounded ones, Run 5's measure read, Run 12's stack-exhaustion
    # reads, Run 10's hangs.
    ops = {(d, "fault", op) for d, op in {**ci_suite._SUSTAINED_FAULT}.items()} | {(d, "fault", op) for d, op in ci_suite._BOUNDED_FAULT.items()}
    ops.add(("sgp40", "fault", ci_suite._RUN_5_FAULT_OP))
    ops |= {(d, "fault", op) for d, op in ci_suite._STACK_FAULT_READ_OP.items()}
    return ops | {(d, "hang", op) for d, op in ci_suite._HANG_MATRIX.items()}


def _suite(*args: str) -> "subprocess.CompletedProcess[str]":
    return subprocess.run([sys.executable, str(_SUITE), *args], capture_output=True, text=True, check=False, cwd=_REPO_ROOT, timeout=60)


def _vocabulary(name: str) -> "dict[str, tuple[str, ...]]":
    # One of digital_twin/launch.py's --fault/--hang tables, read by ast: driver -> its ops.
    for node in ast.parse((_REPO_ROOT / "digital_twin" / "launch.py").read_text(encoding="utf-8")).body:
        if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name) and node.targets[0].id == name:
            table = ast.literal_eval(node.value)
            assert isinstance(table, dict)
            return table
    raise AssertionError(f"digital_twin/launch.py no longer defines {name}")


def test_the_hook_scan_sees_the_chip_fakes() -> None:
    # The premise of the completeness check below: a scan that saw nothing would pass it vacuously.
    ops = _chip_hook_ops()
    assert {d for d, _, _ in ops} >= {"scd30", "sgp40", "bmp3xx", "isl29125", "fram"}, ops
    assert ("sgp40", "fault", "readfrom_into") in ops and ("fram", "hang", "write") in ops


def test_every_hooked_op_is_driven_by_a_run_or_left_out_with_a_reason(ci_suite: ModuleType) -> None:
    missing = sorted(_chip_hook_ops() - _driven(ci_suite) - set(ci_suite._LEFT_OUT))
    assert not missing, f"chip-fake hook op(s) {missing} are in no run of the fault matrix and not in _LEFT_OUT"
    assert all(reason.strip() for reason in ci_suite._LEFT_OUT.values()), "every left-out op names its reason"


def test_the_matrix_names_only_ops_the_twin_accepts(ci_suite: ModuleType) -> None:
    faults, hangs = _vocabulary("_FAULT_DEVICE_OPS"), _vocabulary("_HANG_DEVICE_OPS")
    bad = sorted((d, k, op) for d, k, op in _driven(ci_suite) if op not in (faults if k == "fault" else hangs).get(d, ()))
    assert not bad, f"the fault matrix names op(s) the twin's --fault/--hang refuse: {bad}"
    wildcard = {"*", "bounded"}  # a whole family left out, whose ops are not chip hooks
    bad_left = sorted((d, k, op) for d, k, op in ci_suite._LEFT_OUT if op not in wildcard and op not in (faults if k == "fault" else hangs).get(d, ()))
    assert not bad_left, f"_LEFT_OUT names op(s) the twin does not have: {bad_left}"


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_every_uart_link_instance_gets_its_silent_fault(ci_suite: ModuleType, device: str) -> None:
    instances = ci_suite._plan_instances(device_toml(device))
    links = [inst.key for inst in instances if inst.driver == "uart_link"]
    ctx = ci_suite.RunContext(micropython_bin="/nonexistent", logs_dir=Path("/nonexistent"), device=device, module=f"sensortask_{device}", wiring_plan_path=Path("/nonexistent"), instances=instances, gc_threshold=-1, routes=("/status",))
    faulted = [inst.key for inst in ci_suite._fault_instances(ctx, ci_suite._SUSTAINED_FAULT) if inst.driver == "uart_link"]
    assert faulted == links
    assert ci_suite._SUSTAINED_FAULT["uart_link"] == "silent"
    assert len(links) in (0, 2), f"{device} wires {links}: the pair has an initiator and a responder"


def test_run_12s_stack_fault_reads_on_the_plans_first_bus_device(ci_suite: ModuleType) -> None:
    # The plan's first attachment, its I2C buses in plan order before its SPI device, by instance key; a plan wiring no
    # bus device has no subject, and the cell is skipped by name.
    i2c = {"i2c1": [{"driver": "sgp40", "name_ext": "in", "address": 0x59}], "i2c0": [{"driver": "scd30", "name_ext": "", "address": 0x61}]}
    spi = {"spi0": {"driver": "fram", "name_ext": "", "max_size": 0x2000}}
    assert ci_suite._stack_fault_instance({"buses": i2c, "spi": spi, "uart": None}) == ci_suite.Instance("sgp40_in", "sgp40", "in")
    assert ci_suite._stack_fault_instance({"buses": {}, "spi": spi, "uart": None}) == ci_suite.Instance("fram", "fram", "")
    assert ci_suite._stack_fault_instance({"buses": {}, "spi": {}, "uart": None}) is None


def test_run_12s_stack_fault_ops_are_queued_reads_the_twin_raises_from(ci_suite: ModuleType) -> None:
    # A mode that stays set for the run takes no stack fault (digital_twin/launch.py parse_fault_spec()).
    persistent = _vocabulary_tuple("_PERSISTENT_FAULT_OPS")
    assert set(ci_suite._STACK_FAULT_READ_OP) == {d for d in _vocabulary("_FAULT_DEVICE_OPS") if d not in ("uart_link", "wlan")}
    assert not [(d, op) for d, op in ci_suite._STACK_FAULT_READ_OP.items() if (d, op) in persistent or op not in _vocabulary("_FAULT_DEVICE_OPS")[d]]


def _vocabulary_tuple(name: str) -> "tuple[tuple[str, str], ...]":
    # digital_twin/launch.py's tuple of (driver, op) pairs under `name`, read by ast.
    for node in ast.parse((_REPO_ROOT / "digital_twin" / "launch.py").read_text(encoding="utf-8")).body:
        if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name) and node.targets[0].id == name:
            pairs = ast.literal_eval(node.value)
            assert isinstance(pairs, tuple)
            return pairs
    raise AssertionError(f"digital_twin/launch.py no longer defines {name}")


@pytest.mark.parametrize("args", [["--only", "5x"], ["--only", "5b"], ["--only", "4,5"], ["--repeat", "0"], ["--gc-threshold", "1024"]])
def test_a_selection_the_suite_cannot_honour_is_a_usage_error(args: "list[str]") -> None:
    # 5b alone and 4 alone read state their producer never wrote: refused, never a pass that checks less.
    done = _suite("--micropython-bin", "/nonexistent", "--device", "fixture-device", *args)
    assert done.returncode == 2, (done.returncode, done.stderr)


def test_the_device_is_required() -> None:
    done = _suite("--micropython-bin", "/nonexistent")
    assert done.returncode == 2 and "--device" in done.stderr, done.stderr


def test_the_selection_parser_accepts_known_runs_with_their_producers(ci_suite: ModuleType) -> None:
    assert ci_suite._run_selection("5c") == frozenset({"5c"})
    assert ci_suite._run_selection("3, 4") == frozenset({"3", "4"})
    assert ci_suite._build_parser().parse_args(["--micropython-bin", "mp", "--device", "fixture-device", "--device-toml", "x/fixture-device.toml", "--only", "3"]).device_toml == Path("x/fixture-device.toml")
