# Harvest — TOOL: Toolchain installer and build overrides

What the project's own comments, docs and history already record for this area (snapshot `2a88cc8`, moved to `4dc80ef` by V11).
Recorded, not verified or triaged; `audit/HARVEST.md` explains the kinds, tags and method.

Kinds: SETTLED 19, INVAR 28, MIRROR 7, LIMIT 24, RISK 12, ASSUME 20, PLATFORM 18, WORKAROUND 16, SUPPRESS 5, TODO 11, DRIFT 4, NOTE 8 — 172 items.


## tests_hardware/README.md

- **TOOL.N001** WORKAROUND · `tests_hardware/README.md:30-39` — "produced a `picotool` explicitly
  compiled *without* USB support" — A sandbox-built picotool cannot flash; must be rebuilt on the bench
  host (or the apt one checked for the same warning) before any `picotool load`. Removal trigger: none
  stated. · related: TOOL.T09 · [H08]

## REAL_HARDWARE_TEST_QUEUE.md (snapshot only; being updated by another session)

- **TOOL.N002** TODO · `REAL_HARDWARE_TEST_QUEUE.md:283` — "**The two-chroot verification, unsatisfied
  since 2026-09-12**" — H1 OPEN (owner-run): covers setup_toolchain/micropython_overrides changes, two
  Unix ports, rewritten test.sh; the (f) stage never run in any chroot. · related: TOOL.T09 · [H08]
  ⟨4dc80ef: H1 open: BACKLOG.md chroot entry ("Still owed elsewhere")⟩

## dev_legacy/README.md

- **TOOL.N003** WORKAROUND · `dev_legacy/README.md:525-528` — "a stale system-wide install is shadowing
  the toolchain's own rebuilt copy" — picotool version mismatch → rerun `setup_toolchain.py setup`.
  Removal trigger: none stated. · - (low) · [H08]
- **TOOL.N004** SETTLED · `dev_legacy/README.md:554-561` — "It's idempotent: if `br0-wifi-ap` already
  exists ... it's left alone" — `env --tier bench` never recreates or re-randomizes an existing bridge.
  · related: TOOL.T03 · [H08]

## scripts/test.sh

- **TOOL.N005** ASSUME · `scripts/test.sh:75-77` — "compiling MICROPY_PY_SYS_SETTRACE in allocates a
  frame and a code object per call ... inflating every allocation figure 4-5x" — Single measured figure
  (Part E.5.2) justifying the two-binary split. · related: TOOL.T05 · [H09]

## scripts/build_firmware.py

- **TOOL.N006** MIRROR · `scripts/build_firmware.py:39-45` — "Mirrors the two stock manifests combined:
  their require()s and freeze(\"$(PORT_DIR)/modules\") are reused unchanged" — Depends on the pinned
  MicroPython's stock `boards/{board}/manifest.py` layout. · related: TOOL.T04 · [H09]
- **TOOL.N007** RISK · `scripts/build_firmware.py:151-158` — "mpy-cross's build/ does not self-clean per
  build ... so it is wiped here" — Wipes a shared toolchain build dir; unsafe under concurrent builds. ·
  covered-by: TOOL.T08 · [H09]
- **TOOL.N008** PLATFORM · `scripts/build_firmware.py:152-153` — "the rp2 port's own implicit sub-build
  fails from a freshly wiped directory (Part B.11)" — Version-specific build-system behaviour. · [H09]
- **TOOL.N009** LIMIT · `scripts/build_firmware.py:118` —
  "default=Path(os.environ.get(\"PICO_TOOLCHAIN_DIR\", ...))" — `--toolchain-dir` not resolved to
  absolute. · covered-by: TOOL.S05 · [H09]

## toolchain/versions.toml

- **TOOL.N010** ASSUME · `toolchain/versions.toml:3-5` — "pico-sdk is derived from MicroPython's own
  lib/pico-sdk submodule at this ref, picotool as the newest tag matching its major.minor" — picotool
  floats within major.minor; only the MicroPython ref is pinned by hand. · covered-by: TOOL.T02 · [H09]
- **TOOL.N011** LIMIT · `toolchain/versions.toml:7-8` — "or run the installer with --latest to write
  back the newest stable tag" — `--latest` moves the pin without prompting the mandatory re-check. ·
  covered-by: TOOL.S09 · [H09]
- **TOOL.N012** LIMIT · `toolchain/versions.toml:14-29` — "\"gcc-arm-none-eabi\"," — apt packages
  (including the ARM compiler) are distro-versioned and unpinned. · covered-by: TOOL.T12 · [H09]
- **TOOL.N013** MIRROR · `toolchain/versions.toml:26-28` — "setcap, for the port-53 DNS-server test's
  CAP_NET_BIND_SERVICE grant: absent from a minimal image" — `libcap2-bin` is also listed by hand in
  CLAUDE.md's chroot recipe for reused chroots. · [H09]
- **TOOL.N014** INVAR · `toolchain/versions.toml:31-40` — "AN ENSEMBLE, NOT INDEPENDENT KNOBS ... three
  per-connection relationships lwIP does not check are all re-stated by check_lwip_ensemble()" — lwIP
  option set must stay coherent; enforced by `check_lwip_ensemble()`. · covered-by: TOOL.T04 · [H09]

## toolchain/micropython_overrides.py

- **TOOL.N015** SETTLED · `toolchain/micropython_overrides.py:1-3, 15-18` — "Re-verify against the new
  source and update the override's anchor/generated content (SPECIFICATION.md Part B.14) - never silence
  this by removing the check." — Every override fails loudly on anchor drift; re-verification trigger is
  any MicroPython ref move (CLAUDE.md standing practice, B.14 checklist). · covered-by: TOOL.T04 · [H09]
- **TOOL.N016** PLATFORM · `toolchain/micropython_overrides.py:37-40` — "_UNIX_KBD_INTR_ANCHOR =
  \"#define MICROPY_ASYNC_KBD_INTR (!MICROPY_PY_THREAD_GIL)\"" — Anchor 1 (unix_kbd_intr): exact
  unguarded line in `ports/unix/variants/mpconfigvariant_common.h`; re-verify on every ref move. ·
  covered-by: TOOL.T04 · [H09]
- **TOOL.N017** PLATFORM · `toolchain/micropython_overrides.py:38-39` — "a later plain #define always
  wins over an earlier -D (verified 2026-09-15), and the redefinition warning is a hard failure here
  anyway" — Preprocessor/build-flag fact the override design depends on (dated verification). · [H09]
- **TOOL.N018** LIMIT · `toolchain/micropython_overrides.py:43-57` — "the async/immediate
  nlr_raise()-from-signal-handler mechanism itself was restructured in ports/unix/unix_mphal.c's
  sighandler()" — The check verifies only the header line text, not the `sighandler()` mechanism, and no
  post-build proof shows `MICROPY_ASYNC_KBD_INTR == 0` in the binary. · covered-by: TOOL.S07 · [H09]
- **TOOL.N019** SETTLED · `toolchain/micropython_overrides.py:53-55` — "Do NOT remove this check and
  build unpatched: the whole point is that an interrupt-mid-critical-section can corrupt VM state" —
  Standing rule tied to CLAUDE.md's shutdown-flake entry (Part F.6/B.14.1). · [H09]
- **TOOL.N020** ASSUME · `toolchain/micropython_overrides.py:75-77, 338-342` — "relay to the real files
  rather than copying their content, so neither can silently drift" — Relay-by-include design assumed
  drift-proof; `manifest.py` relayed only if it exists (:81-83). · related: TOOL.T04 · [H09]
- **TOOL.N021** PLATFORM · `toolchain/micropython_overrides.py:98-103` — "Split by how the PINNED source
  defines each macro, because that is what decides whether a plain -D could ever be trusted for it" —
  Guarded vs predefined macro classification is pinned-source specific. · covered-by: TOOL.T04 · [H09]
- **TOOL.N022** PLATFORM · `toolchain/micropython_overrides.py:105-118` — "The MEM_SIZE group is ONE
  atomic `#ifndef MEM_SIZE` block upstream, so a -D of any of it would drop TCP_MSS to lwIP's 536" —
  Anchor 2 set (`_LWIP_COMMON_ANCHORS`): exact default lines of `extmod/lwip-include/lwipopts_common.h`;
  re-verify on a ref move. · covered-by: TOOL.T04 · [H09]
- **TOOL.N023** INVAR · `toolchain/micropython_overrides.py:119-125` — "lwip_inc must stay a PLAIN
  target-level include dir: a BEFORE form there would beat the directory-scope one this override
  prepends" — Anchor 3 set (`_RP2_CMAKE_ANCHORS`) guards rp2 CMake include ordering;
  `_RP2_LWIPOPTS_ANCHOR` (:126) and `_BOARD_CMAKE_ANCHOR` (:127) are anchors 4-5. · covered-by: TOOL.T04
  · [H09]
- **TOOL.N024** SETTLED · `toolchain/micropython_overrides.py:129-134` — "Do NOT remove the check and
  build anyway: an lwIP option that silently keeps its old value produces a firmware that accepts fewer
  connections" — Standing rule. · [H09]
- **TOOL.N025** INVAR · `toolchain/micropython_overrides.py:166-168` — "for name in
  (\"mpconfigboard.h\", \"manifest.py\", \"pins.csv\"):" — Board dir shape anchor: generated board dir
  relays exactly these three files. · covered-by: TOOL.T04 · [H09]
- **TOOL.N026** MIRROR · `toolchain/micropython_overrides.py:171-173, 190-202, 214-247` — "Mirrored here
  to fail before the build, naming the relationship" — Python re-statement of `lib/lwip/src/core/init.c`
  #errors and `opt.h`'s four derived formulas; must be re-checked against lwIP whenever the pin moves. ·
  covered-by: TOOL.T04 · [H09]
- **TOOL.N027** SUPPRESS · `toolchain/micropython_overrides.py:224` — "# noqa: PLR2004 - init.c's own
  literal" — Magic-number suppression. · [H09]
- **TOOL.N028** INVAR · `toolchain/micropython_overrides.py:318-321, 448-458` — "The sentinel closes the
  one hole a value comparison cannot" — Post-build proof for lwIP (sentinel + preprocessor readback);
  none exists for unix_kbd_intr. · covered-by: TOOL.T11 · [H09]
- **TOOL.N029** LIMIT · `toolchain/micropython_overrides.py:329-336` — "include_directories(BEFORE
  \"{include_dir}\")" — Generated CMake/make include paths are unquoted in `include(...)`; relative
  paths or spaces break. · covered-by: TOOL.S05 · [H09]
- **TOOL.N030** LIMIT · `toolchain/micropython_overrides.py:355-388` — "lwIP options are arithmetic over
  literals, and anything else must fail loudly, not guess" — Readback evaluator supports only + - * / <<
  >>; any cast/ternary in a future lwIP option fails the build. · [H09]
- **TOOL.N031** ASSUME · `toolchain/micropython_overrides.py:391-402` — "else the toolchain's usual name
  on PATH" — Falls back to `arm-none-eabi-gcc` on PATH if CMake's record is missing. (low) · [H09]
- **TOOL.N032** PLATFORM · `toolchain/micropython_overrides.py:409, 417-420` — "flags.make ... has no
  {key} line - CMake's generated layout has changed" — Readback depends on CMake's
  `CMakeFiles/firmware.dir/flags.make` layout (C_DEFINES/C_INCLUDES/C_FLAGS). · related: TOOL.T11 ·
  [H09]

## toolchain/setup_toolchain.py

- **TOOL.N033** WORKAROUND · `toolchain/setup_toolchain.py:33-36, 335, 379` — "Confirmed GCC >=14 false
  positive in mbedtls_xor(), not a real bug ... See Part B.7.1 for the periodic-recheck instructions
  before ever removing this." — `-Wno-array-bounds` is passed via CFLAGS_EXTRA to the whole rp2 firmware
  and both Unix-port builds, not only mbedtls; removal trigger: B.7.1's periodic recheck. · related:
  CI.T10 · [H09]
- **TOOL.N034** SUPPRESS · `toolchain/setup_toolchain.py:36` — "_MBEDTLS_GCC14_ARRAY_BOUNDS_WORKAROUND =
  \"-Wno-array-bounds\"" — Compiler-warning class disabled build-wide (every translation unit), while
  any other warning fails the build. · related: TOOL.T10 · [H09]
- **TOOL.N035** INVAR · `toolchain/setup_toolchain.py:73-82` — "never the caller's raw environment ...
  build failure detection greps build output for literal English \"error:\"/\"warning:\"" — Fixed
  PATH/locale allowlist; failure detection is an English-text grep (Part B.4/B.7). · covered-by:
  TOOL.T10 · [H09]
- **TOOL.N036** INVAR · `toolchain/setup_toolchain.py:84-91` — "Named explicitly rather than inherited
  wholesale, so it stays only ever these variables." — Proxy/CA allowlist for network steps; `PIP_CERT`
  and others are not in it. · related: TOOL.T01 · [H09]
- **TOOL.N037** LIMIT · `toolchain/setup_toolchain.py:154-157` — "new_text = re.sub(r'(?m)^ref =
  \".*\"$', f'ref = \"{ref}\"', text, count=1)" — Rewrites the first `ref = ` line; silent no-op if
  nothing matches. · covered-by: TOOL.S09 · [H09]
- **TOOL.N038** SUPPRESS · `toolchain/setup_toolchain.py:166-168` — "Non-fatal: unrelated third-party
  sources some environments have configured (PPAs etc.)" — `apt-get update` failure ignored
  (`check=False`). · covered-by: TOOL.T10 · [H09]
- **TOOL.N039** RISK · `toolchain/setup_toolchain.py:169-172` — "[\"sudo\", \"env\",
  \"DEBIAN_FRONTEND=noninteractive\", \"apt-get\", \"install\"" — `sudo env` likely drops proxy
  variables set in `network_env()`. · covered-by: TOOL.S04 · [H09]
- **TOOL.N040** SETTLED · `toolchain/setup_toolchain.py:184-186` — "Deliberately a full clone, not
  `--depth 1`" — In-place update is a first-class requirement. · [H09]
- **TOOL.N041** SUPPRESS · `toolchain/setup_toolchain.py:195-200` — "except SetupError: # The commit
  wasn't already present locally ... fetch it directly by hash. pass" — Checkout failure swallowed then
  retried via fetch-by-hash. · related: TOOL.T02 · [H09]
- **TOOL.N042** LIMIT · `toolchain/setup_toolchain.py:193` — "[\"git\", \"fetch\", \"--quiet\",
  \"--tags\", \"--force\", \"origin\"]" — Tags are force-fetched (a moved upstream tag is silently
  accepted); pin is a tag, not a SHA. · covered-by: TOOL.T02 · [H09]
- **TOOL.N043** ASSUME · `toolchain/setup_toolchain.py:224-233` — "read straight out of MicroPython's
  own submodule pin at lib/pico-sdk" — pico-sdk derivation parses `git ls-tree` output shape. · [H09]
- **TOOL.N044** PLATFORM · `toolchain/setup_toolchain.py:236-255` — "(\"Incompatible picotool
  installation found\" since pico-sdk 2.0.0)" — picotool = newest tag matching pico-sdk major.minor,
  from a live `ls-remote` (floats). · covered-by: TOOL.T02 · [H09]
- **TOOL.N045** RISK · `toolchain/setup_toolchain.py:258, 276` — "run([\"sudo\", \"make\", \"install\"],
  cwd=build_dir, env=env)" — Every `setup` (including test.sh's auto-build) installs picotool into
  `/usr/local` as root. · covered-by: TOOL.S08 · [H09]
- **TOOL.N046** LIMIT · `toolchain/setup_toolchain.py:292-294` — "if re.search(r\"\bwarning:\", out,
  re.IGNORECASE):" — mpy-cross build checks warnings but not `error:` text (relies on exit code). (low)
  · related: TOOL.T10 · [H09]
- **TOOL.N047** INVAR · `toolchain/setup_toolchain.py:321-350` — "Always applies and then verifies the
  lwip_connection_counts override" — Every firmware build (incl. the verification chain) goes through
  the override and its post-build readback. · covered-by: TOOL.T04 · [H09]
- **TOOL.N048** ASSUME · `toolchain/setup_toolchain.py:373-374` — "the Makefile's own `BUILD ?= build-$(VARIANT)`
  already lands the settrace-free rig in build-standard, which every other script resolves" — Build dir
  naming relies on upstream Makefile default; five scripts hard-code `build-standard`. · related:
  SCR.S05 · [H09]
- **TOOL.N049** DRIFT · `toolchain/setup_toolchain.py:491-493, 540-547` — "The 8-step frozen-bytecode
  verification chain" / "8. Vanilla Unix port rebuilt as the standing test rig" — The settrace build
  (:517) is an unlisted extra step; the printed summary never mentions it. (low) · related: TOOL.T11 ·
  [H09]
- **TOOL.N050** LIMIT · `toolchain/setup_toolchain.py:458-469` — "the only way this can succeed is if
  the module was actually baked into the binary" — The chain proves freezing works with a probe module,
  not that the project's own frozen set or overrides landed. · covered-by: TOOL.T11 · [H09]
- **TOOL.N051** LIMIT · `toolchain/setup_toolchain.py:479-481` — "the verification chain builds the
  default variant, never the settrace one" — Frozen-bytecode verification is never run against the
  settrace binary. (low) · [H09]
- **TOOL.N052** LIMIT · `toolchain/setup_toolchain.py:554-560` — "mpy_ref = args.micropython_ref" —
  `--micropython-ref` builds a ref recorded nowhere; `--latest` rewrites the pin without the re-check. ·
  covered-by: TOOL.S06 · [H09]
- **TOOL.N053** ASSUME · `toolchain/setup_toolchain.py:619-621` — "Submodules are assumed already
  fetched." — `test` subcommand is offline and trusts the existing checkout. · [H09]
- **TOOL.N054** LIMIT · `toolchain/setup_toolchain.py:686-691` — "log(\"Skipping dialout group check
  (--skip-apt)\")" — `--skip-apt` also skips the dialout group step. · covered-by: TOOL.S04 · [H09]
- **TOOL.N055** MIRROR · `toolchain/setup_toolchain.py:790-794` — "Connection names match
  dev_legacy/README.md's manual nmcli recipe exactly" — `br0`/`br0-eth0`/`br0-wifi-ap` must stay
  identical to the manual recipe. · related: TOOL.T03 · [H09]
- **TOOL.N056** RISK · `toolchain/setup_toolchain.py:815-840` — "Idempotent: loads br_netfilter and
  enables net.bridge.bridge-nf-call-iptables=1" — Persistent host-wide kernel/sysctl files written as
  root; temp file leaks if `sudo cp` fails. · covered-by: TOOL.S04 · [H09]
- **TOOL.N057** SETTLED · `toolchain/setup_toolchain.py:843-846, 860-862` — "A bridge MAC mismatch is
  flagged, never auto-repaired" — Repairing a live bridge's MAC needs a human decision (SSH-loss risk).
  · related: TOOL.T03 · [H09]
- **TOOL.N058** RISK · `toolchain/setup_toolchain.py:852-859` — "Self-heal a bridge created before the
  channel-pinning fix" — Re-runs `nmcli connection modify/up` on an existing live AP with no dead-man's
  switch armed. · related: TOOL.T03 · [H09]
- **TOOL.N059** INVAR · `toolchain/setup_toolchain.py:868-871` — "`--escape no` is load-bearing" —
  Without it the MAC comparison always mismatches and prints a remedy that cycles a live bridge. ·
  related: TOOL.T03 · [H09]
- **TOOL.N060** RISK · `toolchain/setup_toolchain.py:893-925` — "run([\"sudo\", \"nmcli\",
  \"connection\", \"up\", BENCH_ETH_CONN], env=env)" — Bridge creation enslaves the uplink with no
  dead-man's switch (the 2026-09-04 lockout operation). · covered-by: TOOL.S03 · [H09]
- **TOOL.N061** LIMIT · `toolchain/setup_toolchain.py:1063-1068` — "run_setup(args, versions_path,
  versions)" — Every `env` tier always runs a full `setup` (sudo apt, picotool install). · covered-by:
  TOOL.T13 · [H09]
- **TOOL.N062** SETTLED · `toolchain/setup_toolchain.py:1147-1153` — "Backward/convenience compat:
  `setup_toolchain.py [--some-setup-flag ...]` (no subcommand) still means \"setup\"" — Implicit default
  subcommand kept deliberately. · [H09]

## tests_scripts/test_micropython_overrides.py

- **TOOL.N063** PLATFORM · `tests_scripts/test_micropython_overrides.py:16,60-65` — "_REAL_ANCHOR_LINE =
  \"#define MICROPY_ASYNC_KBD_INTR (!MICROPY_PY_THREAD_GIL)\"" — Exact v1.29.0 source line the SIGINT
  override is anchored to; any textual drift is "unverified", never fuzzy-matched; only the anchor text
  is checked, not the mechanism · covered-by: TOOL.S07 · [H10]
- **TOOL.N064** SUPPRESS · `tests_scripts/test_micropython_overrides.py:44-49,346-350` —
  "pytest.skip(f\"no real toolchain checkout at {micropython_dir} - build it first (scripts/test.sh
  does)\")" — The only two checks against the REAL pinned source (kbd-intr anchor, 21 lwIP anchors) skip
  without a provisioned toolchain; everything else runs on synthetic trees · related: TEST.T13 · [H10]
- **TOOL.N065** INVAR · `tests_scripts/test_micropython_overrides.py:135-138,237-252` — "must fail a
  test rather than silently ship an unpatched binary again" — Pins build_unix_port() applying the
  override and raising before `make` when the anchor is unverifiable ("again" implies a past unpatched
  ship) · related: TOOL.T04 · [H10]
- **TOOL.N066** INVAR · `tests_scripts/test_micropython_overrides.py:197-224` — "compiled in, the flag
  allocates a frame and a code object per call, inflating every figure the memory work measures 4-5x" —
  Rig binary must be settrace-free, coverage binary settrace-enabled in its own build dir (2026-09-21
  split, E.5.2); test.sh and conftest.py must spell both dir names (enforced by substring) · related:
  TOOL.T05 · [H10]
- **TOOL.N067** LIMIT · `tests_scripts/test_micropython_overrides.py:226-232` — "assert
  \"build_unix_port(micropython_dir, toolchain_dir, jobs, settrace=True)\" in source" — "setup builds
  both variants" is proven by an exact source-substring match, not by exercising `setup` (low) · [H10]
- **TOOL.N068** PLATFORM · `tests_scripts/test_micropython_overrides.py:320-344` — "18 text anchors plus
  the three relayed board files" — 21 pinned lwIP/rp2/board-cmake anchor strings from the v1.29.0 tree
  (incl. "trap B" plain `MEMP_NUM_UDP_PCB` define, `LWIP_NETCONN 0` making MEMP_NUM_NETCONN a no-op);
  each proven load-bearing and the list pinned equal to the code's · related: TOOL.T04 · [H10]
- **TOOL.N069** MIRROR · `tests_scripts/test_micropython_overrides.py:447-481,563-568` —
  "lib/lwip/src/core/init.c turns each of these into a compile-time #error, and opt.h derives four more
  values from them" — `derive_lwip_dependents`/`check_lwip_ensemble` restate lwIP's opt.h formulas and
  init.c checks in Python; must be re-derived when lwIP moves · related: PLAT.T04 · [H10]
- **TOOL.N070** ASSUME · `tests_scripts/test_micropython_overrides.py:480-481,454-458` — "the pinned
  block sits exactly on lwIP's own MEMP_NUM_TCP_SEG >= TCP_SND_QUEUELEN boundary, 32 against 32" —
  MicroPython's own lwIP defaults (PCB 5, MEM_SIZE 8000, MSS 800, WND/SND_BUF 6400, SEG 32) hand-copied
  into `_pinned()` · [H10]
- **TOOL.N071** INVAR · `tests_scripts/test_micropython_overrides.py:649-652` — "Values alone cannot
  prove the shim was REACHED" — Generated lwipopts.h carries a sentinel that the build readback must
  find · covered-by: TOOL.T11 · [H10]
- **TOOL.N072** LIMIT · `tests_scripts/test_micropython_overrides.py:658-660` — "Driven through a stub
  compiler, so every outcome of the real `-E` run is reachable without an ARM toolchain." — Readback
  logic is tested only with a stub compiler here; the real `-E` run happens only in a real firmware
  build · [H10]
- **TOOL.N073** LIMIT · `tests_scripts/test_micropython_overrides.py:792-793` — "(\"800U\", \"cannot
  parse\"), # the options set here never carry a suffix - refuse, not guess" — Macro evaluator refuses
  casts and integer suffixes by design · [H10]

## tests_scripts/test_setup_toolchain_env.py

- **TOOL.N074** LIMIT · `tests_scripts/test_setup_toolchain_env.py:1-7` — "never real hardware, sudo, or
  network" / "End-to-end behavior - USB detection, the bridge and AP working - is proven on the real
  bench unit instead" — `env` tiers are tested only against a recording fake `run()` and fake /sys; the
  real bridge/AP path is verified manually on the bench, not in CI · related: TOOL.T13 · [H10]
- **TOOL.N075** LIMIT · `tests_scripts/test_setup_toolchain_env.py:269-271` — "`nmcli -g`'s own ':'
  escaping modelled - without either, the MAC check passes here while never matching on hardware" — Fake
  fidelity explicitly limited to the nmcli/ip output shapes it models · [H10]
- **TOOL.N076** SETTLED · `tests_scripts/test_setup_toolchain_env.py:335-337` — "must be flagged and
  never auto-repaired - cycling a live bridge's MAC risks the same SSH-drop" — Pins CLAUDE.md's
  2026-09-04 lockout rule: MAC mismatch warns only; on creation the MAC pin precedes `connection up br0-eth0`
  (enforced by ordering assert, :403-416) · related: TOOL.T03 · [H10]
- **TOOL.N077** PLATFORM · `tests_scripts/test_setup_toolchain_env.py:409,314` — "assert
  any(\"wifi-sec.pmf disable\" in c for c in joined) # load-bearing cyw43439 tuning" — Bench AP must
  disable PMF for the CYW43439 and pin channel 6 (a pre-fix bridge on channel 13 is self-healed) ·
  related: HW.T07 · [H10]
- **TOOL.N078** WORKAROUND · `tests_scripts/test_setup_toolchain_env.py:480-514` — "run() failing its
  first `failures` calls the way a 502 from a release download does" — `uv sync` retried
  UV_SYNC_ATTEMPTS=3 with 10 s/20 s pauses for transient upstream download failures; removal trigger:
  none stated · related: CI.S17 · [H10]
- **TOOL.N079** LIMIT · `tests_scripts/test_setup_toolchain_env.py:464-465` — "the soft skip is still
  the right outcome - it is only the *silent* skip on a pinned repo that was wrong" — npm install is
  silently skipped when neither .nvmrc nor npm exists (deliberate) · [H10]
- **TOOL.N080** ASSUME · `tests_scripts/test_setup_toolchain_env.py:533-534` — "never to override a
  correct Node the caller already manages (nvm, a system install, CI's own setup-node)" — ensure_node
  defers to any PATH node whose major matches; only the major is compared · related: TOOL.S02 · [H10]

## SPECIFICATION.md Part B intro, B.1-B.3 (688-753)

- **TOOL.N081** INVAR · `SPECIFICATION.md:700-703` — "The four pieces must agree exactly, or the build
  silently breaks" — MicroPython/pico-sdk/picotool/ARM GCC coherence is derived, not pinned separately.
  · related: TOOL.T02 · [H12]
- **TOOL.N082** SETTLED · `SPECIFICATION.md:725-728` — "Both subcommands also build/verify two Unix-port
  interpreters (owner decision, 2026-09-21)" — build-standard without settrace, build-settrace for
  --coverage only; firmware never gets the flag. · related: TOOL.T05 · [H12]
- **TOOL.N083** PLATFORM · `SPECIFICATION.md:738-739` — "Ubuntu's `universe` component (default on real
  Ubuntu images — `gcc-arm-none-eabi` lives there)" — Distro-packaging prerequisite. · [H12]
- **TOOL.N084** ASSUME · `SPECIFICATION.md:746-747` — "Derive the matching `picotool` version by
  resolving that commit to its nearest tag, taking major.minor, picking the newest `picotool` tag
  sharing it" — Heuristic version derivation; floats as picotool tags appear. · covered-by: TOOL.T02 ·
  [H12]
- **TOOL.N085** RISK · `SPECIFICATION.md:748` — "Install the ARM cross-compiler from `apt`'s
  `gcc-arm-none-eabi` (no pin needed)." — Compiler unpinned — the GCC-14 mbedtls break (B.7.1) shows a
  pin can matter. · covered-by: TOOL.T12 · [H12]

## SPECIFICATION.md Part B.4-B.9 (754-826)

- **TOOL.N086** INVAR · `SPECIFICATION.md:761-765` — "Every subprocess ... gets an explicit, constructed
  environment, never the caller's shell wholesale" — Isolation convention with one stated exception
  (B.12 :1009-1011). · related: TOOL.T01 · [H12]
- **TOOL.N087** RISK · `SPECIFICATION.md:770` — "`picotool`'s install location is pinned explicitly
  (`-DCMAKE_INSTALL_PREFIX=/usr/local`)" — Host-wide install via `sudo make install` (B.5:778). ·
  covered-by: TOOL.T09 · [H12]
- **TOOL.N088** SETTLED · `SPECIFICATION.md:785` — "Full (non-shallow) clones — shallow clones make the
  update path unreliable." — Deliberate full clones. · [H12]
- **TOOL.N089** ASSUME · `SPECIFICATION.md:803-807` — "Verified end-to-end in a clean `debootstrap`
  Ubuntu 24.04 chroot for both the deployed `v1.26.1` and latest stable ... `test` alone completes in
  ~30s offline" — Undated evidence claim from an earlier pin; CLAUDE.md dates the chroot legs
  2026-09-12. · related: HW.T16 · [H12]
- **TOOL.N090** WORKAROUND · `SPECIFICATION.md:811-817` — "Worked around via `-Wno-array-bounds` in
  `_MBEDTLS_GCC14_ARRAY_BOUNDS_WORKAROUND` ... recheck its status, and whether a future MicroPython ref
  vendors mbedtls ≥3.6.6, before removing this" — GCC ≥14 false positive (Debian #1085354, GCC #121044
  UNCONFIRMED); removal trigger stated; applied to every build (`toolchain/setup_toolchain.py:335, 379`).
  · related: CI.T10 · [H12]

## SPECIFICATION.md Part B.11 (Building this project's firmware, 931-984)

- **TOOL.N091** INVAR · `SPECIFICATION.md:937-939` — "change `versions.toml`'s `[micropython] ref` — the
  only place. Everything else derives automatically" — Single-source pin; `--micropython-ref`/`--latest`
  paths bypass or move it silently. · related: TOOL.S06 · [H12]

## SPECIFICATION.md Part B.12 (Tiered dev-environment setup, 986-1014)

- **TOOL.N092** INVAR · `SPECIFICATION.md:997-1000` — "Exactly one match required; zero or multiple is a
  hard error naming `--device` as the escape hatch, never a silent guess." — USB detection by
  `idVendor=2e8a`. · [H12]
- **TOOL.N093** RISK · `SPECIFICATION.md:1002-1007` — "A genuinely new bridge gets fresh random
  SSID/password (`secrets`-generated) unless overridden, printed once at creation only." — Bench AP
  secret printed (and in argv per TOOL.S01). · covered-by: TOOL.S01 · [H12]
- **TOOL.N094** SETTLED · `SPECIFICATION.md:1009-1013` — "runs with `env=None` (inherit the caller's
  real environment) — the one deliberate exception to this script's isolation convention" — Deliberate
  isolation exception for uv/npm. · [H12]
- **TOOL.N095** LIMIT · `SPECIFICATION.md:1014-1018` — "Not exercised there: actually flashing a
  physical board, or creating the bridge/AP ... Full flash/bench real-hardware verification is DONE ...
  (2026-09-04)" — Sandbox cannot verify flash/bench tiers; single dated bench verification. · related:
  TOOL.T13 · [H12]

## SPECIFICATION.md Part B.13 (Bench network safety, 1016-1061)

- **TOOL.N096** SETTLED · `SPECIFICATION.md:1032-1038` — "`ensure_bench_bridge()` now pins
  `bridge.mac-address` ... and warns (never auto-repairs — cycling a live bridge's MAC risks the same
  incident)" — Deliberately warn-only. · related: TOOL.T03 · [H12]

## SPECIFICATION.md Part B.14 (MicroPython build overrides framework, 1063-1114)

- **TOOL.N097** ASSUME · `SPECIFICATION.md:1069` — "so far: two implemented, one identified and planned"
  — Dated count. (low) · [H12]
- **TOOL.N098** INVAR · `SPECIFICATION.md:1074-1077` — "every override there generates files or extra
  build flags entirely *outside* the fetched checkout (never a single byte written into it)" —
  Zero-touch rule by convention. · related: TOOL.T04 · [H12]
- **TOOL.N099** PLATFORM · `SPECIFICATION.md:1090-1094` — "confirmed directly (2026-09-15) that a later
  plain `#define` in the same translation unit always wins over an earlier command-line `-D`" —
  Toolchain fact behind the header mechanism. · [H12]
- **TOOL.N100** SETTLED · `SPECIFICATION.md:1104-1105` — "there is no opt-out flag, since an override
  existing at all means the *unpatched* build is the one considered unsafe" — No opt-out by design. ·
  [H12]
- **TOOL.N101** ASSUME · `SPECIFICATION.md:1108-1112` — "every one of them reaches the toolchain build
  through this same entry point, with no alternate path anywhere in this project's own tooling" — But
  twin/web runners reuse a cached binary without rebuilding on override change. · related: TOOL.T07 ·
  [H12]

## SPECIFICATION.md Part B.14.1 (`unix_kbd_intr`, 1116-1213)

- **TOOL.N102** WORKAROUND · `SPECIFICATION.md:1163-1169` — "`apply_unix_kbd_intr_override()` forces
  this path for the Unix \"standard\" variant ... without editing anything inside the fetched checkout"
  — Upstream Unix-port async SIGINT (`MICROPY_ASYNC_KBD_INTR`) workaround; removal trigger at :1215-1217
  (upstream default inverted). · related: TOOL.S07 · [H12]
- **TOOL.N103** PLATFORM · `SPECIFICATION.md:1170-1176` — "`VARIANT_DIR ?= variants/$(VARIANT)` ... a
  `CFLAGS_EXTRA`-appended `-I` was tried and empirically confirmed to lose" — Makefile-ordering facts
  the override depends on. · [H12]
- **TOOL.N104** SETTLED · `SPECIFICATION.md:1179-1185` — "Deliberately never a symlink: MicroPython
  issue #12671" — Symlinked variant dir breaks; real files with absolute includes. · [H12] ⟨quote not
  matched at the anchor⟩
- **TOOL.N105** ASSUME · `SPECIFICATION.md:1198-1202` — "ran clean for a combined 700+ iterations
  against the patched binary with zero shutdown failures" — Single hammer-loop verification
  (2026-09-14/15). · [H12]
- **TOOL.N106** LIMIT · `SPECIFICATION.md:1197-1198` — "preprocessing the resulting `unix_mphal.c`
  directly confirms the safe branch" — One-off manual proof; no in-build readback. · covered-by:
  TOOL.S07 · [H12]

## SPECIFICATION.md Part B.14.2 / B.14.2.1 (`lwip_connection_counts`, 1215-1379)

- **TOOL.N107** PLATFORM · `SPECIFICATION.md:1239-1246` — "one atomic `#ifndef MEM_SIZE` block (8000 /
  800 / 6400 / 6400 / 32 as pinned). Defining `MEM_SIZE` alone on the command line disables the whole
  block" — Trap the override must avoid. · [H12]
- **TOOL.N108** ASSUME · `SPECIFICATION.md:1259-1266` — "checks twenty-one anchors ... a completeness
  test pins that list to the code's own" — Count; enforced by
  `tests_scripts/test_micropython_overrides.py`. · [H12]
- **TOOL.N109** INVAR · `SPECIFICATION.md:1277-1284` — "`verify_lwip_macros_in_build()` ...
  `build_firmware()` calls it after every build" — Post-build proof (asymmetry with unix_kbd_intr). ·
  covered-by: TOOL.T11 · [H12]
- **TOOL.N110** MIRROR · `SPECIFICATION.md:1287-1298` — "`check_lwip_ensemble()` restates every one of
  them ... `derive_lwip_dependents()` reproduces opt.h's four formulas" — Python restatement of lwIP
  `init.c` `#error`s / `opt.h` derivations; drifts on lwIP bump. · covered-by: TOOL.T04 · [H12]
- **TOOL.N111** INVAR · `SPECIFICATION.md:1301-1304` — "Its own checks size the shared pools for one
  connection ... (and a `max_connections` below 1 is refused by name" — Three N-connection relationships
  lwIP doesn't check, enforced by the override. · [H12]
- **TOOL.N112** MIRROR · `SPECIFICATION.md:1374-1378` — "update the anchor list and
  `LWIP_MACROS_GUARDED_IN_OPT_H`/`LWIP_MACROS_PREDEFINED_BY_MICROPYTHON` together" — Two lists that must
  move in step on a bump. · [H12]

## SPECIFICATION.md Part B.14.3 (`littlefs_flash_storage_size`, 1381-1410)

- **TOOL.N113** TODO · `SPECIFICATION.md:1385-1394` — "(documented, not yet implemented) ... Mechanism,
  verified workable against the pinned source, not yet wired in" — Planned override not implemented. ·
  covered-by: TOOL.T06 · [H12]
- **TOOL.N114** TODO · `SPECIFICATION.md:1403-1408` — "What a real implementation still needs: a
  `verify_littlefs_flash_storage_size_anchor()`" — Missing anchor check spelled out. · [H12]

## SPECIFICATION.md Part E.5 / E.5.1-E.5.3 (Coverage, 2951-3088)

- **TOOL.N115** SETTLED · `SPECIFICATION.md:3054-3057` — "builds two Unix-port variants rather than one
  (owner decision, 2026-09-21)" — Duplicate of B.2's decision. · [H12]

## SPECIFICATION.md Part F.1 — Core platform facts

- **TOOL.N116** PLATFORM · `SPECIFICATION.md:3438-3439` — "MicroPython 1.26 bundles pico-sdk 2.1.1;
  since pico-sdk 2.0.0, a standalone `picotool` must match its major.minor" — The picotool/pico-sdk
  coupling is stated for 1.26 only, not for the pinned 1.29.0 build that the toolchain actually builds
  (low). · related: TOOL.T09 · [H13]

## SPECIFICATION.md Part F.5.6 — Smaller 1.29 facts / non-events

- **TOOL.N117** PLATFORM · `SPECIFICATION.md:3843-3846` — "`MICROPY_C_HEAP_SIZE` is now settable ...
  mpy-cross gained `-X no-source-lines` ... Not worth it at current flash headroom" — Unused knobs; the
  second is a decision resting on current flash headroom. · [H13]

## SPECIFICATION.md Part F.6 — SIGINT during gc_collect() wedges the Unix-port heap

- **TOOL.N118** INVAR · `SPECIFICATION.md:4125-4127` — "there is no other build path — every script that
  needs this binary goes through `toolchain/setup_toolchain.py setup`" — The root-cause closure holds
  only while no binary is built outside this path; the plan notes nothing proves `MICROPY_ASYNC_KBD_INTR == 0`
  in the built binary. · related: TOOL.S07 · [H13]

## SPECIFICATION.md Part L.6.4 — Comment-tag family

- **TOOL.N119** ASSUME · `SPECIFICATION.md:6489-6490` — "Measured saving ... ~3,576 bytes, about 2.6 %
  of `src/`'s frozen bytecode" — Dated measurement. · related: DOC.T08 · [H13]

## CLAUDE.md

- **TOOL.N120** INVAR · `CLAUDE.md:46-49` — "each `verify_*()` there already fails loudly on its own if
  its anchor text drifted" — Override anchors are checked mechanically, but only as literal text. The
  mechanism behind each anchor is re-read by convention only; `unix_kbd_intr` has no post-build proof. ·
  covered-by: TOOL.S07 (related TOOL.T11) · [H14]
- **TOOL.N121** INVAR · `CLAUDE.md:295-301` — "must keep a recovery dead-man's-switch continuously armed
  for the entire risk window" — Convention only. The creation path of setup_toolchain's
  `ensure_bench_bridge()` arms none. The 2026-09-04 incident cost the Pi4's SSH. · covered-by: TOOL.S03
  (related HW.T04) · [H14]
- **TOOL.N122** INVAR · `CLAUDE.md:302-306` — "pin it via `bridge.mac-address`, always, on every bridge
  creation" — Enforced at creation (toolchain/setup_toolchain.py:900). On an existing bridge, drift is
  only flagged (:871-878). dev_legacy/README.md's manual recipe is convention. · covered-by: TOOL.T03 ·
  [H14]
- **TOOL.N123** SETTLED · `CLAUDE.md:566-570` — "Two Unix-port binaries are built, not one (owner
  decision, 2026-09-21)" — `build-standard` has no settrace; `build-settrace` is used only for
  `--coverage`. · covered-by: TOOL.T05 · [H14]
- **TOOL.N124** WORKAROUND · `CLAUDE.md:681-695` — "`apply_unix_kbd_intr_override()` forces the Unix
  port's own safe, deferred SIGINT-delivery path (`MICROPY_ASYNC_KBD_INTR=0`)" — Upstream Unix-port
  SIGINT defect (toolchain/micropython_overrides.py:40-84). Removal trigger: none stated; re-verify on
  every version bump. · related: TOOL.S07, CI.S01 · [H14]
- **TOOL.N125** SETTLED · `CLAUDE.md:693-695` — "Don't re-diagnose a shutdown-only exit-code-1 flake ...
  before confirming this override is still actually being applied" — Only anchor-verified; there is no
  post-build proof, and the CI cache key omits micropython_overrides.py. · covered-by: TOOL.S07 (related
  CI.S01) · [H14]
- **TOOL.N126** INVAR · `CLAUDE.md:864-866` — "What a session owes instead is an entry in BACKLOG.md's
  running list of build-environment changes" — Convention only (BACKLOG.md:514ff). · [H14]
- **TOOL.N127** INVAR · `CLAUDE.md:873-875` — "Two targets, both required: Ubuntu 24.04 \"noble\" (GCC
  13.x ...) and Debian trixie (GCC 14.x ...)" — Convention only. CI's `ubuntu-latest` never builds with
  GCC 14. · related: CI.T10 · [H14]
- **TOOL.N128** WORKAROUND · `CLAUDE.md:900-907` — "ON arm64 (the bench Pi4 itself), the three URLs
  above serve NO packages" — Use ports.ubuntu.com for arm64 noble (verified 2026-09-12). · [H14]
- **TOOL.N129** WORKAROUND · `CLAUDE.md:912-929` — "astral.sh (the official `uv` installer's domain) is
  blocked by this session's egress policy - use `pip install uv`" — Sandbox-only proxy and CA
  workaround. · related: ENV.T01 · [H14]
- **TOOL.N130** WORKAROUND · `CLAUDE.md:934-953` — "sudo is not part of debootstrap --variant=minbase
  ... libcap2-bin is the same class of gap" — Both are installed in the chroot. libcap2-bin is also in
  versions.toml `apt_packages` but kept here for reused chroots. · [H14]
- **TOOL.N131** WORKAROUND · `CLAUDE.md:979-986` — "the mbedtls `mbedtls_xor()` `-Warray-bounds` false
  positive ... worked around by `_MBEDTLS_GCC14_ARRAY_BOUNDS_WORKAROUND`" — Upstream compiler-diagnostic
  defect. Removal trigger: none stated here. · related: CI.T10 · [H14]
- **TOOL.N132** LIMIT · `CLAUDE.md:982-983` — "the build treats any `warning:` as a hard failure" —
  Detects failures by grepping English text; tied to the unpinned distro GCC. · related: TOOL.T10,
  TOOL.T12 · [H14]
- **TOOL.N133** ASSUME · `CLAUDE.md:1009-1013` — "The trixie leg was last satisfied on 2026-09-12 ...
  (v22.23.2), 203 npm packages" — Dated; the noble leg ran the same day. Later changes accumulate in
  BACKLOG's owed list. · [H14]
- **TOOL.N134** INVAR · `CLAUDE.md:1026-1034` — "Changes to `toolchain/setup_toolchain.py` or
  `toolchain/versions.toml` itself need a second, separate verification" — A full `uv run toolchain/setup_toolchain.py`
  in the chroot. Convention only. · [H14]
- **TOOL.N135** INVAR · `CLAUDE.md:1038-1042` — "record it in BACKLOG.md's running list of what the
  owner's next manual chroot run has to cover" — No longer a blocking gate (owner, 2026-09-18).
  Convention only. · [H14]

## README.md

- **TOOL.N136** ASSUME · `README.md:36, 54-56` — "offline re-verify an existing install (~30s), no
  network/apt access needed" — Timing claim; "the CI-friendly ... re-check", yet CI jobs don't run
  `test` (low). · [H14]
- **TOOL.N137** RISK · `README.md:47-48` — "`--micropython-ref REF` — Build a specific MicroPython
  tag/ref instead of ... pinned one" / "`--latest` | ... pin `versions.toml` to it" | Both move the
  built or pinned version without triggering CLAUDE.md's mandatory platform re-check, and
  `--micropython-ref` records nothing. · covered-by: TOOL.S06, TOOL.S09 · [H14]
- **TOOL.N138** LIMIT · `README.md:69-72` — "apt packages, `dialout` group membership, and the `bench`
  NetworkManager bridge/AP all install/configure automatically via `sudo`" — Host-wide side effects of
  `env`. · covered-by: TOOL.T09 · [H14]
- **TOOL.N139** DRIFT · `README.md:104-108` — "self-heals two specific drift cases (a non-pinned AP
  channel, an unpinned/drifted bridge MAC — the latter only flagged, never auto-repaired" — Only one of
  the "two" is self-healed; MAC drift is only reported (toolchain/setup_toolchain.py:871-878) (low). ·
  related: TOOL.T03 · [H14]
- **TOOL.N140** INVAR · `README.md:109-111` — "never run it over a connection that depends on the bridge
  staying up" — The manual `nmcli connection delete` recipe mentions no dead-man's switch, which
  CLAUDE.md:295-301 requires. Convention only. · related: TOOL.S03, HW.T04 · [H14]
- **TOOL.N141** RISK · `README.md:94-95, 100-101` — "a fresh bridge gets a randomly generated
  SSID/password ... `--password correct-horse-battery`" — Bench AP password is passed on the command
  line (argv/log exposure). · related: TOOL.S01, HW.T11 · [H14]
- **TOOL.N142** SETTLED · `README.md:207-211` — "Node comes from nodejs.org (checksum-verified against
  the release SHASUMS), deliberately **not** from apt: Debian trixie ships Node 20" — The checksum comes
  from the same origin, with no signature. · related: TOOL.S02, TOOL.T13 · [H14]

## update_and_install.txt

- **TOOL.N143** PLATFORM · `update_and_install.txt:3-5` — "since pico-sdk 2.0.0, a standalone `picotool`
  build must have a matching major.minor version to whatever pico-sdk it's built against" — The
  installer's picotool tag selection depends on this version coupling. · related: TOOL.T02 · [H14]
- **TOOL.N144** PLATFORM · `update_and_install.txt:5` — "MicroPython 1.26 already bundles pico-sdk 2.1.1
  internally" — A 1.26-specific fact; the pin is now 1.29.0, so it is stale if read as current (low). ·
  related: TOOL.T02 · [H14]
- **TOOL.N145** INVAR · `update_and_install.txt:5-7` — "they must track whatever MicroPython version
  you're building. The script derives both automatically" — Asserts setup_toolchain derives the
  pico-sdk/picotool versions from the MicroPython ref. · related: TOOL.T02, TOOL.T12 · [H14]

## BACKLOG.md

- **TOOL.N146** SETTLED · `BACKLOG.md:514-519` — "an owner-run periodic check, not a blocking per-push
  gate - settled (owner decision, 2026-09-18)" — Chroot legs last satisfied 2026-09-12; the running owed
  list (items [099]-[119] below). · related: plan §1.2 DoD (chroot-owed list) · [H15]
- **TOOL.N147** TODO · `BACKLOG.md:519` — "The legs were last satisfied 2026-09-12. Changed since:" —
  List header. · [H15]
- **TOOL.N148** TODO · `BACKLOG.md:527-533` — "build_unix_port() now builds TWO variants" —
  `build-standard`/`build-settrace`; a reused chroot's old `build-standard` carries the flag — detected
  by `test.sh`'s variant probe. · related: TOOL.T05 · [H15]
- **TOOL.N149** TODO · `BACKLOG.md:537-541` — "the new micropython_overrides.py (PR #90's
  MICROPY_ASYNC_KBD_INTR=0 Unix-port build override" — Named "the part worth the owner's next manual
  run". · related: TOOL.T04, TOOL.S07 · [H15]
- **TOOL.N150** TODO · `BACKLOG.md:542-557` — "lwip_connection_counts (Part B.14.2) generates an
  out-of-tree board directory and passes BOARD_DIR= to make" — Changes the rp2 firmware build:
  post-build `-E` readback, `[lwip]` table read every build, ensemble validation vs 16 `init.c`
  `#error`s, sentinel. Installer leg only. · related: TOOL.T04, TOOL.T11 · [H15]
- **TOOL.N151** TODO · `BACKLOG.md:579-583` — "versions.toml's [lwip] sized for max_connections = 6 (PCB
  9, SEG 48, MEM_SIZE 12000" — Readback via the CMake-recorded compiler with a 120 s timeout;
  `OverrideError` reported like `SetupError`. · related: TOOL.T04 · [H15]
- **TOOL.N152** TODO · `BACKLOG.md:584-589` — "check_lwip_ensemble() restates all sixteen init.c checks,
  adds MEMP_NUM_TCP_PCB >= max_connections + SPARE_TCP_PCBS (3)" — Also public `validate_lwip_macros()`,
  `TCP_MSS` 0 refused; `build_firmware.py` passes `toolchain_dir=` so every device build applies the
  override. · related: GEN.T15 · [H15]
- **TOOL.N153** TODO · `BACKLOG.md:605-608` — "env's uv sync is retried three times with a 10 s / 20 s
  pause (run_retried(), mirroring ci.yml's unit-tests)" — MIRROR `toolchain/setup_toolchain.py:124` ↔
  ci.yml retry. · related: CI.T12 · [H15]
- **TOOL.N154** ASSUME · `BACKLOG.md:609-612` — "Partial evidence, not a leg: a session sandbox (GCC
  13.3, not a --variant=minbase chroot)" — 2026-09-24 installer run, "all eight verification checks
  passed". · [H15]
- **TOOL.N155** DRIFT · `BACKLOG.md:519-612 vs `git log --since=2026-09-13` — (list omits files) — Build-env files changed since the legs but not itemised: `scripts/_generate_sensortask_modules.py` (2026-09-16/19), `scripts/cross_browser_smoke.mjs` (2026-09-18/19/24), `scripts/_render_coverage.py` (2026-09-19), `scripts/build_website.sh` and `run_{flash,bench,manual}_hardware*.sh`/`run_bench_soak_tests.sh` (2026-09-18, 2026-09-22 comment sweep `35ba8ac`), `.github/zizmor.yml` and the composite `action.yml` (2026-09-21/24). Many are comment-only; not investigated. (low) · [H15] ⟨quote not matched at the anchor⟩

## HEAP_FRAGMENTATION_MEASUREMENTS.md (current, 393 lines; owning area HW)

- **TOOL.N156** WORKAROUND · `HEAP_FRAGMENTATION_MEASUREMENTS.md:285-289` — "1.29's Makefile silently
  ignores MICROPY_FORCE_32BIT and builds 64-bit" — 32-bit twin needs `CC="gcc -m32"` etc.,
  `gcc-multilib`, `-Wno-array-bounds`; removal trigger: none stated. · [H15]

## Commit messages (chronological)

- **TOOL.N157** TODO · `commit 239be54` — "pico-sdk 2.0.0+ requires a matching-version picotool build
  ... Also notes missing toolchain package list and an official one-shot setup script alternative" —
  update_and_install.txt gaps. · tracked: BACKLOG "Dev/build environment setup" | - · [H17]
- **TOOL.N158** WORKAROUND · `commit 5a6deea` — "debootstrap's default sources.list only enables the
  `main` component, and gcc-arm-none-eabi ... lives in `universe`" — Chroot recipe must enable universe.
  · tracked: CLAUDE.md chroot recipe | - · [H17]
- **TOOL.N159** RISK · `commit f33f1e6` — "build_firmware() and build_mpy_cross() detect failure by
  grepping build output for the literal English \"error:\"/\"warning:\"" — Build-failure detection is
  text-grep based; locale forced to C.UTF-8 to keep it valid. · status: done-in f33f1e6 (locale pinned);
  grep-based detection remains by design | related: TOOL.T* · [H17]
- **TOOL.N160** DRIFT · `commit e176775` — "softened the \"verified from scratch on a clean chroot\"
  claim, since that specific from-scratch run predates the 8-step chain" — Clean-chroot verification
  claim was known stale vs the 8-step chain at that time. · status: later chroot legs 2026-09-12
  (CLAUDE.md) | - · [H17]
- **TOOL.N161** ASSUME · `commit 06ae5d8` — "MICROPY_PY_SYS_SETTRACE just adds an inert hook check in
  the bytecode dispatch loop ... not a behavior change" — Assumption later disproved (4-5x allocation
  inflation) and reversed by the 2026-09-21 two-binary split. · status: done-in (two-binary split,
  CLAUDE.md / SPECIFICATION Part E.5.2) | - · [H17]
- **TOOL.N162** WORKAROUND · `commit 51ebe44` — "Suppressed via -Wno-array-bounds appended to
  CFLAGS_EXTRA in both build functions ... explicit instructions to recheck GCC bug #121044 and the
  vendored mbedtls version before ever removing" — GCC>=14 mbedtls false positive; removal trigger
  stated. · tracked: SPECIFICATION Part B.7.1, CLAUDE.md trixie target | related: TOOL.T* · [H17]
- **TOOL.N163** WORKAROUND · `commit 21106f2` — "pins 802-11-wireless.channel to 6 ... unlike 12-13
  which are EU/DE-only ... Pico W's cyw43439 didn't associate with reliably" — Bench AP channel pin;
  chroot recipe cannot exercise NetworkManager bridging. · tracked: SPECIFICATION Part B.12/B.13 (per
  2296e3e) | related: HW.T* · [H17]
- **TOOL.N164** WORKAROUND · `commit 68b5bc3` — "`nmcli -g` escapes every ':' ... The comparison was
  unconditionally true: the MAC-drift check ... has therefore never verified anything" — Fake did not
  model nmcli escaping; fixed with `--escape no`. · status: done-in 68b5bc3 | - · [H17]
- **TOOL.N165** NOTE(VERIFY-GAP) · `commit 8e70914 / f8d511a` — "the trixie leg could not run in this
  session's own sandbox because deb.debian.org is blocked ... flagged ... rather than skipped silently"
  — Chroot leg skipped for max-args ratchet 21->22. · status: superseded — both legs satisfied
  2026-09-12 (c82149f) and chroot made owner-run (CLAUDE.md, 2026-09-18) | - · [H17]
- **TOOL.N166** NOTE(FUTURE) · `commit 8466f2b` — "two researched-but-not-yet-implemented future entries
  (lwIP connection counts, littlefs/flash storage size)" — Future MicroPython build overrides. ·
  tracked: SPEC Part B.14 | related: PLAT.T* · [H17]
- **TOOL.N167** NOTE(VALIDATION-GAP) · `commit cbe07a6` — "validated best-effort in this sandbox rather
  than CLAUDE.md's full dual-OS clean-chroot recipe (no root/debootstrap access here) - that gap is
  called out explicitly in the PR" — Chroot legs skipped. · status: superseded by owner decision
  2026-09-18 (chroot is owner-run; BACKLOG running list) | - · [H17]
- **TOOL.N168** NOTE(UNCALIBRATED) · `commit 4d4a881` — "the Pi4's own reported parallelism-probe line,
  since those thresholds were calibrated from an x86 sandbox and a simulated slow host but never from
  the real Pi4" — Probe thresholds unvalidated on real bench host. · status: unknown — no later record
  found in this pass whether the Pi4 line was reported (not re-verified) | - · [H17]
- **TOOL.N169** NOTE(INSTRUMENT-DEFECT) · `commit 1e2f5b2` — "MICROPY_PY_SYS_SETTRACE=1 is not inert ...
  Whether to build a flag-free binary for the plain test run is put to the owner (doc §11 item 0)" —
  Unix port allocations inflated 4-5x. · status: done (two binaries, owner decision 2026-09-21;
  CLAUDE.md, SPEC E.5.2) | - · [H17]
- **TOOL.N170** NOTE(VERIFY-GAP) · `commit 7603cb9` — "The two-target clean-chroot pre-push gate is
  unsatisfied for every build-environment change on this branch after 2026-09-12" — Chroot legs
  outstanding. · tracked: BACKLOG running list of build-environment changes (owner-run check) | - ·
  [H17]
- **TOOL.N171** NOTE(OWNER) · `commit fb26903 / 1bbce05` — "§11 item 0, taken by the owner: the plain
  suite no longer measures under a profiler"; "The (f) stage ... had NO runner at all ...
  unit-tests-gc-threshold CI job makes it routine"; "Also withdrawn: 7H.3 concluded 'the threshold is
  not defence in depth'. That overreached" — Two Unix-port binaries; (f)-stage runner. · tracked:
  CLAUDE.md, SPEC E.5.2/I.4 | - · [H17]
- **TOOL.N172** NOTE(PROCESS-LESSON) · `commit c2050da (also 4f39c0b)` — "Lint was red from 55e5f6f9:
  the gate checks before those commits read lint.sh through tail, which hid ruff's output and exit
  status" — Second recurrence of reading lint.sh's tail instead of its exit code. · UNTRACKED (low;
  lesson in commit messages only, not in CLAUDE.md/README) | - · [H17]
