import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import PortfolioPage from './components/PortfolioPage.jsx'
import PortfolioScene from './components/PortfolioScene.jsx'
import { PAGE_COUNT, pageData, motionData, loadOriginal, loadMotion } from './lib/portfolioAssets.js'
import { animateEditorial } from './lib/editorialMotion.js'

const storageKey = 'portfolio-language'
const interactive = 'a, button, input, textarea, select, [contenteditable="true"], [role="button"]'
function initialLanguage() {
  try { return localStorage.getItem(storageKey) === 'zh' ? 'zh' : 'en' }
  catch { return 'en' }
}
function initialWidth() {
  return Math.min(window.innerWidth, Math.max(1, window.innerHeight - 112) * 16 / 9)
}

export default function App() {
  const [language, setLanguage] = useState(initialLanguage)
  const [index, setIndex] = useState(0)
  const [transition, setTransition] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(false)
  const [width, setWidth] = useState(initialWidth)
  const [reduced, setReduced] = useState(() => matchMedia('(prefers-reduced-motion: reduce)').matches)
  const frameRef = useRef(null)
  const busy = useRef(false)
  const ticket = useRef(0)
  const stopAnimation = useRef(null)
  const activeTransition = useRef(null)
  const pendingLanguage = useRef(null)
  const current = useRef({ index, language, width, reduced })
  const navigation = useRef(null)
  const pointer = useRef(null)
  const suppressClick = useRef(false)
  current.current = { index, language, width, reduced }

  useEffect(() => {
    document.documentElement.lang = language === 'zh' ? 'zh-Hans' : 'en'
    document.title = language === 'zh' ? '作品集' : 'Portfolio'
    try { localStorage.setItem(storageKey, language) } catch { /* Storage is optional. */ }
  }, [language])

  useLayoutEffect(() => {
    const observer = new ResizeObserver(([entry]) => setWidth(entry.contentRect.width))
    observer.observe(frameRef.current)
    return () => observer.disconnect()
  }, [])

  function settle() {
    ticket.current++
    const destination = activeTransition.current?.to ?? current.current.index
    stopAnimation.current?.()
    stopAnimation.current = null
    activeTransition.current = null
    pendingLanguage.current = null
    busy.current = false
    setTransition(null)
    setIndex(destination)
    setLoading(false)
    return destination
  }

  useEffect(() => {
    const media = matchMedia('(prefers-reduced-motion: reduce)')
    const update = () => {
      setReduced(media.matches)
      current.current.reduced = media.matches
      if (media.matches) settle()
    }
    media.addEventListener('change', update)
    return () => media.removeEventListener('change', update)
  }, [])

  useEffect(() => () => { ticket.current++; stopAnimation.current?.() }, [])

  // Only the current and adjacent scenes warm. The original remains visible
  // while motion assets arrive; cold network time is outside the 2s animation.
  useEffect(() => {
    let cancelled = false
    const prepare = () => {
      if (cancelled) return
      const view = current.current
      const neighbors = [index, index + 1, index - 1].filter((i) => i >= 0 && i < PAGE_COUNT)
      void loadOriginal(index, language === 'en' ? 'zh' : 'en', view.width).catch(() => {})
      for (const i of neighbors) {
        void loadOriginal(i, language, view.width).catch(() => {})
        if (!view.reduced && !navigator.connection?.saveData) {
          void loadMotion(i, language, view.width).catch(() => {})
        }
      }
    }
    const handle = window.requestIdleCallback
      ? window.requestIdleCallback(prepare, { timeout: 1000 })
      : window.setTimeout(prepare, 180)
    return () => {
      cancelled = true
      if (window.cancelIdleCallback) window.cancelIdleCallback(handle)
      else clearTimeout(handle)
    }
  }, [index, language, reduced])

  async function navigate(destination) {
    const view = current.current
    if (busy.current || destination < 0 || destination >= PAGE_COUNT || destination === view.index) return
    busy.current = true
    setLoading(true)
    setError(false)
    const request = ++ticket.current
    try {
      const original = loadOriginal(destination, view.language, view.width, 'high')
      if (view.reduced || matchMedia('(prefers-reduced-motion: reduce)').matches || !Element.prototype.animate) {
        await original
        if (request !== ticket.current) return
        setIndex(destination)
        setLoading(false)
        busy.current = false
        return
      }
      const [outgoing, incoming] = await Promise.all([
        loadMotion(view.index, view.language, view.width),
        loadMotion(destination, view.language, view.width), original,
      ])
      if (request !== ticket.current) return
      const scene = { id: request, from: view.index, to: destination, outgoing, incoming }
      activeTransition.current = scene
      setTransition(scene)
      setLoading(false)
    } catch {
      if (request !== ticket.current) return
      busy.current = false
      setLoading(false)
      setError(true)
    }
  }
  navigation.current = navigate

  useLayoutEffect(() => {
    if (!transition) return
    const stop = animateEditorial(frameRef.current, transition, () => {
      if (transition.id !== ticket.current) return
      activeTransition.current = null
      busy.current = false
      setIndex(transition.to)
      setTransition(null)
    })
    stopAnimation.current = stop
    return () => {
      stop()
      if (stopAnimation.current === stop) stopAnimation.current = null
    }
  }, [transition])

  async function changeLanguage(nextLanguage) {
    if (nextLanguage === current.current.language) {
      if (pendingLanguage.current) settle()
      return
    }
    const destination = settle()
    const request = ++ticket.current
    busy.current = true
    pendingLanguage.current = nextLanguage
    setLoading(true)
    setError(false)
    try {
      await loadOriginal(destination, nextLanguage, current.current.width, 'high')
      if (request !== ticket.current) return
      setLanguage(nextLanguage)
      pendingLanguage.current = null
      setLoading(false)
      busy.current = false
    } catch {
      if (request !== ticket.current) return
      setLoading(false)
      setError(true)
      pendingLanguage.current = null
      busy.current = false
    }
  }

  useEffect(() => {
    const onKey = (event) => {
      if (event.altKey || event.ctrlKey || event.metaKey ||
          event.target.closest?.('input, textarea, select, [contenteditable="true"]')) return
      if (event.key === ' ' && event.target.closest?.('a, button, [role="button"]')) return
      let destination
      if (['ArrowRight', 'ArrowDown', ' '].includes(event.key)) destination = current.current.index + 1
      if (['ArrowLeft', 'ArrowUp'].includes(event.key)) destination = current.current.index - 1
      if (event.key === 'Home') destination = 0
      if (event.key === 'End') destination = PAGE_COUNT - 1
      if (destination !== undefined) {
        event.preventDefault()
        void navigation.current(destination)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  function clickPage(event) {
    if (suppressClick.current || event.button !== 0 || event.ctrlKey || event.metaKey ||
        event.target.closest(interactive) || window.getSelection()?.toString()) return
    void navigate(current.current.index + 1)
  }
  function pointerDown(event) {
    pointer.current = { x: event.clientX, y: event.clientY, type: event.pointerType }
    suppressClick.current = false
  }
  function pointerUp(event) {
    if (!pointer.current) return
    const dx = event.clientX - pointer.current.x
    const dy = event.clientY - pointer.current.y
    suppressClick.current = Math.hypot(dx, dy) > 10
    if (pointer.current.type === 'touch' && Math.abs(dx) > 48 && Math.abs(dx) > Math.abs(dy) * 1.3) {
      void navigate(current.current.index + (dx < 0 ? 1 : -1))
    }
    pointer.current = null
  }

  const isBusy = loading || Boolean(transition)
  const label = (number) => language === 'en' ? `Page ${number} of ${PAGE_COUNT}` : `第 ${number} 页，共 ${PAGE_COUNT} 页`
  return (
    <>
      <main className="portfolio-stage" data-language={language} data-page={index + 1}
        data-transitioning={Boolean(transition)} aria-busy={isBusy}
        aria-label={language === 'en' ? 'Portfolio. Click to advance; use arrow keys to navigate.' : '作品集。点击翻页，也可使用方向键。'}
        tabIndex={0} onClick={clickPage} onPointerDown={pointerDown} onPointerUp={pointerUp}
        onPointerCancel={() => { pointer.current = null; suppressClick.current = true }}>
        <section ref={frameRef} className="portfolio-frame" aria-label={label(index + 1)}>
          {transition ? <>
            <PortfolioScene key={`out-${transition.id}`} index={transition.from} language={language}
              width={width} prepared={transition.outgoing} role="outgoing" />
            <PortfolioScene key={`in-${transition.id}`} index={transition.to} language={language}
              width={width} prepared={transition.incoming} role="incoming" />
          </> : <PortfolioPage page={pageData(index)} language={language} width={width} />}
        </section>
        <p className="screen-reader-only">{motionData(index, language).copy}</p>
      </main>

      <div className="language-switcher" role="group" aria-label="Language / 语言">
        <button type="button" lang="en" aria-pressed={language === 'en'}
          onPointerEnter={() => { void loadOriginal(current.current.index, 'en', width).catch(() => {}) }}
          onFocus={() => { void loadOriginal(current.current.index, 'en', width).catch(() => {}) }}
          onClick={() => changeLanguage('en')}>EN</button>
        <span aria-hidden="true">/</span>
        <button type="button" lang="zh-Hans" aria-pressed={language === 'zh'}
          onPointerEnter={() => { void loadOriginal(current.current.index, 'zh', width).catch(() => {}) }}
          onFocus={() => { void loadOriginal(current.current.index, 'zh', width).catch(() => {}) }}
          onClick={() => changeLanguage('zh')}>中文</button>
      </div>

      <nav className="page-navigation" aria-label={language === 'en' ? 'Portfolio pages' : '作品集翻页'}>
        <button type="button" className="page-arrow" disabled={index === 0 || isBusy}
          aria-label={language === 'en' ? 'Previous page' : '上一页'} onClick={() => navigate(index - 1)}>
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M19 12H5m6-6-6 6 6 6" /></svg>
        </button>
        <div className="page-dots">
          {Array.from({ length: PAGE_COUNT }, (_, i) => (
            <button type="button" key={i} disabled={isBusy} aria-label={label(i + 1)}
              aria-current={i === index ? 'page' : undefined} onClick={() => navigate(i)}><span /></button>
          ))}
        </div>
        <output className="page-count" aria-live="polite" aria-atomic="true">
          <span>{String(index + 1).padStart(2, '0')}</span><span className="count-slash">/</span><span>13</span>
        </output>
        <button type="button" className="page-arrow" disabled={index === PAGE_COUNT - 1 || isBusy}
          aria-label={language === 'en' ? 'Next page' : '下一页'} onClick={() => navigate(index + 1)}>
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12h14m-6-6 6 6-6 6" /></svg>
        </button>
      </nav>
      {error && <p className="page-error" role="status">{language === 'en' ? 'Could not load this page. Please try again.' : '页面加载失败，请重试。'}</p>}
    </>
  )
}
