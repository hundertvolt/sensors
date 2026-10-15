"""Included into device scripts at render (harness.render_device_script()): a script reports what it measured as
FACT <key>=<json> lines and ends with DONE; the host test parses them (harness.parse_facts()) and gives the verdict.
A failure list is one fact, its total beside the first few, so a persistent fault never floods the console."""

import json

# @tunable l3.device_script_errors_kept = 5
_ERRORS_KEPT = 5


def done() -> None:
    print("DONE")


def errors(key: str, total: int, first: "list[str]") -> None:
    fact(key, {"total": total, "first": first[:_ERRORS_KEPT]})


def fact(key: str, value: object) -> None:
    print("FACT " + key + "=" + json.dumps(value))
