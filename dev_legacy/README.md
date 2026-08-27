# dev_legacy

Verbatim snapshot of the physical "dev" RP2040 bench unit's onboard filesystem, pulled over USB
serial via `mpremote` (`scripts/mpremote_connect.sh cp -r :. dev_legacy/`) on 2026-08-27. This unit
runs MicroPython 1.24.1 — the deployed-fleet firmware version the legacy `python/`/`modules/` code
targets, distinct from `improved-quality/`'s (now fully promoted into `src/`) 1.26 target. Contains
code changes made directly on this unit that were never copied back to any host machine, so this is
the only remaining copy — kept here as reference for future `src/` promotion work, not itself
promoted, reviewed, or covered by lint/type/test config (see CLAUDE.md's `src/` scope).
