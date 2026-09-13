# The Arduino C++ UART implementation — read-through, correlation and findings

**Temporary file, companion to `UART_C_PORT_CHANGELOG.md`. Delete both once the C implementation
has been reconciled with `src/asy_uart_comm.py`** — this one records what the imported C code
*actually does*, the changelog records what has to *change*. Neither has value afterwards.

Produced by a read-only familiarization pass (2026-09-13): no code was changed, nothing was run on
hardware. Everything below is from reading `arduino/`, `python/IndividualDrivers/`, `dev_legacy/`
and `src/`, plus one throwaway numeric check of the two CRC variants (§9).

## 1 What is in `arduino/`, and what it corresponds to

`arduino/` was added to `main` in commit `4d169a3` ("Arduino libraries added"). Three of the
libraries are this project's own; the rest are vendored third party.

| Path | Lines | Role |
|---|---|---|
| `libraries/Async_UART/Async_UART.{h,cpp}` | 53 / 170 | Bus driver. Counterpart of `python/IndividualDrivers/asy_uart.py` → `src/asy_uart_driver.py` |
| `libraries/Async_UART_Comm/Async_UART_Comm.{h,cpp}` | 134 / 779 | Message protocol. Counterpart of `python/IndividualDrivers/asy_uart_comm.py` → `src/asy_uart_comm.py` |
| `libraries/CRC_Check/CRC_Check.{h,cpp}` | 45 / 68 | CRC layer. Counterpart of `asy_uart.py`'s `CRC_Pass`/`CRC16` → `src/crc_checks.py` |
| `gas_sensor/basic_config_state/basic_config_state.ino` | 602 | **The real peer application**: BME688 + BSEC2, responder-only. Counterpart of `dev_legacy/asy_bsec_driver.py`'s `BSEC_UART` |
| `crc_test/crc_test.ino` | 197 | Bench/bring-up sketch for the link, mostly commented out |
| `basic_bme688/basic_bme688.ino` | 187 | Bosch BSEC example, **no UART protocol use at all** (`Serial1.begin()` only) |
| `libraries/{bsec2,BME68x_Sensor_library,Adafruit_BusIO,Adafruit_FRAM_SPI,FlashStorage,wdt_samd21}` | — | Vendored third party; `bsec2-6-1-0_generic_release/` is the raw Bosch release drop |

Only `basic_config_state.ino` and `crc_test.ino` use the protocol. `Adafruit_FRAM_SPI` and
`FlashStorage` are vendored but referenced by **no** sketch here — the C peer keeps no persistent
state of its own; the BSEC blob is pushed to it over the link and read back the same way.

**Provenance is not in doubt.** The C is a direct port of the legacy Python, not an independent
design: the same non-ASCII typo survives in both — `asy_uart_comm.py:50` `# skip timer onĺy in
listen mode.` and `Async_UART_Comm.cpp:33` `// skip timer onĺy in listen mode.` (U+013A). Field
names, state names, the `0xFE` UID wrap, the `(timeout*3)>>1` constants and the comment wording all
line up one-to-one.

## 2 Correlation map

```
                 legacy Python (field-proven)      C++ (Arduino peer)          promoted src/
  bus driver     asy_uart.py / AsyUART             Async_UART                  asy_uart_driver.py / UART
  CRC            asy_uart.py / CRC16, CRC_Pass     CRC_Check / CRC_16, CRC_None  crc_checks.py / CRC16, CRC_Pass
  framing        (none)                            (none)                      framing_codecs.py / Framing_Pass, Framing_COBS
  protocol       asy_uart_comm.py / UART_Comm      Async_UART_Comm             asy_uart_comm.py / UART_Comm
  application    dev_legacy/asy_bsec_driver.py     gas_sensor/basic_config_state.ino   (none yet — see BACKLOG)
  role           initiator (Pico)                  responder (SAMD21)          role is a constructor parameter
```

The two sides are **structurally mirrored, not symmetric**: Python is `async`/`await` over
`select.poll`, C is a cooperative state machine polled from `loop()`. Both express the same
stop-and-wait frame protocol.

- `Async_UART_Comm::loop_comm()` is the outer state machine (`_comm_mode`: IDLE / START_GET /
  READ_GET / WRITE_SET / LISTEN / CLEARING). It maps onto Python's `uart_get()` /
  `_get_unlocked()` / `_recv_train()` / `_send_train()` / `uart_listen()` / `_resync()`.
- `Async_UART_Comm::_check_comm()` is the inner state machine (`_comm_state`: IDLE /
  WRITE_STARTING / WRITE_WRITING / WRITE_READING / READ_READING / READ_READING_ACK / READ_WRITING /
  CLEARING). It maps onto Python's `_write_frame_with_ack()` / `_read_frame()` / `_send_ack()` /
  `_drain()`.
- `getCB`/`setCB` map onto `get_callback`/`set_callback`. Both are called **after** the command
  frame has already been ACKed, and a `false` return withholds the answer and forces a buffer
  clear — same shape as Python's `_reject_wrn()` path.

## 3 The protocol as the C actually implements it

Confirmed conformant to `SPECIFICATION.md` Part J (i.e. the C really does what J describes):

- **Frame layout** `[UID][CMD][SIZE][CHUNKS][CUR_CHUNK][payload…]`, fixed `5 + payload_size` bytes,
  payload zero-padded to full width from `_build_msg()`'s `memset` — J.3 and J.8's
  "no remnant is ever transmitted" rule both hold.
- **Command values** `ACK 0x01`, `GET 0x02`, `SET 0x04` — identical constants.
- **ACK shape** `_build_msg(recv_uid, CMD_ACK, chunks=1, cur_chunk=1, size=0, NULL)` — echoes the
  received UID, consumes none of the sender's own. Exactly what `_validate_ack()` expects.
- **UID** `_inc_uid()` is `(_uid >= 0xFE) ? 0 : _uid + 1` — **the `0xFF` barrier and the controlled
  wrap of changelog A8 are present and correct in C.** One UID per emitted data frame,
  consecutive across a train, so Python's `_next_uid(prev_uid)` prediction in `_recv_train()`
  matches the C sender byte for byte.
- **Constant `CHUNKS` across a train** — `_num_chunks` is computed once in `uart_set()` / the
  LISTEN→SET branch and passed to every `_build_msg()`. **A2's sender-side assumption holds.**
- **Chunk-count arithmetic is equivalent to Python's**, despite looking different:
  C `(size / payload) + 1`, `+1` again if `size % payload` or the result is `< 2`;
  Python `max(ceil(total/payload) + 1, 2)`. Checked at 0, `payload`, `payload+1`, `2*payload` — identical.
- **GET is answered by a SET train** whose chunk 1 echoes the requested id (`_build_msg(..., 1,
  &msgID)`), and the responder's answer runs through the same `MODE_WRITE_SET` code as an
  initiator's SET — the same "two primitives cover four directions" property J.4 describes.
- **The final ACK is deferred until after the total-size check** (`last_chunk` branch checks
  `_get_size != _get_addr` before `_enable_ack()`). J.4's deliberate deferral is present.
- **Recovery constants match exactly.** Drain quiet window `(timeout * 3) >> 1` and write hold-off
  `(timeout * 3) >> 1` — both 1.5 × timeout, both derived from the C side's own `timeout`, exactly
  as changelog A4 requires. **A4 is verified conformant.**
- **ACKs are never gated by the hold-off.** `STATE_READ_READING_ACK` calls `start_writing()`
  without consulting `_enable_writing`; only `STATE_WRITE_STARTING` checks it. Same rule as J.5.
- **`uart_listen()` drops the hold-off** (`_enable_writing = true; _write_timer_running = false;`)
  on the same reasoning as Python's `self._holdoff_active = False` in `uart_listen()`.
- **No retransmission anywhere.** Every fault path routes to `clear_buffers()` → drain → hold-off.

## 4 Deployment parameters actually in use — and the three live mismatches

| | C peer (`basic_config_state.ino`) | legacy Python (`dev_legacy`) | promoted Python (`src/sensortask_dev.py`, and `devices/dev.toml` on the buildgen branch) |
|---|---|---|---|
| baud | 115200 | 115200 | 115200 |
| `payload_size` | **20** | 20 | **48** |
| `timeout` | 1000 ms | 1000 ms | 1000 ms |
| CRC | **CRC_16, hardcoded** | `CRC16` (same algorithm) | **`CRC_Pass` — `crc=` is left unset** |
| framing codec | none | none | `Framing_Pass` (none) |
| `rxbuf` | SAMD21 core ring, 256 B | 32 | 512 |
| role | responder only | initiator | one of each, across the jumper |
| pins | `Serial1` (SAMD21 SERCOM) | Pico UART0 on **GP16/GP17** | GP0/GP1 (UART0) <-> GP8/GP9 (UART1) jumper |

`crc_test.ino` differs again: `payload_size = 48`, `timeout = 2500`.

The legacy pin choice is worth recording because Part J already leans on it: the deployed
`BME688_Reader(0, 16, 17, ...)` is why the dev board keeps GP16/GP17 free - "a BME688's BSEC
coprocessor wants UART0 there and one peripheral serves one pair". The crossover jumper and a real
Arduino link are therefore alternative uses of the same two peripherals, not things that can run
side by side: the Pico W has exactly two UARTs and the jumper already occupies both.

**Three independent reasons the promoted Python cannot talk to the existing Arduino today.** None of
them is a bug; all three are the expected consequence of the promotion, and all three have to be
settled together at reconciliation:

1. **CRC presence.** The C side *always* appends two CRC bytes; the promoted dev wiring appends
   none. Frame lengths differ (27 vs 25 at `payload_size = 20`), so not one frame can ever
   validate. This is the symptom changelog B18/B26 describe — and per B26 it will present as
   repeated `errno` 22 + `wrnno` 10, **not** as the named `errno` 32 diagnostic, because the
   Arduino only speaks when spoken to.
2. **CRC algorithm and byte order** (changelog A7) — see §9. Even with `CRC16` selected on the
   Python side, the two reject each other's frames.
3. **`payload_size` 48 vs 20** — a straight `_check_msg`/`_validate` mismatch on both sides.

**The interim A7 records — "run the link with CRC disabled (`CRC_Pass`)" — is not available without
changing C code.** `Async_UART_Comm` holds a `CRC_16 _crc16;` member by value and hands
`&this->_crc16` to `Async_UART::init()` unconditionally. `CRC_None` exists in `CRC_Check.h` and is
never instantiated anywhere. `Async_UART_Comm::init()` has no parameter for it. So the "supported
configuration" the changelog leans on is, on the C side as it stands, unreachable.

## 5 Defects found in the C library code

Severity is about what it does to the link, not about how hard it is to fix.

### 5.1 `CMD` is validated by bitmask, and the LISTEN path then falls through — **high**

`Async_UART_Comm.cpp:_check_msg()`:

```c
if (!((uint8_t)this->_read_buffer[ASYNC_UART_COMM_MSG_CMD] & exp_cmd)) { ... return false; }
```

This is exactly the defect changelog **A1** describes, and the changelog's open question ("this is
A1's fall-through bug on the C side, if it has it") is answered: **it has it, and it is worse in C
than it was in Python.**

In `MODE_LISTEN`, `exp_cmd = GET | SET = 0x06`. A frame whose `CMD` is `0x06` (also `0x03`, `0x05`,
`0x07`) passes the mask, then matches neither `if (CMD == CMD_GET)` nor `if (CMD == CMD_SET)`, and
execution **falls out of the `case ASYNC_UART_COMM_CHECK_OK:` block into the next label**,
`case ASYNC_UART_COMM_CHECK_CLEARING:` — not into `default:` as the comment on line 398 claims:

```c
        // in (the actually impossible) case of no return until here, code will correctly fall to "default" state!

        case ASYNC_UART_COMM_CHECK_CLEARING:
          this->_comm_mode = ASYNC_UART_COMM_MODE_CLEARING;
          _printDebug("Uart_Comm_uart_listen: Forced into Clearing mode!");
          return ASYNC_UART_COMM_CLEARING;
```

That branch sets clearing *mode* but never calls `clear_buffers()`, so `_clear` stays false and the
actual drain never starts. Meanwhile `_comm_state` is still `READ_READING_ACK` with
`_enable_read_ack` true, so the next `_check_comm()` **sends an ACK for the malformed frame** before
the state machine flounders into `MODE_CLEARING`'s `default:` and retries a clear. Net effect: a
malformed frame is acknowledged as if valid, the recovery that was supposed to run does not, and the
debug log names the wrong cause.

In `MODE_START_GET`/`MODE_READ_GET` (`exp_cmd = CMD_SET`) the same mask accepts `0x05`, `0x06`,
`0x0C`… and then processes them *as* a SET. No fall-through there, but silent mishandling.

### 5.2 The receive drain is unbounded — **high**

`_check_comm()`'s `STATE_CLEARING` re-issues `start_reading(NULL, frame, 1.5 × timeout)` for as long
as bytes keep arriving; the only exit is a full quiet window. A peer that never stops transmitting
keeps the C side clearing forever. This is changelog **A5**, and it is absent in C. Python bounds
the loop at `4 × quiet_ms` and logs `wrnno` 11.

### 5.3 `cancel_read_timeout()` is only honoured on an empty receive buffer — **medium**

`Async_UART::check_reading()` / `check_reading_until_complete()` consult `_cancel_reading` **only**
inside the `available() == 0` branch. While bytes keep arriving the cancel is never observed, and
`_check_comm()`'s clearing preamble calls `cancel_read_timeout()` once per round to no effect. The
request is also silently discarded by the next `start_reading*()` (both set `_cancel_reading =
false`). This is the C form of the two defects changelog **B15** fixed on the Python side (a request
cleared by an unrelated entry; no bounded acknowledgement). J.5 designates this mechanism as *the*
recovery route for a blocked listener, so it needs to be equally terminating in C.

### 5.4 A zero-`SIZE` chunk mid-train silently truncates a variable-size GET — **high**

`loop_comm()`, `MODE_READ_GET`, `CHECK_READING_DONE`:

```c
} else if (msg_size == 0) {                  // received empty message
  if (this->_get_received_size == NULL) { ...fixed size: error if _get_size != 0... }
  else { *this->_get_received_size = 0; }
  this->_exp_chunk = 0;
  _enable_ack();
  return ASYNC_UART_COMM_GETTING;
}
```

A `SIZE = 0` frame is treated as "end of message" at **any** chunk index ≥ 2, regardless of
`last_chunk`. In the variable-size branch it then reports **zero bytes received** even when earlier
chunks already wrote data into the destination buffer — the caller gets `received_size == 0` and a
*success* status, with stale data sitting in its buffer. The fixed-size branch is saved by accident
(`_get_size != 0` errors out).

Python's changelog **A12** rule is `SIZE == 0` legal only on the final chunk of a two-chunk train.

### 5.5 `&this->_get_dest == NULL` — the NULL-destination guard is dead code — **medium**

```c
if ( (msg_addr > this->_get_size) || (&this->_get_dest == NULL) ) {  // message too large for buffer
```

`&this->_get_dest` is the address of a member of a live object and can never be null; GCC warns on
this. The intent was `this->_get_dest == NULL`. It happens not to bite today only because every
caller that passes a NULL destination also forces `_get_size = 0`, so `msg_addr > 0` catches it
first. Any future path that sets a size without a buffer memcpy's to NULL.

### 5.6 `uart_set()` chunk-count overflow at `payload_size == 1` — **low**

```c
uint16_t num_chunks = (this->_set_size / this->_payload_size) + 1;
```

With `_set_size = 0xFFFF` and `_payload_size = 1`, this is `65536` truncated to `0` in `uint16_t`;
the `< 2` branch then makes it `1`, the `> 0xFF` guard never fires, and a 65535-byte payload is sent
as a **one-chunk train**. Only reachable at `payload_size == 1`, which changelog A6's range check
would not exclude (A6 allows `1 … 255`). Worth widening the intermediate to `uint32_t`.

### 5.7 No `payload_size` validation at all — **medium**

`Async_UART_Comm::init()` accepts any `uint8_t`, including `0`. At `payload_size = 0` the buffers are
7 bytes, `_build_msg()` writes the command id at index 5, and `start_writing()`'s CRC then overwrites
indices 5 and 6 — the command id never reaches the wire and nothing reports it. This is changelog
**A6**, absent in C.

### 5.8 `init()` leaks on partial allocation failure — **low**

If `_read_buffer` succeeds and `_write_buffer` fails, `init()` returns `false` without freeing the
first. There is no destructor and no `free()` anywhere; a re-`init()` leaks both. Compare
changelog **B23**, which is the same failure shape the Python side had to close.

### 5.9 `check_writing()` tests the write state against a *read* constant — **low**

```c
uint8_t Async_UART::check_writing() {
  if (this->_write_status == ASYNC_UART_READ_IDLE) {
```

Works only because `ASYNC_UART_READ_IDLE` and `ASYNC_UART_WRITE_IDLE` are both `0`. A latent trap if
either enumeration is ever renumbered.

### 5.10 Dead `< 0` test on an unsigned value — **cosmetic**

`_check_msg()`: `if ( (*msg_size < 0) || (*msg_size > this->_payload_size) )`. `*msg_size` is
`uint8_t`; the first half is always false and GCC warns.

### 5.11 No ACK-shape validation — **medium**

`_check_comm()`'s `STATE_WRITE_READING` checks only `CMD == ACK` and the UID. It does not check
`SIZE == 0`, `CHUNKS == 1`, `CUR_CHUNK == 1` the way Python's `_validate_ack()` does. A malformed
ACK confirms a frame.

### 5.12 No `SIZE`-per-position validation outside the LISTEN chunk 1 — **medium**

The C *does* enforce `msg_size == 1` on chunk 1 in `MODE_LISTEN` — that half of changelog **A12** is
already present. It does **not** enforce it on a GET answer's chunk 1 (`MODE_READ_GET` with
`_exp_chunk == 1` only compares the echoed id, so a `SIZE = 0` chunk 1 yields id `0x00` from a
padding byte and is rejected only if the requested id happened to be non-zero), and it does not
enforce `SIZE == payload_size` on middle chunks. Both are silent-corruption paths.

### 5.13 A `SET` train declaring `CHUNKS = 1` is rejected late — **low**

C sets `_exp_chunk = 2` and discovers the problem only when chunk 2 fails `cur > chunks` — after
chunk 1 has already been ACKed. Python rejects it at chunk 1 (`cmd == CMD_SET and chunks < 2`).

### 5.14 No write-side timeout — **low, shared with Python**

`check_writing()` returns `ASYNC_UART_WAITING` indefinitely if `availableForWrite()` never rises, and
its `Uart::write()` return value is ignored (Python's `_write_all()` does handle a short write).
`asy_uart_driver.py`'s `_write_all()` likewise awaits `ready(POLLOUT)` with no deadline, so this is a
symmetric gap rather than a divergence — worth a decision at reconciliation, not a unilateral fix.

### 5.15 `CRC_16::add()` relies on `char` being unsigned — **portability**

```c
bytes[length]     = (char)0xFF & crc;
bytes[length + 1] = (char)0xFF & crc >> 8;
```

Correct on SAMD21 (ARM: `char` is unsigned), and the precedence is right (`>>` binds tighter than
`&`). On a signed-`char` target `(char)0xFF` sign-extends to `-1` and the masking silently becomes a
no-op. The same assumption runs through the whole library, which passes command ids around as `char`
— any command id ≥ `0x80` would compare as negative in a `switch` on a signed-`char` platform.
Python's range is a full `0 … 255` (changelog B19).

### 5.16 `Async_UART::start_writing()` writes past the caller's length — **API landmine**

`start_writing(buf, n)` calls `_crc->add(buf, n)`, which writes `buf[n]` and `buf[n+1]`. Safe for
`Async_UART_Comm` (its buffers are `malloc`'d with `+CRC_CHECK_CRC_16_SIZE`), but the commented-out
direct-`Async_UART` use in `crc_test.ino` would overflow a plain `char buf[]`. The header says
"make sure buffer is large enough!" and nothing enforces it.

### 5.17 Declarations between a `case` label and its statement — **style/robustness**

`loop_comm()` declares `uint8_t msg_size; uint16_t msg_addr; bool last_chunk;` and
`uint16_t cur_addr, cur_size;` and `char msgID; ... uint16_t num_chunks;` directly after `case`
labels. Legal only because none has an initializer; adding one turns it into a hard compile error
("jump to case label crosses initialization"). The blocks want braces.

### 5.18 Missing library metadata — **cosmetic**

`Async_UART`, `Async_UART_Comm` and `CRC_Check` have no `library.properties` and no `keywords.txt`,
unlike every vendored library beside them. They work as flat sketchbook libraries but cannot be
managed by the Arduino library manager or pinned by `arduino-cli`.

### 5.19 `ASNYC_UART_NO_TIMEOUT` — **cosmetic**

Misspelt (`ASNYC`) in the public header and used at four call sites.

## 6 Defects and hazards at the sketch level

### 6.1 `uart_listen()`'s return value is ignored in both sketches — **latent**

```c
if ((readStatus == ASYNC_UART_COMM_IDLE) && (listenStatus == LISTEN_IDLE)) {
  uart_comm.uart_listen(getCallback, setCallback);
  listenStatus = LISTEN_LISTENING;
}
```

If `uart_listen()` ever returned `false`, `listenStatus` would go to `LISTEN_LISTENING` while the
library stayed idle, and neither of the two conditions that reset `listenStatus` can fire again — a
permanent stall, with the watchdog still being fed, so no reset either. It cannot currently trigger
(the app only calls it when `loop_comm()` reported `IDLE`, which implies `_comm_state == IDLE`), but
it is one refactor away from being live and costs one `if`.

### 6.2 Structs are put on the wire raw — **fragile contract**

`getCallback` hands out `(char*)&AllMeasDataCache, sizeof(meas_data)` and
`(char*)&SystemStatusCache, sizeof(system_status)`; `dev_legacy/asy_bsec_driver.py` decodes with
`struct.unpack(num_datafields * "f" + "HH", res)` and `struct.unpack("bbbbL", res)`.

Today the layouts agree — `meas_data` is 13 × `float` + 2 × `uint16_t` = 56 bytes with no padding,
`system_status` is 4 × `int8_t` + `uint32_t` = 8 bytes (matching `_BME688_Num_Datafields = 13` and
`_UART_SYSTEM_STATE_SIZE = 8` on the Python side), and both targets are little-endian ARM with
the same alignment rules. But nothing checks it: the Python format strings are hand-maintained
mirrors of the C structs, the `#if SENSOR_MODE` switch silently changes `meas_data`'s shape
(CLASSIFICATION mode has 9 floats, not 13), and adding a field of a different width would introduce
padding the Python side does not model. Worth a comment on both sides at minimum.

### 6.3 A GET callback can do real work inside the protocol's critical section

`UART_GET_BSEC_STATE` calls `envSensor.getState(bsecState)` from inside `getCallback`, i.e. inside
`loop_comm()`. A slow callback stalls the state machine and, more to the point, the 250 ms watchdog
(`wdt_init(WDT_CONFIG_PER_256)` — 256 cycles of the 1.024 kHz WDT clock). Same class of risk as
Python's guarded dispatch, but with a hardware deadline attached.

### 6.4 Debug output can trip the watchdog

`_printDebug()` writes to the native-USB CDC `Serial`. With `set_debug(true)` and no host reading
the port, `println()` can block far longer than the 250 ms watchdog window. Debug is off by default
in `basic_config_state.ino`; `crc_test.ino` turns it on.

### 6.5 `crc_test.ino` initiates from the responder side

It calls both `uart_listen()` and `uart_set()`/`uart_get()` on the same instance. That is fine for a
bench sketch against a quiet peer, but it is exactly the simultaneous-initiation case J.2 says is out
of contract, and the promoted Python now refuses it structurally (changelog B8). If that sketch is
kept, it should be documented as a single-ended test tool.

### 6.6 `uart_comm.init()`'s failure handling resets the board

`if (!uart_comm.init(...)) { updateWatchdog = false; }` — a failed `malloc` reboots the board about
250 ms later, forever, with no diagnostic. Deliberate, and arguably right for a headless peer, but
worth knowing before chasing a "boot loop".

## 7 Verdict on every `UART_C_PORT_CHANGELOG.md` Class A entry, against the real C source

This is the column the changelog left open ("Verify in C"). Nothing here changes the changelog's
decisions; it fills in what was unknown.

| # | Changelog expectation | What the C source actually does | Work needed in C |
|---|---|---|---|
| **A1** | "Whether the C receiver also masks; whether the C sender can ever emit a multi-bit `CMD`" | **It masks** (`_check_msg`, §5.1). The sender never emits a multi-bit `CMD`. The receiver additionally **falls through to the wrong label** and ACKs the frame | Exact-match `CMD`; add `default:`/braces to the LISTEN switch. Fixes §5.1 |
| **A2** | "That the C sender writes a constant `CHUNKS` across every frame of a train" | **It does** — `_num_chunks` is fixed per train. The receiver does **not** latch/compare it | Add the receiver-side latch. Sender needs nothing |
| **A3** | "Whether the C sender increments `UID` per chunk exactly as Python does" | **It does** — `_inc_uid()` per emitted data frame, ACKs echo and consume none. The receiver does **not** validate UID on data chunks | Add receiver-side UID validation. Sender needs nothing |
| **A4** | "That the C side uses the same two durations, derived from its own `timeout`" | **Verified conformant** — `(timeout * 3) >> 1` for both the drain quiet window and the write hold-off | None |
| **A5** | "That the bound chosen is never shorter than the C side's own drain window" | The C drain is **unbounded** (§5.2) | Add a bound ≥ Python's `4 × 1.5 × timeout`, plus a diagnostic |
| **A6** | "That the C side's compile-time constant is within range and matches the Python deployment value" | `payload_size` is a **runtime** `uint8_t` parameter with **no validation** (§5.7). Deployed value is **20**; promoted Python defaults to **48** | Add the `1 … 255` check *and* settle the deployed value on both sides |
| **A7** | CRC algorithm + byte order flag day; interim "run with `CRC_Pass`" | C uses the legacy algorithm **and cannot be configured without CRC at all** (§4) — `CRC_None` exists but is never reachable from `Async_UART_Comm`. See §9 for the numeric identity | Replace `CRC_16::_crc16` with MSB-first CCITT-FALSE, append big-endian, **and** add a way to select `CRC_None` so the documented interim actually exists |
| **A8** | "That the C counter also stops at `0xFE`, and nothing predicts a next UID with a bare `+1`" | **Verified conformant** — `_inc_uid()` wraps `0xFE → 0`; nothing in C predicts a next UID at all | None |
| **A9** | NAK; "verify the C receiver's unknown-`CMD` path really does reject-and-resync rather than mishandle" | **It does not** — §5.1 is precisely that mishandling. A9's "degrades safely" argument **fails against the current C** | A1 must land in C *before* A9 can be considered safe |
| **A10** | Short 5-byte ACK; "that the C side's ACK read/write sites are likewise context-determined" | **They are.** `STATE_WRITE_READING` always expects an ACK; `STATE_READ_READING` always expects a data frame; `STATE_READ_READING_ACK` always writes one. No shared fixed-length frame routine | Mechanically feasible; still a flag day |
| **A11** | COBS framing; "the whole C framing layer is replaced" | Confirmed: `check_reading_until_complete()` is a pure fixed-count reader with no delimiter concept. There is no C counterpart to `framing_codecs.py` | Largest single change; flag day |
| **A12** | "That its first chunk always declares `SIZE = 1`, and that it never short-fills a non-final chunk" | **Sender conforms** on both counts. **Receiver enforces `SIZE == 1` only in `MODE_LISTEN`** — not on a GET answer's chunk 1, not `SIZE == payload_size` on middle chunks, and it accepts `SIZE == 0` anywhere (§5.4, §5.12) | Add the full per-position rule to `_check_msg()` |

**Summary: of the seven Class A entries with a sender-side assumption, every one holds.** The C
*emits* what the promoted Python expects. The gap is entirely on the receiving side (validation
strictness) plus the two flag days (A7 now, A10/A11 if chosen).

## 8 Class B entries that nevertheless have a C-side counterpart worth acting on

The changelog already flags most of these as "worth the C side's attention". Confirming which ones
actually apply:

| # | Applies to C? | Note |
|---|---|---|
| **B15** (cancel is latched, acknowledged, bounded) | **Yes** — §5.3. J.5 names this as the recovery route, so it has to terminate |
| **B17** (`rxbuf` floors) | **Partly.** The SAMD21 core's 256-byte RX ring comfortably holds a 27-byte frame at `payload_size = 20`, but would be overrun by the 260-byte frame at the maximum legal `payload_size = 255`. Worth a static assert |
| **B19 / B22** (validate caller arguments) | **Yes** — `char getID` (§5.15) and the unvalidated `payload_size` (§5.7) are the same shape: a silently-truncated value that produces a *different valid* request |
| **B23** (refuse construction unless every buffer allocated) | **Yes** — §5.8. C checks both buffers but leaks the first |
| **B24 / B25** (never hold the loop in a read) | **Partly.** The C reader is already non-blocking by construction (`available()` before every `read()`), which is structurally what B24's clamp achieves. But §6.3 shows the *callbacks* can hold the loop, and `_printDebug()` (§6.4) certainly can |
| **B26** (the errno-32 blind spot) | **Yes, as a diagnostic expectation.** The C peer is speak-when-spoken-to, so B26 predicts the mismatch in §4 will present as `errno` 22 + `wrnno` 10 on the Python side, never as `errno` 32. Expect that signature first at reconciliation |
| **B29 / B30** (every fault also resyncs) | **Mostly holds in C** by construction — nearly every error path calls `clear_buffers()`. **One real exception**: the A1 fall-through (§5.1) sets clearing mode without setting `_clear`, so that fault does *not* drain |
| **B8** (role enforced structurally) | **No C counterpart.** `Async_UART_Comm` is symmetric and `crc_test.ino` uses it that way (§6.5) |
| **B13 / B21** (well-defined result shape, message delivery) | **No C counterpart needed** — the C API is callback+status-code, not a return value |
| **B16** (boot drain) | **Present, but at the application level**, not in the library: `listenStatus = LISTEN_UNINITIALIZED` → `clear_buffers()` on the first `loop()`. Worth moving into `init()` so every sketch gets it |

## 9 The CRC, verified numerically

Verified directly this session with a throwaway reference implementation of both variants (not
committed):

| | algorithm | poly constant | init | wire order | check value over `"123456789"` |
|---|---|---|---|---|---|
| C `CRC_16` / legacy `asy_uart.py` | reflected (right-shifting) | `0x1021` | `0xFFFF` | little-endian (`struct.pack("H", …)`, native) | **`0x1DBA`** |
| `src/crc_checks.py` `CRC16` | MSB-first, CRC-16/CCITT-FALSE | `0x1021` | `0xFFFF` | big-endian (`pack_into(">H", …)`) | **`0x29B1`** |

- Each is **self-consistent**: the residue over payload+CRC is `0x0000` for its own frames.
- Each **rejects the other's** frames (`0xBEF6` and `0x121B` on a 25-byte sample). Part J.3 and
  changelog A7 are confirmed exactly.
- **The C/legacy variant matches no catalogued CRC-16.** `0x1DBA` is not KERMIT (`0x2189`), X-25
  (`0x906E`), MCRF4XX (`0x6F91`) or CCITT-FALSE (`0x29B1`). It is the classic reflected-loop /
  normal-form-constant mismatch: a right-shifting loop wants `0x8408`, and this one was given
  `0x1021`. The result is a valid, self-consistent CRC — just not a named one.
- **It is not, however, measurably weaker.** An exhaustive meet-in-the-middle search over a 48-bit
  window found **no** undetected 2-, 3- or 5-bit error for either variant, and weight-4 undetected
  patterns for both. So "replace it" (A7's owner decision, Python leads) is the right call for
  *specification* reasons — a named, reproducible algorithm — not because the field-proven one was
  unsound. Worth saying plainly, because the changelog does not, and a reconciliation session could
  otherwise read A7 as a defect fix.

## 10 Ordered to-do list for bringing the Arduino side up to date

Ordered so that each step leaves the link in a testable state. Steps 1–3 are pure
receiver-strictness and can land on the C side *alone*, against today's Python, before any flag day.

1. **A1 + the fall-through** (§5.1) — exact-match `CMD`, brace the `MODE_LISTEN` switch, add
   `default:`. Also makes A9 safe to consider later.
2. **A12 receiver rules + A2 + A3 + §5.11** (§5.4, §5.11, §5.12) — one pass over `_check_msg()`:
   exact `SIZE` per chunk position, latched `CHUNKS`, per-chunk `UID`, ACK shape. This is where most
   of the silent-corruption surface is.
3. **A5 + B15** (§5.2, §5.3) — bound the drain; latch and bound the cancel.
4. **A6 + §5.6 + §5.8 + §5.5 + §5.9 + §5.10** (§5.5–§5.10) — input validation, the `uint16_t`
   overflow, the dead NULL guard, the allocation leak, the two wrong-constant/dead-code warnings.
5. **Agree `payload_size`** — 20 (the C peer's deployed value) or 48 (the promoted Python default).
   Out-of-band decision, owner's call, both ends changed together.
6. **A7, the flag day** — replace `CRC_16::_crc16` with MSB-first CCITT-FALSE and big-endian
   append, **and** plumb `CRC_None` through `Async_UART_Comm::init()` so the documented CRC-off
   interim exists. Then select `CRC16` on the Python construction site.
7. **Optional, separately decided**: A10 (short ACK), A11 (COBS). Both are flag days; A11 replaces
   the whole C framing layer.
8. **Sketch-level**: §6.1 (check `uart_listen()`'s return), §6.2 (document or generate the wire
   struct layout on both sides), §6.5 (document `crc_test.ino` as single-ended).
9. **Housekeeping**: `library.properties`/`keywords.txt` for the three project libraries (§5.18),
   the `ASNYC` typo (§5.19), the `char`-signedness assumption (§5.15).

## 11 Open questions for the project owner

1. **`payload_size`: 20 or 48?** Step 5 above. 20 is what the field-validated pair used; 48 is the
   promoted default and what `devices/dev.toml` declares for the crossover jumper. The dev bench's
   two Python instances and the Arduino peer do not have to agree with each other — but a
   Pico↔Arduino link does.
2. **Does the C side get a CRC-selection parameter at all**, or is CRC simply always on once both
   ends carry the same algorithm? The changelog's A7 interim assumes selectable; the C code assumes
   fixed. Either is fine, but the changelog should stop promising an interim that does not exist.
3. **Is `crc_test.ino` worth keeping** once the promoted Python can drive the link from the dev
   bench? It is the only thing in `arduino/` that initiates from the responder side.
4. **Should `basic_bme688/` and `bsec2-6-1-0_generic_release/` stay in the repo?** Neither is part of
   the UART story; the latter is a 200+ file vendor release drop whose relevant parts are already
   duplicated inside `libraries/bsec2/`. If they stay, they want the same "vendored, hands-off"
   rule `ext/microdot.py` has.
5. **Do the `arduino/` sources come under any of the repo's quality apparatus?** Today they are
   outside every lint/typecheck/test scope, like `python/` and `modules/`. Unlike those, the C is
   *not* reference-only — it is a live second implementation that will be edited. Worth an explicit
   decision rather than inheriting the legacy-tree rule by default.
