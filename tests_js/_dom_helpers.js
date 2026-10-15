// DOM helpers several tests_js files share: a querySelector that must find its element, and the page-shell elements
// the entry modules start on.

/**
 * querySelector with a runtime + type assertion that the element exists, so tests can chain
 * straight into `.value`/`.click()`/`.dataset` without every call site null-checking.
 * @template {Element} [T=HTMLElement]
 * @param {ParentNode} root
 * @param {string} selector
 * @returns {T}
 */
export function mustQuery(root, selector) {
    const found = root.querySelector(selector);
    if (found === null) {
        throw new Error(`Expected to find "${selector}"`);
    }
    return /** @type {T} */ (found);
}

/**
 * The page shell's elements, attached to the document (js/app.js's and js/main.js's entry points start on them).
 */
export function buildElements() {
    const appShellEl = document.createElement("div");
    const mainEl = document.createElement("main");
    const drawerEl = document.createElement("nav");
    const hamburgerEl = document.createElement("button");
    const backdropEl = document.createElement("div");
    const errorBannerEl = document.createElement("p");
    errorBannerEl.className = "error-banner";
    errorBannerEl.dataset.shown = "false";
    const deviceNameEl = document.createElement("span");
    const elements = { appShellEl, mainEl, drawerEl, hamburgerEl, backdropEl, errorBannerEl, deviceNameEl };
    for (const el of Object.values(elements)) {
        document.body.appendChild(el);
    }
    return elements;
}
