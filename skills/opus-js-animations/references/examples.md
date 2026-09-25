# Worked examples

Finished films, what made each one work, and what review changed. Read the one closest to the
request before designing.

## 1. Glass and gold-leaf mosaic (square, 80 s, WebGL2, no assets)

Figures made of flocks of tiles; a fish swims by its tiles swimming. The full scene table,
technique and review notes are in `tiles-and-flocks.md` §8. Key lessons: figures need a
different material and an outline from the ground; formation beats flutter; flips reveal the
backing when tiles are edge-on; differential rotation makes a spiral read.

## 2. Kite planet (landscape loop, 24 s)

A child, a dog and a kite on a tiny planet, with six sky scenes cycling and procedural Web Audio music.
Built to demonstrate the style of a screen recording: one fixed subject with the world changing
around it, silhouettes on gradient skies, and the tiny-planet composition.

## 3. Sketch to living painting (landscape, 14 s, JavaScript; analysed from a screen recording)

A post titled "Claude Opus 5.5 drew every frame of this animation in JavaScript": blank paper →
a hatched drawing appears in soft blotches → colour blooms in → a golden-hour coastal oil painting
whose sea, glitter, grass and tree keep moving. Measured timings, the scene and the techniques are in
`painting.md` §7. What makes it work: one process shown from start to finish (the making is the
story), the drawing and painting coming from the same scene data, and motion restricted to the things
wind and water would move.

## 4. "The Script of Me": an ingredients reel for a journal page (portrait, 48 s, Canvas 2D)

A calm voice lists what went into one journal page, each ingredient with a short story; a new picture lands on every phrase, and the
real page is revealed last. The opening is in the repo's `docs/script-of-me-opening.gif`: a macro of the page's clock stepping to half
past midnight, a letterboxed pendulum whose swing quickens on "The heart is not", then the clock's parts arriving one by one in
stop-motion on mauve paper under a numbered title (*No. 1* · THE CLOCK · *Brass · Water · Patience*).
- **The voice sets every cut:** word times from the recorded voice; cuts land 0.05–0.15 s before each phrase.
- **Two clocks:** stop-motion objects step at 15 poses a second (`floor(15t)/15`) while pushes and drawn lines move every frame.
- **Shot vocabulary:** a macro of the real thing with a soft depth-of-field ellipse, a letterbox on black, a flat-lay whose parts land
  with a lifted first pose, then settle; one caption per phrase in an italic serif.

## 5. "Shaml": a paper-lightbox scene (portrait + 16:9, 20.4 s, Canvas 2D)

The style and its recipes are in `styles.md` §3. The opening is in the repo's `docs/shaml-opening-3s.gif`: a medallion of 336 cut-paper
pieces bursts into spiral arms around a white-gold sun while large blurred pieces fly past the lens; the camera pulls back as the
pieces unwind home and the first ones lock into place.

## Patterns across them

- One fixed subject, one place; the world (light, sky, time) changes around it.
- Everything is data on one timeline: text, camera, light, events, sound.
- Figures are rigs or flocks, built from parts or elements, never a single blob.
- Every review pass found something only a 1:1 crop or a frame strip could show.
- Showing the making (paper → drawing → paint, tiles leaving and returning) is itself a story.
- A chain of handoffs (one object passing the story to the next) with one colour travelling through it holds a very short film together.
- Two halves of one saying can share one place and one set of pieces: gathered for one, scattered for the other.
- Over a talk, one character living the words on one set beats a scene per sentence; a rewind gives the "other choice" for free.
- The shorter the clip, the fewer the scenes: a 46 s talk holds two or three movements on one set; a 20 s saying, one scene.
- A made thing (a page, a perfume, a dish) can be told as its ingredients, a short story each, and revealed last; the voice sets every cut.
