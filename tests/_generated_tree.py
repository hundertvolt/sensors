"""require_fresh(): refuses a missing or stale build/generated_src/ before a test imports a generated module or reads a
plan. The generator's stamp holds the sha256 of every file it reads and the name of every file it leaves; content, not
mtime, since this port's os.stat() has whole seconds only (extmod/vfs_posix.c:380, v1.29.0)."""

import hashlib
import json
import os
from binascii import hexlify

_TREE = "build/generated_src"
_STAMP = "build/generated_src/.inputs_stamp.json"
_STALE = "build/generated_src/ is missing or stale - run: uv run scripts/_generate_sensortask_modules.py"
_NAMED = ("buildgen/error_catalog.json", "toolchain/versions.toml", "toolchain/micropython_overrides.py", "scripts/_generate_sensortask_modules.py")
_LISTED = (("devices", ".toml"), ("buildgen", ".py"), ("src", ".py"), ("ext", ".py"))
_CHUNK = bytearray(4096)  # one read buffer for every file: hashing allocates no file-sized block


def _differs(outputs: "list[str]") -> bool:
    # The tree's finished files are not the ones the stamped generation left: one is missing, or a removed device's
    # stayed, which a consumer listing the tree takes for a device. A .tmp is a write before its rename, never imported.
    found: set[str] = set()
    try:
        for directory in {""} | {path.rpartition("/")[0] for path in outputs}:  # the top level always: no list passes empty
            base = _TREE + "/" + directory if directory else _TREE
            found.update(directory + "/" + name if directory else name for name in os.listdir(base) if not name.endswith(".tmp") and not _is_dir(base + "/" + name))
    except OSError:  # a directory the generation wrote into is gone
        return True
    return found != set(outputs)


def _exists(path: str) -> bool:
    try:
        os.stat(path)
    except OSError:
        return False
    return True


def _inputs() -> "list[str]":
    # The current input set, relative to the repository root this process runs in; a zz_test_ TOML is a fixture.
    found = [path for path in _NAMED if _exists(path)]
    for directory, suffix in _LISTED:
        if not _exists(directory):  # the generator's glob finds nothing there either
            continue
        fixture = "zz_test_" if directory == "devices" else None
        found.extend(directory + "/" + name for name in os.listdir(directory) if name.endswith(suffix) and not (fixture and name.startswith(fixture)))
    return found


def _is_dir(path: str) -> bool:
    return os.stat(path)[0] & 0xF000 == 0x4000  # S_IFMT, S_IFDIR


def _sha256(path: str) -> str:
    digest = hashlib.sha256()
    view = memoryview(_CHUNK)
    with open(path, "rb") as f:
        while True:
            count = f.readinto(_CHUNK)
            if not count:
                break
            digest.update(view[:count])
    return hexlify(digest.digest()).decode()


def devices() -> "list[str]":
    # Every derived device, sorted: each devices/*.toml but a zz_test_ fixture, as the generator takes them.
    return sorted(name[:-5] for name in os.listdir("devices") if name.endswith(".toml") and not name.startswith("zz_test_"))


def require_fresh() -> None:
    try:
        with open(_STAMP) as f:
            stamp = json.load(f)
        recorded, outputs = stamp["inputs"], stamp["outputs"]
    except (OSError, ValueError, KeyError):  # absent, unreadable or not the generator's: the same refusal
        raise RuntimeError(_STALE) from None
    current = _inputs()
    if len(current) != len(recorded) or any(path not in recorded or _sha256(path) != recorded[path] for path in current):
        raise RuntimeError(_STALE)
    if _differs(outputs):
        raise RuntimeError(_STALE)
