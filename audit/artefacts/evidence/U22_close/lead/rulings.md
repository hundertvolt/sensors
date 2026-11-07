# U22 rulings (lead, 2026-10-08; amend lane_plan.md section 5)

Every ruling takes the plan's default (A-1..A-27), each conservative and reversible, decided on the owner's behalf and
listed for their review at the close (agent, 2026-10-08). Checked by the lead against the tree before accepting:
A-3 (`asy_wifi_service.py:458-462` sets `_PHASE_STA_SEEKING` on every non-hotspot reconnect; `:676-680` sets
`_reconn_wifi` from `isconnected()`/`active()` at a task start, so a restart in the silent mode would otherwise leave
it) and A-8 (`buildgen/codegen.py:645-651`: the notification reaches only `/status`'s `notification` block).

Operational rulings:
1. Lanes W, P and T run as wave 1 (three agents, disjoint files: `files_{W,P,T}.txt`); D and E are wave 2, after W, P
   and T have handed back their finals, with the facts relayed.
2. WIP order (plan section 3): W1 and P1 are written in parallel; T does its W-independent parts. Each hands back "WIP
   <hash>". The lead merges W1 and P1 into `audit/u22-api`, regenerates the device modules, runs ruff, the three mypy
   passes and the L0 files W and P touched, and resumes W, P and T on the API base.
3. No toolchain rebuild at U22: `/root/pico-toolchain` is read-only for everyone (its record and three binaries are the
   U21 ones). A lane that finds it needs a rebuild stops and reports.
4. The frozen website (`frozen_modules/`, `build/`) is the lead's: P reports every definitions/sample change and the lead
   rebuilds it in each worktree that runs a full-graph test before that run.
5. Runs: single files only, at `nice -n 19`; at most one heavy run per lane at a time (three lanes, so at most three heavy
   processes plus the lead's one); every port-binding run under `unshare -n`; CONCURRENCY.md (u21 copy) is binding.
6. The twin file's time (A-19): T measures `tests/test_digital_twin_sensortask_integration.py` at both GC stages and under
   settrace; above 168 s at any of the three, T stops and reports, and the lead decides.
7. A-19 decided (lead, 2026-10-12, T's STOP: the grown twin file at 211.7 / 216.1 / 220.7 s, base 61.9 / 65.0 / 70.0 s;
   the three scenarios 53.6 + 65.6 + 31.0 s, all real product time). Taken: the plan's two options combined - ONE boot
   (stage order: (c) the chip-down stations answer in the first hotspot, then (a) the settings change reopening it once
   more, then (b) the window end, the second streak, silent and dark, the later attempt linking; the settings change
   lands in the fresh-boot state, so (b)'s path from there is (b)'s path from a boot) in a NEW twin file
   `tests/test_digital_twin_wifi_modes.py`, the old file back to its base. Real product timing kept (option 3, a fast
   asyncio view, rejected: the L2 tier would stop running the product's real waits - strictness; the owner's standing direction in this session: "not
   cutting back strictness, but making it more efficient"); the shared boot and transitions are the efficiency (~50 s
   less in all), and the two files run in parallel under test.sh. Registration: `wifi_modes` in the role-reversal bench
   file's COVERS_TWIN_SCENARIOS (T's file; no E.6.6 row). Owner-review item.
