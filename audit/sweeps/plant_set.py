"""The planted set (owner's scope): named bites, the boot entry's decisions, the K rows, the memory gates, the
complex-measurement seeds. Each edit names a regex that must match exactly `count` lines; `sub` is literal text."""

import re


def mp(f, dev=None):
    return {"file": f"tests/{f}", "level": "mp", **({"device": dev} if dev else {})}


def host(f, *args):
    return {"file": f, "level": "host", "args": list(args)}


def js(f):
    return {"file": f, "level": "js"}


def sub(row, pid, file, match, old, new, tests, why="", count=1, nth=0):
    return {"id": pid, "row": row, "why": why, "edits": [{"file": file, "match": match, "sub": [re.escape(old), new], "count": count, "nth": nth}], "tests": tests}


def ins(row, pid, file, match, lines, tests, why="", indent=0):
    return {"id": pid, "row": row, "why": why, "edits": [{"file": file, "match": match, "insert": lines, "indent": indent}], "tests": tests}


def app(row, pid, file, text, tests, why=""):
    return {"id": pid, "row": row, "why": why, "edits": [{"file": file, "append": text}], "tests": tests}


BC, SS, WS, PL = "src/asy_base_classes.py", "src/asy_system_service.py", "src/asy_webserver_service.py", "src/asy_print_log.py"
UC, UD, UL, FM = "src/asy_uart_comm.py", "src/asy_uart_driver.py", "src/asy_uart_link_driver.py", "src/asy_fram_manager.py"
NO, NP, IS, CG = "src/asy_notification_service.py", "src/asy_neopixel_driver.py", "src/asy_isl29125_driver.py", "buildgen/codegen.py"
T_BC, T_SS, T_WS, T_PL = [mp("test_asy_base_classes.py")], [mp("test_asy_system_service.py")], [mp("test_asy_webserver_service.py")], [mp("test_asy_print_log.py")]
T_UC, T_UD, T_UL, T_FM = [mp("test_asy_uart_comm.py")], [mp("test_asy_uart_driver.py")], [mp("test_asy_uart_link_driver.py")], [mp("test_asy_fram_manager.py")]


def cap_pair(row, file, match, old, flipped, dropped, tests, count=1, nth=0):
    # The two K plants: the cap's comparison flipped, and the check dropped.
    return [sub(row, f"{row}-flip", file, match, old, flipped, tests, count=count, nth=nth), sub(row, f"{row}-drop", file, match, old, dropped, tests, count=count, nth=nth)]


PLANTS = [
    # K rows: two plants each
    *cap_pair("K.01", BC, r"if current < self\._max_val:  # checked before", "if current < self._max_val:", "if current <= self._max_val:", "if True:", T_BC),
    *cap_pair("K.bins", BC, r"if self\._bins\[i\] < COUNTER_CAP:", "if self._bins[i] < COUNTER_CAP:", "if self._bins[i] <= COUNTER_CAP:", "if True:", T_BC),
    *cap_pair("K.bins-total", BC, r"if b >= COUNTER_CAP - s:", "if b >= COUNTER_CAP - s:", "if b > COUNTER_CAP - s:", "if False:", T_BC),
    *cap_pair("K.02-06-08", BC, r"self\._value = self\._value \+ secs if self\._value < COUNTER_CAP - secs else COUNTER_CAP", "self._value + secs if self._value < COUNTER_CAP - secs else COUNTER_CAP", "self._value + secs if self._value <= COUNTER_CAP - secs else COUNTER_CAP", "self._value + secs", T_BC),
    *cap_pair("K.12-down", BC, r"self\._value = self\._value - secs if self\._value > secs else 0", "self._value - secs if self._value > secs else 0", "self._value - secs if self._value >= secs else 0", "self._value - secs", T_BC),
    *cap_pair("K.12-cap", NO, r"self\._pause\.restart\(min\(max\(secs, 0\), _MAX_OVERRIDE_TIME\)\)", "min(max(secs, 0), _MAX_OVERRIDE_TIME)", "min(max(secs, 0), _MAX_OVERRIDE_TIME + 1)", "max(secs, 0)", [mp("test_asy_notification_service.py")]),
    *cap_pair("K.04", SS, r"return budget \+ _TASK_FAIL_INCREMENT if budget <= _TASK_FAIL_MAX else budget", " if budget <= _TASK_FAIL_MAX else budget", " if budget < _TASK_FAIL_MAX else budget", "", T_SS),
    *cap_pair("K.04-trigger", SS, r"if task_errors > _TASK_FAIL_MAX and not self\._reset_armed:", "task_errors > _TASK_FAIL_MAX", "task_errors >= _TASK_FAIL_MAX", "False", T_SS),
    *cap_pair("K.05", WS, r"if current > self\._max_connections:", "if current > self._max_connections:", "if current >= self._max_connections:", "if False:", [mp("test_asy_webserver_connections.py"), *T_WS]),
    *cap_pair("K.14", "src/asy_scd30_driver.py", r"if self\._irq_pin\.value\(\) == 1 and self\._scd_timer_triggers < self\._trigger_half_ticks:", " and self._scd_timer_triggers < self._trigger_half_ticks", " and self._scd_timer_triggers <= self._trigger_half_ticks", "", [mp("test_asy_scd30_driver.py")]),
    *cap_pair("K.18", IS, r"self\._write_failures = self\._write_failures \+ 1 if self\._write_failures < COUNTER_CAP else 0", " if self._write_failures < COUNTER_CAP else 0", " if self._write_failures <= COUNTER_CAP else 0", "", [mp("test_asy_isl29125_driver.py")]),
    *cap_pair("K.23", UC, r"if self\._valid_frames < COUNTER_CAP:", "if self._valid_frames < COUNTER_CAP:", "if self._valid_frames <= COUNTER_CAP:", "if True:", T_UC),
    *cap_pair("K.24", UC, r"if self\._blind_resyncs < _DIAG_RESYNC_STREAK:", "if self._blind_resyncs < _DIAG_RESYNC_STREAK:", "if self._blind_resyncs <= _DIAG_RESYNC_STREAK:", "if True:", T_UC),
    *cap_pair("K.25", UD, r"self\._cancel_req = self\._cancel_req \+ 1 if self\._cancel_req < COUNTER_CAP else 0", " if self._cancel_req < COUNTER_CAP else 0", " if self._cancel_req <= COUNTER_CAP else 0", "", T_UD),
    sub("K.25", "K.25-mask-drop", UD, r"while 0 < \(\(my_req - self\._cancel_ack\) & COUNTER_CAP\) < _SEQ_HALF:", "((my_req - self._cancel_ack) & COUNTER_CAP)", "(my_req - self._cancel_ack)", T_UD),
    *cap_pair("K.26", UD, r"self\.cancel_unacknowledged = n \+ 1 if n < COUNTER_CAP else 0", " if n < COUNTER_CAP else 0", " if n <= COUNTER_CAP else 0", "", T_UD),
    *cap_pair("K.27-transfers", UL, r"if self\._transfers < COUNTER_CAP:", "if self._transfers < COUNTER_CAP:", "if self._transfers <= COUNTER_CAP:", "if True:", T_UL),
    *cap_pair("K.27-failures", UL, r"elif self\._failures < COUNTER_CAP:", "elif self._failures < COUNTER_CAP:", "elif self._failures <= COUNTER_CAP:", "else:", T_UL),
    *cap_pair("K.28", PL, r"if self\._err_count < _MAX_CNT:", "if self._err_count < _MAX_CNT:", "if self._err_count <= _MAX_CNT:", "if True:", T_PL),
    *cap_pair("K.28-seq", PL, r"self\._counted = self\._counted \+ 1 if self\._counted < _WRAP_MAX else 0", " if self._counted < _WRAP_MAX else 0", " if self._counted <= _WRAP_MAX else 0", "", T_PL),
    *cap_pair("K.28-merge", PL, r"self\._err_count = count \+ self\._err_count if self\._err_count < _MAX_CNT - count else _MAX_CNT", " if self._err_count < _MAX_CNT - count else _MAX_CNT", " if self._err_count <= _MAX_CNT - count else _MAX_CNT", "", T_PL),
    *cap_pair("K.29-gamma", "src/voc_algorithm.py", r"if self\.params\.m_mean_variance_estimator_uptime_gamma < uptime_limit:", "_uptime_gamma < uptime_limit:", "_uptime_gamma <= uptime_limit:", "_uptime_gamma < 10**9:", [mp("test_voc_algorithm.py")]),
    *cap_pair("K.29-gating", "src/voc_algorithm.py", r"if self\.params\.m_mean_variance_estimator_uptime_gating < uptime_limit:", "_uptime_gating < uptime_limit:", "_uptime_gating <= uptime_limit:", "_uptime_gating < 10**9:", [mp("test_voc_algorithm.py")]),
    *cap_pair("K.20", FM, r"if \(self\._allocated_size \+ full_size\) > self\.size:", "> self.size:", ">= self.size:", "> 10**9:", T_FM, count=2, nth=0),
    *cap_pair("K.20-log", FM, r"if \(self\._allocated_size \+ full_size\) > self\.size:", "> self.size:", ">= self.size:", "> 10**9:", T_FM, count=2, nth=1),
    *cap_pair("K.42", "digital_twin/_twin_common.py", r"return value \+ n if value <= COUNTER_CAP - n else COUNTER_CAP", " if value <= COUNTER_CAP - n else COUNTER_CAP", " if value < COUNTER_CAP - n else COUNTER_CAP", "", [mp("test_digital_twin_machine.py")]),
    *cap_pair("K.42-log", "digital_twin/_twin_common.py", r"if len\(self\._items\) < self\.maxlen:", "if len(self._items) < self.maxlen:", "if len(self._items) <= self.maxlen:", "if True:", [mp("test_digital_twin_machine.py")]),
    *cap_pair("K.43", "digital_twin/_isl29125_chip.py", r"if self\._prst_count < target:  # the count stops", "if self._prst_count < target:", "if self._prst_count <= target:", "if True:", [mp("test_digital_twin_isl29125.py")]),
    *cap_pair("K.53", "js/mock-server.js", r'if \(typeof value === "number" && value < COUNTER_CAP\) \{', ' && value < COUNTER_CAP', ' && value <= COUNTER_CAP', '', [js("tests_js/mock-server.test.js")]),
    # A.U35.04's named planting requests
    sub("named.clamp_byte", "named.clamp_byte-signal", NP, r"return \[_clamp_byte\(r\), _clamp_byte\(g\), _clamp_byte\(b\), dur\]", "[_clamp_byte(r), _clamp_byte(g), _clamp_byte(b), dur]", "[r, g, b, dur]", [mp("test_asy_neopixel_driver.py")]),
    sub("named.clamp_byte", "named.clamp_byte-overlay", NP, r"bri = _clamp_byte\(self\._overlay_bri\)", "_clamp_byte(self._overlay_bri)", "self._overlay_bri", [mp("test_asy_neopixel_driver.py")]),
    ins("named.fram_alloc", "named.fram_alloc", FM, r"async def _write_chunk\(self, buf: bytearray, addr: int\) -> bool:", ["_planted = bytearray(16)"], [mp("test_asy_fram_allocation_budget.py")], indent=4),
    ins("named.webserver_leak", "named.webserver_leak", WS, r"async def _serve\(self, reader", ['globals().setdefault("_PLANTED_KEEP", []).append(bytes(16))'], T_WS, indent=4),
    ins("named.uart_latency", "named.uart_latency", UC, r"async def uart_set_into\(self, set_id", ["await asyncio.sleep_ms(20)"], [mp("test_uart_comm_hazard.py")], indent=4),
    sub("named.catalog", "named.catalog-literal", NO, r'await self\.pr\.err_s\(notif\.name, "Value read failed:", e, errno=_ERR_SOURCE\)', "errno=_ERR_SOURCE)", "errno=10)", [host("tests_scripts/test_error_catalog.py")]),
    app("named.catalog", "named.catalog-band", NO, "_ERR_PLANTED = const(126)\n", [host("tests_scripts/test_error_catalog.py")]),
    app("named.catalog", "named.catalog-dupname", "src/asy_scd30_driver.py", "_ERR_SOURCE = const(7)\n", [host("tests_scripts/test_error_catalog.py")]),
    app("named.catalog", "named.catalog-testcopy", "tests/test_asy_uart_comm.py", "\n_ERR_NO_ACK = 20\n", [host("tests_scripts/test_error_catalog.py")]),
    app("named.catalog", "named.catalog-persisted", "tests/test_asy_notification_service.py", '\n\ndef _planted_assert(c: object) -> None:\n    assert persisted(c) == ["E99"]\n', [host("tests_scripts/test_error_catalog.py")]),
    ins("named.pair_scan", "named.pair_scan", NO, r'await self\.pr\.err_s\(notif\.name, "Value read failed:", e, errno=_ERR_SOURCE\)', ['await self.pr.wrn_s(notif.name, "planted", wrnno=_ERR_SOURCE)'], [host("tests_scripts/test_fault_or_warning_never_both.py")]),
    ins("named.write_counters", "named.write_counters", "src/asy_config_manager.py", r"^\s*f\.write\(text\)$", ["f.write(text)"], [mp("test_write_counters.py"), mp("test_asy_config_manager.py")]),
    app("named.result_words", "named.result_words", NO, '_PLANTED_WORD = "Valid"\n', [host("tests_scripts/test_result_words.py")]),
    sub("named.api_contract", "named.api_contract", "js/api-contract.js", r'^export const VALID = "Valid";', '"Valid";', '"Valld";', [host("tests_scripts/test_js_api_mirrors.py")]),
    sub("named.mock_routes", "named.mock_routes", "js/mock-server.js", r"routes\.get\.set\(section\.rest\.get, section\);", "section.rest.get, section", 'section.rest.get + "x", section', [js("tests_js/mock-server.test.js")]),
    app("named.layering", "named.layering", "js/render.js", 'export function plantedBuild() { return document.createElement("div"); }\n', [host("tests_scripts/test_website_layering.py")]),
    # The generated boot entry's decisions (buildgen/codegen.py's template), regenerated in the copy
    sub("boot", "boot.interrupt_record", CG, r'^        "    write_reset_record\(RR_INTERRUPTED\)\\n"$', "write_reset_record(RR_INTERRUPTED)", "pass", [mp("test_generated_boot_entry.py")]),
    sub("boot", "boot.interrupt_raise", CG, r'^        "    raise\\n"$', '"    raise', '"    pass', [mp("test_generated_boot_entry.py")]),
    sub("boot", "boot.report", CG, r'^        "    report_if_fatal\(ended\)\\n"$', "report_if_fatal(ended)", "pass", [mp("test_generated_boot_entry.py")]),
    sub("boot", "boot.loop_end", CG, r'^        "    record_loop_end\(\)\\n"$', "record_loop_end()", "pass", [mp("test_generated_boot_entry.py")]),
    sub("boot", "boot.finally", CG, r'^        "    asyncio\.new_event_loop\(\)\\n"$', "asyncio.new_event_loop()", "pass", [mp("test_generated_boot_entry.py")]),
    # A.U35.05: two plants per memory gate, plus each gate's unplanted control
    {"id": "gate.unit-control", "row": "gate.unit", "why": "", "edits": [], "tests": [{"file": "tests/test_math_helpers.py", "level": "mp_gate"}]},
    app("gate.unit", "gate.unit-caught", "src/math_helpers.py", 'print("planted: memory allocation failed, allocating 64 bytes")\n', [{"file": "tests/test_math_helpers.py", "level": "mp_gate"}]),
    app("gate.unit", "gate.unit-class", "src/math_helpers.py", 'print("MemoryError: ")\n', [{"file": "tests/test_math_helpers.py", "level": "mp_gate"}]),
    {"id": "gate.twin-control", "row": "gate.twin", "why": "", "edits": [], "tests": [{"file": "scripts/_digital_twin_ci_suite.py", "level": "twin_gate"}]},
    app("gate.twin", "gate.twin-caught", PL, 'print("planted: memory allocation failed, allocating 64 bytes")\n', [{"file": "scripts/_digital_twin_ci_suite.py", "level": "twin_gate"}]),
    app("gate.twin", "gate.twin-class", PL, 'print("MemoryError: ")\n', [{"file": "scripts/_digital_twin_ci_suite.py", "level": "twin_gate"}]),
    {"id": "gate.flash-control", "row": "gate.flash", "why": "", "edits": [], "tests": [host("tests_hardware/flash/test_unretrieved_task_exception_handler.py", "--twin")]},
    app("gate.flash", "gate.flash-caught", PL, 'print("planted: memory allocation failed, allocating 64 bytes")\n', [host("tests_hardware/flash/test_unretrieved_task_exception_handler.py", "--twin")]),
    app("gate.flash", "gate.flash-class", PL, 'print("MemoryError: ")\n', [host("tests_hardware/flash/test_unretrieved_task_exception_handler.py", "--twin")]),
    # Seeded picks that are complex measurement tests (never-block yields, memory, accumulation, timing bounds, log gates)
    sub("seed", "asy_fram_manager.erase_yield", FM, r"^            await asyncio\.sleep\(0\)$", "await asyncio.sleep(0)", "pass", T_FM, why="never-block: the chip erase's per-unit yield (timing)"),
    sub("seed", "asy_fram_manager.read_yield", FM, r"^                    await asyncio\.sleep\(0\)$", "await asyncio.sleep(0)", "pass", T_FM, why="never-block: the read loop's per-slice yield (timing)"),
    sub("seed", "asy_fram_manager.status_yield", FM, r"await asyncio\.sleep\(0\)  # after the status-byte pair", "await asyncio.sleep(0)", "pass", T_FM, why="never-block: the yield after the status-byte pair (timing)", count=3, nth=0),
    sub("seed", "asy_framing_codecs.decode_yield", "src/asy_framing_codecs.py", r"^\s*await asyncio\.sleep\(0\)$", "await asyncio.sleep(0)", "pass", [mp("test_asy_framing_codecs.py")], why="never-block: the decode loop's yield (timing)"),
    sub("seed", "asy_uart_driver.idle_poll", UD, r"wait_ms = self\.poll_wait_ms if timeout_ms > 0 else self\.poll_idle_ms", " if timeout_ms > 0 else self.poll_idle_ms", "", T_UD, why="F.5.9: an open-ended wait polls at the idle rate (timing)"),
    sub("seed", "asy_uart_driver.drain_yield", UD, r"await asyncio\.sleep_ms\(0\)  # this loop never reaches", "await asyncio.sleep_ms(0)", "pass", T_UD, why="F.5.8: never block the loop, the drain's own yield (timing)"),
    sub("seed", "asy_uart_driver.rx_clamp", UD, r"return min\(max\(want, 0\), level\)", "min(max(want, 0), level)", "max(want, 0)", T_UD, why="F.5.8: each read clamped to what has arrived (timing)"),
    sub("seed", "asy_uart_driver.read_alloc_print", UD, r'console\(_NAME, "read buffer allocation failed:", e\)', 'console(_NAME, "read buffer allocation failed:", e)', "pass", T_UD, why="memory: a caught allocation failure prints its own text (log gate)"),
    sub("seed", "asy_uart_driver.line_alloc_print", UD, r'console\(_NAME, "line buffer allocation failed:", e\)', 'console(_NAME, "line buffer allocation failed:", e)', "pass", T_UD, why="memory: a caught allocation failure prints its own text (log gate)"),
    sub("seed", "asy_uart_comm.gate_step", UC, r"await asyncio\.sleep_ms\(min\(remaining, _GATE_STEP_MS\)\)", "min(remaining, _GATE_STEP_MS)", "remaining", T_UC, why="the hold-off waits in bounded steps (timing)"),
    sub("seed", "asy_uart_link_driver.recovery_window", UL, r"await asyncio\.sleep_ms\(self\._window_ms\)", "await asyncio.sleep_ms(self._window_ms)", "pass", T_UL, why="each recovery try first waits one window (timing, multi-layer)"),
    sub("seed", "asy_uart_link_driver.quiet", UL, r"await asyncio\.sleep_ms\(self\._quiet_ms\)", "await asyncio.sleep_ms(self._quiet_ms)", "pass", T_UL, why="the peer's own timeout passes first (timing, multi-layer)"),
    sub("seed", "asy_system_service.last_feed", SS, r"self\._own_feed\(\)  # a system command's last feed", "self._own_feed()", "pass", T_SS, why="watchdog: the command's last feed before the arm (timing)"),
    sub("seed", "asy_system_service.alarm_enomem", SS, r"except \(MemoryError, OSError\) as e:  # alarm-pool exhaustion", "(MemoryError, OSError)", "OSError", T_SS, why="memory: the alarm-pool or allocation failure is caught (memory exhaustion)", count=2, nth=0),
    sub("seed", "asy_system_service.supervisor_memerr", SS, r"^            except MemoryError as e:$", "MemoryError", "OSError", T_SS, why="memory: the supervisor's caught allocation failure (memory exhaustion)"),
    sub("seed", "asy_webserver_service.stream", WS, r"return await _stream_dict_response\(result, self\._chunk_bytes\)$", "await _stream_dict_response(result, self._chunk_bytes)", "result", T_WS, why="memory: a growing GET body streams in chunks (I.4)", count=2, nth=0),
    sub("seed", "asy_print_log.ring_alloc", PL, r"except MemoryError as e:  # a 0-length ring", "MemoryError", "OSError", T_PL, why="memory: the history ring's allocation failure degrades to a 0-length ring"),
    sub("seed", "asy_captive_dns.backoff_cap", "src/asy_captive_dns.py", r"recv_fail_backoff_ms \* _RECV_FAIL_BACKOFF_MULTIPLIER, _RECV_FAIL_BACKOFF_MAX_MS,", ", _RECV_FAIL_BACKOFF_MAX_MS,", ", 10**9,", [mp("test_asy_captive_dns.py")], why="accumulating: the receive-failure backoff stops at its cap"),
    sub("seed", "asy_ntp_client.backoff_cap", "src/asy_ntp_client.py", r"self\._retry_wait_s = min\(self\._retry_wait_s \* _NTP_BACKOFF_MULT, self\._retry_max_s\)", ", self._retry_max_s)", ", 10**9)", [mp("test_asy_ntp_client.py")], why="accumulating: the retry backoff stops at its cap"),
    sub("seed", "asy_sgp40_driver.backup_cadence", "src/asy_sgp40_driver.py", r"if cfg_values\[0\] > 0 and self\._backup_counter >= \(60 \* cfg_values\[0\]\):", "self._backup_counter >= (60", "self._backup_counter > (60", [mp("test_asy_sgp40_driver.py")], why="long-running: the FRAM backup cadence (accumulation)"),
    sub("seed", "asy_sgp40_driver.backup_counter_max", "src/asy_sgp40_driver.py", r"if self\._backup_counter >= _BACKUP_COUNTER_MAX:", ">= _BACKUP_COUNTER_MAX", "> _BACKUP_COUNTER_MAX", [mp("test_asy_sgp40_driver.py")], why="long-running: the backup counter's own bound (accumulation)"),
    sub("seed", "asy_isl29125_driver.cal_hold", IS, r"if time\.ticks_diff\(time\.ticks_ms\(\), self\._cal_meas_until_ms\) >= 0:", ") >= 0:", ") > 0:", [mp("test_asy_isl29125_driver.py")], why="timing bound: the measured ratio's hold expires at its exact tick"),
    sub("seed", "asy_neopixel_driver.signal_deadline", NP, r"if time\.ticks_diff\(deadline, time\.ticks_ms\(\)\) <= 0:", ") <= 0:", ") < 0:", [mp("test_asy_neopixel_driver.py")], why="timing bound: an internal request waits at most _SIGNAL_WAIT_MS"),
    sub("seed", "asy_notification_service.sample_age", NO, r"now - ts > _SAMPLE_MAX_AGE_S:", "now - ts > _SAMPLE_MAX_AGE_S", "now - ts >= _SAMPLE_MAX_AGE_S", [mp("test_asy_notification_service.py")], why="timing bound: a sample older than the bound is unavailable"),
    sub("seed", "asy_crc_checks.check_inc_reset", "src/asy_crc_checks.py", r"^            self\._inc_count = 0$", "self._inc_count = 0", "pass", [mp("test_asy_crc_checks.py")], why="accumulating: the incremental state resets after each check"),
    sub("seed", "asy_wifi_service.conn_failures", "src/asy_wifi_service.py", r"if self\._connection_failures < \(self\._conn_fail_to_hotspot - 1\):", "self._connection_failures < (", "self._connection_failures <= (", [mp("test_asy_wifi_service.py")], why="accumulating: the failure count that hands over to the hotspot"),
    sub("seed", "asy_i2c_driver.recoveries", "src/asy_i2c_driver.py", r"self\.recoveries = self\.recoveries \+ 1 if self\.recoveries < COUNTER_CAP else 0", " if self.recoveries < COUNTER_CAP else 0", "", [mp("test_asy_i2c_driver.py")], why="accumulating: the recovery sequence wraps at COUNTER_CAP", count=2, nth=0),
    sub("seed", "asy_base_classes.bins_advance", BC, r"for h in range\(self\._hour \+ 1, hour \+ 1\):", "hour + 1):", "hour):", T_BC, why="accumulating: the 24-hour window clears each passed hour"),
]

# Each target file unplanted first, at both stages: a plant's red counts only against a green baseline.
_SEEN: list = []
for _p in PLANTS:
    for _t in _p["tests"]:
        if _t["level"] in ("mp", "host", "js") and _t not in _SEEN:
            _SEEN.append(_t)
PLANTS[:0] = [{"id": f"base.{_t['file']}", "row": "baseline", "why": "", "edits": [], "tests": [_t]} for _t in _SEEN]

# The re-plant set: the survivors whose fixes landed, run on a later snapshot.
REPLANT = ["K.04-flip", "K.04-drop", "K.04-trigger-drop", "K.28-seq-flip", "K.28-seq-drop", "K.29-gamma-flip", "K.29-gamma-drop", "K.29-gating-flip", "K.29-gating-drop", "K.20-log-flip"]
