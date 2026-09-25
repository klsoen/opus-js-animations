# Quotations, poems and lyrics

For films built on a poem, lyrics, a speech, a literary passage or any quotation where exact wording matters.

## Identify, then verify

1. Identify the passage from the source's metadata and on-screen text (title, author, book and line, song and verse), then confirm it by
   transcription (`align_audio.py`).
2. Fetch the canonical text from an authoritative source (the publisher, an official lyrics source, a critical edition, a public-domain
   archive); never type it from memory.
3. Build phrase strings as **exact word slices of the fetched text** (split on spaces, join word ranges), not retyped. Combining marks can
   be ordered differently and still look the same, so compare byte for byte:
   ```js
   words.slice(0, 3).join(' ') === canonical   // the displayed phrases re-join to the source text
   ```
   Verify again after every edit to the phrase list. Parse the list with a robust boundary, because translations contain brackets like
   "[above such a thing];", which can break naive `];` matching.
4. If the recording differs from the canonical wording, follow the recording on screen and list the differences in `FILM.md`.
5. Keep a translation's own words and brackets, and name the translation in the post description.

## Display

- Use a font with full support for the script and its marks; check that small marks render, not as boxes.
- Don't break joined scripts (Arabic, Devanagari and others) into letters for animation: reveal whole words or lines, or use a gradient
  mask moving in the writing direction.
- If the speaker or singer repeats a phrase, show it again at the repeat.
- Credits, references and hashtags: ask; many people prefer them in the caption rather than in the video.

## Depiction and sound

- When the content is sensitive (a real person, grief, a community's own texts), ask how people may be shown: faceless figures,
  silhouettes, or no figures at all (symbols, nature, sky) are all options, and the person decides.
- Illustrate the meaning, not your gloss: "the alternation of night and day" is shown as day and night passing, not an unrelated symbol.
  For dark themes, prefer restraint (a distant glow, then relief) over graphic imagery.
- Ask whether music may play under a voice; some people want none.

## Post description

Offer a ready caption: the text or its translation, the reference, the speaker or performer, and a few relevant hashtags. Mention where
the recording came from so the person can judge reuse rights.
