// Renders each slide of deck.html to slides/slide-NN.png at 1600x900.
const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

(async () => {
  const out = path.join(__dirname, 'slides');
  fs.mkdirSync(out, { recursive: true });
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1600, height: 900 }, deviceScaleFactor: 1 });
  await page.goto('file://' + path.join(__dirname, 'deck.html'));
  await page.evaluate(() => document.fonts.ready);
  const slides = await page.$$('section.slide');
  for (const [i, s] of slides.entries()) {
    await s.screenshot({ path: path.join(out, `slide-${String(i + 1).padStart(2, '0')}.png`) });
  }
  await browser.close();
  console.log(`${slides.length} slides`);
})();
