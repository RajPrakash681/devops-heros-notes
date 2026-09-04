// Renders REAL captured terminal output (stdout text from this machine) as a PNG.
// Input JSON: [{ title, lines: [{cmd, out}], out: "path.png" }]
import { chromium } from 'playwright';
import fs from 'node:fs';
import path from 'node:path';

const jobs = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

const render = (job) => `<!doctype html>
<meta charset="utf-8">
<style>
  * { box-sizing: border-box; }
  body { margin:0; background:#c8cdd4; padding:22px; font:14px -apple-system,Segoe UI,sans-serif; }
  .win { width:1140px; margin:0 auto; border-radius:10px; overflow:hidden;
         box-shadow:0 10px 34px rgba(0,0,0,.3); }
  .bar { background:#3a3f44; padding:9px 12px; display:flex; align-items:center; gap:10px; }
  .dots { display:flex; gap:6px; }
  .dots i { width:11px; height:11px; border-radius:50%; display:block; }
  .title { color:#d6d9dc; font-size:12.5px; }
  .body { background:#12141a; padding:16px 18px; }
  pre { margin:0 0 4px; color:#d6dae0; font:13px/1.55 ui-monospace,Consolas,monospace;
        white-space:pre-wrap; word-break:break-word; }
  .cmd { color:#7ee787; margin-top:14px; }
  .cmd:first-child { margin-top:0; }
  .ps1 { color:#58a6ff; }
</style>
<div class="win">
  <div class="bar">
    <div class="dots"><i style="background:#ff5f57"></i><i style="background:#febc2e"></i><i style="background:#28c840"></i></div>
    <div class="title">${esc(job.title)}</div>
  </div>
  <div class="body">
    ${job.lines.map((l) => `<pre class="cmd"><span class="ps1">$</span> ${esc(l.cmd)}</pre>${
      l.out && l.out.trim() ? `<pre>${esc(l.out.replace(/\s+$/, ''))}</pre>` : ''
    }`).join('')}
  </div>
</div>`;

const browser = await chromium.launch();
for (const job of jobs) {
  const page = await browser.newPage({ viewport: { width: 1190, height: 400 }, deviceScaleFactor: 2 });
  await page.setContent(render(job), { waitUntil: 'load' });
  await page.waitForTimeout(250);
  fs.mkdirSync(path.dirname(job.out), { recursive: true });
  await page.locator('.win').screenshot({ path: job.out });
  console.log(`OK   ${job.title} -> ${path.basename(job.out)}`);
  await page.close();
}
await browser.close();
