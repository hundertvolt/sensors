// Exercises the real website (html/ + js/, the real production entry point - never
// js/mock-server.js's static fixtures) against a live digital-twin backend: a real MicroPython
// Unix-port process serving the real REST API over real HTTP, the same "living integration" this
// project's other test tiers already prove for the Python side
// (tests/test_digital_twin_real_website_integration.py) and for a standalone boot
// (tests/test_digital_twin_sensortask_integration.py) - this is the missing third leg, the
// website's own JS actually driving a real browser against that live backend. See
// SPECIFICATION.md Part H.7.
//
// Needs the MicroPython Unix-port toolchain built (`uv run toolchain/setup_toolchain.py setup`)
// and the real wozi website frozen (`scripts/build_website.sh wozi`) - both are prerequisites the
// Python side's own test tiers already share, not something this file re-derives. Skips itself
// with a clear message if the toolchain isn't present (e.g. a quick local `npm test` with no
// MicroPython toolchain installed yet) rather than failing the whole suite; CI's web-unit-tests
// job builds both before running `npm test`, so it always exercises this for real.
import { commands } from "vitest/browser";
import { describe, expect, test } from "vitest";

describe("live digital-twin backend", () => {
    test(
        "the real website, driven by a real browser, round-trips a real PUT against a live twin",
        async () => {
            const result = await commands.runLiveBackendSmoke();

            if (result.skipped) {
                console.warn(`Skipping live-backend smoke check: ${result.reason}`);
                return;
            }

            expect(result.titleHasSensorStation).toBe(true);
            expect(result.deviceName).toContain("wozi");
            // "Valid" or "Unchanged" both mean the real backend genuinely accepted the write -
            // matching every other tier's own acceptance predicate for this same field
            // (scripts/_digital_twin_ci_suite.py's Run 1, SPECIFICATION.md Part H.4's PUT-result
            // vocabulary lowercased on the wire by the controller - see Part H.3's hooks table).
            expect(["valid", "unchanged"]).toContain(result.debugLevelApplyStatus);
        },
        45000, // real subprocess boot + real HTTP + real browser navigation - well past the
        // suite's default 20000ms backstop (vitest.config.js), same reasoning as that backstop's
        // own comment, scaled up for a real external process instead of an in-page fetch.
    );
});

// Known, harmless quirk: this file's own run prints "close timed out after 10000ms" from
// Vitest's own browser-mode teardown (confirmed: exit code 0, no leftover twin subprocess either
// way - `ps aux` clean after every run). Opening a second real page via the Commands API's raw
// BrowserContext (tests_js/_live_twin_command.js's own `context.newPage()`) appears to put
// Vitest's own teardown into a state its normal-case fast path doesn't handle, falling back to its
// documented 10s force-close watchdog instead - every other tests_js/*.test.js file (none of which
// open a second page) closes cleanly with no such message. Not a bug in this test or the command
// module as far as could be confirmed; revisit if a future Vitest/@vitest/browser-playwright
// release changes this.
