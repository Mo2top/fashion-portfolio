# Bilingual fashion portfolio

The actual English (`Portfolio_10MB.pdf`) and Chinese (`作品集 1.pdf`) portfolios,
with all **13 pages per language** in their original order. The PDF composition,
images, fonts, colors, spacing and artwork are preserved.

The portfolio is presented in a page-by-page editorial viewer. Every resting
page displays its original lossless PDF raster. Click the artwork or its
surrounding stage to advance, or use the small navigation controls to go back,
advance or select a page. The complete 16:9 artwork scales to fit desktop,
tablet and mobile without cropping or rearranging its content.

## Navigation and language

- Click/tap the portfolio to advance. Clicking a control does not also advance.
- Use the previous/next arrows; desktop also shows 13 page indicators.
- Arrow keys navigate; Space advances; Home/End go to the first/final page.
- Horizontal touch swipes go forward/back. A swipe never also counts as a tap.
- The final page stays at page 13; the first page has no previous page.
- EN / 中文 remains fixed at the top-right. English is the initial default;
  `portfolio-language` in localStorage remembers a valid saved choice.
- Changing language preserves the current page. If an animation is in progress,
  it settles on the destination page before changing language. Rapid language
  reversals cancel stale requests. Storage restrictions do not break the site.

## Editorial transitions

The Web Animations API controls a **2,000 ms** cinematic transition. Large
headlines scatter in letter fragments; body text and script signatures use
small grouped fragments. Each fragment moves independently, fades and softly
blurs. Photography and decorative artwork fade separately. Incoming text
returns to its original positions; the complete original raster takes over
at the end, preserving the exact resting appearance.

The animation uses transform, opacity and a small CSS blur on cached transparent
text fragments. React does not run a render loop per frame. Repeated navigation
is locked during a transition; cold requests keep the current artwork visible
until the next scene has decoded. Only current/adjacent scenes warm in advance.
The measured two-second animation begins when its required assets are ready.

`prefers-reduced-motion: reduce` uses immediate page changes without scatter,
blur or motion layers. Changing this setting during a transition settles the
scene immediately. Missing motion assets retain the original page and allow
a retry instead of showing broken or duplicated typography.

## Accurate text separation

`scripts/build_motion_layers.py` works directly from the supplied PDFs. It
creates two copies of each page using native PDF text/graphics operators:

1. A text-free background keeps photographs, illustrations and decoration.
2. A transparent text-only render keeps the original glyph ink, including the
   Chinese Type 3 font shapes. No replacement web fonts, OCR, inpainting,
   translations or manually retyped layout are used.

Original glyph geometry determines fragment crops. Transparent fragments are
packed into one atlas per page/resolution, so individual animation fragments
share one downloaded texture. Every visible text pixel belongs to exactly one
fragment; the generator verifies that reassembling the fragments reproduces
the transparent text layer exactly. Recomposition against the original page
is measured and recorded in `src/motion.generated.json`.

Text already baked into photographs, magazine covers or screenshots remains
part of the image and fades with it. It is not artificially removed or retyped.

The text layer uses correctly unpremultiplied alpha to avoid dark fringes over
photographs. The transparent atlas and background are encoded losslessly.
The original full-page images remain unchanged in `public/portfolio/`.

## Run and build

Use Node.js 24 LTS (or 22.12+):

```sh
npm ci
npm run dev
```

Vite listens on port 5173. This address belongs to the machine running Vite;
a cloud environment's localhost is not your Mac's localhost.

```sh
npm run verify:assets
npm run verify:motion
npm run build
npm run preview
```

`npm run build` runs both validators before building `dist/`. Production preview
uses port 4173. No backend, API keys, environment variables, Python or PDF viewer
is required by the deployed website.

## Regenerate assets

Python is needed only to regenerate the images. The exact supplied PDFs are
kept locally in the ignored `source-pdfs/` directory.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-render.txt
.venv/bin/python scripts/render_portfolio.py --en source-pdfs/Portfolio_10MB.pdf --zh 'source-pdfs/作品集 1.pdf'
.venv/bin/python scripts/build_motion_layers.py
npm run build
```

The original-page exporter creates 78 responsive lossless WebP files (13 pages
× 2 languages × 3 widths: 960, 1920, 3840). The motion exporter creates another
156 files: a background and transparent atlas for each page/size/language.
The 735 independent text fragments share those atlases; they do not require
735 separate image requests. Browsers download selected resolutions as needed,
not every variant. Motion assets are not preloaded for reduced-motion or
save-data preferences.

Commit **both** generated manifests and **both** public image directories:

```text
src/portfolio.generated.json
src/motion.generated.json
public/portfolio/
public/portfolio-motion/
```

The manifests record source and asset hashes. The motion validator also checks
its source-manifest hash, page counts, crop/atlas bounds, separation checks and
every image file, preventing deployment of incomplete or stale layers.

## Vercel

The GitHub repository `Mo2top/fashion-portfolio` is connected to Vercel.
Pushing to its production branch triggers deployment. The existing live domain
is https://fashion-portfolio-flax.vercel.app/.

The included `vercel.json` selects Vite, `npm run build`, and `dist/`. Both
hashed image directories have immutable caching. All assets are generated
before committing; Vercel does not need the original PDFs or a Python runtime.

## Verification

The generator verifies lossless encoding, exact fragment pixel ownership,
text-free backgrounds, matching language/page dimensions and fidelity of the
recomposed layers against every supplied PDF page. The original full-page
images are the final source of truth for the resting view.

Browser QA covers the actual English and Chinese pages on desktop/mobile,
resting-page pixel comparisons, independent fragment movement, two-second
timing, navigation limits, keyboard/back controls, language changes during
motion, reduced motion, blocked storage and failed asset recovery. Performance
measurements are browser/emulation observations, not a guarantee of 60 FPS on
every physical device.

Completed Chromium checks measured normal transitions at approximately
2.01–2.17 seconds and average requestAnimationFrame rates of 59.0 FPS on desktop
and 59.9 FPS in mobile emulation. All 26 resting-page screenshots matched their
original 3840 × 2160 PDF rasters exactly. Forward/back touch swipes and landscape
proportions were checked as well.

To repeat the browser suite, start `npm run preview` in one terminal, then:

```sh
.venv/bin/python -m pip install -r requirements-test.txt
.venv/bin/python -m playwright install chromium
.venv/bin/python scripts/test_portfolio.py
```

The suite writes screenshots/results to ignored `work/browser-qa/`. Set
`PORTFOLIO_TEST_URL` to test a different deployment, or
`PORTFOLIO_CHROMIUM_PATH` to use an existing Chromium executable. An activated
Python environment can also run the suite using `npm run test:browser`.
