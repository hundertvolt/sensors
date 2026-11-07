// Counts TCP connections per page load through a logging proxy and records each connection's requests.
import net from "node:net";
import { chromium } from "playwright";
const TWIN = 19431, PROXY = 19432;
const conns = [];
const server = net.createServer((client) => {
    const rec = { id: conns.length, firstLines: [], bytes: 0 };
    conns.push(rec);
    const up = net.connect(TWIN, "127.0.0.1");
    client.on("data", (d) => { rec.bytes += d.length; const s = d.toString("latin1"); for (const m of s.matchAll(/^(GET|PUT|POST|HEAD) [^\r\n]+/gm)) rec.firstLines.push(m[0]); up.write(d); });
    up.on("data", (d) => client.write(d));
    client.on("close", () => up.destroy()); up.on("close", () => client.destroy());
    client.on("error", () => {}); up.on("error", () => {});
});
await new Promise((r) => server.listen(PROXY, "127.0.0.1", r));
const browser = await chromium.launch({ executablePath: "/opt/pw-browsers/chromium-1194/chrome-linux/chrome" });
for (const vp of [{ width: 1280, height: 800 }, { width: 390, height: 844 }]) {
    conns.length = 0;
    const ctx = await browser.newContext({ viewport: vp });
    const page = await ctx.newPage();
    const reqs = [];
    page.on("request", (r) => reqs.push(r.url()));
    await page.goto(`http://127.0.0.1:${PROXY}/`);
    await page.waitForSelector('[data-section-key="system"]', { timeout: 20000 });
    await page.waitForTimeout(1500);
    console.log(JSON.stringify({ viewport: vp.width, connections: conns.length, conns: conns.map((c) => ({ id: c.id, bytes: c.bytes, requests: c.firstLines })), pageRequests: reqs }, null, 1));
    await ctx.close();
}
await browser.close(); server.close();
