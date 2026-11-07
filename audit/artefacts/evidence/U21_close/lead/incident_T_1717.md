# Incident 2026-10-08 17:17:33-~17:20 UTC: a lane-T L0 test ran the real installer against /root/pico-toolchain

Reported by lane T 17:2x; verified and restored by the lead 17:21:17-17:21:38.

Cause: `test_cli_env_has_no_password_option` (tests_scripts/test_setup_toolchain_env.py, lane T, written test-first) ran
`setup_toolchain.py env --tier bench --password x` as a subprocess, expecting argparse to reject `--password`. On the
not-yet-changed code argparse accepted it, so the real `env` path ran: default toolchain dir (~/pico-toolchain), outside
/tmp/sensors-audit-toolchain.lock, at -j4. Breaks the brief ("setup_toolchain.py setup or env anywhere" not allowed;
no apt, sudo or write into /root/pico-toolchain) and plan section 8 ("an L0 case calling main() with setup/test/env
passes --toolchain-dir <tmp_path>"). T stopped it by pid (SIGTERM).

What it changed (T's account, lead-verified where marked V):
- /root/pico-toolchain/.toolchain.lock created (pid 21907) - V; removed by the lead 17:21:38, no holder.
- `sudo apt-get update` (lists 17:17:37) - V; apt history.log has no 2026-10-08 entry, dpkg.log last entry 2026-10-06 - V: no package changed.
- `git fetch` in micropython, pico-sdk, picotool (FETCH_HEAD 17:17:45/46/49) - V; checkouts clean at v1.29.0 0fd6c573e, 2.3.0 98a542c1, 2.3.1 2041936 - V.
- picotool rebuilt, /usr/local/bin/picotool reinstalled 17:18:42, `picotool version` v2.3.1 (GNU-13.3.0) - V.
- mpy-cross/build/mpy-cross re-made 17:18:45 (same source).
- ports/unix/build-standard removed 17:18:46, rebuilt as the frozen-verify variant by 17:19:02 (sha f394adee…) - V;
  restored by the lead from scratchpad/u21/pretc/micropython-standard (sha 177ea20b…, plain, no frozen_verify_test)
  via copy + rename at 17:21:38 - V. The frozen-verify binary kept as u21/incident_build_standard_frozen_verify.bin.
- build_overrides/unix_kbd_intr_variant rewritten, build_overrides/modlwip_eagain created (17:19:02) - V (mtimes);
  left until A-21's rebuild (nothing reads them before).
- ports/rp2/build-RPI_PICO_W removed and partly rebuilt (17:19:11) - V (mtime); left until A-21.
- build-settrace untouched (sha 32c751d2…) - V. No bench, bridge or sudoers step reached.
- Ran beside the lead's base_build2 (u21tc-base, separate dir) for ~2 min: CPU contention only.

Suspect window for runs on the shared build-standard: 17:18:46-17:21:38. Lanes S and O asked to list and re-run any.
Fix required of T: in-process CLI tests with --toolchain-dir tmp and failing runners; an autouse guard (PICO_TOOLCHAIN_DIR
and HOME = tmp_path, failing PATH shims for sudo/apt-get/git/make/cmake/curl/npx/picotool) proven by a deliberate reach.
Owner report: breach of a standing constraint, with this account.
