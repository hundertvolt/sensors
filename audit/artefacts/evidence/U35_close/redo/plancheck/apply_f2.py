import sys
path = sys.argv[1]; text = open(path).read()
def rep(old, new):
    global text
    n = text.count(old); assert n == 1, (n, old[:90]); text = text.replace(old, new)

rep("the resolver's passed-in logger and `(address, cause)` widening (a diagnostic beyond need; one E67 as before);",
    "the resolver's passed-in logger and `(address, cause)` widening (a diagnostic beyond need; one E67 as before), its console line for a caught `MemoryError` (`asy_dns_client.py:154`) joining clarification (d)'s list;")

rep("| B6 UART | `asy_uart_driver.py`, `asy_uart_comm.py`, `asy_uart_link_driver.py`, `asy_framing_codecs.py` | Go: the zero-length guard; `PieceBuffer.read_at()`, whose one user is the responder's piece reply. Kept: `PieceBuffer.trim()`, which `uart_get()`, the SET receive and `readline()` call; the construction refusals E91/E92 and their build mirrors, the pre-audit pattern of a standalone module that refuses its own bad parameters (the ledger may shrink their form);",
    "| B6 UART | `asy_uart_driver.py`, `asy_uart_comm.py`, `asy_uart_link_driver.py`, `asy_framing_codecs.py`; `PieceBuffer` in `asy_base_classes.py` | Go: the zero-length guard. Kept: `PieceBuffer.trim()`, which `uart_get()`, the SET receive and `readline()` call; `PieceBuffer.read_at()` with the responder's piece reply and the echo's piece answer (without them the echo copies the peer's whole train, 12,192 bytes on dev, per GET: the scans' one measured row, and OR143 bounds contiguous allocations); the construction refusals, E91 with its build mirror and E92 (no TOML reaches it: generated code wires no framing), the pre-audit pattern of a standalone module that refuses its own bad parameters (the ledger may shrink their form);")

rep("The notification's sample-age check and its `State` field go.",
    "The notification's sample-age check and its `State` field go, with the field's generated status key (`buildgen/codegen.py:307`), its website row (`definitions.py:700-702`), its `NotifyState` code table, the mock data and the website test that names it, all in this batch.")
rep("| B7 LED | `asy_neopixel_driver.py`, `asy_notification_service.py` |",
    "| B7 LED | `asy_neopixel_driver.py`, `asy_notification_service.py`; the `State` field's buildgen, catalog and website sites |")

rep("Go: the build checks that no device TOML can trip (about 314 lines), except a rule whose violation would make a boot refuse or boot-loop: of the three I2C timeout checks, `bus.i2c-timeout-max` stays while the dominated boot-clear budget and loop-hold bound go, and the UART ranges stay as the build mirror of B6's kept refusals. The read triggers' bus-spread order (refuted: on all six devices it equals the construction order). The website lines with no recorded agreement (the items the owner approved stay; `PICTURE.md` 5), among them the page build-date stamp and the website rows of the status keys B2 and B7 remove.",
    "Go: the build checks that no device TOML can trip (about 260 lines; the twin-wiring typing and the compile check of the generated text are judged on their own), except a rule whose violation would make a boot refuse or boot-loop: of the four I2C timeout rules, `bus.i2c-timeout-range` and `bus.i2c-timeout-max` stay as one 1-200,000 us range (rp2 stores the timeout as `uint32_t`, `machine_i2c.c:47`), the boot-clear budget and the loop-hold rule go, and `smallest_hard_consumer()` stays for the twin, flash, bench and timing tests that read it; the UART ranges stay as the build mirror of B6's kept refusals. The website lines with no recorded agreement (the items the owner approved stay; `PICTURE.md` 5), among them the page build-date stamp, with its stager half in `scripts/_stage_website.py`, `build_firmware.py` and `build_website.sh`.")
rep("Kept: the generated boot entry's confirmed gaps (the emergency exception buffer, the loop-end labels). |",
    "Kept: the generated boot entry's confirmed gaps (the emergency exception buffer, the loop-end labels); the read triggers' bus-spread order, OR47's \"it's always only about sensors with bus access\" (it equals the construction order on today's six devices). |")
rep("| B8 build chain and generated code | `buildgen/`, the generated modules, `devices/*.toml`, `js/` and `html/` frozen into the image |",
    "| B8 build chain and generated code | `buildgen/`, the generated modules, `devices/*.toml`, `js/` and `html/` frozen into the image, the website stager in `scripts/` |")

rep("`src/LICENSE-captive_dns` (path names\nonly) is R4's.", "`src/LICENSE-captive_dns` (path names\nand the holder line, U34) is R4's.")

rep("""**Order.** B1 runs alone, then B2. B3-B7 run at most two at a time, on disjoint files. B8 runs last, because buildgen
reads the drivers' tags.""",
"""**Order.** B1 runs alone, then B2. B3-B7 run at most two at a time, on disjoint `src/` files. Three files are shared:
`buildgen/error_catalog.json`, the generated status emitter (`buildgen/codegen.py`) and its website rows
(`definitions.py`). `tests_scripts/test_error_catalog.py` makes a code's row go with its last site, and
`test_buildgen_definitions.py` makes a status row go with its key, so each batch removes its own rows and keys there,
and the lead merges those hunks of two parallel batches. B8 runs last for the rest of buildgen, because buildgen reads
the drivers' tags.""")
open(path, "w").write(text); print("ok")
