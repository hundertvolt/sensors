# e3_patch.py <src> <dst>: E3's change to tests_js/_live_matrix_command.js (kept in scratch until the before runs end).
import sys
s = open(sys.argv[1]).read()
def sub(old, new):
    global s
    assert s.count(old) == 1, old
    s = s.replace(old, new)
sub("""        livePage = await context.newPage();
        await livePage.goto(`http://${HOST}:${PORT}/`);
""", """        livePage = await context.newPage();
        // The drawer then opens without its 0.18 s slide (style.css drops only that), so a nav click does not wait the
        // slide out to find its link stable; every check of the page stays as it was.
        await livePage.emulateMedia({ reducedMotion: "reduce" });
        await livePage.goto(`http://${HOST}:${PORT}/`);
""")
sub("""/**
 * Navigates to `sectionKey` via a real drawer-open + nav-link click, exactly like a visitor would -""", """/**
 * Resolves on the first frame `locator`'s element is visible as a locator's waitFor judges it, and enabled when asked:
 * that waitFor checks at steps growing to 0.5 s, so it idled up to that long after each paint it waited for.
 * @param {import("playwright").Locator} locator one element already in the page
 * @param {{enabled?: boolean, timeout?: number}} [options] the page's default timeout when none is given
 */
async function onFrameShown(locator, { enabled = false, timeout } = {}) {
    const limit = timeout === undefined ? {} : { timeout };
    const handle = await locator.elementHandle(limit);
    try {
        await locator.page().waitForFunction(([el, wantEnabled]) => {
            if (!el.isConnected || !el.checkVisibility() || el.ownerDocument.defaultView?.getComputedStyle(el).visibility !== "visible") {
                return false;
            }
            const box = el.getBoundingClientRect();
            return box.width > 0 && box.height > 0 && (!wantEnabled || el.matches(":enabled"));
        }, /** @type {const} */ ([handle, enabled]), limit);
    } catch (err) {
        throw new Error(`${String(locator)} was not shown${enabled ? " and enabled" : ""} in time`, { cause: err });
    } finally {
        await handle.dispose();
    }
}

/**
 * Navigates to `sectionKey` via a real drawer-open + nav-link click, exactly like a visitor would -""")
sub("""    await page.locator(`[data-section-key="${sectionKey}"]`).click();
    await page.locator(".group-grid").waitFor();
}""", """    await page.locator(`[data-section-key="${sectionKey}"]`).click();
    await onFrameShown(page.locator(".group-grid"));
    await page.locator(".group-grid").waitFor();
}""")
sub("""        await card.locator(".apply-button").click();
        await card.locator(".apply-button:enabled").waitFor({ timeout: APPLY_STATUS_TIMEOUT_MS });""", """        await card.locator(".apply-button").click();
        await onFrameShown(card.locator(".apply-button"), { enabled: true, timeout: APPLY_STATUS_TIMEOUT_MS });
        await card.locator(".apply-button:enabled").waitFor({ timeout: APPLY_STATUS_TIMEOUT_MS });""")
open(sys.argv[2], "w").write(s)
