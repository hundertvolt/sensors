import { afterEach, describe, expect, it, vi } from "vitest";
import { startApp } from "../js/app.js";
import { buildElements } from "./_dom_helpers.js";

const DEVICES = ["fixture-a", "fixture-b"];
const DEFINITIONS_DIR = "../build/generated_src/definitions";

/**
 * @param {string} id
 * @returns {import("../js/definitions.js").SiteDefinitions}
 */
function defsFor(id) {
    return {
        schemaVersion: "1.0.0",
        device: { id, displayName: `Display ${id}` },
        landingSection: "measurements",
        defaultPollIntervalMs: 20,
        sections: [
            { key: "measurements", label: "Measurements", rest: { get: "/measurements" }, pollGroup: "live", groups: [] },
            { key: "status", label: "Status", rest: { get: "/status" }, pollGroup: "settings", groups: [] },
        ],
    };
}

/** @type {import("../js/definitions.js").MockSamples} */
const SAMPLES = {
    measurements: {},
    sensorsConfig: {},
    networkingConfig: {},
    systemConfig: {},
    notificationConfig: {},
    status: { networking: {}, system: {}, sensors: {}, notification: {} },
    errcount: {},
};

/**
 * Serves the build's manifest, each manifest device's definitions and the mock samples; anything
 * else is a 404. A response given in `overrides` replaces the matching file's.
 * @param {{manifest?: Response, definitions?: Response, samples?: Response}} [overrides]
 */
function buildFetchStub(overrides = {}) {
    return vi.fn((/** @type {RequestInfo | URL} */ input) => {
        const url = String(input);
        if (url === `${DEFINITIONS_DIR}/index.json`) {
            return Promise.resolve(overrides.manifest ?? new Response(JSON.stringify({ devices: DEVICES }), { status: 200 }));
        }
        const device = DEVICES.find((id) => url === `${DEFINITIONS_DIR}/${id}.json`);
        if (device !== undefined) {
            return Promise.resolve(overrides.definitions ?? new Response(JSON.stringify(defsFor(device)), { status: 200 }));
        }
        if (url === "../mockdata/samples.json") {
            return Promise.resolve(overrides.samples ?? new Response(JSON.stringify(SAMPLES), { status: 200 }));
        }
        return Promise.resolve(new Response("not found", { status: 404 }));
    });
}

describe("startApp", () => {
    const originalFetch = window.fetch;
    const originalUrl = window.location.href;
    /** @type {ReturnType<typeof buildElements> | undefined} */
    let elements;
    /** @type {(() => void) | undefined} */
    let stop;

    afterEach(() => {
        stop?.();
        stop = undefined;
        window.fetch = originalFetch;
        if (elements) {
            for (const el of Object.values(elements)) {
                el.remove();
            }
        }
        window.history.replaceState(null, "", originalUrl);
    });

    it("loads the manifest's first device when ?device= is absent, renders its landing section", async () => {
        window.history.replaceState(null, "", "?");
        window.fetch = buildFetchStub();
        elements = buildElements();

        stop = await startApp(elements);

        expect(elements.deviceNameEl.textContent).toBe("Display fixture-a");
        expect(elements.errorBannerEl.dataset.shown).toBe("false");
        expect(elements.mainEl.querySelector(".section-heading")?.textContent).toBe("Measurements");
    });

    it("falls back to the manifest's first device when ?device= names an unknown device", async () => {
        window.history.replaceState(null, "", "?device=nonexistent");
        window.fetch = buildFetchStub();
        elements = buildElements();

        stop = await startApp(elements);

        expect(elements.deviceNameEl.textContent).toBe("Display fixture-a");
    });

    it("loads the device ?device= names when the manifest lists it", async () => {
        window.history.replaceState(null, "", "?device=fixture-b");
        window.fetch = buildFetchStub();
        elements = buildElements();

        stop = await startApp(elements);

        expect(elements.deviceNameEl.textContent).toBe("Display fixture-b");
    });

    it("selects the definitions' landingSection and marks it current in the nav drawer", async () => {
        window.history.replaceState(null, "", "?device=fixture-a");
        window.fetch = buildFetchStub();
        elements = buildElements();

        stop = await startApp(elements);

        const current = elements.drawerEl.querySelector('[aria-current="page"]');
        expect(current?.textContent).toBe("Measurements");
    });

    it("keeps ?device= while the URL's hash follows the section: a deep link, a menu selection, then Back", async () => {
        window.history.replaceState(null, "", "?device=fixture-b#status");
        window.fetch = buildFetchStub();
        elements = buildElements();
        stop = await startApp(elements);
        const { mainEl, drawerEl, deviceNameEl } = elements;
        const heading = () => mainEl.querySelector(".section-heading")?.textContent;
        expect(deviceNameEl.textContent).toBe("Display fixture-b");
        expect(heading()).toBe("Status");

        /** @type {HTMLElement} */ (drawerEl.querySelector('[data-section-key="measurements"]')).click();
        expect([window.location.search, window.location.hash, heading()]).toEqual(["?device=fixture-b", "#measurements", "Measurements"]);

        window.history.back();
        await vi.waitFor(() => expect(heading()).toBe("Status"));
        expect(window.location.search).toBe("?device=fixture-b");
    });

    it("returns a stop handle that stops the shell and uninstalls the mock backend", async () => {
        window.history.replaceState(null, "", "?device=fixture-a");
        const fetchStub = buildFetchStub();
        window.fetch = fetchStub;
        elements = buildElements();
        const stopApp = await startApp(elements);
        expect(window.fetch).not.toBe(fetchStub);

        stopApp();

        expect(window.fetch).toBe(fetchStub);
    });

    it("shows the device-list banner and renders no section when the manifest fails to load", async () => {
        window.history.replaceState(null, "", "?");
        window.fetch = buildFetchStub({ manifest: new Response("not found", { status: 404 }) });
        elements = buildElements();

        stop = await startApp(elements);

        expect(elements.errorBannerEl.dataset.shown).toBe("true");
        expect(elements.errorBannerEl.textContent).toMatch(/^Could not load the device list: Error: HTTP 404/);
        expect(elements.mainEl.querySelector(".section-heading")).toBeNull();
    });

    it("shows the device-list banner when the manifest lists no device", async () => {
        window.history.replaceState(null, "", "?");
        window.fetch = buildFetchStub({ manifest: new Response(JSON.stringify({ devices: [] }), { status: 200 }) });
        elements = buildElements();

        stop = await startApp(elements);

        expect(elements.errorBannerEl.dataset.shown).toBe("true");
        expect(elements.errorBannerEl.textContent).toMatch(/^Could not load the device list/);
        expect(elements.mainEl.querySelector(".section-heading")).toBeNull();
    });

    it("shows the error banner (and does not throw) when the device's definitions.json fails to load", async () => {
        window.history.replaceState(null, "", "?device=fixture-b");
        window.fetch = buildFetchStub({ definitions: new Response("not found", { status: 404 }) });
        elements = buildElements();

        stop = await startApp(elements);

        expect(elements.errorBannerEl.dataset.shown).toBe("true");
        expect(elements.errorBannerEl.textContent).toMatch(/fixture-b/);
        expect(elements.mainEl.querySelector(".section-heading")).toBeNull();
    });

    it("shows the error banner (and does not throw) when the mock samples answer HTTP 500", async () => {
        window.history.replaceState(null, "", "?device=fixture-a");
        window.fetch = buildFetchStub({ samples: new Response("server error", { status: 500 }) });
        elements = buildElements();

        stop = await startApp(elements);

        expect(elements.errorBannerEl.dataset.shown).toBe("true");
        expect(elements.errorBannerEl.textContent).toMatch(/fixture-a/);
        // Never got as far as rendering a section - no stale/half-built page left behind.
        expect(elements.mainEl.querySelector(".section-heading")).toBeNull();
    });

    it("shows a clear error banner (not a crash) when the mock samples are torn/truncated JSON", async () => {
        window.history.replaceState(null, "", "?device=fixture-a");
        window.fetch = buildFetchStub({ samples: new Response("{not valid json", { status: 200 }) });
        elements = buildElements();

        stop = await startApp(elements);

        expect(elements.errorBannerEl.dataset.shown).toBe("true");
        expect(elements.errorBannerEl.textContent).toMatch(/not valid json/i);
        expect(elements.mainEl.querySelector(".section-heading")).toBeNull();
    });
});
