# N11 launch: base, scope boundary, load (lead, 2026-10-27)
Your task is `S/u35r/briefs/n11_untagged_waits.md`; this sheet sets what it leaves open.

- Worktree `S/wt-u35n11`, branch `audit/u35-n11` at a42de8b5 (the integration head, clean, generated inputs rebuilt).
  Logs in `S/u35/laneN/n11/`.
- Not yours while lane CMr1e edits them (it makes the widened twin files efficient on another branch):
  tests/test_digital_twin_ntp.py, _hot_replug.py, _bus_hazard_concurrency.py, _clock_jump.py, _loop_end.py,
  _wifi_modes.py, tests/_twin_devices.py, and the twin scenario helpers for the SCD30 and the SGP40 (the
  `tests/_digital_twin_*` modules those files import for them). A candidate there is read and classed, then left
  unchanged. Your hand-back lists it with its class, for a later block once CMr1e is merged.
- The lead's `mc_cov` (a full `scripts/test.sh --coverage` on int) started at 05:46. Take no timing pair while it runs:
  its RUNS.md "U35 lead mc_cov" RUNNING line has no done line yet, or a scripts/test.sh process is listed. Before
  each timing pair, check `uptime` and the process list against CHECKLIST 12 (at most 4 heavy processes) and record
  both. Another lane times its own files too; one pair at a time is yours.
- Every run goes through your own run wrapper in your log dir, modelled on `S/u35/lead/run.sh` (namespace, nice 19,
  disk check, RUNS.md lines). Its RUNS.md lines name `U35 lane N11`.
- File edits use the Edit or Write tool. A deletion is its own Bash call, with a literal path or "${var:?}".
