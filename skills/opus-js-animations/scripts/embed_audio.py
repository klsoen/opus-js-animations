#!/usr/bin/env python3
"""Embed an audio file as window.FILM_AUDIO_B64 in an audio.js beside the film.

A page opened from file:// cannot fetch() files, and routing an <audio> element through
Web Audio yields silence (opaque origin). A base64 script works everywhere, including the
render tools, at ~1.37x the file size. Keep the source as a compressed MP3/AAC.

  python3 embed_audio.py voice.mp3 film/audio.js
"""
import base64, sys

src, out = sys.argv[1], sys.argv[2]
data = base64.b64encode(open(src, 'rb').read()).decode()
with open(out, 'w') as f:
    f.write(f'// {src.split("/")[-1]} as base64 so the film works from file://\nwindow.FILM_AUDIO_B64 = "{data}";\n')
print(f'{out}: {len(data) / 1e6:.2f} MB')
