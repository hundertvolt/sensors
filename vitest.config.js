import { existsSync } from "node:fs";
import { defineConfig } from "vitest/config";
import { playwright } from "@vitest/browser-playwright";

// This dev sandbox pre-installs Chromium at a fixed path/revision and asks tools not to fetch
// their own copy (see the environment's own README); CI runners have no such path and instead
// run `npx playwright install chromium` before the test step (see .github/workflows/ci.yml's
// web-unit-tests job), so Playwright resolves its own normally-installed browser there.
const sandboxChromium = "/opt/pw-browsers/chromium";
const launchOptions = existsSync(sandboxChromium) ? { executablePath: sandboxChromium } : {};

/**
 * Vitest in real-browser mode (Playwright + Chromium, not jsdom) - the JS unit-test tier's
 * "real environment over a shim" equivalent to running Python tests under a real MicroPython
 * Unix-port interpreter (SPECIFICATION.md Part E.1). See WEBSITE_PLAN.md §6.
 */
export default defineConfig({
    test: {
        include: ["tests_js/**/*.test.js"],
        browser: {
            enabled: true,
            provider: playwright({ launchOptions }),
            headless: true,
            instances: [{ browser: "chromium" }],
        },
    },
});
