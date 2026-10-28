# U30 close evidence

What each folder proves (the scan record `audit/sweeps/scan_runs/20261020_U30_close.md` cites them). Logs only:
`assemble.sh` copies each lane's and fix's `*.log`, `*.txt`, `*.out`, `*.tsv` and `*.time` files two levels deep with the
hand-backs, and then deletes every code file it picked up (`*.py`, `*.sh`, `*.js`, `*.mjs`, `*.toml`, `*.ini`, `*.yml`,
`*.diff`, `*.pid`), every empty file and every empty folder. No copy of a tracked file and no withheld value, checked
on the final staging (1969 files): over `5ba138c` and the 87 revisions of `5ba138c..ad29382` (blob, name and line overlap) it flags only `README.md`, this index itself, as at U28 and U29, and its 393 credential-word hits are test names, help text and prose; the withheld-value token hash check (`withheld_check.py`, kept outside the evidence) found neither withheld bench password over 11348 files (this staging, `audit/` and the lead's scans, review and hand-backs), its control (the hotspot default's hash over `audit/harvest/`) 8 hits. The trial staging (1616 files) was checked the same way: over `5ba138c` and the 71
revisions of `5ba138c..ff18c87` (blob, name and line overlap) it flagged exactly the two files below, and its 258
credential-word hits are test names, help text and prose. Two files are left out as copies of tracked text:
`lane_S2/inits.txt` (34 of its 35 lines are `src/voc_algorithm.py`'s) and `fix/f3a/i2.txt` (all 209 lines are
SPECIFICATION.md I.2's); each is the tree's own text at its commit, which the record names instead. No credential value:
the hotspot default reads `<row-8-default>` and the bench LAN's third octet `<bench>` in every file here; in the trial a
token hash check (`withheld_check.py`, kept outside the evidence) found neither withheld bench password (`sha256[:8]`
`ead195cc`, `ab75b959`) in any staged file, and its control, the hotspot default's own hash, in no masked file. Files
over 20 KB are gzipped.

- `gates/gate1/`: the gate on `fef34d0` (`gate.out` the timeline): generation, lint, ruff with CI's paths, typecheck with
  no arguments and with CI's paths, `pytest --collect-only tests_hardware`; `scripts/test.sh` at -1 and 32768 and the
  coverage leg (each red only on the four `tests_scripts` cases `d860130` fixes); the six twin runners; `npm test`,
  `npm run test:coverage` and the web statics (`npm_static/`); `vmstat.log`, the host's load through the gate.
- `gates/gate2/`: the gate on `6df1409`: every leg green; its coverage leg not run (superseded by gate2b's); the twins'
  and npm legs stand for the final head, which changes no file they read.
- `gates/gate2b/`: the legs that execute the files changed after it, on the final head `dd0a4c7`, all green;
  `coverage_diskfull.log` the first coverage run, dead on a full disk; `coverage.log` its re-run alone (green (107 files, 5218 tests, `tests/test_asy_print_log.py` 102/102, 0 retried, 0 memory markers)).
- `lane_C/`: the C-stack flag and reboot, the paused reset, the resolver's causes, the config store's runs, the
  fatal-report check: the batches at both stages (`batch_c1.out`, `batch_final.out`), `logs/` (seen-failing runs, bites,
  times), the C1 and final hand-backs.
- `lane_G/`: the gc site checker and X01: the checker's tests red on the old checker's shim, the live sites before and
  after (`sites_base.txt`), X01's root cause (`x01/`, `x01b/`), OF-187's slope (`of187/`), the six settrace runs that did
  not reproduce OF-149 and OF-188 (`batch2b/`), the mypy passes.
- `lane_L/`: the unit tier's error level: base, after and final times at both stages and settrace, the planted fault's
  bite (0 lines on W1, 2-390 at the head: `bite_summary.tsv`), the opt-out bite (`optout/`), the paired timings.
- `lane_M/`, `lane_M2/`: the UART layer's caught allocation failures and its teardown: the 47-handler sweep
  (`sweep_sites.txt`), seen-failing runs, bites, base and after times at -1, 32768 and settrace, the scans.
- `lane_N/`: the web, network and FRAM handlers: the batches at both stages, seen failing and bites, and the 32768-stage
  measurement that found the GC mark stack's overflow (`gcmeas/`).
- `lane_R/`: the rig's GC mark stack: the five builds' logs, the readback, the 39 tests seen failing, the bites, the heap
  layouts of the stock, 1024 and 4096 builds, the paired timings (`t1024v4096/`, `cov/`, `cov_alt/`).
- `lane_S1/`, `lane_S2/`: the reader buffers and handlers: each file's first, after and final runs at both stages, the
  bites, boot contiguity (S2), times.
- `lane_V/`, `lane_V2/`, `lane_V3/`, `lane_V4/`: the twin verification and the launch-string refusals: base and after
  times, seen failing, bites, Run 12's runs (`dev/`), the qstr limit reproduced at 255 and 256 bytes (`lane_V2/repro/`),
  the per-boot cost (`lane_V2/cost/`), the launchers' runs at both stages. Lane V's verified OF-215 patch is a `.diff`,
  so it is not here; V2's commit `95ed89f` carries it.
- `lane_X/`, `lane_X2/`: the await-depth tripwire, the catalog's check and the docs: base times, the planted chain and
  site failing, `fram_peak/` (the ResetErrors FRAM-buffer peak in I.2), the scan, the doc readers' runs.
- `review/`: the four readers' hand-backs (`RA.md` to `RD.md`) and the lead's dispositions (`rulings.md`).
- `fix/`: one folder per fix with its hand-back and logs: `f1a/` (before and after times, seen failing, the webserver
  bite, the twin runs at both stages), `f1c/` (the settling sequences, times), `f1d/` (seen failing, the eight bites, the
  allocation counts before and after, the final runs), `f3a/` and `f3a2/` (seen failing on `fef34d0` and `a52d4cc`, the
  bites, the deepest chain before and after: `deepest_fef.log`, `deepest_after.log`), `fix0/` (`d860130`'s 209 passed),
  `f1b/` (seen failing at each level: `seen_fatal_sites.log`, `seen_hooks.log`, `seen_webserver.log`; `disc/` the 13
  files that can set the flag, run under the new hook before the clears (the seven setters failing, nothing else); `f1dt/` the boot-window test against `fef34d0`'s store; `bisA/`, `bisB/`,
  `probe/`, `layout/` the soak test's layout runs; `after_m1/`, `after_32k/` the final runs at both stages; the bites,
  the type checks and the scans), `f3b/` (the 113 doc-reading files' run with its two reds, the rerun, the 12 commit
  checks), `f1e/` (the soak's root cause: `repro1.log` the exact reproduction; `gdb/` the heap dumps' diff, the stack
  word and the watchpoints, `watch4_gdb.log` the root written once at startup; `sweep/` 40 paddings without and with the
  period, `asweep/` what sat on the root's block at each collect; `plant/` the planted leaks on both trees and stages;
  `rate/` the healthy rates and times; its scratch tree copies and padded files are not staged).
- `lead/`: the checklist, concurrency rules and run record, the lane plan, the landed check, option 1's map, the carried
  actions, the rulings and their re-sort, the relay, the close notes and the lead's log for the unit (`lead_todo.md`,
  from its U30 entry on); `merges/` the lane merges; `w1/` the W1 sync (the toolchain install, the hazard files,
  the W1 tier and its reds); `twin_record/`, `twin_record2/` the twin record's re-records (`a104068`, `7ab7dd2`),
  `twin_record3/` the re-record on the final tree (`6df1409`; `trace.txt`: 121 results unchanged, 35 `api_sha256`
  values moved, each traced to an imported `src/` module changed since `7ab7dd2`, 0 untraced); `twin_record_api/` the API merge's checks; `soakfix/` the lead's checks of `f0dd414` (the webserver file at -1, 32768
  and settrace, the scans and their readers, ruff, the gc site check); `gcstack/` the mark-stack probe (`lay_A.txt`,
  `lay_B.txt`, identical but the heap base) and its pairs (`pairs1/` void, both binaries in one worktree; `pairs2/`);
  `tier_fef34d0/` the whole `tests_scripts` tier on `fef34d0` (the four reds), `tier_final/` the whole tier on `6df1409` (6577 passed, 9 skipped, 0 failed, 0 memory markers), `tier_final2/`
  the same on `cead564`, after the soak fix, `tier_squash/`
  the tier on the squash, staged before it ran (its result in U31's record); `records1/`, `records2/` the records agents' lists and scans.
