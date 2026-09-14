"""A build's GC policy: the `gc.threshold()` value its generated boot entry sets, and whether the
build also carries the memory-pressure toolkit. One source of truth for buildgen,
scripts/build_firmware.py and tests_hardware/ alike - see SPECIFICATION.md Part I.4."""

from buildgen.errors import BuildError

# "reactive" is MicroPython's own real default - py/modgc.c's gc_threshold() disables the threshold
# for any negative value, leaving collection purely reactive. It is the harder case and the vital
# bar (I.4(e)); "threshold" is the shipped defense in depth layered on top of it (I.4(f)).
GC_POLICY_THRESHOLDS = {
    "reactive": -1,
    "threshold": 32768,
}
DEFAULT_GC_POLICY = "threshold"
GC_POLICIES = tuple(sorted(GC_POLICY_THRESHOLDS))

# Frozen into a --memory-pressure build only, and imported by name from both the generated boot
# entry and any pressure-marked device script. Its absence from an ordinary build is what makes
# "pressure tests never run against the shipped GC policy" structural rather than conventional.
PRESSURE_MODULE = "memory_pressure"


def threshold_for(policy: str, device: str = "") -> int:
    if policy not in GC_POLICY_THRESHOLDS:
        raise BuildError(device, f"unknown gc policy {policy!r} - expected one of {', '.join(GC_POLICIES)}", field="gc_policy")
    return GC_POLICY_THRESHOLDS[policy]


def check_pressure_policy(policy: str, device: str = "", *, memory_pressure: bool) -> None:
    # Pressure under a proactive threshold measures the collector, not the design: the churn it
    # creates is exactly what the threshold collects away (I.4(e)). Refused rather than warned.
    if memory_pressure and policy != "reactive":
        raise BuildError(device, f"--memory-pressure needs gc policy 'reactive', not {policy!r} - a proactive threshold collects the churn away and the run measures nothing", field="gc_policy")
