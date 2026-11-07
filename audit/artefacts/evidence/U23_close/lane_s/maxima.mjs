// Per-file maxima of the four ESLint ceiling rules (lane S report); run from the worktree root.
import { ESLint } from "eslint";
const files = process.argv.slice(2);
const rules = { complexity: 1, "max-depth": 0, "max-nested-callbacks": 0 };
for (const [rule, value] of Object.entries(rules)) {
    const eslint = new ESLint({ cwd: process.cwd(), overrideConfig: { rules: { [rule]: ["error", value] } }, ruleFilter: ({ ruleId }) => ruleId === rule });
    const results = await eslint.lintFiles(files);
    for (const r of results) {
        const nums = r.messages.filter((m) => m.ruleId === rule).map((m) => Number((/\((\d+)\)|maximum allowed is \d+|(\d+)\.\s*Maximum/.exec(m.message) ?? [])[1] ?? (/(\d+)/.exec(m.message.replace(/Maximum.*$/, "")) ?? [])[1]));
        console.log(rule, r.filePath.replace(process.cwd() + "/", ""), Math.max(0, ...nums.filter((n) => !Number.isNaN(n))));
    }
}
