import { useLayoutEffect } from 'react'
import type { RefObject } from 'react'

const target = '[data-scroll-reveal], [data-scroll-fields] > .field, [data-scroll-copy] > p'

export function useViewportMotion(ref: RefObject<HTMLElement | null>, page: string) {
  useLayoutEffect(() => {
    const root = ref.current
    if (!root || typeof IntersectionObserver === 'undefined') return
    const preference = matchMedia('(prefers-reduced-motion: reduce)')
    const landing = root.querySelector('.landing')
    const disabled = () => preference.matches || landing?.hasAttribute('data-paused')
    const seen = new WeakSet<HTMLElement>()
    const waiting = new Set<HTMLElement>()

    function finish(element: HTMLElement) {
      if (waiting.delete(element)) observer.unobserve(element)
      element.removeAttribute('data-scroll-state')
      element.style.removeProperty('--reveal-delay')
    }

    const observer = new IntersectionObserver(entries => {
      const groups = new Map<Element, number>()
      for (const { target, isIntersecting } of entries) {
        const element = target as HTMLElement
        if (!isIntersecting || !waiting.delete(element)) continue
        observer.unobserve(element)
        if (disabled() || element.matches(':focus-within')) { finish(element); continue }
        const group = element.parentElement
        const step = group ? groups.get(group) ?? 0 : 0
        if (group) groups.set(group, step + 1)
        element.style.setProperty('--reveal-delay', `${Math.min(step, 3) * 36}ms`)
        element.dataset.scrollState = 'enter'
      }
    }, { threshold: 0 })

    function collect(node: Element, candidates: Set<HTMLElement>) {
      if (node instanceof HTMLElement && node.matches(target)) candidates.add(node)
      node.querySelectorAll<HTMLElement>(target).forEach(element => candidates.add(element))
    }

    function register(candidates: Set<HTMLElement>, initial: boolean) {
      const bottom = document.documentElement.clientHeight
      const queue = [...candidates].filter(element => {
        if (seen.has(element) || !root!.contains(element)) return false
        seen.add(element)
        if (disabled() || element.matches(':focus-within')) return false
        const { top, bottom: end, height } = element.getBoundingClientRect()
        return height > 0 && (initial ? top >= bottom : end > 0)
      })
      for (const element of queue) {
        waiting.add(element)
        element.dataset.scrollState = 'waiting'
        observer.observe(element)
      }
    }

    function settle() {
      if (disabled()) root!.querySelectorAll<HTMLElement>('[data-scroll-state]').forEach(finish)
    }

    function expose(event: Event) {
      if (!(event.target instanceof Element)) return
      for (let element = event.target.closest<HTMLElement>(target); element; element = element.parentElement?.closest<HTMLElement>(target) ?? null) finish(element)
    }

    const changes = new MutationObserver(records => {
      const candidates = new Set<HTMLElement>()
      for (const record of records) for (const node of record.addedNodes) if (node instanceof Element) collect(node, candidates)
      for (const element of waiting) if (!root.contains(element)) finish(element)
      register(candidates, false)
    })
    const pause = landing && new MutationObserver(settle)
    if (landing && pause) pause.observe(landing, { attributes: true, attributeFilter: ['data-paused'] })
    const initial = new Set<HTMLElement>()
    collect(root, initial)
    register(initial, true)
    changes.observe(root, { childList: true, subtree: true })
    preference.addEventListener('change', settle)
    root.addEventListener('focusin', expose)
    root.addEventListener('invalid', expose, true)
    return () => {
      changes.disconnect()
      pause?.disconnect()
      observer.disconnect()
      preference.removeEventListener('change', settle)
      root.removeEventListener('focusin', expose)
      root.removeEventListener('invalid', expose, true)
      root.querySelectorAll<HTMLElement>('[data-scroll-state]').forEach(finish)
    }
  }, [ref, page])
}
