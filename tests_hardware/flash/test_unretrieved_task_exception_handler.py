"""Flash-tier automated test: SYSTEM's unretrieved-task-exception report on real silicon - allocation-free with the
heap locked at DebugLevel 0 and 1 through the real USB console path, and a thousand detached task deaths leaving the
collected heap where it was. The twin and unit tiers cannot confirm the console path; this is where it is confirmed."""

from typing import TYPE_CHECKING

from harness import DEVICE_SCRIPTS_DIR, MEMORY_ERROR_MARKERS, parse_facts

if TYPE_CHECKING:
    from collections.abc import Callable

    from harness import Board

COVERS_TWIN_SCENARIOS: tuple[str, ...] = ()

# @tunable l3.unretrieved_task_exception_handler_script_timeout_s = 30.0
_SCRIPT_TIMEOUT_S = 30.0


def test_the_unretrieved_exception_report_is_allocation_free_and_retains_nothing_on_real_hardware(board: "Board", result_note: "Callable[[str], None]") -> None:
    output = board.run_isolated(DEVICE_SCRIPTS_DIR / "unretrieved_task_exception_handler.py", timeout_s=_SCRIPT_TIMEOUT_S)
    # The level-1 probes print under their own names, so a gate word in the output is a real allocation failure.
    failed = [line for line in output.splitlines() if any(marker in line for marker in MEMORY_ERROR_MARKERS)]
    assert not failed, "the report run printed an allocation failure:\n" + "\n".join(failed)
    facts = parse_facts(output)
    assert facts.get("installed") is True, f"start_tasks() did not install SYSTEM's report on a loop with no handler: {facts}"
    stages, bounds = facts.get("gc_threshold"), facts.get("bounds")
    assert isinstance(stages, list) and isinstance(bounds, dict), f"no gc_threshold or bounds fact: {facts}"
    for n, threshold in enumerate(stages):
        stage = facts.get(f"stage_{n}")
        assert isinstance(stage, dict), f"no fact for the stage at gc.threshold {threshold}: {facts}"
        result_note(f"gc.threshold {stage.get('gc_threshold')}: reports {stage.get('reports')}, {bounds.get('deaths')} deaths in {stage.get('hammer_ms')} ms, drift {stage.get('drift')}, default handler kept {stage.get('default_handler_kept')} B")
        assert stage.get("gc_threshold") == threshold, f"the stage ran at gc.threshold {stage.get('gc_threshold')}, not {threshold}: {stage}"
        reports = stage.get("reports")
        assert isinstance(reports, list) and reports, f"no report figures at gc.threshold {threshold}: {stage}"
        kept = [r for r in reports if not r.get("cleared") or r.get("alloc_delta") != 0]
        assert not kept, f"at gc.threshold {threshold} the report kept its context or allocated: {kept}"
        assert stage.get("console_allocates") is False, f"print() or sys.print_exception() allocated on the console path at gc.threshold {threshold}: {stage}"
        assert stage.get("settled") is True, f"a dying task had not ended within the settle yields at gc.threshold {threshold}: {stage}"
        assert stage.get("context_held") is False, f"asyncio's context still holds the last dead task at gc.threshold {threshold}: {stage}"
        drift = stage.get("drift")
        assert isinstance(drift, list) and max(drift) <= bounds["drift_bytes"], f"the collected heap drifted {drift} B over {bounds.get('deaths')} deaths, past {bounds['drift_bytes']} B: {stage}"
        # The contrast: a bound the default handler also met would measure nothing.
        assert isinstance(stage.get("default_handler_kept"), int) and stage["default_handler_kept"] >= bounds["large_local"], f"the default handler kept only {stage.get('default_handler_kept')} B - the contrast measured nothing: {stage}"
