"""Fake `network` module for asy_wifi_service.py's tests - the MicroPython Unix port build has no
real network module (confirmed directly: `import network` raises ImportError). Resolved ahead of any real module because tests/ precedes .frozen on MICROPYPATH, the same convention tests/machine.py already established for `machine`.
"""
# Status constant values mirror the real rp2/CYW43 port's documented meanings (STAT_IDLE=0,
# STAT_CONNECTING=1, "obtaining IP"=2 - no named constant on the real port either, matching
# asy_wifi_service.py's own `elif status == 2:` comment - STAT_GOT_IP=3, STAT_CONNECT_FAIL=-1,
# STAT_NO_AP_FOUND=-2, STAT_WRONG_PASSWORD=-3). This fake's own internal consistency with
# asy_wifi_service.py's comparisons is what actually matters for a test double, not bit-for-bit
# fidelity to a real chip.

STA_IF = 0
AP_IF = 1

STAT_IDLE = 0
STAT_CONNECTING = 1
STAT_GOT_IP = 3
STAT_CONNECT_FAIL = -1
STAT_NO_AP_FOUND = -2
STAT_WRONG_PASSWORD = -3

_country_code = ["DE"]
_hostname_value = ["SensorNode"]


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
        self._ifconfig = ("0.0.0.0", "255.255.255.0", "0.0.0.0", "0.0.0.0")
        # A real AP-mode status("stations") returns a list of per-station tuples starting with the
        # MAC bytes - the fake keeps that shape, since that is what src/ actually walks.
        self._stations: list[tuple[bytes, ...]] = []
        self._rssi = -50
        self.config_calls: list[dict[str, object]] = []
        self.connect_calls: list[tuple[str | None, str | None]] = []
        self.deinit_called = False
        self.disconnect_called = False
        # test-only fault injection - method name -> exception to raise once armed, same spirit as
        # tests/machine.py's Timer.raise_on_arm/RTC.raise_exc
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

    def connect(self, ssid: "str | None" = None, password: "str | None" = None) -> None:
        self._maybe_raise("connect")
        self.connect_calls.append((ssid, password))

    def disconnect(self) -> None:
        self._maybe_raise("disconnect")
        self.disconnect_called = True
        self._connected = False

    def deinit(self) -> None:
        self._maybe_raise("deinit")
        self.deinit_called = True

    def isconnected(self) -> bool:
        self._maybe_raise("isconnected")
        return self._connected

    def status(self, param: "str | None" = None) -> "int | list[tuple[bytes, ...]]":
        self._maybe_raise("status")
        if param == "rssi":
            return self._rssi
        if param == "stations":
            return self._stations
        return self._status

    def config(self, **kwargs: object) -> None:
        self._maybe_raise("config")
        self.config_calls.append(kwargs)

    def ifconfig(self) -> "tuple[str, str, str, str]":
        self._maybe_raise("ifconfig")
        return self._ifconfig
