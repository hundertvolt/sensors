"""Writes the NTP config a twin or Unix-port boot starts from, so no run reaches a public NTP or DNS host: the twin's
local responder on loopback, or TEST-NET-1 (RFC 5737) where a run must not sync; never a DNS fallback."""

import json
import os

from asy_config_manager import config_filename

# src/asy_ntp_client.py's _NAME, the NTP store's own name: a private const() is no module attribute at run time
# (py/parse.c, v1.29.0), so this is a named copy of it.
_NTP_STORE_NAME = "NTP"
_OFFLINE_HOST = "192.0.2.1"  # RFC 5737 TEST-NET-1: routed nowhere, so no sync attempt leaves the host
_RESPONDER_HOST = "127.0.0.1"  # the twin's local NTP responder (_ntp_responder.py)
# The store's other keys at src/asy_ntp_client.py's defaults (tests_scripts/test_offline_ntp_config.py pins both): a
# store missing a key warns once per key at every fresh boot, in a FRAM-backed log.
_STORE_DEFAULTS = {"NTPOffset": 0, "NTPInterval": 12, "GMTOffset": 3600, "DSTOffset": 3600}


def write_ntp_config(cfg_dir: str, host: str) -> None:
    # The whole NTP store in the product's flat config format, its host and an empty fallback set; only when absent: a
    # file a test planted, or an earlier boot of the same directory wrote, is the run's own state and stays as it is.
    path = config_filename(cfg_dir, _NTP_STORE_NAME)
    try:
        os.stat(path)
    except OSError:
        store: dict[str, object] = dict(_STORE_DEFAULTS)
        store["NTPHost"] = host
        store["DNSFallback"] = ""
        with open(path, "w") as f:
            f.write(json.dumps(store))


def write_offline_ntp_config(cfg_dir: str) -> None:
    write_ntp_config(cfg_dir, _OFFLINE_HOST)


def write_responder_ntp_config(cfg_dir: str) -> None:
    write_ntp_config(cfg_dir, _RESPONDER_HOST)
