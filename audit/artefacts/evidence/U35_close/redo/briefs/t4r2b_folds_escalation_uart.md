# T4r2b: the three folds, the escalation's timeout path, the UART load plant (lead, 2026-10-26)
Read `S/u35r/briefs/redo_common.md` first. Base, worktree and branch named at launch; logs in `S/u35/laneT/t4r2b/`.
This is the second block of T4r2: read `S/u35r/briefs/t4r2_twin_scenarios.md` in full; its items 3, 4 and 5 and its
"Proof and checks" and "Not yours" sections are your brief, unchanged. Items 1, 2 and 6 are done and merged (T4r2's
hand-back `S/u35r/handbacks_redo/T4r2.md`; do not redo them). T4r2's facts for you, each to re-check on your base:
- `_ESCALATION_ENTRY_WAIT_MS` = 1200 at src/asy_system_service.py:77; the bounded wait at :591, its message at :593.
- The hold knob is `_test_hold_system_entry` in digital_twin/run_generic_integration.py near :652; its bound starts at
  the release (so a hold today is never counted by the bound).
- `/status`'s field is `ConfigUnpersisted`, from `sysfunct.get_config_unpersisted()` (buildgen/codegen.py near :297).
- `HTTPDropped`: src/asy_webserver_service.py near :592 and :1045; `_WRN_HTTP_PEER_RESET` = 48 (near :108).
- No SO_SNDBUF knob exists in digital_twin/.
- `_UART_LOAD_REQUEST_S`: scripts/_digital_twin_scenarios.py:146, used near :1935 and :1942.
Order: fold (2) and fold (3) first (they need no new knob), then item 4, then fold (1) with its knob, then item 5.
Commit each item green on its own; past 80 tool calls hand back the rest at a seam with its facts.
The scenario runs need a private toolchain copy (`cp -a S/tc-int S/tc-t4r2b`, disk check first, keep 3 GB free,
deleted after, say so). Three other lanes share the 4-core host: nice 19, one run at a time.
