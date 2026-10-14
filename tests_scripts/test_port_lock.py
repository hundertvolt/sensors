"""The product-fixed port lock, scripts/_port_lock.sh: a port a live runner holds refuses every other runner at once,
naming the holder; a dead holder's lock is taken over; the holder's own descendants pass; a runner removes only its own
locks, on every exit path. Every lock here lives under tmp_path, never the runtime dir a real suite's runner uses."""

import errno
import os
import shlex
import shutil
import signal
import subprocess
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
_LOCK_LIB = REPO_ROOT / "scripts" / "_port_lock.sh"
_CHAIN_VARS = ("SENSORS_PORT_LOCK_OWNER", "SENSORS_PORT_LOCKS_HELD")
_RACERS = 6
# Each runner's arguments and the product-fixed ports it holds for its whole run, in the order it takes them.
_RUNNERS: dict[str, tuple[tuple[str, ...], tuple[int, ...]]] = {
    "scripts/test.sh": ((), (53,)),
    "scripts/run_digital_twin_ci.sh": ((), (53, 18080)),
    "scripts/run_unix_port_integration.sh": (("--device", "fixture_device"), (53,)),
}
_RUNNER_PORTS = [(runner, port) for runner, (_, ports) in _RUNNERS.items() for port in ports]


def _child(*lines: str) -> str:
    # A nested runner: a bash -c line the outer script runs, inheriting its exported chain.
    return f"/bin/bash -c {shlex.quote(_script(*lines))}"


def _dead_pid() -> int:
    done = subprocess.Popen(["/bin/true"])
    done.wait(timeout=10)
    return done.pid


def _end_normally(proc: subprocess.Popen[str]) -> int:
    assert proc.stdin is not None
    proc.stdin.close()
    return proc.wait(timeout=10)


def _env(runtime_dir: Path) -> dict[str, str]:
    # The chain this pytest process may inherit from scripts/test.sh is dropped: every shell here starts unrelated.
    env = {name: value for name, value in os.environ.items() if name not in _CHAIN_VARS}
    env["XDG_RUNTIME_DIR"] = str(runtime_dir)
    return env


def _held(port: int, runner: str, pid: int) -> str:
    return f"port {port} is held by {runner} (pid {pid}) - run the suites one after the other (CLAUDE.md)"


@contextmanager
def _holder(runtime_dir: Path, ports: tuple[int, ...], runner: str) -> Iterator[tuple[subprocess.Popen[str], int]]:
    proc = _start_holder(runtime_dir, ports, runner)
    try:
        assert proc.stdout is not None
        line = proc.stdout.readline()
        assert line.startswith("took "), f"the holder did not take {ports}: {line!r} {proc.stderr.read() if proc.stderr else ''}"
        yield proc, int(line.split()[1])
    finally:
        _stop(proc)


def _lock(runtime_dir: Path, port: int) -> Path:
    return runtime_dir / f"sensors-port-{port}.lock"


def _open_writer(fifo: Path, reader: subprocess.Popen[str]) -> int:
    # Opens the FIFO's write end once the reader is blocked on it; ENXIO until then.
    deadline = time.monotonic() + 10
    while True:
        try:
            return os.open(fifo, os.O_WRONLY | os.O_NONBLOCK)
        except OSError as e:
            if e.errno != errno.ENXIO or reader.poll() is not None or time.monotonic() > deadline:
                raise
            time.sleep(0.01)


@contextmanager
def _other_process() -> Iterator[int]:
    # A live process that is no runner's ancestor or descendant: the holder of a planted lock.
    proc = subprocess.Popen(["/bin/sleep", "60"], text=True)
    try:
        yield proc.pid
    finally:
        _stop(proc)


def _plant(runtime_dir: Path, port: int, pid: int, runner: str) -> None:
    # A lock exactly as another runner leaves it: the directory with its pid and runner files.
    lock = _lock(runtime_dir, port)
    lock.mkdir()
    (lock / "pid").write_text(f"{pid}\n", encoding="utf-8")
    (lock / "runner").write_text(f"{runner}\n", encoding="utf-8")


def _recorded(runtime_dir: Path, port: int) -> tuple[str, str]:
    lock = _lock(runtime_dir, port)
    return (lock / "pid").read_text(encoding="utf-8").strip(), (lock / "runner").read_text(encoding="utf-8").strip()


def _run(runtime_dir: Path, *lines: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["/bin/bash", "-c", _script(*lines)], env=_env(runtime_dir), capture_output=True, text=True, check=False, timeout=30)


def _run_runner(tmp_path: Path, runner: str) -> tuple[subprocess.CompletedProcess[str], Path, Path]:
    # Runs the runner's copy with the toolchain missing; returns the run, its tree and the uv call log.
    root, calls = _runner_tree(tmp_path, runner)
    stub_bin = tmp_path / "stub_bin"
    env = {**_env(tmp_path / "runtime"), "PATH": f"{stub_bin}:{os.environ['PATH']}", "HOME": str(tmp_path), "PICO_TOOLCHAIN_DIR": str(tmp_path / "no_toolchain")}
    args = _RUNNERS[runner][0]
    done = subprocess.run(["/bin/bash", str(root / runner), *args], cwd=root, env=env, capture_output=True, text=True, check=False, timeout=60)
    return done, root, calls


def _runner_tree(tmp_path: Path, runner: str) -> tuple[Path, Path]:
    # A copy of the runner beside the lock library in a throwaway tree, with a scratch file its sweeps would
    # remove; every uv call is logged with the locks held at that moment and fails, ending the run there.
    root = tmp_path / "repo"
    for rel in (runner, "scripts/_port_lock.sh"):
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO_ROOT / rel, root / rel)
    (root / "devices").mkdir()
    (root / "devices" / "fixture_device.toml").write_text("# fixture\n", encoding="utf-8")
    (root / "tests" / "_tmp").mkdir(parents=True)
    (root / "tests" / "_tmp" / "in_use").write_text("held by a concurrently running test file\n", encoding="utf-8")
    (tmp_path / "runtime").mkdir(exist_ok=True)
    calls = tmp_path / "uv.calls"
    stub_bin = tmp_path / "stub_bin"
    stub_bin.mkdir()
    (stub_bin / "uv").write_text(f'#!/usr/bin/env bash\necho "uv $* | held: $(LC_ALL=C ls "$XDG_RUNTIME_DIR" | tr "\\n" " ")" >>{shlex.quote(str(calls))}\nexit 1\n', encoding="utf-8")
    (stub_bin / "uv").chmod(0o755)
    return root, calls


def _script(*lines: str) -> str:
    return "\n".join(["set -euo pipefail", f"source {shlex.quote(str(_LOCK_LIB))}", "trap port_lock_release_all EXIT", *lines])


def _start_holder(runtime_dir: Path, ports: tuple[int, ...], runner: str) -> subprocess.Popen[str]:
    # Takes its ports, prints "took <pid>" and blocks on stdin; closing stdin ends it normally.
    takes = [f"port_lock_take {port} {shlex.quote(runner)}" for port in ports]
    script = _script(*takes, 'echo "took $$"', "read -r _ || true")
    return subprocess.Popen(["/bin/bash", "-c", script], env=_env(runtime_dir), stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)


def _stop(proc: subprocess.Popen[str]) -> None:
    if proc.poll() is None:
        proc.kill()
    proc.wait(timeout=10)


def test_a_second_runner_on_a_held_port_exits_1_naming_the_holder(tmp_path: Path) -> None:
    with _holder(tmp_path, (53,), "first-runner") as (holder, holder_pid):
        second = _run(tmp_path, "port_lock_take 53 second-runner", "echo proceeded")
        assert second.returncode == 1, second
        assert second.stderr.strip() == _held(53, "first-runner", holder_pid)
        assert "proceeded" not in second.stdout
        assert _recorded(tmp_path, 53) == (str(holder_pid), "first-runner")
        assert _end_normally(holder) == 0
    assert not _lock(tmp_path, 53).exists(), "the holder's EXIT trap left its lock behind"


def test_a_planted_lock_of_a_live_unrelated_process_refuses_the_taker(tmp_path: Path) -> None:
    with _other_process() as other:
        _plant(tmp_path, 53, other, "scripts/run_digital_twin_ci.sh")
        taker = _run(tmp_path, "port_lock_take 53 scripts/test.sh", "echo proceeded")
        assert (taker.returncode, taker.stderr.strip(), taker.stdout) == (1, _held(53, "scripts/run_digital_twin_ci.sh", other), "")
        assert _recorded(tmp_path, 53) == (str(other), "scripts/run_digital_twin_ci.sh")


def test_a_dead_holders_lock_is_taken_over(tmp_path: Path) -> None:
    dead = _dead_pid()
    _plant(tmp_path, 53, dead, "crashed-runner")
    taker = _run(tmp_path, "port_lock_take 53 new-runner", 'cat "$XDG_RUNTIME_DIR/sensors-port-53.lock/pid"; echo "me $$"')
    assert taker.returncode == 0, taker
    recorded, me = taker.stdout.split("\n")[:2]
    assert recorded == me.removeprefix("me "), "the taken-over lock does not record its new holder"
    assert not _lock(tmp_path, 53).exists(), "the new holder's EXIT trap left the lock behind"


def test_a_taker_that_read_a_dead_pid_leaves_a_fresh_live_lock_in_place(tmp_path: Path) -> None:
    # The taker reads a dead pid, then finds another runner's fresh lock at the path: it refuses rather than remove
    # it. The pid file is a FIFO, so the lock is swapped while the taker is still inside its read.
    dead = _dead_pid()
    lock = _lock(tmp_path, 53)
    lock.mkdir()
    (lock / "runner").write_text("crashed-runner\n", encoding="utf-8")
    os.mkfifo(lock / "pid")
    with _other_process() as other:
        script = _script("port_lock_take 53 late-runner", "echo proceeded")
        taker = subprocess.Popen(["/bin/bash", "-c", script], env=_env(tmp_path), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            writer = _open_writer(lock / "pid", taker)
            os.write(writer, f"{dead}\n".encode())
            lock.rename(tmp_path / "swapped-out")
            _plant(tmp_path, 53, other, "fresh-runner")
            os.close(writer)
            out, err = taker.communicate(timeout=30)
        finally:
            _stop(taker)
        assert (taker.returncode, err.strip(), out) == (1, _held(53, "fresh-runner", other), "")
        assert _recorded(tmp_path, 53) == (str(other), "fresh-runner")


def test_a_lock_left_without_a_pid_is_taken_over_after_the_bounded_wait(tmp_path: Path) -> None:
    # A holder killed between its mkdir and its pid write leaves an empty directory behind.
    _lock(tmp_path, 53).mkdir()
    taker = _run(tmp_path, "port_lock_take 53 new-runner", 'cat "$XDG_RUNTIME_DIR/sensors-port-53.lock/runner"')
    assert (taker.returncode, taker.stdout.strip()) == (0, "new-runner"), taker


def test_a_pid_written_during_the_wait_is_honoured(tmp_path: Path) -> None:
    # The holder is between its mkdir and its pid write when the taker looks: the taker waits for the pid.
    with _other_process() as other:
        lock = _lock(tmp_path, 53)
        lock.mkdir()
        writer = f"sleep 0.2; printf 'slow-runner\\n' > {shlex.quote(str(lock / 'runner'))}; printf '{other}\\n' > {shlex.quote(str(lock / 'pid'))}"
        late = subprocess.Popen(["/bin/bash", "-c", writer])
        try:
            taker = _run(tmp_path, "port_lock_take 53 new-runner")
        finally:
            late.wait(timeout=10)
        assert (taker.returncode, taker.stderr.strip()) == (1, _held(53, "slow-runner", other))


def test_a_descendant_of_the_owner_passes_without_retaking(tmp_path: Path) -> None:
    child = _child("port_lock_take 53 child-runner", "echo child-took")
    done = _run(tmp_path, "port_lock_take 53 parent-runner", child, 'cat "$XDG_RUNTIME_DIR/sensors-port-53.lock/pid"; echo "parent $$"')
    assert done.returncode == 0, done
    took, recorded, parent = done.stdout.split("\n")[:3]
    assert took == "child-took"
    assert recorded == parent.removeprefix("parent "), "the child retook the parent's lock, or its exit released it"


def test_a_grandchild_passes_after_its_parent_took_a_port_of_its_own(tmp_path: Path) -> None:
    grandchild = _child("port_lock_take 53 grandchild-runner", "port_lock_take 18080 grandchild-runner", "echo grandchild-took")
    child = _child("port_lock_take 18080 child-runner", grandchild)
    done = _run(tmp_path, "port_lock_take 53 parent-runner", child)
    assert (done.returncode, done.stdout.strip()) == (0, "grandchild-took"), done


def test_the_inherited_chain_does_not_open_a_port_an_unrelated_process_holds(tmp_path: Path) -> None:
    with _other_process() as other:
        _plant(tmp_path, 53, other, "other-runner")
        child = _child("port_lock_take 53 child-runner", "echo child-took")
        done = _run(tmp_path, "port_lock_take 18080 parent-runner", child)
        assert (done.returncode, done.stderr.strip(), done.stdout) == (1, _held(53, "other-runner", other), "")


def test_a_runner_retaking_its_own_port_passes(tmp_path: Path) -> None:
    done = _run(tmp_path, "port_lock_take 53 one-runner", "port_lock_take 53 one-runner", "echo retook")
    assert (done.returncode, done.stdout.strip()) == (0, "retook"), done


def test_release_removes_only_the_runners_own_locks(tmp_path: Path) -> None:
    dead = _dead_pid()
    with _other_process() as other:
        _plant(tmp_path, 18080, other, "other-runner")
        _plant(tmp_path, 123, dead, "crashed-runner")
        child = _child("port_lock_release_all")
        done = _run(tmp_path, "port_lock_take 53 own-runner", child, 'test -d "$XDG_RUNTIME_DIR/sensors-port-53.lock" && echo kept-by-child', "port_lock_release_all", "trap - EXIT", 'ls "$XDG_RUNTIME_DIR"')
        assert done.returncode == 0, done
        assert done.stdout.split() == ["kept-by-child", "sensors-port-123.lock", "sensors-port-18080.lock"]


def test_a_refused_runner_releases_the_ports_it_took_before(tmp_path: Path) -> None:
    with _other_process() as other:
        _plant(tmp_path, 53, other, "other-runner")
        done = _run(tmp_path, "port_lock_take 18080 refused-runner", "port_lock_take 53 refused-runner")
        assert (done.returncode, done.stderr.strip()) == (1, _held(53, "other-runner", other)), done
        assert not _lock(tmp_path, 18080).exists(), "the refused runner's EXIT trap left its 18080 lock behind"


def test_a_terminated_holder_releases_its_locks(tmp_path: Path) -> None:
    with _holder(tmp_path, (53, 18080), "term-runner") as (holder, _):
        holder.send_signal(signal.SIGTERM)
        # bash runs its EXIT trap on a fatal signal, then dies of that signal.
        assert holder.wait(timeout=10) == -signal.SIGTERM
    assert not _lock(tmp_path, 53).exists()
    assert not _lock(tmp_path, 18080).exists()


@pytest.mark.parametrize("stale", [False, True], ids=["free", "stale"])
def test_racing_takers_leave_exactly_one_holder(tmp_path: Path, *, stale: bool) -> None:
    if stale:
        _plant(tmp_path, 53, _dead_pid(), "crashed-runner")
    racers = [_start_holder(tmp_path, (53,), f"racer-{n}") for n in range(_RACERS)]
    try:
        deadline = time.monotonic() + 20
        while sum(proc.poll() is None for proc in racers) > 1 and time.monotonic() < deadline:
            time.sleep(0.05)
        alive = [n for n, proc in enumerate(racers) if proc.poll() is None]
        assert len(alive) == 1, f"{len(alive)} racers hold port 53 at once"
        winner = racers[alive[0]]
        assert winner.stdout is not None
        took = winner.stdout.readline().split()
        assert took[0] == "took", took
        held = _held(53, f"racer-{alive[0]}", int(took[1]))
        for proc in racers:
            if proc is not winner:
                assert (proc.returncode, proc.stderr.read().strip() if proc.stderr else "") == (1, held)
    finally:
        for proc in racers:
            _stop(proc)


@pytest.mark.parametrize("args", ["0 r", "65536 r", "5x r", "53 ''"], ids=["zero", "too-high", "not-a-number", "no-runner"])
def test_a_malformed_take_is_a_usage_error(tmp_path: Path, args: str) -> None:
    done = _run(tmp_path, f"port_lock_take {args}", "echo proceeded")
    assert (done.returncode, done.stdout) == (2, ""), done
    assert done.stderr.startswith("error: port_lock_take"), done.stderr
    assert list(tmp_path.iterdir()) == []


def test_the_library_refuses_to_run_as_a_script(tmp_path: Path) -> None:
    done = subprocess.run(["/bin/bash", str(_LOCK_LIB)], env=_env(tmp_path), capture_output=True, text=True, check=False, timeout=30)
    assert (done.returncode, done.stderr.strip()) == (2, "error: source scripts/_port_lock.sh, do not run it")


@pytest.mark.parametrize(("runner", "port"), _RUNNER_PORTS, ids=[f"{Path(r).name}-{p}" for r, p in _RUNNER_PORTS])
def test_each_runner_refuses_a_port_a_live_process_holds_before_touching_anything(tmp_path: Path, runner: str, port: int) -> None:
    with _other_process() as other:
        (tmp_path / "runtime").mkdir()
        _plant(tmp_path / "runtime", port, other, "other-runner")
        done, root, calls = _run_runner(tmp_path, runner)
        assert (done.returncode, done.stderr.strip().splitlines()[-1:]) == (1, [_held(port, "other-runner", other)]), done.stderr
        assert not calls.exists(), f"{runner} got past its lock: {calls.read_text(encoding='utf-8')}"
        assert (root / "tests" / "_tmp" / "in_use").is_file(), f"{runner} swept tests/_tmp before taking its lock"
        assert sorted(p.name for p in (tmp_path / "runtime").iterdir()) == [f"sensors-port-{port}.lock"], "the refused runner left a lock of its own"


@pytest.mark.parametrize("runner", list(_RUNNERS))
def test_each_runner_holds_its_ports_past_the_lock_and_releases_them_on_exit(tmp_path: Path, runner: str) -> None:
    # The stub uv fails the toolchain step, the first thing past the locks: an abort under set -e.
    done, _, calls = _run_runner(tmp_path, runner)
    assert done.returncode == 1, done.stderr
    held = " ".join(sorted(f"sensors-port-{port}.lock" for port in _RUNNERS[runner][1]))
    first = calls.read_text(encoding="utf-8").splitlines()[0]
    assert first.startswith("uv run toolchain/setup_toolchain.py setup"), done.stderr
    assert first.endswith(f"| held: {held} "), f"{runner} reached its toolchain step without holding its ports: {first}"
    assert list((tmp_path / "runtime").iterdir()) == [], "the runner's exit left a lock behind"

