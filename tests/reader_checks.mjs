// Legacy continuous-reader regression; both prebuilt fixtures must explicitly use
// readingMode: continuous. New defaults are exercised by focus_browser_checks.py.
// Install Playwright or set REPORT_PLAYWRIGHT_MODULE.
import { mkdir, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
const { chromium } = await import(process.env.REPORT_PLAYWRIGHT_MODULE || 'playwright');
const out = resolve(process.argv[2]);
await mkdir(resolve(out, 'reader-qa'), { recursive: true });
const records = [], errors = [], requests = [];
const browser = await chromium.launch({ headless: true, ...(process.env.REPORT_BROWSER_PATH ? { executablePath: process.env.REPORT_BROWSER_PATH } : process.platform === 'win32' ? { channel: 'chrome' } : {}) });
function ok(value, name) { records.push({ name, pass: !!value }); if (!value) throw Error(name); }
try {
  const context = await browser.newContext({ offline: true, viewport: { width: 1440, height: 1000 } });
  const page = await context.newPage();
  page.on('pageerror', e => errors.push(e.message)); page.on('request', r => { if (/^https?:/.test(r.url())) requests.push(r.url()); });
  await page.goto(pathToFileURL(resolve(out, '增强版预览.html')).href);
  const navText = await page.locator('#report-outline nav').innerText();
  ok(await page.locator('#report-outline').evaluate(el => getComputedStyle(el).position === 'fixed'), 'sidebar fixed by default');
  ok(await page.evaluate(() => document.querySelector('#overview').getBoundingClientRect().top < document.querySelector('.report-meta').getBoundingClientRect().top), 'conclusion before metadata');
  ok(await page.locator('#work .section-content').isHidden(), 'brief view keeps detail section folded');
  await page.locator('[data-report-view="full"]').click();
  ok(await page.locator('#work .section-content').isVisible(), 'full view restores details');
  ok(navText === await page.locator('#report-outline nav').innerText(), 'view switch preserves chapter structure and numbering');
  await page.locator('[data-report-view="brief"]').click();
  const chapter = page.locator('#chapter-dialog');
  await page.locator('#report-outline a[href="#work"]').click();
  ok(await chapter.isVisible() && (await chapter.innerText()).includes('允许、拒绝及权限变化'), 'sidebar click opens complete chapter in overlay');
  const unique = () => page.evaluate(() => { const ids = [...document.querySelectorAll('[id]')].map(e => e.id); return ids.length === new Set(ids).size; });
  ok(await unique(), 'no duplicate ids while chapter overlay open');
  await page.keyboard.press('Escape'); ok(await chapter.isHidden(), 'chapter Esc close');
  ok(await page.locator('#report-outline a[href="#work"]').evaluate(el => el === document.activeElement), 'chapter focus returns to sidebar');
  await page.locator('#report-outline a[href="#choose"]').click();
  const select = chapter.locator('[data-scenario-select]'); await select.selectOption('local-use');
  ok(await chapter.locator('[data-scenario="local-use"]').isVisible() && await chapter.locator('[data-scenario="remote-use"]').isHidden(), 'scenario switch shows registered local model');
  await chapter.locator('[data-scenario="local-use"] [data-node="engine"]').click();
  ok(await page.locator('#component-dialog').isVisible() && (await page.locator('#component-dialog').innerText()).includes('本地权限引擎'), 'node detail opens over chapter');
  await page.keyboard.press('Escape'); ok(await chapter.isVisible(), 'node close leaves chapter open');
  await chapter.locator('[data-scenario="local-use"] [data-trace-next]').click();
  ok((await chapter.locator('[data-scenario="local-use"] .trace-state').innerText()).includes('第1/2步'), 'trace follows selected model');
  await select.selectOption('future-use');
  ok((await chapter.locator('[data-scenario="future-use"]').innerText()).includes('未来方案，尚不可作为可运行能力'), 'future mode remains labeled unimplemented');
  await page.keyboard.press('Escape');
  await page.locator('#report-outline a[href="#figure"]').click();
  const image = chapter.locator('.report-figure img'); await image.click();
  const preview = page.locator('#figure-dialog'); ok(await preview.isVisible(), 'figure opens over chapter');
  await preview.locator('img').click(); ok(await preview.isHidden() && await chapter.isVisible(), 'second image click closes only image overlay');
  await image.focus(); await page.keyboard.press('Enter'); await page.keyboard.press('Escape');
  ok(await preview.isHidden() && await image.evaluate(el => el === document.activeElement), 'image keyboard and focus return');
  await chapter.locator('[data-close-dialog]').click();
  await page.locator('#choose .node-index').first().locator('summary').click();
  const term = page.locator('#choose a.term').first(); await term.click();
  ok(await page.locator('#term-dialog').isVisible(), 'glossary remains usable with native graph'); await page.keyboard.press('Escape');
  for (const width of [1440, 390]) {
    await page.setViewportSize({ width, height: width === 390 ? 844 : 1000 }); await page.evaluate(() => scrollTo(0,0));
    await page.waitForTimeout(120);
    ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), `${width}px no page overflow`);
    ok(await page.evaluate(() => document.querySelector('#report-outline').getBoundingClientRect().right <= document.querySelector('.shell').getBoundingClientRect().left), `${width}px sidebar does not cover body`);
    await page.screenshot({ path: resolve(out, 'reader-qa', 'default-'+width+'.png') });
    await page.locator('#report-outline a[href="#choose"]').click();
    ok(await chapter.isVisible(), `${width}px chapter overlay available`);
    await chapter.locator('[data-scenario="remote-use"] [data-node="engine"]').focus(); await page.keyboard.press('Enter');
    ok(await page.locator('#component-dialog').isVisible(), `${width}px node keyboard support`); await page.keyboard.press('Escape');
    await page.screenshot({ path: resolve(out, 'reader-qa', 'chapter-'+width+'.png') }); await page.keyboard.press('Escape');
  }
  await page.pdf({ path: resolve(out, 'reader-qa/full-print.pdf'), format: 'A4', printBackground: true });
  await page.emulateMedia({ media: 'print' });
  ok(await page.locator('[data-scenario="future-use"]').isVisible(), 'print retains all scenarios');
  ok(await page.locator('#work .section-content').isVisible(), 'print retains detailed chapter'); await page.emulateMedia({ media: 'screen' });
  await page.goto(pathToFileURL(resolve(out, 'legacy-audit.html')).href);
  await page.locator('#report-outline a[href="#findings-section"]').click();
  const input = chapter.locator('input'); await input.fill('no-such-finding');
  ok(await chapter.locator('tbody tr:visible').count() === 0, 'finding search works inside chapter');
  await chapter.locator('[data-original-id="reset"]').click();
  ok(await chapter.locator('tbody tr:visible').count() === 3, 'finding reset restores all rows');
  await chapter.locator('.finding').first().click(); ok(await page.locator('#drawer').isVisible(), 'finding detail opens over chapter');
  await page.keyboard.press('Escape'); await page.keyboard.press('Escape');
  const nojs = await browser.newContext({ offline: true, javaScriptEnabled: false, viewport: { width: 390, height: 844 } });
  const np = await nojs.newPage(); await np.goto(pathToFileURL(resolve(out, '增强版预览.html')).href);
  ok(await np.locator('[data-scenario]:visible').count() === 3, 'no-JS keeps every scenario');
  ok(await np.locator('#work .section-content').isVisible() && await np.locator('[data-scenario-select]').isHidden(), 'no-JS shows details and hides inactive controls');
  await np.locator('#report-outline a[href="#work"]').click(); ok(new URL(np.url()).hash === '#work', 'no-JS directory links to source chapter');
  await nojs.close();
  ok(errors.length === 0, 'no script errors'); ok(requests.length === 0, 'no external runtime requests');
} finally {
  await browser.close();
  await writeFile(resolve(out, 'reader-qa/results.json'), JSON.stringify({ date: '2026-11-17', records, errors, externalRequests: requests }, null, 2));
}
console.log(JSON.stringify({ checks: records.length, passed: records.filter(x => x.pass).length, errors }, null, 2));
