# U0 record (M.PROC.003 order)

| step | content | state | evidence |
|---|---|---|---|
| (1) | baseline SHA and anchor move (A.U0.02) | done 2026-10-06 | baseline `798e5a7` (`origin/main` at the go-ahead, already an ancestor of the audit branch). Anchors resolve at the branch head; between `4dc80ef` and `798e5a7` only BACKLOG.md moved (+1 from :351), so only BACKLOG anchors moved: `reanchor.py 4dc80ef 798e5a7 … --only=BACKLOG.md` over the plan, `audit/pass2/`, `audit/harvest/`, `audit/refined/` (116 lines in 29 files). `reanchor.py` gained three guards found on the way: commit-qualified anchors (`sha^2`:path:N) never move, `--only=` restricts the mapped files, a number beyond the old file's length is a continuation token naming another file. One hunk-internal anchor kept as is (`audit/pass2/G9.md:105`, BACKLOG :350). One hand fix: the plan's ENV.T10 example `BACKLOG.md:575 for :555 at 0615eba` is commit-qualified after the path and was restored. README and SPECIFICATION anchors were not moved: the plan already cites them at the branch tree. Delta harvest over `4dc80ef..798e5a7`: README.md's removed audit-plan entry (the branch carries its own, rewritten) and BACKLOG.md :347-349's reworded sentence; neither holds an owner decision or a code fact the register lacks. |
| (2) | the non-interference frame (M.PROC.001) | done 2026-10-06 | `audit/REGISTER.md` "Non-interference" |
| (3) | toolchain, corpus, extractor (M.PROC.004) | done 2026-10-06 | `setup_toolchain.py setup` passed (4 min 49 s; apt `update` warnings from two unrelated PPAs, installs fine). Probes: `build-standard` plain, `build-settrace` settrace. Corpus: `~/pico-toolchain/micropython` at `v1.29.0` with `lib/lwip` 77dcd25, `lib/pico-sdk` 98a542c, `lib/cyw43-driver` 055d642, `lib/micropython-lib` ee4bb8f (read-only); scratchpad `corpus/microdot` at `v2.6.2`, `corpus/gas-index-algorithm`. Extractor: 21 PDFs extracted; no chip lacks a datasheet directory. No egress failure. |
| (4) | audit apparatus (M.PROC.005) | running | |
| (5) | baseline measurement (M.PROC.007) | running | `baseline.md` |
| (5a) | port-isolation proof | pending | |
| (6) | dependency refresh (M.PROC.008-.013) | pending | `dependency_refresh.md` |
| (7) | history trace (M.PROC.006) | running | `history_trace.md` |
| (8) | A.U0.01, A.U0.07-.60 code and doc actions; allow-lists built last | running (doc and SPEC/BACKLOG lanes) | |
