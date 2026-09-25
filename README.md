# opus-js-animations

**Claude Opus 5.5 directs and renders films in JavaScript: from a spoken idea to a frame-exact MP4.**

A skill and plugin for [Claude Code](https://claude.com/claude-code) that works like a film director:
1. It asks where your sound comes from.
2. It listens to it.
3. It asks you the questions a director asks.
4. It pitches a scene-by-scene treatment.
5. Only after your go, it writes the whole film as JavaScript and renders it frame by frame with your audio,
   for Reels, TikTok, Shorts, X or YouTube.

<p align="center">
  <img src="docs/shaml-opening-3s.gif" width="250" alt="The opening of Shaml: a gold medallion of cut paper bursts into spiral arms around a white-gold sun, then gathers above two men">
  &nbsp;
  <img src="docs/script-of-me-opening.gif" width="250" alt="The opening of The Script of Me: a clock at half past midnight, a pendulum swinging in a pool of light, then the clock's parts laid out as No. 1, The Clock">
</p>
<p align="center"><sub>Opening seconds of <i>Shaml</i> (a paper-lightbox scene) and <i>The Script of Me</i> (an "ingredients" reel for a journal page). Every frame is Canvas 2D, written by Opus 5.5.</sub></p>

## Why Opus 5.5

Claude Opus 5.5 is a big step up at generating JavaScript animation. It can hold a whole film in its head and write it as one coherent program:
- a medallion of 336 cut-paper pieces, each with its own closed-form motion;
- parallax sheets of a city;
- puppets on skeletons;
- a wet-floor reflection;
- bilingual typography.

Then it reads its own frames and fixes what it sees. Earlier models could make a bouncing logo; Opus 5.5 can make the film.

What it needed was a **director's process**, so the film is the one you meant, and a **render pipeline that never drops a frame**,
so what you approve is exactly what you post. That is this skill.

## How it works: five conversations before a single frame

| | Step | What happens |
|---|---|---|
| 1 | **Brief** | You describe the video. It reflects the brief back and, if you have a reference clip, measures it (length, cuts, style). |
| 2 | **Sound** | It asks where the audio comes from, and takes one of four routes (below). |
| 3 | **Listening** | It analyses the audio. Then it tells you **what it hears**: the structure, key words and hits, tempo and mood. |
| 4 | **Direction** | It asks about the look, pacing, **2D or 3D (three.js or not)**, the points a muted viewer must get, formats and text on screen. |
| 5 | **Treatment** | You get a director's overview. **Nothing is built until you say go.** |

**Sound routes (step 2):**
- your own file;
- a YouTube or other link, downloaded with **yt-dlp**;
- music and effects **generated in JavaScript** (Web Audio);
- a **voiceover from your ElevenLabs or OpenAI key**.

**Listening (step 3):** it measures length, loudness, pauses, sections and tempo, and reads a spectrogram. It transcribes and aligns any
voice with Whisper, and checks lyrics or quotations against the canonical text.

**Treatment (step 5):**
- a logline and the one central image;
- the look and palette;
- every scene timed to the audio, with camera, light and text.

After the go it builds, then **checks its own work**:
- a purity test on every frame;
- contact sheets and frame-by-frame strips;
- 1:1 crops of faces and hands.

Then it renders a master and an upload copy for each format, made to stay crisp after the platform's re-encode:
lossless frames, correct HD colour, and no animated grain. It also gives you an upload checklist. You revise in plain words ("the text is too subtle", "let the pieces stay
visible"); it treats each note as a design change and keeps a record of what you taught it.

## Every frame is `seek(t)`

Each film is one HTML page where every frame is a **pure function of time**, drawn into one canvas.
- **Inspectable:** any moment can be rendered and checked exactly.
- **Revisable:** retiming is a data edit, not a re-shoot.
- **Frame-exact:** headless Chrome renders frame *i* as `seek(i / fps)` across parallel workers, so nothing drops or drifts, whatever the machine.

2D (Canvas plus WebGL shaders for light and sky) is the default. It is the fastest to perfect. three.js and raymarched 3D are there when you
choose them.

## Install

**As a Claude Code plugin**, inside Claude Code:
```
/plugin marketplace add klsoen/opus-js-animations
/plugin install opus-js-animations@opus-js-animations
```

**Or as a personal skill:**
```bash
git clone https://github.com/klsoen/opus-js-animations
cp -r opus-js-animations/skills/opus-js-animations ~/.claude/skills/
```

Then ask for a film, for example:
- *"Make a 20-second reel of this poem reading: https://youtu.be/…"*
- *"An explainer on compound interest with a calm male voiceover (I have an ElevenLabs key)"*
- *"A looping visualizer for this track, 16:9, generated music is fine"*

## Requirements

| Needed | For |
|---|---|
| **Claude Opus 5.5** in Claude Code | the directing and the animation code (the skill works with other models; it was built for this one) |
| **Node ≥ 22** | the render and inspection tools (built-in `fetch` and `WebSocket`: no `npm install`) |
| **Google Chrome** or Chromium | headless, frame-exact rendering (GPU on macOS via Metal); set `CHROME=/path` if it isn't found |
| **ffmpeg** | encoding, audio cuts, analysis |
| Python 3 (+ numpy) | audio analysis; `openai-whisper` for aligning a voice |
| yt-dlp | fetched automatically the first time you give a link |
| an ElevenLabs or OpenAI key | only for voiceovers; read from the environment or `~/.config/opus-js-animations/keys.env`, never written into your project |

## What's inside

```
skills/opus-js-animations/
  SKILL.md                    the workflow: five conversations, then build → inspect → render → deliver
  references/
    directing.md              question bank, the "what I hear" audio report, the treatment template
    styles.md                 a style menu (cut-paper stop-motion, paper lightbox, night realism, mosaic, …)
    design.md                 composition, camera, characters, text on screen, lessons from real revisions
    audio.md                  the four sound routes, alignment, Web Audio scores, mixing, TTS voiceovers
    shaders.md                skies, stars, galaxies, dunes, lakes, mist (WebGL, composited into 2D)
    tiles-and-flocks.md       thousands of elements: mosaics, particles, birds, letters (WebGL2 instancing)
    painting.md               painter emulation and sketch → painting reveals; stills in a named style
    threejs.md                real 3D when chosen: rigs, instancing, shadows, depth of field, exploded models
    production.md             minutes-long films with parallel agents
    quoted-text.md            verifying quotations, poems and lyrics byte for byte
    delivery.md               crisp on Instagram/TikTok/X: why some uploads look sharp, the export, an upload checklist
    examples.md, pitfalls.md  finished films and what their revisions taught; environment gotchas
  scripts/
    render.mjs                frame-exact MP4 with audio, parallel workers
    stills.mjs                frames, contact sheets, frame strips, 1:1 crops
    verify.mjs                proves seek(t) is pure
    get_audio.py              audio (and a frame sheet) from YouTube or any yt-dlp site
    analyze_audio.py          length, loudness, pauses, sections, onsets, tempo, spectrogram
    align_audio.py            words and breath points in time (Whisper)
    voiceover.py              ElevenLabs / OpenAI text-to-speech, line by line, with timings
    embed_audio.py, page_audio.mjs, paint.py
  assets/
    film-template.html        the starting page with the seek(t) contract
    watermark.js              a channel handle: faint inside the picture, then a front-and-centre end card
```

## Principles it follows

- **Direct before building.** A treatment costs a minute to change; a film costs an hour.
- **Scenes scale with length.** Under ~30 s is one continuous scene whose state changes on each phrase.
- **Show the meaning with the sound off.** The picture carries the argument; text confirms it.
- **Your audio stays untouched.** It is cut on zero crossings, with no normalising, EQ or fades unless you ask.
- **Look, don't assume.** Every claim about the film is checked on rendered frames.

## License

MIT © klsoen.
