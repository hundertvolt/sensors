    if (kind === "errcount") {
        // TEMPORARY E1 PROBE (scratch only, never committed): eight section switches, each with a /status GET on the wire.
        /* eslint-disable */
        const log = [];
        const isStatusGet = (r) => r.method() === "GET" && r.url().endsWith("/status");
        const onReq = (r) => { if (isStatusGet(r)) { log.push({ r, start: performance.now(), end: null, failure: null }); } };
        const onFin = (r) => { const e = log.find((x) => x.r === r); if (e) { e.end = performance.now(); } };
        const onFail = (r) => { const e = log.find((x) => x.r === r); if (e) { e.end = performance.now(); e.failure = r.failure()?.errorText ?? "failed"; } };
        page.on("request", onReq);
        page.on("requestfinished", onFin);
        page.on("requestfailed", onFail);
        const waitUntil = async (check, ms, what) => { const d = performance.now() + ms; while (!check()) { if (performance.now() > d) { throw new Error(`probe: ${what} timed out`); } await sleep(1); } };
        const link = page.locator('[data-section-key="status"]');
        const switches = [];
        for (let i = 0; i < 8; i += 1) {
            const seen = log.length;
            let left;
            await waitUntil(() => { left = log.slice(seen).find((e) => e.end === null); return left !== undefined; }, 10000, "a GET on the wire");
            const tClick = performance.now();
            await link.dispatchEvent("click");
            const tClicked = performance.now();
            const idx = log.indexOf(left);
            await waitUntil(() => log.length > idx + 1, 20000, "the next section's first GET");
            const next = log[idx + 1];
            await waitUntil(() => left.end !== null, 20000, "the left GET's end");
            switches.push({ i, leftDurMs: +(left.end - left.start).toFixed(1), clickAfterStartMs: +(tClick - left.start).toFixed(1), clickDispatchMs: +(tClicked - tClick).toFixed(1), leftEndAfterClickMs: +(left.end - tClick).toFixed(1), leftFailure: left.failure, nextStartAfterClickMs: +(next.start - tClick).toFixed(1) });
        }
        page.off("request", onReq);
        page.off("requestfinished", onFin);
        page.off("requestfailed", onFail);
        await sleep(4500);
        const rows = page.locator(`[data-group-key="${groupKey}"] .errcount-row`);
        await rows.first().waitFor({ state: "attached" });
        const texts = () => rows.evaluateAll((elements) => elements.map((row) => `${row.querySelector(".errcount-row-name")?.textContent ?? "?"}: ${row.querySelector(".errcount-row-count")?.textContent ?? "?"}`));
        const errcountRows = await texts();
        const direct = await (await fetch(`http://${HOST}:${PORT}/status`)).json();
        writeFileSync(process.env.E1_PROBE_OUT ?? "/dev/null", `${JSON.stringify({ switches, errcountRows, webserver: direct.errcount?.WEBSERVER ?? null }, null, 1)}\n`);
        /* eslint-enable */
        return { ...read, errcountRows };
    }
