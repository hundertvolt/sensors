# Final bird's-eye scan: common brief (read this first, all of it)

S = /tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad

## What this is

The project (MicroPython 1.29 firmware for RP2040 sensor units, plus `buildgen/` which generates each device's
firmware module from `devices/*.toml`, plus a website, tests and tooling) went through a long audit, 2026-09-25 to
2026-11-13. The audit drifted badly from 2026-10-06 on and was restarted on 2026-10-28; cleanup rounds since then
aimed at one target state:

> Each module is the pre-audit code, plus the owner's foundations, plus the smallest fix for each confirmed gap, plus
> the owner's decided features in their smallest form, plus the rare-but-real cases worth keeping, plus what is proven
> good in its leanest form. Everything else goes (and stays only as knowledge in the archived records).

The owner now asks for a final, global, bird's-eye scan by fresh eyes: **do the owner's rulings hold across the
release, and are all leftovers of the drifts and mistakes cleaned out?** This is a READ-ONLY scan. You fix nothing.

- Release head (what you scan): `S/wt-final` (detached worktree at `590cffcf`). Do not modify anything in it.
- Pre-audit baseline: commit `25caf528` (origin/main is its parent; same code). Compare with
  `git -C S/wt-final diff -M 25caf528 HEAD -- <paths> ':!arduino'` (rename detection matters: many files were renamed
  `x.py` -> `asy_x.py`).
- The audit's own records were removed from the release; they live on branch `origin/claude/u35-audit-archive`. You
  do not need them; use them only for a targeted, filtered lookup.

## The owner's rulings (the yardstick)

Read, filtered (see Safety), as needed:
- `S/u35r/picture/PICTURE.md` - the big picture: sections 1-3 (the concept and the eight lines L1-L8) and section 4
  (the drift's leftover categories M1-M10).
- `S/u35r/drift/DRIFT.md` - how the drift happened (sections "The short answer", 2.6, 2.7, 2.9).
- `S/u35r/recovered/owner_rulings_after_LN118.md` - the owner's verbatim words, in time order, 2026-10-23 on.

**General precedence (owner, 2026-11-10):** "if there are decisions into a different direction which are clear and
came in later, the more recent ones supersede the older ones." An earlier rule with weak backing (written by an agent,
or a promotion-session instruction) yields to a later clear owner decision. Only the owner's own words are decisions;
agent-written text is a proposal unless the owner adopted it.

The rulings that matter most here (verbatim):
- 2026-11-07: "all gaps closed, (really) agreed on features implemented, and from there on minimal, efficient and lean
  changes."
- 2026-11-07: every part, pre-audit code included, is judged by "is that reasonable, is that minimal and efficient for
  the intended function, could the same outcome be implemented leaner without losing anything". The agreements apply
  "on function, module, import, integration and upstream and downstream, and full system".
- 2026-11-09: "minimal and optimal at the same time through smart design" - remove the cause so the mitigation built
  around it can go; "a general principle to ask on micro, intermediate and macro level if there might be a simpler or
  more efficient solution, still having gaps closed (or ideally not even opened) and dropping no functionality".
- 2026-11-09: "Before removing any function which could be a feature which is just unused, ask me". Also (10-23):
  "Always regard the modules as libraries, not every feature must be immediately used, as long as it is a real
  feature". Small per-module default-value helpers stay (they keep a module self-contained).
- 2026-11-02: "nothing proven good shall be removed, but checked if it can be leaner"; "no knowledge may be lost".
  Proven good = fixes/prevents an observed or reproduced failure, measurably improves the device or build, or the
  owner approved it.
- 2026-10-28: "building upon hypothetical findings is a clear no-go"; "Hypothetical findings which are suspicious to be
  real need to be verified". A free bound by construction (a capped counter, no growing long-lived allocation) is
  wanted; a MECHANISM (task, timer, flag, fallback, retry, timed check) for a trigger nobody observed is not.
- 2026-11-11: "address the root causes of issues, not something derived over multiple steps" - no runaway chains.
- 2026-11-11: "Minimal complexity, no dropped features, no known or new gaps, and no runaway fixing chains, and don't
  drift into fixing tests, concentrate on the quality of the firmware and the buildgen."
- 2026-11-11: "be careful with such negative tests. they are extremely prone to become overkill."
- 2026-10-28: "The unit tests shall have good quality, but don't need deep dives. The audit verification machinery is
  just a temporary tool." OR36: "zero artifacts specifically added for testing" in the product. OR20 (twin/test code
  in rigs): "Only if there is no alternative, and keep tiny anyway".
- One mechanism at the layer that owns the fault; beyond it the existing ladder (task ends, supervisor restarts it,
  reboot, hardware watchdog) carries it. Containment code beyond the ladder is not wanted. One shape per job.

The pillars P1-P12 (the device concept): P1 unattended indefinitely, nothing drifts or saturates; P2 handles
everything inside at the right layer; P3 layered fallbacks up to reboot/watchdog; P4 premium code, one material,
nothing in the product for tests; P5 proven by tests that bite; P6 efficient and compact on low-end hardware; P7
evidence survives; P8 one source of truth, generated not copied; P9 least wear; P10 extensible without edits
elsewhere; P11 grounded and traceable, only the owner's words are decisions; P12 contracts at boundaries.

## Already decided - do NOT raise these as findings

The hardcoded hotspot fallback credential (accepted risk; never mention or print it); `modules/_boot.py`; the whole
legacy tree (`python/`, `modules/`, `legacy/`, `build-*.sh`) is reference-only and never a to-do; `ext/` is vendored
and hands-off; the watchdog as backstop for a wedged I2C bus and the Wi-Fi false positive (no I2C timeout mechanism);
the Wi-Fi behaviour as built; the FRAM per-owner CRC seed; the C-stack reboot; the boot-confined `gc.collect()`
placement reset and `gc.threshold(32768)`; `dev`'s bench-only quirks; the UART wire format (Class A changes need the
changelog); CI's `uv sync` retry and the hang backstops in CLAUDE.md; the native CRC engine. If you think one of these
is wrong, say so in one line under "Notes", not as a finding.

Before reporting anything as a leftover, look for a decision on it: grep the rulings file and
`S/wt-final/BACKLOG.md` / `SPECIFICATION.md` (filtered) for the item's name. Report what you found ("owner decision
2026-xx-xx: '...'", or "none found").

## What counts as a finding (classes)

- **L - leftover**: code/doc/test that exists because of the drift or a mistake and does not fit the target state:
  a mechanism built on a hypothesis; a cascade (an addition that protects another addition); hardcoded timed checks;
  per-episode log flags; typing-only guards; the same contract copied into several modules instead of one place;
  test needs inside the product; audit machinery; agent text bound as a rule; dead code. Say what is smaller.
- **G - gap**: a known gap left open or reopened, or a new gap a cleanup introduced (a real failure path, verified by
  reading the code path end to end).
- **F - feature**: an owner-agreed feature missing, broken or dropped.
- **R - ruling conflict**: code or a standing doc rule contradicts a later owner ruling (for example a superseded or
  agent-written rule still binding).
- **E - efficiency/design**: a clearly leaner design for the same outcome with nothing lost (the 11-07/11-09 lens),
  only when the gain is clear, not marginal.

**Evidence standard.** Every finding cites `file:line` in `S/wt-final` and states what you verified by reading
(VERIFIED) versus what you suspect (SUSPECTED). A suspicion of a failure must name the concrete trigger; "could
theoretically" is not a finding. Do not propose new machinery, new tests or test fixes; the fix you name is the
smallest change at the root (usually a deletion or a merge into an existing place). No chains: if a finding would only
exist because of another, report the root one.

**Bird's eye.** Look at the shape first (what was added since the baseline, what each addition is for, whether it
earns its place), then read code where the shape is suspicious. Do not review line by line for style. "Nothing found"
for an area is a valid and useful result; say so. At most 15 findings, most important first. Quality over count.

## Safety rules (binding, no exceptions)

- READ-ONLY: no edits to any repo file, no commits, no pushes, no git stash, no builds, no test runs, no network, no
  hardware tools (mpremote, picotool, nmcli, iw, iptables). Write only your report file.
- Filter every view or grep of repo text through `grep -v -i -E "hotspot|passw|psk|ssid|wificonfig|credential"`.
  Never print a password, key or Wi-Fi credential, and never write one into your report. A line hidden by the filter
  is unread: never treat it as evidence that something is absent.
- Never view whole (filtered excerpts only): `devices/*.toml`, generated modules, `SPECIFICATION.md`, `CLAUDE.md`,
  `BACKLOG.md`, `README.md`, `src/asy_wifi_service.py`.
- Never read anything under `arduino/`: add `':!arduino'` to every `git grep`, `git diff` and `git log`. Never open
  anything under `/root/.claude/`. Never read agent `.output` files.
- Bound every recursive grep with an explicit path list and `timeout 60`.
- In your report quote at most one line of code at a time; cite `file:line` instead of copying code.

## Your output

Write `S/u35r/final_scan/<YOUR_ID>.md`:

```
# <YOUR_ID>: <scope>
## Verdict (3-6 lines): do the rulings hold in this scope; are drift leftovers gone?
## Shape since the baseline (a few lines: what was added/removed and what it is for)
## Findings (most important first, max 15)
### <ID>-1 [class L/G/F/R/E] [VERIFIED|SUSPECTED] <one-line title>
- Where: file:line (and others)
- What: ...
- Ruling/pillar it meets: ...
- Decision record: ... | none found
- Smallest fix: ... (if it removes something that could be a real feature: "owner must decide")
## Checked and clean (one line each)
## Notes (anything else, one line each)
```

Your final message: the verdict plus a one-line list of finding titles, at most 20 lines.
