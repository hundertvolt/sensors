"""Dev-only MQTT link exerciser over the wired MQTTClient: one QoS 1 echo probe per period on <base>/link/echo, counted
as a transfer when it comes back through the broker before the next round, and the device's <base>/cmd/# messages
counted, so the link is never idle on the bench rig. Built like asy_uart_link_driver.py; SPECIFICATION.md Part A.12."""
# Not a SensorReader subclass, like UARTLinkDriver: buildgen resolves it through driver_registry._OVERRIDES.

import asyncio

from micropython import const

from asy_base_classes import COUNTER_CAP

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from asy_base_classes import ErrorSource, JsonDict, TaskStarter, TimerStarter
    from asy_mqtt_client import MQTTClient
    from asy_print_log import PrintLogHistory

# The client it drives (Part C.14.2): no other wiring, no setting, no route; it shares the client's logger.
# @wiring mqtt_target MQTTClient client required kwarg

_ECHO_TOPIC = const("link/echo")  # below <base>: the probe goes out on it and comes back through the subscription
_CMD_FILTER = const("cmd/#")  # the device's commands, below <base>
_PROBE_BYTES = const(4)  # the probe's sequence number, big-endian
_RETAIN = const(0x01)  # a PUBLISH's RETAIN flag (MQTT 3.1.1 section 3.3.1.3), bit 0 of the flags each callback gets
# One probe per period while the client is connected: the link's own traffic on a live system, as uart_link's echo.
# @tunable mqtt_link.exercise_period_ms = 10000
_EXERCISE_PERIOD_MS = const(10000)


class MQTTLinkDriver:
    def __init__(self, client: "MQTTClient") -> None:
        self._client = client
        self.name = client.name  # matches self.pr.name - the _ModuleLike registration shape
        self.pr = client.pr  # the client's logger: no log, errcount row or FRAM chunk of its own
        # Registered before any task starts, so the client builds the topics with its settings and subscribes at connect.
        self._echo_topic = client.add_topic(_ECHO_TOPIC)
        client.add_consumer(_ECHO_TOPIC, self._on_echo)
        client.add_consumer(_CMD_FILTER, self._on_command)
        self._probe = bytearray(_PROBE_BYTES)  # rewritten in place each round; the client copies it into its ring
        self._seq = 0
        self._pending = False  # a probe is out and its echo not back yet
        self._transfers = 0
        self._failures = 0
        self._commands = 0

    async def _exercise_loop(self) -> None:
        # Each round first fails the probe still out, then sends the next while the client is connected; nothing goes out
        # otherwise. A refused publish (the ring full) fails at once. Never raises: is_connected() and publish_under() don't.
        while True:
            if self._pending:
                self._pending = False
                if self._failures < COUNTER_CAP:
                    self._failures += 1
            if self._client.is_connected():
                seq = self._seq + 1 if self._seq < COUNTER_CAP else 0  # wrapped, never add-then-mask: a small int throughout
                self._seq = seq
                probe = self._probe
                probe[0] = seq >> 24
                probe[1] = (seq >> 16) & 0xFF
                probe[2] = (seq >> 8) & 0xFF
                probe[3] = seq & 0xFF
                if self._client.publish_under(self._echo_topic, probe, qos=1):
                    self._pending = True
                elif self._failures < COUNTER_CAP:
                    self._failures += 1
            await asyncio.sleep_ms(_EXERCISE_PERIOD_MS)

    def _on_command(self, _topic: memoryview, _payload: memoryview, _flags: int) -> None:
        # A message on <base>/cmd/#, counted; the client's MQTTLastRxTopic shows its topic.
        if self._commands < COUNTER_CAP:
            self._commands += 1

    def _on_echo(self, _topic: memoryview, payload: memoryview, flags: int) -> None:
        # The probe back through the broker, counted once while it is the one out: a retained or stale copy (a resent
        # probe, one a persistent session queued) is not. Compares in place, allocating nothing, and never raises.
        if self._pending and not flags & _RETAIN and self._probe == payload:
            self._pending = False
            if self._transfers < COUNTER_CAP:
                self._transfers += 1

    # -- starters ----------------------------------------------------------

    def get_task_starters(self) -> "list[TaskStarter]":
        return [self.start_asy_exercise]

    def get_timer_starters(self) -> "list[TimerStarter]":
        return []  # no machine.Timer anywhere in this file (SPECIFICATION.md C.9 shape)

    def start_asy_exercise(self) -> asyncio.Task[None]:
        return asyncio.create_task(self._exercise_loop())

    # -- getters -----------------------------------------------------------

    def get_error_sources(self) -> "list[ErrorSource]":
        return []  # the client's own errcount row is the one this exerciser shares; it writes no entry of its own

    async def get_link_status(self) -> "JsonDict":
        # The MQTTLINK maintenance sensor, UARTLINK's keys plus the commands; built with no await, so one snapshot.
        return {"Transfers": self._transfers, "Failures": self._failures, "Commands": self._commands}

    def get_loggers(self) -> "list[PrintLogHistory]":
        return []  # the client registers the logger this exerciser shares, so the debug level reaches it once
