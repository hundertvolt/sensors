"""The shared test doubles and readers no consumer test pins yet: the src const() reader, the fast sleep, the timer-arm
failure, the fake time sources, the FRAM manager builder, the NTP frames and server, the print recorder and the fixed
random source, each against the behaviour its former copies had."""

import asyncio
import errno
import os
import select
import socket
import struct
import time

from _async_harness import run
from _fake_time import DrivenTime, FakeTime, Rp2Gmtime, tick
from _fake_timer_arm import RaiseOnArm
from _fast_sleep import FastAsyncSleep, check_sleep_ms
from _fram_builders import make_fram_manager
from _fram_chip_fake import FakeMB85RS64V
from _generated_tree import devices
from _ntp_frames import FakeNtpServer, make_ntp_reply
from _recording_print import record_prints
from _shared_rest_roundtrip import drain_json
from _src_const import NTP_EPOCH_DELTA, py_value, src_bytes, src_const, src_consts, src_float, src_int, src_strs
from _src_schema import src_schema
from _ticks30 import TICKS_PERIOD, Ticks30Time
from _tmp_scratch import TmpScratch
from _twin_random import FixedRandom
from machine import Timer

import asy_print_log
import asy_spi_driver
from asy_print_log import PrintLogHistory, console

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from _protocols import I2CLike, UARTLike, WLANLike
    from machine import I2C, UART
    from network import WLAN

    # The fakes stand in for these boundaries: each must offer every method its protocol lists.
    def _boundaries(i2c: I2C, uart: UART, wlan: WLAN) -> "tuple[I2CLike, UARTLike, WLANLike]":
        return i2c, uart, wlan


_SRC_DIR = "src"
_scratch = TmpScratch("shared_helpers")
_NTP_PORT = 28001  # this file's own UDP port, clear of every other file's band (21000-27000, 19100-19700)


class _Holder:
    # A module stand-in whose `time` a DrivenTime replaces for the block.
    def __init__(self) -> None:
        self.time: object = time


class _BigChip(FakeMB85RS64V):
    SIZE = 0x8000


async def _refused_sleep_ms(ms: float) -> str:
    # What sleep_ms() raises for ms, or "no error" once it has slept.
    try:
        await asyncio.sleep_ms(ms)  # a float on purpose: the device refuses it
    except (TypeError, OverflowError) as e:
        return f"{type(e).__name__}: {e}"
    return "no error"


def _times(*holders: _Holder) -> "list[object]":
    return [holder.time for holder in holders]


# ---------------------------------------------------------------------------
# _src_const
# ---------------------------------------------------------------------------


def test_src_const_reads_a_folded_tuple_as_a_tuple() -> None:
    assert src_const("src/asy_webserver_service.py", "_SYSTEM_CMDS") == ("reboot", "bootloader", "mempause", "resetconfig", "erasefram")


def test_src_const_evaluates_each_value_with_the_names_bound_before_it() -> None:
    assert src_const("src/asy_bmp3xx_driver.py", "_VAL_SAMPLE_INTERVAL") == (("SampleInterval", "int", 2, 1, 3600, None),)
    assert src_const("src/asy_bmp3xx_driver.py", "_VAL_PRES_OVERS") == (("PresOvers", "int", 1, None, None, (1, 2, 4, 8, 16, 32)),)


def test_src_const_refuses_a_name_that_is_no_const() -> None:
    raised = ""
    try:
        src_const("src/asy_webserver_service.py", "_body_as_dict")
    except KeyError as e:
        raised = e.args[0]
    assert raised == "_body_as_dict is not a const() in src/asy_webserver_service.py", raised


def test_each_typed_reader_raises_on_a_value_of_another_type() -> None:
    ws = "src/asy_webserver_service.py"
    for reader, name in ((src_int, "_SYSTEM_CMDS"), (src_float, "_SYSTEM_CMDS"), (src_bytes, "_PAUSE_TIME_MAX"), (src_schema, "_PAUSE_TIME_MAX"), (src_strs, "_PAUSE_TIME_MAX"), (src_schema, "_SYSTEM_CMDS")):
        try:
            reader(ws, name)
        except TypeError as e:
            assert name in str(e) and ws in str(e), e
        else:
            raise AssertionError(name + " read without a TypeError")
    assert src_int(ws, "_PAUSE_TIME_MAX") == 3600 and src_float(ws, "_PAUSE_TIME_MAX") == 3600
    assert src_strs(ws, "_SYSTEM_CMDS") == ("reboot", "bootloader", "mempause", "resetconfig", "erasefram")
    assert src_schema("src/asy_bmp3xx_driver.py", "_VAL_SAMPLE_INTERVAL") == (("SampleInterval", "int", 2, 1, 3600, None),)

def test_src_consts_reads_each_file_once_and_every_src_const_evaluates() -> None:
    assert src_consts("src/asy_ntp_client.py") is src_consts("src/asy_ntp_client.py")
    count = 0
    for name in sorted(os.listdir(_SRC_DIR)):
        if name.endswith(".py"):
            count += len(src_consts(_SRC_DIR + "/" + name))
    assert count > 700, count  # every const() binding in src/, each evaluated without raising


def test_py_value_reads_a_host_files_literal_past_its_comment_and_refuses_an_unknown_name() -> None:
    path = _scratch.path("host.py")
    with open(path, "w") as f:
        f.write('_SIZE = 4096  # a comment # with a hash\n_TEXT = "a#b"  # the hash in the string stays\n    _SIZE = 1\n')
    assert py_value(path, "_SIZE") == 4096
    assert py_value(path, "_TEXT") == "a#b"
    raised = ""
    try:
        py_value(path, "_NOT_THERE")
    except KeyError as e:
        raised = e.args[0]
    assert raised == "_NOT_THERE is not a module-level binding in " + path, raised


def test_devices_are_the_tomls_but_a_zz_test_fixture_sorted() -> None:
    expected = sorted(name[:-5] for name in os.listdir("devices") if name.endswith(".toml"))
    assert devices() == [name for name in expected if not name.startswith("zz_test_")]
    assert devices(), "no device TOML found"


def test_the_ntp_epoch_delta_is_rfc_5905s() -> None:
    assert NTP_EPOCH_DELTA == 2208988800


# ---------------------------------------------------------------------------
# _fast_sleep
# ---------------------------------------------------------------------------


def test_fast_sleep_turns_both_sleeps_into_one_yield_and_records_each_delay() -> None:
    real_sleep, real_sleep_ms = asyncio.sleep, asyncio.sleep_ms

    async def scenario() -> "tuple[float, list[float]]":
        start = time.ticks_ms()
        await asyncio.sleep(3600)
        await asyncio.sleep_ms(250)
        return time.ticks_diff(time.ticks_ms(), start) / 1000, fast.of(asyncio.current_task())

    with FastAsyncSleep() as fast:
        elapsed, mine = run(scenario(), 5)  # bounded: an unpatched sleep would wait out the hour
    assert elapsed < 1.0
    assert mine == [3600, 0.25]
    assert (asyncio.sleep, asyncio.sleep_ms) == (real_sleep, real_sleep_ms)


def test_fast_sleep_advances_a_given_clock_by_each_slept_time() -> None:
    clock = DrivenTime()

    async def scenario() -> None:
        await asyncio.sleep(2)
        await asyncio.sleep_ms(500)

    with FastAsyncSleep(clock):
        run(scenario(), 5)
    assert clock.now == 2500


def test_fast_sleep_keeps_a_bounded_record_and_counts_what_it_dropped() -> None:
    async def scenario(count: int) -> None:
        for _ in range(count):
            await asyncio.sleep(0)

    with FastAsyncSleep() as fast:
        run(scenario(FastAsyncSleep.CAP + 3), 5)
    assert len(fast.slept) == FastAsyncSleep.CAP
    assert fast.dropped == 3


def test_fast_sleep_keeps_the_form_each_wait_was_asked_in() -> None:
    # A sleep_ms() keeps the int it was given and a sleep() keeps None there, so a wait asked in seconds never reads as
    # one asked in milliseconds, even at the same length.
    async def scenario() -> "tuple[list[int], list[float]]":
        await asyncio.sleep_ms(250)
        await asyncio.sleep(0.25)
        await asyncio.sleep(1)
        await asyncio.sleep_ms(0)
        task = asyncio.current_task()
        return fast.ms_of(task), fast.of(task)

    with FastAsyncSleep() as fast:
        asked = run(scenario(), 5)
    assert asked == ([250, 0], [0.25, 0.25, 1, 0]), asked
    assert [form for _task, _seconds, form in fast.slept] == [250, None, None, 0], fast.slept


def test_fast_sleep_refuses_a_float_sleep_ms_as_the_real_one_does() -> None:
    # The real sleep_ms() hands its delay to ticks_add(), whose mp_obj_get_int() refuses a float (extmod/asyncio/core.py:55-57,
    # extmod/modtime.c:181, v1.29.0), and MicroPython's 2.0 == 2 would let a recorded float pass an int pin.
    real = run(_refused_sleep_ms(2.0), 5)
    with FastAsyncSleep() as fast:
        stood_in = run(_refused_sleep_ms(2.0), 5)
    assert real == stood_in == "TypeError: can't convert float to int", (real, stood_in)
    assert fast.slept == [], fast.slept  # refused before it was recorded


def test_check_sleep_ms_refuses_what_the_real_sleep_ms_refuses_and_takes_an_int() -> None:
    # The one check every other stand-in runs: the real call's own exception for a float, nothing for an int or a negative.
    try:
        check_sleep_ms(2.0)  # type: ignore[arg-type]  # a float on purpose
        said = "no error"
    except TypeError as e:
        said = f"TypeError: {e}"
    assert said == run(_refused_sleep_ms(2.0), 5), said
    check_sleep_ms(5)
    check_sleep_ms(-1)  # sleep_ms() clamps a negative delay to 0


def test_fast_sleep_restores_both_sleeps_when_the_block_raises() -> None:
    real_sleep, real_sleep_ms = asyncio.sleep, asyncio.sleep_ms
    try:
        with FastAsyncSleep():
            raise ValueError("block failed")
    except ValueError:
        pass
    assert (asyncio.sleep, asyncio.sleep_ms) == (real_sleep, real_sleep_ms)


# ---------------------------------------------------------------------------
# _fake_timer_arm
# ---------------------------------------------------------------------------


def test_raise_on_arm_makes_init_raise_enomem_or_the_given_class_then_restores() -> None:
    before = (Timer.raise_on_arm, Timer.raise_on_arm_exc)
    for exc in (OSError, MemoryError):
        caught: OSError | MemoryError | None = None
        with RaiseOnArm(exc):
            try:
                Timer().init(period=1000, mode=Timer.PERIODIC, callback=lambda _t: None)
            except (OSError, MemoryError) as e:
                caught = e
        assert type(caught) is exc, caught
        if isinstance(caught, OSError):
            assert caught.errno == errno.ENOMEM
        assert (Timer.raise_on_arm, Timer.raise_on_arm_exc) == before


# ---------------------------------------------------------------------------
# _fake_time
# ---------------------------------------------------------------------------


def test_fake_time_carries_the_hour_and_minute_it_was_given() -> None:
    now = FakeTime(12, 30)
    assert (now.hour, now.minute) == (12, 30)


def test_driven_time_wraps_at_2_30_exactly_as_ticks30time_does() -> None:
    driven, reference = DrivenTime(now=TICKS_PERIOD - 10), Ticks30Time(TICKS_PERIOD - 10)
    start = driven.ticks_ms()
    driven.advance(20)
    reference.advance(20)
    assert driven.ticks_ms() == reference.ticks_ms() == 10
    assert driven.ticks_diff(driven.ticks_ms(), start) == reference.ticks_diff(reference.ticks_ms(), start) == 20
    assert driven.ticks_add(start, 20) == 10


def test_driven_time_is_each_modules_time_inside_the_block_only() -> None:
    first, second = _Holder(), _Holder()
    with DrivenTime(first, second) as clock:
        assert _times(first, second) == [clock, clock]
        assert clock.gmtime is time.gmtime  # every other name is the real module's
    assert _times(first, second) == [time, time]


def test_a_strict_driven_time_refuses_every_wall_clock_read() -> None:
    clock = DrivenTime(strict=True)
    for name in ("gmtime", "localtime", "mktime", "time"):
        raised = ""
        try:
            getattr(clock, name)
        except AssertionError as e:
            raised = str(e)
        assert raised == "the wall clock was read: time." + name, raised


def test_tick_sets_the_flag_once_per_time_and_advances_a_given_clock() -> None:
    flag = asyncio.ThreadSafeFlag()
    clock = DrivenTime()
    wakes: list[int] = []

    async def waiter() -> None:
        while True:
            await flag.wait()
            wakes.append(clock.now)

    async def scenario() -> None:
        task = asyncio.create_task(waiter())
        await asyncio.sleep(0)
        await tick(flag, 3, clock)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    run(scenario(), 5)
    assert wakes == [1000, 2000, 3000]


def test_rp2_gmtime_answers_rp2s_eight_fields() -> None:
    clock = Rp2Gmtime()
    assert len(clock.gmtime()) == 8
    assert len(clock.gmtime(86400)) == 8
    assert clock.mktime(clock.gmtime(86400)) == 86400
    assert abs(clock.time() - time.time()) <= 1


# ---------------------------------------------------------------------------
# _fram_builders
# ---------------------------------------------------------------------------


def test_make_fram_manager_builds_over_a_fresh_chip_of_the_given_size() -> None:
    manager, chip = make_fram_manager()
    assert type(chip) is FakeMB85RS64V
    assert manager.size == 0x2000
    small, _chip = make_fram_manager(64)
    assert small.size == 64


def test_make_fram_manager_over_an_existing_chip_keeps_its_memory() -> None:
    _manager, chip = make_fram_manager()
    chip.memory[5] = 0xA5
    rebooted, same = make_fram_manager(chip=chip)
    assert same is chip
    assert rebooted.fram._spidev.spi._spi is chip
    assert same.memory[5] == 0xA5


def test_make_fram_manager_builds_another_part_and_restores_the_spi_class() -> None:
    before = asy_spi_driver._SPI
    manager, chip = make_fram_manager(_BigChip.SIZE, _BigChip)
    assert type(chip) is _BigChip
    assert manager.size == 0x8000
    assert asy_spi_driver._SPI is before


def test_make_fram_manager_takes_the_history_length() -> None:
    manager, _chip = make_fram_manager(history_length=3)
    assert len(manager.pr.history) == 3


# ---------------------------------------------------------------------------
# _ntp_frames
# ---------------------------------------------------------------------------


def test_make_ntp_reply_is_a_48_byte_synchronized_server_reply_at_the_given_time() -> None:
    reply = make_ntp_reply(1_790_000_000)
    assert len(reply) == 48
    assert reply[:2] == b"\x1c\x01"  # LI 0, VN 3, mode 4 (server); stratum 1
    assert struct.unpack("!I", reply[40:44])[0] == 1_790_000_000 + NTP_EPOCH_DELTA
    assert reply[44:48] == bytes(4)


def test_the_fake_ntp_server_answers_one_request_or_drops_it() -> None:
    server = FakeNtpServer(_NTP_PORT, poll_ms=5, poll_tries=200)
    client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client.setblocking(False)
    poller = select.poll()
    poller.register(client, select.POLLIN)
    target = socket.getaddrinfo("127.0.0.1", _NTP_PORT)[0][-1]
    reply = make_ntp_reply(1_790_000_000)

    async def exchange(answer: "bytes | None") -> "bytes | None":
        served = asyncio.create_task(server.serve_once(answer))
        await asyncio.sleep(0)
        client.sendto(b"\x23" + bytes(47), target)
        await served
        for _ in range(20):
            # ipoll(0) returns an always-truthy iterator on this port - iterate and check the flags.
            if any(event & select.POLLIN for _obj, event in poller.ipoll(0)):
                return client.recv(64)
            await asyncio.sleep_ms(5)
        return None

    try:
        assert run(exchange(reply), 10) == reply
        assert run(exchange(None), 10) is None
    finally:
        client.close()
        server.close()


# ---------------------------------------------------------------------------
# _recording_print
# ---------------------------------------------------------------------------


def test_record_prints_captures_every_logger_line_and_restores_print() -> None:
    pr = PrintLogHistory(level=1, name="T")
    with record_prints() as recorded:
        pr.err("refused", 5)
        console("LAYER", "lost", 7)
    assert recorded.lines == [("T", "refused", 5), ("LAYER", "lost", 7)]
    assert recorded.text() == "T refused 5\nLAYER lost 7"
    assert not hasattr(asy_print_log, "print")


def test_record_prints_for_one_logger_keeps_only_its_lines() -> None:
    mine, other = PrintLogHistory(level=1, name="MINE"), PrintLogHistory(level=1, name="OTHER")
    with record_prints(mine) as recorded:
        other.err("not mine")
        mine.err("mine", sep="|")
    assert recorded.lines == [("MINE", "mine")]
    assert recorded.kwargs == [{"sep": "|", "end": "\n"}]


# ---------------------------------------------------------------------------
# _shared_rest_roundtrip
# ---------------------------------------------------------------------------


def test_drain_json_decodes_a_streamed_body_and_refuses_a_slip_in_it() -> None:
    pieces: list[str | bytes] = ['{"a": ', b"[1, 2]", "}"]
    assert drain_json(iter(pieces)) == {"a": [1, 2]}
    assert drain_json(b'{"ok": true}') == {"ok": True}
    raised = ""
    try:
        drain_json(iter(['{"a": 1', ",", ',"b": 2}']))
    except ValueError as e:
        raised = str(e)
    assert "not strict JSON" in raised


# ---------------------------------------------------------------------------
# _twin_random
# ---------------------------------------------------------------------------


def test_fixed_random_records_every_uniform_call_and_answers_its_script() -> None:
    source = FixedRandom([22.0, 0.5])
    assert source.uniform(20.0, 25.0) == 22.0
    assert source.uniform(-1.0, 1.0) == 0.5
    assert source.calls == [(20.0, 25.0), (-1.0, 1.0)]
    raised = ""
    try:
        source.uniform(0.0, 1.0)
    except AssertionError as e:
        raised = str(e)
    assert raised == "uniform() called more times than scripted"


def test_fixed_random_refuses_a_scripted_value_outside_the_requested_range() -> None:
    raised = ""
    try:
        FixedRandom([5.0]).uniform(-0.1, 0.1)
    except AssertionError as e:
        raised = str(e)
    assert raised == "scripted value 5.0 outside requested range [-0.1,0.1]", raised


def test_fixed_random_unscripted_answers_its_value_or_the_lower_bound() -> None:
    assert FixedRandom(value=100.0).uniform(0.0, 50.0) == 100.0
    plain = FixedRandom()
    assert plain.uniform(3.0, 9.0) == 3.0
    assert plain.randint(4, 9) == 4
    assert plain.getrandbits(8) == 0


def test_fixed_random_scripts_randint_and_getrandbits_too() -> None:
    source = FixedRandom(randint_values=[7], getrandbits_values=[3])
    assert source.randint(0, 10) == 7
    assert source.getrandbits(2) == 3
    raised = ""
    try:
        source.randint(0, 10)
    except AssertionError as e:
        raised = str(e)
    assert raised == "randint() called more times than scripted"


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
