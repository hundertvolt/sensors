# Round 1 bench runner brief (lead, 2026-11-05)

Write round 1's bench runner and its handover. Nothing runs against hardware here: a separate bench session on the
owner's Pi4 runs it later, after the owner's go-ahead in that session.

S = `/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad`.

- **Worktree.** `S/wt-bench` (branch `audit/bench-r1`, at `0c10c57c`). This is the bench branch
  `claude/u35-bench-campaign` with the audit head `009f193e` merged in, so outside `audit/` it is the final firmware.
- **Where to write.** New files only, under `audit/artefacts/evidence/U35_close/redo/hw_round1/`.
- **Inputs.**
  - The sheet: `S/u35r/r3/d2/round1_sheet.md`, rows 1-16b.
  - October's runner, the model to follow: reuse its functions. It is in the worktree's
    `audit/artefacts/evidence/U35_close/redo/hw_handover/`, as `run_all.sh`, `handback.py`, `aggregate.py`,
    `HANDOVER.md` and the `mp/` scripts.
  - The repository's runners: `scripts/run_flash_hardware_suite.sh`, `run_bench_hardware_suite.sh`,
    `run_bench_soak_tests.sh`, `run_bench_rollover_test.sh` and `run_manual_hardware_tests.sh`.
  - `tests_hardware/README.md`.
  - BACKLOG.md's "Real-hardware work still owed".
- **Environment and the run wrapper:** `S/u35r/r1/common_r1.md`.

## The owner's words (binding)
- 2026-11-05: "The bench test may go into detail, running a timed script is fine, especially the option to roughly
  define breakpoints was great. It cannot run truly over night. It should live in the branch it was running past
  time."
- 2026-10-28: "interruptible anytime without losses (max 10 minutes wait time)"
- 2026-10-28: "The sessions shall push regularly and dump all details into a single hand back file"

## Design
1. **Interface:** `round1.sh list | run FROM [TO] | summary`, run from the repository root.
   - The steps are numbered and named after the sheet's rows.
   - `list` prints each step's number, name, expected duration and wear (FC/FS/NVM), and whether it needs the owner
     or a setup.
   - `run FROM [TO]` runs that inclusive range in sheet order. The step boundaries are the owner's breakpoints.
   - Like October, `run` first continues `claude/u35-bench-campaign`, fetched.
2. **Stopping:**
   - `touch STOP` ends the run after the current step.
   - While a step runs, the runner checks STOP about every 10 s. If the step is a pytest run or soak with no flash
     cycle in it, the runner sends it SIGINT, so pytest prints what finished.
   - A step that holds a flash cycle (build and flash, the flash-cycle tests, the rollover) is never interrupted.
     `list` marks those steps.
   - Every exit pushes the hand-back, including the running step's partial log. This includes Ctrl-C and kill.
3. **No step spans a night.**
   - No single step runs longer than about 6 h.
   - Row 11's 10 h FRAM run becomes 9-minute `long_fram.py` slices at 8 MHz, for `FRAM_HOURS` (default 2), summed
     across slices as October's aggregate does.
   - On the final image the boot's watchdog stays armed through `mpremote`'s soft reset (the sheet's blocker). Give
     the slice one feed in its loop, in whichever is smaller: the sed-rendered copy in `logs/`, or a minimal edit of
     `mp/long_fram.py`. Say which you chose.
   - The handover proposes a day plan: each launch at most about 10 h, with the ranges per day. Each 6 h soak fills
     its own day, and the owner's bench items fall on a day they are there.
4. **The steps, from the sheet:**
   - **1. Evidence:**
     - `fram_raw_dump.py` (October's render) runs before anything else, on whatever image is on the board.
     - If the product answers, also save `GET /status`, using the harness's own board address.
   - **2. Host:**
     - `uv run toolchain/setup_toolchain.py env --tier bench`.
     - The installed versions of `toolchain/versions.toml`'s `apt_packages`, from dpkg-query.
     - The bridge-under-recovery-timer item is not in the runner. It goes in the handover as the owner's manual line
       (B.13: a second recovery timer armed).
   - **3. Build and flash:** build and flash the final dev image (FC 1), then confirm `/system`'s `build.BuildDate`
     against the build.
   - **4. Flash tier:**
     - The lower levels are a step of their own (long on a Pi4). The tier then runs with `--skip-lower-levels`.
     - Check the sheet's expected-FAIL nodes against the merged head, and list the ones that still stand. The UART
       hazard script's evidence fields were added in R3, so row 9 is no longer blocked. Find whether the loop-lag
       skip (G2) still reads "unexpected skip".
   - **5. Bench tier:**
     - Check whether its runner re-runs L3, and avoid a second whole flash tier (and its prerequisite writes) if the
       runner allows it.
     - Row 6 is a `GET /status` errcount read after steps 4 and 5, taken into the hand-back.
   - **7. Gated run:**
     - Run with `--allow-persistence-write --allow-scd30-extra-write --allow-neopixel-sweep`.
     - Narrow it with `-m` to the gated tests, so ungated ones don't run twice and spend prerequisite writes again.
   - **8. Flash-cycle tests:**
     - Run with `--allow-flash-cycle`, narrowed to the flash-cycle tests.
     - The modlwip send stall's "owner's protocol": find it. If it needs the owner, it goes to the manual list.
   - **9. CRC16 hazard rerun:** row 9's node in crc16 mode. Find how that mode is selected.
   - **10. Soaks:** short, long (6 h), and hotspot case (b) long, as separate steps. Say the true hours of each.
   - **11. FRAM:** the FRAM slices, as point 3.
   - **12a-12f:**
     - The `mp/` scripts, as the sheet says (`CONFIRM` and `MODE` by sed; host scripts get the board's IP).
     - 12d answers "wipe" without a prompt, and only once step 1's evidence exists in `logs/`.
   - **13. Country scan:** runs only with `CH13=1` (the owner's access point on channel 13). Otherwise one skip line.
   - **14. Manual items:** not in the runner. The handover gives the owner the command.
   - **15. Rollover:** last.
   - **16. Read across:** each step's `ResetReason` and errcount from `/status`, in the hand-back.
   - **16b. BMP3XX probe:** the rendered BMP3XX conformance probe (the soft-reset half). The power-on half is manual:
     the owner power-cycles, then reruns this step.
5. **The hand-back:**
   - One `HANDBACK.md` in `hw_round1/`, rebuilt after every step.
   - It holds a verdict line per step, durations, the wear spent so far against the sheet's budget, then the full
     logs.
   - LAN addresses are filtered and no credential is ever printed: reuse `handback.py`'s filter.
   - Commit it `[skip ci]` and push it to `claude/u35-bench-campaign`, with October's retries.
6. **`HANDOVER.md`, concise:**
   - Start a fresh session on the Pi4, check out `claude/u35-bench-campaign`, and get the owner's go-ahead there
     (CLAUDE.md's gate).
   - The commands, the day plan and the manual items.
   - What comes back.

## Constraints (binding)
- **Where you may write:**
  - Only under `hw_round1/`.
  - If an `mp/` script must change, keep the change minimal and say why.
  - Never edit `ext/`.
- **Arduino:** never read `arduino/`. Put `':!arduino'` in every git grep and git log.
- **No hardware or network:**
  - Never run anything against hardware or network config: no mpremote, picotool, nmcli, iw, iptables or curl to a
    board.
  - Never run `round1.sh run`.
- **Allowed checks**, each through `S/u35/lead/run.sh S/wt-bench r1b_<label> <cmd>`, one at a time, at most ten
  runs:
  - `bash -n`, `shellcheck`, `python3 -m py_compile`;
  - `round1.sh list` and `summary`;
  - `uv run pytest -p no:cacheprovider --collect-only -q` of the `tests_hardware` nodes you name.
- **Secrets:**
  - Never print or copy a credential, a Wi-Fi config or the hotspot fallback literal.
  - The runner never prints a config file.
- **Size and style:**
  - Comment blocks are at most 3 lines; markdown lines at most 120 characters.
  - Low complexity: aim at October's size, about 160 lines of shell, and reuse its functions instead of new
    machinery.
- **Hands off:**
  - Never open anything under `/root/.claude/`.
  - Never commit or push. Touch no other worktree.
  - Use `rm` only with literal paths, as its own call.
- **Report**, at most 40 lines:
  - the files and their line counts;
  - the step list with durations and wear;
  - the day plan;
  - what you could not determine;
  - every decision you took.
