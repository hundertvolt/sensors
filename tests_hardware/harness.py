"""Host-side (CPython) harness primitives for the flash/bench real-hardware tiers: the board over `mpremote`, its facts
read from the device TOMLs, device scripts rendered with them and their FACT lines parsed, and the boot, crash and
recovery helpers every hardware test shares - never run under the MicroPython Unix port (tests_hardware/README.md)."""

import ast
import json
import os
import socket
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, NamedTuple, TypeVar

import serial
import tomllib

# toolchain/ for setup_toolchain, the same bare-sibling shape as its own `import micropython_overrides` (SPECIFICATION.md
# B.15), the repo root for buildgen and scripts/, and tests_hardware/ itself for a loader that imports this file alone.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "toolchain"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import bench_facts
import evidence
import http_client
import setup_toolchain
from setup_toolchain import resolve_board_serial

from buildgen.api_reference import generate_api_reference
from buildgen.generate import expected_facts
from buildgen.graph import build_construction_order
from buildgen.jsontypes import JsonDict
from buildgen.schema_ast import extract_field_schemas
from buildgen.source_ast import parse_source
from buildgen.validate import build_model, device_max_connections_by_name

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Protocol

    from bench_control import BenchBridge

    class _Note(Protocol):
        # A test's result_note()/record_session_note() as recover_by_reset() reports through it.
        def __call__(self, text: str, *, recovery: bool = ...) -> None: ...

T = TypeVar("T")

REPO_ROOT = Path(__file__).resolve().parent.parent
DEVICES_DIR = REPO_ROOT / "devices"
DEVICE_SCRIPTS_DIR = Path(__file__).resolve().parent / "device_scripts"
RENDERED_SCRIPTS_DIR = REPO_ROOT / "build" / "device_scripts"
SRC_DIR = REPO_ROOT / "src"
_SYS_CLASS_TTY = Path("/sys/class/tty")

# SPECIFICATION.md Part I.4(e)'s bar, as the board's own log shows it. BOTH spellings: src/'s
# degrade handlers log str(e), so a real caught allocation failure reads "memory allocation
# failed, ..." (py/runtime.c) and the class name appears only in an UNCAUGHT traceback.
MEMORY_ERROR_MARKERS = ("MemoryError", "memory allocation failed")
# One-time setup() lines, printed at DebugLevel >= 3 (the standard state holds 5); tests_scripts pins each against src/.
BOOT_COMPLETION_MARKERS = ("config is ready", "FRAM SPI FRAM Driver Setup complete")

# The request line every connection held open against the board sends. A FIN close ends its headers,
# so microdot answers whatever it asked: an unrouted method is a small 405, never a route's work. Not
# an RST - a read of it leaves modlwip writing the 400 to a NULL pcb (SPECIFICATION.md Part H.7.1).
HELD_REQUEST_LINE = b"HOLD / HTTP/1.0\r\n"
# Workaround: one header line resets the server's per-call read timeout, so each walk step re-sends it to outlast
# per_call_timeout_s; one line per held connection per step. Remove if the walk stops outlasting that timeout.
HELD_PAD_LINE = b"X-Pad: y\r\n"

# Read from the module that CREATES these NetworkManager connections rather than copied, so a
# rename there cannot leave the bench tier looking for a rig nobody built - its skip gate
# deselects rather than fails, which is exactly the way that goes unnoticed.
BENCH_BRIDGE_CONN = setup_toolchain.BENCH_BRIDGE_CONN
BENCH_ETH_CONN = setup_toolchain.BENCH_ETH_CONN
BENCH_AP_CONN = setup_toolchain.BENCH_AP_CONN

# The lines a device script's source carries for render_device_script() (SPECIFICATION.md E.6.5).
_BENCH_LINE = 'BENCH: "BenchFacts" = {}  # rendered by tests_hardware/harness.py'
_DEVICE_IMPORT = "import _bench_device as device  # rendered: "
_INCLUDE = "# @include _shared/"
_WEBSERVER_SOURCE = "asy_webserver_service.py"
_STREAMING_BUILDERS = ("_stream_dict_response", "_pieces_response")
# Returned when no Pico-family board is attached at all: a path that cannot exist, so the `board`
# fixture's own is_reachable() probe fails and SKIPS (this tier stays collectible with nothing
# attached) without mpremote ever opening some other device's port to find that out.
_NO_BOARD_DEVICE = "/dev/no-pico-serial-device-detected"
# The arming every isolated run starts with: the product's own timeout, so a script that outlasts it resets the board.
# @tunable wdt.timeout_ms = 8000
_ARM_WATCHDOG = "import machine; machine.WDT(timeout=8000)"
# picotool's ERROR_NO_DEVICE (-7, picotool errors/errors.h:16) as an exit status: no BOOTSEL device enumerated yet,
# so nothing was written. Every other exit may already have written flash.
_PICOTOOL_NO_DEVICE_EXIT = 249
_TRANSIENT_MARKERS = ("may be in use by another program", "could not enter raw repl", "could not open")

# @tunable l4.harness_wait_until_poll_s = 1.0
_WAIT_UNTIL_POLL_S = 1.0
# @tunable l4.harness_serving_probe_timeout_s = 10.0
_SERVING_PROBE_TIMEOUT_S = 10.0
# @tunable l4.harness_serving_restore_timeout_s = 90.0
_SERVING_RESTORE_TIMEOUT_S = 90.0
# @tunable l4.harness_serving_restore_poll_s = 3.0
_SERVING_RESTORE_POLL_S = 3.0
# @tunable l4.harness_script_server_timeout_s = 120.0
_SCRIPT_SERVER_TIMEOUT_S = 120.0
# @tunable l4.harness_script_server_handover_s = 20.0
_SCRIPT_SERVER_HANDOVER_S = 20.0
# @tunable l4.harness_script_server_probe_timeout_s = 3.0
_SCRIPT_SERVER_PROBE_TIMEOUT_S = 3.0
# @tunable l4.harness_script_server_handover_poll_s = 0.5
_SCRIPT_SERVER_HANDOVER_POLL_S = 0.5
# @tunable l4.harness_script_server_poll_s = 1.0
_SCRIPT_SERVER_POLL_S = 1.0
# @tunable l4.ceiling_hold_check_timeout_s = 0.05
_HOLD_CHECK_TIMEOUT_S = 0.05
# @tunable l4.harness_usb_rebind_cmd_timeout_s = 10.0
_USB_REBIND_CMD_TIMEOUT_S = 10.0
# @tunable l4.harness_usb_unbind_settle_max_s = 2.0
_USB_UNBIND_SETTLE_MAX_S = 2.0
# @tunable l4.harness_usb_bind_settle_max_s = 3.0
_USB_BIND_SETTLE_MAX_S = 3.0
# Bounded for the same reason the USB unbind/rebind escalation below is: a node that keeps
# vanishing and reappearing under an alternating name would otherwise extend the grace window
# forever, and no single subprocess timeout breaks out of _mpremote()'s own loop.
# @tunable l4.harness_max_device_rebinds = 2
_MAX_DEVICE_REBINDS = 2
# @tunable l4.harness_mpremote_default_timeout_s = 60.0
_MPREMOTE_DEFAULT_TIMEOUT_S = 60.0
# @tunable l4.harness_usb_grace_s = 10.0
_USB_GRACE_S = 10.0
# @tunable l4.harness_usb_grace_poll_s = 0.5
_USB_GRACE_POLL_S = 0.5
# @tunable l4.harness_mpremote_short_timeout_s = 10.0
_MPREMOTE_SHORT_TIMEOUT_S = 10.0
# @tunable l4.harness_presence_probe_timeout_s = 0.2
_PRESENCE_PROBE_TIMEOUT_S = 0.2
# @tunable l4.harness_mpremote_reset_timeout_s = 15.0
_MPREMOTE_RESET_TIMEOUT_S = 15.0
# @tunable l4.harness_log_tail_read_timeout_s = 0.5
_LOG_TAIL_READ_TIMEOUT_S = 0.5
# @tunable l4.observe_during_tail_after_s = 5.0
_OBSERVE_TAIL_AFTER_S = 5.0
# @tunable l4.observe_during_tail_step_s = 1.0
_OBSERVE_TAIL_STEP_S = 1.0
# @tunable l3.toolchain_flash_boot_picotool_load_attempts = 5
_PICOTOOL_LOAD_ATTEMPTS = 5
# @tunable l3.toolchain_flash_boot_load_timeout_s = 120
_PICOTOOL_LOAD_TIMEOUT_S = 120
# @tunable l3.toolchain_flash_boot_load_retry_backoff_s = 2.0
_PICOTOOL_RETRY_BACKOFF_S = 2.0
# @tunable l3.reflash_present_timeout_s = 30.0
_REFLASH_PRESENT_TIMEOUT_S = 30.0
# @tunable l3.reflash_boot_timeout_s = 60.0
_REFLASH_BOOT_TIMEOUT_S = 60.0


class FramDump(NamedTuple):
    path: Path
    facts: "dict[str, object]"


class HardwareNotAvailableError(RuntimeError):
    # Raised when a real board/bench isn't reachable - conftest.py turns it into a skip, so this
    # tier stays collectible with nothing attached. resolve_board_device()'s ambiguous-hardware raise
    # is the deliberate exception: two attached boards must error naming both, never skip.
    pass


class HardwareTestFailureError(AssertionError):
    # Raised for a genuine real-hardware assertion failure - deliberately a plain AssertionError
    # subclass so pytest reports it like any other failed assertion, not a framework-level error.
    pass


@dataclass
class MpremoteResult:
    returncode: int
    stdout: str
    stderr: str


@dataclass
class _Rendering:
    # One script's render: the extras it was asked for, the facts once loaded, the includes already inlined.
    extras: "dict[str, object]"
    facts: "dict[str, object] | None" = None
    included: "set[str]" = field(default_factory=set)

    def bench(self) -> "dict[str, object]":
        if self.facts is None:
            facts: dict[str, object] = dict(bench_facts.build(bench_device()))
            shadowed = sorted(set(facts) & set(self.extras))
            if shadowed:
                raise ValueError(f"extras {shadowed} would shadow board facts of the same name")
            self.facts = {**facts, **self.extras}
        return self.facts


def _api_reference(device: str) -> JsonDict:
    # The device's REST reference as buildgen generates it (SPECIFICATION.md A.8), in process: no build output read.
    model = build_model(device_toml(device), SRC_DIR)
    build_construction_order(model)
    return generate_api_reference(model, SRC_DIR)


def _assert_probe_held(admitted_socks: "list[socket.socket]", started: float) -> None:
    # Every connection the probe counted must still be open at the moment the refusal landed,
    # or they were never held simultaneously and the count is an artefact of the walk's own pace.
    for index, sock in enumerate(admitted_socks):
        sock.settimeout(_HOLD_CHECK_TIMEOUT_S)
        try:
            payload = sock.recv(4096)
        except TimeoutError:
            continue  # still open with nothing to say, which is what an admitted connection does
        except OSError:
            payload = b"<reset>"
        raise AssertionError(f"connection {index} was no longer held ({payload[:40]!r}) {time.monotonic() - started:.2f}s into the walk - the count is not a simultaneous ceiling")


def _close_all(socks: "list[socket.socket]") -> None:
    for sock in socks:
        sock.close()


def _device_table(device: str) -> "dict[str, object]":
    table = tomllib.loads(device_toml(device).read_text(encoding="utf-8")).get("device")
    if not isinstance(table, dict):
        raise HardwareNotAvailableError(f"{device_toml(device)} has no [device] table")
    return table


def _inline(text: str, rendering: _Rendering, source: Path) -> str:
    # The three render lines replaced, every `# @include _shared/<name>.py` inlined once (nested includes too).
    out = []
    for line in text.splitlines(keepends=True):
        stripped = line.rstrip("\r\n")
        if stripped == _BENCH_LINE:
            out.append(f'BENCH: "BenchFacts" = {rendering.bench()!r}  # rendered by tests_hardware/harness.py\n')
        elif stripped.startswith(_DEVICE_IMPORT):
            out.append(f"import {rendering.bench()['device_module']} as device  # rendered: {stripped[len(_DEVICE_IMPORT) :]}\n")
        elif stripped.startswith(_INCLUDE):
            name = stripped[len(_INCLUDE) :].strip()
            if name not in rendering.included:
                rendering.included.add(name)
                include = DEVICE_SCRIPTS_DIR / "_shared" / name
                if not include.is_file():
                    raise FileNotFoundError(f"{source.name} includes _shared/{name}, which does not exist")
                out.append(_inline(include.read_text(encoding="utf-8"), rendering, include) + "\n")
        else:
            out.append(line)
    return "".join(out)


# @tunable l4.ceiling_probe_connect_timeout_s = 2.0
def _open_probe(host: str, port: int, connect_timeout_s: float = 2.0) -> "socket.socket | None":
    # A connected socket, or None when the connect itself fails - its own timeout, apart from the
    # probe's read timeout, so a slow handshake is never mistaken for a held-open connection.
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(connect_timeout_s)
    try:
        sock.connect((host, port))
    except OSError:
        sock.close()
        return None
    return sock


def _page_routes() -> "list[str]":
    # The literal GET paths the webserver registers beside its JSON routes (the site's index), read from src/ by ast.
    tree = _webserver_tree()
    return [
        node.func.args[0].value
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Call) and ast.unparse(node.func.func) == "app.get"
        and node.func.args and isinstance(node.func.args[0], ast.Constant) and isinstance(node.func.args[0].value, str) and "<" not in node.func.args[0].value
    ]


def _poll(check: "Callable[[], bool]", bound_s: float) -> bool:
    # A bounded poll on a state, never a fixed sleep: True as soon as `check` holds, False at the bound.
    deadline = time.monotonic() + bound_s
    while not check():
        if time.monotonic() >= deadline:
            return False
        time.sleep(_USB_GRACE_POLL_S)
    return True


def _retryable_picotool_exit(code: int) -> bool:
    return code == _PICOTOOL_NO_DEVICE_EXIT


def _still_open(sock: socket.socket) -> bool:
    # True while the server has neither answered nor closed: a read would still block.
    sock.setblocking(False)
    try:
        sock.recv(4096)
    except BlockingIOError:
        return True
    except OSError:
        return False  # reset: refused
    return False  # data or EOF: answered or refused


def _streaming_paths(method: str) -> "set[str]":
    # The ROUTES entries whose handler streams its body in bounded pieces (_stream_dict_response() or _pieces_response(),
    # SPECIFICATION.md I.3), read from src/ by ast.
    tree = _webserver_tree()
    routes = next(node.value for node in tree.body if isinstance(node, ast.Assign) and ast.unparse(node.targets[0]) == "ROUTES")
    handlers = {fn.name: fn for fn in ast.walk(tree) if isinstance(fn, ast.AsyncFunctionDef)}
    streaming = set()
    for entry in ast.literal_eval(routes):
        verb, path, handler = entry
        if verb == method and handler in handlers and any(isinstance(n, ast.Call) and ast.unparse(n.func) in _STREAMING_BUILDERS for n in ast.walk(handlers[handler])):
            streaming.add(path)
    return streaming


def _usb_reset_device(device: str) -> "tuple[bool, str]":
    # Workaround: the bench's USB CDC can stop entering raw REPL until the port is rebound (tests_hardware/README.md
    # traps); one unbind+bind per _mpremote() call, each sudo tee checked. Remove when a full round records no rebind.
    name = Path(device).resolve().name  # the by-id link resolve_board_device() returns has no /sys/class/tty entry
    sys_tty_device = _SYS_CLASS_TTY / name / "device"
    if not sys_tty_device.exists():
        return False, f"no /sys/class/tty/{name}/device to rebind"
    usb_device_dir = sys_tty_device.resolve().parent  # the USB device, one level above the tty's interface
    usb_id = usb_device_dir.name
    notes = []
    for action in ("unbind", "bind"):
        try:
            proc = subprocess.run(["sudo", "tee", f"/sys/bus/usb/drivers/usb/{action}"], input=usb_id, capture_output=True, text=True, timeout=_USB_REBIND_CMD_TIMEOUT_S, check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            return False, f"{action} refused: {exc}"
        if proc.returncode != 0:
            return False, f"{action} refused: {proc.stderr.strip()}"
        if action == "unbind" and not _poll(lambda: not (usb_device_dir / "driver").exists(), _USB_UNBIND_SETTLE_MAX_S):
            notes.append(f"driver still bound after {_USB_UNBIND_SETTLE_MAX_S}s")
        if action == "bind" and not _poll(lambda: Path(device).exists(), _USB_BIND_SETTLE_MAX_S):
            notes.append(f"{device} not back after {_USB_BIND_SETTLE_MAX_S}s")
    return True, f"unbind+bind of {usb_id}" + (f" ({'; '.join(notes)})" if notes else "")


# @tunable l4.ceiling_drain_timeout_s = 10.0
# @tunable l4.ceiling_drain_release_s = 1.0
# @tunable l4.ceiling_drain_hold_s = 0.3
def _wait_for_slots_to_drain(host: str, port: int, admitted: int, timeout_s: float = 10.0, release_s: float = 1.0, hold_s: float = 0.3) -> None:
    # Block until `admitted` connections are held at once again - the whole ceiling, not one slot -
    # then give that check's own connections `release_s` to free theirs: a slot outlives its client's
    # close by 0.71-0.84 s (SPECIFICATION.md Part H.7.1), which no probe observes without taking one.
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        probes: list[socket.socket] = []
        try:
            while len(probes) < admitted and (sock := _open_probe(host, port)) is not None:
                probes.append(sock)
            time.sleep(hold_s)  # a refusal closes within milliseconds; an admitted one stays silent
            held = sum(_still_open(sock) for sock in probes)
        finally:
            _close_all(probes)
        if held == admitted:
            time.sleep(release_s)
            return
        # A partial set holds slots of its own until release_s after its close: retrying sooner can
        # alternate forever between two half-drained sets, never seeing the whole ceiling at once.
        time.sleep(release_s if held else 0.1)
    raise AssertionError(f"{host}:{port} never held {admitted} connections at once again within {timeout_s}s of the probe releasing its own - the slots did not drain")


def _walk_to_the_wall(host: str, port: int, probe_limit: int, dwell_s: float, held: "list[socket.socket]") -> int:
    # discover_max_connections()'s walk. Every held connection is sent a request line, then a header
    # line per step, so the per-call read timeout never frees a slot mid-walk; only the outer cap bounds
    # it, which is why probe_limit * dwell_s stays under it (SPECIFICATION.md Part H.7.1).
    started = time.monotonic()
    for admitted in range(probe_limit):
        for index, open_sock in enumerate(held):
            try:
                open_sock.sendall(HELD_PAD_LINE)
            except OSError as exc:
                raise AssertionError(f"connection {index} was no longer held ({exc!r}) {time.monotonic() - started:.2f}s into the walk - the count is not a simultaneous ceiling") from exc
        sock = _open_probe(host, port)
        if sock is None:  # refused or unanswered at connect: the stack itself has no slot left
            _assert_probe_held(held, started)
            return admitted
        held.append(sock)
        sock.settimeout(dwell_s)
        try:
            sock.sendall(HELD_REQUEST_LINE)
            payload = sock.recv(4096)
        except TimeoutError:
            continue  # held open mid-request, as an admitted connection should be
        except OSError:  # reset or broken pipe: closed before it was ever served
            payload = b""
        if payload == b"":
            _assert_probe_held(held[:-1], started)
            return admitted  # refused without a response: this one did not get a slot
        raise AssertionError(f"connection {admitted} against {host} answered {payload[:40]!r} instead of being held open - the server answered a request it should still be waiting on, so this reading is not a ceiling")
    raise AssertionError(f"no connection was refused within {probe_limit} attempts against {host} - the ceiling is higher than this probe looks, or admission is not bounded at all")


def _webserver_tree() -> ast.Module:
    # The webserver source's tree, shared with buildgen's reads through its text-keyed parse cache (a read-only tree).
    path = SRC_DIR / _WEBSERVER_SOURCE
    return parse_source(path.read_text(encoding="utf-8"), str(path))


def get_routes(method: str = "GET", *, json_only: bool = True, streams: "bool | None" = None) -> "list[str]":
    # The bench device's REST routes of `method` from its generated reference (SPECIFICATION.md A.8): JSON-bodied ones,
    # json_only=False adding the page routes, streams filtering by whether the handler streams its body (read from
    # src/, the reference carrying no such property; page routes have none, so a streams filter leaves them out).
    table = _api_reference(bench_device()).get("routes")
    if not isinstance(table, list):
        raise TypeError(f"the REST reference carries no route list: {table!r}")
    routes = [str(route["path"]) for route in table if isinstance(route, dict) and route.get("method") == method]
    if streams is not None:
        streaming = _streaming_paths(method)
        return [path for path in routes if (path in streaming) == streams]
    if not json_only and method == "GET":
        routes += [path for path in _page_routes() if path not in routes]
    return routes


def bench_device() -> str:
    # The board on the bench: $BENCH_DEVICE when set (the run's override, which must name a devices/ TOML), else the
    # one device TOML whose [device] bench is true. None or several flagged is an error naming the files, never a guess.
    override = os.environ.get("BENCH_DEVICE")
    if override:
        if not (DEVICES_DIR / f"{override}.toml").is_file():
            raise HardwareNotAvailableError(f"BENCH_DEVICE names {override}.toml, which is not in {DEVICES_DIR}")
        return override
    flagged = []
    for path in sorted(DEVICES_DIR.glob("*.toml")):
        table = tomllib.loads(path.read_text(encoding="utf-8")).get("device")
        if not path.stem.startswith("zz_test_") and isinstance(table, dict) and table.get("bench") is True:
            flagged.append(path.name)
    if not flagged:
        raise HardwareNotAvailableError(f"no device TOML in {DEVICES_DIR} sets [device] bench = true")
    if len(flagged) > 1:
        raise HardwareNotAvailableError(f"several device TOMLs set [device] bench = true ({', '.join(flagged)}) - exactly one board is on the bench")
    return flagged[0].removesuffix(".toml")


def boot_lines(lines: "list[str]") -> "list[str]":
    # The lines proving a boot ran its one-time setup(): a completion marker, never a bare CFGMGR_/FRAM tag.
    return [line for line in lines if any(marker in line for marker in BOOT_COMPLETION_MARKERS)]


def configured_max_connections(device: "str | None" = None) -> int:
    # The admission ceiling this repo's config would build for `device` (the bench board by default). It describes the
    # TREE, not necessarily the image on the board, so a test that cares asserts the two agree.
    return device_max_connections_by_name(device or bench_device())


def crash_lines(lines: "list[str]") -> "list[str]":
    # A traceback or an allocation failure in either spelling MEMORY_ERROR_MARKERS names.
    return [line for line in lines if "Traceback" in line or any(marker in line for marker in MEMORY_ERROR_MARKERS)]


def device_toml(device: "str | None" = None) -> Path:
    # The device file a build comes from, the bench board's by default: a wait or ceiling the tier derives reads it.
    return DEVICES_DIR / f"{device or bench_device()}.toml"


# @tunable l4.ceiling_probe_limit = 40
# @tunable l4.ceiling_settle_s = 1.0
# @tunable l4.ceiling_dwell_s = 0.3
def discover_max_connections(host: str, port: int = 80, probe_limit: int = 40, settle_s: float = 1.0, dwell_s: float = 0.3) -> int:
    # The ceiling the BOARD actually holds, found by holding connections open one at a time until
    # one is refused. The only figure that is silicon's own rather than the tree's, and the one a
    # raised lwIP PCB count has to be confirmed against (SPECIFICATION.md Part B.14.2).
    time.sleep(settle_s)  # _serve()'s slot release outlives the response (Part I.6), so start clean
    held: list[socket.socket] = []
    try:
        admitted = _walk_to_the_wall(host, port, probe_limit, dwell_s, held)
    except AssertionError as walk_error:
        _close_all(held)
        try:  # best effort, one slot: the next test starts cleaner, and the walk's error stays the headline
            _wait_for_slots_to_drain(host, port, 1, release_s=settle_s)
        except AssertionError as drain_error:
            walk_error.args = (f"{walk_error} (and the drain wait after it failed too: {drain_error})",)
        raise
    finally:
        _close_all(held)
    _wait_for_slots_to_drain(host, port, max(admitted, 1), release_s=settle_s)
    return admitted


def dut_hostname_candidates() -> "tuple[str, str]":
    # The names the DUT's hotspot may carry: the bench TOML's hostname, then the product default WifiService falls
    # back to (schema_default()'s read of _VAL_HOSTNAME).
    hostname = _device_table(bench_device()).get("hostname")
    default = schema_default("asy_wifi_service.py", "Hostname")
    if not isinstance(hostname, str) or not isinstance(default, str):
        raise HardwareNotAvailableError(f"no string hostname in {device_toml()} or no _VAL_HOSTNAME default in src/")
    return hostname, default


def fram_backed_logger_names(device: "str | None" = None) -> "list[str]":
    # Every logger the device keeps on FRAM, as buildgen derives it from the TOML (its expected facts), never a list.
    names = expected_facts(build_model(device_toml(device), SRC_DIR), SRC_DIR)["fram_backed_loggers"]
    if not isinstance(names, list) or not all(isinstance(name, str) for name in names):
        raise TypeError(f"buildgen's fram_backed_loggers is no list of names: {names!r}")
    return [str(name) for name in names]


def hotspot_password(device: "str | None" = None) -> str:
    # The hotspot password the device's TOML builds in ([device] hotspot_password), the bench board's by default.
    password = _device_table(device or bench_device()).get("hotspot_password")
    if not isinstance(password, str):
        raise HardwareNotAvailableError(f"{device_toml(device)} sets no string [device] hotspot_password")
    return password


def kick_then_reset(board: "Board", bench: "BenchBridge") -> None:
    # kick_all_stations()'s workaround, then the reset: no stale AP-side entry outlives the DUT's reboot.
    bench.kick_all_stations()
    board.hard_reset()


def observe_during(board: "Board", action: "Callable[[], T]") -> "tuple[T, list[str]]":
    # The board's log over a whole fault window: tailed from before `action` until it returns plus
    # _OBSERVE_TAIL_AFTER_S, so a crash during the recovery is seen too. A tail that broke raises after the action.
    lines: list[str] = []
    failures: list[BaseException] = []
    stop = threading.Event()

    def tail() -> None:
        while not stop.is_set():
            try:
                lines.extend(board.tail_log(_OBSERVE_TAIL_STEP_S))
            except Exception as exc:  # re-raised below: an unobserved window is no clean one
                failures.append(exc)
                return

    tailer = threading.Thread(target=tail, name="observe_during", daemon=True)
    tailer.start()
    try:
        result = action()
        time.sleep(_OBSERVE_TAIL_AFTER_S)
    finally:
        stop.set()
        tailer.join(_OBSERVE_TAIL_STEP_S + _LOG_TAIL_READ_TIMEOUT_S + _USB_GRACE_S)
    if failures:
        raise HardwareTestFailureError(f"the log tail over the fault window broke: {failures[0]!r}") from failures[0]
    if tailer.is_alive():
        raise HardwareTestFailureError("the log tail over the fault window did not end")
    return result, lines


def parse_facts(output: str, *, allow_missing_done: bool = False) -> "dict[str, object]":
    # Every FACT <key>=<json> line of a device script's output. No DONE line means the script did not finish, which
    # fails quoting the output - except for a script that ends in a reset (its facts come before the reset).
    facts: dict[str, object] = {}
    done = False
    for raw in output.splitlines():
        line = raw.rstrip("\r")
        if line == "DONE":
            done = True
        elif line.startswith("FACT "):
            key, sep, value = line[len("FACT ") :].partition("=")
            if not sep or not key or key in facts:
                raise HardwareTestFailureError(f"malformed or repeated FACT line {line!r} in:\n{output}")
            try:
                facts[key] = json.loads(value)
            except ValueError as exc:  # nan/inf included: MicroPython prints them, JSON has no such value
                raise HardwareTestFailureError(f"FACT {key} is no JSON value: {value!r}") from exc
    if not done and not allow_missing_done:
        raise HardwareTestFailureError(f"the script printed no DONE line - it did not finish:\n{output}")
    return facts


def recover_by_reset(
    board: "Board",
    bench: "BenchBridge",
    ready: "Callable[[], bool]",
    *,
    first_wait_s: float,
    retry_wait_s: float,
    skipped: str,
    note: "_Note",
    description: str,
) -> None:
    # A known bench effect's one bounded recovery, always reported: wait for `ready`; on a timeout record the recovery
    # pass naming what the reset path does not check, kick and reset once, and wait again - a second timeout raises.
    try:
        wait_until(ready, first_wait_s, description=description)
    except TimeoutError:
        note(f"recovery pass: kick + hard_reset() after {description}; skipped: {skipped}", recovery=True)
        kick_then_reset(board, bench)
        wait_until(ready, retry_wait_s, description=f"{description} (after one recovery kick + hard_reset())")


def reflash(board: "Board", uf2_path: Path) -> None:
    # The board onto `uf2_path`, an image its caller built: bootloader, then `picotool load` retried only while no BOOTSEL
    # device is enumerated yet (each retry recorded), then a passive wait for presence and a boot line. Builds nothing.
    board.enter_bootloader()
    for attempt in range(1, _PICOTOOL_LOAD_ATTEMPTS + 1):
        try:
            load = subprocess.run(["sudo", "picotool", "load", "-x", "-v", str(uf2_path)], cwd=REPO_ROOT, capture_output=True, text=True, timeout=_PICOTOOL_LOAD_TIMEOUT_S, check=False)
        except FileNotFoundError as exc:
            raise HardwareNotAvailableError(f"picotool not on sudo's PATH: {exc}") from exc
        except subprocess.TimeoutExpired as exc:
            raise HardwareTestFailureError(f"picotool load {uf2_path} timed out after {_PICOTOOL_LOAD_TIMEOUT_S}s") from exc
        if load.returncode == 0:
            break
        if not _retryable_picotool_exit(load.returncode) or attempt == _PICOTOOL_LOAD_ATTEMPTS:
            raise HardwareTestFailureError(f"picotool load -x -v {uf2_path} failed on attempt {attempt} (exit {load.returncode}):\n{load.stdout}\n{load.stderr}")
        board.recovery_events.append(f"picotool load attempt {attempt}: exit {load.returncode} (no BOOTSEL device yet), retried after {_PICOTOOL_RETRY_BACKOFF_S}s")
        time.sleep(_PICOTOOL_RETRY_BACKOFF_S)
    wait_until(board.is_device_present, timeout_s=_REFLASH_PRESENT_TIMEOUT_S, description=f"board back on USB after flashing {uf2_path.name}")
    wait_for_boot(board, _REFLASH_BOOT_TIMEOUT_S)


def render_device_script(path: Path, **extras: object) -> Path:
    # The script as the board runs it: its BENCH line given the bench board's facts merged with `extras`, its marked
    # device import naming the generated module, every include inlined; written to build/device_scripts/<name>,
    # overwritten per run. A script carrying none of the three runs unchanged; extras it cannot receive raise.
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    lines = [line.rstrip("\r") for line in text.splitlines()]
    if extras and _BENCH_LINE not in lines:
        raise ValueError(f"{path.name} holds no BENCH line, so the extras {sorted(extras)} would never reach it")
    if not any(line == _BENCH_LINE or line.startswith((_DEVICE_IMPORT, _INCLUDE)) for line in lines):
        return path
    rendering = _Rendering(dict(extras))
    rendered = _inline(text, rendering, path)
    if rendering.facts is not None:
        ast.literal_eval(repr(rendering.facts))  # a value repr() cannot write back as a literal fails here, not on the board
    RENDERED_SCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
    target = RENDERED_SCRIPTS_DIR / path.name
    target.write_text(rendered, encoding="utf-8")
    return target


def resolve_board_device(
    by_id_dir: Path = Path("/dev/serial/by-id"),
    sys_tty_dir: Path = Path("/sys/class/tty"),
    dev_dir: Path = Path("/dev"),
) -> str:
    # The board's by-id serial node, as setup_toolchain.resolve_board_serial() identifies it (MicroPython's USB name and
    # vendor 2e8a, never a bare ttyACM scan that could pick the bench's Arduino). Two matches is a hard error.
    candidates = resolve_board_serial(by_id_dir, sys_tty_dir, dev_dir)
    if len(candidates) > 1:
        names = ", ".join(f"{c} ({c.resolve().name})" for c in candidates)
        raise HardwareNotAvailableError(
            f"multiple Raspberry Pi USB serial devices found ({names}) - pass --device or set "
            "MPREMOTE_DEVICE to pick one explicitly, rather than have the suite guess which board to drive",
        )
    if not candidates:
        return _NO_BOARD_DEVICE
    return str(candidates[0])


def restore_board_to_serving(board: "Board", bench: "BenchBridge", dut_ip: str) -> None:
    # run_isolated() leaves main.py stopped, so the webserver is gone until a real hard reset. A bench
    # test that runs a device script calls this in a finally or a fixture's teardown, or every network test
    # after it fails on a refused connection (tests_scripts/test_bench_restores_serving.py pins it).
    kick_then_reset(board, bench)
    wait_until(
        lambda: http_client.fetch(dut_ip, 80, "GET", "/status", timeout_s=_SERVING_PROBE_TIMEOUT_S).status_code == 200,
        timeout_s=_SERVING_RESTORE_TIMEOUT_S,
        poll_interval_s=_SERVING_RESTORE_POLL_S,
        description="DUT serving HTTP again after a device script left main.py stopped",
    )


def save_fram_raw(board: "Board", reason: str) -> FramDump:
    # The FRAM evidence before anything clears it: the read-only raw dump of the whole part (the size the bench
    # build's allocation lies within), saved verbatim to the run's evidence, with the dump's own facts.
    if not isinstance(bench_facts.build(bench_device())["fram_max_size"], int):
        raise HardwareNotAvailableError(f"{device_toml()} wires no FRAM to dump")
    output = board.run_isolated(DEVICE_SCRIPTS_DIR / "fram_raw_dump.py")
    return FramDump(evidence.save_text(f"fram-raw-{reason}.txt", output), parse_facts(output))


def schema_default(src_file: str, field: str) -> object:
    # The product default of one REST field, as its src/ schema tuple declares it, read by buildgen's schema reader
    # (never imported): what a bench repair restores. A field the file does not declare raises naming both.
    fields = extract_field_schemas(SRC_DIR / src_file)
    if field not in fields:
        raise HardwareNotAvailableError(f"src/{src_file} declares no schema field {field!r} (it has {sorted(fields)})")
    return fields[field][1]


def wait_for_boot(board: "Board", timeout_s: float) -> "list[str]":
    # Passive: the live log until a boot line arrives (boot_lines()), every line read so far returned. Those lines are
    # printed at DebugLevel >= 3, so a timeout names that need rather than a hung boot alone.
    lines: list[str] = []
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        lines.extend(board.tail_log(min(_OBSERVE_TAIL_STEP_S, max(deadline - time.monotonic(), 0.0))))
        if boot_lines(lines):
            return lines
    raise TimeoutError(f"no boot line ({' / '.join(BOOT_COMPLETION_MARKERS)}) within {timeout_s}s - the board needs DebugLevel >= 3 for it (the standard state holds 5); log tail: {lines[-5:]!r}")


def wait_for_script_server(dut_ip: str, stop: "threading.Event", path: str = "/status", timeout_s: float = _SCRIPT_SERVER_TIMEOUT_S, handover_s: float = _SCRIPT_SERVER_HANDOVER_S) -> bool:
    # True once a device script's own server answers `path` with a 200, counted only after a probe found nothing
    # serving: main.py's server still answering after `handover_s` raises, never passing for the script's. `stop`
    # ends the wait early, so it never outlives its test; each wait ends at its deadline.
    def serves() -> bool:
        try:
            return http_client.fetch(dut_ip, 80, "GET", path, timeout_s=_SCRIPT_SERVER_PROBE_TIMEOUT_S).status_code == 200
        except (OSError, http_client.HTTP_ERROR):
            return False

    handover_until = time.monotonic() + handover_s
    while not stop.is_set() and serves():
        remaining = handover_until - time.monotonic()
        if remaining <= 0:
            raise HardwareTestFailureError(f"main.py's server still answers {path} {handover_s}s into the handover - a 200 cannot be told from the device script's")
        stop.wait(min(_SCRIPT_SERVER_HANDOVER_POLL_S, remaining))
    deadline = time.monotonic() + timeout_s
    while not stop.is_set():
        if serves():
            return True
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return False
        stop.wait(min(_SCRIPT_SERVER_POLL_S, remaining))
    return False


def wait_until(
    check_fn: "Callable[[], bool]",
    timeout_s: float,
    poll_interval_s: float = _WAIT_UNTIL_POLL_S,
    description: str = "condition",
) -> bool:
    # Bounded poll-until-condition wait, test-harness-only (never used to change src/'s own real
    # timing - SPECIFICATION.md Part F.3). Polls `check_fn()` until truthy or `timeout_s` elapses,
    # treating a raising check as not-yet-ready; always returns True or raises TimeoutError.
    deadline = time.monotonic() + timeout_s
    last_exc: BaseException | None = None
    while time.monotonic() < deadline:
        try:
            if check_fn():
                return True
        except Exception as exc:
            last_exc = exc
        time.sleep(min(poll_interval_s, max(deadline - time.monotonic(), 0.0)))
    try:
        if check_fn():
            return True
    except Exception as exc:
        last_exc = exc
    detail = f" (last error: {last_exc!r})" if last_exc is not None else ""
    raise TimeoutError(f"timed out after {timeout_s}s waiting for: {description}{detail}")


class Board:
    # Drives the board through `uv run --no-sync mpremote`: the one isolated-driver mechanism, the reset, the bootloader
    # entry the reflash helper uses, and passive log tailing. Raw-REPL entry stops main.py; the soft reset after it keeps
    # the armed watchdog, the GC threshold, ticks_ms() and pin muxing and never re-runs main.py (ports/rp2/main.c:246-247).

    def __init__(self, device: "str | None" = None, default_timeout_s: float = _MPREMOTE_DEFAULT_TIMEOUT_S) -> None:
        self._pinned_device = device or os.environ.get("MPREMOTE_DEVICE")
        self.device = self._pinned_device or resolve_board_device()
        self.default_timeout_s = default_timeout_s
        self.recovery_events: list[str] = []  # every retry, node rebind, USB rebind and timeout interrupt, one line each

    def _command(self, *args: str) -> "list[str]":
        # --no-sync: the environment the runner prepared is used as is; nothing inside a hardware run syncs.
        return ["uv", "run", "--no-sync", "mpremote", "connect", self.device, *args]

    def _interrupt_after_timeout(self) -> str:
        # A timed-out call killed only the host process; the script may still run on the board. Ctrl-C twice stops it,
        # then a reset, so no half-run script continues into the next test. Returns what each step did.
        steps = []
        try:
            with serial.Serial(self.device, 115200, timeout=_LOG_TAIL_READ_TIMEOUT_S) as port:
                port.write(b"\x03\x03")
            steps.append("Ctrl-C x2 sent")
        except (OSError, serial.SerialException) as exc:
            steps.append(f"Ctrl-C failed: {exc}")
        try:
            reset = subprocess.run(self._command("reset"), cwd=REPO_ROOT, capture_output=True, text=True, timeout=_MPREMOTE_RESET_TIMEOUT_S, check=False)
            steps.append(f"reset exit {reset.returncode}")
        except (OSError, subprocess.TimeoutExpired) as exc:
            steps.append(f"reset failed: {exc}")
        return ", ".join(steps)

    def _mpremote(self, *args: str, timeout_s: "float | None" = None, allow_recovery: bool = True, retry_if_started: bool = True) -> MpremoteResult:
        # One `uv run --no-sync mpremote connect <device> ...` call. Workaround: a transient USB-settle failure is retried
        # within _USB_GRACE_S, then the node re-resolved, then one USB rebind; each recorded. Remove when a round records
        # none. A retry never re-runs a started script (retry_if_started=False); allow_recovery=False retries nothing.
        started = time.monotonic()
        timeout = timeout_s or self.default_timeout_s
        grace_deadline = started + _USB_GRACE_S
        usb_reset_attempted = False
        rebinds_left = _MAX_DEVICE_REBINDS
        attempt = 0
        while True:
            attempt += 1
            try:
                proc = subprocess.run(self._command(*args), cwd=REPO_ROOT, capture_output=True, text=True, timeout=timeout, check=False)
            except FileNotFoundError as exc:
                raise HardwareNotAvailableError(f"uv/mpremote not on PATH: {exc}") from exc
            except subprocess.TimeoutExpired as exc:
                self.recovery_events.append(f"mpremote {' '.join(args)[:60]} timed out after {timeout}s: {self._interrupt_after_timeout()}")
                raise HardwareTestFailureError(f"mpremote {' '.join(args)} timed out after {timeout}s") from exc
            marker = next((m for m in _TRANSIENT_MARKERS if m in proc.stderr.lower()), None)
            result = MpremoteResult(proc.returncode, proc.stdout, proc.stderr)
            if proc.returncode == 0 or marker is None or not allow_recovery or (proc.stdout and not retry_if_started):
                return result
            elapsed = time.monotonic() - started
            if time.monotonic() < grace_deadline:
                self.recovery_events.append(f"mpremote attempt {attempt}: {marker!r} after {elapsed:.1f}s, retried")
                time.sleep(_USB_GRACE_POLL_S)
                continue
            if rebinds_left > 0 and self._rebind_device_if_moved():
                # Workaround: a reset re-enumerates the CDC device under another node; the retry follows it (at most
                # _MAX_DEVICE_REBINDS times). Remove when a round records no node rebind.
                rebinds_left -= 1
                self.recovery_events.append(f"mpremote attempt {attempt}: node moved, now {self.device} ({elapsed:.1f}s)")
                grace_deadline = time.monotonic() + _USB_GRACE_S
                continue
            if not usb_reset_attempted:
                usb_reset_attempted = True
                rebound, detail = _usb_reset_device(self.device)
                self.recovery_events.append(f"mpremote attempt {attempt}: USB rebind - {detail} ({elapsed:.1f}s)")
                if rebound:
                    grace_deadline = time.monotonic() + _USB_GRACE_S
                    continue
                if " refused: " in detail:
                    raise HardwareNotAvailableError(f"USB rebind recovery refused by sudo ({detail}) - see tests_hardware/README.md prerequisites")
            return result

    def _rebind_device_if_moved(self) -> bool:
        # Re-resolves the serial node when the current one has vanished; True if it moved. A hard
        # reset re-enumerates the CDC-ACM device with no index guarantee (observed ttyACM0 -> ttyACM1
        # mid-suite). An explicitly pinned device is never second-guessed.
        if self._pinned_device is not None or Path(self.device).exists():
            return False
        rebound = resolve_board_device()
        if rebound == self.device:
            return False
        self.device = rebound
        return True

    def is_device_present(self) -> bool:
        # Passive, non-disruptive USB-presence check - opens/closes the CDC-ACM serial port
        # without writing a byte, unlike is_reachable()'s raw-REPL entry (see its comment).
        # Correctly reports False during a hard_reset()'s USB re-enumeration window.
        try:
            probe = serial.Serial(self.device, baudrate=115200, timeout=_PRESENCE_PROBE_TIMEOUT_S)
        except (OSError, serial.SerialException):
            return False
        probe.close()
        return True

    def is_reachable(self) -> bool:
        # allow_recovery=False: the honest current state, since a caller may poll for an expected "no" while a real
        # reboot runs. Raw-REPL entry stops main.py; never poll a live system - is_device_present() is for that.
        try:
            result = self._mpremote("exec", "print('mpremote-ok')", timeout_s=_MPREMOTE_SHORT_TIMEOUT_S, allow_recovery=False)
        except (HardwareNotAvailableError, HardwareTestFailureError):
            return False
        return result.returncode == 0 and "mpremote-ok" in result.stdout

    def enter_bootloader(self) -> None:
        # `machine.bootloader()` triggered remotely - drops the board into BOOTSEL mode for
        # picotool to re-flash (reflash()); a flash cycle once picotool writes. exec(), not run_isolated(): the board
        # never comes back to answer, so a non-zero or timed-out exit here is expected, not a failure.
        self._mpremote("exec", "import machine; machine.bootloader()", timeout_s=_MPREMOTE_SHORT_TIMEOUT_S)

    def exec(self, expr: str, timeout_s: "float | None" = None) -> str:
        # `mpremote exec "<expr>"` in a fresh raw-REPL session, which stops main.py first; never for passive
        # observation of a live system - tail_log() is for that.
        result = self._mpremote("exec", expr, timeout_s=timeout_s)
        if result.returncode != 0:
            # Both streams included: a device-side traceback prints on mpremote's stdout, not
            # stderr, and would otherwise be silently dropped.
            raise HardwareTestFailureError(f"mpremote exec {expr!r} failed (exit {result.returncode}):\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}")
        return result.stdout

    def hard_reset(self) -> None:
        # `mpremote reset`: a raw-REPL exec of machine.reset() (tools/mpremote/mpremote/main.py:407-411, v1.29.0), a
        # real MCU reset that re-runs the frozen main.py; it writes no reset record, so /status reports it as a
        # watchdog reset without a record.
        result = self._mpremote("reset", timeout_s=_MPREMOTE_RESET_TIMEOUT_S)
        if result.returncode != 0:
            raise HardwareTestFailureError(f"mpremote reset failed (exit {result.returncode}):\n{result.stderr}")

    def run_isolated(self, script_path: "str | Path", *, soft_reset_after: bool = True, timeout_s: "float | None" = None, allow_recovery: bool = True, **extras: object) -> str:
        # Isolated-driver mode: the rendered script (render_device_script()) run once against the real frozen src/
        # drivers under a re-armed watchdog; then, when asked, a separate soft reset whose failure never re-runs it.
        # allow_recovery=False when the disconnect IS the outcome - else the 10s grace is measured.
        rendered = render_device_script(Path(script_path), **extras)
        result = self._mpremote("exec", _ARM_WATCHDOG, "run", str(rendered), timeout_s=timeout_s, allow_recovery=allow_recovery, retry_if_started=False)
        if result.returncode != 0:
            # See exec()'s own comment: a device-side traceback lands on mpremote's stdout, not
            # stderr - both are included here for the same reason.
            raise HardwareTestFailureError(f"mpremote run {script_path} failed (exit {result.returncode}):\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}")
        if soft_reset_after:
            reset = self._mpremote("soft-reset", timeout_s=_MPREMOTE_RESET_TIMEOUT_S)
            if reset.returncode != 0:
                raise HardwareTestFailureError(f"script completed (output below) but the trailing soft-reset failed (exit {reset.returncode}): {reset.stderr.strip()}\n{result.stdout}")
        return result.stdout

    def run_isolated_expect_reset(self, script_path: "str | Path", *, timeout_s: "float | None" = None, hold_unread_s: "float | None" = None, **extras: object) -> str:
        # For a script that ends in a real machine.reset(): the device dropping off is the outcome, so the stdout it got
        # out first is returned (parse_facts(..., allow_missing_done=True)). With hold_unread_s the console is held open
        # unread until then or until the board drops off, and "" is returned: its outcome is read from /status after.
        rendered = render_device_script(Path(script_path), **extras)
        args = ["exec", _ARM_WATCHDOG, "run", *(["--no-follow"] if hold_unread_s is not None else []), str(rendered)]
        result = self._mpremote(*args, timeout_s=timeout_s, retry_if_started=False)
        if result.returncode != 0 and not result.stdout and any(marker in result.stderr.lower() for marker in _TRANSIENT_MARKERS):
            raise HardwareTestFailureError(f"mpremote never reached the board, so {Path(script_path).name} never ran (exit {result.returncode}): {result.stderr.strip()}")
        if hold_unread_s is None:
            return result.stdout
        try:
            with serial.Serial(self.device, 115200, timeout=_LOG_TAIL_READ_TIMEOUT_S) as port:
                port.dtr = True
                _poll(lambda: not Path(self.device).exists(), hold_unread_s)
        except (OSError, serial.SerialException):
            pass  # the board already left USB: the reset this run expects
        return ""

    def tail_log(self, duration_s: float, baudrate: int = 115200) -> "list[str]":
        # Passively captures what the live system prints over `duration_s`, without interrupting
        # it (unlike exec()/run_isolated(), which always Ctrl-C first - see tests_hardware/README.md).
        # Retries a transient post-hard_reset() USB-settle failure before raising HardwareNotAvailableError.
        grace_deadline = time.monotonic() + _USB_GRACE_S
        overall_deadline = time.monotonic() + duration_s
        lines: list[str] = []
        while True:
            try:
                with serial.Serial(self.device, baudrate, timeout=_LOG_TAIL_READ_TIMEOUT_S) as port:
                    while time.monotonic() < overall_deadline:
                        raw = port.readline()
                        if raw:
                            lines.append(raw.decode("utf-8", errors="replace").rstrip("\r\n"))
            except serial.SerialException as exc:
                if time.monotonic() >= grace_deadline:
                    raise HardwareNotAvailableError(f"could not read {self.device} for passive log tailing: {exc}") from exc
                time.sleep(_USB_GRACE_POLL_S)
            else:
                return lines
