// Shared helpers: drive headless Chrome over the DevTools protocol with no npm installs
// (Node ≥ 22 has fetch and WebSocket built in). Every tool loads a film page with
// ?capture=1 and calls window.__film.seek(t).
import { spawn } from 'node:child_process';
import { mkdtempSync, existsSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';

export const sleep = ms => new Promise(r => setTimeout(r, ms));

const CHROME_CANDIDATES = [
  process.env.CHROME,
  '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  '/Applications/Chromium.app/Contents/MacOS/Chromium',
  '/usr/bin/google-chrome', '/usr/bin/chromium', '/usr/bin/chromium-browser',
].filter(Boolean);

export function findChrome() {
  const c = CHROME_CANDIDATES.find(p => existsSync(p));
  if (!c) throw new Error('No Chrome found; set CHROME=/path/to/chrome');
  return c;
}

export function parseArgs(argv) {
  const out = { _: [] };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a.startsWith('--')) {
      const k = a.slice(2), next = argv[i + 1];
      if (next === undefined || next.startsWith('--')) out[k] = true; else { out[k] = next; i++; }
    } else out._.push(a);
  }
  return out;
}

// Launch a headless Chrome with GPU (Metal on macOS; the shader layers need it to be fast)
// and open the film. ss > 1 asks a supersampling-aware film for an ss× canvas (?ss=2). Returns { ev, close, info }.
export async function openFilm(htmlPath, { port = 9400 + Math.floor(Math.random() * 400), gpu = true, ss = 1 } = {}) {
  const flags = ['--headless=new', `--remote-debugging-port=${port}`, `--user-data-dir=${mkdtempSync(join(tmpdir(), 'film-'))}`,
    '--hide-scrollbars', '--autoplay-policy=no-user-gesture-required', '--ignore-gpu-blocklist'];
  if (gpu && process.platform === 'darwin') flags.push('--use-angle=metal');
  if (!gpu) flags.push('--disable-gpu');
  const chrome = spawn(findChrome(), [...flags, 'about:blank'], { stdio: 'ignore' });

  let targets;
  for (let i = 0; i < 150; i++) {
    try { targets = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json(); if (targets.some(t => t.type === 'page')) break; } catch {}
    await sleep(100);
  }
  const ws = new WebSocket(targets.find(t => t.type === 'page').webSocketDebuggerUrl);
  await new Promise(r => ws.onopen = r);
  let id = 0; const pending = new Map(), logs = [];
  ws.onmessage = m => {
    const d = JSON.parse(m.data);
    if (d.id && pending.has(d.id)) { pending.get(d.id)(d); pending.delete(d.id); }
    if (d.method === 'Runtime.exceptionThrown') logs.push(d.params.exceptionDetails.exception?.description || d.params.exceptionDetails.text);
  };
  const send = (method, params = {}) => new Promise(r => { const i = ++id; pending.set(i, r); ws.send(JSON.stringify({ id: i, method, params })); });
  const ev = async expr => {
    const r = await send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true });
    if (r.result?.exceptionDetails) throw new Error(r.result.exceptionDetails.exception?.description || r.result.exceptionDetails.text);
    return r.result.result.value;
  };
  await send('Runtime.enable');
  const url = pathToFileURL(resolve(htmlPath)).href + '?capture=1' + (ss > 1 ? `&ss=${ss}` : '');
  await send('Page.navigate', { url });
  // Navigation returns before the page loads; poll for the contract, not a timer.
  let ok = false;
  for (let i = 0; i < 300; i++) {
    try { ok = await ev('!!(window.__film && window.__film.ready)'); } catch {}
    if (ok) break;
    await sleep(100);
  }
  if (!ok) throw new Error(`window.__film never became ready.${logs.length ? ' Page errors:\n' + logs.join('\n') : ''}`);
  const info = await ev(`({ duration: __film.duration, w: document.getElementById('c')?.width ?? document.querySelector('canvas').width,
    h: document.getElementById('c')?.height ?? document.querySelector('canvas').height, gpu: (() => { try {
      const g = document.createElement('canvas').getContext('webgl'); const e = g.getExtension('WEBGL_debug_renderer_info');
      return e ? g.getParameter(e.UNMASKED_RENDERER_WEBGL) : g.getParameter(g.RENDERER); } catch { return 'none'; } })() })`);
  return { ev, logs, info, close: () => { try { ws.close(); } catch {} chrome.kill(); } };
}

// Seek and grab the canvas as JPEG (or PNG) bytes.
export async function grab(ev, t, type = 'image/jpeg', q = .95) {
  const url = await ev(`(__film.seek(${t}), (document.getElementById('c') || document.querySelector('canvas')).toDataURL('${type}', ${q}))`);
  return Buffer.from(url.slice(url.indexOf(',') + 1), 'base64');
}
