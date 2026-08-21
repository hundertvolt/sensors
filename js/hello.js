/** Placeholder module proving the js/ CI pipeline (lint, typecheck, browser test) end to end. */

/**
 * Render a greeting into the given element and return the greeting text.
 * @param {HTMLElement} target
 * @param {string} deviceName
 * @returns {string}
 */
export function renderHello(target, deviceName) {
    const greeting = `Hello, ${deviceName}!`;
    target.textContent = greeting;
    return greeting;
}
