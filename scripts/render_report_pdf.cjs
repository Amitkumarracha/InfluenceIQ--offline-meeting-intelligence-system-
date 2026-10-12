// Local Chromium print; uses the existing browser-test installation.
const { chromium } = require('../.runtime/browser/node_modules/playwright');
const { pathToFileURL } = require('node:url');
const fs = require('node:fs/promises');
const path = require('node:path');
const assert = require('node:assert/strict');
(async () => {
  const [input, output] = process.argv.slice(2);
  assert(input && output, 'Usage: node scripts/render_report_pdf.cjs INPUT.html OUTPUT.pdf');
  const browser = await chromium.launch({headless:true, channel:'chromium', args:['--no-sandbox']});
  try {
    const page = await browser.newPage({viewport:{width:794,height:1123}});
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.route(/^https?:/, route => route.abort());
    await page.goto(pathToFileURL(path.resolve(input)).href);
    await page.evaluate(async () => {
      await document.fonts.ready;
      await Promise.all([...document.images].map(image => image.decode()));
    });
    const checks = await page.evaluate(() => ({
      images:[...document.images].every(image=>image.complete && image.naturalWidth>0),
      headings:document.querySelectorAll('h2').length,
      overflow:[...document.querySelectorAll('table,pre,img')].filter(el=>el.getBoundingClientRect().right > document.documentElement.clientWidth+2).length
    }));
    assert(checks.images && checks.headings>=20 && checks.overflow===0, JSON.stringify(checks));
    assert.deepEqual(errors,[]);
    await page.pdf({path:output,format:'A4',printBackground:true,displayHeaderFooter:true,
      margin:{top:'18mm',bottom:'18mm',left:'19mm',right:'19mm'},
      headerTemplate:'<div style="font-family:Arial;font-size:8px;color:#61717d;width:100%;margin:0 19mm;">GROUP 12 · INFLUENCEIQ · MULTIMODAL AI</div>',
      footerTemplate:'<div style="font-family:Arial;font-size:8px;color:#61717d;width:100%;margin:0 19mm;display:flex;justify-content:space-between;"><span>Final cumulative report · CA4 · AY 2026–27</span><span>Page <span class="pageNumber"></span> / <span class="totalPages"></span></span></div>'});
    const stats = await fs.stat(output);assert(stats.size>100000,'PDF unexpectedly small');
    console.log(JSON.stringify({pdf:path.basename(output),bytes:stats.size,...checks}));
  } finally { await browser.close(); }
})().catch(error=>{console.error(error);process.exitCode=1;});
