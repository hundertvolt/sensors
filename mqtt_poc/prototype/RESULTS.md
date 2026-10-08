# MQTT PoC prototype — dev digital twin against a real mosquitto: results (2026-10-07)

**What this is.** The owner's request (2026-10-07): "Just run a test try: install a real mosquitto and check a dev
variant digital twin against it. And once working, torture it with errors and outages from both sides and watch it
recover well according to our rules. Hammer it and see that it does not flood the heap, even with gc threshold off."
This file records what was run and what it showed. The client is a **prototype** (`asy_mqtt_client.py`), written to
`mqtt_poc/RESEARCH.md` section 7 and the owner's answers in section 8.0; it is not `src/` code and is wired into no
build. Everything ran on the MicroPython v1.29.0 Unix port (the twin), not on rp2 hardware, so rp2-only behaviour
(lwIP pools, the `ERR_MEM` stall, CYW43 link loss) is untested here — RESEARCH.md section 4 lists those.

## Setup

| Part | What |
|---|---|
| Broker | mosquitto 2.0.18 (Ubuntu 24.04 apt package), `listener <free port> 127.0.0.1`, anonymous, no persistence |
| Device | the buildgen-generated `sensortask_dev` booted by `digital_twin/run_generic_integration.py` on the audit tree at `5689e2f` (U15) merged into this branch |
| Client | `asy_mqtt_client.py`: MQTT 3.1.1, QoS 0/1, clean session, keepalive 30 s, ping every 10 s with a 5 s deadline, backoff 2 s doubling to a 30 s cap and reset only after 15 s of stable connection, 1 KB receive buffer, 16-slot x 512 B outbound ring, last will `offline` (retained, QoS 1) |
| Harness | `run_dev_mqtt_twin.py`: attaches the client to the twin's real `WifiService` (lock, `network_available_locked`, DNS getter), publishes each sensor module's measurements as JSON every 5 s (owner decision 8.7), test consumers for `cmd/echo`, `cmd/value/+` and `cmd/#` (8.6: values and behaviours, RAM only) |
| Driver | `torture.py`: starts mosquitto and an observer (`mosquitto_sub sensors/#`), boots the twin, sets the SSID through the real `PUT /networking`, runs the fault timeline from the first retained `online`, then summarises |
| GC | `gc.threshold(-1)` (MicroPython's own default, "threshold off"); heap samples are instrumentation-only collects every 5 s, as `run_generic_integration.py`'s own sampler does |

## Results at a glance

- **Zero** `MemoryError`, **zero** "memory allocation failed", **zero** tracebacks, clean exit, in every run, at
  `gc.threshold(-1)` and at the shipped `gc.threshold(32768)`.
- Every fault ended in a reconnect without any WiFi action, inside the backoff schedule.
- No QoS 1 message the client accepted was lost; QoS 0 drops happen only at the bounded ring and are counted.
- The live heap with the client is flat apart from a drift the twin shows **without** the client too (below).

## The torture run (gc.threshold(-1), ~12 min)

Times are seconds after the first connection. "Back after" is from the end of the fault to the next CONNACK.

| t (s) | Fault (side) | Detected by | Back after | Rule it shows |
|---|---|---|---|---|
| 25 | inbound burst: 200 QoS0 echo, 100 QoS1 values, 5 x 5,000 B payloads, 6 bad values, 20 new value names, 100 retained (broker side) | — | no outage | 5 oversize packets discarded in chunks, never allocated (`rx_oversize` 5); 6 bad values refused; value table capped at 8 names (13 refused); 184 echo replies dropped at the 16-slot ring and counted |
| 55-80 | broker SIGKILL, 25 s down | EOF, then 3 x `ECONNREFUSED` | 10.7 s (next backoff slot) | capped exponential backoff (2, 4, 8, 16 s), never zero |
| 110-150 | broker SIGSTOP: connections stay open, nothing answers | missed PINGRESP; CONNACK waits time out | 14.7 s | the ping deadline is the dead-link detector |
| 180-220 | iptables DROP on the broker port, both directions (silent path loss: the CYW43 false-positive shape) | missed PINGRESP; connects time out | 14.8 s | as above |
| 250-265 | a second client takes the id `dev` | EOF on each takeover | 1.8 s after it left | 3 swaps in 15 s: the backoff only resets after a stable connection, so a duplicate id cannot drive a fast loop |
| ~290 | outbound hammer 200 msg/s for 30 s, every tenth QoS 1 (device side) | — | no outage | 4,646 accepted, none refused; 464 QoS 1 delivered and acknowledged; 38 QoS 0 overwritten at the ring, counted |
| ~336 | WiFi drop in the twin, 2 failed rejoins (device side) | `network_available_locked()` False | 2 s after WifiService rejoined (outage ~140 s, WifiService's own 60 s wait plus two failed joins) | link outage waited out, backoff not grown, WiFi never touched by the client |
| 470 | broker graceful restart (SIGTERM) | EOF | inside the WiFi recovery above | — |
| 510-580 | broker SIGKILL, 70 s down | `ECONNREFUSED` x 5 | 21 s (backoff at its 30 s cap) | the cap holds |

Final counters: 9 connects, 14 failed connect attempts, 2 ping timeouts, 8 teardowns, 0 protocol errors, 0 handler
errors, 473 PUBACKs for 473 QoS 1 publishes, 0 retransmissions, 0 give-ups.

**Will messages.** The retained status always ended `online` while connected. Two things are worth knowing:
- After the SIGSTOP stall the broker published `offline` four times at once: one will per connection attempt it had
  accepted at TCP level but never answered. Harmless (the client's fresh `online` followed 13 s later), but a status
  consumer sees a burst.
- During the takeover each swap publishes the old connection's will, so `offline`/`online` alternate. The final
  retained value is right; a consumer must read the retained state, not count transitions.

**Missed by design of the timeline.** The 20,000-message sustained flood at t=430 landed while the client was waiting
out the WiFi drop, so it reached nobody. The flood run below repeats it while connected.

## The flood run (gc.threshold(-1), ~5 min, connected throughout)

| Phase | Result |
|---|---|
| Inbound flood: 20,000 QoS 0 echo + 2,000 QoS 1 values, sent in 0.3 s | all 20,000 QoS 0 received; 1,127 QoS 1 received and acknowledged; **873 QoS 1 dropped by mosquitto**, not by the client ("Outgoing messages are being dropped for client dev": the broker's per-client queue, `max_queued_messages` 1000 by default); 19,813 echo replies dropped at the ring and counted |
| Outbound hammer: 200 msg/s for 30 s | 4,680 accepted, none refused; all QoS 1 acknowledged |
| Connection | no teardown, 27 pings answered |

**Allocation churn** (`gc.mem_alloc()` sampled every 500 ms *without* collecting; the rise between samples is what was
allocated). The connected-idle client adds nothing measurable: the twin allocates ~128 KB/s on its own and ~126 KB/s
with the client idle, so the client's idle path sits inside the twin's own noise. Under load the client costs tens of
bytes per received message and ~140 B per publish:

| Phase | Allocated | Extra over idle | Per message |
|---|---|---|---|
| Twin with client, connected, idle | ~126 KB/s | — | — |
| Inbound flood (21,127 messages) | ~180 KB/s | ~54 KB/s for ~15 s | ~38 B per received message |
| Outbound hammer (~156 msg/s) | ~150 KB/s | ~22 KB/s | ~140 B per publish, harness loop included |
| Twin **without** client (baseline, 180 s) | ~128 KB/s | — | — |

## The same torture run at the shipped gc.threshold(32768)

The project rule runs everything at both GC stages (CLAUDE.md memory-safety rule), so the full timeline ran a second
time at the firmware's own threshold. Same outcome: zero `MemoryError`, zero "memory allocation failed", zero
tracebacks, clean exit; 9 connects at 0.7, 86.7, 150.8, 230.9, 252.9, 258.9, 266.9, 475.1 and 601.2 s (the stall
recovery landed 0.8 s after SIGCONT this time, because a backoff slot happened to fall there); 2 ping timeouts, 0
protocol errors, 0 retransmissions, 0 give-ups; live-heap slope 22.5 B/s, the twin's own drift again.

## Heap: does it flood?

Live heap after an instrumentation collect, every 5 s, at `gc.threshold(-1)` on the twin's default 2 MB heap:

| Run | After boot settle (+90 s) | End | Linear slope after +90 s |
|---|---|---|---|
| dev twin **without** the client (baseline, same 12 min) | 1,096,768 B | 1,112,256 B | **24.9 B/s** |
| dev twin **with** the client and the whole torture timeline | 1,117,024 B | 1,132,448 B | **22.7 B/s** |

- The client adds a **constant ~20 KB** (its buffers plus the prototype's bytecode, which the Unix port keeps on the
  heap and the firmware would freeze into flash) and **no growth**: the slope is the same with and without it, and no
  phase (burst, nine reconnects, hammer, WiFi outage, flood) leaves a step.
- The ~25 B/s drift belongs to the twin's dev system itself. It is outside this PoC; it may be a fill-to-capacity
  effect (for example U15's new SCD30 deviation window) that plateaus over a longer run. Recorded here for the audit,
  not chased.

## Findings for the real client

1. **Gating works as designed**: on a fresh twin with no SSID, WifiService runs the hotspot, `network_available_locked()`
   is False, and the client never tried to connect until the SSID was set over REST.
2. **Backoff reset needs a stability condition**, not "first success": with a reset on CONNACK, a duplicate client id
   or a broker that drops each new session would loop at the minimum backoff. Resetting after 15 s connected kept the
   takeover to three swaps.
3. **A broker can drop QoS 1 on its side** under an inbound flood (mosquitto's per-client queue). End-to-end QoS 1
   holds only inside the broker's limits; worth a line in the topic/payload contract.
4. **Will bursts after a stall** (four `offline` at once): consumers should read the retained state.
5. **A duplicate client id is invisible today** except as frequent EOF teardowns; the real module should count short
   sessions and warn once ("possible duplicate client id").
6. **Echo-style replies need their own budget**: one inbound message producing one outbound message makes the
   outbound ring the bottleneck under any inbound flood (19,813 dropped). Correct (bounded, counted), but the real
   design should decide per consumer whether replies may be dropped.
7. Cosmetic: the teardown log line for a link outage carried the previous `last_err` text.

## Not covered here (needs the dev bench, owner go-ahead per CLAUDE.md)

lwIP PCB/pbuf/`MEM_SIZE` limits and the `ERR_MEM` 10 s stall; CYW43 link loss and the `isconnected()` false positive;
`ECONNRESET`/`ECONNABORTED` (rp2) instead of the Unix port's `ECONNREFUSED`; heap placement in the real 192 KB GC heap
next to six HTTP connections (`max_connections` 5 on dev, owner decision 8.4); the ~125-byte payload stall reported on
Pico W (micropython-lib #994).

## Reproducing

As root from the repo root, with the toolchain built (`uv run toolchain/setup_toolchain.py setup`), mosquitto
installed, `scripts/build_website.sh dev` and `uv run scripts/_generate_sensortask_modules.py` run first:

```bash
python3 mqtt_poc/prototype/torture.py --gc-threshold -1 --out /tmp/mqtt_torture          # full timeline, ~12 min
python3 mqtt_poc/prototype/torture.py --baseline --gc-threshold -1 --out /tmp/mqtt_base   # twin without the client
python3 mqtt_poc/prototype/torture.py --scenario flood --churn-ms 500 --duration 300 --gc-threshold -1 --out /tmp/mqtt_flood
```

`torture.py` only adds iptables rules for loopback traffic on the broker's own free port and removes them in `finally`.
