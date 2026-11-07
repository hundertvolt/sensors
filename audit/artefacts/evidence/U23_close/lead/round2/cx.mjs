// cx.mjs: every function's complexity above a floor over the lint targets, as the ceiling probe counts it.
import { ESLint } from "eslint";
const eslint = new ESLint({ cwd: process.cwd(), overrideConfig: { rules: { complexity: ["error", Number(process.argv[2])] } }, ruleFilter: ({ ruleId }) => ruleId === "complexity" });
const results = await eslint.lintFiles(["js", "tests_js", "scripts", "html", "eslint.config.js", "vitest.config.js"]);
for (const r of results) for (const m of r.messages) if (m.ruleId === "complexity") console.log(`${r.filePath.replace(process.cwd() + "/", "")}:${m.line} ${m.message}`);
