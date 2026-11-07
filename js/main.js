/**
 * Real production entry point - no mock, one build-fixed device, no `?device=` switch.
 * Staged into the frozen build as `app.js` (js/app.js is the prototype-only entry).
 * See SPECIFICATION.md Part H.2.
 */

import { loadDefinitions } from "./definitions.js";
import { showBanner } from "./render.js";
import { historyOf, startShell, visibilityOf } from "./shell.js";

/** @typedef {import("./definitions.js").SiteDefinitions} SiteDefinitions */

/**
 * @param {{
 *   appShellEl: HTMLElement, mainEl: HTMLElement, drawerEl: HTMLElement,
 *   hamburgerEl: HTMLElement, backdropEl: HTMLElement, errorBannerEl: HTMLElement,
 *   deviceNameEl: HTMLElement, inlinedDefinitionsEl?: HTMLElement | null,
 * }} elements
 * @returns {Promise<() => void>} stop: ends everything the page started.
 */
export async function startApp(elements) {
    const { appShellEl, mainEl, drawerEl, hamburgerEl, backdropEl, errorBannerEl, deviceNameEl, inlinedDefinitionsEl } = elements;

    /** @type {SiteDefinitions} */
    let defs;
    try {
        defs = await loadDefinitions("definitions.json", inlinedDefinitionsEl);
    } catch (error) {
        showBanner(errorBannerEl, `Could not load definitions: ${String(error)}`);
        return () => { /* nothing was started */ };
    }

    deviceNameEl.textContent = defs.device.displayName;
    return startShell({
        defs,
        elements: { appShellEl, mainEl, drawerEl, hamburgerEl, backdropEl },
        keyTarget: document,
        visibility: visibilityOf(document),
        history: historyOf(window),
        reload: () => window.location.reload(),
    });
}
