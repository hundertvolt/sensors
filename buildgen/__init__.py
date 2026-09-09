"""Session 3 of BUILD_CHAIN_PLAN.md's device-genericization initiative: a host-side (CPython)
generator that turns one `devices/<device>.toml` into the equivalent of a hand-written
`sensortask_<device>.py` + boot entry. Never imports `src/` (those modules need real
MicroPython-only names like `machine`/`neopixel`) - everything is derived by parsing TOML and by
AST-parsing driver source as text. See BUILD_CHAIN_PLAN.md and SPECIFICATION.md Part C.14 for the
mechanism this drives."""
