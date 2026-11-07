// Print the top complexity findings over the lint targets (rule at 1), from the worktree given as argv[2].
import path from "node:path";
import { createRequire } from "node:module";
const root = process.argv[2];
const require = createRequire(path.join(root, "package.json"));
const { ESLint } = require("eslint");
const eslint = new ESLint({ cwd: root, overrideConfig: { rules: { complexity: ["error", 1] } }, ruleFilter: ({ ruleId }) => ruleId === "complexity" });
const results = await eslint.lintFiles(["js", "tests_js", "scripts", "html", "eslint.config.js", "vitest.config.js"]);
const rows = [];
for (const r of results) for (const m of r.messages) if (m.ruleId === "complexity") { const n = Number(/complexity of (\d+)/u.exec(m.message)?.[1]); rows.push([n, `${path.relative(root, r.filePath)}:${m.line} ${m.message}`]); }
rows.sort((a, b) => b[0] - a[0]);
for (const [, t] of rows.slice(0, 6)) console.log(t);
