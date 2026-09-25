# Design: from an idea to a beat table

Read before building anything. Covers intake, studying a reference, mapping meaning to
pictures, restraint, camera language, characters and text.

## Contents
1. Intake
2. Studying a reference video
3. Mapping meaning to pictures
4. Restraint and polish (what "simple, elegant, awe-inspiring" means in practice)
5. Camera language
6. Characters and figures
7. Text on screen
8. Lessons from real revisions

## 1. Intake

The intake is a conversation (`directing.md`): the brief, the sound, what the sound holds, the direction questions, then a
treatment the person approves. Extract: subject, feeling, platform/format, length, audio source, text on screen, audience,
exclusions. Defaults when unstated:

| Platform | Canvas | Notes |
|---|---|---|
| Reels / TikTok / Shorts | 1080×1920 | UI covers the top ~250 px, bottom ~400 px, right ~140 px. Keep text and faces in the band y≈300–1450, x≈90–940. |
| Feed post / square | 1080×1080 | |
| YouTube / landscape | 1920×1080 | |

30 fps. Length follows the audio when there is audio (a reading, song, voice-over),
otherwise the story, and the length sets how many scenes the film can hold (§3).

Always present the director's treatment and wait for a go before building (`directing.md` §5). An open aesthetic brief is
permission to art-direct inside the treatment, not to skip it. When the content is sensitive (a real person, grief, a community's own texts),
put the depiction choices in the treatment explicitly.

## 2. Studying a reference video

When the idea comes from a clip ("how was this made, what's the style"), measure the file,
don't guess from memory:

```bash
f="$(ls -t ~/Desktop/*.mov | head -1)"        # quote: macOS names contain spaces and U+202F
ffprobe -v error -show_entries format=duration:stream=width,height,r_frame_rate -of compact "$f"
ffmpeg -v error -i "$f" -vf "fps=1,scale=640:-1" frame_%02d.png   # one frame per second
ffmpeg -v error -i "$f" -vf "select='gt(scene,0.08)',showinfo" -f null - 2>&1 | grep -o "pts_time:[0-9.]*"  # cuts
```

Tile frames into one image (`xstack`/`hstack`) and read them. Name the style precisely
(e.g. "silhouette art on gradient skies with a tiny-planet composition", "risograph
halftone", "flat vector motion graphics"), the likely stack (Canvas 2D vs WebGL vs Remotion
vs After Effects, judged from particle counts, grain, glow blending), and what makes it work
(one fixed subject, the world changing around it, text as lyric). Keep the reference's
identity (structure, rhythm, its one big idea); drop its defects.

## 3. Mapping meaning to pictures

**First let the length set the number of scenes.** Under ~30 s (a saying, a single stanza, a short
reminder), make one scene: one set, one continuous take, whose state changes on each phrase (the
light, a gesture, things arriving, gathering or scattering). About 30–60 s: one to three movements,
ideally on one set, with cuts kept for the turns in the meaning. Minutes: several scenes
(`production.md`). A new picture for every phrase reads as a slideshow and never lets the idea settle.

Then write a table with one row per phrase, line or beat, **timed to the audio**. The rows are beats
inside the scene:

| Time | Words / beat | What it means | What changes in the picture | Camera |
|---|---|---|---|---|

Principles that made the difference:
- **Make the meaning visible.** When the words praise or warn about a way of living ("whoever lives for what lasts"), let the
  viewer see it in what people do and in the world around them, not only in a symbol or a colour. A man merely facing a building read as
  "barren, nothing happening" to a viewer, and a monochrome, sparse "elegant" world read as bland: give the world colour and life. Contrast two
  ways of living by content (what each one does, holds and faces) as well as by light. How to show sensitive subjects: `quoted-text.md` (Depiction).
- **Keep the set's edges out of frame.** A "reveal it's a small model" pull-out read as exposing a limited world. Keep the camera
  inside what is built (or ring the set with far scenery in haze) and end on a composed frame inside the world.
- **Concrete beats vague, and generic can be iconic.** "The alternation of night and day" became the terminator
  sweeping across a planet as the sun circles it. "Standing, sitting, lying" became a figure
  changing posture exactly on each word. But one well-chosen image (a gesture, a light kindling,
  things gathering for one man and scattering for another) can carry a whole saying. In a short
  clip, prefer one generalized, iconic setting over a hyper-specific place crowded with props.
- **One idea per beat.** If a beat needs two images, it is two beats, or one image goes.
- **Tie the ending to this subject.** Swap in an unrelated subject: if the progression still
  works, it's generic. Tie it closer.
- **Motion is a consequence**, not decoration: things arrive, act, and leave a result.
- **Repeat structure in the audio → rhyme in the picture.** A repeated line can return to a
  place you've been, changed. Two halves of one saying can be the same scene played two ways.

Write this into `FILM.md` beside the film (premise, table, palette, camera plan, text,
decisions and why, what's still weak). It survives context loss and lets later sessions
revise without guessing.

## 4. Restraint and polish

The strongest correction in practice was: **"too dense — simple, elegant, wonderful,
awe-inspiring, well aligned, like a motion graphics expert."** What that means concretely:

- Few elements per frame; negative space is part of the design. Remove before adding.
  Particles, fireflies, grass, houses, extra stars, lens flares, clouds: each must earn its
  place. Default to none. Few is not empty: the richness (colour, light, life) goes into the
  things you keep, since a sparse monochrome world read as bland.
- Composition on a grid: subject on a third or the centre line; text in one fixed block that
  never jumps between phrases; horizon at a deliberate height.
- Motion carried by the **camera**, slowly and continuously (push in, pull out, tilt), with
  eased keyframes. A shot that moves by one smooth camera move reads as expensive.
- Continuity of space: zoom *through* things (planet → atmosphere → hill; sky → galaxy →
  cosmic web) instead of cutting.
- Colour: one palette per section, gradients rather than flat fills, glow with additive
  blending, soft vignette, very light grain (alpha ≤ 10/255). No pure black ink; darks are
  deep colour.
- Scale for awe: tiny human against a vast sky; one continuous zoom out from a person to
  galaxies (powers of ten) is more powerful than a montage of space pictures.
- Transitions: crossfade only with a reason; prefer camera moves, light blooms, and dips
  through atmosphere.
- **Open on a hook, end on black** (for feeds: Reels, TikTok, Shorts, X). Frame 0 is a composed, bright, *moving* image: it is the
  thumbnail and the reason a scrolling viewer stops (motion from the first frame, light against dark, a strange or wondrous image, e.g. a
  world hanging in pieces around a glowing light). The voice or music arrives within ~0.5 s. No fade up from black and no inherited title
  cards; the ending may fade to black.

## 5. Camera language

Implement the camera as a transform or shader uniform driven by eased keyframes
(`keyed(t, [[t0, v0], [t1, v1]], true)`; `true` = multiplicative, use it for zoom so the
speed feels constant across scales).

- Push in: `scale 1 → 1.06–1.12` over a shot, anchored on the subject.
- Pull out / zoom out: geometric interpolation; keep one point fixed on screen
  (`center = anchor - offset * radius`) so the zoom has a target.
- Tilt up to the sky: slide the land down (parallax: far layers move less) while sky layers
  move slightly.
- Dive: exponential radius growth with ease-in, crossfading into the destination.
- Never resize a rendered bitmap to fake a zoom; redraw at the new scale.
- **Anchor solving (3D camera).** Instead of keying yaw and pitch, key *what must be where*: "the
  man's feet at (410, 1300)", "the pole at (540, 1000)". Solve yaw and pitch for the current
  focal length every frame, then blend between anchors with a weight curve. Zooms then stay pinned
  on the subject automatically:
  ```js
  function aim(D, sx, sy, f) {          // world direction D appears at screen (sx, sy)
    const v = norm([(sx - W / 2) / f, (H / 2 - sy) / f, 1]);
    const r = Math.hypot(v[1], v[2]), beta = Math.atan2(v[1], v[2]);
    const pitch = Math.asin(clamp(D[1] / r, -1, 1)) - beta;
    const zp = -v[1] * Math.sin(pitch) + v[2] * Math.cos(pitch);
    return { yaw: Math.atan2(D[0], D[2]) - Math.atan2(v[0], zp), pitch };
  }
  ```
- **Monotone cubic splines** (Fritsch–Carlson) for every keyed value: smooth through many keys,
  no overshoot, easing at the ends. Eased piecewise segments stop at every key, which is wrong for
  a time-lapse that must accelerate and settle continuously. Interpolate zoom in log space.

## 6. Characters and figures

- Build figures from **parts on a joint skeleton**, each part outlined then filled (dark
  stroke `w+3`, then colour `w`), so overlaps read: back arm → back leg → front leg →
  garment → torso → head → front arm. A single hull or silhouette blob reads as a cone
  or ghost.
- Poses are joint arrays; interpolate between them with ease-in-out for transitions.
- Light the figure: gradient across the body along the light direction plus a **rim light**
  (draw into an offscreen layer; fill the silhouette with the rim colour; subtract the
  silhouette shifted away from the light; composite `source-atop`). Recipe in
  `shaders.md → 2D rim light`.
- Cultural identity comes from specific, respectful details (clothing, hair, objects the person would
  really own) rather than stereotype. Faceless figures (no eyes or mouth) are a common and respectful
  choice; ask when unsure.
- Check a 1:1 crop of every pose at full resolution; contact sheets hide construction errors.

## 7. Text on screen

- Two fonts at most. A second script gets a face with full support for its marks (check that small marks render).
- For English, a plain form with a **strong read** works best:
  - Jost **Medium (500)** in sentence case, letter-spacing ≈2.5% of the size (`ctx.letterSpacing`; set it on the measuring context too).
  - Full-opacity ivory (`#f7f1e5`).
  - A soft dark halo plus a tight 1.5 px shadow, so it stays crisp over busy ground.
  - One short pale-gold hairline as the divider.
  - History: an EB Garamond italic with an ornamented divider was replaced as "too much". The Jost Light (300), 32 px, 7% tracking that
    followed was then called "so subtle and overshadowed" next to an 80 px gold title line, with "make english text bigger … maybe bold too".
- Sizes at 1080 wide: a display line ~64–80 px, body text ~44 px Medium, line heights ~1.4×; keep lines ≤ 800 px so they clear
  the Reels buttons (two balanced lines are fine). On 16:9 at 1920 wide: display ~66–72 px, body ~42 px, lines up to ~1300 px.
- **Balanced line breaks**: find the narrowest width that keeps the same line count, so
  lines are even (see the template's `balanced()`).
- One fixed text block position for the whole film, with a small divider between original and translation.
- Reveal: fade + 16 px rise + blur 7→0 over ~1 s; original first, translation 0.3–0.4 s
  later; fade out 0.5 s before the next line. Per-letter animation breaks joined scripts
  (Arabic, Devanagari); reveal them whole or with a gradient mask in the writing direction.
- Pre-render each text block once to an offscreen canvas after fonts load
  (`document.fonts.load`); draw that canvas each frame.
- Keep references, performer names and hashtags out of the video when the person plans to put
  them in the post description; draft that description for them.
- **A channel watermark**, when the person has a handle to show (`assets/watermark.js`, `makeWatermark`):
  - **While it plays, keep it subtle.** Plain text at ~20% opacity, with no box, border, icon or corner-hopping, in one calm spot. Draw it
    *before* the vignette and grain so it looks part of the picture. A frosted pill with a gold border was rejected as "too visible … no
    border, no special encasing".
  - **At the end, make it front and centre.** The mark glides to the centre, grows and turns to gold while the film's own motif assembles
    above it (the `ornament` callback). A hairline then draws and a light sweep crosses the letters.
  - **Motif examples:** the medallion's pieces lifting off the fading picture and locking into a small medallion; the sky's stars
    converging into a shape.
  - **Timing:** add ~2.2 s after the picture's fade, pad the audio with silence, and re-apply the film's grain over the card.
  - **Placement:**
    - away from the subtitle block, and off the subjects on every camera push-in (bottom corners often hit figures);
    - in 9:16, out of the platform UI (x ≤ 920, y ≈ 180–1450);
    - after frame 0.

## 8. Lessons from real revisions

- A liked first pass was still "not enough": the second request was for *more detail and
  grandeur*; the third for *less density and more elegance*. Aim for the third from the
  start: rich rendering of few elements.
- A silhouette alone wasn't enough for a human subject; a characterful but faceless figure
  was.
- Stars that swell when zooming look cheap; keep star size fixed in pixels while positions
  scale (`r² *= zoom²` in the star function).
- Anisotropic noise in a band reads as scratches; keep decorative noise isotropic.
- Additive glows (bloom, nebula cores) blow out to grey or white; tone-map emission
  (`col += E / (1 + E * 0.35)`) and keep flat bloom terms at zero.
- Objects moving along an arc can drift into the text block; give them explicit paths.
- **One place, one continuous take** can beat a montage: a fixed subject (a man on a dune) while
  time, light and sky change around it, and a single camera turning from earth to sky and back.
  Tie a visual event to the key word (trails closing into circles exactly on the key word).
- A faceless head in profile needs skin at the front of the face; a beard drawn over the whole
  lower face reads as a helmet visor. Check heads at 1:1.
- Dense line textures behind text (star trails, rain) need a soft dark pool behind the text block,
  not just a gradient at the top.
- Put the horizon where the key event happens: an ending sunrise needs the horizon inside the
  frame, which may mean changing the camera height, not only the framing.
- **Generalize the idea; don't illustrate every line.** Over a talk, symbol worlds (coins, disembodied hands) were rejected for
  "an animated man and we are following along his story through the subtitles". The next treatment then gave every caption line
  its own scene and was rejected as "the scenes change too fastly rather than generalize the idea". What worked for that 46 s
  talk: one set, two or three long movements, one per idea, where time, light and counters change inside the shot and cuts are
  kept for the turns in the argument. On a 20 s saying, after three versions that moved through a detailed
  3D city with a new camera setup on almost every phrase, the client asked for "generic singular scenes": one scene for a short clip (§3).
- **Scattered things should stay in the frame.** On the line about a life coming apart, pieces blown off-screen read as gone, not as disorder.
  The client asked for them "dispersed and visible … a mess in the sky on his side". Disorder that hangs in view beside something whole
  shows the contrast better than an empty space (`styles.md` §3).
- **2D is the default.** In the same note the client said "no longer shall we do 3d". Build in Canvas 2D, with WebGL shaders
  composited in for skies, light and glow; use three.js meshes or raymarched worlds only when 3D is asked for.
- **A rewind turns one set into two lives.** When every frame is `seek(t)`, "what if he had given instead" costs nothing:
  evaluate the first life at a story time that runs backwards, with extra flicker, then play the second life on the same set.
