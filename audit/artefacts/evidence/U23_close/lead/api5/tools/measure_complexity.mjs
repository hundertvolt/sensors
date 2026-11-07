// measure_complexity.mjs <repo>: lists every function's complexity over lint-ceilings' targets, highest first.
import { createRequire } from "node:module";
import path from "node:path";
const repo = path.resolve(process.argv[2]);
const { ESLint } = createRequire(path.join(repo, "package.json"))("eslint");
const eslint = new ESLint({ cwd: repo, overrideConfig: { rules: { complexity: ["error", 0] } }, ruleFilter: ({ ruleId }) => ruleId === "complexity" });
const results = await eslint.lintFiles(["js", "tests_js", "scripts", "html", "eslint.config.js", "vitest.config.js"]);
const rows = [];
for (const r of results) for (const m of r.messages) {
  if (m.fatal) { console.log("FATAL", r.filePath); process.exitCode = 1; }
  if (m.ruleId !== "complexity") continue;
  const n = Number(/complexity of (\d+)/u.exec(m.message)[1]);
  rows.push([n, `${path.relative(repo, r.filePath)}:${m.line}`, m.message]);
}
rows.sort((a, b) => b[0] - a[0]);
for (const row of rows.slice(0, 6)) console.log(row.join("  "));
