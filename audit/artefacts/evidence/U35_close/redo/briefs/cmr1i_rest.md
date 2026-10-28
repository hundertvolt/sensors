# CMr1i: the release growth's cause, the sites, the bites, the rows (lead, 2026-10-27)
Read `S/u35r/briefs/redo_common.md` (all of it; its "Efficiency" section is binding and says how you hand back),
then `S/u35r/briefs/cmr1h_sites_bites_rows.md` (its rules and items stand), then CMr1h's hand-back
`S/u35r/handbacks_redo/CMr1h.md` (the state, its probes, the sites it left, the ready rows). `cmr1_device_picks.md`
(the owner rule) when classing. Worktree `S/wt-u35cm2`, branch `audit/u35-cm2` at the integration head 5a8c6e35
(clean, rebuilt). Logs in `S/u35/laneC/cmr1i/`; CMr1h's in `S/u35/laneC/cmr1h/`.

## The lead's review of CMr1h (binding)
- The revert is right: a change that slows the file is not kept. But the ~18 s growth after the clock release is
  unexplained, and an unexplained effect is not left behind (owner: root-cause, no evidence silently lost).
- The skip classes are accepted as the owner's rule applied (devices deduplicated by identical wiring; a mechanism
  that reaches no part whose wiring differs runs once), on one condition: each of the 20 "same mechanism" skips is
  backed by the wiring read, i.e. the test reaches no part whose wiring differs. A skip that fails that is widened.
- The DHCP-trace test (:759 at cce274e1) reads the WiFi log, which lives in FRAM, wired three ways: measure whether
  its read reaches the FRAM wiring; if it does, it runs on each FRAM wiring.

## Items, in order (each committed green on its own)
1. The release growth's cause, bounded: probe CMr1h's two candidates (DrivenTime's Python ticks_ms() on every time
   read of the driven modules; the twin chips running on real time while their drivers saw driven time, which
   shifts their phase, e.g. the SCD30 healthy window), one probe each. Name the cause with numbers. If the cause is
   in the harness and fixable there (the chips on the same clock, say), fix it, re-try CMr1h's attempt, and keep it
   only with a formal pair that shows the gain (base then head, both stages, the load recorded). Otherwise the
   cause is recorded and the residual stands.
2. The 20 "same mechanism" skips against the wiring read, and the DHCP-trace test, as above.
3. cmr1d item 3's sites (CMr1h.md lists them; re-locate).
4. The four bites from cmr1b's item 4.
5. matrices.md's device-pick rows (CMr1h's ready rows), and resolve the "open" row; no "open" row is left.
   CMr1h's E.2.1 text stays in its hand-back for the docs pass; re-check it against your result.
- Lane N11c tags waits in the CMr1 twin files beside you. Lane HP1 measures the twin's heap; touch neither's work.
- Seams: at about 80 tool calls, commit what is green and hand back with what is left.

## Hand-back (the file, per redo_common)
Commits; the cause with numbers; per file, the times (a formal pair where a time changed); every site's class; the
bites; the matrices rows; the E.2.1 text if it changed; last line "nothing of mine is running".
