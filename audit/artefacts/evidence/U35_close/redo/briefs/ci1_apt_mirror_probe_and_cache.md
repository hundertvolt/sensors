# CI1: CI's apt downloads leave a slow mirror and reuse cached packages (lead, 2026-10-27)
Read `S/u35r/briefs/redo_common.md` (all of it; "Quality comes first" and "Efficiency" are binding, and it says how
you hand back). Then:
- `S/u35/ci_apt/notes.md`, the investigation behind this lane;
- on your worktree: CLAUDE.md's bullets "A third party's momentary outage must never read as a red test result" and
  the zizmor bullet;
- `.github/workflows/ci.yml`: the four web jobs' Playwright steps (:160-210 and their three copies), the cross-browser
  job's toolchain cache (:425-440), and `firmware-build-verify` (:691-741);
- `.github/actions/*/action.yml`;
- `toolchain/setup_toolchain.py`'s `apt_options()` and `ensure_apt_packages()` (read only: it stays untouched);
- `scripts/setup_cross_browser_toolchain.sh`'s apt use;
- SPECIFICATION.md B.4, B.10/B.10.1, and Part N's rows `tool.apt_acquire_timeout_s`, `tool.uv_sync_attempts` and
  `ci.playwright_install_timeout_min`;
- `tests_scripts/test_ci_workflow.py`, and every reader of `@tunable` tags (find them).

Worktree and base: in your launch message. Logs go in `S/u35/laneD/ci1/`.

## The fault
Some azure.archive.ubuntu.com nodes serve `.deb` files at 45-130 kB/s, while serving the package index at about 9 MB/s.
Healthy nodes run at 30 MB/s or more. Which node a job gets is luck. apt's `Acquire::http::Timeout` fires only when no
data arrives at all, so apt never moves on to the next mirror, and each retry returns to the same node. This is upstream
actions/runner-images#14823, open since Sep 30.
- In `firmware-build-verify`, the 588 MB package set cannot finish inside any bound on a slow node: about 89 minutes at
  110 kB/s.
- The Playwright `install-deps` step, 25.9 MB, outlasts its 5-minute bound there.
Failing jobs: run 40570757608, jobs 122430825421 (wozi) and 122426649230 (web-coverage).

## The owner's decision (verbatim: "Yes do it like you proposed")
The design approved is this one:
- **(a) A per-job mirror check before apt downloads anything.** One small package from the set about to be fetched is
  downloaded with a short cap. If it does not finish at a healthy rate, the slow mirror is removed from the runner's
  mirror list (`/etc/apt/apt-mirrors.txt`), and apt uses the next mirror for the rest of the job.
- **(b) The downloaded packages cached in GitHub's cache.**
  - The key is built from the exact package versions apt is about to fetch (after `apt-get update`, from
    `apt-get install --print-uris`, or the equivalent for Playwright's list).
  - The restore uses the key's prefix as a fallback, so a changed version restores the previous entry and fetches only
    what changed.
  - The save is an explicit step that runs even when a later step fails.
- **(c) Integrity stays with Ubuntu's signature.** The index is downloaded fresh in every job, and apt checks each cached
  file against it, so a stale or altered file is fetched again and never installed. Verify that this holds for the way
  you restore the files. Say what you found.
- **(d) The cache-usage check comes first.**
  - Measure what the repository's caches hold now, for each key family and branch scope. Use the "Cache restored" and
    "Cache saved" sizes in the job logs; GitHub's cache API is not reachable from here.
  - Estimate the total with the new entries, against GitHub's 10 GB per repository with LRU eviction.
  - If the total stays under about 8 GB, cache the firmware job's full set. Otherwise cache only the large ARM
    cross-compiler packages, so the MicroPython Unix-port cache (444 MB) is never evicted.
  - The numbers and the choice go in your hand-back.
- **(e) One shared CI action replaces the four copies of the web jobs' Playwright and apt steps.** The firmware job uses
  the same check-and-cache mechanics for its package set. `scripts/setup_cross_browser_toolchain.sh`'s apt fetches get
  the same mirror check if they run on the same runner image; otherwise state why not.
- **(f) `toolchain/setup_toolchain.py` stays untouched,** so nothing changes on a dev box or the bench Pi. apt's
  archive folder belongs to root: CI steps copy the cached files in before apt runs, and copy new ones out afterwards.

## Items, in order (each committed green on its own)
1. **The mechanics as a tested host script.**
   - Put the logic in one host-side script under `scripts/` (Python is preferred, since pytest and the host mypy pass
     can then check it): the mirror check, the mirror-list edit, the key computation, and the copy-in and copy-out
     lists.
   - Every path is a parameter, so tests run on temporary files.
   - `tests_scripts/` gets its tests. Run a local throttled HTTP server and a fast one, and assert that the slow mirror
     is dropped and the fast one kept.
   - Also assert:
     - a list whose format the script does not recognise is left unchanged, with a warning;
     - the list is never emptied;
     - the key changes when a package version changes, and stays the same when the set is reordered;
     - a full cache hit skips the check.
   - Red first: each test is seen failing on a plant (the drop disabled, the order-sensitive key, the empty list
     allowed).
   - Real waits get an `@tunable` tag and a Part N row: the check's cap (about 10 s) and its rate threshold (about 1
     MB/s; healthy nodes run at ≥30 MB/s and slow ones at ≤130 kB/s). Mark both "estimated (agent, <date>) —
     measurement owed".
2. **The CI wiring.**
   - The shared action and the firmware job's steps. The runner's `apt-mirrors.txt` and the measured rate are printed
     into the job log, so the first run on a slow node shows the fallback mirror's speed.
   - Nothing in the check or the cache machinery may turn a job red on its own. A failed check, cache restore, save or
     list edit warns and carries on. Only the real install's own failure fails the step, as today.
   - The existing bounds stay as they are: `_APT_STEP_TIMEOUT_S`, `ci.playwright_install_timeout_min`, the jobs'
     limits.
   - Update Part N's tag counts and rows (`tool.apt_acquire_timeout_s`, `tool.uv_sync_attempts`,
     `ci.playwright_install_timeout_min`), plus B.4 and B.10.1's text where it states the mechanism.
   - Actions: `actions/*` may be tag-pinned and must match the versions already used (`actions/cache@v6`, including its
     `restore` and `save` sub-actions). Third-party actions are not allowed.
3. **Checks:**
   - `actionlint` and `zizmor --offline`, with zero findings (the zizmor policy is `.github/zizmor.yml`; do not change
     it);
   - shellcheck on any shell you touch;
   - ruff and the host mypy pass on a new Python script;
   - `tests_scripts/test_ci_workflow.py`, every `@tunable` reader, `test_comment_block_cap.py`, `test_citations`,
     `test_decision_vocabulary` and your new tests;
   - `lint_direct` and the three mypy passes;
   - the three audit checks.
   - This lane runs no twin or tier. CI itself cannot run here; the lead sees the first real run on the next snapshot.

## Notes
- Comment blocks are at most 3 prose lines. Text outside `audit/` cites no audit IDs. The decision tag is "(owner,
  2026-10-27)".
- Do not push, re-run or trigger anything on GitHub.
- Other lanes may add Part N rows. Keep yours in Part N's existing order, so the merge stays mechanical.
- CLAUDE.md's third-party-outage bullet, and a BACKLOG.md line if `scripts/` gains a file: write that text into your
  hand-back for the lead's D3r. Do not edit those two files.
- Run to the end; hand back early only as redo_common says.

## Hand-back (the file, per redo_common)
- Commits.
- The cache-usage numbers and the full-set or compiler-only choice.
- The design as built: steps, keys, and where each runs.
- Item (c)'s finding.
- Each test with its red-first evidence.
- What only a real CI run can confirm, so the lead can read it on the next snapshot's logs.
- The checks.
- The doc text for D3r.
- Last line: "nothing of mine is running".
