"""Tests scripts/_digital_twin_ci_suite.py's own state handling without a live twin: each pass keeps its state under
its logs directory and archives it before every fresh start, never deleting it (CLAUDE.md's FRAM-log rule, the twin
case), and Run 7's port 53: the interpreter's file capability read, no caller's TEST_TWIN_HOST in its twin."""

import struct
import subprocess
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

_CAP_XATTR = "security.capability"


def _ctx(ci_suite: ModuleType, logs_dir: Path) -> object:
    return ci_suite.RunContext(micropython_bin="/nonexistent", logs_dir=logs_dir, device="fixture-device", module="sensortask_fixture", wiring_plan_path=logs_dir / "plan.json", instances=(), gc_threshold=-1, routes=("/status",))


def _fake_xattr(value: "bytes | None") -> object:
    def getxattr(_path: str, name: str) -> bytes:
        assert name == _CAP_XATTR
        if value is None:
            raise OSError(61, "No data available")
        return value

    return getxattr


def test_a_pass_keeps_its_state_under_its_own_logs_directory(ci_suite: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Never digital_twin/'s manual defaults: every launch's four state paths sit in the pass's state directory.
    launched: list[Path] = []
    monkeypatch.setattr(ci_suite, "spawn", lambda _launch, *, state_dir, log_path, args: launched.append(state_dir))
    ci_suite._spawn(_ctx(ci_suite, tmp_path / "pass"), [], tmp_path / "run.log")
    assert launched == [tmp_path / "pass" / "state"]
    assert all(path.is_relative_to(tmp_path / "pass") for path in ci_suite.state_paths(launched[0]))


def test_archiving_moves_the_state_and_recreates_it_empty(ci_suite: ModuleType, tmp_path: Path) -> None:
    ctx = _ctx(ci_suite, tmp_path)
    ctx.state_dir.mkdir(parents=True)  # type: ignore[attr-defined]
    (ctx.state_dir / "fram_state.json").write_text("{}", encoding="utf-8")  # type: ignore[attr-defined]
    ci_suite._archive_state(ctx, "run5")
    assert (tmp_path / "state_archive" / "01_before_run5" / "fram_state.json").read_text(encoding="utf-8") == "{}"
    assert ctx.state_dir.is_dir() and not any(ctx.state_dir.iterdir())  # type: ignore[attr-defined]


def test_archives_are_numbered_in_order_and_never_overwrite_each_other(ci_suite: ModuleType, tmp_path: Path) -> None:
    ctx = _ctx(ci_suite, tmp_path)
    for label in ("pass start", "run10 sgp40"):
        ctx.state_dir.mkdir(parents=True, exist_ok=True)  # type: ignore[attr-defined]
        (ctx.state_dir / "scd30_state.json").write_text(label, encoding="utf-8")  # type: ignore[attr-defined]
        ci_suite._archive_state(ctx, label)
    archived = sorted(p.name for p in (tmp_path / "state_archive").iterdir())
    assert archived == ["01_before_pass_start", "02_before_run10_sgp40"]
    assert (tmp_path / "state_archive" / "01_before_pass_start" / "scd30_state.json").read_text(encoding="utf-8") == "pass start"


def test_an_empty_state_directory_is_not_archived(ci_suite: ModuleType, tmp_path: Path) -> None:
    ctx = _ctx(ci_suite, tmp_path)
    ci_suite._archive_state(ctx, "pass start")
    ci_suite._archive_state(ctx, "run5")
    assert not (tmp_path / "state_archive").exists()
    assert ctx.state_dir.is_dir()  # type: ignore[attr-defined]


def test_the_suite_has_no_deleting_clean_any_more(ci_suite: ModuleType) -> None:
    assert not hasattr(ci_suite, "_clean_state"), "the state is archived, never wiped"


def test_the_capability_helper_reads_net_bind_service_from_the_file_capability(ci_suite: ModuleType) -> None:
    # vfs_cap_data revision 2: magic with the effective flag, permitted bit 10 (CAP_NET_BIND_SERVICE), inheritable.
    granted = struct.pack("<IIIII", 0x02000001, 1 << 10, 0, 0, 0)
    assert ci_suite._has_net_bind_capability("/bin/mp", getxattr=_fake_xattr(granted)) is True


@pytest.mark.parametrize(
    "value",
    [None, struct.pack("<IIIII", 0x02000000, 1 << 10, 0, 0, 0), struct.pack("<IIIII", 0x02000001, 1 << 11, 0, 0, 0), b"\x01"],
    ids=["no capability", "not effective", "another capability", "truncated"],
)
def test_the_capability_helper_reports_absent_otherwise(ci_suite: ModuleType, value: "bytes | None") -> None:
    assert ci_suite._has_net_bind_capability("/bin/mp", getxattr=_fake_xattr(value)) is False


def test_run_7_fails_at_once_without_the_capability(ci_suite: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # A loud failure naming the cause instead of a 90 s wait for a DNS answer that cannot come.
    monkeypatch.setattr(ci_suite, "_FAILURES", [])
    monkeypatch.setattr(ci_suite, "_has_net_bind_capability", lambda _binary: False)
    monkeypatch.setattr(ci_suite, "_spawn", lambda *_a: pytest.fail("Run 7 launched a twin that cannot bind port 53"))
    ci_suite._run_7_wifi_hotspot_dns(_ctx(ci_suite, tmp_path))
    assert ci_suite._FAILURES == ["Run 7: the interpreter lacks CAP_NET_BIND_SERVICE: Run 7's DNS server cannot bind port 53 (/nonexistent)"]


def test_a_callers_twin_host_never_moves_the_twin_off_where_run_7_queries(ci_suite: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Run 7 queries the captive DNS at HOST, and the twin binds it at its own TEST_TWIN_HOST: a caller's must not reach it.
    envs: list[object] = []

    def popen(_cmd: "list[str]", **kw: object) -> object:
        envs.append(kw["env"])
        return SimpleNamespace(pid=0)

    monkeypatch.setenv("TEST_TWIN_HOST", "127.0.0.77")
    monkeypatch.setattr(subprocess, "Popen", popen)
    run = ci_suite._spawn(_ctx(ci_suite, tmp_path / "pass"), [], tmp_path / "run.log")
    run.log_file.close()
    assert len(envs) == 1 and isinstance(envs[0], dict), envs
    assert "TEST_TWIN_HOST" not in envs[0], f"the caller's TEST_TWIN_HOST={envs[0]['TEST_TWIN_HOST']!r} reached Run 7's twin: its captive DNS binds there while Run 7 queries {ci_suite.HOST}"
