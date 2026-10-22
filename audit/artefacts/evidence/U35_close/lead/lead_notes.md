## LEAD NOTES (lead, 2026-10-21)
1. Base `f3fff0e`: U34's integration head `1dd6dd5` merged with U33's records head `c26db17`, which carries U32's squash
   `970b63b`. Against `1dd6dd5` only tests/test_asy_neopixel_driver.py and tests_js/shell.test.js (U32's two gate fixes)
   and `audit/` differ, so P1's and P2's line numbers hold everywhere else; N1 and W1 re-locate in those two files.
   Lanes never merge anything: the lead merges U33's and U34's final heads into `audit/u35-int` at W6. The base worktree
   is `S/wt-u35base` (detached at `f3fff0e`, rebuilt); every base/head time pair runs against it.
2. P2's rulings R-1 to R-34 stand, with these amendments (lead, 2026-10-21):
   a. R-8, the FRAM probe. Before writing it, P2 states from the code, per device, when a blank status byte is read in
      steady state (boot, chunk allocation, each errcount read behind `/status`, other). If one can recur per request,
      P2 measures the probe's SPI cost per request on the twin, states it, and keeps the probe bounded (its bound
      recorded as "(agent, 2026-10-21)"). An undriven bus reads every chunk blank, so no bound may hide a chip that
      stops answering; a test shows that. P may also edit digital_twin/_fram_chip.py, src/asy_fram_driver.py and
      tests/test_asy_fram_wire_trace.py where its steps need them: no other lane holds them (`S/u35/lead/lanes.py`).
   b. R-9, the config flush in chunks. The lock that serialises config writes stays held across every yield; P3 names
      it by line. The config file is a shared resource (CLAUDE.md's hazard rule), so P3 adds an L1 test: a concurrent
      PUT and a concurrent read of the same file during a yielded write see the old or the new document, never a torn
      one. A twin test follows if the twin's filesystem models commit at close. P3 states the flush's allocation per
      write before and after: no new whole-document copy, slice churn bounded and stated, zero MemoryError at both
      stages.
   c. R-26: T4's build-settrace runs of the twin integration file are heavy processes (arzi takes 119 s plain); one at
      a time.
   d. The coverage-growth finding: U32's coverage CI step grew 603 s to 881 s while the plain run did not, and agent CG
      measures it. When CG reports, the lead routes its fix to the lane that holds the file and adds it to that lane's
      next block.
3. W1 runs four blocks: C1, D1, P1, Y1. CG and the lead's close work (U33, then U34's records block) share the host
   and the six-agent cap. T1 starts when a slot frees; T's chain has slack until W7. Later waves follow P2.3, at most
   five blocks at once, fewer while a lead gate or U34's records block runs.
4. Times (CHECKLIST 14): base and head back to back in one run, alternating. Growth over 10 % and over 0.5 s, or a
   changed file over 10 s, is made efficient, never by cutting strictness. A changed file already over 10 s at base
   must not grow, and its time is stated. An annotation-only edit (MicroPython never evaluates annotations) is timed
   at the head only, at both stages, against its known figure; a paired run follows only if that time is off by more
   than 10 %.
5. The whole `tests_scripts` tier is the lead's, at W6 and W10. A lane's final block runs its readers (P2.2), the 17
   repo-wide scans (`S/u32/briefs/common_u32.md`, "Before your lane's final") and its own files' runs.
6. The host is shared with the lead's U33 gate (until about 17:20 UTC), U33's tier on its squash, U34's gate (about
   75 minutes) and CG's settrace measurements. Every wall-time-bound run obeys CHECKLIST 12.
7. `src/` edits: each file gets an mpy-cross byte compare of base and head, using the pinned build under
   `/root/pico-toolchain` (run it, never write there); the output goes under `S/u35/lane<L>/`.
   - P's files: crc, uart_comm's comments, fram_manager, config_manager, print_log. Y's: system_service's annotations.
   - A comment-only edit keeps its line count where it can. One that moves lines states the moved range (the line
     tables are then the only change); the tests prove the behaviour.
   - Firmware is final at U35's end: every `src/`, device-script, flash and bench edit lands before W6.
8. tests_hardware/twin_record.json: the lead re-records it at W6. H2 may commit only a record its own changed script
   produced (step 140's new shape), never a hand edit.
9. Relay `S/u35/relay.md`, sections C N U P T H Y D W B. The first-commit tokens:
   - C1: <CORE>, <SWEEP>, <NTPF>;
   - D1: <PARTN>; T1: <SHUT>; B1: <T30>; U1: <HANDOVER-UART>;
   - any lane, to D: <TAG name value basis>.
10. Names:
    - commits `U35 lane <L>: <summary>`; branches `audit/u35-<l>`;
    - worktrees `S/wt-u35<l>`, created from `f3fff0e` and set up with `S/u23/rebuild.sh`; logs in `S/u35/lane<L>/`;
    - the lead saves each hand-back as `S/u35/handbacks/<L><n>_final.md`;
    - `python3 -I S/u35/tools/steps.py [--standing] N ...` prints the packet's standing sections and the steps you name.
