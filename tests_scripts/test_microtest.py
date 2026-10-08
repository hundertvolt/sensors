"""tests/microtest.py's contract, which scripts/test.sh's summary reads: a skip is reported as one,
the closing line counts passed, failed and skipped, and a file that collects no test_* function
fails instead of passing with nothing checked. Run under the real Unix port, as tests/ is."""

import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _run(micropython_bin: Path, tmp_path: Path, source: str) -> subprocess.CompletedProcess[str]:
    test_file = tmp_path / "test_case.py"
    test_file.write_text(source + '\n\nif __name__ == "__main__":\n    import microtest\n\n    microtest.run(globals())\n')
    env = {**os.environ, "MICROPYPATH": f"{REPO_ROOT / 'tests'}:.frozen"}
    return subprocess.run([str(micropython_bin), str(test_file)], cwd=tmp_path, env=env, capture_output=True, text=True, check=False, timeout=60)


def test_a_skip_a_pass_and_a_failure_are_each_reported_and_counted(micropython_bin: Path, tmp_path: Path) -> None:
    done = _run(
        micropython_bin,
        tmp_path,
        "import microtest\n\n\ndef test_a_pass():\n    pass\n\n\ndef test_b_fail():\n    assert False, 'boom'\n\n\ndef test_c_skip():\n    raise microtest.Skip('needs a board')\n",
    )
    lines = done.stdout.splitlines()
    assert "PASS test_a_pass" in lines
    assert "FAIL test_b_fail:" in lines
    assert "SKIP test_c_skip: needs a board" in lines
    assert lines[-1] == "1/3 passed, 1 failed, 1 skipped", done.stdout
    assert done.returncode == 1


def test_a_skip_alone_is_not_a_failure(micropython_bin: Path, tmp_path: Path) -> None:
    done = _run(micropython_bin, tmp_path, "import microtest\n\n\ndef test_a_pass():\n    pass\n\n\ndef test_c_skip():\n    raise microtest.Skip('not here')\n")
    assert done.stdout.splitlines()[-1] == "1/2 passed, 0 failed, 1 skipped", done.stdout
    assert done.returncode == 0


def test_a_file_with_no_test_function_fails(micropython_bin: Path, tmp_path: Path) -> None:
    done = _run(micropython_bin, tmp_path, "def helper():\n    pass\n")
    assert done.stdout.splitlines()[-1] == "0/0 passed, 0 failed, 0 skipped - no test_* function collected", done.stdout
    assert done.returncode == 1


def test_the_pc_report_is_installed_first_and_prints_a_detached_task_dying_of_memory(micropython_bin: Path, tmp_path: Path) -> None:
    # The memory gate greps this output: a task that died of an exhausted heap, unawaited, must reach it with the
    # interpreter's own wording, whatever the firmware's DebugLevel (SPECIFICATION.md Part I.4(e)).
    done = _run(
        micropython_bin,
        tmp_path,
        "import asyncio\nimport micropython\nimport sys\n\n\n"
        "async def _dies():\n    micropython.heap_lock()\n    try:\n        bytearray(16)\n    finally:\n        micropython.heap_unlock()\n\n\n"
        "def test_a_detached_death():\n"
        "    assert asyncio.get_event_loop().get_exception_handler() is sys.modules['unix_port_unretrieved_report'].report_unretrieved\n\n"
        "    async def scenario():\n        task = asyncio.create_task(_dies())\n        for _ in range(4):\n            await asyncio.sleep(0)\n        assert task.done()\n\n"
        "    asyncio.run(scenario())\n",
    )
    lines = done.stdout.splitlines()
    assert "UNRETRIEVED TASK EXCEPTION: Task exception wasn't retrieved" in lines, done.stdout
    assert "MemoryError: memory allocation failed, heap is locked" in lines, done.stdout
    assert lines[-1] == "1/1 passed, 0 failed, 0 skipped", done.stdout
    assert done.returncode == 0
