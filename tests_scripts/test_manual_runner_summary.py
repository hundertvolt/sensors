"""The manual-mode runner (tests_hardware/manual/runner.py) ends every run with the summary block
(SPECIFICATION.md E.10): a scripted run with stub manual tests, no board and no real test module
imported, checks the counts, the per-test level from each tier and the exit code of each ending."""

import subprocess
import sys
from pathlib import Path

# Registers stub tests in place of the five real manual modules, then runs main() with the given
# argv. The stub modules stand in for the real ones so nothing reaches for a board or a bridge.
_DRIVER = """
import builtins, sys, types
sys.path.insert(0, {manual_dir!r})
for name in ("manual_bus_electrical", "manual_persistence", "manual_sensor_accuracy", "manual_toolchain", "manual_wifi"):
    sys.modules[name] = types.ModuleType(name)
import runner

{body}

sys.argv = ["runner", *{argv!r}]
sys.exit(runner.main())
"""

_TWO_STEPS = """
@runner.register("usb_step_that_passes", "a [USB] step", "[USB][MANUAL]")
def _a():
    runner.confirm_pass()

@runner.register("wifi_step_that_fails", "a [USB+WiFi] step", "[USB+WiFi][MANUAL]")
def _b():
    runner.confirm_pass()
"""


def _run(repo_root: Path, body: str, *argv: str, stdin: str = "") -> subprocess.CompletedProcess[str]:
    script = _DRIVER.format(manual_dir=str(repo_root / "tests_hardware" / "manual"), body=body, argv=list(argv))
    return subprocess.run([sys.executable, "-c", script], input=stdin, capture_output=True, text=True, check=False, cwd=repo_root, timeout=60)


def _block(stdout: str) -> str:
    start = stdout.rfind("== Summary: ")
    assert start != -1, f"no summary block printed:\n{stdout}"
    return stdout[start:]


def _line(block: str, prefix: str) -> str:
    return next((ln for ln in block.splitlines() if ln.startswith(prefix)), "")


def test_one_pass_and_one_fail_print_the_block_and_exit_1(repo_root: Path) -> None:
    result = _run(repo_root, _TWO_STEPS, stdin="y\nn\n")
    block = _block(result.stdout)
    assert result.returncode == 1, result.stdout + result.stderr
    counts = _line(block, "Counts (manual steps):")
    assert "passed 1" in counts and "failed 1" in counts, block
    assert _line(block, "Levels:") == "Levels: L3/L4 (manual mode)", block
    assert "L4 wifi_step_that_fails" in block, f"the failed step must carry its level from its [USB+WiFi] tier:\n{block}"
    assert _line(block, "Result:").startswith("Result: FAIL"), block
    assert block.rstrip().splitlines()[-1] == "Exit code: 1", "nothing may follow the block"


def test_every_step_passing_exits_0_with_a_pass_block(repo_root: Path) -> None:
    result = _run(repo_root, _TWO_STEPS, stdin="y\ny\n")
    block = _block(result.stdout)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "passed 2" in _line(block, "Counts (manual steps):"), block
    assert _line(block, "Result:") == "Result: PASS", block


def test_ctrl_c_fails_the_current_step_lists_the_rest_as_not_run_and_exits_130(repo_root: Path) -> None:
    body = _TWO_STEPS + """
def _interrupted(prompt=""):
    raise KeyboardInterrupt
builtins.input = _interrupted
"""
    result = _run(repo_root, body)
    block = _block(result.stdout)
    assert result.returncode == 130, result.stdout + result.stderr
    assert "L3 usb_step_that_passes: aborted by operator" in block, block
    assert "L4 wifi_step_that_fails: not run (run aborted)" in block, block
    assert block.rstrip().splitlines()[-1] == "Exit code: 130", block


def test_an_unexpected_exception_fails_its_step_and_the_run_continues(repo_root: Path) -> None:
    body = """
@runner.register("step_that_raises", "raises", "[USB][MANUAL]")
def _a():
    raise RuntimeError("bench cable unplugged")

@runner.register("step_after_it", "passes", "[USB][MANUAL]")
def _b():
    runner.confirm_pass()
"""
    result = _run(repo_root, body, stdin="y\n")
    block = _block(result.stdout)
    assert result.returncode == 1, result.stdout + result.stderr
    assert "L3 step_that_raises: RuntimeError: bench cable unplugged" in block, block
    assert "passed 1" in _line(block, "Counts (manual steps):"), "the step after the exception must still run"


def test_an_unknown_only_name_prints_the_block_and_exits_2(repo_root: Path) -> None:
    result = _run(repo_root, _TWO_STEPS, "--only", "no_such_step")
    block = _block(result.stdout)
    assert result.returncode == 2, result.stdout + result.stderr
    assert "no manual test named no_such_step" in block, block
    assert block.rstrip().splitlines()[-1] == "Exit code: 2", block
