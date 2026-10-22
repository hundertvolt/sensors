"""A littlefs model behind a module's `open`: a file written "w" reaches readers only at its close, a new file is
committed empty at its open, and the close after a failed write commits nothing. Runs under the MicroPython Unix port."""

import io

from _write_counters import WriteCountingOpen

# littlefs v2.11 on rp2 (v1.29.0, VfsLfs2): "w" on an existing file truncates in RAM only, a new file commits empty
# (lfs2.c:3146-3149, :3125-3128), close commits (:3473), and an errored file's close skips that commit (:3250-3253).


class LittlefsHandle:
    # One open-for-writing handle: the document reaches readers only at its close; a write error marks it errored, so
    # its close commits nothing.
    def __init__(self, files: "LittlefsOpen", path: str) -> None:
        self._files = files
        self._path = path
        self._parts: list[bytes] = []
        self._errored = False
        self._open = True

    def __enter__(self) -> "LittlefsHandle":
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def close(self) -> None:
        if not self._open:
            return
        self._open = False
        if not self._errored:
            self._files.docs[self._path] = b"".join(self._parts).decode()

    def write(self, data: "str | bytes") -> int:
        self._files.write_calls += 1
        if self._files.write_calls == self._files.fail_at:
            self._errored = True
            raise OSError(5, "EIO")
        chunk = data.encode() if isinstance(data, str) else bytes(data)
        self._parts.append(chunk)
        return len(chunk)


class LittlefsOpen(WriteCountingOpen):
    # While entered, `module`'s open() over that model: `docs` holds what a reader opening a file sees.
    def __init__(self, module: object, docs: "dict[str, str]") -> None:
        super().__init__(module)
        self.docs = docs
        self.write_calls = 0
        self.fail_at = 0  # the write call (from 1) that fails with EIO; 0: none

    def __call__(self, path: str, mode: str = "r") -> object:
        if "w" not in mode:
            self.reads += 1
            if path not in self.docs:
                raise OSError(2, "ENOENT")
            return io.StringIO(self.docs[path])
        self.writes += 1
        if path not in self.docs:
            self.docs[path] = ""
        return LittlefsHandle(self, path)
