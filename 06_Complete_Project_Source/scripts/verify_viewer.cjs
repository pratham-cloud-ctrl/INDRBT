/* Optional browser QA. Run: node scripts/verify_viewer.cjs [playwright module] [Chrome executable] */
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { chromium } = require(process.argv[2] || 'playwright');
const root = path.resolve(__dirname, '..');
const html = path.join(root, 'simulations/aster6_twin.html');
const reference = JSON.parse(fs.readFileSync(path.join(root, 'results/validation/viewer_reference.json'), 'utf8'));

(async () => {
  const browser = await chromium.launch({
    headless: true,
    executablePath: process.argv[3] || process.env.CHROME_EXECUTABLE || undefined,
    args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'],
  });
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 980 } });
    const errors = [];
    page.on('pageerror', error => errors.push(String(error)));
    await page.goto('file:///' + html.replace(/\\/g, '/'));
    await page.waitForFunction(() => window.asterDebug && document.querySelector('#tcp').textContent.length > 0);
    await page.screenshot({ path: path.join(root, 'simulations/viewer_preview.png') });
    const baseline = await page.evaluate(() => ({ tcp: document.querySelector('#tcp').textContent, meshes: window.asterDebug.meshCount }));
    await page.getByRole('button', { name: 'Play demo', exact: true }).click();
    await page.waitForTimeout(350);
    await page.getByRole('button', { name: 'Pause demo', exact: true }).click();
    await page.evaluate(() => window.asterDebug.sample(3.4));
    const closed = await page.evaluate(() => window.asterDebug.opening);
    await page.evaluate(() => window.asterDebug.sample(7));
    const opened = await page.evaluate(() => window.asterDebug.opening);
    await page.getByRole('button', { name: 'Vertical', exact: true }).click();
    const vertical = await page.evaluate(() => window.asterDebug.fk(window.asterDebug.q).tcp);
    const transforms = await page.evaluate(qs => qs.map(q => window.asterDebug.fk(q).tcp), reference.q_rad);
    const components = await page.locator('#component option').evaluateAll(options => options.map(o => o.value).filter(Boolean));
    let minimumVisiblePixels = Infinity;
    for (const name of components) {
      await page.locator('#component').selectOption(name);
      await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
      const inspection = await page.evaluate(() => {
        const source = document.querySelector('canvas'), thumbnail = document.createElement('canvas');
        thumbnail.width = thumbnail.height = 64;
        const ctx = thumbnail.getContext('2d');
        ctx.drawImage(source, 0, 0, 64, 64);
        const pixels = ctx.getImageData(0, 0, 64, 64).data;
        let visible = 0;
        for (let i = 0; i < pixels.length; i += 4) {
          if (Math.abs(pixels[i] - 11) + Math.abs(pixels[i+1] - 21) + Math.abs(pixels[i+2] - 31) > 8) visible++;
        }
        return { visible, selected: window.asterDebug.selectedComponent, count: window.asterDebug.renderedComponentCount, glError: source.getContext('webgl').getError() };
      });
      if (inspection.selected !== name || inspection.count !== 1 || inspection.visible === 0 || inspection.glError !== 0) {
        throw Error(JSON.stringify({ name, inspection }));
      }
      minimumVisiblePixels = Math.min(minimumVisiblePixels, inspection.visible);
    }
    await page.locator('#component').selectOption('');
    const labels = await page.locator('body').innerText();
    if (/\u00c2|\u00c3|\ufffd/.test(labels) || !labels.includes('\u00b0') || !labels.includes('54 components \u00b7 complete assembly')) {
      throw Error('Viewer labels contain incorrect character encoding');
    }
    let maxError = 0;
    for (let i = 0; i < transforms.length; i++) {
      for (let j = 0; j < 16; j++) maxError = Math.max(maxError, Math.abs(transforms[i][j] - reference.matrices[i][j]));
    }
    if (errors.length || maxError > 1e-9 || Math.abs(closed - .028) > 1e-12 || Math.abs(opened - .09) > 1e-12 || Math.abs(vertical[11] - .98) > 1e-9 || baseline.meshes !== 54 || components.length !== 54) {
      throw Error(JSON.stringify({ errors, maxError, closed, opened, vertical, baseline }));
    }
    const report = {
      status: 'VERIFIED DIGITALLY',
      browser: 'Chromium / headless WebGL',
      mesh_count: baseline.meshes,
      random_fk_comparisons: transforms.length,
      maximum_js_python_matrix_difference: maxError,
      play_pause_interaction: 'PASS',
      label_encoding: 'PASS',
      individual_components_inspected: components.length,
      minimum_component_visible_pixels_in_64px_thumbnail: minimumVisiblePixels,
      restore_complete_assembly: await page.evaluate(() => window.asterDebug.renderedComponentCount === 54),
      gripper_closed_m: closed,
      gripper_open_m: opened,
      vertical_tcp_z_m: vertical[11],
      page_errors: errors,
      html_sha256: crypto.createHash('sha256').update(fs.readFileSync(html, 'utf8').replace(/\r\n/g, '\n')).digest('hex'),
      hash_convention: 'UTF-8 HTML with LF line endings',
      scope: 'Actual browser render, playback interactions and transform checks; not collision or contact validation',
    };
    fs.writeFileSync(path.join(root, 'results/validation/viewer_validation.json'), JSON.stringify(report, null, 2) + '\n');
    console.log(JSON.stringify(report));
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exit(1); });
