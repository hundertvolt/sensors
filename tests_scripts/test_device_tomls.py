"""Device-TOML checks `validate.py` does not make: reserved I2C addresses, the hostname convention,
the FRAM part comment, section layout and banners, and per-device test coverage. Every device's own
validation runs here too, through `build_model()` itself rather than a second hand-written validator."""

import ast
import io
import re
import tokenize
from pathlib import Path

import pytest
import tomllib
from _devices import DEVICE_NAMES

from buildgen.buildspec import BUS_KIND_BY_DRIVER, FIXED_ADDRESS_DRIVERS
from buildgen.driver_registry import SINGLETON_SERVICE_DRIVERS, resolve_driver
from buildgen.graph import build_construction_order
from buildgen.twin_wiring import fixed_address
from buildgen.validate import build_model

# The one banner form and its titles, in the order the sections stand (SPECIFICATION.md Part L.3).
_BANNER_RE = re.compile(r"^# --- [a-z -]+ -+$")
_BANNER_WIDTH = 100
_BANNERS = ("sensor drivers", "singleton services", "multi-instance services")
_HOSTNAME_PREFIX = "SensorStation"
# Only name and hostname may differ between the devices of one [device] hardware_family.
_IDENTITY_KEYS = ("name", "hostname")


@pytest.fixture(scope="session")
def devices_dir(repo_root: Path) -> Path:
    return repo_root / "devices"


def _load(devices_dir: Path, name: str) -> "dict[str, object]":
    with open(devices_dir / f"{name}.toml", "rb") as f:
        return tomllib.load(f)


def _device_table(doc: "dict[str, object]") -> "dict[str, object]":
    table = doc.get("device")
    assert isinstance(table, dict), "no [device] table"
    return table


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_every_device_builds(devices_dir: Path, repo_root: Path, device: str) -> None:
    # The validator is the schema check: a device that builds orders every instance it declares.
    model = build_model(devices_dir / f"{device}.toml", repo_root / "src")
    assert set(model.instances) <= set(build_construction_order(model)), device


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_hostname_is_sensorstation_plus_name(devices_dir: Path, device: str) -> None:
    table = _device_table(_load(devices_dir, device))
    assert table["hostname"] == f"{_HOSTNAME_PREFIX}{table['name']}", device


def test_devices_of_one_hardware_family_differ_only_in_identity(devices_dir: Path) -> None:
    # Devices naming one [device] hardware_family share their hardware (agent, 2026-09-14): every table but
    # name and hostname is equal; diverging hardware removes the key from that one file.
    families: dict[str, list[tuple[str, dict[str, object]]]] = {}
    for device in DEVICE_NAMES:
        doc = _load(devices_dir, device)
        family = _device_table(doc).get("hardware_family")
        if isinstance(family, str):
            for key in _IDENTITY_KEYS:
                del _device_table(doc)[key]
            families.setdefault(family, []).append((device, doc))
    shared = {family: members for family, members in families.items() if len(members) > 1}
    assert shared, "no hardware_family names two devices - this check is comparing nothing"
    for family, members in shared.items():
        first_device, first = members[0]
        for device, doc in members[1:]:
            assert doc == first, f"{device} and {first_device} share hardware_family {family!r} but differ beyond {_IDENTITY_KEYS}"


def _expected_banner(driver: str, src_dir: Path, device: str) -> str:
    # The banner a driver's instance sits under, by the registry's own classification of the driver.
    if resolve_driver(driver, src_dir, device).kind == "sensor":
        return _BANNERS[0]
    return _BANNERS[1] if driver in SINGLETON_SERVICE_DRIVERS else _BANNERS[2]


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_the_sections_stand_in_the_fixed_order_under_their_banners(devices_dir: Path, repo_root: Path, device: str) -> None:
    # [device], [device.wiring] and the buses first, then each instance under the banner its driver's kind selects;
    # one banner form at the file's 100 characters, each banner over at least one instance (SPECIFICATION.md L.3).
    text = (devices_dir / f"{device}.toml").read_text()
    lines = text.splitlines()
    instances = tomllib.loads(text).get("instance", [])
    assert isinstance(instances, list)
    banners = [(n, line) for n, line in enumerate(lines, 1) if line.startswith("# ---")]
    for n, line in banners:
        assert _BANNER_RE.match(line) and len(line) == _BANNER_WIDTH, f"{device}:{n}: banner {line!r} is not '# --- <title> ---' at {_BANNER_WIDTH} characters"
    titles = [line[len("# --- ") :].rstrip("- ") for _, line in banners]
    assert all(t in _BANNERS for t in titles) and titles == sorted(titles, key=_BANNERS.index) and len(set(titles)) == len(titles), f"{device}: banners {titles}"
    headers = [(n, line) for n, line in enumerate(lines, 1) if line.startswith("[") and not line.startswith(("[[", "[instance."))]
    assert headers and headers[0][1] == "[device]", f"{device}: the first table is {headers[:1]}, not [device]"
    first_banner = banners[0][0] if banners else len(lines) + 1
    assert all(n < first_banner for n, _ in headers), f"{device}: a [device]/[bus.*] table stands below the first banner"
    starts = [n for n, line in enumerate(lines, 1) if line == "[[instance]]"]
    assert len(starts) == len(instances)
    under: dict[str, int] = {}
    for start, inst in zip(starts, instances, strict=True):
        assert isinstance(inst, dict)
        driver = str(inst["driver"])
        title = next((t for (n, _), t in zip(reversed(banners), reversed(titles), strict=True) if n < start), None)
        assert title == _expected_banner(driver, repo_root / "src", device), f"{device}:{start}: {driver} sits under {title!r}"
        under[title] = under.get(title, 0) + 1
        if driver not in SINGLETON_SERVICE_DRIVERS:
            assert "name_ext" in inst, f"{device}:{start}: {driver} states no name_ext"
    assert all(under.get(t) for t in titles), f"{device}: a banner stands over no instance: {titles} vs {under}"


def _fram_part_names(repo_root: Path) -> "dict[int, str]":
    # asy_fram_driver._KNOWN_PRODUCT_IDS's sizes with the part each entry's comment names, read by ast and tokenize.
    path = repo_root / "src" / "asy_fram_driver.py"
    text = path.read_text()
    comments = {tok.start[0]: tok.string for tok in tokenize.generate_tokens(io.StringIO(text).readline) if tok.type == tokenize.COMMENT}
    for node in ast.parse(text).body:
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == "_KNOWN_PRODUCT_IDS" and isinstance(node.value, ast.Dict):
            parts: dict[int, str] = {}
            for key in node.value.keys:
                assert isinstance(key, ast.Constant) and isinstance(key.value, int), "a _KNOWN_PRODUCT_IDS key is no int literal"
                parts[key.value] = comments[key.lineno].lstrip("# ").split(",")[0]
            return parts
    raise AssertionError(f"{path} declares no _KNOWN_PRODUCT_IDS dict")


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_the_fram_part_is_named_above_its_size(devices_dir: Path, repo_root: Path, device: str) -> None:
    # The driver checks the wired chip against the part max_size implies; the TOML names that part beside it.
    parts = _fram_part_names(repo_root)
    lines = (devices_dir / f"{device}.toml").read_text().splitlines()
    sizes = [n for n, line in enumerate(lines) if line.startswith("max_size = ")]
    for n in sizes:
        size = int(lines[n].split("=")[1], 0)
        assert lines[n - 1].startswith(f"# {parts[size]},"), f"{device}:{n + 1}: the line above max_size = {size:#x} does not name {parts[size]}"
    instances = tomllib.loads("\n".join(lines)).get("instance", [])
    assert len(sizes) == sum(1 for inst in instances if isinstance(inst, dict) and inst.get("driver") == "fram"), device


def test_every_device_is_covered_by_the_micropython_tiers_per_device_files(repo_root: Path) -> None:
    # The MicroPython tier cannot discover devices the way DEVICE_NAMES does, so it is checked
    # against them instead: tests/ runs one process per test FILE, and no import-time glob conjures
    # a file. Replaces an older devices/-holds-exactly-DEVICE_NAMES check, tautological since.
    #
    # Each scenario library's `_DEVICES` tuple stays hand-written deliberately: its ORDER assigns
    # the twin's TCP port bases. What must not stay silent is a device added to devices/ while
    # these are not - it would ship uncovered, with every one of those suites still passing.
    expected = set(DEVICE_NAMES)
    problems = []
    for family in ("test_sensortask", "test_digital_twin_construction", "test_digital_twin_webserver_concurrency"):
        present = {p.stem[len(family) + 1 :] for p in (repo_root / "tests").glob(f"{family}_*.py")}
        if present != expected:
            problems.append(f"tests/{family}_<device>.py covers {sorted(present)}, but devices/ holds {sorted(expected)}")
    for scenarios in ("_sensortask_scenarios.py", "_digital_twin_construction_scenarios.py", "_webserver_concurrency_scenarios.py"):
        text = (repo_root / "tests" / scenarios).read_text()
        match = re.search(r"^_DEVICES = \(([^)]*)\)", text, re.MULTILINE)
        if match is None:
            problems.append(f"tests/{scenarios} no longer declares a _DEVICES tuple - update this check with it")
            continue
        listed = {name.strip().strip('"') for name in match.group(1).split(",") if name.strip()}
        if listed != expected:
            problems.append(f"tests/{scenarios}'s _DEVICES is {sorted(listed)}, but devices/ holds {sorted(expected)}")
    assert not problems, "the MicroPython tier does not cover every real device:\n  " + "\n  ".join(problems)


def test_every_device_is_in_the_ci_workflow_matrices(repo_root: Path) -> None:
    # A GitHub Actions matrix is a literal - no expression can glob devices/ at parse time, so the
    # two lists stay hand-written and are checked here instead. Without this a seventh device would
    # generate, build and pass locally while CI silently kept exercising the old six.
    #
    # Regex rather than a YAML parse: pyyaml is not a dependency of this repo, and the matrix line
    # is a fixed one-line flow sequence. A reshaped matrix fails the count assert below, loudly.
    text = (repo_root / ".github" / "workflows" / "ci.yml").read_text()
    matrices = re.findall(r"^\s*device: \[([^\]]*)\]", text, re.MULTILINE)
    assert len(matrices) == 2, f"expected exactly 2 device matrices in ci.yml (digital-twin-e2e, firmware-build-verify), found {len(matrices)} - update this check with the workflow"
    for matrix in matrices:
        listed = {name.strip() for name in matrix.split(",") if name.strip()}
        assert listed == set(DEVICE_NAMES), f"a ci.yml device matrix is {sorted(listed)}, but devices/ holds {sorted(DEVICE_NAMES)}"


# I2C-spec reserved ranges: 0x00-0x07 and 0x78-0x7F. No device address may fall inside either, or
# the chip answers to - or is masked by - a bus-wide protocol address.

# Inherited from the deleted tests_hardware/bus_topology.py, which asserted it over two hand-kept
# tuples nothing imported; here it runs against the real device set. The on-target sweep keeps
# its own copy deliberately, being MicroPython on the board and unable to import host test code.
_RESERVED_I2C_RANGES = ((0x00, 0x07), (0x78, 0x7F))


def _is_reserved(address: int) -> bool:
    return any(lo <= address <= hi for lo, hi in _RESERVED_I2C_RANGES)


def _declared_i2c_addresses(doc: "dict[str, object]") -> "list[tuple[str, int]]":
    # Filtered on the instance's own bus, not just on the presence of an `address` field: a reserved
    # I2C range says nothing about an address on any other kind of bus, and a future SPI/UART driver
    # carrying an `address` field would otherwise be judged against ranges that do not apply to it.
    instances = doc.get("instance", [])
    declared = [inst for inst in instances if isinstance(inst, dict)] if isinstance(instances, list) else []
    return [(str(inst["driver"]), inst["address"]) for inst in declared if isinstance(inst.get("address"), int) and str(inst.get("bus", "")).startswith("i2c")]


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_no_declared_i2c_address_falls_in_a_reserved_range(devices_dir: Path, device: str) -> None:
    for driver, address in _declared_i2c_addresses(_load(devices_dir, device)):
        assert not _is_reserved(address), f"{device}: {driver} declares I2C address {address:#04x}, which is in a reserved range"


def test_the_reserved_range_sweep_actually_sees_a_declared_address(devices_dir: Path) -> None:
    # Part E.8's guard-is-blind trap: only bmp3xx carries a TOML address field today, so a schema
    # change that renamed it - or moved the bus field - would turn the per-device sweep above into a
    # silent no-op on every device, and a passing suite would say nothing at all.
    seen = [pair for device in DEVICE_NAMES for pair in _declared_i2c_addresses(_load(devices_dir, device))]
    assert seen, "no device declares an I2C address field at all - the reserved-range sweep above is checking nothing"


def test_no_fixed_driver_address_falls_in_a_reserved_range(repo_root: Path) -> None:
    # The other half: the fixed-address I2C drivers carry no TOML address field at all, so the TOML
    # sweep above can never see them; each one's address is read from its own driver file.
    drivers = sorted(d for d in FIXED_ADDRESS_DRIVERS if BUS_KIND_BY_DRIVER[d] == "i2c")
    assert drivers, "no fixed-address I2C driver - the sweep is checking nothing"
    for driver in drivers:
        address = fixed_address(resolve_driver(driver, repo_root / "src", "fixture"))
        assert not _is_reserved(address), f"{driver}'s fixed I2C address {address:#04x} is in a reserved range"
