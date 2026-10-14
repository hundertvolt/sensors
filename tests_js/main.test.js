import { afterEach, describe, expect, it, vi } from "vitest";
import { startApp } from "../js/main.js";
import { buildElements } from "./_dom_helpers.js";

/** @type {import("../js/definitions.js").SiteDefinitions} */
const DEFS = {
    schemaVersion: "1.0.0",
    device: { id: "fixture-device", displayName: "Fixture Device" },
    landingSection: "measurements",
    defaultPollIntervalMs: 20,
    sections: [
        { key: "measurements", label: "Measurements", rest: { get: "/measurements" }, pollGroup: "live", groups: [] },
        { key: "status", label: "Status", rest: { get: "/status" }, pollGroup: "settings", groups: [] },
    ],
};

/**
 * Serves definitions.json, the landing section's GET and the device watch's /status and /system.
 * @param {{definitionsOk?: boolean}} [options]
 */
function buildFetchStub({ definitionsOk = true } = {}) {
    return vi.fn((/** @type {RequestInfo | URL} */ input) => {
        const url = String(input);
        if (url.includes("definitions.json")) {
            return Promise.resolve(definitionsOk ? new Response(JSON.stringify(DEFS), { status: 200 }) : new Response("not found", { status: 404 }));
        }
        if (url === "/measurements") {
            return Promise.resolve(new Response(JSON.stringify({}), { status: 200 }));
        }
        if (url === "/status") {
            return Promise.resolve(new Response(JSON.stringify({ system: { UnixTime: 1_700_000_000 } }), { status: 200 }));
        }
        if (url === "/system") {
            return Promise.resolve(new Response(JSON.stringify({ build: { version: "1.0.0" } }), { status: 200 }));
        }
        return Promise.resolve(new Response("not found", { status: 404 }));
    });
}

/**
 * The URLs a fetch stub was asked for.
 * @param {ReturnType<typeof vi.fn>} stub
 */
function requestedUrls(stub) {
    return stub.mock.calls.map(([input]) => String(input));
}

/**
 * Builds the `<script type="application/json" id="inlined-definitions">` element a real device
 * build embeds into index.html (scripts/_stage_website.py inlines it). buildElements() never
 * attaches one, since dev/preview has none, so each test that wants one passes it explicitly.
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
    const originalUrl = window.location.href;
    /** @type {ReturnType<typeof buildElements> | undefined} */
    let elements;
    /** @type {HTMLElement | undefined} */
    let inlinedEl;
    /** @type {(() => void) | undefined} */
    let stop;

    afterEach(() => {
        stop?.();
        stop = undefined;
        window.fetch = originalFetch;
        window.history.replaceState(null, "", originalUrl);
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

        stop = await startApp(elements);

        expect(fetchStub).toHaveBeenCalledWith("definitions.json", expect.anything());
        expect(elements.deviceNameEl.textContent).toBe("Fixture Device");
        expect(elements.errorBannerEl.dataset.shown).toBe("false");
        expect(elements.mainEl.querySelector(".section-heading")?.textContent).toBe("Measurements");
    });

    it("marks the landing section current in the nav drawer", async () => {
        window.fetch = buildFetchStub();
        elements = buildElements();

        stop = await startApp(elements);

        const current = elements.drawerEl.querySelector('[aria-current="page"]');
        expect(current?.textContent).toBe("Measurements");
    });

    it("returns a stop handle that ends the live landing section's polling and the device watch", async () => {
        const fetchStub = buildFetchStub();
        window.fetch = fetchStub;
        elements = buildElements();
        const stopApp = await startApp(elements);
        await vi.waitFor(() => expect(requestedUrls(fetchStub).filter((url) => url === "/measurements").length).toBeGreaterThan(1));

        stopApp();
        await new Promise((resolve) => {
            setTimeout(resolve, 100);
        });
        const afterStop = fetchStub.mock.calls.length;
        await new Promise((resolve) => {
            setTimeout(resolve, 100);
        });

        expect(fetchStub.mock.calls.length).toBe(afterStop);
        expect(requestedUrls(fetchStub)).toEqual(expect.arrayContaining(["/status", "/system"]));
    });

    it("opens the section a #<key> deep link names, through the page's own history", async () => {
        window.history.replaceState(null, "", "#status");
        window.fetch = buildFetchStub();
        elements = buildElements();

        stop = await startApp(elements);

        expect(elements.mainEl.querySelector(".section-heading")?.textContent).toBe("Status");
    });

    it("pushes #<key> for a menu selection, and the browser's Back returns to the landing section", async () => {
        window.fetch = buildFetchStub();
        elements = buildElements();
        stop = await startApp(elements);
        const { mainEl, drawerEl } = elements;

        /** @type {HTMLElement} */ (drawerEl.querySelector('[data-section-key="status"]')).click();
        expect(window.location.hash).toBe("#status");
        expect(mainEl.querySelector(".section-heading")?.textContent).toBe("Status");

        window.history.back();
        await vi.waitFor(() => expect(mainEl.querySelector(".section-heading")?.textContent).toBe("Measurements"));
    });

    it("closes the open drawer on Escape pressed anywhere on the page", async () => {
        window.fetch = buildFetchStub();
        elements = buildElements();
        stop = await startApp(elements);

        elements.hamburgerEl.click();
        expect(elements.appShellEl.dataset.navOpen).toBe("true");
        document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }));

        expect(elements.appShellEl.dataset.navOpen).toBe("false");
    });

    it("shows the error banner (and does not throw) when definitions.json fails to load", async () => {
        window.fetch = buildFetchStub({ definitionsOk: false });
        elements = buildElements();

        stop = await startApp(elements);

        expect(elements.errorBannerEl.dataset.shown).toBe("true");
        expect(elements.errorBannerEl.textContent).toMatch(/HTTP 404/);
        expect(elements.mainEl.querySelector(".section-heading")).toBeNull();
    });

    it("shows a clear error banner (not a crash) when definitions.json is torn/truncated JSON", async () => {
        window.fetch = vi.fn(() => Promise.resolve(new Response("{not valid json", { status: 200 })));
        elements = buildElements();

        stop = await startApp(elements);

        expect(elements.errorBannerEl.dataset.shown).toBe("true");
        expect(elements.errorBannerEl.textContent).toMatch(/not valid json/i);
        expect(elements.mainEl.querySelector(".section-heading")).toBeNull();
    });

    it("uses an inlined definitions element instead of fetching, when a real device build provides one", async () => {
        // The point of inlining (SPECIFICATION.md H.2: the stager inlines definitions.json): a device build never fetches it.
        const fetchStub = buildFetchStub();
        window.fetch = fetchStub;
        elements = buildElements();
        inlinedEl = buildInlinedDefinitionsEl(JSON.stringify(DEFS));

        stop = await startApp({ ...elements, inlinedDefinitionsEl: inlinedEl });

        expect(requestedUrls(fetchStub).filter((url) => url.includes("definitions.json"))).toEqual([]);
        expect(elements.deviceNameEl.textContent).toBe("Fixture Device");
        expect(elements.errorBannerEl.dataset.shown).toBe("false");
        expect(elements.mainEl.querySelector(".section-heading")?.textContent).toBe("Measurements");
    });

    it("shows a clear error banner (not a crash) when the inlined definitions element holds corrupted JSON", async () => {
        // Would only ever indicate a corrupted build (scripts/_stage_website.py always writes valid
        // JSON) - still must degrade the same clean way as a torn network response, not throw.
        window.fetch = vi.fn(() => {
            throw new Error("must not be called when an inlined element is present");
        });
        elements = buildElements();
        inlinedEl = buildInlinedDefinitionsEl("{not valid json");

        stop = await startApp({ ...elements, inlinedDefinitionsEl: inlinedEl });

        expect(elements.errorBannerEl.dataset.shown).toBe("true");
        expect(elements.mainEl.querySelector(".section-heading")).toBeNull();
    });

    it("falls back to fetching definitions.json when no inlined element is present (dev/preview mode)", async () => {
        const fetchStub = buildFetchStub();
        window.fetch = fetchStub;
        elements = buildElements();

        stop = await startApp({ ...elements, inlinedDefinitionsEl: null });

        expect(fetchStub).toHaveBeenCalledWith("definitions.json", expect.anything());
        expect(elements.deviceNameEl.textContent).toBe("Fixture Device");
    });
});
