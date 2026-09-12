"""Single source of truth for this project's own product version (BUILD_CHAIN_PLAN.md Session 7) -
tracked independently for firmware and website since Session 4/6 already decoupled their own build
steps (a website-only fix can bump one without the other). Bump either constant by editing it
directly here; no automation exists or is planned - see BUILD_CHAIN_PLAN.md's own Session 7 account
for why. Consumed by buildgen.codegen, which embeds both plus a fresh current_build_date() into
every generated device module as the "build" sub-object of GET /system's response
(asy_webserver_service.py's build_info= constructor kwarg), and by buildgen.definitions, which
stamps WEBSITE_VERSION into definitions.json separately as build provenance for that file itself."""

from datetime import UTC, datetime

FIRMWARE_VERSION = "2.0b0"
WEBSITE_VERSION = "2.0b0"


def current_build_date() -> str:
    """An ISO-8601 UTC timestamp for "right now" - captured once per real generate_device() call,
    never computed on-device (the generated value is a plain string literal, not live device
    state). Threaded through as an explicit parameter everywhere else in buildgen so tests can pin
    a fixed value instead of asserting against a moving "now"."""
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
