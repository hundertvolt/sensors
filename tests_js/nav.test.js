import { afterEach, describe, expect, it, vi } from "vitest";
import { initNav } from "../js/nav.js";

/** @type {import("../js/definitions.js").SiteDefinitions} */
const DEFS = {
    schemaVersion: "1.0.0",
    device: { id: "wozi", displayName: "wozi" },
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

describe("initNav", () => {
    /** @type {ReturnType<typeof mount> | undefined} */
    let elements;

    afterEach(() => {
        if (elements) {
            for (const el of Object.values(elements)) {
                el.remove();
            }
        }
    });

    it("builds the drawer from definitions and toggles nav-open when the hamburger is clicked", () => {
        elements = mount();
        const { appShellEl, drawerEl, hamburgerEl, backdropEl } = elements;
        initNav({ defs: DEFS, appShellEl, drawerEl, hamburgerEl, backdropEl, onSelect: () => {} });

        expect(drawerEl.querySelectorAll("[data-section-key]")).toHaveLength(2);
        expect(appShellEl.classList.contains("nav-open")).toBe(false);

        hamburgerEl.click();
        expect(appShellEl.classList.contains("nav-open")).toBe(true);
        expect(hamburgerEl.getAttribute("aria-expanded")).toBe("true");

        hamburgerEl.click();
        expect(appShellEl.classList.contains("nav-open")).toBe(false);
        expect(hamburgerEl.getAttribute("aria-expanded")).toBe("false");
    });

    it("closes the drawer when the backdrop is clicked", () => {
        elements = mount();
        const { appShellEl, drawerEl, hamburgerEl, backdropEl } = elements;
        initNav({ defs: DEFS, appShellEl, drawerEl, hamburgerEl, backdropEl, onSelect: () => {} });

        hamburgerEl.click();
        expect(appShellEl.classList.contains("nav-open")).toBe(true);

        backdropEl.click();
        expect(appShellEl.classList.contains("nav-open")).toBe(false);
        expect(hamburgerEl.getAttribute("aria-expanded")).toBe("false");
    });

    it("closes the drawer on Escape", () => {
        elements = mount();
        const { appShellEl, drawerEl, hamburgerEl, backdropEl } = elements;
        initNav({ defs: DEFS, appShellEl, drawerEl, hamburgerEl, backdropEl, onSelect: () => {} });

        hamburgerEl.click();
        expect(appShellEl.classList.contains("nav-open")).toBe(true);

        document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }));
        expect(appShellEl.classList.contains("nav-open")).toBe(false);
    });

    it("closes the drawer and fires onSelect with the clicked section's key", () => {
        elements = mount();
        const { appShellEl, drawerEl, hamburgerEl, backdropEl } = elements;
        const onSelect = vi.fn();
        initNav({ defs: DEFS, appShellEl, drawerEl, hamburgerEl, backdropEl, onSelect });

        hamburgerEl.click();
        const statusLink = /** @type {HTMLElement} */ (drawerEl.querySelector('[data-section-key="status"]'));
        statusLink.click();

        expect(onSelect).toHaveBeenCalledWith("status");
        expect(appShellEl.classList.contains("nav-open")).toBe(false);
    });

    it("returned setCurrentNav marks exactly one link aria-current, moving it between calls", () => {
        elements = mount();
        const { appShellEl, drawerEl, hamburgerEl, backdropEl } = elements;
        const setCurrentNav = initNav({ defs: DEFS, appShellEl, drawerEl, hamburgerEl, backdropEl, onSelect: () => {} });

        setCurrentNav("measurements");
        const measurementsLink = /** @type {HTMLElement} */ (drawerEl.querySelector('[data-section-key="measurements"]'));
        const statusLink = /** @type {HTMLElement} */ (drawerEl.querySelector('[data-section-key="status"]'));
        expect(measurementsLink.getAttribute("aria-current")).toBe("page");
        expect(statusLink.hasAttribute("aria-current")).toBe(false);

        setCurrentNav("status");
        expect(measurementsLink.hasAttribute("aria-current")).toBe(false);
        expect(statusLink.getAttribute("aria-current")).toBe("page");
    });
});
