"""Isolated-driver device script: WP4/Topic 6's own real-hardware capacity check - after a full
build_system(), every module that should have inherited a real FRAM chunk (own pr, plus its own
cfgmgr where one exists) actually has one, not a silently-degraded RAM-only fallback. Deliberately
NOT `fram.allocated_size <= fram.size` - that can never be false by construction
(AsyFramManager.get_chunk() checks capacity before incrementing, never after), so it would be a
tautology, not a check; a None chunk reference on a module that should have gotten one is the real,
observable signal capacity ran out. mpremote-only by design (owner's own decision, WP_RESTART_HANDOVER.md's
Topic 6) - no new /status field, this is a one-time build-validity fact, not live operational state."""

import asyncio

import sensortask_dev

failures: list[str] = []

# Every mandatory-infra/optional-instance name dev's own build_system() constructs that could hold
# a FRAM-backed logger - checked generically via getattr(), not by importing the real classes,
# since not every device wires every one of these (this script is dev-specific, but written the
# same way the mock tier's own tests are, so it stays correct if dev's own TOML ever changes).
_CANDIDATE_MODULE_NAMES = (
    "conn", "ntp", "sysfunct", "scd30", "sgp40", "bmp3xx", "isl29125", "neopixel", "notification", "webserver",
    "uart_link_init", "uart_link_resp",
)


def _check_fram_backed(label: str, pr: object) -> None:
    if not hasattr(pr, "fram"):
        failures.append(f"{label}.pr is not a PrintLogHistoryStore at all (expected FRAM-backed - dev.toml wires fram_target everywhere)")
        return
    if pr.fram is None:
        failures.append(f"{label}.pr.fram is None - FRAM allocation failed for this module's own logger")


async def _main() -> None:
    try:
        await sensortask_dev.build_system(cfg_path="", web_host="127.0.0.1", web_port=8080)
    except Exception as e:
        print(f"RESULT: FAIL build_system() raised on real hardware: {e!r}")
        return

    assert sensortask_dev.fram is not None
    for name in _CANDIDATE_MODULE_NAMES:
        module = getattr(sensortask_dev, name, None)
        if module is None:
            continue
        _check_fram_backed(name, module.pr)
        cfgmgr = getattr(module, "cfgmgr", None)
        if cfgmgr is not None:
            _check_fram_backed(f"{name}.cfgmgr", cfgmgr.pr)

    if failures:
        print("RESULT: FAIL " + "; ".join(failures))
        return
    print(
        f"RESULT: PASS every FRAM-wired module's own chunk allocated successfully "
        f"(fram.allocated_size={sensortask_dev.fram.allocated_size}, fram.size={sensortask_dev.fram.size})",
    )


asyncio.run(_main())
