// Exercises the real website's own JS in a real browser against a live digital-twin backend for every device (real
// REST API over real HTTP, SPECIFICATION.md Part H.7). A missing interpreter or build fails the suite; it never skips.
import { commands } from "vitest/browser";
import { describe, expect, it } from "vitest";
import { DEVICE_IDS, GENERATED_DEFINITIONS } from "./_generated_definitions.js";

// Real subprocess boot + real HTTP + real browser navigation, well past the suite's 20000ms backstop (vitest.config.js).
// Each command takes its test's timeout and ends its own waits one twin stop before it: Vitest never cancels a command.
const SMOKE_TIMEOUT_MS = 45000;
// Boot 20 s, the first pass within the page's 15 s request cap plus 5 s, one 20 s reload slot per tab of the six, each
// slot including its drain (agent, 2026-10-13), the stop.
// @tunable l0.live_concurrent_tabs_timeout_ms = 200000
const CONCURRENT_TABS_TIMEOUT_MS = 200000;
// Two boots of 20 s, the banner, the 60 s back-off cap the page may be waiting out, two stops and their drains.
// @tunable l0.live_restart_recovery_timeout_ms = 180000
const RESTART_RECOVERY_TIMEOUT_MS = 180000;

/**
 * The display name the device's own generated definitions give its page.
 * @param {string} device
 * @returns {string}
 */
function displayNameOf(device) {
    return /** @type {import("../js/definitions.js").SiteDefinitions} */ (GENERATED_DEFINITIONS.get(device)).device.displayName;
}

describe.each(DEVICE_IDS)("live digital-twin backend: %s", (device) => {
    it(
        "the real website, driven by a real browser, round-trips a real PUT against a live twin",
        async () => {
            const result = await commands.runLiveBackendSmoke(device, SMOKE_TIMEOUT_MS);


            expect(result.titleHasSensorStation).toBe(true);
            expect(result.deviceName).toContain(displayNameOf(device));
            expect([result.firstStatus, result.resubmitStatus]).toEqual(["valid", "unchanged"]);
        },
        SMOKE_TIMEOUT_MS,
    );
});

describe.each(DEVICE_IDS)("live digital-twin backend, concurrent browser sessions: %s", (device) => {
    it(
        "a full ceiling of browser tabs against one live twin all load, directly or on one reload",
        async () => {
            const result = await commands.runLiveBackendConcurrentTabs(device, CONCURRENT_TABS_TIMEOUT_MS);


            const { tabs, loadedFirstPass, loadedAfterRetry } = result;
            // eslint-disable-next-line no-console -- a pass keeps its evidence: one line of counts per device
            console.log(`concurrent tabs on ${device}: ${tabs} tabs, ${loadedFirstPass} loaded on the first pass, ${loadedAfterRetry - loadedFirstPass} on their reload, ${tabs - loadedAfterRetry} not at all`);
            expect(result.loadedFirstPass).toBeGreaterThanOrEqual(1);
            expect(result.loadedAfterRetry, result.failures.join("\n")).toBe(result.tabs);
        },
        CONCURRENT_TABS_TIMEOUT_MS,
    );
});

describe.each(DEVICE_IDS)("live digital-twin backend, device restart: %s", (device) => {
    it(
        "the page recovers from a device restart without reloading",
        async () => {
            const result = await commands.runLiveBackendRestartRecovery(device, RESTART_RECOVERY_TIMEOUT_MS);


            expect(result).toEqual({ bannerShown: true, recovered: true, reloaded: false });
        },
        RESTART_RECOVERY_TIMEOUT_MS,
    );
});
