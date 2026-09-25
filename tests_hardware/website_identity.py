"""Checks that the website the DUT actually serves is the one built for THIS device, not merely
non-empty (queue row G9). Every expected name is derived from `devices/<device>.toml` through
buildgen itself, so a new instance is covered the day it is declared rather than when someone edits a list."""

from __future__ import annotations

import gzip
import sys
from pathlib import Path
from typing import TYPE_CHECKING

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))  # buildgen lives at the repo root, which pytest does not put on sys.path itself

from buildgen.definitions import generate_definitions  # noqa: E402  (the sys.path line above is what makes this importable)
from buildgen.validate import build_model  # noqa: E402  (same)

if TYPE_CHECKING:
    from http_client import HttpResponse

DEVICES_DIR = REPO_ROOT / "devices"
SRC_DIR = REPO_ROOT / "src"


def decoded_body(res: HttpResponse) -> str:
    # The firmware serves index.html.gz, so the body is gzip whenever the server says so. Keyed on
    # the header rather than sniffed, so a future uncompressed build reads correctly instead of raising.
    encoding = next((v for k, v in res.headers.items() if k.lower() == "content-encoding"), "")
    raw = gzip.decompress(res.body) if "gzip" in encoding.lower() else res.body
    return raw.decode("utf-8", "replace")


def _errcount_keys(device: str) -> list[str]:
    model = build_model(DEVICES_DIR / f"{device}.toml", SRC_DIR)
    definitions = generate_definitions(model, SRC_DIR)
    for section in definitions["sections"]:
        for group in section.get("groups", []):
            if group.get("kind") == "errcount":
                return [module["key"] for module in group["modules"]]
    raise AssertionError(f"buildgen produced no errcount group for {device!r} - the definitions shape has changed")


def foreign_device_ids(device: str) -> list[str]:
    return sorted(p.stem for p in DEVICES_DIR.glob("*.toml") if p.stem != device)


def assert_page_is_this_devices_build(res: HttpResponse, link: str, device: str = "dev") -> None:
    """The one check that the image's website half matches its firmware half: a build for another
    device, or one predating generated definitions, passes `200`/non-empty but fails every line here."""
    body = decoded_body(res)
    assert body, f"GET / returned an empty body over {link}"

    assert f'"id": "{device}"' in body, f"the page served over {link} does not identify itself as {device!r} - it is not this device's build"
    missing = [key for key in _errcount_keys(device) if key not in body]
    assert not missing, f"the page served over {link} is missing {len(missing)} name(s) {device}.toml declares: {missing}"

    # dev is a superset of every other variant today, so no foreign errcount key exists to look for -
    # the device id is what actually discriminates, and it stays meaningful if that ever stops holding.
    intruders = [other for other in foreign_device_ids(device) if f'"id": "{other}"' in body]
    assert not intruders, f"the page served over {link} identifies itself as {intruders} as well as {device!r}"
