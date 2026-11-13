// Server-side Vitest Commands API module backing tests_js/lint-ceilings.test.js: runs ESLint's Node
// API, which the browser page cannot reach, over every file the complexity ceilings apply to
// (SPECIFICATION.md H.8).

import path from "node:path";
import { fileURLToPath } from "node:url";
import { ESLint } from "eslint";

const REPO_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
// package.json's "lint" targets: every block of eslint.config.js spreads the ceilings into its rules.
const LINT_TARGETS = ["js", "tests_js", "scripts", "html", "eslint.config.js", "vitest.config.js"];

/**
 * The number of findings one ceiling rule reports at `value` over every linted file.
 * @param {unknown} _context Vitest's injected command context (unused)
 * @param {{rule: string, value: number}} args
 * @returns {Promise<number>}
 */
export async function probeLintRule(_context, { rule, value }) {
    const eslint = new ESLint({
        cwd: REPO_ROOT,
        overrideConfig: { rules: { [rule]: ["error", value] } },
        ruleFilter: ({ ruleId }) => ruleId === rule,
    });
    const results = await eslint.lintFiles(LINT_TARGETS);
    // A file ESLint cannot parse reports no rule at all, so it would read as "no finding" here.
    const fatal = results.filter((result) => result.messages.some((message) => message.fatal === true));
    if (fatal.length > 0) {
        throw new Error(`ESLint could not parse ${fatal.map((result) => result.filePath).join(", ")}`);
    }
    return results.reduce((sum, result) => sum + result.messages.filter((message) => message.ruleId === rule).length, 0);
}
