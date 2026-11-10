# R5 unit LR: the last bench round's relay, drafted (lead, 2026-11-10; read-only)

## Read first
`S/u35r/r1/common_r1.md` (binding, all of it; the filter rule above all; label `lr_`). S =
`/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad`. The image's tree: int `S/wt-u35int`
at bfa240fa (read only; the lead's gate runs in it: never write there, never run anything in it). The bench branch:
`origin/claude/u35-bench-campaign` at bc53cdfa (the bench idles on snapshot 58's image); its runner
`audit/artefacts/evidence/U35_close/redo/hw_round1/round1.sh`, its hand-back `.../hw_round1/HANDBACK.md` (read by
grep), the relay file `.../hw_round1/LEAD_RELAY.md` (newest on top; the 11-10 entries say what the bench did on
snapshot 58), the two-image proof `audit/actions/C.md` lines 396-416 (A.C.09).

## What the round must cover (the sources, all of them)
- `S/u35r/r5/CLOSE_STATUS.tsv` rows of kind bench-last-round (36), and `CLOSE_STATUS.md` "The last round" section.
- `S/u35r/plan/PLAN.md`, R5's last-round bullet and the round-1 list (grep "round 1", "last round").
- `S/u35r/r5/PROBES_RECHECK.md`: 12f is obsolete (round1.sh row 12f and held_sda() go); ring_peak_final.py:33's
  comment "2.5 s" becomes "2 s"; the rest OK.
- FINDINGS (`S/u35r/findings/FINDINGS.md`, grep, never whole): 12.169 (the heap load pattern, owed on both images),
  the FRAM settle removal and its re-measure (grep "settle"), 12.179-12.183, and O6's settlement (grep "O6").
- Settled, not to be measured: O3 (the SCD30 keeps its pressure through a power cut; owner 2026-11-10, "Field proven
  many times"); the SGP40 serial read (done on the bench 2026-10-28, FINDINGS 12.179).

## Your work
`S/u35r/r5/LASTROUND_DRAFT.md` (at most 80 lines; first line "lr draft, written by the agent (<date -u>)"):
1. The relay text for the bench runner, ready to send (at most 40 lines, operational, no audit IDs needed by the
   bench beyond step numbers): the image to build and flash (the tree the lead pushes), FRAM evidence first, then
   every step in run order with what it answers, and what needs the owner at the bench (hands, an AP, a power cycle).
2. Per step: the step, its source row(s), present in round1.sh or missing (the smallest addition, in lines), its
   flash writes and SCD30 NVM writes (round1.sh's columns), its time.
3. The round1.sh edits as a unified diff against bc53cdfa's file (not applied), and the probe edit.
4. Anything a source asks for that the tree or the runner cannot yet do, said plainly; anything two sources
   disagree on, said, not decided.

## Never
Never edit any tree, branch, probe or the relay file; never run anything; git, grep and read-only text tools only.
Never read `arduino/` (`':!arduino'` in every git grep and git log); never view SPECIFICATION.md, CLAUDE.md,
BACKLOG.md, README.md, `devices/`, `audit/`, `src/asy_wifi_service.py` or a probe touching Wi-Fi settings unfiltered;
where a claim depends on a filtered line, print only identifier matches. Never open `/root/.claude/`. No hardware.
Scratch only under `S/u35r/r5/ftmp_lr/`. Budget about 1.5 % of the week. Your last line: "nothing of mine is running".
