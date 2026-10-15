// Vitest reporter that closes every npm test run with the runner summary block (SPECIFICATION.md E.10),
// after vitest's own report, through tests_js/_summary_layout.js. Node-context (git, stdout); the hook
// names and result shapes were read from the installed vitest's own type declarations.
import { execFileSync } from "node:child_process";
import { createSummary, renderSummary, summaryExitCode } from "./_summary_layout.js";

/** @typedef {import("vitest/node").TestCase} TestCase */
/** @typedef {import("vitest/node").TestModule} TestModule */
/** @typedef {import("vitest/node").SerializedError} SerializedError */
/** @typedef {import("vitest/node").TestRunEndReason} TestRunEndReason */
/** @typedef {import("./_summary_layout.js").Summary} Summary */

/** @param {string[]} args @returns {string | null} */
function gitOutput(args) {
    try {
        return execFileSync("git", args, { encoding: "utf8", stdio: ["ignore", "pipe", "ignore"] });
    } catch {
        return null;
    }
}

/** The Commit: value, derived as scripts/_summary_block.py derives it; an unreadable status reads as dirty. */
function commitLabel() {
    const sha = (gitOutput(["rev-parse", "--short", "HEAD"]) ?? "").trim();
    if (sha === "") {
        return "unknown";
    }
    const porcelain = gitOutput(["status", "--porcelain"]);
    return porcelain === null || porcelain.trim() !== "" ? `${sha} (uncommitted changes)` : sha;
}

/** @param {string | undefined} message */
function firstLine(message) {
    return (message ?? "").split("\n")[0]?.trim() || "no message";
}

/** @param {TestCase} testCase */
function retryAttempts(testCase) {
    const { retry } = testCase.options;
    const allowed = typeof retry === "number" ? retry : retry?.count ?? 0;
    const used = testCase.diagnostic()?.retryCount ?? 0;
    return `${used + 1}/${Math.max(allowed, used) + 1}`;
}

/** @param {TestCase} testCase @param {string | undefined} note */
function skipReason(testCase, note) {
    if (note) {
        return note;
    }
    const { mode } = testCase.options;
    if (mode === "todo" || mode === "skip") {
        return mode;
    }
    return "not selected (.only or a name filter)";
}

/** One case filed by its own result; a case with no result yet (an interrupted run) has no verdict. @param {Summary} summary @param {TestCase} testCase */
function fileCase(summary, testCase) {
    const name = `${testCase.module.relativeModuleId} > ${testCase.fullName}`;
    const result = testCase.result();
    if (result.state === "passed") {
        // A pass that needed a retry is reported apart from the passes, never folded into them.
        if (testCase.diagnostic()?.flaky) {
            summary.add("retried", name, retryAttempts(testCase));
        } else {
            summary.add("passed", name);
        }
    } else if (result.state === "failed") {
        summary.add("failed", name, firstLine(result.errors[0]?.message));
    } else if (result.state === "skipped") {
        summary.add("skipped", name, skipReason(testCase, result.note));
    } else {
        summary.add("", name);
    }
}

export default class SummaryReporter {
    /**
     * @param {ReadonlyArray<TestModule>} testModules
     * @param {ReadonlyArray<SerializedError>} unhandledErrors
     * @param {TestRunEndReason} reason
     */
    // eslint-disable-next-line class-methods-use-this -- vitest calls reporter hooks as methods of the instance it builds
    onTestRunEnd(testModules, unhandledErrors, reason) {
        const summary = createSummary("npm test", commitLabel());
        summary.levels = "L0";
        let cases = 0;
        for (const testModule of testModules) {
            for (const error of testModule.errors()) {
                summary.add("failed", testModule.relativeModuleId, `module error: ${firstLine(error.message)}`);
            }
            // A suite hook (beforeAll/afterAll) failing leaves every case of it passed; the suite carries it.
            for (const suite of testModule.children.allSuites()) {
                for (const error of suite.errors()) {
                    summary.add("failed", `${testModule.relativeModuleId} > ${suite.fullName}`, `suite error: ${firstLine(error.message)}`);
                }
            }
            for (const testCase of testModule.children.allTests()) {
                cases += 1;
                fileCase(summary, testCase);
            }
        }
        for (const error of unhandledErrors) {
            summary.add("failed", "unhandled error", firstLine(error.message));
        }
        if (reason === "interrupted") {
            summary.add("failed", "vitest run", "interrupted before every test reported");
        }
        if (cases === 0) {
            summary.add("vacuous", "npm test: no test case ran");
        }
        // A failing status with nothing filed failed still names itself rather than reading "Failed: none";
        // a verdict filed failed fails the run too, so `Exit code:` is the status the process ends with.
        const vitestCode = Number(process.exitCode ?? 0);
        if (vitestCode !== 0 && (summary.items.get("failed")?.length ?? 0) === 0) {
            summary.add("failed", "vitest run", `exit code ${vitestCode} with no failing test recorded`);
        }
        const exitCode = summaryExitCode(summary, vitestCode);
        process.exitCode = exitCode;
        process.stdout.write(renderSummary(summary, exitCode));
    }
}
