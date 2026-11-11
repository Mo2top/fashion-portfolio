#!/usr/bin/env python3
"""Separate the actual PDF typography and artwork for editorial transitions.

No fonts are substituted and no image inpainting is used. PDF text operators
(including Type 3 Chinese glyphs) are retained in a transparent text-only PDF
and removed from a second, artwork-only PDF. Text fragments partition the
transparent pixels exactly once and are packed into one atlas per page/size.
"""

from collections import defaultdict
from functools import lru_cache
import hashlib
import io
import json
import math
from pathlib import Path
import shutil
import tempfile
import re
import xml.etree.ElementTree as ET

import fitz
from PIL import Image, ImageChops, ImageDraw, ImageStat
from fontTools.pens.boundsPen import BoundsPen
from fontTools.svgLib.path import parse_path

ROOT = Path(__file__).resolve().parents[1]
BASE_WIDTH, BASE_HEIGHT = 960, 540
WIDTHS = [960, 1920, 3840]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def union(rects):
    return [min(r[0] for r in rects), min(r[1] for r in rects),
            max(r[2] for r in rects), max(r[3] for r in rects)]


@lru_cache(maxsize=4096)
def path_bounds(data):
    pen = BoundsPen(None)
    parse_path(data, pen)
    return pen.bounds


def multiply(a, b):
    return (a[0]*b[0]+a[2]*b[1], a[1]*b[0]+a[3]*b[1],
            a[0]*b[2]+a[2]*b[3], a[1]*b[2]+a[3]*b[3],
            a[0]*b[4]+a[2]*b[5]+a[4], a[1]*b[4]+a[3]*b[5]+a[5])


def native_glyph_bounds(page):
    """Ink bounds from original font outlines, including italic swashes.

    Text trace font metrics can understate CJK ascenders and aggregate unrelated
    text in PDF Forms. SVG outlines provide actual ink bounds without guessing.
    They are used for crop geometry only; all displayed pixels come from PDF.
    """
    root = ET.fromstring(page.get_svg_image(text_as_path=True))
    definitions = {e.get('id'): e for e in root.iter() if e.get('id')}
    result = []

    def transformed(matrix, bounds):
        x0, y0, x1, y1 = bounds
        corners = [(matrix[0]*x+matrix[2]*y+matrix[4],
                    matrix[1]*x+matrix[3]*y+matrix[5])
                   for x in (x0, x1) for y in (y0, y1)]
        return (min(p[0] for p in corners), min(p[1] for p in corners),
                max(p[0] for p in corners), max(p[1] for p in corners))

    def with_transform(element, matrix):
        for match in re.finditer(r'matrix\(([^)]+)\)', element.get('transform', '')):
            local = tuple(float(n) for n in re.split(r'[,\s]+', match[1]))
            matrix = multiply(matrix, local)
        return matrix

    def outline_bounds(element, matrix):
        if element.tag.endswith(('defs', 'clipPath')):
            return None
        matrix = with_transform(element, matrix)
        if element.tag.endswith('path'):
            bounds = path_bounds(element.get('d', ''))
            return transformed(matrix, bounds) if bounds else None
        if element.tag.endswith('use'):
            href = element.get('{http://www.w3.org/1999/xlink}href')
            return outline_bounds(definitions[href[1:]], matrix)
        bounds = [outline_bounds(child, matrix) for child in element]
        bounds = [box for box in bounds if box]
        return union(bounds) if bounds else None

    def walk(element, matrix=(1, 0, 0, 1, 0, 0)):
        if element.tag.endswith('defs'):
            return
        matrix = with_transform(element, matrix)
        if 'data-text' in element.attrib:
            href = element.get('{http://www.w3.org/1999/xlink}href')
            bounds = outline_bounds(definitions[href[1:]], matrix)
            result.append((element.get('data-text'), bounds))
        for child in element:
            walk(child, matrix)

    walk(root)
    return iter(result)


def fragment_boxes(page):
    """Use original glyph positions, keeping script signatures together."""
    log = page.get_bboxlog()
    glyphs = native_glyph_bounds(page)
    lines = defaultdict(list)
    groups = []
    for trace in page.get_texttrace():
        chars = trace['chars']
        if not chars or trace['opacity'] == 0:
            continue
        script = []
        for char in chars:
            text = chr(char[0])
            if trace['type'] == 3:
                bbox = log[trace['seqno'] - 1][1]
            else:
                glyph_text, bbox = next(glyphs)
                assert glyph_text == text, 'Glyph order differs from original PDF.'
            if text.isspace():
                continue
            if not bbox:
                continue
            item = {'bbox': bbox, 'text': text, 'origin': char[2],
                    'size': trace['size'], 'dir': trace['dir']}
            if 'script' in trace['font'].lower():
                script.append(item)
            elif trace['size'] >= 60:
                groups.append(item)
            else:
                dx, dy = trace['dir']
                baseline = -dy * char[2][0] + dx * char[2][1]
                key = (round(dx, 2), round(dy, 2), round(baseline),
                       round(trace['size'] / 2))
                lines[key].append(item)
        if script:
            groups.append({'bbox': union([c['bbox'] for c in script]),
                           'text': ''.join(c['text'] for c in script)})
    for items in lines.values():
        dx, dy = items[0]['dir']
        items.sort(key=lambda item: dx * item['origin'][0] + dy * item['origin'][1])
        chunk = []
        previous = None
        for item in items:
            distance = (math.dist(item['origin'], previous['origin'])
                        if previous else 0)
            if chunk and (len(chunk) >= 26 or
                          distance > max(22, item['size'] * 1.8) or
                          math.dist(item['origin'], chunk[0]['origin']) > 420):
                groups.append({'bbox': union([c['bbox'] for c in chunk]),
                               'text': ''.join(c['text'] for c in chunk)})
                chunk = []
            chunk.append(item)
            previous = item
        if chunk:
            groups.append({'bbox': union([c['bbox'] for c in chunk]),
                           'text': ''.join(c['text'] for c in chunk)})
    result = []
    for group in groups:
        x0, y0, x1, y1 = group['bbox']
        # All responsive crops share the 960-pixel coordinate grid. Padding
        # contains original ink, italic overhangs and antialiased edge pixels.
        x0 = max(0, math.floor((x0 - 2) * 2 / 3))
        y0 = max(0, math.floor((y0 - 2) * 2 / 3))
        x1 = min(BASE_WIDTH, math.ceil((x1 + 2) * 2 / 3))
        y1 = min(BASE_HEIGHT, math.ceil((y1 + 2) * 2 / 3))
        if x1 > x0 and y1 > y0:
            result.append({'rect': [x0, y0, x1 - x0, y1 - y0],
                           'text': group['text']})
    return result


def pack(fragments):
    positions = {}
    x = y = row_height = 0
    padding = 2
    for index in sorted(range(len(fragments)),
                        key=lambda i: -fragments[i]['rect'][3]):
        _, _, width, height = fragments[index]['rect']
        if x + width + 2 * padding > BASE_WIDTH:
            x = 0
            y += row_height
            row_height = 0
        positions[index] = [x + padding, y + padding]
        x += width + padding * 2
        row_height = max(row_height, height + padding * 2)
    return positions, [BASE_WIDTH, y + row_height]


def render(page, width, alpha):
    scale = (width - 0.00001) / page.rect.width
    pixmap = page.get_pixmap(matrix=fitz.Matrix(scale, scale),
                            colorspace=fitz.csRGB, alpha=alpha)
    # MuPDF's PNG encoder unpremultiplies alpha correctly. Reading raw pixmap
    # samples as straight RGBA would produce dark fringes over photographs.
    return Image.open(io.BytesIO(pixmap.tobytes('png'))).convert('RGBA' if alpha else 'RGB')


def write_image(image, directory, stem, width):
    buffer = io.BytesIO()
    image.save(buffer, 'WEBP', lossless=True, method=6, exact=True)
    data = buffer.getvalue()
    with Image.open(io.BytesIO(data)) as decoded:
        assert decoded.convert(image.mode).tobytes() == image.tobytes(), 'Lossless verification failed'
    sha = digest(data)
    filename = f'{stem}-{sha[:16]}-{width}.webp'
    (directory / filename).write_bytes(data)
    return {'src': f'/portfolio-motion/{directory.name}/{filename}',
            'width': image.width, 'height': image.height,
            'bytes': len(data), 'sha256': sha}


def main():
    source_bytes = (ROOT / 'src/portfolio.generated.json').read_bytes()
    originals = json.loads(source_bytes)
    assert len(originals['pages']) == 13
    result = {'schemaVersion': 1, 'sourceManifestSha256': digest(source_bytes),
              'coordinateWidth': BASE_WIDTH, 'coordinateHeight': BASE_HEIGHT,
              'widths': WIDTHS, 'languages': {'en': [], 'zh': []}}
    work = ROOT / 'work'
    work.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='motion-', dir=work) as temporary:
        staging = Path(temporary) / 'portfolio-motion'
        staging.mkdir()
        for language in ['en', 'zh']:
            inputs = originals['sources'][language]
            assert len(inputs) == 1, 'Import combined source PDFs before generating motion assets.'
            path = ROOT / 'source-pdfs' / inputs[0]['filename']
            assert digest(path.read_bytes()) == inputs[0]['sha256'], 'The PDF differs from the original import.'
            original_pdf = fitz.open(path)
            assert len(original_pdf) == 13
            directory = staging / language
            directory.mkdir()
            for number in range(13):
                source = original_pdf[number]
                fragments = fragment_boxes(source)
                positions, atlas_size = pack(fragments)
                for index, fragment in enumerate(fragments):
                    fragment['sprite'] = positions[index]
                entry = {'number': number + 1, 'copy': source.get_text(),
                         'fragments': fragments, 'atlasSize': atlas_size,
                         'variants': [], 'verification': []}
                # Isolated one-page documents preserve the original resources.
                background_pdf, text_pdf = fitz.open(), fitz.open()
                background_pdf.insert_pdf(original_pdf, from_page=number, to_page=number)
                text_pdf.insert_pdf(original_pdf, from_page=number, to_page=number)
                background, typography = background_pdf[0], text_pdf[0]
                background.add_redact_annot(background.rect, fill=False, cross_out=False)
                background.apply_redactions(images=0, graphics=0, text=0)
                assert not background.get_texttrace(), 'Background still contains PDF text.'
                typography.add_redact_annot(typography.rect, fill=False, cross_out=False)
                typography.apply_redactions(images=1, graphics=2, text=1)
                for width in WIDTHS:
                    multiplier = width // BASE_WIDTH
                    text_image = render(typography, width, True)
                    background_image = render(background, width, False)
                    original_image = render(source, width, False)
                    remaining = text_image.getchannel('A')
                    clear_remaining = ImageDraw.Draw(remaining)
                    atlas = Image.new('RGBA', tuple(n * multiplier for n in atlas_size))
                    rebuilt = Image.new('RGBA', text_image.size)
                    for fragment in fragments:
                        x, y, w, h = [n * multiplier for n in fragment['rect']]
                        box = (x, y, x + w, y + h)
                        crop = text_image.crop(box)
                        ownership = remaining.crop(box)
                        crop.putalpha(ownership)
                        # Overlapping typographic bounds never duplicate pixels.
                        # Every original text pixel belongs to exactly one fragment.
                        visible = ownership.point(lambda value: 255 if value else 0)
                        crop = Image.composite(crop, Image.new('RGBA', crop.size), visible)
                        clear_remaining.rectangle((x, y, x + w - 1, y + h - 1), fill=0)
                        sx, sy = [n * multiplier for n in fragment['sprite']]
                        atlas.paste(crop, (sx, sy))
                        rebuilt.alpha_composite(crop, (x, y))
                    assert not remaining.getbbox(), f'{language} page {number+1}: unassigned text pixels.'
                    assert rebuilt.tobytes() == text_image.tobytes(), 'Fragment partition changes typography.'
                    recomposed = Image.alpha_composite(background_image.convert('RGBA'), rebuilt).convert('RGB')
                    difference = ImageChops.difference(original_image, recomposed)
                    means = ImageStat.Stat(difference).mean
                    # Original full-page rasters remain the resting view. Small
                    # alpha rounding while decomposed is measured, never hidden.
                    assert max(means) < 0.5, f'{language} page {number+1}: separation changes the artwork.'
                    entry['verification'].append({'width': width,
                        'meanChannelDifference': [round(v, 6) for v in means],
                        'maximumChannelDifference': max(v[1] for v in difference.getextrema()),
                        'allTextPixelsAssignedExactlyOnce': True,
                        'backgroundContainsPdfText': False})
                    entry['variants'].append({'width': width,
                        'background': write_image(background_image, directory, f'page-{number+1:02d}-background', width),
                        'atlas': write_image(atlas, directory, f'page-{number+1:02d}-type', width)})
                result['languages'][language].append(entry)
                background_pdf.close()
                text_pdf.close()
                print(f'{language} {number+1}/13: {len(fragments)} independent text fragments verified', flush=True)
            original_pdf.close()
        destination = ROOT / 'public/portfolio-motion'
        if destination.exists():
            shutil.move(str(destination), str(Path(temporary) / 'previous'))
        shutil.move(str(staging), str(destination))
        (ROOT / 'src/motion.generated.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
        print('All 26 pages separated and verified; original page images unchanged.', flush=True)


if __name__ == '__main__':
    main()
