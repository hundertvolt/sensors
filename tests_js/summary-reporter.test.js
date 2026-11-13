// npm test's closing block (SPECIFICATION.md E.10): the items its accumulator, tests_js/_summary_layout.js, files as the
// records scripts/_summary_block.py prints the block from (that emitter's layout is tests_scripts/test_summary_block.py's).
import { describe, expect, test } from "vitest";
import { createSummary, summaryRecords } from "./_summary_layout.js";

describe("summaryRecords", () => {
    test("writes the unit, the set header fields, every item kind by kind, the notes and the extra counts", () => {
        const summary = createSummary("npm test");
        summary.levels = "L0";
        summary.add("retried", "a.test.js > four", "2/3");
        summary.add("failed", "a.test.js > two", "expected 1 to be 2");
        summary.add("", "a.test.js > five");
        summary.note("n", "t");
        summary.extraCounts.push(["tests", [1, 2, 3, 4, 5, 6, 7]]);
        expect(summaryRecords(summary).split("\0")).toEqual([
            "unit", "tests", "levels", "L0",
            "item", "failed", "a.test.js > two", "expected 1 to be 2", "item", "failed", "a.test.js > five", "no verdict",
            "item", "retried", "a.test.js > four", "2/3", "note", "n", "t", "counts", "tests", "1", "2", "3", "4", "5", "6", "7", "",
        ]);
    });

    test("refuses a kind the block does not know", () => {
        const summary = createSummary("npm test");
        expect(() => summary.add("flaky", "x")).toThrow(/unknown summary kind "flaky"/u);
    });
});

// The retry this tier resolves from vitest.config.js, as a test receives it: two retries on vitest's own timeout message
// for a test or a hook (the pinned vitest's makeTimeoutError()), never on another failure (SPECIFICATION.md E.3.1).
describe("the JS tier's timeout retry", () => {
    test("retries a timed-out test or hook twice and nothing else", ({ task }) => {
        const { count, condition: resolved } = /** @type {{ count?: number, condition?: unknown }} */ (task.retry ?? {});
        expect(count).toBe(2);
        expect(resolved).toBeInstanceOf(RegExp);
        const condition = /** @type {RegExp} */ (resolved);
        const help = (/** @type {string} */ kind, /** @type {string} */ option) => `.\nIf this is a long-running ${kind}, pass a timeout value as the last argument or configure it globally with "${option}".`;
        for (const message of [`Test timed out in 20000ms${help("test", "testTimeout")}`, `Hook timed out in 10000ms${help("hook", "hookTimeout")}`, `Test timed out in 5000ms while waiting for page.click${help("test", "testTimeout")}`]) {
            expect(condition.test(message), message).toBe(true);
        }
        for (const message of ["expected 1 to be 2 // Object.is equality", "expected 'Test timed out in 5ms' to be 'x' // Object.is equality", "still booting when its test's 45000ms were up"]) {
            expect(condition.test(message), message).toBe(false);
        }
    });
});
