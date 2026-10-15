// npm test's closing block (SPECIFICATION.md E.10) through its pure layout, tests_js/_summary_layout.js;
// byte equality with the shell and Python emitters is tests_scripts/test_summary_block.py's.
import { describe, expect, test } from "vitest";
import { createSummary, renderSummary, summaryExitCode } from "./_summary_layout.js";

describe("renderSummary", () => {
    test("prints the whole block, every list empty, for a clean run", () => {
        const summary = createSummary("npm test", "abc1234");
        summary.levels = "L0";
        summary.add("passed", "a.test.js > one");
        expect(renderSummary(summary, 0)).toBe([
            "== Summary: npm test ==",
            "Commit: abc1234",
            "Levels: L0",
            "Counts (tests): passed 1 · failed 0 · skipped 0 · deselected 0 · retried 0 · recovered 0 · vacuous 0",
            "Failed: none",
            "Skipped: none",
            "Deselected: none",
            "Passed only on retry: none",
            "Recovery passes: none",
            "Notes: none",
            "Checked nothing: none",
            "Result: PASS",
            "Exit code: 0",
            "",
        ].join("\n"));
    });

    test("lists failed, skipped and retried items apart from the passes", () => {
        const summary = createSummary("npm test", "abc1234");
        summary.add("failed", "a.test.js > two", "expected 1 to be 2");
        summary.add("skipped", "a.test.js > three", "todo");
        summary.add("retried", "a.test.js > four", "2/3");
        const block = renderSummary(summary, 1);
        expect(block).toContain("passed 0 · failed 1 · skipped 1 · deselected 0 · retried 1 ·");
        expect(block).toContain("Failed:\n  - a.test.js > two: expected 1 to be 2\n");
        expect(block).toContain("Skipped:\n  - a.test.js > three: todo\n");
        expect(block).toContain("Passed only on retry:\n  - a.test.js > four (attempt 2/3)\n");
        expect(block.endsWith("Result: FAIL\nExit code: 1\n")).toBe(true);
    });

    test("lists notes after the recovery passes, never counting them or changing the result", () => {
        const summary = createSummary("npm test", "abc1234");
        summary.add("passed", "a.test.js > one");
        summary.note("a.test.js > one", "graceful wait 150.0s");
        summary.note("session (bench)");
        const block = renderSummary(summary, 0);
        expect(block).toContain("passed 1 · failed 0 · skipped 0 · deselected 0 · retried 0 · recovered 0 · vacuous 0\n");
        expect(block).toContain("Recovery passes: none\nNotes:\n  - a.test.js > one: graceful wait 150.0s\n  - session (bench)\nChecked nothing: none\n");
        expect(block.endsWith("Result: PASS\nExit code: 0\n")).toBe(true);
    });

    test("files a missing verdict as failed", () => {
        const summary = createSummary("npm test", "abc1234");
        summary.add("", "a.test.js > five");
        expect(renderSummary(summary, 1)).toContain("Failed:\n  - a.test.js > five: no verdict\n");
    });

    test("raises a passing code to 1 under a failed or vacuous item, and keeps a failure code", () => {
        for (const kind of ["failed", "vacuous"]) {
            for (const [given, printed] of [[0, 1], [3, 1], [4, 1], [1, 1], [2, 2], [130, 130]]) {
                const summary = createSummary("npm test", "abc1234");
                summary.add(kind, "x");
                expect(summaryExitCode(summary, /** @type {number} */ (given))).toBe(printed);
                expect(renderSummary(summary, /** @type {number} */ (given)).endsWith(`Exit code: ${printed}\n`)).toBe(true);
            }
        }
    });

    test("states the result each exit code stands for", () => {
        const cases = [[0, "PASS"], [1, "FAIL"], [2, "USAGE ERROR"], [3, "PASS (coverage report not rendered)"], [4, "NOT CLEAN (why)"], [130, "FAIL"]];
        for (const [code, result] of /** @type {[number, string][]} */ (cases)) {
            const summary = createSummary("npm test", "abc1234");
            summary.notCleanReason = "why";
            expect(renderSummary(summary, code).endsWith(`Result: ${result}\nExit code: ${code}\n`)).toBe(true);
        }
    });

    test("refuses a kind the block does not know", () => {
        const summary = createSummary("npm test", "abc1234");
        expect(() => summary.add("flaky", "x")).toThrow(/unknown summary kind "flaky"/u);
    });
});
