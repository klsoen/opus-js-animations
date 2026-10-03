// Shared helpers: drive headless Chrome over the DevTools protocol with no npm installs
// (Node ≥ 22 has fetch and WebSocket built in). Every tool loads a film page with
// ?capture=1 and calls window.__film.seek(t).
import { spawn } from 'node:child_process';
import http from 'node:http';
import { mkdtempSync, existsSync, readFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve, sep, extname } from 'node:path';
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
// url: open the film from a local server (serveDir) instead of file://, so the page can send frames back over HTTP.
export async function openFilm(htmlPath, { port = 9400 + Math.floor(Math.random() * 400), gpu = true, ss = 1, url: pageUrl = null } = {}) {
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
  const url = (pageUrl || pathToFileURL(resolve(htmlPath)).href) + '?capture=1' + (ss > 1 ? `&ss=${ss}` : '');
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

// A local server for a film folder: GET serves its files (the film, its scripts, fonts, audio), and POST /frame hands each
// frame's raw bytes to onFrame(query, body, done). render.mjs uses it to take frames out of the page as raw pixels: a PNG
// data URL through DevTools costs most of a second for a 2× frame, a POST of raw RGBA a few milliseconds.
const MIME = { '.html': 'text/html', '.js': 'text/javascript', '.mjs': 'text/javascript', '.json': 'application/json', '.css': 'text/css',
  '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.webp': 'image/webp', '.svg': 'image/svg+xml', '.gif': 'image/gif',
  '.wav': 'audio/wav', '.mp3': 'audio/mpeg', '.m4a': 'audio/mp4', '.ogg': 'audio/ogg', '.mp4': 'video/mp4',
  '.woff': 'font/woff', '.woff2': 'font/woff2', '.ttf': 'font/ttf', '.otf': 'font/otf', '.glb': 'model/gltf-binary', '.gltf': 'model/gltf+json', '.hdr': 'application/octet-stream' };
export async function serveDir(root, onFrame = null) {
  root = resolve(root);
  const server = http.createServer((req, res) => {
    const u = new URL(req.url, 'http://local');
    if (req.method === 'POST' && u.pathname === '/frame' && onFrame) {
      const chunks = []; req.on('data', c => chunks.push(c));
      req.on('end', () => onFrame(u.searchParams, Buffer.concat(chunks), () => res.end('ok')));
      return;
    }
    const f = resolve(root, '.' + decodeURIComponent(u.pathname));
    if (f !== root && !f.startsWith(root + sep)) { res.writeHead(403); res.end(); return; }
    try { const body = readFileSync(f); res.writeHead(200, { 'content-type': MIME[extname(f).toLowerCase()] || 'application/octet-stream' }); res.end(body); }
    catch { res.writeHead(404); res.end(); }
  });
  await new Promise(r => server.listen(0, '127.0.0.1', r));
  const port = server.address().port;
  return { port, url: rel => `http://127.0.0.1:${port}/${rel.split(sep).map(encodeURIComponent).join('/')}`, close: () => server.close() };
}

