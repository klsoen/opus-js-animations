# Production: long films with many agents

Use when the film is longer than ~90 s, has several scenes, characters or dialogue, or the
user asks for a big, ambitious piece ("4 minutes, story, dialogue, sounds, use up to N
agents"). The pipeline below delivered a 4-minute animated film with 7,200 frames, 557
sound cues, a score and dialogue using ~15 agents. Solo shorts don't need it.

## Contents
1. Shape of the pipeline
2. Bible and script (you, before any agent)
3. Kits: characters, worlds, props
4. Prove the cold open
5. Scene directors in parallel
6. Audio team
7. Render farm, mix, assembly
8. Review and the continuity pass
9. Agent briefs (templates)

## 1. Shape of the pipeline

```
bible + script + timing ──► kits (parallel) ──► cold open proof ──► scene directors (parallel)
         │                                                   │
         └──► audio: dialogue, composer, sound design ◄──────┘ (reads scene event data)
                                   ▼
             render farm ──► mix/master ──► assemble ──► review sheets ──► continuity fixes ──► final
```

Run agents with the Agent tool (independent tasks, in one message so they run in parallel)
or the Workflow tool when the user has opted into multi-agent orchestration. Keep the
orchestrator (you) responsible for the bible, integration, review and every decision about
quality; agents build parts.

## 2. Bible and script

Write `production/BIBLE.md` first. Every agent gets it.
- Logline, theme, ending, and why the ending belongs to this story.
- Characters: silhouette, proportions, palette, costume, mannerisms, voice.
- Worlds: locations, time of day, palette per scene, recurring props.
- Script with scene numbers, dialogue lines (speaker, text, emotion), and target timings.
- Scene table: id, start, end, what happens, camera, emotional beat, key sync events.
- Style rules: canvas size, fps, line/outline rules, grain, fonts, forbidden things.
- Technical contract (below).

Technical contract every module follows:
- A scene module exports `seek(tLocal)` drawing into a shared context, pure in time; no
  `Math.random()` in draw paths; seeded RNG by stable keys.
- The film shell maps global time to scene and local time, and exposes
  `window.__film = { duration, ready, seek, shots, marks }`.
- Events that sound must hear (impacts, doors, lines) are exported as data
  (`scene.events = [{t, type, x}]`).

## 3. Kits

Build reusable kits first, one agent each, in parallel: a **character rig** per main
character (joint skeleton, poses, expressions/moods, mouth shapes for dialogue, lighting
hooks), a **world kit** per location (backgrounds, time-of-day palettes, weather), and a
**props kit**. Each kit agent must deliver:
- the module file(s),
- a test page with a contact sheet of every pose, mood and lighting condition,
- `API.md`: functions, parameters, coordinate conventions, performance per frame, known gaps.

Review every kit's sheet yourself at full size before any scene uses it. Merge all `API.md`
files into one `production/KITS.md` for the scene agents.

## 4. Prove the cold open

Build the first scene to final quality end to end, including rendered sound, mix and a
muxed test MP4, before launching scene directors. It proves the kits, the contract, the
render farm and the audio path, and becomes the quality reference every scene director
must match. Check a frame decoded from the encoded MP4, not just the canvas.

## 5. Scene directors in parallel

One agent per scene, launched together. Each gets: the bible, KITS.md, a continuity sheet
(what the previous scene ends on and the next scene begins with: positions, lighting,
props, emotional state), the dialogue timings (measured TTS durations), the sound
designer's sync offsets, and the cold-open as the quality bar. Each must return a contact
sheet, per-frame render cost, its events list, and open issues.

Parallel agents can't see each other's work, so expect **continuity drift** (the same prop
drawn differently, a hand-off that doesn't match). Plan for it: anything shown in more than
one scene lives in a **shared module** that scenes import (e.g. the photo a character takes
in scene 7 and shows in scenes 8 and 9 is one `drawPhoto()`), never re-drawn from a
description.

## 6. Audio team

Launch in parallel with the scene directors once the script is timed:
- **Dialogue**: render every line, measure durations, deliver files and a timing table.
- **Composer**: score from the dramatic arc and dialogue map; leave space under lines.
- **Sound designer**: renders cues from the scenes' event lists; foley, ambience, UI sounds.
Then mix (see `audio.md §6`). A music bus that sits ~18 dB under dialogue is too quiet;
~10 dB under in talky scenes with swells in action is a normal film balance.

## 7. Render farm, mix, assembly

```bash
node scripts/render.mjs production/film.html --workers 10 --fps 30 --audio production/master.wav --out film.mp4
```
Workers split the frame range across parallel headless Chrome instances with GPU; 7,200
frames at 27–97 ms each took ~3.5 minutes on 10 workers. Render sections silently while
iterating (`--from 60 --to 90`). For per-scene pages, render each scene to a segment and
concatenate with an absolute-path concat list (relative paths in concat lists resolve
against the list file, a common failure).

## 8. Review and the continuity pass

- Contact sheet of the whole film at one frame every 2 s (`stills.mjs --every 2 --sheet`);
  read every sheet. Look for flashes (a full white or black frame at a cut), dead frames,
  mismatched props, characters jumping position across cuts.
- Frame-by-frame strips at every scene boundary (`--range a:b:0.0333`).
- Full-resolution stills of emotional close-ups and every hand/prop contact.
- Fix continuity with shared modules and re-render only affected scenes; keep the previous
  cut for comparison.
- Record in `production/REVIEW.md` what was checked, what was fixed, what remains.

## 9. Agent briefs (templates)

Kit agent:
```
You are building the <name> kit for a 2D animated film. Read production/BIBLE.md.
Deliver: production/kits/<name>.js (ES module), a test page kits/<name>.test.html that
draws a contact sheet of every pose/mood/lighting, and kits/<name>.API.md (functions,
params, coordinates, ms/frame, known gaps). Everything must be a pure function of its
inputs (no Math.random in draw paths; use the seeded rng). Match the style rules exactly.
Render the sheet with node <skill>/scripts/stills.mjs and inspect it before finishing.
```
Scene director:
```
You direct scene <id> (<start>–<end> s): <what happens>. Read BIBLE.md, KITS.md and
CONTINUITY.md (your first frame must match the previous scene's last frame: <details>).
Dialogue timings: <table>. Build production/scenes/<id>.js exporting seek(tLocal) and
events. Match the cold open's quality (scenes/s01). Deliver a contact sheet every 0.5 s,
strips at your first and last second, ms/frame, your events list and open issues.
Don't modify kits; report kit bugs instead.
```
