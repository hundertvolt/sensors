/**
 * Real production entry point - no mock, one build-fixed device, no `?device=` switch.
 * Staged into the frozen build as `app.js` (js/app.js is the prototype-only entry).
 * See SPECIFICATION.md Part H.2.
 */

import { loadDefinitions } from "./definitions.js";
import { initNav } from "./nav.js";
import { renderSection } from "./render.js";

/** @typedef {import("./definitions.js").SiteDefinitions} SiteDefinitions */

/**
 * @param {{
 *   appShellEl: HTMLElement, mainEl: HTMLElement, drawerEl: HTMLElement,
 *   hamburgerEl: HTMLElement, backdropEl: HTMLElement, errorBannerEl: HTMLElement,
 *   deviceNameEl: HTMLElement, inlinedDefinitionsEl?: HTMLElement | null,
 * }} elements
 */
export async function startApp(elements) {
    const { appShellEl, mainEl, drawerEl, hamburgerEl, backdropEl, errorBannerEl, deviceNameEl, inlinedDefinitionsEl } = elements;

    /** @type {SiteDefinitions} */
    let defs;
    try {
        defs = await loadDefinitions("definitions.json", inlinedDefinitionsEl);
    } catch (error) {
        errorBannerEl.textContent = `Could not load definitions: ${String(error)}`;
        errorBannerEl.classList.remove("hidden");
        return;
    }

    deviceNameEl.textContent = defs.device.displayName;

    let stopCurrentSection = () => {};
    const setCurrentNav = initNav({
        defs,
        appShellEl,
        drawerEl,
        hamburgerEl,
        backdropEl,
        onSelect: (sectionKey) => selectSection(sectionKey),
    });

    /** @param {string} sectionKey */
    function selectSection(sectionKey) {
        const section = defs.sections.find((/** @type {SiteDefinitions["sections"][number]} */ entry) => entry.key === sectionKey);
        if (section === undefined) {
            // Defensive only: every real sectionKey traces back to defs.sections itself (a nav
            // click, or defs.landingSection, which validateDefinitions() already requires to
            // match a real section key), so this can't currently fire.
            return;
        }
        stopCurrentSection();
        setCurrentNav(sectionKey);
        stopCurrentSection = renderSection(defs, section, mainEl);
    }

    selectSection(defs.landingSection);
}
