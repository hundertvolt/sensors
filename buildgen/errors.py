"""Fail-loud build errors (BUILD_CHAIN_PLAN.md's "Build/generator script quality bar"): every
abort names exactly what's wrong and where - device, instance/bus, field - never a raw traceback
or a generic "build failed"."""


class BuildError(Exception):
    def __init__(self, device: str, message: str, *, instance: str | None = None, field: str | None = None) -> None:
        self.device = device
        self.instance = instance
        self.field = field
        self.message = message
        where = device
        if instance is not None:
            where += "/" + instance
        if field is not None:
            where += "." + field
        super().__init__(f"[{where}] {message}")
