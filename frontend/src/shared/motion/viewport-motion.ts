import { useLayoutEffect } from 'react'
import type { RefObject } from 'react'

const target = '[data-scroll-reveal], [data-scroll-fields] > .field, [data-scroll-copy] > p, [data-loop]'

export function useViewportMotion(ref: RefObject<HTMLElement | null>, page: string, enabled: boolean) {
  useLayoutEffect(() => {
    const root = ref.current
    if (!enabled || !root || typeof IntersectionObserver === 'undefined') return
    const observed = new Set<HTMLElement>()
    const observer = new IntersectionObserver(entries => {
      for (const { target, isIntersecting, intersectionRatio } of entries) {
        const element = target as HTMLElement
        if (element.hasAttribute('data-loop')) element.dataset.loop = isIntersecting ? 'visible' : ''
        else if (!isIntersecting) delete element.dataset.scrollState
        else if (intersectionRatio >= .15) element.dataset.scrollState = 'enter'
      }
    }, { threshold: [0, .15] })

    function observeChildren(element: Element) {
      const children = Array.from(element.querySelectorAll<HTMLElement>(target))
      if (element instanceof HTMLElement && element.matches(target)) children.unshift(element)
      for (const child of children) {
        if (observed.has(child)) continue
        observed.add(child)
        observer.observe(child)
      }
    }

    observeChildren(root)
    const changes = new MutationObserver(records => {
      for (const element of observed) {
        if (root.contains(element)) continue
        observer.unobserve(element)
        observed.delete(element)
      }
      for (const record of records) for (const node of record.addedNodes) {
        if (node instanceof Element) observeChildren(node)
      }
    })
    changes.observe(root, { childList: true, subtree: true })
    return () => {
      changes.disconnect()
      observer.disconnect()
      for (const element of observed) {
        delete element.dataset.scrollState
        if (element.hasAttribute('data-loop')) element.dataset.loop = ''
      }
    }
  }, [ref, page, enabled])
}
