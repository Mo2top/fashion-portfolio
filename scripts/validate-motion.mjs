import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import { readFile } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const hash = (data) => createHash('sha256').update(data).digest('hex')
try {
  const manifest = JSON.parse(await readFile(path.join(root, 'src/motion.generated.json'), 'utf8'))
  assert.equal(manifest.schemaVersion, 1)
  assert.equal(manifest.sourceManifestSha256,
    hash(await readFile(path.join(root, 'src/portfolio.generated.json'))),
    'Motion layers must be regenerated from the current original PDF import.')
  let assets = 0
  let fragments = 0
  for (const language of ['en', 'zh']) {
    assert.equal(manifest.languages[language].length, 13)
    for (const [index, page] of manifest.languages[language].entries()) {
      assert.equal(page.number, index + 1)
      assert.ok(page.copy.length > 0)
      assert.ok(page.fragments.length > 1, 'Typography must be separated into independent fragments.')
      assert.equal(page.variants.length, manifest.widths.length)
      for (const fragment of page.fragments) {
        const [x, y, width, height] = fragment.rect
        assert.ok(x >= 0 && y >= 0 && width > 0 && height > 0)
        assert.ok(x + width <= 960 && y + height <= 540)
        assert.ok(fragment.sprite[0] + width <= page.atlasSize[0])
        assert.ok(fragment.sprite[1] + height <= page.atlasSize[1])
        fragments++
      }
      for (const [i, variant] of page.variants.entries()) {
        assert.equal(variant.width, manifest.widths[i])
        assert.equal(page.verification[i].allTextPixelsAssignedExactlyOnce, true)
        assert.equal(page.verification[i].backgroundContainsPdfText, false)
        assert.ok(Math.max(...page.verification[i].meanChannelDifference) < 0.5)
        for (const asset of [variant.background, variant.atlas]) {
          assert.ok(asset.src.startsWith(`/portfolio-motion/${language}/`))
          assert.ok(!asset.src.includes('..'))
          const bytes = await readFile(path.join(root, 'public', asset.src))
          assert.equal(bytes.length, asset.bytes)
          assert.equal(hash(bytes), asset.sha256, `Missing or changed motion asset: ${asset.src}`)
          assets++
        }
      }
    }
  }
  console.log(`Verified 26 layered pages, ${fragments} independent text fragments, and ${assets} lossless motion assets.`)
} catch (error) {
  console.error(`Motion validation failed: ${error.message}`)
  process.exitCode = 1
}
