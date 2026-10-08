"""Emits a device's `sensortask_<device>.py` (SPECIFICATION.md Part A.7's construction-order shape)
and its two boot entries, from a validated `DeviceModel` and its construction order
(`buildgen.graph.build_construction_order()`)."""

import keyword
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, cast

from buildgen.buildspec import UART_CRC_MODES
from buildgen.defaults import default_class_name
from buildgen.driver_registry import DriverInfo, class_has_read_triggers
from buildgen.errors import BuildError, BuildInternalError
from buildgen.model import MAINTENANCE_NAMES, DeviceModel, InstanceSpec, TomlDoc, TomlValue, instance_label, resolve_instance_key
from buildgen.signals import WARN_SIGNALS
from buildgen.validate import _WDT_TIMEOUT_MS, SETTINGS_GROUPS, module_float_const, module_int_const, module_str_const, ntp_backoff
from buildgen.version import FIRMWARE_VERSION, WEBSITE_VERSION
from buildgen.wiring import WiringField

if TYPE_CHECKING:
    from collections.abc import Callable

# @tunable module.max_error = 5
_MAX_MODULE_ERROR = 5
# @tunable dns.timeout_ms = 500
_DNS_TIMEOUT_MS = 500
# @tunable dns.tries = 1
_DNS_TRIES = 1
# @tunable ntp.fetch_timeout_ms = 5000
_NTP_FETCH_TIMEOUT_MS = 5000

# The keywords main() and build_system() take after the required watchdog, each with its annotation and default.
_BOOT_KEYWORDS = (("cfg_path", 'str = ""'), ("debug", "int | None = None"), ("web_host", 'str = "0.0.0.0"'), ("web_port", "int = 80"))
_BOOT_SIGNATURE = '*, watchdog: "WDT", ' + ", ".join(f"{name}: {rest}" for name, rest in _BOOT_KEYWORDS)
_UART_COMM = "asy_uart_comm.py"  # the link protocol module whose defaults a TransferLimits carries


def _text(value: TomlValue) -> str:
    # build_model() refused anything but a string here (Part L.5); the cast only narrows the TOML value's type.
    return cast("str", value)


def _table(value: TomlValue) -> TomlDoc:
    # build_model() refused anything but a table here (Part L.5); the cast only narrows the TOML value's type.
    return cast("TomlDoc", value)


def _bus_tables(model: DeviceModel) -> "dict[str, TomlDoc]":
    # Every [bus.*] table in TOML order; validate.py allows a device without one.
    return cast("dict[str, TomlDoc]", model.doc.get("bus", {}))


def _device_wiring(model: DeviceModel) -> TomlDoc:
    # [device.wiring], empty when the TOML has none.
    return _table(_table(model.doc["device"]).get("wiring", {}))


def _identifier(name: str, device: str, instance: "str | None"=None, field: "str | None"=None) -> str:
    # instance=/field= carried through so this matches every other BuildError call site's
    # "name exactly what and where" contract (SPECIFICATION.md Part L.5).
    if not name.isidentifier() or keyword.iskeyword(name):
        raise BuildError(
            device,
            f"{name!r} is not usable as a generated Python identifier",
            rule="names.not-an-identifier",
            fix="use letters, digits and underscores only, not starting with a digit and not a Python keyword",
            instance=instance,
            field=field,
        )
    return name


@dataclass
class _Ctx:
    model: DeviceModel
    # FRAM instance var -> its LogConfig var (log_<fram var>); a module with no FRAM store gets log_ram.
    log_vars: "dict[str, str]" = field(default_factory=dict)
    src: "Path | None" = None  # src/, for the shipped defaults codegen reads by AST

    @property
    def src_dir(self) -> Path:
        if self.src is None:
            raise BuildInternalError(f"[{self.model.device}] codegen reached a src/ default with no src_dir")
        return self.src

    def log_var(self, fram_var: "str | None") -> str:
        return "log_ram" if fram_var is None else self.log_vars[fram_var]

    def bus_var(self, bus_id: str) -> str:
        return _identifier(bus_id, self.model.device, instance=f"bus.{bus_id}", field=bus_id)

    def instance_var(self, key: "tuple[str, str]") -> str:
        label = instance_label(key)
        return _identifier(label, self.model.device, instance=label, field="driver" if not key[1] else "name_ext")

    def default_provider_expr(self, toml_field: str, value: TomlDoc) -> str:
        # SPECIFICATION.md Part L.6.2's generated-code shape: construct the provider inline, at the exact
        # call-site the real wiring expression would occupy - never a separate named global.
        class_name = default_class_name(toml_field)
        kwargs = ", ".join(f"{k}={v!r}" for k, v in value.items() if k != "default")
        return f"{class_name}({kwargs})"

    def wiring_expr(self, spec: InstanceSpec, wf: WiringField) -> str:
        value = spec.wiring[wf.toml_field]
        if isinstance(value, dict) and value.get("default") is True:
            provider_expr = self.default_provider_expr(wf.toml_field, value)
            return provider_expr if wf.mode == "kwarg" else f"{provider_expr}.{wf.target}"
        target_key = resolve_instance_key(self.model, _text(value))
        var = self.instance_var(target_key)
        return var if wf.mode == "kwarg" else f"{var}.{wf.target}"

    def value_ref(self, value: TomlValue, toml_field: str) -> str:
        # Per-value measurement wiring: either a real {source, field} reference matched by
        # attribute name, or an explicit default provider, whose one field is "value".
        reference = _table(value)
        if reference.get("default") is True:
            return f"ValueRef({self.default_provider_expr(toml_field, reference)}, {'value'!r})"
        source_var = self.instance_var(resolve_instance_key(self.model, _text(reference["source"])))
        return f"ValueRef({source_var}, {reference['field']!r})"

    def value_wiring_kwargs(self, spec: InstanceSpec) -> "list[tuple[str, str]]":
        # Every @value-wiring field the TOML wires, in the driver's tag order; an optional one left out
        # passes no keyword, so the constructor default applies (validate.py refused a required one).
        return [(vwf.kwarg, self.value_ref(spec.wiring[vwf.toml_field], vwf.toml_field)) for vwf in spec.value_wiring_schema if vwf.toml_field in spec.wiring]


def _wf(spec: InstanceSpec, toml_field: str) -> "WiringField | None":
    for wf in spec.wiring_schema:
        if wf.toml_field == toml_field:
            return wf
    return None


def _kw(pairs: "list[tuple[str, str]]") -> str:
    return ", ".join(f"{k}={v}" for k, v in pairs)


def _defaulted_wiring_fields(spec: InstanceSpec) -> "list[str]":
    # Every field on this instance that opted into the wiring-defaults mechanism, covering both
    # _WIRING- and _VALUE_WIRING-based fields uniformly since both live in spec.wiring. Decides
    # which _Default<Field> classes the instance's import line needs.
    return [f for f, v in spec.wiring.items() if isinstance(v, dict) and v.get("default") is True]


def _fram_var(spec: InstanceSpec, ctx: _Ctx) -> "str | None":
    # The instance's wired FRAM store, or None (no fram_target tag, or not wired).
    fram_wf = _wf(spec, "fram_target")
    return ctx.wiring_expr(spec, fram_wf) if fram_wf is not None and "fram_target" in spec.wiring else None


def _fram_kw(spec: InstanceSpec, ctx: _Ctx) -> "tuple[str, str]":
    # Every module's log config: its FRAM target's LogConfig, else the FRAM-less one, passed under
    # its fram_target tag's own target name ("log").
    fram_wf = _wf(spec, "fram_target")
    return ("log" if fram_wf is None else fram_wf.target), ctx.log_var(_fram_var(spec, ctx))


def _device_fram_var(model: DeviceModel, ctx: _Ctx) -> "str | None":
    # The device-level counterpart to _fram_var(): [device.wiring].fram_target is always a plain
    # instance name, never a default-provider dict (_check_device_wiring() enforces that), and is
    # wired into every mandatory-infra consumer declaring a fram_target tag.
    fram_target = _device_wiring(model).get("fram_target")
    return ctx.instance_var(resolve_instance_key(model, _text(fram_target))) if fram_target else None


def _device_target(model: DeviceModel, consumer: str, toml_field: str, unwired: str) -> str:
    # The keyword a [device.wiring] field reaches its consumer under: that consumer's own @wiring tag
    # target, as validate.py recorded it; `unwired` names the constructor parameter when the TOML leaves it out.
    wf = model.device_wiring.get(consumer, {}).get(toml_field)
    return unwired if wf is None else wf.target


def _device_log_arg(model: DeviceModel, ctx: _Ctx, consumer: str) -> str:
    return f"{_device_target(model, consumer, 'fram_target', 'log')}={ctx.log_var(_device_fram_var(model, ctx))}"


def _build_args_scd30(spec: InstanceSpec, ctx: _Ctx) -> "tuple[list[str], list[tuple[str, str]]]":
    f = spec.fields
    pos = [ctx.bus_var(_text(f["bus"])), str(f["irq_pin"])]
    kw: list[tuple[str, str]] = []
    if "trigger_s" in f:
        kw.append(("trigger_s", str(f["trigger_s"])))
    kw.append(("max_module_error", "_MAX_MODULE_ERROR"))
    if spec.name_ext:
        kw.append(("name_ext", repr(spec.name_ext)))
    kw.append(("cfg_path", "cfg_path"))
    kw.append(_fram_kw(spec, ctx))
    return pos, kw


def _build_args_sgp40(spec: InstanceSpec, ctx: _Ctx) -> "tuple[list[str], list[tuple[str, str]]]":
    f = spec.fields
    pos = [ctx.bus_var(_text(f["bus"]))]
    kw = ctx.value_wiring_kwargs(spec)
    fram_var = _fram_var(spec, ctx)
    if fram_var is not None:  # the VOC backup lives in the same FRAM store its logger does
        kw.append(("backup", f"SgpBackup({fram_var}, ntp.ntp_issynced)"))
    kw.append(("max_module_error", "_MAX_MODULE_ERROR"))
    if spec.name_ext:
        kw.append(("name_ext", repr(spec.name_ext)))
    kw.append(("cfg_path", "cfg_path"))
    kw.append(_fram_kw(spec, ctx))
    return pos, kw


def _build_args_bmp3xx(spec: InstanceSpec, ctx: _Ctx) -> "tuple[list[str], list[tuple[str, str]]]":
    f = spec.fields
    pos = [ctx.bus_var(_text(f["bus"]))]
    kw: list[tuple[str, str]] = []
    if "address" in f:
        kw.append(("address", f"{f['address']:#x}"))
    if "trigger_s" in f:
        kw.append(("trigger_s", str(f["trigger_s"])))
    kw.append(("max_module_error", "_MAX_MODULE_ERROR"))
    if spec.name_ext:
        kw.append(("name_ext", repr(spec.name_ext)))
    kw.append(("cfg_path", "cfg_path"))
    kw.append(_fram_kw(spec, ctx))
    return pos, kw


def _build_args_isl29125(spec: InstanceSpec, ctx: _Ctx) -> "tuple[list[str], list[tuple[str, str]]]":
    # irq_pin positional, like _build_args_scd30's own shape; cfg_path/optional trigger_s kwargs,
    # like _build_args_bmp3xx's own shape - ISL29125_Reader is a SensorReaderConfig (needs cfg_path)
    # wired to a real interrupt pin (needs irq_pin), the one driver combining both facts.
    f = spec.fields
    pos = [ctx.bus_var(_text(f["bus"])), str(f["irq_pin"])]
    kw: list[tuple[str, str]] = []
    if "trigger_s" in f:
        kw.append(("trigger_s", str(f["trigger_s"])))
    kw.append(("max_module_error", "_MAX_MODULE_ERROR"))
    if spec.name_ext:
        kw.append(("name_ext", repr(spec.name_ext)))
    kw.append(("cfg_path", "cfg_path"))
    # Omitted -> the driver's own irq_pull_up=True default (the internal pull-up, for a board with
    # no external resistor of its own); a device whose board already has one sets this false.
    if "irq_pull_up" in f:
        kw.append(("irq_pull_up", str(f["irq_pull_up"])))
    kw.append(_fram_kw(spec, ctx))
    return pos, kw


def _build_args_fram(spec: InstanceSpec, ctx: _Ctx) -> "tuple[list[str], list[tuple[str, str]]]":
    f = spec.fields
    pos = [ctx.bus_var(_text(f["bus"])), str(f["cs_pin"])]
    # The FRAM manager's own log never lives on the chip it manages (Part C.7.1).
    kw: list[tuple[str, str]] = [("max_size", f"{f['max_size']:#x}"), ("log", "log_ram")]
    return pos, kw


def _build_args_neopixel(spec: InstanceSpec, ctx: _Ctx) -> "tuple[list[str], list[tuple[str, str]]]":
    pos = [str(spec.fields["pin"])]
    kw: list[tuple[str, str]] = [_fram_kw(spec, ctx)]
    return pos, kw


def _build_args_notification(spec: InstanceSpec, ctx: _Ctx) -> "tuple[list[str], list[tuple[str, str]]]":
    signal_wf = _wf(spec, "signal_sink")
    if signal_wf is None:
        raise BuildInternalError(f"[{ctx.model.device}/{spec.label}] notification has no signal_sink wiring field by codegen time")
    pos = [ctx.wiring_expr(spec, signal_wf), "ntp.cettime"]
    kw: list[tuple[str, str]] = [("signals", _notification_signals(spec, ctx)), ("cfg_path", "cfg_path"), _fram_kw(spec, ctx)]
    return pos, kw


def _build_args_uart_link(spec: InstanceSpec, ctx: _Ctx) -> "tuple[list[str], list[tuple[str, str]]]":
    # Forwards bus, role, name_ext and the log config; the CRC is the bus's (A.7). One TransferLimits: the
    # protocol's defaults read from its source (no TOML key) and the TOML's receive cap, else the default one.
    f = spec.fields
    defaults = [module_int_const(ctx.src_dir, _UART_COMM, name) for name in ("_DEFAULT_PAYLOAD_SIZE", "_DEFAULT_TIMEOUT_MS", "_DEFAULT_CHUNK_BYTES")]
    cap = f["max_transfer_bytes"] if "max_transfer_bytes" in f else module_int_const(ctx.src_dir, _UART_COMM, "_DEFAULT_MAX_TRANSFER_BYTES")
    pos = [ctx.bus_var(_text(f["bus"])), repr(f["role"])]
    kw: list[tuple[str, str]] = [("limits", f"TransferLimits({', '.join(map(str, defaults))}, {cap})")]
    if spec.name_ext:
        kw.append(("name_ext", repr(spec.name_ext)))
    kw.append(_fram_kw(spec, ctx))
    return pos, kw


# One handler per driver, the same "add a driver, add a row" shape buildspec.py's tables use. A
# dispatch table rather than the if/elif chain this used to be, purely to stay under ruff's
# complexity ceiling - the per-driver logic itself is unchanged.
_BUILD_ARGS_HANDLERS: "dict[str, Callable[[InstanceSpec, _Ctx], tuple[list[str], list[tuple[str, str]]]]]" = {
    "scd30": _build_args_scd30,
    "sgp40": _build_args_sgp40,
    "bmp3xx": _build_args_bmp3xx,
    "isl29125": _build_args_isl29125,
    "fram": _build_args_fram,
    "neopixel": _build_args_neopixel,
    "notification": _build_args_notification,
    "uart_link": _build_args_uart_link,
}


def _build_call(spec: InstanceSpec, info: DriverInfo, ctx: _Ctx) -> str:
    handler = _BUILD_ARGS_HANDLERS.get(spec.driver)
    if handler is None:
        raise BuildError(
            ctx.model.device,
            f"codegen has no build recipe for driver {spec.driver!r}",
            rule="driver.no-build-recipe",
            fix="add one to buildgen.codegen._BUILD_ARGS_HANDLERS",
            instance=spec.label,
        )
    pos, kw = handler(spec, ctx)
    args = ", ".join(pos + ([_kw(kw)] if kw else []))
    return f"{info.class_name}({args})"


def _notification_signals(spec: InstanceSpec, ctx: _Ctx) -> str:
    # The notification's signals, passed at construction as one tuple, in TOML order.
    signals = []
    for toml_field, source in spec.wiring.items():
        if not toml_field.startswith("warn_"):
            continue
        sig = WARN_SIGNALS.get(toml_field)
        if sig is None:
            # validate.py refuses a warn_* key outside the catalog before generation starts.
            raise BuildInternalError(f"[{ctx.model.device}/{spec.label}.{toml_field}] a warn signal outside buildgen.signals.WARN_SIGNALS reached codegen")
        signals.append(f"NotificationSignal({sig.name!r}, {ctx.value_ref(source, toml_field)}, {sig.const_name}, {sig.color!r})")
    return "(" + ", ".join(signals) + ("," if len(signals) == 1 else "") + ")"


def _schema_literal(toml_field: str) -> str:
    # A warn signal's one-field schema, rendered from the catalog in the form the device modules have always carried.
    sig = WARN_SIGNALS[toml_field]
    return f'(("{sig.name}", "{sig.field_type}", {sig.default!r}, {sig.min!r}, {sig.max!r}, None),)'


def _bus_crc_class(model: DeviceModel, bus_id: str) -> "str | None":
    # The CRC the bus's one uart_link instance names, as its asy_crc_checks class; None for no CRC.
    links = [s for s in model.instances.values() if s.driver == "uart_link" and s.fields.get("bus") == bus_id]
    if not links:
        return None
    mode = _text(links[0].fields.get("crc", "none"))
    if mode not in UART_CRC_MODES:
        raise BuildInternalError(f"[{model.device}/{links[0].label}.crc] crc mode {mode!r} reached codegen unchecked")
    return None if mode == "none" else UART_CRC_MODES[mode][0]


def _emit_header_and_imports(lines: "list[str]", model: DeviceModel, ctx: _Ctx, instances: "dict[tuple[str, str], InstanceSpec]", have: "set[str]", build_date: str) -> None:
    lines.append(f'"""Generated by buildgen from devices/{model.device}.toml - do not edit.')
    lines.append('Construction order: SPECIFICATION.md Part A.7."""')
    lines.append("")
    lines.append("import gc")
    lines.append("import time")
    lines.append("")
    lines.append("# mounts the frozen website at /html on import")
    lines.append("import frozen_html")
    lines.append("from microdot import Microdot")
    lines.append("from micropython import const")
    lines.append("")
    lines.append("import asy_i2c_driver")
    lines.append("import asy_spi_driver")
    lines.append("import asy_uart_driver")
    lines.append("import asy_config_manager as cm")
    # One import line per module, not per instance - two instances of the same driver (e.g. a
    # multi-scd30 device) share one module and must share one import line, merging whichever
    # _Default* extras either instance's own wiring needs rather than importing the class twice.
    module_imports: dict[str, tuple[str, list[str]]] = {}
    for spec in sorted(instances.values(), key=lambda s: s.order_index):
        if spec.driver_info is None:
            raise BuildInternalError(f"[{ctx.model.device}/{spec.label}] driver_info unresolved by codegen time")
        if spec.driver == "notification":
            continue  # imported below, together with NotificationSignal
        _class_name, extras = module_imports.setdefault(spec.driver_info.module, (spec.driver_info.class_name, []))
        names = [default_class_name(f) for f in _defaulted_wiring_fields(spec)]
        if spec.driver == "sgp40" and _fram_var(spec, ctx) is not None:
            names.append("SgpBackup")
        for name in names:
            if name not in extras:
                extras.append(name)
    for module, (class_name, extras) in module_imports.items():
        extra = "".join(f", {name}" for name in extras)
        lines.append(f"from {module} import {class_name}{extra}")
    if "notification" in have:
        notif_extra_spec = next(s for s in instances.values() if s.driver == "notification")
        notif_extra = "".join(f", {default_class_name(f)}" for f in _defaulted_wiring_fields(notif_extra_spec))
        lines.append(f"from asy_notification_service import NotificationService, NotificationSignal{notif_extra}")
    lines.append("from asy_ntp_client import NTPClient, NtpTiming")
    lines.append("from asy_webserver_service import RouteSources, ServingLimits, SettingsGroup, StaticSite, WebserverService")
    lines.append("from asy_wifi_service import WifiService, WifiConfig")
    if have & {"sgp40", "notification"}:
        lines.append("from asy_base_classes import ValueRef")
    crc_classes = sorted({c for c in (_bus_crc_class(model, b) for b in _bus_tables(model)) if c is not None})
    if crc_classes:
        lines.append(f"from asy_crc_checks import {', '.join(crc_classes)}")
    if "uart_link" in have:
        lines.append("from asy_uart_comm import TransferLimits")
    lines.append("from asy_print_log import DEFAULT_LOG, LogConfig")
    lines.append("from asy_system_service import SystemService, begin_boot, BOOT_SETUP, BOOT_TASKS, BOOT_TIMERS, BOOT_NTP, BOOT_DONE")
    lines.append("")
    lines.append("try:")
    lines.append("    from typing import TYPE_CHECKING")
    lines.append("except ImportError:")
    lines.append("    TYPE_CHECKING = False")
    lines.append("")
    lines.append("if TYPE_CHECKING:")
    lines.append("    from collections.abc import Callable")
    lines.append("")
    lines.append("    from machine import WDT")
    lines.append("")
    lines.append("    from asy_base_classes import ErrorSource, JsonDict, SetupFct, TaskStarter, TimerStarter")
    lines.append("")
    lines.append(f"_MAX_MODULE_ERROR = const({_MAX_MODULE_ERROR})")
    lines.append(f"_DNS_TIMEOUT_MS = const({_DNS_TIMEOUT_MS})")
    lines.append(f"_DNS_TRIES = const({_DNS_TRIES})")
    lines.append(f"_NTP_FETCH_TIMEOUT_MS = const({_NTP_FETCH_TIMEOUT_MS})")
    lines.append(f"_FIRMWARE_VERSION = const({FIRMWARE_VERSION!r})")
    lines.append(f"_WEBSITE_VERSION = const({WEBSITE_VERSION!r})")
    lines.append(f"_BUILD_DATE = const({build_date!r})")
    lines.append("")


def _emit_globals(lines: "list[str]", instances: "dict[tuple[str, str], InstanceSpec]", have: "set[str]", global_types: "dict[str, str]") -> None:
    if "notification" in have:
        notif_spec = next(s for s in instances.values() if s.driver == "notification")
        for toml_field in notif_spec.wiring:
            if toml_field.startswith("warn_") and toml_field in WARN_SIGNALS:
                lines.append(f"{WARN_SIGNALS[toml_field].const_name}: cm.ConfigSchema = {_schema_literal(toml_field)}")
        lines.append("")

    # Declared, never None-initialised: each name stays unbound until build_system() assigns it, and every
    # class named here is a runtime import, so no annotation needs quotes.
    lines.extend(f"{name}: {class_expr}" for name, class_expr in global_types.items())
    lines.append("webserver: WebserverService")
    lines.append("")


def _emit_build_system(lines: "list[str]", model: DeviceModel, ctx: _Ctx, instances: "dict[tuple[str, str], InstanceSpec]", have: "set[str]", construction_order: "list[str | tuple[str, str]]", all_vars: "list[str]", sensor_vars: "list[str]") -> None:
    device_table = _table(model.doc["device"])
    lines.append("async def build_system(")
    lines.append(f"    {_BOOT_SIGNATURE}")
    lines.append(") -> None:")
    lines.append('    """Construct every module in the generated order (SPECIFICATION.md Part A.7)."""')
    lines.append("    global " + ", ".join([*all_vars, "webserver"]))
    lines.append("")
    # Read and cleared before any construction, so a crash in a constructor already reads as a boot failure.
    lines.append("    reset_reason = begin_boot()")
    buses = _bus_tables(model)
    if any(bus_id.startswith("i2c") for bus_id in buses):
        lines.append("    # each I2C bus clears a held SDA before its controller starts (owner, 2026-09-30)")
    for bus_id, bus_table in buses.items():
        var = ctx.bus_var(bus_id)
        if bus_id.startswith("i2c"):
            port = bus_id[len("i2c") :]  # "i2c0" -> "0" - strip the prefix, don't scan for digits (the "2" in "i2c" is itself a digit)
            timeout_kw = f", timeout={bus_table['timeout']}" if "timeout" in bus_table else ""
            lines.append(f"    {var} = asy_i2c_driver.I2C({port}, {bus_table['scl_pin']}, {bus_table['sda_pin']}, frequency={bus_table['frequency']}{timeout_kw})")
        elif bus_id.startswith("spi"):
            port = bus_id[len("spi") :]  # "spi0" -> "0"
            lines.append(f"    {var} = asy_spi_driver.SPI({port}, {bus_table['sck_pin']}, {bus_table['mosi_pin']}, {bus_table['miso_pin']})")
        else:
            port = bus_id[len("uart") :]  # "uart0" -> "0"
            # Each optional UART kwarg is emitted only when the bus table states it (the constructor default
            # applies otherwise); crc comes from the bus's one uart_link instance, absent for no CRC.
            extra_kw = "".join(f", {f}={bus_table[f]}" for f in ("rxbuf", "txbuf", "rx_ring", "poll_wait_ms", "poll_idle_ms") if f in bus_table)
            crc_class = _bus_crc_class(model, bus_id)
            crc_kw = f", crc={crc_class}()" if crc_class is not None else ""
            lines.append(f"    {var} = asy_uart_driver.UART({port}, {bus_table['tx_pin']}, {bus_table['rx_pin']}, baudrate={bus_table['baudrate']}{extra_kw}{crc_kw})")

    # One LogConfig per FRAM store a module logs into (log_<fram var>, right after that FRAM), and
    # log_ram for every module without one, the FRAM manager itself included.
    lines.append("    log_ram = LogConfig(None, DEFAULT_LOG.history_length, debug)")
    device_wiring = _device_wiring(model)
    led_var = ctx.instance_var(resolve_instance_key(model, _text(device_wiring["led_target"]))) if "led_target" in device_wiring else None
    led_kw = f"{_device_target(model, 'conn', 'led_target', 'ext_led')}={led_var}"
    for node in construction_order:
        if node == "conn":
            # Here rather than hardcoded ahead of the bus loop, so it can follow fram's own
            # construction whenever a device-level fram_target wires it in. A device without one
            # still builds conn first.

            # hostname/hotspot_password are [device]'s values, passed as the DEFAULTS of the two
            # ConfigManager-persisted fields (_with_default). The status LED is built first (graph.py).
            wifi = f"WifiConfig({device_table['hostname']!r}, {device_table['hotspot_password']!r}, {device_table['conn_fail_to_hotspot']}, {device_table['hotspot_time_min']})"
            lines.append(f"    conn = WifiService({wifi}, {led_kw}, max_module_error=_MAX_MODULE_ERROR, cfg_path=cfg_path, {_device_log_arg(model, ctx, 'conn')})")
            continue
        if node == "ntp":
            # The backoff pair is always the effective one: [device]'s stated keys, else the src/ defaults.
            retry_s, retry_max_s = ntp_backoff(device_table, ctx.src_dir)
            timing = f"NtpTiming(_DNS_TIMEOUT_MS, _DNS_TRIES, _NTP_FETCH_TIMEOUT_MS, {retry_s}, {retry_max_s})"
            lines.append(f"    ntp = NTPClient(conn.get_wifi_mode_lock(), conn.network_available_locked, conn.get_dns_server_ip, {timing}, cfg_path=cfg_path, {_device_log_arg(model, ctx, 'ntp')})")
            continue
        if node == "sysfunct":
            storage = _device_fram_var(model, ctx)
            providers = "level_setters=_collect_level_setters, config_stores=_collect_config_stores, reset_reason=reset_reason"
            lines.append(f"    sysfunct = SystemService(ntp.ntp_issynced, watchdog=watchdog, storage={storage}, cfg_path=cfg_path, {_device_log_arg(model, ctx, 'sysfunct')}, {providers})")
            continue
        if not isinstance(node, tuple):
            raise BuildInternalError(f"[{model.device}] construction_order entry {node!r} is not a known bare node or an instance key")
        spec = instances[node]
        var = ctx.instance_var(node)
        # _emit_header_and_imports() already refused an unresolved driver_info; the cast only narrows its type.
        lines.append(f"    {var} = {_build_call(spec, cast('DriverInfo', spec.driver_info), ctx)}")
        if spec.driver == "fram" and var in ctx.log_vars:
            lines.append(f"    {ctx.log_vars[var]} = LogConfig({var}, DEFAULT_LOG.history_length, debug)")

    lines.append("")
    uart_initiator_var = next(
        (ctx.instance_var(n) for n in construction_order if isinstance(n, tuple) and instances[n].driver == "uart_link" and instances[n].fields.get("role") == "initiator"),
        None,
    )
    maintenance_entries = [f'("{name}", _sgp_maintenance_status_{var})' for name, var in _sgp40_status_vars(construction_order, ctx)]
    if uart_initiator_var is not None:
        # Only the initiator side owns real transfer/failure counts (it's the only one that ever
        # initiates a transfer - SPECIFICATION.md Part J.1's "the protocol carries no application
        # semantics" means the responder side has nothing of its own to report here).
        maintenance_entries.append(f'("{MAINTENANCE_NAMES["uart_link"]}", {uart_initiator_var}.get_link_status)')
    _emit_webserver(lines, ctx, have, sensor_vars, maintenance_entries, _device_log_arg(model, ctx, "webserver"), device_table)
    lines.append("")


def _emit_main(lines: "list[str]") -> None:
    # The boot sequence (Part A.7): each phase complete before the next, its mark set before it starts.
    lines.append(f"async def main({_BOOT_SIGNATURE}) -> None:")
    lines.append(f"    await build_system(watchdog=watchdog, {', '.join(f'{name}={name}' for name, _ in _BOOT_KEYWORDS)})")
    lines.append("    sysfunct.boot_phase(BOOT_SETUP)")
    lines.append("    await sysfunct.run_setups(_collect_setups())")
    lines.append("    sysfunct.boot_phase(BOOT_TASKS)")
    lines.append("    await sysfunct.start_tasks(_collect_task_starters())")
    lines.append("    sysfunct.boot_phase(BOOT_TIMERS)")
    lines.append("    await sysfunct.start_timers(_collect_trigger_starters(), _collect_timer_starters())")
    lines.append("    sysfunct.boot_phase(BOOT_NTP)")
    lines.append("    # first NTP sync last: tasks already serve while it runs (agent, 2026-09-28; owner-reviewed, 2026-10-02)")
    lines.append("    await ntp.ntp_force_sync()")
    lines.append("    sysfunct.boot_phase(BOOT_DONE)")
    lines.append("    await sysfunct.supervise_tasks()")
    lines.append("")


_BUS_CLASSES = {"i2c": "asy_i2c_driver.I2C", "spi": "asy_spi_driver.SPI", "uart": "asy_uart_driver.UART"}
_SERVICE_CLASSES = {"conn": "WifiService", "ntp": "NTPClient", "sysfunct": "SystemService"}


def _global_types(model: DeviceModel, construction_order: "list[str | tuple[str, str]]", ctx: _Ctx) -> "dict[str, str]":
    # Every module global typed by the class build_system() constructs into it, in declaration order.
    types = {ctx.bus_var(bus_id): _BUS_CLASSES[bus_id.rstrip("0123456789")] for bus_id in _bus_tables(model)}
    for node in construction_order:
        if isinstance(node, tuple):
            info = model.instances[node].driver_info
            if info is None:
                raise BuildInternalError(f"[{model.device}/{model.instances[node].label}] driver_info unresolved by codegen time")
            types[ctx.instance_var(node)] = info.class_name
        elif node in _SERVICE_CLASSES:
            types[node] = _SERVICE_CLASSES[node]
        else:
            raise BuildInternalError(f"[{model.device}] construction_order entry {node!r} is not a known bare node or an instance key")
    return types


def generate_module_source(model: DeviceModel, construction_order: "list[str | tuple[str, str]]", build_date: str, src_dir: Path) -> str:
    ctx = _Ctx(model, src=src_dir)
    instances = model.instances
    # Every FRAM instance some module logs into, the device's infra included, gets its LogConfig.
    targeted = [_device_fram_var(model, ctx)] + [_fram_var(spec, ctx) for spec in instances.values()]
    ctx.log_vars = {var: f"log_{var}" for var in targeted if var is not None}
    have = {spec.driver for spec in instances.values()}
    order_position = {node: i for i, node in enumerate(construction_order)}
    sensor_specs = sorted((s for s in instances.values() if s.driver_info and s.driver_info.kind == "sensor"), key=lambda s: order_position[s.key])
    sensor_vars = [ctx.instance_var(spec.key) for spec in sensor_specs]
    all_vars = [ctx.bus_var(b) for b in _bus_tables(model)] + [ctx.instance_var(k) if isinstance(k, tuple) else k for k in construction_order]

    lines: list[str] = []
    _emit_header_and_imports(lines, model, ctx, instances, have, build_date)
    _emit_globals(lines, instances, have, _global_types(model, construction_order, ctx))
    _emit_callbacks(lines, have, construction_order, ctx)
    _emit_build_system(lines, model, ctx, instances, have, construction_order, all_vars, sensor_vars)
    _emit_collectors(lines, construction_order, ctx)
    _emit_trigger_collector(lines, sensor_specs, ctx)
    _emit_main(lines)
    return "\n".join(lines) + "\n"


def _sgp40_status_vars(construction_order: "list[str | tuple[str, str]]", ctx: _Ctx) -> "list[tuple[str, str]]":
    # One maintenance status source per SGP40, in construction order, keyed by its REST identity
    # (resolved_name, SPECIFICATION.md Part C.14) - "SGP40" for the default instance.
    specs = [ctx.model.instances[n] for n in construction_order if isinstance(n, tuple) and ctx.model.instances[n].driver == "sgp40"]
    for spec in specs:
        if spec.resolved_name is None:
            raise BuildInternalError(f"[{ctx.model.device}/{spec.label}] resolved_name unresolved before code generation")
    return [(str(spec.resolved_name), ctx.instance_var(spec.key)) for spec in specs]


def _singleton_var(ctx: _Ctx, driver: str) -> str:
    # The variable of the device's one instance of a singleton driver, as the build call names it.
    return ctx.instance_var(next(key for key, spec in ctx.model.instances.items() if spec.driver == driver))


def _emit_callbacks(lines: "list[str]", have: "set[str]", construction_order: "list[str | tuple[str, str]]", ctx: _Ctx) -> None:
    lines.append('def _gmtimestruct_to_dict(t: tuple[int, ...] | None) -> "JsonDict | None":')
    lines.append("    if t is None:")
    lines.append("        return None")
    lines.append('    return {"Year": t[0], "Month": t[1], "MDay": t[2], "Hour": t[3], "Minute": t[4], "Second": t[5], "Weekday": t[6], "Yearday": t[7]}')
    lines.append("")
    # Each word answers the service's own bool; the shutdown sequence flushes every store itself.
    lines.append("async def _system_cmd_callback(cmd: str) -> bool:")
    for word, call in (
        ("reboot", "await sysfunct.reboot_system()"),
        ("bootloader", "await sysfunct.reboot_bootloader()"),
        ("mempause", "sysfunct.pause_permanent_storage(300)"),
        ("resetconfig", "await sysfunct.reset_to_defaults()"),
        ("erasefram", "await sysfunct.erase_fram()"),
    ):
        lines.append(f'    if cmd == "{word}":')
        lines.append(f"        return {call}")
    lines.append("    return False")
    lines.append("")
    if "neopixel" in have:
        # The webserver validates R/G/B/T against its _LIGHT_CMD_FIELDS before this is called.
        lines.append("async def _notification_led_callback(r: int, g: int, b: int, t: float) -> bool:")
        lines.append(f"    return {_singleton_var(ctx, 'neopixel')}.led_signal(r, g, b, t)")
        lines.append("")
    if "notification" in have:
        lines.append("async def _notification_pause_callback(payload: int) -> bool:")
        lines.append(f"    return await {_singleton_var(ctx, 'notification')}.set_override_led(payload)")
        lines.append("")
    for _name, var in _sgp40_status_vars(construction_order, ctx):
        lines.append(f'async def _sgp_maintenance_status_{var}() -> "JsonDict":')
        lines.append(f"    backup_ts, restore_ts = await {var}.get_mem_status()")
        lines.append('    return {"BackupTS": backup_ts, "RestoreTS": restore_ts}')
        lines.append("")
    lines.append('async def _networking_status() -> "JsonDict":')
    # One snapshot per response (the WiFi service refreshes it each second); no call reads the radio.
    lines.append("    wifi_data = await conn.get_data()")
    lines.append("    ntp_data = await ntp.get_data()")
    lines.append("    return {")
    lines.append('        "WifiUptime": await conn.get_wifi_uptime(), "Mode": wifi_data.Mode, "Connected": wifi_data.Connected,')
    lines.append('        "IPv4": wifi_data.IP, "Subnet": wifi_data.Subnet, "Gateway": wifi_data.Gateway, "DNS": wifi_data.DNS, "RSSI": wifi_data.RSSI,')
    lines.append('        "NTPSynced": ntp_data.Synced, "NTPLastSyncAge": ntp_data.LastSyncAge, "NTPLastSync": ntp_data.TS,')
    lines.append('        "HTTPDropped": await webserver.get_dropped_count(), "WifiTS": wifi_data.TS,')
    lines.append("    }")
    lines.append("")
    lines.append('async def _system_status() -> "JsonDict":')
    # UTCTime waits for the first NTP sync as LocalTime does: rp2's RTC starts at its reset epoch.
    lines.extend(("    local_time = await ntp.cettime()", "    utc = time.gmtime() if await ntp.ntp_issynced() else None"))
    lines.append("    return {")
    lines.append('        "SysUptime": await sysfunct.get_uptime(), "BootSignature": await sysfunct.get_boot_signature(),')
    lines.append('        "ResetReason": sysfunct.get_reset_reason(), "ResetBits": sysfunct.get_reset_bits(), "MemFree": gc.mem_free(),')
    if "fram" in have:
        lines.append(f'        "MemPaused": {_singleton_var(ctx, "fram")}.get_pause(),')
    # Copied into the JSON value type: a list[str] is not a list of JSON values (lists are invariant).
    lines.append('        "ConfigFaults": list(sysfunct.get_config_faults()), "ConfigUnpersisted": list(sysfunct.get_config_unpersisted()),')
    lines.append('        "LocalTime": _gmtimestruct_to_dict(local_time), "UTCTime": _gmtimestruct_to_dict(utc),')
    lines.append("    }")
    lines.append("")
    if "notification" in have:
        notification = _singleton_var(ctx, "notification")
        lines.append('async def _notification_status() -> "JsonDict":')
        lines.append(f"    data = await {notification}.get_data()")
        lines.append(f'    return {{"Triggered": data.Triggered, "TS": data.TS, "PauseTime": await {notification}.get_override_led()}}')
        lines.append("")


def _settings_group_lines(section: str) -> "list[str]":
    # The section's rows of validate.SETTINGS_GROUPS, the table the build's key-collision check reads too.
    # The arg-type ignore stays until the webserver's _ModuleLike accepts the modules' own return types.
    out = []
    for row_section, module_var, fields, hook in SETTINGS_GROUPS:
        if row_section == section:
            keys = "(" + ", ".join(f'"{name}"' for name in fields) + ("," if len(fields) == 1 else "") + ")"
            out.append(f"                    SettingsGroup({module_var}, {keys}{f', {hook}' if hook else ''}),")
    return out


def _emit_webserver(lines: "list[str]", ctx: _Ctx, have: "set[str]", sensor_vars: "list[str]", maintenance_entries: "list[str]", log_arg: str, device_table: TomlDoc) -> None:
    # The three config objects, every field passed: a [device] value where the TOML states one,
    # else the shipped default read out of asy_webserver_service.py's own _DEFAULT_* constants.
    ws = "asy_webserver_service.py"
    src_dir = ctx.src_dir
    max_connections = device_table["max_connections"] if "max_connections" in device_table else module_int_const(src_dir, ws, "_DEFAULT_MAX_CONNECTIONS")
    lines.append("    app = Microdot()")
    lines.append("    webserver = WebserverService(")
    lines.append("        app,")
    lines.append("        routes=RouteSources(")
    lines.append(f"            sensors=({', '.join(sensor_vars)}{',' if len(sensor_vars) == 1 else ''}),")
    lines.append("            settings={")
    for section in dict.fromkeys(row[0] for row in SETTINGS_GROUPS):
        lines.append(f'                "{section}": [')
        lines.extend(_settings_group_lines(section))
        lines.append("                ],")
    if "notification" in have:
        # Computed from the notification's own schema, so its keys follow the wired signals.
        notification = _singleton_var(ctx, "notification")
        lines.append(f'                "notification": [SettingsGroup({notification}, cm.schema_names({notification}.get_cfg_schema()))],')
    lines.append("            },")
    lines.append('            build_info={"FirmwareVersion": _FIRMWARE_VERSION, "WebsiteVersion": _WEBSITE_VERSION, "BuildDate": _BUILD_DATE},')
    lines.append("            system_cmd=_system_cmd_callback,")
    lines.append(f"            notification_led={'_notification_led_callback' if 'neopixel' in have else None},")
    lines.append(f"            notification_pause={'_notification_pause_callback' if 'notification' in have else None},")
    status_sources = ['"networking": _networking_status', '"system": _system_status']
    if "notification" in have:
        status_sources.append('"notification": _notification_status')
    lines.append("            status_sources={" + ", ".join(status_sources) + "},")
    comma = "," if len(maintenance_entries) == 1 else ""
    lines.append(f"            maintenance_sensors=({', '.join(maintenance_entries)}{comma}),")
    lines.append("            error_sources=_collect_error_sources(),")
    lines.append("        ),")
    # max_connections/backlog: [device]'s values when stated; validate.py has already checked the
    # effective pair against the firmware's own lwIP PCB count.
    lines.append("        serving=ServingLimits(")
    lines.append(f"            max_content_length={module_int_const(src_dir, ws, '_DEFAULT_MAX_CONTENT_LENGTH')},")
    lines.append(f"            chunk_bytes={module_int_const(src_dir, ws, '_DEFAULT_CHUNK_BYTES')},")
    lines.append(f"            max_connections={max_connections},")
    lines.append(f"            backlog={device_table.get('backlog')},")
    lines.append(f"            per_call_timeout_s={module_float_const(src_dir, ws, '_DEFAULT_PER_CALL_TIMEOUT_S')!r},")
    lines.append(f"            outer_cap_s={module_float_const(src_dir, ws, '_DEFAULT_OUTER_CAP_S')!r},")
    lines.append("            host=web_host,")
    lines.append("            port=web_port,")
    lines.append("        ),")
    lines.append("        uptime_s=sysfunct.get_uptime,")
    lines.append(f'        static=StaticSite(mount="/html", index_file={module_str_const(src_dir, ws, "_DEFAULT_STATIC_INDEX")!r}, is_hotspot_active=conn.is_hotspot_active),')
    lines.append(f"        {log_arg},")
    lines.append("    )")


def _module_names(construction_order: "list[str | tuple[str, str]]", ctx: _Ctx) -> "list[str]":
    return ["conn", "ntp"] + [ctx.instance_var(n) if isinstance(n, tuple) else n for n in construction_order if n not in ("conn", "ntp")]


def _setup_vars(construction_order: "list[str | tuple[str, str]]", ctx: _Ctx) -> "list[str]":
    # fram must precede sysfunct: sysfunct.setup() reaches its store's FRAM-backed logger, which needs the
    # manager initialised (the other order left CFGMGR_SYSTEM degrading every boot); the webserver, built last, goes last.
    instances = ctx.model.instances
    fram = [ctx.instance_var(n) for n in construction_order if isinstance(n, tuple) and instances[n].driver == "fram"]
    rest = []
    for node in construction_order:
        if not isinstance(node, tuple) or instances[node].driver == "fram":
            continue
        info = instances[node].driver_info
        if info is not None and info.needs_setup:
            rest.append(ctx.instance_var(node))
    return [*fram, "sysfunct", "conn", "ntp", *rest, "webserver"]


def _emit_collectors(lines: "list[str]", construction_order: "list[str | tuple[str, str]]", ctx: _Ctx) -> None:
    modules = _module_names(construction_order, ctx)
    lines.append('def _collect_setups() -> "list[SetupFct]":')
    lines.append("    # fram first: sysfunct's config store logs to it; then the mandatory services; then the rest in construction order")
    lines.append(f"    return [{', '.join(f'{name}.setup' for name in _setup_vars(construction_order, ctx))}]")
    lines.append("")
    lines.append('def _collect_error_sources() -> "list[ErrorSource]":')
    lines.append('    sources: "list[ErrorSource]" = []')
    lines.append(f"    for module in ({', '.join(modules)},):")
    lines.append("        sources.extend(module.get_error_sources())")
    lines.append("    return sources")
    lines.append("")
    lines.append('def _collect_level_setters() -> "list[Callable[[int], bool]]":')
    lines.append("    setters: list[Callable[[int], bool]] = []")
    lines.append(f"    for module in ({', '.join(modules)}, webserver):")
    lines.append("        setters.extend(logger.set_level for logger in module.get_loggers())")
    lines.append("    return setters")
    lines.append("")
    # Every module's config store, each once; reached by getattr, so no module class needs a store to be listed.
    lines.append("def _collect_config_stores() -> list[cm.ConfigManager]:")
    lines.append("    # the accepted residual risk is power loss between a PUT and its flush (owner, 2026-09-26)")
    lines.append("    stores: list[cm.ConfigManager] = []")
    lines.append(f"    for module in ({', '.join(modules)}, webserver):")
    lines.append('        store = getattr(module, "cfgmgr", None)')
    lines.append("        if store is not None:")
    lines.append("            stores.append(store)")
    lines.append("    return stores")
    lines.append("")
    lines.append('def _collect_task_starters() -> "list[TaskStarter]":')
    lines.append('    starters: "list[TaskStarter]" = []')
    lines.append(f"    for module in ({', '.join(modules)}, webserver):")
    lines.append("        starters.extend(module.get_task_starters())")
    lines.append("    return starters")
    lines.append("")
    lines.append('def _collect_timer_starters() -> "list[TimerStarter]":')
    lines.append('    starters: "list[TimerStarter]" = []')
    lines.append(f"    for module in ({', '.join(modules)}, webserver):")
    lines.append("        starters.extend(module.get_timer_starters())")
    lines.append("    return starters")
    lines.append("")


def trigger_spread(readers: "list[tuple[str, str]]") -> "list[str]":
    # (instance var, bus) pairs in construction order -> stagger-slot order: one reader from each bus
    # group in turn, the largest group first and ties by construction order, so readers sharing a bus
    # sit furthest apart in the one-second plan (SPECIFICATION.md Part C.9.1).
    groups: dict[str, list[str]] = {}
    for var, bus in readers:
        groups.setdefault(bus, []).append(var)
    ordered = sorted(groups.values(), key=len, reverse=True)
    return [group[i] for i in range(max(map(len, ordered), default=0)) for group in ordered if i < len(group)]


def _emit_trigger_collector(lines: "list[str]", sensor_specs: "list[InstanceSpec]", ctx: _Ctx) -> None:
    readers = [(ctx.instance_var(spec.key), _text(spec.fields["bus"])) for spec in sensor_specs if spec.driver_info is not None and class_has_read_triggers(spec.driver_info)]
    order = trigger_spread(readers)
    lines.append('def _collect_trigger_starters() -> "list[TimerStarter]":')
    if not order:
        lines.append("    return []")
        lines.append("")
        return
    lines.append("    # In stagger-slot order: readers sharing a bus sit furthest apart (SPECIFICATION.md Part C.9.1).")
    lines.append('    starters: "list[TimerStarter]" = []')
    lines.append(f"    for module in ({', '.join(order)},):")
    lines.append("        starters.extend(module.get_trigger_starters())")
    lines.append("    return starters")
    lines.append("")


def generate_boot_entry_source(device: str, *, autostart: bool = True) -> str:
    # Both variants share the head; only the autostart one arms the watchdog (first, before any product
    # import) and runs main(), while the manual one prints the start line that does the same at the REPL.
    head = (
        "import sys\n\n"
        "# frozen code first: a filesystem .py/.mpy may not replace a frozen module (owner, 2026-09-26)\n"
        'sys.path.insert(0, ".frozen")\n\n'
        "import gc\n"
        "import micropython\n\n"
        "# room for a MemoryError's message when the heap cannot place it (Part I.4(e))\n"
        # @tunable gc.emergency_exc_buf_bytes = 100
        "micropython.alloc_emergency_exception_buf(100)\n\n"
        "import asyncio\n\n"
        f"from sensortask_{device} import main\n"
    )
    threshold = (
        "\n"
        # @tunable gc.threshold_bytes = 32768
        "gc.threshold(32768)\n\n"
    )
    docstring = '"""Generated by buildgen: the device\'s boot entry, frozen as main.py.\n'
    if not autostart:
        return (
            docstring
            + 'No autostart: prints the manual start line and returns to the REPL; a VFS `boot.py` still runs before this entry (see the reflash runbook)."""\n\n'
            + head
            + threshold
            + f"# main() also takes {', '.join(name for name, _ in _BOOT_KEYWORDS)} (keyword-only)\n"
            + f'print("from machine import WDT; asyncio.run(main(watchdog=WDT(timeout={_WDT_TIMEOUT_MS})))")\n'
        )
    return (
        docstring
        + 'Arms the watchdog before any product import (owner, 2026-09-25)."""\n\n'
        + "from machine import WDT\n\n"
        + f"watchdog = WDT(timeout={_WDT_TIMEOUT_MS})\n\n"
        + head
        + "from asy_system_service import RR_INTERRUPTED, write_reset_record\n"
        + threshold
        + "try:\n"
        "    asyncio.run(main(watchdog=watchdog))\n"
        "except KeyboardInterrupt:\n"
        "    # Ctrl-C on the console ends the whole loop and the armed watchdog then resets the unit: record\n"
        "    # why first, or the next boot reads a plain watchdog reset.\n"
        "    write_reset_record(RR_INTERRUPTED)\n"
        "    raise\n"
        "finally:\n"
        "    asyncio.new_event_loop()\n"
    )
