D2S hand-back, written by the lane (2026-10-27 13:02 UTC)

Lane D2S: runtime checks that only guard what typing enforces, across src/ and the generated modules, plus the lead's
D.15 addition. Worktree S/wt-u35d2s, branch audit/u35-d2s from 96ed596f. Not pushed; nothing uncommitted (node_modules
was already untracked). Logs in S/u35/laneB/d2s/. Every run went through d2s/run.sh (namespace, nice 19, RUNS.md:
60 starts, 60 dones), except the very first rebuild.sh (rebuild1), run before the wrapper covered it.

## Commits (oldest first)
- 51fafa07 item 0b: raising.md's header names src/'s git tree id from the working tree.
- f0b2f2fb asy_dns_client: resolve_ipv4() drops TypeError from its range(tries) catch.
- 17755605 asy_uart_driver: UART.ready() drops TypeError from its loop's catch.
- d9a9d328 asy_udp_socket: the Literal mode check goes; ready(), recvfrom() and write() drop TypeError.
- 890c5ab1 asy_isl29125_driver: the try/excepts in _decode_rgb_burst() and decode_config() go, is_bus_fault_pattern() loses its tuple-length test, _CHANNELS goes.
- 2c74d3fb asy_uart_comm: _check_buffer() keeps only the writability check (UART_C_PORT_CHANGELOG.md B90, Class B).
- 6e0d3fba voc_algorithm: unpack_from() drops TypeError.
- 32c4266d asy_neopixel_driver: _signal_values()/_clamp_byte() lose their numeric gates and _clamp_byte() its int() catch.
- fccb464d the lead's addition: _FRAMBaseChunk._copy_out() moved to its D.15 place (pure move).
- 73811fa1 records: e51 hits for the eight changed modules re-dumped from fresh coverage; stale citations re-located.

## Item 0b (51fafa07)
- The header now names git's tree id of `src/`, taken from the working tree (`git ls-files -co --exclude-standard`, hashed as git would). That is the id `git rev-parse <commit>:src` prints. At the head the header reads be61a52f5d14, which equals HEAD:src.
- Bite (scratch copy, fresh `git init`):
  - a src edit without a re-render fails `--check`;
  - re-rendered, it passes;
  - over the same edit, the old header's `--check` stayed green.
- Every later src commit carries its own re-render.

## Item 0: the records
- The raising walk has 15 verdicts that lean on typing. They are "this call cannot raise" proofs (len() of a typed buffer, a builtin classinfo, the TYPE_CHECKING import, typed dict reads). None is a guard on a value.
- e51's uncovered guard lines are Optional narrowings (class c), which mypy needs. The rest are covered.
- So no guard sits on both lists. Every candidate came from item 1.

## Item 1/2: inventory and classes
- The full table is below: 196 sites at base lines, with each site's class and proof.
- Method:
  - an AST scan of the brief's shapes;
  - `--enable-error-code redundant-expr` over mypy's main pass, whose only src hits were udp:43 and uart_comm 240, 241 and 957-976;
  - a probe statement before every raise/pass-only branch, so warn_unreachable reports it (92 probes, none unreachable; a planted control was reported);
  - reveal_type() on every argument of the named calls. That showed no Any at any site, and showed which int-typed parameters are fed only exact ints.
- A fact behind several rows: on MicroPython `isinstance(True, int)` is False, while mypy accepts a bool wherever an int is declared (probed on the Unix port).
- Counts:
  - **remove 14**, all removed: dns:149, uart_driver:725, udp:41-42, :135, :147, :170, isl:1222, :1276 (the length half), :1407, uart_comm:431-432, voc:154, neopixel:49, :53, :59;
  - **unsure 14**: below;
  - the rest **keep**, or **not a check**.

## Item 3: the removals
- **Seen failing first.** Each module's src edit was run against its unchanged test file first. Exactly the predicted tests failed, each feeding a value through a type ignore: dns 1, uart_driver 1, udp 5, isl 3, uart_comm 2, voc 1, neopixel 3.
- **Tests removed whole (11):**
  - test_ready_returns_false_on_a_malformed_mask
  - test_init_rejects_invalid_mode
  - test_ready_returns_false_sentinel_for_a_malformed_timeout_ms
  - test_ready_returns_false_sentinel_for_a_malformed_mask
  - test_recvfrom_returns_none_sentinel_for_a_malformed_buf_with_real_pending_data
  - test_recvfrom_propagates_readys_false_sentinel_for_a_malformed_timeout_ms
  - test_the_config_decoder_survives_an_answer_that_is_not_bytes_at_all
  - test_a_non_buffer_payload_returns_a_sentinel_instead_of_raising
  - test_an_immutable_destination_is_refused_before_the_train_starts
  - test_a_non_numeric_signal_value_is_refused_without_a_frame
  - test_request_signal_infinite_rgb_clamped_not_raised
- **Tests trimmed:**
  - test_resolve_ipv4_a_malformed_tries_... keeps its 2**70 case, renamed ..._a_tries_past_a_machine_word_...
  - test_decode_rgb_burst_rejects_short_and_none and test_decode_config_rejects_the_wrong_length_and_none drop their 42 lines.
  - test_clamp_byte_direct drops its float, str and None lines.
  - test_a_buffer_or_offset_struct_refuses_is_a_false_answer drops `unpack_from(None)`. Its read-only pack_into case now passes `memoryview(bytes(...))` (type-correct) instead of bytes behind an ignore (agent, 2026-10-27).
- **Docs:** SPECIFICATION.md's poll-rate paragraph and its VOC serialisation bullet; sendto()'s comment now names the real reason for its TypeError.
- **Records:**
  - review.md: 8545 → 8534 rows;
  - the walk keeps its 1264 sites (none of the seven modules was changed);
  - e51 (73811fa1): the eight files' hits are the union of 87 fresh settrace jobs. No previously hit line is uncovered now. 24 "covered" verdicts left with their sites, as in BR4's b3e9ff3e (61 → 37 sites).
- **Re-located citations:**
  - asy_base_classes.json, into isl29125 and uart_comm;
  - e51_verdicts.json, uart_comm :934 → :927;
  - SPECIFICATION.md's _read_frame() range, already off at the base, now :715-729.
- **mpy-cross** (-march=armv6m, base vs head): -378 bytes in all:
  - dns -6, uart_driver -4, udp -94, isl -66, uart_comm -86, voc -3, neopixel -119.

## The lead's addition: D.15 (fccb464d)
- `_copy_out` moved from old lines 463-471 to 192-200. The lines between shift by 10; no other change.
- test_code_conventions.py: 25 passed, member_order included.
- Citations re-located by the exact permutation: 25 in asy_fram_manager.json and asy_fram_driver.json. Two of them were bare "(:328)" refs following a :298 citation, re-located by hand.
- e51_hits for the moved lines carried the same way; raising.md and e51's block re-rendered.
- All three audit checks are green at 73811fa1: the walk, e51 and review_rows `--check`.
- Run on the moved code:
  - test_asy_fram_manager.py at both stages;
  - the 11 importers of asy_fram_manager that the main run did not cover, at both stages;
  - all 62 importers under settrace in the coverage run.
- Gap: the main both-stage run of the 51 shared importers ran at 32c4266d, before the move.

## Checks on the head
- Importers of the seven modules: 51 files, PER_DEVICE ones on six devices. 76 jobs at -1 and 32768: all rc 0, zero memory markers.
- Plus the 11 extra files (22 stage runs): clean.
- Coverage (settrace): 87 jobs, 86 clean. The one failure is root-caused, see F1.
- lint_direct rc 0; the six mypy passes clean.
- tests_scripts readers: 57 files. 3347 passed. 2 failed, both in test_twin_record.py, the expected red on any src change; they wait on the lead's re-record.
- npm unit tier not run: no js/, html/, emitter or catalog file changed.
- Head times: dns 1.0/1.0 s, isl 3.0/3.2, neopixel 0.8/0.9, uart_driver 7.7/13.1, udp 6.0/6.0, uart_comm 63.5/65.0, voc 4.5/9.7.
  - No test file grew.
  - base_testsh_m1.log holds no per-file times, so there is no paired base figure.
- Silent-failure classes 1-7 over the changed files: nothing new. Class 4 shrinks; a typing breakage now raises instead of answering a sentinel.

## Unsure sites, for the owner
**U1: one question covers twelve sites: a bool through an int-typed path.** mypy treats bool as an int. MicroPython's
isinstance(True, int) is False, and type(True) is not int. So each of these checks also refuses a bool, which typing
accepts. Every product path to them passes exact ints (literals and constants, _coerce_int() results, raw[0] of bytes).
- uart_comm 240, 957, 963, 965, 974, 976: TransferLimits from int literals, and the UART's poll_wait_ms. Without them, True is accepted as 1 at 957 (payload_size), 965 (poll_wait_ms) and 974 (chunk_bytes).
- uart_comm 241, held with them. It is proven like a remove, and a bool gives identical values there. But 240/241 carry one stated rule, "__init__ answers through errno", and removing 241 alone makes __init__ raise for a non-int timeout but not for a non-int payload. CLAUDE.md's scan rule says to flag such a split, not create it.
- uart_comm 447 (_check_cmd_id) and 459 (_check_size): True would be sent as command 1 and size 1.
- udp:43-44, the addr check: a bool port. Removing it ends the module's "__init__ excepted" raise.
- isl 1237/1245, _reject_outside/_reject_unless. Their comment's stated reason, 375.0, is a float, which typing already excludes.

Recommendation: count a bool fed to an int-typed path as a typing breakage too and remove all twelve as one change,
with a B-entry for uart_comm. Typing lets the slip through, but nothing outside the type system can produce it.
Values from outside enter through config_manager's exact-type validators (A.8), which already refuse bool. Keep the
documented exact-type refusals that serve a real input: print_log set_level, and the config validators.

**U2: public API breadth.** decode_status(status: object) and is_bus_fault_pattern(counts: tuple|None, status:
object) are public static methods. Their signatures and comments declare the wider input, and tests call them with
None, which is type-correct. The product passes read_status()'s int and read_counts()'s tuple. These are not
out-of-contract input. Recommendation: keep, as the library rule's class (d). Narrow them only if the owner wants
the API narrowed, together with U1's bool angle on status.

## For the lead
- **F1: a twin defect.** In digital_twin/machine.py's UARTLink.settle(), `if remaining <= 0: break` leaves out the `_advance()` that delivers the bytes now due.
  - So a descheduling between the first `_advance()` and the deadline test leaves bytes for the next read.
  - test_digital_twin_machine_uart.py's second-construction test failed once that way (line 88: it read the old bytes), in the coverage run under host load of about 27 heavy processes.
  - It passed 4/4 in isolation on both toolchains. A planted 1 ms stall reproduces the failure deterministically at -1 (d2s/plant_settle.log).
  - Fix: `self._advance()` before that `break`. The file is outside my set, so it is not edited.
- **F2: D.10.** UDPSocket.ready() does not catch the OverflowError that asyncio.wait_for_ms() raises for a timeout_ms of 2**29 ms or more. UART.ready() catches it, and SPECIFICATION.md states it for UART. Flagged, not fixed; I have not checked whether a configured timeout can reach that value.
- **F3: living registers' citations moved by these commits** (other lanes' files, not edited):
  - faults.md: :29-30 isl 1378→1372; :31-32 uart_comm 630→623; :33-34 826→819; :66-67 neopixel 67→57, 96→86; :68 fram_manager 396→406; :70 uart_comm 1167→1160; :94 fram_manager 316→326; :114 isl 569→568; :115 neopixel 184→170.
  - REGISTER.md:726 and :839 udp lines were stale already.
  - REGISTER.md:738 records F1c's malformed-tries guard, whose TypeError half f0b2f2fb removes.
  - e51.md's header line 11 names fram_manager 222/230/249, now 232/240/259; it describes CEr1's base.
- **F4:** e51_hits.json is fresh for the eight changed files; the other files still carry CEr1's hits.
- **Deviations:**
  - The D.15 item arrived after my first src commit, so it is its own commit after the removals.
  - Scratch tooling broke the Edit/Write rule:
    - the first one.sh was written by heredoc (rewritten with Write);
    - the 0b and settle() plants were applied by Python in scratch copies;
    - 23 audit-JSON citation edits were applied by d2s/remap_fm.py, after a dry run reviewed line by line;
    - e51_hits.json was rewritten by d2s/remap_hits_fm.py and BR4's dump_hits.py, generated output like the walk's render.
  - Two waits used pgrep to find my own pid (no kills).

## Inventory (lines at the base 96ed596f; `scan.py` over src/*.py and build/generated_src/*.py, 231 hits on 196 sites)

Construct key: is = isinstance(), ty = type(x) is/==, ha = hasattr(), ga = getattr(), len = a len() comparison,
exc = an except naming TypeError/AttributeError/KeyError/IndexError/ValueError, rz = a raise TypeError. Plus the one
check the scan's shapes miss and a mypy probe found: a membership test on a Literal (udp:41).
Classes: keep (the reason); remove (mypy fixes the type on every path, the check fires only on a typing breakage for
every value mypy accepts, bool for int included, and product code cannot reach it); unsure (why).
"union narrowing": the declared type is a union (or object) that real product values span, and the check is how
mypy-typed code consumes it. "exc dispatch": an isinstance() on a caught exception. "not a check": a construct with
the shape that tests nothing (a name for a log line, a field read by name, a constructor call).

| site | construct | function | class | proof |
|---|---|---|---|---|
| asy_base_classes.py:188 | len | PieceBuffer.copy_into | keep | dest's length is a runtime property of a caller buffer (variable length) |
| asy_base_classes.py:209 | len | PieceBuffer.trim | keep | a loop bound over the piece list, not a check |
| asy_base_classes.py:699 | ga | SensorReader._republish | not a check | reads a namedtuple field by name to rebuild the sample |
| asy_base_classes.py:700 | ty | SensorReader._republish | not a check | type(old)(...) constructs the sample's own class |
| asy_bmp3xx_driver.py:203 | len | _apply_stored_config | keep | get_int_values() answers a list (variable length): a config-file contract, not a typed tuple |
| asy_bmp3xx_driver.py:242, 247, 252, 257 | ty | _push_* (4) | keep | union narrowing: value is the config union int/float/str/bool/None from a PUT body; mypy needs the int |
| asy_bmp3xx_driver.py:265 | len | _read_bmp | keep | as :203 (get_float_values()) |
| asy_bmp3xx_driver.py:285 | exc ValueError | _read_bmp | keep | the driver's own range gate raises it (a sensor reading) |
| asy_bmp3xx_driver.py:505, 620, 706 | is | _read, _wait_status_bits, reset | keep | union narrowing: get_register_struct() answers int/float/bytes/None, None for a down bus |
| asy_config_manager.py:75, 79 | ty | _as_bool, _as_str | keep | union narrowing of CfgValue read from the config file (JSON from flash) |
| asy_config_manager.py:85, 87, 99, 101 | ty | _coerce_float, _coerce_int | keep | value: object from a PUT body or the config file; exact type refuses bool (A.8) |
| asy_config_manager.py:104 | exc ValueError | _coerce_int | keep | int() of NaN (a value) |
| asy_config_manager.py:115 (x2), 116, 121 | ty | _special_bypass | keep | the schema's special is a scalar or tuple/list (CfgSpecial union); its element kind against the field's kind string is a link typing cannot express |
| asy_config_manager.py:145 | is | check_cfg_get_default | keep | union narrowing of CfgSpecial |
| asy_config_manager.py:165 (x2), 179 (x2) | ty | checked_float, checked_int | keep | the schema's min/max are a union; their kind against field[1] is not typed |
| asy_config_manager.py:204 | ty | compare_before_write | keep | data is JsonMapping (a Mapping), which admits a non-dict mapping |
| asy_config_manager.py:261, 262 | ty, ga | make_dict | not a check | type name and field reads |
| asy_config_manager.py:267, 550 | len | name_cfg, setup | keep | schema counts (values) |
| asy_config_manager.py:302, 308 (x2), 310 | ty | type_or_range_error | keep | check_val: object from a PUT body or the file; min/max a union |
| asy_config_manager.py:372, 451 | exc KeyError | _get_values, get_dict | keep | an unknown key name (a value against the cached file) |
| asy_config_manager.py:405 | exc ValueError | _flush_staged | keep | serialisation and file errors (runtime) |
| asy_config_manager.py:527, 531, 576 | is, exc ValueError, ty | setup | keep | JSON parsed from flash |
| asy_config_manager.py:539 | is | setup | keep | exc dispatch (OSError's ENOENT) |
| asy_config_manager.py:655 | ty | write_config | keep | union narrowing (a coerced float stored in its file form) |
| asy_crc_checks.py:115 | len | CRCBase.check | keep | a frame's length (wire) |
| asy_dns_client.py:62, 109, 126, 178 | len | _build_query, _reply_rcode, ipv4_to_int, resolve_ipv4 | keep | host labels, wire bytes, a dotted quad's parts |
| asy_dns_client.py:149 | exc TypeError (+OverflowError) | resolve_ipv4 | **remove** (TypeError) | tries: int at the one caller (ntp:415, revealed int, from the config); range() of an int or a bool never raises TypeError; reached only by the malformed-tries test (None/"3"/[1]/1.5 behind a type ignore). OverflowError (2**70) stays |
| asy_dns_client.py:156, 187 | exc ValueError, IndexError/ValueError | resolve_ipv4 | keep | an unencodable name; reply parse (wire) |
| asy_fram_driver.py:296 | len | _setup_addr_buffer | keep | dispatch on the address width the chip size chose |
| asy_fram_manager.py:216, 372, 513, 612 | len | _read, _write, FRAMChunk.write, FRAMTimestampedChunk.write | keep | buffer sizes against the chunk's size (variable-length buffers) |
| asy_i2c_driver.py:264, 269, 322 | exc ValueError | get/set_register_struct | keep | a format string's content (struct.calcsize), not its type |
| asy_i2c_driver.py:274 | is | get_register_struct | keep | struct.unpack()'s element is Any to mypy, its type follows the format at run time |
| asy_i2c_driver.py:328 | exc TypeError/ValueError | set_register_struct | keep | the value's fit to a caller's format (a float for "B") is a link typing cannot express |
| asy_i2c_driver.py:394 | exc ValueError | recover | keep | machine.I2C() construction refusing (runtime) |
| asy_i2c_driver.py:424, 427 | is, exc ValueError | writeto | keep | union narrowing (bytes/bytearray/str); a character outside 0-255 |
| asy_isl29125_driver.py:484, 486, 488, 582 | len | _init_isl, _note_candidate | keep | config list lengths; a history count |
| asy_isl29125_driver.py:620-656 (11) | ty | _push_* (11) | keep | as bmp3xx:242 |
| asy_isl29125_driver.py:1219, 1404, 1462 | len | _decode_rgb_burst, decode_config, matches_shadow | keep | a read's length (variable-length buffer) |
| asy_isl29125_driver.py:1222 | exc TypeError/ValueError (the try) | _decode_rgb_burst | **remove** | raw a buffer after the None test (its caller :1502 passes the instance's bytearray); len() of a buffer never raises and unpack_from("<HHH") of a 6-item buffer has 6+ bytes; reached only by `_decode_rgb_burst(42)` (type ignore) |
| asy_isl29125_driver.py:1237, 1245 | ty | _reject_outside, _reject_unless | unsure (U1) | value: int (revealed int at :1302, :1329, :1333, :1335, :1337); also refuses a bool |
| asy_isl29125_driver.py:1276 | len | is_bus_fault_pattern | **remove** (the length half) | counts: tuple[int, int, int] after the None test, a typed fixed-length tuple (revealed at :704); `counts is None` stays |
| asy_isl29125_driver.py:1282 | ty | is_bus_fault_pattern | unsure (U2) | status: object, its one caller passes an int; public signature, tests pass None; also a bool |
| asy_isl29125_driver.py:1407 | exc IndexError/TypeError (the try) | decode_config | **remove** | raw a buffer after the None test (callers :785, :858 pass bytearrays); the length test makes indexes 0-2 valid; reached only by decode_config(42) and (5) (type ignores) |
| asy_isl29125_driver.py:1421 | ty | decode_status | unsure (U2) | status: object, the product passes read_status()'s int (via _handle_status, revealed int at :679); public signature; also a bool |
| asy_neopixel_driver.py:49 | is | _clamp_byte | **remove** | private; every caller passes an int (revealed :67 and :96); _NUMERIC held bool, so no mypy-accepted value failed it |
| asy_neopixel_driver.py:53 | exc OverflowError/ValueError | _clamp_byte | **remove** | int() of an int or a bool never raises; inf/NaN reached it only as a float for an int parameter (type ignore) |
| asy_neopixel_driver.py:59 (x4) | is | _signal_values | **remove** | private; led_signal()/request_signal() are typed r, g, b: int, t: float (revealed at :159, :179; their callers, the generated LED callback and notification:334, pass int/float); _NUMERIC held bool and int |
| asy_notification_service.py:225, 226 | ga | _check_one | keep | documented duck typing: the field name comes from the registration (Part C.14) |
| asy_notification_service.py:234, 238 | is | _check_one | keep | the getattr() results are object |
| asy_notification_service.py:239 | ty | _check_one | not a check | type name for the log line |
| asy_notification_service.py:265-267 | len | _monitor_loop | keep | as bmp3xx:203 |
| asy_ntp_client.py:149, 164 | ty | _dns_fallback_ok, _ntp_host_ok | keep | value: object from a PUT body (:234, :236) or the file |
| asy_ntp_client.py:154, 166, 215, 376, 550 | len | (as named) | keep | values and list lengths |
| asy_ntp_client.py:316 | len | _parse_ntp_reply | keep | wire bytes |
| asy_ntp_client.py:566 | len | cettime | keep | time.gmtime()'s tuple is the port's (9 fields on the Unix port, 8 on rp2) |
| asy_print_log.py:99 | is | PrintLog._line | keep | args: object |
| asy_print_log.py:106 | ty | set_level | keep | narrows int or None; the documented exact type refuses a bool |
| asy_print_log.py:414 | is | PrintLogHistoryStore.setup | keep | union narrowing of the FRAM read's answer |
| asy_print_log.py:486 | is | report_if_fatal | keep | exc dispatch |
| asy_scd30_driver.py:489 | exc ValueError | _read_scd | keep | the range gate (a sensor reading) |
| asy_scd30_driver.py:533, 534 | ga | _store_scd | keep | _datastruct's static type is the base NamedTuple, which declares no FRC field: getattr is the typed access |
| asy_sgp40_driver.py:182, 183, 185 | ga, is | _current_value | keep | data: object, a producer's sample read by field name (Part C.14) |
| asy_sgp40_driver.py:272, 347 | len | _check_storage, _init_sgp | keep | as bmp3xx:203 |
| asy_spi_driver.py:103 | exc ValueError | write_readinto | keep | two buffers' lengths |
| asy_uart_comm.py:186 | exc TypeError | _is_writable | keep | a read-only memoryview is type-correct and refuses the slice assignment |
| asy_uart_comm.py:240 | is | __init__ | unsure (U1) | limits.payload_size: int (TransferLimits from int literals, revealed); also refuses a bool |
| asy_uart_comm.py:241 | is | __init__ | unsure (U1, held) | proven like a remove, a bool giving the same backoff values; held with :240 (one stated rule) |
| asy_uart_comm.py:279, 343, 397-399, 673, 863, 910 | len | (as named) | keep | buffer sizes (a failed allocation leaves zero-length buffers) and frame lengths |
| asy_uart_comm.py:306, 364, 696 | is | _accept_set, _answer_get, _pull_chunk | keep | callback results (object) |
| asy_uart_comm.py:411 | ha | _call | keep | documented duck typing: a callback returns a coroutine or a plain value |
| asy_uart_comm.py:424, 429 | is | _check_buffer | keep | writability is checked on bytearray/memoryview (the :429 bytes branch went with the refusal) |
| asy_uart_comm.py:431-432 | ty (the refusal) | _check_buffer | **remove** | private; callers pass Writable (:1122, revealed bytearray/memoryview) or Readable/None (:1172); :424/:429 caught every typed value first |
| asy_uart_comm.py:447, 459 | is | _check_cmd_id, _check_size | unsure (U1) | ints at every call (revealed :1104-:1201; uart_link_driver passes int constants); the ranges stay; also refuse a bool |
| asy_uart_comm.py:646, 650, 652 | len, exc IndexError/TypeError, is | _pair | keep | an arbitrary callback's result (object) |
| asy_uart_comm.py:777 | is | _recv_train | keep | union narrowing (a caller buffer or the PieceBuffer) |
| asy_uart_comm.py:957, 963, 965, 974, 976 | is | _validate_link, _validate_receive | unsure (U1) | mypy redundant-expr ("left operand of or is always false"); each also refuses a bool, which the remaining range accepts at :957, :965, :974 |
| asy_uart_driver.py:212, 298, 349, 429, 767 | exc ValueError | (as named) | keep | a closed DMA channel raises it |
| asy_uart_driver.py:435, 728, 768, 774 | is | (as named) | keep | exc dispatch |
| asy_uart_driver.py:725 | exc TypeError (+MemoryError/OSError/OverflowError) | ready | **remove** (TypeError) | mask/timeout_ms ints at every call (eight internal calls, revealed int, select constants for mask); nothing in the loop raises TypeError for an int or a bool, and a malformed timeout_ms raised before the try anyway; reached only by the malformed-mask test (type ignore) |
| asy_uart_link_driver.py:139 | len | _exercise_loop | keep | the peer's answer (wire) |
| asy_udp_socket.py:41-42 | `mode not in` + raise ValueError | __init__ | **remove** | mode: Literal["client", "server"], and the three constructions pass literals (revealed); found by a mypy probe, not the scan; reached only by test_init_rejects_invalid_mode (type ignores) |
| asy_udp_socket.py:43 (is x3, len), 44 (rz) | is, len, rz | __init__ | unsure (U1) | redundant-expr ("left operand of and is always true"); addr: tuple[str, int] at all three constructions; the documented __init__ raise; also refuses a bool port |
| asy_udp_socket.py:69, 161 | exc TypeError | _connect, sendto | keep | documented API: the socket address format is port-specific (docs/library/socket.rst "Socket address format(s)"); the Unix port's connect/bind/sendto refuse a tuple (SPECIFICATION.md's Unix-port table) |
| asy_udp_socket.py:70, 93, 99, 136, 148, 162, 171 | is | (as named) | keep | exc dispatch |
| asy_udp_socket.py:135 | exc TypeError | ready | **remove** (TypeError) | mask/timeout_ms ints at every call (revealed :141, :158, :167); nothing in the try raises TypeError for an int or a bool; reached only by the malformed mask/timeout tests (type ignores) |
| asy_udp_socket.py:147 | exc TypeError | recvfrom | **remove** (TypeError) | buf: int (revealed; callers pass DNS_UDP_MAX, _NTP_PACKET_LEN); lwIP's and the Unix port's recvfrom raise TypeError only for a non-int (extmod/modlwip.c:1316); reached only by the malformed-buf test |
| asy_udp_socket.py:170 | exc TypeError | write | **remove** (TypeError) | msg bytes/bytearray (revealed at dns_client:167, ntp:269); the stream write raises TypeError only for a non-buffer (py/stream.c:277); no test raised TypeError there |
| asy_webserver_service.py:205, 746, 841 | is (+len at 746) | _body_as_dict, _dispatch_notification_led, _put_sensors | keep | a request body |
| asy_webserver_service.py:230, 362, 433, 449, 658 | len | (as named) | keep | fragment counts, HTTP lines (wire), the unavailable marker's shape |
| asy_webserver_service.py:238, 242, 245, 252 | is | _PieceWriter.add_value | keep | union narrowing over JSON values |
| asy_webserver_service.py:378 | exc ValueError | _check_head_line | keep | a request line (wire) |
| asy_webserver_service.py:606 | ga | __init__ | not a check | the route table names its handler |
| asy_webserver_service.py:811, 876, 879 | is | _print_exception, _put_status | keep | exc dispatch; gather(return_exceptions=True)'s results |
| asy_wifi_service.py:103, 113, 292, 344, 360, 570, 671 | len | (as named) | keep | values and list lengths |
| asy_wifi_service.py:111 (x3) | ty | _radio_value_ok | keep | value: object from a PUT body (:298); min/max a schema union |
| asy_wifi_service.py:652 | is | _push_wifi_led | keep | union narrowing of CfgValue (its comment says so) |
| asy_wifi_service.py:836 | len | _update_wifi_snapshot | keep | wlan.ifconfig() is the CYW43 port's answer; the stub's 4-tuple is a claim about C code mypy cannot check |
| build/generated_src/sensortask_*.py:203/206/221 (6) | ga | _collect_config_stores | keep | documented duck typing: the device's module set is heterogeneous, only some carry a cfgmgr |
| math_helpers.py:71, 123, 150, 170, 230 | exc ValueError | (as named) | keep | math domain errors |
| voc_algorithm.py:146 | exc TypeError (+OverflowError/ValueError) | pack_into | keep | buf: bytearray/memoryview admits a read-only memoryview, which pack_into() refuses with TypeError |
| voc_algorithm.py:154 | exc TypeError (+OverflowError/ValueError) | unpack_from | **remove** (TypeError) | buf a buffer and offset an int (revealed :848, :153); unpack_from() raises TypeError only for a non-buffer or a non-int offset; reached only by `unpack_from(None)` (type ignore). OverflowError/ValueError stay |

buildgen/codegen.py has 13 isinstance() calls. All are host-side code over the parsed TOML (tomllib's values are Any),
and none is emitted text; the one emitted check is the generated getattr() above.

nothing of mine is running
