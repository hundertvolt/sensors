/**
 * Hamburger + slide-in drawer nav (WEBSITE_PLAN.md §10 session 2 decision: drawer, section links
 * only). Single-page shell - selecting a link never reloads the page, it just calls back into
 * app.js to swap the rendered section.
 */

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
    drawerEl.replaceChildren();

    const heading = document.createElement("div");
    heading.className = "nav-drawer-heading";
    heading.textContent = defs.device.displayName;
    drawerEl.appendChild(heading);

    /** @type {Map<string, HTMLButtonElement>} */
    const linksByKey = new Map();

    for (const section of defs.sections) {
        const link = document.createElement("button");
        link.type = "button";
        link.className = "nav-link";
        link.textContent = section.label;
        link.addEventListener("click", () => {
            closeDrawer();
            onSelect(section.key);
        });
        drawerEl.appendChild(link);
        linksByKey.set(section.key, link);
    }

    const openDrawer = () => {
        appShellEl.classList.add("nav-open");
        hamburgerEl.setAttribute("aria-expanded", "true");
    };
    const closeDrawer = () => {
        appShellEl.classList.remove("nav-open");
        hamburgerEl.setAttribute("aria-expanded", "false");
    };

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
        for (const [key, link] of linksByKey) {
            if (key === sectionKey) {
                link.setAttribute("aria-current", "page");
            } else {
                link.removeAttribute("aria-current");
            }
        }
    };
}
