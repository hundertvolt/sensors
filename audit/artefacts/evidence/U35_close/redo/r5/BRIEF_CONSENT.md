# R5 unit consent: what the audit added without the owner's consent and kept growing (lead, 2026-11-09; read-only)

## Read first
`S/u35r/r1/common_r1.md` (binding; its Standing direction, the bound rule with the tag sentence, the filter rule;
labels `consent1_` .. `consent4_`). S = `/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad`.
Tree `S/wt-u35int` (head 6aec784f), read only; the audit's start is `25caf528` (2026-09-25). Then, never redone, only
cited: `S/u35r/scan/REPORT.md` and `S/u35r/scan2/SCAN2.md` (the 10-28 scans; SCAN2 section 2 lists eight patterns,
`scan2/tools/census.py` built its function census), FINDINGS 12.96-12.138 (headings and routing lines),
`S/u35r/r5/GIVEUP_1.md`-`GIVEUP_3.md` and their ledgers (the bound family, done), `SIMPLER_1.md`-`SIMPLER_4.md`,
`BRIEF_B.md` and `BRIEF_FSYNC.md` (writing now: mark "in B" / "in fsync"), `NEXT.md`.
Consent sources: `S/u35r/recovered/owner_rulings_after_LN118.md` (verbatim since 2026-10-26) and, before it,
PROJECT_AUDIT_PLAN.md's OR records and decision lines quoting the owner (filtered; grep by topic, never read whole).

## Owner (verbatim)
- 2026-11-09 22:27:31: "Not "this" specific pattern, rather "similar patterns of what happened in the audit and was added
  without my consent and kept growing" Not to forget - don't drop real features and don't introduce or reintroduce
  gaps. Lean, functional, no losses, no gaps, efficient by smart design appropriate for limited devices like the rp2"
- 2026-11-09 18:30:08: "Before removing any function which could be a feature which is just unused, ask me"
- 2026-10-28 (SCAN2's request): "... real features, real findings inside the minimal code, rare but real cases all keep
  effective."

## Per mechanism (a mechanism = one addition and everything that exists only because of it)
- Consent: the owner's own words asking for or accepting this mechanism or its form (quote, date). Not consent: an
  "(agent, date)" decision; "owner-reviewed, 2026-11-06" (topic level: "Single decision is by far to fine grained");
  an owner's general principle applied by an agent to a case found by reading (SCAN2 pattern 8); a "decided under the
  owner's direction" line; an agent-written rule in a document that reads as standing.
- Need: demonstrated (a test reproducing the failure against the real mechanism, a bench or CI incident with its
  record, a datasheet statement, legacy field behaviour) / inferred (reading only) / none.
- Growth: commits touching it since it appeared (`git log -S`/`-G`, `':!arduino'`), lines then and now, and what it
  seeded: catalog codes, /status keys, tunables and Part N rows, JS fields, tests, spec text, rules.
- Verdict: KEEP (consented, or a demonstrated need met at its size) / SIMPLIFY (need real, form beyond it: give the lean
  form) / REMOVE (no consent and no demonstrated need, or its cause is gone: it and all it seeded) / ASK (possibly a
  real feature, user-visible behaviour, or an owner ruling touched) / ROUTED (cite B, fsync, a GIVEUP or SIMPLER row).
  Every SIMPLIFY and REMOVE states: the feature check (not a legacy top-level feature, not owner-ruled, not API that
  completes a driver, OR36.a (3)); the gap check (the failure it guards, its evidence, and how it stays closed after:
  cause removed, or a remaining mechanism, with the test that pins it); the rp2 effect (bytecode, RAM, CPU per
  operation, where product); what goes, in lines. Group ASK items by family, so the owner gets few questions.

## Families to recognise (examples, not limits)
SCAN2's eight patterns; bounds on inside waits (GIVEUP); a mitigation of a self-made cost (per-byte CRC yield,
per-command FRAM lock and yield, writer tasks to keep a lock short); authority labels (the 11-06 tag on a number, an
owner credit in a comment with no ruling behind it); tunables nobody tunes; product hooks for tests (OR36.a (1));
tests pinning an implementation detail one site at a time; one rule stated in several documents; an agent-written
"standing" rule that forces growth elsewhere (SCAN2: "Retired numbers are never reused", agent text).

## The four passes (one agent each)
1. Firmware: `src/`, the generated modules (filtered), buildgen's product rules (validate, tunables, signal catalog).
2. Website and build chain: `js/`, `html/`, buildgen host code, `scripts/`, `toolchain/`, `.github/`, tool config.
3. Tests and twin: `tests/`, `digital_twin/`, `tests_hardware/`, `tests_scripts/`, `tests_js/`.
4. Documents and rules: SPECIFICATION.md, CLAUDE.md, README.md, BACKLOG.md, UART_C_PORT_CHANGELOG.md, `.claude/skills/`,
   PROJECT_AUDIT_PLAN.md's standing rules (rules only), device TOML comments: each rule's source and the growth it forces.

## Completeness
Enumerate mechanically from `git diff 25caf528 6aec784f -- <scope>`: added files, definitions, constants, catalog
codes, tunables, config and /status keys, CI jobs, document headings and rule sentences (must, never, always, every).
Every added item maps to one mechanism row or to NOTMECH. Ledger `S/u35r/r5/CONSENT_<pass>_ledger.tsv`: mechanism,
sites, consent quote or none, need, growth, verdict, origin commit - no source text. The hand-back states the
commands, the counts, and that items = items mapped and mechanisms = ledger rows = the sum by verdict.

## Never
Never edit any tree. No runs but git, grep, read-only text tools and `scan2/tools/census.py` on git output: no gate,
test, probe or build (two writing units hold the host). No hardware. Never read `arduino/`; never open `/root/.claude/`.
Credential filter on every view or grep of `src/asy_wifi_service.py`, generated modules, `devices/`, SPECIFICATION.md,
CLAUDE.md, PROJECT_AUDIT_PLAN.md and `audit/`; print only identifier matches where a hidden line decides a claim; never
print, copy or write any Wi-Fi credential, the hotspot password, or a credential-scan pattern. `python/` and `legacy/`
are read for comparison only. Scratch only under `S/u35r/r5/ftmp_consent<pass>/`.

## Limits and hand-back
Write only `S/u35r/r5/CONSENT_<pass>.md` (at most 60 lines; first line "consent<pass> hand-back, written by the agent
(<date -u>)"; REMOVE and SIMPLIFY ranked by gain against risk, then ASK by family; one line naming what is KEEP and
clean) and its ledger. Budget about 1.5 % of the week each. Hand back by 03:30 UTC: its path, one line per headline
result, and last "nothing of mine is running".
