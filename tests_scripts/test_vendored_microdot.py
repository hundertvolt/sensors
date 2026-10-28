"""The vendored Microdot is pinned by sha256 to the upstream tag THIRD_PARTY_LICENSES.md records: the module,
its licence and upstream's type stubs are never edited, only re-vendored whole from a tag (CLAUDE.md's
vendoring rule), so any other change to one of them fails here, with no network or git history needed."""

import hashlib
import re
from pathlib import Path

import pytest

# {path: (tag, sha256)}: each file as upstream miguelgrinberg/microdot ships it at the tag (the module, its
# licence, its type stubs), hashed from the tag's own tree.
_PINNED: "dict[str, tuple[str, str]]" = {
    "ext/microdot.py": ("v2.7.0", "d9e0bea681d15965e8c683f642e03536fbed34e0bc55fe5000324208924936c1"),
    "ext/LICENSE-microdot": ("v2.7.0", "1f509e83450df3402a221384fdf1508bae2e00ecddaa5b5cf3bbc5aa7d29f72c"),
    "ext/typings/microdot/__init__.pyi": ("v2.7.0", "6fed3ee85f723853cbb5652a2af0248596e923f271b1d0760387976485b5b6a8"),
    "ext/typings/microdot/microdot.pyi": ("v2.7.0", "f6a3c4d99fc6e70231ad2eb852c1ba84a8d1f5a4a4e0ff316c9be4a60ea1a2ee"),
    "ext/typings/microdot/multipart.pyi": ("v2.7.0", "208e93559e2501ef66cf88fea88696ca76cb951ae14310da5da25f3ae588ae8c"),
}
_STUB_DIR = "ext/typings/microdot"
_RECORDED_TAG = re.compile(r"`ext/microdot\.py`, pinned `(v\d+\.\d+\.\d+)`")


@pytest.mark.parametrize("path", sorted(_PINNED))
def test_each_vendored_file_is_byte_identical_to_its_tag(repo_root: Path, path: str) -> None:
    tag, pinned = _PINNED[path]
    actual = hashlib.sha256((repo_root / path).read_bytes()).hexdigest()
    assert actual == pinned, (
        f"{path} is not Microdot {tag} as vendored (sha256 {actual}, pinned {pinned}). The file is never edited; "
        f"moving to another tag is a recorded decision in THIRD_PARTY_LICENSES.md, re-vendored whole with this table."
    )


def test_every_vendored_microdot_file_is_in_the_table(repo_root: Path) -> None:
    # A stub file upstream adds at a later tag joins the table with it, never unpinned.
    on_disk = {"ext/microdot.py", "ext/LICENSE-microdot", *(f"{_STUB_DIR}/{p.name}" for p in (repo_root / _STUB_DIR).iterdir())}
    assert on_disk == set(_PINNED)


def test_the_table_pins_the_one_tag_third_party_licenses_records(repo_root: Path) -> None:
    recorded = _RECORDED_TAG.search((repo_root / "THIRD_PARTY_LICENSES.md").read_text(encoding="utf-8"))
    assert recorded is not None, "THIRD_PARTY_LICENSES.md no longer names ext/microdot.py's pinned tag"
    assert {tag for tag, _digest in _PINNED.values()} == {recorded.group(1)}
