# tests_hardware/ - real-hardware test tier

Implements SPECIFICATION.md Part E.6's flash/bench/manual backends: automated tests driven from the
host over `mpremote`/`nmcli`/`iptables` (never the MicroPython Unix port `tests/` uses - see
SPECIFICATION.md Part E.1), plus a structurally separate manual runner for tests that need a human's
hands. Real-hardware runs happen on the bench Pi4 against the board whose device TOML sets `[device]
bench = true` (today `dev`); this file is the durable reference for prerequisites, environment variables, how to run it, and the facts/assumptions
worth knowing before trusting a run's results.

**Any session about to run real-hardware tests against this tier needs the project owner's
go-ahead first, given directly in that session's own conversation** - see CLAUDE.md's own hard rule
on this. Once granted, this file has everything else needed: prerequisites below, environment
variables, the critical safety facts folded into "Known assumptions and open findings" (the
`--allow-flash-cycle`/`--soak-duration` opt-in gates in "Running" below, the role reversal's stage-6
fallback in "The hotspot role reversal", `BENCH_AP_PASSWORD` handling in "Environment variables" below).

## Prerequisites

1. `uv run toolchain/setup_toolchain.py env --tier flash` (real USB board attached) or `--tier
   bench` (also needs a WiFi adapter for the bridge) - see README.md's own environment-tiers table.
   Each tier checks the commands it runs and, unless `--skip-apt`, installs the missing ones'
   packages; the table of commands and packages is `_TIER_COMMANDS` in
   `toolchain/setup_toolchain.py`. Flash adds the `dialout` group and resolves the board (USB vendor
   `2e8a` plus its MicroPython `/dev/serial/by-id` name, SPECIFICATION.md Part B.12); bench creates
   the `br0-wifi-ap` bridge through `ensure_bench_bridge()` ("Host network" below). After `npm ci`
   every tier installs Playwright's Chromium, and a failed install stops `env` by name; a failed
   `install-deps` stops it too unless `--skip-apt` skips that step (pass it where the libraries are
   present).
2. **Passwordless sudo for every command the bench tier runs unattended.** `env --tier bench`
   writes no sudoers file: it probes each command with `sudo -k -n <path> <version argument>` and
   names every one refused, including one whose rule allows only other arguments (the probe fails
   there though the real call would run). A sample `/etc/sudoers.d/` line, each `<command>` the
   absolute path `which <command>` prints on the bench host:

   ```
   <user> ALL=(root) NOPASSWD: <nmcli>, <iw>, <iptables>, <tc>, <tee>, <picotool>, <timeout>, <systemd-run>, <systemctl>
   ```

   Why each: `nmcli` for the bridge and its AP, `iw` for the AP's station kick, `iptables` and `tc`
   for fault injection, `tee` for the USB unbind/rebind, `picotool` for flashing, `timeout` for the
   `tcpdump` capture it wraps, and `systemd-run`/`systemctl` for the bridge's recovery timer. Root
   passes the probe as it is. Unrestricted, `tee`, `timeout` and `systemd-run` each run or write
   anything as root, so this line grants as much as `NOPASSWD: ALL`. A refused USB rebind fails the
   run as `HardwareNotAvailableError` naming sudo, never as the stale `mpremote` error it was
   recovering from. The off-subnet spoof test also runs `sudo -n <python> tests_hardware/spoof_udp.py`
   with the venv's interpreter (a raw socket needs root); its rule is added by hand, and
   `env --tier bench` probes it too (`sudo -k -n <python> tests_hardware/spoof_udp.py --help`, which
   only prints usage), failing with the command it needs.
3. The board named by `[device] bench = true` (`harness.bench_device()`, "Environment variables"
   below) runs its own image (SPECIFICATION.md Part E.6.3's "one allowed flash" -
   `uv run scripts/build_firmware.py <bench device>` + `picotool load -x -v`, or the manual
   BOOTSEL-button first flash for a genuinely blank board, see
   `tests_hardware/manual/manual_toolchain.py`). No other build's image is flashed: another device's
   pins do not match the bench wiring (CLAUDE.md's `dev` rule).
4. **The board's standard state**: `DebugLevel` 5, the FRAM write-protect clear and no
   `config_HWTEST_*` file or `hwtest-scratch/` directory. The session fixtures check it at the start
   and the end and stop the run naming each deviation; `--repair-standard-state` repairs one instead,
   each repair a listed prerequisite write, read back after it ("Persistence-write gating").
5. **RP2040-E15 and the bench Pi 4's VL805.** A Raspberry Pi 4's downstream USB ports (VL805 xHCI)
   can hang the RP2040's USB device controller on Bulk IN transfers over 50 bytes (RP2040 datasheet,
   erratum RP2040-E15). The firmware at the pin carries TinyUSB's workaround (pico-sdk's TinyUSB
   target sets `PICO_RP2040_USB_DEVICE_UFRAME_FIX`); the host-side fix is VL805 firmware 0138c1 or
   later (`sudo rpi-eeprom-update -a`). The bench session reads the version with the read-only
   `rpi-eeprom-update` (no sudo) into the run record and warns on the console below it. The
   workaround's presence is re-checked at each pin move (the
   `PICO_RP2040_USB_DEVICE_UFRAME_FIX=1` define in the rp2 build flags).
6. **`picotool` needs real USB support to actually flash anything.** `env --tier flash` and
   `--tier bench` refuse a `picotool` built without it (its `picotool version` output then says
   "compiled without USB support"; install `libusb-1.0-0-dev`, in `toolchain/versions.toml`'s
   `apt_packages`, and re-run setup), while `setup` and `--tier generic`, which flash nothing, only
   warn. picotool is rebuilt only when its tag changed or the installed binary no longer reports it,
   and a different `picotool` earlier on the installer's `PATH` is reported with both paths. A
   `picotool` reporting "Requires version X, you have version Y" is a stale system-wide install
   shadowing the toolchain's own build: rerun `uv run toolchain/setup_toolchain.py setup` rather
   than working around it.
7. **The NeoPixel sweep rig**, only for `--allow-neopixel-sweep`: physical, so no
   `setup_toolchain.py` tier provisions it ("The NeoPixel sweep rig" below).
8. **The bench host's `uv` is the version `pyproject.toml`'s `[tool.uv] required-version` names.**
   Any other uv refuses to run in this tree with its own message. Before it touches the board, every
   runner runs the one retried sync, `scripts/uv_sync_retried.sh` (`uv sync --locked`, three
   attempts; the flash and bench runners after their lower levels); a sync that still fails ends the
   run with "error: the retried uv sync failed - its output above names the cause; nothing reached
   the board" (exit 1).

## The dev bench

The one board a session flashes and tests (CLAUDE.md): its wiring and chips, its dated state, the
bench host's network, what each tool writes to it, and how to test a driver on it by hand. Every bus
pin, bus parameter, UART pair and peripheral GPIO is `devices/dev.toml`'s; this section holds only
what that file cannot.

### Wiring and chips

Wiring verified on the board by the owner, as recorded by the agent (2026-08-28, `7f6bdaa`,
paraphrase), unless a line says otherwise:

- **FRAM** is an **MB85RS2MTA**, 256 KB (`max_size` in `devices/dev.toml`); its CS, GP5, is
  physical pin 7.
- **BMP3xx** is physically a **BMP384**, at 0x77.
- **NeoPixel**: GP18 is physical pin 24.
- **ISL29125 INT** is GP6, physical pin 9, and pulled up on this board, which is why
  `devices/dev.toml` sets `irq_pull_up = false` (owner, 2026-09-12, `7be762f`, paraphrase). The
  breakout itself carries R4 = 10 kΩ from `!INT` to 3V3, per SparkFun's schematic (agent,
  2026-09-12, `7890e2b`).
- **UART crossover jumper**, permanent and bench-only: GP0 (pin 1) ↔ GP9 (pin 12) and GP1 (pin 2)
  ↔ GP8 (pin 11), a TX↔RX crossover between the board's own UART0 and UART1, so two `UARTComm`
  instances talk to each other on one board (confirmed by the owner on the board, as recorded by the
  agent, 2026-08-28, `7f6bdaa`). The UART pairs themselves are `devices/dev.toml`'s `[bus.uart0]`
  and `[bus.uart1]`.
- **Attached, not driven by the `dev` firmware**: an MPRLS on I2C0 with its reset on GP10; its EOC
  pin is open - GP7 in `legacy/dev_drivers/sensortask-dev.py`, GP9 in
  `legacy/firmware/modules/sensortask-dev.py` - until a bench check reads it. A BME688 (BSEC) on
  UART0, GP16/GP17 at 115200 baud, was recorded on 2026-08-28; whether it is still attached is open
  until the same check. No SHTC3 is fitted, though some legacy code wires one.

Silicon observations on this bench (agent, 2026-08-28):

- After `stop_continuous_measurement()` the SCD30 completes one more reading about 1 s later before
  it goes idle; a test polling data-ready right after the stop sees that reading.
- The SGP40's VOC index reads 0 through cycle 46 and real values from cycle 47, the VOC algorithm's
  initial blackout.
- A full-range MB85RS2MTA write/read-back across every power-of-two address boundary passed
  (SPECIFICATION.md Part C.3.1).

### Bench state (dated)

What was last read from the board and its host, each line with its date; none of it is current until
re-read.

- SCD30 NVM: temperature offset 1.5 °C, altitude and ambient-pressure compensation 0 (recorded
  2026-08-28). The NVM survives a power cycle and a reflash.
- Bench host: `br0`, `br0-eth0` and `br0-wifi-ap` live, `dialout` membership restored, hostname
  `raspberrypi` (recorded 2026-09-04).
- The router's DHCP reservation was keyed to a MAC the bridge no longer presents (recorded
  2026-09-04); the owner confirms the re-keying at the first round.

**Never `cp` a script meant to run onto the board's filesystem; mount it.** Upstream's frozen
`_boot.py` mounts the filesystem and returns, then `ports/rp2/main.c` runs `boot.py` and
`main.py`, each the frozen module when one exists and otherwise the filesystem file
(`shared/runtime/pyexec.c`'s `pyexec_file_if_exists()`, v1.29.0). The `dev` image freezes its
entry as `main.py`, so a filesystem `boot.py` runs before it at every boot, and a filesystem
`main.py` runs under any image without a frozen one, with nothing showing why. One `exec` of
`os.listdir('/')` confirms the filesystem holds neither - a one-shot check, never a poll ("Known
assumptions and open findings" says why).

### Bench facts

What the bench itself answers, where the documents disagree or a test needs the value; a filled row
names its source and its date (`tests_scripts/test_device_script_bench_facts.py`), an open one how it
is read.

| fact | value | source | date |
|---|---|---|---|
| each I2C bus's answering addresses (`i2c0`'s MPRLS among them) | to be read: the `addresses` fact of `bus_topology_autodetect_and_hazard_sweep.py`, which `flash/test_bus_concurrency.py`'s sweep test notes | | |
| FRAM part | to be read: the `rdid` fact of `fram_raw_dump.py`, saved by every session's start | | |
| SCD30 NVM state (temperature offset, altitude, ambient pressure, ASC) | to be read: the standard-state fixture's SCD30 snapshot at a session start | | |
| NeoPixel rig geometry (distance, ambient) | to be read: the manual `isl29125_real_lux_vs_reference_meter_and_neopixel_rig_geometry` | | |
| the router's DHCP reservation keyed to the uplink's MAC | to be read: the owner's answer | | |
| the BME688 on UART0 (GP16/GP17) still attached | to be read: the owner's answer | | |
| bench host OS and stale packages | to be read: the bench host's `/etc/os-release` and `apt list --upgradable` | | |
| WiFi radios on the bench host | to be read: `iw dev` on the bench host; the harness assumes one, shared by the AP and every scan | | |
| the standard board state | to be read: the standard-state fixture at a session start (`DebugLevel` 5, FRAM write-protect clear, no scratch files) | | |

### Host network: the `br0` bridge and its AP

The board reaches a real network through the bench host, a Raspberry Pi 4: NetworkManager bridges
the host's uplink with a WiFi AP the host serves, so the board joins the LAN and internet path the
host has and `asy_wifi_service.py`'s own connect state machine runs against a real AP. The bridge is
persistent host state: it survives a host reboot, and `nmcli connection show` lists it.
`uv run toolchain/setup_toolchain.py env --tier bench` builds it through `ensure_bench_bridge()`;
the manual recipe below is the same sequence, for a host where interface detection is ambiguous or a
bridge has to be rebuilt by hand.

**Arm the dead-man's switch first.** Every step below that can cut the host's connection - creating
or modifying the bridge, enslaving the uplink, cycling the AP, deleting the bridge, and the MAC
remedy `env --tier bench` prints - runs with SPECIFICATION.md Part B.13's recovery switch armed:
its recovery script recreated fresh in the session scratchpad and never committed, armed per step
or once around a sequence whose timing was measured, the outcome polled, then disarmed, following
B.13's arm/verify/disarm steps rather than a copy of them here (CLAUDE.md's hard rule).
`env --tier bench` arms its own recovery timer around every bridge change it makes - the creation
and the channel re-pin: a `systemd-run` timer whose script tears the bridge down (and, around a
creation, brings back the uplink's own profile, read at run time); verified active before the first
change, stopped only once `br0` holds an address and the default route, and left armed when the
change fails, the log naming when it fires.

```sh
sudo modprobe br_netfilter
sudo sysctl -w net.bridge.bridge-nf-call-iptables=1
echo br_netfilter | sudo tee /etc/modules-load.d/sensors-bench-br-netfilter.conf
echo net.bridge.bridge-nf-call-iptables=1 | sudo tee /etc/sysctl.d/99-sensors-bench-br-netfilter.conf

sudo nmcli connection add type bridge ifname br0 con-name br0
sudo nmcli connection modify br0 bridge.mac-address <eth0's real MAC, from `ip link show eth0`>
sudo nmcli connection add type ethernet ifname eth0 master br0 con-name br0-eth0 slave-type bridge
sudo nmcli connection add type wifi ifname wlan0 con-name br0-wifi-ap ssid <ssid> \
    802-11-wireless.mode ap 802-11-wireless.band bg 802-11-wireless.channel 6 \
    master br0 slave-type bridge
sudo nmcli connection modify br0-wifi-ap wifi-sec.key-mgmt wpa-psk wifi-sec.psk <password> \
    wifi-sec.proto rsn wifi-sec.pairwise ccmp wifi-sec.group ccmp wifi-sec.pmf disable
sudo nmcli connection up br0-eth0; sudo nmcli connection up br0-wifi-ap
```

`eth0` and `wlan0` stand for the uplink and the WiFi adapter (`--uplink-iface`/`--wifi-iface` name
others); the three connection names are the ones `ensure_bench_bridge()` looks for. Why each setting
is there:

- `bridge.mac-address` is pinned to the uplink's real hardware MAC before the bridge first comes up:
  a synthesized bridge MAC can drift and orphan the router's DHCP reservation (agent, 2026-09-04,
  `28c5d8e`; SPECIFICATION.md Part B.13).
- The AP runs at 2.4 GHz (`band bg`) on channel 6: left on auto, NetworkManager picked channel 13,
  which the board's CYW43439 did not associate with reliably (`ensure_bench_bridge()`'s own note).
- WPA2-PSK with AES only: `proto rsn`, `pairwise ccmp`, `group ccmp`, and `pmf disable`. Against a
  PMF-enabled or mixed configuration the CYW43439's handshake fails with no error anywhere - `iw
  event` shows `new station` and then `del station` (observed on this bench, 2026-08-28).
  `bridge.stp` stays at its default.
- `br_netfilter` with `bridge-nf-call-iptables=1` makes iptables see bridged traffic; without it
  `bench_control.py`'s fault injection is a silent no-op (SPECIFICATION.md Part B.13).

Credentials: a new bridge gets random ones (`generate_bench_ap_credentials()`) unless `--ssid` and
`$BENCH_AP_PASSWORD` name them, an existing one keeps its own, and real ones are never committed
(CLAUDE.md). The AP's PSK is a throwaway password used once, passed plainly to the one
`nmcli connection modify` on its command line, as in the recipe above (owner, 2026-10-02); the
installer keeps it out of the command it echoes and shows a generated one once. An existing bridge
is reported, not recreated; its MAC is compared with the uplink's, and a mismatch is only reported
with the manual remedy, never repaired live. The comparison reads `nmcli --escape no`, since plain
`nmcli -g` escapes every `:` in a MAC; SPECIFICATION.md Part B.13 says why a live repair is out.

Bench control (`tests_hardware/bench_control.py`) leaves the host as it found it: every injected
fault - an iptables DROP or DNAT rule carrying `FAULT_COMMENT`, a `tc netem` qdisc - is undone and
then proven absent by listing its chain or qdisc, so a restore that left one in place raises naming
it; and the `bench` fixture starts a run by clearing a killed run's leftovers (`clear_leftovers()`:
those rules, a netem qdisc on the AP radio, the role-reversal client profile, an AP left down), each
removal a session note in the run record. The adapter has one radio: an SSID scan runs only while
the AP is down, and `is_ssid_visible()` raises when it is called with the AP up.

To force a new bridge (new credentials, another adapter), delete the bridge and both its slave
connections with the switch armed, then rerun `env --tier bench` or the recipe above. The host's
connection through the bridge drops until the uplink is back, which is what the switch covers:

```sh
sudo nmcli connection delete br0-wifi-ap br0-eth0 br0
```

### What each tool writes to the board

| Operation | Flash write | What it does to the running firmware |
|---|---|---|
| `mpremote` `exec`, `run`, `mount`, `ls`, `cat` | none | enters the raw REPL with Ctrl-C, which stops the running `main.py` (`tools/mpremote/mpremote/transport_serial.py`'s `enter_raw_repl()`, v1.29.0); the soft reset that follows keeps the armed watchdog, the GC threshold, `ticks_ms()` and the pin muxing and never re-runs `main.py`, so every raw-REPL session ends in a hard reset (SPECIFICATION.md Part F.1) |
| `mpremote` `reset` | none | an `exec` of `machine.reset()` (the shortcut table in `tools/mpremote/mpremote/main.py`, v1.29.0): the firmware restarts |
| `mpremote` `cp`, `rm`, `mkdir`, `rmdir` | the flash filesystem | stops `main.py` like the row above, then writes |
| a script under `mpremote run` that persists config | the flash filesystem | `_set_dict_cfg()` → `ConfigManager.write_config()` → `flush_pending()` writes the config file like any test's write, counted against `persistence_write` |
| a device script that builds the system (`build_system()` or `main()`: the full-build, heap, serving and command scripts) | the flash filesystem, in a scratch directory | one defaults write per config store into `hwtest-scratch/`, which the script creates and removes on every path, a leftover removed first: an absent file's first write, a prerequisite, never a production file |
| `picotool load` | a flash cycle | replaces the image; only as a `flash_cycle`-gated test (`--allow-flash-cycle`) or as a round's planned prerequisite write |

### Testing a driver by hand over mpremote

One driver, or a partial closure, at a time, against the `dev` image already on the board
(Prerequisites item 3):

- **Mount, never copy.** `scripts/mpremote_connect.sh mount <dir> run <script>.py` makes `<dir>`
  importable with no flash write. A mounted module shadows the frozen one of the same name, since
  `sys.path` lists the current directory before `.frozen` (`py/runtime.c`, v1.29.0).
- **Heavy closures need `.mpy`.** Importing over a mount compiles from source on the board, so a
  heavy closure (`asy_fram_manager.py`, `asy_scd30_driver.py`, `asy_sgp40_driver.py` with
  `voc_algorithm.py`) can raise `MemoryError` mid-import even with about 200 KB free. Precompile it
  with the pinned `mpy-cross` (`$PICO_TOOLCHAIN_DIR/micropython/mpy-cross/build/mpy-cross`) into a
  scratch directory and mount that; its `mpy` version must match the board's `sys.implementation`.
- **Inline `const()` values.** A `micropython.const()` name is compiled away at its definition site
  and cannot be imported from another module (SPECIFICATION.md Part E.5.1); write the literal.
- **Prime a reader's config in RAM.** `cfgmgr.setup()` reads the config file and can write it back
  (creating or repairing it). Set the cache from the schema instead, as
  `tests_hardware/device_scripts/bmp3xx_plausibility_read.py` does: `reader.cfgmgr.valid = True;
  reader.cfgmgr._cache = {f[0]: f[2] for f in reader.get_cfg_schema() if f[2] is not None}`. A later
  `_set_dict_cfg()` still writes unless its persist is diverted (the scratch-path habit in "Writing a new device script").
- **Exercise persisted settings through the protocol-layer driver** (the `*_I2C`/`*_SPI` class,
  SPECIFICATION.md Part C.3), not the `*_Reader`, whose `cfgmgr` writes the config file.
- **A simulated restart takes a fresh `FRAMManager`.** It is a bump allocator (SPECIFICATION.md
  Part A.4): a fresh manager per restart lands each chunk back at the same base address, while a
  second reader on one manager gets a second, non-overlapping chunk. Ask for it under the same
  `owner=` name: the name seeds the chunk's CRC, so another name reads the same bytes as blank.

## Environment variables

- `MPREMOTE_DEVICE` (or `--device` on any `pytest tests_hardware` invocation) - serial device path
  for the flash-tier board. With neither set, `harness.resolve_board_device()` identifies the board
  by USB vendor ID through `toolchain/setup_toolchain.py`'s `detect_pico_serial_devices()` and
  returns its `/dev/serial/by-id/...` symlink, which is named by USB serial number and so survives
  the re-enumeration a hard reset causes. Two boards attached is a hard error naming both rather
  than a silent pick; none attached returns a path that cannot exist, so the `board` fixture skips
  without mpremote opening some other device's port to find that out. Either variable pins the path
  outright, and a pinned path is never re-resolved. The installer's own resolver
  (`setup_toolchain.py board`, `env --tier flash|bench`) also requires the MicroPython by-id name
  (SPECIFICATION.md Part B.12), so a debug probe sharing vendor `2e8a` is a candidate here but not
  there. `scripts/mpremote_connect.sh` resolves its board through `setup_toolchain.py board`,
  `MPREMOTE_DEVICE` overriding it; the resolver's own error line ends its run before any `mpremote`
  call.
- `BENCH_DEVICE` (or `--bench-device NAME`) - the board on the bench. The default is the one
  `devices/*.toml` whose `[device]` sets `bench = true`; none or several flagged is an error naming
  the files, and a name with no TOML of that name in `devices/` is a usage error. The option is exported as the
  variable for the session, so every harness helper that takes a device by default reads it.
- `--dut-ip ADDR` - the DUT's last known address on the bench network: the session then saves
  `GET /status` (the FRAM-backed `errcount` and the in-RAM reset reason) before anything resets the
  board. Without it the session notes that nothing was saved over REST and starts from the raw FRAM
  dump alone.
- `--image-record PATH` - the image record of the build on the board (default
  `build/firmware-<bench device>.json`, beside its `.uf2`); "Verify the image" below.
- `BENCH_AP_PASSWORD` - optional. `tests_hardware/bench/test_hotspot_role_reversal.py`'s stage-6
  real credential handoff and its wrong-password case (which derives its well-formed wrong password
  from it) default to `bench.ap_password()`, the bench bridge AP's own PSK read live
  from `nmcli --show-secrets` under the tier's sudo access; set the variable only to override it
  (an AP whose secrets `nmcli` cannot read back), and it takes priority over the lookup.
  `env --tier bench` reads the same variable when it creates a bridge. The handoff does not skip on
  its own: a bench bridge built by `ensure_bench_bridge()` always has a readable password.

## Running

```bash
# Automated, flash tier (L3; real USB board, no network) - runs L0-L2 first:
scripts/run_flash_hardware_suite.sh

# Automated, bench tier (L4; real USB board + real WiFi bridge) - runs L0-L2, then L3 as its own
# clean step, then tests_hardware/bench/:
scripts/run_bench_hardware_suite.sh

# Soak durations (soak_duration marker) are never bundled into either suite runner: each is its own
# invocation on top of a clean bench run, liveness only (tests_hardware/soak_durations.py's
# SOAK_DURATION_SECONDS; SPECIFICATION.md Part N l4.soak_duration_short_s / _mid_s / _long_h); a
# missing or unknown duration exits 2 naming the valid ones, before anything runs:
scripts/run_bench_soak_tests.sh --duration short   # 60 s
scripts/run_bench_soak_tests.sh --duration mid     # 600 s
scripts/run_bench_soak_tests.sh --duration long    # 6 h

# The tick rollover, on top of a clean bench run: the runner builds the bench device's tick-offset
# test image (build_firmware.py --tick-offset-test; its record beside it names tick_offset_test), then
# bench/test_ticks_ms_rollover.py reflashes it (one flash cycle) and polls it about two hours over
# REST - start it detached. It never flashes back: the next round flashes its own image.
scripts/run_bench_rollover_test.sh

# --allow-flash-cycle runs the tests that reflash the board (flash wear; "Persistence-write gating"
# lists them, SPECIFICATION.md Part E.6.3):
scripts/run_flash_hardware_suite.sh --allow-flash-cycle

# Limited-endurance writes a test owns are off by default; --allow-persistence-write runs them, and
# --allow-scd30-extra-write on top of it (AND-gated, never alone) the further SCD30 NVM writes
# ("Persistence-write gating" holds the budget table):
scripts/run_flash_hardware_suite.sh --allow-persistence-write
scripts/run_flash_hardware_suite.sh --allow-persistence-write --allow-scd30-extra-write

# The two long ISL29125 light programs need the physical rig ("The NeoPixel sweep rig") and ~10
# minutes; the envelope's config pushes also need --allow-persistence-write:
scripts/run_flash_hardware_suite.sh --allow-neopixel-sweep --allow-persistence-write

# The full toolchain re-verification (network fetches, ~8 min of builds, no board write):
scripts/run_flash_hardware_suite.sh --allow-toolchain-reverify

# Manual tests (interactive, prints instructions, waits for confirmation):
scripts/run_manual_hardware_tests.sh --list          # see what's registered, run nothing
scripts/run_manual_hardware_tests.sh --only <name>   # run just one
scripts/run_manual_hardware_tests.sh                 # run all of them, in sequence
```

Both automated runners first run L0-L2 (`scripts/_run_lower_levels.sh`: `scripts/test.sh` at both
GC stages, `npm test`, and `scripts/run_digital_twin_ci.sh` for every device), stopping at the first
failure before the board is touched; `--skip-lower-levels` is for debugging only and is never
reported clean (`NOT CLEAN`, exit 4). The soak and rollover runners run no lower level: each sits on
top of a clean bench run. Otherwise they are pytest wrappers - any pytest flag works (`-k <substring>`,
`-m role_reversal`, `-v`, `--tb=short`, ...). A runner syncs the environment once before its
hardware step, through the retried `scripts/uv_sync_retried.sh` (Prerequisites); nothing inside the
hardware run syncs again: every `uv run` of the runners and the harness is `uv run --no-sync`, so a
third-party outage never reads as a hardware failure. `--collect-only` works
with nothing attached at all (every fixture skips cleanly, never errors, when the hardware it needs
isn't reachable), under every option (`tests_scripts/test_tests_hardware_collect_matrix.py`).
`--twin` runs the flash tier and its device scripts against the Unix-port twin instead of a board
(`tests_hardware/twin_board.py`, `digital_twin/README.md`'s "Running device scripts in the twin").

**Why the runners judge a run from its run record rather than trusting pytest's exit code.** That
clean-skip design is what makes a run against genuinely *unreachable* hardware look identical at the
exit-code level to a real clean run: pytest exits 0 for an all-skipped run exactly as it does for an
all-passed one. These runners exist to run against real, attached hardware, so that ambiguity must
not pass silently. `scripts/_require_clean_hardware_run.sh` therefore runs pytest with the
run-record plugin (SPECIFICATION.md E.10) and hands the record to `scripts/_hardware_verdict.py`;
the verdict reads the run record: a skip passes only as its gate's own skip with the flag absent
(`--allow-flash-cycle`, `--soak-duration`, `--allow-multi-day-rollover`, `--allow-neopixel-sweep`,
`--allow-toolchain-reverify`); a deselection is reported with its flag and counted; a `-m`
exclusion is reported as runner selection; a recovery pass is counted apart. Zero passed tests fail
the run, a nonzero pytest exit is passed on unchanged, and a `--collect-only` run reads
`NOT A RUN (collection only)`. The pytest log and the record land in
`build/archive/<runner>/<UTC>/` (the runner's name lowercased, every other character `_`), each
runner's newest three kept; the bench runner's flash step archives as
`run_bench_hardware_suite_flash_step`. A bench runner's test paths go to its bench step only. A
run's evidence files (the saved `/status` bodies and raw FRAM dumps, `tests_hardware/evidence.py`)
land in the same directory, which the runner exports as `EVIDENCE_DIR`.

A test reports what it measured through the `result_note` fixture (`recovery=True` for a pass that
needed a recovery) and a session-scoped fixture through `record_session_note()`
(`tests_hardware/conftest.py`): both reach the run record and the summary block, which pytest's
captured output of a passing test never would.

Each runner passes its own `--marker-floor` to `scripts/_require_clean_hardware_run.sh`: the flash
and bench runners `not soak_duration and not multi_day_rollover`, so those tests are deselected as
runner selection rather than reaching the verdict as skips, the soak runner `soak_duration` and the
rollover runner `multi_day_rollover`. A `-m` you pass narrows the selection, never replaces it:
pytest gets exactly one `-m "(FLOOR) and (EXPR)"` for your last `-m EXPR`, printed as
`== Marker selection: -m "<expr>"` before the run and into the archived pytest log. Under the soak
runner `--soak-duration` *is* set, making those tests "must pass" rather than "may skip".

**The SCD30 prerequisite.** Every SCD30-reading flash test takes the session fixture
`scd30_measuring` (`tests_hardware/scd30_prerequisite.py`): it reads the measurement interval, waits
up to three intervals for a measurement and sends the start command only when none arrives - so a
default run normally writes the SCD30's NVM zero times and at most once (the start command, only
when measurement is off), at most once per pytest session and never retried after a failure
(owner, 2026-09-29).

**The session's own state.** Before the first test the session saves the evidence (the `/status`
body when `--dut-ip` answers, then the raw FRAM dump) and checks the standard state
(Prerequisites); at its end it saves both again, compares the SCD30 values with the start and leaves
the board serving: every flash run ends with one hard reset to a serving board.

**Verify the image.** Before any bench test runs, the bench conftest's `board_image` fixture reads
the image record (`--image-record`, default beside the `.uf2`) and compares it with the board's
`GET /system`: the device, `BuildDate`, the lwIP ensemble at the record's `maxConnections`, that
`maxConnections` against this tree's device TOML, and no tick-offset test image unless
`--allow-multi-day-rollover`. A mismatch stops the session naming each deviation and the reflash
that fixes it; a record from a dirty tree is reported as a local-only image to revert after the
round. A test that reflashes mid-session runs the same comparison (`check_image()`).

## The NeoPixel sweep rig

Two flash-tier tests are gated on physical geometry rather than on wear or wall clock -
`test_isl29125_mechanism_envelope_holds_across_range_resolution_and_calibration` and
`test_isl29125_survives_recombined_realistic_lighting_scenarios`, both behind `--allow-neopixel-sweep`,
whose skip the verdict accepts while the flag is absent, so an expected skip does not read as a
failure. They are the suite's longest pair at roughly ten minutes combined. The envelope's config
pushes spend seven scratch flash writes, so it needs `--allow-persistence-write` as well as
`--allow-neopixel-sweep`, and it cleans up on every path; the lighting scenarios write nothing. What
the rig needs:

- The bench board's own WS2812 (the NeoPixel pin, `devices/dev.toml`) aimed at the ISL29125's window
  at a fixed, recorded distance -
  close enough that full-brightness white crosses the 375 lx range's top into the 10000 lx range.
  Record the geometry through the manual tier's
  `isl29125_real_lux_vs_reference_meter_and_neopixel_rig_geometry`.
- Ambient excluded (enclosure or darkened room). Ambient above the low range puts the whole run on
  the high range and fails with "only range N was ever used" - a rig fault, not a driver one.
- Nothing else driving the pixel: these scripts write the pixel directly, past `request_signal()`'s
  arbitration, so a notification signal landing mid-scenario is indistinguishable from a bad reading.

Every assertion is **relative** - continuity across the switch, no chatter, hue/saturation invariance
while the level moves, gain-ratio convergence. Absolute lux and CCT against a WS2812's three narrow
emission lines are meaningless and are asserted nowhere; the reference-meter half is the manual
tier's job. CLAUDE.md's FRAM rule applies in its sharpest form to every script here - see "A hardware
run overwrites the production modules' FRAM chunks" below before treating any log as evidence.

The rig as last recorded (the manual step saves `rig-geometry.json` into its run's evidence):

| distance | ambient | recorded |
|---|---|---|
| to be read | to be read | the manual `isl29125_real_lux_vs_reference_meter_and_neopixel_rig_geometry` |

## ISL29125 bench-rig facts, before reading any result

Each of these looks like a driver defect and is not:

- **An interrupted `main.py` leaves the WS2812 latched**, often at full white (~2000 lx at this
  geometry), because a WS2812 holds its last value and every `mpremote run` interrupts `main.py`.
  Every ISL29125 script that reads light therefore parks the pixel dark itself and takes an ambient
  baseline first. Found twice: a register probe read 65444/65272/65323 and was briefly taken for real
  saturation (parked dark, the same bench reads ~40 lx, 10.7% of the low range); and
  `isl29125_real_irq_edge.py` failed its first real run because latched white is a **static** scene -
  it crosses no threshold, no interrupt fires, and the first sample waits for the 30 s periodic tick.
  Parked dark it passes in 0.60 s.
- **The sensor can be covered or uncovered between runs** (~40 lx uncovered here, far less covered),
  so nothing compares an absolute reading across a cover change and the return-to-baseline check uses
  an LED-dominated level rather than ambient.
- **The breakout carries its own red LEDs**, so red reads systematically high against green and blue.
  Nothing asserts channel equality or a specific hue, only that HSB stays in domain and coherent with
  RGB.
- **The auto-range hysteresis band**, measured covered at this geometry (2026-09-12), in NeoPixel
  levels:

  | direction | low range (375 lx) holds | high range (10000 lx) takes over |
  |---|---|---|
  | rising | to level 6 (~197 lx) | from level 8 (~300 lx) |
  | falling | from level 2 (~76 lx) | to level 3 (~112 lx) |

  **Levels 2-8 sit inside the band and cannot force a switch either way.** Re-measure if the rig or
  the cover changes.

## Which path decides a range switch

Measured 2026-09-13, six forced crossings per setting. The chip cannot raise `RGBTHF` before `PRST`
whole RGB cycles have passed (303 ms each at 16 bit), while the driver re-checks the same condition
in software every sample with no persistence requirement. **The shorter window decides every switch.**

| `PRST` | window at 16 bit | against `SampleInterval = 1` | measured |
|---|---|---|---|
| 4 | 1212 ms | longer - software wins | 5 of 6 periodic-led, latency ~1000 ms |
| 2 | 606 ms | shorter - interrupt wins | 6 of 6 interrupt-led, 500-800 ms |
| 1 | 303 ms | shorter - interrupt wins | 6 of 6 interrupt-led, 200-613 ms |

That is why the window is derived rather than configured (SPECIFICATION.md Part M.1.4), and why
`ISL_PERIODIC_ONLY` (`W32`) - five range decisions in a row taken by the periodic path - means the
INT line looks dead rather than that a setting is wrong.

## What the two gated light tests prove

- **Mechanism envelope** (`isl29125_mechanism_envelope.py`, ~99 s of settles alone): eight steady
  levels up and back down through the overlay path, never a ramp - a ramp confounds the range step
  with the light's own change. One run proves a live read chain at every level, `Bri == max(R, G, B)`
  with every field in domain, monotonic response across the envelope, both ranges used, hysteresis
  with no chatter, the return to the low range, fixed-range pinning at both ends, 12-bit and 16-bit
  agreeing on one static scene (which is what proves the `<< 4` normalisation), `Calibrate`
  starting a run without moving the applied ratio, `Overrange` true at full white (this rig really
  does exceed 10000 lx at ~20 mm), no `ISL_PERIODIC_ONLY` (`W32`), and zero `E` entries.
- **Lighting scenarios** (`isl29125_lighting_scenarios.py`, ~8.5 min of real segments): ten scenarios
  recombining colour, slope shape, direction, start/end level, pauses and threshold proximity, driven
  **raw** because `NeopixelDriver` offers only a steady white and a 0->peak->0 triangle. Two
  cross-scenario invariants: the inter-sample gap stays at the sample interval (a stall means the read
  chain died, not that the light moved slowly), and a return-to-baseline re-read after each scenario
  catches a driver left wedged in a range.

## Writing a new device script

A test depending on an unstated rig condition is this tier's recurring failure mode - each instance
found by running the test rather than reading it. Every habit below has a check that enforces it,
named beside it; a script runs rendered (`harness.render_device_script()`), and the checks read it so.

| habit | enforced by |
|---|---|
| Every board fact - a pin, a bus, an address, a size - comes from the rendered `BENCH` dict (`tests_hardware/bench_facts.py`, from the bench device's TOML), and every product value from the TOML or `src/`, never a literal; a copy that cannot be read carries `# source:` | `tests_scripts/test_device_script_bench_facts.py`, `tests_scripts/test_tests_hardware_product_copies.py` |
| The script prints facts (`_shared/facts.py`'s `fact()`, `errors()`, `done()`) and the host test gives the verdict through `harness.parse_facts()`; every loop in an `async def` awaits on each path that loops back | `tests_scripts/test_device_script_facts.py` |
| A config write goes to a scratch path (`config_HWTEST_*`, or `hwtest-scratch/` for a script that builds the system), primed in RAM, flushed on the manager that holds it (`write_config()` only stages), and removed on every path, a leftover removed first: the removal is an allowed prerequisite write (owner, 2026-09-26) | `tests_scripts/test_device_script_config_flush.py` |
| Raw FRAM calls are addressed only from the script's declared `_SCRATCH_REGIONS`, each above the bench build's FRAM allocation and disjoint from every other script's, or from `_EVIDENCE_REGIONS` for a production read; a seed/verify pair may share one identical scratch region | `tests_scripts/test_device_script_fram_regions.py` |
| A script that reads error-log content clears its chunk at its start, after the session's evidence save; `fram_error_log_reset_race_verify.py` is the one exception, since it reads what the raced reset left | review |
| A script that boots the firmware's `main()` installs an always-printing unretrieved-task report first (the product's `PrintLog` report at level 1, or a script-local one) | `tests_scripts/test_exception_handler_contract.py` |
| A heap-measuring script sets `gc.threshold` itself and reports it as its first fact | `tests_scripts/test_device_script_gc_threshold.py` |
| A STATE-dispatched script needs the `persistence_write` marker only on the runs that pass a writing STATE | `tests_scripts/test_persistence_write_marker_completeness.py` |
| Run it in the twin first (`scripts/record_twin_instrument_runs.py`), then commit the record | `tests_scripts/test_twin_record.py` |
| Park the shared rig (the NeoPixel) dark in a `finally` | `tests_scripts/test_device_script_rig_parking.py` |
| Feed the watchdog in short steps: `_shared/watchdog.py`'s fed waits, at most 2 s a step (`l3.device_script_feed_step_ms`) | `tests_scripts/test_device_script_watchdog.py` |
| Shared code lives in `_shared/`, inlined at render by `# @include _shared/<name>.py` | `tests_scripts/test_hardware_clones.py` |

Two habits stay judgment, each learned the hard way:

- **Provide your own light.** `isl29125_plausibility_read.py` passed while a preceding test left the
  pixel latched white, then failed once another parked it dark - its result depended on test ORDER,
  with the script itself unchanged.
- **Assert a minimum engagement beside every ceiling**, or a test passes while the mechanism it
  targets never runs. A "no `ISL_PERIODIC_ONLY`" check proves nothing in a run making two switches
  when the warning needs five in a row, and an oscillation scenario passed with `switches=0` because
  both its levels sat inside the band. Every scenario now carries `min_switches` and a
  must-use-both-ranges flag beside its ceiling: `threshold_oscillation_crossing` must switch at
  least 4 times and `hysteresis_band_dwell_no_chatter` exactly zero, so an edit making either
  vacuous fails the other. Evidence for the flush habit (three scripts broken, two omissions
  cancelling so the test passed): `HEAP_FRAGMENTATION_MEASUREMENTS.md` archive §7O.

## Bench traps

None of these is discoverable by reading the code; each is a current fact of this bench.

- **A DUT that has gone unreachable is usually your own `mpremote` call, and every serial check you
  make to diagnose it re-causes the symptom.** `exec` and `run` interrupt the running firmware into
  the REPL, so `main.py` stops and the board leaves the network; `run_isolated()`'s armed
  `WDT(timeout=8000)` then resets it ~8 s after the command ends. The loop to avoid: curl fails ->
  `exec` to inspect the config -> the inspection strands `main.py` again -> curl still fails.
  Diagnose *passively*: `hard_reset()`, then `Board.tail_log()` with no `exec`/`run` at all, and
  only then curl. `tail_log()` replays buffered history, so several identical "WLAN connection
  established" blocks are **not** a reboot loop - poll `SysUptime` and watch it advance, which is
  the cheap discriminator.
- **A test that opens as many concurrent connections as the device's `max_connections`
  (`devices/*.toml`) cannot expect a definitive status from all of them**, whatever it is testing:
  the reject-when-full branch closes without a response, a FIN or an RST (SPECIFICATION.md Part
  H.7), and a slot is held until its socket closes. Measured with tiny bodies at a limit of 4:
  concurrency 2 -> 0% reset, 4 -> 25%, 8 -> 12%, 24 -> 25% - resets begin **at** the ceiling.
  **Before calling such a reset a defect, run the all-small-bodies control** - two minutes, and it
  separates the feature under test from the connection ceiling.

The rule for any test that reaches the ceiling: **assert the property your feature owns, not that
every client is served.** A body-cap test owns "every client that IS answered is answered
correctly"; being answered at all is the ceiling's business. Pair that with a floor on how many
were answered, or the test passes vacuously on a run where nearly everything was refused - the
same "assert a minimum engagement beside every ceiling" habit as for device scripts.

The rest, one fact each (occurrences: `HEAP_FRAGMENTATION_MEASUREMENTS.md` archive §7R.5):

- After an unexpected reset, read `GET /status`'s `ResetReason` and the FRAM-backed error logs
  (CLAUDE.md) before anything flashes, resets or clears the board; `journalctl -k` times the USB
  disconnect. `machine.reset_cause()` reads `WDT_RESET` after a starvation, `machine.reset()` and
  `mpremote reset` alike (SPECIFICATION.md Part F.5.4), so it only separates power-on from the rest.
  A harness `hard_reset()` or `mpremote reset` writes no record and reads as "watchdog without a
  record"; an attach or device script that stopped the boot before it finished reads as a boot
  failure in that phase (SPECIFICATION.md Part A.8).
- An `mpremote` `exec`/`run` stops `main.py`, and nothing feeds the watchdog after it, so the board
  resets about 8 s later unless the session resets it first: a device script that never feeds it
  dies ~8 s after it attaches (bench, 2026-09-25), and every raw-REPL session ends in a hard reset.
- A transient `mpremote` failure is retried - within `l4.harness_usb_grace_s`, then the device node
  re-resolved, then one USB rebind - only while the script has printed nothing: a script never runs
  twice, and every retry and rebind is a recovery event in the run record.
- The bench's USB CDC can stop entering the raw REPL until the port is rebound (recorded 2026-09-02,
  `e249999`); the harness does one unbind and bind per `mpremote` call ("Workarounds").
- Ctrl-C reaches the autostart image only while the board's 512-byte stdin ring has room: the
  firmware never reads stdin, so after a host program has sent 511 bytes (a terminal, a probe) a
  later Ctrl-C stays in the USB buffer and `mpremote`'s raw-REPL entry fails with a generic error
  that looks like a board fault. Reset the board by power or RUN (`shared/tinyusb/mp_usbd_cdc.c`,
  `ports/rp2/mphalport.c`, v1.29.0).
- A Ctrl-C into the autostart image ends its whole event loop: the board records reset reason 21
  and the watchdog resets it within its timeout; a change answered `Valid` whose deferred flush has
  not run yet is lost.
- Every flash run ends with one hard reset to a serving board (`flash/conftest.py`'s
  `leave_board_serving`).
- Every hard-reset fallback goes through `harness.recover_by_reset()`, reported as a recovery pass
  naming what the reset path skipped; for a hand recovery `.venv/bin/python
  tests_hardware/kick_then_reset.py [--device D]` kicks every station off the bench AP and then
  resets, since a reset without the kick right before it is what leaves a board in hotspot mode.
- After a reset or a flash the board can fall back to hotspot mode; `kick_all_stations()` +
  `hard_reset()` recovers it, occasionally only on a second try.
- An ad-hoc bench script caps every retry and runs under `timeout`: one that retried a refused
  `PUT` without bound ran for 1 h 40 min (2026-09-25).
- Leave > 45 s between a reset and the next `mpremote` attach; a watchdog reset ~9 s after an early
  attach is the likely, unconfirmed cause of one dead run.
- An attach within ~1 s of boot (before `main.py` arms the watchdog) parks the board at the REPL
  with no watchdog: no WiFi, no output, no self-recovery until the next reset (bench, 2026-09-25,
  when the device module armed it; the boot entry's first statement arms it now, so the window is
  shorter and unmeasured). A test that polls `is_reachable()` right after a reset must end with
  `hard_reset()`.
- A `pkill -f`/`pgrep -f` wait loop matches its own command line; list by PID or wait on a log marker.
- A running process keeps its loaded code, while a new invocation of a host tool re-reads it and its
  device script — don't edit either between chained runs.
- A FRAM pair, one entry per layer that met the failure - the guard's `FRAM_STATUS_BYTE` (`E46`,
  status byte not IDLE at a write), then the chunk's `FRAM_BLOCK_INVALID` (`W63`, block 1 invalid,
  restored from block 0) - is what a block write cut off by a reset leaves; the two-copy scheme
  recovers it.

## Workarounds

Every harness workaround of an external defect, with its bound and the event that removes it. Each
site's code comment says the same; this table and SPECIFICATION.md Part F.9 are re-checked at each
MicroPython pin move and dependency refresh; "last checked" names the date and the pin of the last
check.

| defect | where | bound | removal trigger | last checked |
|---|---|---|---|---|
| the bench's USB CDC stops entering the raw REPL until the port is rebound (recorded 2026-09-02) | `harness._usb_reset_device()`, from `Board._mpremote()` | one unbind and bind per `mpremote` call (`l4.harness_usb_rebind_cmd_timeout_s`, `l4.harness_usb_unbind_settle_max_s`, `l4.harness_usb_bind_settle_max_s`); a refused sudo fails the run | a full round records no rebind in `Board.recovery_events` | 2026-10-14, `v1.29.0` (code read) |
| a transient USB-settle failure of `mpremote` right after a reset | `Board._mpremote()` | retried within `l4.harness_usb_grace_s`, polled every `l4.harness_usb_grace_poll_s`, never once the script printed | a round records no transient retry | 2026-10-14, `v1.29.0` (code read) |
| a reset re-enumerates the CDC device under another node | `Board._mpremote()`, `_rebind_device_if_moved()` | `l4.harness_max_device_rebinds` re-resolves per call | a round records no node rebind | 2026-10-14, `v1.29.0` (code read) |
| a stale AP-side station entry survives the DUT's reset and blocks its reassociation (recorded 2026-09-02) | `BenchBridge.kick_client()`, through `kick_all_stations()` before every expected reconnect | one `iw station del` per station before each reset | a round records no stale-entry reconnect failure | 2026-10-14, `v1.29.0` (code read) |
| `nmcli -g` escapes `:` as `\:` in an SSID or PSK | `BenchBridge.ap_ssid()`, `ap_password()` | `--escape no` on every SSID/PSK read | `nmcli -g` stops escaping | 2026-10-14, `v1.29.0` (code read) |
| `nmcli connection down` errors on an inactive connection | `BenchBridge.ap_down()` | that one error taken as already down, once per call | `nmcli` makes `down` idempotent | 2026-10-14, `v1.29.0` (code read) |
| nmcli's own rescan can miss a hotspot `is_ssid_visible()` just saw (recorded 2026-09-08) | `bench/test_hotspot_role_reversal.py`'s `_join_dut_hotspot_with_reverify_retry()` | `l4.hotspot_role_reversal_join_attempts` joins, each retry a recovery note | a round records no re-verify retry | 2026-10-14, `v1.29.0` (code read) |
| a ceiling refusal under concurrent API load is the stack's reject-when-full, not a fault | `bench/test_bus_concurrency_under_api_load.py`'s `fetch()` | `l4.bus_concurrency_under_api_load_ceiling_retry_attempts` attempts per call, `l4.bus_concurrency_under_api_load_ceiling_retry_backoff_s` apart, each counted | the arms run below the ceiling | 2026-10-14, `v1.29.0` (code read) |
| one header line resets the server's per-call read timeout | `harness.HELD_PAD_LINE`, in the ceiling probe's walk | one line per held connection per step (`l4.ceiling_dwell_s`) | the walk no longer outlasts `web.per_call_timeout_s` | 2026-10-14, `v1.29.0` (code read) |
| DNAT to 127.0.0.1 does not deliver to a local socket on this bench (`route_localnet` 0) | `BenchBridge.start_udp_source_capture()`, read by `read_captured_udp_source_port()` | one `tcpdump -c 1` capture per test (`l4.bench_control_tcpdump_timeout_s`) | the redirect delivers locally | 2026-10-14, `v1.29.0` (code read) |

## Measuring heap and serving under load

Rules from the sittings that set `max_connections = 6`. The method behind them, the twin side and
the removed sweep tool's recipe: `HEAP_FRAGMENTATION_MEASUREMENTS.md` §M6 and §M5.4; the evidence is
that file's archived record ("archive §7R" below).

**Fix the question and the pass criterion before measuring.**
- **Stable** = zero true failures **and** zero device lines matching `MEMORY_ERROR_MARKERS`,
  caught-and-logged ones included. A reset before any response at the ceiling is a refusal and
  expected (`http_client.is_ceiling_close()`; owner, 2026-09-23, `84f3d57`/`399e2f0`); everything
  else — a short body, a 4xx/5xx, a timeout — is a failure.
- **A task that died is a failure too, and at DebugLevel 0 the console does not show it.** The
  firmware's unretrieved-exception report prints nothing at level 0 (SPECIFICATION.md Part F.1), so
  every console-tail memory gate also reads SYSTEM's task-end log around its window and fails on a
  new `TASK_RAISED` (`error_log_helpers.assert_no_new_task_raised()`): over `GET /status` on the bench,
  over the REPL on the flash tier (`read_live_system_log()`, which interrupts the firmware, so the
  flash soak hard-resets after each read). A test that clears the logs reads them first. A device
  script running the firmware's `main()` installs an always-printing report before it, as the PC
  tiers do; `tests_scripts/test_exception_handler_contract.py` pins all three.
- **Peak is not rounds.** Rounds of N parallel requests with pauses are typical load and overstate
  free heap (archive §7R.4). Peak is as many back-to-back clients as the limit plus forced internal work (the
  hammer test's dispatch-only SGP40 reset PUT every 3 s), on the full task graph, over every path a
  page load really fetches (`/js/app.js` included).
- **Check every body, not the status.** A static body against a validated idle reference and its
  `Content-Length`, a JSON body by parsing. The reference itself must be a 200 whose non-empty body
  equals its `Content-Length`, retried: every device-script boot drops and rejoins WLAN at ~6 s
  uptime.

**Every heap figure names the GC threshold it was measured at**; a figure that does not is void
(SPECIFICATION.md E.8). `mpremote`'s soft reset keeps the boot entry's threshold, so a measuring
script sets `gc.threshold` itself and reports it as its first fact
(`tests_scripts/test_device_script_gc_threshold.py`), and its host test names the threshold beside
every figure it records.

**Separate the verdict from the measurement.**
- An instrument that changes the system may measure but not judge: a run that calls `gc.collect()`
  before each sample gives the exact live set, and its stability verdict is not evidence. Take the
  verdict from the least-instrumented run that can give it, the heap figure from the run that
  measures it exactly — two runs rather than one approximate one.
- **Run the control**: the same load with nothing on the device but the task graph.
- **Price the instrument**: a device script's own code and globals cost heap production's frozen
  `main.py` does not pay (2,720 B: its `gc.mem_alloc()` after a collect against an import-only
  script's, archive §7R.4); samplers cost ~10-20 % of throughput. Report heap both as measured and
  production-equivalent, as a percentage of `mem_info`'s total (the linker's
  `0x20040000 − __GcHeapStart` minus the GC's own tables, ~4.3-4.5 KB scaling with heap, §M6.2).
- **rp2 has no exact end-of-GC signal** — `__del__` never runs on user-class instances and
  `MICROPY_PY_WEAKREF` is off — so a sampler that never collects cannot find the live set (archive
  §7R.4, §9). Read `_open_conns.value` as a plain int (no coroutine, no allocation); an `await`-less
  `get_value()` is a coroutine object, always truthy.

**Re-derive a tool's printed summary from the raw output when a label looks wrong**, and remember
a minimum from a 5 s snapshot bounds the true peak from one side only.

**Count on both sides, and treat a gap as a finding.** Wrap `_open_conns.increment` to count every
increment above the limit — installed as soon as `sensortask_dev.webserver` exists, not at a
`READY` line, or the first seconds of load reach only the host's count. Device allocation lines come
in pairs per failure (the `MemoryError` and the webserver's `Unhandled exception in route
handler`), so lines ÷ 2 = host 500s.

**Verify the image before its figures count.** Every image build writes its image record beside the
`.uf2` (`scripts/build_firmware.py`: the device, `BuildDate`, the lwIP macros read back out of the
built firmware, `maxConnections`, the commit and whether the tree was dirty), and the bench
conftest's `board_image` fixture checks the board against it before any bench test ("Verify the
image" above): `/system`'s `build.BuildDate`, the device, `check_lwip_ensemble()` at the record's
limit. Check the linker heap against §M6.2's per-connection formula by hand, and on the board static
`Content-Length` and `gzip -t`. Local-only images (a
`max_connections`/`[lwip]` edit) are built, recorded by recipe and reverted at once; keep each
`.uf2` aside so a later level can reflash without a rebuild.

**One fresh boot per data point, and enough of them.** Failures near the wall are probabilistic, so
zero failures in one boot proves little (archive §7R.4); the heap margin separates neighbouring limits. The
bench tests' assertion messages carry only `output[-2000:]` of device output and host tallies print
after it, so a one-boot sweep loses which level broke: per-level answers need one boot per level.

**The OpenHAB case** (`bench/test_network_resilience.py::test_openhab_case_two_pollers_and_an_open_website_are_all_served`):
for 120 s (`l4.openhab_window_s`), two pollers - `GET /measurements` and `GET /status`, each every
`l4.openhab_poll_interval_s` (5 s) - and one website client, which loads the index page's assets
once and then polls the landing section's GET route at its `pollIntervalMs` from the generated
definitions. Every response must be complete, with no ceiling refusal, no reboot (`BootSignature`
unchanged) and no task end; the per-route maximum and median latency go into the run record.

**Client-triggered console output cannot starve the watchdog**: the gated bench test
`test_console_output_with_a_non_reading_usb_host_never_starves_the_watchdog`
(`bench/test_network_resilience.py`) sets `DebugLevel` 0, holds the serial port open with DTR
asserted and never reads it, and drives the adversarial load for 60 s (`l4.console_starvation_load_s`:
six slowloris clients, a refused head, a truncated PUT and two resetting clients) - `BootSignature`
and `ResetReason` unchanged, then `DebugLevel` 5 restored. Its two `DebugLevel` writes are owned, so
it runs only with `--allow-persistence-write`.

**Holding a ceiling open** (`bench/test_heap_under_connection_ceiling.py`) needs five layered
measures, each visible only once the one above was in: no connection outlives the SPECIFICATION.md
Part H.7.1 timeouts, so holders drip a header line and recycle (`_RECYCLE_S`); started together they
expire together, so each is staggered by `i × _RECYCLE_S / N`; a connection counts as held only once
a 0.3 s read of it stays silent (a refusal answers at once); the holder threads are stoppable by the
test's own `stop` and joined; and since `run_isolated()` leaves `main.py` stopped, the test restores
the board — `harness.restore_board_to_serving()`: `kick_all_stations()`, `hard_reset()`, wait for
HTTP — in its own `finally`. `harness.discover_max_connections()` and
`test_connections_at_and_above_the_real_socket_limit_degrade_cleanly` hold theirs with
`harness.HELD_REQUEST_LINE` (`HOLD / HTTP/1.0`) and close with a plain FIN: EOF ends microdot's
headers and it answers what was asked, so a held socket costs only a small 405 and is released
the normal way (a reset is handled as well, SPECIFICATION.md Part H.7.1).

- **The ceiling probe** (`discover_max_connections()`) dwells 0.3 s per step (`l4.ceiling_dwell_s`)
  and pads every held connection with a header line (`HELD_PAD_LINE`) per step, so the per-call
  timeout never frees a slot mid-walk and only the outer cap bounds it (`probe_limit` 40 × 0.3 s,
  `l4.ceiling_probe_limit`). It fails loudly if a held connection answers instead of staying open,
  and re-checks every counted socket is still open when the refusal lands. A connect that is refused
  or times out is the wall itself, counted rather than raised, with its own 2 s timeout
  (`l4.ceiling_probe_connect_timeout_s`) apart from the read's, so a slow handshake is never read as
  a held connection. After a successful walk it waits until the whole discovered ceiling can be held
  at once again — not one slot — then allows `settle_s` for its own check connections to release
  theirs, backing off the same interval after a partial set; after a failed walk it drains one slot
  best-effort and keeps the walk's own error as the headline.
- **Pinned by the pytest tier.** `tests_scripts/test_request_timeout_ceiling.py` reads both
  timeouts from `src/` and keeps the probe's dwell and the holder's drip under `per_call_timeout_s`,
  the whole walk and the holder's recycle under `outer_cap_s`; against a loopback server it checks
  the holder keeps a parked connection through every drip until its recycle time, replaces one a
  server answered, never counts one against a server that refuses everything, starts nothing when
  the script's server never answers, and ends once its test sets `stop`.
  `tests_scripts/test_ceiling_probe.py` runs the probe and its drain wait against a loopback server
  shaped like `_serve()`: the walk finds the ceiling, padding outlasts an idle timeout a plain walk
  cannot, a refused connect counts as the wall, a connect timeout never reads as a free slot, the
  walk returns only once its whole ceiling is admittable again, and an answered walk, an exhausted
  `probe_limit`, a connection closed mid-walk and an RST refusal each fail or count by name.
  `tests_scripts/test_bench_harness_helpers.py` covers the readiness wait, the board restore's call
  order and the error-log comparison, and pins every bench thread worker to catch
  `http_client.HTTP_ERROR` as well as `OSError`.
- **Both instruments that wait for a device script's own server** first let main.py's go quiet
  (`harness.wait_for_script_server()`), so main.py can never answer the readiness probe.

**The C-stack budget** (`flash/test_memory_stress.py::test_c_stack_peak_is_within_half_the_limit`,
`device_scripts/c_stack_budget.py`, L3, ungated) boots the bench device's generated system over the
scratch config directory `hwtest-scratch/`, wraps every I2C bus leaf and the FRAM driver's two sync
leaves from outside to record `micropython.stack_use()`, runs the started tasks and timers for a fed
10 s window (`l3.c_stack_budget_window_ms`), then dispatches one `GET /status` in-process through the
app's own `dispatch_request()`: the top of the longest static await chain
`tests_scripts/test_await_depth.py` pins (SPECIFICATION.md Part F.1), which must answer 200, since
Microdot answers a raising handler with a 500. The host holds the peak to half
the 7,936 B limit; the twin's figure (`twin_c_stack_peak`) is reported, never compared. No flash
cycle and no production config file: each setup writes its defaults once into the scratch
directory, removed afterwards; the booted modules' logs go into FRAM, which the session start saved
first.

## Chip conformance probes

Every bus chip - the ISL29125, SCD30, SGP40, BMP3xx and FRAM - has a probe script that talks raw
`machine.I2C`/`SPI` only (`device_scripts/<chip>_conformance_probe.py`,
`isl29125_mock_conformance_probe.py`), so the same file runs against the part on the bench and
against the chip's fake in the twin. `flash/test_chip_conformance.py` runs each on the board, then
`conformance.py` runs it through `TwinBoard` at both GC stages (`gc.threshold` -1 and 32768) and
diffs the two: a protocol key verbatim, a physical key - one that depends on what falls on the part,
such as light or CO2 - only in an independent form both sides must hold (a CRC that verifies, a value
in range, a relation). A divergence is a fidelity finding, recorded in `digital_twin/README.md`'s
fidelity table, never a fake edit made to pass; decide which side is wrong from the datasheet **and**
a fresh measurement, never from the fake (SPECIFICATION.md Part C.11.1; Part M.1.2 lists what the
ISL29125's first real run found). A missing Unix-port build fails the twin half with the build hint
rather than skipping. The ISL29125's 12-bit conversion cycle is measured by its probe and reported,
and the BMP3xx probe reports the part's chip id and calibration block. The SCD30's argument reaction
(a wrong argument CRC, an out-of-range interval) is recorded, not judged, with up to three SCD30 NVM
writes restored in the script, so it runs only with `--allow-persistence-write` and
`--allow-scd30-extra-write`.

## Reset codes proven on the bench

Each `ResetReason` code (SPECIFICATION.md Part A.8 holds the meanings), the test that proves it and
its level. Every bench test reads the code from `GET /status` after a serving boot, with the FRAM
evidence saved first. `ResetBits` is recorded for every row; once measured, a table here lists the
raw flags each reset kind leaves.

| code | test that proves it | level | on silicon |
|---|---|---|---|
| 0 | `bench/test_reset_reasons.py::test_an_invalid_record_reads_as_unknown` | L4 | not yet run |
| 1 | `manual/manual_persistence.py`'s power-cycle steps (each reads `ResetReason` after power returns) | manual | not yet run |
| 2 | `bench/test_reset_reasons.py::test_a_harness_hard_reset_reads_as_watchdog_without_a_record` | L4 | not yet run |
| 3 | `bench/test_end_to_end_timing.py::test_real_reboot_sequencing_via_rest_completes_cleanly`; `flash/test_system_commands.py::test_a_reboot_with_storage_paused_still_resets_attributed` | L4, L3 | not yet run |
| 4 | `bench/test_reset_reasons.py::test_a_bootloader_reboot_is_attributed` (the way back is `sudo picotool reboot`, no load); `flash/test_system_commands.py::test_bootloader_command_shuts_down_then_enters_bootsel` | L4, L3 | not yet run |
| 5 | `bench/test_reset_reasons.py::test_the_supervisor_escalation_reboot_is_attributed` (a task dying until the budget reboots, also with a console host holding the port unread) | L4 | not yet run |
| 6 | `bench/test_reset_reasons.py::test_the_starved_watchdog_fallback_is_attributed`; the fallback itself on L3: `flash/test_watchdog_starvation.py::test_reboot_falls_back_to_starving_the_watchdog_when_its_timer_cannot_arm` (`reboot_fallback_starves_the_watchdog.py`) | L4, L3 | not yet run |
| 7 | `flash/test_system_commands.py::test_config_reset_deletes_every_config_file_and_reboots`; `bench/test_system_commands_over_rest.py::test_config_reset_over_rest_brings_back_the_defaults` | L3, L4 | not yet run |
| 8 | `flash/test_system_commands.py::test_fram_erase_blanks_the_chip_and_every_logger_restarts_empty`; `bench/test_system_commands_over_rest.py::test_fram_erase_over_rest_blanks_every_error_log` | L3, L4 | not yet run |
| 9 | `bench/test_reset_reasons.py::test_an_incomplete_command_is_attributed`; `flash/test_system_commands.py::test_a_hung_shutdown_step_ends_in_a_watchdog_reset` | L4, L3 | not yet run |
| 11-15 | `bench/test_reset_reasons.py::test_a_hang_in_boot_phase_p_is_attributed`, one case per boot phase 1-5 | L4 | not yet run |
| 20 | `bench/test_reset_reasons.py::test_a_c_stack_exhaustion_is_attributed` (`reset_code_stack_exhausted.py`: a reader recursing until the stack check raises; the handler that catches it records the overflow and the supervisor's next pass reboots with the stack code) | L4 | not yet run |
| 21 | `bench/test_reset_reasons.py::test_a_console_interrupt_is_attributed` | L4 | not yet run |

## System commands

`PUT /system {"SystemCmd": ...}`, each command at L3 (`flash/test_system_commands.py`: over USB,
through the webserver's dispatch into the generated callback over a scratch config directory) and at
L4 (`bench/test_system_commands_over_rest.py`: over REST on the bench network). Each test saves the
FRAM evidence first (the raw dump, and `GET /status` on the bench) and reads the attribution after
the reset:

- **`resetconfig`** deletes every config file and reboots (code 7). At L3 its deletes and the
  following boot's defaults land in the scratch directory, owned scratch flash writes behind
  `persistence_write`, and the hung-step case spends the same. At L4 it deletes the board's real
  files: the test saves them first (`config_files_dump.py`), and since the boot that follows has no
  WiFi settings, it joins the DUT's own hotspot to read the defaults back, then writes the saved
  files back once each (`config_files_restore.py`) and leaves the board serving - behind
  `persistence_write`. A board found holding no config file is an aborted earlier run's: the newest
  saved set in `build/archive/` goes back first.
- **`erasefram`** blanks the whole chip and reboots (code 8), destroying every FRAM-backed log: the
  raw dump runs first. L3 also measures the erase's feed gaps, races it against a chunk write, a bus
  session and a storage pause, and cuts it with a reset mid-erase (every chunk old or blank after);
  L4 checks every error log blank after the boot. FRAM is outside the wear budget.
- **`reboot`** and **`bootloader`** run the reboot sequence - record, flush, pause, reset - and the
  reply precedes the reset within its bound (codes 3 and 4); a hung shutdown step ends in a watchdog
  reset read as command incomplete (code 9).
- **`mempause`** pauses storage; a reboot with storage paused still resets attributed (L3), and L4
  races `erasefram`, `reboot` and `mempause` at once, then `reboot` and `bootloader` at once.

A near-miss action word does nothing at either level, and a refused command never stops the feed.

## Recovery rungs on silicon

Each rung of the recovery ladder (SPECIFICATION.md Part F.2) with the trigger a test injects, the
level that reaches it and its discriminating oracle. Raw-REPL access stops `main.py`, so a rung that
needs a driver-level trigger is not reachable at L4 except by hand.

| rung | trigger | level(s) | test | oracle |
|---|---|---|---|---|
| retry | one failed cycle under concurrent bus load | L3 | `flash/test_bus_concurrency.py`'s same- and cross-device tests | the next trigger reads valid |
| participant | the chip's recovery: the BMP3xx soft reset with its OSR re-applied, the SGP40 heater-off, the FRAM's WREN repeated once | L3 | `test_bmp3xx_same_device_read_write_concurrency`, `test_cross_device_concurrent_sessions_genuinely_interleave`, `test_fram_cs_pin_hijack_fault_injection_and_recovery` | a valid read after the rung, the OSR as configured; the dropped WREN recovered |
| bus clear and controller re-init | a real held SDA (`i2c_held_sda_recovery.py`); `recover()` among every device's reads | L3; L4 not reachable (raw REPL stops `main.py`), by hand with the manual SDA-to-GND step | `test_a_held_sda_line_is_cleared_and_every_device_answers`, `test_bus_topology_autodetect_address_and_reserved_range_sweep`; `manual/manual_bus_electrical.py::test_wedged_i2c_bus_watchdog_backstop` | SDA high and every device answers; no sibling read fails; by hand the bus-recovery entries, then `ResetReason` 5 |
| boot bus clear | SDA held at construction | L3 | `test_a_held_sda_line_is_cleared_and_every_device_answers` (its boot-clear case) | SDA high, the controller constructs, every device answers |
| WiFi radio re-init | `_recover_device()` on a connected link | L4 | `bench/test_wifi_radio_reinit.py` (`wifi_radio_reinit_recovery.py`) | the link back within the connect budget |
| task restart | a starter that dies at once; a chip unplugged live | L3; manual L4 | `flash/test_task_supervisor.py`; `manual/manual_bus_electrical.py::test_hot_unplug_replug_i2c_recovery`, `::test_fram_unplug_replug_recovery` | the starter called again, SYSTEM's log holding one `TASK_RETURNED` end per restart; by hand the log entries while unplugged and the readings back with no reboot |
| FRAM chip lost | CS held inactive across two writes; the chip unplugged | L3; manual L4 | `test_fram_cs_pin_hijack_fault_injection_and_recovery`; `::test_fram_unplug_replug_recovery` | the chip-lost entry, then recovery; by hand the seconds from the pull to the first FRAM log entry (`fram-pull-latency.txt`, "none within 120 s" when none) |
| UART link lost | the crossover jumper pulled mid-transfer | manual L4 | `manual/manual_bus_electrical.py::test_uart_crossover_pull_recovery` | the link's `Failures` rise and every code logged meanwhile (`uart-crossover-pull.txt`, the verbatim errcount beside it), its `Transfers` advancing within 30 s of the replug, no reboot |
| supervisor reboot | a task dying until the restart budget is spent | L4 | `bench/test_reset_reasons.py::test_the_supervisor_escalation_reboot_is_attributed` | `ResetReason` 5 and SYSTEM's escalation entry |
| hardware watchdog | the watchdog starved | L3, L4 | `flash/test_watchdog_starvation.py`; `bench/test_reset_reasons.py` (codes 2 and 6) | the reset, then the code |

## The hotspot role reversal

`bench/test_hotspot_role_reversal.py` turns the bench radio into a client of the DUT's own hotspot
(SPECIFICATION.md Part E.6.4). Its module fixture `joined_hotspot` clears the SSID (stage 0), joins
the hotspot (stage 1) and takes a lease (stage 2); the stage tests read what it recorded, and the
fixture's teardown restores the SSID (stage 7) and the bridge (stage 8).

- **Every path restores.** A setup failure after stage 0's `PUT {"SSID": ""}` reaches the DUT over
  its hotspot, puts the saved SSID back and brings the bridge back; a refused or unreachable restore
  raises, naming the stranded state and the repair below, so it never passes silently. The flip back
  is a test of its own, `test_the_role_flips_back_and_the_board_is_sta_connected_on_the_bridge`,
  which asserts the board is back on the bridge in STA mode with stage 0's SSID; the teardown repeats
  the flip back only when that test did not get it done. The flip back waits for a passive
  reconnect, then kicks and resets at most once through `harness.recover_by_reset()`, reported as a
  recovery pass.
- **The credential stage runs last.** Stage 6's tests carry `destructive_last`, which
  `conftest.py`'s collection hook moves behind every other test of the module, the order otherwise
  kept, so a reorder cannot run them before a read-only check.
- **The lease test asserts the range MicroPython's DHCP server hands out**: the AP's server is
  `shared/netutils/dhcpserver.c` (`v1.29.0`), which leases the server's own first three octets and a
  last octet of 16 to 23 (`dhcpserver.h`'s `DHCPS_BASE_IP` and `DHCPS_MAX_IP`).
- **What a failed stage-6 credential does**: a credentials change lands in the fresh-boot state
  (owner, 2026-10-08, paraphrase), so a failed real-credential `PUT` reopens the DUT's hotspot once
  more although it has run since stage 0; with no client its window ends in one more streak and then
  the silent mode, which retries once per `hotspot_time_min` (SPECIFICATION.md Part A.4). Nothing is
  terminal: the flip back's reset ends the wait. Two stage-6 cases pin this path, and both compare
  WIFI's history before and after and never clear it:
  `test_a_wrong_password_over_the_hotspot_reopens_the_hotspot` (`persistence_write`: it owns one
  flash write, a well-formed wrong password, which the real-credentials test after it restores) and
  `test_a_second_failed_streak_goes_silent_and_links_on_a_later_attempt`. The second case is two
  `hotspot_time_min` windows long (16 min on `dev`) plus its streaks; it writes nothing and runs on
  the real-credentials test's write, so it needs the whole module in one run with
  `--allow-persistence-write` and a `--soak-duration` covering both windows (`long` on `dev`), and
  skips otherwise. A candidate invocation, not yet run on hardware:
  `scripts/run_bench_soak_tests.sh --duration long --allow-persistence-write -m role_reversal`
  (pytest takes the last `-m`).
- **The role-reversal repair**, for a board still unreachable after the fixture gave up (the
  message says "stranded in hotspot mode"): first `.venv/bin/python tests_hardware/kick_then_reset.py`
  ("Bench traps"). With the SSID still empty the board returns to its hotspot, so the SSID goes back
  over the serial console: wait the 45 s "Bench traps" names after the reset, then rewrite the
  `SSID` field (and `PW`, after a failed stage-6 run) of the board's `config_WIFI.cfg`, a JSON
  object, in one `mpremote exec` that loads, edits and dumps it. The raw-REPL entry stops `main.py`,
  so the watchdog resets the board right after; with the bench AP up it rejoins the bridge. The
  bench AP's own values come from `nmcli`, never from this file. Not yet run on hardware.

## What the network-fault injections reach

What each injection on the bench reaches, and what it cannot (`bench/test_network_resilience.py`,
`bench/test_hotspot_role_reversal.py`; every fault is undone by the `FAULT_COMMENT` cleanup in "Host
network"). The source trace of the DUT's source filter is SPECIFICATION.md Part C.7.2's "No origin
check" paragraph.

- **Drops and impairments reach the DUT's own traffic**: `block_udp_ports()` drops by destination
  port and `block_udp_ports_from()` by source port, both in the bridge's FORWARD chain, and a
  `tc netem` qdisc on the AP radio adds loss, delay, jitter, corruption, duplication or reordering.
  The four netem tests prove REST reachability under the impairment and recovery after it, which
  their names state; none waits for an NTP exchange inside the window.
- **Every garbage injection proves it was delivered.** The NTP and DNS garbage tests redirect the
  port with a `nat` PREROUTING DNAT to a `RogueUdpResponder` on 127.0.0.1, and each asserts the
  responder answered the DUT's address at least once (`answered_from`), so a redirect that never
  delivered fails as "the injection never reached the DUT", never as a pass. That redirect may not
  deliver on this bench: a live `iptables -t nat -L PREROUTING -n -v` poll showed the rule matching
  real traffic while a listening socket on the redirected port received nothing, across several
  `hard_reset()` cycles, and `net.ipv4.conf.*.route_localnet` reads `0` on every interface, the
  Linux condition under which DNAT to 127.0.0.1 from a non-loopback interface fails. The garbage
  tests have not run on the bench since the delivery check; their next run settles it.
- **A garbage DNS reply and silence log the same code** (`NTP_DNS`: `resolve_ipv4()` keeps no log
  of its own), so the DNS garbage test's delivery proof is the responder's count, not the log.
- **The redirect cannot exercise the DUT's source filter**: conntrack rewrites the redirected
  reply's source to the original server. The connected-socket test reaches it instead: it holds the
  real reply back with `block_udp_ports_from([123])`, reads the DUT's port from a `tcpdump -c 1`
  capture (`start_udp_source_capture()`, the Workarounds table) and sends the spoof from this host,
  asserting it left within the client's reply timeout.
- **The off-subnet spoof is attempted** (owner, 2026-09-28: 'let's at least try it'):
  `test_spoofed_off_subnet_source_address_is_ignored` forges a DNS query from an RFC 5737 address
  through a raw socket (`sudo -n` `tests_hardware/spoof_udp.py`, Prerequisites item 2) and asserts
  the DUT sends nothing to that address and still answers a legitimate query. Not yet run on the
  bench (SPECIFICATION.md Part E.6.6's `off-subnet-spoof` row).
- **A DNS flood reaches the normal receive path only**: a garbage payload is still a real
  `(data, addr)` from `recvfrom()`, so `test_dns_flood_leaves_captive_dns_serving_and_it_recovers`
  proves serving under flood and recovery after, never the receive-failure backoff, which is L1's
  (`tests/test_asy_captive_dns.py`).
- **DHCP is not fault-injected, a documented known limitation (owner, 2026-09-26)**: the DUT's DHCP
  client is lwIP's and the AP-side server is MicroPython's `shared/netutils/dhcpserver.c`, no
  project code on either side; the bench bridge's DHCP server is NetworkManager's `dnsmasq` with no
  per-request fault knob, and a rogue DHCP responder could strand the DUT without a lease, with
  nothing in this tier able to recover it. Network-robustness tests treat "WiFi up, no internet" as
  NTP/DNS unreachable and only use DHCP results (`bench/test_hotspot_role_reversal.py` asserts the
  hotspot lease range).

## Known assumptions and open findings

Flagged while writing this tier against real source/datasheets, or found once real-hardware runs
started. Read them before trusting a run's results blindly - a failure in one of these areas may
point at a flagged assumption being wrong, not at a real product bug. Resolved items are struck
through, kept (not deleted) so a reader mid-investigation doesn't wonder whether something was ever
a live question:

- ~~The bench has never run MicroPython 1.29.0.~~ — **resolved (2026-09-11): it has, repeatedly.**
  Real `dev` firmware built from `src/` and flashed, with the flash, bench and mid soak tiers all
  run clean against it. All three items that wanted on-target confirmation are answered: the SPI
  RX-overrun raise site and the `deinit()` no-ops (both in BACKLOG.md's "Deferred" list), and the
  SRAM-placement change, now measured rather than inferred (SPECIFICATION.md Part F.5.3).
- **A hardware run overwrites the production modules' FRAM chunks — never read an error log as
  firmware evidence straight after one.** `FRAMManager` is a deterministic bump allocator (a
  required property, SPECIFICATION.md Part A.4), so a device script's own first chunk *is*
  production's first chunk. Usually the next boot's `_read()` just fails on the size/CRC mismatch
  (each chunk's CRC is seeded by its owner's name) and the log honestly reads empty — but a script
  leaving a well-formed chunk behind under the production owner's name fabricates a plausible one.
  `fram_error_log_reset_race_seed_and_race.py` seeds three entries into what is physically
  SystemService's chunk; before the owner seed, a seeded entry read back as a plausible SYSTEM task
  end (test data, not firmware evidence; chased down as real on 2026-09-11). CLAUDE.md's
  "read the FRAM logs before clearing" rule assumes a board that has been running normally — check
  what was last run against this one first. Every session therefore saves the whole FRAM part raw
  at its start and end (`fram-raw-session-start.txt`, `fram-raw-session-end.txt` in the run's
  evidence, `fram_raw_dump.py` reading only) and `GET /status` with it on the bench, so the
  before-image is kept and every entry a run adds is attributable. Two kinds of entry a run leaves
  in the production history are its own: every scratch build (`build_system()` or `main()` over
  `hwtest-scratch/`) records `W CONFIG_LOST` (69) in SYSTEM's history, since its settings file is
  absent while FRAM history is restored; and test-band residue - the reboot script's load entries,
  an erase script's seeds when it fails before erasing - is the same kind.
- **The chunk reset race lands on each named seam, and a stale seed cannot pass.**
  `flash/test_fram_storage.py::test_error_log_history_is_all_or_nothing_across_a_reset_raced_chunk_write`
  runs once per seam of a chunk write's five transfers (status byte 1 and 2 BUSY, payload and CRC,
  status byte 1 and 2 IDLE): the seed phase seeds three test-band entries chosen by a fresh nonce
  and resets right after that transfer (`LANDED seam=<n>`), and the verify phase accepts only the
  whole history lost, the seeded three, or the seeded three plus the raced entry - so a history
  seeded by another run fails - then clears the chunk.
- **The UART link's coverage on silicon is 11 flash-tier tests and 5 bench-tier tests**
  (`flash/test_uart_crossover.py`; `bench/test_uart_link_under_api_load.py`,
  `bench/test_uart_link_crc16.py`), none run since the receive path moved onto the DMA ring. Each
  crossover script that runs the link runs with no CRC and with CRC16; the bench link suite runs
  once per mode, the CRC16 run behind `--allow-flash-cycle` (two reflashes: the CRC16 image built
  with `--device-toml` from a copy setting `crc = "crc16"`, and back to the round's image).
  - Two platform findings are asserted rather than documented: F.5.8's clamped read
    (`uart_driver_read_never_blocks_the_loop.py` times the shipped driver's own synchronous calls
    against an unclamped `machine.UART` read of the same frame, its control arm: longest call
    126-132 us against 3,251 us, 2026-09-25) and F.5.9's idle poll rate (`uart_idle_poll_rate.py`).
  - Each link receives through a DMA ring (SPECIFICATION.md J.6): `uart_dma_ring_interrupts_off.py`
    holds interrupts off for the flash's datasheet erase and program times without writing flash and
    shows no frame lost within the ring's bound and an overrun beyond it; its STATEs run a soft reset
    during traffic (no DMA channel left running), a break mid-frame (that transaction alone fails)
    and a real config write during traffic, the last only with `--allow-persistence-write`. A
    maximum-size train crosses the jumper intact and an over-cap train is refused before any
    allocation (`uart_crossover_exchange.py`).
  - `uart_comm_hazards.py` runs the comm hazards across the jumper: two initiations on one instance,
    `clear()` racing a transaction, both ends transmitting, the first-chunk field boundaries and a
    stalled TX. `uart_link_under_concurrent_system_load.py` runs the link against both I2C buses,
    the FRAM's SPI bus and heavy allocation churn at once, asserting both ways - the link keeps
    transferring *and* nothing else was starved.
  - The bench tier carries a multi-chunk SET under serving load (`uart_link_echo_under_serving_load.py`
    driving the initiator's public `uart_set()`), with no `src/` change, besides the link's
    transfer/failure count in `/status`'s `UARTLINK`, asserted advancing while the API is hammered.
    The comm hazards under API load are not written: the hazard script drives the raw UART pair,
    which a serving `main()` owns (SPECIFICATION.md E.6.6).
  - The UART fault catalog (~20 scenarios: corruption, drop, truncate, duplicate, overrun, lost
    final ACK, peer reset mid-transaction, ...) is mock-only, a listed structural exception: no
    injection hardware will be bought (owner, 2026-09-22), and a second raw UART is not used as a
    stand-in (owner, 2026-09-22). On silicon the flash tier covers silence and a baud mismatch
    (`uart_crossover_recovery.py`), and `uart_comm_hazards.py` the concurrency and field sweeps.
  - A build without the UART modules fails the tier, never skips; a board running an image older
    than the tree simply does not carry a change, which "Verify the image" catches.
- **A device script's every wait must stay inside its own watchdog window, or a link fault reports
  as a reset instead of a result.** `tests_hardware/device_scripts/uart_crossover_*.py` arm an 8s
  `machine.WDT` and used to join their responder task with `asyncio.wait_for(listener, 10/12)`.
  That join can never complete on its own when the frame never arrived - `uart_listen()` parks in
  its one legitimate unbounded read - so the watchdog fired first and the run died with an
  `mpremote` I/O error and no `RESULT:` line at all. Found (2026-09-11) by running the exchange
  script with UART1 deliberately moved to unjumpered pins, i.e. by simulating the exact wiring fault
  this tier exists to catch. Both scripts now poll `task.done()` in bounded steps, feeding as they
  go, and use `UARTComm.clear()` - the module's own documented unstick - to free a parked listener.
  The same run now reports `GET returned None ... ` with `UART_NO_ACK` (`errno` 81, initiator) and
  `TIMEOUT` (`errno` 22, responder read timeout), which is the diagnosis a bench session actually
  needs.
- **Both crossover device scripts poll at two rates, matching `sensortask_dev.py`**: `POLL_WAIT_MS`
  (2 ms) for a transaction in flight, `POLL_IDLE_MS` (50 ms) for a listener waiting on a frame that
  may never come (SPECIFICATION.md Part F.5.9). A script that used one rate would not be exercising
  the shipped configuration, which is the whole point of the flash tier. The practical consequence
  for a bench session: a responder notices the first byte of a frame up to 50 ms late by design, so
  a measured first-frame latency on this rig includes that and is not a link fault.
- **`asy_uart_driver.UART.deinit()` does not release the GPIO function select, so a script that
  inits a UART on different pins poisons that peripheral until the next hard reset.** Confirmed the
  hard way (2026-09-11): a throwaway diagnostic that put UART1 on GP4/GP5 left those pins muxed to
  UART1 after `deinit()`. UART1's RX input then kept being taken from the floating GP5 instead of
  the jumpered GP9, so **every subsequent run of the real crossover tests failed** - deterministically,
  and across `mpremote`'s own soft resets, which do not restore pin defaults. A `mpremote reset`
  (real hard reset) cleared it immediately. The shipped scripts always use GP8/GP9 and never hit
  this, but any ad-hoc device script that moves a UART's pins must hard-reset the board afterwards
  before its results - or the next test's - mean anything.
- **A device script that reads error-log content clears its chunk at the START, never at the end.**
  Clearing first is what makes a run deterministic: the chunk is real persistent storage, so
  without it a script inherits the previous run's ring and its assertions drift silently. Clearing
  at the end would destroy the evidence of what the script just did. Residue is the accepted
  outcome; the caveat above is how a reader avoids misreading it.
  `fram_error_log_reset_race_verify.py` is the one deliberate exception — it exists to read what
  the raced reset left behind, so a baseline wipe would erase the thing under test.
- ~~Does `mpremote`'s implicit soft-reset re-execute the frozen `_boot.py`/`boot.py`/`main.py`?~~ —
  **resolved: no.** Confirmed against the pinned MicroPython C source and empirically on real
  hardware: only a genuine `hard_reset()` resumes the live system; `exec()`/`run_isolated()` never
  do, regardless of `soft_reset_after`. See `harness.Board.run_isolated()`'s own docstring for the
  full finding. Tests that need to observe the *real* boot sequence correctly use `hard_reset()` +
  `tail_log()` instead, for exactly this reason.
- **A device script's heap reading is taken inside `main.py`'s aged heap, so a standalone figure and
  an in-suite one are not comparable.** Same consequence as the bullet above, and it has produced a
  false conclusion once: freshly flashed, the heap probe read 95,104 B and passed; deep in a suite
  the *same* firmware read 28,864 B and failed, with `free` unchanged to 0.2 % — the defect is
  position-dependent and a cold build cannot see it. **Any heap figure must state its suite
  position, or it is not a comparison** (HEAP_FRAGMENTATION_MEASUREMENTS.md §M3.9).
- ~~Is it safe to poll a live, already-running system with `board.exec()`/`is_reachable()`?~~ —
  **resolved: no, never.** `mpremote`'s `enter_raw_repl()` unconditionally sends Ctrl-C plus, by
  default, a real Ctrl-D `machine.soft_reset()` before running anything — polling either one against
  a live system self-resets its heap on every single poll, wiping the very state being waited on
  (this once made a real reboot's own transient unreachable window look like the reboot silently
  never happened). **Rule**: use the genuinely passive `Board.is_device_present()` (opens/closes the
  serial port, sends nothing) for any liveness poll against a live system. `is_reachable()` stays
  `mpremote`-based deliberately, for the few callers specifically testing that reset mechanism
  itself (e.g. the flash tier's own connection-stability test) — see both methods' own docstrings in
  `harness.py`.
- **`machine.soft_reset()` keeps `time.ticks_ms()` counting** (free-running); a raw-REPL entry stops
  `main.py`, and the watchdog then resets the board, which zeroes it - so the rollover check observes
  over REST only (`bench/test_ticks_ms_rollover.py`).
- **The off-subnet spoofing test** (`bench/test_hotspot_role_reversal.py`) sends a hand-built
  datagram through a raw socket under a named sudo rule (`tests_hardware/spoof_udp.py`,
  Prerequisites item 2).
- **`nmcli -g IP4.ADDRESS` returns a CIDR-suffixed address, `IP4.GATEWAY` a plain one**
  (`bench_control.BenchBridge.own_ip_on()`/`gateway_ip()`).
- ~~Captive-portal hotspot-mode redirect fallback (SPECIFICATION.md Part A.5) - real-hardware
  verification status: NEVER ACTUALLY RUN under a valid configuration.~~ — **resolved: confirmed
  working on real hardware (2026-09-03), on the real `dev` build via
  `scripts/build_firmware.py dev`** (the now-deleted `DEV_HARDWARE_BASELINE_PLAN.md` §4b steps 10-12). A real
  `GET /generate_204` over the real hotspot link returned a genuine `302`/`Location: /`, `GET /`
  served the real site (`200`), and all three sensors (BMP3xx/SCD30/SGP40) read plausible real
  values — a 6.5-minute stability window afterward showed zero real errors on any module, watchdog
  armed throughout. The earlier "dropped as noise" finding (a bare 404 on a mismatched
  `scripts/build_firmware.py wozi`-on-dev-bench test) is now doubly moot: not only was that
  configuration invalid, the *real*, valid `dev`-native configuration has since been directly
  confirmed working. `src/`'s own `is_hotspot_active()`/`_StaticRoutes.serve()` logic was already
  proven correct against the real Unix-port interpreter; this closes the one remaining "never run on
  real rp2/lwIP" gap. Per CLAUDE.md's hard rule, `wozi` is never physically flashed — this dev-bench
  result is the real, complete verification, valid for `wozi` too.
  **Pitfall found investigating this, still worth keeping**: don't reach for `mpremote exec()` to
  inspect live state — per the liveness-polling finding above, `exec()` soft-resets the board and
  wipes the very live state you're trying to observe. Use a passive method (a second REST/
  network-level check, or a genuinely code-level trace) instead.
- **A real phone can fail to show the captive-portal "Sign in to network" prompt even though the
  DUT's own server-side behavior is textbook-correct** (real-hardware production-hotspot session,
  2026-09-03, Samsung Galaxy A54 5G / One UI 8.5): connecting showed Android's "No internet" badge
  in the WiFi list, with no sign-in popup, despite a direct check confirming the DUT answered every
  captive-portal probe host with a real `302`/`Location: /` and DNS-spoofed every hostname to its
  own IP exactly as `SPECIFICATION.md` Part A.5/`asy_captive_dns.py` describe. Not a `src/` bug — this
  is almost certainly phone-side: (1) **Private DNS (DNS-over-HTTPS)**, when enabled in Android's
  network settings, bypasses the DUT's local DNS spoofing entirely for the connectivity-check
  request, so on an isolated hotspot with no real internet the check simply times out with no
  signal, instead of getting the redirect that would trigger the popup — turning it off (or setting
  it to "Automatic", which most Android versions correctly skip on a network with no working DNS
  resolution to a public DoH provider) is the fix to try first; (2) Android can cache a "no
  internet" verdict per-SSID, which would also explain the badge appearing before even tapping to
  connect, if the same SSID (`"SensorNode"`, the config default) was already seen failing this
  check on a previous connection (this bench's own repeated automated test runs are a plausible
  source) — forgetting the saved network and rejoining fresh rules this out. No code changed as a
  result of this investigation.
- **The standard board state holds `DebugLevel` 5; boot oracles need at least 3, and the session
  fixtures check the level before the first test.** The tier's log-based synchronization reads
  one-time-per-`setup()` lines (`harness.BOOT_COMPLETION_MARKERS`, read through `wait_for_boot()` and
  `boot_lines()`) and `asy_wifi_service.py`'s `pr.one()` lines, all printed at `DebugLevel` >= 3
  (`asy_print_log.py`'s `_LOG_ONCE`); `test_real_ntp_sync_succeeds_over_genuine_udp` needs
  `asy_ntp_client.py`'s `pr.all()` lines at 5. At the shipped `DebugLevel` 0 none of these print, so a
  board left there reads as a dead link: on 2026-09-04 a full 77-test bench run gave 2 failures and
  48 errors, none a regression. The standard-state fixture now stops such a session at its start
  naming the level, or repairs it with `--repair-standard-state` ("Prerequisites").
- **WS2812 bit timing is specified in `datasheets/ws2812/WS2812.pdf` p.4** ("Data transfer time":
  T0H 0.35 us, T1H 0.7 us, each +-150 ns; reset low above 50 us). The manual
  `test_real_ws2812_neopixel_signal_timing` compares a scope or logic-analyzer trace against it when
  one is at hand, colour correctness by eye otherwise; automating it needs a logic analyzer the
  bench does not have (no test hardware is bought, owner, 2026-09-22).
- **WiFi reconnection flakiness after a hardware reset - root-caused and mitigated.** A hard reset
  followed by a fresh STA connect attempt used to sometimes fall back to hotspot mode instead of
  reconnecting. **Root cause, confirmed decisively via a real-hardware A/B test**:
  NetworkManager's own AP-mode backend for `br0-wifi-ap`
  (confirmed to be its internal `wpa_supplicant`, not a separate `hostapd` process) retains a stale
  station-table entry for the DUT's MAC across a hard reset (a real power-cycle, no clean 802.11
  deauth), and a fresh association racing against that stale entry doesn't reliably get treated as
  a clean new session - 10/10 trials fell back to hotspot with the stale entry left in place, 10/10
  connected cleanly once it was cleared first. Not a `src/` bug - `asy_wifi_service.py`'s own
  retry/hotspot-fallback logic behaves exactly as designed. **Fixed**: `bench_control.BenchBridge.
  kick_all_stations()` (wrapping the `kick_client()`/`bench_associated_station_macs()` primitives)
  is now called before every `hard_reset()` that expects a real reconnect afterward - the `dut_ip`
  fixture, `joined_hotspot`'s recovery fallback, and `test_real_sta_connect_reaches_established_
  after_a_hard_reset` (`bench/test_wifi_networking.py`, now also asserts a real connection, not
  just any WiFi-related log line).
  - One real caveat for the field, not a reason to distrust this fix: a device WDT-looping against
    a real router would hit the same stale-entry pattern with no bench harness able to
    `kick_client()` on its behalf.
  - **Confirmed the same fix is also required after a `picotool load` reflash, not just
    `hard_reset()`** (BACKLOG.md's 2026-09-05/07 real-hardware `MemoryError`-mitigation sessions,
    hit repeatedly, every single reflash): a fresh flash cycle reboots the board the same abrupt,
    no-clean-802.11-deauth way a hard reset does, so it's mechanically the identical hazard - `kick_
    all_stations()` before the post-flash reconnect attempt, every time, not just around
    `hard_reset()` calls already inside the test harness itself.
- **A CYW43 link can report `isconnected()` true while the association is dead; the recovery is a
  power cycle or `hard_reset()`.** An independent reachability probe was judged not worth its
  complexity (owner, 2026-09-04, `655e4f9`). Seen while confirming the stale-station fix above at
  scale: a real `arping` got no answer from the DUT while `iw station dump` showed it associated for
  hundreds of seconds across the whole outage, and `asy_wifi_service.py`'s
  `_wlan_isconnected_or_false()` passes `wlan.isconnected()` through, so its retry cannot fire on a
  disconnect the firmware never reports. The bench tests that meet it (`bench/test_network_resilience.py`'s
  outage and flap tests) recover by kick + `hard_reset()` through `recover_by_reset()` and pass,
  reported as recovery passes in the run's summary with the checks the reset skipped. Upstream:
  `micropython/micropython#9505` (open since v1.19.1), related `#9455`.
- **Lesson from a since-fixed test bug, worth keeping as standing practice**:
  `test_garbage_ssid_via_rest_config_is_handled_gracefully`'s own final "did the DUT reconnect"
  check spent many hours looking like unexplained hardware flakiness (escalating retry budgets,
  multiple `hard_reset()` retries, even a full physical power-cycle) before the real cause was
  found: the check read a `"Mode"` field from `GET /networking`, which never has that field
  (`"Mode"` exists only under `GET /status`'s nested `"networking"` object) — so it was
  unconditionally `False` regardless of how long the DUT had actually been reconnected. The DUT was
  reconnecting normally the whole time. **Before trusting an "it's flaky" signal from a
  real-hardware test enough to spend serious time chasing a hardware/firmware explanation, first
  re-verify the test's own check is asking the right question of the right endpoint/field** — a
  plain `curl` of both endpoints side by side would have caught this in under a minute.
- **SCD30's RDY pin is real and wired**: `SCD30_Reader`'s `irq_pin` constructor parameter (GPIO 8 in
  production), a real `irq_pin.irq(trigger=IRQ_RISING, ...)` in `start_timer()`, plus a staged
  500ms software self-healing fallback in `_irq_loop()` if the real IRQ is ever missed.
  `test_scd30_real_irq_edge_drives_a_real_read` (`device_scripts/scd30_real_irq_edge.py`) exercises
  it - its one genuine, disclosed limit: software alone can't fully distinguish a genuine hardware
  IRQ firing from the self-healing fallback firing instead; only a scope on the pin itself could.
- **`tests_hardware/manual/`'s files are deliberately named away from the `test_*.py` glob**
  (`manual_wifi.py`, not `test_wifi_manual.py`) - a bare `uv run pytest tests_hardware` (no path
  scoping) would otherwise collect and run them as ordinary pytest tests, each calling `input()`
  and hanging forever. `scripts/run_flash_hardware_suite.sh`/`run_bench_hardware_suite.sh` are
  scoped to avoid this either way, but the naming is the structural backstop.
- **Reusable real-hardware GC/fragmentation-instrumentation technique**: a temporary async probe
  task added to the boot entry (generated as `sensortask_<device>_main.py`, SPECIFICATION.md Part
  L.4, and staged as `main.py` by a build - add it to that staged `main.py` before flashing, and
  never commit the edit), printing a fixed-format
  line every N ms/every real event, captured via direct `pyserial` reads (`Board.tail_log()`, never
  `mpremote exec()` against a live system - that soft-resets it, wiping the very state being
  measured). Used for `gc.mem_free()` sampling + collection detection, real per-collection pause
  timing (bracket `gc.collect()` with `time.ticks_us()`), and real contiguous-allocation-frontier
  probing (attempt a real `bytearray()` at each of a descending candidate-size list, record the
  largest that succeeds - `gc.mem_free()` alone can't distinguish contiguous from scattered free
  space). Reuse this pattern for any future real-hardware memory/timing investigation rather than
  re-deriving it; SPECIFICATION.md Part I.1/I.3/I.5 has the results this technique already produced.
  The same technique applied to `UDPSocket.ready()` (a one-line `print()` on a real
  `POLLERR`/`POLLHUP` event) found that real rp2/lwIP does not propagate ICMP errors onto a
  connected UDP socket's poll state at all (BACKLOG.md open question 5) - zero such events observed
  across 6 real retry cycles against a target with no listener (the condition that generates a real
  ICMP Port Unreachable). The source agrees: lwIP's `icmp_input()` counts an incoming
  destination-unreachable and drops it (`lib/lwip/src/core/ipv4/icmp.c:258-283`, lwIP `77dcd25`),
  and a UDP socket's state stays `STATE_ACTIVE_UDP` (`extmod/modlwip.c:1008`, v1.29.0), which sets
  no error flag in modlwip's poll (`:1646-1666`).
- **Open on silicon, each with the instrument that settles it** (none has run yet):
  - what the CYW43 firmware drops while a flash write holds interrupts off -
    `bench/test_network_resilience.py::test_a_flash_write_holding_interrupts_off_keeps_the_wifi_link`;
  - whether DMA reads update UARTRSR's error flags as CPU reads do -
    `flash/test_uart_crossover.py::test_a_break_mid_frame_fails_that_transaction_only`;
  - whether the reset record survives a RUN-pin reset - `manual/manual_persistence.py::test_run_pin_reset_keeps_or_clears_the_record` -
    and the bootloader reboot - `bench/test_reset_reasons.py::test_a_bootloader_reboot_is_attributed`;
  - the SCD30's answer to a read with no command before it - `scd30_conformance_probe.py`'s
    `C03_read_before_a_command` - and after an NVM write cut by power loss -
    `manual/manual_persistence.py::test_power_loss_mid_scd30_nvm_write`;
  - the FRAM breakout's MISO idle level - `fram_conformance_probe.py`'s `A01_miso_idle_byte`;
  - the FRAM CS level at power-off - `manual/manual_bus_electrical.py::test_fram_cs_at_power_off`, with
    an oscilloscope only;
  - the seconds from a FRAM pull to its first FRAM log entry, and a pulled crossover jumper's first
    failed transfer, codes and recovery - `manual/manual_bus_electrical.py::test_fram_unplug_replug_recovery`
    and `::test_uart_crossover_pull_recovery`;
  - whether the SCD30's soft reset at every boot restarts its automatic self-calibration's
    first-week search, which no reading of the sensor's interface shows (no ASC progress readout).

## Third pass - closing real coverage gaps (found via a direct project-owner audit question)

Asked directly: "did you also add tests for the sensors and the on-board hardware itself and
standalone, up through the integration, and at the top level checking the API delivering sensible
values, including the VOC algorithm producing good results, FRAM backup working, FRAM error storage
working, website working... (all of which are tests of the twin, partially simulated, but now
running for real)?" Answer at the time, honestly: no - only SCD30 had any automated real-hardware
value check at all, and several real mechanisms (FRAM, the VOC algorithm, website-over-the-normal-
network, multi-sensor REST value sanity) had zero automated coverage. Confirmed by grep before
writing anything (`grep -rln "FRAMManager\|asy_fram" tests_hardware/` etc. all came back with
nothing but this README/manual-test references). Ten tests closed these gaps (44 -> 54):

- **BMP3xx/SGP40 standalone plausibility** (`flash/test_sensor_accuracy.py`, `device_scripts/
  bmp3xx_plausibility_read.py` / `sgp40_voc_algorithm_quality.py`): same isolated-driver-plus-
  datasheet-bounds shape as the pre-existing SCD30 test, now covering all three real sensors.
- **VOC algorithm quality** (same `sgp40_voc_algorithm_quality.py`): SGP40's raw signal and
  `voc_algorithm.py`'s Sensirion Gas Index Algorithm can't be exercised independently of each other
  (the driver always runs one straight into the other), so one script covers both - waits out the
  algorithm's own documented 45s initial blackout, then samples several real post-blackout readings
  and checks they're in range *and* neither frozen nor erratic. Deliberately a stability/sanity
  check, not a numerical-accuracy claim against a calibrated reference (that needs a human-supplied
  VOC stimulus - `manual/manual_sensor_accuracy.py` item 10).
- **SGP40 sample cadence** (`flash/test_sensor_accuracy.py::test_sgp40_sample_cadence`,
  `device_scripts/sgp40_sample_cadence.py`, L3, `soak_duration`: runs under
  `scripts/run_bench_soak_tests.sh --duration short`, its window fixed at 600 s whatever the
  duration): boots the bench device's generated system over the scratch config directory
  `hwtest-scratch/`, counts SGP40 read cycles over ten minutes of the real task graph and reports
  them as facts (cycles, elapsed, lost samples, the largest gap, the gaps over 1.5 s). No pass
  threshold: the figures are the deliverable (SPECIFICATION.md M.3). No flash cycle and no
  production config file; it writes the SGP40 backup chunk and the booted modules' logs into FRAM,
  which the session start saved first.
- **FRAM backup working** (`device_scripts/fram_manager_roundtrip.py`,
  `sgp40_fram_backup_restore.py`, `flash/test_fram_storage.py`): a real chunk write/read/CRC/dual-
  copy round trip against the physical MB85RS64V chip, plus the real SGP40 VOC-state backup/restore
  pathway specifically, driven through `SGP40_Reader`'s own real production `_read_loop()` (natural
  ~60s `BackupPeriod` schedule) rather than synthetic internal calls. A "fresh boot" is simulated by
  constructing a brand-new `FRAMManager` Python object against the same physical chip (allocator
  state is per-object, so this lands on the identical chunk address a real reboot's own fresh
  `build_system()` call would) rather than requiring an actual `hard_reset()` - the real chip's
  bytes are untouched by a plain object-level restart either way.
- **FRAM error storage working** (`device_scripts/fram_error_log_roundtrip.py`):
  `PrintLogHistoryStore` (every FRAM-chunk-owning module's own `err_s()`/`wrn_s()` persistence)
  against the real chip, same fresh-boot-simulation pattern as the backup/restore test above.
- **Website over the normal network** (`bench/test_rest_endpoints_over_sta.py`): the only prior
  `GET "/"` check anywhere in this tier was hotspot-mode-only, inside
  `test_hotspot_role_reversal.py`.
- **Top-level API delivering sensible values, across all three real sensors together, via REST**
  (same file): the pre-existing endpoint check
  (`test_end_to_end_timing.py::test_real_concurrent_client_burst_does_not_crash_the_webserver`) only
  ever checked HTTP status, never values.

A follow-up clarification then widened scope further, on the same audit thread: not just twin-
parity, but (1) bottom-level hardware *function* checks, not just readings, and (2) a real-hardware
counterpart for every mock-driven integration test in `tests/` "wherever possible". Two more
additions from that:

- **FRAM write protection actually gates a real write, a real read, and does so in silicon**
  (`device_scripts/fram_write_protect_roundtrip.py`, `flash/test_fram_storage.py`): sets the real
  WPEN|BP0|BP1 status-register bits, then checks three things - a write is rejected while
  protected and succeeds once cleared again (not just "can a chunk be written at all", which the
  roundtrip test above already covers); a *read* is rejected too, because `_read_chunk()` must
  write a transient busy marker first (intended behavior, SPECIFICATION.md Part A.4's FRAM entry,
  asserted identically at the mock and twin tiers); and - the part no fake can reach - the chip
  itself refuses, not merely the driver's own guard, proven by desyncing the cached `_wp` from the
  still-protected chip and sending a real WREN+WRITE whose bytes never land.
- **Real PUT /sensors config pushes** (`bench/test_sensor_config_push_over_real_hardware.py`): the
  real-hardware counterpart to `tests/test_setter_microdot_integration.py`'s mock-driven coverage.
  BMP3xx's oversampling/filter-coefficient fields are pushed to non-default values over a real REST
  call, confirmed `"Valid"` (proof the real I2C write succeeded), then read back via a second real
  REST call and restored to their original values in a `finally` block (this mutates the bench
  board's real persisted config). SGP40's `ResetVOC` command-only field is pushed the same way.
  SCD30 registers no `_push_callbacks`, but `PUT /sensors` reaches SCD30's NVM through its chip
  store (`_set_mgr_cfg()`, compare-before-write); a bench counterpart spends real NVM wear, so it is
  added behind `persistence_write` or its wear reason is listed.

A later flash-tier FRAM entry in the same `flash/test_fram_storage.py`:

- **FRAM command hold** (`device_scripts/fram_command_hold_timing.py`, flash tier): the command
  hold time stays under its bound - the longest non-yielding FRAM stretch under one UART poll floor
  (80 B of 8N1 at 115200 baud, 6,944 us, SPECIFICATION.md J.6 and F.5.8); the whole block hold is
  reported beside it. It writes only its scratch region at 0x3FF00, never a chunk.

**Still not automated even after this pass** (flagged honestly, not silently left implicit):
real-hardware numerical-accuracy validation against a calibrated reference for any sensor (needs a
human-supplied known-good stimulus - `manual/manual_sensor_accuracy.py` items 9/10, inherently
manual); WS2812/Neopixel notification-signal validation beyond the manual check (the timing is
`datasheets/ws2812/WS2812.pdf` p.4's; asserting it needs a logic analyzer, which the bench does not
have: no test hardware is bought, owner, 2026-09-22); a genuine power-loss test of the FRAM backup/restore or
error-log mechanisms specifically (only `manual/manual_persistence.py`'s raw-persistence power-loss
tests touch real power loss at all, and those don't drive `FRAMManager`'s own chunk logic).

## Fourth pass - real networking-robustness gaps against the API/website/internals

Asked directly: real WiFi outage, WiFi flapping, "WiFi available but no internet", NTP unresponsive
or slow, DHCP flaky/slow, connections at/above the real socket limit, nonsense GET/PUT requests,
and stale/broken-mid-transmission connections - "imagine more". A grep-first check
(`grep -rn "ap_down\|ap_up" tests_hardware/`, `grep -rln "malformed\|garbage\|nonsense"
tests_hardware/`, etc.) confirmed real gaps: `ap_down()`/`ap_up()` were only ever used *inside* the
hotspot role-reversal scenario's own internal join/leave mechanics, never as a standalone "the DUT
was already connected and the AP just disappeared" fault; the only "malformed request" test was
GET-only, hotspot-mode-only, and never checked the response was actually shaped correctly; nothing
checked the real `max_connections=4` ceiling under genuine concurrency (the pre-existing 8-client
burst test in `test_end_to_end_timing.py` never holds a connection open long enough to occupy more
than a couple of real slots); and BACKLOG.md's own open question #5 ("real-hardware verification
gap for `asy_udp_socket.py`/`asy_captive_dns.py`") was still open - every existing NTP/DNS fault test
only ever *dropped* traffic (`block_udp_ports()`), never fed the DUT a real garbage response. Eleven
tests closed these (54 -> 65, `bench/test_network_resilience.py` plus two new
`bench_control.BenchBridge` primitives and a shared `rogue_udp_responder.py` helper):

- **WiFi outage / flap while already connected**: grounded directly against
  `src/asy_wifi_service.py`'s `_on_sta_disconnected()` - once `_conn_phase` is
  `_PHASE_STA_ESTABLISHED` (which it necessarily already is, since these tests depend on `dut_ip`),
  a disconnect takes the "retrying previously successful connection in one minute" branch, which
  never increments `_connection_failures` and never reaches the hotspot-fallback path at all. This is
  a structurally *different, safer* branch than the one SPECIFICATION.md Part E.6.4's role-reversal
  scenario exercises (a never-yet-connected DUT) - confirmed by reading the real source before
  designing these tests, specifically to stay off that scenario's hotspot fallback. "WiFi available
  but no internet access" is treated as equivalent
  to "NTP/DNS unreachable" for this device: it has no other internet-dependent feature (no outbound
  fetch of remote content) to distinguish a general internet outage from an NTP/DNS-specific one -
  the pre-existing `test_real_ntp_handles_a_genuinely_unreachable_server_without_crashing` already
  covers the *unresponsive* case; deliberately not duplicated here.
- **NTP/DNS servers answering with real garbage** (`rogue_udp_responder.py`,
  `bench_control.py`'s new `redirect_udp_port_to_local()`/`clear_udp_port_redirect()`): a real `nat`
  table PREROUTING DNAT-to-loopback redirects the real port to a local rogue UDP responder that
  answers every query with a fixed non-protocol payload, closing BACKLOG.md's open question #5's
  "garbage response" half specifically (the *unresponsive* half was already covered). Whether the
  redirect delivers on this bench, and how each test proves it did: "What the network-fault
  injections reach".
- **Real socket-limit degradation** (`test_connections_at_and_above_the_real_socket_limit_degrade_cleanly`):
  grounded against `asy_webserver_service.py`'s own `_serve()` - `_open_conns` increments the instant
  a TCP connection is *accepted*, before any byte is read, which is what lets this test hold exactly
  the build's configured `max_connections` (6 on `dev`) real slots open with bare `connect()` calls
  and deterministically observe the next one being rejected (closed with zero bytes written, matching
  `_serve()`'s reject-when-full comment).
- **Nonsense GET/PUT over the normal network**: a genuine 404 (shaped per `_ERROR_STATUSES`), a
  genuinely malformed raw JSON body (needs a raw socket - `http_client.fetch()` can only ever
  serialize valid JSON), a real 413 over `max_content_length=2048`, and syntactically valid but
  nonsensical field values (wrong type, out-of-range, an entirely unknown sensor key) - each
  confirmed against `_body_as_dict()`/`asy_base_classes.py`'s `_set_dict_cfg()` to land exactly where the
  real source says it should, including confirming none of these paths ever reach
  `ConfigManager.write_config()` (so nothing needed restoring afterward, unlike the third pass's
  BMP3xx config-push test).
- **Slowloris-style partial requests and abrupt mid-response disconnects**: grounded against
  `_serve()`'s own outer `asyncio.wait_for(..., outer_cap_s)` (production default 15.0s, confirmed
  not overridden anywhere in `sensortask_wozi.py`) - the exact mechanism the code's own comment says
  bounds "a Slowloris-paced client no single per-call timeout alone would catch".

**Every hardware test that injects a fault also calls `assert_no_task_ended()`** before its
closing reset: a task ending under a routine fault (and the reboot three of those cost) lands in the
FRAM-kept SYSTEM log even across a `hard_reset()`, where a "no Traceback" check sees nothing - which
is how an NTP give-up restarting a task every minute passed this tier (SPECIFICATION.md C.7.2).
`tests_scripts/test_bench_no_task_ended_completeness.py` fails a fault test that skips it. Its scan
covers test functions and `Test*` methods, the helpers and fixtures a test reaches by name (a fixture
that injects counts unless it asserts in its own teardown), and the flash tier's fault-making device
scripts, which report their own SYSTEM logger as a fact for the host to assert; the session's
stale-credential recovery downs the AP only to join the DUT's hotspot and is not a fault.

**Standing policy from this pass on, applied everywhere it's practical**: reset the real, REST-
exposed error/warning history (`PUT /status {"ResetErrors": true}`) before a fault-injecting test,
confirm the *specific* expected `err_s()`/`wrn_s()` entry actually landed on the *right* module's
log afterward (not just "the system didn't crash"), then reset again so a real bench rig's live
error history is never left showing a test's own deliberately-provoked faults - `error_log_helpers.py`
(new shared module) is the reusable primitive for this, and its re-exported `code("E"|"W", NAME)`
(`tests/_error_codes.py`, read from `buildgen/error_catalog.json`) is how a test names the expected
entry. `/status`'s own `errcount` shape (`asy_webserver_service.py`'s
`_shape_errcount_entry()`: `{"counter": int, "history": [{"num": int,
"type": "E"|"W"}, ...]}`) is *not* the same shape as `asy_print_log.py`'s raw `get_log()` several
`device_scripts/` files already consume directly - confirmed directly before writing the helper,
not assumed from that other shape. Applied to every fault-injecting test in
`test_network_resilience.py`, the two `test_sensor_config_push_over_real_hardware.py` tests (confirming
a fully valid push-and-restore leaves nothing behind), and retrofitted onto the pre-existing
`test_real_ntp_handles_a_genuinely_unreachable_server_without_crashing` (`test_wifi_networking.py`).
One real design bug this same grounding pass caught in itself, fixed before this even shipped: the
first draft of the slowloris test asserted the wrong response shape and attributed it to the wrong
timeout mechanism - a single stall over 5s actually hits `_TimeoutStreamProxy`'s own *per-call*
read timeout, which Microdot itself silently absorbs and recovers from by writing an ordinary
response (confirmed directly against that class's own module comment), not the *outer* 15s
`outer_cap_s` backstop the test meant to exercise. Fixed with a genuine trickle-feed pace (one extra
header line every 3s, 6 of them - each individual gap safely under the 5s per-call timeout, the 18s
cumulative total safely over the 15s outer one) that actually reaches the outer path instead.
Not every fault has a groundable expected log entry: a 404 or 405 from `_shaped_error_handler()`
and the `_body_as_dict() is None` path call no `pr.err_s()`/`wrn_s()` at all (confirmed directly,
not assumed) - those tests assert the log stays *empty* instead, which is itself the real,
meaningful check for a benign/expected outcome. `_serve()`'s own drops do log: one
`HTTP_REFUSED` warning per connection refused at the ceiling and one `HTTP_BAD_HEAD` per refused
request head, each counted in `/status`'s `HTTPDropped`. One case (`test_abrupt_disconnect_
mid_response_does_not_hang_the_server`) has a real but genuinely timing-dependent expected log entry
(whether the server is still mid-write when the client's RST lands) - documented as a deliberate
non-assertion rather than a flaky one. This retrofit was **not** extended to the rest of the tier in
this pass.

**Partially closed later (2026-09-04, cloud-agent pass)**: `test_hotspot_role_reversal.py`'s
`test_malformed_truncated_packet_is_silently_dropped` and
`test_malformed_http_request_over_real_wireless_degrades_cleanly` now assert the module log stays
empty too (`DNSSRV`/`WEBSERVER` respectively - both grounded directly against source: a
garbage-but-present UDP datagram never reaches `asy_captive_dns.py`'s own `DNS_RECV_FAILED` (`W42`)
backoff branch, which only fires on a genuine `(None, None)` `recvfrom()` failure, and an
unparseable HTTP request line then failed entirely inside vendored `ext/microdot.py`). The
webserver's request-head guard now refuses such a line before Microdot parses it, answering 400
and logging one `HTTP_BAD_HEAD` warning: the malformed-request test allows exactly that warning,
asserts `HTTPDropped` counts the refused head, and fails when the server neither answers with a
400-class status line nor closes within its read timeout. **Real finding while doing this, since corrected (2026-09-08)**:
`test_dns_flood_leaves_captive_dns_serving_and_it_recovers` (then named for a backoff curve) had a comment claiming its flood
"triggers the backoff path" - checked directly against `asy_captive_dns.py`'s `run()` and that was not
what happens: `UDPSocket.recvfrom()` returns real `(data, addr)` for any received-but-garbage UDP
payload (UDP has no content validation), so the flood actually takes the *same* `pr.evt()`-only path
as the truncated-packet test above, never the `recv_fail_backoff_s`-growing branch the old comment
described. The test's own assertions (a legitimate query still answered promptly once the flood
stops) always held regardless, so this was never a false pass - only the comment's account of
*which* code path it was proving was wrong. **Resolved by correcting the comment in place**
(project-owner direction): it now describes the actual `pr.evt()`-only path the flood exercises and
notes that no fault in this codebase can currently force a real `(None, None)` `recvfrom()` failure
from a bench test, so the backoff-growth branch itself remains unexercised by any test in this
tier; it is covered at L1 instead (`tests/test_asy_captive_dns.py`'s backoff tests: an unbound
socket logs `INIT`, a failed receive `DNS_RECV_FAILED`, each backing off).

The rest of the tier - `test_hotspot_role_reversal.py`'s remaining fault tests (association/DHCP
churn, which are bench-radio-observable only and have no DUT-side `src/` module to log against, so
this policy doesn't apply to them) - stays outside this policy's scope for the reason already
given, not silently left looking finished. The flash-tier timer-exhaustion/scheduler-saturation
device scripts (`timer_alarm_pool_exhaustion.py`/`scheduler_saturation_drop.py`) were re-checked too
and turned out **not** to need this retrofit at all: flash tier has no REST server reachable at all
(USB/serial only, no network), both scripts already assert the *specific* expected outcome via
their own `RESULT: PASS/FAIL` line (exact `errno`, per-timer self-heal proof) rather than "didn't
crash," and neither invokes any `src/` driver module that could log to `errcount` in the first
place (bare `machine.Timer` only) - so there is no comparable gap there to close. The original note
above overstated this; corrected here rather than left stale.

## Fifth pass - FRAM fault-injection: CS hijack and hard-reset race

Partially closes the "still not automated" gap noted in the Third pass above (a genuine power-loss
test of FRAM backup/restore) - not full power loss, but two real, reachable fault shapes during an
in-flight FRAM write:

- **FRAM CS-pin hijack** (`device_scripts/fram_cs_hijack_fault_injection_and_recovery.py`): races a
  software CS deassertion against an in-flight SPI write/read. `SPIDevice.write()`/`readinto()` have
  no internal yield point (synchronous `machine.SPI` calls), so the only reachable race window is
  `SPIDevice.__aenter__()`'s `await asyncio.sleep(0.001)` - CS already asserted, opcode not yet
  clocked out. Confirmed empirically (2026-09-04, this bench unit): 5/5 trials of both scenarios
  landed identically (a deterministic scheduling-order race, not timing luck). Write hijack: the
  write never reaches the chip (real memory shows the untouched original). Read hijack: the buffer
  comes back all zero bytes (MISO's real electrical state while SO is high-Z during deselect), never
  the real seeded pattern, never an exception. Both scenarios end with `verify_present()` succeeding
  and a fresh write+read round trip working normally - the chip's SPI protocol state machine is
  never left wedged by a CS-based interruption.
- **FRAM hard-reset race during write** (`device_scripts/fram_reset_race_during_write_seed_and_race.py`
  + `..._verify_recovery.py`): races a genuine `machine.reset()` against an in-flight FRAM write, at
  the same yield-point technique as the CS-hijack script above. A real reset is a genuinely different
  fault than a CS deselect: the FRAM chip has no idea the RP2040 rebooted, so the WEL write-enable
  latch (already SET by the prior WREN handshake) is left exactly as it was, not cleanly unwound.
  Because `SPIDevice.write()`/`readinto()` have no internal yield point, this cannot prove a
  genuinely torn (partially-written) transfer - only that a reset landing right as a write session
  begins leaves the target region untouched and the driver/chip fully recoverable, including that the
  stray SET WEL causes no problem for the very next real write. A true mid-byte-transfer power loss
  is architecturally unreachable via any interpreter-level race (same class of limitation as the
  wedged-bus case in SPECIFICATION.md Part F.2) - only a real external power cycle or an
  out-of-process host-triggered interrupt could reach that point; this is the honest, safely-buildable
  scope, not the exhaustive one.

**Isolated-driver device-script cfgmgr priming pattern**: any device script that constructs a
`*_Reader` directly (not via `sensortask_*.build_system()`) must prime `reader.cfgmgr.valid = True`
and `reader.cfgmgr._cache = {...}` with the driver's own schema defaults before starting read/trigger
tasks. Without it, `cfgmgr.valid` stays `False`, the reader's first config read returns `None`, and
the read loop fails silently (visible only at `debug=5`, e.g. "Error reading config data!") without
ever attempting a real sensor read. Found independently in `bmp3xx_plausibility_read.py` and
`sgp40_fram_backup_restore.py`. Never call `cfgmgr.setup()` in such scripts - that performs a real
littlefs file write/read.

## Sixth pass - the `dut_ip()` fixture's retry/recovery methodology, and other bench-harness findings

`conftest.py`'s session-scoped `dut_ip()` fixture gates nearly every bench test, so its retry logic
carries more real-hardware findings than any other piece of harness code in this tier - recorded
here in full since the code comment that used to carry them had to shrink to a pointer:

1. Early WiFi reconnection flakiness on this bench unit was undiagnosed; a single bad boot used to
   fail this session-scoped fixture outright, cascading into every other bench test. Fixed with one
   bounded `hard_reset()` retry.
2. A real STA IP does not mean the webserver is serving: the generated `main()` starts the WiFi
   connect loop and the webserver as separate tasks of one staggered starter list
   (`start_tasks()`), so the link can come up before port 80 answers - up to ~20s back when the
   first NTP sync still held the boot ahead of every task. Fixed by waiting for real HTTP
   reachability, not just link connectivity.
3. Polling for an IP via `board.exec()` in a loop is self-defeating: `mpremote`'s raw-REPL entry
   always performs an implicit `machine.soft_reset()` (confirmed against `transport_serial.py`'s
   `enter_raw_repl(soft_reset=True)`), which tears down the whole running Python VM/heap per
   MicroPython's `ports/rp2/main.c`, killing whatever WiFi reconnection attempt was in progress on
   every single poll.
4. A single (not looped) `board.exec()` call is *also* unsafe: entering raw REPL sets
   `pyexec_mode_kind` to `RAW_REPL`; the soft-reset boot path in `ports/rp2/main.c` only re-runs
   `main.py` when that's `FRIENDLY_REPL`. A trailing `soft-reset` command returns to an idle
   friendly-REPL *prompt* only - it does not retroactively make the already-completed soft-reset's
   boot sequence recheck that condition, so `main.py` stays stopped regardless. Confirmed via an A/B
   test: `exec` alone, `exec ... soft-reset`, and `run <script> soft-reset` all left the board
   silent (no `main.py` output) afterward. Only a genuine `hard_reset()` (real `machine.reset()`)
   reliably resumes normal auto-boot, since the RP2040 restarts from its own reset vector where
   `pyexec_mode_kind` starts fresh at its compiled-in `FRIENDLY_REPL` default.
5. **Dominant root cause, found via a real-hardware A/B test**: the WiFi reconnection flakiness is
   overwhelmingly a stale AP-side station-table entry - the bench AP backend (NetworkManager's
   internal `wpa_supplicant`, confirmed not a separate `hostapd` process) still lists the DUT's MAC
   as associated from before a `hard_reset()` (a real power-cycle, no clean 802.11 deauth frame
   sent), and a fresh association attempt racing against that stale entry doesn't reliably get
   treated as a clean new session. **10/10 trials fell back to hotspot mode with the stale entry
   left in place; 10/10 trials connected cleanly once `kick_all_stations()` cleared it immediately
   before each `hard_reset()`.** Not a `src/` bug - `asy_wifi_service.py`'s own retry/hotspot-fallback
   logic is textbook-correct given what the CYW43 firmware reports; the AP's own stale bookkeeping
   is what was wrong, and only this bench-host-side harness can see or fix it. Caveat: a device
   WDT-looping in the field would hit the same stale-entry pattern against a real router with no
   bench harness able to `kick_client()` on its behalf - this fix makes bench testing representative
   of a *clean* reconnect, not proof the field scenario is risk-free.
6. Neither retry above helps if the real cause is stale stored WiFi credentials (e.g. the bridge was
   just recreated with a fresh random SSID/password) - the DUT organically falls back to its own
   hotspot every time. Fixed by `_recover_stale_dut_credentials()`: joins the DUT's own hotspot
   fallback as a client, PUTs the bench AP's real current SSID/password to it (read via
   `BenchBridge.ap_password()`'s `--show-secrets` nmcli query), then restores the bridge - reusing
   the exact mechanism `test_hotspot_role_reversal.py`'s own stage 6 exercises by hand.

The fixture's current implementation: watches passively via `board.tail_log()` for
`asy_wifi_service.py`'s `pr.one("WLAN connection established")` line (printed at `DebugLevel` >= 3);
the hotspot fallback's "Permanently no WLAN connection - activating hotspot!" is a `wrn_s()` warning
(printed at level 2), which the fixture does not watch. Reading the actual IP still needs one
`board.exec()` call (unavoidable), always immediately followed by `board.hard_reset()`.

**`bench_control.py`'s `redirect_udp_port_to_local()` - a DNAT-to-loopback local-delivery gap**: the
observation, and the delivery check every garbage test now makes, are in "What the network-fault
injections reach".

**`bench_control.py`'s `is_ssid_visible()`/`join_dut_hotspot()` real-hardware timing**: `is_ssid_visible()`
being True one moment doesn't guarantee `nmcli device wifi connect`'s own internal (re)scan still
sees it a moment later - an isolated repro (2026-09-08) showed this can persist across several
consecutive attempts, not just one. `_join_dut_hotspot_with_reverify_retry()`'s reverify window is
30s/2s (widened from an original 15s/1s that let a `TimeoutError` escape uncaught, crashing the
retry loop on attempt 1 instead of exhausting all attempts) and catches `TimeoutError` alongside
`HardwareTestFailureError`. A repro with both fixes in place once exhausted 3 attempts; its cause is
still open, and the next hardware round investigates it. The join keeps its five attempts
(`l4.hotspot_role_reversal_join_attempts`) on that nmcli race, each retry a recovery note (owner,
2026-10-20: 'The Hotspot remains untouched.'). An AP-reconfiguration theory recorded the same day was
ruled out against the pinned source: an AP that is up reports `STAT_GOT_IP`, so `_run_hotspot_mode()`
only manages its stations, and `_configure_hotspot_ap()` configures only an inactive AP.

**The manual-test runner's duplicate-module-instance bug**: running `python3
tests_hardware/manual/runner.py` directly makes Python load that file as the `__main__` module,
while every `test_*.py`'s `from runner import register, ...` imports a *separate* module instance
literally named `runner` (found on `sys.path`) - two distinct module objects, each with its own
separate `_REGISTRY` list. Decorators in the test files populate the `runner`-named instance's
registry; `main()` running as `__main__` reads its own, different, permanently-empty one. Result: a
silent no-op - exit 0, zero output, `--list` showing nothing, no exception anywhere to point at the
cause. Confirmed directly by tracing both module instances' `id()`/`_REGISTRY` in a running
interpreter. Fixed by `__main__.py`: always imports `runner.py` as a plain module, never running it
as `__main__` itself - run `uv run python tests_hardware/manual/__main__.py`, never `runner.py`
directly.

**Manual-test conventions** (`tests_hardware/manual/runner.py`'s helper functions):
`print_instruction()` before the window that depends on it, not after. Timing is human-executable on
a breadboard test device (tens of seconds, chosen per what's physically involved), never a value
carried over from an automated/simulated test. `confirm()` waits for explicit human confirmation
wherever the console survives the step; `countdown()` is reserved for genuine power-cycle cases
where it doesn't. `state_expected_outcome()` prints what "passed" should look like before the
script's own verdict, for tests that end in a human visual/instrument check rather than a
script-only assertion.

## Seventh pass - cross-occupant write-vs-siblings real-hardware coverage (mock-tier gap closure)

`tests/_bus_hazard_catalog.py`'s generic mock-tier scenario
(`scenario_a_write_does_not_disturb_concurrent_sibling_reads`) surfaced a real gap once its own
"same test bar as `src/`" audit was extended to the real-hardware tier: no existing flash-tier test
proved a config WRITE from one dev/i2c1 occupant landing concurrently with its SIBLINGS' own reads -
only same-device write-vs-own-read (`bus_concurrency_same_device_scd30.py`,
`isl29125_same_device_rw_concurrency.py`) and the SGP40 general-call broadcast case
(`sgp40_general_call_reset_hazard.py`, SCD30 sibling only, not ISL29125). Two new tests close this:

- **`test_isl29125_config_write_does_not_disturb_concurrent_sibling_reads`**
  (`device_scripts/bus_concurrency_isl29125_write_vs_siblings.py`) - ISL29125's own `configure()` is
  the writer (a volatile config register, no NVM-write-budget concern per FN8424 p7), repeated
  `WRITE_CYCLES=8` times over a real multi-second window with SCD30 and SGP40 both reading
  concurrently. Part of the routine group, no opt-in needed.
- **`test_scd30_config_write_does_not_disturb_concurrent_sibling_reads`**
  (`device_scripts/bus_concurrency_scd30_write_vs_siblings.py`) - the SCD30-as-writer half of the
  same gap. SCD30's own `set_temperature_offset()` is a real NVM write, so this is deliberately
  **not** part of the routine group: gated behind `@pytest.mark.persistence_write` +
  `@pytest.mark.scd30_extra_write`, which need `--allow-persistence-write` and
  `--allow-scd30-extra-write` together ("Persistence-write gating" below), it spends two NVM writes
  (the offset and its restore) per invocation, never folded into the routine group's at most one
  (`scd30_measuring`'s start command; SPECIFICATION.md Part C.8's write-budget rule).

**Honesty note - neither test has been run against real hardware yet.** Both were written and typed
during a session with no real-hardware go-ahead (CLAUDE.md's own standing gate) and no ability to
verify against the real bench Pi4/dev board - they pass `ruff`/`mypy` and follow the same structural
conventions as every proven-on-hardware script in this directory (window-overlap interleaving proof,
`RESULT: PASS/FAIL` line, `wdt.feed()` cadence, plausibility bounds), but that is not the same as a
real run. Treat both as a first cut to be smoke-tested (and fixed if wrong) on the next real-hardware
session, not as already-confirmed coverage - flagged here explicitly rather than left to look
finished.

## Eighth pass - full mock/twin-to-real-hardware scenario parity for dev's own topology, and flash-tier/bench-tier parity

Follow-up direction (project owner): every generic mock/twin bus-hazard scenario type must have a
real-hardware equivalent for whichever bus dev's own real wiring makes it applicable to (SCD30 stays
under its write-budget restriction), and whatever gets added to the flash tier must also get a
bench-tier counterpart - flash-tier bus-hazard coverage is always a subset of bench-tier coverage,
never the other half.

**The mock tier's timing-offset sweep, made explicit on real hardware, not just implicit in natural
jitter**: the Seventh pass's own two new scripts originally relied on a fixed write cadence (ISL29125)
or natural scheduling jitter alone to vary timing. `bus_concurrency_isl29125_write_vs_siblings.py` now
cycles through a deliberately varied, explicit set of pre-write delays
(`_WRITE_DELAYS_MS = (5, 15, 40, 80, 120)`, each exercised twice) instead of one fixed 30ms cadence -
a designed spread of relative timings against the siblings' own read loops, not merely hoping
uncontrolled jitter happens to cover a range. `bus_concurrency_scd30_write_vs_siblings.py` still fires
at exactly ONE fixed offset (0.3s in) - the one-write budget makes a real multi-offset sweep
structurally impossible there, not a design choice to skip it; its own docstring now says so
explicitly rather than silently reading like an oversight. Real hardware still has no literal
equivalent of the mock tier's `asyncio.sleep(0)`-count offset (a yield count means nothing against a
real preemptible interpreter and real bus timing) - a real elapsed-time delay is the honest,
tier-appropriate substitute.

**Two real gaps closed in dev's own general-call/address-sweep coverage**, found by checking every
mock-tier generic scenario type against what real hardware actually covers for dev's real topology
(i2c0: BMP3xx alone; i2c1: SCD30+SGP40+ISL29125):

- `sgp40_general_call_reset_hazard.py` used to run its concurrent-sibling check against SCD30 only,
  even though ISL29125 is also a real, non-broadcasting sibling on the same bus (mirroring
  `tests/_bus_hazard_catalog.py`'s own `scenario_general_call_does_not_disturb_concurrent_siblings`,
  which runs against every non-broadcasting occupant, not just one). Now reads both concurrently
  while SGP40's own `initialize()` fires its real general-call broadcast; the flash-tier test this
  wraps was renamed to `test_sgp40_general_call_reset_does_not_corrupt_concurrent_scd30_and_isl29125_
  transactions` to say so.
- `bus_topology_autodetect_and_hazard_sweep.py`'s own `KNOWN_ADDRESSES` table had drifted out of
  sync with the since-deleted `tests_hardware/bus_topology.py`'s own copy (that file's module
  docstring stated the invariant; nothing enforced it, which is why it drifted) - it was missing ISL29125 (`0x44`) entirely, so the address sweep never probed/labeled
  it and the lone-device self-hazard branch could never apply to it. Fixed: `ISL29125_I2C` support
  added to both the address table and the self-hazard construction/read branch.
  - Everything else in the mock tier's generic scenario set already had a real-hardware equivalent
    for dev's own topology once this pass checked systematically: same-occupant write-vs-own-read
    (per-driver same-device scripts, all three occupants), all-occupants-concurrent-reads
    (`isl29125_cross_device_concurrency.py` already runs all three of i2c1's occupants at once), and
    the "rogue general call against a lone occupant with no real broadcaster" case (i2c0's own
    BMP3xx-alone bus) - the topology script's own self-hazard branch already covered this before this
    pass, for whichever known device turns out to be the bus's sole occupant.

**Flash-tier -> bench-tier parity**: added
`test_isl29125_config_write_does_not_disturb_concurrent_sibling_reads_under_api_load`
(`tests_hardware/bench/test_bus_concurrency_under_api_load.py`) - the same ISL29125-writes-while-
siblings-read hazard as the flash-tier test above, driven through the real HTTP/REST stack instead of
the bare driver (`PUT /sensors {"ISL29125": {"Resolution": ...}}` alternating between both real valid
settings, concurrent with `GET /sensors` hammering, with the board's original `Resolution` restored
in a `finally` block - the same push/restore duty `test_sensor_config_push_over_real_hardware.py`'s
own BMP3xx test already owes for a shared bench rig).

**SCD30's write-vs-siblings hazard has its bench-tier counterpart**: `PUT /sensors` reaches
SCD30's NVM through its chip store (`_set_mgr_cfg()`, compare-before-write), so
`bench/test_bus_concurrency_under_api_load.py`'s
`test_scd30_config_write_does_not_disturb_concurrent_sibling_reads_under_api_load` spends real NVM
wear (two offsets and the restore) and runs behind `persistence_write` and `scd30_extra_write`,
beside the flash tier's `bus_concurrency_scd30_write_vs_siblings.py` behind the same two flags.

Same honesty note as the Seventh pass: none of this pass's changes have been run against real
hardware either (no go-ahead at the time) - `ruff`/`mypy` clean, structurally consistent with
proven scripts, but unverified on silicon until a real bench session confirms it.

## Ninth pass - auditing the flash-tier/bench-tier bus-hazard pairing itself, and a real miscoverage found

Direct follow-up question: does *every* pre-existing flash-tier bus-hazard test (not just the ones
earlier passes added) actually have a bench-tier counterpart? Checking systematically found one
genuine, surprising miscoverage plus two closeable gaps:

- **SGP40's general-call hazard has ZERO real bench-tier coverage, despite `test_bus_concurrency_
  under_api_load.py` appearing to exercise it.** Every one of that file's four tests already runs a
  `sgp40_reset_trigger_worker()` PUTting `ResetVOC` concurrently with GET load - reasonable to
  assume, from the name and the pattern, that this re-triggers the same general-call broadcast the
  flash tier's `sgp40_general_call_reset_hazard.py` proves survives concurrent reads. **It does not.**
  Read the real call chain directly: `reset_voc()` only sets a flag consumed by the next
  `measure_index_and_raw(reset=True)` call, which calls `vocalgorithm_reset()` - a software-only VOC
  algorithm reset. The real broadcast only ever fires from `SGP40_I2C._reset()`, itself only called
  from `initialize()`, itself only ever invoked internally at driver setup/task-supervisor restart -
  never through any `_push_callbacks`/REST field. There is currently no way to force this hazard on a
  live, already-running system via REST at all - a bench test would need a real reboot mid-load,
  which would confound the very load being measured. Listed as SPECIFICATION.md E.6.6 row
  `sgp40-general-call` (and in `test_bus_concurrency_under_api_load.py`'s module docstring) rather
  than left implied by the superficially-similar-looking worker.
- **SGP40 was never schema-sanity-checked in any bench GET worker at all** - `_schema_sanity_findings()`
  checked SCD30/BMP3xx/ISL29125's own config fields but no SGP40 field, so a torn/corrupted VOC
  reading under bench load would have gone completely undetected. Closed: checks `SGP40.VOC` against
  the same `[0, 500]` bounds `sgp40_voc_algorithm_quality.py` already uses.
- **BMP3xx's same-device write-vs-own-read had no bench-tier counterpart**, even though (unlike
  SCD30) BMP3xx has real REST-pushable fields already exercised elsewhere
  (`test_sensor_config_push_over_real_hardware.py`). Closed:
  `test_bmp3xx_config_write_does_not_disturb_its_own_concurrent_reads_under_api_load` - alternates
  `PresOvers` between both real valid settings concurrently with this same sensor's own GET reads,
  restoring the original value afterward.
- **SCD30's own same-device write-vs-own-read** has no bench-tier counterpart yet either, for the
  same reason as its write-vs-siblings hazard: `PUT /sensors` reaches SCD30's NVM through its chip
  store, so a bench counterpart spends real NVM wear and is added behind `persistence_write` or its
  wear reason is listed.

Same honesty note again: the two new/closed items above are `ruff`/`mypy`-clean but unverified
against real silicon when written.

## Tenth pass - full test-suite sweep for tier/layering completeness and wrongly-trusted tests, beyond bus-hazard (owner, 2026-09-15; important to apply, no ordering — owner, 2026-09-29: 'It has no priority in terms of order now, it's only highly important to be applied.')

Direct follow-up to the Ninth pass's own SGP40 miscoverage: is that failure mode (a test whose
name/pattern matches a hazard but whose real call chain doesn't reach it) present anywhere else in
the suite, and does E.6.6/E.6.1's tier-parity requirement hold outside the bus-hazard domain? Swept
UART, WiFi/network/NTP/DNS, FRAM/memory/reboot/watchdog, and webserver/notification/config-push -
each domain's own real call chains traced against the test files that claim to exercise them, not
grepped for coverage. No second instance of the exact SGP40 bug (a real hardware trigger silently
substituted with a software-only one) turned up, but several real tier-parity gaps did.

**Fixed this pass:**

- **`isl29125_plausibility_read.py` was a real, working, silicon-ready device script with no pytest
  wrapper at all** - written during the ISL29125 promotion (PR #83) but never wired into
  `test_sensor_accuracy.py`, so it never actually ran as part of this suite. Closed:
  `test_isl29125_real_reading_is_within_datasheet_plausible_bounds`.
- **ISL29125's entire real REST config-push surface had zero bench-tier coverage** - ISL29125
  has four hardware-backed, read-back-able fields (`Resolution`/`Range`/`IRCompOffset`/
  `IRCompAdjust`) with no exclusion comment, suggesting oversight rather than a decision. Closed:
  `test_isl29125_resolution_range_and_ir_comp_push_over_real_rest_and_readback` in
  `test_sensor_config_push_over_real_hardware.py` - also pushes `RangeAuto: False` alongside `Range`,
  since under real auto-ranging (the driver's own default) the chip's own range bit is the state
  machine's choice, not the user's setting, and `_read_sensor_dict()` omits `Range` from a live
  snapshot entirely rather than misreport it (`asy_isl29125_driver.py`'s own comment) - a real
  readback of a pushed `Range` needs auto-ranging off first.
- **FRAM's write-protect gate (`get_write_protected()`/`set_write_protected()`) had real flash-tier
  coverage with its own bench-vs-flash split never written down anywhere**, unlike storage-pause
  gating's own explicitly-documented split. Confirmed structural (E.6.6 row `fram-write-protect-no-rest`:
  neither method has a REST route at all, by grep) and now stated as such directly in `test_fram_storage.py`.
- **`SystemService.supervise_tasks()`'s own real restart-a-dead-task mechanism (over the tasks
  `start_tasks()` started) had no real-hardware test at all** - the exact recovery rung CLAUDE.md's
  memory-safety-discipline rule leans on ("trust `asy_system_service.py`'s task supervisor to
  restart a task that still dies"), proven only at the mock/twin tiers. New:
  `device_scripts/system_service_restarts_a_real_dead_task.py` +
  `tests_hardware/flash/test_task_supervisor.py`'s
  `test_the_supervisor_restarts_a_real_dead_task` - a starter that dies immediately, checked
  called at least twice within one real `_TASK_CHECK_TIME` (2s) cycle. Deliberately stops at ~3.6s
  real time (task_errors capped at 200): a task that dies immediately adds `_TASK_FAIL_INCREMENT`
  (100) per cycle, and `_TASK_FAIL_MAX` (300) would otherwise trip a real reboot around the 4th
  cycle (~7s) - not what this script is testing.
- **`PUT /notification`'s `PauseTime` field was initially misjudged as an unfixable structural
  exception during this pass (no GET /notification field reads it back) - wrong**: buildgen's own
  generated `_notification_status()` puts a live `PauseTime` (`await notification.get_override_led()`)
  into `GET /status`'s own `"notification"` section on every real device, the same real signal
  `tests/test_digital_twin_sensortask_integration.py`'s own
  `test_put_pause_time_round_trips_and_counts_down_over_real_http` already reads. Closed (once
  found, not left as the wrong "exception"):
  `test_notification_pause_time_push_counts_down_over_real_rest` in
  `test_sensor_config_push_over_real_hardware.py` - proves the pushed pause counts down to 0 on
  real hardware, not just that the PUT stuck.

**Exceptions this pass confirmed** are rows of SPECIFICATION.md E.6.6: `ws2812-no-readback`
(`LightCmdLED` and the WS2812 timing) and `scd30-rdy-irq-vs-fallback` (the SCD30 IRQ-pin edge).

**Named, not fixed this pass** (real, credible findings from the domain sweeps below, each requiring
either a dedicated real-hardware session to get right or a project-owner decision this pass
shouldn't make unilaterally - disclosed rather than silently dropped, per BACKLOG.md's own
"resolved or migrated, never silently dropped" rule):

- **UART's sharpest invariant (`asy_uart_driver.py`/`asy_uart_comm.py` may never block the loop -
  CLAUDE.md)**: its silicon proof of F.5.8 is `uart_driver_read_never_blocks_the_loop.py` (flash
  tier), which times the shipped driver's own UART calls.
- **The bench tier carries a multi-chunk SET under serving load** (`uart_link_echo_under_serving_load.py`
  driving the initiator's public `uart_set()`), with no `src/` change.
- **The UART fault catalog** (~20 scenarios: corruption, drop, truncate, duplicate, overrun, lost
  final ACK, peer reset mid-transaction, ...) is mock-only, a listed structural exception: no
  injection hardware will be bought (owner, 2026-09-22), and a second raw UART is not used as a
  stand-in (owner, 2026-09-22). On silicon the flash tier covers silence and a baud mismatch
  (`uart_crossover_recovery.py`), and `device_scripts/uart_comm_hazards.py` covers concurrency and
  field sweeps.
- **NOTIFY's own FRAM chunk has no hard-reset-recovery bench test**, unlike SGP40's
  (`test_real_hard_resets_during_natural_fram_backup_activity_recover_cleanly`). Extending that
  ~5-minute, 3-real-hard-reset test to a second FRAM-backed module needs first identifying NOTIFY's
  own equivalent of `BackupTS` (an observable "a fresh write just completed" signal), which does not
  exist. **Scratched (owner, 2026-09-25)**: adding one would change `src/` for the test alone, and
  the flash tier already proves a FRAM chunk's reset-raced write is all-or-nothing.

**Confirmed clean, no fixes needed** (traced end-to-end, not just grep-counted): WiFi's real bench
worker call chains (`ap_down`/`ap_up`, UDP block/redirect, `netem` fault injection, hotspot
role-reversal, spoofed-NTP-source) all genuinely reach the real mechanism their names claim; the
wedged-WiFi `isconnected()` backstop has real, automated bench coverage with real timing data
(`test_network_resilience.py`), not just a one-off manual finding; UART's flash-tier fault-injection
and idle-poll-rate scripts, and mock/twin/flash parity for the core happy-path and one-sided-silence
scenarios, are all genuine; BMP3xx/SGP40's REST config-push is proven end-to-end via real
GET-after-PUT readback; the bench mempause test and the flash/bench memory-stress split are both
honestly and correctly scoped, not wrongly-trusted; SGP40's `ResetVOC` push is a thin test (it
never asserts the reset's own effect) but says so in its own comment - not a new instance of the
Ninth pass's bug, just worth naming.

## Persistence-write gating: one global flag plus an AND-gated extra flag

**Standing design (owner, 2026-09-16, `98dc1b2`/`4f1c802`)** (broadened from SCD30-only to all
persistence, 2026-09-17): every write to a **limited-endurance** store that a test owns runs only
behind a flag. The stores are the SCD30's on-chip NVM and the RP2040's flash filesystem, which every
accepted config-persisting `PUT` writes through `asy_config_manager.py`; FRAM is not wear (owner,
2026-09-26: 'FRAM writes do not count as wear.').

**The gates** (`tests_hardware/markers.py` is the one marker table; each flag is `--allow-<marker>`,
or `--soak-duration` for the one valued gate):

| marker | flag | gate | what it spends |
|---|---|---|---|
| `persistence_write` | `--allow-persistence-write` | deselected at collection | the owned flash-filesystem and SCD30 NVM writes of the budget table below |
| `scd30_extra_write` | `--allow-scd30-extra-write`, only together with `--allow-persistence-write` | deselected at collection | the further SCD30 NVM writes the budget table lists under it; always carried with `persistence_write` |
| `flash_cycle` | `--allow-flash-cycle` | skipped by the test | one or more reflashes (the flash-cycle rows below) |
| `soak_duration` | `--soak-duration {short,mid,long}` | skipped by the test | time only |
| `multi_day_rollover` | `--allow-multi-day-rollover` | skipped by the test | about 2 h on the tick-offset test image; no write of its own |
| `neopixel_sweep` | `--allow-neopixel-sweep` | skipped by the test | about 10 min of light programs on the NeoPixel rig; its config pushes need `--allow-persistence-write` |
| `toolchain_reverify` | `--allow-toolchain-reverify` | skipped by the test | network fetches and about 8 min of builds; no board write |

`destructive_last`, `role_reversal` and `over_provisioned_image` are informational. The two wear
gates deselect rather than skip, which is why the verdict names the deselected count ("Read the
deselections in the verdict" below).

**What the gate is about: the write a test OWNS, not one it is reached through** (owner,
2026-09-18). A persisting write that *is* the thing under test is optional and belongs behind the
marker. A persisting write that is a **prerequisite** several other tests are reached through stays
unmarked and allowed: gating it would deselect the tests it exists to enable, and those tests are
not what spends the wear. So the choice the flag offers is "test everything and accept the higher
write wear" versus "test everything that matters and keep wear as low as it can go" - never "spend
zero". A `PUT` whose every field is rejected, unknown, unchanged or dispatch-only writes nothing
and needs no marker (`write_config()` stages nothing then); a field the definitions flag
`alwaysExecuted` always writes, and the `resetconfig` command is persisting (it deletes every config
file). Dispatch-only fields are the ones whose `@web` tag carries `dispatch=true`, read from the
generated definitions, never from a list here.

**The budget**, per run (a "scratch" file is a `config_HWTEST_*` file or the `hwtest-scratch/`
directory, removed on every path; a store's absent file gets one defaults write on its first
`setup()`, counted as a prerequisite):

| run | store | writes |
|---|---|---|
| default | flash filesystem | prerequisites only: `joined_hotspot`'s SSID clear and its restore (2, on a run reaching the role-reversal module); `_recover_stale_dut_credentials()`'s SSID/PW push (0-1, only when the DUT cannot rejoin the bench AP); `--repair-standard-state`'s repairs (0 or more, each read back); an aborted run's leftover removed (0-1); per run of a device script that builds the system, one defaults write per config store into `hwtest-scratch/` and that directory's removal |
| default | SCD30 NVM | 0, at most 1: `scd30_measuring`'s start command, only when no measurement arrives within three intervals, at most once per session |
| `--allow-persistence-write`, flash tier | SCD30 NVM | `test_scd30_same_device_read_write_concurrency`: 1 (the ambient pressure the chip already holds, re-sent) |
| `--allow-persistence-write`, flash tier | flash filesystem | `test_config_floats_round_trip_unchanged`: 1 scratch write (its repeat answers `Unchanged`); `test_isl29125_mechanism_envelope_holds_across_range_resolution_and_calibration`: 7 scratch writes (also needs `--allow-neopixel-sweep`); `test_a_real_config_write_during_traffic_loses_no_frame`: 1 scratch flush per CRC mode (2 modes); `test_link_transactions_during_config_writes_are_recorded`: 5 scratch writes per CRC mode; `test_config_value_survives_a_genuine_hard_reset`: 2 (the scratch file's defaults, then the marker); `test_config_reset_deletes_every_config_file_and_reboots`: the scratch build's defaults per store, one damaged file, `resetconfig`'s deletions; `test_a_hung_shutdown_step_ends_in_a_watchdog_reset`: per command, the scratch build's defaults per store and the deletions until the hung step |
| `--allow-persistence-write`, bench tier | flash filesystem | 2 each (the change and its restore): `test_isl29125_gain_ratio_survives_a_real_reboot_as_an_ordinary_config_value`, `test_representative_put_round_trips_over_the_hotspot_link`, `test_real_hard_resets_during_natural_fram_backup_activity_recover_cleanly`, `test_garbage_ntp_host_via_rest_config_degrades_and_recovers_cleanly`, `test_garbage_ssid_via_rest_config_is_handled_gracefully`, `test_console_output_with_a_non_reading_usb_host_never_starves_the_watchdog` (`DebugLevel` 0, then 5), `test_a_flash_write_holding_interrupts_off_keeps_the_wifi_link`, `test_bmp3xx_oversampling_and_filter_push_over_real_rest_and_readback`, `test_isl29125_resolution_range_and_ir_comp_push_over_real_rest_and_readback`; up to 5 each (4 changes and the restore): the ISL29125 and BMP3xx config-write arms of `bench/test_bus_concurrency_under_api_load.py`; 1: `test_a_wrong_password_over_the_hotspot_reopens_the_hotspot` (a well-formed wrong password, which the next test restores); 1: `test_real_credentials_put_succeeds_and_confirms_accepted_values`; 0: `test_a_second_failed_streak_goes_silent_and_links_on_a_later_attempt` (the marker is its AND-gate on the previous test's write); `test_config_reset_over_rest_brings_back_the_defaults`: `resetconfig`'s deletions, the reboot's one defaults write per file, one restore write per saved file |
| `--allow-scd30-extra-write` (with `--allow-persistence-write`) | SCD30 NVM | flash `test_scd30_config_write_does_not_disturb_concurrent_sibling_reads`: 2 (the offset and its restore); flash `test_scd30_argument_reaction_is_recorded`: up to 3, restored in the script; bench `test_scd30_config_write_does_not_disturb_concurrent_sibling_reads_under_api_load`: up to 3 (2 offsets and the restore); bench `test_scd30_altitude_takes_effect_while_ambient_pressure_is_zero`: 4 (`AmbPres` 0, the stepped `Altitude`, and both restores) |
| manual (`scripts/run_manual_hardware_tests.sh`; each step states its writes before its `confirm()`) | flash filesystem | the flash config across a power cycle: 2 (`WarnCO2` and its restore); the power cut mid config write: up to 20 scratch writes and 1 removal per round, 3 rounds; the shutdown-command power cuts: `resetconfig`'s deletions, the next boot's one defaults write per file, one restore write per saved file (`config_files_restore.py`; `erasefram` is FRAM, outside the budget) |
| manual | SCD30 NVM | the NVM across a power cycle: 2 (`MeasInterval` and its restore); the power cut mid NVM write: up to 21 (20 changes and the restore), plus 1 for the `PUT` that puts `MeasInterval` back after the boot when the cut left it changed |
| `--allow-flash-cycle` | flash (reflash) | `test_real_uf2_reflash_and_boot_smoke_test`: 1; `bench/test_uart_link_crc16.py`: 2 (the CRC16 image and back); `test_send_stall_on_the_unpatched_image`: 2 (the control image and back); `test_ticks_ms_rollover_is_survived`: 1 (the tick-offset test image; the next round flashes its own image), counted in the rollover round's budget |

A `PUT /sensors` to the SCD30 spends one NVM write per field whose value changed, one per
`AmbPres`/`ForceCalRef` sent and one per `ContMeas=false`, none for an identical
TempOffset/MeasInterval/Altitude/SelfCal.

**Read the deselections in the verdict.** Because the gate deselects at collection time rather than
skipping per test, each deselected test carries a `deselected_by` property naming its flag, and the
run record's report lists it under `Deselected:` with that flag, counted and named as not covered
by this run; the advice line names only the flags of the wear-gate deselections present. "Clean"
there means "everything that ran, passed", not "everything ran".

**Mechanism and its checks:**

- `tests_hardware/conftest.py`'s `pytest_collection_modifyitems()` is the single deselection point:
  it deselects every `persistence_write` item without `--allow-persistence-write` and every
  `scd30_extra_write` item without `--allow-scd30-extra-write`, tagging each with
  `("deselected_by", <flag>)` in its `user_properties` before pytest's deselection hook, so the run
  record tells a wear-gate deselection from a runner's `-m` exclusion. No test checks either flag
  inline.
- `scd30_measuring` (`tests_hardware/flash/conftest.py`) is unmarked and ungated: it normally writes
  nothing, and its one possible write is a pinned prerequisite.
- `tests_scripts/test_persistence_write_marker_completeness.py` checks, without hardware: every test
  that `PUT`s a persisting field carries the marker, or is listed with the reason it writes nothing;
  every persisting helper or fixture is one of a set pinned by name, so a new prerequisite is
  triaged against the rule above rather than joining it silently; a device script that writes is
  run only by a gated test, a listed prerequisite, or a manual step that states its writes before
  its `confirm()`; no raw-socket request persists unlisted; `fetch()` is this tier's only route to an
  HTTP request; every marker is registered, every gate flag names a marker of its own name, and
  `scd30_extra_write` never appears without `persistence_write`.

## FRAM capacity check, real-hardware tier

`flash/test_fram_storage.py::test_every_fram_wired_module_gets_a_real_chunk_after_a_full_system_build`
(device script `fram_capacity_after_full_system_build.py`) is the real-hardware leg of the capacity
backstop of CLAUDE.md's implicit-FRAM-wiring rule: a shipped firmware asking for more FRAM than its
chip has must fail a test before it is flashed, not print once at boot. The script builds the bench
device's generated system over the scratch config directory `hwtest-scratch/` and runs its setup
list as `main()` does, then reports every logger of every FRAM-wired module that holds a real
chunk and every one left RAM-only. The FRAM-backed logger set and the module labels are derived
from the build's facts, never listed by hand: the script walks the rendered `fram_wired` labels,
and the host compares what it found with `harness.fram_backed_logger_names()` (buildgen's
`fram_backed_loggers`: each module's own logger, its `CFGMGR_<name>` where its config store logs to
FRAM, and the captive DNS server's with `conn`) -
a missing or extra name fails, naming it. A new driver, or `dev`'s two `uart_link` instances wired
with `fram_target = "fram"`, is checked with no test edit.

The L1 half is `tests/_sensortask_scenarios.py`'s
`fram_chunks_are_all_successfully_allocated_not_out_of_memory`, run for every device, with its
module list derived the same way (the `fram_wired` list of
`build/generated_src/sensortask_<device>_expected.json`), so a module off the list must hold none;
`tests/test_asy_base_classes.py`'s
`test_sensorreaderconfig_fram_allocation_failure_and_missing_config_file_together` is the negative
case proving it can fail.

**Deliberately not `fram._allocated_size <= fram.size`** - `FRAMManager.get_chunk()` checks
capacity *before* incrementing `_allocated_size`, never after, so that comparison can never be
false by construction. A `None` chunk on a module that should have one is the observable signal
that capacity ran out.

**mpremote-only by design (owner, 2026-09-16: 'we do not even add errno/wrnno for the out of FRAM
memory … Handle via mpremote.')**: no new `/status` field - this is a one-time, build-deterministic
fact (`FRAMManager` is a bump-pointer allocator with no deallocation, so "does everything fit" is
decided once construction finishes and stays true for that build's life), not live operational
state a client needs to query.

The UART links' FRAM-backed history is covered beyond this check by `tests/test_asy_uart_link_driver.py`
(L1: the RAM-only default, the allocation-failure fallback, the `logger=` reach-through and a
simulated-reboot roundtrip), `tests/test_digital_twin_uart_link.py`'s
`test_both_ends_get_their_own_real_fram_chunk` (L2) and, through `/status`, by
`bench/test_uart_link_under_api_load.py`'s `get_errcount()` calls.
