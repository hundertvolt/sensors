// Every device's generated definitions pass the validator, load through the inlined element a device
// build serves, and render every group, field and errcount row against the device's composed mock data.
import { afterEach, describe, expect, it, vi } from "vitest";
import samples from "../mockdata/samples.json";
import { loadDefinitions, validateDefinitions } from "../js/definitions.js";
import { composeMockData, installMockFetch } from "../js/mock-server.js";
import { renderSection } from "../js/render.js";
import { DEVICE_IDS, GENERATED_DEFINITIONS } from "./_generated_definitions.js";

/** @typedef {import("../js/definitions.js").SiteDefinitions} SiteDefinitions */
/** @typedef {import("../js/definitions.js").Section} Section */

const SAMPLES = /** @type {import("../js/definitions.js").MockSamples} */ (samples);

// Polls instead of a fixed sleep: the mock answers after a randomised latency (js/mock-server.js).
/**
 * @param {() => boolean} check
 * @param {number} [timeoutMs]
 */
async function waitFor(check, timeoutMs = 5000) {
    const start = Date.now();
    while (!check()) {
        if (Date.now() - start > timeoutMs) {
            throw new Error(`condition not met within ${timeoutMs}ms`);
        }
        // eslint-disable-next-line no-await-in-loop -- each poll waits for the previous one
        await new Promise((resolve) => {
            setTimeout(resolve, 20);
        });
    }
}

/**
 * @param {string} device
 * @returns {SiteDefinitions}
 */
function definitionsOf(device) {
    const defs = GENERATED_DEFINITIONS.get(device);
    if (defs === undefined) {
        throw new Error(`no generated definitions for ${device}`);
    }
    return defs;
}

describe.each(DEVICE_IDS)("%s's generated definitions", (device) => {
    const defs = definitionsOf(device);
    /** @type {(() => void) | undefined} */
    let stop;
    /** @type {(() => void) | undefined} */
    let uninstall;
    /** @type {HTMLElement | undefined} */
    let mainEl;

    afterEach(() => {
        stop?.();
        uninstall?.();
        mainEl?.remove();
        vi.restoreAllMocks();
    });

    it("pass the validator", () => {
        expect(validateDefinitions(defs)).toEqual([]);
    });

    it("load through the inlined element a device build serves", async () => {
        const inlined = document.createElement("script");
        inlined.type = "application/json";
        inlined.textContent = JSON.stringify(defs);
        await expect(loadDefinitions("never-fetched.json", inlined)).resolves.toEqual(defs);
    });

    it.each(defs.sections.map((section) => /** @type {[string, Section]} */ ([section.key, section])))(
        "render the %s section's every group, field and errcount row, with no error",
        async (_key, section) => {
            const consoleError = vi.spyOn(console, "error");
            uninstall = installMockFetch(defs, composeMockData(defs, SAMPLES));
            const main = document.createElement("main");
            mainEl = main;
            document.body.appendChild(main);
            stop = renderSection(defs, section, main);
            await waitFor(() => main.querySelectorAll("[data-group-key]").length === section.groups.length);

            for (const group of section.groups) {
                const card = main.querySelector(`[data-group-key="${group.key}"]`);
                if (card === null) {
                    throw new Error(`no card for ${section.key}/${group.key}`);
                }
                const [rows, expected] = "fields" in group
                    ? [card.querySelectorAll("[data-field-wrapper-key]"), group.fields.length]
                    : [card.querySelectorAll(".errcount-row-wrapper"), group.modules.length];
                expect(rows, `${section.key}/${group.key}`).toHaveLength(expected);
            }
            expect(main.querySelector(".error-banner")?.classList.contains("hidden")).toBe(true);
            expect(consoleError).not.toHaveBeenCalled();
        },
    );
});
