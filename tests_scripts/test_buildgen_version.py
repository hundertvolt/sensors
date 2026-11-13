"""Tests for buildgen.version (SPECIFICATION.md Part L.7): the two version constants are
well-formed and the build date is a real UTC timestamp; bumps are by hand."""

import re
from datetime import UTC, datetime, timedelta

import pytest

from buildgen.version import FIRMWARE_VERSION, WEBSITE_VERSION, current_build_date

# <major>.<minor>, optionally a|b|rc<N> (e.g. 2.0b0, 2.1rc1, 2.1): enough to catch a stray space or a
# missing digit before it ships.
_VERSION_RE = re.compile(r"^\d+\.\d+(?:(?:a|b|rc)\d+)?$")


def test_firmware_version_is_a_well_formed_version_string() -> None:
    assert _VERSION_RE.match(FIRMWARE_VERSION)


def test_website_version_is_a_well_formed_version_string() -> None:
    assert _VERSION_RE.match(WEBSITE_VERSION)


@pytest.mark.parametrize(
    ("version", "accepted"),
    [
        ("2.0b0", True),
        ("2.1", True),
        ("10.12rc3", True),
        ("2.0a1", True),
        ("2.0 b0", False),
        ("2.0.1", False),
        ("2.0.dev1", False),
        ("v2.0", False),
        ("2.0b", False),
        ("2", False),
    ],
)
def test_the_version_form_accepts_exactly_its_comment(version: str, *, accepted: bool) -> None:
    assert bool(_VERSION_RE.match(version)) is accepted


def test_current_build_date_matches_the_documented_format() -> None:
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", current_build_date())


def test_current_build_date_is_a_real_utc_timestamp_for_right_now() -> None:
    before = datetime.now(UTC)
    parsed = datetime.fromisoformat(current_build_date())
    after = datetime.now(UTC)
    assert before - timedelta(seconds=1) <= parsed <= after + timedelta(seconds=1)
