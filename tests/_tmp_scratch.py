"""Per-test-file scratch space under tests/_tmp/<key>/: wiped clean at construction and by teardown_all() (microtest's
run()), every op scoped to <key>, never tests/_tmp's shared root. A key is live once per process; a cleanup failure
other than absence (and a directory already there) is raised naming its path."""

import errno
import os

_ROOT = "tests/_tmp"
_S_IFDIR = 0x4000  # os.ilistdir()'s and os.stat()'s directory type bits (extmod/vfs.h MP_S_IFDIR)
_S_IFMT = 0xF000

_registered: "list[TmpScratch]" = []


def _os_call(op: str, path: str, tolerated: int) -> bool:
    # os.<op>(path): False when it failed with `tolerated` (absent, or already there), True when done; any other
    # failure is raised again naming the operation and the path.
    try:
        getattr(os, op)(path)
    except OSError as e:
        if e.errno == tolerated:
            return False
        raise OSError(e.errno, op + " " + path) from None
    return True


def _remove_tree(path: str) -> None:
    try:
        entries = list(os.ilistdir(path))
    except OSError as e:
        if e.errno == errno.ENOENT:
            return  # absent: nothing to remove
        raise OSError(e.errno, "ilistdir " + path) from None
    for entry in entries:
        child = path + "/" + entry[0]
        kind = entry[1] or os.stat(child)[0] & _S_IFMT  # 0: the filesystem gave no type (DT_UNKNOWN)
        if kind == _S_IFDIR:
            _remove_tree(child)
        else:
            _os_call("remove", child, errno.ENOENT)
    _os_call("rmdir", path, errno.ENOENT)


class TmpScratch:
    # One test file's own scratch directory (tests/_tmp/<key>/). Construct once at module level with a key unique
    # across files; dir()/path() then hand out fresh, isolated locations for that process's own test functions.

    def __init__(self, key: str) -> None:
        self._dir = _ROOT + "/" + key
        if any(scratch._dir == self._dir for scratch in _registered):
            raise AssertionError("TmpScratch key " + key + " already in use")
        _remove_tree(self._dir)  # this file's own leftovers from an earlier run - never another file's
        self._next = 0
        _registered.append(self)

    def _ensure_dir(self) -> None:
        _os_call("mkdir", _ROOT, errno.EEXIST)
        _os_call("mkdir", self._dir, errno.EEXIST)

    def dir(self, label: str = "") -> str:
        # A fresh, numbered subdirectory - the _tmp_cfg_dir()-style shape most callers need.
        self._ensure_dir()
        self._next += 1
        name = str(self._next) + ("_" + label if label else "")
        path = self._dir + "/" + name
        _os_call("mkdir", path, errno.EEXIST)
        return path + "/"

    def path(self, name: str) -> str:
        # A single, guaranteed-fresh file path (not a directory) - the _tmp_path()-style shape the files writing one
        # flat config file per test need instead.
        self._ensure_dir()
        full = self._dir + "/" + name
        _os_call("remove", full, errno.ENOENT)  # absent is already fresh
        return full

    def teardown(self) -> None:
        _remove_tree(self._dir)


def teardown_all() -> None:
    for scratch in _registered:
        scratch.teardown()
    _registered.clear()
