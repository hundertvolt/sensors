"""Completeness guard for tests_hardware/'s persistence gate: a test that PUTs a config-persisting
field but forgets @pytest.mark.persistence_write spends real RP2040 flash wear on every routine run,
silently. The sibling gating test proves the flag WORKS; this proves nothing escapes it unowned."""

# The gate covers the write a test OWNS, not one it is merely reached through: a shared
# prerequisite stays unmarked, since gating it would deselect the tests it enables. Owner's rule,
# 2026-09-18; tests_hardware/README.md states it fully, and why the answer is not "spend zero".

import ast
import re
from pathlib import Path

import pytest

# The four route-level dispatch-only fields (asy_webserver_service.py's own PUT handlers act on them
# and never hand them to ConfigManager) - the rest are derived from the real @web schema tags below,
# so a driver that stops declaring dispatch=true is caught rather than assumed.
_ROUTE_DISPATCH_FIELDS = frozenset({"SystemCmd", "PauseTime", "lightCmdLED", "ResetErrors"})

# Tests whose only persisting-looking PUT provably writes nothing, with the reason each is exempt.
# config_manager.py's write_config() short-circuits on `if not changed` BEFORE staging anything, so
# a body whose every field is rejected (or unchanged) never reaches _flush_staged()'s json.dump().
_JUSTIFIED_UNMARKED = {
    "test_put_nonsense_field_values_are_marked_invalid_not_crashed": "every field in the body is rejected as Invalid, so write_config() returns on `not changed` without staging a flash write",
    "test_the_largest_body_any_schema_can_produce_still_fits_under_the_cap": "its NTP_Host is 1025 characters, ONE over _VAL_NH's own 3..1024 bound, so the field is rejected as Invalid and write_config() returns on `not changed` - at exactly 1024 it would be valid and this would be a real flash write",
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
}


def _tests_hardware_modules(repo_root: Path) -> list[Path]:
    base = repo_root / "tests_hardware"
    # device_scripts/ is real MicroPython pushed to the board - it has no http_client and no markers.
    return sorted(p for p in base.rglob("*.py") if "device_scripts" not in p.parts)


def _dispatch_only_fields(repo_root: Path) -> frozenset[str]:
    """Every field a PUT can carry that persists nothing - route-level plus `dispatch=true` schema tags."""
    tagged = set()
    for src in sorted((repo_root / "src").glob("*.py")):
        tagged |= set(re.findall(r"^# @web (\w+) .*\bdispatch=true\b", src.read_text(), re.MULTILINE))
    assert tagged, "no `dispatch=true` @web tags found in src/ - the derivation broke, and every dispatch-only PUT would now look like a flash write"
    return frozenset(_ROUTE_DISPATCH_FIELDS | tagged)


def _leaf_keys(node: ast.expr) -> set[str]:
    """Every leaf key of a literal PUT body - {"SGP40": {"BackupPeriod": 1}} is BackupPeriod, not SGP40."""
    keys: set[str] = set()
    if isinstance(node, ast.Dict):
        for key, value in zip(node.keys, node.values, strict=True):
            if isinstance(value, ast.Dict):
                keys |= _leaf_keys(value)
            elif isinstance(key, ast.Constant) and isinstance(key.value, str):
                keys.add(key.value)
    return keys


def _non_literal_put_bodies(path: Path) -> list[str]:
    """Function names whose PUT body is not a literal dict, so _leaf_keys() cannot read it and the
    detector below never sees them as writers. Enumerated rather than left implicit, or a
    `payload = {...}` refactor would silently unmark a marked test. Exactly one today."""
    tree = ast.parse(path.read_text())
    offenders = []
    for fn in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef)]:
        for call in [n for n in ast.walk(fn) if isinstance(n, ast.Call)]:
            name = call.func.attr if isinstance(call.func, ast.Attribute) else getattr(call.func, "id", "")
            if name != "fetch":
                continue
            method = call.args[2] if len(call.args) >= 3 else None
            if not (isinstance(method, ast.Constant) and method.value == "PUT"):
                continue
            body = call.args[4] if len(call.args) >= 5 else next((kw.value for kw in call.keywords if kw.arg == "body"), None)
            if body is not None and not isinstance(body, ast.Dict):
                offenders.append(fn.name)
    return sorted(set(offenders))


def _persisting_put_functions(path: Path, dispatch_only: frozenset[str]) -> dict[str, set[str]]:
    """Function name -> the persisting fields its own body PUTs, for every function that PUTs one."""
    tree = ast.parse(path.read_text())
    found: dict[str, set[str]] = {}
    for fn in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef)]:
        keys: set[str] = set()
        for call in [n for n in ast.walk(fn) if isinstance(n, ast.Call)]:
            name = call.func.attr if isinstance(call.func, ast.Attribute) else getattr(call.func, "id", "")
            # http_client.fetch(host, port, method, route, body, ...) - a body argument is required
            # for this to be a write at all, so a 4-argument GET never reaches _leaf_keys().
            if name != "fetch" or len(call.args) < 5:
                continue
            method = call.args[2]
            if isinstance(method, ast.Constant) and method.value == "PUT":
                keys |= _leaf_keys(call.args[4]) - dispatch_only
        if keys:
            found[fn.name] = keys
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
    offenders = []
    for path in _tests_hardware_modules(repo_root):
        marked = _marked_functions(path)
        for name, keys in _persisting_put_functions(path, dispatch_only).items():
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
    unreadable = {name for path in _tests_hardware_modules(repo_root) for name in _non_literal_put_bodies(path)}
    assert unreadable == set(_JUSTIFIED_UNREADABLE_BODIES), f"a PUT body the marker guard cannot read changed - triage each one and update _JUSTIFIED_UNREADABLE_BODIES.\n  added: {sorted(unreadable - set(_JUSTIFIED_UNREADABLE_BODIES))}\n  gone: {sorted(set(_JUSTIFIED_UNREADABLE_BODIES) - unreadable)}"


def test_every_justified_exemption_still_rests_on_every_field_being_rejected(repo_root: Path) -> None:
    # An allowlist entry is only as good as its reason: stop asserting a field comes back
    # "Invalid" and the body persists after all. Checked per entry and per FIELD rather than
    # against a fixed count, so a second entry cannot inherit the first one's verification.
    path = repo_root / "tests_hardware" / "bench" / "test_network_resilience.py"
    source = path.read_text()
    persisting = _persisting_put_functions(path, _dispatch_only_fields(repo_root))
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
    helpers = {
        name
        for path in _tests_hardware_modules(repo_root)
        for name in _persisting_put_functions(path, dispatch_only)
        if not name.startswith("test_")
    }
    assert helpers == _KNOWN_PERSISTING_HELPERS, f"the set of non-test functions issuing a persisting PUT changed - triage each one and update _KNOWN_PERSISTING_HELPERS.\n  added: {sorted(helpers - _KNOWN_PERSISTING_HELPERS)}\n  gone: {sorted(_KNOWN_PERSISTING_HELPERS - helpers)}"


def test_the_dispatch_only_derivation_still_finds_the_real_schema_tags(repo_root: Path) -> None:
    # If the @web parse silently returned nothing useful, every dispatch-only PUT would read as a
    # flash write and the guard above would fail noisily - but the reverse (a field wrongly counted
    # as dispatch-only) fails SILENTLY, which is the direction that actually spends wear.
    dispatch_only = _dispatch_only_fields(repo_root)
    assert {"SGPResetVOC", "ISLCalibrate"} <= dispatch_only, "the dispatch=true schema tags are no longer being picked up"
    assert dispatch_only >= _ROUTE_DISPATCH_FIELDS
    for persisting in ("PressOvers", "Resolution", "BackupPeriod", "SSID", "NTP_Host", "WarnCO2"):
        assert persisting not in dispatch_only, f"{persisting} is a real persisted config field and must never be treated as dispatch-only"


def test_a_synthetic_unmarked_writer_is_actually_caught(tmp_path: Path, repo_root: Path) -> None:
    # Proves the detector bites rather than merely agreeing with today's tree: the guard above passes
    # trivially if _persisting_put_functions() ever stops finding anything at all.
    module = tmp_path / "test_synthetic.py"
    module.write_text('def test_writes() -> None:\n    http_client.fetch(ip, 80, "PUT", "/sensors", {"BMP3XX": {"PressOvers": 4}}, timeout_s=10.0)\n')
    found = _persisting_put_functions(module, _dispatch_only_fields(repo_root))
    assert found == {"test_writes": {"PressOvers"}}
    assert _marked_functions(module) == set(), "an unmarked writer must not look marked"


@pytest.mark.parametrize("body", ['{"SGP40": {"SGPResetVOC": True}}', '{"ResetErrors": True}', '{"SystemCmd": "reboot"}'])
def test_a_dispatch_only_put_is_not_flagged(tmp_path: Path, repo_root: Path, body: str) -> None:
    module = tmp_path / "test_dispatch.py"
    module.write_text(f'def test_dispatches() -> None:\n    http_client.fetch(ip, 80, "PUT", "/sensors", {body}, timeout_s=10.0)\n')
    assert _persisting_put_functions(module, _dispatch_only_fields(repo_root)) == {}


def _registered_markers(repo_root: Path) -> set[str]:
    conftest = (repo_root / "tests_hardware" / "conftest.py").read_text()
    names = set(re.findall(r'addinivalue_line\(\s*"markers",\s*"(\w+):', conftest))
    assert names, "tests_hardware/conftest.py no longer registers any markers - update this parse with it"
    return names


def _used_markers(repo_root: Path) -> dict[str, set[str]]:
    """Test function name -> the pytest.mark.* names it carries, across the whole tier."""
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
