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
