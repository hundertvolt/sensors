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

Silicon observations on this bench (2026-08-28):

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
| NeoPixel rig geometry (distance, ambient) | about 20 mm, an opaque cap over the LED and the sensor (0.9 lx with the LED dark) | the manual `isl29125_relative_lux_and_neopixel_rig_geometry`, the owner at the bench | 2026-11-13 |
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
  a synthesized bridge MAC can drift and orphan the router's DHCP reservation (observed 2026-09-04,
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
| `mpremote` `resume exec` (`Board.exec_live()`) | none | the same Ctrl-C, but no soft reset (`resume` clears mpremote's auto soft reset, `tools/mpremote/mpremote/commands.py`'s `do_resume()`, v1.29.0): `main.py`'s `KeyboardInterrupt` clause writes reset record 21 and the REPL keeps every module, so the read meets the running firmware's objects; nothing feeds the armed watchdog after it, which resets the board within one period of the firmware's last feed |
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
  Every device script that builds a `*_Reader` directly, not through `build_system()`, primes it: unprimed,
  `cfgmgr.valid` stays `False`, the first config read returns `None` and the read loop never reaches the
  sensor (`Error reading config data!` in its log).
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
  `GET /status` (the FRAM-backed `errcount` and the in-RAM reset reason) before anything touches the
  board, the `board` fixture's own reachability `exec` included. Without it the session notes that nothing was saved over REST and starts from the raw FRAM
  dump alone. To find the address without disturbing the running system (an `exec` stops `main.py`):
  the firmware sets `network.hostname()` from the `Hostname` setting (`devices/dev.toml`'s `hostname`
  until changed) before it connects, and rp2's lwIP sends it in the DHCP request and answers mDNS for
  it (`extmod/lwip-include/lwipopts_common.h`, `extmod/cyw43_config_common.h`, v1.29.0): the
  router's lease list names it, and an mDNS query for `<hostname>.local` returns it.
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
# (up to 12, 13 a session with both; "Persistence-write gating" holds the budget table):
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
the board serving: every flash run ends with one hard reset to a serving board. With a bench bridge
configured (`BenchBridge().is_configured()`, as the bench tier reads it, and no `--twin`), that
reset and every flash soak's closing one go through `harness.kick_then_reset()`
(`harness.reset_board()`), as every session reset does; a flash-only rig resets plainly.

**Verify the image.** Before any bench test runs, the bench conftest's `board_image` fixture reads
the image record (`--image-record`, default beside the `.uf2`) and compares it with the board's
`GET /system`: the device, `BuildDate`, the lwIP ensemble at the record's `maxConnections`, that
`maxConnections` against this tree's device TOML, and no tick-offset test image unless
`--allow-multi-day-rollover`, once the board answers at all: a board still rebooting or rejoining
after the last reset (a flash half before the bench half) is waited for up to 90 s. A mismatch
stops the session naming each deviation and the reflash that fixes it; a record from a dirty tree
is reported as a local-only image to revert after the round. A test that reflashes mid-session
runs the same comparison (`check_image()`).

## How a round runs

A round starts only with the owner's go-ahead in that session's own conversation (CLAUDE.md). Its plan
names the order, each row's expected outcome and wear, and the twin parameter the row confirms; the
results correct the twin until the two agree (owner, 2026-09-25, paraphrase).

1. Save the logs before anything writes: the session saves `GET /status` (with `--dut-ip`) and the
   raw FRAM dump itself ("The session's own state"); a step by hand does the same first (CLAUDE.md).
2. Build and flash `dev`'s own image of the tree under test: a device's result counts only from its
   own build on its own hardware (CLAUDE.md). An image from a dirty tree is local-only, reverted after
   the round ("Verify the image").
3. Flash tier, then bench tier (each runs L0-L2 first, "Running"), reading each verdict's deselected
   count, not only "clean".
4. The gated run (`--allow-persistence-write`) only after a clean default run, so a gated failure is
   the gated test's own (owner, 2026-09-22, paraphrase).
5. An unanticipated red stops the round and is reported; an ad-hoc script caps its retries and runs
   under `timeout` ("Bench traps").

## The bench log check

Every bench test runs inside `bench/conftest.py`'s autouse `no_unprovoked_log_entry`: one `GET /status` before the
test and one after, clearing and writing nothing. A new E or W entry in any logger between the two fails the test,
naming the logger, the code, its catalog name and the test - a normal operation logs neither. A test whose entries are
its purpose carries `@pytest.mark.provokes_log("<why>", (logger, kind, catalog name), ...)` (`markers.py`), naming
every entry the source can leave on its path, and is read like any other: an entry outside that set fails it, and an
entry in it need not appear (the test asserts its own). Collection refuses a marker with a reason alone, a malformed
entry or a name with no live catalog row. A clear made through `reset_all_error_logs()` hides nothing: the `GET
/status` it already takes before its `PUT` (saved to the evidence first) is kept, so the check reads each segment - the
test's first read to its first clear's, each clear to the next one's, the last to the after-read, all of a segment
after a clear new - against the same set, adding no read and no write. A board that cannot answer
`/status` at a test's bound - unreachable, or still booting - fails that test by name after one read under the
helpers' own timeout: a test leaves the board serving. The exception is a test marked `ends_unreachable` (the hotspot
credential stage, the isolated-board heap module): its unanswered end leaves its window open, and the next read that
answers - the next test's, or one at the session's end - closes it against the union of the sets it spans. The
hotspot module reads through the DUT's gateway while the bench radio is its client.

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
  `isl29125_relative_lux_and_neopixel_rig_geometry`.
- Ambient excluded (enclosure or darkened room). Ambient above the low range puts the whole run on
  the high range and fails with "only range N was ever used" - a rig fault, not a driver one.
- Nothing else driving the pixel: these scripts write the pixel directly, past `request_signal()`'s
  arbitration, so a notification signal landing mid-scenario is indistinguishable from a bad reading.

Every assertion is **relative** - continuity across the switch, no chatter, hue/saturation invariance
while the level moves, gain-ratio convergence. Absolute lux and CCT against a WS2812's three narrow
emission lines are meaningless and are asserted nowhere; the manual tier checks relative values
only, with no reference meter (owner, 2026-11-13). CLAUDE.md's FRAM rule applies in its sharpest
form to every script here - see "A hardware run overwrites the production modules' FRAM chunks"
below before treating any log as evidence.

The rig as last recorded (the manual step saves `rig-geometry.json` into its run's evidence):

| distance | ambient | recorded |
|---|---|---|
| about 20 mm | an opaque cap over the LED and the sensor (0.9 lx with the LED dark) | 2026-11-13, the manual `isl29125_relative_lux_and_neopixel_rig_geometry` |

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
| A script that reads error-log content clears its chunk at its start, after the session's evidence save: an inherited ring drifts its assertions, and a clear at the end would erase what it just did, so its residue stays (read it as "Known assumptions and open findings" says); `fram_error_log_reset_race_verify.py` is the one exception, since it reads what the raced reset left | review |
| A script that boots the firmware's `main()` installs an always-printing unretrieved-task report first (the product's `PrintLog` report at level 1, or a script-local one) | `tests_scripts/test_exception_handler_contract.py` |
| A heap-measuring script sets `gc.threshold` itself and reports it as its first fact | `tests_scripts/test_device_script_gc_threshold.py` |
| A STATE-dispatched script needs the `persistence_write` marker only on the runs that pass a writing STATE | `tests_scripts/test_persistence_write_marker_completeness.py` |
| Run it in the twin first, at both GC stages (`scripts/record_twin_instrument_runs.py`; the flash tier once per stage, refused if its twin board never took the stage): each entry's `stages` holds `"-1"` and `"32768"`, each `pass` or `exception`, and its `result` is `exception` if any stage failed; a script a flash test runs is charged with the outcomes of the flash tests that run it, not its whole module's | review |
| Park the shared rig (the NeoPixel) dark in a `finally` | `tests_scripts/test_device_script_rig_parking.py` |
| Feed the watchdog in short steps: `_shared/watchdog.py`'s fed waits, at most 2 s a step | `tests_scripts/test_device_script_watchdog.py` |
| Shared code lives in `_shared/`, inlined at render by `# @include _shared/<name>.py` | review |

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
correctly"; being answered at all is the ceiling's business. A 413 goes out before its body is read,
so the close's RST can cut the 413's own body: a reset after its status line counts as that 413
(owner, 2026-11-06). Pair that with a floor on how many
were answered, or the test passes vacuously on a run where nearly everything was refused - the
same "assert a minimum engagement beside every ceiling" habit as for device scripts.

The rest, one fact each (occurrences: `HEAP_FRAGMENTATION_MEASUREMENTS.md` archive §7R.5):

- After an unexpected reset, read `GET /status`'s `ResetReason` and the FRAM-backed error logs
  (CLAUDE.md) before anything flashes, resets or clears the board; `journalctl -k` times the USB
  disconnect. `machine.reset_cause()` reads `WDT_RESET` after a starvation, `machine.reset()` and
  `mpremote reset` alike (SPECIFICATION.md Part F.5.4), so it only separates power-on from the rest.
  A harness `hard_reset()` or `mpremote reset` of a running board reads 21 (interrupted), and 2 after
  a device script that ran the system's boot: that boot consumed record 21 and the script cleared its
  phase mark, so the reset finds neither (2026-11-06); a device script whose own build stopped before
  it finished reads as a boot failure in that phase (SPECIFICATION.md Part A.8).
- An `mpremote` `exec`/`run` stops `main.py`, and nothing feeds the watchdog after it, so the board
  resets about 8 s later unless the session resets it first: a device script that never feeds it
  dies ~8 s after it attaches (bench, 2026-09-25), and every raw-REPL session ends in a hard reset.
- A transient `mpremote` failure is retried - within 10 s, then the device node
  re-resolved, then one USB rebind - only while the script has printed nothing: a script never runs
  twice, and every retry and rebind is a recovery event in the run record.
- The bench's USB CDC can stop entering the raw REPL until the port is rebound (recorded 2026-09-02,
  `e249999`); the harness does one unbind and bind per `mpremote` call ("Workarounds").
- Ctrl-C reaches the autostart image only while the board's 512-byte stdin ring has room: the
  firmware never reads stdin, so after a host program has sent 511 bytes (a terminal, a probe) a
  later Ctrl-C stays in the USB buffer and `mpremote`'s raw-REPL entry fails with a generic error
  that looks like a board fault. Reset the board by power or RUN, or use the no-autostart image
  (`scripts/build_firmware.py <device> --no-autostart`), whose REPL keeps reading stdin
  (`shared/tinyusb/mp_usbd_cdc.c`, `ports/rp2/mphalport.c`, v1.29.0).
- A Ctrl-C into the autostart image ends its whole event loop: the board records reset reason 21
  and the watchdog resets it within its timeout, unless a Ctrl-D at the REPL soft-resets it first, whose boot reads the same code (any other exception ending the loop after boot records 22 and the entry resets the chip at once; SPECIFICATION.md Part F.5.4); a change answered `Valid` whose deferred flush has
  not run yet is lost.
- Every flash run ends with one hard reset to a serving board (`flash/conftest.py`'s
  `leave_board_serving`).
- Every hard-reset fallback goes through `harness.recover_by_reset()`, reported as a recovery pass
  naming what the reset path skipped; its reset waits for an `observe_during()` log tail to free
  the serial port, which `mpremote` needs for its raw REPL entry.
- After a reset or a flash the board can fall back to hotspot mode, since a reset without a kick
  leaves a stale station entry on the bench AP for about 60 s ("Workarounds");
  `kick_all_stations()` + `hard_reset()` recovers it, occasionally only on a second try, and for a
  hand recovery `.venv/bin/python tests_hardware/kick_then_reset.py [--device D]` does both steps
  (~40 s to recover, recorded 2026-09-19, `1fb370b`). A system command issued over REST
  (`PUT /system {"SystemCmd": "reboot"}`, `erasefram`) is the same trap: kick the AP's stations once
  the reset it arms has taken the board off USB (`harness.kick_after_reset()`), or the board comes
  back healthy but never re-associates (serial: `WIFI Hotspot mode is active`). A kick at the
  answer is not enough: a shutdown still running rejoins after it (erasefram's took ~22 s, bench,
  2026-11-05).
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
| the bench's USB CDC stops entering the raw REPL until the port is rebound (recorded 2026-09-02) | `harness._usb_reset_device()`, from `Board._mpremote()` | one unbind and bind per `mpremote` call (a 10 s command timeout, at most 2 s to unbind and 3 s to bind); a refused sudo fails the run | a full round records no rebind in `Board.recovery_events` | 2026-10-14, `v1.29.0` (code read) |
| a transient USB-settle failure of `mpremote` right after a reset | `Board._mpremote()` | retried within 10 s, polled every 0.5 s, never once the script printed | a round records no transient retry | 2026-10-14, `v1.29.0` (code read) |
| a reset re-enumerates the CDC device under another node | `Board._mpremote()`, `_rebind_device_if_moved()` | 2 re-resolves per call | a round records no node rebind | 2026-10-14, `v1.29.0` (code read) |
| a stale AP-side station entry survives the DUT's reset and blocks its reassociation (recorded 2026-09-02) | `BenchBridge.kick_client()`, through `kick_all_stations()` before every expected reconnect (`harness.kick_then_reset()`, which `harness.reset_board()` uses for a session, flash-run or soak reset), through `harness.kick_after_reset()` once a command's own reset took the board off USB, or in `harness.reflash()` once the board is in its bootloader | one `iw station del` per station per reset | a round records no stale-entry reconnect failure | 2026-10-14, `v1.29.0` (code read) |
| `nmcli -g` escapes `:` as `\:` in an SSID or PSK | `BenchBridge.ap_ssid()`, `ap_password()` | `--escape no` on every SSID/PSK read | `nmcli -g` stops escaping | 2026-10-14, `v1.29.0` (code read) |
| `nmcli connection down` errors on an inactive connection | `BenchBridge.ap_down()` | that one error taken as already down, once per call | `nmcli` makes `down` idempotent | 2026-10-14, `v1.29.0` (code read) |
| nmcli's own rescan can miss a hotspot `is_ssid_visible()` just saw (recorded 2026-09-08) | `bench/test_hotspot_role_reversal.py`'s `_join_dut_hotspot_with_reverify_retry()` | 5 joins, each retry a recovery note | a round records no re-verify retry | 2026-10-14, `v1.29.0` (code read) |
| a ceiling refusal under concurrent API load is the stack's reject-when-full, not a fault | `bench/test_bus_concurrency_under_api_load.py`'s `fetch()` | 3 attempts per call, 0.25 s apart, each counted | the arms run below the ceiling | 2026-10-14, `v1.29.0` (code read) |
| one header line resets the server's per-call read timeout | `harness.HELD_PAD_LINE`, in the ceiling probe's walk | one line per held connection per step (0.3 s) | the walk no longer outlasts `web.per_call_timeout_s` | 2026-10-14, `v1.29.0` (code read) |
| DNAT to 127.0.0.1 does not deliver to a local socket on this bench (`route_localnet` 0) | `BenchBridge.start_udp_source_capture()`, read by `read_captured_udp_source_port()` | one `tcpdump -c 1` capture per test (60 s) | the redirect delivers locally | 2026-10-14, `v1.29.0` (code read) |

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
  new `TASK_RAISED` or `SUPERVISOR_RAISED` (`error_log_helpers.assert_no_new_task_raised()`): over
  `GET /status` on the bench, over the REPL on the flash tier (`read_live_system_log()`, which
  interrupts the firmware, so the flash soak hard-resets after each read, and reads the first only once
  a hard reset's boot line has come). A test that clears the logs reads them first. A device script
  running the firmware's `main()` installs an always-printing report before it, as the PC tiers do;
  `tests_scripts/test_exception_handler_contract.py` pins all three.
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
  §7R.4, §9). Read `_open_conns`, a plain int (no coroutine, no allocation).

**Re-derive a tool's printed summary from the raw output when a label looks wrong**, and remember
a minimum from a 5 s snapshot bounds the true peak from one side only.

**Count on both sides, and treat a gap as a finding.** Count every `_open_conns`
step above the limit — installed as soon as `sensortask_dev.webserver` exists, not at a
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
for 120 s, two pollers - `GET /measurements` and `GET /status`, each every
5 s - and one website client, which loads the index page's assets
once and then polls the landing section's GET route at its `pollIntervalMs` from the generated
definitions. Every response must be complete, with no ceiling refusal, no reboot (`BootSignature`
unchanged) and no task end; the per-route maximum and median latency go into the run record.

**Client-triggered console output cannot starve the watchdog**: the gated bench test
`test_console_output_with_a_non_reading_usb_host_never_starves_the_watchdog`
(`bench/test_network_resilience.py`) sets `DebugLevel` 0, holds the serial port open with DTR
asserted and never reads it, and drives the adversarial load for 60 s
(six slowloris clients, a refused head, a truncated PUT and two resetting clients) - `BootSignature`
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

- **The ceiling probe** (`discover_max_connections()`) dwells 0.3 s per step
  and pads every held connection with a header line (`HELD_PAD_LINE`) per step, so the per-call
  timeout never frees a slot mid-walk and only the outer cap bounds it (`probe_limit` 40 × 0.3 s). It fails loudly if a held connection answers instead of staying open,
  and re-checks every counted socket is still open when the refusal lands. A connect that is refused
  or times out is the wall itself, counted rather than raised, with its own 2 s timeout
  apart from the read's, so a slow handshake is never read as
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

**The C-stack budget** (`flash/test_memory_stress.py::test_c_stack_deepest_chain_leaves_the_reserve`,
`device_scripts/c_stack_budget.py`, L3, ungated) boots the bench device's generated system over the
scratch config directory `hwtest-scratch/` and wraps every I2C bus leaf and the FRAM driver's three
SPI command functions (`_send_and_read()`, `_send_and_write()`, `_send_command()`: where every FRAM
chain ends, three plain calls below `set_values()`, whose own wrapper would add a frame under them,
944 B on the twin; agent, 2026-11-11) from outside to record `micropython.stack_use()` per phase:
the setup batch, the started tasks and timers over a fed 10 s window
(`l3.c_stack_budget_window_ms`), then one `GET /status` dispatched in-process through the app's own
`dispatch_request()`: the top of the longest static await chain `tests_scripts/test_await_depth.py`
pins (SPECIFICATION.md Part F.1), which must answer 200, since Microdot answers a raising handler
with a 500. The peak's leaf and phase are reported (`chain`, `phase`). A second `GET /status` then
takes, once, that route's deepest static chain ending in a FRAM-backed log entry: after a sync
(`set_utc_valid()`), the system source's local time reads NTP's config store as `setup()` leaves it
on a directory at its path (`valid` False; agent, 2026-11-11), and `CFGMGR_NTP` logs E34
`CFG_NOT_VALID` (`asy_config_manager.py` `_get_values()`, 12 await levels from the request's top,
then 10 nested plain calls down to `_send_and_read()`); its end is its own fact (`provoked_end`,
beside `provoked_logged`, the entries it logged). The host holds the provoked end to leave
`l3.c_stack_reserve_b` (1,024 B) of the 7,936 B limit and notes the quiet peak beside it (owner,
2026-11-11: "A", asked which bound the C-stack check holds); the twin's figures
(`twin_c_stack_peak`) are reported, never compared. No flash cycle and no production config file: each
setup writes its defaults once into the
scratch directory, removed afterwards; the booted modules' logs, the provoked E34 among them, go
into FRAM, which the session start saved first.

**The routine no-yield stretches**
(`flash/test_memory_stress.py::test_routine_no_yield_stretches_stay_under_the_gc_term`,
`device_scripts/loop_stretch_timing.py`, L3, ungated) constructs the bench device's generated system
over the scratch config directory `hwtest-scratch/` and times on the chip what the product runs
without a yield: a `gc.collect()` over that object graph (the worst of 5), one VOC-algorithm step
(the worst of the last 20 of 60, past the algorithm's start-up blackout) and the longest gap between
two yields of one CRC32 check over a 256-byte chunk. The host holds each to the 21 ms collection
pause the UART reply floor budgets (Part N `uart.gc_pause_worst_ms`; SPECIFICATION.md Part F.3).
Construction only: no task, no bus I/O, no flash cycle and no production config file; the scratch
directory is made and removed around it, an aborted run's leftover first.

**The flash write's loop gap**
(`flash/test_memory_stress.py::test_flash_write_loop_gap_is_recorded`,
`device_scripts/flash_write_loop_gap.py`, L3, behind `--allow-persistence-write`: the test owns one
scratch flash write) times each synchronous call of one 1 KiB scratch file - its open, the write,
the close and the removal - and prints
`STRETCH flash_call_max_us=… flash_total_us=…`. The file is
the relative `config_HWTEST_stretch.bin`: the board's root on silicon, the twin's scratch directory
there, never the host's `/`; it is removed before and after, and one a reset strands is a scratch
file the session fixtures' standard-state check names ("Prerequisites" item 4). A measurement,
never failed on the figure: the host records it for SPECIFICATION.md Part F.3's
`stall.flash_program` row.

**The listener close on silicon** (`flash/test_modlwip_listener_close.py`,
`device_scripts/listener_close_leaves_the_pcb_pools.py`, L3, ungated: no write of any kind, no flash
cycle and no FRAM manager) checks SPECIFICATION.md B.14.4's close and `listen()` patches on the
flashed image. The host reads the two TCP pcb pools' descriptors, slot arrays and free-list heads
(`memp_TCP_PCB`, `memp_TCP_PCB_LISTEN`, their `memp_memory_*_base` and `memp_tab_*`) from
`firmware.elf` in the toolchain's rp2 build directory (`harness.elf_symbols()`, `arm-none-eabi-nm`),
once that build's `.uf2` equals the one beside the image record (`--image-record`) and it compiled
the patched modlwip copy. The script, production stopped, reads each descriptor - unless the board
reports the ELF's array and head it reads no pool byte - and takes both pools in one interrupts-off
picture; it closes a listener, then a socket whose `listen()` met a locked heap, and takes a second.
Every slot free in both, except the one each pool hands the script's own sockets, must be
byte-identical (at least one per pool, or the check would pass on nothing), reported by pool, slot
and offset, and no free slot may go missing, then or after the round trip (a third picture). A bind
without `SO_REUSEADDR` must take the port again, and one loopback round trip runs: the twin echoes
it, while rp2's lwIP has no loopback netif (`LWIP_NETIF_LOOPBACK` 0), so silicon's answer is
`EHOSTUNREACH`. Memory is only read (`machine.mem32`), never written by address. On an unpatched
image the listener's stray stores are NULLs, seen only where they land on non-zero bytes; the failed
listen's `tcp_poll()` stores a function pointer, seen anywhere. `--twin` runs the socket half only.

**The loop lag under combined load** (`device_scripts/loop_lag_under_combined_load.py`) runs the
bench build's shipped `main()` beside a 10 ms lag probe, an allocation-churn task and FRAM block
writes in the script's own scratch region (`fram_max_size - 0x200`), while the host's readers
cycle every JSON GET route. The flash test
(`flash/test_memory_stress.py::test_loop_lag_under_combined_load_stays_under_the_uart_reply_budget`)
runs in the twin only (`--twin`: the script's scratch config, serving on 127.0.0.1:8080, under a
ceiling of readers), since only the bench network reaches the script's server on the board.
Silicon's run is the bench tier's
`bench/test_memory_stress_bench.py::test_loop_lag_under_http_load_on_every_route_stays_under_the_smallest_hard_consumer`
(BENCH mode `"production"`: `main()` on the board's own config and address); the shipped `main()`
writes production FRAM chunks, so the board's error log is saved first. The script emits facts
only, among them when its worst lag ended after `main()` started (inside the boot or under the load);
the host holds the worst lag to the device's smallest hard consumer (Part F.3's `lag.loop`)
and checks that every route was served, `main()` kept running and the FRAM load ran without a
failed write.

Four of Part F.3's timing rows wait on these instruments' silicon figures: the flash stretch
(`stall.flash_program`), the on-target stretches (`stall.voc_process`, `stall.crc`) and the
loop lag under combined load (`lag.loop`); BACKLOG.md's "Real-hardware work still owed" carries the
runs.

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
evidence saved first; `bench/test_reset_reasons.py` then reads the watchdog's REASON bits on the
board itself and asserts the half each reset kind sets. The last column holds the date each code
was read back on `dev`'s final images.

| code | test that proves it | level | on silicon |
|---|---|---|---|
| 0 | `bench/test_reset_reasons.py::test_an_invalid_record_reads_as_unknown` | L4 | 2026-11-11 |
| 1 | `manual/manual_persistence.py`'s power-cycle steps (each reads `ResetReason` after power returns; `test_console_soft_reset_keeps_the_reset_record` holds a valid record across its cut, so its 1 also shows the cut cleared the scratch registers) | manual | 2026-11-13 (the power cut and the RUN pin) |
| 2 | with SDA held across a `machine.reset()` and a watchdog reset, each with its REASON bit: `flash/test_bus_concurrency.py::test_a_held_sda_line_through_a_reset_is_freed_by_the_next_boot`; after the bootloader command's BOOTSEL round trip, which loses the record: `bench/test_reset_reasons.py::test_a_bootloader_reboot_is_attributed` (the way back is `sudo picotool reboot`, no load), `flash/test_system_commands.py::test_bootloader_command_shuts_down_then_enters_bootsel`; after a fault inside the running graph that stops every feed: `flash/test_task_supervisor.py::test_a_fault_inside_the_running_graph_stops_every_feed_and_the_watchdog_resets` | L4, L3 | 2026-11-11 |
| 3 | `bench/test_end_to_end_timing.py::test_real_reboot_sequencing_via_rest_completes_cleanly`; `flash/test_system_commands.py::test_a_reboot_with_storage_paused_still_resets_attributed`; a reboot at a boot's first answer: `bench/test_system_commands_over_rest.py::test_a_reboot_at_a_boots_first_answer_resets_cleanly` | L4, L3 | 2026-11-11; 2026-11-13 (five warm reboots) |
| 5 | `bench/test_reset_reasons.py::test_the_supervisor_escalation_reboot_is_attributed` (a task dying until the budget reboots, also with a console host holding the port unread) | L4 | 2026-11-11 |
| 6 | `bench/test_reset_reasons.py::test_the_starved_watchdog_fallback_is_attributed`; the fallback itself on L3: `flash/test_watchdog_starvation.py::test_reboot_falls_back_to_starving_the_watchdog_when_its_timer_cannot_arm` (`reboot_fallback_starves_the_watchdog.py`) | L4, L3 | 2026-11-11 |
| 7 | `flash/test_system_commands.py::test_config_reset_deletes_every_config_file_and_reboots`; `bench/test_system_commands_over_rest.py::test_config_reset_over_rest_brings_back_the_defaults` | L3, L4 | 2026-11-12; 2026-11-13 |
| 8 | `flash/test_system_commands.py::test_fram_erase_blanks_the_chip_and_every_logger_restarts_empty`; `bench/test_system_commands_over_rest.py::test_fram_erase_over_rest_blanks_every_error_log` | L3, L4 | 2026-11-11 |
| 9 | `bench/test_reset_reasons.py::test_an_incomplete_command_is_attributed`; `flash/test_system_commands.py::test_a_hung_shutdown_step_ends_in_a_watchdog_reset` | L4, L3 | 2026-11-11 |
| 11-15 | `bench/test_reset_reasons.py::test_a_hang_in_boot_phase_p_is_attributed`, one case per boot phase 1-5; 11 after a power-on, a Ctrl-D soft reset with phase 1 marked and no record (`reset_code_invalid_record.py`'s STATE `boot_phase` calls `begin_boot()`): `manual/manual_persistence.py::test_console_soft_reset_keeps_the_reset_record` | L4, manual | 2026-11-11 |
| 20 | `bench/test_reset_reasons.py::test_a_c_stack_exhaustion_is_attributed` (`reset_code_stack_exhausted.py`: a reader recursing until the stack check raises; the handler that catches it records the overflow and the supervisor's next pass reboots with the stack code; with SYSTEM's FRAM entry write never returning (the loop with it), the watchdog's reset, timer bit, reads the recorded 20; mode `escape`: no handler records it, the dead-task entry writes 20 before its held write) | L4 | 2026-11-11 |
| 21 | `bench/test_reset_reasons.py::test_a_console_interrupt_is_attributed`; a harness hard reset of the serving board, whose `mpremote` Ctrl-C ends `main.py` before its `machine.reset()`: `bench/test_reset_reasons.py::test_a_harness_hard_reset_reads_as_a_console_interrupt`; after a power-on, a Ctrl-D soft reset inside the watchdog window: `manual/manual_persistence.py::test_console_soft_reset_keeps_the_reset_record` | L4, manual | 2026-11-11 |
| 22 | `bench/test_reset_reasons.py::test_a_loop_ended_by_an_exception_after_boot_is_attributed`, an `OSError` and a `SystemExit` from the loop core (`reset_code_loop_end.py`: the frozen entry imported again after `mpremote`'s Ctrl-C, under the board's own config, no flash write) | L4 | 2026-11-11 |

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
  L4 checks every error log blank after the boot, then waits up to 150 s (about 60 s) for each SGP40's
  first backup (`GET /status` `BackupTS`), as does the cut erase of code 9, so no later boot reads a
  blank backup chunk (agent, 2026-11-06). FRAM is outside the wear budget.
- **`reboot`** and **`bootloader`** run the reboot sequence - record, flush, pause, reset - and the
  reply precedes the reset within its bound (code 3; `bootloader`'s BOOTSEL round trip loses the
  record, read back as code 2); a hung shutdown step ends in a watchdog
  reset read as command incomplete (code 9).
- **`mempause`** pauses storage; a reboot with storage paused still resets attributed (L3), and L4
  races `erasefram`, `reboot` and `mempause` at once, then `reboot` and `bootloader` at once.
- **`ResetErrors`** answers `Failed` and clears nothing under `mempause` and after a `reboot` that
  answered `Valid` (L4, the errcount saved first). A damaged store file is repaired at setup and listed in
  `ConfigFaults` (L3).

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
| boot bus clear | SDA held at construction; held across a `machine.reset()` or a watchdog reset | L3 | `test_a_held_sda_line_is_cleared_and_every_device_answers` (its boot-clear case); `test_a_held_sda_line_through_a_reset_is_freed_by_the_next_boot` | SDA high, the controller constructs, every device answers; after a reset, every device answers the production boot's controller and the boot reads 2 with the reset's REASON bit |
| setup reset | each I2C chip's driver `setup()`, every transfer recorded (`setup_resets_each_chip_once.py`) | L3 | `test_every_chip_setup_resets_it_once_after_a_read_identified_it` | one soft reset per chip, after the read that identified it, then a valid read |
| WiFi radio re-init | `_recover_device()` on a connected link | L4 | `bench/test_wifi_radio_reinit.py` (`wifi_radio_reinit_recovery.py`) | the link back within the connect budget |
| task restart | a starter that dies at once; a chip unplugged live | L3; manual L4 | `flash/test_task_supervisor.py`; `manual/manual_bus_electrical.py::test_hot_unplug_replug_i2c_recovery` | the starter called again, SYSTEM's log holding one `TASK_RETURNED` end per restart; by hand the log entries while unplugged and the readings back with no reboot |
| FRAM chip lost | the chip unplugged | manual L4 | `manual/manual_bus_electrical.py::test_fram_unplug_replug_recovery` | by hand the seconds from the pull to the first FRAM log entry (`fram-pull-latency.txt`, "none within 120 s" when none), then FRAM-backed entries written again after the replug, no reboot |
| UART link lost | the crossover jumper pulled mid-transfer | manual L4 | `manual/manual_bus_electrical.py::test_uart_crossover_pull_recovery` | the link's `Failures` rise and every code logged meanwhile (`uart-crossover-pull.txt`, the verbatim errcount beside it), its `Transfers` advancing within 30 s of the replug, no reboot |
| supervisor reboot | a task dying until the restart budget is spent | L4 | `bench/test_reset_reasons.py::test_the_supervisor_escalation_reboot_is_attributed` | `ResetReason` 5 with the forced bit; SYSTEM's escalation entry in the rounds the script printed before the reset (its log is RAM-only, so production's history never holds it) |
| hardware watchdog | the watchdog starved; every feed stopped inside the running graph | L3, L4 | `flash/test_watchdog_starvation.py`; `flash/test_task_supervisor.py`; `bench/test_reset_reasons.py` (codes 2 and 6) | the reset, then the code |

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
  `--allow-persistence-write` and a `--soak-duration` covering both windows (`long` on `dev`): it
  skips without that duration and fails without that write. The soak runner cannot give it the
  module, since its `soak_duration` floor narrows any `-m` to this case alone; the module runs whole
  through the runners' wrapper (not yet run on hardware):
  `scripts/_require_clean_hardware_run.sh --runner run_bench_soak_tests_hotspot --levels "soak duration long (not a level)" tests_hardware/bench/test_hotspot_role_reversal.py --soak-duration long --allow-persistence-write`.
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
  their names state; none waits for an NTP exchange inside the window. A CYW43-level fault such as
  `wlan.connect()` itself raising is no network-path fault `tc` or `iptables` can express; the
  twin's `--fault wlan:...` hook (`digital_twin/run_generic_integration.py`) injects it.
- **Every garbage injection proves it was delivered.** The NTP and DNS garbage tests redirect the
  port with a `nat` PREROUTING `REDIRECT` to a `RogueUdpResponder` bound on every address, and each
  asserts the responder answered the DUT's address at least once (`answered_from`), so a redirect
  that never delivered fails as "the injection never reached the DUT", never as a pass. `REDIRECT`
  targets the ingress interface's own address: a DNAT to 127.0.0.1 never delivered on this bench,
  whose `net.ipv4.conf.*.route_localnet` reads `0` on every interface, the Linux condition under
  which DNAT to 127.0.0.1 from a non-loopback interface fails.
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

Read these before trusting a run's results: a failure in one of these areas may point at an
assumption, not at a product bug.

- **L3 and L4 have run end to end on this bench under MicroPython 1.29.0** (2026-09-11): a `dev`
  image built from `src/`, the flash, bench and mid soak tiers clean against it; the on-target
  answers it gave are in SPECIFICATION.md Part F.5.
- **A hardware run overwrites the production modules' FRAM chunks — never read an error log as
  firmware evidence straight after one.** `FRAMManager` is a deterministic bump allocator (a
  required property, SPECIFICATION.md Part A.4), so a device script's own first chunk *is*
  production's first chunk. Usually the next boot's `_read()` just fails on the size/CRC mismatch
  (each chunk's CRC is seeded by its owner's name) and the log honestly reads empty — but a script
  leaving a well-formed chunk behind under the production owner's name fabricates a plausible one:
  `fram_error_log_reset_race_seed_and_race.py` seeds three entries into what is physically
  SystemService's chunk. CLAUDE.md's "read the FRAM logs before clearing" rule assumes a board that
  has been running normally — check what was last run against this one first. Every session
  therefore saves the whole FRAM part raw at its start and end (`fram-raw-session-start.txt`,
  `fram-raw-session-end.txt` in the run's evidence, `fram_raw_dump.py` reading only) and
  `GET /status` with it on the bench, so the before-image is kept and every entry a run adds is
  attributable. Three kinds of entry a run leaves in the production history are its own: every
  scratch build (`build_system()` or `main()` over `hwtest-scratch/`) records `W CFG_FILE_UNREADABLE`
  (22) in each FRAM-backed config store's history, its files not found there; `c_stack_budget.py`'s
  provoked phase records `E CFG_NOT_VALID` (34) in `CFGMGR_NTP`'s; and test-band residue
  - the reboot script's load entries, an erase script's seeds when it fails before erasing - is the
  same kind.
- **The chunk reset race lands on each named seam, and a stale seed cannot pass.**
  `flash/test_fram_storage.py::test_error_log_history_is_all_or_nothing_across_a_reset_raced_chunk_write`
  runs once per seam of a chunk write's five transfers (status byte 1 and 2 BUSY, payload and CRC,
  status byte 1 and 2 IDLE): the seed phase seeds three test-band entries chosen by a fresh nonce
  and resets right after that transfer (`LANDED seam=<n>`), and the verify phase accepts only the
  whole history lost, the seeded three, or the seeded three plus the raced entry - so a history
  seeded by another run fails - then clears the chunk.
- **A real hard reset can cut a FRAM chunk write part-way, and the bench test that lands them expects
  it.** `bench/test_end_to_end_timing.py::test_real_hard_resets_during_natural_fram_backup_activity_recover_cleanly`
  resets the board at uncontrolled points of SGP40's natural VOC backups, so the next boot may find a
  block status byte neither idle nor uninitialised (`E FRAM_STATUS_BYTE`) or a block holding invalid
  data, repaired from the other copy (`W FRAM_BLOCK_INVALID`): three resets during FRAM writes left
  such entries on the bench (agent, 2026-09-13). The test allows exactly those two entries in FRAM's
  log, saves the log, then clears it (`reset_all_error_logs()`).
- **The UART link's silicon coverage** is `flash/test_uart_crossover.py`, `bench/test_uart_link_under_api_load.py`
  and `bench/test_uart_link_crc16.py`, none run since the receive path moved onto the DMA ring. Each
  crossover script that runs the link runs with no CRC and with CRC16, the exchange script also with
  COBS framing (`cobs`, no CRC; owner, 2026-11-02); the bench link suite runs
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
    driving the initiator's public `uart_set()` in the exerciser's sleep after each of its banner GETs,
    since the initiator refuses a second transaction: SPECIFICATION.md J.2), with no `src/` change,
    besides the link's transfer/failure count in `/status`'s `UARTLINK`, asserted advancing while the
    API is hammered.
    The comm hazards run under API load through `PUT /uart`'s dispatch-only `UartHazards` on `dev`
    (SPECIFICATION.md A.8 and E.6.6): the bench tier's
    `test_a_hazard_run_under_the_readers_load_reports_every_verdict` starts one hazard run while 3
    readers GET `/status` until it ends, judges every verdict as the twin does, and checks the echo's
    `Failures` unchanged, the echo resumed, the WEBSERVER counter at 0 and no task ended; it is
    collected, its silicon run owed. Read and save both UART logs (`UART_init`, `UART_resp`)
    first: the faults the run provokes land in both, and one run fills `UART_resp`'s 10-entry log,
    overwriting its older history (agent, 2026-10-22). The stalled TX stays with the raw hazard script.
  - The UART fault catalog (~20 scenarios: corruption, drop, truncate, duplicate, overrun, lost
    final ACK, peer reset mid-transaction, ...) is mock-only, a listed structural exception: no
    injection hardware will be bought (owner, 2026-09-22), and a second raw UART is not used as a
    stand-in (owner, 2026-09-22). On silicon the flash tier covers silence and a baud mismatch
    (`uart_crossover_recovery.py`), and `uart_comm_hazards.py` the concurrency and field sweeps.
  - A build without the UART modules fails the tier, never skips; a board running an image older
    than the tree simply does not carry a change, which "Verify the image" catches.
- **A device script's every wait stays inside its own watchdog window, or a link fault reports as a
  reset instead of a result.** The crossover scripts arm the 8 s watchdog of `_shared/watchdog.py`;
  a join on a responder whose frame never arrives cannot complete (`uart_listen()` parks in its one
  unbounded read), so they poll `task.done()` in fed steps and free a parked listener with
  `UARTComm.clear()`. A frame that never arrives then reports `UART_NO_ACK` (`errno` 81, initiator)
  and `TIMEOUT` (`errno` 22, responder read timeout) instead of an `mpremote` I/O error with no
  facts.
- **Both crossover device scripts poll at the two rates the device TOML sets for each UART**
  (`poll_wait_ms`, 2 ms on `dev`, for a transaction in flight; `poll_idle_ms`, 50 ms, for a listener
  waiting on a frame that may never come; SPECIFICATION.md Part F.5.9), so the flash tier exercises
  the shipped configuration. A responder notices the first byte of a frame up to 50 ms late, so a
  measured first-frame latency on this rig includes that and is not a link fault.
- **`asy_uart_driver.UART.deinit()` does not release the GPIO function select, so a script that
  inits a UART on different pins poisons that peripheral until the next hard reset.** UART1 put on
  GP4/GP5 stays muxed there after `deinit()` and keeps taking RX from the floating GP5 instead of the
  jumpered GP9, failing every later crossover run, across `mpremote`'s soft resets (which do not
  restore pin defaults) until a `mpremote reset`. The shipped scripts use only the bench TOML's
  pins; any ad-hoc script that moves a UART's pins hard-resets the board afterwards.
- **`mpremote`'s soft reset never re-executes the frozen `_boot.py`/`boot.py`/`main.py`**
  (the pinned MicroPython C source and the bench agree): only a genuine `hard_reset()` resumes the
  live system; `exec()`/`run_isolated()` never do, regardless of `soft_reset_after`
  (`harness.Board.run_isolated()`'s docstring). The two read paths differ in what they meet:
  `exec()`'s raw-REPL Ctrl-D soft reset (`ports/rp2/main.c`'s `soft_reset_exit`, then
  `mp_deinit()`/`mp_init()`) leaves a fresh interpreter whose `sys.modules` holds no firmware module,
  so a read of the running firmware's objects goes through `exec_live()` (`mpremote resume exec`),
  which skips that reset and meets the parked firmware; the armed watchdog then resets the board,
  cause WDT, record 21 (`tests_scripts/test_harness_mpremote_retry.py` pins both, and that every such
  read uses it). Tests that observe the real boot sequence use `hard_reset()` + `tail_log()`.
- **A device script's heap reading is taken inside `main.py`'s aged heap, so a standalone figure and
  an in-suite one are not comparable**: freshly flashed, the heap probe read 95,104 B and passed;
  deep in a suite the same firmware read 28,864 B and failed, with `free` unchanged to 0.2 %.
  **Any heap figure states its suite position, or it is not a comparison**
  (HEAP_FRAGMENTATION_MEASUREMENTS.md §M3.9).
- **Never poll a live system with `board.exec()`/`is_reachable()`.** `mpremote`'s `enter_raw_repl()`
  sends Ctrl-C plus, by default, a real Ctrl-D `machine.soft_reset()` before running anything, so
  each poll resets the heap and wipes the state being waited on. A liveness poll uses the passive
  `Board.is_device_present()` (opens and closes the serial port, sends nothing); inspecting live state
  takes a passive method too (a REST or network-level check, or a code-level trace).
  `is_reachable()` stays `mpremote`-based deliberately, for the few callers specifically testing that
  reset mechanism itself (e.g. the flash tier's own connection-stability test) — see both methods'
  own docstrings in `harness.py`.
- **`machine.soft_reset()` keeps `time.ticks_ms()` counting** (free-running); a raw-REPL entry stops
  `main.py`, and the watchdog then resets the board, which zeroes it - so the rollover check observes
  over REST only (`bench/test_ticks_ms_rollover.py`).
- **The off-subnet spoofing test** (`bench/test_hotspot_role_reversal.py`) sends a hand-built
  datagram through a raw socket under a named sudo rule (`tests_hardware/spoof_udp.py`,
  Prerequisites item 2).
- **`nmcli -g IP4.ADDRESS` returns a CIDR-suffixed address, `IP4.GATEWAY` a plain one**
  (`bench_control.BenchBridge.own_ip_on()`/`gateway_ip()`).
- **The captive-portal redirect works on silicon** (2026-09-03, the `dev` build of
  `scripts/build_firmware.py dev`): over the real hotspot link `GET /generate_204` returned `302`
  with `Location: /`, `GET /` served the site (`200`), the BMP3xx, SCD30 and SGP40 read plausible
  values, and a 6.5-minute window after it showed no error on any module, the watchdog armed
  throughout.
- **A real phone can show no captive-portal "Sign in to network" prompt while the DUT answers every
  probe correctly** (2026-09-03, Samsung Galaxy A54 5G / One UI 8.5: "No internet" in the WiFi list,
  no popup, while the DUT answered every probe host with `302`/`Location: /` and spoofed every
  hostname, SPECIFICATION.md Part A.5). The likely causes are phone-side: Android's Private DNS
  (DNS-over-HTTPS) bypasses the DUT's DNS spoofing for the connectivity check, so turn it off or set
  it to "Automatic" first; and Android caches a "no internet" verdict per SSID (`"SensorNode"`, the
  config default, seen failing in earlier bench runs), so forget the network and rejoin.
- **The standard board state holds `DebugLevel` 5; boot oracles need at least 3, and the session
  fixtures check the level before the first test.** The tier's log-based synchronization reads
  one-time-per-`setup()` lines (`harness.BOOT_COMPLETION_MARKERS`, read through `wait_for_boot()` and
  `boot_lines()`) and `asy_wifi_service.py`'s `pr.one()` lines, all printed at `DebugLevel` >= 3
  (`asy_print_log.py`'s `_LOG_ONCE`); `test_real_ntp_sync_succeeds_over_genuine_udp` needs
  `asy_ntp_client.py`'s `pr.all()` lines at 5. The one-time lines print in the boot's first second, which a
  reset's USB gap can hide, so both helpers also take SYSTEM's per-second `System uptime:` line at 5 when it
  falls below the line before it (a capture that spans the reset), and `wait_for_boot()` also takes its first
  uptime line when that value is within the wait's own elapsed time plus `_FRESH_BOOT_UPTIME_SLACK_S`; on a
  capture of one boot alone, `boot_lines()` has only the markers. At the shipped `DebugLevel` 0 none of
  these print, so a board left there reads as a dead link. The standard-state fixture stops such a session at its
  start naming the level, or repairs it with `--repair-standard-state` ("Prerequisites").
- **WS2812 bit timing is specified in `datasheets/ws2812/WS2812.pdf` p.4** ("Data transfer time":
  T0H 0.35 us, T1H 0.7 us, each +-150 ns; reset low above 50 us). The manual
  `test_real_ws2812_neopixel_signal_timing` compares a scope or logic-analyzer trace against it when
  one is at hand, colour correctness by eye otherwise; automating it needs a logic analyzer the
  bench does not have (no test hardware is bought, owner, 2026-09-22).
- **A stale AP-side station entry is what makes a reconnect after a hard reset fall back to hotspot
  mode** (the Workarounds table's row and "Bench traps" carry the kick). NetworkManager's AP backend
  for `br0-wifi-ap` (its internal `wpa_supplicant`, no separate `hostapd`) keeps the DUT's MAC
  associated across a reset with no 802.11 deauth: 10/10 trials fell back to hotspot with the entry
  left in place, 10/10 connected once it was cleared. Not a `src/` bug - `asy_wifi_service.py`'s
  retry and hotspot fallback behave as specified. A `picotool load` reflash reboots the board the
  same way, so the kick precedes the post-flash reconnect too. The bench fix makes a *clean*
  reconnect representative, not the field risk-free: a device WDT-looping against a real router
  meets the same stale entry with no harness to kick it.
- **A CYW43 link can report `isconnected()` true while the association is dead; the recovery is a
  power cycle or `hard_reset()`.** An independent reachability probe was judged not worth its
  complexity (owner, 2026-09-04, `655e4f9`). A real `arping` got no answer from the DUT while
  `iw station dump` showed it associated for hundreds of seconds across the whole outage, and
  `asy_wifi_service.py`'s `_wlan_isconnected_or_false()` passes `wlan.isconnected()` through, so its
  retry cannot fire on a disconnect the firmware never reports. The bench tests that meet it
  (`bench/test_network_resilience.py`'s outage and flap tests) recover by kick + `hard_reset()`
  through `recover_by_reset()` and pass, reported as recovery passes in the run's summary with the
  checks the reset skipped. Upstream: `micropython/micropython#9505` (open since v1.19.1), related
  `#9455`.
- **Before chasing a hardware or firmware explanation for an "it's flaky" real-hardware test,
  re-verify that the test's own check asks the right endpoint for the right field** - a plain `curl`
  of both endpoints side by side shows it in a minute. `GET /networking` has no `"Mode"` field; it
  exists only in `GET /status`'s nested `"networking"` object.
- **SCD30's RDY pin is real and wired**: `SCD30_Reader`'s `irq_pin` (the device TOML's), a real
  `irq_pin.irq(trigger=IRQ_RISING, ...)` in `start_timer()`, plus a staged 500 ms software
  self-healing fallback in `_irq_loop()` if the real IRQ is missed.
  `test_scd30_real_irq_edge_drives_a_real_read` (`device_scripts/scd30_real_irq_edge.py`) exercises
  it; software alone cannot tell the real IRQ from the fallback, only a scope on the pin can
  (SPECIFICATION.md E.6.6 row `scd30-rdy-irq-vs-fallback`).
- **`tests_hardware/manual/`'s files are deliberately named away from the `test_*.py` glob**
  (`manual_wifi.py`, not `test_wifi_manual.py`) - a bare `uv run pytest tests_hardware` (no path
  scoping) would otherwise collect and run them as ordinary pytest tests, each calling `input()`
  and hanging forever. `scripts/run_flash_hardware_suite.sh`/`run_bench_hardware_suite.sh` are
  scoped to avoid this either way, but the naming is the structural backstop.
- **Reusable GC/fragmentation instrumentation on silicon**: a temporary async probe task added to the
  boot entry (generated as `sensortask_<device>_main.py`, SPECIFICATION.md Part L.4, and staged as
  `main.py` by a build - add it to that staged `main.py` before flashing, and never commit the
  edit), printing a fixed-format line every N ms or every event, captured through direct `pyserial`
  reads (`Board.tail_log()`, never `mpremote exec()` against a live system). It samples
  `gc.mem_free()` and detects collections, times each collection (bracket `gc.collect()` with
  `time.ticks_us()`), and probes the contiguous-allocation frontier (a `bytearray()` at each of a
  descending candidate-size list, the largest that succeeds - `gc.mem_free()` alone cannot tell
  contiguous from scattered free space). SPECIFICATION.md Part I.1/I.3/I.5 has its results. The same
  technique applied to `UDPSocket.ready()` (a one-line `print()` on a `POLLERR`/`POLLHUP` event)
  found that rp2/lwIP does not propagate ICMP errors onto a connected UDP socket's poll state
  (2026-09-08): no such event across 6 retry cycles against a target with no
  listener. The source agrees: lwIP's `icmp_input()` counts an incoming destination-unreachable and
  drops it (`lib/lwip/src/core/ipv4/icmp.c:258-283`, lwIP `77dcd25`), and a UDP socket's state stays
  `STATE_ACTIVE_UDP` (`extmod/modlwip.c:1008`, v1.29.0), which sets no error flag in modlwip's poll
  (`:1646-1666`).
- **Open on silicon, each with the instrument that settles it**:
  - what the CYW43 firmware drops while a flash write holds interrupts off -
    `bench/test_network_resilience.py::test_a_flash_write_holding_interrupts_off_keeps_the_wifi_link`;
  - whether DMA reads update UARTRSR's error flags as CPU reads do -
    `flash/test_uart_crossover.py::test_a_break_mid_frame_fails_that_transaction_only`;
  - the SCD30's answer to a read with no command before it - `scd30_conformance_probe.py`'s
    `C03_read_before_a_command` - and after an NVM write cut by power loss -
    `manual/manual_persistence.py::test_power_loss_mid_scd30_nvm_write`;
  - the FRAM breakout's MISO idle level - `fram_conformance_probe.py`'s `A01_miso_idle_byte`;
  - the FRAM CS level at power-off - unmeasured, a limitation (SPECIFICATION.md C.3.1, `FRAM_SPI`'s
    CS pad);
  - why the hotspot join can still exhaust its five attempts with the re-verify in place -
    `bench/test_hotspot_role_reversal.py`'s `_join_dut_hotspot_with_reverify_retry()`;
  - whether the SCD30's soft reset at every boot restarts its automatic self-calibration's
    first-week search, which no reading of the sensor's interface shows (no ASC progress readout).
- **Answered on silicon, 2026-11-11 to 2026-11-13** (the dev bench, the final images):
  - the bootloader reboot loses the reset record, read back as code 2 (2026-11-11) -
    `bench/test_reset_reasons.py::test_a_bootloader_reboot_is_attributed`;
  - a RUN-pin reset clears the reset record: ResetReason 1 after one with a valid record held -
    `manual/manual_persistence.py::test_run_pin_reset_keeps_or_clears_the_record`;
  - a FRAM pull: the first FRAM log entry 36.4 s after it (W26, E102, E100; SGP40's backup in the gap
    E110), backups written again ~22 s after the replug, no reboot -
    `manual/manual_bus_electrical.py::test_fram_unplug_replug_recovery`;
  - a crossover pull: the first failed transfer 0.8 s after it (E81 initiator; E80, E22 responder),
    transfers again 0.5 s after the replug, no reboot -
    `manual/manual_bus_electrical.py::test_uart_crossover_pull_recovery`.

## Sensor, FRAM and supervisor coverage on silicon

- **Sensor plausibility** (`flash/test_sensor_accuracy.py`): the SCD30, BMP3xx and ISL29125 each read
  through their isolated driver against datasheet bounds (`scd30_plausibility_read.py`,
  `bmp3xx_plausibility_read.py`, `isl29125_plausibility_read.py`;
  `test_isl29125_real_reading_is_within_datasheet_plausible_bounds` among them).
- **VOC algorithm quality** (`sgp40_voc_algorithm_quality.py`): SGP40's raw signal and
  `voc_algorithm.py`'s Sensirion Gas Index Algorithm cannot run apart (the driver feeds one straight
  into the other), so one script covers both - it waits out the algorithm's documented 45 s
  initial blackout, then samples several readings and checks they are in range and neither frozen nor
  erratic. Deliberately a stability/sanity check, not a numerical-accuracy claim against a calibrated
  reference (that needs a human-supplied VOC stimulus - `manual/manual_sensor_accuracy.py`).
- **SGP40 sample cadence** (`flash/test_sensor_accuracy.py::test_sgp40_sample_cadence`,
  `device_scripts/sgp40_sample_cadence.py`, L3, `soak_duration`: runs under
  `scripts/run_bench_soak_tests.sh --duration short`, its window fixed at 600 s whatever the
  duration): boots the bench device's generated system over the scratch config directory
  `hwtest-scratch/`, counts SGP40 read cycles over ten minutes of the real task graph and reports
  them as facts (cycles, elapsed, lost samples, the largest gap, the gaps over 1.5 s). No pass
  threshold: the figures are the deliverable (SPECIFICATION.md M.3). No flash cycle and no
  production config file; it writes the SGP40 backup chunk and the booted modules' logs into FRAM,
  which the session start saved first.
- **FRAM backup** (`fram_manager_roundtrip.py`, `sgp40_fram_backup_restore.py`,
  `flash/test_fram_storage.py`): a chunk write/read/CRC/dual-copy round trip against the bench's FRAM
  part, and the SGP40 VOC-state backup/restore driven through `SGP40_Reader`'s production
  `_read_loop()` on its natural `BackupPeriod` schedule. A fresh boot is a fresh `FRAMManager` over
  the same chip, which lands on the chunk address a reboot's `build_system()` would ("Testing a
  driver by hand over mpremote").
- **FRAM error storage** (`fram_error_log_roundtrip.py`): `PrintLogHistoryStore` (every
  FRAM-chunk-owning module's `err_s()`/`wrn_s()` persistence) against the real chip, the same
  fresh-boot pattern.
- **FRAM write protection gates in silicon** (`fram_write_protect_roundtrip.py`,
  `flash/test_fram_storage.py`): with WPEN|BP0|BP1 set, a write is refused and succeeds once cleared;
  a read is refused too, because `_read_chunk()` writes a transient busy marker first (SPECIFICATION.md
  Part A.4's FRAM entry, asserted the same way at the mock and twin tiers); and the chip itself
  refuses, not only the driver's guard - with the cached `_wp` desynced from the still-protected chip,
  a real WREN+WRITE lands no byte. Its bench-vs-flash split is SPECIFICATION.md E.6.6 row
  `fram-write-protect-no-rest` (no REST route reaches either method).
- **FRAM command hold** (`fram_command_hold_timing.py`, flash tier): one FRAM command stays under one
  UART poll floor (80 B of 8N1 at 115200 baud, 6,944 us, SPECIFICATION.md J.6 and F.5.8), and records one
  log entry's whole chunk write, its 51 commands, for F.3's `stall.fram_entry`. It writes only its
  scratch region, the part's top 256 B, never a chunk.
- **FRAM chip-select fault injection** (`fram_cs_hijack_fault_injection_and_recovery.py`): CS
  deasserted at the driver's synchronous seam, inside a write's payload (the write never reaches the
  chip, measured on the bench, 2026-09-04), a read's payload (it never returns the real data, measured
  on the bench, 2026-09-04) and a
  write's first WREN (the driver's one WREN retry lands the write); each scenario ends with
  the chip identifying again (RDID) and a clean write reading back.
- **FRAM reset inside a write** (`fram_reset_race_during_write_seed_and_race.py` +
  `fram_reset_race_during_write_verify_recovery.py`): a real `machine.reset()` inside a write's
  payload transfer, CS still asserted; phase 2 accepts the original bytes or a prefix of the new ones,
  both guards untouched, and the driver recovering (the WEL latch the chip kept set included). A
  power loss mid-byte is out of an interpreter-level race's reach (the same class of limit as
  SPECIFICATION.md Part F.2's wedged bus).
- **The task supervisor restarts a dead task** (`flash/test_task_supervisor.py::test_the_supervisor_restarts_a_real_dead_task`,
  `system_service_restarts_a_real_dead_task.py`): a starter that dies at once is called again at
  least twice within one `_TASK_CHECK_TIME` (2 s) cycle. Deliberately stops at ~3.6s real time
  (task_errors capped at 200): a task that dies at once adds `_TASK_FAIL_INCREMENT` (100) per cycle,
  and `_TASK_FAIL_MAX` (300) would trip a reboot around the 4th cycle (~7 s), which this script does
  not test.
- **One supervisor pass with every task ended** (`flash/test_task_supervisor.py::test_one_supervisor_pass_with_every_task_ended_stays_inside_the_watchdog`,
  `supervisor_scan_timing.py`): Part N's `system.scan_budget` measured - five tasks end at once after a clean pass, and
  the 2 s sleep plus the escalating pass (four end entries and the reboot's, persisted to SYSTEM's FRAM chunk, three
  task starts) is timed between two feeds, then the countdown from the last feed to the reset, which is stubbed, so the
  board keeps running. Zero flash wear; the chunk is cleared at both ends, the raw FRAM dump saved first.
- **The running graph under a fault** (`flash/test_task_supervisor.py`, each over the bench build's scratch config):
  every failed arm of an emptied alarm pool handled in place (`timer_pool_empty_beside_the_graph.py`), every wall-clock
  consumer following a stepped RTC (`clock_step_under_the_running_graph.py`), and `main()` ending or a supervisor raise
  stopping every feed until the watchdog resets (`watchdog_fault_in_the_running_graph.py`).
- **Real clients' request heads** (`bench/test_request_head_capture.py::test_real_clients_request_heads_fit_the_devices_head_guard`):
  Part N's `web.max_header_lines` and `web.max_head_bytes` measured - the bench host's Python, curl and Playwright
  Chromium each load a page from a local capturing listener, and each head stays inside the device's guard; the
  result note carries every client's largest head. It needs node and the repository's `node_modules` (`env --tier
  generic`); the board is only read by the tier's own fixtures, so it writes nothing.
- **REST on the normal network** (`bench/test_rest_endpoints_over_sta.py`): the website served over
  the bridge, and `GET /measurements` plausible for every sensor the bench TOML declares
  (`_load.measurement_findings()`, `tests_hardware/plausibility_bounds.py`).
- **Config pushes over REST** (`bench/test_sensor_config_push_over_real_hardware.py`, the counterpart
  of `tests/test_setter_microdot_integration.py`): BMP3xx oversampling and filter pushed, answered
  `Valid` (the I2C write landed), read back and restored in a `finally` (the bench's persisted config
  changes meanwhile); ISL29125 `Resolution`/`Range`/`IRCompOffset`/`IRCompAdjust` the same way, with
  `RangeAuto: False` pushed beside `Range`, since under auto-ranging the chip's range bit is the state
  machine's and `_read_sensor_dict()` omits `Range` from a live snapshot; SGP40's `ResetVOC` and
  ISL29125's `Calibrate` commands; `PUT /notification`'s `PauseTime` counting down to 0, read from
  `GET /status`'s `"notification"` section (buildgen's `_notification_status()`); and SCD30's
  altitude while ambient pressure is 0, behind both SCD30 write gates. The `ResetVOC` push is thin:
  it never asserts the reset's own effect, and says so in its comment.

**Not automated**: numerical accuracy against a calibrated reference for any sensor (a human
supplies the known stimulus, `manual/manual_sensor_accuracy.py`); WS2812 signal timing beyond the
manual check (see the WS2812 bullet above); a power loss during `FRAMManager`'s chunk logic (only
`manual/manual_persistence.py`'s raw-persistence power-loss tests cut real power).

## Network-robustness tests

`bench/test_network_resilience.py` with `bench_control.BenchBridge`'s fault primitives and
`rogue_udp_responder.py`; what each injection reaches is "What the network-fault injections reach".

- **WiFi outage and flap while connected**: once `_conn_phase` is `_PHASE_STA_ESTABLISHED` (these
  tests depend on `dut_ip`), `asy_wifi_service.py`'s `_on_sta_disconnected()` takes the "retrying
  previously successful connection in one minute" branch, which never increments
  `_connection_failures` and never reaches the hotspot fallback - a different branch from the
  never-yet-connected DUT of SPECIFICATION.md Part E.6.4's role reversal. The unresponsive-NTP case is
  `test_real_ntp_handles_a_genuinely_unreachable_server_without_crashing` (`bench/test_wifi_networking.py`).
- **NTP and DNS answering garbage**: `redirect_udp_port_to_local()`/`clear_udp_port_redirect()`
  redirect the port to a rogue responder answering every query with a fixed non-protocol payload.
- **Socket limit**: `test_connections_at_and_above_the_real_socket_limit_degrade_cleanly` holds the
  build's `max_connections` (6 on `dev`) slots open with bare `connect()` calls - `_serve()` counts a
  connection as its handler starts, before any byte is read - and the next one is closed with no
  response written.
- **Nonsense GET and PUT**: a 404 shaped per `_ERROR_STATUSES`, a malformed raw JSON body (a raw
  socket: `http_client.fetch()` serializes only valid JSON), a 413 over `max_content_length` (2048),
  and valid JSON with nonsensical values (wrong type, out of range, an unknown sensor key), each
  landing where `_body_as_dict()`/`asy_base_classes.py`'s `_set_dict_cfg()` put it and none reaching
  `ConfigManager.write_config()`, so nothing needs restoring.
- **Slowloris and abrupt disconnects**: `_serve()`'s outer `asyncio.wait_for_ms(...,
  self._outer_cap_ms)` (`web.outer_cap_s`, 15.0 s) bounds a Slowloris-paced client. A single stall
  over 5 s hits `_TimeoutStreamProxy`'s per-call read timeout instead, which Microdot absorbs by
  writing an ordinary response, so the test trickle-feeds one header line every 3 s, 6 of them: each
  gap under the 5 s per-call timeout, the 18 s total over the 15 s outer cap.

**Every hardware test that injects a fault also calls `assert_no_task_ended()`** before its
closing reset: a task ending under a routine fault (and the reboot three of those cost) lands in the
FRAM-kept SYSTEM log even across a `hard_reset()`, where a "no Traceback" check sees nothing - which
is how an NTP give-up restarting a task every minute passed this tier (SPECIFICATION.md C.7.2).
`tests_scripts/test_bench_no_task_ended_completeness.py` fails a fault test that skips it. Its scan
covers test functions and `Test*` methods, the helpers and fixtures a test reaches by name (a fixture
that injects counts unless it asserts in its own teardown), and the flash tier's fault-making device
scripts, which report their own SYSTEM logger as a fact for the host to assert; the session's
stale-credential recovery downs the AP only to join the DUT's hotspot and is not a fault.

**A fault-injecting test resets the REST-exposed error history before the fault, asserts the
specific expected entry on the right module's log afterwards, and resets again**, so the bench's
live history never keeps a test's own provoked faults. `error_log_helpers.py` is the primitive, and
its re-exported `code("E"|"W", NAME)` (`tests/_error_codes.py`, from `buildgen/error_catalog.json`)
names the expected entry. `/status`'s `errcount` shape (`asy_webserver_service.py`'s
`_write_errcount_entry()`: `{"counter": int, "history": [{"num": int, "type": "E"|"W"}, ...]}`) is
not `asy_print_log.py`'s raw `get_log()` shape that `device_scripts/` files read. Where no entry is
due the test asserts the log stays empty: a 404 or 405 from `_shaped_error_handler()` and the
`_body_as_dict() is None` path log nothing, while `_serve()`'s drops log one `HTTP_REFUSED` warning
per connection refused at the ceiling and one `HTTP_BAD_HEAD` per refused request head, each counted
in `/status`'s `HTTPDropped`. One case (`test_abrupt_disconnect_mid_response_does_not_hang_the_server`)
has a timing-dependent entry (whether the server is still mid-write when the client's RST lands) and
asserts none. In `bench/test_hotspot_role_reversal.py`, `test_malformed_truncated_packet_is_silently_dropped`
asserts `DNSSRV` stays empty (a garbage datagram is a real `(data, addr)`, never the `DNS_RECV_FAILED`
(`W42`) path, which needs a `(None, None)` `recvfrom()`), and
`test_malformed_http_request_over_real_wireless_degrades_cleanly` allows exactly one `HTTP_BAD_HEAD`
warning, asserts `HTTPDropped` counts the refused head, and fails when the server neither answers
with a 400-class status line nor closes within its read timeout. Outside the rule: the role
reversal's association and DHCP churn tests (radio-observable only, no DUT-side module logs them) and
the flash tier's `timer_alarm_pool_exhaustion.py`/`scheduler_saturation_drop.py` (no REST on the
flash tier, no `src/` logger involved; each asserts its exact outcome in its own facts).

## Harness mechanisms: `dut_ip()`, the hotspot join, the manual runner

**`conftest.py`'s session-scoped `dut_ip()`** gates nearly every bench test:
- it kicks the AP's stations and resets the board (`harness.kick_then_reset()`), then waits for
  `asy_wifi_service.py`'s `pr.one("WLAN connection established")` line passively through
  `board.tail_log()` (printed at `DebugLevel` >= 3), or, given `--dut-ip`, for `GET /status`
  answering at that address (the console drops what it prints between two tails), with one bounded
  reset retry through `recover_by_reset()`;
- when neither connects, the DUT holds stale stored credentials (a bridge recreated with a new
  SSID/password) and falls back to its own hotspot every time: `_recover_stale_dut_credentials()`
  joins that hotspot, PUTs the bench AP's current SSID/password (`BenchBridge.ap_password()`'s
  `--show-secrets` read), restores the bridge and resets again - the mechanism stage 6 of
  `test_hotspot_role_reversal.py` exercises;
- the address is read with one `board.exec()`, always followed by a kick and `hard_reset()` (an exec
  stops `main.py`; "What each tool writes to the board"), and the fixture then waits for real HTTP on
  that address, since the link comes up before the webserver serves. The hotspot fallback's
  "Permanently no WLAN connection - activating hotspot!" is a `wrn_s()` warning (level 2), which the
  fixture does not watch.

**The hotspot join retries on nmcli's rescan**: `is_ssid_visible()` being True does not guarantee
`nmcli device wifi connect`'s own rescan still sees the hotspot a moment later, across several
consecutive attempts (2026-09-08). `_join_dut_hotspot_with_reverify_retry()` re-verifies visibility
for up to 30 s between attempts and takes a `TimeoutError` there as the next join's business.
Exhausting the attempts even so is an open finding ("Open on silicon", above). The join keeps its
five attempts on that nmcli race, each retry a recovery note (owner, 2026-10-20: 'The Hotspot remains untouched.'). An AP-reconfiguration theory was ruled
out against the pinned source: an AP that is up reports `STAT_GOT_IP`, so `_run_hotspot_mode()`
only manages its stations, and `_configure_hotspot_ap()` configures only an inactive AP.

**Run the manual tests through `__main__.py`, never `runner.py` directly**
(`uv run python tests_hardware/manual/__main__.py`, or `scripts/run_manual_hardware_tests.sh`):
running `runner.py` loads it as `__main__` while every `test_*.py`'s `from runner import register,
...` imports a second instance named `runner`, each with its own `_REGISTRY`, so `main()` reads an
empty registry - exit 0, no output, `--list` empty. **Manual-test conventions**
(`tests_hardware/manual/runner.py`'s helpers): `print_instruction()` before the window that depends
on it, not after. Timing is human-executable on a breadboard test device (tens of seconds, chosen per
what is physically involved), never a value carried over from an automated or simulated test.
`confirm()` waits for explicit human confirmation wherever the console survives the step;
`countdown()` is for power-cycle cases where it does not. `state_expected_outcome()` prints what
"passed" looks like before the script's own verdict, for tests ending in a human visual or
instrument check.

## Bus-hazard coverage on silicon

Every generic mock/twin bus-hazard scenario type has a real-hardware equivalent on whichever bus
`dev`'s wiring makes it apply to (the SCD30 under its write budget), and flash-tier bus-hazard
coverage is a subset of the bench tier's (project owner; SPECIFICATION.md Part E.6.6 lists the
exceptions, CLAUDE.md the four-tier rule). `dev`'s topology: i2c0 the BMP3xx alone, i2c1 the SCD30,
SGP40 and ISL29125.

- **Same occupant, write against its own read**: the `*_same_device_*` device scripts and
  `bus_concurrency_same_device_scd30.py`, one per occupant.
- **All of i2c1's occupants reading at once**: `isl29125_cross_device_concurrency.py`.
- **One occupant's config write against its siblings' reads** (`flash/test_bus_concurrency.py`):
  `test_isl29125_config_write_does_not_disturb_concurrent_sibling_reads`
  (`bus_concurrency_isl29125_write_vs_siblings.py`) writes the ISL29125's volatile config register
  (no NVM budget, FN8424 p7) over an explicit spread of pre-write delays (`_WRITE_DELAYS_MS =
  (5, 15, 40, 80, 120)`, each `_DELAY_REPEATS` = 2 times) while the SCD30 and SGP40 read: on silicon
  an elapsed-time delay stands in for the mock tier's `asyncio.sleep(0)`-count offset, which means
  nothing against real bus timing. Part of the routine group.
  `test_scd30_config_write_does_not_disturb_concurrent_sibling_reads`
  (`bus_concurrency_scd30_write_vs_siblings.py`) writes `set_temperature_offset()`, a real NVM write,
  so it runs behind `persistence_write` + `scd30_extra_write` (`--allow-persistence-write` and
  `--allow-scd30-extra-write` together, "Persistence-write gating" below) and spends two NVM writes
  (the offset and its restore), never folded into the routine group's at most one (`scd30_measuring`'s
  start command; SPECIFICATION.md Part C.8's write-budget rule). The one write starts at the head of an
  SGP40 round, inside that sibling's session and ahead of its command (`write_in_sgp_round`, asserted);
  the budget leaves no room for a multi-offset sweep. Both tests credit "not disturbed" only once a
  sibling read's window overlapped a write's (`overlapped_reads`).
- **General call against concurrent siblings**:
  `test_sgp40_general_call_reset_does_not_corrupt_concurrent_scd30_and_isl29125_transactions`
  (`sgp40_general_call_reset_hazard.py`) reads both non-broadcasting siblings while SGP40's
  `initialize()` fires its general-call broadcast, as the mock tier's
  `scenario_general_call_does_not_disturb_concurrent_siblings` runs against every non-broadcasting
  occupant.
- **Address sweep and the lone-occupant general call**: `bus_topology_autodetect_and_hazard_sweep.py`
  sweeps the known addresses (the rendered `BENCH` dict's, ISL29125's `0x44` among them) and the
  reserved ranges, and its self-hazard check reads a bus's lone known device clean while broadcasts
  race its reads. `flash/test_bus_concurrency.py::test_bmp3xx_alone_survives_a_general_call`
  (`bmp3xx_alone_survives_a_general_call.py`, L3, ungated; no write, no flash cycle: volatile
  registers only, restored by a soft reset at the end) checks that the BMP3xx keeps its
  configuration, chip ID, power-control bits and readings through them, with no power-on flag
  raised. It has no bench counterpart (SPECIFICATION.md Part E.6.6, row `flash-only-bus-checks`).
- **The bench tier under API load** (`bench/test_bus_concurrency_under_api_load.py`):
  `test_isl29125_config_write_does_not_disturb_concurrent_sibling_reads_under_api_load` pushes
  `PUT /sensors {"ISL29125": {"Resolution": ...}}` alternating both valid settings while `GET /sensors`
  hammers, the original restored in a `finally`: every write answered `Valid`, the readers' floor met
  with schema-sane bodies, the bus logs clean. Each `GET /sensors` reads the ISL29125's and SCD30's
  config from the chips over i2c1, so sibling reads run beside the writes, but nothing host-side
  shows one overlapping a write: that proof stays with the flash test's `overlapped_reads`.
  `test_scd30_config_write_does_not_disturb_concurrent_sibling_reads_under_api_load` reaches the
  SCD30's NVM through its chip store (`_set_mgr_cfg()`, compare-before-write), spending two offsets
  and the restore behind the same two flags as its flash counterpart.
  `test_bmp3xx_config_write_does_not_disturb_its_own_concurrent_reads_under_api_load` alternates
  `PresOvers` against the same sensor's GET reads and restores it. The GET workers check each
  `/sensors` config field against its driver's schema (`_load.schema_sanity_findings()`), and after
  the load each `/measurements` reading, SGP40's VOC within `[0, 500]` among them, is held to
  `tests_hardware/plausibility_bounds.py` (`_load.measurement_findings()`).
- **SGP40's general call has no bench counterpart** (SPECIFICATION.md Part C.8's structural
  exception 2, E.6.6 row `sgp40-general-call`): the `ResetVOC` the workers PUT reaches
  `reset_voc()`, a software-only reset of the VOC algorithm; the broadcast fires only from
  `SGP40_I2C._reset()` inside `initialize()`, at driver setup or a supervisor restart, which no REST
  field reaches.
- **Open**: the SCD30's same-device write against its own read has no bench counterpart - `PUT
  /sensors` reaches its NVM through the chip store, so one is added behind `persistence_write` or
  its wear reason is listed. The write-vs-siblings tests, the explicit delay sweep, the two-sibling
  general call, the ISL29125 address-sweep entry, the three bench write tests and the SGP40 VOC
  check have not yet run on silicon.

## Tier parity beyond the bus hazards

Every domain's real call chains - UART, WiFi/network/NTP/DNS, FRAM/memory/reboot/watchdog, and
webserver/notification/config-push - reach the tier each test claims, beyond the bus hazards (owner,
2026-09-15; owner, 2026-09-29: 'It has no priority in terms of order now, it's only highly important
to be applied.'); no test swaps a real hardware trigger for a software-only one, as the SGP40
`ResetVOC` worker would if trusted.

- **Exceptions**, rows of SPECIFICATION.md E.6.6: `ws2812-no-readback` (`LightCmdLED` and the WS2812
  timing), `scd30-rdy-irq-vs-fallback`, `fram-write-protect-no-rest`, `uart-fault-catalog`, `ntp-responder-modes`.
- **Scratched (agent, 2026-09-25)**: a periodic SET wired into the bench UART exerciser's live load,
  and a hard-reset-recovery bench test for NOTIFY's FRAM chunk like SGP40's, which needs an observable
  "a fresh write just completed" signal NOTIFY lacks: each would change `src/` for the test alone, and
  the flash tier already proves a FRAM chunk's reset-raced write is all-or-nothing.
- **Traced end to end and genuine**: the WiFi bench workers (`ap_down`/`ap_up`, UDP block and
  redirect, `netem`, the role reversal, the spoofed NTP source), each reaching the mechanism its name
  claims; the wedged-WiFi `isconnected()` backstop's automated bench coverage with timing data
  (`bench/test_network_resilience.py`); UART's flash-tier fault-injection and idle-poll-rate scripts,
  and the mock/twin/flash parity of the happy path and one-sided silence; BMP3xx and SGP40's REST
  config push by GET-after-PUT readback; the bench mempause test and the flash/bench memory-stress
  split.
- **The boot entry and the system service** (setups, task start, timers, stagger, supervisor, feeds,
  shutdown, reset records, error counts), traced from `src/` through every tier: each silicon script
  drives real product objects from a real trigger - the boot phases, every reset code but the power
  cut's 1, both boot-entry handlers, the restart, both escalations, the shutdown's steps and feed gaps,
  a held SDA across both resets and its one report, `ResetErrors` refused, an escalation entry that
  never ends, `ConfigFaults`, the random boot signature, the trigger spacing, a reboot at a boot's first
  answer, the failed arms of an emptied alarm pool, `main()` ending and a supervisor raise inside the
  running graph, a stepped RTC. L1/L2 only: a dropped one-shot fire's watchdog reset (each half on
  silicon apart); gaps until written: the unfed boot stretches' and the supervisor scan budget's figures.
- **The webserver and the link under the bench's load**: a negative Content-Length, each refusal at the
  ceiling counted once in `HTTPDropped`, four zero-think-time readers' floor and the cap after them, and
  FRAM log writes and a config flush during link traffic. The scriptable NTP responder's modes are an
  accepted limitation (owner, 2026-11-06; E.6.6 `ntp-responder-modes`).

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
| `scd30_extra_write` | `--allow-scd30-extra-write`, only together with `--allow-persistence-write` | deselected at collection | the four tests' further SCD30 NVM writes, up to 12 (the budget table's row): with both flags a session spends up to 13 owned writes on `dev`'s SCD30, plus at most one start command, what the tests carry (owner, 2026-10-21: "option a", asked "Cap the SCD30 NVM writes the extra-write flag admits?"); always carried with `persistence_write` |
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
| `--allow-persistence-write`, flash tier | flash filesystem | `test_config_floats_round_trip_unchanged`: 1 scratch write (its repeat answers `Unchanged`); `test_isl29125_mechanism_envelope_holds_across_range_resolution_and_calibration`: 7 scratch writes (also needs `--allow-neopixel-sweep`); `test_link_transactions_during_config_writes_are_recorded`: 5 scratch writes per CRC mode; `test_config_value_survives_a_genuine_hard_reset`: 2 (the scratch file's defaults, then the marker); `test_config_reset_deletes_every_config_file_and_reboots`: the scratch build's defaults per store, one damaged file, `resetconfig`'s deletions; `test_a_damaged_config_file_is_repaired_and_listed_as_a_config_fault`: the scratch build's defaults per store, one damaged file and its repair; `test_a_hung_shutdown_step_ends_in_a_watchdog_reset`: per command, the scratch build's defaults per store and the deletions until the hung step; `test_flash_write_loop_gap_is_recorded`: 1 scratch write (create, 1 KiB, close, remove) |
| `--allow-persistence-write`, bench tier | flash filesystem | 2 each (the change and its restore): `test_isl29125_gain_ratio_survives_a_real_reboot_as_an_ordinary_config_value`, `test_representative_put_round_trips_over_the_hotspot_link`, `test_real_hard_resets_during_natural_fram_backup_activity_recover_cleanly`, `test_garbage_ntp_host_via_rest_config_degrades_and_recovers_cleanly`, `test_garbage_ssid_via_rest_config_is_handled_gracefully`, `test_console_output_with_a_non_reading_usb_host_never_starves_the_watchdog` (`DebugLevel` 0, then 5), `test_a_flash_write_holding_interrupts_off_keeps_the_wifi_link`, `test_bmp3xx_oversampling_and_filter_push_over_real_rest_and_readback`, `test_isl29125_resolution_range_and_ir_comp_push_over_real_rest_and_readback`; up to 5 each (4 changes and the restore): the ISL29125 and BMP3xx config-write arms of `bench/test_bus_concurrency_under_api_load.py`; 1: `test_a_wrong_password_over_the_hotspot_reopens_the_hotspot` (a well-formed wrong password, which the next test restores); 1: `test_fram_log_writes_and_a_config_flush_during_link_traffic_under_api_load` (`GMTOffset`, local time only, toggled between its default and the default plus a minute, so no run spends a restore); 1: `test_real_credentials_put_succeeds_and_confirms_accepted_values`; 0: `test_a_second_failed_streak_goes_silent_and_links_on_a_later_attempt` (the marker is its AND-gate on the previous test's write); `test_config_reset_over_rest_brings_back_the_defaults`: `resetconfig`'s deletions, the reboot's one defaults write per file, one restore write per saved file |
| `--allow-scd30-extra-write` (with `--allow-persistence-write`) | SCD30 NVM | flash `test_scd30_config_write_does_not_disturb_concurrent_sibling_reads`: 2 (the offset and its restore); flash `test_scd30_argument_reaction_is_recorded`: up to 3, restored in the script; bench `test_scd30_config_write_does_not_disturb_concurrent_sibling_reads_under_api_load`: up to 3 (2 offsets and the restore); bench `test_scd30_altitude_takes_effect_while_ambient_pressure_is_zero`: 4 (`AmbPres` 0, the stepped `Altitude`, and both restores); up to 12 in all |
| manual (`scripts/run_manual_hardware_tests.sh`; each step states its writes before its `confirm()`) | flash filesystem | the flash config across a power cycle: 2 (`WarnCO2` and its restore); the power cut mid config write: up to 20 scratch writes and 1 removal per round, 3 rounds; the shutdown-command power cuts: `resetconfig`'s deletions, the next boot's one defaults write per file, one restore write per saved file (`config_files_restore.py`; `erasefram` is FRAM, outside the budget) |
| manual | SCD30 NVM | the NVM across a power cycle: 2 (`MeasInterval` and its restore); the power cut mid NVM write: up to 21 (20 changes and the restore), plus 1 for the `PUT` that puts `MeasInterval` back after the boot when the cut left it changed |
| `--allow-flash-cycle` | flash (reflash) | `test_real_uf2_reflash_and_boot_smoke_test`: 1; `bench/test_uart_link_crc16.py`: 2 (the CRC16 image and back); `test_ticks_ms_rollover_is_survived`: 1 (the tick-offset test image; the next round flashes its own image), counted in the rollover round's budget |

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
backstop of the implicit FRAM-wiring rule (SPECIFICATION.md A.7): a shipped firmware asking for more FRAM than its
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
