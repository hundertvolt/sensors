"""What a persistence write lands in, by name: "<section>/<group>" for every settings group a PUT can persist
on any device, as the device definitions key it, plus HWTEST_FILE. The vocabulary of
@pytest.mark.persistence_write's arguments and of --allow-persistence-writes-to (tests_hardware/README.md)."""

from __future__ import annotations

import sys
from functools import cache
from pathlib import Path
from typing import TYPE_CHECKING

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # the repo root, for buildgen

from buildgen.definitions import definitions_for_toml

if TYPE_CHECKING:
    from collections.abc import Iterable

    import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
HWTEST_FILE = "hwtest"  # a config_HWTEST_*.cfg file a device script writes for itself, no settings group
GLOBAL_FLAG = "--allow-persistence-writes"
SCOPED_FLAG = "--allow-persistence-writes-to"


@cache
def persistence_groups() -> frozenset[str]:
    # Every group holding a field a PUT persists: neither readonly nor dispatch-only, on any device.
    found = {HWTEST_FILE}
    for toml in sorted((REPO_ROOT / "devices").glob("*.toml")):
        if toml.stem.startswith("zz_test_"):  # a leaked live-tree fixture, never a device
            continue
        for section in definitions_for_toml(toml, REPO_ROOT / "src")["sections"]:
            if "put" not in section.get("rest", {}):
                continue
            for group in section["groups"]:
                if any(f.get("kind") not in (None, "readonly") and not f.get("dispatch") for f in group.get("fields", [])):
                    found.add(f"{section['key']}/{group['key']}")
    return frozenset(found)


def parse_groups(values: Iterable[str]) -> frozenset[str]:
    # --allow-persistence-writes-to's values, each one group or a comma-separated list.
    return frozenset(group.strip() for value in values for group in value.split(",") if group.strip())


def allowed_groups(config: pytest.Config) -> frozenset[str]:
    return parse_groups(config.getoption(SCOPED_FLAG) or ())


def deselected_by(groups: Iterable[str], config: pytest.Config) -> str | None:
    # The flag that would permit a write to these groups, None when one already does. A marker naming no
    # group needs the global flag; without any scoped flag the advice stays the global one.
    if config.getoption(GLOBAL_FLAG):
        return None
    wanted = tuple(groups)
    allowed = allowed_groups(config)
    missing = sorted(group for group in wanted if group not in allowed)
    if wanted and not missing:
        return None
    if not wanted or not allowed:
        return GLOBAL_FLAG
    return f"{SCOPED_FLAG}={','.join(missing)}"


def writes_permitted(groups: Iterable[str], config: pytest.Config) -> bool:
    return deselected_by(groups, config) is None
