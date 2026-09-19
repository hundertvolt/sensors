// Exercises the real website's own JS in a real browser against a live digital-twin backend (real
// REST API over real HTTP) - see SPECIFICATION.md Part H.7. Skips itself with a clear message if
// the MicroPython toolchain/frozen website aren't built yet, rather than failing the suite.
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
            // "Valid" or "Unchanged" both mean the backend accepted the write, matching every
            // other tier's acceptance predicate for this field (the twin suite's Run 1, Part
            // H.4's PUT-result vocabulary as the controller lowercases it on the wire).
            expect(["valid", "unchanged"]).toContain(result.debugLevelApplyStatus);
        },
        45000, // real subprocess boot + real HTTP + real browser navigation - well past the
        // suite's default 20000ms backstop (vitest.config.js), same reasoning as that backstop's
        // own comment, scaled up for a real external process instead of an in-page fetch.
    );
});

// Known harmless quirk: this file prints "close timed out after 10000ms" from Vitest's own
// teardown, with exit code 0 and no leftover twin. Opening a second page through the Commands
// API's raw BrowserContext appears to miss Vitest's fast path; no other file here opens one.
