"""The bench link suite in the UART link's CRC16 mode (owner, 2026-09-30): the bench TOML copied with crc = "crc16" on
both link ends, built beside the round's image, flashed, the three API-load link checks run, and the round's own image
flashed back - two flash cycles, so behind flash_cycle; the no-CRC run is test_uart_link_under_api_load.py itself."""

import json
import re
import subprocess
import time
from typing import TYPE_CHECKING

import _load
import harness
import pytest
import tomllib
from error_log_helpers import save_errcount
from test_uart_link_under_api_load import check_link_healthy_under_load, check_overload_does_not_corrupt, check_transfers_under_load

if TYPE_CHECKING:
    from pathlib import Path

    from bench_control import BenchBridge
    from harness import Board

COVERS_TWIN_SCENARIOS: tuple[str, ...] = ("uart_link",)

_CRC_MODE = "crc16"
_LINK_DRIVER = re.compile(r'^driver = "uart_link"\n', re.MULTILINE)
# A firmware build from scratch on the bench host: minutes, never hours.
# @tunable l4.uart_link_crc16_build_timeout_s = 1800.0
_BUILD_TIMEOUT_S = 1800.0
# @tunable l4.uart_link_crc16_serving_timeout_s = 120.0
_SERVING_TIMEOUT_S = 120.0
# Two polls one exercise period or more apart, after the board is serving the round's image again.
# @tunable l4.uart_link_crc16_failure_poll_gap_s = 3.0
_FAILURE_POLL_GAP_S = 3.0


@pytest.mark.flash_cycle
def test_the_link_suite_runs_on_a_crc16_image(board: "Board", bench: "BenchBridge", dut_ip: str, bench_device_name: str, tmp_path: "Path", request: pytest.FixtureRequest) -> None:
    if not request.config.getoption("--allow-flash-cycle"):
        pytest.skip("flashes a CRC16 image and the round's image back - pass --allow-flash-cycle to deliberately run it")
    # The FRAM evidence first: a reflash is a clearing path (CLAUDE.md's FRAM rule).
    reason = request.node.name
    save_errcount(dut_ip, reason)
    harness.save_fram_raw(board, reason)
    round_uf2, round_record = _load.round_image(request)
    uf2 = tmp_path / f"firmware-{bench_device_name}-{_CRC_MODE}.uf2"
    record = _build(bench_device_name, _crc16_toml(bench_device_name, tmp_path), uf2)
    flashed = False
    try:
        flashed = True
        harness.reflash(board, uf2)
        harness.wait_until(lambda: _load.serving(dut_ip), timeout_s=_SERVING_TIMEOUT_S, description="the CRC16 image serving")
        assert _load.image_deviations(request, dut_ip, record) == [], f"the board does not run the CRC16 image just flashed: {_load.image_deviations(request, dut_ip, record)}"
        check_link_healthy_under_load(dut_ip, reason)
        check_transfers_under_load(dut_ip)
        check_overload_does_not_corrupt(dut_ip, reason)
    finally:
        if flashed:
            harness.reflash(board, round_uf2)  # the round's own image, unchanged: a rebuild would carry a new build date
            harness.wait_until(lambda: _load.serving(dut_ip), timeout_s=_SERVING_TIMEOUT_S, description="the round's image serving again")
            assert _load.image_deviations(request, dut_ip, round_record) == [], f"the board is not back on the round's image: {_load.image_deviations(request, dut_ip, round_record)}"
            _assert_no_link_failure(dut_ip)


def _assert_no_link_failure(dut_ip: str) -> None:
    # The standard image's link answers again: UARTLINK.Failures 0 on two polls an exercise period apart.
    for poll in range(2):
        if poll:
            time.sleep(_FAILURE_POLL_GAP_S)
        sensors = _load.as_object(_load.get_object(dut_ip, "/status").get("sensors"), "GET /status sensors")
        link = _load.as_object(sensors.get("UARTLINK"), "GET /status sensors.UARTLINK")
        assert link.get("Failures") == 0, f"the link fails on the round's image after the CRC16 run: {link!r}"


def _build(device: str, toml: "Path", uf2: "Path") -> "dict[str, object]":
    # scripts/build_firmware.py from that copy, into tmp_path: the round's own image and record stay untouched.
    argv = ["uv", "run", "--no-sync", "scripts/build_firmware.py", device, "--device-toml", str(toml), "--output", str(uf2)]
    proc = subprocess.run(argv, cwd=harness.REPO_ROOT, capture_output=True, text=True, timeout=_BUILD_TIMEOUT_S, check=False)  # argv from repo paths, no shell
    assert proc.returncode == 0, f"building the CRC16 image failed (exit {proc.returncode}):\n{proc.stdout[-2000:]}\n{proc.stderr[-2000:]}"
    record = json.loads(uf2.with_suffix(".json").read_text(encoding="utf-8"))
    crc = record.get("uartCrc") if isinstance(record, dict) else None
    assert isinstance(record, dict) and isinstance(crc, dict) and crc and set(crc.values()) == {_CRC_MODE}, f"the CRC16 image's record names uartCrc {crc!r}"
    return record


def _crc16_toml(device: str, directory: "Path") -> "Path":
    # The bench TOML with crc = "crc16" on every uart_link end, named <device>.toml as build_firmware.py requires.
    source = harness.device_toml(device).read_text(encoding="utf-8")
    assert not re.search(r"^crc\s*=", source, re.MULTILINE), f"{device}.toml already sets a crc: this test flips the default mode only"
    text, count = _LINK_DRIVER.subn(f'driver = "uart_link"\ncrc = "{_CRC_MODE}"\n', source)
    links = [i for i in tomllib.loads(text).get("instance", []) if isinstance(i, dict) and i.get("driver") == "uart_link"]
    assert count == len(_load.instance_loggers("uart_link")) == len(links) and all(link.get("crc") == _CRC_MODE for link in links), f"the copy sets crc on {count} of the bench TOML's uart_link ends"
    path = directory / f"{device}.toml"
    path.write_text(text, encoding="utf-8")
    return path
