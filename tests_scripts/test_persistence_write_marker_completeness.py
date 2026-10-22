"""Completeness guard for tests_hardware/'s persistence gate: a test that PUTs a config-persisting
field but forgets @pytest.mark.persistence_write spends real RP2040 flash wear on every routine run,
silently. The sibling gating test proves the flag WORKS; this proves nothing escapes it unowned."""

# Blind spots, each named by its closing check: a variable PUT body (the unreadable-body triage), a wrapper hiding its
# method (the forwarding-wrapper check), a device script that writes (the device-script check) and a raw socket
# request (the raw-request check); an HTTP library besides fetch() is refused outright.

# The gate covers the write a test OWNS, not one it is merely reached through: a shared
# prerequisite stays unmarked, since gating it would deselect the tests it enables. Owner's rule,
# 2026-09-18; tests_hardware/README.md states it fully, and why the answer is not "spend zero".

import ast
import json
import operator
import re
from functools import cache
from pathlib import Path
from typing import TYPE_CHECKING, NamedTuple

import pytest
from _devices import DEVICE_NAMES, device_toml

from buildgen.definitions import definitions_for_toml

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

# Tests whose only persisting-looking PUT provably writes nothing, with the reason each is exempt.
# asy_config_manager.py's write_config() short-circuits on `if not changed` BEFORE staging anything, so
# a body whose every field is rejected (or unchanged) never reaches _flush_staged()'s json.dump().
_JUSTIFIED_UNMARKED = {
    "test_put_nonsense_field_values_are_marked_invalid_not_crashed": "every field in the body is rejected as Invalid, so write_config() returns on `not changed` without staging a flash write; the Hostname/SSID values exceed their byte bounds and are rejected",
    "test_the_largest_body_any_schema_can_produce_still_fits_under_the_cap": "its NTPHost, the largest string field, is 254 characters, ONE over _VAL_NTP_HOST's own 3..253 bound (RFC 1035), so the field is rejected as Invalid and write_config() returns on `not changed` - at exactly 253 it would be valid and this would be a real flash write",
    "test_concurrent_get_sensors_under_real_multi_client_load_survives_an_ntp_transient_outage_and_retry": "its NTPHost PUT carries the stored value and is asserted Unchanged: write_config() stages nothing",
    "test_ntp_recovers_by_its_own_retry_timer_after_a_transient_outage": "its NTPHost PUT carries the stored value and is asserted Unchanged: write_config() stages nothing",
    "test_invalid_credentials_rejected_without_triggering_reconnect": "its PW is one short of _VAL_PW's lower bound and is asserted Invalid: nothing persists",
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
    "_repair",  # restores the standard board state: tests_hardware/conftest.py's repair, only under --repair-standard-state
    "_repair_leftover",  # repairs an aborted run's leftover; runs only when one exists
    "scd30_write_worker",  # the SCD30 write arm, driven only from the persistence_write + scd30_extra_write test
    "_restore_hotspot_ssid",  # the role-reversal restore and the stranded-setup repair: the fixture's prerequisite write undone
}


@cache
def _parse(source: str) -> ast.Module:
    # One parse per distinct source: every check below walks the same tier's modules again. Keyed by the text, so a
    # bite that rewrites its file is parsed afresh; no caller changes a tree it gets.
    return ast.parse(source)


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
        definitions = json.loads(json.dumps(definitions_for_toml(device_toml(device), repo_root / "src")))
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


def _fetch_shape(repo_root: Path) -> _FetchShape:
    # Derived, never hardcoded: every detector here indexes fetch()'s positional arguments, so a
    # reordered or renamed parameter would silently make them read the wrong one - and the keyword
    # fallback did exactly that, looking for `body=` when the parameter has always been `json_body`.
    tree = ast.parse((repo_root / "tests_hardware" / "http_client.py").read_text(encoding="utf-8"))
    fn = next((n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "fetch"), None)
    assert fn is not None, "tests_hardware/http_client.py no longer defines fetch() - every detector in this file reads its call sites"
    names = [arg.arg for arg in fn.args.args]
    bodies = [n for n in names if "body" in n]
    assert len(bodies) == 1, f"fetch()'s body argument is no longer unambiguous ({bodies}) - update this derivation with it"
    assert "method" in names, f"fetch() no longer takes a `method` argument ({names}) - every detector here reads it to tell a PUT from a GET"
    return _FetchShape(names.index("method"), names.index(bodies[0]), bodies[0])


def _fetch_calls(path: Path) -> "Iterator[tuple[str, ast.Call]]":
    # (enclosing function name, call) for every call named `fetch` in the module.
    tree = _parse(path.read_text(encoding="utf-8"))
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


# SystemCmd is dispatch-only in general, but one command word deletes every config file, so a PUT
# carrying it writes the flash filesystem. Pinned by name with its reason (owner, 2026-09-30); the
# word must still be a real _SYSTEM_CMDS entry (checked below), never a literal that drifted.
_PERSISTING_COMMAND_WORDS = {"resetconfig": "deletes every config file (a flash-filesystem write the test owns)"}


@cache
def _system_cmds(repo_root: Path) -> frozenset[str]:
    # The _SYSTEM_CMDS tuple in src/asy_webserver_service.py, read by ast.
    tree = ast.parse((repo_root / "src" / "asy_webserver_service.py").read_text(encoding="utf-8"))
    value = next((n.value for n in ast.walk(tree) if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "_SYSTEM_CMDS" for t in n.targets)), None)
    assert value is not None, "src/asy_webserver_service.py no longer defines _SYSTEM_CMDS - update this reader"
    inner = value.args[0] if isinstance(value, ast.Call) and value.args else value  # const((...,)) or a bare tuple
    assert isinstance(inner, ast.Tuple), "_SYSTEM_CMDS is no longer a literal tuple - update this reader"
    return frozenset(e.value for e in inner.elts if isinstance(e, ast.Constant) and isinstance(e.value, str))


def _persisting_command(call: ast.Call, shape: _FetchShape, repo_root: Path) -> "str | None":
    # The persisting SystemCmd word a PUT body carries literally, or None - e.g. {"SystemCmd": "resetconfig"}.
    body = _put_body(call, shape)
    if not isinstance(body, ast.Dict):
        return None
    for key, value in zip(body.keys, body.values, strict=True):
        if isinstance(key, ast.Constant) and key.value == "SystemCmd" and isinstance(value, ast.Constant) and value.value in _PERSISTING_COMMAND_WORDS and value.value in _system_cmds(repo_root):
            return str(value.value)
    return None


def _persisting_put_functions(path: Path, dispatch_only: frozenset[str], shape: _FetchShape, repo_root: "Path | None" = None) -> dict[str, set[str]]:
    # Function name -> the persisting fields its own body PUTs, for every function that PUTs one.
    found: dict[str, set[str]] = {}
    for fn_name, call in _fetch_calls(path):
        # A body argument is required for this to be a write at all, so a bodyless GET - or a PUT
        # whose body arrived by keyword, which the old positional-only read missed - is handled here
        # once, by _put_body(), rather than by each detector guessing at argument positions.
        body = _put_body(call, shape)
        keys = _leaf_keys(body) - dispatch_only if body is not None else set()
        if repo_root is not None and (word := _persisting_command(call, shape, repo_root)) is not None:
            keys |= {f"SystemCmd={word}"}
        if keys:
            found[fn_name] = found.get(fn_name, set()) | keys
    return found


def _carries_mark(nodes: "list[ast.expr]") -> bool:
    return any("persistence_write" in ast.dump(node) for node in nodes)


def _pytestmark(body: "list[ast.stmt]") -> "list[ast.expr]":
    # The values of a module's or class body's `pytestmark = ...` assignments.
    return [n.value for n in body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "pytestmark" for t in n.targets)]


def _marked_tests(path: Path) -> set[str]:
    # Every function carrying persistence_write: its own decorator, its class's decorator or pytestmark, or the module's.
    tree = _parse(path.read_text(encoding="utf-8"))
    marked: set[str] = set()

    def visit(body: "list[ast.stmt]", *, inherited: bool) -> None:
        for node in body:
            if isinstance(node, ast.ClassDef):
                visit(node.body, inherited=inherited or _carries_mark(node.decorator_list) or _carries_mark(_pytestmark(node.body)))
            elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and (inherited or _carries_mark(node.decorator_list)):
                marked.add(node.name)

    visit(tree.body, inherited=_carries_mark(_pytestmark(tree.body)))
    return marked


def test_every_test_that_persists_a_config_field_carries_the_marker(repo_root: Path) -> None:
    # The wear guard itself. An unmarked writer is invisible - it passes, the suite goes green, and
    # the only evidence is flash endurance spent on a run that was never meant to spend any.
    dispatch_only = _dispatch_only_fields(repo_root)
    shape = _fetch_shape(repo_root)
    offenders = []
    for path in _tests_hardware_modules(repo_root):
        marked = _marked_tests(path)
        for name, keys in _persisting_put_functions(path, dispatch_only, shape, repo_root).items():
            if name.startswith("test_") and name not in marked and name not in _JUSTIFIED_UNMARKED:
                offenders.append(f"{path.relative_to(repo_root)}::{name} PUTs {sorted(keys)}")
    assert not offenders, "these tests persist config to the RP2040's flash without @pytest.mark.persistence_write:\n  " + "\n  ".join(offenders)


# Function -> why its non-literal PUT body is safe to be invisible to the detector above.
_JUSTIFIED_UNREADABLE_BODIES = {
    "test_put_oversized_body_is_rejected_with_413_over_the_normal_network": "the body is deliberately past max_content_length, so vendored ext/microdot.py rejects it with 413 before this project's route handler - and therefore ConfigManager - is ever reached",
    "_put_sized": "the body-cap helper: it pads an UNKNOWN sensor key, which PUT /sensors ignores silently, so no field of it ever reaches ConfigManager at any size - accepted or 413'd alike",
}


def test_every_unreadable_put_body_is_a_triaged_one(repo_root: Path) -> None:
    # Closes the detector's one blind spot by naming it: a PUT whose body is a variable yields no
    # keys, so the wear guard below passes on it no matter what it writes. Exactly one exists today
    # and it provably persists nothing; a second has to be triaged rather than silently inherit that.
    shape = _fetch_shape(repo_root)
    unreadable = {name for path in _tests_hardware_modules(repo_root) for name in _non_literal_put_bodies(path, shape)} - _KNOWN_PERSISTING_HELPERS
    assert unreadable == set(_JUSTIFIED_UNREADABLE_BODIES), f"a PUT body the marker guard cannot read changed - triage each one and update _JUSTIFIED_UNREADABLE_BODIES.\n  added: {sorted(unreadable - set(_JUSTIFIED_UNREADABLE_BODIES))}\n  gone: {sorted(set(_JUSTIFIED_UNREADABLE_BODIES) - unreadable)}"


# Wrapper -> why a fetch() call it makes may keep its method in a variable. An entry is only
# admissible when the wrapper presents http_client.fetch's own name and positional signature, so its
# CALLERS are what the detector reads; the test below re-derives that rather than trusting the entry.
_JUSTIFIED_FORWARDED_METHODS = {
    "tests_hardware/bench/test_bus_concurrency_under_api_load.py::fetch": "a ceiling-close retry wrapper that forwards every argument unchanged, named `fetch` with http_client.fetch's exact positional signature, so each call site is read directly and nothing is hidden behind it",
}


def _positional_parameters(path: Path, name: str) -> list[str]:
    # The positional parameter names of one top-level function, in order.
    tree = _parse(path.read_text(encoding="utf-8"))
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
    # A method kept in a variable, closed. Every detector above starts by reading fetch()'s method argument, so a
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
    # The same "prove it bites" treatment the detector itself gets: the wrapper shape that once hid two writers is
    # replayed verbatim, and must be both invisible to the PUT detector and loud in the check above.
    module = tmp_path / "test_wrapper.py"
    module.write_text(
        'def _put(ip, method, route, body):\n'
        '    return http_client.fetch(ip, 80, method, route, body, timeout_s=10.0)\n'
        '\n'
        'def test_writes() -> None:\n'
        '    _put(ip, "PUT", "/sensors", {"BMP3XX": {"PresOvers": 4}})\n', encoding="utf-8",
    )
    shape = _fetch_shape(repo_root)
    assert _persisting_put_functions(module, _dispatch_only_fields(repo_root), shape) == {}, "the PUT detector cannot see through a wrapper - if it ever can, this guard is redundant, not wrong"
    assert _forwarded_method_calls(module, shape) == ["_put"]


def test_a_put_body_passed_by_keyword_is_still_seen(tmp_path: Path, repo_root: Path) -> None:
    # The positional-only read missed this outright, and its keyword fallback looked for `body=`
    # while the parameter has always been `json_body` - so the one escape hatch could never fire.
    module = tmp_path / "test_keyword.py"
    module.write_text('def test_writes() -> None:\n    http_client.fetch(ip, 80, "PUT", "/sensors", json_body={"BMP3XX": {"PresOvers": 4}}, timeout_s=10.0)\n', encoding="utf-8")
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
        for node in ast.walk(_parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Import):
                offenders += [f"{path.relative_to(repo_root)}: import {a.name}" for a in node.names if a.name.split(".")[0] in _HTTP_LIBRARIES]
            elif isinstance(node, ast.ImportFrom) and (node.module or "").split(".")[0] in _HTTP_LIBRARIES:
                offenders.append(f"{path.relative_to(repo_root)}: from {node.module} import ...")
    assert not offenders, "these modules can issue an HTTP request without going through http_client.fetch(), which is the only call the wear guard can see:\n  " + "\n  ".join(offenders)


def test_every_justified_exemption_still_rests_on_every_field_being_rejected(repo_root: Path) -> None:
    # An allowlist entry is only as good as its reason: stop asserting a field comes back
    # "Invalid" and the body persists after all. Checked per entry and per FIELD rather than
    # against a fixed count, so a second entry cannot inherit the first one's verification.
    always_executed = _always_executed_fields(repo_root)
    for name in _JUSTIFIED_UNMARKED:
        homes = [path for path in _tests_hardware_modules(repo_root) if f"def {name}(" in path.read_text(encoding="utf-8")]
        assert len(homes) == 1, f"{name} is gone (or defined twice: {homes}) - drop its _JUSTIFIED_UNMARKED entry with it"
        fn_text = homes[0].read_text(encoding="utf-8").split(f"def {name}(", 1)[1].split("\ndef ", 1)[0]
        fields = _persisting_put_functions(homes[0], _dispatch_only_fields(repo_root), _fetch_shape(repo_root)).get(name, set())
        needed = len(fields)
        # Three ways a PUT field provably writes nothing: rejected "Invalid", "Unchanged" (a stored field only - an
        # always-executed one writes the chip every time), or under a key no driver registers, dropped silently.
        unchanged = fn_text.count('== "Unchanged"') if not fields & always_executed else 0
        proven = fn_text.count('== "Invalid"') + unchanged + fn_text.count('not in body["result"]')
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
        for name in [*_persisting_put_functions(path, dispatch_only, shape, repo_root), *_non_literal_put_bodies(path, shape)]
        if not name.startswith("test_") and name not in _JUSTIFIED_UNREADABLE_BODIES
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
    # Every pinned persisting-command word is still a real _SYSTEM_CMDS entry; resetconfig is one.
    assert set(_PERSISTING_COMMAND_WORDS) <= _system_cmds(repo_root), f"a pinned persisting command is not in _SYSTEM_CMDS: {set(_PERSISTING_COMMAND_WORDS) - _system_cmds(repo_root)}"
    assert "resetconfig" in _PERSISTING_COMMAND_WORDS, "resetconfig deletes every config file - it must count as a persisting write (owner, 2026-09-30)"


def test_a_synthetic_unmarked_writer_is_actually_caught(tmp_path: Path, repo_root: Path) -> None:
    # Proves the detector bites rather than merely agreeing with today's tree: the guard above passes
    # trivially if _persisting_put_functions() ever stops finding anything at all.
    module = tmp_path / "test_synthetic.py"
    module.write_text('def test_writes() -> None:\n    http_client.fetch(ip, 80, "PUT", "/sensors", {"BMP3XX": {"PresOvers": 4}}, timeout_s=10.0)\n', encoding="utf-8")
    found = _persisting_put_functions(module, _dispatch_only_fields(repo_root), _fetch_shape(repo_root))
    assert found == {"test_writes": {"PresOvers"}}
    assert _marked_tests(module) == set(), "an unmarked writer must not look marked"


@pytest.mark.parametrize("body", ['{"SGP40": {"ResetVOC": True}}', '{"ResetErrors": True}', '{"SystemCmd": "reboot"}', '{"SystemCmd": "bootloader"}', '{"SystemCmd": "erasefram"}'])
def test_a_dispatch_only_put_is_not_flagged(tmp_path: Path, repo_root: Path, body: str) -> None:
    # reboot/bootloader write nothing of their own; erasefram is FRAM, outside the wear gate.
    module = tmp_path / "test_dispatch.py"
    module.write_text(f'def test_dispatches() -> None:\n    http_client.fetch(ip, 80, "PUT", "/sensors", {body}, timeout_s=10.0)\n', encoding="utf-8")
    assert _persisting_put_functions(module, _dispatch_only_fields(repo_root), _fetch_shape(repo_root), repo_root) == {}


def test_a_resetconfig_command_is_a_persisting_write(tmp_path: Path, repo_root: Path) -> None:
    # resetconfig deletes every config file, so an unmarked test sending it spends a flash cycle.
    module = tmp_path / "test_reset.py"
    module.write_text('def test_resets() -> None:\n    http_client.fetch(ip, 80, "PUT", "/status", {"SystemCmd": "resetconfig"}, timeout_s=10.0)\n', encoding="utf-8")
    found = _persisting_put_functions(module, _dispatch_only_fields(repo_root), _fetch_shape(repo_root), repo_root)
    assert found == {"test_resets": {"SystemCmd=resetconfig"}}, found
    assert _marked_tests(module) == set(), "an unmarked resetconfig writer must not look marked"


# Device scripts that persist, run as a shared prerequisite rather than a write a test owns, each with its reason.
_SERVING_REASON = (
    "boots main() over the production config, which carries the WiFi credentials; its only possible writes are the ones a "
    "production boot makes anyway: a genuinely absent file's first write and a malformed file's repair"
)
_PREREQUISITE_DEVICE_SCRIPTS = {
    "scd30_start_continuous_measurement.py": "the flash tier's SCD30 prerequisite: sent only when no measurement arrives within three intervals, at most once per session",
    "system_debug_level_set_standard.py": "restores the standard board state: the DebugLevel repair, only under --repair-standard-state",
    "serving_at_default_gc.py": _SERVING_REASON,
    "heap_under_connection_ceiling.py": _SERVING_REASON,
    "uart_link_echo_under_serving_load.py": _SERVING_REASON,
    "loop_lag_under_combined_load.py": _SERVING_REASON,
}
# Persisting scripts a manual step runs: the operator confirms the stated writes before the run.
_MANUAL_PERSISTING_STEPS = {
    "config_files_restore.py": "rewrites the config files saved before the resetconfig power cut, once: one flash write per file",
    "scd30_argument_reaction.py": "STATE interval_write_loop: up to 21 SCD30 NVM writes, stated and confirmed by the operator before the run",
}
_CONFIG_WRITERS = ("write_config", "flush_pending", "delete_file")
_SCD30_NVM_SETTERS = ("set_altitude", "set_ambient_pressure", "set_forced_recalibration_reference", "set_measurement_interval", "set_self_calibration_enabled", "set_temperature_offset")
_SCD30_CONFIG_COMMANDS = ("_CMD_CONTINUOUS_MEASUREMENT", "_CMD_SET_MEASUREMENT_INTERVAL", "_CMD_AUTOMATIC_SELF_CALIBRATION", "_CMD_SET_FORCED_RECALIBRATION_FACTOR", "_CMD_SET_TEMPERATURE_OFFSET", "_CMD_SET_ALTITUDE_COMPENSATION")
_SCRATCH_CFG_PATH = "_SCRATCH_CFG_PATH"


@cache
def _scd30_config_codes(repo_root: Path) -> frozenset[int]:
    # The SCD30 commands that write its NVM, read from the driver's own const() lines.
    source = (repo_root / "src" / "asy_scd30_driver.py").read_text(encoding="utf-8")
    codes = {name: re.search(rf"^{name} = const\((0x[0-9A-Fa-f]+)\)", source, re.MULTILINE) for name in _SCD30_CONFIG_COMMANDS}
    missing = sorted(name for name, match in codes.items() if match is None)
    assert not missing, f"src/asy_scd30_driver.py no longer declares {missing} - update this reader"
    return frozenset(int(match.group(1), 16) for match in codes.values() if match is not None)


def _call_name(call: ast.Call) -> str:
    return call.func.attr if isinstance(call.func, ast.Attribute) else getattr(call.func, "id", "")


def _write_mode(call: ast.Call) -> bool:
    mode = _argument(call, 1, "mode")
    return isinstance(mode, ast.Constant) and isinstance(mode.value, str) and any(c in mode.value for c in "wax+")


_INT_OPS: "dict[type[ast.operator], Callable[[int, int], int]]" = {ast.RShift: operator.rshift, ast.LShift: operator.lshift, ast.BitAnd: operator.and_, ast.BitOr: operator.or_}


def _module_ints(tree: ast.Module) -> "dict[str, int]":
    # The script's module-level int constants, plain and tuple-unpacked (CMD_A, CMD_B = 0x4600, 0x0202).
    found: dict[str, int] = {}
    for node in [n for n in tree.body if isinstance(n, ast.Assign) and len(n.targets) == 1]:
        target, value = node.targets[0], node.value
        pairs = list(zip(target.elts, value.elts, strict=False)) if isinstance(target, ast.Tuple) and isinstance(value, ast.Tuple) else [(target, value)]
        found.update({t.id: v.value for t, v in pairs if isinstance(t, ast.Name) and isinstance(v, ast.Constant) and isinstance(v.value, int)})
    return found


def _int_of(node: ast.expr, ints: "dict[str, int]") -> "int | None":
    # A byte expression the scan can fold: an int literal, a module constant, and >> << & | over them.
    if isinstance(node, ast.Constant) and isinstance(node.value, int):
        return node.value
    if isinstance(node, ast.Name):
        return ints.get(node.id)
    if isinstance(node, ast.BinOp) and type(node.op) in _INT_OPS:
        left, right = _int_of(node.left, ints), _int_of(node.right, ints)
        return None if left is None or right is None else _INT_OPS[type(node.op)](left, right)
    return None


def _sends_scd30_config(call: ast.Call, codes: frozenset[int], ints: "dict[str, int] | None" = None) -> bool:
    # A raw write of a configuration command and its argument: more than the two command bytes a register read sends.
    for node in [n for arg in call.args for n in ast.walk(arg)]:
        if isinstance(node, ast.Constant) and isinstance(node.value, bytes) and len(node.value) > 2 and int.from_bytes(node.value[:2], "big") in codes:
            return True
        if isinstance(node, ast.Tuple | ast.List) and len(node.elts) > 2:
            hi, lo = (_int_of(e, ints or {}) for e in node.elts[:2])
            if hi is not None and lo is not None and (hi << 8 | lo) in codes:
                return True
    return False


def _persisting_device_calls(source: str, codes: frozenset[int], ints: "dict[str, int] | None" = None) -> "list[str]":
    # What a device script's own source does that writes flash or the SCD30's NVM (includes carry no such write); a
    # fragment of a script takes the script's module constants as `ints`.
    tree = _parse(source)
    local = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef)}
    ints = _module_ints(tree) if ints is None else ints
    found: list[str] = []
    for call in [n for n in ast.walk(tree) if isinstance(n, ast.Call)]:
        name = _call_name(call)
        scratch = any(kw.arg == "cfg_path" and isinstance(kw.value, ast.Name) and kw.value.id == _SCRATCH_CFG_PATH for kw in call.keywords)
        if name in _CONFIG_WRITERS or name in _SCD30_NVM_SETTERS:
            found.append(f"{name}()")
        elif name == "open" and _write_mode(call):
            found.append("open() in a write mode")
        elif name in {"writeto", "writeto_mem"} and _sends_scd30_config(call, codes, ints):
            found.append(f"{name}() of an SCD30 configuration command")
        elif name in {"build_system", "main"} and not (isinstance(call.func, ast.Name) and name in local) and not scratch:
            found.append(f"{name}() over the production config")
    return found


def _persisting_scripts(scripts_dir: Path, codes: frozenset[int]) -> "dict[str, list[str]]":
    return {path.name: calls for path in sorted(scripts_dir.glob("*.py")) if (calls := _persisting_device_calls(path.read_text(encoding="utf-8"), codes))}


def _outermost_functions(tree: ast.Module) -> "list[ast.FunctionDef | ast.AsyncFunctionDef]":
    # Module-level functions and class methods: a nested def belongs to the function around it.
    found: list[ast.FunctionDef | ast.AsyncFunctionDef] = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            found.append(node)
        elif isinstance(node, ast.ClassDef):
            found += [n for n in node.body if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef)]
    return found


def _names_scripts(node: ast.AST, scripts: "set[str]") -> "set[str]":
    return {script for n in ast.walk(node) if isinstance(n, ast.Constant) and isinstance(n.value, str) for script in scripts if n.value == script or n.value.endswith("/" + script)}


_RUN_CALLS = frozenset({"run_isolated", "run_isolated_expect_reset"})


def _running_functions(tree: ast.Module) -> "set[str]":
    # The module's functions that run a script: a run call of their own, or a call to one that does (by name).
    fns = {fn.name: fn for fn in _outermost_functions(tree)}
    running: set[str] = set()
    while True:
        more = {name for name, fn in fns.items() if name not in running and any(isinstance(n, ast.Call) and _call_name(n) in _RUN_CALLS | running for n in ast.walk(fn))}
        if not more:
            return running
        running |= more


def _script_runners(modules: "list[Path]", scripts: "set[str]") -> "dict[str, list[tuple[Path, ast.FunctionDef | ast.AsyncFunctionDef, int]]]":
    # Script -> (module, outermost function, first line naming it) for every function that names it and runs a script:
    # by a "<script>.py" string, or a module-level constant of any host module holding one (scd30_prerequisite.START_SCRIPT).
    trees = {path: _parse(path.read_text(encoding="utf-8")) for path in modules}
    own: dict[Path, dict[str, set[str]]] = {path: {} for path in trees}
    for path, tree in trees.items():
        for node in tree.body:
            if isinstance(node, ast.Assign | ast.AnnAssign) and (named := _names_scripts(node, scripts)):
                for target in node.targets if isinstance(node, ast.Assign) else [node.target]:
                    if isinstance(target, ast.Name):
                        own[path].setdefault(target.id, set()).update(named)
    anywhere = {name: named for constants in own.values() for name, named in constants.items()}
    runners: dict[str, list[tuple[Path, ast.FunctionDef | ast.AsyncFunctionDef, int]]] = {}
    for path, tree in trees.items():
        running = _running_functions(tree)
        for fn in [fn for fn in _outermost_functions(tree) if fn.name in running]:
            lines: dict[str, int] = {}
            for ref in ast.walk(fn):
                if isinstance(ref, ast.Constant):
                    named = _names_scripts(ref, scripts)
                elif isinstance(ref, ast.Name):
                    named = own[path].get(ref.id, set())
                elif isinstance(ref, ast.Attribute):
                    named = anywhere.get(ref.attr, set())
                else:
                    continue
                for script in named:
                    lines[script] = min(lines.get(script, ref.lineno), ref.lineno)
            for script, line in lines.items():
                runners.setdefault(script, []).append((path, fn, line))
    return runners


def _state_test(node: ast.expr) -> "str | None":
    # The constant of a `state == "<x>"` test, the dispatch a STATE-selected device script's _main() runs.
    ok = isinstance(node, ast.Compare) and isinstance(node.left, ast.Name) and node.left.id == "state" and len(node.ops) == 1
    value = node.comparators[0] if ok and isinstance(node, ast.Compare) and isinstance(node.ops[0], ast.Eq) else None
    return value.value if isinstance(value, ast.Constant) and isinstance(value.value, str) else None


def _writing_states(source: str, codes: frozenset[int]) -> "tuple[frozenset[str], frozenset[str], bool] | None":
    # (every STATE _main() dispatches on, those whose branch reaches a persisting call, whether its default branch does);
    # None when a write is reachable outside a plain `state == "<x>"` chain - then every run persists.
    tree = _parse(source)
    fns = {fn.name: fn for fn in _outermost_functions(tree)}
    ints = _module_ints(tree)
    writers = {name for name, fn in fns.items() if _persisting_device_calls(ast.unparse(fn), codes, ints)}
    while more := {name for name, fn in fns.items() if name not in writers and any(isinstance(n, ast.Call) and _call_name(n) in writers for n in ast.walk(fn))}:
        writers |= more
    main = fns.get("_main")
    if main is None:
        return None

    def writes(body: "list[ast.stmt]") -> bool:
        return any(isinstance(n, ast.Call) and (_call_name(n) in writers or bool(_persisting_device_calls(ast.unparse(n), codes, ints))) for stmt in body for n in ast.walk(stmt))

    every: set[str] = set()
    writing: set[str] = set()
    default = False
    for stmt in main.body:
        if not (isinstance(stmt, ast.If) and _state_test(stmt.test) is not None):
            if writes([stmt]):
                return None
            continue
        node = stmt
        while True:
            value = _state_test(node.test)
            if value is None:
                return None
            every.add(value)
            if writes(node.body):
                writing.add(value)
            if len(node.orelse) == 1 and isinstance(node.orelse[0], ast.If):
                node = node.orelse[0]
                continue
            default = default or writes(node.orelse)
            break
    return frozenset(every), frozenset(writing), default


def _run_persists(fn: "ast.FunctionDef | ast.AsyncFunctionDef", dispatch: "tuple[frozenset[str], frozenset[str], bool] | None") -> bool:
    # Whether a runner's run of a STATE-dispatched script can write: its STATE/state keyword constants decide, a run
    # with none or an undispatched value takes the default branch, and a STATE the scan cannot read is taken to write.
    if dispatch is None:
        return True
    every, writing, default = dispatch
    passed = [kw.value for n in ast.walk(fn) if isinstance(n, ast.Call) for kw in n.keywords if kw.arg in {"STATE", "state"}]
    values = [v.value for v in passed if isinstance(v, ast.Constant) and isinstance(v.value, str)]
    if len(values) < len(passed):
        return True
    return default if not values else any(value in writing or (value not in every and default) for value in values)


def _confirmed_before(fn: "ast.FunctionDef | ast.AsyncFunctionDef", line: int) -> bool:
    return any(isinstance(n, ast.Call) and _call_name(n) == "confirm" and n.lineno < line for n in ast.walk(fn))


def _unowned_device_writes(modules: "list[Path]", scripts_dir: Path, codes: frozenset[int]) -> "list[str]":
    persisting = _persisting_scripts(scripts_dir, codes)
    runners = _script_runners(modules, set(persisting))
    dispatch = {script: _writing_states((scripts_dir / script).read_text(encoding="utf-8"), codes) for script in persisting}
    offenders: list[str] = []
    for script, calls in persisting.items():
        if not runners.get(script):
            offenders.append(f"{script} ({', '.join(calls)}) has no runner in tests_hardware/")
        for path, fn, line in runners.get(script, []):
            where = f"{path.parent.name}/{path.name}::{fn.name}"
            if path.parent.name == "manual":
                if script not in _MANUAL_PERSISTING_STEPS or not _confirmed_before(fn, line):
                    offenders.append(f"{where} runs {script} ({', '.join(calls)}) without a listed, confirm()-first manual step")
            elif script not in _PREREQUISITE_DEVICE_SCRIPTS and fn.name not in _marked_tests(path) and fn.name not in _KNOWN_PERSISTING_HELPERS and _run_persists(fn, dispatch[script]):
                offenders.append(f"{where} runs {script} ({', '.join(calls)}) unmarked")
    return offenders


def test_every_device_script_that_persists_is_run_only_by_a_gated_test(repo_root: Path) -> None:
    assert _persisting_scripts(repo_root / "tests_hardware" / "device_scripts", _scd30_config_codes(repo_root)), "no device script persists anything - the scan reads nothing"
    offenders = _unowned_device_writes(_tests_hardware_modules(repo_root), repo_root / "tests_hardware" / "device_scripts", _scd30_config_codes(repo_root))
    assert not offenders, "these device scripts write flash or the SCD30's NVM outside the gate:\n  " + "\n  ".join(offenders)


def test_the_listed_device_scripts_and_persisting_calls_are_current(repo_root: Path) -> None:
    # Each listed script still persists (else its row is stale), and each pinned call is still an async def in src/.
    persisting = _persisting_scripts(repo_root / "tests_hardware" / "device_scripts", _scd30_config_codes(repo_root))
    stale = sorted((set(_PREREQUISITE_DEVICE_SCRIPTS) | set(_MANUAL_PERSISTING_STEPS)) - set(persisting))
    assert not stale, f"listed as persisting but no longer writing anything: {stale}"
    defined = {n.name for f in ("asy_config_manager.py", "asy_scd30_driver.py") for n in ast.walk(ast.parse((repo_root / "src" / f).read_text(encoding="utf-8"))) if isinstance(n, ast.AsyncFunctionDef)}
    assert set(_CONFIG_WRITERS + _SCD30_NVM_SETTERS) <= defined, f"no longer an async def in src/: {sorted(set(_CONFIG_WRITERS + _SCD30_NVM_SETTERS) - defined)}"


_BITE_SCRIPTS = {
    "writes_config.py": "async def _main():\n    await mgr.write_config({'DebugLevel': 1})\n",
    "opens_for_write.py": "with open('x.cfg', 'w') as f:\n    f.write('1')\n",
    "raw_scd30_write.py": "i2c.writeto(0x61, bytes([0x54, 0x03, 0x01, 0x90, 0x4C]))\n",
    "named_scd30_write.py": "CMD_A, CMD_B = 0x4600, 0x0202\ni2c.writeto(0x61, bytes([CMD_A >> 8, CMD_A & 0xFF, 0x00, 0x02, 0xE3]))\n",
    "named_register_read.py": "CMD_B = 0x0202\ni2c.writeto(0x61, bytes([CMD_B >> 8, CMD_B & 0xFF]))\n",
    "builds_production.py": "async def _main():\n    await sensortask.build_system(watchdog=wdt)\n",
    "builds_scratch.py": "async def _main():\n    await sensortask.build_system(watchdog=wdt, cfg_path=_SCRATCH_CFG_PATH)\n",
    "reads_register.py": "i2c.writeto(0x61, bytes([0x54, 0x03]))\n",
}


def test_the_device_script_check_bites(tmp_path: Path, repo_root: Path) -> None:
    scripts, host = tmp_path / "device_scripts", tmp_path / "flash"
    scripts.mkdir()
    host.mkdir()
    for name, source in _BITE_SCRIPTS.items():
        (scripts / name).write_text(source, encoding="utf-8")
    runs = "\n".join(f"    board.run_isolated(DEVICE_SCRIPTS / {name!r})" for name in _BITE_SCRIPTS if name != "opens_for_write.py")
    (host / "test_bite.py").write_text(f"import pytest\n\n\ndef test_unmarked(board):\n{runs}\n\n\n@pytest.mark.persistence_write\ndef test_marked(board):\n    board.run_isolated(DEVICE_SCRIPTS / 'writes_config.py')\n", encoding="utf-8")
    offenders = _unowned_device_writes([host / "test_bite.py"], scripts, _scd30_config_codes(repo_root))
    flagged = sorted({line.split(" runs ", 1)[1].split(" ", 1)[0] for line in offenders if " runs " in line})
    assert flagged == ["builds_production.py", "named_scd30_write.py", "raw_scd30_write.py", "writes_config.py"], offenders
    assert any(line.startswith("opens_for_write.py") and "no runner" in line for line in offenders), offenders


_STATED = (
    "async def _write():\n    await mgr.write_config({'V': 1})\n\n\n"
    "async def _main():\n    state = BENCH.get('STATE', 'r')\n    if state == 'w':\n        await _write()\n    elif state == 'r':\n        pass\n"
)


def test_a_state_dispatched_script_gates_only_its_writing_states(tmp_path: Path, repo_root: Path) -> None:
    scripts, host = tmp_path / "device_scripts", tmp_path / "flash"
    scripts.mkdir()
    host.mkdir()
    (scripts / "stated.py").write_text(_STATED, encoding="utf-8")
    (scripts / "default_writes.py").write_text(_STATED + "    else:\n        await _write()\n", encoding="utf-8")
    runs = {"read": "'stated.py', STATE='r'", "default": "'stated.py'", "write": "'stated.py', STATE='w'", "unread": "'stated.py', STATE=s", "other": "'default_writes.py', STATE='x'"}
    (host / "test_bite.py").write_text("\n\n".join(f"def test_{name}(board, s):\n    board.run_isolated(DEVICE_SCRIPTS / {args})\n" for name, args in runs.items()), encoding="utf-8")
    offenders = _unowned_device_writes([host / "test_bite.py"], scripts, _scd30_config_codes(repo_root))
    assert sorted(line.split("::", 1)[1].split(" ", 1)[0] for line in offenders) == ["test_other", "test_unread", "test_write"], offenders


def test_a_manual_step_needs_its_listing_and_a_confirm_first(tmp_path: Path, repo_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    scripts, manual = tmp_path / "device_scripts", tmp_path / "manual"
    scripts.mkdir()
    manual.mkdir()
    (scripts / "writes_config.py").write_text(_BITE_SCRIPTS["writes_config.py"], encoding="utf-8")
    step = "def test_step(board):\n    {first}\n    {second}\n"
    run, ask = "board.run_isolated(DEVICE_SCRIPTS / 'writes_config.py')", "confirm('writes the config file once')"
    codes = _scd30_config_codes(repo_root)
    (manual / "manual_step.py").write_text(step.format(first=ask, second=run), encoding="utf-8")
    assert _unowned_device_writes([manual / "manual_step.py"], scripts, codes), "an unlisted manual step must be flagged"
    monkeypatch.setitem(_MANUAL_PERSISTING_STEPS, "writes_config.py", "a stated write")
    assert _unowned_device_writes([manual / "manual_step.py"], scripts, codes) == []
    (manual / "manual_step.py").write_text(step.format(first=run, second=ask), encoding="utf-8")
    assert _unowned_device_writes([manual / "manual_step.py"], scripts, codes), "a confirm() after the run must be flagged"


# Tests whose raw socket request (a request fetch() cannot form) provably persists nothing, with the reason.
_JUSTIFIED_RAW_REQUESTS = {
    "test_put_malformed_raw_request_is_rejected_cleanly_over_the_normal_network": "its body is not JSON, so the handler answers an ERR envelope and stages nothing",
    "test_an_oversized_body_is_refused_before_it_is_read": "its declared body is never sent: refused unread (413) or reclaimed at the per-call timeout, no handler runs",
}


def _raw_write_requests(path: Path) -> "set[str]":
    # Outermost functions that send a raw PUT or POST request line over a socket.
    found: set[str] = set()
    for fn in _outermost_functions(_parse(path.read_text(encoding="utf-8"))):
        texts = [n.value for n in ast.walk(fn) if isinstance(n, ast.Constant) and isinstance(n.value, str | bytes)]
        sends = any(isinstance(n, ast.Call) and _call_name(n) in {"sendall", "send"} for n in ast.walk(fn))
        if sends and any((t if isinstance(t, str) else t.decode("latin-1")).startswith(("PUT ", "POST ")) for t in texts):
            found.add(fn.name)
    return found


def test_no_raw_socket_request_persists(repo_root: Path) -> None:
    raw = {name: path for path in _tests_hardware_modules(repo_root) for name in _raw_write_requests(path)}
    stale = sorted(set(_JUSTIFIED_RAW_REQUESTS) - set(raw))
    assert not stale, f"no longer a raw write request - drop its _JUSTIFIED_RAW_REQUESTS entry: {stale}"
    unowned = sorted(name for name, path in raw.items() if name not in _JUSTIFIED_RAW_REQUESTS and name not in _marked_tests(path))
    assert not unowned, f"a raw socket PUT/POST the fetch() detector cannot read, neither marked nor justified: {unowned}"


def test_the_raw_request_check_and_class_marks_bite(tmp_path: Path) -> None:
    module = tmp_path / "test_raw.py"
    module.write_text(
        'import pytest\n\npytestmark = pytest.mark.persistence_write\n\n\ndef test_raw(sock):\n    sock.sendall(f"PUT /sensors HTTP/1.1\\r\\n".encode())\n\n\n'
        "class TestGroup:\n    def test_in_class(self):\n        pass\n", encoding="utf-8",
    )
    assert _raw_write_requests(module) == {"test_raw"}
    assert _marked_tests(module) == {"test_raw", "test_in_class"}, "a module pytestmark marks every test in it"
    module.write_text("import pytest\n\n\n@pytest.mark.persistence_write\nclass TestGroup:\n    def test_a(self):\n        pass\n\n\ndef test_b():\n    pass\n", encoding="utf-8")
    assert _marked_tests(module) == {"test_a"}


def _marker_table(repo_root: Path) -> dict[str, str]:
    # tests_hardware/markers.py's MARKERS literal, read without importing it: name -> help text.
    tree = ast.parse((repo_root / "tests_hardware" / "markers.py").read_text(encoding="utf-8"))
    value = next((n.value for n in tree.body if isinstance(n, ast.AnnAssign | ast.Assign) and "MARKERS" in ast.dump(n.target if isinstance(n, ast.AnnAssign) else n.targets[0])), None)
    assert value is not None, "tests_hardware/markers.py no longer assigns MARKERS - update this parse with it"
    table = ast.literal_eval(value)
    assert table, "tests_hardware/markers.py registers no marker"
    return dict(table)


def _registered_markers(repo_root: Path) -> set[str]:
    return set(_marker_table(repo_root))


def _conftest_options(repo_root: Path) -> list[str]:
    # Every option flag tests_hardware/conftest.py registers, in order.
    tree = ast.parse((repo_root / "tests_hardware" / "conftest.py").read_text(encoding="utf-8"))
    calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "addoption"]
    return [str(c.args[0].value) for c in calls if c.args and isinstance(c.args[0], ast.Constant)]


def _used_markers(repo_root: Path) -> dict[str, set[str]]:
    # Test function name -> the pytest.mark.* names it carries, across the whole tier.
    used: dict[str, set[str]] = {}
    for path in _tests_hardware_modules(repo_root):
        for fn in [n for n in ast.walk(_parse(path.read_text(encoding="utf-8"))) if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef)]:
            for dec in fn.decorator_list:
                for attr in [n for n in ast.walk(dec) if isinstance(n, ast.Attribute)]:
                    if isinstance(attr.value, ast.Attribute) and attr.value.attr == "mark":
                        used.setdefault(f"{path.relative_to(repo_root)}::{fn.name}", set()).add(attr.attr)
    return used


def test_no_test_carries_an_unregistered_marker(repo_root: Path) -> None:
    # --strict-markers is on (pyproject addopts), so an unregistered marker fails collection; this
    # names it before a hardware run would.
    registered = _registered_markers(repo_root)
    builtin = {"parametrize", "skipif", "skip", "xfail", "usefixtures", "filterwarnings"}
    offenders = {name: sorted(marks - registered - builtin) for name, marks in _used_markers(repo_root).items() if marks - registered - builtin}
    assert not offenders, f"unregistered markers (a collection error under --strict-markers): {offenders}"


def test_every_gate_flag_names_a_registered_marker_of_its_own_name(repo_root: Path) -> None:
    # --allow-<marker> in kebab case, so a flag and the marker it selects can never drift apart;
    # --soak-duration is the one valued gate, named after its marker the same way.
    registered = _registered_markers(repo_root)
    options = _conftest_options(repo_root)
    gates = {flag: flag.removeprefix("--allow-").replace("-", "_") for flag in options if flag.startswith("--allow-")}
    assert gates, "tests_hardware/conftest.py registers no --allow-* option - the scan has stopped seeing them"
    gates["--soak-duration"] = "soak_duration"
    unmatched = {flag: marker for flag, marker in gates.items() if flag not in options or marker not in registered}
    assert not unmatched, f"gate options without a registered marker of the same name (or not registered as options): {unmatched}"


def test_tests_scripts_registers_the_same_marker_table(request: pytest.FixtureRequest, repo_root: Path) -> None:
    # tests_scripts loads bench modules carrying these marks, so its own session must know them too.
    known = {line.split(":", 1)[0] for line in request.config.getini("markers")}
    missing = sorted(set(_marker_table(repo_root)) - known)
    assert not missing, f"tests_scripts/conftest.py does not register these markers.py entries: {missing}"


def test_the_extra_write_marker_is_never_carried_alone(repo_root: Path) -> None:
    # The AND-gate's structural half: scd30_extra_write only NARROWS, and nothing makes it imply
    # the global gate, so a test carrying it alone would run unflagged and spend the SCD30's NVM.
    # The sibling test proves the flags compose; this proves the usage does.
    lone = [name for name, marks in _used_markers(repo_root).items() if "scd30_extra_write" in marks and "persistence_write" not in marks]
    assert not lone, f"scd30_extra_write must always be carried alongside persistence_write: {lone}"
