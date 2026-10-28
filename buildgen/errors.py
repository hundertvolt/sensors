"""Fail-loud build errors (SPECIFICATION.md Part L.5's build-tooling quality bar): every
abort names exactly what's wrong and where - device, instance/bus, field - never a raw traceback
or a generic "build failed"."""


class BuildError(Exception):
    # rule: a stable kebab-case id of the broken rule; fix: one imperative sentence, appended to
    # the message as " - fix: <fix>".
    def __init__(self, device: str, message: str, *, rule: str, fix: str, instance: str | None = None, field: str | None = None) -> None:
        self.device = device
        self.instance = instance
        self.field = field
        self.message = message
        self.rule = rule
        self.fix = fix
        where = device
        if instance is not None:
            where += "/" + instance
        if field is not None:
            where += "." + field
        super().__init__(f"[{where}] {message} - fix: {fix}")


class BuildInternalError(Exception):
    # A generator bug, never a TOML mistake: it propagates with its traceback.
    pass
