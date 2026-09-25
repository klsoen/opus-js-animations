#!/usr/bin/env node
// Proves the contract: seek(t) is pure. The same t twice, and a cold jump to t after
// seeking elsewhere, must give identical pixels. A failure means something in the draw
// path depends on history (Math.random, frame counters, mutable state), which shows up as
// flicker and makes the exported MP4 differ from what you inspected.
//
//   node verify.mjs film.html [--times 0.5,10,20] [--ss 2]   (default: 9 times across the film; --ss checks the supersampled path)
import { createHash } from 'node:crypto';
import { openFilm, parseArgs } from './lib.mjs';

const args = parseArgs(process.argv.slice(2));
const film = await openFilm(args._[0], { gpu: !args['no-gpu'], ss: Math.max(1, Math.round(Number(args.ss || 1))) });
const { duration, w, h, gpu } = film.info;
const times = args.times ? String(args.times).split(',').map(Number)
  : Array.from({ length: 9 }, (_, i) => +(duration * (i + .5) / 9).toFixed(3));

const hash = async t => {
  const px = await film.ev(`(() => { __film.seek(${t}); const c = document.getElementById('c') || document.querySelector('canvas');
    return c.toDataURL('image/png'); })()`);
  return createHash('sha1').update(px).digest('hex').slice(0, 12);
};
let fail = 0;
console.log(`${w}×${h}, ${duration}s, GPU: ${gpu}`);
for (const t of times) {
  const a = await hash(t), b = await hash(t);
  await hash((t + duration / 2) % duration);        // wander off
  const c = await hash(t);                           // cold jump back
  const ok = a === b && a === c;
  if (!ok) fail++;
  console.log(`${ok ? 'ok  ' : 'FAIL'} t=${t}  ${a} ${b} ${c}`);
}
if (film.logs.length) { console.log('page errors:\n' + film.logs.join('\n')); fail++; }
film.close();
console.log(fail ? `${fail} problem(s)` : 'seek(t) is pure at every tested time');
process.exit(fail ? 1 : 0);
