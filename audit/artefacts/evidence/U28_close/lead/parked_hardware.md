# U28 parked hardware items (nothing ran on hardware in U28)

Every round: the owner's go-ahead in its own conversation (CLAUDE.md); the FRAM-backed `errcount` and the raw FRAM saved
before anything writes (`fram_evidence_saved`); the lower levels L0-L2 at both GC stages first; the image record and
`board_image`; the standard board state at start and end. Session 1 (R0-R6) runs after U35, beside U36/U37, from
`audit/c/handover/HANDOVER.md` (owner, 2026-10-19; `audit/order/WORK_ORDER.md` 5 and 5.1); BACKLOG.md's two rows
"`env --tier bench` on the bench Pi4 once more" and "The default and the gated bench round over the files the tooling
consolidation touched" (`BACKLOG.md:440-469` at `3e87082`) are the durable text.

| round | item | what runs (U28 code it depends on) | markers and wear |
|---|---|---|---|
| R0 | H57 | `uv run toolchain/setup_toolchain.py env --tier bench` on the bench Pi4: its uv must equal `[tool.uv] required-version` (`==0.8.17`; any other uv refuses to sync), the Playwright step fatal under the bench tier; reads only | none (host only) |
| R1 | H73 | the default bench round: every runner runs `scripts/uv_sync_retried.sh` (the flash and bench runners after their lower levels); the device scripts whose comments P moved and the host files R and P edited, through the flash and bench tests that run them; dev's UART link naming a dropped frame (OF-159) | default run, wear gates off |
| R3 | H73 (gated) | `--allow-persistence-write` for `bench/test_hotspot_role_reversal.py`, `bench/test_system_commands_over_rest.py`, `flash/test_system_commands.py` (the ISL29125 envelope behind `--allow-neopixel-sweep`); `bench/test_uart_link_crc16.py` behind `--allow-flash-cycle` (its CRC16 image flashed, the standard one flashed back) | the gated run's budget plus two flash cycles |

Untouched and still parked: OF-70 (R2 [H37]), OF-183 (R1), U26's and U27's items. CI-only proofs (R-20) are not hardware:
they are read from the unit push's CI run (this record's CI section).
