# R5 unit bchain: two build-chain costs far beyond their need, removed at their source (lead, 2026-11-09)

## Read first
`S/u35r/r1/common_r1.md` (binding; labels `bchain_`). S =
`/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad`. Then `S/u35r/r5/COMPLETE_2.md`
section 3 (the evidence), SPECIFICATION.md Part D.8 and E.2.1 and the `hardware_family` row (grep it), CLAUDE.md's
"Code quality tooling" bullets on `scripts/test.sh` and the GC stages, `scripts/_devices.sh`, `scripts/test.sh`,
`.github/workflows/ci.yml` (jobs `devices`, `unit-tests-gc-threshold`, `digital-twin-e2e`, `firmware-build-verify`),
`tests_scripts/_devices.py`, `tests/_twin_devices.py`, `tests_scripts/test_device_tomls.py:27-60`.

## Owner rulings behind this unit (verbatim)
- 2026-10-23 (the final description of how tests pick devices): "My words about not having tests arbitrarily fixed for
  specific configurations or devices still hold. They shall all be treated the same, only depending on their hardware
  configuration. But matrix deduplication is something different! If the pattern is like "the first device runs
  specific tests, which are always and guaranteed present and always identical for every device, fully independent from
  their configuration", and any device could be the first to be tested, then it is a good thing as it saves time and is
  not actually device specific." ... "So target minimal changes."
- 2026-11-07 17:57:27: "Go to all, be sure you really found all such occurrences, and it won't happen again."

## Your work (worktree `S/wt-bchain`, branch `audit/bchain` from int `b412d1b3`; create it; commit locally, never push)
1. The GC-threshold stage reruns the host `tests_scripts/` tier for an identical result (no host test reads
   `GC_THRESHOLD`; verify that first, by grep and by reading `tests_scripts/test_test_sh.py`'s handling). With
   `GC_THRESHOLD` set, `scripts/test.sh` skips that tier and its summary says so in one line. One condition.
2. Matrix deduplication by `hardware_family`: devices of one family differ only in `name` and `hostname` (pinned by
   `test_device_tomls.py`), so a run whose result cannot depend on those two takes one device per family; a device
   with no family is its own. Applies to the shell device list the runners share (`scripts/_devices.sh`), CI's
   `devices` job (which today re-derives the list in its own loop: prefer making it use the shared derivation over
   adding a second family rule), and through them the twin legs, firmware builds and per-device unit and scenario
   jobs. Which member stands for the family must not matter and is derived, never a literal (no device name outside
   `devices/`). Keep every-device coverage where it is cheap and is the guard of the family rule itself (the
   `tests_scripts` parametrizations, `test_device_tomls.py`). For each fan-out site, say in the hand-back whether it
   dedups and why.
3. Tests first (seen red on b412d1b3): a `tests_scripts` check that two devices of one family yield one entry in the
   shared list and a familyless device stays; the GC-threshold skip pinned in `test_test_sh.py`'s style.
4. Docs, current state, fewest lines: E.2.1 and the `hardware_family` row name the deduplication with the 2026-10-23
   ruling; CLAUDE.md's GC-stage bullets stay true (the (f) stage covers every MicroPython file; the host tier runs once);
   BACKLOG.md's running list of build-environment changes gets one entry (CLAUDE.md "Pull request workflow").

## Size
Expected: a few lines per site. If the change grows past about 60 changed lines outside tests and docs, stop and
report the form you found instead of building it.

## Never
Never weaken a product check; nothing in `src/` changes. Never read `arduino/`; never edit `ext/`; never open
`/root/.claude/`; no hardware. Credential filter on every view of SPECIFICATION.md, CLAUDE.md, `devices/` and generated
modules; never print, copy or write any Wi-Fi credential or the hotspot password.

## Checks
`lint_direct.sh` (shellcheck, actionlint, zizmor included), the three mypy passes, `uv run pytest` on the touched
`tests_scripts` files, then the gate as common_r1 says, under `S/u35/lead/heavy.lock` holding the line `bchain` (unit
bfix may hold it: wait while it exists; `rm` it, literal path, its own command, after). Report each stage's wall time
against 18e9d59c's last gate where a log exists (`S/u35/lead/*.log`).

## Limits and hand-back
Write only the files above and their tests. One commit. Budget about 1.5 % of the week. Hand back by 23:00 UTC:
`S/u35r/r5/HANDBACK_BCHAIN.md` (at most 30 lines, as common_r1 says, including need against cost per changed step),
your commit, one line per headline result, and last "nothing of mine is running".
