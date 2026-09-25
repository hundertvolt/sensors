# Harvest — UNSORTED: unsorted

What the project's own comments, docs and history already record for this area (snapshot `2a88cc8`).
Recorded, not verified or triaged; `audit/HARVEST.md` explains the kinds, tags and method.

Kinds: NOTE 5 — 5 items.


## Commit messages (chronological)

- **UNSORTED.N001** NOTE(OWNER) · `commits 12640c2, 6b47a98, 6b014dc, 0615eba, 58abf8f` — html_stub/
  retired; arduino/ out of scope; four heap research gaps "closed as not pursued"; R5 one more BMP3XX
  pass; "config repair writes stay bounded by boots"; four consistency decisions — Decisions. · tracked:
  BACKLOG / SPEC C.7.3 / HEAP §M8 | - · [H17]

## GitHub PRs and issues (hundertvolt/sensors)

- **UNSORTED.N002** NOTE(DOC-DRIFT) · `https://github.com/hundertvolt/sensors/pull/53` — "an end-to-end
  HTTP redirect check once hotspot mode is genuinely reached" — PR #53 added captive-portal
  `redirect("/")` (src/asy_webserver_service.py:658-660) but tests_hardware/manual/manual_wifi.py:40
  still says no HTTP redirect exists · UNTRACKED | - · [H17 (also H17)]
- **UNSORTED.N003** NOTE(DISCREPANCY) · `https://github.com/hundertvolt/sensors/pull/65` — "**One
  discrepancy found, deliberately not fixed:** `_digital_twin_ci_suite.py` suppresses its own S603 with
  an inline `# noqa`" — Inline vs central per-file-ignores S603 policy · covered-by: commit 454f6a2 item
  | related: 454f6a2 · [H17]
- **UNSORTED.N004** NOTE(PRE-EXISTING) ·
  `https://github.com/hundertvolt/sensors/pull/23#issuecomment-5067694240` — "`pyproject.toml` leaves
  `mypy` unpinned ... this run picked up **mypy 2.3.0**" — CI broke on unpinned tool drift · done (all
  tools pinned; CLAUDE.md "Code quality tooling") | related: PR #24 comment · [H17]
- **UNSORTED.N005** NOTE(RED-ACCEPTED) ·
  `https://github.com/hundertvolt/sensors/pull/64#issuecomment-5622193607` — "`lint-and-typecheck` will
  go green on this branch once the other three scope PRs land" — Four-way scope split merged red by
  design · done (eight scopes clean per CLAUDE.md) | related: PR #67 · [H17]
