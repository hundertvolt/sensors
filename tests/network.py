"""Fake `network` module for the unit tier: the Unix port has none (`import network` raises ImportError), and tests/
precedes .frozen on MICROPYPATH, as for tests/machine.py. Models the Pico W's cyw43 surface the product uses
(MicroPython v1.29.0): power-on seeds, one static WLAN per interface, the status() raises."""

import microtest

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from typing import ClassVar

# Status values are the cyw43 link codes `network` exports; 2 is CYW43_LINK_NOIP (joined, no IP yet), which
# network exports no name for (cyw43.h:100, extmod/modnetwork.c:197-202, v1.29.0).

STA_IF = 0
AP_IF = 1

STAT_IDLE = 0
STAT_CONNECTING = 1
STAT_GOT_IP = 3
STAT_CONNECT_FAIL = -1
STAT_NO_AP_FOUND = -2
STAT_WRONG_PASSWORD = -3

_COUNTRY_SEED = "XX"  # extmod/modnetwork.c:71
_HOSTNAME_SEED = "PicoW"  # ports/rp2/boards/RPI_PICO_W/mpconfigboard.h:8, MICROPY_PY_NETWORK_HOSTNAME_DEFAULT
_country_code = [_COUNTRY_SEED]
_hostname_value = [_HOSTNAME_SEED]
_constructions: "dict[int, int]" = {}

# The module's test-only names: the after-each reset.
TEST_API = ("reset_test_state",)


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


class WLAN:
    # One static object per interface, as cyw43's make_new() hands back (extmod/network_cyw43.c:96-103): any id but
    # STA_IF is the AP. Not modelled: scan(), ipconfig(), the radio's own join timing (a test sets _status/_connected).
    TEST_API = (
        "if_id", "config_calls", "connect_calls", "status_calls", "raise_on", "constructions", "deinit_called",
        "disconnect_called",
    )  # fmt: skip
    # test-only: WLAN() calls per interface. Counted through the module's own dict, never the name WLAN, which a
    # consumer may have swapped for a wrapper that builds this class.
    constructions: "ClassVar[dict[int, int]]" = _constructions
    _fresh: bool

    def __init__(self, if_id: int = STA_IF) -> None:
        interface = STA_IF if if_id == STA_IF else AP_IF
        _constructions[interface] = _constructions.get(interface, 0) + 1
        if not self._fresh:
            return
        self._fresh = False
        self.if_id = interface
        self._active = False
        self._connected = False
        self._status: int | None = None  # None: the link status follows active() (AP) or STAT_IDLE (STA)
        self._ifconfig = ("0.0.0.0", "255.255.255.0", "0.0.0.0", "0.0.0.0")
        # A real AP-mode status("stations") returns a list of per-station tuples starting with the
        # MAC bytes - the fake keeps that shape, since that is what src/ actually walks.
        self._stations: list[tuple[bytes, ...]] = []
        self._rssi = -50
        self.config_calls: list[dict[str, object]] = []
        self.connect_calls: list[tuple[str | None, str | None]] = []
        self.status_calls: list[str | None] = []
        self.deinit_called = False
        self.disconnect_called = False
        # test-only fault injection - method name -> exception to raise once armed, same spirit as
        # tests/machine.py's Timer.raise_on_arm/RTC.raise_exc
        self.raise_on: dict[str, Exception] = {}

    def __new__(cls, if_id: int = STA_IF) -> "WLAN":
        interface = STA_IF if if_id == STA_IF else AP_IF
        wlan = _WLANS.get(interface)
        if wlan is None:
            wlan = _WLANS[interface] = super().__new__(cls)
            wlan._fresh = True
        return wlan

    def _link_status(self) -> int:
        # An active AP's netif is up with its address, so it reports STAT_GOT_IP (cyw43/src/cyw43_lwip.c:300-320).
        if self._status is not None:
            return self._status
        if self.if_id == AP_IF and self._active:
            return STAT_GOT_IP
        return STAT_IDLE

    def _maybe_raise(self, method: str) -> None:
        exc = self.raise_on.get(method)
        if exc is not None:
            raise exc

    def active(self, value: "bool | None" = None) -> bool:
        self._maybe_raise("active")
        if value is not None:
            self._active = bool(value)
        return self._active

    def config(self, **kwargs: object) -> None:
        self._maybe_raise("config")
        self.config_calls.append(kwargs)

    def connect(self, ssid: "str | None" = None, password: "str | None" = None) -> None:
        self._maybe_raise("connect")
        if password is not None and len(password.encode()) > 64:  # cyw43_ll_wifi_join()'s -CYW43_EINVAL
            raise OSError(22, "EINVAL")
        if ssid is not None and len(ssid.encode()) > 32:  # real driver: unchecked copy past a 32-byte field
            raise AssertionError("SSID over 32 bytes reached connect() - overflows cyw43's last_ssid_joined on silicon")
        self.connect_calls.append((ssid, password))

    def deinit(self) -> None:
        # cyw43_deinit() powers the whole chip off (network_cyw43.c:133-137, cyw43_ctrl.c:118-139): both interfaces
        # go down, whichever object deinit() was called on.
        self._maybe_raise("deinit")
        self.deinit_called = True
        for wlan in _WLANS.values():
            wlan._active = False
            wlan._connected = False

    def disconnect(self) -> None:
        self._maybe_raise("disconnect")
        self.disconnect_called = True
        self._connected = False

    def ifconfig(self) -> "tuple[str, str, str, str]":
        self._maybe_raise("ifconfig")
        return self._ifconfig

    def isconnected(self) -> bool:
        self._maybe_raise("isconnected")
        return self._connected

    def status(self, *params: str) -> "int | list[tuple[bytes, ...]]":
        # network_cyw43.c:351-392: no argument is the link status; "rssi" needs the STA, "stations" the AP, any other
        # string raises, and a non-string such as None raises TypeError (mp_obj_str_get_qstr()). Each call is recorded.
        param = params[0] if params else None
        self.status_calls.append(param)
        self._maybe_raise("status")
        if len(params) > 1:
            raise TypeError("function takes at most 2 positional arguments")
        if not params:
            return self._link_status()
        if not isinstance(param, str):
            raise TypeError("can't convert to str implicitly")
        if param == "rssi":
            if self.if_id != STA_IF:
                raise ValueError("STA required")
            return self._rssi
        if param == "stations":
            if self.if_id != AP_IF:
                raise ValueError("AP required")
            return self._stations
        raise ValueError("unknown status param")


_WLANS: "dict[int, WLAN]" = {}


def reset_test_state() -> None:
    # After every test (registered below): the power-on seeds back in place, every WLAN object and count forgotten.
    _country_code[0] = _COUNTRY_SEED
    _hostname_value[0] = _HOSTNAME_SEED
    _WLANS.clear()
    _constructions.clear()


microtest.after_each(reset_test_state)
