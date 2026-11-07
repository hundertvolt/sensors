# Lane B's CLAUDE.md rule ledger (agent, 2026-11-05)

One line per CLAUDE.md rule at c78bbcf1: old line | its first words | where it stands now (line in the rewritten file,
or the pointer target). 'rewritten' keeps the meaning except where the report lists an adopted proposal or a drift.
Counts: kept 40, rewritten 38, pointed 8, vanished 0.

3 | Operating constraints and architecture reference for AI sessions working in this repo. See | rewritten, same meaning unless listed: new line 3: Operating rules and working agreements for AI sessions in this repo, e
10 | Full detail (folder contents, the "read the PDF first" rule, what to do when one's missing | rewritten, same meaning unless listed: new line 10: The datasheets for every chip this codebase drives are the private sub
18 | **The concrete facts** — MicroPython 1.29.0/RP2040 specifics (the legacy units run 1.24.1) | rewritten, same meaning unless listed: new line 19: **The concrete facts** — MicroPython 1.29.0/RP2040 specifics (the lega
27 | Three standing AI-session practices (not facts, kept here since they're instructions, not | rewritten, same meaning unless listed: new line 27: Three standing practices:
30 | - **Always check current MicroPython and Microdot documentation before asserting how an AP | rewritten, same meaning unless listed: new line 29: - **Always check current MicroPython and Microdot documentation before
33 | - **Whenever the owner moves the pinned MicroPython version (owner, 2026-09-26: the pin mo | rewritten, same meaning unless listed: new line 31: - **Whenever the owner moves the pinned MicroPython version (owner, 20
58 | - **Every external dependency is refreshed as one step, not only MicroPython** (owner, 202 | kept: new line 51
70 | - **`improved-quality/` (the refactor's WIP staging directory) has been fully retired and | rewritten, same meaning unless listed: new line 63: - **An owner-authorised exception to a hands-off rule** (owner, 2026-0
86 | - **`src/` is where files land once they're fully reviewed and tested** — formula/logic | rewritten, same meaning unless listed: new line 69: - **`src/` is where files land once they're fully reviewed and tested*
96 | - **Whenever a new file is added to `src/`, run a bird's-eye-view scan over the whole | rewritten, same meaning unless listed: new line 77: - **Whenever a new file is added to `src/`, run a bird's-eye-view scan
109 | - **Do not "fix" `legacy/firmware/modules/_boot.py`'s `import sensortask.py`** (literal `. | kept: new line 91
120 | - **`legacy/firmware/python/CommonDrivers/microdot.py` is vendored third-party code.** Par | rewritten, same meaning unless listed: new line 102: - **`legacy/firmware/python/CommonDrivers/microdot.py` is vendored thi
134 | - **The UART message protocol (`src/asy_uart_comm.py`, promoted) has a second | rewritten, same meaning unless listed: new line 115: - **The UART message protocol (`src/asy_uart_comm.py`) has a second
189 | - **`dev` meets every device's bar**: its generated config is held to the same standard as | rewritten, same meaning unless listed: new line 170: - **`dev` meets every device's bar**: its generated config is held to 
191 | - **WoZi is the exemplary/base variant the whole `src/` promotion is built and validated a | rewritten, same meaning unless listed: new line 172: - **A device's result counts only from its own build on its own hardwa
206 | - **The legacy tree is reference-only, forever — it never gets work of any kind** (owner, | kept: new line 182
226 | - **Don't touch `sensors/config.json`-equivalent files or commit any real credentials.** A | kept: new line 199
237 | - **A wedged I2C bus or sensor recovers through the recovery ladder, smallest blast radius | kept: new line 207
243 | - **The same backstop applies to a WiFi link stuck in a CYW43-firmware-level `isconnected( | rewritten, same meaning unless listed: new line 213: - **The same backstop applies to a WiFi link stuck in a CYW43-firmware
250 | - **`MemoryError` handling follows one criterion** — a function with a true graceful-degra | kept: new line 230
259 | - **Adafruit-derived driver code is fair game to restructure/rewrite** (keeping attributio | kept: new line 239
263 | - **Long-blocking operations must not stall timing-sensitive work** — standing design prin | kept: new line 243
266 | - **Boot latency is not a metric to optimise for its own sake** (owner, 2026-09-16, the ow | kept: new line 246
276 | - **`asy_uart_driver.py` and `asy_uart_comm.py` may never block the asyncio loop — not eve | kept: new line 256
294 | - **A new device on a shared resource — an I2C/SPI bus and every other shared resource (lo | rewritten, same meaning unless listed: new line 274: - **A new device on a shared resource — an I2C/SPI bus and every other
308 | - **Least wear in the production code: the central wear rule, ahead of the test rule below | kept: new line 282
323 | - **No test may inflict avoidable wear on real hardware — the host's own SSD included, not | kept: new line 297
368 | - **A session needs the project owner's go-ahead, given directly in that session's own | kept: new line 337
380 | - **A destructive test of the bench host's own network/access config (tearing down `br0`/i | rewritten, same meaning unless listed: new line 349: - **A destructive test of the bench host's own network/access config (
389 | - **The bench Pi4's `br0` bridge must always present `eth0`'s own real hardware MAC, never | rewritten, same meaning unless listed: new line 358: - **The bench Pi4's `br0` bridge must always present `eth0`'s own real
395 | - **Memory-safety discipline: design for zero `MemoryError`s first, catch→degrade→restart→ | kept: new line 364
478 | - **When investigating any unexpected real-hardware error or reset — read the FRAM-persist | rewritten, same meaning unless listed: new line 447: - **When investigating any unexpected real-hardware error or reset — r
508 | - Long-term goal: fully understand the current (production) system in detail, then check w | kept: new line 468
513 | - When a fact in this file or BACKLOG.md turns out to be stale (version drift, changed ups | rewritten, same meaning unless listed: new line 473: - **Change classes** (owner, 2026-09-25). A consistency discrepancy — 
516 | - **Documentation contains current state, future targets, and rules/agreements — not the h | rewritten, same meaning unless listed: new line 484: - **Documentation contains current state, future targets, and rules/ag
524 | - **Decision records (owner, 2026-09-26: the five prevention rules, answered '4. yes')**:  | kept: new line 494
539 | - **Every module gets exactly one header comment block — module/function/class `"""..."""` | rewritten, same meaning unless listed: new line 509: - **Every file opens with exactly one header comment block, and every 
584 | - When changing a sensor driver's behavior, verify against the legacy driver's own actuall | rewritten, same meaning unless listed: new line 547: - **Legacy parity means no lost function.** When `src/` or generated c
586 | - **Workflow for substantial work** (owner, 2026-09-26: 'superseded by the workflow descri | kept: new line 561
604 | - **Work split across subagents: small blocks, fresh agents** (owner, 2026-10-20). The que | kept: new line 601
622 | - **Config lives in root `pyproject.toml`** (ruff/mypy/pytest/uv, dev-tooling only — the s | kept: new line 619
633 | - **Wired into CI** via `.github/workflows/ci.yml` (GitHub Actions). **Each tool is its ow | rewritten, same meaning unless listed: new line 630: - **Wired into CI** via `.github/workflows/ci.yml` (GitHub Actions). *
646 | - **`zizmor` audits the GitHub Actions workflows themselves** — `GITHUB_TOKEN` scope, chec | kept: new line 643
659 | - **Scope is eight directories**: `src/`, `tests/`, `digital_twin/`, `buildgen/` (the | kept: new line 656
699 | - **Unit tests run under a real MicroPython Unix-port interpreter, not pytest/CPython** —  | kept: new line 693
727 | - **`scripts/test.sh --coverage` reports `src/` line coverage; it never gates anything** — | rewritten, same meaning unless listed: new line 721: - **`scripts/test.sh --coverage` reports line coverage and never gates
762 | - **A third party's momentary outage must never read as a red test result** (owner, 2026-0 | kept: new line 748
770 | - **Standing backstop: hanging tests are never allowed.** `scripts/test.sh`/`ci.yml` enfor | kept: new line 756
790 | - **Known hang cause, fixed**: a real `select.poll()` asks each registered stream object f | rewritten, same meaning unless listed: new line 774: - **Known hang cause: any test double for `uart.poller`, or an equival
803 | - **Known hang cause #2, fixed**: a digital-twin integration test that drives the real | rewritten, same meaning unless listed: new line 784: - **Known hang cause #2: `tests/microtest.py`'s `run()` always ends wi
831 | - **Known segfault cause, fixed**: a **nested `asyncio.run()` while any other task is stil | rewritten, same meaning unless listed: new line 792: - **Known segfault cause: a nested `asyncio.run()` while any other tas
853 | - **Known intermittent-`MemoryError` cause #2, fixed**: a real SIGINT landing inside a | rewritten, same meaning unless listed: new line 812: - **Known intermittent-`MemoryError` cause #2: don't re-diagnose a "he
867 | - **Known intermittent `digital-twin-e2e` shutdown flake, fixed**: a SIGINT-triggered shut | rewritten, same meaning unless listed: new line 821: - **Known intermittent `digital-twin-e2e` shutdown flake: don't re-dia
882 | - **Known intermittent-`MemoryError` cause, fixed**: `scripts/test.sh` runs every `tests/t | rewritten, same meaning unless listed: new line 832: - **Known intermittent-`MemoryError` cause: every test file runs with 
896 | - **Local test runs pin `$TZ=UTC` (Unix port only).** The Unix port's `time.mktime()` | kept: new line 841
905 | - **Two suites that both bind real ports must never run at the same time.** `scripts/test. | kept: new line 850
929 | - **Tuned values carry `@tunable` and a Part N row, both changed in the same change** (own | kept: new line 872
931 | - **`ruff format` is not used anywhere** (agent, 2026-07-13) — line breaks are hand-chosen | kept: new line 874
938 | - **Bare `except:` (E722) stays enabled** (owner, 2026-07-13, `c0dfd20`, paraphrase: flag  | kept: new line 881
941 | - **Union type annotations: always PEP 604 `X | Y` (and `X | None`), never `typing.Union[. | rewritten, same meaning unless listed: new line 886: interpreter: an unquoted, executed `int | None` works with no import n
954 | - **mypy runs full `--strict`, minus exactly one flag.** All three configs set `strict = t | rewritten, same meaning unless listed: new line 894: (spelled that way, not as the individual flags, so a deliberate mypy v
966 | - **`method-assign` stays globally enabled, and `src/` must never suppress it** (owner, | kept: new line 907
976 | - **`# noqa: E402` belongs only on files with a real statement before their imports.** Sev | kept: new line 917
984 | - **A merge resolved by taking one side wholesale hides test/source mismatches — run every | kept: new line 925
987 | - **A merge that touches `uv.lock` can silently bypass the tool pins — always re-verify af | kept: new line 928
1003 | - **MicroPython stubs**: `micropython-rp2-rpi_pico_w-stubs` (PyPI, board/version-specific, | kept: new line 941
1023 | - **`scripts/typecheck.sh`'s combined `mypy src tests` run resolves every `from machine im | rewritten, same meaning unless listed: new line 963: `call-overload` errors at every bare `Timer()`, which is valid on rp2 
1034 | - **The `I2C.deinit()` half of this note was backwards and has been corrected** (audited a | rewritten, same meaning unless listed: new line 963: `call-overload` errors at every bare `Timer()`, which is valid on rp2 
1043 | - **`scripts/typecheck.sh` repairs two verified defects in the MicroPython stub package af | rewritten, same meaning unless listed: new line 971: conditional on the
1058 | - **`improved-quality/microdot.py` no longer exists** — it was a confirmed *unintentional* | pointed: ext/microdot.py's vendoring hard rule (its current fact); the deleted fork is history
1064 | **Owner decision, 2026-09-18: this is a periodic check the project owner runs manually, no | rewritten, same meaning unless listed: new line 982: covers. The verification is a periodic check the owner runs by hand, n
1073 | For any change to `pyproject.toml`, `scripts/`, `toolchain/versions.toml`, or | rewritten, same meaning unless listed: new line 982: covers. The verification is a periodic check the owner runs by hand, n
1086 | **Recipe** (needs root; mirrors how `toolchain/setup_toolchain.py`'s own "verified from sc | pointed: README.md, Build-environment verification (the recipe)
1185 | **The trixie target, and why noble alone is not enough.** The noble chroot above pins GCC  | pointed: README.md, Build-environment verification (the trixie target and its reason)
1194 | Everything in the recipe above is identical for trixie except the `debootstrap` invocation | pointed: README.md, Build-environment verification (the two lines that differ)
1208 | Two practical notes. `debootstrap` needs a script for the suite it is asked to build, so a | pointed: README.md, Build-environment verification (debootstrap script, gcc check)
1215 | The trixie leg was last satisfied on 2026-09-12 by a real `--variant=minbase` trixie chroo | pointed: BACKLOG.md, the chroot entry's head (when the legs were last satisfied)
1221 | **What counts as passing**: `lint.sh`/`typecheck.sh`/`scripts/test.sh` all run to completi | pointed: README.md, Build-environment verification (what counts as passing)
1232 | **Changes to `toolchain/setup_toolchain.py` or `toolchain/versions.toml` itself need a sec | pointed: README.md, Build-environment verification (the installer leg); CLAUDE.md keeps the rule
1244 | - **When pushing anything touching the dev-tooling/build-environment setup** (`pyproject.t | rewritten, same meaning unless listed: new line 995: - **The project owner has explicitly authorized creating pull requests
1249 | - **The project owner has explicitly authorized creating pull requests proactively, at any | kept: new line 995
1253 | - **Always create a pull request with a meaningful description** when finishing work on a  | kept: new line 999
1255 | - **A branch counts green only when CI ran on its head commit** (agent, 2026-09-18): read  | kept: new line 1001
1258 | - **Automatically subscribe to the pull request's activity** (review comments, CI results) | kept: new line 1004
1263 | **Moved to `SPECIFICATION.md`.** The condensed version is Part A.2 ("Architecture at a gla | kept: new line 1012
1271 | **Moved to `SPECIFICATION.md` Part A.5.** Covers what Microdot's own `ext/microdot.py` (ve | kept: new line 1020
