"""Single source of truth for this project's own product version (BUILD_CHAIN_PLAN.md Session 7) -
bump FIRMWARE_VERSION/WEBSITE_VERSION by hand; no automation exists or is planned. Consumed by
buildgen.codegen/definitions (see that session's own account for the full consumer list/reasoning)."""

from datetime import UTC, datetime

FIRMWARE_VERSION = "2.0b0"
WEBSITE_VERSION = "2.0b0"


def current_build_date() -> str:
    """ISO-8601 UTC "now", captured once per real generate_device() call (never computed on-device).
    Threaded through as an explicit parameter so tests/batch builds can pin one fixed value instead
    of racing a moving wall clock (BUILD_CHAIN_PLAN.md Session 7)."""
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
