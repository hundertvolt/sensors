"""Per-test-file scratch space under tests/_tmp/<key>/: wiped clean at construction and by
teardown_all() (tests/microtest.py's run()), so no file's leftovers depend on another file - or a
later run of itself - to clean up. Every op stays scoped to <key>, never tests/_tmp's shared root."""

import os

_ROOT = "tests/_tmp"

_registered: "list[TmpScratch]" = []


def _remove_tree(path: str) -> None:
    try:
        entries = os.listdir(path)
    except OSError:
        pass  # path doesn't exist - nothing to remove
    else:
        for entry in entries:
            child = path + "/" + entry
            try:
                os.remove(child)
                continue
            except OSError:
                pass  # a directory, not a file - recurse below
            _remove_tree(child)
            try:
                os.rmdir(child)
            except OSError:
                pass
    try:
        os.rmdir(path)
    except OSError:
        pass  # already gone, or never existed


class TmpScratch:
    """One test file's own scratch directory (tests/_tmp/<key>/). Construct once at module level
    with a key unique to that file (its old sweep prefix works fine); dir()/path() then hand out
    fresh, isolated locations for that process's own test functions."""

    def __init__(self, key: str) -> None:
        self._dir = _ROOT + "/" + key
        _remove_tree(self._dir)  # this file's own leftovers from an earlier run - never another file's
        self._next = 0
        _registered.append(self)

    def _ensure_dir(self) -> None:
        try:
            os.mkdir(_ROOT)
        except OSError:
            pass
        try:
            os.mkdir(self._dir)
        except OSError:
            pass

    def dir(self, label: str = "") -> str:
        """A fresh, numbered subdirectory - the _tmp_cfg_dir()-style shape most callers need."""
        self._ensure_dir()
        self._next += 1
        name = str(self._next) + ("_" + label if label else "")
        path = self._dir + "/" + name
        try:
            os.mkdir(path)
        except OSError:
            pass
        return path + "/"

    def path(self, name: str) -> str:
        """A single, guaranteed-fresh file path (not a directory) - the _tmp_path()-style shape
        the files writing one flat config file per test need instead."""
        self._ensure_dir()
        full = self._dir + "/" + name
        try:
            os.remove(full)
        except OSError:
            pass  # not present yet - already fresh
        return full

    def teardown(self) -> None:
        _remove_tree(self._dir)


def teardown_all() -> None:
    for scratch in _registered:
        scratch.teardown()
    _registered.clear()
