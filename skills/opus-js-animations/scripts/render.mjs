#!/usr/bin/env node
// Frame-exact MP4 export. Every frame is __film.seek(i / fps), so nothing drops or drifts,
// whatever the machine speed. Long films split across parallel Chrome workers.
//
//   node render.mjs film/index.html [--fps 30] [--audio mix.wav] [--out film.mp4]
//                   [--from 0 --to 12] [--workers 4] [--crf 16] [--ss 2] [--no-gpu] [--fast]
//
// --audio is muxed and the video is cut to the shorter of the two (-shortest).
// Without --audio the output is silent (use for section previews).
// Frames are captured losslessly as PNG and converted to standard HD video: BT.709, limited (TV) range, tagged, so phones and
// Instagram/TikTok/X transcoders read the colours and blacks correctly. --fast captures JPEG (q .95) instead: for quick previews only.
// --ss 2 supersamples: the film draws every frame at 2× (?ss=2; the film must support it, see references/delivery.md) and each frame
// is scaled back down with Lanczos in 16-bit RGB before the BT.709 conversion. Four samples per pixel: smoother edges, text and fine detail.
import { spawn, spawnSync } from 'node:child_process';
import { mkdtempSync, writeFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, dirname, resolve } from 'node:path';
import { openFilm, grab, parseArgs } from './lib.mjs';

const args = parseArgs(process.argv.slice(2));
const html = args._[0];
if (!html) { console.error('usage: node render.mjs <film.html> [--fps 30] [--audio file] [--out file.mp4] [--from s --to s] [--workers n] [--ss 2]'); process.exit(1); }
const fps = Number(args.fps || 30), workers = Math.max(1, Number(args.workers || 1)), crf = String(args.crf || 16);
const ss = Math.max(1, Math.round(Number(args.ss || 1)));
const out = resolve(args.out || join(dirname(resolve(html)), 'film.mp4'));

const probe = await openFilm(html, { gpu: !args['no-gpu'] });
const { duration, w: ow, h: oh, gpu } = probe.info;                  // the film's own size
probe.close();
let w = ow, h = oh;
if (ss > 1) {                                                          // the canvas must hold exactly ss× the pixels
  const p2 = await openFilm(html, { gpu: !args['no-gpu'], ss }); ({ w, h } = p2.info); p2.close();
  if (w !== ow * ss || h !== oh * ss) { console.error(`--ss ${ss}: the film drew ${w}×${h}, not ${ow * ss}×${oh * ss}. Does it read ?ss= (references/delivery.md §3)?`); process.exit(1); }
}
const from = Number(args.from || 0), to = Math.min(Number(args.to ?? duration), duration);
const first = Math.round(from * fps), last = Math.ceil(to * fps) - 1, total = last - first + 1;
console.log(`${ow}×${oh}${ss > 1 ? ` (drawn at ${w}×${h}, ${ss}× supersampled)` : ''} · ${fps} fps · frames ${first}–${last} (${total}) · ${workers} worker(s) · GPU: ${gpu}`);

const tmp = mkdtempSync(join(tmpdir(), 'render-'));
const t0 = Date.now();
let done = 0;
const tick = () => process.stdout.write(`\r${done}/${total} frames · ${((Date.now() - t0) / 1000).toFixed(0)}s`);

async function renderRange(a, b, segPath) {
  const film = await openFilm(html, { gpu: !args['no-gpu'], ss });
  const fast = !!args.fast;
  const down = ss > 1 ? `scale=${ow}:${oh}:flags=lanczos+accurate_rnd${fast ? '' : ',format=rgb48le'},` : '';
  const toHD = down + (fast ? 'scale=in_range=pc:in_color_matrix=bt601:' : 'scale=') + 'out_range=tv:out_color_matrix=bt709:flags=accurate_rnd+full_chroma_int,format=yuv420p,setparams=range=tv:colorspace=bt709:color_primaries=bt709:color_trc=bt709';
  const ff = spawn('ffmpeg', ['-v', 'error', '-y', '-f', 'image2pipe', '-framerate', String(fps), '-c:v', fast ? 'mjpeg' : 'png', '-i', '-',
    '-vf', toHD, '-color_range', 'tv', '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709',
    '-c:v', 'libx264', '-preset', 'slow', '-crf', crf, '-profile:v', 'high', segPath], { stdio: ['pipe', 'inherit', 'inherit'] });
  for (let i = a; i <= b; i++) {
    const buf = await grab(film.ev, i / fps, fast ? 'image/jpeg' : 'image/png');
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    done++; if (done % fps === 0) tick();
  }
  ff.stdin.end();
  await new Promise(r => ff.on('close', r));
  if (film.logs.length) console.error('\npage errors:\n' + film.logs.join('\n'));
  film.close();
}

const per = Math.ceil(total / workers), segs = [];
await Promise.all(Array.from({ length: workers }, (_, k) => {
  const a = first + k * per, b = Math.min(last, a + per - 1);
  if (a > b) return null;
  const seg = join(tmp, `seg${String(k).padStart(3, '0')}.mp4`); segs.push(seg);
  return renderRange(a, b, seg);
}));
tick(); console.log();

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
console.log(`done → ${out}\n${p}`);
