import { afterEach, describe, expect, it, vi } from "vitest";
import { startApp } from "../js/app.js";

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
            // pollGroup "none" - startApp() has no stop handle exposed to callers, so a "live" section
            // here would keep polling (and calling the test's stubbed fetch) forever after each test ends.
            { key: "measurements", label: "Measurements", rest: { get: "/measurements" }, pollGroup: "none", groups: [] },
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
 * @returns {typeof fetch}
 */
function buildFetchStub(overrides = {}) {
    return vi.fn((input) => {
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

function buildElements() {
    const appShellEl = document.createElement("div");
    const mainEl = document.createElement("main");
    const drawerEl = document.createElement("nav");
    const hamburgerEl = document.createElement("button");
    const backdropEl = document.createElement("div");
    const errorBannerEl = document.createElement("p");
    errorBannerEl.className = "error-banner hidden";
    const deviceNameEl = document.createElement("span");
    const elements = { appShellEl, mainEl, drawerEl, hamburgerEl, backdropEl, errorBannerEl, deviceNameEl };
    for (const el of Object.values(elements)) {
        document.body.appendChild(el);
    }
    return elements;
}

describe("startApp", () => {
    const originalFetch = window.fetch;
    /** @type {ReturnType<typeof buildElements> | undefined} */
    let elements;

    afterEach(() => {
        window.fetch = originalFetch;
        if (elements) {
            for (const el of Object.values(elements)) {
                el.remove();
            }
        }
        window.history.pushState(null, "", window.location.pathname);
    });

    it("loads the manifest's first device when ?device= is absent, renders its landing section", async () => {
        window.history.pushState(null, "", "?");
        window.fetch = buildFetchStub();
        elements = buildElements();

        await startApp(elements);

        expect(elements.deviceNameEl.textContent).toBe("Display fixture-a");
        expect(elements.errorBannerEl.classList.contains("hidden")).toBe(true);
        expect(elements.mainEl.querySelector(".section-heading")?.textContent).toBe("Measurements");
    });

    it("falls back to the manifest's first device when ?device= names an unknown device", async () => {
        window.history.pushState(null, "", "?device=nonexistent");
        window.fetch = buildFetchStub();
        elements = buildElements();

        await startApp(elements);

        expect(elements.deviceNameEl.textContent).toBe("Display fixture-a");
    });

    it("loads the device ?device= names when the manifest lists it", async () => {
        window.history.pushState(null, "", "?device=fixture-b");
        window.fetch = buildFetchStub();
        elements = buildElements();

        await startApp(elements);

        expect(elements.deviceNameEl.textContent).toBe("Display fixture-b");
    });

    it("selects the definitions' landingSection and marks it current in the nav drawer", async () => {
        window.history.pushState(null, "", "?device=fixture-a");
        window.fetch = buildFetchStub();
        elements = buildElements();

        await startApp(elements);

        const current = elements.drawerEl.querySelector('[aria-current="page"]');
        expect(current?.textContent).toBe("Measurements");
    });

    it("shows the device-list banner and renders no section when the manifest fails to load", async () => {
        window.history.pushState(null, "", "?");
        window.fetch = buildFetchStub({ manifest: new Response("not found", { status: 404 }) });
        elements = buildElements();

        await startApp(elements);

        expect(elements.errorBannerEl.classList.contains("hidden")).toBe(false);
        expect(elements.errorBannerEl.textContent).toMatch(/^Could not load the device list/);
        expect(elements.mainEl.querySelector(".section-heading")).toBeNull();
    });

    it("shows the error banner (and does not throw) when the device's definitions.json fails to load", async () => {
        window.history.pushState(null, "", "?device=fixture-b");
        window.fetch = buildFetchStub({ definitions: new Response("not found", { status: 404 }) });
        elements = buildElements();

        await startApp(elements);

        expect(elements.errorBannerEl.classList.contains("hidden")).toBe(false);
        expect(elements.errorBannerEl.textContent).toMatch(/fixture-b/);
        expect(elements.mainEl.querySelector(".section-heading")).toBeNull();
    });

    it("shows the error banner (and does not throw) when the mock samples answer HTTP 500", async () => {
        window.history.pushState(null, "", "?device=fixture-a");
        window.fetch = buildFetchStub({ samples: new Response("server error", { status: 500 }) });
        elements = buildElements();

        await startApp(elements);

        expect(elements.errorBannerEl.classList.contains("hidden")).toBe(false);
        expect(elements.errorBannerEl.textContent).toMatch(/fixture-a/);
        // Never got as far as rendering a section - no stale/half-built page left behind.
        expect(elements.mainEl.querySelector(".section-heading")).toBeNull();
    });

    it("shows a clear error banner (not a crash) when the mock samples are torn/truncated JSON", async () => {
        window.history.pushState(null, "", "?device=fixture-a");
        window.fetch = buildFetchStub({ samples: new Response("{not valid json", { status: 200 }) });
        elements = buildElements();

        await startApp(elements);

        expect(elements.errorBannerEl.classList.contains("hidden")).toBe(false);
        expect(elements.errorBannerEl.textContent).toMatch(/not valid json/i);
        expect(elements.mainEl.querySelector(".section-heading")).toBeNull();
    });
});
