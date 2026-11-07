# U21 rulings (lead, 2026-10-08; amend lane_plan.md section 5)

Every ruling takes the plan's default unless stated; each is conservative and reversible, decided on the owner's behalf
and listed for their review at the close (agent, 2026-10-08).

1. A-1 lane cut: default. Wave 1 = T, O, S (three agents, disjoint files); wave 2 = D, E (two agents), last. S's hammer
   stays in S (it needs S's own `test.sh` dispatch and the base's `build-lwip`).
2. A-2 OF-57's apt half comes forward into T: default, with two conditions. (a) Before writing step (3)/(4), T reads
   apt-get(8), apt.conf(5) and dpkg(1) as installed on this host (`man -P cat`, or `/usr/share/doc`), and states in its
   report what a killed `apt-get install --download-only` leaves and whether `/var/cache/apt/archives/partial` resumes;
   if either contradicts the plan, T takes the alternative (one bounded, retried `install`) only if a killed retry
   cannot reach `dpkg`, else reports and keeps the plan's split. (b) `run()`'s streaming is proven by an L0 case with a
   real child that writes a line, sleeps and writes again: the first line must appear before the child exits. Nothing
   runs `apt-get` on this host (L0 fakes only); the first real run is CI's.
3. A-3 mbedtls: branch 2b. Checked by the lead: the scratch chroot is noble (gcc 13, arm-none-eabi-gcc 13.2.1), the host
   the same, so no GCC >= 14 build of either target runs here. The two false SPEC sentences are corrected now.
4. A-4: default (no node record, no Node tree removed).
5. A-5: default (no L0 real-build readback; every real build runs it; lanes prove it on their private toolchain).
   Owner-review item.
6. A-6: default (`tests_hardware/` untouched; T's L0 pins the two globs equal).
7. A-7: default; the U26 note goes into the scan record.
8. A-8 to A-14: defaults.
9. A-15: default (each lane removes its own test file's host-baseline section only when the host pass is clean without
   it); reported as U24's part landed early.
10. A-16: default.
11. A-17 OF-41: default; the structural test must be seen failing on the base first.
12. A-18 to A-20: defaults.
13. A-21 the shared toolchain: default, by the lead only, once, alone (no run reading `/root/pico-toolchain`, nothing
    else heavy), after the merged tree passes L0 and before the U21 gate; offline (`SKIP_APT=1` or the `test`
    subcommand, which runs no apt), no picotool install. Before it, the lead copies `/root/pico-toolchain/micropython`'s
    `ports/unix/build-standard/micropython` and `build-settrace/micropython` to `scratchpad/u21/pretc/` so a pre-U21
    comparison stays possible.
14. A-22 to A-28: defaults.
15. Lane-private toolchains (plan section 8): every build, `setup_toolchain.py test`, firmware build or `test.sh` run in
    a lane uses `PICO_TOOLCHAIN_DIR=<scratch>/u21tc-<lane>` (a `cp -a` copy, never hardlinks), `--jobs 2`, `nice -n 19`,
    inside `flock /tmp/sensors-audit-toolchain.lock` (one build at a time on the host), each entered in
    `scratchpad/u21/RUNS.md` by the lane (one line at start, struck at exit). Disk: each copy ~0.6 GB before builds;
    a lane keeps one copy and deletes nothing outside it.
16. Wave-1 WIP order: O1, T1, S1 in parallel; each hands back "WIP <hash>"; the lead merges into `audit/u21-api`,
    builds the base toolchain once (`scratchpad/u21tc-base`), and resumes each lane with the base hash and the base
    toolchain path.
