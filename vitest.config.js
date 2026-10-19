/**
 * Vitest in real-browser mode (Playwright + Chromium, not jsdom) - the JS unit-test tier's
 * "real environment over a shim" equivalent to running Python tests under a real MicroPython
 * Unix-port interpreter (SPECIFICATION.md Part E.1). See SPECIFICATION.md Part H.8.
 */
import { existsSync } from "node:fs";
import { chromium } from "playwright";
import { defineConfig } from "vitest/config";
import { playwright } from "@vitest/browser-playwright";

import { runLiveBackendConcurrentTabs, runLiveBackendRestartRecovery, runLiveBackendSmoke } from "./tests_js/_live_twin_command.js";
import {
    applyField,
    applyUnchangedFieldExpectNothingToSubmit,
    archiveErrcount,
    getLiveMatrixConfig,
    getRealCurrentValues,
    remountAndReadField,
    startLiveMatrix,
    stopLiveMatrix,
} from "./tests_js/_live_matrix_command.js";
import { probeLintRule } from "./tests_js/_lint_command.js";
import { probePortLock } from "./tests_js/_port_lock.js";

// The lock-pinned Playwright Chromium runs whenever it is installed; a session sandbox that cannot download it
// pre-installs one here (agent, 2026-08-21). Remove this fallback once the sandbox can run `npx playwright install chromium`.
const sandboxChromium = "/opt/pw-browsers/chromium";
const launchOptions = !existsSync(chromium.executablePath()) && existsSync(sandboxChromium) ? { executablePath: sandboxChromium } : {};

export default defineConfig({
    test: {
        include: ["tests_js/**/*.test.js"],
        // No spy or fake timer one test set reaches the next, whatever path it ended on: spies are restored
        // before each test, real timers return after each (tests_js/_test_setup.js; SPECIFICATION.md H.8).
        restoreMocks: true,
        setupFiles: ["tests_js/_test_setup.js"],
        // Every run ends with the runner summary block (SPECIFICATION.md E.10), after vitest's own report.
        reporters: ["default", "./tests_js/_summary_reporter.js"],
        // Backstop, not a fix for a known hang (CLAUDE.md "Code quality tooling": hanging tests
        // are never allowed); covers the longest explicit wait (5000ms, render.test.js) with margin.
        // @tunable l0.vitest_test_timeout_ms = 20000
        testTimeout: 20000,
        coverage: {
            // A `coverage/` directory at the repo root is importable as a namespace package and
            // shadows the real `coverage` distribution scripts/_render_coverage.py imports, so a
            // web-coverage run turned scripts/typecheck.sh red. htmlcov_js/ matches htmlcov*/.
            reportsDirectory: "htmlcov_js",
            // The v8 provider re-parses every file V8 reported coverage for as JavaScript, so the
            // JSON the site fetches at runtime (the generated definitions and mockdata/) threw a
            // rolldown parse stack per file before being dropped anyway - same report, without the noise.
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
                runLiveBackendRestartRecovery,
                getLiveMatrixConfig,
                startLiveMatrix,
                stopLiveMatrix,
                getRealCurrentValues,
                applyField,
                applyUnchangedFieldExpectNothingToSubmit,
                remountAndReadField,
                archiveErrcount,
                probeLintRule,
                probePortLock,
            },
        },
    },
});
