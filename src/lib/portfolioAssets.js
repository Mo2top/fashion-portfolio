import portfolio from '../portfolio.generated.json'
import motion from '../motion.generated.json'

export const PAGE_COUNT = portfolio.pages.length
export const pageData = (index) => portfolio.pages[index]
export const motionData = (index, language) => motion.languages[language][index]

const images = new Map()
export function loadImage(src, priority = 'auto') {
  if (images.has(src)) return images.get(src)
  const image = new Image()
  image.decoding = 'async'
  image.fetchPriority = priority
  image.src = src
  const promise = image.decode().catch((error) => {
    images.delete(src)
    throw error
  })
  images.set(src, promise)
  return promise
}

function variantFor(variants, frameWidth) {
  const target = frameWidth * Math.min(window.devicePixelRatio || 1, 3)
  return variants.find((variant) => variant.width >= target) || variants.at(-1)
}

export function loadOriginal(index, language, frameWidth, priority = 'auto') {
  const image = variantFor(pageData(index).images[language], frameWidth)
  return loadImage(image.src, priority)
}

export async function loadMotion(index, language, frameWidth) {
  const data = motionData(index, language)
  const variant = variantFor(data.variants, frameWidth)
  await Promise.all([loadImage(variant.background.src), loadImage(variant.atlas.src)])
  return { data, variant }
}
