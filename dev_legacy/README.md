# dev_legacy

Two things live in this directory:

1. **The current, maintained single source of truth for the physical "dev" RP2040 bench unit** —
   wiring, chip identities, confirmed-working status, current bench state, and the mpremote
   workflow for testing `src/` drivers against it. Kept up to date as real-hardware sessions learn
   more; historic debugging narrative is pruned once resolved, not accumulated (see CLAUDE.md's
   documentation-maintenance working agreement).
2. **A historical, frozen-in-time snapshot** of this same unit's onboard filesystem as it was on
   2026-08-27 (the "Legacy on-device filesystem snapshot" section at the end) — kept as reference
   for `src/` promotion work. Not itself reviewed, promoted, or covered by lint/type/test config.

For a **structured, repeatable** automated test tier against this same kind of bench unit (rather
than the ad hoc/exploratory sessions this file documents), see **`tests_hardware/`** at the repo
root (`tests_hardware/README.md`) — a `pytest`-based flash/bench suite plus a separate manual-test
runner, built on the same `mpremote`/bridged-AP access this file describes.

As of 2026-08-28 this unit runs a **custom-built firmware** based on **MicroPython 1.28.0**
(matching `toolchain/versions.toml`'s `[micropython] ref` — the refactor/`src/` target, not the
deployed-fleet 1.26 pin), with every `src/*.py` module plus `ext/microdot.py` **frozen in** (see
"Frozen firmware for a full-system bring-up" below) — importable directly with zero mount and
near-zero heap cost. Its onboard **flash filesystem (VFS) is still empty** — no autostart script,
no config files; frozen modules live in flash/XIP, not the VFS, so `os.listdir("/")` genuinely
still returns `[]` (confirmed directly). No longer represents deployed-fleet (1.26,
`python/`/`modules/`) behavior. Used as a live test bench for the promoted `src/` drivers and the
full assembled system, exercised via `mpremote mount` for whichever entry/wiring script is under
test (see "Testing real hardware from a session" below) rather than by flashing user files onto it.

## Hardware wiring (single source of truth)

Derived from the original 2026-08-27 snapshot's code, then verified against the actual physical
board by the project owner — this table is the authoritative source for wiring this specific
unit, not any code that references it.

| Bus | Pins |
| --- | --- |
| I2C0 | scl=GPIO13, sda=GPIO12, freq=50000 |
| I2C1 | scl=GPIO15, sda=GPIO14, freq=50000 |
| SPI0 | sck=GPIO2, mosi=GPIO3, miso=GPIO4 |

| Device | Bus | Pins / notes |
| --- | --- | --- |
| FRAM | SPI0 | CS=GPIO5 (physical pin 7) — chip is a **MB85RS2MTA**, 256 KB (`max_size=0x40000`); deployed `wozi` uses CS=GPIO1, an **MB85RS64V**, 8 KB (`max_size=0x2000`) |
| BMP3xx | I2C0 | address 0x77 (driver default); physically a **BMP384** |
| SGP40 | I2C1 | address-only (0x59 default), no extra pins |
| SCD30 | I2C1 | interrupt/RDY = GPIO11 |
| MPRLS | I2C0 | reset_pin=GPIO10, eoc_pin=GPIO7 |
| ISL29125 | I2C1 | irq_pin=GPIO6 |
| BME688 (BSEC) | UART0 | tx=GPIO16, rx=GPIO17, 115200 baud — not I2C/SPI |
| Neopixel | — | **GPIO18** (physical pin 24); deployed `wozi` uses GPIO15, a different pin again |
| SHTC3 | — | **not present** on this board (some legacy code wires it, but it's not actually connected) |

### Bench-only jumper: UART0↔UART1 crossover (kept for future tests)

GP0 (physical pin 1) is jumpered to GP9 (physical pin 12), and GP1 (physical pin 2) is jumpered to
GP8 (physical pin 11) — confirmed by the project owner directly on the board. This is a TX↔RX
crossover between the board's own UART0 and UART1 peripherals, used to test two `UART_Comm`
instances talking to each other on the same board rather than to any external device. Not a
sensor/peripheral wiring — a deliberate bench-only loopback jumper, kept in place for further
tests. (`dev_legacy/uart_test.py` in the legacy snapshot below exercises exactly this: UART0
tx=GPIO0/rx=GPIO1 and UART1 tx=GPIO8/rx=GPIO9, matching the physical crossover.)

## Confirmed working — real-hardware test session (2026-08-28)

All currently-wired peripherals were exercised end-to-end against the promoted `src/` drivers on
this bench unit:

- **Neopixel** (GPIO18): confirmed at both the raw `neopixel.NeoPixel` level (red/green/blue/off)
  and through the real `NeopixelDriver` class — direct pixel writes, and three chained 10s
  dim-up/dim-down pulses fired back-to-back via `request_signal()`, correctly serialized in order
  by its own internal lock/event, with no explicit sequencing needed by the caller.
- **SCD30** (I2C1, IRQ=GPIO11): CO2/temperature/humidity all read correctly through the real
  `SCD30_Reader`. The interrupt-sync startup (`scd_init_irq()`'s real-edge + self-healing
  500ms-timer fallback) was verified reliable under every combination of prior data-ready-flag
  state — cleared or left stale before a stop/restart cycle — always resyncing within ~3s and
  never hanging. `stop_continuous_measurement()` shows one grace-period reading completing roughly
  1s after the stop command before the sensor genuinely goes idle (not documented by Sensirion,
  but consistent with an in-flight conversion finishing) — expect this if a future test polls
  data-ready right after issuing stop.
- **SGP40 + VOC algorithm + FRAM** (I2C1): raw/VOC-index reads confirmed; the algorithm's
  documented 45-cycle blackout (`VOCAlgorithm`'s `_VOCALGORITHM_INITIAL_BLACKOUT`) was observed
  exactly — `VOC=0` through cycle 46, real values from cycle 47 on, climbing as the raw signal
  settled. Backup-to-FRAM, restart-from-scratch, restore-from-FRAM (immediately continuing from
  the restored state rather than cold-starting), and reset-including-FRAM (verified via a third
  fresh reader finding nothing to restore) were all confirmed through the real
  `SGP40_Reader`/`AsyFramManager` code paths.
- **FRAM** (SPI0, MB85RS2MTA, 256 KB): full-range write/read-back swept clean across all
  power-of-two address boundaries, confirming the `_KNOWN_PRODUCT_IDS`-keyed chip-identification
  fix (see `SPECIFICATION.md` Part C.3.1) and the driver's own addressing scheme both handle the
  256 KB chip correctly, not just the smaller 8 KB one.
- **BMP384**: breakout had a broken 3.3V trace, running parasitically off the I2C pull-ups until
  repaired 2026-08-28. Retested immediately after with the unmodified, promoted
  `src/asy_bmp3xx_driver.py` — 5/5 clean reads, no `EIO`, stable values (~999.1-999.3 hPa,
  ~26.2°C). The broken trace was the sole root cause; driver code, MicroPython version, and the
  RP2040 I2C peripheral were never at fault.

## Confirmed working — full assembled system bring-up (2026-08-28)

Beyond the per-peripheral checks above, a `sensornode-dev` wiring (this bench unit's real pins,
per the table above) assembling the exact same top-level functionality as the deployed `wozi`
config — SCD30, SGP40+VOC, BMP3xx, Neopixel, FRAM, WiFi/NTP/DNS, REST webserver — was built and run
in full, via the frozen-firmware approach below (watchdog deliberately spared as a debugging aid,
not a standing bench convention). Confirmed end-to-end over the real REST API: every sensor reading
and storing on its own independent cycle, WiFi associating through the bridged AP below and
reaching real NTP, and a real SGP40→FRAM VOC backup firing on schedule. Also exercised the real
`DebugLevel` live-reconfiguration mechanism (`PUT /system {"DebugLevel": 5}`) end-to-end against
the running system, confirming it reaches every module's own logger with no reboot needed.

## Testing real hardware from a session (mpremote workflow)

`scripts/mpremote_connect.sh` (see README.md's "Real hardware access" section) wraps `mpremote
connect <device>`; `exec`/`run`/`mount` stay RAM-only, `cp`/`rm`/`mkdir`/`rmdir` write flash. This
section covers testing one driver (or a partial closure) at a time; for assembling the *whole*
system together, see "Frozen firmware for a full-system bring-up" below instead.

- Since this bench unit's flash is empty, a `src/` module needs `mpremote mount src <exec|run>
  ...` (or `mount` a directory of precompiled `.mpy` files, see below) to become importable —
  nothing needs to be flashed onto the device first.
- **Light dependency closures** (e.g. `asy_neopixel_driver.py`, or
  `asy_fram_driver.py`+`asy_spi_driver.py`) import fine straight from mounted raw `.py` source.
- **Heavier closures** (anything pulling in `asy_fram_manager.py`, `asy_scd30_driver.py`, or
  `asy_sgp40_driver.py`+`voc_algorithm.py`) can raise `MemoryError` mid-import even with ~200 KB
  free — importing over a remote mount compiles from source on-device with no bytecode caching,
  unlike the frozen-bytecode firmware build. Fix: precompile the needed closure to `.mpy` with the
  toolchain's own `mpy-cross` (`$HOME/pico-toolchain/micropython/mpy-cross/build/mpy-cross`,
  version-matched to the device's firmware — check `mpy-cross --version`'s `mpy vX.Y` against the
  device's `sys.implementation` before trusting it) into a scratch directory, then `mpremote mount
  <that dir> run ...` instead of mounting `src/` directly.
- `micropython.const()` names can't be imported across modules under either approach — they're
  compiled away at the definition site (SPECIFICATION.md Part E.5.1). Inline the literal value in
  the test script instead of importing the constant.
- `SensorReaderConfig`-based modules (e.g. `SGP40_Reader`) carry a `cfgmgr`
  (`config_manager.ConfigManager`) whose own `setup()` does real flash file I/O. For a diagnostic
  script that must not write to the RP2040's own flash, prime `reader.cfgmgr.valid = True` and
  `reader.cfgmgr._cache = {...}` directly instead of calling `cfgmgr.setup()` — every read
  (`get_int_values()` etc.) is a pure in-memory `_cache` lookup once `valid` is set.
- `AsyFramManager` is a bump-pointer allocator (CLAUDE.md). Simulating "the module restarted, FRAM
  persisted" requires constructing a **fresh** `AsyFramManager` per simulated restart, so its
  single chunk allocation lands back at the same `base_addr` — not a fresh reader sharing one
  already-allocated manager instance, which would allocate a second, non-overlapping chunk.

## Frozen firmware for a full-system bring-up

Assembling the *whole* system (every sensor driver + `AsyConnTime`/`AsyNtpClient`/`asy_dns_client`
+ `WebserverService`/Microdot together, not just one driver) exceeds even the `.mpy` mount-import
workaround above: the full dependency closure costs ~140-180 KB of heap to import raw/`.mpy` over
a mount, against ~196 KB free on this board — too tight in practice (confirmed: a real
`MemoryError` mid-import). **Freezing every module into the firmware itself instead** (flash/
XIP-resident bytecode, not heap-parsed at import time) drops that same closure's cost to ~33 KB.

Build a bench-only frozen firmware — freezes `src/*.py` + `ext/microdot.py` on top of the stock
`RPI_PICO_W` board manifest, with none of `scripts/build_firmware.py`'s wozi-specific
`boot_entry`/website coupling — by reusing `toolchain/setup_toolchain.py`'s own `build_firmware()`
function directly from a small ad-hoc script:

```python
import sys, shutil, tempfile
from pathlib import Path
sys.path.insert(0, "toolchain")
import setup_toolchain as st

versions = st.load_versions(Path("toolchain/versions.toml"))
board = versions["toolchain"]["board"]
with tempfile.TemporaryDirectory() as tmp:
    stage_dir = Path(tmp) / "stage"
    stage_dir.mkdir()
    for py_file in sorted(Path("src").glob("*.py")):
        shutil.copy(py_file, stage_dir / py_file.name)
    shutil.copy("ext/microdot.py", stage_dir / "microdot.py")
    manifest = Path(tmp) / "manifest.py"
    manifest.write_text(f'include("$(PORT_DIR)/boards/RPI_PICO_W/manifest.py")\nfreeze({str(stage_dir)!r})\n')
    uf2 = st.build_firmware(Path.home() / "pico-toolchain" / "micropython", board, 4, frozen_manifest=manifest)
    shutil.copy(uf2, "build/firmware-dev-bench.uf2")
```

Flash it (a real, deliberate flash write — the one accepted exception to the usual "no RP2040
flash writes for bench testing" default, since it's a reproducible toolchain build, not ad hoc
device state):

```sh
scripts/mpremote_connect.sh bootloader   # reboot into BOOTSEL mode
picotool load -f -x build/firmware-dev-bench.uf2
```

**The entry/wiring script itself** (mounted, never flashed — see "After flashing" below), matching
`src/sensortask_wozi.py`'s own current shape but rewired for this bench's real pins per the table
above (this exact content lived on the device's own flash filesystem as `/main.py` for a long
stretch, confirmed working repeatedly; it was removed during a 2026-09-02 full-flash-erase — see
"Current bench state" below — so it's captured here in full instead of only living
device-side again):

```python
"""Bench bring-up adaptation of src/sensortask_wozi.py: same top-level functionality (SCD30, SGP40+VOC,
BMP3xx, Neopixel, FRAM, WiFi/NTP/DNS, notification, webserver), rewired for the dev bench unit's real
hardware (dev_legacy/README.md) instead of wozi's. Not a promoted src/ file - a scratch bring-up
script, run via mpremote mount, never flashed by itself (everything it imports IS frozen - see the
bench-only frozen firmware recipe in dev_legacy/README.md)."""

import asyncio
import gc
import time
from asyncio import ThreadSafeFlag


def _mem(label):
    gc.collect()
    print("MEM %-24s free=%d" % (label, gc.mem_free()))


_mem("post-import")

import asy_i2c_driver
import asy_spi_driver
import config_manager as cm
from asy_fram_manager import AsyFramManager
from asy_bmp3xx_driver import BMP3xx_Reader
from asy_neopixel_driver import NeopixelDriver
from asy_scd30_driver import SCD30_Reader
from asy_sgp40_driver import SGP40_Reader
from asy_wifi_service import AsyConnTime
from asy_ntp_client import AsyNtpClient
from asy_notification_service import NotificationCoordinator, NotificationSignal
from system_service import SystemService
from microdot import Microdot
from asy_webserver_service import SettingsGroup, WebserverService

_MAX_MODULE_ERROR = 5
_DNS_TIMEOUT_MS = 500
_DNS_TRIES = 1
_NTP_FETCH_TIMEOUT_MS = 5000

_FIELD_WARN_CO2 = (("WarnCO2", "int", 1600, 0, 3000, None),)
_FIELD_WARN_VOC = (("WarnVOC", "int", 350, 0, 500, None),)
_FIELD_WARN_HUM = (("WarnHum", "float", 65.0, 0.0, 100.0, None),)

watchdog = None  # deliberately spared for this bring-up - debugging aid, see module docstring
conn = None
ntp = None
i2c0 = None
i2c1 = None
spi0 = None
fram = None
sysfunct = None
sgp_reader = None
bmp_reader = None
scd_reader = None
pixel = None
notify_service = None
webserver = None


async def sgp_comp_callback():
    data = await scd_reader.get_data()
    try:
        return [float(data.Temp), float(data.Hum)]
    except Exception:
        return [None, None]


async def co2_value_callback():
    scd_data = await scd_reader.get_data()
    if scd_data is None or scd_data.CO2 is None:
        return None
    return float(scd_data.CO2)


async def voc_value_callback():
    sgp_data = await sgp_reader.get_data()
    if sgp_data is None or sgp_data.VOC is None:
        return None
    return int(sgp_data.VOC)


async def hum_value_callback():
    scd_data = await scd_reader.get_data()
    if scd_data is None or scd_data.Hum is None:
        return None
    return float(scd_data.Hum)


def _gmtimestruct_to_dict(t):
    if t is None:
        return None
    return {
        "year": t[0], "month": t[1], "mday": t[2], "hour": t[3],
        "minute": t[4], "second": t[5], "weekday": t[6], "yearday": t[7],
    }


async def _system_cmd_callback(cmd):
    if cmd == "reboot":
        sysfunct.reboot_system()
    elif cmd == "bootloader":
        sysfunct.reboot_bootloader()
    elif cmd == "mempause":
        sysfunct.pause_permanent_storage(300)
    else:
        return False
    return True


_FIELD_LED_R = ("r", "int", None, 0, 255, None)
_FIELD_LED_G = ("g", "int", None, 0, 255, None)
_FIELD_LED_B = ("b", "int", None, 0, 255, None)
_FIELD_LED_T = ("t", "float", None, 0.5, 60.0, None)


async def _notification_led_callback(payload):
    try:
        r_err, r = cm.type_or_range_error(payload["r"], _FIELD_LED_R)
        g_err, g = cm.type_or_range_error(payload["g"], _FIELD_LED_G)
        b_err, b = cm.type_or_range_error(payload["b"], _FIELD_LED_B)
        t_err, t = cm.type_or_range_error(payload["t"], _FIELD_LED_T)
    except KeyError:
        return False
    if r_err or g_err or b_err or t_err:
        return False
    return await pixel.request_signal(r, g, b, t)


async def _notification_pause_callback(payload):
    await notify_service.set_override_led(payload)
    return True


async def _sgp_maintenance_status():
    backup_ts, restore_ts = await sgp_reader.get_mem_status()
    return {"BackupTS": backup_ts, "RestoreTS": restore_ts}


async def _networking_status():
    wifi_data = await conn.get_data()
    ifcfg = conn.get_wlan_ifconfig()
    ntp_data = await ntp.get_data()
    return {
        "WifiUptime": await conn.get_wifi_uptime(),
        "Mode": wifi_data.Mode,
        "Connected": wifi_data.Connected,
        "IP": wifi_data.IP,
        "IPv4": None if ifcfg is None else ifcfg[0],
        "Subnet": None if ifcfg is None else ifcfg[1],
        "Gateway": None if ifcfg is None else ifcfg[2],
        "DNS": None if ifcfg is None else ifcfg[3],
        "Rssi": conn.get_wlan_rssi(),
        "NtpSynced": ntp_data.Synced,
        "NtpLastSyncAge": ntp_data.LastSyncAge,
        "NtpLastSync": ntp_data.TS,
    }


async def _system_status():
    local_time = await ntp.cettime()
    return {
        "SysUptime": await sysfunct.get_uptime(),
        "BootSignature": await sysfunct.get_boot_signature(),
        "MemPaused": fram.get_pause(),
        "LocalTime": _gmtimestruct_to_dict(local_time),
        "UtcTime": _gmtimestruct_to_dict(time.gmtime()),
    }


async def _notification_status():
    data = await notify_service.get_data()
    return {"Triggered": data.Triggered, "TS": data.TS, "PauseTime": await notify_service.get_override_led()}


def _collect_error_sources():
    return [
        conn, conn.cfgmgr, conn.dns_server, ntp, ntp.cfgmgr, fram, sysfunct, sysfunct.cfgmgr,
        sgp_reader, sgp_reader.cfgmgr, bmp_reader, bmp_reader.cfgmgr, scd_reader, pixel,
        notify_service, notify_service.cfgmgr,
    ]


def _collect_level_setters():
    return [
        conn.pr.set_level, conn.cfgmgr.pr.set_level, conn.dns_server.pr.set_level,
        ntp.pr.set_level, ntp.cfgmgr.pr.set_level, fram.pr.set_level,
        sysfunct.pr.set_level, sysfunct.cfgmgr.pr.set_level,
        sgp_reader.pr.set_level, sgp_reader.cfgmgr.pr.set_level,
        bmp_reader.pr.set_level, bmp_reader.cfgmgr.pr.set_level,
        scd_reader.pr.set_level, pixel.pr.set_level,
        notify_service.pr.set_level, notify_service.cfgmgr.pr.set_level,
        webserver.pr.set_level,
    ]


async def build_system(*, cfg_path="", debug=None, web_host="0.0.0.0", web_port=80):
    global conn, ntp, i2c0, i2c1, spi0, fram, sysfunct
    global sgp_reader, bmp_reader, scd_reader, pixel, notify_service, webserver

    _mem("build_system start")
    conn = AsyConnTime(
        conn_fail_to_hotspot=5, hotspot_time_min=8, max_module_error=_MAX_MODULE_ERROR,
        cfg_path=cfg_path, debug=debug,
    )
    ntp = AsyNtpClient(
        conn.get_wifi_mode_lock(), conn.network_available, conn.get_dns_server_ip,
        max_module_error=_MAX_MODULE_ERROR, dns_timeout_ms=_DNS_TIMEOUT_MS, dns_tries=_DNS_TRIES,
        ntp_fetch_timeout_ms=_NTP_FETCH_TIMEOUT_MS, cfg_path=cfg_path, debug=debug,
    )
    # dev_legacy/README.md wiring table (bench unit, not wozi):
    # I2C0 (13,12) = BMP3xx only. I2C1 (15,14) = SCD30 + SGP40 (shared bus, distinct addresses) -
    # SCD30's clock-stretch timeout extension (wozi's own i2c0 comment) follows SCD30 onto whichever
    # bus it's actually on here, i.e. i2c1, not i2c0.
    i2c0 = asy_i2c_driver.I2C(0, 13, 12, frequency=50000)
    i2c1 = asy_i2c_driver.I2C(1, 15, 14, frequency=50000, timeout=200000)
    spi0 = asy_spi_driver.SPI(0, 2, 3, 4)
    # FRAM: dev bench chip is a 256KB MB85RS2MTA at CS=GPIO5 (wozi: 8KB MB85RS64V at CS=1).
    fram = AsyFramManager(spi0, 5, max_size=0x40000, debug=debug)
    _mem("after fram")
    sysfunct = SystemService(ntp.ntp_issynced, watchdog=watchdog, fram=fram, cfg_path=cfg_path, debug=debug)
    _mem("after sysfunct")
    sgp_reader = SGP40_Reader(
        i2c1, sgp_comp_callback, fram_storage=fram, fram_ntp_callback=ntp.ntp_issynced,
        max_module_error=_MAX_MODULE_ERROR, cfg_path=cfg_path, debug=debug,
    )
    _mem("after sgp_reader")
    bmp_reader = BMP3xx_Reader(i2c0, max_module_error=_MAX_MODULE_ERROR, cfg_path=cfg_path, fram=fram, debug=debug)
    _mem("after bmp_reader")
    # IRQ/RDY = GPIO11 on this bench unit (wozi: GPIO8).
    scd_reader = SCD30_Reader(i2c1, 11, trigger_sec=3, max_module_error=_MAX_MODULE_ERROR, fram=fram, debug=debug)
    _mem("after scd_reader")
    # GPIO18 on this bench unit (wozi: GPIO15).
    pixel = NeopixelDriver(18, fram=fram, debug=debug)
    notify_service = NotificationCoordinator(
        pixel.request_signal, ntp.cettime, max_module_error=_MAX_MODULE_ERROR,
        cfg_path=cfg_path, fram=fram, debug=debug,
    )
    notify_service.register(NotificationSignal("WarnCO2", co2_value_callback, _FIELD_WARN_CO2, (1, 0, 0)))
    notify_service.register(NotificationSignal("WarnVOC", voc_value_callback, _FIELD_WARN_VOC, (0, 1, 0)))
    notify_service.register(NotificationSignal("WarnHum", hum_value_callback, _FIELD_WARN_HUM, (0, 0, 1)))
    notify_service.finalize()
    conn.set_ext_led(pixel)
    _mem("after pixel+notify_service")

    app = Microdot()
    _mem("after Microdot()")
    webserver = WebserverService(
        app,
        sensors=(scd_reader, bmp_reader, sgp_reader),
        settings={
            "networking": [
                SettingsGroup(conn, ("SSID", "PW", "Country", "Hostname"), post_fct=conn.reconnect_wifi),
                SettingsGroup(conn, ("LedWifiOn",)),
                SettingsGroup(ntp, ("NTP_Host", "NTP_Offset_S", "NTP_Interv_H"), post_asy_fct=ntp.ntp_force_sync),
            ],
            "system": [
                SettingsGroup(sysfunct, ("DebugLevel", "TaskCheckSecs")),
                SettingsGroup(ntp, ("GMTOffset", "DSTOffset")),
            ],
            "notification": [
                SettingsGroup(notify_service, cm.schema_names(notify_service.get_cfg_schema())),
            ],
        },
        system_cmd=_system_cmd_callback,
        notification_led=_notification_led_callback,
        notification_pause=_notification_pause_callback,
        status_sources={
            "networking": _networking_status,
            "system": _system_status,
            "notification": _notification_status,
        },
        maintenance_sensors=(("SGP40", _sgp_maintenance_status),),
        error_sources=_collect_error_sources(),
        debug=debug,
        host=web_host,
        port=web_port,
    )
    _mem("after WebserverService()")

    sysfunct.set_level_setters(_collect_level_setters())

    await sysfunct.setup()
    await fram.setup()
    await conn.setup()
    await ntp.setup()
    await sgp_reader.setup()
    await bmp_reader.setup()
    await notify_service.setup()
    _mem("after setup() batch")


def _collect_task_starters():
    return (
        scd_reader.get_task_starters() + bmp_reader.get_task_starters() + sgp_reader.get_task_starters()
        + pixel.get_task_starters() + notify_service.get_task_starters() + sysfunct.get_task_starters()
        + conn.get_task_starters() + ntp.get_task_starters() + webserver.get_task_starters()
    )


def _collect_timer_starters():
    return (
        scd_reader.get_timer_starters() + bmp_reader.get_timer_starters() + sgp_reader.get_timer_starters()
        + pixel.get_timer_starters() + notify_service.get_timer_starters() + sysfunct.get_timer_starters()
        + conn.get_timer_starters() + ntp.get_timer_starters() + webserver.get_timer_starters()
    )


async def main(*, cfg_path="", debug=None, web_host="0.0.0.0", web_port=80):
    await build_system(cfg_path=cfg_path, debug=debug, web_host=web_host, web_port=web_port)

    task_starters = _collect_task_starters()
    timer_starters = _collect_timer_starters()
    print("MEM task/timer starters collected: %d tasks, %d timers" % (len(task_starters), len(timer_starters)))

    # Real sysfunct.start_timers() now - the _timer_sequencer() Timer-GC bug is fixed (frozen into
    # this firmware), no manual bypass loop needed anymore.
    await sysfunct.start_timers(timer_starters)
    _mem("after start_timers()")

    try:
        await asyncio.wait_for(ntp.ntp_force_sync(), 20)
    except asyncio.TimeoutError:
        print("NTP force-sync did not complete within 20s - continuing anyway")
    _mem("after ntp_force_sync()")

    await sysfunct.start_and_check_tasks(task_starters)  # never returns under normal operation


asyncio.run(main(cfg_path=""))
```

If `picotool` reports a version mismatch (`Requires version X, you have version Y`), a stale
system-wide install is shadowing the toolchain's own rebuilt copy — rerun `uv run
toolchain/setup_toolchain.py` (its `setup` subcommand) to rebuild and reinstall it properly rather
than working around it locally.

After flashing, only the entry/wiring script itself needs to stay live-mounted (everything it
imports is already frozen in) — fast to edit and rerun without a firmware rebuild:

```sh
scripts/mpremote_connect.sh mount path/to/dir/containing/only/the/entry_script.py run entry_script.py
```

**Before starting a fresh diagnostic run against this bench's FRAM-backed error/warning history**,
clear it first (`PUT /status {"ResetErrors": true}` once the system is up and reachable over REST) —
it survives everything short of that, including a firmware reflash (FRAM is a separate SPI chip,
untouched by `picotool load`). See SPECIFICATION.md Part C.7 for the full rule and the real
investigation this caught out (a stale, never-cleared entry misread as a bug reproducing on every
boot). Don't treat a nonzero `errcount` entry as evidence from *this* run until you've confirmed the
counter was at zero right after your own last reset.

## WiFi/NTP/DNS integration testing (bridged AP on the host Rpi4)

Exercising the real `AsyConnTime`/`AsyNtpClient`/`asy_dns_client` code paths (not a bypass script)
needs the bench unit to reach a real WiFi network with real internet/NTP access. The session host
(an Rpi4) bridges its own uplink (`eth0`) with a WiFi AP it hosts (`wlan0`) via NetworkManager, so
the RP2040 joins the exact same LAN/internet path the host itself has. This is real, persistent
host infrastructure (survives a host reboot; verify with `nmcli connection show`), not a
one-off/torn-down-after-use setup.

**Automated**: `uv run toolchain/setup_toolchain.py env --tier bench` (see README.md's "Dev
environment setup" table) runs exactly the recipe below — auto-detecting the uplink/WiFi
interfaces, generating a fresh SSID/password unless `--ssid`/`--password` are given, and applying
the same PMF/WPA2 tuning. It's idempotent: if `br0-wifi-ap` already exists (e.g. from a prior run,
or from following the manual recipe by hand), it's left alone and only its current SSID is
reported — nothing gets recreated or re-randomized. The manual recipe below remains the documented
mechanism it wraps, and the fallback for a host where interface auto-detection is ambiguous
(`--uplink-iface`/`--wifi-iface` override it explicitly):

```sh
nmcli connection add type bridge ifname br0 con-name br0
nmcli connection modify br0 bridge.mac-address <eth0's real MAC, from `ip link show eth0`>
nmcli connection add type ethernet ifname eth0 master br0 con-name br0-eth0 slave-type bridge
nmcli connection add type wifi ifname wlan0 con-name br0-wifi-ap ssid <ssid> \
    802-11-wireless.mode ap 802-11-wireless.band bg master br0 slave-type bridge
nmcli connection modify br0-wifi-ap wifi-sec.key-mgmt wpa-psk wifi-sec.psk <password> \
    wifi-sec.proto rsn wifi-sec.pairwise ccmp wifi-sec.group ccmp wifi-sec.pmf disable
nmcli connection up br0-eth0; nmcli connection up br0-wifi-ap
```

**Pin `bridge.mac-address` to `eth0`'s own real hardware MAC before ever bringing the bridge up —
load-bearing, not optional** (REAL FINDING, 2026-09-04 bench Pi4 lockout incident, see CLAUDE.md's
"Hard rules"): left unset, NetworkManager synthesizes the bridge's own MAC (commonly inherited from
a slave port, and this can shift across the bridge's lifetime) instead of exposing `eth0`'s real,
permanent one. The router's static DHCP reservation is keyed to whatever MAC it saw when the
reservation was made — once the bridge presents a different one, the reservation silently orphans:
the host gets bumped to a new pool address and a synthesized `PC-<mac>` hostname instead of its real
one. Pinning to the real hardware MAC means a reservation keyed to it survives any future
teardown/recreate of this exact bridge. `toolchain/setup_toolchain.py`'s `ensure_bench_bridge()`
does this automatically on creation, and warns (without auto-repairing — cycling a live bridge's MAC
risks the same SSH-drop this fix exists to prevent) if an existing bridge's MAC doesn't match.

**`wifi-sec.pmf disable` (not `optional`/`required`) is load-bearing** — the Pico W's `cyw43439`
WiFi chip's WPA2 handshake silently fails against a PMF-enabled/mixed config (observed: `iw event`
showed `new station` immediately followed by `del station`, no explicit error anywhere).
`wifi-sec.proto rsn`/`pairwise ccmp`/`group ccmp` (WPA2-only, AES-only, no TKIP/WPA3 fallback) is
the rest of the tuning that made the handshake succeed reliably. `bridge.stp` stays at its default
(off isn't required, wasn't found necessary).

Generate a fresh test-only SSID/password per session rather than reusing a fixed one, and never
commit real credentials to this file (see CLAUDE.md's credential-handling rule). Connect the
RP2040 the intended way — through the real production code path (`PUT /networking` with
`SSID`/`PW`, or the mount-proxied `config_WIFI.cfg`; mount-proxied config is the accepted default
for bench testing, not real device flash — see "Testing real hardware from a session" above), not
a bypass script, so the test actually exercises `asy_wifi_service.py`'s own connect state machine.

## Current bench state (as of 2026-09-02 — supersedes 2026-08-28 where they conflict)

Facts a future session should know before assuming anything about what's currently on this board.
The 2026-08-28 facts below (FRAM chunk layout, SCD30 NVM temperature offset) are about the
external FRAM/SCD30 chips specifically — unaffected by an RP2040-internal-flash erase — and stay
believed-true; the flash-filesystem/firmware facts from that date are superseded by this section.

- **A stray `/main.py` was found on the device's own flash filesystem and deleted (2026-09-02,
  full `picotool erase -a` + owner sign-off).** It was byte-for-byte the entry script now embedded
  in full above — apparently it had been `cp`'d onto the device's real VFS at some point rather
  than only ever used via `mpremote mount` as this doc's own recipe describes, and this caused real
  confusion: MicroPython's rp2 `main.c` runs a frozen `_boot.py` first, then falls back to a
  **filesystem** `boot.py`/`main.py` if the frozen path returns instead of blocking forever — so a
  session's attempt to test a "no-autostart" frozen `_boot.py` variant kept auto-starting anyway,
  from this stale file, with nothing to indicate why. **Standing lesson for this bench going
  forward**: never `cp` this entry script (or any equivalent) onto the device's real VFS — mount it
  per this doc's own recipe every time, precisely so stale copies like this can't accumulate again.
  A quick `os.listdir('/')` (via `exec()`, one-shot — see `tests_hardware/README.md`'s
  liveness-polling finding for why this is fine as a one-shot check but never a polling one) is a
  cheap way to confirm the VFS is actually empty before trusting "nothing auto-starts" again.
- **Onboard flash filesystem (VFS) is empty again** after the full erase above — no autostart
  script, no config files. Currently flashed with a freshly-rebuilt copy of the "bench-only frozen
  firmware" recipe above (`build/firmware-dev-bench.uf2`, not committed — rebuild from the recipe
  above, it's fully reproducible); the entry script is running **mounted**, not flashed, per the
  recipe's own intent this time. This is a scratch/debug state, not a final one — no watchdog is
  armed (see the entry script's own `watchdog = None`, unchanged from this doc's existing
  convention) and WiFi has no saved credentials (falls back to hotspot mode, SSID `SensorNode`).
- **`scripts/build_firmware.py`'s own autostart chain was tried against this bench once and produced
  a real I2C failure that this doc's own mounted-entry-script recipe does not — since re-classified
  as noise from an invalid mixed test, not a real bug (2026-09-03 cleanup, see `BACKLOG.md`'s
  "per-variant `sensortask-*.py` generator" item for the full account).** `scripts/build_firmware.py`
  only ever encodes `wozi`'s production pins — no per-variant `sensortask-*.py` exists yet — so an
  earlier session worked around that by scratch-patching a copy of `src/sensortask_wozi.py` with
  this doc's own wiring table values (verified correct independently via direct
  `machine.I2C.scan()` + chip-ID/address readback: BMP390 chip_id=0x50 at i2c0/0x77, SGP40 at
  i2c1/0x59, SCD30 at i2c1/0x61) and flashing *that* through `scripts/build_firmware.py`'s own
  autostart chain. BMP3xx came up clean but SCD30+SGP40 (sharing i2c1) failed with real `errno=11`
  ("Read failed") under the full 18-task system, while the identical wiring via this doc's own
  mounted-entry-script recipe ran cleanly (100+s, zero errors). The patched module was still wozi's
  own full production `sensortask_wozi.py` — including its `import frozen_html`/`static_mount`
  static-website plumbing, which has no reason to run in a dev-bench diagnostic at all — flashed
  through wozi's own boot chain, which has zero awareness this bench exists. That's not a
  representative test of either target, so the `errno=11` finding isn't tracked as a bug to fix.
  **Standing rule for this bench going forward**: don't flash `scripts/build_firmware.py wozi` (or a
  hand-patched copy of it) here expecting a meaningful result — the mounted-entry-script recipe above
  is the only currently-valid way to run the real, wired-together system on this hardware, until the
  per-variant generator exists.
- **FRAM's first ~720 bytes hold real, structured data again** — 7 chunks, in `sensortask_dev`'s
  own `build_system()` construction order (sysfunct's error log, sgp_reader's error log + VOC-backup
  chunk, bmp_reader's, scd_reader's, pixel's, notify_service's — see CLAUDE.md's FRAM chunk
  determinism rule), from the full-system bring-up above, overwriting the earlier range-sweep
  test's pattern bytes at those same addresses. Anything past that offset is still stale
  test-pattern garbage from the earlier per-peripheral FRAM sweep — treat only the unclaimed tail
  as garbage, not the whole chip.
- **SCD30 temperature offset is still 1.5°C** (unchanged by the full-system bring-up, which only
  set `trigger_sec=3`) — not the sensor's power-on default of 0.0°C; NVM-persisted, so it survives
  a power cycle. Ambient pressure and altitude compensation are both 0 (disabled/default).
- **SGP40's VOC algorithm holds real backup state again** (no longer freshly reset/in blackout) —
  the full-system bring-up's own periodic backup cycle fired repeatedly and wrote real algorithm
  state to its FRAM chunk.
- **The bench *host* (the Rpi4 itself, not the RP2040 DUT) lost SSH access on 2026-09-04 during a
  from-blank `env --tier bench` test (BACKLOG.md's top priority) and was recovered by pulling the
  SD card into a second machine** — see BACKLOG.md's `env --tier bench` item for the full account
  (root cause: a one-shot `systemd-run` recovery dead-man's-switch, verified on a dry run, was never
  re-armed before the real `nmcli connection delete br0-eth0`/`br0` that followed — dropping the
  host's own LAN IP synchronously, since it lives on the bridge once `eth0` is enslaved to it).
  Recovery: NetworkManager had auto-suppressed its own default wired profile
  (`autoconnect=false` + a deeply negative `autoconnect-priority`) once the bridge slave profile
  claimed `eth0`; re-enabling it (`autoconnect=true`, drop the priority override) restored plain
  DHCP-over-`eth0` with no bridge.
  - **Two downstream symptoms, both from one cause**: the host now shows up under a *different*
    DHCP-leased IP and a synthesized `PC-D8-3A-DD-28-EA-5A` hostname in the router, instead of the
    old static reservation/friendly name. Cause: a Linux bridge synthesizes its own MAC (often
    inherited from a slave port, and it can shift across the bridge's lifetime) rather than exposing
    `eth0`'s real one — the router's reservation was keyed to whatever MAC `br0` presented while it
    existed, so once `eth0` connects unbridged (its own true MAC), the router treats it as a new
    device. **Fixed going forward** (2026-09-04): the bridge recipe above and
    `ensure_bench_bridge()` now pin `bridge.mac-address` to `eth0`'s real hardware MAC
    (`d8:3a:dd:28:ea:5a`, confirmed via `ip link show eth0` — matches the router's own synthesized
    `PC-D8-3A-DD-28-EA-5A` name, confirming this MAC is what the router now sees) on every future
    bridge creation, so a reservation keyed to this MAC survives any future teardown/recreate.
    **Still open, needs router admin UI access (not automatable from here)**: re-key the router's
    existing static reservation to `d8:3a:dd:28:ea:5a` and, if the router doesn't infer it
    automatically, rename the entry back to `raspberrypi`. On-device hostname itself
    (`/etc/hostname`, `/etc/hosts`) was confirmed still correctly `raspberrypi` throughout — this was
    never an on-device regression, only the router's stale MAC-keyed bookkeeping.
  - `nico`'s `dialout` membership, also revoked during the same test, has been restored
    (`sudo gpasswd -a nico dialout`, confirmed 2026-09-04).
  - **`env --tier bench`'s real from-blank bridge creation is now verified working, for real, on
    this bench Pi4 (2026-09-04)** — the last open gap in BACKLOG.md's `env --tier bench` item is
    closed. `env --tier flash` was run first, full and unmodified end to end (real toolchain
    rebuild, real `/dev/ttyACM0` USB auto-detection) — no network changes, so no dead-man's-switch
    needed for that part. `ensure_bench_bridge()`'s own creation path was then exercised directly
    (calling it in-process rather than re-running `run_env()`'s multi-minute, already-verified
    `run_setup()` prefix a third time) under a freshly-armed `systemd-run` recovery timer, sized
    from a first, deliberately-observed real timing run: `nmcli connection up br0-eth0`/
    `br0-wifi-ap` both report success in ~1s, but the bridge doesn't actually get a DHCP lease and
    become the default route until ~30s later (STP carrier/forwarding delay), confirmed directly
    via `journalctl -u NetworkManager`. First attempt's own recovery timer (120s) fired and tore
    the freshly-created bridge back down before it could be confirmed+disarmed — the agent spent
    that time on unplanned diagnosis instead of promptly checking and disarming, not a bug in the
    bridge logic itself (`journalctl -u bench-recovery.service` timestamps confirm the bridge had
    in fact come up cleanly, ~90s before the timer fired) - itself a real proof that the dead-man's-
    switch mechanism works exactly as designed. **Redone properly**: armed again (150s), then a
    short bounded poll (3s interval) for `br0` to actually carry an IP, then immediate
    verify-and-disarm the moment it did (~30s in, leaving ample unused margin) — this is the
    validated pattern for any future single-atomic-sequence network test: one arm covering the
    whole sequence generously (not a per-command re-arm, since there is no dry-run/real-run gap
    within one continuous script call), then check-and-disarm *immediately* on completion, with no
    detour in between. **Confirms the MAC-pinning fix works as intended**: `br0`'s live MAC came up
    as `d8:3a:dd:28:ea:5a` (`eth0`'s real hardware MAC, pinned by `ensure_bench_bridge()` before the
    bridge was ever brought up) and the DHCP lease it got back was the *same* IP
    (`192.168.85.75`) `eth0` already held unbridged - no drift, exactly the property this fix
    exists to guarantee for any future teardown/recreate. The router's *existing* reservation is
    still keyed to the old, pre-incident synthesized MAC, not this real one - that manual
    re-keying (see above) remains open and is unaffected by this verification.
  - `br0`/`br0-eth0`/`br0-wifi-ap` are **live again** as of the verification above (a fresh
    randomly-generated SSID/password per session, not committed anywhere - see
    `generate_bench_ap_credentials()`) - no longer in the deliberately-blank state.

## Legacy on-device filesystem snapshot (2026-08-27, historical)

Verbatim snapshot of this bench unit's onboard filesystem *as it was on 2026-08-27*, pulled over
USB serial via `mpremote` (`scripts/mpremote_connect.sh cp -r :. dev_legacy/`), back when the unit
still ran MicroPython 1.24.1 and held on-device code changes that were never copied to any host
machine. No longer live (the flash is now empty, see above) — kept purely as reference for future
`src/` promotion work.

`sensortask-dev.py` itself is stale/non-functional as captured (wrong `asy_FRAM_manager` import
name, wires SHTC3 that isn't there, hardcodes a Neopixel pin that isn't the real one) —
`sensortask_test.py` is the more internally-consistent reference for what was actually running,
though the wiring table above is the ground truth for either.
