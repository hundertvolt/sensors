"""Shared fixtures for tests_scripts/ (SPECIFICATION.md Part B.11's build-chain verification).
See CLAUDE.md's "Code quality tooling" for why this suite runs under CPython/pytest rather than
the real MicroPython Unix-port interpreter tests/ uses (SPECIFICATION.md Part E.1)."""

import fcntl
import subprocess
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING

import pytest
from _script_loader import load_script_module

if TYPE_CHECKING:
    from collections.abc import Generator, Iterator

REPO_ROOT = Path(__file__).resolve().parent.parent


def _exit_fails_the_test() -> "Generator[None, None, None]":
    # A pytest.exit() reached inside one test (a bench conftest function under test, say) would end the whole tier with
    # every later test unrun and one trailing line to show it: it fails that test, and the session goes on.
    try:
        return (yield)
    except pytest.exit.Exception as exc:
        pytest.fail(f"pytest.exit() inside a test ends the session with every later test unrun: {exc.msg}", pytrace=False)


@pytest.fixture(scope="session", autouse=True)
def _reclaim_leaked_device_fixtures() -> None:
    # Reclaims any `devices/zz_test_*.toml` a KILLED earlier run left behind, once, before any test
    # runs - race-free by construction, since nothing has created one yet at session start (a test
    # globbing the live tree could only tell leak from legitimate fixture by racing it).
    for stale in sorted((REPO_ROOT / "devices").glob("zz_test_*.toml")):
        stale.unlink()
        print(f"reclaimed leaked live-tree device fixture: {stale.name}")


def _unix_port(*args: str) -> Path:
    # A path scripts/_unix_port.sh prints, the one reader of PICO_TOOLCHAIN_DIR; its refusal fails the test, never skips.
    done = subprocess.run(["/bin/bash", str(REPO_ROOT / "scripts" / "_unix_port.sh"), *args], cwd=REPO_ROOT, capture_output=True, text=True, timeout=60, check=False)
    if done.returncode != 0:
        pytest.fail(done.stderr.strip() or f"scripts/_unix_port.sh {' '.join(args)} exited {done.returncode}")
    return Path(done.stdout.strip())


@pytest.fixture(scope="session")
def ci_suite(repo_root: Path) -> ModuleType:
    # scripts/_digital_twin_ci_suite.py as a real module - a standalone `uv run`-style script, not a
    # package member, so its pure helpers are only reachable through the loader. Session-scoped and
    # shared, so the three test files exercising it execute the module once between them, not once each.
    return load_script_module(repo_root / "scripts" / "_digital_twin_ci_suite.py", "_digital_twin_ci_suite")


@pytest.fixture(scope="session")
def micropython_bin() -> "Iterator[Path]":
    # The standard build through the one probe: a missing one or one of another build flavour fails every test that needs
    # it, never skips it. The toolchain lock is held shared for the session, so a setup cannot rebuild the binary under
    # the twins this tier boots; a setup holding it already fails the session's first use, naming it (agent, 2026-10-15).
    path = _unix_port("check", "standard")
    toolchain = path.parents[4]
    with (toolchain / ".toolchain.lock").open("a+", encoding="utf-8") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_SH | fcntl.LOCK_NB)
        except BlockingIOError:
            lock.seek(0)
            holder = lock.readline().strip() or "unknown"
            pytest.fail(f"error: the toolchain at {toolchain} is in use by a setup or firmware build (pid {holder}, holding {toolchain / '.toolchain.lock'}) - wait for it to finish, or use another PICO_TOOLCHAIN_DIR")
        yield path
@pytest.fixture(scope="session")
def micropython_dir() -> Path:
    # The toolchain's MicroPython checkout, where scripts/_unix_port.sh puts the toolchain (its standard binary's
    # parents[3]) - scripts/test.sh and CI provision a real one before this suite runs (build_stage_dir()'s rp2.py copy).
    return _unix_port("unix_port_bin", "standard").parents[3]


def pytest_configure(config: pytest.Config) -> None:
    # Some tests here load bench modules, so their marks must be known under --strict-markers too:
    # tests_hardware/markers.py is the one table both tiers register.
    load_script_module(REPO_ROOT / "tests_hardware" / "markers.py", "_tests_hardware_markers").register(config)


@pytest.hookimpl(wrapper=True)
def pytest_runtest_call(item: pytest.Item) -> "Generator[None, None, None]":
    del item
    return (yield from _exit_fails_the_test())


@pytest.hookimpl(wrapper=True)
def pytest_runtest_setup(item: pytest.Item) -> "Generator[None, None, None]":
    del item
    return (yield from _exit_fails_the_test())


@pytest.hookimpl(wrapper=True)
def pytest_runtest_teardown(item: pytest.Item, nextitem: "pytest.Item | None") -> "Generator[None, None, None]":
    del item, nextitem
    return (yield from _exit_fails_the_test())


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return REPO_ROOT


