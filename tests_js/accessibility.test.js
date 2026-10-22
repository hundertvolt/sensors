// Every device's page, through the production entry against its composed mock: each section has unique ids, bound
// labels, a name on every control and no autofillable masked input, and the closed drawer is inert with focus handled.
import { afterEach, describe, expect, it, vi } from "vitest";
import { userEvent } from "vitest/browser";
import pageSource from "../html/index.html?raw";
import samples from "../mockdata/samples.json";
import { startApp } from "../js/main.js";
import { composeMockData, installMockFetch } from "../js/mock-server.js";
import { accessibilityProblems, autofillableMaskedInputs, danglingReferences, duplicateIds, unnamedControls } from "./_a11y_checks.js";
import { DEVICE_IDS, GENERATED_DEFINITIONS } from "./_generated_definitions.js";

/** @typedef {import("../js/definitions.js").SiteDefinitions} SiteDefinitions */
/** @typedef {import("../js/definitions.js").Section} Section */

const SAMPLES = /** @type {import("../js/definitions.js").MockSamples} */ (samples);
// @tunable l0.section_render_wait_ms = 5000
const SECTION_RENDER_WAIT_MS = 5000;

/**
 * @param {() => boolean} check
 */
async function waitFor(check) {
    const start = Date.now();
    while (!check()) {
        if (Date.now() - start > SECTION_RENDER_WAIT_MS) {
            throw new Error(`condition not met within ${SECTION_RENDER_WAIT_MS}ms`);
        }
        // eslint-disable-next-line no-await-in-loop -- each poll waits for the previous one
        await new Promise((resolve) => {
            setTimeout(resolve, 20);
        });
    }
}

/**
 * @param {ParentNode} root
 * @param {string} selector
 * @returns {HTMLElement}
 */
function mustQuery(root, selector) {
    const found = root.querySelector(selector);
    if (!(found instanceof HTMLElement)) {
        throw new Error(`Expected to find "${selector}"`);
    }
    return found;
}

describe("the accessibility checks", () => {
    /** @type {HTMLElement | undefined} */
    let fixture;

    afterEach(() => {
        fixture?.remove();
        fixture = undefined;
    });

    /**
     * @param {(root: HTMLElement) => void} build
     * @returns {HTMLElement}
     */
    function mountFixture(build) {
        fixture = document.createElement("div");
        build(fixture);
        document.body.appendChild(fixture);
        return fixture;
    }

    it("find a repeated id, a label naming nothing, a label naming a span and a labelledby naming nothing", () => {
        const root = mountFixture((el) => {
            const first = document.createElement("input");
            first.id = "fixture-twice";
            const second = document.createElement("select");
            second.id = "fixture-twice";
            const span = document.createElement("span");
            span.id = "fixture-span";
            const toNothing = document.createElement("label");
            toNothing.htmlFor = "fixture-missing";
            const toSpan = document.createElement("label");
            toSpan.htmlFor = "fixture-span";
            const value = document.createElement("span");
            value.setAttribute("aria-labelledby", "fixture-gone");
            el.append(first, second, span, toNothing, toSpan, value);
        });
        expect(duplicateIds(root)).toEqual(['id "fixture-twice" is used 2 times']);
        expect(danglingReferences(root)).toHaveLength(3);
    });

    it("find a button, an input and a select with no name, and accept each way a control can have one", () => {
        const root = mountFixture((el) => {
            const bare = [document.createElement("button"), document.createElement("input"), document.createElement("select")];
            const byText = document.createElement("button");
            byText.textContent = "Apply";
            const byAria = document.createElement("button");
            byAria.setAttribute("aria-label", "Open navigation");
            const byFor = document.createElement("input");
            byFor.id = "fixture-for";
            const forLabel = document.createElement("label");
            forLabel.htmlFor = "fixture-for";
            forLabel.textContent = "Hostname";
            const wrapping = document.createElement("label");
            wrapping.textContent = "Red";
            wrapping.appendChild(document.createElement("input"));
            const named = document.createElement("span");
            named.id = "fixture-name";
            named.textContent = "Reset Reason";
            const byLabelledBy = document.createElement("button");
            byLabelledBy.setAttribute("aria-labelledby", "fixture-name");
            el.append(...bare, byText, byAria, byFor, forLabel, wrapping, named, byLabelledBy);
        });
        expect(unnamedControls(root)).toEqual(["<button> has no accessible name", "<input> has no accessible name", "<select> has no accessible name"]);
    });

    it("find a masked input without autocomplete=new-password", () => {
        const root = mountFixture((el) => {
            const bare = document.createElement("input");
            bare.type = "password";
            bare.dataset.fieldKey = "PW";
            const guarded = document.createElement("input");
            guarded.type = "password";
            guarded.setAttribute("autocomplete", "new-password");
            el.append(bare, guarded);
        });
        expect(autofillableMaskedInputs(root)).toEqual(['masked input <input key=PW> lacks autocomplete="new-password"']);
    });
});

describe.each(DEVICE_IDS)("%s's page", (device) => {
    const defs = /** @type {SiteDefinitions} */ (GENERATED_DEFINITIONS.get(device));
    const originalUrl = window.location.href;
    /** @type {HTMLElement | undefined} */
    let page;
    /** @type {(() => void) | undefined} */
    let stop;
    /** @type {(() => void) | undefined} */
    let uninstall;

    afterEach(() => {
        stop?.();
        stop = undefined;
        uninstall?.();
        uninstall = undefined;
        page?.remove();
        page = undefined;
        window.history.replaceState(null, "", originalUrl);
    });

    /**
     * Mounts html/index.html's shell with the device's definitions inlined, as a device build serves it, and starts
     * the production entry on `section` against the device's composed mock.
     * @param {Section} section
     * @returns {Promise<HTMLElement>}
     */
    async function openPage(section) {
        const shell = new DOMParser().parseFromString(pageSource, "text/html").querySelector(".app-shell");
        if (shell === null) {
            throw new Error("html/index.html has no .app-shell");
        }
        const root = document.createElement("div");
        page = root;
        const inlined = document.createElement("script");
        inlined.type = "application/json";
        inlined.id = "inlined-definitions";
        inlined.textContent = JSON.stringify(defs);
        root.append(document.importNode(shell, true), inlined);
        document.body.appendChild(root);
        window.history.replaceState(null, "", `#${section.key}`);
        uninstall = installMockFetch(defs, composeMockData(defs, SAMPLES));
        stop = await startApp({
            appShellEl: mustQuery(root, "#app-shell"),
            mainEl: mustQuery(root, "#app-main"),
            drawerEl: mustQuery(root, "#nav-drawer"),
            hamburgerEl: mustQuery(root, "#hamburger-button"),
            backdropEl: mustQuery(root, "#nav-backdrop"),
            errorBannerEl: mustQuery(root, "#error-banner"),
            deviceNameEl: mustQuery(root, "#device-name"),
            inlinedDefinitionsEl: inlined,
        });
        const main = mustQuery(root, "#app-main");
        await waitFor(() => main.querySelector(".section-heading")?.textContent === section.label && main.querySelectorAll("[data-group-key]").length === section.groups.length);
        return root;
    }

    it.each(defs.sections.map((section) => /** @type {[string, Section]} */ ([section.key, section])))(
        "%s section: unique ids, bound labels, a name on every control, no autofillable masked input",
        async (_key, section) => {
            const consoleError = vi.spyOn(console, "error");
            const root = await openPage(section);
            expect(accessibilityProblems(root)).toEqual([]);
            expect(mustQuery(root, "#app-main .error-banner").dataset.shown).toBe("false");
            expect(consoleError).not.toHaveBeenCalled();
        },
    );

    it("keeps the closed drawer inert, focuses its first link on open and returns the focus on close", async () => {
        const root = await openPage(/** @type {Section} */ (defs.sections.find((section) => section.key === defs.landingSection)));
        const drawer = mustQuery(root, "#nav-drawer");
        const hamburger = mustQuery(root, "#hamburger-button");
        expect(drawer.inert).toBe(true);

        hamburger.click();
        expect(drawer.inert).toBe(false);
        expect(document.activeElement).toBe(drawer.querySelector("[data-section-key]"));
        expect(hamburger.getAttribute("aria-label")).toBe("Close navigation");
        expect(accessibilityProblems(root)).toEqual([]);

        await userEvent.keyboard("{Escape}");
        expect(drawer.inert).toBe(true);
        expect(document.activeElement).toBe(hamburger);
        expect(hamburger.getAttribute("aria-label")).toBe("Open navigation");

        hamburger.click();
        mustQuery(drawer, "[data-section-key]").click();
        expect(drawer.inert).toBe(true);
        expect(document.activeElement).toBe(hamburger);
    });
});
