#!/usr/bin/env python3
"""Find where the words are in a reading, narration, song or dialogue track.

Continuous, reverberant voices (chanting, singing, slow sung speech) often have no true
silence, so plain silence detection finds nothing. This measures loudness every 0.1 s,
treats short dips as breath points, transcribes each breath-to-breath chunk separately
with word timestamps (much more reliable than one long pass, which drifts and merges
repeated phrases), and writes <audio>.align.json.

  python3 align_audio.py voice.mp3 [--lang ar] [--model small] [--dip -30] [--min-gap 3]

Needs: numpy and openai-whisper (pip install -U openai-whisper; ffmpeg on PATH).
Whisper's words are approximate, especially for sung or chanted words (elongated vowels,
repeated phrases). Use them to find boundaries, then take the displayed text from a
canonical source, never from the transcript.
"""
import argparse, json, sys

ap = argparse.ArgumentParser()
ap.add_argument('audio')
ap.add_argument('--lang', default=None, help='language code, e.g. ar, en (default: auto)')
ap.add_argument('--model', default='small')
ap.add_argument('--dip', type=float, default=-30.0, help='dBFS below which a 0.1 s window counts as a dip')
ap.add_argument('--min-gap', type=float, default=3.0, help='merge breath points closer than this (s)')
a = ap.parse_args()

try:
    import numpy as np, whisper
except ImportError:
    sys.exit('needs numpy and openai-whisper: pip install -U openai-whisper')

SR = 16000
audio = whisper.load_audio(a.audio)
dur = len(audio) / SR
win = SR // 10
rms = [20 * np.log10(np.sqrt(np.mean(audio[i:i + win] ** 2)) + 1e-9) for i in range(0, len(audio) - win, win)]

# breath points: centre of each run of quiet windows (leading silence ignored)
dips, run = [], []
for i, v in enumerate(rms):
    if v < a.dip: run.append(i)
    elif run:
        if run[0] > 0: dips.append(round((run[0] + run[-1]) / 2 / 10 + .05, 2))
        run = []
start = next((i / 10 for i, v in enumerate(rms) if v > a.dip), 0.0)
cuts = [start]
for d in dips:
    if d - cuts[-1] >= a.min_gap and dur - d >= 1.0: cuts.append(d)
cuts.append(round(dur, 2))

print(f'{a.audio}: {dur:.2f}s, voice starts {start:.2f}s')
print('quiet dips (breaths):', ', '.join(f'{d:.1f}' for d in dips) or 'none')

model = whisper.load_model(a.model)
chunks = []
for c0, c1 in zip(cuts[:-1], cuts[1:]):
    seg = audio[int(c0 * SR):int(c1 * SR)]
    r = model.transcribe(seg, language=a.lang, fp16=False, word_timestamps=True)
    words = [{'w': w['word'].strip(), 't0': round(c0 + w['start'], 2), 't1': round(c0 + w['end'], 2)}
             for s in r['segments'] for w in s.get('words', [])]
    chunks.append({'t0': c0, 't1': c1, 'text': r['text'].strip(), 'words': words})
    print(f'\n[{c0:6.2f} – {c1:6.2f}] {r["text"].strip()}')
    print('   ' + ' | '.join(f'{w["w"]} {w["t0"]:.1f}' for w in words))

out = a.audio.rsplit('.', 1)[0] + '.align.json'
with open(out, 'w') as f:
    json.dump({'duration': dur, 'start': start, 'dips': dips, 'chunks': chunks}, f, ensure_ascii=False, indent=1)
print(f'\n→ {out}')
print('Check for repeated phrases (speakers and singers often repeat a line) before assigning text to times.')
