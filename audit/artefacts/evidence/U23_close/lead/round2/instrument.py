# instrument.py <src> <dst>: a TEMPORARY traced copy of tests_js/_live_matrix_command.js for the E3 split measurement
# (scratch only, never committed): JSON lines to $E3_TRACE for every command, its steps and every page request.
import re, sys
s = open(sys.argv[1]).read()
def sub(old, new, count=1):
    global s
    assert s.count(old) == count, (old, s.count(old))
    s = s.replace(old, new)
sub('import { existsSync, rmSync, writeFileSync } from "node:fs";', 'import { appendFileSync, existsSync, rmSync, writeFileSync } from "node:fs";')
sub('/** @type {WeakMap<import("node:child_process").ChildProcess, Error>} */\nconst spawnErrors = new WeakMap();',
    '/** @type {WeakMap<import("node:child_process").ChildProcess, Error>} */\nconst spawnErrors = new WeakMap();\n'
    '/* eslint-disable */\nconst TRACE = process.env.E3_TRACE ?? "";\nconst reqIds = new WeakMap(); let reqN = 0;\n'
    'function trace(ev, extra = {}) { if (TRACE) { appendFileSync(TRACE, `${JSON.stringify({ t: +performance.now().toFixed(1), ev, ...extra })}\\n`); } }\n'
    'function traced(name, fn) { return async (...args) => { trace("cmd0", { c: name, a: args[1]?.fieldKey ?? args[1] }); try { return await fn(...args); } finally { trace("cmd1", { c: name }); } }; }\n/* eslint-enable */')
sub('        livePage = await context.newPage();\n        await livePage.goto(',
    '        livePage = await context.newPage();\n'
    '        livePage.on("request", (r) => { reqN += 1; reqIds.set(r, reqN); trace("req", { id: reqN, m: r.method(), u: new URL(r.url()).pathname }); });\n'
    '        livePage.on("requestfinished", (r) => trace("fin", { id: reqIds.get(r) }));\n'
    '        livePage.on("requestfailed", (r) => trace("fail", { id: reqIds.get(r), e: r.failure()?.errorText }));\n'
    '        await livePage.goto(')
sub('    await page.locator(`[data-section-key="${sectionKey}"]`).click();\n    await page.locator(".group-grid").waitFor();\n',
    '    trace("nav_open");\n    await page.locator(`[data-section-key="${sectionKey}"]`).click();\n    trace("nav_clicked");\n    await page.locator(".group-grid").waitFor();\n    trace("nav_grid");\n')
sub('        await card.locator(".apply-button").click();\n        await card.locator(".apply-button:enabled").waitFor({ timeout: APPLY_STATUS_TIMEOUT_MS });\n',
    '        trace("ap_click0");\n        await card.locator(".apply-button").click();\n        trace("ap_click1");\n        await card.locator(".apply-button:enabled").waitFor({ timeout: APPLY_STATUS_TIMEOUT_MS });\n        trace("ap_done");\n')
for name in ["getRealCurrentValues", "applyField", "applyUnchangedFieldExpectNothingToSubmit", "remountAndReadField", "startLiveMatrix", "stopLiveMatrix", "archiveErrcount"]:
    sub(f"export async function {name}(", f"async function {name}Inner(")
    s += f'\nexport const {name} = traced("{name}", {name}Inner);\n'
# card-ready marks after each "await card.waitFor();"
s = s.replace("    await card.waitFor();\n", '    await card.waitFor();\n    trace("card");\n')
open(sys.argv[2], "w").write(s)
