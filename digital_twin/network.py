"""Twin fake of the rp2 network module (the Unix port has none): WLAN fakes connection state only - real NTP/DNS/HTTP
traffic uses the host's sockets. Per-interface singletons with cyw43's status rules and a 0.7 s connect phase;
independent of tests/network.py (digital_twin/README.md fidelity table)."""

import asyncio

from _twin_common import LOG_MAXLEN, BoundedLog, saturating_add

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

STA_IF = 0
AP_IF = 1

# The cyw43 link codes network exports (lib/cyw43-driver/src/cyw43.h:98-104, v1.29.0); 2 is CYW43_LINK_NOIP.
STAT_IDLE = 0
STAT_CONNECTING = 1
STAT_GOT_IP = 3
STAT_CONNECT_FAIL = -1
STAT_NO_AP_FOUND = -2
STAT_WRONG_PASSWORD = -3

# One real STAT_CONNECTING phase, under _poll_sta_connect_status()'s 5 s budget (pinned by a test).
# @tunable l2.twin_wifi_connect_delay_s = 0.7
_CONNECT_DELAY_S = 0.7

_COUNTRY_SEED = "XX"  # extmod/modnetwork.c:71 (v1.29.0) power-on value
_HOSTNAME_SEED = "PicoW"  # ports/rp2/boards/RPI_PICO_W/mpconfigboard.h:8
# twin-only test knob: the home network's access point is down for every interface object until switched back
_access_point_up = [True]
_country_code = [_COUNTRY_SEED]
_hostname_value = [_HOSTNAME_SEED]
# RFC 5737 TEST-NET-1: the DHCP-provided DNS is unroutable, so no twin run reaches a public resolver.
_CONNECTED_IFCONFIG = ("192.0.2.42", "255.255.255.0", "192.0.2.1", "192.0.2.1")
_UNSET_IFCONFIG = ("0.0.0.0",) * 4
# cyw43's AP layout (cyw43_config.h:194, 206: a /24, the AP its own gateway) on the host loopback, where every twin
# client is: silicon's 192.168.4.1 would put each one off-subnet, and the captive DNS ignores off-subnet senders.
_AP_IFCONFIG_BASE = ("127.0.0.1", "255.255.255.0", "127.0.0.1")
_DNS_SEED = "192.0.2.1"
_dns = [_DNS_SEED]  # one lwIP DNS server shared by both interfaces (extmod/network_lwip.c:70-73)
_MAX_STAS = 32  # extmod/network_cyw43.c:377 (v1.29.0): the stations buffer's size
_AP_SSID_MAX = 32  # cyw43.h:431-448: the AP ssid and key fields, truncated to silently
_AP_KEY_MAX = 64


def _truncated(value: object, limit: int) -> object:
    # cyw43 copies at most `limit` bytes of a string setting, dropping the rest without a word.
    return value.encode()[:limit].decode() if isinstance(value, str) else value


_INTERFACES: "dict[int, WLAN]" = {}
constructions = {STA_IF: 0, AP_IF: 0}  # WLAN() calls per interface, saturating


def set_access_point_up(*, up: bool) -> None:
    _access_point_up[0] = up


def country(code: "str | None" = None) -> str:
    if code is not None:
        if len(code.encode()) != 2:  # extmod/modnetwork.c: exactly 2 BYTES, else ValueError
            raise ValueError
        _country_code[0] = code
    return _country_code[0]


def hostname(name: "str | None" = None) -> str:
    if name is not None:
        if len(name.encode()) > 32:  # MICROPY_PY_NETWORK_HOSTNAME_MAX_LEN, in bytes
            raise ValueError
        _hostname_value[0] = name
    return _hostname_value[0]


def reset_interfaces() -> None:
    # Test-only, as machine.Pin.reset_registry(): silicon never forgets its interfaces.
    _INTERFACES.clear()
    for if_id in constructions:
        constructions[if_id] = 0


def reset_test_state() -> None:
    # Test-only: restores every process-wide twin knob a test can change; each twin test file registers it with
    # microtest.after_each() (the twin never has tests/ on its path).
    reset_interfaces()
    _access_point_up[0] = True
    _country_code[0] = _COUNTRY_SEED
    _hostname_value[0] = _HOSTNAME_SEED
    _dns[0] = _DNS_SEED


class WLAN:
    # One object per interface, as extmod/network_cyw43.c:96-103 (v1.29.0): STA_IF answers the STA singleton, any other
    # id the AP one, and a later construction returns it with its state.
    TEST_API = (
        "if_id", "config_calls", "connect_calls", "deinit_called", "disconnect_called", "raise_on", "stations_chip_down",
        "script_connect_outcomes",
    )  # fmt: skip
    _initialised: bool

    def __init__(self, if_id: int = STA_IF) -> None:
        if self._initialised:
            return
        self._initialised = True
        self.if_id = STA_IF if if_id == STA_IF else AP_IF
        self._active = False
        self._connected = False
        self._status = STAT_IDLE
        self._ifconfig = _UNSET_IFCONFIG
        self._stations: list[tuple[bytes]] = []  # rp2's one-element MAC tuples
        self._rssi = -50
        self._config: dict[str, object] = {}
        self.config_calls: BoundedLog[dict[str, object]] = BoundedLog(LOG_MAXLEN)
        self.connect_calls: BoundedLog[tuple[str | None, str | None]] = BoundedLog(LOG_MAXLEN)
        self.deinit_called = False
        self.disconnect_called = False
        self._connect_task: asyncio.Task[None] | None = None
        self._scripted_outcomes: list[int] = []
        # twin-only test knob: method -> (exception type, args, times[, status params]); times None raises until
        # cleared, and the optional parameter tuple limits a status() entry to those queries.
        self.raise_on: dict[str, tuple[object, ...]] = {}
        # twin-only test knob: rp2's stations answer with the radio down (network_cyw43.c:371-388)
        self.stations_chip_down = False

    def __new__(cls, if_id: int = STA_IF) -> "WLAN":
        key = STA_IF if if_id == STA_IF else AP_IF
        constructions[key] = saturating_add(constructions[key])
        existing = _INTERFACES.get(key)
        if existing is not None:
            return existing
        wlan = super().__new__(cls)
        wlan._initialised = False
        _INTERFACES[key] = wlan
        return wlan

    def _maybe_raise(self, method: str, param: object = None) -> None:
        entry = self.raise_on.get(method)
        if entry is None:
            return
        exc_type, args, times = entry[0], entry[1], entry[2]
        params = entry[3] if len(entry) > 3 else None
        if isinstance(params, tuple) and param not in params:
            return
        if not (isinstance(exc_type, type) and issubclass(exc_type, BaseException) and isinstance(args, tuple)):
            raise TypeError("a raise_on entry is (exception type, args, times[, status params])")
        if isinstance(times, int):
            if times <= 1:
                del self.raise_on[method]
            else:
                self.raise_on[method] = (exc_type, args, times - 1) + entry[3:]
        raise exc_type(*args)  # a fresh instance each time, as FaultInjector raises

    def _power_down(self) -> None:
        if self._connect_task is not None:
            self._connect_task.cancel()
            self._connect_task = None
        self._active = False
        self._connected = False
        self._status = STAT_IDLE
        self._ifconfig = _UNSET_IFCONFIG

    async def _run_connect(self) -> None:
        await asyncio.sleep(_CONNECT_DELAY_S)
        if not _access_point_up[0]:  # nothing to join, so no scripted outcome is consumed
            outcome = STAT_NO_AP_FOUND
        elif self._scripted_outcomes:
            outcome = self._scripted_outcomes.pop(0)
        else:
            outcome = STAT_GOT_IP
        if outcome == STAT_GOT_IP:
            self._connected = True
            self._status = STAT_GOT_IP
            self._ifconfig = _CONNECTED_IFCONFIG
            _dns[0] = _CONNECTED_IFCONFIG[3]
        else:
            # A failure status means no address was obtained, which is what the real driver
            # expects: revert to the unconfigured tuple rather than only clearing _connected, so
            # a failure after an earlier success leaves no stale connected-looking address.
            self._connected = False
            self._status = outcome
            self._ifconfig = _UNSET_IFCONFIG

    def active(self, value: "bool | None" = None) -> bool:
        self._maybe_raise("active")
        if value is not None:
            self._active = bool(value)
            if self.if_id == AP_IF:
                # The AP is up with its fixed address once active; down again it reads as the unconfigured interface.
                self._status = STAT_GOT_IP if self._active else STAT_IDLE
                self._ifconfig = _AP_IFCONFIG_BASE + (_dns[0],) if self._active else _UNSET_IFCONFIG
        return self._active

    def config(self, *args: str, **kwargs: object) -> object:
        # extmod/network_cyw43.c:400-555: one positional name reads a setting back (the essid only, here), keywords
        # store one, the essid and key truncated as cyw43 does (cyw43.h:431-448).
        self._maybe_raise("config")
        if args:
            if len(args) != 1 or kwargs:
                raise TypeError("must query one param")
            if args[0] in ("essid", "ssid"):
                return self._config.get("essid", "")
            raise ValueError("unknown config param")
        stored = dict(kwargs)
        for name, limit in (("essid", _AP_SSID_MAX), ("ssid", _AP_SSID_MAX), ("password", _AP_KEY_MAX), ("key", _AP_KEY_MAX)):
            if name in stored:
                stored[name] = _truncated(stored[name], limit)
        if "ssid" in stored:
            self._config["essid"] = stored["ssid"]
        self._config.update(stored)
        self.config_calls.append(stored)
        return None

    def connect(self, ssid: "str | None" = None, password: "str | None" = None) -> None:
        self._maybe_raise("connect")
        if password is not None and len(password.encode()) > 64:  # cyw43_ll_wifi_join()'s -CYW43_EINVAL
            raise OSError(22, "EINVAL")
        if ssid is not None and len(ssid.encode()) > 32:  # real driver: unchecked copy past a 32-byte field
            raise AssertionError("SSID over 32 bytes reached connect() - overflows cyw43's last_ssid_joined on silicon")
        self.connect_calls.append((ssid, password))
        self._status = STAT_CONNECTING
        if self._connect_task is not None:
            self._connect_task.cancel()
        self._connect_task = asyncio.get_event_loop().create_task(self._run_connect())

    def deinit(self) -> None:
        # One cyw43_state behind both interfaces (cyw43_ctrl.c:118-146): deinit() powers the whole radio down.
        self._maybe_raise("deinit")
        self.deinit_called = True
        for wlan in _INTERFACES.values():
            wlan._power_down()

    def disconnect(self) -> None:
        self._maybe_raise("disconnect")
        self.disconnect_called = True
        if self._connect_task is not None:
            self._connect_task.cancel()
            self._connect_task = None
        self._connected = False
        self._status = STAT_IDLE

    def ifconfig(self) -> "tuple[str, str, str, str]":
        self._maybe_raise("ifconfig")
        return self._ifconfig

    def isconnected(self) -> bool:
        self._maybe_raise("isconnected")
        return self._connected

    def script_connect_outcomes(self, outcomes: "list[int]") -> None:
        # A FIFO consumed one entry per COMPLETED _run_connect() with the access point up: a
        # disconnect() that cancels a pending attempt never reaches the assignment past its await, so
        # it consumes nothing. An exhausted queue falls back to always-succeeds.
        self._scripted_outcomes = list(outcomes)

    def status(self, param: "str | None" = None) -> "int | list[tuple[bytes]]":
        # As extmod/network_cyw43.c:352-392 (v1.29.0); SPECIFICATION.md F.1 states the contract.
        self._maybe_raise("status", param)
        if param is None:
            return self._status
        if param == "rssi":
            if self.if_id != STA_IF:
                raise ValueError("STA required")
            return self._rssi
        if param == "stations":
            if self.if_id != AP_IF:
                raise ValueError("AP required")
            if self.stations_chip_down:  # cyw43_ensure_up() failed: the count stays at the buffer size, the bytes unfilled (cyw43_ctrl.c:717-723)
                return [(bytes(6),) for _ in range(_MAX_STAS)]
            return self._stations
        raise ValueError("unknown status param")
