T4r2b hand-back, saved by the lead from the message it sent (2026-10-26). Commits 46bf1f34, 9ce4accd on audit/u35-t4r2b (on fb6e0b4a).

T4r2b hand-back (worktree S/wt-u35t4r2b, branch audit/u35-t4r2b). Two new commits on top of fb6e0b4a: 46bf1f34, then 9ce4accd. Nothing is pushed and nothing is uncommitted. I stopped at the 80-call valve at a seam. Fold (3) and item 4 are done; fold (2), fold (1) and item 5 are left.

**Done**
- **Fold (3), 46bf1f34.** `refused_config_write_is_reported_unpersisted` makes NTP's config file 0444 and its directory 0555. It then checks: the PUT /networking NTPOffset answers Valid; once the flush has run (polled), `/status` system.ConfigUnpersisted == ["NTP"] and CFGMGR_NTP holds E CFG_FILE_WRITE. The modes are restored in `finally`. A second changing PUT reads back [] and the file holds the new value.
  - It decides by a write probe, not by uid. Under plain root it skips with its reason (skip_dev_m1). The harness exits 1 in that run because a run that passed nothing is no pass, which is the existing rule.
  - New mechanism in the same commit: a body can raise `UnmetPremiseError(reason)`, recorded as "skipped". A boot that itself failed still records "failed". Its tests_scripts test failed first on the old harness (AttributeError).
  - setpriv: the proof ran the whole harness under `setpriv --bounding-set=-dac_override`, and the twin inherits that. It is not wired per scenario: that would need a launcher prefix in `spawn()` (scripts/_twin_process.py:430), a shared file I left alone. CI runs as non-root, so the modes bind there.
- **Item 4, 9ce4accd.** `--test-hold-system-entry ERRNO:cut` (README row updated): the entry's real write is held after its first FRAM block's busy mark and never released, so the 1200 ms bound counts the hold and cancels the write there.
  - `an_escalation_entry_held_past_its_bound_is_cut_and_the_reset_still_follows` checks: exit 3 with the watchdog fed; the log line "its entry write did not finish within"; the relaunch reads ResetReason 20; no cut entry in SYSTEM's history; FRAM logs E FRAM_STATUS_BYTE and W FRAM_BLOCK_INVALID; a third boot shows neither, so the block was healed.
  - The release scenario is unchanged.
  - Knob unit and flag tests failed first on the base runner at both stages ("unexpected keyword argument 'cut'", and the TestFlags assertion), then passed 45/45 at both.

**Red and green** (dev, both stages)
- Scratch-copy plants, each failed as planted:
  - Bound removed (src/asy_system_service.py:591) → "a simulated reset expected, got no exit before the caller's deadline".
  - `unpersisted = False` (src/asy_config_manager.py:407) → "ConfigUnpersisted never named NTP".
- Green: both scenarios on dev and on arzi at both stages, under setpriv.
- Times: item 4 takes 13.3-13.4 s on dev and 11.3-11.4 s on arzi; fold (3) takes 4.7-4.8 s on dev and 3.6-3.7 s on arzi.

**Left**
- **Fold (2): red on the tree, not committed.** WIP is in S/u35/laneT/t4r2b/fold2_wip_harness.py (`_SNAPSHOT_READS`, `_failed_config_snapshot`, `_pending_faults`).
  - BMP3XX: the task start's stored-config apply reads the same registers as the snapshot (twin_01 line 22, "BMP3XX Error setting config data"; pending 2→1 at BOOT_TASKS). No BMP3XX key is snapshot-only.
  - ISL29125: `_verify_config` (asy_isl29125_driver.py:935, every cycle) and `reset()` (:1520) read the same CONFIG1 burst.
  - SCD30 (0x5403) passed on arzi at both stages, but no plant has turned it red yet.
  - Proposed fix: read the pending count after BOOT_DONE and account the GETs plus the verify's lines against that count.
- **Fold (1) and item 5: not started (valve).** T4r2's facts still hold on this base: `_UART_LOAD_REQUEST_S` is at scripts/_digital_twin_scenarios.py:146 (the line moves once fold 2 lands), there is no SO_SNDBUF knob in digital_twin/, and `HTTPDropped` is under /status networking.

**Checks** (zero memory markers in every run)
- ruff clean; twin mypy cold, 53 files, 0 issues; host mypy cold, 309 files, 0 issues (typings symlinked from S/shared/typings and removed after).
- Comment cap, citations, decision vocabulary, tunables register and 9 static readers: 961 passed.
- The 9 twin-starting readers, in the namespace with the private toolchain: 426 passed.
- On commit A's own state: 707 passed.

**Notes**
- The integration file takes 1.39-1.45 s against the base's 1.32/1.37-1.40 s, under 10 % slower.
- No new tunable, no SPEC sentence stale (SPECIFICATION.md:1017 and :3815 still match), no allow-list row, no write site added or changed.
- The private toolchain S/tc-t4r2b and the plant copy were made and are now deleted.

**Runs** (all in RUNS.md)
- red_knob rc=1 and green_knob/green_knob2 rc=0.
- Plant runs on dev at both stages rc=1, as planted, except fold (2), which failed its own BOOT_TASKS pre-check before its plant could act.
- Green dev rc=1 only from fold (2); green arzi rc=0 at both stages; skip_dev_m1 rc=1 as explained above; readers2 rc=0.
- Logs are in S/u35/laneT/t4r2b/ (runs.sum, logs/, scen/).

nothing of mine is running
