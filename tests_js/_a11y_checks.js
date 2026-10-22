/**
 * Deterministic accessibility rules over a rendered page, as pure DOM functions: each returns one line per problem,
 * so a test asserts an empty list. No npm dependency; colour contrast is tests_scripts/test_website_tokens.py's.
 */

// HTML's labelable elements: the only ones a <label for> can name.
const LABELABLE_TAGS = new Set(["BUTTON", "INPUT", "METER", "OUTPUT", "PROGRESS", "SELECT", "TEXTAREA"]);

/**
 * The accessible name of a control, from aria-labelledby, aria-label, its labels or its own text, in that order.
 * @param {Element} el
 * @returns {string} empty when the control has none
 */
export function accessibleName(el) {
    const labelledBy = (el.getAttribute("aria-labelledby") ?? "")
        .split(/\s+/u)
        .filter((id) => id !== "")
        .map((id) => el.ownerDocument.getElementById(id)?.textContent?.trim() ?? "")
        .filter((text) => text !== "")
        .join(" ");
    if (labelledBy !== "") {
        return labelledBy;
    }
    const ariaLabel = el.getAttribute("aria-label")?.trim() ?? "";
    if (ariaLabel !== "") {
        return ariaLabel;
    }
    const labels = "labels" in el && el.labels instanceof NodeList ? [...el.labels] : [];
    const labelText = labels.map((label) => label.textContent?.trim() ?? "").filter((text) => text !== "").join(" ");
    if (labelText !== "") {
        return labelText;
    }
    return el.tagName === "BUTTON" ? (el.textContent?.trim() ?? "") : "";
}

/**
 * Every problem the four rules find under `root`.
 * @param {ParentNode} root
 * @returns {string[]}
 */
export function accessibilityProblems(root) {
    return [...duplicateIds(root), ...danglingReferences(root), ...unnamedControls(root), ...autofillableMaskedInputs(root)];
}

/**
 * Masked inputs a browser may fill with a saved password, which the page would then send.
 * @param {ParentNode} root
 * @returns {string[]}
 */
export function autofillableMaskedInputs(root) {
    return [...root.querySelectorAll('input[type="password"]')]
        .filter((input) => input.getAttribute("autocomplete") !== "new-password")
        .map((input) => `masked input ${describe(input)} lacks autocomplete="new-password"`);
}

/**
 * Labels naming no labelable element, and aria-labelledby ids naming no element.
 * @param {ParentNode} root
 * @returns {string[]}
 */
export function danglingReferences(root) {
    const problems = [];
    for (const label of /** @type {NodeListOf<HTMLLabelElement>} */ (root.querySelectorAll("label[for]"))) {
        const target = label.ownerDocument.getElementById(label.htmlFor);
        if (target === null || !LABELABLE_TAGS.has(target.tagName) || (target instanceof HTMLInputElement && target.type === "hidden")) {
            problems.push(`label "${label.textContent?.trim() ?? ""}" names "${label.htmlFor}", which is no labelable element`);
        }
    }
    for (const el of root.querySelectorAll("[aria-labelledby]")) {
        for (const id of (el.getAttribute("aria-labelledby") ?? "").split(/\s+/u).filter((part) => part !== "")) {
            if (el.ownerDocument.getElementById(id) === null) {
                problems.push(`${describe(el)} is labelled by "${id}", which is no element`);
            }
        }
    }
    return problems;
}

/**
 * Ids used by more than one element.
 * @param {ParentNode} root
 * @returns {string[]}
 */
export function duplicateIds(root) {
    /** @type {Map<string, number>} */
    const counts = new Map();
    for (const el of root.querySelectorAll("[id]")) {
        counts.set(el.id, (counts.get(el.id) ?? 0) + 1);
    }
    return [...counts].filter(([, count]) => count > 1).map(([id, count]) => `id "${id}" is used ${count} times`);
}

/**
 * Inputs, selects and buttons with no accessible name.
 * @param {ParentNode} root
 * @returns {string[]}
 */
export function unnamedControls(root) {
    return [...root.querySelectorAll("input:not([type='hidden']), select, button")]
        .filter((control) => accessibleName(control) === "")
        .map((control) => `${describe(control)} has no accessible name`);
}

/**
 * @param {Element} el
 * @returns {string} the element as a problem line names it: its tag, id and field key
 */
function describe(el) {
    const id = el.id === "" ? "" : `#${el.id}`;
    const key = el.getAttribute("data-field-key") ?? el.getAttribute("data-sub-field-key");
    return `<${el.tagName.toLowerCase()}${id}${key === null ? "" : ` key=${key}`}>`;
}
