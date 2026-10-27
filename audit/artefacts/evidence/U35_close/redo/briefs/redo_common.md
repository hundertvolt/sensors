# U35 redo blocks: what every redo brief shares (lead, 2026-10-26)

## Why there is a redo
The cloud container was reclaimed during a pause. The audit branch at `656fc82` survives (its tree outside `audit/`
equals gate 2's 7851668, LEAD NOTES 118); every U35 commit after gate 2 is lost. The owner (2026-10-26): "Recover and
redo what was lost, be really sure." and "Firmware really complete, don't push fixes to future units". Your block redoes
lost work. What a lost block reported (its hand-back in `S/u35r/recovered/handbacks/`) is a map, not proof: re-check
every claim on the tree before you rely on it, and re-establish every result (a test seen failing first, a bite) here.
Line numbers in the recovered briefs and hand-backs refer to the lost heads: re-locate each on your base.

## Environment (this container)
- S = `/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad`.
- The shared venv: `S/wt-base/.venv` (activate it); the pinned uv 0.8.17: `S/uvenv/bin/uv` (put `S/uvenv/bin` first on
  PATH, set `UV_OFFLINE=1 UV_PROJECT_ENVIRONMENT=S/wt-base/.venv`); Node: `/root/pico-toolchain/node/node-v24.22.1-linux-x64/bin`.
  Where an old brief names `S/wt-u8/.venv` or node-v24.21.0, use these instead.
- One MicroPython test file at both GC stages: `env -u TEST_DEVICE TZ=UTC
  MICROPYPATH=build/generated_src:src:tests:frozen_modules:.frozen
  /root/pico-toolchain/micropython/ports/unix/build-standard/micropython -X heapsize=16M tests/test_x.py`, and the same
  with `tests/_threshold_runner.py tests/test_x.py 32768` as its arguments (TEST_DEVICE=<device> for per-device files,
  as scripts/test.sh sets it). `S/u35/lead/files_both.sh` is not restored: write your own small wrapper in your log dir.
  A model run wrapper (namespace, nice, RUNS.md lines, disk check): `S/u35/lead/run.sh`.
- The shared toolchain (`/root/pico-toolchain`) holds Unix ports built from 656fc82's `toolchain/` files. From
  `8d2bfb13` on, `toolchain/micropython_overrides.py` differs, and `scripts/test.sh` and the twin CI rebuild the
  shared binaries when the hash differs (`scripts/_unix_port.sh ensure`), under every other block's runs. On a base
  with a different `toolchain/`, run neither against the shared toolchain: use a private copy (`cp -a`,
  `PICO_TOOLCHAIN_DIR`, a disk check first, deleted after) or ask the lead. Running a test file with the binary
  directly is unaffected.
- Port-binding runs: `unshare -n S/u24/ns_xdg.sh nice -n 19 <command>` (the wrapper brings loopback up itself).
- After any `src/` edit, regenerate with `S/u23/rebuild.sh <your worktree>` before running a test file, or the
  generated tree reads stale and every boot refuses.
- The mypy passes need typings: run them as `scripts/typecheck.sh` does, or ask the lead for the shared copy.
- Baseline at 656fc82 in this container: `scripts/test.sh` at -1 PASS, 643 s, 115 files, tests_scripts 6809 passed
  (S/u35/lead/base_testsh_m1.log, per-file times in it); use its per-file times as your base table.

## Rules (in addition to S/CHECKLIST.md, binding, and the Rules of S/u35/briefs/common_u35.md)
- Never open Claude Code's own transcripts or anything under `/root/.claude/` (CHECKLIST 1b).
- Owner rulings in force: `S/u35r/recovered/owner_rulings_after_LN118.md` (verbatim) and LEAD NOTES 1-151 in
  `S/u35/lane_plan.md`. The owner's 2026-10-26 rule replaces the old routing: a fix in a product file that U35 can make
  lands here; a finding only silicon can settle stays with its hardware round, named as such.
- Commit subject `U35 lane <block>: <summary>`, the two trailers (`Co-Authored-By: Claude Opus 5.5
  <noreply@anthropic.com>`, `Claude-Session: https://claude.ai/code/session_01BWfjT6GSD7bxCP57j86vB8`); decision tags
  "(agent, <date -u>)"; text outside `audit/` cites no audit ID, lane or plan. Do not push.
- Run your brief to its end: there is no tool-call limit, since an unclosed hand-back costs a new lane's re-reading
  (owner, 2026-10-27). Hand back early only for a question or decision for the lead or owner, a finding that changes
  the brief's direction, or a context so large it would be summarized. Hand-back as your brief says; last line
  "nothing of mine is running".
- The "17 repo-wide scans" (S/u32/briefs/common_u32.md) and S/u24/briefs/common.md are lost with the container; no copy
  survives. Run your brief's named checks, and on your final head the whole tests_scripts tier (it holds the 17 scans
  and every reader; a chosen subset missed two reds this unit). The lead's merge check runs it too (lead, 2026-10-27).
- Lint: `scripts/lint.sh` refuses the shared venv (its guard wants the worktree's own `.venv`, resolved). Run its passes
  with `S/u35/lead/lint_direct.sh` from your worktree (ruff over the eight scopes AND `build/generated_src`, shellcheck,
  actionlint, zizmor, the method-assign guard, the gc-site checker), after `S/u23/rebuild.sh`. A ruff run that leaves
  out `build/generated_src` misses the generated modules: it did once (lead, 2026-10-26).
- Web tier: a change to `tests_js/`, `js/`, `html/` or anything the website's definitions read (a `scripts/` emitter,
  `buildgen/error_catalog.json`) runs `npm run test:unit` inside the namespace (node_modules linked as above), not only
  `npm run lint`/`typecheck`: a lane's emitter change once left its JS twin test red (lead, 2026-10-26).
- Quality comes first (owner, 2026-10-27: "don't cut back the quality"): no item, check, stage, device or bite is
  dropped or narrowed to save budget; where a quality step costs more, it gets more.
- Efficiency (owner, 2026-10-27: same quality, same result, no slowdown, less budget). Binding for every lane:
  - Hand-back: write it yourself, complete, with the Write tool to `S/u35r/handbacks_redo/<block>.md` (first line
    "<block> hand-back, written by the lane (<date -u>)"). Your final message is then only that path, the commits
    and one line per headline result. If that Write is refused, put the full hand-back in your final message instead.
  - Read what you need, not whole files: grep for the anchor, then the line range; whole SPECIFICATION.md or a whole
    large test file only when the item is about the whole file.
  - Logs: read the summary or tail lines and the failing test's block, never a whole passing log.
  - Long runs: start them in the background and wait for the completion notice. No Monitor or tail loop on a run,
    no repeated status checks.
  - No exploratory full-tier or both-stage runs while iterating: run the one test or file in question; the formal
    pair or both-stage run is taken once, on the finished change.
  - Hand-backs and commit messages state results; no narration of the steps that led there.
- Twin state dirs: a dir reused after a twin stopped under load can hold a torn FRAM block, and the next boot then
  logs E FRAM_STATUS_BYTE and W FRAM_BLOCK_INVALID (the design's allowed cut, correctly reported; CRr2b11). Use a
  fresh state dir per run; if you reuse one, read that pair as this mechanism, not as a new finding.
- Every run goes through your run wrapper, a short probe or a plant run included: namespace, nice 19, RUNS.md lines
  (CHECKLIST 12). Three lanes ran short probes outside it; "under a minute" and "binds no port" are not exceptions.
