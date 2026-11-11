import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import { readFile } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')

try {
  const manifest = JSON.parse(await readFile(path.join(root, 'src/portfolio.generated.json'), 'utf8'))
  assert.equal(manifest.schemaVersion, 1, 'Unsupported asset manifest.')
  assert.equal(manifest.status, 'ready',
    'The original PDFs have not been imported. Run npm run import:pdf -- --en <PDF> --zh <PDF>.')
  assert.equal(manifest.pages.length, 13, 'Exactly 13 pages are required in each language.')
  assert.equal(manifest.rendering.format, 'lossless WebP')
  const widths = manifest.rendering.widths
  assert.ok(Array.isArray(widths) && widths.length > 0)
  assert.ok(widths.every((width, i) => Number.isInteger(width) && width > (widths[i - 1] ?? 0)))
  const seen = new Set()
  let count = 0
  let bytes = 0

  for (const [index, page] of manifest.pages.entries()) {
    assert.equal(page.number, index + 1, 'Pages must remain in their original order.')
    assert.equal(page.width, widths.at(-1))
    assert.ok(Number.isInteger(page.height) && page.height > 0)
    for (const language of ['en', 'zh']) {
      assert.equal(manifest.sources[language].reduce((sum, source) => sum + source.pageCount, 0), 13)
      const images = page.images[language]
      assert.equal(images.length, widths.length)
      for (const [variant, image] of images.entries()) {
        assert.equal(image.width, widths[variant])
        assert.equal(image.height, page.images.en[variant].height,
          `Page ${page.number}: corresponding language image dimensions must match.`)
        assert.ok(image.src.startsWith(`/portfolio/${language}/page-`))
        assert.ok(!image.src.includes('..') && image.src.endsWith('.webp'))
        assert.ok(!seen.has(image.src), 'Each page variant needs a unique asset path.')
        seen.add(image.src)
        const file = await readFile(path.join(root, 'public', image.src))
        assert.equal(file.toString('ascii', 0, 4), 'RIFF')
        assert.equal(file.toString('ascii', 8, 12), 'WEBP')
        assert.equal(file.length, image.bytes, `Image size mismatch: ${image.src}`)
        assert.equal(createHash('sha256').update(file).digest('hex'), image.sha256,
          `Image is missing or changed: ${image.src}`)
        bytes += file.length
        count++
      }
    }
  }
  console.log(`Verified 13 pages × 2 languages, ${count} lossless assets, ${(bytes / 1024 / 1024).toFixed(2)} MiB.`)
} catch (error) {
  console.error(`Portfolio validation failed: ${error.message}`)
  process.exitCode = 1
}
