"""One evidence directory per run: $EVIDENCE_DIR when the hardware wrapper sets it (its archive run directory), else a
build/archive/pytest/<UTC>/ directory made once per process through scripts/_archive_evidence.py (newest three kept).
save_json()/save_text() write one small file each and never overwrite one: a name already there gains -<n>."""

import functools
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts._archive_evidence import new_run_dir

REPO_ROOT = Path(__file__).resolve().parent.parent

_RUNNER = "pytest"
# A file name keeps letters, digits and the punctuation a pytest node name carries; anything else (a path separator
# in a parametrize id included) becomes "_", so a reason can never name a file outside the directory.
_UNSAFE = re.compile(r"[^A-Za-z0-9._\-\[\]=]+")


def _free_path(name: str) -> Path:
    # The first of <name>, <stem>-1<suffix>, <stem>-2<suffix>, ... not yet taken, created empty so a second
    # writer racing this one takes the next.
    safe = Path(_UNSAFE.sub("_", name))
    directory = evidence_dir()
    candidate, n = directory / safe.name, 0
    while True:
        try:
            candidate.touch(exist_ok=False)
        except FileExistsError:
            n += 1
            candidate = directory / f"{safe.stem}-{n}{safe.suffix}"
        else:
            return candidate


@functools.cache
def _process_dir() -> Path:
    return new_run_dir(_RUNNER)


def evidence_dir() -> Path:
    override = os.environ.get("EVIDENCE_DIR")
    if override:
        path = Path(override)
        path.mkdir(parents=True, exist_ok=True)
        return path
    return _process_dir()


def save_json(name: str, obj: object) -> Path:
    return save_text(name, json.dumps(obj, indent=2, sort_keys=True) + "\n")  # serialised first: a failure leaves no file


def save_text(name: str, text: str) -> Path:
    path = _free_path(name)
    path.write_text(text, encoding="utf-8")
    return path
