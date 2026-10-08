"""Completeness guard for tests_hardware/'s persistence gate: a test that PUTs a config-persisting
field but forgets @pytest.mark.persistence_write spends real RP2040 flash wear on every routine run,
silently. The sibling gating test proves the flag WORKS; this proves nothing escapes it unowned."""

# The gate covers the write a test OWNS, not one it is merely reached through: a shared
# prerequisite stays unmarked, since gating it would deselect the tests it enables. Owner's rule,
# 2026-09-18; tests_hardware/README.md states it fully, and why the answer is not "spend zero".

import ast
import re
import sys
from functools import cache
from pathlib import Path
from typing import TYPE_CHECKING, NamedTuple

import pytest
from _devices import DEVICE_NAMES, device_toml

from buildgen.definitions import definitions_for_toml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tests_hardware"))

from persistence_groups import persistence_groups

if TYPE_CHECKING:
    from collections.abc import Iterator

# Tests whose only persisting-looking PUT provably writes nothing, with the reason each is exempt.
# asy_config_manager.py's write_config() short-circuits on `if not changed` BEFORE staging anything, so
# a body whose every field is rejected (or unchanged) never reaches _flush_staged()'s json.dump().
_JUSTIFIED_UNMARKED = {
    "test_put_nonsense_field_values_are_marked_invalid_not_crashed": "every field in the body is rejected as Invalid, so write_config() returns on `not changed` without staging a flash write",
    "test_the_largest_body_any_schema_can_produce_still_fits_under_the_cap": "its NTPHost, the largest string field, is 254 characters, ONE over _VAL_NTP_HOST's own 3..253 bound (RFC 1035), so the field is rejected as Invalid and write_config() returns on `not changed` - at exactly 253 it would be valid and this would be a real flash write",
}

# Non-test functions (helpers and fixtures) that issue a persisting PUT. Pinned by name so a NEW one
# has to be triaged deliberately: a helper is reached from several tests at once, and marking its
# callers is a judgement call this file cannot make for a caller it has never seen.
_KNOWN_PERSISTING_HELPERS = {
    "isl29125_write_worker",  # bus-concurrency writer, driven only from persistence_write-marked tests
    "bmp3xx_write_worker",  # same
    # Fixture: its stage-0 PUT forces hotspot mode so two dozen tests can run at all, and its
    # stage-7 restore undoes that - prerequisite writes, so every dependent but the three that
    # PUT a persisting field themselves is correctly unmarked.

    # Stated as a rule, not a count: an earlier revision named "its six unmarked dependents",
    # which was wrong when written and would have gone stale anyway.
    "joined_hotspot",
    "_restore_ssid_over",  # teardown-side restore for the garbage-SSID outage test
    "_recover_stale_dut_credentials",  # session-level recovery path, not a test's own write
    # The MQTT bench module's fixture: one write points the client at the bench broker for every test there,
    # and its undo leaves the next module the old baseline - prerequisite writes, so no dependent is marked.
    "_enable_mqtt",
    "_disable_mqtt",
}


def _tests_hardware_modules(repo_root: Path) -> list[Path]:
    base = repo_root / "tests_hardware"
    # device_scripts/ is real MicroPython pushed to the board - it has no http_client and no markers.
    return sorted(p for p in base.rglob("*.py") if "device_scripts" not in p.parts)


@cache
def _flagged_fields(repo_root: Path, flag: str) -> frozenset[str]:
    # Every field key carrying `flag: true` in any device's generated definitions, the one source the
    # website, the mock and this gate all read the two never-"Unchanged" classes from.
    found = set()
    for device in DEVICE_NAMES:
        definitions = definitions_for_toml(device_toml(device), repo_root / "src")
        found |= {f["key"] for s in definitions["sections"] for g in s["groups"] for f in g.get("fields", []) if f.get(flag) is True}
    return frozenset(found)


def _dispatch_only_fields(repo_root: Path) -> frozenset[str]:
    # Every field a PUT can carry that persists nothing: the definitions' `dispatch` fields.
    dispatch_only = _flagged_fields(repo_root, "dispatch")
    assert dispatch_only, "no `dispatch` field in any device's definitions - the derivation broke, and every dispatch-only PUT would now look like a flash write"
    return dispatch_only


def _always_executed_fields(repo_root: Path) -> frozenset[str]:
    # The fields the chip takes on every PUT (`alwaysExecuted`): each one writes the chip's own store.
    return _flagged_fields(repo_root, "alwaysExecuted")


def _leaf_keys(node: ast.expr) -> set[str]:
    # Every leaf key of a literal PUT body - {"SGP40": {"BackupPeriod": 1}} is BackupPeriod, not SGP40.
    keys: set[str] = set()
    if isinstance(node, ast.Dict):
        for key, value in zip(node.keys, node.values, strict=True):
            if isinstance(value, ast.Dict):
                keys |= _leaf_keys(value)
            elif isinstance(key, ast.Constant) and isinstance(key.value, str):
                keys.add(key.value)
    return keys


class _FetchShape(NamedTuple):
    # Where fetch() really keeps its method and body arguments, read from its own def below.

    method_at: int
    body_at: int
    body_kw: str
    path_at: int


def _fetch_shape(repo_root: Path) -> _FetchShape:
    # Derived, never hardcoded: every detector here indexes fetch()'s positional arguments, so a
    # reordered or renamed parameter would silently make them read the wrong one - and the keyword
    # fallback did exactly that, looking for `body=` when the parameter has always been `json_body`.
    tree = ast.parse((repo_root / "tests_hardware" / "http_client.py").read_text())
    fn = next((n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "fetch"), None)
    assert fn is not None, "tests_hardware/http_client.py no longer defines fetch() - every detector in this file reads its call sites"
    names = [arg.arg for arg in fn.args.args]
    bodies = [n for n in names if "body" in n]
    assert len(bodies) == 1, f"fetch()'s body argument is no longer unambiguous ({bodies}) - update this derivation with it"
    assert "method" in names, f"fetch() no longer takes a `method` argument ({names}) - every detector here reads it to tell a PUT from a GET"
    assert "path" in names, f"fetch() no longer takes a `path` argument ({names}) - the group derivation reads it to find the route"
    return _FetchShape(names.index("method"), names.index(bodies[0]), bodies[0], names.index("path"))


def _fetch_calls(path: Path) -> "Iterator[tuple[str, ast.Call]]":
    # (enclosing function name, call) for every call named `fetch` in the module.
    tree = ast.parse(path.read_text())
    for fn in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef)]:
        for call in [n for n in ast.walk(fn) if isinstance(n, ast.Call)]:
            name = call.func.attr if isinstance(call.func, ast.Attribute) else getattr(call.func, "id", "")
            if name == "fetch":
                yield fn.name, call


def _argument(call: ast.Call, index: int, keyword: str) -> ast.expr | None:
    # One argument of a call, whether it was passed positionally or by keyword.
    if len(call.args) > index:
        return call.args[index]
    return next((kw.value for kw in call.keywords if kw.arg == keyword), None)


def _put_body(call: ast.Call, shape: _FetchShape) -> ast.expr | None:
    # The body a fetch() call PUTs, or None when the call is not a literal-method PUT with a body.
    method = _argument(call, shape.method_at, "method")
    if not (isinstance(method, ast.Constant) and method.value == "PUT"):
        return None
    return _argument(call, shape.body_at, shape.body_kw)


def _non_literal_put_bodies(path: Path, shape: _FetchShape) -> list[str]:
    # Function names whose PUT body is not a literal dict, so _leaf_keys() cannot read it and the
    # detector below never sees them as writers. Enumerated rather than left implicit, or a
    # `payload = {...}` refactor would silently unmark a marked test.
    offenders = []
    for fn_name, call in _fetch_calls(path):
        body = _put_body(call, shape)
        if body is not None and not isinstance(body, ast.Dict):
            offenders.append(fn_name)
    return sorted(set(offenders))


def _forwarded_method_calls(path: Path, shape: _FetchShape) -> list[str]:
    # Function names calling fetch() with a non-literal method: wrappers no detector here can
    # classify, since deciding whether a call writes at all starts by reading that argument.
    offenders = []
    for fn_name, call in _fetch_calls(path):
        method = _argument(call, shape.method_at, "method")
        if not (isinstance(method, ast.Constant) and isinstance(method.value, str)):
            offenders.append(fn_name)
    return sorted(set(offenders))


def _persisting_put_functions(path: Path, dispatch_only: frozenset[str], shape: _FetchShape) -> dict[str, set[str]]:
    # Function name -> the persisting fields its own body PUTs, for every function that PUTs one.
    found: dict[str, set[str]] = {}
    for fn_name, call in _fetch_calls(path):
        # A body argument is required for this to be a write at all, so a bodyless GET - or a PUT
        # whose body arrived by keyword, which the old positional-only read missed - is handled here
        # once, by _put_body(), rather than by each detector guessing at argument positions.
        body = _put_body(call, shape)
        keys = _leaf_keys(body) - dispatch_only if body is not None else set()
        if keys:
            found[fn_name] = found.get(fn_name, set()) | keys
    return found


def _marked_functions(path: Path) -> set[str]:
    tree = ast.parse(path.read_text())
    return {
        fn.name
        for fn in ast.walk(tree)
        if isinstance(fn, ast.FunctionDef | ast.AsyncFunctionDef)
        for dec in fn.decorator_list
        if "persistence_write" in ast.dump(dec)
    }


def test_every_test_that_persists_a_config_field_carries_the_marker(repo_root: Path) -> None:
    # The wear guard itself. An unmarked writer is invisible - it passes, the suite goes green, and
    # the only evidence is flash endurance spent on a run that was never meant to spend any.
    dispatch_only = _dispatch_only_fields(repo_root)
    shape = _fetch_shape(repo_root)
    offenders = []
    for path in _tests_hardware_modules(repo_root):
        marked = _marked_functions(path)
        for name, keys in _persisting_put_functions(path, dispatch_only, shape).items():
            if name.startswith("test_") and name not in marked and name not in _JUSTIFIED_UNMARKED:
                offenders.append(f"{path.relative_to(repo_root)}::{name} PUTs {sorted(keys)}")
    assert not offenders, "these tests persist config to the RP2040's flash without @pytest.mark.persistence_write:\n  " + "\n  ".join(offenders)


# Function -> why its non-literal PUT body is safe to be invisible to the detector above.
_JUSTIFIED_UNREADABLE_BODIES = {
    "test_put_oversized_body_is_rejected_with_413_over_the_normal_network": "the body is deliberately past max_content_length, so vendored ext/microdot.py rejects it with 413 before this project's route handler - and therefore ConfigManager - is ever reached",
    "_put_sized": "queue section 1D's body-cap helper: it pads an UNKNOWN sensor key, which PUT /sensors ignores silently, so no field of it ever reaches ConfigManager at any size - accepted or 413'd alike",
}


def test_every_unreadable_put_body_is_a_triaged_one(repo_root: Path) -> None:
    # Closes the detector's one blind spot by naming it: a PUT whose body is a variable yields no
    # keys, so the wear guard below passes on it no matter what it writes. Exactly one exists today
    # and it provably persists nothing; a second has to be triaged rather than silently inherit that.
    shape = _fetch_shape(repo_root)
    unreadable = {name for path in _tests_hardware_modules(repo_root) for name in _non_literal_put_bodies(path, shape)}
    assert unreadable == set(_JUSTIFIED_UNREADABLE_BODIES), f"a PUT body the marker guard cannot read changed - triage each one and update _JUSTIFIED_UNREADABLE_BODIES.\n  added: {sorted(unreadable - set(_JUSTIFIED_UNREADABLE_BODIES))}\n  gone: {sorted(set(_JUSTIFIED_UNREADABLE_BODIES) - unreadable)}"


# Wrapper -> why a fetch() call it makes may keep its method in a variable. An entry is only
# admissible when the wrapper presents http_client.fetch's own name and positional signature, so its
# CALLERS are what the detector reads; the test below re-derives that rather than trusting the entry.
_JUSTIFIED_FORWARDED_METHODS = {
    "tests_hardware/bench/test_bus_concurrency_under_api_load.py::fetch": "a ceiling-close retry wrapper that forwards every argument unchanged, named `fetch` with http_client.fetch's exact positional signature, so each call site is read directly and nothing is hidden behind it",
}


def _positional_parameters(path: Path, name: str) -> list[str]:
    # The positional parameter names of one top-level function, in order.
    tree = ast.parse(path.read_text())
    fn = next((n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef) and n.name == name), None)
    assert fn is not None, f"{path}::{name} is gone - drop its _JUSTIFIED_FORWARDED_METHODS entry with it"
    return [arg.arg for arg in fn.args.args]


def test_every_forwarding_wrapper_still_mirrors_fetchs_own_signature(repo_root: Path) -> None:
    # The exemption above rests entirely on the wrapper being indistinguishable from fetch() at its
    # call sites. Rename one parameter or reorder two and that stops being true while the allowlist
    # entry goes on excusing it - so the premise is re-derived here, never assumed.
    expected = _positional_parameters(repo_root / "tests_hardware" / "http_client.py", "fetch")
    for entry in _JUSTIFIED_FORWARDED_METHODS:
        rel, _, name = entry.partition("::")
        actual = _positional_parameters(repo_root / rel, name)
        assert actual == expected, f"{entry} no longer mirrors http_client.fetch's positional signature, so its call sites are no longer readable by the detector: {actual} != {expected}"


def test_no_fetch_wrapper_hides_its_method_from_the_detector(repo_root: Path) -> None:
    # F15's residual, closed. Every detector above starts by reading fetch()'s method argument, so a
    # wrapper forwarding its own parameter there is classified as nothing at all - which is exactly
    # how isl29125_write_worker and bmp3xx_write_worker left _KNOWN_PERSISTING_HELPERS unnoticed.
    shape = _fetch_shape(repo_root)
    forwarders = {
        f"{path.relative_to(repo_root)}::{name}"
        for path in _tests_hardware_modules(repo_root)
        for name in _forwarded_method_calls(path, shape)
    }
    assert forwarders == set(_JUSTIFIED_FORWARDED_METHODS), f"a fetch() call now passes its method as a variable, so the wear guard cannot tell a PUT from a GET there. Give the wrapper http_client.fetch's own name and positional signature, or triage it into _JUSTIFIED_FORWARDED_METHODS.\n  added: {sorted(forwarders - set(_JUSTIFIED_FORWARDED_METHODS))}\n  gone: {sorted(set(_JUSTIFIED_FORWARDED_METHODS) - forwarders)}"


def test_a_synthetic_forwarding_wrapper_is_actually_caught(tmp_path: Path, repo_root: Path) -> None:
    # The same "prove it bites" treatment the detector itself gets: F14's first draft is replayed
    # verbatim, and must be both invisible to the PUT detector and loud in the check above.
    module = tmp_path / "test_wrapper.py"
    module.write_text(
        'def _put(ip, method, route, body):\n'
        '    return http_client.fetch(ip, 80, method, route, body, timeout_s=10.0)\n'
        '\n'
        'def test_writes() -> None:\n'
        '    _put(ip, "PUT", "/sensors", {"BMP3XX": {"PresOvers": 4}})\n',
    )
    shape = _fetch_shape(repo_root)
    assert _persisting_put_functions(module, _dispatch_only_fields(repo_root), shape) == {}, "the PUT detector cannot see through a wrapper - if it ever can, this guard is redundant, not wrong"
    assert _forwarded_method_calls(module, shape) == ["_put"]


def test_a_put_body_passed_by_keyword_is_still_seen(tmp_path: Path, repo_root: Path) -> None:
    # The positional-only read missed this outright, and its keyword fallback looked for `body=`
    # while the parameter has always been `json_body` - so the one escape hatch could never fire.
    module = tmp_path / "test_keyword.py"
    module.write_text('def test_writes() -> None:\n    http_client.fetch(ip, 80, "PUT", "/sensors", json_body={"BMP3XX": {"PresOvers": 4}}, timeout_s=10.0)\n')
    found = _persisting_put_functions(module, _dispatch_only_fields(repo_root), _fetch_shape(repo_root))
    assert found == {"test_writes": {"PresOvers"}}


# Modules that issue HTTP without going through fetch(), and why each is not a way to reach a PUT.
_HTTP_LIBRARIES = frozenset({"urllib", "http", "requests", "httpx", "aiohttp"})


def test_fetch_is_the_only_route_from_this_tier_to_an_http_request(repo_root: Path) -> None:
    # Every check in this file begins at a call named fetch, so a module driving an HTTP library
    # itself would bypass the wear guard completely. Raw `socket` is deliberately out of scope: this
    # tier uses it for DNS probes and the connection-ceiling rows, never to speak HTTP.
    offenders = []
    for path in _tests_hardware_modules(repo_root):
        if path.name == "http_client.py":  # the one place allowed to, and the shape everything else reads
            continue
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.Import):
                offenders += [f"{path.relative_to(repo_root)}: import {a.name}" for a in node.names if a.name.split(".")[0] in _HTTP_LIBRARIES]
            elif isinstance(node, ast.ImportFrom) and (node.module or "").split(".")[0] in _HTTP_LIBRARIES:
                offenders.append(f"{path.relative_to(repo_root)}: from {node.module} import ...")
    assert not offenders, "these modules can issue an HTTP request without going through http_client.fetch(), which is the only call the wear guard can see:\n  " + "\n  ".join(offenders)


def test_every_justified_exemption_still_rests_on_every_field_being_rejected(repo_root: Path) -> None:
    # An allowlist entry is only as good as its reason: stop asserting a field comes back
    # "Invalid" and the body persists after all. Checked per entry and per FIELD rather than
    # against a fixed count, so a second entry cannot inherit the first one's verification.
    path = repo_root / "tests_hardware" / "bench" / "test_network_resilience.py"
    source = path.read_text()
    persisting = _persisting_put_functions(path, _dispatch_only_fields(repo_root), _fetch_shape(repo_root))
    for name in _JUSTIFIED_UNMARKED:
        body = source.split(f"def {name}(", 1)
        assert len(body) == 2, f"{name} is gone - drop its _JUSTIFIED_UNMARKED entry with it"
        fn_text = body[1].split("\ndef ", 1)[0]
        needed = len(persisting.get(name, ()))
        # Two ways a PUT field provably writes nothing, and both have to count: rejected as
        # "Invalid", or sitting under a sensor key no driver registers, which _put_sensors()
        # drops silently. Counting only the first wrongly condemns a body that mixes them.
        proven = fn_text.count('== "Invalid"') + fn_text.count('not in body["result"]')
        assert needed, f"{name} no longer PUTs any persisting field - drop its _JUSTIFIED_UNMARKED entry, it is exempt from nothing"
        assert proven >= needed, f"{name} PUTs {needed} persisting field(s) but proves only {proven} of them are rejected or ignored - it may now persist, so the exemption no longer holds"


def test_the_set_of_persisting_helpers_is_exactly_the_triaged_one(repo_root: Path) -> None:
    # A helper's own callers carry the marker, which this file cannot verify by name resolution.
    # Pinning the set converts "a new untriaged helper" from silent into a failing test.
    dispatch_only = _dispatch_only_fields(repo_root)
    shape = _fetch_shape(repo_root)
    helpers = {
        name
        for path in _tests_hardware_modules(repo_root)
        for name in _persisting_put_functions(path, dispatch_only, shape)
        if not name.startswith("test_")
    }
    assert helpers == _KNOWN_PERSISTING_HELPERS, f"the set of non-test functions issuing a persisting PUT changed - triage each one and update _KNOWN_PERSISTING_HELPERS.\n  added: {sorted(helpers - _KNOWN_PERSISTING_HELPERS)}\n  gone: {sorted(_KNOWN_PERSISTING_HELPERS - helpers)}"


def test_the_derived_classes_still_hold_every_known_action_and_chip_field(repo_root: Path) -> None:
    # If the derivation silently returned nothing useful, every dispatch-only PUT would read as a
    # flash write and the guard above would fail noisily - but the reverse (a field wrongly counted
    # as dispatch-only) fails SILENTLY, which is the direction that actually spends wear.
    dispatch_only = _dispatch_only_fields(repo_root)
    assert {"ResetVOC", "Calibrate", "SystemCmd", "PauseTime", "LightCmdLED", "ResetErrors"} <= dispatch_only
    assert {"AmbPres", "ForceCalRef", "ContMeas"} <= _always_executed_fields(repo_root)
    for persisting in ("PresOvers", "Resolution", "BackupPeriod", "SSID", "NTPHost", "WarnCO2"):
        assert persisting not in dispatch_only, f"{persisting} is a real persisted config field and must never be treated as dispatch-only"


def test_a_synthetic_unmarked_writer_is_actually_caught(tmp_path: Path, repo_root: Path) -> None:
    # Proves the detector bites rather than merely agreeing with today's tree: the guard above passes
    # trivially if _persisting_put_functions() ever stops finding anything at all.
    module = tmp_path / "test_synthetic.py"
    module.write_text('def test_writes() -> None:\n    http_client.fetch(ip, 80, "PUT", "/sensors", {"BMP3XX": {"PresOvers": 4}}, timeout_s=10.0)\n')
    found = _persisting_put_functions(module, _dispatch_only_fields(repo_root), _fetch_shape(repo_root))
    assert found == {"test_writes": {"PresOvers"}}
    assert _marked_functions(module) == set(), "an unmarked writer must not look marked"


@pytest.mark.parametrize("body", ['{"SGP40": {"ResetVOC": True}}', '{"ResetErrors": True}', '{"SystemCmd": "reboot"}'])
def test_a_dispatch_only_put_is_not_flagged(tmp_path: Path, repo_root: Path, body: str) -> None:
    module = tmp_path / "test_dispatch.py"
    module.write_text(f'def test_dispatches() -> None:\n    http_client.fetch(ip, 80, "PUT", "/sensors", {body}, timeout_s=10.0)\n')
    assert _persisting_put_functions(module, _dispatch_only_fields(repo_root), _fetch_shape(repo_root)) == {}


def _registered_markers(repo_root: Path) -> set[str]:
    conftest = (repo_root / "tests_hardware" / "conftest.py").read_text()
    names = set(re.findall(r"""addinivalue_line\(\s*"markers",\s*["'](\w+)[(:]""", conftest))
    assert names, "tests_hardware/conftest.py no longer registers any markers - update this parse with it"
    return names


def _used_markers(repo_root: Path) -> dict[str, set[str]]:
    # Test function name -> the pytest.mark.* names it carries, across the whole tier.
    used: dict[str, set[str]] = {}
    for path in _tests_hardware_modules(repo_root):
        for fn in [n for n in ast.walk(ast.parse(path.read_text())) if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef)]:
            for dec in fn.decorator_list:
                for attr in [n for n in ast.walk(dec) if isinstance(n, ast.Attribute)]:
                    if isinstance(attr.value, ast.Attribute) and attr.value.attr == "mark":
                        used.setdefault(f"{path.relative_to(repo_root)}::{fn.name}", set()).add(attr.attr)
    return used


def test_no_test_carries_an_unregistered_marker(repo_root: Path) -> None:
    # --strict-markers is off, so an unregistered marker - a typo, or one left by a rename - is
    # silently inert: nothing matches it, the test is never deselected, and a routine run spends
    # the wear it was meant to gate. It emits a warning at most, and nothing reads those.
    registered = _registered_markers(repo_root)
    # parametrize/skipif/usefixtures are pytest's own built-ins, never registered by a project.
    builtin = {"parametrize", "skipif", "skip", "xfail", "usefixtures", "filterwarnings", "timeout"}
    offenders = {name: sorted(marks - registered - builtin) for name, marks in _used_markers(repo_root).items() if marks - registered - builtin}
    assert not offenders, f"unregistered (and therefore inert) markers: {offenders}"


def test_the_extra_write_marker_is_never_carried_alone(repo_root: Path) -> None:
    # The AND-gate's structural half: scd30_extra_write only NARROWS, and nothing makes it imply
    # the global gate, so a test carrying it alone would run unflagged and spend the SCD30's NVM.
    # The sibling test proves the flags compose; this proves the usage does.
    lone = [name for name, marks in _used_markers(repo_root).items() if "scd30_extra_write" in marks and "persistence_write" not in marks]
    assert not lone, f"scd30_extra_write must always be carried alongside persistence_write: {lone}"


# ---------------------------------------------------------------------------
# Which store each owned write lands in (owner, 2026-10-08: "it makes absolutely no sense globally enable
# persistence writes, as writing the scd30 for mqtt tests is nonsense, so scope it correctly"): every marker
# names its groups, and --allow-persistence-writes-to permits a run exactly those (tests_hardware/README.md).
# ---------------------------------------------------------------------------

_SCD30_FIXTURE = "scd30_continuous_measurement_triggered"  # tests_hardware/flash/conftest.py: one SCD30 NVM write


def _marker_groups(path: Path) -> "dict[str, list[ast.expr]]":
    # Test name -> the arguments of its persistence_write marker, for every marked test in the module.
    found: dict[str, list[ast.expr]] = {}
    for fn in [n for n in ast.walk(ast.parse(path.read_text())) if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef)]:
        for dec in fn.decorator_list:
            target = dec.func if isinstance(dec, ast.Call) else dec
            if isinstance(target, ast.Attribute) and target.attr == "persistence_write":
                found[fn.name] = list(dec.args) if isinstance(dec, ast.Call) else []
    return found


@cache
def _route_groups(repo_root: Path) -> "tuple[dict[tuple[str, str], frozenset[str]], dict[tuple[str, str], frozenset[str]]]":
    # (route, group key) -> that group's persisting field keys, and (route, field key) -> the groups the field
    # persists into, over every device. Dispatch and readonly fields persist nothing.
    by_group: dict[tuple[str, str], set[str]] = {}
    by_field: dict[tuple[str, str], set[str]] = {}
    for device in DEVICE_NAMES:
        for section in definitions_for_toml(device_toml(device), repo_root / "src")["sections"]:
            route = section.get("rest", {}).get("put")
            for group in section["groups"] if route is not None else []:
                for field in group.get("fields", []):
                    if field.get("kind") not in (None, "readonly") and not field.get("dispatch"):
                        by_group.setdefault((route, group["key"]), set()).add(field["key"])
                        by_field.setdefault((route, field["key"]), set()).add(f"{section['key']}/{group['key']}")
    return {k: frozenset(v) for k, v in by_group.items()}, {k: frozenset(v) for k, v in by_field.items()}


def _key_groups(route: str, key: str, value: ast.expr, repo_root: Path) -> "set[str]":
    # The groups one top-level body key persists into: a nested group's ({"BMP3XX": {...}}) when its literal
    # value names a persisting field or is no literal at all, else the field's own groups.
    by_group, by_field = _route_groups(repo_root)
    fields = by_group.get((route, key))
    if fields is not None and not isinstance(value, ast.Constant):
        written = not isinstance(value, ast.Dict) or bool(_leaf_keys(value) & fields)
        return {f"{section}/{key}" for section in _sections_of(route, repo_root)} if written else set()
    return set(by_field.get((route, key), frozenset()))


@cache
def _sections_of(route: str, repo_root: Path) -> "frozenset[str]":
    return frozenset(s["key"] for d in DEVICE_NAMES for s in definitions_for_toml(device_toml(d), repo_root / "src")["sections"] if s.get("rest", {}).get("put") == route)


def _written_groups(path: Path, shape: _FetchShape, repo_root: Path) -> "dict[str, set[str]]":
    # Function name -> the groups its own literal-route, literal-body PUTs persist into.
    found: dict[str, set[str]] = {}
    for fn_name, call in _fetch_calls(path):
        body = _put_body(call, shape)
        route = _argument(call, shape.path_at, "path")
        if not (isinstance(body, ast.Dict) and isinstance(route, ast.Constant) and isinstance(route.value, str)):
            continue
        for key, value in zip(body.keys, body.values, strict=True):
            if isinstance(key, ast.Constant) and isinstance(key.value, str):
                groups = _key_groups(route.value, key.value, value, repo_root)
                if groups:
                    found.setdefault(fn_name, set()).update(groups)
    return found


def test_every_marker_names_the_groups_it_writes(repo_root: Path) -> None:
    # A marker naming nothing runs only under the global flag, so a scoped run could never select it.
    vocabulary = persistence_groups()
    offenders = []
    for path in _tests_hardware_modules(repo_root):
        for name, args in _marker_groups(path).items():
            values = [a.value for a in args if isinstance(a, ast.Constant) and isinstance(a.value, str)]
            if not args or len(values) != len(args) or set(values) - vocabulary:
                offenders.append(f"{path.relative_to(repo_root)}::{name} {[ast.unparse(a) for a in args]}")
    assert not offenders, f"every persistence_write marker names its groups as string literals from {sorted(vocabulary)}:\n  " + "\n  ".join(offenders)


def test_a_marker_covers_every_group_its_own_puts_write(repo_root: Path) -> None:
    # The scoped permission is only as good as the names: a PUT into a group its marker omits would run
    # under a permission scoped to the others and spend a write nobody allowed.
    shape = _fetch_shape(repo_root)
    offenders = []
    for path in _tests_hardware_modules(repo_root):
        declared = {name: {a.value for a in args if isinstance(a, ast.Constant) and isinstance(a.value, str)} for name, args in _marker_groups(path).items()}
        for name, groups in _written_groups(path, shape, repo_root).items():
            if name in declared and groups - declared[name]:
                offenders.append(f"{path.relative_to(repo_root)}::{name} writes {sorted(groups - declared[name])} beyond {sorted(declared[name])}")
    assert not offenders, "\n  ".join(["these markers omit a group the test's own PUTs write:", *offenders])


def test_the_group_derivation_reads_a_real_marked_test(repo_root: Path) -> None:
    # Guards the scan itself: an AST or definitions change must not quietly turn the check above into none.
    path = repo_root / "tests_hardware" / "bench" / "test_mqtt_broker_faults.py"
    written = _written_groups(path, _fetch_shape(repo_root), repo_root)
    assert written.get("test_the_broker_is_found_by_the_bench_hosts_local_name") == {"networking/mqtt"}, written
    assert written.get("_enable_mqtt") == {"networking/mqtt"}, written


def test_every_test_spending_the_scd30_fixtures_write_names_sensors_scd30(repo_root: Path) -> None:
    # The fixture's NVM write is checked at run time against the same permission; this catches the omission statically.
    offenders = []
    for path in _tests_hardware_modules(repo_root):
        markers = _marker_groups(path)
        for fn in [n for n in ast.walk(ast.parse(path.read_text())) if isinstance(n, ast.FunctionDef) and n.name.startswith("test_")]:
            if _SCD30_FIXTURE in {a.arg for a in fn.args.args}:
                declared = {a.value for a in markers.get(fn.name, []) if isinstance(a, ast.Constant) and isinstance(a.value, str)}
                if "sensors/SCD30" not in declared:
                    offenders.append(f"{path.relative_to(repo_root)}::{fn.name}")
    assert not offenders, f'these tests take {_SCD30_FIXTURE} without persistence_write("sensors/SCD30"): {offenders}'


def test_the_extra_write_marker_rides_on_an_scd30_group(repo_root: Path) -> None:
    offenders = []
    for path in _tests_hardware_modules(repo_root):
        markers = _marker_groups(path)
        for name, marks in _used_markers(repo_root).items():
            if name.startswith(f"{path.relative_to(repo_root)}::") and "scd30_extra_write" in marks:
                declared = {a.value for a in markers.get(name.rsplit("::", 1)[1], []) if isinstance(a, ast.Constant) and isinstance(a.value, str)}
                if "sensors/SCD30" not in declared:
                    offenders.append(name)
    assert not offenders, f'scd30_extra_write needs persistence_write("sensors/SCD30") beside it: {offenders}'


@pytest.mark.parametrize(
    ("body", "groups"),
    [
        ('"/sensors", {"BMP3XX": {"PresOvers": 4}}', {"sensors/BMP3XX"}),
        ('"/sensors", {"SGP40": {"ResetVOC": True}}', set()),
        ('"/sensors", {"ISL29125": values}', {"sensors/ISL29125"}),
        ('"/networking", {"NTPHost": "a.b", "MQTTHost": "c.d"}', {"networking/ntp", "networking/mqtt"}),
    ],
)
def test_a_synthetic_put_is_read_into_its_groups(tmp_path: Path, repo_root: Path, body: str, groups: "set[str]") -> None:
    # Bites rather than agrees: a nested group, a dispatch-only one, a non-literal group value and two flat fields.
    module = tmp_path / "test_synthetic_groups.py"
    module.write_text(f'def test_writes() -> None:\n    http_client.fetch(ip, 80, "PUT", {body}, timeout_s=10.0)\n')
    assert _written_groups(module, _fetch_shape(repo_root), repo_root).get("test_writes", set()) == groups
