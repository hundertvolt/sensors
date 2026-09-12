"""Tests for buildgen.version (BUILD_CHAIN_PLAN.md Session 7): the one source-of-truth pair of
product-version constants every generated firmware module and every generated definitions.json
stamps itself with, plus current_build_date() (GET /system's "build" sub-entry). No bump mechanism
exists (deliberately, per that session's own account) - these tests only prove the two constants
are well-formed and match the plan's own starting value, and that the date helper is correct."""

import re
from datetime import UTC, datetime, timedelta

from buildgen.version import FIRMWARE_VERSION, WEBSITE_VERSION, current_build_date

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


def test_current_build_date_matches_the_documented_format() -> None:
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", current_build_date())


def test_current_build_date_is_a_real_utc_timestamp_for_right_now() -> None:
    before = datetime.now(UTC)
    parsed = datetime.fromisoformat(current_build_date())
    after = datetime.now(UTC)
    assert before - timedelta(seconds=1) <= parsed <= after + timedelta(seconds=1)
