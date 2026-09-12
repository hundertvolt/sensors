"""Tests for buildgen.version (BUILD_CHAIN_PLAN.md Session 7): the one source-of-truth pair of
product-version constants every generated firmware module and every generated definitions.json
stamps itself with. No bump mechanism exists (deliberately, per that session's own account) - these
tests only prove the two constants are well-formed and match the plan's own starting value."""

import re

from buildgen.version import FIRMWARE_VERSION, WEBSITE_VERSION

# PEP 440-style release[.dev|a|b|rc][N] segment - loose on purpose (this project's own version
# scheme, not a contract with an external tool), just enough to catch a typo like a stray space or
# a missing digit before it ships in a real build.
_VERSION_RE = re.compile(r"^\d+\.\d+(?:(?:a|b|rc)\d+)?$")


def test_firmware_version_is_a_well_formed_version_string() -> None:
    assert _VERSION_RE.match(FIRMWARE_VERSION)


def test_website_version_is_a_well_formed_version_string() -> None:
    assert _VERSION_RE.match(WEBSITE_VERSION)


def test_starting_values_match_the_plan() -> None:
    # BUILD_CHAIN_PLAN.md's own Session 7 scope line: "firmware + website, both starting at 2.0b0".
    assert FIRMWARE_VERSION == "2.0b0"
    assert WEBSITE_VERSION == "2.0b0"
