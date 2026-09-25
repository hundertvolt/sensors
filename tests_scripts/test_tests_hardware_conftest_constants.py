"""Holds tests_hardware/conftest.py's three hardcoded DUT-identity constants to the two files that
actually decide them - devices/dev.toml and src/asy_wifi_service.py's schema defaults. Drift here is
silent and only shows up as a bench recovery that scans for an SSID no board is broadcasting."""

import ast
import re
from pathlib import Path

import pytest
import tomllib
from _devices import device_toml

_BENCH_DEVICE = "dev"  # the only unit ever bench-flashed (CLAUDE.md's hard rule)


def _conftest_constant(repo_root: Path, name: str) -> object:
    """The literal value assigned to a module-level constant, read without importing the module
    (tests_hardware/conftest.py imports pytest plugins and hardware helpers this suite has no
    business pulling in just to read two strings)."""
    tree = ast.parse((repo_root / "tests_hardware" / "conftest.py").read_text())
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in node.targets):
            return ast.literal_eval(node.value)
    raise AssertionError(f"tests_hardware/conftest.py no longer defines {name}")


def _hostname_candidates(repo_root: Path) -> "tuple[str, ...]":
    value = _conftest_constant(repo_root, "_DUT_HOSTNAME_CANDIDATES")
    # Shape-checked, not cast: a candidate list that stopped being a tuple of strings would make
    # every assertion below either vacuous or confusingly wrong.
    assert isinstance(value, tuple) and value and all(isinstance(c, str) for c in value), value
    return value


def _hotspot_password(repo_root: Path) -> str:
    value = _conftest_constant(repo_root, "_DUT_HOTSPOT_PASSWORD")
    assert isinstance(value, str), value
    return value


def _schema_default(repo_root: Path, const_name: str) -> str:
    """The default (third element) of a one-field _VAL_* schema tuple in src/asy_wifi_service.py.
    Read as text, not imported: micropython.const() folds the name out at runtime anyway."""
    source = (repo_root / "src" / "asy_wifi_service.py").read_text()
    match = re.search(rf"^{const_name} = const\((\(\(.*?\),\))\)", source, re.MULTILINE)
    assert match is not None, f"src/asy_wifi_service.py no longer declares {const_name} in the expected shape"
    return str(ast.literal_eval(match.group(1))[0][2])


def test_the_first_hostname_candidate_is_the_bench_devices_own_toml_hostname(repo_root: Path) -> None:
    # Ordered newest-first, so a freshly flashed board is found on the first scan - which only holds
    # if the first entry really is what a build now injects as that board's hostname default.
    candidates = _hostname_candidates(repo_root)
    doc = tomllib.loads(device_toml(_BENCH_DEVICE).read_text())
    assert candidates[0] == doc["device"]["hostname"], "the bench would scan for an SSID the dev board no longer broadcasts"


def test_the_last_hostname_candidate_is_still_the_shared_schema_default(repo_root: Path) -> None:
    # The fallback exists for a board whose config file predates per-device hostname injection: it
    # still carries the persisted shared default and keeps using it.
    candidates = _hostname_candidates(repo_root)
    assert candidates[-1] == _schema_default(repo_root, "_VAL_HOST")


def test_every_hostname_candidate_fits_the_schema_bound_it_will_be_matched_against(repo_root: Path) -> None:
    # A candidate longer than the field's own cap could never be a live Hostname, so scanning for it
    # is dead code that reads as coverage.
    for candidate in _hostname_candidates(repo_root):
        assert 1 <= len(candidate) <= 32, f"{candidate!r} cannot be a live Hostname value"


@pytest.mark.parametrize("source", ["toml", "schema"])
def test_the_bench_hotspot_password_matches_both_sides(repo_root: Path, source: str) -> None:
    # The bench joins the DUT's own hotspot with this password; the board derives it from its schema
    # default, which a build now overrides with the TOML's. Both must agree or the join just fails.
    expected = (
        tomllib.loads(device_toml(_BENCH_DEVICE).read_text())["device"]["hotspot_password"]
        if source == "toml"
        else _schema_default(repo_root, "_VAL_HOTSPOT_PW")
    )
    assert _hotspot_password(repo_root) == expected
