# Twin UART-link file red on the merged U16 tree: root cause

Seen (before_d.log, before_t.log): "UART_init counted an error on a clean link", plus the hammer, max-train and
back-to-back checks, at both GC stages.

Probes (uart_probe.py, uart_probe2.py, run from the merged tree): both UART loggers held one E28 `LOG_RAM_ONLY` from
boot; dev's FRAM logger held 121 entries (W63, E18 NOT_INIT, E101); `FRAMManager.initialized` was False with
`size` 262144, while the twin's chip was 8192 bytes answering MB85RS64V's RDID (04 7F 03 02).

Cause: `build_linked_system()` built dev's graph without `machine.configure_i2c_wiring("dev")`, so the twin fell
back to wozi's wiring plan and attached wozi's 8 KB chip under dev's 256 KB manager. Before U16 that aliased
silently (the same class lane G closed at the mock tier); U16's FRAM setup checks the product ID against the
declared size and refuses the chip, so every FRAM-backed logger ran RAM-only. The product behaved correctly; the
fixture was wrong. Every other twin file that builds dev configures dev's plan first (checked).

Fix: the fixture configures dev's plan before the build. After: 17/17 at both stages, no memory markers
(after_d.log, after_t.log).
