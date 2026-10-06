"""No file outside devices/ names a device variant: the device set comes from data (devices/*.toml), a
runner argument or a TOML property, never a literal. Files still carrying one sit in _NOT_YET_CLEANED,
which only shrinks; `python tests_scripts/test_no_variant_literals.py` lists the current findings."""

import re
import sys

import pytest
import tomllib
from _devices import DEVICE_NAMES
from _repo_scan import REPO_ROOT, is_shared_excluded, read_text, repo_files

# The check's own patterns and homonym list spell the forms it looks for.
_SELF = "tests_scripts/test_no_variant_literals.py"
# Data read from the devices, not code that names one.
_FIXTURE_PREFIXES = ("devices/", "tests_scripts/golden/", "tests_scripts/fixtures/api_reference/")
# A device name that is also an ordinary word is matched only in variant-shaped forms.
_ENGLISH_HOMONYMS = frozenset({"dev"})
_TC_VERBS = ("replace", "del", "add", "change")

# The content change that removes each kind of literal, named by what it does.
_REASON_CI = "CI takes its device matrix and site builds from devices/*.toml"
_REASON_COMMENT = "the comment or docstring names the per-device pattern, not one device"
_REASON_RUNNER = "the runner takes its device from devices/*.toml or a required argument"
_REASON_UNIT_TEST = "the unit test takes its device from the generated build, selecting by TOML property"
_REASON_PYTEST = "the test iterates DEVICE_NAMES, selects by TOML property or uses the synthetic fixture device"
_REASON_BENCH = "the bench tier names its device through the bench = true TOML key"
_REASON_DEVICE_SCRIPT = "the device script is handed the bench device's generated module, not one name"
_REASON_ALLOWLIST = "shrinks as the quoted sentences naming a device are rewritten"
_REASON_FIXTURE_COMMENT = "the fixture's comments name the property each block copies, not a device TOML"

# File -> the content change that removes its literal. Only shrinks: an entry whose file is clean fails.
_NOT_YET_CLEANED: "dict[str, str]" = {
    ".github/workflows/ci.yml": _REASON_CI,
    ".gitignore": _REASON_COMMENT,
    "buildgen/twin_wiring.py": _REASON_COMMENT,
    "digital_twin/_fram_chip.py": _REASON_RUNNER,
    "digital_twin/launch.py": _REASON_RUNNER,
    "digital_twin/machine.py": _REASON_RUNNER,
    "digital_twin/run_generic_integration.py": _REASON_RUNNER,
    "digital_twin/segfault_stress_repro.py": _REASON_RUNNER,
    "js/mock-server.js": _REASON_COMMENT,
    "pyproject.toml": _REASON_COMMENT,
    "scripts/_digital_twin_ci_suite.py": _REASON_RUNNER,
    "scripts/build_firmware.py": _REASON_RUNNER,
    "scripts/run_digital_twin_ci.sh": _REASON_RUNNER,
    "scripts/run_unix_port_integration.sh": _REASON_RUNNER,
    "scripts/test.sh": _REASON_RUNNER,
    "scripts/typecheck.sh": _REASON_RUNNER,
    "tests/_digital_twin_construction_scenarios.py": _REASON_UNIT_TEST,
    "tests/_sensortask_scenarios.py": _REASON_UNIT_TEST,
    "tests/_webserver_concurrency_scenarios.py": _REASON_UNIT_TEST,
    "tests/test_asy_isl29125_driver.py": _REASON_UNIT_TEST,
    "tests/test_asy_wifi_service.py": _REASON_UNIT_TEST,
    "tests/test_bus_hazard_multi_device.py": _REASON_UNIT_TEST,
    "tests/test_config_manager.py": _REASON_UNIT_TEST,
    "tests/test_digital_twin_bus_hazard_concurrency.py": _REASON_UNIT_TEST,
    "tests/test_digital_twin_construction_arzi.py": _REASON_UNIT_TEST,
    "tests/test_digital_twin_construction_dev.py": _REASON_UNIT_TEST,
    "tests/test_digital_twin_construction_grkizi.py": _REASON_UNIT_TEST,
    "tests/test_digital_twin_construction_klkizi.py": _REASON_UNIT_TEST,
    "tests/test_digital_twin_construction_schlafzi.py": _REASON_UNIT_TEST,
    "tests/test_digital_twin_construction_wozi.py": _REASON_UNIT_TEST,
    "tests/test_digital_twin_generic_wiring.py": _REASON_UNIT_TEST,
    "tests/test_digital_twin_isl29125_autorange.py": _REASON_UNIT_TEST,
    "tests/test_digital_twin_machine.py": _REASON_UNIT_TEST,
    "tests/test_digital_twin_real_website_integration.py": _REASON_UNIT_TEST,
    "tests/test_digital_twin_run_generic_integration.py": _REASON_UNIT_TEST,
    "tests/test_digital_twin_sensortask_integration.py": _REASON_UNIT_TEST,
    "tests/test_digital_twin_uart_link.py": _REASON_UNIT_TEST,
    "tests/test_digital_twin_webserver_concurrency_arzi.py": _REASON_UNIT_TEST,
    "tests/test_digital_twin_webserver_concurrency_dev.py": _REASON_UNIT_TEST,
    "tests/test_digital_twin_webserver_concurrency_grkizi.py": _REASON_UNIT_TEST,
    "tests/test_digital_twin_webserver_concurrency_klkizi.py": _REASON_UNIT_TEST,
    "tests/test_digital_twin_webserver_concurrency_schlafzi.py": _REASON_UNIT_TEST,
    "tests/test_digital_twin_webserver_concurrency_wozi.py": _REASON_UNIT_TEST,
    "tests/test_notification_neopixel_integration.py": _REASON_UNIT_TEST,
    "tests/test_notification_scd30_integration.py": _REASON_UNIT_TEST,
    "tests/test_notification_scd30_sgp40_integration.py": _REASON_UNIT_TEST,
    "tests/test_notification_sgp40_integration.py": _REASON_UNIT_TEST,
    "tests/test_ntp_fram_system_integration.py": _REASON_UNIT_TEST,
    "tests/test_ntp_wifi_dns_integration.py": _REASON_UNIT_TEST,
    "tests/test_sensortask_arzi.py": _REASON_UNIT_TEST,
    "tests/test_sensortask_dev.py": _REASON_UNIT_TEST,
    "tests/test_sensortask_grkizi.py": _REASON_UNIT_TEST,
    "tests/test_sensortask_klkizi.py": _REASON_UNIT_TEST,
    "tests/test_sensortask_schlafzi.py": _REASON_UNIT_TEST,
    "tests/test_sensortask_wozi.py": _REASON_UNIT_TEST,
    "tests/test_system_service.py": _REASON_UNIT_TEST,
    "tests/test_website_build_integration.py": _REASON_UNIT_TEST,
    "tests_hardware/bench/test_network_resilience.py": _REASON_BENCH,
    "tests_hardware/conftest.py": _REASON_BENCH,
    "tests_hardware/device_scripts/allocation_need_per_source.py": _REASON_DEVICE_SCRIPT,
    "tests_hardware/device_scripts/bus_topology_autodetect_and_hazard_sweep.py": _REASON_DEVICE_SCRIPT,
    "tests_hardware/device_scripts/fram_capacity_after_full_system_build.py": _REASON_DEVICE_SCRIPT,
    "tests_hardware/device_scripts/heap_headroom_after_full_system_build.py": _REASON_DEVICE_SCRIPT,
    "tests_hardware/device_scripts/heap_layout_after_full_boot_sequence.py": _REASON_DEVICE_SCRIPT,
    "tests_hardware/device_scripts/heap_under_connection_ceiling.py": _REASON_DEVICE_SCRIPT,
    "tests_hardware/device_scripts/serving_at_default_gc.py": _REASON_DEVICE_SCRIPT,
    "tests_hardware/device_scripts/uart_crossover_exchange.py": _REASON_DEVICE_SCRIPT,
    "tests_hardware/device_scripts/uart_crossover_recovery.py": _REASON_DEVICE_SCRIPT,
    "tests_hardware/device_scripts/uart_driver_read_never_blocks_the_loop.py": _REASON_DEVICE_SCRIPT,
    "tests_hardware/device_scripts/uart_idle_poll_rate.py": _REASON_DEVICE_SCRIPT,
    "tests_hardware/flash/test_reboot_persistence.py": _REASON_BENCH,
    "tests_hardware/flash/test_toolchain_flash_boot.py": _REASON_BENCH,
    "tests_hardware/harness.py": _REASON_BENCH,
    "tests_hardware/isl29125_conformance.py": _REASON_BENCH,
    "tests_hardware/manual/manual_toolchain.py": _REASON_BENCH,
    "tests_hardware/website_identity.py": _REASON_BENCH,
    "tests_scripts/_citation_allowlist.txt": _REASON_ALLOWLIST,
    "tests_scripts/_decision_vocab_allowlist.txt": _REASON_ALLOWLIST,
    "tests_scripts/buildgen_fixtures/novel_combo.toml": _REASON_FIXTURE_COMMENT,
    "tests_scripts/test_build_firmware.py": _REASON_PYTEST,
    "tests_scripts/test_buildgen_defaults.py": _REASON_PYTEST,
    "tests_scripts/test_buildgen_definitions.py": _REASON_PYTEST,
    "tests_scripts/test_buildgen_driver_registry.py": _REASON_PYTEST,
    "tests_scripts/test_buildgen_frozen_modules.py": _REASON_PYTEST,
    "tests_scripts/test_buildgen_generate.py": _REASON_PYTEST,
    "tests_scripts/test_buildgen_graph.py": _REASON_PYTEST,
    "tests_scripts/test_buildgen_limits.py": _REASON_PYTEST,
    "tests_scripts/test_buildgen_requires_tag.py": _REASON_PYTEST,
    "tests_scripts/test_buildgen_tag_comments.py": _REASON_PYTEST,
    "tests_scripts/test_buildgen_twin_wiring.py": _REASON_PYTEST,
    "tests_scripts/test_buildgen_validate.py": _REASON_PYTEST,
    "tests_scripts/test_buildgen_value_wiring.py": _REASON_PYTEST,
    "tests_scripts/test_buildgen_web_tag.py": _REASON_PYTEST,
    "tests_scripts/test_buildgen_wiring.py": _REASON_PYTEST,
    "tests_scripts/test_device_tomls.py": _REASON_PYTEST,
    "tests_scripts/test_digital_twin_boot_contiguity.py": _REASON_PYTEST,
    "tests_scripts/test_digital_twin_ci_suite_ceiling.py": _REASON_PYTEST,
    "tests_scripts/test_digital_twin_ci_suite_errcount.py": _REASON_PYTEST,
    "tests_scripts/test_digital_twin_ci_suite_soak.py": _REASON_PYTEST,
    "tests_scripts/test_digital_twin_generated_boot.py": _REASON_PYTEST,
    "tests_scripts/test_request_body_cap_headroom.py": _REASON_PYTEST,
    "tests_scripts/test_test_sh.py": _REASON_PYTEST,
    "tests_scripts/test_tests_hardware_conftest_constants.py": _REASON_PYTEST,
}


def _homonyms(names: "list[str]", pyproject_text: str) -> "frozenset[str]":
    groups = tomllib.loads(pyproject_text).get("dependency-groups", {})
    return frozenset(n for n in names if n in groups or n in _ENGLISH_HOMONYMS)


def _homonym_patterns(name: str) -> "list[re.Pattern[str]]":
    n = re.escape(name)
    return [
        re.compile(rf"sensortask_{n}\b", re.IGNORECASE),
        re.compile(rf"{n}\.(?:toml|json|uf2)\b", re.IGNORECASE),
        re.compile(rf"firmware-{n}\b", re.IGNORECASE),
        re.compile(rf"SensorStation{n}\b", re.IGNORECASE),
        re.compile(rf"device[= ]{n}\b", re.IGNORECASE),
    ]


def _quoted_is_exempt(line: str, start: int) -> bool:
    """A quoted homonym that is a path join's right operand or a device argv element of `iw`/`tc`."""
    before = line[:start].rstrip()
    if before.endswith("/"):
        return True
    previous = re.search(r"""["'](\w+)["']\s*,$""", before)
    return previous is not None and previous.group(1) in ("iw", *_TC_VERBS)


def _homonym_hits(name: str, line: str, others: "list[str]") -> "list[str]":
    hits = [m.group(0) for p in _homonym_patterns(name) for m in p.finditer(line)]
    quoted = re.finditer(rf"""(["']){re.escape(name)}\1""", line, re.IGNORECASE)
    hits += [m.group(0) for m in quoted if not _quoted_is_exempt(line, m.start())]
    for m in re.finditer(r"\[[^\[\]]*\]", line):
        listed = m.group(0)
        if re.search(rf"\b{re.escape(name)}\b", listed, re.IGNORECASE) and any(re.search(rf"\b{re.escape(o)}\b", listed, re.IGNORECASE) for o in others):
            hits.append(listed)
    return hits


def line_hits(line: str, names: "list[str]", homonyms: "frozenset[str]") -> "list[str]":
    """Every variant literal on one line: a plain name anywhere, a homonym only in variant-shaped forms."""
    hits: list[str] = []
    for name in names:
        if name in homonyms:
            hits += _homonym_hits(name, line, [o for o in names if o != name])
        else:
            hits += [m.group(0) for m in re.finditer(re.escape(name), line, re.IGNORECASE)]
    return hits


def _in_scope(path: str) -> bool:
    return not (is_shared_excluded(path) or path == _SELF or path.endswith(".md") or path.startswith(_FIXTURE_PREFIXES))


def file_findings(text: str, names: "list[str]", homonyms: "frozenset[str]") -> "list[tuple[int, str]]":
    return [(number, hit) for number, line in enumerate(text.splitlines(), 1) for hit in line_hits(line, names, homonyms)]


def collect_findings() -> "dict[str, list[tuple[int, str]]]":
    homonyms = _homonyms(DEVICE_NAMES, (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    found: dict[str, list[tuple[int, str]]] = {}
    for path in repo_files():
        if _in_scope(path) and (text := read_text(path)) is not None:
            hits = file_findings(text, DEVICE_NAMES, homonyms)
            if hits:
                found[path] = hits
    return found


def test_no_file_outside_the_device_tomls_names_a_variant() -> None:
    found = collect_findings()
    new = {path: hits[:3] for path, hits in found.items() if path not in _NOT_YET_CLEANED}
    assert not new, "variant literals outside devices/ - take the device from data, an argument or a TOML property:\n" + "\n".join(f"  {p}: {h}" for p, h in sorted(new.items()))


def test_every_not_yet_cleaned_entry_still_carries_a_literal() -> None:
    found = collect_findings()
    stale = sorted(path for path in _NOT_YET_CLEANED if path not in found)
    assert not stale, f"these files are clean now - remove their _NOT_YET_CLEANED entries: {stale}"


def test_every_not_yet_cleaned_reason_names_a_change() -> None:
    blank = sorted(path for path, reason in _NOT_YET_CLEANED.items() if not reason.strip())
    assert not blank, f"each entry names the change that removes its literal: {blank}"


def _named(text: str) -> str:
    """A self-test line with `{V}` as a plain device name and `{H}` as a homonym, both from the data."""
    plain = next(n for n in DEVICE_NAMES if n not in _homonyms(DEVICE_NAMES, ""))
    homonym = next(iter(_homonyms(DEVICE_NAMES, "") or _ENGLISH_HOMONYMS))
    return text.replace("{V}", plain).replace("{Vc}", plain.capitalize()).replace("{H}", homonym).replace("{Hc}", homonym.capitalize())


@pytest.mark.parametrize(
    "line",
    [
        "# the {V} board",  # a comment
        'device = "{V}"',  # a string
        "import sensortask_{V}",  # an identifier
        'name = "SensorStation{Vc}"',
        "const {V}Data = 1;",
        'title = "SensorStation{Hc}"',
        'args = ["--device", "{H}"]',
        "path = 'devices/{H}.toml'",
        "matrix: [{V}, {H}]",
    ],
)
def test_a_variant_literal_is_caught(line: str) -> None:
    names = [*DEVICE_NAMES, *_ENGLISH_HOMONYMS]
    assert line_hits(_named(line), names, _homonyms(names, "")), _named(line)


@pytest.mark.parametrize(
    "line",
    [
        'port = "/{H}/ttyACM0"',
        'apt = "libffi-{H}"',
        "# {H}-tooling only",
        'subprocess.run(["iw", "{H}", iface])',
        'subprocess.run(["tc", "qdisc", "del", "{H}", iface])',
        'root = tmp_path / "{H}"',
    ],
)
def test_a_homonym_in_ordinary_use_passes(line: str) -> None:
    names = [*DEVICE_NAMES, *_ENGLISH_HOMONYMS]
    assert not line_hits(_named(line), names, _homonyms(names, "")), _named(line)


def test_a_dependency_group_name_counts_as_a_homonym() -> None:
    assert _homonyms(["zz", "tools"], '[dependency-groups]\ntools = ["x"]\n') == frozenset({"tools"})


if __name__ == "__main__":
    for found_path, found_hits in sorted(collect_findings().items()):
        marker = " " if found_path in _NOT_YET_CLEANED else "+"
        print(f"{marker} {found_path}: {found_hits[:3]}")
    sys.exit(0)
