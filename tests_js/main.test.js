import { afterEach, describe, expect, it, vi } from "vitest";
import { startApp } from "../js/main.js";

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

/**
 * @param {{definitionsOk?: boolean}} [options]
 * @returns {typeof fetch}
 */
function buildFetchStub({ definitionsOk = true } = {}) {
    return vi.fn(async (input) => {
        const url = String(input);
        if (url.includes("definitions.json")) {
            return definitionsOk ? new Response(JSON.stringify(DEFS), { status: 200 }) : new Response("not found", { status: 404 });
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

describe("startApp (production entry)", () => {
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
    });

    it("loads definitions.json (no device segment, no mock install) and renders the landing section", async () => {
        const fetchStub = buildFetchStub();
        window.fetch = fetchStub;
        elements = buildElements();

        await startApp(elements);

        expect(fetchStub).toHaveBeenCalledWith("definitions.json", expect.anything());
        expect(elements.deviceNameEl.textContent).toBe("Wozi Test");
        expect(elements.errorBannerEl.classList.contains("hidden")).toBe(true);
        expect(elements.mainEl.querySelector(".section-heading")?.textContent).toBe("Measurements");
    });

    it("marks the landing section current in the nav drawer", async () => {
        window.fetch = buildFetchStub();
        elements = buildElements();

        await startApp(elements);

        const current = elements.drawerEl.querySelector('[aria-current="page"]');
        expect(current?.textContent).toBe("Measurements");
    });

    it("shows the error banner (and does not throw) when definitions.json fails to load", async () => {
        window.fetch = buildFetchStub({ definitionsOk: false });
        elements = buildElements();

        await startApp(elements);

        expect(elements.errorBannerEl.classList.contains("hidden")).toBe(false);
        expect(elements.mainEl.querySelector(".section-heading")).toBeNull();
    });

    it("shows a clear error banner (not a crash) when definitions.json is torn/truncated JSON", async () => {
        window.fetch = vi.fn(async () => new Response("{not valid json", { status: 200 }));
        elements = buildElements();

        await startApp(elements);

        expect(elements.errorBannerEl.classList.contains("hidden")).toBe(false);
        expect(elements.errorBannerEl.textContent).toMatch(/not valid json/i);
        expect(elements.mainEl.querySelector(".section-heading")).toBeNull();
    });
});
