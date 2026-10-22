"""End to end over the product's REST routes: real readers, a real WebserverService and the vendored Microdot (v2.7.0).
Every PUT is a sparse body on a product route; the settings groups are read from buildgen/validate.py's SETTINGS_GROUPS,
the table buildgen/codegen.py emits them from."""

import asyncio
import errno as errno_mod
import json
import os
import struct
import sys
from collections import namedtuple

# The unit tier's MICROPYPATH holds src/ and tests/ but no ext/ (scripts/micropypath.toml); this file alone reaches ext/microdot.py.
sys.path.insert(0, "ext")

from _async_harness import run
from _error_codes import code
from _fast_sleep import FastAsyncSleep
from _src_schema import src_schema
from _strict_json import strict_loads
from _tmp_scratch import TmpScratch
from machine import I2C as _MachineI2C
from microdot import Microdot, Request, Response

import asy_api_response as ar
import asy_wifi_service
from asy_base_classes import ValueRef
from asy_bmp3xx_driver import BMP3XX_Reader
from asy_crc_checks import CRC8
from asy_i2c_driver import I2C
from asy_ntp_client import NTPClient, NtpTiming
from asy_scd30_driver import SCD30_Reader
from asy_sgp40_driver import SGP40_Reader
from asy_system_service import SystemService
from asy_webserver_service import RouteSources, ServingLimits, SettingsGroup, WebserverService
from asy_wifi_service import WifiConfig, WifiService

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Sequence

    import asy_config_manager as cm
    from asy_base_classes import AsyncCallback, JsonDict, JsonMapping


_scratch = TmpScratch("msi")
_SgpComp = namedtuple("_SgpComp", ("Temp", "Hum"))
_SETTINGS_TABLE = "buildgen/validate.py"
_SETTINGS_ROWS: "list[tuple[str, str, tuple[str, ...], str | None]]" = []  # _settings_rows()'s one read of the table

# The SCD30 product schema, read from source (tests/_src_const.py).
_VAL_TEMP_OFFSET: "cm.ConfigSchema" = src_schema("src/asy_scd30_driver.py", "_VAL_TEMP_OFFSET")
_VAL_MEAS_INTERVAL: "cm.ConfigSchema" = src_schema("src/asy_scd30_driver.py", "_VAL_MEAS_INTERVAL")
_VAL_AMB_PRES: "cm.ConfigSchema" = src_schema("src/asy_scd30_driver.py", "_VAL_AMB_PRES")
_VAL_ALTITUDE: "cm.ConfigSchema" = src_schema("src/asy_scd30_driver.py", "_VAL_ALTITUDE")
_VAL_FORCE_CAL_REF: "cm.ConfigSchema" = src_schema("src/asy_scd30_driver.py", "_VAL_FORCE_CAL_REF")
_VAL_SELF_CAL: "cm.ConfigSchema" = src_schema("src/asy_scd30_driver.py", "_VAL_SELF_CAL")
_VAL_FRC_NOISE: "cm.ConfigSchema" = src_schema("src/asy_scd30_driver.py", "_VAL_FRC_NOISE")


class _FakeCompSource:
    # SGP40's temperature/humidity source (SPECIFICATION.md Part C.14): only get_data() is read.
    async def get_data(self) -> object:
        return _SgpComp(25.0, 50.0)


class _Product:
    # The modules one device build wires together, the service and its Microdot app, and each settings hook's calls.
    def __init__(self, wifi: WifiService, ntp: NTPClient, system: SystemService, readers: "tuple[BMP3XX_Reader, SGP40_Reader, SCD30_Reader]", buses: "tuple[I2C, I2C]") -> None:
        self.wifi, self.ntp, self.system = wifi, ntp, system
        self.bmp, self.sgp, self.scd = readers
        self.bus0, self.bus1 = buses
        self.calls: dict[str, int] = {}
        self.app = Microdot()
        modules: dict[str, WifiService | NTPClient | SystemService] = {"conn": wifi, "ntp": ntp, "sysfunct": system}  # the generated module's names
        routes = RouteSources(readers, _settings_groups(modules, self.calls), None, None, None, None, None, None, (), ())
        self.service = WebserverService(self.app, routes, ServingLimits(2048, 256, 3, None, 0.2, 0.5, "0.0.0.0", 80), uptime_s=self.system.get_uptime)


class _RaisingBMP(BMP3XX_Reader):
    # A reader whose setter raises past every guard of its own: PUT /sensors calls it directly.
    async def _set_dict_cfg(self, data: "JsonMapping", cfg_vals: "cm.ConfigSchema") -> "cm.WriteValidity":
        raise RuntimeError("simulated handler bug")


class _YieldOnlyAsyncio:
    # asy_wifi_service's view of asyncio, each sleep one yield: the trigger's grace and settle are not under test here.
    def __getattr__(self, name: str) -> object:
        return getattr(asyncio, name)

    async def sleep(self, _seconds: float) -> None:
        await asyncio.sleep(0)


def _body_bytes(body: "bytes | str | Iterable[bytes]") -> bytes:
    # A dict route's body is bytes; a streamed route's an iterator of pieces (SPECIFICATION.md Part I.3).
    if isinstance(body, str):
        return body.encode()
    return body if isinstance(body, bytes) else b"".join(body)


def _break_cfg_file(path: str) -> None:
    # The config file becomes a directory of the same name, so write_config()'s open(path, "w") raises a real OSError
    # (EISDIR) from the filesystem: the "persistence layer is broken" fault, SGP40's setter path's only real failure.
    os.remove(path)
    os.mkdir(path)


def _counted_async(calls: "dict[str, int]", name: str, hook: "AsyncCallback") -> "AsyncCallback":
    # A settings hook as the generated module binds it (post_asy_fct=), counted per call and then run.
    async def counted() -> None:
        calls[name] = calls.get(name, 0) + 1
        await hook()

    return counted


def _counted_sync(calls: "dict[str, int]", name: str, hook: "Callable[[], None]") -> "Callable[[], None]":
    # As _counted_async(), for a post_fct= hook.
    def counted() -> None:
        calls[name] = calls.get(name, 0) + 1
        hook()

    return counted


def _dispatch(product: _Product, method: str, path: str, body: object = None) -> "tuple[int, JsonDict]":
    # One request through the product's app; each product wait is one yield (SCD30's 50 ms register reads among them).
    with FastAsyncSleep():
        res = run(product.app.dispatch_request(_make_request(product.app, method, path, body)))
    return res.status_code, _json(res)


def _fault_i2c_write(i2c: I2C, exc: Exception) -> None:
    # Fails only the write half of a read-modify-write register access (the next writeto with a stop; a read's address
    # write has none), so reads and the registered getter keep working.
    real_i2c = i2c._i2c
    assert isinstance(real_i2c, _MachineI2C)
    real_writeto = real_i2c.writeto

    def fail_the_next_register_write(address: int, buf: object, stop: bool = True) -> int:
        if stop:
            real_i2c.writeto = real_writeto  # type: ignore[method-assign]  # once only
            raise exc
        return real_writeto(address, buf, stop)

    real_i2c.writeto = fail_the_next_register_write  # type: ignore[method-assign]


def _fault_next_i2c_write(reader: SCD30_Reader) -> None:
    # One-shot: tests/machine.py's inject_fault is a FIFO of one exception per matching call.
    real_i2c = reader._scd._i2c_scd30.i2c_device.i2c._i2c
    assert isinstance(real_i2c, _MachineI2C)
    real_i2c.inject_fault("writeto", OSError, errno_mod.EIO, "no ACK on write")


def _json(res: Response) -> "JsonDict":
    # The response body, strict-parsed (tests/_strict_json.py): a duplicate key or a non-object body fails here.
    body = strict_loads(_body_bytes(res.body))
    assert isinstance(body, dict), body
    return body


def _make_request(app: Microdot, method: str, path: str, body: object) -> Request:
    # A JSON body is serialised; bytes go on the wire as they are (a body that is not JSON at all).
    raw = body if isinstance(body, bytes) else b"" if body is None else json.dumps(body).encode()
    headers = {"Content-Length": str(len(raw)), "Content-Type": "application/json"}
    return Request(app, ("127.0.0.1", 12345), method, path, "1.1", headers, body=raw)


def _make_service(bmp_cls: "type[BMP3XX_Reader]" = BMP3XX_Reader) -> _Product:
    # The product surface: every module set up over power-cycled fake buses, one config directory, the three readers as
    # the sensors and the settings groups as the generated module builds them, in a real WebserverService.
    _MachineI2C.reset_id(0)
    _MachineI2C.reset_id(1)
    cfg_path = _scratch.dir()
    with open(cfg_path + "config_NTP.cfg", "w") as f:
        f.write('{"DNSFallback": ""}')  # no public resolver as a candidate, whatever a test triggers
    bus0 = I2C(0, scl_pin=1, sda_pin=0, frequency=100000)
    bus1 = I2C(1, scl_pin=19, sda_pin=18, frequency=50000)
    wifi = WifiService(WifiConfig("SensorNode", "12345678", 5, 5), cfg_path=cfg_path)
    ntp = NTPClient(asyncio.Lock(), _network_available, _no_dns_server, NtpTiming(500, 1, 5000, 10, 600), cfg_path=cfg_path)
    system = SystemService(ntp.ntp_issynced, cfg_path=cfg_path)
    comp = _FakeCompSource()
    readers = (
        bmp_cls(bus0, address=0x77, cfg_path=cfg_path),
        SGP40_Reader(bus1, ValueRef(comp, "Temp"), ValueRef(comp, "Hum"), max_module_error=5, cfg_path=cfg_path),
        SCD30_Reader(bus0, irq_pin=5, trigger_s=3, max_module_error=5, cfg_path=cfg_path),
    )
    assert [run(wifi.setup()), run(ntp.setup()), run(system.setup())] == [True] * 3
    assert [run(reader.setup()) for reader in readers] == [True] * len(readers)
    return _Product(wifi, ntp, system, readers, (bus0, bus1))


def _nak_i2c_address(i2c: I2C, address: int) -> None:
    # Every op to `address` answers EIO from now on, as a dead or disconnected sensor does.
    real_i2c = i2c._i2c
    assert isinstance(real_i2c, _MachineI2C)
    real_i2c.nak_addresses.add(address)


def _network_available() -> bool:
    return True


def _no_dns_server() -> "str | None":
    return None


def _queue_scd_snapshot(reader: SCD30_Reader) -> None:
    # One config snapshot (word + CRC-8 each, Interface Description 1.1.3): TempOffset 0, MeasInterval 2,
    # AmbPres 0, Altitude 0, ForceCalRef 400, SelfCal 0 - the chip's own power-up values.
    real_i2c = reader._scd._i2c_scd30.i2c_device.i2c._i2c
    assert real_i2c is not None
    for value in (0, 2, 0, 0, 400, 0):
        payload = struct.pack(">H", value)
        crc = run(CRC8().add(bytearray(payload)))
        assert crc is not None
        real_i2c.read_queue.append(payload + bytes([crc[-1]]))


def _register_device(i2c: I2C, address: int) -> None:
    # The fake routes a declared register device's address writes and reads through its registers.
    real_i2c = i2c._i2c
    assert real_i2c is not None
    real_i2c.register_device(address)


def _scd_writes(reader: SCD30_Reader) -> "list[bytes]":
    # The command frames that changed a setting (5-byte argument frames and the bare stop), in bus order;
    # the snapshot's own 2-byte register-address writes are left out.
    real_i2c = reader._scd._i2c_scd30.i2c_device.i2c._i2c
    assert isinstance(real_i2c, _MachineI2C)
    return [entry[2] for entry in real_i2c.log if entry[0] == "writeto" and (len(entry[2]) == 5 or entry[2] == b"\x01\x04")]


def _settings_groups(modules: "dict[str, WifiService | NTPClient | SystemService]", calls: "dict[str, int]") -> "dict[str, Sequence[SettingsGroup]]":
    # SETTINGS_GROUPS' rows bound to this product's modules, each hook counted in calls.
    groups: dict[str, list[SettingsGroup]] = {}
    for section, var, fields, hook in _settings_rows():
        post_fct: Callable[[], None] | None = None
        post_asy_fct: AsyncCallback | None = None
        if hook is not None:  # "post_fct=conn.reconnect_wifi": the keyword, then the module's own method
            kind, target = hook.split("=")
            name = target.split(".")[1]
            if kind == "post_fct":
                post_fct = _counted_sync(calls, name, getattr(modules[var], name))
            else:
                post_asy_fct = _counted_async(calls, name, getattr(modules[var], name))
        groups.setdefault(section, []).append(SettingsGroup(modules[var], fields, post_fct, post_asy_fct))
    assert sorted(groups) == ["networking", "system"], _settings_rows()  # the sections the generated webserver serves them under
    return dict(groups)


def _settings_rows() -> "list[tuple[str, str, tuple[str, ...], str | None]]":
    # SETTINGS_GROUPS' rows as source text: (section, module var, fields, hook) - each one tuple literal on its line. Read
    # once per file run: the table does not change, and reading it again cost each product build nearly half its time.
    if not _SETTINGS_ROWS:
        with open(_SETTINGS_TABLE) as f:
            rows = f.read().split("SETTINGS_GROUPS: ", 1)[1].split("\n)\n", 1)[0].split("\n")[1:]
        for row in rows:
            literal = row.split("#", 1)[0].strip().rstrip(",")  # no string in the table holds a "#"
            _SETTINGS_ROWS.append(eval(literal, {}))
    return _SETTINGS_ROWS


def _wifi_const(name: str) -> int:
    # A phase's value from src/asy_wifi_service.py's source: a const() is not a module attribute on MicroPython.
    with open("src/asy_wifi_service.py") as f:
        for line in f:
            if line.startswith(name + " = const("):
                return int(line.split("const(", 1)[1].split(")", 1)[0])
    raise AssertionError(name + " not found in src/asy_wifi_service.py")


# ---------------------------------------------------------------------------
# PUT /networking: sparse bodies dispatched to their own groups only; a body that is not a JSON object is refused.
# ---------------------------------------------------------------------------


def test_networking_put_of_valid_identity_fields_applies_them_and_reconnects() -> None:
    product = _make_service()
    body = {"Hostname": "NewHost", "SSID": "MyNet", "PW": "supersecret", "Country": "US"}
    status, resp = _dispatch(product, "PUT", "/networking", body)
    assert (status, resp) == (200, {"res": "OK", "code": 0, "descr": "Command executed", "result": dict.fromkeys(body, "Valid")})
    assert product.calls == {"reconnect_wifi": 1} and product.wifi._reconnect_fresh is True
    assert run(product.wifi.cfgmgr.get_dict(["Hostname", "SSID", "PW", "Country"])) == body


def test_networking_put_with_refused_fields_reports_each_and_still_reconnects() -> None:
    product = _make_service()
    _status, resp = _dispatch(product, "PUT", "/networking", {"Hostname": "NewHost", "SSID": "MyNet", "PW": "short", "Country": "United States"})
    assert resp["res"] == "OK"  # per-field detail lives in "result", the request itself was sound
    assert resp["result"] == {"Hostname": "Valid", "SSID": "Valid", "PW": "Invalid", "Country": "Invalid"}
    assert product.calls == {"reconnect_wifi": 1}  # Hostname and SSID changed
    assert run(product.wifi.cfgmgr.get_dict(["PW", "Country"])) == {"PW": "", "Country": "DE"}  # both left at their defaults


def test_networking_put_of_a_body_that_is_not_json_answers_code_1() -> None:
    product = _make_service()
    status, resp = _dispatch(product, "PUT", "/networking", b"{not valid json")
    assert (status, resp) == (200, {"res": "ERR", "code": 1, "descr": "Invalid JSON request", "result": {}})
    assert product.calls == {}


def test_networking_put_of_a_json_array_or_scalar_answers_code_1() -> None:
    product = _make_service()
    for body in ([1, 2, 3], "just a string", 42, True, None):
        status, resp = _dispatch(product, "PUT", "/networking", json.dumps(body).encode())
        assert (status, resp) == (200, {"res": "ERR", "code": 1, "descr": "Invalid JSON request", "result": {}}), body
    assert product.calls == {}


def test_networking_put_of_an_empty_object_is_ok_and_changes_nothing() -> None:
    product = _make_service()
    assert _dispatch(product, "PUT", "/networking", {}) == (200, {"res": "OK", "code": 0, "descr": "Command executed", "result": {}})
    assert product.calls == {}


def test_networking_put_answers_an_unknown_key_invalid_beside_a_valid_one() -> None:
    # (owner, 2026-09-26): an unknown key is a per-field Invalid, never a whole-request refusal.
    product = _make_service()
    _status, resp = _dispatch(product, "PUT", "/networking", {"Hostname": "NewHost", "Bogus": 1})
    assert (resp["res"], resp["result"]) == ("OK", {"Hostname": "Valid", "Bogus": "Invalid"})
    assert run(product.wifi.cfgmgr.get_dict(["Hostname"])) == {"Hostname": "NewHost"}


def test_networking_put_of_the_hotspot_password_applies_in_the_identity_group_and_reconnects() -> None:
    product = _make_service()
    assert _dispatch(product, "PUT", "/networking", {"HotspotPW": "newpass123"})[1]["result"] == {"HotspotPW": "Valid"}
    assert product.calls == {"reconnect_wifi": 1}  # the next hotspot start configures it
    assert run(product.wifi.cfgmgr.get_dict(["HotspotPW"])) == {"HotspotPW": "newpass123"}
    assert _dispatch(product, "GET", "/networking")[1]["HotspotPW"] == "********"  # read back masked, like PW


def test_networking_put_of_a_hotspot_password_outside_8_to_63_characters_is_refused() -> None:
    product = _make_service()
    assert _dispatch(product, "PUT", "/networking", {"HotspotPW": "short"})[1]["result"] == {"HotspotPW": "Invalid"}
    assert product.calls == {}  # nothing changed, so no reconnect
    assert run(product.wifi.cfgmgr.get_dict(["HotspotPW"])) == {"HotspotPW": "12345678"}  # the build-time default kept


def test_networking_put_of_the_led_field_alone_never_reconnects() -> None:
    # Toggling the Wi-Fi status LED never reconnects: its group carries no hook.
    product = _make_service()
    assert _dispatch(product, "PUT", "/networking", {"LEDWifiOn": False})[1]["result"] == {"LEDWifiOn": "Valid"}
    assert run(product.wifi.cfgmgr.get_dict(["LEDWifiOn"])) == {"LEDWifiOn": False}
    assert product.calls == {} and product.wifi._reconnect_fresh is False


def test_networking_put_of_an_identity_field_and_the_led_field_reconnects_once() -> None:
    product = _make_service()
    _status, resp = _dispatch(product, "PUT", "/networking", {"Hostname": "NewHost", "LEDWifiOn": False})
    assert resp["result"] == {"Hostname": "Valid", "LEDWifiOn": "Valid"}
    assert product.calls == {"reconnect_wifi": 1}  # the identity group changed; the LED group adds none


def test_networking_put_of_ssid_reaches_the_identity_group_only() -> None:
    product = _make_service()
    assert _dispatch(product, "PUT", "/networking", {"SSID": "Hacked"})[1]["result"] == {"SSID": "Valid"}
    assert product.calls == {"reconnect_wifi": 1}
    assert run(product.wifi.cfgmgr.get_dict(["SSID", "LEDWifiOn"])) == {"SSID": "Hacked", "LEDWifiOn": True}


def test_an_identity_change_lands_the_unit_in_the_fresh_boot_state() -> None:
    # (owner, 2026-10-08): "Any change of credentials, no matter from which side, lands in the same mode as "initial
    # connection attempt after a fresh boot"" - here from the hotspot after its boot streak and from an established link.
    async def select(mode: int) -> bool:
        return mode >= 0

    seeking = _wifi_const("_PHASE_STA_SEEKING")
    for phase in (_wifi_const("_PHASE_HOTSPOT"), _wifi_const("_PHASE_STA_ESTABLISHED")):
        product = _make_service()
        wifi = product.wifi
        wifi._select_wifi_mode = select  # type: ignore[method-assign]  # the mode switch is not under test
        wifi._conn_phase, wifi._hotspot_started_once = phase, True
        assert _dispatch(product, "PUT", "/networking", {"SSID": "NewNet", "PW": "newpassword"})[1]["result"] == {"SSID": "Valid", "PW": "Valid"}, phase
        assert (wifi._reconn_wifi, wifi._reconnect_fresh) == (True, True), phase
        asy_wifi_service.asyncio = _YieldOnlyAsyncio()  # type: ignore[assignment]
        try:
            run(wifi._handle_reconnect_trigger())
        finally:
            asy_wifi_service.asyncio = asyncio
        assert (wifi._connection_failures, wifi._hotspot_started_once, wifi._conn_phase) == (0, False, seeking), phase
        assert (wifi._reconn_wifi, wifi._reconnect_fresh) == (False, False), phase
    led_only = _make_service()
    _dispatch(led_only, "PUT", "/networking", {"LEDWifiOn": False})
    assert (led_only.wifi._reconn_wifi, led_only.wifi._reconnect_fresh) == (False, False)


# ---------------------------------------------------------------------------
# Microdot's own semantics on the product app: the shaped 404/405 and the service's 500 path.
# ---------------------------------------------------------------------------


def test_an_unregistered_path_answers_the_shaped_404() -> None:
    assert _dispatch(_make_service(), "GET", "/no/such/route") == (404, ar.make_response(404))


def test_a_put_to_the_get_only_measurements_route_answers_the_shaped_405() -> None:
    assert _dispatch(_make_service(), "PUT", "/measurements", {}) == (405, ar.make_response(405))


def test_a_raising_reader_reaches_the_services_own_500_path() -> None:
    # Microdot's blanket catch (SPECIFICATION.md A.5) hands a raise past every guard of ours to the service's handler.
    product = _make_service(_RaisingBMP)
    assert _dispatch(product, "PUT", "/sensors", {product.bmp.name: {"PresOvers": 8}}) == (500, ar.make_response(500))
    nums = run(product.service.get_error_counter())[product.service.name]["ErrNum"]
    assert isinstance(nums, list) and nums[-1] == code("E", "UNEXPECTED"), nums


# ---------------------------------------------------------------------------
# PUT /sensors: each reader under its own name. A bus fault is that field's "Failed" inside a normal 200 envelope,
# never a raise or a bare Microdot 500 (SPECIFICATION.md Part C.4's layer-3 "never raises").
# ---------------------------------------------------------------------------


def test_sensors_put_to_a_bmp3xx_on_a_dead_bus_fails_the_field_and_keeps_the_default() -> None:
    product = _make_service()
    _nak_i2c_address(product.bus0, 0x77)  # unreachable, like a dead or disconnected sensor
    name = product.bmp.name
    assert _dispatch(product, "PUT", "/sensors", {name: {"PresOvers": 8}}) == (200, ar.make_response(0, result={name: {"PresOvers": "Failed"}}))
    # The failed-push recovery chain puts the stored value back; the bus is dead from the start, so the pre-write
    # snapshot rung is the schema default (1), the chain's last rung.
    assert run(product.bmp.cfgmgr.get_dict(["PresOvers"])) == {"PresOvers": 1}


def test_sensors_put_to_a_bmp3xx_with_a_failed_write_recovers_from_the_live_getter() -> None:
    # The write half fails only, so the registered getter reads the chip's real state back.
    product = _make_service()
    _register_device(product.bus0, 0x77)
    run(product.bmp._bmp.set_pressure_oversampling(2))  # desync: the chip register holds 2, the store the default 1
    _fault_i2c_write(product.bus0, OSError(errno_mod.EIO, "no ACK on write"))
    name = product.bmp.name
    assert _dispatch(product, "PUT", "/sensors", {name: {"PresOvers": 8}})[1]["result"] == {name: {"PresOvers": "Failed"}}
    assert run(product.bmp.cfgmgr.get_dict(["PresOvers"])) == {"PresOvers": 2}  # neither the failed 8 nor the snapshot's 1


def test_sensors_put_of_the_sgp40_reset_and_backup_period_round_trips() -> None:
    # ResetVOC is a command-only, never-persisted field dispatched through the same generic path as a stored one.
    product = _make_service()
    name = product.sgp.name
    assert _dispatch(product, "PUT", "/sensors", {name: {"ResetVOC": True, "BackupPeriod": 5}}) == (200, ar.make_response(0, result={name: {"ResetVOC": "Valid", "BackupPeriod": "Valid"}}))
    assert product.sgp._reset_pending is True  # the command field's push callback fired
    assert run(product.sgp.cfgmgr.get_dict(["BackupPeriod"])) == {"BackupPeriod": 5}
    assert run(product.sgp.cfgmgr.get_dict(["ResetVOC"])) is None  # never stored (get_dict() is all-or-nothing per key)


def test_sensors_put_to_an_sgp40_on_a_dead_bus_still_succeeds() -> None:
    # SGP40's setter surface is bus-free: ResetVOC only arms in-RAM flags for _read_loop(), where a bus fault surfaces.
    product = _make_service()
    _nak_i2c_address(product.bus1, 0x59)
    name = product.sgp.name
    assert _dispatch(product, "PUT", "/sensors", {name: {"ResetVOC": True}})[1]["result"] == {name: {"ResetVOC": "Valid"}}
    assert product.sgp._reset_pending is True


def test_sensors_put_to_an_sgp40_whose_config_write_fails_logs_it_after_the_flush() -> None:
    # write_config() stages and hands the file write to its own task (SPECIFICATION.md Part F.2): the response reads
    # Valid, the value stays in effect (C.7.3) and the failure lands on the store's log once the flush runs.
    product = _make_service()
    _break_cfg_file(product.sgp.cfgmgr._config_file)
    name = product.sgp.name

    async def put_then_flush() -> "JsonDict":
        with FastAsyncSleep():
            res = await product.app.dispatch_request(_make_request(product.app, "PUT", "/sensors", {name: {"BackupPeriod": 5, "ResetVOC": True}}))
        await product.sgp.cfgmgr.flush_pending()
        return _json(res)

    assert run(put_then_flush())["result"] == {name: {"BackupPeriod": "Valid", "ResetVOC": "Valid"}}
    assert product.sgp._reset_pending is True
    assert run(product.sgp.cfgmgr.get_dict(["BackupPeriod"])) == {"BackupPeriod": 5}
    nums = run(product.sgp.cfgmgr.pr.get_log())[product.sgp.cfgmgr.name]["ErrNum"]
    assert isinstance(nums, list) and nums[-1] == code("E", "CFG_FILE_WRITE"), nums


def test_sensors_put_writes_each_scd30_field_through_the_real_driver() -> None:
    # One request per product-schema field: "Valid" and that field's own command word on the bus (Interface
    # Description 1.4); ContMeas has no stored value and no schema entry of its own (asy_scd30_driver.py).
    cases: tuple[tuple[str, cm.CfgValue, bytes], ...] = (
        (_VAL_TEMP_OFFSET[0][0], 4.5, b"\x54\x03"),
        (_VAL_MEAS_INTERVAL[0][0], 10, b"\x46\x00"),
        (_VAL_AMB_PRES[0][0], 1013, b"\x00\x10"),
        (_VAL_ALTITUDE[0][0], 200, b"\x51\x02"),
        (_VAL_FORCE_CAL_REF[0][0], 500, b"\x52\x04"),
        (_VAL_SELF_CAL[0][0], True, b"\x53\x06"),
        ("ContMeas", False, b"\x01\x04"),
    )
    for key, value, word in cases:
        product = _make_service()
        _queue_scd_snapshot(product.scd)
        name = product.scd.name
        assert _dispatch(product, "PUT", "/sensors", {name: {key: value}}) == (200, ar.make_response(0, result={name: {key: "Valid"}})), key
        writes = _scd_writes(product.scd)
        assert len(writes) == 1 and writes[0][:2] == word, (key, writes)


def test_sensors_put_keeps_an_scd30_frc_setting_in_the_config_file() -> None:
    # The readiness settings are file-stored config: "Valid", no command on the bus, the value read back.
    product = _make_service()
    key, name = _VAL_FRC_NOISE[0][0], product.scd.name
    assert _dispatch(product, "PUT", "/sensors", {name: {key: 30.0}})[1]["result"] == {name: {key: "Valid"}}
    assert _scd_writes(product.scd) == []
    assert run(product.scd.cfgmgr.get_dict([key])) == {key: 30.0}


def test_sensors_put_applies_several_scd30_fields_in_the_fixed_order() -> None:
    product = _make_service()
    _queue_scd_snapshot(product.scd)
    name = product.scd.name
    result = _dispatch(product, "PUT", "/sensors", {name: {"ForceCalRef": 500, "AmbPres": 1013, "MeasInterval": 10}})[1]["result"]
    assert result == {name: {"MeasInterval": "Valid", "AmbPres": "Valid", "ForceCalRef": "Valid"}}
    # The command frames reach the bus in the driver's fixed order, each with its own value; the CRC byte is covered
    # byte for byte against the Interface Description in test_asy_scd30_driver.py.
    writes = _scd_writes(product.scd)
    assert [w[:4] for w in writes] == [b"\x46\x00\x00\x0a", b"\x00\x10\x03\xf5", b"\x52\x04\x01\xf4"], writes


def test_sensors_put_of_the_scd30_ambpres_bypass_value_is_sent() -> None:
    # AmbPres 0 is the documented "compensation off" special value: valid, and sent although it equals the stored 0
    # (the command also starts continuous measurement).
    product = _make_service()
    _queue_scd_snapshot(product.scd)
    name = product.scd.name
    assert _dispatch(product, "PUT", "/sensors", {name: {"AmbPres": 0}})[1]["result"] == {name: {"AmbPres": "Valid"}}
    assert _scd_writes(product.scd) == [b"\x00\x10\x00\x00\x81"]


def test_sensors_put_of_an_out_of_range_scd30_field_never_reaches_the_bus() -> None:
    product = _make_service()
    _queue_scd_snapshot(product.scd)
    name = product.scd.name
    result = _dispatch(product, "PUT", "/sensors", {name: {"MeasInterval": 1, "ForceCalRef": 500}})[1]["result"]  # MeasInterval min is 2
    assert result == {name: {"MeasInterval": "Invalid", "ForceCalRef": "Valid"}}
    assert [w[:4] for w in _scd_writes(product.scd)] == [b"\x52\x04\x01\xf4"]  # only the valid field was sent


def test_sensors_put_of_a_faulted_scd30_write_fails_that_field_and_logs_it() -> None:
    # The snapshot is stubbed so the one-shot fault lands on MeasInterval, first in the fixed order, and AmbPres applies.
    product = _make_service()

    async def stored() -> "tuple[float, int, int, int, int, bool]":
        return 0.0, 2, 0, 0, 400, False

    product.scd._scd.get_config_snapshot = stored  # type: ignore[method-assign]
    _fault_next_i2c_write(product.scd)
    name = product.scd.name
    assert _dispatch(product, "PUT", "/sensors", {name: {"MeasInterval": 10, "AmbPres": 1013}}) == (200, ar.make_response(0, result={name: {"MeasInterval": "Failed", "AmbPres": "Valid"}}))
    assert [w[:4] for w in _scd_writes(product.scd)] == [b"\x00\x10\x03\xf5"]  # the faulted write never reached the log
    nums = run(product.scd.get_error_counter())[name]["ErrNum"]
    assert isinstance(nums, list) and nums[-1] == code("E", "CHIP_SET"), nums  # counted on SCD30's own log


# ---------------------------------------------------------------------------
# Time settings over /networking (the NTP group forces one resync per valid change) and /system (the offsets, no hook).
# ---------------------------------------------------------------------------


def test_networking_get_carries_the_ntp_defaults_and_a_prior_write() -> None:
    product = _make_service()
    defaults = {"NTPHost": "pool.ntp.org", "NTPOffset": 0, "NTPInterval": 12, "DNSFallback": ""}
    status, body = _dispatch(product, "GET", "/networking")
    assert status == 200 and {k: body[k] for k in defaults} == defaults, body
    _dispatch(product, "PUT", "/networking", {"NTPHost": "time.example.org"})
    assert _dispatch(product, "GET", "/networking")[1]["NTPHost"] == "time.example.org"


def test_system_get_carries_the_offsets_and_the_debug_level() -> None:
    assert _dispatch(_make_service(), "GET", "/system") == (200, {"DebugLevel": 0, "GMTOffset": 3600, "DSTOffset": 3600})


def test_networking_put_of_the_ntp_host_persists_and_forces_one_resync() -> None:
    product = _make_service()
    product.ntp._ntp_retries = 3  # a failing-sync streak in progress; ntp_force_sync() clears it
    assert _dispatch(product, "PUT", "/networking", {"NTPHost": "time.example.org"})[1]["result"] == {"NTPHost": "Valid"}
    assert run(product.ntp.cfgmgr.get_dict(["NTPHost"])) == {"NTPHost": "time.example.org"}
    assert (product.calls, product.ntp._ntp_retries) == ({"ntp_force_sync": 1}, 0)


def test_networking_put_of_the_dns_fallback_persists_without_a_resync() -> None:
    product = _make_service()
    assert _dispatch(product, "PUT", "/networking", {"DNSFallback": "9.9.9.9,1.1.1.1"})[1]["result"] == {"DNSFallback": "Valid"}
    assert run(product.ntp.cfgmgr.get_dict(["DNSFallback"])) == {"DNSFallback": "9.9.9.9,1.1.1.1"}
    assert product.calls == {}  # its own group has no hook: the next attempt reads the list


def test_networking_put_can_empty_the_dns_fallback() -> None:
    product = _make_service()
    _dispatch(product, "PUT", "/networking", {"DNSFallback": "9.9.9.9"})
    assert _dispatch(product, "PUT", "/networking", {"DNSFallback": ""})[1]["result"] == {"DNSFallback": "Valid"}
    assert run(product.ntp.cfgmgr.get_dict(["DNSFallback"])) == {"DNSFallback": ""}


def test_networking_put_of_a_malformed_dns_fallback_is_refused_and_logged() -> None:
    for value in ("8.8.8.8,", "a.b.c.d", "1.2.3.4,5.6.7.8,9.9.9.9,1.1.1.1", "8.8.8.8 ,1.1.1.1", "256.1.1.1"):
        product = _make_service()
        assert _dispatch(product, "PUT", "/networking", {"DNSFallback": value}) == (200, ar.make_response(0, result={"DNSFallback": "Invalid"})), value
        assert run(product.ntp.cfgmgr.get_dict(["DNSFallback"])) == {"DNSFallback": ""}, value  # nothing stored
        nums = run(product.ntp.get_error_counter())[product.ntp.name]["ErrNum"]
        assert isinstance(nums, list) and nums[-1] == code("E", "BAD_ARG"), value


def test_system_put_of_an_out_of_range_offset_is_refused_without_a_resync() -> None:
    product = _make_service()
    assert _dispatch(product, "PUT", "/system", {"GMTOffset": 99999})[1]["result"] == {"GMTOffset": "Invalid"}  # max is 43200
    assert run(product.ntp.cfgmgr.get_dict(["GMTOffset"])) == {"GMTOffset": 3600}  # the default kept
    assert product.calls == {}


def test_system_put_of_a_valid_offset_persists_without_a_resync() -> None:
    product = _make_service()
    assert _dispatch(product, "PUT", "/system", {"GMTOffset": 7200})[1]["result"] == {"GMTOffset": "Valid"}
    assert run(product.ntp.cfgmgr.get_dict(["GMTOffset", "DSTOffset"])) == {"GMTOffset": 7200, "DSTOffset": 3600}
    assert product.calls == {}  # the offsets' group has no hook: the next conversion reads them


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
