# Real-hardware handover — the request-body cap on silicon (SPECIFICATION.md Part I.6)

Temporary file, same convention as every handover before it: **delete once its results are
migrated** into `SPECIFICATION.md` Part I.6, `REAL_HARDWARE_TEST_QUEUE.md` §1D and
`HEAP_FRAGMENTATION_MEASUREMENTS.md`. Written 2026-09-19 by a session with **no** real-hardware
go-ahead — every claim below was [SRC] or [MOCK] when written.

> **RUN 2026-09-19 by a session that had the go-ahead. W1-W4 PASS; W5 FAILED and has since been
> rewritten.** Results are in `SPECIFICATION.md` Part I.6 as `[HW]` and in
> `REAL_HARDWARE_TEST_QUEUE.md` §1D. **§4's advance note about W5's soft spot was wrong in its
> premise, and its prescribed fix would not have worked** — the boxed note there records why.
> W5 was then rewritten around the invariant the cap actually owns (queue §2A F10) and replays
> PASS against every recorded run. **This file stays until that rewrite is confirmed on silicon**,
> which is one bench-suite run; everything else it owed is migrated.

**Nothing in this file authorizes anything.** CLAUDE.md's gate stands: the session that runs this
needs the project owner's go-ahead **in its own conversation**. A go-ahead given to the session
that wrote this, or to the 2026-09-18/2026-09-19 bench sittings, does not carry over.
`tests_hardware/README.md` stays the technical reference for prerequisites, flags and safety facts.

It replaces `REAL_HARDWARE_HANDOVER_MEASURE_B.md`, which was **deleted** once §7H migrated every
result it owed — that file's own stated condition for going.

---

## 1. What changed, and why it needs silicon at all

`src/asy_webserver_service.py`, two values:

```python
max_content_length: int = 2048,              # was 4096
Request.max_body_length = max_content_length # was microdot's own 16384 default, never set by us
```

Vendored `ext/microdot.py` has **two** body limits and they were unbound. `Request.create()`
(`:426`) buffers the body into one contiguous `bytes` **before** `handle_request` (`:1400`/`:1410`)
ever calls `dispatch_request()`, which is what answers 413 (`:1443`). So every body between
`max_content_length` and `max_body_length` was allocated in full and then thrown away. With
`max_connections = 4` and a fresh buffer per request, that is **4 x 16384 = 65536 B** of
simultaneous contiguous demand on a 264 KB device whose largest *legitimate* body is 1312 B.

**No patch into microdot.** Both values are set from our own code; the vendoring rule is untouched.

### Why the wire cannot show the whole change — read this before reporting anything

The mock tier proves *"an oversized body is never READ"* directly, by counting the `readexactly()`
sizes the server asks its reader for (`tests/test_asy_webserver_service.py` §F.2b). **That is not
observable over a socket.** Old firmware and new both answer 413 to an oversized body; they differ
only in *which sizes* count as oversized.

So the bench mirrors prove the **cap value moved**. They do **not** prove the binding itself, and a
green run must not be written up as if they did. **W2 is the only row that distinguishes this
firmware from the previous one** — see its own note below.

---

## 2. Prerequisites

1. **One image**, this branch's own tip: `scripts/build_firmware.py dev`, then flash. Never a
   `wozi` build (CLAUDE.md: it "tests nothing at all" and has produced false bugs before).
2. **Real WiFi and a reachable DUT** — this is a bench-tier run, not a flash-tier one. Every row
   goes over the real network stack through `tests_hardware/http_client.py`.
3. **Confirm the cap is what you think it is** before running anything, or W2's verdict is
   meaningless: `GET /status` the board, then check the flashed source really carries 2048. No
   device TOML overrides it (checked: `max_content_length` appears only in
   `src/asy_webserver_service.py`), so the default is what every device gets.

**No wear flags needed.** None of §1D's rows is `@pytest.mark.persistence_write`-marked and none
should become so — see §5.

---

## 3. The run

The five rows live in `tests_hardware/bench/test_network_resilience.py` and ride along with the
ordinary bench suite. No separate invocation:

```
scripts/run_bench_hardware_suite.sh
```

Read the **deselected** count, not just the word "clean" — the wear gates deselect rather than
skip, so "everything that ran, passed" is not "everything ran" (CLAUDE.md).

To run just this section while iterating:

```
scripts/run_bench_hardware_suite.sh -k "body_cap or band_that_used_to_be or largest_body or mixed_stream or concurrent_mixed_body"
```

---

## 4. The five rows, each with what would falsify it

| # | Test | Asserts | A failure means |
| --- | --- | --- | --- |
| W1 | `test_put_body_cap_boundary_is_exact_over_the_normal_network` | 2047 -> 200, 2048 -> 200, 2049 -> 413 | An off-by-one at the cap. microdot compares with `<=`, so **2048 itself must be served**; this is not a tolerance to widen. |
| W2 | `test_put_the_band_that_used_to_be_accepted_is_now_rejected_over_the_normal_network` | 3072 -> 413, 4096 -> 413 | **Most likely the wrong image was flashed.** Under the old 4096 B cap both were accepted. Check the image before touching the code. |
| W3 | `test_the_largest_body_any_schema_can_produce_still_fits_under_the_cap` | 1312 B -> 200, and a maximal `NTP_Host` -> 200 + `"Invalid"` | The regression that actually matters when a cap is *lowered*: something legitimate is now refused. Do **not** respond by raising the cap without re-deriving the schema maximum. |
| W4 | `test_put_a_mixed_stream_of_body_sizes_is_handled_each_on_its_own_merits` | Interleaved sizes, each answered on its own merits | A 413 left the next request mis-parsed on a connection the server closed early — a real connection-handling defect, not a cap one. |
| W5 | `test_concurrent_mixed_body_sizes_are_never_answered_with_the_wrong_status` | 24 threads, mixed sizes, against the real `max_connections = 4`. Asserts that every client **that is answered** is answered correctly; a refusal at the ceiling is counted, not failed. | **This is the one row to re-run.** A wrong status means the cap genuinely mis-answers under concurrency. A *non-ceiling* exception (a timeout above all) is not tolerated and means something hung. "Too few answered" or "never saw both verdicts" means the run was too starved to prove anything — re-run rather than relax. |

> **MEASURED WRONG, 2026-09-19 [HW].** The note below says a red W5 showing exception strings
> *only on the oversized arm* should be relaxed on that arm. On the board **half the resets are on
> bodies well under the cap** (64, 512, 900, 2048 B), in 5 of 5 runs. Two controls settle it: 24
> concurrent PUTs with every body under the cap, and again with all bodies at 64 B, reset at the
> same rate. The resets are **`max_connections = 4` under 24-way concurrency, not the body cap** —
> measured 2 -> 0%, 4 -> 25%, 6 -> 16%, 8 -> 12%, 12 -> 33%, 16 -> 25%, 24 -> 25%, so they begin
> *at* the ceiling rather than beyond it. Relaxing only the oversized arm would leave W5 failing on
> the undersized one. The server stayed responsive, did not reboot, and `WEBSERVER`'s log stayed
> empty, so nothing in `src/` is implicated.
>
> **Resolved 2026-09-19, host-side.** F10's own raw data settles it: across 96 concurrent requests
> **not one was answered with the wrong status** — every failure is a refusal. So the cap held and
> the assertion was wrong, which none of F10's three options addresses. W5 now asserts correctness
> of the answers it gets, tolerating only a *ceiling close*. See queue §2A F10.

### W5's one known soft spot, stated in advance — and measured wrong

W5 asserts every worker got either 200 or 413. A worker may instead report an **exception string**:
an oversized body means the server answers 413 and closes **without draining** the request, so the
client can see `BrokenPipeError`/`ConnectionResetError` once the RP2040's small lwIP receive window
fills. **That is correct server behaviour, not a failure** — but it fails the assertion as written.

**The prescription that followed was wrong, and is kept here only so the mistake is legible**: it
said to relax the oversized arm alone. The reset has nothing to do with body size — it is the
connection ceiling, and it lands on 64 B bodies just as often. The lesson worth carrying forward is
in `tests_hardware/README.md`'s "two traps" section: a test that exceeds `max_connections` must
assert the property its own feature owns, not that every client is served, and an all-small-bodies
control is the two-minute check that tells the two apart.

---

## 5. Why none of this spends a flash cycle, and the one place that was nearly wrong

Every sized body pads an **unknown** sensor key (`HWTESTNoSuchSensor`). `PUT /sensors` ignores an
unknown key silently — the existing `test_put_nonsense_field_values_are_marked_invalid_not_crashed`
already pins that — so nothing validates, nothing persists and no `CFGMGR_*` logger fires. The
body's *size* is the whole subject.

**The near-miss, recorded because it is the kind of thing that repeats.** W3's second half sends a
maximal `NTP_Host`. The first draft sent `"z" * 1024`, which is **valid** per `_VAL_NH`'s own
`3..1024` bound — it would have been accepted and **written to flash**, an unmarked wear cycle in a
test claiming to need none. It now sends **1025** characters: one over the field's bound, so the
handler marks it `Invalid` and nothing is written, while the body is still large enough to prove
the transport cap passes it. If a future edit "fixes" that 1025 back to 1024, it reintroduces a
real flash write.

If one of these ever genuinely needs an *accepted* config write to make its point, that is the
moment to add `@pytest.mark.persistence_write` — not before.

**This is machine-checked, not a promise.** `tests_scripts/test_persistence_write_marker_completeness.py`
caught the `"z" * 1024` draft above on the first run and refused it, which is how the near-miss was
found. W3 is now a named entry in its `_JUSTIFIED_UNMARKED` allowlist, carrying the reason it is
exempt, and the helper `_put_sized` is a named entry in `_JUSTIFIED_UNREADABLE_BODIES` because its
body is built by a call the guard's AST walk cannot read. Both lists are pinned by name, so a
future test cannot inherit either exemption silently.

---

## 6. What to write down

- The pass/fail of each of W1-W5, and for W5 specifically **whether any worker reported an exception
  string rather than a status**, with the string.
- `GET /status`'s `errcount` for `WEBSERVER` before and after. Every row asserts it stays empty: a
  413 is raised inside vendored microdot before any handler or `pr` of ours is reached, so anything
  appearing there is a genuine finding about our own code.
- **Read `errcount` BEFORE any `ResetErrors`** (CLAUDE.md). These tests call `reset_all_error_logs()`
  themselves, so the pre-flight read has to happen before the suite starts, not after.

Then migrate: the results into `SPECIFICATION.md` Part I.6 as a `[HW]` line, the row statuses into
`REAL_HARDWARE_TEST_QUEUE.md` §1D, and **delete this file**.
