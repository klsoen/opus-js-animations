# Delivery: crisp on Instagram, TikTok and X

Every platform re-encodes the upload, to a few Mbps for a 1080×1920 Reel. Two videos at the same resolution can look very different
afterwards. What decides it: how much of that small budget the picture needs, how cleanly the file arrives, and choices the platform makes.

## Contents
1. Why some videos look crisp and others don't
2. What the film should be (design for the re-encode)
3. The export (what `render.mjs` does, supersampling with `--ss 2`, and the upload copy)
4. The upload checklist for the person
5. Covers and thumbnails
6. How the grain and supersampling tests were run

## 1. Why some videos look crisp and others don't

| Factor | Effect | Who controls it |
|---|---|---|
| **Compressibility of the picture** | Noise, animated grain, fine twinkling particles and full-frame chaos eat the bitrate. Clean flat colour, sharp edges and steady motion survive. | the film |
| **The upload file** | A lossy or mis-tagged file loses twice. JPEG frame capture, full-range or BT.601 colour flags, and a 60 fps file splitting the same bits over twice the frames all cost quality. | the export |
| **The app's upload setting** | With "Upload at highest quality" off, the phone compresses the video *before* uploading, and Instagram then compresses it again. | the person |
| **Popularity** | Instagram re-encodes videos that get more views with costlier encoders (VP9, and AV1 for the most popular), and falls back to a cheaper encode when views stop. Mosseri confirmed it; he says the difference "isn't huge". | the audience |
| **The viewer's connection** | Adaptive streaming drops to a lower rung on slow networks or in data-saver mode. | nobody |

## 2. What the film should be (design for the re-encode)

- **No animated grain in the upload.** Grain that changes every frame is noise the encoder must spend bits on. It can't be kept at a few
  Mbps anyway; it becomes smeared blocks, and it takes the bits that text and edges needed.
  - **Measured on the opening burst of a 20 s reel:** at near-lossless quality the section needs 116 Mbps with animated grain, 51 Mbps with
    static grain and 31 Mbps with none.
  - **After a simulated Instagram re-encode**, the grain-free version kept SSIM .94 (H.264, 3 Mbps) and .95 (AV1, 1.5 Mbps) against its own
    upload; the animated-grain version kept .85–.86.
  - **What to do:** films expose `window.FILM_GRAIN = 'animated' | 'static' | 'none'` and the delivery shells set `'none'`. The paper
    textures inside the artwork stay; they move with the picture and compress well.
- **Bold, generous text.** Thin light type at 32 px smears. Medium weight at ~44 px (1080 wide) stays sharp (`design.md` §7).
- **Big shapes carry the frame; tiny sparkles are garnish.** Dozens of 2 px twinkling points turn to mush; fewer and larger ones read.
- **30 fps.** At the same bitrate 30 fps gives each frame twice the bits of 60.
- **Dark gradients:** the smooth night skies held without banding in the test once grain was removed. If banding appears, use a *static*
  dither at ≤ 4/255, not animated grain.

## 3. The export

`render.mjs` (default):
- captures every frame losslessly as PNG from the canvas (`--fast` uses JPEG q .95, for previews only);
- converts to standard HD video: `yuv420p`, BT.709 matrix, limited (TV) range;
- tags primaries, transfer, matrix and range as BT.709/TV, so phones and platform transcoders don't shift colours or lift or crush the
  blacks. The old path produced full-range, BT.601-flagged files.

**Supersampling (`--ss 2`)**: the film draws every frame at 2× (2160×3840, `?ss=2`) and `render.mjs` scales it back down with Lanczos in
16-bit RGB before the BT.709 conversion. Four samples per pixel give smoother edges, rounder type and less shimmer on moving detail.
- **Measured** on the opening burst of the same 20 s reel, against a 4× render boxed down to 1080×1920 (the nearest thing to the ideal picture):
  - the master moved from 39.1 to 45.0 dB PSNR (SSIM .985 → .996): a quarter of the error;
  - it stays ahead after a simulated Instagram re-encode: 32.7 → 33.5 dB (H.264, 3 Mbps) and 34.3 → 35.0 dB (AV1, 1.5 Mbps);
  - the upload needs slightly fewer bits (17.2 → 16.7 Mbps at CRF 17) and survives the re-encode as well as before (SSIM .94/.95
    against itself). Lanczos and a box filter scored the same; Lanczos looks crisper.
- **Cost:** about twice the render time for Canvas 2D. Heavy shaders cost up to four times (every fragment runs four times); give WebGL
  films 2 workers at 2×.
- **What a film needs** (`assets/film-template.html` has it):
  - read `ss` from the URL and make the canvas `W·SS × H·SS`, but keep all drawing in film pixels;
  - wrap the main context with `supersample(ctx, SS)`. It scales `setTransform`, `resetTransform`, shadow blur and offsets, and `filter`
    lengths. The last three are canvas pixels that the transform does not touch;
  - bake every sprite, text line and buffer at SS× its density, and multiply shadow and filter lengths inside a bake by SS yourself;
  - draw every baked canvas at an explicit film-pixel size. `drawImage(c, x, y)` uses its pixel size, which is now SS× too big;
  - multiply by SS the pixel numbers of pixel-space steps: offset copies for rims, source rectangles, reads of the main canvas. A bloom
    that read the main canvas at film size boxes it down to film size first;
  - shaders keep `uRes` and focal lengths in film pixels and map each fragment back,
    `vec2 fc = vec2(gl_FragCoord.x, uRes.y * uSS - gl_FragCoord.y) / uSS;`, so pixel-sized features (star radii, detail fades) keep
    their size and are simply sampled four times.
- **Check:**
  - at `ss=1` the frames stay byte-identical to the film before the change (hash a dozen times);
  - `verify.mjs --ss 2` passes;
  - a 2× frame scaled down matches the 1× frame at SSIM ≥ .95, with a difference map that lights only edges and fine texture.
- **Covers:** grab at `ss=2` and scale down the same way.

The upload copy for each format, 1080×1920 (or 1920×1080) at 30 fps:
```bash
ffmpeg -i film/film.mp4 -c:v libx264 -preset slow -crf 17 -maxrate 20M -bufsize 40M -profile:v high -pix_fmt yuv420p \
  -color_range tv -colorspace bt709 -color_primaries bt709 -color_trc bt709 -g 60 -c:a copy -movflags +faststart film/film-upload.mp4
```
Upload at exactly the platform's size (1080×1920 for Reels, TikTok and Shorts). Bigger gets downscaled by the platform's scaler; smaller
gets upscaled and looks soft. Check the result with
`ffprobe -show_entries stream=pix_fmt,color_range,color_space,color_primaries,color_transfer film-upload.mp4`.

## 4. The upload checklist for the person

1. In Instagram: **Profile → ☰ → Media quality** (on some builds, Data usage / Cellular data use): turn on **Upload at highest quality**.
2. **Get the file onto the phone without recompression:** AirDrop, a cable, or iCloud Photos with "Download and Keep Originals".
   Not WhatsApp, Telegram or other messengers.
3. **Upload on Wi-Fi.**
4. **Post the finished file as it is.** Don't trim, filter, add text or stickers, or re-crop in the app; each edit is another processing
   pass. Choose the cover frame instead.
5. **Pick a strong cover and give the first hour its best push.** Views earn the better encode (§1).
6. **Same file for TikTok.** TikTok also has an "upload HD" option in its post settings; turn it on.

## 5. Covers and thumbnails

- **Where they're seen:**
  - A Reel's cover shows mostly in the profile grid, which crops the **centre 3:4** of the 9:16 image (1080×1440 of 1080×1920).
    Keep every word inside y ≈ 240–1680.
  - The 16:9 thumbnail is for X and YouTube, wherever a custom thumbnail is allowed.
- **How to make them:** render a *clean* frame of the film's strongest moment in cover mode (`window.FILM_COVER = true`: no subtitles, no
  watermark), then set a title in the film's own type.
  - One idea, big: a two-word contrast ("NOW | LATER") or an imperative ("Look up tonight.").
  - A small reference line above it.
  - One line of hook below it, plus the handle.
- **Text and output:**
  - Take any quotation on a cover from the verified text (`quoted-text.md`). Match words by their base letters, because the order of
    combining marks can vary.
  - Capture the cover losslessly (PNG) and save a JPG at quality 95 for phones.
  - In Instagram: Edit cover → Add from camera roll.

## 6. How the grain and supersampling tests were run

1. Render the hardest 3.5 s (the opening burst) four ways: the old JPEG path with animated grain, then PNG capture with animated, static and
   no grain.
2. Encode each near-lossless, then simulate the platform: H.264 at 3 Mbps (`-b:v 3000k -maxrate 3500k`) and SVT-AV1 at 1.5 Mbps.
3. Measure SSIM and PSNR of each simulated copy against its own upload and against the clean picture.
4. Look at 1:1 crops of the text and pieces.

For supersampling:
1. Capture the same burst as PNG frames at 1× and 2×, plus six frames at 4× boxed down to film size as the reference.
2. Make the master and upload copy of each (2× scaled down with Lanczos and with a box filter), then the two simulated re-encodes.
3. Score every stage against the 4× reference, not against its own upload. Only the reference shows which version is closer to the ideal
   picture.

Repeat these tests for a new style whenever its look depends on fine texture.
