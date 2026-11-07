# Facts owed to wave 2 (lead, 2026-10-21)
- N2 (from C1, 0f55912): SPECIFICATION.md B.10.1 says "Playwright's browser is cached keyed on `package-lock.json`
  (which pins its version)"; since C1 every Playwright key also carries the runner identity (`ImageOS`, the compiler and
  the C library, hashed by the same `id: ident` step the toolchain action uses). Locate by text; reword to current state.
- T2 (from C1): `.github/workflows/ci.yml` changed in U34 (the four Playwright keys gain the runner identity): it
  belongs in the chroot-list paragraph as CI only, no chroot leg (R-15).
