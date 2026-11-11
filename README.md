# Bilingual PDF portfolio

The actual supplied portfolios are imported into this React + Vite website:

- English: `Portfolio_10MB.pdf` — 13 pages.
- Chinese: `作品集 1.pdf` — 13 pages.

All pages retain their original 1440 × 810 (16:9) proportions and page order.
The only added visible element is the fixed **EN / 中文** switcher. Each PDF
page is rendered as a complete image, preserving its text, embedded fonts,
photos, colors, spacing, backgrounds and decorative elements.

## Run locally

Use Node.js 24 LTS (or 22.12+):

```sh
npm ci
npm run dev
```

The development server listens on port 5173.

```sh
npm run verify:assets
npm run build
npm run preview
```

The production build is generated in `dist/`; the default production preview
port is 4173. No server, API keys or environment variables are needed in
production.

## Rendering and performance

`public/portfolio/` contains 78 lossless WebP images: 13 pages × 2 languages ×
3 responsive widths (960, 1920 and 3840 pixels). All variants together occupy
66.87 MiB. Browsers select an appropriate size through `srcSet`, rather than
downloading all three variants. The 960-pixel variants total 5.29 MiB across
both entire portfolios. Later pages load lazily; both language versions warm
near the viewport so switching is usually immediate.

The converter verifies every lossless image against its original rendered
pixels before saving. `src/portfolio.generated.json` records the exact input
PDF hashes, source dimensions, page order, image variants and image hashes.
The build validates all generated assets and requires exactly 13 pages per
language. Corresponding pages share identical dimensions.

Page wrappers always preserve the source PDF proportions, including before
images load. Desktop, tablet and mobile scale the complete PDF composition;
text and images are never rearranged, stretched or cropped.

## Language switching

English is the default. A previously saved choice takes precedence; the
switcher stores `en` or `zh` under `portfolio-language` in localStorage.
Switching changes the visible artwork inside persistent page wrappers, with
no navigation or page reload. Both the scroll offset and corresponding page
remain unchanged. On a cold connection, the current artwork stays visible
until the requested visible images have decoded. Storage restrictions do not
prevent switching.

## Re-render from the source PDFs

The supplied PDFs are retained locally in the ignored `source-pdfs/` folder;
the deployed website uses only the generated images. Python is required only
when regenerating assets, not for building or deploying the website.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-render.txt
.venv/bin/python scripts/render_portfolio.py --en source-pdfs/Portfolio_10MB.pdf --zh 'source-pdfs/作品集 1.pdf'
```

With the Python dependencies already available:

```sh
npm run import:pdf -- --en source-pdfs/Portfolio_10MB.pdf --zh 'source-pdfs/作品集 1.pdf'
```

Multiple PDF parts can be supplied after `--en` or `--zh`, in original page
order. Each language must total exactly 13 pages. The converter stops if the
corresponding page proportions differ. It uses a uniform scale and never
rebuilds, translates, crops or rewrites the content.

Commit `public/portfolio/` and `src/portfolio.generated.json` with the source
code. Image filenames contain content hashes for safe long-lived caching.

## Deploy to Vercel

Import this project into Vercel. The included `vercel.json` selects Vite,
`npm run build`, and `dist/`, and enables immutable caching for hashed page
images. All required portfolio assets are already generated; no PDF conversion
or Python runtime is required on Vercel.

## Verification completed

Checks were run against the actual supplied PDFs, not sample content:

- All 13 English and 13 Chinese pages were compared with their matching
  original PDF raster at 3840 × 2160 pixels. Every imported raster matched.
- Chromium screenshots of all 26 displayed pages at a 1920 CSS-pixel viewport
  and 2× density matched those rasters exactly (maximum pixel difference: 0).
  The permitted language overlay was hidden only during artwork comparisons.
- Every page was also visually reviewed beside an independent PDFium rendering
  of the original PDF, covering layout, text, images, colors and decorations.
- Browser checks passed at widths of 1440, 768, 390 and 320 CSS pixels, including
  all 26 page/language combinations at each width. No gaps, horizontal overflow
  or scroll movement occurred when changing languages, including the final page.
- Saved language, rapid switching and blocked localStorage were checked.
- Asset validation and the Vite production build passed.
