"""tests/microtest.py's per-test reset: registered hooks, the restored sys.path and gc.threshold(), the parked-task
check and the one-way product flags. Each case runs a small test file of its own in a child interpreter, since
microtest.run() always ends its process; the child's lines and exit status are what is asserted."""

import os
import sys

from _tmp_scratch import TmpScratch

_scratch = TmpScratch("microtest_hooks")

_TRAILER = '\n\nif __name__ == "__main__":\n    import microtest\n\n    microtest.run(globals())\n'


def _run_child(source: str) -> "tuple[int, list[str]]":
    # One test file in a fresh interpreter: (its exit code, its output lines). os.system() returns the wait status.
    where = _scratch.dir()
    script = where + "case.py"
    out = where + "out.txt"
    with open(script, "w") as f:
        f.write(source + _TRAILER)
    binary = sys.executable  # type: ignore[attr-defined]  # the Unix port's sys has it; the rp2 board stub does not
    status = os.system(binary + " " + script + " > " + out + " 2>&1")
    with open(out) as f:
        lines = f.read().split("\n")
    assert status & 0x7F == 0, f"the child died of signal {status & 0x7F}: {lines}"
    return status >> 8, lines


def test_a_hook_runs_after_every_test_and_one_that_raises_fails_the_test_it_follows() -> None:
    code, lines = _run_child(
        "import microtest\n\n_calls = []\n\n\n"
        "def _hook():\n    _calls.append(1)\n    if len(_calls) == 2:\n        raise ValueError('hook refused')\n\n\n"
        "microtest.after_each(_hook)\n\n\n"
        "def test_a():\n    pass\n\n\ndef test_b():\n    pass\n\n\n"
        "def test_c():\n    assert len(_calls) == 2, _calls\n",
    )
    assert "PASS test_a" in lines, lines
    assert "FAIL test_b: teardown: ValueError('hook refused',)" in lines, lines
    assert "PASS test_c" in lines, lines
    assert "2/3 passed, 1 failed, 0 skipped" in lines, lines
    assert code == 1


def test_sys_path_and_the_gc_threshold_are_back_after_each_test_in_either_order() -> None:
    # The same two tests in both run orders (microtest runs them sorted by name): neither may see the other's change.
    mutate = "    sys.path.append('zz_hook_probe')\n    gc.threshold(4096)\n"
    check = "    assert 'zz_hook_probe' not in sys.path, sys.path\n    assert gc.threshold() == _START, gc.threshold()\n"
    head = "import gc\nimport sys\n\n_START = gc.threshold()\n\n\n"
    for first, second in ((mutate, check), (check, mutate)):
        code, lines = _run_child(head + "def test_a():\n" + first + "\n\ndef test_b():\n" + second + "\n\ndef test_c():\n" + check)
        assert "3/3 passed, 0 failed, 0 skipped" in lines, lines
        assert code == 0


def test_a_test_leaving_tasks_parked_fails_and_the_next_test_finds_the_scheduler_empty() -> None:
    # Three sleepers on the task queue and a flag waiter on the stream queue, none cancelled by the test itself.
    code, lines = _run_child(
        "import asyncio\nimport asyncio.core as core\n\n\n"
        "async def _sleeper():\n    await asyncio.sleep(3600)\n\n\n"
        "def test_a_parks_four():\n"
        "    async def main():\n"
        "        for _ in range(3):\n            asyncio.create_task(_sleeper())\n"
        "        asyncio.create_task(asyncio.ThreadSafeFlag().wait())\n"
        "        await asyncio.sleep(0)\n\n"
        "    asyncio.run(main())\n\n\n"
        "def test_b_finds_it_empty():\n"
        "    assert core._task_queue.peek() is None\n    assert not core._io_queue.map\n",
    )
    assert "FAIL test_a_parks_four: left a task parked on the scheduler" in lines, lines
    assert "PASS test_b_finds_it_empty" in lines, lines
    assert "1/2 passed, 1 failed, 0 skipped" in lines, lines
    assert code == 1


def test_a_failed_test_that_also_parks_a_task_is_counted_once() -> None:
    code, lines = _run_child(
        "import asyncio\n\n\n"
        "async def _sleeper():\n    await asyncio.sleep(3600)\n\n\n"
        "def test_a():\n"
        "    async def main():\n        asyncio.create_task(_sleeper())\n        await asyncio.sleep(0)\n\n"
        "    asyncio.run(main())\n    assert False, 'body failed'\n",
    )
    assert "FAIL test_a:" in lines, lines
    assert "FAIL test_a: left a task parked on the scheduler" in lines, lines
    assert "0/1 passed, 1 failed, 0 skipped" in lines, lines
    assert code == 1


def test_a_base_exception_ending_a_loop_leaves_no_running_task_for_the_next_test() -> None:
    # Such an escape leaves asyncio's running-task slot set; a test is synchronous scope, so the next one starts clear.
    code, lines = _run_child(
        "import asyncio\nimport asyncio.core as core\n\n\n"
        "class _Stop(BaseException):\n    pass\n\n\n"
        "async def _stops():\n    raise _Stop\n\n\n"
        "def test_a_escapes():\n    try:\n        asyncio.run(_stops())\n    except _Stop:\n        pass\n\n\n"
        "def test_b_starts_clear():\n    assert core.cur_task is None, core.cur_task\n",
    )
    assert "2/2 passed, 0 failed, 0 skipped" in lines, lines
    assert code == 0


def test_the_pre_sync_timestamp_flag_is_back_to_its_boot_value_after_each_test() -> None:
    code, lines = _run_child(
        "import asy_base_classes\n\n\n"
        "def test_a_syncs():\n    asy_base_classes.set_utc_valid()\n\n\n"
        "def test_b_sees_boot_state():\n    assert asy_base_classes._utc_valid is False\n",
    )
    assert "2/2 passed, 0 failed, 0 skipped" in lines, lines
    assert code == 0


def test_a_test_leaving_the_fatal_report_flag_set_fails_and_the_next_test_finds_it_clear() -> None:
    # Each of the first two records a real C-stack overflow: the one leaving the flag set fails, the one clearing its own
    # passes; the third, run after both, finds the flag at its boot value.
    code, lines = _run_child(
        "import asy_print_log\n\n\n"
        "def _dive(depth):\n    return _dive(depth + 1)\n\n\n"
        "def _record():\n    try:\n        _dive(0)\n    except RuntimeError as e:\n        asy_print_log.report_if_fatal(e)\n"
        "    assert asy_print_log.fatal_reported() is True\n\n\n"
        "def test_a_leaves_it_set():\n    _record()\n\n\n"
        "def test_b_clears_its_own():\n    assert asy_print_log.fatal_reported() is False\n    _record()\n    asy_print_log._fatal = False\n\n\n"
        "def test_c_sees_boot_state():\n    assert asy_print_log.fatal_reported() is False\n",
    )
    assert "FAIL test_a_leaves_it_set: left the C-stack fatal flag set" in lines, lines
    assert "PASS test_b_clears_its_own" in lines, lines
    assert "PASS test_c_sees_boot_state" in lines, lines
    assert "2/3 passed, 1 failed, 0 skipped" in lines, lines
    assert code == 1


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
