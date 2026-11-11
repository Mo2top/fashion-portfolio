import { useEffect, useRef, useState } from 'react'
import PortfolioPage from './components/PortfolioPage.jsx'
import portfolio from './portfolio.generated.json'

const storageKey = 'portfolio-language'

function initialLanguage() {
  try {
    return localStorage.getItem(storageKey) === 'zh' ? 'zh' : 'en'
  } catch {
    return 'en'
  }
}

export default function App() {
  const [language, setLanguage] = useState(initialLanguage)
  const portfolioRef = useRef(null)
  const switchRequest = useRef(0)

  useEffect(() => {
    document.documentElement.lang = language === 'zh' ? 'zh-Hans' : 'en'
    document.title = language === 'zh' ? '作品集' : 'Portfolio'
    try {
      localStorage.setItem(storageKey, language)
    } catch {
      // The portfolio also works when storage is unavailable.
    }
  }, [language])

  async function changeLanguage(nextLanguage) {
    const request = ++switchRequest.current
    if (nextLanguage === language) return

    // Both versions load together near the viewport. On a cold connection,
    // retain the current artwork until the replacement is decoded.
    const visibleImages = [...portfolioRef.current.querySelectorAll(
      `[data-language="${nextLanguage}"] img`,
    )].filter((image) => {
      const { top, bottom } = image.closest('.portfolio-page').getBoundingClientRect()
      return bottom > 0 && top < window.innerHeight
    })

    try {
      await Promise.all(visibleImages.map((image) => {
        image.loading = 'eager'
        image.fetchPriority = 'high'
        return image.decode()
      }))
      if (request === switchRequest.current) setLanguage(nextLanguage)
    } catch (error) {
      console.error('The requested portfolio images could not be loaded.', error)
    }
    // Stable page wrappers and aspect ratios preserve the exact scroll offset
    // and corresponding PDF page, with no remount or navigation.
  }

  return (
    <>
      <div className="language-switcher" role="group" aria-label="Language / 语言">
        <button type="button" lang="en" aria-pressed={language === 'en'}
          onClick={() => changeLanguage('en')}>EN</button>
        <span aria-hidden="true">/</span>
        <button type="button" lang="zh-Hans" aria-pressed={language === 'zh'}
          onClick={() => changeLanguage('zh')}>中文</button>
      </div>
      <main ref={portfolioRef} className="portfolio" data-language={language}
        aria-label={language === 'en' ? 'Portfolio' : '作品集'}>
        {portfolio.pages.map((page) => (
          <PortfolioPage key={page.number} page={page} language={language} />
        ))}
      </main>
    </>
  )
}
