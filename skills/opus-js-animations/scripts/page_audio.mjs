#!/usr/bin/env node
// Pull a film's own procedural soundtrack out of the page as a WAV, for render.mjs --audio.
// The page must expose __film.wav(): a Promise of a base64 WAV rendered with OfflineAudioContext
// from the same score (and the same physics-born events) the picture uses.
//
//   node page_audio.mjs film/index.html --out film/mix.wav
//   node render.mjs film/index.html --fps 30 --audio film/mix.wav --out film/film.mp4
import { writeFileSync } from 'node:fs';
import { resolve, dirname, join } from 'node:path';
import { spawnSync } from 'node:child_process';
import { openFilm, parseArgs } from './lib.mjs';

const args = parseArgs(process.argv.slice(2));
const html = args._[0];
if (!html) { console.error('usage: node page_audio.mjs <film.html> [--out mix.wav]'); process.exit(1); }
const out = resolve(args.out || join(dirname(resolve(html)), 'mix.wav'));
const film = await openFilm(html, { gpu: !args['no-gpu'] });
if (!(await film.ev('typeof __film.wav === "function"'))) { console.error('page has no __film.wav()'); film.close(); process.exit(1); }
const b64 = await film.ev('__film.wav()');
writeFileSync(out, Buffer.from(b64, 'base64'));
film.close();
console.log(out);
// levels: you usually can't listen, so at least read them
const r = spawnSync('ffmpeg', ['-hide_banner', '-nostats', '-i', out, '-af', 'ebur128=peak=true', '-f', 'null', '-'], { encoding: 'utf8' });
const s = r.stderr.slice(r.stderr.lastIndexOf('Summary:'));
const I = /I:\s+(-?[\d.]+) LUFS/.exec(s)?.[1], P = /Peak:\s+(-?[\d.]+) dBFS/.exec(s)?.[1];
if (I) console.log(`integrated ${I} LUFS · true peak ${P} dBFS${+P > -1 ? '  (hot: normalise before muxing, audio.md §7)' : ''}`);
