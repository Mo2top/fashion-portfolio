import PortfolioPage from './PortfolioPage.jsx'
import { pageData } from '../lib/portfolioAssets.js'

export default function PortfolioScene({ index, language, width, prepared, role }) {
  const { data, variant } = prepared
  const [atlasWidth, atlasHeight] = data.atlasSize
  return (
    <div className="portfolio-scene" data-scene={role} aria-hidden="true">
      <img className="scene-background" src={variant.background.src} alt="" draggable="false" />
      <div className="scene-typography">
        {data.fragments.map((fragment, i) => {
          const [x, y, w, h] = fragment.rect
          const [sx, sy] = fragment.sprite
          return (
            <span key={i} className="text-fragment" data-rect={JSON.stringify(fragment.rect)}
              style={{
                left: `${x / 960 * 100}%`, top: `${y / 540 * 100}%`,
                width: `${w / 960 * 100}%`, height: `${h / 540 * 100}%`,
                backgroundImage: `url("${variant.atlas.src}")`,
                backgroundSize: `${atlasWidth / w * 100}% ${atlasHeight / h * 100}%`,
                backgroundPosition: `${atlasWidth === w ? 0 : sx / (atlasWidth - w) * 100}% ${atlasHeight === h ? 0 : sy / (atlasHeight - h) * 100}%`,
              }} />
          )
        })}
      </div>
      <PortfolioPage page={pageData(index)} language={language} width={width} />
    </div>
  )
}
