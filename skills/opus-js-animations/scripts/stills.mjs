#!/usr/bin/env node
// Exact stills and labelled contact sheets, drawn by seek(t) (never a realtime screenshot).
//
//   node stills.mjs film.html --times 0.5,3,7.2              individual JPEGs
//   node stills.mjs film.html --every 2 --sheet              whole film, one frame per 2 s
//   node stills.mjs film.html --range 6.6:7.2:0.0333 --sheet frame-by-frame strip at a handoff
//   node stills.mjs film.html --times 12,18 --crop 380,1040,440,380 --sheet   1:1 detail crops
//
// Options: --out dir (default <film dir>/stills)  --cell 300 (sheet cell width)  --cols 6
//          --png (lossless frames)  --ss 2 (supersampled, as render.mjs --ss 2)  --no-gpu
// With --ss, crops and cells stay in film pixels (the sheet boxes the supersampled frame down); single stills keep the full canvas.
// Read every sheet you make; a sheet can't judge pacing, so also watch a render.
import { mkdirSync, writeFileSync } from 'node:fs';
import { join, dirname, resolve } from 'node:path';
import { openFilm, grab, parseArgs } from './lib.mjs';

const args = parseArgs(process.argv.slice(2));
const html = args._[0];
if (!html) { console.error('usage: node stills.mjs <film.html> (--times a,b | --range a:b:step | --every s) [--sheet] [--crop x,y,w,h] [--ss 2]'); process.exit(1); }
const ss = Math.max(1, Math.round(Number(args.ss || 1)));
const film = await openFilm(html, { gpu: !args['no-gpu'], ss });
const { duration } = film.info, w = film.info.w / ss, h = film.info.h / ss;

let times;
if (args.times) times = String(args.times).split(',').map(Number);
else if (args.range) { const [a, b, s] = String(args.range).split(':').map(Number); times = []; for (let t = a; t <= b + 1e-9; t += s) times.push(+t.toFixed(4)); }
else { const s = Number(args.every || Math.max(1, duration / 12)); times = []; for (let t = s / 2; t < duration; t += s) times.push(+t.toFixed(3)); }

const outDir = resolve(args.out || join(dirname(resolve(html)), 'stills'));
mkdirSync(outDir, { recursive: true });
const crop = args.crop ? String(args.crop).split(',').map(Number) : null;

if (args.sheet) {
  const cols = Number(args.cols || Math.min(times.length, crop ? 4 : 6));
  const cellW = Number(args.cell || (crop ? crop[2] : 300));
  const src = crop || [0, 0, w, h];
  const cellH = Math.round(cellW * src[3] / src[2]);
  const url = await film.ev(`(() => {
    const times = ${JSON.stringify(times)}, src = ${JSON.stringify(src.map(v => v * ss))}, cols = ${cols}, cw = ${cellW}, ch = ${cellH}, lab = 26;
    const rows = Math.ceil(times.length / cols), main = document.getElementById('c') || document.querySelector('canvas');
    const s = document.createElement('canvas'); s.width = cols * cw; s.height = rows * (ch + lab);
    const x = s.getContext('2d'); x.fillStyle = '#111'; x.fillRect(0, 0, s.width, s.height);
    x.font = '15px ui-monospace, Menlo, monospace'; x.textBaseline = 'middle';
    times.forEach((t, i) => {
      __film.seek(t);
      const cx = (i % cols) * cw, cy = Math.floor(i / cols) * (ch + lab);
      x.drawImage(main, src[0], src[1], src[2], src[3], cx, cy, cw, ch);
      x.fillStyle = '#ddd'; x.fillText(t.toFixed(t % 1 ? 3 : 1) + 's', cx + 8, cy + ch + lab / 2);
    });
    return s.toDataURL('image/jpeg', .9);
  })()`);
  const name = `sheet_${times[0]}-${times[times.length - 1]}${crop ? '_crop' : ''}.jpg`;
  writeFileSync(join(outDir, name), Buffer.from(url.split(',')[1], 'base64'));
  console.log(join(outDir, name));
} else {
  for (const t of times) {
    const ext = args.png ? 'png' : 'jpg';
    const buf = await grab(film.ev, t, args.png ? 'image/png' : 'image/jpeg', .92);
    writeFileSync(join(outDir, `t_${t}.${ext}`), buf);
  }
  console.log(`${times.length} stills → ${outDir}`);
}
if (film.logs.length) console.error('page errors:\n' + film.logs.join('\n'));
film.close();
