# U35 blocks Z, M and O: the single config write and two product cleanups (lead, 2026-10-22)

Read `S/CHECKLIST.md`, then from `S/u35/briefs/common_u35.md` only the sections Rules, Hand-back and Same-device runs
(your work is not step-based: skip Reading and Sites), then your block. About 60-80 tool calls: past 80, commit what is
done and hand back the rest (CHECKLIST 21). CHECKLIST 22 (disk) and 23 (load) are binding. Batch independent calls.

## All three blocks
- Base: the integration head `6dabd9b`. Your branch `audit/u35-<l>`, worktree `S/wt-u35<l>`
  (`git -C /home/user/sensors worktree add -b audit/u35-<l> S/wt-u35<l> 6dabd9b`), then `S/u23/rebuild.sh S/wt-u35<l>`.
  Logs in `S/u35/lane<L>/`. Commit subject `U35 lane <L>: <summary>`. Decision tags read "(agent, 2026-10-22)".
- The owner's go-ahead and its condition (owner, 2026-10-22): "the cleanups are fine as well, as long as their intended
  behavior and resilience are either unaffected or even improved. Be sure not to intruduce a regression."
- The regression bar, binding for every part:
  - every test that passes at `6dabd9b` still passes, at -1 and 32768;
  - no existing test's asserted outcome changes, except a Z test of the removed mechanism itself;
  - nothing in the part adds a write to the flash filesystem or the SCD30's NVM, an await on a previously
    await-free path, a task, or a held allocation.
  A part that cannot meet the bar is stopped and left as it was, with its reason in the hand-back. That is a valid
  outcome, not a failure.
- Stopped parts and anything outside your files go in the hand-back. SPECIFICATION.md and CLAUDE.md are not yours: a
  sentence there that your change makes stale goes in the hand-back with its line (a later doc block writes it).
- Expected reds, not yours: `tests_scripts/test_twin_record.py` (any `src/` change); for Z also
  `tests_scripts/test_tunables_register.py` (Part N's `config.flush_slice_bytes` row left without its tag).

## Z: the config write back to one direct write
The owner's decision (owner, 2026-10-22, on the lead's proposed next steps: "For your records, your suggested next steps
are fine (go back to the single write)."), and on "Keep lane P's one separable change: the boot write now holds the
config lock, so a Reset to defaults waits for it (no extra write)?": "1. is good.". This removes writes; it is the
owner's decided change, so CHECKLIST 24's stop does not apply to it.
Files: `src/asy_config_manager.py`, `tests/test_asy_config_manager.py`, `tests/_littlefs_fake.py`,
`tests/_sensortask_scenarios.py`, and `buildgen/error_catalog.json` only if a removed log site orphans an entry.
1. `git log f3fff0e..6dabd9b -- src/asy_config_manager.py` shows four lane P commits (`934539c`, `b52f3b6`, `8f2f15f`,
   `65f7454`) and K1's comment refit (`af38779`). Return both write sites, `_flush_staged()` and `setup()`'s boot
   write, to `f3fff0e`'s form: `with open(self._config_file, "w") as f:` then `f.write(text)` then
   `self.unpersisted = False`, with `f3fff0e`'s failure handling.
   - Out: `_write_text()`, `_finish_write()`, `_remove_sibling()`, `_TMP_SUFFIX`, `_FLUSH_SLICE_BYTES` and its `@tunable`
     tag, and `delete_file()`'s sibling cleanup.
   - Kept: the boot write under `async with self._config_lock`, and K1's refit of every comment that survives.
2. The tests of the removed mechanism return to `f3fff0e`'s shape. `tests/_littlefs_fake.py` keeps only what a kept test
   uses (its commit-at-close model, if a test pins that a failure before the close leaves the old document); a part
   nothing uses goes. `tests/_sensortask_scenarios.py`: only its uses of the removed names.
3. Pins, with an `open`/`os` call recorder (the TmpScratch pattern CLAUDE.md describes), counting operations on the
   config file:
   - a PUT that changes a value: exactly one `open(<config file>, "w")` and its close, no other filesystem call;
   - a PUT that changes nothing: none;
   - a boot with a valid file: no write; a boot with a missing file: one write;
   - Reset to defaults: one `os.remove` per store's file.
   An existing test that already pins one of these counts; say which. Each new pin is bitten once in a scratch copy
   (for example a second `open` planted in `_flush_staged()`).
4. Checks: the file's tests and `tests/test_sensortask_*.py` at both stages, mpy-cross, and every `tests_scripts` reader
   of a changed file (grep its name), at least `test_buildgen_error_contract.py` and
   `test_generate_sensortask_modules.py`. Hand-back: the SPECIFICATION.md sentences describing the slices, the sibling
   file or the rename (A.4, C.7.3, F.3 `stall.flash_program`, J.6, Part N), with their lines.

## M: the shutdown gate without its lock, and a supervisor that returns
Files: `src/asy_system_service.py`, `tests/test_asy_system_service.py`. Not `tests/_sensortask_scenarios.py` (Z's).
1. The command gate in `_request_shutdown()` holds an `asyncio.Lock` around a tentative claim with two rollbacks and a
   `_reset_armed` re-check. If its only await is `erase_ready()`, do that await first, then check and claim with no
   await in between: cooperative scheduling makes that atomic. The Lock, the tentative claim and the rollbacks go,
   along with anything they alone made reachable.
   - Proof: every existing gate test passes unchanged.
   - A new test, seen biting a planted await between the check and the claim in a scratch copy, pins that two commands
     arriving together get one acceptance.
2. `_shutdown_sequence()` waits for the supervisor to park on an Event and then cancels it. The supervisor returns once
   it has set that Event instead, and the sequence confirms with `task.done()`. Same proof bar.
   - Check first: nothing restarts the supervisor, and every path after the Event ends in the reset.
   - The boot-time case stays covered (a command arriving before the supervisor exists).
3. Kept by the lead's decision:
   - `_shutdown_task`: tests in four files read it, and removing it costs more than its one reference;
   - the `if loop.get_exception_handler() is None:` guard: `tests_scripts/test_exception_handler_contract.py` and the
     device scripts depend on that contract;
   - the Event, the task, and `_shutdown`/`_feed_owned` as separate fields unless merging them changes no test.
4. Checks: the file's tests, `tests/test_asy_webserver_service.py`, `tests/test_digital_twin_timer_pool.py` and
   `tests/test_sensortask_*.py` at both stages, mpy-cross, and the `tests_scripts` readers of the file (grep
   `asy_system_service`), at least `test_memory_catalog.py`, `test_exception_handler_contract.py` and
   `test_task_inventory.py`.

## O: the captive DNS's Unix-port branch out of the product, and the hazard run's website text
Files: `src/asy_captive_dns.py`, `tests/test_asy_captive_dns.py`, `digital_twin/unixport/_unix_port_udp_addr_shim.py`,
`buildgen/definitions.py`, `tests/test_digital_twin_uart_link.py`, and the readers of the changed definition text.
1. `CaptiveDNS.run()` wraps `ipv4_to_int(addr[0])` in a `try` for an int address. Its comment says the address "can
   come back as a plain int", which only the Unix port produces.
   - Establish with the source: on rp2 `recvfrom` gives a str (`/root/pico-toolchain/micropython`, extmod/modlwip.c),
     and `ipv4_to_int` on any str returns a value or None without raising, MemoryError aside.
   - If every Unix-port path that runs `CaptiveDNS` gets str addresses through the existing shim, or does after a
     change in the shim alone, the product `try` and its comment go.
   - Whatever happened to a malformed or off-subnet sender before still happens.
   - If not, the `try` stays; report why.
2. Kept by the lead's decision: the MemoryError re-raise in `run()` and `DNSQuery`. Narrowing `DNSQuery`'s handler would
   let an unexpected exception type from one bad datagram pause the server for 3 s, which is a resilience loss.
3. `buildgen/definitions.py`'s `UartHazards` description ends "Bench-only; nothing is stored." The request is indeed
   never stored, but a hazard run's provoked faults are logged.
   - First establish in the twin, as a new assertion in `tests/test_digital_twin_uart_link.py`, whether a run leaves
     entries in the FRAM-backed `UART_init`/`UART_resp` error logs. The assertion is seen failing first (for example
     against an expectation of no entries).
   - Then the description says exactly what holds, in one short sentence, for example "Bench-only: the request is not
     stored; the faults the run provokes appear in both UART error logs."
   - Update its readers (grep the old text) with the repo's own generation tooling, never by hand.
4. Effects: captive DNS runs only in AP mode; the text is dev's website only. Checks: the changed files' tests at both
   stages, `tests/test_digital_twin_sensortask_integration.py`, the `tests_scripts` readers (grep `definitions` and
   `captive_dns`), and `npm test` if a web-tier file reads the text; every port-binding run inside
`unshare -n S/u24/ns_xdg.sh`, as the common Rules say.

## J: the firmware's write sites pinned, the UART link kept to dev, the SCD30 write counts (after Z merges)
Base: the integration head the lead names when starting you (Z merged). Same rules as above; files: two new files
`tests_scripts/test_firmware_write_sites.py` and `tests_scripts/test_uart_link_bench_only.py`, and
`tests/test_asy_scd30_driver.py`.
1. `test_firmware_write_sites.py`: an AST scan of `src/*.py` and of every device's generated modules (generate them in
   process through `buildgen.generate.generate_device` for each `devices/*.toml`, writing nothing), listing every
   limited-endurance write:
   - `open()` in a mode holding w, a, x or +, or a non-literal mode;
   - `os`/`uos` `remove`, `rename`, `mkdir`, `rmdir`, `unlink`, `mount`, `umount`; any `mkfs` or `Vfs*`;
     `writeblocks`; `rp2.Flash`;
   - a call whose name holds "send" or "write" carrying an SCD30 command that stores in NVM: 0x0010, 0x0104, 0x4600,
     0x5306, 0x5204, 0x5403, 0x5102 (the Interface Description's "saved in non-volatile memory" commands; 0x0104 changes
     the saved measurement status).
   Each site is pinned by (file, function, construct) with its trigger and why it is needed, in one table at the top of
   the test. A new, moved or vanished site fails, naming file:line, with a message that the owner decides any change
   (owner, 2026-10-22: "a condition strictly to be avoided by rule and nothing you were allowed to decide without even
   asking"). Seen failing first in a scratch copy: a planted `open(..., "w")`, a planted `os.rename()`, a planted SCD30
   `_send_command(_CMD_SET_ALTITUDE_COMPENSATION, ...)`; a planted `open(p)` and `open(p, "rb")` stay unflagged.
   The lead's inventory (`S/screen/inventory.py`, proven on these plants) is a reference, not a dependency.
2. `test_uart_link_bench_only.py`: every `devices/*.toml` declaring `driver = "uart_link"` is in an allow-set holding
   `dev` only (owner, 2026-10-22: "the guard from being included in real deployed firmware is the fact that the module is
   never included in the config files for deployment boards"); also no non-dev device's generated module imports
   `asy_uart_link_driver`. Seen failing on a planted TOML in a scratch copy.
3. `tests/test_asy_scd30_driver.py`: a PUT changing n NVM-backed settings sends exactly n NVM-storing commands; a PUT
   changing none sends none; `setup()` sends none (its temperature-offset access is a read); a boot's whole start
   sequence (setup, reset, the reader's start) sends the NVM-storing commands it sends today: count them, pin that
   count, and report it with each command. Pins of the current behaviour only: if a count differs from this, stop and
   report, never change the driver.
Checks: the three files at both stages where they apply; the 17 repo-wide scans of `S/u32/briefs/common_u32.md` once.

## Addendum for Z, M and O (lead, 2026-10-22, sent to the running blocks)
The owner (2026-10-22): "double check where it came from what it affects, what its intended function is. So if you
found opportunities to improve with no risk is absolutely desirable, but no regressions, also no hidden ones."
- Z: every hunk of the four lane P commits is classed as write mechanism (reverted) or other (kept unless it serves
  only the mechanism), with its function; nothing outside the files calls a removed name.
- M: each construct's origin (`git log -S --all`, then its step or finding); a construct added later to fix a fault
  keeps its guarantee, proven by a test biting a planted copy of that fault, or it stays; everything it affects is
  listed (callers, the REST command paths, the boot window, the feed hand-over, each mode).
- O: the int-address guard goes only if its int case is shown to come from the Unix port alone, never from rp2 at
  v1.29.0; unclear evidence keeps it. The hazard text is reworded only after the persisting site is found in source.
- Each hand-back adds a provenance table: construct, origin, intended function, change or "kept", the proving test.

### J addendum after block M (lead, 2026-10-22)
4. Add `S/u35/laneM/test_gate_guard.py`'s two tests as their own file `tests/test_asy_system_service_gate.py`
   (header: it pins the command gate's rule that a command holds the gate through a preflight that yields). Keep its
   import of test_asy_system_service's rig; drop the "Scratch guard (never committed)" wording. Show it passing at -1
   and 32768, and bitten by the lock-free gate (`S/u35/laneM/m_attempt.diff`'s gate hunk, applied in a scratch copy
   only). Run whatever tests_scripts check lists or times the tests/ files, and add the file wherever such a list
   needs it.
