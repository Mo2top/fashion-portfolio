#!/usr/bin/env python3
"""Rasterize the supplied PDFs without rebuilding or translating their contents."""

import argparse
from contextlib import ExitStack
import hashlib
import json
import math
from pathlib import Path
import shutil
import sys
import tempfile

import fitz
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
PAGE_COUNT = 13


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def convert(args):
    widths = sorted(set(args.widths))
    if len(widths) < 1 or widths[0] < 100 or widths[-1] > 8192:
        raise ValueError('Image widths must be between 100 and 8192 pixels.')

    # Validate every source before writing any generated assets. Multiple
    # split PDFs are concatenated in the exact order of the command arguments.
    with ExitStack() as stack:
        pages = {'en': [], 'zh': []}
        sources = {'en': [], 'zh': []}
        for language in pages:
            for filename in getattr(args, language):
                path = Path(filename).resolve(strict=True)
                document = stack.enter_context(fitz.open(path))
                if not document.is_pdf or document.needs_pass:
                    raise ValueError(f'{path.name}: an unlocked PDF is required.')
                sources[language].append({
                    'filename': path.name,
                    'sha256': sha256(path),
                    'pageCount': len(document),
                })
                pages[language].extend(document)
            if len(pages[language]) != PAGE_COUNT:
                raise ValueError(
                    f'{language}: expected exactly {PAGE_COUNT} pages; '
                    f'received {len(pages[language])}.'
                )

        for index, (english, chinese) in enumerate(zip(pages['en'], pages['zh']), 1):
            if not math.isclose(
                english.rect.width / english.rect.height,
                chinese.rect.width / chinese.rect.height,
                rel_tol=0.00001,
            ):
                raise ValueError(
                    f'Page {index}: the PDF aspect ratios differ between languages. '
                    'Conversion stopped to avoid cropping or distorting either design.'
                )

        work = ROOT / 'work'
        work.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='pdf-render-', dir=work) as temporary:
            staging = Path(temporary) / 'portfolio'
            staging.mkdir()
            manifest = {
                'schemaVersion': 1,
                'status': 'ready',
                'rendering': {
                    'engine': f'PyMuPDF {fitz.VersionBind}',
                    'format': 'lossless WebP',
                    'widths': widths,
                    'colorSpace': 'sRGB',
                    'annotations': True,
                },
                'sources': sources,
                'pages': [],
            }
            total_bytes = 0
            for index in range(PAGE_COUNT):
                original = pages['en'][index].rect
                entry = {
                    'number': index + 1,
                    'width': widths[-1],
                    'height': None,
                    'sourceDimensions': {},
                    'images': {'en': [], 'zh': []},
                }
                for language in pages:
                    page = pages[language][index]
                    rect = page.rect
                    entry['sourceDimensions'][language] = {
                        'width': rect.width, 'height': rect.height,
                    }
                    directory = staging / language
                    directory.mkdir(exist_ok=True)
                    for width in widths:
                        # Use one uniform scale on both axes. Render the full
                        # visible page, with embedded fonts and annotations.
                        # The epsilon avoids a floating point ceil adding a
                        # column; no resampling or cropping follows rendering.
                        scale = (width - 0.00001) / rect.width
                        matrix = fitz.Matrix(scale, scale)
                        pixmap = page.get_pixmap(
                            matrix=matrix, colorspace=fitz.csRGB,
                            alpha=False, annots=True,
                        )
                        image = Image.frombytes('RGB', (pixmap.width, pixmap.height), pixmap.samples)
                        if image.width != width:
                            raise ValueError(f'Unexpected raster size on {language} page {index + 1}.')
                        if language == 'en' and width == widths[-1]:
                            entry['height'] = image.height
                        if language == 'zh':
                            english_variant = entry['images']['en'][widths.index(width)]
                            if image.height != english_variant['height']:
                                raise ValueError(f'Raster proportions differ on page {index + 1}.')
                        temporary_image = directory / 'render.webp'
                        image.save(temporary_image, 'WEBP', lossless=True, method=6, exact=True)
                        # Confirm the web optimization preserves every raster pixel.
                        with Image.open(temporary_image) as decoded:
                            if decoded.convert('RGB').tobytes() != image.tobytes():
                                raise ValueError('Lossless image round-trip verification failed.')
                        digest = sha256(temporary_image)
                        name = f'page-{index + 1:02d}-{digest[:16]}-{width}.webp'
                        final_image = directory / name
                        temporary_image.rename(final_image)
                        size = final_image.stat().st_size
                        total_bytes += size
                        entry['images'][language].append({
                            'src': f'/portfolio/{language}/{name}',
                            'width': width,
                            'height': image.height,
                            'bytes': size,
                            'sha256': digest,
                        })
                    print(f'Rendered {language} page {index + 1}/{PAGE_COUNT}', flush=True)
                manifest['pages'].append(entry)

            destination = ROOT / 'public' / 'portfolio'
            destination.parent.mkdir(exist_ok=True)
            # Only replace this script's generated directory after all 26
            # original PDF pages have rendered and passed pixel verification.
            if destination.exists():
                shutil.move(str(destination), str(Path(temporary) / 'previous-assets'))
            shutil.move(str(staging), str(destination))
            manifest_path = ROOT / 'src' / 'portfolio.generated.json'
            manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
            print(f'Complete: 13 pages per language; {total_bytes / 1024 / 1024:.2f} MiB of responsive assets.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--en', nargs='+', required=True, metavar='PDF', help='English PDF(s), in page order')
    parser.add_argument('--zh', nargs='+', required=True, metavar='PDF', help='Chinese PDF(s), in page order')
    parser.add_argument('--widths', nargs='+', type=int, default=[960, 1920, 3840])
    try:
        convert(parser.parse_args())
    except (ValueError, OSError, RuntimeError) as error:
        print(f'Conversion failed: {error}', file=sys.stderr)
        sys.exit(1)
