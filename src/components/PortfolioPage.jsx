import { useEffect, useRef } from 'react'

export default function PortfolioPage({ page, language }) {
  const pageRef = useRef(null)

  useEffect(() => {
    const element = pageRef.current
    if (!('IntersectionObserver' in window)) return
    const observer = new IntersectionObserver((entries) => {
      if (entries.some((entry) => entry.isIntersecting)) {
        for (const image of element.querySelectorAll('img')) {
          image.loading = 'eager'
          void image.decode().catch(() => {})
        }
        observer.disconnect()
      }
    }, { rootMargin: '100% 0px' })
    observer.observe(element)
    return () => observer.disconnect()
  }, [])

  return (
    <div ref={pageRef} className="portfolio-page" data-page={page.number}
      style={{ aspectRatio: `${page.sourceDimensions.en.width} / ${page.sourceDimensions.en.height}` }}>
      {['en', 'zh'].map((version) => {
        const images = page.images[version]
        const largest = images[images.length - 1]
        return (
          <picture key={version} className="page-artwork" data-language={version}
            aria-hidden={version !== language}>
            <img
              src={largest.src}
              srcSet={images.map((image) => `${image.src} ${image.width}w`).join(', ')}
              sizes="100vw"
              width={page.width}
              height={page.height}
              loading={page.number === 1 ? 'eager' : 'lazy'}
              fetchPriority={page.number === 1 && version === language ? 'high' : 'auto'}
              decoding="async"
              alt={version === 'en'
                ? `Portfolio — page ${page.number} of 13`
                : `作品集 — 第 ${page.number} 页，共 13 页`}
            />
          </picture>
        )
      })}
    </div>
  )
}
