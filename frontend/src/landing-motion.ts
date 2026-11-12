import { useLayoutEffect, useRef, useState } from 'react'

const pauseKey = 'pdd-landing-motion-paused'

function wasPaused() {
  try { return sessionStorage.getItem(pauseKey) === 'true' }
  catch { return false }
}

export function useLandingMotion() {
  const landing = useRef<HTMLDivElement>(null)
  const [paused, setPaused] = useState(wasPaused)
  const intro = useRef(!paused)

  function toggle() {
    const next = !paused
    intro.current = false
    if (next) landing.current?.querySelectorAll<HTMLElement>("[data-reveal='active']").forEach(scene => {
      scene.dataset.reveal = 'instant'
    })
    try { sessionStorage.setItem(pauseKey, String(next)) } catch { /* storage can be unavailable */ }
    setPaused(next)
  }

  useLayoutEffect(() => {
    if (!landing.current || typeof IntersectionObserver === 'undefined') return
    const root = landing.current
    const motion = matchMedia('(prefers-reduced-motion: no-preference)')
    const compact = matchMedia('(max-width: 760px)')
    const audience = root.querySelector<HTMLElement>('.audience')!
    const cards = Array.from(audience.querySelectorAll<HTMLElement>('.audience-card'))
    const scenes = root.querySelectorAll<HTMLElement>('[data-reveal]')
    const loops = root.querySelectorAll<HTMLElement>('[data-loop]')
    let audienceVisible = false
    let frame: number | undefined

    function updateDepth() {
      frame = undefined
      const viewport = document.documentElement.clientHeight
      const offsets = cards.map(card => {
        const { top, height } = card.getBoundingClientRect()
        const progress = (viewport - height / 2 - top) / viewport - .5
        return Math.max(-1, Math.min(1, progress * 2)) * (compact.matches ? 14 : 24)
      })
      cards.forEach((card, index) => card.style.setProperty('--depth-y', `${offsets[index].toFixed(1)}px`))
    }

    function scheduleDepth() {
      if (frame === undefined && audienceVisible && motion.matches && !document.hidden && !root.hasAttribute('data-paused')) {
        frame = requestAnimationFrame(updateDepth)
      }
    }

    function syncDepth() {
      if (motion.matches && !root.hasAttribute('data-paused') && !document.hidden) scheduleDepth()
      else if (frame !== undefined) {
        cancelAnimationFrame(frame)
        frame = undefined
      }
    }

    // A focus target must be readable immediately, even if the browser just scrolled to it.
    function onFocus(event: FocusEvent) {
      const scene = (event.target as Element).closest<HTMLElement>('[data-reveal]')
      if (scene) {
        scene.dataset.reveal = 'instant'
        reveal.unobserve(scene)
      }
    }

    const reveal = new IntersectionObserver(entries => {
      for (const { target, isIntersecting } of entries) {
        if (!isIntersecting) continue
        const scene = target as HTMLElement
        scene.dataset.reveal = motion.matches && !root.hasAttribute('data-paused') ? 'active' : 'instant'
        reveal.unobserve(target)
      }
    }, { rootMargin: '0px 0px 20px', threshold: .04 })

    const viewport = new IntersectionObserver(entries => {
      for (const { target, isIntersecting } of entries) {
        if (target === audience) audienceVisible = isIntersecting
        else (target as HTMLElement).dataset.loop = isIntersecting ? 'visible' : ''
      }
      scheduleDepth()
    })

    const pauseObserver = new MutationObserver(syncDepth)
    pauseObserver.observe(root, { attributes: true, attributeFilter: ['data-paused'] })
    scenes.forEach(scene => reveal.observe(scene))
    loops.forEach(loop => viewport.observe(loop))
    viewport.observe(audience)
    root.dataset.scenes = ''
    root.addEventListener('focusin', onFocus)
    window.addEventListener('scroll', scheduleDepth, { passive: true })
    window.addEventListener('resize', scheduleDepth)
    document.addEventListener('visibilitychange', syncDepth)
    motion.addEventListener('change', syncDepth)

    return () => {
      if (frame !== undefined) cancelAnimationFrame(frame)
      reveal.disconnect()
      viewport.disconnect()
      pauseObserver.disconnect()
      root.removeEventListener('focusin', onFocus)
      window.removeEventListener('scroll', scheduleDepth)
      window.removeEventListener('resize', scheduleDepth)
      document.removeEventListener('visibilitychange', syncDepth)
      motion.removeEventListener('change', syncDepth)
    }
  }, [])

  return { landing, paused, intro: intro.current, toggle }
}
