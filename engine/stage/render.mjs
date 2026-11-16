// node render.mjs <port> <id> <style> frames <t...>      still frames -> <outdir>/<id>_<t>.jpg
// node render.mjs <port> <id> <style> video <out.mp4> [f0 f1]   silent video (frames f0..f1-1) piped to ffmpeg
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';

let chromium;
try { ({ chromium } = await import('playwright-core')); } catch { ({ chromium } = await import('/opt/npm-tools/node_modules/playwright/index.mjs')); }
const [port, id, style, mode, ...rest] = process.argv.slice(2);
const FPS = 30;
const here = path.dirname(new URL(import.meta.url).pathname);
const spec = JSON.parse(fs.readFileSync(path.join(here, 'work', id, 'spec.json')));
const exe = process.env.CHROME || ['/usr/bin/google-chrome', '/usr/bin/google-chrome-stable', '/usr/bin/chromium-browser', '/usr/bin/chromium'].find(p => fs.existsSync(p));
const browser = await chromium.launch({ executablePath: exe, args: ['--no-proxy-server', '--no-sandbox', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--disable-gpu-vsync', '--hide-scrollbars', '--force-color-profile=srgb'] });
const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
page.on('pageerror', e => { console.log('[pageerror]', e.message); process.exitCode = 2; });
await page.goto(`http://127.0.0.1:${port}/index.html?id=${id}&style=${style}`);
await page.waitForFunction('window.ready === true', null, { timeout: 180000 });
if (!(mode === 'video' && rest[1] && rest[1] !== '0')) for (const w of await page.evaluate(() => window.audit())) console.log('WARNING:', w);

if (mode === 'frames') {
  const dir = rest[0];
  for (const s of rest.slice(1)) {
    const t = parseFloat(s);
    await page.evaluate(t => window.renderAt(t), t);
    await page.screenshot({ path: path.join(dir, `${id}_${t.toFixed(2).padStart(6, '0')}.jpg`), type: 'jpeg', quality: 90 });
  }
} else {
  const out = rest[0], tmp = out.replace('.mp4', '.part.mp4');
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'mjpeg', '-i', '-',
    '-c:v', 'libx264', '-crf', '18', '-preset', 'veryfast', '-pix_fmt', 'yuv420p', '-r', String(FPS), tmp], { stdio: ['pipe', 'inherit', 'inherit'] });
  const n = Math.round(spec.TL.total * FPS), t0 = Date.now();
  const f0 = rest[1] ? parseInt(rest[1]) : 0, f1 = rest[2] ? Math.min(n, parseInt(rest[2])) : n;
  for (let f = f0; f < f1; f++) {
    await page.evaluate(t => window.renderAt(t), f / FPS);
    const buf = await page.screenshot({ type: 'jpeg', quality: 92 });
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    if ((f - f0) % 300 === 0 && f0 === 0) console.log(`   frame ${f}/${f1}  ${((Date.now() - t0) / 1000).toFixed(0)}s`);
  }
  ff.stdin.end();
  if (await new Promise(r => ff.on('close', r)) !== 0) throw new Error('ffmpeg failed');
  fs.renameSync(tmp, out);
}
await browser.close();
