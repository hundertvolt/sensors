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
