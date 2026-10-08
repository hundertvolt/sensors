"""ext/freezefs/ stays byte-identical to the upstream commit it was vendored from: upstream publishes no
release tags, so the commit and these hashes are the pin. Moving it is a recorded re-vendor decision."""

import hashlib
from pathlib import Path

import pytest

# bixb922/freezefs `main` at this commit (2025-10-25); the five files are its freezefs/*.py and LICENSE.
UPSTREAM_COMMIT = "26be9e339a25e71f506f06a33a2346d6a13a07b8"
VENDORED_SHA256 = {
    "__main__.py": "b937e1778c506acf04f9ca32661bd27f6e74e893c8347d290308f2d042210990",
    "archive.py": "50278ef50bb5efb4b8abcaf22def127b885918677b770000c6a500ff3f933802",
    "ffsextract.py": "9a30a1939d495c27133b8953b462307b67fbd55a37effa48a6b81ae645fc59e3",
    "ffsmount.py": "e8bd4887ef1c35dc938ad016dcd2ec1213381e169533a2ca0257c5afe3da0f63",
    "LICENSE": "cd6a0db606632a8a736341a1066113e2bdd80cce06e73495a0a4903e01dce96e",
}


@pytest.mark.parametrize("name", sorted(VENDORED_SHA256))
def test_vendored_file_matches_the_pinned_upstream_commit(repo_root: Path, name: str) -> None:
    digest = hashlib.sha256((repo_root / "ext" / "freezefs" / name).read_bytes()).hexdigest()
    assert digest == VENDORED_SHA256[name], (
        f"ext/freezefs/{name} differs from bixb922/freezefs at {UPSTREAM_COMMIT}: vendored code is never edited "
        "in place, and moving to another upstream commit is a recorded re-vendor decision (hashes updated with it)."
    )


def test_nothing_else_is_vendored_there(repo_root: Path) -> None:
    present = {p.name for p in (repo_root / "ext" / "freezefs").iterdir() if p.name != "__pycache__"}
    assert present == set(VENDORED_SHA256), f"ext/freezefs/ holds {sorted(present)}, the pin covers {sorted(VENDORED_SHA256)}"
