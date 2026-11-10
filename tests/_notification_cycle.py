"""The notification monitor's first cycle on a driven clock, shared by the notification integration tests: its end by
the service's own rule, and the loop parked FlashInterval after its start."""

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from _fake_time import DrivenTime

    from asy_notification_service import NotificationService


async def cycle(clock: "DrivenTime", notify: "NotificationService", flashes: int, ramp_ms: int | None = None) -> None:
    # Each triggered flash's ramp (FlashDur, or a real LED's ramp_ms), then FlashDur dark: 1 ms before that end the loop
    # has not parked on its next cycle yet; then it parks there, FlashInterval after its start.
    cfg = (await notify.get_dict_cfg())["NOTIFY"]
    flash_dur, interval = cfg["FlashDur"], cfg["FlashInterval"]
    assert isinstance(flash_dur, float) and isinstance(interval, float), cfg
    start = clock.now
    end = start + flashes * ((round(flash_dur * 1000) if ramp_ms is None else ramp_ms) + round(flash_dur * 1000))
    if end > start:
        await clock.elapse(end - 1 - start)
        assert start + round(interval * 1000) not in clock.wakes(), f"the cycle ended by virtual t={clock.now} ms: {clock.wakes()}"
    await clock.elapse(end - clock.now)
    assert clock.wakes()[-1] == start + round(interval * 1000), f"at virtual t={clock.now} ms the loop waits for {clock.wakes()}"
