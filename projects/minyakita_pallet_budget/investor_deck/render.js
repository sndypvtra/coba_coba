// Renders deck.html to high-resolution images:
//   slides/slide-NN.png      each slide at 3200x1800 (2x)
//   grafik/<name>.png        each chart/diagram alone at 3x, white padding
//   grafik/<name>.svg        the same chart as a standalone vector file
const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

const CHARTS = [
  'grafik-01-alur-sistem',
  'grafik-02-contoh-dashboard',
  'grafik-03-timeline-16-minggu',
  'grafik-04-komposisi-investasi',
  'grafik-05-waterfall-beli-putus',
  'grafik-06-saldo-subscription',
];
const FONT = "Inter, 'Helvetica Neue', Arial, sans-serif";

(async () => {
  const slidesDir = path.join(__dirname, 'slides');
  const chartDir = path.join(__dirname, 'grafik');
  fs.mkdirSync(slidesDir, { recursive: true });
  fs.mkdirSync(chartDir, { recursive: true });
  const browser = await chromium.launch();

  const page = await browser.newPage({ viewport: { width: 1600, height: 900 }, deviceScaleFactor: 2 });
  await page.goto('file://' + path.join(__dirname, 'deck.html'));
  await page.evaluate(() => document.fonts.ready);
  const slides = await page.$$('section.slide');
  for (const [i, s] of slides.entries()) {
    await s.screenshot({ path: path.join(slidesDir, `slide-${String(i + 1).padStart(2, '0')}.png`) });
  }

  const svgs = await page.$$eval('section.slide svg', (els) => els.map((e) => e.outerHTML));
  if (svgs.length !== CHARTS.length) throw new Error(`expected ${CHARTS.length} charts, found ${svgs.length}`);
  const chartPage = await browser.newPage({ viewport: { width: 1600, height: 900 }, deviceScaleFactor: 3 });
  for (const [i, raw] of svgs.entries()) {
    const svg = raw.replace('<svg ', `<svg xmlns="http://www.w3.org/2000/svg" font-family="${FONT}" `);
    fs.writeFileSync(path.join(chartDir, `${CHARTS[i]}.svg`), svg);
    await chartPage.setContent(
      `<html><body style="margin:0;background:#fff"><div id="c" style="display:inline-block;padding:32px;background:#fff">${svg}</div></body></html>`);
    await chartPage.evaluate(() => document.fonts.ready);
    await (await chartPage.$('#c')).screenshot({ path: path.join(chartDir, `${CHARTS[i]}.png`) });
  }

  await browser.close();
  console.log(`${slides.length} slides, ${svgs.length} charts`);
})();
