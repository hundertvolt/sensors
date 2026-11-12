TITLE: Release 2.0: the audited firmware, build chain, tests and docs

BODY:
Release 2.0 of the sensor-station firmware: the refactored `src/` on MicroPython v1.29.0, built per device by
`buildgen` from `devices/*.toml`, verified on four test tiers and on the dev bench. README's "Release" section is the
release note against the legacy firmware; `buildgen/version.py` carries 2.0.

## What changed against the pre-audit tree (25caf528)
- Errors and logs: one global error catalog, every module's history under `GET /status` `errcount`, FRAM-backed
  where wired.
- Storage: synchronous FRAM chunk operations and log entries, the FRAM bus at 8 MHz, owner-seeded CRCs, config
  files written only on change.
- Time and supervision: deadline sleeps on fixed grids, a recorded `ResetReason` for every reset, one controlled
  shutdown per system command, `LastTaskEnd`.
- Drivers: one base and recovery ladder for the four sensors; SGP40 VOC port bit-identical to Sensirion's C
  reference; ISL29125 `RangeAuto`.
- Network: six REST endpoints from one generated reference; a patched lwIP copy (EAGAIN on a full send queue) with
  `TCP_SND_BUF` 1,600 B, chosen on silicon.
- UART link: bounded receives on a DMA ring that never block the loop; protocol changes logged for the C side.
- Tests and CI: unit (Unix port, both GC stages), digital twin on every device, flash and bench tiers on silicon.

## Verified
- Final tree `<sha>`: unit tests at both GC stages, twins at both, web tier, lint, three mypy passes, every
  device's firmware build (dev 94.2 % of the image space, the others 89.2 %), `tests_hardware --collect-only`.
- Silicon (dev bench, 2026-11-11/12): heap, C-stack and send-stall margins, the 6 h HTTP soak `<10g>`, the clean
  build legs on Ubuntu 24.04 and Debian trixie `<k>`, the wear steps `<wear>`.
- Real-hardware items still owed are listed in BACKLOG.md's "Real-hardware work still owed".

## Records
The audit's records are not merged: they stay on `claude/u35-audit-archive` `<sha>`, beside
`claude/u35-bench-campaign` (bench evidence) and `claude/u35-int-backup` (integration history).

🤖 Generated with [Claude Code](https://claude.com/claude-code)

https://claude.ai/code/session_01BWfjT6GSD7bxCP57j86vB8
