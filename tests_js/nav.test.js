import { afterEach, describe, expect, it, vi } from "vitest";
import { initNav } from "../js/nav.js";

/** @type {import("../js/definitions.js").SiteDefinitions} */
const DEFS = {
    schemaVersion: "1.0.0",
    device: { id: "fixture-device", displayName: "Fixture Device" },
    landingSection: "measurements",
    defaultPollIntervalMs: 3000,
    sections: [
        { key: "measurements", label: "Measurements", rest: { get: "/measurements" }, pollGroup: "live", groups: [] },
        { key: "status", label: "Status", rest: { get: "/status" }, pollGroup: "settings", groups: [] },
    ],
};

function mount() {
    const appShellEl = document.createElement("div");
    const drawerEl = document.createElement("nav");
    const hamburgerEl = document.createElement("button");
    hamburgerEl.setAttribute("aria-expanded", "false");
    const backdropEl = document.createElement("div");
    document.body.append(appShellEl, drawerEl, hamburgerEl, backdropEl);
    return { appShellEl, drawerEl, hamburgerEl, backdropEl };
}

/**
 * The listeners still registered on `target`: every (type, listener) added and not removed since the spies began.
 * @param {EventTarget} target
 * @returns {() => number}
 */
function listenerCounter(target) {
    const added = vi.spyOn(target, "addEventListener");
    const removed = vi.spyOn(target, "removeEventListener");
    return () => added.mock.calls.filter(([type, listener]) => !removed.mock.calls.some(([t, l]) => t === type && l === listener)).length;
}

describe("initNav", () => {
    /** @type {ReturnType<typeof mount> | undefined} */
    let elements;
    /** @type {EventTarget} */
    let keyTarget;
    /** @type {ReturnType<typeof initNav> | undefined} */
    let nav;

    /** @param {(sectionKey: string) => void} [onSelect] */
    function start(onSelect = () => { /* the test checks drawer mechanics, not selection */ }) {
        elements = mount();
        keyTarget = new EventTarget();
        nav = initNav({ defs: DEFS, ...elements, keyTarget, onSelect });
        return elements;
    }

    afterEach(() => {
        nav?.dispose();
        nav = undefined;
        if (elements) {
            for (const el of Object.values(elements)) {
                el.remove();
            }
        }
    });

    it("builds the drawer from definitions and toggles data-nav-open when the hamburger is clicked", () => {
        const { appShellEl, drawerEl, hamburgerEl } = start();

        expect(drawerEl.querySelectorAll("[data-section-key]")).toHaveLength(2);
        expect(appShellEl.dataset.navOpen).toBe("false");

        hamburgerEl.click();
        expect(appShellEl.dataset.navOpen).toBe("true");
        expect(hamburgerEl.getAttribute("aria-expanded")).toBe("true");

        hamburgerEl.click();
        expect(appShellEl.dataset.navOpen).toBe("false");
        expect(hamburgerEl.getAttribute("aria-expanded")).toBe("false");
    });

    it("closes the drawer when the backdrop is clicked", () => {
        const { appShellEl, hamburgerEl, backdropEl } = start();

        hamburgerEl.click();
        expect(appShellEl.dataset.navOpen).toBe("true");

        backdropEl.click();
        expect(appShellEl.dataset.navOpen).toBe("false");
        expect(hamburgerEl.getAttribute("aria-expanded")).toBe("false");
    });

    it("closes the drawer on Escape pressed on the key target it was given", () => {
        const { appShellEl, hamburgerEl } = start();

        hamburgerEl.click();
        expect(appShellEl.dataset.navOpen).toBe("true");

        keyTarget.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }));
        expect(appShellEl.dataset.navOpen).toBe("false");
    });

    it("closes the drawer and fires onSelect with the clicked section's key", () => {
        const onSelect = vi.fn();
        const { appShellEl, drawerEl, hamburgerEl } = start(onSelect);

        hamburgerEl.click();
        const statusLink = /** @type {HTMLElement} */ (drawerEl.querySelector('[data-section-key="status"]'));
        statusLink.click();

        expect(onSelect).toHaveBeenCalledWith("status");
        expect(appShellEl.dataset.navOpen).toBe("false");
    });

    it("setCurrent marks exactly one link aria-current, moving it between calls", () => {
        const { drawerEl } = start();

        nav?.setCurrent("measurements");
        const measurementsLink = /** @type {HTMLElement} */ (drawerEl.querySelector('[data-section-key="measurements"]'));
        const statusLink = /** @type {HTMLElement} */ (drawerEl.querySelector('[data-section-key="status"]'));
        expect(measurementsLink.getAttribute("aria-current")).toBe("page");
        expect(statusLink.hasAttribute("aria-current")).toBe(false);

        nav?.setCurrent("status");
        expect(measurementsLink.hasAttribute("aria-current")).toBe(false);
        expect(statusLink.getAttribute("aria-current")).toBe("page");
    });

    it("keeps the closed drawer inert and names the hamburger's action; opening lifts it and focuses the first link", () => {
        const { drawerEl, hamburgerEl } = start();
        expect(drawerEl.inert).toBe(true);
        expect(hamburgerEl.getAttribute("aria-label")).toBe("Open navigation");

        hamburgerEl.click();

        expect(drawerEl.inert).toBe(false);
        expect(hamburgerEl.getAttribute("aria-label")).toBe("Close navigation");
        expect(document.activeElement).toBe(drawerEl.querySelector("[data-section-key]"));
    });

    it("returns focus to the hamburger when the drawer closes with focus inside it", () => {
        const { drawerEl, hamburgerEl } = start();
        hamburgerEl.click();
        expect(drawerEl.matches(":focus-within")).toBe(true);

        keyTarget.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }));

        expect(drawerEl.inert).toBe(true);
        expect(hamburgerEl.getAttribute("aria-label")).toBe("Open navigation");
        expect(document.activeElement).toBe(hamburgerEl);
    });

    it("dispose() removes every listener it added: on the key target, the hamburger, the backdrop and the links", () => {
        elements = mount();
        keyTarget = new EventTarget();
        const counters = [keyTarget, elements.hamburgerEl, elements.backdropEl].map(listenerCounter);
        const onSelect = vi.fn();
        nav = initNav({ defs: DEFS, ...elements, keyTarget, onSelect });
        expect(counters.map((left) => left())).toEqual([1, 1, 1]);
        const statusLink = /** @type {HTMLElement} */ (elements.drawerEl.querySelector('[data-section-key="status"]'));

        nav.dispose();
        nav = undefined;

        expect(counters.map((left) => left())).toEqual([0, 0, 0]);
        statusLink.click();
        elements.hamburgerEl.click();
        expect(onSelect).not.toHaveBeenCalled();
        expect(elements.appShellEl.dataset.navOpen).toBe("false");
    });
});
