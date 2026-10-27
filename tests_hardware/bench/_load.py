"""The bench modules' shared parts: one /sensors reader worker counting the requests it got answered and range-checking
each body against the drivers' own schemas, the per-driver measurement checks against the sourced plausibility bounds,
and the bench board's facts, readiness probes and NTP end wait several modules read (SPECIFICATION.md C.8)."""

import contextlib
import functools
import json
import threading
import time
import types
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

import harness
import http_client
from error_log_helpers import errcount_entry, get_errcount
from http_client import JSONObject, JSONValue
from plausibility_bounds import BOUNDS

from buildgen.definitions import definitions_for_toml
from buildgen.schema_ast import extract_field_schemas
from buildgen.validate import build_model, ntp_backoff
from tests._src_const import py_value, src_const

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence

    import pytest
    from bench_control import BenchBridge

    from buildgen.jsontypes import JsonDict, JsonValue
    from buildgen.model import DeviceModel

# @tunable l4.bench_load_probe_timeout_s = 10.0
_PROBE_TIMEOUT_S = 10.0
# @tunable l4.network_resilience_ntp_resync_after_reset_timeout_s = 120.0
_NTP_RESYNC_AFTER_RESET_TIMEOUT_S = 120.0
# @tunable l4.network_resilience_ntp_retry_chain_margin_s = 10.0
_NTP_RETRY_CHAIN_MARGIN_S = 10.0
# @tunable l4.network_resilience_sync_age_slack_s = 2.0
_SYNC_AGE_SLACK_S = 2.0
# @tunable l4.network_resilience_wait_poll_s = 2.0
_WAIT_POLL_S = 2.0
_ISL29125_DRIVER = "asy_isl29125_driver.py"
_MATH_HELPERS = "math_helpers.py"
_NTP = "asy_ntp_client.py"
_HUE_SPAN = (0.0, 360.0)  # source: src/math_helpers.py rgb_to_hsb(), "hue in [0, 360)"
# The widest JSON number a double round-trips to: no numeric field a client sends can be longer.
_MAX_JSON_NUMBER = len("-1.2345678901234567e+308")
_NESTED_ROUTE = "/sensors"  # source: src/asy_webserver_service.py, the one PUT route nesting its body per group
# Per driver, each /measurements field and the plausibility_bounds quantity it is held to.
_QUANTITIES: "dict[str, tuple[tuple[str, str], ...]]" = {
    "scd30": (("CO2", "co2_ppm"), ("Hum", "humidity_rh"), ("Temp", "scd30_temp_c")),
    "sgp40": (("VOC", "voc_index"), ("Raw", "voc_raw_ticks")),
    "bmp3xx": (("Pres", "pressure_hpa"), ("SLPres", "pressure_hpa"), ("Temp", "bmp3xx_temp_c")),
    "isl29125": (("Lux", "lux"),),
}


class Fetch(Protocol):
    # http_client.fetch()'s positional shape, which a module's ceiling-retry wrapper keeps too.
    def __call__(self, host: str, port: int, method: str, path: str, json_body: "JSONObject | None" = ..., timeout_s: float = ...) -> http_client.HttpResponse: ...


class Load:
    # One load arm's record, filled by its threads: each failed request, each torn or corrupted answer, and one entry
    # per request answered (2xx, parsed), with the arm's `context` in each message. Failures are tolerated by a fault
    # arm; nothing tolerates a finding.
    def __init__(self, context: str = "") -> None:
        self.context = context
        self.answered: list[int] = []
        self.failures: list[str] = []
        self.findings: list[str] = []
        self._lock = threading.Lock()

    def failure(self, message: str) -> None:
        with self._lock:
            self.failures.append(message)

    def finding(self, message: str) -> None:
        with self._lock:
            self.findings.append(message)


class Note(Protocol):
    # The result_note fixture as a test receives it: a note on the test's report, recovery=True marking a recovery pass.
    def __call__(self, text: str, *, recovery: bool = ...) -> None: ...


class Noted:
    # A test's result_note, forwarded, remembering whether recover_by_reset() reported a recovery pass: the checks it
    # names as skipped are then skipped by the test too.
    def __init__(self, note: Note) -> None:
        self._note = note
        self.recovered = False

    def __call__(self, text: str, *, recovery: bool = False) -> None:
        self.recovered = self.recovered or recovery
        self._note(text, recovery=recovery)


class SessionNote(Protocol):
    # The session_note fixture: a note on the run record's session section, for a module- or session-scoped fixture.
    def __call__(self, text: str, *, recovery: bool = ..., source: str) -> None: ...


def _bench_conftest(request: "pytest.FixtureRequest") -> "types.ModuleType":
    # bench/conftest.py as pytest registered it, found by its file: pytest imports every conftest as a bare `conftest`,
    # which the tier's root conftest shares, so that name cannot reach it.
    target = Path(__file__).with_name("conftest.py").resolve()
    found = [p for p in request.config.pluginmanager.get_plugins() if isinstance(p, types.ModuleType) and isinstance(p.__file__, str) and Path(p.__file__).resolve() == target]
    assert len(found) == 1, f"pytest registered {len(found)} plugins for {target}"
    return found[0]


@functools.cache
def _config_schemas(device: "str | None" = None) -> "dict[str, dict[str, tuple[object, object, object]]]":
    # Per sensor's /sensors key, every int or float config field's (min, max, special) from its driver's schema.
    found: dict[str, dict[str, tuple[object, object, object]]] = {}
    for spec in _model(device).instances.values():
        if spec.driver_info is not None and spec.driver_info.kind == "sensor" and spec.resolved_name:
            fields = extract_field_schemas(spec.driver_info.source_path)
            found[spec.resolved_name] = {name: (low, high, special) for name, (kind, _default, low, high, special) in fields.items() if kind in ("int", "float")}
    return found


def _field_bytes(field: "JsonDict") -> int:
    # The longest JSON text one writable field's value can take, by its definitions kind.
    kind = field.get("kind")
    if kind == "string":
        length = field.get("maxLength", 0)
        assert isinstance(length, int), f"{field.get('key')} maxLength is {length!r}"
        return length + 2  # the two quotes
    if kind == "toggle":
        return len("false")
    if kind == "enum":
        return max(len(json.dumps(option.get("value"))) for option in _objects(field.get("options")))
    if kind == "number":
        return _MAX_JSON_NUMBER
    if kind == "composite":
        return _members_bytes(_objects(field.get("subFields"))) + 1
    raise AssertionError(f"unhandled writable field kind {kind!r} of {field.get('key')}")


def _isl29125_findings(name: str, data: JSONObject) -> "list[str]":
    # ISL29125's own domain checks: the active range one of the driver's two, CCT inside McCamy's span or absent below the
    # low-light floor, the normalised RGB and saturation/brightness inside 0..1 and hue inside 0..360.
    findings: list[str] = []
    ranges = field_schema(_ISL29125_DRIVER, "Range")[4]
    if not isinstance(ranges, tuple) or data.get("RangeAct") not in ranges:
        findings.append(f"{name}.RangeAct={data.get('RangeAct')!r} is none of the driver's ranges {ranges!r} (src/{_ISL29125_DRIVER} _VAL_RANGE)")
    cct = data.get("CCT")
    if cct is not None:
        findings += _outside(f"{name}.CCT", cct, src_number(_MATH_HELPERS, "_CCT_MIN"), src_number(_MATH_HELPERS, "_CCT_MAX"), "src/math_helpers.py _CCT_MIN/_CCT_MAX (McCamy 1992)")
    unit = (src_number(_MATH_HELPERS, "_COLOUR_IN_MIN"), src_number(_MATH_HELPERS, "_COLOUR_IN_MAX"), "src/math_helpers.py _COLOUR_IN_MIN/_COLOUR_IN_MAX")
    for group, fields in (("RGB", (("R", unit), ("G", unit), ("B", unit))), ("HSB", (("H", (*_HUE_SPAN, "src/math_helpers.py rgb_to_hsb()")), ("S", unit), ("B", unit)))):
        values = data.get(group)
        if not isinstance(values, dict):
            findings.append(f"{name}.{group} is {values!r}, not an object")
            continue
        for field, (low, high, source) in fields:
            findings += _outside(f"{name}.{group}.{field}", values.get(field), low, high, source)
    return findings


def _members_bytes(fields: "list[JsonDict]") -> int:
    # `"key":value,` per member, each value at its longest.
    return sum(len(json.dumps(f.get("key"))) + 1 + _field_bytes(f) + 1 for f in fields)


@functools.cache
def _model(device: "str | None" = None) -> "DeviceModel":
    return build_model(harness.device_toml(device), harness.SRC_DIR)


@functools.cache
def _ntp_backoff() -> "tuple[float, float]":
    # The bench device's unsynced backoff as its NTPClient runs it: buildgen's effective pair (the generated NtpTiming's,
    # validate.ntp_backoff()), the interval at least one check tick and the cap at least the interval (asy_ntp_client.py).
    table = _model().doc.get("device")
    assert isinstance(table, dict), f"{harness.device_toml()} has no [device] table"
    retry_s, retry_max_s = ntp_backoff(table, harness.SRC_DIR)
    period = max(retry_s, src_number(_NTP, "_NTP_CHECK_INTERV"))
    return period, max(retry_max_s, period)


def _ntp_error_log_contains(dut_ip: str, errno: int) -> bool:
    # Whether the NTP logger's history holds error `errno` (a code() read, never a number restated here).
    return any(h.get("num") == errno and h.get("type") == "E" for h in errcount_entry(get_errcount(dut_ip), "NTP")["history"])


def _ntp_retry_chain_s() -> float:
    # A synced client's failed attempt arms up to _NTP_SYNC_RETRIES one-shot retries, each _NTP_RETRY_INTERV after the
    # failure before it (src/asy_ntp_client.py _handle_ntp_sync_failure()); a retry finding no network ends it silently.
    return src_number(_NTP, "_NTP_SYNC_RETRIES") * (src_number(_NTP, "_NTP_RETRY_INTERV") + ntp_attempt_s())


def _ntp_view(dut_ip: str) -> "tuple[int, bool, object] | None":
    # NTP's logged count, NTPSynced and NTPLastSyncAge from one GET /status, None while the board does not answer.
    try:
        status = get_object(dut_ip, "/status")
        networking = as_object(status.get("networking"), "GET /status networking")
        counter = errcount_entry(as_object(status.get("errcount"), "GET /status errcount"), "NTP")["counter"]
    except (OSError, http_client.HTTP_ERROR, ValueError, TypeError, AssertionError):
        return None
    return counter, networking.get("NTPSynced") is True, networking.get("NTPLastSyncAge")


def _objects(value: "JsonValue") -> "list[JsonDict]":
    # A definitions list whose every entry is an object, as the schema requires.
    assert isinstance(value, list) and all(isinstance(item, dict) for item in value), f"a definitions list holds {value!r}"
    return [item for item in value if isinstance(item, dict)]


def _outside(label: str, value: "JSONValue", low: float, high: float, source: str) -> "list[str]":
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not low <= value <= high:
        return [f"{label}={value!r} not within [{low}, {high}] ({source})"]
    return []


def _repair_leftover(host: str, route: str, body: JSONObject) -> None:
    # An aborted run's leftover PUT back (the caller notes the repair): every field of `body`, nested per group on
    # /sensors, must come back "Valid".
    res = http_client.fetch(host, 80, "PUT", route, body, timeout_s=_PROBE_TIMEOUT_S)
    assert res.status_code == 200, f"repairing a leftover on {route} failed: {res.status_code} {res.body[:200]!r}"
    result = as_object(res.json().get("result"), f"PUT {route} result")
    words = {f"{group}.{field}": as_object(result.get(group), f"result.{group}").get(field) for group, fields in body.items() if isinstance(fields, dict) for field in fields}
    words.update({field: result.get(field) for field, value in body.items() if not isinstance(value, dict)})
    refused = {key: word for key, word in words.items() if word != "Valid"}
    assert words and not refused, f"repairing a leftover on {route} was not taken: {refused or res.body[:200]!r}"


def _section_body_bytes(section: "JsonDict") -> int:
    # One section's largest PUT body: its writable fields per group, nested under each group's key on /sensors only.
    rest = section.get("rest")
    if not isinstance(rest, dict) or "put" not in rest:
        return 0
    groups = {str(g.get("key")): _members_bytes([f for f in _objects(g.get("fields", [])) if f.get("kind") not in (None, "readonly")]) for g in _objects(section.get("groups", []))}
    groups = {key: cost for key, cost in groups.items() if cost}
    if not groups:
        return 0
    if rest.get("put") == _NESTED_ROUTE:
        return sum(len(json.dumps(key)) + 1 + (cost + 1) + 1 for key, cost in groups.items()) + 2
    return sum(groups.values()) + 2


def get_object(dut_ip: str, path: str, timeout_s: float = _PROBE_TIMEOUT_S) -> JSONObject:
    # GET `path`, strict: a 200 whose body is one JSON object.
    res = http_client.fetch(dut_ip, 80, "GET", path, timeout_s=timeout_s)
    assert res.status_code == 200, f"GET {path} failed: {res.status_code} {res.body[:200]!r}"
    return res.json()


def allowed_ints(src_file: str, field: str) -> "list[int]":
    # A discrete field's allowed settings, its schema's special tuple (e.g. PresOvers' oversampling steps).
    special = field_schema(src_file, field)[4]
    assert isinstance(special, tuple) and all(isinstance(v, int) for v in special), f"src/{src_file} {field} declares no allowed-value tuple: {special!r}"
    return [v for v in special if isinstance(v, int)]


def as_object(value: "JSONValue", where: str) -> JSONObject:
    # One nested JSON value narrowed to the object the REST shape says it is, or a failure naming where it was not.
    assert isinstance(value, dict), f"{where} is {value!r}, not a JSON object"
    return value


def buildgen_number(module_file: str, name: str) -> float:
    # One literal buildgen writes into every generated device module (NtpTiming's fetch timeout, the WDT timeout), read
    # from the buildgen/ module that holds it.
    value = py_value(str(harness.REPO_ROOT / "buildgen" / module_file), name)
    assert isinstance(value, (int, float)) and not isinstance(value, bool), f"buildgen/{module_file} {name} is {value!r}, no number"
    return value


def bus_loggers(device: "str | None" = None) -> "list[str]":
    # The logger of every instance on an I2C or SPI bus: the modules a bus fault or a bus load reaches.
    return sorted(spec.resolved_name for spec in _model(device).instances.values() if spec.resolved_name and str(spec.fields.get("bus", "")).startswith(("i2c", "spi")))


def bus_sharer_loggers(driver: str, device: "str | None" = None) -> "list[str]":
    # The FRAM-backed loggers of every other instance on `driver`'s bus, their config stores' CFGMGR_ loggers included.
    model = _model(device)
    own = next(spec for spec in model.instances.values() if spec.driver == driver)
    sharers = {spec.resolved_name for spec in model.instances.values() if spec is not own and spec.resolved_name and spec.fields.get("bus") == own.fields.get("bus")}
    return [name for name in harness.fram_backed_logger_names(device) if name.removeprefix("CFGMGR_") in sharers]


def field_schema(src_file: str, field: str) -> "tuple[object, object, object, object, object]":
    # One REST field's (type, default, min, max, special) as its src/ schema tuple declares it, by buildgen's reader.
    fields = extract_field_schemas(harness.SRC_DIR / src_file)
    assert field in fields, f"src/{src_file} declares no schema field {field!r}"
    return fields[field]


def image_deviations(request: "pytest.FixtureRequest", dut_ip: str, record: "dict[str, object]", *, allow_rollover: bool = False) -> "list[tuple[str, str, str, str]]":
    # bench/conftest.py's check_image(): how the board's running image differs from `record`, for a mid-session reflash.
    found = _bench_conftest(request).check_image(dut_ip, record, allow_rollover=allow_rollover)
    assert isinstance(found, list) and all(isinstance(row, tuple) and len(row) == 4 for row in found), f"check_image() answered {found!r}"
    return [(str(a), str(b), str(c), str(d)) for a, b, c, d in found]


def instance_loggers(driver: str, device: "str | None" = None) -> "list[str]":
    # The loggers of every instance of `driver` the bench TOML declares, as the generated definitions name them.
    return sorted(spec.resolved_name for spec in _model(device).instances.values() if spec.driver == driver and spec.resolved_name)


def join(threads: "Sequence[threading.Thread]", timeout_s: float) -> "list[str]":
    # Joins every started thread, each bounded; the names of those still running, which the caller fails on.
    for thread in threads:
        if thread.ident is not None:
            thread.join(timeout_s)
    return [thread.name for thread in threads if thread.is_alive()]


def largest_put_body(device: "str | None" = None) -> int:
    # The largest body any PUT route of the bench build's schemas can legitimately be sent, in bytes, derived from its
    # website definitions as tests_scripts/test_request_body_cap_headroom.py derives it per device.
    sections = _objects(definitions_for_toml(harness.device_toml(device), harness.SRC_DIR).get("sections"))
    return max(_section_body_bytes(section) for section in sections if isinstance(section.get("rest"), dict))


def measurement_findings(body: JSONObject, device: "str | None" = None) -> "list[str]":
    # Every sensor the bench TOML declares, checked by its driver's entry against the sourced bounds: a declared
    # sensor with no checker, a missing key or field, or a value outside its bound is a finding naming the source.
    findings: list[str] = []
    for spec in _model(device).instances.values():
        if spec.driver_info is None or spec.driver_info.kind != "sensor" or spec.resolved_name is None:
            continue
        if spec.driver not in _QUANTITIES:
            findings.append(f"no plausibility checker for driver {spec.driver}")
            continue
        data = body.get(spec.resolved_name)
        if not isinstance(data, dict):
            findings.append(f"GET /measurements carries no {spec.resolved_name} object: {data!r}")
            continue
        for field, quantity in _QUANTITIES[spec.driver]:
            low, high, source = BOUNDS[quantity]
            findings += _outside(f"{spec.resolved_name}.{field}", data.get(field), low, high, source)
        if spec.driver == "isl29125":
            findings += _isl29125_findings(spec.resolved_name, data)
    return findings


def mode(host: str) -> object:
    # GET /status's networking.Mode: "AP" while the DUT hosts its hotspot, "STA" otherwise (src/asy_wifi_service.py).
    return as_object(get_object(host, "/status").get("networking"), "GET /status networking").get("Mode")


def ntp_attempt_s() -> float:
    # One sync attempt's longest run (src/asy_ntp_client.py _run_ntp_sync_attempt()): a send and a reply wait per lookup
    # try on each server, the DHCP one and up to _DNS_FALLBACK_MAX more (asy_dns_client.py resolve_ipv4()), then the NTP
    # request's send and reply wait (_fetch_ntp_reply()), each bounded by its timeout in buildgen/codegen.py.
    servers = 1 + src_number(_NTP, "_DNS_FALLBACK_MAX")
    lookup_s = servers * buildgen_number("codegen.py", "_DNS_TRIES") * 2 * buildgen_number("codegen.py", "_DNS_TIMEOUT_MS") / 1000
    return lookup_s + 2 * ntp_fetch_timeout_s()


def ntp_fetch_timeout_s() -> float:
    # The client's reply timeout: NtpTiming.fetch_timeout_ms, which buildgen/codegen.py writes into the device module.
    return buildgen_number("codegen.py", "_NTP_FETCH_TIMEOUT_MS") / 1000


def ntp_retry_max_s() -> float:
    # The cap the unsynced client's doubling backoff stops at (_ntp_backoff()).
    return _ntp_backoff()[1]


def ntp_retry_period_s() -> float:
    # The unsynced client's first retry step, rounded up to the check tick it is counted on (_ntp_backoff()).
    return _ntp_backoff()[0]


def ntp_synced(dut_ip: str) -> bool:
    # GET /status's networking.NTPSynced, False while the board does not answer.
    try:
        networking = get_object(dut_ip, "/status").get("networking")
    except (OSError, http_client.HTTP_ERROR, ValueError, TypeError, AssertionError):
        return False
    return isinstance(networking, dict) and networking.get("NTPSynced") is True


@contextlib.contextmanager
def readers(count: int, dut_ip: str, load: Load, *, iterations: int, timeout_s: float, join_s: float, fetch: Fetch = http_client.fetch, others: "Sequence[threading.Thread]" = ()) -> "Iterator[list[str]]":
    # `count` reader threads over one shared record, plus `others` (a writer, a fault), started for the with-block and
    # joined when it ends, each bounded: the list it yields then names those still running, which the caller fails on.
    threads = [threading.Thread(target=sensors_reader, args=(dut_ip, iterations, load), kwargs={"timeout_s": timeout_s, "fetch": fetch}, name=f"reader-{n}") for n in range(count)]
    threads += others
    alive: list[str] = []
    try:
        for thread in threads:
            thread.start()
        yield alive
    finally:
        alive += join(threads, join_s)


def reset_and_wait(board: "harness.Board", bench: "BenchBridge", dut_ip: str, *, timeout_s: float) -> None:
    # The reset a test makes as its own step (never a recovery): the kick, the one reset, then a passive wait for serving.
    harness.kick_then_reset(board, bench)
    harness.wait_until(lambda: serving(dut_ip), timeout_s=timeout_s, description="the DUT serving after the test's own reset")


def round_image(request: "pytest.FixtureRequest") -> "tuple[Path, dict[str, object]]":
    # The round's standard image and its record, as the board_image fixture found them: the .uf2 beside the record.
    path = _bench_conftest(request).record_path(request.config.getoption("--image-record"), harness.bench_device())
    assert isinstance(path, Path), f"record_path() answered {path!r}"
    record = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(record, dict), f"the image record at {path} holds no JSON object"
    uf2 = path.with_suffix(".uf2")
    assert uf2.is_file(), f"no round image beside its record: {uf2}"
    return uf2, record


def schema_sanity_findings(body: JSONObject, context: str) -> "list[str]":
    # Each numeric config field of a GET /sensors body against its driver's own schema: a value outside it is a torn or
    # corrupted read, never a setting the board could hold. A body with no checkable field is a finding too.
    findings: list[str] = []
    checked = 0
    for name, schema in _config_schemas().items():
        cfg = body.get(name)
        if not isinstance(cfg, dict):
            findings.append(f"GET /sensors carries no {name} object{context}")
            continue
        for field, (low, high, special) in schema.items():
            value = cfg.get(field)
            bounded = isinstance(low, (int, float)) and isinstance(high, (int, float))
            if value is None or isinstance(value, bool) or not isinstance(value, (int, float)) or not (bounded or isinstance(special, tuple)):
                continue
            checked += 1
            allowed = special if isinstance(special, tuple) else (special,)
            in_range = bounded and isinstance(low, (int, float)) and isinstance(high, (int, float)) and low <= value <= high
            if not (in_range or value in allowed):
                findings.append(f"{name} {field}={value!r} outside its schema ({low}..{high}, special {special!r}){context} - a torn or corrupted read")
    if not checked:
        findings.append(f"GET /sensors held no numeric config field to check{context}")
    return findings


def sensors_reader(dut_ip: str, iterations: int, load: Load, *, timeout_s: float, fetch: Fetch = http_client.fetch) -> None:
    # One worker: GET /sensors `iterations` times, each answer counted and checked, each failure recorded; a refusal or a
    # cut-off answer is a failure here, never a crash of the worker.
    for i in range(iterations):
        try:
            res = fetch(dut_ip, 80, "GET", "/sensors", None, timeout_s=timeout_s)
            body = res.json() if res.status_code == 200 else None
        except (OSError, http_client.HTTP_ERROR, ValueError, TypeError) as e:
            load.failure(f"GET /sensors {i}{load.context}: {type(e).__name__}: {e}")
            continue
        if body is None:
            load.failure(f"GET /sensors {i}{load.context}: {res.status_code} {res.body[:120]!r}")
            continue
        load.answered.append(1)
        for finding in schema_sanity_findings(body, load.context):
            load.finding(f"GET /sensors {i}: {finding}")


def serving(dut_ip: str) -> bool:
    # GET /status answered 200, False while the board does not answer: a passive readiness probe.
    try:
        return http_client.fetch(dut_ip, 80, "GET", "/status", timeout_s=_PROBE_TIMEOUT_S).status_code == 200
    except (OSError, http_client.HTTP_ERROR):
        return False


def src_number(src_file: str, name: str) -> float:
    # One module-level const() of a src/ file, read from its text (const() names do not survive compilation).
    value = src_const(str(harness.SRC_DIR / src_file), name)
    assert isinstance(value, (int, float)) and not isinstance(value, bool), f"src/{src_file} {name} is {value!r}, no number"
    return value


def sta_mode(dut_ip: str) -> bool:
    # STA mode is GET /status's networking.Mode with the board answering over the bridge; /networking carries no such
    # field (owner, 2026-09-26: 'It seems to be unreachable by definition.').
    try:
        return mode(dut_ip) == "STA"
    except (OSError, http_client.HTTP_ERROR, ValueError, TypeError, AssertionError):
        return False


def wait_for_ntp_quiet(dut_ip: str, served_at: float, result_note: Note) -> None:
    # What NTP still does after an outage logs into this window: the reset path's boot sync, after serving, and the
    # retries a failure here arms. Synced is required; a logged failure then waits for a newer sync, or for the chain's
    # longest run since serving: an attempt holds wifi_mode_lock, which the reconnect takes (_sync_loop()).
    synced_by = served_at + _NTP_RESYNC_AFTER_RESET_TIMEOUT_S
    chain_by = served_at + _ntp_retry_chain_s() + _NTP_RETRY_CHAIN_MARGIN_S
    counted, counted_at, view = -1, served_at, None
    while True:
        asked = time.monotonic()
        view = _ntp_view(dut_ip)
        answered = time.monotonic()
        if view is not None:
            counter, synced, age = view
            if counter != counted:
                counted, counted_at = counter, answered  # every failure counted so far lies before this answer
            # LastSyncAge is whole seconds, refreshed on a 1 s tick (asy_base_classes.py arm_tick_timer(), TickSeconds.read()).
            fresh = isinstance(age, (int, float)) and not isinstance(age, bool) and asked - age - _SYNC_AGE_SLACK_S > counted_at
            if synced and (counter == 0 or fresh or answered >= chain_by):
                ended = "nothing logged" if counter == 0 else "a sync newer than its last failure" if fresh else "the retry chain's bound"
                result_note(f"NTP quiet {answered - served_at:.0f}s after serving: {ended}")
                return
        if answered >= synced_by:
            raise TimeoutError(f"NTP not synced within {_NTP_RESYNC_AFTER_RESET_TIMEOUT_S}s of serving after the outage, so its sync would log into the next test's window: last view (counter, synced, age) {view!r}")
        time.sleep(_WAIT_POLL_S)
