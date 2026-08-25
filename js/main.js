/**
 * Real production entry point (WEBSITE_PLAN.md §10 item 4). Unlike js/app.js (prototype-only:
 * mock fetch, `?device=` switch, dev-server-relative paths), this installs no mock and targets
 * exactly one device - the real backend is reached at plain root-relative REST paths, and the
 * device is fixed by which definitions file the build staged as `definitions.json` (see
 * scripts/build_website.sh), not by a runtime switch. Staged into the frozen build as `app.js` -
 * see build_website.sh's own comment for why html/index.html needs no change to pick this up.
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
