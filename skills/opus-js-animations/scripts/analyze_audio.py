#!/usr/bin/env python3
"""Study a soundtrack before directing to it: length, loudness, pauses, sections, hits and tempo.

  python3 analyze_audio.py source/source.wav [--out source] [--silence -35] [--min-pause .25]

Prints a short report and writes, next to the audio (or into --out):
  <name>.analysis.json   duration, loudness (LUFS, true peak), pauses, a 10 Hz loudness contour, sections by
                         energy, onsets and an estimated tempo with beat times (needs numpy)
  <name>.spectrum.png    a spectrogram with a labelled time axis: read it to see phrases, pauses, hits and swells
  <name>.wave.png        the waveform, for a quick look at the shape of the piece

Use it on anything (a voice, a reading, a song, a score you generated). For words in time, run
align_audio.py as well. ffmpeg on PATH; numpy is optional (without it: no onsets, tempo or sections).
"""
import argparse, json, re, subprocess, sys
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument('audio')
ap.add_argument('--out')
ap.add_argument('--silence', type=float, default=-35.0, help='dBFS below which audio counts as a pause')
ap.add_argument('--min-pause', type=float, default=.25, help='shortest pause to report (s)')
a = ap.parse_args()

src = Path(a.audio)
out = Path(a.out) if a.out else src.parent
out.mkdir(parents=True, exist_ok=True)
stem = out / src.stem


def ff(*args):
    return subprocess.run(['ffmpeg', '-hide_banner', '-nostats', *args], capture_output=True, text=True).stderr


# duration and format
probe = json.loads(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration:stream=sample_rate,channels,codec_name',
                                   '-of', 'json', str(src)], capture_output=True, text=True).stdout or '{}')
dur = float(probe.get('format', {}).get('duration', 0))
st = next((s for s in probe.get('streams', []) if s.get('sample_rate')), {})

# loudness (EBU R128) and true peak
log = ff('-i', str(src), '-af', 'ebur128=peak=true', '-f', 'null', '-')
lufs = re.findall(r'I:\s+(-?[\d.]+) LUFS', log)
peak = re.findall(r'Peak:\s+(-?[\d.]+) dBFS', log)
lra = re.findall(r'LRA:\s+(-?[\d.]+) LU', log)

# pauses
log = ff('-i', str(src), '-af', f'silencedetect=noise={a.silence}dB:d={a.min_pause}', '-f', 'null', '-')
starts = [float(x) for x in re.findall(r'silence_start: (-?[\d.]+)', log)]
ends = [float(x) for x in re.findall(r'silence_end: ([\d.]+)', log)]
pauses = [[round(max(0, s), 2), round(e, 2)] for s, e in zip(starts, ends + [dur] * (len(starts) - len(ends)))]

report = {'file': str(src), 'duration': round(dur, 3), 'sample_rate': int(st.get('sample_rate', 0) or 0), 'channels': st.get('channels'),
          'lufs': float(lufs[-1]) if lufs else None, 'true_peak_dbfs': float(peak[-1]) if peak else None,
          'loudness_range_lu': float(lra[-1]) if lra else None, 'pauses': pauses}

# contour, sections, onsets, tempo
try:
    import numpy as np
    SR = 22050
    x = np.frombuffer(subprocess.run(['ffmpeg', '-v', 'error', '-i', str(src), '-ac', '1', '-ar', str(SR), '-f', 'f32le', '-'],
                                     capture_output=True).stdout, dtype=np.float32)
    hop = SR // 10
    n = len(x) // hop
    rms = np.array([np.sqrt(np.mean(x[i * hop:(i + 1) * hop] ** 2) + 1e-12) for i in range(n)])
    db = 20 * np.log10(rms + 1e-9)
    report['contour_db_10hz'] = [round(float(v), 1) for v in db]
    # sections: smooth the loudness over 2 s and split where it crosses its own median by a margin
    k = 20
    sm = np.convolve(db, np.ones(k) / k, mode='same') if n > k else db
    med = float(np.median(sm[sm > -60])) if np.any(sm > -60) else -30.0
    lvl = np.where(sm > med + 3, 'loud', np.where(sm < med - 6, 'quiet', 'mid'))
    sections, s0 = [], 0
    for i in range(1, n + 1):
        if i == n or lvl[i] != lvl[s0]:
            if (i - s0) / 10 >= 1.5 or not sections:
                sections.append({'t0': round(s0 / 10, 1), 't1': round(i / 10, 1), 'level': str(lvl[s0]), 'mean_db': round(float(np.mean(db[s0:i])), 1)})
            else:
                sections[-1]['t1'] = round(i / 10, 1)
            s0 = i
    report['sections'] = sections
    # onsets: positive spectral flux, peak-picked
    N, H = 1024, 256
    win = np.hanning(N)
    frames = 1 + max(0, (len(x) - N) // H)
    mag = np.abs(np.fft.rfft(np.stack([x[i * H:i * H + N] * win for i in range(frames)]), axis=1)) if frames > 2 else np.zeros((1, N // 2 + 1))
    flux = np.maximum(0, np.diff(np.log1p(mag), axis=0)).sum(axis=1)
    flux = (flux - flux.mean()) / (flux.std() + 1e-9)
    fr = SR / H
    thr = np.convolve(flux, np.ones(int(fr * .5)) / int(fr * .5), mode='same') + .8
    on = [i for i in range(1, len(flux) - 1) if flux[i] > thr[i] and flux[i] >= flux[i - 1] and flux[i] >= flux[i + 1]]
    onsets, last = [], -1
    for i in on:
        if i - last >= fr * .1: onsets.append(round((i + 1) / fr, 3)); last = i
    report['onsets'] = onsets
    # tempo: autocorrelation of the flux between 60 and 180 BPM
    if len(flux) > fr * 8:
        f = flux - flux.mean()
        ac = np.correlate(f, f, mode='full')[len(f) - 1:]
        lo, hi = int(fr * 60 / 180), int(fr * 60 / 60)
        lag = lo + int(np.argmax(ac[lo:hi]))
        bpm = 60 * fr / lag
        strength = float(ac[lag] / (ac[0] + 1e-9))
        report['tempo'] = {'bpm': round(bpm, 1), 'confidence': round(strength, 2),
                           'note': 'steady beat' if strength > .3 else 'no steady beat (speech, chant or free time)'}
        if strength > .3:
            period = lag / fr
            first = onsets[0] if onsets else 0.0
            report['beats'] = [round(first + k * period, 3) for k in range(int((dur - first) / period) + 1)]
except ImportError:
    report['note'] = 'numpy not installed: no contour, sections, onsets or tempo (pip install numpy)'

(stem.parent / f'{stem.name}.analysis.json').write_text(json.dumps(report, indent=1))
ff('-y', '-i', str(src), '-lavfi', 'showspectrumpic=s=1600x420:legend=1:scale=log:fscale=log:stop=8000', str(stem) + '.spectrum.png')
ff('-y', '-i', str(src), '-filter_complex', 'aformat=channel_layouts=mono,showwavespic=s=1600x240:colors=#d9b25a', '-frames:v', '1', str(stem) + '.wave.png')

# the report
print(f"{src.name}: {dur:.2f} s · {report['sample_rate']} Hz · {report['channels']} ch")
if report['lufs'] is not None:
    print(f"loudness {report['lufs']:.1f} LUFS · true peak {report['true_peak_dbfs']:.1f} dBFS · range {report['loudness_range_lu']:.1f} LU")
if pauses:
    print('pauses: ' + ', '.join(f'{p[0]:.2f}–{p[1]:.2f}' for p in pauses[:40]) + (' …' if len(pauses) > 40 else ''))
else:
    print(f'pauses: none below {a.silence} dB (reverberant voice or continuous music: use align_audio.py for breath points)')
for s in report.get('sections', []):
    print(f"  {s['t0']:6.1f}–{s['t1']:6.1f} s  {s['level']:<5} {s['mean_db']:6.1f} dB")
if 'tempo' in report:
    print(f"tempo ≈ {report['tempo']['bpm']} BPM ({report['tempo']['note']}, confidence {report['tempo']['confidence']})")
if report.get('onsets'):
    print(f"{len(report['onsets'])} onsets (hits and syllable attacks); first few: " + ', '.join(f'{t:.2f}' for t in report['onsets'][:12]))
if report['true_peak_dbfs'] is not None and report['true_peak_dbfs'] > -.1:
    print('warning: the peak touches 0 dBFS; listen for clipping before building to it')
print(f"→ {stem}.analysis.json, {stem}.spectrum.png, {stem}.wave.png (read the spectrogram: phrases, pauses and hits are visible)")
