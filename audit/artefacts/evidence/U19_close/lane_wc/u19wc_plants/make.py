"""Writes one overlay copy of src/asy_webserver_service.py per planted regression (src itself is never touched)."""
import pathlib
import sys

WT = pathlib.Path("/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/wt-u19wc")
OUT = pathlib.Path(sys.argv[1])
SRC = (WT / "src/asy_webserver_service.py").read_text()

PLANTS = {
    "P01_no_rebind": [("        microdot.print_exception = self._print_exception  # type: ignore[attr-defined]\n", "        pass\n")],
    "P02_no_write_reset": [("""        try:
            await self._bounded(self._stream.awrite(data))
        except OSError:
            # Microdot mutes ECONNRESET/EPIPE from a response write (ext/microdot.py:56-61, 689-705), so a client gone
            # mid-response is recorded here; the early return above then stops further writes.
            self._peer_gone[0] = True
            raise
""", "        await self._bounded(self._stream.awrite(data))\n")],
    "P03_no_refusal_trace": [('await self._note_drop(_WRN_HTTP_REFUSED, "Connection refused at the ceiling")', "pass")],
    "P04_reset_keeps_window": [("        self._dropped.reset()  # ResetErrors", "        pass  # ResetErrors")],
    "P05_window_never_moves": [("return self._dropped.total(await self._uptime_s())", "return self._dropped.total(0)")],
    "P06_no_length_rule": [("if self._length_seen or not text[colon + 1 :].strip().isdigit():", "if False:")],
    "P07_no_count_rule": [("if self._head_lines <= _MAX_HEADER_LINES:", "if True:")],
    "P08_no_total_rule": [("if len(line) > limit or self._head_bytes > _MAX_HEAD_BYTES:", "if len(line) > limit:")],
    "P09_unchunked_read": [("min(limit + 1 - len(buf), self._chunk)", "limit + 1 - len(buf)")],
    "P10_eof_not_refused": [("        except EOFError:  # the body ended", "        except KeyError:  # the body ended")],
    "P11_no_te_rule": [('if name == "transfer-encoding":', 'if name == "x-never":')],
    "P12_ungated_print": [("""        if isinstance(exc, MemoryError):
            console(_NAME, "Microdot caught:", exc)
        else:
            self.pr.err("Microdot caught:", exc)
""", """        console(_NAME, "Microdot caught:", exc)
""")],
    "P13_no_peer_trace": [('await self._note_drop(_WRN_HTTP_PEER_RESET, "Connection reset by the peer before or during its response")', "pass")],
    "P14_no_head_trace": [('await self._note_drop(_WRN_HTTP_BAD_HEAD, "Request head refused")', "pass")],
    "P15_unbounded_write": [("""        try:
            return await asyncio.wait_for(coro, self._timeout_s)
        except asyncio.TimeoutError:
            self._timed_out[0] = True""", """        try:
            return await coro
        except asyncio.TimeoutError:
            self._timed_out[0] = True""")],
    "P16_no_start_retry": [("if attempt >= _START_RETRIES:", "if attempt >= 1:")],
    "P17_cancel_not_forwarded": [("        await server.wait_closed()\n", "        await asyncio.Event().wait()\n")],
    "P18_eof_is_a_bad_head": [("            if not data:\n                break\n", "            if not data:\n                self._refuse()\n")],
    "P19_window_ignores_uptime": [("self._dropped.add(await self._uptime_s())", "self._dropped.add(0)")],
    "P20_tiny_write_bound": [("""        try:
            return await asyncio.wait_for(coro, self._timeout_s)
        except asyncio.TimeoutError:
            self._timed_out[0] = True""", """        try:
            return await asyncio.wait_for(coro, 0.001)
        except asyncio.TimeoutError:
            self._timed_out[0] = True""")],
    "P21_short_read_bound": [("""        try:
            return await asyncio.wait_for(coro, self._timeout_s)
        except asyncio.TimeoutError as e:""", """        try:
            return await asyncio.wait_for(coro, 0.5)
        except asyncio.TimeoutError as e:""")],
    "P22_digit_cap": [("if self._length_seen or not text[colon + 1 :].strip().isdigit():", "if self._length_seen or not text[colon + 1 :].strip().isdigit() or len(text[colon + 1 :].strip()) > 10:")],
    "P24_socket_error_also_traced": [("""                await self.pr.wrn_s("Connection reclaimed (socket error):", e, wrnno=_WRN_HTTP_SOCKET_ERROR)
                logged = True
""", """                await self.pr.wrn_s("Connection reclaimed (socket error):", e, wrnno=_WRN_HTTP_SOCKET_ERROR)
""")],
    "P23_short_line_limit": [("        limit = Request.max_readline  # Microdot's own bound", "        limit = 1024  # Microdot's own bound")],
}

for name, edits in PLANTS.items():
    text = SRC
    for old, new in edits:
        assert text.count(old) == 1, (name, old[:60], text.count(old))
        text = text.replace(old, new)
    d = OUT / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "asy_webserver_service.py").write_text(text)
print(" ".join(PLANTS))
