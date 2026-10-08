"""Fires every validate.py rule once, from one malformed input each, and prints rule/instance/field/message."""
import copy, shutil, sys, tempfile, tomllib
from pathlib import Path
WT = Path(sys.argv[1]); OUT = Path(sys.argv[2])
sys.path[:0] = [str(WT), str(WT / "tests_scripts")]
from _toml_fixtures import base_doc, write_doc, write_text
import buildgen.validate as V
from buildgen.errors import BuildError
SRC = WT / "src"

def pair(doc):
    next(i for i in doc["instance"] if i["driver"] == "scd30")["irq_pin"] = 6
    knobs = {"baudrate": 115200, "rxbuf": 512, "txbuf": 512, "poll_wait_ms": 2, "poll_idle_ms": 50}
    doc["bus"]["uart0"] = {"tx_pin": 16, "rx_pin": 17, **knobs}
    doc["bus"]["uart1"] = {"tx_pin": 8, "rx_pin": 9, **knobs}
    doc["instance"].append({"driver": "uart_link", "name_ext": "init", "bus": "uart0", "role": "initiator"})
    doc["instance"].append({"driver": "uart_link", "name_ext": "resp", "bus": "uart1", "role": "responder"})
    return doc

def inst(doc, driver):
    return next(i for i in doc["instance"] if i["driver"] == driver)

def src_edit(tmp, filename, old, new):
    staged = tmp / "src"
    if not staged.exists():
        shutil.copytree(SRC, staged)
    p = staged / filename
    text = p.read_text()
    assert old in text, (filename, old)
    p.write_text(text.replace(old, new, 1))
    return staged

def src_drop(tmp, filename):
    staged = tmp / "src"
    shutil.copytree(SRC, staged)
    (staged / filename).unlink()
    return staged

CASES = []
def case(rule, desc):
    def deco(fn):
        CASES.append((rule, desc, fn)); return fn
    return deco

def d(fn):  # doc-only mutation helper
    def run(tmp):
        doc = base_doc(); fn(doc); return doc, SRC, None
    return run

def setk(path, value):
    def m(doc):
        t = doc
        for k in path[:-1]:
            t = t[k] if not isinstance(k, int) else t[k]
        t[path[-1]] = value
    return m

R = []
def add(rule, desc, run):
    R.append((rule, desc, run))

# [device]
add("device.table-missing", "no [device] table", d(lambda doc: doc.pop("device")))
add("device.field-missing", "[device] without hostname", d(lambda doc: doc["device"].pop("hostname")))
add("device.field-type", "[device].name = 5", d(setk(["device", "name"], 5)))
add("device.wiring-not-table", '[device] wiring = "neopixel" (a string, not a table)', d(setk(["device", "wiring"], "neopixel")))
add("device.field-unknown", "[device].colour = 1", d(setk(["device", "colour"], 1)))
add("device.hotspot-password-length", '[device].hotspot_password = "short"', d(setk(["device", "hotspot_password"], "short")))
add("device.hostname-convention", '[device].hostname = "SensorStationOther"', d(setk(["device", "hostname"], "SensorStationOther")))
def bad_label(doc):
    doc["device"]["name"] = "Te_st"; doc["device"]["hostname"] = "SensorStationTe_st"
add("device.hostname-label", '[device].name = "Te_st", hostname = "SensorStationTe_st"', d(bad_label))
def long_host(doc):
    doc["device"]["name"] = "T" * 60; doc["device"]["hostname"] = "SensorStation" + "T" * 60
add("device.hostname-length", '[device].name = 60 x "T", hostname = "SensorStation" + 60 x "T"', d(long_host))
add("device.hotspot-time-min-range", "[device].hotspot_time_min = 35792", d(setk(["device", "hotspot_time_min"], 35792)))
add("device.conn-fail-to-hotspot-range", "[device].conn_fail_to_hotspot = 0", d(setk(["device", "conn_fail_to_hotspot"], 0)))
add("device.max-connections-range", "[device].max_connections = 0", d(setk(["device", "max_connections"], 0)))
add("device.max-connections-lwip", "[device].max_connections = 64", d(setk(["device", "max_connections"], 64)))
def backlog_low(doc):
    doc["device"]["max_connections"] = 4; doc["device"]["backlog"] = 3
add("device.backlog-below-ceiling", "[device].max_connections = 4, backlog = 3", d(backlog_low))
def backlog_high(doc):
    doc["device"]["max_connections"] = 4; doc["device"]["backlog"] = 6
add("device.backlog-above-ceiling", "[device].max_connections = 4, backlog = 6", d(backlog_high))
add("device.ntp-retry-below-tick", "[device].ntp_retry_s = 1", d(setk(["device", "ntp_retry_s"], 1)))
def ntp_max_below(doc):
    doc["device"]["ntp_retry_s"] = 120; doc["device"]["ntp_retry_max_s"] = 60
add("device.ntp-retry-max-below-retry", "[device].ntp_retry_s = 120, ntp_retry_max_s = 60", d(ntp_max_below))
add("device.ntp-retry-max-range", "[device].ntp_retry_max_s = 536870912", d(setk(["device", "ntp_retry_max_s"], 536870912)))
add("device.wiring-field-unknown", '[device.wiring].bogus_target = "fram"', d(lambda doc: doc["device"]["wiring"].__setitem__("bogus_target", "fram")))
add("wiring.target-type", "[device.wiring].led_target = 5", d(lambda doc: doc["device"]["wiring"].__setitem__("led_target", 5)))

# [bus.*]
def unknown_bus(doc):
    doc["bus"]["i2c7"] = doc["bus"].pop("i2c0")
    for i in doc["instance"]:
        if i.get("bus") == "i2c0": i["bus"] = "i2c7"
add("bus.unknown-id", "[bus.i2c7] (an id the Pico W has no bus for)", d(unknown_bus))
def not_table(tmp):
    from _toml_fixtures import dump_toml
    text = dump_toml(base_doc()).replace("[bus.spi0]", "[bus]\nspi0 = 5\n[bus.spi0x]", 1)
    return text, SRC, None
add("bus.not-a-table", "[bus] spi0 = 5 (a bus that is no table)", not_table)
add("bus.field-missing", "[bus.i2c0] without scl_pin", d(lambda doc: doc["bus"]["i2c0"].pop("scl_pin")))
add("bus.field-unknown", "[bus.i2c0].speed = 1", d(setk(["bus", "i2c0", "speed"], 1)))
add("bus.i2c-frequency-range", "[bus.i2c0].frequency = 1000001", d(setk(["bus", "i2c0", "frequency"], 1000001)))
add("bus.field-type", '[bus.i2c0].timeout = "200ms"', d(setk(["bus", "i2c0", "timeout"], "200ms")))
add("bus.field-type", 'uart pair with [bus.uart0].rxbuf = "512"', (lambda tmp: (lambda doc: (doc["bus"]["uart0"].__setitem__("rxbuf", "512"), doc)[1])(pair(base_doc())) and ((lambda doc: (doc["bus"]["uart0"].__setitem__("rxbuf", "512"), doc)[1])(pair(base_doc())), SRC, None)))
add("bus.i2c-timeout-range", "[bus.i2c0].timeout = 0", d(setk(["bus", "i2c0", "timeout"], 0)))
add("bus.i2c-timeout-max", "[bus.i2c0].timeout = 10000000", d(setk(["bus", "i2c0", "timeout"], 10000000)))
def p(fn):
    def run(tmp):
        doc = pair(base_doc()); fn(doc); return doc, SRC, None
    return run
add("bus.uart-baudrate-range", "uart pair with [bus.uart0].baudrate = 7812501", p(setk(["bus", "uart0", "baudrate"], 7812501)))
add("bus.uart-rxbuf-range", "uart pair with [bus.uart0].rxbuf = 32767", p(setk(["bus", "uart0", "rxbuf"], 32767)))
add("bus.uart-txbuf-range", "uart pair with [bus.uart0].txbuf = 31", p(setk(["bus", "uart0", "txbuf"], 31)))
add("bus.uart-poll-wait-range", "uart pair with [bus.uart0].poll_wait_ms = 0", p(setk(["bus", "uart0", "poll_wait_ms"], 0)))
add("bus.uart-poll-idle-range", "uart pair with [bus.uart0].poll_idle_ms = 1 (below poll_wait_ms 2)", p(setk(["bus", "uart0", "poll_idle_ms"], 1)))
add("bus.uart-timeout-floor", "uart pair with [bus.uart1].poll_idle_ms = 976", p(setk(["bus", "uart1", "poll_idle_ms"], 976)))
add("bus.uart-rxbuf-floor", "uart pair with [bus.uart0].rxbuf = 79", p(setk(["bus", "uart0", "rxbuf"], 79)))
add("bus.uart-rx-ring", "uart pair with [bus.uart0].rx_ring = 64 (below the 128-byte floor)", p(setk(["bus", "uart0", "rx_ring"], 64)))
add("bus.uart-rx-ring", "uart pair with [bus.uart0].rx_ring = 1", p(setk(["bus", "uart0", "rx_ring"], 1)))
add("bus.uart-rx-ring", "uart pair with [bus.uart0].rx_ring = 384", p(setk(["bus", "uart0", "rx_ring"], 384)))
add("bus.unused", "an extra [bus.i2c1] no instance names", d(setk(["bus", "i2c1"], {"scl_pin": 7, "sda_pin": 6, "frequency": 50000})))
def shared(doc):
    pair(doc); doc["instance"][-1]["bus"] = "uart0"; del doc["bus"]["uart1"]
add("bus.uart-shared", "uart pair with both links on bus = \"uart0\"", d(shared))
def address(doc):
    doc["instance"].append({"driver": "scd30", "name_ext": "b", "bus": "i2c0", "irq_pin": 9, "trigger_s": 3})
add("bus.fixed-address-collision", "a second scd30 (name_ext = \"b\", irq_pin = 9) on i2c0 beside the first", d(address))

# instances
add("instance.name-ext-singleton", 'notification with name_ext = "x"', d(lambda doc: inst(doc, "notification").__setitem__("name_ext", "x")))
add("instance.name-ext-missing", "scd30 without name_ext", d(lambda doc: inst(doc, "scd30").pop("name_ext")))
add("instance.field-missing", "scd30 without irq_pin", d(lambda doc: inst(doc, "scd30").pop("irq_pin")))
add("instance.address-not-selectable", "scd30 with address = 0x61", d(lambda doc: inst(doc, "scd30").__setitem__("address", 0x61)))
add("instance.field-type", "scd30 with bus = 0", d(lambda doc: inst(doc, "scd30").__setitem__("bus", 0)))
add("instance.bus-undeclared", 'scd30 with bus = "i2c1" (no [bus.i2c1])', d(lambda doc: inst(doc, "scd30").__setitem__("bus", "i2c1")))
add("instance.bus-kind", 'scd30 with bus = "spi0"', d(lambda doc: inst(doc, "scd30").__setitem__("bus", "spi0")))
add("instance.uart-role", 'uart pair with the responder\'s role = "peer"', p(lambda doc: doc["instance"][-1].__setitem__("role", "peer")))
add("instance.uart-crc-mode", 'uart pair with the initiator\'s crc = "crc32"', p(lambda doc: doc["instance"][-2].__setitem__("crc", "crc32")))
add("instance.irq-pull-up-type", "scd30 with irq_pull_up = 1", d(lambda doc: inst(doc, "scd30").__setitem__("irq_pull_up", 1)))
add("instance.field-unknown", "scd30 with colour = 1", d(lambda doc: inst(doc, "scd30").__setitem__("colour", 1)))
add("instance.uart-transfer-cap", "uart pair with the initiator's max_transfer_bytes = 47", p(lambda doc: doc["instance"][-2].__setitem__("max_transfer_bytes", 47)))
add("instance.uart-link-pair", "uart pair with both links role = \"initiator\"", p(lambda doc: doc["instance"][-1].__setitem__("role", "initiator")))
add("instance.uart-baud-mismatch", "uart pair with [bus.uart1].baudrate = 57600", p(setk(["bus", "uart1", "baudrate"], 57600)))
add("instance.uart-crc-mismatch", 'uart pair with only the initiator\'s crc = "crc16"', p(lambda doc: doc["instance"][-2].__setitem__("crc", "crc16")))

# names
def dup_name(tmp):
    doc = base_doc(); doc["instance"].append({"driver": "bmp3xx", "name_ext": "", "bus": "i2c0"})
    return doc, src_edit(tmp, "asy_bmp3xx_driver.py", '_NAME = const("BMP3XX")', '_NAME = const("NTP")'), None
add("names.logger-collision", 'a bmp3xx instance whose asy_bmp3xx_driver.py says _NAME = const("NTP")', dup_name)
def dup_inst(doc):
    doc["instance"].append(dict(inst(doc, "neopixel"), pin=16))
add("(none: model.py)", "a second neopixel [[instance]] (same driver+name_ext)", d(dup_inst))
# gpio
add("gpio.type", 'scd30 with irq_pin = "8"', d(lambda doc: inst(doc, "scd30").__setitem__("irq_pin", "8")))
add("gpio.not-usable", "scd30 with irq_pin = 23", d(lambda doc: inst(doc, "scd30").__setitem__("irq_pin", 23)))
add("gpio.claimed-twice", "neopixel with pin = 8 (scd30's irq_pin)", d(lambda doc: inst(doc, "neopixel").__setitem__("pin", 8)))
add("gpio.no-function", "uart pair with [bus.uart0].tx_pin = 18 (UART0 CTS)", p(setk(["bus", "uart0", "tx_pin"], 18)))
add("gpio.wrong-bus", "[bus.i2c0].scl_pin = 11, sda_pin = 10 (I2C1's pins)", d(lambda doc: doc["bus"]["i2c0"].update(scl_pin=11, sda_pin=10)))
add("gpio.wrong-role", "[bus.i2c0].scl_pin = 12, sda_pin = 13 (transposed)", d(lambda doc: doc["bus"]["i2c0"].update(scl_pin=12, sda_pin=13)))
# wiring
add("wiring.target-unresolved", 'sgp40 wiring.fram_target = "nothing"', d(lambda doc: inst(doc, "sgp40")["wiring"].__setitem__("fram_target", "nothing")))
add("wiring.target-class", 'notification wiring.signal_sink = "fram"', d(lambda doc: inst(doc, "notification")["wiring"].__setitem__("signal_sink", "fram")))
add("wiring.source-shape", 'sgp40 wiring.temperature_source = { source = "scd30" } (no field)', d(lambda doc: inst(doc, "sgp40")["wiring"].__setitem__("temperature_source", {"source": "scd30"})))
add("wiring.source-shape", 'sgp40 wiring.temperature_source = { source = "scd30", field = 1 }', d(lambda doc: inst(doc, "sgp40")["wiring"].__setitem__("temperature_source", {"source": "scd30", "field": 1})))
add("wiring.source-unresolved", 'sgp40 wiring.temperature_source = { source = "bme", field = "Temp" }', d(lambda doc: inst(doc, "sgp40")["wiring"].__setitem__("temperature_source", {"source": "bme", "field": "Temp"})))
add("source.field-unknown", 'sgp40 wiring.temperature_source = { source = "scd30", field = "Tmp" }', d(lambda doc: inst(doc, "sgp40")["wiring"].__setitem__("temperature_source", {"source": "scd30", "field": "Tmp"})))
add("wiring.default-key-unknown", 'sgp40 wiring.temperature_source = { default = true, temperature = 20, bogus = 1 }', d(lambda doc: inst(doc, "sgp40")["wiring"].__setitem__("temperature_source", {"default": True, "temperature": 20, "bogus": 1})))
def key_missing(tmp):
    doc = base_doc(); inst(doc, "sgp40")["wiring"]["temperature_source"] = {"default": True}
    return doc, src_edit(tmp, "asy_sgp40_driver.py", "def __init__(self, temperature: float = 25) -> None:", "def __init__(self, *, temperature: float) -> None:"), None
add("wiring.default-key-missing", "sgp40 wiring.temperature_source = { default = true }, _DefaultTemperatureSource.__init__(self, *, temperature: float)", key_missing)
add("wiring.default-class-missing", 'sgp40 wiring.fram_target = { default = true }', d(lambda doc: inst(doc, "sgp40")["wiring"].__setitem__("fram_target", {"default": True})))
add("wiring.warn-outside-notification", 'scd30 wiring.warn_co2 = { source = "scd30", field = "CO2" }', d(lambda doc: inst(doc, "scd30")["wiring"].__setitem__("warn_co2", {"source": "scd30", "field": "CO2"})))
add("wiring.warn-unknown", 'notification wiring.warn_radon = { source = "scd30", field = "CO2" }', d(lambda doc: inst(doc, "notification")["wiring"].__setitem__("warn_radon", {"source": "scd30", "field": "CO2"})))
add("wiring.field-unknown", 'scd30 wiring.led_target = "neopixel"', d(lambda doc: inst(doc, "scd30")["wiring"].__setitem__("led_target", "neopixel")))
add("wiring.target-type", "scd30 wiring.fram_target = 5", d(lambda doc: inst(doc, "scd30")["wiring"].__setitem__("fram_target", 5)))
add("wiring.field-missing", "notification without wiring.signal_sink", d(lambda doc: inst(doc, "notification")["wiring"].pop("signal_sink")))

# src / toolchain / buildspec
def s(filename, old, new, mut=None):
    def run(tmp):
        doc = base_doc()
        if mut: mut(doc)
        return doc, src_edit(tmp, filename, old, new), None
    return run
add("src.unreadable", "src/ without asy_wifi_service.py", lambda tmp: (base_doc(), src_drop(tmp, "asy_wifi_service.py"), None))
add("src.const-missing", "asy_ntp_client.py's _NTP_CHECK_INTERV renamed, with [device].ntp_retry_s = 60",
    s("asy_ntp_client.py", "_NTP_CHECK_INTERV = const(", "_NTP_CHECK_INTERVAL_X = const(", lambda doc: doc["device"].__setitem__("ntp_retry_s", 60)))
add("src.schema-missing", 'asy_wifi_service.py\'s HotspotPW schema with max bound None', s("asy_wifi_service.py", '("HotspotPW", "str", "12345678", 8, 63, None)', '("HotspotPW", "str", "12345678", 8, None, None)'))
def ring_default(tmp):
    doc = pair(base_doc())
    return doc, src_edit(tmp, "asy_uart_driver.py", "rx_ring: int = 512,", "rx_ring: int = RING,"), None
add("src.default-missing", "uart pair stating no rx_ring, asy_uart_driver.UART.__init__'s rx_ring default a name, not a literal", ring_default)
def timeout_max(tmp):
    doc = pair(base_doc())
    return doc, src_edit(tmp, "asy_uart_comm.py", "_DEFAULT_TIMEOUT_MS = const(1000)", "_DEFAULT_TIMEOUT_MS = const(100000000)"), None
add("instance.uart-timeout-max", "uart pair, asy_uart_comm's _DEFAULT_TIMEOUT_MS = const(100000000)", timeout_max)
add("device.wiring-no-tag", "[device.wiring].led_target with asy_wifi_service.py's @wiring led_target tag removed",
    s("asy_wifi_service.py", "# @wiring led_target NeopixelDriver ext_led optional kwarg", "#"))
add("device.wiring-field-missing", "no [device.wiring].led_target, asy_wifi_service.py's led_target tag made required",
    s("asy_wifi_service.py", "# @wiring led_target NeopixelDriver ext_led optional kwarg", "# @wiring led_target NeopixelDriver ext_led required kwarg", lambda doc: doc["device"]["wiring"].pop("led_target")))
add("instance.requires-without-bus", "asy_neopixel_driver.py carrying # @requires bus.timeout>=1",
    s("asy_neopixel_driver.py", "# @wiring fram_target FRAMManager log optional kwarg", "# @requires bus.timeout>=1\n# @wiring fram_target FRAMManager log optional kwarg"))
def bogus_driver(tmp):
    staged = tmp / "src"; shutil.copytree(SRC, staged)
    (staged / "asy_bogus2_driver.py").write_text('_NAME = "BOGUS2"\n\n\nclass Bogus2_Reader(SensorReader):\n    pass\n')
    doc = base_doc(); doc["instance"].append({"driver": "bogus2", "name_ext": ""})
    return doc, staged, None
add("instance.no-buildspec-row", "an [[instance]] driver = \"bogus2\" whose asy_bogus2_driver.py resolves but has no buildspec row", bogus_driver)
add("instance.field-not-in-set", "fram with max_size = 4096", d(lambda doc: inst(doc, "fram").__setitem__("max_size", 4096)))
add("instance.field-out-of-range", "scd30 with trigger_s = 1801", d(lambda doc: inst(doc, "scd30").__setitem__("trigger_s", 1801)))
def float_lim(tmp):
    doc = base_doc(); inst(doc, "scd30")["gain"] = float("nan")
    staged = src_edit(tmp, "asy_scd30_driver.py", "# @limits trigger_s 1..1800", "# @limits trigger_s 1..1800\n# @limits gain 0.5..2.5")
    import buildgen.buildspec as B
    return doc, staged, (B.ALLOWED_INSTANCE_FIELDS, "scd30", B.ALLOWED_INSTANCE_FIELDS["scd30"] | {"gain"})
add("instance.field-not-finite", "scd30 with gain = nan, against a synthetic # @limits gain 0.5..2.5", float_lim)
def two_bmp(doc):
    doc["instance"].append({"driver": "bmp3xx", "name_ext": "a", "bus": "i2c0", "address": 0x76})
    doc["instance"].append({"driver": "bmp3xx", "name_ext": "b", "bus": "i2c0", "address": 0x76})
add("bus.address-collision", "two bmp3xx on i2c0, both address = 0x76", d(two_bmp))
def two_slow(tmp):
    doc = base_doc(); doc["bus"]["i2c0"]["timeout"] = 200000
    doc["bus"]["i2c1"] = {"scl_pin": 7, "sda_pin": 6, "frequency": 50000, "timeout": 200000}
    doc["instance"].append({"driver": "bmp3xx", "name_ext": "", "bus": "i2c1", "address": 0x76})
    return doc, src_edit(tmp, "asy_i2c_driver.py", "_CLEAR_PULSES = const(9)", "_CLEAR_PULSES = const(18)"), None
add("bus.boot-clear-budget", "i2c0 and i2c1 both at timeout = 200000, asy_i2c_driver's _CLEAR_PULSES = const(18)", two_slow)
def attr_missing(tmp):
    doc = base_doc(); inst(doc, "notification")["wiring"]["signal_sink"] = {"default": True}
    staged = tmp / "src"; shutil.copytree(SRC, staged)
    return doc, staged, "attr"
add("wiring.default-attr-missing", "notification wiring.signal_sink = { default = true }, _DefaultSignalSink's request_signal renamed", attr_missing)

ok = 0
lines = []
for idx, (rule, desc, run) in enumerate(R):
    tmp = Path(tempfile.mkdtemp(dir=OUT))
    doc, src, extra = run(tmp)
    restore = None
    if isinstance(extra, tuple):
        table, key, value = extra; restore = (table, key, table[key]); table[key] = value
    if extra == "attr":
        p = src / "asy_notification_service.py"; t = p.read_text()
        import re
        m = re.search(r"class _DefaultSignalSink.*?(?=\nclass |\Z)", t, re.S)
        assert m, "no _DefaultSignalSink"
        p.write_text(t.replace(m.group(0), m.group(0).replace("request_signal", "request_signalx")))
    try:
        V.build_model(write_text(tmp, "fixture", doc) if isinstance(doc, str) else write_doc(tmp, "fixture", doc), src)
        got = ("BUILT", None, None, "")
    except BuildError as e:
        got = (e.rule, e.instance, e.field, str(e))
    finally:
        if restore: restore[0][restore[1]] = restore[2]
    mark = "OK " if got[0] == rule else "XX "
    ok += got[0] == rule
    lines.append(f"{mark}{rule}\t{desc}\t-> {got[0]} inst={got[1]} field={got[2]}\t{got[3][:220]}")
for line in lines: print(line)
print(f"{ok}/{len(R)} fire as expected; rules covered: {len({r for r, _d, _f in R})}")
