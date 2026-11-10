# R5 unit RP: the last round's 11-04 bench probes re-read against the current tree (lead, 2026-11-10; read-only)

## Read first
`S/u35r/r1/common_r1.md` (binding, all of it; the filter rule above all; label `rp_`). S =
`/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad`. Tree: int `S/wt-u35int` at
886f8af0, read only (the lead runs checks in it: never write there, never run anything in it). The need:
`S/u35r/r5/CLOSE_STATUS.md` section "The last round: what the tree must hold before the image" ("Their probes are present
... but date from 11-04, before fsync: re-read them against 651af010 before the image, boot_stretch_final.py first
(e1958815 took the boot lists' collects)"). The probes: `S/u35r/hw_handover/mp/*.py`, and the copies the bench runs
(find them on `origin/claude/u35-bench-campaign`, e.g. under `audit/artefacts/evidence/U35_close/redo/`; the runner is
`.../redo/hw_round1/round1.sh`, steps 12a-12f, 13, 16b, 11). Since 651af010 nothing in `src/` changed but comments.

## Owner (verbatim)
- 2026-11-09 22:27:31: "... don't drop real features and don't introduce or reintroduce gaps. Lean, functional, no
  losses, no gaps, efficient by smart design appropriate for limited devices like the rp2"

## Your work (one table)
For each probe round1.sh still runs (boot_stretch_final, ring_peak_final, dns_idle_poll, host_reset_errors_timing,
general_call_per_chip, held_sda_reset, country_scan, host_dns_query_timing, long_fram; any other it names):
1. Is the bench's copy the same as the scratch copy (`git show ...:path | diff - file`, say which differs)?
2. Every `src/` module, function, attribute, constant, import, command code and /status or REST field it uses: present
   at 886f8af0 with the same meaning (file:line)? Every assumption it states about the firmware (a boot list's
   `gc.collect()`, a fsync or settle, a supervisor timing, a log line's text): still true (file:line)?
3. Its pass criterion or the figure it reports: still the one SPEC or BACKLOG names today (filtered grep, cite)?
Verdict per probe: OK, STALE (the smallest edit that makes it right, in lines; do not make it), or OBSOLETE (what
removed its subject, with the commit).

## Never
Never edit any tree, branch or probe; never run a probe, a test or a build; git, grep and read-only text tools only.
Never read `arduino/` (`':!arduino'` in every git grep and git log); never view SPECIFICATION.md, CLAUDE.md,
BACKLOG.md, README.md, `devices/`, `audit/`, `src/asy_wifi_service.py` or a probe touching Wi-Fi settings unfiltered;
where a claim depends on a filtered line, print only identifier matches. Never open `/root/.claude/`. No hardware, no
mpremote. Scratch only under `S/u35r/r5/ftmp_rp/`.

## Hand-back
`S/u35r/r5/PROBES_RECHECK.md` (at most 40 lines; first line "rp hand-back, written by the agent (<date -u>)": the
table probe | copies same | verdict | evidence | smallest edit). Budget about 1 % of the week. Your last line: "nothing
of mine is running".
