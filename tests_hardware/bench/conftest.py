"""Bench-tier fixtures: before the first bench test the board must run the image this round built - its image record
(beside the .uf2, scripts/build_firmware.py) against the board's own GET /system build date, device and lwIP ensemble;
check_image() is the same comparison for a test that reflashes mid-session."""

import json
from pathlib import Path
from typing import TYPE_CHECKING, NoReturn, Protocol

import harness
import http_client
import micropython_overrides
import pytest

if TYPE_CHECKING:
    from collections.abc import Sequence

# @tunable l4.board_image_system_timeout_s = 10.0
_SYSTEM_TIMEOUT_S = 10.0
_REFLASH = "manual step: reflash the round's standard image (scripts/build_firmware.py), or rebuild from this tree"
_TICK_OFFSET = "the board runs the tick-offset test image"


class _SessionNote(Protocol):
    # The root conftest's session_note fixture: record_session_note() bound to this session.
    def __call__(self, text: str, *, recovery: bool = False, source: str) -> None: ...


class _StandardStateExit(Protocol):
    # The root conftest's standard_state_exit fixture: the console message, then the failed session start.
    def __call__(self, deviations: "Sequence[tuple[str, str, str, str]]") -> NoReturn: ...


def record_path(option: "str | None", bench_device: str) -> Path:
    # --image-record when given (a throwaway worktree's record), else the bench device's own beside its .uf2.
    return Path(option) if option else harness.REPO_ROOT / "build" / f"firmware-{bench_device}.json"


def load_record(path: Path) -> "dict[str, object]":
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        pytest.exit(f"no image record at {path}: build the bench image with scripts/build_firmware.py before a bench run", returncode=1)
    if not isinstance(record, dict):
        pytest.exit(f"the image record at {path} holds no JSON object: rebuild it with scripts/build_firmware.py", returncode=1)
    return record


def image_deviations(record: "dict[str, object]", build: object, bench_device: str, *, allow_rollover: bool) -> "list[tuple[str, str, str, str]]":
    # Each way the board's image differs from the record this round built, as standard-state deviations; none is repaired.
    found: list[tuple[str, str, str, str]] = []
    if record.get("device") != bench_device:
        found.append(("image device", repr(record.get("device")), repr(bench_device), _REFLASH))
    board_date = build.get("BuildDate") if isinstance(build, dict) else f"no build object ({build!r})"
    if board_date != record.get("BuildDate"):
        found.append(("image BuildDate", repr(board_date), repr(record.get("BuildDate")), _REFLASH))
    lwip, max_connections = record.get("lwip"), record.get("maxConnections")
    problems = [f"the record carries no lwip macros or maxConnections ({lwip!r}, {max_connections!r})"]
    if isinstance(lwip, dict) and all(isinstance(v, int) for v in lwip.values()) and isinstance(max_connections, int):
        problems = micropython_overrides.check_lwip_ensemble(lwip, max_connections)
    if problems:
        found.append(("image lwIP ensemble", "; ".join(problems), "no finding", _REFLASH))
    configured = harness.configured_max_connections(bench_device)
    if max_connections != configured:
        found.append(("image maxConnections", repr(max_connections), f"{configured} (this tree's device TOML)", _REFLASH))
    overrides = record.get("overrides")
    if isinstance(overrides, list) and micropython_overrides.TICK_OFFSET_DIR_NAME in overrides and not allow_rollover:
        found.append(("tick-offset test image", _TICK_OFFSET, "the round's standard image", "manual step: reflash the round's standard image"))
    return found


def check_image(dut_ip: str, record: "dict[str, object]", *, allow_rollover: bool = False) -> "list[tuple[str, str, str, str]]":
    # The board's GET /system build against the record, strict: anything but a 200 object is itself a deviation.
    res = http_client.fetch(dut_ip, 80, "GET", "/system", timeout_s=_SYSTEM_TIMEOUT_S)
    try:
        body = res.json() if res.status_code == 200 else None
    except (ValueError, TypeError):  # no JSON, or a JSON value other than an object
        body = None
    build = body.get("build") if isinstance(body, dict) else f"GET /system {res.status_code} {res.body[:80]!r}"
    return image_deviations(record, build, harness.bench_device(), allow_rollover=allow_rollover)


@pytest.fixture(scope="session", autouse=True)
def board_image(dut_ip: str, bench_device_name: str, request: pytest.FixtureRequest, standard_state_exit: _StandardStateExit, session_note: _SessionNote) -> "dict[str, object]":
    path = record_path(request.config.getoption("--image-record"), bench_device_name)
    record = load_record(path)
    deviations = check_image(dut_ip, record, allow_rollover=request.config.getoption("--allow-multi-day-rollover"))
    if deviations:
        standard_state_exit(deviations)
    which = f"overrides {record.get('overrides')!r}, uartCrc {record.get('uartCrc')!r}, BuildDate {record.get('BuildDate')!r}"
    if record.get("dirty") is True:
        session_note(f"local-only image: revert after this round ({which})", source="board_image")
    else:
        session_note(f"image: {which}", source="board_image")
    return record
