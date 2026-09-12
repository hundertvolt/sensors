"""Single source of truth for this project's own product version (BUILD_CHAIN_PLAN.md Session 7) -
tracked independently for firmware and website since Session 4/6 already decoupled their own build
steps (a website-only fix can bump one without the other). Bump either constant by editing it
directly here; no automation exists or is planned - see BUILD_CHAIN_PLAN.md's own Session 7 account
for why. Consumed by buildgen.codegen (embeds FIRMWARE_VERSION into every generated device module,
readable live via GET /status) and buildgen.definitions (stamps WEBSITE_VERSION into
definitions.json as build provenance)."""

FIRMWARE_VERSION = "2.0b0"
WEBSITE_VERSION = "2.0b0"
