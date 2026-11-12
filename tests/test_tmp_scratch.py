"""Regression coverage for _tmp_scratch.py's TmpScratch, the per-test-file scratch directory: every operation stays
inside its own key's subtree, and a cleanup failure other than absence is raised."""

import errno
import os

import _tmp_scratch  # the module object itself, for the os-swap in the shared-root invariant test
from _tmp_scratch import _ROOT, TmpScratch, teardown_all

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Iterator


def _exists(path: str) -> bool:
    try:
        os.stat(path)
    except OSError:
        return False
    return True


def _write(path: str, content: str = "x") -> None:
    with open(path, "w") as f:
        f.write(content)


def test_dir_returns_a_fresh_existing_directory_each_call() -> None:
    scratch = TmpScratch("scratchtest_fresh")
    try:
        first = scratch.dir()
        second = scratch.dir()
        assert first != second
        assert _exists(first.rstrip("/"))
        assert _exists(second.rstrip("/"))
    finally:
        scratch.teardown()


def test_dir_accepts_an_optional_label_for_readability() -> None:
    scratch = TmpScratch("scratchtest_label")
    try:
        path = scratch.dir("scd30")
        assert path.rstrip("/").endswith("_scd30")
    finally:
        scratch.teardown()


def test_path_returns_a_file_location_not_yet_present() -> None:
    scratch = TmpScratch("scratchtest_path")
    try:
        path = scratch.path("config_NOTIFY.cfg")
        assert not _exists(path)
    finally:
        scratch.teardown()


def test_path_removes_a_value_left_by_an_earlier_call_with_the_same_name() -> None:
    # The exact bug _sweep_stale_tmp_dirs() existed for: a second call reusing the same name must
    # never silently observe a value an earlier call in this same run already wrote.
    scratch = TmpScratch("scratchtest_path_reuse")
    try:
        path = scratch.path("config_NOTIFY.cfg")
        _write(path, "first")
        path_again = scratch.path("config_NOTIFY.cfg")
        assert path_again == path
        assert not _exists(path_again)
    finally:
        scratch.teardown()


def test_teardown_removes_the_whole_subtree_including_nested_files() -> None:
    scratch = TmpScratch("scratchtest_teardown")
    d = scratch.dir()
    _write(d + "config_A.cfg")
    _write(d + "config_B.cfg")

    scratch.teardown()

    assert not _exists(d.rstrip("/"))
    assert not _exists(_ROOT + "/scratchtest_teardown")


def test_constructing_a_new_scratch_wipes_a_stale_directory_left_by_an_earlier_process() -> None:
    # Simulates a previous run of this same file, whose _next_dir would have restarted at 0 and reused the
    # same directory name, leaving a real persisted config file behind - the actual mechanism that used to
    # make a "Valid" write silently read back as "Unchanged". A fresh TmpScratch() must not let it survive.
    stale = _ROOT + "/scratchtest_stale/1"
    try:
        os.mkdir(_ROOT)
    except OSError:
        pass
    os.mkdir(_ROOT + "/scratchtest_stale")
    os.mkdir(stale)
    _write(stale + "/config_NTP.cfg", '{"NTPHost": "stale.example.org"}')

    scratch = TmpScratch("scratchtest_stale")
    try:
        assert not _exists(stale)  # the whole key directory, this leftover included, is gone
        fresh = scratch.dir()
        assert not _exists(fresh + "config_NTP.cfg")
    finally:
        scratch.teardown()


def test_two_scratch_keys_never_touch_each_others_directories() -> None:
    a = TmpScratch("scratchtest_iso_a")
    b = TmpScratch("scratchtest_iso_b")
    try:
        keep = b.dir()
        _write(keep + "marker.cfg")

        a.teardown()  # must not affect b's own directory at all

        assert _exists(keep + "marker.cfg")
    finally:
        a.teardown()
        b.teardown()


def test_construction_and_teardown_tolerate_a_missing_key_directory_entirely() -> None:
    # The first use of a key has nothing to remove: construction and two teardowns stay inside the key's own path,
    # never the shared root, and leave no key directory behind.
    calls: list[tuple[str, str]] = []
    own = _ROOT + "/scratchtest_never_used_before"
    with _recording(_RecordingOs(calls)):
        scratch = TmpScratch("scratchtest_never_used_before")
        scratch.teardown()
        scratch.teardown()  # a second, redundant teardown is a no-op too
    assert calls, "recorded nothing - the os wrappers never took effect"
    assert all(path == own for _name, path in calls), calls
    assert not _exists(own)


def test_teardown_all_clears_every_registered_scratch_and_the_registry_itself() -> None:
    a = TmpScratch("scratchtest_all_a")
    b = TmpScratch("scratchtest_all_b")
    dir_a = a.dir()
    dir_b = b.dir()

    teardown_all()

    assert not _exists(dir_a.rstrip("/"))
    assert not _exists(dir_b.rstrip("/"))
    # A second call must be a cheap no-op, not re-walk (and re-fail on) already-removed paths.
    teardown_all()


class _RecordingOs:
    # Stands in for the `os` binding inside _tmp_scratch itself, recording (call, path) for every directory
    # operation and forwarding to the real one. Swapping a module's own imported name is this project's
    # mocking mechanism, MicroPython having no unittest.mock, and the builtin module cannot be patched.
    def __init__(self, calls: "list[tuple[str, str]]") -> None:
        self._calls = calls

    def ilistdir(self, path: str) -> "Iterator[tuple[str, int, int] | tuple[str, int, int, int]]":
        self._calls.append(("ilistdir", path))
        return os.ilistdir(path)

    def listdir(self, path: str) -> "list[str]":
        self._calls.append(("listdir", path))
        return os.listdir(path)

    def mkdir(self, path: str) -> None:
        self._calls.append(("mkdir", path))
        os.mkdir(path)

    def remove(self, path: str) -> None:
        self._calls.append(("remove", path))
        os.remove(path)

    def rmdir(self, path: str) -> None:
        self._calls.append(("rmdir", path))
        os.rmdir(path)

    def stat(self, path: str) -> "tuple[int, ...]":
        self._calls.append(("stat", path))
        return os.stat(path)


class _RaisingOs(_RecordingOs):
    # The recorder, with one operation on one path raising the given errno before reaching the real call.
    def __init__(self, op: str, path: str, code: int) -> None:
        super().__init__([])
        self._fault = (op, path, code)

    def _raise_if(self, op: str, path: str) -> None:
        if (op, path) == self._fault[:2]:
            raise OSError(self._fault[2])

    def mkdir(self, path: str) -> None:
        self._raise_if("mkdir", path)
        super().mkdir(path)

    def remove(self, path: str) -> None:
        self._raise_if("remove", path)
        super().remove(path)

    def rmdir(self, path: str) -> None:
        self._raise_if("rmdir", path)
        super().rmdir(path)


class _recording:
    # Installs a stand-in as _tmp_scratch's own `os` for the block.
    def __init__(self, stand_in: _RecordingOs) -> None:
        self._stand_in = stand_in

    def __enter__(self) -> _RecordingOs:
        _tmp_scratch.os = self._stand_in  # type: ignore[assignment]
        return self._stand_in

    def __exit__(self, *_exc_info: object) -> None:
        _tmp_scratch.os = os


def test_a_cleanup_failure_other_than_absence_is_raised_naming_its_path() -> None:
    scratch = TmpScratch("scratchtest_rmdir_refused")
    nested = scratch.dir()
    raised = ""
    with _recording(_RaisingOs("rmdir", nested.rstrip("/"), errno.EACCES)):
        try:
            scratch.teardown()
        except OSError as e:
            raised = str(e)
    assert str(errno.EACCES) in raised and nested.rstrip("/") in raised, raised
    scratch.teardown()  # the real os again: the subtree goes


def test_an_existing_directory_and_an_absent_file_are_no_failure() -> None:
    scratch = TmpScratch("scratchtest_tolerated")
    with _recording(_RaisingOs("mkdir", _ROOT, errno.EEXIST)):
        path = scratch.path("absent.cfg")  # mkdir(_ROOT) answers EEXIST, remove() of the fresh name ENOENT
    assert not _exists(path)
    scratch.teardown()


def test_a_key_still_in_use_is_refused_until_teardown_all_releases_it() -> None:
    first = TmpScratch("scratchtest_live_key")
    raised = ""
    try:
        TmpScratch("scratchtest_live_key")
    except AssertionError as e:
        raised = str(e)
    assert raised == "TmpScratch key scratchtest_live_key already in use", raised
    first.teardown()
    teardown_all()
    TmpScratch("scratchtest_live_key").teardown()


def test_no_operation_ever_reads_the_shared_root_only_its_own_key_subtree() -> None:
    # The whole point of TmpScratch over the retired per-file _sweep_stale_tmp_dirs() trio, asserted as the
    # structural invariant it actually is - "every op stays scoped to <key>, never tests/_tmp's shared root"
    # - rather than inferred from a symptom.
    #
    # The old shape's real failure was an os.listdir() on the shared root, whose allocation scales with
    # every file's leftover entries, so what has to stay true is simply that no TmpScratch operation reads
    # that root. Proven directly by recording every os call a full lifecycle makes.
    #
    # This replaces a test that populated the shared root with 400,000 real sibling directories to reproduce
    # that MemoryError, at a measured 396MB of physical disk writes per run, in two CI jobs plus every local
    # run, to re-demonstrate a defect in an implementation this repo no longer contains.
    #
    # The assertion is also strictly stronger: a reintroduced listdir(_ROOT) fails here immediately, where
    # the scale test only noticed once the root had grown enormous.
    calls: list[tuple[str, str]] = []
    key = "scratchtest_root_untouched"
    own = _ROOT + "/" + key
    with _recording(_RecordingOs(calls)):
        scratch = TmpScratch(key)  # construction wipes its own subtree
        _write(scratch.path("flat.cfg"))
        _write(scratch.dir() + "nested.cfg")
        scratch.dir("labelled")
        scratch.teardown()

    assert calls, "recorded nothing - the os wrappers never took effect, so this test proves nothing"
    for name, path in calls:
        assert not (name in ("listdir", "ilistdir", "stat") and path.rstrip("/") == _ROOT), f"{name}({path!r}) reads tests/_tmp's shared root - the one thing TmpScratch must never do, since that allocation scales with every other file's entries"
        # mkdir(_ROOT) is the one legitimate touch of the root itself: idempotent, EEXIST-swallowed,
        # and what makes concurrent construction from several test processes safe.
        assert (name == "mkdir" and path.rstrip("/") == _ROOT) or path.startswith(own + "/") or path == own, f"{name}({path!r}) escapes this scratch's own {own!r} subtree"

    assert not _exists(own)  # teardown still actually removed it


def test_unrelated_siblings_in_the_shared_root_do_not_affect_a_scratchs_own_behavior() -> None:
    # The behavioral companion to the structural assertion above: with unrelated entries in the shared root,
    # a scratch's construct/dir/teardown cycle still works and leaves them alone. A deliberately cheap
    # population - the invariant is independence from sibling COUNT, which a handful proves as well.
    try:
        os.mkdir(_ROOT)
    except OSError:
        pass
    siblings = [_ROOT + "/unrelated_sibling_" + str(i) for i in range(25)]
    for path in siblings:
        try:
            os.mkdir(path)
        except OSError:
            pass
    try:
        scratch = TmpScratch("scratchtest_sibling_independence")
        created = [scratch.dir() for _ in range(3)]
        for path in created:
            assert _exists(path)
        scratch.teardown()
        for path in created:
            assert not _exists(path)
        for path in siblings:
            assert _exists(path), f"teardown removed an unrelated sibling {path!r} - it must only ever touch its own key subtree"
    finally:
        for path in siblings:
            try:
                os.rmdir(path)
            except OSError:
                pass


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
