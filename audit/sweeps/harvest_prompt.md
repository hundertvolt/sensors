You are one of 17 parallel read-only "harvest" agents in the PLANNING phase of a whole-project audit of the `sensors` repo (MicroPython 1.29 firmware for Raspberry Pi Pico W sensor units, plus its host build chain, digital twin, website and test tiers). Audit execution is BLOCKED. You do not audit, verify in depth, or propose fixes. Your only job is to RECORD, exhaustively, every item that the project's own comments, docstrings and docs (in your partition) state and that an auditor must not miss. The project owner's words: "recording all you find and all which is noted in comments and docs is sufficient, and it's more important not to miss anything there."

SNAPSHOT. Read ONLY from W=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/wt (a detached worktree at commit 2a88cc8), never from /home/user/sensors. Cite `path:line` relative to the repo root at that commit.

HARD CONSTRAINTS. Read-only: do not modify, create or delete anything except your single output file OUT. Do not run tests, builds, uv, npm, mpremote, or anything that binds ports or touches hardware or the network (the git-history agent's GitHub reads are the only exception). No git command that writes (checkout, stash, worktree, fetch, gc, ...). Never read or record anything under `arduino/`: it is out of scope, and that is settled. `ext/` is vendored upstream code that is never edited.

HELPERS. `cd W && python3 /tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/harvest/extract_comments.py <repo-relative files...>` prints every comment and docstring line as `path:line: text`. Your file list is in `.../scratchpad/harvest/lists/<ID>.txt` where one exists.

WHAT TO RECORD, by KIND:
- TODO: to-do, deferred work, follow-up, "not yet", "for now", "temporary", "until X", future work.
- LIMIT: a known limitation, gap or unhandled case; "does not handle/cover/model/test"; best effort; an approximation; a degraded mode; a fidelity gap of a fake, mock or twin.
- RISK: an accepted or tolerated risk or behavior ("acceptable because", "rare", "benign", "harmless").
- SETTLED: an owner decision, or a "don't change / don't re-propose / by design / deliberate" statement. It is recorded so the audit can check it is still accurate; it is never reopened.
- ASSUME: a stated assumption or an unverified or inferred claim ("assumes", "should", "expected", "believed", "presumably", "inferred", "unverified", "never happens"). Also any number from a single, dated measurement.
- WORKAROUND: a workaround for an external, upstream, toolchain, stub, hardware or browser defect. Give its removal trigger if one is stated, else "none stated".
- INVAR: an invariant or contract upheld only by convention or caller discipline, not enforced mechanically ("must", "must not", "never", "caller must", "only safe because", "keep in sync with"). If something does enforce it (a test, lint or script), name it.
- MIRROR: a stated duplicate or mirror obligation between two places (src↔js, code↔doc, Python↔C, fake↔real, a copied constant). Record both ends.
- SUPPRESS: every lint, type or test suppression or gate: `# noqa`, `# type: ignore[...]`, `pragma: no cover`, `eslint-disable`, `@ts-ignore`/`@ts-expect-error`, `# shellcheck disable`, pytest skip/skipif/xfail/deselect and gating markers, `continue-on-error`, disabled audits or rules, ruff/mypy ignore or override entries, `|| true`, and exceptions swallowed with a comment. For a high-volume identical class (e.g. `type: ignore[method-assign]` in tests) record ONE aggregate item with the count and the file list. In shipped code (src/, js/, html/) record every site.
- PLATFORM: a platform, runtime, chip or datasheet fact the code depends on that is specific to a version or to silicon, and so needs re-checking when versions move.
- OPENQ: an open question; "undecided", "unclear", "TBD", "owner to decide", "investigate".
- DRIFT (noticed incidentally): a comment or doc that seems to contradict the code or another doc; a stale count, date, name or path; a dangling reference ("see X" where X doesn't exist); a retired ID. Cite both sides; don't investigate in depth.
EXCLUDE plain descriptions of what the code does, and rationale that flags no gap, limit, risk, assumption or obligation. When in doubt, INCLUDE the item and append `(low)`.

METHOD (be exhaustive):
1. Read EVERY comment and docstring line of EVERY file in your partition: run the helper and read the whole dump, not a keyword grep of it. For .md/.txt docs, read the full text in chunks.
2. Also grep your files for suppression syntax and these keyword families, to catch what the dump misses (e.g. log and error message strings, code-level skips): TODO|FIXME|XXX|HACK|later|for now|temporar|until|not yet|workaround|limitation|known|caveat|best.effort|approximat|assum|should|expect|unverified|inferred|never|must|only safe|accept|tolerat|deliberate|by design|settled|owner|skip|xfail|deselect|noqa|type: ignore|pragma|disable|flaky|race|wrap|overflow.
3. Open the surrounding code only as far as needed to state the item correctly in one sentence.
4. Dedup against the existing plan. `W/PROJECT_AUDIT_PLAN.md` already has about 345 topics (`<AREA>.Tnn`) and 306 unverified seeds (`<AREA>.Snn`), and its §5.0 maps every file to one owning area. For each item, grep the plan for the file path and a distinctive keyword. If a topic or seed clearly covers the same point, set `covered-by: <ID>`; if it overlaps partly, `related: <ID>`; otherwise `-`. Record the item in every case.

AREA CODES (take the file's owner from plan §5.0; for doc statements, use the area the statement is about): XCUT cross-cutting, CORE (system_service/config/logging/locks), ALGO (math/VOC), BUS (I2C/SPI), SENS (sensor drivers), STOR (FRAM), UART, NET (wifi/ntp/dns/udp), REST (webserver/Microdot use), LED (neopixel/notification), GEN (buildgen), TOOL (toolchain), SCR (scripts), CI, WEB (js/html/css), TEST (unit/mock tier), TWIN (digital twin), HW (real-hardware tests/bench), SEC, MEM, PERF, PLAT (platform facts), PAR (legacy parity), DOC, LIC.

OUTPUT. Write ONE markdown file OUT, appending per file as you go so partial work survives:
```
# Harvest <ID> — <partition> (snapshot 2a88cc8)
## <path>
- KIND | path:line[-line] | "short verbatim quote (<= ~20 words)" | what it declares / why an auditor must know it (one sentence) | area: XXX | covered-by: ID  (or related: ID, or -)
## Coverage
| file | comment/doc lines read | items |      <- EVERY file of the partition; 0 items is allowed
## Totals per kind
## Top 10          <- by reference to your own items: the ones you judge most important for the audit
```
No solutions, no fix proposals, no severities. Quote precisely and check your line numbers. Final reply to the orchestrator: at most 150 words, with totals, files covered, anything you could not read, and your Top 10 anchors.
