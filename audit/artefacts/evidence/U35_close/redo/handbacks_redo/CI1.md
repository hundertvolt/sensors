CI1 hand-back, written by the lane (2026-10-27 22:43 UTC)

Worktree S/wt-u35ci, branch audit/u35-ci, base 4adf28a6. Logs: S/u35/laneD/ci1/. Not pushed.

## Commits
- `bd004254` item 1: `scripts/ci_apt_cache.py` (new, 100755, stdlib only, never needs root) + `tests_scripts/test_ci_apt_cache.py`
  (new, 16 tests) + 4 Part N rows (`ci.apt_mirror_probe_cap_s` 10, `ci.apt_mirror_min_bytes_per_s` 1000000,
  `l0.apt_mirror_probe_test_cap_s` 0.5, `l0.apt_mirror_probe_stall_test_cap_s` 2.0; all "estimated (agent, 2026-10-27) —
  measurement owed"). Checked green on its own with the item-2 files out of the tree. (Rebuilt once: the first tier run
  found `sys.exit(main())` against test_host_cli_exit_idiom's `raise SystemExit(main())`; fixed in item 1, item 2 reapplied.)
- `3b9b2e72` item 2: three composite actions (`.github/actions/apt-cache-restore`, `apt-cache-save`,
  `playwright-chromium`), ci.yml wiring, `test_ci_workflow.py` rules, B.4/B.10/B.10.1 text, Part N rows
  `tool.apt_acquire_timeout_s`, `tool.uv_sync_attempts`, `tool.apt_step_timeout_s` (gained a site), `ci.playwright_install_timeout_min`.

## Cache usage (d), measured from run 40570757608's logs (MCP get_job_logs; the cache API and gh's log download are refused here)
- Scope: every run since 2026-10-13 is a pull_request run of PR #107 (`refs/pull/107/merge`); the push twins are cancelled
  by the concurrency group, main has no run since before 2026-10-13, so its entries are past GitHub's 7-day eviction.
- unix-port-Linux-<ident>-<hash>: 444 MB (465,719,496 B) a key. Key inputs (git history of the three toolchain files at the
  run heads): 3 distinct hashes used in the last 7 days (Oct 20 23:05-Oct 21, Oct 22, Oct 27) -> at most 1.33 GB.
- playwright-chromium-Linux-330f9b489af43254-<lock>: 271 MB (284,182,583 B); package-lock.json unchanged all window -> 1 key.
- node-cache-Linux-x64-npm-<lock>: 35 MB (36,784,391 B), 1 key.
- cross-browser-firefox-Linux-<script hash>-2026-10: 253 MB (265,623,296 B); script hash changed Oct 20/21 -> at most 2 keys
  (the older last used ~Oct 20 23:05, expiring about now).
- Today: at most ~2.4 GB (the keys seen in today's logs alone: ~1.0 GB). New entries: apt-firmware 588 MB (587,835,714 B,
  from the noble index: the six ARM packages 574,196,676 B, libstdc++-arm-none-eabi-newlib alone 463 MB; the other six
  13.6 MB), apt-playwright ~26 MB (25.9 MB set). Total with one new key each ~3.0 GB; worst case with two keys of each
  new family (1.2 GB) and a main-scope copy after the merge (~1.6 GB): ~5.2 GB, under 8 GB.
- Choice: FULL SET for the firmware job (the compiler-only set would save 14 MB of 588, 2.3 %). The Unix-port entry is not
  at eviction risk at these totals.

## Design as built
- `apt-cache-restore` (firmware-build-verify directly; playwright-chromium for the four web jobs), every step
  `continue-on-error: true` and warning on its known failures:
  1. `timeout 150 sudo apt-get -o Acquire::Retries=2 -o Acquire::http(s)::Timeout=30 update` (tags tool.apt_step_timeout_s,
     tool.apt_acquire_timeout_s, tool.uv_sync_attempts), non-fatal.
  2. plan: package list = input `packages`, or Playwright's own via `npx playwright install-deps --dry-run <browser>`
     (1.63 prints "Missing system dependencies (N):" from its `apt-get install -s` Inst lines; read after the update);
     `apt-get -qq --print-uris -o Acquire::ForceHash=SHA256 install -y --no-install-recommends <list>` (no root: apt opens
     the cache without a lock for Print-URIs, apt-private/private-cachefile.h); `ci_apt_cache.py plan` writes
     `$RUNNER_TEMP/apt-cache-<family>/manifest.json` and key `apt-<family>-Linux-<sha256 of sorted "file size sha256" lines>`,
     restore prefix `apt-<family>-Linux-`.
  3. `actions/cache/restore@v6`, path `~/.cache/apt-archives/<family>`, `restore-keys` = the prefix.
  4. copy-in: `ci_apt_cache.py copy-in` lists (NUL) the cached archives whose size AND SHA-256 match the manifest; `xargs -0
     sudo cp -t /var/cache/apt/archives/`; a failed copy empties the list, which forces the check.
  5. check: skipped when every planned archive was restored (unless `always-check`); probe target = the smallest remaining
     mirror-served archive of at least cap x rate = 10 MB, else the largest; each mirror of /etc/apt/apt-mirrors.txt in apt's
     order (priority, methods/mirror.cc) is read for at most that budget with each read waiting only the time left to the
     10 s cap; the first healthy mirror stops the probing; every mirror ahead of it is dropped; with none healthy the fastest
     measured goes first; all refused -> unchanged; any line not `http(s)://... [TAB priority:N]` -> unchanged + warning.
     The list, each probe (bytes, seconds, kB/s, verdict) and a `::warning::` on a drop go to the job log; the new list is
     `sudo install`ed beside the old one and `mv`ed over it (a failed write never leaves a cut list).
- `apt-cache-save` (if: !cancelled(), right after the install): `copy-out` copies each planned archive apt fetched whose
  SHA-256 matches into the cache folder, prunes files the set no longer holds, `complete=true` only for the whole set;
  `actions/cache/save@v6` when complete and the restore was not an exact hit.
- `playwright-chromium`: ident step (identical text to the toolchain action's), browser cache (key unchanged), the
  `80-bounded-downloads` drop-in plus `apt-config dump` of the effective values, apt-cache-restore (family playwright,
  playwright-deps chromium), ONE install step (miss: `install --with-deps chromium`, hit: `install-deps chromium`) under
  `timeout "${limit_min}m"` with the tag (a composite step takes no timeout-minutes), apt-cache-save.
- firmware-build-verify: `apt-packages` step (continue-on-error) reads `versions["toolchain"]["apt_packages"]` exactly as
  the install step does; restore; the unchanged install step; save. setup_toolchain.py untouched.
- web-cross-browser-smoke passes `always-check: 'true'`: setup_cross_browser_toolchain.sh runs on the same runner after the
  action, and its WebKit packages (43.4 MB on run 40570757608) come from the same mirror list; Edge comes from
  packages.microsoft.com, outside the list. The script itself is unchanged (it also runs on dev boxes with no mirror list).

## Item (c) finding
apt does NOT check a pre-placed archive's content: in apt 2.8.3 (the runner's noble-updates apt; source from
archive.ubuntu.com's apt_2.8.3.tar.xz) and 2.7.14 alike, `pkgAcqArchive`'s constructor (apt-pkg/acquire-item.cc:3495-3512 in
2.8.3) marks a file in Dir::Cache::Archives Complete when `st_size == Version->Size`, no hash; a size mismatch is deleted
and re-fetched; a stale version has another file name and is ignored. So "apt checks each cached file against the index"
holds for size only; a same-size altered file would reach dpkg. As built, copy-in checks every cached file's SHA-256
against the hash `--print-uris` prints from the freshly updated, signature-checked index (`Acquire::ForceHash=SHA256`,
since Print-URIs otherwise forces MD5Sum: private-install.cc:157-161), so a stale or altered file is never copied in and
apt fetches it; copy-out stores only SHA-256-verified files. Integrity therefore stays with Ubuntu's signature.

## Tests, each seen red on a plant in a scratch copy (logs bite/…, bites2.log, bites3.log, wfbites1-3.log)
test_ci_apt_cache.py (16): slow-dropped/fast-kept <- P1 drop disabled, P12 file order instead of priority; healthy-first
unchanged <- P13 probing past the first healthy; redirect followed / HTTP error not healthy <- P9, P1; unknown form
unchanged + warning (4 forms) <- P5 bad URI skipped, P5b unknown tag ignored; never emptied (all slow keeps the fastest,
lone slow and all-refused unchanged) <- P3 empty list allowed, P1; full hit skips unless forced <- P4 skip removed,
P4b `have` ignored, P1; probe never outlasts its cap <- P6 read waits a whole cap (3.01 s vs bound 2.5); key order-free and
version-sensitive <- P2 unsorted lines; SHA-256-less lines never cached / path-like names refused <- P10; copy-in needs
size and SHA-256 <- P7 size-only; copy-out prunes <- P11, P7; dry-run reader <- P8 count unchecked; CLI chain <- P1, P4b.
test_ci_workflow.py (rewritten 2, new 3): W1 a job installing Playwright itself, W2 the bound step made conditional
(first passed: the rule then gained the bound step's no-`if:` check; red after), W2b drop-in not written, W3 install
without `timeout`, W3b install continue-on-error, W4 ident text drift, W4b key without ident, W5 save not right after the
install, W6/W6b save without `!cancelled()`, W7 smoke not forced, W8 restore/save paths differ, W8b packages not wired
from the list step, W9/W9b a machinery step without continue-on-error, W10 two actions/cache tags. All red.

## Findings for the lead
1. DECISION FOR THE LEAD (no change made): on runner image ubuntu24/20261012.334 the image's own
   /etc/apt/apt.conf.d/zz-retries (Acquire::Retries 1, http(s) Timeout 15 on x64; runner-images configure-apt.sh at that
   tag, identical to main) sorts after our `80-bounded-downloads`, and apt keeps the last value read, so the web jobs'
   drop-in has not been in force: Playwright's apt calls run with 1 retry/15 s, not 2/30 s. The installer's and
   apt-cache-restore's `-o` options win over both. Options: rename the drop-in to sort last (e.g. `zzz-…`: makes the
   documented 30 s/2 effective, an effective raise from the image's 15 s/1, so not mine to make), or drop it and document
   the image's values. B.10.1 and Part N now state the override; the action prints `apt-config dump` so the next snapshot's
   log shows the effective values.
2. Deviation, stated: "one small package with a short cap" is built as a byte budget (cap x rate = 10 MB) read from the
   smallest archive at least that large, else the largest, so "healthy" is exactly "the budget inside the cap" and slow
   start on a far mirror does not decide the verdict; on the firmware set that is cmake (11.2 MB), on Playwright's the
   largest (fonts-wqy-zenhei 7.5 MB). Healthy probes take well under a second.
3. Deviation, stated: the two Playwright install steps became one step (same 5-minute bound per path) because a composite
   step takes no timeout-minutes; the bound moved from the runner's step timer to `timeout`.
4. Silent-failure scan (classes 1-7, mode "Twin and tooling" incl. offline run, killed job, dirty re-run) over the new
   files: fixed in place: a failed mirror-list write could have left a cut list (now write-then-rename); the dry-run
   reader's refusal went into the captured $(...) (now stderr plus an explicit step warning). Inherently safe: a
   corrupted cache entry fails zstd extraction (restore warns, apt fetches) and a same-size altered file is rejected
   per file; a partial set is never saved (complete required). Residual, visible: an exact-key entry holding a file that
   no longer verifies is never re-saved (same key), so that one file is re-fetched each run with a warning; not reachable
   from our own saves, which store only verified files.

## Only a real CI run can confirm (read on the next snapshot's logs)
- apt-cache-restore's plan prints "N archives to fetch" with `mirror+file:/etc/apt/apt-mirrors.txt/pool/...` URIs (from apt's
  FixupURI + ArchiveURI; the check also accepts a mirror's own URI). If not, the log says "no planned archive comes from
  /etc/apt/apt-mirrors.txt: no mirror check".
- Playwright 1.63's dry-run form on the runner (else "printed no list ci_apt_cache.py reads").
- The probe lines: healthy and slow rates and seconds (owed by both ci.apt_mirror_* rows), and on a slow node the
  `::warning::dropped http://azure.archive.ubuntu.com/ubuntu/ ...` plus the fallback's rate.
- Cache restore/save sizes (~588 MB, ~26 MB), the firmware matrix's save race (one save wins, the others warn), the
  restore + verify + copy time on a hit (~20 s expected) and the save cost on a miss (~30 s).
- The `!cancelled()` save inside a composite after a failed install (the runner evaluates composite steps on the action's
  own status), and `timeout 5m` stopping Playwright's sudo'd apt.
- `apt-config dump` showing whether zz-retries' 1/15 is what Playwright's apt gets (finding 1).

## Checks (final head 3b9b2e72)
- actionlint 0, zizmor --offline 0 findings (15 suppressed, the base's same 15 pedantic anonymous-definition), shellcheck
  clean on the three actions' run blocks (extracted; SC1091 info only, as in ci.yml), ruff (lint_direct incl.
  build/generated_src) clean, method-assign guard and gc-site checker clean.
- mypy main (274 files), host (314), twin (57): no issues (cold cache, temporary typings link, removed).
- raising_walk --check rc 0, e51_sweep --check rc 0, review_rows --check rc 0 (8610 rows, CRr2 63, fixed 67, justified 129,
  biting 8351).
- Named readers: test_ci_workflow, test_ci_apt_cache, test_tunables_register, test_comment_block_cap, test_citations,
  test_decision_vocabulary, test_retry_counts, test_script_metadata_pins, test_config_paths_resolve, test_lint_type_scopes,
  test_uv_sync_retried_sh, test_tool_pins, test_setup_cross_browser_toolchain_sh: 799 passed.
- Whole tests_scripts tier on the final head 3b9b2e72 (tier_final3.log, 23:15-23:25, after the container restart killed
  tier_final2): 7065 passed, 9 skipped, 2 failed, zero MemoryError / "memory allocation failed". The two reds are
  test_twin_record's `test_every_instrument_has_an_entry` and `test_every_entrys_hashes_are_the_current_files`, the class
  common_u35 names expected, and not mine: `git diff 4adf28a6 HEAD -- tests_hardware digital_twin
  scripts/record_twin_instrument_runs.py tests_scripts/test_twin_record.py` is empty, so their inputs equal the base's.
  The first tier run (c004dbdc, tier_final.log) had a third red, test_host_cli_exit_idiom on my script; fixed in item 1.
- Times: test_ci_apt_cache.py's tests 5.8 s (slowest: the stall test 2.0 s); test_ci_workflow.py grew by 3 cheap text rules.

## Doc text for D3r (not edited by this lane)
CLAUDE.md, the "A third party's momentary outage must never read as a red test result" bullet, append:
"The same holds for apt's downloads in CI. Some `azure.archive.ubuntu.com` nodes trickle `.deb` files at 45-130 kB/s
(actions/runner-images#14823), and apt's timeout never fires on a trickle, so `.github/actions/apt-cache-restore` checks
the runner's mirror before each CI apt install, dropping a slow one from `/etc/apt/apt-mirrors.txt` for the rest of the
job, and restores the packages from GitHub's cache, each archive checked against the fresh index's SHA-256;
`apt-cache-save` keeps what was fetched (owner, 2026-10-27: "Yes do it like you proposed"; SPECIFICATION.md B.10.1). Every
step of it warns and carries on, so only the install itself can fail a job: keep it that way, and when an apt step goes
red, read the job log's probe lines before the install's."
BACKLOG.md, the running list of build-environment changes for the owner's next manual chroot run:
"2026-10-27: `scripts/ci_apt_cache.py` (new; CI-only host script, stdlib only, run by `.github/actions/apt-cache-restore`
and `apt-cache-save`; no dev-box or bench effect, `toolchain/setup_toolchain.py` untouched) - the chroot's lint, typecheck
and test legs cover it like any `scripts/` file."

## State
Nothing uncommitted in S/wt-u35ci (checked after the 23:11 restart: clean, both commits intact, no lock or typings link).
Runs: every run through S/u35/laneD/ci1/run.sh (namespace, nice 19, RUNS.md lines); all exited: rc 0, except c1_checks
rc 1 (citations of then-untracked files, before `git add`), reg1 rc 1 (before the Part N rows moved), tier_final rc 1
(the idiom red, fixed) and tier_final3 rc 1 (the two twin_record reds above); tier_final2 was killed by the restart
(the lead wrote its done line; its partial log deleted). Raw downloads (apt and runner-images sources) deleted after use.
nothing of mine is running

## Follow-up CI1b, written by the lane (2026-10-28 00:33 UTC)

Branch audit/u35-ci after 3b9b2e72, worktree S/wt-u35ci, logs S/u35/laneD/ci1/b_*. Not pushed.

### Commits
- `fdd3da68` the rule, its tests and the CI wiring (+ the new margin row, which its tag needs to be green).
- `db5d8fd5` Part N (floor, cap, test-cap, tool.apt_step_timeout_s, ci.playwright_install_timeout_min rows) and B.10.1's
  step 4.

### The rule and its numbers
- required = max(floor, margin x bytes still to fetch after copy-in / bound of the step that fetches them).
  `Rule(cap_s, floor, bound_s, bound_from, margin)` in `scripts/ci_apt_cache.py`; `check --bound-s --bound-from [--margin]`.
- Margin: new `ci.apt_mirror_rate_margin = 2.0` (the fetch fits half its bound; a larger margin costs only probe time,
  since with no mirror fast enough the fastest measured still goes first). Floor: `ci.apt_mirror_min_bytes_per_s`
  (1 MB/s), unchanged value, now the floor.
- Bounds, each read from its tag's own site: firmware-build-verify's apt-packages step prints
  `bound-s={st._APT_STEP_TIMEOUT_S}` (tool.apt_step_timeout_s, 150 s, one download attempt) and passes
  `bound-from: tool.apt_step_timeout_s`; playwright-chromium has one bound step (the tag `ci.playwright_install_timeout_min
  = 5` moved there) whose `min` the install's `timeout "${LIMIT_MIN}m"` reads and whose `s` (300) goes to the check.
- Numbers: firmware 588 MB -> 2 x 588/150 = 7.84 MB/s (the 1.3 MB/s node of job 122543124264 now fails it, as it fails
  the set); Playwright 25.9 MB -> 173 kB/s, under the floor -> 1 MB/s (unchanged behaviour for the web jobs). With
  nothing left to fetch (the smoke job's forced check after a full hit) the floor applies.
- Probe: budget = cap x required (the most a mirror at exactly the required rate moves inside the cap: 10 MB on the
  floor, 78 MB for the firmware set, read from libstdc++-arm-none-eabi-newlib). The cap stays the fixed 10 s, so the
  probe costs at most 10 s a mirror (three mirrors) whatever the set; a healthy 30 MB/s node reads the 78 MB in ~2.6 s.
- Log: "== required rate N kB/s: M x B bytes still to fetch over the S s bound (<tag>), floor F kB/s"; verdicts
  "fast enough" / "too slow (required N kB/s)"; with none fast enough "::warning::no mirror in ... reached N kB/s
  (measured: <uri> <rate>, ...): the fastest measured, <uri>, goes first" (the all-refused warning lists them too).
- Unchanged: the complete-set-only save; the drop-in finding 1 (zz-retries) still open for the lead.

### Red first and plants (b_red1.log, b_oldrule.log, b_bites.log, b_bites2.log, b_wfbites2.log)
- New tests: `test_a_medium_mirror_too_slow_for_the_set_inside_its_bound_is_dropped` (1.3 MB/s loopback, 1 MB set, 2 s
  bound, margin 4 -> 2 MB/s: dropped, the fast one kept, the log line and the 1 MB budget pinned),
  `test_a_set_the_medium_mirror_fits_inside_its_bound_keeps_it` (20 s bound -> floor 400 kB/s: kept; a restored 20 MB
  archive is not counted), `test_with_every_archive_under_the_budget_the_measured_rate_decides`, and
  `test_every_mirror_check_sizes_its_rate_on_its_own_fetching_bound` (workflow). On the old code all new script tests and
  every check() caller were red (b_red1: 12 failed, the new signature); run behaviourally on the old rule (b_oldrule) the
  medium test fails because the old code KEEPS the 1.3 MB/s mirror ("200000 of 200000 bytes in 0.15 s = 1313 kB/s,
  healthy", which matches the CI probe's 1290 kB/s).
- Script plants, each red: Q1 margin ignored (medium-dropped test), Q2 floor ignored (5 tests), Q3 budget from the floor
  (the 1 MB budget assertion), Q4 restored bytes counted (fits test), Q5 verdict on the floor instead of the required
  rate (first passed: reaching the budget inside the cap already implies the rate; the new rate-decides test, where the
  archive is under the budget, made it red), Q6 warning without the measured rates. All 15 earlier plants (P1-P13, P4b)
  re-run against the new code: all red.
- Workflow plants, each red: W11 firmware bound-from the Playwright tag, W12 firmware bound literal, W13 Playwright
  bound-from the firmware tag, W14 the install's own literal instead of the bound step, W15 the check ignoring its bound
  inputs, W16 apt-packages printing another constant, W17 Playwright passing minutes as seconds; W1-W10 re-run (W3's
  anchor moved to `${LIMIT_MIN}`): all red.

### Part N
- `ci.apt_mirror_rate_margin` new (estimated (agent, 2026-10-28), measurement owed: the install's rate against the
  probe's on the next CI runs that fetch).
- `ci.apt_mirror_min_bytes_per_s`: now the floor; measurement status names the 1.3 MB/s node that passed it and could
  not fit the set.
- `ci.apt_mirror_probe_cap_s`: the budget it sets now (cap x required), why the cap stays fixed, and the one real
  measurement: run 40603784233 job 122543124264 (2026-10-27), the 10 MB budget in 7.75 s = 1290 kB/s against the
  install's steady 1.3 MB/s (cmake 11.2 MB in 8.7 s, gcc 57.5 MB in 43.9 s, newlib 49.2 MB in 37.2 s): the probe reads
  the node's real rate. Still "measurement owed" for a healthy node.
- `tool.apt_step_timeout_s`, `ci.playwright_install_timeout_min` (same values and sites): name the rate sized on them.
  `l0.apt_mirror_probe_test_cap_s`: covers the medium-node tests.
- B.10.1 step 4 states the rule, its numbers and the run behind it.

### Checks (final head db5d8fd5)
- lint_direct rc 0 (ruff incl. build/generated_src, shellcheck, actionlint, zizmor --offline: 0 findings, the base's 15
  suppressed); shellcheck on the three actions' run blocks clean; mypy main 274, host 314, twin 57: no issues.
- raising_walk, e51_sweep, review_rows --check: rc 0 (8614 rows).
- test_ci_apt_cache (19), test_ci_workflow, every @tunable reader named before, comment cap, citations, decision
  vocabulary, retry counts, host CLI idiom: 803 passed (b_cA), 699 (b_cB).
- Whole tests_scripts tier on db5d8fd5 (b_tier.log, pinned to CPUs 0-2): 7069 passed, 9 skipped, 2 failed, zero
  MemoryError / "memory allocation failed": the same two test_twin_record reds as on 3b9b2e72, their inputs still equal
  to 4adf28a6's (`git diff 4adf28a6 HEAD -- tests_hardware digital_twin scripts/record_twin_instrument_runs.py
  tests_scripts/test_twin_record.py` empty), so not this lane's.
- Times: test_ci_apt_cache.py 19 tests in 6.5-6.8 s (was 16 in 5.8 s; the three new tests add 0.5 s each at most).

### Only a real CI run can confirm
- The firmware job's log line "required rate 7840 kB/s: 2 x 587835714 bytes ... over the 150 s bound
  (tool.apt_step_timeout_s)" and, on a medium node, the drop of azure with the fallback's measured rate; whether the https
  archive.ubuntu.com mirror moves the 78 MB budget at 7.84 MB/s from Azure (if not, the fastest goes first with the
  warning, and the 588 MB may still not fit: that would be a bound question, not the check's).

State: nothing uncommitted in S/wt-u35ci; every run through S/u35/laneD/ci1/run.sh with RUNS.md lines, all exited
(b_red1 rc 1 and b_oldrule's two reds are the red-first evidence; b_wf1 rc 1 was the margin tag before its row; b_tier
rc 1 the two twin_record reds).
nothing of mine is running
