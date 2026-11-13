"""The manual-mode runner (tests_hardware/manual/runner.py) ends every run with the summary block (SPECIFICATION.md
E.10): scripted runs of stub steps check the counts, levels and exit codes; the pull steps run against a faked board and
clock, recording their latencies; and a fresh interpreter lists every step, reaching harness and buildgen on its own."""

import os
import subprocess
import sys
from pathlib import Path

import pytest
from _script_loader import load_script_module

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


# Imports the real manual_bus_electrical with the board faked: a clock that a one-second poll advances without sleeping,
# a /status and errcount the case scripts against it, the countdowns skipped, and the evidence under the test's own dir.
_REAL_STEPS = """
import sys
sys.path.insert(0, {manual_dir!r})
import runner
import manual_bus_electrical as step
from buildgen.model import MAINTENANCE_NAMES
from tests._error_codes import code

class Clock:
    now = 0.0
    def monotonic(self):
        return self.now
    def sleep(self, seconds):
        self.now += seconds

clock = step.time = Clock()
step.countdown = lambda seconds, message: None
step.dut_ip = lambda: "192.0.2.1"
step.save_errcount = lambda dut_ip, reason: None
uptime = [100]

def system():
    uptime[0] += 1
    return {{"SysUptime": uptime[0]}}

{body}

sys.argv = ["runner", *{argv!r}]
sys.exit(runner.main())
"""

# The FRAM log's first entry `late_s` after the pull (never, for None).
_FRAM_BOARD = """
def get_errcount(dut_ip):
    return {{"FRAM": {{"counter": 1 if {late_s!r} is not None and clock.now >= {late_s!r} else 0, "history": []}}}}

step.get_errcount = get_errcount
step.rest_get = lambda path: {{"system": system()}}
"""

# The link fails from 2 s after the pull, logging two NO_ACK entries, and transfers again 3 s after the replug (or never).
_LINK_BOARD = """
def link():
    return {{"Transfers": 11 if {resumes!r} and clock.now >= 5 else 10, "Failures": 2 if clock.now >= 2 else 0}}

def get_errcount(dut_ip):
    failed = clock.now >= 2
    return {{"fixture_link_logger": {{"counter": 2 if failed else 0, "history": [{{"type": "E", "num": code("E", "UART_NO_ACK")}}] * (2 if failed else 0)}}}}

step.get_errcount = get_errcount
step.rest_get = lambda path: {{"system": system(), "sensors": {{MAINTENANCE_NAMES["uart_link"]: link()}}}}
"""


def _block(stdout: str) -> str:
    start = stdout.rfind("== Summary: ")
    assert start != -1, f"no summary block printed:\n{stdout}"
    return stdout[start:]


def _line(block: str, prefix: str) -> str:
    return next((ln for ln in block.splitlines() if ln.startswith(prefix)), "")


def _real_steps(repo_root: Path, tmp_path: Path, body: str, *argv: str, stdin: str) -> subprocess.CompletedProcess[str]:
    script = _REAL_STEPS.format(manual_dir=str(repo_root / "tests_hardware" / "manual"), body=body, argv=list(argv))
    env = {**os.environ, "EVIDENCE_DIR": str(tmp_path / "evidence")}
    return subprocess.run([sys.executable, "-c", script], input=stdin, capture_output=True, text=True, check=False, cwd=repo_root, env=env, timeout=60)


def _run(repo_root: Path, body: str, *argv: str, stdin: str = "") -> subprocess.CompletedProcess[str]:
    script = _DRIVER.format(manual_dir=str(repo_root / "tests_hardware" / "manual"), body=body, argv=list(argv))
    return subprocess.run([sys.executable, "-c", script], input=stdin, capture_output=True, text=True, check=False, cwd=repo_root, timeout=60)


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


def test_a_step_returning_with_no_judgment_fails(repo_root: Path) -> None:
    # Enter alone is no verdict: a step that only confirms fails; one that reached a scripted assertion passes.
    body = """
@runner.register("step_without_judgment", "only confirms", "[USB][MANUAL]")
def _a():
    runner.confirm()

@runner.register("step_ending_on_an_assert", "a scripted check", "[USB][MANUAL]")
def _b():
    runner.record_assertion()
"""
    result = _run(repo_root, body, stdin="\n")
    block = _block(result.stdout)
    assert result.returncode == 1, result.stdout + result.stderr
    assert "L3 step_without_judgment: no pass/fail judgment recorded" in block, block
    assert "passed 1" in _line(block, "Counts (manual steps):"), block
    assert "step_ending_on_an_assert: PASS (operator judged)" in result.stdout, result.stdout


def test_an_observation_is_a_verdict_only_with_text(repo_root: Path) -> None:
    body = """
@runner.register("observed_with_text", "an exploratory item", "[USB+WiFi][MANUAL]")
def _a():
    runner.observe("What happened?")

@runner.register("observed_with_enter", "the same item, Enter alone", "[USB+WiFi][MANUAL]")
def _b():
    runner.observe("What happened?")
"""
    result = _run(repo_root, body, stdin="a popup appeared\n\n")
    block = _block(result.stdout)
    assert result.returncode == 1, result.stdout + result.stderr
    assert "passed 1" in _line(block, "Counts (manual steps):"), block
    assert "L4 observed_with_enter: no pass/fail judgment recorded" in block, block


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


@pytest.mark.parametrize(("late_s", "recorded"), [(3, "3 s"), (None, "none within 120 s")], ids=["answering-late", "never"])
def test_the_fram_pull_records_the_seconds_to_the_first_fram_entry(repo_root: Path, tmp_path: Path, late_s: "int | None", recorded: str) -> None:
    result = _real_steps(repo_root, tmp_path, _FRAM_BOARD.format(late_s=late_s), "--only", "fram_unplug_replug_recovery", stdin="\ny\n")
    assert result.returncode == 0, result.stdout + result.stderr
    assert (tmp_path / "evidence" / "fram-pull-latency.txt").read_text(encoding="utf-8") == f"seconds from the FRAM pull to its first FRAM log entry: {recorded}\n"
    assert f"The first FRAM log entry after the pull: {recorded}." in result.stdout, result.stdout


def test_the_uart_crossover_pull_records_its_codes_and_its_recovery(repo_root: Path, tmp_path: Path) -> None:
    result = _real_steps(repo_root, tmp_path, _LINK_BOARD.format(resumes=True), "--only", "uart_crossover_pull_recovery", stdin="\n\ny\n")
    assert result.returncode == 0, result.stdout + result.stderr
    no_ack = f"E{load_script_module(repo_root / 'tests' / '_error_codes.py', '_error_codes_for_the_pull_step').code('E', 'UART_NO_ACK')}"
    recorded = (tmp_path / "evidence" / "uart-crossover-pull.txt").read_text(encoding="utf-8")
    assert recorded == f"first failed transfer after the pull: 2 s; Failures 0 -> 2; codes logged: {{'fixture_link_logger': ['{no_ack}', '{no_ack}']}}; transfers resumed after the replug: 3 s\n", recorded
    assert _line(_block(result.stdout), "Result:") == "Result: PASS", result.stdout


def test_codes_the_ring_no_longer_holds_are_counted_not_dropped(repo_root: Path, tmp_path: Path) -> None:
    # Five entries logged into a ring holding two: the record names the two it can read and counts the three it cannot.
    body = _LINK_BOARD.format(resumes=True).replace('"counter": 2 if failed else 0', '"counter": 5 if failed else 0')
    assert '"counter": 5 if failed' in body, "the fake board's counter is no longer where this case raises it"
    result = _real_steps(repo_root, tmp_path, body, "--only", "uart_crossover_pull_recovery", stdin="\n\ny\n")
    assert result.returncode == 0, result.stdout + result.stderr
    no_ack = f"E{load_script_module(repo_root / 'tests' / '_error_codes.py', '_error_codes_for_the_ring_case').code('E', 'UART_NO_ACK')}"
    assert f"codes logged: {{'fixture_link_logger': ['{no_ack}', '{no_ack}', '+3 past the ring']}}" in (tmp_path / "evidence" / "uart-crossover-pull.txt").read_text(encoding="utf-8")


def test_a_link_that_never_resumes_fails_the_pull_step_naming_it(repo_root: Path, tmp_path: Path) -> None:
    result = _real_steps(repo_root, tmp_path, _LINK_BOARD.format(resumes=False), "--only", "uart_crossover_pull_recovery", stdin="\n\n")
    assert result.returncode == 1, result.stdout + result.stderr
    assert "L4 uart_crossover_pull_recovery: the link's transfers did not resume within 30s of the replug" in _block(result.stdout), result.stdout
    assert "transfers resumed after the replug: not within 30 s" in (tmp_path / "evidence" / "uart-crossover-pull.txt").read_text(encoding="utf-8")


def test_a_device_without_a_uart_link_fails_the_pull_step_before_any_instruction(repo_root: Path, tmp_path: Path) -> None:
    body = _FRAM_BOARD.format(late_s=None)  # a /status with no sensors list: no link to pull
    result = _real_steps(repo_root, tmp_path, body, "--only", "uart_crossover_pull_recovery", stdin="")
    assert result.returncode == 1, result.stdout + result.stderr
    assert "the bench device wires no uart_link pair" in _block(result.stdout), result.stdout
    assert ">>> Pull both wires" not in result.stdout


def test_a_fresh_interpreter_lists_every_manual_step(repo_root: Path, tmp_path: Path) -> None:
    # As scripts/run_manual_hardware_tests.sh starts it: a plain interpreter with nothing of pytest's path, so every step
    # module's imports (harness, buildgen) resolve on their own; listing touches no board and writes nothing.
    env = {name: value for name, value in os.environ.items() if name != "PYTHONPATH"}
    done = subprocess.run([sys.executable, str(repo_root / "tests_hardware" / "manual" / "__main__.py"), "--list"], cwd=tmp_path, env=env, capture_output=True, text=True, check=False, timeout=60)
    assert done.returncode == 0, done.stdout + done.stderr
    names = {line.split(" ", 1)[1].split(":", 1)[0] for line in done.stdout.splitlines() if line.startswith("[")}
    assert {"fram_unplug_replug_recovery", "uart_crossover_pull_recovery", "hot_unplug_replug_i2c_recovery"} <= names, done.stdout
    assert not list(tmp_path.iterdir()), "listing wrote into its working directory"
