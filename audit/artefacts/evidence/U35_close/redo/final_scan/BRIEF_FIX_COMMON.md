# Final fix round: common brief for every lane (read all of it first)

S = /tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad

## Context
A final, verified scan of the release (`S/u35r/final_scan/FINAL_SCAN.md`; per-area reports `FWA.md`, `FWB.md`,
`BUILD.md`, `TESTS.md`, `DOCS.md`, `DECISIONS.md`; verifications `V_*.md`) found small leftovers, and the owner took
five decisions today (verbatim, in `S/u35r/recovered/owner_rulings_after_LN118.md`, entries 2026-11-13 11:56 to
12:11). You implement your lane's items, nothing else. Read `S/u35r/final_scan/BRIEF_COMMON.md`'s "The owner's
rulings" and "Safety rules" sections: the rulings are your yardstick and the safety rules bind you, with one change:
you MAY edit files and commit inside YOUR OWN worktree (below). Everything else stays read-only.

## The rules for this round (owner's words, binding)
- "all gaps closed, (really) agreed on features implemented, and from there on minimal, efficient and lean changes."
- "Minimal complexity, no dropped features, no known or new gaps, and no runaway fixing chains, and don't drift into
  fixing tests, concentrate on the quality of the firmware and the buildgen."
- "prefer to keep existing, working tests, i would not like something removed which is good." and "as long as they
  don't block anything and do real good, it's ok". So: change a test only where your change makes it wrong; remove a
  test only when it exercises nothing but code you removed. Never weaken a product check.
- "Before removing any function which could be a feature which is just unused, ask me" - your items were already
  decided; do not remove anything beyond them. If you think something else should go, write it in your report.
- No chains: if an item turns out bigger than its brief says, or needs a change outside your lane's files, stop that
  item and report it instead of widening.

## How to work
- Your worktree: `S/wt-<lane>` on local branch `final-<lane>`, at release head 590cffcf. Edit and commit only there.
  Never push. Never touch another worktree, `ext/`, `arduino/` (never read it either), or the legacy tree.
- Commits: one or a few, message via `git commit -F <file>` (write the file in `S/u35r/final_scan/`), ending with:
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` and
  `Claude-Session: https://claude.ai/code/session_01BWfjT6GSD7bxCP57j86vB8`.
- Repo text conventions: every comment or docstring block at most 3 prose lines; no audit IDs in repo text (no OR/U/LN
  numbers, no FWA-/DOCS-/BUILD- ids, no "audit" lane words); docs state current state and rules, not history. A
  decision record quotes the owner: `(owner, 2026-11-13: "...")`; an agent's own choice is `(agent, 2026-11-13)`.
- The UART wire format, its constants and timings are untouched. A Python-internal UART change gets a "no C impact"
  line in `UART_C_PORT_CHANGELOG.md`.
- Filter every view or grep of repo text through `grep -v -i -E "hotspot|passw|psk|ssid|wificonfig|credential"`;
  never view whole `devices/*.toml`, generated modules, `SPECIFICATION.md`, `CLAUDE.md`, `BACKLOG.md`, `README.md`,
  `src/asy_wifi_service.py`. Edit those files only with targeted edits on lines you have read (filtered); a line the
  filter hides is unread - never edit around it blind.

## Running checks (no network; never `uv sync`, `npm install` or a toolchain setup)
- Wrapper: `bash S/u35/lead/run.sh S/wt-<lane> <label> "<command>"` runs the command inside your worktree, offline,
  with the shared venv and Node; output goes to `S/u35/lead/<label>.log`. Use labels starting with your lane name.
- Generated inputs first: `bash S/u23/rebuild.sh S/wt-<lane>` (device modules, frozen website, device sites).
- Lint + the three mypy passes + chosen pytest files: `bash S/u35/lead/checks.sh S/wt-<lane> <label> <readers_file>`,
  where `<readers_file>` lists the tests_scripts/ test files to run, one per line.
- MicroPython tests: `PICO_TOOLCHAIN_DIR=S/tc-c`. A single file: see how `scripts/test.sh` prepares
  `build/portable_src`/`build/generated_src` and the MICROPYPATH (`scripts/_unix_port.sh micropypath unit`, binary via
  `scripts/_unix_port.sh unix_port_bin standard`), and run your touched test files that way, at the default and with
  `GC_THRESHOLD=32768`. The full suite is `scripts/test.sh` (about 20-40 min).
- Port-binding runs (any MicroPython or twin test, `scripts/test.sh`, `npm test`/`npm run test:unit`) must never
  overlap with another lane's: wrap each one as `flock S/u35r/final_scan/ports.flock bash S/u35/lead/run.sh ...`.
  Lint, mypy and plain pytest of non-port files need no lock.
- A red in a test you did not touch and whose code you did not change: record it in your report, do not fix it.

## Your report
Write `S/u35r/final_scan/R_<lane>.md`: per item - done / stopped (why) - files touched with +/- lines, the checks you
ran and their results, anything you noticed but did not do. Final message: a short table, item | status | +/- lines |
checks, at most 25 lines.
