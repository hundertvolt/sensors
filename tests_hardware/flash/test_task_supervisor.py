"""Flash-tier automated test: SystemService.start_tasks()/supervise_tasks()'s own restart of a dead task on a real
board, not just mock/twin bookkeeping - the recovery rung CLAUDE.md's memory-safety rule leans on between a caught
local degrade and the hardware watchdog. The script reports; the verdict is here."""

from typing import TYPE_CHECKING

from error_log_helpers import code
from harness import DEVICE_SCRIPTS_DIR, parse_facts

if TYPE_CHECKING:
    from harness import Board

COVERS_TWIN_SCENARIOS: tuple[str, ...] = ("ci_suite._run_5_recovery_after_bounded_fault",)

# @tunable l3.task_supervisor_script_timeout_s = 15.0
_SCRIPT_TIMEOUT_S = 15.0
_TASK_RETURNED = code("E", "TASK_RETURNED")


def test_the_supervisor_restarts_a_real_dead_task(board: "Board") -> None:
    output = board.run_isolated(DEVICE_SCRIPTS_DIR / "system_service_restarts_a_real_dead_task.py", timeout_s=_SCRIPT_TIMEOUT_S, mode="restart")
    facts = parse_facts(output)
    calls, system = facts.get("starter_calls"), facts.get("system")
    assert isinstance(calls, int) and calls >= 2, f"the dying task's starter ran {calls} time(s) - expected the first start and a real restart: {facts}"
    assert isinstance(system, dict), f"no SYSTEM log fact: {facts}"
    # Each restart follows exactly one logged end: the supervisor logs the dead task, then starts it anew.
    assert system.get("ErrCount") == calls - 1, f"{calls} starter calls but {system.get('ErrCount')} logged task ends: {facts}"
    logged = [(t, n) for t, n in zip(system.get("ErrType", []), system.get("ErrNum", []), strict=True) if t != "N"]
    assert logged and all(entry == ("E", _TASK_RETURNED) for entry in logged), f"the SYSTEM log holds other than TASK_RETURNED entries: {system}"
    # At DebugLevel 0 a dying task prints nothing: asyncio's default handler text or a traceback is a leak past the log.
    leaked = [line for line in output.splitlines() if "Task exception wasn't retrieved" in line or "Traceback" in line]
    assert not leaked, "a task's end reached the console at DebugLevel 0:\n" + "\n".join(leaked)
