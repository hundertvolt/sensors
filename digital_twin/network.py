"""Digital-twin fake `network` module - the MicroPython Unix port build has no real network module
(confirmed directly: `import network` raises ImportError, same finding tests/network.py's own
module docstring already recorded). Deliberately a separate, independent copy from tests/network.py
rather than a reuse of it (owner's explicit choice, FINAL_WIRING_PLAN.md's Step 3
clarifying-question round: full independence from tests/ at Step 5 runtime, over reuse).

Not datasheet-backed the way the three sensor twins are - the real rp2040/CYW43 WiFi driver this
fakes obviously can't run on the Unix port at all. Owner-specified strategy (FINAL_WIRING_PLAN.md's
Step 3): simulate a successful connection through all the real phases, with reasonable timing, so
asy_wifi_service.py's own state machine sees the same shape of transitions real hardware would -
but for actual data traffic (NTP/DNS/the webserver), just use the host computer's real network.
That second half needs nothing built here: `network.WLAN` only ever gates the *connection state*
asy_wifi_service.py polls (`status()`/`isconnected()`) - actual I/O goes through the separate
`socket` module, which on the Unix port is a real wrapper around the host's own BSD sockets
(confirmed directly: src/asy_udp_socket.py calls socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
straight through). So once this fake reports "connected", any NTP/DNS/HTTP traffic src/ code
initiates already transparently reaches the real internet via the host machine - no interception
needed or possible at this layer.

connect() therefore transitions through STAT_CONNECTING -> STAT_GOT_IP over a short, real delay
(_CONNECT_DELAY_S, comfortably inside asy_wifi_service.py's own ~5s/10-poll connect-status budget -
confirmed directly against that file's _poll_sta_connect_status()), scheduled via the same
asyncio-task mechanism machine.py's own Timer uses, rather than resolving instantly.

ifconfig() reports a plausible static private-network address, not a dynamically-discovered real
one - a UDP "connect, then read back the chosen local address" was tried first (the standard
no-packets-sent trick for asking the OS which local interface it would route through), but this
MicroPython build's `socket.socket` has no `getsockname()` at all (confirmed directly against the
built interpreter: `dir(socket.socket)` lists close/read/readinto/readline/send/write/accept/bind/
connect/fileno/listen/makefile/recv/recvfrom/sendto/setblocking/setsockopt/settimeout - no
getsockname), so there is no portable way to ask this platform for it. Not a functional gap: real
DNS/NTP/HTTP traffic reaches the host's actual network regardless of what this value reports (see
module docstring above) - nothing in src/ constructs a socket using its own WLAN.ifconfig() result,
only logs/serves it for diagnostics - so a plausible-looking static value is sufficient here.
"""

import asyncio

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from typing import Any

STA_IF = 0
AP_IF = 1

STAT_IDLE = 0
STAT_CONNECTING = 1
STAT_GOT_IP = 3
STAT_CONNECT_FAIL = -1
STAT_NO_AP_FOUND = -2
STAT_WRONG_PASSWORD = -3

# Real WiFi association + DHCP typically takes low single-digit seconds in the field; this is
# comfortably under asy_wifi_service.py's own 10 * 0.5s = 5s polling budget while still being long
# enough that a poller sees at least one real STAT_CONNECTING observation first, matching "all
# phases, reasonable timing" rather than an instant flip.
_CONNECT_DELAY_S = 0.7

_country_code = ["DE"]
_hostname_value = ["SensorNode"]
_CONNECTED_IFCONFIG = ("192.168.1.42", "255.255.255.0", "192.168.1.1", "192.168.1.1")


def country(code: "str | None" = None) -> str:
    if code is not None:
        _country_code[0] = code
    return _country_code[0]


def hostname(name: "str | None" = None) -> str:
    if name is not None:
        _hostname_value[0] = name
    return _hostname_value[0]


class WLAN:
    def __init__(self, if_id: int) -> None:
        self.if_id = if_id
        self._active = False
        self._connected = False
        self._status = STAT_IDLE
        self._ifconfig = ("0.0.0.0", "0.0.0.0", "0.0.0.0", "0.0.0.0")
        self._stations: list[Any] = []
        self._rssi = -50
        self.config_calls: list[dict[str, Any]] = []
        self.connect_calls: list[tuple[Any, Any]] = []
        self.deinit_called = False
        self.disconnect_called = False
        self._connect_task: asyncio.Task | None = None
        self._scripted_outcomes: list[int] = []
        # Test/Step-5-run fault injection - method name -> exception to raise once armed, same
        # shape as every chip fake's FaultInjector in this package.
        self.raise_on: dict[str, Exception] = {}

    def _maybe_raise(self, method: str) -> None:
        exc = self.raise_on.get(method)
        if exc is not None:
            raise exc

    def active(self, value: "bool | None" = None) -> bool:
        self._maybe_raise("active")
        if value is not None:
            self._active = bool(value)
        return self._active

    def script_connect_outcomes(self, outcomes: "list[int]") -> None:
        # A FIFO consumed one entry per *completed* _run_connect() resolution below - a disconnect()
        # that cancels a pending attempt never reaches the assignment past its own await, so a
        # cancelled attempt never consumes a queued outcome (nothing about it "completed"). Empty/
        # exhausted queue falls back to today's always-succeeds behavior, so every test written
        # before this existed keeps passing unchanged.
        self._scripted_outcomes = list(outcomes)

    async def _run_connect(self) -> None:
        await asyncio.sleep(_CONNECT_DELAY_S)
        outcome = self._scripted_outcomes.pop(0) if self._scripted_outcomes else STAT_GOT_IP
        if outcome == STAT_GOT_IP:
            self._connected = True
            self._status = STAT_GOT_IP
            self._ifconfig = _CONNECTED_IFCONFIG
        else:
            # A failure status means no address was ever obtained - matches real driver
            # expectations (src/asy_wifi_service.py's own _poll_sta_connect_status()): reverting to
            # the unconfigured tuple, not just leaving _connected False, so a *second* connect()
            # attempt that fails after an earlier successful one doesn't leave a stale, still-
            # "connected-looking" address behind.
            self._connected = False
            self._status = outcome
            self._ifconfig = ("0.0.0.0", "0.0.0.0", "0.0.0.0", "0.0.0.0")

    def connect(self, ssid: "Any" = None, password: "Any" = None) -> None:
        self._maybe_raise("connect")
        self.connect_calls.append((ssid, password))
        self._status = STAT_CONNECTING
        if self._connect_task is not None:
            self._connect_task.cancel()
        self._connect_task = asyncio.get_event_loop().create_task(self._run_connect())

    def disconnect(self) -> None:
        self._maybe_raise("disconnect")
        self.disconnect_called = True
        if self._connect_task is not None:
            self._connect_task.cancel()
            self._connect_task = None
        self._connected = False
        self._status = STAT_IDLE

    def deinit(self) -> None:
        self._maybe_raise("deinit")
        self.deinit_called = True

    def isconnected(self) -> bool:
        self._maybe_raise("isconnected")
        return self._connected

    def status(self, param: "str | None" = None) -> "Any":
        self._maybe_raise("status")
        if param == "rssi":
            return self._rssi
        if param == "stations":
            return self._stations
        return self._status

    def config(self, **kwargs: "Any") -> None:
        self._maybe_raise("config")
        self.config_calls.append(kwargs)

    def ifconfig(self) -> "tuple[str, str, str, str]":
        self._maybe_raise("ifconfig")
        return self._ifconfig
