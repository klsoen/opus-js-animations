# Audio: sourcing, understanding, generating, voicing, mixing

## Contents
1. The four sources
2. Getting and trimming source audio (a file or a link)
3. Understanding it: analysis and aligning text to a voice
4. Using audio in the page
5. Generating the sound in JavaScript (Web Audio)
6. Dialogue, sound effects and the mix (longer films)
7. Mux and checks
8. Voiceover from a script (ElevenLabs or OpenAI)

## 1. The four sources

Ask which one it is before anything else (`directing.md` §2):

| Source | Picture follows | Tool | Notes |
|---|---|---|---|
| Their own file (voice, reading, song, music) | the audio: every beat is a word or hit | none; `ffmpeg` to take audio from a video | use it untouched (§7) |
| A link (YouTube, or any site yt-dlp supports) | the audio | `get_audio.py` (§2) | say where it came from; reuse rights are the person's call |
| Generated in JavaScript | the story; the score reads the picture's event times | Web Audio in the page, `page_audio.mjs` (§5) | deterministic, rendered offline for export |
| A voiceover from their TTS key | the script: each line is a sync point | `voiceover.py` (§8) | approve the script before voicing it |

Longer films mix several of these (dialogue plus score plus effects, §6). No music under a voice wherever the person asks for none.

The picture and the sound share one timeline defined as data (phrase list, cue list, event
times). Never copy numbers between them by hand; retiming one must retime the other.

## 2. Getting and trimming source audio

Use `scripts/get_audio.py`; it does the steps below and handles the tools:
- **Install**: finds a working yt-dlp, else installs it with Homebrew → pipx → `pip --user` →
  the official standalone binary into `~/.local/bin` (no Python needed). ffmpeg is installed
  with Homebrew when available; otherwise it stops with the install command for the platform.
- **Stale yt-dlp**: most failures ("Unable to extract", HTTP 403, signature errors) are fixed by
  a newer version, so on failure it updates (brew/pipx/pip, or `yt-dlp -U` for the binary) and
  retries once.
- **Output**: `source.wav` (48 kHz), `meta.txt`, and with `--video` a 720p `clip.mp4` plus `sheet.png`.
- **End check**: loudness of the last 0.4 s. A loud tail means the section stops mid-word. This
  happened in practice: a 55 s section cut the last word of a line, found only after the film
  was finished. Take ~10 s more than you need and trim at a measured quiet point.
- `--search "query"` lists the top 8 results (id, length, uploader, title) when there is no URL.

The manual equivalent:

```bash
# a section of an online video (video kept for reading on-screen text; audio extracted)
yt-dlp -q --no-playlist --download-sections "*0-55" --force-keyframes-at-cuts \
  -f "bv*[height<=720]+ba/b[height<=720]" --merge-output-format mp4 -o "clip.%(ext)s" "<url>"
yt-dlp --skip-download --print "%(title)s|%(uploader)s|%(duration)s" --print description "<url>"  # metadata first
ffmpeg -v error -y -i clip.mp4 -vn -c:a libmp3lame -q:a 2 voice.mp3
ffmpeg -v error -y -i clip.mp4 -vf "fps=1/3,scale=640:-1,tile=3x3" sheet_%d.png   # read on-screen text/translation
```

The title, description and on-screen text often identify the content exactly (title,
author, lyrics, speaker). Read them before transcribing.

Trim at a measured quiet point, never mid-word, on a zero crossing, so no fade is needed (§7):
```bash
ffmpeg -v error -y -ss 7.35 -i voice.mp3 -c:a libmp3lame -q:a 2 voice-trimmed.mp3   # add -af "afade=t=in:d=0.005" only if a click remains
```
When trimming the start, keep scene times in the original clip's seconds and apply one
constant offset (`SHIFT`) in the player and renderer; this keeps every measured time valid.

Respect rights: say where the audio came from and let the user decide about reuse.

## 3. Understanding it: analysis and aligning text to a voice

Start with the whole shape of the sound:
```bash
python3 scripts/analyze_audio.py source/source.wav
```
It prints:
- the length, loudness (LUFS) and true peak;
- the pauses;
- sections by energy (quiet, mid, loud), with their times;
- onsets (hits and syllable attacks);
- an estimated tempo with beat times, when there is a steady beat.

It writes `source.analysis.json`, a spectrogram with a labelled time axis (`source.spectrum.png`) and a waveform (`source.wave.png`).
Read the spectrogram: phrases, pauses, beats, swells and faint endings are visible at a glance. Report what you hear before you design
(`directing.md` §3). For music, the beat times are candidate cut points and event times. For a voice, align the words:


**Quiet endings are real.** A speaker or singer often says the last words softly or under a pad. Whisper-small can drop them, so a transcript
that stops early proves nothing. Re-transcribe the last few seconds with a larger model on a loudness-normalised clip before deciding
what the audio contains:
```bash
ffmpeg -ss 15.9 -i clip.mp4 -vn -ac 1 -ar 16000 -af loudnorm=I=-16 tail.wav
python3 -c "import whisper; r = whisper.load_model('medium').transcribe('tail.wav', language='en', word_timestamps=True, condition_on_previous_text=False); print(r['text'])"
```
Keep the user's audio whole: no tail fades or trims beyond a few-millisecond de-click, unless they ask.

```bash
python3 scripts/align_audio.py voice.mp3 --lang en      # or another language code, or omit for auto
```
It prints breath points (loudness dips), a transcript per breath-to-breath chunk with word
times, and writes `voice.align.json`. Then:

1. Take the **displayed text from a canonical source**, not the transcript (see
   `quoted-text.md`). The transcript only locates the words.
2. Look for repeats: speakers and singers often repeat a phrase (a chorus, a
   line said twice for weight). A phrase list must show
   the repeat.
3. Split into phrases at breath points; each phrase gets `t0` (word onset − ~0.2 s) and
   `t1` (next phrase's onset).
4. Silence detection (`silencedetect`) fails on reverberant voices (chant, sung or elongated speech); loudness dips at
   0.1 s resolution work (`astats` RMS per 1600 samples at 16 kHz, or the script above).
5. **Refine cues that picture events land on** (a posture change on a word) from the signal
   itself. Whisper word times can be off by up to ~1 s on elongated or sung words: the first word of
   a window is pinned to the window start, and neighbouring words share boundaries. Two passes
   with different models disagreed by 0.7–0.9 s. Use:
   - **stop consonants** (q, k, t, b, j): a sharp 30–60 ms loudness dip (10 ms RMS windows, local
     minimum > 7 dB below its ±80 ms neighbourhood);
   - **fricatives** (s, sh, f, h): a peak in the ratio of energy above 4 kHz to energy below it (2048-point FFT every 10 ms).
   ```python
   S = np.abs(np.fft.rfft(seg * np.hanning(2048))) ** 2; f = np.fft.rfftfreq(2048, 1 / sr)
   hf = 10 * np.log10(S[f > 4000].sum() / S[(f > 80) & (f < 4000)].sum())   # > ~5 dB: /s/-like
   ```
   Cross-check each cue with two independent measures before timing picture to it.

## 4. Using audio in the page

Pages opened from `file://` can't `fetch()` local files, and an `<audio>` element routed
through Web Audio outputs silence. Embed the file as base64:
```bash
python3 scripts/embed_audio.py voice-trimmed.mp3 film/audio.js
```
The template decodes `window.FILM_AUDIO_B64` with `decodeAudioData` and plays it with an
`AudioBufferSourceNode`; `ac.currentTime - t0` is the film clock, so picture and sound
can't drift. Autoplay needs a click; keep a "click to play" card.

## 5. Procedural score (Web Audio)

Build instruments from oscillators, filters and envelopes; schedule notes from an event list:
- Pad: 2 detuned saws per chord note → low-pass (600→1500→700 Hz sweep) → slow envelope.
- Bell / music box: sine at f + sine at 4.01f (fast decay) + triangle at 2f; reverb and a dotted-eighth delay.
- Pluck arpeggio: triangle → low-pass envelope 3200→500 Hz, 0.7 s decay, alternating pan.
- Bass: sine plus low-passed triangle; kick: sine 130→42 Hz in 0.14 s.
- Reverb: `ConvolverNode` with a generated impulse (noise × (1 − i/n)^2.6, 3.4 s).
- SFX from noise: whoosh (band-pass sweep), firework (whistle + low-pass boom + crackles),
  rain (high-pass + band-pass loop), thunder (low-pass 170 Hz, 3 s decay).

- Foley kit for small physical worlds (music box, Karplus–Strong wire, wing flaps, chirps, paper
  rustle, ceramic clink, creak, per-shot room tones): `styles.md` §2.
- Sounds born from physics (a landing, a petal touching down): `emit()` them from the simulation;
  for export, simulate the whole film once with a baking flag to record them with their times, then
  render them with the score.

Live playback: a look-ahead scheduler (every 40 ms, schedule events up to 1 s ahead) on a
per-session bus; restarting fades the old bus out. Export: render the same event list in an
`OfflineAudioContext`, return it from `__film.wav()` as a base64 WAV, and pull it out with
`scripts/page_audio.mjs` (it also prints integrated LUFS and true peak).
Check levels offline: peak < 1.0, per-section RMS around −17 dBFS. If you can't listen,
say so; meters do not prove the music sounds good.

## 6. Dialogue, sound effects and the mix (longer films)

The pipeline that delivered a 4-minute film with dialogue:
1. **Script with timings**: each line has a speaker, text, target start and emotion.
   Picture timing reads these.
2. **Voices**: `voiceover.py` with the person's ElevenLabs or OpenAI key (§8), one voice per character; or a local TTS
   (macOS `say -v <voice> -o line.aiff`). Render each line to its own file and measure its real duration; the picture's
   timing uses measured durations, not guesses.
3. **Cue sheet**: every visible event (door, footstep, impact, UI beep) exported from the
   picture as `{t, type, x}` data; the sound designer renders a cue per event and pans by
   screen x.
4. **Score**: the composer gets the dialogue map and the dramatic arc (silence at bad news,
   swell at the crest) and leaves space under every line.
5. **Mix** in ffmpeg with separate buses (dialogue, music, SFX): duck music under dialogue
   (`sidechaincompress`, or keyframed volume), keep music ~10 dB under speech in talky
   scenes and let it swell above in action. Master a mix you built to −16 LUFS integrated, true peak ≤ −1 dBTP
   (a user's own recording stays as it is, §7):
   ```bash
   ffmpeg -i mix.wav -af loudnorm=I=-16:TP=-1:LRA=11:print_format=summary -ar 48000 master.wav
   ```
6. **Plot loudness over time** and check the arc lands (dips where planned, peaks where planned).

## 7. Mux and checks

`scripts/render.mjs film.html --audio master.wav` muxes AAC 192k with `-shortest`.
Afterwards:
```bash
ffprobe -v error -count_packets -show_entries stream=codec_type,nb_read_packets:format=duration -of compact film.mp4
```
Frame count must equal duration × fps; the audio stream must exist; spot-check a decoded
frame from the MP4 itself (encoding can band gradients: use CRF ≤ 16 and grain).

**Default to the source audio untouched.** Cut the section on zero crossings (no fade needed), pad silence for holds, and
don't add EQ, denoise, loudness normalisation or reverb. A user asked "why even have to edit the audio instead of using it
as is from the reference video" after a talk clip had been cleaned. If the recording has a flaw, name it and offer a repair
as an option. Diagnose first with a spectrogram and the peak distribution per speaker. In that clip the second speaker's voice
was squashed by the phone's limiter whenever van rumble pushed the signal to the ceiling (3 % of his samples above 0.7 against
0.002 % for the first speaker), so removing the rumble afterwards couldn't undo the distortion. Only a restoration model
(e.g. VoiceFixer, installed in a throwaway venv) could, and the user preferred the original.

## 8. Voiceover from a script (ElevenLabs or OpenAI)

When the person has no audio but has a text-to-speech key.

**1. The script.** Theirs, or one you draft from the brief, as plain text with one phrase per line (a phrase is what one picture
beat will carry) and a blank line where a longer pause belongs. Aim for ~2.3–2.8 words a second for calm narration,
~3.2 for brisk explainers, and read the timing back to them (20 s is ~50 words). Get the script approved before voicing it,
because every call costs them money.

**2. The key.** The script reads it, in order, from:
- `--key-file <path>`;
- the environment variable (`ELEVENLABS_API_KEY`, `OPENAI_API_KEY`);
- `~/.config/opus-js-animations/keys.env`, as `KEY=value` lines.

If they paste a key in the chat, write that file yourself and `chmod 600` it. Never echo it, and never put it in the project, a command line or a log.

**3. The voice.** List what their key can use and offer two or three voices that suit the film:
```bash
python3 scripts/voiceover.py --provider elevenlabs --list-voices
```
- **OpenAI:** `alloy`, `ash`, `ballad`, `coral`, `echo`, `fable`, `nova`, `onyx`, `sage`, `shimmer`, `verse`.
  `gpt-4o-mini-tts` takes `--instructions` for tone and pace ("warm, unhurried, a slight smile").
- **ElevenLabs:** `eleven_multilingual_v2` covers most languages. `--stability` (lower is more expressive), `--similarity` and
  `--style` shape the read.

**4. Voice it.**
```bash
python3 scripts/voiceover.py source/script.txt --provider elevenlabs --voice "Rachel" --out source
python3 scripts/voiceover.py source/script.txt --provider openai --voice onyx --instructions "slow, reverent, low" --out source
python3 scripts/voiceover.py source/script.txt --provider openai --voice onyx --only 3 --out source    # re-voice line 3 only
```
Each line is voiced on its own and joined with measured silences (`--gap` between lines, `--para` at blank lines).
- **Outputs:** `voice.wav`, `voice.mp3`, and `voice.align.json`, which has the same shape as `align_audio.py` output, with one chunk per
  line and exact line boundaries.
- **Word times:** ElevenLabs returns them from its character alignment. For OpenAI, run `align_audio.py` when picture events must
  land on words.
- **Re-takes:** takes are cached in `lines/`, so changing one line re-voices only that line.

**5. Then treat it like any recorded voice:** analyse it (§3), report what you hear, and time the treatment to the measured lines.
Name the provider and voice in the post description when their terms ask for it.
