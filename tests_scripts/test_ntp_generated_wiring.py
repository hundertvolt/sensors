"""The NTP chain the integration tests build by hand is the generated build_system()'s own (SPECIFICATION.md A.7):
NTPClient's three positional providers and SystemService's sync check, read by ast from every device's generated
module, and the same three providers in both _make_ntp() bodies under tests/."""

import ast
from pathlib import Path

import pytest
from _devices import DEVICE_NAMES, device_toml

from buildgen.generate import generate_device

_REPO_ROOT = Path(__file__).resolve().parent.parent
_MAKE_NTP_FILES = ("tests/test_ntp_fram_system_integration.py", "tests/test_ntp_wifi_dns_integration.py")
# NTPClient's wifi-mode lock, network check and DNS server, then SystemService's sync check: providers by position.
_NTP_PROVIDERS = ["conn.get_wifi_mode_lock()", "conn.network_available_locked", "conn.get_dns_server_ip"]
_SYNC_CHECK = ["ntp.ntp_issynced"]


def _providers(source: str, function: str, callee: str, count: int) -> "list[str]":
    # The first `count` positional arguments of the one `callee(...)` call inside `function`, as source text.
    tree = ast.parse(source)
    (body,) = [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == function]
    calls = [n for n in ast.walk(body) if isinstance(n, ast.Call) and ast.unparse(n.func) == callee]
    assert len(calls) == 1, f"{function}() holds {len(calls)} {callee}() calls, not one"
    return [ast.unparse(a) for a in calls[0].args[:count]]


@pytest.fixture(scope="module")
def generated() -> "dict[str, str]":
    return {d: generate_device(device_toml(d), _REPO_ROOT / "src", _REPO_ROOT / "ext").module_source for d in DEVICE_NAMES}


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_the_generated_build_system_passes_the_ntp_providers_and_the_sync_check(generated: "dict[str, str]", device: str) -> None:
    assert _providers(generated[device], "build_system", "NTPClient", 3) == _NTP_PROVIDERS
    assert _providers(generated[device], "build_system", "SystemService", 1) == _SYNC_CHECK


def _hand_chain_problems(test_source: str, generated: "dict[str, str]") -> "list[str]":
    wired = {tuple(_providers(source, "build_system", "NTPClient", 3)) for source in generated.values()}
    if len(wired) != 1:
        return [f"the devices' generated NTP providers differ: {sorted(wired)}"]
    hand = _providers(test_source, "_make_ntp", "NTPClient", 3)
    return [] if hand == list(wired.pop()) else [f"_make_ntp() passes {hand}, the generated build_system() {_NTP_PROVIDERS}"]


@pytest.mark.parametrize("path", _MAKE_NTP_FILES)
def test_each_make_ntp_body_passes_the_generated_providers_in_their_order(generated: "dict[str, str]", path: str) -> None:
    assert _hand_chain_problems((_REPO_ROOT / path).read_text(encoding="utf-8"), generated) == []


def test_a_swapped_provider_in_a_make_ntp_body_fails(generated: "dict[str, str]") -> None:
    # Two providers traded in place: still three callables, so only their positions show the hand chain drifted.
    text = (_REPO_ROOT / _MAKE_NTP_FILES[1]).read_text(encoding="utf-8")
    swapped = text.replace("conn.get_wifi_mode_lock(), conn.network_available_locked,", "conn.network_available_locked, conn.get_wifi_mode_lock(),", 1)
    assert swapped != text, "the planted swap found no anchor"
    assert _hand_chain_problems(swapped, generated)
