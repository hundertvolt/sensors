/**
 * Nav controller: drawer open/close state and section-select dispatch. Builds no DOM itself -
 * see SPECIFICATION.md Part H.3 for the full mechanics/visual split this file follows.
 */

import { buildNavDrawer } from "./templates.js";

/** @typedef {import("./definitions.js").SiteDefinitions} SiteDefinitions */

/**
 * @param {{
 *   defs: SiteDefinitions,
 *   appShellEl: HTMLElement,
 *   drawerEl: HTMLElement,
 *   hamburgerEl: HTMLElement,
 *   backdropEl: HTMLElement,
 *   onSelect: (sectionKey: string) => void,
 * }} options
 * @returns {(sectionKey: string) => void} call to update which nav link is marked current.
 */
export function initNav({ defs, appShellEl, drawerEl, hamburgerEl, backdropEl, onSelect }) {
    buildNavDrawer(defs, drawerEl);

    const closeDrawer = () => {
        appShellEl.classList.remove("nav-open");
        hamburgerEl.setAttribute("aria-expanded", "false");
    };
    const openDrawer = () => {
        appShellEl.classList.add("nav-open");
        hamburgerEl.setAttribute("aria-expanded", "true");
    };

    for (const link of /** @type {NodeListOf<HTMLElement>} */ (drawerEl.querySelectorAll("[data-section-key]"))) {
        const sectionKey = link.dataset.sectionKey;
        if (sectionKey === undefined) {
            continue; // defensive only: buildNavDrawer() always sets this on every link it builds
        }
        link.addEventListener("click", () => {
            closeDrawer();
            onSelect(sectionKey);
        });
    }

    hamburgerEl.addEventListener("click", () => {
        if (appShellEl.classList.contains("nav-open")) {
            closeDrawer();
        } else {
            openDrawer();
        }
    });
    backdropEl.addEventListener("click", closeDrawer);
    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape") {
            closeDrawer();
        }
    });

    return (sectionKey) => {
        for (const link of /** @type {NodeListOf<HTMLElement>} */ (drawerEl.querySelectorAll("[data-section-key]"))) {
            if (link.dataset.sectionKey === sectionKey) {
                link.setAttribute("aria-current", "page");
            } else {
                link.removeAttribute("aria-current");
            }
        }
    };
}
