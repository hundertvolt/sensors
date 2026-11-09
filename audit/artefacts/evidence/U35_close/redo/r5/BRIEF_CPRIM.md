# R5 unit cprim: every Python loop the platform does faster, and every poll beyond its event, found and sized (lead, 2026-11-09; read-only)

## Read first
`S/u35r/r1/common_r1.md` (binding; its "The platform first" lines above all; label `cprim_`). S =
`/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad`. Tree `S/wt-u35int` (int b412d1b3;
read only). The pinned MicroPython source: `S/tc-int/micropython` (v1.29.0; rp2 enables the Thumb native emitter,
`binascii.crc32` and `deflate`; mpy-cross gets `-march=armv6m` for rp2's frozen modules). Then
`S/u35r/r5/STRETCH.md` (the silicon factor: the board runs this code ~130-190x slower than the Unix port) and the lead's
CRC probe `S/u35/lead/probes_20261109/crc_chip.py` with its host output in `S/u35/lead/lead_crcchip2.log`.

## Owner (2026-11-09 17:33:38, verbatim)
"Micropyhton has a C implementation for CRC which can replace the existing modules? Finding such cases absolutely *is*
the spirit, just wondering why now is the first time you stumble upon that, while I was asking many times throughout
the process to explcitly use such optimizations"

## Your work
1. Every loop in `src/` (and the generated device modules, read filtered) that does per-byte, per-bit, per-element or
   arithmetic work: CRCs (8, 16, 32), COBS and other codecs, the VOC port, JSON or string building, hex or base64,
   buffer copies and searches, sums and scans. Per site: what it computes; its worst-case input; its cost (a Unix-port
   probe under your `ftmp_cprim/` through `S/u35/lead/run.sh`, times the silicon factor, or a bench figure where one
   exists); the C primitive or native-code form that gives the identical result; the constraints (a value on a wire,
   in FRAM or in a peer's code - a changed value is a format or protocol change, UART CRCs are a C-side contract; a
   same-value faster form is internal); lines added and removed. Rank by silicon cost times frequency.
2. The native emitter as a project mechanism, from the pinned source and the current MicroPython docs: does a
   `@micropython.viper` function freeze into rp2's image and run (persistent native code, the arch flag); does it run
   under both Unix-port test binaries (`build-standard`, `build-settrace`) and the twin; what ruff and the three mypy
   passes say about viper's names (`ptr8`, `uint`) with the repo's stubs, and the smallest clean way through; what
   viper cannot do that the sites need. C (confirmed) or I (inferred) on each.
3. Every poll, wait or retry loop in `src/` (a loop around `sleep`/`sleep_ms`, a status read, a ready check, a
   counter): per site, the event it waits for and that event's physical time (datasheet, protocol, measured), the poll
   step, and so the reads or rounds per operation at the worst configuration a user can set (e.g. BMP3XX at x32/x32:
   ~130 ms conversion polled every 2 ms, ~65 bus reads where one read after the datasheet's computed conversion time
   would do - owner 17:35:55: "major overkill"). Any count far beyond one or two per event is a finding.
4. Why the reviews missed each site, from git and the docs only (the commits that touched it, what their review
   checked): one line per site, no speculation.

## Never
Never edit any tree. No gate or whole-tier run (bfix and bchain hold the host); single-file probes only. No hardware.
Never read `arduino/` (`':!arduino'` in every git grep and log); never open `/root/.claude/`. Credential filter on every
view or grep of SPECIFICATION.md, CLAUDE.md, `devices/`, generated modules and `audit/`; never print, copy or write any
Wi-Fi credential or the hotspot password.

## Limits and hand-back
Write only `S/u35r/r5/CPRIM.md` (at most 60 lines, ranked, C/I marks, file:line) and scratch under
`S/u35r/r5/ftmp_cprim/`. Budget about 1 % of the week. Hand back by 19:45 UTC: the path, one line per headline
result, and last "nothing of mine is running".
