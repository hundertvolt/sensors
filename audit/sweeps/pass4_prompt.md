# Pass 4 — brief for the scan agents (2026-09-29)

Common part for every scan; your TASK follows in the prompt that launched you (and in section "Tasks" below).

You are scan agent SCAN of CONSOLIDATION PASS 4 in the whole-project audit of the `sensors` repo at
/home/user/sensors (branch `claude/whole-project-audit-plan`, HEAD as given in your prompt). Audit execution is
BLOCKED: you change nothing except your single output file OUT = /home/user/sensors/audit/pass4/SCAN.md. Append to
OUT as you go so partial work survives.

Why: the owner's goal is a true release with no leftovers (OR5) and no foreseeable question left for execution
(OR2.a/b, OR52.a (5)). Pass 4 closes what pass 3 left uncovered, adds the counter inventory (OR105.a (4)), and
checks against fetched primary sources what could not be checked offline (OR108.a (3)). After pass 4 the register
becomes an action list (phase A-L), so every verdict must be precise enough to turn into a concrete change.

**Accuracy before speed (owner, 2026-09-29, OR107.a).** Never cut a check short, sample down, or judge by score
where reading is possible, unless your TASK explicitly defines a sample. If your input is larger than you can read
properly, say so in Coverage rather than filtering silently.

Read first: CLAUDE.md; audit/CONSOLIDATION.md (sections 1, 2, 3, 5, 9); PROJECT_AUDIT_PLAN.md section 3.2 (owner
rows OR1-OR108, each a quote row plus an ".a" reading; the most recent owner decision wins); audit/pass2/INDEX.md
and the register blocks your items land near (audit/pass2/G1.md-G10.md, LEAD.md, REF.md; block form `### Gn/Rnn`
with Req, Sources, Rank, State, Home, Pillar, Pass 2 lines); audit/pass3/SUMMARY.md and the pass-3 file your task
continues. Dedup against the register, audit/pass3/*.md, audit/refined/FINDINGS.md (RF001-RF354), audit/harvest/,
audit/hreq/, audit/DECISION_PROVENANCE.md and the plan's section 5 topics/seeds before recording.

Constraints (binding): read-only on the repo; git read-only (log, show, blame, diff, log -S/-G); no tests, builds,
uv, npm, mpremote, port binding. Network only where your TASK allows it, and then read-only (git fetch into the
scratchpad, WebFetch of public pages). Never read `arduino/`. `ext/` only for Microdot semantics. The legacy tree
(`python/`, `modules/`, `build-*.sh`, `dev_legacy/` old driver copies; `html_raw/` for UI parity) is
reference-only: an oracle for field-proven behaviour, never a finding target. Scratch dir for ad-hoc `python3`
scripts: /tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/pass4/SCAN/ (create
it). Primary sources under /tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/:
MicroPython v1.29.0 `mp/`, v1.28.0 `mp128/`, lwIP at MicroPython's pinned `77dcd25` `lwip/`, cyw43-driver
`cyw43/`, datasheet text `dstxt/` (also `txt_*.txt`), Microdot `microdot/`. Generated modules: read them through
`buildgen/codegen.py`'s templates (do not build). Never declare a defect or a fact from memory: open the site, the
datasheet page or the pinned source and cite it. Quote owner words exactly, keep qualifiers, never call something
the owner's without an owner source (OR64: a missing owner trace never proves the owner did not decide), date
every "decided". Self-resolve before asking (OR51.a (3)).

OUTPUT (OUT, markdown):
```
# Pass 4 SCAN — <title> (HEAD <sha>)
## Items
- SCAN.nn | <item ID or file:line or commit> | <VERDICT> | <evidence: file:line, commit, source file+line, URL> | <one line: why> | register: <req ID, or "new req: <one-line req>"> | owner: y/n
## Coverage
| input set | items | per verdict counts | not covered (why) |
## Proposed owner questions
<numbered; each: a top-level decision in max 10 words; then the options, each with its consequence; cite the SCAN.nn lines it settles>
## Register lines
<for each item that settles into the register without the owner: the register block ID and the exact line to add or change>
```
Be exhaustive over your input set: every item gets a line (a large identical class may be one aggregate line with
count and full ID list). FINAL REPLY (max 150 words): per verdict counts, the proposed owner questions as one line
each, anything not covered and why.

## Tasks

**K — counter inventory (OR103.a, OR105.a, LEAD/R24).** Find every counter candidate in `src/`,
`buildgen/codegen.py` templates, `digital_twin/` and `js/`: any value that grows with time or events (`+= 1`,
`+ 1` assignments, `increment()`, `LockedCounter`/`LockedValue` users, uptime/age/elapsed seconds, error/retry/
transfer/failure/connection counts, sequence numbers, accumulated sums and averages, `ticks`-derived stored
values). Use an AST pass plus reading; list every hit. Per candidate: site, what it counts, its realistic highest
rate, its current cap (or none), its storage and wire width (FRAM field, struct format, JSON, `@web` type), and the
allocation check of OR105.a (3): does any step, cap constant or intermediate exceed `MP_SMALL_INT_MAX` = 2**30 − 1
on rp2 (`mp/py/smallint.h`), and is the step `min(v + 1, CAP)`-shaped. Verdicts: OK (capped, allocation-free,
check-before-step) · UNBOUNDED · ALLOCATES · WRONG-FORM · NARROW (width below the shared cap, needs its own named
cap) · NOT-A-COUNTER (wrap-by-design per G5/R10: `ticks_ms()`, CRCs, protocol sequence/id bytes — say why). Also
list counters in `tests/`, `tests_hardware/device_scripts/` and host code as a separate, lower-priority set
(OR103.a: "test and host code follow it where a counter lives"). Every non-OK line names LEAD/R24 plus the unit.
No network.

**H — history remainder (pass 3 H1 and H2 limits).** (1) The ~145 BACKLOG "fixed … per owner request"
narratives H1's forward pass filtered by vocabulary instead of reading (`audit/pass3/H1.md` Coverage, row
"Deleted/predecessor docs"; H1's scratch `scratchpad/pass3/H1/lostfwd_*.json`, `lostfwd_rem.json`): read each one
and decide whether it carries a standing owner decision with no HEAD descendant (DRIFT / LOST) or is history
(PRUNED-OK). (2) Comments in `scripts/`, `toolchain/`, `devices/`, `.github/`, the config files (`pyproject.toml`,
`*.ini`, `eslint.config.js`, `vitest.config.js`, `package.json`) and `html/`: the reason-dropped/reason-swapped
chain trace H1 ran over code comments (H1's scripts `chain.py`, `cmreason.py`), verdicts as in H1. (3) The 76
decision commits H2 excluded because the provenance files cite them (`scratchpad/pass3/H2/rows.txt`, lines marked
`|DP|`): H2 found that a citation does not prove every decision in the commit was traced (`ee5310c`, `8d77994`,
`7c8dbbc`); re-trace each of the 76 the way H2 did (message in full, every added "owner" line of the diff outside
`audit/`, the plan, legacy and `arduino/`), verdicts as in H2. No network.

**F — fetched-source checks (OR108.a (3)).** Network allowed, read-only. (1) Every claim that something is
"unchanged", "byte-identical" or otherwise compared between MicroPython v1.28.0 and v1.29.0 (SPEC F.5, CLAUDE.md
"Last run", the register, BACKLOG): check it by diffing `mp128/` against `mp/`. (2) Every claim about an upstream
issue, PR, release or tracker state (MicroPython, cyw43-driver, lwIP, Microdot, the stub packages, actionlint,
zizmor, dorny/paths-filter, codecov, pico-sdk): open the cited page with WebFetch (or `git ls-remote`/`git fetch`
into the scratchpad) and record what it says today. (3) NET.S19: does lwIP 2.2.1 at `77dcd25` drop a UDP datagram
whose source address or port differs from a connected PCB's remote (`lwip/src/core/udp.c` `udp_input()`), and does
MicroPython's socket layer at v1.29.0 (`mp/extmod/modlwip.c`) connect the PCB for this code's use
(`src/asy_udp_socket.py`, `src/asy_ntp_client.py:183-184`, `src/asy_dns_client.py`)? (4) CI.S11: dorny/paths-filter
at the SHA pinned in `.github/workflows/ci.yml:35`: which base does it compare against on a `push` event, and can a
cancelled run make a later push skip the web tier permanently (`ci.yml:13-15`, `:38-41`)? Fetch the action's source
at that SHA. (5) Every deferral whose trigger lies outside the sandbox (pass 3 O.md Coverage row 4 names actionlint,
the mbedtls submodule and Microdot hints; find the rest with the same method): check the trigger's current state.
Verdicts: HOLDS · WRONG (with the corrected fact) · TRIGGER-MET · TRIGGER-NOT-MET · UNREACHABLE (page not
fetchable; say which).

**R — reference sample and one test file.** (1) Pass 3 C1 judged 675 identifier-free SPECIFICATION Part references
with ≥ 1/3 word overlap by score, without reading them (`audit/pass3/C1.md` Coverage row "S03 RP04.c"; C1's scripts
in `scratchpad/pass3/C1/`, e.g. `docsec.py`). Rebuild that set exactly, then read a seeded random sample of 150,
stratified by source file: each reference against its target section's text at HEAD. Verdicts: RIGHT · WRONG-SECTION
(name the right one) · STALE (the content is gone) · AMBIGUOUS. If the sample holds 3 or more non-RIGHT verdicts,
read the whole of every stratum in which one occurred. (2) `tests/test_bus_hazard_multi_device.py`: a verdict per
test function under G2/R17 (keep, naming the property it guards; adapt; move; retire with the guard named) and
against CLAUDE.md's four-tier bus-hazard rule (which tier covers each hazard class, gaps). The file stays (B05). No
network.
