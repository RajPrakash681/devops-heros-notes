// Screenshots a live URL inside a browser-style frame that shows the real URL.
// The rendered content is served live by the running container - nothing is mocked.
import { chromium } from 'playwright';
import fs from 'node:fs';
import path from 'node:path';

const targets = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));

const chrome = (url, h) => `<!doctype html>
<meta charset="utf-8">
<style>
  * { box-sizing: border-box; }
  body { margin:0; background:#c8cdd4; font:14px -apple-system,Segoe UI,system-ui,sans-serif; padding:22px; }
  .win { width:1040px; margin:0 auto; border-radius:10px; overflow:hidden;
         box-shadow:0 10px 34px rgba(0,0,0,.28); background:#fff; }
  .bar { background:#dee1e6; padding:9px 12px; display:flex; align-items:center; gap:10px; }
  .dots { display:flex; gap:6px; }
  .dots i { width:11px; height:11px; border-radius:50%; display:block; }
  .omni { flex:1; background:#fff; border-radius:14px; padding:6px 13px; color:#202124;
          font:13px ui-monospace,Consolas,monospace; border:1px solid #c4c7cb; }
  iframe { width:100%; height:${h}px; border:0; display:block; background:#fff; }
</style>
<div class="win">
  <div class="bar">
    <div class="dots"><i style="background:#ff5f57"></i><i style="background:#febc2e"></i><i style="background:#28c840"></i></div>
    <div class="omni">${url}</div>
  </div>
  <iframe src="${url}"></iframe>
</div>`;

const browser = await chromium.launch();
for (const t of targets) {
  const h = t.height || 330;
  const page = await browser.newPage({
    viewport: { width: 1100, height: h + 130 },
    deviceScaleFactor: 2,
  });
  try {
    // verify the container is actually serving before we render the frame
    const res = await page.request.get(t.url, { timeout: 15000 });
    if (!res.ok()) throw new Error(`HTTP ${res.status()}`);

    await page.setContent(chrome(t.url, h), { waitUntil: 'load' });
    await page.waitForTimeout(700);
    fs.mkdirSync(path.dirname(t.out), { recursive: true });
    await page.screenshot({ path: t.out });
    console.log(`OK   ${t.url}  (HTTP ${res.status()})  -> ${path.basename(t.out)}`);
  } catch (e) {
    console.log(`FAIL ${t.url}: ${String(e.message).split('\n')[0]}`);
  }
  await page.close();
}
await browser.close();
