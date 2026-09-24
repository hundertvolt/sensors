import { existsSync } from "node:fs";
import { defineConfig } from "vitest/config";
import { playwright } from "@vitest/browser-playwright";

import { runLiveBackendConcurrentTabs, runLiveBackendSmoke } from "./tests_js/_live_twin_command.js";
import {
    applyField,
    applyUnchangedFieldExpectNothingToSubmit,
    getRealCurrentValues,
    remountAndReadField,
    startLiveMatrix,
    stopLiveMatrix,
} from "./tests_js/_live_matrix_command.js";

// The dev sandbox pre-installs Chromium at this fixed path; CI runners lack it and run
// `npx playwright install chromium` first (ci.yml's web-unit-tests job), so Playwright
// resolves its own install there.
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
        // Backstop, not a fix for a known hang (CLAUDE.md "Code quality tooling": hanging tests
        // are never allowed); covers the longest explicit wait (5000ms, render.test.js) with margin.
        testTimeout: 20000,
        coverage: {
            // A `coverage/` directory at the repo root is importable as a namespace package and
            // shadows the real `coverage` distribution scripts/_render_coverage.py imports, so a
            // web-coverage run turned scripts/typecheck.sh red. htmlcov_js/ matches htmlcov*/.
            reportsDirectory: "htmlcov_js",
            // The v8 provider re-parses every file V8 reported coverage for as JavaScript, so the
            // JSON the site fetches at runtime (html/definitions/, mockdata/) threw a rolldown
            // parse stack per file before being dropped anyway - same report, without the noise.
            exclude: ["**/*.json"],
        },
        browser: {
            enabled: true,
            provider: playwright({ launchOptions }),
            headless: true,
            instances: [{ browser: "chromium" }],
            // Commands API (server-side Node, not the browser context) backs the live-twin tests;
            // why not Vitest's `page` object: tests_js/_live_twin_command.js, SPEC Part H.7.
            commands: {
                runLiveBackendSmoke,
                runLiveBackendConcurrentTabs,
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
