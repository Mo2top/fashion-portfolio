export default function PortfolioPage({ page, language, width, className = '' }) {
  const images = page.images[language]
  return (
    <picture className={`original-artwork ${className}`}>
      <img
        src={images.at(-1).src}
        srcSet={images.map((image) => `${image.src} ${image.width}w`).join(', ')}
        sizes={`${Math.ceil(width)}px`}
        width={page.width}
        height={page.height}
        decoding="async"
        fetchPriority="high"
        draggable="false"
        alt={language === 'en' ? `Portfolio — page ${page.number} of 13` : `作品集 — 第 ${page.number} 页，共 13 页`}
      />
    </picture>
  )
}
