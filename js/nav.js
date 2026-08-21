/**
 * Nav controller (WEBSITE_PLAN.md §12): drawer open/close state and section-select dispatch. It
 * builds no DOM itself - `js/templates.js`'s `buildNavDrawer()` owns the drawer's markup/order; this
 * file only locates the resulting `[data-section-key]` links to wire the real (app-level) select
 * behavior, and toggles the `nav-open` class that `html/style.css` uses to show/hide the drawer.
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
            continue;
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
