# Directing: the five conversations before a single frame

A film made in code costs little to change while it is still words and a lot once it is 1,500 lines of JavaScript.
So direct first: listen, get the sound, study it, ask, write the treatment, and build only on a "go".

## Contents
1. The brief and a reference clip
2. Asking about the sound
3. Understanding the sound: the audio report
4. The question bank
5. The director's treatment: template and example
6. Skipping, shortcuts and revisions

## 1. The brief and a reference clip

Listen to the whole brief before proposing anything. Reflect it back in two or three lines:
- subject, feeling and audience;
- platform and formats, and length;
- text on screen;
- anything to avoid.

Note what is still unknown; those become questions in §4.

When they bring a reference clip ("make something like this"), measure it; don't guess from memory (`design.md` §2):
```bash
f="clip.mp4"                                                   # quote paths: macOS names can contain spaces and U+202F
ffprobe -v error -show_entries format=duration:stream=width,height,r_frame_rate -of compact "$f"
ffmpeg -v error -i "$f" -vf "fps=1,scale=320:-1,tile=6x4" sheet.png                        # one frame a second, tiled
ffmpeg -v error -i "$f" -vf "select='gt(scene,0.08)',showinfo" -f null - 2>&1 | grep -o "pts_time:[0-9.]*"   # its cuts
```
Read the sheet, then name the reference precisely:
- the style (e.g. "silhouettes on gradient skies with a tiny-planet horizon");
- the likely stack;
- its one big idea;
- its rhythm (cuts per second, or one take).

Keep its identity and drop its defects.

## 2. Asking about the sound

Everything downstream is timed to the sound, so settle it first. One question, four options (plus "silent" for loops and GIFs):

| They choose | Follow-up | Then |
|---|---|---|
| **My own file** | The path. If it's a video, you'll take its audio. | `ffmpeg -i in.mp4 -vn -c:a pcm_s16le -ar 48000 source/source.wav`. Use it untouched (`audio.md` §7). |
| **A link** | Which section (from and to, in seconds), or all of it if it's short. | `get_audio.py "<url>" --from 12 --to 44 --out source --video`, then read `meta.txt` and the frame sheet. Say where the audio came from; reuse rights are theirs to judge. |
| **Generate it in JavaScript** | The mood and genre, a tempo if they care, instruments or "you choose", and whether sound effects should follow the action. | The score is written into the page from the film's own timeline (`audio.md` §5), so music and picture can't drift. Draft its tempo and structure in the treatment; render the mix with `page_audio.mjs`. |
| **A voiceover from my TTS key** | The provider (ElevenLabs or OpenAI) and the key; the script (theirs, or one you draft); the language, a voice and the pace. | Approve the script in writing before voicing it, because each call costs them money. `voiceover.py` (`audio.md` §8). |

**Keys.** Ask them to put the key where the script reads it:
- `export ELEVENLABS_API_KEY=…` in their shell profile, or
- a line in `~/.config/opus-js-animations/keys.env` (chmod 600).

If they paste a key into the chat, write it to that file yourself with `chmod 600`. Never put it in the project, a command line, a log or a reply.

## 3. Understanding the sound: the audio report

```bash
python3 <skill>/scripts/analyze_audio.py source/source.wav         # report + source.analysis.json + source.spectrum.png
python3 <skill>/scripts/align_audio.py source/source.wav --lang en   # words and breath points (voice only)
```
Read the spectrogram image, not only the numbers:
- phrases are islands of energy and pauses are gaps;
- a beat shows as vertical stripes;
- a swell is a widening band;
- a quiet last word is a faint smudge at the end.

Whisper can miss a quiet ending; check it (`audio.md` §3) before saying the audio stops early. For lyrics, poems and quotations, fetch the canonical text now (`quoted-text.md`).

Then give the person a short report in this shape:

> **What I hear** (20.4 s; one voice reading in English; no music)
> - **Structure:** two halves of four clauses each; the turn comes at 8.6 s ("And whoever lives for more").
> - **Key words:** "together" at 2.4 s, "heart" at 5.4 s, "anyway" at 7.9 s, "want" at 11.5 s, "apart" at 13.6 s, "share" at 17.6 s (spoken softly).
> - **Tempo and mood:** unhurried and warm, with breaths of 0.3–0.6 s between clauses.
> - **Flaws:** a soft tonal bed under the voice; the last words are quiet but present.

For music, report the tempo and bar length, the sections (intro, verse, drop, outro) with times, the hits worth landing a cut or event on, and the loudest moment.
For a voiceover you generated, report the measured length of each line against the plan.

## 4. The question bank

Ask what the brief and the sound leave open: at most four questions per round, and ideally one round. Put your recommendation first, and say why in its description.

**Look.** Offer two or three styles from `styles.md` that fit the subject, each with a one-line description. Include "you choose".

**Pacing and structure.** Recommend by length:

| Length | Recommend | Why |
|---|---|---|
| under ~30 s | one continuous scene whose state changes on each phrase | a cut every phrase feels frantic and says less |
| ~30–60 s | one to three movements, ideally on one set | one per idea; cut at the turns of the argument |
| music with a beat | movement locked to the beat, cuts on downbeats | the picture should play the music |
| minutes | production with scenes (`production.md`) | |

Also ask whether it should feel calm or energetic.

**2D or 3D.**
- **2D** (Canvas 2D with WebGL shaders for light and sky) is the default: the quickest to perfect and the most controllable.
- A **raymarched 3D look** suits landscapes, water and sky.
- **three.js meshes** suit a built world, rigged figures or an exploded model.

Offer 3D when the idea needs depth, not by default.

**The points to land.** Ask directly: what must a viewer with the sound off understand, and on which words or hits? Offer your reading of the audio as the default.

**As needed:**
- **Formats:** 9:16 1080×1920 (Reels, TikTok, Shorts), 16:9 1920×1080 (X, YouTube), 1:1, or several from one source.
- **Text:** the original only, original plus translation, captions of the voice, or none; which translation.
- **Characters:** a faceless figure, silhouettes, no figures (symbols, nature, objects), or a mascot.
  For sensitive content, ask how people may be shown (`quoted-text.md`).
- **The hook** (for social feeds): a bright, moving, strange first frame is the default; a calm open is the alternative.
- **The ending:** resolve on the central image, a text card or line, or a loop back to frame 0.
- **A watermark:** their handle or logo. By default it stays faint inside the picture and becomes an end card (`design.md` §7).
- **Avoid:** anything they never want to see (music under a voice, faces, a brand's colours).

## 5. The director's treatment: template and example

Write it in `film/FILM.md` and present it in the chat. Keep it to one screen or two. It is a promise of what the film will do, beat by beat, so a person can say "yes" or "change scene 3" to it.

```markdown
# <Title>: treatment

**Logline.** One sentence: who or what, what changes, and what it means.
**The central image.** The one picture that carries the idea; the thumbnail.
**Look.** A style from the menu, 5–7 colours with their roles, texture, light. 2D or 3D, and why.
**Sound.** Its source and length, what drives the picture (words, beats), and any score or effects.
**Structure.** Scenes or movements with their times, and the turn.

| Time | Words / beat | What we see | What changes | Camera | Light and colour | Text |
|---|---|---|---|---|---|---|

**The hook.** Frame 0 and the first second.
**The ending.** The last image and how it goes out.
**Formats.** Canvas sizes and where the text sits in each.
**Risks.** What might not read, and how it will be checked.
```

An example, abridged:

> **Logline.** Two men stand back to back under one gold medallion split between them. The half of the one who lives for what lasts gathers
> and lights up; the half of the one who lives for more falls apart into a mess over his head.
> **The central image.** The split medallion over the two men: a gold half over a lit hall, a broken half over a neon market.
> **Look.** A paper lightbox at night in 2D: indigo sky; gold, amber and rose on his side; magenta and cyan neon on the other; a wet floor mirroring both.
> **Sound.** The client's 20.4 s reading, untouched. Every change lands on a clause.
>
> | Time | Words | What changes | Camera |
> |---|---|---|---|
> | 0–0.5 | (hook) | the medallion bursts into spiral arms around a white-gold sun | close on the core, pulling back |
> | 2.4–4.1 | "his days come together" | his half locks home piece by piece; lanterns light outward from him | wide, drifting to him |
> | 4.1–6.6 | "his heart is full" | a light kindles in his chest; his half lights from within | push in on him |
> | 6.6–8.6 | "the world comes to him" | coins roll from the market past the other man and lie down at his feet | ease back |
> | 10.9–13.5 | "want before his eyes" | an empty coin hangs before the other man's eyes, always a hand ahead | push in |
> | 13.5–15.4 | "his days come apart" | his half bursts into a mess that stays in his sky; bags and phone among it | pull back |
> | 17.2–20.4 | "only his share" | one piece comes down into his palm; pull back to both | wide, fade |
>
> **Risks.** A muted viewer must read "gathered versus scattered" from the medallion alone, so the loose half has to look loose at thumbnail size.

## 6. Skipping, shortcuts and revisions

- **Detailed briefs:** if the brief already answers a question, don't ask it; state the assumption in the treatment.
- **"Just make it":** skip the questions, not the treatment. Show it and wait, unless they say plainly that they don't want to see a plan.
- **Revisions of a delivered film:** don't rerun the five conversations. Take the note, restate the change in one line if it is ambiguous, update `FILM.md`, and rebuild.
- **Changes that break the contract** after approval (a new scene, a new style, a different length) go back to them as a revised treatment.
- **Record what they teach you** in `FILM.md` ("Revisions" with their words), so a later session revises in the same direction.
