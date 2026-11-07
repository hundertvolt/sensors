# N15: the twin's port-53 servers isolated per test process (lead, 2026-10-27)
Read `S/u35r/briefs/redo_common.md` (all of it; "Quality comes first" and "Efficiency" are binding, and it says how
you hand back). Then, on your worktree:
- CLAUDE.md's "Two suites that both bind real ports" bullet;
- `digital_twin/unixport/_unix_port_udp_addr_shim.py` in full, and `digital_twin/README.md`'s section on it;
- `scripts/test.sh`'s job list and TEST_PARALLELISM;
- `tests/test_digital_twin_sensortask_integration.py`'s `_dns_burst`, `_CountingPoller`, and the three captive-DNS
  tests (the idle rate, the bind that fails, the hotspot fallback);
- `scripts/_digital_twin_ci_suite.py`'s `DNS_PORT` user (Run 7).

Worktree and base: in your launch message. Logs go in `S/u35/laneC/n15/`.

## The fault (CI run 40563803565, unit-tests, GC stage -1, head 4753a394)
`tests/test_digital_twin_sensortask_integration.py[grkizi]::test_the_captive_dns_listener_idles_at_its_idle_rate`:
"36 listener wake-ups in 3000 ms, not 30 +-1 at 100 ms". The same test passed in the run before, on 2a4bc11e.

The lead's reading: the excess is exactly `_BURST` (6), one other process's query burst.
- The shim binds every server wildcard on 127.0.0.1, and `asy_udp_socket.py` sets SO_REUSEADDR.
- So every concurrently running test process that boots a captive DNS shares 127.0.0.1:53. The PER_DEVICE jobs of this
  file (arzi, dev, grkizi) are such processes, and others may be too.
- Linux delivers a unicast datagram to one of the sharing sockets, so a sibling's burst can land in this listener.
- The same sharing can produce a false pass. A test asserting that its own (rebuilt) socket answered can be answered
  by another process's listener. The bind-fails test asserts exactly that.
- This is the in-tier counterpart of CLAUDE.md's "two suites that bind real ports" rule. That bullet's "overlap
  safely" covers the bind, not the delivery.

## Items, in order (each committed green on its own)
1. **Reproduce first.**
   - Use a tests_scripts (pytest) test, or a harness under `S/u35/laneC/n15/`, that runs two Unix-port processes at
     once on the current shim.
   - Process A boots a captive DNS listener and counts the datagrams it receives over a window. Process B sends one
     burst to the twin's DNS address.
   - Show A receiving B's queries, at both stages. That is the red-first evidence.
   - If it does not reproduce, stop and hand the facts to the lead.
   - Keep the reproduction cheap: bare `UDPSocket`s through the shim, not two full device boots, if that shows the
     same delivery.
2. **The fix, preferred direction:** each test process gets its own loopback address.
   - The shim binds a server's wildcard on that address instead of 127.0.0.1. Every in-process peer that targets the
     twin's own server (`_dns_burst` and its kind) reads the address from the shim rather than hard-coding 127.0.0.1.
   - The real port 53 stays, so the CAP_NET_BIND_SERVICE path keeps its fidelity.
   - The address comes from the runner (`scripts/test.sh` gives each job a distinct one), with 127.0.0.1 as the default.
     That way `run_digital_twin_ci.sh`, the host-side scenario harness and the tests_scripts twins, which talk to the
     twin from the host, keep working unchanged, or read the same value.
   - An alternative may serve better, for example remapping only the fixed server ports, or `scripts/test.sh`
     serializing the port-53 users. If so, say why with numbers. Serializing costs wall time: measure it.
   - No src/ change. If one turns out to be needed, stop and hand back.
3. **Bites:**
   - item 1's reproduction green on the new shim, at both stages;
   - the reproduction red again when the shim's old address is planted back;
   - every twin test that reaches a captive DNS still passes with its own address, on all six devices, at both stages.
4. Find every other fixed-port server the twin binds on loopback (grep the shim's users and every `bind(` reached from
   a booted graph). Each one is either covered by item 2, or listed with the reason it cannot collide (an ephemeral
   port, for instance).
5. `digital_twin/README.md`'s shim section and CLAUDE.md's "Two suites" bullet: write the corrected text into your
   hand-back for the lead's D3r. Do not edit those two docs.
6. Checks:
   - digital_twin/unixport is shared by every twin test, so run the whole twin tier (every
     tests/test_digital_twin_*.py, all six devices, both stages) and the scenario harness jobs, with zero memory
     markers;
   - `tests_scripts/test_test_sh.py` and any tests_scripts file the runner change touches;
   - on the final head, the whole tests_scripts tier;
   - lint_direct, the six mypy passes, and the three audit checks;
   - review rows if a test's text changed.

## Notes
- Other lanes are changing parts of `tests/test_digital_twin_sensortask_integration.py`. N11e has the streak constants
  near :132; CMr1m has the drift check. Keep your edit there to `_dns_burst`'s address and whatever reads the shim.
  UM4 is changing `digital_twin/run_generic_integration.py` and `scripts/_digital_twin_scenarios.py`; avoid them, or
  name the need.
- Port-binding runs go in `unshare -n S/u24/ns_xdg.sh`, nice 19, as redo_common says. That namespace isolates your runs
  from the other lanes. It does not isolate the jobs inside one run from each other, which is the fault.
- Run to the end; hand back early only as redo_common says.

## Hand-back (the file, per redo_common)
- Commits.
- The reproduction: red and green, with logs.
- The fix and why that form.
- The bites.
- Item 4's list.
- The doc text for D3r.
- The twin tier's results at both stages, with wall time before and after.
- The checks.
- Last line: "nothing of mine is running".
