import { afterEach, describe, expect, it, vi } from "vitest";
import { startApp } from "../js/app.js";

/** @type {import("../js/definitions.js").SiteDefinitions} */
const DEFS = {
    schemaVersion: "1.0.0",
    device: { id: "wozi", displayName: "Wozi Test" },
    landingSection: "measurements",
    defaultPollIntervalMs: 20,
    sections: [
        // pollGroup "none" - startApp() has no stop handle exposed to callers, so a "live" section
        // here would keep polling (and calling the test's stubbed fetch) forever after each test ends.
        { key: "measurements", label: "Measurements", rest: { get: "/measurements" }, pollGroup: "none", groups: [] },
    ],
};

/** @type {import("../js/definitions.js").MockDeviceData} */
const MOCK_DATA = {
    measurements: {},
    sensorsConfig: {},
    networkingConfig: {},
    systemConfig: {},
    notificationConfig: {},
    status: { networking: {}, system: {}, sensors: {}, notification: {}, errcount: {} },
};

/**
 * @param {{definitionsOk?: boolean, mockDataOk?: boolean}} [options]
 * @returns {typeof fetch}
 */
function buildFetchStub({ definitionsOk = true, mockDataOk = true } = {}) {
    return vi.fn(async (input) => {
        const url = String(input);
        if (url.includes("definitions/wozi.json")) {
            return definitionsOk ? new Response(JSON.stringify(DEFS), { status: 200 }) : new Response("not found", { status: 404 });
        }
        if (url.includes("mockdata/wozi.json")) {
            return mockDataOk ? new Response(JSON.stringify(MOCK_DATA), { status: 200 }) : new Response("server error", { status: 500 });
        }
        return new Response("not found", { status: 404 });
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

    it("loads the default device (wozi) when ?device= is absent, renders its landing section", async () => {
        window.history.pushState(null, "", "?");
        window.fetch = buildFetchStub();
        elements = buildElements();

        await startApp(elements);

        expect(elements.deviceNameEl.textContent).toBe("Wozi Test");
        expect(elements.errorBannerEl.classList.contains("hidden")).toBe(true);
        expect(elements.mainEl.querySelector(".section-heading")?.textContent).toBe("Measurements");
    });

    it("falls back to the default device when ?device= names an unknown device", async () => {
        window.history.pushState(null, "", "?device=nonexistent");
        window.fetch = buildFetchStub();
        elements = buildElements();

        await startApp(elements);

        expect(elements.deviceNameEl.textContent).toBe("Wozi Test");
    });

    it("selects the definitions' landingSection and marks it current in the nav drawer", async () => {
        window.history.pushState(null, "", "?device=wozi");
        window.fetch = buildFetchStub();
        elements = buildElements();

        await startApp(elements);

        const current = elements.drawerEl.querySelector('[aria-current="page"]');
        expect(current?.textContent).toBe("Measurements");
    });

    it("shows the error banner (and does not throw) when the device's definitions.json fails to load", async () => {
        window.history.pushState(null, "", "?device=dev");
        window.fetch = buildFetchStub({ definitionsOk: false });
        elements = buildElements();

        await startApp(elements);

        expect(elements.errorBannerEl.classList.contains("hidden")).toBe(false);
        expect(elements.errorBannerEl.textContent).toMatch(/dev/);
    });

    it("shows the error banner (and does not throw) when the mock fixture data fails to load", async () => {
        window.history.pushState(null, "", "?device=wozi");
        window.fetch = buildFetchStub({ mockDataOk: false });
        elements = buildElements();

        await startApp(elements);

        expect(elements.errorBannerEl.classList.contains("hidden")).toBe(false);
        expect(elements.errorBannerEl.textContent).toMatch(/wozi/i);
        // Never got as far as rendering a section - no stale/half-built page left behind.
        expect(elements.mainEl.querySelector(".section-heading")).toBeNull();
    });

    it("shows a clear error banner (not a crash) when the mock fixture data is torn/truncated JSON", async () => {
        window.history.pushState(null, "", "?device=wozi");
        window.fetch = vi.fn(async (input) => {
            const url = String(input);
            if (url.includes("definitions/wozi.json")) {
                return new Response(JSON.stringify(DEFS), { status: 200 });
            }
            if (url.includes("mockdata/wozi.json")) {
                return new Response("{not valid json", { status: 200 });
            }
            return new Response("not found", { status: 404 });
        });
        elements = buildElements();

        await startApp(elements);

        expect(elements.errorBannerEl.classList.contains("hidden")).toBe(false);
        expect(elements.errorBannerEl.textContent).toMatch(/not valid json/i);
        expect(elements.mainEl.querySelector(".section-heading")).toBeNull();
    });
});
