"""Backend-agnostic mem_backup()/reset_cause() checks both machine fakes are held to (tests/machine.py,
digital_twin/machine.py): rp2's two watchdog-scratch regions (ports/rp2/machine_mem_backup.c:36-40, v1.29.0) and the
cause a reset leaves. tests/test_fakes.py and tests/test_digital_twin_machine.py run every one."""

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from types import ModuleType


def _reset_through(m: "ModuleType") -> None:
    # A real reset() never returns: the fake raises its reset error, a BaseException, which this lets nothing else past.
    try:
        m.reset()
    except m.SimulatedRebootError:
        return
    raise AssertionError("reset() returned")


def check_regions_are_four_and_three_words(m: "ModuleType") -> None:
    m.power_on()
    assert (len(m.mem_backup(0)), len(m.mem_backup(1))) == (4, 3)


def check_each_call_answers_the_same_view(m: "ModuleType") -> None:
    # extmod/machine_mem.c:135-148: one static view per region, region 0 the default, -1 the tuple of both.
    region0 = m.mem_backup(0)
    assert m.mem_backup(0) is region0 and m.mem_backup() is region0
    both = m.mem_backup(-1)
    assert isinstance(both, tuple) and both[0] is region0 and both[1] is m.mem_backup(1)


def check_any_other_region_is_invalid(m: "ModuleType") -> None:
    for region in (2, -2):
        try:
            m.mem_backup(region)
        except ValueError as e:
            assert str(e) == "invalid region"
        else:
            raise AssertionError(f"mem_backup({region}) answered")


def check_power_on_clears_both_regions(m: "ModuleType") -> None:
    m.mem_backup(0)[3] = 9
    m.mem_backup(1)[0] = 9
    m.power_on()
    assert (list(m.mem_backup(0)), list(m.mem_backup(1)), m.reset_cause()) == ([0] * 4, [0] * 3, m.PWRON_RESET)


def check_a_reset_keeps_the_regions_and_reads_watchdog(m: "ModuleType") -> None:
    m.power_on()
    m.mem_backup(0)[1] = 0x12345678
    m.mem_backup(1)[2] = 0xFFFFFFFF
    _reset_through(m)
    assert (m.mem_backup(0)[1], m.mem_backup(1)[2], m.reset_cause()) == (0x12345678, 0xFFFFFFFF, m.WDT_RESET)
    m.power_on()


ALL_CHECKS = (
    check_a_reset_keeps_the_regions_and_reads_watchdog,
    check_any_other_region_is_invalid,
    check_each_call_answers_the_same_view,
    check_power_on_clears_both_regions,
    check_regions_are_four_and_three_words,
)
