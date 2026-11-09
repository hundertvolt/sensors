# R5 unit simpler: the complete look for simpler or more efficient forms that drop nothing (lead, 2026-11-09; read-only)

## Read first
`S/u35r/r1/common_r1.md` (binding; its "Standing direction" lines above all; labels `simpler1_` .. `simpler4_` by
pass). S = `/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad`. Tree `S/wt-u35int` at
f1a734f5, read only. Then SPECIFICATION.md Part 0 and D.8 (filtered), and what is already found and routed, never
redo it: `S/u35r/findings/FINDINGS.md` 12.96-12.122 (headings and routing lines), `S/u35r/r5/NEXT.md`, and the
tallies of `DESIGN_FU.md`, `LEVELS_1.md`-`LEVELS_3.md`, `STRETCH.md`, `COMPLETE_1.md`, `COMPLETE_2.md`, `CPRIM.md`.
Units writing now (their files may change; note overlaps, do not redo): crceng (`asy_crc_checks`, `asy_fram_manager`,
`asy_uart_*`, `asy_i2c_driver`'s `_bytes_to_int`, `asy_framing_codecs`, `buildgen/validate.py` poll rule) and weblog
(`asy_webserver_service`, `asy_print_log` reset, the five lock sites).

## Owner (2026-11-09 19:17:45, verbatim)
"Yes, but this is a pattern really meant general, not only CRC,  not just locks, not just timing. It's a general
principle to ask on  micro, intermediate and macro level if there might be a simpler or more efficient solution, still
having gaps closed (or ideally not even opened) and dropping no functionality at the same time. It sounds like
potentially contradictory requirements, but it is possible, we already had multiple success stories like that. So we
should have a complete closer look for such opportunities."
Success stories to measure against: the per-byte CRC yield gone by a native CRC (the cause removed, the mitigation
with it); bfix's FRAM hold fixed by removal (-149 lines); the CI's device loop replaced by the shared derivation.

## The question, at three levels
Micro (a function, an expression, a test), intermediate (a module, a mechanism, an integration between two modules or
tiers), macro (the system's structure, the test tiers, the build chain, the docs and the project's own apparatus).
For each candidate: is there a simpler or more efficient form that keeps every gap closed and drops no function? Look
above all for a mechanism that exists only to mitigate another one (remove the cause, the mitigation goes), two
mechanisms doing one job, a special case a general form covers, defensive code against a state that cannot occur,
work done more often or at a larger size than its consumer needs, and volume beyond need (tests pinning one fact many
times, docs stating one rule in several places).

## The four passes (one agent each)
1. Macro: the whole project's structure. Volumes as of f1a734f5: src 15,750 lines (29 files); buildgen 6,105;
   digital_twin 8,285; tests 106,667 (146 files); tests_scripts 56,743 (210); tests_hardware 26,701 (177); scripts
   12,737; toolchain 3,031; js 3,601; tests_js 12,012; SPECIFICATION.md 12,250; CLAUDE.md 879; README.md 1,268;
   PROJECT_AUDIT_PLAN.md 3,335; ci.yml 664. Product layering, the device-TOML generator, the four test tiers and the
   twin, CI's job graph, the docs' split. Where would one structure, tier or document do the job of two?
2. Firmware, intermediate and micro: every `src/` module and the generated modules (filtered), beyond the routed items.
3. Tests and twin: `tests/`, `digital_twin/`, `tests_hardware/` - duplicate coverage of one fact, tests pinning an
   implementation detail instead of a function, harness and fixture machinery beyond need, a tier testing what a
   cheaper tier already proves; never a gap opened (CLAUDE.md's four-tier bus-hazard rule and the GC stages stand).
4. Build chain, website and docs: `scripts/`, `toolchain/`, `buildgen/`, `tests_scripts/`, `.github/`, `js/`, `html/`,
   `tests_js/`, and SPECIFICATION.md, CLAUDE.md, README.md, BACKLOG.md as documents (one rule stated once, the rest
   pointing to it; CLAUDE.md citing the specification rather than repeating it).

## Every finding
Current form (file:line or doc section), the simpler or more efficient form, what goes (lines, states, mechanisms,
tests, RAM, CPU, CI minutes) and what stays, why no function drops and no gap opens (evidence: code, test, record), C
or I, origin (original 2026-07-13 / pre-audit / audit 10-06 to 10-28 / post-restart), and a flag where it would remove
a possibly unused feature (owner 2026-11-09 18:30:08: "Before removing any function which could be a feature which is
just unused, ask me") or touch an owner ruling (name it). No hypothesis is a finding. Rank by gain against risk.

## Never
Never edit any tree. No gate or whole-tier run (two writing units hold the host); single-file probes through
`S/u35/lead/run.sh` at most. No hardware. Never read `arduino/` (`':!arduino'` in every git grep and log); never open
`/root/.claude/`. Credential filter on every view or grep of SPECIFICATION.md, CLAUDE.md, `devices/`, generated
modules, `audit/` and `src/asy_wifi_service.py`; never print, copy or write any Wi-Fi credential or the hotspot
password. Scratch only under your own `S/u35r/r5/ftmp_simpler<pass>/`.

## Limits and hand-back
Write only `S/u35r/r5/SIMPLER_<pass>.md` (at most 60 lines; first line "simpler<pass> hand-back, written by the agent
(<date -u>)"; ranked; one line naming what was read and found clean). Budget about 1.5 % of the week each. Hand back
by 23:30 UTC: its path, one line per headline result, and last "nothing of mine is running".
