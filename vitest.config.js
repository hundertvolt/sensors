import { existsSync } from "node:fs";
import { defineConfig } from "vitest/config";
import { playwright } from "@vitest/browser-playwright";

import { runLiveBackendSmoke } from "./tests_js/_live_twin_command.js";
import {
    applyField,
    applyUnchangedFieldExpectNothingToSubmit,
    getRealCurrentValues,
    remountAndReadField,
    startLiveMatrix,
    stopLiveMatrix,
} from "./tests_js/_live_matrix_command.js";

// This dev sandbox pre-installs Chromium at a fixed path/revision and asks tools not to fetch
// their own copy (see the environment's own README); CI runners have no such path and instead
// run `npx playwright install chromium` before the test step (see .github/workflows/ci.yml's
// web-unit-tests job), so Playwright resolves its own normally-installed browser there.
const sandboxChromium = "/opt/pw-browsers/chromium";
const launchOptions = existsSync(sandboxChromium) ? { executablePath: sandboxChromium } : {};

/**
 * Vitest in real-browser mode (Playwright + Chromium, not jsdom) - the JS unit-test tier's
 * "real environment over a shim" equivalent to running Python tests under a real MicroPython
 * Unix-port interpreter (SPECIFICATION.md Part E.1). See SPECIFICATION.md Part H.8.
 */
export default defineConfig({
    test: {
        include: ["tests_js/**/*.test.js"],
        // Explicit backstop, not a fix for any known hang - mirrors the Python side's standing
        // "hanging tests are never allowed" practice (CLAUDE.md's "Code quality tooling"). Generous
        // enough to cover this suite's own longest explicit wait (5000ms, render.test.js) with
        // margin for CI/real-browser overhead.
        testTimeout: 20000,
        browser: {
            enabled: true,
            provider: playwright({ launchOptions }),
            headless: true,
            instances: [{ browser: "chromium" }],
            // Custom Commands API (server-side, real Node - not the sandboxed browser test
            // context): backs tests_js/live-backend.test.js's real-digital-twin round trip. See
            // tests_js/_live_twin_command.js's own header comment for why this needs the Commands
            // API rather than Vitest's browser-side `page` object (SPECIFICATION.md Part H.7).
            commands: {
                runLiveBackendSmoke,
                startLiveMatrix,
                stopLiveMatrix,
                getRealCurrentValues,
                applyField,
                applyUnchangedFieldExpectNothingToSubmit,
                remountAndReadField,
            },
        },
    },
});
