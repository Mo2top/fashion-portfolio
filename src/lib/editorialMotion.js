export const TRANSITION_DURATION = 2000
const cinematic = 'cubic-bezier(0.22, 0.61, 0.36, 1)'

function random(seed) {
  const value = Math.sin(seed * 127.1 + 311.7) * 43758.5453
  return value - Math.floor(value)
}

export function animateEditorial(frame, transition, onComplete) {
  const animations = []
  const animate = (element, keyframes, options) => {
    const animation = element.animate(keyframes, { fill: 'both', easing: cinematic, ...options })
    animations.push(animation)
    return animation
  }
  const outgoing = frame.querySelector('[data-scene="outgoing"]')
  const incoming = frame.querySelector('[data-scene="incoming"]')
  const width = frame.getBoundingClientRect().width
  const strength = Math.min(width, 1600) * 0.055
  const blur = Math.min(4, Math.max(1.3, width / 400))

  // The complete original is replaced by a pixel-verified decomposition before
  // any fragment moves. Incoming typography returns to the original at rest.
  animate(outgoing.querySelector('.original-artwork'), [{ opacity: 1 }, { opacity: 0 }],
    { duration: 100 })
  animate(outgoing.querySelector('.scene-background'), [{ opacity: 1 }, { opacity: 0 }],
    { delay: 60, duration: 1100 })
  animate(incoming.querySelector('.scene-background'), [{ opacity: 0 }, { opacity: 1 }],
    { delay: 650, duration: 1200 })

  for (const [scene, entering] of [[outgoing, false], [incoming, true]]) {
    const fragments = [...scene.querySelectorAll('.text-fragment')]
    fragments.forEach((element, index) => {
      const [x, y, w, h] = JSON.parse(element.dataset.rect)
      const seed = (entering ? transition.to : transition.from) * 91 + index + 1
      const jitter = random(seed)
      let dx = ((x + w / 2) / 960 - 0.5) * 1.5 + (jitter - 0.5) * 0.5
      let dy = ((y + h / 2) / 540 - 0.5) * 1.5 + (random(seed + 9) - 0.5) * 0.5
      const length = Math.hypot(dx, dy) || 1
      dx = dx / length * strength * (0.55 + jitter * 0.65)
      dy = dy / length * strength * (0.55 + random(seed + 2) * 0.65)
      const rotation = (random(seed + 3) - 0.5) * 4
      const rest = { transform: 'translate3d(0, 0, 0) rotate(0deg)', opacity: 1, filter: 'blur(0px)' }
      const dispersed = {
        transform: `translate3d(${dx}px, ${dy}px, 0) rotate(${rotation}deg)`,
        opacity: 0, filter: `blur(${blur}px)`,
      }
      const arrival = {
        transform: `translate3d(${dx * 0.16}px, ${dy * 0.16 + Math.min(12, width * 0.012)}px, 0) rotate(${rotation * 0.12}deg)`,
        opacity: 0, filter: `blur(${blur * 0.7}px)`,
      }
      animate(element, entering ? [arrival, rest] : [rest, dispersed], {
        delay: entering ? 930 + jitter * 140 : 110 + jitter * 160,
        duration: entering ? 760 : 810,
      })
    })
  }
  animate(incoming.querySelector('.original-artwork'), [{ opacity: 0 }, { opacity: 1 }],
    { delay: TRANSITION_DURATION - 150, duration: 150 })
  Promise.all(animations.map((animation) => animation.finished)).then(onComplete).catch(() => {})
  return () => animations.forEach((animation) => animation.cancel())
}
