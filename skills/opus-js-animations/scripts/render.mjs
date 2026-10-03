#!/usr/bin/env node
// Frame-exact MP4 export. Every frame is __film.seek(i / fps), so nothing drops or drifts,
// whatever the machine speed. Long films split across parallel Chrome workers.
//
//   node render.mjs film/index.html [--fps 30] [--audio mix.wav] [--out film.mp4]
//                   [--from 0 --to 12] [--workers 2] [--crf 16] [--ss 2] [--root dir] [--no-gpu] [--fast] [--legacy] [--profile]
//
// --audio is muxed and the video is cut to the shorter of the two (-shortest).
// Without --audio the output is silent (use for section previews).
//
// How frames leave the page. The film is served from its folder over http://127.0.0.1 (--root serves a parent folder when the
// film loads files from outside its own). In each worker the page runs its own loop: seek(t), then a small WebGL2 exporter
// copies the canvas to a texture, scales it down with a 3-lobe Lanczos when --ss > 1 (the kernel ffmpeg's "lanczos" uses), reads
// the raw RGBA and POSTs it back. Node pipes it into ffmpeg as rawvideo. A few frames are kept in flight, so drawing,
// copying and encoding overlap. Measured on an Apple M1 at 2160×3840: the PNG data URL the old path sent through DevTools cost
// ~0.9 s a frame; this costs ~30 ms. Frames match the old path to PSNR 60–68 dB (differences of a level or so on hard edges).
// --legacy keeps the old path (a lossless PNG of the canvas through DevTools, scaled in ffmpeg) for comparison.
//
// Frames are converted to standard HD video: BT.709, limited (TV) range, tagged, so phones and Instagram/TikTok/X
// transcoders read the colours and blacks correctly. --fast encodes with x264 "veryfast" at CRF 20, for previews only.
// --ss 2 supersamples: the film draws every frame at 2× (?ss=2; the film must support it, see references/delivery.md) and each
// frame is scaled back down. Four samples per pixel: smoother edges, text and fine detail.
// Workers: the GPU is shared, so a WebGL film saturates it at about 2 workers on an M1; more only queue. --profile prints what
// one frame costs (drawing, export) before you choose.
import { spawn, spawnSync } from 'node:child_process';
import { mkdtempSync, writeFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, dirname, resolve, relative } from 'node:path';
import { openFilm, grab, parseArgs, serveDir } from './lib.mjs';

const args = parseArgs(process.argv.slice(2));
const html = args._[0];
if (!html) { console.error('usage: node render.mjs <film.html> [--fps 30] [--audio file] [--out file.mp4] [--from s --to s] [--workers n] [--ss 2] [--root dir]'); process.exit(1); }
const fps = Number(args.fps || 30), workers = Math.max(1, Number(args.workers || 2)), fast = !!args.fast, legacy = !!args.legacy;
const crf = String(args.crf || (fast ? 20 : 16)), preset = fast ? 'veryfast' : 'slow';
const ss = Math.max(1, Math.round(Number(args.ss || 1)));
const out = resolve(args.out || join(dirname(resolve(html)), 'film.mp4'));
const root = resolve(args.root || dirname(resolve(html)));
const rel = relative(root, resolve(html));
if (rel.startsWith('..')) { console.error(`--root ${root} must contain the film`); process.exit(1); }

// the local server: the film's files, and the door frames come back through (one ordered queue per worker)
const sinks = new Map();
function onFrame(q, body, done) {
  const s = sinks.get(Number(q.get('w'))); s.waiting.set(Number(q.get('i')), { body, done });
  const pump = () => {
    while (s.waiting.has(s.next)) {
      const f = s.waiting.get(s.next); s.waiting.delete(s.next); s.next++; s.count++;
      // answer each POST once its frame is in ffmpeg's pipe, so a page never runs far ahead of the encoder
      if (!s.ff.stdin.write(f.body)) { s.ff.stdin.once('drain', () => { f.done(); pump(); }); return; }
      f.done();
    }
  };
  pump();
}
const server = await serveDir(root, onFrame);
const pageUrl = server.url(rel);
const open = (opts = {}) => openFilm(html, { gpu: !args['no-gpu'], url: legacy ? null : pageUrl, ...opts });

const probe = await open();
const { duration, w: ow, h: oh, gpu } = probe.info;                  // the film's own size
probe.close();
let w = ow, h = oh;
if (ss > 1) {                                                          // the canvas must hold exactly ss× the pixels
  const p2 = await open({ ss }); ({ w, h } = p2.info); p2.close();
  if (w !== ow * ss || h !== oh * ss) { console.error(`--ss ${ss}: the film drew ${w}×${h}, not ${ow * ss}×${oh * ss}. Does it read ?ss= (references/delivery.md §3)?`); process.exit(1); }
}

// The exporter, put into each page: the canvas → a texture → Lanczos ↓ss in two separable passes (float) → RGBA8, top row
// first. At ss = 1 it reads the texture as it is.
const EXPORTER = String.raw`(() => {
  const src = document.getElementById('c') || document.querySelector('canvas'), SSX = ${ss}, OW = src.width / SSX, OH = src.height / SSX;
  const cv = document.createElement('canvas'); cv.width = OW; cv.height = OH;
  const g = cv.getContext('webgl2', { antialias: false, premultipliedAlpha: false, preserveDrawingBuffer: false });
  if (!g) throw new Error('render.mjs: no WebGL2 for the exporter (use --legacy)');
  if (SSX > 1 && !g.getExtension('EXT_color_buffer_float')) throw new Error('render.mjs: no float render targets (use --legacy)');
  const params = t => { for (const [k, v] of [[g.TEXTURE_MIN_FILTER, g.NEAREST], [g.TEXTURE_MAG_FILTER, g.NEAREST], [g.TEXTURE_WRAP_S, g.CLAMP_TO_EDGE], [g.TEXTURE_WRAP_T, g.CLAMP_TO_EDGE]]) g.texParameteri(g.TEXTURE_2D, k, v); };
  const fbOf = t => { const f = g.createFramebuffer(); g.bindFramebuffer(g.FRAMEBUFFER, f); g.framebufferTexture2D(g.FRAMEBUFFER, g.COLOR_ATTACHMENT0, g.TEXTURE_2D, t, 0); return f; };
  const tIn = g.createTexture(); g.bindTexture(g.TEXTURE_2D, tIn); params(tIn);
  g.pixelStorei(g.UNPACK_FLIP_Y_WEBGL, false); g.pixelStorei(g.UNPACK_PREMULTIPLY_ALPHA_WEBGL, false);
  const px = new Uint8Array(OW * OH * 4);
  let draw = null;
  if (SSX > 1) {
    const VS = '#version 300 es\nin vec2 p; void main(){ gl_Position = vec4(p, 0., 1.); }';
    const FS = dir => '#version 300 es\n' +
      'precision highp float; uniform sampler2D t; uniform vec2 inSize; out vec4 o;\n' +
      'float L(float x){ x = abs(x); if (x < 1e-5) return 1.; if (x >= 3.) return 0.; float a = 3.14159265*x; return 3.*sin(a)*sin(a/3.)/(a*a); }\n' +
      'void main(){\n' +
      '  float c = ' + (dir === 'x' ? 'gl_FragCoord.x' : 'gl_FragCoord.y') + '*' + SSX + '.;\n' +
      '  vec4 s = vec4(0.); float ws = 0.;\n' +
      '  for (int k = -' + 3 * SSX + '; k <= ' + 3 * SSX + '; k++){\n' +
      '    float x = floor(c) + float(k) + .5, w = L((x - c)/' + SSX + '.);\n' +
      '    vec2 uv = ' + (dir === 'x' ? 'vec2(clamp(x, .5, inSize.x - .5), gl_FragCoord.y)' : 'vec2(gl_FragCoord.x, clamp(x, .5, inSize.y - .5))') + '/inSize;\n' +
      '    s += texture(t, uv)*w; ws += w;\n' +
      '  }\n' +
      '  o = s/ws;\n' +
      '}';
    const prog = fs => { const sh = (ty, s) => { const x = g.createShader(ty); g.shaderSource(x, s); g.compileShader(x); if (!g.getShaderParameter(x, g.COMPILE_STATUS)) throw new Error(g.getShaderInfoLog(x)); return x; };
      const p = g.createProgram(); g.attachShader(p, sh(g.VERTEX_SHADER, VS)); g.attachShader(p, sh(g.FRAGMENT_SHADER, fs)); g.bindAttribLocation(p, 0, 'p'); g.linkProgram(p); return p; };
    const PX = prog(FS('x')), PY = prog(FS('y'));
    const vb = g.createBuffer(); g.bindBuffer(g.ARRAY_BUFFER, vb); g.bufferData(g.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), g.STATIC_DRAW);
    g.enableVertexAttribArray(0); g.vertexAttribPointer(0, 2, g.FLOAT, false, 0, 0);
    const store = (w, h, fmt) => { const t = g.createTexture(); g.bindTexture(g.TEXTURE_2D, t); g.texStorage2D(g.TEXTURE_2D, 1, fmt, w, h); params(t); return t; };
    const tMid = store(OW, src.height, g.RGBA32F), tOut = store(OW, OH, g.RGBA8);
    const fMid = fbOf(tMid), fOut = fbOf(tOut);
    const pass = (p, tex, fb, w, h, inW, inH) => { g.bindTexture(g.TEXTURE_2D, tex); g.bindFramebuffer(g.FRAMEBUFFER, fb); g.viewport(0, 0, w, h);
      g.useProgram(p); g.uniform1i(g.getUniformLocation(p, 't'), 0); g.uniform2f(g.getUniformLocation(p, 'inSize'), inW, inH); g.drawArrays(g.TRIANGLES, 0, 3); };
    draw = () => { pass(PX, tIn, fMid, OW, src.height, src.width, src.height); pass(PY, tMid, fOut, OW, OH, OW, src.height); };
  }
  const fIn = fbOf(tIn);
  window.__export = () => {
    g.bindTexture(g.TEXTURE_2D, tIn); g.texImage2D(g.TEXTURE_2D, 0, g.RGBA, g.RGBA, g.UNSIGNED_BYTE, src);   // row 0 = the top of the frame
    if (draw) draw(); else g.bindFramebuffer(g.FRAMEBUFFER, fIn);
    g.readPixels(0, 0, OW, OH, g.RGBA, g.UNSIGNED_BYTE, px);                                               // so the rows come out top first
    return px;
  };
  window.__runRange = async (a, b, fps, w, depth) => {
    const inflight = [];
    for (let i = a; i <= b; i++) {
      __film.seek(i / fps);
      inflight.push(fetch('/frame?w=' + w + '&i=' + i, { method: 'POST', body: __export() }).then(r => r.text()));   // the body is copied at the call
      if (inflight.length >= depth) await inflight.shift();
    }
    await Promise.all(inflight);
    return true;
  };
  return [OW, OH];
})()`;

if (args.profile) {                                                    // what one frame costs, in one page
  const film = await open({ ss });
  if (!legacy) await film.ev(EXPORTER);
  const r = await film.ev(`(() => {
    const c = document.getElementById('c') || document.querySelector('canvas'), T = []; for (let i = 0; i < 40; i++) T.push(${Number(args.profile) > 1 ? Number(args.profile) : duration / 3} + i / ${fps});
    const sync = () => { try { c.getContext('2d') ? c.getContext('2d').getImageData(0, 0, 1, 1) : c.toDataURL('image/jpeg', .1); } catch { c.toDataURL('image/jpeg', .1); } };
    let draw = 0, exp = 0;
    for (const t of T) { let a = performance.now(); __film.seek(t); sync(); let b = performance.now(); draw += b - a;
      ${legacy ? "c.toDataURL('image/png');" : '__export();'} exp += performance.now() - b; }
    return { draw_ms: +(draw / T.length).toFixed(1), export_ms: +(exp / T.length).toFixed(1) };
  })()`);
  console.log(`one frame at ${w}×${h}:`, r, legacy ? '(legacy export; the DevTools transfer comes on top)' : '');
  film.close(); server.close(); process.exit(0);
}

const from = Number(args.from || 0), to = Math.min(Number(args.to ?? duration), duration);
const first = Math.round(from * fps), last = Math.ceil(to * fps) - 1, total = last - first + 1;
console.log(`${ow}×${oh}${ss > 1 ? ` (drawn at ${w}×${h}, ${ss}× supersampled)` : ''} · ${fps} fps · frames ${first}–${last} (${total}) · ${workers} worker(s) · ${legacy ? 'legacy PNG export' : 'raw export'} · GPU: ${gpu}`);

const tmp = mkdtempSync(join(tmpdir(), 'render-'));
const t0 = Date.now();
let done = 0;
const tick = () => { const n = legacy ? done : [...sinks.values()].reduce((a, s) => a + s.count, 0), sec = (Date.now() - t0) / 1000;
  process.stdout.write(`\r${n}/${total} frames · ${sec.toFixed(0)}s · ${(n / Math.max(sec, .001)).toFixed(1)} fps`); };
const timer = setInterval(tick, 2000);
const toHD = 'scale=out_range=tv:out_color_matrix=bt709:flags=accurate_rnd+full_chroma_int,format=yuv420p,setparams=range=tv:colorspace=bt709:color_primaries=bt709:color_trc=bt709';
const enc = seg => ['-color_range', 'tv', '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709',
  '-c:v', 'libx264', '-preset', preset, '-crf', crf, '-profile:v', 'high', seg];

async function renderRange(k, a, b, seg) {
  const film = await open({ ss });
  if (legacy) {
    const down = ss > 1 ? `scale=${ow}:${oh}:flags=lanczos+accurate_rnd,format=rgb48le,` : '';
    const ff = spawn('ffmpeg', ['-v', 'error', '-y', '-f', 'image2pipe', '-framerate', String(fps), '-c:v', 'png', '-i', '-', '-vf', down + toHD, ...enc(seg)], { stdio: ['pipe', 'inherit', 'inherit'] });
    for (let i = a; i <= b; i++) {
      const buf = await grab(film.ev, i / fps, 'image/png');
      if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
      done++;
    }
    ff.stdin.end(); await new Promise(r => ff.on('close', r));
  } else {
    const [OW, OH] = await film.ev(EXPORTER);
    const ff = spawn('ffmpeg', ['-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgba', '-s', `${OW}x${OH}`, '-framerate', String(fps), '-i', '-', '-vf', toHD, ...enc(seg)],
      { stdio: ['pipe', 'inherit', 'inherit'] });
    sinks.set(k, { next: a, waiting: new Map(), ff, count: 0 });
    await film.ev(`__runRange(${a}, ${b}, ${fps}, ${k}, 3)`);
    ff.stdin.end(); await new Promise(r => ff.on('close', r));
  }
  if (film.logs.length) console.error('\npage errors:\n' + film.logs.join('\n'));
  film.close();
}

const per = Math.ceil(total / workers), segs = [];
await Promise.all(Array.from({ length: workers }, (_, k) => {
  const a = first + k * per, b = Math.min(last, a + per - 1);
  if (a > b) return null;
  const seg = join(tmp, `seg${String(k).padStart(3, '0')}.mp4`); segs.push(seg);
  return renderRange(k, a, b, seg);
}));
clearInterval(timer); tick(); console.log();
server.close();

segs.sort();
writeFileSync(join(tmp, 'list.txt'), segs.map(s => `file '${s}'`).join('\n'));
const video = join(tmp, 'video.mp4');
spawnSync('ffmpeg', ['-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', join(tmp, 'list.txt'), '-c', 'copy', video], { stdio: 'inherit' });
const mux = args.audio
  ? ['-v', 'error', '-y', '-i', video, '-ss', String(from), '-i', resolve(args.audio), '-map', '0:v', '-map', '1:a', '-c:v', 'copy',
     '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', out]
  : ['-v', 'error', '-y', '-i', video, '-c', 'copy', '-movflags', '+faststart', out];
spawnSync('ffmpeg', mux, { stdio: 'inherit' });
rmSync(tmp, { recursive: true, force: true });

const p = spawnSync('ffprobe', ['-v', 'error', '-count_packets', '-show_entries', 'stream=codec_type,width,height,nb_read_packets:format=duration',
  '-of', 'compact', out]).stdout.toString().trim();
console.log(`done → ${out} in ${((Date.now() - t0) / 1000).toFixed(0)} s\n${p}`);
process.exit(0);
