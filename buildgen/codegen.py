"""Code generation: emits the equivalent of a hand-written `sensortask_<device>.py`
(SPECIFICATION.md Part A.7's construction-order shape) plus its `boot_entry/<device>_boot.py`
sibling, from a fully-validated `DeviceModel` (`buildgen.validate.build_model()`) and its
topological construction order (`buildgen.graph.build_construction_order()`).

The construction/wiring core (watchdog/conn/ntp/buses, each instance in dependency order, every
`_WIRING` reference resolved, notification's `register()`/`finalize()`, `device.wiring`'s
"setter"-mode calls) is templated directly from the TOML's own facts - this is the part this
session's own tests hold to the same bar as the validator. The webserver/task-supervisor tail is
genuinely uniform boilerplate across every device - `sensortask_wozi.py`/`sensortask_dev.py` are
byte-for-byte the same shape (confirmed directly diffing the two; only pin/wiring constants
differ) - so it's emitted from a fixed template too, parameterized only by which optional
instances exist; see this session's PR description for how deep this session's own correctness
proof goes for that slice specifically (syntactic validity + structural shape, not execution under
a real interpreter - Session 5's digital-twin generalization is what actually boots a generated
module)."""

import keyword
from dataclasses import dataclass

from buildgen.defaults import default_class_name
from buildgen.errors import BuildError
from buildgen.model import DeviceModel, InstanceSpec, instance_label, resolve_instance_key
from buildgen.wiring import WiringField

_MAX_MODULE_ERROR = 5
_DNS_TIMEOUT_MS = 500
_DNS_TRIES = 1
_NTP_FETCH_TIMEOUT_MS = 5000

# The generator's own fixed catalog for notification's per-signal getters (BUILD_CHAIN_PLAN.md's
# "Each notification signal's own threshold default/range and flash color are a related, still-open
# question for Session 3" - resolved here: every real device TOML today uses identical
# threshold/color values with no per-device override in the schema, so this session hardcodes the
# known catalog exactly as sensortask_wozi.py/sensortask_dev.py already do, rather than inventing a
# TOML field neither of those two hand-written files has. See this session's PR description for the
# "flagged for a future TOML-schema extension" note this implies.
_KNOWN_SIGNALS: "dict[str, tuple[str, str, str, tuple[int, int, int]]]" = {
    # toml key: (signal name, const name, field_schema literal, color)
    "warn_co2": ("WarnCO2", "_FIELD_WARN_CO2", '(("WarnCO2", "int", 1600, 0, 3000, None),)', (1, 0, 0)),
    "warn_voc": ("WarnVOC", "_FIELD_WARN_VOC", '(("WarnVOC", "int", 350, 0, 500, None),)', (0, 1, 0)),
    "warn_hum": ("WarnHum", "_FIELD_WARN_HUM", '(("WarnHum", "float", 65.0, 0.0, 100.0, None),)', (0, 0, 1)),
}


def _identifier(name: str, device: str, instance: "str | None"=None, field: "str | None"=None) -> str:
    # instance=/field= carried through so this matches every other BuildError call site's
    # "name exactly what and where" contract (BUILD_CHAIN_PLAN.md's quality bar) - it was the one
    # raise in the package that named only the device.
    if not name.isidentifier() or keyword.iskeyword(name):
        raise BuildError(device, f"{name!r} is not usable as a generated Python identifier", instance=instance, field=field)
    return name


@dataclass
class _Ctx:
    model: DeviceModel

    def bus_var(self, bus_id: str) -> str:
        return _identifier(bus_id, self.model.device, instance=f"bus.{bus_id}", field=bus_id)

    def instance_var(self, key: "tuple[str, str]") -> str:
        label = instance_label(key)
        return _identifier(label, self.model.device, instance=label, field="driver" if not key[1] else "name_ext")

    def default_provider_expr(self, toml_field: str, value: dict) -> str:
        # §2.6's generated-code shape: construct the default provider inline, at the exact
        # call-site the real wiring expression would occupy - never a separate named global.
        class_name = default_class_name(toml_field)
        kwargs = ", ".join(f"{k}={v!r}" for k, v in value.items() if k != "default")
        return f"{class_name}({kwargs})"

    def wiring_expr(self, spec: InstanceSpec, wf: WiringField) -> str:
        value = spec.wiring[wf.toml_field]
        if isinstance(value, dict) and value.get("default") is True:
            provider_expr = self.default_provider_expr(wf.toml_field, value)
            return provider_expr if wf.mode == "kwarg" else f"{provider_expr}.{wf.target}"
        target_key = resolve_instance_key(self.model, value)
        var = self.instance_var(target_key)
        return var if wf.mode == "kwarg" else f"{var}.{wf.target}"

    def value_wiring_kwargs(self, spec: InstanceSpec, toml_field: str) -> "list[tuple[str, str]]":
        # §2.9's per-value measurement wiring: resolves to either a real {source, field} reference
        # (any producer, matched by attribute name) or an explicit default provider - always
        # (source_kwarg, field_kwarg) rendered as a pair, mirroring how _DefaultTemperatureSource/
        # _DefaultHumiditySource's get_data() always exposes a single "value" attribute (§10.1 item 1).
        vwf = next(f for f in spec.value_wiring_schema if f.toml_field == toml_field)
        value = spec.wiring[toml_field]
        if isinstance(value, dict) and value.get("default") is True:
            provider_expr = self.default_provider_expr(toml_field, value)
            return [(vwf.source_kwarg, provider_expr), (vwf.field_kwarg, repr("value"))]
        source_key = resolve_instance_key(self.model, value["source"])
        source_var = self.instance_var(source_key)
        return [(vwf.source_kwarg, source_var), (vwf.field_kwarg, repr(value["field"]))]


def _wf(spec: InstanceSpec, toml_field: str) -> "WiringField | None":
    for wf in spec.wiring_schema:
        if wf.toml_field == toml_field:
            return wf
    return None


def _kw(pairs: "list[tuple[str, str]]") -> str:
    return ", ".join(f"{k}={v}" for k, v in pairs)


def _defaulted_wiring_fields(spec: InstanceSpec) -> "list[str]":
    # Every TOML field on this instance that opted into §2's wiring-defaults mechanism
    # ({default = true, ...}) - covers both _WIRING-based (signal_sink) and _VALUE_WIRING-based
    # (temperature_source/humidity_source) fields uniformly, since both live in spec.wiring the
    # same way. Used to decide which _Default<Field> classes this instance's import line needs.
    return [f for f, v in spec.wiring.items() if isinstance(v, dict) and v.get("default") is True]


def _build_call(spec: InstanceSpec, ctx: _Ctx) -> str:
    class_name = spec.driver_info.class_name  # type: ignore[union-attr]
    driver = spec.driver
    f = spec.fields
    pos: list[str] = []
    kw: list[tuple[str, str]] = []
    fram_wf = _wf(spec, "fram_target")
    fram_kw = (fram_wf.target, ctx.wiring_expr(spec, fram_wf)) if fram_wf is not None and "fram_target" in spec.wiring else None

    if driver == "scd30":
        pos = [ctx.bus_var(f["bus"]), str(f["irq_pin"])]
        if "trigger_sec" in f:
            kw.append(("trigger_sec", str(f["trigger_sec"])))
        kw.append(("max_module_error", "_MAX_MODULE_ERROR"))
        if spec.name_ext:
            kw.append(("name_ext", repr(spec.name_ext)))
        if fram_kw:
            kw.append(fram_kw)
        kw.append(("debug", "debug"))
    elif driver == "sgp40":
        pos = [ctx.bus_var(f["bus"])]
        kw.extend(ctx.value_wiring_kwargs(spec, "temperature_source"))
        kw.extend(ctx.value_wiring_kwargs(spec, "humidity_source"))
        kw.append(("max_module_error", "_MAX_MODULE_ERROR"))
        if spec.name_ext:
            kw.append(("name_ext", repr(spec.name_ext)))
        kw.append(("cfg_path", "cfg_path"))
        if fram_kw:
            kw.append(fram_kw)
        kw.append(("fram_ntp_callback", "ntp.ntp_issynced"))
        kw.append(("debug", "debug"))
    elif driver == "bmp3xx":
        pos = [ctx.bus_var(f["bus"])]
        if "address" in f:
            kw.append(("address", hex(f["address"])))
        if "trigger_sec" in f:
            kw.append(("trigger_sec", str(f["trigger_sec"])))
        kw.append(("max_module_error", "_MAX_MODULE_ERROR"))
        if spec.name_ext:
            kw.append(("name_ext", repr(spec.name_ext)))
        kw.append(("cfg_path", "cfg_path"))
        if fram_kw:
            kw.append(fram_kw)
        kw.append(("debug", "debug"))
    elif driver == "fram":
        pos = [ctx.bus_var(f["bus"]), str(f["cs_pin"])]
        kw.append(("max_size", hex(f["max_size"])))
        kw.append(("debug", "debug"))
    elif driver == "neopixel":
        pos = [str(f["pin"])]
        if fram_kw:
            kw.append(fram_kw)
        kw.append(("debug", "debug"))
    elif driver == "notification":
        signal_wf = _wf(spec, "signal_sink")
        assert signal_wf is not None
        pos = [ctx.wiring_expr(spec, signal_wf), "ntp.cettime"]
        kw.append(("max_module_error", "_MAX_MODULE_ERROR"))
        kw.append(("cfg_path", "cfg_path"))
        if fram_kw:
            kw.append(fram_kw)
        kw.append(("debug", "debug"))
    else:
        raise BuildError(ctx.model.device, f"codegen has no build recipe for driver {driver!r} - add one to buildgen.codegen._build_call", instance=spec.label)

    args = ", ".join(pos + ([_kw(kw)] if kw else []))
    return f"{class_name}({args})"


def _notification_lines(spec: InstanceSpec, ctx: _Ctx, var: str) -> "list[str]":
    lines = []
    for toml_field, sig in spec.wiring.items():
        if not toml_field.startswith("warn_"):
            continue
        known = _KNOWN_SIGNALS.get(toml_field)
        if known is None:
            raise BuildError(
                ctx.model.device,
                f"notification declares wiring.{toml_field}, but the generator's built-in signal catalog only knows {sorted(_KNOWN_SIGNALS)} for now - "
                "add it to buildgen.codegen._KNOWN_SIGNALS (with a real threshold schema/color), or flag it as a future TOML-schema extension",
                instance=spec.label,
                field=toml_field,
            )
        name, const_name, _schema_literal, color = known
        source_var = ctx.instance_var(resolve_instance_key(ctx.model, sig["source"]))
        lines.append(f'{var}.register(NotificationSignal({name!r}, {source_var}, {sig["field"]!r}, {const_name}, {color!r}))')
    lines.append(f"{var}.finalize()")
    return lines


def generate_module_source(model: DeviceModel, construction_order: "list") -> str:
    ctx = _Ctx(model)
    dev = model.doc["device"]
    instances = model.instances
    have = {spec.driver for spec in instances.values()}
    order_position = {node: i for i, node in enumerate(construction_order)}
    sensor_specs = sorted((s for s in instances.values() if s.driver_info and s.driver_info.kind == "sensor"), key=lambda s: order_position[s.key])
    sensor_vars = [ctx.instance_var(spec.key) for spec in sensor_specs]

    lines: list[str] = []
    lines.append(f'"""Generated by buildgen from devices/{model.device}.toml - do not edit by hand.')
    lines.append('Mirrors src/sensortask_wozi.py\'s construction-order shape (SPECIFICATION.md Part A.7)."""')
    lines.append("")
    lines.append("import asyncio")
    lines.append("import time")
    lines.append("from asyncio import ThreadSafeFlag")
    lines.append("")
    lines.append("import frozen_html  # type: ignore[import-not-found]  # noqa: F401")
    lines.append("from machine import WDT")
    lines.append("from microdot import Microdot  # type: ignore[import-not-found]")
    lines.append("from micropython import const")
    lines.append("")
    lines.append("import asy_i2c_driver")
    lines.append("import asy_spi_driver")
    lines.append("import config_manager as cm")
    for spec in sorted(instances.values(), key=lambda s: s.order_index):
        assert spec.driver_info is not None
        if spec.driver == "notification":
            continue  # imported below, together with NotificationSignal
        extra = "".join(f", {default_class_name(f)}" for f in _defaulted_wiring_fields(spec))
        lines.append(f"from {spec.driver_info.module} import {spec.driver_info.class_name}{extra}")
    if "notification" in have:
        notif_extra_spec = next(s for s in instances.values() if s.driver == "notification")
        notif_extra = "".join(f", {default_class_name(f)}" for f in _defaulted_wiring_fields(notif_extra_spec))
        lines.append(f"from asy_notification_service import NotificationCoordinator, NotificationSignal{notif_extra}")
    lines.append("from asy_ntp_client import AsyNtpClient")
    lines.append("from asy_webserver_service import SettingsGroup, WebserverService")
    lines.append("from asy_wifi_service import AsyConnTime")
    lines.append("from system_service import SystemService")
    lines.append("")
    lines.append("try:")
    lines.append("    from typing import TYPE_CHECKING")
    lines.append("except ImportError:")
    lines.append("    TYPE_CHECKING = False")
    lines.append("")
    lines.append("if TYPE_CHECKING:")
    lines.append("    from collections.abc import Callable")
    lines.append("    from typing import Any")
    lines.append("")
    lines.append(f"_MAX_MODULE_ERROR = const({_MAX_MODULE_ERROR})")
    lines.append(f"_DNS_TIMEOUT_MS = const({_DNS_TIMEOUT_MS})")
    lines.append(f"_DNS_TRIES = const({_DNS_TRIES})")
    lines.append(f"_NTP_FETCH_TIMEOUT_MS = const({_NTP_FETCH_TIMEOUT_MS})")
    lines.append("")

    if "notification" in have:
        notif_spec = next(s for s in instances.values() if s.driver == "notification")
        for toml_field in notif_spec.wiring:
            if toml_field.startswith("warn_") and toml_field in _KNOWN_SIGNALS:
                _name, const_name, schema_literal, _color = _KNOWN_SIGNALS[toml_field]
                lines.append(f'{const_name}: "cm.ConfigSchema" = {schema_literal}')
        lines.append("")

    all_vars = [ctx.bus_var(b) for b in model.doc["bus"]] + [ctx.instance_var(k) if isinstance(k, tuple) else k for k in construction_order]
    lines.append("watchdog: \"WDT | None\" = None")
    for name in all_vars:
        lines.append(f'{name}: "Any | None" = None')
    lines.append('webserver: "WebserverService | None" = None')
    lines.append('timers_running: "ThreadSafeFlag | None" = None')
    lines.append("")

    _emit_callbacks(lines, have)

    lines.append("async def build_system(")
    lines.append("    *, cfg_path: str = \"\", debug: int | None = None, web_host: str = \"0.0.0.0\", web_port: int = 80")
    lines.append(") -> None:")
    lines.append('    """Construct every module and run the grouped setup() batch - generated, mirrors build_system()\'s')
    lines.append('    documented shape in every hand-written sensortask_*.py (SPECIFICATION.md Part A.7)."""')
    global_names = ["watchdog"] + all_vars + ["webserver", "timers_running"]
    lines.append("    global " + ", ".join(global_names))
    lines.append("")
    lines.append("    watchdog = WDT(timeout=8000)")
    lines.append(f"    conn = AsyConnTime(conn_fail_to_hotspot={dev['conn_fail_to_hotspot']}, hotspot_time_min={dev['hotspot_time_min']}, max_module_error=_MAX_MODULE_ERROR, cfg_path=cfg_path, debug=debug)")
    lines.append("    ntp = AsyNtpClient(conn.get_wifi_mode_lock(), conn.network_available, conn.get_dns_server_ip, max_module_error=_MAX_MODULE_ERROR, dns_timeout_ms=_DNS_TIMEOUT_MS, dns_tries=_DNS_TRIES, ntp_fetch_timeout_ms=_NTP_FETCH_TIMEOUT_MS, cfg_path=cfg_path, debug=debug)")
    for bus_id, bus_table in model.doc["bus"].items():
        var = ctx.bus_var(bus_id)
        if bus_id.startswith("i2c"):
            port = bus_id[len("i2c") :]  # "i2c0" -> "0" - strip the prefix, don't scan for digits (the "2" in "i2c" is itself a digit)
            timeout_kw = f", timeout={bus_table['timeout']}" if "timeout" in bus_table else ""
            lines.append(f"    {var} = asy_i2c_driver.I2C({port}, {bus_table['scl_pin']}, {bus_table['sda_pin']}, frequency={bus_table['frequency']}{timeout_kw})")
        else:
            port = bus_id[len("spi") :]  # "spi0" -> "0"
            lines.append(f"    {var} = asy_spi_driver.SPI({port}, {bus_table['sck_pin']}, {bus_table['mosi_pin']}, {bus_table['miso_pin']})")

    for node in construction_order:
        if node in ("conn", "ntp"):
            continue  # already emitted above, unconditionally, ahead of the buses
        if node == "sysfunct":
            device_wiring = model.doc.get("device", {}).get("wiring", {})
            fram_target = device_wiring.get("fram_target")
            fram_arg = f", fram={ctx.instance_var(resolve_instance_key(model, fram_target))}" if fram_target else ""
            lines.append(f"    sysfunct = SystemService(ntp.ntp_issynced, watchdog=watchdog{fram_arg}, cfg_path=cfg_path, debug=debug)")
            continue
        assert isinstance(node, tuple)
        spec = instances[node]
        var = ctx.instance_var(node)
        lines.append(f"    {var} = {_build_call(spec, ctx)}")
        if spec.driver == "notification":
            lines.extend(f"    {line}" for line in _notification_lines(spec, ctx, var))

    device_wiring = model.doc.get("device", {}).get("wiring", {})
    led_target = device_wiring.get("led_target")
    if led_target is not None:
        lines.append(f"    conn.set_ext_led({ctx.instance_var(resolve_instance_key(model, led_target))})")

    lines.append("")
    _emit_webserver(lines, model, ctx, have, sensor_vars)

    lines.append("    timers_running = ThreadSafeFlag()")
    lines.append("    sysfunct.set_level_setters(_collect_level_setters())")
    lines.append("")
    setup_order = ["sysfunct"]
    if "fram" in have:
        setup_order.append(ctx.instance_var(("fram", "")))
    setup_order += ["conn", "ntp"]
    for node in construction_order:
        if node in ("sysfunct",) or not isinstance(node, tuple):
            continue
        spec = instances[node]
        if spec.driver == "fram":
            continue
        if spec.driver_info and spec.driver_info.needs_setup:
            setup_order.append(ctx.instance_var(node))
    for name in setup_order:
        lines.append(f"    await {name}.setup()")
    lines.append("")

    _emit_collectors(lines, construction_order, ctx)

    lines.append("async def main(*, cfg_path: str = \"\", debug: int | None = None, web_host: str = \"0.0.0.0\", web_port: int = 80) -> None:")
    lines.append("    await build_system(cfg_path=cfg_path, debug=debug, web_host=web_host, web_port=web_port)")
    lines.append("    assert sysfunct is not None and ntp is not None")
    lines.append("    task_starters = _collect_task_starters()")
    lines.append("    timer_starters = _collect_timer_starters()")
    lines.append("    await sysfunct.start_timers(timer_starters)")
    lines.append("    await ntp.ntp_force_sync()")
    lines.append("    await sysfunct.start_and_check_tasks(task_starters)")
    lines.append("")
    return "\n".join(lines) + "\n"


def _emit_callbacks(lines: "list[str]", have: "set[str]") -> None:
    lines.append('def _gmtimestruct_to_dict(t: "Any") -> "dict[str, int] | None":')
    lines.append("    if t is None:")
    lines.append("        return None")
    lines.append('    return {"year": t[0], "month": t[1], "mday": t[2], "hour": t[3], "minute": t[4], "second": t[5], "weekday": t[6], "yearday": t[7]}')
    lines.append("")
    lines.append('async def _system_cmd_callback(cmd: str) -> bool:')
    lines.append("    assert sysfunct is not None")
    lines.append('    if cmd == "reboot":')
    lines.append("        sysfunct.reboot_system()")
    lines.append('    elif cmd == "bootloader":')
    lines.append("        sysfunct.reboot_bootloader()")
    lines.append('    elif cmd == "mempause":')
    lines.append("        sysfunct.pause_permanent_storage(300)")
    lines.append("    else:")
    lines.append("        return False")
    lines.append("    return True")
    lines.append("")
    if "neopixel" in have:
        lines.append('_FIELD_LED_R: "cm.FieldSchema" = ("r", "int", None, 0, 255, None)')
        lines.append('_FIELD_LED_G: "cm.FieldSchema" = ("g", "int", None, 0, 255, None)')
        lines.append('_FIELD_LED_B: "cm.FieldSchema" = ("b", "int", None, 0, 255, None)')
        lines.append('_FIELD_LED_T: "cm.FieldSchema" = ("t", "float", None, 0.5, 60.0, None)')
        lines.append("")
        lines.append('async def _notification_led_callback(payload: "dict[str, Any]") -> bool:')
        lines.append("    assert neopixel is not None")
        lines.append("    try:")
        lines.append("        r_err, r = cm.type_or_range_error(payload[\"r\"], _FIELD_LED_R)")
        lines.append("        g_err, g = cm.type_or_range_error(payload[\"g\"], _FIELD_LED_G)")
        lines.append("        b_err, b = cm.type_or_range_error(payload[\"b\"], _FIELD_LED_B)")
        lines.append("        t_err, t = cm.type_or_range_error(payload[\"t\"], _FIELD_LED_T)")
        lines.append("    except KeyError:")
        lines.append("        return False")
        lines.append("    if r_err or g_err or b_err or t_err:")
        lines.append("        return False")
        lines.append("    return await neopixel.request_signal(r, g, b, t)")
        lines.append("")
    if "notification" in have:
        lines.append('async def _notification_pause_callback(payload: int) -> bool:')
        lines.append("    assert notification is not None")
        lines.append("    await notification.set_override_led(payload)")
        lines.append("    return True")
        lines.append("")
    if "sgp40" in have:
        lines.append('async def _sgp_maintenance_status() -> "dict[str, Any]":')
        lines.append("    assert sgp40 is not None")
        lines.append("    backup_ts, restore_ts = await sgp40.get_mem_status()")
        lines.append('    return {"BackupTS": backup_ts, "RestoreTS": restore_ts}')
        lines.append("")
    lines.append('async def _networking_status() -> "dict[str, Any]":')
    lines.append("    assert conn is not None and ntp is not None")
    lines.append("    wifi_data = await conn.get_data()")
    lines.append("    ifcfg = conn.get_wlan_ifconfig()")
    lines.append("    ntp_data = await ntp.get_data()")
    lines.append("    return {")
    lines.append('        "WifiUptime": await conn.get_wifi_uptime(), "Mode": wifi_data.Mode, "Connected": wifi_data.Connected, "IP": wifi_data.IP,')
    lines.append('        "IPv4": None if ifcfg is None else ifcfg[0], "Subnet": None if ifcfg is None else ifcfg[1],')
    lines.append('        "Gateway": None if ifcfg is None else ifcfg[2], "DNS": None if ifcfg is None else ifcfg[3], "Rssi": conn.get_wlan_rssi(),')
    lines.append('        "NtpSynced": ntp_data.Synced, "NtpLastSyncAge": ntp_data.LastSyncAge, "NtpLastSync": ntp_data.TS,')
    lines.append("    }")
    lines.append("")
    lines.append('async def _system_status() -> "dict[str, Any]":')
    lines.append("    assert sysfunct is not None and ntp is not None")
    lines.append("    local_time = await ntp.cettime()")
    lines.append("    return {")
    lines.append('        "SysUptime": await sysfunct.get_uptime(), "BootSignature": await sysfunct.get_boot_signature(),')
    if "fram" in have:
        lines.append('        "MemPaused": fram.get_pause(),')
    lines.append('        "LocalTime": _gmtimestruct_to_dict(local_time), "UtcTime": _gmtimestruct_to_dict(time.gmtime()),')
    lines.append("    }")
    lines.append("")
    if "notification" in have:
        lines.append('async def _notification_status() -> "dict[str, Any]":')
        lines.append("    assert notification is not None")
        lines.append("    data = await notification.get_data()")
        lines.append('    return {"Triggered": data.Triggered, "TS": data.TS, "PauseTime": await notification.get_override_led()}')
        lines.append("")


def _emit_webserver(lines: "list[str]", model: DeviceModel, ctx: _Ctx, have: "set[str]", sensor_vars: "list[str]") -> None:
    lines.append("    app = Microdot()")
    lines.append("    webserver = WebserverService(")
    lines.append("        app,")
    lines.append(f"        sensors=({', '.join(sensor_vars)}{',' if len(sensor_vars) == 1 else ''}),  # type: ignore[arg-type]")
    lines.append("        settings={")
    lines.append('            "networking": [')
    lines.append('                SettingsGroup(conn, ("SSID", "PW", "Country", "Hostname"), post_fct=conn.reconnect_wifi),  # type: ignore[arg-type]')
    lines.append('                SettingsGroup(conn, ("LedWifiOn",)),  # type: ignore[arg-type]')
    lines.append('                SettingsGroup(ntp, ("NTP_Host", "NTP_Offset_S", "NTP_Interv_H"), post_asy_fct=ntp.ntp_force_sync),  # type: ignore[arg-type]')
    lines.append("            ],")
    lines.append('            "system": [')
    lines.append('                SettingsGroup(sysfunct, ("DebugLevel",)),  # type: ignore[arg-type]')
    lines.append('                SettingsGroup(ntp, ("GMTOffset", "DSTOffset")),  # type: ignore[arg-type]')
    lines.append("            ],")
    if "notification" in have:
        lines.append('            "notification": [SettingsGroup(notification, cm.schema_names(notification.get_cfg_schema()))],  # type: ignore[arg-type]')
    lines.append("        },")
    lines.append("        system_cmd=_system_cmd_callback,")
    if "neopixel" in have:
        lines.append("        notification_led=_notification_led_callback,")
    if "notification" in have:
        lines.append("        notification_pause=_notification_pause_callback,")
    status_sources = ['"networking": _networking_status', '"system": _system_status']
    if "notification" in have:
        status_sources.append('"notification": _notification_status')
    lines.append("        status_sources={" + ", ".join(status_sources) + "},")
    if "sgp40" in have:
        lines.append('        maintenance_sensors=(("SGP40", _sgp_maintenance_status),),')
    lines.append("        error_sources=_collect_error_sources(),")
    lines.append("        debug=debug,")
    lines.append('        static_mount="/html",')
    lines.append("        is_hotspot_active=conn.is_hotspot_active,")
    lines.append("        host=web_host,")
    lines.append("        port=web_port,")
    lines.append("    )")


def _emit_collectors(lines: "list[str]", construction_order: "list", ctx: _Ctx) -> None:
    modules = ["conn", "ntp"] + [ctx.instance_var(n) if isinstance(n, tuple) else n for n in construction_order if n not in ("conn", "ntp")]
    lines.append('def _collect_error_sources() -> "list[Any]":')
    for name in modules:
        lines.append(f"    assert {name} is not None")
    lines.append("    sources: list[Any] = []")
    lines.append(f"    for module in ({', '.join(modules)},):")
    lines.append("        sources.extend(module.get_error_sources())")
    lines.append("    return sources")
    lines.append("")
    lines.append('def _collect_level_setters() -> "list[Callable[[int], None]]":')
    lines.append("    assert webserver is not None")
    lines.append('    setters: list[Callable[[int], None]] = []')
    lines.append(f"    for module in ({', '.join(modules)}, webserver):")
    lines.append("        setters.extend(logger.set_level for logger in module.get_loggers())")
    lines.append("    return setters")
    lines.append("")
    lines.append('def _collect_task_starters() -> "list[Callable[[], asyncio.Task[Any]]]":')
    lines.append("    assert webserver is not None")
    lines.append("    starters: list[Callable[[], asyncio.Task[Any]]] = []")
    lines.append(f"    for module in ({', '.join(modules)}, webserver):")
    lines.append("        starters.extend(module.get_task_starters())")
    lines.append("    return starters")
    lines.append("")
    lines.append('def _collect_timer_starters() -> "list[Callable[[], None]]":')
    lines.append("    assert webserver is not None")
    lines.append("    starters: list[Callable[[], None]] = []")
    lines.append(f"    for module in ({', '.join(modules)}, webserver):")
    lines.append("        starters.extend(module.get_timer_starters())")
    lines.append("    return starters")
    lines.append("")


def generate_boot_entry_source(device: str) -> str:
    module = f"sensortask_{device}"
    return (
        f'"""Generated by buildgen: real firmware entry point for the {device} device - blocks forever,\n'
        f'matching every hand-written boot_entry/*_boot.py sibling (see modules/_boot.py)."""\n\n'
        "import asyncio\n"
        "import gc\n\n"
        f"from {module} import main\n\n"
        "gc.threshold(32768)\n\n"
        "try:\n"
        "    asyncio.run(main())\n"
        "finally:\n"
        "    asyncio.new_event_loop()\n"
    )
