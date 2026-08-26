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

/**
 * Builds a `<script type="application/json" id="inlined-definitions">` element the same shape
 * scripts/build_website.sh's own "Inlining" comment describes a real device build embedding into
 * index.html - not attached to `elements` by buildElements() itself (dev/preview mode's own
 * html/index.html never has one), so each test that wants one builds and passes it explicitly.
 * @param {string} jsonText
 */
function buildInlinedDefinitionsEl(jsonText) {
    const el = document.createElement("script");
    el.type = "application/json";
    el.id = "inlined-definitions";
    el.textContent = jsonText;
    document.body.appendChild(el);
    return el;
}

describe("startApp (production entry)", () => {
    const originalFetch = window.fetch;
    /** @type {ReturnType<typeof buildElements> | undefined} */
    let elements;
    /** @type {HTMLElement | undefined} */
    let inlinedEl;

    afterEach(() => {
        window.fetch = originalFetch;
        if (elements) {
            for (const el of Object.values(elements)) {
                el.remove();
            }
        }
        if (inlinedEl) {
            inlinedEl.remove();
            inlinedEl = undefined;
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

    it("uses an inlined definitions element instead of fetching, when a real device build provides one", async () => {
        // The actual point of inlining (scripts/build_website.sh's own "Inlining" comment,
        // SPECIFICATION.md Part H.7's follow-up round): a real device build must never hit the
        // network for definitions.json at all once this element is present.
        const fetchStub = buildFetchStub();
        window.fetch = fetchStub;
        elements = buildElements();
        inlinedEl = buildInlinedDefinitionsEl(JSON.stringify(DEFS));

        await startApp({ ...elements, inlinedDefinitionsEl: inlinedEl });

        expect(fetchStub).not.toHaveBeenCalled();
        expect(elements.deviceNameEl.textContent).toBe("Wozi Test");
        expect(elements.errorBannerEl.classList.contains("hidden")).toBe(true);
        expect(elements.mainEl.querySelector(".section-heading")?.textContent).toBe("Measurements");
    });

    it("shows a clear error banner (not a crash) when the inlined definitions element holds corrupted JSON", async () => {
        // Would only ever indicate a corrupted build (scripts/build_website.sh always writes valid
        // JSON) - still must degrade the same clean way as a torn network response, not throw.
        window.fetch = vi.fn(() => {
            throw new Error("must not be called when an inlined element is present");
        });
        elements = buildElements();
        inlinedEl = buildInlinedDefinitionsEl("{not valid json");

        await startApp({ ...elements, inlinedDefinitionsEl: inlinedEl });

        expect(elements.errorBannerEl.classList.contains("hidden")).toBe(false);
        expect(elements.mainEl.querySelector(".section-heading")).toBeNull();
    });

    it("falls back to fetching definitions.json when no inlined element is present (dev/preview mode)", async () => {
        const fetchStub = buildFetchStub();
        window.fetch = fetchStub;
        elements = buildElements();

        await startApp({ ...elements, inlinedDefinitionsEl: null });

        expect(fetchStub).toHaveBeenCalledWith("definitions.json", expect.anything());
        expect(elements.deviceNameEl.textContent).toBe("Wozi Test");
    });
});
