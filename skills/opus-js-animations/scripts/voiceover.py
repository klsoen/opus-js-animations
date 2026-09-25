#!/usr/bin/env python3
"""Voice a script with a text-to-speech API (ElevenLabs or OpenAI), line by line, with timings.

  python3 voiceover.py script.txt --provider elevenlabs [--voice "Rachel" | <voice_id>] [--model eleven_multilingual_v2]
  python3 voiceover.py script.txt --provider openai [--voice coral] [--model gpt-4o-mini-tts] [--instructions "warm, unhurried"]
  python3 voiceover.py --provider elevenlabs --list-voices
  python3 voiceover.py script.txt --provider openai --only 4          re-voice line 4 only, keep the other takes

The script is plain text: one phrase per line, in the order spoken. A blank line is a longer pause (a paragraph).
Each line is voiced on its own, so phrase boundaries are exact, one line can be re-voiced without redoing the rest,
and the picture can be timed to the measured durations instead of guesses.

The key comes from the environment (ELEVENLABS_API_KEY or OPENAI_API_KEY), from --key-file (a file holding only
the key), or from ~/.config/opus-js-animations/keys.env (KEY=value lines; keep it chmod 600). It is never printed or written.

Writes into --out (default ./source):
  voice.wav          the whole voiceover: 48 kHz mono, lines joined with --gap / --para seconds of silence
  voice.mp3          the same, for embed_audio.py
  voice.align.json   the same format as align_audio.py: one chunk per line with t0/t1 and, from ElevenLabs,
                     word times from the API's character alignment (OpenAI returns none: run align_audio.py)
  lines/NN.mp3       each line's take, reused unless --only or --redo names it

Stdlib only (plus ffmpeg on PATH). Voice names, models and prices change: --list-voices shows what the key can use.
Say which provider and voice made the audio, and check its terms for the platform the film is for.
"""
import argparse, base64, json, os, shutil, subprocess, sys, urllib.error, urllib.request, wave
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument('script', nargs='?', help='text file: one phrase per line, blank line = paragraph pause')
ap.add_argument('--provider', choices=['elevenlabs', 'openai'], required=True)
ap.add_argument('--voice', help='ElevenLabs: voice name or id (default Rachel). OpenAI: alloy, ash, ballad, coral, echo, fable, nova, onyx, sage, shimmer, verse (default coral)')
ap.add_argument('--model', help='ElevenLabs default eleven_multilingual_v2; OpenAI default gpt-4o-mini-tts')
ap.add_argument('--instructions', help='OpenAI gpt-4o-mini-tts only: how to speak (tone, pace, accent)')
ap.add_argument('--stability', type=float, default=.5, help='ElevenLabs voice stability 0–1 (lower = more expressive)')
ap.add_argument('--similarity', type=float, default=.75, help='ElevenLabs similarity boost 0–1')
ap.add_argument('--style', type=float, default=0.0, help='ElevenLabs style exaggeration 0–1')
ap.add_argument('--speed', type=float, default=1.0, help='speaking rate (OpenAI 0.25–4; ElevenLabs 0.7–1.2)')
ap.add_argument('--gap', type=float, default=.35, help='silence between lines (s)')
ap.add_argument('--para', type=float, default=.9, help='silence at a blank line (s)')
ap.add_argument('--lead', type=float, default=.25, help='silence before the first line (s)')
ap.add_argument('--tail', type=float, default=.8, help='silence after the last line (s)')
ap.add_argument('--out', default='source')
ap.add_argument('--only', type=int, nargs='*', help='re-voice only these line numbers (1-based), keep the rest')
ap.add_argument('--redo', action='store_true', help='re-voice every line')
ap.add_argument('--key-file')
ap.add_argument('--list-voices', action='store_true')
a = ap.parse_args()

ENV = {'elevenlabs': 'ELEVENLABS_API_KEY', 'openai': 'OPENAI_API_KEY'}[a.provider]
SR = 48000


def api_key():
    if a.key_file:
        return Path(a.key_file).expanduser().read_text().strip()
    if os.environ.get(ENV):
        return os.environ[ENV].strip()
    cfg = Path.home() / '.config' / 'opus-js-animations' / 'keys.env'
    if cfg.exists():
        for line in cfg.read_text().splitlines():
            k, _, v = line.partition('=')
            if k.strip() == ENV and v.strip():
                return v.strip().strip('"\'')
    sys.exit(f'No {ENV}. Set it in the environment, pass --key-file, or add {ENV}=... to {cfg} (chmod 600).')


def request(url, key, body=None, accept='application/json'):
    headers = {'Accept': accept}
    if a.provider == 'elevenlabs': headers['xi-api-key'] = key
    else: headers['Authorization'] = f'Bearer {key}'
    data = None
    if body is not None:
        headers['Content-Type'] = 'application/json'
        data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, headers=headers, method='POST' if data else 'GET')
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            return r.read()
    except urllib.error.HTTPError as e:
        msg = e.read().decode(errors='replace')[:600]
        sys.exit(f'{a.provider} API error {e.code}: {msg}')
    except urllib.error.URLError as e:
        sys.exit(f'{a.provider} API unreachable: {e.reason}')


def list_voices(key):
    if a.provider == 'openai':
        print('OpenAI voices: alloy, ash, ballad, coral, echo, fable, nova, onyx, sage, shimmer, verse (see the API docs for new ones)')
        return
    vs = json.loads(request('https://api.elevenlabs.io/v1/voices', key)).get('voices', [])
    for v in vs:
        labels = ', '.join(f'{k}: {x}' for k, x in (v.get('labels') or {}).items())
        print(f"{v['voice_id']}  {v['name']:<22} {v.get('category', ''):<12} {labels}")


def eleven_voice_id(key, want):
    want = want or 'Rachel'
    if len(want) >= 20 and want.isalnum():
        return want
    vs = json.loads(request('https://api.elevenlabs.io/v1/voices', key)).get('voices', [])
    for v in vs:
        if v['name'].lower() == want.lower() or v['name'].lower().startswith(want.lower() + ' '):
            return v['voice_id']
    sys.exit(f'No ElevenLabs voice named "{want}". Run with --list-voices.')


def voice_line(key, text, voice_id):
    """Returns (mp3 bytes, [(word, t0, t1)] or None)."""
    if a.provider == 'elevenlabs':
        body = {'text': text, 'model_id': a.model or 'eleven_multilingual_v2',
                'voice_settings': {'stability': a.stability, 'similarity_boost': a.similarity, 'style': a.style,
                                   'use_speaker_boost': True, **({'speed': a.speed} if a.speed != 1.0 else {})}}
        r = json.loads(request(f'https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/with-timestamps?output_format=mp3_44100_128', key, body))
        al = r.get('alignment') or r.get('normalized_alignment') or {}
        return base64.b64decode(r['audio_base64']), chars_to_words(al)
    body = {'model': a.model or 'gpt-4o-mini-tts', 'voice': a.voice or 'coral', 'input': text, 'response_format': 'mp3'}
    if a.speed != 1.0: body['speed'] = a.speed
    if a.instructions: body['instructions'] = a.instructions
    return request('https://api.openai.com/v1/audio/speech', key, body, accept='audio/mpeg'), None


def chars_to_words(al):
    cs, s0, s1 = al.get('characters') or [], al.get('character_start_times_seconds') or [], al.get('character_end_times_seconds') or []
    words, cur, t0 = [], '', None
    for c, a0, a1 in zip(cs, s0, s1):
        if c.isspace():
            if cur: words.append((cur, t0, prev)); cur = ''
            continue
        if not cur: t0 = a0
        cur += c; prev = a1
    if cur: words.append((cur, t0, prev))
    return words


def pcm(path):
    """Decode any audio file to 48 kHz mono s16 PCM bytes."""
    return subprocess.run(['ffmpeg', '-v', 'error', '-i', str(path), '-ac', '1', '-ar', str(SR), '-f', 's16le', '-'],
                          capture_output=True, check=True).stdout


if not shutil.which('ffmpeg'):
    sys.exit('needs ffmpeg on PATH (macOS: brew install ffmpeg)')
key = api_key()
if a.list_voices:
    list_voices(key); sys.exit()
if not a.script:
    sys.exit('give a script file (one phrase per line)')

raw = Path(a.script).read_text(encoding='utf-8').splitlines()
lines, breaks = [], set()                      # breaks: indices of lines that follow a blank line
for s in raw:
    if not s.strip():
        if lines: breaks.add(len(lines))
        continue
    lines.append(s.strip())
if not lines:
    sys.exit('the script is empty')

out = Path(a.out); (out / 'lines').mkdir(parents=True, exist_ok=True)
voice_id = eleven_voice_id(key, a.voice) if a.provider == 'elevenlabs' else None
todo = set(range(1, len(lines) + 1)) if a.redo else set(a.only or [])
meta_path = out / 'lines' / 'takes.json'
takes = json.loads(meta_path.read_text()) if meta_path.exists() else {}

for i, text in enumerate(lines, 1):
    f = out / 'lines' / f'{i:02d}.mp3'
    same = takes.get(str(i), {}).get('text') == text
    if f.exists() and same and i not in todo:
        continue
    print(f'voicing {i}/{len(lines)}: {text[:70]}')
    audio, words = voice_line(key, text, voice_id)
    f.write_bytes(audio)
    takes[str(i)] = {'text': text, 'provider': a.provider, 'voice': a.voice or ('Rachel' if a.provider == 'elevenlabs' else 'coral'),
                     'model': a.model, 'words': words}
meta_path.write_text(json.dumps(takes, ensure_ascii=False, indent=1))

# join the takes with measured silences
silence = lambda s: b'\x00\x00' * int(round(s * SR))
buf, chunks, t = bytearray(silence(a.lead)), [], a.lead
for i, text in enumerate(lines, 1):
    if i > 1:
        g = a.para if (i - 1) in breaks else a.gap
        buf += silence(g); t += g
    p = pcm(out / 'lines' / f'{i:02d}.mp3')
    d = len(p) / 2 / SR
    ws = takes[str(i)].get('words')
    chunks.append({'t0': round(t, 3), 't1': round(t + d, 3), 'text': text,
                   'words': [{'w': w, 't0': round(t + w0, 3), 't1': round(t + w1, 3)} for w, w0, w1 in ws] if ws else []})
    buf += p; t += d
buf += silence(a.tail); t += a.tail

with wave.open(str(out / 'voice.wav'), 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(bytes(buf))
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(out / 'voice.wav'), '-c:a', 'libmp3lame', '-q:a', '2', str(out / 'voice.mp3')], check=True)
(out / 'voice.align.json').write_text(json.dumps({'duration': round(t, 3), 'start': a.lead, 'dips': [], 'chunks': chunks,
                                                  'source': {'provider': a.provider, 'voice': a.voice, 'model': a.model}},
                                                 ensure_ascii=False, indent=1))
for c in chunks:
    print(f"[{c['t0']:6.2f} – {c['t1']:6.2f}] {c['text']}")
print(f'\n{len(lines)} lines, {t:.2f} s → {out / "voice.wav"}, {out / "voice.mp3"}, {out / "voice.align.json"}')
if a.provider == 'openai':
    print('OpenAI returns no word times: run align_audio.py on voice.wav if picture events must land on words.')
